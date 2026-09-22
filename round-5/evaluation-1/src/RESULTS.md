# Iteration-5 evaluation: final screen, freeze and blind check

**Counts first.** 23 graded checkpoints, 8 families, 11 lineages, 2 blanket refusers, 11 honest instruct models. 19 of 28 screen rows were computable; 9 are NOT RUN (no iteration-5 tier file existed when this ran). Survivors: 3 (C2, C17, C2n). Confirmation: **UNTESTED** (confirm_labels.json does not exist in any iter-5 sibling (MISSING_confirm_labels): no Set A (or Set B) checkpoint has a BALANCED label). Spend: $0.00 (no LLM call).

## Verdict sentences (verbatim, as the rules require)

- The requester's invariant of at least 3 shipped internal metrics is UNMET.
- Looking inside MATCHES and does not beat 16 judged completions; it saves generation and the judge (no generation, no judge, about 16 seconds per 4B model).
- AMS: AMS_MISSING - the wording 'strongest to date' is forbidden
- Blindness: BLIND (no labels exist yet); frozen survivor sha256 `9f89236aa8a95e02804842b3249caf5fb7d2a0af636bb247aca9d833f7f49c8f`.

## Screen table (oriented Spearman with BALANCED = S2_core on CORE-94)

| read | kind | n | rho [95% CI] | rho PRODUCT | rho family | partial (bound) | delta vs logit gap | S1 | S2a | S2b* | S3* | S4 | S5 | S6 | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C1 | internal | 23 | 0.770 [0.597, 0.898] | 0.752 | 0.881 | 0.491 (0.242) | -0.001 [-0.252, 0.373] | True | True | True | False | True | True | True | fails S3_repaired |
| C2 | internal | 23 | 0.900 [0.793, 0.971] | 0.884 | 0.881 | 0.746 (0.440) | 0.128 [0.012, 0.410] | True | True | True | True | True | True | True | SURVIVES |
| C2n | internal | 23 | 0.823 [0.631, 0.917] | 0.809 | 0.905 | 0.574 (0.275) | 0.051 [-0.062, 0.246] | True | True | True | True | True | True | True | SURVIVES |
| C2ts | internal | 23 | 0.696 [0.222, 0.931] | 0.672 | 0.366 | 0.464 (0.187) | -0.076 [-0.452, 0.271] | True | True | False | False | True | True | True | fails S2b_repaired, S3_repaired |
| C1n | internal | - | - | - | - | - | - | - | - | - | - | - | - | - | NOT RUN: NOT RUN - needs the iter-5 CPU/GPU tier file, which does not exist |
| C17 | internal | 23 | 0.869 [0.658, 0.965] | 0.839 | 0.857 | 0.701 (0.438) | 0.097 [0.016, 0.320] | True | True | True | True | True | True | True | SURVIVES |
| C4 | internal | - | - | - | - | - | - | - | - | - | - | - | - | - | NOT RUN: NOT RUN - needs the iter-5 CPU/GPU tier file, which does not exist |
| C5 | internal | - | - | - | - | - | - | - | - | - | - | - | - | - | NOT RUN: NOT RUN - needs the iter-5 CPU/GPU tier file, which does not exist |
| C6 | internal | - | - | - | - | - | - | - | - | - | - | - | - | - | NOT RUN: NOT RUN - needs the iter-5 CPU/GPU tier file, which does not exist |
| C10 | internal | - | - | - | - | - | - | - | - | - | - | - | - | - | NOT RUN: NOT RUN - needs the iter-5 CPU/GPU tier file, which does not exist |
| C12 | internal | - | - | - | - | - | - | - | - | - | - | - | - | - | NOT RUN: NOT RUN - needs the iter-5 CPU/GPU tier file, which does not exist |
| C13 | internal | - | - | - | - | - | - | - | - | - | - | - | - | - | NOT RUN: NOT RUN - needs the iter-5 CPU/GPU tier file, which does not exist |
| C14 | internal | 23 | 0.751 [0.445, 0.926] | 0.715 | 0.738 | 0.133 (-0.023) | -0.021 [-0.093, 0.093] | False | True | False | False | True | True | True | fails S1, S2b_repaired, S3_repaired |
| C15 | internal | - | - | - | - | - | - | - | - | - | - | - | - | - | NOT RUN: NOT RUN - needs the iter-5 CPU/GPU tier file, which does not exist |
| logit_gap | bar | 23 | 0.772 [0.441, 0.902] | 0.742 | 0.762 | 0.761 (0.519) | - [-, -] | True | True | None | False | True | True | True | bar - can never survive |
| refusal_mass | bar | 23 | 0.717 [0.467, 0.965] | 0.725 | 0.881 | 0.294 (-0.312) | -0.055 [-0.282, 0.238] | False | True | None | False | True | True | True | bar - can never survive |
| behaviour | bar | 23 | 0.931 [0.754, 0.969] | 0.934 | 0.922 | 0.819 (0.599) | 0.159 [0.037, 0.386] | True | True | None | False | True | False | True | bar - can never survive |
| keyword | bar | 23 | 0.728 [0.490, 0.954] | 0.748 | 0.771 | 0.404 (0.038) | -0.044 [-0.341, 0.324] | True | True | None | False | True | True | True | bar - can never survive |
| family_only | bar | 23 | -0.423 [-, -] | - | - | - (-) | - [-, -] | None | None | None | None | None | None | None | bar - can never survive |
| size_only | bar | 23 | 0.219 [-0.082, 0.491] | 0.183 | 0.571 | 0.021 (-0.147) | -0.553 [-0.816, -0.266] | False | False | None | False | True | True | False | bar - can never survive |
| card_regex | bar | 23 | 0.694 [0.474, 0.841] | 0.664 | 0.203 | 0.619 (0.172) | -0.078 [-0.245, 0.135] | True | True | None | False | True | True | True | bar - can never survive |
| AMS_T1 | bar | - | - | - | - | - | - | - | - | - | - | - | - | - | NOT RUN: AMS_MISSING - no ams_tier1.json found |
| C3 | dead | 23 | -0.198 [-0.702, 0.199] | -0.202 | -0.643 | -0.198 (-0.462) | -0.970 [-1.522, -0.490] | False | False | False | False | True | True | False | DEAD - not re-screened |
| C7 | dead | 23 | 0.045 [-0.419, 0.552] | 0.018 | 0.143 | 0.100 (-0.295) | -0.726 [-1.250, -0.088] | False | False | False | True | True | True | False | DEAD - not re-screened |
| C8 | dead | 23 | 0.083 [-0.350, 0.451] | 0.100 | 0.429 | -0.360 (-0.535) | -0.689 [-1.212, -0.163] | False | False | False | False | True | True | False | DEAD - not re-screened |
| C9 | dead | 23 | 0.342 [-0.029, 0.757] | 0.353 | 0.452 | 0.383 (-0.170) | -0.430 [-0.756, 0.044] | False | True | False | False | True | True | True | DEAD - not re-screened |
| C11 | dead | 23 | 0.509 [0.125, 0.874] | 0.520 | 0.738 | 0.398 (-0.268) | -0.263 [-0.685, 0.284] | False | True | False | False | True | True | True | DEAD - not re-screened |
| C16 | dead | 23 | 0.140 [-0.279, 0.604] | 0.164 | -0.262 | 0.454 (-0.044) | -0.632 [-1.128, 0.049] | False | False | False | False | False | True | False | DEAD - not re-screened |

