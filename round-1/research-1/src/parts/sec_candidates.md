## F. CANDIDATE SATURATION — C1 to C5, searched 2026-09-20

**Verdict rule applied without softening.** CLOSED = a paper computes substantially the same quantity on substantially the same unit of analysis and reports it against a comparable outcome. PARTIAL = same quantity, different unit (per-prompt vs per-checkpoint), OR same unit, weaker outcome. OPEN = neither, and at least three distinct query formulations were run.

**A tooling finding that downstream artifacts must know.** The `aii-web-tools` **scholarly mode (OpenAlex/Crossref) is unusable for this field.** Every scholarly-mode query returned off-topic results — "coupling between harm representation and refusal direction predicts safety" returned brand-crisis marketing papers, service-robot reviews and oncology scoping reviews; "activation probe versus behavioral evaluation sample efficiency crossover" returned stochastic resonance and polymer photophysics. All usable coverage came from general-mode search over arXiv / ACL Anthology / OpenReview. **An empty scholarly-mode result is evidence about the backend, not about the field.** The plan's requirement of "one scholarly query per candidate" was executed and is recorded, but it contributed nothing; the substantive queries were general-mode, and a 2026-restricted query was run for each candidate.

| id | verdict | nearest paper | what is left that is ours |
|---|---|---|---|
| C1 per-checkpoint harm×refusal coupling | **PARTIAL** | 2606.16349 (HRCI_repr) | PER-CHECKPOINT ∧ CROSS-FITTED ∧ DISCRIMINATOR-NOT-PREDICTOR |
| C2 prompt-budget crossover | **PARTIAL** | 2608.13329 (probe direction is a property of its prompt) | the CROSSOVER POINT ITSELF at matched budget |
| C3 refusal-depth minus content-depth | **OPEN** (as an aggregation only) | 2609.00760 (commit-then-specify) | PER-CHECKPOINT ∧ DIFFERENCE-OF-TWO-DEPTHS ∧ CORRELATED-WITH-AN-OUTCOME |
| C4 parent-free graded edit strength | **OPEN** (on a four-way conjunction) | 2607.01854 (two-signal audit) | WEIGHTS-ONLY ∧ PARENT-FREE ∧ GRADED ∧ PREDICTS-COMPLIANCE |
| C5 hidden-state metamodel vs lineage probe | **OPEN** (on the ablation) | 2608.14929 (centered residual signatures) | SAME-FEATURES ∧ HELD-OUT-LINEAGE ∧ ABLATED-AGAINST-IDENTITY |

### C1 — PARTIAL
The adverse incumbent was not rediscovered but started from: **arXiv:2606.16349** defines a parent-free, single-checkpoint harmfulness–refusal coupling index and tracks it over fine-tuning, and its authors conclude that low coupling is not a safety score (verified verbatim — see N5). **C1 is therefore at best PARTIAL as a predictor.** Its surviving margin is the discriminator role plus cross-fitting. It must be pre-registered as a discriminator and explicitly *not* as a predictor of harmful compliance (decision D5), and it must beat `HRCI_repr` — a baseline implementable in a few lines. A candidate that does not beat a few-line published baseline has no story.

Also in this lane and newly relevant: **arXiv:2606.25750 (RAS)** publishes a per-checkpoint internal score that already separates aligned / uncensored / abliterated, and **arXiv:2607.00572 (HARC)** uses the same coupling construct as a training objective. Neither is parent-free.

### C2 — PARTIAL
The behavioural half is **closed twice over**: arXiv:2608.05086 (IRT for AI Safety — 8 benchmarks, 192 models, three factors of refusal strictness / truthfulness / contextual harm, "roughly ten adaptively chosen items suffice for several individual benchmarks, cutting evaluation cost by 97–99%") and arXiv:2606.20626 (ICML 2026 — adaptive item selection cutting cost "by at least 80% … and by up to 99.9% on AIR-Bench 2024", plus a fixed reusable subset at up to 99.8%).

