#!/usr/bin/env python3
"""Build a Stage-1 panel of exactly the checkpoints that have GENERATIONS but no recipe vector yet.

Stage 1 and Stage 2 walk different orderings under different size caps, so a checkpoint can end up
GRADED with no weight readout and be silently dropped from the join that the primary endpoint needs.
This closes that gap explicitly: every graded checkpoint is guaranteed a recipe vector.
"""
from __future__ import annotations
import json, sys
from pathlib import Path

WS = Path(__file__).resolve().parent


def main() -> None:
    gen = {p.stem for p in (WS / "results" / "gen").glob("*.jsonl")}
    have = {p.stem for p in (WS / "results" / "ckpt").glob("*.json")}
    missing = sorted(gen - have)
    panel = json.loads((WS / "results" / "panel.json").read_text())
    rows = panel["checkpoints"] if isinstance(panel, dict) else panel
    by = {r["repo_id"].replace("/", "__"): r for r in rows}
    sel = [by[m] for m in missing if m in by]
    (WS / "results" / "panel_graded_gap.json").write_text(
        json.dumps({"checkpoints": sel}, indent=1))
    print(f"generated={len(gen)} with_recipe={len(have & gen)} missing_recipe={len(sel)}")
    for r in sel:
        print(f"  {r['arm']:<7} {(r.get('n_params_est') or 0)/1e9:5.2f}B {r['repo_id']}")
    sys.exit(0)


if __name__ == "__main__":
    main()
