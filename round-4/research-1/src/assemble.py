"""Assemble research_out.json, research_report.md and the struct-out from the
three subagent outputs (sa1/sa2/sa3) plus the kill-check (step5)."""
import json
import re
from pathlib import Path

WS = Path(__file__).parent
IT3 = Path("/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_3")
sa1 = json.loads((WS / "sa1/sa1_out.json").read_text())
sa2 = json.loads((WS / "sa2/sa2_out.json").read_text())
sa3 = json.loads((WS / "sa3/sa3_out.json").read_text())
kc = json.loads((WS / "step5/kill_check.json").read_text())
bib_diff = json.loads((WS / "step5/bib_diff_final.json").read_text())
bib_text = (WS / "references.bib").read_text()
BIB_KEYS = set(re.findall(r"^@\w+\{([^,]+),", bib_text, re.M))

# ---------------------------------------------------------------- sources
KILL_SOURCES = [
    {"url": "https://arxiv.org/abs/2609.06951", "title": "Steering Interference Reflects the Model's Defaults, Not the Behavior Directions",
     "authors": ["Srikanth Malla", "Chiho Choi", "Joon Choi"], "year": 2026,
     "summary": "Kill-check hit (NARROWS C1): a norm-matched, content-free steer moves the same behaviours in the same order as real steers (rank corr 0.90); the pull toward refusal is strongest below 10B.",
     "passages": [{"quote": "moves the same behaviors in the same order as real steers do (rank correlation 0.90)", "locator": "Contributions, p.2"},
                  {"quote": "the pull toward defaults strongest below 10B parameters and weakening in each family", "locator": "Abstract"}]},
    {"url": "https://arxiv.org/abs/2609.16204", "title": "Decoy Direction Optimization: A Post-Hoc Defense Against LLM Abliteration",
     "authors": ["Aashiq Muhamed", "Mona T. Diab", "Virginia Smith"], "year": 2026,
     "summary": "Kill-check hit (NARROWS C2/C5): a post-hoc weight edit corrupts difference-in-means refusal-direction estimators across six families, so DIM-based self-ablation or weight-path scores can be gamed.",
     "passages": [{"quote": "ablation attacks rely on contrastive estimators to find the refusal direction", "locator": "Abstract"}]},
    {"url": "https://arxiv.org/abs/2609.14759", "title": "Refusal Reads Only a Slice of What the Model Knows: Harm-Keyed Routing and Its Exceptions Across Model Families",
     "authors": ["Orion Reblitz-Richardson"], "year": 2026,
     "summary": "Kill-check hit (ADJACENT C1): harm-to-refusal routing on 4 models / 3 families; the causal result is single-model (OLMo-3); no benchmark correlation.",
     "passages": [{"quote": "The central result is causal and comes from one model, OLMo-3.", "locator": "Abstract"}]},
    {"url": "https://arxiv.org/abs/2609.19366", "title": "The Role of Fine-grained Harm Signals in LLM Safety",
     "authors": ["Soyeon Park", "Seogyeong Jeong", "Sunwoo Kim", "Alice Oh"], "year": 2026,
     "summary": "Kill-check hit (ADJACENT C1): steering category residuals induces refusal with model-dependent strength on 3 models; no benchmark correlation.",
     "passages": [{"quote": "Whether category residuals induce refusal also varies across categories, but this category-wise pattern is more model-dependent.", "locator": "Abstract"}]},
    {"url": "https://arxiv.org/abs/2607.00572", "title": "HARC: Coupling Harmfulness and Refusal Directions for Robust Safety Alignment",
     "authors": ["Shei Pern Chua", "Hao Wu", "Qianli Ma", "Fang-Zhao Wu"], "year": 2026,
     "summary": "Kill-check hit (ADJACENT C1): harmfulness-refusal geometry across five architectures, used for a defense; no per-model benchmark correlation found.",
     "passages": []},
    {"url": "https://arxiv.org/abs/2604.27401", "title": "Perturbation Probing: A Two-Pass-per-Prompt Diagnostic for FFN Behavioral Circuits in Aligned LLMs",
     "authors": None, "year": 2026,
     "summary": "C5 nearest miss (unchanged): the FFN/Skip ratio predicts ablation effectiveness across 13 models / 4 families, not a safety benchmark.",
     "passages": []},
    {"url": "https://failurefirst.org/research/reports/74-abliteration-jailbreak-orthogonality/", "title": "Report 74: Abliteration Resistance and Jailbreak Resistance Are Orthogonal Defense Dimensions",
     "authors": None, "year": 2026,
     "summary": "Adverse prior for C1/C2 (grey literature, carried from iter-3): abliteration resistance vs jailbreak refusal, Spearman rho=-0.003, n=16.",
     "passages": []},
]


