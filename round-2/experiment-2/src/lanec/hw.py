"""Hardware detection and memory budgets (aii-use-hardware conventions)."""
from __future__ import annotations

import math
import os
import resource
import shutil
from pathlib import Path
from typing import Any

from loguru import logger


def detect_cpus() -> int:
    """Actual CPU allocation: cgroup v2 quota, then v1, then affinity, then os.cpu_count."""
    try:
        parts = Path("/sys/fs/cgroup/cpu.max").read_text().split()
        if parts[0] != "max":
            return max(1, math.ceil(int(parts[0]) / int(parts[1])))
    except (FileNotFoundError, ValueError, IndexError, PermissionError):
        pass
    try:
        q = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us").read_text())
        p = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us").read_text())
        if q > 0:
            return max(1, math.ceil(q / p))
    except (FileNotFoundError, ValueError, PermissionError):
        pass
    try:
        return len(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        pass
    return os.cpu_count() or 1


def container_ram_gb() -> float | None:
    for p in ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
        try:
            v = Path(p).read_text().strip()
            if v != "max" and int(v) < 1_000_000_000_000:
                return int(v) / 1e9
        except (FileNotFoundError, ValueError, PermissionError):
            pass
    return None


def probe() -> dict[str, Any]:
    """Measure the pod BEFORE sizing anything. Never trusts host values blindly."""
    import psutil

    info: dict[str, Any] = {
        "n_cpus": detect_cpus(),
        "host_cpu_count": os.cpu_count(),
        "ram_total_gb": round(container_ram_gb() or psutil.virtual_memory().total / 1e9, 2),
        "ram_available_gb": round(psutil.virtual_memory().available / 1e9, 2),
        "cgroup_limited": container_ram_gb() is not None,
    }
    for label, path in (("root", "/"), ("hf_cache", os.environ.get("HF_HOME", "/"))):
        try:
            du = shutil.disk_usage(path)
            info[f"disk_{label}_total_gb"] = round(du.total / 1e9, 1)
            info[f"disk_{label}_free_gb"] = round(du.free / 1e9, 1)
        except OSError:
            info[f"disk_{label}_free_gb"] = None
    try:
        import torch

        info["torch_version"] = torch.__version__
        info["has_gpu"] = bool(torch.cuda.is_available())
        if info["has_gpu"]:
            props = torch.cuda.get_device_properties(0)
            info["gpu_name"] = props.name
            info["vram_total_gb"] = round(props.total_memory / 1e9, 2)
            free_b, total_b = torch.cuda.mem_get_info(0)
            info["vram_free_gb"] = round(free_b / 1e9, 2)
            info["cuda_capability"] = f"{props.major}.{props.minor}"
        else:
            info["vram_total_gb"] = 0.0
    except ImportError:
        info["has_gpu"] = False
        info["vram_total_gb"] = 0.0
    return info


def set_budgets(ram_budget_gb: float, vram_fraction: float = 0.92) -> None:
    """Fail fast with a catchable error instead of being OOM-killed."""
    import psutil

    avail = psutil.virtual_memory().available
    budget_b = int(ram_budget_gb * 1e9)
    if budget_b >= avail:
        budget_b = int(avail * 0.85)
        logger.warning(f"RAM budget clipped to {budget_b/1e9:.1f}GB (available {avail/1e9:.1f}GB)")
    # 3x: virtual address space exceeds RSS, especially with CUDA's reservations.
    try:
        resource.setrlimit(resource.RLIMIT_AS, (budget_b * 3, budget_b * 3))
        logger.info(f"RLIMIT_AS set to {budget_b*3/1e9:.1f}GB virtual ({budget_b/1e9:.1f}GB target RSS)")
    except (ValueError, OSError) as exc:
        logger.warning(f"Could not set RLIMIT_AS: {exc}")
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.set_per_process_memory_fraction(min(vram_fraction, 0.95))
            logger.info(f"VRAM fraction capped at {min(vram_fraction, 0.95):.2f}")
    except (ImportError, RuntimeError) as exc:
        logger.warning(f"Could not cap VRAM: {exc}")


def free_disk_gb(path: str | None = None) -> float:
    return shutil.disk_usage(path or os.environ.get("HF_HOME", "/")).free / 1e9
