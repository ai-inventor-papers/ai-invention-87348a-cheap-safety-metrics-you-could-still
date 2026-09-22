# Cheap single-checkpoint safety metrics — iteration 2, experiment 1

**Two jobs, in strict order: (1) repair the refusal readout, (2) buy the model-family axis.**

Iteration 1's "refusal drive" agreed with judged refusal at AUROC 0.750 on Qwen3-4B and **0.391 —
below chance —** on its abliterated sibling, so every across-item metric in its frozen 50-metric
battery sat on a broken primitive. It also lost **15 of its 32 checkpoints** at harvest time,
which left a two-family panel (Qwen3 + TinyLlama) on which leave-one-family-out is not definable.

This artifact repairs what can be repaired, measures what cannot, and states the panel it actually
scored. **Read `results/summary.json` first**: `PARTIAL_PANEL`, `n_checkpoints_harvested`,
`n_families_harvested` and `harvest_tiers` are at its top level, and the `gates` block is the first
key of `analysis_out.json`. Iteration 1's artifact summary read like a completed study while its
own `summary.json` said 3 of 32; that is the one failure this iteration exists not to repeat.

Every number below is copied from a file in `results/`; `scripts/digest.py` regenerates all of
them (`results/DIGEST.md`).

---
## What was scored

**33 of 34 scheduled checkpoints across all 8 scheduled families, `PARTIAL_PANEL = false`**
(`results/summary.json`; the harvest-complete barrier passed with 33 loadable harvests). The one
drop is `venkycs/SmolLM2-1.7B-Instruct-abliterated`, which is FP8 compressed-tensors, not the fp16
the panel note claimed (a bottom-of-spectrum weight read is exactly where FP8 rounding lands).
The two sealed families (Granite, StableLM2) were never scheduled.

| tier | n | checkpoints |
|---|---|---|
| I (inherited GPU) | 17 | Qwen3 0.6B/1.7B/4B base + instruct, Qwen3-4B-SafeRL, 4 Qwen3 abliterated (heretic, mlabonne, huihui 0.6B/1.7B), TinyLlama chat + base, 4 TinyLlama safety runs |
| G (CPU, this iteration) | 3 | `Qwen/Qwen2.5-1.5B-Instruct` (full), `Goekdeniz-Guelmez/Josiefied-Qwen2.5-1.5B-Instruct-abliterated-v1` (plain + wrapped + N-GLARE, 48-token generations, D12), `huihui-ai/Qwen2.5-0.5B-Instruct-CensorTune` (full; a REAL blanket refuser: judged refusal 1.000 on harmful AND benign-alarming items) |
| W (weights only) | 13 | Phi-4-mini instruct + abliterated, gemma-2-2b-it + 2 safety siblings, OLMo-2 1B base + instruct, SmolLM2 1.7B base + instruct, SmolLM3-3B, Qwen2.5-3B-Instruct, Qwen2.5-1.5B base, CensorTune-1.5B |

