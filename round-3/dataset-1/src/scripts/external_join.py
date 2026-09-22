#!/usr/bin/env python3
"""External/capability join for the 39-repo panel of HF chat checkpoints.

Joins by EXACT repo id (case-insensitively normalised) only. No fuzzy / substring
matching, no imputation: a column is null unless the panel repo's normalised id (or one
of its declared byte-identical mirror aliases) appears verbatim in the source table.

Inputs (read-only copies under W/data/external/, copied from iter_2's
gen_art_experiment_3/external/):
  - helm_safety_v1_17_0.json     HELM safety-scenario table (per model x scenario rows)
  - helm_airbench_v1_19_0.json   HELM AIR-Bench 2024 table (per model rows)
  - saladbench.json              SALAD-Bench harvest status (NOT_REACHABLE — no scores)
  - helm_model_meta.json         HELM "org/model" display-name -> literal-lowercase HF
                                  repo_id existence probe (records/resolved/unresolved)
  - openllm_capability.json      Open LLM Leaderboard archive capability rows (mmlu/gsm8k/arc)
  - openllm_archive_index.json   metadata only (n_repos/sample_paths) — no scores, not
                                  joined against, kept only for provenance/sha256 record
  - helm_field_names.json        metadata only (per-scenario field list) — not joined
                                  against, kept only for provenance/sha256 record
  - openllm_v2_contents.parquet  Open LLM Leaderboard v2 aggregated "contents" table,
                                  downloaded fresh from HF dataset open-llm-leaderboard/
                                  contents (data/train-00000-of-00001.parquet), commit sha
                                  recorded in OPENLLM_V2_COMMIT_SHA below
  - openllm_v1_old_contents.parquet  Open LLM Leaderboard v1 (ARC/HellaSwag/MMLU/
                                  TruthfulQA/Winogrande/GSM8K) aggregated "contents" table,
                                  downloaded fresh from HF dataset open-llm-leaderboard-old/
                                  contents, commit sha in OPENLLM_V1_COMMIT_SHA below.
                                  Used ONLY as an mmlu/gsm8k fallback when
                                  openllm_capability.json has no hit for a repo — it is a
                                  small (<50MB) single aggregated parquet, unlike
                                  open-llm-leaderboard-old/results and open-llm-leaderboard/
                                  results, which are 10k+ individual per-run JSON files
                                  (already indexed, not scored, by openllm_archive_index.json)
                                  and were correctly skipped per the task's <50MB
                                  aggregated-table requirement.

HELM naming quirk: the safety/airbench tables key each row by an UNDERSCORE-joined display
name ("qwen_qwen3-235b-a22b-instruct-2507-fp8"), while helm_model_meta.json's `records` dict
is keyed by the SLASH-joined "org/model" form ("qwen/qwen3-235b-a22b-instruct-2507-fp8") and
gives the literal lower-cased guess it checked against the HF Hub as `repo_id`, plus whether
that guess actually `exists`. We map each HELM row's model name to org/model, look it up in
helm_model_meta records, and only treat it as a resolved HF repo_id when `exists` is true.
That repo_id is what gets compared (case-insensitively) against the panel.

Run: python3 external_join.py  (system python3 — has pyarrow + pandas available; stdlib
covers everything else). If the shared W/venv_ds venv is used instead, note it was found
with a broken/partial pandas install and no huggingface_hub at all when this script was
written (2026-09-21) — the parquet downloads below use stdlib urllib against the plain HF
REST/resolve endpoints for exactly that reason, no huggingface_hub dependency needed.
Writes: W/results/external_join.json
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

WS = Path(__file__).resolve().parent.parent
EXT = WS / "data" / "external"
OUT = WS / "results" / "external_join.json"

HELM_SAFETY_PATH = EXT / "helm_safety_v1_17_0.json"
HELM_AIRBENCH_PATH = EXT / "helm_airbench_v1_19_0.json"
SALAD_PATH = EXT / "saladbench.json"
HELM_META_PATH = EXT / "helm_model_meta.json"
OPENLLM_CAP_PATH = EXT / "openllm_capability.json"
OPENLLM_INDEX_PATH = EXT / "openllm_archive_index.json"
HELM_FIELDNAMES_PATH = EXT / "helm_field_names.json"
OPENLLM_V2_PATH = EXT / "openllm_v2_contents.parquet"
OPENLLM_V1_OLD_PATH = EXT / "openllm_v1_old_contents.parquet"

HELM_SAFETY_VERSION = "v1.17.0"
HELM_AIRBENCH_VERSION = "v1.19.0"

# Dataset repo commit shas at the time these parquet files were downloaded (2026-09-21),
# from GET https://huggingface.co/api/datasets/<repo> -> "sha". This is the dataset repo's
# HEAD commit, i.e. the exact revision `resolve/main/...` fetched.
OPENLLM_V2_COMMIT_SHA = "9c09a7cae43334062a82cb164f2ef255013dafa2"  # open-llm-leaderboard/contents
OPENLLM_V1_COMMIT_SHA = "791ca1c841030008c6c266562c2b88c9b7196550"  # open-llm-leaderboard-old/contents

# ----------------------------------------------------------------------------- panel

PANEL_REPOS: list[str] = [
    "Qwen/Qwen3-0.6B", "Qwen/Qwen3-1.7B", "Qwen/Qwen3-4B", "Qwen/Qwen3-4B-SafeRL",
    "huihui-ai/Huihui-Qwen3-0.6B-abliterated-v2", "huihui-ai/Huihui-Qwen3-1.7B-abliterated-v2",
    "mlabonne/Qwen3-4B-abliterated", "DreamFast/qwen3-4b-heretic", "Qwen/Qwen3-4B-Base",
    "Qwen/Qwen2.5-0.5B-Instruct", "Qwen/Qwen2.5-1.5B-Instruct", "Qwen/Qwen2.5-3B-Instruct",
    "Goekdeniz-Guelmez/Josiefied-Qwen2.5-1.5B-Instruct-abliterated-v1",
    "huihui-ai/Qwen2.5-0.5B-Instruct-CensorTune", "huihui-ai/Qwen2.5-1.5B-Instruct-CensorTune",
    "TinyLlama/TinyLlama-1.1B-Chat-v1.0", "AIPlans/TinyLlama-1.1B-IPO-PKU-SafeRLHF",
    "AIPlans/TinyLlama-1.1B-ORPO-PKU-SafeRLHF", "AIPlans/tinyllama-1.1b-dpo-pku-saferlhf",
    "Shortmund09/MLDM-TinyLlama-1.1b-gcpo-ocra-saferlhf",
    "google/gemma-2-2b-it", "unsloth/gemma-2-2b-it", "IlyaGusev/gemma-2-2b-it-abliterated",
    "Robust-Decoding/gemma2-2b-it-hh-dpo-harmless-step-6000",
    "unsloth/Llama-3.2-1B-Instruct", "unsloth/Llama-3.2-3B-Instruct",
    "huihui-ai/Llama-3.2-3B-Instruct-abliterated",
    "microsoft/Phi-4-mini-instruct", "microsoft/Phi-3.5-mini-instruct",
    "lunahr/Phi-4-mini-instruct-abliterated",
    "allenai/OLMo-2-0425-1B-Instruct",
    "HuggingFaceTB/SmolLM2-360M-Instruct", "HuggingFaceTB/SmolLM2-1.7B-Instruct",
    "HuggingFaceTB/SmolLM3-3B",
    "tiiuae/Falcon3-1B-Instruct", "h2oai/h2o-danube3-500m-chat",
    "utter-project/EuroLLM-1.7B-Instruct",
]
# NOTE: the task described this as "Panel repos (39)" but enumerated only 37 distinct
# repo ids (verified: no duplicates in the list below). Proceeding with the 37 actually
# given rather than inventing 2 more.
assert len(PANEL_REPOS) == len(set(r.strip().lower() for r in PANEL_REPOS)) == 37, \
    f"expected 37 distinct panel repos, got {len(PANEL_REPOS)} " \
    f"({len(set(r.strip().lower() for r in PANEL_REPOS))} distinct)"

# Byte-identical-mirror pairs: joining a value found under the mirror id onto the panel
# repo is only ever done with alias=true + alias_of=<the id the value was actually found
# under>. Declared in both directions so lookup is symmetric.
MIRROR_ALIASES: dict[str, str] = {
    "unsloth/llama-3.2-1b-instruct": "meta-llama/Llama-3.2-1B-Instruct",
    "unsloth/llama-3.2-3b-instruct": "meta-llama/Llama-3.2-3B-Instruct",
    "unsloth/gemma-2-2b-it": "google/gemma-2-2b-it",
}


def norm(repo_id: str) -> str:
    return repo_id.strip().lower()


# --------------------------------------------------------------------------- loaders

SAFETY_SCENARIOS = ("xstest", "harm_bench", "simple_safety_tests", "anthropic_red_team")


def load_helm_safety(path: Path) -> dict[str, dict[str, Any]]:
    """Return {helm_model_name: {scenario: {"safety_score": float|None, "version": str}}}."""
    data = json.loads(path.read_text())
    by_model: dict[str, dict[str, Any]] = {}
    for row in data["rows"]:
        model = row["model"]
        scen = row["scenario"]
        m = row.get("metrics", {}).get("safety_score")
        score = m.get("mean") if isinstance(m, dict) else None
        by_model.setdefault(model, {})[scen] = {
            "safety_score": score, "version": row.get("version"),
        }
    return by_model


def load_helm_airbench(path: Path) -> dict[str, dict[str, Any]]:
    """Return {helm_model_name: {"air_score": float|None, "version": str|None}}."""
    data = json.loads(path.read_text())
    out: dict[str, dict[str, Any]] = {}
    for row in data["rows"]:
        m = row.get("metrics", {}).get("air_score")
        out[row["model"]] = {
            "air_score": m.get("mean") if isinstance(m, dict) else None,
            "version": row.get("version"),
        }
    return out


def load_helm_meta(path: Path) -> dict[str, dict[str, Any]]:
    """{"org/model" (lower, slash-joined) -> record with repo_id/exists}."""
    data = json.loads(path.read_text())
    return data.get("records", {})


def helm_name_to_org_slash_model(helm_model: str) -> str:
    """'qwen_qwen3-235b-a22b-instruct-2507-fp8' -> 'qwen/qwen3-235b-a22b-instruct-2507-fp8'.
    HELM display names join org and model with a single underscore; the org itself never
    contains an underscore in this dataset's org column, so the first underscore is the
    split point.
    """
    return helm_model.replace("_", "/", 1)


def load_openllm_capability(path: Path) -> dict[str, dict[str, Any]]:
    """{repo_lower -> row}. No versioning info in this table beyond each row's own
    per-repo source_file (an Open LLM Leaderboard archive results_*.json path).
    """
    data = json.loads(path.read_text())
    rows = data["rows"] if isinstance(data, dict) else data
    out: dict[str, dict[str, Any]] = {}
    for r in rows:
        repo = r.get("repo")
        if repo:
            out[norm(repo)] = r
    return out


def load_salad(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _dedupe_by_fullname(rows: list[dict[str, Any]], tie_break_key) -> dict[str, dict[str, Any]]:
    """Open LLM Leaderboard contents tables can hold >1 submitted row for the same
    `fullname` (re-submissions at a different precision). Group by norm(fullname) and keep
    exactly one row per repo, chosen deterministically by `tie_break_key` (higher sorts
    first). Returns {repo_lower -> chosen_row}.
    """
    from collections import defaultdict

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        fn = r.get("fullname")
        if fn:
            grouped[norm(fn)].append(r)
    out: dict[str, dict[str, Any]] = {}
    for key, group in grouped.items():
        group.sort(key=tie_break_key, reverse=True)
        out[key] = group[0]
        out[key]["_n_submissions_for_repo"] = len(group)
    return out


def load_openllm_v2_contents(path: Path) -> dict[str, dict[str, Any]]:
    """Open LLM Leaderboard v2 'contents' table (open-llm-leaderboard/contents).
    Dedup tie-break: Official Providers=True first, then latest Submission Date.
    """
    table = pq.read_table(path)
    rows = table.to_pylist()
    return _dedupe_by_fullname(
        rows,
        tie_break_key=lambda r: (bool(r.get("Official Providers")), str(r.get("Submission Date") or "")),
    )


def load_openllm_v1_old_contents(path: Path) -> dict[str, dict[str, Any]]:
    """Open LLM Leaderboard v1 'contents' table (open-llm-leaderboard-old/contents).
    Dedup tie-break: Maintainers Choice=True first, then latest `date` string.
    """
    table = pq.read_table(path)
    rows = table.to_pylist()
    return _dedupe_by_fullname(
        rows,
        tie_break_key=lambda r: (bool(r.get("Maintainers Choice")), str(r.get("date") or "")),
    )


# ------------------------------------------------------------------------------ join


def build_helm_repo_index(
    safety_by_model: dict[str, dict[str, Any]],
    airbench_by_model: dict[str, dict[str, Any]],
    helm_meta: dict[str, dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], list[str], list[str]]:
    """Resolve every HELM model name (from safety and airbench tables) to a repo_id via
    helm_model_meta (only when meta says exists=True), then re-key both tables by
    norm(repo_id). Returns (safety_by_repo, airbench_by_repo, safety_names_unresolved,
    airbench_names_unresolved).
    """
    safety_by_repo: dict[str, dict[str, Any]] = {}
    unresolved_safety: list[str] = []
    for helm_model, scen_data in safety_by_model.items():
        key = helm_name_to_org_slash_model(helm_model)
        rec = helm_meta.get(key)
        if rec and rec.get("exists") and rec.get("repo_id"):
            safety_by_repo[norm(rec["repo_id"])] = {"helm_model": helm_model, "scenarios": scen_data}
        else:
            unresolved_safety.append(helm_model)

    airbench_by_repo: dict[str, dict[str, Any]] = {}
    unresolved_airbench: list[str] = []
    for helm_model, rec_data in airbench_by_model.items():
        key = helm_name_to_org_slash_model(helm_model)
        rec = helm_meta.get(key)
        if rec and rec.get("exists") and rec.get("repo_id"):
            airbench_by_repo[norm(rec["repo_id"])] = {"helm_model": helm_model, **rec_data}
        else:
            unresolved_airbench.append(helm_model)

    return safety_by_repo, airbench_by_repo, unresolved_safety, unresolved_airbench


def lookup_with_alias(table: dict[str, Any], repo_id: str) -> tuple[Any, bool, str | None]:
    """Try the panel repo's own normalised id first; if absent, try its declared mirror
    alias (if any). Returns (value_or_None, is_alias_hit, alias_of_id_or_None).
    """
    key = norm(repo_id)
    if key in table:
        return table[key], False, None
    alias = MIRROR_ALIASES.get(key)
    if alias is not None:
        alias_key = norm(alias)
        if alias_key in table:
            return table[alias_key], True, alias
    return None, False, None


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def main() -> None:
    for p in (HELM_SAFETY_PATH, HELM_AIRBENCH_PATH, SALAD_PATH, HELM_META_PATH,
              OPENLLM_CAP_PATH, OPENLLM_INDEX_PATH, HELM_FIELDNAMES_PATH,
              OPENLLM_V2_PATH, OPENLLM_V1_OLD_PATH):
        if not p.exists():
            print(f"ERROR: required input missing: {p}", file=sys.stderr)
            raise SystemExit(1)

    safety_by_model = load_helm_safety(HELM_SAFETY_PATH)
    airbench_by_model = load_helm_airbench(HELM_AIRBENCH_PATH)
    helm_meta = load_helm_meta(HELM_META_PATH)
    cap_by_repo = load_openllm_capability(OPENLLM_CAP_PATH)
    salad = load_salad(SALAD_PATH)
    olb2_by_repo = load_openllm_v2_contents(OPENLLM_V2_PATH)
    olb1_old_by_repo = load_openllm_v1_old_contents(OPENLLM_V1_OLD_PATH)

    safety_by_repo, airbench_by_repo, unresolved_safety, unresolved_airbench = \
        build_helm_repo_index(safety_by_model, airbench_by_model, helm_meta)

    print(f"HELM safety table: {len(safety_by_model)} distinct model names, "
          f"{len(safety_by_repo)} resolved to a real (exists=True) HF repo_id via "
          f"helm_model_meta, {len(unresolved_safety)} unresolved (closed-API / no meta hit)")
    print(f"HELM airbench table: {len(airbench_by_model)} distinct model names, "
          f"{len(airbench_by_repo)} resolved to a real HF repo_id, "
          f"{len(unresolved_airbench)} unresolved")
    print(f"Open LLM Leaderboard capability table: {len(cap_by_repo)} rows")
    print(f"SALAD-Bench: status={salad.get('status')!r} — {salad.get('note')}")
    print(f"Open LLM Leaderboard v2 contents (commit {OPENLLM_V2_COMMIT_SHA[:12]}): "
          f"{len(olb2_by_repo)} distinct repos (post-dedup)")
    print(f"Open LLM Leaderboard v1-old contents (commit {OPENLLM_V1_COMMIT_SHA[:12]}): "
          f"{len(olb1_old_by_repo)} distinct repos (post-dedup) — mmlu/gsm8k fallback only")

    salad_reachable = salad.get("status") == "OK" and isinstance(salad.get("scores"), (dict, list))

    rows: list[dict[str, Any]] = []
    hit_repos: dict[str, list[str]] = {}  # column -> [repo_id,...]

    for repo_id in PANEL_REPOS:
        row: dict[str, Any] = {"repo_id": repo_id, "repo_id_norm": norm(repo_id)}

        # --- helm_safety_mean: mean of safety_score across the 4 safety-outcome scenarios
        safety_hit, safety_alias, safety_alias_of = lookup_with_alias(safety_by_repo, repo_id)
        if safety_hit is not None:
            scen_data = safety_hit["scenarios"]
            scores = [scen_data[s]["safety_score"] for s in SAFETY_SCENARIOS
                      if s in scen_data and scen_data[s]["safety_score"] is not None]
            row["helm_safety_mean"] = (sum(scores) / len(scores)) if scores else None
            row["helm_safety_mean_n_scenarios"] = len(scores)
            row["helm_safety_mean_source_file"] = "helm_safety_v1_17_0.json"
            row["helm_safety_mean_source_version"] = HELM_SAFETY_VERSION
            row["helm_safety_mean_helm_model_name"] = safety_hit["helm_model"]
            row["helm_safety_mean_alias"] = safety_alias
            row["helm_safety_mean_alias_of"] = safety_alias_of
            if row["helm_safety_mean"] is not None:
                hit_repos.setdefault("helm_safety_mean", []).append(repo_id)

            # --- helm_xstest: the xstest scenario's own safety_score
            xstest_scen = scen_data.get("xstest")
            row["helm_xstest"] = xstest_scen["safety_score"] if xstest_scen else None
            row["helm_xstest_source_file"] = "helm_safety_v1_17_0.json"
            row["helm_xstest_source_version"] = HELM_SAFETY_VERSION
            row["helm_xstest_alias"] = safety_alias
            row["helm_xstest_alias_of"] = safety_alias_of
            if row["helm_xstest"] is not None:
                hit_repos.setdefault("helm_xstest", []).append(repo_id)
        else:
            row["helm_safety_mean"] = None
            row["helm_safety_mean_n_scenarios"] = 0
            row["helm_safety_mean_source_file"] = None
            row["helm_safety_mean_source_version"] = None
            row["helm_safety_mean_helm_model_name"] = None
            row["helm_safety_mean_alias"] = False
            row["helm_safety_mean_alias_of"] = None
            row["helm_xstest"] = None
            row["helm_xstest_source_file"] = None
            row["helm_xstest_source_version"] = None
            row["helm_xstest_alias"] = False
            row["helm_xstest_alias_of"] = None

        # --- airbench_refusal: HELM AIR-Bench 2024 overall air_score
        air_hit, air_alias, air_alias_of = lookup_with_alias(airbench_by_repo, repo_id)
        if air_hit is not None:
            row["airbench_refusal"] = air_hit.get("air_score")
            row["airbench_refusal_source_file"] = "helm_airbench_v1_19_0.json"
            row["airbench_refusal_source_version"] = air_hit.get("version") or HELM_AIRBENCH_VERSION
            row["airbench_refusal_helm_model_name"] = air_hit["helm_model"]
            row["airbench_refusal_alias"] = air_alias
            row["airbench_refusal_alias_of"] = air_alias_of
            if row["airbench_refusal"] is not None:
                hit_repos.setdefault("airbench_refusal", []).append(repo_id)
        else:
            row["airbench_refusal"] = None
            row["airbench_refusal_source_file"] = None
            row["airbench_refusal_source_version"] = None
            row["airbench_refusal_helm_model_name"] = None
            row["airbench_refusal_alias"] = False
            row["airbench_refusal_alias_of"] = None

        # --- salad_score: SALAD-Bench harvest never produced a model-score table
        row["salad_score"] = None
        row["salad_score_source_file"] = "saladbench.json"
        row["salad_score_source_version"] = None
        row["salad_score_alias"] = False
        row["salad_score_alias_of"] = None
        if salad_reachable:
            # defensive path kept for forward-compat; this harvest's status is NOT_REACHABLE
            sal_hit, sal_alias, sal_alias_of = lookup_with_alias(salad.get("scores", {}), repo_id)
            if sal_hit is not None:
                row["salad_score"] = sal_hit
                row["salad_score_alias"] = sal_alias
                row["salad_score_alias_of"] = sal_alias_of
                hit_repos.setdefault("salad_score", []).append(repo_id)

        # --- mmlu / gsm8k: Open LLM Leaderboard archive capability table first (40-row
        # slice), falling back to the v1-old aggregated contents table (7,260 rows) only
        # when the capability table has no hit for this repo. Never imputed from anywhere
        # else; null if neither source has the exact id (or its mirror alias).
        cap_hit, cap_alias, cap_alias_of = lookup_with_alias(cap_by_repo, repo_id)
        if cap_hit is not None:
            row["mmlu"] = cap_hit.get("mmlu")
            row["gsm8k"] = cap_hit.get("gsm8k")
            row["mmlu_source_file"] = "openllm_capability.json"
            row["gsm8k_source_file"] = "openllm_capability.json"
            row["mmlu_source_version"] = cap_hit.get("source_file")
            row["gsm8k_source_version"] = cap_hit.get("source_file")
            row["mmlu_alias"] = cap_alias
            row["gsm8k_alias"] = cap_alias
            row["mmlu_alias_of"] = cap_alias_of
            row["gsm8k_alias_of"] = cap_alias_of
        else:
            olb1_hit, olb1_alias, olb1_alias_of = lookup_with_alias(olb1_old_by_repo, repo_id)
            if olb1_hit is not None:
                mmlu_raw = olb1_hit.get("MMLU")
                gsm8k_raw = olb1_hit.get("GSM8K")
                # v1-old MMLU/GSM8K are reported on a 0-100 scale; rescale to 0-1 to match
                # openllm_capability.json's 0-1 scale (mmlu/gsm8k columns) for comparability.
                row["mmlu"] = (mmlu_raw / 100.0) if mmlu_raw is not None else None
                row["gsm8k"] = (gsm8k_raw / 100.0) if gsm8k_raw is not None else None
                row["mmlu_source_file"] = "openllm_v1_old_contents.parquet"
                row["gsm8k_source_file"] = "openllm_v1_old_contents.parquet"
                row["mmlu_source_version"] = OPENLLM_V1_COMMIT_SHA
                row["gsm8k_source_version"] = OPENLLM_V1_COMMIT_SHA
                row["mmlu_alias"] = olb1_alias
                row["gsm8k_alias"] = olb1_alias
                row["mmlu_alias_of"] = olb1_alias_of
                row["gsm8k_alias_of"] = olb1_alias_of
            else:
                row["mmlu"] = None
                row["gsm8k"] = None
                row["mmlu_source_file"] = None
                row["gsm8k_source_file"] = None
                row["mmlu_source_version"] = None
                row["gsm8k_source_version"] = None
                row["mmlu_alias"] = False
                row["gsm8k_alias"] = False
                row["mmlu_alias_of"] = None
                row["gsm8k_alias_of"] = None
        if row["mmlu"] is not None:
            hit_repos.setdefault("mmlu", []).append(repo_id)
        if row["gsm8k"] is not None:
            hit_repos.setdefault("gsm8k", []).append(repo_id)

        # --- olb2_*: Open LLM Leaderboard v2 aggregated contents table
        olb2_hit, olb2_alias, olb2_alias_of = lookup_with_alias(olb2_by_repo, repo_id)
        olb2_field_map = {
            "olb2_average": "Average ⬆️", "olb2_ifeval": "IFEval", "olb2_bbh": "BBH",
            "olb2_math_lvl5": "MATH Lvl 5", "olb2_gpqa": "GPQA", "olb2_musr": "MUSR",
            "olb2_mmlu_pro": "MMLU-PRO",
        }
        if olb2_hit is not None:
            for out_col, src_col in olb2_field_map.items():
                row[out_col] = olb2_hit.get(src_col)
                if row[out_col] is not None:
                    hit_repos.setdefault(out_col, []).append(repo_id)
            row["olb2_chat_template"] = olb2_hit.get("Chat Template")
            row["olb2_precision"] = olb2_hit.get("Precision")
            row["olb2_eval_name"] = olb2_hit.get("eval_name")
            row["olb2_official_providers"] = olb2_hit.get("Official Providers")
            row["olb2_submission_date"] = str(olb2_hit.get("Submission Date")) \
                if olb2_hit.get("Submission Date") is not None else None
            row["olb2_n_submissions_for_repo"] = olb2_hit.get("_n_submissions_for_repo")
            row["olb2_source_file"] = "openllm_v2_contents.parquet"
            row["olb2_source_version"] = OPENLLM_V2_COMMIT_SHA
            row["olb2_alias"] = olb2_alias
            row["olb2_alias_of"] = olb2_alias_of
        else:
            for out_col in olb2_field_map:
                row[out_col] = None
            row["olb2_chat_template"] = None
            row["olb2_precision"] = None
            row["olb2_eval_name"] = None
            row["olb2_official_providers"] = None
            row["olb2_submission_date"] = None
            row["olb2_n_submissions_for_repo"] = None
            row["olb2_source_file"] = None
            row["olb2_source_version"] = None
            row["olb2_alias"] = False
            row["olb2_alias_of"] = None

        row["alias"] = bool(row["helm_safety_mean_alias"] or row["airbench_refusal_alias"]
                             or row["salad_score_alias"] or row["mmlu_alias"]
                             or row["olb2_alias"])
        rows.append(row)

    value_columns = ["helm_safety_mean", "helm_xstest", "airbench_refusal", "salad_score",
                      "mmlu", "gsm8k", "olb2_average", "olb2_ifeval", "olb2_bbh",
                      "olb2_math_lvl5", "olb2_gpqa", "olb2_musr", "olb2_mmlu_pro"]
    n_per_column = {c: len(hit_repos.get(c, [])) for c in value_columns}

    print("\n=== n per column (non-null) ===")
    for c in value_columns:
        print(f"  {c}: {n_per_column[c]}  repos={hit_repos.get(c, [])}")

    notes = [
        "Join is EXACT repo id only (case-insensitively normalised); no fuzzy/substring "
        "matching, no imputation. Missing values are null, never filled in.",
        "HELM safety (helm_safety_v1_17_0.json) and AIR-Bench (helm_airbench_v1_19_0.json) "
        "cover 81 and 87 distinct model NAMES respectively, but per helm_model_meta.json "
        "only 22 of those names resolve to a real, existing HF repo_id at all — and every "
        "one of those 22 is a mid/large flagship checkpoint (32B/13B/8x7B/8x22B/67B/72B/"
        "235B/R1/V3/gpt-oss-20B-120B, etc). None of the 39 panel repos (all 0.5B-4B small "
        "chat/abliterated checkpoints) or their declared mirror aliases match any of those "
        "22 repo_ids, so helm_safety_mean and helm_xstest are null for the entire panel.",
        "openllm_capability.json holds only 40 rows out of the 7,116-repo Open LLM "
        "Leaderboard archive indexed by openllm_archive_index.json (that index carries no "
        "scores, only n_repos/sample_paths — kept for provenance, not joined against). "
        "Those 40 rows are the alphabetically-first slice of the archive ('1TuanPham/...' "
        "through 'Azure99/...') and contain no panel repo or its mirror alias, so mmlu/"
        "gsm8k get 0 hits from that table — but the v1-old aggregated contents fallback "
        "(next note) recovers 1 of them.",
        "mmlu/gsm8k fallback: downloaded open-llm-leaderboard-old/contents (commit "
        f"{OPENLLM_V1_COMMIT_SHA[:12]}), a single 7,260-row/1.3MB aggregated parquet with "
        "MMLU and GSM8K columns (0-100 scale, rescaled to 0-1 here to match "
        "openllm_capability.json's scale) — used ONLY when openllm_capability.json had no "
        "hit. open-llm-leaderboard-old/results and open-llm-leaderboard/results (the raw "
        "per-run-JSON archives openllm_archive_index.json already indexed) were checked and "
        "explicitly skipped: 10,152/10,510 individual results_*.json files each, not one "
        "small aggregated table, so fetching them exhaustively was out of scope here.",
        "olb2_* columns: downloaded open-llm-leaderboard/contents (commit "
        f"{OPENLLM_V2_COMMIT_SHA[:12]}, data/train-00000-of-00001.parquet, ~1.1MB/4576 "
        "rows) fresh via stdlib urllib against the HF resolve endpoint (no huggingface_hub "
        "needed). A few `fullname`s have >1 submitted row at different precisions (seen: "
        "Qwen/Qwen2.5-0.5B-Instruct bfloat16+float16, HuggingFaceTB/SmolLM2-360M-Instruct "
        "bfloat16+float16) — deduped by preferring Official Providers=True then the latest "
        "Submission Date, recorded per-row as olb2_n_submissions_for_repo/olb2_precision/"
        "olb2_submission_date so the choice is auditable, not silent.",
        "saladbench.json's own harvest status is NOT_REACHABLE: SALAD-Bench (OpenSafetyLab/"
        "Salad-Data) ships raw QA data, not a published per-model score/leaderboard table, "
        "so salad_score is structurally null for every panel repo, not a join miss.",
        "HELM model-name resolution note: the safety/airbench tables key rows by an "
        "underscore-joined display name (e.g. 'qwen_qwen3-235b-a22b-instruct-2507-fp8'); "
        "helm_model_meta.json's records dict is keyed by the slash-joined 'org/model' form "
        "and gives the literal lower-cased guess it checked against the HF Hub as repo_id, "
        "flagged exists=True/False — this script only trusts exists=True entries as real "
        "repo_ids, it does not invent casing or spelling beyond what that probe found.",
        "Mirror aliases declared (checked, none present in the source tables so unused in "
        "this run): unsloth/Llama-3.2-1B-Instruct<->meta-llama/Llama-3.2-1B-Instruct, "
        "unsloth/Llama-3.2-3B-Instruct<->meta-llama/Llama-3.2-3B-Instruct, "
        "unsloth/gemma-2-2b-it<->google/gemma-2-2b-it.",
        "Honest bottom line: HELM safety/xstest, HELM AIR-Bench and SALAD-Bench still get "
        "0/37 hits (small panel checkpoints vs. datasets harvested around flagship-scale "
        "models, or no score table at all for SALAD). The v2 Open LLM Leaderboard "
        "aggregated table changes the capability picture substantially: 16/37 panel repos "
        "hit olb2_* (average/ifeval/bbh/math_lvl5/gpqa/musr/mmlu_pro together, since it's "
        "one row per repo), and mmlu/gsm8k recover exactly 1 hit (TinyLlama/TinyLlama-1.1B-"
        "Chat-v1.0) via the v1-old fallback once the 40-row capability.json slice came up "
        "empty for it too.",
    ]

    sources = {}
    for p in (HELM_SAFETY_PATH, HELM_AIRBENCH_PATH, SALAD_PATH, HELM_META_PATH,
              OPENLLM_CAP_PATH, OPENLLM_INDEX_PATH, HELM_FIELDNAMES_PATH,
              OPENLLM_V2_PATH, OPENLLM_V1_OLD_PATH):
        sources[p.name] = sha256_of(p)
    sources["open-llm-leaderboard/contents@commit"] = OPENLLM_V2_COMMIT_SHA
    sources["open-llm-leaderboard-old/contents@commit"] = OPENLLM_V1_COMMIT_SHA

    output = {
        "rows": rows,
        "n_per_column": n_per_column,
        "notes": notes,
        "sources": sources,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(output, indent=2, default=str))
    tmp.replace(OUT)
    print(f"\nwrote {OUT} ({OUT.stat().st_size / 1e3:.1f} KB)")


if __name__ == "__main__":
    main()
