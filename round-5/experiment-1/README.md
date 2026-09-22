# A cheap inside-the-model safety metric, screened blind against its black-box baseline

`demo/` — Self-contained demo (Colab-ready notebook or markdown). Run without setup.  
`src/` — Full source code, data, and outputs from the experiment execution.

**Type:** experiment  
**ID:** `art_OCDSllyuKmFT`

## Layman Summary

Tests cheap "look inside the model" safety signals on 35 small chat models using 16 prompts each. Against a rulebook fixed in advance, exactly one signal passes every gate - but it still does not beat simply reading the model's output probabilities.

## Full Summary

GPU TIER of the iteration-5 cheap-safety screen (run_fcYd_7ruOwtm), on an L4 under a 10.0 GB cap (declared 10.5, never exceeded). One pass over the SAME 36 checkpoints iteration 4 measured, on the SAME frozen SCREEN16 substrate (8 harmful/benign-twin pairs = 16 prompts, seed 20260921): 23 GRADED, 12 SET A (measured and hashed BEFORE any Set A label exists) and Qwen3-4B-Base in its own stratum. 35 rows; microsoft/Phi-3.5-mini-instruct is the one recorded skip (OOM_AT_10GB), so Set A is 11/12. PREREG.json (S1-S6, orientations, seeds) was frozen and hashed 2026-09-21T21:52:31Z (46accdd6...) BEFORE any value was computed; every row carries the hash and the analysis refuses a different one. No backward pass anywhere, which is what fits the VRAM budget.

MEASURED. (1) C1n: C1 minus the same finite-difference gain under 20 NORM-MATCHED random steers drawn from each layer's own activation span, eps in {0.02,0.05,0.10}, as a central difference (the odd part) and one-sided plus the even 'pull' where Malla et al. 2609.06951's content-free pull lives. (2) Five never-run activation reads, cross-fitted on 4 twin-grouped folds: C6 (DLA concentration), C10 (area between harm-decodability and refusal-drive depth curves), C12 (twin d-prime on a cross-fitted harm axis), C13 (presentation invariance), C15-act (late-layer effective rank/dispersion). (3) AMS Tier-1 (ams-scanner 0.1.3) as the published incumbent, in-process on our bf16 model, plus our cross-fitted variants and random-direction nulls. Logit-only bars: first-token logit gap, refusal-token mass.

RESULTS (graded n=23, 8 families, 11 lineages, 2 blanket refusers; MDE_rho=0.531).
1. C12 IS THE ONLY READ TO PASS ALL OF S1-S6, the first across iterations 4-5. rho=0.607 [0.360,0.868] with BALANCED, 0.786 at family level, 0.581 on PRODUCT; S1 partial given logit gap and log size 0.432, one-sided 5% bound 0.006 - it clears by a hair, stated not rounded away. Only internal read to pass the repaired S3. Positive in Qwen3 (0.67, n=8) and Qwen2.5 (0.70, n=5) but NEGATIVE in TinyLlama (-0.10, n=5): not yet a cross-family law.
2. HEAD-TO-HEAD VS THE BLACK-BOX BAR (pre-registered under S1; the number that answers whether looking inside buys anything). Of 27 reads with a paired lineage-bootstrap CI of rho(cand)-rho(logit_gap), exactly ONE beats the first-token logit gap: C2, +0.128 [+0.012,+0.423]. Thirteen are indistinguishable, thirteen clearly WORSE. C12, the sole S1-S6 passer, is INDISTINGUISHABLE from the bar (-0.165 [-0.311,+0.168]). Passing the frozen rule and beating the baseline are different things.
3. C1 IS NOT THE CONTENT-FREE PULL: rho(C1, C1n_cd)=0.995 over 35 models; rho with BALANCED 0.770 before, 0.762 after subtracting the median random steer. The pull is real but does not carry C1, and its sign varies by model.
4. THE ODD PART IS THE SIGNAL, THE EVEN PART MISLEADS: C1n_cd (central) +0.762 vs C1n_os (one-sided) -0.446. A one-sided steering gain would have been confidently WRONG-SIGNED.
5. THE INCUMBENT LOSES AND ITS SHIPPED CODE HAS A BUG. Every AMS variant is worse than C2 with a paired CI excluding zero (AMS_published -0.622 [-1.005,-0.254]); 4/5 also clearly worse than the logit gap; AMS fails S5 (96 prompts vs our 16); its in-sample-minus-cross-fitted gap is ~1.4 sigma against its own 2.0/3.5 band. ams-scanner 0.1.3 never sets tokenizer.padding_side and reads hidden_states[:,-1,:] at batch_size=8, i.e. PAD activations: an isolation test on Qwen2.5-0.5B harmful_content gives package sigma 0.745 (CRITICAL) vs 5.334 at batch_size=1 and 5.292 with left padding. Verdicts over 35 models: ours 27 PASS/8 WARN/0 CRIT, the package's 16/11/8. Both reported side by side, never reconciled.
6. HONEST NEGATIVE: no internal read adds anything over judging the model's own 16 replies (C12 -0.006, C2 +0.309 with a 5% bound of -0.075).
7. DROPPING THE OLD S2(b) RULE WAS RIGHT: under it the only passing row is AMS_published at 1.00, which is what an overfitted in-sample direction does; C12 0.52, C2 0.30.
8. BLINDNESS: 11 Set A checkpoints frozen into values_setA.json (95d97ac3...) before any label existed - no Set A grading workspace existed at freeze - with an audit hook over open()/read_text() (167 opens checked, 0 blocked). Set B stayed sealed.

VALIDATION. 26 unit tests pass. The smoke model reproduces iteration 4's C1, C2, logit_gap and refusal_mass BIT-EXACTLY; the analysis dry run reproduces iteration 4's C2 rho 0.900, partial 0.746, old-S2b 7/23. OpenRouter spend $0.00 of $1.00. 13 deviations with codes, including SIBLING_PREREG_ABSENT, AMS_PKG_PADDING_BUG, OOM_AT_10GB and PAIRED_CI_STATEMENT_THREE_WAY (the paired-CI sentence was binary and mislabelled 9 of 10 negative-side exclusions as 'CI includes 0'; now three-way, and re-running the analysis changed 0 numeric leaves by more than 1e-12). Labels: BALANCED = S2_core on CORE-94 (64-token greedy, gemini-2.5-flash stance judge); PRODUCT = P2.

## Dependencies

- `art_newxSSMj3rpV` — dataset
- `art_DeogIL_xh3pE` — incumbent specs
- `art_EnR_R4JcH3XY` — kill-check

## Output Files

- `method.py`
- `full_method_out.json`
- `mini_method_out.json`
- `preview_method_out.json`

## Demo Files

- **method.py** — Research methodology implementation

---
*Generated by AI Inventor Pipeline*
