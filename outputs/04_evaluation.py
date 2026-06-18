"""
Evaluation skript — univerzální verze pro full + short + combined.

Skript automaticky:
  1. Vyhodnotí predikce z predictions/        → eval_outputs/full/
  2. Vyhodnotí predikce z predictions_short/  → eval_outputs/short/
  3. Vyrobí kombinované grafy (full vs. short) → eval_outputs/combined/

Pro každou variantu generuje:
  - CSV tabulky (summary, e1_detail, multilabel)
  - Markdown report
  - Confusion matrices pro všechna single-label pole
  - Sadu sloupcových grafů (F1 per pole, κ per pole, distribuční bias, atd.)

Použití:
  python 04_evaluation.py
"""
import json
import re
from pathlib import Path
from collections import Counter, defaultdict

import pandas as pd
import numpy as np
from sklearn.metrics import (
    accuracy_score, f1_score, precision_recall_fscore_support,
    cohen_kappa_score, confusion_matrix, jaccard_score, hamming_loss,
)
import matplotlib.pyplot as plt
import seaborn as sns

# ============================================================================
# KONFIGURACE
# ============================================================================
SCRIPT_DIR = Path(__file__).resolve().parent

# Adresáře s predikcemi (full + short)
PREDICTIONS_FULL = SCRIPT_DIR / "predictions"
PREDICTIONS_SHORT = SCRIPT_DIR / "predictions_short"

# Konfigurace pro každou variantu — bez/s _short suffixem
CONFIGS_FULL = [
    "llama_base_zs",
    "llama_base_qlora_zs",
    "llama_instruct_zs",
    "llama_instruct_qlora_zs",
    "gpt_5_5_zs",
]
CONFIGS_SHORT = [c + "_short" for c in CONFIGS_FULL]

# Hezké labely pro grafy (technické názvy zůstávají v CSV)
PRETTY_LABELS = {
    "llama_base_zs":              "Llama Base ZS",
    "llama_base_qlora_zs":        "Llama Base QLoRA",
    "llama_instruct_zs":          "Llama Instruct ZS",
    "llama_instruct_qlora_zs":    "Llama Instruct QLoRA",
    "gpt_5_5_zs":                 "GPT-5.5",
}
def pretty(config_name: str, with_variant: bool = False) -> str:
    """Vrátí hezký label.
    
    with_variant=False: "Llama Base ZS"  (pro full/ a short/)
    with_variant=True:  "Llama Base ZS (short)" / "Llama Base ZS (full)"  (pro combined/)
    """
    # Pokud je nastaven globální flag, ignoruj parametr (override)
    if _WITH_VARIANT_GLOBAL:
        with_variant = True
    
    if config_name.endswith("_short"):
        base = config_name[:-len("_short")]
        label = PRETTY_LABELS.get(base, config_name)
        return f"{label} (short)" if with_variant else label
    label = PRETTY_LABELS.get(config_name, config_name)
    return f"{label} (full)" if with_variant else label


# Globální flag — když True, pretty() přidá (full)/(short) suffix
_WITH_VARIANT_GLOBAL = False


# Výstupní adresáře
OUTPUT_BASE = SCRIPT_DIR / "eval_outputs"
OUTPUT_FULL = OUTPUT_BASE / "full"
OUTPUT_SHORT = OUTPUT_BASE / "short"
OUTPUT_COMBINED = OUTPUT_BASE / "combined"

# ============================================================================
# DEFINICE POLÍ
# ============================================================================

# Single-label nominální pole
SINGLE_LABEL_NOMINAL = [
    "B1-framing_present",
    "B3-attribution_clarity",
    "C3-conspiracy_pattern",
    "D1-sensitive_domain",
    "M1-language",
    "M2-topic_domain",
]

# Single-label ORDINÁLNÍ pole (zde dává smysl weighted kappa)
SINGLE_LABEL_ORDINAL = {
    "A1-scope_of_missing_context": ["NONE", "LOW", "HIGH"],
    "A3-quantification_present": ["NONE", "PARTIAL", "FULL"],
    "C1-misinterpretation_risk": ["LOW", "MEDIUM", "HIGH"],
    "E1-misleading_header_model_final": [
        "NOT_MISLEADING", "POTENTIALLY_MISLEADING", "MISLEADING"
    ],
    "M3-annotation_confidence": ["LOW", "MEDIUM", "HIGH"],
}

# Multi-label pole
MULTI_LABEL_FIELDS = [
    "A2-scope_of_missing_context_type",
    "B2-framing_type",
]

# Pole, které je v output (z TRAINING_FIELDS) — tj. můžeme pro ně počítat metriky
# Pokud predikce nemá pole (typicky M1, M2, M3 pokud nejsou v output), přeskočíme
TARGET_FIELDS = (
    list(SINGLE_LABEL_ORDINAL.keys())
    + SINGLE_LABEL_NOMINAL
    + MULTI_LABEL_FIELDS
)


# ============================================================================
# NAČÍTÁNÍ DAT
# ============================================================================

def load_predictions(config_name: str, predictions_dir: Path) -> pd.DataFrame:
    """Načte JSONL predikce pro jednu konfiguraci do DataFrame."""
    path = predictions_dir / f"{config_name}.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"Chybí: {path}")
    
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line.strip()))
    
    return pd.DataFrame(rows)


def extract_field_values(df: pd.DataFrame, field: str) -> tuple:
    """
    Vrátí (gold_values, pred_values) pro zadané pole.
    Pro multi-label vrátí list listů.
    Pro chybějící hodnoty (parsing failed) vrátí None.
    """
    gold_vals = []
    pred_vals = []
    
    for _, row in df.iterrows():
        gold = row["gold_annotation"].get(field) if row["gold_annotation"] else None
        
        if row["parsed_output"] and field in row["parsed_output"]:
            pred = row["parsed_output"][field]
        else:
            pred = None
        
        gold_vals.append(gold)
        pred_vals.append(pred)
    
    return gold_vals, pred_vals


# ============================================================================
# METRIKY — SINGLE LABEL
# ============================================================================

def evaluate_single_label(gold: list, pred: list, ordinal_order: list = None) -> dict:
    """
    Spočítá metriky pro single-label pole.
    Pokud ordinal_order, počítá i weighted kappa.
    
    Páry (gold, pred), kde je některý None nebo nevalidní, jsou vyloučeny ze základních metrik.
    """
    # Vyfiltrovat páry, kde má smysl počítat
    valid_pairs = [
        (g, p) for g, p in zip(gold, pred)
        if g is not None and p is not None
    ]
    n_valid = len(valid_pairs)
    n_total = len(gold)
    
    if n_valid == 0:
        return {
            "n_total": n_total,
            "n_valid": 0,
            "accuracy": None,
            "f1_macro": None,
            "f1_weighted": None,
            "kappa": None,
            "kappa_weighted_quadratic": None,
        }
    
    g_valid = [g for g, _ in valid_pairs]
    p_valid = [p for _, p in valid_pairs]
    
    metrics = {
        "n_total": n_total,
        "n_valid": n_valid,
        "accuracy": accuracy_score(g_valid, p_valid),
        "f1_macro": f1_score(g_valid, p_valid, average="macro", zero_division=0),
        "f1_weighted": f1_score(g_valid, p_valid, average="weighted", zero_division=0),
        "kappa": cohen_kappa_score(g_valid, p_valid),
    }
    
    # Weighted kappa (jen pro ordinální pole)
    if ordinal_order:
        try:
            label_to_int = {lbl: i for i, lbl in enumerate(ordinal_order)}
            # Vyfiltrovat páry, kde obě hodnoty jsou v ordinal_order
            ord_pairs = [
                (label_to_int[g], label_to_int[p])
                for g, p in zip(g_valid, p_valid)
                if g in label_to_int and p in label_to_int
            ]
            if ord_pairs:
                g_ord = [g for g, _ in ord_pairs]
                p_ord = [p for _, p in ord_pairs]
                metrics["kappa_weighted_quadratic"] = cohen_kappa_score(
                    g_ord, p_ord, weights="quadratic"
                )
            else:
                metrics["kappa_weighted_quadratic"] = None
        except Exception:
            metrics["kappa_weighted_quadratic"] = None
    else:
        metrics["kappa_weighted_quadratic"] = None
    
    return metrics


