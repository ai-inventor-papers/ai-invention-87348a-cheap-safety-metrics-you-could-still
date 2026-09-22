## F2. THE ADVERSARIAL PASS — a deliberate attempt to kill the three OPEN verdicts

Three OPEN verdicts out of five is, by this field's measured base rate, weak evidence that the queries were too narrow rather than strong evidence that the field is empty. So an independent pass was commissioned whose *only* instruction was to refute C3, C4 and C5 — with finding a scoop counted as a success, not a failure. **39 further query formulations were run across the three.** All three survived, but two of the three were materially narrowed and one had its novelty framing downgraded.

| id | after attack | queries | what changed |
|---|---|---|---|
| C3 | **STILL-OPEN** (medium) | 15 | margin narrowed — both required curves already coexist in one paper, on the same models |
| C4 | **STILL-OPEN** (medium) | 12 | margin held; three further near-misses named |
| C5 | **STILL-OPEN** (medium) | 12 (+6 independent) | **novelty framing downgraded** — the ablation as a method is established prior art |

**A process note, and an accidental replication.** When nudged for partial results mid-run, the delegated pass reported C5 as not yet attacked (zero queries, self-labelled `STILL-OPEN-INSUFFICIENTLY-ATTACKED`). Rather than let an untested verdict stand as if it had been tested, the coordinator ran a separate six-query attack on C5. The delegated pass then finished and attacked C5 properly with twelve of its own. **The two independent searches converged on the same strongest counterexample (arXiv 2606.02907)**, which is a better outcome than either alone: a nearest paper found twice by two disjoint query sets is more likely to be *the* nearest paper. Both query sets are recorded in `spec_table.json`.

### C3 — survives, but the margin is thinner than section F claimed

The strongest counterexample is **arXiv 2507.11878** — the *same paper* as N1:

> "This suggests that the harmfulness direction represents the concept of harmfulness that LLMs can internally reason about before generating their responses, while the refusal direction may reflect more explicit, surface-level refusal signals."

**Both curves C3 needs already coexist in one paper, on the same models, and that paper already states that harmfulness precedes refusal.** What it never does: collapse either curve to a single onset-layer index, subtract two such indices, produce a per-checkpoint scalar, or correlate it across models.

**Revised margin, stated at its true strength:** C3's novelty is now only the three mechanical steps — *collapse each curve to an onset index, subtract, correlate across checkpoints*. That is an aggregation contribution on top of a published qualitative ordering. It should be written up as such; framing C3 as "we discovered refusal forms after content" would be false.

### C4 — survives, margin held, three further near-misses named

Newly surfaced and checked, none disqualifying:
- **Failure-First Report 74** (2026-03-11) correlates a *behavioural* "abliteration resistance" against jailbreak resistance using OBLITERATUS telemetry — but over **known, executed** abliteration runs where the technique and base model are the experimenter's own, not blind weight recovery.
- **arXiv 2512.13655** compares four abliteration tools (Heretic, DECCP, ErisForge, FailSpy) across 16 models on **capability** metrics (GSM8K delta, KL divergence) — capability collapse, not harmful compliance, and no reference-free strength recovery.
- The **Alice April-2026 activation-space abliteration report** was grepped for dose/strength-vs-ASR and without-base language: **zero matches**.

**Revised wording for the paper, adopted:** state explicitly that (i) parent-dependent *graded* diagnostics exist (Skin-Deep 2606.22676, WeightWatch 2508.00161); (ii) reference-free but *label-only* detectors exist (Jorak; the AUROC-0.95 two-signal audit, whose stronger signal "presumes an attested reference"); (iii) *behavioural* abliteration-dose-vs-jailbreak correlations exist but over known executed runs. **The unclaimed cell is blind graded weight-space recovery — no parent, no execution log — regressed against continuous harmful compliance.**

One honest qualifier the attack surfaced: a practitioner wiki independently flags this exact cell as the hardest open problem. That **raises** confidence the gap is real, but it also means the framing is *"a known open problem in a practitioner community"*, not undiscovered territory. **Cite the wiki to pre-empt a reviewer finding it first** — this run has been penalised before for conceding priority late rather than early.

### C5 — survives on the axis, but the ablation is not ours to claim as an idea

The strongest counterexample is **arXiv 2606.02907** (TrustNLP @ ACL 2026):

> "However, this separation is entirely driven by format confounds. Residualizing source identity, option count, and response length reduces accuracy to chance."

That is **exactly C5's ablation pattern** — a hidden-state probe at 100 % accuracy collapsing to chance once an identity variable is residualised out — and the paper explicitly frames it as "motivating routine format deconfounding in mechanistic interpretability". It fails C5's conjuncts only because it operates on a **per-prompt / per-task-type** axis (the benchmark item's source identity), on a single model (Qwen3-14B), and predicts a reasoning *type* rather than a model's benchmark *score*. Behind it stands **Hewitt & Liang's control tasks** (EMNLP 2019), the canonical ancestor of the whole move, and an adjacent weight-space-learning literature — accuracy predictable from weights on CNN zoos (arXiv 2002.11448), and generalisation across heterogeneous zoos (arXiv 2504.10141) — which asks a related question without running the identity ablation.

**Revised framing, binding on the write-up:** the verdict stays OPEN, but the contribution is *"we ran the established control on the per-model / per-lineage axis, where nobody had"* — **not** *"we invented the control"*. Claimed at that strength it is still worth doing, arguably more so: a well-known control that nobody has applied in a given setting is exactly the kind of gap a reviewer respects. Claimed as a novel method, it will be marked down.
