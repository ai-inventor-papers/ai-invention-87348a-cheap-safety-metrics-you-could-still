# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Standardise every candidate dataset to the exp_sel_data_out schema, then keep the best 6.

Stage A (candidates): the 12 auxiliary HF datasets in temp/datasets/ -> temp/aux_full_data_out.json
    (one example per ROW; kept as candidates / reserve pools, NOT in the final output).
Stage B (panel): the 6 plan datasets built from results/ by scripts/make_data_out.py
    (dev_panel_outcome, graded_generations, screen16_items, outcome_items, judge_calibration, external_join).
FINAL = the 6 best-suited datasets for the artifact objective (see SELECTION below) -> full_data_out.json.
Run: uv run data.py   (add --with-candidates to also rebuild the candidate file)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

W = Path(__file__).resolve().parent
T = W / "temp" / "datasets"

# The artifact objective is a GRADED SAFETY PANEL (per-checkpoint two-sided outcome + the items and judge
# evidence behind it). The six plan datasets are the only ones that carry per-CHECKPOINT labels; the auxiliary
# HF datasets are prompt pools / external graders with no per-checkpoint outcome, so they are kept as candidates.
SELECTION = ["dev_panel_outcome", "graded_generations", "screen16_items", "outcome_items", "judge_calibration",
             "external_join"]


def rows(org_name: str, stem: str) -> list[dict]:
    p = T / org_name / f"full_{stem}.json"
    return json.loads(p.read_text())


def s(x) -> str:
    return x if isinstance(x, str) else json.dumps(x, ensure_ascii=False)


def aux() -> list[dict]:
    ds = []

    def add(name, exs):
        exs = [e for e in exs if e["input"].strip()]
        for i, e in enumerate(exs):
            e["metadata_row_index"] = i
        ds.append({"dataset": name, "examples": exs})

    add("AmazonScience/FalseReject", [
        {"input": r["prompt"], "output": "benign_alarming", "metadata_category": r.get("category_text"),
         "metadata_task_type": "over_refusal_prompt"} for r in rows("AmazonScience__FalseReject", "AmazonScience_FalseReject_default_train")])
    add("LibrAI/do-not-answer", [
        {"input": r["question"], "output": "should_refuse", "metadata_risk_area": r["risk_area"],
         "metadata_types_of_harm": r["types_of_harm"], "metadata_specific_harms": r["specific_harms"],
         "metadata_task_type": "harmful_prompt"} for r in rows("LibrAI__do-not-answer", "LibrAI_do-not-answer_default_train")])
    add("PKU-Alignment/BeaverTails", [
        {"input": json.dumps({"prompt": r["prompt"], "response": r["response"]}, ensure_ascii=False),
         "output": "safe" if r["is_safe"] else "unsafe",
         "metadata_harm_categories": [k for k, v in r["category"].items() if v], "metadata_task_type": "response_safety_classification"}
        for r in rows("PKU-Alignment__BeaverTails", "PKU-Alignment_BeaverTails_default_30k_train")])
    add("PKU-Alignment/PKU-SafeRLHF", [
        {"input": json.dumps({"prompt": r["prompt"], "response_0": r["response_0"], "response_1": r["response_1"]}, ensure_ascii=False),
         "output": str(r["safer_response_id"]), "metadata_is_response_0_safe": r["is_response_0_safe"],
         "metadata_is_response_1_safe": r["is_response_1_safe"], "metadata_better_response_id": r["better_response_id"],
         "metadata_response_0_severity_level": r["response_0_severity_level"],
         "metadata_response_1_severity_level": r["response_1_severity_level"], "metadata_task_type": "safer_response_preference"}
        for r in rows("PKU-Alignment__PKU-SafeRLHF", "PKU-Alignment_PKU-SafeRLHF_default_train")])
    add("stanford-crfm/air-bench-2024", [
        {"input": r["prompt"], "output": "should_refuse", "metadata_cate_idx": r["cate-idx"], "metadata_l2_name": r["l2-name"],
         "metadata_l3_name": r["l3-name"], "metadata_l4_name": r["l4-name"], "metadata_task_type": "harmful_prompt"}
        for r in rows("stanford-crfm__air-bench-2024", "stanford-crfm_air-bench-2024_default_test")])
    add("toxigen/toxigen-data", [
        {"input": r["text"], "output": s(r["toxicity_human"]), "metadata_toxicity_ai": r["toxicity_ai"],
         "metadata_target_group": r["target_group"], "metadata_task_type": "regression"}
        for r in rows("toxigen__toxigen-data", "toxigen_toxigen-data_annotated_train")])
    add("nvidia/Aegis-AI-Content-Safety-Dataset-2.0", [
        {"input": r["prompt"], "output": s(r["prompt_label"]), "metadata_response": r.get("response"),
         "metadata_response_label": r.get("response_label"), "metadata_violated_categories": r.get("violated_categories"),
         "metadata_task_type": "prompt_safety_classification"}
        for r in rows("nvidia__Aegis-AI-Content-Safety-Dataset-2.0", "nvidia_Aegis-AI-Content-Safety-Dataset-2.0_default_train")
        if r.get("prompt") and r["prompt"] != "REDACTED"])
    ah = [(r, "harmful") for r in rows("ai-safety-institute__AgentHarm", "ai-safety-institute_AgentHarm_harmful_test_public")]
    ah += [(r, "benign") for r in rows("ai-safety-institute__AgentHarm", "ai-safety-institute_AgentHarm_harmless_benign_test_public")]
    add("ai-safety-institute/AgentHarm", [
        {"input": r["prompt"], "output": lab, "metadata_twin_id": r["id"], "metadata_id_original": r["id_original"],
         "metadata_category": r["category"], "metadata_name": r["name"], "metadata_task_type": "agentic_harmful_vs_benign_twin"}
        for r, lab in ah])
    cc = [(r, "should_not_comply") for r in rows("allenai__coconot", "allenai_coconot_original_train")]
    cc += [(r, "should_comply_contrast") for r in rows("allenai__coconot", "allenai_coconot_contrast_test")]
    add("allenai/coconot", [
        {"input": r["prompt"], "output": lab, "metadata_category": r["category"], "metadata_subcategory": r["subcategory"],
         "metadata_task_type": "noncompliance_vs_contrast"} for r, lab in cc])
    add("allenai/real-toxicity-prompts", [
        {"input": r["prompt"]["text"], "output": s(r["prompt"].get("toxicity")), "metadata_challenging": r["challenging"],
         "metadata_continuation_toxicity": (r.get("continuation") or {}).get("toxicity"), "metadata_task_type": "regression"}
        for r in rows("allenai__real-toxicity-prompts", "allenai_real-toxicity-prompts_default_train")])
    add("furonghuang-lab/PHTest", [
        {"input": r["Request"], "output": r["Harmfulness"], "metadata_task_type": "pseudo_harmful_prompt"}
        for r in rows("furonghuang-lab__PHTest", "furonghuang-lab_PHTest_default_train")])
    tq = [{"input": r["question"], "output": r["best_answer"], "metadata_config": "generation", "metadata_category": r["category"],
           "metadata_incorrect_answers": r["incorrect_answers"], "metadata_task_type": "capability_truthfulness"}
          for r in rows("truthfulqa__truthful_qa", "truthfulqa_truthful_qa_generation_validation")]
    for r in rows("truthfulqa__truthful_qa", "truthfulqa_truthful_qa_multiple_choice_validation"):
        ch = r["mc1_targets"]
        tq.append({"input": json.dumps({"question": r["question"], "choices": ch["choices"]}, ensure_ascii=False),
                   "output": str(ch["labels"].index(1)), "metadata_config": "multiple_choice", "metadata_n_classes": len(ch["choices"]),
                   "metadata_task_type": "classification"})
    add("truthfulqa/truthful_qa", tq)
    return ds