def per_class_metrics(gold: list, pred: list, labels: list = None) -> pd.DataFrame:
    """Vrátí DataFrame s precision/recall/F1 pro každou třídu."""
    valid_pairs = [(g, p) for g, p in zip(gold, pred) if g is not None and p is not None]
    if not valid_pairs:
        return pd.DataFrame()
    
    g_valid = [g for g, _ in valid_pairs]
    p_valid = [p for _, p in valid_pairs]
    
    if labels is None:
        labels = sorted(set(g_valid) | set(p_valid))
    
    p, r, f, support = precision_recall_fscore_support(
        g_valid, p_valid, labels=labels, average=None, zero_division=0
    )
    
    return pd.DataFrame({
        "label": labels,
        "precision": p,
        "recall": r,
        "f1": f,
        "support": support,
    })


# ============================================================================
# METRIKY — MULTI LABEL
# ============================================================================

def evaluate_multi_label(gold: list, pred: list) -> dict:
    """
    Spočítá metriky pro multi-label pole.
    Gold a pred jsou listy listů.
    """
    valid_pairs = [
        (g, p) for g, p in zip(gold, pred)
        if g is not None and p is not None and isinstance(g, list) and isinstance(p, list)
    ]
    n_valid = len(valid_pairs)
    n_total = len(gold)
    
    if n_valid == 0:
        return {
            "n_total": n_total,
            "n_valid": 0,
            "jaccard_avg": None,
            "exact_match": None,
            "f1_macro_per_label": None,
            "hamming_loss": None,
            "avg_n_labels_gold": None,
            "avg_n_labels_pred": None,
        }
    
    # Sjednotit množinu všech labelů
    all_labels = set()
    for g, p in valid_pairs:
        all_labels.update(g)
        all_labels.update(p)
    all_labels = sorted(all_labels)
    
    # Převést na binární indikátor matice
    def to_binary(items_list, label_set):
        return [1 if lbl in items_list else 0 for lbl in label_set]
    
    g_binary = np.array([to_binary(g, all_labels) for g, _ in valid_pairs])
    p_binary = np.array([to_binary(p, all_labels) for _, p in valid_pairs])
    
    # Jaccard průměrný (per-sample)
    jaccards = []
    for g, p in valid_pairs:
        g_set, p_set = set(g), set(p)
        if not g_set and not p_set:
            jaccards.append(1.0)
        else:
            jaccards.append(len(g_set & p_set) / len(g_set | p_set))
    
    # Exact match
    exact = sum(1 for g, p in valid_pairs if set(g) == set(p)) / n_valid
    
    # F1 macro per label, pak průměr
    if g_binary.shape[1] > 0:
        f1_per_label = f1_score(g_binary, p_binary, average=None, zero_division=0)
        f1_macro = float(np.mean(f1_per_label))
    else:
        f1_macro = 0.0
    
    # Hamming loss
    h_loss = hamming_loss(g_binary, p_binary) if g_binary.size > 0 else None
    
    # Průměrný počet labelů
    avg_g = float(np.mean([len(g) for g, _ in valid_pairs]))
    avg_p = float(np.mean([len(p) for _, p in valid_pairs]))
    
    return {
        "n_total": n_total,
        "n_valid": n_valid,
        "jaccard_avg": float(np.mean(jaccards)),
        "exact_match": exact,
        "f1_macro_per_label": f1_macro,
        "hamming_loss": h_loss,
        "avg_n_labels_gold": avg_g,
        "avg_n_labels_pred": avg_p,
    }


def per_label_kappa(gold: list, pred: list) -> pd.DataFrame:
    """
    Pro multi-label pole spočítá per-label binární kappa.
    """
    valid_pairs = [
        (g, p) for g, p in zip(gold, pred)
        if g is not None and p is not None and isinstance(g, list) and isinstance(p, list)
    ]
    if not valid_pairs:
        return pd.DataFrame()
    
    all_labels = set()
    for g, p in valid_pairs:
        all_labels.update(g)
        all_labels.update(p)
    all_labels = sorted(all_labels)
    
    rows = []
    for label in all_labels:
        g_bin = [1 if label in g else 0 for g, _ in valid_pairs]
        p_bin = [1 if label in p else 0 for _, p in valid_pairs]
        
        try:
            kappa = cohen_kappa_score(g_bin, p_bin)
        except Exception:
            kappa = None
        
        rows.append({
            "label": label,
            "n_gold": sum(g_bin),
            "n_pred": sum(p_bin),
            "kappa": kappa,
        })
    
    return pd.DataFrame(rows)


# ============================================================================
# CONFUSION MATRIX
# ============================================================================

def plot_confusion_matrix(
    gold: list, pred: list, labels: list, title: str, output_path: Path,
    parsing_status: dict = None,
):
    """Vykreslí confusion matrix jako heatmap PNG."""
    valid_pairs = [(g, p) for g, p in zip(gold, pred) if g is not None and p is not None]
    if not valid_pairs:
        print(f"  ⚠️  {title}: žádné validní páry pro confusion matrix")
        return
    
    g_valid = [g for g, _ in valid_pairs]
    p_valid = [p for _, p in valid_pairs]
    
    cm = confusion_matrix(g_valid, p_valid, labels=labels)
    cm_df = pd.DataFrame(cm, index=labels, columns=labels)
    
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm_df, annot=True, fmt="d", cmap="Blues", cbar=True,
                xticklabels=labels, yticklabels=labels,
                annot_kws={"size": 14}, linewidths=0.5, linecolor='white',
                square=True)
    plt.xlabel("Predikce modelu", fontsize=12)
    plt.ylabel("Gold (anotace)", fontsize=12)
    plt.title(title, fontsize=13, pad=12)
    plt.xticks(rotation=20, ha='right')
    plt.yticks(rotation=0)
    plt.tight_layout()
    # PNG + PDF
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.savefig(str(output_path).replace('.png', '.pdf'), bbox_inches='tight')
    plt.close()




# ============================================================================
# PLOTS — pomocné funkce
# ============================================================================

# Konzistentní barvy pro modely (stejné napříč grafy)
MODEL_COLORS = {
    "llama_base_zs":              "#BFBFBF",  # šedá (nejslabší baseline)
    "llama_base_qlora_zs":        "#2E75B6",  # střední modrá (fine-tuned base)
    "llama_instruct_zs":          "#9DC3E6",  # světlejší modrá
    "llama_instruct_qlora_zs":    "#1F4E79",  # tmavá modrá (fine-tuned instruct)
    "gpt_5_5_zs":                 "#E67E22",  # oranžová (komerční referenční)
}
def model_color(config_name: str) -> str:
    """Barva podle technického názvu (ignoruje _short suffix)."""
    base = config_name.replace("_short", "")
    return MODEL_COLORS.get(base, "#999999")


def _save_fig(fig, output_dir: Path, name: str):
    """Uloží PNG + PDF a zavře figure."""
    fig.savefig(output_dir / f"{name}.png", dpi=300, bbox_inches='tight')
    fig.savefig(output_dir / f"{name}.pdf", bbox_inches='tight')
    plt.close(fig)


# Pretty názvy polí pro titulky a popisky
FIELD_PRETTY = {
    "A1": "A1 — Rozsah chybějícího kontextu",
    "A2": "A2 — Typ chybějícího kontextu",
    "A3": "A3 — Přítomnost kvantifikace",
    "B1": "B1 — Přítomnost framingu",
    "B2": "B2 — Typ framingu",
    "B3": "B3 — Jasnost atribuce",
    "C1": "C1 — Riziko chybné interpretace",
    "C3": "C3 — Konspirační vzor",
    "D1": "D1 — Citlivá doména",
    "E1": "E1 — Finální zavádějícnost",
    "M1": "M1 — Jazyk",
    "M2": "M2 — Tematická doména",
    "M3": "M3 — Anotační jistota",
}

CLASS_COLORS = {
    "NOT_MISLEADING":          "#27AE60",
    "POTENTIALLY_MISLEADING":  "#F39C12",
    "MISLEADING":              "#C0392B",
}


# ============================================================================
# PLOTS — varianta (full nebo short, 5 modelů)
# ============================================================================

