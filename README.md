# Detekce zavádějícnosti českých zpravodajských titulků

Bakalářská práce — FAI UTB Zlín, 2026.

**Téma:** Trénování a kvalitativní analýza lokálních jazykových modelů s využitím vlastní datové sady.

## Abstrakt

Tato práce se zabývá detekcí zavádějícnosti v krátkých českých zpravodajských sděleních (titulcích) pomocí lokálního jazykového modelu LLaMA 3.1 8B doladěného metodou QLoRA na vlastním anotovaném datasetu (n = 400 záznamů). Práce porovnává výkon fine-tunovaných modelů s zero-shot inferencí (base i Instruct varianta) a komerčním modelem GPT-5.5 jako horní mezí.

## Klíčové výsledky

| Konfigurace | F1 macro | Accuracy | Cohen κ |
|---|---|---|---|
| LLaMA 3.1 8B base (zero-shot) | 0.361 | 48.7% | 0.134 |
| LLaMA 3.1 8B base + QLoRA | 0.700 | 71.3% | 0.573 |
| LLaMA 3.1 8B Instruct (zero-shot) | 0.752 | 76.2% | 0.628 |
| LLaMA 3.1 8B Instruct + QLoRA | 0.666 | 67.5% | 0.513 |
| GPT-5.5 (zero-shot) | 0.767 | 77.5% | 0.662 |

Hlavní zjištění:
- Fine-tuning přinesl dramatické zlepšení slabšího výchozího modelu (+0.34 F1).
- Fine-tuning silnějšího Instruct modelu vedl k mírné degradaci (-0.09 F1).
- Lokální model dosahuje 98 % výkonu komerčního SOTA při nulových cenových nákladech.
- Inter-annotator agreement: Cohen's kappa = 0.80 (téměř dokonalá shoda).

## Struktura projektu

```
bp-misleading-cs/
├── README.md
├── requirements.txt
├── annotation_guidelines/    ← Anotační pravidla
├── data/                     ← Raw, processed a IAA data
├── docs/                     ← Workflow a doprovodná dokumentace
├── label_studio/             ← XML konfigurace pro Label Studio
├── notebooks/
│   ├── finetune/             ← Colab notebooky pro QLoRA
│   └── inference/            ← Short/long prompt inference notebooky
├── prompts/                  ← Použité systémové prompty
├── scripts/                  ← Lokální utility a evaluace
├── models/                   ← LoRA adaptery a checkpointy
└── outputs/                  ← Predikce a evaluační výstupy
```

Poznámka: kvůli GitHub file-size limitům nejsou v repozitáři verzované velké `.safetensors` soubory a checkpointy v `models/`.

## Reprodukce experimentu

Detailní krok-za-krokem návod je v [`docs/workflow.md`](docs/workflow.md).

Stručně:

```bash
# 1. Vytvořit virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Vytvořit data splity (lokálně)
python data/processed/dataset_split.py

# 3. Spočítat IAA (lokálně)
python data/iaa/iaa_evaluation.py

# 4. Fine-tuning (Colab — notebooky 01, 02)

# 5. Inference (Colab — notebooky 03, 04)

# 6. Stáhnout predikce z Drive lokálně do outputs/predictions_short/ a outputs/predictions_long/

# 7. Evaluace (lokálně)
python outputs/04_evaluation.py
```

## Použité technologie

- **Modely:** LLaMA 3.1 8B (base + Instruct), GPT-5.5
- **Fine-tuning:** QLoRA (4-bit kvantizace + LoRA adapter)
- **Frameworks:** Unsloth, PEFT, Transformers, scikit-learn
- **Anotace:** Label Studio
- **Cloud:** Google Colab Pro (NVIDIA L4 GPU)
- **Lokální:** Apple M1 (16 GB RAM)

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
