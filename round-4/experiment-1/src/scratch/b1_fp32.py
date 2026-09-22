import sys, json, numpy as np, torch
import method as M
from live_lib import build_batch, load_model, get_layers
REPO = "Qwen/Qwen2.5-0.5B-Instruct"
out = {}
for dt_name, dt in (("fp32", torch.float32),):
    mr = M.ModelRun(REPO)
    # load in the requested dtype by temporarily patching load_model
    import live_lib
    orig = M.load_model
    M.load_model = lambda repo, dtype: orig(repo, dt)
    mr.load()
    M.load_model = orig
    b = mr.batch("plain"); b.item_idx = list(range(16))
    base = mr.base_pass(b, [], want_attn=False)
    single = []
    for i, p in enumerate(M.PROMPTS):
        bi = build_batch(mr.tok, REPO, [p], None, "system_ok"); bi.item_idx = [i]
        single.append(float(mr.base_pass(bi, [], want_attn=False)["m"][0]))
    d = np.abs(np.array(single) - base["m"])
    out[dt_name] = {"max_abs_diff": float(d.max()), "mean_abs_diff": float(d.mean()), "batched": base["m"].tolist(), "unbatched": single}
    print(dt_name, out[dt_name]["max_abs_diff"], out[dt_name]["mean_abs_diff"], flush=True)
    mr.unload()
json.dump(out, open("scratch/b1_fp32.json", "w"), indent=1)
