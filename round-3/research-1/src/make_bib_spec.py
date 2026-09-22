"""Build the identifier list (raw/bib_spec.json) for build_bib.py.

Base list = every work cited by the iteration-2 draft/bib + the plan's fix-list (viii)
additions + every closest-prior-work ID from novelty_A/B/C.json. Venue overrides below
are only for venues verified in this run (Crossref / arXiv journal_ref / iteration-1
dependency), never from memory.
"""
import json
import re
from pathlib import Path

WS = Path(__file__).parent

BASE = [
    # id, forced key (None = FirstAuthorYYYY), expected title fragment, overrides
    ("2608.05578", "Messenger2026", "Detecting Safety Training Modification",
     {"venue": "IEEE Access", "journal_venue": True, "volume": "14", "pages": "91723--91737",
      "doi": "10.1109/ACCESS.2026.3704057", "year": "2026"}),
    ("2606.22676", "Lee2026", "Skin-Deep", {}),
    ("2606.25750", "Huang2026", "RAS", {}),
    ("2511.14195", "Lin2026", "N-GLARE",
     {"venue": "Proceedings of the Annual Meeting of the Association for Computational Linguistics (ACL 2026)",
      "year": "2026", "note": "Long paper; venue per iteration-1 verification (ACL 2026 Long 1334)"}),
    ("2604.18901", "LlorenteSaguer2026a", "Harmful Intent as a Geometrically Recoverable", {}),
    ("2603.27412", "LlorenteSaguer2026b", "Geometry of Harmful Intent", {}),
    ("2406.11717", "Arditi2024", "Refusal in Language Models Is Mediated", {}),
    ("2508.20766", "AbuShairah2025", "Rank-One Safety Injection", {}),
    ("2507.11878", "Zhao2025", "Harmfulness and Refusal Separately", {}),
    ("2602.02132", "Joad2026", "More to Refusal", {}),
    ("2603.05773", "Wu2026", "Knowing without Acting", {}),
    ("2606.16349", "Lan2026", "Harmfulness--Refusal Coupling", {}),
    ("2607.00572", "Chua2026", "HARC", {}),
    ("2508.00161", "Zhong2025", "Watch the Weights", {}),
    ("2607.01854", "Hurtado2026", "Abliterated", {}),
    ("2408.00761", None, "Tamper-Resistant", {}),
    ("2410.07137", None, "Null Models", {}),
    ("2407.21792", "Ren2024", "Safetywashing", {}),
    ("2504.20879", "Singh2025", "Leaderboard Illusion", {}),
    ("2605.06324", "Burnat2026", "Gaming the Metric", {}),
    ("2602.04653", "Fogel2026", "Inference-Time Backdoors via Chat Templates", {}),
    ("2406.09289", "Ball2024", "Understanding Jailbreak Success", {}),
    ("2407.12404", "Tan2024", "Generalization and Reliability of Steering Vectors", {}),
    ("2608.09624", "Luo2026", "Measuring the Wrong Thing", {}),
    ("2607.13075", "Schwarz2026", "Entanglement Wall", {}),
    ("2608.05086", "Rivera2026", "Item Response Theory for AI Safety", {}),
    ("2606.20626", "Spagliardi2026", "Efficient Safety Benchmarking", {}),
    ("2401.14446", "Casper2024", "Black-Box Access is Insufficient",
     {"venue": "Proceedings of the 2024 ACM Conference on Fairness, Accountability, and Transparency (FAccT '24)",
      "doi": "10.1145/3630106.3659037", "pages": "2254--2272", "year": "2024"}),
    ("2406.05946", None, "More Than Just a Few Tokens Deep", {}),
    ("2412.09565", "Bailey2024", "Obfuscated Activations", {}),
    ("2308.01263", None, "XSTest", {}),
    ("2402.10260", "Souly2024", "StrongREJECT", {}),
    # fix-list (viii) additions
    ("2608.07786", None, "", {}), ("2511.06390", None, "", {}), ("2601.10266", None, "", {}),
    ("2512.05117", None, "", {}), ("2607.25750", None, "", {}), ("2607.12792", None, "", {}),
    ("2609.14759", None, "", {}), ("2608.13329", None, "", {}), ("2609.03887", None, "", {}),
    ("2606.02907", None, "", {}), ("2602.06911", None, "TamperBench", {}), ("2502.16173", None, "", {}),
    ("2104.14337", None, "Dynabench", {}), ("2210.03165", None, "", {}), ("2403.00393", None, "", {}),
    ("1506.06980", None, "Strategic Classification", {}),
    ("2505.17815", None, "", {}), ("2509.18058", None, "", {}),
    ("2404.01318", None, "JailbreakBench", {}), ("2405.20947", None, "OR-Bench", {}),
    ("2407.17436", None, "AIR-Bench 2024", {}), ("2401.05561", None, "TrustLLM", {}),
    ("2009.03300", None, "Massive Multitask", {}), ("2110.14168", None, "Math Word Problems", {}),
    ("2406.11939", None, "Arena-Hard", {}), ("2505.09388", None, "Qwen3 Technical Report", {}),
]


def main():
    spec, seen = [], set()
    for aid, key, exp, ov in BASE:
        d = {"arxiv": aid, "expect": exp, **ov}
        if key:
            d["key"] = key
        spec.append(d)
        seen.add(aid)
    extra = []
    for f in ("novelty_A.json", "novelty_B.json", "novelty_C.json", "extra_ids.json"):
        p = WS / f
        if not p.exists():
            continue
        d = json.loads(p.read_text())
        recs = []
        if isinstance(d, list):
            recs = d
        else:
            for r in d.get("records", []):
                recs += r.get("closest_prior_work", [])
            if d.get("kill_check"):
                recs.append(d["kill_check"].get("closest_paper"))
        for r in recs:
            for m in re.findall(r"(?<![\d.])(\d{4}\.\d{4,5})(?![\d])", json.dumps(r)):
                if m not in seen and 1400 < int(m[:4]) < 2610:
                    seen.add(m)
                    extra.append(m)
    spec += [{"arxiv": m, "expect": ""} for m in extra]
    spec += json.loads((WS / "raw" / "manual_bib_entries.json").read_text())
    (WS / "raw" / "bib_spec.json").write_text(json.dumps(spec, indent=1))
    print(len(spec), "ids;", len(extra), "added from novelty files")


if __name__ == "__main__":
    main()
