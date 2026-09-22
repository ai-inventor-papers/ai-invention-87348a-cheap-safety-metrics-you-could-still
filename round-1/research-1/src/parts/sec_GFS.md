## C. INCUMBENT 2 — Skin-Deep / GFS, arXiv 2606.22676

"Skin-Deep: A Geometric Diagnostic for Alignment Fragility in Large Language Model Representations", Lee et al., 21 Jun 2026 (cs.AI, preprint; no venue acceptance found). **Public code: https://github.com/js-lee-AI/skin-deep (MIT).**

**Two findings here overturn what the plan assumed about this incumbent.** Both are good for us, and both must be stated plainly rather than left implicit.

### C.1 GFS is NOT parent-free and NOT reference-free — it is in a different access class entirely

> "Setup. Let M be an aligned causal transformer and M0 its base counterpart, both with L layers and hidden size d… We use a safety set D_safe of harmful-request prompts that an aligned model should refuse and a general set D_gen of benign instructions, matched in size and token length."

The direction is defined by **contrastive PCA against the base model's covariance**:

`v_cPCA_l = argmax_{‖v‖=1} vᵀ (Sigma_inst_l − alpha·Sigma_base_l) v`  (Eq 1), with `alpha = 100` fixed at every layer.

So computing GFS requires forward passes through **both the aligned model and its base counterpart**. The plan's flagged risk was correct and is now confirmed from the source: GFS needs `M0` *and* `D_safe`.

**Prompt budget: 1000 prompts** — 500 harmful (AdvBench 200 + HarmBench 200 + BeaverTails 100) and 500 benign (Alpaca 250 + OASST 250), token-matched. No generation required.

**Consequence.** GFS is a **partial competitor, not a matched one**: it sits at *parent-required × 1000-prompt*, while the commissioned deliverable sits at *parent-free × 0-to-few-prompt*. That is a two-axis gap, and it is worth a paragraph and a row in the comparability table — not silence.

### C.2 The statistic

`GFS(M) = Σ_{l=1}^{L} w_l · |d_l| · (1 − |cos(v_l, v_Arditi_l)|)`  (Eq 3)

per layer `l`: `d_l` is Cohen's d of the harmful-vs-benign separation along the layer's cPCA direction; `v_Arditi_l` is the Arditi-style difference-of-means refusal direction; `w_l ∝ l/L` is a linear depth weight. Activations are residual-stream at the **final token position** (a chat-template variant uses the final *attended* token). Summed over **all** layers. No threshold rule: GFS is reported as a continuous ranking score, and no cutoff is printed (**UNSTATED-IN-SOURCE**).

A token-position ablation (Appendix Table 10, 5 models) is worth importing into our own protocol: first-token extraction collapses to peak |d| ≤ 0.27, while mean-pooling retains a coherent late-layer signal (peak |d| 1.98–4.63). **Extraction position is load-bearing**, which is the same lesson N4's 73° protocol angle teaches.

### C.3 The retention claim has **no printed coefficient** — there is no number to make a bar out of

This is the second overturned assumption, and it changes what the payoff executor can do.

- Panel: 21 instruction-tuned models, 6 alignment recipes, 3B–32B — confirmed. But the GFS-vs-LoRA-retention analysis runs on a **core set of 4 models** (Llama-3.1-8B-Instruct, Qwen-2.5-7B-Instruct, Mistral-7B-v0.3-Instruct, Gemma-2-9B) plus a **3-model hold-out** (Tulu-3-8B-DPO, Qwen-2.5-3B, Qwen-2.5-14B) — **n = 7**, not 21.
- **No Spearman, no Kendall, no rank-accuracy percentage is reported.** The claim is a *qualitative co-occurrence*: the lowest-GFS core model (Gemma-2-9B) is the one that retains refusal after small-scale LoRA fine-tuning. The paper's own Limitations section calls for "future predictive validation of GFS".
- What *is* quantified: cPCA subspace separation (peak |d| ≥ 1.8 on all 4 core models, probe accuracy ≥ 0.90, held-out split-sample `d_test` ≥ 2.71, Table 1) and cross-family recurrence (peak-layer linear CKA 0.676–0.881 across all 6 inter-family pairs, all above a prompt-shuffle null at p < 0.001, Table 4).

**Bar row verdict: `comparable: false`, reason = NO QUANTITATIVE PREDICTIVE STATISTIC PRINTED.** The plan instructed that "GFS's reported retention-prediction number, at its n = 21, is the number our H7 limb must be stated against". **That number does not exist.** The honest row is: *GFS's retention claim is a qualitative co-occurrence at n = 7 with no coefficient; if our transfer limb reports a coefficient with a CI at any n, that is a strictly stronger claim than the incumbent's, and we should say so in exactly those words rather than inventing a GFS number to beat.* This is the kind of row a reviewer checks, so it must be right.

### C.4 Held-out protocol and reimplementation

Held out: a 20 % probe split for `alpha` selection and split-sample `d_test`; the 3-model LoRA hold-out; 50 held-out harmful prompts for post-LoRA compliance. **Not** held out: GFS itself is computed on the same 500+500 prompt set used to select `alpha` and report the headline separation, and the 4 core models were used to tune the pipeline.

**Verdict: PARTIALLY-REPRODUCIBLE**, and the code closes most of the gap. From the prose alone, two things are under-specified: the proportionality constant of `w_l ∝ l/L`, and the exact Cohen's d variant (pooled vs per-class SD). The public repo fixes last-token/all-layer raw-prompt extraction as the default path and `alpha = 100`, and implements Cohen's d / cPCA / MMD / PERMANOVA / BH-FDR in `common_utils.py` — but its default `--models` flag covers only the 4 core models, not the 21-model pool.

### C.5 A near-ID collision that will otherwise bite a later artifact

**arXiv 2606.22676 is Skin-Deep. arXiv 2606.226*8*6 is a different paper** — "The Geometry of Refusal: Linear Instability in Safety-Aligned LLMs" (Ratnakar & Vats, TrustNLP 2026, co-located with ACL 2026), which introduces **Contrastive Logit Steering**, a zero-optimisation *output-distribution/logit-level* diagnostic. Different authors, different mechanism, different level of analysis. The ids differ by one digit and both are June-2026 refusal-geometry papers. Recorded in `name_collisions`.
