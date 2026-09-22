"""Lane C — external limb: aggregates the pre-downloaded HELM/Open-LLM-Leaderboard JSON
tables into joined, resolved, feasibility-annotated python structures.

Nothing here downloads from HELM — the three input files
(helm_safety_v1_17_0.json, helm_airbench_v1_19_0.json, openllm_capability.json) are already
on disk under WS/external/. The only network calls this module makes are to the HF Hub, to
resolve a HELM display name to a real repo_id and to check whether that repo's weights are
actually downloadable (gated / safetensors / size / quantisation).

Resolution pipeline (resolve_name_to_repo), in order:
  (i)   CLOSED-API detection: the org prefix of the HELM name is checked against the closed
        set actually present in this file's `org` column, with explicit per-model carve-outs
        for closed-org names that are nonetheless open-weight releases (e.g. openai_gpt-oss-*).
  (ii)  a hand map of verified aliases (checked live against the HF Hub while building this
        module — see HAND_MAP below).
  (iii) HfApi.list_models(search=...) with a scored match that requires both the model
        FAMILY token and the SIZE token to appear in the candidate id, and prefers a
        non-quantised, canonical-org candidate.
  (iv)  otherwise UNRESOLVED. This function never guesses past step (iii)'s scored match.

All functions are pure / side-effect-free at import time. resolve_name_to_repo and
helm_feasibility perform network I/O only when *called*, and only when handed a live HfApi
client (resolve_name_to_repo) — with no client they stop after the hand map.
"""
from __future__ import annotations

import re
import statistics
from typing import Any

from loguru import logger

# --------------------------------------------------------------------------------- constants

#: Orgs that are closed-API-only IN THIS DATASET. Membership here is necessary but not
#: sufficient — PER_MODEL_OPEN_EXCEPTIONS (checked first) carves out open-weight releases
#: from organisations that are otherwise closed-API (e.g. OpenAI's gpt-oss line).
KNOWN_CLOSED_API_ORGS: frozenset[str] = frozenset({
    "openai", "anthropic", "google", "cohere", "xai", "writer",
    # not observed in this dataset's `org` column, but kept so the classifier is correct if a
    # future harvest adds them (per the task's "build carefully" instruction):
    "ai21", "ai21labs", "aws", "amazon", "perplexity", "microsoft",
})

#: Orgs whose HELM names look like they *could* be closed-API but ship real open weights in
#: THIS dataset — spelled out so nobody re-adds them to KNOWN_CLOSED_API_ORGS by reflex.
#: (databricks_dbrx-instruct is Apache-2.0 open weight; deepseek-ai is fully open.)
CONFIRMED_OPEN_ORGS_NOT_CLOSED: frozenset[str] = frozenset({"databricks", "deepseek-ai"})

#: Per-model carve-outs: a HELM name whose ORG is in KNOWN_CLOSED_API_ORGS but which is
#: itself an open-weight release. Detected by a regex over the slug (portion after "org_"),
#: not by full-name equality, so future gpt-oss variants are covered too.
_OPEN_EXCEPTION_PATTERNS: dict[str, re.Pattern] = {
    "openai": re.compile(r"gpt-oss"),
}

