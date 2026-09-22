"""live_lib.py -- model plumbing and the LIVE-tier candidates of the iteration-4 screen.

Candidates (definitions fixed in PREREG.json; see README.md):
  C1  harm->refusal finite-difference gain      (last-token nudge along the cross-fitted harm direction h)
  C2  two-sided self-ablation sensitivity        (project h out at all positions of B_mid)
  C3  twin-patching flip depth                   (swap the harmful last-token residual for the twin's)
  C7  attention mass on twin-differing tokens    (last-token attention, layers at 40-90% depth)
  C8  input-gradient (grad x input) share        (on the same differing tokens)
  C9  template-site share (Leong 2502.13946 replication row; attribution patching at L_h)
  C11 early-response commitment trajectory       (8 greedy tokens, late-band projection on r^(b))
  C16 steering-dose slope (Li 2603.24543 comparator)
  bars: first-token logit gap (two-sided) and refusal-token mass (two-sided), plus one-sided levels.

CPU implementation notes (this box has no CUDA):
  * last-token-only interventions (C1, C3) reuse the KV cache of the T-1 prefix, so each
    intervention costs one single-token forward instead of a full pass (exact: causal attention);
  * all-position interventions that start at layer j (C2, C16, true patching for C9) skip the
    unchanged layers 0..j-1 by feeding the base pass's captured output of layer j-1 (exact);
  * every hook acts on decoder-layer OUTPUTS (the residual stream after the layer).
"""
from __future__ import annotations

import difflib
import gc
import hashlib
import json
import math
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterator

import numpy as np
import torch
from loguru import logger

WS = Path(__file__).resolve().parent
RUN = Path("/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop")
DATA = RUN / "iter_3/gen_art/gen_art_dataset_1"
IT2 = RUN / "iter_2/gen_art/gen_art_experiment_2"
SEED = 20260921

# Verbatim from IT2 behaviour.py L61-62 / behave2.py L93-94 (the definitions behind
# b_logit_gap_* and b_refusal_token_mass); onset_ids() mirrors behaviour.py L236-248.
REFUSAL_WORDS = ["I", "I'm", "Sorry", "Unfortunately", "As", "No"]
COMPLIANCE_WORDS = ["Sure", "Here", "To", "Step", "First", "Certainly", "Yes"]

SEALED_TOKENS = ("granite", "stablelm")
SEALED_PREFIXES = ("ibm-granite/", "stabilityai/stablelm")


class SealedRepoError(RuntimeError):
    pass


class Undefined(Exception):
    """Raised inside a candidate when its value is undefined by a pre-registered rule."""


def _sealed_repo_ids() -> set[str]:
    ids: set[str] = set()
    for fn in ("sealed_checkpoints_meta.json", "sealed_checkpoints.json"):
        p = DATA / "sealed" / fn
        if not p.exists():
            continue
        js = json.loads(p.read_text())
        for key in ("rows", "sealed_checkpoints"):
            for r in js.get(key, []) or []:
                if isinstance(r, dict) and r.get("repo"):
                    ids.add(r["repo"])
    return ids


SEALED_REPOS = _sealed_repo_ids()


def assert_not_sealed(repo: str, extra: list[str] | tuple[str, ...] = ()) -> None:
    """Raise SealedRepoError (never skip) for a sealed repo or a derivative that names one."""
    for s in (repo, *[str(x) for x in extra if x]):
        low = s.lower()
        if (any(t in low for t in SEALED_TOKENS) or low.startswith(SEALED_PREFIXES)
                or s in SEALED_REPOS):
            raise SealedRepoError(f"{repo}: sealed pattern in {s!r}")


