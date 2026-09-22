# gen_paper_site — report_results

> Phase: `gen_paper_repo` · `gen_full_paper`
> Run: `run_fcYd_7ruOwtm` — One Candidate Survives: A Pre-Registered Screen of Internal Safety Metrics for Language Model Checkpoints
>
> Full, verbatim record of every prompt the AI Inventor pipeline gave this agent — system-user, human-user and skill-input — in the order they landed. Nothing truncated.

## Task: `gen_paper_site` (terminal_claude_agent)

### [1] SYSTEM-USER prompt · 2026-09-22 03:49:48 UTC

````


<pasted_content id="c653">
<system-prompt>
<design_philosophy>
You are building ONE web page whose only job is to let a reader understand a research paper faster
than they could by opening the PDF. Every decision on the page is judged against that.

WHAT "FASTER" MEANS HERE
- A reader who leaves after thirty seconds still knows the finding and the number behind it.
- A reader who stays five minutes has the method, the figures and the caveats, in that order.
- Nothing on the page is there because a layout had a slot for it.

ACCURACY IS THE HARD CONSTRAINT
Every number, name and claim comes from the paper as written — you read them out of the LaTeX
source and the run's own data files. You never change a number's precision, never restate a
comparison the paper did not make, and never invent a headline figure to fill a card. A page that
looks excellent and misreports one result is worse than no page, because the PDF beside it says
something else and a reader will find that out.

CRAFT, AND THE LOOK TO AVOID
The failure mode for a generated page is a look every reader now recognises on sight: a
purple-to-blue gradient banner, three identical cards with emoji headings, and body text set in
one weight at one size. Avoid all of it.
- Type carries the design. One system font stack, a real scale with visible jumps between levels
  rather than a creep of similar sizes, long-form text around 17-19px with a measure of 65-75
  characters and generous line height. Weight and size do the emphasis; colour rarely does.
- Colour is restrained. A light, near-white ground, one dark ink for text, one accent used for
  links and the current-section marker and almost nothing else. No gradients as decoration.
- Space does the work that borders and boxes would do badly. Sections separated by real vertical
  rhythm, cards defined by alignment and a single hairline rather than by shadow stacks.
- Structure over ornament: no emoji as section markers, no icon fonts, no badge clutter, no
  animated counters.
- Motion is a courtesy. A short transition on a lightbox or a hover state is welcome; anything
  that moves on scroll, autoplays, or delays the reader is not — and all of it stops under
  prefers-reduced-motion.
- Every interactive element works with a keyboard and says what it is to a screen reader. That is
  part of the craft, not a checklist bolted on at the end.

FINISH IT
The page is done when you have opened it in a browser, read it at a phone width and a desktop
width, tabbed through every control, and found nothing to fix. Not before.
</design_philosophy>

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
Your workspace: `/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/4_gen_paper_repo/_4_assemble_paper/paper`

CRITICAL: Every file you create, write, or save MUST be inside this workspace directory (subdirectories OK). You MUST NOT write files anywhere outside this path — external paths are READ-ONLY. Use absolute paths for all file operations.

EVERY file write MUST start with `/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/4_gen_paper_repo/_4_assemble_paper/paper/`:
GOOD: `/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/4_gen_paper_repo/_4_assemble_paper/paper/file.py`, `/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/4_gen_paper_repo/_4_assemble_paper/paper/results/out.json`
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
Build the paper's public web page: ONE self-contained `index.html` that lets a reader grasp
this paper faster than opening the PDF would. It is published as this run's GitHub Pages site, so
it is the first thing anyone sees.
</task>

<tool_use>
Maximize parallel tool calls. Parallelize independent operations, only sequentialize dependencies.
- Multiple searches/fetches on different topics → parallel in one turn
- Search then fetch results → sequential (need URLs first)
</tool_use>

<what_is_already_here>
Your workspace is the finished paper folder. It already holds everything the page is made of, and
you must not change any of it — you are adding one file, not revising the paper.

