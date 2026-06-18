# Evaluation report

## Souhrn

| Konfigurace | Parsing | E1 F1 macro | E1 kappa | E1 kappa weighted |
|---|---|---|---|---|
| llama_base_zs | 100.0% | 0.361 | 0.134 | 0.256 |
| llama_base_qlora_zs | 100.0% | 0.700 | 0.573 | 0.761 |
| llama_instruct_zs | 100.0% | 0.752 | 0.628 | 0.787 |
| llama_instruct_qlora_zs | 100.0% | 0.666 | 0.513 | 0.720 |
| gpt_5_5_zs | 100.0% | 0.767 | 0.662 | 0.829 |

## Per-pole F1 macro

| Konfigurace | A1 | A3 | C1 | E1 | M3 | B1 | B3 | C3 | D1 | M1 | M2 | A2 | B2 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| llama_base_zs | 0.249 | 0.440 | 0.462 | 0.361 | — | 0.370 | 0.172 | 0.306 | 0.162 | — | — | 0.274 | 0.241 |
| llama_base_qlora_zs | 0.657 | 0.518 | 0.740 | 0.700 | — | 0.879 | 0.382 | 0.340 | 0.826 | — | — | 0.433 | 0.234 |
| llama_instruct_zs | 0.442 | 0.426 | 0.625 | 0.752 | — | 0.402 | 0.246 | 0.484 | 0.489 | — | — | 0.209 | 0.156 |
| llama_instruct_qlora_zs | 0.615 | 0.515 | 0.619 | 0.666 | — | 0.792 | 0.360 | 0.502 | 0.681 | — | — | 0.289 | 0.242 |
| gpt_5_5_zs | 0.685 | 0.825 | 0.815 | 0.767 | — | 0.961 | 0.801 | 0.408 | 0.692 | — | — | 0.453 | 0.598 |

## E1 detail (hlavní pole)

### llama_base_zs
- Validních predikcí: 80/80
- Accuracy: 0.487
- F1 macro: 0.361
- F1 weighted: 0.359
- Cohen's kappa: 0.134
- Cohen's kappa (weighted quadratic): 0.256

**Per-class:**
| Třída | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| NOT_MISLEADING | 0.459 | 1.000 | 0.630 | 34 |
| POTENTIALLY_MISLEADING | 0.000 | 0.000 | 0.000 | 30 |
| MISLEADING | 0.833 | 0.312 | 0.455 | 16 |

### llama_base_qlora_zs
- Validních predikcí: 80/80
- Accuracy: 0.713
- F1 macro: 0.700
- F1 weighted: 0.717
- Cohen's kappa: 0.573
- Cohen's kappa (weighted quadratic): 0.761

**Per-class:**
| Třída | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| NOT_MISLEADING | 0.964 | 0.794 | 0.871 | 34 |
| POTENTIALLY_MISLEADING | 0.682 | 0.500 | 0.577 | 30 |
| MISLEADING | 0.500 | 0.938 | 0.652 | 16 |

### llama_instruct_zs
- Validních predikcí: 80/80
- Accuracy: 0.762
- F1 macro: 0.752
- F1 weighted: 0.764
- Cohen's kappa: 0.628
- Cohen's kappa (weighted quadratic): 0.787

**Per-class:**
| Třída | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| NOT_MISLEADING | 0.875 | 0.824 | 0.848 | 34 |
| POTENTIALLY_MISLEADING | 0.667 | 0.733 | 0.698 | 30 |
| MISLEADING | 0.733 | 0.688 | 0.710 | 16 |

### llama_instruct_qlora_zs
- Validních predikcí: 80/80
- Accuracy: 0.675
- F1 macro: 0.666
- F1 weighted: 0.686
- Cohen's kappa: 0.513
- Cohen's kappa (weighted quadratic): 0.720

**Per-class:**
| Třída | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| NOT_MISLEADING | 0.962 | 0.735 | 0.833 | 34 |
| POTENTIALLY_MISLEADING | 0.593 | 0.533 | 0.561 | 30 |
| MISLEADING | 0.481 | 0.812 | 0.605 | 16 |

### gpt_5_5_zs
- Validních predikcí: 80/80
- Accuracy: 0.775
- F1 macro: 0.767
- F1 weighted: 0.777
- Cohen's kappa: 0.662
- Cohen's kappa (weighted quadratic): 0.829

**Per-class:**
| Třída | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| NOT_MISLEADING | 0.966 | 0.824 | 0.889 | 34 |
| POTENTIALLY_MISLEADING | 0.750 | 0.600 | 0.667 | 30 |
| MISLEADING | 0.593 | 1.000 | 0.744 | 16 |