def norm_authors(a):
    if a is None:
        return None
    if isinstance(a, list):
        return a or None
    parts = [x.strip() for x in re.split(r",| and ", str(a)) if x.strip()]
    return parts or None


def norm_year(y):
    m = re.search(r"(19|20)\d\d", str(y)) if y is not None else None
    return int(m.group(0)) if m else None


sources, by_url, LOCAL = [], {}, []
for group in (sa1["sources"], sa2["sources"], sa3["sources"], KILL_SOURCES):
    for s in group:
        url = s["url"]
        if url.startswith("local:"):
            LOCAL.append({"path": url[len("local:"):], "title": s["title"], "summary": s["summary"]})
            continue
            loc = url[len("local:"):].split(",")[0].strip()
            base = "/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/"
            if loc.startswith("data/"):
                loc = "iter_3/gen_art/gen_art_dataset_1/" + loc
            url = "file://" + base + loc
        k = url.replace("/pdf/", "/abs/").rstrip("/")
        if k in by_url:
            continue
        idx = len(sources) + 1
        by_url[k] = idx
        passages = [{"quote": p["quote"], "locator": p.get("locator")} for p in (s.get("passages") or s.get("supporting_passages") or [])
                    if p.get("quote") and len(p["quote"].split()) <= 50]
        sources.append({"index": idx, "url": url, "title": s["title"], "summary": s["summary"],
                        "authors": norm_authors(s.get("authors")), "year": norm_year(s.get("year")),
                        "supporting_passages": passages})


PFX = json.loads((WS / "step5/passage_fixes.json").read_text()) if (WS / "step5/passage_fixes.json").exists() else {}
_old = {s["index"]: s["url"] for s in sources}
for s in sources:
    fx = PFX.get(str(s["index"]))
    if fx is not None:
        s["url"] = fx["url"]
        s["supporting_passages"] = [{"quote": q["quote"], "locator": q.get("locator")} for q in fx["passages"]]


def S(frag):
    """citation index of the first source whose url contains frag"""
    for s in sources:
        if frag in s["url"] or frag in _old[s["index"]]:
            return s["index"]
    raise KeyError(frag)


# ---------------------------------------------------------------- positioning
grader = sa1["positioning_grader_refusal"]
grader = grader.replace(
    "\\citet{Huang2025} deliberately select less safety-restricted evaluator backbones so that they \"do not refuse evaluation tasks involving harmful content,\"",
    "\\citet{Huang2025} motivate GuidedEval partly by letting users pick evaluators that are less restrictive in safety constraints, \"thus ensuring evaluators do not refuse evaluation tasks involving harmful content,\"")
grader = grader.replace(
    "add affirmative prefilling to their judge prompt because the underlying model otherwise declines to grade sensitive completions",
    "add affirmative prefilling to their judge \"to handle sensitive content\"")
assert "do not refuse" in grader and "to handle sensitive content" in grader, "grader paragraph patch failed"