- `paper.tex` — the paper as it was actually written. This is the source of truth for
  every claim, name and NUMBER that goes on the page.
- `paper.pdf` — the compiled paper. The page must NOT link to it by this local name:
  the PDF is published on the code branch and the page on a different one. Link to it at the
  full URL below instead.
- `references.bib` — the bibliography, when the paper has one.
- `figures/` — every figure the paper uses, flattened into one folder.
- `workspace/` — the scratch folder the LaTeX task worked in. Ignore it.
</what_is_already_here>

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

  C12 shows a different pattern: 12 of 23 models exceed the null,
</pasted_content id="c653">


<pasted_content id="c653">
 more evenly distributed across the safety range (point-biserial = 0.29). C12's restricted rho within exceeders is 0.66.

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

  Table 5 shows the Qwen3-4B lineage, which includes a SafeRL variant, the standard instruct model, a community-edited "heretic" and an abliterated version. SafeRL is the safer checkpoint by S_2 (0.93 vs. 0.91 for Instruct), yet C2 ranks it lower (0.75 vs. 1.23): a boundary case for C2, not a win. A plausible explanation is that SafeRL was trained by reinforcement learning rather than direction-level safety editing
</pasted_content id="c653">


<pasted_content id="c653">
 (its reward signal derives from Qwen3Guard [Zhao et al., 2025b]), which may leave a smaller trace in an ablation-sensitivity read even though it yields a safer model. The logit gap reverses the C2 ordering (SafeRL 5.0 vs. Instruct 15.7), reflecting its sensitivity to output-distribution properties rather than internal geometry. The cross-fitted harm AUROC reaches 0.95 on Qwen3-4B (permutation p = 0.025), confirming that the harm direction is recoverable from 16 prompts at this model size. Harmful and safe activations project onto shared subspaces but with different directional emphases (first principal angle 31.1 degrees, max |cos| = 0.20 against a random-direction null 95th percentile of 0.42 and a positive-control value of 0.88), consistent with the "shared subspace, different directions" finding of Zhao et al. [2025].

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

  C2 correlates at rho = 0.51 [-0.04, 0.91] with harm-refusal rate (n = 23) and rho = 0.69 with OLB2 average (n = 8, descriptive, n < 10). The safety-capability relationship on this panel is negligible: rho(S_2, OLB2) = 0.24 [-0.55, 1.00] (n = 8), consistent with the pane
</pasted_content id="c653">


<pasted_content id="c653">
l's narrow size range and the absence of a general alignment tax at this scale.

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

  **The logit gap remains the floor.** The first-token logit gap (rho = 0.77) requires no internal access, costs one forward pass per prompt and fails 
</pasted_content id="c653">


<pasted_content id="c653">
only S3 (pole control) among the rules it is eligible for. Any internal metric must justify its additional complexity against this baseline. C2 significantly exceeds the logit gap (Delta rho = 0.13 [0.01, 0.41]), but C12 does not (Delta rho = -0.17 [-0.47, 0.19]). The logit gap is blind to TinyLlama (rho = 0.00), and C2's advantage there (rho = 1.00) is the strongest argument for internal reads.

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
Each line gives the path the PAGE must use, then the figure's title and caption. It is the same
path the file has on disk here: the publish s
</pasted_content id="c653">


<pasted_content id="c653">
tep copies the page and its figures into one folder,
so what works in this workspace is what works on the live site.