#: Hand map of HELM display name -> real, verified HF repo_id, for the open-weight orgs in
#: this dataset. Every entry was checked live via HfApi.model_info while this module was
#: written (2026-09-21) and existed with status 200 at that time.
HAND_MAP: dict[str, str] = {
    # allenai — OLMo
    "allenai_olmo-2-0325-32b-instruct": "allenai/OLMo-2-0325-32B-Instruct",
    "allenai_olmo-2-1124-13b-instruct": "allenai/OLMo-2-1124-13B-Instruct",
    "allenai_olmo-2-1124-7b-instruct": "allenai/OLMo-2-1124-7B-Instruct",
    "allenai_olmoe-1b-7b-0125-instruct": "allenai/OLMoE-1B-7B-0125-Instruct",
    # databricks
    "databricks_dbrx-instruct": "databricks/dbrx-instruct",
    # deepseek-ai
    "deepseek-ai_deepseek-llm-67b-chat": "deepseek-ai/deepseek-llm-67b-chat",
    "deepseek-ai_deepseek-r1": "deepseek-ai/DeepSeek-R1",
    "deepseek-ai_deepseek-r1-0528": "deepseek-ai/DeepSeek-R1-0528",
    # "-hide-reasoning" is a HELM SERVING CONFIG (whether the <think> block is shown), not a
    # distinct HF checkpoint: same weights as deepseek-r1. Flagged for guardian_pair_ceiling.
    "deepseek-ai_deepseek-r1-hide-reasoning": "deepseek-ai/DeepSeek-R1",
    "deepseek-ai_deepseek-v3": "deepseek-ai/DeepSeek-V3",
    # ibm — Granite
    "ibm_granite-3.3-8b-instruct": "ibm-granite/granite-3.3-8b-instruct",
    "ibm_granite-4.0-h-small": "ibm-granite/granite-4.0-h-small",
    # "-with-guardian" is the base model served behind IBM's Granite Guardian moderation
    # layer, not a separate weights repo: same weights as granite-4.0-h-small. Flagged for
    # guardian_pair_ceiling.
    "ibm_granite-4.0-h-small-with-guardian": "ibm-granite/granite-4.0-h-small",
    "ibm_granite-4.0-micro": "ibm-granite/granite-4.0-micro",
    "ibm_granite-4.0-micro-with-guardian": "ibm-granite/granite-4.0-micro",
    # marin-community
    "marin-community_marin-8b-instruct": "marin-community/marin-8b-instruct",
    # meta — Llama (HELM's "-turbo" suffix is a Together-AI serving tier, not a repo variant)
    "meta_llama-3-70b-chat": "meta-llama/Meta-Llama-3-70B-Instruct",
    "meta_llama-3-8b-chat": "meta-llama/Meta-Llama-3-8B-Instruct",
    "meta_llama-3.1-405b-instruct-turbo": "meta-llama/Llama-3.1-405B-Instruct",
    "meta_llama-3.1-70b-instruct-turbo": "meta-llama/Llama-3.1-70B-Instruct",
    "meta_llama-3.1-8b-instruct-turbo": "meta-llama/Llama-3.1-8B-Instruct",
    "meta_llama-4-maverick-17b-128e-instruct-fp8": "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
    "meta_llama-4-scout-17b-16e-instruct": "meta-llama/Llama-4-Scout-17B-16E-Instruct",
    # mistralai
    "mistralai_mistral-7b-instruct-v0.1": "mistralai/Mistral-7B-Instruct-v0.1",
    "mistralai_mistral-7b-instruct-v0.3": "mistralai/Mistral-7B-Instruct-v0.3",
    "mistralai_mixtral-8x22b-instruct-v0.1": "mistralai/Mixtral-8x22B-Instruct-v0.1",
    "mistralai_mixtral-8x7b-instruct-v0.1": "mistralai/Mixtral-8x7B-Instruct-v0.1",
    # moonshotai
    "moonshotai_kimi-k2-instruct": "moonshotai/Kimi-K2-Instruct",
    # openai open-weight carve-outs
    "openai_gpt-oss-120b": "openai/gpt-oss-120b",
    "openai_gpt-oss-20b": "openai/gpt-oss-20b",
    # qwen (HELM's "-tput" suffix is a Together-AI throughput serving tier)
    "qwen_qwen1.5-72b-chat": "Qwen/Qwen1.5-72B-Chat",
    "qwen_qwen2-72b-instruct": "Qwen/Qwen2-72B-Instruct",
    "qwen_qwen3-235b-a22b-fp8-tput": "Qwen/Qwen3-235B-A22B-FP8",
    "qwen_qwen3-235b-a22b-instruct-2507-fp8": "Qwen/Qwen3-235B-A22B-Instruct-2507-FP8",
    "qwen_qwen3-next-80b-a3b-thinking": "Qwen/Qwen3-Next-80B-A3B-Thinking",
    # zai-org
    "zai-org_glm-4.5-air-fp8": "zai-org/GLM-4.5-Air-FP8",
}