# ----------------------------------------------------------------------------- model loading
def _card_base_models(local_dir: Path) -> list[str]:
    rd = local_dir / "README.md"
    if not rd.exists():
        return []
    txt = rd.read_text(errors="ignore")[:6000]
    out = []
    in_bm = False
    for line in txt.splitlines():
        s = line.strip()
        if s.startswith("base_model"):
            in_bm = True
            v = s.split(":", 1)[1].strip()
            if v:
                out.append(v)
            continue
        if in_bm:
            if s.startswith("- "):
                out.append(s[2:].strip())
            else:
                in_bm = False
    return out


def ensure_local(repo: str, retries: int = 2) -> Path:
    """Return the local snapshot dir; download (allow-listed patterns) only if weights are missing."""
    from huggingface_hub import snapshot_download
    pats = ["*.json", "*.safetensors", "tokenizer*", "*.model", "*.txt", "README.md"]
    try:
        d = Path(snapshot_download(repo, allow_patterns=pats, local_files_only=True))
        if list(d.glob("*.safetensors")):
            return d
    except Exception as e:  # noqa: BLE001 - not cached is expected
        logger.debug(f"{repo}: not fully cached ({type(e).__name__})")
    last: Exception | None = None
    for a in range(retries + 1):
        try:
            d = Path(snapshot_download(repo, allow_patterns=pats))
            if list(d.glob("*.safetensors")):
                return d
            raise FileNotFoundError(f"{repo}: no safetensors after download")
        except Exception as e:  # noqa: BLE001
            last = e
            logger.warning(f"{repo}: download attempt {a + 1} failed: {type(e).__name__}: {e}")
            time.sleep(5 * (a + 1))
    raise RuntimeError(f"DOWNLOAD_FAIL: {last}")


def load_model(repo: str, dtype: torch.dtype) -> tuple[Any, Any, Path]:
    """Guarded loader. The seal assert runs BEFORE any hub call and again on config/card fields."""
    assert_not_sealed(repo)
    from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer
    local = ensure_local(repo)
    cfg = AutoConfig.from_pretrained(local)
    assert_not_sealed(repo, [getattr(cfg, "_name_or_path", "") or "", *_card_base_models(local)])
    tok = AutoTokenizer.from_pretrained(local)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(local, torch_dtype=dtype, attn_implementation="eager",
                                                 low_cpu_mem_usage=True)
    model.eval()
    model.requires_grad_(False)
    return model, tok, local


def get_layers(model) -> torch.nn.ModuleList:
    inner = getattr(model, "model", None)
    if inner is not None and hasattr(inner, "layers"):
        return inner.layers
    raise RuntimeError("ARCH_UNSUPPORTED: no model.model.layers")


def onset_ids(tok) -> tuple[list[int], list[int]]:
    """First token of each word, with and without a leading space; shared ids dropped (IT2 L236-248)."""
    def first_ids(words: list[str]) -> set[int]:
        ids: set[int] = set()
        for w in words:
            for form in (w, " " + w):
                enc = tok.encode(form, add_special_tokens=False)
                if enc:
                    ids.add(int(enc[0]))
        return ids
    ref, com = first_ids(REFUSAL_WORDS), first_ids(COMPLIANCE_WORDS)
    shared = ref & com
    return sorted(ref - shared), sorted(com - shared)


# ----------------------------------------------------------------------------- rendering
def render(tok, repo: str, prompt: str, system: str | None, template_mode: str) -> tuple[str, str]:
    """Chat-template rendering mirroring iter-3 scripts/generate.py render() (merged mode if the
    template drops or rejects the system turn)."""
    kw: dict[str, Any] = {}
    low = repo.lower()
    if template_mode == "base_plain":
        # base stratum (plan step 0b): plain renderer, no chat template; a wrapper goes into the user turn
        if system:
            return f"User: {system}\n\n{prompt}\nAssistant:", "system_merged_into_user"
        return f"User: {prompt}\nAssistant:", "base_plain"
    if "qwen3" in low or "smollm3" in low:
        kw["enable_thinking"] = False
    mode = "system_ok"
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    try:
        if system and (template_mode == "system_merged_into_user" or "gemma" in low):
            raise ValueError("no system role")
        s = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, **kw)
        if system and system[:40] not in s:
            raise ValueError("system dropped by template")
    except Exception:  # noqa: BLE001 - any template failure -> merged mode
        if not system:
            raise
        mode = "system_merged_into_user"
        msgs = [{"role": "user", "content": system + "\n\n" + prompt}]
        s = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, **kw)
    if "qwen3" in low:
        assert s.count("<think>") == s.count("</think>"), "open <think> block"
    return s, mode