- figures/fig_overview_v0.jpg — "Pipeline Overview" (caption: "Overview of the cheap safety metric screening pipeline. Sixteen candidate metrics are pre-registered and fourteen are executed on 23 graded checkpoints from 8 architecture families. Each metric reads a single checkpoint's weights or activations on at most 16 prompts (the SCREEN16 set). Ground truth is two-sided balanced safety (S_2), scored on the 94-item CORE-94 set with 64-token greedy decoding and a Gemini-2.5-Flash stance judge. Six pre-registered selection rules filter candidates; one candidate (C12, twin d-prime) passes all six.")
- figures/fig_screen_scatter_v0.png [render from fig_screen_scatter_v0.pdf first] — "C2 Self-Ablation vs Balanced Safety" (caption: "Scatter plot of C2 (self-ablation sensitivity) versus balanced safety (S_2) for the 23 graded checkpoints. Points are coloured by architecture family. C2 achieves Spearman rho = 0.90 [0.79, 0.97]. The plot reveals a near-binary split: 10 of 23 models have |C2| > 0.1 (right cluster), while 13 cluster near zero. The dashed vertical line marks |C2| = 0.1.")
- figures/fig_grader_v0.png [render from fig_grader_v0.pdf first] — "Grader-Side Refusal Comparison" (caption: "Comparison of LLM judge behaviour under the StrongREJECT rubric versus stance-based framing on 1,040 paired items. The StrongREJECT rubric assigns the degenerate (1,1,1) tuple to 65.9 percent of harmful items. Of 395 discordant items, 328 are scored as refused by StrongREJECT but engaged by the stance framing, versus 67 in the opposite direction (McNemar p < 10^{-42}).")
- figures/fig_c12_scatter_v0.png [render from fig_c12_scatter_v0.pdf first] — "C12 Twin D-Prime vs Balanced Safety" (caption: "Scatter plot of C12 (twin d-prime) versus balanced safety (S_2) for the 23 graded checkpoints, coloured by architecture family. C12 is the sole candidate to pass all six pre-registered selection rules, with Spearman rho = 0.61 [0.36, 0.87]. Unlike C2, C12's values are more evenly distributed: 12 of 23 models exceed the random-direction null.")
</available_figures>

<figure_requirements>
- Reference every figure as `figures/` plus its filename, exactly as listed above.
  The publish step copies the page and its figures into one folder together, so that relative
  path is what resolves on the live site; anything else breaks once published.
- A browser cannot draw a PDF in an image element. Data figures are delivered as vector PDF for
  LaTeX's benefit, so for each one check whether a PNG of the same name already sits in
  `figures/`; if it does not, render one there at about 200 DPI with pdftoppm or
  pymupdf before referencing it. Renderable formats: .avif, .gif, .jpeg, .jpg, .png, .svg, .webp.
- Write those PNG files into `figures/` and nowhere else — that folder is published, a
  new folder of your own is not.
- Use each figure's own caption. Do not invent new ones, and do not describe a figure you did not
  place on the page.
- Look at every figure before you place it. A figure whose axis labels are unreadable at the size
  you give it is worse than no figure.
</figure_requirements>

<page_structure>
In this order, top to bottom:

1. HERO — the paper's title, the author line as the paper gives it, and a one-paragraph TL;DR in
   plain language: what was asked, what was found, and the single number that carries the finding.
   Not the abstract, and not a rewrite of it. Below it, two links: the PDF and the code
   repository, both at the exact URLs given in the links section below.
2. CONTRIBUTIONS — the paper's actual contributions as three to five scannable cards, each a short
   heading plus one or two sentences. If the paper claims four things, show four cards, not five.
3. METHOD — a walkthrough a technically literate non-specialist can follow: what goes in, what
   happens to it, what comes out, and why the design is the way it is. Lead with the paper's own
   method figure when it has one.
4. RESULTS — t
</pasted_content id="c653">


<pasted_content id="c653">
he paper's real headline numbers, read out of `paper.tex` and the data
   files behind it, each next to what it was measured on and what it is being compared against.
   A number that is not in the paper does not go on the page, and neither does a comparison the
   paper did not make. If a slot has no number, drop the slot.
5. FIGURE GALLERY — every figure, each with its caption, click-to-enlarge into a lightbox that
   closes on Escape, on a click outside, and on a visible close control.
6. LIMITATIONS — what the paper says it does not show. Verbatim in substance; do not soften it.
7. FOOTER — links to the PDF and the repository again, and the citation if the paper carries one.

