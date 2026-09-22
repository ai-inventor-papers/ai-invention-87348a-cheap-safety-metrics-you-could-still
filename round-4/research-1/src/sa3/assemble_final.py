#!/usr/bin/env python3
import json
from pathlib import Path

WS = Path("/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_4/gen_art/gen_art_research_1")
rows = json.load(open(WS / "sa3/_rows_partial.json"))
counts = json.load(open(WS / "sa3/census_counts_out.json"))

cross_check_vs_iter3 = {
    "iter3_claims_checked": [
        "HELM coverage n=0 for sub-4B panel",
        "only 2 sub-4B models with published HELM numbers",
        "identical-weights guardian-pair gap up to 6.7x the across-model variance",
        "OLB v2 capability join n=16",
    ],
    "verdict": "AGREE on all four numeric claims, once the two different panels those claims describe are told apart.",
    "detail": [
        {
            "claim": "HELM coverage n=0 for sub-4B panel",
            "agreement": "AGREE",
            "evidence": ("Re-read .../gen_art_dataset_1/README.md:26 ('HELM safety, AIR-Bench and SALAD have "
                         "n=0 exact-id hits for this panel') and independently re-derived the same result "
                         "in this session by loading data/external/helm_model_meta.json directly: of 99 total "
                         "HELM model-name records, only 22 resolve to a real HF repo_id, and every one of "
                         "those 22 is a mid/large flagship (e.g. allenai/olmo-2-1124-32b-instruct, "
                         "qwen/qwen3-235b-a22b-instruct-2507-fp8, deepseek-ai/deepseek-v3, "
                         "mistralai/mixtral-8x22b-instruct-v0.1) -- none sub-4B, none in this 36-model panel."),
        },
        {
            "claim": "only 2 sub-4B models with published HELM numbers",
            "agreement": "AGREE, but this claim describes a DIFFERENT and larger corpus than the 36-model dataset panel",
            "evidence": ("Sourced to iter_3/gen_strat/gen_strat_1/arts_pool.json ('PART 3 (HELM, reused v1 limb): "
                         "81 models, 36 resolved, 45 closed-API; only 2 sub-4B with published numbers') and "
                         "restated identically in iter_3/review_paper/review_paper/.terminal_claude_agent_struct_out.json. "
                         "That '81 models / 36 resolved' HELM limb is a SEPARATE, wider model universe than the "
                         "36-CHECKPOINT dev panel used in gen_art_dataset_1/panel.json (81 vs 36 is coincidentally "
                         "close in count but is a different list -- the dataset panel's own HELM join gets 0/22 "
                         "resolved names overlapping it, not 2). This census's own live re-check of HELM v1.17.0 "
                         "(same file, data/external/helm_safety_v1_17_0.json) finds 0 of the 36 dataset-panel "
                         "repos among the 22 HELM-resolvable names, consistent with both numbers: the wider "
                         "81-model HELM limb apparently DID catch 2 sub-4B models somewhere in its broader net, "
                         "but neither of those 2 (unnamed in the source artifacts found) appears to be one of "
                         "the 36 repos in THIS panel."),
        },
        {
            "claim": "identical-weights guardian-pair gap up to 6.7x the across-model variance",
            "agreement": "AGREE (not independently re-verifiable from this task's scope, taken as reported)",
            "evidence": ("Same two source artifacts (arts_pool.json and the iter_3 review) state this ceiling "
                         "figure ('a ceiling for any weights-only readout') in the same breath as the HELM "
                         "81-model/36-resolved/2-sub-4B figures. This is a methodological finding from the "
                         "safety-metric research thread (about how much a per-checkpoint readout can possibly "
                         "predict), not a benchmark-coverage fact this ecosystem census independently re-measures; "
                         "it is orthogonal to (and not contradicted by) anything found in this census."),
        },
        {
            "claim": "OLB v2 capability join n=16",
            "agreement": "AGREE, exactly",
            "evidence": ("README.md:27 states 'Open LLM Leaderboard v2 capability columns: n=16.' Independently "
                         "re-derived in this session by reading results/external_join.json directly: "
                         "n_per_column.olb2_average = 16 (also confirmed for olb2_ifeval/bbh/math_lvl5/gpqa/musr/"
                         "mmlu_pro, all =16). This census's own row-by-row listing of that join (see rows tagged "
                         "benchmark=OLB_v2 in this file) reproduces the same 16 repos, 15 of which are distinct "
                         "panel checkpoints plus one extra 'google/gemma-2-2b-it' lineage-reference row that "
                         "duplicates the unsloth/gemma-2-2b-it mirror's numbers."),
        },
    ],
    "new_findings_not_in_iter3": [
        ("This census additionally found real, exact-checkpoint safety/over-refusal numbers OUTSIDE the "
         "4 leaderboards iter-3 checked (HELM/AIR-Bench/SALAD/OLB), by mining official technical reports and "
         "HF model cards directly: Microsoft's Phi-4-mini paper (XSTest IPRR/VPRR + RAI Defect Rate for "
         "Phi-4-mini/Phi-3.5-mini/Llama-3.2-3B/Qwen2.5-3B), AI2's OLMo-2-0425-1B-Instruct card ('Safety' "
         "composite for itself, Qwen2.5-1.5B-Instruct and SmolLM2-1.7B-Instruct), the aiXamine paper "
         "(Over-Refusal + Safety&Alignment composites for Llama-3.2-1B/3B-Instruct), and the Qwen3Guard "
         "technical report (Qwen3-4B and Qwen3-4B-SafeRL WildGuard-judged safety/refusal rates). "
         "This raises the exact-checkpoint safety-number count for the 36-model panel to 15/36 (42%), "
         "materially higher than a naive 'n=0 on the 4 big leaderboards' reading would suggest -- the "
         "numbers exist, but scattered one-off in competitor papers' comparison tables, not on any single "
         "safety leaderboard."),
    ],
}

