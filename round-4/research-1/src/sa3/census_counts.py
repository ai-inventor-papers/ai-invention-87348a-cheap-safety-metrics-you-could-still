#!/usr/bin/env python3
"""Compute census_counts.json + printed summary from sa3/_rows_partial.json + panel.json.
Definitions:
  - "exact" = checkpoint_exact_match True AND number_exists == 'yes'
  - "upstream" = number_exists in ('yes','upstream_only') regardless of checkpoint_exact_match,
                 i.e. allowing an upstream-official number to stand in for the exact checkpoint.
  - Safety benchmarks (for (a)/(b)):
        HELM_Safety, AIR_Bench, SALAD, TrustLLM, JailbreakBench, HarmBench, other_card_safety
  - Over-refusal benchmark (for (c)): HELM_XSTest_overrefusal, or other_card_safety rows whose
    metric_name/value mentions XSTest/over-refusal/refusal-rate/VPRR/IPRR/Over-Refusal explicitly.
  - Capability benchmarks (for (d)/(e)): MMLU, GSM8K, Arena_Hard, OLB_v2
"""
import json
from pathlib import Path

WS = Path("/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_4/gen_art/gen_art_research_1")
PANEL = Path("/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_3/gen_art/gen_art_dataset_1/panel.json")

rows = json.load(open(WS / "sa3/_rows_partial.json"))
panel = json.load(open(PANEL))["rows"]
panel_repos = {r["repo"] for r in panel}
N = len(panel_repos)  # panel size, excluding sealed (sealed families are not in panel.json at all)

SAFETY_BENCHES = {"HELM_Safety", "AIR_Bench", "SALAD", "TrustLLM", "JailbreakBench", "HarmBench", "other_card_safety"}
CAPABILITY_BENCHES = ["MMLU", "GSM8K", "Arena_Hard", "OLB_v2"]
OVERREFUSAL_KEYWORDS = ["xstest", "over-refusal", "over refusal", "vprr", "iprr", "refusal rate", "false refusal"]

def is_overrefusal_row(r):
    # Only rows that actually carry a number count; ignore collapsed 'no' rows and ignore the
    # free-text 'notes' field (which may incidentally mention 'xstest'/'refusal' while describing
    # what was CHECKED-AND-NOT-FOUND, e.g. "grepped for ... xstest|harmbench|refusal ... keywords").
    if r["number_exists"] not in ("yes", "upstream_only"):
        return False
    if r["benchmark"] == "HELM_XSTest_overrefusal":
        return True
    blob = " ".join(str(r.get(k, "")) for k in ("benchmark", "metric_name", "value")).lower()
    return any(k in blob for k in OVERREFUSAL_KEYWORDS)

def row_benches(r):
    """A collapsed 'no' row may list several benchmarks joined by '+'; split them."""
    return r["benchmark"].split("+")

# per-repo aggregation, panel repos only (exclude sealed_family rows from N-based counts)
per_repo = {repo: {"safety_exact": False, "safety_upstream": False, "overrefusal_exact": False,
                    "overrefusal_upstream": False, "cap_exact": {b: False for b in CAPABILITY_BENCHES},
                    "cap_upstream": {b: False for b in CAPABILITY_BENCHES}, "class": None}
            for repo in panel_repos}
panel_by_repo = {r["repo"]: r for r in panel}
for repo in panel_repos:
    per_repo[repo]["class"] = panel_by_repo[repo]["class"]

for r in rows:
    repo = r["repo"]
    if repo not in per_repo:
        continue  # sealed_family rows handled separately below
    yes = r["number_exists"] == "yes"
    upstream_ok = r["number_exists"] in ("yes", "upstream_only")
    exact = bool(r.get("checkpoint_exact_match"))
    for b in row_benches(r):
        b_clean = b.split("(")[0]  # strip footnote-style suffixes like "(HELM-native)"
        if b_clean in SAFETY_BENCHES or b_clean == "other_card_safety":
            if yes and exact:
                per_repo[repo]["safety_exact"] = True
            if upstream_ok:
                per_repo[repo]["safety_upstream"] = True
        if b_clean in CAPABILITY_BENCHES:
            if yes and exact:
                per_repo[repo]["cap_exact"][b_clean] = True
            if upstream_ok:
                per_repo[repo]["cap_upstream"][b_clean] = True
    if is_overrefusal_row(r) and b_clean != "HELM_Safety":
        pass
    if is_overrefusal_row(r):
        if yes and exact:
            per_repo[repo]["overrefusal_exact"] = True
        if upstream_ok:
            per_repo[repo]["overrefusal_upstream"] = True

a_exact_any_safety = sum(1 for v in per_repo.values() if v["safety_exact"])
b_upstream_any_safety = sum(1 for v in per_repo.values() if v["safety_upstream"])
c_overrefusal_exact = sum(1 for v in per_repo.values() if v["overrefusal_exact"])
c_overrefusal_upstream = sum(1 for v in per_repo.values() if v["overrefusal_upstream"])

d_capability = {}
for b in CAPABILITY_BENCHES:
    exact_n = sum(1 for v in per_repo.values() if v["cap_exact"][b])
    upstream_n = sum(1 for v in per_repo.values() if v["cap_upstream"][b])
    d_capability[b] = {"exact": exact_n, "upstream_or_exact": upstream_n, "coverage_fraction_exact": round(exact_n / N, 3),
                        "coverage_fraction_upstream": round(upstream_n / N, 3)}