def plot_f1_per_field(summary: pd.DataFrame, output_dir: Path):
    """Graf 1: F1 macro per pole — všech 5 modelů, sloupce per pole."""
    fields_order = ['E1', 'A1', 'A3', 'B1', 'B3', 'C1', 'C3', 'D1', 'M3']
    f1_cols = [f'{f}_f1' for f in fields_order if f'{f}_f1' in summary.columns]
    
    # Vyhodit pole, kde mají VŠECHNY modely None (např. M1, M2 — modely je nepředpovídají)
    f1_cols = [c for c in f1_cols if summary[c].notna().any()]
    if not f1_cols:
        return
    
    fig, ax = plt.subplots(figsize=(13, 6.5))
    n_configs = len(summary)
    width = 0.8 / n_configs
    x = np.arange(len(f1_cols))
    
    for i, (_, row) in enumerate(summary.iterrows()):
        offset = (i - n_configs / 2 + 0.5) * width
        values = [row[col] if pd.notna(row[col]) else 0 for col in f1_cols]
        bars = ax.bar(x + offset, values, width,
                      label=pretty(row['config']),
                      color=model_color(row['config']),
                      edgecolor='white', linewidth=0.4)
    
    ax.set_xticks(x)
    ax.set_xticklabels([c.replace('_f1', '') for c in f1_cols], fontsize=11)
    ax.set_ylabel("F1 macro", fontsize=12)
    ax.set_ylim(0, 1.0)
    ax.set_title("F1 macro napříč anotačními poli", fontsize=14, pad=14)
    ax.legend(loc='upper right', fontsize=10, ncol=2)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    _save_fig(fig, output_dir, "01_F1_per_field")


