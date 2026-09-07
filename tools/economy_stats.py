#!/usr/bin/env python3
"""Resource economy statistics: per resource, how many choices raise/lower it and by how much,
split by pool/category. Helps explain simulation death distributions. Read-only.

Usage: python3 tools/economy_stats.py
"""
import collections
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ["water", "traffic", "coffers", "company", "town"]


def main():
    cards = []
    for p in sorted((ROOT / "content" / "cards").glob("*/*.json")):
        cards += json.loads(p.read_text())["cards"]
    up = collections.Counter()
    down = collections.Counter()
    sum_up = collections.Counter()
    sum_down = collections.Counter()
    best_up = {r: [] for r in RES}
    general_cards = [c for c in cards if c.get("pool", "general") in ("general", "character") and not c.get("conditions")]
    print("unconditional general/character cards:", len(general_cards))
    for c in cards:
        for s in ("left", "right"):
            for r, v in c[s]["effects"].get("resources", {}).items():
                if v > 0:
                    up[r] += 1
                    sum_up[r] += v
                    best_up[r].append((v, c["id"], s))
                elif v < 0:
                    down[r] += 1
                    sum_down[r] += v
    for r in RES:
        print(f"{r:8s} up {up[r]:4d} (+{sum_up[r]:5d})  down {down[r]:4d} ({sum_down[r]:6d})  net {sum_up[r] + sum_down[r]:+6d}")
    # Unconditional-only view (what an early run actually sees)
    print("\nunconditional cards only:")
    u_up, u_down = collections.Counter(), collections.Counter()
    for c in general_cards:
        for s in ("left", "right"):
            for r, v in c[s]["effects"].get("resources", {}).items():
                (u_up if v > 0 else u_down)[r] += v
    for r in RES:
        print(f"{r:8s} +{u_up[r]:5d} {u_down[r]:6d} net {u_up[r] + u_down[r]:+5d}")
    # Cards where both sides lower water
    both_down = [c["id"] for c in cards if all(c[s]["effects"].get("resources", {}).get("water", 0) < 0 for s in ("left", "right"))]
    both_up = [c["id"] for c in cards if all(c[s]["effects"].get("resources", {}).get("water", 0) > 0 for s in ("left", "right"))]
    print("\nboth sides lower water:", len(both_down), "; both raise water:", len(both_up))
    print("res:water tagged:", sum(1 for c in cards if "res:water" in c.get("tags", [])))


if __name__ == "__main__":
    main()
