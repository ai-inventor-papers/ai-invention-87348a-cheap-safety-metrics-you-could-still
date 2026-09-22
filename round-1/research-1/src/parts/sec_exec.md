# Turning three rival methods into bars — and finding a fourth

**Artifact:** `gen_plan_research_1_idx1` · web-only · searched and verified **2026-09-20** · all eleven planned targets reachable (HTTP 200 on `abs` for every one; no substitutions, no fabricated locators).

## A. EXECUTIVE ANSWER

**The one-line result.** All three commissioned incumbents were converted from related-work entries into implementation-grade specs with a named access class and a bar row — **two of the three turned out to be in a different access class than the deliverable, one of them has no printed number to be a bar at all, and a fourth incumbent that the plan did not know about (RAS / SafeVec, arXiv 2606.25750) is the closest published thing to what we are building.** Separately, the strongest incumbent (AMS) is not merely reproducible but `pip`-installable, which converts it from an argument into a table row this week.

### A.1 The three bar rows (plus the fourth)

| incumbent | published value | what was held out | access class | comparable? |
|---|---|---|---|---|
| **AMS** 2608.05578 (IEEE Access 14:91723–91737) | **71 % (10/14)** LOOCV; `sigma_harmful` vs compliance **r = −0.546, p = 0.043** (Spearman **rho = −0.423, p = 0.13 n.s.**) | **only the threshold** | parent-free (Tier 1), 96 prompts, no generation | **NO — loose bar, non-matched** (D6) |
| **Skin-Deep / GFS** 2606.22676 | **no coefficient printed**; qualitative co-occurrence at **n = 7** | 20 % probe split; 3-model LoRA hold-out | **parent-REQUIRED** (base-model covariance, Eq 1) + **1000 prompts** | **NO — no quantitative statistic exists** |
| **N-GLARE** 2511.14195 / ACL 2026 Long 1334 | "less than 1% token and runtime cost"; **no numeric tau for the headline claim** | UNSTATED-IN-SOURCE | **parent-free and generation-free**, but needs **four probing conditions** {B,J,R,P} over 7000+ cases | **NO — classify-by-functional-form** |
| **RAS / SafeVec** 2606.25750 *(not in the plan)* | 210–217× faster than judge-based; separation reported in-sample | **nothing** | **parent-REQUIRED + calibration models + their measured ASR + per-family calibration** | **NO — richer access class** |

**Read the right-hand column before anything else.** Every incumbent is `comparable: false`, and in each case for a *different, nameable* reason. That is not an evasion — it is the finding. The deliverable's slot is defended not by being better at the same task but by sitting one or two access axes away from every occupant: **parent-free × few-prompt × cross-lineage-held-out**. What has been missing from this run is that the reasons were never written down. They are now, one row each, and each one is checkable.

### A.2 The five candidate verdicts

| id | verdict | nearest paper | surviving margin |
|---|---|---|---|
| **C1** per-checkpoint harm×refusal coupling | **PARTIAL** | 2606.16349 `HRCI_repr` | PER-CHECKPOINT ∧ CROSS-FITTED ∧ DISCRIMINATOR-NOT-PREDICTOR |
| **C2** prompt-budget crossover | **PARTIAL** | 2608.13329 | the CROSSOVER POINT ITSELF at matched budget |
| **C3** refusal-depth − content-depth | **OPEN** (aggregation only) | 2609.00760 | PER-CHECKPOINT ∧ DIFFERENCE-OF-DEPTHS ∧ CORRELATED |
| **C4** parent-free graded edit strength | **OPEN** (four-way conjunction) | 2607.01854 | WEIGHTS-ONLY ∧ PARENT-FREE ∧ GRADED ∧ PREDICTS-COMPLIANCE |
| **C5** hidden-state metamodel vs lineage probe | **OPEN** (on the ablation) | 2608.14929 | SAME-FEATURES ∧ HELD-OUT-LINEAGE ∧ ABLATED-AGAINST-IDENTITY |