def plot_kappa_per_field(summary: pd.DataFrame, output_dir: Path):
    """Graf 2: Cohen κ per pole."""
    fields_order = ['E1', 'A1', 'A3', 'B1', 'B3', 'C1', 'C3', 'D1', 'M3']
    k_cols = [f'{f}_kappa' for f in fields_order if f'{f}_kappa' in summary.columns]
    k_cols = [c for c in k_cols if summary[c].notna().any()]
    if not k_cols:
        return
    
    fig, ax = plt.subplots(figsize=(13, 6.5))
    n_configs = len(summary)
    width = 0.8 / n_configs
    x = np.arange(len(k_cols))
    
    for i, (_, row) in enumerate(summary.iterrows()):
        offset = (i - n_configs / 2 + 0.5) * width
        values = [row[col] if pd.notna(row[col]) else 0 for col in k_cols]
        ax.bar(x + offset, values, width,
               label=pretty(row['config']),
               color=model_color(row['config']),
               edgecolor='white', linewidth=0.4)
    
    ax.axhline(0, color='black', linewidth=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels([c.replace('_kappa', '') for c in k_cols], fontsize=11)
    ax.set_ylabel("Cohen's κ", fontsize=12)
    
    valid_min = summary[k_cols].min(numeric_only=True).min()
    if pd.isna(valid_min):
        valid_min = 0
    ax.set_ylim(min(-0.1, float(valid_min) - 0.05), 1.0)
    ax.set_title("Cohenova κ napříč anotačními poli", fontsize=14, pad=14)
    ax.legend(loc='upper right', fontsize=10, ncol=2)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    _save_fig(fig, output_dir, "02_kappa_per_field")


def plot_e1_distribution_bias(all_results: list, output_dir: Path):
    """Graf 3: Distribuční bias E1 — Ground Truth + 5 modelů, 3 kategorie."""
    classes = ['NOT_MISLEADING', 'POTENTIALLY_MISLEADING', 'MISLEADING']
    field = 'E1-misleading_header_model_final'
    
    # Ground truth + per model predikce
    gold_dist = None
    pred_dists = []
    
    for res in all_results:
        df = res['df']
        
        # Gold
        gold_vals = [row['gold_annotation'].get(field) if row['gold_annotation'] else None
                     for _, row in df.iterrows()]
        if gold_dist is None:
            gold_counter = Counter(v for v in gold_vals if v is not None)
            total_gold = sum(gold_counter.values())
            gold_dist = {c: gold_counter.get(c, 0) / total_gold for c in classes}
        
        # Pred
        pred_vals = [row['parsed_output'].get(field) if row['parsed_output'] else None
                     for _, row in df.iterrows()]
        valid_preds = [v for v in pred_vals if v in classes]
        pred_counter = Counter(valid_preds)
        total_pred = sum(pred_counter.values())
        pred_dist = {c: pred_counter.get(c, 0) / total_pred if total_pred > 0 else 0 for c in classes}
        pred_dists.append((res['config'], pred_dist))
    
    fig, ax = plt.subplots(figsize=(13, 6.5))
    n_bars = 1 + len(pred_dists)
    width = 0.8 / n_bars
    x = np.arange(len(classes))
    
    # Ground truth (černý)
    gt_values = [gold_dist[c] for c in classes]
    offset = (0 - n_bars / 2 + 0.5) * width
    ax.bar(x + offset, gt_values, width, label='Ground Truth (Realita)',
           color='#1A1A1A', edgecolor='white', linewidth=0.4)
    
    for i, (cfg, dist) in enumerate(pred_dists):
        offset = (i + 1 - n_bars / 2 + 0.5) * width
        values = [dist[c] for c in classes]
        ax.bar(x + offset, values, width, label=pretty(cfg),
               color=model_color(cfg), edgecolor='white', linewidth=0.4)
    
    ax.set_xticks(x)
    ax.set_xticklabels(['NOT_MISLEADING', 'POT_MISLEADING', 'MISLEADING'], fontsize=11)
    ax.set_ylabel("Podíl v datasetu", fontsize=12)
    ax.set_ylim(0, 1.0)
    ax.set_title("Distribuční bias modelů — predikce vs. realita (E1)", fontsize=14, pad=14)
    ax.legend(loc='upper right', fontsize=10, ncol=2)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    _save_fig(fig, output_dir, "03_E1_distribution_bias")


def plot_e1_per_class_metrics(e1_detail: pd.DataFrame, output_dir: Path):
    """Graf 4: E1 per-class — 3 panely (F1, Recall, Precision), v každém 3 třídy × 5 modelů."""
    classes = ['NOT_MISLEADING', 'POTENTIALLY_MISLEADING', 'MISLEADING']
    metrics = [('f1', 'F1'), ('recall', 'Recall'), ('precision', 'Precision')]
    
    fig, axes = plt.subplots(1, 3, figsize=(18, 6.5))
    
    for ax, (mkey, mname) in zip(axes, metrics):
        n_classes = len(classes)
        width = 0.8 / n_classes
        x = np.arange(len(e1_detail))
        
        for i, cls in enumerate(classes):
            col = f'{mkey}_{cls}'
            if col not in e1_detail.columns:
                continue
            offset = (i - n_classes / 2 + 0.5) * width
            values = e1_detail[col].values
            ax.bar(x + offset, values, width, label=cls,
                   color=CLASS_COLORS[cls], edgecolor='white', linewidth=0.4)
        
        ax.set_xticks(x)
        ax.set_xticklabels([pretty(c) for c in e1_detail['config']],
                           rotation=30, ha='right', fontsize=10)
        ax.set_ylabel(mname, fontsize=12)
        ax.set_ylim(0, 1.05)
        ax.set_title(f"E1 — {mname} per třída", fontsize=13, pad=10)
        ax.legend(loc='upper right', fontsize=9)
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        ax.set_axisbelow(True)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
    
    plt.suptitle("Per-class metriky pro pole E1", fontsize=15, y=1.02)
    plt.tight_layout()
    _save_fig(fig, output_dir, "04_E1_per_class_metrics")


def plot_misleading_tradeoff(e1_detail: pd.DataFrame, output_dir: Path):
    """Graf 5: Trade-off precision vs. recall pro třídu MISLEADING (scatter)."""
    if 'precision_MISLEADING' not in e1_detail.columns:
        return
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Diagonála F1=const
    ax.plot([0, 1.05], [0, 1.05], '--', color='#999999', linewidth=1, label='Recall = Precision')
    
    for _, row in e1_detail.iterrows():
        x = row['recall_MISLEADING']
        y = row['precision_MISLEADING']
        cfg = row['config']
        ax.scatter(x, y, s=200, color=model_color(cfg),
                   edgecolor='black', linewidth=1.2, zorder=3)
        ax.annotate(pretty(cfg), (x, y), xytext=(8, 8),
                    textcoords='offset points', fontsize=11)
    
    ax.set_xlabel("Recall (schopnost najít všechny zavádějící)", fontsize=12)
    ax.set_ylabel("Precision (spolehlivost označení 'zavádějící')", fontsize=12)
    ax.set_xlim(0, 1.1)
    ax.set_ylim(0, 1.1)
    ax.set_title("Trade-off: detekce třídy MISLEADING", fontsize=14, pad=14)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    _save_fig(fig, output_dir, "05_MISLEADING_tradeoff")


def plot_multilabel_jaccard(summary: pd.DataFrame, output_dir: Path):
    """Graf 6: Multi-label Jaccard A2+B2 — grouped bar napříč modely."""
    if 'A2_jaccard' not in summary.columns or 'B2_jaccard' not in summary.columns:
        return
    
    fig, ax = plt.subplots(figsize=(11, 6.5))
    width = 0.4
    x = np.arange(len(summary))
    
    a2_values = summary['A2_jaccard'].values
    b2_values = summary['B2_jaccard'].values
    
    ax.bar(x - width/2, a2_values, width, label='A2 (Rozsah chybějícího kontextu)',
           color='#9B59B6', edgecolor='white', linewidth=0.4)
    ax.bar(x + width/2, b2_values, width, label='B2 (Typ rámování)',
           color='#34495E', edgecolor='white', linewidth=0.4)
    
    ax.set_xticks(x)
    ax.set_xticklabels([pretty(c) for c in summary['config']],
                       rotation=30, ha='right', fontsize=10)
    ax.set_ylabel("Jaccard Index (Shoda)", fontsize=12)
    ax.set_ylim(0, 1.0)
    ax.set_title("Výkon v multi-label úlohách (Jaccard Index)", fontsize=14, pad=14)
    ax.legend(loc='upper left', fontsize=10)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    _save_fig(fig, output_dir, "06_multilabel_jaccard")


def plot_multilabel_count(all_results: list, output_dir: Path):
    """Graf 7: Průměrný počet predikovaných labelů A2/B2 vs. realita."""
    a2_field = 'A2-scope_of_missing_context_type'
    b2_field = 'B2-framing_type'
    a2_avg_pred = []
    b2_avg_pred = []
    a2_avg_gold = None
    b2_avg_gold = None
    configs_list = []
    
    for res in all_results:
        df = res['df']
        configs_list.append(res['config'])
        
        a2_lens = []
        b2_lens = []
        a2_gold_lens = []
        b2_gold_lens = []
        for _, row in df.iterrows():
            pred = row['parsed_output'] or {}
            gold = row['gold_annotation'] or {}
            a2_p = pred.get(a2_field) if isinstance(pred.get(a2_field), list) else []
            b2_p = pred.get(b2_field) if isinstance(pred.get(b2_field), list) else []
            a2_g = gold.get(a2_field) if isinstance(gold.get(a2_field), list) else []
            b2_g = gold.get(b2_field) if isinstance(gold.get(b2_field), list) else []
            a2_lens.append(len(a2_p))
            b2_lens.append(len(b2_p))
            a2_gold_lens.append(len(a2_g))
            b2_gold_lens.append(len(b2_g))
        
        a2_avg_pred.append(np.mean(a2_lens) if a2_lens else 0)
        b2_avg_pred.append(np.mean(b2_lens) if b2_lens else 0)
        if a2_avg_gold is None:
            a2_avg_gold = np.mean(a2_gold_lens) if a2_gold_lens else 0
            b2_avg_gold = np.mean(b2_gold_lens) if b2_gold_lens else 0
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    for ax, values, gold_avg, color, title in [
        (axes[0], a2_avg_pred, a2_avg_gold, '#5DADE2', 'A2: Počet predikovaných štítků vs. realita'),
        (axes[1], b2_avg_pred, b2_avg_gold, '#27AE60', 'B2: Počet predikovaných štítků vs. realita'),
    ]:
        x = np.arange(len(configs_list))
        ax.bar(x, values, color=color, edgecolor='white', linewidth=0.4,
               label='Průměrný počet predikcí')
        ax.axhline(gold_avg, color='red', linestyle='--', linewidth=1.8,
                   label=f'Skutečný průměr ({gold_avg:.2f})')
        ax.set_xticks(x)
        ax.set_xticklabels([pretty(c) for c in configs_list],
                           rotation=30, ha='right', fontsize=10)
        ax.set_ylabel("Průměrný počet labelů", fontsize=11)
        ax.set_title(title, fontsize=12, pad=10)
        ax.legend(loc='upper right', fontsize=10)
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        ax.set_axisbelow(True)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
    
    plt.tight_layout()
    _save_fig(fig, output_dir, "07_multilabel_count")


def plot_parsing_rate(summary: pd.DataFrame, output_dir: Path):
    """Graf 8: Parsing success rate."""
    df = summary.copy()
    df['parse_pct'] = df['parse_rate'] * 100
    df = df.sort_values('parse_pct', ascending=True)
    
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh([pretty(c) for c in df['config']], df['parse_pct'],
                    color=[model_color(c) for c in df['config']],
                    edgecolor='white', linewidth=0.5)
    for bar, val in zip(bars, df['parse_pct']):
        ax.text(val + 0.5, bar.get_y() + bar.get_height() / 2,
                f"{val:.1f} %", va='center', fontsize=11)
    ax.set_xlabel("Parsing success rate (%)", fontsize=12)
    ax.set_xlim(0, 105)
    ax.set_title("Úspěšnost parsování JSON výstupu", fontsize=14, pad=14)
    ax.grid(axis='x', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    _save_fig(fig, output_dir, "08_parsing_rate")


def _extract_gold_pred(df: pd.DataFrame, field: str) -> tuple:
    """Z df vytáhne (gold_list, pred_list) pro dané pole."""
    gold = []
    pred = []
    for _, row in df.iterrows():
        g = row['gold_annotation'].get(field) if row['gold_annotation'] else None
        p = row['parsed_output'].get(field) if row['parsed_output'] else None
        gold.append(g)
        pred.append(p)
    return gold, pred


def _compute_recall_fpr(all_results: list) -> pd.DataFrame:
    """Spočítá recall MISLEADING + FPR NOT_MISLEADING pro každý model."""
    field = 'E1-misleading_header_model_final'
    rows = []
    for res in all_results:
        gold, pred = _extract_gold_pred(res['df'], field)
        # Filter: validní predikce
        pairs = [(g, p) for g, p in zip(gold, pred) if p is not None]
        if not pairs:
            rows.append({'config': res['config'], 'recall_MISLEADING': 0, 'FPR_NOT': 0})
            continue
        
        gold_v = np.array([g for g, _ in pairs])
        pred_v = np.array([p for _, p in pairs])
        
        # Recall MISLEADING
        is_mis_gold = (gold_v == 'MISLEADING')
        is_mis_pred = (pred_v == 'MISLEADING')
        tp = (is_mis_gold & is_mis_pred).sum()
        fn = (is_mis_gold & ~is_mis_pred).sum()
        recall_mis = tp / (tp + fn) if (tp + fn) > 0 else 0
        
        # FPR NOT
        is_not_gold = (gold_v == 'NOT_MISLEADING')
        is_not_pred = (pred_v == 'NOT_MISLEADING')
        fp = (is_not_gold & ~is_not_pred).sum()
        tn = (~is_not_gold & ~is_not_pred).sum()
        fpr_not = fp / (fp + tn) if (fp + tn) > 0 else 0
        
        rows.append({
            'config': res['config'],
            'recall_MISLEADING': recall_mis,
            'FPR_NOT': fpr_not,
        })
    return pd.DataFrame(rows)


def plot_recall_fpr(all_results: list, output_dir: Path):
    """Graf 9: Operativní mapa — Recall MIS vs. FPR NOT (scatter)."""
    df = _compute_recall_fpr(all_results)
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    for _, row in df.iterrows():
        x = row['FPR_NOT']
        y = row['recall_MISLEADING']
        cfg = row['config']
        ax.scatter(x, y, s=220, color=model_color(cfg),
                   edgecolor='black', linewidth=1.2, zorder=3)
        ax.annotate(pretty(cfg), (x, y), xytext=(8, 8),
                    textcoords='offset points', fontsize=11)
    
    # Ideální bod (0, 1) — vlevo nahoře
    ax.scatter(0, 1, s=300, marker='*', color='gold',
               edgecolor='black', linewidth=1.2, zorder=4)
    ax.annotate('Ideál', (0, 1), xytext=(10, -5),
                textcoords='offset points', fontsize=12, fontweight='bold')
    
    ax.set_xlabel("FPR pro NOT_MISLEADING (% neutrálních označených za zavádějící)", fontsize=12)
    ax.set_ylabel("Recall pro MISLEADING (% zachycených zavádějících)", fontsize=12)
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.10)
    ax.set_title("Operativní mapa detektoru zavádějících titulků", fontsize=14, pad=14)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    _save_fig(fig, output_dir, "09_recall_fpr_map")


def _compute_extreme_errors(all_results: list) -> pd.DataFrame:
    """Spočítá krajní chyby NOT↔MISLEADING pro každý model."""
    field = 'E1-misleading_header_model_final'
    rows = []
    for res in all_results:
        gold, pred = _extract_gold_pred(res['df'], field)
        pairs = [(g, p) for g, p in zip(gold, pred) if p is not None]
        n_total = len(pairs)
        
        not_to_mis = sum(1 for g, p in pairs if g == 'NOT_MISLEADING' and p == 'MISLEADING')
        mis_to_not = sum(1 for g, p in pairs if g == 'MISLEADING' and p == 'NOT_MISLEADING')
        
        rows.append({
            'config': res['config'],
            'NOT_to_MIS_count': int(not_to_mis),
            'MIS_to_NOT_count': int(mis_to_not),
            'extreme_total': int(not_to_mis + mis_to_not),
            'extreme_rate': (not_to_mis + mis_to_not) / n_total if n_total > 0 else 0,
        })
    return pd.DataFrame(rows)


def plot_extreme_errors(all_results: list, output_dir: Path):
    """Graf 10: Krajní chyby NOT↔MISLEADING."""
    df = _compute_extreme_errors(all_results).sort_values('extreme_total')
    
    fig, ax = plt.subplots(figsize=(11, 6))
    width = 0.4
    x = np.arange(len(df))
    
    ax.barh(x - width/2, df['NOT_to_MIS_count'], width,
            label='Falešný poplach (NOT → MISLEADING)',
            color='#E74C3C', edgecolor='white', linewidth=0.4)
    ax.barh(x + width/2, df['MIS_to_NOT_count'], width,
            label='Přehlédnuté zavádění (MISLEADING → NOT)',
            color='#8E44AD', edgecolor='white', linewidth=0.4)
    
    for i, row in enumerate(df.itertuples()):
        if row.NOT_to_MIS_count > 0:
            ax.text(row.NOT_to_MIS_count + 0.3, i - width/2,
                    str(row.NOT_to_MIS_count), va='center', fontsize=10)
        if row.MIS_to_NOT_count > 0:
            ax.text(row.MIS_to_NOT_count + 0.3, i + width/2,
                    str(row.MIS_to_NOT_count), va='center', fontsize=10)
    
    ax.set_yticks(x)
    ax.set_yticklabels([pretty(c) for c in df['config']], fontsize=11)
    ax.set_xlabel("Počet krajních chyb na test setu", fontsize=12)
    ax.set_title("Krajní chyby — záměna mezi NOT a MISLEADING", fontsize=14, pad=14)
    ax.legend(loc='lower right', fontsize=10)
    ax.grid(axis='x', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    _save_fig(fig, output_dir, "10_extreme_errors")


def _compute_exact_match(all_results: list) -> pd.DataFrame:
    """Multi-label exact match ratio pro A2 a B2."""
    a2_field = 'A2-scope_of_missing_context_type'
    b2_field = 'B2-framing_type'
    rows = []
    for res in all_results:
        df = res['df']
        n = len(df)
        a2_match = 0
        b2_match = 0
        for _, row in df.iterrows():
            pred = row['parsed_output'] or {}
            gold = row['gold_annotation'] or {}
            a2_p = pred.get(a2_field)
            a2_g = gold.get(a2_field)
            b2_p = pred.get(b2_field)
            b2_g = gold.get(b2_field)
            if isinstance(a2_p, list) and isinstance(a2_g, list) and set(a2_p) == set(a2_g):
                a2_match += 1
            if isinstance(b2_p, list) and isinstance(b2_g, list) and set(b2_p) == set(b2_g):
                b2_match += 1
        rows.append({
            'config': res['config'],
            'A2_exact_match': a2_match / n if n > 0 else 0,
            'B2_exact_match': b2_match / n if n > 0 else 0,
        })
    return pd.DataFrame(rows)


def plot_exact_match(all_results: list, output_dir: Path):
    """Graf 11: Multi-label exact match ratio pro A2 a B2."""
    df = _compute_exact_match(all_results)
    
    fig, ax = plt.subplots(figsize=(11, 6))
    width = 0.4
    x = np.arange(len(df))
    
    ax.bar(x - width/2, df['A2_exact_match'], width,
           label='A2 (Rozsah chybějícího kontextu)',
           color='#9B59B6', edgecolor='white', linewidth=0.4)
    ax.bar(x + width/2, df['B2_exact_match'], width,
           label='B2 (Typ rámování)',
           color='#34495E', edgecolor='white', linewidth=0.4)
    
    for i, row in enumerate(df.itertuples()):
        ax.text(i - width/2, row.A2_exact_match + 0.01,
                f"{row.A2_exact_match:.2f}", ha='center', fontsize=9)
        ax.text(i + width/2, row.B2_exact_match + 0.01,
                f"{row.B2_exact_match:.2f}", ha='center', fontsize=9)
    
    ax.set_xticks(x)
    ax.set_xticklabels([pretty(c) for c in df['config']],
                       rotation=30, ha='right', fontsize=10)
    ax.set_ylabel("Exact match ratio", fontsize=12)
    ax.set_ylim(0, 1.0)
    ax.set_title("Multi-label exact match — celá množina labelů přesně shodná s gold", fontsize=14, pad=14)
    ax.legend(loc='upper right', fontsize=10)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    _save_fig(fig, output_dir, "11_multilabel_exact_match")


def generate_variant_plots(summary: pd.DataFrame, e1_detail: pd.DataFrame,
                           ml_detail: pd.DataFrame, all_results: list, output_dir: Path,
                           with_variant: bool = False):
    """Vyrobí všechny grafy pro jednu variantu (full nebo short).
    
    with_variant=True → pretty labels obsahují (full)/(short) suffix (pro combined/).
    """
    global _WITH_VARIANT_GLOBAL
    _WITH_VARIANT_GLOBAL = with_variant
    
    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n  GENERUJI GRAFY → {plots_dir}")
    
    try:
        plot_f1_per_field(summary, plots_dir);              print(f"    ✅ 01_F1_per_field")
        plot_kappa_per_field(summary, plots_dir);           print(f"    ✅ 02_kappa_per_field")
        plot_e1_distribution_bias(all_results, plots_dir);  print(f"    ✅ 03_E1_distribution_bias")
        plot_e1_per_class_metrics(e1_detail, plots_dir);    print(f"    ✅ 04_E1_per_class_metrics")
        plot_misleading_tradeoff(e1_detail, plots_dir);     print(f"    ✅ 05_MISLEADING_tradeoff")
        plot_multilabel_jaccard(summary, plots_dir);        print(f"    ✅ 06_multilabel_jaccard")
        plot_multilabel_count(all_results, plots_dir);      print(f"    ✅ 07_multilabel_count")
        plot_parsing_rate(summary, plots_dir);              print(f"    ✅ 08_parsing_rate")
        plot_recall_fpr(all_results, plots_dir);            print(f"    ✅ 09_recall_fpr_map")
        plot_extreme_errors(all_results, plots_dir);        print(f"    ✅ 10_extreme_errors")
        plot_exact_match(all_results, plots_dir);           print(f"    ✅ 11_multilabel_exact_match")
    finally:
        _WITH_VARIANT_GLOBAL = False  # reset


# ============================================================================
# PLOTS — kombinované (full vs. short, 5 párů)
# ============================================================================

def _strip_short(config_name: str) -> str:
    """Vrátí technický název bez _short suffixu."""
    return config_name.replace("_short", "")


def plot_combined_kappa_e1(full_summary: pd.DataFrame, short_summary: pd.DataFrame, output_dir: Path):
    """Cohen κ pro E1 — krátký vs. plný prompt."""
    full = full_summary.set_index(full_summary['config'].apply(_strip_short))
    short = short_summary.set_index(short_summary['config'].apply(_strip_short))
    common = sorted(set(full.index) & set(short.index),
                    key=lambda c: list(MODEL_COLORS.keys()).index(c) if c in MODEL_COLORS else 999)
    
    fig, ax = plt.subplots(figsize=(12, 6.5))
    width = 0.4
    x = np.arange(len(common))
    
    short_vals = [short.loc[c, 'E1_kappa'] for c in common]
    full_vals = [full.loc[c, 'E1_kappa'] for c in common]
    
    bars1 = ax.bar(x - width/2, short_vals, width, label='Krátký prompt',
                    color='#2ECC71', edgecolor='white', linewidth=0.4)
    bars2 = ax.bar(x + width/2, full_vals, width, label='Dlouhý prompt',
                    color='#F1C40F', edgecolor='white', linewidth=0.4)
    
    for bar, val in zip(bars1, short_vals):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 0.01,
                f"{val:.3f}", ha='center', fontsize=10)
    for bar, val in zip(bars2, full_vals):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 0.01,
                f"{val:.3f}", ha='center', fontsize=10)
    
    ax.set_xticks(x)
    ax.set_xticklabels([PRETTY_LABELS.get(c, c) for c in common],
                       rotation=15, ha='right', fontsize=11)
    ax.set_ylabel("Cohen's κ", fontsize=12)
    ax.set_ylim(min(0, min(short_vals + full_vals) - 0.05), 1.0)
    ax.set_title("Srovnání shody s experty (κ) — krátký vs. dlouhý prompt", fontsize=14, pad=14)
    ax.legend(loc='upper left', fontsize=11)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    _save_fig(fig, output_dir, "C01_kappa_short_vs_full")


