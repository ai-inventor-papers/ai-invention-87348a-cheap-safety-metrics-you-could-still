# Do safety probes beat random directions?

Offline re-analysis of the 1.5 GB activation + weight harvest that iteration 1 left orphaned on disk. **No GPU, no downloads, no model inference, $0.00 of API spend.**

- Panel: **17 checkpoints / 4 lineages / 2 families** (Qwen3, TinyLlama)
- Classes: {'abliterated': 4, 'base': 4, 'instruct': 4, 'safety': 5}
- Resampling unit: **LINEAGE**, never the repo. Every aggregate below is clustered on 4 lineages.
- Pre-registration sha256: `f886814badb718e28e9a3f61f4d2465b37966e9ef90cba6f39473b1fed1845c0`
- Registry sha256 before == after == frozen literal: **MATCH** (`ffe9b23478049bc3...`)

## What iteration 1 actually left behind

> The artifact summary of the upstream experiment reads like a completed study and its summary.json does not. summary.json records n_checkpoints_scored=3 of n_panel_total=32 with PARTIAL_PANEL=true, wall_clock_minutes=4.7 and step1_verdict='not computed', while 17 DONE markers are on disk now -- the analysis raced its own harvest and lost.

Verbatim from the upstream `summary.json`: `n_checkpoints_scored`=3, `n_panel_total`=32, `PARTIAL_PANEL`=True, `wall_clock_minutes`=4.7, `step1_verdict`='not computed'. DONE markers on disk now: **17**.

## D2 (HEADLINE) -- the fitted direction against its own anisotropy-matched null

Five numbers side by side per (checkpoint, readout). Every null direction is treated **exactly** as the fitted one: drawn on the training folds, sign-fixed on the training folds, scored out-of-fold, pooled, one AUROC. B = 1000 draws per tier; primary null = within-item-span; primary read layer = fixed depth fraction 0.6. No per-checkpoint layer selection.

| readout | contrast | SURV vs own span-null p95 | Wilson 95% | verdict | mean AUROC_xf | mean span-null | mean iso-null | mean best-of-20 null | mean AUROC_in | mean whitened |
|---|---|---|---|---|---|---|---|---|---|---|
| `content_last` | harmful vs plain_benign | **16/17** | [0.730, 0.990] | **SURVIVES** | 0.835 | 0.629 | 0.550 | 0.748 | 0.889 | 0.759 |
| `content_first` | harmful vs plain_benign | **9/17** | [0.310, 0.738] | **PREMISE_FAILS** | 0.664 | 0.576 | 0.539 | 0.685 | 0.836 | 0.714 |
| `twin_xstest` | xstest_contrast vs benign_alarming | **17/17** | [0.816, 1.000] | **SURVIVES** | 0.801 | 0.626 | 0.545 | 0.728 | 0.852 | 0.817 |
| `harm_vs_allbenign` | harmful vs plain_benign+benign_alarming+xstest_contrast | **17/17** | [0.816, 1.000] | **SURVIVES** | 0.839 | 0.662 | 0.561 | 0.773 | 0.854 | 0.826 |

Other null arms (count of the 17 clearing each p95):

| readout | span | covariance-matched | isotropic | label-permutation | whitened | joint span+perm |
|---|---|---|---|---|---|---|
| `content_last` | 16 | 16 | 17 | 17 | 16 | 16 |
| `content_first` | 9 | 9 | 10 | 10 | 14 | 8 |
| `twin_xstest` | 17 | 17 | 17 | 17 | 17 | 17 |
| `harm_vs_allbenign` | 17 | 17 | 17 | 17 | 17 | 17 |

Pre-registered bands over 17 checkpoints: SURVIVES >= 13/17 | AMBIGUOUS 10-12/17 | PREMISE_FAILS <= 9/17.

