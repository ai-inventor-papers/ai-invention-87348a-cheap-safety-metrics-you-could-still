#!/usr/bin/env python3
"""Build sa3 census rows from research findings. Writes WS/sa3/rows.json."""
import json
from pathlib import Path

WS = Path("/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_4/gen_art/gen_art_research_1")
ACCESSED = "2026-09-21"

rows = []

def R(**kw):
    d = dict(
        repo=None, family=None, n_params=None, class_=None, benchmark=None,
        number_exists="no", value=None, metric_name=None, setting=None,
        source_url=None, source_type=None, accessed_date=ACCESSED,
        checkpoint_exact_match=False, notes="",
    )
    d.update(kw)
    d["class"] = d.pop("class_")
    rows.append(d)

# ---------------------------------------------------------------------------
# LOCAL TABLE CONFIRMATIONS (HELM safety/AIR-Bench/SALAD/OLB v2) -- checked-no
# rows collapsed per repo; OLB v2 "yes" rows are individual below.
# ---------------------------------------------------------------------------
HELM_NO_NOTE = ("Local external_join.json (exact repo_id join, no fuzzy match): "
                "helm_safety_v1_17_0.json (81 model names, only 22 resolve to real HF repo_ids "
                "per helm_model_meta.json, all mid/large flagships e.g. olmo-2-32b, qwen3-235b, "
                "deepseek-v3/r1, mixtral-8x22b -- none sub-4B); helm_airbench_v1_19_0.json same 22 "
                "resolved names; saladbench.json = NOT_REACHABLE, dataset holds only raw QA text, "
                "no leaderboard/score file exists in OpenSafetyLab/Salad-Data on HF. Re-confirmed by "
                "direct read of these 3 local files in this run.")

# Official/upstream instruct+base rows with local-table checked-no safety (still list once, since
# capability/other findings for these repos are individual rows below; the safety-no fact is folded
# into a single collapsed row per repo for the benchmarks with zero hits.)

def collapsed_no(repo, family, n_params, klass, checked, note):
    R(repo=repo, family=family, n_params=n_params, class_=klass,
      benchmark="+".join(checked), number_exists="no", value=None, metric_name=None,
      setting=None, source_url="local:data/external/{helm_safety_v1_17_0.json,helm_airbench_v1_19_0.json,saladbench.json,openllm_v2_contents.parquet}",
      source_type="local_table", checkpoint_exact_match=True, notes=note)

# ===========================================================================
# QWEN3 FAMILY
# ===========================================================================
R(repo="Qwen/Qwen3-0.6B", family="qwen3", n_params=751632384, class_="instruct",
  benchmark="Arena_Hard", number_exists="yes", value=6.5, metric_name="Arena-Hard v1 (non-thinking mode)",
  setting="enable_thinking=False", source_url="https://arxiv.org/abs/2505.09388", source_type="paper",
  checkpoint_exact_match=True,
  notes="Qwen3 Technical Report Table 20 (Qwen3-1.7B/0.6B Non-thinking baselines). Matches panel thinking_flag=False.")
R(repo="Qwen/Qwen3-0.6B", family="qwen3", n_params=751632384, class_="instruct",
  benchmark="MMLU", number_exists="yes", value=44.6, metric_name="MMLU-Redux (5-shot, CoT), NOT vanilla MMLU",
  setting="enable_thinking=False", source_url="https://arxiv.org/abs/2505.09388", source_type="paper",
  checkpoint_exact_match=True, notes="Same Table 20. Qwen reports MMLU-Redux, not standard MMLU, at this size; GSM8K is not reported for this size either (superseded by MATH-500 in their harness).")
collapsed_no("Qwen/Qwen3-0.6B", "qwen3", 751632384, "instruct",
  ["HELM_Safety","HELM_XSTest_overrefusal","AIR_Bench","SALAD","TrustLLM","JailbreakBench","HarmBench","GSM8K","OLB_v2"],
  HELM_NO_NOTE + " OLB v2 (open-llm-leaderboard/contents, commit 9c09a7cae433): no row (model post-dates leaderboard's active submission window). No official safety table on HF card (README has zero MMLU/GSM8K/safety keyword hits) or in the tech report for 0.6B.")

R(repo="Qwen/Qwen3-1.7B", family="qwen3", n_params=2031739904, class_="instruct",
  benchmark="Arena_Hard", number_exists="yes", value=36.9, metric_name="Arena-Hard v1 (non-thinking mode)",
  setting="enable_thinking=False", source_url="https://arxiv.org/abs/2505.09388", source_type="paper",
  checkpoint_exact_match=True, notes="Qwen3 Technical Report Table 20.")
R(repo="Qwen/Qwen3-1.7B", family="qwen3", n_params=2031739904, class_="instruct",
  benchmark="MMLU", number_exists="yes", value=64.4, metric_name="MMLU-Redux (5-shot, CoT)",
  setting="enable_thinking=False", source_url="https://arxiv.org/abs/2505.09388", source_type="paper",
  checkpoint_exact_match=True, notes="Table 20. Cross-check: SmolLM3-3B card (HF, No-Extended-Thinking table) reports Qwen3-1.7B IFEval=74.0 vs Qwen's own self-reported IFEval for the same nominal checkpoint elsewhere in Table 20 context -- absolute values differ by harness/prompt, a recurring pattern across every cross-paper comparison found in this census.")
collapsed_no("Qwen/Qwen3-1.7B", "qwen3", 2031739904, "instruct",
  ["HELM_Safety","HELM_XSTest_overrefusal","AIR_Bench","SALAD","TrustLLM","JailbreakBench","HarmBench","GSM8K","OLB_v2"],
  HELM_NO_NOTE + " OLB v2: no row (post-dates leaderboard). No safety number found on card, in tech report, or in any third-party card that cross-cites Qwen3-1.7B.")

R(repo="Qwen/Qwen3-4B", family="qwen3", n_params=4022468096, class_="instruct",
  benchmark="Arena_Hard", number_exists="yes", value=66.2, metric_name="Arena-Hard v1 (non-thinking mode)",
  setting="enable_thinking=False", source_url="https://arxiv.org/abs/2505.09388", source_type="paper",
  checkpoint_exact_match=True, notes="Qwen3 Technical Report Table 18 (Qwen3-8B/4B Non-thinking).")
R(repo="Qwen/Qwen3-4B", family="qwen3", n_params=4022468096, class_="instruct",
  benchmark="MMLU", number_exists="yes", value=77.3, metric_name="MMLU-Redux (5-shot, CoT)",
  setting="enable_thinking=False", source_url="https://arxiv.org/abs/2505.09388", source_type="paper",
  checkpoint_exact_match=True, notes="Table 18.")
R(repo="Qwen/Qwen3-4B", family="qwen3", n_params=4022468096, class_="instruct",
  benchmark="other_card_safety", number_exists="yes",
  value="Safety Rate (Qwen3-235B-Instruct-2507 judge)=47.5%; WildGuard safety rate=64.7%; WildGuard refusal-on-benign=12.9%; ArenaHard-v2 (GPT-4.1 judge) winrate=9.5",
  metric_name="Pre-SafeRL baseline safety/refusal/quality quad, Non-Think mode",
  setting="enable_thinking=False; eval set = WildJailbreak (2000 harmful + 210 benign prompts)",
  source_url="https://arxiv.org/abs/2510.14276", source_type="paper", checkpoint_exact_match=True,
  notes="Qwen3Guard Technical Report Table 10, the 'before' row used as the RL baseline for Qwen3-4B-SafeRL. Judges (Qwen3-235B-Instruct-2507 + WildGuard) are explicitly NOT Qwen3Guard itself ('we avoid using Qwen3Guard for safety evaluation... to mitigate risk of metric hack'), so this is less self-referential than the SafeRL row, but still produced and reported by the Qwen team about their own base model.")
collapsed_no("Qwen/Qwen3-4B", "qwen3", 4022468096, "instruct",
  ["HELM_Safety","HELM_XSTest_overrefusal","AIR_Bench","SALAD","TrustLLM","JailbreakBench","HarmBench","GSM8K","OLB_v2"],
  HELM_NO_NOTE + " OLB v2: no row (post-dates leaderboard).")

