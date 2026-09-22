# Fix citations, compare rivals, count safety scores

## Summary

LITERATURE MUST-FIXES CLOSED + DATED ECOSYSTEM CENSUS + C1/C2/C5 KILL-CHECK. Files: research_out.json (keys: positioning{grader_refusal,incumbents,ecosystem} paste-ready LaTeX; judge_refusal_prior_art; incumbent_table (9 rows); table1_rows; citation_fixes; arditi_reconciliation; ecosystem_census (102 rows, counts, provenance); kill_check; must_fix_trace; bib_diff), references.bib (93 entries = 83 + 10 via Semantic Scholar, 0 dup keys/ids), research_report.md, raw/ grep captures. (1) JUDGE REFUSAL: GuidedBench 2502.16903 (Huang2025) phrase 'do not refuse evaluation tasks involving harmful content' FOUND (Sec 5.2 p.9) but as a design motivation, with NO measured rate; headline = 76.03-88.28% variance cut. Mu2026 2609.10594: StrongReject 89.5% acc / 89.8% F1 / 8.4% FPR vs humans; JADES best; no grader-refusal discussion. JailJudge (Liu2024) GPT-4 judge F1 55%; AdvPrefix (Zhu2024) judge prefilling 'to handle sensitive content'. Frame as QUANTIFY per judge x framing; drop 'overestimated safety'. (2) INCUMBENTS all comparable=false: AMS r=-0.546 in-sample, 71% = threshold-only LOO; RAS per-family calibration; GFS needs base, no coefficient; N-GLARE never quote Table-2 taus; Hurtado2026 AUROC 0.95 + LOFO BA 0.89 is the ONLY real cross-family holdout but parent-dependent and binary; HRCI 'not a safety score'; Li2026 slope null for Qwen 3B (p=.696). (3) CITATIONS: OR-Bench (Cui2024) single-turn; Kaushik2025 is an unrelated weight-subspace paper, so REMOVE it; TAR = fine-tuning attacks only, 'adapter rank'/'chat-template' absent (0 hits), the 500-step plateau is an SFT attack; Arditi softened; the reconciliation reason is quoted from iter_3 gen_art_evaluation_1/README.md:57 (bug fix: 'first' angle was the largest principal angle). (4) CENSUS 2026-09-21, N=36: 15/36 have any safety number (6 own-developer, 6 third-party-only, 3 community self-reports); 0/36 on HELM Safety/AIR-Bench/SALAD/TrustLLM/JailbreakBench/HarmBench; over-refusal 5/36 (7 incl. WildJailbreak benign); MMLU 17, GSM8K 9, Arena-Hard 8 (developer-run), OLB v2 8; 0/15 community fine-tunes independently measured. SafeRL numbers NOT_INDEPENDENT. CAUTION: Llama-3.2-1B MMLU=68.2 (Falcon3 card) is implausible. iter-3 claims agree; the '2 sub-4B / 6.7x' figures are from a different, 81-model HELM limb. (5) KILL-CHECK closed=false: C1 ADJACENT, NARROWED by Malla2026 2609.06951 (content-free steers pull toward refusal, rank corr 0.90, strongest <10B), so C1 must subtract a norm-matched random steer; C2/C5 get a gameability caveat from Muhamed2026 DDO 2609.16204; C5 still NEW.

## Research Findings

(a) Judge refusal is known, not new. GuidedBench motivates its evaluator design partly by letting users pick less safety-restricted judges, 'thus ensuring evaluators do not refuse evaluation tasks involving harmful content' (Sec 5.2), but it prints no evaluator-refusal rate; its measured result is a 76.03-88.28% cut in inter-evaluator variance [1]. AdvPrefix adds affirmative prefilling to its judge 'to handle sensitive content' [9]. 2609.10594 compares six evaluators with human labels: StrongReject reaches 89.5% accuracy / 89.8% F1 / 8.4% FPR, JADES does best, and grader refusal is never discussed [2]. JailJudge reports GPT-4-judge F1 of 55% in complex scenarios [8]; StrongREJECT prints no grader-refusal number [10]. Our contribution is therefore a per-judge x framing quantification on a fixed 60+60 calibration set.