eco = ("As of 2026-09-21, 15 of the 36 sub-4B checkpoints in our panel carry any published safety number, and none of those numbers "
       "comes from a dedicated safety leaderboard: HELM Safety, AIR-Bench, SALAD-Bench and TrustLLM list none of the 36, and we found no "
       "JailbreakBench or HarmBench entry for any of them. Six of the 15 are the developer's own report or card (Qwen3-4B and Qwen3-4B-SafeRL, "
       "the latter evaluated by the team that trained it; Gemma-2-2B-it \\citep{Riviere2024}; Phi-4-mini and Phi-3.5-mini \\citep{Abouelenin2025}; "
       "OLMo-2-1B). Six appear only as baseline rows in another vendor's or a third-party table \\citep{Abouelenin2025,Deniz2025}. The remaining three are "
       "self-reported by community fine-tuners on their own cards. Only 5 of 36 have an XSTest-style over-refusal number (7 if WildJailbreak benign-prompt "
       "refusal is counted). Capability numbers are commoner but harness-dependent: MMLU-family 17/36, GSM8K 9/36, developer-run Arena-Hard 8/36, "
       "Open LLM Leaderboard v2 8/36. None of the 15 community fine-tunes (abliterated, CensorTune, SafeRLHF variants) has an independently measured "
       "safety number. The checkpoints a downloader actually meets are, as a rule, unmeasured. This is the gap a parent-free, few-prompt score is meant to fill.")

positioning = {"grader_refusal": grader, "incumbents": sa2["positioning_incumbents"], "ecosystem": eco}
for name, para in positioning.items():
    for group in re.findall(r"\\cite[tp]?\{([^}]+)\}", para):
        for k in group.split(","):
            assert k.strip() in BIB_KEYS, f"{name}: missing bib key {k}"

# ---------------------------------------------------------------- census
sa3_counts = sa3["counts"]
provenance = {
    "developer_own_report_or_card": ["Qwen/Qwen3-4B (Qwen3Guard report 2510.14276 Table 10 pre-RL row)",
                                     "Qwen/Qwen3-4B-SafeRL (own card; NOT_INDEPENDENT: Qwen3Guard-Gen-4B was the RL reward, eval by Qwen3-235B judge + WildGuard)",
                                     "unsloth/gemma-2-2b-it (mirror of google/gemma-2-2b-it; Gemma 2 report Tables 15/18)",
                                     "microsoft/Phi-4-mini-instruct (own report 2503.01743 Tables 10-12)",
                                     "microsoft/Phi-3.5-mini-instruct (same developer, Phi-4-mini report comparison)",
                                     "allenai/OLMo-2-0425-1B-Instruct (own card, Tulu-3 'Safety' composite 87.6)"],
    "third_party_table_only": ["Qwen/Qwen2.5-0.5B-Instruct (huihui-ai CensorTune card baseline row, community harmbench variant)",
                               "Qwen/Qwen2.5-1.5B-Instruct (AI2 OLMo-2-1B card row 'Safety'=77.6; CensorTune card baseline row)",
                               "Qwen/Qwen2.5-3B-Instruct (Phi-4-mini report XSTest + defect-rate tables)",
                               "unsloth/Llama-3.2-1B-Instruct (aiXamine 2504.14985)",
                               "unsloth/Llama-3.2-3B-Instruct (Phi-4-mini report; aiXamine)",
                               "HuggingFaceTB/SmolLM2-1.7B-Instruct (AI2 OLMo-2-1B card row 'Safety'=52.4)"],
    "community_self_reported": ["huihui-ai/Qwen2.5-0.5B-Instruct-CensorTune (0/320 on huihui-ai/harmbench_behaviors, own script)",
                                "huihui-ai/Qwen2.5-1.5B-Instruct-CensorTune (0/320, same)",
                                "DreamFast/qwen3-4b-heretic (Heretic tool trial log 3/100 refusals; undisclosed prompt set)"],
}
counts = dict(sa3_counts)
counts["safety_number_provenance_of_the_15"] = {k: len(v) for k, v in provenance.items()}
counts["overrefusal_including_wildjailbreak_benign_refusal"] = 7
counts["community_finetunes_with_independent_safety_number"] = 0
counts["community_finetunes_with_self_reported_safety_number"] = 3
counts["orchestrator_corrections"] = [
    "sa3 summary text said 2/15 community fine-tunes carry a safety number; its own row list and f_community_finetune_repos_WITH_a_safety_number give 3 (incl. DreamFast heretic self-reported 3/100 refusals). 3 is used.",
    "sa3 positioning said every number comes from a report's/card's OWN table; provenance split shows 6 own-developer, 6 third-party-only, 3 community self-reported. Paragraph rewritten.",
    "unsloth/Llama-3.2-1B-Instruct MMLU=68.2 is transcribed correctly from the Falcon3-1B-Instruct card comparison table (raw/sa3/cards/tiiuae_Falcon3-1B-Instruct.md, column 'Llama-3.2-1B') but is implausibly high for a 1B model and harness-dependent; do NOT use it as a capability ground-truth value without a second source.",
    "Rows filed under HELM_XSTest_overrefusal are XSTest run by the Phi-4-mini team (2503.01743 Table 12), NOT HELM's XSTest scenario; HELM itself covers 0/36.",
]
ecosystem_census = {"rows": sa3["rows"], "counts": counts, "safety_provenance": provenance,
                    "accessed_date": sa3.get("accessed_date", "2026-09-21"),
                    "cross_check_vs_iter3": sa3["cross_check_vs_iter3"], "blockers": sa3.get("blockers", [])}

