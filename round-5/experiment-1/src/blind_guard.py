"""Set A blindness guard (plan Step 7, test T7).

While Set A candidate values are measured, frozen and analysed, no code path in this workspace may open a file
under RUN/iter_5/gen_art/*dataset* (the sibling artifact that grades Set A), except a Set B declaration file whose
name matches (?i)set_?b.*\\.json. `install()` enforces this for the whole process in two layers:

  1. sys.addaudithook: the "open" audit event fires for builtins.open, io.open, os.open, pathlib and every C-level
     open, BEFORE the file is touched, so a forbidden open raises BlindnessViolation even if the file exists.
     Audit hooks cannot be removed, so the guard stays on for the life of the process.
  2. explicit wrappers of builtins.open / io.open / pathlib.Path.open / read_text / read_bytes (belt and braces,
     and what the plan names).

Directory listings (os.scandir / glob / os.stat) are NOT opens, so the freeze certificate can list names, sizes and
mtimes of the sibling workspace without reading any content.
"""
from __future__ import annotations

import builtins
import fnmatch
import io
import os
import pathlib
import re
import sys

RUN = pathlib.Path("/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop")
GEN_ART = RUN / "iter_5" / "gen_art"
ALLOWED_NAME = re.compile(r"(?i)set_?b.*\.json$")
_INSTALLED = False
N_CHECKED = {"opens_checked": 0, "blocked": 0}


class BlindnessViolation(RuntimeError):
    """A code path tried to read the Set A grading workspace."""


def is_forbidden(path: object) -> bool:
    """True if `path` lies under RUN/iter_5/gen_art/<*dataset*>/ and is not a Set B declaration file."""
    if isinstance(path, int):  # a raw file descriptor carries no path
        return False
    try:
        p = os.fspath(path)  # type: ignore[arg-type]
    except TypeError:
        return False
    if isinstance(p, bytes):
        p = p.decode("utf-8", "replace")
    ap = os.path.abspath(p)
    root = str(GEN_ART) + os.sep
    if not ap.startswith(root):
        return False
    first = ap[len(root):].split(os.sep, 1)[0]
    if not fnmatch.fnmatch(first, "*dataset*"):
        return False
    return not ALLOWED_NAME.search(os.path.basename(ap))


def _check(path: object) -> None:
    N_CHECKED["opens_checked"] += 1
    if is_forbidden(path):
        N_CHECKED["blocked"] += 1
        raise BlindnessViolation(f"blindness guard: refusing to open {path!s} (Set A grading workspace)")


def _audit(event: str, args: tuple) -> None:
    if event == "open" and args:
        _check(args[0])


def install() -> None:
    """Idempotent; call once at import time of every script that measures or analyses candidate values."""
    global _INSTALLED
    if _INSTALLED:
        return
    sys.addaudithook(_audit)
    _orig_open = builtins.open

    def guarded_open(file, *a, **k):  # noqa: ANN001
        _check(file)
        return _orig_open(file, *a, **k)
    builtins.open = guarded_open
    io.open = guarded_open  # type: ignore[assignment]
    _p_open, _p_rt, _p_rb = pathlib.Path.open, pathlib.Path.read_text, pathlib.Path.read_bytes

    def p_open(self, *a, **k):  # noqa: ANN001
        _check(self)
        return _p_open(self, *a, **k)

    def p_read_text(self, *a, **k):  # noqa: ANN001
        _check(self)
        return _p_rt(self, *a, **k)

    def p_read_bytes(self, *a, **k):  # noqa: ANN001
        _check(self)
        return _p_rb(self, *a, **k)
    pathlib.Path.open = p_open  # type: ignore[method-assign]
    pathlib.Path.read_text = p_read_text  # type: ignore[method-assign]
    pathlib.Path.read_bytes = p_read_bytes  # type: ignore[method-assign]
    _INSTALLED = True


def installed() -> bool:
    return _INSTALLED
