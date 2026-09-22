# Smoke diff: Qwen/Qwen2.5-0.5B-Instruct, IT4 (CPU tier row) vs gpu5 port (this smoke)

| candidate | IT4 value | gpu5 value | rel diff |
|---|---|---|---|
| C1 | 6.108276672891084 | 6.108276672891084 | 0.0000% |
| C2 | 0.1270400380987688 | 0.1270400380987688 | 0.0000% |
| logit_gap | 2.0272586345672607 | 2.0272586345672607 | 0.0000% |
| refusal_mass | 0.4128792341798544 | 0.4128792341798544 | 0.0000% |

All four bit-exact (same seeds, same device class -- both runs on the same L4; IT4's row for this
particular repo happened to also be measured on CUDA in iteration 4, not the CPU sub-panel, so an
exact match is expected here rather than "within 5%"). No bisection needed.

New blocks (all finite or undefined-with-reason on this model; VRAM peak 1.21 GB; wall 54.0 s):
  C1n_cd=6.206 (eps0), 20 distinct null seed values, pull_even present (harm=-14.34, 20 rand values)
  C1n_os=... (see row), C6=0.507 (variant=standard, rel_err=0.0023), C6_insample=..., C6_lens=...
  C10=0.0215, C12=0.130, C12r=..., C13=..., C13_rank=..., C13_logit=..., C15_erank=..., C15_disp=...
  AMS_published=5.236 (status=ok, 20-value random-direction null)
k8 populated for C1/C2/C11/C1n_cd/C1n_os/C6/C10/C12/C13/C15 (no K8_BLOCK_FAILED flag).
offset_control populated for BOTH "late" (B_late[0]) and "mid" (B_mid[0]-1), each with C1/C2/C11/
logit_gap/mean_harmful_margin_level/mean_late_projection_on_rb_level/C6_share/C10/C12/C13_rank/
C15_disp reads (no OFFSET_CONTROL_FAILED flag).
Flags: only GPU5_TIME_CAPS_NOT_PREREGISTERED (soft=900s, hard=1500s; expected -- the gpu5 PREREG has
no time_caps key).
