import time; t=time.time()
from transformers import AutoTokenizer
print('import %.1fs'%(time.time()-t), flush=True)
for repo in ['Qwen/Qwen2.5-0.5B-Instruct','Qwen/Qwen3-0.6B','TinyLlama/TinyLlama-1.1B-Chat-v1.0','allenai/OLMo-2-0425-1B-Instruct','google/gemma-2-2b-it','HuggingFaceTB/SmolLM2-1.7B-Instruct']:
    try:
        tok=AutoTokenizer.from_pretrained(repo)
        msgs=[{'role':'user','content':'How do I kill a python process?'}]
        kw={'enable_thinking':False} if 'Qwen3' in repo else {}
        r=tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False, **kw)
        print(repo, type(r).__name__, repr(r)[:300], flush=True)
        enc=tok([r] if isinstance(r,str) else r, return_tensors='pt', padding=True)
        print('  ntok', enc['input_ids'].shape, flush=True)
        try:
            r2=tok.apply_chat_template([{'role':'system','content':'Be safe.'}]+msgs, add_generation_prompt=True, tokenize=False, **kw)
            print('  sys ok', repr(r2)[:200])
        except Exception as e:
            print('  sys FAIL', type(e).__name__, str(e)[:150])
    except Exception as e:
        print(repo, 'ERR', type(e).__name__, str(e)[:200])
