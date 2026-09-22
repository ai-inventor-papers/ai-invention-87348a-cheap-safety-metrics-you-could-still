import json, re, os

W = "/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_5/gen_art/gen_art_research_1"
data = json.load(open(f"{W}/sa_A/sa_A_out.json"))

def norm(s):
    return re.sub(r'\s+', ' ', s).strip()

def in_any_capture(quote, capture_files):
    nq = norm(quote)
    if not nq:
        return None, "empty"
    for cf in capture_files:
        if not os.path.exists(cf):
            continue
        txt = norm(open(cf, encoding='utf-8', errors='ignore').read())
        if nq in txt:
            return True, cf
    return False, None

total = 0
passed = 0
fails = []

for row in data["incumbent_table"]:
    cfs = row.get("capture_files", [])
    quotes = []
    hv = row["headline_number"].get("verbatim","")
    if hv and not hv.startswith("N/A"):
        quotes.append(("headline_number.verbatim", hv))
    hq = row["holdout_actually_used"].get("quote","")
    if hq and hq != "n/a (in-house)":
        quotes.append(("holdout_actually_used.quote", hq))
    hq2 = row["holdout_actually_used"].get("quote2")
    if hq2:
        quotes.append(("holdout_actually_used.quote2", hq2))
    for label, quote in quotes:
        total += 1
        ok, where = in_any_capture(quote, cfs)
        if ok:
            passed += 1
        else:
            fails.append((row["key"], label, quote[:100], cfs))

for item in data["missing_citations"]:
    cfs = item.get("capture_files", [])
    quotes = [("quote", item["quote"])]
    for k, v in item.get("extra_quotes", {}).items():
        if v.startswith("NOT_FOUND"):
            continue
        quotes.append((f"extra_quotes.{k}", v))
    for label, quote in quotes:
        total += 1
        ok, where = in_any_capture(quote, cfs)
        if ok:
            passed += 1
        else:
            fails.append((item["key"], label, quote[:100], cfs))

print(f"TOTAL quotes checked: {total}")
print(f"PASSED: {passed}")
print(f"FAILED: {total - passed}")
for f in fails:
    print("FAIL:", f)

print()
print("--- capture file existence (non-bar rows) ---")
for row in data["incumbent_table"]:
    if row["key"] == "InHouse_16PromptBar":
        continue
    cfs = row.get("capture_files", [])
    exist = [c for c in cfs if os.path.exists(c)]
    print(row["key"], len(exist), "/", len(cfs))
    assert len(exist) >= 1

print()
print("Row count:", len(data["incumbent_table"]))
print("Missing-citations count:", len(data["missing_citations"]))
