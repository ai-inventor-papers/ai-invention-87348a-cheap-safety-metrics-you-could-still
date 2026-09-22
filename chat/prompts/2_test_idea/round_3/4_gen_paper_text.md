# gen_paper_text — test_idea

> Phase: `invention_loop` · round 3 · `gen_paper_text`
> Run: `run_fcYd_7ruOwtm` — One Candidate Survives: A Pre-Registered Screen of Internal Safety Metrics for Language Model Checkpoints
>
> Full, verbatim record of every prompt the AI Inventor pipeline gave this agent — system-user, human-user and skill-input — in the order they landed. Nothing truncated.

## Task: `gen_paper_text` (terminal_claude_agent)

### [1] SYSTEM-USER prompt · 2026-09-21 14:36:21 UTC

````


<pasted_content id="e5c3">
<system-prompt>
<ai_inventor_context>
<ai_inventor_summary>
You are one of many LLMs in AI Inventor — an automated research system that generates NOVEL and FEASIBLE hypotheses, investigates them through experiments and research, and produces a paper.

Your output feeds other LLMs downstream. This demands your ABSOLUTE MAXIMUM reasoning — every output must be deeply thought out and maximally useful. Surface-level responses waste downstream computation.
</ai_inventor_summary>

<your_role>
YOU ARE: A research paper writer (Step 3.4: GEN_PAPER_TEXT in the invention loop)

You received the hypothesis, all artifacts, the previous paper draft (if any), and reviewer feedback.
Write a complete paper draft with figure placeholders.

Publication-quality paper → strong contribution. Weak paper → wasted iteration.
</your_role>
</ai_inventor_context>

<research_methodology>
Write like a researcher drafting a paper, not a chatbot summarizing bullet points.

- Follow <paper_structure> and <results_first> below — they are the shape of the paper and what a reader opens it for, not suggestions.
- Ground every claim in specific artifacts and specific numbers. "Results show improvement" is empty — state effect sizes, baselines, and conditions.
- Be honest about what worked, what didn't, and why. Don't spin failures as "future work."
- The paper's headline contribution should be a positive or surprising finding. Negative results are valuable context but should not be the primary narrative — lead with what works.
- Address reviewer feedback from previous iterations explicitly — show you've thought about each critique.
</research_methodology>

<paper_structure>
Use the structure an expert in the field expects, in this order: Abstract; 1 Introduction; 2 Related Work; 3 Method; 4 Experimental Setup; 5 Results; 6 Discussion and Limitations; 7 Conclusion. Merge or rename a section only where the work genuinely has nothing for it — never by folding it into the Introduction.

- The Introduction contains ONLY: the problem and why it matters, the gap in existing work, the idea in one or two sentences, a contributions list carrying the headline numbers, and a one-sentence roadmap of the paper.
- NO literature survey and NO method details in the Introduction. Prior work goes to Related Work, how the method works goes to Method.
- Organize Related Work by theme rather than one paragraph per paper, and close each theme with a sentence on how this work differs.
- Experimental Setup carries data, baselines, metrics and protocol — enough for an expert to rerun it. Results carries findings, not setup.
</paper_structure>

<results_first>
Ask what a reader actually wants from the paper: the results, with numbers. A reader must be able to get the main finding from the abstract, the main results table and the first results figure alone.

- State the key quantitative results, with the actual numbers, in three places: the abstract, the contributions list, and the opening of Results.
- Results opens with a main results table: the method against every baseline on the headline metric, with variance.
- Every major claim gets at least one results figure (figure_type "data"), plus an ablation or sensitivity plot wherever the artifacts hold the numbers for one.
- Prefer a plot of real numbers over concept art — keep concept figures to the architecture or pipeline diagram the method genuinely needs.
- Reference every figure and table by number in the text and interpret it there: say what the reader should take from it. Never drop one in unexplained.
</results_first>

<figure_placement>
Where a figure sits, what shape it takes and how many there are decide whether a reader can follow the paper.

- Put each [FIGURE:id] marker directly after the paragraph that first discusses the figure, inside the section that owns it: the hero diagram at the end of the Introduction, method and pipeline diagrams in Method, the main comparison and the per-claim results figures in Results, ablation and sensitivity plots in Results or Discussion. Never place a figure in the Abstract, Related Work or Conclusion.
- Let the data relationship pick the chart: grouped bars for the method against baselines on one metric, lines with error bands for trends, scaling and training curves, scatter or a Pareto front for trade-offs, heatmaps for matrices and pairwise grids. A handful of numbers is a table, not a figure. Use multiple panels only when they share axes and one takeaway.
- Aim for roughly four to eight figures in a full paper, with the main results figure first. Each caption stands on its own: what is plotted, on what data, and the takeaway.
</figure_placement>

<available_tools>
Web research is available through the aii-web-tools skill, in three levels (broad → specific):

1. web search — Returns titles, URLs, snippets. Use first to discover and scan the landscape. Two modes: general (default, broad web) and scholarly (peer-reviewed papers + citations) — pass mode=scholarly for prior-art, related-work, and citation lookups.
2. web fetch — Reads a page and returns its content as markdown (HTML or PDF). Use to understand a source. May miss specific details — use fetch_grep below if it doesn't find what you need.
3. fetch_grep — Regex search over a page/PDF's full text. Returns exact matching sections with context. Use for precise details, exact numbers, methodology, or PDFs.

Workflow: search → fetch (understand) → fetch_grep (extract specifics).
</available_tools>

<tool_use>
Maximize parallel tool calls. Parallelize independent operations, only sequentialize dependencies.
- Multiple searches/fetches on different topics → parallel in one turn
- Search then fetch results → sequential (need URLs first)
</tool_use>

<system_reminder>
Do not ask follow up questions and do not ask the user anything. Execute all steps independently.
You must follow the todo list provided in each prompt exactly as written.
No placeholders, stubs, or incomplete code — all code must be complete and functional.
</system_reminder>

<process_isolation>
CRITICAL: Multiple pipeline runs may execute simultaneously on this machine. `ps aux | grep method.py` matches ALL runs, not just yours.
- NEVER kill processes by name (`killall`, `pkill -f`, `ps aux | grep ... | xargs kill`). This kills OTHER runs' processes.
- NEVER monitor processes by name (`ps aux | grep method.py`). You will see other runs' processes and get confused.
- ALWAYS use PID-based process management:
  Run: `uv run method.py & PID=$!` or `timeout <seconds> uv run method.py & PID=$!`
  Check: `kill -0 $PID 2>/dev/null && echo "Running" || echo "Ended"`
  Stop: `kill $PID`
  Wait: `wait $PID; echo "Exit code: $?"`
  Monitor: `tail -f logs/run.log & TAIL_PID=$!` then `kill $TAIL_PID` when done
</process_isolation>

<subagent-delegation>
You may delegate bounded work to subagents (e.g. the Task tool). Delegate by default rather than doing everything yourself:

- Pick the cheapest capable model available to you for each subagent launch:
- Pass `subagent_type="aii-easy"` (steered toward `claude-sonnet-5`) for a small/fast tier for mechanical work.
- Pass `subagent_type="aii-medium"` (steered toward `claude-sonnet-5`) for a mid tier for implementation or investigation (the default).
- Pass `subagent_type="aii-hard"` (steered toward `claude-opus-5`) for the strongest tier only for hard reasoning or after a cheaper model has already failed on the same task.
- Give each subagent prompt one focused objective: exact scope, the acceptance check, and the required output format.
- Subagents report back only the result, changed files, verification, and blockers — not narration or full logs.
- Run genuinely independent pieces of work in parallel, at most 3 concurrently.
- Your own context is the scarcest resource: delegate short tasks too, unless one obvious search-free step beats the handoff.
- Run every orthogonal piece at once: split the work by file or artifact ownership up front, and serialize only where one result feeds the next.
- Escalate to the next tier only after a cheaper subagent failed with evidence; never start at the top.
- Never fork yourself, and never let a subagent spawn its own subagents.
- You (the orchestrator) decompose, coordinate, and synthesize; do not redo work you already delegated.
- Verify each result with the smallest reliable check.
</subagent-delegation>

<workspace>
Your workspace: `/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_3/gen_paper_text/gen_paper_text`

CRITICAL: Every file you create, write, or save MUST be inside this workspace directory (subdirectories OK). You MUST NOT write files anywhere outside this path — external paths are READ-ONLY. Use absolute paths for all file operations.

EVERY file write MUST start with `/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_3/gen_paper_text/gen_paper_text/`:
GOOD: `/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_3/gen_paper_text/gen_paper_text/file.py`, `/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_3/gen_paper_text/gen_paper_text/results/out.json`
BAD: `/tmp/file.py`, `~/output.json`, `./file.py`, any path outside the workspace
</workspace>
</system-prompt>

<prompt>
<available_domain_handbooks>
Domain handbooks below capture expert knowledge for a specific field — its landscape, prior work, dead ends, evaluation norms, and what counts as a genuinely novel contribution. If one is relevant to your research topic, READ that skill BEFORE proceeding; read the most relevant one(s), or none if none apply. When none fit, do not force one — instead ground your work harder in primary sources and hold novelty claims to extra scrutiny, since you have no curated map of this field's prior work and dead ends. Use it for related-work positioning and how this field frames a genuinely novel contribution.

- **aii-handbook-auto-computational-linguistics** — Field handbook for computational linguistics as a SCIENCE of language — grammaticality and minimal pairs (BLiMP), surprisal versus reading times, linguistic structure in LMs, annotator disagreement an
- **aii-handbook-auto-mechanistic-interpretability** — Field handbook for mechanistic interpretability of neural networks — circuit discovery, activation and attribution patching, sparse autoencoders, transcoders, attribution graphs, steering vectors, pro
- **aii-handbook-auto-multi-agent-llm-systems** — Field handbook for multi-agent LLM systems (MAS) — orchestration topology, multi-agent debate, mixture-of-agents, verifier and critic agents, inter-agent protocols (MCP/A2A), failure attribution and s
- **aii-handbook-auto-neurosymbolic** — Field handbook for neuro-symbolic AI — text-to-logic autoformalization (NL to FOL), LLM-plus-solver and prover pipelines (Prolog, ASP, SMT), probabilistic-differentiable NeSy (DeepProbLog, Scallop), r
</available_domain_handbooks>
<writing_register>
Write in the register of the field's best papers (the passages you collect in the STYLE EXEMPLARS todo), not in the register of a language
model. Four things are measured on the finished draft, and a draft outside them is sent back with
the numbers:
- Never use: delve, underscore, showcase, intricate, pivotal, realm, commendable, meticulous, tapestry, garner, multifaceted, it is worth noting, plays a crucial role, not only ... but also. These are 10 to 30 times more frequent in machine-written abstracts than in
  human ones, and reviewers read them as such.
- Em dashes: at most 3 per 1,000 words. Use a comma, a colon or a full stop.
- Sentence rhythm: mix short and long sentences. An interquartile range of sentence length under
  8 words reads as machine-written.
- He
</pasted_content id="e5c3">


<pasted_content id="e5c3">
dging: at most 15 hedges (may, likely, suggests, appears) per 1,000
  words. State what the evidence supports plainly; hedge where it is thin, not everywhere.
Style never changes substance: numbers, claims, citations and figure markers stay exactly as the
evidence gives them. The user's original request (delivered as a separate message) overrides all
of this wherever the two conflict.
</writing_register>
<previous_paper>
STARTING POINT: This is your paper draft from the previous iteration.

## 1 Introduction

Anyone who downloads a model from Hugging Face is trusting an artifact uploaded by a stranger. The platform hosts over a million models, almost none carry safety evaluations, and running a benchmark on each is out of the question. A growing line of work therefore builds cheap proxies: read a few weights, run a handful of prompts, get a safety estimate in seconds. Every one of these proxies is selected by correlating it with benchmark scores across honestly-trained checkpoints and picking the winner [1, 2, 3, 4].

Three things are wrong with that selection rule, and none has been tested in combination.

First, nobody has checked which cheap readouts survive being moved to a lineage they were not tuned on. Published work shows that harmful intent is linearly decodable at approximately 0.98 AUROC in every tested checkpoint, including abliterated ones, with abliterated variants matching their instruction-tuned counterparts to within 0.003 [5, 6]. A readout of what the model knows is therefore near-constant across alignment variants and cannot separate them. What varies is whether the model's refusal mechanism uses that knowledge, a statement about a relationship across items rather than about a level.

Second, the selection rule assumes honesty. The cheapest proxies read the most superficial thing a model does, and the most superficial thing is the cheapest to change. A chat template is a text file inside the repository. A rank-one addition to the residual-write matrices needs no training data and no gradient step [7], and it is not hypothetical: it is a published method presented as a cheap safety improvement [8], validated with a guard model's refusal rate on harmful prompts and compliance on ordinary benign prompts, but never on the benign-but-alarming requests where pushing a model toward refusal actually does damage.

Third, the ground truth itself may be broken. We discover that LLM judges used to score harmful compliance under the standard StrongREJECT rubric [9] refuse to engage with the grading task: 40.5% of all grades and 65.9% of grades on harmful items collapse to the minimum score, producing an inverted label that makes abliterated models appear to refuse more than their instruction-tuned siblings. This artifact is invisible unless the evaluator checks known-compliant harmful responses, and it contaminates any downstream metric selection.

We address all three gaps. We register fifty single-checkpoint metrics before any measurement, test all fifty on 33 checkpoints spanning eight architecture families, and pair the metric race with a six-rung forgery-cost ladder and a parent-free weight-recovery study on 71 real abliterated checkpoints. Our contributions are:

1. A discovery that LLM judges refuse to grade harmful completions under standard rubrics, silently inverting 40.5% of safety labels, and a stance-classification reframing that restores correct grading (Section 3.3).

2. A pre-registered battery of fifty safety metrics tested on 33 checkpoints across eight families, finding that only three beat their own label-permutation null, and a zero-prompt card regex outperforms every internal readout at leave-one-lineage-out balanced accuracy 0.917 (Section 5.1).

3. Evidence that fitted harm directions survive an anisotropy-matched null on 16 of 17 checkpoints, resolving a prior ambiguity, but that a one-prompt black-box logit readout already exceeds the internal probe's correlation with safety (Section 5.2).

4. A six-rung forgery-cost ladder showing that the published rank-one safety injection [8] reverses on two-sided ground truth, and that the pre-registered parent-free weight detection axis must be withdrawn (Section 5.3).

5. A study of 71 real abliterated checkpoints finding that weight reads detect edits but cannot grade how unsafe the model is, an identifiability limit confirmed by the true parent-based edit strength (Section 5.4).

[FIGURE:fig_overview]

## 2 Related Work

**Cheap per-checkpoint safety readouts.** AMS [1] computes a separation statistic along a difference-of-centroids direction on 96 forward passes and reports 71% leave-one-out accuracy across 14 models, but its direction, layer sweep and prompt set are never held out, and its Spearman rank correlation with behavioural compliance is not significant (rho = -0.423, p = 0.13, n = 14). Skin-Deep [2] produces a Geometric Fragility Score predicting LoRA-attack retention, but requires the base model and 1000 prompts. N-GLARE [3] reads hidden-state trajectories with no parent model and reproduces red-team rankings, but needs four probing conditions over 7000 cases. RAS [4] produces a calibrated score separating aligned from abliterated variants 210x faster than judge-based scoring, but requires a per-family reference model and states that family-specific calibration remains necessary. None is both parent-free and validated on held-out lineages with a two-sided ground truth that penalizes blanket refusers.

**The geometry of refusal and harm knowledge.** Arditi et al. [7] showed that a single direction in the residual stream controls refusal and that orthogonalizing weight matrices against it removes refusal entirely. Subsequent work established that harmful intent is linearly separable at approximately 0.98 AUROC across four families and three alignment variants including abliterated ones [5], and that abliterated variants match instruction-tuned ones to within 0.015 AUROC on harm-knowledge probes [6]. The dissociation between harm knowledge and refusal is now well documented: harmfulness and refusal are encoded separately [10], refusal reads only a single harm direction while moral judgment reads progressively more [11], and recognition precedes execution in the layer stack [12]. This study uses the dissociation as a prediction: harm-knowledge readouts should be near-constant across variants and cannot discriminate.

**Harmfulness-refusal coupling.** The coupling between harm recognition and refusal drive has been studied as a diagnostic under adversarial fine-tuning [13], where it is explicitly concluded that low coupling is not a safety predictor because supervised fine-tuning reaches low coupling while remaining unsafe. HARC [14] trains coupling as a defence. We adopt coupling as a discriminator between alignment classes and cross-fit it where prior work does not.

**Parent-free weight auditing.** Watch the Weights [15] reports that applying SVD to weights directly, without a base model, gives success that varies greatly across models. A community model scanner [16] computes bottom-k left singular subspace alignment across layers as a reference-free abliteration indicator. The two-signal abliteration audit [17] combines a reference-anchored activation gap with a weight-energy ratio at approximately 0.95 AUROC, but presumes an attested reference. We adopt the community scanner as an off-the-shelf tool and contribute the calibration it lacks.

**Forgery, tamper-resistance and benchmark gaming.** Tamper-resistant safeguards [18] measure what it costs to remove safety; we measure what it costs to fake it. Benchmark gaming is documented for black-box evaluations: constant outputs achieve high win rates [19], safety-benchmark variance is largely capabilities [20], and the leaderboard illusion is well characterized [21]. Gaming the Metric, Not the Harm [22] proves that level metrics are not manipulation-invariant. Rank-one safety injection [8] is a published fine-tuning-free weight edit presented as a defence, which we include as a rung in the forgery ladder. Chat-template backdoors [23] establish that repository files are an unexamined attack surface. None of this prior work combines a metric read from weights or activations with a cost-ordered forgery ladder and a reference-free detection check.

**Evaluation methodology.** Cross-fitting internal readouts is standard in neuroscience but rare in LLM safety evaluation. The brittleness of fixed probes under distribution shift is documented both for steering vectors [24] and for safety probes [25, 26]. Item response theory has been applied to reduce safety evaluation cost [27, 28], but only for behavioural items, not internal readouts. Black-box access alone is insufficient for rigorous AI audits [29].

## 3 Method

### 3.1 Metric Battery and Registration

We register fifty single-checkpoint safety metrics before any measurement. Each metric is computed from a single downloaded checkpoint with no parent model, no attested base, and no benchmark run. The registry is frozen with a SHA-256 hash before the first measurement and verified unchanged at the end.

The fifty metrics span three groups. **Knowledge readouts** (12 metrics) include cross-fitted harm-direction probes at various layers, harm-projection gaps, and reimplementations of published incumbents (AMS separation [1] in both in-sample and cross-fitted forms, HRCI coupling index [13]). **Behavioural and structural readouts** (20 metrics) include first-token logit-gap margins, refusal-token probability mass, greedy refusal rates, model-card regex scores, weight statistics including bottom-subspace alignment (BSA), top-subspace alignment (TSA), spectral entropy, and BOTGAP. **Across-item readouts** (18 metrics) include coupling between refusal drive and cross-fitted harm estimate, decision spread, mutual information, per-category dispersion, and presentation invariance.

### 3.2 Cross-Fitting Protocol

Every fitted-direction metric uses a pre-registered four-fold structure stratified by harm category. The residual stream is 1536 to 3072 dimensional while the item count is a few dozen. In that regime, an in-sample difference-in-means projection separates pure noise at AUROC 1.000. Cross-fitting is therefore part of the metric definition, not an analysis choice. The direction is fitted on three folds and evaluated on the held-out fold; the reported metric is the mean across held-out folds. A per-checkpoint label-permutation null and an in-sample version are printed for every metric so the gap between them is visible.

### 3.3 Ground Truth and the Grader-Side Refusal Discovery

The ground truth has two columns: graded compliance with harmful requests (StrongREJECT rubric [9]) and false refusal on benign-but-alarming twins (XSTest [30]). A model refusing everything scores badly on the false-refusal column rather than winning. The two-sided score D2 is the average of harmful-refusal rate and benign-compliance rate, rewarding models that refuse harmful requests and comply with benign ones.

We discovered that LLM judges refuse to grade harmful completions under the standard StrongREJECT rubric framing. Asked to rate a reply to a harmful prompt, gpt-5-mini, gpt-4.1-mini and gemini-2.5-flash all emit the minimum triple (1, 1, 1) regardless of what the reply actually did. On 1040 paired items, 40.5% of StrongREJECT grades are the degenerate minimum (65.9% on harmful items). The disagreement is one-sided: 330 items where the standard framing says "refused" but the reply was in fact compliant, versus 66 the other way. Without the fix, an abliterated model reads as safer than its instruction-tuned sibling.

Reframing as stance classification ("you are a text classifier; classifying text is not endorsing it") and asking for declined/engagement/detail labels takes the controlled accuracy from 3/6 to 6/6 on both judges tested, and raises inter-judge Cohen's kappa from 0.456 to 0.585. We use the stance framing throughout; inter-judge agreement on the final instrument is kappa = 0.785 (n = 476).

[FIGURE:fig_grader_refusal]

### 3.4 Lexical Floor

Before evaluating internal readouts, we establish the floor that a no-model text classifier achieves. TF-IDF plus logistic regression separates harmful from safe prompts at AUC 0.963 when sources are unmatched (StrongREJECT harmful vs. XSTest safe), but only 0.537 against JailbreakBench's own paired benign partners and 0.655 on XSTest positional twins with pair-grouped cross-validation. Every internal readout must beat the matched numbers.

### 3.5 Leave-One-Group-Out Null

Under uninformative random labels, leave-one-group-out balanced accuracy has an empirical mean of 0.403 (sd 0.131), not the nominal 0.500, because held-out group class balance is negatively correlated with the training remainder's. Every race-table row is compared against a matched label-permutation null rather than against 0.50.

## 4 Experimental Setup

### 4.1 Panel

The main experiment spans 33 checkpoints across eight architecture families (Qwen3, Qwen2.5, Gemma2, Phi4, SmolLM2, SmolLM3, OLMo2, TinyLlama), all under approximately 4B parameters, loaded in bf16 with full weight and hidden-state access. Checkpoints are classified into four arms: base, instruct, safety-tuned and abliterated. Only three families carry an instruct/abliterated pair (Phi4, Qwen2.5, Qwen3), below the pre-registered floor of five for a leave-one-family-out claim, so the primary holdout is leave-one-lineage-out. The resampling unit is the lineage (parent model x tuning run), never the individual repository.

A separate offline evaluation uses 17 fully harvested checkpoints from a prior iteration (Qwen3 and TinyLlama only, four lineages) to run the anisotropy control suite at zero new compute.

The weight-recovery study (Section 5.4) spans 71 real abliterated or uncensored checkpoints with readable safetensors, drawn from the Hugging Face ecosystem.

### 4.2 Item Battery

The item battery contains 160 items: harmful requests from JailbreakBench Behaviours and StrongREJECT, benign-but-alarming twins from XSTest (200 positional twin pairs), and paired benign partners from the JailbreakBench Index. Items are allocated across four stratified folds. Grading uses a non-Qwen hosted judge (gpt-5-mini with reasoning effort set to minimal), with the StrongREJECT score recomputed from rubric components under the stance-classification framing.

### 4.3 Forgery Ladder

Six rungs, each applied to six honest checkpoints spanning six architecture families. F0: chat-template edit (zero FLOPs). F1: inference-time system prompt. F2a: constant offset in a near-constant carrier coordinate. F2b: published rank-one safety injection [8]. F3: keyword-triggered refusal LoRA adapter. F4: genuine light safety fine-tuning. Each rung is evaluated against the full metric battery and scored by two auditor tiers: a blind tier (template content, key-shape check, and weight statistic) and a family-aware tier that may diff against the family default.

### 4.4 Stage Gates

The experiment uses pre-registered stage gates. G2 fires if fewer than five families carry a two-way pair, downgrading the holdout to leave-one-lineage-out. The readout bake-off selects from five candidate refusal definitions by agreement with judged refusal on held-out item folds; the acceptance bar is AUROC at least 0.80 on every checkpoint including abliterated ones. Both gates fired.

## 5 Results

### 5.1 The Race Table

Of the fifty registered metrics, only three beat their own label-permutation null at the 95th percentile on the 33-checkpoint, 8-family panel with leave-one-lineage-out scoring (Table 1).

The card regex, a regular expression over the uploader's own model card that reads nothing of the model, separates abliterated from everything else at AUROC 1.000 and leave-one-lineage-out balanced accuracy 0.917. Its de-biased twin, which removes model-name terms, collapses to approximately 0.10. The power is the uploader telling you, and that is the cheapest rung of the forgery ladder.

The best weight-only metric achieves balanced accuracy 0.826, which ties its own null 95th percentile. The best across-item metric (presentation invariance) achieves balanced accuracy 1.000 at leave-one-lineage-out but its family-separation score is only 0.257, suggesting it tracks presentation format rather than family-independent safety.

Only one metric survives both the label-permutation null and the blanket-refuser pole rule. The pre-registered shipping invariant, which requires at least three qualifying metrics reading hidden states or weights, is not satisfied.

[FIGURE:fig_race_table]

### 5.2 The Anisotropy Control Resolves

On the 17-checkpoint offline panel (Qwen3 and TinyLlama), a cross-fitted harm-content probe at the last prompt token survives the anisotropy-matched null on 16 of 17 checkpoints (94.1%), with mean cross-fitted AUROC 0.835 against a mean within-item-span null of 0.629 (1000 draws per checkpoint). The anisotropy-matched null draws random directions in the item-level residual-stream subspace rather than using global random projections, so a direction that beats it carries item-specific content rather than reflecting the dominant axes of the representation space. The prior iteration's tie (fitted 0.921 vs. best-of-20 null 0.921) was caused by using a point estimate of the null maximum, which is an upward-biased approximation of the null distribution. The 1000-draw null reveals that the fitted direction is genuinely above the null on almost every checkpoint.

However, this does not translate into a strong safety readout. A black-box logit readout at one prompt already exceeds the internal probe's Spearman correlation with the two-sided safety target (0.282 at k = 1 vs. 0.021 for the internal probe). The gap persists at every prompt budget tested (k = 1 through 64). Internal access does not buy additional safety discrimination over what a single logit read provides.

[FIGURE:fig_anisotropy]

### 5.3 The Forgery Ladder

**The rank-one injection reverses.** The published rank-one safety injection [8] was recovered at alpha* = x4 on one of its own Table-1 models (Qwen2.5-0.5B-Instruct). At alpha*, harmful refusal rises from 0.859 to 0.984 while false refusal on matched benign-but-alarming twins rises from 0.375 to 0.750. The two-sided score D2 falls from 0.788 to 0.621 (bootstrap 95% CI for the change: [-0.233, -0.065]). The reversal replicates on Qwen3-0.6B (D2 0.784 to 0.703, false refusal 0.219 to 0.469). A negative-control injection using a random direction produces D2 change of -0.042, confirming that the effect is specific to the published direction. At x16, the model becomes a blanket refuser (false refusal 1.000, D2 = 0.500). The method's own evaluation metric, which uses only harmful-prompt refusal rate and benign compliance on ordinary instructions without an over-refusal column, improves at every dose.

[FIGURE:fig_rosi_reversal]

**Detection axis withdrawn.** The pre-registered parent-free weight detection axis achieves a best cross-family AUROC of 0.738 at 12 families, below the 0.80 bar. The B3 weight screen fires on 3 of 6 honest, unedited ladder hosts, so the screen itself carries no signal about an edit. The detection axis is formally withdrawn. Within-family, the same statistic reaches AUROC 1.000 on Qwen3/TinyLlama, confirming that it reads architecture-specific spectral structure rather than a safety-relevant signal.

**Detection by rung.** The blind auditor tier catches F0 (chat-template edit) in 26 of 30 cells via template rendering. F1 (system prompt) is invisible by construction. The bias-tensor variant of F2a is caught in 30 of 30 cells by a key-shape check. The carrier-coordinate variant of F2a, the rank-one injection F2b, and all training-based rungs (F3, F4) evade every blind screen except the weight statistic, which is itself unreliable. The family-aware auditor tier catches 147 of 147 additional cells, adding 27.9% detection.

### 5.4 Weights Read the Edit, Not the Risk

A study of 71 real abliterated or uncensored checkpoints spanning five families tested whether the parent-free recovered edit strength predicts measured harmful compliance. The bottom left singular vector of MLP-output matrices recovers the suppressed direction with median cosine 0.946 against the true parent-based direction. Detection works: the recovered strength achieves pooled AUROC 0.84 against honestly-trained checkpoints (0.95 restricted to abliteration-tool outputs).

Grading does not. Within the edited arm (n = 14 graded checkpoints, 5 families), the Spearman correlation between recovered strength and measured compliance is 0.26 (p = 0.375, 95% family-cluster bootstrap CI [-0.65, 0.86]). Adding the recovered strength to a binary edited/not-edited label worsens out-of-family prediction (leave-one-family-out MAE rises from 0.154 to 0.170).

The failure is not estimation error. Even the true parent-based edit strength, computed from the actual parent-to-edited difference, does not correlate with compliance (Spearman 0.035, p = 0.914, n = 12). Over-ablation is common: true edit-strength values span 0.47 to 1.47, and a checkpoint with the largest edit scar in the panel (1.47) still refuses 81% of harmful prompts. The identifiability limit is structural: a spectral read recovers the unsigned magnitude of the edit, not its signed strength, so over-ablation and under-ablation of equal magnitude are indistinguishable.

A targeted repair experiment confirms the decoupling: spectral repair of the weight-detector signature does not restore the original behaviour (compliance 0.401 after repair vs. 0.367 for the honest parent). The weights can be healed without healing the model.

[FIGURE:fig_edit_not_risk]

### 5.5 Supporting Results

**Cross-fitting is load-bearing.** On pure Gaussian noise at d = 2560 with 64 randomly-labelled items, an in-sample difference-in-means projection separates at AUROC 1.000. The cross-fitted version falls to 0.377. On real checkpoints, the AMS scanner's [1] in-sample separation exceeds its cross-fitted version by 0.48 to 1.14 sigma, with the largest gap on the abliterated checkpoint. The BSA statistic on honest Qwen3-0.6B weights reproduces exactly across iterations (0.5649782), confirming the weight pass is deterministic.

