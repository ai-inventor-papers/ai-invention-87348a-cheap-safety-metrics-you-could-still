## G. LOAD-BEARING NUMBERS N1–N5, AND THE DECISION EACH ONE TRIGGERS

Every quote below was grepped from the paper's **PDF** (not a plain HTML fetch) and re-verified. The headline result of this section is that **nothing the hypothesis leans on is a misattribution** — but two of the five change what we are allowed to say.

### N1 — arXiv 2507.11878, "LLMs Encode Harmfulness and Refusal Separately" (NeurIPS 2025; v5 6 Jul 2026) — **CONFIRMED**, and it costs us a sentence

> "We also find that adversarially finetuning models to accept harmful instructions has minimal impact on the model's internal belief of harmfulness."

> "our Latent Guard achieves performance comparable to or better than Llama Guard 3 8B … reducing over-refusals"

Table 3 example: Qwen2 persuasion detection, Latent Guard **75.0%** vs Llama Guard 3 8B **17.8%**.

**The decisive sub-question — answered.** Latent Guard is a **per-prompt classifier on a fixed model**, not a per-model score:

> "For an incoming instruction, the Latent Guard model computes the belief of harmfulness ∆harmful following Equation 3. If ∆harmful is negative, the instruction will be classified as harmless, and vice versa."

and it is fitted per base model from labelled data:

> "We sample 100 harmful and 100 harmless examples from the training set (see details in Appendix B) to compute the centroid of clusters."

**DECISION D1 (binding).** Our motivating sentence "internals have never beaten outputs" is **false as written** and must be replaced by the scoped version: *per-PROMPT internal classifiers have already beaten output-based guards, on a fixed model, using ~200 labelled examples per model; what has not been shown is a per-CHECKPOINT scalar that transfers to unseen uploaders.* The distinction is verified, not assumed — and it is the only thing holding the motivation up. It is also **narrowed further** by arXiv:2608.08029 (8 Aug 2026), which reproduces such probes across Gemma-4-E4B, Mistral-7B-v0.3 and Qwen2-7B "with F1 scores within a point of the values reported for LLaMA-3.1-8B" — so per-prompt latent probes transfer across families too. The per-checkpoint/per-prompt axis is now the *whole* of the gap; write the motivation on that axis alone.

### N2 — arXiv 2603.05773 (DSH), recognition vs execution — **CONFIRMED**

> "we uncover a critical architectural divergence, contrasting the Explicit Semantic Control of Llama3.1 with the Latent Distributed Control of Qwen2.5."

Confirmed as a central, repeated finding (abstract, intro contributions, §4.2/4.3, conclusion), alongside the "Knowing without Acting" double dissociation.

**DECISION D2.** Any candidate with a fitted direction must report **Qwen-held-out separately rather than pooled**, and the choice of Qwen as the anchor lineage must be written up as a **stated risk**, not an incidental convenience: the anchor family is precisely the one whose control is latent/distributed rather than explicitly semantic. Compounded by N3 below.

### N3 — arXiv 2609.14759, harm-keyed routing — **CONFIRMED** on all three targets

> "refusal levels off at the level of a single harm direction, and about three-quarters of refusal's causal input lies outside the moral subspace altogether."

> "Qwen reads beyond the single harm cue but is unresolved at our sample size"

Quantified in their Figure 4: refusal transfer "saturates at the harm rank-1 level (0.25; 95% CI bars over twins)" while judgment "climbs (reads the whole subspace)" to 0.66 at rank 16. For Qwen the refusal point estimate (0.54) exceeds the harm-rank-1 level (0.38), but the gap to judgment (0.12) is **not resolved against their 0.10 plateau tolerance at 19 twins** — verdict indeterminate.

**DECISION D3.** Quote the rank-1 saturation as the *reason* our battery spends no metrics on higher-rank refusal subspaces — a multi-direction refusal readout is capped in what it can add over a single direction. And note that the "Qwen unresolved" sentence compounds D2: our anchor lineage is the one the nearest paper could not resolve.

