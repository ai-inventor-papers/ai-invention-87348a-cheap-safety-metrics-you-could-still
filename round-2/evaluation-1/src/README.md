# Do safety probes beat random directions?

An **offline, zero-new-compute evaluation** that mines the 1.5 GB activation + weight harvest
that iteration 1 of this programme left orphaned on disk.

**No GPU. No downloads. No model inference. $0.00 of API spend.**

---

## The problem this artifact fixes

Iteration 1's analysis raced its own harvest and lost. Its `make_outputs.py` filters the panel
on `DONE` markers *at call time*:

```python
rows_all = [e for e in PN.active_panel()]
rows = [r for r in rows_all if (HARVEST / slugify(r["repo"]) / "DONE").exists()]
```

It was called while only **3 of 32** markers existed, so every score cell of `race_table.csv`
came out `nan` and `step1_claim.json` recorded the Qwen3-4B anchor as "incomplete". **Seventeen
checkpoints carry a DONE marker now**, including all five anchor members. Nothing in that code
is wrong; re-driving it against the harvest as it stands is the whole fix, and it is the
cheapest result in the iteration.

## The headline

The control that the entire cheap-single-checkpoint-safety-readout literature rests on: does a
difference-in-means direction fitted from labelled harmful/benign items beat an
**anisotropy-matched random direction drawn from that same checkpoint's own item span**?

Iteration 1 answered at n=3 with a **best-of-20** null and got a tie (0.921 vs 0.921). This
artifact replays it at **n=17 with a 1000-draw null distribution** in three tiers (isotropic,
covariance-matched, within-item-span), plus label-permutation and whitened-refit arms, and
reports the fraction of checkpoints on which the fitted direction clears **its own** null.

See `RESULTS.md` for every number.

## Layout

| path | what it is |
|---|---|
| `evallib/core.py` | shared primitives: harvest IO, fold tools, vectorised many-column AUROC, low-rank Ledoit-Wolf algebra (exact `Sigma^-1 v` and `Sigma^1/2 z` by Woodbury), Wilson intervals, lineage-clustered bootstrap, Fisher-z CIs, BH-FDR |
| `s0_setup.py` | S0: inventory, registry hash integrity, harvest-schema discovery, lineage map, fold verification, and the **pre-registration** (`results/PREREG.json`) written before any evaluation number exists |
| `d2_controls.py` | **D2, the headline**: the five-number control suite, parallel over checkpoints |
| `d2b_first_token.py` | D2b: first-generated-token identity audit, decoding `first_token_id` straight out of the cached `tokenizer.json` |
| `d1_step1.py` | D1: the user's step 1 — principal angles between the instruct→SafeRL and instruct→abliterated activation differences, with a matched-anisotropy null floor and a split-half reliability ceiling |
| `d3_table.py` | D3: `race_table_v2.csv`, a strict superset of the frozen 18-column `race_table.csv`, with family/size-only baselines and the Qwen3 size ladder |
| `eval.py` | assembles every stage into `eval_out.json` (the `exp_eval_sol_out` schema) |
| `make_results_md.py` | renders `RESULTS.md` from the stage JSON |
| `vendor/` | the iteration-1 scorer (`make_outputs.py`, `method.py`, `screen/`, `data/`), **copied** and redirected to write inside this workspace — the upstream workspace is read-only to this artifact |
| `results/` | every output; each stage persists the moment its numbers exist |
| `results_d0/` | the re-driven iteration-1 scorer's own output tree |
| `eval_out.json` | the output contract (`exp_eval_sol_out`, schema-validated) |
| `full_eval_out.json`, `mini_eval_out.json`, `preview_eval_out.json` | full / 14-example / truncated variants of the contract |
| `results/race_table_v2.csv`, `results/d3_table.json` | D3: 50-row within-family table, strict superset of the frozen 18 columns |
| `RESULTS.md` | human-readable digest |

## How to run

```bash
./install.sh                 # creates a torch-free CPU-only .venv
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 .venv/bin/python s0_setup.py          # S0 + PREREG
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 .venv/bin/python d2_controls.py       # D2 (~15 min)
OMP_NUM_THREADS=1 .venv/bin/python d2b_first_token.py                     # D2b (~1 min)
OMP_NUM_THREADS=2 .venv/bin/python d1_step1.py                            # D1
cd vendor && OMP_NUM_THREADS=2 ../.venv/bin/python make_outputs.py        # D0 rescore
cd .. && OMP_NUM_THREADS=2 .venv/bin/python d3_table.py                   # D3
.venv/bin/python eval.py && .venv/bin/python make_results_md.py
```

Thread caps must be set **in the launch command**: setting them after numpy is imported is too
late. The box this ran on has 2 usable CPUs and the workspace is a FUSE mount where package
import alone can take minutes under load — slowness there is not a hang.

## Design commitments

- **Pre-registration first.** `results/PREREG.json` fixes every band, `B`, the fold structure,
  the sign convention and the read layer, and is hashed before any number is computed. Every
  verdict cites the band it was judged against.
- **Identical treatment of the null.** Each null direction is drawn on the training folds,
  **sign-fixed on the training folds**, and scored out-of-fold — exactly like the fitted
  direction. Taking `max(AUROC, 1-AUROC)` would inflate the null, so that variant is reported
  only as a labelled sensitivity.
- **No free maximisation.** The primary read layer is a *fixed* depth fraction, so no
  per-checkpoint selection happens at all. The secondary arm reproduces iteration 1's
  argmax-over-layers and applies **the same argmax to every null draw**.
- **The lineage is the resampling unit**, never the repo. `n_lineages` is printed beside every
  aggregate, and every bootstrap resamples lineages.
- **Every null is a distribution with `B` stated**, never a best-of-N point estimate — and the
  best-of-20 statistic is printed beside the distribution so the earlier tie is explained
  rather than contradicted.
- **The seal is respected.** Granite and StableLM2 are never touched. Item fold 4 is *not*
  treated as a fresh confirmation split; `SEALED.md` states the weaker, true claim.

## Restoring removed files

`.aii/manifest.yaml` marks these paths for deletion. `./restore.sh` rebuilds all of them.

| path | how to restore |
|---|---|
| `.venv/` | `./install.sh` — i.e. `uv venv --python 3.12 && uv pip install -r pyproject.toml` |
| `__pycache__/`, `vendor/__pycache__/`, `vendor/screen/__pycache__/`, `evallib/__pycache__/` | regenerate automatically on the next import |

Nothing under `results/`, `results_d0/`, `logs/`, `vendor/screen/`, `vendor/data/` or
`vendor/results_seed/` is deletable: they are the outputs, the code and the frozen inputs.

## Scope, stated up front

This is a **within-family** artifact. The 17 finished harvests span exactly two model families
(Qwen3 and TinyLlama) across **4 lineages**, at an item budget of **160**. It supports zero
held-out-*family* answer; the family axis belongs to the sibling experiment. Any negative
result here is a measured statement about a **per-checkpoint** score on *this* panel at *this*
item budget — never a refutation of a published per-prompt number evaluated on its own panel.
