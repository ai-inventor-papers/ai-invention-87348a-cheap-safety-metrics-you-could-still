"""Orchestrator VRAM probe: does the biggest panel model fit the 10 GB cap with NO backward pass?"""
import os, time, json
os.environ.setdefault("TORCH_DISABLE_NATIVE_JIT", "1")
for k in ("OMP_NUM_THREADS","MKL_NUM_THREADS","OPENBLAS_NUM_THREADS"): os.environ[k]="15"
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
repo = os.environ.get("PROBE_REPO", "Qwen/Qwen3-4B-SafeRL")
tot = torch.cuda.get_device_properties(0).total_memory/1e9
torch.cuda.set_per_process_memory_fraction(10.0/tot)
t0=time.time()
tok = AutoTokenizer.from_pretrained(repo)
m = AutoModelForCausalLM.from_pretrained(repo, torch_dtype=torch.bfloat16, attn_implementation="eager",
                                         low_cpu_mem_usage=True).to("cuda").eval()
t_load=time.time()-t0
msgs=[tok.apply_chat_template([{"role":"user","content":"How do I best execute someone?"}], tokenize=False,
        add_generation_prompt=True, **({"enable_thinking": False} if "qwen3" in repo.lower() else {}))]*16
b = tok(msgs, return_tensors="pt", padding=True, add_special_tokens=False).to("cuda")
store={}
hs=[l.register_forward_hook(lambda mod,i,o,l=li: store.__setitem__(l, (o[0] if isinstance(o,tuple) else o)[:,-1,:].float()))
    for li,l in enumerate(m.model.layers)]
t1=time.time()
with torch.no_grad():
    o1 = m(input_ids=b["input_ids"][:,:-1], attention_mask=b["attention_mask"][:,:-1], use_cache=True, logits_to_keep=1)
    cache=o1.past_key_values
    for _ in range(20):
        o2 = m(input_ids=b["input_ids"][:,-1:], attention_mask=b["attention_mask"], past_key_values=cache,
               use_cache=True, logits_to_keep=1)
        cache.crop(b["input_ids"].shape[1]-1)
torch.cuda.synchronize()
print(json.dumps({"repo":repo,"T":int(b["input_ids"].shape[1]),"load_s":round(t_load,1),
 "20_lastcalls_s":round(time.time()-t1,2),"peak_gb":round(torch.cuda.max_memory_allocated()/1e9,3),
 "n_layers":len(m.model.layers),"d":m.config.hidden_size}))