R(repo="Qwen/Qwen3-4B-SafeRL", family="qwen3", n_params=4411424256, class_="safety_tuned",
  benchmark="other_card_safety", number_exists="yes",
  value="Safety Rate (Qwen3-235B judge)=86.5%; Safety Rate (WildGuard)=98.1%; Refusal (WildGuard)=5.3%",
  metric_name="Hybrid-reward SafeRL safety/refusal, Non-Think mode",
  setting="enable_thinking=False (matches panel thinking_flag). Released checkpoint = Hybrid-reward variant per its own HF card.",
  source_url="https://huggingface.co/Qwen/Qwen3-4B-SafeRL", source_type="card", checkpoint_exact_match=True,
  notes="NOT_INDEPENDENT (flagged per task instruction): Qwen3Guard-Gen-4B was the reward model used to TRAIN this checkpoint (Qwen3Guard Technical Report 2510.14276 Sec 3.5, Table 10). The safety EVAL itself uses Qwen3-235B-Instruct-2507-as-judge and WildGuard, which the paper says were chosen specifically to avoid grading with Qwen3Guard -- but training reward and eval are still both produced by the same team on their own held-out WildJailbreak split, not an external leaderboard. A second reward variant ('Guard-only': Safety 99.7%/WildGuard 100.0%/Refusal 96.6%) exists in the paper but was NOT released as this HF checkpoint per the card's own text.")
R(repo="Qwen/Qwen3-4B-SafeRL", family="qwen3", n_params=4411424256, class_="safety_tuned",
  benchmark="Arena_Hard", number_exists="yes", value=10.7, metric_name="ArenaHard-v2 (winrate vs GPT-4.1)",
  setting="enable_thinking=False, Hybrid reward", source_url="https://huggingface.co/Qwen/Qwen3-4B-SafeRL",
  source_type="card", checkpoint_exact_match=True,
  notes="Same card/table. Not directly comparable to the plain Arena-Hard v1 numbers used elsewhere in this census (ArenaHard-v2 is judged by GPT-4.1 winrate, a different protocol/scale).")
collapsed_no("Qwen/Qwen3-4B-SafeRL", "qwen3", 4411424256, "safety_tuned",
  ["HELM_Safety","HELM_XSTest_overrefusal","AIR_Bench","SALAD","TrustLLM","JailbreakBench","HarmBench","OLB_v2"],
  HELM_NO_NOTE + " Released 2025-10, post-dates OLB v2's active window.")

for repo, n in [("huihui-ai/Huihui-Qwen3-0.6B-abliterated-v2", 596049920),
                ("huihui-ai/Huihui-Qwen3-1.7B-abliterated-v2", 1720574976),
                ("mlabonne/Qwen3-4B-abliterated", 4022468096)]:
    R(repo=repo, family="qwen3", n_params=n, class_="abliterated",
      benchmark="HELM_Safety+HELM_XSTest_overrefusal+AIR_Bench+SALAD+TrustLLM+JailbreakBench+HarmBench+MMLU+GSM8K+Arena_Hard+OLB_v2",
      number_exists="no", source_url="checked card only (raw README)", source_type="card",
      checkpoint_exact_match=True,
      notes="Card grepped for mmlu|gsm8k|arena.hard|xstest|harmbench|refusal|benchmark keywords: zero hits. Card is boilerplate abliteration usage instructions with no evaluation section at all. Not in OLB v2 join (external_join.json), not in local HELM/AIR-Bench/SALAD tables.")

R(repo="DreamFast/qwen3-4b-heretic", family="qwen3", n_params=4022468096, class_="abliterated",
  benchmark="other_card_safety", number_exists="yes",
  value="Refusals: 3/100 (selected trial) vs 100/100 (original Qwen3-4B), self-reported by the Heretic tool's own trial-selection log",
  metric_name="Heretic internal refusal-rate optimizer output (undisclosed 100-prompt eval set, tool version v1.2.0)",
  setting="n/a", source_url="https://huggingface.co/DreamFast/qwen3-4b-heretic", source_type="card",
  checkpoint_exact_match=True,
  notes="SELF-REPORTED, methodology undisclosed on the card (no link to the 100-prompt set or judge used); this is the Heretic abliteration tool's own hyperparameter-search log printed verbatim on the card, not a named external benchmark (not XSTest/HarmBench/etc). Card has zero MMLU/GSM8K/Arena-Hard numbers.")
collapsed_no("DreamFast/qwen3-4b-heretic", "qwen3", 4022468096, "abliterated",
  ["HELM_Safety","HELM_XSTest_overrefusal","AIR_Bench","SALAD","TrustLLM","JailbreakBench","HarmBench","MMLU","GSM8K","Arena_Hard","OLB_v2"],
  "No named-benchmark numbers anywhere; not in OLB v2/HELM/AIR-Bench/SALAD local tables.")

R(repo="Qwen/Qwen3-4B-Base", family="qwen3", n_params=4022468096, class_="base",
  benchmark="GSM8K", number_exists="yes", value=74.14, metric_name="GSM8K (5-shot), base pretrained model",
  setting="base (no chat template)", source_url="https://huggingface.co/HuggingFaceTB/SmolLM3-3B",
  source_type="card", checkpoint_exact_match=True,
  notes="From SmolLM3-3B's own card 'Base Pre-Trained Model' comparison table (third-party eval of Qwen3-4B-Base as a baseline). No safety number expected/found for a base (non-chat) model; not applicable.")
collapsed_no("Qwen/Qwen3-4B-Base", "qwen3", 4022468096, "base",
  ["HELM_Safety","HELM_XSTest_overrefusal","AIR_Bench","SALAD","TrustLLM","JailbreakBench","HarmBench","OLB_v2"],
  HELM_NO_NOTE + " Safety benchmarks are not meaningfully applicable to a base (non-instruction-tuned) checkpoint; none found regardless.")

# ===========================================================================
# QWEN2.5 FAMILY
# ===========================================================================
R(repo="Qwen/Qwen2.5-0.5B-Instruct", family="qwen2.5", n_params=494032768, class_="instruct",
  benchmark="MMLU", number_exists="yes", value=24.1, metric_name="MMLU-Redux (Qwen2.5 report Table 10); also MMLU-Pro=15.0 same table",
  setting="default", source_url="https://arxiv.org/abs/2412.15115", source_type="paper",
  checkpoint_exact_match=True, notes="Qwen2.5 Technical Report Table 10 ('0.5B-1.5B instruction-tuned models'). GSM8K=49.6, IFEval=27.9 same table/row.")
R(repo="Qwen/Qwen2.5-0.5B-Instruct", family="qwen2.5", n_params=494032768, class_="instruct",
  benchmark="GSM8K", number_exists="yes", value=49.6, metric_name="GSM8K",
  setting="default", source_url="https://arxiv.org/abs/2412.15115", source_type="paper", checkpoint_exact_match=True,
  notes="Same Table 10. Cross-check discrepancy: SmolLM2-360M-Instruct's own HF card reports Qwen2.5-0.5B-Instruct GSM8K(5-shot)=26.8 and MMLU(cloze)=31.7 -- a different lighteval harness giving materially different absolute numbers for the identical checkpoint than Qwen's own self-reported 49.6/24.1. huihui-ai's CensorTune card reports yet a third set (IF_Eval=33.07, MMLU-Pro=17.18). All three are 'real' published numbers for the same exact repo; they simply disagree by harness, illustrating that these small-model numbers are not directly comparable across sources.")
R(repo="Qwen/Qwen2.5-0.5B-Instruct", family="qwen2.5", n_params=494032768, class_="instruct",
  benchmark="other_card_safety", number_exists="yes", value="201/320 = 62.8% harmful-instruction compliance ('Passed ratio')",
  metric_name="huihui-ai/harmbench_behaviors pass-rate (community-hosted HarmBench-behaviors variant, 320 prompts)",
  setting="default", source_url="https://huggingface.co/huihui-ai/Qwen2.5-0.5B-Instruct-CensorTune",
  source_type="card", checkpoint_exact_match=True,
  notes="Reported as the un-fine-tuned baseline row on a THIRD-PARTY community card (huihui-ai's CensorTune card), not on Qwen's own card/report. Self-reported by huihui-ai, methodology = huihui-ai's own TestPassed.py script against huihui-ai/harmbench_behaviors (a community-hosted derivative, not the official HarmBench leaderboard/harness). Treat as low-confidence but genuinely published.")
