#!/usr/bin/env python3
"""s4_bookkeeping.py -- session-4 bookkeeping (idempotent; safe to re-run after every GPU panel stage).

Session 4 started after the third pod restart on a new pod that HAS a GPU (NVIDIA L4, 23 GB). The whole panel
is re-measured on CUDA into rows/, and the session-3 CPU rows are kept in scratch/rows_cpu_v3/.

1. skips.json: a repo with a rows/<slug>.json row is MEASURED, so any skip entry for it (e.g. the session-1
   NOT_IN_CPU_SUBPANEL entries) moves to skips_superseded.json with the time and the superseding row.
2. DEVIATIONS.json: marks the CPU-era entries SUPERSEDED for the final rows (their text is kept for provenance,
   because it still describes scratch/rows_cpu_v3/), appends the third restart to POD_RESTART_RESUME, and
   adds or refreshes the session-4 entries. The texts are regenerated from the rows on disk.
3. Coverage: every non-sealed chat/base panel repo must be in rows/ or skips.json; prints the gaps.

Usage: venv_live/bin/python s4_bookkeeping.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import numpy as np

WS = Path(__file__).resolve().parent
DATA = Path("/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_3/gen_art/gen_art_dataset_1")
ANCHORS = ["Qwen/Qwen3-4B", "Qwen/Qwen3-4B-SafeRL", "DreamFast/qwen3-4b-heretic", "mlabonne/Qwen3-4B-abliterated"]
BASE = "Qwen/Qwen3-4B-Base"
SUPERSEDED_TAG = "SUPERSEDED in session 4"


def slug(repo: str) -> str:
    return repo.replace("/", "__")


def atomic_write(p: Path, obj) -> None:
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1))
    os.replace(tmp, p)


def load_rows(d: Path) -> dict[str, dict]:
    out = {}
    for p in sorted(d.glob("*.json")):
        r = json.loads(p.read_text())
        out[r["repo"]] = r
    return out


def upsert(devs: list[dict], code: str, detail: str, affected: list[str]) -> None:
    for d in devs:
        if d.get("code") == code:
            d["detail"], d["affected_repos"] = detail, affected
            return
    devs.append({"code": code, "detail": detail, "affected_repos": affected})


def supersede(devs: list[dict], code: str, why: str) -> None:
    for d in devs:
        if d.get("code") == code and not d["detail"].startswith(SUPERSEDED_TAG):
            d["detail"] = f"{SUPERSEDED_TAG} ({why}). Earlier text, kept for provenance: " + d["detail"]


def dev(r: dict) -> str:
    return (r.get("compute") or {}).get("device", "cpu")


def main() -> None:
    rows = load_rows(WS / "rows")
    cpu_rows = load_rows(WS / "scratch" / "rows_cpu_v3") if (WS / "scratch" / "rows_cpu_v3").exists() else {}
    panel = json.loads((DATA / "panel.json").read_text())["rows"]
    labels = json.loads((WS / "labels_map.json").read_text())["rows"]
    gpu = {k: r for k, r in rows.items() if dev(r) == "cuda"}
    non_gpu = sorted(k for k, r in rows.items() if dev(r) != "cuda")

    # ---- 1. skips
    skips = json.loads((WS / "skips.json").read_text()) if (WS / "skips.json").exists() else []
    sup_p = WS / "skips_superseded.json"
    superseded = json.loads(sup_p.read_text()) if sup_p.exists() else []
    keep = []
    for s in skips:
        if s["repo"] in rows:
            s2 = dict(s)
            s2["superseded_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            s2["superseded_by"] = f"rows/{slug(s['repo'])}.json ({dev(rows[s['repo']])})"
            if not any(x["repo"] == s["repo"] and x.get("code") == s.get("code") for x in superseded):
                superseded.append(s2)
        else:
            keep.append(s)
    atomic_write(WS / "skips.json", keep)
    atomic_write(sup_p, superseded)

    # ---- 2. deviations
    devs = json.loads((WS / "DEVIATIONS.json").read_text())
    why_gpu = "the final rows/ were re-measured on an NVIDIA L4 GPU; see GPU_SESSION4_FULL_PANEL"
    for code in ("LIVE_TIER_NO_CUDA", "CPU_DTYPE_BF16_ALL", "HARDWARE_SESSION3", "ANCHOR_QUARTET_FULL_ON_CPU",
                 "PANEL_EXTENDED_UNGRADED_EXTRAS"):
        supersede(devs, code, why_gpu + "; the text still describes the CPU rows in scratch/rows_cpu_v3/")
    for d in devs:
        if d.get("code") == "ANCHOR_QUARTET_LITE" and "session 4" not in d["detail"]:
            d["detail"] = ("Session 4: the anchor quartet was measured on the GPU in full mode with the PREREG caps; no "
                           "row carries ANCHOR_LITE. " + d["detail"])
        if d.get("code") == "POD_RESTART_RESUME" and "third pod restart" not in d["detail"]:
            d["detail"] += (" A third pod restart (~18:17-18:23 UTC) killed the session-3 v3 driver after 12 v3 CPU rows. "
                            "Session 4 (18:24 UTC) started on a new pod with an NVIDIA L4 GPU and re-measured the whole "
                            "panel on CUDA (GPU_SESSION4_FULL_PANEL); the 12 session-3 CPU rows were moved to "
                            "scratch/rows_cpu_v3/.")
    n_rand = sorted({(r.get("compute") or {}).get("n_rand") for r in gpu.values()} - {None})
    peaks = [(r.get("compute") or {}).get("vram_peak_gb") for r in gpu.values()]
    peaks = [p for p in peaks if isinstance(p, (int, float))]
    chunked = sorted(k for k, r in gpu.items() if any(isinstance(f, dict) and f.get("code") == "GRAD_CHUNKED"
                                                      for f in (r.get("flags") or [])))
    graded_gpu = sorted(k for k in gpu if (labels.get(k) or {}).get("BALANCED") is not None)
    vram_txt = (f"VRAM peak: max {max(peaks):.2f} GB over {len(peaks)} rows (cap 9.3 GB). " if peaks
                else "VRAM peak: not yet available. ")
    upsert(devs, "GPU_SESSION4_FULL_PANEL",
           "Session 4 ran on a new pod with an NVIDIA L4 (23 GB; cgroup 15.3 CPUs / 71 GB RAM), after the third pod "
           "restart. It built the CUDA venv venv_gpu (torch 2.14.0 CUDA build, transformers 4.57.6; same versions as "
           "venv_live apart from the CUDA build). It made method.py/live_lib.py device-agnostic with device plumbing "
           "only: model and batch on the device, .cpu() before numpy, hook vectors on the hidden state's device, "
           "torch.cuda.synchronize() in the per-block timers, set_per_process_memory_fraction(9.3/total), no RLIMIT_AS "
           "under CUDA, and a GRAD_CHUNKED halving fallback for the backward pass. Candidate definitions, directions, "
           "folds, seeds, bands, prompts and judge calls are unchanged. "
           f"Measured on the GPU: {len(gpu)} rows ({len(graded_gpu)} graded), in full mode with the PREREG time caps. "
           f"PREREG's pre-declared GPU-branch constants apply: {n_rand or '[20]'} anisotropy-matched random "
           "directions (PREREG n_gpu = 20; its 'used': 8 and compute_mode.cuda = false describe the CPU state when the "
           "file was hashed at 15:59:59Z, and the file is unchanged), and all 5 C16 alphas in every variant, because "
           "the 3-alpha variant grid was a CPU-only budget cut. " + vram_txt, sorted(gpu))
    d_last = next(d for d in devs if d["code"] == "GPU_SESSION4_FULL_PANEL")
    d_last["detail"] += (f"The backward pass fell back to chunks on: {chunked or 'none'}. "
                         f"Rows not measured on CUDA: {non_gpu or 'none'}. S5 (<120 s per 4B model on the GPU, "
                         "excluding load) is measurable in this session. The 12 CPU rows of session 3 "
                         f"({len(cpu_rows)} files in scratch/rows_cpu_v3/) are compared with their GPU re-measurement "
                         "in candidates_live.json 'cross_hardware'. That comparison is descriptive only.")
    d_last["affected_repos"] = sorted(gpu)
    d_last["detail"] += (" torch 2.14 routes the RoPE outer product (inv_freq @ position_ids) through a Triton 'native DSL' "
                         "kernel that JIT-compiles a C helper; this pod has no libc headers, so every model failed to load "
                         "until TORCH_DISABLE_NATIVE_JIT=1 was set (method.py sets it before importing torch). torch then "
                         "uses its standard ATen kernels, so no measured quantity depends on this switch.")

    def flagged(code: str) -> list[str]:
        return sorted(k for k, r in rows.items() if any(isinstance(f, dict) and f.get("code") == code
                                                         for f in (r.get("flags") or [])))
    raised = flagged("VRAM_CAP_RAISED")
    caps = sorted({f.get("cap_gb") for k in raised for f in rows[k].get("flags", [])
                   if isinstance(f, dict) and f.get("code") == "VRAM_CAP_RAISED"})
    upsert(devs, "VRAM_CAP_RAISED_OOM_RETRY",
           f"{len(raised)} ungraded chat models ran out of memory under the plan's 9.3 GB VRAM cap in run_panel_gpu.sh, "
           "even with the 1-item backward fallback: Llama-3.2-3B-abliterated (3.6 B, untied embeddings) in the backward "
           "pass, and Phi-3.5-mini (3.8 B, 32 KV heads) in the first base pass. The plan's fallback 2 prescribes halving the "
           "batch to 8 and then 4. Instead they were re-run (run_panel_gpu_retry.sh) with the cap raised to "
           f"{caps} GB, which is still inside a 16 GB worker. That keeps their 16-item batches, and therefore the bf16 "
           "numerics, identical to every other model's. Each of these rows carries a VRAM_CAP_RAISED flag. Both "
           "models are ungraded and enter no correlation. They do enter the S5 (~4B timing) set.", raised)
    tok_fb = flagged("TOKENIZER_FROM_LINEAGE")
    upsert(devs, "TOKENIZER_FROM_LINEAGE",
           "Robust-Decoding/gemma2-2b-it-hh-dpo-harmless-step-6000 ships no tokenizer files. The repo holds only the "
           "config, weights and an empty auto-generated card; vocab_size is 256000, the Gemma-2 vocabulary. It failed to "
           "load (RUN_FAIL) in run_panel_gpu.sh. It was re-run in run_panel_gpu_retry.sh with the tokenizer and "
           "chat template of its panel lineage root, unsloth/gemma-2-2b-it (live_lib.TOKENIZER_FROM_LINEAGE). This "
           "borrows the family tokenizer, not any parent weights or activations, so the model is still read alone. The "
           "row is ungraded and carries a TOKENIZER_FROM_LINEAGE flag.", tok_fb)
    sb = WS / "scratch" / "stage_b_cuda_Qwen__Qwen2.5-0.5B-Instruct.json"
    if sb.exists():
        b = json.loads(sb.read_text())
        b1 = b.get("B1_batched_vs_unbatched", {})
        for d in devs:
            if d.get("code") == "STAGE_B1_BF16_ROUNDING" and "Session 4 (GPU)" not in d["detail"]:
                d["detail"] += (f" Session 4 (GPU, CUDA bf16): on the same check, max |diff| = {b1.get('max_abs_diff'):.3f} and "
                                f"mean = {b1.get('mean_abs_diff'):.3f} logits (scratch/stage_b_cuda_Qwen__Qwen2.5-0.5B-Instruct.json). "
                                "The GPU bf16 kernels depend on batch shape more than the CPU ones. The same-batch-composition "
                                "design is what keeps this out of the candidates. B2, B3, B5 and D pass on the GPU row; B4 "
                                f"(C2 {b.get('B4_c2_vs_null', {}).get('C2'):.3f} vs its null p95 "
                                f"{b.get('B4_c2_vs_null', {}).get('null_p95'):.3f}) is recorded as measured.")

    # refresh two session-3 texts from the GPU rows (the entries were computed from the CPU rows)
    off = sorted(k for k, r in rows.items() if r.get("offset_control"))
    upsert(devs, "OFFSET_CONTROL_SET",
           "The plan's constant-offset control set is Qwen3-4B, Qwen2.5-1.5B-Instruct, Llama-3.2-1B, TinyLlama, "
           "OLMo-2-1B and SmolLM2-360M. Session 1 substituted Qwen3-0.6B for Qwen3-4B (outside the CPU sub-panel). "
           "The GPU rows run the plan's set plus Qwen3-0.6B, so the control covers "
           f"{len(off)} models: {', '.join(off)}. The C9 AtP-validation set keeps its session-1 substitute "
           "(Qwen2.5-0.5B for Qwen3-4B). C9 true patching is measured on every model, so the per-model AtP-vs-true "
           "Pearson is reported for all.", off)
    ratios, acc, n_layers_tot = [], 0, 0
    for r in rows.values():
        for cid in ("C1", "C2"):
            for e in ((r.get("random_dirs") or {}).get(cid) or []):
                n_layers_tot += 1
                acc += int(bool(e.get("n_accepted_in_tries")))
                ratios += [x for x in (e.get("ratio_picked") or []) if isinstance(x, (int, float))]
    if ratios:
        q = np.percentile(ratios, [5, 50, 95])
        for d in devs:
            if d.get("code") == "RANDOM_DIRS_FALLBACK_CLOSEST":
                d["detail"] = (d["detail"].split(" GPU rows (session 4):")[0] +
                               f" GPU rows (session 4): {acc} of {n_layers_tot} (model, candidate, B_mid layer) cells had "
                               f"at least one accepted draw in 2000 tries; the picked directions' activation-variance "
                               f"ratio var(Av)/var(Ah) has median {q[1]:.2f} (5-95%: {q[0]:.2f}-{q[2]:.2f}). The random "
                               "directions typically carry several times the harm direction's variance. That is "
                               "expected to widen the direction-null p95 used by S2(b); it was not tested with an "
                               "exactly variance-matched null (see RESULTS 4c for the S2(b) decomposition).")
                d["affected_repos"] = sorted(rows)
    upsert(devs, "ROSI_ARM_CPU_FP32",
           "The ROSI 128-token side arm (rosi128.py, rosi_128tok.json) ran in sessions 1-2 on CPU in float32 "
           "(the plan's CPU rule), not in bf16 on a GPU. Session 4 does not re-run it: fp32 is the more exact path, "
           "the 128-token generations and their paid grades are final, and the arm does not depend on the panel.",
           ["Qwen/Qwen2.5-0.5B-Instruct"])
    atomic_write(WS / "DEVIATIONS.json", devs)

    # ---- 3. coverage
    skip_repos = {s["repo"] for s in keep}
    gaps = [pr["repo"] for pr in panel if not pr.get("sealed") and pr.get("stratum") in ("chat", "base")
            and pr["repo"] not in rows and pr["repo"] not in skip_repos]
    print(json.dumps({"rows": len(rows), "gpu_rows": len(gpu), "graded_gpu_rows": len(graded_gpu),
                      "anchors_measured": [a for a in ANCHORS if a in rows], "base_measured": BASE in rows,
                      "non_gpu_rows": non_gpu, "skips_active": keep, "skips_superseded": len(superseded),
                      "grad_chunked": chunked, "vram_peak_max_gb": max(peaks) if peaks else None,
                      "coverage_gaps": gaps}, indent=1))
    if gaps:
        print("COVERAGE GAPS: these panel repos are neither in rows/ nor in skips.json (still queued?)", file=sys.stderr)


if __name__ == "__main__":
    main()
