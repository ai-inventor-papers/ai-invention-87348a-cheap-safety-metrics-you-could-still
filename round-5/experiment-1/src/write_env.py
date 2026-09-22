#!/usr/bin/env python3
"""write_env.py -- record the compute environment of the CURRENT session into env.json (plan step 0).

env.json keeps one entry per session, because this artifact ran across four pods:
  sessions 1-3 were CPU-only (LIVE_TIER_NO_CUDA), and session 4 got an NVIDIA L4.
The top-level keys describe the session that produced the final rows/ (the latest session).
Re-running the script replaces the entry for the same session id instead of appending a duplicate.

Usage: venv_gpu/bin/python write_env.py --session 4 [--note "..."]
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import time
from pathlib import Path

WS = Path(__file__).resolve().parent


def cgroup_cpus() -> float | None:
    for p, per in (("/sys/fs/cgroup/cpu.max", None), ("/sys/fs/cgroup/cpu/cpu.cfs_quota_us",
                                                        "/sys/fs/cgroup/cpu/cpu.cfs_period_us")):
        try:
            if per is None:
                q, prd = Path(p).read_text().split()
                if q != "max":
                    return int(q) / int(prd)
            else:
                q = int(Path(p).read_text())
                if q > 0:
                    return q / int(Path(per).read_text())
        except (OSError, ValueError):
            continue
    return None


def cgroup_mem_gb() -> float | None:
    for p in ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
        try:
            v = Path(p).read_text().strip()
            if v != "max" and int(v) < 1 << 60:
                return int(v) / 1e9
        except (OSError, ValueError):
            continue
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", type=int, required=True)
    ap.add_argument("--note", default="")
    a = ap.parse_args()
    import torch
    import transformers
    cuda = torch.cuda.is_available()
    ent = {
        "session": a.session,
        "start_time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cuda": cuda,
        "device_name": torch.cuda.get_device_name(0) if cuda else None,
        "vram_total_gb": round(torch.cuda.get_device_properties(0).total_memory / 1e9, 2) if cuda else None,
        "vram_cap_gb": float(os.environ.get("GPU_VRAM_CAP_GB", 10.0)) if cuda else None,
        "torch": torch.__version__, "torch_cuda": torch.version.cuda, "transformers": transformers.__version__,
        "python": platform.python_version(),
        "nproc_affinity": len(os.sched_getaffinity(0)),
        "cgroup_cpus": cgroup_cpus(),
        "ram_limit_gb_cgroup": cgroup_mem_gb(),
        "git_sha": None,
        "note": a.note,
    }
    try:
        ent["nvidia_smi"] = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version,memory.total",
                                            "--format=csv,noheader"], capture_output=True, text=True,
                                           timeout=20).stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        ent["nvidia_smi"] = None
    p = WS / "env.json"
    env = json.loads(p.read_text()) if p.exists() else {"sessions": []}
    env["sessions"] = [s for s in env.get("sessions", []) if s.get("session") != a.session] + [ent]
    env["sessions"].sort(key=lambda s: s["session"])
    latest = env["sessions"][-1]
    env.update({k: v for k, v in latest.items() if k != "note"})
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(env, indent=1))
    os.replace(tmp, p)
    print(json.dumps(latest, indent=1))


if __name__ == "__main__":
    main()
