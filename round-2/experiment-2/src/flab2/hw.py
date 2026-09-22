#!/usr/bin/env python3
"""Container-aware resource limits.

This box reports 755 GB of RAM through `free` and 2.2 PB of disk, but it is a
DOCKER CONTAINER under cgroup v2 with a 14 GB memory limit.  Reading the host
values instead of the cgroup is the single most expensive mistake available
here: exceeding the cgroup limit is an OOM kill of the whole container, which
takes every running stage with it and cannot be caught.
"""

from __future__ import annotations

import math
import os
import resource
from pathlib import Path


def container_ram_bytes() -> int | None:
    """The cgroup memory limit, or None when unlimited / not containerised."""
    for p in ("/sys/fs/cgroup/memory.max",
              "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
        try:
            v = Path(p).read_text().strip()
            if v != "max" and int(v) < 10**12:
                return int(v)
        except (FileNotFoundError, ValueError, PermissionError):
            continue
    return None


def container_ram_current() -> int | None:
    """Current cgroup memory charge, INCLUDING reclaimable page cache."""
    for p in ("/sys/fs/cgroup/memory.current",
              "/sys/fs/cgroup/memory/memory.usage_in_bytes"):
        try:
            return int(Path(p).read_text().strip())
        except (FileNotFoundError, ValueError, PermissionError):
            continue
    return None


def detect_cpus() -> int:
    """CPU allocation from the cgroup quota, then affinity, then os.cpu_count."""
    try:
        parts = Path("/sys/fs/cgroup/cpu.max").read_text().split()
        if parts[0] != "max":
            return max(1, math.ceil(int(parts[0]) / int(parts[1])))
    except (FileNotFoundError, ValueError, PermissionError):
        pass
    try:
        return max(1, len(os.sched_getaffinity(0)))
    except (AttributeError, OSError):
        pass
    return os.cpu_count() or 1


def cap_address_space(fraction: float = 0.45) -> dict:
    """Cap this process's address space at a FRACTION of the container limit.

    Three stages share one 14 GB container here, so no single stage may claim
    more than a fraction of it.  RLIMIT_AS raises a catchable MemoryError at the
    boundary instead of letting the kernel kill the container, which turns an
    unrecoverable loss of every stage into one failed cell.
    """
    total = container_ram_bytes()
    info = {"cgroup_limit_bytes": total, "applied": False,
            "cpus": detect_cpus(), "current_bytes": container_ram_current()}
    if not total:
        return info
    budget = int(total * fraction)
    try:
        soft, hard = resource.getrlimit(resource.RLIMIT_AS)
        new_hard = hard if hard != resource.RLIM_INFINITY else budget
        resource.setrlimit(resource.RLIMIT_AS, (budget, max(budget, new_hard)))
        info.update({"applied": True, "budget_bytes": budget,
                     "budget_gb": round(budget / 1e9, 2)})
    except (ValueError, OSError) as exc:
        info["error"] = f"{type(exc).__name__}: {exc}"
    return info