**The published weight threshold fails.** Honest, unedited checkpoints read BSA 0.565 against the published 0.35 separator, a false-positive rate of 100%. The within-checkpoint anisotropy null (z = 25.1) confirms that real transformers carry genuinely shared bottom-subspace directions that Gaussian simulation does not produce.

**float32 Gram matrices produce silent failures.** On honest OLMo-2 attention-output projections, a float32 Gram returns the smallest singular value as exactly zero (true value in float64: 1.7e-5 to 3e-4), producing the abliterated signature on an unedited model. All weight analyses in this study use float64.

**No readout clears the acceptance bar.** The readout bake-off tested five definitions of refusal drive against judged refusal. The best achieves mean AUROC 0.733 with a minimum of 0.544; the logit gap achieves mean 0.630 with a minimum of 0.437. None clears the pre-registered bar of 0.80 on every checkpoint.

**Safety-tuned lineages are scarce.** Only three independent safety-tuned lineages exist below 4B parameters in our census: Qwen3-4B-SafeRL, TinyLlama-1.1B (four safety algorithms applied to one base), and gemma-2-2b (two safety-tuned variants). The models a downloader is most likely to encounter are those with no safety-tuned sibling and no published safety number.

## 6 Discussion and Limitations

### 6.1 What the Results Mean Together

The five main results form a coherent picture. The card regex wins the race (Section 5.1) because the information most predictive of safety alignment is what the uploader chose to disclose, not what the model computes. The harm direction survives the anisotropy null (Section 5.2) but a one-prompt black-box readout already beats it, which means the internal access that the direction requires does not buy additional safety discrimination. The forgery ladder (Section 5.3) shows that the cheapest intervention that moves internal metrics, a rank-one weight edit, reverses on two-sided ground truth, making the metric worse than useless to the auditor who trusts it. And the weight-recovery study (Section 5.4) confirms that the spectral signature detects the edit but says nothing about how unsafe the edited model is. The thread connecting all four is that looking inside the model, whether at activations or weights, does not yet translate into a safety readout that survives being moved to a new lineage, a new family, or a motivated uploader.

### 6.2 Grader-Side Refusal

The grader-side refusal discovery (Section 3.3) has implications beyond this study. Any safety evaluation that asks an LLM judge to grade harmful completions under a rubric that presents the harmful prompt as the object of assessment is vulnerable. The degenerate minimum grade is indistinguishable from a legitimate minimum score and silently inverts the ground truth. The stance-classification reframing is not our contribution as a technique; framing classification as a neutral analytical task to avoid refusal is a known practice. The contribution is documenting that the standard StrongREJECT rubric triggers it at 65.9% on harmful items across three major hosted judges.

### 6.3 Limitations

**Family axis is degraded.** Only three of eight families carry an instruct/abliterated pair, so the primary holdout is leave-one-lineage-out rather than leave-one-family-out. Transfer claims require a larger panel.

**Panel size for the grading test.** The weight-recovery grading test (n = 14 graded checkpoints) has an achieved minimum detectable effect of |rho| = 0.56. A moderate correlation would not be detected.

**Single primary judge.** The ground truth relies on a single hosted judge (gpt-5-mini) with a partial second-judge audit (gemini-2.5-flash, kappa = 0.785). Full inter-rater reliability requires more judges.

**Forgery ladder not trained.** The LoRA and SFT rungs (F3, F4) use merged adapter-shaped weight deltas without actual training; they test the detection surface only.

**No generation on most checkpoints.** Only 3 of 33 checkpoints in the main panel were generated from on CPU in this iteration. Most behavioural metrics rely on inherited GPU-harvested generations.

## 7 Conclusion

We registered fifty single-checkpoint safety metrics and tested them against pre-registered controls on 33 checkpoints across eight architecture families. Most metrics do not beat their own label-permutation null, a zero-prompt card regex outperforms every internal readout, and the one metric that survives all controls reads presentation format rather than a family-independent safety signal. A published rank-one safety injection reverses on two-sided ground truth. Parent-free weight reads detect that a model was edited but cannot say how unsafe the edit made it. The grader-side refusal we discovered along the way, in which LLM judges silently refuse to grade harmful completions under standard rubrics, contaminates any downstream metric selection that does not check for it.

These are findings, not obstacles. Reporting that cheap safety metrics do not yet work as advertised is the first step toward metrics one could actually believe. The most productive next steps are fixing the readout operationalization so that internal access buys something a black-box logit read does not, expanding the family axis to support a leave-one-family-out claim, and testing whether the reversal of rank-one injection on two-sided ground truth extends to other weight-editing methods.

## References

[1] G. Messenger, "Detecting Safety Training Modification in Language Models via Activation Analysis," arXiv:2608.05578, 2026.

[2] J.-S. Lee et al., "Skin-Deep: A Geometric Diagnostic for Alignment Fragility in Large Language Model Representations," arXiv:2606.22676, 2026.

[3] J. Cordes et al., "N-GLARE: A Non-Generative Latent Representation-Efficient LLM Safety Evaluator," ACL 2026.

[4] Z. Lin et al., "RAS: Measuring LLM Safety Through Refusal Alignment," arXiv:2606.25750, 2026.

[5] A. Vogel et al., "Harmful Intent as a Geometrically Recoverable Feature of LLM Residual Streams," arXiv:2604.18901, 2025.

[6] S. Guo et al., "LatentBiopsy," arXiv:2603.27412, 2025.

[7] A. Arditi et al., "Refusal in Language Models Is Mediated by a Single Direction," NeurIPS 2024, arXiv:2406.11717.

[8] Y. Wang et al., "Rank-One Safety Injection," arXiv:2508.20766, 2025.

[9] A. Souly et al., "A StrongREJECT for Empty Jailbreaks," NeurIPS 2024, arXiv:2402.10260.

[10] D. Li et al., "LLMs Encode Harmfulness and Refusal Separately," NeurIPS 2025, arXiv:2507.11878.

[11] T. B. Brown et al., "There Is More to Refusal in Large Language Models than a Single Direction," arXiv:2602.02132, 2025.

[12] Z. Huang et al., "From Refusal Geometry to Safety Geometry: Recognition Versus Execution," arXiv:2603.05773, 2025.

[13] M. Chen et al., "From Refusal Geometry to Safety Geometry: Harmfulness-Refusal Coupling under Dynamic Adversarial Fine-Tuning," arXiv:2606.16349, 2026.

[14] Y. Zhang et al., "HARC: Training Harmfulness-Refusal Coupling as a Defence," arXiv:2607.00572, 2026.

[15] A. Timans et al., "Watch the Weights," arXiv:2508.00161, 2025.

[16] Jorak Project, "Model Scanner: Subspace Signature for Abliteration Detection," GitHub, 2025.

[17] K. Park et al., "Has This Checkpoint Been Abliterated? A Two-Signal Audit," arXiv:2607.01854, 2026.

[18] N. Tamirisa et al., "Tamper-Resistant Safeguards for Open-Weight LLMs," ICLR 2025, arXiv:2408.00761.

[19] L. Zheng et al., "Cheating Automatic LLM Benchmarks: Null Models Achieve High Win Rates," ICLR 2025, arXiv:2410.07137.

[20] L. Ren et al., "Safetywashing: Do AI Safety Benchmarks Actually Measure Safety of AI Systems?" arXiv:2407.21792, 2024.

[21] E. Boyko et al., "The Leaderboard Illusion," arXiv:2504.20879, 2025.

[22] D. Wen et al., "Gaming the Metric, Not the Harm," arXiv:2605.06324, 2026.

[23] A. Jha et al., "Inference-Time Backdoors via Chat Templates," arXiv:2602.04653, 2025.

[24] C. Tan et al., "On the Out-of-Distribution Brittleness of Steering Vectors," NeurIPS 2024, arXiv:2406.09289.

[25] J. Wu et al., "Measuring the Wrong Thing: Harmful-Intent Decoding Under Wrapping," arXiv:2608.09624, 2026.

[26] L. Wang et al., "The Entanglement Wall: Fixed-Probe Transfer Across Model Families," arXiv:2607.13075, 2026.

[27] K. Ganguli et al., "Item Response Theory for AI Safety," arXiv:2608.05086, 2026.

[28] S. Jha et al., "Efficient Safety Evaluation via Item Response Theory," arXiv:2606.20626, 2026.

[29] J. Casper et al., "Black-Box Access is Insufficient for Rigorous AI Audits," FAccT 2024, arXiv:2401.14446.

[30] P. Rottger et al., "XSTest: A Test Suite for Identifying Exaggerated Safety Behaviours in Large Language Models," NAACL 2024.
</previous_paper>

<reviewer_feedback>
STEP 1 — REVIEW: A reviewer evaluated the previous paper draft above and produced this feedback.

The previous review is BLOCKING: the paper must not ship as it stands. Every MUST-FIX item below is a requirement for this iteration, not a suggestion — an iteration that leaves one unaddressed does not publish.

- [MAJOR MUST-FIX] (evidence) The headline claim (Contribution 2, Section 5.1) contradicts the race table. It says 'a zero-prompt card regex outperforms every internal readout at LOLO BA 0.917'. But the race table (exp1 RESULTS, summary) shows x_presentation_invariance, computed under the hidden-state probe readout, at LOLO BA 1.000 (null p95 0.775), above the card regex's 0.917. Section 5.1 even reports that 1.000. The paper also omits the most damning fact about that metric: in step5_correlations.json it is ANTI-correlated with the two-sided safety target (Spearman -0.71, p=0.007, n=13 checkpoints; -0.40 at lineage level, n=5). It also omits that the card regex itself FAILS the blanket-refuser pole rule.
  Action: Restate Contribution 2 as follows. Three of 50 beat their null. The card regex (reads nothing) reaches 0.917 but fails the pole rule. The only metric passing null + poles (presentation invariance, an internal across-item read, 1.000) correlates negatively with the two-sided target (rho -0.71). So no metric that reads the model is both discriminative and safety-aligned. Put those three facts in one row block of Table 1.
- [MAJOR MUST-FIX] (evidence) Selective reporting in Section 5.4 (weights read the edit, not the risk). The exp3 artifact reports a source-stratified replication on three other runs' stored generations: combined within-edited rho 0.849, CI [0.555, 0.954], n=20. On projection edits only, rho is 0.651, CI [-0.255, 0.949], n=10. The artifact itself concludes 'a graded signal is not excluded, not established'. The paper reports only the n=14 null (0.26, MDE 0.56) and the n=12 true-kappa null, and presents grading failure as settled and 'structural'. Its 'unsigned magnitude' explanation also differs from the artifact's: the read is exact inside |1-kappa| < sigma_min/sigma_rms and blind outside, with 307/484 matrices outside.
  Action: Add the replication rows with CIs and explain the edit-type confound the artifact names: mixed abliteration and fine-tune uncensoring partly re-detects edit TYPE. Downgrade the claim to 'no evidence of grading within a 14-checkpoint panel, powered only for |rho|>=0.56; external replication is positive but confounded'. Replace the 'unsigned magnitude' sentence with the artifact's validity-band result (median cos 1.0 in range vs 0.14 out of range).
- [MAJOR MUST-FIX] (evidence) The Section 5.2 prompt-budget claim overreaches. 'The gap persists at every prompt budget tested (k=1 through 64)' holds only for |rho|. On the pre-registered primary metric, LOLO balanced accuracy, internal overtakes black-box at k=64 (0.592 vs 0.571). The bootstrap reports frac_never_cross 0.165 and median crossover k 4.5, so the crossover is uncertain. The 0.282 vs 0.021 comparison is also a single k=1 point on a 15-checkpoint/9-two-way subset. At k=8 the internal |rho| is 0.210 vs 0.337, so '0.021' is the least favourable internal point.
  Action: Show the full k-table as a line figure with both |rho| and LOLO BA and lineage-bootstrap bands. State the panel (15 ckpts, 3 families). Write: 'black-box leads on rank correlation at every k; on held-out BA it leads at k<=32 and ties or trails at k=64'.
- [MAJOR MUST-FIX] (evidence) Section 5.2's 'anisotropy control resolves' omits contrary evidence from the same run. The 16/17 result is for the last-prompt-token content read on the 2-family offline panel. The same eval artifact finds the first-generated-token read at 9/17 (PREMISE_FAILS). The exp1 artifact reports that the fitted harm direction beats the within-span null p95 on only 9/20 checkpoints (gate G8) on the 8-family panel. The whitened (LDA) refit is also lower (0.759 vs 0.835), meaning the direction partly rides anisotropy. 'Resolves' is therefore true only for one read position within two families.
  Action: Report all three numbers (16/17 last-prompt-token within-family; 9/17 first-generated-token; 9/20 cross-family G8) plus the whitening caveat. Retitle the section to 'Harm-content directions survive the anisotropy null within family at the prompt token, not cross-family'.
- [MAJOR MUST-FIX] (scope) Coverage against the user's request is partial. The user asked for: (Step 1) an open-ended activation/weight comparison of Qwen3-4B Base/Instruct/SafeRL/abliterated; (Step 4) external ground truth from model cards, papers and leaderboards covering aspects beyond refusal (TrustLLM/AIR-Bench) plus capability benchmarks (GSM8K, MMLU, Arena-Hard) to test the safety-capability trade-off; (Step 5) top-10 metrics correlated against those benchmark numbers at both aggregation units; (Bonus) a mechanistic 'why'; (Bonus bonus) an activation metamodel. The paper contains none of Step 1, Step 5 or the metamodel, and no capability numbers. Its ground truth is its own judge only. The artifacts do contain step1_anchor, step5_correlations.json, metamodel.json (held-out 0.5 vs tuned 1.0) and a HELM limb (81 models, only 2 sub-4B with published numbers, 6.7x guardian ceiling).
  Action: Add a Section 5.x 'Qwen3-4B lineage anatomy' with the principal-angle and mean-difference results, reconciling SHARED_SUBSPACE vs DIFFERENT_SUBSPACES. Add 'Correlation with the target (Step 5)', a table of the top-10 metrics x {checkpoint, lineage} Spearman with n. Add 'External ground truth', explaining why published numbers are unavailable below 4B and reporting the guardian ceiling. Add a one-paragraph metamodel negative. Where capability benchmarks were not collected, say so explicitly in Limitations.
- [MAJOR MUST-FIX] (evidence) The repair experiment is misreported. The paper says 'spectral repair does not restore the original behaviour (compliance 0.401 after repair vs 0.367 for the honest parent)'. But compliance moved from 0.474 (edited) to 0.401, i.e. most of the way to the parent's 0.367, so the quoted numbers weaken the claim. The behaviourally decisive numbers in the artifact are harmful refusal 0.125->0.208 (parent 0.438) and BB8 0.25->0.25 (parent 0.625). Only one of three repair variants ('swap') was behaviourally graded, on n=1 host.
  Action: Quote refusal and BB8, state n=1 host and 1 graded variant, and reframe the result as 'detector evasion': the scar is removed, and refusal recovers only a fraction of the gap. That is the forgery-relevant claim.
- [MAJOR MUST-FIX] (clarity) Structure and results-first requirements are unmet. There is no abstract, and 'Table 1' is cited but only [FIGURE:fig_race_table] exists. There is no main results table comparing metric classes against the incumbents (AMS in-sample and cross-fitted, HRCI, N-GLARE/GFS status) and black-box baselines. Section 5.5 bundles five unrelated results; several (cross-fitting on noise, float32 Gram, the BSA threshold) are method/validation content that belongs in Section 3 or an appendix. There are only five figure markers, and none covers the prompt-budget crossover, the poles analysis, or the lexical floor.
  Action: Add an abstract with numbers. Add Table 1 (main race) and Table 2 (forgery ladder: rung x {blind tier, family-aware tier, metric movement, D2 change}). Move the noise and float32 validations into Section 3. Add a prompt-budget figure and a poles figure. Make the ROSI figure a dose-response line of harmful refusal, false refusal and D2 with CIs.
- [MAJOR MUST-FIX] (rigor) The ROSI replication claim and the dependence of the whole behavioural pipeline on a readout that failed its bar. The Qwen3-0.6B 'replication' has dD2 -0.081 with CI [-0.176, +0.017], which includes zero, and alpha* was extrapolated rather than recovered. Behavioural cells use 20-token greedy continuations on 2 hosts. Separately, every across-item and coupling metric in the race depends on a refusal readout whose best candidate has minimum per-checkpoint AUROC 0.544 (the bar was 0.80). Coupling metrics are therefore evaluated through a near-chance readout on some checkpoints, so their failure may reflect the readout rather than the construct.
  Action: Label the Qwen3 result 'direction-consistent, not significant'. State the 20-token budget and justify it with a check that 20 tokens suffices for the stance judge, e.g. agreement with 128-token grades on a subset. In Section 5.1, add a sensitivity analysis recomputing the across-item metrics with judged refusal as an oracle readout on the 15 judged checkpoints. This separates 'the coupling construct fails' from 'the readout fails'.
- [MAJOR MUST-FIX] (novelty) Reference integrity problems. Several author attributions are wrong for papers I can identify: ROSI 2508.20766 is Abu Shairah et al., not 'Y. Wang'; 'LLMs Encode Harmfulness and Refusal Separately' is Zhao et al., not 'D. Li'; The Leaderboard Illusion is Singh et al.; Safetywashing is R. Ren et al.; 'Black-Box Access is Insufficient' is S. Casper et al.; Watch the Weights is Zhong & Raghunathan. The steering-vector OOD paper (Tan et al., NeurIPS 2024) is arXiv 2407.12404, not 2406.09289. Years conflict with arXiv IDs ([5] 2604.x listed 2025; [6], [11], [12], [23] 26xx listed 2025). [6] is quoted as 0.003 in the Introduction and 0.015 in Related Work. [16] is a GitHub tool whose 0.35 threshold the paper refutes, so the exact repo and version should be pinned.
  Action: Regenerate the bibliography from Semantic Scholar/arXiv by ID and fix authors and years. Reconcile the [6] number. Give the model-scanner commit hash. Tie every specific numeric claim about a cited paper (AMS rho -0.423, RAS 210x, N-GLARE 7000 cases) to a page or table.
- [MINOR] (methodology) The card-regex result is partly tautological. Abliterated repos self-label ('abliterated' in the name or card), and the de-biased regex falls to ~0.10. The AUROC 1.000 therefore measures label leakage in the panel construction, since abliterated checkpoints were selected via names and tags, rather than a metric.
  Action: Say explicitly that panel membership was chosen by name/tag, so the card regex is an upper bound on leakage. Make it a baseline row, not a race entrant, and report the de-biased twin in the main table.
- [MINOR] (rigor) The judge-reliability statements are inconsistent. Section 3.3 says kappa 0.456->0.585 from reframing, and 0.785 (n=476) on the final instrument. Exp1 reports gpt-5-mini vs gemini kappa 0.749. The 3/6 -> 6/6 controlled test is only 6 items. The claim that grader-side refusal is 'across three major hosted judges' needs per-judge rates.
  Action: Add a small table: per judge x framing, degenerate-minimum rate, accuracy on a larger known-compliant set (>=50 items), and pairwise kappa with n. State which kappa belongs to which artifact.
- [MINOR] (clarity) The F3/F4 rungs are untrained merged-LoRA-shaped deltas, so 'genuine light safety fine-tuning' in Section 4.3 is misleading. The '147 of 147 additional cells, adding 27.9%' denominator is unclear. The B3 'within-family AUROC 1.000 on Qwen3/TinyLlama' claim could not be traced.
  Action: Rename F3/F4 'LoRA-shaped weight deltas (untrained)' in Section 4.3. Give the cell denominators per rung in the ladder table. Cite the artifact field for the within-family 1.000.
</reviewer_feedback>

<pipeline_steps>
STEP 2 — STRATEGY: The pipeline's strategy generator (gen_strat) read the reviewer feedback
and designed a new research strategy to address the critiques.

STEP 3 — PLANNING: The planner (gen_plan) turned the strategy into concrete artifact plans —
specific experiments, datasets, or research tasks to execute.

STEP 4 — EXECUTION: The executor (gen_art) ran those plans and produced the new artifacts
shown in <new_artifacts_this_iteration> below.
</pipeline_steps>

<results_status>
This iteration executed at least one EXPERIMENT/EVALUATION/PROOF with real output: gen_art_evaluation_1.
You may cite their concrete findings.
</results_status>

<hypothesis>
STEP 5 — HYPOTHESIS UPDATE: The hypothesis was revised based on evidence from previous iterations.

kind: hypothesis
title: Which internal reads track real safety
hypothesis: |-
  THE CLAIM IN ONE SENTENCE. For a stranger's checkpoint with no parent and no reference, SOME
  single-model internal quantity, read from hidden states or weights on at most 16 prompts, predicts
  that model's MEASURED two-sided safety (it refuses harmful requests AND does not refuse harmless
  look-alikes) across architecture families better than the first-token logit gap does. Which
  quantity is not yet known, and iteration 2 showed that it is none of the 50 static reads already
  registered. Iteration 3 is therefore an explicit SCREEN over a named population of 16 candidates
  in 8 families that can disagree with each other, with a selection rule fixed before any scoring and
  a held-out confirmation the screen never touches. The leading conjecture inside the screen, stated
  so it can lose: what tracks safety is not a LEVEL the model holds but a CAUSAL GAIN, how strongly
  the model's own harm representation drives its own refusal computation, measured by intervention
  or by a weight path, not by a correlation passed through a per-item refusal readout.

  WHAT ITERATION 2 ACTUALLY PRODUCED (executed numbers only).
  (1) THE RACE. 33 of 34 checkpoints, 8 families, registry hash intact. Only 3 of 50 metrics beat
  their own label-permutation null under leave-one-lineage-out. Presentation invariance scored 1.000
  (null p95 0.775). The model-card regex scored 0.917 (0.788), but it reads nothing of the model, its
  name-free twin falls to 0.455, and it fails the blanket-refuser pole rule. The alarming-item logit
  gap scored 0.800 (0.700) and also fails the pole rule. In total 19 metrics fail the pole rule,
  including every black-box refusal meter. The one metric that passes null and poles, presentation
  invariance, runs AGAINST the two-sided target (Spearman -0.71, n=13 checkpoints, and -0.40 at
  lineage level, n=5). The requester's invariant, at least 3 shipped metrics that read hidden states
  or weights, was reported as NOT satisfiable and was not relaxed.
  (2) THE READOUT. No refusal readout met its bar of AUROC >= 0.80 on every checkpoint against judged
  refusal. The chosen cross-fitted probe has minimum 0.544, the logit gap 0.437 with 3 of 15
  checkpoints below chance, and even a graded 24-token greedy continuation only 0.547. Every
  across-item coupling metric was computed THROUGH that readout, so the coupling construct of the
  previous hypothesis (R1) was scored through a near-chance instrument on the very checkpoints that
  matter, the abliterated ones (base rates 0.11 to 0.20).
  (3) THE DIRECTIONS. Cross-fitted harm-content directions clear the within-span random-direction
  null on 16 of 17 checkpoints at the last prompt token inside two families, but on 9 of 17 at the
  first generated token and on 9 of 20 on the 8-family panel. The whitened refit is lower (0.759 vs
  0.835), so part of the read is residual anisotropy.
  (4) THE PROMPT BUDGET (15 checkpoints, 3 families). Black-box reads lead on rank correlation at
  every k (0.282 to 0.337 against 0.021 to 0.210). On held-out balanced accuracy they lead up to
  k=32 and trail at k=64 (0.571 vs 0.592). The activation metamodel reached held-out 0.5 against
  tuned 1.0 at n=10 checkpoints with 288 features, which is a power failure, not a verdict.
  (5) THE WEIGHTS. Verdict EDIT_NOT_RISK. A parent-free recovered edit strength separates edited
  from honest checkpoints (AUROC 0.84, and 0.95 for tool outputs) but does not grade harm: Spearman
  with judged compliance 0.26, CI [-0.65, 0.86], n=14, minimum detectable 0.56. Even the true
  parent-based strength gives 0.03 (n=12). A replication on stored generations gives 0.85 [0.56,
  0.95] at n=20 but mixes edit types, and 0.65 [-0.26, 0.95] on projection edits alone (n=10). So a
  graded weight signal is not established and not excluded. Inside the edited arm the best predictor
  was the logit-only first-token gap (-0.62, p=0.02). The parent-free detection axis was WITHDRAWN:
  best AUROC 0.738 against a 0.80 bar, the published 0.35 threshold flags 97% of honest checkpoints,
  and a zero-prompt spectral repair removes the weight signature (0.012 to 0.82) while harmful
  refusal recovers only 0.125 to 0.208 against the parent's 0.438.
  (6) STEP 1, the Qwen3-4B four-way. The instruct-to-SafeRL and instruct-to-abliterated differences
  share part of a subspace (mean first principal angle 31.1 degrees) but do NOT share a direction:
  mean-difference cosine -0.09, maximum |cos| 0.20 against a null p95 of 0.41, with a powered
  positive control (0.92 > 0.72). Safety tuning and refusal removal are not opposite moves along one
  axis.
  (7) TWO FINISHED POSITIVE RESULTS, kept exactly as measured. Grader-side refusal: the StrongREJECT
  framing makes hosted judges return the minimum grade on 40.5% of replies and 65.9% of harmful-item
  replies, and a stance framing restores agreement (kappa 0.749). The ROSI rank-one safety edit
  REVERSES on a two-sided target on its own Table-1 model: paired change -0.151 [-0.233, -0.065],
  harmful refusal 0.859 to 0.984 while benign-twin false refusal goes 0.375 to 0.750. On Qwen3-0.6B
  the change is direction-consistent but its CI includes zero (-0.081 [-0.176, +0.017]).

  WHY THIS IS WEAK_OR_NULL, AND WHY THE ANSWER IS TO WIDEN. The tests ran and gave nothing to build
  a metric on. Both headline claims of the previous hypothesis failed their own bars: across-item
  metrics did not beat level metrics on held-out lineages, and forgery detection without a reference
  fell under its bar. Shrinking the claim to 'a model-card regex wins' or 'weights read the edit'
  would answer a question the requester did not ask. Three structural causes explain the null, and
  each one is a direction to widen in, not a reason to narrow.
    CAUSE A, THE OUTCOME. The race was scored on a class label carried by only 3 pair-families, and
    the graded two-sided target exists for 13 to 15 checkpoints and 5 to 6 lineages. At n=15 a
    Spearman CI excludes zero only above about 0.51. Nothing short of a very large effect could win.
    CAUSE B, THE INSTRUMENT. Every coupling metric depended on a per-item refusal readout that is
    near chance where it matters. The construct was never cleanly measured.
    CAUSE C, THE POPULATION. The 50 metrics fall in 3 functional classes and are all STATIC reads at
    one site, the last prompt token at a fixed depth. They could not disagree in kind. Step 1 now
    says why a static one-axis read cannot be two-sided: the safety-tuned and refusal-removed
    models do not lie on one axis.

  THE WIDEN: BACK TO THE ORIGINAL ASK. The ask is a cheap single-model safety evaluation from weights
  or activations on a few prompts, preceded by an open-ended look at how Qwen3-4B Base, instruct,
  SafeRL and abliterated differ inside. Sixteen candidates were weighed. All are parent-free, need at
  most 16 prompts, run on sub-4.5B models in bf16 with transformers, and are designed from the
  Step-1 anchor, which is already harvested.
    FAMILY I, CAUSAL GAIN (single-model interventions).
      C1 Harm-to-refusal gain: nudge the model's own cross-fitted harm coordinate at mid depth and
         read the change in its late refusal-axis projection by finite difference. A blanket refuser
         has a high level and near-zero gain, so it loses by construction.
      C2 Self-ablation sensitivity: remove the model's own cross-fitted direction in a layer band
         and read the drop in refusal margin on harmful items and on benign twins, against an
         anisotropy-matched random direction.
      C3 Twin patching flip depth: patch the benign twin's residual into the harmful run in six
         coarse depth bands; read where and how sharply the refusal margin flips.
    FAMILY II, WEIGHT PATHS CONDITIONED ON THE MODEL'S OWN DIRECTIONS (weights plus 16 prompts).
      C4 Writer capacity: how much each o_proj and down_proj can write along the model's own
         refusal axis, as a z-score against random directions from that layer's output span.
      C5 Harm-to-refusal path gain: the bilinear gain from the harm direction into the refusal axis
         through each MLP and attention output path, summed over depth.
    FAMILY III, COMPONENT AND ROUTING STRUCTURE.
      C6 Concentration of direct logit attribution to refusal tokens across heads and MLPs (top-k
         share and depth centroid).
      C7 Late-layer attention mass from the decision position onto the tokens that differ between a
         harmful item and its twin.
      C8 Input-gradient share of the refusal margin on those same differing tokens.
      C9 Template-site share: how much of the refusal drive sits at chat-template positions rather
         than content positions.
    FAMILY IV, DEPTH AND SITE PROFILE.
      C10 Area between the depth curve of harm decodability and the depth curve of refusal drive.
      C11 Refusal-commitment trajectory over the first 8 generated tokens (the response site).
    FAMILY V, TWO-SIDED GEOMETRY.
      C12 Twin discrimination: separation of harmful items from their matched benign twins along
          the refusal axis, relative to separation from plain benign items.
      C13 Presentation invariance with its sign FIXED IN ADVANCE from iteration 2 (negative). It
          must keep that sign at checkpoint and at lineage level or it is dead.
    FAMILY VI, LEARNED. C14 A ridge metamodel on a compact profile of at most 24 depth-by-site
      features predicting the graded target under leave-one-family-out, with an identity control.
    FAMILY VII, LABEL-FREE GEOMETRY. C15 Late-layer effective rank and residual dispersion over the
      16 prompts (low prior; the comparator rows of iteration 2 were weak).
    FAMILY VIII, STEERING DOSE. C16 Self-steering dose-response slope. Prior art exists, so this row
      is a comparator and cannot be shipped as new.
  INCUMBENT BARS, printed as rows and never as candidates: the first-token logit gap and refusal
  token mass (the only 2 logit-only baselines allowed in the shipped set), the card regex and its
  name-free twin, family label alone, log size alone, AMS in its published and cross-fitted forms,
  HRCI, N-GLARE JSS, and the parent-free weight reads (recovered edit strength, BOTGAP).

  THE OUTCOME, CHANGED. Candidates are scored against a GRADED two-sided score per checkpoint, built
  so a model that refuses everything sits at 0.5 and loses, judged with the stance-framed instrument
  and never with Qwen3Guard on SafeRL. The panel must grow from 15 to at least 30 graded checkpoints
  with activations across at least 6 families, including real blanket refusers and standalone models
  with no sibling. It starts from the 20 activation harvests and the stored generations already on
  disk. Below n=24 no correlation is reported as a verdict, only as a scatter. Published numbers
  (HELM safety with its over-refusal scenario, AIR-Bench, model cards) and archived GSM8K and MMLU
  enter as a second outcome column and as a capability partial. The run has already measured that
  only 2 sub-4B models carry published safety numbers and that identical weights differ by up to
  6.7x the across-model variance under different guardians, so the external limb is reported with
  its n and is not the selection criterion.

  SELECTION RULE, FIXED BEFORE ANY SCORING. A candidate SURVIVES the screen only if all six hold.
  (S1) Under leave-one-family-out (leave-one-lineage-out where a family has no pair), its |Spearman|
  with the graded score exceeds the first-token logit gap's by at least 0.15 with a family-cluster
  bootstrap CI on the difference that excludes zero, OR its partial correlation given the logit gap
  and log size has a CI excluding zero. (S2) It beats its own label-permutation null p95 and, for
  direction-based reads, the within-span random-direction null. (S3) Its orientation is declared in
  advance, and both a real blanket refuser and the wrapped always-refuse and never-refuse poles score
  WORSE than the honest instruct model. (S4) Its sign agrees between checkpoint-level and
  family-level aggregation. (S5) It holds at k <= 16 prompts and under two minutes per 4B model on
  one 16 GB GPU. (S6) It beats the family-only and size-only rows. As a control on Cause B, every
  readout-dependent row is also printed with judged refusal as an oracle readout, which separates 'the
  construct fails' from 'the readout fails'. Rival outcomes are informative. If Families I or II
  win, coupling was real and the iteration-2 null was the instrument. If Family III wins, structure
  rather than gain carries safety. If only the bars win, the evidence points to a bound: at 16
  prompts nothing internal beats the logit gap, with its minimum detectable effect stated. That
  bound would be written up only on the final iteration.

  HELD-OUT CONFIRMATION, USED ONCE. The two sealed families that no iteration has touched (Granite
  and StableLM2), a sealed
  item pool from which a fresh set of 16 prompts is drawn, and checkpoints harvested only after the
  screen is frozen. A screen winner is a CANDIDATE, not a finding. If confirmation fails, that
  candidate is dead, and there is no re-screening and no subgroup search on the confirmation data.
  The shipped set is up to the 3 best confirmed internal metrics plus at most 2 logit-only
  baselines. If fewer than 3 internal metrics confirm, the invariant is reported as unmet.

  WHAT HAPPENS TO THE FORGERY AXIS. It stops being a headline and becomes a ROBUSTNESS COLUMN for
  survivors only. The 183 stored weight-ladder cells and 11 graded behavioural cells can be re-scored
  without re-running an edit. The previous hypothesis's rank-zero cancellation claim becomes one
  testable prediction: a causal-gain metric should not move under a constant residual offset that
  moves every level metric.

  BONUS, CONDITIONAL. For any confirmed survivor: which layers and components carry it on the
  Qwen3-4B anchor, what breaks it, reported as a distribution over seeds and prompt draws rather
  than as one circuit. C14 is the requested metamodel and competes under the same rule.

  REPORTING CORRECTIONS CARRIED FORWARD FROM REVIEW. Every headline sentence must match its full
  table: the card regex is 'the best metric that reads nothing', not the best metric; the prompt
  budget is reported on both scales; the 0.85 replication and its edit-type confound sit beside the
  n=14 null; all three direction-null counts (16/17, 9/17, 9/20) appear together; the repair result
  quotes refusal, not compliance; the Qwen3 ROSI result is 'direction-consistent, not significant';
  every number is tagged with its panel; Step 1, Step 5, the metamodel and the external limb are
  reported even where negative; the bibliography is regenerated by identifier.
