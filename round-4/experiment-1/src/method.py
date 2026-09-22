#!/usr/bin/env python3
"""method.py (== the plan's live_screen.py): LIVE-tier per-checkpoint measurement, one process, resumable.

For every non-sealed checkpoint of the CPU sub-panel it measures, on the 16 frozen SCREEN16 prompts only,
the causal / routing candidates C1, C2, C3, C7, C8, C9, C11, C16 and the two logit-only bars (first-token
logit gap, refusal-token mass) under three presentations (plain, always-refuse wrapper, never-refuse
wrapper), with direction nulls, k=8 variants, oracle-readout rows (judged refusal of the model's own
64-token greedy replies) and, on 6 models, a constant-offset control.  One JSON row per model is written
atomically to rows/<slug>.json the moment the model finishes.  See PREREG.json for every fixed choice.

Usage:  venv_live/bin/python method.py [--repos a,b,...] [--smoke] [--max-models N]
"""
from __future__ import annotations

import os
import sys


def _cgroup_cpu_quota() -> float | None:
    """cgroup CPU quota in whole cpus (v2 cpu.max, else v1 cfs_quota/cfs_period); None if unlimited/unreadable.
    GPU-port fix: os.sched_getaffinity(0) reports the host's cores (128 here), not this container's
    cgroup quota (15.3 here), so using it alone thrashes BLAS/torch CPU-side work even on the GPU box."""
    try:
        p2 = "/sys/fs/cgroup/cpu.max"
        if os.path.exists(p2):
            parts = open(p2).read().split()
            if parts[0] == "max":
                return None
            return int(parts[0]) / int(parts[1])
        q, pd = "/sys/fs/cgroup/cpu/cpu.cfs_quota_us", "/sys/fs/cgroup/cpu/cpu.cfs_period_us"
        if os.path.exists(q) and os.path.exists(pd):
            quota, period = int(open(q).read().strip()), int(open(pd).read().strip())
            if quota > 0 and period > 0:
                return quota / period
        return None
    except (OSError, ValueError, IndexError):
        return None


_AFFINITY = len(os.sched_getaffinity(0))
_QUOTA = _cgroup_cpu_quota()
_NT_INT = max(1, min(_AFFINITY, int(_QUOTA))) if _QUOTA else _AFFINITY
_NT = str(_NT_INT)
for _k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ[_k] = _NT
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
# GPU-port fix: torch 2.14 routes some ops (e.g. RoPE's inv_freq @ position_ids outer product) through
# a Triton "native DSL" kernel that JIT-compiles a small .so via gcc; this box has no C compiler wired
# up for that path. Disabling it falls back to the standard ATen CUDA kernels (numerically identical).
os.environ.setdefault("TORCH_DISABLE_NATIVE_JIT", "1")

import argparse  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import resource  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402
import traceback  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Any  # noqa: E402

import numpy as np  # noqa: E402
import torch  # noqa: E402
import transformers  # noqa: E402
from loguru import logger  # noqa: E402

torch.set_num_threads(int(_NT))

from live_lib import (DATA, DEVICE, SEED, Batch, SealedRepoError, auroc, build_batch, differing_positions,  # noqa: E402
                      get_layers, hooks, load_model, ols_slope, onset_ids, sd, skip_below, unit)

WS = Path(__file__).resolve().parent
ROWS = WS / "rows"
LOGS = WS / "logs"
ROWS.mkdir(exist_ok=True)
LOGS.mkdir(exist_ok=True)

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(LOGS / "method.log", rotation="30 MB", level="DEBUG")

# ----------------------------------------------------------------------------- PREREG gate
PREREG_TXT = (WS / "PREREG.json").read_text()
PREREG_HASH = hashlib.sha256(PREREG_TXT.encode()).hexdigest()
_hash_file = (WS / "PREREG_hash.txt").read_text().split()[0]
assert _hash_file == PREREG_HASH, "PREREG.json does not match PREREG_hash.txt -- refusing to score"
PREREG = json.loads(PREREG_TXT)
S16_INFO = json.loads((WS / "screen16_ids.json").read_text())
LABELS = json.loads((WS / "labels_map.json").read_text())["rows"]
POLES = json.loads((DATA / "poles.json").read_text())
PANEL = {r["repo"]: r for r in json.loads((DATA / "panel.json").read_text())["rows"]}

EPS_GRID = [0.02, 0.05, 0.10]
EPS0 = 0.05
# GPU-port PREREG branch: CPU keeps the current (n_cpu == 'used') values; CUDA uses the pre-registered
# n_gpu random directions and runs every C16 variant at the full alpha grid, not the CPU budget cut.
N_RAND = int(PREREG["random_directions"]["n_gpu"]) if DEVICE.type == "cuda" else int(PREREG["random_directions"]["used"])
N_SUB = int(PREREG["random_subsets_C7_C8"])
ALPHAS = [-2.0, -1.0, 0.0, 1.0, 2.0]
ALPHAS_VAR = ALPHAS if DEVICE.type == "cuda" else [-2.0, 0.0, 2.0]
VRAM_CAP_PLAN_GB = 9.3  # plan's hard cap; applied via torch.cuda.set_per_process_memory_fraction() in main()
# OOM retry only (DEVIATIONS VRAM_CAP_RAISED_OOM_RETRY): LIVE_VRAM_CAP_GB raises the cap for a named re-run, so the
# 16-item batches stay identical to every other model; the row records the cap and a VRAM_CAP_RAISED flag
VRAM_CAP_GB = float(os.environ.get("LIVE_VRAM_CAP_GB", VRAM_CAP_PLAN_GB))
SOFT_CAP = float(PREREG["time_caps"]["soft_s"])
HARD_CAP = float(PREREG["time_caps"]["hard_s"])
CAP_OVERRIDE: dict | None = None  # set by --soft-cap/--hard-cap (anchor runs); recorded in every row's flags
SD_FLOOR = 0.25
INFORMATIVE = 0.25
# the plan's offset-control set is Qwen3-4B + the 5 models below. Session 1 substituted Qwen3-0.6B because Qwen3-4B was
# outside CPU_SUBPANEL; session 3 measures the anchors in full mode, so Qwen3-4B is added back (OFFSET_CONTROL_SET deviation).
OFFSET_MODELS = ["Qwen/Qwen3-0.6B", "Qwen/Qwen2.5-1.5B-Instruct", "unsloth/Llama-3.2-1B-Instruct",
                 "TinyLlama/TinyLlama-1.1B-Chat-v1.0", "allenai/OLMo-2-0425-1B-Instruct",
                 "HuggingFaceTB/SmolLM2-360M-Instruct", "Qwen/Qwen3-4B"]
ATP_VALIDATION_MODELS = ["Qwen/Qwen2.5-0.5B-Instruct", "Qwen/Qwen2.5-1.5B-Instruct", "unsloth/Llama-3.2-1B-Instruct"]

# ----------------------------------------------------------------------------- SCREEN16 layout
_S16 = [json.loads(l) for l in (DATA / "screen16.jsonl").read_text().splitlines() if l.strip()]
assert hashlib.sha256((DATA / "screen16.jsonl").read_bytes()).hexdigest() == S16_INFO["file_sha256"]
PAIR_IDS: list[str] = []
for _r in _S16:
    if _r["pair_id"] not in PAIR_IDS:
        PAIR_IDS.append(_r["pair_id"])
ITEMS: list[dict] = []
for _p in PAIR_IDS:
    ITEMS.append(next(r for r in _S16 if r["pair_id"] == _p and r["side"] == "harmful"))
    ITEMS.append(next(r for r in _S16 if r["pair_id"] == _p and r["side"] == "benign_twin"))
PROMPTS = [r["prompt"] for r in ITEMS]
ALLOWED_PROMPTS = frozenset(PROMPTS)
NP = len(PAIR_IDS)
IS_HARM = np.array([r["side"] == "harmful" for r in ITEMS])
HARM_IDX = np.arange(0, 2 * NP, 2)
TWIN_IDX = HARM_IDX + 1
K8_PAIR_NAMES = ["S16_xs0", "S16_xs1", "S16_jbb0", "S16_jbb1"]
K8_PAIRS = [PAIR_IDS.index(x) for x in K8_PAIR_NAMES]
K8_ITEMS = np.array(sorted([2 * p for p in K8_PAIRS] + [2 * p + 1 for p in K8_PAIRS]))
_perm8 = np.random.default_rng(SEED).permutation(NP)
FOLDS = [list(map(int, _perm8[2 * k: 2 * k + 2])) for k in range(4)]
_perm4 = np.random.default_rng(SEED).permutation(4)
K8_FOLDS = [[K8_PAIRS[i] for i in _perm4[0:2]], [K8_PAIRS[i] for i in _perm4[2:4]]]


def items_of(pairs: list[int]) -> list[int]:
    return sorted([2 * p for p in pairs] + [2 * p + 1 for p in pairs])


def slug(repo: str) -> str:
    return repo.replace("/", "__")


