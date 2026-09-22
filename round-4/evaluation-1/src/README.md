# Verified numbers and figures for the rewrite (run_fcYd, iteration 4, evaluation 1)

This artifact runs on CPU only and makes **zero LLM calls ($0)**. It re-reads or recomputes every number the paper
cites, taking each one from a `file:key` in the iteration 1 to 3 artifacts. It clears the reviewer's blocking items
A to I.

## Counts first

| what | count |
|---|---|
| Table-1 cells (10 metrics × 2 levels) that reproduce the stored value under the product target (tolerance 0.005, same n) | **20 / 20** |
| Table-1 rows that change **sign** between the balanced target B and the product target P: checkpoint level / lineage level | **0 / 1** |
| Table-1 rows that change **significance** between B and P: checkpoint level / lineage level | **0 / 5** (lineage n=5–6, descriptive) |
| Corrections written (`corrections.json`) | **31**, of which 6 are DISCREPANCY, 5 CONFIRMED_AS_IS and 20 CORRECTED |
| `numbers_ledger_v2.json` entries | **167**. Of the 41 v1 ledger rows, 5 are superseded, 36 confirmed and 0 retracted |
| Reproducibility table | 10 artifacts × 8 columns; **17 cells UNSOURCED**; $2.87 of sourced OpenRouter spend across iterations 1–3 |
| Figures | 6 (PDF with Type-42 fonts, plus 200-dpi PNG) |

## Headline findings

**A. Target.** The stored Table-1 correlations use **P = (1−hc)(1−fr)**, where a blanket refuser scores 0. They do not
use the balanced **B = 0.5(1−hc)+0.5(1−fr)** the paper defines, where a blanket refuser scores 0.5. Recomputed under B:

| metric | n | ρ_B checkpoint level [lineage-bootstrap 95% CI] | ρ_P checkpoint level | p_B | ρ_B lineage level (n) | ρ_P lineage level |
|---|---|---|---|---|---|---|
| x_presentation_invariance | 13 | −0.692 [−0.93, −0.28] | −0.709 | 0.009 | −0.60 (5) | −0.40 |
| b_card_regex_termswept | 15 | +0.491 [−0.24, +0.83] | +0.451 | 0.063 | +0.06 (6) | −0.03 |
| w_bsa_w8_k4 | 15 | −0.268 [−0.81, +0.58] | −0.189 | 0.334 | −0.09 (6) | −0.14 |
| k_hrci_repr | 14 | +0.068 [−0.73, +1.00] | +0.015 | 0.817 | −0.70 (5) | −0.40 |
| b_logit_gap_mean | 15 | +0.329 [−0.49, +0.80] | +0.229 | 0.232 | −0.77 (6) | −0.83 |
| b_logit_gap_harmful | 15 | +0.400 [−0.44, +0.81] | +0.307 | 0.140 | −0.60 (6) | −0.66 |
| b_logit_gap_alarming | 15 | +0.129 [−0.59, +0.65] | +0.011 | 0.648 | −1.00 (6) | −0.94 |
| b_refusal_token_mass | 15 | −0.314 [−0.79, +0.44] | −0.354 | 0.254 | −0.83 (6) | −0.77 |
| x_c1_r2 | 14 | +0.516 [−0.43, +0.95] | +0.385 | 0.059 | −0.40 (5) | −0.30 |
| x_c1_auroc_items | 14 | +0.495 [−0.22, +0.89] | +0.358 | 0.072 | −0.40 (5) | −0.30 |

- **Presentation invariance: SURVIVES.** At checkpoint level under B it has ρ = −0.692, p = 0.009, permutation p = 0.011,
  and the CI excludes 0. It is a **negative** association. At lineage level n = 5, and that cannot reach significance
  under any target: the minimum achievable two-sided Spearman p at n = 5 is 0.0167, and only for a perfect rank order.
  The iteration-2 conclusion stands: the effect is within-lineage only and negative.
- **The iteration-3 panel's "J2 product" is not a product.** J2_core = 2·S2_core − 1, the Youden form, so it is exactly
  rank-identical to S2. A true product P3 = harm_refusal × benign_alarming_compliance was rebuilt from the stored
  components.
- Iteration-2 B vs iteration-3 S2 on 15 shared checkpoints: Spearman 0.76. Iteration-2 P vs iteration-3 P3: 0.70. The
  two iterations used different items, token budgets and judges.
- The family ANOVA R² = 0.469 is the variance of the **P target** explained by family. Under B it is 0.455; by lineage
  it is 0.725 (P) and 0.716 (B).

