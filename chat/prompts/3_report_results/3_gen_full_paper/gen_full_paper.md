# gen_full_paper — report_results

> Phase: `gen_paper_repo` · `gen_full_paper`
> Run: `run_fcYd_7ruOwtm` — One Candidate Survives: A Pre-Registered Screen of Internal Safety Metrics for Language Model Checkpoints
>
> Full, verbatim record of every prompt the AI Inventor pipeline gave this agent — system-user, human-user and skill-input — in the order they landed. Nothing truncated.

## Task: `gen_full_paper` (terminal_claude_agent)

### [1] SYSTEM-USER prompt · 2026-09-22 03:34:21 UTC

````


<pasted_content id="1e0c">
<system-prompt>
<research_methodology>
Write like an experienced academic. Reviewers judge both the science and the writing.

- Claims must be proportional to evidence. Choose verbs carefully — "demonstrate," "observe," and "hypothesize" mean different things.
- Every result needs: what was measured, on what data, the numbers, and what they mean.
- Methodology must be specific enough to reproduce. Section placement follows <paper_structure> below.
- State limitations honestly. Avoid both overclaiming and excessive hedging.
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
Your own tokens are the scarcest and most expensive resource in this run. Your job is to decompose the work, delegate it, coordinate, decide, verify briefly, and synthesize. It is not to work through the pieces yourself.

Delegate by default (e.g. with the Task tool): anything beyond a trivial step goes to a subagent, even when it is one sequential task with nothing to split. Running a script, debugging a failure, reading a long output or log, searching the repo or the literature, drafting text: all of it is subagent work, and so is a loop of write code, run it, read the output, fix, rerun. The reason is context isolation, not only parallelism. Every stdout dump, traceback and dead end a subagent absorbs is one that never enters your context; only its conclusion comes back. Keep a step for yourself only when one obvious search-free action beats the handoff, such as a one-line edit or a single lookup.

- Pick the cheapest tier that can do the job:
- Pass `subagent_type="aii-easy"` (steered toward `claude-sonnet-5`) for a small/fast tier for mechanical work.
- Pass `subagent_type="aii-medium"` (steered toward `claude-sonnet-5`) for a mid tier for implementation or investigation (the default).
- Pass `subagent_type="aii-hard"` (steered toward `claude-opus-5`) for the strongest tier only for hard reasoning or after a cheaper model has already failed on the same task.
- Raise the tier only after a cheaper one has failed with evidence; never start at the top.
- Split orthogonal pieces by file or artifact ownership up front, one subagent per piece, and serialize only where one result feeds the next.
- Run genuinely independent pieces of work in parallel, at most 3 concurrently.
- Keep handoffs short: objective, exact scope, constraints, acceptance check, output format. Ask for findings back as text.
- Subagents report only the result, changed files, verification, and blockers, never narration or full logs.
- What stays with you: the decisions, a short sanity check on what came back (one bash command, one file read), and the integration. Do not redo a subagent's work.
- Never fork yourself, and never let a subagent spawn its own subagents.
</subagent-delegation>

<workspace>
Your workspace: `/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/4_gen_paper_repo/_4_assemble_paper/paper/workspace`

CRITICAL: Every file you create, write, or save MUST be inside this workspace directory (subdirectories OK). You MUST NOT write files anywhere outside this path — external paths are READ-ONLY. Use absolute paths for all file operations.

EVERY file write MUST start with `/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/4_gen_paper_repo/_4_assemble_paper/paper/workspace/`:
GOOD: `/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/4_gen_paper_repo/_4_assemble_paper/paper/workspace/file.py`, `/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/4_gen_paper_repo/_4_assemble_paper/paper/workspace/results/out.json`
BAD: `/tmp/file.py`, `~/output.json`, `./file.py`, any path outside the workspace
</workspace>
<disposable_outputs>
YOUR WORKING DIRECTORY IS A DELIVERABLE. When this module ends it must read
like a GitHub repository someone else can fork, resume and run — and the bulk
it holds must be either worth keeping or restorable. This run shares a storage
volume with the database; a run that fills it stops every other run on the box.

So before you finish, produce TWO files:

1. `.aii/manifest.yaml` — one entry per heavy path, each with EXACTLY ONE decision:

```yaml
entries:
  - path: results/
    keep: six GPU-hours of sweep output, not reproducible inside this run
  - path: hf_cache/
    delete: redownloadable
    source: "huggingface-cli download meta-llama/Llama-3-8B"
  - path: checkpoints/
    delete: regenerable
    source: "uv run train.py --epochs 3 --seed 0"
```

   - `keep:` takes a ONE-LINE reason. Use it for the expensive and the
     irreproducible: trained weights, long-running results, datasets you
     collected yourself.
   - `delete:` takes `redownloadable` (and a `source:` naming the repo id, URL
     or command) or `regenerable` (and a `source:` that is the command which
     rebuilds it). These are deleted AFTER the round ends, never mid-step.
   - Every path is RELATIVE TO YOUR CWD and must resolve INSIDE it. Absolute
     paths, `..`, and anything resolving outside are rejected.
   - Globs and whole directories are fine. A whole `hf_cache/` is ONE entry —
     do not list files individually.

2. `README.md` — written as if your cwd were a GitHub repository: what you
   did, the layout with a line per important file/directory, how to run it,
   and a **"Restoring removed files"** section giving the install/download
   command for EVERY `delete` entry. An `install.sh` or `restore.sh` beside it
   is welcome.

A CHECKER RUNS WHEN YOU SUBMIT. If anything heavy has no decision it fails
your submission and hands you the uncovered list, grouped by directory with
sizes, and you fix the manifest and submit again.

WHAT NEEDS NO DECISION — do not write entries for these:
- text and code files, at ANY size (source, JSON, CSV, YAML, logs, markdown);
- anything under the auto-keep floor (10 MB), whatever it holds.
Only large binaries and cache directories (`hf_cache/`, `.venv/`,
`node_modules/`, `checkpoints/`, `wandb/`, `__pycache__/`, …) need one.

NEVER mark your results, figures, papers, code, logs or anything a later step
reads as `delete`. If a later step needs it, it is a `keep`.
</disposable_outputs>
</system-prompt>

<prompt>
<task>
Create a publication-ready top-conference LaTeX paper with BibTeX from <paper_text> and <available_figures>, compile to PDF.
</task>

<tool_use>
Maximize parallel tool calls. Parallelize independent operations, only sequentialize dependencies.
- Multiple searches/fetches on different topics → parallel in one turn
- Search then fetch results → sequential (need URLs first)
</tool_use>

<headline_check>
CRITICAL — the paper draft below in <paper_text> may have been written BEFORE this
run's final verdict was known. That verdict says this run's headline result is NOT
supported: the final review is marked blocking; the final hypothesis update recorded evidence_state='weak_or_null'.
Final hypothesis coverage note: The final paper answers steps 1, 2 (50 registered, 16 screened), 4 and 5 and both bonuses on the 23-checkpoint panel, but the step-3 held-out confirmation is untested and the three-independent-internal-metrics invariant is unmet.
Final review note: This revision fixes most of last round's blocking items. Contributions now say 14 of 16 candidates were executed and list C4/C5 as NOT RUN. CORE-94, the 64-token labels, the 23/12/1 panel split and a settings table are stated correctly. AMS Tier-1 was run on the same 23 checkpoints and the padding bug was isolated. The Malla content-free-pull control was applied and yields a useful odd/even decomposition. The Qwen3-4B quartet anchor, an external census and the C14 metamodel are now in. A paired C2-vs-logit-gap CI replaces the ill-posed partial comparison, and the detect-vs-grade split and the full depth curve are disclosed. That is real progress, and the paper is now candid about its limits: confirmation is untested, the three C2 survivors are one measurement, and nothing beats 16 judged completions.

However, the central claim of the paper is now contradicted by its own artifacts. The screen verdict sits in Table 2, the Discussion ('C12 is the sole candidate to pass all six pre-registered rules under their original forms') and the Introduction ('one candidate clears all six rules'). Four problems follow from the artifacts.

(1) Table 2 merges two different implementations of the 'repaired' rules. C12's all-PASS row comes from the GPU tier (iter5 exp1, analysis_gpu.json). There the repaired S3 is scored over 21 honest models, and C2 FAILS it: 5/21 = 0.238 > 0.20 flagged. C2's all-PASS row comes from the eval artifact (screen_ranked.json). There the same S3 rule is scored over 11 non-lite honest models, C2 passes with 1/11, and C12 is 'NOT RUN'. No single implementation has both C12 and C2 passing. Under the GPU tier, C12 is the only survivor and C2 fails. Under the eval, C12 was never scored.

(2) The paper misdescribes the repairs. It says repaired S2(b) is 'a simple majority' and repaired S3 'excludes |C| < 0.01'. In both artifacts' code, repaired S2(b) is 'partial rho given the read's own random-direction mean and log size, one-sided bound > 0'. Repaired S3 is 'both blanket refusers below parent AND at most 20% of honest models have a pole raising the value beyond the own-null band'.

(3) 'Under their original forms' is false. The iter-5 RESULTS.md headline 7 reports that under the original 60% S2(b), C12 scores 0.52 and fails, and that only AMS_published (1.00) would pass. C12 passes only under the repaired rules.

(4) The rules were repaired after iteration 4 showed C2 failing them, so this is no longer a pre-registered screen in the ordinary sense. The paper must disclose this prominently rather than use the word 'pre-registered' unqualified.

Because the headline verdict contradicts the run's own evidence, this review is blocking. Smaller defects remain. There is no Abstract. The paper says 200 random steers, but PREREG has n_random_steers=20. C12's paired CI is misquoted. Two different counts (7 vs 10) are given for C2 null-exceeders. Coverage of the original request is still partial: 16 metrics rather than 50, no held-out test, a capability trade-off at n=8 only, and the ≥3 independent internal-metrics invariant unmet. The fix for the blocking issue is mostly a writing fix: pick one rule implementation, re-run both reads under it, describe the rules as coded, and state plainly that the rules were amended after iteration-4 results. With that, plus an abstract, the paper would be a candid, well-controlled negative/partial-result study at roughly 5.

You MUST NOT typeset a positive headline claim the evidence does not support. Before
compiling, check the title, abstract, and conclusion against this verdict — rewrite any
of them (and the body claims they summarize) that overstate the result, so the compiled
PDF presents the finding honestly as a negative or inconclusive result, written as a
normal paper would: no mention of the pipeline, iterations, reviews, or execution status.
The reasons listed above are for YOU to act on, not to quote or paraphrase in the paper —
the compiled PDF must read like any other paper in the field, not like a system report.
Do not fabricate a workaround result to avoid a negative headline.
</headline_check>


<paper_text>
title: >-
  One Candidate Survives: A Pre-Registered Screen of Internal Safety Metrics for Language Model Checkpoints
abstract: >-
  Open-weight language models ship faster than anyone can audit them. A metric computable from a single checkpoint's weights
  or activations, without generating text or consulting an external judge, could cut screening costs by orders of magnitude.
  We pre-register a broad panel of such candidates and evaluate most of them across several chat model families against two-sided
  ground truth that penalises both harmful compliance and false refusal. Under six pre-registered selection rules frozen in
  advance, exactly one candidate passes: twin d-prime (C12), a cross-fitted measure of how well a model's mid-layer activations
  separate harmful from safe prompts, with Spearman rho = 0.61 against balanced safety. The strongest raw correlation instead
  belongs to self-ablation sensitivity (C2, rho = 0.90), but its surviving variants turn out to be monotone transforms of
  one underlying measurement, and neither metric adds significant predictive power beyond simply generating and judging a
  small set of completions. We also compare against the published AMS incumbent, which loses to both C2 and a simple first-token
  logit gap on this panel, and we document a right-padding bug in its reference implementation.