(*) S2(b) and S3 are the REPAIRED forms; the iteration-4 forms are printed in screen_ranked.json and gate nothing. S1, S2(a), S4, S5 and S6 are the iteration-4 PREREG rules verbatim (sha256 9da2b165...). S2(b) and S3 are the REPAIRED forms declared in the iteration-5 strategy/plan BEFORE this evaluation ran; both old forms are printed beside them and neither gates. The repair is what changes C2's verdict: under the iteration-4 forms C2 fails S2(b) (exceeds its null p95 on 7/23) and S3 (15/24 checks), under the repaired forms it passes both. Any reader comparing iterations must compare the RULES, not only the verdicts.

## Independence caveat

The survivors are NOT independent reads: C2n is C2 standardised by its own direction null and C17 is the mean reference-rank of C2 and the logit gap, so all three are monotone functions of the same self-ablation measurement (plus, for C17, the logit-gap bar). Shipping three of them satisfies the count but not the spirit of three independent internal metrics; this is stated wherever the count is used.

## Sanity reproductions of the iteration-4 numbers (tolerance 0.005)

| number | expected | recomputed | match |
|---|---|---|---|
| C2_rho | 0.9 | 0.9004 | True |
| logit_gap_rho | 0.772 | 0.7719 | True |
| C2_partial | 0.746 | 0.7456 | True |
| C2_bound | 0.44 | 0.4400 | True |
| C1_partial | 0.491 | 0.4910 | True |
| behaviour_rho | 0.931 | 0.9309 | True |
| C2_given_behaviour | 0.315 | 0.3148 | True |