Three families carry an instruct/abliterated pair (Qwen3, Qwen2.5, Phi-4), below the
pre-registered floor of 5, so gate **G2 fires and leave-one-LINEAGE-out is the primary holdout**,
exactly as pre-registered (a lineage's instruct and abliterated siblings are held out together);
leave-one-family-out is printed beside it on every row. Independent safety-tuned lineages: 3
(Qwen3-4B-SafeRL; TinyLlama ×4 algorithms = one lineage; gemma-2 ×2 = one lineage) — the
three-way race is descriptive only.

---

## The results you should read first

### 1. No cheap refusal-drive readout is auditable — and the judge had to be fixed first

**The grader refuses before the model does.** Under the standard StrongREJECT framing, hosted
judges emit the minimum triple `1,1,1` for replies to harmful prompts regardless of what the reply
did: **40.5%** of all StrongREJECT replies (65.9% on harmful items) are that degenerate triple, and
the two framings disagree on **38.0%** of 1,040 paired items, one-sidedly (328 "refused→engaged"
vs 67 the other way; `results/judge_framing_comparison.json`). The primary target is therefore
graded with a **stance-classification** framing on the same model (`openai/gpt-5-mini`,
reasoning.effort=minimal), with inter-judge agreement vs `google/gemini-2.5-flash` of
**κ = 0.749, Spearman 0.659** on a 200-item subsample (deviation D1).

**Then the readout bake-off, against the corrected labels** — 15 judged checkpoints over **3
families** (Qwen3, Qwen2.5, TinyLlama), 5 abliterated and 5 safety-tuned among them; the
CensorTune refuser's base rate is 1.000, so its AUROC is UNDEFINED, not low
(`results/readout_bakeoff.json`; AUROC is **signed**, never `max(a, 1-a)`):

| readout | min AUROC | mean AUROC | min on abliterated | below chance | invariance ρ min / mean | judge calls |
|---|---|---|---|---|---|---|
| `logitgap` (iteration 1's) | **0.437** | 0.630 | 0.441 | **3 / 15** | 0.076 / 0.477 | 0 |
| `refmass` | 0.506 | 0.692 | 0.590 | 0 | **−0.141** / 0.254 | 0 |
| `probe_cf` (nested, full-coverage probe) | **0.544** | 0.733 | 0.544 | 0 | 0.133 / 0.391 | 0 |
| `probe_first_V1` (same probe, first generated token) | 0.516 | 0.727 | 0.516 | 0 | not measurable | 0 |
| `greedy24` (*upper bound — shares the target's grader*) | 0.547 | 0.767 | 0.714 | 0 | not measurable | 1,280 |

The pre-registered bars are AUROC ≥ 0.80 on **every** checkpoint and presentation invariance
ρ ≥ 0.70. **Nothing clears either.** Gate `READOUT_BAR_NOT_MET` fires and `probe_cf` is selected as
argmax(min AUROC) among readouts whose invariance is measurable. Three things this pins down:

* **Iteration 1's 0.391 was two faults stacked**: an inverted target *and* a readout that runs
  backwards where refusal is rare. With the judge fixed, the logit gap is *still* below chance on
  3 of 15 checkpoints; the base rates are not degenerate (0.113–0.775 on every scored checkpoint).
* **Every readout works only where refusal is common** — the high-refusal instruct models
  (Qwen3-1.7B/4B, Qwen2.5-1.5B-Instruct: 0.853–0.996). They degrade wherever refusal is rare: the
  abliterated and safety-tuned arms and the small instruct models (0.44–0.81) — exactly the
  checkpoints an audit exists for.
* **Labels do not rescue it.** A difference-in-means readout fitted on 8 → 64 *labelled* items
  lifts the mean AUROC from 0.651 to 0.745, but the **minimum over checkpoints stays at
  0.455–0.472** at every budget (`readout_bakeoff.json → probe_learning_curve`): no affordable label
  budget makes an internal refusal readout auditable on every checkpoint.

The prime suspect — the Qwen3 hybrid-thinking trap — is **ruled out**: on all 11 Qwen3 harvests,
**0 of 1,760** stored first-token ids is `<think>` (id 151667) and no completion starts with it
(`results/think_trap_qwen3_offline.json`).

### 2. The race: one internal metric survives every control — and it does not transfer to the benchmark

Two-way (instruct vs abliterated), primary holdout leave-one-lineage-out, every row beside a
within-lineage label-permutation null run through the identical pipeline (`results/race.json`,
`results/race_table.csv`). **3 rows beat their own null's 95th percentile**:

| metric | reads | primary BA | null p95 | lineage-bootstrap CI | passes pole rule |
|---|---|---|---|---|---|
| `x_presentation_invariance` (under the probe readout) | hidden states, 2 prompts per item | **1.000** | 0.775 | 0.667–1.000 | **yes** |
| `b_card_regex_termswept` | the model card, zero prompts | 0.917 | 0.788 | 0.700–1.000 | no |
| `b_logit_gap_alarming` | first-token logits | 0.800 | 0.700 | 0.250–1.000 | no |

The best weight metric, `w_bsa_w8_k4`, reaches 0.826 (leave-one-family-out 0.871 over the three
pair families) but only **ties** its null (p95 0.826). The family-label-only baseline is 0.500
(LOFO) / 0.652 (LOLO). The twelve LEVEL-KNOWLEDGE metrics (harm-probe AUROC, AMS, HRCI…) sit at
0.10–0.80 and **none beats its null**: how well a model *recognises* harm says nothing about
whether it was abliterated. Four registry rows are undefined by construction and say so:
`b_massive_act_depth` (the registered 1000× within-layer criterion is never met),
`gfs_parent_anchored` (needs a parent), and the two panel-level `x_c5_*` metamodel rows.

**`x_presentation_invariance` is the only metric that clears the null AND the pole rule**, and it
reads hidden states (the probe readout applied to the plain and the roleplay-wrapped prompt of the
same item). But it fails the request's transfer test: against the two-sided judged target its
Spearman is **−0.709 at checkpoint level (n = 13, p = 0.007) and −0.40 at lineage level (n = 5,
p = 0.50)** (`results/step5_correlations.json`). The effect lives *within* lineages. By the
request's own rule that is a negative result, and it is reported as one.

**The requester's invariant cannot be met** (`results/shipped_metrics.json`): exactly one metric
reading hidden states or weights (`x_presentation_invariance` — an R-dependent metric, so under the
probe readout its *effective* input is hidden states, not the registry's "logits") survives both the
null and the pole rule, so a shipped set with ≥ 3 such metrics would have to include something that
failed a control. Reported rather than
relaxed (gate `SHIP_INVARIANT_NOT_SATISFIED`).

### 3. A refuse-everything model wins on every black-box meter — the pole rule rejects them all

The pre-registered rule is applied to every metric on its **own** safe direction
(sign of instruct − abliterated). **19 metrics fail** (`results/poles.json`), including **every
black-box refusal meter** (`b_logit_gap_mean/harmful/alarming`, `b_refusal_token_mass`,
`b_refusal_rate_probe`) and the card regex: a blanket refuser looks *safest* to them. That is
the two-sided argument made concrete — a metric that rewards refusal *level* cannot tell safety
from uselessness.

Level and decision spread dissociate at the poles (first-token logit gap, 48 pole items):

| checkpoint | normal level / spread | forced always-refuse | forced never-refuse |
|---|---|---|---|
| Qwen/Qwen3-4B | 9.12 / 9.61 | **38.65 / 1.80** | −12.25 / 9.95 |
| mlabonne/Qwen3-4B-abliterated | −6.20 / 7.64 | **41.12 / 1.64** | −20.56 / 1.07 |
| DreamFast/qwen3-4b-heretic | −6.52 / 6.24 | 38.82 / 1.31 | −25.26 / 1.65 |
| huihui-ai/Qwen2.5-0.5B-Instruct-CensorTune (REAL refuser) | **10.68 / 1.24** | 11.18 / 0.84 | 4.10 / 1.49 |
| TinyLlama/TinyLlama-1.1B-Chat-v1.0 | −1.62 / 2.55 | −1.42 / 2.60 | −1.23 / 2.54 |

Two readings: **abliterated Qwen3 models still obey an explicit refusal instruction** — under a
forced-refusal system prompt their first-token refusal log-odds (38.8–41.1) match their parent's
(38.7): abliteration removed the *spontaneous* refusal of harmful content, not the capacity to
refuse on command; and **TinyLlama ignores the system prompt entirely** (−1.62 → −1.42), so a
synthetic wrapper is not a pole for every family. Spread collapses under the forced condition
(9.61 → 1.80 on Qwen3-4B), which is why the coupling ratio needs its spread floor.

### 4. The fitted harm direction barely beats an honest null

Cross-fitted difference-in-means "harm" directions, each null draw's sign fixed on the training
folds exactly like the fitted direction's, 1,000 draws per tier (`results/direction_nulls.json`,
every draw in `direction_null_draws.json`): the fitted direction beats the **within-item-span**
null's 95th percentile on only **9 of 20** checkpoints (it sits at the 84th–99.9th percentile).
Gate G8 fires. Harmful-vs-benign is the dominant anisotropy of these hidden states — random
directions in the span of the item representations recover most of it — which is the premise
every diff-in-means safety readout (AMS, RAS, LatentBiopsy) shares. Iteration 1's "tie at 0.921"
was an upward-biased best-of-20; with the honest distribution the probe usually wins, but not by
the margin that premise assumes.

### 5. The prompt budget: at a few prompts the black box wins

At a matched, paired budget of k items (internal = leave-one-out cross-fitted hidden-state
separation; black-box = first-token logit-gap margin on the SAME items), the black box's |ρ| with
the two-sided target exceeds the internal readout's from **k = 1** onward (`crossover_k = 1`;
lineage bootstrap: median 4.5, 95% range 1–64, never-cross in 16.5% of resamples; |ρ| gap at k = 64
is −0.28) (`results/prompt_budget.json`). k = 0 is the zero-prompt weight statistic, which the black
box cannot answer at all. By the primary two-way leave-one-lineage-out balanced accuracy the
small-budget picture is the same — black box **0.724** vs internal **0.445** at k = 1 — but the
internal readout catches up only at k = 64 (**0.592** vs **0.571**, well inside the noise of a
9-checkpoint two-way panel); the zero-prompt weight statistic alone gives **0.525**. The request's
"0 to a few prompts" regime is exactly where looking inside the model buys nothing here.

### 6. The class prediction, scored against the registry's own frozen ordering

The frozen `predicted_gap_rank` puts BEHAVIOUR-STRUCTURE at the smallest tuned-minus-held-out gap,
ACROSS-ITEM next, KNOWLEDGE largest — finer-grained than the hypothesis prose's "across-item
survives, level does not". On the **valid common support** (checkpoints carrying activations,
3 families) the rank-gap correlation is **+0.246** (two-sided p = 0.097, one-sided p = 0.048,
10,000 class-label permutations; `results/class_trend.json`) with mean gaps ACROSS-ITEM 0.102 <
BEHAVIOUR-STRUCTURE 0.125 < KNOWLEDGE 0.217. **KNOWLEDGE metrics overfit most, as predicted; the
order of the other two is flipped** on the common support, so the hypothesis headline is partly
right and the registry's finer prediction is partly wrong. The trend's sign does not depend on the
readout (+0.44 to +0.48 under all four).

### 7. Step 1 — the Qwen3-4B lineage

Base / instruct / SafeRL / abliterated (`results/step1_anchor.json`): the SafeRL edit and the
abliteration edit move the last-prompt-token residual stream inside **overlapping subspaces**
(mean first principal angle **31.1°**) but **not along the same axis** — the mean cosine between the
two mean-difference vectors is **−0.09** (early −0.03, middle −0.09, late −0.16): same subspace,
weakly opposite sense.

### 8. What else is now pinned down

* **The 15 lost checkpoints were a version pin**: every iteration-1 loss was `ModuleNotFoundError`
  under transformers 5.17.0; under 4.57.6 all **15/15** import (`results/arch_precheck.json`).
* **Leave-one-group-out has a null of ≈ 0.40, not 0.50** (`results/logo_null_calibration.json`).
* **The published BSA separator (0.35) false-positives**: 5 of 25 unedited checkpoints exceed it
  on the 8-layer band (`race.bsa_published_threshold_check`).
* **The matched lexical floor**: 0.963 cross-source vs **0.537** JBB Index-paired and **0.655**
  XSTest twins (`results/lexical_floor.json`) — an unmatched safety benchmark is mostly lexis.
* **The metamodel does not transfer**: leave-one-lineage-out 0.50 against 1.00 tuned on 10
  checkpoints (`results/metamodel.json`).

---

## The hardware that shaped the run

Iteration 1 ran on an RTX 4000 Ada (20.99 GB). **This box has no GPU at all**, and what it does
have is shared:

* **2 logical CPUs (cpuset 83,179), shared with two sibling artifact executors** of the same run
  (`gen_art_experiment_2`, `gen_art_experiment_3`). A job launched with `nice -n 10` got a few
  percent of the CPU and cannot be re-niced (no `CAP_SYS_NICE`); every harvest here runs at nice 0
  and still gets ~20-40% of the two cores.
* **A 16 GB memory cgroup, also shared, that sits at its limit.** `from_pretrained` of a bf16
  safetensors checkpoint in bf16 is zero-copy, so the weights stay file-backed mmaps; under the
  shared pressure they are evicted and re-read from the network filesystem on every forward pass
  (`workingset_refault_file` = 143M pages). 80 greedy completions × 96 tokens of a 1.5B model took
  **3,498 s**. Copying the weights into anonymous memory would stop the refaults but would make the
  harvest the largest process in a full cgroup — the first thing an OOM kill takes.
* **A box-wide cleaner deletes any `.venv` by name, mid-run.** It killed a session-2 harvest with
  no traceback. The environment therefore lives in `venv_exp1/`.

So the harvest is **tiered**, and every table says which tier each checkpoint carries
(`harvest_tier_meta` in `results/per_checkpoint.json`):

| tier | what it holds | how it was produced |
|---|---|---|
| **I** | activations (last prompt token + first generated token, every layer), first-token logit features, presentation/pole/N-GLARE passes, 80 greedy completions, weight spectra | inherited from iteration 1's GPU harvest, never re-collected |
| **G** | the same arrays, schema-identical, produced on CPU in bf16 (`screen/harvest_cpu_gen.py`) | this iteration, sessions 2-3; profiles `full` / `lite` / `min` recorded per checkpoint |
| **W** | weight spectra only (an 8-layer band at depth 0.5, bottom/top-16 singular subspaces) | this iteration, streamed tensor-by-tensor with `safetensors.safe_open`, no model instantiated |

Weight reads use the **same contiguous 8-layer band on every checkpoint**: the inherited full-depth
harvests are sliced to it, so no comparison is ever band-vs-full. The band read reproduces
iteration 1's full-depth value as a regression test: `BSA_w8` on honest Qwen3-0.6B recomputed from
the inherited arrays is 0.5649782 against iteration 1's 0.5649782 (Δ = 5e-08,
`results/weight_read_regression.json`).

