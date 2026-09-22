"""S8 DETECTION -- two auditor access levels, and the self-reference removed.

Renamed from Tier A/B to BLIND / FAMILY-AWARE to kill the name collision with the
AMS incumbent's own Tier 1 / Tier 2 split.

BLIND AUDITOR  -- has only the downloaded repository and no idea what family it is:
  D1 chat-template content scan
  D2 baked-in system prompt
  D3 key-and-shape check   (milliseconds, no forward pass, no family default)
  D4 the zero-prompt weight screen  (ADOPTED PRIOR ART -- Jorak; see flab.wstats)
FAMILY-AWARE AUDITOR -- may additionally diff against the family default:
  E1 byte diff of the repo's text/config files against the parent
  E2 per-layer spectral energy of dW = W_parent - W_candidate

THE SELF-REFERENCE FIX: D4 is itself one of the ranked candidate metrics, so
every weight rung would be "caught" by construction if the weight screen were
simply assumed. S9 therefore reports undetectable forgery cost TWICE, with and
without D4, and the DIFFERENCE is the headline number.
"""

from __future__ import annotations

import json
import re
import struct
import time
from pathlib import Path

import numpy as np
import torch
from loguru import logger

SENTINEL = "ZQXJWVSENTINEL"

# Role scaffolding that is EXPECTED in any chat template and is therefore whitelisted.
SCAFFOLD_WORDS = {
    "system", "user", "assistant", "tool", "im", "start", "end", "of", "text",
    "bos", "eos", "inst", "s", "b", "human", "ai", "model", "turn", "role",
    "content", "message", "think", "date", "today", "knowledge", "cutoff",
    "cutting", "header", "id", "eot", "sep", "pad", "unk", "begin", "available",
    "tools", "function", "call", "response", "name", "arguments", "json",
}
WORDLIKE = re.compile(r"[A-Za-z]{2,}")


def _read_safetensors_header(p: Path) -> dict:
    """Key -> (dtype, shape) from a .safetensors header, without loading tensors."""
    with open(p, "rb") as fh:
        (n,) = struct.unpack("<Q", fh.read(8))
        hdr = json.loads(fh.read(n).decode("utf-8"))
    return {k: (v["dtype"], tuple(v["shape"])) for k, v in hdr.items() if k != "__metadata__"}


def repo_tensor_index(model_dir: Path) -> dict[str, tuple]:
    """Every tensor key and shape a downloader would receive."""
    out: dict[str, tuple] = {}
    idx = model_dir / "model.safetensors.index.json"
    if idx.exists():
        files = sorted(set(json.loads(idx.read_text())["weight_map"].values()))
    else:
        files = [f.name for f in model_dir.glob("*.safetensors")]
    for f in files:
        p = model_dir / f
        if p.exists():
            out.update(_read_safetensors_header(p))
    return out


# --------------------------------------------------------------------------
# D1 / D2 -- text-side blind screens
# --------------------------------------------------------------------------
def d1_template_content(tok, chat_template: str | None = None) -> dict:
    """D1: how many tokens of NATURAL-LANGUAGE INSTRUCTION does the template inject?

    The template is rendered with a single dummy user turn, the dummy content is
    removed, and every word-like token outside the role-scaffolding whitelist is
    counted. A screen without a false-positive rate is not a screen, so T is
    calibrated on the honest panel in :mod:`flab.panel` and D1's own FPR reported.
    """
    t0 = time.time()
    saved = getattr(tok, "chat_template", None)
    if chat_template is not None:
        tok.chat_template = chat_template
    try:
        try:
            rendered = tok.apply_chat_template(
                [{"role": "user", "content": SENTINEL}],
                tokenize=False, add_generation_prompt=True, enable_thinking=False,
            )
        except (TypeError, ValueError):
            rendered = tok.apply_chat_template(
                [{"role": "user", "content": SENTINEL}],
                tokenize=False, add_generation_prompt=True,
            )
        scaffold = rendered.replace(SENTINEL, " ")
        scaffold = re.sub(r"<\|[^|]*\|>", " ", scaffold)     # strip special markers
        scaffold = re.sub(r"\[/?[A-Z]+\]", " ", scaffold)
        words = [w.lower() for w in WORDLIKE.findall(scaffold)]
        extra = [w for w in words if w not in SCAFFOLD_WORDS]
        return {
            "screen": "D1",
            "n_instruction_words": len(extra),
            "words": extra[:40],
            "seconds": round(time.time() - t0, 4),
            "bytes_read": len(rendered.encode()),
            "gpu_needed": False,
            "parent_needed": False,
        }
    finally:
        if chat_template is not None:
            tok.chat_template = saved


SYSPROMPT_KEYS = re.compile(
    r"default_system(_prompt|_message)?|system_prompt|system_message|default_chat_system", re.I
)


