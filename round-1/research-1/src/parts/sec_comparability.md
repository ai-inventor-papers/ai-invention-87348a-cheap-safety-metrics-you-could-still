## E. THE COMPARABILITY TABLE

One row per incumbent. **Any cell that the source does not state carries the literal string `UNSTATED-IN-SOURCE`; none is a guess.** This is the table a reviewer checks first.

| | **AMS** 2608.05578 | **Skin-Deep / GFS** 2606.22676 | **N-GLARE** 2511.14195 | **RAS / SafeVec** 2606.25750 |
|---|---|---|---|---|
| **bar name** | LOOCV 4-class accuracy; `sigma` vs compliance | GFS→post-LoRA refusal retention | JSS rank agreement with red-team rankings | RAS separation of aligned vs uncensored/abliterated |
| **published value** | **71 % (10/14)**; **r = −0.546** (p = 0.043), **rho = −0.423** (p = 0.13, n.s.) | **NONE PRINTED** — qualitative co-occurrence only | "less than 1% token and runtime cost"; **no numeric tau printed for the headline claim** (see §D) | qualitative separation; no cross-family coefficient in the text read |
| **task** | 4-way: instruct / base / abliterated / uncensored-FT | rank aligned models by post-fine-tuning refusal retention | rank models by red-team safety | rank/score aligned vs uncensored vs abliterated within a family |
| **n** | 14 model configurations | **7** models in the retention analysis (21 in the paper overall) | **40+** models × 20 red-team strategies, 7000+ test cases | 3 families; Table 1 lists 5 Llama-lineage rows |
| **unit of resampling** | model (for LOOCV and both correlations); contrastive pair (for the sigma CIs) | per-model; **no resampling/CI reported for GFS itself** | UNSTATED-IN-SOURCE | model; no resampling reported |
| **what was held out** | **only the classification threshold** | 20 % probe split; 3 unseen models; 50 unseen harmful prompts | UNSTATED-IN-SOURCE | **nothing** — window, directions and calibration constants all fitted on the reported models |
| **parent-free?** | **YES** (Tier 1); Tier 2 needs a stored baseline | **NO** — Eq 1 needs the base model's covariance | **YES** — benign manifold built from the model's own activations | **NO** — needs a reference model *and* calibration models *and* their measured ASR |
| **prompts needed** | 96 (32 per concept × 3) | **1000** (500 harmful + 500 benign) | **four probing conditions** {B,J,R,P}; 7000+ test cases; per-condition n UNSTATED | three prompt sets (`S`, `U`, `J`); sizes UNSTATED-IN-SOURCE |
| **generation?** | **NO** for the statistic (yes, separately, for its own compliance measurement) | **NO** | **NO** (that is its selling point) | **NO** |
| **public code** | **YES** — Apache-2.0, PyPI `ams-scanner` | **YES** — MIT, `js-lee-AI/skin-deep` | **none found** (2 searches) | none found |
| **our matched protocol** | parent-free, leave-one-**lineage**-out | parent-free, few-prompt | parent-free, few-prompt | parent-free, no calibration ASR |
| **comparable?** | **NO** | **NO** | **NO** | **NO** |
| **if not, why** | their LOO held out only the threshold, so ours is **stricter**; label NON-MATCHED, not a win | **no quantitative predictive statistic exists to compare against** | no code + a four-condition protocol our access model does not grant; classify-by-functional-form-only | strictly richer access class; and its separations are in-sample |

**How to read this table honestly.** Four "no"s in a row looks evasive unless the reasons differ, and they do: AMS is *looser* than us on held-out strictness; GFS has *no number*; N-GLARE is *unreimplementable* under our access model; RAS is *richer* in what it is allowed to assume. Note that N-GLARE is the one incumbent that is genuinely parent-free and generation-free like us — it is separated from the deliverable on the **prompt-budget axis alone**, which makes it the incumbent whose scope distinction is thinnest and therefore the one to state most carefully. Three of those four are arguments in our favour and one (AMS) is an argument we must be careful with — 71 % is easier than what we are attempting, so beating it is necessary, not sufficient.

**What we can nevertheless compare directly.** AMS is installable, so it runs on *our* panel under *our* leave-one-lineage-out protocol. That converts the AMS row from a cross-study comparison into a **same-panel, same-protocol head-to-head** — the only genuinely matched comparison available in this table, and the one the screen executor should build the results table around.
