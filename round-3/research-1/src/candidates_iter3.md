# Iteration-3 screen candidates (C1-C16), with one-line functional forms
NOTE: iteration-1 research (art_DeogIL_xh3pE) used labels C1-C5 for DIFFERENT metrics. Map its findings by CONTENT only.

- C1 harm-to-refusal gain: finite-difference change in the late refusal-axis projection per unit nudge along the model's own mid-depth cross-fitted harm direction.
- C2 self-ablation sensitivity: drop in refusal margin on harmful items and on benign twins after removing the model's own direction in a layer band, compared with an anisotropy-matched random direction.
- C3 twin patching flip depth: patch the benign twin's residual into the harmful run in 6 depth bands; read where and how sharply the refusal margin flips.
- C4 writer capacity: how much o_proj/down_proj can write along the refusal axis, as a z-score against random directions from the layer's output span.
- C5 harm-to-refusal weight-path gain: bilinear gain through MLP and attention output paths, summed over depth.
- C6 concentration of direct logit attribution (DLA) to refusal tokens across heads and MLPs (top-k share and depth centroid).
- C7 late-layer attention mass from the decision position onto harmful-vs-twin differing tokens.
- C8 input-gradient share of the refusal margin on those differing tokens.
- C9 template-site share of refusal drive.
- C10 area between the harm-decodability depth curve and the refusal-drive depth curve.
- C11 refusal-commitment trajectory over the first 8 generated tokens.
- C12 twin discrimination along the refusal axis (harmful vs twin separation relative to harmful vs plain benign).
- C13 presentation invariance, with a pre-signed negative orientation.
- C14 ridge metamodel on at most 24 depth-by-site features.
- C15 late-layer effective rank / dispersion.
- C16 self-steering dose-response slope.
