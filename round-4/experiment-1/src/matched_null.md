# Matched-null robustness check for S2(b) -- C1 / C2 (EXPLORATORY, post hoc)

**This check is exploratory and post hoc. It was never pre-registered, it is not part of S1-S6, and it never changes any pre-registered verdict. The only pre-registered C1/C2 null_p95 values -- the ones used anywhere in S1-S6's rule S2(b) -- are method.py's production values at B_mid = [L_h-1, L_h, L_h+1] (the band at 50% depth), written to rows/<slug>.json. Everything below exists purely to describe how much of S2(b)'s C1/C2 failure traces to the production null directions' variance mismatch (median ratio var(Av)/var(Ah) ~= 2.89 across rows/*.json), for interpretation only.**

## Acceptance check

- **C1**: max |reproduced null_p95 - rows/<slug>.json candidates.C1.null_p95| over 23 models: **0.0** (tolerance 0.001). All checked models passed.
- **C2**: max |reproduced null_p95 - rows/<slug>.json candidates.C2.null_p95| over 23 models: **0.0** (tolerance 0.001). All checked models passed.


## S2(b) exceed counts: production null vs variance-matched null

Split by the BALANCED median (0.6082): upper = BALANCED > median, lower = BALANCED <= median.

| candidate | null | overall | upper half | lower half | S2(b) fraction | S2(b) pass (>=60%) |
|---|---|---|---|---|---|---|
| C1 | production | 11/23 | 10/11 | 1/12 | 0.478 | False |
| C1 | matched | 11/23 | 10/11 | 1/12 | 0.478 | False |
| C2 | production | 7/23 | 7/11 | 0/12 | 0.304 | False |
| C2 | matched | 11/23 | 10/11 | 1/12 | 0.478 | False |

## Per-model detail

| repo | BALANCED | C1 value | C1 null_p95 (prod) | C1 null_p95 (matched) | C1 exceed (prod/matched) | C1 mean ratio (prod/matched) | C2 value | C2 null_p95 (prod) | C2 null_p95 (matched) | C2 exceed (prod/matched) | C2 mean ratio (prod/matched) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen/Qwen3-4B-SafeRL | 0.929 | 3.374 | 1.200 | 0.625 | True/True | 1.937/1.000 | 0.745 | 0.470 | 0.425 | True/True | 2.031/1.000 |
| allenai/OLMo-2-0425-1B-Instruct | 0.913 | 2.722 | 0.342 | 0.176 | True/True | 1.314/1.000 | 0.849 | 0.171 | 0.033 | True/True | 1.354/1.000 |
| unsloth/Llama-3.2-1B-Instruct | 0.909 | 3.218 | 0.872 | 0.267 | True/True | 2.059/1.000 | 1.084 | 0.229 | 0.171 | True/True | 1.990/1.000 |
| Qwen/Qwen3-4B | 0.906 | 3.149 | 0.554 | 0.747 | True/True | 2.854/1.000 | 1.229 | 0.419 | 0.172 | True/True | 2.946/1.000 |
| tiiuae/Falcon3-1B-Instruct | 0.896 | 2.797 | 0.912 | 0.547 | True/True | 5.924/1.000 | 0.227 | 0.261 | 0.067 | False/True | 6.113/1.000 |
| Qwen/Qwen3-1.7B | 0.820 | 5.206 | 0.585 | 0.653 | True/True | 1.997/1.000 | 0.636 | 0.164 | 0.043 | True/True | 1.901/1.000 |
| Qwen/Qwen2.5-1.5B-Instruct | 0.760 | 6.749 | 1.551 | 1.494 | True/True | 2.925/1.000 | 0.503 | 0.113 | 0.135 | True/True | 2.951/1.000 |
| Qwen/Qwen2.5-0.5B-Instruct | 0.708 | 6.108 | 3.240 | 1.695 | True/True | 3.785/1.000 | 0.127 | 0.324 | 0.107 | False/True | 3.907/1.000 |
| Qwen/Qwen3-0.6B | 0.638 | 4.800 | 0.990 | 1.564 | True/True | 1.994/1.000 | 0.457 | 0.225 | 0.220 | True/True | 2.039/1.000 |
| AIPlans/TinyLlama-1.1B-ORPO-PKU-SafeRLHF | 0.629 | 0.610 | 0.861 | 1.214 | False/False | 3.741/1.000 | 0.038 | 0.135 | 0.045 | False/False | 3.688/1.000 |
| h2oai/h2o-danube3-500m-chat | 0.614 | 2.565 | 1.051 | 1.238 | True/True | 2.796/1.000 | 0.043 | 0.117 | 0.038 | False/True | 2.714/1.000 |
| HuggingFaceTB/SmolLM2-360M-Instruct | 0.608 | 0.743 | 1.764 | 2.667 | False/False | 8.021/1.000 | 0.011 | 0.122 | 0.065 | False/False | 8.055/1.000 |
| AIPlans/TinyLlama-1.1B-IPO-PKU-SafeRLHF | 0.601 | 0.102 | 0.754 | 0.585 | False/False | 5.604/1.000 | 0.020 | 0.052 | 0.022 | False/False | 5.571/1.000 |
| TinyLlama/TinyLlama-1.1B-Chat-v1.0 | 0.568 | 0.451 | 0.959 | 0.909 | False/False | 6.936/1.000 | -0.001 | 0.047 | 0.044 | False/False | 6.757/1.000 |
| AIPlans/tinyllama-1.1b-dpo-pku-saferlhf | 0.553 | 0.587 | 0.670 | 0.939 | False/False | 6.879/1.000 | -0.010 | 0.058 | 0.041 | False/False | 6.703/1.000 |
| DreamFast/qwen3-4b-heretic | 0.553 | 1.812 | 1.305 | 1.357 | True/True | 3.387/1.000 | 0.170 | 0.404 | 0.213 | False/False | 3.531/1.000 |
| Shortmund09/MLDM-TinyLlama-1.1b-gcpo-ocra-saferlhf | 0.545 | -0.390 | 0.400 | 0.371 | False/False | 7.199/1.000 | -0.037 | 0.030 | 0.025 | False/False | 7.092/1.000 |
| huihui-ai/Huihui-Qwen3-1.7B-abliterated-v2 | 0.535 | 0.024 | 0.515 | 0.764 | False/False | 2.727/1.000 | -0.014 | 0.170 | 0.095 | False/False | 2.647/1.000 |
| Goekdeniz-Guelmez/Josiefied-Qwen2.5-1.5B-Instruct-abliterated-v1 | 0.523 | 0.550 | 1.505 | 1.035 | False/False | 4.278/1.000 | 0.079 | 0.232 | 0.077 | False/True | 4.221/1.000 |
| huihui-ai/Qwen2.5-1.5B-Instruct-CensorTune | 0.518 | -5.928 | 8.384 | 5.898 | False/False | 9.569/1.000 | -0.028 | 0.491 | 0.100 | False/False | 9.433/1.000 |
| mlabonne/Qwen3-4B-abliterated | 0.515 | 0.195 | 0.513 | 0.821 | False/False | 5.082/1.000 | -0.307 | 0.054 | 0.053 | False/False | 5.405/1.000 |
| huihui-ai/Huihui-Qwen3-0.6B-abliterated-v2 | 0.512 | -2.027 | 1.055 | 1.313 | False/False | 1.725/1.000 | -0.267 | 0.091 | 0.128 | False/False | 1.770/1.000 |
| huihui-ai/Qwen2.5-0.5B-Instruct-CensorTune | 0.500 | 1.986 | 2.123 | 4.010 | False/False | 2.848/1.000 | -0.029 | 0.168 | 0.146 | False/False | 2.812/1.000 |

## Interpretation

- **C1**: production null exceed count 11/23 (47.8%) vs variance-matched null exceed count 11/23 (47.8%). The variance-matched null does NOT change the S2(b) pass/fail outcome for C1 (both fail the >=60% bar).
- **C2**: production null exceed count 7/23 (30.4%) vs variance-matched null exceed count 11/23 (47.8%). The variance-matched null does NOT change the S2(b) pass/fail outcome for C2 (both fail the >=60% bar).

This check is exploratory and post hoc; it never changes S1-S6, and the pre-registered S2(b) verdict (C1 11/23, C2 7/23, both below the 60% bar) stands regardless of what the matched null shows.


## Runtime

Total wall time: 596s over 23 repos.


## Failures

None.

