"""
Dataset split — Label Studio JSON → train/val/test sety pro fine-tuning.

Workflow:
  1. Parse Label Studio JSON
  2. Validate (povinná pole, enum hodnoty)
  3. Deduplikace (podle header, podle id)
  4. Filtr: jen M1-language == "CS"
  5. Stratified split 70/10/20 podle E1 + M2
  6. Generate output files:
     - jsonl/  raw + instruction-format pro fine-tuning
     - csv/    train/val/test ve formátu input CSV (jen original cols)
"""
import json
import random
from pathlib import Path
import pandas as pd
from sklearn.model_selection import train_test_split

# ============================================================================
# KONFIGURACE
# ============================================================================
SCRIPT_DIR = Path(__file__).resolve().parent

INPUT_JSON = SCRIPT_DIR / "gold_standard_label_studio_400.json"
OUTPUT_DIR = SCRIPT_DIR / "splits"

# Split poměry
TRAIN_RATIO = 0.70
VAL_RATIO = 0.10
TEST_RATIO = 0.20

SEED = 42

# Pole pro fine-tuning output (Sekce I, 10 polí — bez C2, M1, M2, M3)
TRAINING_FIELDS = [
    "A1-scope_of_missing_context",
    "A2-scope_of_missing_context_type",
    "A3-quantification_present",
    "B1-framing_present",
    "B2-framing_type",
    "B3-attribution_clarity",
    "C1-misinterpretation_risk",
    "C3-conspiracy_pattern",
    "D1-sensitive_domain",
    "E1-misleading_header_model_final",
]

# Pole, která chceme zachovat v raw JSONL (kompletní anotace)
ALL_ANNOTATION_FIELDS = TRAINING_FIELDS + [
    "C2-likely_misinterpretation",
    "M1-language",
    "M2-topic_domain",
    "M3-annotation_confidence",
]

# Multi-label pole (vrací list, ne string)
MULTILABEL_FIELDS = {
    "A2-scope_of_missing_context_type",
    "B2-framing_type",
}

# Volnotextová pole (TextArea)
TEXTAREA_FIELDS = {"C2-likely_misinterpretation"}

# Povolené enum hodnoty pro validaci
ENUMS = {
    "A1-scope_of_missing_context": {"NONE", "LOW", "HIGH"},
    "A2-scope_of_missing_context_type": {
        "MOTIVATION", "CAUSALITY", "SCOPE", "TIMEFRAME", "PROCESS_STAGE",
        "UNCERTAINTY_LEVEL", "STATISTICAL_BASELINE", "RELEVANCE_OF_ATTRIBUTE",
        "NEGATIVE_SPACE",
    },
    "A3-quantification_present": {"FULL", "PARTIAL", "NONE"},
    "B1-framing_present": {"YES", "NO"},
    "B2-framing_type": {
        "IDENTITY_HIGHLIGHTING", "EMOTIONAL_LANGUAGE", "ABSOLUTE_CLAIMS",
        "CAUSAL_SHORTCUT", "SELECTIVE_FACTS", "CLICKBAIT_STYLE",
        "MULTIPLE_MEANING", "ATTRIBUTED_CLAIM", "PRESUPPOSITION",
        "DEHUMANIZATION", "APOCALYPTIC",
    },
    "B3-attribution_clarity": {"CLEAR", "VAGUE", "MISSING", "SPLIT"},
    "C1-misinterpretation_risk": {"LOW", "MEDIUM", "HIGH"},
    "C3-conspiracy_pattern": {"NONE", "SYMBOL", "NARRATIVE", "FALSE_ATTRIBUTION"},
    "D1-sensitive_domain": {"NONE", "HEALTH", "SECURITY", "FINANCE",
                             "IDENTITY", "POLITICS", "OTHER"},
    "E1-misleading_header_model_final": {
        "NOT_MISLEADING", "POTENTIALLY_MISLEADING", "MISLEADING"
    },
    "M1-language": {"CS", "EN", "SK"},
    "M2-topic_domain": {"POLITICS", "CRIME", "HEALTH", "ECONOMY", "SOCIETY",
                         "SPORT", "CULTURE", "TECH", "OTHER"},
    "M3-annotation_confidence": {"HIGH", "MEDIUM", "LOW"},
}