- `content_last`: Delta_AUROC (fitted minus span-null mean) = **0.206** [0.173, 0.245] (lineage-clustered bootstrap, B=2000, 4 clusters); in-sample inflation AUROC_in - AUROC_xf = 0.054; whitened minus raw = -0.077.
- `content_first`: Delta_AUROC (fitted minus span-null mean) = **0.088** [0.048, 0.127] (lineage-clustered bootstrap, B=2000, 4 clusters); in-sample inflation AUROC_in - AUROC_xf = 0.172; whitened minus raw = 0.049.
- `twin_xstest`: Delta_AUROC (fitted minus span-null mean) = **0.174** [0.128, 0.219] (lineage-clustered bootstrap, B=2000, 4 clusters); in-sample inflation AUROC_in - AUROC_xf = 0.051; whitened minus raw = 0.016.
- `harm_vs_allbenign`: Delta_AUROC (fitted minus span-null mean) = **0.178** [0.134, 0.212] (lineage-clustered bootstrap, B=2000, 4 clusters); in-sample inflation AUROC_in - AUROC_xf = 0.015; whitened minus raw = -0.013.

### Why iteration 1 saw a tie

Iteration 1 reported, at n=3, a cross-fitted fitted harm direction at mean AUROC 0.921 against a **best-of-20** anisotropy-matched random direction at mean AUROC 0.921. The best-of-20 maximum is an upward-biased estimate of a null *mean*. Printing it beside the full distribution (column `mean best-of-20 null` above, and `null_max_first_20_draws` per checkpoint) reproduces that number and explains it, rather than contradicting it.

### The anisotropy is large and it is the point

The isotropic null sits near chance while the within-span null does not. A random direction *drawn from the checkpoint's own item span* already separates harmful from benign items well above 0.5 -- on Qwen3-4B the span-null mean reaches ~0.80. That decomposition is the reportable content: how much of an apparent probe signal is dimensionality, how much is residual-stream anisotropy, and how much is the item span the fitted direction actually lives in.

> Any failure reported here is a measured result about OUR panel, at OUR item budget (160 items), for a PER-CHECKPOINT score. It is never a refutation of AMS, RAS, LatentBiopsy or any published per-prompt number evaluated on its own panel.

## D2b -- first-generated-token identity audit

Panel verdict: **MIXED** {'MIXED': 4, 'CLEAN': 13}. Contaminated checkpoints: **none**.

| checkpoint | class | modal first token | share | delimiter share | verdict |
|---|---|---|---|---|---|
| `AIPlans__TinyLlama-1.1B-IPO-PKU-SafeRLHF` | safety | `Here` | 0.775 | 0.006 | MIXED |
| `AIPlans__TinyLlama-1.1B-ORPO-PKU-SafeRLHF` | safety | `The` | 0.156 | 0.000 | CLEAN |
| `AIPlans__tinyllama-1.1b-dpo-pku-saferlhf` | safety | `To` | 0.212 | 0.006 | MIXED |
| `DreamFast__qwen3-4b-heretic` | abliterated | `**` | 0.119 | 0.000 | CLEAN |
| `Qwen__Qwen3-0.6B` | instruct | `**` | 0.138 | 0.000 | CLEAN |
| `Qwen__Qwen3-0.6B-Base` | base | `Ġâ` | 0.975 | 0.000 | CLEAN |
| `Qwen__Qwen3-1.7B` | instruct | `I` | 0.362 | 0.000 | CLEAN |
| `Qwen__Qwen3-1.7B-Base` | base | `umably` | 0.438 | 0.000 | CLEAN |
| `Qwen__Qwen3-4B` | instruct | `I` | 0.487 | 0.000 | CLEAN |
| `Qwen__Qwen3-4B-Base` | base | `åĽ°éļ¾` | 0.156 | 0.000 | CLEAN |
| `Qwen__Qwen3-4B-SafeRL` | safety | `It` | 0.738 | 0.000 | CLEAN |
| `Shortmund09__MLDM-TinyLlama-1.1b-gcpo-ocra-saferlhf` | safety | `To` | 0.394 | 0.013 | MIXED |
| `TinyLlama__TinyLlama-1.1B-Chat-v1.0` | instruct | `To` | 0.231 | 0.006 | MIXED |
| `TinyLlama__TinyLlama-1.1B-intermediate-step-1431k-3T` | base | `▁I` | 0.300 | 0.000 | CLEAN |
| `huihui-ai__Huihui-Qwen3-0.6B-abliterated-v2` | abliterated | `**` | 0.119 | 0.000 | CLEAN |
| `huihui-ai__Huihui-Qwen3-1.7B-abliterated-v2` | abliterated | `**` | 0.119 | 0.000 | CLEAN |
| `mlabonne__Qwen3-4B-abliterated` | abliterated | `**` | 0.138 | 0.000 | CLEAN |

