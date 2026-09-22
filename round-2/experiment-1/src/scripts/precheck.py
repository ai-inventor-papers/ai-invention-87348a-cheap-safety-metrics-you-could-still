"""P0. ARCHITECTURE PRECHECK.

Prove, before any weights are touched, which model classes actually import at
the transformers version pinned in this workspace's lockfile.  Iteration 1
lost 15 of its 32 checkpoints at harvest time to ModuleNotFoundError because
its resolved transformers (5.17.0) removed/moved several model modules.  This
script makes ONLY config/metadata HTTP calls -- it never downloads weights.
"""

from __future__ import annotations

import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Any, Callable, TypeVar

from loguru import logger

_T = TypeVar("_T")

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
LOGS = ROOT / "logs"
SCREEN = ROOT / "screen"
INHERITED = ROOT / "inherited"

sys.path.insert(0, str(ROOT))

RESULTS.mkdir(parents=True, exist_ok=True)
LOGS.mkdir(parents=True, exist_ok=True)

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss} | {level: <7} | {message}")
logger.add(LOGS / "precheck.log", level="DEBUG", format="{time:HH:mm:ss} | {level: <7} | {message}", mode="w")

HF_TOKEN = os.environ.get("HF_TOKEN")

EXTRA_CENSORTUNE_REPOS: list[dict] = [
    dict(
        repo="huihui-ai/Qwen2.5-0.5B-Instruct-CensorTune",
        family="Qwen2.5",
        cls="blanket_refuser",
        lineage="Qwen2.5::CensorTune-0.5B",
    ),
    dict(
        repo="huihui-ai/Qwen2.5-1.5B-Instruct-CensorTune",
        family="Qwen2.5",
        cls="blanket_refuser",
        lineage="Qwen2.5::CensorTune-1.5B",
    ),
]

REQUIRED_MODEL_TYPES = {"gemma2", "qwen2", "qwen3", "phi3", "olmo2", "smollm3", "llama"}

# This machine's HF_TOKEN is shared across many concurrent tenants on this box, so the
# Hub's "1000 requests / 5 minutes" quota gets hit routinely and returns transient 429s
# that have NOTHING to do with a repo's real architecture. Retrying with backoff turns
# those transient failures back into real signal instead of false "dropped" rows.
MAX_HUB_RETRIES = 6
HUB_RETRY_BASE_SECS = 4.0
HUB_RETRY_MAX_SECS = 45.0


def call_with_retry(fn: Callable[[], _T], what: str) -> _T:
    """Call fn(), retrying with exponential backoff + jitter on 429 / 5xx Hub errors.
    Any other exception (404, 403, config errors, etc.) propagates immediately --
    those are real signal, not transient load."""
    from huggingface_hub.utils import HfHubHTTPError

    last_exc: Exception | None = None
    for attempt in range(MAX_HUB_RETRIES):
        try:
            return fn()
        except HfHubHTTPError as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            last_exc = exc
            if status == 429 or (isinstance(status, int) and 500 <= status < 600):
                delay = min(HUB_RETRY_MAX_SECS, HUB_RETRY_BASE_SECS * (2 ** attempt)) + random.uniform(0, 1.5)
                logger.debug(
                    f"{what}: transient HfHubHTTPError status={status} "
                    f"(attempt {attempt + 1}/{MAX_HUB_RETRIES}); backing off {delay:.1f}s"
                )
                time.sleep(delay)
                continue
            raise
    assert last_exc is not None
    raise last_exc


