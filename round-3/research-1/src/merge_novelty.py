"""Merge novelty_A/B/C.json into novelty_table.json (16 rows).

Verdicts are taken from the subagent records; where the orchestrator re-read the
quote and changed a field, the change and the reason are recorded in
`orchestrator_edit` (no majority voting). Positioning sentences are rewritten so
they do not claim results the screen has not produced yet.
"""
import json
from pathlib import Path

WS = Path(__file__).parent

EDITS = {
    "C15": {
        "orchestrator_edit": "Orchestrator adversarial pass (raw/orch_adversarial_new.txt, raw/orch_2608.25390*.txt) found a new nearest miss: Labunets, arXiv:2608.25390 (v2), 'Refusal geometry reflects refusal training', which links a RANK quantity to safety vulnerability ('greater refusal-start diversity is associated with higher stable ranks and weaker difference-in-means single-vector ablation'). It stays a miss: the rank is the stable rank of refusal RESIDUALS, gradients and activation changes (not late-layer effective rank of hidden states); the study covers one lineage (OLMo-2-0425-1B SFT/DPO/RLVR/Instruct stages plus synthetic fine-tunes); and it predicts ablation robustness, not benchmark safety. Verdict NEW kept, and this paper must be cited as the nearest miss.",
        "extra_closest_prior_work": [{"arxiv_id_or_doi": "2608.25390", "title": "Refusal geometry reflects refusal training: diverse refusal prefixes can raise stable rank and weaken refusal vector ablation attacks", "first_author": "Andrey Labunets", "year": 2026, "venue": "arXiv"}],
        "extra_quote": "Across frozen-model analyses and controlled fine-tuning, greater refusal-start diversity is associated with higher stable ranks and weaker difference-in-means single-vector ablation, providing evidence of a simple hardening lever.",
    },
    "C9": {
        "verdict_scope": "PUBLISHED as a per-model, cross-model-normalised quantity tied qualitatively to vulnerability; NOT published as a scalar model ranking correlated numerically with a safety benchmark",
        "positioning_sentence": "Template-region reliance of the refusal decision was introduced and compared across six chat models from four families by Leong et al. (arXiv:2502.13946), who normalise the indirect effect 'for a fair cross-model comparison' and tie template anchoring to vulnerability; our template-site share is a re-derivation of their normalised indirect effect, and our only addition is a numeric test of it as a parent-free cross-family safety score.",
        "orchestrator_edit": "Kept PUBLISHED (plan rule: never soften). Re-read the quote in raw/orch_c9_leong.txt: the NIE normalisation is explicitly 'for a fair cross-model comparison' across Gemma-2, Llama-2, Llama-3 and Mistral; the safety link is qualitative (Figure 4 plus TempPatch), with no per-model scalar correlated against a benchmark.",
    },
    "C16": {
        "correlated_with_benchmark_safety": {"value": "no", "number": "gamma_1 is compared across 6 models by scale, not correlated with an external safety benchmark"},
        "verdict_scope": "PUBLISHED as a per-model steering-sensitivity slope compared across models; the published quantity is gamma_1, the OLS slope of the per-vector ASR dose-response slope (multipliers -1.5..1.5) on cos(v, r_hat). The pure self-steering dose-response along the model's own refusal direction is the special case v = r_hat.",
        "positioning_sentence": "Per-model steering dose-response has already been compared across models: Li (arXiv:2603.24543) fits, for each of six chat models, how steeply attack success responds to steering vectors as a function of their alignment with the refusal direction (gamma_1 from -36.52 for Llama 7B to -193.40 for Qwen 32B), and Tan et al. (arXiv:2407.12404) document that steerability is unreliable across inputs; we therefore use the self-steering slope only as a comparator row.",
        "orchestrator_edit": "Re-grepped arXiv:2603.24543 (raw/orch_c16_2603.24543.txt): Eq. 4 defines slopeASR(v) = (ASR(1.5) - ASR(-1.5))/3 per steering vector, and Eq. 5 regresses it on cos(v, r_hat) per model. The subagent's sentence ('reports self-steering dose-response slopes') overstated the match, so the scope was narrowed and corr_with_benchmark changed from yes to no. The verdict stays PUBLISHED because the hypothesis already concedes C16 and the screen treats it as a comparator.",
    },
}

GENERIC_POS_FIX = [("which is what our metric does", "which is what our screen tests"),
                   ("and is validated as a cross-model safety-ranking feature", "and is tested as a cross-model safety-ranking feature"),
                   ("and is validated as a safety-ra", "and is tested as a safety-ra"),
                   ("is computed per checkpoint and validated as a cross-fam", "is computed per checkpoint and tested as a cross-fam"),
                   ("and validate it as a cross-family safety indicator", "and test it as a cross-family safety indicator"),
                   ("and use the resulting share as a per-checkpoint, cross-family safety indicator", "and test the resulting share as a per-checkpoint, cross-family safety indicator"),
                   ("enabling cross-family comparison where theirs cannot be applied", "which makes a cross-family comparison possible where theirs cannot be applied")]


def main():
    rows = []
    for f in ("novelty_A.json", "novelty_B.json", "novelty_C.json"):
        for r in json.loads((WS / f).read_text())["records"]:
            cid = r["candidate"].split()[0].rstrip(":")
            pos = r.get("positioning_sentence", "")
            for a, b in GENERIC_POS_FIX:
                pos = pos.replace(a, b)
            row = {
                "candidate": cid,
                "name": r["candidate"],
                "verdict": r["verdict"],
                "closest_prior_work": r["closest_prior_work"],
                "what_it_measured": r.get("what_it_measured"),
                "n_models_and_families": r.get("n_models_and_families"),
                "used_to_rank_models": r.get("used_to_rank_models"),
                "parent_free": r.get("parent_free"),
                "prompt_budget": r.get("prompt_budget"),
                "correlated_with_benchmark_safety": r.get("correlated_with_benchmark_safety"),
                "quote": r.get("verbatim_quote"),
                "locator": r.get("locator"),
                "queries_run": r.get("queries_run"),
                "adversarial_note": r.get("adversarial_note"),
                "positioning_sentence": pos,
                "source_file": f,
            }
            row.update(EDITS.get(cid, {}))
            if row.get("extra_closest_prior_work"):
                row["closest_prior_work"] = row["closest_prior_work"] + row.pop("extra_closest_prior_work")
            rows.append(row)
    rows.sort(key=lambda x: int(x["candidate"][1:]))
    assert [r["candidate"] for r in rows] == [f"C{i}" for i in range(1, 17)], [r["candidate"] for r in rows]
    for r in rows:
        assert r["quote"], r["candidate"]
        assert len(r["queries_run"] or []) >= 4, r["candidate"]
    (WS / "novelty_table.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    from collections import Counter
    print(Counter(r["verdict"] for r in rows))


if __name__ == "__main__":
    main()
