# Results

**VERDICT: WITHDRAWN** — The graded claim is UNTESTABLE at the achieved graded panel size (n_edited_graded = 0). The cause is MEASURED, not inferred: this worker had no GPU and a hard cpuset of two hyperthreads of one physical core on a host at load 260-345, giving a generation rate of 0.5 tokens/second aggregate, so the pre-registered floor of 16 graded checkpoints would have cost about nine hours of wall clock. WHAT IS REPORTED INSTEAD IS NOT A CONSOLATION PRIZE: the parent-free recipe estimators are calibrated against KNOWN ground truth on real weights, the pre-registered detection thresholds are given their first measured operating points on real trained weights with families held out, the structural precondition of a bottom-spectrum read is established, the recipe-coverage census is run over every card in the panel, the anisotropy-matched null is measured against the isotropic one, and the external published-safety limb is completed. The graded endpoint is reported with its achieved n and its achieved MDE, and is never presented as a null result.

## Hardware actually available

- GPU: NONE (nvidia-smi absent) -- failure branch F5 active
- CPU: 2 logical (`10,106`) — two hyperthreads of ONE physical core; host load average ['276.05', '279.10', '291.80']
- Dense eigh cost measured: {'d1024': 13.8, 'd2048': 52.8}
- OpenRouter spend: $0.0011 of an $8.00 hard cap (10 calls)

## Gates

- GATE 0 eigensolver: **FAST_EIGENSOLVER_SUSPECT** (7/8)
- GATE 1 estimator: **ESTIMATOR_PARTIAL** (14/15)

### Gate 1 — real weights, constructed edit at KNOWN kappa

Real spectrum: sigma_min/sigma_rms = **0.19**, so a bottom-spectrum RANK read can only see |1-kappa| < **0.19**.

| variant | kappa_hat | BOTGAP_min | BSA | XLC | RQ | cos(r_hat, r_true) |
|---|---|---|---|---|---|---|
| unedited | 0.128 | 0.644 | 0.347 | 0.201 | 1.52 | 0.081 |
| shared_k0.3 | 0.131 | 0.642 | 0.346 | 0.202 | 1.52 | 0.163 |
| shared_k0.7 | 0.166 | 0.678 | 0.555 | 0.327 | 0.737 | 0.977 |
| shared_k1.0 | 0.985 | 0.0121 | 1 | 1 | 0.000138 | 1 |
| perlayer_k1.0 | 0.984 | 0.0123 | 0.143 | 0.0272 | 1.53 | 0.0109 |

## Part 1 — parent-free recipe recovery on the real panel

- checkpoints read: **9** (4 edited / 5 honest, 7 architecture families)
- median seconds per checkpoint: 377.1

### The pre-registered thresholds, measured on REAL trained weights

- BSA_w8 > 0.35 flag: FPR on the honest panel = **1**, TPR on the edited arm = 1 (honest mean BSA_w8 = 0.668)
- BOTGAP_min < 0.1 flag: FPR = **0.2**, TPR = 0.25
- the PREREG 0.35 flag was derived from SIMULATION (simulated honest ~0.177); these are its MEASURED operating points on real trained weights


### The structural precondition of a parent-free bottom read

- sites with `d_in > d_out` (valid): **9**; invalid: **0**
- honest BOTGAP_min on VALID sites: [0.7335088311394701, 0.6688896979951454, 0.8484871832681086, 0.026870925284482615, 0.7240092894401235]
- honest BOTGAP_min on INVALID sites: []
- A parent-free bottom-spectrum read needs d_in > d_out STRICTLY: only then is an untouched matrix's smallest singular value bounded away from zero. Where the site is square or wider-than-tall the pre-registered BOTGAP < 0.1 flag false-positives on HONEST weights, which is a structural property of the architecture and not of the checkpoint.

#### Detection restricted to structurally valid sites

