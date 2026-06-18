# Workflow — Reprodukce experimentu

Kompletni postup od sbehu dat az po finalni evaluaci.

---

## Struktura projektu

```
bp-misleading-cs/
├── annotation_guidelines/     Anotacni prirucka (v3-final)
├── data/
│   ├── raw/
│   │   ├── scrapers/          10 zdrojovych slozek (scraper .py + sitemap .csv)
│   │   ├── merged/            Spojeny dataset vsech zdroju (225k titulku)
│   │   └── shuffler/          Priprava 400 kandidatu pro Label Studio
│   ├── processed/
│   │   ├── gold_standard_label_studio_400.json   Export z Label Studia
│   │   ├── dataset_split.py                      Split skript
│   │   └── splits/                               Vysledne train/val/test
│   │       ├── jsonl/raw/         (dataset_full, train, val, test)
│   │       ├── jsonl/instruction/ (train_instruction, val_instruction)
│   │       ├── csv/               (train, val, test)
│   │       └── split_stats.json
│   └── iaa/                   Inter-annotator agreement (Gemini jako 2. anotator)
├── label_studio/              XML konfigurace projektu (used + full)
├── prompts/                   System prompty (v1 long, v2 short)
├── notebooks/
│   ├── finetune/              Google Colab — QLoRA fine-tuning
│   │   ├── 01_finetune_llama_base.ipynb
│   │   └── 02_finetune_llama_instruct.ipynb
│   └── inference/             Google Colab — inference
│       ├── short/             (03_inference_llama_short, 04_inference_gpt_short)
│       └── long/              (03_inference_llama_long, 04_inference_gpt_long)
├── models/                    Finalni LoRA adaptery + checkpointy
│   ├── llama_base_qlora_v1/
│   └── llama_instruct_qlora_v1/
├── outputs/
│   ├── predictions_short/     5 JSONL predikcnich souboru (short prompt)
│   ├── predictions_long/      5 JSONL predikcnich souboru (long prompt)
│   ├── eval_outputs/          Vysledky evaluace (full/short/combined podsady)
│   └── 04_evaluation.py       Evaluacni skript (spolecny pro obe varianty)
└── docs/                      Tento soubor
```

---

## Faze 1: Sber dat (lokalne)

**Slozka:** `data/raw/scrapers/`

Pro kazdy z 10 zdroju existuje scraper (.py) a sitemap (.csv). Scrapery stahuji titulky z RSS/sitemap, vystup ukladaji do CSV.

**Slozka:** `data/raw/merged/`

`stats_merged.py` spoji vystupy vsech scraperu do jednoho `merged.csv` (225 288 zaznamu).

---

## Faze 2: Vyber kandidatu a anotace

**Slozka:** `data/raw/shuffler/`

1. Z merged datasetu se rucne (Google Sheets) vybere 400 kandidatu s pre-labelem
   → `candidate_list_400_gsheets_export.csv`
2. `shuffle_csv_by_lines.py` promisa poradi (max 2 stejne kategorie za sebou)
   → `label_studio_shuffled.csv`
3. Import do Label Studia (konfigurace: `label_studio/label_studio_config_used.xml`)
4. Anotace podle `annotation_guidelines/annotation_guidelines.md`

**Vystup:** `data/processed/gold_standard_label_studio_400.json`

---

## Faze 3: Dataset split (lokalne)

**Slozka:** `data/processed/`

```bash
python dataset_split.py
```

- Nacte Label Studio JSON export (400 zaznamu)
- Validuje, deduplikuje, filtruje CS-only (398)
- Stratifikovany split 70/10/20 podle E1 + M2
- Vystup: `splits/` (JSONL raw + instruction format, CSV, split_stats.json)

Vysledek: train (278) / val (40) / test (80)

---

## Faze 4: IAA — Inter-annotator agreement (lokalne)

**Slozka:** `data/iaa/`

