"""Assemble research_out.json, research_report.md and .terminal_claude_agent_struct_out.json
from the merged artifacts (novelty_table.json, novelty_A.json kill_check, bib_fixes.json,
citation_corrections.json, number_ledger.json, scanner_pin.json, references.bib)."""
import json
import re
from collections import Counter
from pathlib import Path

from sources_def import SOURCES

WS = Path(__file__).parent
J = lambda f: json.loads((WS / f).read_text())

TITLE = "Prior-art check for 16 safety-metric candidates"
LAYMAN = ("Checks whether each of 16 proposed cheap safety checks for AI models has already been published, "
          "and repairs the study's reference list and quoted numbers.")


def ledger_block():
    if not (WS / "number_ledger.json").exists():
        return [], Counter(), []
    led = J("number_ledger.json")
    recs = led if isinstance(led, list) else led.get("records", led.get("ledger", []))
    c = Counter(r.get("status", "?").split()[0].split("(")[0].strip().upper() for r in recs)
    bad = [r for r in recs if not str(r.get("status", "")).upper().startswith(("CONFIRMED", "INTERNAL"))]
    return recs, c, bad


def main():
    table = J("novelty_table.json")
    kc = J("novelty_A.json")["kill_check"]
    fixes = J("bib_fixes.json")
    cc = J("citation_corrections.json")
    pin = J("scanner_pin.json")
    bibtxt = (WS / "references.bib").read_text()
    bibent = J("bib_entries.json")
    recs, lc, bad = ledger_block()
    ledger_summary = J("ledger_summary.json") if (WS / "ledger_summary.json").exists() else {}

    verdicts = Counter(r["verdict"] for r in table)
    answer = f"""BOTTOM LINE (2026-09-21). None of the 16 candidates is published as a single-model, parent-free safety score that has been correlated with benchmark safety across architecture families. The kill-check on the leading conjecture comes back OPEN (closed = false). Row verdicts: {verdicts['NEW']} NEW (C5, C14, C15), {verdicts['ADJACENT']} ADJACENT and {verdicts['PUBLISHED']} PUBLISHED (C9, C16). Four bibliography findings matter more for the paper than the planner expected: (a) the '0.35 published Jorak threshold' is our own pre-registered simulation value, and Jorak ships 0.5 [7, 37] (origin traced in this artifact's scanner_pin.json to the run's own config file iter_1/gen_art/gen_art_experiment_2/flab/config.py, line 74); (b) 20 of the 30 hand-typed references in the iteration-2 draft carry fabricated first-author names, checked against the arXiv API [36] (row-by-row audit in citation_corrections.json); (c) two of the seven planner fix-list defects (Casper's 'eprint 0106.36590' and AMS's 'DOI fragment 2026.37040') are misreadings of DOIs that are actually correct [29, 30]; (d) the 'Tan et al. 2406.09289' citation is a misattribution. 2406.09289 is Ball, Kreuter & Rimsky, and the steering-reliability paper is Tan et al. 2407.12404 [25, 26].

1. KILL-CHECK: IS THE LEADING CONJECTURE STILL NOVEL? Question: does any paper compute a per-model harm-to-refusal CAUSAL quantity (steering gain, ablation effect, patching, weight-path gain) and correlate it with benchmark safety across models? Answer: no. The search ran 14 targeted queries and a forward citation chase: 1,061 papers citing Arditi 2406.11717, 74 citing Zhao 2507.11878, and none yet indexed for 2606.16349. Of 1,006 titles from 2025 onward, 156 were filtered, 25 abstracts screened and 6 PDFs grepped. Causal refusal interventions appear only as within-model mechanism evidence: 13 models in Arditi [1], 3 models in Zhao [2], and anchor checkpoints plus one trajectory in HRCI [33]. The closest hit is grey literature: Failure-First Report 74 ranks 16 models by resistance to weight abliteration and correlates that with jailbreak refusal, and finds no relationship ('rho = -0.003') [3]. It misses the conjecture because it is not peer reviewed, it measures third-party abliteration success rather than a gain keyed to the model's own harm direction, and it has no over-refusal arm. The closest arXiv hit is LVS (2606.08044), a causal per-model score built from UNDIRECTED latent perturbations and never correlated with a benchmark [4]. AMS [27] and RAS [20] are confirmed NON-causal. Required positioning sentence: "{kc['required_positioning_sentence']}" What remains novel: (1) a causal quantity keyed to the model's OWN cross-fitted harm direction; (2) parent-free with about 16 prompts; (3) a two-sided target, harmful-refusal AND over-refusal, under which a blanket refuser loses; (4) held-out cross-family validation; (5) anisotropy-matched random-direction controls. Implication: Report 74's null result is prior evidence AGAINST a generic 'ablation robustness tracks safety' story. It must be cited as the adverse prior, and a positive C1/C2 result must be shown to differ from it.

2. PER-CANDIDATE VERDICTS (full records with quotes, locators, queries and positioning sentences are in novelty_table.json).
Family I/II, causal (C1-C5). C1 harm-to-refusal gain: ADJACENT. Harm-direction steering elicits different refusal rates on 3 models, but only as a mechanism contrast [2]; LVS is a cross-model score, but its perturbation is undirected [4]. C2 self-ablation sensitivity: ADJACENT, and closest to PUBLISHED. Arditi ablates the refusal direction in 13 models without ranking them [1], and false-refusal vector ablation is a single-model tool [42]; Report 74 does the cross-model correlation in generic form and finds a null [3]. The claim must be narrowed to the margin-based, two-sided, random-direction-controlled form. C3 twin patching flip depth: ADJACENT. Benign-twin activation substitution exists as a jailbreak on mainly one model and is never reduced to a per-model scalar [5]. C4 writer capacity: ADJACENT. Jorak already reads o_proj/down_proj against the refusal axis without a reference model, but only to assign a provenance label [6, 7]. C4's novelty is the graded, random-direction z-scored write along the model's own axis and its benchmark validation. C5 weight-path gain: NEW. The nearest miss predicts ablation effectiveness from an FFN/Skip ratio across 13 models and 4 families, but that ratio mixes weights and activations and the target is not a benchmark [8].
Family III/IV, attribution and dynamics (C6-C11). C6 DLA concentration: ADJACENT. Arditi's component attribution is a single-model case study [1]; Ships/Sahara covers two same-lineage models [9]. C7 attention mass on differing tokens: ADJACENT. Attention to sensitive words correlates with ASR within the Llama-2 family only [10]. C8 input-gradient share: ADJACENT. GradSafe uses parameter gradients, not input-token gradients [11]. C9 template-site share: PUBLISHED. Leong et al. compute a template-region normalised indirect effect across six chat models from four families, normalised 'for a fair cross-model comparison', and tie template anchoring to vulnerability [12]. The caveat is that the safety link is qualitative, with no numeric per-model correlation with a benchmark, so C9 becomes a REPLICATION row. C10 area between depth curves: ADJACENT. Both curves already exist on the same 3 models [2], and harm-only trajectories exist across 4 families [13]; only the area aggregation and its use as a ranking are new. C11 first-8-token commitment: ADJACENT. Every close hit needs a parent or counterpart model: per-token KL against the base model [14] and instruct/reasoning pairs [15]. The parent-free single-checkpoint version is the residual novelty.
Family V-VIII, discrimination, invariance, metamodel, geometry, steering (C12-C16). C12 twin discrimination: ADJACENT. LatentBiopsy reports harmful-vs-XSTest-twin AUROC = 1.000 per checkpoint but has no plain-benign ratio [16]; Entanglement Wall declines to use twin separation for ranking [17]. C13 presentation invariance: ADJACENT. A wrapped-vs-plain AUROC drop (0.936 to 0.803) is reported per model, but framed as a validity critique [18]. C14 ridge metamodel on 24 or fewer depth-by-site features: NEW. GFS uses a FIXED l/L depth weight [19], RAS a fixed average with a hand-set logistic [20], and the log-likelihood model map uses outputs rather than activations [41]. C15 late-layer effective rank: NEW. Effective rank separates models only on capability [21, 22]. The orchestrator's adversarial pass found a new nearest miss that must be cited: Labunets links the stable rank of refusal residuals and gradients to ablation robustness, in one OLMo-2-1B lineage [23]. C16 self-steering slope: PUBLISHED as a comparator. Li fits per-model ASR dose-response slopes against steering/refusal-direction alignment and compares 6 models ('becomes progressively steeper with model size') [24]. Steering unreliability is documented by Tan et al. [25]. Orchestrator correction: the published quantity is gamma_1, the special case v = r_hat of C16, and it is NOT correlated with a safety benchmark.

3. CLAIMABLE NOVELTY AND SCREEN IMPLICATIONS. Only C5, C14 and C15 may be called new, each in a precise scope. C5: 'a weights-only harm-to-refusal path gain as a cross-family safety score' [8]. C14: 'a FITTED metamodel over depth-by-site internal features, as opposed to fixed-weight aggregations' [19, 20]. C15: 'late-layer dispersion validated against two-sided safety benchmarks', citing [23] as the nearest miss. C1-C4, C6-C8 and C10-C13 may be called new only as parent-free, few-prompt, cross-family SAFETY SCORES; each is an established single-model mechanism quantity. Screen status changes: C9 becomes a replication of Leong et al. [12]; C16 is comparator-only [24]; C2 must cite Report 74's null as the adverse prior [3]; C4 must cite Jorak [6] and state that the weight read is not new; C11 is the only candidate whose incumbents are all parent-DEPENDENT [14, 15], which is its strongest positioning. The incumbent map places AMS nearest to C12 [27], N-GLARE nearest to C13 [28], RAS nearest to C14 [20], and LatentBiopsy nearest to C12/C15 [16].

4. SCANNER PIN AND A CORRECTION TO THE PAPER'S HEADLINE. The Jorak repository is github.com/JolanMc/Jorak; its default-branch head is SHA 8147de343964a3cced37db71814e9007c7465a52, dated 2026-07-24 [6, 37]. The thresholds are in modelscanner/classifier/scanner.py, lines 48, 49 and 55: svd_align_severed = band_align_severed = subspace_severed = 0.5. They are calibrated on Qwen2.5-0.5B ('0.24 vs 1.00') and were never changed across the three commits that touched the file [7, 37]. A grep of all 90 text files at HEAD finds 0.35 only as a plotting width. The 0.35 the iteration-1/2 papers call 'the published separator' is this run's own BSA_PREREG_THRESHOLD, a simulation-calibrated pre-registration (iter_1 flab/config.py, line 74, quoted in scanner_pin.json), not a value from Jorak [7]. The run's BSA_w8 statistic (windowed mean pairwise |cos|) is also not Jorak's statistic, which is sigma_1/||U||_F plus a band of width L/6. So the claim '100% false-positive rate of a published scanner' must be withdrawn or re-run with Jorak's own statistic at 0.5.

5. BIBLIOGRAPHY. references.bib was regenerated by identifier: {bibent['n']} entries, no duplicate keys, author names from the arXiv API [36] and venues from Semantic Scholar. Every entry carries eprint and DOI, except the two @misc grey-literature items (Jorak, pinned to its SHA, and Report 74). Planner fix-list: (i) the duplicate LlorenteSaguer2026 key is split into LlorenteSaguer2026a (2604.18901) and LlorenteSaguer2026b (2603.27412) [16]. (ii) Casper: the iteration-2 bib already had the CORRECT DOI 10.1145/3630106.3659037 (FAccT '24, pp. 2254-2272) [29]. '0106.36590' is a substring of that DOI; the real defect was a missing eprint, and 2401.14446 has been added. (iii) Key AbuShairah2025 with author {{Abu Shairah}}, Harethah [31]. (iv) Tan2024 = 2407.12404 added; Ball2024 = 2406.09289 kept for jailbreak dynamics only [25, 26]. (v) Lan 2606.16349 [33], Fogel 2602.04653 [34], Luo 2608.09624 [18] and Rivera 2608.05086 [32] now have IDs; Rivera's merged affiliation 'Independent and UK AI Security Institute' has been removed [32]. (vi) AMS: the full DOI 10.1109/ACCESS.2026.3704057 (IEEE Access 14:91723-91737) was ALREADY present [30]. The defect was the entry type (@inproceedings for a journal); it is now @article with eprint 2608.05578 [27, 30]. (vii) Zhao2025's authors are confirmed [2]; Singh2025, Ren2024 and Zhong2025 names were corrected from arXiv. (viii) All 26 missing works were added, plus the Qwen3Guard report. That report confirms Qwen3Guard-4B-Gen was SafeRL's reward model, so it must not judge SafeRL [35]. Extra defects found: RAS's first author is 'Chang-Chieh Huang' on arXiv, not Semantic Scholar's 'Changhui Huang' [20]; N-GLARE's key is now Lin2026 [28]. CITATION-LIST AUDIT: the iteration-2 draft's hand-typed list (entries 1-30) has 20 fabricated first authors (e.g. Zhao's paper credited to 'D. Li', Joad's to 'T. B. Brown', Hurtado's to 'K. Park') and 5 wrong initials, with 4 entries correct. At least 8 titles are altered, e.g. 2603.05773 is 'Knowing without Acting', not 'Recognition Versus Execution' [36]. Fix: generate the reference list only from references.bib.

6. NUMBER LEDGER. {ledger_summary.get('prose', 'PENDING: the number-ledger pass (number_ledger.json) was still running when this version was written; every numeric claim about a cited paper must be taken as UNVERIFIED until that file exists. Numbers verified directly in this artifact: gamma_1 from -36.52 to -193.40 [24]; LatentBiopsy harmful-vs-XSTest AUROC = 1.000 [16]; Report 74 rho = -0.003 over 16 models [3]; AMS in IEEE Access 14:91723-91737 [30].')}

CONFIDENCE. High for the fix-list, the scanner pin and the reference-list audit: all were checked mechanically against the arXiv API, Crossref and GitHub [7, 29, 30, 36, 37]. Medium-high for the ADJACENT and PUBLISHED verdicts, each backed by an exact quote. Medium for the three NEW verdicts: absence of evidence after 4 or more general queries, a citation hop and one orchestrator adversarial pass. The field moves weekly, and the pass surfaced one new near miss for C15 [23]. Medium for kill-check = OPEN. Semantic Scholar does not yet index citations of 2606.16349, and grey literature (Report 74 [3], Jorak [6]) is where the closest work lives, so a practitioner blog could close it. Evidence that would change a verdict: a 2026 paper correlating any causal per-model refusal quantity with XSTest/OR-Bench or HarmBench across families (closes the kill-check); a paper validating effective rank against safety benchmarks (closes C15); a learned internal-feature safety predictor (closes C14)."""

    sources = SOURCES
    idx = {s["index"] for s in sources}
    cited = {int(x) for grp in re.findall(r"\[([\d,\s]+)\]", answer) for x in grp.replace(" ", "").split(",") if x}
    missing = cited - idx
    assert not missing, f"citations without sources: {missing}"

    summary = (
        "NOVELTY TABLE FOR C1-C16, KILL-CHECK, REGENERATED BIB, NUMBER LEDGER AND SCANNER PIN. Files: novelty_table.json (16 rows, each with a quote, locator, at least 4 queries, and a paste-ready positioning sentence), "
        "novelty_A/B/C.json (raw subagent records), references.bib ({n} entries, no duplicate keys), bib_fixes.json, citation_corrections.json, number_ledger.json, scanner_pin.json. "
        "KILL-CHECK OPEN (closed=false). No paper correlates a per-model causal harm-to-refusal quantity with benchmark safety across families. The adverse prior to cite is Failure-First Report 74 (grey literature): abliteration resistance vs jailbreak refusal, rho=-0.003, n=16. The closest arXiv hit is LVS 2606.08044 (undirected perturbation, no benchmark correlation). "
        "VERDICTS: NEW = C5 (weight-path gain; nearest miss 2604.27401), C14 (ridge metamodel; GFS/RAS use fixed weights), C15 (late-layer effective rank; must cite the new nearest miss 2608.25390, stable rank vs ablation robustness in one OLMo lineage). "
        "PUBLISHED = C9 (Leong 2502.13946: template-region NIE normalised 'for a fair cross-model comparison' across 6 models from 4 families) -> REPLICATION row; C16 (Li 2603.24543: per-model steering slope gamma_1 across 6 models) -> COMPARATOR only. "
        "ADJACENT = C1, C2 (closest to published; cite Report 74), C3, C4 (Jorak already reads o_proj/down_proj parent-free, but only as a label), C6, C7, C8, C10, C11 (all incumbents parent-dependent), C12, C13. "
        "CRITICAL CORRECTIONS FOR THE PAPER: (1) '0.35 published Jorak threshold' is WRONG. Jorak @8147de3 scanner.py L48-55 ships 0.5 (unchanged since the first commit). 0.35 is this run's own BSA_PREREG_THRESHOLD (iter_1 flab/config.py:74), and BSA_w8 is not Jorak's statistic, so withdraw the 'published scanner 100% FPR' claim. "
        "(2) The iter-2 draft's hand-typed reference list has 20/30 fabricated first authors and 5 wrong initials; generate references only from the bib. (3) Cite Tan2024 = 2407.12404 for steering brittleness; 2406.09289 is Ball et al. "
        "(4) Planner fix-list items ii (Casper) and vi (AMS DOI) were false positives: both DOIs were already correct; the fixes were an added eprint and @article. "
        "(5) Qwen3Guard report 2510.14276 Section 3.5 confirms Qwen3Guard-4B-Gen was SafeRL's reward. "
        "LEDGER: {lsum}"
    ).format(n=bibent["n"], lsum=ledger_summary.get("short", "see number_ledger.json"))

    follow = [
        "Does Jorak's own statistic (sigma_1/||U||_F global and round(L/6)-window band alignment, threshold 0.5) produce false positives on the honest panel? This is needed to replace the withdrawn '0.35 / 100% FPR' claim.",
        "Does any causal quantity keyed to the model's own harm direction (C1/C2/C5) beat Report 74's null (rho = -0.003) once over-refusal is scored as a second arm and a blanket refuser is forced to lose?",
        "Is Leong et al.'s template-region NIE (C9) numerically correlated with harmful-refusal and over-refusal benchmarks across held-out families, i.e. does the published quantity survive as a score?",
    ]

    out = {
        "title": TITLE,
        "summary": summary,
        "answer": answer,
        "sources": sources,
        "follow_up_questions": follow,
        "novelty_table": table,
        "kill_check": kc,
        "claimable_novelty_summary": {
            "NEW": {"C5": "weights-only harm-to-refusal path gain as a cross-family safety score",
                    "C14": "FITTED metamodel over depth-by-site internal features (vs fixed-weight GFS/RAS aggregations)",
                    "C15": "late-layer dispersion validated against two-sided safety benchmarks (cite 2608.25390 as nearest miss)"},
            "NEW_ONLY_AS_PARENT_FREE_CROSS_FAMILY_SCORE": ["C1", "C2", "C3", "C4", "C6", "C7", "C8", "C10", "C11", "C12", "C13"],
            "PUBLISHED": {"C9": "replication of Leong et al. 2502.13946", "C16": "comparator of Li 2603.24543"}},
        "screen_implications": [
            "C9 -> REPLICATION row (Leong 2502.13946); do not claim the construct.",
            "C16 -> COMPARATOR-only row (Li 2603.24543; Tan 2407.12404).",
            "C2 -> must cite Failure-First Report 74's null result as the adverse prior; claim only the two-sided, margin-based, random-direction-controlled form.",
            "C4 -> must cite Jorak (reference-free weight read of o_proj/down_proj); novelty is graded z-scored writer capacity plus benchmark validation.",
            "C11 -> strongest positioning: every incumbent is parent-dependent (Qi 2406.05946; Yang 2609.18471).",
            "C15 -> cite Labunets 2608.25390 (stable rank vs ablation robustness, one lineage).",
            "BSA/Jorak row -> relabel 0.35 as our pre-registered simulation threshold; Jorak's shipped threshold is 0.5 on different statistics.",
        ],
        "bib_fixes": fixes,
        "citation_corrections": cc,
        "number_ledger": recs,
        "scanner_pin": pin,
        "references_bib": bibtxt,
    }
    (WS / "research_out.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))

    # prose twin
    md = [f"# {TITLE}\n", summary, "\n## Answer\n", answer, "\n## Novelty table\n",
          "| Cand | Verdict | Closest prior work | Used to rank models? | Positioning |", "|---|---|---|---|---|"]
    for r in table:
        ids = ", ".join(str(p.get("arxiv_id_or_doi")) for p in r["closest_prior_work"][:3])
        rk = r["used_to_rank_models"]["value"] if isinstance(r["used_to_rank_models"], dict) else r["used_to_rank_models"]
        md.append(f"| {r['candidate']} | {r['verdict']} | {ids} | {rk} | {r['positioning_sentence'].replace('|', '/')} |")
    md += ["\n## Quotes and locators\n"] + [f"- **{r['candidate']}** ({r['verdict']}): \"{r['quote']}\" — {r['locator']}" for r in table]
    md += ["\n## Kill-check\n", "```json", json.dumps(kc, indent=1, ensure_ascii=False)[:6000], "```",
           "\n## Scanner pin\n", "```json", json.dumps(pin, indent=1, ensure_ascii=False), "```",
           "\n## Bib fixes\n"] + [f"- ({f['item']}) {f['key_old']} -> {f['key_new']}: {f['problem']} FIX: {f['fix']}" for f in fixes]
    md += ["\n## Number ledger\n", "| Claim | Paper | Status | Locator |", "|---|---|---|---|"]
    for r in recs:
        md.append(f"| {str(r.get('claim_text',''))[:110].replace('|','/')} | {r.get('paper_id','')} | {str(r.get('status',''))[:60]} | {str(r.get('locator',''))[:80].replace('|','/')} |")
    md += ["\n## Sources\n"] + [f"[{s['index']}] {s['title']} — {s['url']}" for s in sources]
    md += ["\n## Follow-up questions\n"] + [f"- {q}" for q in follow]
    (WS / "research_report.md").write_text("\n".join(md) + "\n")

    struct = {"title": TITLE, "layman_summary": LAYMAN, "summary": summary,
              "out_expected_files": {"output": "research_out.json"},
              "upload_ignore_regexes": [r"(^|/)raw/jorak_src/", r"(^|/)raw/arxiv_atom_\d+\.xml$"],
              "answer": answer, "sources": sources, "follow_up_questions": follow}
    (WS / ".terminal_claude_agent_struct_out.json").write_text(json.dumps(struct, indent=1, ensure_ascii=False))
    print("summary chars", len(summary), "answer chars", len(answer), "sources", len(sources), "cited", sorted(cited))
    assert 500 <= len(summary) <= 5000, len(summary)


if __name__ == "__main__":
    main()