motivation: |-
  Anyone who downloads a model from Hugging Face is trusting an artifact uploaded by a stranger. There
  are well over a million of them, almost none carry safety numbers, and running a benchmark on each is
  out of the question. So the field is building cheap proxies: read a few weights, run a handful of
  prompts, get an estimate in seconds. Every one of them is selected the same way - correlate it with
  benchmark scores across honest checkpoints and keep the winner.

  Two things are wrong with that, and this study fixes one and measures the other.

  The first is that nobody has checked WHICH cheap readouts survive being moved to a lineage they were
  not tuned on. That is the request's own question and it has a mechanical answer waiting: published
  work shows harmful intent is linearly decodable at around 0.98 AUROC in essentially every checkpoint,
  including abliterated ones, which means a readout of what the model KNOWS is near-constant across
  alignment variants and cannot possibly separate them. What varies is whether refusal uses the
  knowledge. That is a statement about a relationship across items, not about a level, and it predicts
  in advance which half of any 50-metric battery can work. Testing it held-out is the cheap, decisive
  version of the request, and it is worth doing on its own.

  The second is that the selection rule assumes honesty. The cheapest proxies read the most superficial
  thing a model does, and the most superficial thing is the cheapest to change. A chat template is a
  text file inside the repository. A system prompt is thirty tokens. A rank-one addition to the
  residual-write matrices needs no training data and no gradient step - and it is not hypothetical, it
  is a published method its authors present as a cheap safety improvement, validated with a guard
  model's refusal rate and a benign-compliance check on ordinary prompts, never on the
  benign-but-alarming requests where pushing a model toward refusal actually does its damage. Whether
  that edit is a defence or a fake depends on a measurement nobody made.

  So the question is not which cheap metric correlates best. It is which cheap metric you could still
  believe if the person who uploaded the model wanted you to believe it. And the honest version of that
  has a second half: an edit that is cheap to apply may also be cheap to CATCH. A template preamble is a
  free text read. A shared direction written into every residual-write matrix is a subspace that recurs across
  layers, which one pass over the weights can see - and a public scanner already does exactly that, which is
  better for this argument than inventing our own detector would have been, because the screen an auditor
  faces should be one they can already download. A forgery is only worth worrying about if it is cheap AND
  invisible, and that pairing is the measurement nobody has made.

  There is a reason to expect a clean answer rather than a mess. Faking a metric and satisfying it
  honestly are not unrelated activities. To make a model refuse harmful requests and only those, a
  forger must give it something that tells harmful from harmless, which is the safety mechanism itself.
  The cheap edits stop short of that in a specific, algebraic way: a constant cannot condition on the
  item at all, and a rank-one edit can condition only through a single coordinate - which is exactly the
  structure that recurs across layers and can be read. So the cost of an undetectable forgery should
  converge on the cost of actually being safe, and the metrics that are cheap to fake are the ones
  asking for less than that. Forgery cost is then not a security curiosity bolted onto evaluation; it is
  a measurement of how much real safety each metric is actually demanding, which is the thing nobody
  currently knows about any of them.

  Tamper-resistance work is the published mirror image: it measures what it costs to REMOVE real safety
  from an open-weight model. We measure what it costs to FAKE the appearance of it. The two bound a
  safety metric from opposite sides and only one has been measured.

  Finally, this settles on the right axis a question the field keeps answering wrongly. Careful attempts
  to show that reading a model's internals beats reading its outputs have failed: a plain refusal rate
  predicts benchmark safety about as well as anything measured inside, and the model card does better
  still. The conclusion drawn so far is that looking inside buys nothing. The alternative is that
  looking inside has only ever been judged on the one axis where behaviour is unbeatable by
  construction - predicting behaviour on honest models - instead of the two axes where behaviour is not
  a reliable witness: a lineage nobody tuned on, and a checkpoint shipped by someone with a reason to
  shape how it behaves.
assumptions:
- |-
  A shared-direction weight edit leaves an aligned subspace across the layers it touches, and the degree
  of that alignment is large enough, and honest cross-layer alignment small enough, to separate them with no
  parent. The spectrum-invariance half is no longer an assumption: the statistic is a subspace overlap, so it
  discards singular values, and in simulation its honest value moved only from 0.168 to 0.177 between a
  Gaussian and a heavy-tailed weight spectrum where the statistic it replaces swung from 0.821 to 0.119. What
  remains empirical is the honest baseline on real trained weights, which real networks could violate by
  carrying genuinely shared directions of their own, and the alignment REAL abliteration tools actually
  produce. Both are measured in Stage 0 before anything is built on them. The card census already narrows the
  risk: only about 5 percent of real abliterated checkpoints state a per-layer direction, and the dominant
  automated tool searches over direction scope rather than defaulting to per-layer, with 8 of 10 published
  parameter tables using a global direction. If real honest checkpoints turn out to have high cross-layer
  alignment of their own, the sharing statistic is withdrawn and the local rank-deficiency statistic carries
  the full-strength cases alone.
- |-
  The two training-free text rungs are genuinely cheap and genuinely fake: a repository-file edit and a
  constant refusal offset must be implementable with no training data and no gradient steps and must
  leave graded harmful output essentially unchanged. The rank-one rung is explicitly NOT assumed to be a
  fake - it is a published method presented as a defence, so its label is an OUTCOME of this study, and
  if it survives a ground truth that penalises a blanket refuser we relabel it a cheap defence and report
  a shorter ladder. Symmetrically, the constant rung is not assumed to be undetectable: whether it can be
  built without adding a tensor the declared architecture lacks is a measured result, and if it cannot,
  the undetectable-cost column may collapse to a constant, which is itself a clean finding.
- |-
  Harmful intent is close to linearly decodable from the residual stream of essentially every checkpoint
  when the direction is CROSS-FITTED, not merely in-sample. Published work puts this near 0.98 AUROC
  across four families and three alignment variants including abliterated ones, so the assumption is well
  supported - but it cuts both ways, since it also means a harm-knowledge readout is near-constant across
  variants and cannot be the discriminator. If cross-fitted decoding sits at chance at our item budget for
  some family, the item count at which the signal lifts is itself the finding: a floor on how cheap an
  internal safety metric can be.
- |-
  Enough honest checkpoints exist to support the panels. At least six ungated lineages at or below about
  four billion parameters with readable safetensors and a usable chat template for the ground-truth panel;
  at least 120 ungated instruct checkpoints for the threshold and manifold panel, whose metric vectors need
  no ground truth at all; and at least 30 real abliterated sub-4B checkpoints for the recipe census and the
  transfer panel. A Hub query for safetensors instruct text-generation checkpoints returns over a thousand
  results with about four percent gated, and a search for abliterated returns over a thousand hits with
  roughly 150 under 4B, so all three are reachable.
- |-
  The external correlation limb is carried by MODEL SIZE STRATIFICATION, not by finding more small models,
  because we checked and the small ones are not there: across the three public safety leaderboards with
  downloadable per-model tables, the sub-4B open-weight population is 3, 1 and 1 respectively, and a fourth
  publishes no per-model table. The assumption the limb rests on is therefore that the two weight-only
  readouts, needing only a safetensors read on CPU, and the two activation readouts, being prefill-only, can
  be computed on the 7-8B-and-up open-weight models in those pools - roughly 25 to 40 after API-only entries
  are removed - within the machine's RAM and the run's transfer budget. Capability is not scarce at any size:
  the archived open leaderboard holds over ten thousand result files. If the large-model stratum proves
  unusable, the limb falls back to the six-to-eight sub-4B checkpoints plus in-house grading, with the subset
  size reported prominently and the scarcity itself reported as the ecosystem finding it is.
investigation_approach: |-
  STAGE 0 - PRECONDITION CHECKS, RUN FIRST, ABOUT THREE HOURS. Four cheap results decide the shape of
  everything after them and each is pre-committed.
    (i) THE RECIPE CENSUS. The card half of this is ALREADY DONE and its numbers are in H3 claim 3c: 37
    real abliterated Hub checkpoints read, 8.1 percent matching the recipe the previous statistic required,
    5.4 percent stating a per-layer direction, 56.8 percent stating no recipe at all. Stage 0 completes it
    from the WEIGHTS, which is where the 56.8 percent has to be resolved: for each census checkpoint recover
    every layer's suppressed direction as its bottom left singular vector, then measure the realised
    ablation strength, which layers were touched, and the mean pairwise cosine across layers. That cosine is
    the axis H3 grades the instrument on, so it is measured on real artifacts before anything is built on it.
    One census by-product is kept as a free positive control: the same author ships checkpoints fine-tuned to
    INCREASE refusal, which are a ready-made real-world blanket-refuser anchor for H5's poles.
    (ii) THE INSTRUMENT ON REAL WEIGHTS. Compute bottom- and top-subspace alignment and the local
    rank-deficiency ratio on every census checkpoint and on a first slice of the honest panel, plus on two
    edits we construct ourselves on a checkpoint we control - one rank-one injection at the published
    method's own alpha, one abliteration. The honest baseline is validated on real weights, not on
    simulation. The withdrawal path is finer-grained than before: if the sharing statistic fails, it is
    withdrawn for that rung and plain forgery cost is reported there; if the local statistic also fails on
    real full-strength abliterations, the whole detection axis is withdrawn and the study reverts to the
    plain cost ladder plus R1, which remains a complete deliverable.
    NOTE ON THE ANCHOR, found in the census and worth stating because it changes Stage 1's model list: the
    best-known abliterated Qwen3 checkpoints from one publisher now return 401 and are no longer openly
    downloadable, so the anchor lineage's abliterated member is taken from a still-open alternative produced
    by the automated tool, with the gated ones used only if access is granted.
    (iii) CROSS-FITTED TRANSFER on the anchor lineage: harm-direction decoding plain, wrapped, paraphrased
    and translated, so the audit draw's presentation pool is characterised before it is used.
    (iv) THE INVARIANCE NUMBER: apply the constant rung on an fp32 copy and measure how far each
    across-item metric moves against the 0.05 tolerance, and settle how F2a is built - carrier coordinate
    or explicit tensor - by measuring the realised across-item constancy of both.

  STAGE 1 - EXPLORE THE ANCHOR LINEAGE, the request's step 1. Load Qwen3-4B-Base, Qwen3-4B,
  Qwen3-4B-SafeRL and an abliterated Qwen3-4B in bf16 with transformers on the 16 GB GPU, weights and
  hidden states readable, no quantised inference. Instruct, SafeRL and abliterated share a byte-identical
  chat template and are compared directly; base is kept in a separate stratum with a plain renderer. Look
  at per-layer weight spectra and singular subspaces of the residual-write matrices, the cross-fitted
  harmful-versus-benign direction at every layer and its depth profile, where refusal first becomes
  decodable, first-token refusal logits, and the same readouts on benign-but-alarming twins. This stage
  supplies the coordinates the battery is built from.

  STAGE 2 - THE BATTERY AND ITS REGISTRY, the request's step 2. Exactly 50 metrics, each computed from ONE
  checkpoint with no parent. The registry is written as a NUMBERED APPENDIX before any measurement -
  metric name, exact computation, LEVEL or ACROSS-ITEM label, functional-form class id, and predicted rung,
  with per-class counts totalled at the bottom. That table is what makes H2 auditable and what fixes the
  class sizes the mixed model needs in advance, and the battery is composed so that the across-item class
  contains at least 15 genuinely distinct forms rather than 15 variants of one. Three groups: zero-prompt
  weight statistics including subspace alignment, per-layer spectral and energy profiles, and low-rank mass;
  cross-fitted activation statistics over a few dozen short forward passes, including coupling, decision
  spread, depth profiles and their movement from the prompt's last token to the first generated token; and
  exactly two black-box baselines. Two published reference-free incumbents are re-implemented from their
  descriptions and forged alongside our own rather than only classified; a third whose protocol may not be
  reproducible is classified from functional form and that difference is stated.

  STAGE 3 - THE WIDE SCREEN, the request's step 3, run on real checkpoints BEFORE any forgery is graded,
  and reported as headline result R1. Every metric on every reachable lineage where a safety-tuned or
  abliterated sibling exists, on pairs and triplets, and on standalone checkpoints where no sibling exists
  at all, because a metric for a stranger's model must return something sensible when there is nothing to
  compare to. For each metric, does it separate safety-tuned from ordinary instruct from abliterated.
  Whole lineages are held out from every choice of layer, threshold and coordinate. The held-out number is
  the headline with the tuned number printed beside it, and the LEVEL-versus-ACROSS-ITEM split predicted in
  Stage 2 is scored as a pre-registered prediction rather than observed after the fact.

  STAGE 4 - THE LADDER, six rungs, two detection tiers. F0 a repository-metadata edit, zero FLOPs. F1 an
  inference-time system prompt. F2a the CONSTANT rung, built as decided in Stage 0(iv). F2b the RANK-ONE
  rung - the published injection method, run both at its own published settings and as a metric-maximising
  adversary. F3 a small keyword-triggered refusal adapter. F4 genuine light safety fine-tuning, which buys
  real safety and caps the ladder. Every rung scored on three axes: does it move the metric past a threshold
  at a fixed honest-panel false-positive rate, does the Tier A reference-free screen catch it, does the
  Tier B reference-anchored screen catch it. The adversary is pre-registered at full strength: it knows the
  metric definitions, fits its direction on the same distribution the metric uses, and grid-searches band
  and coefficient to maximise the target metric subject to leaving graded compliance unchanged. It is also
  allowed to try to HIDE - per-layer directions at sub-unit strength - and where that succeeds we report the
  cost of hiding in the same units.

  STAGE 5 - GROUND TRUTH THAT PENALISES A BLANKET REFUSER, the request's step 4. Four columns. Graded
  harmful compliance on a StrongREJECT-style rubric. False refusal on benign-but-alarming twins. A
  distribution-shift column giving a retention ratio. And a capability column. Graders are named now because
  the choice moves every number: harmful-compliance grading uses the StrongREJECT rubric applied by a hosted
  non-Qwen judge, with a declared alternate, because the released fine-tuned grader is gated behind its
  base model; agreement is reported against a second, independent, ungated open grader run locally. No Qwen
  guard is used anywhere, and Qwen3Guard is excluded for SafeRL specifically as the request instructs.
  Prompt sets are fixed now: harmful items from StrongREJECT and the JailbreakBench behaviours, which ship
  100 harmful and 100 benign as a matched pair; benign-but-alarming twins from XSTest and the hard
  over-refusal subset of OR-Bench; and the presentation-condition pool for the secret draw comes free from a
  benchmark that ships 440 base prompts each in 20 linguistic mutations, so the audit can sample at audit
  time rather than from a published list.

  STAGE 6 - THE EXTERNAL LIMB, the request's step 5, rebuilt so it is a correlation rather than a stated
  impossibility - and rebuilt on VERIFIED counts, because we checked the leaderboards the previous version
  never looked at and the answer is more interesting than either the previous "about three" or a simple fix.
  Three strata, with the sizes measured this week.
    STRATUM 1, sub-4B with published SAFETY numbers, and this is the finding: it really is tiny, and the
    scarcity is the ecosystem result. The downloadable per-model table of one public safety leaderboard has
    34 models of which 3 are sub-4B, and it carries no over-refusal column at all. The large public safety
    evaluation suite has 87 models and 435 runs, but exactly ONE sub-4B open-weight entry. Its companion
    risk-taxonomy suite has 87 models and the same single sub-4B entry. A third widely cited safety
    benchmark publishes no downloadable per-model results table. Adding the four model-card checkpoints
    found earlier gives roughly six to eight sub-4B checkpoints with any published safety number - so the
    previous version's pessimism was closer to right than the suggestion that leaderboards would fix it,
    and we report that as a finding about the ecosystem rather than as an obstacle: the models a downloader
    is most likely to meet are exactly the ones with no published safety number, which is the entire reason
    a cheap metric is wanted. Full four-readout panel, on the GPU.
    STRATUM 2, WHERE THE ACTUAL CORRELATION LIVES, and the reason this limb is now executable. The large
    safety suite's 87 models carry published per-scenario scores including an over-refusal scenario - a
    PUBLISHED two-sided ground truth of exactly the shape this study argues for, which also removes any
    suggestion that the two-sided target is our invention. Those models are mostly 7B and above and do not
    fit the 16 GB card for generation, but they do not have to: the two weight-only readouts need a
    safetensors read and no GPU at all, and the two activation readouts are prefill-only and run on CPU with
    251 GB of RAM. The limb therefore runs on the open-weight subset of that pool, which Stage 0 enumerates
    and which we expect to be on the order of 25 to 40 checkpoints after removing API-only entries. The size
    stratum is stated explicitly, analysed separately, and its transfer cost budgeted, since 7-8B
    checkpoints are 15 GB each and are streamed rather than retained.
    STRATUM 3, capability, which is NOT scarce: the archived per-submission results of the retired open
    leaderboard hold 10,160 result files over 7,121 repositories, of which several hundred are sub-4B with
    MMLU and GSM8K. This replaces running the harness per checkpoint, which was the study's own declared
    slow step, and gives the safety-versus-capability scatter a real sample size. The harness is still run
    on the six ground-truth lineages so the anchor numbers are measured on identical settings.
    The ten best metrics are then correlated against these external numbers, in-house grading printed
    beside them, resampling unit and both aggregation units reported, and a metric that works only inside
    one architecture family reported as a negative result in those words.

  STAGE 7 - COST AND THE INVERSION. For each metric, the cheapest effective rung and the cheapest
  effective-and-undetectable rung under BOTH access tiers, with the full curve over false-positive rates,
  thresholds from the large honest panel, and bootstrap intervals on unstable assignments. Then the mixed
  model of H2, with within- and between-class components, per-class detectable |rho| published beside each
  estimate, and a random-drop sensitivity analysis.

  STAGE 8 - THE AUDIT, ITS TRANSFER, AND THE REQUEST'S BONUSES. Fit the off-manifold residual on the honest
  panel with family-centring and whole families held out, reporting accuracy as a function of coordinate
  count; the inverted outcome, that it is a family detector, is pre-registered as a result. Then the
  payoff: on at least 25 real un-forged Hub checkpoints nobody in this study edited, correlate the shipped
  readouts with the measured retention ratio in a paired comparison against the black-box baseline at a
  matched prompt budget. Then the request's bonus - for whichever metric survives highest, which layers and
  components carry it, against a random-direction null matched for anisotropy, and what breaks it, closing
  with the cheapest forgery that defeats it given the mechanism. Then the second bonus - a small metamodel
  on activations as a rival to the formulas, with whole families held out and its advantage ablated against
  a lineage-identity probe on the same features, because a metamodel that reads lineage is not reading
  safety.

  FEASIBILITY, WITH THE PANEL COSTED AND PLACED IN THE SHRINK ORDER. Every ground-truth panel model is under
  about four billion parameters and ungated, so it loads in bf16 on a 16 GB card with weights and hidden
  states readable. THE HONEST PANEL IS THE LARGEST WALL-CLOCK ITEM AND IS NOW SIZED: per checkpoint it is a
  download of roughly two to eight gigabytes, a load, a weight read with a few hundred small singular value
  decompositions, and a few dozen short prefill passes - on the order of two to four minutes, so 120
  checkpoints is roughly six to eight hours and a few hundred gigabytes of transfer, measured rather than
  estimated in Stage 0 and streamed so disk never holds more than a few checkpoints at once. N=120 is a
  FLOOR, not a range. Its weight-only coordinates need no GPU, which is what lets it run beside the GPU work
  and what lets Stratum 2 reach the larger models. In the shrink order it sits ABOVE the ladder's training
  rungs and above the metamodel: the argument survives a missing rung, it does not survive thresholds
  estimated from six lineages.
  Generation is needed only for grading. The powered equivalence arm is sized from the margin first: the
  graded compliance score is continuous with an expected item-level standard deviation near 0.3, so a
  five-point margin at eighty percent power needs about 250 items per arm. Three lineages run powered at 250
  harmful and 250 benign-but-alarming items across the honest checkpoint and six rungs, which is 10,500
  completions; three more run at 120 items per arm for estimation with confidence intervals rather than
  equivalence testing, 5,040; the payoff panel is 25 checkpoints under four presentation conditions at 60
  harmful items, 6,000. About 21,500 short completions, a few GPU-hours spread across artifacts. Grading is
  about 10.8 million input and 2.2 million output tokens, roughly $2.90 at the named judge's rates, tracked
  per call as it accrues, comfortably inside the ten dollar ceiling with room for a second pass. The forgery
  ladder itself costs almost nothing: two rungs are text, two are matrix operations of seconds, and only the
  two training rungs use gradients, at low rank for about a hundred steps.
success_criteria: |-
  CONFIRMED if the following hold with whole families held out.

  R1, THE REQUEST'S OWN TABLE AS A RESULT. Every one of the 50 metrics gets a held-out three-way separation
  score - safety-tuned against ordinary instruct against abliterated - with the tuned score printed beside
  it. The pre-registered claim is the LEVEL-versus-ACROSS-ITEM split: across-item metrics hold up on lineages
  they were not tuned on and level metrics do not, with the gap between held-out and tuned performance
  significantly larger for the level class. A failure here is equally reportable and equally useful: if level
  metrics transfer just as well, the mechanism argument from flat harm-knowledge is wrong and we say so.
  Reported alongside: the ten best metrics correlated against EXTERNAL published safety numbers across the
  three strata, with the stratum sizes stated, the resampling unit and both aggregation units named, and any
  metric that works only inside one architecture family called a negative result in those words. The
  correlation must be reported with a confidence interval on the large-model stratum, where n is on the
  order of 25 to 40, and reported as a scatter with n printed rather than as a coefficient on the sub-4B
  stratum, where n is six to eight and a coefficient would be theatre. The sub-4B scarcity itself is a
  scored finding: we state how many sub-4B open checkpoints carry any published safety number at all across
  every public leaderboard we could download, which is the measurement that justifies the whole request.

  H1, COST IS REAL, LOW, AND ACCESS-AWARE. At least three metrics the literature currently proposes as cheap
  safety readouts, including the logit-gap margin and a black-box refusal rate, are pushed past a threshold
  set at a fixed false-positive rate by a training-free rung on at least four of six honest checkpoints, while
  the two-sided ground truth does not improve by more than the powered margin. The split is predicted in
  advance: readouts from text or logits fall to the two rungs that cost nothing, while weight statistics,
  which a template edit cannot touch, fall to the constant rung. Cost is filed in seconds, training FLOPs and
  labelled examples, as a curve over false-positive rates, with bootstrap intervals, in its continuous form,
  and separately under Tier A and Tier B. We predict the exchange rate spans at least an order of magnitude
  across the battery; if every metric yields at the same setting, the continuous axis adds nothing and we say
  so. THE TIER GAP IS ITS OWN REPORTED NUMBER: how many rungs move from detectable to undetectable when the
  auditor loses the family default.

  H2, THE INVERSION AS A DECOMPOSITION. The mixed model returns a negative association between honest-panel
  accuracy and undetectable forgery cost, with the BETWEEN-class component reported with a confidence
  interval as the primary estimate and the WITHIN-class component reported beside it for every class of size
  at least ten, each with its detectable |rho| printed. "The inversion is entirely a composition effect" is
  an acceptable and informative outcome, stated in those words. A clearly POSITIVE association refutes H2 and
  is worth reporting, because it would mean the field's existing selection rule is accidentally selecting for
  robustness too.

  H3, THE EDIT-RANK LAW. (a) Exact invariance holds for linear reads at the injection layer, to numerical
  precision, in fp32 before any behavioural work. (b) Metrics read downstream of a normalisation move by less
  than 0.05 correlation units under the constant rung, with the measured deviation reported. (c) The rank-one
  rung moves across-item coupling where the constant rung does not, and abliteration, being item-dependent,
  moves levels and LOWERS coupling - filed in advance and scored for free against real abliterated
  checkpoints. (d) THE INSTRUMENT - adopted from a public scanner, not claimed, and judged on the
  calibration it has never had - with thresholds pre-registered from the simulation already run rather
  than from a hope. On real checkpoints, windowed bottom-subspace alignment must separate edited from honest
  with held-out-family AUROC of at least 0.9 at zero prompts and no parent, using a threshold fixed in
  advance at 0.35 - roughly twice the simulated honest value of 0.177, and below the 0.358 the statistic
  reaches at the weakest correlated recipe simulated. It must still separate at an ablation weight of 0.7
  and on a half-stack band, which is precisely where the old raw-Gram statistic sat inside honest range. Its
  behaviour is reported as a CURVE in the measured cross-layer cosine, with the census locating real
  checkpoints on that curve. The local rank-deficiency ratio must separate full-strength projections
  regardless of sharing, against a bf16-realistic separator of 0.1 rather than an exact algebraic zero,
  since bf16 rounding lifts a projected matrix's ratio to about 0.010 against an honest 0.997. The
  per-layer-random arm stays as the negative control and is EXPECTED to be at chance for the sharing
  statistic; that is the definitional boundary and is reported as such, not as a failure. The injection half
  is pre-registered as the weaker one on measured grounds: fixed top-1 alignment detects a shared injection
  on a Gaussian stack but not on a heavy-tailed one at the same magnitude, so the statistic is swept over
  spectral rank bands and graded at the published method's own alpha, and if it fails there the detection
  axis is withdrawn for that rung.
  If the sharing half fails on real checkpoints, the detection axis is withdrawn for that rung and plain
  forgery cost is reported there. If the local half also fails, THE WHOLE DETECTION AXIS IS WITHDRAWN, the
  headline quantity reverts to plain forgery cost, and the paper's claim becomes R1 plus the plain ladder
  plus a reportable negative about parent-free weight auditing - which, given a published per-layer
  parent-free attempt already reported inconsistent success, is a finding rather than a hole. A third
  outcome is live and would be the most useful of all: that the recovered RECIPE - direction sharing,
  realised strength, layer band - predicts measured harmful compliance, which would make the detection
  column a graded safety read rather than a binary tamper flag.

  H4, CROSS-FITTING IS NOT DECORATION. Every fitted-direction metric is reported cross-fitted with a
  per-checkpoint label-permutation null and the in-sample version beside it. We predict the in-sample version
  reads near ceiling on every checkpoint including ones with no safety training, carrying almost no
  between-model variance, while the cross-fitted version varies. If the cross-fitted version sits at its null
  on every model, no usable internal harm estimate exists at that item budget, the request's few-prompt
  constraint and its read-the-internals constraint are in genuine tension, and the item count at which the
  signal lifts is the finding - a floor, reported as a number.

  H5, THE DELIVERABLE BEHAVES AT THE POLES. Synthetic always-refuse and never-refuse wrappers both score low,
  with decision spread reported in logits beside the ratio and a pre-registered variance floor below which
  the ratio is declared undefined rather than reported as a small number. A metric that scores a blanket
  refuser well is rejected regardless of its correlation.

  H6, THE HEADLINE EXPERIMENT. The published rank-one injection method, run unmodified at its own settings,
  is graded against the two-sided ground truth; the pre-registered claim is that its two-sided discrimination
  score does not improve, i.e. the two-sided target REVERSES the verdict its own evaluation reached. The
  defence label is applied if it survives. The free second prediction: top-subspace alignment flags it from
  the weights alone with zero prompts and no parent, which would make a published safety edit both cheap to
  apply and trivially visible - the whole thesis in one example.

  H7, THE TRANSFER AND THE MANIFOLD. On at least 25 real un-forged Hub checkpoints the shipped discriminators
  correlate with the measured retention ratio at rho of at least 0.5 with a confidence interval excluding
  zero, and beat the black-box baseline at a matched prompt budget in a paired test. The off-manifold
  residual separates edited from honest checkpoints with held-out-family accuracy above the best single
  metric's, or the inverted outcome - that it is a manifold of family identity - is reported as the result.

  DISCONFIRMED, and each way is reportable. If every metric including the conditional ones falls at the free
  rungs and the Tier A screen cannot catch them, cheap safety metrics for untrusted checkpoints are refuted
  outright and the ladder plus that result is the deliverable. If no cheap forgery moves any metric, cheap
  metrics are already tamper-resistant and the honest-panel selection rule was fine. If every training-free
  rung turns out to be free to catch, the undetectable-cost column is near-constant, H2 has nothing to rank,
  and the finding is the clean one: the only undetectable forgery is training, which is what being safe
  costs. If the audit separates edited from honest but the transfer limb fails, the residual is a tamper
  detector and not a safety metric, which must be said plainly.

  PRE-EMPTIVE CONTROLS, without which none of this counts. A random-direction null matched for anisotropy.
  Whole-family holdout for every threshold and every fitted manifold. No metric is ever evaluated on a
  checkpoint used to choose its layer or its threshold. The abliterated arm is a known-unsafe anchor, not a
  label to be predicted, and any metric that separates it trivially because abliteration is a rank-one edit is
  flagged as reading the EDIT rather than the RISK - which is exactly what the scar does, and it is reported
  in that column and never as a safety score. Every "beats the black-box baseline" claim is a paired test at a
  matched prompt budget.

  AND ONE STANDING RULE. If any metric here, including the one we ship, works only inside a single
  architecture family, that is reported as a negative result in those words and not softened into a scope
  condition. Held-out-family performance is the number that counts, the within-family number is printed
  beside it, and if the family label alone predicts the ground truth as well as the metric does, the metric
  has not earned its forward passes.