def plot_combined_f1_e1(full_summary: pd.DataFrame, short_summary: pd.DataFrame, output_dir: Path):
    """F1 macro pro E1 — krátký vs. plný prompt."""
    full = full_summary.set_index(full_summary['config'].apply(_strip_short))
    short = short_summary.set_index(short_summary['config'].apply(_strip_short))
    common = sorted(set(full.index) & set(short.index),
                    key=lambda c: list(MODEL_COLORS.keys()).index(c) if c in MODEL_COLORS else 999)
    
    fig, ax = plt.subplots(figsize=(12, 6.5))
    width = 0.4
    x = np.arange(len(common))
    
    short_vals = [short.loc[c, 'E1_f1'] for c in common]
    full_vals = [full.loc[c, 'E1_f1'] for c in common]
    
    bars1 = ax.bar(x - width/2, short_vals, width, label='Krátký prompt',
                    color='#2ECC71', edgecolor='white', linewidth=0.4)
    bars2 = ax.bar(x + width/2, full_vals, width, label='Dlouhý prompt',
                    color='#F1C40F', edgecolor='white', linewidth=0.4)
    
    for bar, val in zip(bars1, short_vals):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 0.01,
                f"{val:.3f}", ha='center', fontsize=10)
    for bar, val in zip(bars2, full_vals):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 0.01,
                f"{val:.3f}", ha='center', fontsize=10)
    
    ax.set_xticks(x)
    ax.set_xticklabels([PRETTY_LABELS.get(c, c) for c in common],
                       rotation=15, ha='right', fontsize=11)
    ax.set_ylabel("F1 macro", fontsize=12)
    ax.set_ylim(0, 1.0)
    ax.set_title("Srovnání F1 macro pro E1 — krátký vs. dlouhý prompt", fontsize=14, pad=14)
    ax.legend(loc='upper left', fontsize=11)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    _save_fig(fig, output_dir, "C02_F1_short_vs_full")