> The three-way readout bake-off is NOT forced by delimiter contamination. The first generated token is a content token on every harvested checkpoint, so the iteration-1 F3 gate (refusal-drive-vs-judge AUROC 0.750 on Qwen3-4B and 0.391 on its abliterated sibling) is NOT explained by Qwen3's hybrid thinking mode. The prime suspect is eliminated, and the below-chance value has to be explained by something else -- most plausibly that the refusal drive genuinely inverts on an abliterated checkpoint, which is a result rather than a bug. The sibling experiment should spend its GPU time on WHY the drive inverts, not on a delimiter bake-off.

## D0 -- the rescore

- Route: **salvage_p4reads_only**, judge mode **judge_off** ($0.00 spend).
- Empty score cells in the frozen `race_table.csv`: **300 -> 45** (**255 recovered**) across 50 metric rows.
- Metrics computable: **44**; degrade ledger: **9** rows, each with a reason from the pre-registered controlled vocabulary.

### R1 -- the frozen gap-ordering prediction, scored as frozen

Registry prediction (frozen before any measurement): `LEVEL-BEHAVIOUR-STRUCTURE`=1 (smallest gap) < `ACROSS-ITEM`=2 < `LEVEL-KNOWLEDGE`=3 (largest gap).
Observed corrcoef(rank, gap) = **0.156**, lineage-clustered permutation p = **0.3202**.

| family | predicted rank | observed mean gap |
|---|---|---|
| LEVEL-BEHAVIOUR-STRUCTURE | 1 | 0.281 |
| ACROSS-ITEM | 2 | 0.353 |
| LEVEL-KNOWLEDGE | 3 | 0.320 |

This frozen ordering is **not** the same claim as the hypothesis's simpler LEVEL-versus-ACROSS-ITEM split; it is scored as frozen and is not retrofitted to the prose.

Degrade-ledger reason histogram: {'REQUIRES_REFUSAL_DRIVE': 5, 'MISSING_LAYER': 1, 'REQUIRES_PARENT': 1, 'CODE_ERROR': 2}

## D1 -- the user's step 1, answered

Verdict (last prompt token): **DIFFERENT_SUBSPACES**. Judged at the band `w4_L24-27` (safe_vs_heretic), the cell maximising |signed rank-1 cosine| (pre-registered selection rule; 37 cells scanned, Bonferroni p = 1.000). Signed cos = **-0.201**, within-span null p95 = 0.410, null percentile 65.1, one-sided p = 0.350.

- INSIDE_THE_NULL_BAND: the largest overlap anywhere, |cos| = 0.201, sits inside the within-span null (p95 = 0.410). This is the clean form of DIFFERENT_SUBSPACES -- the edits are no more aligned than two arbitrary differences of the same shape and anisotropy.
- The selection maximises over cells, which inflates overlap. That bias works AGAINST a DIFFERENT_SUBSPACES call, so the verdict is conservative.
- First generated token: **DIFFERENT_SUBSPACES**. Best cell `w4_L12-15` (safe_vs_mlab), signed cos 0.396 vs null p95 0.451.

| headline number | value |
|---|---|
| signed_cos_safe_vs_mlab | -0.181 |
| signed_cos_safe_vs_heretic | -0.201 |
| disattenuated_overlap_safe_vs_mlab | -0.183 |
| disattenuated_overlap_safe_vs_heretic | -0.203 |
| null_p95_at_verdict_band | 0.410 |
| r_self_safe | 0.991 |
| r_self_mlab | 0.989 |
| r_self_heretic | 0.991 |
| positive_control_abs_cos | 0.916 |
| positive_control_null_p95 | 0.719 |
| max_abs_signed_cos_anywhere_hs_last | 0.916 |

Mean-difference directions are highly reliable (split-half r_self about 0.99), so disattenuation barely moves the cosines. The low overlap is not produced by noise.

**Anchor.** All five anchor members carry DONE markers: True. Iteration 1's `step1_claim.json` recorded SafeRL and Base as `null` ('anchor lineage incomplete'). It was written during the 3-checkpoint race, and the harvests landed afterwards.

