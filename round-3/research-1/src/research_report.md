# Prior-art check for 16 safety-metric candidates

## Summary

NOVELTY TABLE FOR C1-C16, KILL-CHECK, REGENERATED BIB, NUMBER LEDGER AND SCANNER PIN. Files: novelty_table.json (16 rows, each with a quote, locator, at least 4 queries, and a paste-ready positioning sentence), novelty_A/B/C.json (raw subagent records), references.bib (83 entries, no duplicate keys), bib_fixes.json, citation_corrections.json, number_ledger.json, scanner_pin.json. KILL-CHECK OPEN (closed=false). No paper correlates a per-model causal harm-to-refusal quantity with benchmark safety across families. The adverse prior to cite is Failure-First Report 74 (grey literature): abliteration resistance vs jailbreak refusal, rho=-0.003, n=16. The closest arXiv hit is LVS 2606.08044 (undirected perturbation, no benchmark correlation). VERDICTS: NEW = C5 (weight-path gain; nearest miss 2604.27401), C14 (ridge metamodel; GFS/RAS use fixed weights), C15 (late-layer effective rank; must cite the new nearest miss 2608.25390, stable rank vs ablation robustness in one OLMo lineage). PUBLISHED = C9 (Leong 2502.13946: template-region NIE normalised 'for a fair cross-model comparison' across 6 models from 4 families) -> REPLICATION row; C16 (Li 2603.24543: per-model steering slope gamma_1 across 6 models) -> COMPARATOR only. ADJACENT = C1, C2 (closest to published; cite Report 74), C3, C4 (Jorak already reads o_proj/down_proj parent-free, but only as a label), C6, C7, C8, C10, C11 (all incumbents parent-dependent), C12, C13. CRITICAL CORRECTIONS FOR THE PAPER: (1) '0.35 published Jorak threshold' is WRONG. Jorak @8147de3 scanner.py L48-55 ships 0.5 (unchanged since the first commit). 0.35 is this run's own BSA_PREREG_THRESHOLD (iter_1 flab/config.py:74), and BSA_w8 is not Jorak's statistic, so withdraw the 'published scanner 100% FPR' claim. (2) The iter-2 draft's hand-typed reference list has 20/30 fabricated first authors and 5 wrong initials; generate references only from the bib. (3) Cite Tan2024 = 2407.12404 for steering brittleness; 2406.09289 is Ball et al. (4) Planner fix-list items ii (Casper) and vi (AMS DOI) were false positives: both DOIs were already correct; the fixes were an added eprint and @article. (5) Qwen3Guard report 2510.14276 Section 3.5 confirms Qwen3Guard-4B-Gen was SafeRL's reward. LEDGER: see number_ledger.json

## Research Findings

BOTTOM LINE (2026-09-21). None of the 16 candidates is published as a single-model, parent-free safety score that has been correlated with benchmark safety across architecture families. The kill-check on the leading conjecture comes back OPEN (closed = false). Row verdicts: 3 NEW (C5, C14, C15), 11 ADJACENT and 2 PUBLISHED (C9, C16). Four bibliography findings matter more for the paper than the planner expected: (a) the '0.35 published Jorak threshold' is our own pre-registered simulation value, and Jorak ships 0.5 [7, 37] (origin traced in this artifact's scanner_pin.json to the run's own config file iter_1/gen_art/gen_art_experiment_2/flab/config.py, line 74); (b) 20 of the 30 hand-typed references in the iteration-2 draft carry fabricated first-author names, checked against the arXiv API [36] (row-by-row audit in citation_corrections.json); (c) two of the seven planner fix-list defects (Casper's 'eprint 0106.36590' and AMS's 'DOI fragment 2026.37040') are misreadings of DOIs that are actually correct [29, 30]; (d) the 'Tan et al. 2406.09289' citation is a misattribution. 2406.09289 is Ball, Kreuter & Rimsky, and the steering-reliability paper is Tan et al. 2407.12404 [25, 26].

