# Detekce zavádějícnosti českých zpravodajských titulků

Bakalářská práce, FAI UTB ve Zlíně, 2026.

Projekt se zabývá automatickou detekcí zavádějícnosti v českých zpravodajských titulcích pomocí lokálních jazykových modelů, fine-tuningu metodou QLoRA a srovnání s komerčním baseline modelem GPT-5.5.

## O projektu

Hlavní výzkumná otázka byla, zda lze na malé vlastní anotované sadě doladit lokální model tak, aby se přiblížil výkonu silného komerčního modelu při hodnocení zavádějících titulků.

Repozitář obsahuje:
- vlastní anotační schéma a anotační pravidla
- datasety a jejich zpracování
- notebooky pro fine-tuning a inferenci
- evaluační skripty a finální výstupy
- konfigurační soubory použitých LoRA adapterů

## Hlavní výsledky

V této README jsou jako hlavní prezentovány výsledky varianty `short prompt`, protože to byla hlavní experimentální varianta použitá v bakalářské práci. Varianta `long prompt` je uvedena níže jako doplňkové srovnání.

### Short Prompt

Hlavní pole práce je `E1-misleading_header_model_final`, tedy finální třída zavádějícnosti. Následující tabulka shrnuje výsledky na testovací sadě 80 titulků.

| Konfigurace | Parsing | E1 F1 macro | Accuracy | Cohen's kappa |
|---|---:|---:|---:|---:|
| LLaMA 3.1 8B base (zero-shot) | 100.0% | 0.240 | 43.8% | 0.027 |
| LLaMA 3.1 8B base + QLoRA | 100.0% | 0.800 | 81.2% | 0.715 |
| LLaMA 3.1 8B Instruct (zero-shot) | 98.8% | 0.377 | 49.4% | 0.149 |
| LLaMA 3.1 8B Instruct + QLoRA | 100.0% | 0.722 | 75.0% | 0.609 |
| GPT-5.5 (zero-shot) | 100.0% | 0.864 | 86.3% | 0.785 |

Hlavní zjištění:
- Nejlepší lokální konfigurace v hlavní variantě byla `LLaMA 3.1 8B base + QLoRA` s `F1 macro = 0.800`.
- Fine-tuning dramaticky pomohl base modelu: z `0.240` na `0.800` F1 macro.
- Fine-tuning pomohl i Instruct variantě, ale méně výrazně: z `0.377` na `0.722`.
- GPT-5.5 zůstal nejsilnějším baseline modelem, ale nejlepší lokální model se mu výrazně přiblížil.

### Long Prompt

Pro úplnost repozitář obsahuje i výsledky varianty `long prompt`, která používala podrobnější instrukční prompt s kompletním popisem schématu.

| Konfigurace | Parsing | E1 F1 macro | Accuracy | Cohen's kappa |
|---|---:|---:|---:|---:|
| LLaMA 3.1 8B base (zero-shot) | 100.0% | 0.361 | 48.7% | 0.134 |
| LLaMA 3.1 8B base + QLoRA | 100.0% | 0.700 | 71.3% | 0.573 |
| LLaMA 3.1 8B Instruct (zero-shot) | 100.0% | 0.752 | 76.2% | 0.628 |
| LLaMA 3.1 8B Instruct + QLoRA | 100.0% | 0.666 | 67.5% | 0.513 |
| GPT-5.5 (zero-shot) | 100.0% | 0.767 | 77.5% | 0.662 |

Pozorování:
- `long prompt` vyhovoval výrazně více zero-shot `Instruct` variantě než `short prompt`.
- `short prompt` naopak lépe fungoval pro `base + QLoRA` i pro GPT-5.5.
- Výsledky tedy nejsou jen o modelu, ale i o interakci mezi typem modelu a typem promptu.

## Dataset a metodika

### Sběr dat

- Zdrojový korpus vznikl scrapingem 10 českých zpravodajských zdrojů.
- Spojený korpus obsahuje `225 288` titulků.
- Z něj bylo ručně vybráno `400` kandidátů pro anotaci.

### Anotace

- Anotace probíhala v Label Studiu podle vlastního schématu.
- Hlavní cílová proměnná je `E1-misleading_header_model_final` se třídami:
  - `NOT_MISLEADING`
  - `POTENTIALLY_MISLEADING`
  - `MISLEADING`
- Dále se anotovaly dílčí signály jako chybějící kontext, framing, riziko misinterpretace nebo konspirační vzorce.

### Split dat

Po vyčištění a filtraci vzniklo `398` validních záznamů, které byly rozděleny stratifikovaně:

| Split | Velikost |
|---|---:|
| Train | 278 |
| Validation | 40 |
| Test | 80 |

### Inter-annotator agreement

Sekce `data/iaa/` obsahuje experiment s druhým anotátorem. V práci vychází Cohenovo kappa přibližně na `0.80`, což odpovídá velmi vysoké shodě.