```bash
python iaa_evaluation.py
```

- Gemini 3 Thinking jako druhy anotator (30 zaznamu)
- Spocita Cohen's kappa, weighted kappa, percent agreement

---

## Faze 5: Fine-tuning (Google Colab, GPU L4)

**Slozka:** `notebooks/finetune/`

**Predpoklady:**
- Colab Pro s GPU L4 (22 GB VRAM)
- HuggingFace token v Colab Secrets (pristup k meta-llama/Meta-Llama-3.1-8B)
- Data na Google Drive: `train_instruction.jsonl`, `val_instruction.jsonl`

**Postup:**

| Notebook | Model | Doba | Vystup |
|----------|-------|------|--------|
| `01_finetune_llama_base.ipynb` | LLaMA 3.1 8B Base | ~15 min | adapter v `models/llama_base_qlora_v1/` |
| `02_finetune_llama_instruct.ipynb` | LLaMA 3.1 8B Instruct | ~15 min | adapter v `models/llama_instruct_qlora_v1/` |

Oba pouzivaji QLoRA (rank 16, alpha 32, 3 epochy, 105 kroku). Logging pres W&B.

---

## Faze 6: Inference (Google Colab, GPU L4 / OpenAI API)

**Slozka:** `notebooks/inference/short/` a `notebooks/inference/long/`

Dve varianty promptu (short = v2 produkani, long = v1 experimentalni). Kazda varianta bezi ve svem notebooku.

### LLaMA inference (4 konfigurace)

Notebook `03_inference_llama_*.ipynb`:
- llama_base_zs (base, zero-shot)
- llama_base_qlora_zs (base + QLoRA adapter)
- llama_instruct_zs (Instruct, zero-shot)
- llama_instruct_qlora_zs (Instruct + QLoRA adapter)

Deterministicke generovani (temperature=0). Doba: ~30 min na 4 konfigurace.

### GPT-5.5 inference (komercni baseline)

Notebook `04_inference_gpt_*.ipynb`:
- Vyzaduje OPENAI_API_KEY v Colab Secrets
- Pouziva response_format pro garantovany JSON
- Doba: ~5 min, cena: ~$1.34

**Vystupy:** `outputs/predictions_short/` a `outputs/predictions_long/` (5 JSONL kazdy)

---

## Faze 7: Evaluace (lokalne)

**Slozka:** `outputs/`

```bash
python 04_evaluation.py
```

Jeden skript pro obe varianty promptu. Pocita:
- Single-label: accuracy, F1 macro, F1 weighted, Cohen's kappa, weighted kappa
- Multi-label: Jaccard, F1 per-label, exact match
- Per-class: precision, recall, F1 pro E1
- Confusion matrices

**Vystupy:** `outputs/eval_outputs/` (podsady full / short / combined s CSV reporty, confusion matrices, ploty)

---

## Reprodukovatelnost

| Faze | Seed | Poznamka |
|------|------|----------|
| Dataset split | 42 | stratifikovany split |
| Shuffler | 42 | poradi pro Label Studio |
| Fine-tuning | 42 | TrainingArguments(seed=42) |
| LLaMA inference | — | temperature=0, deterministicke |
| GPT-5.5 inference | — | temperature=0 (API) |

---

## Casova a cenova bilance

| Faze | Doba | Naklady |
|------|------|---------|
| Sber dat (scrapery) | ~2 h | $0 |
| Anotace (400 zaznamu) | ~6 h | $0 |
| IAA | ~15 min | ~$0.05 (Gemini API) |
| Fine-tuning (2x) | ~30 min | ~5 Colab units |
| Inference LLaMA (2 varianty) | ~1 h | ~10 Colab units |
| Inference GPT-5.5 (2 varianty) | ~10 min | ~$2.70 |
| Evaluace | ~5 min | $0 |
| **CELKEM** | **~10 h aktivni** | **~60 Kc + Colab Pro** |