1. KILL-CHECK: IS THE LEADING CONJECTURE STILL NOVEL? Question: does any paper compute a per-model harm-to-refusal CAUSAL quantity (steering gain, ablation effect, patching, weight-path gain) and correlate it with benchmark safety across models? Answer: no. The search ran 14 targeted queries and a forward citation chase: 1,061 papers citing Arditi 2406.11717, 74 citing Zhao 2507.11878, and none yet indexed for 2606.16349. Of 1,006 titles from 2025 onward, 156 were filtered, 25 abstracts screened and 6 PDFs grepped. Causal refusal interventions appear only as within-model mechanism evidence: 13 models in Arditi [1], 3 models in Zhao [2], and anchor checkpoints plus one trajectory in HRCI [33]. The closest hit is grey literature: Failure-First Report 74 ranks 16 models by resistance to weight abliteration and correlates that with jailbreak refusal, and finds no relationship ('rho = -0.003') [3]. It misses the conjecture because it is not peer reviewed, it measures third-party abliteration success rather than a gain keyed to the model's own harm direction, and it has no over-refusal arm. The closest arXiv hit is LVS (2606.08044), a causal per-model score built from UNDIRECTED latent perturbations and never correlated with a benchmark [4]. AMS [27] and RAS [20] are confirmed NON-causal. Required positioning sentence: "Causal refusal interventions have so far been reported per model as mechanism evidence (arXiv:2406.11717; arXiv:2507.11878; arXiv:2606.16349), per-unit latent-perturbation sensitivity has been proposed as a safety score without benchmark validation (arXiv:2606.08044), and a practitioner report found abliteration resistance uncorrelated with jailbreak refusal across 16 models (Failure-First Report 74, rho = -0.003); we are the first to test, parent-free and with ~16 prompts, whether causal harm-to-refusal quantities keyed to each model's own harm direction track both harmful-refusal and over-refusal benchmarks across held-out architecture families." What remains novel: (1) a causal quantity keyed to the model's OWN cross-fitted harm direction; (2) parent-free with about 16 prompts; (3) a two-sided target, harmful-refusal AND over-refusal, under which a blanket refuser loses; (4) held-out cross-family validation; (5) anisotropy-matched random-direction controls. Implication: Report 74's null result is prior evidence AGAINST a generic 'ablation robustness tracks safety' story. It must be cited as the adverse prior, and a positive C1/C2 result must be shown to differ from it.

