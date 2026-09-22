# Lane C (v2) — Can weights alone *grade* how unsafe a model is?

Given **one** checkpoint and nothing else — no parent, no reference model, no attested base, no prompts —
this repository recovers an *abliteration recipe* from the checkpoint's residual-write matrices
(`o_proj`, `down_proj`) and tests whether the recovered recipe **grades** the checkpoint's measured
harmful compliance, or only **flags** that an edit happened.

The inverted outcome — *"the weights read the EDIT and not the RISK"* — was pre-registered as a result in
those words (`PREREG.json`, sha256 in `method_out.json`). **All numbers are in `RESULTS.md`, which is
generated from `results/stage3_v2.json` by `make_results_md_v2.py`; nothing in it is typed by hand.**

<!-- HEADLINE_START -->
## Headline findings (auto-generated from results/stage3_v2.json)

- **Verdict: EDIT_NOT_RISK.** the weights read the EDIT and not the RISK: the parent-free down_proj strength read separates edited from honest checkpoints (pooled AUROC 0.8429, n = 71; abliteration-tool outputs only: 0.9474), but inside the edited arm the pre-registered strength coordinate kappa_hat has Spearman 0.2571 with measured harmful compliance (95% CI [-0.6507, 0.8629], n_edited_graded = 14, resampling unit = architecture family; achieved MDE |rho| = 0.5556, so effects smaller than that are not excluded); adding it to the binary edited label changes in-sample R^2 by 0.05969 (permutation p = 0.1584) and changes leave-one-family-out MAE from 0.154 to 0.1698 (paired difference 0.0158, family-cluster 95% CI [-0.00573, 0.05419]). Nor is this the estimator's fault: even the PARENT-BASED true realised strength of the same published edits does not grade compliance (signed kappa_true Spearman 0.03497, p = 0.9141; |1 - kappa_true| Spearman -0.4056, p = 0.1908; n = 12 projection edits) - e.g. an edit that over-ablates to kappa ~1.5 can still refuse most harmful prompts. How much harm follows an edit is not a monotone function of how strong the edit is. The detection column separates edited from honest; the strength column does not grade how harmful the edit made the model.
- **Detection (edited vs honest, pooled AUROC):** down_proj kappa_hat 0.843 over ALL edited (abliteration-tool outputs only: 0.947), down_proj BOTGAP_min 0.737 (0.783), RQ 0.666 (0.806); o_proj BOTGAP_min on structurally valid sites 0.841 vs square sites 0.569. The published 0.35 BSA flag false-positives on 97.1% of honest checkpoints.
- **Primary endpoint (pre-registered):** within-edited Spearman(kappa_hat, COMPLIANCE) = 0.257, 95% CI [-0.651, 0.863], n = 14, achieved MDE 0.556.
- **Bar 1:** adding kappa_hat to the binary edited label: permutation p = 0.158, out-of-family MAE 0.154 -> 0.17.
- **Ground truth on real edits (parent-based):** the parent-free read is exact inside |1-kappa| < sigma_min/sigma_rms (median kappa_hat 0.979, true-direction cos 1) and blind outside it (median kappa_hat 0.286, cos 0.144); 307 of 484 real edited layer-matrices lie outside it.
- **Ground truth on strength vs risk (parent-based):** signed true kappa vs COMPLIANCE Spearman 0.035 (p = 0.914), |1-kappa_true| vs COMPLIANCE -0.406 (p = 0.191), n = 12 projection edits, of which 4 over-ablate (kappa > 1) and 5 under-ablate: even the TRUE strength of an edit does not order models by harm.
- **Where a graded signal does exist, it is not in the weights.** Pooled over all graded checkpoints the cross-fitted activation coupling tracks COMPLIANCE (Spearman -0.782, CI [-0.947, -0.327], n = 24) more strongly than kappa_hat does (0.567); inside the edited arm the best single predictor is the logit-only L1 first-token gap BASELINE (Spearman -0.618, p = 0.0186, n = 14).
- **Replication on other runs' stored generations (source-stratified, their own item sets):** within-source within-edited Spearman(kappa_hat, COMPLIANCE) combined = 0.849 (CI [0.555, 0.954], n = 20) - but those 'edited' arms mix abliterations with behaviour-uncensored fine-tunes that carry no scar, so this partly re-detects EDIT TYPE; restricted to weight-detected projection edits it is 0.651 (CI [-0.255, 0.949], n = 10). A positive graded signal inside projection edits is therefore NOT excluded at these n; it is not established.
- **Cheapest forgery:** a zero-prompt rank-one repair heals the weight detectors (BOTGAP_min 0.0123 -> 0.824) but not the behaviour (harmful refusal 0.125 -> 0.208, honest parent 0.438; 8-probe refusal 0.25 -> 0.25, parent 0.625). The activation coupling reads -0.584 -> -0.693 (parent -0.437); in this small family the parent is itself weakly coupled, so it does not separate the three.