def clean(o: Any) -> Any:
    """Recursively convert numpy/torch objects to JSON types; non-finite floats -> None; keys -> str."""
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(x) for x in o]
    if isinstance(o, np.ndarray):
        return clean(o.tolist())
    if isinstance(o, torch.Tensor):
        return clean(o.detach().cpu().tolist())
    if isinstance(o, (bool, np.bool_)):
        return bool(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        v = float(o)
        return v if math.isfinite(v) else None
    return o


def atomic_write(p: Path, obj: Any) -> None:
    tmp = p.with_suffix(p.suffix + f".tmp{os.getpid()}")
    tmp.write_text(json.dumps(clean(obj), indent=1))
    tmp.replace(p)


def fnum(x: Any) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def cand(value: float | None, reason: str | None = None, **extra: Any) -> dict:
    v = fnum(value)
    und = v is None
    return {"value": v, "undefined": und, "reason": (reason or ("non-finite" if und else None)), **extra}


# ----------------------------------------------------------------------------- direction fitting (numpy)
def cf_harm_dirs(R: np.ndarray, pairs: list[int], folds: list[list[int]]) -> np.ndarray:
    """Cross-fitted harm directions. R (16, nL, d). Item i of a pair in fold k gets unit(mean harm - mean twin)
    over the OTHER folds' pairs (restricted to `pairs`). Items outside `pairs` get zeros."""
    D = np.zeros_like(R)
    for fold in folds:
        fold = [p for p in fold if p in pairs]
        train = [p for p in pairs if p not in fold]
        if not fold or not train:
            continue
        h = R[[2 * p for p in train]].mean(0) - R[[2 * p + 1 for p in train]].mean(0)
        h = unit(h)
        for p in fold:
            D[2 * p] = h
            D[2 * p + 1] = h
    return D


def cf_rank_dirs(R: np.ndarray, score: np.ndarray, pairs: list[int], folds: list[list[int]],
                 binary: bool = False) -> tuple[np.ndarray, list[bool]]:
    """Cross-fitted readout direction: training items split by `score` (top half vs bottom half, or
    score==1 vs score==0 when binary). Returns (D, defined-per-fold)."""
    D = np.zeros_like(R)
    ok = []
    for fold in folds:
        fold = [p for p in fold if p in pairs]
        train = [p for p in pairs if p not in fold]
        tr = items_of(train)
        if binary:
            hi = [i for i in tr if score[i] == 1]
            lo = [i for i in tr if score[i] == 0]
        else:
            order = sorted(tr, key=lambda i: score[i])
            half = len(order) // 2
            lo, hi = order[:half], order[len(order) - half:]
        good = len(hi) >= 1 and len(lo) >= 1 and bool(fold)
        ok.append(good)
        if not good:
            continue
        r = unit(R[hi].mean(0) - R[lo].mean(0))
        for i in items_of(fold):
            D[i] = r
    return D, ok


def aniso_random_dirs(A: np.ndarray, h: np.ndarray, n: int, rng: np.random.Generator,
                      tries: int = 2000) -> tuple[np.ndarray, dict]:
    """Anisotropy-matched random directions v = A^T g (normalised), accepted when var(Av) is within
    +/-25% of var(Ah); if fewer than n accepted in `tries`, fill with the closest by |ratio-1|."""
    A = A - A.mean(0, keepdims=True)
    tgt = float(np.mean((A @ h) ** 2))
    G = rng.standard_normal((tries, A.shape[0])).astype(np.float32)
    V = G @ A
    V /= np.maximum(np.linalg.norm(V, axis=1, keepdims=True), 1e-12)
    ratio = np.mean((A @ V.T) ** 2, axis=0) / max(tgt, 1e-12)
    acc = np.where(np.abs(ratio - 1) <= 0.25)[0]
    pick = list(acc[:n])
    if len(pick) < n:
        rest = [i for i in np.argsort(np.abs(ratio - 1)) if i not in set(pick)]
        pick += rest[: n - len(pick)]
    info = {"n_accepted_in_tries": int(len(acc)), "tries": tries, "fallback_closest": bool(len(acc) < n),
            "ratio_picked": [float(ratio[i]) for i in pick], "var_h": tgt}
    return V[pick].astype(np.float32), info


def massive_filter(H: np.ndarray) -> np.ndarray:
    """Token rows of H (N, d) whose norm is <= 10x the median row norm (drops attention-sink rows)."""
    nr = np.linalg.norm(H, axis=1)
    return H[nr <= 10 * np.median(nr)]


# ----------------------------------------------------------------------------- per-model runner
class JudgeThread(threading.Thread):
    def __init__(self, pairs: list[tuple[str, str]]) -> None:
        super().__init__(daemon=True)
        self.pairs, self.result, self.error, self.summary = pairs, None, None, None

    def run(self) -> None:
        try:
            from judge_lib import Judge
            j = Judge(arm="oracle")
            self.result = j.grade_sync(self.pairs)
            self.summary = j.summary()
        except Exception as e:  # noqa: BLE001 - recorded, never silent
            self.error = f"{type(e).__name__}: {e}"
            logger.error(f"oracle judge failed: {self.error}")


class TimeCap(Exception):
    pass


class ModelRun:
    def __init__(self, repo: str, smoke: bool = False) -> None:
        self.repo = repo
        self.smoke = smoke
        self.t0 = time.time()
        self.timing: dict[str, float] = {}
        self.cand_seconds: dict[str, float] = {}
        self.flags: list[dict] = []
        pr = PANEL.get(repo, {})
        lab = LABELS.get(repo, {})
        self.meta = {"repo": repo, "resolved_sha": pr.get("resolved_sha"), "family": pr.get("family"),
                     "lineage": pr.get("lineage"), "class": pr.get("class"), "n_params": pr.get("n_params"),
                     "stratum": pr.get("stratum"),
                     # base stratum: plain 'User: ...\nAssistant:' renderer (no chat template), per the plan
                     "template_mode_panel": ("base_plain" if pr.get("stratum") == "base"
                                             else pr.get("template_mode", "system_ok")),
                     "graded": lab.get("BALANCED") is not None, "BALANCED": lab.get("BALANCED"),
                     "PRODUCT": lab.get("PRODUCT")}

    # -- time helpers
    def elapsed(self) -> float:
        return time.time() - self.t_load_end if hasattr(self, "t_load_end") else 0.0

    def check_hard(self) -> None:
        if self.elapsed() > HARD_CAP:
            raise TimeoutError(f"TIMEOUT after {self.elapsed():.0f}s (hard cap {HARD_CAP}s)")

    def soft_ok(self, block: str) -> bool:
        self.check_hard()
        if self.elapsed() > SOFT_CAP:
            self.flags.append({"code": "TIME_CAP", "block": block, "elapsed_s": round(self.elapsed(), 1)})
            logger.warning(f"{self.repo}: soft cap reached, skipping block {block}")
            return False
        return True

    def tic(self) -> float:
        if DEVICE.type == "cuda":
            torch.cuda.synchronize()
        return time.perf_counter()

    def toc(self, key: str, t: float, cand_keys: tuple[str, ...] = ()) -> None:
        if DEVICE.type == "cuda":
            torch.cuda.synchronize()
        dt = time.perf_counter() - t
        logger.info(f"  {self.repo.split('/')[-1][:28]} block {key}: {dt:.1f}s (elapsed {self.elapsed():.0f}s)")
        self.timing[key] = self.timing.get(key, 0.0) + dt
        for c in cand_keys:
            self.cand_seconds[c] = self.cand_seconds.get(c, 0.0) + dt / max(len(cand_keys), 1)

    # -- model
    def load(self) -> None:
        t = time.time()
        if DEVICE.type == "cuda":
            torch.cuda.reset_peak_memory_stats()
        self.model, self.tok, self.local = load_model(self.repo, torch.bfloat16)
        if getattr(self.tok, "_aii_tokenizer_source", None):
            self.flags.append(dict(self.tok._aii_tokenizer_source))
        if DEVICE.type == "cuda" and VRAM_CAP_GB != VRAM_CAP_PLAN_GB:
            self.flags.append({"code": "VRAM_CAP_RAISED", "cap_gb": VRAM_CAP_GB, "plan_cap_gb": VRAM_CAP_PLAN_GB})
        self.layers = get_layers(self.model)
        self.L = len(self.layers)
        self.d = int(self.model.config.hidden_size)
        L = self.L
        self.L_h = min(int(round(0.5 * L)), L - 2)
        self.B_mid = [self.L_h - 1, self.L_h, self.L_h + 1]
        self.B_late = [l for l in range(L) if 0.75 <= l / L <= 0.90 and l < L - 1]
        if not self.B_late:
            self.B_late = [int(0.8 * L)]
        self.C7_layers = [l for l in range(L) if 0.4 <= l / L <= 0.9]
        self.C3_mid = []
        for b in range(6):
            band = list(range(math.ceil(b * L / 6), math.ceil((b + 1) * L / 6)))
            band = [l for l in band if l < L] or [min(L - 1, int(b * L / 6))]
            mid = band[len(band) // 2]
            # review fix (v2): never patch the FINAL layer (for L=16 the upper-middle of band 5 is L-1, where
            # last-token patching reproduces the twin's final state exactly and f_5 = 1 by construction)
            self.C3_mid.append(mid if mid < L - 1 else L - 2)
        self.ref, self.com = onset_ids(self.tok)
        W = self.model.get_output_embeddings().weight
        self.W_rc = W[self.ref + self.com].detach().float().clone()
        self.n_ref = len(self.ref)
        eos = set()
        for e in (self.tok.eos_token_id, getattr(self.model.generation_config, "eos_token_id", None)):
            if isinstance(e, int):
                eos.add(e)
            elif isinstance(e, (list, tuple)):
                eos.update(int(x) for x in e)
        self.eos_ids = torch.tensor(sorted(eos) if eos else [-1])
        self._normed = None

        def norm_hook(mod, inp, out):
            self._normed = out[:, -1, :]
        self.norm_handle = self.model.model.norm.register_forward_hook(norm_hook)
        probe = {}
        h = self.layers[0].register_forward_hook(lambda m, i, o: probe.__setitem__("t", isinstance(o, tuple)))
        with torch.no_grad():
            self.model(input_ids=torch.tensor([[self.tok.eos_token_id or 0]], device=DEVICE), use_cache=False,
                       logits_to_keep=1)
        h.remove()
        self.out_is_tuple = bool(probe.get("t", False))
        self.timing["load_s"] = time.time() - t
        self.t_load_end = time.time()
        logger.info(f"{self.repo}: loaded in {self.timing['load_s']:.0f}s L={L} d={self.d} L_h={self.L_h} "
                    f"B_mid={self.B_mid} B_late={self.B_late} C3_mid={self.C3_mid} |R|={len(self.ref)} "
                    f"|C|={len(self.com)} tuple_out={self.out_is_tuple}")

    def unload(self) -> None:
        try:
            self.norm_handle.remove()
        except AttributeError:
            pass
        for k in ("model", "tok", "W_rc", "layers"):
            if hasattr(self, k):
                delattr(self, k)
        import gc
        gc.collect()
        if DEVICE.type == "cuda":
            torch.cuda.empty_cache()

    # -- readout
    def margin_now(self) -> torch.Tensor:
        z = self._normed.float() @ self.W_rc.T
        return torch.logsumexp(z[:, : self.n_ref], -1) - torch.logsumexp(z[:, self.n_ref:], -1)

    def batch(self, cond: str) -> Batch:
        system = None if cond == "plain" else POLES["always_refuse" if cond == "pole_refuse" else "never_refuse"]
        for p in PROMPTS:
            assert p in ALLOWED_PROMPTS
        return build_batch(self.tok, self.repo, PROMPTS, system, self.meta["template_mode_panel"])

    # -- passes
    def _cap(self, store: dict, l: int, full: bool = False):
        def f(h: torch.Tensor):
            store[l] = h.detach().clone() if full else h[:, -1, :].detach().float()
            return None
        return f

    @torch.no_grad()
    def base_pass(self, b: Batch, full_layers: list[int], want_attn: bool,
                  extra_fns: list | None = None) -> dict:
        last: dict[int, torch.Tensor] = {}
        full: dict[int, list[torch.Tensor]] = {l: [] for l in full_layers}

        def mk(l: int):
            def f(h: torch.Tensor):
                last[l] = h[:, -1, :].detach().float()
                if l in full:
                    full[l].append(h.detach().clone())
                return None
            return f
        fns = list(extra_fns or []) + [(l, mk(l)) for l in range(self.L)]
        with hooks(self.layers, fns):
            o1 = self.model(input_ids=b.ids[:, :-1], attention_mask=b.mask[:, :-1], position_ids=b.pos[:, :-1],
                            use_cache=True, logits_to_keep=1)
            cache = o1.past_key_values
            o2 = self.model(input_ids=b.ids[:, -1:], attention_mask=b.mask, position_ids=b.pos[:, -1:],
                            past_key_values=cache, use_cache=True, output_attentions=want_attn, logits_to_keep=1)
        m = self.margin_now().detach().cpu().numpy().astype(np.float64)
        logits = o2.logits[:, -1, :].float()
        lg_ref = torch.logsumexp(logits[:, self.ref], -1)
        lg_com = torch.logsumexp(logits[:, self.com], -1)
        m_logits = (lg_ref - lg_com).detach().cpu().numpy().astype(np.float64)
        mass = torch.exp(lg_ref - torch.logsumexp(logits, -1)).detach().cpu().numpy().astype(np.float64)
        R = torch.stack([last[l] for l in range(self.L)], 1).detach().cpu().numpy()
        attn = None
        if want_attn and o2.attentions is not None:
            attn = torch.stack([a[:, :, -1, :].float().mean(1) for a in o2.attentions],
                               1).detach().cpu().numpy()  # (B, L, T)
        out = {"m": m, "m_logits": m_logits, "mass": mass, "R": R, "attn": attn, "cache": cache,
               "first_tok": logits.argmax(-1), "full": {l: torch.cat(v, 1) for l, v in full.items()}}
        del o1, o2, logits
        return out

    def late_caps(self, store: dict) -> list:
        return [(l, self._cap(store, l)) for l in self.B_late]

    @torch.no_grad()
    def last_call(self, b: Batch, cache, fns: list, capture_late: bool = True) -> tuple[np.ndarray, np.ndarray | None]:
        st: dict[int, torch.Tensor] = {}
        cf = self.late_caps(st) if capture_late else []
        # review fix (v2): a cache still holding the last prompt token would make the re-run token attend to a
        # stale unperturbed copy of itself (the short mask is zero-padded silently by transformers)
        assert cache.get_seq_length() == b.T - 1, f"stale KV cache: length {cache.get_seq_length()} != T-1={b.T - 1}"
        with hooks(self.layers, list(fns) + cf):
            self.model(input_ids=b.ids[:, -1:], attention_mask=b.mask, position_ids=b.pos[:, -1:],
                       past_key_values=cache, use_cache=True, logits_to_keep=1)
        cache.crop(b.T - 1)
        m = self.margin_now().detach().cpu().numpy().astype(np.float64)
        late = torch.stack([st[l] for l in self.B_late], 1).detach().cpu().numpy() if capture_late else None
        return m, late

    @torch.no_grad()
    def skip_call(self, b: Batch, j: int, h_in: torch.Tensor, fns: list,
                  capture_late: bool = True) -> tuple[np.ndarray, np.ndarray | None]:
        st: dict[int, torch.Tensor] = {}
        cf = self.late_caps(st) if capture_late else []
        with skip_below(self.layers, j, h_in, self.out_is_tuple), hooks(self.layers, list(fns) + cf):
            self.model(input_ids=b.ids, attention_mask=b.mask, position_ids=b.pos, use_cache=False, logits_to_keep=1)
        m = self.margin_now().detach().cpu().numpy().astype(np.float64)
        late = torch.stack([st[l] for l in self.B_late], 1).detach().cpu().numpy() if capture_late else None
        return m, late

    @torch.no_grad()
    def generate(self, b: Batch, base: dict, n_new: int, n_capture: int = 8,
                 extra_fns: list | None = None) -> tuple[list[str], np.ndarray, list[list[int]]]:
        cache = base["cache"]
        B = b.ids.shape[0]
        if cache.get_seq_length() == b.T - 1:
            with hooks(self.layers, list(extra_fns or [])):
                o0 = self.model(input_ids=b.ids[:, -1:], attention_mask=b.mask, position_ids=b.pos[:, -1:],
                                past_key_values=cache, use_cache=True, logits_to_keep=1)
            y = o0.logits[:, -1, :].argmax(-1)
        else:
            assert cache.get_seq_length() == b.T, "unexpected cache length"
            y = base["first_tok"].clone()
        toks = [y]
        mask = b.mask
        traj = []
        n_calls = max(n_new - 1, n_capture)
        for t in range(1, n_calls + 1):
            mask = torch.cat([mask, torch.ones(B, 1, dtype=mask.dtype, device=mask.device)], 1)
            st: dict[int, torch.Tensor] = {}
            fns = list(extra_fns or []) + (self.late_caps(st) if t <= n_capture else [])
            with hooks(self.layers, fns):
                o = self.model(input_ids=y[:, None], attention_mask=mask, position_ids=b.pos[:, -1:] + t,
                               past_key_values=cache, use_cache=True, logits_to_keep=1)
            if t <= n_capture:
                traj.append(torch.stack([st[l] for l in self.B_late], 1).detach().cpu().numpy())
            y = o.logits[:, -1, :].argmax(-1)
            if len(toks) < n_new:
                toks.append(y)
        cache.crop(b.T - 1)
        T = torch.stack(toks, 1)
        texts, ids_out = [], []
        eos = set(self.eos_ids.tolist())
        for i in range(B):
            ids = T[i].tolist()
            cut = next((k for k, t_ in enumerate(ids) if t_ in eos), len(ids))
            ids_out.append(ids[:cut])
            texts.append(self.tok.decode(ids[:cut], skip_special_tokens=True))
        return texts, np.stack(traj, 1), ids_out  # traj (B, n_capture, n_late, d)

    def _grad_pass_chunk(self, b: Batch, rows_chunk: list[int]) -> dict:
        bb = b.rows(rows_chunk)
        emb = self.model.get_input_embeddings()(bb.ids).detach().requires_grad_(True)
        store: dict[str, torch.Tensor] = {}

        def keep(h: torch.Tensor):
            h.retain_grad()
            store["x"] = h
            return None
        with torch.enable_grad(), hooks(self.layers, [(self.L_h, keep)]):
            self.model(inputs_embeds=emb, attention_mask=bb.mask, position_ids=bb.pos, use_cache=False,
                       logits_to_keep=1)
            m = self.margin_now()
            m.sum().backward()
        G = (emb.grad.float() * emb.detach().float()).sum(-1).abs().detach().cpu().numpy()
        out = {"m": m.detach().cpu().numpy().astype(np.float64), "G": G,
               "x": store["x"].detach().float().cpu().numpy(), "xg": store["x"].grad.float().cpu().numpy()}
        del emb, store, m
        return out

    def grad_pass(self, b: Batch, rows: list[int]) -> dict:
        """Batched backward over `rows` (indices into the full Batch b). On a CUDA OOM the same call is
        retried in successively halved row-chunks (down to 1 item), each built with b.rows(...) exactly
        as the unchunked call (so the padded length T is unchanged), then concatenated per-item so the
        result is identical in shape and meaning to the unchunked call."""
        try:
            return self._grad_pass_chunk(b, rows)
        except torch.cuda.OutOfMemoryError:
            logger.warning(f"{self.repo}: grad_pass OOM on {len(rows)} rows, falling back to row-chunking")
        torch.cuda.empty_cache()
        chunk = max(1, len(rows) // 2)
        while True:
            try:
                parts = []
                for i in range(0, len(rows), chunk):
                    torch.cuda.empty_cache()
                    parts.append(self._grad_pass_chunk(b, rows[i:i + chunk]))
                break
            except torch.cuda.OutOfMemoryError:
                torch.cuda.empty_cache()
                if chunk <= 1:
                    raise
                chunk = max(1, chunk // 2)
        self.flags.append({"code": "GRAD_CHUNKED", "chunk": chunk})
        return {"m": np.concatenate([p["m"] for p in parts], 0), "G": np.concatenate([p["G"] for p in parts], 0),
                "x": np.concatenate([p["x"] for p in parts], 0), "xg": np.concatenate([p["xg"] for p in parts], 0)}

    # ------------------------------------------------------------------------- candidate blocks
    def c1_block(self, b: Batch, base: dict, D: np.ndarray, rows_eval: list[int], eps_list: list[float],
                 rb: np.ndarray | None, null_dirs: np.ndarray | None, extra_fns: list | None = None) -> dict:
        """C1 finite-difference gain. D (16, L, d) per-item directions; norms from base R."""
        R = base["R"]
        m0 = base["m"]
        res: dict[str, Any] = {"eps": {}}
        late_store = {}

        def run(dirs_bl: dict[int, np.ndarray], eps: float, s: float) -> tuple[np.ndarray, np.ndarray]:
            fns = list(extra_fns or [])
            for l in self.B_mid:
                nrm = np.linalg.norm(R[:, l, :], axis=1)
                vec = torch.from_numpy((s * eps * nrm[:, None] * dirs_bl[l]).astype(np.float32)).to(DEVICE)
                vec[[i for i in range(len(R)) if i not in rows_eval]] = 0.0

                def f(h: torch.Tensor, _v=vec):
                    h = h.clone()
                    h[:, -1, :] = (h[:, -1, :].float() + _v).to(h.dtype)
                    return h
                fns.append((l, f))
            return self.last_call(b, base["cache"], fns)

        dirs = {l: D[:, l, :] for l in self.B_mid}
        for eps in eps_list:
            mp, lp = run(dirs, eps, +1.0)
            mm, lm = run(dirs, eps, -1.0)
            res["eps"][eps] = {"m_plus": mp, "m_minus": mm}
            late_store[eps] = (lp, lm)
        res["late_store"] = late_store
        ev = np.array(rows_eval)
        s_m = sd(m0[ev])
        g = (res["eps"][EPS0]["m_plus"] - res["eps"][EPS0]["m_minus"]) / (2 * EPS0)
        res["g_items"] = g
        res["sd_margin"] = s_m
        raw = float(np.mean(g[ev]))
        res["raw"] = raw
        und = (not math.isfinite(s_m)) or s_m < SD_FLOOR
        res["value"] = None if und else raw / s_m
        res["undefined_reason"] = f"H5 variance floor: SD(margin)={s_m:.3f} < {SD_FLOOR}" if und else None
        hi = [i for i in ev if IS_HARM[i]]
        ti = [i for i in ev if not IS_HARM[i]]
        res["harm_only"] = None if und else float(np.mean(g[hi])) / s_m
        res["twin_only"] = None if und else float(np.mean(g[ti])) / s_m
        # linearity per eps. review fix (v2): item-level ABSOLUTE one-sided differences (signed item means cancel
        # across items of opposite sign), and 'undetermined' when both are below the bf16 noise scale (0.05 logits)
        lin = {}
        for eps in eps_list:
            dpi = res["eps"][eps]["m_plus"][ev] - m0[ev]
            dmi = m0[ev] - res["eps"][eps]["m_minus"][ev]
            dp, dm = float(np.mean(np.abs(dpi))), float(np.mean(np.abs(dmi)))
            rel = abs(dp - dm) / max(dp, dm, 1e-9)
            det = max(dp, dm) >= 0.05
            lin[str(eps)] = {"d_plus_abs": dp, "d_minus_abs": dm, "d_plus_signed": float(np.mean(dpi)),
                             "d_minus_signed": float(np.mean(dmi)), "rel_asym": rel,
                             "linear": (rel < 0.2) if det else None,
                             "undetermined_below_noise": not det,
                             "gain": float(np.mean((res["eps"][eps]["m_plus"][ev] - res["eps"][eps]["m_minus"][ev])
                                                   / (2 * eps)))}
        res["linearity"] = lin
        res["linear_range_eps"] = [float(e) for e in eps_list if lin[str(e)]["linear"] is True]
        res["nonlinear_at_primary"] = (lin[str(EPS0)]["linear"] is False)
        # C1_late (projection of the late band on r^(b))
        if rb is not None:
            lp, lm = late_store[EPS0]
            proj = lambda Z: np.mean(np.einsum("bld,ld->bl", Z, rb[self.B_late]), 1)  # noqa: E731
            gl = (proj(lp) - proj(lm)) / (2 * EPS0)
            p0 = np.mean(np.einsum("bld,ld->bl", R[:, self.B_late, :], rb[self.B_late]), 1)
            sp = sd(p0[ev])
            res["late"] = float(np.mean(gl[ev])) / sp if sp > 0 else None
        # direction null
        if null_dirs is not None:
            nv = []
            for k in range(null_dirs.shape[1]):
                dk = {l: np.repeat(null_dirs[li, k][None, :], len(R), 0) for li, l in enumerate(self.B_mid)}
                mp, _ = run(dk, EPS0, +1.0)
                mm, _ = run(dk, EPS0, -1.0)
                gk = (mp - mm) / (2 * EPS0)
                nv.append(float(np.mean(gk[ev])) / s_m if not und else float(np.mean(gk[ev])))
            res["null_values"] = nv
            res["null_p95"] = float(np.percentile(nv, 95))
        return res

    def c2_block(self, b: Batch, j: int, h_in: torch.Tensor, D: np.ndarray, m_ref: np.ndarray,
                 null_dirs: np.ndarray | None, extra_fns: list | None = None) -> dict:
        """C2 two-sided self-ablation sensitivity on batch b (rows already selected)."""
        def abl(dirs_bl: dict[int, np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
            fns = list(extra_fns or [])
            for l in self.B_mid:
                U = torch.from_numpy(dirs_bl[l].astype(np.float32)).to(DEVICE)

                def f(h: torch.Tensor, _U=U):
                    hf = h.float()
                    pr = (hf * _U[:, None, :]).sum(-1, keepdim=True)
                    return (hf - pr * _U[:, None, :]).to(h.dtype)
                fns.append((l, f))
            return self.skip_call(b, j, h_in, fns)
        n = b.ids.shape[0]
        harm = np.array([bool(IS_HARM[i]) for i in b.item_idx])
        m_abl, late_abl = abl({l: D[:, l, :] for l in self.B_mid})
        drop = m_ref - m_abl
        s_m = sd(m_ref)
        und = (not math.isfinite(s_m)) or s_m < SD_FLOOR
        raw = float(drop[harm].mean() - drop[~harm].mean())
        res = {"m_abl": m_abl, "late_abl": late_abl, "drop": drop, "raw": raw, "sd_margin": s_m,
               "value": None if und else raw / s_m,
               "undefined_reason": f"H5 variance floor: SD(margin)={s_m:.3f} < {SD_FLOOR}" if und else None,
               "drop_harm_mean": float(drop[harm].mean()), "drop_twin_mean": float(drop[~harm].mean())}
        if null_dirs is not None:
            nv = []
            for k in range(null_dirs.shape[1]):
                mk, _ = abl({l: np.repeat(null_dirs[li, k][None, :], n, 0) for li, l in enumerate(self.B_mid)})
                dk = m_ref - mk
                rk = float(dk[harm].mean() - dk[~harm].mean())
                nv.append(rk / s_m if not und else rk)
            res["null_values"] = nv
            res["null_p95"] = float(np.percentile(nv, 95))
            v = res["value"]
            res["ratio_to_null_p95"] = (v / res["null_p95"]) if (v is not None and res["null_p95"] not in (0.0,)) else None
        return res

    def c3_block(self, b: Batch, base: dict, pairs: list[int], extra_fns: list | None = None) -> dict:
        R, m0 = base["R"], base["m"]
        F = np.full((NP, 6), np.nan)
        for bi, lb in enumerate(self.C3_mid):
            rows = [2 * p for p in range(NP)]
            vals = torch.from_numpy(R[[2 * p + 1 for p in range(NP)], lb, :].astype(np.float32))

            def f(h: torch.Tensor, _rows=rows, _vals=vals):
                h = h.clone()
                h[_rows, -1, :] = _vals.to(h.device, h.dtype)
                return h
            mp, _ = self.last_call(b, base["cache"], list(extra_fns or []) + [(lb, f)], capture_late=False)
            for p in range(NP):
                den = m0[2 * p] - m0[2 * p + 1]
                F[p, bi] = np.clip((m0[2 * p] - mp[2 * p]) / den, -0.5, 1.5) if abs(den) >= INFORMATIVE else np.nan
        return {"F": F, **self.c3_value(F, m0, pairs)}

    def c3_value(self, F: np.ndarray, m0: np.ndarray, pairs: list[int]) -> dict:
        inf = [p for p in pairs if abs(m0[2 * p] - m0[2 * p + 1]) >= INFORMATIVE]
        depths = [self.C3_mid[bi] / self.L for bi in range(6)]  # review fix (v2): depth of the PATCHED layer
        if len(inf) < 3:
            return {"value": None, "undefined_reason": f"only {len(inf)} informative pairs (<3)",
                    "n_informative": len(inf), "depth": None, "sharp": None}
        flip = float(np.mean([np.nanmax(F[p]) for p in inf]))
        dl, sh = [], []
        for p in inf:
            hit = [depths[bi] for bi in range(6) if F[p, bi] >= 0.5]
            if hit:
                dl.append(hit[0])
            sh.append(float(np.nanmax(np.diff(F[p]))))  # review fix (v2): max_b f_b - f_{b-1}, b >= 1
        return {"value": flip, "undefined_reason": None, "n_informative": len(inf),
                "depth": float(np.mean(dl)) if dl else None, "depth_n": len(dl), "sharp": float(np.mean(sh))}

    def c7_c8(self, b: Batch, attn: np.ndarray | None, G_harm: np.ndarray | None, G_twin: np.ndarray | None,
              pairs: list[int], rng_seed: int) -> dict:
        """C7 (attention mass) and C8 (grad x input share) on twin-differing tokens (harm side)."""
        diffs = {}
        for p in range(NP):
            dh, dt = differing_positions(b, 2 * p, 2 * p + 1)
            diffs[p] = (dh, dt)
        use = [p for p in pairs if len(diffs[p][0]) > 0]
        out: dict[str, Any] = {"n_pairs_used": len(use), "diff_tokens": {
            PAIR_IDS[p]: [self.tok.decode([int(b.ids[2 * p, j])]) for j in diffs[p][0]] for p in range(NP)}}
        rng7 = np.random.default_rng(rng_seed)
        if len(use) < 4:
            out["C7"] = cand(None, f"only {len(use)} pairs with non-empty differing sets (<4)")
            out["C8"] = cand(None, f"only {len(use)} pairs with non-empty differing sets (<4)")
            return out
        if attn is not None:
            a = attn[:, self.C7_layers, :].mean(1)
            vals, within, nulls = [], [], []
            for p in use:
                i = 2 * p
                cont = b.content[i]
                dh = diffs[p][0]
                share = len(dh) / len(cont)
                vals.append(a[i, dh].sum() / share)
                within.append((a[i, dh].sum() / max(a[i, cont].sum(), 1e-12)) / share)
            for _ in range(N_SUB):
                nv = []
                for p in use:
                    i = 2 * p
                    cont = b.content[i]
                    k = len(diffs[p][0])
                    sub = rng7.choice(cont, size=k, replace=False)
                    nv.append(a[i, sub].sum() / (k / len(cont)))
                nulls.append(float(np.mean(nv)))
            out["C7"] = cand(float(np.mean(vals)), None, within_content=float(np.mean(within)),
                             null_values=nulls, null_p95=float(np.percentile(nulls, 95)),
                             per_pair={PAIR_IDS[p]: float(v) for p, v in zip(use, vals)})
        else:
            out["C7"] = cand(None, "C7_UNAVAILABLE (no attentions)")
        if G_harm is not None:
            rng8 = np.random.default_rng(rng_seed + 1)
            vals, tw, nulls = [], [], []
            for k_, p in enumerate(use):
                i = 2 * p
                g = G_harm[p]
                cont = b.content[i]
                dh = diffs[p][0]
                vals.append((g[dh].sum() / max(g[cont].sum(), 1e-12)) / (len(dh) / len(cont)))
                if G_twin is not None and len(diffs[p][1]) > 0:
                    gt = G_twin[p]
                    ct = b.content[i + 1]
                    tw.append((gt[diffs[p][1]].sum() / max(gt[ct].sum(), 1e-12)) / (len(diffs[p][1]) / len(ct)))
            for _ in range(N_SUB):
                nv = []
                for p in use:
                    i = 2 * p
                    g = G_harm[p]
                    cont = b.content[i]
                    k = len(diffs[p][0])
                    sub = rng8.choice(cont, size=k, replace=False)
                    nv.append((g[sub].sum() / max(g[cont].sum(), 1e-12)) / (k / len(cont)))
                nulls.append(float(np.mean(nv)))
            out["C8"] = cand(float(np.mean(vals)), None, twin_side=(float(np.mean(tw)) if tw else None),
                             null_values=nulls, null_p95=float(np.percentile(nulls, 95)),
                             per_pair={PAIR_IDS[p]: float(v) for p, v in zip(use, vals)})
        else:
            out["C8"] = cand(None, "no gradient pass")
        return out

    def c9_atp(self, b: Batch, gh: dict, base: dict, pairs: list[int]) -> dict:
        """AtP template share at L_h. gh: grad pass over the 8 harmful rows (pair order)."""
        full = base["full"][self.L_h].float().detach().cpu().numpy()
        m0 = base["m"]
        vals = {}
        for p in range(NP):
            i, t = 2 * p, 2 * p + 1
            sh, st = b.suffix[i], b.suffix[t]
            k = min(len(sh), len(st))
            if k == 0:
                continue
            ph, pt = sh[-k:], st[-k:]
            atp = float(np.sum((gh["x"][p, ph, :] - full[t, pt, :]) * gh["xg"][p, ph, :]))
            den = m0[i] - m0[t]  # review fix (v2): both margins from the same 16-row base pass
            vals[p] = (atp, den)
        inf = [p for p in pairs if p in vals and abs(vals[p][1]) >= INFORMATIVE]
        per = {PAIR_IDS[p]: float(np.clip(vals[p][0] / vals[p][1], -0.5, 1.5)) for p in inf}
        if len(inf) < 3:
            return {"value": None, "undefined_reason": f"only {len(inf)} informative pairs (<3)", "per_pair": per,
                    "n_informative": len(inf)}
        return {"value": float(np.mean(list(per.values()))), "undefined_reason": None, "per_pair": per,
                "n_informative": len(inf), "raw_atp": {PAIR_IDS[p]: vals[p][0] for p in vals}}

    def c9_true(self, b: Batch, base: dict, pairs: list[int]) -> dict:
        """True activation patching of all template-suffix positions at L_h (harm <- twin), from L_h+1."""
        j = self.L_h + 1
        full = base["full"][self.L_h]
        m_ref, _ = self.skip_call(b, j, full, [], capture_late=False)
        rows = list(HARM_IDX)
        patched = full[rows].clone()
        for k_, p in enumerate(range(NP)):
            i, t = 2 * p, 2 * p + 1
            sh, st = b.suffix[i], b.suffix[t]
            k = min(len(sh), len(st))
            if k:
                sh_idx = torch.from_numpy(sh[-k:]).to(full.device)
                st_idx = torch.from_numpy(st[-k:]).to(full.device)
                patched[k_, sh_idx, :] = full[t, st_idx, :]
        m_p, _ = self.skip_call(b.rows(rows), j, patched, [], capture_late=False)
        # review fix (v2): the unpatched reference for the numerator comes from the SAME 8-row batch shape as the
        # patched pass (bf16 kernels round differently by batch shape; see STAGE_B1_BF16_ROUNDING)
        m_h8, _ = self.skip_call(b.rows(rows), j, full[rows], [], capture_late=False)
        per = {}
        for k_, p in enumerate(range(NP)):
            den = m_ref[2 * p] - m_ref[2 * p + 1]
            if abs(den) >= INFORMATIVE and p in pairs:
                per[PAIR_IDS[p]] = float(np.clip((m_h8[k_] - m_p[k_]) / den, -0.5, 1.5))
        val = float(np.mean(list(per.values()))) if len(per) >= 3 else None
        return {"value": val, "per_pair": per, "n_informative": len(per), "m_ref": m_ref, "m_patched": m_p,
                "m_ref_8row": m_h8,
                "undefined_reason": None if val is not None else f"only {len(per)} informative pairs (<3)"}

    @staticmethod
    def c9_true_subset(per_pair: dict, pairs: list[int]) -> dict:
        """C9 true-patching value restricted to a pair subset (k8), same <3-informative rule."""
        sub = [per_pair[PAIR_IDS[p]] for p in pairs if PAIR_IDS[p] in per_pair]
        val = float(np.mean(sub)) if len(sub) >= 3 else None
        return {"value": val, "undefined_reason": None if val is not None else f"only {len(sub)} informative pairs (<3)"}

    def c11_value(self, traj: np.ndarray, rb: np.ndarray, pairs: list[int]) -> dict:
        """traj (16, 8, n_late, d); rb (L, d)."""
        P = np.einsum("btld,ld->btl", traj, rb[self.B_late]).mean(2)  # (16, 8)
        t = np.arange(1, P.shape[1] + 1)
        slope = np.array([ols_slope(t, P[i]) for i in range(P.shape[0])])
        plateau = P[:, 4:8].mean(1)
        hs = [2 * p for p in pairs]
        ts = [2 * p + 1 for p in pairs]
        diff = plateau[hs] - plateau[ts]
        pooled = math.sqrt((np.var(plateau[hs], ddof=1) + np.var(plateau[ts], ddof=1)) / 2)
        val = float(np.mean(diff) / pooled) if pooled > 0 else None
        return {"value": val, "undefined_reason": None if val is not None else "zero pooled SD",
                "slope_diff": float(np.mean(slope[hs] - slope[ts])), "plateau_harm": float(np.mean(plateau[hs])),
                "plateau_twin": float(np.mean(plateau[ts])), "pooled_sd": pooled, "proj": P}

    def c16_block(self, b: Batch, j: int, h_in: torch.Tensor, rdir: np.ndarray, m_ref: np.ndarray,
                  scale: dict[int, float], alphas: list[float], extra_fns: list | None = None) -> dict:
        ms = {}
        for a in alphas:
            if a == 0.0:
                ms[a] = m_ref
                continue
            fns = list(extra_fns or [])
            for l in self.B_mid:
                v = torch.from_numpy((a * 0.05 * scale[l] * rdir[l]).astype(np.float32)).to(DEVICE)
                fns.append((l, lambda h, _v=v: (h.float() + _v).to(h.dtype)))
            ms[a], _ = self.skip_call(b, j, h_in, fns, capture_late=False)
        A = np.array(alphas)
        M = np.stack([ms[a] for a in alphas], 1)
        sl = np.array([ols_slope(A, M[i]) for i in range(M.shape[0])])
        harm = np.array([bool(IS_HARM[i]) for i in b.item_idx])
        s_m = sd(m_ref)
        und = (not math.isfinite(s_m)) or s_m < SD_FLOOR
        return {"value": None if und else float(sl.mean()) / s_m, "raw_slope": float(sl.mean()),
                "harm_slope": float(sl[harm].mean()), "twin_slope": float(sl[~harm].mean()), "alphas": alphas,
                "undefined_reason": f"H5 variance floor: SD(margin)={s_m:.3f} < {SD_FLOOR}" if und else None,
                "margins_by_alpha": {str(a): ms[a] for a in alphas}}

    def bars(self, base: dict, rows: list[int]) -> dict:
        m, mass = base["m"], base["mass"]
        h = [i for i in rows if IS_HARM[i]]
        t = [i for i in rows if not IS_HARM[i]]
        return {"logit_gap": float(m[h].mean() - m[t].mean()), "refusal_mass": float(mass[h].mean() - mass[t].mean()),
                "logit_gap_level": float(m[h].mean()), "refusal_mass_level": float(mass[h].mean()),
                "margin_twin_mean": float(m[t].mean()), "sd_margin": sd(m[rows])}

    # ------------------------------------------------------------------------- one condition
    def run_condition(self, cond: str, b: Batch, base: dict, rb: np.ndarray, scale: dict[int, float],
                      full_mode: bool) -> dict:
        """All candidates under one presentation. full_mode (plain) adds nulls, linearity grid, k8,
        twin-side C8 and true patching."""
        out: dict[str, Any] = {}
        R, m0 = base["R"], base["m"]
        allp = list(range(NP))
        j = self.B_mid[0]
        h_in = base["full"][j - 1]
        # directions within the condition
        D = cf_harm_dirs(R, allp, FOLDS)
        # --- bars
        out["bars"] = self.bars(base, list(range(2 * NP)))
        # --- C1
        t = self.tic()
        null1 = self.null_dirs["C1"] if full_mode else None
        c1 = self.c1_block(b, base, D, list(range(2 * NP)), EPS_GRID if full_mode else [EPS0], rb, null1)
        self.toc(f"{cond}:C1", t, ("C1",) if full_mode else ())
        out["C1"] = c1
        # --- C3
        t = self.tic()
        out["C3"] = self.c3_block(b, base, allp)
        self.toc(f"{cond}:C3", t, ("C3",) if full_mode else ())
        # --- C2 (reference skip pass shared with C16)
        t = self.tic()
        m_ref, late_ref = self.skip_call(b.with_items(list(range(2 * NP))), j, h_in, [])
        self.toc(f"{cond}:ref_skip", t, ("C2", "C16") if full_mode else ())
        out["ref_skip"] = {"m_ref": m_ref, "max_abs_vs_base": float(np.max(np.abs(m_ref - m0)))}
        t = self.tic()
        c2 = self.c2_block(b.with_items(list(range(2 * NP))), j, h_in, D, m_ref,
                           self.null_dirs["C2"] if full_mode else None)
        c2["late_ref"] = late_ref
        self.toc(f"{cond}:C2", t, ("C2",) if full_mode else ())
        out["C2"] = c2
        # --- C16
        t = self.tic()
        out["C16"] = self.c16_block(b.with_items(list(range(2 * NP))), j, h_in, rb, m_ref, scale,
                                    ALPHAS if full_mode else ALPHAS_VAR)
        self.toc(f"{cond}:C16", t, ("C16",) if full_mode else ())
        # --- gradient pass (C8 / C9)
        t = self.tic()
        gh = self.grad_pass(b, list(HARM_IDX))
        gt = self.grad_pass(b, list(TWIN_IDX)) if full_mode else None
        self.toc(f"{cond}:grad", t, ("C8", "C9") if full_mode else ())
        # --- C7 / C8
        t = self.tic()
        c78 = self.c7_c8(b, base["attn"], gh["G"], gt["G"] if gt else None, allp, SEED + 7)
        out["C7"], out["C8"] = c78["C7"], c78["C8"]
        out["diff_tokens"] = c78["diff_tokens"]
        out["c78_pairs_used"] = c78["n_pairs_used"]
        # --- C9
        out["C9"] = self.c9_atp(b, gh, base, allp)
        self.toc(f"{cond}:C7C8C9", t, ())
        # review fix (v2): true patching in EVERY condition, so the pole values exist if ATP_UNRELIABLE fires
        t = self.tic()
        out["C9_true"] = self.c9_true(b, base, allp)
        self.toc(f"{cond}:C9_true", t, ("C9",) if full_mode else ())
        if full_mode:
            if out["C9"]["value"] is not None and out["C9_true"]["value"] is not None:
                common = [k for k in out["C9"]["per_pair"] if k in out["C9_true"]["per_pair"]]
                if len(common) >= 3:
                    a_ = [out["C9"]["per_pair"][k] for k in common]
                    b_ = [out["C9_true"]["per_pair"][k] for k in common]
                    out["C9_atp_vs_true_pearson"] = (float(np.corrcoef(a_, b_)[0, 1])
                                                     if np.std(a_) > 0 and np.std(b_) > 0 else None)
        out["_gh"] = gh
        out["_D"] = D
        return out


# ----------------------------------------------------------------------------- Batch helpers (item tracking)
def _with_items(self: Batch, items: list[int]) -> Batch:
    nb = self.rows(items)
    nb.item_idx = list(items)
    return nb


Batch.with_items = _with_items  # type: ignore[attr-defined]
_orig_rows = Batch.rows


def _rows_tracked(self: Batch, idx):
    nb = _orig_rows(self, idx)
    base_idx = getattr(self, "item_idx", list(range(self.ids.shape[0])))
    nb.item_idx = [base_idx[int(i)] for i in idx]
    return nb


Batch.rows = _rows_tracked  # type: ignore[assignment]


# ----------------------------------------------------------------------------- the full per-model procedure
def measure(repo: str, smoke: bool = False, lite: bool = False) -> dict:
    mr = ModelRun(repo, smoke)
    mr.load()
    mr.lite = lite
    if CAP_OVERRIDE:
        mr.flags.append(dict(CAP_OVERRIDE))
    if lite:
        mr.flags.append({"code": "ANCHOR_LITE", "detail": "plain-condition candidates only: no random-direction nulls, "
                         "no k8, no pole-condition candidate values (pole base passes kept for r^(b)), no C16 oracle, no offset control"})
    row: dict[str, Any] = {**mr.meta, "status": "ok", "tier": "live", "prereg_hash": PREREG_HASH,
                           "screen16_file_sha256": S16_INFO["file_sha256"], "dtype": "bfloat16",
                           "device": DEVICE.type, "n_layers": mr.L, "d_model": mr.d, "local_snapshot": str(mr.local),
                           "bands": {"L_h": mr.L_h, "B_mid": mr.B_mid, "B_late": mr.B_late, "C3_mid": mr.C3_mid,
                                     "C7_layers": [mr.C7_layers[0], mr.C7_layers[-1]]},
                           "token_sets": {"refuse_ids": mr.ref, "comply_ids": mr.com,
                                          "refuse_tokens": [mr.tok.decode([i]) for i in mr.ref],
                                          "comply_tokens": [mr.tok.decode([i]) for i in mr.com]}}
    conds = ["plain", "pole_refuse", "pole_comply"]
    B = {c: mr.batch(c) for c in conds}
    for c in conds:
        B[c].item_idx = list(range(2 * NP))
    row["render"] = {c: {"T": B[c].T, "modes": sorted(set(B[c].modes)), "add_special_tokens": B[c].add_special,
                         "example": B[c].texts[0][-300:]} for c in conds}
    j = mr.B_mid[0]
    full_plain = sorted(set([j - 1, mr.L_h] + mr.B_mid))
    full_pole = sorted(set([j - 1, mr.L_h]))
    # ---------------- plain base pass + 64-token generation (C11 trajectory + oracle replies)
    t = mr.tic()
    base = {"plain": mr.base_pass(B["plain"], full_plain, want_attn=True)}
    mr.toc("plain:base", t)
    row["readout_check"] = {"max_abs_margin_fp32_vs_logits": float(np.max(np.abs(base["plain"]["m"] -
                                                                                  base["plain"]["m_logits"])))}
    t = mr.tic()
    texts64, traj_plain, gen_ids = mr.generate(B["plain"], base["plain"], 64, 8)
    mr.toc("plain:gen64", t, ("C11",))
    judge_t = JudgeThread([(PROMPTS[i], texts64[i]) for i in range(2 * NP)])
    judge_t.start()
    row["gen64"] = [{"pair_id": ITEMS[i]["pair_id"], "side": ITEMS[i]["side"], "text": texts64[i],
                     "n_tokens": len(gen_ids[i])} for i in range(2 * NP)]
    # ---------------- pole base passes (r^(b) needs both)
    for c in ("pole_refuse", "pole_comply"):
        t = mr.tic()
        base[c] = mr.base_pass(B[c], full_pole, want_attn=True)
        mr.toc(f"{c}:base", t)
    mr.check_hard()
    # ---------------- directions (plain)
    Rp = base["plain"]["R"]
    L = mr.L
    rb = unit((base["pole_refuse"]["R"] - base["pole_comply"]["R"]).mean(0))  # (L, d)
    k8i = [int(x) for x in K8_ITEMS]
    rb_k8 = unit((base["pole_refuse"]["R"][k8i] - base["pole_comply"]["R"][k8i]).mean(0))
    Dh = cf_harm_dirs(Rp, list(range(NP)), FOLDS)
    proj_h = np.einsum("bd,bd->b", Rp[:, mr.L_h, :], Dh[:, mr.L_h, :])
    auc_cf = auroc(proj_h, IS_HARM.astype(int))
    h_all_in = unit(Rp[HARM_IDX, mr.L_h].mean(0) - Rp[TWIN_IDX, mr.L_h].mean(0))
    auc_in = auroc(Rp[:, mr.L_h] @ h_all_in, IS_HARM.astype(int))
    rng = np.random.default_rng(SEED)
    null_auc = []
    RLh = Rp[:, [mr.L_h], :]
    for _ in range(200):
        flip = rng.integers(0, 2, NP).astype(bool)
        Rperm = RLh.copy()
        for p in np.where(flip)[0]:
            Rperm[[2 * p, 2 * p + 1]] = Rperm[[2 * p + 1, 2 * p]]
        Dp = cf_harm_dirs(Rperm, list(range(NP)), FOLDS)
        null_auc.append(auroc(np.einsum("bd,bd->b", Rperm[:, 0], Dp[:, 0]), IS_HARM.astype(int)))
    Da, oka = cf_rank_dirs(Rp, base["plain"]["m"], list(range(NP)), FOLDS)
    cos_ab = [float(np.mean(np.einsum("bd,d->b", Da[:, l, :], rb[l]))) for l in range(L)]
    row["directions"] = {"h_auroc_crossfit_Lh": auc_cf, "h_auroc_insample_Lh": auc_in,
                         "h_auroc_perm_null_p95": float(np.percentile(null_auc, 95)),
                         "h_auroc_perm_p": float(np.mean(np.array(null_auc) >= auc_cf)),
                         "ra_folds_defined": oka, "cos_ra_rb_per_layer": cos_ab,
                         "cos_h_rb_per_layer": [float(np.dot(unit(Rp[HARM_IDX, l].mean(0) - Rp[TWIN_IDX, l].mean(0)),
                                                             rb[l])) for l in range(L)]}
    # anisotropy-matched random directions at B_mid (C1 seed +1, C2 seed +2)
    mr.null_dirs = {"C1": None, "C2": None}
    info_null = {}
    for cname, off in (() if lite else (("C1", 1), ("C2", 2))):
        rng_c = np.random.default_rng(SEED + off)
        V = np.zeros((len(mr.B_mid), N_RAND, mr.d), np.float32)
        infos = []
        for li, l in enumerate(mr.B_mid):
            Hf = base["plain"]["full"][l].float().detach().cpu().numpy()
            A = np.concatenate([Hf[i, B["plain"].mask[i].detach().cpu().numpy().astype(bool)]
                                for i in range(2 * NP)], 0)
            A = massive_filter(A)
            h_l = unit(Rp[HARM_IDX, l].mean(0) - Rp[TWIN_IDX, l].mean(0)).astype(np.float32)
            V[li], inf_ = aniso_random_dirs(A.astype(np.float32), h_l, N_RAND, rng_c)
            inf_["n_rows"] = int(A.shape[0])
            infos.append(inf_)
        mr.null_dirs[cname] = V
        info_null[cname] = infos
    row["random_dirs"] = info_null
    scale = {l: float(np.mean(np.linalg.norm(Rp[:, l, :], axis=1))) for l in mr.B_mid}
    row["c16_scale"] = scale
    # ---------------- plain candidates
    res = {}
    res["plain"] = mr.run_condition("plain", B["plain"], base["plain"], rb, scale, full_mode=True)
    c11 = mr.c11_value(traj_plain, rb, list(range(NP)))
    res["plain"]["C11"] = c11
    mr.check_hard()
    # ---------------- k8 variants
    k8 = {}
    if not lite and mr.soft_ok("k8"):
      try:
        t = mr.tic()
        bp = base["plain"]
        k8["bars"] = mr.bars(bp, k8i)
        D8 = cf_harm_dirs(Rp, K8_PAIRS, K8_FOLDS)
        c1k = mr.c1_block(B["plain"], bp, D8, k8i, [EPS0], None, None)
        k8["C1"] = cand(c1k["value"], c1k["undefined_reason"])
        bk = B["plain"].with_items(k8i)
        hk = bp["full"][j - 1][k8i]
        m_ref8, _ = mr.skip_call(bk, j, hk, [], capture_late=False)
        c2k = mr.c2_block(bk, j, hk, D8[k8i], m_ref8, None)
        k8["C2"] = cand(c2k["value"], c2k["undefined_reason"])
        k8["C3"] = cand(**{k: v for k, v in mr.c3_value(res["plain"]["C3"]["F"], bp["m"], K8_PAIRS).items()
                          if k in ("value",)}, reason=mr.c3_value(res["plain"]["C3"]["F"], bp["m"], K8_PAIRS)["undefined_reason"])
        c78k = mr.c7_c8(B["plain"], bp["attn"], res["plain"]["_gh"]["G"], None, K8_PAIRS, SEED + 7)
        k8["C7"], k8["C8"] = cand(c78k["C7"]["value"], c78k["C7"]["reason"]), cand(c78k["C8"]["value"], c78k["C8"]["reason"])
        c9k = mr.c9_atp(B["plain"], res["plain"]["_gh"], bp, K8_PAIRS)
        k8["C9"] = cand(c9k["value"], c9k["undefined_reason"])
        c9tk = mr.c9_true_subset(res["plain"]["C9_true"]["per_pair"], K8_PAIRS)
        k8["C9_true"] = cand(c9tk["value"], c9tk["undefined_reason"])
        c11k = mr.c11_value(traj_plain, rb_k8, K8_PAIRS)
        k8["C11"] = cand(c11k["value"], c11k["undefined_reason"])
        c16k = mr.c16_block(bk, j, hk, rb_k8, m_ref8, scale, ALPHAS_VAR)
        k8["C16"] = cand(c16k["value"], c16k["undefined_reason"])
        mr.toc("k8", t)
      except (RuntimeError, ValueError, IndexError, KeyError, TypeError) as e:
        logger.exception(f"{repo}: k8 block failed")
        mr.flags.append({"code": "K8_BLOCK_FAILED", "detail": f"{type(e).__name__}: {e}"})
        k8 = {}
    # ---------------- pole conditions
    for c in (() if lite else ("pole_refuse", "pole_comply")):
        if c == "pole_comply" and not mr.soft_ok(c):
            continue
        mr.check_hard()
        t = mr.tic()
        _, traj_c, _ = mr.generate(B[c], base[c], 1, 8)
        mr.toc(f"{c}:C11", t)
        res[c] = mr.run_condition(c, B[c], base[c], rb, scale, full_mode=False)
        res[c]["C11"] = mr.c11_value(traj_c, rb, list(range(NP)))
    # ---------------- oracle rows
    judge_t.join(timeout=300)
    oracle: dict[str, Any] = {"judge_error": judge_t.error, "judge_summary": judge_t.summary}
    try:
        if judge_t.result is not None:
            y = np.array([1 if (g.get("parse_ok") and g.get("declined") == 1) else (0 if g.get("parse_ok") else -1)
                          for g in judge_t.result])
            oracle["judged_refusal"] = y.tolist()
            oracle["grades"] = [{k: g.get(k) for k in ("declined", "engagement", "detail", "harm_score", "model",
                                                       "judge_fallback", "status")} for g in judge_t.result]
            ok = y >= 0
            oracle["readout_validity_auroc"] = auroc(base["plain"]["m"][ok], y[ok]) if ok.sum() > 2 else None
            oracle["n_refused"] = int((y == 1).sum())
            oracle["n_complied"] = int((y == 0).sum())
            oracle["judged_harm_refusal"] = float(np.mean(y[HARM_IDX][y[HARM_IDX] >= 0])) if (y[HARM_IDX] >= 0).any() else None
            oracle["judged_twin_refusal"] = float(np.mean(y[TWIN_IDX][y[TWIN_IDX] >= 0])) if (y[TWIN_IDX] >= 0).any() else None
            Do, oko = cf_rank_dirs(Rp, y, list(range(NP)), FOLDS, binary=True)
            defined_items = [i for i in range(2 * NP) if np.linalg.norm(Do[i, mr.B_late[0]]) > 0]
            oracle["ro_folds_defined"] = oko
            pc = res["plain"]
            # review fix (v2): the same >=2-items-per-class gate as C16_oracle (a single refused item made r^(o))
            n_pos, n_neg = int((y == 1).sum()), int((y == 0).sum())
            oracle["C16_oracle_direction"] = "in-sample mean(refused) - mean(complied) over all 16 items (not cross-fitted)"
            if n_pos < 2 or n_neg < 2:
                oracle["C1_oracle"] = cand(None, f"judged refusals {n_pos}/{n_pos + n_neg}: fewer than 2 items per class")
                oracle["C2_oracle"] = cand(None, oracle["C1_oracle"]["reason"])
            elif len(defined_items) >= 8:
                ev = defined_items
                proj = lambda Z, D_: np.mean(np.einsum("bld,bld->bl", Z, D_[:, mr.B_late, :]), 1)  # noqa: E731
                lp, lm = pc["C1"]["late_store"][EPS0]
                p0 = proj(Rp[:, mr.B_late, :], Do)
                s0 = sd(p0[ev])
                g = (proj(lp, Do) - proj(lm, Do)) / (2 * EPS0)
                oracle["C1_oracle"] = cand(float(np.mean(g[ev])) / s0 if s0 > 0 else None, None, n_items=len(ev))
                pr_ref = proj(pc["C2"]["late_ref"], Do)
                pr_abl = proj(pc["C2"]["late_abl"], Do)
                drop = pr_ref - pr_abl
                hh = [i for i in ev if IS_HARM[i]]
                tt = [i for i in ev if not IS_HARM[i]]
                s_r = sd(pr_ref[ev])
                oracle["C2_oracle"] = cand((float(drop[hh].mean() - drop[tt].mean()) / s_r) if (hh and tt and s_r > 0) else None,
                                           None if (hh and tt) else "one side has no defined oracle items")
            else:
                oracle["C1_oracle"] = cand(None, f"oracle direction defined for {len(defined_items)} items (<8): "
                                                 f"judged refusals {int((y == 1).sum())}/16")
                oracle["C2_oracle"] = cand(None, oracle["C1_oracle"]["reason"])
            yk = y[y >= 0]
            if (yk == 1).sum() >= 2 and (yk == 0).sum() >= 2 and not lite and mr.soft_ok("C16_oracle"):
                ro_full = unit(Rp[y == 1].mean(0) - Rp[y == 0].mean(0))
                t = mr.tic()
                c16o = mr.c16_block(B["plain"].with_items(list(range(2 * NP))), j, base["plain"]["full"][j - 1], ro_full,
                                    res["plain"]["ref_skip"]["m_ref"], scale, ALPHAS_VAR)
                mr.toc("oracle:C16", t)
                oracle["C16_oracle"] = cand(c16o["value"], c16o["undefined_reason"])
            else:
                oracle["C16_oracle"] = cand(None, "judged refusals do not give >=2 items per class" if not
                                            ((yk == 1).sum() >= 2 and (yk == 0).sum() >= 2) else "TIME_CAP")
        else:
            for k in ("C1_oracle", "C2_oracle", "C16_oracle"):
                oracle[k] = cand(None, f"judge unavailable: {judge_t.error}")
    except (RuntimeError, ValueError, IndexError, KeyError, TypeError, ZeroDivisionError) as e:
        logger.exception(f"{repo}: oracle block failed")
        oracle["block_error"] = f"{type(e).__name__}: {e}"
        for k in ("C1_oracle", "C2_oracle", "C16_oracle"):
            oracle.setdefault(k, cand(None, f"oracle block failed: {e}"))
    row["oracle"] = oracle
    # ---------------- constant-offset control
    if (repo in OFFSET_MODELS or smoke) and not lite and mr.soft_ok("offset_control"):
        try:
            row["offset_control"] = offset_control(mr, B["plain"], base["plain"], res["plain"], c11, rb, full_plain)
        except (RuntimeError, ValueError, IndexError, KeyError, TypeError) as e:
            logger.exception(f"{repo}: offset control failed")
            row["offset_control"] = {"error": f"{type(e).__name__}: {e}"}
            mr.flags.append({"code": "OFFSET_CONTROL_FAILED", "detail": str(e)[:300]})
    # ---------------- assemble
    row["conditions"] = {}
    cond_bars = {c: mr.bars(bc, list(range(2 * NP))) for c, bc in base.items()}
    for c, bc in base.items():
        row["conditions"][c] = {"margins": bc["m"], "mass": bc["mass"], "sd_margin": sd(bc["m"]), **cond_bars[c]}
    row["candidates"] = assemble(res, k8, oracle, c11, cond_bars)
    row["C1_linearity"] = res["plain"]["C1"]["linearity"]
    row["C1_linear_range_eps"] = res["plain"]["C1"]["linear_range_eps"]
    row["C1_nonlinear_at_primary"] = res["plain"]["C1"]["nonlinear_at_primary"]
    row["C3_F"] = {c: res[c]["C3"]["F"] for c in res}
    row["C9_true"] = {k: v for k, v in res["plain"]["C9_true"].items() if k not in ("m_ref", "m_patched")}
    row["C9_atp_vs_true_pearson"] = res["plain"].get("C9_atp_vs_true_pearson")
    row["C11_proj_plain"] = c11["proj"]
    row["ref_skip_consistency"] = {c: res[c]["ref_skip"]["max_abs_vs_base"] for c in res}
    row["diff_tokens"] = res["plain"]["diff_tokens"]
    row["c78_pairs_used"] = res["plain"]["c78_pairs_used"]
    row["timing"] = {**{k: round(v, 2) for k, v in mr.timing.items()},
                     "total_after_load_s": round(mr.elapsed(), 1)}
    row["candidate_seconds"] = {k: round(v, 2) for k, v in mr.cand_seconds.items()}
    row["flags"] = mr.flags
    row["compute"] = {"device": DEVICE.type,
                      "device_name": torch.cuda.get_device_name(0) if DEVICE.type == "cuda" else "cpu",
                      "torch": torch.__version__, "cuda": torch.version.cuda,
                      "transformers": transformers.__version__, "dtype": "bfloat16", "n_rand": N_RAND,
                      "alphas_variants": ALPHAS_VAR, "vram_cap_gb": (VRAM_CAP_GB if DEVICE.type == "cuda" else None),
                      "vram_peak_gb": (float(torch.cuda.max_memory_allocated()) / 1e9
                                       if DEVICE.type == "cuda" else None),
                      "n_threads": torch.get_num_threads(),
                      "torch_native_jit": ("disabled" if os.environ.get("TORCH_DISABLE_NATIVE_JIT") == "1"
                                           else "enabled")}
    mr.unload()
    return row


def assemble(res: dict, k8: dict, oracle: dict, c11: dict, cond_bars: dict) -> dict:
    """Per candidate: value (plain), pole values, null_p95, k8, oracle, extras."""
    pl = res["plain"]
    out: dict[str, Any] = {}

    def pole(c: str, key: str, sub: str = "value") -> float | None:
        if c not in res:
            return None
        v = res[c].get(key)
        if isinstance(v, dict):
            return fnum(v.get(sub))
        return None
    out["C1"] = {**cand(pl["C1"]["value"], pl["C1"]["undefined_reason"]), "raw": pl["C1"]["raw"],
                 "late": fnum(pl["C1"].get("late")), "harm_only": fnum(pl["C1"]["harm_only"]),
                 "twin_only": fnum(pl["C1"]["twin_only"]), "null_p95": pl["C1"].get("null_p95"),
                 "null_values": pl["C1"].get("null_values"),
                 "gain_by_eps": {e: v["gain"] for e, v in pl["C1"]["linearity"].items()}}
    out["C2"] = {**cand(pl["C2"]["value"], pl["C2"]["undefined_reason"]), "raw": pl["C2"]["raw"],
                 "null_p95": pl["C2"].get("null_p95"), "null_values": pl["C2"].get("null_values"),
                 "ratio_to_null_p95": fnum(pl["C2"].get("ratio_to_null_p95")),
                 "drop_harm_mean": pl["C2"]["drop_harm_mean"], "drop_twin_mean": pl["C2"]["drop_twin_mean"]}
    out["C3"] = {**cand(pl["C3"]["value"], pl["C3"]["undefined_reason"]), "depth": pl["C3"].get("depth"),
                 "sharp": pl["C3"].get("sharp"), "n_informative": pl["C3"]["n_informative"]}
    out["C7"] = dict(pl["C7"])
    out["C8"] = dict(pl["C8"])
    out["C9"] = {**cand(pl["C9"]["value"], pl["C9"]["undefined_reason"]), "per_pair": pl["C9"].get("per_pair"),
                 "true_patch_value": fnum(pl["C9_true"]["value"]),
                 "true_patch_reason": pl["C9_true"].get("undefined_reason"),
                 "atp_vs_true_pearson": pl.get("C9_atp_vs_true_pearson")}
    # review fix (v2): true-patching variants for the ATP_UNRELIABLE switch (poles, k8)
    for c in ("pole_refuse", "pole_comply"):
        tv = res.get(c, {}).get("C9_true") if c in res else None
        out["C9"][f"true_patch_{c}"] = fnum(tv["value"]) if isinstance(tv, dict) else None
        out["C9"][f"true_patch_{c}_reason"] = (tv.get("undefined_reason") if isinstance(tv, dict)
                                                else "condition not run (ANCHOR_LITE or TIME_CAP)")
    tk = k8.get("C9_true")
    out["C9"]["true_patch_k8"] = tk["value"] if tk else None
    out["C9"]["true_patch_k8_reason"] = tk["reason"] if tk else "not computed (TIME_CAP, ANCHOR_LITE or K8_BLOCK_FAILED)"
    out["C11"] = {**cand(c11["value"], c11["undefined_reason"]), "slope_diff": c11["slope_diff"],
                  "plateau_harm": c11["plateau_harm"], "plateau_twin": c11["plateau_twin"]}
    out["C16"] = {**cand(pl["C16"]["value"], pl["C16"]["undefined_reason"]), "raw_slope": pl["C16"]["raw_slope"],
                  "harm_slope": pl["C16"]["harm_slope"], "twin_slope": pl["C16"]["twin_slope"]}
    out["logit_gap"] = cand(pl["bars"]["logit_gap"])
    out["refusal_mass"] = cand(pl["bars"]["refusal_mass"])
    out["logit_gap_level"] = cand(pl["bars"]["logit_gap_level"])
    out["refusal_mass_level"] = cand(pl["bars"]["refusal_mass_level"])
    for key in ("C1", "C2", "C3", "C7", "C8", "C9", "C11", "C16"):
        for c in ("pole_refuse", "pole_comply"):
            out[key][c] = pole(c, key)
            if c in res and isinstance(res[c].get(key), dict):
                out[key][c + "_reason"] = (res[c][key].get("undefined_reason") or res[c][key].get("reason"))
        kv = k8.get(key)
        out[key]["k8"] = kv["value"] if kv else None
        out[key]["k8_reason"] = kv["reason"] if kv else "not computed (TIME_CAP, ANCHOR_LITE or K8_BLOCK_FAILED; see flags)"
    for key in ("logit_gap", "refusal_mass", "logit_gap_level", "refusal_mass_level"):
        for c in ("pole_refuse", "pole_comply"):
            out[key][c] = cond_bars[c][key] if c in cond_bars else None
        out[key]["k8"] = k8["bars"][key] if "bars" in k8 else None
    for key, ok in (("C1", "C1_oracle"), ("C2", "C2_oracle"), ("C16", "C16_oracle")):
        out[key]["oracle"] = oracle.get(ok, {}).get("value")
        out[key]["oracle_reason"] = oracle.get(ok, {}).get("reason")
    return out


def offset_control(mr: ModelRun, b: Batch, base: dict, pc: dict, c11: dict, rb: np.ndarray,
                   full_layers: list[int]) -> dict:
    """Add c = 2*mean||x|| * u at ALL positions of the first B_late layer; recompute reads."""
    t = mr.tic()
    lo = mr.B_late[0]
    u = unit(np.random.default_rng(SEED + 99).standard_normal(mr.d)).astype(np.float32)
    cn = 2.0 * float(np.mean(np.linalg.norm(base["R"][:, lo, :], axis=1)))
    cvec = torch.from_numpy(cn * u).to(DEVICE)
    off = [(lo, lambda h: (h.float() + cvec).to(h.dtype))]
    bo = mr.base_pass(b, full_layers, want_attn=False, extra_fns=off)
    bo["cache"].crop(b.T - 1)  # review fix (v2): base_pass leaves the last prompt token cached
    bars_o = mr.bars(bo, list(range(2 * NP)))
    D = pc["_D"]
    c1o = mr.c1_block(b, bo, D, list(range(2 * NP)), [EPS0], rb, None, extra_fns=off)
    j = mr.B_mid[0]
    bi = b.with_items(list(range(2 * NP)))
    m_ref, _ = mr.skip_call(bi, j, bo["full"][j - 1], off, capture_late=False)
    c2o = mr.c2_block(bi, j, bo["full"][j - 1], D, m_ref, None, extra_fns=off)
    c3o = mr.c3_block(b, bo, list(range(NP)), extra_fns=off)
    _, traj_o, _ = mr.generate(b, bo, 1, 8, extra_fns=off)
    c11o = mr.c11_value(traj_o, rb, list(range(NP)))
    late_level = lambda R_: float(np.mean(np.einsum("bld,ld->bl", R_[:, mr.B_late, :], rb[mr.B_late])))  # noqa: E731
    reads = {
        "C1": (pc["C1"]["value"], c1o["value"]), "C2": (pc["C2"]["value"], c2o["value"]),
        "C3": (pc["C3"]["value"], c3o["value"]), "C11": (c11["value"], c11o["value"]),
        "logit_gap": (pc["bars"]["logit_gap"], bars_o["logit_gap"]),
        "mean_harmful_margin_level": (pc["bars"]["logit_gap_level"], bars_o["logit_gap_level"]),
        "mean_late_projection_on_rb_level": (late_level(base["R"]), late_level(bo["R"])),
    }
    out = {"offset_layer": lo, "offset_norm": cn, "u_seed": SEED + 99, "reads": {}}
    for k, (a, b_) in reads.items():
        a, b_ = fnum(a), fnum(b_)
        rel = (abs(b_ - a) / abs(a)) if (a is not None and b_ is not None and abs(a) > 1e-9) else None
        out["reads"][k] = {"without": a, "with": b_, "rel_change": rel,
                           "kind": "level" if "level" in k else "across-item/causal"}
    mr.toc("offset_control", t)
    del bo
    return out


# ----------------------------------------------------------------------------- driver
def panel_order(repos: list[str]) -> list[str]:
    hub = Path(os.environ.get("HF_HUB_CACHE", ""))
    cached = set()
    for r in repos:
        snaps = hub / f"models--{r.replace('/', '--')}" / "snapshots"
        if snaps.exists() and any(list(s.glob("*.safetensors")) for s in snaps.iterdir()):
            cached.add(r)

    def key(r: str) -> tuple:
        lab = LABELS.get(r, {})
        return (0 if lab.get("BALANCED") is not None else 1, 0 if r in cached else 1,
                PANEL.get(r, {}).get("n_params") or 9e9)
    return sorted(repos, key=key)


def load_skips() -> list[dict]:
    p = WS / "skips.json"
    return json.loads(p.read_text()) if p.exists() else []


def add_skip(repo: str, code: str, detail: str) -> None:
    sk = [s for s in load_skips() if s["repo"] != repo]
    sk.append({"repo": repo, "code": code, "detail": detail[:2000], "time": time.strftime("%H:%M:%S")})
    atomic_write(WS / "skips.json", sk)


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos", default="")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--max-models", type=int, default=999)
    ap.add_argument("--ram-gb", type=float, default=9.0)
    ap.add_argument("--lite", action="store_true", help="anchor-lite mode (see ANCHOR_LITE flag)")
    ap.add_argument("--soft-cap", type=float, default=None, help="override PREREG soft cap (s); recorded as a flag")
    ap.add_argument("--hard-cap", type=float, default=None, help="override PREREG hard cap (s); recorded as a flag")
    ap.add_argument("--allow-base", action="store_true", help="allow the base stratum (plain renderer; no correlations)")
    a = ap.parse_args()
    global SOFT_CAP, HARD_CAP, CAP_OVERRIDE
    if a.soft_cap is not None or a.hard_cap is not None:
        SOFT_CAP = float(a.soft_cap) if a.soft_cap is not None else SOFT_CAP
        HARD_CAP = float(a.hard_cap) if a.hard_cap is not None else HARD_CAP
        CAP_OVERRIDE = {"code": "TIME_CAP_OVERRIDE", "soft_s": SOFT_CAP, "hard_s": HARD_CAP,
                        "prereg_soft_s": float(PREREG["time_caps"]["soft_s"]),
                        "prereg_hard_s": float(PREREG["time_caps"]["hard_s"])}
        logger.warning(f"time caps overridden: {CAP_OVERRIDE}")
    if DEVICE.type == "cuda":
        # an address-space rlimit breaks CUDA initialisation, so the RAM guard is replaced by the
        # per-process VRAM fraction cap below; kept on CPU exactly as before.
        total_vram_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
        torch.cuda.set_per_process_memory_fraction(VRAM_CAP_GB / total_vram_gb)
        logger.info(f"CUDA device {torch.cuda.get_device_name(0)}: {total_vram_gb:.1f} GB total, "
                    f"capped at {VRAM_CAP_GB} GB ({VRAM_CAP_GB / total_vram_gb:.3f} fraction)")
    else:
        resource.setrlimit(resource.RLIMIT_AS, (int(a.ram_gb * 3 * 1e9), int(a.ram_gb * 3 * 1e9)))
    sub = PREREG["cpu_subpanel"]
    repos = [r for r in a.repos.split(",") if r] if a.repos else sub
    for r in repos:
        pr = PANEL.get(r, {})
        ok_strata = ("chat", None, "base") if a.allow_base else ("chat", None)
        if pr.get("sealed") or pr.get("stratum") not in ok_strata:
            raise RuntimeError(f"{r} not a non-sealed chat panel row (use --allow-base for the base stratum)")
    # the panel rows that are NOT in the CPU sub-panel are recorded once as skips
    if not a.smoke and not a.repos:
        for r, pr in PANEL.items():
            if r not in sub and not pr.get("sealed"):
                if not any(s["repo"] == r for s in load_skips()):
                    add_skip(r, "NOT_IN_CPU_SUBPANEL", "LIVE_TIER_NO_CUDA: panel restricted to CPU_SUBPANEL "
                             f"(n_params={pr.get('n_params')}, stratum={pr.get('stratum')})")
    order = panel_order(repos)
    logger.info(f"order ({len(order)}): {order}")
    done = 0
    for repo in order:
        if done >= a.max_models:
            break
        out_p = ROWS / f"{slug(repo)}.json"
        if out_p.exists() and not a.smoke:
            logger.info(f"skip (row exists): {repo}")
            continue
        t0 = time.time()
        try:
            row = measure(repo, smoke=a.smoke, lite=a.lite)
            row["wall_s"] = round(time.time() - t0, 1)
            atomic_write(out_p if not a.smoke else WS / "scratch" / f"smoke_{slug(repo)}.json", row)
            logger.info(f"DONE {repo} in {row['wall_s']}s  C1={row['candidates']['C1']['value']} "
                        f"C2={row['candidates']['C2']['value']} C3={row['candidates']['C3']['value']} "
                        f"C11={row['candidates']['C11']['value']} gap={row['candidates']['logit_gap']['value']:.3f}")
            done += 1
        except SealedRepoError as e:
            add_skip(repo, "SEALED", str(e))
            raise
        except TimeoutError as e:
            logger.error(f"{repo}: {e}")
            add_skip(repo, "TIMEOUT", str(e))
        except MemoryError as e:
            logger.error(f"{repo}: OOM {e}")
            add_skip(repo, "OOM", traceback.format_exc())
        except RuntimeError as e:
            msg = str(e)
            code = ("DOWNLOAD_FAIL" if "DOWNLOAD_FAIL" in msg else "ARCH_UNSUPPORTED" if "ARCH_UNSUPPORTED" in msg
                    else "OOM" if "memory" in msg.lower() else "LOAD_FAIL")
            logger.error(f"{repo}: {code}: {msg[:300]}")
            add_skip(repo, code, traceback.format_exc())
        except Exception as e:  # noqa: BLE001 - every failure is recorded in skips.json, nothing dropped silently
            logger.exception(f"{repo}: unexpected failure")
            add_skip(repo, "LOAD_FAIL" if "load" in str(e).lower() else "RUN_FAIL", traceback.format_exc())
        finally:
            import gc
            gc.collect()


if __name__ == "__main__":
    main()
