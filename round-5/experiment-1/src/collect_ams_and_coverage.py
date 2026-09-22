#!/usr/bin/env python3
"""STEP 6 coverage check + STEP 9 ams_tier1.json.

coverage: every one of the 36 panel repos (23 graded + 12 Set A + the base stratum) must have a row with
status ok, or a skip with a code; any row missing C1, C2, logit_gap or refusal_mass is listed for re-measurement
("join complete" requirement). Writes coverage_gpu5.json and prints the re-measure command.
ams_tier1.json: one entry per model (package version or REIMPLEMENTATION, path used, per-concept sigma and layer,
verdict, wall seconds, extra args needed, published vs cross-fitted values and gap, random-direction null).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import blind_guard

blind_guard.install()

WS = Path(__file__).resolve().parent
ROWS = WS / "rows"
REQUIRED = ["C1", "C2", "logit_gap", "refusal_mass"]


def slug(repo: str) -> str:
    return repo.replace("/", "__")


def main() -> None:
    prereg = json.loads((WS / "PREREG.json").read_text())
    panel = prereg["panel"]["graded"] + prereg["panel"]["setA"] + prereg["panel"]["base"]
    skips = json.loads((WS / "skips.json").read_text()) if (WS / "skips.json").exists() else []
    skip_by = {s["repo"]: s for s in skips}
    cov: dict[str, object] = {"n_panel": len(panel), "ok": [], "incomplete": [], "skipped": [], "missing": []}
    ams: dict[str, object] = {}
    for repo in panel:
        p = ROWS / f"{slug(repo)}.json"
        if not p.exists():
            (cov["skipped"] if repo in skip_by else cov["missing"]).append(  # type: ignore[union-attr]
                {"repo": repo, **({"code": skip_by[repo]["code"]} if repo in skip_by else {})})
            continue
        r = json.loads(p.read_text())
        cands = r.get("candidates") or {}
        missing = [c for c in REQUIRED if not isinstance(cands.get(c), dict)
                   or cands[c].get("value") is None and not cands[c].get("undefined")]
        entry = {"repo": repo, "status": r.get("status"), "missing_required": missing,
                 "n_candidates": len(cands), "wall_s": r.get("wall_s"),
                 "vram_peak_gb": (r.get("compute") or {}).get("vram_peak_gb"),
                 "flags": [f.get("code") for f in (r.get("flags") or [])]}
        (cov["incomplete"] if missing else cov["ok"]).append(entry)  # type: ignore[union-attr]
        a = r.get("ams") or {}
        ams[repo] = {"status": a.get("status"), "package": a.get("package"), "path_used": a.get("path_used"),
                     "extra_args": a.get("extra_args"), "seconds": a.get("seconds"),
                     "concepts": a.get("concepts"), "summary": a.get("summary"),
                     "notes": a.get("notes"), "deviations": a.get("deviations"),
                     "class": r.get("class"), "family": r.get("family"), "n_params": r.get("n_params"),
                     "graded": r.get("graded"), "setA": repo in prereg["panel"]["setA"]}
    cov["n_ok"] = len(cov["ok"])  # type: ignore[arg-type]
    cov["n_incomplete"] = len(cov["incomplete"])  # type: ignore[arg-type]
    cov["n_skipped"] = len(cov["skipped"])  # type: ignore[arg-type]
    cov["n_missing"] = len(cov["missing"])  # type: ignore[arg-type]
    (WS / "coverage_gpu5.json").write_text(json.dumps(cov, indent=1))
    (WS / "ams_tier1.json").write_text(json.dumps(ams, indent=1))
    todo = [e["repo"] for e in cov["incomplete"]] + [e["repo"] for e in cov["missing"]]  # type: ignore[index]
    print(json.dumps({k: cov[k] for k in ("n_panel", "n_ok", "n_incomplete", "n_skipped", "n_missing")}))
    if todo:
        print("re-measure: venv_gpu/bin/python method.py --repos " + ",".join(todo))
    sys.exit(0)


if __name__ == "__main__":
    main()