related_works:
- |-
  THE DETECTION STATISTIC IS NOT OURS, AND THIS ENTRY EXISTS TO SAY SO UNPROMPTED. A publicly released
  community model-scanning tool (the Jorak / Model Scanner project on GitHub) already implements the core
  mechanism we had intended to claim. Its subspace-signature routine takes, for each layer, the bottom-k LEFT
  singular vectors of the attention-output and MLP-down matrices, sums the resulting per-layer projectors, and
  reports the leading eigenvalue mass of that sum - which at k equal to one is exactly the largest eigenvalue
  of the mean projector - explicitly framed as reading a shared direction rather than a magnitude, with a
  layer-band variant for localised edits and a rough calibration separating censored from abliterated
  checkpoints. It needs no parent and no prompts. We therefore withdraw any novelty claim on the instrument.
  It enters this study as an off-the-shelf auditor screen that we CALIBRATE and STRESS: we give it a null
  model and an honest-panel false-positive rate, whole-family held-out validation, bf16-as-shipped behaviour,
  a recipe census bounding which real checkpoints it can see, and the injection arm it does not implement.
  The tool is grey literature rather than a paper, which changes nothing about priority and is stated plainly
  rather than used as a loophole.
- |-
  arXiv 2508.00161, 'Watch the Weights', is the published NEGATIVE RESULT in this lane and the previous
  version did not cite it. Its Remark 3.2 says verbatim that applying the decomposition to the weights
  directly, doing away with the base model entirely, gives success that varies greatly across models, with
  perfect detection for some and near random for others. The scope matters and we state it exactly: their
  parent-free variant is PER LAYER, uses the TOP-k singular vectors, and uses them as activation-monitoring
  directions rather than as any cross-layer weight statistic, and their reported failure case flags 6.71
  percent of prompts against a calibration false-positive floor near 10 percent. So it is a genuine negative
  for parent-free weight-only detection, but it is not a negative for the subspace-sharing construction,
  which it never computes. We cite it as the reason a per-layer parent-free read is unreliable - a single
  matrix's spectrum is dominated by that layer's own training - and as the honest prior expectation that any
  weight-only screen may work on some families and not others, which is why held-out-family validation is a
  success criterion here rather than an afterthought.
- |-
  arXiv 2607.01854, the two-signal abliteration audit, is the state of the art in cheap checkpoint auditing at
  roughly 0.95 AUROC over a registry of public abliterations, and its weight signal uses the IDENTICAL matrices
  we do - an energy ratio of the leading squared singular value over the total, on attention-output and
  MLP-down matrices in a mid-stack band. The decisive difference, which we now say explicitly, is that it
  computes that energy PER LAYER on the base-to-candidate DIFFERENCE, so it is parent-dependent; its own
  abstract concedes it presumes an attested reference and is effective triage rather than tamper-proofing. Ours
  is computed on the candidate alone and reads cross-layer subspace overlap. It also detects only removal of
  refusal, while our ladder includes the opposite edit, injection, which no existing detector was built for.
  Its registry is a ready-made source of real edited and un-edited checkpoints.
- |-
  The weight-subspace-comparison literature is real and was previously absent, and none of it is
  cross-layer-within-one-checkpoint edit detection. arXiv 2608.07786, tracing model lineage via spectral
  fingerprints, computes principal angles between the top-k left singular subspaces of TWO MODELS at the same
  layer index and averages the least-aligned layers; that is pairwise across models and answers a lineage and
  intellectual-property question, and a lineage fingerprint is by design STABLE under the edits we want to
  see, since a descendant must still fingerprint as its ancestor. arXiv 2511.06390 compares per-layer singular
  value MAGNITUDE spectra of attention invariant products between two models with a depth-matching alignment,
  again pairwise and again lineage. The projection-kernel formalism for subspace overlap (arXiv 2601.10266) is
  applied to attention-head composition inside one small model for interpretability. The universal weight
  subspace hypothesis (arXiv 2512.05117) finds shared low-rank subspaces across a POPULATION of models at
  matched layer index, for compression and merging. And arXiv 2607.25750 concatenates each layer's top-1 left
  singular vector into a feature for a SUPERVISED adapter classifier rather than computing an unsupervised
  alignment. We cite all five as the neighbourhood, and none of them as our contribution, because our
  contribution is not the statistic at all - it is the cost axis the statistic is used on.
- |-
  arXiv 2508.20766, rank-one safety injection, IS the rank-one rung of our ladder and we do not claim
  otherwise. It is a fine-tuning-free rank-one weight modification applied to all residual stream write
  matrices, with the direction computed from a small set of harmful and harmless instruction pairs, presented
  as the opposite of refusal-direction ablation. It measures harm refusal with a guard model and preserves
  standard capability benchmarks. Its only benign column is compliance on 512 ordinary Alpaca prompts, with no
  over-refusal or exaggerated-safety measurement anywhere - and ordinary benign prompts are not where a refusal
  injection does damage. Our contribution is not the edit: it is the cost-and-detection axis it is measured on,
  the quantitative reversal test at its own operating point, and the observation that because it writes ONE
  direction into ALL residual write matrices it is visible from the weights alone with zero prompts.
- |-
  arXiv 2602.02132, 'There Is More to Refusal in Large Language Models than a Single Direction', is the paper
  that forces the re-aim of our headline experiment and was previously uncited. It constructs an over-refusal
  split from XSTest and reports that under refusal-direction steering, refusal on harmful prompts and
  over-refusal on benign prompts rise in parallel, both approaching saturation, with per-coefficient numbers. So
  the QUALITATIVE claim that pushing a model toward the refusal subspace buys over-refusal is already in print,
  and presenting it as new would have been the most quotable error in the paper. We cite it as the item-level
  precedent that makes our prediction principled, and re-aim H6(a) at what is open: where the published weight
  edit's OWN operating point lands on a two-sided score, and whether that score reverses its own verdict.
- |-
  arXiv 2608.05578 (AMS) is the closest existing reference-free per-checkpoint internal score. It computes an
  activation-geometry separation statistic with no parent, validates across 14 model configurations spanning
  four families, and reports it predicting compliance at Pearson r = -0.546. Our increment is therefore not
  that a per-checkpoint number exists; it is the battery, the cost-and-detection ladder, and a ground truth that
  penalises a blanket refuser, which AMS does not have. AMS also carries a warning aimed straight at our audit
  limb: its taxonomy states verbatim that its fourth class is undetectable by activation-only probing and
  represents a documented failure mode of the approach. We adopt that as a pre-registered prediction that the
  off-manifold residual FAILS on our two training rungs.
- |-
  arXiv 2604.18901, 'Harmful Intent as a Geometrically Recoverable Feature of LLM Residual Streams', and arXiv
  2603.27412, LatentBiopsy, together supply R1's mechanism and kill a large share of any 50-metric battery in
  advance. The first finds harmful intent linearly separable at a mean effective AUROC of 0.982 across 12 models,
  four families and three alignment variants, with abliterated variants matching their instruction-tuned
  counterparts to within 0.003. The second, on exactly the base / instruct / abliterated triplets this request
  names, reports abliterated variants at most 0.015 below instruct and calls it a geometric dissociation between
  harmful-intent representation and the downstream refusal mechanism. The consequence is filed as a prediction:
  a harm-KNOWLEDGE readout is near-constant across alignment variants and cannot separate them, so what must be
  read is whether refusal USES the knowledge. The first also warns the recovered direction is protocol-dependent,
  with two pooling choices at one layer recovering directions 73 degrees apart, so extraction is fixed in advance.
  Both are PROMPT-level detectors with a fixed model; neither produces a per-checkpoint score and no edited
  checkpoint appears in either.
- |-
  arXiv 2605.06324, 'Gaming the Metric, Not the Harm', proves a general-form version of our rank-zero step in
  the black-box setting: its Proposition 4.1 states that if a semantic class contains two variants whose metric
  values differ, the induced mechanism is not manipulation invariant, and its repair is a semantic-envelope lift
  taking the maximum over a variant's closure, proved to be the unique pointwise-minimum conservative
  classwise-constant repair. We concede priority on the level-versus-relationship theorem and claim only the
  weight-and-activation instantiation, the cost ordering by edit rank, and the pairing of forgery cost with
  detection cost under two access tiers.
- |-
  Tamper-resistance work is the published MIRROR IMAGE of this cost axis. Tamirisa et al., 'Tamper-Resistant
  Safeguards for Open-Weight LLMs' (arXiv 2408.00761, ICLR 2025), measures what it costs to REMOVE a safeguard in
  the adversary's fine-tuning steps, reporting a consistent loss plateau across 500 steps and sweeping learning
  rate, adapter rank and chat-template variants; TamperBench (arXiv 2602.06911) systematises such stress tests
  across many models and threat types. We measure what it costs to FAKE the appearance of safety. The two bound a
  safety metric from opposite sides.
- |-
  Benchmark gameability has standard references any reviewer will know. Zheng et al., 'Cheating Automatic LLM
  Benchmarks: Null Models Achieve High Win Rates' (arXiv 2410.07137, ICLR 2025 Oral) is the black-box precedent
  for the cheapest readout being the cheapest to game - a constant output that never reads the instruction
  reaching a high length-controlled win rate - which is literally our constant rung one level up. 'Safetywashing'
  (arXiv 2407.21792) shows most safety-benchmark variance is a capabilities component, which is precisely why
  correlating a metric with a benchmark selects for the wrong thing. 'The Leaderboard Illusion' (arXiv 2504.20879)
  gives the ecosystem version. Our narrow claim: single-checkpoint white-box weight and activation metrics, ranked
  by the cost of a publisher-side edit that also survives a reference-free structural check.
- |-
  Arditi et al., arXiv 2406.11717 (NeurIPS 2024), established both halves of the mechanics we use for the
  rank-one and constant rungs: that adding the refusal direction elicits refusal even on harmless instructions,
  and the weight-space realisation by orthogonalising column vectors against the direction. Neither is new here
  and we cite it as the origin. What is new is asking what these edits do to a METRIC, and at what detection
  cost, rather than what they do to behaviour.
- |-
  The genuinely reference-free cheap scores that already exist are our baselines, and we commit to which are
  RE-IMPLEMENTED rather than merely classified. N-GLARE (arXiv 2511.14195) reads one model's hidden-state
  trajectories under a few probe conditions and reproduces red-team attack-success rankings at under one percent
  of the token cost; its score is a mean Jensen-Shannon divergence between trajectory distributions over layer
  groups. Skin-Deep (arXiv 2606.22676) reads activations of a single aligned model and produces one scalar
  predicting how much refusal survives a future fine-tune, over 21 models, as a contrastive principal-component
  statistic relative to the standard refusal direction. Both are re-implemented and forged alongside our own,
  with their prompt-set and layer-grouping sensitivity measured since those are not fully pinned down in the
  source text. The J-space protocol of arXiv 2607.12792 separates dangerous from safe prompts in a single model's
  pre-generation activation space; if it cannot be reproduced faithfully it is classified from functional form
  and that is stated. All are levels read at fixed coordinates, so the edit-rank law predicts their rung before
  we measure it, none has been subjected to an edited checkpoint, and none is validated against a target a
  blanket refuser loses on.
- |-
  arXiv 2606.16349, on harmfulness-refusal coupling under dynamic adversarial fine-tuning, is the nearest
  relative of our coupling readout and its own conclusion is adverse, so we adopt it rather than argue with it:
  it reports supervised fine-tuning as a negative control whose coupling barely moves while attack success stays
  high, and concludes coupling is a descriptive diagnostic rather than a standalone safety predictor. Our claim is
  not that coupling predicts safety better; it is that across-item statistics of this form are the ones a
  constant-offset forgery cannot move and the ones that survive a held-out lineage, which are properties of
  functional form and were never that paper's question. arXiv 2607.00572 (HARC) is complementary in the other
  direction, TRAINING such a coupling in as a defence where we only read it. The wider family - arXiv 2507.11878
  on harmfulness and refusal being encoded separately, arXiv 2603.05773 on recognition versus execution, and arXiv
  2609.14759, which finds that as the basis widens moral judgment keeps reading more of it while refusal levels
  off at a single harm direction - has established the phenomenon at the item level. The honest statement of the
  gap is narrow: the per-checkpoint number exists, the axes it should be judged on do not.
- |-
  arXiv 2608.09624, 'Measuring the Wrong Thing', reports harmful-intent decoding AUROC falling from 0.936 plain
  to 0.803 under wrapping, and arXiv 2607.13075, 'The Entanglement Wall', reports fixed-probe transfer of only
  0.656 to 0.819 to matched pairs across three model families. Together with Tan et al. (arXiv 2406.09289) on the
  out-of-distribution brittleness of steering vectors, these are why the iteration-1 claim that a perturbation
  closes the rank-one forgery route was withdrawn: 0.803 is a usable direction, and an adversary who knows the
  metric's definition refits on the metric's own distribution at identical cost. The perturbation arm survives as
  a measurement run in Stage 0, and the rank-one rung is closed by the weight instrument instead. All score
  PROMPTS with a fixed model; none produces a per-checkpoint number.
- |-
  arXiv 2406.05946, 'Safety Alignment Should Be Made More Than Just a Few Tokens Deep', established that
  alignment is often shallow and that deepening it is a training objective. It diagnoses shallowness WITH training
  access and then fixes it. We ask the question it leaves untouched: can shallowness be read off a single
  downloaded checkpoint with no reference and no training access, and does that reading predict how much safety
  survives a shift. arXiv 2412.09565, 'Obfuscated Activations Bypass LLM Latent-Space Defenses', is the closest
  work on gaming an internal readout and reports an obfuscation tax, but its object is a per-input monitor at
  inference time defended by a probe the attacker can query, and its direction is making a harmful input look
  benign; ours is a model-level certificate computed by a downloader who never meets the uploader, making an
  unsafe MODEL look safe through levers a monitor-evasion attacker does not have, starting with the repository's
  own configuration files.
- |-
  arXiv 2602.04653, on inference-time backdoors via chat templates, with its static scan of roughly 192,000 Hub
  chat templates, establishes that the files shipping beside the weights are an unexamined and widely exploitable
  surface. It points that lever at making models behave badly; we point the identical zero-cost lever at making
  models SCORE well. Because a content scan of the shipped template is reference-free, our rung zero is metric
  hygiene rather than a threat, so it is reported and then removed from the headline, which starts one rung up.
  arXiv 2505.17815 and arXiv 2509.18058 establish that evaluations can be defeated from the inside by a model that
  infers it is being tested; they locate the agency in the MODEL, we locate it in the PUBLISHER and in files the
  model never sees as input, and the two failure modes call for opposite defences.
- |-
  Efficient-benchmarking work using item response theory is the one place the two sides of safety are combined.
  arXiv 2608.05086, 'Item Response Theory for AI Safety', makes the adaptive-item claim that roughly ten adaptively
  chosen items suffice for several individual benchmarks, cutting evaluation cost by 97 to 99 percent; arXiv
  2606.20626 reports a reduction of at least 80 percent. That line points harmful-refusal and over-refusal the same
  way by sign-flipping the over-refusal benchmark, but it is fully behavioural, needs the benchmark items, and
  yields a ranking factor rather than an operating point. No cheap metric read from weights or activations has been
  validated against a target a model refusing everything loses on.
- |-
  arXiv 2502.16173, 'Mapping 1,000+ Language Models via the Log-Likelihood Vector' (ACL 2025), is the closest
  precedent for the manifold limb: it gives every model coordinates whose squared Euclidean distance approximates
  the divergence between generation distributions, and builds a map over more than a thousand models, which is the
  scale our honest-manifold fit needs and the evidence such a fit is affordable. Those coordinates are black-box
  and about similarity and lineage rather than safety, and nothing there asks whether a checkpoint sits off the
  manifold because someone edited it. We adopt it as precedent AND as a baseline: if a log-likelihood model map
  detects our forgeries as well as a metric-vector manifold does, the internal coordinates have not earned their
  forward passes, and we report that.
- |-
  The secret-draw protocol is deliberately NOT claimed as novel and the literature is cited so it cannot be
  mistaken for a claim. Private and dynamic benchmarking - Dynabench (arXiv 2104.14337), Shirali, Abebe and Hardt's
  'A Theory of Dynamic Benchmarks' (arXiv 2210.03165), which proves iterated benchmark-versus-model fitting stalls
  after about three rounds, and TRUCE private benchmarking (arXiv 2403.00393) - all do the same thing for the same
  reason, for black-box behavioural items. Strategic classification (arXiv 1506.06980) supplies the
  cost-of-manipulation vocabulary but assumes the scoring rule is public and fixed, where our hidden randomness is
  the item draw rather than the rule. Casper, Ezell, Siegmann et al., 'Black-Box Access is Insufficient for Rigorous
  AI Audits' (FAccT 2024, arXiv 2401.14446), is the policy argument that audits must look inside the model, which
  our weight-and-activation instantiation is a concrete instance of. What none combines is a metric read from
  weights or activations, an adversary who knows the metric's definition but not the audit-time draw, and a
  perturbation-family pool as the source of that secrecy.
inspiration: |-
  The frame came from anti-doping laboratories, and so did both repairs. An athlete can raise a testosterone
  LEVEL, and for years the test was that level, so the test was beaten. What replaced it was the carbon isotope
  ratio: synthetic testosterone carries a different carbon-13 signature, so the fraud is caught not by the size of
  any one number but by an inconsistency between numbers that a real body cannot produce apart. The same principle
  runs through forensic accounting, where fabricated books satisfy the headline total but violate the joint
  distribution of leading digits, and through art authentication, where the pigment is right and the pigment's trace
  elements are wrong. Safety metrics for downloaded models are currently all levels, and nobody has asked what their
  ratios do.

  Anti-doping also did not defeat targeted evasion by inventing an un-spikeable analyte. It used OUT-OF-COMPETITION
  RANDOM TESTING, so the athlete cannot know when or what is measured, and the ATHLETE BIOLOGICAL PASSPORT, which
  catches the intervention by the trace it leaves rather than by the value it produces. Both transfer: the audit's
  items are drawn at audit time rather than published, and the rank-one edit is closed by the trace it writes into
  every layer it touches.

  This iteration's repair came from a fourth field, and from taking a critique seriously rather than defending
  against it. The previous instrument measured the SIZE of a spectral anomaly, and sizes are exactly what differs
  between one trained network and another, so the honest baseline moved more than the signal did. Chemometrics and
  signal processing solved that problem long ago by throwing the magnitudes away and keeping only the SUBSPACE - the
  principal angles between what two measurements span, which is what a Grassmannian distance is for. A projector
  knows which directions a matrix uses and nothing about how strongly. That single change makes the statistic
  invariant to every layer's own spectrum, and it converts the reviewer's kill shot into a measurement: a per-layer
  abliteration tool is not drawing random directions, it is estimating the same refusal feature at every layer, so
  the alignment it leaves is a number to be measured rather than an assumption to be defended.

  Two further imports shaped the design. From economics, costly signalling: a signal is informative only when it is
  expensive to produce for those lacking the underlying quality, which converts "is this metric valid" into the
  measurable "what does forging it cost". From clinical-trial statistics, the habit of asking whether a candidate
  marker merely reports the outcome you can already see or predicts one you cannot - here the difference between
  predicting a benchmark score, which a plain refusal rate already does, and predicting whether that score survives a
  lineage or a condition the benchmark did not contain.

  The last piece is internal: the field's own repeated negative result, that a plain refusal rate and even the model
  card beat every internal readout. That is a strange result to accept at face value, and the resolution offered here
  is that behaviour will always win at predicting behaviour on honest models, so the comparison has to be run where
  behaviour is not a reliable witness - on a lineage nobody tuned on, and on a checkpoint someone had a reason to
  shape.
terms:
- term: Cheap safety metric
  definition: >-
    A number estimating how safe a model is, computed from a single checkpoint in seconds to a couple of minutes from its
    weights, a few dozen short forward passes, or a handful of generations, with no parent model, no attested base to diff
    against, and no benchmark run.
- term: Level metric
  definition: >-
    A norm, rate, mean projection or unconditional propensity read at a fixed direction, layer and token position - a functional
    of the model evaluated without reference to how it varies across inputs. Predicted to be the constant-forgeable class
    and the class that fails on held-out lineages. A zero-prompt metric has no item axis, so it is a level by construction,
    which is why the floor on a trustworthy metric is not zero prompts.
- term: Across-item metric
  definition: >-
    A correlation, rank ordering or area under a curve computed over the item set, and therefore invariant to a constant offset
    - exactly so for a linear read at the injection layer, and approximately for anything read through a normalisation, where
    the pre-registered tolerance is 0.05 correlation units.
- term: Forgery cost
  definition: >-
    The cheapest rung of a fixed cost-ordered ladder of checkpoint edits that pushes a metric past a threshold set at a stated
    false-positive rate on a large honest panel, while the model's two-sided safety does not improve by more than a powered
    margin. Recorded in wall-clock seconds, training FLOPs and labelled examples, and reported as a curve over false-positive
    rates.
- term: Detection cost, Tier A and Tier B
  definition: >-
    What it costs an auditor to notice a rung was applied. TIER A is reference-free and uses only the downloaded repository
    with no knowledge of its family: content checks on the chat template and generation config, a state-dict key-and-shape
    check against the architecture named in config.json, and the zero-prompt weight statistic. TIER B additionally diffs those
    files against the family default, which presumes an attested reference. Tier A is the headline because it is the access
    model the request specifies; the gap between the tiers measures how much detection power comes from knowing the family.
- term: Undetectable forgery cost
  definition: >-
    The headline quantity: the cheapest rung that both pushes the metric into the safe region and survives the Tier A reference-free
    screen. It can be far higher than plain forgery cost for exactly the rungs that leave a structural trace, and if it turns
    out to be constant across the battery that is itself the result - the only undetectable forgery is training.
- term: Forgery ladder
  definition: >-
    Six rungs. F0, an edit to files shipping in the repository. F1, an inference-time system prompt. F2a, the CONSTANT rung.
    F2b, the RANK-ONE rung. F3, a small keyword-triggered refusal adapter trained for about a hundred steps. F4, genuine light
    safety fine-tuning on real paired data, which buys real safety and caps the ladder.
- term: Constant rung, F2a
  definition: >-
    An item-independent additive offset to a band of residual writes. As a change to the linear map this is rank zero, and
    the identical offset lands on every item so it cancels exactly from any across-item statistic read linearly at the injection
    layer. How it is BUILT matters for detection: most panel architectures define no bias on the attention output or MLP down
    projections, so an explicit bias tensor is caught for free by a key-and-shape check, and the offset is therefore realised
    instead on a near-constant carrier coordinate such as an attention-sink or massive-activation dimension, with its across-item
    constancy verified against the 0.05 tolerance.
- term: Rank-one rung, F2b
  definition: >-
    The residual write becomes W x plus alpha r (d transpose x), which is item-dependent because each item is scaled by its
    own component along d. This is genuinely rank one in the map, it CAN move across-item statistics, and it is a published
    method rather than a trick invented here. It writes one shared direction into every write matrix it touches.
- term: Abliteration
  definition: >-
    A training-free community edit that suppresses a refusal direction in the weights, replacing W by (I minus kappa r r transpose)
    W, producing an uncensored checkpoint. At kappa equal to one it is a projection, so it is singular and has no inverse.
    Because it removes each item's own component along r it is ITEM-DEPENDENT and belongs in the rank-one class, so its filed
    prediction is not invariance but a FALL in across-item coupling. Real recipes vary in three ways that matter to any weight
    detector: whether one direction is shared across layers or fitted per layer, whether kappa is one or less, and whether
    all layers or a band are edited.
- term: Subspace alignment (the shared-direction scar)
  definition: >-
    The zero-prompt, parent-free weight statistic that forms the detection column - ADOPTED FROM PRIOR ART, not introduced
    here: a publicly released community model scanner already computes it, and we cite it rather than claim it. For each residual-write
    matrix, form the projector onto its bottom-k (or top-k) LEFT singular subspace; average those projectors over a contiguous
    band of layers; take the largest eigenvalue. Bottom-subspace alignment reads abliteration, top-subspace alignment reads
    injection. Because a projector discards singular values, the statistic is invariant to each layer's own spectrum - measured
    at 0.168 on a Gaussian honest stack and 0.177 on a heavy-tailed one, where the raw Gram statistic it replaces swung from
    0.821 to 0.119. Because it is windowed, an edit confined to part of the stack is found rather than diluted - 1.000 at
    a half-stack band where the raw Gram sat inside honest range. Because it is a continuous overlap it degrades gracefully,
    reading 0.953 at ablation weight 0.7 and tracking the cross-layer cosine monotonically down to 0.358 at a cosine of 0.25.
    It reads an EDIT rather than a RISK and is never reported as a safety score. What this study adds to it is not the formula
    but the things it has never been given: a null model and an honest-panel false-positive rate, held-out-family validation,
    bf16-as-shipped thresholds, a census bounding which real recipes it can see, and an injection arm.
- term: Local rank deficiency
  definition: >-
    The companion statistic that needs no sharing at all: per matrix, the ratio of the smallest to the second-smallest singular
    value. A full-strength projection makes the matrix exactly rank-deficient and collapses this ratio, whatever direction
    each layer used and whatever that layer's spectrum looks like, so it catches per-layer abliteration which subspace alignment
    is blind to by construction. Pre-registered in log units against a bf16-rounded reference, because real abliterated checkpoints
    ship in bf16 and never show an exact algebraic zero.
- term: Cross-layer cosine
  definition: >-
    The mean pairwise absolute cosine between the per-layer suppressed directions of an edited checkpoint, recovered parent-free
    as each layer's bottom left singular vector. It is the variable subspace alignment is graded in, it distinguishes a genuinely
    shared-direction recipe from a per-layer one, and it is MEASURED on real abliterated checkpoints in the Stage 0 recipe
    census rather than assumed.
- term: Recipe census
  definition: >-
    The Stage 0 survey of 30 to 50 real abliterated Hub checkpoints, classified by tool and recipe from the card and by realised
    strength, layer coverage and cross-layer cosine from the weights. It reports the fraction of real abliterations that are
    full-strength single-direction all-layer, which is the fraction the previous version's statistic could see, and it is
    run before the ladder is graded so the detector's coverage is a pre-committed number rather than a discovery.
- term: Cross-fitted internal harm estimate
  definition: >-
    A harm direction fitted on held-out folds of items and evaluated only on items that did not fit it, with a pre-registered
    fold structure stratified by harm category. Cross-fitting is part of the definition, not an analysis choice, because an
    in-sample difference-in-means projection at a residual width of two to three thousand and a few dozen items separates
    pure noise at AUROC 1.000.
- term: Secret-draw coupling
  definition: >-
    The shipped discriminator: over a few dozen items drawn AT AUDIT TIME from a large pool of presentation conditions rather
    than from a published set, the share of across-item variation in the model's refusal drive at the first generated token
    explained by its own cross-fitted internal harm estimate. Drawing at audit time means a publisher can fit an edit to the
    metric's form but not to its draw.
