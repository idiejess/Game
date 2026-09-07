#!/usr/bin/env python3
"""Print the card trace of one deterministic run using the alternating left/right policy that
game/tests/EngineTests.gd::test_engine_matches_python_simulator replays. Used to verify that the
GDScript engine and the Python simulator stay bit-for-bit in step.

Usage: python3 tools/sim_trace.py --seed 12345 --steps 40 [--json]
"""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import simulate_runs as S  # noqa: E402


class Alternate(S.Strategy):
    name = "alternate"

    def __init__(self):
        self.i = 0

    def choose(self, sim, card):
        side = "left" if self.i % 2 == 0 else "right"
        self.i += 1
        return side


def trace(seed, steps):
    cards, chars, endings, counters = S.load_content()
    sim = S.Sim(cards, chars, endings, counters)
    out = sim.play(seed, Alternate(), max_steps=steps)
    return out, sim.run


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=12345)
    ap.add_argument("--steps", type=int, default=40)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    t, run = trace(args.seed, args.steps)
    if args.json:
        print(json.dumps({"seed": args.seed, "trace": t, "resources": run["res"], "watch": run["watch"], "ended": run["ended"]}))
    else:
        print(" ".join(t))
        print("resources", run["res"], "watch", run["watch"], "ended", run["ended"])


if __name__ == "__main__":
    main()