collapsed_no("Qwen/Qwen2.5-0.5B-Instruct", "qwen2.5", 494032768, "instruct",
  ["HELM_Safety","HELM_XSTest_overrefusal","AIR_Bench","SALAD","TrustLLM","JailbreakBench","Arena_Hard","OLB_v2"],
  HELM_NO_NOTE + " OLB v2 join: no row for this exact repo (checked in external_join.json rows list).")

R(repo="Qwen/Qwen2.5-1.5B-Instruct", family="qwen2.5", n_params=1543714304, class_="instruct",
  benchmark="OLB_v2", number_exists="yes", value=18.430509141644382, metric_name="olb2_average (Open LLM Leaderboard v2, IFEval+BBH+MATH-lvl5+GPQA+MUSR+MMLU-Pro composite)",
  setting="submission_date=2024-09-19", source_url="local:data/external/openllm_v2_contents.parquet via results/external_join.json",
  source_type="local_table", checkpoint_exact_match=True,
  notes="Exact repo_id join. Sub-scores: ifeval=44.76, bbh=19.81, math_lvl5=22.05, gpqa=0.78, musr=3.19, mmlu_pro=19.99.")
R(repo="Qwen/Qwen2.5-1.5B-Instruct", family="qwen2.5", n_params=1543714304, class_="instruct",
  benchmark="MMLU", number_exists="yes", value=32.4, metric_name="MMLU-Pro (Qwen2.5 report Table 10); MMLU-Redux=50.7 same table",
  setting="default", source_url="https://arxiv.org/abs/2412.15115", source_type="paper", checkpoint_exact_match=True,
  notes="GSM8K=73.2, IFEval=42.5 same row/table. Cross-check: Falcon3-1B-Instruct's own card reports Qwen2.5-1.5B MMLU(5-shot)=59.8/GSM8K(5-shot)=57.8; SmolLM2-1.7B's card reports Qwen2.5-1.5B-Instruct IFEval=47.4/MMLU-Pro=24.2/GSM8K=42.8 -- three more disagreeing harness-specific numbers for this one checkpoint.")
R(repo="Qwen/Qwen2.5-1.5B-Instruct", family="qwen2.5", n_params=1543714304, class_="instruct",
  benchmark="other_card_safety", number_exists="yes", value=77.6,
  metric_name="'Safety' composite score, AI2 Tulu-3 evaluation suite (0-100)",
  setting="default", source_url="https://huggingface.co/allenai/OLMo-2-0425-1B-Instruct", source_type="card",
  checkpoint_exact_match=True,
  notes="INDEPENDENT THIRD PARTY: reported on AI2's OLMo-2-0425-1B-Instruct card as a baseline comparison row ('Qwen 2.5 1.5B'), not on Qwen's own materials. AI2's 'Safety' column methodology is the Tulu-3 eval-suite composite (not individually broken out here into XSTest/WildGuard/etc. -- treated as other_card_safety rather than a single named benchmark from the task's list).")
R(repo="Qwen/Qwen2.5-1.5B-Instruct", family="qwen2.5", n_params=1543714304, class_="instruct",
  benchmark="other_card_safety", number_exists="yes", value="73/320 = 22.81% harmful-instruction compliance",
  metric_name="huihui-ai/harmbench_behaviors pass-rate (community variant)",
  setting="default", source_url="https://huggingface.co/huihui-ai/Qwen2.5-1.5B-Instruct-CensorTune", source_type="card",
  checkpoint_exact_match=True, notes="Same caveats as the 0.5B CensorTune row above (self-reported, community dataset).")
collapsed_no("Qwen/Qwen2.5-1.5B-Instruct", "qwen2.5", 1543714304, "instruct",
  ["HELM_Safety","HELM_XSTest_overrefusal","AIR_Bench","SALAD","TrustLLM","JailbreakBench","HarmBench","Arena_Hard"],
  HELM_NO_NOTE)

R(repo="huihui-ai/Qwen2.5-0.5B-Instruct-CensorTune", family="qwen2.5", n_params=494032768, class_="blanket_refuser",
  benchmark="other_card_safety", number_exists="yes", value="0/320 = 0.00% harmful-instruction compliance",
  metric_name="huihui-ai/harmbench_behaviors pass-rate (own card, self test)",
  setting="default", source_url="https://huggingface.co/huihui-ai/Qwen2.5-0.5B-Instruct-CensorTune",
  source_type="card", checkpoint_exact_match=True,
  notes="SELF-REPORTED by the fine-tuner on their own card using their own community-hosted harmbench_behaviors dataset and TestPassed.py script; not an independent/official leaderboard. This is the one community-fine-tune EXCEPTION found in this census with a published safety-adjacent number.")
R(repo="huihui-ai/Qwen2.5-0.5B-Instruct-CensorTune", family="qwen2.5", n_params=494032768, class_="blanket_refuser",
  benchmark="MMLU", number_exists="yes", value=17.09, metric_name="MMLU Pro (own card re-eval)",
  setting="default", source_url="https://huggingface.co/huihui-ai/Qwen2.5-0.5B-Instruct-CensorTune",
  source_type="card", checkpoint_exact_match=True, notes="Card also reports IF_Eval=16.20, BBH=32.51, GPQA=25.25, TruthfulQA=45.48.")
collapsed_no("huihui-ai/Qwen2.5-0.5B-Instruct-CensorTune", "qwen2.5", 494032768, "blanket_refuser",
  ["HELM_Safety","HELM_XSTest_overrefusal","AIR_Bench","SALAD","TrustLLM","JailbreakBench","HarmBench(official)","GSM8K","Arena_Hard","OLB_v2"],
  "No hit on any official leaderboard/local table; the harmbench_behaviors number above is a community self-test, not the official HarmBench leaderboard.")

R(repo="huihui-ai/Qwen2.5-1.5B-Instruct-CensorTune", family="qwen2.5", n_params=1543714304, class_="blanket_refuser",
  benchmark="other_card_safety", number_exists="yes", value="0/320 = 0.00% harmful-instruction compliance",
  metric_name="huihui-ai/harmbench_behaviors pass-rate (own card, self test)",
  setting="default", source_url="https://huggingface.co/huihui-ai/Qwen2.5-1.5B-Instruct-CensorTune",
  source_type="card", checkpoint_exact_match=True, notes="Same pattern as the 0.5B CensorTune row.")
collapsed_no("huihui-ai/Qwen2.5-1.5B-Instruct-CensorTune", "qwen2.5", 1543714304, "blanket_refuser",
  ["HELM_Safety","HELM_XSTest_overrefusal","AIR_Bench","SALAD","TrustLLM","JailbreakBench","HarmBench(official)","MMLU","GSM8K","Arena_Hard","OLB_v2"],
  "Card has an 'Evaluations' capability table too but with different columns per its README structure; no official-leaderboard hit found.")

R(repo="Goekdeniz-Guelmez/Josiefied-Qwen2.5-1.5B-Instruct-abliterated-v1", family="qwen2.5", n_params=1777088000,
  class_="abliterated", benchmark="OLB_v2", number_exists="yes", value=18.44117473256343,
  metric_name="olb2_average", setting="submission_date=2024-09-28",
  source_url="local:data/external/openllm_v2_contents.parquet via results/external_join.json",
  source_type="local_table", checkpoint_exact_match=True,
  notes="Sub-scores: ifeval=47.69, bbh=18.31, math_lvl5=20.85, gpqa=0.0, musr=4.00, mmlu_pro=19.81. This is a CAPABILITY number only; no safety number found anywhere for this checkpoint (card checked, no benchmark keywords).")
collapsed_no("Goekdeniz-Guelmez/Josiefied-Qwen2.5-1.5B-Instruct-abliterated-v1", "qwen2.5", 1777088000, "abliterated",
  ["HELM_Safety","HELM_XSTest_overrefusal","AIR_Bench","SALAD","TrustLLM","JailbreakBench","HarmBench"],
  HELM_NO_NOTE + " Own card has zero MMLU/GSM8K/safety keyword hits (checked separately from the OLB v2 join).")