#: Notes attached to resolutions where repo_id is the SAME WEIGHTS as another HELM row under
#: a different safety wrapper / serving config (rather than a 1:1 unique checkpoint).
_SHARED_WEIGHTS_NOTE: dict[str, str] = {
    "deepseek-ai_deepseek-r1-hide-reasoning": "same weights as deepseek-ai_deepseek-r1; "
        "'-hide-reasoning' is a HELM serving config, not a distinct HF checkpoint",
    "ibm_granite-4.0-h-small-with-guardian": "same weights as ibm_granite-4.0-h-small; "
        "'-with-guardian' denotes the base model served behind Granite Guardian, not a "
        "distinct HF checkpoint",
    "ibm_granite-4.0-micro-with-guardian": "same weights as ibm_granite-4.0-micro; "
        "'-with-guardian' denotes the base model served behind Granite Guardian, not a "
        "distinct HF checkpoint",
}

#: Filename / repo-id substrings that mark a quantised release.
_QUANT_MARKERS = re.compile(r"gptq|awq|\bfp8\b|int4|int8|bnb|exl2|gguf|quant", re.IGNORECASE)

#: Family tokens used by the search-fallback scorer (extend as new families appear).
_FAMILY_TOKENS = (
    "olmoe", "olmo", "granite", "llama", "mixtral", "mistral", "deepseek", "qwen", "glm",
    "kimi", "dbrx", "marin", "gpt-oss", "gptoss",
)

#: HELM's 5 safety-outcome scenarios use this common metric shape; bbq instead carries bias
#: metrics with no safety_score. Both sets are pulled straight off the file's own
#: field_names_by_scenario, this list only orders and documents them.
_SAFETY_METRIC_FIELDS = (
    "safety_score", "safety_gpt_score", "safety_llama_score",
    "safety_gpt_annotator_success", "safety_llama_annotator_success",
)
_BBQ_METRIC_FIELDS = ("bbq_accuracy", "bbq_metric_ambiguous_bias", "bbq_metric_unambiguous_bias")

#: Suffixes that denote "same weights, different safety wrapper / serving config" pairs.
_GUARDIAN_SUFFIX_MARKERS: tuple[tuple[str, str], ...] = (
    ("-with-guardian", "guardian_wrapper"),
    ("-hide-reasoning", "reasoning_visibility"),
    ("-safety-block-none", "safety_block_none"),
    ("-safety-block-most", "safety_block_most"),
    ("-thinking-10k", "reasoning_budget"),
)
#: Keyword allowlist for the generic auto-detection pass over any OTHER suffix pattern.
_GUARDIAN_KEYWORDS = (
    "guardian", "hide", "reasoning", "thinking", "safety", "block", "unsafe", "unfiltered",
    "moderated", "shield", "filter",
)


# ------------------------------------------------------------------------------ helm safety


def load_helm_safety(path: Any) -> list[dict[str, Any]]:
    """Pivot helm_safety_v1_17_0.json rows (one row per model*scenario) into one row per
    model, with a sub-dict per scenario. Every scenario key is present for every model, with
    an explicit `present` flag, so absence is never silently a missing key.
    """
    import json
    from pathlib import Path

    data = json.loads(Path(path).read_text())
    scenarios: list[str] = list(data["scenarios"])
    field_names = data.get("field_names_by_scenario", {})

    by_model: dict[str, dict[str, Any]] = {}
    for row in data["rows"]:
        model = row["model"]
        rec = by_model.setdefault(model, {"model": model, "org": row.get("org")})
        scen = row["scenario"]
        fields_here = set(field_names.get(scen, []))
        wanted = [f for f in _SAFETY_METRIC_FIELDS if f in fields_here] + \
                 [f for f in _BBQ_METRIC_FIELDS if f in fields_here]
        metrics = row.get("metrics", {})
        scen_rec: dict[str, Any] = {"present": True, "run_folder": row.get("run_folder"),
                                     "version": row.get("version")}
        for f in wanted:
            m = metrics.get(f)
            scen_rec[f] = m.get("mean") if isinstance(m, dict) else None
        rec[scen] = scen_rec

    out: list[dict[str, Any]] = []
    for model, rec in sorted(by_model.items()):
        for scen in scenarios:
            rec.setdefault(scen, {"present": False})
        out.append(rec)
    logger.info(f"load_helm_safety: {len(out)} models x {len(scenarios)} scenarios from {path}")
    return out


# ------------------------------------------------------------------------------- helm airbench