def build_candidates(panel: list[dict], sealed_families: list[str]) -> tuple[list[dict], list[dict]]:
    """Union PANEL repos (excluding sealed families) with the extra CensorTune
    poles. Returns (candidates, sealed_not_touched)."""
    candidates: list[dict] = []
    sealed_not_touched: list[dict] = []
    seen_repos: set[str] = set()
    for entry in panel:
        if entry["family"] in sealed_families:
            sealed_not_touched.append(
                dict(repo=entry["repo"], family=entry["family"], cls=entry.get("cls"), lineage=entry.get("lineage"))
            )
            continue
        if entry["repo"] in seen_repos:
            continue
        seen_repos.add(entry["repo"])
        candidates.append(
            dict(repo=entry["repo"], family=entry["family"], cls=entry.get("cls"), lineage=entry.get("lineage"))
        )
    for extra in EXTRA_CENSORTUNE_REPOS:
        if extra["repo"] in seen_repos:
            continue
        seen_repos.add(extra["repo"])
        candidates.append(dict(extra))
    return candidates, sealed_not_touched


def cache_dir_for_repo(hf_hub_cache: Path, repo: str) -> Path:
    safe = repo.replace("/", "--").replace("_", "-")
    return hf_hub_cache / f"models--{safe}" / "blobs"


def weights_cached_gb(hf_hub_cache: Path, repo: str) -> float:
    blobs_dir = cache_dir_for_repo(hf_hub_cache, repo)
    if not blobs_dir.is_dir():
        return 0.0
    total_bytes = 0
    threshold = 50 * 1024 * 1024
    try:
        for f in blobs_dir.iterdir():
            try:
                if f.is_file():
                    sz = f.stat().st_size
                    if sz > threshold:
                        total_bytes += sz
            except OSError as exc:
                logger.debug(f"stat failed for {f}: {exc}")
    except OSError as exc:
        logger.debug(f"iterdir failed for {blobs_dir}: {exc}")
        return 0.0
    return round(total_bytes / (1024 ** 3), 4)


