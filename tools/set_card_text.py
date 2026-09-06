#!/usr/bin/env python3
"""Replace the situation text of one or more cards in place.

Usage: python3 tools/set_card_text.py <card_id> "<new text>" [<card_id> "<new text>" ...]
Finds the card across content/cards/**.json, rewrites only that file, preserves formatting style
(indent=1 dump). Used for targeted editorial revisions after analyzer warnings.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main():
    args = sys.argv[1:]
    if len(args) < 2 or len(args) % 2:
        print(__doc__)
        sys.exit(2)
    edits = dict(zip(args[0::2], args[1::2]))
    done = set()
    for p in sorted((ROOT / "content" / "cards").glob("*/*.json")):
        data = json.loads(p.read_text())
        changed = False
        for c in data["cards"]:
            if c["id"] in edits:
                c["text"] = edits[c["id"]]
                done.add(c["id"])
                changed = True
        if changed:
            p.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    missing = set(edits) - done
    if missing:
        print("not found:", sorted(missing))
        sys.exit(1)
    print("updated", sorted(done))


if __name__ == "__main__":
    main()