A sticky section navigation runs alongside all of it and marks where the reader currently is.
</page_structure>

<technical_requirements>
- ONE file. All CSS in a style element, all JavaScript in a script element, both inline in
  `index.html`. No build step, no bundler, no framework, no external script, stylesheet, web
  font or analytics — nothing fetched at load time. The page must render with the network off,
  and the only files it may point at are the figures listed above and the PDF beside it.
- System font stack only, since no font may be downloaded.
- Light theme. Responsive from a 360px phone to a wide desktop, with no horizontal page scroll;
  wide content scrolls inside its own container.
- Honour prefers-reduced-motion: under it, transitions and any scroll-driven effect stop.
- Keyboard-navigable: every control reachable by Tab in a sensible order, a visible focus ring,
  the lightbox trapping focus while open and returning it to the thumbnail on close, and a skip
  link to the main content.
- Semantic HTML: one top-level heading, headings that descend without skipping, landmark elements,
  and alt text on every image that says what the figure shows rather than repeating its number.
- No emoji anywhere. No purple-to-blue gradients. No decorative icon fonts.
- Keep the whole file comfortably under a megabyte.
</technical_requirements>

<writing_register>
Write in the register of the field's best papers (the paper this page presents, which was written to them), not in the register of a language
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

<links>
Use these two URLs VERBATIM wherever the page links to the paper or the code. Do not shorten them,
do not turn either into a relative path, and do not compose one of your own.

- The paper PDF: https://cdn.jsdelivr.net/gh/ai-inventor-papers/ai-invention-87348a-cheap-safety-metrics-you-could-still@main/paper.pdf
- The code repository: https://github.com/ai-inventor-papers/ai-invention-87348a-cheap-safety-metrics-you-could-still

Both carry the branch this run publishes to. A link without it opens a DIFFERENT run's work —
it resolves and looks correct, which is why it must be copied rather than derived. They begin
resolving only after this run finishes publishing, so do NOT try to open or verify them.
</links>

FIRST, add ALL of these to your todo list using your task/todo-tracking tool:

CRITICAL: T
</pasted_content id="c653">


<pasted_content id="c653">
odo content must be copied exactly as is written here, with NO CHANGES. These todos are intentionally detailed so that another LLM could read each one without any external context and understand exactly what it has to do.

<todos>
TODO 1. Read and STRICTLY follow these skills: aii-web-tools.
TODO 2. Read `paper.tex` end to end and list `figures/`. Write down the
paper's title, its author line, its contributions, and every headline number together with the
sentence it appears in — those sentences are the only numbers allowed on the page. Note which
figures are PDFs and so need a PNG rendered.
TODO 3. Render a PNG at about 200 DPI, into `figures/`, for every figure not already
in a browser-renderable format, then LOOK at each image you plan to use so you know what it shows
and how large it has to be on the page to stay legible.
TODO 4. Write `index.html` following the page_structure and technical_requirements sections
above: one file, inline CSS and JavaScript, every image referenced through the published figure
prefix.
TODO 5. VERIFY THE NUMBERS: for each number on the page, grep `paper.tex` for it and
confirm it appears there with the same meaning. Delete any number you cannot find. Then confirm
every claim on the page is one the paper actually makes.
TODO 6. VERIFY THE PAGE: confirm `index.html` has no external script, stylesheet or font
reference; that every image path starts with the published figure prefix and names a file that
exists in `figures/`; and that the PDF and repository links are character-for-
character the two URLs given in the links section, not `paper.pdf` and not any URL you
composed. Then open the page in a browser, screenshot it at a phone width and a desktop width,
read both screenshots, and fix anything cramped, overlapping or cut off.
TODO 7. ACCESSIBILITY PASS: tab through the whole page and confirm every control is reachable with a
visible focus ring, the lightbox traps focus and closes on Escape, headings descend without
skipping, and every image has alt text. Fix what fails.
</todos>

---

