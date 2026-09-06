#!/usr/bin/env python3
"""Print selected cards compactly (id, speaker, text, labels, outcomes) for targeted review.

Usage: python3 tools/show_cards.py id1 id2 ... | --grep REGEX [--field text|label|outcome]
"""
import argparse
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_cards():
    out = {}
    for p in sorted((ROOT / "content" / "cards").glob("*/*.json")):
        for c in json.loads(p.read_text())["cards"]:
            out[c["id"]] = (c, p.relative_to(ROOT))
    return out


def show(c, path):
    print(f"--- {c['id']} ({c['speaker']}, {c['category']}) {path}")
    print("  T:", c["text"])
    for s in ("left", "right"):
        o = c[s].get("outcome", "")
        print(f"  {s[0].upper()}: [{c[s]['label']}]" + (f" -> {o}" if o else ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--grep")
    ap.add_argument("--field", default="text")
    args = ap.parse_args()
    cards = load_cards()
    if args.grep:
        rx = re.compile(args.grep, re.I)
        for cid, (c, p) in cards.items():
            hay = c["text"] if args.field == "text" else " ".join(c[s].get("label" if args.field == "label" else "outcome", "") for s in ("left", "right"))
            if rx.search(hay):
                show(c, p)
    for cid in args.ids:
        if cid in cards:
            show(*cards[cid])
        else:
            print("unknown card", cid)


if __name__ == "__main__":
    main()
