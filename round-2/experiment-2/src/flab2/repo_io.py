#!/usr/bin/env python3
"""Repository-level I/O: read a HuggingFace checkpoint WITHOUT instantiating it.

Two deliberate design choices, both forced by what killed iteration 1.

1. NO MMAP.  `safetensors.safe_open` memory-maps the file, and mmap over the
   FUSE/MooseFS mount this workspace lives on stalls.  The header format is
   simple and stable, so this module parses it with ordinary buffered reads and
   `np.frombuffer` on bytes it has explicitly read.  Nothing is mapped.

2. NO MODEL CLASS.  Iteration 1 lost 15 of 32 panel repositories because the
   installed `transformers` had no class for their `model_type`.  Every read
   here is by TENSOR NAME, so a checkpoint whose architecture `transformers`
   has never heard of is still fully auditable.  That is not a workaround: it
   is the correct threat model, because an auditor who can only read
   architectures their library already supports is not a blind auditor.
"""

from __future__ import annotations

import json
import re
import struct
from dataclasses import dataclass
from pathlib import Path

import numpy as np

# safetensors dtype -> (numpy dtype, itemsize).  bfloat16 has no numpy dtype, so
# it is read as uint16 and widened by shifting into the high half of a float32,
# which is exact (bf16 IS the top 16 bits of fp32).
_ST_DTYPES: dict[str, str] = {
    "F64": "f8", "F32": "f4", "F16": "f2", "BF16": "bf16",
    "I64": "i8", "I32": "i4", "I16": "i2", "I8": "i1",
    "U8": "u1", "BOOL": "?",
}

_O_PROJ_RE = re.compile(r"(?:^|\.)layers\.(\d+)\..*\bo_proj\.weight$")
_DOWN_PROJ_RE = re.compile(r"(?:^|\.)layers\.(\d+)\..*\bdown_proj\.weight$")
# fallbacks for architectures that name the residual-write matrices differently
_ATTN_OUT_ALT = [
    re.compile(r"(?:^|\.)layers\.(\d+)\..*\battention\.(?:wo|dense|out_proj)\.weight$"),
    re.compile(r"(?:^|\.)h\.(\d+)\..*\battn\.(?:c_proj|out_proj|dense)\.weight$"),
    re.compile(r"(?:^|\.)layers\.(\d+)\..*\bself_attn\.dense\.weight$"),
]
_MLP_OUT_ALT = [
    re.compile(r"(?:^|\.)layers\.(\d+)\..*\bfeed_forward\.w2\.weight$"),
    re.compile(r"(?:^|\.)h\.(\d+)\..*\bmlp\.(?:c_proj|fc2|down_proj)\.weight$"),
    re.compile(r"(?:^|\.)layers\.(\d+)\..*\bmlp\.(?:fc2|c_proj)\.weight$"),
]


@dataclass
class TensorRef:
    """Where one tensor lives, without having read it."""

    name: str
    file: Path
    dtype: str
    shape: tuple[int, ...]
    begin: int          # byte offset within the data section
    end: int
    data_start: int     # byte offset of the data section within the file

    @property
    def nbytes(self) -> int:
        return self.end - self.begin


def read_st_header(path: Path) -> tuple[dict, int]:
    """Parse a .safetensors header with ordinary reads. Returns (header, data_start)."""
    with path.open("rb") as fh:
        raw = fh.read(8)
        if len(raw) != 8:
            raise ValueError(f"{path}: truncated safetensors header length")
        (n,) = struct.unpack("<Q", raw)
        if n <= 0 or n > 400_000_000:
            raise ValueError(f"{path}: implausible header length {n}")
        head = json.loads(fh.read(n).decode("utf-8"))
    return head, 8 + n


def build_index(snapshot: Path) -> dict[str, TensorRef]:
    """Map every tensor name in a checkpoint to a TensorRef.

    Handles both the single-file and the sharded (`*.index.json`) layouts.  This
    index IS the key/shape screen's input: no weights are read to build it.
    """
    files = sorted(snapshot.glob("*.safetensors"))
    if not files:
        raise FileNotFoundError(f"no .safetensors under {snapshot}")
    index: dict[str, TensorRef] = {}
    for f in files:
        real = f.resolve()
        head, data_start = read_st_header(real)
        for name, meta in head.items():
            if name == "__metadata__":
                continue
            b, e = meta["data_offsets"]
            index[name] = TensorRef(
                name=name,
                file=real,
                dtype=meta["dtype"],
                shape=tuple(int(x) for x in meta["shape"]),
                begin=int(b),
                end=int(e),
                data_start=data_start,
            )
    return index


def read_tensor(ref: TensorRef) -> np.ndarray:
    """Read one tensor as float32 (or its native integer dtype). No mmap."""
    with ref.file.open("rb") as fh:
        fh.seek(ref.data_start + ref.begin)
        buf = fh.read(ref.nbytes)
    if len(buf) != ref.nbytes:
        raise ValueError(f"{ref.name}: short read {len(buf)} != {ref.nbytes}")
    kind = _ST_DTYPES.get(ref.dtype)
    if kind is None:
        raise ValueError(f"{ref.name}: unsupported dtype {ref.dtype}")
    if kind == "bf16":
        u = np.frombuffer(buf, dtype="<u2").astype(np.uint32) << 16
        a = u.view(np.float32)
    else:
        a = np.frombuffer(buf, dtype=np.dtype("<" + kind) if kind != "?" else np.bool_)
        if a.dtype != np.float32 and a.dtype.kind == "f":
            a = a.astype(np.float32)
    return a.reshape(ref.shape)