R(repo="Qwen/Qwen2.5-3B-Instruct", family="qwen2.5", n_params=3085938688, class_="instruct",
  benchmark="OLB_v2", number_exists="yes", value=27.16175720903232, metric_name="olb2_average",
  setting="submission_date=2024-09-19", source_url="local:data/external/openllm_v2_contents.parquet via results/external_join.json",
  source_type="local_table", checkpoint_exact_match=True, notes="Sub-scores: ifeval=64.75, bbh=25.80, math_lvl5=36.78, gpqa=3.02, musr=7.57, mmlu_pro=25.05.")
R(repo="Qwen/Qwen2.5-3B-Instruct", family="qwen2.5", n_params=3085938688, class_="instruct",
  benchmark="Arena_Hard", number_exists="yes", value=32.0, metric_name="Arena-Hard v1",
  setting="default", source_url="https://arxiv.org/abs/2503.01743", source_type="paper", checkpoint_exact_match=True,
  notes="Third-party: Microsoft's Phi-4-mini Technical Report Table (Sec 'Model Quality') comparison row. Same table gives MMLU(5-shot)=65.0, MMLU-Pro=44.7, BigBenchHard=56.2, GSM8K(8-shot,CoT)=80.6, ARC-Challenge=82.6.")
R(repo="Qwen/Qwen2.5-3B-Instruct", family="qwen2.5", n_params=3085938688, class_="instruct",
  benchmark="HELM_XSTest_overrefusal", number_exists="yes", value="IPRR=92%, VPRR=25.6%",
  metric_name="XSTest via Phi-4-mini paper's own harness (NOT the HELM XSTest scenario)",
  setting="default", source_url="https://arxiv.org/abs/2503.01743", source_type="paper", checkpoint_exact_match=True,
  notes="IMPORTANT: this is XSTest run by Microsoft's Phi-4-mini team as a third-party comparison (their Table 12), NOT HELM's XSTest scenario -- filed under HELM_XSTest_overrefusal only because it is the closest benchmark bucket in the task's taxonomy; treat as 'other_card_safety'-style provenance. IPRR=Inappropriate-Prompt Refusal Rate (higher better), VPRR=Valid-Prompt Refusal Rate (lower better, i.e. over-refusal).")
R(repo="Qwen/Qwen2.5-3B-Instruct", family="qwen2.5", n_params=3085938688, class_="instruct",
  benchmark="other_card_safety", number_exists="yes", value="Defect Rate avg=4.25% (no-JB), 14% (with known jailbreaks)",
  metric_name="Azure AI RAI Defect Rate across Violence/Sexual/Self-Harm/Hateful categories (GPT-4o-simulated adversarial conversations)",
  setting="default", source_url="https://arxiv.org/abs/2503.01743", source_type="paper", checkpoint_exact_match=True,
  notes="Phi-4-mini paper Tables 10-11, third-party comparison row for Qwen2.5-3B.")
collapsed_no("Qwen/Qwen2.5-3B-Instruct", "qwen2.5", 3085938688, "instruct",
  ["HELM_Safety","AIR_Bench","SALAD","TrustLLM","JailbreakBench","HarmBench"], HELM_NO_NOTE)

# ===========================================================================
# TINYLLAMA FAMILY
# ===========================================================================
R(repo="TinyLlama/TinyLlama-1.1B-Chat-v1.0", family="tinyllama", n_params=1100048384, class_="instruct",
  benchmark="OLB_v2", number_exists="yes", value=2.818859486124847, metric_name="olb2_average",
  setting="submission_date=2024-08-04", source_url="local:data/external/openllm_v2_contents.parquet via results/external_join.json",
  source_type="local_table", checkpoint_exact_match=True, notes="Sub-scores: ifeval=5.96, bbh=4.01, math_lvl5=1.51, gpqa=0.0, musr=4.31, mmlu_pro=1.12.")
R(repo="TinyLlama/TinyLlama-1.1B-Chat-v1.0", family="tinyllama", n_params=1100048384, class_="instruct",
  benchmark="MMLU", number_exists="yes", value=0.253901737256654, metric_name="MMLU (0-100 rescaled to 0-1)",
  setting="default", source_url="local:data/external/openllm_v1_old_contents.parquet (open-llm-leaderboard-old/contents @ 791ca1c) via results/external_join.json",
  source_type="local_table", checkpoint_exact_match=True,
  notes="v1-old fallback, used only because openllm_capability.json had no direct hit (that file is only a 40-row alphabetic slice of the 7,116-repo archive, not a full join).")
R(repo="TinyLlama/TinyLlama-1.1B-Chat-v1.0", family="tinyllama", n_params=1100048384, class_="instruct",
  benchmark="GSM8K", number_exists="yes", value=0.02350265352539803, metric_name="GSM8K (0-100 rescaled to 0-1)",
  setting="default", source_url="local:data/external/openllm_v1_old_contents.parquet via results/external_join.json",
  source_type="local_table", checkpoint_exact_match=True, notes="Same v1-old fallback row as MMLU above.")
collapsed_no("TinyLlama/TinyLlama-1.1B-Chat-v1.0", "tinyllama", 1100048384, "instruct",
  ["HELM_Safety","HELM_XSTest_overrefusal","AIR_Bench","SALAD","TrustLLM","JailbreakBench","HarmBench","Arena_Hard"],
  HELM_NO_NOTE + " No dedicated TinyLlama technical report/card safety section found; the original TinyLlama paper (2401.02385) reports only pretraining perplexity/downstream-task accuracy, no safety evaluation.")

for repo in ["AIPlans/TinyLlama-1.1B-IPO-PKU-SafeRLHF", "AIPlans/TinyLlama-1.1B-ORPO-PKU-SafeRLHF",
             "AIPlans/tinyllama-1.1b-dpo-pku-saferlhf"]:
    R(repo=repo, family="tinyllama", n_params=1100048384, class_="safety_tuned",
      benchmark="HELM_Safety+HELM_XSTest_overrefusal+AIR_Bench+SALAD+TrustLLM+JailbreakBench+HarmBench+MMLU+GSM8K+Arena_Hard+OLB_v2",
      number_exists="no", source_url="checked card only (raw README)", source_type="card", checkpoint_exact_match=True,
      notes="Card is an auto-generated HF Trainer model-card template. It reports only training-time DPO/IPO/ORPO loss and preference-pair 'Rewards/accuracies' (an internal training diagnostic, not an evaluated benchmark score) -- e.g. Rewards/accuracies=0.7389. No XSTest/HarmBench/MMLU/GSM8K/Arena-Hard number anywhere. Not in OLB v2 join.")

R(repo="Shortmund09/MLDM-TinyLlama-1.1b-gcpo-ocra-saferlhf", family="tinyllama", n_params=1100048384, class_="safety_tuned",
  benchmark="HELM_Safety+HELM_XSTest_overrefusal+AIR_Bench+SALAD+TrustLLM+JailbreakBench+HarmBench+MMLU+GSM8K+Arena_Hard+OLB_v2",
  number_exists="no", source_url="checked card only", source_type="card", checkpoint_exact_match=True,
  notes="Card raw README is literally the single word 'hello' (6 bytes) -- effectively no card content at all, let alone a benchmark number.")

# ===========================================================================
# GEMMA2 FAMILY
# ===========================================================================
R(repo="unsloth/gemma-2-2b-it", family="gemma2", n_params=2614341888, class_="instruct",
  benchmark="OLB_v2", number_exists="yes", value=17.046939294966545, metric_name="olb2_average",
  setting="submission_date=2024-07-31", source_url="local:data/external/openllm_v2_contents.parquet via results/external_join.json",
  source_type="local_table", checkpoint_exact_match=True,
  notes="Identical row also present under google/gemma-2-2b-it in the local join (both resolve to the same weights). Sub-scores: ifeval=56.68, bbh=17.98, math_lvl5=0.08, gpqa=3.24, musr=7.08, mmlu_pro=17.22.")
R(repo="unsloth/gemma-2-2b-it", family="gemma2", n_params=2614341888, class_="instruct",
  benchmark="MMLU", number_exists="yes", value=56.1, metric_name="MMLU (5-shot), instruction-tuned",
  setting="default", source_url="https://arxiv.org/abs/2408.00118", source_type="paper", checkpoint_exact_match=True,
  notes="Gemma 2 Technical Report Table 17 (PT vs IT comparison), row 'Gemma-2 IT 2B'. checkpoint_exact_match=True because unsloth/gemma-2-2b-it is an unquantized re-upload of the identical google/gemma-2-2b-it weights (the official HF card itself is gated and returned 'Access restricted' on raw README fetch in this session).")