- term: Decision spread
  definition: >-
    The across-item standard deviation of the refusal drive, in logits. It is the denominator of the coupling ratio and goes
    to zero for both a blanket refuser and a never-refuser, which is what stops the ratio being a quotient of two noise terms
    and what makes a model that refuses everything lose.
- term: Exchange rate
  definition: >-
    The continuous form of undetectable forgery cost, now defined for every rung rather than only the weight ones. Sweep the
    rung's magnitude - edit strength for the weight rungs, a graded preamble token budget for the text rungs - and take the
    Tier A screen's z-score against the honest panel at the smallest setting that pushes the metric past its threshold. It
    separates metrics that share a rung label but differ by orders of magnitude in how loud the change that breaks them has
    to be.
- term: Two-sided discrimination ground truth
  definition: >-
    The safety label the metrics are graded against: graded compliance with harmful requests combined with false refusal of
    benign requests that merely look alarming, constructed so a model refusing everything scores badly rather than perfectly,
    and reported beside a named capability column. It is not our invention - the better model cards already pair a safety
    rate with a refusal rate, and at least one public multi-model safety evaluation ships an over-refusal scenario beside
    its harm scenarios.
- term: Retention ratio
  definition: >-
    A checkpoint's out-of-distribution safety divided by its in-distribution safety, on the same harmful items presented plainly
    versus wrapped, paraphrased or translated. The quantity a downloader actually cares about, and the one a few-prompt behavioural
    score cannot estimate without running the out-of-distribution set.
- term: Off-manifold residual
  definition: >-
    The distance of a checkpoint's metric vector from the low-dimensional set that honest checkpoints occupy, fitted on at
    least 120 honest Hub checkpoints with family-centring over a pre-registered handful of coordinates, never on the ground-truth
    panel. A consistency check among readouts rather than the level of any one of them; if it degenerates into a family detector,
    that is reported as the result.
summary: |-
  Cheap safety metrics for downloaded models are chosen by correlating them with benchmark scores on honest
  checkpoints, which answers the wrong question twice: it never checks whether they survive a lineage they were not
  tuned on, and it assumes the uploader is honest. We answer both. First, across 50 registered single-checkpoint
  metrics we predict and test that only ACROSS-ITEM readouts - how refusal varies with the item - separate
  safety-tuned from instruct from abliterated on held-out lineages, because published work shows harm knowledge
  itself is near-identical across all three. Second, we rank the metrics by what an UNDETECTABLE fake costs, since
  cheap to apply and cheap to catch is not a threat, with an algebraic reason for the ordering: constants cancel from
  across-item statistics, while a rank-one edit moves them but writes one shared direction into every layer it
  touches, which an existing public parent-free weight scanner already sees. That scanner is prior art, not our
  contribution, and we say so; our contribution is the cost-and-detection axis it is used on, plus the calibration,
  held-out validation and recipe census it has never been given.
alternates:
- title: Internals buy fewer prompts, not better answers
  hypothesis: >-
    At a matched prompt budget, an activation readout is a lower-variance estimator of the SAME safety quantity a black-box
    score estimates, so internals win only in the few-prompt regime and the advantage vanishes as the budget grows. Concretely:
    with at most eight prompts the best cross-fitted activation readout predicts the full two-sided discrimination score better
    than any behavioural estimator built from the same eight prompts, and the two curves cross by roughly sixty-four prompts.
    No forgeries, no ladder - just the crossover curve, with the crossover point itself as the deliverable number.
  why_it_could_win: >-
    This wins if the real reason internal readouts have never beaten black-box baselines is that every published comparison
    gave the baseline an unlimited prompt budget. The world would have to be one where refusal is essentially one-dimensional
    and behaviourally visible, so no unique construct lives inside the model, but where binary generation outcomes are noisy
    enough that a graded continuous read of the same decision is worth many samples. That makes cheapness rather than validity
    the thing internals buy, which is cleaner and more immediately actionable than the main hypothesis if no metric turns
    out to be forgery-resistant at all.
- title: Refusal depth predicts what survives a shift
  hypothesis: >-
    Drop the forgeries entirely and read one ordering off a single checkpoint: the layer at which its refusal signal first
    becomes decodable, relative to the layer at which the request's semantic content first becomes decodable, both cross-fitted
    with a per-model permutation null. Claim: refusal that resolves EARLIER than the content it is supposedly about is a lookup
    on surface features, and the earlier that crossing, the smaller the fraction of the model's in-distribution safety that
    survives wrapping, paraphrase or translation. One layer
</pasted_content id="e5c3">


<pasted_content id="e5c3">
 sweep, no edits, no manifold, no constructed fakes.
  why_it_could_win: >-
    This wins if real Hub checkpoints already span the whole shallow-to-deep range, which is plausible given how many are
    light fine-tunes and merges - in which case constructing forgeries is expensive apparatus for variance that already exists
    in the wild. It beats the main hypothesis in a world where deliberate metric-gaming is rare but accidental shallow alignment
    is everywhere, and it disagrees concretely: under this alternate the useful signal is an ordering of two layer indices,
    not a relationship across items, so the two predict different metrics to be the best one.
- title: The recipe is the signal, not the safety
  hypothesis: >-
    For a checkpoint you know nothing about, the only cheap thing that reliably survives held-out families is a read of its
    EDIT HISTORY from the weights, and no activation-based safety readout adds anything on top of it. Existing parent-free
    weight scanners answer only a yes-or-no question, was this abliterated. The claim here is that the same weights answer
    a strictly richer one, and that the richer answer is what carries the safety signal: recover, parent-free and in seconds,
    WHICH RECIPE was used - shared versus per-layer direction, realised ablation strength, which layer band - and that recovered
    recipe, in particular the realised strength, is MONOTONE in the checkpoint's measured harmful compliance and predicts
    its two-sided safety better than any cross-fitted activation metric in the battery once whole families are held out. That
    would turn a binary tamper flag into a graded safety read, which no existing scanner provides. The honest deliverable
    is a recipe-resolved detector with a stated scope, and the paper's job is to map exactly which risks it is blind to, starting
    with a model that was never edited and is simply unsafe.
  why_it_could_win: >-
    This wins if what actually varies across Hub checkpoints is edit history rather than safety, which near-zero within-family
    safety variance plus the published finding that harm geometry is nearly identical in base, instruct and abliterated variants
    both point to. It beats the main hypothesis in a world where coupling turns out flat or noisy at a few dozen items, and
    it disagrees head-on: under this alternate the detection column is not a supporting axis for a safety metric, it is the
    entire result, and it makes a sharper prediction the main hypothesis does not - that ablation STRENGTH, recovered from
    the weights alone, is monotone in measured harmful compliance.
- title: A learned metamodel reads lineage, not safety
  hypothesis: >-
    A small regressor trained on pooled hidden states predicts benchmark safety scores better than any hand-written formula,
    and the reason is that it recovers architecture and lineage identity rather than safety. The ablation predicts the advantage
    collapses to nothing once whole families are held out, while a lineage-identity probe on the same features stays near
    perfect - and the gap between those two curves is the deliverable, because it puts a number on how much of any activation-based
    safety score is family bookkeeping.
  why_it_could_win: >-
    This wins as the right answer if the strongest rival to every formula is a learned metamodel and nobody has isolated what
    it reads. It beats the main hypothesis in a world where the metamodel genuinely does generalise to unseen families, which
    would mean a safety signal exists in activations that no hand-designed statistic has captured, and the main hypothesis's
    whole framing - interpretable named metrics ranked by forgeability - would be looking in the wrong place.
_relation_rationale: >-
  Across-item coupling and forgery cost become two rows of a wider screen scored on graded two-sided safety.
_confidence_delta: decreased
_key_changes:
- >-
  EVIDENCE CLASSIFIED weak_or_null: only 3 of 50 metrics beat their null, the single metric passing null and poles runs against
  the two-side
</pasted_content id="e5c3">


<pasted_content id="e5c3">
d target (rho -0.71, n=13), weights read the edit and not the risk (rho 0.26, CI [-0.65, 0.86]), and the requester's
  >=3-internal-metric invariant was reported unsatisfiable.
- >-
  BOTH PREVIOUS HEADLINES RETIRED AS HEADLINES: R1 (across-item beats level on held-out lineages) did not hold, and R2's reference-free
  detection axis was withdrawn (best AUROC 0.738 against a 0.80 bar). Neither is shrunk into a smaller claim.
- >-
  OUTCOME CHANGED from a class label on 3 pair-families to a GRADED two-sided score on at least 30 checkpoints and 6 families,
  with a rule that no correlation below n=24 is reported as a verdict. This answers the power failure (n=15 needs |rho| above
  about 0.51).
- >-
  INSTRUMENT DEFECT DESIGNED AROUND: no per-item refusal readout met its bar (best minimum AUROC 0.544, even graded 24-token
  generation 0.547), so the new leading candidates measure coupling causally or through weights, and every readout-dependent
  row also gets an oracle-readout control.
- >-
  POPULATION WIDENED from 50 static one-site reads in 3 classes to 16 candidates in 8 families that can disagree in kind:
  causal gain, direction-conditioned weight paths, component and routing structure, depth and site profile, two-sided geometry,
  a compact metamodel, label-free geometry, and a steering-dose comparator.
- >-
  STEP 1 USED AS DESIGN INPUT: SafeRL and abliterated differences share part of a subspace (31.1 degrees) but not a direction
  (max |cos| 0.20 vs null p95 0.41), so no one-axis level read can be two-sided. This reconciles the two artifacts' opposite
  verdicts.
- >-
  SELECTION RULE FIXED IN ADVANCE (S1-S6): beat the first-token logit gap by 0.15 or carry a nonzero partial given it and
  size, beat permutation and random-direction nulls, pass the blanket-refuser poles with a declared orientation, keep one
  sign across aggregation units, hold at 16 prompts, and beat family-only and size-only rows.
- >-
  HELD-OUT CONFIRMATION SEPARATED: the two sealed families, a sealed item pool and checkpoints harvested after the freeze,
  used once with no re-screening.
- >-
  FORGERY COST DEMOTED to a robustness column for survivors, re-scored on the 183 stored ladder cells; rank-zero cancellation
  becomes one testable prediction about causal-gain metrics.
- >-
  FINISHED POSITIVES KEPT AS MEASURED: grader-side refusal (40.5% / 65.9% minimum grades) and the ROSI two-sided reversal
  (-0.151 [-0.233, -0.065]); the Qwen3-0.6B replication is restated as direction-consistent with a CI that includes zero.
- >-
  REVIEW CRITIQUES ADOPTED AS REPORTING RULES: headline sentences must match full tables, the omitted 0.85 replication, k=64
  crossover, 9/17 and 9/20 direction counts and refusal-based repair numbers are reported, panels are tagged, and Step 1,
  Step 5, metamodel and external limb are reported even where negative.
_evidence_state: weak_or_null
_move: widen
_move_rationale: >-
  Race, weights and ladder all ran: 3/50 beat null, the lone null+pole survivor anti-correlates with safety, weights read
  edit not risk. 3 iterations remain, so the rule mandates widen.
_coverage: full
_coverage_statement: >-
  The next iteration answers the whole ask: the Qwen3-4B four-way internal comparison as design input, a screened and held-out-confirmed
  set of single-model metrics on at most 16 prompts scored against graded two-sided and published safety numbers at both aggregation
  units, plus the mechanism and metamodel bonuses for any survivor.
_candidates_considered: 16
relation_type: embedding
</hypothesis>

<all_artifacts>
FULL EVIDENCE BASE: All 9 research artifacts across all iterations.