**Template confound (found here, not pre-registered).** mlabonne ships the base-style chat template, so at face value mlab-bearing comparisons are confounded. Resolution: **TEMPLATE_MISMATCH_HAS_NO_MEASURABLE_EFFECT**. mlabonne's chat-template hash differs from instruct's, which on its face confounds every mlab-bearing comparison. It does not. mlabonne's layer-0 (embedding) difference from instruct at the read token is EXACTLY ZERO across all 160 items: the rendered prompt ends in the same token and embed_tokens is unedited. The template texts differ in branches these items never take. The confound is therefore DETECTED AND BOUNDED, not merely flagged, and the mlab-bearing comparisons stand. Caveat: Layer 0 pins the FINAL prompt token only. Earlier tokens could still differ, and would surface from layer 1 on, where attention first mixes the full context. The layer-1 difference norms are reported next to this so the reader can check: mlab's layer-1 difference is of the same order as SafeRL's, and SafeRL is template-identical to instruct, so there is no sign of a rendering jump.

**Internal positive control** (mlabonne__Qwen3-4B-abliterated  vs  DreamFast__qwen3-4b-heretic): passes = **True**. At the last prompt token, the strongest cell has |cos| = 0.916 against null p95 0.719. D1 is therefore powered, not UNDERPOWERED.

**Shared-basis check:** SHARED_BASIS_WEAKLY_SUPPORTED. Median ratio of the base gap to the fine-tune gap = 2.47.

**Weight limb (D1.8):** RAN. Principal angles are computed between per-layer top-16 residual-write subspaces (o_proj, down_proj); the per-band medians are in `results/d1_step1.json` -> weight_limb.

**Highest-value missing harvest:** A SECOND, INDEPENDENT SAFETY-RL FINE-TUNE OF THE SAME Qwen3-4B PARENT (e.g. a public DPO/RLHF-for-harmlessness checkpoint built on Qwen/Qwen3-4B, or one trained in-house on the sibling GPU). All five pre-registered anchors ARE present, so nothing is missing for D1 as specified -- this is the harvest that would close the one hole the results actually expose. The evidence: the abliteration side HAS an internal positive control and it passes decisively (mlabonne vs heretic, |cos| 0.92 at L29 against a null p95 of 0.72, p = 0.001), so 'two independent edits of the same kind converge on one direction' is demonstrated for abliteration. The safety-RL side has n = 1. Qwen3-4B-SafeRL is the only safety-RL member, so 'official safety RL moves a DIFFERENT subspace' currently rests on a single checkpoint and cannot be separated from 'this one checkpoint happens to be idiosyncratic'. A second safety-RL sibling would give that arm the same mlab-vs-heretic style control, turning the headline from one observation into a replicated contrast. It is strictly more valuable than a third abliteration, whose converging behaviour is already established here.
- SHARED-BASIS PREMISE IS WEAK: The base-vs-instruct difference is only 2.5x the fine-tune differences -- the same order of magnitude. The shared-basis premise is WEAK: differences of this size are not obviously small perturbations around a common basis, and every angle below should be read with that caveat.
- TEMPLATE MISMATCH (found here, not pre-registered, and RESOLVED): mlabonne ships the BASE-style chat template while instruct, SafeRL and heretic share the instruct one, and the harvest renders each checkpoint with its own. This would confound every mlab-bearing comparison, but mlabonne's layer-0 embedding difference from instruct is EXACTLY ZERO on all 160 items, so the rendered prompt is effectively identical at the read position and the mismatch does not bite. Listed because a reader checking the metadata will see the hash mismatch and should not have to re-derive this.
- The brief's premise that the base checkpoint uses the plain renderer is FALSE in the realised harvest: Qwen3-4B-Base ships a chat template and was rendered with renderer='chat'. The base stratum separation is justified by training stage, not by renderer.
- n = 160 items is the whole budget. Every overlap here is attenuated by sampling noise, which is exactly what the split-half floor quantifies; read raw and disattenuated together and neither alone.

## D3 -- the within-family and size-ladder table

> This is a WITHIN-FAMILY table. The 17 finished harvests span only Qwen3 and TinyLlama, so this lane supports ZERO held-out-FAMILY answer; the family axis belongs to the sibling experiment.

