import os, sys, time
os.environ.update(OMP_NUM_THREADS="2", MKL_NUM_THREADS="2", OPENBLAS_NUM_THREADS="2")
import torch
torch.set_num_threads(2)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from live_lib import load_model
repo, dt = sys.argv[1], {"fp32": torch.float32, "bf16": torch.bfloat16}[sys.argv[2]]
t0 = time.time(); model, tok, _ = load_model(repo, dt); print("load", round(time.time()-t0, 1), flush=True)
B, T = 16, 70
ids = torch.randint(100, 1000, (B, T)); mask = torch.ones_like(ids)
with torch.no_grad():
    for rep in range(2):
        t0 = time.time(); out = model(input_ids=ids, attention_mask=mask, use_cache=True); t1 = time.time()
        print("full16x70", round(t1-t0, 2), flush=True)
    cache = out.past_key_values
    t0 = time.time()
    for k in range(5):
        o = model(input_ids=ids[:, -1:], attention_mask=torch.ones(B, T+1, dtype=torch.long), past_key_values=cache, use_cache=True); cache.crop(T)
    print("single-token x5", round(time.time()-t0, 2), flush=True)