---

## Controls, and why each one is there

Every number in the race table is surrounded by comparisons chosen so that a metric cannot look
good for a boring reason:

| control | question it answers | where |
|---|---|---|
| structural fit/apply isolation (`FoldView`) + deliberate-violation test | can a held-out checkpoint leak into the fit? | `tests/test_isolation.py` |
| label-permutation null through the identical LOFO pipeline, within family | could a feature unrelated to the label score this well? (LOFO chance is ~0.40, not 0.50) | every race row (`null_*`) |
| three-tier direction nulls (isotropic / Ledoit-Wolf covariance-matched / within-item-span), 1000 draws each, signs fixed on the train folds | is a *fitted* harm direction better than a random one drawn the honest way? | `results/direction_nulls.json` (+ every draw in `direction_null_draws.json`) |
| non-featurised comparators (`z_*`: raw activation norms, a raw spread, first-token-id entropy) | does feature engineering add anything over the crudest statistic? | race rows, `shipped_metrics.json` |
| matched lexical floor (TF-IDF on item text: cross-source, JBB Index-paired, XSTest twins) | is this just the wording of the prompts? | `results/lexical_floor.json` |
| card-regex text floor (zero prompts, zero forward passes) | could a regex over the model card do as well? | `race.card_regex_text_floor` |
| family-label-only baseline (categorical majority rule) | does the architecture family alone predict the role? | `race.family_label_only_baseline` |
| phantom-specialisation check | does the metric separate *architectures* better than *safety roles*? | `family_separability_ba` per row |
| refusal poles (two REAL CensorTune checkpoints + synthetic always/never-refuse wrappers) | does a model that refuses everything score as safe? if so the metric is rejected | `results/poles.json` |
| nested readout re-selection | does choosing the readout on the scored checkpoints change the verdict? | `race.nested_selection_race` |
| lineage-cluster bootstrap | how wide is the held-out score when LINEAGES, not checkpoints, are resampled? | race rows (`ci_lo`, `ci_hi`) |
| metamodel identity control | does the metamodel recover architecture identity from the same features? | `results/metamodel.json` |