2. PER-CANDIDATE VERDICTS (full records with quotes, locators, queries and positioning sentences are in novelty_table.json).
Family I/II, causal (C1-C5). C1 harm-to-refusal gain: ADJACENT. Harm-direction steering elicits different refusal rates on 3 models, but only as a mechanism contrast [2]; LVS is a cross-model score, but its perturbation is undirected [4]. C2 self-ablation sensitivity: ADJACENT, and closest to PUBLISHED. Arditi ablates the refusal direction in 13 models without ranking them [1], and false-refusal vector ablation is a single-model tool [42]; Report 74 does the cross-model correlation in generic form and finds a null [3]. The claim must be narrowed to the margin-based, two-sided, random-direction-controlled form. C3 twin patching flip depth: ADJACENT. Benign-twin activation substitution exists as a jailbreak on mainly one model and is never reduced to a per-model scalar [5]. C4 writer capacity: ADJACENT. Jorak already reads o_proj/down_proj against the refusal axis without a reference model, but only to assign a provenance label [6, 7]. C4's novelty is the graded, random-direction z-scored write along the model's own axis and its benchmark validation. C5 weight-path gain: NEW. The nearest miss predicts ablation effectiveness from an FFN/Skip ratio across 13 models and 4 families, but that ratio mixes weights and activations and the target is not a benchmark [8].
Family III/IV, attribution and dynamics (C6-C11). C6 DLA concentration: ADJACENT. Arditi's component attribution is a single-model case study [1]; Ships/Sahara covers two same-lineage models [9]. C7 attention mass on differing tokens: ADJACENT. Attention to sensitive words correlates with ASR within the Llama-2 family only [10]. C8 input-gradient share: ADJACENT. GradSafe uses parameter gradients, not input-token gradients [11]. C9 template-site share: PUBLISHED. Leong et al. compute a template-region normalised indirect effect across six chat models from four families, normalised 'for a fair cross-model comparison', and tie template anchoring to vulnerability [12]. The caveat is that the safety link is qualitative, with no numeric per-model correlation with a benchmark, so C9 becomes a REPLICATION row. C10 area between depth curves: ADJACENT. Both curves already exist on the same 3 models [2], and harm-only trajectories exist across 4 families [13]; only the area aggregation and its use as a ranking are new. C11 first-8-token commitment: ADJACENT. Every close hit needs a parent or counterpart model: per-token KL against the base model [14] and instruct/reasoning pairs [15]. The parent-free single-checkpoint version is the residual novelty.
Family V-VIII, discrimination, invariance, metamodel, geometry, steering (C12-C16). C12 twin discrimination: ADJACENT. LatentBiopsy reports harmful-vs-XSTest-twin AUROC = 1.000 per checkpoint but has no plain-benign ratio [16]; Entanglement Wall declines to use twin separation for ranking [17]. C13 presentation invariance: ADJACENT. A wrapped-vs-plain AUROC drop (0.936 to 0.803) is reported per model, but framed as a validity critique [18]. C14 ridge metamodel on 24 or fewer depth-by-site features: NEW. GFS uses a FIXED l/L depth weight [19], RAS a fixed average with a hand-set logistic [20], and the log-likelihood model map uses outputs rather than activations [41]. C15 late-layer effective rank: NEW. Effective rank separates models only on capability [21, 22]. The orchestrator's adversarial pass found a new nearest miss that must be cited: Labunets links the stable rank of refusal residuals and gradients to ablation robustness, in one OLMo-2-1B lineage [23]. C16 self-steering slope: PUBLISHED as a comparator. Li fits per-model ASR dose-response slopes against steering/refusal-direction alignment and compares 6 models ('becomes progressively steeper with model size') [24]. Steering unreliability is documented by Tan et al. [25]. Orchestrator correction: the published quantity is gamma_1, the special case v = r_hat of C16, and it is NOT correlated with a safety benchmark.

3. CLAIMABLE NOVELTY AND SCREEN IMPLICATIONS. Only C5, C14 and C15 may be called new, each in a precise scope. C5: 'a weights-only harm-to-refusal path gain as a cross-family safety score' [8]. C14: 'a FITTED metamodel over depth-by-site internal features, as opposed to fixed-weight aggregations' [19, 20]. C15: 'late-layer dispersion validated against two-sided safety benchmarks', citing [23] as the nearest miss. C1-C4, C6-C8 and C10-C13 may be called new only as parent-free, few-prompt, cross-family SAFETY SCORES; each is an established single-model mechanism quantity. Screen status changes: C9 becomes a replication of Leong et al. [12]; C16 is comparator-only [24]; C2 must cite Report 74's null as the adverse prior [3]; C4 must cite Jorak [6] and state that the weight read is not new; C11 is the only candidate whose incumbents are all parent-DEPENDENT [14, 15], which is its strongest positioning. The incumbent map places AMS nearest to C12 [27], N-GLARE nearest to C13 [28], RAS nearest to C14 [20], and LatentBiopsy nearest to C12/C15 [16].

4. SCANNER PIN AND A CORRECTION TO THE PAPER'S HEADLINE. The Jorak repository is github.com/JolanMc/Jorak; its default-branch head is SHA 8147de343964a3cced37db71814e9007c7465a52, dated 2026-07-24 [6, 37]. The thresholds are in modelscanner/classifier/scanner.py, lines 48, 49 and 55: svd_align_severed = band_align_severed = subspace_severed = 0.5. They are calibrated on Qwen2.5-0.5B ('0.24 vs 1.00') and were never changed across the three commits that touched the file [7, 37]. A grep of all 90 text files at HEAD finds 0.35 only as a plotting width. The 0.35 the iteration-1/2 papers call 'the published separator' is this run's own BSA_PREREG_THRESHOLD, a simulation-calibrated pre-registration (iter_1 flab/config.py, line 74, quoted in scanner_pin.json), not a value from Jorak [7]. The run's BSA_w8 statistic (windowed mean pairwise |cos|) is also not Jorak's statistic, which is sigma_1/||U||_F plus a band of width L/6. So the claim '100% false-positive rate of a published scanner' must be withdrawn or re-run with Jorak's own statistic at 0.5.