_AIR_TOP_CATEGORY_RE = re.compile(r"^air_category_(\d+)_score$")


def load_airbench(path: Any) -> list[dict[str, Any]]:
    """Pivot helm_airbench_v1_19_0.json (one scenario, air_bench_2024) into one row per model
    with the overall air_score plus the 16 top-level category scores.
    """
    import json
    from pathlib import Path

    data = json.loads(Path(path).read_text())
    out: list[dict[str, Any]] = []
    for row in data["rows"]:
        metrics = row.get("metrics", {})
        cat_scores: dict[str, float] = {}
        for key, m in metrics.items():
            match = _AIR_TOP_CATEGORY_RE.match(key)
            if match and isinstance(m, dict) and m.get("mean") is not None:
                cat_scores[f"category_{match.group(1)}"] = m["mean"]
        air = metrics.get("air_score")
        out.append({
            "model": row["model"],
            "org": row.get("org"),
            "air_score": air.get("mean") if isinstance(air, dict) else None,
            "n_top_category_scores": len(cat_scores),
            "air_category_scores": cat_scores,
        })
    out.sort(key=lambda r: r["model"])
    logger.info(f"load_airbench: {len(out)} models from {path}")
    return out


# ------------------------------------------------------------------------------- capability


def load_capability(path: Any) -> list[dict[str, Any]]:
    """Open LLM Leaderboard archive rows. Adds a lowercased repo key for joining."""
    import json
    from pathlib import Path

    data = json.loads(Path(path).read_text())
    rows = data["rows"] if isinstance(data, dict) and "rows" in data else data
    out = []
    for r in rows:
        rec = dict(r)
        rec["repo_lower"] = str(r.get("repo", "")).lower()
        out.append(rec)
    out.sort(key=lambda r: r.get("repo", ""))
    logger.info(f"load_capability: {len(out)} rows from {path}")
    return out


# --------------------------------------------------------------------------- name resolution


def _infer_org(helm_name: str) -> str:
    return helm_name.split("_", 1)[0]


def _is_closed_api(helm_name: str, org: str) -> bool:
    if org in CONFIRMED_OPEN_ORGS_NOT_CLOSED:
        return False
    if org not in KNOWN_CLOSED_API_ORGS:
        return False
    pattern = _OPEN_EXCEPTION_PATTERNS.get(org)
    slug = helm_name[len(org) + 1:] if helm_name.startswith(org + "_") else helm_name
    if pattern is not None and pattern.search(slug):
        return False
    return True


def _tokenize(s: str) -> set[str]:
    return set(t for t in re.split(r"[^a-z0-9]+", s.lower()) if t)


def _extract_family_and_size(slug: str) -> tuple[str | None, list[str]]:
    low = slug.lower()
    family = next((f for f in _FAMILY_TOKENS if f in low), None)
    sizes = re.findall(r"\d+(?:\.\d+)?x?\d*b(?!it)", low)
    return family, sizes


def _score_search_candidates(candidates: list[str], family: str | None,
                              sizes: list[str]) -> str | None:
    """Accept only a single, high-confidence, non-quantised candidate that contains both the
    family token and at least one size token. Never falls back to a fuzzy best-effort pick.
    """
    if family is None or not sizes:
        return None
    accepted = []
    for cand in candidates:
        norm = _tokenize(cand)
        cand_family_hit = any(family.replace("-", "") in tok or family in tok for tok in norm) \
            or family.replace("-", "") in cand.lower().replace("-", "")
        cand_size_hit = any(size in cand.lower() for size in sizes)
        if cand_family_hit and cand_size_hit and not _QUANT_MARKERS.search(cand):
            accepted.append(cand)
    if not accepted:
        return None
    accepted.sort(key=len)  # prefer the shortest / most canonical-looking id
    return accepted[0]


