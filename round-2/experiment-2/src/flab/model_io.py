"""Checkpoint loading, VRAM budgeting and weight snapshot/restore.

The GPU on this worker is SHARED with sibling artifacts, so free VRAM is measured
at load time rather than assumed, and the weight pass falls back to CPU when the
card is busy -- the weight pass needs no forward pass at all, so nothing is lost
but wall-clock.
"""

from __future__ import annotations

import gc
import json
import os
import shutil
import time
from pathlib import Path

import torch
from loguru import logger

MODELS_ROOT = Path(os.environ.get("HF_HOME", "/tmp")) / "models"
# safetensors loads by MEMORY MAPPING. The run directory is a FUSE network volume,
# where sequential reads are fast (~420 MB/s) but mmap page faults are per-page
# round trips and a 0.6B load stalls for minutes at ~3% CPU. Checkpoints are
# therefore STAGED to local disk before loading, and staged copies are deleted
# as soon as the checkpoint is done with.
STAGE_ROOT = Path(os.environ.get("FLAB_STAGE_DIR", "/var/flab_models"))


def local_dir(repo: str) -> Path:
    return MODELS_ROOT / repo.replace("/", "__")


def stage_local(path: str | Path, keep_free_gb: float = 6.0) -> Path:
    """Copy a checkpoint directory to local disk so mmap does not go over FUSE."""
    src = Path(path)
    if str(src).startswith(str(STAGE_ROOT)):
        return src
    STAGE_ROOT.mkdir(parents=True, exist_ok=True)
    dst = STAGE_ROOT / src.name
    need = sum(f.stat().st_size for f in src.rglob("*") if f.is_file()) / 2**30
    if dst.exists() and _dir_size_gb(dst) >= need * 0.98:
        return dst
    free = shutil.disk_usage(STAGE_ROOT).free / 2**30
    if free - need < keep_free_gb:
        for old in sorted(STAGE_ROOT.iterdir(), key=lambda q: q.stat().st_mtime):
            if old.is_dir() and old != dst:
                shutil.rmtree(old, ignore_errors=True)
                if shutil.disk_usage(STAGE_ROOT).free / 2**30 - need >= keep_free_gb:
                    break
    t0 = time.time()
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst)
    logger.info(f"staged {src.name} ({need:.1f} GB) to local disk in {time.time() - t0:.1f}s")
    return dst


def _dir_size_gb(d: Path) -> float:
    return sum(f.stat().st_size for f in d.rglob("*") if f.is_file()) / 2**30


def unstage(path: str | Path) -> None:
    p = Path(path)
    if str(p).startswith(str(STAGE_ROOT)):
        shutil.rmtree(p, ignore_errors=True)


def free_vram_gb() -> float:
    if not torch.cuda.is_available():
        return 0.0
    free, _total = torch.cuda.mem_get_info()
    return free / 2**30


def weight_pass_device(min_free_gb: float = 4.0) -> str:
    """Where to run the weight pass. The weight pass needs NO forward pass, so
    forcing it to CPU costs only wall-clock and frees the shared GPU entirely --
    which is what lets the panel run concurrently with the ladder."""
    override = os.environ.get("FLAB_WEIGHT_DEVICE")
    if override:
        return override
    return "cuda" if free_vram_gb() >= min_free_gb else "cpu"


def load_model(path: str | Path, *, dtype=torch.bfloat16, device: str = "cuda",
               attn: str | None = None):
    """Load a checkpoint in bf16 with transformers. NEVER GGUF/llama.cpp -- they hide
    exactly the activations and weights this study reads."""
    from transformers import AutoModelForCausalLM, AutoTokenizer

    t0 = time.time()
    path = stage_local(path)
    tok = AutoTokenizer.from_pretrained(path, trust_remote_code=False)
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "left"
    kw = {"dtype": dtype}
    if attn:
        kw["attn_implementation"] = attn
    model = AutoModelForCausalLM.from_pretrained(path, **kw)
    model.to(device)
    model.eval()
    model.config.use_cache = True
    logger.info(f"loaded {path} -> {device} in {time.time() - t0:.1f}s "
                f"(free VRAM {free_vram_gb():.1f} GB)")
    return model, tok


def unload(*objs) -> None:
    for o in objs:
        del o
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def card_text(path: str | Path) -> str:
    p = Path(path) / "README.md"
    return p.read_text(errors="ignore") if p.exists() else ""


class WeightSnapshot:
    """Snapshot selected module weights to CPU and restore them on exit.

    Used so a weight-editing rung can be applied IN MEMORY and undone without
    writing 8 GB per rung to disk.
    """

    def __init__(self, model, modules=("o_proj", "down_proj")):
        from flab.harvest import _get_layers, _get_module_weight

        self.model = model
        self.saved: list[tuple] = []
        for li, layer in enumerate(_get_layers(model)):
            for mod in modules:
                W = _get_module_weight(layer, mod)
                if W is not None:
                    self.saved.append((W, W.detach().to("cpu", copy=True)))

    def __enter__(self):
        return self

    @torch.no_grad()
    def restore(self) -> None:
        for W, cpu in self.saved:
            W.copy_(cpu.to(W.device))

    def __exit__(self, *exc):
        self.restore()
        self.saved.clear()
        gc.collect()
        return False


def state_keys_shapes(model) -> dict[str, tuple]:
    return {k: tuple(v.shape) for k, v in model.state_dict().items()}


def assert_disk(min_gb: float, path: str = "/") -> None:
    free = shutil.disk_usage(path).free / 2**30
    if free < min_gb:
        raise RuntimeError(f"free disk {free:.1f} GB < required {min_gb} GB at {path}")


def repo_meta(repo: str, token: str | None = None) -> dict:
    """RE-VERIFY EVERY REPO LIVE before downloading: gated status changes."""
    import requests

    tok = token or os.environ.get("HF_TOKEN", "")
    h = {"Authorization": f"Bearer {tok}"} if tok else {}
    r = requests.get(f"https://huggingface.co/api/models/{repo}", headers=h, timeout=60)
    if r.status_code != 200:
        return {"repo": repo, "status": r.status_code, "available": False}
    j = r.json()
    return {
        "repo": repo, "status": 200, "available": True,
        "gated": j.get("gated"), "sha": j.get("sha"),
        "safetensors_bytes": sum(s.get("size") or 0 for s in j.get("siblings", [])
                                 if s["rfilename"].endswith(".safetensors")),
        "model_type": (j.get("config") or {}).get("model_type"),
    }