R(repo="unsloth/gemma-2-2b-it", family="gemma2", n_params=2614341888, class_="instruct",
  benchmark="other_card_safety", number_exists="yes",
  value="Human-preference Safety win-rate vs GPT-4o-2024-05-13 = 57.5% (Win 53% / Tie 9% / Loss 38%)",
  metric_name="Human single-sided safety preference (held-out safety prompt set)",
  setting="default", source_url="https://arxiv.org/abs/2408.00118", source_type="paper", checkpoint_exact_match=True,
  notes="Gemma 2 Technical Report Table 15, row 'Gemma 2 IT 2B'.")
R(repo="unsloth/gemma-2-2b-it", family="gemma2", n_params=2614341888, class_="instruct",
  benchmark="other_card_safety", number_exists="yes",
  value="RealToxicity avg tox=8.16; CrowS-Pairs=37.67; BBQ Ambig=83.20; BBQ Disambig=69.31; TruthfulQA MC2Acc=43.72",
  metric_name="Academic safety/bias benchmark suite", setting="default",
  source_url="https://arxiv.org/abs/2408.00118", source_type="paper", checkpoint_exact_match=True,
  notes="Gemma 2 Technical Report Table 18, row labelled 'Gemma 2 IT 2.6B' (their own parameter-count label for the same 2B-class checkpoint).")
R(repo="unsloth/gemma-2-2b-it", family="gemma2", n_params=2614341888, class_="instruct",
  benchmark="GSM8K", number_exists="yes", value=63.2, metric_name="GSM8K (5-shot)",
  setting="default", source_url="https://arxiv.org/abs/2412.15115", source_type="paper", checkpoint_exact_match=True,
  notes="Third-party: Qwen2.5 Technical Report Table 9 ('2B-4B instruction-tuned models'), row 'Gemma2-2B' -- MMLU-Pro=26.7, MMLU-Redux=51.9, IFEval=51.0 same row. Label just says 'Gemma2-2B' without explicit '-it' suffix but the table is titled 'instruction-tuned models' and uses IFEval, so it is the IT checkpoint.")
collapsed_no("unsloth/gemma-2-2b-it", "gemma2", 2614341888, "instruct",
  ["HELM_Safety","HELM_XSTest_overrefusal","AIR_Bench","SALAD","TrustLLM","JailbreakBench","HarmBench","Arena_Hard"],
  HELM_NO_NOTE + " Official google/gemma-2-2b-it card raw README returned 'Access to model ... is restricted' (gated, needs HF auth) in this session; capability/safety numbers above are sourced from the arXiv report and third-party cards instead.")

R(repo="IlyaGusev/gemma-2-2b-it-abliterated", family="gemma2", n_params=2614341888, class_="abliterated",
  benchmark="OLB_v2", number_exists="yes", value=16.705746365531194, metric_name="olb2_average",
  setting="submission_date=2025-01-07", source_url="local:data/external/openllm_v2_contents.parquet via results/external_join.json",
  source_type="local_table", checkpoint_exact_match=True,
  notes="Sub-scores: ifeval=53.31, bbh=16.80, math_lvl5=6.12, gpqa=2.01, musr=4.91, mmlu_pro=17.09. Capability only; card itself has zero safety-keyword hits.")
collapsed_no("IlyaGusev/gemma-2-2b-it-abliterated", "gemma2", 2614341888, "abliterated",
  ["HELM_Safety","HELM_XSTest_overrefusal","AIR_Bench","SALAD","TrustLLM","JailbreakBench","HarmBench"], HELM_NO_NOTE)

R(repo="Robust-Decoding/gemma2-2b-it-hh-dpo-harmless-step-6000", family="gemma2", n_params=2614341888,
  class_="safety_tuned",
  benchmark="HELM_Safety+HELM_XSTest_overrefusal+AIR_Bench+SALAD+TrustLLM+JailbreakBench+HarmBench+MMLU+GSM8K+Arena_Hard+OLB_v2",
  number_exists="no", source_url="checked card only", source_type="card", checkpoint_exact_match=True,
  notes="Card is the unfilled HF default template ('[More Information Needed]' throughout, no model description, no eval section at all) despite the repo name indicating Anthropic-HH-style DPO-for-harmlessness training. Not in OLB v2 join.")

# ===========================================================================
# LLAMA-3.2 FAMILY
# ===========================================================================
R(repo="unsloth/Llama-3.2-1B-Instruct", family="llama3.2", n_params=1235814400, class_="instruct",
  benchmark="OLB_v2", number_exists="yes", value=14.532450983938604, metric_name="olb2_average",
  setting="submission_date=2025-01-23", source_url="local:data/external/openllm_v2_contents.parquet via results/external_join.json",
  source_type="local_table", checkpoint_exact_match=True, notes="Sub-scores: ifeval=58.10, bbh=8.32, math_lvl5=8.23, gpqa=2.35, musr=1.95, mmlu_pro=8.24.")
R(repo="unsloth/Llama-3.2-1B-Instruct", family="llama3.2", n_params=1235814400, class_="instruct",
  benchmark="MMLU", number_exists="yes", value=68.2, metric_name="MMLU (5-shot)",
  setting="default", source_url="https://huggingface.co/tiiuae/Falcon3-1B-Instruct", source_type="card",
  checkpoint_exact_match=True,
  notes="Third-party: TII's Falcon3-1B-Instruct card comparison table, column header 'Llama-3.2-1B' (no explicit -Instruct suffix, but table is evaluated with chat template + IFEval so is the instruct checkpoint). Same table: GSM8K(5-shot)=82.6, MMLU-Pro=16, IFEval=55.3. NOTE: this is far higher than the 58.1 IFEval reported by OLB v2 for the same nominal checkpoint above -- harness-dependent again.")
R(repo="unsloth/Llama-3.2-1B-Instruct", family="llama3.2", n_params=1235814400, class_="instruct",
  benchmark="other_card_safety", number_exists="yes",
  value="Over-Refusal=81.86, Safety&Alignment=96.30, Overall=63.99 (aiXamine composite, 0-100)",
  metric_name="aiXamine leaderboard: Over-Refusal (OK-Test/OR-Bench/WildGuard/XSTest composite) and Safety&Alignment services",
  setting="default", source_url="https://arxiv.org/abs/2504.14985", source_type="paper", checkpoint_exact_match=True,
  notes="INDEPENDENT THIRD-PARTY academic paper (aiXamine, April 2025), model listed as 'Llama3.2-1B' in Table 6, an open-source HF chat model so almost certainly the Instruct checkpoint. Over-Refusal sub-scores from their Table 3.7 section: OK-Test=94.57, OR-Bench=57.01, WildGuard=86.51, XSTest=89.33.")
collapsed_no("unsloth/Llama-3.2-1B-Instruct", "llama3.2", 1235814400, "instruct",
  ["HELM_Safety","HELM_XSTest_overrefusal(HELM-native)","AIR_Bench","SALAD","TrustLLM","JailbreakBench","HarmBench","GSM8K(HELM/Arena-Hard)"],
  HELM_NO_NOTE + " Official meta-llama/Llama-3.2-1B-Instruct card raw README returned 'Access ... is restricted' (gated) in this session; no official Meta safety table was reachable this way.")

R(repo="unsloth/Llama-3.2-3B-Instruct", family="llama3.2", n_params=3212749824, class_="instruct",
  benchmark="OLB_v2", number_exists="yes", value=24.204650807793456, metric_name="olb2_average",
  setting="submission_date=2024-09-27", source_url="local:data/external/openllm_v2_contents.parquet via results/external_join.json",
  source_type="local_table", checkpoint_exact_match=True, notes="Sub-scores: ifeval=73.93, bbh=24.06, math_lvl5=17.67, gpqa=3.80, musr=1.37, mmlu_pro=24.39.")