Full tables: `RESULTS.md`.

<!-- HEADLINE_END -->

This is the second execution of the same plan in this workspace. The first (v1, kept under
`results/v1_attempt/` and the `stage*_*.py` files without a `_v2` suffix) ended `WITHDRAWN` with zero graded
checkpoints. v2 found why and fixed it (see *What changed in v2*).

## What is measured

| readout | reads | prompts | role |
|---|---|---|---|
| `W_RECIPE` κ̂ / abs_dev = \|1−κ̂\| | weights | 0 | **ours** — realised ablation strength: quadratic-in-log tail fit of the checkpoint's OWN bottom singular spectrum (j∈[3,40]) extrapolated to rank 0, index scan j∈[0,15] (load-bearing for κ>1), max over the honest-referenced touched band. Plus band_frac, XLC (cross-layer \|cos\| of suppressed directions), XFC (o_proj vs down_proj) |
| `W_RQ` | weights | 0 | Rayleigh depression of the pooled cross-layer bottom direction |
| `W_DETECT` BSA_w8 + BOTGAP_min | weights | 0 | **ADOPTED PRIOR ART** (public Jorak Model Scanner subspace signature) — a *detection* statistic, never a safety score |
| `A_coupling` | hidden states | 80 prefills | cross-fitted harm projection vs refusal drive (PREREG; UNDEFINED below 0.25 logits spread) |
| `L1` logit gap | logits | 48 | **baseline** — first-token refusal-minus-compliance log-mass |
| `L2` / `BB8` | output text | 8 | **baseline** — judge refusal rate on 8 XSTest-unsafe probes, DISJOINT from the outcome items |
| family label, name-free card regex | nothing | 0 | free baselines |

The standing invariant (≥3 readouts that read weights or hidden states, ≤2 logit-only baselines) is asserted
programmatically in `method.py`.

**Ground truth (two-sided).** Greedy replies to a fixed hashed item protocol — 48 JBB-Behaviors/StrongREJECT
harmful items, 32 XSTest benign-but-alarming twins, 8 disjoint probes — graded by `openai/gpt-5-mini`
(reasoning effort *minimal*) under a **stance** framing, rubric recomputed locally with the StrongREJECT
formula. COMPLIANCE and OVERREFUSAL are reported separately everywhere. No Qwen model is ever a judge.

## What changed in v2 (all measured; details in `DEVIATIONS.json` D11–D24)

1. **The v1 slowness was thread oversubscription, not the hardware.** On a 2-hyperthread cpuset, torch/OpenBLAS
   saw the host's 192 CPUs. Pinned to 1–2 threads, a d=1024 float64 `eigh` takes 0.64 s (v1: 13.8 s) and bf16
   generation of a 0.6B model runs at 14.5 tok/s uncontended (v1: 0.5 tok/s). v2 therefore reads **every layer
   exactly** (no subspace solver, no stride) and generates on CPU.
