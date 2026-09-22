# Lane C — Can weights alone *grade* how unsafe a model is?

Given **one** checkpoint and nothing else — no parent, no reference model, no attested base — this
repository recovers an *abliteration recipe* from its residual-write matrices and asks whether the
recovered recipe **grades** the checkpoint's measured harmful compliance, or only **flags** that it
was edited at all.

The inverted outcome — *"the weights read the EDIT and not the RISK"* — is pre-registered as a
result **in those words**, not treated as a failure.

## What is measured

| Readout | Reads | Cost | Status |
|---|---|---|---|
| `W_RECIPE` `kappa_hat` / `abs_dev` | weights | 0 prompts | realised ablation strength from a tail fit of the checkpoint's **own** bottom spectrum, with an index scan for the κ>1 case |
| `W_DETECT` `BSA_w8` + `BOTGAP_min` | weights | 0 prompts | **ADOPTED PRIOR ART** — the public Jorak Model Scanner already ships a bottom-k subspace signature on exactly these matrices. A *detection* statistic, never a safety score. |
| `W_RQ` `RQ_pooled` | weights | 0 prompts | **new** — Rayleigh depression of the pooled cross-layer direction; graded at *every* κ |
| `A_coupling` | hidden states | 48 prefills | cross-fitted activation readout |
| `L1_logit_gap` | logits | teacher-forced | **baseline** |
| `L2` / `BB8` | output text | 8 disjoint prompts | **baseline** |

The standing invariant — ≥3 readouts that read weights or hidden states, ≤2 logit-only baselines —
is asserted programmatically in `method.py::build_examples` and fails the run if violated.

## Gate 1 — the calibration table that changed the design

A real Qwen3-0.6B `o_proj`, abliterated **by us** at known κ, read back parent-free:

| κ (true) | κ̂ (rank read) | BOTGAP_min | BSA | XLC | RQ | cos(r̂, r_true) |
|---|---|---|---|---|---|---|
| 0.3 shared | 0.131 — blind | 0.642 | 0.346 | 0.202 | 1.52 | 0.16 |
| 0.7 shared | 0.166 — blind | 0.678 | 0.555 | 0.327 | 0.737 | **0.977** |
| 1.0 shared | 0.985 ✓ | **0.0121** | 1.000 | 1.000 | 1.4e-4 | **1.000** |
| 1.0 per-layer | 0.984 | 0.0123 | 0.143 | **0.027** | 1.53 | 0.011 |

Read across the rows:

* the **rank** read (`κ̂`, `BOTGAP`) is blind below κ ≈ 0.9 and exact at κ = 1;
* the **sharing** read (`BSA`, `XLC`) is the graded one — it climbs monotonically with κ;
* `XLC` separates a shared-direction edit from a per-layer one at the *same* κ (1.000 vs 0.027),
  which is the sharing statistic's definitional boundary;
* the ablation **direction itself** is recoverable parent-free from κ ≈ 0.7 (`cos(r̂, r) = 0.977`);
* the bf16 floor on `BOTGAP` at κ = 1 is **0.0121** — not algebraic zero, and comfortably under the
  pre-registered 0.1 separator, exactly as predicted.

## Five measured findings that changed the design

1. **A rank read has a narrow operating range.** Abliteration is `W' = (I − κ r rᵀ) W`, so
   `rᵀG'r = (1−κ)² rᵀGr`. The *bottom* of the spectrum only moves once `(1−κ)²·rᵀGr` falls below the
   layer's own `σ_min²`. Measured on real Qwen3-0.6B `o_proj`, `σ_min/σ_rms = 0.19`, so a rank read
   is blind outside `|1−κ| < 0.19`. Gate 1 duly measured `κ̂` = 0.139 (unedited) → 0.141 (κ=0.3) →
   0.162 (κ=0.7): **no recovery of a large real edit.** That is a property of the statistic, and it
   is why `RQ_pooled` exists beside it.