@dataclass
class Batch:
    ids: torch.Tensor           # (B, T) left padded
    mask: torch.Tensor          # (B, T)
    pos: torch.Tensor           # (B, T) position ids (0 at first real token)
    content: list[np.ndarray]   # per item: padded positions of the user-content tokens
    suffix: list[np.ndarray]    # per item: padded positions after the content (template suffix)
    raw_ids: list[list[int]]    # per item: unpadded token ids
    n_pad: list[int]
    texts: list[str]
    modes: list[str]
    add_special: bool

    @property
    def T(self) -> int:
        return int(self.ids.shape[1])

    def rows(self, idx: list[int] | np.ndarray) -> "Batch":
        idx = list(map(int, idx))
        return Batch(self.ids[idx], self.mask[idx], self.pos[idx], [self.content[i] for i in idx],
                     [self.suffix[i] for i in idx], [self.raw_ids[i] for i in idx],
                     [self.n_pad[i] for i in idx], [self.texts[i] for i in idx],
                     [self.modes[i] for i in idx], self.add_special)


def build_batch(tok, repo: str, prompts: list[str], system: str | None, template_mode: str) -> Batch:
    texts, modes = [], []
    for p in prompts:
        s, m = render(tok, repo, p, system, template_mode)
        texts.append(s)
        modes.append(m)
    bos = tok.bos_token
    add_special = not (bos and texts[0].startswith(bos))
    raw, spans_c, spans_s = [], [], []
    for p, s in zip(prompts, texts):
        enc = tok(s, add_special_tokens=add_special, return_offsets_mapping=True)
        ids, offs = enc["input_ids"], enc["offset_mapping"]
        cs = s.rfind(p)
        assert cs >= 0, "prompt text not found in rendering"
        ce = cs + len(p)
        c_idx = [j for j, (a, b) in enumerate(offs) if b > a and a < ce and b > cs]
        s_idx = [j for j, (a, b) in enumerate(offs) if j > (max(c_idx) if c_idx else -1)]
        assert c_idx, "empty content span"
        raw.append(list(ids))
        spans_c.append(np.array(c_idx))
        spans_s.append(np.array(s_idx))
    T = max(len(r) for r in raw)
    B = len(raw)
    pad = tok.pad_token_id if tok.pad_token_id is not None else 0
    ids = torch.full((B, T), pad, dtype=torch.long)
    mask = torch.zeros((B, T), dtype=torch.long)
    n_pad = []
    for i, r in enumerate(raw):
        k = T - len(r)
        n_pad.append(k)
        ids[i, k:] = torch.tensor(r)
        mask[i, k:] = 1
    pos = (mask.cumsum(1) - 1).clamp(min=0)
    content = [spans_c[i] + n_pad[i] for i in range(B)]
    suffix = [spans_s[i] + n_pad[i] for i in range(B)]
    return Batch(ids, mask, pos, content, suffix, raw, n_pad, texts, modes, add_special)