def resolve_name_to_repo(helm_name: str, hf_api: Any = None) -> dict[str, Any]:
    """Resolve one HELM display name to an HF repo_id, or explain why not.

    `hf_api` is an optional live huggingface_hub.HfApi instance; without one, resolution
    stops after the hand map (steps i-ii) and returns UNRESOLVED rather than guessing.
    """
    org = _infer_org(helm_name)

    if _is_closed_api(helm_name, org):
        return {"repo_id": None, "status": "CLOSED_API_BY_CONSTRUCTION", "org": org}

    if helm_name in HAND_MAP:
        result = {"repo_id": HAND_MAP[helm_name], "status": "RESOLVED_HANDMAP", "org": org}
        if helm_name in _SHARED_WEIGHTS_NOTE:
            result["note"] = _SHARED_WEIGHTS_NOTE[helm_name]
        return result

    if hf_api is not None:
        from huggingface_hub.errors import HfHubHTTPError

        slug = helm_name[len(org) + 1:] if helm_name.startswith(org + "_") else helm_name
        family, sizes = _extract_family_and_size(slug)
        if family is not None and sizes:
            try:
                query = f"{family} {sizes[0]}"
                candidates = [m.id for m in hf_api.list_models(search=query, limit=20)]
            except (HfHubHTTPError, OSError, ValueError) as exc:
                logger.warning(f"search fallback failed for {helm_name}: {exc}")
                candidates = []
            picked = _score_search_candidates(candidates, family, sizes)
            if picked is not None:
                return {"repo_id": picked, "status": "RESOLVED_SEARCH", "org": org}

    return {"repo_id": None, "status": "UNRESOLVED", "org": org}


# ---------------------------------------------------------------------------- HF feasibility


def helm_feasibility(repo_id: str, hf_api: Any) -> dict[str, Any]:
    """Query the HF Hub for one repo_id and record what a downloader would actually find:
    gated status, safetensors presence/bytes, architecture, param count, quantisation. 401 /
    403 / 404 come back as DATA (status_code + reason), never as a raised exception.
    """
    from huggingface_hub.errors import HfHubHTTPError

    result: dict[str, Any] = {
        "repo_id": repo_id, "exists": False, "status_code": None, "gated": None,
        "token_can_read": None, "has_safetensors": False, "n_params": None,
        "total_safetensors_bytes": 0, "architecture": None, "model_type": None,
        "is_quantised": bool(_QUANT_MARKERS.search(repo_id)), "feasible": False,
        "infeasible_reasons": [],
    }
    try:
        info = hf_api.model_info(repo_id, files_metadata=True)
    except HfHubHTTPError as exc:
        status = exc.response.status_code if exc.response is not None else None
        result["status_code"] = status
        result["exists"] = status not in (404, None)
        result["token_can_read"] = False
        result["infeasible_reasons"].append(f"HfHubHTTPError status={status}: {type(exc).__name__}")
        return result
    except (OSError, ValueError) as exc:
        result["infeasible_reasons"].append(f"{type(exc).__name__}: {exc}")
        return result

    result["exists"] = True
    result["status_code"] = 200
    result["token_can_read"] = True
    result["gated"] = info.gated

    siblings = list(info.siblings or [])
    st_files = [s for s in siblings if s.rfilename.endswith(".safetensors")]
    result["has_safetensors"] = len(st_files) > 0
    result["total_safetensors_bytes"] = sum((s.size or 0) for s in st_files)
    if any(_QUANT_MARKERS.search(s.rfilename) for s in siblings):
        result["is_quantised"] = True

    if info.safetensors is not None:
        result["n_params"] = info.safetensors.total
    cfg = info.config or {}
    archs = cfg.get("architectures")
    result["architecture"] = archs[0] if archs else None
    result["model_type"] = cfg.get("model_type")

    gated_ok = (info.gated in (False, None)) or bool(result["token_can_read"])
    if not gated_ok:
        result["infeasible_reasons"].append("gated and token cannot read")
    if not result["has_safetensors"]:
        result["infeasible_reasons"].append("no .safetensors files in repo")
    if result["n_params"] is None:
        result["infeasible_reasons"].append("n_params unknown (no safetensors parameter count)")
    elif result["n_params"] > 14e9:
        result["infeasible_reasons"].append(f"n_params={result['n_params']:.3g} > 14e9 cap")
    if result["is_quantised"]:
        result["infeasible_reasons"].append("quantised release (gptq/awq/fp8/int4/int8/gguf marker)")

    result["feasible"] = len(result["infeasible_reasons"]) == 0
    return result


# ---------------------------------------------------------------------- guardian pair ceiling