e_per_benchmark_coverage = {}
ALL_BENCHES = list(SAFETY_BENCHES - {"other_card_safety"}) + ["HELM_XSTest_overrefusal"] + CAPABILITY_BENCHES
for b in ALL_BENCHES:
    exact_n = 0
    upstream_n = 0
    for repo in panel_repos:
        exact_flag = False
        upstream_flag = False
        for r in rows:
            if r["repo"] != repo:
                continue
            if b not in row_benches(r):
                continue
            if r["number_exists"] == "yes" and r.get("checkpoint_exact_match"):
                exact_flag = True
            if r["number_exists"] in ("yes", "upstream_only"):
                upstream_flag = True
        exact_n += exact_flag
        upstream_n += upstream_flag
    e_per_benchmark_coverage[b] = {"exact": exact_n, "upstream_or_exact": upstream_n,
                                    "fraction_exact": round(exact_n / N, 3), "fraction_upstream": round(upstream_n / N, 3)}

# (f) community fine-tunes: classes considered "community fine-tune" = abliterated, blanket_refuser,
# safety_tuned EXCEPT Qwen/Qwen3-4B-SafeRL which is an official Qwen-team release (flagged not_independent
# but not a third-party community fine-tune).
COMMUNITY_CLASSES = {"abliterated", "blanket_refuser", "safety_tuned"}
community_repos = {repo for repo, v in per_repo.items() if v["class"] in COMMUNITY_CLASSES and repo != "Qwen/Qwen3-4B-SafeRL"}
community_with_safety = [repo for repo in community_repos if per_repo[repo]["safety_exact"] or per_repo[repo]["safety_upstream"]]
community_zero_safety = len(community_with_safety) == 0

counts = {
    "panel_size_N_excluding_sealed": N,
    "a_exact_checkpoint_any_published_safety_number": a_exact_any_safety,
    "b_allowing_upstream_official_any_published_safety_number": b_upstream_any_safety,
    "c_overrefusal_number": {"exact": c_overrefusal_exact, "upstream_or_exact": c_overrefusal_upstream},
    "d_capability_benchmark_coverage": d_capability,
    "e_per_benchmark_coverage_fraction": e_per_benchmark_coverage,
    "f_community_finetunes_zero_published_safety_numbers": community_zero_safety,
    "f_community_finetune_repos_total": len(community_repos),
    "f_community_finetune_repos_WITH_a_safety_number": community_with_safety,
    "note_on_f": ("FALSE as a blanket claim: "
                  f"{len(community_with_safety)} of {len(community_repos)} community fine-tune checkpoints carry a "
                  "self-reported safety-adjacent number, on ZERO independent/official leaderboards -- all "
                  f"{len(community_with_safety)} hits are self-published on the fine-tuner's own HF card: "
                  "huihui-ai's Qwen2.5-0.5B/1.5B-Instruct-CensorTune (0% harmful-instruction pass-rate on a "
                  "community-hosted HarmBench-behaviors variant, 320 prompts, own TestPassed.py script) and "
                  "DreamFast's qwen3-4b-heretic (a 3/100-vs-100/100 refusal count from the Heretic abliteration "
                  "tool's own undisclosed 100-prompt trial log, not a named external benchmark). "
                  "All other community fine-tunes checked (huihui/mlabonne abliterated Qwen3 variants, "
                  "Josiefied-Qwen2.5-1.5B-abliterated, Llama-3.2-3B-Instruct-abliterated, "
                  "gemma-2-2b-it-abliterated, Phi-4-mini-instruct-abliterated, the 3 AIPlans TinyLlama "
                  "SafeRLHF DPO/IPO/ORPO variants, the Robust-Decoding gemma2 hh-dpo variant, and the "
                  "near-empty Shortmund09 card) have ZERO published safety numbers of any kind. "
                  "Capability numbers ARE published for several community fine-tunes via the Open LLM "
                  "Leaderboard v2 exact-repo-id join (Josiefied-Qwen2.5-1.5B-abliterated, "
                  "gemma-2-2b-it-abliterated) and via self-reported re-eval tables (Llama-3.2-3B-Instruct-"
                  "abliterated, both CensorTune repos)."),
}

json.dump(counts, open(WS / "sa3/census_counts_out.json", "w"), indent=2)

print("=" * 70)
print(f"Panel size N (excluding sealed) = {N}")
print(f"(a) exact-checkpoint, ANY published safety number: {a_exact_any_safety} / {N}")
print(f"(b) allowing upstream-official numbers too:        {b_upstream_any_safety} / {N}")
print(f"(c) over-refusal number -- exact: {c_overrefusal_exact} / {N}; upstream-or-exact: {c_overrefusal_upstream} / {N}")
print("(d) capability benchmark coverage (exact / upstream-or-exact):")
for b, v in d_capability.items():
    print(f"    {b}: {v['exact']} / {v['upstream_or_exact']}  (N={N})")
print("(e) per-benchmark coverage fraction (exact | upstream):")
for b, v in e_per_benchmark_coverage.items():
    print(f"    {b}: {v['fraction_exact']} | {v['fraction_upstream']}")
print(f"(f) community fine-tunes have ZERO published safety numbers overall? {community_zero_safety}")
print(f"    community fine-tune repos total: {len(community_repos)}; WITH a safety number: {community_with_safety}")
print("=" * 70)