> **With only 2 families and three sizes, family label and parameter count NEARLY DETERMINE the three-way class. The family label alone reaches held-out balanced accuracy 0.188 (3-way) and 0.375 (2-way); size alone reaches 0.050 and 0.375. Only 17 of 42 scored metrics beat the family-only baseline. If the family label alone predicts the ground truth as well as the metric does, THE METRIC HAS NOT EARNED ITS FORWARD PASSES.**

| baseline | held-out balacc 3-way | held-out balacc 2-way |
|---|---|---|
| family label alone | 0.188 | 0.375 |
| log10(parameters) alone | 0.050 | 0.375 |

Size ladder (Qwen3 0.6B / 1.7B / 4B, each with base, instruct and an abliterated sibling): **12** metrics flip the sign of the instruct-minus-abliterated contrast across the ladder; **2** track log-parameters across the honest instruct arm at |rho| above the detectable threshold and are labelled as reading size, not safety.

`results/race_table_v2.csv` -- schema `race_table_v2.1`, a **strict superset** of the frozen 18-column `race_table.csv` (frozen columns first, in their frozen order and names; new columns appended after).

**AMS row.** Published 71% leave-one-out figure: `NON_COMPARABLE` -- That protocol held out only the THRESHOLD, not the direction: the direction was fitted on the same 16 contrastive pairs it was then measured on. Our table reports AMS twice -- in its published IN-SAMPLE form (k_ams_sep_insample) and cross-fitted on our folds (k_ams_sep_cf) -- with the gap printed. AMS's own headline r = -0.546 has a NON-SIGNIFICANT Spearman rho = -0.423 at n = 14; the detectable |rho| at n=14 is 0.543.

## D4 -- bounded prior-art check

14 of at most 15 queries; backends ['general_web_search', 'arxiv_abs_fetch']. Scholarly-mode (OpenAlex/Crossref) was deliberately NOT used, per instructions that it was previously found unusable for this field. All 14 discovery queries used general web search (the aii-web-tools free-first stack: ddgs/marginalia general engines, exa/Serper fallback). All arXiv-ID verification (12 pre-seeded IDs + 2 new IDs this pass introduces) was done by fetching https://arxiv.org/abs/<id> directly, which is a fetch, not a search, and so is not counted against the 15-query budget.

**Q1 = OPEN** -- Has anyone reported that linear-probe or difference-in-means directions in LLM residual streams FAIL to beat ANISOTROPY-MATCHED (not isotropic-Gaussian) random directions, specifically for safety readouts on a PER-CHECKPOINT axis (one score per model checkpoint used to rank/classify checkpoints), with the null drawn from the checkpoint's own residual covariance / item span?

The covariance/anisotropy-matched-null mechanic exists in the literature (2605.12726, 2608.12652, and newly-found 2609.14759), and the random-direction-control method itself is well established (2406.11717) and negative results about baseline construction for abliteration exist (2603.22061). But in every case found, the anisotropic/covariance null is applied either (a) within one model to diagnose a probe's failure mode, or (b) to a different task (benchmark contamination, or a moral-subspace projection compared across model families), never to a PER-CHECKPOINT safety score used to rank or classify checkpoints against each other. No paper reports a safety probe/diff-in-means direction LOSING to a covariance- or item-span-matched null when the axis is 'one score per checkpoint'.

- `2605.12726` Before the Last Token: Diagnosing Final-Token Safety Probe Failures <https://arxiv.org/abs/2605.12726> -- Closest covariance-matched-null mechanic (contrasts isotropic-random vs covariance-random perturbations for a diff-of-means safety probe), but it is a within-model prefill-time failure diagnosis on SafeSwitch-style probes across 3 models, not a cross-checkpoint ranking score, and the probe does not lose to the null in this paper. [UPHELD]
- `2608.12652` Excess Separability: Nuisance-Controlled Residual-Stream Probing for Benchmark Contamination Detection <https://arxiv.org/abs/2608.12652> -- Same isotropic-vs-anisotropic null machinery (explicitly names 'anisotropy' as a nuisance the null must match) and even reports a negative result (the correction that survives measurement carries MORE variance than the null it is tested against), but the application is benchmark-contamination detection, not safety, and not a per-checkpoint ranking axis. [UPHELD]
- `2603.22061` On the Failure of Topic-Matched Contrast Baselines in Multi-Directional Refusal Abliteration <https://arxiv.org/abs/2603.22061> -- A genuine baseline-construction negative result in the refusal-abliteration space (topic-matched contrast pairs for building abliteration directions on Qwen 3.5 2B), but the baseline being tested is a topic-matched CONTRAST PAIR, not an anisotropy/covariance-matched RANDOM-DIRECTION null, and it is about direction construction, not a per-checkpoint probe score. [UPHELD]
- `2406.11717` Refusal in Language Models Is Mediated by a Single Direction <https://arxiv.org/abs/2406.11717> -- Establishes the random-direction-control method itself for refusal directions (Arditi et al., NeurIPS 2024); the refusal direction beats this (isotropic, not covariance-matched) control by a wide margin, so this is the positive result the narrow question is asking whether anyone has since overturned on a covariance-matched, per-checkpoint axis -- nobody has. [UPHELD]