**B. Nulls.** The race null is a **within-lineage label-permutation null**: 300 permutations through the identical
leave-one-lineage-out pipeline, with the bar at p95. It is not the anisotropy-matched null the paper describes. Three
rows beat it: presentation invariance 1.000 vs 0.775, card regex 0.917 vs 0.788, and b_logit_gap_alarming 0.800 vs
0.700. w_bsa_w8_k4 only ties its null, 0.826 vs 0.826. The four direction-null counts are always printed together, with
Wilson 95% CIs:

| count | what it counts | Wilson 95% CI |
|---|---|---|
| 16/17 | last-token read | [0.73, 0.99] |
| 17/17 | XSTest twins | [0.82, 1.00] |
| 9/17 | first-token read | [0.31, 0.74] |
| 9/20 | experiment-1 probe layer | [0.26, 0.66] |

About **38.5%** of the harm direction's above-chance AUROC (0.835) is reachable by a random within-span direction (span
null 0.629; 4-lineage bootstrap [0.33, 0.41]). Whitening removes **22.9%** (whitened AUROC 0.759; bootstrap
[0.13, 0.37]).

**C. Weights.** Every weight number now uses the wording **down_proj kappa_hat (realised-strength estimate)**, not BSA.
The one exception is the pre-registered BSA flag line, which really is BSA.

- AUROC pooled 0.843 [0.74, 0.93], n = 71; abliteration-tool outputs only 0.947 [0.86, 1.00].
- Within-edited Spearman(kappa_hat, compliance) = 0.26, n = 14, lineage-cluster CI [−0.47, 0.83]. The stored interval
  [−0.65, 0.86] comes from a different bootstrap.
- **The stored "MDE 0.56" is not an 80%-power MDE.** It is the |ρ| at which the estimate's own CI just excludes 0. The
  Fisher-z MDE at 80% power and n = 14 is **0.714**.
- True kappa ρ = 0.035 (n = 12). The L1 logit gap ρ = −0.62 (p = 0.019).
- Replication across three other runs: 0.85 [0.58, 0.95] over all edits and 0.65 [−0.20, 0.94] over projection edits
  only. Both are **confounded by edit type**.
- **307/484** layer-matrices lie outside the validity band (Wilson [0.590, 0.676]). Median cosine is 1.00 in band and
  0.14 out of band; per-layer ρ = 0.075.
- The BSA 0.35 flag fires on 34/35 honest checkpoints (Wilson [0.855, 0.995]).
- A **rank-one spectral repair** (not a parent swap) moves BOTGAP_min from 0.012 to 0.82. Harmful refusal moves only
  from 0.125 to 0.208, against 0.438 for the honest parent.

**D. ROSI.** The implementation edits **o_proj and down_proj only**, on every layer. The published ROSI (arXiv
2508.20766) adds a rank-one term to all residual-stream write matrices. Here the embeddings and lm_head are untouched.

- The edit is W += α·d·w̄ᵀ, with α = mult·0.01·‖W‖_F/‖w̄‖, where w̄ is the mean row of W itself.
- Qwen2.5-0.5B-Instruct, B at ×0/×1/×4/×16: 0.788 / 0.776 / 0.621 / 0.500.
- ×4 paired change: ΔB **−0.151** [−0.233, −0.065], ΔP **−0.317** [−0.472, −0.159], refusal-based Δ −0.109.
- The hidden-direction control gives ΔB −0.042 [−0.0948, −0.0010]. That CI **barely** excludes 0, so part of the drop is
  generic perturbation.
- Qwen3-0.6B ×4: −0.081 [−0.176, +0.017].
- Caveats: 20-token continuations, 2 hosts.

**E.** No experiment generated 256 tokens, although the iteration-3 paper says so. The actual max_new_tokens were 96/48
(iteration-2 experiment 1), 20 (ladder), 64 (iteration-2 experiment 3 and the iteration-3 panel), 192/96/48
(iteration 1). gemini-2.5-flash is the primary judge only for the iteration-3 panel.

**F. Grader-side refusal.** This quantifies a known LLM-judge failure (GuidedBench 2502.16903, and 2609.10594).

- On 1,040 paired replies, the StrongREJECT framing said "refused" where the stance framing said "engaged" 328 times,
  and the reverse happened 67 times. Exact McNemar p = 2.1e−42.
- The degenerate grade 1,1,1 appears on 40.5% of all replies and 65.9% of harmful ones.
- **1,1,1 is also the rubric's legitimate output for a true refusal**, so these counts bound grader-side refusal from
  above; they do not measure it.
- Calibration gate: gpt-5-mini accuracy 0.892 fails it (specificity 47/60); gemini-2.5-flash 0.975 passes.

**G. External.**

- HELM: 81 models, 36 resolved, 45 closed-API, 2 sub-4B.
- Guardian pair: the squared identical-weights gap is **6.72× the across-model variance**, or 2.59× as a ratio of SDs.
  This is a ceiling on any weights-only readout.