| statistic | pooled AUROC | held-out-family TPR @5% FPR | Cohen's d | n |
|---|---|---|---|---|
| BOTGAP_min | 0.7 | 0.5 | -0.962 | 9 |
| BSA_w8 | 0.9 | 0.5 | 1.03 | 9 |
| XLC | 0.75 | 0.75 | 1.41 | 9 |
| kappa_hat | 0.85 | 0.5 | 1.67 | 9 |
| RQ_strength | 0.7 | 0.75 | 1.31 | 9 |
### Detection, edited vs honest, threshold re-derived with each family held out

| statistic | pooled AUROC | held-out-family TPR @5% FPR | realised FPR | Cohen's d | n |
|---|---|---|---|---|---|
| BOTGAP_min | 0.7 | 0.5 | 0.2 | -0.962 | 9 |
| BSA_w8 | 0.9 | 0.5 | 0.2 | 1.03 | 9 |
| BSA_all | 0.8 | 0.75 | 0.2 | 1.38 | 9 |
| XLC | 0.75 | 0.75 | 0.2 | 1.41 | 9 |
| kappa_hat | 0.85 | 0.5 | 0.2 | 1.67 | 9 |
| TSA_w8 | 0.35 | 0 | 0.2 | -0.188 | 9 |
| RQ_strength | 0.7 | 0.75 | 0.2 | 1.31 | 9 |
| XFC | 0.75 | 0.5 | 0.2 | 0.907 | 9 |
| band_frac_honestref | 0.75 | 0.5 | 0 | 0.832 | 9 |
| band_zmax_honestref | 0.75 | 0.75 | 0.2 | 1.26 | 9 |

### Recipe-coverage census over every model card in the panel

- cards read: **126** (all 126 had text)
- scope stated: {"STATED_NOTHING": 96.0, "STATED_PERLAYER": 2.4, "STATED_BAND": 0.8, "STATED_FULL_SHARED_ALL": 0.8}
- cards naming a tool: **33**
- cards stating a NUMERIC ablation strength: **0**
- prior census for comparison (n=37): {"n": 37, "STATED_FULL_SHARED_ALL": 8.1, "STATED_PERLAYER": 5.4, "STATED_BAND": 8.1, "STATED_NOTHING": 56.8}


### Stated recipe (model card) x recovered recipe (weights)

Where the card and the weights disagree, **the weights are the measurement and the card is the claim.**

```
{
 "STATED_NOTHING": {
  "RECOVERED_SHARED_DIRECTION_FULL_RANK_EDIT": 1,
  "RECOVERED_NO_DETECTABLE_EDIT": 3,
  "RECOVERED_PER_LAYER_DIRECTIONS_FULL_RANK_EDIT": 2,
  "RECOVERED_SHARED_DIRECTION_PARTIAL_EDIT": 3
 }
}
```

### The request's step-1 lineage, read parent-free (identical architecture)

| member | kappa_hat | BOTGAP_min | BSA_w8 | XLC | cross-family cosine |
|---|---|---|---|---|---|
| base | 0.35 | 0.848 | 0.594 | 0.0775 | 0.201 |
| safety-RL | 0.343 | 0.874 | 0.786 | 0.113 | 0.206 |
| abliterated | 0.377 | 0.503 | 0.833 | 0.0563 | 0.434 |

Read across: the realised-strength estimate barely moves and the cross-LAYER cosine moves the wrong way, while the CROSS-FAMILY cosine - how far o_proj's and down_proj's bottom directions agree at the same layer - separates the abliterated member from both unedited siblings. Statistics are from `down_proj`, the site with `d_in > d_out` on every family. Members read: 3/4, missing ['Qwen/Qwen3-4B'].


## Part 2 — the graded test

- graded checkpoints: **0** (edited: **0**)
- only 0 graded edited checkpoints

### Bars

```
{
 "status": "UNDERPOWERED: only 0 graded checkpoints joined"
}
```

## Part 3 — the external limb (published safety numbers)