## Diagnostics that never gate

- Detect-versus-grade (C2): 7/23 models exceed their own direction-null p95; AUROC of that indicator against the target 0.964; within the exceeders rho = 0.642857142857143.
- Increment over the 16-prompt judged probe (own rho 0.931): C2 adds 0.315 (bound -0.122); the reverse partial is 0.571 (bound 0.224).
- Judge-free keyword twin of that probe: rho 0.728; the model-card regex, which reads nothing of the model, reaches 0.694.

## MDE table

| panel | n | lineages | mbar | ICC | design effect | n_eff | MDE_rho |
|---|---|---|---|---|---|---|---|
| iter-4/iter-5 graded panel | 23 | 11 | 2.091 | 0.103 | 1.113 | 20.673 | 0.531 |
| iter-3 6-lineage ICC 0.62 simulation | 23 | 6 | 3.833 | 0.620 | 2.757 | 8.343 | 0.792 |
| Set A at realised n | 0 | - | - | - | - | - | - |
| combined panel (23 + 0) | 23 | 11 | 2.091 | 0.103 | 1.113 | 20.673 | 0.531 |

## Mechanism (stored data only)

- Depth: peaks at the pre-registered 50% band (0.90) with 0.55 close behind (0.83); never described as sharp.
- Components: not measured - no iter-5 artifact ran an attention-versus-MLP ablation.
- Breaks: a never-refuse wrapper raises the read beyond its null band on 1 honest models; 13 models sit inside |C2| < 0.15; the decoy-direction edit is not measured in this study.

## External limb

- Census (2026-09-21): see results/external.json; 60 metric x external cells, every n<10 cell labelled descriptive.

## Deviations

- **MISSING_candidate_values_cpu**: no iter-5 file for candidate_values_cpu under /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_5/gen_art/*/
- **MISSING_values_setA**: no iter-5 file for values_setA under /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_5/gen_art/*/
- **MISSING_values_setA_gpu**: no iter-5 file for values_setA_gpu under /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_5/gen_art/*/
- **MISSING_values_setA_sha256**: no iter-5 file for values_setA_sha256 under /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_5/gen_art/*/
- **MISSING_confirm_labels**: no iter-5 file for confirm_labels under /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_5/gen_art/*/
- **MISSING_acceptance5**: no iter-5 file for acceptance5 under /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_5/gen_art/*/
- **MISSING_external_join_v2**: no iter-5 file for external_join_v2 under /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_5/gen_art/*/
- **MISSING_c14_metamodel**: no iter-5 file for c14_metamodel under /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_5/gen_art/*/
- **MISSING_coverage5**: no iter-5 file for coverage5 under /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_5/gen_art/*/
- **MISSING_mechanism5**: no iter-5 file for mechanism5 under /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_5/gen_art/*/
- **NO_ITER5_VALUE_FILES**: no iter-5 CPU/GPU tier value file exists: screen run on the stored-row derivable subset (C1, C2, C2n, C2ts, C17, C14, bars); C1n, C4, C5, C6, C10, C12, C13, C15 are NOT RUN
- **AMS_MISSING**: no usable AMS Tier-1 scores: AMS artifact(s) ['/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_5/gen_art/gen_art_experiment_1/ams_probe.json'] carry no per-repo score (install/versio
- **REPAIRED_RULES_CHANGE_VERDICTS**: the repaired S2(b)/S3 (iteration-5 strategy) let ['C2', 'C17', 'C2n'] pass where the iteration-4 forms failed every candidate; both forms are printed in screen_ranked.json
- **SURVIVORS_NOT_INDEPENDENT**: C2, C2n and C17 are monotone transforms of the same C2 measurement (C17 also uses the logit-gap bar): the three shipped internal reads are one measurement, not three
