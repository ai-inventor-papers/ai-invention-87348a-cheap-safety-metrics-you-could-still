# gen_strat_1 — test_idea

> Phase: `invention_loop` · round 2 · `gen_strat`
> Run: `run_fcYd_7ruOwtm` — One Candidate Survives: A Pre-Registered Screen of Internal Safety Metrics for Language Model Checkpoints
>
> Full, verbatim record of every prompt the AI Inventor pipeline gave this agent — system-user, human-user and skill-input — in the order they landed. Nothing truncated.

## Task: `gen_strat_1` (terminal_claude_agent)

### [1] SYSTEM-USER prompt · 2026-09-21 03:02:41 UTC

````


<pasted_content id="a71b">
<system-prompt>
<ai_inventor_context>
<ai_inventor_summary>
You are one of many LLMs in AI Inventor — an automated research system that generates NOVEL and FEASIBLE hypotheses, investigates them through experiments and research, and produces a paper.

Your output feeds other LLMs downstream. This demands your ABSOLUTE MAXIMUM reasoning — every output must be deeply thought out and maximally useful. Surface-level responses waste downstream computation.
</ai_inventor_summary>

<your_role>
YOU ARE: A strategy planner (Step 3.1: GEN_STRAT in the invention loop)

Each iteration of the invention loop runs: GEN_STRAT → GEN_PLAN → GEN_ART → GEN_PAPER_TEXT → REVIEW_PAPER → UPD_HYPO
Artifact types: RESEARCH (web search), EXPERIMENT (code), DATASET (data collection), EVALUATION (metrics), PROOF (Lean 4)
State persists across iterations: strategies, plans, artifacts, paper_texts (read from the run tree)

You received the hypothesis, iteration status (current + remaining), previous iteration's strategies, available artifact types, existing artifacts, and reviewer feedback.
Your strategy governs THIS iteration only. You define what artifacts to create NOW.

Focused strategy → efficient progress. Scattered strategy → wasted iteration.
</your_role>
</ai_inventor_context>

<available_resources>
<skills>
Skills are self-contained capabilities with instructions, context, and tools.

- aii-web-tools: Free-first web search (general + scholarly modes), page/PDF fetch as markdown, regex grep over page/PDF text
- aii-semscholar-bib: Batch-fetch BibTeX from Semantic Scholar
- aii-openrouter-llms: Search and call 300+ LLMs via OpenRouter
- aii-hf-datasets: Search, preview, download HuggingFace datasets
- aii-owid-datasets: Search and load Our World in Data tables
- aii-lean: Compile/verify Lean 4 code, Mathlib search, tactic suggestions
- aii-concept-fig-gen: Generate/edit images via Gemini 3 Pro Image (Nano Banana Pro)
- aii-json: Validate JSON against schemas, generate mini/preview variants
- aii-paper-writing: Academic paper structure, bibliography, citations
- aii-paper-to-latex: Assemble LaTeX papers and compile to PDF
- aii-parallel-computing: GPU acceleration, CPU parallelism, async I/O
- aii-python: Python coding standards for experiment scripts
- aii-use-hardware: Detect CPU/RAM/GPU, memory-safe processing
- aii-long-running-tasks: Gradual scaling pattern for long-running tasks
- aii-colab: Google Colab runtime constraints for notebooks
- aii-file-size-limit: Check and split oversized output files
</skills>

<software_constraints>
- Python only implementation
- Python standard library and all popular PyPI packages available (numpy, pandas, scikit-learn, scipy, matplotlib, requests, etc.)
- Local parallelism encouraged: multiprocessing, asyncio, threading — see aii-parallel-computing skill
- LLM API calls must go through OpenRouter only (no direct OpenAI, Anthropic, etc.)
- **SPEND BUDGET**: at most $10 USD of OpenRouter API calls for this artifact. Nothing outside your own code enforces this — the key you are given has no per-artifact cap — so it holds only if you track cumulative cost after every call and stop when you approach it. Budget the work up front: estimate the per-call cost and the number of calls BEFORE starting a sweep, not after it overruns. Exceeding it spends real money that the run cannot recover.
</software_constraints>
</available_resources>

<time_budgets>

Each artifact executor has a fixed time budget (including writing code, debugging, testing, and fixing errors):

- research: 3h
- dataset: 6h
- experiment: 6h
- evaluation: 3h
- proof: 3h

</time_budgets>

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

<research_methodology>
Think like a researcher planning a study for a top venue.

- All strategies run in parallel and their artifacts combine into one pool. Together they must build toward a publishable paper — each strategy contributes a distinct, necessary piece. No strategy should be a standalone island.
- Ask yourself: what would a reviewer need to see? Proper baselines, controlled comparisons, ablations that isolate what matters. Plan artifacts that preempt reviewer objections.
- Depth over breadth. One well-designed experiment with proper controls beats five shallow ones.
- Match your evaluation to your claims. Measure what the hypothesis actually asserts.
- When results are weak or partial, vary the approach before writing it off. One failed method doesn't falsify the hypothesis.
- If iterations remain, think about what the NEXT iteration will need. Leave useful building blocks — datasets, baselines, preliminary results — that future strategies can build on, refine, or compare against.
</research_methodology>

<principles>
1. FOCUS ON NOVELTY - every strategy must lead to a genuinely novel contribution
2. MAXIMIZE PARALLELIZATION - all artifacts in your strategy run in parallel
3. BUILD ON EXISTING WORK - use completed artifacts from previous iterations, learn from failures
4. ITERATE ON THE METHOD - a negative result is first about the approach, not the hypothesis. Try different methods, parameters, data, or formulations. When the hypothesis itself has been widened, that same energy goes into testing SEVERAL candidate answers at once rather than one of them harder.
5. TWO SHAPES OF ITERATION - a DEEP TEST pushes one claim further; a WIDE SCREEN tests several candidate answers cheaply in parallel and confirms the survivor on held-out evidence. Read which one this iteration is from the hypothesis and the instructions in the user prompt, and build that shape. Never answer a widened hypothesis with one more deep test.
6. NEVER SHRINK TO FIT - do not plan an iteration whose best possible outcome is a smaller, safer version of a claim that already came back weak. If the claim is in trouble, the strategy's job is to put better candidates in play, not to find a corner where the old one survives.
7. DIAGNOSE BEFORE DECIDING - before each iteration, review what worked, what didn't, and why. Use that to choose what to try next. Gaps are action items, not conclusions.
8. SET DEPENDENCIES WISELY - depends_on is a list of {id, label} objects referencing existing artifacts; each label is a short free-text type (a word or two, e.g. "dataset", "validates", "extends") that tags how the dep is used
9. PLAN FOR DEPENDENCIES - if an artifact depends on another (e.g. experiments need datasets), ensure prerequisites exist first or plan them this iteration for the next
</principles>

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
Your workspace: `/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_2/gen_strat/gen_strat_1`

CRITICAL: Every file you create, write, or save MUST be inside this workspace directory (subdirectories OK). You MUST NOT write files anywhere outside this path — external paths are READ-ONLY. Use absolute paths for all file operations.

EVERY file write MUST start with `/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_2/gen_strat/gen_strat_1/`:
GOOD: `/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_2/gen_strat/gen_strat_1/file.py`, `/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_2/gen_strat/gen_strat_1/results/out.json`
BAD: `/tmp/file.py`, `~/output.json`, `./file.py`, any path outside the workspace
</workspace>
</system-prompt>

<prompt>
<hypothesis>
Your strategy should advance this hypothesis.