Output the result as JSON to: `./.terminal_claude_agent_struct_out.json`

JSON Schema:
```json
{
  "$defs": {
    "PaperSiteExpectedFiles": {
      "description": "All expected output files from paper-site generation.",
      "properties": {
        "site_html_path": {
          "description": "Path to the single self-contained HTML page. Example: 'index.html'",
          "title": "Site Html Path",
          "type": "string"
        }
      },
      "required": [
        "site_html_path"
      ],
      "title": "PaperSiteExpectedFiles",
      "type": "object"
    }
  },
  "description": "Paper site \u2014 structured output from presentation-page generation.",
  "properties": {
    "summary": {
      "description": "Brief summary of the page you built: the sections it carries, which figures it shows, which numbers it quotes and where each came from in the paper.",
      "maxLength": 5000,
      "minLength": 300,
      "title": "Summary",
      "type": "string"
    },
    "out_expected_files": {
      "$ref": "#/$defs/PaperSiteExpectedFiles",
      "description": "All output files you created. Must include index.html."
    }
  },
  "required": [
    "summary",
    "out_expected_files"
  ],
  "title": "PaperSite",
  "type": "object"
}
```

IMPORTANT: this task is NOT complete until `./.terminal_claude_agent_struct_out.json` exists and contains JSON matching the schema above.

qwen3 on huggingface has base model also official safety finetuned version and there is a community finetuned uncensored model called abliterated. take these models and do a mech interp analysis of how they differ in activation. also find some patterns in internal computation on safety prompts. and possibly create a new metric for safety. so that for any random model on huggingface you would not need to run the full benchmarks, but only this metric on 0- to few prompts and get a safety evaluation

i want cheap safety metrics that work on a single model. no parent, no reference model, no
attested base to diff against - assume i found so
</pasted_content id="c653">


<pasted_content id="c653">
me random model on huggingface and i have
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
</pasted_content id="c653">
````

### [2] SKILL-INPUT — aii-web-tools · 2026-09-22 03:50:00 UTC

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

### [3] SYSTEM-USER prompt · 2026-09-22 03:51:21 UTC

```
[Image: original 2752x1536, displayed at 2000x1116. Multiply coordinates by 1.38 to map to original image.]
```

### [4] SYSTEM-USER prompt · 2026-09-22 03:53:01 UTC