def _collect(index: dict[str, TensorRef], primary: re.Pattern, alts: list[re.Pattern]):
    """Layer-indexed tensor refs matching the primary pattern, else the fallbacks."""
    for pat in [primary, *alts]:
        hits: dict[int, TensorRef] = {}
        for name, ref in index.items():
            m = pat.search(name)
            if m and len(ref.shape) == 2:
                hits[int(m.group(1))] = ref
        if hits:
            return [hits[i] for i in sorted(hits)]
    return []


class QuantizedCheckpoint(ValueError):
    """Raised when a repository ships quantized tensors rather than dense ones.

    A checkpoint stored as FP8/INT4 blocks plus scales (`weight._data` +
    `weight._scale`, `qweight`, `scales`, `qzeros`) is a DIFFERENT OBJECT from
    the dense matrix every spectral statistic here is defined on, and silently
    de-quantizing it would put a rounding artefact into the honest null.  It is
    excluded explicitly, with the reason recorded on the panel row.
    """


_QUANT_MARKERS = ("._data", "._scale", "qweight", "qzeros", "scales", "g_idx")


def quantization_reason(index: dict[str, TensorRef]) -> str | None:
    """Name the quantization scheme if the checkpoint is not dense, else None."""
    names = list(index)
    for marker in _QUANT_MARKERS:
        hits = [n for n in names if marker in n]
        if hits:
            return f"quantized: {len(hits)} tensors carry '{marker}' (e.g. {hits[0]})"
    return None


def residual_write_refs(index: dict[str, TensorRef]) -> tuple[list[TensorRef], list[TensorRef]]:
    """The attention-output and MLP-output projections, layer-ordered.

    These are the two matrices that WRITE into the residual stream, which is why
    a residual-direction edit (abliteration, ROSI, a constant carrier offset)
    must land in one of them and why every weight statistic here reads them.
    """
    return (
        _collect(index, _O_PROJ_RE, _ATTN_OUT_ALT),
        _collect(index, _DOWN_PROJ_RE, _MLP_OUT_ALT),
    )


def load_residual_matrices(
    snapshot: Path, *, max_layers: int | None = None
) -> tuple[list[np.ndarray], list[np.ndarray], dict]:
    """Read o_proj and down_proj for every layer as float32 arrays.

    Returns (o_list, d_list, info).  Memory is bounded: for a 4B model the two
    stacks are about 1.5 GB in float32, which this box has in abundance, and
    nothing else is read.
    """
    index = build_index(snapshot)
    qr = quantization_reason(index)
    if qr:
        raise QuantizedCheckpoint(f"{snapshot.name}: {qr}")
    o_refs, d_refs = residual_write_refs(index)
    if max_layers is not None:
        o_refs, d_refs = o_refs[:max_layers], d_refs[:max_layers]
    o = [read_tensor(r) for r in o_refs]
    d = [read_tensor(r) for r in d_refs]
    info = {
        "n_tensors": len(index),
        "n_o_proj": len(o),
        "n_down_proj": len(d),
        "o_names": [r.name for r in o_refs[:2]],
        "d_names": [r.name for r in d_refs[:2]],
        "o_dtype": o_refs[0].dtype if o_refs else None,
        "total_bytes": int(sum(r.nbytes for r in index.values())),
    }
    return o, d, info


# --------------------------------------------------------------------------
# Repository text files -- the surface the BLIND auditor's B1 screen reads
# --------------------------------------------------------------------------

_TEXT_FILES = (
    "config.json",
    "tokenizer_config.json",
    "generation_config.json",
    "chat_template.jinja",
    "README.md",
)


def read_repo_text(snapshot: Path) -> dict[str, str | None]:
    """Read the small text files of a repository, tolerating missing ones."""
    out: dict[str, str | None] = {}
    for name in _TEXT_FILES:
        p = snapshot / name
        try:
            out[name] = p.read_text(encoding="utf-8", errors="replace") if p.exists() else None
        except OSError:
            out[name] = None
    return out


def snapshot_dir(cache_root: Path, repo_id: str) -> Path | None:
    """Resolve `org/name` to its cached snapshot directory, or None."""
    slug = "models--" + repo_id.replace("/", "--")
    base = cache_root / slug / "snapshots"
    if not base.is_dir():
        return None
    revs = sorted((p for p in base.iterdir() if p.is_dir()), key=lambda p: p.name)
    for rev in revs:
        if list(rev.glob("*.safetensors")):
            return rev
    return revs[-1] if revs else None


def key_shape_signature(index: dict[str, TensorRef]) -> dict:
    """A compact, comparable summary of the state dict's key set and shapes.

    This is what makes the key/shape screen work with no parent: an explicit
    bias tensor added to `o_proj` is a NEW KEY that the declared architecture
    does not define, and no reference checkpoint is needed to see that.
    """
    keys = sorted(index)
    return {
        "n_keys": len(keys),
        "shapes": {k: list(index[k].shape) for k in keys},
        "dtypes": sorted({index[k].dtype for k in keys}),
        "bias_keys": [k for k in keys if k.endswith(".bias")],
        "o_proj_bias": [k for k in keys if "o_proj.bias" in k],
        "down_proj_bias": [k for k in keys if "down_proj.bias" in k],
        "lora_keys": [k for k in keys if "lora_" in k.lower()],
    }