**C4 is worth the most and C1 is at most risk.** C4's three neighbouring sub-problems are each closed — binary parent-free detection (Jorak), parent-anchored detection (2607.01854 at AUROC 0.95, which "presumes an attested reference"), and graded *activation*-vs-compliance (AMS) — leaving a genuinely unoccupied conjunction. C1's nearest paper is parent-free, single-checkpoint and interaction-flavoured, and its authors already published the negative: **"Thus low coupling is not a safety score."**

### A.3 The five load-bearing numbers

| id | verdict | what changes |
|---|---|---|
| **N1** 2507.11878 | **CONFIRMED** | the motivating sentence is false as written; rewrite to per-PROMPT vs per-CHECKPOINT (D1) |
| **N2** 2603.05773 | **CONFIRMED** | report Qwen-held-out separately; write the Qwen anchor up as a stated risk (D2) |
| **N3** 2609.14759 | **CONFIRMED** | spend no metrics on higher-rank refusal subspaces (D3) |
| **N4** 2604.18901 | **AMBIGUOUS-MULTIPLE-OCCURRENCES** | **both readings of both numbers are genuinely true** — no correction needed; name which reading you cite (D4) |
| **N5** 2606.16349 | **CONFIRMED** | pre-register C1 as a discriminator only (D5) |

**Nothing the hypothesis leans on turned out to be a misattribution.** N4 was the high-risk item and the pre-committed procedure — grep the whole PDF, report every occurrence before declaring anything wrong — showed that the two "conflicting" readings are two distinct true findings that happen to share digits. A third, unrelated 73.4° also exists and is neither.

### A.4 The three things that most change what iteration 2 does

1. **Run AMS, do not argue with it.** `pip install "ams-scanner[cli]"; ams scan <model>` — Apache-2.0, 10–40 s per model on an A100/L4, parent-free at Tier 1. The screen executor can fill the strongest incumbent's bar row on day one. This removes the single largest score blocker identified by the iteration-3 review.
2. **Size the success criteria off the incumbent, not off hope.** AMS's own numbers say the realistic target is **|r| ≈ 0.5 at model-level n with a rank test that may not clear**, and that its statistic carries a **median bootstrap 95 % CI width of 3.36 sigma against a 2.0–3.5 decision band** — 62 % of its cells cannot be resolved against its own PASS threshold at 16 pairs. Pre-commit to reporting both Pearson and Spearman, and to a prompt-count power check (D8, D9).
3. **The few-prompt cross-family framing does not survive the measurement-design literature as stated.** arXiv:2608.13329 reports a generalizability coefficient of **0.00002** for cross-family comparison of an internal readout on a single prompt rendering. Either vary the rendering by design or concede it in the abstract (D11).

### A.5 The decisions ledger — every one names an artifact and an action

Full text (question, answer, evidence, action) is in `spec_table.json` under `decisions`.

| id | decision | who acts |
|---|---|---|
| **D1** | Motivating sentence is false as written; rescope to per-PROMPT vs per-CHECKPOINT | paper + screen |
| **D2** | Report Qwen held out separately, never pooled; write the Qwen anchor up as a stated risk | screen + paper |
| **D3** | Spend no metrics on higher-rank refusal subspaces; quote the rank-1 saturation as the reason | screen |
| **D4** | Both readings of both numbers are true; name which reading you cite, and add LatentBiopsy | all artifacts |
| **D5** | Pre-register C1 as a DISCRIMINATOR ONLY, and make it beat HRCI_repr | screen + paper |
| **D6** | 71% is a LOOSE, NON-MATCHED bar; label it, do not present it as a win or loss | screen |
| **D7** | Run AMS on every panel checkpoint via the public package, using its exact prompt pairs | screen |
| **D8** | Size success at |r|~0.5 at model-level n; report BOTH Pearson and Spearman, pre-committed | screen |
| **D9** | Run a prompt-count power check; the incumbent's own CI width makes the point for us | screen |
| **D10** | Add RAS to related work in the FIRST draft with its access-class distinction in one sentence | paper + screen + payoff |
| **D11** | Vary the prompt rendering by design, or concede the 0.00002 generalizability result in the abstract | screen |
| **D12** | Give C4 the largest share of the shared harvest's analysis budget | screen |