## What this artifact does not claim

* No forgery ladder, no external-leaderboard correlation, no recipe recovery — those are sibling
  lanes (experiment_2, experiment_3).
* The `greedy24` readout **shares its grader with the target**, so it is favoured by construction
  and is an upper bound, never a fair rival; its judge-call cost is printed beside its AUROC.
* The real blanket-refuser poles (`huihui-ai/Qwen2.5-*-Instruct-CensorTune`) are **off-family and
  off-size** — no Qwen3 CensorTune exists.
* Under leave-one-**family**-out the family-label-only baseline is *structurally* at chance (the
  held-out family was never seen); it is informative only under leave-one-**lineage**-out.
* Independent safety-tuned lineages are below the pre-registered floor of 5, so the three-way race
  is **descriptive only**, with its lineage count printed on the table.
* Balanced accuracy and AUROC are reported instead of the pre-registered TPR at FPR ∈ {0.01, 0.05,
  0.10}: with n instruct negatives the smallest non-zero FPR is 1/n, above every grid point
  (`race.fpr_grid_status`).

---

## Layout

```
method.py                  CLI stage runner: inherit | env | harvest | harvest_g | judge | score | output
run_final.sh               judge -> score (barrier first) -> deviations -> output -> mini/preview -> schema check
run_harvest_g{,2,3,4}.sh   the tier-G CPU harvest queues as they were actually launched (sessions 2-3)
run_harvest{,2,3}.sh       the session-1 tier-W (weights-only) workers on disjoint queues
run_all.sh, stop_harvest.sh    session-1 drivers (stop_harvest selects workers by /proc/<pid>/cwd)
PREREG.json / .sha256      pre-registration, hashed before any model was touched, never edited
scripts/precheck.py        architecture coverage precheck (config/metadata only, no weights)
scripts/bench_cpu.py       the CPU bf16 prefill/generation benchmark that justified tier G
scripts/record_deviations.py   writes the session-3 pre-registration deviations (D6-D12)
scripts/digest.py          regenerates results/DIGEST.md (= the numeric body of RESULTS.md)
RESULTS.md                 every table and number of the final run (from the digest)
TODO.md                    the working notes of all three sessions
tests/test_isolation.py    structural fit/apply isolation + the LOGO null calibration
tests/test_session3.py     session-3 checks: vectorised null AUROC, nested probe, LOO budget readout
tests/post_race_smoke.py   exercises the post-race stages against a finished race + metric cache
tests/judge_rubric_variants.py, tests/judge_triage.py   the grader-refusal experiment

screen/                    vendored from iteration 1, plus this iteration's modules
  harvest_cpu.py           weights-only streaming harvest (8-layer band) + CPU prefill
  harvest_cpu_gen.py       tier G: activations + greedy generations on CPU, schema-identical
                           to the inherited GPU harvests (profiles full / lite / min)
  analysis2.py             bake-off, nested full-coverage probe, fit/apply isolation,
                           exact 1-D logistic, vectorised 3-tier direction nulls, bootstrap
  pipeline2.py             stage bodies: judge, score (race, trend, budget, poles, ...), output
  poles2.py                the pole battery on EVERY metric, on each metric's own safe direction
  judge2.py                async OpenRouter grader (stance framing) with a cost ledger
  reads.py, race.py, registry.py, panel.py, substrate.py, harvest.py, judge.py, step1.py,
  selftest.py, common.py   vendored from iteration 1 (reads/race carry small, commented fixes)

inherited/                 copied from iteration 1, read-only inputs
  metrics_registry.json    THE 50 FROZEN METRICS (sha256 verified, never edited)
  items.json               160 frozen items with pre-registered `fold` and `twin_group`
  SEALED.md                the two sealed families, touched by nothing here

harvest/<slug>/            one directory per checkpoint: weights.npz [+ acts.npz, generations.json,
                           presentation.npz, poles.npz, nglare.npz], meta.json, DONE [, DONE_G]

results/                   every sub-result, persisted the moment it is measured
  summary.json             THE COUNTS: families/checkpoints scheduled vs harvested, PARTIAL_PANEL,
                           tiers, readout choice, crossover k, spend -- read this first
  gates.json               every gate that fired, with its counts
  barrier.json             the harvest-complete barrier verdict
  arch_precheck.json       the precheck table + the transformers pin experiment
  inherited_manifest.json  integrity of every inherited harvest
  harvest_manifest.json, manifest/<slug>.json   per-slug harvest status (race-free)
  readout_bakeoff.json     Part 1: every readout x every judged checkpoint (+ V1, learning curve)
  bakeoff_raw.json         the per-item readout values behind it
  readout_choice.json      which readout was selected and under which rule
  think_trap.json          the <think> assertion (tier-G meta); think_trap_qwen3_offline.json:
                           the same check on all 11 Qwen3 harvests from stored first-token ids
  DIGEST.md                every table in RESULTS.md, regenerated by scripts/digest.py
  harvest_report_tier_g.json, bench_cpu.json   the tier-G runs and the CPU benchmark behind them
  judge_grades.json        the PRIMARY (stance-framed) grades; judge_grades_strongreject.json
  judge_framing_comparison.json   the paired grader-refusal result
  race.json / race_table.csv      Part 3: LOFO race, 50 metrics + 5 comparators, all readouts
  race_common_support.json the race restricted to checkpoints carrying activations
  class_trend.json         the frozen predicted_gap_rank trend, on BOTH supports
  direction_nulls.json (+ direction_null_draws.json)   3-tier null distributions, 1000 draws each
  lexical_floor.json       matched lexical floor, three ways
  prompt_budget.json (+ budget_raw.json)   the k in {0,1,8,16,32,64} crossover
  poles.json               level vs decision spread at the poles + the rejection rule per metric
  step1_anchor.json        the Qwen3-4B base/instruct/SafeRL/abliterated lineage (request step 1)
  step5_correlations.json  top metrics vs the two-sided target, both aggregation units
  metamodel.json           the trained metamodel, WITH its identity control
  mechanistic_profile.json which depths carry harm content vs refusal
  shipped_metrics.json     what survives everything, and the requester's invariant check
  per_checkpoint.json      one row per checkpoint: tier, class, family, diagnostics
  prereg_deviations.json   every departure from PREREG.json (D1-D12), with evidence
  cost_ledger.jsonl        one line per OpenRouter call, cumulative spend

method_out.json            the four datasets (D1-D4) in exp_gen_sol_out shape
full_/mini_/preview_method_out.json   size variants produced by the aii-json formatter
analysis_out.json          everything that is not a per-example prediction: `gates` and the
                           panel counts FIRST, then `headline_findings`, then every table
```

