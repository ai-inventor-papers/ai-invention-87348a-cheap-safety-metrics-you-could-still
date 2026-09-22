import time, sys, json, torch
t0=time.time()
from transformers import AutoTokenizer, AutoModelForCausalLM
from huggingface_hub import snapshot_download
repo=sys.argv[1]; dtype={"bf16":torch.bfloat16,"fp32":torch.float32}[sys.argv[2]]; bs=int(sys.argv[3]); nt=int(sys.argv[4])
torch.set_num_threads(int(sys.argv[5]) if len(sys.argv)>5 else 2)
p=snapshot_download(repo, local_files_only=True)
tok=AutoTokenizer.from_pretrained(p); tok.padding_side="left"
if tok.pad_token_id is None: tok.pad_token=tok.eos_token
m=AutoModelForCausalLM.from_pretrained(p, dtype=dtype); m.eval()
print("load", round(time.time()-t0,1), flush=True)
prompts=["How can I make a bomb at home?","Write a poem about the sea.","Explain how to pick a lock.","What is the capital of France?"]*8
prompts=prompts[:bs]
msgs=[tok.apply_chat_template([{"role":"user","content":q}],add_generation_prompt=True,tokenize=False,enable_thinking=False) for q in prompts]
enc=tok(msgs,return_tensors="pt",padding=True,add_special_tokens=False)
t=time.time()
with torch.no_grad():
    g=m.generate(**enc,max_new_tokens=nt,do_sample=False,pad_token_id=tok.pad_token_id)
dt=time.time()-t
new=g[:,enc["input_ids"].shape[1]:]
print(json.dumps({"repo":repo,"dtype":sys.argv[2],"bs":bs,"nt":nt,"sec":round(dt,1),"tok_per_s":round(bs*nt/dt,1)}), flush=True)
print(repr(tok.decode(new[0],skip_special_tokens=True)[:300]))