def d2_baked_system(model_dir: Path, chat_template: str | None = None, tok=None) -> dict:
    """D2: a default system message hiding in the configs, or baked into the template.

    The config half is a key scan. The template half is BEHAVIOURAL, not a Jinja
    regex: the template is rendered with a single user turn and no system message,
    and any system turn that still appears is inspected for natural-language
    instruction words. A Jinja regex gets this wrong -- the stock Qwen3 template
    contains the literal string ``'<|im_start|>system\n'`` inside a ``{%- if tools %}``
    branch and guards the user-supplied case with ``messages[0].role == 'system'``
    (dot form, not subscript), so a pattern match on the source flags every honest
    Qwen3 checkpoint. Rendering settles it.
    """
    t0 = time.time()
    hits: list[str] = []
    nbytes = 0
    for fn in ("generation_config.json", "tokenizer_config.json", "config.json"):
        p = model_dir / fn
        if not p.exists():
            continue
        raw = p.read_text(errors="ignore")
        nbytes += len(raw)
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for k, v in (obj.items() if isinstance(obj, dict) else []):
            if SYSPROMPT_KEYS.search(str(k)) and v:
                hits.append(f"{fn}:{k}")

    n_sys_words = 0
    sys_words: list[str] = []
    if tok is not None:
        saved = getattr(tok, "chat_template", None)
        if chat_template is not None:
            tok.chat_template = chat_template
        try:
            try:
                rendered = tok.apply_chat_template(
                    [{"role": "user", "content": SENTINEL}], tokenize=False,
                    add_generation_prompt=True, enable_thinking=False)
            except (TypeError, ValueError):
                rendered = tok.apply_chat_template(
                    [{"role": "user", "content": SENTINEL}], tokenize=False,
                    add_generation_prompt=True)
            nbytes += len(rendered)
            for blk in re.findall(r"<\|im_start\|>system(.*?)(?:<\|im_end\|>|$)",
                                  rendered, re.S):
                words = [w.lower() for w in WORDLIKE.findall(blk)]
                sys_words += [w for w in words if w not in SCAFFOLD_WORDS]
            n_sys_words = len(sys_words)
            if n_sys_words > 0:
                hits.append(f"chat_template:system_turn_with_{n_sys_words}_instruction_words")
        finally:
            if chat_template is not None:
                tok.chat_template = saved

    return {
        "screen": "D2", "flagged": bool(hits), "hits": hits,
        "system_turn_instruction_words": n_sys_words,
        "system_turn_words_sample": sys_words[:20],
        "method": "config key scan + BEHAVIOURAL template render (no Jinja regex)",
        "seconds": round(time.time() - t0, 4), "bytes_read": nbytes,
        "gpu_needed": False, "parent_needed": False,
    }


# --------------------------------------------------------------------------
# D3 -- key-and-shape check
# --------------------------------------------------------------------------
def d3_key_shape(model_dir: Path, observed: dict[str, tuple] | None = None) -> dict:
    """D3: build the declared architecture on the META device and compare keys+shapes.

    Milliseconds, no forward pass, no family default. Catches an explicit bias
    tensor, a leftover adapter tensor, or a wrong shape.
    """
    t0 = time.time()
    from transformers import AutoConfig, AutoModelForCausalLM

    cfg = AutoConfig.from_pretrained(model_dir, trust_remote_code=False)
    with torch.device("meta"):
        ref = AutoModelForCausalLM.from_config(cfg)
    expected = {k: tuple(v.shape) for k, v in ref.state_dict().items()}
    got = observed if observed is not None else repo_tensor_index(Path(model_dir))

    tied = bool(getattr(cfg, "tie_word_embeddings", False))
    exp_keys, got_keys = set(expected), set(got)
    if tied:                      # a tied lm_head is legitimately absent from the files
        exp_keys.discard("lm_head.weight")
        got_keys.discard("lm_head.weight")
    extra = sorted(got_keys - exp_keys)
    missing = sorted(exp_keys - got_keys)
    shape_mismatch = {
        k: {"expected": expected[k], "got": got[k][1] if isinstance(got[k], tuple) and len(got[k]) == 2 else got[k]}
        for k in (exp_keys & got_keys)
        if tuple(got[k][1] if isinstance(got[k], tuple) and len(got[k]) == 2 else got[k]) != tuple(expected[k])
    }
    del ref
    return {
        "screen": "D3",
        "flagged": bool(extra or shape_mismatch),
        "extra_keys": extra[:20],
        "missing_keys": missing[:20],
        "shape_mismatch": {k: v for k, v in list(shape_mismatch.items())[:20]},
        "n_expected": len(exp_keys), "n_got": len(got_keys),
        "seconds": round(time.time() - t0, 4), "bytes_read": 0,
        "gpu_needed": False, "parent_needed": False,
    }