# ---------------------------------------------------------------- must-fix trace
review = json.loads((IT3 / "review_paper/review_paper/.terminal_claude_agent_struct_out.json").read_text())
items = []
for it in review.get("weaknesses") or review.get("issues") or []:
    items.append(it)
if not items:  # fall back to scanning the file text by line
    lines = (IT3 / "review_paper/review_paper/.terminal_claude_agent_struct_out.json").read_text().splitlines()
    items = [json.loads(lines[i - 1].strip().rstrip(",")) for i in (24, 25, 29)]
else:
    lines = (IT3 / "review_paper/review_paper/.terminal_claude_agent_struct_out.json").read_text().splitlines()
    items = [json.loads(lines[i - 1].strip().rstrip(",")) for i in (24, 25, 29)]


def short(t, n=45):
    w = t.split()
    return " ".join(w[:n]) + (" ..." if len(w) > n else "")


must_fix_trace = [
    {"review_line": 24, "review_category": items[0]["category"], "review_quote": short(items[0]["description"]),
     "fix_fields": ["positioning.grader_refusal", "judge_refusal_prior_art", "guidedbench_verdict"],
     "resolution": "GuidedBench phrase FOUND near-verbatim (Sec 5.2, p.9) but as a design motivation, with no measured refusal rate; 2609.10594 measures evaluator-vs-human agreement (StrongReject 89.5% acc / 89.8% F1 / 8.4% FPR on JailbreakQR) and never discusses grader refusal. The paragraph now says QUANTIFY per judge x framing, drops the 'overestimated safety' claim, and notes that a literal 1,1,1 is legitimate for a real refusal."},
    {"review_line": 25, "review_category": items[1]["category"], "review_quote": short(items[1]["description"]),
     "fix_fields": ["ecosystem_census", "positioning.ecosystem"],
     "resolution": "Dated census of 36 panel checkpoints x 12 benchmarks (2026-09-21): 15/36 have any safety number, 0 from any safety leaderboard; TrustLLM/AIR-Bench/SALAD/HELM-Safety = 0/36; MMLU 17, GSM8K 9, Arena-Hard 8 (developer-run), OLB v2 8. The iter-3 HELM n=0 / OLB n=16 claims agree; the '2 sub-4B / 6.7x' figures belong to a different, wider 81-model HELM limb."},
    {"review_line": 29, "review_category": items[2]["category"], "review_quote": short(items[2]["description"]),
     "fix_fields": ["incumbent_table", "positioning.incumbents", "citation_fixes", "arditi_reconciliation"],
     "resolution": "9-row incumbent table, each row with a comparable/non-comparable reason (all non-comparable). OR-Bench is single-turn (Cui2024), and Kaushik2025 is an unrelated weight-subspace paper, so the citation is removed. TAR covers fine-tuning attacks only: there is no 'adapter rank' or 'chat-template' in the paper, and the 500-step plateau is an SFT attack on a TAR model. Arditi is softened, and the reconciliation reason is quoted from iter_3 evaluation README:57."},
]

