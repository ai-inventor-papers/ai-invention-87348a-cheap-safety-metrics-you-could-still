# Re-scoring old safety reads without new runs (iter-3, evaluation 1)

This is a CPU-only re-analysis of data that iteration 2 already put on disk (`iter_2/gen_art/gen_art_experiment_1`, read-only).
No model is loaded, no LLM is called and nothing was spent on OpenRouter ($0). It covers the four items the iteration-3 reviewer marked as blocking:

1. **Oracle re-score** (`oracle_rescore.json`). The 13 registry metrics that depend on the refusal readout are re-scored with the per-item readout R replaced by judged refusal. Each is scored in two forms (pipeline/mean-imputed and restricted/judged-only), with two oracles (binary `refused`, continuous `1-score`) and a **split-half leakage control**: the metric comes from item half A and the target from half B, then the halves are swapped and the two values averaged.
2. **Early scatter** (`early_scatter.json`, `figures/early_scatter_panels.png`). C12, C13, C15 and the two logit-only bars are plotted on SCREEN16 for the 15 graded checkpoints. This is scatter only: no read gets a survival verdict because n<24.
3. **Power** (`power.json`, `figures/power_curves.png`). A lineage-cluster simulation of the minimum detectable effect (MDE) for a single Spearman and for the S1 "beat the logit gap by 0.15" rule, at n = 15/24/30/38.
4. **Step-1 reconciliation** (`step1_reconciled.json`, `figures/step1_per_layer.png`) and the **numbers ledger** (`numbers_ledger.json`).

All sentences below are taken from those JSON files. Every target correlation uses n ≤ 15 checkpoints (6 lineages, 3 families), so it is **SCATTER ONLY**.

## Headline results

**Warm-up (reproduction before any new number).** `compute_all_metrics` reproduces iteration 2's memoised metric rows exactly: 181/181 checks, with |Δ| < 1e-6 under `probe_cf` and `logitgap`. The subset re-implementation of the 13 R-dependent metrics plus 3 bars matches `compute_all_metrics` on the full item set in 684/690 checks. The 6 mismatches are all on CensorTune under `probe_cf`: no probe can be fitted because every judged item is refused, and the pipeline would impute R=0, so this module keeps those values UNDEFINED. The registry sha256 is asserted (`ffe9b234…6fdd`).

**Coverage fact that shapes everything.** Every checkpoint has judged grades on only **48 harmful + 32 benign_alarming** items. No xstest_contrast or plain_benign item was ever generated or graded. So under the oracle, the twin metrics are UNDEFINED in the restricted form. In the pipeline form they compare a mean-imputed constant against the alarming side, which reads the same false-refusal rate that defines the target. `x_presentation_invariance` is **ORACLE_UNDEFINED**, because judged grades exist only for the plain presentation.

**(1) Oracle verdicts** (primary: binary oracle, product target; split-half; MDE from `power.json`). Out of 13:
- **11 × CONSTRUCT_UNTESTABLE_AT_n**
- **1 × READOUT_FAILED** (`x_category_dispersion`)
- **1 × ORACLE_UNDEFINED** (`x_presentation_invariance`)

The balanced target gives identical counts. The continuous-score oracle gives 12 untestable and 1 undefined.
- **Cause-B answer:** *"the readout: 1 metric(s) pass with judged refusal but fail through probe_cf."*
- **Caveat on that one pass.** On judged items, `x_category_dispersion` is the spread of refusal rates across JBB-harmful and XSTest-alarming categories. That is close to the construct the target itself measures. Its split-half ρ = +0.59 (lineage-cluster bootstrap CI [+0.05, +0.91]; lineage level +0.77, n=6; null p95 0.52) is partly a split-half reliability of the target, not independent evidence that across-item structure carries safety signal.
- **Everything else is below the MDE.** Examples of split-half oracle ρ: decision_spread +0.60, twin_delta +0.58, mutual_info +0.53. At n=15 with lineage ICC 0.62, power stays below 80% even at ρ=0.9. No metric in this set can be declared CONSTRUCT_FAILS.
- **The leakage control matters.** Same-item ("LEAKY") oracle ρ runs higher than split-half, e.g. decision_spread 0.71 vs 0.60 and twin_delta 0.73 vs 0.58.
- **Consistency check with iteration 2.** `probe_cf` `x_presentation_invariance` against the full target gives ρ = −0.71, reproducing iteration 2's −0.71 (n=13).
- **LOLO two-way instruct-vs-abliterated BA.** No R-dependent metric beats its within-lineage permutation null p95 under the oracle or under `probe_cf` (graded panel: 9 checkpoints, 5 lineages).