The genuinely adverse hit is on the **internal** side. **arXiv:2608.13329, "A Probe Direction Is a Property of Its Prompt"**, applies generalizability theory to an internal probe readout, decomposes its variance into model, prompt and model×prompt components, and concludes:

> "We conclude that a single-prompt design cannot support comparison between models, and we give the number of prompts a defensible comparison requires."

> "The generalizability coefficient for a design that must generalize across families with one wrapper is 0.00002, which is to say that cross-family comparison on a single wrapper carries no information about models at all."

**And the prescription is concrete enough to adopt.** Their own design crosses **36 wrappers**, and they state what a defensible comparison needs:

> "A defensible comparison needs every prompt's score reported, both arms of the contrast crossed, a content-free direction scored under the same convention, and many prompts where current practice uses one."

That is four requirements, not a single integer: (i) per-prompt scores reported, not just an aggregate; (ii) both arms of the contrast crossed; (iii) a **content-free control direction** scored under the same convention; (iv) many prompts where current practice uses one. Requirement (iii) is the sharpest for us — they find "a direction carrying no information about evaluation at all still reproduces a substantial fraction of each published score", which is a content-free null that our battery should carry for every fitted-direction metric.

That second sentence is a **direct threat to the run's headline framing** — a 0-to-few-prompt internal score compared across families on a single prompt rendering is, by their measurement, uninformative about models. Our prompt-budget claims must either adopt a prompt-varying design or concede this explicitly in the limitations. What remains ours is narrow but real: **the crossover point** at which a graded internal readout and a binary generation-based readout attain equal discriminative power on the same checkpoints. IRT owns few-items on the text side; 2608.13329 owns the variance decomposition on the internal side; no source puts them on one axis.

### C3 — OPEN, as an aggregation only
Per-prompt and per-condition layer-emergence curves are thoroughly published — arXiv:2609.00760 (EMNLP 2026) characterises refusal as "a commit-then-specify process: a shared initial mechanism commits to refusing, then type-specific features in later layers specify whether the grounds are epistemic or normative", and arXiv:2605.28553 shows refusal is decodable from intermediate activations before decoding. What no source found does is collapse **the difference of two layer indices into a single per-checkpoint scalar** and correlate it with anything. That is a modest margin and is claimed here at exactly that strength.

**Named confound imported into the plan:** arXiv:2609.03887 (EMNLP 2026) shows the post-training *method* — SFT vs reasoning-augmented FT vs ORPO — independently reshapes where refusal is computed, across Llama-3.1-8B, Gemma-2-9B and Qwen3-8B. A depth-difference scalar therefore risks reading training recipe rather than safety level, and the screen must carry a recipe control.

### C4 — OPEN, on a four-way conjunction; the most valuable verdict in this artifact
Three sub-questions are each already closed, and the conjunction is what survives.