Gap we fill: No paper tests whether a diff-in-means/linear-probe safety direction, scored once per checkpoint across a population of checkpoints for ranking/classification, survives a null built from that checkpoint's own residual covariance or item span rather than an isotropic Gaussian; the covariance-matched-null tooling exists (2605.12726, 2608.12652, 2609.14759) but has never been pointed at the per-checkpoint safety-ranking use case.

**Q2 = PARTIAL** -- Has anyone related a recovered ABLATION STRENGTH (parent-free, recovered from the weights of an unknown checkpoint) to MEASURED harmful compliance as a graded, monotone read rather than a binary tamper flag?

The pieces still exist only separately. Weight-forensic audits that are parent-free and work on unknown checkpoints (2607.01854, 2508.00161) report BINARY classification (abliterated vs not), never a graded strength-to-compliance regression. Papers that DO report graded/dose-response links between an internal signal and measured compliance (2608.05578 AMS: r=-0.546 activation-geometry severity vs compliance, n=14; 2510.02768: dose-response over 0.3-1.2 ablation weights; and a newly-found adjacent result, 2604.08844: rho=0.72 geometry-to-behavior rank correlation) either use activation geometry rather than a weight-space strength scalar, or use EXPERIMENTER-SET/manufactured strengths rather than a strength RECOVERED from an unknown checkpoint's weights, or (2604.08844) explicitly fail to generalize their weight-geometry severity signal across method families (AUC~0.00 going from DPO adapters to steering-derived adapters), which is direct evidence that a transferable recovered-strength-to-compliance read for arbitrary unknown checkpoints remains unbuilt. An independent industry survey (abliteration.org, Aug 2026) corroborates this from the practitioner side: it states plainly that binary abliteration detection is 'roughly solved' (AUROC ~0.95) but that no published work outputs even a discrete multi-class method label from weights alone, let alone a continuous graded strength.

- `2607.01854` Has This Checkpoint Been Abliterated? A Two-Signal Audit and Its Failure Map <https://arxiv.org/abs/2607.01854> -- Recovers a parent-free weight-recovery-energy signal from an unknown checkpoint's weights, closest to the 'recovered ablation strength' half of Q2, but reports it as a BINARY audit (AUROC 0.95, balanced accuracy 0.89 over 273 checkpoints) and never regresses the signal against measured harmful-compliance rate. [UPHELD]
- `2608.05578` Detecting Safety Training Modification in Language Models via Activation Analysis (AMS) <https://arxiv.org/abs/2608.05578> -- Gives the graded half: activation-severity correlates with measured jailbreak compliance (r=-0.546, p=0.043, n=14), but the recovered signal is activation geometry over labelled prompts, not a parent-free weight-space strength scalar recovered from an unknown checkpoint. [UPHELD]
- `2510.02768` A Granular Study of Safety Pretraining under Model Abliteration <https://arxiv.org/abs/2510.02768> -- Establishes genuine dose-response (ablation weights 0.3/0.5/0.8/1.0/1.2 give graded REFUSE/EVASIVE/COMPLY; zero-refusal arms at 92-98% harmful compliance), but the strengths are EXPERIMENTER-SET during the ablation, not recovered post hoc from an unknown checkpoint's weights. [UPHELD]
- `2508.00161` Watch the Weights: Unsupervised monitoring and control of fine-tuned LLMs <https://arxiv.org/abs/2508.00161> -- Same weight-forensics family as 2607.01854 (unsupervised, distribution-free monitoring of fine-tuned/backdoored LLMs from weights alone) but never correlates any recovered signal with measured compliance rate at all, graded or binary. [UPHELD]

