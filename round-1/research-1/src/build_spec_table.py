#!/usr/bin/env python3
"""Merge the per-source raw JSON files into the single machine-readable spec table
that downstream artifacts parse out of research_out.json."""
import json, datetime, pathlib

RAW = pathlib.Path(__file__).parent / "raw"

def load(name, default=None):
    p = RAW / name
    if not p.exists():
        return default
    with p.open() as f:
        return json.load(f)

incumbents = []
for fn in ["spec_AMS.json", "spec_GFS.json", "spec_NGLARE.json", "spec_RAS.json"]:
    d = load(fn)
    if d is None:
        incumbents.append({"id": fn.replace("spec_", "").replace(".json", ""),
                           "status": "NOT-EXTRACTED-IN-THIS-ARTIFACT"})
    else:
        incumbents.append(d)

cands = load("candidates.json", {})
nums = load("numbers_N1_N5.json", {})
decs = load("decisions.json", {})
adv = load("adversarial_C3_C4_C5.json")

# fold the adversarial re-check into the candidate records
if adv:
    by_id = {v["id"]: v for v in adv.get("verdicts", [])}
    for c in cands.get("candidates", []):
        if c["id"] in by_id:
            c["adversarial_recheck"] = by_id[c["id"]]

table = {
    "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "artifact": "gen_plan_research_1_idx1 - incumbent bars + dated saturation screen",
    "search_date": "2026-09-20",
    "incumbents": incumbents,
    "candidates": cands.get("candidates", []),
    "recency_sweep_2026_08_to_09": cands.get("recency_sweep_2026_08_to_09", []),
    "load_bearing_numbers": nums.get("load_bearing_numbers", []),
    "aux_2603_27412": nums.get("aux_2603_27412"),
    "decisions": decs.get("decisions", []),
    "tooling_note": cands.get("tooling_note"),
}
out = pathlib.Path(__file__).parent / "spec_table.json"
out.write_text(json.dumps(table, indent=2))
print(f"wrote {out} ({out.stat().st_size} bytes); "
      f"{len(incumbents)} incumbents, {len(table['candidates'])} candidates, "
      f"{len(table['load_bearing_numbers'])} numbers, {len(table['decisions'])} decisions")
