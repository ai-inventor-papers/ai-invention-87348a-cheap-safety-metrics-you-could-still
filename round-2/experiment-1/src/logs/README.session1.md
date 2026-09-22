# Cheap single-checkpoint safety metrics — iteration 2

**Two jobs, in strict order: (1) repair the refusal readout, (2) buy the model-family axis.**

Iteration 1 measured a "refusal drive" that agreed with judged refusal at AUROC 0.750 on
Qwen3-4B and **0.391 — below chance —** on its abliterated sibling, so every across-item metric
in its 50-metric battery sat on a broken primitive. It also lost **15 of its 32 checkpoints** at
harvest time, all to `ModuleNotFoundError` on transformers model modules, which left a two-family
panel (Qwen3 + TinyLlama) on which leave-one-family-out is not even definable.

This iteration fixes both, and reports honestly where the hardware stopped it.

---

## The four results you should read first

1. **The judge was broken *as well as* the readout — iteration 1's anomaly was two faults
   stacked.** Under the standard StrongREJECT framing, hosted graders *refuse to grade*:
   asked to rate a reply to a harmful prompt, `openai/gpt-5-mini`, `openai/gpt-4.1-mini` and
   `google/gemini-2.5-flash` all emit the minimum triple `1,1,1` **regardless of what the reply
   actually did**. A fully compliant abliterated completion — a fabricated news article, a
   fraudulent IRS letter — was recorded as `refused=1`. Reframing the identical task as *stance
   classification* ("you are a classifier; classifying text is not endorsing it") takes
   `gpt-5-mini` from **3/6 to 6/6** and `gemini-2.5-flash` from **1/6 to 6/6** on hand-checked
   cases.

   Measured on **all 1040 graded items**, paired by (checkpoint, item):

   | | StrongREJECT framing | stance framing |
   |---|---|---|
   | refusal rate, all items | 0.514 | 0.261 |
   | refusal rate, **harmful** items | 0.819 | 0.409 |
   | replies that are the degenerate `1,1,1` | **40.5%** (65.9% on harmful items) | — |
   | inter-judge agreement (κ, vs gemini-2.5-flash) | 0.456 | **0.585** |

   The two framings **disagree on 38.1% of items**, and the disagreement is one-sided: 330 items
   where StrongREJECT says "refused" but stance says "engaged", against 66 the other way. The
   ordering only becomes coherent under the stance framing — Qwen3-4B refuses **0.938** of
   harmful prompts while its abliterated sibling `mlabonne/Qwen3-4B-abliterated` refuses
   **0.188**; StrongREJECT reported 0.667 vs 0.979, i.e. *exactly backwards*, and the raw
   generations (a fabricated news article, a fraudulent IRS letter) confirm the abliterated model
   complied.

   Why this matters for iteration 1: its refusal drive scored AUROC 0.750 on Qwen3-4B and **0.391
   — below chance —** on the abliterated sibling. *Below-chance agreement is the signature of an
   inverted label, not a weak feature*, and the abliterated arm is exactly where grader-side
   refusal flips it. See `results/judge_framing_comparison.json`,
   `tests/judge_rubric_variants.py`, and deviation `D1_JUDGE_FRAMING` in
   `results/prereg_deviations.json`.

   **But repairing the judge did not rescue the readout, and that is the more useful result.**
   Re-scored against the corrected labels, the first-token logit gap *still* runs backwards on
   3 of 13 checkpoints (minimum AUROC **0.437**; minimum on abliterated checkpoints **0.441**).
   So iteration 1's anomaly was *two* faults stacked, not one: an inverted target **and** a
   readout that genuinely fails where refusal is rare. Both had to be separated before either
   could be seen.