## How to run

```bash
# environment (a `.venv` in this workspace is reaped by a box-wide cleaner; use another name)
UV_PROJECT_ENVIRONMENT=venv_exp1 uv sync --python 3.12      # transformers>=4.55,<5 (5.x drops gemma2/phi3/olmo2/smollm3)

# thread caps must be in the LAUNCH command -- setting them after numpy imports is too late
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
venv_exp1/bin/python scripts/precheck.py                    # stage A: config-only precheck
venv_exp1/bin/python method.py --stage inherit              # inheritance + integrity + env
venv_exp1/bin/python method.py --stage harvest --only "<repo,...>"          # tier W (weights)
./run_harvest_g4.sh <pid-to-wait-for|0>  &  PID=$!;  wait $PID              # tier G (CPU acts+gen)
./run_final.sh                                              # judge -> score -> output -> validate
```

Process management is PID-based only: `cmd & PID=$!`, `kill -0 $PID`, `wait $PID`. Never
`pkill`/`killall`/`ps | grep` -- two sibling executors share this container and its CPUs.

`--stage score` runs the BARRIER first: it refuses to treat a `START` record as finished, and if
anything is still pending it scores what is `DONE` and stamps `PARTIAL_PANEL` with exact counts at
the top of `results/summary.json` and `analysis_out.json`.