def plot_combined_distribution_bias(full_results: list, short_results: list, output_dir: Path):
    """Distribuční bias E1 — všech 10 modelů + Ground Truth."""
    classes = ['NOT_MISLEADING', 'POTENTIALLY_MISLEADING', 'MISLEADING']
    field = 'E1-misleading_header_model_final'
    
    # Ground truth
    df0 = full_results[0]['df']
    gold0, _ = _extract_gold_pred(df0, field)
    gold_counter = Counter(g for g in gold0 if g is not None)
    total_gold = sum(gold_counter.values())
    gt_values = [gold_counter.get(c, 0) / total_gold if total_gold > 0 else 0 for c in classes]
    
    # Predikce per model + varianta
    rows = []
    for res in full_results:
        _, pred = _extract_gold_pred(res['df'], field)
        valid = [p for p in pred if p in classes]
        pc = Counter(valid)
        total = sum(pc.values())
        rows.append((res['config'], 'full',
                     [pc.get(c, 0) / total if total > 0 else 0 for c in classes]))
    for res in short_results:
        _, pred = _extract_gold_pred(res['df'], field)
        valid = [p for p in pred if p in classes]
        pc = Counter(valid)
        total = sum(pc.values())
        rows.append((res['config'], 'short',
                     [pc.get(c, 0) / total if total > 0 else 0 for c in classes]))
    
    fig, ax = plt.subplots(figsize=(15, 7))
    n_total = 1 + len(rows)
    width = 0.85 / n_total
    x = np.arange(len(classes))
    
    offset = (0 - n_total / 2 + 0.5) * width
    ax.bar(x + offset, gt_values, width, label='Ground Truth',
           color='#1A1A1A', edgecolor='white', linewidth=0.3)
    
    for i, (cfg, variant, values) in enumerate(rows):
        offset = (i + 1 - n_total / 2 + 0.5) * width
        color = model_color(cfg)
        hatch = '//' if variant == 'short' else None
        label = f"{pretty(cfg)} ({variant})"
        ax.bar(x + offset, values, width, label=label, color=color,
               edgecolor='white', linewidth=0.3, hatch=hatch)
    
    ax.set_xticks(x)
    ax.set_xticklabels(['NOT_MISLEADING', 'POT_MISLEADING', 'MISLEADING'], fontsize=11)
    ax.set_ylabel("Podíl predikcí", fontsize=12)
    ax.set_ylim(0, 1.0)
    ax.set_title("Distribuční bias — všechny modely × oba prompty + Ground Truth", fontsize=14, pad=14)
    ax.legend(loc='upper right', fontsize=8, ncol=2)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    _save_fig(fig, output_dir, "C03_distribution_bias_combined")