```

Write a single self-contained `index.html` file at:
`/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/4_gen_paper_repo/_4_assemble_paper/paper/index.html`

This is a public web page for a research paper. It must let a reader understand the paper faster than opening the PDF. ALL CSS and JS are inline. No external scripts, stylesheets, fonts, or analytics. System font stack only. Light theme. Must render with network off.

## PAPER METADATA

**Title:** Pre-Registered Screening of Internal Safety Metrics for Language Model Checkpoints
**Author line:** Anonymous
**PDF URL (use verbatim):** https://cdn.jsdelivr.net/gh/ai-inventor-papers/ai-invention-87348a-cheap-safety-metrics-you-could-still@main/paper.pdf
**Code URL (use verbatim):** https://github.com/ai-inventor-papers/ai-invention-87348a-cheap-safety-metrics-you-could-still

## TL;DR (for the hero, in plain language, NOT the abstract)

Open-weight language models proliferate faster than anyone can evaluate them for safety. We asked whether a metric computable from a single checkpoint, using at most 16 prompts and no text generation, could rank models by safety without running a full benchmark. We screened 14 candidate internal metrics on 23 chat models from 8 architecture families against a two-sided safety score that penalises both harmful compliance and over-refusal. Under six selection rules frozen before scoring, one candidate passed: twin d-prime (C12), which measures how well a model's mid-layer activations separate harmful from safe prompts, with Spearman rho = 0.61 against balanced safety. The strongest raw correlation belonged to self-ablation sensitivity (C2, rho = 0.90), but no internal metric added significant information beyond generating and judging just 16 completions.

## PAGE STRUCTURE (in this exact order, top to bottom)

### 1. HERO
- Paper title, author line "Anonymous", the TL;DR above
- Two links below: "Read the Paper (PDF)" and "Code Repository" using the exact URLs above
- Do NOT link to paper.pdf locally

### 2. CONTRIBUTIONS (5 cards)

Card 1: "The Screen"
14 of 16 registered candidate metrics executed on 23 graded checkpoints from 8 architecture families. Under six selection rules, one candidate passes all six: twin d-prime (C12, rho = 0.61 [0.36, 0.87]). Self-ablation sensitivity (C2, rho = 0.90) clears amended rules, but its three surviving variants (C2, C2n, C17) are monotone transforms of one measurement.

Card 2: "Two-Sided Ground Truth"
23 checkpoints scored on the 94-item CORE-94 set (66 harmful, 28 XSTest-safe) with 64-token greedy decoding and a Gemini-2.5-Flash stance judge. A secondary judge (GPT-5-mini) agrees at kappa = 0.72. A blanket refuser scores S_2 = 0.5, not 1.0.

Card 3: "AMS Incumbent Comparison"
Every variant of the published AMS metric correlates worse than C2 with two-sided safety, with paired confidence intervals excluding zero. The reference implementation (ams-scanner 0.1.3) contains a right-padding bug that reads PAD-token activations.

Card 4: "Content-Free Pull Control"
After subtracting a norm-matched random steer from C1, the corrected metric (C1n) correlates at rho = 0.76, essentially unchanged (rho(C1, C1n) = 0.995), refuting the hypothesis that C1's signal is a content-free pull toward refusal.

Card 5: "Grader-Side Refusal"
LLM judges under the StrongREJECT rubric assign the degenerate score tuple (1,1,1) to 65.9% of harmful items, with 328 vs. 67 discordant items against a stance-based framing (McNemar p &lt; 10^-42).

### 3. METHOD
Lead with the pipeline overview figure (figures/fig_overview_v0.jpg).
Explain: 
- Two-sided ground truth: S_2 = 0.5 * (harm-refusal rate) + 0.5 * (benign-compliance rate) on CORE-94 (66 harmful + 28 XSTest-safe items). Blanket refuser scores 0.5.
- Panel: 36 checkpoints from 8 families (Qwen3, Qwen2.5, TinyLlama, Llama-3.2, OLMo-2, SmolLM2, Falcon3, Danube3), 23 graded, all at most 4B parameters in bf16.
- 16 candidate metrics in 7 families, each reading hidden states or weights on at most 16 prompts (SCREEN16). Logit-gap and refusal-mass baselines enter as bars, not survivors.
- Six selection rules: S1 incremental signal, S2 direction specificity, S3 pole control, S4 sign agreement, S5 efficiency, S6 beyond confounds.

### 4. RESULTS
Include these headline numbers (each from paper.tex):

**The sole survivor:**
- C12 (twin d-prime): rho = 0.61 [0.36, 0.87], partial rho = 0.43 (one-sided bound 0.006)
- C12 significant within Qwen3 (rho = 0.67, n=8) and Qwen2.5 (rho = 0.70, n=5), not TinyLlama (rho = -0.10, n=5)

**The strongest correlation:**
- C2 (self-ablation): rho = 0.90 [0.79, 0.97]
- C2 exceeds logit gap by 0.128 [0.012, 0.410]
- C2 detects models with ablatable harm direction at AUROC = 0.96
- Within 10 models exceeding null, restricted rho = 0.64

**AMS comparison (show as compact table):**
- AMS_published rho = 0.28, vs C2: -0.62 [-1.01, -0.25]
- AMS_mean3 rho = 0.50, vs C2: -0.40 [-0.68, -0.07]
- AMS_cf_layer rho = 0.33, vs C2: -0.57 [-0.83, -0.17]
- AMS_cf_sweep rho = 0.21, vs C2: -0.69 [-1.05, -0.33]
- AMS_screen16 rho = 0.48, vs C2: -0.42 [-0.66, -0.14]

**The ceiling:** 16 judged completions achieves rho = 0.93 with the full CORE-94 target. No internal metric adds significant information beyond this. Practical advantage: internal read takes ~16 seconds per 4B model, no judge needed.

**Logit gap as floor:** rho = 0.77, requires no internal access, fails only S3 (pole control).

Include figures/fig_c12_scatter_v0.png and figures/fig_screen_scatter_v0.png in the results section with their captions (given below).

### 5. FIGURE GALLERY
All four figures with click-to-enlarge lightbox. Lightbox closes on Escape, click outside, or visible close button. Each with its caption:

1. figures/fig_overview_v0.jpg — "Pipeline Overview" — Caption: "Overview of the cheap safety metric screening pipeline. Sixteen candidate metrics are pre-registered and fourteen are executed on 23 graded checkpoints from 8 architecture families. Each metric reads a single checkpoint's weights or activations on at most 16 prompts (the SCREEN16 set). Ground truth is two-sided balanced safety (S_2), scored on the 94-item CORE-94 set with 64-token greedy decoding and a Gemini-2.5-Flash stance judge. Six selection rules filter candidates; one candidate (C12, twin d-prime) passes all six."

2. figures/fig_c12_scatter_v0.png — "C12 Twin D-Prime vs Balanced Safety" — Caption: "Scatter plot of C12 (twin d-prime) versus balanced safety (S_2) for the 23 graded checkpoints, coloured by architecture family. C12 is the sole candidate to pass all six selection rules, with Spearman rho = 0.61 [0.36, 0.87]. Unlike C2, C12's values are more evenly distributed: 12 of 23 models exceed the random-direction null."

3. figures/fig_screen_scatter_v0.png — "C2 Self-Ablation vs Balanced Safety" — Caption: "Scatter plot of C2 (self-ablation sensitivity) versus balanced safety (S_2) for the 23 graded checkpoints. Points are coloured by architecture family. C2 achieves Spearman rho = 0.90 [0.79, 0.97]. The plot reveals a near-binary split: 10 of 23 models have |C2| > 0.1 (right cluster), while 13 cluster near zero. The dashed vertical line marks |C2| = 0.1."

4. figures/fig_grader_v0.png — "Grader-Side Refusal Comparison" — Caption: "Comparison of LLM judge behaviour under the StrongREJECT rubric versus stance-based framing on 1,040 paired items. The StrongREJECT rubric assigns the degenerate (1,1,1) tuple to 65.9 percent of harmful items. Of 395 discordant items, 328 are scored as refused by StrongREJECT but engaged by the stance framing, versus 67 in the opposite direction (McNemar p &lt; 10^-42)."

### 6. LIMITATIONS (verbatim in substance from the paper)
- Panel covers only models at or below 4B parameters. Generalisability to larger or proprietary models is unknown.
- Prompt set limited to English single-turn interactions; multi-turn and multilingual safety not tested.
- C4 and C5 (direction-conditioned weight paths) were not executed.
- ROSI reversal tested on one checkpoint at 128 tokens and two at 20 tokens.
- Confirmation test on blind Set A checkpoints has not been run: no safety labels exist for the frozen Set A models.
- The 16-prompt judged behavioural probe (rho = 0.93) remains the ceiling. No internal metric adds significant predictive power beyond generating and judging 16 completions.
- Standard safety benchmarks (TrustLLM, AIR-Bench, HELM-Safety) have zero coverage on this panel.

### 7. FOOTER
- Links to PDF and repository again (same exact URLs)
- No citation needed (anonymous paper)

## DESIGN REQUIREMENTS

- **Type:** System font stack: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif. Long-form text 17-19px, measure 65-75ch, generous line height (1.6-1.7). Real scale with visible jumps between heading levels. Weight and size for emphasis, color rarely.
- **Color:** Light near-white ground (#fafafa or similar). One dark ink for text (#1a1a1a or similar). ONE accent color for links and section marker (a muted blue like #2563eb or teal). No gradients as decoration.
- **Space:** Sections separated by vertical rhythm, not borders/boxes. Cards defined by alignment and a single hairline, not shadow stacks.
- **No emoji anywhere.** No icon fonts. No badge clutter. No animated counters. No purple-to-blue gradients.
- **Sticky section navigation** on the side (desktop) or top (mobile) that marks the current section.
- **Lightbox** for figure gallery: click to enlarge, close on Escape/click-outside/close-button, focus trapped while open, focus returns to thumbnail on close.
- **Motion:** Short transitions on hover/lightbox only. All stops under prefers-reduced-motion.
- **Responsive:** Works from 360px phone to wide desktop. No horizontal page scroll. Wide content (tables) scrolls inside its own container.
- **Accessibility:** Skip link to main content. Every control reachable by Tab with visible focus ring. Semantic HTML: one h1 (title), headings descend without skipping. Alt text on every image describing what the figure shows. Landmark elements (nav, main, footer).
- **File size:** Well under 1 MB total.

## WRITING REGISTER
- Never use: delve, underscore, showcase, intricate, pivotal, realm, commendable, meticulous, tapestry, garner, multifaceted, "it is worth noting", "plays a crucial role", "not only ... but also"
- At most 3 em dashes per 1000 words
- Mix short and long sentences
- State what the evidence supports plainly; hedge only where evidence is thin
- No emoji

## CRITICAL CONSTRAINTS
- Every number must come from the paper. Do not invent numbers.
- Do not change any number's precision.
- Do not make comparisons the paper does not make.
- Image paths must be exactly: figures/fig_overview_v0.jpg, figures/fig_c12_scatter_v0.png, figures/fig_screen_scatter_v0.png, figures/fig_grader_v0.png
- PDF link must be exactly: https://cdn.jsdelivr.net/gh/ai-inventor-papers/ai-invention-87348a-cheap-safety-metrics-you-could-still@main/paper.pdf
- Code link must be exactly: https://github.com/ai-inventor-papers/ai-invention-87348a-cheap-safety-metrics-you-could-still
- Use HTML entities for special chars: rho as "&#961;" or just spell out "rho", kappa as "&#954;" or spell out. Use subscript tags for S&#8322; etc.

Write the COMPLETE file. No placeholders, no stubs, no incomplete code.
```