def process_repo(
    transformers_mod: Any,
    hf_api: Any,
    hf_hub_cache: Path,
    entry: dict,
) -> dict:
    from huggingface_hub.utils import HfHubHTTPError, RepositoryNotFoundError, GatedRepoError

    repo = entry["repo"]
    row: dict[str, Any] = dict(
        repo=repo,
        family=entry.get("family"),
        cls=entry.get("cls"),
        lineage=entry.get("lineage"),
        model_type=None,
        cls_name=None,
        import_ok=False,
        import_error=None,
        config_ok=False,
        config_error=None,
        gated=None,
        token_resolves=False,
        http_status=None,
        has_safetensors=False,
        n_params=None,
        bf16_gb=None,
        n_layers=None,
        hidden_size=None,
        tie_word_embeddings=None,
        torch_dtype=None,
        chat_template_present=False,
        config_sha=None,
        weights_cached_gb=0.0,
    )

    # --- AutoConfig ---
    cfg = None
    try:
        cfg = call_with_retry(
            lambda: transformers_mod.AutoConfig.from_pretrained(repo, token=HF_TOKEN, trust_remote_code=False),
            f"{repo}: AutoConfig",
        )
        row["config_ok"] = True
        row["token_resolves"] = True
        row["http_status"] = 200
        row["model_type"] = getattr(cfg, "model_type", None)
        row["n_layers"] = getattr(cfg, "num_hidden_layers", None)
        row["hidden_size"] = getattr(cfg, "hidden_size", None)
        row["tie_word_embeddings"] = getattr(cfg, "tie_word_embeddings", None)
        td = getattr(cfg, "torch_dtype", None)
        row["torch_dtype"] = str(td) if td is not None else None
    except GatedRepoError as exc:
        row["config_error"] = f"GatedRepoError: {exc}"
        row["http_status"] = 403
    except RepositoryNotFoundError as exc:
        row["config_error"] = f"RepositoryNotFoundError: {exc}"
        row["http_status"] = 404
    except HfHubHTTPError as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        row["config_error"] = f"HfHubHTTPError: {exc}"
        row["http_status"] = status if status is not None else "HfHubHTTPError"
    except (OSError, ValueError, KeyError, TypeError) as exc:
        row["config_error"] = f"{type(exc).__name__}: {exc}"
        row["http_status"] = type(exc).__name__

    # --- import check: does the mapped modeling class resolve on this transformers? ---
    if row["model_type"] is not None:
        try:
            from transformers.models.auto.modeling_auto import MODEL_FOR_CAUSAL_LM_MAPPING_NAMES

            cls_name = MODEL_FOR_CAUSAL_LM_MAPPING_NAMES.get(row["model_type"])
            row["cls_name"] = cls_name
            if cls_name is None:
                row["import_ok"] = False
                row["import_error"] = f"model_type {row['model_type']!r} not in MODEL_FOR_CAUSAL_LM_MAPPING_NAMES"
            else:
                resolved = getattr(transformers_mod, cls_name, None)
                row["import_ok"] = resolved is not None
                if resolved is None:
                    row["import_error"] = f"getattr(transformers, {cls_name!r}) is None / missing"
        except (ImportError, ModuleNotFoundError, AttributeError, KeyError) as exc:
            row["import_ok"] = False
            row["import_error"] = f"{type(exc).__name__}: {exc}"

    # --- model_info (gated flag, file list, safetensors, sha) ---
    try:
        info = call_with_retry(
            lambda: hf_api.model_info(repo, files_metadata=True, token=HF_TOKEN),
            f"{repo}: model_info",
        )
        row["gated"] = info.gated
        row["config_sha"] = info.sha
        siblings = info.siblings or []
        has_st = any(s.rfilename.endswith(".safetensors") for s in siblings)
        row["has_safetensors"] = has_st
        total_params = None
        st = getattr(info, "safetensors", None)
        if st is not None and getattr(st, "total", None):
            total_params = st.total
        if total_params:
            row["n_params"] = total_params
            row["bf16_gb"] = round(total_params * 2 / (1024 ** 3), 4)
        else:
            total_size = 0
            for s in siblings:
                if s.rfilename.endswith(".safetensors") and getattr(s, "size", None):
                    total_size += s.size
            if total_size:
                row["bf16_gb"] = round(total_size / (1024 ** 3), 4)
    except GatedRepoError as exc:
        row["config_error"] = row["config_error"] or f"GatedRepoError(model_info): {exc}"
        if row["http_status"] is None:
            row["http_status"] = 403
    except RepositoryNotFoundError as exc:
        row["config_error"] = row["config_error"] or f"RepositoryNotFoundError(model_info): {exc}"
        if row["http_status"] is None:
            row["http_status"] = 404
    except HfHubHTTPError as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        row["config_error"] = row["config_error"] or f"HfHubHTTPError(model_info): {exc}"
        if row["http_status"] is None:
            row["http_status"] = status if status is not None else "HfHubHTTPError"
    except (OSError, ValueError, KeyError, TypeError) as exc:
        row["config_error"] = row["config_error"] or f"{type(exc).__name__}(model_info): {exc}"
        if row["http_status"] is None:
            row["http_status"] = type(exc).__name__

    # --- chat template presence (tokenizer config fetch, no weights) ---
    try:
        tok = call_with_retry(
            lambda: transformers_mod.AutoTokenizer.from_pretrained(repo, token=HF_TOKEN, trust_remote_code=False),
            f"{repo}: AutoTokenizer",
        )
        tmpl = getattr(tok, "chat_template", None)
        row["chat_template_present"] = bool(tmpl)
    except (OSError, ValueError, KeyError, TypeError, ImportError, ModuleNotFoundError) as exc:
        logger.debug(f"{repo}: tokenizer fetch failed: {type(exc).__name__}: {exc}")

    # --- cached weight bytes already on the shared cache disk ---
    try:
        row["weights_cached_gb"] = weights_cached_gb(hf_hub_cache, repo)
    except (OSError, ValueError) as exc:
        logger.debug(f"{repo}: cache scan failed: {exc}")

    return row