# ---------------------------------------------------------------- answer
c = S
answer = (
    f"(a) Judge refusal is known, not new. GuidedBench motivates its evaluator design partly by letting users pick less safety-restricted judges, "
    f"'thus ensuring evaluators do not refuse evaluation tasks involving harmful content' (Sec 5.2), but it prints no evaluator-refusal rate; its measured "
    f"result is a 76.03-88.28% cut in inter-evaluator variance [{c('2502.16903')}]. AdvPrefix adds affirmative prefilling to its judge 'to handle sensitive content' [{c('2412.10321')}]. "
    f"2609.10594 compares six evaluators with human labels: StrongReject reaches 89.5% accuracy / 89.8% F1 / 8.4% FPR, JADES does best, and grader refusal is never discussed [{c('2609.10594')}]. "
    f"JailJudge reports GPT-4-judge F1 of 55% in complex scenarios [{c('2410.12855')}]; StrongREJECT prints no grader-refusal number [{c('2402.10260')}]. "
    f"Our contribution is therefore a per-judge x framing quantification on a fixed 60+60 calibration set.\n\n"
    f"(b) No incumbent is comparable to a parent-free, leave-one-lineage-out, few-prompt screen. "
    f"AMS's r=-0.546 (p=.043, n=14) is in-sample; its 71% (10/14) holds out only the threshold [{c('2608.05578')}]. "
    f"RAS needs a per-family reference model, a calibration set and measured ASR [{c('2606.25750')}]. Skin-Deep needs the base model and prints no coefficient (n=7, qualitative) [{c('2606.22676')}]. "
    f"N-GLARE needs 7000+ trajectories and has no cross-model headline tau [{c('2511.14195')}]. "
    f"The only genuine cross-family holdout, Hurtado's audit (AUROC 0.95; LOFO balanced accuracy 0.89), needs a parent checkpoint and is a binary abliteration detector [{c('2607.01854')}]. "
    f"Leong, Li and Labunets are per-model/single-lineage [{c('2502.13946')}, {c('2603.24543')}, {c('2608.25390')}]; HRCI is disclaimed as 'not a safety score' [{c('2606.16349')}].\n\n"
    f"(c) OR-Bench is a single-turn benchmark (80K / 1K hard / 600 toxic prompts) [{c('2405.20947')}]; cited Kaushik2025 is unrelated [{c('2512.05117')}]. "
    f"TAR resists gradient fine-tuning attacks and never tests training-free edits [{c('2408.00761')}]. Arditi shows erasing one direction removes refusal and adding it induces refusal [{c('2406.11717')}], "
    f"so a SafeRL shift in a different direction inside a shared subspace is consistent with Arditi; for the multi-direction view see [{c('2602.02132')}].\n\n"
    f"(d) As of 2026-09-21, 15/36 panel checkpoints have any safety number and 0 are covered by any safety leaderboard; TrustLLM covers mostly 7B+/API models [{c('2401.05561')}]. "
    f"Of the 15, 6 numbers come from the developer's own reports [{c('2503.01743')}, {c('2408.00118')}, {c('OLMo-2-0425-1B-Instruct')}], "
    f"6 only from third-party tables [{c('2504.14985')}], and 3 are community self-reports [{c('0.5B-Instruct-CensorTune')}, {c('1.5B-Instruct-CensorTune')}, {c('qwen3-4b-heretic')}]; other abliterated cards print only capability [{c('Llama-3.2-3B-Instruct-abliterated')}]. "
    f"SafeRL's numbers are not independent: Qwen3Guard was its reward [{c('2510.14276')}, {c('Qwen3-4B-SafeRL')}]. Capability coverage: MMLU 17, GSM8K 9, Arena-Hard 8 [{c('2505.09388')}, {c('2412.15115')}, {c('blog/falcon3')}, {c('Falcon3-1B-Instruct')}, {c('2407.09276')}, {c('2502.02737')}, {c('SmolLM2-360M')}, {c('SmolLM2-1.7B')}, {c('SmolLM3-3B')}, {c('EuroLLM-1.7B')}]; sealed Granite/StableLM families publish no size-specific safety table [{c('rivista.ai')}, {c('2402.17834')}], and TrustLLM's leaderboard lists no panel model [{c('leaderboard.html')}].\n\n"
    f"(e) Kill-check: nothing kills C1/C2/C5; Report 74's rho=-0.003 (n=16) stays the adverse prior [{c('failurefirst')}] and C5's nearest miss predicts ablation effect, not benchmarks [{c('2604.27401')}]. Content-free steers move refusal like real ones, most strongly below 10B, so C1 must be net of a random steer [{c('2609.06951')}]. "
    f"Decoy edits can fool DIM-based C2/C5 [{c('2609.16204')}]. Other hits are adjacent [{c('2609.14759')}, {c('2609.19366')}, {c('2607.00572')}]. "
    f"Confidence: high for (a)-(c); medium for (d) (gated/JS pages)."
)
used = {int(x) for x in re.findall(r"\[(\d+)", answer)} | {int(x) for grp in re.findall(r"\[([\d, ]+)\]", answer) for x in grp.split(",")}
assert all(1 <= u <= len(sources) for u in used)
unc=[s["index"] for s in sources if s["index"] not in used]
assert not unc, unc
assert all(s["url"].startswith("http") for s in sources)