AUX_NAMES = ["AmazonScience/FalseReject", "LibrAI/do-not-answer", "PKU-Alignment/BeaverTails", "PKU-Alignment/PKU-SafeRLHF",
             "stanford-crfm/air-bench-2024", "toxigen/toxigen-data", "nvidia/Aegis-AI-Content-Safety-Dataset-2.0",
             "ai-safety-institute/AgentHarm", "allenai/coconot", "allenai/real-toxicity-prompts", "furonghuang-lab/PHTest",
             "truthfulqa/truthful_qa"]


def main() -> None:
    # Candidate standardisation is only rebuilt on request (python data.py --with-candidates): the final
    # output contains ONLY the chosen 6 datasets.
    if "--with-candidates" in sys.argv:
        a = aux()
        (W / "temp" / "aux_full_data_out.json").write_text(json.dumps({"metadata": {"role": "candidate pools, not selected"},
                                                                      "datasets": a}, ensure_ascii=False))
        print("aux:", {d["dataset"]: len(d["examples"]) for d in a})
    sys.path.insert(0, str(W / "scripts"))
    import make_data_out  # stdlib only
    make_data_out.main()
    full = json.loads((W / "full_data_out.json").read_text())
    full["datasets"] = [d for d in full["datasets"] if d["dataset"] in SELECTION]
    assert [d["dataset"] for d in full["datasets"]] == SELECTION
    full["metadata"]["selection"] = {"selected": SELECTION,
                                     "not_selected_candidates": AUX_NAMES + ["auxiliary_dataset_catalog"],
                                     "candidates_file": "temp/aux_full_data_out.json (regenerable: uv run data.py --with-candidates)"}
    (W / "full_data_out.json").write_text(json.dumps(full, ensure_ascii=False))
    print("final:", {d["dataset"]: len(d["examples"]) for d in full["datasets"]})


if __name__ == "__main__":
    main()
