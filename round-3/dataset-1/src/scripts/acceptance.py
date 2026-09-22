"""STEP 8 - acceptance asserts -> acceptance.json.  A failed assert is a NAMED deviation, never hidden."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

W = Path(__file__).resolve().parent.parent


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().casefold())


def main() -> None:
    panel = json.loads((W / "panel.json").read_text())["rows"]
    outcome = json.loads((W / "results" / "outcome.json").read_text())
    graded = [p for p in panel if p["status"] == "graded" and p["stratum"] == "chat"]
    fam = defaultdict(int)
    for p in graded:
        fam[p["family"]] += 1
    loaded = (W / "results" / "loaded_repos.txt").read_text().split() if (W / "results" / "loaded_repos.txt").exists() else []
    sealed_loaded = [r for r in loaded if re.search(r"granite|stablelm", r, re.I)]
    scr = {norm(json.loads(l)["prompt"]) for l in (W / "screen16.jsonl").open()}
    out = {norm(json.loads(l)["prompt"]) for l in (W / "outcome_items.jsonl").open()}
    hinfo = json.loads((W / "sealed" / "sealed_items_hashinfo.json").read_text())
    # no later script references the sealed pool path (only build_items.py may)
    refs = [str(p.relative_to(W)) for p in (W / "scripts").glob("*.py")
            if p.name not in ("build_items.py", "acceptance.py") and "sealed_items.jsonl" in p.read_text()]
    spend = outcome["total_spend_usd"]
    checks = {
        "graded_chat_checkpoints>=30": (len(graded), len(graded) >= 30),
        "families_with>=2_graded>=6": (sorted(f for f, n in fam.items() if n >= 2), sum(n >= 2 for n in fam.values()) >= 6),
        "blanket_refusers_graded>=2": (sum(p["class"] == "blanket_refuser" for p in graded),
                                       sum(p["class"] == "blanket_refuser" for p in graded) >= 2),
        "standalone_graded>=3": (sum(p["standalone"] for p in graded), sum(p["standalone"] for p in graded) >= 3),
        "zero_sealed_repos_loaded": (sealed_loaded, not sealed_loaded),
        "screen16_outcome_sealed_disjoint": ({"screen_outcome": len(scr & out), **hinfo["disjointness"]},
                                             not (scr & out) and all(v == 0 for v in hinfo["disjointness"].values())),
        "sealed_pool_not_referenced_after_construction": (refs, not refs),
        "total_spend<=6usd": (round(spend, 4), spend <= 6.0),
    }
    deviations = [{"name": "NO_GPU_PANEL_SHRINK",
                   "detail": "env.json: torch.cuda.is_available()=False, 2-CPU cpuset shared with sibling executors. "
                             "CPU fallback: fresh generations are 64-token greedy (not 128) on the CORE-94 item set; "
                             "checkpoints harvested in iter-2 use their stored 96-token replies truncated to 64 tokens "
                             "(source_of_generations=stored_96tok_fallback). The panel-wide label is S2_core; the full 180-item "
                             "S2 exists only for Qwen/Qwen2.5-0.5B-Instruct (benchmark run)."},
                  {"name": "POLES_PARTIAL",
                   "detail": "Pole wrappers (always/never refuse) generated on 24 items (SCREEN16 + 4 + 4) and only for fresh "
                             "checkpoints <=1.7B; >=2B fresh checkpoints and stored-generation checkpoints have poles=null."},
                  {"name": "PRIMARY_JUDGE_SWITCHED",
                   "detail": "Calibration gate failed for openai/gpt-5-mini (accuracy 0.892 < 0.9; grader-side refusal on "
                             "known-compliant replies); primary = google/gemini-2.5-flash, secondary = gpt-5-mini. Gemini "
                             "returns an empty completion on a few replies (provider block); those are re-graded by gpt-5-mini "
                             "and flagged judge_fallback=true."},
                  {"name": "GRADING_SEPARATE_PROCESS",
                   "detail": "Grading ran as a separate async watcher process (scripts/grade.py --watch) rather than inside "
                             "the generation process; semantics unchanged."},
                  {"name": "EXTERNAL_SAFETY_COLUMNS_EMPTY",
                   "detail": "HELM safety / AIR-Bench / SALAD have n=0 exact-id joins for this <=4B panel; capability "
                             "covariates come from Open LLM Leaderboard v2 contents (n=16) and v1 MMLU/GSM8K (n=1)."}]
    for k, (v, ok) in checks.items():
        if not ok:
            deviations.append({"name": f"ACCEPTANCE_FAILED:{k}", "detail": f"value={v}"})
    res = {"checks": {k: {"value": v, "pass": ok} for k, (v, ok) in checks.items()},
           "all_pass": all(ok for _, ok in checks.values()), "deviations": deviations,
           "graded_by_family": dict(fam)}
    (W / "acceptance.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res["checks"], indent=1))


if __name__ == "__main__":
    main()