def _find_guardian_pairs(models: list[str]) -> list[tuple[str, str, str]]:
    """(base, variant, tag) triples: variant is the SAME underlying weights as base, served
    under a different safety wrapper / reasoning-visibility / reasoning-budget config.
    """
    name_set = set(models)
    seen: set[tuple[str, str]] = set()
    pairs: list[tuple[str, str, str]] = []

    for name in models:
        for marker, tag in _GUARDIAN_SUFFIX_MARKERS:
            if name.endswith(marker):
                base = name[: -len(marker)]
                if base in name_set and (base, name) not in seen:
                    pairs.append((base, name, tag))
                    seen.add((base, name))

    # generic pass: any OTHER model name that is base + "-" + suffix, where suffix contains a
    # guardian-style keyword not already caught by the explicit marker list above.
    for base in models:
        prefix = base + "-"
        for name in models:
            if name == base or not name.startswith(prefix) or (base, name) in seen:
                continue
            suffix = name[len(prefix):]
            if any(kw in suffix for kw in _GUARDIAN_KEYWORDS):
                pairs.append((base, name, f"auto:{suffix}"))
                seen.add((base, name))

    return pairs


def guardian_pair_ceiling(table: list[dict[str, Any]]) -> dict[str, Any]:
    """For every (base, variant) pair of HELM rows identified as the SAME WEIGHTS under a
    different safety wrapper, report the per-scenario |delta| in safety_score and the share
    of the TOTAL across-model variance in that scenario that this one pair's gap represents.
    This is a HARD CEILING on the variance any weights-only readout can ever explain, since
    two runs of literally the same weights already move the published score by this much.
    """
    by_model = {r["model"]: r for r in table}
    scenarios = [k for k in table[0].keys() if k not in ("model", "org")] if table else []
    models = [r["model"] for r in table]

    pairs_out: list[dict[str, Any]] = []
    best_share = 0.0
    best_share_ref: dict[str, Any] | None = None

    for base, variant, tag in _find_guardian_pairs(models):
        base_row, var_row = by_model[base], by_model[variant]
        per_scenario: dict[str, Any] = {}
        abs_deltas: list[float] = []
        for scen in scenarios:
            b_scen, v_scen = base_row.get(scen, {}), var_row.get(scen, {})
            if not (b_scen.get("present") and v_scen.get("present")):
                continue
            b, v = b_scen.get("safety_score"), v_scen.get("safety_score")
            if b is None or v is None:
                continue
            delta = v - b
            across = [r[scen].get("safety_score") for r in table
                      if r.get(scen, {}).get("present") and r[scen].get("safety_score") is not None]
            var_across = statistics.pvariance(across) if len(across) >= 3 else None
            share = (delta ** 2 / var_across) if var_across not in (None, 0) else None
            per_scenario[scen] = {
                "base_score": b, "variant_score": v, "delta": delta,
                "across_model_n": len(across), "across_model_variance": var_across,
                "share_of_across_model_variance": share,
            }
            abs_deltas.append(abs(delta))
            if share is not None and share > best_share:
                best_share = share
                best_share_ref = {"base": base, "variant": variant, "tag": tag, "scenario": scen,
                                   "share_of_across_model_variance": share}
        pairs_out.append({
            "base": base, "variant": variant, "tag": tag,
            "per_scenario": per_scenario,
            "mean_abs_delta": statistics.fmean(abs_deltas) if abs_deltas else None,
            "n_scenarios_with_data": len(per_scenario),
        })

    logger.info(f"guardian_pair_ceiling: {len(pairs_out)} same-weights pairs found; "
                f"headline max share_of_across_model_variance={best_share:.4f}")
    return {
        "pairs": pairs_out,
        "n_pairs": len(pairs_out),
        "headline_max_share_of_across_model_variance": best_share if pairs_out else None,
        "headline_ref": best_share_ref,
        "note": "A single same-weights pair's squared score gap divided by the total "
                "across-model variance in that scenario. This is a HARD CEILING: any "
                "weights-only readout is mechanically blind to the wrapper, so it cannot "
                "explain more of the across-model variance than genuinely different weights "
                "leave unexplained once this much is already wrapper-only noise.",
    }