# Originální vstupní sloupce (pro CSV výstup)
INPUT_CSV_COLUMNS = ["id", "url", "source", "published", "pre-label", "header"]


# ============================================================================
# SYSTEM PROMPT (pro instruction-format)
# ============================================================================
SYSTEM_PROMPT = """Jsi expert na analýzu zpravodajských sdělení. Tvým úkolem je vyhodnotit \
česky psaný titulek a posoudit jeho zavádějícnost podle definovaného schématu.

Vyplníš pole v pořadí A → B → C → D → E. Až po vyhodnocení bloků A-D rozhodneš o E1.

Vrať pouze validní JSON s následujícími poli (žádný text před ani po):
- A1-scope_of_missing_context: NONE / LOW / HIGH
- A2-scope_of_missing_context_type: array of MOTIVATION / CAUSALITY / SCOPE / TIMEFRAME / PROCESS_STAGE / UNCERTAINTY_LEVEL / STATISTICAL_BASELINE / RELEVANCE_OF_ATTRIBUTE / NEGATIVE_SPACE (prázdné [] pokud A1=NONE)
- A3-quantification_present: FULL / PARTIAL / NONE
- B1-framing_present: YES / NO
- B2-framing_type: array of IDENTITY_HIGHLIGHTING / EMOTIONAL_LANGUAGE / ABSOLUTE_CLAIMS / CAUSAL_SHORTCUT / SELECTIVE_FACTS / CLICKBAIT_STYLE / MULTIPLE_MEANING / ATTRIBUTED_CLAIM / PRESUPPOSITION / DEHUMANIZATION / APOCALYPTIC (prázdné [] pokud B1=NO)
- B3-attribution_clarity: CLEAR / VAGUE / MISSING / SPLIT
- C1-misinterpretation_risk: LOW / MEDIUM / HIGH
- C3-conspiracy_pattern: NONE / SYMBOL / NARRATIVE / FALSE_ATTRIBUTION
- D1-sensitive_domain: NONE / HEALTH / SECURITY / FINANCE / IDENTITY / POLITICS / OTHER
- E1-misleading_header_model_final: NOT_MISLEADING / POTENTIALLY_MISLEADING / MISLEADING"""


# ============================================================================
# PARSING
# ============================================================================