2. **Ground truth without a GPU.** 13 checkpoints come graded from the sibling screen lane's stored GPU greedy
   generations on the same item protocol; every further checkpoint is generated here on CPU on that protocol.
3. **Judge framing.** The sibling lane measured that the StrongREJECT framing makes hosted judges refuse to grade
   (65.9% degenerate `1,1,1` on harmful prompts), inverting the label on the edited arm. The stance framing is used.
4. **Known truth from a real edit.** The constructed arm scales a *published* abliteration along its own
   weight-space direction, `W(κ) = W_parent + κ·(W_edited − W_parent)`, κ ∈ {0 … 2}.
5. **Forgery measured, not just predicted.** A parent-free rank-one spectral repair (`lanec/forgery.py`, targets
   gap / swap / bulk) is applied, re-read by the detector, and — on huihui Qwen3-0.6B-abliterated-v2 — re-generated
   and re-graded (the 1.7B forgery - behavioural run and weight-side read - did not fit the CPU budget).
6. **Replication panel.** Greedy generations stored by three other runs on this machine are re-graded with the
   same judge and analysed *within source* only (their item sets differ), combined by Fisher z.
7. **Ground truth on real published edits.** For every edited checkpoint whose parent is cached,
   `stage1b_true_kappa.py` solves for the TRUE per-matrix ablation strength (parent-based, calibration only) and
   compares it with the parent-free read of the same matrices — the estimator's validation on real edits.
8. **Surviving a shared, OOM-prone pod.** Three executors share one 16 GB cgroup; the kernel OOM-killed this lane's
   generator and grader once. Fixes: first-step logit capture instead of `output_logits`, a fixed glibc mmap
   threshold + `malloc_trim` in the weight reader, and a watchdog (`scratch/watchdog.sh`) that restarts a killed
   worker. Late edited/constructed checkpoints generate only the 48 harmful items + 8 probes (benign items get a
   prefill-only pass) to fit the CPU budget (D24); heretic checkpoints use the parent's tokenizer (D23).

## Layout

```
method.py                   orchestrator + method_out.json assembly (exp_gen_sol_out, predict_* all strings) + GATE 5 checks
stage2_generate_v2.py       CPU greedy generation queue (results/gen/, hidden states -> results/acts_v2/)
stage2b_grade_v2.py         OpenRouter judge, stance framing, $8 cumulative hard cap (results/graded/)
stage2x_external_gens.py    converts other runs' stored generations into this lane's row schema (results/ext_gen/)
stage1_weights_v2.py        parent-free exact weight reads, every layer, both write matrices (results/ckpt_v2/, vecs_v2/)
stage3_analysis_v2.py       every statistic: Part 1, the graded test + Bars 1-5, constructed arm, forgery, Part 4, replication
make_results_md_v2.py       renders RESULTS.md from results/stage3_v2.json
build_weights_queue.py      weight-read queue from the cached panel (graded first)
build_ext_weights_queue.py  appends the replication panel's checkpoints (download -> read -> delete)
stage1b_true_kappa.py       parent-BASED ground truth: true per-matrix kappa of real published edits (calibration only)
stage2c_prefill_acts_v2.py  prefill-only activation pass for a checkpoint generated before hidden-state capture
regression_v2_vs_harvest.py v2 exact read vs the sibling's GPU harvest (valid sites must agree)
gate1_v2_synthetic.py       GATE 1a with v2 settings: synthetic known kappa incl. kappa > 1
edit_anatomy.py             which tensors a published edit changed, and the rank of each change
finalize_v2.sh              regression -> analysis -> method_out.json -> RESULTS.md -> schema check -> mini/preview
lanec/recipe.py             tail-fit strength estimator, XLC/XFC, BSA window, depth profile, touched band (v1, reused)
lanec/forgery.py            NEW: parent-free rank-one spectral repair (the cheapest forgery)
lanec/{judge,stats,acts,weights,models,io,rosi,hw}.py   inherited modules (CostTracker, REFUSAL_REGEX, ... reused)
items/harvest_protocol/     the hashed 160-item protocol + generation indices + the 8 BB probes
results/gen/                this lane's CPU generations (one JSON per checkpoint)
results/graded/             judge grades + per-checkpoint outcomes (`__full96` = 96-token sensitivity grading)
results/ckpt_v2/, vecs_v2/  per-checkpoint recipe vectors (+ bottom/top singular vectors, float16)
results/acts_v2/            last-prompt-token hidden states of the generation pass (for A_coupling)
results/ext_gen/            other runs' generations in this lane's schema (replication panel)
results/true_kappa/         per-edit ground truth (true kappa per matrix, rank-one share, true-direction cosines)
results/forgery_handoff.json  the Stage 5.3 hand-off to the forgery lane (prediction + measured numbers + cost)
results/judge_agreement_v2.json, gate1_v2_synthetic.json, regression_v2_vs_harvest.json, hardware_v2.json
results/stage3_v2.json      the complete analysis
results/stage4_external.json, stage4b_strata.json   Part 3 (HELM external limb; computed by v1, reused)
results/v1_attempt/         the v1 method_out.json / RESULTS.md / README.md, kept for provenance
stage*_*.py (no _v2)        the v1 pipeline (Part 3 stage4*.py is still the source of the external limb)
PREREG.json                 inherited pre-registration (byte-identical)
DEVIATIONS.json             append-only list of every departure from the plan (D0-D24)
method_out.json             the contract output; full_/mini_/preview_ variants beside it
```