R(repo="unsloth/Llama-3.2-3B-Instruct", family="llama3.2", n_params=3212749824, class_="instruct",
  benchmark="Arena_Hard", number_exists="yes", value=17.0, metric_name="Arena-Hard v1",
  setting="default", source_url="https://arxiv.org/abs/2503.01743", source_type="paper", checkpoint_exact_match=True,
  notes="Third-party: Microsoft Phi-4-mini Technical Report comparison table (column 'Llama-3.2-3B-Ins'). Same table: MMLU(5-shot)=61.8, MMLU-Pro=39.2, BBH=55.4, GSM8K(8-shot,CoT)=75.6.")
R(repo="unsloth/Llama-3.2-3B-Instruct", family="llama3.2", n_params=3212749824, class_="instruct",
  benchmark="HELM_XSTest_overrefusal", number_exists="yes", value="IPRR=92.5%, VPRR=15.6%",
  metric_name="XSTest via Phi-4-mini paper's harness (NOT HELM's XSTest scenario -- see note)",
  setting="default", source_url="https://arxiv.org/abs/2503.01743", source_type="paper", checkpoint_exact_match=True,
  notes="Same caveat as the Qwen2.5-3B-Instruct XSTest row: this is Microsoft's own third-party XSTest run, not HELM's. Filed here only because it is the closest bucket in the task's benchmark taxonomy.")
R(repo="unsloth/Llama-3.2-3B-Instruct", family="llama3.2", n_params=3212749824, class_="instruct",
  benchmark="other_card_safety", number_exists="yes",
  value="Defect Rate avg=5% (no-JB) / 8% (with jailbreaks) [Phi-4-mini paper]; Over-Refusal=93.77 / Safety&Alignment=94.67 / Overall=73.04 [aiXamine paper]",
  metric_name="Two independent third-party safety composites", setting="default",
  source_url="https://arxiv.org/abs/2503.01743 ; https://arxiv.org/abs/2504.14985", source_type="paper",
  checkpoint_exact_match=True,
  notes="aiXamine Over-Refusal sub-scores: OK-Test=95.43, OR-Bench=94.24, WildGuard=96.09, XSTest=89.33.")
collapsed_no("unsloth/Llama-3.2-3B-Instruct", "llama3.2", 3212749824, "instruct",
  ["HELM_Safety(HELM-native)","AIR_Bench","SALAD","TrustLLM","JailbreakBench","HarmBench"], HELM_NO_NOTE)

R(repo="huihui-ai/Llama-3.2-3B-Instruct-abliterated", family="llama3.2", n_params=3606752256, class_="abliterated",
  benchmark="MMLU", number_exists="yes", value=28.00, metric_name="MMLU Pro (own card re-eval, abliterated vs original comparison)",
  setting="default", source_url="https://huggingface.co/huihui-ai/Llama-3.2-3B-Instruct-abliterated",
  source_type="card", checkpoint_exact_match=True,
  notes="Self-reported re-evaluation on the fine-tuner's own card: IF_Eval=76.76, MMLU Pro=28.00, TruthfulQA=50.73, BBH=41.86, GPQA=28.41 (vs original Llama-3.2-3B-Instruct: 76.55/27.88/50.55/41.81/28.39 same row). Capability only -- no safety/refusal number on this card.")
collapsed_no("huihui-ai/Llama-3.2-3B-Instruct-abliterated", "llama3.2", 3606752256, "abliterated",
  ["HELM_Safety","HELM_XSTest_overrefusal","AIR_Bench","SALAD","TrustLLM","JailbreakBench","HarmBench","GSM8K","Arena_Hard","OLB_v2"],
  HELM_NO_NOTE + " Not in OLB v2 join.")

# ===========================================================================
# PHI FAMILY
# ===========================================================================
R(repo="microsoft/Phi-4-mini-instruct", family="phi", n_params=3836021760, class_="instruct",
  benchmark="Arena_Hard", number_exists="yes", value=32.8, metric_name="Arena-Hard v1",
  setting="default", source_url="https://arxiv.org/abs/2503.01743", source_type="paper", checkpoint_exact_match=True,
  notes="Own official technical report / HF card 'Model Quality' table. Same table: MMLU(5-shot)=67.3, MMLU-Pro(0-shot,CoT)=52.8, BigBenchHard=70.4, GSM8K(8-shot,CoT)=88.6, ARC-Challenge=83.7.")
R(repo="microsoft/Phi-4-mini-instruct", family="phi", n_params=3836021760, class_="instruct",
  benchmark="HELM_XSTest_overrefusal", number_exists="yes", value="IPRR=93.5%, VPRR=20.8%",
  metric_name="XSTest via Phi-4-mini paper's own harness (NOT HELM's XSTest scenario)",
  setting="default", source_url="https://arxiv.org/abs/2503.01743", source_type="paper", checkpoint_exact_match=True,
  notes="Own official Table 12.")
R(repo="microsoft/Phi-4-mini-instruct", family="phi", n_params=3836021760, class_="instruct",
  benchmark="other_card_safety", number_exists="yes",
  value="Defect Rate avg=3.75% (no-JB) / 1.25% (with known jailbreaks)",
  metric_name="Azure AI RAI Defect Rate (Violence/Sexual/Self-Harm/Hateful, GPT-4o-simulated adversarial conv.)",
  setting="default", source_url="https://arxiv.org/abs/2503.01743", source_type="paper", checkpoint_exact_match=True,
  notes="Own official Tables 10-11. This is the single best-covered checkpoint in the whole panel for named safety numbers.")
collapsed_no("microsoft/Phi-4-mini-instruct", "phi", 3836021760, "instruct",
  ["HELM_Safety(HELM-native)","AIR_Bench","SALAD","TrustLLM","JailbreakBench","HarmBench","OLB_v2"],
  HELM_NO_NOTE + " Not in OLB v2 join (released 2025-02, checked against external_join.json rows -- no hit).")

R(repo="lunahr/Phi-4-mini-instruct-abliterated", family="phi", n_params=3836021760, class_="abliterated",
  benchmark="HELM_Safety+HELM_XSTest_overrefusal+AIR_Bench+SALAD+TrustLLM+JailbreakBench+HarmBench+MMLU+GSM8K+Arena_Hard+OLB_v2",
  number_exists="no", source_url="https://huggingface.co/lunahr/Phi-4-mini-instruct-abliterated", source_type="card",
  checkpoint_exact_match=True,
  notes="IMPORTANT: the card DOES contain a large benchmark table (Arena-Hard=32.8, MMLU=67.3, GSM8K etc.) but it is a VERBATIM COPY of Microsoft's original Phi-4-mini-instruct comparison table, not a re-evaluation of the abliterated checkpoint itself (no 'abliterated' row/column anywhere, no re-eval methodology described). Recorded here as number_exists=no for THIS checkpoint; the copied numbers are already captured under microsoft/Phi-4-mini-instruct above.")

R(repo="microsoft/Phi-3.5-mini-instruct", family="phi", n_params=3821079552, class_="instruct",
  benchmark="Arena_Hard", number_exists="yes", value=34.4, metric_name="Arena-Hard v1",
  setting="default", source_url="https://arxiv.org/abs/2503.01743", source_type="paper", checkpoint_exact_match=True,
  notes="Third-party (but same vendor/Microsoft): Phi-4-mini paper's own comparison table, column 'Phi-3.5-mini-Ins'. Same table: MMLU=65.5, MMLU-Pro=47.4, BBH=63.1.")
R(repo="microsoft/Phi-3.5-mini-instruct", family="phi", n_params=3821079552, class_="instruct",
  benchmark="MMLU", number_exists="yes", value=67.7, metric_name="MMLU-Redux",
  setting="default", source_url="https://arxiv.org/abs/2412.15115", source_type="paper", checkpoint_exact_match=True,
  notes="Third-party: Qwen2.5 Technical Report Table 9, column 'Phi3.5-Mini'. Same table: MMLU-Pro=47.5, GSM8K=86.2, IFEval=52.1.")
R(repo="microsoft/Phi-3.5-mini-instruct", family="phi", n_params=3821079552, class_="instruct",
  benchmark="HELM_XSTest_overrefusal", number_exists="yes", value="IPRR=87%, VPRR=21.2%",
  metric_name="XSTest via Phi-4-mini paper's harness (own-vendor retrospective comparison, NOT HELM's scenario)",
  setting="default", source_url="https://arxiv.org/abs/2503.01743", source_type="paper", checkpoint_exact_match=True, notes="")
