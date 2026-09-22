# review_hypo — create_idea

> Phase: `hypo_loop` · round 1 · `review_hypo`
> Run: `run_fcYd_7ruOwtm` — One Candidate Survives: A Pre-Registered Screen of Internal Safety Metrics for Language Model Checkpoints
>
> Full, verbatim record of every prompt the AI Inventor pipeline gave this agent — system-user, human-user and skill-input — in the order they landed. Nothing truncated.

## Task: `review_hypo` (terminal_claude_agent)

### [1] SYSTEM-USER prompt · 2026-09-20 20:28:29 UTC

```
B VRAM GPU. load the 4B models in bf16 with transformers so hidden states and weights are readable. do not switch to llama.cpp or GGUF, that hides the activations this study is about.


invariant: at least 3 of the metrics you ship must read hidden states or weights of a single model. logit-only and teacher-forced readouts are baselines, at most 2 of them.
</prompt>
```

### [2] SYSTEM-USER prompt · 2026-09-20 20:31:54 UTC

```
You are verifying citations for a peer review. Today is 2026-09-20. Use WebFetch/WebSearch (or curl to https://arxiv.org/abs/<ID>) to check each arXiv ID below RESOLVES and whether the real title matches the title the author claims. Report for each: ID | RESOLVES? | REAL TITLE (verbatim) | matches claimed title? (yes/no/partial).

IDs and claimed titles:
1. 2412.09565 = "Obfuscated Activations Bypass LLM Latent-Space Defenses"
2. 2602.04653 = "Inference-Time Backdoors via Chat Templates"
3. 2606.16349 = "From Refusal Geometry to Safety Geometry: Harmfulness-Refusal Coupling under Dynamic Adversarial Fine-Tuning"
4. 2607.00572 = "HARC"
5. 2507.11878 = harmfulness and refusal encoded separately
6. 2609.14759 = most of refusal's causal input lies outside the model's moral subspace
7. 2603.05773 = recognition versus execution
8. 2607.01854 = two-signal abliteration audit (~0.95 AUROC)
9. 2608.09624 = "Measuring the Wrong Thing: Internal Harmfulness Scores Anti-Rank Successful Jailbreaks"
10. 2406.05946 = "Safety Alignment Should Be Made More Than Just a Few Tokens Deep"
11. 2511.14195 = "N-GLARE" non-generative latent safety evaluator
12. 2606.22676 = "Skin-Deep" geometric diagnostic for alignment fragility
13. 2607.12792 = "Silent Alarm" J-space protocol
14. 2508.00161 = "Watch the Weights"
15. 2608.05086 = item-response-theory efficient safety benchmarking
16. 2606.20626 = few-item safety IRT

ALSO, for these four, extract the EXACT numbers if the abstract/paper states them (quote verbatim, give the sentence):
- 2608.09624: any AUROC numbers for internal harmfulness scores on PLAIN vs WRAPPED/jailbroken prompts (I have heard .936 plain -> .803 wrapped, and an outcome AUROC of .220 — confirm or correct).
- 2607.01854: the detection AUROC, and whether the paper states it "presumes an attested reference" / "effective triage, not tamper-proofing".
- 2606.22676 (Skin-Deep): how many models, and what it predicts.
- 2511.14195 (N-GLARE): what it reads and its cost claim.

Be strictly factual. If an ID does not resolve, say NOT FOUND — do not guess. Report as a compact table plus a short notes section. Do not write any files.
```

### [3] SYSTEM-USER prompt · 2026-09-20 20:32:00 UTC

```
You are doing a prior-art / novelty screen for a peer review of a research hypothesis. Today is 2026-09-20. Use WebSearch + WebFetch (arxiv, semantic scholar, openreview) aggressively.

THE HYPOTHESIS UNDER REVIEW claims these things are NEW:
(A) Cheap single-model "safety metrics" (read from weights/activations/logits of one HuggingFace checkpoint, no reference model) should be ranked by FORGERY COST — the cheapest edit to a checkpoint that pushes the metric into the "safe" region without improving real safety — rather than by correlation with safety benchmarks. And that these two rankings are roughly OPPOSITE.
(B) A cost-ordered "forgery ladder": F0 edit the chat template / generation config / baked-in system prompt shipped in the repo (zero FLOPs); F1 inference-time system prompt; F2a training-free CONSTANT injection of a refusal direction into the weights ("refusal injection", the claimed inverse of abliteration); F2b training-free RANK-1 edit wiring the model's harm direction into its refusal drive; F3 small keyword refusal LoRA; F4 real safety fine-tuning.
(C) An algebraic law: metrics that are LEVELS (norm/rate/mean projection at a fixed direction-layer-position) are forgeable by a constant; ACROSS-ITEM statistics (correlation/AUROC over prompts) are invariant to a constant; only "shift-robust conditionality" (correlation between internal harm estimate and refusal drive, measured on perturbed prompts) requires real training.
(D) An "honest metric manifold": honest checkpoints' metric vectors lie on a low-dim set; a forged checkpoint moves one coordinate and lands off it; the off-manifold residual detects tampering with no reference model.

FIND AND REPORT, with exact titles, venues, years, arXiv IDs and one-line what-they-did:
1. Any existing work that MEASURES THE COST OF FAKING / GAMING a safety metric, probe, monitor or evaluation of a model. Especially anything with a "cost ladder", "attack budget", or "cost to evade" framing. Check: Tamirisa et al. "Tamper-Resistant Safeguards for Open-Weight LLMs" (TAR) — what exactly does it measure the cost of? Also anything on "obfuscated activations", "probe evasion", "gaming interpretability probes".
2. Work showing automatic/cheap benchmarks can be trivially gamed. Specifically find: Zheng et al. "Cheating Automatic LLM Benchmarks: Null Models Achieve High Win Rates" (ICLR 2025) — confirm exact title/venue and what the null model was. Also "The Leaderboard Illusion" (2025). Also Ren et al. "Safetywashing" (NeurIPS 2024) — what exactly it claims.
3. Arditi et al. 2024 "Refusal in Language Models Is Mediated by a Single Direction" (arXiv 2406.11717?) — confirm ID/venue, and CRITICALLY: does it demonstrate ADDING the refusal direction (activation addition) to induce refusal on harmless prompts, and does it do a WEIGHT-space version ("weight orthogonalization")? Quote the relevant sentence. This decides whether "refusal injection" is new.
4. Anything that detects a TAMPERED / edited open-weight checkpoint WITHOUT a reference model (reference-free tamper detection, model provenance, weight forensics, "is this model abliterated").
5. Anything using a MULTI-METRIC CONSISTENCY / joint-distribution / "off-manifold" check to catch a model whose single score was manipulated (analogy: Benford's law for books, isotope ratio for doping).
6. Any paper proposing that the correlation between a model's internal harmfulness representation and its refusal behaviour be used as a per-checkpoint SAFETY SCORE.
7. Any work on making safety evaluations tamper-resistant / "evaluation gaming by the model PUBLISHER" (as opposed to by the model itself, e.g. eval-awareness / sandbagging).

For each numbered item, state clearly: SCOOPED (someone already did this), NEAR-NEIGHBOUR (close but different object), or EMPTY (found nothing). Be honest about EMPTY — do not invent papers. Every arXiv ID you report must be one you actually fetched and saw the title of. Do not write any files. Report compactly.
```
