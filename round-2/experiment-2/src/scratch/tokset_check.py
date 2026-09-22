import json, sys
sys.path.insert(0, '.')
from pathlib import Path
from transformers import AutoTokenizer
import behave2 as B
H = Path('/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_1/gen_art/gen_art_experiment_1/harvest')
for repo, slug in (('Qwen/Qwen3-0.6B', 'Qwen__Qwen3-0.6B'),):
    meta = json.loads((H / slug / 'meta.json').read_text())
    ts = meta['token_sets']
    tok = AutoTokenizer.from_pretrained(str(B.snapshot(repo)))
    r, c = B.token_sets(tok)
    print(repo, 'refusal match', sorted(ts['refusal']) == r, 'compliance match', sorted(ts['compliance']) == c)
    print(' harvest', ts['refusal'][:8], ts['compliance'][:8]); print(' mine   ', r[:8], c[:8])