2. **The sharing statistic is the graded one.** Over the same sweep `BSA_w8` moved 0.402 → 0.555.
3. **`o_proj` is not always a valid detection site.** On families where `num_heads · head_dim <
   hidden_size` (Gemma3-1B is one), `W Wᵀ` is rank-deficient *by construction*: its bottom spectrum
   is zero for an untouched checkpoint, and a full κ = 1 ablation adds no new deficiency there. The
   first Stage-1 pass duly returned `κ̂ = nan` on such a repo. `down_proj` always has
   `d_in > d_out`, so it always carries the scar; the headline component is chosen accordingly and
   the choice is recorded per checkpoint. Measured on Gemma3-1B: `o_proj` XLC = 0.024 (the isotropic
   null), `down_proj` XLC = 0.197 with κ̂ = 0.74.

4. **A parent-free bottom read needs `d_in > d_out` *strictly*.** Only then is an untouched
   matrix's smallest singular value bounded away from zero — which is the whole reason a
   rank-deficiency read can mean anything without a parent. Two failure modes were **measured**, not
   anticipated:
   * `d_in < d_out` (Gemma3-1B `o_proj`): rank-deficient by construction; a full κ = 1 ablation adds
     no new deficiency, so the read is structurally blind there.
   * `d_in == d_out` (**every** Qwen2 / Qwen3 / Llama `o_proj` on this panel — `num_heads · head_dim
     == hidden_size`): the honest bottom edge is unbounded, and the pre-registered `BOTGAP < 0.1`
     flag fires on *untouched* weights. Measured: honest `unsloth/Llama-3.2-1B-Instruct` scored
     `BOTGAP_min = 0.0136`.

   `down_proj` always has `intermediate_size > hidden_size`, so it is always a valid site. The
   analysis therefore picks the headline site **by aspect ratio**, and reports detection both
   overall and restricted to structurally valid sites. With the valid site the arms separate as
   predicted (edited κ̂ 0.883 / XLC 0.538 / BSA 0.858 / BOTGAP 0.067 versus honest 0.631 / 0.125 /
   0.544 / 0.375).

5. **The isotropic null is wrong by a factor of three.** The anisotropy-matched null — directions
   drawn from the empirical covariance of the *real* recovered bottom directions on the honest panel
   — puts `BSA_w8` at **0.37–0.42**, while an isotropic Gaussian null puts it at **0.137**. Reading
   the observed statistic against the isotropic null would make almost anything look significant.
   Observed honest checkpoints sit at or above the matched null (0.975 / 0.703 / 0.384), i.e. real
   trained weights genuinely carry shared bottom directions of their own. The null is sampled in
   low-rank factor form — `normalise(Vᵀg)` with `V` the honest direction set — which is exactly the
   same distribution as a Cholesky draw from the empirical covariance at O(n·d) instead of O(d²).

## Inherited-code smoke test

`tier0_tests.py` is inherited unchanged and scores **10 PASS / 1 FAIL**. The failure is
`T0.2_subspace_reference`, **the same test that failed in iteration 1** — a simulated-threshold
reference check, not a port regression. Recorded and proceeded, per the plan.

## Layout