- OLB v2 joins 15 panel repos, but only **n = 7** of them have a graded target:
  Spearman(B, capability) = 0.21 [−0.55, 1.0] and Spearman(P3, capability) = 0.18. Partial Spearman(metric, B | capability)
  is undefined for all 10 metrics (n = 3).
- Published numbers for this panel: TrustLLM n = 0, AIR-Bench n = 0, Arena-Hard n = 0, and GSM8K and MMLU n = **1** each
  (TinyLlama, from the old leaderboard). HELM/AIR/SALAD coverage of the sub-4B panel is 0. The sealed hold-out leaked in
  iteration 2 (verbatim note in `corrections.json`, item G4).

**H. Power.** Lineage-cluster simulation with iteration-3 `power.py` imported, ICC 0.617, 6 lineage clusters.

- Single-Spearman MDE at 80% power, two-sided: n=15 **0.89**, 21 0.90, 24 0.79, 30 **0.78**, 38 0.74, 50 **0.71**.
  One-sided it is 0.05–0.07 lower.
- ρ = 0.5 and ρ = 0.4 are **unreachable below n = 100 with 6 lineages**. With about 2.5 checkpoints per lineage, ρ = 0.5
  needs **n = 55 across 22 lineages** and ρ = 0.4 needs n = 90 across 36. The paper's "≥30 checkpoints suffice" is
  refuted.
- The difference test from the S1 rule never reaches 80% power at n ≤ 30 and needs ρ ≈ 0.89 at n = 50. The new
  partial-Spearman S1 has an MDE similar to the single test.
- The sub-chance identity BA of the metamodel (LOLO 0.14, LOFO 0.00) is a fold artefact. In 2 of 5 LOLO folds and 3 of
  3 LOFO folds, the held-out family label never appears in training, so every prediction on those folds is wrong by
  construction.
- Recomputed metamodel out-of-fold Spearman with B: 0.12 (n = 9, p = 0.76).

## Layout

| path | what |
|---|---|
| `eval.py` | orchestrator: step-0 inventory, runs `sections/*.py`, then writes `corrections.json`, `numbers_ledger_v2.json` and `eval_out.json` |
| `io_utils.py` | shared helpers: `get` with a provenance log, `lineage_cluster_bootstrap`, `wilson`, `spearman_with_p` (exact permutation when n ≤ 8) |
| `sections/a_targets.py` | A1–A6: target recompute, reproduction gate, B vs P, flags, verdict, iteration-3 cross-check |
| `sections/b_nulls.py` | B1–B3: null naming, direction-null counts, above-chance shares |
| `sections/c_weights.py` | C: kappa_hat AUROC, within-edited test, validity band, BSA flag, repair (plus `results/C_kappa_points.json`) |
| `sections/d_rosi.py` | D: ROSI method from code, and the dose table under B, P and the refusal-based variant |
| `sections/e_repro.py` | E: reproducibility table (`results/E_repro.md`) |
| `sections/f_grader.py`, `sections/g_external.py` | F: grader calibration and McNemar; G: HELM, guardian, OLB v2 join, coverage |
| `sections/h_misc.py`, `sections/h_power.py`, `sections/h_power_growing.py` | H: ANOVA and metamodel; MDE simulation; the n-needed supplement with growing lineages |
| `vendor/iter3_power/power.py` | verbatim copy of iteration-3 `power.py` (sha256 in `SHA256`), imported rather than rewritten |
| `figures.py`, `figures/` | fig1–fig6 plus `figures_manifest.json` (caption, sources, n) |
| `results/*.json` | per-step outputs; `results/old_text_quotes.json` holds the verbatim iteration-3 paper and review sentences |
| `corrections.json` | one entry per must-fix item: old_text (verbatim paper sentence where one exists), corrected_text, numbers, source, status |
| `numbers_ledger_v2.json` | every citable number with its CI, n, target, aggregation, source and v1 status |
| `full_/mini_/preview_eval_out.json`, `eval_out.json` | exp_eval_sol_out; schema-validated |
| `inputs_manifest.json` | path, size, sha256 and top-level keys of every input |

## Run

```bash
bash install.sh                                  # uv venv + pinned deps (requirements_lock.txt)
.venv/bin/python eval.py --skip-power            # every section + figures + assembly (~3 min on 2 CPUs)
.venv/bin/python sections/h_power.py             # optional: rerun the MDE simulation (~8 min)
.venv/bin/python eval.py --assemble-only         # rebuild deliverables from results/
```

All inputs are read-only, from `/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_{1,2,3}`.

## Restoring removed files

`.venv/` is marked `delete: regenerable`. Rebuild it with `bash install.sh`, which runs
`uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r requirements_lock.txt`.