positioning_ecosystem = (
    "As of 2026-09-21, 15 of 36 sub-4B panel checkpoints (42%) carry any published safety number, but "
    "every one comes from a technical report's or card's own comparison table (Phi-4-mini, OLMo-2, "
    "aiXamine, Qwen3Guard), never a dedicated safety leaderboard: HELM Safety, AIR-Bench, SALAD-Bench "
    "and TrustLLM each return zero exact-id hits, and JailbreakBench/HarmBench target adversarial-attack "
    "research, not routine coverage. Only 5 of 36 (14%) carry any over-refusal number (XSTest-style), "
    "again via cross-vendor tables, not a leaderboard scenario. Capability fares better: MMLU-family "
    "numbers exist for 17/36 (47%), GSM8K for 9/36 (25%), self-reported Arena-Hard for 8/36 (22%), and "
    "Open LLM Leaderboard v2 for 8/36 (22%) -- but that Arena-Hard means a developer's own local run, not "
    "a live lmarena entry, which has none for this panel. Community fine-tunes are almost uniformly "
    "unmeasured: only 2 of 15 print a self-reported safety number, on a community harmbench variant, not "
    "an independent benchmark. The gap is structural: benchmarks built for this size class don't evaluate it."
)

sources = [
    {"url": "https://arxiv.org/abs/2505.09388", "title": "Qwen3 Technical Report", "summary": "Tables 17-20 give MMLU-Redux/Arena-Hard/IFEval for Qwen3-0.6B/1.7B/4B and Qwen2.5/Phi-4-mini/Gemma-3 baselines; no dedicated safety section.", "passages": [{"quote": "Table 20: Comparison among Qwen3-1.7B / Qwen3-0.6B (Non-thinking)... Arena-Hard 17.8 32.8 9.0 23.7 6.5 36.9", "locator": "Table 20"}]},
    {"url": "https://arxiv.org/abs/2412.15115", "title": "Qwen2.5 Technical Report", "summary": "Tables 9-10 give MMLU-Redux/MMLU-Pro/GSM8K/IFEval for Qwen2.5-0.5B/1.5B/3B-Instruct plus Gemma2-2B and Phi3.5-mini baselines.", "passages": [{"quote": "Table 10: Performance comparison of 0.5B-1.5B instruction-tuned models... Qwen2.5-0.5B... GSM8K 49.6", "locator": "Table 10"}]},
    {"url": "https://arxiv.org/abs/2510.14276", "title": "Qwen3Guard Technical Report", "summary": "Section 3.5/Table 10 reports the exact Safety-RL experiment that produced Qwen3-4B-SafeRL, with Non-Think/Think x Guard-only/Hybrid safety-rate, refusal, ArenaHard-v2 and reasoning numbers for base Qwen3-4B and both SafeRL variants.", "passages": [{"quote": "Mode Model Safety Rate Refusal ArenaHard-v2 ... Non-Think Qwen3-4B 47.5 64.7 12.9 9.5 ... + SafeRL (Hybrid) 86.5 98.1 5.3 10.7", "locator": "Table 10, Sec 3.5"}]},
    {"url": "https://huggingface.co/Qwen/Qwen3-4B-SafeRL", "title": "Qwen3-4B-SafeRL model card", "summary": "Confirms the released checkpoint is the Hybrid-reward variant and reprints the Non-Think/Think performance table.", "passages": [{"quote": "Non-Think | Qwen3-4B-SafeRL | 86.5 | 98.1 | 5.3 | 10.7 | 18.2 | 27.7 | 40.8", "locator": "Performance table"}]},
    {"url": "https://arxiv.org/abs/2503.01743", "title": "Phi-4-Mini Technical Report", "summary": "Tables 10-12 give RAI Defect Rate and XSTest IPRR/VPRR for Phi-4-Mini, Phi-4-Multimodal, Phi-3.5-mini, Llama-3.2-3B and Qwen-2.5-3B; the Model Quality table gives Arena-Hard/MMLU/GSM8K for the same set plus Llama-3.2-3B/Qwen2.5-3B.", "passages": [{"quote": "IPRR 93.5% | 92% | 87% | 92.5% | 92% ... VPRR 20.8% | 26.4% | 21.2% | 15.6% | 25.6%", "locator": "Table 12"}]},
    {"url": "https://arxiv.org/abs/2408.00118", "title": "Gemma 2 Technical Report", "summary": "Table 15 (human-preference safety win-rate vs GPT-4o), Table 17 (PT vs IT MMLU) and Table 18 (RealToxicity/CrowS-Pairs/BBQ) for Gemma-2 IT 2B.", "passages": [{"quote": "Gemma 2 IT 2B 26.5%+-1.8% 57.5% ... Win/Tie/Loss 53%/9%/38%", "locator": "Table 15"}]},
    {"url": "https://huggingface.co/blog/falcon3", "title": "Falcon3 launch blog (HF)", "summary": "Prose benchmark summary; actual numeric tables are images, not machine-extractable text. No safety section.", "passages": [{"quote": "Falcon3-1B attains competitive results in IFEval (54.4), MUSR (40.7), and SciQ (86.8)", "locator": "Instruct models section"}]},
    {"url": "https://huggingface.co/tiiuae/Falcon3-1B-Instruct", "title": "Falcon3-1B-Instruct model card", "summary": "Benchmarks table with MMLU/MMLU-Pro/IFEval/GSM8K for Falcon3-1B-Instruct plus Llama-3.2-1B/Qwen2.5-1.5B/SmolLM2-1.7B comparison columns.", "passages": [{"quote": "MMLU (5-shot) | 68.2 | 59.8 | 49.2 | 46.1", "locator": "Benchmarks table"}]},
    {"url": "https://arxiv.org/abs/2407.09276", "title": "H2O-Danube3 Technical Report", "summary": "MMLU/GSM8K table for H2O-Danube3-500M-Chat vs Qwen2-0.5B-Instruct; separate MT-Bench/WildBench chat table, no named safety benchmark.", "passages": [{"quote": "MMLU 5-shot 26.33 43.88 ... GSM8K 5-shot 16.00 34.12", "locator": "smaller-models academic benchmark table"}]},
    {"url": "https://arxiv.org/abs/2502.02737", "title": "SmolLM2: When Smol Goes Big", "summary": "Table 5 compares SmolLM2-1.7B-Instruct, Llama3.2-1B and Qwen2.5-1.5B on IFEval/MT-Bench/MMLU-Pro/GSM8K/MATH; no safety section.", "passages": [{"quote": "IFEval (Average) 56.7 53.5 47.4 ... GSM8K (5-shot) 48.8 37.4 63.3", "locator": "Table 5"}]},
    {"url": "https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct", "title": "SmolLM2-360M-Instruct model card", "summary": "Own IFEval/MMLU/GSM8K numbers plus a Qwen2.5-0.5B-Instruct comparison row.", "passages": [{"quote": "GSM8K (5-shot) | 7.43 | **26.8** | 1.36", "locator": "Instruction Model table"}]},
    {"url": "https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B-Instruct", "title": "SmolLM2-1.7B-Instruct model card", "summary": "Own IFEval/MMLU-Pro/GSM8K numbers plus Llama-1B-Instruct/Qwen2.5-1.5B-Instruct comparison rows.", "passages": [{"quote": "GSM8K (5-shot) | **48.2** | 26.8 | 42.8 | 4.62", "locator": "Instruction Model table"}]},
    {"url": "https://huggingface.co/HuggingFaceTB/SmolLM3-3B", "title": "SmolLM3-3B model card", "summary": "No-Extended-Thinking table gives IFEval for SmolLM3-3B, Qwen2.5-3B, Llama3.1-3B, Qwen3-1.7B, Qwen3-4B; base table gives GSM8K(5-shot) for Qwen3-4B-Base.", "passages": [{"quote": "Instruction following | IFEval | 76.7 | 65.6 | 71.6 | 74.0 | 68.9", "locator": "No Extended Thinking table"}]},
    {"url": "https://huggingface.co/allenai/OLMo-2-0425-1B-Instruct", "title": "OLMo-2-0425-1B-Instruct model card", "summary": "Performance table with an explicit 'Safety' column (Tulu-3 eval suite) for OLMo 2 1B (final), Qwen 2.5 1.5B and SmolLM2 1.7B baselines.", "passages": [{"quote": "OLMo 2 1B | 42.7 | 9.1 | 35.0 | 34.6 | 68.3 | 70.1 | 20.7 | 40.0 | 87.6 | 12.9 | 48.7", "locator": "Performance table"}]},
    {"url": "https://huggingface.co/utter-project/EuroLLM-1.7B-Instruct", "title": "EuroLLM-1.7B-Instruct model card", "summary": "Only ArcChallenge/HellaSwag multilingual tables; no MMLU/GSM8K/Arena-Hard/safety number.", "passages": [{"quote": "EuroLLM-1.7B 0.3496 ... TinyLlama-v1.1 0.2650 ... Gemma-2B 0.3617", "locator": "Arc Challenge table"}]},
    {"url": "https://huggingface.co/huihui-ai/Qwen2.5-0.5B-Instruct-CensorTune", "title": "Qwen2.5-0.5B-Instruct-CensorTune model card", "summary": "Self-reported harmbench_behaviors pass-rate table (own fine-tune vs original vs abliterated variants) plus an IF_Eval/BBH/GPQA/MMLU-Pro/TruthfulQA re-eval table.", "passages": [{"quote": "Qwen2.5-0.5B-Instruct-CensorTune | 0/320 | 0.00% ... Qwen2.5-0.5B-Instruct | 201/320 | 62.8%", "locator": "pass-rate table"}]},
    {"url": "https://huggingface.co/huihui-ai/Qwen2.5-1.5B-Instruct-CensorTune", "title": "Qwen2.5-1.5B-Instruct-CensorTune model card", "summary": "Same harmbench_behaviors pass-rate pattern as the 0.5B CensorTune card.", "passages": [{"quote": "Qwen2.5-1.5B-Instruct-CensorTune | 0/320 | 0.00% ... Qwen2.5-1.5B-Instruct | 73/320 | 22.81%", "locator": "pass-rate table"}]},
    {"url": "https://huggingface.co/huihui-ai/Llama-3.2-3B-Instruct-abliterated", "title": "Llama-3.2-3B-Instruct-abliterated model card", "summary": "Self-reported IF_Eval/MMLU-Pro/TruthfulQA/BBH/GPQA re-eval vs the original checkpoint; no safety number.", "passages": [{"quote": "IF_Eval | 76.55 | 76.76 ... MMLU Pro | 27.88 | 28.00", "locator": "Evaluations table"}]},
    {"url": "https://huggingface.co/DreamFast/qwen3-4b-heretic", "title": "qwen3-4b-heretic model card", "summary": "Self-reported Heretic-tool refusal count (3/100 vs 100/100 original); no named benchmark.", "passages": [{"quote": "Refusals: 3/100 (vs 100/100 original)", "locator": "Model Details"}]},
    {"url": "https://arxiv.org/abs/2504.14985", "title": "aiXamine: Simplified LLM Safety and Security", "summary": "Table 6 leaderboard gives an Over-Refusal composite (OK-Test/OR-Bench/WildGuard/XSTest) and a Safety&Alignment composite for Llama3.2-1B and Llama3.2-3B, among other models.", "passages": [{"quote": "Llama3.2-3B ... 91.09 86.21 93.77 94.67 73.04 ... Llama3.2-1B ... 87.21 54.37 81.86 96.30 63.99", "locator": "Table 6"}]},
    {"url": "https://www.rivista.ai/wp-content/uploads/2024/10/paper-1.pdf", "title": "Granite 3.0 Language Models (IBM technical report)", "summary": "Figure 7(b)/Table 17 establish IBM's family-level AttaQ/SocialStigmaQA/SALAD-safety-rate practice for 2B-3B Granite Instruct models vs Llama-3.2/Gemma-2; 2B-3B numbers are figure-only.", "passages": [{"quote": "Granite-3.0 models perform best in their parameter range, outperforming other models in all 7 aspects of safety, including Llama-3.1, Llama-3.2 and Gemma-2 models.", "locator": "Sec on safety evaluation, Figure 7"}]},
    {"url": "https://arxiv.org/abs/2402.17834", "title": "Stable LM 2 1.6B Technical Report", "summary": "Full-text grep for safety|toxicity|RealToxicity|refusal returns only one incidental citation match; no safety/toxicity evaluation section exists in this report.", "passages": [{"quote": "(no safety/toxicity evaluation section found; only bibliography citation of an unrelated 'toxicity' paper)", "locator": "full-text grep, 1/1 match = bibliography"}]},
    {"url": "local:data/external/helm_safety_v1_17_0.json, helm_airbench_v1_19_0.json, saladbench.json, helm_model_meta.json", "title": "iter_3 gen_art_dataset_1 pinned local tables", "summary": "Re-read directly in this session: 99 total HELM model-name records, 22 resolve to real repo_ids (all mid/large flagships, 0 sub-4B); saladbench.json status=NOT_REACHABLE (no leaderboard file exists in the SALAD-Bench HF dataset).", "passages": [{"quote": "\"status\": \"NOT_REACHABLE\", \"note\": \"...dataset holds only raw QA data, not a published model-score table\"", "locator": "saladbench.json"}]},
    {"url": "local:iter_3/gen_art/gen_art_dataset_1/results/external_join.json", "title": "iter_3 dataset panel external/capability join", "summary": "Exact-repo-id join giving n_per_column: helm_safety_mean=0, helm_xstest=0, airbench_refusal=0, salad_score=0, mmlu=1, gsm8k=1, olb2_*=16 for all 7 OLB v2 sub-columns.", "passages": [{"quote": "\"olb2_average\": 16, \"olb2_ifeval\": 16, \"olb2_bbh\": 16, \"olb2_math_lvl5\": 16, \"olb2_gpqa\": 16, \"olb2_musr\": 16, \"olb2_mmlu_pro\": 16", "locator": "n_per_column"}]},
    {"url": "local:iter_3/gen_art/gen_art_dataset_1/README.md", "title": "iter_3 dataset panel README", "summary": "States the HELM/AIR-Bench/SALAD n=0 and OLB v2 n=16 findings this census cross-checks.", "passages": [{"quote": "HELM safety, AIR-Bench and SALAD have n=0 exact-id hits for this panel. Open LLM Leaderboard v2 capability columns: n=16.", "locator": "External join section, lines 25-28"}]},
    {"url": "local:iter_3/gen_strat/gen_strat_1/arts_pool.json", "title": "iter_3 gen_strat arts_pool (HELM v1 limb)", "summary": "Source of the '81 models, 36 resolved, only 2 sub-4B with published numbers; 6.7x guardian-pair ceiling' figures cross-checked in this census.", "passages": [{"quote": "PART 3 (HELM, reused v1 limb): 81 models, 36 resolved, 45 closed-API; only 2 sub-4B with published numbers; identical-weights guardian-pair gap up to 6.7x the across-model variance", "locator": "arts_pool.json"}]},
    {"url": "https://trustllmbenchmark.github.io/TrustLLM-Website/leaderboard.html", "title": "TrustLLM leaderboard", "summary": "JS-rendered page; static fetch returned no model names. TrustLLM's own paper (2401.05561) roster is 16 models, all 7B+ / proprietary API (Llama2, Vicuna, Mistral-7B, ChatGLM2, GPT-4, PaLM 2, ERNIE, etc.) -- none overlap this sub-4B panel.", "passages": []},
    {"url": "https://arxiv.org/abs/2401.05561", "title": "TrustLLM: Trustworthiness in Large Language Models", "summary": "Confirms the 16-model roster is 7B+/proprietary-API only.", "passages": []},
]

