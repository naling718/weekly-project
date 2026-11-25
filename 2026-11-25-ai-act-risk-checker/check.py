"""CLI: python check.py "description"  |  python check.py --samples"""
import json
import sys
from pathlib import Path

from classifier import classify


def show(name, result):
    print(f"\n{name}\n  Tier: {result['tier'].upper()}")
    for m in result["matches"]:
        print(f"  - {m['ref']} {m['title']} (matched: \"{m['evidence']}\")")
    print("  Obligations:")
    for o in result["obligations"]:
        print(f"    * {o}")


if __name__ == "__main__":
    if sys.argv[1:] == ["--samples"]:
        samples = json.loads((Path(__file__).parent / "samples.json").read_text())
        for s in samples:
            r = classify(s["description"])
            print(f"{'OK ' if r['tier'] == s['expected'] else 'XX '} {r['tier']:<13} {s['name']}")
    elif len(sys.argv) == 2:
        show("Result", classify(sys.argv[1]))
    else:
        sys.exit(__doc__)