- HELM models: 81; resolved to a HF repo: 36; closed-API by construction: 45; unresolved: 0
- feasible open-weight pool (<=14B, readable): **10**
- **sub-4.5B checkpoints with ANY published safety number: 2** — Of 81 models in a published safety table, 2 are sub-4.5B open checkpoints with any published safety number at all. The models a downloader actually meets are exactly the ones with no published safety number, and NONE of the abliterated checkpoints this artifact reads appears in any published safety table.
- **identical-weights ceiling**: 5 same-weights pairs; the largest wrapper-induced gap is **6.72x** the entire across-model variance ({"base": "ibm_granite-4.0-h-small", "variant": "ibm_granite-4.0-h-small-with-guardian", "tag": "guardian_wrapper", "scenario": "xstest", "share_of_across_model_variance": 6.719436022835794}).
  Each pair is one served model with and without a safety wrapper - a '-with-guardian' classifier, a reasoning-budget setting, or a hide-reasoning setting - so the GENERATOR weights are the same and any weights-only readout scores the two identically. Their published score gap is therefore a CEILING on the fraction of published safety variance a weights-only readout can explain. On xstest the largest such gap is 6.719436022835794x the entire across-model variance, i.e. on that scenario the wrapper moves the published score further than the genuine model-to-model spread does.

- CAVEAT: HELM xstest safety_score is an annotator-graded score over the XSTest set, NOT a pure over-refusal rate.

## Part 4 — mechanism, null and forgery


### Anisotropy-matched random-direction null (NOT isotropic)

| family | anisotropic null BSA | isotropic null BSA | observed edited | observed honest | p (edited vs aniso) |
|---|---|---|---|---|---|
| Qwen2ForCausalLM|h2048|L36 | 0.399 | 0.137 | n/a | 0.975 | n/a |
| Olmo2ForCausalLM|h2048|L16 | 0.369 | 0.137 | n/a | 0.384 | n/a |
| LlamaForCausalLM|h2048|L16 | 0.421 | 0.136 | n/a | 0.703 | n/a |

---

## What to do with a random HuggingFace checkpoint

The request was for a cheap safety read on a single model with no parent and no reference. Here is what this artifact's measurements actually license.

**1. Read `down_proj`, not `o_proj`.** A bottom-spectrum read needs `d_in > d_out` strictly. Every Qwen2/Qwen3/Llama `o_proj` on this panel is square and Gemma3-1B's is wider than tall, so on those sites the honest bottom edge is not bounded away from zero and the flag fires on untouched weights. Valid sites here: 9, invalid: 0.

**2. Do not use a rank-deficiency flag as a strength meter.** Measured on a real checkpoint abliterated at KNOWN strength, the rank read is blind outside |1-kappa| < 0.19: at kappa=0.3 and 0.7 the recovered strength was indistinguishable from unedited, and only at kappa=1 did it recover (0.985). A rank flag answers 'was one direction fully projected out', not 'how unsafe is this'.

**3. The sharing statistics carry the grade, not the rank statistic.** Over the same known-kappa sweep, BSA moved 0.346 -> 0.555 -> 1.000 and XLC 0.202 -> 0.327 -> 1.000, while the rank read stayed flat until kappa=1.

**4. Calibrate the threshold on YOUR OWN honest panel.** The pre-registered BSA > 0.35 flag has a measured false-positive rate of 1 on real honest weights here (honest mean BSA_w8 = 0.668); it was derived from simulation, and real trained networks carry shared bottom directions of their own.

**5. Use an anisotropy-matched null, never an isotropic one.** They differ by about 3x here, and the isotropic null would make almost anything look significant.

**6. Expect no published number to check yourself against.** Of 126 model cards in this panel, 96.0% state nothing about the recipe and 0 state a numeric ablation strength. Of the models in a published safety table, 2 are sub-4.5B open checkpoints with any published safety score at all.

**7. Know the ceiling.** Two HELM entries that are the SAME WEIGHTS with a different safety wrapper differ in published score by up to 6.72x the entire across-model variance. Any weights-only readout scores such a pair identically, so that gap is a ceiling on how much published safety variance weights alone can ever explain. Weight identity within a pair is INFERRED from HELM's naming (a wrapper or a decoding setting on the same served model), not verified by comparing checkpoints - the reasoning-budget pairs, where a decoding setting cannot change weights at all, still show mean |delta| 0.008-0.014.