### [5] SYSTEM-USER prompt · 2026-09-22 03:53:05 UTC

```
<validation-feedback>
Attempt 1 failed validation.

The output file `.terminal_claude_agent_struct_out.json` does not exist yet. Produce it as JSON matching the schema.

Produce `.terminal_claude_agent_struct_out.json` again so it contains corrected JSON that matches the schema. Do not invent new fields.
</validation-feedback>
```

### [6] SYSTEM-USER prompt · 2026-09-22 03:58:16 UTC

```
[Image: original 1280x8089, displayed at 316x2000. Multiply coordinates by 4.05 to map to original image.]
```

### [7] SYSTEM-USER prompt · 2026-09-22 03:58:22 UTC

```
[Image: original 452x10257, displayed at 88x2000. Multiply coordinates by 5.14 to map to original image.]
```

### [8] SYSTEM-USER prompt · 2026-09-22 04:00:29 UTC

```
SITE VERIFICATION FAILED: 1 problem(s) in index.html.

- image source '' does not start with 'figures/', so it will not resolve once the page is published beside its figures folder

You MUST:
1. Fix every problem listed above in index.html.
2. Keep the page ONE self-contained file — all CSS and JavaScript inline, no external scripts, stylesheets or web fonts, nothing fetched at load time.
3. Point every image at figures/<filename>, where <filename> is a browser-renderable image that really exists in your figures/ folder. A vector PDF figure needs a PNG rendered beside it first; reference the PNG.
4. Re-open the page and confirm it still renders before finishing.
```