(b) No incumbent is comparable to a parent-free, leave-one-lineage-out, few-prompt screen. AMS's r=-0.546 (p=.043, n=14) is in-sample; its 71% (10/14) holds out only the threshold [11]. RAS needs a per-family reference model, a calibration set and measured ASR [12]. Skin-Deep needs the base model and prints no coefficient (n=7, qualitative) [13]. N-GLARE needs 7000+ trajectories and has no cross-model headline tau [14]. The only genuine cross-family holdout, Hurtado's audit (AUROC 0.95; LOFO balanced accuracy 0.89), needs a parent checkpoint and is a binary abliteration detector [19]. Leong, Li and Labunets are per-model/single-lineage [15, 16, 17]; HRCI is disclaimed as 'not a safety score' [18].

(c) OR-Bench is a single-turn benchmark (80K / 1K hard / 600 toxic prompts) [3]; cited Kaushik2025 is unrelated [4]. TAR resists gradient fine-tuning attacks and never tests training-free edits [5]. Arditi shows erasing one direction removes refusal and adding it induces refusal [6], so a SafeRL shift in a different direction inside a shared subspace is consistent with Arditi; for the multi-direction view see [7].

(d) As of 2026-09-21, 15/36 panel checkpoints have any safety number and 0 are covered by any safety leaderboard; TrustLLM covers mostly 7B+/API models [43]. Of the 15, 6 numbers come from the developer's own reports [24, 25, 33], 6 only from third-party tables [39], and 3 are community self-reports [35, 36, 38]; other abliterated cards print only capability [37]. SafeRL's numbers are not independent: Qwen3Guard was its reward [22, 23]. Capability coverage: MMLU 17, GSM8K 9, Arena-Hard 8 [20, 21, 26, 27, 28, 29, 30, 31, 32, 34]; sealed Granite/StableLM families publish no size-specific safety table [40, 41], and TrustLLM's leaderboard lists no panel model [42].

(e) Kill-check: nothing kills C1/C2/C5; Report 74's rho=-0.003 (n=16) stays the adverse prior [50] and C5's nearest miss predicts ablation effect, not benchmarks [49]. Content-free steers move refusal like real ones, most strongly below 10B, so C1 must be net of a random steer [44]. Decoy edits can fool DIM-based C2/C5 [45]. Other hits are adjacent [46, 47, 48]. Confidence: high for (a)-(c); medium for (d) (gated/JS pages).

## Sources