def parse_label_studio_export(path: Path) -> list[dict]:
    """
    Vrátí list záznamů. Každý záznam:
        {
            "id": str,
            "header": str,
            "url": str,
            "source": str,
            "published": str,
            "pre-label": str,
            "annotation": { "A1-...": ..., "B1-...": ..., ... }
        }
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    records = []
    skipped_no_annotation = 0
    
    for record in data:
        record_id = record["data"].get("id")
        annotations = record.get("annotations", [])
        if not annotations:
            skipped_no_annotation += 1
            continue
        
        # Vytáhnout všechny anotační hodnoty
        annotation = {}
        for r in annotations[0].get("result", []):
            field_name = r.get("from_name")
            value = r.get("value", {})
            
            if field_name in MULTILABEL_FIELDS:
                annotation[field_name] = value.get("choices", [])
            elif field_name in TEXTAREA_FIELDS:
                # TextArea vrací list of strings
                texts = value.get("text", [])
                annotation[field_name] = texts[0] if texts else ""
            else:
                # Single-choice
                choices = value.get("choices", [])
                annotation[field_name] = choices[0] if choices else None
        
        # Default hodnoty pro pole, která mohou chybět (podmíněná, nepovinná)
        for field in ALL_ANNOTATION_FIELDS:
            if field not in annotation:
                if field in MULTILABEL_FIELDS:
                    annotation[field] = []
                elif field in TEXTAREA_FIELDS:
                    annotation[field] = ""
                else:
                    annotation[field] = None
        
        records.append({
            "id": record_id,
            "header": record["data"].get("header", ""),
            "url": record["data"].get("url", ""),
            "source": record["data"].get("source", ""),
            "published": record["data"].get("published", ""),
            "pre-label": record["data"].get("pre-label", ""),
            "annotation": annotation,
        })
    
    if skipped_no_annotation > 0:
        print(f"  ℹ️  Přeskočeno {skipped_no_annotation} záznamů bez anotace")
    
    return records


# ============================================================================
# VALIDACE
# ============================================================================

def validate_records(records: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Validuje záznamy proti enum hodnotám a povinným polím.
    Vrací: (valid_records, invalid_records_with_errors)
    """
    valid = []
    invalid = []
    
    for rec in records:
        errors = []
        ann = rec["annotation"]
        
        # 1. Single-choice required fields
        single_required = [
            "A1-scope_of_missing_context", "A3-quantification_present",
            "B1-framing_present", "B3-attribution_clarity",
            "C1-misinterpretation_risk", "C3-conspiracy_pattern",
            "D1-sensitive_domain", "E1-misleading_header_model_final",
            "M1-language", "M2-topic_domain", "M3-annotation_confidence",
        ]
        for field in single_required:
            val = ann.get(field)
            if val is None:
                errors.append(f"chybí {field}")
            elif val not in ENUMS[field]:
                errors.append(f"{field}={val!r} není v enum")
        
        # 2. Multi-label fields — všechny prvky v enum
        for field in MULTILABEL_FIELDS:
            vals = ann.get(field, [])
            if not isinstance(vals, list):
                errors.append(f"{field} není list")
                continue
            for v in vals:
                if v not in ENUMS[field]:
                    errors.append(f"{field}: {v!r} není v enum")
        
        # 3. Konzistence podmíněných polí
        if ann.get("A1-scope_of_missing_context") == "NONE":
            if ann.get("A2-scope_of_missing_context_type"):
                errors.append("A1=NONE ale A2 není prázdné")
        
        if ann.get("B1-framing_present") == "NO":
            if ann.get("B2-framing_type"):
                errors.append("B1=NO ale B2 není prázdné")
        
        if errors:
            invalid.append({"id": rec["id"], "errors": errors})
        else:
            valid.append(rec)
    
    return valid, invalid


# ============================================================================
# DEDUPLIKACE
# ============================================================================

def deduplicate(records: list[dict]) -> tuple[list[dict], int, int]:
    """
    Deduplikace nejdřív podle id, pak podle header.
    Vrací: (unique_records, dup_id_count, dup_header_count)
    """
    # Dedup podle id
    seen_ids = set()
    after_id = []
    dup_id_count = 0
    for rec in records:
        if rec["id"] in seen_ids:
            dup_id_count += 1
            continue
        seen_ids.add(rec["id"])
        after_id.append(rec)
    
    # Dedup podle header (case-insensitive, trim)
    seen_headers = set()
    after_header = []
    dup_header_count = 0
    for rec in after_id:
        normalized = rec["header"].strip().lower()
        if normalized in seen_headers:
            dup_header_count += 1
            continue
        seen_headers.add(normalized)
        after_header.append(rec)
    
    return after_header, dup_id_count, dup_header_count


# ============================================================================
# FILTR JAZYKA
# ============================================================================

def filter_language(records: list[dict], lang: str = "CS") -> tuple[list[dict], int]:
    """Vrátí jen záznamy s M1-language == lang."""
    filtered = [r for r in records if r["annotation"].get("M1-language") == lang]
    excluded = len(records) - len(filtered)
    return filtered, excluded


# ============================================================================
# STRATIFIED SPLIT
# ============================================================================

