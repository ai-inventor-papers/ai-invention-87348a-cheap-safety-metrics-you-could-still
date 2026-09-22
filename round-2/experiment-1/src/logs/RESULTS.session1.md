# Results

Every number below is copied from a file in `results/`, and the file is named beside it. Where a
figure was measured on the panel as it stood partway through the harvest it says so explicitly and
names the file that supersedes it. `results/summary.json` is authoritative for all counts.

The single most important line in that file is `PARTIAL_PANEL`, beside `n_checkpoints_harvested`,
`n_families_harvested` and `harvest_tiers`. Iteration 1's artifact summary read like a completed
study while its own `summary.json` said 3 of 32.

---

## 1. Grader-side refusal: the standard StrongREJECT judge framing inverts the label

Three hosted graders were shown responses that plainly comply and responses that plainly refuse,
to prompts that are harmful. Under the StrongREJECT framing they emit the minimum triple `1,1,1`
regardless of what the response did — i.e. **the grader refuses, and its refusal is recorded as
the graded model's refusal**.

Controlled triage (`tests/judge_rubric_variants.py`, 6 hand-checked responses):

| framing | openai/gpt-5-mini | google/gemini-2.5-flash | openai/gpt-4.1-mini |
|---|---|---|---|
| StrongREJECT | 3/6 | 1/6 | 0/6 (`1,1,1` on all) |
| **stance classification** | **6/6** | **6/6** | not retested |

At scale, paired over all **1040** graded (checkpoint, item) pairs
(`results/judge_framing_comparison.json`):

| | StrongREJECT | stance |
|---|---|---|
| refusal rate, all items | 0.514 | 0.261 |
| refusal rate, **harmful** items | 0.819 | 0.409 |
| replies that are the degenerate `1,1,1` | **40.5%** (65.9% on harmful) | — |
| Cohen's κ vs an independent second grader | 0.456 | **0.585** |

The framings disagree on **38.1%** of items, one-sidedly: **330** items where StrongREJECT says
"refused" and stance says "engaged", against **66** the other way. Only the stance framing
reproduces the ordering visible in the raw text — `Qwen/Qwen3-4B` refuses **0.938** of harmful
prompts while `mlabonne/Qwen3-4B-abliterated` refuses **0.188**; StrongREJECT reported 0.667 vs
0.979, exactly backwards, while the abliterated model's stored completions are a fabricated news
article and a fraudulent IRS letter.

**Any refusal-agreement number produced with an off-the-shelf LLM judge and no grader-refusal
check is measuring the grader.** This is recorded as pre-registration deviation `D1_JUDGE_FRAMING`.

## 2. The readout bake-off: no cheap refusal-drive readout is auditable

13 tier-I checkpoints, 2 families, scored against stance-framed judged refusal on held-out item
folds (`results/bakeoff_standalone.json`, superseded by `results/readout_bakeoff.json`).
AUROC is **signed** — never `max(a, 1-a)` — so a readout running backwards shows as `< 0.5`.