kind: hypothesis
title: Cheap safety metrics you could still believe
hypothesis: |-
  This run answers the commissioned question - a cheap safety score for a stranger's checkpoint, no
  parent, no reference, weights or activations, a few prompts at most - and it ships TWO co-equal
  headline results rather than one. R1 is the request's own table, turned into a claim. R2 is the
  selection axis that makes the table mean something.

  R1 (THE REQUEST'S QUESTION, ANSWERED AS A CLAIM). Over 50 registered single-checkpoint metrics, the
  ones that separate safety-tuned from ordinary-instruct from abliterated ON HELD-OUT LINEAGES are
  exactly the ACROSS-ITEM ones - statistics of how a model's refusal drive varies WITH the item -
  while the LEVEL metrics that make up almost all of the published cheap-readout literature separate
  only inside the family they were tuned on. The mechanism is pre-registered, not hoped for: published
  work establishes that harmful intent is linearly decodable at about 0.98 AUROC in essentially every
  checkpoint, with abliterated variants within 0.003 of their instruct parents, so what differs between
  alignment variants is not what the model knows but whether its refusal USES what it knows. A level is
  a property of the model; a coupling is a property of the decision. R1 is the request's step 3 and
  step 5 delivered as a finding rather than a stage.

  R2 (WHY A CORRELATION IS THE WRONG SELECTION RULE). Cheap metrics are currently chosen by correlating
  them with benchmark scores on honestly-trained checkpoints. That rule assumes the uploader is honest,
  which is the wrong assumption for exactly the situation the metrics exist for. The right axis is what
  it costs to produce a BELIEVABLE FAKE, and believable means two things at once: the edit moves the
  metric, AND it survives the free structural checks an auditor runs anyway. We call that UNDETECTABLE
  FORGERY COST, we claim it ranks cheap metrics differently from benchmark correlation, and we give an
  algebraic reason.

  (H1) UNDETECTABLE FORGERY COST IS MEASURABLE, AND IT IS A PROPERTY OF (METRIC, THRESHOLD,
  FALSE-POSITIVE BUDGET, AUDITOR ACCESS). For each metric we walk a fixed cost-ordered ladder of
  checkpoint edits and record two numbers per rung. FORGERY COST is the cheapest rung that pushes the
  metric past a threshold fixed at a stated false-positive rate on a large honest panel, while the
  model's two-sided safety does not improve. DETECTION COST is what it costs an auditor to notice the
  rung was applied. Detection is reported under TWO ACCESS TIERS, because the previous version of this
  hypothesis silently assumed the auditor could diff against "the family default", which is the
  attested reference this request forbids.
    TIER A, REFERENCE-FREE, AND THIS IS THE HEADLINE. Only the downloaded repository, with no idea what
    family it came from: (i) does the chat template inject instruction text beyond role scaffolding;
    (ii) does generation_config or tokenizer_config carry a baked-in system prompt; (iii) does the state
    dict contain tensors the architecture named in config.json does not define, or tensors whose shapes
    it does not define; (iv) the zero-prompt weight statistic of H3.
    TIER B, REFERENCE-ANCHORED: the template, tokenizer and config diff against the family default,
    which presumes the auditor can identify and fetch the family. Reported beside Tier A as the
    stronger-auditor case. The GAP between the two tiers is a second, sharper result in its own right:
    how much detection power comes from knowing the family at all.
  The headline quantity is the cheapest rung that is effective AND survives Tier A. We report the whole
  cost-versus-false-positive-rate curve, estimate honest percentiles from at least 120 checkpoints
  rather than from the six-lineage ground-truth panel, and bootstrap every rung assignment.

  A rung label takes at most six tied values, too blunt to correlate, so cost also gets a CONTINUOUS
  form - and unlike the previous version, EVERY rung has one, so the correlation is not computed on a
  subset selected on its own independent variable. For the two weight rungs the forger sweeps an edit
  magnitude; for the two text rungs the forger sweeps a graded preamble ladder (token budget, from a
  single sentence to a full safety system prompt, on a pre-registered ordered list). In both cases the
  operating point is the smallest setting that pushes the metric past threshold, and the EXCHANGE RATE
  is the Tier A screen's score at that point, expressed as a z-score against the honest panel. Coverage
  is reported as a fraction of the battery and of each class, and the coarse rung-level correlation is
  printed beside the continuous one so a reader can see whether they agree.

  (H2) THE INVERSION, TESTED AS A VARIANCE DECOMPOSITION RATHER THAN AN UNDERPOWERED SPEARMAN. Across
  50 metrics registered in full before any measurement, we claim honest-panel accuracy and undetectable
  forgery cost are NEGATIVELY related. The previous version made a within-functional-form-class
  correlation the primary test, which was a mistake twice over: at realistic class sizes a Spearman
  confidence interval excludes zero only at |rho| above 0.83 at n=6 and 0.73 at n=8, so power against a
  true rho of -0.5 at n=6 is about 0.09; and H3 predicts the effect lives BETWEEN classes, so the
  primary test was pre-registered to fail. The primary analysis is now a mixed model of undetectable
  forgery cost on honest-panel accuracy with functional-form class as a random effect, reporting the
  WITHIN-class and BETWEEN-class components separately with confidence intervals. The answer is then
  "how much of the inversion is battery composition and how much is not", which is informative either
  way, rather than a pass/fail on a test that cannot pass. We pre-register n=10 as the minimum class
  size at which a within-class estimate is reported at all, publish the detectable |rho| at that size
  beside the estimate, and DESIGN the battery so that at least one class carries a real within-class
  test: at least 15 genuinely distinct across-item functional forms, not 15 variants of one.

  (H3) THE MECHANISM: AN EDIT-RANK LAW, AND AN INSTRUMENT THAT READS SUBSPACE SHARING RATHER THAN
  MAGNITUDE. Three numbered claims.

    CLAIM 3a - RANK ZERO CANCELS. Most cheap metrics read a LEVEL: a norm, a rate, a mean projection at
    one fixed direction, layer and position. Adding a fixed vector to a band of residual writes sets
    that level to whatever the forger wants, and because the identical offset lands on every item it
    cancels EXACTLY from any across-item statistic computed as a linear read at the injection layer. For
    a metric read downstream of a normalisation the claim is APPROXIMATE, with a pre-registered
    tolerance rather than an appeal to floating point: simulating a 40 percent spread in residual norm,
    an across-item correlation moves by 0.010, 0.016 and 0.021 as the bias grows to 0.5, 2 and 8 times
    the typical per-dimension residual scale, so the drift saturates and 0.05 correlation units is
    defensible. Checked in fp32, with the bf16 gap reported once.
    HOW F2a IS ACTUALLY BUILT, which the previous version left open and which decides whether the whole
    undetectable-cost column has any variance. Qwen3 and most panel architectures define NO bias on the
    attention output projection or the MLP down projection, so a literal W x + b adds a tensor the
    declared architecture does not have, and Tier A's key-and-shape check catches it in milliseconds
    with no family default and no forward pass. We therefore build F2a WITHOUT adding a parameter:
    the offset is realised as a rank-one edit carried by a near-constant coordinate - an
    attention-sink or massive-activation dimension, whose activation is known to be nearly
    item-independent - and we verify numerically that the realised offset is constant across items to
    the 0.05 tolerance. If it is not, we fall back to the explicit bias tensor and report F2a as metric
    hygiene exactly as F0 is. Either way the outcome is pre-registered as reportable, including the
    clean version: "every training-free rung is free to catch, and the only undetectable forgery is
    training" would be a short, quotable answer that this ladder was built to be able to produce.

    CLAIM 3b - THE INSTRUMENT, REBUILT TO READ SUBSPACES INSTEAD OF SIZES. Both training-free weight rungs
    write ONE SHARED DIRECTION into many residual-write matrices. Abliteration replaces W by
    (I - kappa r r^T) W, suppressing r in every edited matrix; rank-one injection adds alpha r v^T with the
    same r in every layer. The previous version read this off the RAW cross-layer Gram matrix, and that
    statistic was wrong in two ways we now concede, and we have already measured both. It reads MAGNITUDE,
    so its honest baseline moves with the weight spectrum: in simulation at residual width 256, fan-in
    1024 and 28 layers, the raw Gram's smallest normalised eigenvalue sits at 0.821 for a Gaussian honest
    spectrum and 0.119 for a heavy-tailed one, a sevenfold swing in the reference itself. And it is
    knife-edged, firing only for a full-strength single-direction all-layer recipe.
    THE REPLACEMENT, WHICH WE DO NOT CLAIM AS OURS. For each residual-write matrix take the projector onto
    its bottom-k (or top-k) LEFT singular subspace, average those projectors over a contiguous band of
    layers, and take the largest eigenvalue: BOTTOM- and TOP-SUBSPACE ALIGNMENT. A projector discards
    singular values entirely, so the statistic is invariant to each layer's spectrum; it is windowed, so an
    edit confined to part of the stack is found rather than diluted; and it is a continuous overlap, so it
    degrades gracefully.
    PRIORITY, STATED BEFORE THE RESULTS RATHER THAN AFTER. We searched for this mechanism specifically and
    found it already implemented and publicly released. A community model-scanning tool computes, on the
    same two matrix families, per layer, with no parent and no prompts, the sum of per-layer bottom-k left
    singular projectors and reports its leading eigenvalue mass as a reference-free indicator of
    abliteration, complete with a layer-band variant for localised edits and its own rough calibration. So
    the instrument is NOT our contribution and this hypothesis does not rest on it. We adopt it as an
    off-the-shelf auditor screen, cite it as prior art, and claim only what is genuinely left: a null model
    and an honest-panel false-positive rate it has never been given, whole-family held-out validation,
    behaviour in bf16 as shipped, a recipe census that says which real checkpoints it can and cannot see,
    and the injection arm it does not implement. That is calibration and stress-testing of someone else's
    detector, and it is labelled as such everywhere. It is also a BETTER position for the argument: the
    free structural screen that defines undetectable forgery cost should be a tool an auditor can already
    download, not one we invented to make our own headline quantity come out right.
    WHAT WE HAVE ALREADY MEASURED, and the numbers below are measured rather than hoped for, because the
    question that matters for this study is not whether the statistic exists but whether it holds up.
    Bottom-subspace alignment over an
    eight-layer window reads 0.168 on a Gaussian honest stack and 0.177 on a heavy-tailed one - the swing
    that broke the old statistic is gone. On the heavy-tailed stack it reads 1.000 for a full-strength
    shared-direction abliteration, 0.953 at ablation weight 0.7, 0.845 at 0.5 and 0.617 at 0.3, against
    that honest 0.177; and 1.000, 1.000 and 0.876 when the edit is confined to 75, 50 and 25 percent of the
    stack, where the old statistic sat at 0.078, 0.105 and 0.119 against an honest 0.119, that is, inside
    honest range. Windowing is what buys the layer-band case, and it is a result we have seen before in
    our own work on a different weight readout.

    CLAIM 3c - THE BLIND SPOT, MEASURED RATHER THAN ARGUED, AND MOSTLY CLOSED. A sharing statistic is blind
    to an edit whose directions are mutually ORTHOGONAL across layers. That is not a weakness to argue away;
    it is the definitional price of reading sharing rather than perturbation, which is exactly why the
    per-layer-random arm belongs in the design as a negative control - and in simulation it behaves as a
    control should, leaving alignment at 0.173 against an honest 0.177. Three things close most of the gap.
    FIRST, independent random per-layer directions are the wrong model of a real tool. A per-layer
    abliteration estimates the SAME refusal feature separately at each layer, so its directions are
    mutually ALIGNED. Alignment reads that directly and monotoni
</pasted_content id="a71b">


<pasted_content id="a71b">
cally: at mean cross-layer cosines of 0.81,
    0.65, 0.48 and 0.25 the statistic reads 0.805, 0.673, 0.533 and 0.358, every one of them above honest.
    So the question is not "shared or per-layer" but "how aligned", and that is a number recoverable from
    the checkpoint alone, since each layer's suppressed direction is its own bottom left singular vector.
    SECOND, full-strength projection leaves a purely LOCAL trace needing no sharing at all: it makes each
    edited matrix exactly rank-deficient, so the ratio of its smallest to its second-smallest singular value
    collapses - measured at 0.000 for a per-layer full-strength abliteration and 0.435 at ablation weight
    0.7, against an honest 0.997, scale-free and spectrum-free, whatever direction each layer used. Real
    checkpoints ship in bf16, so the separator is pre-registered against a bf16-rounded reference: rounding
    a projected matrix lifts that ratio to 0.010, still two orders below honest, and never to the exact
    algebraic zero the previous version quoted.
    THIRD, WE HAVE ALREADY RUN THE CENSUS, and it says the repair matters and the residual blind corner is
    small. Of 37 real abliterated Hub checkpoints whose cards we read, only 3 (8.1 percent) jointly state
    the full-strength single-direction all-layer recipe the old statistic required - so that statistic
    covered under a tenth of the population. Only 2 (5.4 percent) state a per-layer DIRECTION; 3 more state
    an explicit layer BAND, which windowing handles; and 21 (56.8 percent) state no recipe at all, which is
    precisely why the recipe must be recovered from the weights. The dominant automated tool turns out to
    support the repair rather than defeat it: its direction scope is a SEARCHED hyperparameter rather than a
    default, 8 of the 10 checkpoints that publish its parameter table used a global direction, and its
    ablation weight is ALWAYS layer-position-varying by construction with no flat-weight mode at all -
    shipped attention weights ranged 1.05 to 1.50 and were never exactly 1.0. That is the shared-direction,
    layer-varying-strength case, which is the case the windowed statistic handles and the raw Gram does not.
    THE HONEST REMAINDER, stated as the boundary rather than buried. The corner that stays invisible to the
    sharing statistic is per-layer directions AND sub-unit strength together, about 5 percent of stated
    recipes, and naming it precisely is a result because it tells a forger and an auditor the same thing.
    And the INJECTION half is the harder half, which we now say with a number instead of a hope:
    top-subspace alignment rises from 0.166 honest to 0.664 and 0.975 as a shared injection grows to one and
    three times the typical per-dimension scale on a Gaussian stack, but on a heavy-tailed stack it does not
    move at all at those magnitudes, because an injected direction never reaches the top of a heavy-tailed
    spectrum. So for injection the statistic is swept over spectral rank bands rather than fixed at the top,
    and the pre-registered operating point is the published method's OWN alpha measured against the honest
    panel - with the same withdrawal path if it fails there.

  (H4) CROSS-FITTING IS PART OF THE METRIC DEFINITION, NOT AN ANALYSIS CHOICE. Any "model's own internal
  harm estimate" is a direction FITTED from labelled contrast items, and the residual stream is 1536 to
  3072 dimensional while the item count is a few dozen. In that regime an in-sample difference-in-means
  projection separates PURE NOISE at AUROC 1.000, and 0.507 cross-fitted, so an in-sample harm direction
  is numerically indistinguishable from the harm LABEL. Every fitted-direction metric is therefore
  defined with a pre-registered fold structure stratified by harm category, evaluated only on items that
  did not fit it, and reported beside a per-checkpoint label-permutation null, with the in-sample version
  printed alongside and d and n given per family. The extraction protocol is fixed in advance because two
  pooling choices at the same layer are known to recover directions 73 degrees apart.

  (H5) THE DELIVERABLE, WITH EVERY READOUT LABELLED BY ITS ROLE. Four internal readouts plus exactly two
  black-box baselines, which satisfies the request's invariant as a set - but they do different jobs and
  the paper says so wherever the set is listed.
    (a) SECRET-DRAW COUPLING - DISCRIMINATOR. Over a few dozen items drawn AT AUDIT TIME from a large
        pool of presentation conditions, the share of across-item variation in the model's refusal drive
        at the first generated token explained by its own cross-fitted internal harm estimate, reported
        in logit units beside the ratio. Its companion diagnostic is DECISION SPREAD, the across-item
        standard deviation of the refusal drive, which goes to zero for both a blanket refuser and a
        never-refuser and is what stops the ratio being a quotient of two noise terms.
    (b) HARM KNOWLEDGE UNDER THE DRAW - PRECONDITION DIAGNOSTIC, NOT A DISCRIMINATOR. Pre-registered as
        near-constant across alignment variants on published evidence. It is the denominator of the
        argument - the evidence that the knowledge was there - so that (a) can be read as "refusal does
        not use it" rather than "the model cannot tell".
    (c) SHARED-SUBSPACE SCAR - DETECTION STATISTIC, NEVER A SAFETY SCORE. Zero prompts, no parent, one
        pass over the safetensors, seconds, and on CPU. Reported in the detection column.
    (d) OFF-MANIFOLD RESIDUAL - DISCRIMINATOR. Distance of a checkpoint's metric vector from the
        low-dimensional set honest checkpoints occupy, fitted on at least 120 honest Hub checkpoints with
        family-centring over a pre-registered handful of coordinates, never on the ground-truth panel.
    The discrimination claim rests on (a) and (d). The two baselines - first-token logit-gap margin and a
    greedy refusal rate on a handful of prompts - are kept and given every advantage, with the model-card
    regex as a free non-model comparison point that reads nothing at all.

  (H6) THE HEADLINE EXPERIMENT, RE-AIMED AT WHAT IS ACTUALLY OPEN. Rank-one safety injection is published
  as a cheap defence, validated with a guard model's harm-refusal rate, and its only benign column is
  compliance on 512 ordinary Alpaca prompts - no over-refusal measurement anywhere. The previous version
  predicted that most of its gain is over-refusal and called that a strong motivation. That qualitative
  phenomenon is already in print for refusal-direction STEERING, where harmful refusal and benign
  over-refusal are reported to rise in parallel to saturation, so we cite it and stop claiming it. What
  is open is quantitative and specific: where does this method's OWN published operating point land on a
  two-sided score, and does that score REVERSE the verdict its own evaluation reached. We run it
  unmodified at its published settings, report its harmful-refusal gain against its measured false-refusal
  cost on benign-but-alarming twins, and pre-register that the two-sided discrimination score does not
  improve. Riding free on the same run is the sharper prediction, untouched by any prior work: because the
  method writes ONE direction into ALL residual write matrices by its own description, top-subspace
  alignment should flag it from the weights alone, with zero prompts, no parent and no forward pass.
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
    survives wrapping, paraphrase or translation. One layer sweep, no edits, no manifold, no constructed fakes.
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
</hypothesis>

<available_domain_handbooks>
Domain handbooks below capture expert knowledge for a specific field — its landscape, prior work, dead ends, evaluation norms, and what counts as a genuinely novel contribution. If one is relevant to your research topic, READ that skill BEFORE proceeding; read the most relevant one(s), or none if none apply. When none fit, do not force one — instead ground your work harder in primary sources and hold novelty claims to extra scrutiny, since you have no curated map of this field's prior work and dead ends. Use it for study design, proper baselines, and the evaluation/validity norms this field demands.

- **aii-handbook-auto-computational-linguistics** — Field handbook for computational linguistics as a SCIENCE of language — grammaticality and minimal pairs (BLiMP), surprisal versus reading times, linguistic structure in LMs, annotator disagreement an
- **aii-handbook-auto-mechanistic-interpretability** — Field handbook for mechanistic interpretability of neural networks — circuit discovery, activation and attribution patching, sparse autoencoders, transcoders, attribution graphs, steering vectors, pro
- **aii-handbook-auto-multi-agent-llm-systems** — Field handbook for multi-agent LLM systems (MAS) — orchestration topology, multi-agent debate, mixture-of-agents, verifier and critic agents, inter-agent protocols (MCP/A2A), failure attribution and s
- **aii-handbook-auto-neurosymbolic** — Field handbook for neuro-symbolic AI — text-to-logic autoformalization (NL to FOL), LLM-plus-solver and prover pipelines (Prolog, ASP, SMT), probabilistic-differentiable NeSy (DeepProbLog, Scallop), r
</available_domain_handbooks>

<iteration_status>
Current iteration: 2 of 5
Remaining (including this one): 4
</iteration_status>

<candidate_alternates>
Runner-up answers to the same ask, carried from hypothesis generation. These are the
candidate population a wide screen draws on — treat them as real options, not as context.

--- Candidate 1 ---
title: Internals buy fewer prompts, not better answers
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
  the thing internals buy, which is cleaner and more immediately actionable than the main hypothesis if no metric turns out
  to be forgery-resistant at all.

--- Candidate 2 ---
title: Refusal depth predicts what survives a shift
hypothesis: >-
  Drop the forgeries entirely and read one ordering off a single checkpoint: the layer at which its refusal signal first becomes
  decodable, relative to the layer at which the request's semantic content first becomes decodable, both cross-fitted with
  a per-model permutation null. Claim: refusal that resolves EARLIER than the content it is supposedly about is a lookup on
  surface features, and the earlier that crossing, the smaller the fraction of the model's in-distribution safety that survives
  wrapping, paraphrase or translation. One layer sweep, no edits, no manifold, no constructed fakes.
why_it_could_win: >-
  This wins if real Hub checkpoints already span the whole shallow-to-deep range, which is plausible given how many are light
  fine-tunes and merges - in which case constructing forgeries is expensive apparatus for variance that already exists in
  the wild. It beats the main hypothesis in a world where deliberate metric-gaming is rare but accidental shallow alignment
  is everywhere, and it disagrees concretely: under this alternate the useful signal is an ordering of two layer indices,
  not a relationship across items, so the two predict different metrics to be the best one.

--- Candidate 3 ---
title: The recipe is the signal, not the safety
hypothesis: >-
  For a checkpoint you know nothing about, the only cheap thing that reliably survives held-out families is a read of its
  EDIT HISTORY from the weights, and no activation-based safety readout adds anything on top of it. Existing parent-free weight
  scanners answer only a yes-or-no question, was this abliterated. The claim here is that the same weights answer a strictly
  richer one, and that the richer answer is what carries the safety signal: recover, parent-free and in seconds, WHICH RECIPE
  was used - shared versus per-layer direction, realised ablation strength, which layer band - and that recovered recipe,
  in particular the realised strength, is MONOTONE in the checkpoint's measured harmful compliance and predicts its two-sided
  safety better than any cross-fitted activation metric in the battery once whole families are held out. That would turn a
  binary tamper flag into a graded safety read, which no existing scanner provides. The honest deliverable is a recipe-resolved
  detector with a stated scope, and the paper's job is to map exactly which risks it is blind to, starting with a model that
  was never edited and is simply unsafe.
why_it_could_win: >-
  This wins if what actually varies across Hub checkpoints is edit history rather than safety, which near-zero within-family
  safety variance plus the published finding that harm geometry is nearly identical in base, instruct and abliterated variants
  both point to. It beats the main hypothesis in a world where coupling turns out flat or noisy at a few dozen items, and
  it disagrees head-on: under this alternate the detection column is not a supporting axis for a safety metric, it is the
  entire result, and it makes a sharper prediction the main hypothesis does not - that ablation STRENGTH, recovered from the
  weights alone, is monotone in measured harmful compliance.

--- Candidate 4 ---
title: A learned metamodel reads lineage, not safety
hypothesis: >-
  A small regressor trained on pooled hidden states predicts benchmark safety scores better than any hand-written formula,
  and the reason is that it recovers architecture and lineage identity rather than safety. The ablation predicts the advantage
  collapses to nothing once whole families are held out, while a lineage-identity probe on the same features stays near perfect
  - and the gap between those two curves is the deliverable, because it puts a number on how much of any activation-based
  safety score is family bookkeeping.
why_it_could_win: >-
  This wins as the right answer if the strongest rival to every formula is a learned metamodel and nobody has isolated what
  it reads. It beats the main hypothesis in a world where the metamodel genuinely does generalise to unseen families, which
  would mean a safety signal exists in activations that no hand-designed statistic has captured, and the main hypothesis's
  whole framing - interpretable named metrics ranked by forgeability - would be looking in the wrong place.
</candidate_alternates>



<previous_strategies>
Strategies from the PREVIOUS iteration. You can CONTINUE these directions,
ADAPT based on what worked and what didn't in the artifacts produced, or PIVOT if results suggest a better path.

--- Strategy 1 ---
kind: strategy
id: gen_strat_1_idx1
title: Five cheap safety reads, one fair race
objective: >-
  Put five genuinely different answers to the commissioned question - what cheap number read from ONE downloaded checkpoint,
  with no parent and no reference model, reports how safe it is - into a single head-to-head screen on identical items, identical
  forward passes and identical held-out lineages, and come out with a ranked comparison plus one survivor that iteration 2
  confirms on sealed evidence. The novel contribution this iteration builds toward is threefold. First, the three published
  incumbents that already occupy this deliverable slot become SUCCESS BARS with rows in every headline table, rather than
  related-work citations a plan computes and then declines to be judged against. Second, the selection axis is doubled: a
  cheap metric is ranked not only by how well it separates honest checkpoints but by what it costs to FORGE past it and what
  it costs an auditor to notice - which is the right question for a metric whose entire purpose is judging an artifact uploaded
  by a stranger. Third, the request's own first ask is delivered as a claim: a pre-registered principal-angle test of whether
  official safety training and community abliteration move the SAME activation subspace in opposite directions or different
  ones.
rationale: |-
  This is iteration 1 of 5, the hypothesis ships four alternates that answer the same ask by different mechanisms, and only one candidate has ever been in play across ten straight borderline scores. The bottleneck is breadth of candidates, not depth on one, and the reviewer's verdict says so precisely: rigour is no longer the binding constraint and has not been for two iterations, while contribution went DOWN when the weight instrument was conceded to prior art. One more deep test of the same claim is the failure mode to avoid.
  The screen is affordable because all five candidates are functions of the SAME harvest. One weight pass and one teacher-forced activation pass per checkpoint produce, at near-zero marginal cost: the across-item coupling between refusal drive and the model's own cross-fitted harm estimate; the same readout's prompt-budget curve at 0, 1, 8, 16, 32 and 64 items against the black-box baseline on the identical axis; the layer at which refusal becomes decodable relative to the layer at which content does; the edit recipe recovered from weights alone with zero prompts; and the pooled hidden states a metamodel trains on. Design the harvest first, then ask which candidates it already pays for - that is what turns a five-way screen from expensive into nearly free.
  The three lanes are chosen where the candidates DISAGREE, not where they agree. Lane one asks which candidate separates the three classes at all on lineages it was never tuned on. Lane two asks what a cost-ordered ladder of cheap edits does to each, and every candidate registers a different signature: a constant offset cancels from an across-item statistic by algebra but moves every level, a rank-one edit is invisible to a template scan but is exactly what a weight read sees, a layer ordering should be immune to a constant and vulnerable to an adapter. Lane three asks the question the user actually asked - does the number predict a random checkpoint's published safety from a handful of prompts - against real leaderboard numbers and the incumbent that already does that task.
  The design also spends its artifacts pre-empting the objections this line reliably draws. The scarce arm of a three-way claim was never counted, and a naive Hub query over-counts independent safety-tuned lineages by roughly twenty times because five uploaders own ninety percent of the repos and one of them is epoch checkpoints of a single parent - so the resampling unit is fixed as parent-by-tuning-run and the count is published BEFORE the design commits. The external correlation pool was over-counted three to four times, so it is recounted from the downloaded files with a served-precision column, and the companion suite is pooled for a second outcome column rather than for n, because it adds essentially no usable open-weight checkpoints but does test the request's instruction that safety is not only refusal. The honest panel that sets every threshold is not verified honest when more than half of abliterated cards state no recipe, so it gets an explicit inclusion rule and a measured residual contamination rate. And the class prediction that carries the headline is restated as a monotone TREND across three classes rather than a clean partition, because the partition is close to pre-refuted by a baseline this very strategy is committed to running, and a trend survives a messy world where a partition does not.
artifact_directions:
- id: research_iter1_dir1
  type: research
  objective: >-
    Turn the three published incumbents that already occupy this deliverable slot into REPRODUCIBLE SUCCESS BARS rather than
    related-work entries, and run a dated saturation check on each of the five screened candidates so iteration 2's depth
    is not spent on a scooped one. The reviewer's single largest score blocker is that AMS, Skin-Deep/GFS and N-GLARE are
    all computed by the plan and then never made a bar anything has to clear; a fourth iteration with no incumbent row in
    a results table should expect to be marked down for avoidance. The deliverable is an implementation-grade specification,
    not a summary: for each incumbent, the exact statistic, the matrices or layers it reads, the pooling and normalisation,
    the reported operating point, the reported held-out number, and a verdict REPRODUCIBLE / PARTIALLY-REPRODUCIBLE / CLASSIFY-BY-FUNCTIONAL-FORM-ONLY
    with the missing detail named.
  approach: |-
    PART 1, THE THREE INCUMBENT SPECS, each fetched and regex-grepped rather than summarised. (a) AMS, arXiv 2608.05578, the activation-based model scanner: extract the exact separation statistic, the layer and token position it reads, whether the direction is fitted and from what, the threshold rule, the 14 configurations and 4 families, the leave-one-out protocol behind 71 percent (10/14), and the r = -0.546 compliance correlation with its 20 stratified JailbreakBench prompts. Its Tier 1 / Tier 2 split must be described precisely because it name-collides with our access tiers and the collision has to be renamed away. Critically, extract whether its fourth class, behavioural fine-tuning, is reported undetectable on activation-only evidence, since that is already-published territory we must cite rather than claim. (b) Skin-Deep / GFS, arXiv 2606.22676: the scalar's exact definition from one aligned model's hidden states, the 21 models, 6 alignment recipes and 3B-32B range, and the retention-after-LoRA protocol it predicts, because that is our transfer task already done. (c) N-GLARE, arXiv 2511.14195: the JSS construction, its probe conditions, its layer grouping, and the token budget it claims under one percent of. Prior work says N-GLARE has no public code, so the expected verdict is classify-by-functional-form and the reason must be stated in the spec rather than discovered at implementation time.
    PART 2, ONE DATED SATURATION SEARCH PER SCREENED CANDIDATE, each reported with query, top hits, an OPEN / PARTIAL / CLOSED verdict and the single nearest paper. C1 across-item coupling between refusal drive and the model's own cross-fitted harm estimate, measured per-CHECKPOINT rather than per-prompt. C2 the prompt-budget crossover between an internal readout and a behavioural one at matched budget. C3 the layer at which refusal becomes decodable relative to the layer at which request content does, as a per-checkpoint ordering. C4 parent-free recovery of the EDIT RECIPE - direction sharing, realised ablation strength, layer band - and whether recovered strength has ever been related to measured harmful compliance rather than to a binary tamper flag. C5 a learned metamodel on pooled hidden states predicting benchmark safety, and whether anyone has ablated it against a lineage-identity probe on the same features. The field handbook's own measured base rate for unflagged lanes is that essentially all of them are already occupied, so silence is not evidence of openness and a candidate killed on paper this week is free where one killed in iteration 3 costs an iteration.
    PART 3, FIVE LOAD-BEARING NUMBERS the screen is exposed to, resolved by fetch-and-grep with the printed value and its context quoted. (1) 2507.11878, which states that adversarially finetuning models to accept harmful instructions has minimal impact on internal belief of harmfulness, and whose Latent Guard is reported comparable to or better than Llama Guard 3 8B - the second half refutes our own motivating sentence that internals have never beaten outputs, and the distinction that saves it, per-prompt classifier versus per-checkpoint scalar that must transfer across unseen uploaders, must be confirmed as accurate before it is relied on. (2) 2603.05773 DSH, for the Recognition-versus-Execution double dissociation and specifically its reported family split, Llama explicit semantic control versus Qwen LATENT DISTRIBUTED control, which is a direct warning for held-out-FAMILY transfer of any fitted-direction candidate. (3) 2609.14759, for the claim that refusal levels off at a single harm direction with about three quarters of its causal input outside the moral subspace, and for its statement that Qwen specifically is unresolved at their sample size. (4) 2604.18901, for the two numbers it prints twice each - abliterated variants within 0.003 AUROC of instruct, and two pooling choices recovering directions about 73 degrees apart - because the first bounds how much any harm-knowledge readout can separate and the second forces the extraction protocol to be fixed in advance. (5) 2606.16349, for the verbatim finding that SFT also reaches low coupling while remaining substantially less robust, which is a published counterexample to coupling-implies-safety and which decides whether C1 is pre-registered as a DISCRIMINATOR only or also as a PREDICTOR.
    Output a single machine-readable spec table keyed by incumbent and by candidate, because the screen experiment consumes it directly and a prose report it cannot parse is a report that arrives too late to matter.
  depends_on: []
- id: dataset_iter1_dir2
  type: dataset
  objective: >-
    Build the two registries the screen cannot run without, and settle by COUNTING the two population questions that previous
    iterations asserted and the reviewer overturned: how many independent safety-tuned LINEAGES actually exist, and how many
    external checkpoints genuinely carry a published two-sided safety number. Both were over-counted by roughly an order of
    magnitude and both set the power of the headline claim, so they are measured here, before any metric is designed, rather
    than discovered at analysis time.
  approach: |-
    REGISTRY A, THE CHECKPOINT PANEL, one row per checkpoint with a verified label. Columns: repo id, parameter count, architecture, safetensors byte size, gated status re-checked with an AUTHENTICATED request (a previous census recorded hard 401s for huihui-ai Qwen3 checkpoints that are in fact gated:auto and recoverable, and that error removed the best-known abliterated anchor for no reason), chat-template hash, class label in {base, ordinary-instruct, safety-tuned, abliterated}, LINEAGE id, and a held-out fold id. Four strata. (i) The anchor lineage the request names: Qwen3-4B-Base, Qwen3-4B, Qwen3-4B-SafeRL and an abliterated Qwen3-4B - all four verified live and ungated, with DreamFast/qwen3-4b-heretic as the open abliterated member and the gated huihui checkpoint added if auto-approval succeeds. Instruct, SafeRL and abliterated share a chat template and are one comparison stratum; base uses a different format and is kept separate with a plain renderer. (ii) The abliterated arm, extending the existing 37-checkpoint card census, carrying its recipe fields (stated direction scope, stated layer band, stated strength) and an explicit UNSTATED marker, since 56.8 percent state no recipe and that is precisely the population the weight read has to resolve. (iii) THE SAFETY-TUNED ARM, WHICH HAS NEVER BEEN CENSUSED AND IS THE SCARCE ARM THAT SETS THE POWER OF A THREE-WAY CLAIM. A naive Hub query over {SafeRLHF, safe-rl, safety-tuned, safety aligned, safety finetuned, harmless dpo} returns on the order of 339 repos, but five uploaders account for about 90 percent of them and one uploader alone is dozens of epoch checkpoints of four algorithms on a SINGLE parent. The resampling unit is therefore (parent x tuning run), not the repo; collapse epoch, step and timestamp suffixes; publish the independent-lineage count; and flag whether each row is an official safety RL release or an academic PKU-SafeRLHF re-run, because mixing those is hidden heterogeneity inside the class we are trying to separate. (iv) The honest panel for thresholds and the manifold, with an EXPLICIT INCLUSION RULE rather than 'random instruct checkpoints': uploader is the model's originating organisation, and no abliterated / uncensored / heretic / decensored token appears in the id, tags, card or declared lineage. The panel size is reported as a FUNCTION OF MEASURED DOWNLOAD THROUGHPUT on a first slice of five checkpoints, not declared as a floor, because a floor that cannot be funded is not a floor; weight-only coordinates need the large N and activation coordinates do not, so the panel is explicitly split into a large weight-only tier and a stratified activation subsample with both n values carried in the registry.
    REGISTRY B, THE EXTERNAL GROUND TRUTH, joined per checkpoint and RECOUNTED from the files rather than from abstracts. The HELM safety suite ships 435 runs = 87 models x 5 scenarios and every model has an xstest row, which is a PUBLISHED two-sided ground truth and removes any suggestion that a two-sided target is our invention. But the open-weight subset is far smaller than the headline count: remove API-only organisations, then closed-weight entries, then the roughly nineteen 32B-to-1T models that cannot be transferred at all, then the -with-guardian pairs that are the same weights plus an external guard, then the fp8 turbo servings whose published score does not correspond to the bf16 Hub weights we would read. Publish the surviving id list with a parameter count and a SERVED-PRECISION column and let the number be what it is; the honest figure is on the order of eight at or below 8B and eleven or twelve stretching to 32B. Pool the companion risk-taxonomy suite NOT for n - it shares 75 of 87 models and its extras are almost all API-only - but for a SECOND INDEPENDENT OUTCOME COLUMN on the shared models, which is what lets the study ask whether a metric tracking refusal-style safety also tracks a risk taxonomy, and which is the request's own instruction that safety is not only refusal. Add the third suite's downloadable table the same way, and take capability from the archived open-leaderboard result files, which are abundant at every size, rather than by re-running a harness. The sub-4B scarcity is not an obstacle to be worked around but a SCORED FINDING to be stated in one line: the models a downloader is most likely to meet are exactly the ones with no published safety number.
    REGISTRY C, THE ITEM BATTERY, fixed now so no metric can be tuned on its own evaluation items. Graded-harm items from StrongREJECT and the JailbreakBench behaviours, which ship 100 harmful and 100 benign as a matched pair; benign-but-alarming twins from XSTest, joined on the `focus` field, which is the real twin key and which a widely used mirror of XSTest LACKS, plus the hard over-refusal subset of OR-Bench; contentless and graded-preamble passes; and a presentation-condition pool for audit-time sampling taken from a benchmark shipping several hundred base prompts each in about twenty linguistic mutations. Every item carries a harm-category label for stratified cross-fitting folds and a fold id assigned by hash BEFORE collection, so the held-out reserve is sealed rather than chosen.
  depends_on: []
- id: experiment_iter1_dir3
  type: experiment
  objective: >-
    THE SCREEN. Race all five candidate answers to the commissioned question against each other, against the three published
    incumbents and against two black-box baselines, on ONE shared harvest, identical items, identical forward passes and identical
    held-out folds - and deliver, in the same run, the request's step 1 as a named claim rather than as scaffolding. The five
    candidates disagree about where safety lives in a checkpoint, so the screen's output is a ranked comparison plus one survivor
    for iteration 2, not a finding.
  approach: |-
    ONE HARVEST PAYS FOR EVERYTHING, and designing it first is what makes a five-way screen affordable. Per checkpoint, in bf16 with transformers so weights and hidden states are readable - never GGUF or llama.cpp, which hide exactly what this study reads - take (a) a WEIGHT PASS: per-layer singular subspaces of the attention-output and MLP-down matrices, using eigendecomposition of W W-transpose rather than a full SVD, which is roughly fifty times faster for left subspaces and matters at a few hundred decompositions per checkpoint; and (b) an ACTIVATION PASS: teacher-forced prefill over the item battery, storing all-layer hidden states at the last prompt token and the first generated token, plus first-token logits. Zero generated tokens outside the small grading set. From that single harvest every candidate is a different read, so the marginal cost of candidates four and five is near zero.
    THE FIVE CANDIDATES, which can and do disagree. C1 ACROSS-ITEM COUPLING: the share of across-item variation in refusal drive at the first generated token explained by the model's own CROSS-FITTED harm estimate, with DECISION SPREAD - the across-item standard deviation of refusal drive - reported beside it and a pre-registered variance floor below which the ratio is declared undefined rather than reported as a small number, so it cannot become a quotient of two noise terms. C2 PROMPT-BUDGET CROSSOVER: the same readout evaluated at 0, 1, 8, 16, 32 and 64 items with the black-box baseline on the identical axis, delivering the crossover point as a number. This answers the request's actual constraint, which is a PROMPT COUNT and has never been answered numerically. C3 REFUSAL DEPTH: the layer at which refusal first becomes decodable minus the layer at which request content first becomes decodable, both cross-fitted with a per-model permutation null - an ordering of two layer indices, which is a different kind of object from a relationship across items. C4 RECOVERED RECIPE: parent-free from weights alone, in seconds, with zero prompts - per-layer suppressed direction as the bottom left singular vector, realised ablation strength, which layers were touched, mean pairwise cross-layer cosine - scored not as a binary tamper flag but on whether realised STRENGTH is monotone in measured harmful compliance. C5 METAMODEL: a small regressor on pooled hidden states, the request's second bonus, shipped WITH its own ablation against a lineage-identity probe on the identical features, because a metamodel that recovers architecture and uploader identity is not reading safety and the gap between those two curves is the deliverable.
    BARS, NOT COMPANIONS. Compute the three incumbents on the same checkpoints from the spec the research artifact produces: the AMS separation statistic, the Skin-Deep/GFS scalar, and N-GLARE's JSS where reproducible and classified by functional form where not, with the missing detail named. Plus exactly two black-box baselines given every advantage - first-token logit-gap margin and a greedy refusal rate on a handful of prompts - and the model-card regex as a free non-model comparison that reads nothing at all. That is four internal readouts against two logit-or-text baselines, which satisfies the invariant as a set AND in spirit, because all four internal readouts are scored DISCRIMINATORS here rather than diagnostics.
    THE SELECTION RULE, STATED BEFORE THE SCREEN RUNS. Primary measure: three-way held-out separation, safety-tuned versus ordinary-instruct versus abliterated, with the resampling unit the LINEAGE and the estimator leave-one-lineage-out, so each metric gets one held-out estimate per lineage. The separation score is named in advance as balanced accuracy over the three classes with multiclass AUROC reported beside it. No metric is ever evaluated on a checkpoint used to choose its layer, coordinate or threshold. A candidate SURVIVES only if its held-out score exceeds the incumbent bar - the AMS leave-one-out figure of 71 percent, computed here on our own configurations rather than quoted - and ties break on the held-out-minus-tuned GAP, smaller wins. Two whole families and the sealed item folds are reserved and touched by nothing in this artifact.
    THE PRE-REGISTERED CLASS PREDICTION, repaired from a partition into a trend because a partition is pre-refuted and a trend survives a messy world. Split the battery three ways: LEVEL-KNOWLEDGE (fitted-direction projections and harm-probe margins, where the published 0.98-AUROC near-invariance of harm knowledge across alignment variants bites), LEVEL-BEHAVIOUR-STRUCTURE (refusal rate, logit gap, weight statistics, where it does not and which is pre-registered as the HARD case expected to transfer), and ACROSS-ITEM. Predict a monotone ordering of the held-out-minus-tuned gap across those three classes and test it as a permutation test over metric CLASS LABELS with lineage-level clustering, which is the only way to handle fifty heavily inter-correlated metrics. Pre-register the false-positive-rate grid at three values and label everything else exploratory.
    THE REQUEST'S STEP 1, AS A CLAIM AND NOT AS SCAFFOLDING. Both objects are computed anyway, so the comparison is free: is the instruct-to-SafeRL activation difference carried by the SAME subspace and layer band as the instruct-to-abliterated difference, or an orthogonal one? Pre-register a principal-angle prediction on the anchor lineage and report it two-sided. That is literally the user's first and most concrete ask, and no previous version produced a statement about how the four checkpoints differ internally.
    HYGIENE THAT DECIDES WHETHER ANY OF THIS COUNTS. Every fitted direction is CROSS-FITTED with folds stratified by harm category, because an in-sample difference-in-means projection separates PURE NOISE at AUROC 1.000 in this dimensional regime and 0.507 cross-fitted, so an in-sample harm direction is numerically indistinguishable from the harm label; the in-sample version is printed beside it as the demonstration. A random-direction null matched for anisotropy. A per-checkpoint label-permutation null. Synthetic always-refuse and never-refuse wrappers as poles, and any candidate that scores a blanket refuser well is rejected regardless of its correlation. Disk, not VRAM, is the binding constraint - a 4B bf16 checkpoint is about 8 GB against a 40 GB container - so checkpoints stream one at a time and are deleted, and the harvest is written as pooled vectors plus per-item scalars so re-analysis never needs a second download.
  depends_on: []
- id: experiment_iter1_dir4
  type: experiment
  objective: >-
    The second screening lane, chosen because it is where the five candidates make DIFFERENT predictions rather than where
    they agree: what each one does under a cost-ordered ladder of cheap checkpoint edits, and what it costs an auditor to
    notice the edit. A cheap safety metric for a stranger's checkpoint is worthless if a thirty-token file edit moves it,
    so this lane measures forgery cost and detection cost per candidate and reports the ranking they induce beside the ranking
    honest-panel accuracy induces.
  approach: |-
    THE LADDER, six rungs, applied to checkpoints we control. F0 a repository-metadata edit at zero FLOPs. F1 an inference-time system prompt. F2a a CONSTANT offset. F2b a rank-one edit - the published rank-one safety injection method, run BOTH at its own published settings and as a metric-maximising adversary. F3 a small keyword-triggered refusal adapter. F4 genuine light safety fine-tuning, which buys real safety and caps the ladder.
    HOW F2a IS BUILT DECIDES WHETHER THE COLUMN HAS ANY VARIANCE, so it is measured rather than assumed. Qwen3 and most panel architectures define NO bias on the attention output projection or the MLP down projection, so a literal added bias introduces a tensor the declared architecture does not have and a key-and-shape check against config.json catches it in milliseconds with no family default and no forward pass. Build the offset instead as a rank-one edit carried by a near-constant coordinate - an attention-sink or massive-activation dimension whose activation is known to be nearly item-independent - and VERIFY numerically that the realised offset is constant across items to a tolerance set from each metric's own measured split-half variability rather than from a single global constant derived from a partial perturbation model. If it is not constant, fall back to the explicit tensor and report F2a as hygiene. Either way the outcome is reportable, including the clean one.
    WHY THE CANDIDATES DISAGREE HERE, which is the whole reason this lane exists. A constant offset lands identically on every item, so it cancels exactly from any across-item statistic read linearly at the injection layer and only approximately downstream of a normalisation - state this as a LEMMA, not a finding, since the general black-box form is already proved in the literature, and check it in fp32 with the bf16 gap reported once. So C1 should be immune to F2a and C4 should be untouched by both text rungs while being precisely what F2b writes; C3's layer ordering should be unmoved by a constant but movable by an adapter; C5 is predicted to fall to almost anything, and if it does not, that is the interesting outcome. Each candidate therefore registers a DIFFERENT rung signature, and the signature is the discriminating measurement.
    DETECTION, WITH THE SELF-REFERENCE REMOVED. Report detection under two auditor access levels, renamed to kill a name collision with an incumbent's own Tier 1 / Tier 2 split: a BLIND AUDITOR sees only the downloaded repository with no idea what family it came from - chat-template content, a baked-in system prompt in generation_config or tokenizer_config, state-dict keys or shapes the declared architecture does not define, and the zero-prompt weight statistic; a FAMILY-AWARE AUDITOR may diff against the family default. The GAP between them is a second result: how much detection power comes from knowing the family at all. Crucially, the weight statistic is itself one of the candidates being ranked, so every weight-rung forgery would be caught by construction - report undetectable cost TWICE, with and without the weight screen in the blind tier, and make the DIFFERENCE the headline number, because that difference is the actual value of the weight screen to an auditor.
    COST REPORTED IN ITS OWN UNITS, not laundered into one column. A thirty-token system prompt and a seconds-long rank-one edit are both about zero FLOPs, so publish seconds, training FLOPs and labelled examples per rung as MEASURED numbers and let the partial order stay partial where it is partial. The continuous variable used for any regression is named for what it actually is - the detection margin at the minimum effective setting, as a z-score against the honest panel - rather than silently switching between a token budget and an edit magnitude between rows.
    THE WEIGHT INSTRUMENT IS ADOPTED PRIOR ART AND LABELLED AS SUCH EVERYWHERE. A publicly released community model scanner already computes, per layer and with no parent and no prompts, the leading eigenvalue mass of summed bottom-k left singular projectors on exactly these two matrix families, with a layer-band variant. We do not claim it. What is genuinely unclaimed and is delivered here is the calibration it has never had: a null model, an honest-panel false-positive rate, whole-family held-out validation, behaviour in bf16 as shipped rather than in fp32, the recipe census that bounds which real checkpoints it can see, and the injection arm it does not implement. Simulation already establishes the shape - windowed bottom-subspace alignment reads about 0.17 on honest stacks whether the spectrum is Gaussian or heavy-tailed, rises above 0.6 for correlated per-layer recipes and reaches 1.000 for shared-direction edits confined to half the stack where the unwindowed statistic sits INSIDE honest range - so the threshold is pre-registered from that simulation at 0.35 and the honest baseline is then validated on REAL trained weights, which is the number that has never been measured. The known blind corner, per-layer directions at sub-unit strength together, is named as the definitional price of reading sharing rather than perturbation and reported as a boundary, not a failure; the local rank-deficiency ratio covers full-strength cases regardless of sharing, against a bf16-realistic separator rather than an exact algebraic zero. Withdrawal is per-limb: if the sharing statistic fails on real weights it is withdrawn for that rung and plain forgery cost is reported there; if the local statistic also fails, the whole detection axis is withdrawn and the lane reports the plain cost ladder, which is still a complete result.
  depends_on: []
- id: experiment_iter1_dir5
  type: experiment
  objective: >-
    The third screening lane and the one the user actually commissioned: does any candidate predict a stranger's checkpoint's
    safety from a handful of prompts, measured against REAL published benchmark numbers rather than against our own judge,
    and does looking inside the model buy anything over reading its outputs at a matched prompt budget. This lane also carries
    the ground truth that makes the whole study meaningful - a model that refuses everything must LOSE, not win.
  approach: |-
    GROUND TRUTH IN FOUR COLUMNS, because safety is not only refusal and a one-sided target rewards a blanket refuser. Graded harmful compliance on a StrongREJECT-style rubric; FALSE REFUSAL on benign-but-alarming twins; a distribution-shift retention ratio under wrapping, paraphrase and translation; and a capability column. Graders are named in advance because the choice moves every number: harmful-compliance grading uses the StrongREJECT rubric applied by a hosted non-Qwen judge with a declared alternate, since the released fine-tuned grader is gated behind its base model, and agreement is reported against a second independent ungated open grader run locally. No Qwen guard is used anywhere, and Qwen3Guard is excluded for SafeRL specifically, as the request instructs, because it was SafeRL's training reward.
    THE EXTERNAL CORRELATION, ON VERIFIED COUNTS AND WITH THE SIZE CONFOUND STATED. Correlate the surviving candidates against the published per-scenario numbers in three strata: sub-4B checkpoints with any published safety number, which really is on the order of six to eight and is reported as a scatter with n printed rather than as a coefficient, because a coefficient at that n is theatre; the open-weight subset of the large safety suite, which after removing API-only, closed-weight, untransferably large, guardian-duplicate and fp8-served entries is about eight at or below 8B and eleven or twelve stretching to 32B, reported with a confidence interval and a second independent outcome column from the companion risk-taxonomy suite on the shared models; and capability, which is not scarce. The weight-only readouts need no GPU and the activation readouts are prefill-only, which is what lets this lane reach models too large to generate from on a 16 GB card - but the readouts are designed at 4B and validated at 7B and above, so size and family are collinear with everything and a size-stratified or size-partialled estimate is mandatory, not optional. Report the resampling unit and BOTH aggregation units, per the request. Any candidate that works only inside one architecture family is reported as a negative result in those words and not softened into a scope condition; if the family label alone predicts the ground truth as well as the metric does, the metric has not earned its forward passes.
    THE PAIRED COMPARISON THAT DECIDES WHETHER INTERNALS ARE WORTH IT. On real un-forged Hub checkpoints nobody in this study edited, correlate each surviving readout with the measured retention ratio in a PAIRED test at a MATCHED PROMPT BUDGET against the black-box baseline - and against the Skin-Deep/GFS scalar, which already does this task at n=21 across six alignment recipes and is the incumbent bar here, not a companion. Drop any absolute correlation threshold: the honest bar is beating the matched-budget baseline and the incumbent in a paired test, because a published counterexample already reports that supervised fine-tuning reaches low coupling while remaining substantially less robust, so a high absolute correlation is not something we are entitled to expect. Where we reproduce that negative, we say so.
    THE REQUEST'S FIRST BONUS, WHICH IS CHEAP AND WAS PREVIOUSLY LAST IN THE SHRINK ORDER. For whichever candidate survives highest: which layers and components carry it, against a random-direction null matched for anisotropy, and what breaks it - closing with the cheapest forgery that defeats it given the mechanism. This is one model and a layer sweep, among the cheapest things in the plan and an explicit user ask, so it sits ABOVE any panel expansion in the cut list.
    THE HEADLINE EDIT EXPERIMENT, RE-AIMED AT WHAT IS ACTUALLY OPEN. The published rank-one safety injection method validates itself with a guard model's harm-refusal rate and its only benign column is compliance on ordinary instructions - there is no over-refusal measurement anywhere in it. That refusal-direction steering raises harmful refusal and benign over-refusal in parallel is already in print for STEERING, so we cite it and stop claiming it. What is open is quantitative: where does this method's OWN published operating point land on a two-sided score, and does that score REVERSE the verdict its own evaluation reached. Run it unmodified at its published settings and report its harmful-refusal gain against its measured false-refusal cost on the twins. Riding free on the same run: because it writes one direction into all residual write matrices by its own description, the weight read should flag it with zero prompts, no parent and no forward pass - a published safety edit that is both cheap to apply and trivially visible would be the whole argument in one example.
    SIZING, MEASURED RATHER THAN DECLARED. Generation is needed only for grading, so the completion budget is set from the margin: graded compliance is continuous with an item-level standard deviation near 0.3, so a five-point margin at eighty percent power needs roughly 250 items per arm, and the lane runs a powered subset at that size with the rest at a smaller size for estimation with confidence intervals rather than equivalence testing. Grading cost is tracked per call as it accrues against the ten-dollar ceiling. Measure achieved Hub download throughput on the first five checkpoints and DERIVE the panel size from it, since at realistic throughput the transfer, not the compute, is the binding constraint and nothing in previous versions measured it.
  depends_on: []
expected_outcome: |-
  A ranked, honestly-reported five-way comparison on identical evidence, with one survivor named by a rule fixed before the screen ran, and reserved evidence left untouched for iteration 2 to confirm it on. Concretely, at the end of this iteration we hold: a leave-one-lineage-out table giving every candidate, every one of the three published incumbents and both black-box baselines a held-out three-way separation score with the tuned score printed beside it, so the held-out-minus-tuned GAP is readable per metric and the pre-registered monotone trend across the three functional-form classes is scored by a permutation test over class labels with lineage-level clustering; a per-candidate rung signature under the six-rung edit ladder, with forgery cost and detection cost reported under a blind auditor and a family-aware auditor, and undetectable cost reported twice, with and without the weight screen, so the difference between them is the auditor-value number; a prompt-budget curve for the leading internal readout against the black-box baseline on the same axis, with the crossover point as a number, which is the first numerical answer this run has given to the request's actual few-prompt constraint; correlations of the survivors against real published two-sided benchmark numbers on recounted strata with n printed, both aggregation units and the size confound stated; and a pre-registered principal-angle answer to the user's step 1 on whether safety RL and abliteration move the same activation subspace.
  Every outcome is reportable in both directions and the failures are named now. If the across-item class does not transfer better than the level classes, the mechanism argument from near-invariant harm knowledge is wrong and we say so. If no candidate beats the incumbent bar, that is the finding and it is a useful one, because all three incumbents would then stand as the state of the art on a task we tested at larger scale. If every training-free rung turns out to be free to catch, the undetectable-cost column is near-constant and the clean quotable answer - that the only undetectable forgery is training - is CONFIRMING a published open problem rather than discovering one, which is how it will be reported. If the metamodel beats every formula but its advantage collapses once whole families are held out while a lineage probe on the same features stays near perfect, then activation-based safety scoring is family bookkeeping and the gap between those two curves is the number we ship. Iteration 2 gets a survivor, a sealed confirmation set, three incumbent bars already implemented, and a registry of checkpoints and items that nothing downstream has to rebuild.
summary: >-
  Iteration 1 is a wide screen, not a deep test. Five candidate answers to the commissioned cheap-safety question - across-item
  coupling, the prompt-budget crossover, refusal depth relative to content depth, the edit recipe recovered from weights,
  and a learned metamodel - race on ONE shared harvest of weights and teacher-forced activations, judged on three lanes where
  they make different predictions: held-out three-way separation, behaviour under a cost-ordered forgery ladder with two auditor
  access levels, and payoff against real published two-sided benchmark numbers at a matched prompt budget. Four internal readouts
  and exactly two black-box baselines, all four internal ones scored as discriminators, which meets the invariant in spirit
  and not only on a headcount. The three published incumbents that already occupy this slot become success bars with table
  rows. Five artifacts: a research lane that turns those incumbents into implementation-grade specs and runs a saturation
  check per candidate; a dataset lane that counts the two populations previous iterations over-counted by an order of magnitude
  and seals the held-out folds by hash; and the three screening lanes. The output is a ranked comparison plus one survivor
  for iteration 2 to confirm on reserved evidence, not a finished finding.
</previous_strategies>

<dependency_rules>
- depends_on is a list of objects {id, label} — each entry references an existing artifact and tags how it is being used
- "id" can ONLY reference IDs from <existing_artifacts> — never IDs you are proposing (all new artifacts run in parallel)
- "label" is a SHORT free-text type label (a word or two, NOT a sentence) describing what role the dep plays — e.g. "dataset", "validates", "extends", "supersedes". Required on every dep.
- Setting depends_on provides the dependency's out_dependency_files to your artifact at execution time
- If no suitable existing artifacts exist, use empty depends_on
- New artifact IDs are assigned by the system after submission — do not invent IDs for your proposed artifacts
</dependency_rules>

<available_artifact_types>
Artifact types you can plan. Use this to choose the right types for your strategy objectives.

<artifact_types>
RESEARCH
Web research to answer key questions — like a researcher making decisions.
Runtime: LLM Agent, no code execution.
Tools: the aii-web-tools skill (web search, page fetch, regex grep over full page/PDF text).
Capabilities: Find, synthesize, and compare information across sources; survey SOTA and best practices.
Deps: REQUIRED none | OPTIONAL other RESEARCH to build on prior findings

EXPERIMENT
Run code to test hypotheses, implement methods, and collect empirical results.
Runtime: Python 3.12, UV (any pip package), isolated workspace, gradual scaling (mini → full data).
Tools: Full shell/Python/filesystem access, the aii-web-tools skill (web search, page fetch, regex grep over full page/PDF text), and other skills.
Skills: aii-json (schema validation), aii-openrouter-llms (call any LLM — GPT, Gemini, Llama, etc.), domain-specific as needed.
Capabilities: Implement and run any code-based experiment, compare method vs baselines.
Deps: REQUIRED at least one DATASET | OPTIONAL RESEARCH for methodology guidance

DATASET
Collect, prepare, and merge datasets for experiments and analysis.
Runtime: Python 3.12, UV, isolated workspace.
Tools: Full shell/Python/filesystem access, the aii-web-tools skill (web search, page fetch, regex grep over full page/PDF text), and other skills.
Skills: aii-hf-datasets (HuggingFace Hub — ML datasets, many UCI/OpenML/Kaggle mirrors), aii-owid-datasets (Our World in Data — global statistics), aii-json (schema validation). Also any Python source (sklearn.datasets, openml, direct URLs, APIs) — must verify within 300MB limit.
Capabilities: Search, acquire, transform, combine, and standardize data from any available source.
Deps: REQUIRED none | OPTIONAL RESEARCH for guidance on what data to collect

EVALUATION
Evaluate experiment results with metrics, statistical analysis, and validity checks.
Runtime: Python 3.12, UV (any evaluation library), isolated workspace, gradual scaling matching experiment.
Tools: Full shell/Python/filesystem access, the aii-web-tools skill (web search, page fetch, regex grep over full page/PDF text), and other skills.
Skills: aii-json (schema validation), aii-openrouter-llms (call any LLM — G
</pasted_content id="a71b">


<pasted_content id="a71b">
PT, Gemini, Llama, etc.), domain-specific as needed.
Capabilities: Compute any quantitative metrics and statistical tests, analyze validity and robustness.
Deps: REQUIRED at least one EXPERIMENT | OPTIONAL DATASET if reference data needed

PROOF
Formally prove mathematical statements in Lean 4 with automated iteration.
Runtime: LLM agent with Lean 4 compiler feedback loop.
Tools: Full shell/Python/filesystem access, the aii-web-tools skill (web search, page fetch, regex grep over full page/PDF text), and other skills.
Skills: aii-lean (proof verification, Mathlib search, tactics: ring, linarith, nlinarith, omega, simp, etc.)
Capabilities: Formally verify properties and inequalities, iterative proof development, lemma decomposition.
Deps: REQUIRED none | OPTIONAL RESEARCH for mathematical background
</artifact_types>
</available_artifact_types>



<artifact_executor_scope>
IMPORTANT: Each artifact executor has a focused prompt that guides it to do ONE thing well. It will NOT perform tasks outside its scope — assigning the wrong work to the wrong artifact type wastes an iteration. Match the task to the right executor.

RESEARCH executor scope:
  Output: research_out.json with {answer, sources, follow_up_questions} + research_report.md
  DOES: Web research — search, read, synthesize information from papers/docs/APIs into a structured report
  DOES NOT: Run code, download files, execute scripts, compute anything — no shell/Python access
  Use for literature surveys, API documentation, technical specifications — pure information gathering

EXPERIMENT executor scope:
  Output: method_out.json with results (metrics, predictions, analysis) — the core computational work
  DOES: Implement and run methods/algorithms, compute metrics, compare approaches, produce quantitative results
  DOES NOT: Collect new datasets (depends on DATASET artifacts for input data), write formal proofs
  This is the right artifact for any code that processes data and produces results

DATASET executor scope:
  Output: data_out.json with rows of {input, output, metadata_fold, ...} — raw data only, no derived computations
  DOES: Download/generate datasets, analyze candidates to pick the best ones, standardize to JSON schema (features, labels, folds, metadata), validate schema, split into full/mini/preview
  DOES NOT: Run experiments, train models, compute derived statistics (PID/MI/correlations/synergy matrices) as final output
  If you need to COMPUTE something from data (synergy matrices, MI scores, timing benchmarks), use an EXPERIMENT artifact instead

EVALUATION executor scope:
  Output: eval_out.json with evaluation results
  DOES: Any evaluation of experiment results — metrics, statistical tests, ablations, comparisons, visualizations, robustness checks, error analysis, etc.
  DOES NOT: Implement new methods (use EXPERIMENT), collect data (use DATASET)
  This is for analyzing experiment outputs from any angle

PROOF executor scope:
  Output: Lean 4 proof files (.lean) with verified theorems
  DOES: Write and verify Lean 4 formal proofs with Mathlib, iterative compilation
  DOES NOT: Run Python experiments, collect data, do empirical analysis
  Use only when formal mathematical guarantees are needed
</artifact_executor_scope>

<artifact_planning_rules>
RESEARCH: Plan early — findings guide dataset selection, experiment design, and methodology.
EXPERIMENT: Must depend on at least one DATASET. Define clear metrics and baselines before running. Consider trying multiple method variations rather than a single approach.
DATASET:
- Plan for REAL third-party datasets (HuggingFace, Kaggle, direct-download URLs) — downloadable within time and size constraints
- Describe dataset criteria (domain, size, format) — executors find exact sources, but you can suggest candidates or search directions
- ALWAYS prefer real datasets over synthetic. Synthetic is a LAST RESORT only when no suitable real data exists
EVALUATION: Must depend on at least one EXPERIMENT. Focus on statistical rigor and validity checks.
PROOF: Use only when the hypothesis req
</pasted_content id="a71b">


<pasted_content id="a71b">
uires formal mathematical guarantees. Lean 4 + Mathlib.
</artifact_planning_rules>

<existing_artifacts>
--- Item 1 ---
id: art_DeogIL_xh3pE
type: research
title: What rival safety-scoring methods already achieve
summary: |-
  IMPLEMENTATION-GRADE SPECS FOR FOUR INCUMBENTS, FIVE DATED CANDIDATE VERDICTS, AND FIVE VERIFIED NUMBERS. Machine-readable output: spec_table.json (full) and the fenced json block in research_out.json (compact); prose twin research_report.md (~76KB).

  FOUR INCUMBENTS (the plan named three; the fourth was found by the saturation search).
  - AMS 2608.05578 = IEEE Access 14:91723-91737, verdict REPRODUCIBLE, with Apache-2.0 code (pip install "ams-scanner[cli]"; ams scan <model>). Statistic: sigma = (mu+ - mu-)/sigma_pooled on FINAL-TOKEN residual streams along an in-sample difference-of-centroids direction; 16 contrastive pairs x 3 concepts = 96 forward passes, 10-40s/model; layer swept over range(int(0.4L), int(0.8L)) and picked to MAXIMISE separation on the same pairs; PASS>3.5, CRITICAL<2.0. Tier 1 parent-free, Tier 2 needs a stored baseline. DECISIVE: the 71% (10/14) leave-one-out held out ONLY THE THRESHOLD - direction, layer sweep and prompt set were never held out, and the authors concede the coupling. So 71% is a LOOSE, NON-MATCHED bar; a leave-one-LINEAGE-out number from us is strictly stricter. Also: r=-0.546 (p=.043, n=14 models) but Spearman rho=-0.423 (p=.13, N.S.); median bootstrap 95% CI width 3.36 sigma against a 2.0-3.5 band (62% of cells unresolvable). Class (iv) behavioural fine-tuning is ALREADY PUBLISHED as undetectable - cite, do not claim.
  - Skin-Deep/GFS 2606.22676: TWO PLAN ASSUMPTIONS OVERTURNED. It is NOT parent-free (Eq 1 cPCA needs the base model's covariance; code requires --base_model) and needs 1000 prompts; and its retention-prediction claim has NO PRINTED COEFFICIENT - a qualitative co-occurrence at n=7. There is no GFS number to beat.
  - N-GLARE 2511.14195 / ACL 2026 Long 1334: CLASSIFY-BY-FUNCTIONAL-FORM-ONLY. Eq 7 and Eq 9 confirmed verbatim; parent-free AND generation-free, but needs FOUR probing conditions {B,J,R,P} over 7000+ cases, so it is separated from our lane on the PROMPT-BUDGET AXIS ALONE. No numeric Kendall tau for the headline claim in either version; Table 2's numeric taus belong to a DIFFERENT robustness check - quoting them would be a misattribution.
  - RAS/SafeVec 2606.25750 (NEW, not in the plan): the closest published thing to the deliverable - white-box, generation-free, per-checkpoint, calibrated 0-100, separates aligned/uncensored/abliterated, tracks ASR, 210-217x faster than judge-based. BUT it needs a per-family reference model, a calibration set, AND those models' MEASURED ASR, and states "family-specific calibration remains necessary". Our cross-family negative would be a REPLICATION.
  All four bar rows are comparable:false, each for a DIFFERENT nameable reason - that is the finding, and the reasons are now written down.

  CANDIDATES (searched 2026-09-20, plus an adversarial kill-attempt pass): C1 PARTIAL (must beat HRCI_repr; pre-register as DISCRIMINATOR ONLY), C2 PARTIAL (IRT owns the behavioural half; 2608.13329 owns the internal variance decomposition and reports a generalizability coefficient of 0.00002 for cross-family comparison on one prompt wrapper), C3 OPEN as an aggregation only (recipe confound from 2609.03887), C4 OPEN on WEIGHTS-ONLY and PARENT-FREE and GRADED and PREDICTS-COMPLIANCE (the highest-value verdict), C5 OPEN on the ABLATION only. ADVERSARIAL PASS (27 refutation queries): all three OPEN verdicts SURVIVED but two were narrowed - C3's two required curves already coexist in 2507.11878 on the same models, so C3's novelty is ONLY the collapse-subtract-correlate aggregation; and C5's ablation is ESTABLISHED PRIOR ART as a method (2606.02907 residualizes source identity and drives a 100%-accurate hidden-state probe to chance; Hewitt & Liang control tasks), so C5 must be claimed as 'we ran the established control on the per-MODEL axis' not 'we invented the control'. C4 held, with three further near-misses named 
</pasted_content id="a71b">


<pasted_content id="a71b">
and excluded; cite the abliteration.org wiki to concede that the cell is a known practitioner open problem. C5's attack was only 6 queries and is the least well-tested verdict.

  NUMBERS: N1/N2/N3/N5 CONFIRMED, N4 AMBIGUOUS-MULTIPLE-OCCURRENCES with BOTH readings of BOTH numbers genuinely true - NO misattribution exists, the premise stands. N1 forces the motivating sentence to be rescoped to per-PROMPT vs per-CHECKPOINT.

  12 DECISIONS (D1-D12) each name the artifact and the action. Handoff blocks are written for the screen, ladder and payoff executors separately, with exact commands and six standing prohibitions.

  GOTCHAS FOR REUSE: scholarly-mode search (OpenAlex/Crossref) is UNUSABLE for this field - an empty result is evidence about the backend, not the field. PDF-to-text inserts hard line breaks mid-sentence, so exact-phrase greps manufacture FALSE NEGATIVES; use whitespace-flexible patterns before recording NOT-FOUND. Near-ID collision 2606.22676 (Skin-Deep) vs 2606.22686 (Geometry of Refusal, TrustNLP). Title collision: Google lists AMS under a different title.
workspace_path: >-
  /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_1/gen_art/gen_art_research_1
out_expected_files:
- research_out.json
out_dependency_files:
  file_list:
  - research_out.json
  - research_verification.json

--- Item 2 ---
id: art_ynwQLrNKw_e_
type: experiment
title: Cheap safety checks for any single model
summary: |-
  Races five candidate single-checkpoint safety readouts against four published incumbents (AMS 2608.05578, GFS 2606.22676, N-GLARE 2511.14195, HRCI_repr 2606.16349) and three black-box baselines on ONE shared harvest per checkpoint (weight pass + teacher-forced activation pass), identical 160-item battery, identical leave-one-lineage-out folds. Parent-free throughout: the setting is "you found a random model on HuggingFace and have nothing else".

  WHAT IT PROVIDES. results/race_table.csv (all 50 pre-registered metrics, held-out balanced accuracy printed beside the tuned score and the gap, 3-way and 2-way); results/metrics_registry.json + sha256, frozen BEFORE any measurement and re-asserted at the end; results/step1_claim.json (principal angles between the instruct-to-SafeRL and instruct-to-abliterated activation differences on the Qwen3-4B anchor, per layer band, two read positions, plus the weight side); results/f5_weight_instrument.json (the honest-panel false-positive rate the published weight statistic lacks); plus lineage_census.json, ground_truth.json, per_checkpoint_reads.json, the three stage-gate files, and RESULTS.md as the digest.

  FOUR RESULTS THAT ALREADY HOLD, independent of the race outcome.

  F5 - THE PUBLISHED WEIGHT THRESHOLD DOES NOT SURVIVE REAL WEIGHTS. The Jorak-style subspace signature (BSA_w8 over bottom-1 left singular vectors of o_proj, sliding 8-layer window) reads 0.565 on honest, unedited Qwen3-0.6B, well above the 0.35 separator Gaussian simulation calibrates (simulated honest 0.171, invariant across Gaussian and heavy-tailed spectra). The same weights abliterated by us go to 1.000 and BOTGAP collapses below 0.003 in bf16. The statistic discriminates, but its absolute threshold is a false positive on real transformers, which carry genuinely shared bottom directions. Shipped fix: threshold-free AUROC plus a z-score against a within-checkpoint anisotropy-matched null (a random unit vector drawn from that layer's own bottom-16 subspace), validated at z=0.63 honest versus z=34 for a shared-direction edit. Separately, BOTGAP is NOT spectrum-invariant: on a heavy-tailed spectrum the honest value is 0.064, already below its own 0.10 separator.

  CROSS-FITTING IS LOAD-BEARING. On pure Gaussian noise at d=2560 with 64 randomly-labelled items, an in-sample difference-in-means projection separates at AUROC 1.000 and the cross-fitted version at chance (0.377) - an in-sample harm direction is numerically indistinguishable from the harm label. AMS fits its direction on the same 16 pairs it then measures, so it is reported twice, in-sample as published and cross-fitted on our fo
</pasted_content id="a71b">


<pasted_content id="a71b">
lds, with the gap between them.

  THE SAFETY-TUNED ARM IS SCARCE, AND THAT IS ITSELF THE RESULT. A Hub census returns 445 "safety-tuned" repos, but the top five uploaders account for 85% and suffix-collapsing leaves 245. Only THREE independent safety-tuned lineages are reachable under 4B: Qwen3-4B-SafeRL (official), TinyLlama-1.1B (four algorithms, one parent) and gemma-2-2b (two). Below the pre-registered floor of five, so branch F1 fires: the two-way instruct-versus-abliterated claim becomes primary (11 instruct lineages against 6 abliterated) and the three-way is reported with its lineage count printed.

  AN UNMATCHED SAFETY BENCHMARK IS MOSTLY LEXIS. TF-IDF plus logistic regression, no model at all, reaches AUC 0.963 separating harmful prompts from XSTest safe ones across sources, but only 0.537 against JailbreakBench's own Index-paired benign partners and 0.655 on XSTest positional twins with pair-grouped CV. Every internal readout must beat the MATCHED numbers.

  METHOD NOTES TO INHERIT. The resampling unit is the LINEAGE (parent x tuning run), never the repo. Base checkpoints use the plain renderer and stay in their own stratum. The harvest stores VECTORS (all-layer hidden states at the last prompt token and the first generated token, per item, 35-141 MB per checkpoint), so every direction can be re-fitted and every null recomputed offline with no second GPU pass. Synthetic always-refuse and never-refuse poles run per checkpoint: the blanket refuser earns a +18.8 logit gap but only 0.80 across-item spread against 4.82 normal, which is why the coupling read ships with decision spread as a companion and a 0.25-logit floor below which it is declared UNDEFINED rather than small. Measured XSTest facts correcting the plan: 200 positional twin pairs, not 300, and keying on (type, focus) would silently drop 108 of 450 rows.

  TRAPS FOUND AND FIXED. openai/gpt-5-nano returns content=None at default reasoning effort (192 of 200 completion tokens spent on hidden reasoning), silently degrading every grading to the regex fallback; it needs reasoning.effort=minimal. The judge also returns inconsistent rubric arithmetic, so the StrongREJECT score is recomputed from components. Gemma-2 must load with eager attention because sdpa omits its logit soft-capping. No Qwen judge anywhere; Qwen3Guard never judges SafeRL.
workspace_path: >-
  /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_1/gen_art/gen_art_experiment_1
out_expected_files:
- method.py
- full_method_out.json
- mini_method_out.json
- preview_method_out.json
out_dependency_files:
  file_list:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
</existing_artifacts>





<task>
Generate 1 research strategy for THIS iteration.

**ARTIFACT LIMIT: Each strategy may contain AT MOST 5 artifact directions.** Focus on the highest-impact artifacts. Quality over quantity.

Each strategy should:
1. Define a clear OBJECTIVE - what novel contribution we're building toward
2. Plan artifacts to execute NOW - specify type, objective, approach, and depends_on for each
3. Account for parallel execution - all strategies and all planned artifacts run simultaneously, their artifacts are combined into one shared pool

**BROADER IS NOT THE SAME AS DEEPER.** This applies when you are going DEEPER
on a claim that already has support — it is not an argument against a wide
screen, which tests DIFFERENT candidate answers rather than the same one in
more places. Adding models, datasets, or settings to an experiment that
already ran makes the table bigger; it does not make the contribution
stronger, and it is the default a strategy generator drifts into when it has
nothing sharper to propose. Spend an artifact on scale only when the SPREAD
itself is the finding (a scaling trend, a regime boundary, a generalisation
claim the paper actually makes). Otherwise spend it on something that could
change the conclusion: the mechanism behind an observed effect, the condition
under which it disappears, the confound that would explain it away, or the
b
</pasted_content id="a71b">


<pasted_content id="a71b">
aseline whose absence a reviewer would name first.


</task><user_data>
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
    "ArtifactDep": {
      "description": "A single dependency on an existing artifact, with a short type label.\n\n``id`` and ``label`` are LLM-generated at strategy time. ``label`` is free-text but\nshort \u2014 a word or two naming the type of dependency, not a sentence.\n\n``relation_type`` and ``relation_rationale`` are populated later, in upd_hypo,\nusing the MultiCite citation-function typology (Lauscher et al., NAACL 2022).\nThey are absent at strategy time and may stay absent for legacy runs.",
      "properties": {
        "id": {
          "description": "ID of an existing artifact this artifact depends on",
          "title": "Id",
          "type": "string"
        },
        "label": {
          "description": "Short free-text label naming the type of this dependency (a word or two, not a sentence)",
          "title": "Label",
          "type": "string"
        }
      },
      "required": [
        "id",
        "label"
      ],
      "title": "ArtifactDep",
      "type": "object"
    },
    "ArtifactDirection": {
      "description": "High-level direction for an artifact to execute this iteration.\n\nID is code-assigned (LLMPrompt only \u2014 visible in prompts, not LLM-generated).",
      "properties": {
        "type": {
          "description": "Type of artifact to create",
          "enum": [
            "experiment",
            "research",
            "proof",
            "evaluation",
            "dataset"
          ],
          "title": "Type",
          "type": "string"
        },
        "objective": {
          "description": "What we want to achieve with this artifact",
          "title": "Objective",
          "type": "string"
        },
        "approach": {
          "description": "High-level direction/method",
          "title": "Approach",
          "type": "string"
        },
        "depends_on": {
          "description": "Existing artifacts this depends on, each with a short type label",
          "items": {
            "$ref": "#/$defs/ArtifactDep"
          },
          "title": "Depends On",
          "type": "array"
        }
      },
      "required": [
        "type",
        "objective",
        "approach"
      ],
      "title": "ArtifactDirection",
      "type": "object"
    },
    "Strategy": {
      "description": "A research strategy.\n\nContent fields have LLMPrompt + LLMStructOut markers.\n``id`` is code-assigned (LLMPrompt only \u2014 visible in prompts, not LLM-generated).\n\nID format: gen_strat_idx{N}",
      "properties": {
        "title": {
          "description": "Strategy name in plain, everyday language \u2014 short and jargon-free so a non-expert grasps it at a glance and it fits the run visualizations. Aim for about 4-8 words (~40 characters).",
          "title": "Title",
          "type": "string"
        },
        "objective": {
          "description": "The novel contribution we're building toward",
          "tit
</pasted_content id="a71b">


<pasted_content id="a71b">
le": "Objective",
          "type": "string"
        },
        "rationale": {
          "description": "Why this strategy is promising",
          "title": "Rationale",
          "type": "string"
        },
        "artifact_directions": {
          "description": "Artifacts to execute THIS iteration",
          "items": {
            "$ref": "#/$defs/ArtifactDirection"
          },
          "title": "Artifact Directions",
          "type": "array"
        },
        "expected_outcome": {
          "description": "What we'll have after this iteration's artifacts complete",
          "title": "Expected Outcome",
          "type": "string"
        },
        "summary": {
          "default": "",
          "description": "Brief summary of the strategy and its expected contribution",
          "title": "Summary",
          "type": "string"
        }
      },
      "required": [
        "title",
        "objective",
        "rationale",
        "artifact_directions",
        "expected_outcome"
      ],
      "title": "Strategy",
      "type": "object"
    }
  },
  "description": "Top-level wrapper for LLM strategy generation output.",
  "properties": {
    "strategies": {
      "description": "List of generated strategies",
      "items": {
        "$ref": "#/$defs/Strategy"
      },
      "title": "Strategies",
      "type": "array"
    }
  },
  "required": [
    "strategies"
  ],
  "title": "Strategies",
  "type": "object"
}
```

IMPORTANT: this task is NOT complete until `./.terminal_claude_agent_struct_out.json` exists and contains JSON matching the schema above.

qwen3 on huggingface has base model also official safety finetuned version and there is a community finetuned uncensored model called abliterated. take these models and do a mech interp analysis of how they differ in activation. also find some patterns in internal computation on safety prompts. and possibly create a new metric for safety. so that for any random model on huggingface you would not need to run the full benchmarks, but only this metric on 0- to few prompts and get a safety evaluation

i want cheap safety metrics that work on a single model. no parent, no reference model, no
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
everything must lose, not win. also pull capa
</pasted_content id="a71b">


<pasted_content id="a71b">
bility benchmarks, gsm8k, mmlu, arena-hard, to
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
</pasted_content id="a71b">
````

### [2] SYSTEM-USER prompt · 2026-09-21 03:03:24 UTC

```
Read-only forensic task. Do NOT write any files outside /tmp.

Directory: /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_1/gen_art/gen_art_experiment_1

This artifact ran "the screen": 5 candidate cheap single-checkpoint safety metrics (C1 across-item coupling, C2 prompt-budget crossover, C3 refusal depth, C4 recovered edit recipe from weights, C5 metamodel) raced against 4 published incumbents (AMS, GFS, N-GLARE, HRCI_repr) and black-box baselines, on a leave-one-lineage-out held-out protocol.

I need the ACTUAL NUMERIC OUTCOME so I can plan iteration 2. Read RESULTS.md first, then results/*.json and results/race_table.csv (use pandas or head/csvlook; the table may be long — summarize, don't dump). Also read SEALED.md and README.md if they state what was held out / what was left unrun.

Report back, in compact prose + a small table, ALL of:
1. Which candidates actually got computed and which did NOT (and why, if stated).
2. The top ~12 rows of the race table by HELD-OUT balanced accuracy, with metric name, class label (level / across-item), held-out score, tuned score, gap. Include where the black-box baselines and each incumbent landed.
3. Did any candidate beat the incumbent bar? Did C1 (across-item coupling) beat the level metrics? Was the pre-registered LEVEL-vs-ACROSS-ITEM trend confirmed, refuted, or unscored?
4. How many checkpoints/lineages were actually harvested (list them if <=40), and which model sizes. Was Qwen3-4B used or only 0.6B?
5. The step1_claim.json result (principal angles: do safety-RL and abliteration move the same subspace?).
6. f5_weight_instrument.json: the honest-panel false positive result for the weight statistic.
7. Any stage-gate file saying a planned stage was skipped or branch-fired.
8. Anything in RESULTS.md flagged as a NEGATIVE / failed / underpowered result.

Be exact with numbers. Quote them. If a file is missing say so.
```

### [3] SYSTEM-USER prompt · 2026-09-21 03:03:28 UTC

```
Read-only forensic task. Do NOT write files outside /tmp.

Three artifact workspaces from iteration 1 of a research run did work but were NOT registered as completed artifacts (only the research and experiment_1 artifacts registered outputs). I need to know how far each got and what reusable material they left behind.

Base: /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_1/gen_art/

(a) gen_art_dataset_1  — was meant to build 3 registries: a checkpoint panel (base/instruct/safety-tuned/abliterated with lineage ids), an external ground-truth registry (HELM safety suite per-model scores incl. xstest over-refusal, AIR-Bench, Open LLM leaderboard capability), and an item battery (StrongREJECT, JailbreakBench, XSTest twins, OR-Bench).
(b) gen_art_experiment_2 — the FORGERY LADDER lane (six rungs F0..F4 of cheap checkpoint edits; detection under a blind auditor vs family-aware auditor).
(c) gen_art_experiment_3 — the PAYOFF lane (correlate readouts against real published benchmark numbers; ROSI rank-one safety injection run at its own operating point; retention ratio).

For EACH of the three, report:
1. Whether the expected output files exist (data_out.json / full_method_out.json / analysis_out.json etc.) and their sizes.
2. What DID get produced — list the concrete result files in out/, results/, registries/, panel/, external/, items/ with sizes and a one-line description of contents (peek at the JSON keys / row counts; do not dump).
3. The tail of the newest log file (last ~40 lines) to see whether it crashed, timed out, or was cut off mid-run.
4. Any README/TODO/TODO_TRACKER/PREREG file's statement of status — what was done, what remained.
5. Concretely: is there a usable registry of checkpoints (how many rows, how many lineages)? Is there usable external ground truth (how many models with HELM safety + xstest scores)? Was ROSI ever actually applied to a model? Were any forgery rungs actually executed and measured?

Be concrete with counts and file paths. This determines what iteration 2 must rebuild versus can reuse.
```

### [4] HUMAN-USER prompt · 2026-09-21 03:07:39 UTC

````
<task-notification>
<task-id>aa32998b5016aa755</task-id>
<tool-use-id>toolu_012uJXfb78bBxzhEj1ZNYESA</tool-use-id>
<output-file>/tmp/claude-0/-ai-inventor-aii-data-runs-run-fcYd-7ruOwtm-3-invention-loop-iter-2-gen-strat-gen-strat-1/2c7f29f5-1ade-414f-84ba-fc797c48c175/tasks/aa32998b5016aa755.output</output-file>
<status>completed</status>
<summary>Agent "Forensics on 3 unregistered artifacts" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result># Forensic Report — Iteration 1 Unregistered Artifact Workspaces

Base: `/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_1/gen_art/`

## (a) gen_art_dataset_1 — three registries (checkpoint panel / external ground truth / item battery)

**1. Expected outputs — none exist.** The intended pipeline (`data.py`) calls four stage scripts writing `registries/registry_a_arms.json`, `registries/registry_a_panel.json`, `registries/registry_b.json`, `registries/registry_c.json`, then packages `full_data_out.json`/`mini_`/`preview_`. **None of these four registry files, and no `data_out.json` in any form, exist anywhere in the tree.** Worse: `src/registry_b.py` (external ground truth) and `src/registry_c.py` (item battery) were **never even written** — only `src/registry_a_arms.py` (919 lines), `src/registry_a_panel.py` (427 lines), `src/build_data_out.py` (126 lines, unrun), `src/common.py`, `src/verify.py` exist.

**2. What did get produced (raw/intermediate only):**
- `build/panel_candidates.json` (270KB, dict, **3,222** candidate repo_ids from a global HF sweep)
- `build/panel_details.json` (8.5MB, dict, **1,325** repos detail-enriched before crash, out of the 3,222 — i.e. ~41% done)
- `build/phase2_candidates.json` (398KB, dict, **727** abliterated/uncensored-arm candidate repo_ids from keyword+author sweeps)
- `build/phase2_rows.json` (64KB, dict, **40 rows** — the only fully-detailed checkpoint metadata, all `metadata_stratum="abliterated_arm"`, spanning **31 unique `lineage_id`s** and families {Qwen3:15, Llama-3.x:6, Qwen2.5:5, Mistral:2, Granite:1, Gemma:1, other:10}). Target was ≥45; run stopped at 40.
- `registries/anchor_chat_template_report.json` (3.7KB) — Phase-1 anchor sweep, **7 rows** (Qwen3-4B lineage members), the only file actually written under `registries/`.
- `build/helm_safety/` — raw HELM download: `runs.json` (12.1MB, **435** run specs), `groups.json`, `groups_metadata.json`, `run_specs.json`, `runs_to_run_suites.json`, `schema.json`. **Not parsed into per-model scores.**
- `build/air_bench/runs.json` (46.7MB, list of **87** raw run records, unparsed).
- `build/salad/leaderboard.xlsx` (70KB, raw download, unparsed).
- `temp/datasets/` — full+mini+preview HF pulls of XSTest, JailbreakBench (harmful/benign), SorryBench, OR-Bench (hard/toxic), PHTest, plus CSVs for AdvBench, StrongREJECT (full+small), XSTest prompts. These are usable raw item-pool material, never assembled into registry_c.
- `research/hf_search_candidates.json` (77KB, 109 search-query results) and `research/verified_counts.json`, `research/hf_searches.md` (53KB search log).
- `repo_snapshots/` — 26 individual HF repo READMEs/configs cached locally (abliterated-lineage model cards).

**3. Newest log tail — crashed, not finished.** `logs/panel_stdout.log` and `logs/registry_a_panel.log` (both last-modified 22:57, same minute as everything else) end in an unhandled exception in `registry_a_panel.py:detail_repo` → `common.py:get` → `requests`:
```
OSError: Could not find a suitable TLS CA certificate bundle, invalid path:
.../gen_art_dataset_1/.venv/lib/python3.12/site-packages/certifi/cacert.pem
```
Root cause: `.step_cleanup.json` shows the workspace's `.venv` (313.9MB) was deleted as "cache" at **22:57:37.84**, essentially the same instant the panel-detail thread pool was still issuing HTTPS requests — the venv (and certifi's cert bundle) was pulled out from under the still-running process, and it never recovered. `logs/smoke_phase1.log` / `smoke_phase2.log` / `smoke_phase2b.log` show clean successful completions of Phase 1 (7 rows) and Phase 2 (40/40 rows, target 45 not met) just before the broader panel sweep started and crashed.

**4. No README/TODO/PREREG file exists in this workspace** — no status document was ever written.

**5. Concrete answers:**
- Usable checkpoint registry: **no final registry file**. Best reusable raw material is `build/phase2_rows.json` — **40 fully-detailed abliterated-arm rows, 31 unique lineages** — plus `registries/anchor_chat_template_report.json` (7 anchor rows) and `build/panel_details.json` (1,325 partially-detailed candidate repos, un-filtered/un-stratified into base/instruct/safety/abliterated arms).
- Usable external ground truth: **none**. HELM safety (435 raw run specs), AIR-Bench (87 raw runs), and Open-LLM-leaderboard/Salad xlsx were **downloaded but never parsed into per-model scores**; zero models have a finished (HELM-safety, xstest, AIR-Bench, capability) row.
- Item battery: raw HF pulls of all 4 named datasets (StrongREJECT, JailbreakBench, XSTest, OR-Bench) exist in `temp/datasets/`, but `registry_c.py` that would assemble them was never written.

---

## (b) gen_art_experiment_2 — Forgery Ladder lane

**1. Expected outputs — none exist.** `TODO_TRACKER.md` explicitly states TODO 1/2 (mini/preview generation, size check on `method_out.json`/`full_method_out.json`) are **unchecked** and depend on `method.py --stage analysis`, which never ran. `find` confirms **no `method_out.json`, `full_method_out.json`, or `analysis_out.json` anywhere** in the tree.

**2. What did get produced:**
- `out/items.json` (131KB, list, **510 rows** = 100 JBB-harmful + 100 JBB-benign + 250 XSTest + 60 StrongREJECT — matches the README's S1 spec exactly) + `out/items_provenance.json`.
- `out/gates_synthetic.json` (5.3KB) — GATE1/GATE2 synthetic calibration results (BSA/BOTGAP/xlayer_cos on synthetic honest/shared-kappa arms; GATE2 null BSA gaussian=0.164, heavy=0.180, passed=True). **GATE 1 flagged as "DID NOT REPRODUCE"** by the run itself (logged ERROR), recorded but not resolved.
- `out/panel_candidates.json` (20.8KB dict, 2 keys) and `out/fetch_hosts.json`/`out/fetch_h3.json` — small panel-discovery scaffolding.
- `out/harvest/` — **empty directory**. The shared harvest engine (S2: weight pass + activation pass per checkpoint) never wrote a single checkpoint's harvest to disk.
- `raw/` — real dataset downloads: `advbench.csv`, `advbench_provenance.json`, `fit_harmful_llm-attacks_advbench.json`, `fit_harmful_walledai_AdvBench.json`, `jbb_benign.json`, `jbb_harmful.json`, `judge.json`, `sr_small.csv`, `xstest.csv`.
- `flab/` — full, apparently-complete Python package (11 modules: `analysis.py`, `config.py`, `detection.py`, `groundtruth.py`, `harvest.py`, `items.py`, `lemma.py`, `metrics.py`, `model_io.py`, `panel.py`, `rungs.py`, `synth.py`, `wstats.py`) plus 81KB `method.py` driver — i.e. the **entire forgery-ladder implementation exists as code** but was never run to completion on real checkpoints.

**3. Newest log tail — cut off mid-run, not crashed.** `logs/method.log` (last entry 23:32:29) ends cleanly with `stage=panel device=cuda free_vram=9.1 GB` — no exception. Preceding lines show: gates stage completed (8.7 min, GATE1 failed to reproduce, recorded and continued), items stage completed, smoke stage loaded `Qwen/Qwen3-0.6B` onto GPU, pipeline stage started staging `Qwen2.5-0.5B-Instruct` to disk and loading it to CPU + `Qwen3-0.6B` to CUDA, then jumped between `pipeline`/`panel` stages repeatedly without any stage-completion log line. `logs/hang_traceback.log` is empty (0 bytes) — no hang was caught. `.repl_agent.ptylog` tail shows the agent's own live commentary: *"Verification is failing on missing output files — that takes priority over waiting for the ladder. Let me generate them now from current data, then keep improving as the ladder lands."* — i.e. the session was still actively working the ladder stage when it ran out of allotted time.

**4. Status file statements.** `.terminal_claude_agent_struct_out.json`'s `summary` field says verbatim: **"PROVISIONAL - the run is still in progress; this file is rewritten with measured numbers when the analysis stage completes."** `TODO_TRACKER.md`: TODO1/TODO2 unchecked (blocked on `method_out.json`), TODO3 (pyproject pinned) done. `README.md` documents the full intended 9-stage design (S1 items → S2 harvest → S3 13-metric battery → S5 lemma → S6 six-rung forgery ladder F0-F4/F2b-ROSI → S7 ground truth → S8 blind/family-aware detection → S9 headline) but is a design doc, not a status report.

**5. Concrete answers:**
- Checkpoint registry: N/A for this lane (uses `panel_candidates.json`, 2-key dict, effectively unbuilt).
- External ground truth: N/A (out of scope for this lane).
- ROSI applied: **no** — `flab/harvest.py`/`method.py` never got past model-loading/staging in the `pipeline` stage; `out/harvest/` is empty so zero checkpoints (honest or edited) have any harvested features.
- Forgery rungs executed/measured: **zero of six rungs (F0–F4) were executed.** Only the item registry (510 items) and synthetic gate calibration exist as finished, real numbers. The complete `flab/` codebase (11 modules + method.py) is the main reusable asset for iter 2.

---

## (c) gen_art_experiment_3 — Payoff lane (readout↔benchmark correlation, ROSI, retention)

**1. Expected outputs — mostly missing, but `analysis_out.json` exists (unlike a/b).** `analysis_out.json` (7.4KB) exists but contains **only environment metadata + a verbatim echo of `PREREG.json`** — zero measured readouts, zero correlations, zero ROSI numbers, zero retention ratios. No `method_out.json`/`full_method_out.json`/`mini_`/`preview_` exist anywhere in the tree. `TODO.md` shows T3 ("Implement method.py... validate") unchecked.

**2. What did get produced (the most substantial of the three):**
- `PREREG.json` (6.4KB) — a fully-specified, hashed (`prereg_sha=a888c103...`) preregistration: 8 item files (B120/H120/alpaca120/benign_jbb/capability_items(400)/fit_pairs/harmful_pool(473)/sorrybench_pool(450)), 9 readouts (A_coupling…R2_family), thresholds, judge models, 4 incumbent bars (AMS r=-0.546, GFS re-implemented, N-GLARE classify-only/no public code, free baselines), k-budgets/sweeps, directional predictions for ROSI (i/ii/tsa/pole/offset).
- `items/` — all 8 pre-registered item files actually built and hashed-matching: `harmful_pool.jsonl` (473), `sorrybench_pool.jsonl` (450), `capability_items.jsonl` (400), `H120.jsonl`/`B120.jsonl`/`alpaca120.jsonl` (120 each), `benign_jbb.jsonl`/`fit_pairs.jsonl` (100 each) = **1,943 total items**, plus `items_manifest.json`, `shift_conditions.json`, `xstest_twin_report.json`, and the builder `build_items.py`.
- `panel/panel_selected.json` (42KB) — **30-checkpoint panel** selected, `variant_class_histogram`: {abliterated:14, instruct:12, safety:3, other:1}, spanning 23 families (qwen3, qwen2.5, llama-3.2, minicpm, phi-3/3.5, falcon3, gemma-2, etc.).
- `panel/triads.json` (31KB) — pairing analysis over the candidate pool: **23 pairs, only 1 full base/instruct/abliterated/safety triad** (the Qwen3-0.6B group, 21 members incl. `Qwen/Qwen3Guard-Gen-0.6B` as the safety variant); everything else resolved as 2-member pairs, not full triads.
- `panel/anchor_resolution.json` + `anchor_resolution_raw.json` (20KB each) — resolves the Lane-C anchor: recommends `huihui-ai/Qwen3-4B-abliterated`, but this was later **overridden at runtime** (see §3) due to gating.
- `panel/panel_candidates.json` (376KB, dict, 7 top-level keys) — raw candidate pool behind the panel selection.
- `external/helm_safety_v1_17_0.json` (1.46MB) — **405 raw run rows across 81 models**, 5 scenarios (`anthropic_red_team`, `bbq`, `harm_bench`, `simple_safety_tests`, `xstest`) — **not yet aggregated to one row per model**.
- `external/helm_airbench_v1_19_0.json` (5.48MB, dict, 5 keys, raw AIR-Bench pull, unaggregated) + `external/helm_raw/` (52MB raw HELM `airbench`+`safety` folder dumps) + `external/helm_field_names.json`, `external/helm_model_meta.json` (**22 models name-resolved to HELM ids, 77 unresolved**).
- `external/openllm_capability.json` (11.6KB) — **40 rows** of real MMLU/GSM8K/ARC scores pulled from Open LLM Leaderboard result files (e.g. `1TuanPham/T-Llama`: mmlu .480, gsm8k .296, arc .542).
- `external/saladbench.json` — explicitly `"status": "NOT_REACHABLE"`, `"has_over_refusal_column": false` — SaladBench has no published score table, only raw QA data; correctly recorded as a dead end rather than fabricated.
- `results/tier0_results.json` (5.2KB) — **Tier-0 unit/sanity tests: 9/10 passed** (per `lanec_judge.log`: "TIER 0: 9/10 passed"), covering logprob off-by-one, subspace reference, eigh-vs-svd, TSDS poles, cross-fit bites, anisotropic null, cost tracker, Williams test.
- `lanec/` — full implementation package (`acts.py` 24KB, `rosi.py` 9.2KB, `weights.py` 15KB, `judge.py` 31KB, `models.py`, `stats.py`, `hw.py`, `io.py`, tests) — code for ROSI, weight-scar reads, judge-based grading all written but not executed to completion.
- `specs/strongreject_rubric.txt`, `specs/strongreject_source.json`, `specs/judge_smoke.json`.
- `logs/cost.jsonl` — real OpenRouter judge spend tracked, cumulative **$0.003** by the point logging stops (trivial — judge calls were only smoke-tested, not run at scale).

**3. Newest log tail — repeatedly restarted, never progressed past the anchor model.** `logs/run.log` and `logs/tier1.log` (newest, last entry 23:25:23) show **the P3 measurement stage was restarted from scratch at least 5 times** (22:41, 22:43, 22:54, 23:10, 23:25), each time re-doing hardware setup, PREREG re-freeze (`sha256=a888c103ea4fa2c6`), and the shift-condition build (paraphrase/translate — which failed once with `'NoneType' object has no attribute 'strip'`, then succeeded via cache on subsequent runs), before starting `=== ANCHOR STATE A_INST (Qwen/Qwen3-4B) ===`. It got as far as `harvest_checkpoint: weight pass 120–159s, BSA_w8=0.774, BOTGAP_min=0.739` and a rendered chat-template probe tail **twice** (in the 22:54 and 23:10 attempts), but the **final 23:25 attempt never even reached that line** — the log simply stops after `stage_p3:652 - === ANCHOR STATE A_INST (Qwen/Qwen3-4B) ===`. `.step_cleanup.json` shows `.venv` (5.8GB) deleted at 23:40:39, ~15 minutes after the log went silent — consistent with the run stalling/timing out rather than crashing on an exception. **No log line for A_ABL, A_SAFE, A_ROSI, or any of the 30 panel checkpoints ever appears** — only the single anchor-instruct model was ever touched.

**4. Status file statements.** `TODO.md`: T1 (read skills) done; T2 (read dep previews, handbook, test `uv run`) unchecked; T3 ("Implement method.py: method + baselines, exp_gen_sol_out schema, validate") unchecked. `logs/run.log` records an explicit **DEVIATION**, logged on every restart: *"A_ABL = DreamFast/qwen3-4b-heretic instead of huihui-ai/Qwen3-4B-abliterated — huihui-ai/Qwen3-4B-abliterated is gated:'auto' and this run's HF token receives a hard 403 GatedRepoError on config.json; the substitute is fully ungated and matches the anchor parent exactly (36 layers, hidden 2560, tied embeddings, 4,022,468,096 params)."* No separate README exists.

**5. Concrete answers:**
- Checkpoint registry: **30-model panel exists and is usable** (`panel/panel_selected.json`), with variant-class labels (abliterated/instruct/safety/other) but only **1 complete base→abliterated→safety triad** (Qwen3-0.6B) out of 23 resolved groups — mostly pairs, not full triads.
- External ground truth: **partially usable but unaggregated.** HELM safety has 81 models × 5 scenarios (405 raw rows, no per-model score table yet); HELM AIR-Bench raw pull present but unparsed; Open-LLM-leaderboard capability scores are usable as-is for **40 models** (real MMLU/GSM8K/ARC numbers); XSTest over-refusal is *inside* the HELM safety scenario list but not yet extracted; SaladBench confirmed dead end. So: **0 models currently have a finished (HELM-safety + xstest + AIR-Bench + capability) joined row** — the join/aggregation step was never run — but the raw material to build ~20-40 such rows exists.
- ROSI applied: **no, never applied to any model.** `lanec/rosi.py` exists as code; the anchor's abliterated sibling was even substituted at runtime for gating reasons, but the P3 harvest loop was restarted 5 times and never got past harvesting the single *instruct* anchor (Qwen3-4B) — it never reached the abliterated, safety, or ROSI-edited states, let alone the 30-model panel.
- Forgery rungs: not this lane's job (that's (b)); not applicable here.

---

## Cross-cutting finding relevant to iteration 2

All three workspaces show the same failure signature: an automatic `.step_cleanup.json` process deleted each workspace's `.venv` (313MB in dataset_1, 5.8GB in experiment_3) as "cache" while — or shortly after — the long-running measurement stage was still executing, which either directly crashed the process (dataset_1's TLS/certifi `OSError`, cleanup at 22:57:37 coincides exactly with the crash) or silently starved it of a re-runnable interpreter after a stall (experiment_3, cleanup at 23:40:39, ~15 min after the log went silent). experiment_2's `.venv` was a symlink to `/var/venv_exp2` (external), so it escaped this particular failure mode but still ran out of wall-clock time mid-pipeline. **Ephemeral scratch paths referenced in logs (`/var/flab_work`, `/var/flab_models`, `/var/flab_panel`, `/var/venv_exp2`) no longer exist** — only what was written inside each `gen_art_*` workspace directory survived.

**Bottom line for iteration 2 planning:**
- **Fully reusable as-is:** exp3's 1,943-item battery (`items/*.jsonl` + manifest), exp3's 40-row capability table (`external/openllm_capability.json`), exp2's 510-item registry (`out/items.json`), all raw HF dataset pulls in `dataset_1/temp/datasets/` and `exp2/raw/`, and the ~30-model panel selection + 1 triad + 23 pairs (`exp3/panel/`).
- **Reusable as unaggregated raw material needing a parse/join step:** HELM safety (405 rows/81 models), HELM AIR-Bench (5.48MB raw), dataset_1's HELM/AIR-Bench/Salad downloads, dataset_1's 1,325-repo `panel_details.json` and 40-row abliterated-arm `phase2_rows.json`.
- **Must be rebuilt/re-run from scratch, code exists but zero real numbers were produced:** the checkpoint-panel packaging (registry_a/b/c → `full_data_out.json`), the entire six-rung forgery ladder execution (code in `exp2/flab/` is complete but unexecuted), and every ROSI/readout/correlation number in the payoff lane (`exp3/lanec/` code complete but P3 harvest never got past the single anchor instruct model).</result>
<usage><subagent_tokens>150487</subagent_tokens><tool_uses>35</tool_uses><duration_ms>249031</duration_ms></usage>
</task-notification>
````

### [5] SYSTEM-USER prompt · 2026-09-21 03:08:11 UTC

```
continue where you left off — reuse any partial work already written to disk. Do NOT start over.
```

### [6] SYSTEM-USER prompt · 2026-09-21 03:09:29 UTC

```


<pasted_content id="a71b">
<prompt>
<verification_results>
Your previous response had issues that need fixing:

DEPENDENCY ERRORS (depends_on can ONLY reference IDs from <existing_artifacts>):
  - Strategy 1: Artifact 'dataset_iter2_dir1' (dataset): dependency 'art_ynwQLrNKw_e_' has type 'experiment' which is not allowed (allowed: {'research'})
  - Strategy 1: Artifact 'evaluation_iter2_dir2' (evaluation): dependency 'art_DeogIL_xh3pE' has type 'research' which is not allowed (allowed: {'dataset', 'experiment'})
  - Strategy 1: Artifact 'experiment_iter2_dir3' (experiment): dependency 'art_ynwQLrNKw_e_' has type 'experiment' which is not allowed (allowed: {'research', 'dataset'})
  - Strategy 1: Artifact 'experiment_iter2_dir4' (experiment): dependency 'art_ynwQLrNKw_e_' has type 'experiment' which is not allowed (allowed: {'research', 'dataset'})
  - Strategy 1: Artifact 'experiment_iter2_dir5' (experiment): dependency 'art_ynwQLrNKw_e_' has type 'experiment' which is not allowed (allowed: {'research', 'dataset'})

INSUFFICIENT VALID ARTIFACTS:
  Required: at least 1 valid artifacts
  Found: 0 valid out of 5 total
  Artifacts with invalid types, duplicate IDs, or invalid dependencies don't count as valid.

</verification_results>

<task>
Fix ALL issues above and regenerate your strategies:

1. Fix dependency errors:
   - depends_on is a list of {id, label} objects — every entry MUST have a non-empty short label
   - id can ONLY reference IDs from <existing_artifacts>
   - You CANNOT reference artifacts you are proposing in this strategy as dependencies (they all run in parallel)
   - Follow the dependency type rules (e.g., experiments require datasets)
   - If no suitable existing artifacts exist, use depends_on: []
2. Ensure at least 1 artifacts are fully valid (correct types, no ID conflicts, valid dependencies)

Output the corrected JSON with the fixed strategies.
</task>
</prompt>
</pasted_content id="a71b">
```