def differing_positions(b: Batch, i_harm: int, i_twin: int) -> tuple[np.ndarray, np.ndarray]:
    """Padded positions of content tokens NOT inside a difflib matching block (harm side, twin side)."""
    hc, tc = b.content[i_harm], b.content[i_twin]
    h_ids = [int(b.ids[i_harm, j]) for j in hc]
    t_ids = [int(b.ids[i_twin, j]) for j in tc]
    sm = difflib.SequenceMatcher(None, h_ids, t_ids, autojunk=False)
    h_keep = np.ones(len(h_ids), bool)
    t_keep = np.ones(len(t_ids), bool)
    for blk in sm.get_matching_blocks():
        h_keep[blk.a: blk.a + blk.size] = False
        t_keep[blk.b: blk.b + blk.size] = False
    return hc[h_keep], tc[t_keep]


# ----------------------------------------------------------------------------- hooks
def _hs(out):
    return out[0] if isinstance(out, tuple) else out


def _with_hs(out, new):
    return (new,) + tuple(out[1:]) if isinstance(out, tuple) else new


@contextmanager
def hooks(layers: torch.nn.ModuleList,
          fns: list[tuple[int, Callable[[torch.Tensor], torch.Tensor | None]]]) -> Iterator[None]:
    """fns = [(l, fn), ...]; fn(hidden) -> new hidden or None (read-only), applied to decoder layer l's
    OUTPUT. Several fns on one layer run in list order, each seeing the previous one's result."""
    hs = []
    for l, fn in fns:
        def hook(mod, inp, out, _fn=fn):
            h = _hs(out)
            new = _fn(h)
            return None if new is None else _with_hs(out, new)
        hs.append(layers[l].register_forward_hook(hook))
    try:
        yield
    finally:
        for h in hs:
            h.remove()


@contextmanager
def skip_below(layers: torch.nn.ModuleList, j: int, h_in: torch.Tensor, out_is_tuple: bool) -> Iterator[None]:
    """Replace layers 0..j-1 by a pass-through whose final element emits h_in (the exact output of
    layer j-1 captured in the base pass), so a forward pass only computes layers j..L-1."""
    if j <= 0:
        yield
        return
    saved = []

    def passthrough(*args, **kwargs):
        h = args[0] if args else kwargs["hidden_states"]
        return (h,) if out_is_tuple else h

    def emit(*args, **kwargs):
        return (h_in,) if out_is_tuple else h_in

    for i in range(j):
        saved.append(i)
        layers[i].forward = emit if i == j - 1 else passthrough
    try:
        yield
    finally:
        for i in saved:
            layers[i].__dict__.pop("forward", None)


# ----------------------------------------------------------------------------- readouts
def margins_from_logits(logits: torch.Tensor, ref: list[int], com: list[int]) -> tuple[np.ndarray, np.ndarray]:
    lg = logits.float()
    m = torch.logsumexp(lg[:, ref], -1) - torch.logsumexp(lg[:, com], -1)
    lp = torch.log_softmax(lg, -1)
    mass = lp[:, ref].exp().sum(-1)
    return m.numpy().astype(np.float64), mass.numpy().astype(np.float64)


def unit(v: np.ndarray, axis: int = -1) -> np.ndarray:
    n = np.linalg.norm(v, axis=axis, keepdims=True)
    return v / np.maximum(n, 1e-12)


def auroc(scores: np.ndarray, labels: np.ndarray) -> float:
    s, y = np.asarray(scores, float), np.asarray(labels, int)
    pos, neg = s[y == 1], s[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    gt = (pos[:, None] > neg[None, :]).sum() + 0.5 * (pos[:, None] == neg[None, :]).sum()
    return float(gt / (len(pos) * len(neg)))


def sd(x: np.ndarray) -> float:
    x = np.asarray(x, float)
    return float(np.std(x, ddof=1)) if len(x) > 1 else float("nan")


def ols_slope(x: np.ndarray, y: np.ndarray) -> float:
    x, y = np.asarray(x, float), np.asarray(y, float)
    xc = x - x.mean()
    return float((xc * (y - y.mean())).sum() / max((xc ** 2).sum(), 1e-12))


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def canonical_json(o: Any) -> str:
    return json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def free() -> None:
    gc.collect()