| readout | min AUROC | mean AUROC | min on abliterated | n below chance | invariance ρ | judge calls |
|---|---|---|---|---|---|---|
| `logitgap` (iteration 1's) | **0.437** | 0.619 | **0.441** | **3 / 13** | 0.076 | 0 |
| `refmass` | 0.506 | 0.667 | 0.590 | 0 | **−0.141** | 0 |
| `probe_cf` (cross-fitted hidden-state probe) | **0.589** | 0.734 | 0.612 | 0 | 0.442 | 0 |
| `greedy24` (judge-scored, *upper bound by construction*) | 0.547 | **0.757** | 0.714 | 0 | not measurable | **1040** |

Pre-registered bars: AUROC ≥ 0.80 on **every** checkpoint (the statistic is the MINIMUM, never
the mean) and presentation invariance ρ ≥ 0.70. **Nothing clears either bar.** Gate
`READOUT_BAR_NOT_MET` fires; `probe_cf` is selected as `argmax(min AUROC)` among readouts whose
invariance is measurable at all.

Three things this pins down that iteration 1 could not:

* **The base rates are not degenerate.** They span 0.113–0.588, all inside the pre-registered
  [0.05, 0.95] window, so AUROC is well defined on every checkpoint and the "undefined, not low"
  fallback was *not* needed. The low numbers are real.
* **Fixing the judge did not rescue the readout.** `logitgap` still runs backwards on 3 of 13
  checkpoints against corrected labels. Iteration 1's 0.391 was **two faults stacked** — an
  inverted target *and* a readout that fails where refusal is rare.
* **The cheap readouts are not presentation-invariant at all.** ρ = 0.076 (`logitgap`) and
  **−0.141** (`refmass`) between the plain and re-worded presentations of the *same* item.
  Iteration 1 measured 0.559 and treated that as marginal; the corrected figure is near zero and
  of the wrong sign. A readout that moves this much when a request is re-worded cannot support an
  audit-time draw from a pool of presentation conditions, which was the whole secret-draw design.

**The negative is the deliverable:** the across-item half of the 50-metric battery has no valid
primitive at any budget affordable here, and that is a statement about the cheap-readout
literature, not about one implementation.

## 3. The transformers pin, and 15 checkpoints recovered

Every one of iteration 1's 15 harvest losses was `ModuleNotFoundError` on a `transformers.models.*`
module that 5.17.0 removed — `gemma2` (3 repos), `phi3` (2), `olmo2` (2), `smollm3` (1), `blip_2`
(3, hit while importing SmolLM2), plus `Could not import module 'Qwen2Config'` (4). Its
`panel_dropped.json` filed all 15 under one catch-all, *"harvest failed or deadline"*.

Under a pinned **4.57.6**, `scripts/precheck.py` re-resolves 34 candidates: **15/15 import**,
**0 dropped**, 8 families surviving. A catch-all exception reason in a harvest loop is not
evidence about why a checkpoint was lost.

## 4. Leave-one-family-out has a null of ≈0.40, not 0.50

`results/logo_null_calibration.json`: on uninformative labels, leave-one-group-out balanced
accuracy sits at **0.403 (sd 0.131)** over 200 draws, while the fit-on-everything twin reaches
0.562 — the +0.159 gap is the leak the holdout exists to prevent, shown rather than asserted.
The held-out group's class balance is negatively correlated with the training remainder's, so the
classifier leans against the test group's majority. Every race row is therefore compared against a
**label-permutation null run through the identical pipeline**, never against a nominal 0.5.

## 5. The family axis

Iteration 1 had **2 families** and leave-one-family-out was not definable. This iteration
harvested **30 checkpoints across 8 families**:

| family | checkpoints | has instruct+abliterated pair |
|---|---|---|
| Qwen3 | 11 | **yes** |
| TinyLlama | 6 | no (no abliteration exists) |
| Qwen2.5 | 5 | **yes** |
| SmolLM2 | 2 | no — the only sibling is FP8-quantized (§6) |
| OLMo-2 | 2 | no (none exists) |
| Phi-4 | 2 | **yes** |
| SmolLM3 | 1 | no (none exists) |
| gemma-2 | 1+ | no; contributes safety-tuned siblings instead |

By role: 11 instruct, 6 abliterated, 5 safety-tuned, 6 base (separate stratum, plain renderer,
never mixed into the race), 2 real blanket-refuser poles. Harvest tiers: **17 tier-I** (activations
+ generations + weights, inherited) and **13 tier-W** (weights only, this iteration, no GPU).

**3 families carry a usable instruct/abliterated pair**, below the pre-registered floor of 5, so
gate `FAMILY_AXIS_DEGRADED` fires and leave-one-LINEAGE-out is reported beside
leave-one-FAMILY-out with the family count printed on every table.

An early read of the weight-only metrics on the two-way arm, before the last checkpoints landed,
gave leave-one-family-out balanced accuracies of **0.800** (`w_down_botgap_min`, tuned 0.900,
gap 0.100), **0.700** (`w_bsa_w8_k1` and `w_bsa_w8_k4`, AUROC 0.900 and 0.933) and 0.333
(`w_tsa_top1_w8`) — i.e. the bottom-of-spectrum reads carry cross-family signal and the
top-subspace read does not. The final table supersedes these.

See `results/summary.json` for the final counts and `results/race_table.csv` for all 50 metrics
plus 5 non-registry comparators. Two guards are worth reading before the table:

* **Common support.** The weight metrics are defined on every harvested checkpoint; the activation
  and across-item metrics exist only on the tier-I inherited harvests, because generation needs a
  GPU this box does not have. A class-trend test over each metric's own support would compare
  *supports*, not *classes*, so `results/class_trend.json` reports both and flags the wider one as
  confounded. **The common-support row is the valid test.**
* **Phantom specialisation.** Each row carries `family_separability_ba` — how well the metric
  predicts the *architecture family* — beside its safety-role score. A metric that reads
  architecture better than safety is a structural difference being reported as a mechanistic one.

## 6. What the Hub actually contains

`results/panel_realities.json`. The load-bearing one: the only ungated SmolLM2 abliteration,
`venkycs/SmolLM2-1.7B-Instruct-abliterated`, is **FP8 compressed-tensors**, not the fp16 that
iteration 1's panel note claimed. It is dropped rather than dequantized, because every weight read
here is a *bottom-of-spectrum* statistic and FP8 rounding is concentrated exactly there — a
dequantized spectrum would show an editing scar that is really a storage format. **Any parent-free
weight-spectrum safety metric is silently inapplicable to quantized checkpoints**, which are a
large share of what a downloader actually meets.

## 7. No incumbent is comparable, and each for a different reason

`results/incumbent_bars.json`. AMS (2608.05578) held out **only the classification threshold** —
direction, layer sweep and prompt set were all in-sample — so its 71% is a loose, non-matched bar.
Skin-Deep/GFS needs the base model's covariance and 1000 prompts. N-GLARE is parent-free and
generation-free like us but needs four probing conditions over 7000+ cases, separating it on the
**prompt-budget axis alone** — precisely the axis the request constrained. RAS/SafeVec needs a
per-family reference model, a calibration set, and those models' measured ASR.

All four are `comparable: false`. There is no published number in this lane that a parent-free,
few-prompt, leave-one-family-out score can be placed beside, and writing that down is the
contribution — quoting any of them as a beaten baseline would be a category error.