def apply_gate(row: dict) -> tuple[bool, str | None]:
    reasons: list[str] = []
    if not row["import_ok"]:
        reasons.append(f"import_ok=False ({row.get('import_error')})")
    if row["http_status"] in (401, 403, 404):
        reasons.append(f"http_status={row['http_status']}")
    if not row["has_safetensors"]:
        reasons.append("has_safetensors=False")
    if reasons:
        return True, "; ".join(reasons)
    return False, None


@logger.catch(reraise=True)
def main() -> None:
    import torch
    import transformers
    from huggingface_hub import HfApi

    torch_version = torch.__version__
    transformers_version = transformers.__version__
    cuda_available = torch.cuda.is_available()

    logger.info(f"transformers.__version__ = {transformers_version}")
    logger.info(f"torch.__version__ = {torch_version}")
    logger.info(f"torch.cuda.is_available() = {cuda_available} (machine has NO GPU -- expected, not an error)")

    from screen.panel import PANEL, SEALED_FAMILIES, sealed_guard  # noqa: F401

    candidates, sealed_not_touched = build_candidates(PANEL, SEALED_FAMILIES)
    logger.info(f"n_candidates = {len(candidates)}; sealed_not_touched = {len(sealed_not_touched)}")
    for s in sealed_not_touched:
        logger.info(f"SEALED, not touched: {s['repo']} (family={s['family']})")

    hf_hub_cache = Path(os.environ.get("HF_HUB_CACHE", str(Path.home() / ".cache" / "huggingface" / "hub")))
    hf_api = HfApi(token=HF_TOKEN)

    rows: list[dict] = []
    for entry in candidates:
        repo = entry["repo"]
        try:
            row = process_repo(transformers, hf_api, hf_hub_cache, entry)
        except Exception as exc:  # noqa: BLE001 -- last-resort guard so one bad repo never aborts the table
            logger.error(f"{repo}: UNEXPECTED top-level failure: {type(exc).__name__}: {exc}")
            row = dict(
                repo=repo,
                family=entry.get("family"),
                cls=entry.get("cls"),
                lineage=entry.get("lineage"),
                model_type=None,
                cls_name=None,
                import_ok=False,
                import_error=None,
                config_ok=False,
                config_error=f"UNEXPECTED {type(exc).__name__}: {exc}",
                gated=None,
                token_resolves=False,
                http_status=type(exc).__name__,
                has_safetensors=False,
                n_params=None,
                bf16_gb=None,
                n_layers=None,
                hidden_size=None,
                tie_word_embeddings=None,
                torch_dtype=None,
                chat_template_present=False,
                config_sha=None,
                weights_cached_gb=0.0,
            )
        dropped, drop_reason = apply_gate(row)
        row["dropped"] = dropped
        row["drop_reason"] = drop_reason
        rows.append(row)
        logger.info(
            f"row: repo={repo} model_type={row['model_type']} import_ok={row['import_ok']} "
            f"gated={row['gated']} has_safetensors={row['has_safetensors']} "
            f"cached_gb={row['weights_cached_gb']} dropped={dropped}"
            + (f" drop_reason={drop_reason}" if dropped else "")
        )

    # --- families surviving / instruct-abliterated pairs ---
    surviving_by_family: dict[str, list[dict]] = {}
    for r in rows:
        if not r["dropped"]:
            surviving_by_family.setdefault(r["family"], []).append(r)

    families_surviving = sorted(surviving_by_family)
    families_with_pair = sorted(
        fam
        for fam, frows in surviving_by_family.items()
        if any(r["cls"] == "instruct" for r in frows) and any(r["cls"] == "abliterated" for r in frows)
    )

    # --- iteration-1 drop reasons reproduced ---
    it1_drop_reasons_reproduced: dict[str, str] = {}
    harvest_status_path = INHERITED / "harvest_status.json"
    n_it1_failures_now_ok = 0
    still_failing: list[dict] = []
    if harvest_status_path.exists():
        try:
            it1_status = json.loads(harvest_status_path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            logger.error(f"failed to read {harvest_status_path}: {exc}")
            it1_status = {}
        rows_by_repo = {r["repo"]: r for r in rows}
        for repo, status in it1_status.items():
            if status.get("ok") is False:
                it1_drop_reasons_reproduced[repo] = status.get("error", "")
                new_row = rows_by_repo.get(repo)
                if new_row is not None and new_row["import_ok"]:
                    n_it1_failures_now_ok += 1
                else:
                    new_error = None
                    if new_row is not None:
                        new_error = new_row.get("import_error") or new_row.get("config_error")
                    still_failing.append(dict(repo=repo, new_error=new_error))
    else:
        logger.warning(f"{harvest_status_path} not found; it1_drop_reasons_reproduced left empty")

    transformers_pin_experiment = {
        "old_version": "5.17.0",
        "new_version": transformers_version,
        "it1_failures_under_old": len(it1_drop_reasons_reproduced),
        "n_repaired_under_new": n_it1_failures_now_ok,
        "still_failing": still_failing,
    }
    logger.info(f"transformers_pin_experiment = {transformers_pin_experiment}")

    # --- required model types (second check) ---
    from transformers.models.auto.modeling_auto import MODEL_FOR_CAUSAL_LM_MAPPING_NAMES

    required_model_types: dict[str, bool] = {}
    for mt in sorted(REQUIRED_MODEL_TYPES):
        try:
            cls_name = MODEL_FOR_CAUSAL_LM_MAPPING_NAMES.get(mt)
            required_model_types[mt] = cls_name is not None and getattr(transformers, cls_name, None) is not None
        except (KeyError, AttributeError) as exc:
            logger.error(f"required model type {mt} check failed: {exc}")
            required_model_types[mt] = False
    all_required_ok = all(required_model_types.values())
    logger.info(f"required_model_types = {required_model_types}; all_required_ok = {all_required_ok}")

    dropped_list = [dict(repo=r["repo"], drop_reason=r["drop_reason"]) for r in rows if r["dropped"]]

    output = {
        "transformers_version": transformers_version,
        "torch_version": torch_version,
        "cuda_available": cuda_available,
        "n_candidates": len(candidates),
        "rows": rows,
        "families_surviving": families_surviving,
        "n_families_surviving": len(families_surviving),
        "families_with_instruct_abliterated_pair": families_with_pair,
        "n_families_with_pair": len(families_with_pair),
        "sealed_not_touched": sealed_not_touched,
        "dropped": dropped_list,
        "it1_drop_reasons_reproduced": it1_drop_reasons_reproduced,
        "required_model_types": required_model_types,
        "all_required_ok": all_required_ok,
        "transformers_pin_experiment": transformers_pin_experiment,
    }
    if not all_required_ok:
        output["installed_transformers_version_for_bump"] = transformers_version

    out_path = RESULTS / "arch_precheck.json"
    out_path.write_text(json.dumps(output, indent=2, default=str))
    logger.info(f"wrote {out_path}")

    # --- compact pass/fail table ---
    logger.info("---- PASS/FAIL TABLE ----")
    logger.info(f"{'repo':<62} {'model_type':<14} {'import_ok':<10} {'gated':<8} {'safet':<6} {'cached_gb':<10} dropped")
    for r in rows:
        logger.info(
            f"{r['repo']:<62} {str(r['model_type']):<14} {str(r['import_ok']):<10} "
            f"{str(r['gated']):<8} {str(r['has_safetensors']):<6} {str(r['weights_cached_gb']):<10} {r['dropped']}"
        )

    logger.info(
        f"SUMMARY: n_candidates={len(candidates)} all_required_ok={all_required_ok} "
        f"n_families_surviving={len(families_surviving)} n_families_with_pair={len(families_with_pair)} "
        f"n_it1_failures_now_ok={n_it1_failures_now_ok}/{len(it1_drop_reasons_reproduced)}"
    )


if __name__ == "__main__":
    main()
