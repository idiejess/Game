#!/usr/bin/env python3
"""One-off: ordinary and false endings use the ordinary ending music instead of the failure stinger."""
import json
import pathlib

p = pathlib.Path(__file__).resolve().parents[1] / "content" / "endings" / "endings.json"
d = json.loads(p.read_text())
n = 0
for e in d["endings"]:
    if e["kind"] in ("ordinary", "false") and e.get("music") == "mus_ending_fail":
        e["music"] = "mus_ending_ordinary"
        n += 1
p.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n")
print("retargeted", n)