- **Binary parent-free detection is CLOSED** by the Jorak / Model Scanner community tool, which is explicit about it: "**Reference-free** detection of **abliteration** in open-source LLMs … **without access to the original model**", with three techniques (weights/SVD global `A`, band `B` and subspace `S` alignment; activation axis health via Cohen's d; behavioural refusal rate) classified into `censored` / `ablated` / `finetuned_decensored` / `ambiguous`. This is conceded prior art on the *instrument* and must be cited, not claimed.
- **Parent-anchored detection is CLOSED** by arXiv:2607.01854, which combines a reference-anchored activation refusal-gap `rho` with the rank-1 weight-recovery energy `E1` of the base-to-candidate weight difference: "we z-standardize each on a reference population and sum: s(Mc) = z(−rho) + z(E1)". AUROC 0.95 in-sample over a 273-checkpoint registry, leave-one-family-out balanced accuracy 0.89 (FPR 0.11), missing 4 of 57; ΔAUROC +0.10 over the gap (95% CI [0.04, 0.18]) and +0.04 over E1 ([0.005, 0.09]); the two signals correlate at r = −0.41. But it is explicit that it is not parent-free: "it presumes an attested reference".
- **Graded internal-statistic-vs-compliance is CLOSED on activations** by AMS (r = −0.546 against compliance; see section B).

**What no source found does is relate a RECOVERED WEIGHT-SPACE EDIT STRENGTH, obtained without a parent, to MEASURED harmful compliance on a continuous scale.** Every published weight-side result is a binary flag or a bucket label. The surviving margin is the full conjunction **WEIGHTS-ONLY ∧ PARENT-FREE ∧ GRADED ∧ PREDICTS-COMPLIANCE**; dropping any one conjunct lands on a published result.

A secondary source maps the same frontier independently and agrees, which raises confidence: the abliteration.org wiki survey (updated 2026-08-30) states "As of August 2026: whether a model was abliterated is roughly solved. Which method is open", and lists as a gap "**Weights-only operation.** Both leading detectors need forward passes (activation gap) or at least a trusted base (weight diff). A truly novel benchmark should test whether method can be recovered from candidate weights alone, without an attested base. This is the hardest and most useful setting." This is a community wiki and is used here only as triangulation, never as a citable primary claim.

**Null model status re-verified:** RMT / Marchenko–Pastur / WeightWatcher / HTSR applied specifically to **edit detection** (as opposed to pruning — arXiv:2606.02608, arXiv:2503.01922; grokking/overfitting — arXiv:2605.12394, ICML 2026; or generalisation prediction) returned no 2026 hit. Still open, still the intended null model.

### C5 — OPEN, on the ablation
Both halves are individually well occupied. Lineage and provenance are recoverable from weights (arXiv:2607.10617 modelDNA; arXiv:2511.06390 SVD-fingerprint), from residual-stream signatures (arXiv:2608.14929, "can weights alone reveal whether two compatible model checkpoints share ancestry?"), and even from output distributions alone (arXiv:2608.08139 TokenPrint; arXiv:2607.10252). Benchmark scores are predictable from item subsets (arXiv:2506.07673, NeurIPS 2025) and from other benchmark scores (arXiv:2606.24020, to within 3.93 points).

No source found trains a hidden-state performance predictor and then **ablates it against an architecture/lineage-identity probe on the same features**. That absence is precisely why the ablation, not the metamodel, is the contribution. Pre-register the negative: if the metamodel does not beat an identity probe on held-out lineages, the honest headline is that hidden-state safety prediction is largely lineage recognition — which is publishable, and cheaper to pre-register than to discover.

### Part 2b — recency sweep, 2026-08 and 2026-09
Newer than the hypothesis's citation list, in order of how much they cost us if missed:
1. **arXiv:2606.25750 (RAS)** — a fourth incumbent on the deliverable itself. Biggest miss.
2. **arXiv:2608.13329** — adverse to the few-prompt cross-family framing (see C2).
3. **arXiv:2608.08029** (8 Aug 2026) — reproduces latent-space safety probes across Gemma-4-E4B, Mistral-7B-v0.3 and Qwen2-7B and finds "the original MLP probe architecture extends to other model families with F1 scores within a point of the values reported for LLaMA-3.1-8B". This *sharpens* D1: per-prompt latent probes transfer across families; the unsolved thing is the per-checkpoint score.
4. **arXiv:2609.06934** (Sep 2026) — post-hoc safety as a thin, sharp, near-orthogonal weight update; parent-dependent, so not a competitor on access class, but it publishes the mechanism our forgery-cost axis leans on. Cite, do not claim.
5. **arXiv:2609.00760** and **arXiv:2609.03887** (both EMNLP 2026 Main) — nearest paper and named confound for C3.
6. **arXiv:2608.07514** (TMLR 03/2026) — "16 open technical challenges for open-weight model safety"; useful for positioning the deliverable as an acknowledged gap rather than an invented one.