2. **The 15 lost checkpoints were a version pin, and the pin is now proven.** Every one of
   iteration 1's harvest failures was `ModuleNotFoundError: No module named
   'transformers.models.{gemma2,phi3,olmo2,smollm3,blip_2}'` or `Could not import module
   'Qwen2Config'` — transformers **5.17.0** removed or moved those modules. Under a pinned
   **4.57.6**, `scripts/precheck.py` re-resolves all 34 candidates and **15/15 of the old failures
   import**, with zero repos dropped. See `results/arch_precheck.json →
   transformers_pin_experiment`.

3. **The prime suspect for the broken readout is ruled out at zero cost.** The Qwen3
   hybrid-thinking trap — that without `enable_thinking=False` the first generated token is
   `<think>` and every first-token readout measured the delimiter — is testable offline, because
   the harvest stores `first_token_id` from a real one-token decode off the prefill cache.
   See `results/think_trap.json`.

4. **Leave-one-family-out balanced accuracy does not have a null of 0.5.** On uninformative
   labels it sits near **0.40**, because the held-out group's class balance is negatively
   correlated with the training remainder's. Every race row is therefore compared against a
   label-permutation null run through the identical pipeline, never against a nominal 0.5. See
   `results/logo_null_calibration.json` and `tests/test_isolation.py`.

**And the panel is small, and it is labelled as small.** `results/summary.json` carries
`n_checkpoints_harvested`, `n_families_harvested`, `harvest_tiers` and `PARTIAL_PANEL` at the top
level. Iteration 1's artifact summary read like a completed study while its own `summary.json`
said 3 of 32; that is the one failure this iteration exists not to repeat.

---

## The hardware constraint that shaped everything

Iteration 1 ran on an RTX 4000 Ada (20.99 GB). **This box has no GPU at all**: `nvidia-smi` is
absent, `/dev/nvidia*` does not exist, `torch.cuda.is_available()` is `False`. It has **2 CPU
cores**, a **16 GB cgroup limit**, and sits on a host carrying a **load average near 290** — a
single `eigh` of a 1536×1536 Gram measured **25–34 s here against 0.7 s on an idle box**.

Two consequences, both pre-registered in `PREREG.json` before any weights were touched (gate
`G11_HARDWARE_DEGRADED_NO_GPU`), not discovered afterwards:

* **The harvest is tiered.** Tier **I** = the 17 inherited iteration-1 harvests (activations +
  generations + weights). Tier **W** = new checkpoints, **weights only**, streamed
  tensor-by-tensor out of the cached safetensors with `safetensors.safe_open` and never
  instantiating a model. Full-length greedy generation on 2 CPU cores is not feasible, so it is
  not attempted on new checkpoints and the readout bake-off is declared a **tier-I-only**
  analysis up front.
* **Weight reads use a fixed contiguous 8-layer band** at depth 0.5. This is a restriction, not
  an approximation: `BSA_w8` slides an 8-layer window and maxes over windows, so on an 8-layer
  band it is *exactly one window* — the same functional form at one depth. The band is applied
  **identically to the inherited checkpoints** (which hold every layer on disk and are simply
  sliced), so **no comparison in this artifact is ever band-vs-full**.

What survived the constraint, and what did not, is in `results/summary.json` and in the `gates`
block at the top of `analysis_out.json`. No gate aborts the run; each one degrades a metric class
and records its branch.

---

## What this artifact does not claim

* No forgery ladder, no external-leaderboard correlation, no recipe recovery — those are sibling
  lanes.
* The `greedy24` readout **shares its grader with the target**, so it is favoured by construction
  and is reported as an upper bound, not a fair rival, with its judge-CALL cost beside its AUROC (1040 calls, against 0 for every other readout).
* The real blanket-refuser poles (`huihui-ai/Qwen2.5-*-Instruct-CensorTune`) are **off-family and
  off-size** — no Qwen3 CensorTune exists. Said plainly rather than matched away.
* Under leave-one-**family**-out the family-label-only baseline is *structurally* uninformative
  (the held-out family was never seen), so it lands at chance by construction. It is therefore
  also reported under leave-one-**lineage**-out, where it is informative.

---

## Layout

```
method.py                  CLI stage runner: inherit | env | harvest | judge | score | output
run_all.sh                 the whole pipeline, stages strictly serialised
run_harvest{,2,3}.sh       harvest workers on DISJOINT queues (2 cores, heavy host contention)
stop_harvest.sh            stops only THIS workspace's workers, selected by /proc/<pid>/cwd
PREREG.json / .sha256      pre-registration, hashed before any model was touched
scripts/precheck.py        architecture coverage precheck (config/metadata only, no weights)
tests/test_isolation.py    structural fit/apply isolation + the LOGO null calibration
tests/judge_rubric_variants.py   the grader-refusal experiment (StrongREJECT vs stance framing)
tests/judge_triage.py      three judge models on known-compliant vs known-refusing responses