R(repo="microsoft/Phi-3.5-mini-instruct", family="phi", n_params=3821079552, class_="instruct",
  benchmark="other_card_safety", number_exists="yes", value="Defect Rate avg=4% (no-JB) / 7.5% (with jailbreaks)",
  metric_name="Azure AI RAI Defect Rate", setting="default", source_url="https://arxiv.org/abs/2503.01743",
  source_type="paper", checkpoint_exact_match=True, notes="Phi-4-mini paper's retrospective comparison of its own predecessor.")
collapsed_no("microsoft/Phi-3.5-mini-instruct", "phi", 3821079552, "instruct",
  ["HELM_Safety(HELM-native)","AIR_Bench","SALAD","TrustLLM","JailbreakBench","HarmBench","GSM8K(OLB)","OLB_v2"],
  HELM_NO_NOTE + " Not in OLB v2 join.")

# ===========================================================================
# OLMO2 FAMILY
# ===========================================================================
R(repo="allenai/OLMo-2-0425-1B-Instruct", family="olmo2", n_params=1484916736, class_="instruct",
  benchmark="other_card_safety", number_exists="yes", value=87.6,
  metric_name="'Safety' composite score, AI2 Tulu-3 evaluation suite (0-100), final RLVR 'OLMo 2 1B' row",
  setting="default", source_url="https://huggingface.co/allenai/OLMo-2-0425-1B-Instruct", source_type="card",
  checkpoint_exact_match=True,
  notes="Own official card 'Performance' table, final row 'OLMo 2 1B' (distinct from the intermediate 'OLMo 2 1B SFT'=93.2 and 'OLMo 2 1B DPO'=89.9 rows -- the final row is the one matching this exact -Instruct repo per AI2's Tulu3 pipeline). Same row: Average=42.7, MMLU=40.0, GSM8K=68.3, IFEval=70.1, MATH=20.7.")
R(repo="allenai/OLMo-2-0425-1B-Instruct", family="olmo2", n_params=1484916736, class_="instruct",
  benchmark="MMLU", number_exists="yes", value=40.0, metric_name="MMLU",
  setting="default", source_url="https://huggingface.co/allenai/OLMo-2-0425-1B-Instruct", source_type="card",
  checkpoint_exact_match=True, notes="Same table/row as above.")
R(repo="allenai/OLMo-2-0425-1B-Instruct", family="olmo2", n_params=1484916736, class_="instruct",
  benchmark="GSM8K", number_exists="yes", value=68.3, metric_name="GSM8K", setting="default",
  source_url="https://huggingface.co/allenai/OLMo-2-0425-1B-Instruct", source_type="card",
  checkpoint_exact_match=True, notes="Same table/row.")
collapsed_no("allenai/OLMo-2-0425-1B-Instruct", "olmo2", 1484916736, "instruct",
  ["HELM_Safety","HELM_XSTest_overrefusal","AIR_Bench","SALAD","TrustLLM","JailbreakBench","HarmBench","Arena_Hard","OLB_v2"],
  HELM_NO_NOTE + " Card explicitly states: 'The OLMo-2 models have limited safety training ... the model can produce problematic outputs (especially when prompted to do so).' Not in OLB v2 join.")

# ===========================================================================
# SMOLLM FAMILY
# ===========================================================================
R(repo="HuggingFaceTB/SmolLM2-360M-Instruct", family="smollm", n_params=361821120, class_="instruct",
  benchmark="MMLU", number_exists="yes", value=32.8, metric_name="MMLU (cloze)",
  setting="default", source_url="https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct", source_type="card",
  checkpoint_exact_match=True, notes="Own official card 'Instruction Model' table. Same row: IFEval(avg prompt/inst)=41.0, BBH(3-shot)=27.3, GSM8K(5-shot)=7.43.")
R(repo="HuggingFaceTB/SmolLM2-360M-Instruct", family="smollm", n_params=361821120, class_="instruct",
  benchmark="GSM8K", number_exists="yes", value=7.43, metric_name="GSM8K (5-shot)", setting="default",
  source_url="https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct", source_type="card",
  checkpoint_exact_match=True, notes="Same table.")
collapsed_no("HuggingFaceTB/SmolLM2-360M-Instruct", "smollm", 361821120, "instruct",
  ["HELM_Safety","HELM_XSTest_overrefusal","AIR_Bench","SALAD","TrustLLM","JailbreakBench","HarmBench","Arena_Hard","OLB_v2"],
  HELM_NO_NOTE + " SmolLM2 arXiv report (2502.02737) has no dedicated safety section for any size. Not in OLB v2 join.")

R(repo="HuggingFaceTB/SmolLM2-1.7B-Instruct", family="smollm", n_params=1711376384, class_="instruct",
  benchmark="MMLU", number_exists="yes", value=19.3, metric_name="MMLU-Pro (MCF)",
  setting="default", source_url="https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B-Instruct", source_type="card",
  checkpoint_exact_match=True,
  notes="Own official card table: IFEval=56.7, GSM8K(5-shot)=48.2. Cross-check: the SmolLM2 arXiv paper's own Table 5 reports GSM8K=48.8 for the same nominal checkpoint (card vs. paper differ by 0.6 points, a smaller but still real cross-source discrepancy) and MMLU-Pro=19.3 (matches).")
R(repo="HuggingFaceTB/SmolLM2-1.7B-Instruct", family="smollm", n_params=1711376384, class_="instruct",
  benchmark="GSM8K", number_exists="yes", value=48.2, metric_name="GSM8K (5-shot), card version (paper reports 48.8)",
  setting="default", source_url="https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B-Instruct", source_type="card",
  checkpoint_exact_match=True, notes="")
R(repo="HuggingFaceTB/SmolLM2-1.7B-Instruct", family="smollm", n_params=1711376384, class_="instruct",
  benchmark="other_card_safety", number_exists="yes", value=52.4,
  metric_name="'Safety' composite score, AI2 Tulu-3 evaluation suite (0-100)",
  setting="default", source_url="https://huggingface.co/allenai/OLMo-2-0425-1B-Instruct", source_type="card",
  checkpoint_exact_match=True,
  notes="INDEPENDENT THIRD PARTY: AI2's OLMo-2-0425-1B-Instruct card baseline row 'SmolLM2 1.7B'. Same row: MMLU=34.3, GSM8K=45.3, IFEval=51.6.")
collapsed_no("HuggingFaceTB/SmolLM2-1.7B-Instruct", "smollm", 1711376384, "instruct",
  ["HELM_Safety","HELM_XSTest_overrefusal","AIR_Bench","SALAD","TrustLLM","JailbreakBench","HarmBench","Arena_Hard","OLB_v2"],
  HELM_NO_NOTE + " Not in OLB v2 join.")

R(repo="HuggingFaceTB/SmolLM3-3B", family="smollm", n_params=3075098624, class_="instruct",
  benchmark="MMLU", number_exists="yes", value=53.5, metric_name="Global MMLU (No Extended Thinking mode)",
  setting="no_extended_thinking (matches panel thinking_flag=False)",
  source_url="https://huggingface.co/HuggingFaceTB/SmolLM3-3B", source_type="card", checkpoint_exact_match=True,
  notes="Own official card 'Instruction Model / No Extended Thinking' table. Global MMLU, not vanilla MMLU. Same row: IFEval=76.7, GPQA-Diamond=35.7, AIME2025=9.3, MixEval-Hard=26.9, BFCL=92.3. This same table also gives Qwen2.5-3B IFEval=65.6, Qwen3-1.7B IFEval=74.0, Qwen3-4B IFEval=68.9 (all No-Thinking mode, third-party cross-check of those panel checkpoints).")
collapsed_no("HuggingFaceTB/SmolLM3-3B", "smollm", 3075098624, "instruct",
  ["HELM_Safety","HELM_XSTest_overrefusal","AIR_Bench","SALAD","TrustLLM","JailbreakBench","HarmBench","GSM8K","Arena_Hard","OLB_v2"],
  HELM_NO_NOTE + " No GSM8K/Arena-Hard/safety number on the card (it uses GSM-Plus, not GSM8K, and has no safety section). Not in OLB v2 join.")

