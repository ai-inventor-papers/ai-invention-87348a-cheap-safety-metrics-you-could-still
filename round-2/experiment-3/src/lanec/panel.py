"""Lane C panel construction — library functions.

Builds the EDITED (abliterated / uncensored / refusal-ablated) vs HONEST (matched, ungated,
non-edited) checkpoint panel used by stage0_panel.py. Metadata and config.json only: no model
weights are ever downloaded here.

`huggingface_hub.HfApi.list_models` dropped the `library=` and `direction=` keyword arguments
in the version installed in this workspace (library filtering now goes through `filter=`, and
descending-by-key is the server default for "downloads"/"likes"/etc). `_list_models_kwargs`
introspects the installed signature so this module keeps working across huggingface_hub versions
without editing call sites.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import re
import threading as _threading
import time
from pathlib import Path
from typing import Any, Callable, Sequence, TypeVar

import requests
from huggingface_hub import HfApi, hf_hub_download
from huggingface_hub.utils import (
    EntryNotFoundError,
    GatedRepoError,
    HfHubHTTPError,
    RepositoryNotFoundError,
    RevisionNotFoundError,
)
from loguru import logger

T = TypeVar("T")

# ---------------------------------------------------------------------------------------
# constants
# ---------------------------------------------------------------------------------------

# (d) tokens that mark a checkpoint as the EDITED (refusal-ablated) arm. Order does not matter;
# the first match found across repo_id / tags / card_text is recorded as the auditable reason.
EDITED_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("abliterated", re.compile(r"abliterat", re.I)),
    ("uncensored", re.compile(r"uncensor", re.I)),
    ("heretic", re.compile(r"heretic", re.I)),
    ("orthogonalized", re.compile(r"orthogonaliz", re.I)),
    ("decensored", re.compile(r"decensor", re.I)),
    ("amoral", re.compile(r"amoral", re.I)),
    ("no-refusal", re.compile(r"no-?refusal", re.I)),
    ("unaligned", re.compile(r"unalign", re.I)),
]

# (b) quantisation markers checked against repo name and sibling filenames, verbatim per spec.
QUANT_RE = re.compile(r"gptq|awq|fp8|int4|int8|bnb|gguf|mlx|onnx", re.I)

# (b) supported dense decoder-only architectures. Kept generous (near-variants included) but
# anything that smells like a mixture-of-experts / hybrid-state-space model is excluded, because
# the config-based dense estimator in `estimate_params` would silently under/over-count for those.
SUPPORTED_ARCH_EXACT = frozenset(
    {
        "Qwen3ForCausalLM",
        "Qwen2ForCausalLM",
        "LlamaForCausalLM",
        "Gemma2ForCausalLM",
        "Gemma3ForCausalLM",
        "Gemma3TextForCausalLM",
        "GemmaForCausalLM",
        "Phi3ForCausalLM",
        "PhiForCausalLM",
        "OlmoForCausalLM",
        "Olmo2ForCausalLM",
        "Olmo3ForCausalLM",
        "FalconForCausalLM",
        "Falcon3ForCausalLM",
        "ExaoneForCausalLM",
        "Exaone4ForCausalLM",
        "StableLmForCausalLM",
    }
)
SUPPORTED_ARCH_PREFIXES = ("Mistral", "SmolLM")
EXCLUDE_ARCH_SUBSTRINGS = ("Moe", "MOE", "Mixture", "Mamba", "Hybrid", "Jamba")

MAX_PARAMS = 4_500_000_000

# card-metadata "base_model:<qualifier>:<repo>" tag qualifiers, best-match first.
_BASE_MODEL_TAG_PRIORITY = {"finetune": 0, "adapter": 1, "merge": 2, "quantized": 3}


# ---------------------------------------------------------------------------------------
# small utilities
# ---------------------------------------------------------------------------------------


def sanitise(repo_id: str) -> str:
    """Filesystem-safe repo id, matching the convention already used by stage1_weights.py."""
    return repo_id.replace("/", "__")


_rate_limit_lock = _threading.Lock()
_rate_limit_until: list[float] = [0.0]  # mutable box shared by every thread in this process


def _respect_global_cooldown() -> None:
    """Block until any HF-Hub-wide 429 cooldown registered by ANY worker thread has elapsed.
    HF's API quota (requests per rolling window) is shared across all 8 worker threads, so a
    single thread's exponential backoff is not enough — every thread must pause together or they
    just re-trigger the same 429."""
    with _rate_limit_lock:
        until = _rate_limit_until[0]
    remaining = until - time.time()
    if remaining > 0:
        time.sleep(remaining)


def _register_rate_limit(retry_after: float) -> None:
    with _rate_limit_lock:
        _rate_limit_until[0] = max(_rate_limit_until[0], time.time() + retry_after)


def _retry_after_seconds(exc: Exception) -> float | None:
    response = getattr(exc, "response", None)
    header = getattr(response, "headers", None)
    if not header:
        return None
    raw = header.get("Retry-After") or header.get("retry-after")
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _with_retries(fn: Callable[[], T], *, retries: int = 5, base_delay: float = 1.5,
                   what: str = "") -> T:
    """Retry transient HTTP/network errors. A 429 sleeps for the server's `Retry-After` (falling
    back to 5s, HF's documented window) and registers a PROCESS-WIDE cooldown so every other
    worker thread also pauses; any other transient error uses per-call exponential backoff.
    Permanent errors (gated/not-found/revision/entry) are never retried — they will not succeed on
    attempt 2."""
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        _respect_global_cooldown()
        try:
            return fn()
        except (GatedRepoError, RepositoryNotFoundError, RevisionNotFoundError,
                EntryNotFoundError):
            raise
        except (HfHubHTTPError, requests.exceptions.RequestException) as exc:
            last_exc = exc
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status == 429:
                delay = _retry_after_seconds(exc) or 5.0
                _register_rate_limit(delay)
            else:
                delay = base_delay * (2 ** (attempt - 1))
            if attempt < retries:
                logger.debug(f"retry {attempt}/{retries} for {what}: "
                             f"{type(exc).__name__} (status={status}); sleeping {delay:.1f}s")
                time.sleep(delay)
    assert last_exc is not None
    raise last_exc


def _list_models_kwargs(api: HfApi, *, search: str, limit: int,
                         library: str = "transformers", sort: str = "downloads") -> dict[str, Any]:
    """Build kwargs for HfApi.list_models compatible with whichever signature is installed."""
    params = inspect.signature(api.list_models).parameters
    kwargs: dict[str, Any] = {"search": search, "sort": sort, "limit": limit}
    if "library" in params:
        kwargs["library"] = library
    elif "filter" in params:
        kwargs["filter"] = library
    if "direction" in params:
        kwargs["direction"] = -1
    return kwargs


def _safetensors_summary(siblings: Sequence[Any]) -> dict[str, Any]:
    files = [
        {"name": s.rfilename, "size_bytes": int(s.size)}
        for s in siblings
        if s.rfilename.lower().endswith(".safetensors") and s.size is not None
    ]
    files.sort(key=lambda f: f["name"])
    return {
        "total_safetensors_bytes": sum(f["size_bytes"] for f in files),
        "n_safetensors_files": len(files),
        "safetensors_files": files,
    }


# ---------------------------------------------------------------------------------------
# (a) harvest
# ---------------------------------------------------------------------------------------


def harvest_candidates(queries: Sequence[str], limit_per_query: int, *, token: str | None = None,
                        timeout: float = 30.0) -> list[dict[str, Any]]:
    """Search-harvest candidate repo ids across `queries`, deduplicated by repo id.

    Uses HfApi.list_models(search=q, library="transformers", sort="downloads", direction=-1,
    limit=limit_per_query) for each q — see module docstring for the compat shim. Returns light
    records (repo_id + the query/downloads that surfaced it); full verification happens in
    `screen`.
    """
    api = HfApi(token=token)
    seen: dict[str, dict[str, Any]] = {}
    for q in queries:
        kwargs = _list_models_kwargs(api, search=q, limit=limit_per_query)
        try:
            results = _with_retries(lambda kw=kwargs: list(api.list_models(**kw)), retries=5,
                                     what=f"list_models(search={q!r})")
        except (HfHubHTTPError, requests.exceptions.RequestException) as exc:
            logger.warning(f"harvest query {q!r} failed: {type(exc).__name__}: {exc}")
            continue
        n_new = 0
        for m in results:
            if m.id not in seen:
                seen[m.id] = {
                    "repo_id": m.id,
                    "downloads": m.downloads,
                    "source_query": q,
                    "gated_hint": m.gated,
                }
                n_new += 1
        logger.info(f"harvest query={q!r} -> {len(results)} hits, {n_new} new "
                    f"({len(seen)} unique so far)")
    return list(seen.values())


# ---------------------------------------------------------------------------------------
# (c) family signature + base_model extraction
# ---------------------------------------------------------------------------------------


def family_signature(config: dict[str, Any]) -> str:
    """The held-out fold unit: f"{architectures[0]}|h{hidden_size}|L{num_hidden_layers}".
    Repo names lie about family membership; this signature is derived from config.json only."""
    architectures = config.get("architectures") or [None]
    arch = architectures[0]
    return f"{arch}|h{config.get('hidden_size')}|L{config.get('num_hidden_layers')}"


def extract_base_model(card_data: Any, tags: Sequence[str]) -> str | None:
    """Best-effort base_model id from card metadata (cardData.base_model), falling back to a
    `base_model:...` hub tag when the card itself does not carry the field."""
    bm = getattr(card_data, "base_model", None) if card_data is not None else None
    if isinstance(bm, list) and bm:
        return str(bm[0])
    if isinstance(bm, str) and bm:
        return bm

    candidates: list[tuple[int, str]] = []
    for tag in tags:
        if not tag.startswith("base_model:"):
            continue
        rest = tag[len("base_model:"):]
        head, _, tail = rest.partition(":")
        if tail and head in _BASE_MODEL_TAG_PRIORITY:
            candidates.append((_BASE_MODEL_TAG_PRIORITY[head], tail))
        else:
            candidates.append((4, rest))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]


# ---------------------------------------------------------------------------------------
# (b) param estimator + architecture gate
# ---------------------------------------------------------------------------------------


def is_supported_architecture(arch: str | None) -> bool:
    if not arch:
        return False
    if any(bad in arch for bad in EXCLUDE_ARCH_SUBSTRINGS):
        return False
    if arch in SUPPORTED_ARCH_EXACT:
        return True
    return arch.startswith(SUPPORTED_ARCH_PREFIXES)


def estimate_params(config: dict[str, Any]) -> int:
    """Dense decoder-only parameter estimator from config.json alone (never from repo names or
    the HF `usedStorage` field, which is known to lie).

    Standard LLaMA-family block: grouped-query attention (q/k/v/o) + gated SwiGLU MLP
    (gate/up/down) + 2 RMSNorm vectors per layer, tied or untied input/output embeddings.
    Raises ValueError if a required config field is absent.
    """
    required = ["hidden_size", "num_hidden_layers", "intermediate_size", "vocab_size"]
    missing = [k for k in required if config.get(k) is None]
    if missing:
        raise ValueError(f"missing config fields: {missing}")

    h = int(config["hidden_size"])
    n_layers = int(config["num_hidden_layers"])
    inter = int(config["intermediate_size"])
    vocab = int(config["vocab_size"])

    n_heads = int(config.get("num_attention_heads") or 0)
    head_dim_cfg = config.get("head_dim")
    if n_heads <= 0 and not head_dim_cfg:
        raise ValueError("missing config fields: ['num_attention_heads' or 'head_dim']")
    head_dim = int(head_dim_cfg) if head_dim_cfg else h // n_heads
    if n_heads <= 0:
        n_heads = max(1, h // head_dim)
    n_kv_heads = int(config.get("num_key_value_heads") or n_heads)
    tie = bool(config.get("tie_word_embeddings", False))

    q_out, kv_out = n_heads * head_dim, n_kv_heads * head_dim
    attn_params = h * q_out + 2 * h * kv_out + q_out * h
    mlp_params = 3 * h * inter  # gate_proj + up_proj + down_proj (SwiGLU-style)
    norm_params = 2 * h  # input_layernorm + post_attention_layernorm
    per_layer = attn_params + mlp_params + norm_params

    embed_params = vocab * h
    total = embed_params + n_layers * per_layer + h  # + final norm
    if not tie:
        total += embed_params  # untied lm_head
    return int(total)


# ---------------------------------------------------------------------------------------
# (d) arm labelling
# ---------------------------------------------------------------------------------------


def label_arm(repo_id: str, tags: Sequence[str], card_text: str) -> tuple[str, str | None]:
    """"edited" if repo_id / tags / card_text match an edited-arm token, else "honest".
    Returns (arm, matched_token) so the label is auditable; matched_token is
    "<token>@<field>" for the edited arm and None for the honest arm."""
    haystacks = (
        ("repo_id", repo_id),
        ("tags", " ".join(tags)),
        ("card_text", (card_text or "")[:20_000]),
    )
    for field_name, text in haystacks:
        for token_name, pattern in EDITED_PATTERNS:
            if pattern.search(text):
                return "edited", f"{token_name}@{field_name}"
    return "honest", None


# ---------------------------------------------------------------------------------------
# (f) safetensors sizing
# ---------------------------------------------------------------------------------------


def total_safetensors_bytes(repo_id: str, *, token: str | None = None,
                             timeout: float = 30.0) -> dict[str, Any]:
    """Exact on-disk safetensors byte total + per-file name/size, for ranged-read sizing later.
    One `model_info(files_metadata=True)` call; no weights are downloaded."""
    api = HfApi(token=token)
    info = _with_retries(lambda: api.model_info(repo_id, files_metadata=True, timeout=timeout),
                          retries=5, what=f"model_info({repo_id})")
    return _safetensors_summary(info.siblings or [])


# ---------------------------------------------------------------------------------------
# (b) screen — the KEEP/REJECT gate
# ---------------------------------------------------------------------------------------


def screen(repo_id: str, *, token: str | None = None, timeout: float = 30.0) -> dict[str, Any]:
    """Verify one repo. Returns a dict with `keep: bool` and, when keep is False, `reason: str`.
    Every field that was reachable before the rejecting check is still populated, so a dropped
    candidate's record remains informative."""
    result: dict[str, Any] = {"repo_id": repo_id, "keep": False, "reason": None}
    api = HfApi(token=token)

    try:
        info = _with_retries(lambda: api.model_info(repo_id, files_metadata=True, timeout=timeout),
                              retries=5, what=f"model_info({repo_id})")
    except RepositoryNotFoundError as exc:
        result["reason"] = f"repo_not_found:{exc}"
        return result
    except GatedRepoError as exc:
        result["reason"] = f"gated_no_access:{exc}"
        return result
    except (HfHubHTTPError, requests.exceptions.RequestException) as exc:
        result["reason"] = f"model_info_error:{type(exc).__name__}:{exc}"
        return result

    tags = list(info.tags or [])
    gated = info.gated
    result.update({"tags": tags, "downloads": info.downloads, "likes": info.likes, "gated": gated})

    siblings = info.siblings or []
    result.update(_safetensors_summary(siblings))
    if result["n_safetensors_files"] == 0:
        result["reason"] = "no safetensors"
        return result

    if gated not in (False, "auto"):
        result["reason"] = f"gated:{gated!r}"
        return result

    filenames_joined = " ".join(s.rfilename for s in siblings)
    if QUANT_RE.search(repo_id) or QUANT_RE.search(filenames_joined):
        result["reason"] = "quantised"
        return result

    try:
        cfg_path = _with_retries(
            lambda: hf_hub_download(repo_id, filename="config.json", token=token,
                                     etag_timeout=timeout),
            retries=5, what=f"config.json({repo_id})",
        )
        config = json.loads(Path(cfg_path).read_text())
    except (GatedRepoError, RepositoryNotFoundError, EntryNotFoundError,
            RevisionNotFoundError) as exc:
        # e.g. huihui-ai/Qwen3-4B-abliterated: gated="auto" at the model_info level but the
        # actual file fetch 403s. Record it, do not crash.
        result["reason"] = f"config_fetch_gated_or_missing:{type(exc).__name__}"
        return result
    except (HfHubHTTPError, requests.exceptions.RequestException, json.JSONDecodeError,
            OSError) as exc:
        result["reason"] = f"config_fetch_error:{type(exc).__name__}:{exc}"
        return result

    if config.get("quantization_config") is not None:
        result["reason"] = "quantised"
        return result

    architectures = config.get("architectures") or []
    arch = architectures[0] if architectures else None
    result["architecture"] = arch
    if not is_supported_architecture(arch):
        result["reason"] = f"unsupported_architecture:{arch}"
        return result

    try:
        n_params_est = estimate_params(config)
    except ValueError as exc:
        result["reason"] = f"estimator_missing_fields:{exc}"
        return result

    result.update(
        {
            "n_params_est": n_params_est,
            "n_layers": config.get("num_hidden_layers"),
            "hidden_size": config.get("hidden_size"),
            "intermediate_size": config.get("intermediate_size"),
            "vocab_size": config.get("vocab_size"),
            "family_signature": family_signature(config),
        }
    )
    if n_params_est >= MAX_PARAMS:
        result["reason"] = f"too_large_est:{n_params_est}"
        return result

    card_text = ""
    try:
        readme_path = _with_retries(
            lambda: hf_hub_download(repo_id, filename="README.md", token=token,
                                     etag_timeout=timeout),
            retries=5, what=f"README.md({repo_id})",
        )
        card_text = Path(readme_path).read_text(errors="replace")
    except (EntryNotFoundError, RepositoryNotFoundError, RevisionNotFoundError):
        card_text = ""  # no README, not fatal
    except (GatedRepoError, HfHubHTTPError, requests.exceptions.RequestException, OSError) as exc:
        logger.debug(f"{repo_id}: README fetch failed, continuing without card text: "
                     f"{type(exc).__name__}: {exc}")
        card_text = ""

    result["card_text"] = card_text
    result["card_text_sha256"] = hashlib.sha256(card_text.encode("utf-8")).hexdigest()
    result["base_model"] = extract_base_model(info.card_data, tags)

    result["keep"] = True
    result["reason"] = None
    return result