### N4 — arXiv 2604.18901 — **AMBIGUOUS-MULTIPLE-OCCURRENCES, and this is good news**

This was the highest-risk item, and the pre-committed procedure (grep the whole PDF, report every occurrence before declaring a misattribution) paid off. **Both readings of both numbers are genuinely present as two distinct true findings each.** There is no misattribution to correct.

- **0.003 reading (a) — SUPPORTED.** Own-fitted-direction abliteration invariance: "±0.003 AUROC" between each variant's own-direction instruct vs abliterated performance (Abstract, Findings #2, §3.2 first paragraph, Discussion).
- **0.003 reading (b) — SUPPORTED.** A *different* quantity: instruct→abliterated cross-variant **transfer** degradation "≤0.003" at direction angles "11° to 42°" (§3.2, second paragraph after Table 1).
- **73° reading (a) — SUPPORTED.** Protocol angle: max-pool-over-content vs last-token-post-instruction recover directions "73° ± 7°" apart at the same layer (Abstract, Findings #3).
- **73° reading (b) — SUPPORTED.** Gemma-3's base-to-instruct rotation of 73°, co-occurring with ΔAUROC −0.057 and TPR 0.751 → 0.175 (§3.2, Table 1's B↔I cell, Discussion).
- **A third, unrelated 73 exists** — "73.4° ± 12.3°" between wLDA and an angular two-class strategy (§3.3 / Table 9). It is neither target reading. Do not cite it as if it were.

**DECISION D4.** Reading (a) of 0.003 is the one the harm-knowledge-invariance premise needs, and it is supported — the premise stands and does **not** need re-sourcing. Nonetheless **cite arXiv:2603.27412 (LatentBiopsy) alongside it**, because that paper measures the same invariance on exactly the Qwen base/instruct/abliterated triplets this run uses: "both abliterated variants achieve AUROC at most 0.015 below their instruction-tuned counterparts, establishing a geometric dissociation between harmful-intent representation and the downstream generative refusal mechanism" (Qwen3.5-0.8B and Qwen2.5-0.5B triplets). Reading (a) of 73° is supported, so the requirement to **fix the extraction protocol in advance** stands on its cited basis rather than on general grounds. **Standing prohibition for every downstream artifact: when citing either number, name which of the two readings you mean.**

### N5 — arXiv 2606.16349 — **CONFIRMED**, and it forces a pre-registration

- Eq 9 confirmed: `HRCI_repr(t) = ½·C_cos(t) + ½·C_sub(t)`, with `C_sub` (via Eq 8, principal angles) explicitly "the average squared canonical correlation". *Caveat recorded honestly:* whether `C_cos` literally carries absolute-value bars could not be pixel-verified — PDF-to-text garbled the bar/norm glyphs in Eq 7. Treat `C_cos` as "directional alignment (inner-product/cosine based)" and choose the absolute value as our default, flagging it.
- SFT reaches low coupling without robustness: SFT reaches full-HRCI values close to late R2D2 by step 50 but "remains high-ASR throughout the five-anchor window".
- The authors' own verdict, verbatim: **"Thus low coupling is not a safety score."**
- All six numbers confirmed exactly: HRCI_repr 0.0784 @ step 50 → 0.0205 @ step 500, a 73.9% drop; fixed-source ASR 0 → 0.2500; XSTest refusal 1.00 → 0.2280; SFT control 0.0217 → 0.0190.
- Access class: HRCI_repr is **per-checkpoint** but **not prompt-free** — it is recomputed at each checkpoint from freshly extracted **labelled** harmful/benign and refusal/compliance contrastive prompt sets. The word "parent-free" does not appear in the paper (0 matches). The exact prompt count per carrier was not located and is left as an open follow-up rather than guessed.

**DECISION D5 (binding pre-registration).** **C1 is pre-registered as a DISCRIMINATOR ONLY and explicitly NOT as a predictor of harmful compliance.** The paper must say this in advance, citing 2606.16349, rather than discover it. And C1 must beat `HRCI_repr` — a baseline of a few lines — or it has no story.