def plot_combined_delta_per_field(full_summary: pd.DataFrame, short_summary: pd.DataFrame, output_dir: Path):
    """Δ F1 (short − full) per pole — vliv kratšího promptu."""
    full = full_summary.set_index(full_summary['config'].apply(_strip_short))
    short = short_summary.set_index(short_summary['config'].apply(_strip_short))
    common = sorted(set(full.index) & set(short.index),
                    key=lambda c: list(MODEL_COLORS.keys()).index(c) if c in MODEL_COLORS else 999)
    
    fields_order = ['E1', 'A1', 'A3', 'B1', 'B3', 'C1', 'C3', 'D1', 'M3']
    f1_cols = [f'{f}_f1' for f in fields_order if f'{f}_f1' in full.columns and f'{f}_f1' in short.columns]
    # Vyhodit pole, kde mají všechny modely None na jedné z variant
    f1_cols = [c for c in f1_cols
               if any(pd.notna(full.loc[cfg, c]) and pd.notna(short.loc[cfg, c]) for cfg in common)]
    
    fig, ax = plt.subplots(figsize=(13, 6.5))
    n_configs = len(common)
    width = 0.8 / n_configs
    x = np.arange(len(f1_cols))
    
    for i, cfg in enumerate(common):
        offset = (i - n_configs / 2 + 0.5) * width
        deltas = []
        for col in f1_cols:
            sv = short.loc[cfg, col]
            fv = full.loc[cfg, col]
            if pd.notna(sv) and pd.notna(fv):
                deltas.append(sv - fv)
            else:
                deltas.append(0)
        ax.bar(x + offset, deltas, width, label=PRETTY_LABELS.get(cfg, cfg),
               color=MODEL_COLORS.get(cfg, '#999'), edgecolor='white', linewidth=0.4)
    
    ax.axhline(0, color='black', linewidth=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels([c.replace('_f1', '') for c in f1_cols], fontsize=11)
    ax.set_ylabel("Δ F1 macro (krátký − dlouhý)", fontsize=12)
    ax.set_title("Vliv promptu na výkon — Δ F1 macro per pole (short − full)", fontsize=14, pad=14)
    ax.legend(loc='upper right', fontsize=10, ncol=2)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    _save_fig(fig, output_dir, "C04_delta_F1_per_field")


def generate_combined_plots(full_summary, full_e1, full_results,
                            short_summary, short_e1, short_results,
                            output_dir: Path):
    """Vyrobí kombinované grafy (full vs. short) pro celkové srovnání."""
    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n  GENERUJI KOMBINOVANÉ GRAFY → {plots_dir}")
    
    plot_combined_kappa_e1(full_summary, short_summary, plots_dir)
    print(f"    ✅ C01_kappa_short_vs_full")
    plot_combined_f1_e1(full_summary, short_summary, plots_dir)
    print(f"    ✅ C02_F1_short_vs_full")
    plot_combined_distribution_bias(full_results, short_results, plots_dir)
    print(f"    ✅ C03_distribution_bias_combined")
    plot_combined_delta_per_field(full_summary, short_summary, plots_dir)
    print(f"    ✅ C04_delta_F1_per_field")



# ============================================================================
# PARSING STATISTIKY
# ============================================================================

def parsing_stats(df: pd.DataFrame) -> dict:
    """Spočítá parsing success rate."""
    statuses = df["parsing_status"].value_counts().to_dict()
    n_total = len(df)
    
    n_ok = sum(v for k, v in statuses.items() if k.startswith("ok"))
    
    return {
        "n_total": n_total,
        "n_parsed_ok": n_ok,
        "parse_rate": n_ok / n_total if n_total > 0 else 0,
        "by_status": statuses,
    }


# ============================================================================
# HLAVNÍ EVALUACE
# ============================================================================

def evaluate_config(config_name: str, predictions_dir: Path, cm_dir: Path) -> dict:
    """Plná evaluace jedné konfigurace."""
    print(f"\n{'='*60}")
    print(f"  KONFIGURACE: {config_name}")
    print(f"{'='*60}")
    
    df = load_predictions(config_name, predictions_dir)
    
    # Parsing stats
    pstats = parsing_stats(df)
    print(f"  Parsing: {pstats['n_parsed_ok']}/{pstats['n_total']} "
          f"({pstats['parse_rate']*100:.1f}%)")
    
    results = {
        "config": config_name,
        "parsing": pstats,
        "fields": {},
        "df": df,
    }
    
    # Vyhodnotit všechna pole
    for field in TARGET_FIELDS:
        gold, pred = extract_field_values(df, field)
        
        if field in MULTI_LABEL_FIELDS:
            metrics = evaluate_multi_label(gold, pred)
            results["fields"][field] = {
                "type": "multi_label",
                "metrics": metrics,
                "per_label": per_label_kappa(gold, pred).to_dict(orient="records"),
            }
            print(f"  [{field}]")
            print(f"     Jaccard avg: {metrics['jaccard_avg']:.3f}" if metrics['jaccard_avg'] else "     Jaccard: N/A")
            print(f"     F1 per-label avg: {metrics['f1_macro_per_label']:.3f}" if metrics.get('f1_macro_per_label') else "")
        else:
            ordinal = SINGLE_LABEL_ORDINAL.get(field)
            metrics = evaluate_single_label(gold, pred, ordinal_order=ordinal)
            results["fields"][field] = {
                "type": "ordinal" if ordinal else "nominal",
                "metrics": metrics,
                "per_class": per_class_metrics(gold, pred, ordinal).to_dict(orient="records") if ordinal else per_class_metrics(gold, pred).to_dict(orient="records"),
            }
            print(f"  [{field}]")
            if metrics["accuracy"] is not None:
                print(f"     Acc: {metrics['accuracy']:.3f}, "
                      f"F1 macro: {metrics['f1_macro']:.3f}, "
                      f"κ: {metrics['kappa']:.3f}", end="")
                if metrics["kappa_weighted_quadratic"] is not None:
                    print(f", κw: {metrics['kappa_weighted_quadratic']:.3f}", end="")
                print()
            else:
                print(f"     Bez dat (n_valid=0)")
        
        # Confusion matrix pro E1 (hlavní pole)
        if field == "E1-misleading_header_model_final":
            plot_confusion_matrix(
                gold, pred,
                labels=SINGLE_LABEL_ORDINAL[field],
                title=f"Confusion Matrix — {config_name}\n{field}",
                output_path=cm_dir / f"{config_name}_E1.png",
            )
    
    return results


# ============================================================================
# SOUHRNNÉ TABULKY
# ============================================================================

def build_summary_table(all_results: list) -> pd.DataFrame:
    """Souhrnná tabulka — řádek = konfigurace, sloupec = pole F1."""
    rows = []
    for res in all_results:
        row = {
            "config": res["config"],
            "parse_rate": res["parsing"]["parse_rate"],
        }
        for field, fdata in res["fields"].items():
            metrics = fdata["metrics"]
            short_name = field.split("-")[0]  # E1, A1, ...
            
            if fdata["type"] == "multi_label":
                row[f"{short_name}_jaccard"] = metrics.get("jaccard_avg")
                row[f"{short_name}_f1"] = metrics.get("f1_macro_per_label")
            else:
                row[f"{short_name}_f1"] = metrics.get("f1_macro")
                row[f"{short_name}_kappa"] = metrics.get("kappa")
        rows.append(row)
    
    return pd.DataFrame(rows)


def build_e1_detail_table(all_results: list) -> pd.DataFrame:
    """Detailní tabulka pro E1 napříč konfiguracemi."""
    rows = []
    for res in all_results:
        e1 = res["fields"].get("E1-misleading_header_model_final")
        if not e1:
            continue
        m = e1["metrics"]
        row = {
            "config": res["config"],
            "n_valid": m["n_valid"],
            "accuracy": m["accuracy"],
            "f1_macro": m["f1_macro"],
            "f1_weighted": m["f1_weighted"],
            "kappa": m["kappa"],
            "kappa_weighted": m["kappa_weighted_quadratic"],
        }
        # Per-class F1
        for cls in e1["per_class"]:
            label = cls["label"]
            row[f"f1_{label}"] = cls["f1"]
            row[f"recall_{label}"] = cls["recall"]
            row[f"precision_{label}"] = cls["precision"]
        rows.append(row)
    
    return pd.DataFrame(rows)


def build_multilabel_detail_table(all_results: list) -> pd.DataFrame:
    """Detailní tabulka pro multi-label pole."""
    rows = []
    for res in all_results:
        for field in MULTI_LABEL_FIELDS:
            fdata = res["fields"].get(field)
            if not fdata:
                continue
            m = fdata["metrics"]
            rows.append({
                "config": res["config"],
                "field": field,
                "n_valid": m["n_valid"],
                "jaccard_avg": m["jaccard_avg"],
                "f1_macro": m["f1_macro_per_label"],
                "exact_match": m["exact_match"],
                "hamming_loss": m["hamming_loss"],
                "avg_n_gold": m["avg_n_labels_gold"],
                "avg_n_pred": m["avg_n_labels_pred"],
            })
    return pd.DataFrame(rows)


# ============================================================================
# MARKDOWN REPORT
# ============================================================================

def generate_markdown_report(all_results: list, output_path: Path):
    """Vygeneruje markdown report pro BP."""
    lines = ["# Evaluation report\n"]
    
    lines.append("## Souhrn\n")
    lines.append("| Konfigurace | Parsing | E1 F1 macro | E1 kappa | E1 kappa weighted |")
    lines.append("|---|---|---|---|---|")
    for res in all_results:
        e1 = res["fields"].get("E1-misleading_header_model_final", {})
        m = e1.get("metrics", {})
        lines.append(
            f"| {res['config']} "
            f"| {res['parsing']['parse_rate']*100:.1f}% "
            f"| {m.get('f1_macro', 0):.3f} "
            f"| {m.get('kappa', 0):.3f} "
            f"| {m.get('kappa_weighted_quadratic', 0):.3f} |"
        )
    
    lines.append("\n## Per-pole F1 macro\n")
    fields_short = [f.split("-")[0] for f in TARGET_FIELDS]
    lines.append("| Konfigurace | " + " | ".join(fields_short) + " |")
    lines.append("|---|" + "|".join(["---"] * len(fields_short)) + "|")
    for res in all_results:
        row_vals = [res["config"]]
        for field in TARGET_FIELDS:
            fdata = res["fields"].get(field, {})
            metrics = fdata.get("metrics", {})
            if fdata.get("type") == "multi_label":
                v = metrics.get("f1_macro_per_label")
            else:
                v = metrics.get("f1_macro")
            row_vals.append(f"{v:.3f}" if v is not None else "—")
        lines.append("| " + " | ".join(row_vals) + " |")
    
    lines.append("\n## E1 detail (hlavní pole)\n")
    for res in all_results:
        e1 = res["fields"].get("E1-misleading_header_model_final", {})
        if not e1:
            continue
        m = e1["metrics"]
        lines.append(f"### {res['config']}")
        lines.append(f"- Validních predikcí: {m['n_valid']}/{m['n_total']}")
        lines.append(f"- Accuracy: {m['accuracy']:.3f}")
        lines.append(f"- F1 macro: {m['f1_macro']:.3f}")
        lines.append(f"- F1 weighted: {m['f1_weighted']:.3f}")
        lines.append(f"- Cohen's kappa: {m['kappa']:.3f}")
        if m.get("kappa_weighted_quadratic"):
            lines.append(f"- Cohen's kappa (weighted quadratic): {m['kappa_weighted_quadratic']:.3f}")
        lines.append("\n**Per-class:**")
        lines.append("| Třída | Precision | Recall | F1 | Support |")
        lines.append("|---|---|---|---|---|")
        for cls in e1["per_class"]:
            lines.append(
                f"| {cls['label']} | {cls['precision']:.3f} | "
                f"{cls['recall']:.3f} | {cls['f1']:.3f} | {cls['support']} |"
            )
        lines.append("")
    
    output_path.write_text("\n".join(lines), encoding="utf-8")


# ============================================================================
# MAIN
# ============================================================================

def process_variant(variant_name: str, predictions_dir: Path,
                    configs: list, output_dir: Path) -> tuple:
    """Zpracuje jednu variantu (full nebo short) — CSV, MD, confusion matrices, grafy.
    
    Returns:
        (summary_df, e1_detail_df, ml_detail_df, all_results) nebo None pokud nic neexistuje
    """
    if not predictions_dir.exists():
        print(f"⚠️  {predictions_dir} neexistuje — varianta {variant_name} přeskočena")
        return None
    
    output_dir.mkdir(parents=True, exist_ok=True)
    cm_dir = output_dir / "confusion_matrices"
    cm_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'#'*60}")
    print(f"# VARIANTA: {variant_name.upper()}")
    print(f"# Predikce: {predictions_dir}")
    print(f"# Výstupy:  {output_dir}")
    print(f"{'#'*60}")
    
    # Evaluace všech konfigurací
    all_results = []
    for config in configs:
        try:
            res = evaluate_config(config, predictions_dir, cm_dir)
            all_results.append(res)
        except FileNotFoundError as e:
            print(f"⚠️  {e}")
            continue
    
    if not all_results:
        print(f"❌ Žádné predikce v {predictions_dir}")
        return None
    
    # Souhrnné tabulky
    print(f"\n  GENERUJI TABULKY")
    summary = build_summary_table(all_results)
    summary.to_csv(output_dir / "eval_summary.csv", index=False)
    print(f"  ✅ eval_summary.csv ({len(summary)} řádků, {len(summary.columns)} sloupců)")
    
    e1_detail = build_e1_detail_table(all_results)
    e1_detail.to_csv(output_dir / "eval_e1_detail.csv", index=False)
    print(f"  ✅ eval_e1_detail.csv")
    
    ml_detail = build_multilabel_detail_table(all_results)
    ml_detail.to_csv(output_dir / "eval_multilabel.csv", index=False)
    print(f"  ✅ eval_multilabel.csv")
    
    # Markdown report
    generate_markdown_report(all_results, output_dir / "eval_report.md")
    print(f"  ✅ eval_report.md")
    
    # Grafy
    generate_variant_plots(summary, e1_detail, ml_detail, all_results, output_dir)
    
    return (summary, e1_detail, ml_detail, all_results)