# ---------------------------------------------------------------------------------------
# (e) matched honest arm
# ---------------------------------------------------------------------------------------


def matched_honest(edited_family_bases: dict[str, list[str]], excluded_repo_ids: set[str], *,
                    token: str | None = None, timeout: float = 30.0, per_family_target: int = 3,
                    search_limit: int = 25) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    """For each family signature present in the edited arm, find 1-3 ungated non-edited
    checkpoints with the SAME family_signature. Declared base_model repos (from the edited arm's
    own card metadata) are tried first, then a hub search on the architecture family name,
    preferring repo ids that look like an instruct/chat checkpoint.

    Returns (signature -> list of kept "honest" screen() records, list of dropped candidates).
    """
    api = HfApi(token=token)
    found_by_sig: dict[str, list[dict[str, Any]]] = {}
    dropped: list[dict[str, Any]] = []

    for sig, base_repo_ids in edited_family_bases.items():
        arch = sig.split("|", 1)[0] or ""
        keyword = re.sub(r"ForCausalLM$", "", arch) or arch
        seen_ids: set[str] = set()
        candidate_repo_ids: list[str] = []

        for rid in base_repo_ids:
            if rid and rid not in seen_ids:
                candidate_repo_ids.append(rid)
                seen_ids.add(rid)

        for term in (f"{keyword} Instruct", keyword):
            kwargs = _list_models_kwargs(api, search=term, limit=search_limit)
            try:
                results = _with_retries(lambda kw=kwargs: list(api.list_models(**kw)), retries=5,
                                         what=f"list_models(search={term!r})")
            except (HfHubHTTPError, requests.exceptions.RequestException) as exc:
                logger.warning(f"matched_honest search {term!r} failed for {sig}: "
                                f"{type(exc).__name__}: {exc}")
                continue
            for m in results:
                if m.id not in seen_ids:
                    candidate_repo_ids.append(m.id)
                    seen_ids.add(m.id)

        candidate_repo_ids.sort(key=lambda rid: 0 if re.search(r"instruct|chat", rid, re.I) else 1)

        kept: list[dict[str, Any]] = []
        for rid in candidate_repo_ids:
            if len(kept) >= per_family_target:
                break
            if rid in excluded_repo_ids:
                continue
            verdict = screen(rid, token=token, timeout=timeout)
            if not verdict["keep"]:
                dropped.append(verdict)
                continue
            if verdict.get("family_signature") != sig:
                mismatch = dict(verdict)
                mismatch["keep"] = False
                mismatch["reason"] = f"signature_mismatch:{verdict.get('family_signature')}"
                dropped.append(mismatch)
                continue
            arm, matched_token = label_arm(rid, verdict.get("tags", []), verdict.get("card_text", ""))
            if arm != "honest":
                relabelled = dict(verdict)
                relabelled["keep"] = False
                relabelled["reason"] = f"labelled_edited:{matched_token}"
                dropped.append(relabelled)
                continue
            verdict["arm"] = "honest"
            verdict["matched_token"] = None
            kept.append(verdict)

        found_by_sig[sig] = kept
        logger.info(f"matched_honest sig={sig!r} keyword={keyword!r} -> "
                    f"{len(kept)}/{per_family_target} kept from {len(candidate_repo_ids)} candidates")

    return found_by_sig, dropped
