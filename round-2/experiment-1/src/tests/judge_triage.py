import asyncio, json, os, sys
sys.path.insert(0,'.')
from screen.judge2 import AsyncJudge, RUBRIC
items=json.load(open('inherited/items.json'))['items']
cases=[]
for slug,label in [('mlabonne__Qwen3-4B-abliterated','COMPLIES'),('Qwen__Qwen3-4B','REFUSES')]:
    g=json.load(open(f'harvest/{slug}/generations.json'))
    for i in [0,5,2]:
        cases.append((items[g['gen_item_idx'][i]]['prompt'], g['generations'][i], f'{label}:{slug[:18]}:{i}'))
async def run(model, tag):
    j=AsyncJudge(model=model, budget_usd=8.0, cache_dir=__import__('pathlib').Path(f'cache/jt_{tag}'))
    res=await j.grade_many([(p,r) for p,r,_ in cases])
    print(f'--- {model}')
    for (p,r,lab),o in zip(cases,res):
        print(f'   {lab:34s} refused={o["refused"]} conv={o["convincing"]} spec={o["specific"]} src={o["source"]} raw={o["raw"][:20]!r}')
    print('   cost', j.report()['cum_usd'])
asyncio.run(run('openai/gpt-5-mini','m'))
asyncio.run(run('google/gemini-2.5-flash','g'))
asyncio.run(run('openai/gpt-4.1-mini','n'))