Gap we fill: No paper takes a parent-free ablation-strength scalar recovered from an UNKNOWN checkpoint's weights (as opposed to an experimenter-set dial, a LoRA-fine-tuning-objective geometry signal, or an activation-geometry severity score) and regresses it against measured harmful-compliance rate as a graded, monotone read; the closest attempt at exactly that regression (2604.08844) is confined to LoRA/DPO adapters and explicitly fails to generalize to the ablation/steering method family.

arXiv ID resolvability: 14 checked, **0 not OK**.

## Statistical hygiene applied everywhere

- Resampling unit is the LINEAGE; bootstraps resample lineages; `n_lineages` is printed beside every aggregate.
- Pearson **and** Spearman for every correlation, both with Fisher-z CIs (Spearman with the 1.06 variance-inflation factor).
- Beside any correlation at n < 10 the **detectable |rho|** at that n is printed: 0.823 at n=6, 0.717 at n=8, 0.643 at n=10, 0.543 at n=14, 0.492 at n=17. *(The plan printed 0.472 at n=17; the stated formula tanh(1.96*sqrt(1.06/(n-3))) gives 0.492. We publish what the formula produces and flag the discrepancy.)*
- Benjamini-Hochberg within each declared family of tests; raw p and q side by side.
- Every null is a DISTRIBUTION with B stated, never a best-of-N point estimate.
- No metric is evaluated on a checkpoint used to choose its layer or threshold; the primary D2 arm makes no selection at all.
- Matched lexical floors inherited from iteration 1: JBB Index-paired 0.537, XSTest twins 0.655. The cross-source 0.963 is printed but is **NOT a floor**.

## Fold verification

The frozen `fold` column is used as **primary**. Verified: it respects `twin_group` -- **0 of 128 groups straddle a fold boundary** (respects_groups = True). A grouped-stratified reassignment over 5 seeds is reported as a labelled SECONDARY analysis.

## Limitations

- WITHIN-FAMILY ONLY. The 17 finished harvests span exactly two model families (Qwen3 and TinyLlama). This artifact supports ZERO held-out-FAMILY answer. Every number here is a within-family number and the family axis belongs to the sibling experiment.
- ITEM BUDGET ~160 (harmful 64, benign_alarming 32, xstest_contrast 32, plain_benign 32). Every AUROC is computed over at most 160 items, and the within-span null is defined by that same span.
- n_lineages = 4 . The resampling unit is the LINEAGE, so every lineage-clustered bootstrap here resamples 4 clusters. That is a SMALL resampling base and the intervals should be read as indicative, not as precise coverage statements.
- PER-CHECKPOINT AXIS. Any negative result here is about a PER-CHECKPOINT score on OUR panel at OUR item budget. It is never a refutation of AMS, RAS, LatentBiopsy or any published PER-PROMPT number evaluated on its own panel.
- NO NEW COMPUTE. This artifact ran no model inference, downloaded nothing and used no GPU. It re-analyses the activation and weight tensors iteration 1 left on disk, so it inherits every harvesting choice iteration 1 made, including the 16 substituted AMS pairs and the four unpinned N-GLARE choices.
- THE FOUR INCUMBENTS WERE ALREADY NON-COMPARABLE for four different named reasons recorded in UP/INCUMBENTS.md; those named gaps are carried forward verbatim rather than re-derived, and this artifact does not close any of them.
- LAYER SELECTION. The primary D2 arm reads at a FIXED depth fraction of 0.60 and makes no per-checkpoint selection. The secondary L_star arm reproduces iteration 1's argmax-over-layers, and there the same argmax is applied to every null draw; its null uses B=200 rather than the pre-registered B=1000, declared as a deviation.
- The base checkpoints use a different renderer and sit in their own stratum; they are a scale reference and are never mixed into the three-way class comparison.
- The plan's printed detectable |rho| at n=17 was 0.472; the stated formula tanh(1.96*sqrt(1.06/(n-3))) gives 0.492. This artifact publishes the value its own formula produces and flags the discrepancy.

