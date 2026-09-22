import os, sys, json
sys.path.insert(0, '.')
import requests, judge_harvest as JH, judge_stance as JS
from pathlib import Path
led = JH.Ledger(Path('out/spend.jsonl'))
key = os.environ['OPENROUTER_API_KEY']
b = json.loads(Path('out/bcells/Qwen__Qwen2.5-0.5B-Instruct__F_none__0.json').read_text())
pick = []
for it in b['items']:
    r = it['response'] or ''
    if it['arm'] == 'HARM' and (r.startswith('Certainly') or r.startswith('Dear') or r.startswith('Hey')):
        pick.append((it['prompt'], r, 'COMPLIANT'))
    if it['arm'] == 'HARM' and r.startswith("I'm sorry") and len([p for p in pick if p[2]=='REFUSAL']) < 3:
        pick.append((it['prompt'], r, 'REFUSAL'))
pick = pick[:9]
with requests.Session() as s:
    for p, r, lab in pick:
        a = JH.grade_one(s, key, p, r, led); bb = JS.grade_stance(s, key, p, r, led)
        print(lab, '| strongreject refused=', a and a['refused'], a and (a['convincing'], a['specific']), '| stance declined=', bb and bb['refused'], bb and bb['raw'], '|', r[:60].replace('\n',' '))
print('spend', round(led.usd, 4))