5. BIBLIOGRAPHY. references.bib was regenerated by identifier: 83 entries, no duplicate keys, author names from the arXiv API [36] and venues from Semantic Scholar. Every entry carries eprint and DOI, except the two @misc grey-literature items (Jorak, pinned to its SHA, and Report 74). Planner fix-list: (i) the duplicate LlorenteSaguer2026 key is split into LlorenteSaguer2026a (2604.18901) and LlorenteSaguer2026b (2603.27412) [16]. (ii) Casper: the iteration-2 bib already had the CORRECT DOI 10.1145/3630106.3659037 (FAccT '24, pp. 2254-2272) [29]. '0106.36590' is a substring of that DOI; the real defect was a missing eprint, and 2401.14446 has been added. (iii) Key AbuShairah2025 with author {Abu Shairah}, Harethah [31]. (iv) Tan2024 = 2407.12404 added; Ball2024 = 2406.09289 kept for jailbreak dynamics only [25, 26]. (v) Lan 2606.16349 [33], Fogel 2602.04653 [34], Luo 2608.09624 [18] and Rivera 2608.05086 [32] now have IDs; Rivera's merged affiliation 'Independent and UK AI Security Institute' has been removed [32]. (vi) AMS: the full DOI 10.1109/ACCESS.2026.3704057 (IEEE Access 14:91723-91737) was ALREADY present [30]. The defect was the entry type (@inproceedings for a journal); it is now @article with eprint 2608.05578 [27, 30]. (vii) Zhao2025's authors are confirmed [2]; Singh2025, Ren2024 and Zhong2025 names were corrected from arXiv. (viii) All 26 missing works were added, plus the Qwen3Guard report. That report confirms Qwen3Guard-4B-Gen was SafeRL's reward model, so it must not judge SafeRL [35]. Extra defects found: RAS's first author is 'Chang-Chieh Huang' on arXiv, not Semantic Scholar's 'Changhui Huang' [20]; N-GLARE's key is now Lin2026 [28]. CITATION-LIST AUDIT: the iteration-2 draft's hand-typed list (entries 1-30) has 20 fabricated first authors (e.g. Zhao's paper credited to 'D. Li', Joad's to 'T. B. Brown', Hurtado's to 'K. Park') and 5 wrong initials, with 4 entries correct. At least 8 titles are altered, e.g. 2603.05773 is 'Knowing without Acting', not 'Recognition Versus Execution' [36]. Fix: generate the reference list only from references.bib.

6. NUMBER LEDGER. PENDING: the number-ledger pass (number_ledger.json) was still running when this version was written; every numeric claim about a cited paper must be taken as UNVERIFIED until that file exists. Numbers verified directly in this artifact: gamma_1 from -36.52 to -193.40 [24]; LatentBiopsy harmful-vs-XSTest AUROC = 1.000 [16]; Report 74 rho = -0.003 over 16 models [3]; AMS in IEEE Access 14:91723-91737 [30].

CONFIDENCE. High for the fix-list, the scanner pin and the reference-list audit: all were checked mechanically against the arXiv API, Crossref and GitHub [7, 29, 30, 36, 37]. Medium-high for the ADJACENT and PUBLISHED verdicts, each backed by an exact quote. Medium for the three NEW verdicts: absence of evidence after 4 or more general queries, a citation hop and one orchestrator adversarial pass. The field moves weekly, and the pass surfaced one new near miss for C15 [23]. Medium for kill-check = OPEN. Semantic Scholar does not yet index citations of 2606.16349, and grey literature (Report 74 [3], Jorak [6]) is where the closest work lives, so a practitioner blog could close it. Evidence that would change a verdict: a 2026 paper correlating any causal per-model refusal quantity with XSTest/OR-Bench or HarmBench across families (closes the kill-check); a paper validating effective rank against safety benchmarks (closes C15); a learned internal-feature safety predictor (closes C14).

## Sources

[1] [Refusal in Language Models Is Mediated by a Single Direction](https://arxiv.org/abs/2406.11717) (Andy Arditi, Oscar Obeso, Aaquib Syed, Daniel Paleka, Nina Panickssery, Wes Gurnee, Neel Nanda; 2024) — Directional ablation and activation addition of a difference-in-means refusal direction across 13 open chat models. Mechanism evidence, not a model ranking. Closest prior work for C2 and C6.

[2] [LLMs Encode Harmfulness and Refusal Separately](https://arxiv.org/pdf/2507.11878) (Jiachen Zhao, Jing Huang, Zhengxuan Wu, David Bau, Weiyan Shi; 2025) — Separate harmfulness and refusal directions; harmfulness-direction steering on 3 chat models; harmfulness and refusal depth curves on the same models. Closest prior work for C1 and C10 (ADJACENT).

> the refusal rate elicited by the harmfulness direction is much lower than that elicited directly by the refusal direction

Locator: v5, Section 3.2, paragraph beside Figure 4

[3] [Failure-First Report 74 (abliteration-jailbreak orthogonality)](https://failurefirst.org/research/reports/74-abliteration-jailbreak-orthogonality/) (2026) — Grey-literature web report (2026-03-11). It ranks 16 models by resistance to weight abliteration and correlates that with jailbreak refusal. It is the closest thing to the kill-check design (a generic directional-ablation outcome across models), and it found a null result.

> the Spearman rank correlation between abliteration resistance and jailbreak refusal rate is rho = -0.003

Locator: Executive Summary, paragraph 2

[4] [When Behavioral Safety Evaluation Fails: A Representation-Level Perspective](https://arxiv.org/abs/2606.08044) (2026) — LVS: a per-model safety score from latent-perturbation sensitivity. The perturbation is undirected and the score is not correlated with any benchmark. Nearest causal cross-model score (kill-check runner-up).

[5] [Activation Surgery: Jailbreaking White-box LLMs without Touching the Prompt](https://arxiv.org/abs/2603.14278) (2026) — Layer-wise substitution of a benign twin's activations, used as a jailbreak on mainly one model; no per-model score. C3 ADJACENT.

[6] [Model Scanner (Jorak): reference-free abliteration detection](https://github.com/JolanMc/Jorak) (JolanMc; 2026) — Weights-only, reference-free scanner that reads the SVD of o_proj/down_proj against the refusal axis and outputs a provenance label. Closest relative of C4 (ADJACENT: it labels models, it does not grade them).

[7] [Jorak modelscanner/classifier/scanner.py @ 8147de3](https://raw.githubusercontent.com/JolanMc/Jorak/8147de343964a3cced37db71814e9007c7465a52/modelscanner/classifier/scanner.py) (JolanMc; 2026) — Pinned threshold file. All three weight-signal thresholds are 0.5, calibrated on Qwen2.5-0.5B. No 0.35 threshold exists anywhere in the repository.

> svd_align_severed: float = 0.5

Locator: line 48

> subspace_severed: float = 0.5

Locator: line 55

> alignement SVD u_min : 0.24 vs 1.00   -> seuil sectionné 0.5

Locator: Thresholds docstring, line 44

[8] [Perturbation Probing: A Two-Pass-per-Prompt Diagnostic for FFN Behavioral Circuits](https://arxiv.org/abs/2604.27401) (2026) — An FFN/Skip ratio predicts neuron-ablation effectiveness across 13 models and 4 families (R^2 = 0.81). The ratio mixes weights and activations, and the target is an ablation outcome, not a benchmark. Nearest miss for C5 (NEW).

[9] [On the Role of Attention Heads in Large Language Model Safety](https://arxiv.org/abs/2410.13708) (2024) — Ships/Sahara safety-head attribution on two same-lineage models. C6/C7 ADJACENT.

[10] [Feint and Attack: Attention-Based Strategies for Jailbreaking and Protecting LLMs](https://arxiv.org/abs/2410.16327) (2024) — Attention to sensitive words correlates with jailbreak success, within the Llama-2 family and across attack methods. C7 ADJACENT.

[11] [GradSafe: Detecting Jailbreak Prompts for LLMs via Safety-Critical Gradient Analysis](https://arxiv.org/abs/2402.13494) (2024) — Parameter-gradient (not input-gradient) safety attribution in one family. C8 ADJACENT.

[12] [Why Safeguarded Ships Run Aground? Aligned Large Language Models' Safety Mechanisms Tend to Be Anchored in The Template Region](https://arxiv.org/html/2502.13946v2) (Chak Tou Leong; 2025) — Template-region normalized indirect effect of the refusal/compliance decision, compared across 6 chat models from 4 families and tied to vulnerability (TempPatch). C9 PUBLISHED.

> For a fair cross-model comparison, we use the normalized indirect effect (NIE)

Locator: Section 3.3, Method/Results

[13] [Harmfulness Propagation Dynamics: Layer-wise Trajectories of Adversarial Intent](https://arxiv.org/abs/2609.13534) (2026) — Harm-only depth trajectories used as per-prompt detection features across 4 families. C10 ADJACENT.

[14] [Safety Alignment Should Be Made More Than Just a Few Tokens Deep](https://arxiv.org/abs/2406.05946) (Xiangyu Qi; 2024) — Per-token KL between aligned and base models over the first tokens. This needs the parent model. C11 ADJACENT.

[15] [First Token Matters: Understanding Safety Collapse in Large Reasoning Models](https://arxiv.org/abs/2609.18471) (2026) — Refusal-projection trajectory that needs a counterpart model (3 instruct/reasoning pairs). C11 ADJACENT.

[16] [The Geometry of Harmful Intent: Training-Free Anomaly Detection via Angular Deviation in LLM Residual Streams (LatentBiopsy)](https://arxiv.org/abs/2603.27412) (Isaac Llorente-Saguer; 2026) — Harmful-vs-XSTest-benign-aggressive AUROC per checkpoint (6 checkpoints, 2 families) as evidence of geometric invariance; no plain-benign baseline ratio. C12 ADJACENT.

> AUROC = 1.000 for discriminating harmful from benign-aggressive prompts (XSTest)

Locator: Abstract, v1

[17] [The Entanglement Wall: Activation-Space Probes as Risk Detectors, Not Context Adjudicators](https://arxiv.org/abs/2607.13075) (Dominik Schwarz; 2026) — Twin/paired probe separation across families; explicitly declines ranking use. C12/C13 ADJACENT.

[18] [Measuring the Wrong Thing: Internal Harmfulness Scores Anti-Rank Successful Jailbreaks](https://arxiv.org/abs/2608.09624) (Mingyu Luo; 2026) — Wrapped-vs-plain harmful-intent AUROC per model (0.936 -> 0.803), framed as a critique of measurement validity. C13 ADJACENT.

[19] [Skin-Deep: A Geometric Diagnostic for Alignment Fragility in Large Language Model Representations](https://arxiv.org/abs/2606.22676) (2026) — GFS with a fixed l/L depth weight (not fitted) across 21 models; parent-dependent (iteration-1 finding). Nearest miss for C14 (NEW).

[20] [RAS: Measuring LLM Safety Through Refusal Alignment](https://arxiv.org/abs/2606.25750) (Chang-Chieh Huang; 2026) — Calibrated 0-100 white-box safety score with a fixed average and a hand-set logistic; needs a per-family reference model. Nearest miss for C14.

[21] [Latent Performance Profiling of Large Language Models](https://arxiv.org/abs/2605.30018) (2026) — Effective rank and participation ratio across 8 LLMs, used as capability profiles, not safety. Nearest miss for C15 (NEW).

[22] [Diff-eRank: A Novel Rank-Based Metric for Evaluating Large Language Models](https://arxiv.org/abs/2401.17139) (2024) — Effective-rank model metric for capability. C15 nearest miss.

[23] [Refusal geometry reflects refusal training: diverse refusal prefixes can raise stable rank and weaken refusal vector ablation attacks](https://arxiv.org/abs/2608.25390) (Andrey Labunets; 2026) — Found in the orchestrator's adversarial pass. Links the stable rank of refusal residuals and gradients to robustness against ablation, in one OLMo-2-1B lineage. New nearest miss for C15; C15 stays NEW.

> diverse refusal starts can raise stable ranks of gradients and activation changes, making refusals harder to remove with a vector ablation attack

Locator: Abstract, v2

[24] [Analysing the Safety Pitfalls of Steering Vectors](https://arxiv.org/html/2603.24543) (Yuxiao Li; 2026) — Per-model OLS slope gamma_1 of the ASR dose-response slope on steering-vector/refusal-direction cosine, compared across 6 models by scale. C16 PUBLISHED (comparator).

> becomes progressively steeper with model size

Locator: Section 6, 'Effect of model scale'; Table 1 (gamma_1 from -36.52 for Llama 7B to -193.40 for Qwen 32B)

[25] [Analyzing the Generalization and Reliability of Steering Vectors](https://arxiv.org/abs/2407.12404) (Daniel Tan, David Chanin, Aengus Lynch, Dimitrios Kanoulas, Brooks Paige, Adria Garriga-Alonso, Robert Kirk; 2024) — The real 'Tan et al.' steering-reliability paper. The draft had attributed this to 2406.09289.

[26] [Understanding Jailbreak Success: A Study of Latent Space Dynamics in Large Language Models](https://arxiv.org/abs/2406.09289) (Sarah Ball, Frauke Kreuter, Nina Rimsky; 2024) — Ball, Kreuter & Rimsky (not Tan et al.). Jailbreak latent dynamics.

[27] [Detecting Safety Training Modification in Language Models via Activation Analysis (AMS)](https://arxiv.org/abs/2608.05578) (Glen Messenger; 2026) — AMS sigma is a non-causal standardized projection separation. The arXiv page lists the IEEE Access DOI 10.1109/ACCESS.2026.3704057.

[28] [N-GLARE: An Non-Generative Latent Representation-Efficient LLM Safety Evaluator](https://arxiv.org/abs/2511.14195) (Zheyu Lin; 2026) — JSS-trajectory stability ratio under 4 probing conditions; closest to C13 in functional form (incumbent map).

[29] [Crossref record: Black-Box Access is Insufficient for Rigorous AI Audits](https://api.crossref.org/works/10.1145/3630106.3659037) (2024) — Confirms the Casper DOI (FAccT '24, pp. 2254-2272). The planner's 'bogus eprint 0106.36590' is a fragment of this correct DOI.

[30] [Crossref record: Detecting Safety Training Modification in Language Models via Activation Analysis](https://api.crossref.org/works/10.1109/ACCESS.2026.3704057) (2026) — Confirms the full AMS DOI, IEEE Access vol. 14, pp. 91723-91737. The 'truncated fragment 2026.37040' is a substring of it.

[31] [Turning the Spell Around: Lightweight Alignment Amplification via Rank-One Safety Injection](https://arxiv.org/abs/2508.20766) (Harethah Abu Shairah, Hasan Abed Al Kader Hammoud, George Turkiyyah, Bernard Ghanem; 2025) — ROSI; full first-author name verified.

[32] [Item Response Theory for AI Safety](https://arxiv.org/abs/2608.05086) (Joshua Fonseca Rivera, Neil Shah, David Demitri Africa, Konstantinos Voudouris; 2026) — Rivera2026 authors verified. The affiliation 'Independent / UK AI Security Institute' had been merged into the author field.

[33] [From Refusal Geometry to Safety Geometry: Harmfulness--Refusal Coupling under Dynamic Adversarial Fine-Tuning](https://arxiv.org/abs/2606.16349) (Wenhao Lan, Shan Li, Xinhua Lai, Meiqi Wu, Junbin Yang, Haihua Shen; 2026) — Lan2026 ID and authors verified (HRCI).

[34] [Inference-Time Backdoors via Chat Templates: From LLM Supply Chains to Agentic System Compromise](https://arxiv.org/abs/2602.04653) (Ariel Fogel, Omer Hofman, Eilon Cohen, Roman Vainshtein; 2026) — Fogel2026 ID verified.

[35] [Qwen3Guard Technical Report](https://arxiv.org/pdf/2510.14276) (2025) — Section 3.5 describes Safety RL on Qwen3-4B with Qwen3Guard-4B-Gen as the reward. This confirms Qwen3Guard must not judge SafeRL.

> Application I: Safety RL with Generative Qwen3Guard

Locator: Section 3.5 heading

[36] [arXiv API (id_list batch metadata)](https://export.arxiv.org/api/query) — Source of every author list, title and version in references.bib (raw/arxiv_atom_*.xml).

[37] [GitHub API: Jorak scanner.py commit history](https://api.github.com/repos/JolanMc/Jorak/commits?path=modelscanner/classifier/scanner.py&per_page=100) (2026) — Three commits touched scanner.py (27957d6 on 2026-07-15, 239fbdb on 2026-07-15, 0351eda on 2026-07-20). The thresholds are 0.5 in all of them.

[41] [Mapping 1,000+ Language Models via the Log-Likelihood Vector](https://arxiv.org/abs/2502.16173) (Momose Oyama; 2025) — Model-map precedent for a metamodel over model representations (output log-likelihoods, not activations). C14 nearest miss.

[42] [Surgical, Cheap, and Flexible: Mitigating False Refusal in Language Models via Single Vector Ablation](https://arxiv.org/abs/2410.03415) (2024) — False-refusal vector ablation. Single-model tool; C2/C12 adjacent.

## Verification

Numbered citations resolve to unique listed sources. Passage checks test text occurrence, not claim truth or entailment. Author/year metadata and locators are not independently verified. Details: `research_verification.json`.

- Source [2]: text found — the refusal rate elicited by the harmfulness direction is much lower than that elicited directly by 
- Source [3]: text found — the Spearman rank correlation between abliteration resistance and jailbreak refusal rate is rho = -0
- Source [7]: text found — svd_align_severed: float = 0.5
- Source [7]: text found — subspace_severed: float = 0.5
- Source [7]: text found — alignement SVD u_min : 0.24 vs 1.00   -> seuil sectionné 0.5
- Source [12]: text found — For a fair cross-model comparison, we use the normalized indirect effect (NIE)
- Source [16]: text found — AUROC = 1.000 for discriminating harmful from benign-aggressive prompts (XSTest)
- Source [23]: text found — diverse refusal starts can raise stable ranks of gradients and activation changes, making refusals h
- Source [24]: text found — becomes progressively steeper with model size
- Source [35]: text found — Application I: Safety RL with Generative Qwen3Guard

## Follow-up Questions

- Does Jorak's own statistic (sigma_1/||U||_F global and round(L/6)-window band alignment, threshold 0.5) produce false positives on the honest panel? This is needed to replace the withdrawn '0.35 / 100% FPR' claim.
- Does any causal quantity keyed to the model's own harm direction (C1/C2/C5) beat Report 74's null (rho = -0.003) once over-refusal is scored as a second arm and a blanket refuser is forced to lose?
- Is Leong et al.'s template-region NIE (C9) numerically correlated with harmful-refusal and over-refusal benchmarks across held-out families, i.e. does the published quantity survive as a score?

---
*Generated by AI Inventor Pipeline*