**(2) Early scatter** (SCREEN16 item indices are saved in `early_scatter.json → screen16`, product target, n=15):

| read | ρ | CI | lineage-level ρ |
|---|---|---|---|
| C12 twin discrimination | +0.03 | [−0.93, +0.76] | −0.14 |
| C13 presentation invariance (logit gap) | −0.07 (n=14) | — | −0.49 |
| C15 late effective rank | −0.31 | — | — |
| C15 late dispersion | +0.57 | [+0.19, +0.90] | +1.00 |
| bar: logit gap harm−twin | +0.41 | — | — |
| bar: log refusal mass | +0.02 | — | — |

- **C13 sign.** The pre-fixed negative sign holds at both aggregation levels; no violation was recorded.
- **C15 orientation.** Undeclared, so it is scored as |ρ| only.
- **Family and size alone.** Family explains ANOVA R² = 0.47 of the target (p=0.022). Log-size alone gives ρ = +0.31.
- **Poles.** C12 fails its pole rule: the always-refuse wrapper scores *higher* than all 5 honest instruct checkpoints. C13 passes: CensorTune is more invariant, which counts as less safe. All three bars fail.

**(3) Power** (lineage clusters [5,4,2,2,1,1], ICC_obs 0.617, ρ_G obs 0.229; primary cell 1000 Monte Carlo datasets × 300 inner bootstraps):
- **Single test.** *At n=15, no Spearman up to 0.9 reaches 80% power.* The MDE is 0.80 at n = 24, 30 and 38. Analytic Fisher-z MDEs are 0.71/0.58/0.52/0.47. The simulated MDE is much larger because n_eff ≈ 6–9: the number of clusters stays at 6.
- **S1 difference rule.** 80% power is **never reached** for any n ≤ 38 or any corr(X,G). The maximum power is 0.07 at n=15 and 0.62–0.78 at n=38. In plain words: **"nothing beats the logit gap by 0.15" would be a vacuous bound in this design.**
- **Correlation with the logit gap helps, not hurts.** Contrary to the plan's premise, a higher corr(X,G) *raises* the S1 power (n=38: 0.62 → 0.78).
- **Size.** Both tests are conservative: single-test size 0.02–0.05; S1 false-positive rate at ρ_X = ρ_G is ≤ 0.002.

**(4) Step 1: reconciled verdict SHARED_SUBSPACE_DIFFERENT_DIRECTIONS.** This holds at every non-excluded layer for both sites, both abliterated arms and both item sets.
- **Pre de-anisotropisation.** The top-8 first principal angle between the SafeRL and abliteration difference matrices (e.g. 22° at layer 24) beats both the anisotropy-matched null (p5 ≈ 68°) and the random-subspace null.
- **After projecting out the top-5 instruct PCs,** the angle is still significant (47.7° vs post-projection null p5 68°).
- **Mean-shift cosines are at null.** They exceed the anisotropy-matched direction null at layers ~23–31 (|cos| ≈ 0.15–0.22), but never the sign-flip null (p95 ≈ 0.24). The pre-stated reconciliation hypothesis holds: the edits share a low-dimensional subspace that is *not* just the generic high-variance subspace, while moving along different directions inside it.
- **Excluded layers** (difference exactly zero): hs_last/heretic 0–4, hs_last/mlabonne 0.
- **Iteration-2 numbers reproduced:**
  - 31.11° mean first angle, `step1_anchor.json:headline.mean_first_principal_angle_deg_last_prompt_token`
  - −0.092 mean cosine, same file, `headline.mean_cosine_between_mean_difference_vectors`
  - |cos| 0.201 vs null p95 0.417 (claimed 0.41), `d1_step1.json:headline_numbers`