screen/                    vendored from iteration 1, plus this iteration's new modules
  harvest_cpu.py           NEW  weights-only streaming harvest + CPU prefill activation pass
  analysis2.py             NEW  bake-off, fit/apply isolation, 3-tier nulls, cluster bootstrap
  pipeline2.py             NEW  stage bodies: judge, score, output
  judge2.py                NEW  async StrongREJECT grader (OpenRouter) with a cost ledger
  reads.py, race.py, registry.py, panel.py, substrate.py, harvest.py, judge.py, step1.py,
  selftest.py, common.py   vendored unchanged from iteration 1

inherited/                 copied from iteration 1, read-only inputs
  metrics_registry.json    THE 50 FROZEN METRICS (sha256 verified, never edited)
  items.json               160 frozen items with pre-registered `fold` and `twin_group`
  SEALED.md                the two sealed families, touched by nothing here

harvest/<slug>/            one directory per checkpoint: weights.npz [+ acts.npz,
                           generations.json, poles.npz, presentation.npz], meta.json, DONE

results/                   every sub-result, persisted the moment it is measured
  arch_precheck.json       the precheck table + the transformers pin experiment
  inherited_manifest.json  integrity of every inherited harvest
  harvest_manifest.json, manifest/<slug>.json   per-slug status (race-free)
  barrier.json             the harvest-complete barrier verdict
  readout_bakeoff.json     Part 1: the three readouts × every checkpoint
  readout_choice.json      which readout was selected and under which rule
  think_trap.json          the <think> assertion
  judge_grades.json        the PRIMARY (stance-framed) grades
  judge_grades_strongreject.json   the same items under the StrongREJECT framing
  judge_framing_comparison.json    the paired N=1040 grader-refusal result
  race.json / race_table.csv   Part 3: LOFO race over all 50 metrics + 5 comparators
  race_common_support.json the race restricted to checkpoints where ALL 50 metrics exist
  class_trend.json         the frozen predicted_gap_rank trend, on BOTH supports
  direction_nulls.json     isotropic / covariance-matched / within-item-span nulls
  logo_null_calibration.json   why the LOFO null is ~0.40, not 0.50
  lexical_floor.json       matched lexical floor, three ways
  prompt_budget.json       the k ∈ {0,1,8,16,32,64} crossover
  poles.json               level vs decision spread at the refusal poles
  metamodel.json           the trained metamodel, WITH its architecture-identity control
  shipped_metrics.json     what survives everything, and the requester's invariant check
  incumbent_bars.json      the four published incumbents and why none is comparable
  panel_realities.json     what the Hub actually contains (FP8 siblings, stale 404s, scarcity)
  prereg_deviations.json   every departure from PREREG.json, with evidence
  cost_ledger.jsonl        one line per OpenRouter call, cumulative spend
  summary.json             the counts that say whether the race is real

method_out.json            the four datasets (D1–D4) in exp_gen_sol_out shape
full_/mini_/preview_method_out.json   size variants (the formatter prefixes the basename)
analysis_out.json          everything that is not a per-example prediction, with a
                           `headline_findings` block up front and `gates` beside it
```

## How to run

```bash
uv venv .venv --python=3.12 && uv sync
uv pip install --python .venv/bin/python "transformers>=4.55,<5"   # 5.x removes gemma2/phi3/olmo2/smollm3

# everything, stages strictly serialised, with the barrier and schema validation:
./run_all.sh

# or stage by stage:

