# One harvest, five cheap safety reads, one race

A **cheap, single-checkpoint** safety-readout screen. No parent, no reference model, no
attested base to diff against: assume you found a random model on HuggingFace and you
have nothing else. Every read costs one model load, a weight pass, and at most 160
teacher-forced prefills.

Five candidate readouts are raced against **four published incumbents** and **three
black-box baselines** on **one shared harvest per checkpoint** — identical items,
identical leave-one-lineage-out folds — so no comparison is confounded by implementation.

The output is a **ranked comparison plus one survivor for iteration 2**, not a finding.

---

## What is actually measured

| | read | inputs | prompts |
|---|---|---|---|
| **C1** | across-item coupling: does refusal drive track the model's own internal harm estimate, item by item | activations + logits | 160 |
| **C2** | the prompt-budget crossover: at which *n* does a black-box estimator overtake the internal one | both, matched axis | 0–64 |
| **C3** | refusal depth minus harm-content depth, as a fraction of layer count | activations | 160 |
| **C4** | recovered recipe from weights alone: BOTGAP, BSA, cross-layer cosine, TSA | **weights, 0 prompts** | 0 |
| **C5** | metamodel on architecture-free activation geometry, shipped with its own lineage-identity ablation | activations | 160 |

**Incumbents as success bars, not as mentions** — AMS (2608.05578), GFS (2606.22676),
N-GLARE (2511.14195), HRCI_repr (2606.16349). Each is re-implemented on *our*
checkpoints and gets a table row and a bar. See [`INCUMBENTS.md`](INCUMBENTS.md) for the
full positioning, the re-implementation choices, and the named missing details.

**Baselines** — B1 first-token logit-gap margin, B2 greedy refusal rate on a *disjoint*
probe set, B3 model-card regex in both its term-swept and name-free de-biased forms.

---

## Layout

```
method.py                  the orchestrator: P0 freeze -> P1 items -> P2 panel -> P3 harvest
                           -> P4 reads -> P5 race -> P6 step-1 claim -> P8 output contract
screen/
  common.py                paths, seeds, pre-registered thresholds
  registry.py              THE FROZEN 50-METRIC REGISTRY (sha256 re-asserted at the end)
  substrate.py             the 160-item battery + the presentation pool + the lexical floor
  panel.py                 the checkpoint panel, class labels, LINEAGES, poles, seals
  harvest.py               THE HARVEST: weight pass (eigh of the Gram) + activation pass
  reads.py                 the fifteen reads, all offline from the harvest
  race.py                  leave-one-lineage-out, balanced accuracy, the permutation test
  step1.py                 P6: principal angles on the Qwen3-4B anchor
  judge.py                 OpenRouter grading, content-addressed cache, cost cap
  selftest.py              Stage 0 unit tests + the Stage 3 real-weight positive control
download.py                streamed panel downloader (safetensors only, resumable)
data/                      frozen raw substrate + panel/census/model-card metadata
harvest/<slug>/            per-checkpoint: weights.npz, acts.npz, generations.json, DONE
results/                   every deliverable listed below
SEALED.md                  what iteration 2 gets that this artifact never touched
INCUMBENTS.md              how each published rival was re-implemented and scored
```

### results/

| file | what it holds |
|---|---|
| `metrics_registry.json` + `.sha256` | the 50 metrics, frozen before any measurement |
| `stage0_selftest.json` | the cross-fitting-on-noise demonstration and the synthetic weight edits |
| `stage3_instrument_gate.json` | the weight instrument validated on **real** trained weights |
| `stage4_anchor_gate.json` | the anchor-lineage confirmation signals |
| `f5_weight_instrument.json` | the honest-panel **false-positive rate** the published statistic lacks |
| `race_table.csv` | **R1** — all 50 metrics, held-out WITH tuned printed beside it |
| `race.json` | survival rule, permutation test, transfer dissociation, crossover |
| `step1_claim.json` | the principal-angle claim on the Qwen3-4B anchor |
| `lineage_census.json` | the counting rule and the independent-lineage number |
| `ground_truth.json` | graded compliance / false refusal + the judge cost |
| `per_checkpoint_reads.json` | every metric and every null, per checkpoint |
| `summary.json` | the verdict |

---

## How to run

```bash
uv sync
python3 download.py results/dl_wave1.json results/dl_status.json     # then wave2
OMP_NUM_THREADS=8 MKL_NUM_THREADS=8 .venv/bin/python -u method.py --tag run
```

The thread caps must be in the **launch command**: setting them inside a module after
numpy is imported is too late.

Useful flags: `--only <repo,repo>` to run a subset, `--max-prio N` to shrink the panel
family-wise, `--harvest-minutes M` for the harvest deadline, `--no-judge` to skip
OpenRouter entirely (the in-house refusal regex is then used and labelled as such).

The harvest is **idempotent and resumable**: each checkpoint writes a `DONE` marker, so a
restart is nearly free.

---

## Design decisions worth knowing

**We store vectors, not scalars.** The harvest keeps all-layer hidden states at two read
positions for every item (~85–110 MB per checkpoint). Every direction can then be
re-fitted offline, every null recomputed and every candidate re-read with **no second GPU
pass**. That single decision is what makes a fifteen-way screen affordable; scalars force
re-runs and full tensors fill the disk.

**Cross-fitting is part of the definition, not an analysis choice.** Stage 0 shows why:
on pure Gaussian noise at d = 2560 with 64 randomly-labelled items, an in-sample
difference-in-means projection separates at **AUROC 1.000** and the cross-fitted version
at chance. An in-sample harm direction is numerically indistinguishable from the harm
label.

**The resampling unit is the LINEAGE, never the repo.** A naive Hub search returns
hundreds of "safety-tuned" repos, but the top five uploaders account for the large
majority of them and many are epoch snapshots of one parent. `results/lineage_census.json`
publishes the collapse rule and the independent-lineage count *before* the design commits.

**Base models are a separate stratum.** They use the plain renderer, not the chat
template, so they are never mixed into the three-way comparison. They are harvested only
as GFS parents and for the step-1 base note.

---

## Restoring removed files

Nothing under this directory is deleted. The one heavy path with a `delete` decision in
[`.aii/manifest.yaml`](.aii/manifest.yaml) is the shared HuggingFace cache, which lives
**outside** this workspace anyway.

| path | how to restore |
|---|---|
| `cache/` | regenerable — content-addressed OpenRouter judge and paraphrase responses. Rebuilt automatically on the next run (and re-billed at well under $1): `OMP_NUM_THREADS=8 .venv/bin/python -u method.py --tag run` |
| `.venv/` | redownloadable — `uv sync` |
| model weights (in `$HF_HUB_CACHE`, outside this repo) | redownloadable — `python3 download.py results/dl_wave1.json results/dl_status.json` and the same for `dl_wave2.json` |
| `harvest/` | regenerable from the weights, but **kept**: it is the whole point of the artifact and every read in `results/` is a pure function of it. Rebuild with the `method.py` command above. |