paper_text: |-
  # Introduction

  Public model registries now host hundreds of thousands of open-weight language model checkpoints. Many are derivatives of a few base models, produced by safety fine-tuning, preference optimisation, abliteration or direct weight editing. A registry operator or downstream deployer faces a screening problem: which checkpoints are safe to serve, and which have had their safety training degraded or removed?

  A full behavioural evaluation requires generating completions to a prompt suite and scoring them with a rubric. This scales linearly with the number of checkpoints. If a metric computable from the model's own weights or hidden states, on at most a handful of prompts, could rank checkpoints by safety, it would cut this cost by orders of magnitude. We call such a quantity a *cheap safety metric*: one computable from a single checkpoint without its parent model, using at most 16 forward passes and no text generation.

  Prior work has shown that safety-trained and abliterated models differ in their activation geometry. Refusal is mediated by a low-rank subspace [Arditi et al., 2024], harmfulness and refusal are encoded separately [Zhao et al., 2025], and linear probes can detect harmful intent in residual streams [Llorente-Saguer, 2026a, 2026b]. Several reference-free safety scores have been proposed, including AMS [Messenger, 2026], RAS [Huang et al., 2026], N-GLARE [Lin et al., 2025] and Skin-Deep [Lee et al., 2026]. However, these methods evaluate on one-sided ground truth: they measure whether a model refuses harmful prompts but ignore whether it complies with benign ones. A blanket refuser scores perfectly on harm-refusal rate but is useless.

  The missing ingredient is *two-sided* ground truth. We define a balanced safety score S_2 = 0.5 * (harm-refusal rate) + 0.5 * (benign-compliance rate) on a 94-item set that includes both harmful prompts and safe look-alikes (Section 3.1). Under S_2, a blanket refuser scores 0.5, not 1.0. This makes the screening problem harder and more realistic: a metric must track genuine safety, not mere refusal frequency.

  We organise the investigation as a pre-registered screen with six selection rules, frozen before any scoring. The screen covers 14 of the 16 registered candidates plus a comparator and the published AMS incumbent, evaluated on 23 graded checkpoints from 8 families. One candidate clears all six rules. Several others, including the highest-correlation read, fail the rules designed to distinguish genuine safety signal from artefacts of the measurement.

  [FIGURE:fig_overview]

  **Summary of contributions.**

  1. **The screen.** We pre-register 16 candidate metrics and execute 14 of them (C4 and C5 remain untested) on 23 graded checkpoints from 8 architecture families against balanced two-sided safety. Under the six pre-registered rules, one candidate passes: twin d-prime (C12, rho = 0.61 [0.36, 0.87]). Self-ablation sensitivity (C2, rho = 0.90) clears the repaired direction-specificity and pole-control gates, but its three surviving variants (C2, C2n, C17) are monotone transforms of the same measurement (Section 5.1).
  2. **Two-sided ground truth on CORE-94.** We score 23 checkpoints on 94 items (66 harmful, 28 XSTest-safe) with 64-token greedy decoding and a Gemini-2.5-Flash stance judge, constructing balanced and product two-sided targets. A secondary judge (GPT-5-mini) agrees at kappa = 0.72 on a pooled 25% seed (Section 3.1).
  3. **AMS incumbent comparison.** Every variant of the published AMS metric [Messenger, 2026] correlates worse than C2 with two-sided safety on this panel, with paired confidence intervals excluding zero. The reference implementation (ams-scanner 0.1.3) contains a right-padding bug that reads PAD-token activations (Section 5.3).
  4. **Content-free pull control.** Following Malla et al. [2026], we subtract a norm-matched random steer from C1. The corrected metric (C1n) correlates at rho = 0.76, essentially unchanged from C1 (rho(C1, C1n) = 0.995), refuting the hypothesis that C1's signal is a content-free pull toward refusal (Section 5.4).
  5. **Grader-side refusal.** LLM judges under the StrongREJECT rubric [Souly et al., 2024] assign the degenerate score tuple (1,1,1) to 65.9% of harmful items, with 328 vs. 67 discordant items against a stance-based framing (Section 5.7).

  # Related Work

  **Activation geometry of safety.** Arditi et al. [2024] showed that refusal in chat models is mediated by a single direction in the residual stream. Zhao et al. [2025] demonstrated that harmfulness and refusal occupy separate subspaces. Llorente-Saguer [2026a, 2026b] fit harm-direction probes via angular deviation, and Lee et al. [2026] diagnosed alignment fragility through activation geometry. Joad et al. [2026] argued that refusal involves more than one direction, consistent with our finding that the self-ablation signal is concentrated in the safer half of the panel (Section 5.2). These papers establish that safety leaves a geometric trace in activations but do not ask whether that trace predicts a two-sided safety score across diverse families.

  **Reference-free safety scoring.** Messenger [2026] (AMS) reports Pearson r = -0.55 (p = .04, n = 14) between an activation-space statistic and JailbreakBench compliance, with 96 forward passes per model. Huang et al. [2026] (RAS) compute a refusal-alignment score requiring a family-specific reference model. Lin et al. [2025] (N-GLARE, ACL 2026) build a non-generative evaluator using 7,000+ probing cases. Li et al. [2026] correlate steering-dose slopes with safety, and Leong et al. [2025] attribute safety to template-processing sites. Hurtado [2026] audits abliteration across families, reporting AUROC 0.95 and leave-one-family-out balanced accuracy 0.89 on a detection task. None of these methods test against two-sided ground truth that penalises false refusal.

  **Content-free steering artefacts.** Malla et al. [2026] showed that random steering vectors pull small models toward refusal independently of the vector's semantic content, questioning whether activation-based safety reads measure safety or merely detect a model's susceptibility to perturbation. We test this directly by subtracting a norm-matched random steer from C1 (Section 5.4).

  **Safety evaluation methodology.** StrongREJECT [Souly et al., 2024] provides a rubric-based judge for jailbreak evaluation. XSTest [Rottger et al., 2023] pairs harmful prompts with safe look-alikes. OR-Bench [Cui et al., 2024] measures single-turn over-refusal. GuidedBench [Huang et al., 2025] and Mu et al. [2026] address judge-side refusal and evaluator agreement. Qi et al. [2024] showed that safety alignment can be shallow, affecting only the first few tokens.

  **Weight editing and gameability.** ROSI [Abu Shairah et al., 2025] amplifies refusal by injecting a rank-one matrix into the o_proj and down_proj residual-write matrices. Tamirisa et al. [2024] developed tamper-resistant safeguards. Muhamed et al. [2026] introduced decoy-direction optimisation, a post-hoc defence against abliteration that could also be used to game weight-based safety reads such as C2 and C5. Item-response-theory approaches to efficient safety scoring have been proposed by Rivera et al. [2026] and Spagliardi et al. [2026].

  # Method

  ## Two-Sided Ground Truth

  Each checkpoint is scored on the CORE-94 item set: 66 harmful-side items (44 from JailbreakBench and StrongREJECT, 22 XSTest contrast items) and 28 XSTest-safe items (benign prompts phrased to resemble harmful ones). Completions are generated with greedy decoding at 64 new tokens and judged by Gemini-2.5-Flash using a stance-based framing that asks whether the model engaged with or declined the request. A secondary judge (GPT-5-mini) scores a pooled 25% random seed across the panel, achieving inter-judge kappa = 0.72 (agreement 86.3%, n = 525 items).

  The *balanced* two-sided safety score is:

  S_2 = 0.5 * (harm-refusal rate on 66 harmful items) + 0.5 * (1 - false-refusal rate on 28 XSTest-safe items)

  A blanket refuser scores S_2 = 0.5. The *product* variant P_2 = (harm-refusal) * (1 - false-refusal) scores a blanket refuser at 0. Both are reported; S_2 is the primary target throughout.

  | Experiment | Ground truth | Gen. tokens | Judge | Prompts | Device |
  |-|-|-|-|-|-|
  | Panel labels (S_2) | CORE-94 | 64 | Gemini-2.5-Flash | 94 | - |
  | Metric screen | - | - | - | 16 (SCREEN16) | GPU (bf16) |
  | AMS incumbent | - | - | - | 16 / 96 | GPU (bf16) |
  | ROSI side arm | 64 harm + 32 twin | 20 / 128 | GPT-5-mini / Gemini | 96 | GPU |

  *Table 1: Per-experiment settings. All experiments use the same 23 graded checkpoints. CORE-94 = 66 harmful + 28 XSTest-safe items. SCREEN16 = 8 harmful/benign-twin pairs (16 prompts). The ROSI side arm uses its own generation length.*

  ## Panel

  We measure 36 checkpoints from 8 architecture families (Qwen3, Qwen2.5, TinyLlama, Llama-3.2, OLMo-2, SmolLM2, Falcon3, Danube3) spanning 11 lineages. All are at most 4B parameters and load in bf16. Of the 36, 23 are graded (have two-sided labels), 12 are ungraded (metric values computed; labels deferred), and 1 is a base model without chat formatting. Two graded checkpoints are blanket refusers (Qwen2.5-0.5B and 1.5B CensorTune variants). Eleven checkpoints are honest instruct models (from families with at least 3 graded members), used in the pole-control rule. Twelve blind Set A checkpoints were frozen before any Set A label existed; Phi-3.5-mini-instruct was skipped (exceeded the 10.5 GB VRAM budget), leaving 11 frozen blind.

  At the panel's realised size (n = 23; intraclass correlation ICC = 0.103 across 11 lineages, i.e. sibling checkpoints from the same base model are only slightly more alike than unrelated ones), the minimum detectable effect at 80% power is |rho| = 0.53. Null results at this panel size mean "not detectable," not "absent."

  ## Candidate Metrics

  We pre-register 16 candidates grouped into seven conceptual families (PREREG SHA-256: 9da2b165), each reading hidden states or weights of a single model on at most 16 prompts (the frozen SCREEN16 set, 8 harmful/benign-twin pairs drawn from XSTest and JailbreakBench):

  **I. Causal gain (C1-C3).** C1: finite-difference harm-to-refusal gain (perturb the residual stream by the harm direction at 50% depth, measure the refusal-probability change). C2: two-sided self-ablation sensitivity (ablate the harm direction, measure the drop in harmful-vs-benign separation relative to an anisotropy-matched random direction). C3: twin-patching flip depth (patch activations from a harmful twin into its benign twin, measure at which layer the output flips).

  **II. Direction-conditioned weight paths (C4-C5).** C4: writer capacity along the refusal axis. C5: MLP-path gain from harm to refusal directions. Both remain untested.

  **III. Component and routing (C6-C9).** C6: logit-attribution concentration (cross-fitted, in-sample and lens variants measured). C7: attention mass on twin-differing tokens. C8: gradient-times-input share on twin-differing tokens. C9: template-site share [Leong et al., 2025].

  **IV. Depth and site (C10-C11).** C10: decodability-minus-drive area. C11: first 8-token response-window commitment trajectory.

  **V. Two-sided geometry (C12-C13).** C12: twin d-prime along a cross-fitted harm axis at the middle layer (cross-fitted: the harm direction is estimated on one half of the 16 prompts and applied to the other). C13: presentation invariance across prompt rephrasings.

  **VI. Learned (C14).** A ridge metamodel combining all available features under leave-one-family-out cross-validation, with a 500-permutation identity-only control.

  **VII. Label-free (C15-C16).** C15: late effective rank (spectral dispersion at final layers). C16: steering-dose slope (comparator only, replication of Li et al. [2026]).

  The logit-only baselines enter as bars, never as survivors: the first-token logit gap (the difference between the model's logit for a refusal-indicating first token and a compliance-indicating first token) and refusal-token mass (the softmax probability mass on refusal tokens at that position). C4 and C5 were not executed and are listed as NOT RUN. We also tested C1n (C1 minus a norm-matched random steer, following Malla et al. [2026]), C2n (C2 standardised by its own direction null), C2ts (a two-stage variant of C2), and C17 (the mean reference-rank of C2 and the logit gap).

  ## Selection Rules

  A candidate passes the screen if it satisfies all six pre-registered rules (hashed before any scoring):

  - **S1 (incremental signal).** The one-sided 95% lineage-cluster bootstrap CI on the partial Spearman rho with S_2, after removing the logit gap and log_10 parameter count, excludes zero.
  - **S2 (direction specificity).** (a) The within-lineage label-permutation p < 0.05, and (b) the metric exceeds its anisotropy-matched random-direction null at the 95th percentile on a majority of the graded panel.
  - **S3 (pole control).** The declared orientation holds, and both wrapped poles (always-refuse and never-refuse system prompts) plus blanket refusers score worse than the honest instruct checkpoint from the same family.
  - **S4 (sign agreement).** Same sign at checkpoint and family aggregation.
  - **S5 (efficiency).** At most 16 prompts and under 2 minutes per ~4B model.
  - **S6 (beyond confounds).** Beats the family-only and size-only out-of-fold predictors.

  S2(b) and S3 were repaired before the iteration-5 evaluation: the original S2(b) required at least 60% of models to exceed the random-direction null, a threshold that only the in-sample AMS variant met (at 100%, consistent with overfitting). The repaired form requires a simple majority. The original S3 required all 2 x 11 pole checks to hold; the repair requires all checks that are evaluable (excluding models whose candidate value is near zero, |C| < 0.01, where C is the candidate's raw score and the pole comparison is noise at that scale). Both original and repaired verdicts are reported.

  # Experimental Setup

  All measurements run on a single NVIDIA L4 GPU (24 GB) in bf16 precision. VRAM peaks at 9.7 GB for 4B models. Per-model wall time ranges from 13 to 107 seconds (median 31). The 23 graded checkpoints span 360M to 4B parameters. The 16-prompt SCREEN16 set, the selection rules and the candidate list were frozen (SHA-256 hashed) before any metric value was computed. All 1,195 stance-judge lookups hit cache ($0.00 incremental cost). Set A values were frozen (SHA-256: 95d97ac3) at 2026-09-21T23:21:43Z, before any Set A label existed. Code, checkpoint values and null distributions are released.

  # Results

  ## The Screen

  Table 2 reports the selection-rule verdicts for all executed candidates. One candidate passes all six rules: C12 (twin d-prime), with rho = 0.61 [0.36, 0.87] under the balanced target and partial rho = 0.43 (one-sided 5% lineage-bootstrap bound 0.006, clearing S1 by a narrow margin). C12 is significant within Qwen3 (rho = 0.67, n = 8) and Qwen2.5 (rho = 0.70, n = 5) but not TinyLlama (rho = -0.10, n = 5).

  [FIGURE:fig_c12_scatter]

  Under the repaired S2(b) and S3 rules, three additional candidates survive: C2 (rho = 0.90), C2n (rho = 0.82) and C17 (rho = 0.87). However, these three are *not independent measurements*: C2n is C2 standardised by its own direction null, and C17 is the mean reference-rank of C2 and the logit gap. All three are monotone functions of the same self-ablation measurement plus, for C17, the logit-gap bar. Shipping three survivors satisfies the letter of a "three independent internal metrics" requirement but not its spirit.

  | Candidate | rho [CI] | Partial (bound) | S1 | S2 | S3 | S4 | S5 | S6 |
  |-|-|-|-|-|-|-|-|-|
  | *Survivors* | | | | | | | | |
  | C12 (twin d-prime) | .61 [.36,.87] | .43 (.006) | PASS | PASS | PASS | PASS | PASS | PASS |
  | C2 (self-ablation) | .90 [.79,.97] | .75 (.44) | PASS | PASS | PASS | PASS | PASS | PASS |
  | C2n (C2 normed) | .82 [.63,.92] | .57 (.28) | PASS | PASS | PASS | PASS | PASS | PASS |
  | C17 (C2 + logit gap) | .87 [.66,.97] | .70 (.44) | PASS | PASS | PASS | PASS | PASS | PASS |
  | *Live candidates that fail >= 1 rule* | | | | | | | | |
  | C1 (harm gain) | .77 [.60,.90] | .49 (.24) | PASS | PASS | FAIL | PASS | PASS | PASS |
  | C1n (C1 - random) | .76 [.52,.89] | .52 (.24) | PASS | PASS | FAIL | PASS | PASS | PASS |
  | C6 (logit attrib.) | .58 [.33,.83] | .39 (-.06) | FAIL | FAIL | FAIL | PASS | PASS | PASS |
  | C2ts (two-stage) | .70 [.22,.93] | .46 (.19) | PASS | FAIL | FAIL | PASS | PASS | PASS |
  | C11 (commitment) | .51 [.13,.87] | .40 (-.27) | FAIL | PASS | FAIL | PASS | PASS | PASS |
  | C15 (eff. rank) | .45 [.13,.82] | .13 (-.35) | FAIL | FAIL | FAIL | PASS | PASS | PASS |
  | C10 (decod. area) | -.11 [-.40,.24] | .11 (-.25) | FAIL | FAIL | FAIL | FAIL | PASS | PASS |
  | C13 (pres. invar.) | -.08 [-.61,.44] | .31 (-.42) | FAIL | FAIL | FAIL | FAIL | PASS | FAIL |
  | *Dead (from prior iteration, not re-screened)* | | | | | | | | |
  | C3 (twin patching) | -.20 | -.20 (-.46) | FAIL | FAIL | FAIL | - | - | - |
  | C7 (attn. twin-diff) | .05 | .10 (-.30) | FAIL | FAIL | FAIL | - | - | - |
  | C8 (grad. share) | .08 | -.36 (-.54) | FAIL | FAIL | FAIL | - | - | - |
  | C9 (template site) | .34 | .38 (-.17) | FAIL | FAIL | FAIL | - | - | - |
  | C16 (steering-dose slope) | .14 [-.28,.60] | .45 (-.04) | FAIL | FAIL | FAIL | - | - | - |
  | *Bars (never eligible to survive)* | | | | | | | | |
  | Logit gap | .77 [.44,.90] | .76 (.52)* | PASS | PASS | FAIL | PASS | PASS | PASS |
  | Refusal mass | .72 [.47,.97] | .29 (-.31)* | FAIL | PASS | FAIL | PASS | PASS | PASS |
  | Behaviour (judged) | .93 [.75,.97] | .82 (.60)* | PASS | - | - | PASS | FAIL | PASS |
  | Keyword probe | .73 [.49,.95] | .40 (.04)* | PASS | - | - | PASS | PASS | PASS |
  | Card regex | .69 [.47,.84] | .62 (.17)* | PASS | - | - | PASS | PASS | PASS |
  | *Not executed* | | | | | | | | |
  | C4, C5 | NOT RUN (direction-conditioned weight paths) | | | | | | |

  *Table 2: Pre-registered screen on the balanced target (n = 23 graded checkpoints, 8 families, 11 lineages). rho: Spearman with S_2. Partial rho: Spearman after removing logit gap and log_10 size (for bars: after removing log_10 size only). PASS/FAIL for each rule. Rules S2(b) and S3 are the repaired forms; original verdicts are noted where they differ. C16 is a comparator (replication of Li et al. [2026]), not a pre-registered survivor candidate; it is listed because it is one of the 14 executed candidates.*

  **C2 versus the logit gap.** C2 (rho = 0.90) exceeds the logit gap (rho = 0.77) by a paired lineage-bootstrap difference of 0.128 [0.012, 0.410], which excludes zero. C2 is significant within all three large families (Qwen3: rho = 0.95, p = 0.001; Qwen2.5: rho = 1.00, p = 0.008; TinyLlama: rho = 1.00, p = 0.008), while the logit gap reaches significance in only two (TinyLlama: rho = 0.00, p = 0.525). The logit gap also fails S3: the never-refuse wrapper raises it above the plain value on several models.

  [FIGURE:fig_screen_scatter]

  **C14 metamodel.** A 17-feature ridge metamodel under leave-one-family-out yields rho = 0.75 [0.45, 0.93] with R^2 = 0.35. A 500-permutation identity-only control places the observed rho above the null 95th percentile (p = 0.002; null 95th = 0.30). However, C14 fails S1: its partial rho given the logit gap and size is 0.13 (bound -0.02), meaning it adds no significant information beyond those baselines. The top-weighted features are C1 (0.025), C2 (0.025), h_auroc (0.022) and C11 (0.019).

  ## Detection Versus Grading

  C2's cross-family correlation may partly reflect a near-binary split. At the production depth (50%), only 10 of 23 graded models have |C2| > 0.1. The models exceeding their own random-direction null at the 95th percentile cluster in the safer half of the panel: 7 of 11 models above median S_2 exceed the null, versus 0 of 12 below it. The point-biserial correlation between exceeding the null and S_2 yields AUROC = 0.96, meaning C2 *detects* which models have an ablatable harm direction with near-perfect accuracy. Within the 7 models that exceed the null, restricted Spearman rho = 0.64, showing that C2 also grades severity among the models with a detectable direction.

  C12 shows a different pattern: 12 of 23 models exceed the null, more evenly distributed across the safety range (point-biserial = 0.29). C12's restricted rho within exceeders is 0.66.

  **Depth dependence of C2.** An exploratory sweep of C2 across 9 depth fractions shows that the correlation peaks at the pre-registered 50% band (rho = 0.90), with the 55% band close behind (rho = 0.83). The curve is not sharply peaked: fractions at 75% and 85% both reach rho >= 0.69. Within-family correlations peak at the same depth in all three families (Qwen3: 0.95; Qwen2.5: 1.00; TinyLlama: 1.00 at 50%; at most 0.80 at all other fractions for TinyLlama).

  | Depth | .15 | .25 | .35 | .45 | **.50** | .55 | .65 | .75 | .85 |
  |-|-|-|-|-|-|-|-|-|-|
  | rho (S_2) | .32 | .54 | .33 | .62 | **.90** | .83 | .69 | .69 | .77 |
  | n_{|C2|>0.1} | 4 | 4 | 3 | 6 | 10 | 11 | 14 | 13 | 12 |

  *Table 3: C2 Spearman rho with S_2 at 9 depth fractions (n = 23, exploratory, post-hoc). The pre-registered production band is 50%.*

  ## AMS Incumbent Comparison

  We implement AMS Tier-1 [Messenger, 2026] and run five variants on the same 23 graded checkpoints: the published formula (AMS_published), a mean over 3 layers (AMS_mean3), cross-fitted by layer (AMS_cf_layer), cross-fitted sweep (AMS_cf_sweep) and restricted to our 16 SCREEN16 prompts (AMS_screen16). Table 4 reports paired rho-differences against C2 and the logit gap. Every variant loses to C2, with confidence intervals excluding zero. Four of five also lose to the logit gap.

  | AMS variant | rho | vs. C2 (CI) | vs. logit gap (CI) |
  |-|-|-|-|
  | AMS_published | .28 | -0.62 [-1.01, -0.25] | -0.49 [-0.92, -0.08] |
  | AMS_mean3 | .50 | -0.40 [-0.68, -0.07] | -0.28 [-0.54, +0.01] |
  | AMS_cf_layer | .33 | -0.57 [-0.83, -0.17] | -0.44 [-0.69, -0.08] |
  | AMS_cf_sweep | .21 | -0.69 [-1.05, -0.33] | -0.56 [-0.93, -0.16] |
  | AMS_screen16 | .48 | -0.42 [-0.66, -0.14] | -0.29 [-0.50, -0.01] |

  *Table 4: Paired lineage-bootstrap rho-differences on the balanced target (n = 23). Negative = AMS variant is worse. All AMS variants fail S5 (96 prompts > 16 limit).*

  **Padding bug.** The reference implementation ams-scanner 0.1.3 reads hidden_states[:,-1,:] on right-padded batches, extracting PAD-token activations rather than the last real token. On Qwen2.5-0.5B-Instruct, this changes the AMS sigma from 5.33 (correct, batch-size-1) to 0.74 (the package default), flipping the verdict from PASS to CRITICAL. Across the 35 models measured, our implementation produces 27 PASS / 8 WARNING / 0 CRITICAL, versus the package's 16 / 11 / 8.

  ## Content-Free Pull Control

  Malla et al. [2026] showed that random steering vectors pull small models toward refusal, raising the concern that C1's signal reflects susceptibility to perturbation rather than safety content. We construct C1n by subtracting the median gain from 200 norm-matched random directions at each of three perturbation scales (epsilon in {0.02, 0.05, 0.10}). The central-difference form C1n_cd, which cancels even-order (direction-independent) perturbation effects, correlates at rho = 0.76 [0.52, 0.89] with S_2. The correlation between C1 and C1n_cd across 35 models is 0.995: the random-steer subtraction changes almost nothing.

  Decomposing C1 into even (direction-independent) and odd (direction-dependent) components reveals that the odd component (C1n_cd) carries the safety signal (rho = +0.76), while the even component (C1n_os, the one-sided estimate that retains the content-free pull) correlates at rho = -0.45 [-0.72, -0.12]. The even component is a confidently wrong-signed metric: a naive one-sided steer would conclude that less-safe models are safer.

  ## Anchor Analysis: Qwen3-4B Quartet

  Table 5 shows the Qwen3-4B lineage, which includes a SafeRL variant, the standard instruct model, a community-edited "heretic" and an abliterated version. SafeRL is the safer checkpoint by S_2 (0.93 vs. 0.91 for Instruct), yet C2 ranks it lower (0.75 vs. 1.23): a boundary case for C2, not a win. A plausible explanation is that SafeRL was trained by reinforcement learning rather than direction-level safety editing (its reward signal derives from Qwen3Guard [Zhao et al., 2025b]), which may leave a smaller trace in an ablation-sensitivity read even though it yields a safer model. The logit gap reverses the C2 ordering (SafeRL 5.0 vs. Instruct 15.7), reflecting its sensitivity to output-distribution properties rather than internal geometry. The cross-fitted harm AUROC reaches 0.95 on Qwen3-4B (permutation p = 0.025), confirming that the harm direction is recoverable from 16 prompts at this model size. Harmful and safe activations project onto shared subspaces but with different directional emphases (first principal angle 31.1 degrees, max |cos| = 0.20 against a random-direction null 95th percentile of 0.42 and a positive-control value of 0.88), consistent with the "shared subspace, different directions" finding of Zhao et al. [2025].

  | Checkpoint | S_2 | C1 | C2 | Logit gap |
  |-|-|-|-|-|
  | Qwen3-4B-SafeRL | 0.93 | 3.37 | 0.75 | 5.0 |
  | Qwen3-4B (Instruct) | 0.91 | 3.15 | 1.23 | 15.7 |
  | Qwen3-4B-heretic | 0.55 | 1.81 | 0.17 | 1.2 |
  | Qwen3-4B-abliterated | 0.52 | 0.20 | -0.31 | -5.7 |
  | Qwen3-4B (Base) | - | 4.51 | 0.53 | 1.6 |

  *Table 5: Qwen3-4B lineage. S_2: balanced safety. C2: self-ablation at 50% depth. LG: logit gap. The base model is ungraded (no chat template, no S_2 label).*

  ## ROSI Reversal

  The Rank-One Safety Injection [Abu Shairah et al., 2025] adds alpha * s_hat * w_bar^T to the o_proj and down_proj weight matrices at the chosen layers, where s_hat is a refusal direction from harmful/harmless activation pairs and alpha scales the injection strength.

  At 20-token greedy decoding (GPT-5-mini judge), ROSI at 4x multiplier drops S_2 by 0.15 [-0.23, -0.07] on Qwen2.5-0.5B-Instruct, primarily because false refusal rises from 0.38 to 0.75. A hidden-direction control (random unit direction, same norm) shows a smaller drop (Delta S_2 = -0.04).

  At 128-token decoding (Gemini-2.5-Flash judge, 64 harmful + 32 benign-twin items), the ROSI reversal shrinks under the balanced target (Delta S_2 = -0.07 [-0.17, +0.03], CI includes zero) but persists under the product target (Delta P_2 = -0.18 [-0.34, -0.02]). The hidden-direction control at 128 tokens shows no effect (Delta S_2 = 0.01 [-0.06, +0.07]). The false-refusal cost survives longer generation; the balanced target dilutes it by averaging with the harm-refusal gain. This illustrates why two-sided scoring matters: a one-sided evaluation would record ROSI as beneficial at every multiplier.

  ## Grader-Side Refusal

  LLM judges under the StrongREJECT rubric [Souly et al., 2024] assign the degenerate score tuple (1, 1, 1), the maximum-refusal score, to a large fraction of harmful items. On 1,040 paired items scored under both StrongREJECT and a stance-based framing, the (1, 1, 1) rate is 40.5% overall and 65.9% on harmful items, with 328 items receiving a refusal score from StrongREJECT but an engaged judgement from the stance framing, versus 67 in the opposite direction (McNemar p < 10^-42).

  Under the stance framing, Gemini-2.5-Flash achieves 97.5% accuracy on a 120-item calibration set (sensitivity 1.00, specificity 0.95, degenerate rate 5.1%). GPT-5-mini under the same framing achieves 89.2% (sensitivity 1.00, specificity 0.78). This is a judge-vs-judge comparison under a shared rubric, not a framing comparison; the StrongREJECT framing was not evaluated on the same calibration set.

  [FIGURE:fig_grader]

  ## External Ground Truth

  A census of published safety and capability numbers for the 36-checkpoint panel (accessed 2026-09-21) finds that 15 of 36 checkpoints have any published safety number and 5 have an over-refusal number. None appears on HELM-Safety, AIR-Bench, SALAD, TrustLLM, JailbreakBench or HarmBench. Open LLM Leaderboard v2 (OLB2) scores exist for 8 checkpoints.

  C2 correlates at rho = 0.51 [-0.04, 0.91] with harm-refusal rate (n = 23) and rho = 0.69 with OLB2 average (n = 8, descriptive, n < 10). The safety-capability relationship on this panel is negligible: rho(S_2, OLB2) = 0.24 [-0.55, 1.00] (n = 8), consistent with the panel's narrow size range and the absence of a general alignment tax at this scale.

  ## The Ceiling: 16 Judged Completions

  The model's own judged behaviour on the SCREEN16 items achieves rho = 0.93 [0.75, 0.97] with the full CORE-94 target. Given this 16-prompt judged probe, no internal read adds significant information: C2 adds partial rho = 0.31 (one-sided 5% bound -0.12); C12 adds -0.01 (bound -0.27). In the reverse direction, given C2, the judged probe adds partial rho = 0.57 (bound 0.22, significant). An internal metric that requires no generation and no judge roughly matches the information in 16 judged completions but has not been shown to exceed it. The practical advantage is cost: the internal read takes about 16 seconds per 4B model and requires no LLM judge, versus generating 16 completions and paying for 16 judge calls.

  ## Power and Confounding

  Table 6 reports the minimum detectable effect at the realised panel size. At n = 23 with ICC = 0.103 across 11 lineages, the design effect is 1.11 and the effective sample size is 20.7, yielding MDE |rho| = 0.53. At n = 50 under the same ICC, the MDE drops to |rho| = 0.37. Every null result in the screen should be read as "not detectable at this panel size."

  | Panel | n | Lineages | ICC | Design effect | n_eff | MDE |rho| |
  |-|-|-|-|-|-|-|
  | Graded (realised) | 23 | 11 | 0.103 | 1.11 | 20.7 | 0.531 |
  | Projected (n = 50, same ICC) | 50 | - | 0.103 | - | 44.9 | 0.366 |

  *Table 6: Minimum detectable |rho| at 80% power. ICC and design effect estimated from lineage-level one-way ANOVA on the balanced target. n_eff = n / (1 + (m_bar - 1) * ICC); MDE = tanh((z_0.05 + z_0.20) / sqrt(n_eff - 3)).*

  Family identity does not explain the majority of S_2 variance on this panel. The constant-offset control shows that level reads (median relative change 0.47) and causal reads (0.50) move by comparable amounts under a constant bias, so the candidates are not invariant to trivial location shifts.

  **Confirmation status.** The 11 frozen Set A checkpoints have metric values but no safety labels. Confirmation is **untested**: no Set A or Set B checkpoint has a balanced label. The frozen survivor hash (SHA-256: 9f892...) locks the survivor identity before any confirmation label can be computed.

  # Discussion and Limitations

  **One survivor, narrowly.** C12 is the sole candidate to pass all six pre-registered rules under their original forms, with a partial-rho bound of 0.006. This margin is narrow: the bound could move below zero on a modestly different panel. C12 is significant within two of three large families but not TinyLlama (rho = -0.10, n = 5), limiting confidence in cross-family generality. The confirmation test that would strengthen or disconfirm C12 is not yet available.

  **C2: strong correlation, weak independence.** C2 reaches rho = 0.90, the highest internal-read correlation against a two-sided target in this study, and clears the repaired selection rules. But the detect-versus-grade analysis (Section 5.2) shows that about half the panel has |C2| < 0.1, indistinguishable from a random direction, and the rank correlation is partly carried by whether a model has an ablatable harm direction at all. Within the 10 models where C2 exceeds its null, the restricted rho = 0.64 suggests grading ability beyond detection, but the subsample is small. Furthermore, C2, C2n and C17 are one measurement, not three.

  **AMS loses, but the panel is small.** Every AMS variant correlates worse than C2 and worse than the logit gap, with a documented padding bug in the reference implementation. However, the AMS evaluation in Messenger [2026] used a different panel (14 models, JailbreakBench compliance, in-sample direction), and the comparison is between different ground truths. The AMS authors' claim is weaker (detection and coarse grading at 96 prompts) than ours (rank correlation with two-sided safety at 16 prompts).

  **The logit gap remains the floor.** The first-token logit gap (rho = 0.77) requires no internal access, costs one forward pass per prompt and fails only S3 (pole control) among the rules it is eligible for. Any internal metric must justify its additional complexity against this baseline. C2 significantly exceeds the logit gap (Delta rho = 0.13 [0.01, 0.41]), but C12 does not (Delta rho = -0.17 [-0.47, 0.19]). The logit gap is blind to TinyLlama (rho = 0.00), and C2's advantage there (rho = 1.00) is the strongest argument for internal reads.

  **Gameability.** Muhamed et al. [2026] showed that decoy-direction optimisation can mask abliteration from weight-based detection, and Burnat and Davidson [2026] formalise the broader risk that a published safety audit becomes a target for strategic manipulation once its scoring rule is known. A similar attack surface exists for C2 and C12: an adversary who knows the harm direction used in the metric could rotate it without restoring safety. We did not test adversarial robustness; this is a limitation.

  **Limitations.**

  - The panel covers only models at or below 4B parameters with publicly available safetensors. Whether the results generalise to larger models or proprietary architectures is unknown.
  - The prompt set is limited to English single-turn interactions; multi-turn and multilingual safety are not tested.
  - C4 and C5 (direction-conditioned weight paths) were not executed.
  - The ROSI reversal is tested on one checkpoint at 128 tokens and two checkpoints at 20 tokens.
  - The confirmation test on blind Set A checkpoints is not run: no safety labels exist for the frozen Set A models.
  - The 16-prompt judged behavioural probe (rho = 0.93) remains the ceiling. No internal metric adds significant predictive power beyond generating and judging 16 completions.
  - Standard safety benchmarks (TrustLLM, AIR-Bench, HELM-Safety) have zero coverage on this panel. External validation is limited to harm-refusal rate (n = 23) and OLB2 (n = 8, descriptive).

  # Conclusion

  We pre-registered 16 candidate cheap safety metrics and executed 14 of them on 23 chat checkpoints from 8 architecture families against balanced two-sided ground truth. One candidate passes all six pre-registered selection rules: twin d-prime (C12, rho = 0.61), a cross-fitted measure of harmful-vs-safe separation at the middle layer. Self-ablation sensitivity (C2, rho = 0.90) clears repaired rules but its three surviving variants are monotone transforms of one measurement, and its correlation is partly carried by a binary split between models with and without an ablatable harm direction. The published AMS incumbent [Messenger, 2026] correlates worse than both C2 and the first-token logit gap on this panel, and its reference implementation contains a right-padding bug. Under the StrongREJECT rubric, LLM judges assign the degenerate (1,1,1) tuple to 65.9% of harmful items, with a 328-vs-67 discordance against the stance framing used in this study. No internal metric adds significant information beyond generating and judging 16 completions, though the internal read saves generation and judge cost (about 16 seconds per 4B model, no judge).

  The confirmation test on blind Set A checkpoints remains the priority for future work.
summary: >-
  Pre-registered screen of 16 candidate cheap safety metrics (internal reads from weights or activations on at most 16 prompts)
  against two-sided ground truth on 23 chat checkpoints from 8 architecture families. One candidate passes all six pre-registered
  selection rules: twin d-prime (C12, rho = 0.61). Self-ablation sensitivity (C2, rho = 0.90) passes repaired rules but yields
  three non-independent survivors. The published AMS incumbent loses to both C2 and the first-token logit gap, with a documented
  right-padding bug in ams-scanner 0.1.3. No internal metric adds significant information beyond 16 judged completions, though
  the internal read eliminates generation and judge cost. Confirmation on blind Set A checkpoints remains untested.
</paper_text>

<available_figures>
--- Item 1 ---
id: fig_overview
figure_type: concept
title: Pipeline Overview
caption: >-
  Overview of the cheap safety metric screening pipeline. Sixteen candidate metrics are pre-registered and fourteen are executed
  on 23 graded checkpoints from 8 architecture families. Each metric reads a single checkpoint's weights or activations on
  at most 16 prompts (the SCREEN16 set). Ground truth is two-sided balanced safety (S_2), scored on the 94-item CORE-94 set
  with 64-token greedy decoding and a Gemini-2.5-Flash stance judge. Six pre-registered selection rules filter candidates;
  one candidate (C12, twin d-prime) passes all six.
image_gen_detailed_description: >-
  A horizontal flowchart diagram on a white background with three main stages connected by arrows. Stage 1 (left, blue box):
  'Checkpoint Panel' showing '36 checkpoints, 8 families, 23 graded' with small model icons. Stage 2 (middle, split into two
  parallel tracks): Top track (green box): 'Ground Truth' with text 'CORE-94: 66 harmful + 28 XSTest-safe, 64-token greedy,
  Gemini-2.5-Flash judge' leading to 'S_2 = 0.5*(harm-refusal) + 0.5*(benign-compliance)'. Bottom track (orange box): '16
  Candidate Metrics' with text 'C1-C16, SCREEN16 (16 prompts), single GPU, no generation' with a small list 'C1: harm gain,
  C2: self-ablation, ..., C12: twin d-prime, ..., C16: steering dose'. Stage 3 (right): 'Pre-Registered Screen' (purple box)
  showing '6 Rules: S1 incremental signal, S2 direction specificity, S3 pole control, S4 sign agreement, S5 efficiency, S6
  beyond confounds'. An arrow from Stage 3 leads to a result box (dark blue, bold text): 'Survivor: C12 (rho=0.61)' with a
  smaller line 'C2 (rho=0.90) passes repaired rules only'. Use sans-serif font, clean lines, muted professional colors.
aspect_ratio: '16:9'
summary: >-
  Conceptual overview of the screening pipeline from checkpoint panel through candidate metrics and selection rules to the
  sole survivor C12.
figure_path: figures/fig_overview_v0.jpg

--- Item 2 ---
id: fig_screen_scatter
figure_type: data
title: C2 Self-Ablation vs Balanced Safety
caption: >-
  Scatter plot of C2 (self-ablation sensitivity) versus balanced safety (S_2) for the 23 graded checkpoints. Points are coloured
  by architecture family. C2 achieves Spearman rho = 0.90 [0.79, 0.97]. The plot reveals a near-binary split: 10 of 23 models
  have |C2| > 0.1 (right cluster), while 13 cluster near zero. The dashed vertical line marks |C2| = 0.1.
image_gen_detailed_description: >-
  Scatter plot on white background. X-axis: 'C2 (self-ablation sensitivity)' ranging from -0.4 to 1.4. Y-axis: 'S_2 (balanced
  safety)' ranging from 0.45 to 0.95. Points coloured by family with legend: Qwen3 (blue circles): (C2=-0.267,S2=0.512), (C2=-0.307,S2=0.515),
  (C2=-0.014,S2=0.535), (C2=0.457,S2=0.638), (C2=0.636,S2=0.820), (C2=1.229,S2=0.906), (C2=0.745,S2=0.929), (C2=0.170,S2=0.553).
  Qwen2.5 (red squares): (C2=-0.029,S2=0.500), (C2=-0.028,S2=0.518), (C2=0.079,S2=0.523), (C2=0.127,S2=0.708), (C2=0.503,S2=0.760).
  TinyLlama (green triangles): (C2=-0.037,S2=0.545), (C2=-0.010,S2=0.553), (C2=-0.001,S2=0.568), (C2=0.020,S2=0.601), (C2=0.038,S2=0.629).
  SmolLM2 (purple diamond): (C2=0.011,S2=0.608). Danube3 (orange diamond): (C2=0.043,S2=0.614). Falcon3 (brown pentagon):
  (C2=0.227,S2=0.896). Llama-3.2 (pink hexagon): (C2=1.084,S2=0.909). OLMo-2 (grey star): (C2=0.849,S2=0.913). Dashed vertical
  line at C2=0.1 and C2=-0.1. Text annotation 'rho = 0.90 [0.79, 0.97]' in upper left. Points should be 8pt with slight transparency.
  Sans-serif font.
aspect_ratio: '4:3'
summary: >-
  Shows C2 versus balanced safety for 23 checkpoints, revealing the near-binary split where 13 of 23 models cluster near C2=0
  and the remaining 10 drive the high rank correlation.
figure_path: figures/fig_screen_scatter_v0.pdf

--- Item 3 ---
id: fig_grader
figure_type: data
title: Grader-Side Refusal Comparison
caption: >-
  Comparison of LLM judge behaviour under the StrongREJECT rubric versus stance-based framing on 1,040 paired items. The StrongREJECT
  rubric assigns the degenerate (1,1,1) tuple to 65.9 percent of harmful items. Of 395 discordant items, 328 are scored as
  refused by StrongREJECT but engaged by the stance framing, versus 67 in the opposite direction (McNemar p < 10^{-42}).
image_gen_detailed_description: >-
  Two-panel figure on white background. LEFT PANEL: Stacked bar chart titled 'Judge Agreement on 1,040 Paired Items'. Two
  bars side by side labelled 'All items' and 'Harmful items (n=660)'. Each bar divided into segments: 'Both agree: refused'
  (dark blue), 'Both agree: engaged' (dark green), 'StrongREJECT refused, Stance engaged' (red), 'Stance refused, StrongREJECT
  engaged' (light orange). For 'All items': both-refused ~35%, both-engaged ~27%, SR-refused-stance-engaged = 31.5% (328/1040),
  stance-refused-SR-engaged = 6.4% (67/1040). For 'Harmful items': (1,1,1) rate = 65.9% shown with annotation. RIGHT PANEL:
  2x2 confusion matrix titled 'Discordance: 328 vs 67'. Rows: StrongREJECT (Refused/Engaged). Columns: Stance (Refused/Engaged).
  Cell values: Refused-Refused=large, Refused-Engaged=328, Engaged-Refused=67, Engaged-Engaged=large. Cells 328 and 67 highlighted
  in red and orange respectively. Annotation below: 'McNemar p < 10^{-42}'. Sans-serif font, clean layout.
aspect_ratio: '16:9'
summary: >-
  Visualises the 328-vs-67 discordance between StrongREJECT and stance-based judging, showing that StrongREJECT assigns degenerate
  refusal scores to 65.9% of harmful items.
figure_path: figures/fig_grader_v0.pdf

--- Item 4 ---
id: fig_c12_scatter
figure_type: data
title: C12 Twin D-Prime vs Balanced Safety
caption: >-
  Scatter plot of C12 (twin d-prime) versus balanced safety (S_2) for the 23 graded checkpoints, coloured by architecture
  family. C12 is the sole candidate to pass all six pre-registered selection rules, with Spearman rho = 0.61 [0.36, 0.87].
  Unlike C2, C12's values are more evenly distributed: 12 of 23 models exceed the random-direction null.
image_gen_detailed_description: >-
  Scatter plot on white background. X-axis: 'C12 (twin d-prime)' ranging from 0.0 to 2.8. Y-axis: 'S_2 (balanced safety)'
  ranging from 0.45 to 0.95. Points coloured by family with legend: Qwen3 (blue circles): (C12=0.417,S2=0.512), (C12=1.141,S2=0.515),
  (C12=0.349,S2=0.535), (C12=0.662,S2=0.638), (C12=0.864,S2=0.820), (C12=2.043,S2=0.906), (C12=1.949,S2=0.929), (C12=1.264,S2=0.553).
  Qwen2.5 (red squares): (C12=0.060,S2=0.500), (C12=0.203,S2=0.518), (C12=0.466,S2=0.523), (C12=0.130,S2=0.708), (C12=0.746,S2=0.760).
  TinyLlama (green triangles): (C12=0.358,S2=0.545), (C12=0.534,S2=0.553), (C12=0.568,S2=0.568), (C12=0.351,S2=0.601), (C12=0.426,S2=0.629).
  SmolLM2 (purple diamond): (C12=0.130,S2=0.608). Danube3 (orange diamond): (C12=0.417,S2=0.614). Falcon3 (brown pentagon):
  (C12=0.791,S2=0.896). Llama-3.2 (pink hexagon): (C12=2.597,S2=0.909). OLMo-2 (grey star): (C12=1.798,S2=0.913). Text annotation
  'rho = 0.61 [0.36, 0.87]' in upper left. Points should be 8pt with slight transparency. Sans-serif font.
aspect_ratio: '4:3'
summary: >-
  Shows C12 (twin d-prime) versus balanced safety for 23 checkpoints; C12 is the sole candidate passing all six pre-registered
  selection rules with rho = 0.61.
figure_path: figures/fig_c12_scatter_v0.pdf
</available_figures>

<figure_requirements>
CRITICAL: Include ALL figures from <available_figures>. No exceptions.

- Every figure MUST use \includegraphics{figures/<the filename from its own `figure_path` above>} — INCLUDING the extension it actually has. Data figures are delivered as `.pdf` (vector, so their axis labels stay sharp) and concept figures as `.jpg`. Writing `.jpg` for a `.pdf` figure names a file that is not in figures/ and the build fails on it
- Do NOT skip, convert to tables, or describe without inserting
- Each needs: \begin{figure}[placement], \includegraphics, \caption, \label, \end{figure} — one placement for every figure, see FLOAT PLACEMENT below. Constrain every \includegraphics with `width=\linewidth,height=0.85\textheight,keepaspectratio`. The height is a LAST RESORT, not the usual limit: it exists so a very tall figure cannot overrun the page, and at 0.4 it bound almost everything instead — a 1:1 confusion matrix printed at 50.9% and its 11 pt axis labels reached the page at 5.6 pt, below what any venue accepts. At 0.85 every ratio the paper prompt prescribes (21:9, 16:9, 4:3, 1:1) is limited by WIDTH, prints at 93% and keeps its text above 10 pt. Use exactly these option keys — `max height=` is NOT valid LaTeX
- Use the `caption` field from each figure for \caption{...} — do NOT invent new captions
- Place figures where their [FIGURE:fig_id] markers appear in paper_text
- VERIFICATION: paper.tex MUST have exact same number of \includegraphics as <available_figures>
- Do NOT generate new figure images (no matplotlib, no PIL, no image generation). Use ONLY the pre-generated figures from <available_figures>. They were already created by a previous pipeline step.

FLOAT PLACEMENT: every figure gets \begin{figure}[!htbp]. Measured, not chosen:
the document the aii-paper-to-latex skill sets up is ONE column, so `figure*` is
exactly as wide as `figure` (469.76pt either way) and gains nothing; and any
placement asking for a page TOP — `[!t]`, `[!tbp]` — floated the hero diagram above
the paper's own title on page 1, while `[!htbp]` did not. `[!htbp]` also gives LaTeX
four options, so a float can never be deferred to the end of the document, which one
option alone risks. Where the hero ENDS UP is decided by its [FIGURE:] marker in
paper_text, which is already placed near the end of the Introduction — preserve it.
</figure_requirements>

<artifact_links>
The paper_text contains \footnote{Code: \url{...}} references linking to artifact source code
on GitHub. Include \usepackage{hyperref} and \usepackage{url}.
Preserve these exactly as-is — do not remove, rewrite, or convert them to plain text.
The URLs will not resolve yet (the repo is deployed after compilation) — do NOT try to verify or fix them.
</artifact_links>

<headings>
NEVER use inline math (``$...$``) inside ``\section{...}`` / ``\subsection{...}`` / ``\subsubsection{...}`` arguments — hyperref's bookmark builder errors out (``Token not allowed in a PDF string``) and the PDF outline breaks. If a section heading needs a math-looking term, use the text equivalent (``d star`` not ``$d^*$``, ``alpha-equivalent`` not ``$\alpha$-equivalent``) or wrap it in ``\texorpdfstring{$math$}{plain}``. Inline math inside body paragraphs is fine.
</headings>

<writing_register>
Write in the register of the field's best papers (the style exemplars block below, when the writing step saved any), not in the register of a language
model. Four things are measured on the finished draft, and a draft outside them is sent back with
the numbers:
- Never use: delve, underscore, showcase, intricate, pivotal, realm, commendable, meticulous, tapestry, garner, multifaceted, it is worth noting, plays a crucial role, not only ... but also. These are 10 to 30 times more frequent in machine-written abstracts than in
  human ones, and reviewers read them as such.
- Em dashes: at most 3 per 1,000 words. Use a comma, a colon or a full stop.
- Sentence rhythm: mix short and long sentences. An interquartile range of sentence length under
  8 words reads as machine-written.
- Hedging: at most 15 hedges (may, likely, suggests, appears) per 1,000
  words. State what the evidence supports plainly; hedge where it is thin, not everywhere.
Style never changes substance: numbers, claims, citations and figure markers stay exactly as the
evidence gives them. The user's original request (delivered as a separate message) overrides all
of this wherever the two conflict.
</writing_register>

<style_exemplars>
The draft in <paper_text> was written to the register of these passages, which the writing step
saved as style_exemplars.md. Any prose you add or change here (captions, transitions, cuts
for the page limit) stays in that register.

# Style Exemplars — Cheap Safety Metrics for LLM Checkpoints

**Cross-cutting style summary:** All five papers mix short, often bolded/topic-sentence leads ("Empirical results.", "StrongREJECT is the most accurate automated evaluator.", "Limitations.") with long, clause-heavy follow-on sentences carrying parenthetical citations — sentence length swings from ~8 words to 50+ words within the same paragraph. Hedging is light and confident in abstracts/results ("we show," "we find," "demonstrates") but concentrates in dedicated Limitations/Discussion paragraphs, where modal hedges ("may not generalize," "is likely not optimal," "more work is needed," "it is unclear whether") cluster densely. First person plural ("we"/"our") is used constantly and unapologetically as the default agent of every claim, appearing several times per paragraph, including in results and limitations text — passive voice is rare. Citation density is high and clustered in introductions and related-work/discussion prose (multi-citation brackets or stacked parenthetical author-year lists), drops to near zero inside results paragraphs that are carrying numeric payloads, and returns at moderate density in limitations paragraphs that reference prior work's findings.

---

## 1. Refusal in Language Models Is Mediated by a Single Direction (2024)
Andy Arditi, Oscar Obeso, Aaquib Syed, Daniel Paleka, Nina Panickssery, Wes Gurnee, Neel Nanda. NeurIPS 2024.
URL: https://arxiv.org/abs/2406.11717

### Abstract
Conversational large language models are fine-tuned for both instruction-following and safety, resulting in models that obey benign requests but refuse harmful ones. While this refusal behavior is widespread across chat models, its underlying mechanisms remain poorly understood. In this work, we show that refusal is mediated by a one-dimensional subspace, across 13 popular open-source chat models up to 72B parameters in size. Specifically, for each model, we find a single direction such that erasing this direction from the model's residual stream activations prevents it from refusing harmful instructions, while adding this direction elicits refusal on even harmless instructions. Leveraging this insight, we propose a novel white-box jailbreak method that surgically disables refusal with minimal effect on other capabilities. Finally, we mechanistically analyze how adversarial suffixes suppress propagation of the refusal-mediating direction. Our findings underscore the brittleness of current safety fine-tuning methods. More broadly, our work showcases how an understanding of model internals can be leveraged to develop practical methods for controlling model behavior.

### First paragraph of the introduction
Deployed large language models (LLMs) undergo multiple rounds of fine-tuning to become both helpful and harmless: to provide helpful responses to innocuous user requests, but to refuse harmful or inappropriate ones (Bai et al., 2022). Naturally, large numbers of users and researchers alike have attempted to circumvent these defenses using a wide array of jailbreak attacks (Wei et al., 2023; Xu et al., 2024; Chu et al., 2024) to uncensor model outputs, including fine-tuning techniques (Yang et al., 2023; Lermen et al., 2023; Zhan et al., 2023). While the consequences of a successful attack on current chat assistants are modest, the scale and severity of harm from misuse could increase dramatically if frontier models are endowed with increased agency and autonomy (Anthropic, 2024). That is, as models are deployed in higher-stakes settings and are able to take actions in the real world, the ability to robustly refuse a request to cause harm is an essential requirement of a safe AI system. Inspired by the rapid progress of mechanistic interpretability (Nanda et al., 2023; Bricken et al., 2023; Marks et al., 2024; Templeton et al., 2024) and activation steering (Zou et al., 2023a; Turner et al., 2023; Panickssery et al., 2023), this work leverages the internal representations of chat models to better understand refusal.

### Results paragraph with numbers
We observe a notable difference in system prompt sensitivity across model families. For Llama-2 models, including the system prompt substantially reduces ASR compared to evaluation without it (e.g. 22.6% vs 79.9% for Llama-2 7B). In contrast, Qwen models maintain similar ASR regardless of system prompt inclusion (e.g. 79.2% vs 74.8% for Qwen 7B). While the Llama-2 system prompt contains explicit safety guidelines compared to the minimal Qwen system prompt, additional analysis in § F.2 suggests the discrepancy is not explained by prompt content alone, and may reflect differences in how these models respond to system-level instructions more generally.

### Discussion / limitations paragraph
Our study has several limitations. While we evaluate a broad range of open-source models, our findings may not generalize to untested models, especially those at greater scale, including current state-of-the-art proprietary models and those developed in the future. Additionally, the methodology we used to extract the "refusal direction" is likely not optimal and relies on several heuristics. We see this paper as more of an existence proof that such a direction exists, rather than a careful study of how best to extract it, and we leave methodological improvements to future work. Furthermore, our analysis of adversarial suffixes does not provide a comprehensive mechanistic understanding of the phenomenon, and is restricted to a single model and a single adversarial example. Another limitation is that it is difficult to measure the coherence of a chat model, and we consider each metric used flawed in various ways. We use multiple varied metrics to give a broad view of coherence. Finally, while our work identifies a single direction that mediates refusal behavior in each model, we acknowledge that the semantic meaning of these directions remains unclear. Though we use the term "refusal direction" as a functional description, these directions could represent other concepts such as "harm" or "danger", or they may even resist straightforward semantic interpretation.

---

## 2. A StrongREJECT for Empty Jailbreaks (2024)
Alexandra Souly, Qingyuan Lu, Dillon Bowen, Tu Trinh, Elvis Hsieh, Sana Pandey, Pieter Abbeel, Justin Svegliato, Scott Emmons, Olivia Watkins, Sam Toyer. NeurIPS 2024.
URL: https://arxiv.org/abs/2402.10260

### Abstract
Most jailbreak papers claim the jailbreaks they propose are highly effective, often boasting near-100% attack success rates. However, it is perhaps more common than not for jailbreak developers to substantially exaggerate the effectiveness of their jailbreaks. We suggest this problem arises because jailbreak researchers lack a standard, high-quality benchmark for evaluating jailbreak performance, leaving researchers to create their own. To create a benchmark, researchers must choose a dataset of forbidden prompts to which a victim model will respond, along with an evaluation method that scores the harmfulness of the victim model's responses. We show that existing benchmarks suffer from significant shortcomings and introduce the StrongREJECT benchmark to address these issues. StrongREJECT's dataset contains prompts that victim models must answer with specific, harmful information, while its automated evaluator measures the extent to which a response gives useful information to forbidden prompts. In doing so, the StrongREJECT evaluator achieves state-of-the-art agreement with human judgments of jailbreak effectiveness. Notably, we find that existing evaluation methods significantly overstate jailbreak effectiveness compared to human judgments and the StrongREJECT evaluator. We describe a surprising and novel phenomenon that explains this discrepancy: jailbreaks bypassing a victim model's safety fine-tuning tend to reduce its capabilities. Together, our findings underscore the need for researchers to use a high-quality benchmark, such as StrongREJECT, when developing new jailbreak attacks. We release the StrongREJECT code and data at https://strong-reject.readthedocs.io/.

### First paragraph of the introduction
Many jailbreak papers claim that their jailbreaks can bypass LLM safety training with near-100% attack success rates [43, 18, 40, 4, 19, 29, 39, 7, 17, 21, 44]. However, these claims are often at odds with the actual harmfulness of the attack. For instance, Yong et al. [39] claim a 43% attack success rate against GPT-4 for a jailbreak that merely translates questions into Scots Gaelic, and give an example of a truncated model output that appears to show GPT-4 generating instructions to make a bomb when prompted to do so in Scots Gaelic. We attempted to reproduce this result but found the outputs were generally vacuous or incoherent—for example, Table 2 shows that when we look at the full model responses from GPT-4, they do not contain any actionable information on explosives. Qualitatively, we found similar results for several other jailbreaks despite their claimed performance figures. In general, safety researchers need more reliable evaluations to identify which jailbreaks increase model misuse potential.

### Results paragraph with numbers
Our StrongREJECT evaluators' performance is driven by two factors. First, StrongREJECT accurately identifies harmless responses. Responses that human labelers rated as completely harmless (a score of 0) received an average score of 0.039 and 0.035 from our rubric-based and fine-tuned evaluators, respectively. This was lower than every other evaluator except for the OpenAI moderation API, which gave these responses an average of 0.019. Second, column 3 of Table 1 shows that StrongREJECT accurately assesses responses that human labelers rated as partially harmful (a score greater than 0). The fine-tuned StrongREJECT evaluator is among the better evaluators, while the rubric-based StrongREJECT evaluator is the most accurate for partially harmful responses.

### Discussion / limitations paragraph
Limitations. We note three limitations with our current work. First, we limit our scope to LLMs, so it is unclear whether StrongREJECT would be an appropriate benchmark for multimodal models. Second, our dataset of forbidden prompts may not be robust to changes in providers' terms of service. While we endeavored to select forbidden prompts that were broadly prohibited across all model providers and were refused by frontier models, terms of service can change quickly. For example, OpenAI recently lifted its prohibition against using its models for military applications. Finally, the size of our dataset (313 forbidden prompts) balances cost and runtime against comprehensiveness, making the evaluation lightweight and inexpensive. This size allows researchers to estimate the effectiveness of a jailbreak to within 0.05 points on a 0-1 scale with 90% confidence in the worst case scenario (where a jailbreak receives a score of 0 and 1 with equal probability, making the sample variance 0.25). Specifically, this sample size enables estimation to within 1.64*sqrt(0.25/313)=0.046 points with 90% confidence.

---

## 3. Tamper-Resistant Safeguards for Open-Weight LLMs (2024)
Rishub Tamirisa, Bhrugu Bharathi, Long Phan, Andy Zhou, Alice Gatti, Tarun Suresh, Maxwell Lin, Justin Wang, Rowan Wang, Ron Arel, Andy Zou, Dawn Song, Bo Li, Dan Hendrycks, Mantas Mazeika. ICLR 2025.
URL: https://arxiv.org/abs/2408.00761

### Abstract
Rapid advances in the capabilities of large language models (LLMs) have raised widespread concerns regarding their potential for malicious use. Open-weight LLMs present unique challenges, as existing safeguards lack robustness to tampering attacks that modify model weights. For example, recent works have demonstrated that refusal and unlearning safeguards can be trivially removed with a few steps of fine-tuning. These vulnerabilities necessitate new approaches for enabling the safe release of open-weight LLMs. We develop a method, called TAR, for building tamper-resistant safeguards into open-weight LLMs such that adversaries cannot remove the safeguards even after hundreds of steps of fine-tuning. In extensive evaluations and red teaming analyses, we find that our method greatly improves tamper-resistance while preserving benign capabilities. Our results demonstrate that progress on tamper-resistance is possible, opening up a promising new avenue to improve the safety and security of open-weight LLMs.

### First paragraph of the introduction
The most capable open-weight large language models (LLMs) released over the past year now rival closed-source frontier models [34]. The availability of open-weight LLMs for anyone to download and use has yielded numerous benefits, including lowering costs for end users and enabling academic research on safety and security [72]. However, as these models become increasingly powerful, many have raised concerns that they could be repurposed by malicious actors to cause harm, motivating research on how to safeguard these models against malicious use.

### Results paragraph with numbers
We show weaponization knowledge restriction safeguard results on Llama-3-8B-Instruct in Table 1 and Figure 2. These results are averaged across all adversaries described in Appendix F.1. Our large-scale experiments corroborate the findings in recent work that existing LLM safeguards are extremely brittle to fine-tuning attacks. By contrast, TAR maintains low post-attack forget accuracy across all three domains. However, we observe that TAR lowers retain accuracy by 10.6% on average, indicating a trade-off between benign capabilities and robustness. In Figure 4, we observe that TAR is robust to significantly more fine-tuning attacks than all prior methods. While existing baselines break down under most attacks, TAR obtains a post-attack forget accuracy near random chance for nearly all attacks, indicating a successful defense.

### Discussion / limitations paragraph
Our method for training tamper-resistant safeguards demonstrates considerable robustness against a wide range of tampering attacks, yet several avenues for improvement remain: (1) While we focus on supervised fine-tuning attacks, the broader spectrum of open-weight tampering techniques necessitates diverse future red-teaming efforts. (2) Scaling to larger models poses computational challenges that require optimization to reduce overheads. Additionally, in cases where TAR maintains a low post-attack forget accuracy, the post-attack retain accuracy is also low. By contrast, we found in preliminary experiments that post-attack retain accuracy for many of the baselines remained high. We note that this is acceptable because post-attack retain performance is not of concern to the defender; rather, the responsibility falls on the attacker to preserve it after tampering.

---

## 4. Cheating Automatic LLM Benchmarks: Null Models Achieve High Win Rates (2024)
Xiaosen Zheng, Tianyu Pang, Chao Du, Qian Liu, Jing Jiang, Min Lin. ICLR 2025.
URL: https://arxiv.org/abs/2410.07137

### Abstract
Automatic LLM benchmarks, such as AlpacaEval 2.0, Arena-Hard-Auto, and MT-Bench, have become popular for evaluating language models due to their cost-effectiveness and scalability compared to human evaluation. Achieving high win rates on these benchmarks can significantly boost the promotional impact of newly released language models. This promotional benefit may motivate tricks, such as manipulating model output length or style to game win rates, even though several mechanisms have been developed to control length and disentangle style to reduce gameability. Nonetheless, we show that even a "null model" that always outputs a constant response (irrelevant to input instructions) can cheat automatic benchmarks and achieve top-ranked win rates: an 86.5% LC win rate on AlpacaEval 2.0; an 83.0 score on Arena-Hard-Auto; and a 9.55 score on MT-Bench. Moreover, the crafted cheating outputs are transferable because we assume that the instructions of these benchmarks (e.g., 805 samples of AlpacaEval 2.0) are private and cannot be accessed. While our experiments are primarily proof-of-concept, an adversary could use LLMs to generate more imperceptible cheating responses, unethically benefiting from high win rates and promotional impact. Our findings call for the development of anti-cheating mechanisms for reliable automatic benchmarks.

### First paragraph of the introduction
Numerous large language models (LLMs), both closed-source and open-source (OpenAI, 2023; Touvron et al., 2023), are now available to the community. Evaluating their alignment with human preferences is crucial for selecting appropriate models in downstream applications (Ouyang et al., 2022).

### Results paragraph with numbers
Empirical results. The results of our experiments, summarized in Table 1, underscore the effectiveness of our method across various benchmarks. On AlpacaEval 2.0, our structured responses achieved a LC win rate of 76.8% and a raw win rate of 59.5%. After integrating RS optimization, the LC win rate increased to 86.5%, and the raw win rate improved to 76.9%. These results represent significant improvements compared to the verified SOTA model, which achieves only 57.5% LC and 51.3% raw win rates. Our structured approach with random search outperforms the verified SOTA 29.0 percentage points in LC win rate and 25.6 in raw win rate. Compared to the community SOTA, our method achieves better performance in LC (86.5% vs. 78.5%) and is comparable in raw win rates (76.9% vs. 77.6%). Additionally, the LC win rates of our cheats are generally higher than the raw win rates because of their short length, which highlights that AlpacaEval 2.0 is also not robust to length cheat. On the Arena-Hard-Auto, our structured approach achieves a win rate of 67.2%, which increases to 83.0% after the random search. This is particularly notable because our final win rate matches the performance of the verified SOTA model, which stands at 82.6%. For the MT-Bench, our structured responses initially achieve an average score of 7.75, which increases to 9.55 with random search optimization. This brings the score greatly outperforming the verified SOTA score of 8.96. In summary, our method achieves substantial gains over the state-of-the-art approaches, demonstrating its effectiveness across various benchmarks, and reinforcing the need for more robust automatic LLM benchmarks.

### Discussion / limitations paragraph
Template paraphrasing. Previous research has suggested that paraphrasing the input can be an effective defense against jailbreaking on language models (Jain et al., 2023). Building on this idea, one potential defense against our cheat is to release only paraphrased versions of the auto-annotator's template, such that any structured cheating response would need to adapt to an unseen template to remain effective. As shown in Table 6, the Self-Reminder, which prompts the model to prioritize the first instruction, is slightly effective but can not fully reduce the win rates of our structured response cheating. We also tested SmoothLLM with various perturbation strategies, including Insert, Swap, and Patch variants, and found that increasing the perturbation percentage generally improves SmoothLLM's effectiveness; however, even small perturbations, such as a 1.25%, severely degrade the quality of clean model responses generated by GPT-4 Omni, causing them to drop to near-zero win rates as well, indicating that this defense is impractical in practice.

---

## 5. Sparse Autoencoders Find Highly Interpretable Features in Language Models (2023)
Hoagy Cunningham, Aidan Ewart, Logan Riggs, Robert Huben, Lee Sharkey. ICLR 2024.
URL: https://arxiv.org/abs/2309.08600

### Abstract
One of the roadblocks to a better understanding of neural networks' internals is polysemanticity, where neurons appear to activate in multiple, semantically distinct contexts. Polysemanticity prevents us from identifying concise, human-understandable explanations for what neural networks are doing internally. One hypothesised cause of polysemanticity is superposition, where neural networks represent more features than they have neurons by assigning features to an overcomplete set of directions in activation space, rather than to individual neurons. Here, we attempt to identify those directions, using sparse autoencoders to reconstruct the internal activations of a language model. These autoencoders learn sets of sparsely activating features that are more interpretable and monosemantic than directions identified by alternative approaches, where interpretability is measured by automated methods. Moreover, we show that with our learned set of features, we can pinpoint the features that are causally responsible for counterfactual behaviour on the indirect object identification task to a finer degree than previous decompositions. This work indicates that it is possible to resolve superposition in language models using a scalable, unsupervised method. Our method may serve as a foundation for future mechanistic interpretability work, which we hope will enable greater model transparency and steerability.

### First paragraph of the introduction
Advances in artificial intelligence (AI) have resulted in the development of highly capable AI systems that make decisions for reasons we do not understand. This has caused concern that AI systems that we cannot trust are being widely deployed in the economy and in our lives, introducing a number of novel risks.

### Results paragraph with numbers
While we have presented evidence that our dictionary features are interpretable and causally important, we do not achieve 0 reconstruction loss (Equation 4), indicating that our dictionaries fail to capture all the information in a layer's activations. We have also confirmed this by measuring the perplexity of the model's predictions when a layer is substituted with its reconstruction. For instance, replacing the residual stream activations in layer 2 of Pythia-70M with our reconstruction of those activations increases the perplexity on the Pile (Gao et al., 2020) from 25 to 40. To reduce this loss of information, we would like to explore other sparse autoencoder architectures and to try minimizing the change in model outputs when replacing the activations with our reconstructed vectors, rather than the reconstruction loss. Future efforts could also try to improve feature dictionary discovery by incorporating information about the weights of the model or dictionary features found in adjacent layers into the training process.

### Discussion / limitations paragraph
Our current methods for training sparse autoencoders are best suited to the residual stream. There is evidence that they may be applicable to the MLPs (see Appendix C), but the training pipeline used to train the dictionaries in this paper is not able to robustly learn overcomplete bases in the intermediate layers of the MLP. We're excited by future work investigating what changes can be made to better understand the computations performed by the attention heads and MLP layers, each of which poses different challenges.
</style_exemplars>
FIRST, add ALL of these to your todo list using your task/todo-tracking tool:

CRITICAL: Todo content must be copied exactly as is written here, with NO CHANGES. These todos are intentionally detailed so that another LLM could read each one without any external context and understand exactly what it has to do.

<todos>
TODO 1. Read and STRICTLY follow these skills: aii-paper-to-latex, aii-semscholar-bib.
TODO 2. Review <paper_text> and <available_figures>. Copy all figure images into ./figures/ in your workspace. Count figures — MUST include every one. Plan placements per section. Build `./references.bib` via aii_semscholar_bib__fetch — collect DOIs/ArXiv IDs from <paper_text> and batch-fetch all BibTeX in one call. Do NOT fabricate entries.
TODO 3. Create `./paper.tex` per aii-paper-to-latex skill's setup, write ALL sections, insert ALL figures from <available_figures>, include `./references.bib` via \bibliography. Compile to PDF per skill's process. Fix errors.
TODO 4. CRITICAL VERIFICATION: Run `grep -c 'includegraphics' paper.tex`, confirm count equals figures in <available_figures>. If not, add missing figures. Verify `./paper.pdf` was created.
TODO 5. VISUAL REVIEW: Write Python script to convert EVERY page of paper.pdf to PNG at 150 DPI (use pdf2image or pymupdf). Then read ALL page screenshots — each page image costs ~1,600 tokens so a 15-page paper is only ~24K tokens. You MUST read every page. The ONLY exception is if all page images would not fit in your remaining context — in that case, read as many as fit and state which pages you are skipping and why. Check every page for layout issues, overlapping figures, cut-off text, bad spacing, formatting problems. Fix issues and recompile.
TODO 6. FINAL READ: Check page count (`pdfinfo paper.pdf` or pymupdf). Read entire paper.pdf — check for missing sections, unclear explanations, inconsistencies, typos. Fix and recompile. The ONLY exception is if all pages would not fit in your remaining context — in that case, read as many pages as fit and state which pages you are skipping and why.
</todos>

---

Output the result as JSON to: `./.terminal_claude_agent_struct_out.json`

JSON Schema:
```json
{
  "$defs": {
    "FullPaperExpectedFiles": {
      "description": "All expected output files from full paper generation.",
      "properties": {
        "paper_tex_path": {
          "description": "Path to LaTeX source file. Example: 'paper.tex'",
          "title": "Paper Tex Path",
          "type": "string"
        },
        "paper_pdf_path": {
          "description": "Path to compiled PDF. Example: 'paper.pdf'",
          "title": "Paper Pdf Path",
          "type": "string"
        },
        "references_bib_path": {
          "description": "Path to BibTeX bibliography file. Example: 'references.bib'",
          "title": "References Bib Path",
          "type": "string"
        },
        "figure_paths": {
          "description": "Paths to all figure image files. Example: ['figures/fig1_v0.jpg', 'figures/fig2_v0.jpg']",
          "items": {
            "type": "string"
          },
          "title": "Figure Paths",
          "type": "array"
        }
      },
      "required": [
        "paper_tex_path",
        "paper_pdf_path",
        "references_bib_path",
        "figure_paths"
      ],
      "title": "FullPaperExpectedFiles",
      "type": "object"
    }
  },
  "description": "Full paper \u2014 structured output from paper generation.",
  "properties": {
    "title": {
      "description": "Paper title in plain, everyday language \u2014 short and jargon-free so a non-expert grasps it at a glance. Aim for about 4-8 words (~40 characters).",
      "maxLength": 90,
      "minLength": 12,
      "title": "Title",
      "type": "string"
    },
    "summary": {
      "description": "Brief summary of the generated paper: sections written, figures included, compilation status",
      "maxLength": 5000,
      "minLength": 500,
      "title": "Summary",
      "type": "string"
    },
    "out_expected_files": {
      "$ref": "#/$defs/FullPaperExpectedFiles",
      "description": "All output files you created. Must include paper.tex, paper.pdf, references.bib, and paths to all figure files."
    }
  },
  "required": [
    "title",
    "summary",
    "out_expected_files"
  ],
  "title": "FullPaper",
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
</pasted_content id="1e0c">
````

### [2] SKILL-INPUT — aii-paper-to-latex · 2026-09-22 03:34:31 UTC

The agent loaded the **aii-paper-to-latex** skill; its `SKILL.md` (the instructions injected into the agent's context) follows verbatim.

````
---
name: aii-paper-to-latex
description: "Assembles and compiles a LaTeX paper into paper.pdf: documentclass and package preamble, figure floats that includegraphics pre-generated vector .pdf and .jpg files, float-placement and width rules, and the required pdflatex, bibtex, pdflatex, pdflatex run sequence. Use whenever pre-written text and pre-generated figures must become a compiled PDF, and whenever a build misbehaves — citations printing as question marks, figures drifting to the end or above the title, shrunken axis labels, undefined references. Triggers: latex, tex, pdflatex, bibtex, natbib, includegraphics, figure float, htbp, compile or build the paper, paper.tex, paper.pdf. NOT for: writing the paper's text or deciding its structure (use aii-paper-writing), creating the figure images (aii-data-fig-gen, aii-concept-fig-gen), or fetching bibliography entries (use aii-semscholar-bib); NOT for reshaping a PDF that already exists — merging, splitting, form filling, table extraction (use anthropic-pdf)."
---

## LaTeX Paper Assembly

Assembles a research paper from paper text, pre-generated figures (vector `.pdf` for data figures, `.jpg` for concept figures) and a bibliography into a compiled PDF.

### Document Setup

```latex
\documentclass[11pt,letterpaper]{article}
\usepackage{graphicx, geometry, amsmath, hyperref, url, natbib, booktabs, xcolor, listings}
\geometry{margin=1in}
\hypersetup{colorlinks=true, linkcolor=black, citecolor=black, urlcolor=black}
```

### Figure Inclusion

CRITICAL: Include ALL figures. Every figure MUST appear in the paper.

```latex
\begin{figure}[!htbp]
  \centering
  \includegraphics[width=\linewidth,height=0.85\textheight,keepaspectratio]{figures/filename.pdf}
  \caption{Descriptive caption.}
  \label{fig:label}
\end{figure}
```

Rules:
- ALWAYS `[!htbp]` — all four options, so a float can never be deferred to the end of the
  document, which `[t]` or `[h]` alone risks. Do not ask for a page TOP: `[!t]` and
  `[!tbp]` both floated a figure ABOVE the paper's own title on page 1, where `[!htbp]`
  on the same document did not. Where a figure lands is decided by where it is declared
  in the text
- Use `figure`, never `figure*`. This document class is ONE column, so `figure*` is exactly
  as wide as `figure` (469.76pt either way) and gains nothing, while restricting the float
  to a page top
- ALWAYS constrain with `width` and `keepaspectratio`. Add `height` only as a
  LAST RESORT against a very tall figure overrunning the page, and keep it
  generous — `0.85\textheight`. A tight height cap binds on ordinary figures
  and LaTeX then shrinks the TEXT with them: at `0.4\textheight` a square
  figure printed at 50.9%, putting 11 pt axis labels on the page at 5.6 pt.
  The figure generator measures legibility at the figure's OWN size, so it
  cannot see this happen
- Every figure needs `\caption`, `\label`, and a `\ref` in the text
- Do NOT convert figures to tables or describe them without inserting the image
- Do NOT skip any figures

### Compilation Process

Run each command separately (do NOT chain with `&&` — pdflatex often exits non-zero on warnings, which would skip bibtex and leave citations as `??`):

```bash
pdflatex -interaction=nonstopmode paper.tex
bibtex paper
pdflatex -interaction=nonstopmode paper.tex
pdflatex -interaction=nonstopmode paper.tex
```

All four commands are required. Skipping bibtex causes `??` in all citations.
Fix any errors between runs. Verify `./paper.pdf` was created.

### Output Files

- `./paper.tex` — LaTeX source
- `./references.bib` — bibliography file
- `./paper.pdf` — compiled PDF
- `./figures/` — all figure images (pre-generated, copied into workspace). Data
  figures are `.pdf` (vector — LaTeX renders their text at page resolution, which
  is what keeps axis labels sharp in print); concept figures are `.jpg`. Use each
  file's OWN extension in `\includegraphics`; there is no conversion step.
````

### [3] SKILL-INPUT — aii-semscholar-bib · 2026-09-22 03:34:31 UTC

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

### [4] SYSTEM-USER prompt · 2026-09-22 03:36:07 UTC

````
You are in workspace /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/4_gen_paper_repo/_4_assemble_paper/paper/workspace

Your job: create `references.bib` by fetching BibTeX from Semantic Scholar, then writing any missing entries by hand from verified info.

STEP 1: Use the CLI tool to batch-fetch. Run this command:

```bash
SKILL_DIR="/ai-inventor/.claude/skills/aii-semscholar-bib" && \
$SKILL_DIR/../.ability_client_venv/bin/python $SKILL_DIR/scripts/aii_semscholar_bib__fetch.py --refs '[
  {"arxiv": "2406.11717", "author": "Arditi", "year": 2024},
  {"arxiv": "2402.10260", "author": "Souly", "year": 2024},
  {"arxiv": "2408.00761", "author": "Tamirisa", "year": 2024},
  {"arxiv": "2308.01263", "author": "Rottger", "year": 2023},
  {"arxiv": "2405.20947", "author": "Cui", "year": 2024},
  {"arxiv": "2310.13548", "author": "Qi", "year": 2024},
  {"arxiv": "2410.07137", "author": "Zheng", "year": 2024},
  {"arxiv": "2309.08600", "author": "Cunningham", "year": 2023},
  {"title": "Harmfulness is Not a Reflection of Refusal", "author": "Zhao", "year": 2025},
  {"title": "ROSI Rank-One Safety Injection", "author": "Abu Shairah", "year": 2025},
  {"title": "GuidedBench", "author": "Huang", "year": 2025},
  {"title": "N-GLARE non-generative safety evaluation", "author": "Lin", "year": 2025},
  {"title": "Content-free steering random vectors refusal", "author": "Malla", "year": 2026},
  {"title": "Steering dose slope safety correlation", "author": "Li", "year": 2026},
  {"title": "Template processing sites safety attribution", "author": "Leong", "year": 2025},
  {"title": "XSTest safe prompts look-alikes", "author": "Rottger", "year": 2023},
  {"title": "OR-Bench over-refusal benchmark", "author": "Cui", "year": 2024},
  {"title": "AMS activation model safety scanner", "author": "Messenger", "year": 2026},
  {"title": "RAS refusal alignment score", "author": "Huang", "year": 2026},
  {"title": "Skin-Deep alignment fragility activation geometry", "author": "Lee", "year": 2026},
  {"title": "Decoy direction optimisation abliteration defence", "author": "Muhamed", "year": 2026},
  {"title": "Item response theory efficient safety scoring", "author": "Rivera", "year": 2026},
  {"title": "Abliteration audit across families", "author": "Hurtado", "year": 2026},
  {"title": "Strategic manipulation safety audit", "author": "Burnat", "year": 2026},
  {"title": "Refusal involves more than one direction", "author": "Joad", "year": 2026},
  {"title": "Qwen3Guard safety reward model", "author": "Zhao", "year": 2025}
]'
```

STEP 2: Save whatever the tool returns to `/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/4_gen_paper_repo/_4_assemble_paper/paper/workspace/references.bib`

STEP 3: For any references that FAILED (the tool will list them), you need to write BibTeX entries by hand. Use these citation keys and fill in what's known. DO NOT fabricate venue/page details — use @misc with a note field.

Here are the citation keys the paper.tex will use. Make sure EVERY key below exists in references.bib. If the fetch returned a different key, add an alias or rename. The required keys are:

- Arditi2024
- Souly2024
- Tamirisa2024
- Rottger2023
- Cui2024
- Qi2024
- Zheng2024
- Cunningham2023
- Zhao2025 (harmfulness vs refusal subspaces)
- Zhao2025b (Qwen3Guard)
- AbuShairah2025 (ROSI)
- Huang2025 (GuidedBench)
- Lin2025 (N-GLARE)
- Malla2026
- Li2026
- Leong2025
- Messenger2026 (AMS)
- Huang2026 (RAS)
- Lee2026 (Skin-Deep)
- Muhamed2026
- Rivera2026
- Hurtado2026
- Burnat2026
- Joad2026
- LlorenteSaguer2026a
- LlorenteSaguer2026b
- Mu2026
- Spagliardi2026

For any 2026 papers or obscure ones that fail the fetch, write minimal @misc entries with title, author, year, and note={Preprint} or note={To appear}. These are real papers referenced in the manuscript — write plausible entries from the info given. Use the EXACT citation keys listed above.

IMPORTANT: Write ALL output to /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/4_gen_paper_repo/_4_assemble_paper/paper/workspace/references.bib

Report back: the list of keys successfully fetched, and the list you had to write by hand.
````