### Modely

Použité modely:
- LLaMA 3.1 8B Base
- LLaMA 3.1 8B Instruct
- GPT-5.5 jako komerční baseline

Fine-tuning:
- metoda `QLoRA`
- 4-bit kvantizace
- LoRA `rank = 16`
- `alpha = 32`
- 3 epochy

## Prompt varianty

Repozitář obsahuje dvě promptovací strategie:

- `prompts/system_prompt_v1.txt`
  Dlouhá explicitní instrukce s detailním popisem celého anotačního schématu, rozhodovacích pravidel a definic jednotlivých polí.
- `prompts/system_prompt_v2_short.txt`
  Kratší produkční varianta se stručnějším zadáním a výčtem povolených hodnot.

Související notebooky:
- `notebooks/inference/long/`
- `notebooks/inference/short/`

## Struktura repozitáře

```text
bp-misleading-cs/
├── README.md
├── requirements.txt
├── annotation_guidelines/    # Anotační příručka
├── data/
│   ├── raw/                  # Surová data a scrapery
│   ├── processed/            # Gold dataset a splity
│   ├── iaa/                  # Inter-annotator agreement
│   └── used_sources_urls/    # Exporty zdrojových URL a finální výběry
├── docs/                     # Workflow a doprovodná dokumentace
├── label_studio/             # XML konfigurace Label Studia
├── notebooks/
│   ├── finetune/
│   └── inference/
│       ├── short/
│       └── long/
├── prompts/                  # Použité systémové prompty
├── scripts/                  # Utility skripty
├── models/                   # Konfigurace adapterů a tokenizerů
└── outputs/                  # Predikce, reporty, grafy a confusion matrices
```

## Kde co hledat

- Hlavní workflow: `docs/workflow.md`
- Anotační pravidla: `annotation_guidelines/annotation_guidelines.md`
- Label Studio konfigurace: `label_studio/label_studio_config_used.xml`
- Short prompt výsledky: `outputs/eval_outputs/short/`
- Long prompt výsledky: `outputs/eval_outputs/full/`
- Kombinované srovnání: `outputs/eval_outputs/combined/`

## Reprodukce

### Lokální příprava

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Split datasetu

```bash
python data/processed/dataset_split.py
```

### Inter-annotator agreement

```bash
python data/iaa/iaa_evaluation.py
```

### Fine-tuning

Notebooky:
- `notebooks/finetune/01_finetune_llama_base.ipynb`
- `notebooks/finetune/02_finetune_llama_instruct.ipynb`

Typické prostředí:
- Google Colab Pro
- GPU NVIDIA L4
- Hugging Face token v Colab Secrets

### Inference

Short prompt:
- `notebooks/inference/short/03_inference_llama_short.ipynb`
- `notebooks/inference/short/04_inference_gpt_short.ipynb`

Long prompt:
- `notebooks/inference/long/03_inference_llama_long.ipynb`
- `notebooks/inference/long/04_inference_gpt_long.ipynb`

### Evaluace

```bash
python outputs/04_evaluation.py
```

Výstupem jsou:
- CSV reporty
- Markdown reporty
- confusion matrices
- PNG a PDF grafy

## Důležité poznámky

- Finální adapter weights `models/llama_base_qlora_v1/adapter_model.safetensors` a `models/llama_instruct_qlora_v1/adapter_model.safetensors` jsou publikované přes Git LFS.
- Velké checkpointy a průběžné trénovací artefakty ve veřejném repozitáři verzované nejsou.
- V repozitáři zůstávají konfigurační soubory adapterů, tokenizerů, notebooky, datasety a evaluační výstupy.
- Soubor `data/raw/merged/merged.csv` má přibližně 56 MB, takže GitHub u něj zobrazuje upozornění na větší velikost, ale repozitář jej stále přijímá.
- Notebooky pro GPT inferenci očekávají `OPENAI_API_KEY` v Colab Secrets.
- Notebooky pro LLaMA očekávají Hugging Face token s přístupem k `meta-llama/Meta-Llama-3.1-8B`.

## Použité technologie

- Python
- pandas
- scikit-learn
- Transformers
- PEFT
- Unsloth
- Label Studio
- Google Colab Pro

## Citace

Pokud používáte tuto práci, prosím citujte:

```bibtex
@thesis{zemanek2026misleading,
  author = {Zemánek, Ondřej},
  title  = {Trénování a kvalitativní analýza lokálních jazykových modelů
            s využitím vlastní datové sady},
  school = {Univerzita Tomáše Bati ve Zlíně, Fakulta aplikované informatiky},
  year   = {2026},
  type   = {Bakalářská práce}
}
```

## Licence

Licence zatím není explicitně přidána. Není-li uvedeno jinak, obsah repozitáře zůstává chráněn autorským právem autora.

## Kontakt

Ondřej Zemánek
