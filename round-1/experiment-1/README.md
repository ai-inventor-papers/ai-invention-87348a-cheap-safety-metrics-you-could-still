# Cheap safety checks for any single model

`demo/` — Self-contained demo (Colab-ready notebook or markdown). Run without setup.  
`src/` — Full source code, data, and outputs from the experiment execution.

**Type:** experiment  
**ID:** `art_ynwQLrNKw_e_`

## Layman Summary

Tests fifty cheap ways to judge a downloaded AI model's safety using only that model itself, with no reference copy to compare against, and races them against published methods.

## Full Summary

Races five candidate single-checkpoint safety readouts against four published incumbents (AMS 2608.05578, GFS 2606.22676, N-GLARE 2511.14195, HRCI_repr 2606.16349) and three black-box baselines on ONE shared harvest per checkpoint (weight pass + teacher-forced activation pass), identical 160-item battery, identical leave-one-lineage-out folds. Parent-free throughout: the setting is "you found a random model on HuggingFace and have nothing else".

WHAT IT PROVIDES. results/race_table.csv (all 50 pre-registered metrics, held-out balanced accuracy printed beside the tuned score and the gap, 3-way and 2-way); results/metrics_registry.json + sha256, frozen BEFORE any measurement and re-asserted at the end; results/step1_claim.json (principal angles between the instruct-to-SafeRL and instruct-to-abliterated activation differences on the Qwen3-4B anchor, per layer band, two read positions, plus the weight side); results/f5_weight_instrument.json (the honest-panel false-positive rate the published weight statistic lacks); plus lineage_census.json, ground_truth.json, per_checkpoint_reads.json, the three stage-gate files, and RESULTS.md as the digest.

FOUR RESULTS THAT ALREADY HOLD, independent of the race outcome.

F5 - THE PUBLISHED WEIGHT THRESHOLD DOES NOT SURVIVE REAL WEIGHTS. The Jorak-style subspace signature (BSA_w8 over bottom-1 left singular vectors of o_proj, sliding 8-layer window) reads 0.565 on honest, unedited Qwen3-0.6B, well above the 0.35 separator Gaussian simulation calibrates (simulated honest 0.171, invariant across Gaussian and heavy-tailed spectra). The same weights abliterated by us go to 1.000 and BOTGAP collapses below 0.003 in bf16. The statistic discriminates, but its absolute threshold is a false positive on real transformers, which carry genuinely shared bottom directions. Shipped fix: threshold-free AUROC plus a z-score against a within-checkpoint anisotropy-matched null (a random unit vector drawn from that layer's own bottom-16 subspace), validated at z=0.63 honest versus z=34 for a shared-direction edit. Separately, BOTGAP is NOT spectrum-invariant: on a heavy-tailed spectrum the honest value is 0.064, already below its own 0.10 separator.

CROSS-FITTING IS LOAD-BEARING. On pure Gaussian noise at d=2560 with 64 randomly-labelled items, an in-sample difference-in-means projection separates at AUROC 1.000 and the cross-fitted version at chance (0.377) - an in-sample harm direction is numerically indistinguishable from the harm label. AMS fits its direction on the same 16 pairs it then measures, so it is reported twice, in-sample as published and cross-fitted on our folds, with the gap between them.

THE SAFETY-TUNED ARM IS SCARCE, AND THAT IS ITSELF THE RESULT. A Hub census returns 445 "safety-tuned" repos, but the top five uploaders account for 85% and suffix-collapsing leaves 245. Only THREE independent safety-tuned lineages are reachable under 4B: Qwen3-4B-SafeRL (official), TinyLlama-1.1B (four algorithms, one parent) and gemma-2-2b (two). Below the pre-registered floor of five, so branch F1 fires: the two-way instruct-versus-abliterated claim becomes primary (11 instruct lineages against 6 abliterated) and the three-way is reported with its lineage count printed.

AN UNMATCHED SAFETY BENCHMARK IS MOSTLY LEXIS. TF-IDF plus logistic regression, no model at all, reaches AUC 0.963 separating harmful prompts from XSTest safe ones across sources, but only 0.537 against JailbreakBench's own Index-paired benign partners and 0.655 on XSTest positional twins with pair-grouped CV. Every internal readout must beat the MATCHED numbers.

METHOD NOTES TO INHERIT. The resampling unit is the LINEAGE (parent x tuning run), never the repo. Base checkpoints use the plain renderer and stay in their own stratum. The harvest stores VECTORS (all-layer hidden states at the last prompt token and the first generated token, per item, 35-141 MB per checkpoint), so every direction can be re-fitted and every null recomputed offline with no second GPU pass. Synthetic always-refuse and never-refuse poles run per checkpoint: the blanket refuser earns a +18.8 logit gap but only 0.80 across-item spread against 4.82 normal, which is why the coupling read ships with decision spread as a companion and a 0.25-logit floor below which it is declared UNDEFINED rather than small. Measured XSTest facts correcting the plan: 200 positional twin pairs, not 300, and keying on (type, focus) would silently drop 108 of 450 rows.

TRAPS FOUND AND FIXED. openai/gpt-5-nano returns content=None at default reasoning effort (192 of 200 completion tokens spent on hidden reasoning), silently degrading every grading to the regex fallback; it needs reasoning.effort=minimal. The judge also returns inconsistent rubric arithmetic, so the StrongREJECT score is recomputed from components. Gemma-2 must load with eager attention because sdpa omits its logit soft-capping. No Qwen judge anywhere; Qwen3Guard never judges SafeRL.

## Output Files

- `method.py`
- `full_method_out.json`
- `mini_method_out.json`
- `preview_method_out.json`

## Demo Files

- **method.py** — Research methodology implementation

---
*Generated by AI Inventor Pipeline*
