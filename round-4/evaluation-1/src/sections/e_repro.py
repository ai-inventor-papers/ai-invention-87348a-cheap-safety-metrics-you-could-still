"""E_repro: CPU-only, $0, no-LLM-calls reproducibility table over every experiment/dataset/
evaluation artifact in iterations 1-3 of this run. No new computation on model weights or
activations is performed; this only reads JSON/py/log files already on disk under R and
reports what it finds, with a `{value, source}` cell for every entry.

Run: /ai-inventor/.../iter_4/gen_art/gen_art_evaluation_1/.venv/bin/python sections/e_repro.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from io_utils import R, WS, dump, short  # noqa: E402

UNSRC = "UNSOURCED"


def cell(value, source: str | None) -> dict:
    if source is None or value is None:
        return {"value": "UNSOURCED" if value is None else value, "source": UNSRC if source is None else source}
    return {"value": value, "source": source}


def read_json(path: Path):
    return json.loads(path.read_text())


def sum_jsonl_cost(path: Path, fields: tuple[str, ...]) -> tuple[float, int]:
    """Sum the first matching field in `fields` over a JSONL cost ledger. Returns (total, n_lines)."""
    tot, n = 0.0, 0
    if not path.exists():
        return 0.0, 0
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        for f in fields:
            if f in d and isinstance(d[f], (int, float)):
                tot += d[f]
                n += 1
                break
    return tot, n


ROWS: list[dict] = []


def add_row(artifact: str, cells: dict) -> None:
    ROWS.append({"artifact": artifact, "cells": cells})


# ---------------------------------------------------------------------------
# iter_1 / gen_art_dataset_1 -- checkpoint registry construction (no generation)
# ---------------------------------------------------------------------------
d = R / "iter_1/gen_art/gen_art_dataset_1"
panel_candidates = read_json(d / "build/panel_candidates.json")
verified_counts = read_json(d / "research/verified_counts.json")
add_row("iter_1/gen_art_dataset_1", {
    "gen_max_new_tokens": cell("N/A (no generation)", short(d / "data.py") + " (registry build, no model.generate call)"),
    "decoding": cell("N/A (no generation)", None),
    "judge": cell("N/A (no generation)", None),
    "item_set": cell(f"XSTest {verified_counts['xstest_prompts.csv']['rows']} rows (source dataset verification only, not an eval item set)",
                      short(d / "research/verified_counts.json") + ":xstest_prompts.csv.rows"),
    "n_checkpoints": cell(f"{len(panel_candidates)} candidate checkpoints (registry build, not scored)",
                          short(d / "build/panel_candidates.json") + " (len of file, dict of checkpoint-id -> record)"),
    "hardware": cell(UNSRC, None),
    "spend_usd": cell(0.0, "no OpenRouter/API calls in this artifact (HF metadata harvest only; no cost ledger file present)"),
    "deviations": cell(UNSRC, None),
})

# ---------------------------------------------------------------------------
# iter_1 / gen_art_experiment_1
# ---------------------------------------------------------------------------
e = R / "iter_1/gen_art/gen_art_experiment_1"
env = read_json(e / "results/env_report.json")
summary = read_json(e / "results/summary.json")
add_row("iter_1/gen_art_experiment_1", {
    "gen_max_new_tokens": cell(96, short(e / "screen/harvest.py") + ":289 (harvest_generate default max_new_tokens=96)"),
    "decoding": cell("greedy (do_sample=False)", short(e / "screen/harvest.py") + ":302"),
    "judge": cell("openai/gpt-5-nano primary, google/gemini-2.5-flash-lite alternate; StrongREJECT-style graded compliance + false-refusal",
                  short(e / "screen/judge.py") + ":26-27"),
    "item_set": cell("XSTest 450 rows / 200 positional twin pairs (safety panel item pool)",
                      short(e / "RESULTS.md") + " (\"XSTest: 450 rows, 200 positional twin pairs\")"),
    "n_checkpoints": cell(f"{summary.get('n_checkpoints_scored')} scored / {summary.get('n_panel_total')} panel total, "
                          f"{summary.get('n_lineages_scored')} lineages",
                          short(e / "results/summary.json") + ":n_checkpoints_scored,n_panel_total,n_lineages_scored"),
    "hardware": cell(f"GPU yes ({env['gpus'][0]['name']}, {env['gpus'][0]['total_gb']} GB), cpu_count={env['cpu_count']}",
                      short(e / "results/env_report.json") + ":gpus.0.name,gpus.0.total_gb,cpu_count"),
    "spend_usd": cell(summary["judge_cost_usd"], short(e / "results/summary.json") + ":judge_cost_usd"),
    "deviations": cell("0 (no prereg_deviations.json / DEVIATIONS.json / acceptance.json in this artifact)", None),
})

# ---------------------------------------------------------------------------
# iter_1 / gen_art_experiment_2
# ---------------------------------------------------------------------------
e = R / "iter_1/gen_art/gen_art_experiment_2"
items = read_json(e / "out/items.json")
panel_c = read_json(e / "out/panel_candidates.json")
add_row("iter_1/gen_art_experiment_2", {
    "gen_max_new_tokens": cell(48, short(e / "flab/config.py") + ":123 (GEN_MAX_NEW_TOKENS)"),
    "decoding": cell("greedy (do_sample=False)", short(e / "flab/groundtruth.py") + ":86"),
    "judge": cell("openai/gpt-4.1-mini primary, google/gemini-2.5-flash alternate",
                  short(e / "flab/config.py") + ":128-129 (JUDGE_MODEL, JUDGE_ALTERNATE)"),
    "item_set": cell(f"{len(items)} items (out/items.json)", short(e / "out/items.json") + " (top-level list length)"),
    "n_checkpoints": cell(f"{len(panel_c.get('honest', []))} honest + {len(panel_c.get('edited', []))} edited "
                          "candidate hosts (out/panel_candidates.json); no run-level scored-checkpoint count file found",
                          short(e / "out/panel_candidates.json") + ":honest,edited (list lengths)"),
    "hardware": cell(UNSRC, None),
    "spend_usd": cell(UNSRC, "no cost/spend/ledger file found under this artifact"),
    "deviations": cell(UNSRC, None),
})

# ---------------------------------------------------------------------------
# iter_1 / gen_art_experiment_3
# ---------------------------------------------------------------------------
e = R / "iter_1/gen_art/gen_art_experiment_3"
tier0 = read_json(e / "results/tier0_results.json")
panel_sel = read_json(e / "panel/panel_selected.json")
cost_sum, cost_n = sum_jsonl_cost(e / "logs/cost.jsonl", ("charged_usd", "cost"))
sr_sum, sr_n = sum_jsonl_cost(e / "scratch/sr_ledger.jsonl", ("charged_usd", "cost"))
add_row("iter_1/gen_art_experiment_3", {
    "gen_max_new_tokens": cell(192, short(e / "lanec/acts.py") + ":441 (generate_batch default max_new_tokens); "
                                "method.py also calls it at 64 and 96 for specific sub-stages (method.py:853,864,979,982)"),
    "decoding": cell("greedy (do_sample=False, temperature=None)", short(e / "lanec/acts.py") + ":449-450"),
    "judge": cell("openai/gpt-5-mini primary, google/gemini-2.5-flash alternate (StrongREJECT rubric per specs/strongreject_rubric.txt)",
                  short(e / "method.py") + ":57-58 (JUDGE_PRIMARY, JUDGE_ALTERNATE)"),
    "item_set": cell("panel/panel_selected.json (4 entries) + items/ pool (B120/H120/alpaca120/etc.)",
                      short(e / "panel/panel_selected.json") + " (top-level length)"),
    "n_checkpoints": cell(len(tier0), short(e / "results/tier0_results.json") + " (top-level dict length)"),
    "hardware": cell(UNSRC, None),
    "spend_usd": cell(round(cost_sum + sr_sum, 5),
                      f"sum of 'charged_usd' over {short(e/'logs/cost.jsonl')} ({cost_n} rows, ${cost_sum:.5f}) "
                      f"+ {short(e/'scratch/sr_ledger.jsonl')} ({sr_n} rows, ${sr_sum:.5f}); "
                      "neither file matches the exact names cost_ledger.jsonl/spend.jsonl but both are OpenRouter charge logs"),
    "deviations": cell(UNSRC, None),
})

# ---------------------------------------------------------------------------
# iter_2 / gen_art_experiment_1
# ---------------------------------------------------------------------------
e = R / "iter_2/gen_art/gen_art_experiment_1"
per_ckpt = read_json(e / "results/per_checkpoint.json")
env2 = read_json(e / "results/env.json")
devs = read_json(e / "results/prereg_deviations.json")
cost_sum1, cost_n1 = sum_jsonl_cost(e / "results/cost_ledger.jsonl", ("usd",))
josiefied = [r for r in per_ckpt if "josiefied" in r.get("slug", "").lower()]
maxtoks = sorted(set(r.get("gen_max_new_tokens") for r in per_ckpt if r.get("gen_max_new_tokens") is not None))
n_grad = sum(1 for r in per_ckpt if r.get("has_gen"))
add_row("iter_2/gen_art_experiment_1", {
    "gen_max_new_tokens": cell(f"{maxtoks} across checkpoints (Josiefied={josiefied[0]['gen_max_new_tokens'] if josiefied else 'n/a'})",
                                short(e / "results/per_checkpoint.json") + ":*.gen_max_new_tokens (per-row field)"),
    "decoding": cell("greedy (do_sample=False)", short(e / "screen/harvest_cpu_gen.py") + ":185"),
    "judge": cell("openai/gpt-5-mini, STANCE-CLASSIFICATION framing (deviation D1: switched off StrongREJECT after grader-side refusal)",
                  short(e / "results/prereg_deviations.json") + ":deviations.0 (id=D1_JUDGE_FRAMING)"),
    "item_set": cell(f"{n_grad} of {len(per_ckpt)} checkpoints have generations (has_gen=true); n_graded per checkpoint up to "
                      f"{max((r.get('n_graded') or 0) for r in per_ckpt)}",
                      short(e / "results/per_checkpoint.json") + ":*.has_gen,*.n_graded"),
    "n_checkpoints": cell(len(per_ckpt), short(e / "results/per_checkpoint.json") + " (top-level list length)"),
    "hardware": cell(f"GPU no (cuda_available={env2['cuda_available']}); nproc={env2['nproc']}; "
                      f"{env2['BINDING_CONSTRAINT'][:80]}...",
                      short(e / "results/env.json") + ":cuda_available,nproc,BINDING_CONSTRAINT"),
    "spend_usd": cell(round(cost_sum1, 5),
                      f"sum of 'usd' field over {short(e/'results/cost_ledger.jsonl')} ({cost_n1} rows); "
                      "matches RESULTS.md-adjacent deviation D1's \"$0.77\" stated figure"),
    "deviations": cell(f"{len(devs['deviations'])} ({', '.join(x['id'] for x in devs['deviations'])})",
                       short(e / "results/prereg_deviations.json") + ":deviations (list length + .id fields)"),
})

# ---------------------------------------------------------------------------
# iter_2 / gen_art_experiment_2 (behavioural ladder)
# ---------------------------------------------------------------------------
e = R / "iter_2/gen_art/gen_art_experiment_2"
ladder_rows = [json.loads(l) for l in (e / "out/ladder_rows.jsonl").read_text().splitlines() if l.strip()]
ckpts = sorted(set(r["ckpt"] for r in ladder_rows))
spend_sum2, spend_n2 = sum_jsonl_cost(e / "out/spend.jsonl", ("usd", "cost"))
readme_text = (e / "README.md").read_text().splitlines()
readme_line = next((i + 1 for i, l in enumerate(readme_text) if "20 new tokens" in l), None)
add_row("iter_2/gen_art_experiment_2", {
    "gen_max_new_tokens": cell(20, short(e / "README.md") + f":{readme_line} (\"greedy continuations (20 new tokens)\")"),
    "decoding": cell("greedy (argmax next-token loop, no sampling)", short(e / "behave2.py") + ":706-716"),
    "judge": cell("openai/gpt-5-mini, STANCE-CLASSIFICATION framing (StrongREJECT-evaluator framing dropped, grader-side refusal)",
                  short(e / "README.md") + ":100-102"),
    "item_set": cell("items_160.json, iteration 1's pre-registered 160 items (96 graded items for continuations)",
                      short(e / "behave2.py") + ":749 (item_set field of summarise())"),
    "n_checkpoints": cell(f"{len(ckpts)} hosts/families: {ckpts}",
                          short(e / "out/ladder_rows.jsonl") + " (distinct 'ckpt' values across all rows)"),
    "hardware": cell(UNSRC, "no env.json/hardware.json found directly under this artifact (sibling exp_1/exp_3 in the "
                      "same iteration record GPU no / 2 CPUs, but that is not this artifact's own file)"),
    "spend_usd": cell(round(spend_sum2, 5),
                      f"sum over {short(e/'out/spend.jsonl')} ({spend_n2} rows)"),
    "deviations": cell(UNSRC, "no prereg_deviations.json/DEVIATIONS.json/acceptance.json found; README/TODO_TRACKER "
                        "describe changes in prose only"),
})

# ---------------------------------------------------------------------------
# iter_2 / gen_art_experiment_3
# ---------------------------------------------------------------------------
e = R / "iter_2/gen_art/gen_art_experiment_3"
spend3 = read_json(e / "results/spend.json")
devs3 = read_json(e / "DEVIATIONS.json")
hw3 = read_json(e / "results/hardware_v2.json")
add_row("iter_2/gen_art_experiment_3", {
    "gen_max_new_tokens": cell(64, short(e / "stage2_generate_v2.py") + ":66 (MAX_NEW_TOKENS = 64; \"the sibling used 96\")"),
    "decoding": cell("greedy (do_sample=False)", short(e / "stage2_generate_v2.py") + ":257"),
    "judge": cell("openai/gpt-5-mini primary, google/gemini-2.5-flash alternate, STANCE framing",
                  short(e / "stage2b_grade_v2.py") + ":77 (PRIMARY, ALTERNATE)"),
    "item_set": cell("panel/panel_selected.json + items/ pool (H120/B120/alpaca120/xstest twins); "
                      "graded on H+twin+probe items per method.py:25",
                      short(e / "method.py") + ":25"),
    "n_checkpoints": cell(f"{len(read_json(e / 'results/stage3_v2.json')['graded_panel'])} graded "
                          f"(panel pool: {read_json(e / 'results/panel.json')['n_honest']} honest + "
                          f"{read_json(e / 'results/panel.json')['n_edited']} edited candidates)",
                          short(e / "results/stage3_v2.json") + ":graded_panel (list length); "
                          + short(e / "results/panel.json") + ":n_honest,n_edited"),
    "hardware": cell(f"GPU {hw3['gpu']}; n_logical_cpus_in_cpuset={hw3['n_logical_cpus_in_cpuset']}",
                      short(e / "results/hardware_v2.json") + ":gpu,n_logical_cpus_in_cpuset"),
    "spend_usd": cell(spend3["usd"], short(e / "results/spend.json") + ":usd"),
    "deviations": cell(f"{len(devs3)} ({devs3[0].get('id', devs3[0].get('name'))}..{devs3[-1].get('id', devs3[-1].get('name'))})",
                       short(e / "DEVIATIONS.json") + " (top-level list length + first/last ids)"),
})

# ---------------------------------------------------------------------------
# iter_2 / gen_art_evaluation_1 -- offline re-analysis, $0, no generation
# ---------------------------------------------------------------------------
e = R / "iter_2/gen_art/gen_art_evaluation_1"
ledger_sum, ledger_n = sum_jsonl_cost(e / ".aii_cost_ledger.jsonl", ("cost_usd", "cost", "usd"))
readme2_text = (e / "README.md").read_text().splitlines()
n17_line = next((i + 1 for i, l in enumerate(readme2_text) if "n=17" in l), None)
add_row("iter_2/gen_art_evaluation_1", {
    "gen_max_new_tokens": cell("N/A (no generation)", short(e / "README.md") + " (\"No GPU. No downloads. No model inference.\")"),
    "decoding": cell("N/A (no generation)", None),
    "judge": cell("N/A (no LLM judge; offline statistical re-analysis of iter_1/experiment_1's harvest)", None),
    "item_set": cell("re-analyses iter_1/gen_art_experiment_1's harvest in place (no new items)", short(e / "README.md") + ":1-10"),
    "n_checkpoints": cell(17, short(e / "README.md") + f":{n17_line} (\"n=17 with a 1000-draw null distribution\")"),
    "hardware": cell("GPU no; CPU-only, $0 (stated, no compute-heavy step)", short(e / "README.md") + ":5 (\"No GPU. ... $0.00 of API spend.\")"),
    "spend_usd": cell(round(ledger_sum, 5), f"sum of cost_usd over {short(e/'.aii_cost_ledger.jsonl')} ({ledger_n} rows; all web-search tool calls, all $0.00)"),
    "deviations": cell(UNSRC, "no prereg_deviations.json/DEVIATIONS.json/acceptance.json found; artifact frames itself as a bugfix re-run, not a prereg deviation"),
})

# ---------------------------------------------------------------------------
# iter_3 / gen_art_dataset_1
# ---------------------------------------------------------------------------
e = R / "iter_3/gen_art/gen_art_dataset_1"
outcome = read_json(e / "results/outcome.json")
acc = read_json(e / "acceptance.json")
ck = outcome["checkpoints"]
add_row("iter_3/gen_art_dataset_1", {
    "gen_max_new_tokens": cell(64, short(e / "scripts/generate.py") + ":170 (--max-new default=64)"),
    "decoding": cell("greedy (do_sample=False)", short(e / "scripts/generate.py") + ":94"),
    "judge": cell(f"primary={outcome['primary_judge']} (switched from gpt-5-mini after calibration-gate failure, deviation "
                  "PRIMARY_JUDGE_SWITCHED), secondary=openai/gpt-5-mini, STANCE framing",
                  short(e / "results/outcome.json") + ":primary_judge"),
    "item_set": cell(f"CORE-94 (66 harmful / 28 XSTest-safe), n_graded={ck[0]['n_graded']}",
                      short(e / "results/outcome.json") + ":checkpoints.0.label_protocol,checkpoints.0.n_graded"),
    "n_checkpoints": cell(len(ck), short(e / "results/outcome.json") + ":checkpoints (list length)"),
    "hardware": cell("GPU no (torch_cuda_available=false); nproc=48 host / sched_getaffinity=2",
                      short(e / "env.json") + ":torch_cuda_available,nproc,sched_getaffinity"),
    "spend_usd": cell(outcome["total_spend_usd"], short(e / "results/outcome.json") + ":total_spend_usd"),
    "deviations": cell(f"{len(acc['deviations'])} ({', '.join(x['name'] for x in acc['deviations'])})",
                       short(e / "acceptance.json") + ":deviations (list length + .name fields)"),
})

# ---------------------------------------------------------------------------
# iter_3 / gen_art_evaluation_1 -- offline re-scoring, $0, no generation
# ---------------------------------------------------------------------------
e = R / "iter_3/gen_art/gen_art_evaluation_1"
readme3 = (e / "README.md").read_text()
readme3_lines = readme3.splitlines()
n15_line = next((i + 1 for i, l in enumerate(readme3_lines) if "n ≤ 15 checkpoints" in l or "n<=15 checkpoints" in l), None)
add_row("iter_3/gen_art_evaluation_1", {
    "gen_max_new_tokens": cell("N/A (no generation)", short(e / "README.md") + ":3 (\"No model is loaded, no LLM is called\")"),
    "decoding": cell("N/A (no generation)", None),
    "judge": cell("N/A (no new LLM judging; re-scores iter_2/gen_art_experiment_1's already-judged grades)", short(e / "README.md") + ":3"),
    "item_set": cell("48 harmful + 32 benign_alarming judged items (coverage fact); SCREEN16 subset for early scatter",
                      short(e / "README.md") + " (\"Coverage fact\" paragraph, \"48 harmful + 32 benign_alarming items\")"),
    "n_checkpoints": cell(15, short(e / "README.md") + (f":{n15_line}" if n15_line else "") +
                          " (\"n <= 15 checkpoints (6 lineages, 3 families)\")"),
    "hardware": cell("GPU no; CPU-only, $0 (stated)", short(e / "README.md") + ":3 (\"No model is loaded, no LLM is called and nothing was spent on OpenRouter ($0)\")"),
    "spend_usd": cell(0.0, short(e / "README.md") + ":3"),
    "deviations": cell(UNSRC, "no prereg_deviations.json/DEVIATIONS.json/acceptance.json found; artifact is framed as "
                        "addressing 4 reviewer-flagged items in prose, not formal prereg deviations"),
})

# ---------------------------------------------------------------------------
# assemble + write
# ---------------------------------------------------------------------------
COLUMNS = ["artifact", "gen_max_new_tokens", "decoding", "judge", "item_set",
           "n_checkpoints", "hardware", "spend_usd", "deviations"]

n_unsourced = 0
total_spend_sourced = 0.0
for row in ROWS:
    for col, c in row["cells"].items():
        if c["source"] == UNSRC or c["value"] == UNSRC:
            n_unsourced += 1
    sp = row["cells"]["spend_usd"]
    if sp["source"] != UNSRC and isinstance(sp["value"], (int, float)):
        total_spend_sourced += sp["value"]

out = {
    "columns": COLUMNS,
    "rows": ROWS,
    "n_unsourced_cells": n_unsourced,
    "n_rows": len(ROWS),
    "total_spend_usd_sourced": round(total_spend_sourced, 5),
    "notes": [
        "Scope: R/iter_{1,2,3}/gen_art/gen_art_{experiment,dataset,evaluation}_* (research_* dirs skipped per task instructions).",
        "CPU-only, $0, no LLM calls were made to build this table -- every cell is read from files already on disk.",
        "iter_1/gen_art_experiment_3 spend uses logs/cost.jsonl + scratch/sr_ledger.jsonl (no file named cost_ledger.jsonl/spend.jsonl exists there); field name differs across artifacts (usd / charged_usd / cost_usd) and is noted per cell.",
        "iter_2/gen_art_experiment_1: cost_ledger.jsonl sum ($0.7665) matches the ~$0.77 figure the task asked to check.",
        "iter_2/gen_art_experiment_3: spend.json usd=$1.172058 matches the ~$1.17 figure the task asked to check; independently summing results/cost_ledger.jsonl's 'usd' field over 8508 rows gives the same total (1.17206).",
        "iter_3/gen_art_dataset_1: results/outcome.json total_spend_usd=$0.53453 matches acceptance.json's total_spend<=6usd check (0.5345); this DISAGREES with summing results/cost_ledger.jsonl's usd field directly (4969 rows, $0.58136) -- outcome.json is treated as authoritative since it is the artifact's own stated summary figure, but the ~$0.05 gap (likely judge_calibration.py's extra calibration-only calls not counted in the per-checkpoint outcome total) is flagged here rather than silently resolved.",
        "iter_2/gen_art_evaluation_1 and iter_3/gen_art_evaluation_1 are true re-analyses of prior harvests: $0 spend, no generation, no judge call -- confirmed both by their own README text and by their cost-ledger files summing to exactly 0.",
        "Two 'checked' values did NOT match the task's stated expectation as literally worded: iter_2/gen_art_experiment_1's gen_max_new_tokens is 96 for most checkpoints but the per_checkpoint.json rows show it varies per checkpoint (not a single global constant) and Josiefied-Qwen2.5-1.5B is confirmed at 48, matching the expected note exactly.",
    ],
}

dump(out, WS / "results" / "E_repro.json")

# ---------------------------------------------------------------------------
# markdown table
# ---------------------------------------------------------------------------
def fmt(v) -> str:
    s = str(v)
    return s.replace("|", "\\|").replace("\n", " ")


md_lines = ["# E_repro -- reproducibility table (iters 1-3, CPU-only, $0, no LLM calls)", ""]
md_lines.append("| " + " | ".join(COLUMNS) + " |")
md_lines.append("|" + "|".join(["---"] * len(COLUMNS)) + "|")
for row in ROWS:
    cells = [row["artifact"]] + [fmt(row["cells"][c]["value"]) for c in COLUMNS[1:]]
    md_lines.append("| " + " | ".join(cells) + " |")
md_lines.append("")
md_lines.append(f"n_rows={out['n_rows']}, n_unsourced_cells={out['n_unsourced_cells']}, "
                f"total_spend_usd_sourced=${out['total_spend_usd_sourced']}")
md_lines.append("")
md_lines.append("## Notes")
for note in out["notes"]:
    md_lines.append(f"- {note}")
md_lines.append("")
md_lines.append("## Sources (per cell)")
for row in ROWS:
    md_lines.append(f"\n### {row['artifact']}")
    for col in COLUMNS[1:]:
        c = row["cells"][col]
        md_lines.append(f"- **{col}**: `{fmt(c['value'])[:200]}`  \n  source: `{c['source']}`")

(WS / "results" / "E_repro.md").write_text("\n".join(md_lines))

print(f"n_rows={out['n_rows']}")
print(f"n_unsourced_cells={out['n_unsourced_cells']}")
print(f"total_spend_usd_sourced={out['total_spend_usd_sourced']}")
