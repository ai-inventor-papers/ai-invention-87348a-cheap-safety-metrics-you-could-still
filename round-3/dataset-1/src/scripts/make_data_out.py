"""STEP 8 - package everything into full_data_out.json (exp_sel_data_out shape).

Datasets: dev_panel_outcome, graded_generations, screen16_items, outcome_items, judge_calibration,
external_join, auxiliary_dataset_catalog.  The sealed pool is NEVER included (only its hash, in metadata).
"""
from __future__ import annotations

import json
from pathlib import Path

W = Path(__file__).resolve().parent.parent


def jl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.open()] if p.exists() else []


def main() -> None:
    outcome = json.loads((W / "results" / "outcome.json").read_text())
    panel = json.loads((W / "panel.json").read_text())["rows"]
    ext = {r["repo_id"]: r for r in json.loads((W / "results" / "external_join.json").read_text())["rows"]}
    calib = json.loads((W / "results" / "judge_calibration.json").read_text())
    sealed = json.loads((W / "sealed" / "sealed_items_hashinfo.json").read_text())
    oc = {r["repo"]: r for r in outcome["checkpoints"]}
    items = {r["item_id"]: r for r in jl(W / "outcome_items.jsonl")}
    ds = []

    ex = []
    for p in panel:
        o = oc.get(p["repo"])
        e = ext.get(p["repo"], {})
        ex.append({
            "input": json.dumps({k: p[k] for k in ("repo", "resolved_sha", "family", "lineage", "class", "n_params",
                                                    "stratum", "template_mode", "thinking_flag", "source_of_generations")}),
            "output": f"{o['S2_primary']:.6f}" if o and o["S2_primary"] is not None else "NA",
            "metadata_repo": p["repo"], "metadata_family": p["family"], "metadata_lineage": p["lineage"],
            "metadata_class": p["class"], "metadata_stratum": p["stratum"], "metadata_status": p["status"],
            "metadata_has_sibling": p["has_sibling"], "metadata_standalone": p["standalone"],
            "metadata_source_of_generations": p["source_of_generations"],
            "metadata_label_protocol": o["label_protocol"] if o else None,
            "metadata_S2_core": o["core"]["S2"] if o else None, "metadata_J2_core": o["core"]["J2"] if o else None,
            "metadata_core_components": o["core"] if o else None, "metadata_core_ci95": o["core_ci95"] if o else None,
            "metadata_full_components": o["full"] if o else None, "metadata_full_ci95": o.get("full_ci95") if o else None,
            "metadata_poles": o["poles"] if o else None, "metadata_prefix24_vs_full": o["prefix24_vs_full"] if o else None,
            "metadata_secondary_judge": o["secondary_judge"] if o else None,
            "metadata_stored_vs_fresh": o.get("stored_vs_fresh") if o else None,
            "metadata_n_graded": o["n_graded"] if o else 0, "metadata_n_parse_fail": o["n_parse_fail"] if o else None,
            "metadata_external": {k: v for k, v in e.items() if not k.endswith(("_source_file", "_norm"))},
            "metadata_sealed_items_sha256": sealed["sealed_items_sha256"],
        })
    ds.append({"dataset": "dev_panel_outcome", "examples": ex})

    ex = []
    for d in sorted((W / "results" / "ckpt").iterdir()):
        for src, gf in (("fresh", "gens.json"), ("stored", "stored_gens.json")):
            gpath, grp = d / gf, d / f"grades_{src}.jsonl"
            if not gpath.exists() or not grp.exists():
                continue
            gj = json.loads(gpath.read_text())
            for r, g in zip(gj["rows"], jl(grp)):
                assert r["item_id"] == g["item_id"] and r["condition"] == g["condition"]
                it = items.get(r["item_id"], {})
                ex.append({"input": r["prompt"], "output": r["reply"],
                           "metadata_repo": gj["repo"], "metadata_item_id": r["item_id"], "metadata_condition": r["condition"],
                           "metadata_role": g["role"], "metadata_source": it.get("source"), "metadata_kind": it.get("kind"),
                           "metadata_source_of_generations": gj["source_of_generations"],
                           "metadata_template_mode": r.get("template_mode"), "metadata_n_new_tokens": r.get("n_new_tokens"),
                           "metadata_hit_eos": r.get("hit_eos"), "metadata_prefix24": r.get("prefix24"),
                           "metadata_grade": g["grade"], "metadata_grade_prefix24": g["grade_prefix24"],
                           "metadata_grade_secondary": g["grade_secondary"]})
    ds.append({"dataset": "graded_generations", "examples": ex})

    ds.append({"dataset": "screen16_items", "examples": [
        {"input": r["prompt"], "output": r["side"], "metadata_pair_id": r["pair_id"], "metadata_pair_type": r["pair_type"],
         "metadata_source": r["source"], "metadata_category": r["category"], "metadata_substrate_id": r["substrate_id"],
         "metadata_sha256": r["sha256"]} for r in jl(W / "screen16.jsonl")]})
    core = set(json.loads((W / "results" / "core_items.json").read_text())["item_ids"])
    ds.append({"dataset": "outcome_items", "examples": [
        {"input": r["prompt"], "output": r["outcome_role"], "metadata_item_id": r["item_id"], "metadata_kind": r["kind"],
         "metadata_source": r["source"], "metadata_category": r["category"], "metadata_xstest_type": r["xstest_type"],
         "metadata_twin_group": r["twin_group"], "metadata_jbb_index": r["jbb_index"], "metadata_in_core94": r["item_id"] in core,
         "metadata_substrate_id": r["substrate_id"], "metadata_sha256": r["sha256"]} for r in items.values()]})
    ds.append({"dataset": "judge_calibration", "examples": [
        {"input": json.dumps({"prompt": r["prompt"], "reply": r["reply"]}), "output": r["set"],
         "metadata_ckpt": r["ckpt"], "metadata_substrate_item": r["substrate_item"], "metadata_gpt5mini": r["gpt5mini"],
         "metadata_gemini25flash": r["gemini25flash"], "metadata_rubric_sha": calib["rubric_sha"],
         "metadata_primary_judge": calib["primary_judge"]} for r in calib["rows"]]})
    ds.append({"dataset": "external_join", "examples": [
        {"input": r["repo_id"], "output": json.dumps({k: r.get(k) for k in ("helm_safety_mean", "helm_xstest", "airbench_refusal",
                                                                            "salad_score", "mmlu", "gsm8k", "olb2_average",
                                                                            "olb2_mmlu_pro", "olb2_ifeval")}),
         **{f"metadata_{k.replace('-', '_')}": v for k, v in r.items() if k != "repo_id"}}
        for r in ext.values()]})
    cands = json.loads((W / "dataset_search" / "candidates.json").read_text())
    ds.append({"dataset": "auxiliary_dataset_catalog", "examples": [
        {"input": c["id"], "output": c["verdict"], "metadata_reason": c.get("reason"), "metadata_paper": c.get("paper"),
         "metadata_downloads": c.get("downloads"), "metadata_license": c.get("license"), "metadata_gated": c.get("gated"),
         "metadata_n_rows": c.get("n_rows"), "metadata_fields": c.get("fields")} for c in cands]})

    out = {"metadata": {"title": "Shared graded safety panel (iter-3 screen substrate)",
                        "primary_judge": outcome["primary_judge"], "rubric_sha": outcome["rubric_sha"],
                        "total_spend_usd": outcome["total_spend_usd"],
                        "sealed_items_sha256": sealed["sealed_items_sha256"],
                        "label_protocol": "S2_core (see results/outcome.json protocol)",
                        "deviations": json.loads((W / "acceptance.json").read_text()).get("deviations")
                        if (W / "acceptance.json").exists() else None},
           "datasets": ds}
    (W / "full_data_out.json").write_text(json.dumps(out, ensure_ascii=False))
    print({d["dataset"]: len(d["examples"]) for d in ds})


if __name__ == "__main__":
    main()