title = "Fix citations, compare rivals, count safety scores"
summary = (
    "LITERATURE MUST-FIXES CLOSED + DATED ECOSYSTEM CENSUS + C1/C2/C5 KILL-CHECK. Files: research_out.json (keys: positioning{grader_refusal,incumbents,ecosystem} paste-ready LaTeX; "
    "judge_refusal_prior_art; incumbent_table (9 rows); table1_rows; citation_fixes; arditi_reconciliation; ecosystem_census (102 rows, counts, provenance); kill_check; must_fix_trace; bib_diff), "
    "references.bib (93 entries = 83 + 10 via Semantic Scholar, 0 dup keys/ids), research_report.md, raw/ grep captures. "
    "(1) JUDGE REFUSAL: GuidedBench 2502.16903 (Huang2025) phrase 'do not refuse evaluation tasks involving harmful content' FOUND (Sec 5.2 p.9) but as a design motivation, with NO measured rate; "
    "headline = 76.03-88.28% variance cut. Mu2026 2609.10594: StrongReject 89.5% acc / 89.8% F1 / 8.4% FPR vs humans; JADES best; no grader-refusal discussion. JailJudge (Liu2024) GPT-4 judge F1 55%; "
    "AdvPrefix (Zhu2024) judge prefilling 'to handle sensitive content'. Frame as QUANTIFY per judge x framing; drop 'overestimated safety'. "
    "(2) INCUMBENTS all comparable=false: AMS r=-0.546 in-sample, 71% = threshold-only LOO; RAS per-family calibration; GFS needs base, no coefficient; N-GLARE never quote Table-2 taus; "
    "Hurtado2026 AUROC 0.95 + LOFO BA 0.89 is the ONLY real cross-family holdout but parent-dependent and binary; HRCI 'not a safety score'; Li2026 slope null for Qwen 3B (p=.696). "
    "(3) CITATIONS: OR-Bench (Cui2024) single-turn; Kaushik2025 is an unrelated weight-subspace paper, so REMOVE it; TAR = fine-tuning attacks only, 'adapter rank'/'chat-template' absent (0 hits), the 500-step plateau is an SFT attack; "
    "Arditi softened; the reconciliation reason is quoted from iter_3 gen_art_evaluation_1/README.md:57 (bug fix: 'first' angle was the largest principal angle). "
    "(4) CENSUS 2026-09-21, N=36: 15/36 have any safety number (6 own-developer, 6 third-party-only, 3 community self-reports); 0/36 on HELM Safety/AIR-Bench/SALAD/TrustLLM/JailbreakBench/HarmBench; "
    "over-refusal 5/36 (7 incl. WildJailbreak benign); MMLU 17, GSM8K 9, Arena-Hard 8 (developer-run), OLB v2 8; 0/15 community fine-tunes independently measured. "
    "SafeRL numbers NOT_INDEPENDENT. CAUTION: Llama-3.2-1B MMLU=68.2 (Falcon3 card) is implausible. iter-3 claims agree; the '2 sub-4B / 6.7x' figures are from a different, 81-model HELM limb. "
    "(5) KILL-CHECK closed=false: C1 ADJACENT, NARROWED by Malla2026 2609.06951 (content-free steers pull toward refusal, rank corr 0.90, strongest <10B), so C1 must subtract a norm-matched random steer; "
    "C2/C5 get a gameability caveat from Muhamed2026 DDO 2609.16204; C5 still NEW."
)[:4990]
fq = [
    "Does C1 (harm-to-refusal gain) keep any cross-family signal once a norm-matched random-direction steer is subtracted, given 2609.06951 finds the generic pull toward refusal strongest below 10B?",
    "Per judge x framing, how much of the 1,1,1 mass on the 60 known-compliant items is grader refusal versus rubric misreading, and does affirmative prefilling (AdvPrefix-style) remove it?",
    "Can the 6 developer-own safety numbers and the 5-7 over-refusal numbers serve as an external anchor (n<=7) for even a sign test of the top metrics, or is the in-house two-refusal-rate fallback the only viable ground truth?",
]