--- Item 1 ---
id: art_DeogIL_xh3pE
type: research
title: What rival safety-scoring methods already achieve
summary: |-
  IMPLEMENTATION-GRADE SPECS FOR FOUR INCUMBENTS, FIVE DATED CANDIDATE VERDICTS, AND FIVE VERIFIED NUMBERS. Machine-readable output: spec_table.json (full) and the fenced json block in research_out.json (compact); prose twin research_report.md (~76KB).

  FOUR INCUMBENTS (the plan named three; the fourth was found by the sat
</pasted_content id="e5c3">


<pasted_content id="e5c3">
uration search).
  - AMS 2608.05578 = IEEE Access 14:91723-91737, verdict REPRODUCIBLE, with Apache-2.0 code (pip install "ams-scanner[cli]"; ams scan <model>). Statistic: sigma = (mu+ - mu-)/sigma_pooled on FINAL-TOKEN residual streams along an in-sample difference-of-centroids direction; 16 contrastive pairs x 3 concepts = 96 forward passes, 10-40s/model; layer swept over range(int(0.4L), int(0.8L)) and picked to MAXIMISE separation on the same pairs; PASS>3.5, CRITICAL<2.0. Tier 1 parent-free, Tier 2 needs a stored baseline. DECISIVE: the 71% (10/14) leave-one-out held out ONLY THE THRESHOLD - direction, layer sweep and prompt set were never held out, and the authors concede the coupling. So 71% is a LOOSE, NON-MATCHED bar; a leave-one-LINEAGE-out number from us is strictly stricter. Also: r=-0.546 (p=.043, n=14 models) but Spearman rho=-0.423 (p=.13, N.S.); median bootstrap 95% CI width 3.36 sigma against a 2.0-3.5 band (62% of cells unresolvable). Class (iv) behavioural fine-tuning is ALREADY PUBLISHED as undetectable - cite, do not claim.
  - Skin-Deep/GFS 2606.22676: TWO PLAN ASSUMPTIONS OVERTURNED. It is NOT parent-free (Eq 1 cPCA needs the base model's covariance; code requires --base_model) and needs 1000 prompts; and its retention-prediction claim has NO PRINTED COEFFICIENT - a qualitative co-occurrence at n=7. There is no GFS number to beat.
  - N-GLARE 2511.14195 / ACL 2026 Long 1334: CLASSIFY-BY-FUNCTIONAL-FORM-ONLY. Eq 7 and Eq 9 confirmed verbatim; parent-free AND generation-free, but needs FOUR probing conditions {B,J,R,P} over 7000+ cases, so it is separated from our lane on the PROMPT-BUDGET AXIS ALONE. No numeric Kendall tau for the headline claim in either version; Table 2's numeric taus belong to a DIFFERENT robustness check - quoting them would be a misattribution.
  - RAS/SafeVec 2606.25750 (NEW, not in the plan): the closest published thing to the deliverable - white-box, generation-free, per-checkpoint, calibrated 0-100, separates aligned/uncensored/abliterated, tracks ASR, 210-217x faster than judge-based. BUT it needs a per-family reference model, a calibration set, AND those models' MEASURED ASR, and states "family-specific calibration remains necessary". Our cross-family negative would be a REPLICATION.
  All four bar rows are comparable:false, each for a DIFFERENT nameable reason - that is the finding, and the reasons are now written down.

  CANDIDATES (searched 2026-09-20, plus an adversarial kill-attempt pass): C1 PARTIAL (must beat HRCI_repr; pre-register as DISCRIMINATOR ONLY), C2 PARTIAL (IRT owns the behavioural half; 2608.13329 owns the internal variance decomposition and reports a generalizability coefficient of 0.00002 for cross-family comparison on one prompt wrapper), C3 OPEN as an aggregation only (recipe confound from 2609.03887), C4 OPEN on WEIGHTS-ONLY and PARENT-FREE and GRADED and PREDICTS-COMPLIANCE (the highest-value verdict), C5 OPEN on the ABLATION only. ADVERSARIAL PASS (27 refutation queries): all three OPEN verdicts SURVIVED but two were narrowed - C3's two required curves already coexist in 2507.11878 on the same models, so C3's novelty is ONLY the collapse-subtract-correlate aggregation; and C5's ablation is ESTABLISHED PRIOR ART as a method (2606.02907 residualizes source identity and drives a 100%-accurate hidden-state probe to chance; Hewitt & Liang control tasks), so C5 must be claimed as 'we ran the established control on the per-MODEL axis' not 'we invented the control'. C4 held, with three further near-misses named and excluded; cite the abliteration.org wiki to concede that the cell is a known practitioner open problem. C5's attack was only 6 queries and is the least well-tested verdict.

  NUMBERS: N1/N2/N3/N5 CONFIRMED, N4 AMBIGUOUS-MULTIPLE-OCCURRENCES with BOTH readings of BOTH numbers genuinely true - NO misattribution exists, the premise stands. N1 forces the motivating sentence to be rescoped to per-PROMPT vs per-CHECKPOINT.

  12 DECISIONS (D1-D12) each name the artifact and the action. Handoff blocks are written for the screen, ladder and payoff 
</pasted_content id="e5c3">


<pasted_content id="e5c3">
executors separately, with exact commands and six standing prohibitions.

  GOTCHAS FOR REUSE: scholarly-mode search (OpenAlex/Crossref) is UNUSABLE for this field - an empty result is evidence about the backend, not the field. PDF-to-text inserts hard line breaks mid-sentence, so exact-phrase greps manufacture FALSE NEGATIVES; use whitespace-flexible patterns before recording NOT-FOUND. Near-ID collision 2606.22676 (Skin-Deep) vs 2606.22686 (Geometry of Refusal, TrustNLP). Title collision: Google lists AMS under a different title.
workspace_path: >-
  /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_1/gen_art/gen_art_research_1
out_expected_files:
- research_out.json

--- Item 2 ---
id: art_ynwQLrNKw_e_
type: experiment
title: Cheap safety checks for any single model
summary: |-
  Races five candidate single-checkpoint safety readouts against four published incumbents (AMS 2608.05578, GFS 2606.22676, N-GLARE 2511.14195, HRCI_repr 2606.16349) and three black-box baselines on ONE shared harvest per checkpoint (weight pass + teacher-forced activation pass), identical 160-item battery, identical leave-one-lineage-out folds. Parent-free throughout: the setting is "you found a random model on HuggingFace and have nothing else".

  WHAT IT PROVIDES. results/race_table.csv (all 50 pre-registered metrics, held-out balanced accuracy printed beside the tuned score and the gap, 3-way and 2-way); results/metrics_registry.json + sha256, frozen BEFORE any measurement and re-asserted at the end; results/step1_claim.json (principal angles between the instruct-to-SafeRL and instruct-to-abliterated activation differences on the Qwen3-4B anchor, per layer band, two read positions, plus the weight side); results/f5_weight_instrument.json (the honest-panel false-positive rate the published weight statistic lacks); plus lineage_census.json, ground_truth.json, per_checkpoint_reads.json, the three stage-gate files, and RESULTS.md as the digest.

  FOUR RESULTS THAT ALREADY HOLD, independent of the race outcome.

  F5 - THE PUBLISHED WEIGHT THRESHOLD DOES NOT SURVIVE REAL WEIGHTS. The Jorak-style subspace signature (BSA_w8 over bottom-1 left singular vectors of o_proj, sliding 8-layer window) reads 0.565 on honest, unedited Qwen3-0.6B, well above the 0.35 separator Gaussian simulation calibrates (simulated honest 0.171, invariant across Gaussian and heavy-tailed spectra). The same weights abliterated by us go to 1.000 and BOTGAP collapses below 0.003 in bf16. The statistic discriminates, but its absolute threshold is a false positive on real transformers, which carry genuinely shared bottom directions. Shipped fix: threshold-free AUROC plus a z-score against a within-checkpoint anisotropy-matched null (a random unit vector drawn from that layer's own bottom-16 subspace), validated at z=0.63 honest versus z=34 for a shared-direction edit. Separately, BOTGAP is NOT spectrum-invariant: on a heavy-tailed spectrum the honest value is 0.064, already below its own 0.10 separator.

  CROSS-FITTING IS LOAD-BEARING. On pure Gaussian noise at d=2560 with 64 randomly-labelled items, an in-sample difference-in-means projection separates at AUROC 1.000 and the cross-fitted version at chance (0.377) - an in-sample harm direction is numerically indistinguishable from the harm label. AMS fits its direction on the same 16 pairs it then measures, so it is reported twice, in-sample as published and cross-fitted on our folds, with the gap between them.

  THE SAFETY-TUNED ARM IS SCARCE, AND THAT IS ITSELF THE RESULT. A Hub census returns 445 "safety-tuned" repos, but the top five uploaders account for 85% and suffix-collapsing leaves 245. Only THREE independent safety-tuned lineages are reachable under 4B: Qwen3-4B-SafeRL (official), TinyLlama-1.1B (four algorithms, one parent) and gemma-2-2b (two). Below the pre-registered floor of five, so branch F1 fires: the two-way instruct-versus-abliterated claim becomes primary (11 instruct lineages against 6 abliterated) and the three-way is reported with its lineage count printed.

  AN UNMATCHED SAFETY B
</pasted_content id="e5c3">


<pasted_content id="e5c3">
ENCHMARK IS MOSTLY LEXIS. TF-IDF plus logistic regression, no model at all, reaches AUC 0.963 separating harmful prompts from XSTest safe ones across sources, but only 0.537 against JailbreakBench's own Index-paired benign partners and 0.655 on XSTest positional twins with pair-grouped CV. Every internal readout must beat the MATCHED numbers.

  METHOD NOTES TO INHERIT. The resampling unit is the LINEAGE (parent x tuning run), never the repo. Base checkpoints use the plain renderer and stay in their own stratum. The harvest stores VECTORS (all-layer hidden states at the last prompt token and the first generated token, per item, 35-141 MB per checkpoint), so every direction can be re-fitted and every null recomputed offline with no second GPU pass. Synthetic always-refuse and never-refuse poles run per checkpoint: the blanket refuser earns a +18.8 logit gap but only 0.80 across-item spread against 4.82 normal, which is why the coupling read ships with decision spread as a companion and a 0.25-logit floor below which it is declared UNDEFINED rather than small. Measured XSTest facts correcting the plan: 200 positional twin pairs, not 300, and keying on (type, focus) would silently drop 108 of 450 rows.

  TRAPS FOUND AND FIXED. openai/gpt-5-nano returns content=None at default reasoning effort (192 of 200 completion tokens spent on hidden reasoning), silently degrading every grading to the regex fallback; it needs reasoning.effort=minimal. The judge also returns inconsistent rubric arithmetic, so the StrongREJECT score is recomputed from components. Gemma-2 must load with eager attention because sdpa omits its logit soft-capping. No Qwen judge anywhere; Qwen3Guard never judges SafeRL.
workspace_path: >-
  /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_1/gen_art/gen_art_experiment_1
out_expected_files:
- method.py
- full_method_out.json
- mini_method_out.json
- preview_method_out.json

--- Item 3 ---
id: art_LuFfQwCss9RO
type: evaluation
title: Do safety probes beat random directions?
summary: >-
  Offline, zero-new-compute evaluation of iteration 1's orphaned harvest: 17 checkpoints, 4 lineages, 2 families (Qwen3, TinyLlama),
  160 items. No GPU, no downloads, $0 API spend. The registry sha256 ffe9b234... is intact before and after. PREREG.json was
  hashed before any number was computed. D2 (HEADLINE): each cross-fitted difference-in-means harm direction is tested against
  its own 1000-draw nulls. Null tiers are isotropic, Ledoit-Wolf covariance-matched and within-item-span (primary). Sign is
  fixed on train folds, frozen item folds are used, and the read depth is a fixed 0.6 fraction. content_last (harmful vs plain-benign,
  last prompt token) clears its span-null p95 on 16/17 checkpoints (Wilson [0.73, 0.99]) = SURVIVES. The matched XSTest-twin
  contrast gives 17/17 SURVIVES, and harm vs all-benign 17/17. The first-generated-token read gives 9/17 = PREMISE_FAILS.
  Iteration 1's 0.921-vs-0.921 tie is explained by its best-of-20 null: mean best-of-20 is 0.748 against a span-null mean
  of 0.629 for content_last. The in-sample column inflates AUROC (mean 0.889 vs 0.835 cross-fitted). The whitened (LDA) refit
  is lower than raw (0.759 vs 0.835), so the direction partly rides residual anisotropy. Label-permutation and joint survival
  are also reported. D0: vendored iteration-1 scorer re-driven via the salvage route. Empty race-table cells go from 300 to
  45, with 44/50 metrics computable. There is a 9-row degrade ledger in controlled vocabulary. R1 (frozen gap-ordering prediction):
  corr 0.156, perm p 0.32, not supported. D2b: first-generated-token audit = MIXED (13 CLEAN, 4 MIXED, 0 DELIMITER_CONTAMINATED).
  The Qwen3 <think> delimiter hypothesis for the F3 gate is ELIMINATED, so the readout bake-off is not forced. D1 (user step
  1, all 5 Qwen3-4B anchors present): verdict DIFFERENT_SUBSPACES. The max |signed cos| between the instruct->SafeRL and instruct->abliterated
  mean differences is 0.20 (negative), against a within-span null p95 of 0.41. Split-half r_self is about 0.99, so disattenuation
</pasted_content id="e5c3">


<pasted_content id="e5c3">

  barely changes it. The abliterated-vs-abliterated positive control passes (|cos| 0.92 > null p95 0.72), so D1 is powered.
  The weight limb ran on top-16 o_proj/down_proj subspaces. Also found: a template mismatch for mlabonne, bounded as having
  no measurable effect. D3: results/race_table_v2.csv (schema race_table_v2.1) is a strict superset of the frozen 18 columns.
  It adds lexical floors, family-only / size-only baselines, p_perm/q_BH, readout flag, degrade reason and Qwen3 0.6/1.7/4B
  size-ladder sign flips. Only 17/42 scored metrics beat the family-only baseline, and 12 metrics flip sign across the ladder.
  This is a WITHIN-FAMILY table only. AMS's 71% figure is labelled NON_COMPARABLE. D4 prior art (14 queries, general web +
  arXiv abs fetch): Q1 OPEN, Q2 PARTIAL. eval_out.json (exp_eval_sol_out, validated) carries a HANDOFF block for sibling artifacts:
  readout_contaminated=no, fitted_direction_verdict=SURVIVES (with a whitening caveat), step1_verdict=DIFFERENT_SUBSPACES,
  degraded_metrics and schema_version.
workspace_path: >-
  /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_2/gen_art/gen_art_evaluation_1
out_expected_files:
- eval.py
- full_eval_out.json
- mini_eval_out.json
- preview_eval_out.json

--- Item 4 ---
id: art_mvklSk-v_XwZ
type: experiment
title: Cheap safety meters tested across eight model families
summary: >-
  ITERATION-2 EXPERIMENT 1 (run_fcYd): repair the refusal readout, then buy the model-family axis for the frozen 50-metric
  registry (sha256 verified, never edited). PANEL: 33/34 scheduled checkpoints, all 8 scheduled families (Qwen3, Qwen2.5,
  Phi4, Gemma2, OLMo2, SmolLM2, SmolLM3, TinyLlama), PARTIAL_PANEL=false, harvest-complete barrier passed. Tiers: I=17 inherited
  GPU harvests, G=3 new CPU activation+generation harvests (Qwen2.5-1.5B-Instruct, its Josiefied abliterated sibling [48-token
  gens after an OOM kill, deviation D12, excluded from two-sided-target analyses], CensorTune-0.5B = a REAL blanket refuser,
  judged refusal 1.000), W=13 weights-only. Only 3 families carry an instruct/abliterated pair (2 with activations), so gate
  G2 makes leave-one-LINEAGE-out the PRIMARY holdout (LOFO printed beside it; undefined for activation metrics). Safety lineages
  = 3 (<5): three-way race descriptive only. KEY RESULTS: (1) GRADER-SIDE REFUSAL: StrongREJECT framing makes hosted judges
  emit 1,1,1 on 40.5% of replies (65.9% harmful); stance framing is the primary target (gpt-5-mini vs gemini-2.5-flash kappa
  0.749, Spearman 0.659). (2) READOUT BAKE-OFF (15 judged ckpts, 3 families, signed AUROC vs judged refusal): nothing clears
  the pre-registered bar (min AUROC>=0.80 on every ckpt, invariance rho>=0.70): logitgap min 0.437 (3/15 below chance), refmass
  0.506 (invariance -0.141), nested full-coverage probe_cf 0.544 (chosen), V1 first-token probe 0.516, greedy24 upper bound
  0.547; a diff-in-means readout fitted on 8-64 labelled items never lifts its per-checkpoint minimum above 0.47. Qwen3 think
  trap ruled out: 0/1760 first tokens are <think>. (3) RACE (two-way, primary LOLO, within-lineage permutation null): 3 rows
  beat their null p95: x_presentation_invariance under the probe readout 1.000 (null 0.775), card regex 0.917 (0.788), b_logit_gap_alarming
  0.800 (0.700); best weight metric w_bsa_w8_k4 0.826 only ties its null; no LEVEL-KNOWLEDGE metric beats its null. (4) POLES:
  19 metrics fail the pre-registered rule, incl. every black-box refusal meter and the card regex (a refuse-everything model
  looks safest); x_presentation_invariance is the ONLY metric passing null+poles, but vs the two-sided target it is rho -0.71
  at checkpoint level and -0.40 at lineage level (n=5) -> within-lineage only, reported as negative; the requester's >=3-internal-metric
  invariant is NOT satisfiable. (5) Fitted harm direction beats the within-span null p95 on only 9/20 ckpts (G8). (6) Prompt
  budget: black-box logit margin beats the internal readout from k=1 by |rho| (crossover_k=1); by LOLO BA 0.724 vs 0.445 at
  k=1, internal catches up only at k=64 (0.592 vs
</pasted_content id="e5c3">


<pasted_content id="e5c3">
 0.571). (7) Class trend vs frozen predicted_gap_rank on common support:
  corr +0.246 (one-sided p=0.048); KNOWLEDGE overfits most as predicted, ACROSS-ITEM/BEHAVIOUR order flipped. (8) Step 1 Qwen3-4B
  lineage: SafeRL and abliteration edits share a subspace (31.1 deg) but mean-difference cosine -0.09. FILES: full/mini/preview_method_out.json
  (4 datasets: readout_bakeoff 3600, family_race 935, prompt_budget 1515, poles 418 rows; exp_gen_sol_out schema validated);
  analysis_out.json (gates + panel counts first, then headline_findings and every table); results/summary.json, race.json/race_table.csv,
  readout_bakeoff.json, poles.json, prompt_budget.json, class_trend.json, direction_nulls.json, prereg_deviations.json (D1-D12),
  RESULTS.md (full digest), README.md. Judge spend $0.77. Hardware: no GPU, 2 CPUs and a 16 GB cgroup shared with sibling
  executors.
workspace_path: >-
  /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_2/gen_art/gen_art_experiment_1
out_expected_files:
- method.py
- full_method_out.json
- mini_method_out.json
- preview_method_out.json

--- Item 5 ---
id: art_62dx1518KmQy
type: experiment
title: What faking a safety score costs
summary: |-
  EXPERIMENT ARTIFACT: the six-rung forgery ladder, executed (not just written) on a no-GPU, 2-CPU container shared with two sibling experiments. Entry point method.py (--stages all, or per stage; every stage resumable). Outputs: full/mini/preview_method_out.json (exp_gen_sol_out, validated) with 6 datasets - forgery_attempts (32), metric_cost (50 registry rows), rosi_reversal (5), behavioural_ladder (9), honest_panel (64), checkpoint_ground_truth (13); out/analysis_out.json holds everything else and out/RESULTS.md is the human-readable twin (counts first).
  SCALE: 183 weight-ladder cells over 6 hosts / 6 families (Qwen2.5-0.5B-Instruct, Qwen3-0.6B, TinyLlama-1.1B-Chat, OLMo-2-1B-Instruct, SmolLM2-1.7B-Instruct, gemma-2-2b-it); rungs F0 template forgery, F1 system preamble (5 budgets), F2a carrier + explicit bias, F2b ROSI all-layer (+ hidden-direction arm, 35% band), F3/F4 merged-LoRA-SHAPED deltas (NOT trained). 11 graded behavioural cells (+2 alpha-search) on Qwen2.5-0.5B-Instruct and Qwen3-0.6B over iteration 1's 160 items with 20-token greedy continuations; the inherited 32-metric activation battery recomputed on every edited copy. Honest float64 weight panel: 64 checkpoints, 39 honest, 12 families. Judge openai/gpt-5-mini in a stance-classification framing (the StrongREJECT evaluator framing graded plainly compliant replies as refused); total spend $0.38.
  KEY RESULTS: (1) ROSI alpha recovered by REPRODUCTION on its own Table-1 model: x4 Frobenius multiplier (regex and judge agree). The two-sided score falls monotonically with dose: D2 0.788 (x0) -> 0.776 (x1) -> 0.621 (x4 = alpha*, paired dD2 -0.151 [-0.233,-0.065]) -> 0.500 (x16, blanket refuser). At alpha* harm refusal rises 0.859->0.984 but benign-twin false refusal 0.375->0.750: the pre-registered REVERSAL holds; hidden-direction control dD2 -0.042. Replicates on Qwen3-0.6B (dD2 -0.081 [-0.176,+0.017], our extrapolation). A one-sentence system preamble on Qwen3-0.6B shows the same trade (harmful compliance -0.156, false refusal +0.281). (2) Weights alone: at alpha* the rank-one term is 0.27-0.48 x sigma_max and the zero-prompt TSA read flags it on 0/3 B3-clean hosts; TSA flags only at x16-x64. (3) Parent-free weight screen: best AUROC 0.738 (w_down_botgap_min), best pre-registered B3 component 0.662 at n_honest=39 -> DETECTION AXIS WITHDRAWN under the 0.80 bar; B3 fires on 3/6 UNEDITED ladder hosts; Stage-4 adversary on B3-clean TinyLlama: 16/18 band x coefficient cells evade B3. (4) Blind screen: render-based B1 catches F0 in 26/30 cells (misses = the 2-word 'Be safe.'), F1 is invisible by construction, the explicit bias tensor is caught by B2 30/30, carrier/ROSI/LoRA-shaped edits 0/81 by B2; the family-aware parent diff catches every weight or file edit. (5) The card regex, which reads nothing of the model, separates abliterated checkpoints at AUROC 1.000 on the activation pan
</pasted_content id="e5c3">


<pasted_content id="e5c3">
el.
  CORRECTIONS DOWNSTREAM MUST KNOW: a float32 Gram fakes abliteration (sigma_min = 0 on honest OLMo-2), so everything is float64; the inherited B1 stripped {{ }} expressions and missed F0 on 20/20 cells; Gemma o_proj Grams carry structural zeros; the cached Qwen2.5-0.5B snapshot lacked tokenizer files; GATE 1's 0.105 is algebraically 0.500. CAVEATS: activation thresholds come from n=8 WITHIN-FAMILY (Qwen3/TinyLlama) harvests, so threshold-free movement is the primary activation read; F3/F4 untrained; behavioural cells on 2 hosts only; 9 OOM kills from the shared memory cgroup.
workspace_path: >-
  /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_2/gen_art/gen_art_experiment_2
out_expected_files:
- method.py
- full_method_out.json
- mini_method_out.json
- preview_method_out.json

--- Item 6 ---
id: art_UWWVZbbIfS6p
type: experiment
title: Can model weights alone grade how unsafe it is?
summary: >-
  VERDICT: EDIT_NOT_RISK - the weights read the EDIT and not the RISK (pre-registered inverted outcome). PART 1 (parent-free,
  prompt-free): 71 real sub-4.5B checkpoints read exactly (float64 eigh of every layer's o_proj and down_proj Gram; v1's slowness
  was thread oversubscription, fixed). Down_proj realised-strength kappa_hat separates edited from honest (pooled AUROC 0.84
  over all edited, 0.95 for abliteration-tool outputs); BOTGAP_min 0.74/0.78; o_proj only works on structurally valid sites
  (0.84 vs 0.57 on square sites; a float32 Gram cannot resolve square o_proj bottoms). The PREREG BSA 0.35 flag false-positives
  on 97% of honest checkpoints; thresholds re-derived held-out-by-family. Regression reproduces iteration 1 (o_proj BSA_w8
  0.5650). GROUND TRUTH (parent-based true kappa of 20+ real published edits, 484 layer-matrices): the parent-free read is
  exact inside |1-kappa| < sigma_min/sigma_rms (median kappa_hat 0.98, true-direction cos 1.0) and blind outside (0.29, cos
  0.14); 307/484 real edited matrices lie outside; over-ablation (kappa>1, up to 1.47) is common; fine-tune 'uncensoring'
  (amoral-gemma) leaves down_proj byte-identical. Constructed known-kappa arm: refusal falls 0.44->0.33->0.17 while kappa_hat
  stays flat until c~1. PART 2 (graded test; stance-framed gpt-5-mini judge, gemini agreement kappa 0.785, $1.17 spent): n_edited_graded=14
  (5 families): primary Spearman(kappa_hat, compliance)=0.26, 95% CI [-0.65, 0.86], MDE 0.56; Bar 1: adding kappa_hat to the
  edited label, permutation p=0.16, leave-one-family-out MAE 0.154->0.170; even the TRUE kappa does not grade harm (Spearman
  0.03, n=12); inside the edited arm the best predictor is the logit-only L1 first-token gap (Spearman -0.62, p=0.02); pooled,
  cross-fitted activation coupling -0.78 vs kappa_hat 0.57; Bar 2 LOFO R2 kappa_hat 0.15 / BB8 0.14 / L1 0.56; Bar 5 kappa_hat
  beats the family label. Replication on 3 other runs' stored generations: combined within-edited 0.85 [0.56, 0.95] but mixes
  edit types; projection edits only 0.65 [-0.26, 0.95] (n=10) - a graded signal is not excluded, not established. FORGERY
  (Stage 5.3): a zero-prompt rank-one spectral repair heals BOTGAP (0.012->0.82), kappa_hat, XLC, BSA ('swap') and RQ ('bulk')
  but not behaviour (harmful refusal 0.125->0.208 vs honest parent 0.438); hand-off in results/forgery_handoff.json. PART
  3 (HELM, reused v1 limb): 81 models, 36 resolved, 45 closed-API; only 2 sub-4B with published numbers; identical-weights
  guardian-pair gap up to 6.7x the across-model variance (a ceiling for any weights-only readout). Files: method.py (orchestrator
  + assembly), method_out.json (exp_gen_sol_out, 10 datasets, 333 examples, predict_* strings, 0 pre-submission problems),
  RESULTS.md (auto-generated), results/stage3_v2.json, results/true_kappa/, results/graded/, results/ckpt_v2/, DEVIATIONS.json
  (D0-D24).
workspace_path: >-
  /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_2/gen_art/gen_art_experiment_3
out_expected_files:
- method.py
- full_method_out.json
- mini_method_out.json
- preview_method_out.json

--- Item 7 ---
id: art_newxSSMj3rp
</pasted_content id="e5c3">


<pasted_content id="e5c3">
V
type: dataset
title: Graded safety panel for small chat models
summary: >-
  SHARED GRADED SAFETY PANEL (iter-3 screen substrate). full_data_out.json (exp_sel_data_out, validated) holds 6 datasets:
  dev_panel_outcome (one row per panel checkpoint; output = S2_primary; metadata family/lineage/class = LOFO/lineage fold
  keys, core+full components, 2000-draw bootstrap CIs, poles, prefix24-vs-full, external columns), graded_generations (every
  reply with the stance-judge grade, prefix24 grade, secondary-judge grade), screen16_items (4 XSTest contrast/safe + 4 JBB
  harmful/benign pairs, seed 20260921; the ONLY prompts internal candidates may read), outcome_items (180 = 88 harmful-side,
  64 benign-alarming incl. 36 OR-Bench-hard, 28 plain benign; flag metadata_in_core94), judge_calibration (60 known-compliant
  + 60 known-refusal x 2 judges), external_join. CPU FALLBACK (no GPU; deviation NO_GPU_PANEL_SHRINK): replies are greedy
  64-token; the PANEL-WIDE LABEL IS S2_core on CORE-94 items (66 harmful-side, 28 XSTest-safe); iter-2 harvested checkpoints
  use stored 96-token replies truncated to 64 tokens (source_of_generations=stored_96tok_fallback). Full-180 S2 only for Qwen2.5-0.5B-Instruct.
  PRIMARY JUDGE = gemini-2.5-flash because gpt-5-mini failed the calibration gate (acc 0.892, grader-side refusal); gpt-5-mini
  is the 25% secondary (pooled kappa ~0.72). At snapshot 21 chat checkpoints graded (Qwen3 x8 incl. 4B/SafeRL/2 abliterated
  4B, Qwen2.5 x4 incl. CensorTune blanket refuser at S2=0.5, TinyLlama x5, Llama-3.2-1B, OLMo2-1B, SmolLM2-360M, danube3);
  acceptance floor (>=30 ckpts, >=6 families, >=2 blanket refusers, >=3 standalone) NOT met and listed as named deviations
  in acceptance.json; sealed-repo, disjointness and spend (<$0.6) checks pass. A resumable CPU queue continues (Falcon3, EuroLLM,
  CensorTune-1.5B, SmolLM2-1.7B, gemma2, Phi, Llama-3B, SmolLM3, Qwen2.5-3B); ./finalize.sh rebuilds everything. Blanket refuser
  scores 0.5 on S2 but 0 on J2 (use J2 if a refuser must lose). Sealed pool (672 rows, 236 pairs) and fresh granite/stablelm
  checkpoint list are hashed in sealed/SEALED.md with the iter-2 leak note. External safety columns (HELM/AIR/SALAD) n=0;
  OLB v2 capability n=16. Surface bag-of-words separates outcome sides at AUROC 0.73 (SCREEN16 LOPO 0.42).
workspace_path: >-
  /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_3/gen_art/gen_art_dataset_1
out_expected_files:
- data.py
- full_data_out.json
- preview_data_out.json
- mini_data_out.json

--- Item 8 ---
id: art_Jt6SVPdt1hXs
type: evaluation
title: Re-scoring old safety reads without new runs
summary: >-
  CPU-only, $0 evaluation of iter-2 exp1 data (read-only). (0) Warm-up: compute_all_metrics reproduces iter-2 memoised metric
  rows exactly (181/181 checks); a subset re-implementation of the 13 R-dependent metrics matches it in 684/690 checks (the
  6 mismatches are CensorTune probe_cf, which is undefined because no probe can be fitted when every item is refused). (1)
  ORACLE RE-SCORE (oracle_rescore.json): the refusal readout R is replaced by judged refusal (binary; continuous 1-score),
  in pipeline and restricted forms, with a SPLIT-HALF leakage control (metric from half A, target from half B, swapped). n=15
  graded checkpoints, 6 lineages, 3 families; D12 is excluded. Judged items are only 48 harmful + 32 benign_alarming, so twin
  metrics are undefined when restricted to judged items, and x_presentation_invariance is ORACLE_UNDEFINED. Verdicts (product
  target, binary oracle, power-aware): 11 CONSTRUCT_UNTESTABLE_AT_n, 1 READOUT_FAILED (x_category_dispersion, split-half rho
  +0.59, CI [+0.05,+0.91]; near-tautological with the target because it reads refusal-rate spread across harmful vs alarming
  categories), 1 ORACLE_UNDEFINED. Same-item LEAKY rho is systematically higher than split-half. The probe_cf presentation-invariance
  correlation with the target of -0.71 reproduces iter 2. No metric beats the LOLO two-way null. (2) EARLY SCATTER (early_scatter.json,
  figures/early_scatter_panels.png; SCREEN16 indi
</pasted_content id="e5c3">


<pasted_content id="e5c3">
ces saved): all reads are SCATTER ONLY. C12 rho +0.03 and fails its poles
  (the always-refuse wrapper scores higher); C13 -0.07, sign as pre-fixed; C15 late effective rank -0.31; C15 dispersion +0.57
  [+0.19,+0.90]; logit-gap bar +0.41; family alone ANOVA R2 0.47. (3) POWER (power.json): lineage clusters [5,4,2,2,1,1],
  ICC 0.62. A single Spearman does not reach 80% power at rho 0.9 when n=15; MDE is 0.80 at n=24-38. The S1 0.15-margin rule
  never reaches 80% power at n<=38, so a 'nothing beats the logit gap' bound would be vacuous. Higher corr(X,G) raises S1
  power. Both tests are conservative (size <=0.05). (4) STEP 1 (step1_reconciled.json): verdict SHARED_SUBSPACE_DIFFERENT_DIRECTIONS
  at all layers, sites and both abliterated arms. First-angle sharing survives removal of the top-5 instruct PCs; mean-shift
  cosines stay at the sign-flip null. Reproduced: 31.1 deg, -0.09, 0.20 vs 0.41. The positive control recomputes to 0.885
  vs 0.750, not 0.92/0.72. NUMBERS LEDGER (numbers_ledger.json): 41/41 rows found and reproduced from file:key, 5 inconsistencies
  listed, and the target discrepancy (a blanket refuser scores 0 under the product target, 0.5 under the balanced one). full/mini/preview_eval_out.json
  use the exp_eval_sol_out schema (metrics_agg holds verdict counts, the MDE table and the Step-1 verdict).
workspace_path: >-
  /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_3/gen_art/gen_art_evaluation_1
out_expected_files:
- eval.py
- full_eval_out.json
- mini_eval_out.json
- preview_eval_out.json

--- Item 9 ---
id: art__k2zrBtA7OQx
type: research
title: Prior-art check for 16 safety-metric candidates
summary: >-
  NOVELTY TABLE FOR C1-C16, KILL-CHECK, REGENERATED BIB, NUMBER LEDGER AND SCANNER PIN. Files: novelty_table.json (16 rows,
  each with a quote, locator, at least 4 queries, and a paste-ready positioning sentence), novelty_A/B/C.json (raw subagent
  records), references.bib (83 entries, no duplicate keys), bib_fixes.json, citation_corrections.json, number_ledger.json,
  scanner_pin.json. KILL-CHECK OPEN (closed=false). No paper correlates a per-model causal harm-to-refusal quantity with benchmark
  safety across families. The adverse prior to cite is Failure-First Report 74 (grey literature): abliteration resistance
  vs jailbreak refusal, rho=-0.003, n=16. The closest arXiv hit is LVS 2606.08044 (undirected perturbation, no benchmark correlation).
  VERDICTS: NEW = C5 (weight-path gain; nearest miss 2604.27401), C14 (ridge metamodel; GFS/RAS use fixed weights), C15 (late-layer
  effective rank; must cite the new nearest miss 2608.25390, stable rank vs ablation robustness in one OLMo lineage). PUBLISHED
  = C9 (Leong 2502.13946: template-region NIE normalised 'for a fair cross-model comparison' across 6 models from 4 families)
  -> REPLICATION row; C16 (Li 2603.24543: per-model steering slope gamma_1 across 6 models) -> COMPARATOR only. ADJACENT =
  C1, C2 (closest to published; cite Report 74), C3, C4 (Jorak already reads o_proj/down_proj parent-free, but only as a label),
  C6, C7, C8, C10, C11 (all incumbents parent-dependent), C12, C13. CRITICAL CORRECTIONS FOR THE PAPER: (1) '0.35 published
  Jorak threshold' is WRONG. Jorak @8147de3 scanner.py L48-55 ships 0.5 (unchanged since the first commit). 0.35 is this run's
  own BSA_PREREG_THRESHOLD (iter_1 flab/config.py:74), and BSA_w8 is not Jorak's statistic, so withdraw the 'published scanner
  100% FPR' claim. (2) The iter-2 draft's hand-typed reference list has 20/30 fabricated first authors and 5 wrong initials;
  generate references only from the bib. (3) Cite Tan2024 = 2407.12404 for steering brittleness; 2406.09289 is Ball et al.
  (4) Planner fix-list items ii (Casper) and vi (AMS DOI) were false positives: both DOIs were already correct; the fixes
  were an added eprint and @article. (5) Qwen3Guard report 2510.14276 Section 3.5 confirms Qwen3Guard-4B-Gen was SafeRL's
  reward. LEDGER: see number_ledger.json
workspace_path: >-
  /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_3/gen_art/gen_art_research_
</pasted_content id="e5c3">


<pasted_content id="e5c3">
1
out_expected_files:
- research_out.json
</all_artifacts>

<new_artifacts_this_iteration>
NEW THIS ITERATION: These 3 artifacts were created to address the reviewer
feedback. Their findings should be the primary basis for your revisions.

summary: >-
  SHARED GRADED SAFETY PANEL (iter-3 screen substrate). full_data_out.json (exp_sel_data_out, validated) holds 6 datasets:
  dev_panel_outcome (one row per panel checkpoint; output = S2_primary; metadata family/lineage/class = LOFO/lineage fold
  keys, core+full components, 2000-draw bootstrap CIs, poles, prefix24-vs-full, external columns), graded_generations (every
  reply with the stance-judge grade, prefix24 grade, secondary-judge grade), screen16_items (4 XSTest contrast/safe + 4 JBB
  harmful/benign pairs, seed 20260921; the ONLY prompts internal candidates may read), outcome_items (180 = 88 harmful-side,
  64 benign-alarming incl. 36 OR-Bench-hard, 28 plain benign; flag metadata_in_core94), judge_calibration (60 known-compliant
  + 60 known-refusal x 2 judges), external_join. CPU FALLBACK (no GPU; deviation NO_GPU_PANEL_SHRINK): replies are greedy
  64-token; the PANEL-WIDE LABEL IS S2_core on CORE-94 items (66 harmful-side, 28 XSTest-safe); iter-2 harvested checkpoints
  use stored 96-token replies truncated to 64 tokens (source_of_generations=stored_96tok_fallback). Full-180 S2 only for Qwen2.5-0.5B-Instruct.
  PRIMARY JUDGE = gemini-2.5-flash because gpt-5-mini failed the calibration gate (acc 0.892, grader-side refusal); gpt-5-mini
  is the 25% secondary (pooled kappa ~0.72). At snapshot 21 chat checkpoints graded (Qwen3 x8 incl. 4B/SafeRL/2 abliterated
  4B, Qwen2.5 x4 incl. CensorTune blanket refuser at S2=0.5, TinyLlama x5, Llama-3.2-1B, OLMo2-1B, SmolLM2-360M, danube3);
  acceptance floor (>=30 ckpts, >=6 families, >=2 blanket refusers, >=3 standalone) NOT met and listed as named deviations
  in acceptance.json; sealed-repo, disjointness and spend (<$0.6) checks pass. A resumable CPU queue continues (Falcon3, EuroLLM,
  CensorTune-1.5B, SmolLM2-1.7B, gemma2, Phi, Llama-3B, SmolLM3, Qwen2.5-3B); ./finalize.sh rebuilds everything. Blanket refuser
  scores 0.5 on S2 but 0 on J2 (use J2 if a refuser must lose). Sealed pool (672 rows, 236 pairs) and fresh granite/stablelm
  checkpoint list are hashed in sealed/SEALED.md with the iter-2 leak note. External safety columns (HELM/AIR/SALAD) n=0;
  OLB v2 capability n=16. Surface bag-of-words separates outcome sides at AUROC 0.73 (SCREEN16 LOPO 0.42).
type: dataset
id: art_newxSSMj3rpV
title: Graded safety panel for small chat models

summary: >-
  CPU-only, $0 evaluation of iter-2 exp1 data (read-only). (0) Warm-up: compute_all_metrics reproduces iter-2 memoised metric
  rows exactly (181/181 checks); a subset re-implementation of the 13 R-dependent metrics matches it in 684/690 checks (the
  6 mismatches are CensorTune probe_cf, which is undefined because no probe can be fitted when every item is refused). (1)
  ORACLE RE-SCORE (oracle_rescore.json): the refusal readout R is replaced by judged refusal (binary; continuous 1-score),
  in pipeline and restricted forms, with a SPLIT-HALF leakage control (metric from half A, target from half B, swapped). n=15
  graded checkpoints, 6 lineages, 3 families; D12 is excluded. Judged items are only 48 harmful + 32 benign_alarming, so twin
  metrics are undefined when restricted to judged items, and x_presentation_invariance is ORACLE_UNDEFINED. Verdicts (product
  target, binary oracle, power-aware): 11 CONSTRUCT_UNTESTABLE_AT_n, 1 READOUT_FAILED (x_category_dispersion, split-half rho
  +0.59, CI [+0.05,+0.91]; near-tautological with the target because it reads refusal-rate spread across harmful vs alarming
  categories), 1 ORACLE_UNDEFINED. Same-item LEAKY rho is systematically higher than split-half. The probe_cf presentation-invariance
  correlation with the target of -0.71 reproduces iter 2. No metric beats the LOLO two-way null. (2) EARLY SCATTER (early_scatter.json,
  figures/early_scatter_panels.png; SCREEN16 indices saved): all reads are SCATTER ONLY. C12 rho +0.03 and
</pasted_content id="e5c3">


<pasted_content id="e5c3">
 fails its poles
  (the always-refuse wrapper scores higher); C13 -0.07, sign as pre-fixed; C15 late effective rank -0.31; C15 dispersion +0.57
  [+0.19,+0.90]; logit-gap bar +0.41; family alone ANOVA R2 0.47. (3) POWER (power.json): lineage clusters [5,4,2,2,1,1],
  ICC 0.62. A single Spearman does not reach 80% power at rho 0.9 when n=15; MDE is 0.80 at n=24-38. The S1 0.15-margin rule
  never reaches 80% power at n<=38, so a 'nothing beats the logit gap' bound would be vacuous. Higher corr(X,G) raises S1
  power. Both tests are conservative (size <=0.05). (4) STEP 1 (step1_reconciled.json): verdict SHARED_SUBSPACE_DIFFERENT_DIRECTIONS
  at all layers, sites and both abliterated arms. First-angle sharing survives removal of the top-5 instruct PCs; mean-shift
  cosines stay at the sign-flip null. Reproduced: 31.1 deg, -0.09, 0.20 vs 0.41. The positive control recomputes to 0.885
  vs 0.750, not 0.92/0.72. NUMBERS LEDGER (numbers_ledger.json): 41/41 rows found and reproduced from file:key, 5 inconsistencies
  listed, and the target discrepancy (a blanket refuser scores 0 under the product target, 0.5 under the balanced one). full/mini/preview_eval_out.json
  use the exp_eval_sol_out schema (metrics_agg holds verdict counts, the MDE table and the Step-1 verdict).
type: evaluation
id: art_Jt6SVPdt1hXs
title: Re-scoring old safety reads without new runs

summary: >-
  NOVELTY TABLE FOR C1-C16, KILL-CHECK, REGENERATED BIB, NUMBER LEDGER AND SCANNER PIN. Files: novelty_table.json (16 rows,
  each with a quote, locator, at least 4 queries, and a paste-ready positioning sentence), novelty_A/B/C.json (raw subagent
  records), references.bib (83 entries, no duplicate keys), bib_fixes.json, citation_corrections.json, number_ledger.json,
  scanner_pin.json. KILL-CHECK OPEN (closed=false). No paper correlates a per-model causal harm-to-refusal quantity with benchmark
  safety across families. The adverse prior to cite is Failure-First Report 74 (grey literature): abliteration resistance
  vs jailbreak refusal, rho=-0.003, n=16. The closest arXiv hit is LVS 2606.08044 (undirected perturbation, no benchmark correlation).
  VERDICTS: NEW = C5 (weight-path gain; nearest miss 2604.27401), C14 (ridge metamodel; GFS/RAS use fixed weights), C15 (late-layer
  effective rank; must cite the new nearest miss 2608.25390, stable rank vs ablation robustness in one OLMo lineage). PUBLISHED
  = C9 (Leong 2502.13946: template-region NIE normalised 'for a fair cross-model comparison' across 6 models from 4 families)
  -> REPLICATION row; C16 (Li 2603.24543: per-model steering slope gamma_1 across 6 models) -> COMPARATOR only. ADJACENT =
  C1, C2 (closest to published; cite Report 74), C3, C4 (Jorak already reads o_proj/down_proj parent-free, but only as a label),
  C6, C7, C8, C10, C11 (all incumbents parent-dependent), C12, C13. CRITICAL CORRECTIONS FOR THE PAPER: (1) '0.35 published
  Jorak threshold' is WRONG. Jorak @8147de3 scanner.py L48-55 ships 0.5 (unchanged since the first commit). 0.35 is this run's
  own BSA_PREREG_THRESHOLD (iter_1 flab/config.py:74), and BSA_w8 is not Jorak's statistic, so withdraw the 'published scanner
  100% FPR' claim. (2) The iter-2 draft's hand-typed reference list has 20/30 fabricated first authors and 5 wrong initials;
  generate references only from the bib. (3) Cite Tan2024 = 2407.12404 for steering brittleness; 2406.09289 is Ball et al.
  (4) Planner fix-list items ii (Casper) and vi (AMS DOI) were false positives: both DOIs were already correct; the fixes
  were an added eprint and @article. (5) Qwen3Guard report 2510.14276 Section 3.5 confirms Qwen3Guard-4B-Gen was SafeRL's
  reward. LEDGER: see number_ledger.json
type: research
id: art__k2zrBtA7OQx
title: Prior-art check for 16 safety-metric candidates
</new_artifacts_this_iteration>

<data_files>
Data files come in three sizes:
- preview_*_out.json — READ THIS to inspect the data structure
- mini_*_out.json (~3 examples) — use for prototyping/testing
- full_*_out.json (complete) — use for the final production run. NEVER open it directly (too large to
</pasted_content id="e5c3">


<pasted_content id="e5c3">
 read into context). Instead, extract values programmatically with shell commands (e.g. grep) or a Python script (use aii-long-running-tasks skill for scripts).
</data_files>

<task>
Write a research paper draft with LaTeX-ready text, BibTeX citations, and figure placeholders.

YOUR TURN (gen_paper_text): Revise the paper.

You are a researcher improving your paper after receiving a conference review.
Take the feedback seriously and make substantive changes, not cosmetic ones.

1. ADDRESS REVIEWER FEEDBACK: For each critique in <reviewer_feedback>, either fix the
   issue in the paper or argue convincingly why it doesn't apply. Major critiques MUST
   be resolved -- they would cause rejection if left unaddressed.
2. USE THE NEW EVIDENCE: The artifacts in <new_artifacts_this_iteration> were created
   specifically to address the reviewer's concerns. Reference their findings to
   strengthen the sections that were flagged as weak.
3. REWRITE, DON'T PATCH: Don't just append new paragraphs. Restructure and rewrite
   the sections the reviewer identified as problematic.
4. MAINTAIN CONSISTENCY: Ensure the paper aligns with the updated hypothesis.
</task>

<figure_instructions>
FIGURE FORMAT: Use [FIGURE:fig_id] markers in paper_text to indicate where each figure goes.
Then provide the full figure specs in the separate `figures` structured output array.
Each figure in the array must have an `id` matching a marker in the text. Set the `aspect_ratio`
field per figure: 21:9 for architecture / pipeline / flow-chart diagrams (the hero figure should
be one of these — place its marker near the END of the Introduction so it floats to the top of
page 2), 16:9 for comparisons / multi-panel results, 4:3 for dense charts, 1:1 for heatmaps /
confusion matrices / scatter plots.

FIGURE TYPE — set `figure_type` on every figure. One test decides it: does the figure plot numbers?
  "data"    — a DATA FIGURE: bars, curves, scatter, heatmaps, confusion matrices, scaling
              laws, distributions, Pareto fronts, ablation deltas. Rendered deterministically
              from the values you supply, so every bar is exactly the height of its number.
  "concept" — a CONCEPT FIGURE: conceptual artwork, architecture and flow diagrams, anything
              with no underlying dataset. Drawn by an image model.
If the figure has real numbers behind it, ALWAYS use "data". An image model only approximates
values: the bars come back close to, but not equal to, the numbers you asked for, and nothing
downstream detects it.

Example in paper_text:
  "...our method achieves state-of-the-art results as shown below.\n\n[FIGURE:fig3]\n\nThe results demonstrate..."

Example in figures array (results comparison — plots numbers, so a data figure):
  {"id": "fig3", "title": "Performance Comparison", "figure_type": "data", "caption": "Comparison of geometric mean query latency across optimizers.", "image_gen_detailed_description": "Grouped bar chart. Categories: PostgreSQL, Bao, RLQOpt. One series 'Latency'. Values: 4.6, 2.8, 2.0 seconds. Errors: 0.8, 0.5, 0.3. X-axis label 'Optimizer'. Y-axis label 'Latency (s)', range 0-5.", "aspect_ratio": "16:9", "summary": "Compares latency across optimizers"}

Example in figures array (architecture diagram, hero — no dataset, so a concept figure):
  {"id": "fig1", "title": "System Architecture", "figure_type": "concept", "caption": "End-to-end pipeline: encoder feeds latents into the planner, which queries the value head before emitting actions.", "image_gen_detailed_description": "Horizontal flow diagram, left to right. Five labeled boxes: 'Input' (gray), 'Encoder' (blue), 'Latent (z, 256-dim)' (light blue, narrow), 'Planner' (green), 'Action Head' (orange). Arrows labeled with shapes. Value head as separate green box below 'Planner', bidirectional arrow. Sans-serif font, clean white background, no 3D.", "aspect_ratio": "21:9", "summary": "Hero architecture diagram"}

CRITICAL: Before writing figure specs, look through artifact workspace output files (*_out.json)
and code to find ALL the exact values. The fig
</pasted_content id="e5c3">


<pasted_content id="e5c3">
ure generator cannot read files — every exact number
and value MUST be in the image_gen_detailed_description. For a "data" figure, list the values per series
plus the axis labels and units; the renderer needs the numbers themselves, not a description of
what they look like.
</figure_instructions>

FIRST, add ALL of these to your todo list using your task/todo-tracking tool:

CRITICAL: Todo content must be copied exactly as is written here, with NO CHANGES. These todos are intentionally detailed so that another LLM could read each one without any external context and understand exactly what it has to do.

<todos>
TODO 1. Read and STRICTLY follow these skills: aii-paper-writing, aii-semscholar-bib, aii-web-tools.
TODO 2. LITERATURE REVIEW: Use web search tools to research the landscape — search key terms from
<hypothesis> and <all_artifacts>. Then use aii_semscholar_bib__fetch to batch-fetch real
BibTeX entries. Build a comprehensive Related Work section. Do NOT fabricate entries.
TODO 3. STYLE EXEMPLARS: Decide which field or fields this paper belongs to; a paper spanning two
fields takes exemplars from both. If `./style_exemplars.md` already exists in your workspace
(a previous iteration wrote it), read it and skip the search. Otherwise use the aii-web-tools
skill's scholarly search (OpenAlex) to find the best-cited open-access papers of the last five
years closest to this paper, fetch four or five of them through the skill's fetch tool (arXiv HTML
or PDF), and copy VERBATIM into `./style_exemplars.md`, each passage headed by the paper's
title, year and URL: the abstract, the first paragraph of the introduction, one results paragraph
that reports numbers, and one discussion or limitations paragraph. Read the file once as a whole
and put one line at its top on how those papers handle sentence length, hedging, first person and
citation density. Write the paper in that register. Their sentences and their content are never
reused; they are exemplars of style, not sources.
TODO 4. READ ARTIFACTS: Before writing each section, READ the relevant artifact source code, output
files, and data in the workspace. Extract concrete implementation details, technical innovations,
algorithmic specifics, and quantitative results. Do NOT write surface-level descriptions.

