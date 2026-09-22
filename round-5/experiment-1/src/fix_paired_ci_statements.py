#!/usr/bin/env python3
"""fix_paired_ci_statements.py -- documents the PAIRED_CI_STATEMENT_THREE_WAY reporting fix.

Two REPORTING defects, no measured value touched:

1. analyze_gpu.py's extra_ams_head_to_head() used a BINARY rule for `plain_statement`
   (beats = ci_lo>0, else "does NOT clearly beat ... (CI includes 0)"), so the else-branch
   also fired when ci_hi<0 -- i.e. when the CI excludes 0 on the NEGATIVE side and the AMS
   variant is clearly worse. 9/10 blocks in analysis_gpu.json were in that state. Fixed to a
   three-way rule (this file recomputes it deterministically, read-only, from each block's own
   ci_lo/ci_hi -- it does not re-run the bootstrap and changes no number):
     ci_lo > 0  -> "<aid> beats <other> on the paired lineage-bootstrap CI (excludes 0)"
     ci_hi < 0  -> "<aid> is CLEARLY WORSE than <other>: the paired lineage-bootstrap CI
                    excludes 0 on the negative side"
     else       -> "<aid> does NOT clearly beat <other> (CI includes 0)"
   AMS_beats (ci_lo>0) is kept exactly as-is; AMS_clearly_worse (isfinite(ci_hi) and ci_hi<0)
   is a new sibling boolean.

2. make_results.py wrote RESULTS.md Sec 3 as `json.dumps(...)[:500]`, truncating mid-number.
   Replaced with a "variant | rho difference | lineage-bootstrap 95% CI | verdict" table per
   comparison (paired_vs_C2, paired_vs_logit_gap), verdict in {beats, clearly worse, not
   distinguishable}.

HOW THIS RUN WAS ACTUALLY APPLIED (see DEVIATIONS.json code PAIRED_CI_STATEMENT_THREE_WAY):
  - analyze_gpu.py and make_results.py were edited with the rule/table above, then
    analyze_gpu.py was RE-RUN end-to-end (system python3, seeded bootstrap N_BOOT=2000) to
    regenerate analysis_gpu.json + analysis_tables_gpu.md. Every numeric leaf of the new
    analysis_gpu.json was diffed against the pre-fix file: 0 leaves differed by > 1e-12; only
    plain_statement strings and the new AMS_clearly_worse booleans changed (Step B, clean).
  - Running the updated make_results.py, by contrast, was found to DROP the hand-authored
    "## 0. Headline findings" narrative and other hand-added prose in RESULTS.md (that
    content is not reproduced by the current script). That regenerated RESULTS.md was
    therefore discarded, and RESULTS.md was instead hand-patched in place: only the two
    truncated Sec-3 lines were replaced with the two tables below (computed here from
    analysis_gpu.json, matching what the corrected make_results.py emits); every other line,
    including the already-correct Sec 0 item 4 ("CI excludes zero"), was left untouched.

Run this script to reproduce/verify the plain_statement + table logic against the live
analysis_gpu.json; it only prints, it does not write anything.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

WS = Path(__file__).resolve().parent


def three_way_statement(aid: str, other: str, ci_lo: float, ci_hi: float) -> tuple[bool, bool, str]:
    beats = bool(math.isfinite(ci_lo) and ci_lo > 0)
    clearly_worse = bool(math.isfinite(ci_hi) and ci_hi < 0)
    if beats:
        stmt = f"{aid} beats {other} on the paired lineage-bootstrap CI (excludes 0)"
    elif clearly_worse:
        stmt = (f"{aid} is CLEARLY WORSE than {other}: the paired lineage-bootstrap CI "
                f"excludes 0 on the negative side")
    else:
        stmt = f"{aid} does NOT clearly beat {other} (CI includes 0)"
    return beats, clearly_worse, stmt


def verdict(beats: bool, clearly_worse: bool) -> str:
    if beats:
        return "beats"
    if clearly_worse:
        return "clearly worse"
    return "not distinguishable"


def main() -> None:
    an = json.loads((WS / "analysis_gpu.json").read_text())
    h2h = an.get("extra_ams_head_to_head", {})
    for key, other in (("paired_vs_C2", "C2"), ("paired_vs_logit_gap", "logit_gap")):
        print(f"\n{key} (vs {other})")
        for aid, v in (h2h.get(key) or {}).items():
            beats, clearly_worse, stmt = three_way_statement(aid, other, v["ci_lo"], v["ci_hi"])
            assert beats == v["AMS_beats"], (aid, key, "AMS_beats mismatch")
            assert clearly_worse == v.get("AMS_clearly_worse"), (aid, key, "AMS_clearly_worse mismatch")
            assert stmt == v["plain_statement"], (aid, key, "plain_statement mismatch")
            print(f"  {aid}: {v['point']:+.3f} [{v['ci_lo']:+.3f}, {v['ci_hi']:+.3f}] -> "
                  f"{verdict(beats, clearly_worse)}")
    print("\nOK: live analysis_gpu.json matches the three-way rule for every block.")


if __name__ == "__main__":
    main()