research_out = {
    "title": title, "summary": summary, "answer": answer, "sources": sources, "follow_up_questions": fq,
    "positioning": positioning,
    "judge_refusal_prior_art": sa1["judge_refusal_prior_art"], "guidedbench_verdict": sa1["guidedbench_verdict"],
    "incumbent_table": sa2["incumbent_table"], "table1_rows": sa2["table1_rows"],
    "citation_fixes": sa1["citation_fixes"], "arditi_reconciliation": sa1["arditi_reconciliation"],
    "ecosystem_census": ecosystem_census, "kill_check": kc, "must_fix_trace": must_fix_trace,
    "bib_diff": bib_diff, "local_evidence": LOCAL, "accessed_date": "2026-09-21",
    "blockers": {"sa1": sa1.get("blockers", []), "sa2": sa2.get("blockers", []), "sa3": sa3.get("blockers", [])},
}
(WS / "research_out.json").write_text(json.dumps(research_out, indent=1, ensure_ascii=False))

struct = {"title": title,
          "layman_summary": "Checks the research literature so the paper's claims about earlier safety-scoring methods, AI judges and missing public safety scores for small models are accurate and properly cited.",
          "summary": summary, "out_expected_files": {"output": "research_out.json"}, "upload_ignore_regexes": [],
          "answer": answer, "sources": sources, "follow_up_questions": fq}
(WS / ".terminal_claude_agent_struct_out.json").write_text(json.dumps(struct, indent=1, ensure_ascii=False))

# ---------------------------------------------------------------- report
md = [f"# {title}\n", "Accessed 2026-09-21.\n", "## Answer\n", answer, "\n## Positioning paragraphs (paste-ready LaTeX)\n"]
for k, v in positioning.items():
    md += [f"### {k}\n", v, ""]
md += ["## Incumbent Table 1\n", "| incumbent | access | n | holdout | headline | comparable |", "|---|---|---|---|---|---|"]
for r in sa2["table1_rows"]:
    md.append(f"| {r['incumbent']} | {r['access']} | {r['n']} | {r['holdout']} | {r['headline']} | {r['comparable']} |")
md += ["\n## Citation fixes\n"] + [f"- **{x['id']}** ({x['bib_key']}): {x['corrected_text']}" for x in sa1["citation_fixes"]]
md += ["\n## Ecosystem census counts\n", "```json", json.dumps(counts, indent=1), "```", "\n### Safety-number provenance\n"]
for k, v in provenance.items():
    md += [f"- **{k}** ({len(v)}): " + "; ".join(v)]
md += ["\n## Kill-check\n"] + [f"- **{k}**: {v['verdict']}. {v['text']}" for k, v in kc["verdicts"].items()]
md += ["\n## Must-fix trace\n"] + [f"- review line {m['review_line']} -> {', '.join(m['fix_fields'])}: {m['resolution']}" for m in must_fix_trace]
md += ["\n## Sources\n"] + [f"[{s['index']}] {s['title']} - {s['url']}" for s in sources]
(WS / "research_report.md").write_text("\n".join(md))
print("sources", len(sources), "answer words", len(answer.split()), "summary chars", len(summary))