[1] [GuidedBench: Measuring and Mitigating the Evaluation Discrepancies of In-the-wild LLM Jailbreak Methods](https://arxiv.org/pdf/2502.16903) (Ruixuan Huang, Xun-Guang Wang, Zongjie Li, Daoyuan Wu, Shuai Wang; 2026) — Proposes GuidedEval, a guideline-based jailbreak-evaluation system, and shows it reduces inter-evaluator score variance by 76.03%-88.28% vs. keyword and prior LLM-judge baselines (StrongREJECT, PAIR, HarmBench). Judges used: GPT-4o, DeepSeek-V3, Doubao-v1.5-pro, deliberately chosen to be less safety-restricted so they do not refuse to grade harmful content; GPT-3.5 explicitly excluded for triggering refusals during grading.

> GuidedEval reduces inter-evaluator variance by at least 76.03%, ensuring reliable and reproducible evaluations

Locator: Abstract

> This indicates that GuidedEval significantly reduces its dependency on LLM evaluators, enabling users to select evaluator APIs with stronger context extraction and reasoning capabilities yet less restrictive in safety constraints, thus ensuring evaluators do not refuse evaluation tasks involving harmful content

Locator: Section 5.2, page 9

> strict safety filters (e.g., in GPT-3.5) often trigger refusals on harmful inputs during evaluation, resulting in missing data

Locator: Section 4 'Evaluator LLMs', page 5

[2] [An Empirical Measurement of Jailbreaking Evaluators](https://arxiv.org/pdf/2609.10594) (Yujie Mu; 2026) — Systematically compares six jailbreak evaluators (HarmBench, JailbreakBench, JailbreakRadar, StrongReject, JADES, JailMeter) against human labels on two human-labeled datasets. JADES performs best; StrongReject and HarmBench also perform well (~88-90% accuracy/F1). Does not discuss or quantify grader/judge-side refusal-to-evaluate.

> We systematically compare six evaluators that recur in recent jailbreak attack and defense research: HarmBench, JailbreakBench, JailbreakRadar, StrongReject, JADES, and JailMeter

Locator: Abstract

> StrongReject follows with 89.5% accuracy and 89.8% F1, while HarmBench also performs consistently well with 88.3% accuracy and 88.5% F1

Locator: Section 5 Results, page 4

[3] [OR-Bench: An Over-Refusal Benchmark for Large Language Models](https://arxiv.org/abs/2405.20947) (Justin Cui, Wei-Lin Chiang, Ion Stoica, Cho-Jui Hsieh; 2024) — Single-turn over-refusal benchmark: 80,000 seemingly-toxic prompts across 10 rejection categories, ~1,000 hard prompts, 600 toxic prompts; evaluates over-refusal on 32 LLMs across 8 model families. No multi-turn claim.

> OR-Bench comprises 80,000 over-refusal prompts across 10 common rejection categories, a subset of around 1,000 hard prompts that are challenging even for state-of-the-art LLMs, and an additional 600 toxic prompts to prevent indiscriminate responses

Locator: Abstract

[4] [The Universal Weight Subspace Hypothesis](https://arxiv.org/abs/2512.05117) (Prakhar Kaushik, Shravan Chaudhari, Ankit Vaidya, Rama Chellappa, Alan Yuille; 2025) — This is what the bib key Kaushik2025 actually points to: a weight-subspace hypothesis paper unrelated to over-refusal benchmarks or multi-turn evaluation. Confirms the draft's citation for 'multi-turn settings' is misattributed and must be dropped.

[5] [Tamper-Resistant Safeguards for Open-Weight LLMs](https://arxiv.org/pdf/2408.00761) (Rishub Tamirisa et al.; 2024) — TAR: a meta-learned safeguard resisting gradient-based fine-tuning attacks (SFT, up to 1,000 steps) that try to recover weaponization knowledge or restore refusal-bypassing behavior in open-weight LLMs. Red-teaming grid varies optimizer, steps, learning rate, LR schedule, dataset, batch size, and full vs. parameter-efficient fine-tuning -- no mention of adapter rank or chat templates, and no training-free weight-edit attacks are tested.

> We vary the optimizer, number of optimization steps, learning rate, learning rate schedule, fine-tuning dataset, batch size, and overall fine-tuning method (e.g., full fine-tuning versus parameter-efficient fine-tuning). By default, our attacks use 500 fine-tuning steps

Locator: Section 5 red-teaming setup

[6] [Refusal in Language Models Is Mediated by a Single Direction](https://arxiv.org/abs/2406.11717) (Andy Arditi, Oscar Obeso, Aaquib Syed, Daniel Paleka, Nina Panickssery, Wes Gurnee, Neel Nanda; 2024) — Finds a single direction per model such that erasing it from residual-stream activations removes refusal, while adding it induces refusal even on harmless inputs; proposes a white-box abliteration jailbreak from this.

> we find a single direction such that erasing this direction from the model's residual stream activations prevents it from refusing harmful instructions, while adding this direction elicits refusal on even harmless instructions

Locator: Abstract

[7] [There Is More to Refusal in Large Language Models than a Single Direction](https://arxiv.org/abs/2602.02132) (Faaiz Joad, Majd Hawasly, Sabri Boughorbel, Nadir Durrani, Husrev Taha Sencar; 2026) — Shows refusal categories correspond to geometrically distinct directions in activation space, yet steering along any of them produces near-identical refusal/over-refusal trade-offs, acting as a shared one-dimensional control knob -- directly analogous to our SHARED_SUBSPACE_DIFFERENT_DIRECTIONS finding.

> across diverse refusal and non-compliance categories, refusal behaviors correspond to geometrically distinct directions in activation space. Yet activation steering along any refusal-related direction produces nearly identical refusal--over-refusal trade-offs, acting as a shared one-dimensional control knob

Locator: Abstract

[8] [JAILJUDGE: A Comprehensive Jailbreak Judge Benchmark with Multi-Agent Enhanced Explanation Evaluation Framework](https://arxiv.org/pdf/2410.12855) (Fan Liu, Yue Feng, Zhao Xu, Lixin Su, Xinyu Ma, Dawei Yin, Hao Liu; 2024) — Motivates a multi-agent jailbreak-judge framework by showing a plain GPT-4 judge reaches only 55% F1 on complex/OOD scenarios.

> the F1 score of the GPT-4 judge is only 55% in complex scenarios

Locator: Abstract, page 1

[9] [AdvPrefix: An Objective for Nuanced LLM Jailbreaks](https://arxiv.org/pdf/2412.10321) (Sicheng Zhu, Brandon Amos, Yuandong Tian, Chuan Guo, Ivan Evtimov; 2024) — Introduces a prefix-forcing jailbreak objective and, along the way, refines their harmfulness judge with affirmative prefilling to handle sensitive content that the original judge otherwise failed to grade properly, improving human agreement by up to 9%.

> This judge improves human agreement rates by up to 9% on newer LLMs

Locator: Section 2, page 3

[10] [A StrongREJECT for Empty Jailbreaks](https://arxiv.org/pdf/2402.10260) (Alexandra Souly, Qingyuan Lu, Dillon Bowen, Tu Trinh, Elvis Hsieh, Sana Pandey, Pieter Abbeel, Justin Svegliato, Scott Emmons, Olivia Watkins, Sam Toyer; 2024) — Introduces the StrongREJECT rubric this project's judges use. Discusses victim-model refusal at length but never grader/judge-side refusal to evaluate.

> the most significant oversight of past automated evaluation methods is their over-emphasis

Locator: Section 2, page ~4

[11] [Detecting Safety Training Modification in Language Models via Activation Analysis](https://arxiv.org/pdf/2608.05578) (Glen Messenger et al.; 2026) — AMS: activation-based model scanner, 14 models/4 families, LOO threshold 71%, Pearson r=-0.546 (p=.043) in-sample correlation with JailbreakBench compliance.

> σ on the harmful-content concept predicts compliance with Pearson r = −0.546 (p = 0.043); the rank-order Spearman correlation is weaker (ρ = −0.423, p = 0.13)

Locator: arXiv 2608.05578v1 abstract / Section VII-E

[12] [RAS: Measuring LLM Safety Through Refusal Alignment](https://arxiv.org/pdf/2606.25750) (Chang-Chieh Huang et al.; 2026) — RAS/SafeVec: per-family reference-anchored cosine safety score, needs calibration set with measured ASR, 216.88x faster than judge scoring on average.

> On average, RAS is 216.88× faster in our setting

Locator: arXiv 2606.25750, Section 4.2 RQ4, Table 2

[13] [Skin-Deep: A Geometric Diagnostic for Alignment Fragility in Large Language Model Representations](https://arxiv.org/pdf/2606.22676) (Dongyub Jude Lee et al.; 2026) — GFS: cPCA fragility score needing aligned+base model pair; n=7 qualitative LoRA-fragility ranking, no printed correlation coefficient.

> Input. Aligned model M, base model M0, and matched prompt sets Dsafe, Dgen

Locator: arXiv 2606.22676, Appendix Algorithm 1

[14] [N-GLARE: A Non-Generative Latent Representation-Efficient LLM Safety Evaluator](https://arxiv.org/html/2511.14195) (Zheyu Lin et al.; 2026) — ACL 2026; needs internal hidden reps, 7000+ offline trajectories; Table 2 rank-correlation is a robustness check by n/dataset/model, never a headline.

> N-GLARE requires access to internal hidden representations, which limits its direct applicability to fully black-box models that expose only text outputs

Locator: arXiv 2511.14195, Limitations

[15] [Template-Anchored Safety Alignment (TASA)](https://arxiv.org/html/2502.13946v2) (Leong et al.; 2025) — Head-level activation patching of the template region; uses normalized indirect effect (NIE) for fair cross-model comparison across 6 models/4 families; prior art for C9's normalization.

> For a fair cross-model comparison, we use the normalized indirect effect (NIE) by dividing the IE of each pair by

Locator: Sec 3 (activation patching setup)

[16] [Steering vector alignment predicts attack-success-rate slope](https://arxiv.org/pdf/2603.24543) (Li et al.; 2026) — Per-model OLS regression of ASR slope on cosine-to-refusal-direction across 6 models; significant for models >3B (p<.001, R2>=.85), null for Qwen 3B (p=.696); slope scales with model size.

> For every model larger than 3B, the relationship is statistically significant (p < 0.001) and exceptionally strong

Locator: Sec 6

[17] [Refusal geometry reflects refusal training](https://arxiv.org/pdf/2608.25390) (Andrey Labunets; 2026) — Stable rank of gradients/activations vs ablation robustness, validated as a single OLMo-2-0425-1B lineage case study (base/SFT/DPO/RLVR1/Instruct).

[18] [From Refusal Geometry to Safety Geometry: Harmfulness-Refusal Coupling under Dynamic Adversarial Fine-Tuning](https://arxiv.org/pdf/2606.16349) (Wenhao Lan et al.; 2026) — HRCI_repr per-checkpoint coupling discriminator; authors' own verdict: 'low coupling is not a safety score' (SFT trajectory stays high-ASR despite low coupling).

> By step 500, HRCIrepr has fallen to 0.0205, a 73.9% drop from step 50

Locator: arXiv 2606.16349v3, Section 4.4 RQ4

[19] [Has This Checkpoint Been Abliterated? A Two-Signal Audit and Its Failure Map](https://arxiv.org/pdf/2607.01854) (Gabriel Hurtado et al.; 2026) — Combined activation-gap + WeightWatch z-sum audit: AUROC 0.95 in-sample, leave-one-family-out balanced accuracy 0.89; needs a reference (parent) checkpoint per family; spoofable by a fake reference.

> a Youden-calibrated threshold transfers to held-out families at balanced accuracy 0.89 (FPR 0.11), missing only 4 of 57

Locator: Abstract

[20] [Qwen3 Technical Report](https://arxiv.org/abs/2505.09388) — Tables 17-20 give MMLU-Redux/Arena-Hard/IFEval for Qwen3-0.6B/1.7B/4B and Qwen2.5/Phi-4-mini/Gemma-3 baselines; no dedicated safety section.

[21] [Qwen2.5 Technical Report](https://arxiv.org/pdf/2412.15115) — Tables 9-10 give MMLU-Redux/MMLU-Pro/GSM8K/IFEval for Qwen2.5-0.5B/1.5B/3B-Instruct plus Gemma2-2B and Phi3.5-mini baselines.

> Table 10: Performance comparison of 0.5B-1.5B instruction-tuned models

Locator: Table 10

[22] [Qwen3Guard Technical Report](https://arxiv.org/pdf/2510.14276) — Section 3.5/Table 10 reports the exact Safety-RL experiment that produced Qwen3-4B-SafeRL, with Non-Think/Think x Guard-only/Hybrid safety-rate, refusal, ArenaHard-v2 and reasoning numbers for base Qwen3-4B and both SafeRL variants.

> Mode Model Safety Rate Refusal ArenaHard-v2

Locator: Table 10, Sec 3.5

[23] [Qwen3-4B-SafeRL model card](https://huggingface.co/Qwen/Qwen3-4B-SafeRL) — Confirms the released checkpoint is the Hybrid-reward variant and reprints the Non-Think/Think performance table.

[24] [Phi-4-Mini Technical Report](https://arxiv.org/abs/2503.01743) — Tables 10-12 give RAI Defect Rate and XSTest IPRR/VPRR for Phi-4-Mini, Phi-4-Multimodal, Phi-3.5-mini, Llama-3.2-3B and Qwen-2.5-3B; the Model Quality table gives Arena-Hard/MMLU/GSM8K for the same set plus Llama-3.2-3B/Qwen2.5-3B.

[25] [Gemma 2 Technical Report](https://arxiv.org/abs/2408.00118) — Table 15 (human-preference safety win-rate vs GPT-4o), Table 17 (PT vs IT MMLU) and Table 18 (RealToxicity/CrowS-Pairs/BBQ) for Gemma-2 IT 2B.

[26] [Falcon3 launch blog (HF)](https://huggingface.co/blog/falcon3) — Prose benchmark summary; actual numeric tables are images, not machine-extractable text. No safety section.

> Falcon3-1B attains competitive results in IFEval (54.4), MUSR (40.7), and SciQ (86.8)

Locator: Instruct models section

[27] [Falcon3-1B-Instruct model card](https://huggingface.co/tiiuae/Falcon3-1B-Instruct) — Benchmarks table with MMLU/MMLU-Pro/IFEval/GSM8K for Falcon3-1B-Instruct plus Llama-3.2-1B/Qwen2.5-1.5B/SmolLM2-1.7B comparison columns.

[28] [H2O-Danube3 Technical Report](https://arxiv.org/abs/2407.09276) — MMLU/GSM8K table for H2O-Danube3-500M-Chat vs Qwen2-0.5B-Instruct; separate MT-Bench/WildBench chat table, no named safety benchmark.

[29] [SmolLM2: When Smol Goes Big](https://arxiv.org/abs/2502.02737) — Table 5 compares SmolLM2-1.7B-Instruct, Llama3.2-1B and Qwen2.5-1.5B on IFEval/MT-Bench/MMLU-Pro/GSM8K/MATH; no safety section.

[30] [SmolLM2-360M-Instruct model card](https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct) — Own IFEval/MMLU/GSM8K numbers plus a Qwen2.5-0.5B-Instruct comparison row.

> GSM8K (5-shot) | 7.43 | **26.8** | 1.36

Locator: Instruction Model table

[31] [SmolLM2-1.7B-Instruct model card](https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B-Instruct) — Own IFEval/MMLU-Pro/GSM8K numbers plus Llama-1B-Instruct/Qwen2.5-1.5B-Instruct comparison rows.

> GSM8K (5-shot) | **48.2** | 26.8 | 42.8 | 4.62

Locator: Instruction Model table

[32] [SmolLM3-3B model card](https://huggingface.co/HuggingFaceTB/SmolLM3-3B) — No-Extended-Thinking table gives IFEval for SmolLM3-3B, Qwen2.5-3B, Llama3.1-3B, Qwen3-1.7B, Qwen3-4B; base table gives GSM8K(5-shot) for Qwen3-4B-Base.

[33] [OLMo-2-0425-1B-Instruct model card](https://huggingface.co/allenai/OLMo-2-0425-1B-Instruct) — Performance table with an explicit 'Safety' column (Tulu-3 eval suite) for OLMo 2 1B (final), Qwen 2.5 1.5B and SmolLM2 1.7B baselines.

[34] [EuroLLM-1.7B-Instruct model card](https://huggingface.co/utter-project/EuroLLM-1.7B-Instruct) — Only ArcChallenge/HellaSwag multilingual tables; no MMLU/GSM8K/Arena-Hard/safety number.

[35] [Qwen2.5-0.5B-Instruct-CensorTune model card](https://huggingface.co/huihui-ai/Qwen2.5-0.5B-Instruct-CensorTune) — Self-reported harmbench_behaviors pass-rate table (own fine-tune vs original vs abliterated variants) plus an IF_Eval/BBH/GPQA/MMLU-Pro/TruthfulQA re-eval table.

[36] [Qwen2.5-1.5B-Instruct-CensorTune model card](https://huggingface.co/huihui-ai/Qwen2.5-1.5B-Instruct-CensorTune) — Same harmbench_behaviors pass-rate pattern as the 0.5B CensorTune card.

[37] [Llama-3.2-3B-Instruct-abliterated model card](https://huggingface.co/huihui-ai/Llama-3.2-3B-Instruct-abliterated) — Self-reported IF_Eval/MMLU-Pro/TruthfulQA/BBH/GPQA re-eval vs the original checkpoint; no safety number.

[38] [qwen3-4b-heretic model card](https://huggingface.co/DreamFast/qwen3-4b-heretic) — Self-reported Heretic-tool refusal count (3/100 vs 100/100 original); no named benchmark.

[39] [aiXamine: Simplified LLM Safety and Security](https://arxiv.org/abs/2504.14985) — Table 6 leaderboard gives an Over-Refusal composite (OK-Test/OR-Bench/WildGuard/XSTest) and a Safety&Alignment composite for Llama3.2-1B and Llama3.2-3B, among other models.

[40] [Granite 3.0 Language Models (IBM technical report)](https://www.rivista.ai/wp-content/uploads/2024/10/paper-1.pdf) — Figure 7(b)/Table 17 establish IBM's family-level AttaQ/SocialStigmaQA/SALAD-safety-rate practice for 2B-3B Granite Instruct models vs Llama-3.2/Gemma-2; 2B-3B numbers are figure-only.

[41] [Stable LM 2 1.6B Technical Report](https://arxiv.org/abs/2402.17834) — Full-text grep for safety|toxicity|RealToxicity|refusal returns only one incidental citation match; no safety/toxicity evaluation section exists in this report.

[42] [TrustLLM leaderboard](https://trustllmbenchmark.github.io/TrustLLM-Website/leaderboard.html) — JS-rendered page; static fetch returned no model names. TrustLLM's own paper (2401.05561) roster is 16 models, all 7B+ / proprietary API (Llama2, Vicuna, Mistral-7B, ChatGLM2, GPT-4, PaLM 2, ERNIE, etc.) -- none overlap this sub-4B panel.

[43] [TrustLLM: Trustworthiness in Large Language Models](https://arxiv.org/abs/2401.05561) — Confirms the 16-model roster is 7B+/proprietary-API only.

[44] [Steering Interference Reflects the Model's Defaults, Not the Behavior Directions](https://arxiv.org/pdf/2609.06951) (Srikanth Malla, Chiho Choi, Joon Choi; 2026) — Kill-check hit (NARROWS C1): a norm-matched, content-free steer moves the same behaviours in the same order as real steers (rank corr 0.90); the pull toward refusal is strongest below 10B.

> moves the same behaviors in the same order as real steers do (rank correlation 0.90)

Locator: Contributions, p.2

> the pull toward defaults strongest below 10B parameters and weakening in each family

Locator: Abstract

[45] [Decoy Direction Optimization: A Post-Hoc Defense Against LLM Abliteration](https://arxiv.org/abs/2609.16204) (Aashiq Muhamed, Mona T. Diab, Virginia Smith; 2026) — Kill-check hit (NARROWS C2/C5): a post-hoc weight edit corrupts difference-in-means refusal-direction estimators across six families, so DIM-based self-ablation or weight-path scores can be gamed.

> ablation attacks rely on contrastive estimators to find the refusal direction

Locator: Abstract

[46] [Refusal Reads Only a Slice of What the Model Knows: Harm-Keyed Routing and Its Exceptions Across Model Families](https://arxiv.org/abs/2609.14759) (Orion Reblitz-Richardson; 2026) — Kill-check hit (ADJACENT C1): harm-to-refusal routing on 4 models / 3 families; the causal result is single-model (OLMo-3); no benchmark correlation.

> The central result is causal and comes from one model, OLMo-3

Locator: Abstract

[47] [The Role of Fine-grained Harm Signals in LLM Safety](https://arxiv.org/abs/2609.19366) (Soyeon Park, Seogyeong Jeong, Sunwoo Kim, Alice Oh; 2026) — Kill-check hit (ADJACENT C1): steering category residuals induces refusal with model-dependent strength on 3 models; no benchmark correlation.

> Whether category residuals induce refusal also varies across categories, but this category-wise pattern is more model-dependent

Locator: Abstract

[48] [HARC: Coupling Harmfulness and Refusal Directions for Robust Safety Alignment](https://arxiv.org/abs/2607.00572) (Shei Pern Chua, Hao Wu, Qianli Ma, Fang-Zhao Wu; 2026) — Kill-check hit (ADJACENT C1): harmfulness-refusal geometry across five architectures, used for a defense; no per-model benchmark correlation found.

[49] [Perturbation Probing: A Two-Pass-per-Prompt Diagnostic for FFN Behavioral Circuits in Aligned LLMs](https://arxiv.org/abs/2604.27401) (2026) — C5 nearest miss (unchanged): the FFN/Skip ratio predicts ablation effectiveness across 13 models / 4 families, not a safety benchmark.

[50] [Report 74: Abliteration Resistance and Jailbreak Resistance Are Orthogonal Defense Dimensions](https://failurefirst.org/research/reports/74-abliteration-jailbreak-orthogonality/) (2026) — Adverse prior for C1/C2 (grey literature, carried from iter-3): abliteration resistance vs jailbreak refusal, Spearman rho=-0.003, n=16.

## Verification

Numbered citations resolve to unique listed sources. Passage checks test text occurrence, not claim truth or entailment. Author/year metadata and locators are not independently verified. Details: `research_verification.json`.

- Source [1]: text found — GuidedEval reduces inter-evaluator variance by at least 76.03%, ensuring reliable and reproducible e
- Source [1]: text found — This indicates that GuidedEval significantly reduces its dependency on LLM evaluators, enabling user
- Source [1]: text found — strict safety filters (e.g., in GPT-3.5) often trigger refusals on harmful inputs during evaluation,
- Source [2]: text found — We systematically compare six evaluators that recur in recent jailbreak attack and defense research:
- Source [2]: text found — StrongReject follows with 89.5% accuracy and 89.8% F1, while HarmBench also performs consistently we
- Source [3]: text found — OR-Bench comprises 80,000 over-refusal prompts across 10 common rejection categories, a subset of ar
- Source [5]: text found — We vary the optimizer, number of optimization steps, learning rate, learning rate schedule, fine-tun
- Source [6]: text found — we find a single direction such that erasing this direction from the model's residual stream activat
- Source [7]: text found — across diverse refusal and non-compliance categories, refusal behaviors correspond to geometrically 
- Source [8]: text found — the F1 score of the GPT-4 judge is only 55% in complex scenarios
- Source [9]: text found — This judge improves human agreement rates by up to 9% on newer LLMs
- Source [10]: text found — the most significant oversight of past automated evaluation methods is their over-emphasis
- Source [11]: text found — σ on the harmful-content concept predicts compliance with Pearson r = −0.546 (p = 0.043); the rank-o
- Source [12]: text found — On average, RAS is 216.88× faster in our setting
- Source [13]: text found — Input. Aligned model M, base model M0, and matched prompt sets Dsafe, Dgen
- Source [14]: text found — N-GLARE requires access to internal hidden representations, which limits its direct applicability to
- Source [15]: text found — For a fair cross-model comparison, we use the normalized indirect effect (NIE) by dividing the IE of
- Source [16]: text found — For every model larger than 3B, the relationship is statistically significant (p < 0.001) and except
- Source [18]: text found — By step 500, HRCIrepr has fallen to 0.0205, a 73.9% drop from step 50
- Source [19]: text found — a Youden-calibrated threshold transfers to held-out families at balanced accuracy 0.89 (FPR 0.11), m
- Source [21]: text found — Table 10: Performance comparison of 0.5B-1.5B instruction-tuned models
- Source [22]: text found — Mode Model Safety Rate Refusal ArenaHard-v2
- Source [26]: text found — Falcon3-1B attains competitive results in IFEval (54.4), MUSR (40.7), and SciQ (86.8)
- Source [30]: text found — GSM8K (5-shot) | 7.43 | **26.8** | 1.36
- Source [31]: text found — GSM8K (5-shot) | **48.2** | 26.8 | 42.8 | 4.62
- Source [44]: text found — moves the same behaviors in the same order as real steers do (rank correlation 0.90)
- Source [44]: text found — the pull toward defaults strongest below 10B parameters and weakening in each family
- Source [45]: text found — ablation attacks rely on contrastive estimators to find the refusal direction
- Source [46]: text found — The central result is causal and comes from one model, OLMo-3
- Source [47]: text found — Whether category residuals induce refusal also varies across categories, but this category-wise patt

## Follow-up Questions

- Does C1 (harm-to-refusal gain) keep any cross-family signal once a norm-matched random-direction steer is subtracted, given 2609.06951 finds the generic pull toward refusal strongest below 10B?
- Per judge x framing, how much of the 1,1,1 mass on the 60 known-compliant items is grader refusal versus rubric misreading, and does affirmative prefilling (AdvPrefix-style) remove it?
- Can the 6 developer-own safety numbers and the 5-7 over-refusal numbers serve as an external anchor (n<=7) for even a sign test of the top metrics, or is the in-house two-refusal-rate fallback the only viable ground truth?

---
*Generated by AI Inventor Pipeline*