def main():
    OUTPUT_BASE.mkdir(parents=True, exist_ok=True)
    
    print(f"=== EVALUATION ===")
    print(f"Working directory: {SCRIPT_DIR}")
    
    # Zpracuj obě varianty samostatně
    full_data = process_variant("full", PREDICTIONS_FULL, CONFIGS_FULL, OUTPUT_FULL)
    short_data = process_variant("short", PREDICTIONS_SHORT, CONFIGS_SHORT, OUTPUT_SHORT)
    
    # COMBINED — všech 10 modelů v jedné složce
    if full_data and short_data:
        print(f"\n{'#'*60}")
        print(f"# VARIANTA: COMBINED (full + short, 10 modelů)")
        print(f"# Výstupy: {OUTPUT_COMBINED}")
        print(f"{'#'*60}")
        
        OUTPUT_COMBINED.mkdir(parents=True, exist_ok=True)
        cm_dir_combined = OUTPUT_COMBINED / "confusion_matrices"
        cm_dir_combined.mkdir(parents=True, exist_ok=True)
        
        # Spojit all_results z obou variant + překopírovat confusion matrices
        full_results = full_data[3]
        short_results = short_data[3]
        all_combined = full_results + short_results
        
        # Confusion matrices — překopírovat z full/ a short/ do combined/
        import shutil
        for src_dir in [OUTPUT_FULL / "confusion_matrices", OUTPUT_SHORT / "confusion_matrices"]:
            if src_dir.exists():
                for f in src_dir.iterdir():
                    if f.is_file():
                        shutil.copy(f, cm_dir_combined / f.name)
        print(f"  ✅ confusion_matrices/ ({len(list(cm_dir_combined.iterdir()))} souborů)")
        
        # Tabulky — všech 10 modelů
        print(f"\n  GENERUJI TABULKY (10 modelů)")
        summary_c = build_summary_table(all_combined)
        summary_c.to_csv(OUTPUT_COMBINED / "eval_summary.csv", index=False)
        print(f"  ✅ eval_summary.csv ({len(summary_c)} řádků)")
        
        e1_detail_c = build_e1_detail_table(all_combined)
        e1_detail_c.to_csv(OUTPUT_COMBINED / "eval_e1_detail.csv", index=False)
        print(f"  ✅ eval_e1_detail.csv")
        
        ml_detail_c = build_multilabel_detail_table(all_combined)
        ml_detail_c.to_csv(OUTPUT_COMBINED / "eval_multilabel.csv", index=False)
        print(f"  ✅ eval_multilabel.csv")
        
        generate_markdown_report(all_combined, OUTPUT_COMBINED / "eval_report.md")
        print(f"  ✅ eval_report.md")
        
        # Grafy — speciální srovnávací (4) + nově i základní (11) pro 10 modelů
        generate_combined_plots(
            full_summary=full_data[0], full_e1=full_data[1], full_results=full_results,
            short_summary=short_data[0], short_e1=short_data[1], short_results=short_results,
            output_dir=OUTPUT_COMBINED
        )
        # Plus základní sada grafů aplikovaná na 10 modelů dohromady
        generate_variant_plots(summary_c, e1_detail_c, ml_detail_c, all_combined,
                               OUTPUT_COMBINED, with_variant=True)
    
    # Závěrečné info
    print(f"\n{'='*60}")
    print(f"  HOTOVO")
    print(f"{'='*60}")
    print(f"\nVšechny výstupy v: {OUTPUT_BASE}")
    print(f"  ├── full/     → vše pro 5 plných modelů (CSV, MD, conf. matrices, grafy)")
    print(f"  ├── short/    → vše pro 5 krátkých modelů")
    print(f"  └── combined/ → vše pro 10 modelů + srovnávací grafy full vs. short")


if __name__ == "__main__":
    main()