import sys, time, numpy as np, scipy.linalg as sl
sys.path.insert(0, '.')
from flab2 import repo_io as R
from pathlib import Path
import os
snap = R.snapshot_dir(Path(os.environ['HF_HUB_CACHE']), 'allenai/OLMo-2-0425-1B-Instruct')
o, d, info = R.load_residual_matrices(snap)
for li in (0, 5, 10, 15):
    w = np.asarray(o[li], dtype=np.float32)
    g32 = (w @ w.T).astype(np.float32)
    e32 = sl.eigh(g32, eigvals_only=True, driver='ev')
    w64 = w.astype(np.float64)
    e64 = sl.eigh(w64 @ w64.T, eigvals_only=True, driver='ev')
    sv = sl.svd(w64, compute_uv=False)
    print(li, 'f32 gram smallest', np.sqrt(np.clip(e32[:3],0,None)), 'f64 gram', np.sqrt(np.clip(e64[:3],0,None)), 'svd', sv[-3:][::-1], 'smax', sv[0], flush=True)
