## D. INCUMBENT 3 — N-GLARE, arXiv 2511.14195 / ACL 2026 Long 1334

"N-GLARE: A Non-Generative Latent Representation-Efficient LLM Safety Evaluator", Lin et al. (arXiv v2, 8 Jan 2026). **The ACL Anthology version of record is live** at https://aclanthology.org/2026.acl-long.1334.pdf and was grepped alongside the arXiv PDF. **No public code found** (two named searches, both negative — consistent with prior recon).

### D.1 The construction, with both equations confirmed verbatim

- **Eq 7 (JSS):** `JSS(A,B) = (1/|G|) Σ_G [ (1/I) Σ_i JS_i^(G)(A,B) ]` — a Jensen–Shannon divergence between the angular-probabilistic-trajectory (APT) distributions of two probing conditions, averaged over slices `i` within layer groups `G`.
- **Eq 9:** `JR Min/Max = min_s JSS_s(J,R) / max_s JSS_s(J,R)` over the arc-length-standardised progress axis `s`.

Both equation *numbers* and both *forms* are confirmed — the prior recon was right on both counts.

**Layer grouping:** three groups, {lower, middle, upper}. The boundary rule beyond that is **UNSTATED-IN-SOURCE**, as is the slice count `I`.

### D.2 What it needs — the scope distinction, measured rather than assumed

**It IS parent-free and it IS non-generative.** The benign manifold is built from the same model's own activations; a single forward pass, no generation. On those two axes N-GLARE is closer to our deliverable than either GFS or RAS.

**But it is not a 0-or-few-prompt method.** It requires **four probing conditions** — "We define the probing condition A ∈{B, J, R, P} to correspond to four interaction history types":

- **Benign (B)** — "Standard task instructions conforming to natural distributions, used to fit the benign reference manifold."
- **Jailbreak (J)** — "Adversarial sequences designed to induce harmful outputs."
- **Ideal Refusal (R)** — "Identical to J in user content (retaining harmful intent) but forcing the assistant response to a policy-compliant refusal template. This represents the model's ideal defensive state against attacks."
- **Plain Query (P)** — "Direct presentation of harmful intent (without disguise) to capture the model's unconstrained internal" response.

("Baseline" and "Benign" are used interchangeably in the paper.) Note that condition **R requires a forced assistant prefix**, i.e. a teacher-forced continuation the evaluator writes — so N-GLARE is not merely multi-prompt, it needs *constructed* dialogue states, which is a strictly stronger access requirement than sending prompts. The statistic is a *divergence between condition-conditional trajectory distributions*, so it is structurally impossible to compute from a handful of prompts: it needs enough prompts per condition to estimate four distributions. Their evaluation spans **over 40 models, 20 red-teaming strategies, 7000+ test cases**. The exact per-condition prompt count is **UNSTATED-IN-SOURCE**.

**That is the surviving scope distinction, and it is a measured property of N-GLARE, not a convenient assumption:** our lane is *few-prompt*; N-GLARE's is *four-condition, thousands-of-cases*.

**The two JSS relations that carry the safety meaning**, in the paper's own words: `JSS(J, B)` "Measures whether the model internally distinguishes adversarial inputs from normal dialogue. High separability implies acute latent risk recognition"; `JSS(J, R)` "Reflects the model's intrinsic refusal tendency and resistance to late-stage safety erosion." The second is the one whose functional form our edit-rank law should be applied to.

### D.3 The token-budget claim, quoted exactly

> "demonstrate that the JSS metric exhibits high consistency with Red Teaming safety rankings at less than 1% token and runtime cost"

It is a percentage of **both** token cost **and** runtime cost — not one or the other. (The `abs`-page rendering of this sentence contains the LaTeX artifact `1\%`; quote from the PDF, not the abs page.)

### D.4 Kendall tau — the hard rule, and a subtlety that could trap a careless citation

**There is no numeric Kendall tau for the headline JSS-vs-red-teaming-ranking claim** in either the arXiv v2 or the ACL camera-ready. The running text says only that "τ remains consistently high, p < 0.05", with the values living in Figures 4–5. Verdict recorded as **`NOT-PRINTED-IN-RUNNING-TEXT`**, with both URLs and the regexes tried logged in `spec_table.json`.

**The subtlety:** Table 2 (§4.3) *does* print numeric Kendall and Spearman values — but for a **different, weaker claim**: the stability of the metric under perturbation of `n`, dataset and model (e.g. jailbreak/Kendall/`n`: mean 0.87, std 0.14). The identical table appears in both the arXiv and ACL versions. **Quoting "N-GLARE achieves tau = 0.87" would be a misattribution**, because that number is a self-consistency check, not agreement with red-team rankings.

**Standing prohibition for every downstream artifact: never write "N-GLARE achieves tau = X" for the headline claim.** If a tau is quoted at all, it must carry the Table 2 locator *and* the words "robustness/self-consistency, not red-team agreement".

### D.5 Verdict and what a functional-form classification actually buys us

**CLASSIFY-BY-FUNCTIONAL-FORM-ONLY** — and the reason is written down **now**, not discovered at implementation time: (i) no public code, and (ii) a four-probing-condition protocol our access model does not grant, plus unstated layer-group boundaries, slice count and per-condition prompt counts.

What the classification buys: N-GLARE is an **across-condition** statistic — a divergence between two condition-conditional distributions — not a level read off one condition. The edit-rank law therefore **predicts its rung before we measure it**, and it can occupy a predicted-rung cell in the registry with `prediction_verified: false`. That is a legitimate row; presenting it as a measured row would not be.