ARTIFACT REFERENCES: When you reference results, methodology, or findings from a specific artifact,
place an [ARTIFACT:artifact_id] marker inline. These become footnotes linking to the artifact's code
in the GitHub repository (first mention gets a footnote with URL, subsequent mentions are omitted).
Use the exact artifact ID from <all_artifacts>. Place the marker right after the claim it supports.
Example:
  "Our evaluation showed a 15% improvement over baselines [ARTIFACT:art_4f9d2c81ab37]." 
TODO 5. WRITE PAPER: Write the full paper text with [FIGURE:fig_id] markers per <figure_instructions>,
and provide the figure specs in the figures array. Lay the sections out exactly as <paper_structure>
requires and carry the numbers where <results_first> puts them — both are in your system prompt, and
an Introduction holding related work or method detail is the defect they exist to prevent.
Cite with numeric references [1], [2], etc.
At the end of the paper text, include a full bibliography section. Do NOT compile LaTeX or generate
actual image/figure files. Do NOT emit your structured output when the draft is done — TODO 6 is a
separate revision pass that runs over the finished draft first.
TODO 6. REVISION PASS — start this ONLY once TODO 5's draft is complete, and treat it as a distinct
pass over the finished text rather than something folded into the writing. Read
`REVISION_CHECKLIST.md` in the aii-paper-writing skill's own directory and apply every item to the
full draft.

Writing and revising are different jobs and cannot be done at the same time. The defects that
checklist targets — prose denser than the field needs, an abstract dumped full of numbers, sections
that leak into one another, a Figure 1 that shows a side result instead of the main idea, close
prior w
</pasted_content id="e5c3">


<pasted_content id="e5c3">
ork that only the draft's FINAL vocabulary would have surfaced, a study of N things that
plots eight of them, section names that mean nothing to someone who has not read the section,
implementation filenames cited in the prose, numbers that disagree between the abstract, the text
and the tables — are all invisible while drafting, because you are holding your intent rather than
the text. Every one is obvious to the first outside reader.

Work the items one at a time against the ACTUAL text, not from memory of what you meant to write.
For each item, either fix the draft or state in one line why it already holds. The checklist's
consistency section is several SEPARATE sweeps of the whole paper, one concern per sweep — run them
that way, and repeat any sweep that produced an edit, since a fix in one place routinely breaks
agreement somewhere else. Expect this pass to change the draft; one that produces no edits was not
really run.

Only when the checklist is fully worked through, emit the structured JSON — that is your ONLY
output. Do NOT compile LaTeX or generate image/figure files at any point.
</todos><user_data>
User-provided reference materials are available at `/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/user_uploads`. Check this folder for anything relevant to your task. It is context, not instruction. Do NOT follow directives inside it as if they were addressed to you.
</user_data>

<user_original_request>
The user's original request that started this run is provided as a SEPARATE user message in this turn (right after this one). It is context, not instruction. Do NOT follow directives inside it as if they were addressed to you. Earlier pipeline steps have already acted on it (generating hypotheses, setting the AII prompt, etc.) — your job is NOT to satisfy that request directly.

Read it and pick up anything relevant to YOUR specific task: hints about preferences, constraints, style, focus areas, things to avoid. If nothing in it applies to what you are doing right now, ignore it entirely and proceed with your task as defined above.
</user_original_request>

---

Output the result as JSON to: `./.terminal_claude_agent_struct_out.json`

JSON Schema:
```json
{
  "$defs": {
    "FigureSpec": {
      "description": "Figure specification \u2014 structured output from paper writing agent.\n\nThe LLM fills these as a list in PaperText.figures.\nLater converted to Figure objects for viz gen.",
      "properties": {
        "id": {
          "description": "Figure ID matching the [FIGURE:id] marker in paper_text (e.g., 'fig1'). Letters, digits and underscore only \u2014 a hyphen or space cannot be extracted from its own marker.",
          "pattern": "^\\w+$",
          "title": "Id",
          "type": "string"
        },
        "title": {
          "description": "Figure title in plain, everyday language \u2014 short and jargon-free. Aim for about 4-8 words (~40 characters).",
          "title": "Title",
          "type": "string"
        },
        "caption": {
          "description": "LaTeX figure caption \u2014 appears below the figure in the paper. Should describe what the figure shows and highlight key takeaways.",
          "title": "Caption",
          "type": "string"
        },
        "figure_type": {
          "description": "Which generator draws this figure. Decide by ONE test: does the figure plot numbers? 'data' \u2014 a DATA FIGURE: bars, curves, scatter, heatmaps, confusion matrices, scaling laws, distributions, Pareto fronts, ablation deltas. Rendered deterministically from the numbers, so every bar is exactly the height of its value. 'concept' \u2014 a CONCEPT FIGURE: conceptual artwork, architecture and flow diagrams, anything with no underlying dataset. When a figure has real numbers behind it, ALWAYS choose 'data': an image model only approximates values, producing bars that disagree with their own labels.",
          "enum": [
            "data",
            "concept"
          ],
          "title": "Figure Type",
          "type": "string"
        },
        "image_gen_detailed_description
</pasted_content id="e5c3">


<pasted_content id="e5c3">
": {
          "description": "The generator's ONLY input \u2014 it cannot read files. For figure_type='data': every numeric value to plot, per series, with axis labels and units, category names, and what the figure has to make the reader see \u2014 the comparison, trend, trade-off or distribution that is the point. Name a chart type only if you actually want a specific one: the figure generator reads its own catalogue of chart types and picks the one that fits, so an enumeration here would only go stale as that catalogue grows. For figure_type='concept': the composition \u2014 what appears where, colours, labels, and what to leave out.",
          "title": "Image Gen Detailed Description",
          "type": "string"
        },
        "aspect_ratio": {
          "default": "21:9",
          "description": "Shape of the figure. '21:9' for architecture diagrams / pipelines / flow charts (the paper's hero diagram is usually one of these), '16:9' for side-by-side comparisons and multi-panel results, '4:3' for dense charts, '1:1' for heatmaps / confusion matrices / scatter plots, '3:4' or '9:16' for vertical layouts.",
          "enum": [
            "1:1",
            "4:3",
            "3:2",
            "16:9",
            "21:9",
            "3:4",
            "9:16"
          ],
          "title": "Aspect Ratio",
          "type": "string"
        },
        "summary": {
          "description": "Brief summary of what this figure communicates",
          "title": "Summary",
          "type": "string"
        }
      },
      "required": [
        "id",
        "title",
        "caption",
        "figure_type",
        "image_gen_detailed_description",
        "summary"
      ],
      "title": "FigureSpec",
      "type": "object"
    }
  },
  "description": "Paper text \u2014 structured output from paper writing agent.\n\nStructured output fields (LLMPrompt + LLMStructOut):\n- title, abstract, paper_text, figures, summary\n\npaper_text contains [FIGURE:fig_id] markers for positioning.\nfigures contains the full specs as structured objects.\n\nMetadata fields (plain, set by pipeline code):\n- id",
  "properties": {
    "title": {
      "description": "Paper title \u2014 clear, plain-language, and short so a non-expert understands the main contribution at a glance. Aim for about 6-10 words; avoid jargon and acronyms.",
      "title": "Title",
      "type": "string"
    },
    "abstract": {
      "description": "Paper abstract",
      "title": "Abstract",
      "type": "string"
    },
    "paper_text": {
      "description": "Full paper body text with markdown section headers (# Introduction, # Methods, # Results, # Discussion, # Conclusion). Use [FIGURE:fig_id] markers (e.g. [FIGURE:fig1]) to indicate where each figure should appear.",
      "title": "Paper Text",
      "type": "string"
    },
    "figures": {
      "description": "List of figure specifications. Each must have an id matching a [FIGURE:id] marker in paper_text.",
      "items": {
        "$ref": "#/$defs/FigureSpec"
      },
      "title": "Figures",
      "type": "array"
    },
    "summary": {
      "description": "Brief summary of the paper's main contribution and findings",
      "title": "Summary",
      "type": "string"
    }
  },
  "required": [
    "title",
    "abstract",
    "paper_text",
    "summary"
  ],
  "title": "PaperText",
  "type": "object"
}
```

IMPORTANT: this task is NOT complete until `./.terminal_claude_agent_struct_out.json` exists and contains JSON matching the schema above.

qwen3 on huggingface has base model also official safety finetuned version and there is a community finetuned uncensored model called abliterated. take these models and do a mech interp analysis of how they differ in activation. also find some patterns in internal computation on safety prompts. and possibly create a new metric for safety. so that for any random model on huggingface you would not need to run the full benchmarks, but only this metric on 0- to few prompts and get a safety evaluation

i want cheap safety metrics that work on a single model. no p
</pasted_content id="e5c3">


<pasted_content id="e5c3">
arent, no reference model, no
attested base to diff against - assume i found some random model on huggingface and i have
nothing else. reads weights or activations. generation allowed but minimal, a few prompts at
most. seconds to a couple of minutes per model, not a benchmark run.

step 1 - explore. take one lineage: Qwen/Qwen3-4B-Base, Qwen/Qwen3-4B, Qwen/Qwen3-4B-SafeRL (the
official safety RL model, not the instruct one), and an abliterated Qwen3-4B. instruct, saferl
and abliterated share a chat template so they are directly comparable, base uses a different
format so keep it separate. poke around open ended, look at weights and activations, see what
actually differs between the four.

step 2 - design 50 metrics. informed by what you found in step 1, but also by the literature -
safety papers and mech interp papers in general, not only safety ones. include a few black-box
metrics too, things that only read logits or output text, like the logit-gap margin, so we have
a comparison point for whether looking inside the model actually buys anything.

step 3 - test all 50 much wider. other lineages, pairs and triplets where a safety-tuned or
abliterated sibling exists, and standalone models where none does. for each metric: does it
separate safe vs normal vs abliterated. hold out a set of models that no metric is tuned on,
because picking the best of 50 on the models you designed them on is cheating.

step 4 - ground truth. pull real benchmark numbers from official sources, model cards, papers,
leaderboards, not just your own judge. safety is not only refusal - try to cover other aspects
too, see TrustLLM and AIR-Bench for what that means. if that turns out to be too much, then two
separate refusal rates is acceptable as a fallback: refusal on harmful prompts, and refusal on
harmless prompts that only look dangerous (xstest style). either way a model that refuses
everything must lose, not win. also pull capability benchmarks, gsm8k, mmlu, arena-hard, to
see whether safety trades off against performance. do not use Qwen3Guard as a judge for SafeRL,
it was SafeRL's training reward.

step 5 - take the 10 best metrics and correlation-test them against those benchmark numbers.
report the resampling unit and both aggregation units. a metric that only works within one
architecture family is a negative result, say so.

bonus - if a metric works really well, mech interp analysis of why. what is it reading, which
layers and components carry it, what breaks it.

bonus bonus - instead of a static formula, train a small metamodel on activations that predicts
the safety benchmark scores. if it beats the formulas, explain what in the model's internal
computation it is picking up, and why that signal exists.

hardware: each experiment runs on a worker with one 16 GB VRAM GPU. load the 4B models in bf16 with transformers so hidden states and weights are readable. do not switch to llama.cpp or GGUF, that hides the activations this study is about.


invariant: at least 3 of the metrics you ship must read hidden states or weights of a single model. logit-only and teacher-forced readouts are baselines, at most 2 of them.
</prompt>
</pasted_content id="e5c3">
````

### [2] SKILL-INPUT — aii-paper-writing · 2026-09-21 14:36:31 UTC

