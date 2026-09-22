# C2 depth sweep (EXPLORATORY, post hoc)

**This sweep is exploratory and post hoc. It was never pre-registered and it never enters the S1-S6 selection rule. The only pre-registered C2 value -- the one used anywhere in S1-S6 -- is method.py's production value at B_mid = [L_h-1, L_h, L_h+1], the band at 50% depth (L_h = round(0.5 * n_layers)). Every other point below exists purely to describe how sensitive C2's correlation with BALANCED/PRODUCT is to the choice of depth, for interpretation only.**

## Acceptance check

Max |sweep production value - rows/<slug>.json candidates.C2.value| over 24 models: **0.0** (tolerance 0.001).

All checked models passed.


## Spearman(C2_f, BALANCED) over the 23 graded models, lineage-cluster bootstrap 95% CI

n = 23 graded models with a valid sweep in every row shown.

| f | centre depth note | rho | 95% CI | n | # models C2_f>0.1 |
|---|---|---|---|---|---|
| 0.15 |  | 0.322 | [-0.085, 0.633] | 23 | 4 |
| 0.25 |  | 0.536 | [0.103, 0.735] | 23 | 4 |
| 0.35 |  | 0.327 | [-0.214, 0.730] | 23 | 3 |
| 0.45 |  | 0.617 | [0.272, 0.937] | 23 | 6 |
| 0.5 |  (= production band for every model) | 0.900 | [0.796, 0.971] | 23 | 10 |
| 0.55 |  | 0.834 | [0.609, 0.950] | 23 | 11 |
| 0.65 |  | 0.688 | [0.452, 0.926] | 23 | 14 |
| 0.75 |  | 0.689 | [0.443, 0.893] | 23 | 13 |
| 0.85 |  | 0.768 | [0.528, 0.871] | 23 | 12 |

## Spearman(C2_f, PRODUCT), same bootstrap

| f | rho | 95% CI | n |
|---|---|---|---|
| 0.15 | 0.284 | [-0.121, 0.595] | 23 |
| 0.25 | 0.534 | [0.126, 0.721] | 23 |
| 0.35 | 0.299 | [-0.240, 0.702] | 23 |
| 0.45 | 0.571 | [0.227, 0.899] | 23 |
| 0.5 | 0.884 | [0.769, 0.961] | 23 |
| 0.55 | 0.832 | [0.632, 0.946] | 23 |
| 0.65 | 0.669 | [0.446, 0.923] | 23 |
| 0.75 | 0.655 | [0.371, 0.869] | 23 |
| 0.85 | 0.739 | [0.437, 0.875] | 23 |

## Within-family Spearman(C2_f, BALANCED)

n: qwen3=8, qwen2.5=5, tinyllama=5

| f | qwen3 | qwen2.5 | tinyllama |
|---|---|---|---|
| 0.15 | 0.333 | 0.500 | -0.200 |
| 0.25 | 0.548 | 0.800 | 0.300 |
| 0.35 | 0.310 | 0.100 | 0.600 |
| 0.45 | 0.452 | 1.000 | 0.600 |
| 0.5 | 0.952 | 1.000 | 1.000 |
| 0.55 | 0.976 | 0.900 | 0.300 |
| 0.65 | 0.833 | 1.000 | 0.700 |
| 0.75 | 0.833 | 0.700 | 0.700 |
| 0.85 | 0.833 | 0.700 | 0.300 |

Production band match: '0.5' (the fraction whose centre layer c equals L_h for every model, or None if it varies by model -- see `production_band_match_per_model` in the JSON).


## Runtime

Total wall time: 477s over 24 repos.


## Failures

None.

