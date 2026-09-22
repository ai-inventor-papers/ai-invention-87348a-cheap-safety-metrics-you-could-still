#!/usr/bin/env python3
"""Checkpoint-level ground truth, RE-GRADED in the stance framing (judge_stance.py).

Same 13 real checkpoints, same stored generations (iteration 1: 48 harmful + 32
XSTest twins each), same D2 arithmetic as judge_harvest.py -- only the judge's
framing changes, so these numbers and the per-cell numbers of judge2.py are one
instrument. The StrongREJECT-framed originals stay in out/ground_truth/ for
comparison. Writes out/ground_truth_stance/<repo>.json.
"""
import json
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent
sys.path.insert(0, str(WORKSPACE))

import judge_harvest as JH  # noqa: E402
import judge_stance as JS  # noqa: E402

JH.GT_DIR = JH.OUT / "ground_truth_stance"
JH.GT_DIR.mkdir(parents=True, exist_ok=True)
JH.grade_one = JS.grade_stance

if __name__ == "__main__":
    JH.main()
    for p in JH.GT_DIR.glob("*.json"):
        d = json.loads(p.read_text())
        if d.get("judge_rubric") != JS.RUBRIC_VERSION:
            d["judge_rubric"] = JS.RUBRIC_VERSION
            d["scope"] = (d.get("scope", "") + " RE-GRADED in the STANCE framing "
                          "(judge_stance.py) to remove grader-side refusal.")
            p.write_text(json.dumps(d, indent=1, default=float))