def d3_from_state_dict(cfg, state_keys_shapes: dict[str, tuple]) -> dict:
    """D3 against an in-memory edited model (used for the LoRA-merge assertion)."""
    from transformers import AutoModelForCausalLM

    with torch.device("meta"):
        ref = AutoModelForCausalLM.from_config(cfg)
    expected = {k: tuple(v.shape) for k, v in ref.state_dict().items()}
    tied = bool(getattr(cfg, "tie_word_embeddings", False))
    exp, got = set(expected), set(state_keys_shapes)
    if tied:
        exp.discard("lm_head.weight")
        got.discard("lm_head.weight")
    extra = sorted(got - exp)
    mismatch = {k: (expected[k], state_keys_shapes[k]) for k in (exp & got)
                if tuple(state_keys_shapes[k]) != tuple(expected[k])}
    del ref
    return {"screen": "D3", "flagged": bool(extra or mismatch),
            "extra_keys": extra[:20], "shape_mismatch": {k: str(v) for k, v in list(mismatch.items())[:20]},
            "n_expected": len(exp), "n_got": len(got)}


# --------------------------------------------------------------------------
# D4 -- the zero-prompt weight screen (thresholds come from flab.panel)
# --------------------------------------------------------------------------
def d4_weight_screen(reads: dict, thresholds: dict) -> dict:
    """D4: C4a/C4b/C4c/C4d evaluated at the S4 held-out-family thresholds."""
    t0 = time.time()
    fired: list[str] = []
    detail: dict[str, object] = {}
    for name, key, direction in (
        ("bsa_w8", "bsa_w8_pooled", "high"),
        ("jorak", "jorak_pooled", "high"),
        ("tsa_rankband", "tsa_max_pooled", "high"),
        ("botgap", "botgap_pooled", "low"),
    ):
        v = reads.get(key)
        thr = thresholds.get(name)
        if v is None or thr is None or not np.isfinite(v):
            continue
        hit = (v >= thr) if direction == "high" else (v <= thr)
        detail[name] = {"value": float(v), "threshold": float(thr), "flagged": bool(hit)}
        if hit:
            fired.append(name)
    return {
        "screen": "D4", "flagged": bool(fired), "fired": fired, "detail": detail,
        "seconds": round(time.time() - t0, 4) , "gpu_needed": False, "parent_needed": False,
        "prior_art": "Jorak model-scanner subspace signature (adopted, not invented)",
    }


# --------------------------------------------------------------------------
# E1 / E2 -- the FAMILY-AWARE auditor
# --------------------------------------------------------------------------
TEXT_FILES = ("chat_template.jinja", "tokenizer_config.json", "generation_config.json",
              "config.json", "README.md")


def e1_text_diff(cand_dir: Path, parent_dir: Path, overrides: dict | None = None) -> dict:
    """E1: byte diff of the repo's text files against the family default."""
    t0 = time.time()
    diffs: list[str] = []
    nbytes = 0
    overrides = overrides or {}
    for fn in TEXT_FILES:
        a = (cand_dir / fn).read_bytes() if (cand_dir / fn).exists() else b""
        b = (parent_dir / fn).read_bytes() if (parent_dir / fn).exists() else b""
        if fn in overrides and overrides[fn] is not None:
            a = str(overrides[fn]).encode()
        nbytes += len(a) + len(b)
        if a != b:
            diffs.append(fn)
    return {"screen": "E1", "flagged": bool(diffs), "diff_files": diffs,
            "seconds": round(time.time() - t0, 4), "bytes_read": nbytes,
            "gpu_needed": False, "parent_needed": True}


def e2_delta_spectral(parent_specs: dict, cand_specs: dict) -> dict:
    """E2: per-layer spectral energy of dW -- the PUBLISHED PARENT-DEPENDENT statistic.

    Approximated here from the stored spectra: the relative change in total
    spectral energy per layer. Cited as parent-dependent prior art; it is in the
    FAMILY-AWARE tier precisely because it requires fetching the parent.
    """
    t0 = time.time()
    per_layer: list[float] = []
    for mod in parent_specs:
        if mod not in cand_specs:
            continue
        for p, c in zip(sorted(parent_specs[mod], key=lambda s: s.layer),
                        sorted(cand_specs[mod], key=lambda s: s.layer)):
            denom = p.s_sum or 1.0
            per_layer.append(abs(c.s_sum - p.s_sum) / denom)
    if not per_layer:
        return {"screen": "E2", "flagged": False, "reason": "no matched layers",
                "gpu_needed": False, "parent_needed": True}
    e = float(np.max(per_layer))
    return {"screen": "E2", "flagged": bool(e > 1e-4), "max_rel_energy": e,
            "median_rel_energy": float(np.median(per_layer)),
            "seconds": round(time.time() - t0, 4), "gpu_needed": False,
            "parent_needed": True,
            "note": "parent-dependent statistic; requires knowing AND fetching the family"}