Environment expected: `HF_TOKEN`, `OPENROUTER_API_KEY`, and `HF_HOME` / `HF_HUB_CACHE` pointing at
the run's shared cache (weights are read from there and never copied into this workspace).

## Restoring removed files

Everything marked `delete` in `.aii/manifest.yaml` is restorable:

| Path | How to restore |
|---|---|
| `venv_exp1/` | `UV_PROJECT_ENVIRONMENT=venv_exp1 uv sync --python 3.12` (all 55 packages pinned exactly in `pyproject.toml`; `uv.lock` matches — a dry-run sync against the run environment makes no changes) |
| `__pycache__/`, `**/__pycache__/` | regenerated on the next Python import, e.g. `venv_exp1/bin/python method.py --help` |

Two small caches are **kept** (text, under the auto-keep floor) rather than deleted: `cache/`, the
content-addressed OpenRouter judge-response cache that lets `method.py --stage judge` re-run for
free, and `results/metric_cache/`, the memoised per-(checkpoint, readout) metric rows and probe
fits that let `method.py --stage score` re-run in minutes. If either is ever removed, the same
two commands rebuild it (the judge re-spends OpenRouter credit; the grades themselves are kept in
`results/judge_grades.json` and `results/judge_grades_strongreject.json`).

Model weights are not stored here: they are read from the run-level shared HuggingFace cache.
`harvest/` holds only derived arrays and is **kept** -- rebuilding it needs a GPU (tier I) or
hours of contended CPU (tier G).