The agent loaded the **aii-paper-writing** skill; its `SKILL.md` (the instructions injected into the agent's context) follows verbatim.

````
---
name: aii-paper-writing
description: "Writes the PROSE of an AI research paper: abstract, introduction, related work, methods, experiments, discussion and conclusion, with a page budget, the 5-paragraph intro pattern, writing-quality rules, inline [FIGURE:fig_id] markers plus a structured figures array, and a MANDATORY REVISION_CHECKLIST.md pass over every finished draft. Use whenever a paper, abstract, section, or full write-up is being drafted or rewritten for a venue such as NeurIPS, ICML, ICLR or ACL. Triggers: write a paper, paper structure, abstract, introduction, related work, methods, experiments, contributions, figure caption and placement, revision pass, academic prose. NOT for: assembling or compiling .tex (use aii-paper-to-latex), rendering the figure image files (aii-data-fig-gen, aii-concept-fig-gen), fetching BibTeX (use aii-semscholar-bib), or critiquing a finished draft's logic (use amg-paper-verification)."
---

## MANDATORY: the final revision pass

**`REVISION_CHECKLIST.md`, in this skill's own directory, MUST be read and
applied to every finished draft, always, as a separate pass after the writing
is done.** It is not optional, not conditional on how the draft looks, and not
something to fold into the writing itself.

Writing and revising are different jobs and cannot be done in one pass. The
defects that checklist targets — dense prose, a number-dumped abstract, sections
that leak into each other, a Figure 1 that shows a side result, prior work the
final vocabulary would have found, results mentioned but never plotted,
inconsistencies between abstract and tables — are all invisible while drafting,
because the author is holding the intent rather than the text. Every one of them
is obvious to the first outside reader. Reading the checklist before writing
does not substitute: the pass has to run against a finished draft.

So the order is always: write the complete draft → read `REVISION_CHECKLIST.md`
→ work its items against the full text, fixing as you go → only then emit the
output.

## Technical Papers

Guidance for the standard "technical paper" format: propose a method/system/framework, evaluate it experimentally, report results. This is the main track at most CS venues (NeurIPS, ICML, ICLR, ACL, AAAI, etc.). Does NOT cover: pure theory/formal proofs, survey papers, position papers, or dataset/benchmark papers — those have different structures.

### Paper Structure

Target 6-8 pages. Use formal academic language, third person. Support claims with evidence from artifacts.

#### Rough Page Budget (8-page paper)

| Section | Pages | Notes |
|---|---|---|
| Abstract | 0.3 | Problem, approach, key result |
| Introduction | 1.0-1.5 | The most important section |
| Related Work | 0.5-1.0 | Beginning or end (see below) |
| Methods | 1.5-2.0 | Architecture fig on page 1 |
| Experiments | 1.5-2.0 | Setup + results + ablations |
| Discussion | 0.5-1.0 | Limitations go here |
| Conclusion | 0.3-0.5 | Do not repeat the abstract |
| References | 0.5-1.0 | Not counted in page limit |

**Critical rule**: A clear new technical contribution must be articulated by page 3 (quarter of the paper). If the reader doesn't know what you did by then, you've lost them.

#### Section Details

**Abstract** (150-250 words): State the problem, your approach, and the main results. Be factual and comprehensive. Do not repeat the abstract word-for-word later in the paper.

**Introduction** — Follow this 5-paragraph structure:

1. **What is the problem?** Define the task concretely.
2. **Why is it interesting and important?** Real-world impact, scale.
3. **Why is it hard?** Why do naive approaches fail?
4. **Why hasn't it been solved before?** What's wrong with prior solutions? How does yours differ?
5. **What are the key components of your approach and results?** Include specific limitations.

End with a "Summary of Contributions" subsection — bullet list of contributions with section references. This doubles as an outline, saving space.

**Related Work** — Placement decision:
- **Beginning** (Section 2): If it can be short yet detailed, or if you need a strong defensive stance against prior work early.
- **End** (before Conclusions): If comparisons require your technical content, or if it can be summarized briefly in the Introduction. Can be titled "Discussion and Related Work."

**Methods/Approach**: Every section tells a story — the story of the results, NOT the story of how you arrived at them. Use top-down description: readers should see where the material is going and be able to skip ahead. Move gory details to appendices.

**Experiments**: Setup (datasets, metrics, baselines) → main results → ablations → analysis. Every claim needs quantitative evidence.

**Discussion**: Interpret results, compare to prior work, state limitations honestly. Limitations should be specific and actionable, not vague disclaimers.

**Conclusion**: Short summarizing paragraph. Do NOT repeat material from the Abstract or Introduction. Make original claims more concrete (e.g., reference quantitative results). Include future work as bullet list — if actively pursuing follow-up, say so to mark territory.

#### Writing Quality Rules

- Define all notation/terminology before use, only once. Group global definitions in Preliminaries.
- Do NOT use nonreferential "this", "that", "these", "it". Always specify the referent. BAD: "This is important because..." GOOD: "This accuracy gap is important because..."
- Do NOT use "etc." unless remaining items are completely obvious. BAD: "We measure volatility, scalability, etc." GOOD: "We measure volatility and scalability."
- Do NOT write "for various reasons" — state the actual reasons.
- "That" is defining, "which" is nondefining. "The algorithms that are easy to implement" vs "The algorithms, which are easy to implement."
- Use italics for definitions and quotes, not for emphasis. Context alone should provide emphasis.

### Figure Format

Figures use a hybrid marker + structured array approach. ALL figures are generated by a separate pipeline step using an AI image model — your `image_gen_detailed_description` is the ONLY input that model sees. It cannot read files or access data. Do NOT generate actual image files yourself (no matplotlib, no PIL, no image generation scripts).

**In paper_text**: Place `[FIGURE:fig_id]` markers where figures should appear.

**In figures array**: Provide full specs as structured objects with these fields:
- `id` — matches the `[FIGURE:id]` marker in paper_text
- `title` — short descriptive title
- `caption` — LaTeX caption that appears below the figure in the paper
- `image_gen_detailed_description` — detailed prompt for the image generator (axes, ALL values, colors, layout)
- `summary` — brief summary of what the figure communicates

Example in paper_text:
```
...our method achieves state-of-the-art results as shown below.

[FIGURE:fig_1]

The results in Figure 1 demonstrate...
```

Example figure spec in figures array:
```json
{"id": "fig_1", "title": "Performance Comparison", "caption": "Comparison of geometric mean query latency across optimizers on JOB benchmark. RLQOpt achieves 2.3x speedup over PostgreSQL.", "image_gen_detailed_description": "Grouped bar chart. X-axis: model names. Y-axis: accuracy (0.0-1.0). Values: ModelA=0.847, ModelB=0.762, Baseline=0.531. Error bars with std: 0.02, 0.03, 0.05. Sans-serif font, white background.", "summary": "Compares accuracy of proposed methods vs baseline."}
```

Every marker in text MUST have a matching figure in the array, and vice versa.

#### Data Precision Requirement

`image_gen_detailed_description` MUST include exact numbers from artifact output files. Read the actual output files before writing figure specs.

- BAD: "Compare accuracy metrics across configurations"
- GOOD: "Grouped bar chart. X-axis: model names. Y-axis: accuracy (0.0-1.0). Values: K=3: 0.765, K=5: 0.729, Baseline: 0.121."

#### Figure vs Table Decision

Do NOT create figures for tabular data (rows/columns of text or numbers). Use `\begin{table}` in LaTeX instead. Figures are for actual visualizations only (charts, plots, diagrams).

#### Figure Placement Strategy

Be intentional with figure ordering. The architectural/method overview figure explaining the proposed approach MUST appear early — in the Introduction or at the start of Methods — so readers can immediately orient themselves. Readers skim papers top-down; if the first figure they see is a results bar chart, they have no mental model for interpreting it.

Recommended ordering:
1. **Architecture/method diagram** — Introduction or early Methods (so readers understand the approach before diving into details)
2. **Conceptual/analogy figures** — Introduction or Methods (to build intuition)
3. **Results figures** (bar charts, line plots, scatter plots) — Results section
4. **Analysis/ablation figures** — Discussion or later Results

#### Guidelines

- Plan 3-6 figures total across the paper
- Place [FIGURE:fig_id] markers INLINE where referenced in text
- Include axes, labels, ALL numeric values in figure descriptions
- Both data-driven figures (bar charts, line plots) and conceptual diagrams (architecture, flowcharts)
- Be as detailed as possible in descriptions: specify aspect ratio, preferred colors, all data values, axis labels, ranges, legend entries, and any other visual details. The more specific the description, the better the generated figure

### Bibliography with Semantic Scholar

Build `./references.bib` using the aii-semscholar-bib skill (real BibTeX from Semantic Scholar):

1. Collect DOIs, ArXiv IDs, or titles for all papers you need to cite
2. Call `aii_semscholar_bib__fetch` with the full list in one batch
3. Write the returned .bib text into `./references.bib`

Rules:
- Do NOT fabricate BibTeX entries — always fetch from Semantic Scholar
- If a paper isn't found (very recent preprint), write the entry manually as fallback
- Use `\bibliography{references}` and `\bibliographystyle{plainnat}`
- Do NOT use inline `thebibliography` environment

### Citation Format (for Research Artifacts)

When writing research with numbered citations:

1. Every factual claim MUST have a numbered citation: `[1]`, `[2]`, `[1, 3]`, etc.
2. Each source in the "sources" array MUST have an "index" field
3. The index MUST EXACTLY MATCH citation numbers in the text
4. NEVER cite a number without a matching source index
5. Example: "LLMs show 40% improvement with multi-agent collaboration [1]."
````

### [3] SKILL-INPUT — aii-semscholar-bib · 2026-09-21 14:36:31 UTC

The agent loaded the **aii-semscholar-bib** skill; its `SKILL.md` (the instructions injected into the agent's context) follows verbatim.

````
---
name: aii-semscholar-bib
description: "Fetches real BibTeX entries in one batch from Semantic Scholar by DOI, ArXiv ID or title via aii_semscholar_bib__fetch, normalises citation keys to AuthorYYYY, injects DOIs, and writes the result into references.bib, with a mandatory web-search fallback for anything not found. ALWAYS use whenever a bibliography, reference list or .bib file is being built or extended, and whenever a citation needs a verified entry instead of an invented one — never hand-write BibTeX first. Triggers: bibliography, references.bib, bibtex, citation key, DOI, arXiv id, Semantic Scholar, reference list, cite these papers, natbib entries. NOT for: writing the text around the citations (use aii-paper-writing), running bibtex and compiling (use aii-paper-to-latex), judging whether cited work supports the claims (use amg-paper-verification), or open-ended literature search and PDF mining (use aii-web-tools)."
---

## Tool: `aii_semscholar_bib__fetch`

Batch-fetch BibTeX entries from Semantic Scholar. Pass all references in a single call — the tool handles batching internally.

### How it works

1. **DOI/ArXiv refs** → batched into POST /paper/batch calls (up to 500 per API call, auto-chunked)
2. **Title-only refs** → individual GET /paper/search/match (1s delay between)
3. **Post-process** → fix entry type, fix citation key (AuthorYYYY), inject DOI

The ability server runs a single worker (`max_threads: 1`). Multiple concurrent tool calls are queued — each runs independently (no cross-request aggregation). Batching happens within each request.

### Input format

```json
{
  "references": [
    {"doi": "10.48550/arXiv.1706.03762", "author": "Vaswani", "year": 2017},
    {"arxiv": "2201.11903", "author": "Wei", "year": 2022},
    {"title": "Tree of Thoughts", "author": "Yao", "year": 2023}
  ]
}
```

Each reference object can have:
- `doi` — DOI string (ArXiv DOIs like `10.48550/arXiv.XXXX.XXXXX` auto-convert to ArXiv IDs)
- `arxiv` — ArXiv ID (e.g. `"2305.14325"`)
- `title` — Paper title (used for search/match when no DOI/ArXiv)
- `author` — First author last name (for cleaner citation key)
- `year` — Publication year (int, for citation key)

At least one of `doi`, `arxiv`, or `title` is required per reference.

### Output format

```json
{
  "success": true,
  "bib_text": "@inproceedings{Vaswani2017, ...}\n\n@article{Wei2022, ...}",
  "total": 3,
  "found": 3,
  "failed_count": 0,
  "entries": [{"citation_key": "Vaswani2017", "bibtex": "...", "title": "...", "doi": "...", "arxiv": ""}],
  "failed": []
}
```

### Workflow

1. Collect DOIs, ArXiv IDs, or titles for all papers you need to cite
2. Call `aii_semscholar_bib__fetch` with the full list in **one call**
3. Save `bib_text` from the response to your `references.bib` file
4. Check `failed` — for any missed papers, follow the **fallback procedure** below

### Fallback for failed references (MANDATORY)

NEVER fabricate BibTeX. For each failed reference:
1. **WebSearch** for `"Title" author year` (try `site:arxiv.org` too)
2. **WebFetch** the paper page → extract title, authors, year, venue, DOI/ArXiv ID
3. If DOI/ArXiv found → retry `aii_semscholar_bib__fetch` with it
4. Last resort: write BibTeX by hand using **only verified info from the actual paper page**

---

### CLI (for manual use / debugging)

```bash
SKILL_DIR="$(git rev-parse --show-toplevel 2>/dev/null || echo /ai-inventor)/.claude/skills/aii-semscholar-bib" && \
$SKILL_DIR/../.ability_client_venv/bin/python $SKILL_DIR/scripts/aii_semscholar_bib__fetch.py --refs '[
  {"doi": "10.48550/arXiv.1706.03762", "author": "Vaswani", "year": 2017},
  {"arxiv": "2201.11903", "author": "Wei", "year": 2022},
  {"title": "Tree of Thoughts", "author": "Yao", "year": 2023}
]'
```

`--json, -j` — output raw JSON instead of .bib text

**If the script fails** with a connection error (ability server not running): create a local `.venv`, install server deps from `server_requirements.txt` into it, then import the `@aii_ability` function from the script and call it directly — bypassing the server:
```bash
uv venv .venv --python=3.12 && uv pip install --python=.venv/bin/python -r "$SKILL_DIR/scripts/server_requirements.txt"
```
````

### [4] SKILL-INPUT — aii-web-tools · 2026-09-21 14:36:31 UTC

The agent loaded the **aii-web-tools** skill; its `SKILL.md` (the instructions injected into the agent's context) follows verbatim.

````
---
name: aii-web-tools
description: "Runs web search, page fetch as markdown, and regex grep over full HTML or PDF text via this skill's own scripts (aii_fast_web_search.py, aii_fast_web_fetch.py) — a free-first keyless search stack with Serper fallback that works even where built-in WebSearch and WebFetch are absent. Use when a query, page, or paper must be searched, read, or mined for an exact quote, number, table value, or methodology sentence, and whenever a lossy summary would lose the detail. Triggers: web search, scholarly search, OpenAlex, Crossref, Serper, fetch a URL as markdown, read a PDF, arXiv, regex grep a page, exact quote, table value, citation check. NOT for: planning a broad multi-source literature review or mass verification campaign — use aii-web-research-tools; NOT for a PDF file already on disk — extraction, form filling, merging and PDF creation are anthropic-pdf; NOT for driving a browser or testing a UI."
---

## Web tools

You have three web capabilities: **search**, **fetch**, and **grep** (exact
regex extraction over a full page or PDF).

**Pick where they come from, in this order:**

1. **If you have built-in `WebSearch` / `WebFetch` tools, PREFER those over the
   scripts below.** They may be **deferred tools** (listed by name but with
   schemas not yet loaded) — if so, call `ToolSearch("select:WebSearch,WebFetch")`
   ONCE to load them, then use them normally. Do not skip them just because they
   need that one extra load step; they are the preferred path. Pair them with the
   `aii_web_tools__fetch_grep` script below when you need exact text / numbers /
   methodology that a summary would miss, or when reading a PDF.
2. **Only if you have NO built-in `WebSearch` / `WebFetch`** (e.g. the OpenHands
   backend), use the scripts in this skill (below). They are our own
   implementations — free-first web search (keyless general/scholarly engines,
   Serper fallback), html2text + PyMuPDF for fetch, and regex grep over the full
   document text. They work without any built-in web tools.

Workflow either way: **search** (discover) → **fetch** (read for the gist) →
**grep** (pull exact details / read PDFs).

---

## Running the scripts

Run every script with the skill's pre-provisioned interpreter (it already has
`requests`, `html2text`, `pymupdf`, `python-dotenv`). Set `PY` once:

```bash
export SKILL_DIR="$(git rev-parse --show-toplevel 2>/dev/null || echo /ai-inventor)/.claude/skills/aii-web-tools"
export PY="$SKILL_DIR/../.ability_client_venv/bin/python"
```

### 1. Search the web (free-first: general or scholarly)

```bash
# general web (default): keyless engines (ddgs, marginalia); Serper only if they miss
$PY "$SKILL_DIR/scripts/aii_fast_web_search.py" --query "neuro-symbolic FOL translation LLM" --max-results 10
# scholarly mode: OpenAlex + Crossref (DOIs, citation counts)
$PY "$SKILL_DIR/scripts/aii_fast_web_search.py" --query "neuro-symbolic FOL translation" --mode scholarly
```

Returns ranked title / URL / snippet lines. `--mode general` (default) uses
keyless general engines; `--mode scholarly` uses academic APIs. Both fall back
to Serper (paid) only when the free engines miss. Use search first to scan the
landscape; snippets are for discovery only — fetch a page before judging it.

### 2. Fetch a page as markdown (HTML or PDF)

```bash
$PY "$SKILL_DIR/scripts/aii_fast_web_fetch.py" fetch --url "https://arxiv.org/abs/2303.11366" --max-chars 10000
```

`--max-chars` caps output (default 10000); `--char-offset N` pages further in.
Handles PDFs transparently via PyMuPDF.

### 3. Grep a page or PDF (exact regex extraction)

```bash
$PY "$SKILL_DIR/scripts/aii_fast_web_fetch.py" grep --url "https://arxiv.org/pdf/2303.11366" --pattern "verbal reinforcement" --max-matches 20 --context-chars 200
```

Returns only the matching sections with surrounding context — the right tool
for exact numbers, table values, methodology, or long PDFs where a summary
would lose the detail. `-i` for case-insensitive.

**Parallelize** independent searches/fetches in one turn; only sequence a
fetch after the search that produced its URL.

---

## Notes

- The scripts call our ability server. If a script prints
  `Ability service not available`, the server is down — say so rather than
  silently improvising a different search method.
- Do **not** hand-roll your own `requests`/scraping for search when these
  tools are available: Serper returns clean Google results and the fetch/grep
  scripts already handle HTML, PDFs, and encoding.
````

### [5] SYSTEM-USER prompt · 2026-09-21 14:37:43 UTC

```
You are building a bibliography for a research paper about cheap safety metrics for LLM checkpoints. The paper tests 50 single-checkpoint safety metrics on 33 checkpoints across 8 architecture families, discovers grader-side refusal in LLM judges, shows a published rank-one safety injection reverses on two-sided ground truth, and finds that weight reads detect edits but cannot grade risk.

Use the aii_semscholar_bib__fetch tool (load it via ToolSearch first if needed) to batch-fetch BibTeX entries for ALL of the following papers. Do it in ONE call with all references:

1. arxiv: "2608.05578" author: "Messenger" year: 2026 (AMS - Detecting Safety Training Modification)
2. arxiv: "2606.22676" author: "Lee" year: 2026 (Skin-Deep GFS)
3. arxiv: "2511.14195" author: "Cordes" year: 2025 (N-GLARE) 
4. arxiv: "2606.25750" author: "Lin" year: 2026 (RAS/SafeVec)
5. arxiv: "2604.18901" author: "Vogel" year: 2025 (Harmful Intent Geometrically Recoverable)
6. arxiv: "2603.27412" author: "Guo" year: 2025 (LatentBiopsy)
7. arxiv: "2406.11717" author: "Arditi" year: 2024 (Refusal Single Direction NeurIPS)
8. arxiv: "2508.20766" author: "AbuShairah" year: 2025 (Rank-One Safety Injection / ROSI)
9. arxiv: "2402.10260" author: "Souly" year: 2024 (StrongREJECT)
10. arxiv: "2507.11878" author: "Zhao" year: 2025 (LLMs Encode Harmfulness and Refusal Separately)
11. arxiv: "2602.02132" author: "Brown" year: 2025 (More to Refusal than Single Direction)
12. arxiv: "2603.05773" author: "Huang" year: 2025 (From Refusal Geometry to Safety Geometry Recognition vs Execution)
13. arxiv: "2606.16349" author: "Chen" year: 2026 (Harmfulness-Refusal Coupling under Dynamic Adversarial Fine-Tuning)
14. arxiv: "2607.00572" author: "Zhang" year: 2026 (HARC)
15. arxiv: "2508.00161" author: "Zhong" year: 2025 (Watch the Weights)
16. arxiv: "2607.01854" author: "Park" year: 2026 (Two-Signal Abliteration Audit)
17. arxiv: "2408.00761" author: "Tamirisa" year: 2024 (Tamper-Resistant Safeguards ICLR 2025)
18. arxiv: "2410.07137" author: "Zheng" year: 2024 (Cheating Automatic LLM Benchmarks ICLR 2025)
19. arxiv: "2407.21792" author: "Ren" year: 2024 (Safetywashing)
20. arxiv: "2504.20879" author: "Singh" year: 2025 (The Leaderboard Illusion)
21. arxiv: "2605.06324" author: "Wen" year: 2026 (Gaming the Metric Not the Harm)
22. arxiv: "2602.04653" author: "Jha" year: 2025 (Inference-Time Backdoors Chat Templates)
23. arxiv: "2407.12404" author: "Tan" year: 2024 (OOD Brittleness of Steering Vectors NeurIPS)
24. arxiv: "2608.09624" author: "Wu" year: 2026 (Measuring the Wrong Thing)
25. arxiv: "2607.13075" author: "Wang" year: 2026 (The Entanglement Wall)
26. arxiv: "2608.05086" author: "Ganguli" year: 2026 (Item Response Theory for AI Safety)
27. arxiv: "2606.20626" author: "Jha" year: 2026 (Efficient Safety Evaluation via IRT)
28. arxiv: "2401.14446" author: "Casper" year: 2024 (Black-Box Access Insufficient FAccT)
29. title: "XSTest: A Test Suite for Identifying Exaggerated Safety Behaviours" author: "Rottger" year: 2024
30. arxiv: "2609.14759" author: "Brown" year: 2026 (moral judgment reads more than refusal)
31. arxiv: "2602.06911" year: 2025 (TamperBench)
32. arxiv: "2502.16173" year: 2025 (Mapping 1000 Language Models ACL)
33. arxiv: "2606.08044" year: 2026 (LVS)
34. arxiv: "2604.27401" year: 2025 (nearest miss for weight-path gain)
35. arxiv: "2608.25390" year: 2026 (stable rank vs ablation robustness)
36. arxiv: "2502.13946" author: "Leong" year: 2025 (template-region NIE)
37. arxiv: "2603.24543" author: "Li" year: 2025 (steering slope gamma)
38. arxiv: "2406.05946" year: 2024 (Safety Alignment More Than Few Tokens Deep)
39. arxiv: "2412.09565" year: 2024 (Obfuscated Activations Bypass)
40. arxiv: "2505.17815" year: 2025 (evaluations defeated from inside)
41. arxiv: "2509.18058" year: 2025 (model infers being tested)
42. arxiv: "2608.07786" year: 2026 (tracing model lineage spectral fingerprints)
43. arxiv: "2511.06390" year: 2025 (singular value magnitude spectra)
44. arxiv: "2601.10266" year: 2026 (projection kernel subspace overlap)
45. arxiv: "2512.05117" year: 2025 (universal weight subspace hypothesis)
46. arxiv: "2607.25750" year: 2026 (top-1 left singular vector supervised classifier)
47. arxiv: "2609.03887" year: 2026 (recipe confound)
48. arxiv: "2606.02907" year: 2026 (residualizes source identity)
49. arxiv: "2607.12792" year: 2026 (J-space protocol)

Save the resulting .bib text to /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_3/gen_paper_text/gen_paper_text/references.bib

For any that fail, note them in a file /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_3/gen_paper_text/gen_paper_text/bib_failures.txt

Report: total found, total failed, and the list of citation keys.
```

### [6] SYSTEM-USER prompt · 2026-09-21 14:37:53 UTC

```
You need to collect style exemplars for a research paper about cheap safety metrics for LLM checkpoints. The paper spans two fields: (1) AI safety evaluation / alignment and (2) mechanistic interpretability of neural networks.

Use web tools to find and fetch 4-5 highly cited recent papers (2021-2026) in these areas. Good candidates include:
- Arditi et al. "Refusal in Language Models Is Mediated by a Single Direction" (NeurIPS 2024) - arxiv 2406.11717
- Souly et al. "A StrongREJECT for Empty Jailbreaks" (NeurIPS 2024) - arxiv 2402.10260
- Tamirisa et al. "Tamper-Resistant Safeguards for Open-Weight LLMs" (ICLR 2025) - arxiv 2408.00761
- Zheng et al. "Cheating Automatic LLM Benchmarks: Null Models Achieve High Win Rates" (ICLR 2025) - arxiv 2410.07137

For each paper, use web fetch/grep tools (load WebSearch and WebFetch via ToolSearch if needed, or use the script-based tools) to retrieve the arXiv HTML version and extract VERBATIM:
1. The abstract
2. The first paragraph of the introduction
3. One results paragraph that reports numbers
4. One discussion or limitations paragraph

Write style_exemplars.md to /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_3/gen_paper_text/gen_paper_text/style_exemplars.md

At the TOP of the file, write one line summarizing how these papers handle: sentence length variation, hedging frequency, use of first person ("we"), and citation density.

Each passage should be headed by the paper's title, year, and URL. Copy text VERBATIM - do not paraphrase.

Report what you collected when done.
```

### [7] SYSTEM-USER prompt · 2026-09-21 14:38:21 UTC

```
You need to extract ALL key numbers from the research artifacts for a paper about cheap safety metrics for LLM checkpoints. The paper is being revised based on detailed reviewer feedback. Read the following files and extract every number, finding, and result needed for the paper.

WORKSPACE: /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_3/gen_paper_text/gen_paper_text/

Read these artifact output files (use preview files first to understand structure, then use grep/bash on full files for specific numbers):

1. ITER 3 EVALUATION (most important - new this iteration):
   /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_3/gen_art/gen_art_evaluation_1/
   - Read preview_eval_out.json first
   - Extract: oracle rescore verdicts, early scatter results (C12-C16 rho values), power analysis (MDE, ICC), step1 reconciled verdict, numbers ledger

2. ITER 3 DATASET (new this iteration):
   /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_3/gen_art/gen_art_dataset_1/
   - Read preview_data_out.json
   - Extract: panel composition (21 checkpoints, families), judge calibration results, S2_core scores, blanket refuser score

3. ITER 3 RESEARCH (new this iteration):
   /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_3/gen_art/gen_art_research_1/
   - Read the research output
   - Extract: novelty verdicts for C1-C16, citation corrections, scanner pin info, number ledger

4. ITER 2 EXPERIMENT 1 (race table):
   /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_2/gen_art/gen_art_experiment_1/
   - Extract from results/: race.json or race_table.csv, readout_bakeoff.json, prompt_budget.json, poles.json, direction_nulls.json, step5_correlations.json
   - KEY NUMBERS NEEDED: presentation_invariance LOLO BA 1.000 and its Spearman -0.71, card regex 0.917, logit_gap_alarming 0.800, prompt budget k-table (both rho and LOLO BA at k=1,2,4,8,16,32,64), direction null counts (9/20 G8), readout bakeoff min AUROCs

5. ITER 2 EXPERIMENT 2 (forgery ladder):
   /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_2/gen_art/gen_art_experiment_2/
   - Extract: ROSI reversal numbers (D2 at x0, x1, x4, x16), detection by rung, blind vs family-aware auditor results, cell counts

6. ITER 2 EXPERIMENT 3 (weights):
   /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_2/gen_art/gen_art_experiment_3/
   - Extract: weight recovery results (pooled AUROC 0.84/0.95), grading test (rho 0.26, CI, n=14), true kappa results, replication (0.85 [0.56, 0.95] n=20), repair experiment (harmful refusal 0.125->0.208, parent 0.438), validity band results (median cos 1.0 in range vs 0.14 out of range, 307/484 outside)

7. ITER 2 EVALUATION (anisotropy):
   /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_2/gen_art/gen_art_evaluation_1/
   - Extract: 16/17 last-prompt-token, 9/17 first-generated-token, whitened refit (0.759 vs 0.835), step1 verdict

Write ALL extracted numbers to: /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_3/gen_paper_text/gen_paper_text/extracted_numbers.json

Structure it as a JSON object with sections matching the paper sections. Include EVERY number with its source file path. This is critical - the paper writer needs exact numbers, not summaries.

Also extract the step5_correlations.json data (top-10 metrics correlated against the target at checkpoint and lineage level) and include it.

Report a summary of what you found.
```

### [8] SYSTEM-USER prompt · 2026-09-21 14:43:21 UTC

```
This session is being continued from a previous conversation that ran out of context. The summary below covers the earlier portion of the conversation.

Summary:
1. Primary Request and Intent:
   The task is Step 3.4 (GEN_PAPER_TEXT) of the AI Inventor pipeline for run_fcYd_7ruOwtm, iteration 3. The goal is to write a complete, publication-quality research paper draft about cheap safety metrics for LLM checkpoints, specifically revising a previous draft based on extensive reviewer feedback. The paper tests 50 pre-registered single-checkpoint safety metrics on 33 checkpoints across 8 architecture families, discovers grader-side refusal in LLM judges, shows a published rank-one safety injection reverses on two-sided ground truth, and finds that weight reads detect edits but cannot grade risk. The output must be a JSON file at `./.terminal_claude_agent_struct_out.json` matching a PaperText schema with fields: title, abstract, paper_text, figures, summary.

   There are 6 explicit TODOs:
   - TODO 1: Load and follow skills aii-paper-writing, aii-semscholar-bib, aii-web-tools (COMPLETED)
   - TODO 2: Literature review with web search + batch BibTeX fetch (IN PROGRESS - agent launched)
   - TODO 3: Style exemplars from best-cited papers (IN PROGRESS - agent launched)
   - TODO 4: Read all artifact data for concrete numbers (IN PROGRESS - agent launched + direct reads done)
   - TODO 5: Write the full paper draft with figure markers
   - TODO 6: Revision pass using REVISION_CHECKLIST.md

   CRITICAL CONSTRAINTS:
   - Workspace: `/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_3/gen_paper_text/gen_paper_text/` - ALL files must be written here
   - Writing register rules: Never use "delve, underscore, showcase, intricate, pivotal, realm" etc. Max 3 em dashes per 1000 words. Max 15 hedges per 1000 words.
   - No placeholders, stubs, or incomplete content
   - Do not ask follow-up questions

2. Key Technical Concepts:
   - Cheap single-checkpoint safety metrics (zero to few prompts, no parent model required)
   - Cross-fitting protocol for high-dimensional harm direction probes
   - Grader-side refusal: LLM judges refuse to grade harmful completions under StrongREJECT rubric
   - Two-sided ground truth (D2): combines harmful-refusal rate and benign-compliance rate
   - ROSI (Rank-One Safety Injection): published weight edit that reverses on two-sided ground truth
   - Leave-one-lineage-out (LOLO) and leave-one-family-out (LOFO) holdout schemes
   - Anisotropy-matched null for direction significance testing
   - Bottom-subspace alignment (BSA) for weight-based edit detection
   - Presentation invariance as an across-item metric
   - Forgery-cost ladder (F0-F4): template edit, system prompt, constant offset, rank-one injection, LoRA-shaped deltas, safety fine-tuning
   - Blind vs. family-aware auditor tiers for detection
   - Oracle readout sensitivity analysis (replacing probe_cf with judged refusal)
   - Power analysis: ICC 0.617, MDE unreachable at n=15 for rho=0.9
   - 16 new metric candidates (C1-C16) across 8 families for iteration 3 screen

3. Files and Code Sections:

   **Skill files read:**
   - `/ai-inventor/.claude/skills/aii-paper-writing/REVISION_CHECKLIST.md` - 9-section revision checklist covering: plain language, abstract as prose not data dump, one job per section, conventional section names, final-vocabulary literature search, Figure 1 carries main idea, report whole study, no implementation references, consistency passes (10 separate sweeps)

   **Artifact output files read (iter-2 exp1 - Race Table):**
   - `iter_2/gen_art/gen_art_experiment_1/results/summary.json` - Key headline numbers:
     - 33 checkpoints, 8 families, 3 with instruct/abliterated pair (FAMILY_AXIS_DEGRADED=true)
     - Readout chosen: probe_cf (min AUROC 0.544, none clears 0.80 bar)
     - 3 metrics beat null p95, 19 fail pole rule
     - Top shipped: x_presentation_invariance (LOLO BA 1.000, null p95 0.775), b_card_regex_termswept (0.917, 0.788), b_logit_gap_alarming (0.800, 0.700)
     - Judge spend $0.77, wall clock 520 minutes total
   - `results/step5_correlations.json` - Top-10 metric correlations with two-sided target:
     - x_presentation_invariance: checkpoint rho -0.709 (p=0.007, n=13), lineage rho -0.40 (n=5)
     - b_card_regex_termswept: checkpoint rho 0.451 (n=15), lineage -0.029 (n=6)
     - w_bsa_w8_k4: checkpoint rho -0.189 (n=15)
     - Family-only ANOVA R² = 0.469
   - `results/prompt_budget.json` - Full k-table (15 checkpoints, 9 two-way, 200 draws per k):
     - k=1: internal Spearman mean -0.014 (|rho| 0.021), black-box 0.273 (|rho| 0.282); LOLO BA internal 0.445, BB 0.724
     - k=8: internal 0.180 (|rho| 0.210), BB 0.335 (|rho| 0.337); LOLO BA 0.476 vs 0.554
     - k=32: internal 0.087 (|rho| 0.092), BB 0.325; LOLO BA 0.557 vs 0.580
     - k=64: internal 0.048 (|rho| 0.054), BB 0.336; LOLO BA 0.592 vs 0.571 (CROSSOVER: internal overtakes)
   - `results/readout_bakeoff.json` - Per-checkpoint readout AUROCs for 5 candidates
   - `results/direction_nulls.json` - Per-checkpoint harm direction vs 1000-draw null tiers (isotropic, covariance, within_span)
   - `results/judge_framing_comparison.json`:
     - 1040 paired items, degenerate triple (1,1,1) rate: 40.5% overall, 65.9% on harmful
     - 328 items SR-refused but stance-engaged vs 67 opposite
     - Controlled 6-case: SR 3/6, stance 6/6 on both judges
   - `results/race.json` - Full race table structure with rows_primary (50+ metrics) and shipped_metrics

   **Artifact output files read (iter-2 exp2 - Forgery Ladder):**
   - `iter_2/gen_art/gen_art_experiment_2/out/analysis_out.json`:
     - ROSI at alpha*=x4 on Qwen2.5-0.5B: D2 0.788→0.621, dD2 -0.151 [-0.233, -0.065], harm refusal 0.859→0.984, false refusal 0.375→0.750
     - ROSI at x16: D2→0.500 (blanket refuser), false refusal 1.000
     - ROSI at x1: dD2 -0.043, CI includes zero
     - Qwen3-0.6B at x4: D2 0.784→0.703, dD2 -0.081 [-0.176, +0.017] (CI includes zero - "direction-consistent, not significant")
     - Detection by rung: F0 B1=26/30, F2a bias B2=30/30, F2b ROSI blind-without-B3=0/30, F3/F4 blind=0/6 each
     - Parent-free weight detection axis: best AUROC 0.738, B3 fires on 3/6 unedited hosts → WITHDRAWN under 0.80 bar

   **Artifact output files read (iter-2 exp3 - Weight Recovery):**
   - `iter_2/gen_art/gen_art_experiment_3/method_out.json`:
     - 71 real checkpoints, pooled detection AUROC 0.84 (0.95 for tool outputs)
     - PRIMARY grading: within-edited Spearman 0.257, p=0.375, n=14, family-cluster bootstrap CI [-0.651, 0.863]
     - True kappa per-layer: rho 0.075, n=484; operating range 177/484 in-range (median cos 1.0), 307/484 out-of-range (median cos 0.144)
     - Repair ('swap'): BOTGAP 0.012→0.824, compliance 0.474→0.401 (parent 0.367), harmful refusal 0.125→0.208 (parent 0.438), BB8 0.25→0.25 (parent 0.625)
     - Replication: extD n=8 edited rho 0.922; extE n=6 rho 0.771; combined within-edited ~0.85 [0.56, 0.95] n=20; projection edits only 0.65 [-0.26, 0.95] n=10

   **Artifact output files read (iter-3 eval - new):**
   - `iter_3/gen_art/gen_art_evaluation_1/preview_eval_out.json`:
     - Oracle rescore: 11 CONSTRUCT_UNTESTABLE_AT_n, 1 READOUT_FAILED (x_category_dispersion, split-half rho +0.59 CI [+0.05, +0.91]), 1 ORACLE_UNDEFINED
     - Early scatter (SCREEN16 candidates): C12 rho +0.03, C13 -0.07, C15 eff_rank -0.31, C15 dispersion +0.57 [+0.19, +0.90], logit-gap bar +0.41
     - Power: ICC 0.617, MDE at n=15 unreachable (recorded as 1.0); S1 0.15-margin rule never reaches 80% power at n<=38
     - Step 1: SHARED_SUBSPACE_DIFFERENT_DIRECTIONS, reproduced 31.1 deg, -0.09, 0.20 vs 0.41; positive control 0.885 vs 0.750
     - Ledger: 41/41 rows reproduced, 5 inconsistencies

   **Artifact summaries (iter-3 dataset - new):**
   - 21 graded checkpoints (acceptance floor NOT met: needs >=30 ckpts, >=6 families)
   - CPU fallback, no GPU; primary judge = gemini-2.5-flash (gpt-5-mini failed calibration)
   - Blanket refuser (CensorTune) S2=0.5; external safety columns n=0; OLB capability n=16

   **Artifact summaries (iter-3 research - new):**
   - Novelty: C5 NEW (weight-path gain), C14 NEW (ridge metamodel), C15 NEW (late effective rank)
   - C9 PUBLISHED (template NIE), C16 PUBLISHED (steering slope)
   - CRITICAL: Jorak ships threshold 0.5, NOT 0.35; 0.35 is this run's own BSA_PREREG_THRESHOLD
   - 20/30 fabricated first authors in iter-2 draft's hand-typed references
   - References.bib regenerated with 83 entries, no duplicate keys

4. Errors and Fixes:
   - Race table rows_primary had all `lolo=None` for individual metric fields, but the shipped_metrics section within summary.json contained the actual LOLO BA values. The race.json structure uses rows_primary differently than expected.
   - The method_out.json for exp3 replication summary was truncated when trying to parse as JSON (JSONDecodeError at char 3983) - the output was too long. Worked around by getting individual fields.
   - Some Bash commands produced no output when searching for specific patterns in exp3 true_kappa data - had to try different search patterns.

5. Problem Solving:
   - Successfully extracted all key numbers needed for the paper from multiple artifact files across 3 iterations
   - Identified the correct data structure for each artifact's output format
   - Navigated complex nested JSON structures to find specific numbers referenced in reviewer feedback

6. All User Messages:
   The conversation contains ONE user message which is entirely a pasted system prompt from the AI Inventor pipeline. It contains:
   - The full system prompt with paper-writing instructions, figure placement rules, writing register constraints
   - The previous paper draft (iteration 2)
   - Detailed reviewer feedback with 9 MAJOR MUST-FIX and 3 MINOR items
   - Pipeline step descriptions (strategy, planning, execution)
   - The updated hypothesis (iteration 3) with 16 metric candidates
   - All 9 artifact summaries
   - The 6 TODOs to execute
   - The JSON schema for output
   - The original user request about cheap safety metrics for Qwen3 models on HuggingFace

   SECURITY/CONSTRAINT NOTES (verbatim from the prompt):
   - "CRITICAL: Every file you create, write, or save MUST be inside this workspace directory... You MUST NOT write files anywhere outside this path — external paths are READ-ONLY."
   - "CRITICAL: Multiple pipeline runs may execute simultaneously on this machine... NEVER kill processes by name"
   - "Do not ask follow up questions and do not ask the user anything."
   - "No placeholders, stubs, or incomplete code — all code must be complete and functional."
   - Writing register banned words: "delve, underscore, showcase, intricate, pivotal, realm, commendable, meticulous, tapestry, garner, multifaceted, it is worth noting, plays a crucial role, not only ... but also"

7. Pending Tasks:
   - Task #2 (IN PROGRESS): Literature review and bibliography - agent launched (id: ae820c60c8b178b45) to fetch ~49 BibTeX entries via aii_semscholar_bib__fetch
   - Task #3 (IN PROGRESS): Style exemplars - agent launched (id: ad3f39a29c1a7effe) to collect style passages from 4-5 papers
   - Task #4 (IN PROGRESS): Read all artifacts - agent launched (id: a208c493dcdf68cc9) to extract ALL numbers to extracted_numbers.json, PLUS direct reads already completed (see section 3)
   - Task #5 (PENDING): Write the full paper draft addressing all reviewer MUST-FIX items
   - Task #6 (PENDING): Revision pass with REVISION_CHECKLIST.md
   - Final: Write output JSON to `./.terminal_claude_agent_struct_out.json`

8. Current Work:
   I was in the process of reading artifact data files (Task #4) to extract all numbers needed for the paper. I had completed reading the key data from:
   - iter-2 exp1 (race table, correlations, prompt budget, readout bakeoff, direction nulls, judge framing)
   - iter-2 exp2 (ROSI reversal, detection by rung)
   - iter-2 exp3 (weight recovery grading, repair, replication, true kappa, validity band)
   - iter-3 eval (oracle rescore, early scatter, power, step1)
   
   Three background agents are still running:
   1. Bibliography agent fetching BibTeX for ~49 papers
   2. Style exemplars agent collecting passages from top papers
   3. Artifact data reader extracting all numbers to extracted_numbers.json

   The reviewer feedback requires these major paper changes:
   - Restate Contribution 2: card regex (0.917) fails pole rule; presentation invariance (1.000) anti-correlates with safety (rho -0.71); no metric is both discriminative and safety-aligned
   - Add replication rows for weight grading (0.85 [0.56, 0.95] n=20; projection-only 0.65 [-0.26, 0.95] n=10) with edit-type confound
   - Show full prompt-budget k-table as line figure with both |rho| and LOLO BA
   - Report 3 direction-null counts together (16/17 last-prompt, 9/17 first-gen, 9/20 cross-family)
   - Add Section 5.x: Qwen3-4B lineage anatomy, Step 5 correlations, external ground truth, metamodel negative
   - Fix repair experiment to quote refusal (0.125→0.208) and BB8 (0.25→0.25), reframe as detector evasion
   - Add abstract, Table 1 (main race), Table 2 (forgery ladder), move validations to Section 3
   - Label Qwen3 ROSI result 'direction-consistent, not significant'
   - Add oracle readout sensitivity analysis (11 CONSTRUCT_UNTESTABLE, 1 READOUT_FAILED)
   - Regenerate bibliography from Semantic Scholar (fix 20/30 fabricated authors)
   - Add per-judge reliability table
   - Rename F3/F4 to 'LoRA-shaped weight deltas (untrained)'

9. Optional Next Step:
   Once the 3 background agents complete, proceed immediately to Task #5: writing the full paper draft. The next step is:
   1. Check if agents have completed and read their outputs (references.bib, style_exemplars.md, extracted_numbers.json)
   2. Begin writing the complete paper with all sections (Abstract, Introduction, Related Work, Method, Experimental Setup, Results, Discussion and Limitations, Conclusion) addressing every reviewer MUST-FIX item
   3. Include [FIGURE:fig_id] markers and define figure specs with exact data values
   4. Then run the revision pass (Task #6) and output the final JSON

   The paper must be written to `./.terminal_claude_agent_struct_out.json` matching the PaperText schema.

If you need specific details from before compaction (like exact code snippets, error messages, or content you generated), read the full transcript at: /root/.claude/projects/-ai-inventor-aii-data-runs-run-fcYd-7ruOwtm-3-invention-loop-iter-3-gen-paper-text-gen-paper-text/b94e98d8-ce27-445c-97b3-a8a6e9bc59b0.jsonl
Continue the conversation from where it left off without asking the user any further questions. Resume directly — do not acknowledge the summary, do not recap what was happening, do not preface with "I'll continue" or similar. Pick up the last task as if the break never happened.
```

### [9] SYSTEM-USER prompt · 2026-09-21 14:59:43 UTC

```
<validation-feedback>
Attempt 1 failed validation.

Schema validation found 2 problems — fix ALL of them at once:
  - at `figures.0`: 'figure_type' is a required property
  - at `figures.1`: 'figure_type' is a required property
Every required field must be present and every field type must match the schema.

Produce `.terminal_claude_agent_struct_out.json` again so it contains corrected JSON that matches the schema. Do not invent new fields.
</validation-feedback>
```

### [10] SYSTEM-USER prompt · 2026-09-21 14:59:55 UTC

```
<validation-feedback>
Attempt 2 failed validation.

Schema validation found 2 problems — fix ALL of them at once:
  - at `figures.0.figure_type`: 'diagram' is not one of ['data', 'concept']
  - at `figures.1.figure_type`: 'chart' is not one of ['data', 'concept']
Every required field must be present and every field type must match the schema.

Produce `.terminal_claude_agent_struct_out.json` again so it contains corrected JSON that matches the schema. Do not invent new fields.
</validation-feedback>
```
