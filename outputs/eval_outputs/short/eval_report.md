# Evaluation report

## Souhrn

| Konfigurace | Parsing | E1 F1 macro | E1 kappa | E1 kappa weighted |
|---|---|---|---|---|
| llama_base_zs_short | 100.0% | 0.240 | 0.027 | 0.052 |
| llama_base_qlora_zs_short | 100.0% | 0.800 | 0.715 | 0.824 |
| llama_instruct_zs_short | 98.8% | 0.377 | 0.149 | 0.362 |
| llama_instruct_qlora_zs_short | 100.0% | 0.722 | 0.609 | 0.772 |
| gpt_5_5_zs_short | 100.0% | 0.864 | 0.785 | 0.878 |

## Per-pole F1 macro

| Konfigurace | A1 | A3 | C1 | E1 | M3 | B1 | B3 | C3 | D1 | M1 | M2 | A2 | B2 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| llama_base_zs_short | 0.282 | 0.324 | 0.362 | 0.240 | — | 0.462 | 0.130 | 0.306 | 0.086 | — | — | 0.293 | 0.264 |
| llama_base_qlora_zs_short | 0.654 | 0.654 | 0.747 | 0.800 | — | 0.909 | 0.371 | 0.517 | 0.883 | — | — | 0.473 | 0.442 |
| llama_instruct_zs_short | 0.375 | 0.318 | 0.459 | 0.377 | — | 0.373 | 0.157 | 0.308 | 0.367 | — | — | 0.095 | 0.035 |
| llama_instruct_qlora_zs_short | 0.709 | 0.732 | 0.692 | 0.722 | — | 0.895 | 0.391 | 0.460 | 0.743 | — | — | 0.407 | 0.532 |
| gpt_5_5_zs_short | 0.702 | 0.736 | 0.772 | 0.864 | — | 0.863 | 0.661 | 0.558 | 0.677 | — | — | 0.507 | 0.524 |

## E1 detail (hlavní pole)

### llama_base_zs_short
- Validních predikcí: 80/80
- Accuracy: 0.438
- F1 macro: 0.240
- F1 weighted: 0.279
- Cohen's kappa: 0.027
- Cohen's kappa (weighted quadratic): 0.052

**Per-class:**
| Třída | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| NOT_MISLEADING | 0.430 | 1.000 | 0.602 | 34 |
| POTENTIALLY_MISLEADING | 0.000 | 0.000 | 0.000 | 30 |
| MISLEADING | 1.000 | 0.062 | 0.118 | 16 |

### llama_base_qlora_zs_short
- Validních predikcí: 80/80
- Accuracy: 0.812
- F1 macro: 0.800
- F1 weighted: 0.814
- Cohen's kappa: 0.715
- Cohen's kappa (weighted quadratic): 0.824

**Per-class:**
| Třída | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| NOT_MISLEADING | 0.938 | 0.882 | 0.909 | 34 |
| POTENTIALLY_MISLEADING | 0.833 | 0.667 | 0.741 | 30 |
| MISLEADING | 0.625 | 0.938 | 0.750 | 16 |

### llama_instruct_zs_short
- Validních predikcí: 79/80
- Accuracy: 0.494
- F1 macro: 0.377
- F1 weighted: 0.399
- Cohen's kappa: 0.149
- Cohen's kappa (weighted quadratic): 0.362

**Per-class:**
| Třída | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| NOT_MISLEADING | 0.500 | 1.000 | 0.667 | 33 |
| POTENTIALLY_MISLEADING | 0.300 | 0.100 | 0.150 | 30 |
| MISLEADING | 1.000 | 0.188 | 0.316 | 16 |

### llama_instruct_qlora_zs_short
- Validních predikcí: 80/80
- Accuracy: 0.750
- F1 macro: 0.722
- F1 weighted: 0.755
- Cohen's kappa: 0.609
- Cohen's kappa (weighted quadratic): 0.772

**Per-class:**
| Třída | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| NOT_MISLEADING | 0.966 | 0.824 | 0.889 | 34 |
| POTENTIALLY_MISLEADING | 0.639 | 0.767 | 0.697 | 30 |
| MISLEADING | 0.600 | 0.562 | 0.581 | 16 |

### gpt_5_5_zs_short
- Validních predikcí: 80/80
- Accuracy: 0.863
- F1 macro: 0.864
- F1 weighted: 0.864
- Cohen's kappa: 0.785
- Cohen's kappa (weighted quadratic): 0.878

**Per-class:**
| Třída | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| NOT_MISLEADING | 0.935 | 0.853 | 0.892 | 34 |
| POTENTIALLY_MISLEADING | 0.788 | 0.867 | 0.825 | 30 |
| MISLEADING | 0.875 | 0.875 | 0.875 | 16 |