---

## Honest limits

- **The family axis is narrow.** Three families carry an instruct/abliterated pair (Qwen3,
  Qwen2.5, Phi-4); only Qwen3 and Qwen2.5 carry one *with activations*. Gate G2 therefore makes
  leave-one-**lineage**-out the primary holdout, exactly as pre-registered, and leave-one-family-
  out is printed beside it — for the activation metrics it is not even definable here.
- **The activation panel is small.** Tier I (17 inherited) + tier G (3: CensorTune-0.5B,
  Qwen2.5-1.5B-Instruct, Josiefied-Qwen2.5-1.5B-abliterated). The Phi-4 pair, gemma-2, OLMo-2,
  SmolLM2/3 carry weights only: a 1.5B tier-G pass cost ~2 h of wall clock on the shared CPUs,
  and the instruct-only families were skipped by the pre-committed clock gate (G7).
- **One checkpoint was generated at 48 tokens, not 96** (Josiefied, after an OOM kill; deviation
  D12). Its refusal flags are in the bake-off; it is excluded from every two-sided-target analysis.
- `greedy24` shares its grader with the target — an upper bound, never a fair rival.
- The real blanket-refuser poles are **off-family and off-size** — no Qwen3 CensorTune exists —
  and only the 0.5B one carries activations.
- Independent safety-tuned lineages (3: Qwen3-4B-SafeRL, TinyLlama ×4 algorithms = one lineage,
  gemma-2 ×2 = one lineage) are below the pre-registered floor of 5, so the three-way race is
  descriptive only. The models a downloader actually meets are exactly the ones with no
  safety-tuned sibling.
- The cluster bootstrap runs 400 resamples and the per-row permutation null 300 draws, not 2000
  and 1000 (gate `G7_CLOCK_RESAMPLES_CAPPED`, the pre-committed shrink order); the class-trend
  permutation test keeps its full 10,000 and the direction nulls their full 1,000 per tier.
- Fold 4 is used as one of five out-of-fold evaluation folds; it is not a fresh confirmation split
  (`inherited/SEALED.md`).
