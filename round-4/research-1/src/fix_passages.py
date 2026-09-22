"""Verify every supporting passage against the full fetched text of its source
(and the arXiv PDF variant); keep only verbatim segments; write passage_fixes.json
consumed by assemble.py."""
import json, re, subprocess, hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
WS = Path(__file__).parent
SK = "/ai-inventor/.claude/skills/aii-web-tools"; PY = SK + "/../.ability_client_venv/bin/python"
d = json.loads((WS / "research_out.json").read_text())

def fetch(url):
    f = WS / "raw/fulltext" / (hashlib.md5(url.encode()).hexdigest() + ".txt")
    if f.exists() and f.stat().st_size > 500:
        return f.read_text()
    out = ""
    for off in range(0, 400000, 100000):
        r = subprocess.run([PY, SK + "/scripts/aii_fast_web_fetch.py", "fetch", "--url", url, "--max-chars", "100000", "--char-offset", str(off)],
                           capture_output=True, text=True, timeout=300)
        out += r.stdout
        if len(r.stdout) < 90000:
            break
    f.write_text(out); return out

def norm(s):
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').replace("–", "-").replace("—", "-")
    s = re.sub(r"-\s*\n\s*", "", s)
    return re.sub(r"\s+", " ", s).strip().lower()

def variants(url):
    v = [url]
    m = re.search(r"arxiv\.org/(abs|pdf|html)/([\d.]+(v\d)?)", url)
    if m:
        i = m.group(2); v += [f"https://arxiv.org/pdf/{i}", f"https://arxiv.org/abs/{i}", f"https://arxiv.org/html/{i}"]
    return list(dict.fromkeys(v))

fixes = {}
def work(s):
    if not s["supporting_passages"]:
        return
    res = {"url": s["url"], "passages": []}
    texts = {}
    for u in variants(s["url"]):
        try: texts[u] = norm(fetch(u))
        except Exception as e: texts[u] = ""
    chosen_url = None
    for p in s["supporting_passages"]:
        segs = [x.strip(" .;,") for x in re.split(r"\.\.\.|…", p["quote"]) if x.strip()]
        best = None
        for seg in sorted(segs, key=len, reverse=True):
            if len(seg.split()) < 6: continue
            for u, t in texts.items():
                if norm(seg) in t:
                    best = (seg, u); break
            if best: break
        if best:
            # prefer url that holds all kept passages
            res["passages"].append({"quote": best[0], "locator": p.get("locator"), "found_in": best[1]})
    urls = [x["found_in"] for x in res["passages"]]
    if urls:
        # choose a url containing every kept passage, preferring the original
        for u in variants(s["url"]):
            if all(norm(x["quote"]) in texts[u] for x in res["passages"]):
                chosen_url = u; break
        if chosen_url is None:
            chosen_url = max(set(urls), key=urls.count)
            res["passages"] = [x for x in res["passages"] if norm(x["quote"]) in texts[chosen_url]]
    res["url"] = chosen_url or s["url"]
    fixes[str(s["index"])] = res
    print(s["index"], len(s["supporting_passages"]), "->", len(res["passages"]), res["url"])

with ThreadPoolExecutor(6) as ex:
    list(ex.map(work, d["sources"]))
(WS / "step5/passage_fixes.json").write_text(json.dumps(fixes, indent=1))