# ===========================================================================
# FALCON3
# ===========================================================================
R(repo="tiiuae/Falcon3-1B-Instruct", family="falcon3", n_params=1669408768, class_="instruct",
  benchmark="MMLU", number_exists="yes", value=46.1, metric_name="MMLU (5-shot)",
  setting="default", source_url="https://huggingface.co/tiiuae/Falcon3-1B-Instruct", source_type="card",
  checkpoint_exact_match=True, notes="Own official card table. Same row: MMLU-Pro=18.6, IFEval=54.4, GSM8K(5-shot)=43.9, GSM8K(8-shot,CoT)=45.8, MATH-Lvl5=1, ArcChallenge=47.7.")
R(repo="tiiuae/Falcon3-1B-Instruct", family="falcon3", n_params=1669408768, class_="instruct",
  benchmark="GSM8K", number_exists="yes", value=43.9, metric_name="GSM8K (5-shot)", setting="default",
  source_url="https://huggingface.co/tiiuae/Falcon3-1B-Instruct", source_type="card", checkpoint_exact_match=True, notes="")
collapsed_no("tiiuae/Falcon3-1B-Instruct", "falcon3", 1669408768, "instruct",
  ["HELM_Safety","HELM_XSTest_overrefusal","AIR_Bench","SALAD","TrustLLM","JailbreakBench","HarmBench","Arena_Hard","OLB_v2"],
  HELM_NO_NOTE + " TII's Falcon3 launch blog (huggingface.co/blog/falcon3) has no safety/RAI section for any size; no safety number found for this family. Not in OLB v2 join.")

# ===========================================================================
# H2O-DANUBE3
# ===========================================================================
R(repo="h2oai/h2o-danube3-500m-chat", family="danube3", n_params=513590784, class_="instruct",
  benchmark="MMLU", number_exists="yes", value=26.33, metric_name="MMLU (5-shot)",
  setting="default", source_url="https://arxiv.org/abs/2407.09276", source_type="paper", checkpoint_exact_match=True,
  notes="Own official H2O-Danube3 Technical Report Table (vs Qwen2-0.5B-Instruct baseline, not our panel's Qwen2.5-0.5B). Same table: ARC-c=39.25, HellaSwag=61.02, GSM8K(5-shot)=16.00, Winogrande=61.72.")
R(repo="h2oai/h2o-danube3-500m-chat", family="danube3", n_params=513590784, class_="instruct",
  benchmark="GSM8K", number_exists="yes", value=16.00, metric_name="GSM8K (5-shot)", setting="default",
  source_url="https://arxiv.org/abs/2407.09276", source_type="paper", checkpoint_exact_match=True, notes="")
collapsed_no("h2oai/h2o-danube3-500m-chat", "danube3", 513590784, "instruct",
  ["HELM_Safety","HELM_XSTest_overrefusal","AIR_Bench","SALAD","TrustLLM","JailbreakBench","HarmBench","Arena_Hard","OLB_v2"],
  HELM_NO_NOTE + " Own tech report has an MT-Bench/WildBench 'chat benchmark' table (Table 5) but no named safety benchmark. Not in OLB v2 join.")

# ===========================================================================
# EUROLLM
# ===========================================================================
R(repo="utter-project/EuroLLM-1.7B-Instruct", family="eurollm", n_params=1656850432, class_="instruct",
  benchmark="MMLU+GSM8K+Arena_Hard+HELM_Safety+HELM_XSTest_overrefusal+AIR_Bench+SALAD+TrustLLM+JailbreakBench+HarmBench+OLB_v2",
  number_exists="no", source_url="https://huggingface.co/utter-project/EuroLLM-1.7B-Instruct", source_type="card",
  checkpoint_exact_match=True,
  notes="Own card reports only ArcChallenge (avg=0.3496) and HellaSwag (avg=0.4744) multilingual accuracy vs TinyLlama-v1.1 and Gemma-2B -- none of MMLU/GSM8K/Arena-Hard/any safety benchmark from the task's list. The EuroLLM-9B technical report (arXiv:2506.04079) discusses EuroLLM-1.7B only in passing (as 'the earlier release'), with no benchmark table reproduced for it. Not in OLB v2/HELM/AIR-Bench/SALAD local tables. NOTE: EuroLLM-1.7B predates the 9B tech report; its own dedicated report/card (if any) was not separately located in this session's time budget.")

# ===========================================================================
# SEALED FAMILIES -- family-level only, no sealed repo ids anywhere below.
# ===========================================================================
R(repo="granite family (upstream IBM official)", family="granite", n_params=None, class_="sealed_family",
  benchmark="other_card_safety", number_exists="upstream_only",
  value="Qualitative only: 'Granite-3.0 models perform best in their parameter range' on the AttaQ safety benchmark among 2B-3B open models (radar-plot figure, no printable scalar; numeric AttaQ/SocialStigmaQA/SALAD-Bench-safety-rate table is only printed in the report for the 8B row, e.g. Granite-3.0-8B-Instruct=46.14/63.44/98.89/95.30 on 4 safety benchmarks)",
  metric_name="AttaQ (7-category harm refusal) + SocialStigmaQA + SALAD-Bench safety rate, family-level comparison vs Llama-3.1/Llama-3.2/Gemma-2 at 2B-3B scale",
  setting="n/a (family-level report claim, predecessor generation)",
  source_url="https://www.rivista.ai/wp-content/uploads/2024/10/paper-1.pdf (IBM Granite 3.0 technical report)",
  source_type="paper", checkpoint_exact_match=False,
  notes="SEALED FAMILY -- reported at family level only, no sealed repo id read or printed. This is the Granite 3.0 (predecessor of 3.3/4.0) technical report's Figure 7(b), which explicitly benchmarks IBM's 2B-3B-class Granite Instruct models against Llama-3.2 and Gemma-2 peers on AttaQ; it establishes that IBM runs a standing family-level safety-benchmark practice (AttaQ/SocialStigmaQA/SALAD) carried forward across Granite generations, but the 2B-3B panel numbers in that report are figure-only (not machine-extractable text) and a dedicated Granite-3.3/4.0-specific published safety table was not located within this session's time budget (IBM's public Granite docs/leaderboard page at ibm.com/granite/docs/models/granite is JS-rendered and returned no static text).")
collapsed_no("granite family (upstream IBM official)", "granite", None, "sealed_family",
  ["HELM_Safety","HELM_XSTest_overrefusal","AIR_Bench","SALAD(as a leaderboard)","TrustLLM","JailbreakBench","HarmBench","MMLU","GSM8K","Arena_Hard","OLB_v2"],
  HELM_NO_NOTE + " No granite-family repo appears in HELM/AIR-Bench's 22 resolved model names, nor in the OLB v2 join (family not in panel.json at all -- sealed rows are tracked separately in sealed/sealed_checkpoints.json, which this census does not read for individual repo ids per the sealing rule).")

R(repo="stablelm family (upstream Stability official)", family="stablelm", n_params=None, class_="sealed_family",
  benchmark="HELM_Safety+HELM_XSTest_overrefusal+AIR_Bench+SALAD+TrustLLM+JailbreakBench+HarmBench+other_card_safety+MMLU+GSM8K+Arena_Hard+OLB_v2",
  number_exists="no",
  source_url="https://arxiv.org/abs/2402.17834 (Stable LM 2 1.6B Technical Report)", source_type="paper",
  checkpoint_exact_match=False,
  notes="SEALED FAMILY -- reported at family level only. Directly grepped the Stable LM 2 1.6B Technical Report (2402.17834) full text for safety|toxicity|RealToxicity|refusal: a single incidental citation match only, no evaluation section, no safety/toxicity benchmark table anywhere in the report (it covers zero/few-shot academic benchmarks, multilingual evals and MT-Bench-style dialogue quality only). This is the official upstream architecture report for the whole StableLM-2 family; no separate Stability AI blog/report with a family-level safety table was found in this session's time budget. Stability's own model-card boilerplate for this family (seen only incidentally in a general web search snippet, not opened/read directly here to respect the sealing rule) states in prose that the family 'is not trained against adversarial inputs' and 'developers are strongly recommended to pair this model with an input/output classifier' -- a qualitative disclaimer, not a benchmark number.")

# ---------------------------------------------------------------------------
print(f"TOTAL rows built: {len(rows)}")
json.dump(rows, open(WS/"sa3/_rows_partial.json","w"), indent=1)
print("wrote _rows_partial.json")
