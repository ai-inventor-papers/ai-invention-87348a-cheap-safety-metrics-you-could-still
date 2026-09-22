#!/usr/bin/env python3
"""s3_bookkeeping.py -- session-3 bookkeeping (idempotent; safe to re-run after every panel stage).

1. skips.json: a repo that has a rows/<slug>.json row is MEASURED, so any skip entry for it is stale and is moved
   to skips_superseded.json (kept for provenance, with the time it was superseded).
2. DEVIATIONS.json: adds or refreshes the session-3 entries (second pod restart, hardware change, anchor quartet in
   full mode, ungraded 2-4 B extras, offset-control set) and marks the session-2 ANCHOR_QUARTET_LITE entry as
   superseded. The entry texts are regenerated from the rows on disk, so they stay true as the panel grows.
3. Coverage check: every non-sealed chat/base panel repo must appear in rows/ or in skips.json. Prints the gaps.

Usage: venv_live/bin/python s3_bookkeeping.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

WS = Path(__file__).resolve().parent
DATA = Path("/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_3/gen_art/gen_art_dataset_1")
ANCHORS = ["Qwen/Qwen3-4B", "Qwen/Qwen3-4B-SafeRL", "DreamFast/qwen3-4b-heretic", "mlabonne/Qwen3-4B-abliterated"]
BASE = "Qwen/Qwen3-4B-Base"


def slug(repo: str) -> str:
    return repo.replace("/", "__")


def atomic_write(p: Path, obj) -> None:
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1))
    os.replace(tmp, p)


def load_rows() -> dict[str, dict]:
    out = {}
    for p in sorted((WS / "rows").glob("*.json")):
        r = json.loads(p.read_text())
        out[r["repo"]] = r
    return out


def flags_of(r: dict) -> set[str]:
    return {f.get("code") for f in (r.get("flags") or []) if isinstance(f, dict)}


def upsert(devs: list[dict], code: str, detail: str, affected: list[str]) -> None:
    for d in devs:
        if d.get("code") == code:
            d["detail"], d["affected_repos"] = detail, affected
            return
    devs.append({"code": code, "detail": detail, "affected_repos": affected})


def main() -> None:
    rows = load_rows()
    panel = json.loads((DATA / "panel.json").read_text())["rows"]
    prereg = json.loads((WS / "PREREG.json").read_text())
    sub = set(prereg["cpu_subpanel"])
    labels = json.loads((WS / "labels_map.json").read_text())["rows"]

    # ---- 1. skips
    skips = json.loads((WS / "skips.json").read_text()) if (WS / "skips.json").exists() else []
    sup_p = WS / "skips_superseded.json"
    superseded = json.loads(sup_p.read_text()) if sup_p.exists() else []
    keep = []
    for s in skips:
        if s["repo"] in rows:
            s2 = dict(s)
            s2["superseded_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            s2["superseded_by"] = f"rows/{slug(s['repo'])}.json"
            if not any(x["repo"] == s["repo"] and x.get("code") == s.get("code") for x in superseded):
                superseded.append(s2)
        else:
            keep.append(s)
    atomic_write(WS / "skips.json", keep)
    atomic_write(sup_p, superseded)

    # ---- 2. deviations
    devs = json.loads((WS / "DEVIATIONS.json").read_text())
    for d in devs:
        if d.get("code") == "ANCHOR_QUARTET_LITE" and "SUPERSEDED" not in d["detail"][:40]:
            d["detail"] = ("SUPERSEDED in session 3 by ANCHOR_QUARTET_FULL_ON_CPU (no anchor row carries the ANCHOR_LITE "
                           "flag). Session-2 text kept for provenance: " + d["detail"])
        if d.get("code") == "POD_RESTART_RESUME" and "second pod restart" not in d["detail"]:
            d["detail"] += (" A second pod restart at ~17:37 UTC killed the session-2 v2 driver (run_panel_v2.sh) after 4 "
                            "of 19 v2 sub-panel rows. Session 3 (17:53 UTC) resumed from the persisted rows with "
                            "run_panel_v3.sh. The 4 rows measured on 2 threads in session 2 were moved to "
                            "scratch/rows_v2_session2_2threads/ and re-measured, so every row in rows/ was measured in "
                            "session 3 with the same code on the same 4-thread CPU allocation.")
    s3 = [r for r in rows.values()]
    anchors_measured = [a for a in ANCHORS if a in rows]
    anchors_lite = [a for a in anchors_measured if "ANCHOR_LITE" in flags_of(rows[a])]
    upsert(devs, "HARDWARE_SESSION3",
           "Session 3 ran on 4 hyperthreads = 2 physical AMD EPYC 9655P (Zen5) cores (cpuset 20,80,116,176; cgroup "
           "memory 16 GB; no GPU; no sibling agents), versus 2 hyperthreads of one core in sessions 1-2. torch uses "
           "len(os.sched_getaffinity(0)) = 4 threads. All per-candidate seconds in rows/ come from this allocation; "
           "they are CPU wall-clock numbers and say nothing about S5 (GPU timing), which stays not measurable.",
           [])
    upsert(devs, "ANCHOR_QUARTET_FULL_ON_CPU",
           f"With 4 CPUs the graded Qwen3-4B anchor quartet (outside CPU_SUBPANEL) is measured in FULL mode (random-"
           f"direction nulls, k8, both wrapped poles, oracle rows, C9 true patching), with the PREREG time caps raised "
           f"to soft 2400 s / hard 3600 s (TIME_CAP_OVERRIDE flag in each row). Measured so far: "
           f"{len(anchors_measured)}/4; rows still flagged ANCHOR_LITE: {anchors_lite or 'none'}. mlabonne/Qwen3-4B-"
           f"abliterated ships fp32 shards and is loaded into bf16. Qwen/Qwen3-4B-Base (base stratum, plain "
           f"renderer, excluded from every correlation) is measured in ANCHOR_LITE mode"
           f"{' (row present)' if BASE in rows else ' (row not present yet)'}.",
           anchors_measured + ([BASE] if BASE in rows else []))
    extras = [r for r in rows if r not in sub and r not in ANCHORS and r != BASE]
    upsert(devs, "PANEL_EXTENDED_UNGRADED_EXTRAS",
           f"Session 3 also measured {len(extras)} ungraded 2-4 B chat panel rows outside CPU_SUBPANEL in full mode "
           f"(raised caps, TIME_CAP_OVERRIDE) so that iteration 5 has join-ready values for them. They have no label "
           f"and enter no correlation. Their NOT_IN_CPU_SUBPANEL skip entries moved to skips_superseded.json.",
           extras)
    upsert(devs, "OFFSET_CONTROL_SET",
           "The plan's constant-offset control set is Qwen3-4B, Qwen2.5-1.5B-Instruct, Llama-3.2-1B, TinyLlama, "
           "OLMo-2-1B and SmolLM2-360M. Session 1 substituted Qwen3-0.6B for Qwen3-4B (outside CPU_SUBPANEL). "
           "Session 3 added Qwen3-4B back (method.py OFFSET_MODELS) because the anchors now run in full mode, so "
           "the control covers 7 models: " + ", ".join(sorted(r for r in rows if rows[r].get("offset_control")))
           + ". The C9 AtP-validation set keeps its session-1 substitute (Qwen2.5-0.5B for Qwen3-4B); C9 true "
             "patching is measured on every model, so the per-model AtP-vs-true Pearson is reported for all.",
           sorted(r for r in rows if rows[r].get("offset_control")))
    atomic_write(WS / "DEVIATIONS.json", devs)

    # ---- 3. coverage
    skip_repos = {s["repo"] for s in keep}
    gaps = []
    for pr in panel:
        if pr.get("sealed") or pr.get("stratum") not in ("chat", "base"):
            continue
        if pr["repo"] not in rows and pr["repo"] not in skip_repos:
            gaps.append(pr["repo"])
    graded_rows = [r for r in rows if (labels.get(r) or {}).get("BALANCED") is not None]
    print(json.dumps({"rows": len(rows), "graded_rows": len(graded_rows), "anchors_measured": anchors_measured,
                      "extras_measured": extras, "skips_active": len(keep), "skips_superseded": len(superseded),
                      "coverage_gaps": gaps}, indent=1))
    if gaps:
        print("COVERAGE GAPS: these panel repos are neither in rows/ nor in skips.json (still queued?)", file=sys.stderr)


if __name__ == "__main__":
    main()