- **Positive control does not reproduce to rounding.** Recomputed at the fixed w4_L24-27 band it is 0.885 vs 0.750, against the claimed 0.92 > 0.72 (iteration 2 picked its strongest cell). The ordering still holds.
- **Process note.** A first version of this module reported SHARED_ANISOTROPY_ONLY because of a bug: the post-projection "first" angle was the largest principal angle. It was fixed, and a self-check assert (angle == acos(first_cos)) now runs at every site.

**Numbers ledger:** 41 rows, 41 found, 41 reproduced from their file:key (0 NOT_FOUND). It lists 5 inconsistencies:
- `crossover_k=1` by |ρ| hides the fact that by LOLO BA the internal read is ahead again at k=64
- iteration 2's step1_anchor says SHARED_SUBSPACE while d1_step1 says DIFFERENT_SUBSPACES; resolved above
- three different "kappa" values (0.456/0.585/0.749)
- a stale `stage3_analysis.json` (WITHDRAWN) next to `stage3_v2.json` (EDIT_NOT_RISK)
- a misnamed `max_abs_signed_cos_anywhere_hs_last`

**Target discrepancy.** The registered target is (1−hc)(1−fr), under which a blanket refuser scores **0**, not 0.5 as the hypothesis text says. The BALANCED variant 0.5(1−hc)+0.5(1−fr) gives 0.5 and is reported alongside everywhere. Ledger panel tags follow the plan's list; the Step-1 rows carry P17_2 although they come from the single Qwen3-4B lineage.

## Layout

| path | what |
|---|---|
| `eval.py` | single entry point: `oracle`, `scatter`, `power`, `step1`, `ledger`, `finalize`, `all` |
| `common.py` | read-only access to iteration 2 (paths, grades, targets, probe_cf memo, torch-free `select_band` shim) |
| `oracle.py` | warm-up + oracle re-score, split-half control, poles, LOLO null; verdict rules fixed at the top |
| `scatter.py` | SCREEN16 selection, C12/C13/C15/bars, correlations, family/size rows, poles, figure |
| `power.py` | lineage-cluster power/MDE simulation |
| `step1.py` | Step-1 recomputation, matched nulls, de-anisotropisation test, reproduction table |
| `ledger.py` | numbers ledger (values read by key path from iteration-2 files) |
| `oracle_rescore.json`, `early_scatter.json`, `power.json`, `step1_reconciled.json`, `numbers_ledger.json` | results |
| `full_eval_out.json` / `mini_eval_out.json` / `preview_eval_out.json` | exp_eval_sol_out summary (metrics_agg + 6 example datasets) |
| `figures/` | scatter panels, power curves, Step-1 per-layer plot |
| `logs/` | loguru logs of every module |

## How to run

```bash
UV_PROJECT_ENVIRONMENT=venv_eval uv sync
venv_eval/bin/python eval.py all     # ~25 min on 2 shared CPUs; power runs in the background
```

`OMP/MKL/OPENBLAS_NUM_THREADS=1` are set in code. Peak RAM is under 1.5 GB. Nothing is ever written into the iteration-2 directory: `_cached_metrics` is never called.

## Restoring removed files

- `venv_eval/` (delete: regenerable): `UV_PROJECT_ENVIRONMENT=venv_eval uv sync`
- `__pycache__/` (delete: regenerable): created automatically by `venv_eval/bin/python eval.py all`
