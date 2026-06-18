"""
IAA (Inter-Annotator Agreement) výpočet pro pole E1.

Vstup:  2× JSON export z Label Studia (gold = primární anotátor, gemini = 2. anotátor)
Výstup: Cohen's kappa, Weighted kappa, percent agreement, confusion matrix, top neshody.
"""
import json
import pandas as pd
from sklearn.metrics import cohen_kappa_score, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# ============================================================================
# KONFIGURACE — uprav názvy souborů zde, pokud máš jiné
# ============================================================================
SCRIPT_DIR = Path(__file__).resolve().parent

GOLD_PATH = SCRIPT_DIR / "gold_standard_label_studio_400.json"
GEMINI_PATH = SCRIPT_DIR / "gemini_annotations_30.json"
OUTPUT_DIR = SCRIPT_DIR / "iaa_outputs"

# Pole, které vyhodnocujeme
TARGET_FIELD = "E1-misleading_header_model_final"

# Pořadí labelů pro ordinální váhování (NOT < POTENTIALLY < MISLEADING)
LABEL_ORDER = ["NOT_MISLEADING", "POTENTIALLY_MISLEADING", "MISLEADING"]

# ============================================================================
# FUNKCE
# ============================================================================

def parse_label_studio_export(path, target_field: str) -> pd.DataFrame:
    """
    Parsuje Label Studio JSON export do DataFrame se sloupci: id, header, <target_field>.
    Tiše přeskakuje záznamy bez anotace nebo bez target_field. 
    Počet přeskočených najdeš v finálním souhrnu (total vs. parsed).
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    rows = []
    for record in data:
        record_id = record["data"].get("id")
        header = record["data"].get("header", "")
        
        annotations = record.get("annotations", [])
        if not annotations:
            continue
        
        result = annotations[0].get("result", [])
        target_value = None
        for r in result:
            if r.get("from_name") == target_field:
                choices = r.get("value", {}).get("choices", [])
                if choices:
                    target_value = choices[0]
                break
        
        if target_value is None:
            continue
        
        rows.append({
            "id": record_id,
            "header": header,
            target_field: target_value,
        })
    
    parsed_count = len(rows)
    total_count = len(data)
    if parsed_count < total_count:
        print(f"  ℹ️  Naparsováno {parsed_count}/{total_count} (zbytek přeskočen — chybí anotace nebo {target_field})")
    
    return pd.DataFrame(rows)


def compute_iaa(gold_df: pd.DataFrame, gemini_df: pd.DataFrame, 
                target_field: str, output_dir) -> dict:
    """Spočítá IAA metriky a vykreslí confusion matrix."""
    
    # Spárovat podle id (jen záznamy, které jsou v obou)
    merged = gold_df.merge(
        gemini_df,
        on="id",
        suffixes=("_gold", "_gemini"),
        how="inner"
    )
    
    print(f"\n=== IAA EVALUACE pro pole {target_field} ===")
    print(f"Spárované záznamy: {len(merged)}")
    
    if len(merged) == 0:
        print("❌ ŽÁDNÉ spárované záznamy! Zkontroluj, jestli ID v obou souborech sedí.")
        return {}
    
    gold_labels = merged[f"{target_field}_gold"].tolist()
    gemini_labels = merged[f"{target_field}_gemini"].tolist()
    
    # 1. Cohen's kappa (klasický, nominální)
    kappa_classic = cohen_kappa_score(gold_labels, gemini_labels)
    
    # 2. Weighted kappa (kvadratický, ordinální)
    # Mapování labelů na čísla podle LABEL_ORDER
    label_to_int = {lbl: i for i, lbl in enumerate(LABEL_ORDER)}
    gold_int = [label_to_int[l] for l in gold_labels]
    gemini_int = [label_to_int[l] for l in gemini_labels]
    kappa_weighted = cohen_kappa_score(gold_int, gemini_int, weights="quadratic")
    
    # 3. Percent agreement
    agreements = sum(1 for g, m in zip(gold_labels, gemini_labels) if g == m)
    percent_agreement = agreements / len(merged) * 100
    
    # 4. Confusion matrix
    cm = confusion_matrix(gold_labels, gemini_labels, labels=LABEL_ORDER)
    cm_df = pd.DataFrame(cm, index=LABEL_ORDER, columns=LABEL_ORDER)
    
    # Vykreslit confusion matrix
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm_df, annot=True, fmt="d", cmap="Blues", cbar=True,
                xticklabels=LABEL_ORDER, yticklabels=LABEL_ORDER)
    plt.xlabel("Gemini (2. anotátor)")
    plt.ylabel("Gold (primární anotátor)")
    plt.title(f"Confusion Matrix — {target_field}\n"
              f"κ = {kappa_classic:.3f} (klasická), κw = {kappa_weighted:.3f} (weighted)")
    plt.tight_layout()
    cm_path = output_dir / "confusion_matrix_E1.png"
    plt.savefig(cm_path, dpi=150)
    plt.close()
    
    # 5. Top neshody (záznamy, kde se anotátoři liší)
    disagreements = merged[merged[f"{target_field}_gold"] != merged[f"{target_field}_gemini"]].copy()
    disagreements_path = output_dir / "disagreements_E1.csv"
    disagreements[["id", "header_gold", f"{target_field}_gold", f"{target_field}_gemini"]].rename(
        columns={"header_gold": "header"}
    ).to_csv(
        disagreements_path, index=False, encoding="utf-8"
    )
    
    # 6. Marginální distribuce (extra — zdarma s tím, že už máme data)
    print("\n--- VÝSLEDKY ---")
    print(f"Cohen's kappa (klasický):    {kappa_classic:.3f}")
    print(f"Cohen's kappa (weighted):    {kappa_weighted:.3f}")
    print(f"Percent agreement:            {percent_agreement:.1f}% ({agreements}/{len(merged)})")
    print(f"\nDistribuce gold:")
    print(merged[f"{target_field}_gold"].value_counts().reindex(LABEL_ORDER, fill_value=0).to_string())
    print(f"\nDistribuce Gemini:")
    print(merged[f"{target_field}_gemini"].value_counts().reindex(LABEL_ORDER, fill_value=0).to_string())
    print(f"\nNeshod celkem: {len(disagreements)}")
    print(f"\nConfusion matrix:")
    print(cm_df.to_string())
    
    # Interpretace podle Landis & Koch
    interpretation = interpret_kappa(kappa_classic)
    print(f"\nInterpretace (Landis & Koch): {interpretation}")
    
    # Uložit výsledky do CSV
    results = {
        "field": target_field,
        "n_paired": len(merged),
        "kappa_classic": round(kappa_classic, 4),
        "kappa_weighted_quadratic": round(kappa_weighted, 4),
        "percent_agreement": round(percent_agreement, 2),
        "n_disagreements": len(disagreements),
        "interpretation_landis_koch": interpretation,
    }
    results_df = pd.DataFrame([results])
    results_df.to_csv(output_dir / "iaa_results_E1.csv", index=False)
    
    print(f"\n✅ Výstupy uloženy do: {output_dir}")
    print(f"   - confusion_matrix_E1.png")
    print(f"   - disagreements_E1.csv ({len(disagreements)} záznamů)")
    print(f"   - iaa_results_E1.csv")
    
    return results


def interpret_kappa(k: float) -> str:
    """Landis & Koch (1977) stupnice."""
    if k < 0:
        return "Horší než náhoda"
    elif k < 0.20:
        return "Slabá shoda"
    elif k < 0.40:
        return "Spravedlivá shoda"
    elif k < 0.60:
        return "Mírná shoda"
    elif k < 0.80:
        return "Podstatná shoda"
    else:
        return "Téměř dokonalá shoda"


# ============================================================================
# MAIN
# ============================================================================
if __name__ == "__main__":
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"Načítám gold: {GOLD_PATH.name}")
    gold_df = parse_label_studio_export(GOLD_PATH, TARGET_FIELD)
    print(f"  → {len(gold_df)} záznamů")
    
    print(f"\nNačítám gemini: {GEMINI_PATH.name}")
    if not GEMINI_PATH.exists():
        print(f"  ⚠️  Soubor {GEMINI_PATH.name} zatím neexistuje ve složce skriptu.")
        print(f"\nGold parsing OK ({len(gold_df)} záznamů). Distribuce E1 v gold:")
        print(gold_df[TARGET_FIELD].value_counts().reindex(LABEL_ORDER, fill_value=0).to_string())
    else:
        gemini_df = parse_label_studio_export(GEMINI_PATH, TARGET_FIELD)
        print(f"  → {len(gemini_df)} záznamů")
        compute_iaa(gold_df, gemini_df, TARGET_FIELD, OUTPUT_DIR)