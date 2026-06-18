# Evaluation report

## Souhrn

| Konfigurace | Parsing | E1 F1 macro | E1 kappa | E1 kappa weighted |
|---|---|---|---|---|
| llama_base_zs | 100.0% | 0.361 | 0.134 | 0.256 |
| llama_base_qlora_zs | 100.0% | 0.700 | 0.573 | 0.761 |
| llama_instruct_zs | 100.0% | 0.752 | 0.628 | 0.787 |
| llama_instruct_qlora_zs | 100.0% | 0.666 | 0.513 | 0.720 |
| gpt_5_5_zs | 100.0% | 0.767 | 0.662 | 0.829 |
| llama_base_zs_short | 100.0% | 0.240 | 0.027 | 0.052 |
| llama_base_qlora_zs_short | 100.0% | 0.800 | 0.715 | 0.824 |
| llama_instruct_zs_short | 98.8% | 0.377 | 0.149 | 0.362 |
| llama_instruct_qlora_zs_short | 100.0% | 0.722 | 0.609 | 0.772 |
| gpt_5_5_zs_short | 100.0% | 0.864 | 0.785 | 0.878 |

## Per-pole F1 macro

| Konfigurace | A1 | A3 | C1 | E1 | M3 | B1 | B3 | C3 | D1 | M1 | M2 | A2 | B2 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| llama_base_zs | 0.249 | 0.440 | 0.462 | 0.361 | — | 0.370 | 0.172 | 0.306 | 0.162 | — | — | 0.274 | 0.241 |
| llama_base_qlora_zs | 0.657 | 0.518 | 0.740 | 0.700 | — | 0.879 | 0.382 | 0.340 | 0.826 | — | — | 0.433 | 0.234 |
| llama_instruct_zs | 0.442 | 0.426 | 0.625 | 0.752 | — | 0.402 | 0.246 | 0.484 | 0.489 | — | — | 0.209 | 0.156 |
| llama_instruct_qlora_zs | 0.615 | 0.515 | 0.619 | 0.666 | — | 0.792 | 0.360 | 0.502 | 0.681 | — | — | 0.289 | 0.242 |
| gpt_5_5_zs | 0.685 | 0.825 | 0.815 | 0.767 | — | 0.961 | 0.801 | 0.408 | 0.692 | — | — | 0.453 | 0.598 |
| llama_base_zs_short | 0.282 | 0.324 | 0.362 | 0.240 | — | 0.462 | 0.130 | 0.306 | 0.086 | — | — | 0.293 | 0.264 |
| llama_base_qlora_zs_short | 0.654 | 0.654 | 0.747 | 0.800 | — | 0.909 | 0.371 | 0.517 | 0.883 | — | — | 0.473 | 0.442 |
| llama_instruct_zs_short | 0.375 | 0.318 | 0.459 | 0.377 | — | 0.373 | 0.157 | 0.308 | 0.367 | — | — | 0.095 | 0.035 |
| llama_instruct_qlora_zs_short | 0.709 | 0.732 | 0.692 | 0.722 | — | 0.895 | 0.391 | 0.460 | 0.743 | — | — | 0.407 | 0.532 |
| gpt_5_5_zs_short | 0.702 | 0.736 | 0.772 | 0.864 | — | 0.863 | 0.661 | 0.558 | 0.677 | — | — | 0.507 | 0.524 |

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
