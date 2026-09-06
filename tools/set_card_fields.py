#!/usr/bin/env python3
"""Set top-level fields on cards by ID. Usage:
  python3 tools/set_card_fields.py <card_id> '<json object of fields>' [...]
Example: python3 tools/set_card_fields.py evg_cargo_06 '{"pool":"fallback","max_per_run":6}'
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
    edits = {args[i]: json.loads(args[i + 1]) for i in range(0, len(args), 2)}
    done = set()
    for p in sorted((ROOT / "content" / "cards").glob("*/*.json")):
        data = json.loads(p.read_text())
        changed = False
        for c in data["cards"]:
            if c["id"] in edits:
                for k, v in edits[c["id"]].items():
                    if v is None:
                        c.pop(k, None)
                    else:
                        c[k] = v
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
