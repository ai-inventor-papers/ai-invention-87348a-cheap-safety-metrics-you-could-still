#!/usr/bin/env python3
"""Purpose-built compact spec table for embedding in research_out.json's answer.
Every field here is one a downstream executor acts on. The COMPLETE record
(all verbatim quotes, grep logs, queries, full model rosters) is spec_table.json."""
import json, pathlib
D = pathlib.Path(__file__).parent
full = json.loads((D / "spec_table.json").read_text())

def cut(s, n=620):
    if not isinstance(s, str): return s
    return s if len(s) <= n else s[:n] + " …[full text in spec_table.json]"

incs = []
for i in full.get("incumbents", []):
    if i.get("status") == "NOT-EXTRACTED-IN-THIS-ARTIFACT":
        incs.append(i); continue
    st = i.get("statistic", {}) or {}
    ho = i.get("held_out_protocol", {}) or {}
    re_ = i.get("reimplementation", {}) or {}
    ac = i.get("access_class", {}) or {}
    incs.append({
        "id": i.get("id"), "arxiv": i.get("arxiv"), "title": i.get("title"),
        "venue": i.get("venue"), "code": (i.get("urls") or {}).get("code"),
        "role_in_our_study": cut(i.get("role_in_our_study"), 420),
        "statistic": {
            "name": st.get("name"),
            "formula_prose": cut(st.get("formula_prose"), 1500),
            "inputs_read": st.get("inputs_read"),
            "matrices_or_layers": cut(st.get("matrices_or_layers"), 420),
            "token_positions": cut(st.get("token_positions"), 260),
            "pooling": cut(st.get("pooling"), 260),
            "normalisation": cut(st.get("normalisation"), 260),
            "direction_fitted": st.get("direction_fitted"),
            "fitted_from": cut(st.get("fitted_from"), 420),
            "cross_fitted": cut(st.get("cross_fitted"), 420),
            "n_prompts": st.get("n_prompts"),
            "generation_required": st.get("generation_required"),
            "threshold_rule": cut(st.get("threshold_rule"), 520),
            "free_hyperparameters": st.get("free_hyperparameters"),
        },
        "compute_class": cut(i.get("compute_class"), 420),
        "parent_free": i.get("parent_free", ac.get("parent_free")),
        "parent_free_evidence": cut(i.get("parent_free_evidence") or ac.get("quote_reference"), 520),
        "model_panel_summary": {
            "n": (i.get("model_panel") or {}).get("n_configs") or (i.get("model_panel") or {}).get("n_models"),
            "families": (i.get("model_panel") or {}).get("families"),
        },
        "headline_numbers": [
            {"quantity": cut(n.get("quantity"), 200), "value": cut(n.get("value"), 620),
             "n": n.get("n"), "unit_of_resampling": n.get("unit_of_resampling"),
             "locator": n.get("locator")}
            for n in (i.get("reported_numbers") or [])[:6]
        ],
        "held_out_protocol": {
            "what_was_held_out": cut(ho.get("what_was_held_out"), 620),
            "what_was_NOT_held_out": cut(ho.get("what_was_NOT_held_out"), 620),
            "quote": cut(ho.get("quote"), 620),
            "strictness_vs_ours": ho.get("strictness_vs_ours"),
            "why": cut(ho.get("why"), 520),
        },
        "bar_row": i.get("bar_row"),
        "reimplementation": {
            "verdict": re_.get("verdict"),
            "missing_details": re_.get("missing_details"),
            "estimated_effort": cut(re_.get("estimated_effort"), 260),
            "blocking_dependency": cut(re_.get("blocking_dependency"), 420),
        },
        "already_published_we_must_cite_not_claim": i.get("already_published_we_must_cite_not_claim"),
        "name_collisions": i.get("name_collisions"),
    })

cands = []
for c in full.get("candidates", []):
    ar = c.get("adversarial_recheck") or {}
    cands.append({
        "id": c.get("id"), "one_line": cut(c.get("one_line"), 260),
        "search_date": full.get("search_date"),
        "n_queries_run": len(c.get("queries_run") or []),
        "verdict": c.get("verdict"),
        "openness_strength": cut(c.get("openness_strength"), 720),
        "nearest_paper": {k: cut(v, 720) for k, v in (c.get("nearest_paper") or {}).items()},
        "surviving_margin": cut(c.get("surviving_margin"), 520),
        "if_closed_the_pivot": cut(c.get("if_closed_the_pivot"), 420),
        "confidence": c.get("confidence"),
        "must_beat_baseline": cut(c.get("must_beat_baseline"), 420),
        "known_confound": cut(c.get("known_confound"), 520),
        "pre_registration_forced": cut(c.get("pre_registration_forced"), 520),
        "adversarial_recheck": {
            "adversarial_verdict": ar.get("adversarial_verdict"),
            "strongest_counterexample": {k: cut(v, 620) for k, v in (ar.get("strongest_counterexample") or {}).items()},
            "recommended_margin_rewording": cut(ar.get("recommended_margin_rewording"), 520),
            "confidence": ar.get("confidence"),
        } if ar else None,
    })

nums = [{"nid": n.get("nid"), "arxiv": n.get("arxiv"),
         "claim_the_hypothesis_makes": cut(n.get("claim_the_hypothesis_makes"), 420),
         "verdict": n.get("verdict"),
         "key_quote": cut(((n.get("occurrences") or [{}])[0]).get("quote"), 520),
         "consequence": cut(n.get("consequence"), 900)}
        for n in full.get("load_bearing_numbers", [])]

compact = {
    "generated_utc": full.get("generated_utc"),
    "artifact": full.get("artifact"),
    "search_date": full.get("search_date"),
    "_note": ("COMPACT VIEW. The complete record - every verbatim quote, every grep run, "
              "every query, full model rosters - is spec_table.json in this artifact's "
              "workspace; the prose twin is research_report.md."),
    "tooling_note": full.get("tooling_note"),
    "incumbents": incs,
    "candidates": cands,
    "load_bearing_numbers": nums,
    "aux_2603_27412": {"finding": cut((full.get("aux_2603_27412") or {}).get("finding"), 720)},
    "recency_sweep_2026_08_to_09": full.get("recency_sweep_2026_08_to_09"),
    "decisions": full.get("decisions"),
}
out = D / "spec_table_compact.json"
out.write_text(json.dumps(compact, indent=1))
print(f"wrote {out} ({out.stat().st_size} bytes)")