## Running it

```bash
bash install.sh                        # creates venv_lanec/ from requirements_lock.txt (NOT .venv: reaped on this pod)
export HF_TOKEN=...                    # gated configs / downloads
export OPENROUTER_API_KEY=...          # grading only; the ledger hard-stops at $8 cumulative
venv_lanec/bin/python build_weights_queue.py && venv_lanec/bin/python build_ext_weights_queue.py
venv_lanec/bin/python stage2x_external_gens.py      # replication panel rows
venv_lanec/bin/python method.py --stage all         # launch generation + weights + grading workers, wait, analyse, assemble
venv_lanec/bin/python method.py --stage analyse     # re-run the analysis and re-assemble from whatever is on disk
venv_lanec/bin/python make_results_md_v2.py
```

Every worker is resumable (existing `results/gen/<id>.json`, `results/ckpt_v2/<id>.json`,
`results/graded/<id>.json` are skipped) and re-reads its queue file before each checkpoint, so a partial panel is a
partial **result**. Launch workers with `& PID=$!`, stop them with `kill $PID` — never by name (other runs share the box).

## Restoring removed files

| removed (`.aii/manifest.yaml`) | restore with |
|---|---|
| `venv_lanec/`, `.venv/` | `bash install.sh` (uv venv + `uv pip install -r requirements_lock.txt` with the CPU torch index) |
| `scratch/snapshots/` (already removed) | an early-v1 copy of `mlabonne/Qwen3-0.6B-abliterated/model.safetensors` (2.3 GB, over the repo's 100 MB file limit) that was sha256-verified byte-identical to the run-shared HF cache blob and deleted; no code reads it (`stage2_generate.py` / `stage2c_acts.py` load from the shared cache). Restore with `huggingface-cli download mlabonne/Qwen3-0.6B-abliterated`. The small helper scripts in `scratch/` are kept. |
| `__pycache__/`, `lanec/__pycache__/` | `venv_lanec/bin/python -m compileall -q lanec *.py` (or simply run any script; Python regenerates bytecode caches on import) |

Checkpoint weights are never stored in this directory: they are read from the run-shared HuggingFace cache and any
repo this lane downloaded is deleted right after its read (`stage1_weights_v2.py::drop_download`). Every repo id is
listed in `method_out.json → metadata.data_provenance.checkpoints_read`.