def stratified_split(records: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    """
    Stratifikuje podle E1 (primárně) a M2 (sekundárně, kombinovaný strata key).
    Vrací: (train, val, test) — celkem ~70/10/20.
    """
    # Vytvořit kombinovaný strata key
    df = pd.DataFrame(records)
    df["_strata"] = df.apply(
        lambda r: f"{r['annotation']['E1-misleading_header_model_final']}_"
                  f"{r['annotation']['M2-topic_domain']}",
        axis=1
    )
    
    # Některé E1×M2 kombinace mohou mít jen 1-2 záznamy → stratifikace pak selže
    # Spočítat nejmenší stratu — pokud < 3, fallback na stratifikaci jen podle E1
    strata_counts = df["_strata"].value_counts()
    min_strata = strata_counts.min()
    
    if min_strata < 3:
        print(f"  ℹ️  Některé E1×M2 kombinace mají < 3 záznamy "
              f"(min={min_strata}). Fallback: stratifikace jen podle E1.")
        df["_strata"] = df.apply(
            lambda r: r["annotation"]["E1-misleading_header_model_final"],
            axis=1
        )
    
    # First split: train+val vs test (test = TEST_RATIO)
    train_val_df, test_df = train_test_split(
        df,
        test_size=TEST_RATIO,
        stratify=df["_strata"],
        random_state=SEED,
    )
    
    # Second split: train vs val
    # Z train_val (=80% celku) vyrobit val tak, aby val=10% celku → val_size = 10/80
    val_relative = VAL_RATIO / (TRAIN_RATIO + VAL_RATIO)
    train_df, val_df = train_test_split(
        train_val_df,
        test_size=val_relative,
        stratify=train_val_df["_strata"],
        random_state=SEED,
    )
    
    # Drop strata column, zpět na list dictů
    train = train_df.drop(columns=["_strata"]).to_dict("records")
    val = val_df.drop(columns=["_strata"]).to_dict("records")
    test = test_df.drop(columns=["_strata"]).to_dict("records")
    
    return train, val, test


# ============================================================================
# OUTPUT WRITERS
# ============================================================================

def write_raw_jsonl(records: list[dict], path: Path, split_name: str):
    """Raw JSONL — kompletní anotace včetně metadat."""
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            out = {
                "id": rec["id"],
                "header": rec["header"],
                "split": split_name,
                "annotation": rec["annotation"],
                "metadata": {
                    "url": rec["url"],
                    "source": rec["source"],
                    "published": rec["published"],
                    "pre-label": rec["pre-label"],
                },
            }
            f.write(json.dumps(out, ensure_ascii=False) + "\n")


def write_instruction_jsonl(records: list[dict], path: Path):
    """Instruction-format JSONL — pro fine-tuning. Output obsahuje jen TRAINING_FIELDS."""
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            # Output: jen pole pro trénink, v deterministickém pořadí
            output_obj = {
                field: rec["annotation"].get(field) for field in TRAINING_FIELDS
            }
            
            example = {
                "instruction": SYSTEM_PROMPT,
                "input": f'Titulek: "{rec["header"]}"',
                "output": json.dumps(output_obj, ensure_ascii=False),
            }
            f.write(json.dumps(example, ensure_ascii=False) + "\n")


def write_csv(records: list[dict], path: Path):
    """CSV ve formátu původního input CSV (jen INPUT_CSV_COLUMNS)."""
    rows = [{col: rec.get(col, "") for col in INPUT_CSV_COLUMNS} for rec in records]
    df = pd.DataFrame(rows, columns=INPUT_CSV_COLUMNS)
    df.to_csv(path, index=False, encoding="utf-8")


# ============================================================================
# STATS
# ============================================================================

def compute_stats(train, val, test):
    """Spočítá distribuci E1 napříč splity."""
    stats = {}
    for name, recs in [("train", train), ("val", val), ("test", test)]:
        e1_counts = {}
        m2_counts = {}
        for r in recs:
            e1 = r["annotation"]["E1-misleading_header_model_final"]
            m2 = r["annotation"]["M2-topic_domain"]
            e1_counts[e1] = e1_counts.get(e1, 0) + 1
            m2_counts[m2] = m2_counts.get(m2, 0) + 1
        stats[name] = {
            "total": len(recs),
            "by_E1": dict(sorted(e1_counts.items())),
            "by_M2": dict(sorted(m2_counts.items())),
        }
    return stats


# ============================================================================
# MAIN
# ============================================================================

def main():
    random.seed(SEED)
    
    print(f"=== DATASET SPLIT ===\n")
    print(f"Vstup: {INPUT_JSON.name}")
    
    # 1. Parse
    print(f"\n[1/6] Parsuji Label Studio JSON...")
    records = parse_label_studio_export(INPUT_JSON)
    print(f"      Načteno: {len(records)} záznamů")
    
    # 2. Validace
    print(f"\n[2/6] Validace...")
    valid, invalid = validate_records(records)
    print(f"      Validní: {len(valid)}, neplatné: {len(invalid)}")
    if invalid:
        print(f"      ⚠️  Záznamy s chybami:")
        for inv in invalid[:5]:
            print(f"         - {inv['id']}: {', '.join(inv['errors'][:3])}")
        if len(invalid) > 5:
            print(f"         ... a dalších {len(invalid) - 5}")
    
    # 3. Deduplikace
    print(f"\n[3/6] Deduplikace...")
    deduped, dup_id, dup_header = deduplicate(valid)
    print(f"      Po dedup: {len(deduped)} (vyřazeno: {dup_id} duplicit ID, "
          f"{dup_header} duplicit header)")
    
    # 4. Filtr CS
    print(f"\n[4/6] Filtr M1-language == CS...")
    cs_only, excluded = filter_language(deduped, "CS")
    print(f"      Po filtru: {len(cs_only)} (vyřazeno: {excluded} ne-CS)")
    
    # 5. Split
    print(f"\n[5/6] Stratifikovaný split {TRAIN_RATIO:.0%}/{VAL_RATIO:.0%}/{TEST_RATIO:.0%}...")
    train, val, test = stratified_split(cs_only)
    print(f"      train: {len(train)}, val: {len(val)}, test: {len(test)}")
    
    # 6. Výstupy
    print(f"\n[6/6] Generuji výstupní soubory...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    jsonl_dir = OUTPUT_DIR / "jsonl"
    csv_dir = OUTPUT_DIR / "csv"
    jsonl_dir.mkdir(exist_ok=True)
    csv_dir.mkdir(exist_ok=True)
    
    # Raw JSONL pro každý split
    for name, recs in [("train", train), ("val", val), ("test", test)]:
        write_raw_jsonl(recs, jsonl_dir / f"{name}.jsonl", name)
    
    # Záloha kompletního datasetu (po preprocessing)
    write_raw_jsonl(cs_only, jsonl_dir / "dataset_full.jsonl", "all")
    
    # Instruction-format (jen train + val)
    write_instruction_jsonl(train, jsonl_dir / "train_instruction.jsonl")
    write_instruction_jsonl(val, jsonl_dir / "val_instruction.jsonl")
    
    # CSV ve formátu input CSV
    for name, recs in [("train", train), ("val", val), ("test", test)]:
        write_csv(recs, csv_dir / f"{name}.csv")
    
    # Stats
    stats = compute_stats(train, val, test)
    stats_path = OUTPUT_DIR / "split_stats.json"
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump({
            "input_file": INPUT_JSON.name,
            "seed": SEED,
            "ratios": {"train": TRAIN_RATIO, "val": VAL_RATIO, "test": TEST_RATIO},
            "preprocessing": {
                "raw_count": len(records),
                "after_validation": len(valid),
                "after_deduplication": len(deduped),
                "after_cs_filter": len(cs_only),
            },
            "splits": stats,
        }, f, ensure_ascii=False, indent=2)
    
    # Souhrn
    print(f"\n=== HOTOVO ===")
    print(f"Výstup v {OUTPUT_DIR.name}/")
    print(f"  jsonl/    raw + instruction format pro trénink/eval")
    print(f"  csv/      train/val/test CSV pro kontrolu")
    print(f"  split_stats.json  statistiky\n")
    
    print(f"Distribuce E1 napříč splity:")
    print(f"  {'split':<8} {'total':>6} {'NOT':>6} {'POT':>6} {'MISL':>6}")
    for name in ["train", "val", "test"]:
        s = stats[name]
        e1 = s["by_E1"]
        print(f"  {name:<8} {s['total']:>6} "
              f"{e1.get('NOT_MISLEADING', 0):>6} "
              f"{e1.get('POTENTIALLY_MISLEADING', 0):>6} "
              f"{e1.get('MISLEADING', 0):>6}")


if __name__ == "__main__":
    main()