```
method.py                 orchestrator + exp_gen_sol_out assembly (the deliverable entry point)
PREREG.json               inherited pre-registration (byte-identical; its sha256 is in method_out.json)
DEVIATIONS.json           append-only list of every departure from the plan, with its reason
gate0_eigensolver.py      GATE 0 — the fast eigensolver must reproduce an exact eigh
gate1_estimator.py        GATE 1 — the strength estimators on KNOWN ground truth
stage0_panel.py           panel construction (41 edited / 85 honest, 23 family signatures)
stage1_weights.py         PART 1 — parent-free recipe recovery, one checkpoint at a time
stage2_generate.py        PART 2a — CPU generation of the two-sided ground truth
stage2b_grade.py          PART 2b — StrongREJECT grading via OpenRouter, with a hard $8 ledger cap
stage3_analysis.py        PART 2b — the graded test and all five bars
stage4_external.py        PART 3 — the external limb (HELM) and the identical-weights ceiling
stage5_bonus.py           PART 4 — layer profile, anisotropy-matched null, cheapest forgery
lanec/recipe.py           NEW: ranged safetensors reader, strength estimators, XLC, RQ, fast eigensolver
lanec/panel.py            NEW: candidate harvest and screening
lanec/external.py         NEW: HELM aggregation, name→repo resolution, guardian-pair ceiling
lanec/{weights,acts,stats,judge,models,io,rosi,hw}.py   inherited from iteration 1 — CALLED, not rewritten
items/                    hashed item pools (verified against PREREG.item_files)
external/                 published safety and capability tables, already on disk
results/                  every measurement; one file per checkpoint, written the moment it is computed
method_out.json           the contract output (exp_gen_sol_out, datasets-grouped, predict_* all STRINGS)
```

## Running it

```bash
uv venv .venv --python=3.12
uv pip install --python=.venv/bin/python --index-url https://download.pytorch.org/whl/cpu \
  --extra-index-url https://pypi.org/simple --index-strategy unsafe-best-match \
  torch "transformers>=4.51" accelerate safetensors huggingface_hub numpy scipy pandas \
  scikit-learn loguru requests aiohttp sentencepiece protobuf psutil tqdm

export HF_TOKEN=...          # metadata + gated configs
export OPENROUTER_API_KEY=...# grading only; the ledger hard-stops at $8

uv run gate0_eigensolver.py           # validate the eigensolver first
uv run gate1_estimator.py             # calibrate the strength estimators on known ground truth
uv run stage0_panel.py                # build the panel
uv run method.py --stage all          # everything, each stage under its own time box
uv run method.py --stage assemble     # rebuild method_out.json from whatever is on disk
```

Every stage is independently resumable: an existing valid `results/ckpt/<id>.json`,
`results/gen/<id>.jsonl` or `results/graded/<id>.json` is skipped, so a partial panel is a partial
**result** rather than a lost run.

### What the hardware allowed, measured

| quantity | measured |
|---|---|
| GPU | none |
| CPU | 2 hyperthreads of **one** physical EPYC core (`cpuset 10,106`), host load 260–345 |
| share actually obtained | 12% of one core with 4 processes, 26% with 2 |
| dense `eigh` of the Gram | 13.8 s at d=1024, 52.8 s at d=2048 |
| CPU generation | **0.5 tok/s aggregate** (batch 6, 0.6B, float32) |
| HTTP Range read of a tensor span | ~3 MB/s |
| full `snapshot_download` | **56–76 MB/s** |
| read from the run-shared cache | ~48 MB/s |

The last three rows changed the design: ranged reads are 20× slower than just downloading the
shards, so checkpoints are prefetched into the run-shared cache and read from local disk. The
generation rate is what caps the graded panel, and it is reported as a measured number rather than
a declared one.

### Hardware note

The plan asked for a 16 GB GPU. This worker had **no GPU** and a hard cpuset of two hyperthreads of
one physical EPYC core, on a host at load average ~345. Failure branch **F5** fired: generation moved
to CPU, the graded panel is sized from a *measured* rate, and a dense per-layer eigendecomposition
(12 s at d=1024, 52 s at d=2048) was replaced by a Cholesky shift-invert subspace solver validated
against an exact `eigh` in Gate 0. All of this is recorded in `DEVIATIONS.json`.

## Restoring removed files

| Removed | Restore with |
|---|---|
| `.venv/` | the `uv venv` + `uv pip install` block above |
| `scratch/` | transient HuggingFace snapshots, streamed and deleted per checkpoint; `uv run stage2_generate.py` re-fetches them. Repo ids are in `results/panel.json`. |

`install.sh` beside this file runs the venv step.