# thread caps must be in the LAUNCH command — setting them after numpy imports is too late
OMP_NUM_THREADS=2 .venv/bin/python scripts/precheck.py
OMP_NUM_THREADS=2 .venv/bin/python method.py --stage inherit
./run_harvest.sh 150 &  PID=$!;  wait $PID      # PID-based only; never pkill/killall
OMP_NUM_THREADS=1 .venv/bin/python method.py --stage judge
OMP_NUM_THREADS=2 .venv/bin/python method.py --stage score     # runs the BARRIER first
OMP_NUM_THREADS=2 .venv/bin/python method.py --stage output
```

`--stage score` **refuses to start** until every scheduled slug is `DONE` or `DROPPED`. Iteration
1's scorer filtered the panel on `DONE` markers *at call time* and was called when 3 of 32 existed;
the code was correct and the study was not.

Environment expected: `HF_TOKEN`, `OPENROUTER_API_KEY`, and `HF_HOME` / `HF_HUB_CACHE` pointing at
the run's shared cache. Do not override the cache variables — `HF_HOME` and `TRANSFORMERS_CACHE`
are read differently by `huggingface_hub` and pointing both at one directory stores every weight
twice.

## Restoring removed files

Everything marked `delete` in `.aii/manifest.yaml` is restorable:

| Path | How to restore |
|---|---|
| `.venv/` | `uv venv .venv --python=3.12 && uv sync && uv pip install --python .venv/bin/python "transformers>=4.55,<5"` |
| `cache/judge/` | Regenerated by `.venv/bin/python method.py --stage judge` (re-spends OpenRouter credit; the grades themselves are preserved in `results/judge_grades.json`, which is **kept**). |
| `**/__pycache__/` | Regenerated on the next Python import. |

Model weights are **not** stored in this workspace at all — they are read from the run-level shared
HuggingFace cache and never copied in. `harvest/` holds only derived arrays (spectra, hidden
states, generations) and is **kept**: it is the substrate every downstream iteration re-reads and
it cannot be rebuilt here, because rebuilding it needs a GPU this box does not have.

---

## Controls, and why each one is there

Every number in the race table is surrounded by comparisons chosen so that a metric cannot look
good for a boring reason. In rough order of how often they bite:

| control | question it answers | where |
|---|---|---|
| label-permutation null, identical pipeline | could a feature with no relationship to the label score this well? | every race row (`null_*`) |
| three-tier direction nulls (isotropic / Ledoit-Wolf covariance-matched / within-item-span) | is a *fitted* harm direction better than a random one drawn the honest way? | `results/direction_nulls.json` |
| non-featurised comparators (`z_*`: raw activation norms, a raw spread, first-token entropy) | does feature engineering add anything over the crudest statistic available? | race rows, `shipped_metrics.json` |
| matched lexical floor (TF-IDF on item text, three matchings) | is this just the wording of the prompts? | `results/lexical_floor.json` |
| card-regex text floor | could a regex over the model card, with zero prompts and zero forward passes, do as well? | `race.card_regex_text_floor` |
| family-label-only baseline | does the architecture family alone predict the role? | `race.family_label_only_baseline` |
| phantom-specialisation check | does the metric separate *architectures* better than *safety roles*? | `family_separability_ba` per row |
| refusal poles (synthetic + two real CensorTune checkpoints) | does a model that refuses *everything* score well? if so the metric is rejected | `results/poles.json` |
| metamodel identity control | does the metamodel recover uploader/architecture identity from the same features? | `results/metamodel.json` |
| nested readout re-selection | does choosing the readout globally change the verdict? | `race.nested_selection_race` |

The direction nulls deserve a note. Iteration 1 compared a fitted probe against a **best-of-20**
anisotropy-matched direction and found a tie at 0.921 — but a max over draws estimates a null
*maximum*, not a null *mean*, so that comparison was rigged against the probe. Here the null is a
**distribution** at three tiers and the fitted direction is placed as a percentile within it, with
**both signs fixed on the training folds** so neither side gets a free parameter the other lacks.

## Honest limits

- The bake-off spans **2 families**, not the ≥3 the plan asked for, because judged refusal needs
  generations and generation needs a GPU. Pre-registered as a scope boundary, not discovered late.
- The family axis is bought for the **weight and card-text** metrics only. Activation and
  across-item metrics keep a within-family axis. This is why the class-trend test is reported on
  a common support.
- `greedy24` shares its grader with the target. It is an upper bound, reported with its cost
  (1040 judge calls against 0 for every other readout), never as a fair rival.
- The real blanket-refuser poles are **off-family and off-size** — no Qwen3 CensorTune exists.
- Independent safety-tuned lineages are below the pre-registered floor of 5, so the three-way
  race is descriptive only, with its lineage count printed on the table.