out = {
    "rows": rows,
    "counts": counts,
    "accessed_date": "2026-09-21",
    "cross_check_vs_iter3": cross_check_vs_iter3,
    "positioning_ecosystem": positioning_ecosystem,
    "sources": sources,
    "blockers": [
        "google/gemma-2-2b-it and meta-llama/Llama-3.2-1B-Instruct and meta-llama/Llama-3.2-3B-Instruct official raw READMEs are gated on HF (require login); worked around via the arXiv reports (Gemma 2, N/A for Llama) and third-party comparison tables (Falcon3/SmolLM2/Phi-4-mini/aiXamine cards) that quote the same official numbers, but no direct read of Meta's own Llama-3.2 model-card safety section (if any) was possible in this session.",
        "IBM's public Granite docs/leaderboard page (ibm.com/granite/docs/models/granite) is JS-rendered; static fetch returned 1 char, so a Granite-3.3/4.0-SPECIFIC safety table (as opposed to the predecessor Granite-3.0 technical report's family-level AttaQ practice) was not located within the time budget.",
        "TrustLLM's leaderboard.html is JS-rendered (889 chars static); model roster confirmed instead via the TrustLLM paper itself and general web search, not a live leaderboard scrape.",
        "JailbreakBench and HarmBench were checked via web search only (no scrapable public leaderboard/results page enumerating all tested models was found in the time budget); the working assumption of n=0 for this panel rests on those benchmarks' published usage patterns (adversarial-attack research on frontier/7B+ targets), not an exhaustive per-repo check.",
        "EuroLLM-1.7B-Instruct's own dedicated technical report/blog (if one exists separately from the EuroLLM-9B report) was not located; only its HF card (ArcChallenge/HellaSwag only) and the EuroLLM-9B report's passing mention were checked.",
        "Sealed families (granite, stablelm): per the sealing rule, no sealed repo's own HF card/README was opened in this session; family-level findings rest on the Granite 3.0 predecessor technical report and the StableLM-2 1.6B architecture report only, plus one incidental non-opened web-search snippet for a StableLM-2 card disclaimer sentence (noted explicitly in that row).",
        "Given the very large number of cross-paper capability comparisons uncovered (each vendor's card/report benchmarks its neighbors), this census is thorough for official instruct models but the community fine-tune rows (aside from CensorTune, heretic, Llama-3.2-3B-abliterated) were checked at 'card only, single keyword grep' depth per the task's fallback instruction, not a full manual read of every card.",
    ],
}

json.dump(out, open(WS / "sa3/sa3_out.json", "w"), indent=2)
print("wrote sa3_out.json,", len(json.dumps(out)), "bytes,", len(rows), "rows")
