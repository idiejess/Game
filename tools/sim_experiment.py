#!/usr/bin/env python3
"""Compare balance variants quickly (development aid; not part of the shipped tuning).

Variants patch simulate_runs.Sim in memory:
  base           current rules
  drift_alt      water drift applies on every second watch
  start60        water starts at 60
Usage: python3 tools/sim_experiment.py --runs 480 --variants base,drift_alt
"""
import argparse
import collections
import statistics
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import simulate_runs as S  # noqa: E402


def run_variant(name, runs, seed):
    cards, chars, endings, counters = S.load_content()
    sim = S.Sim(cards, chars, endings, counters)
    orig_advance = S.Sim.advance
    orig_start = S.Sim.start_run
    if name == "drift_alt":
        def advance(self):
            if self.run["watch"] % 2 == 0:
                # skip drift on even watches by temporarily neutralising it
                self.run["res"]["water"] += 1 if not self.has_flag("sluice_rebuilt") else 0
                out = orig_advance(self)
                return out
            return orig_advance(self)
        S.Sim.advance = advance
    if name == "start60":
        def start_run(self, seed_v):
            orig_start(self, seed_v)
            self.run["res"]["water"] = 60
        S.Sim.start_run = start_run
    if name.startswith("gain"):
        # Scale positive water effects (e.g. gain2 doubles them) to test restorative pacing.
        factor = float(name[4:] or 2)
        for c in cards.values():
            for side in ("left", "right"):
                res = c[side]["effects"].get("resources", {})
                if res.get("water", 0) > 0:
                    res["water"] = int(round(res["water"] * factor))
    if name == "traffic_drift_legacy":
        # Low traffic lets the pound recover one mark; heavy traffic drains an extra mark.
        def advance(self):
            t = self.get_res("traffic")
            if not self.has_flag("sluice_rebuilt"):
                if t <= 35:
                    self.run["res"]["water"] = min(100, self.run["res"]["water"] + 1)
                elif t >= 70:
                    self.run["res"]["water"] = max(0, self.run["res"]["water"] - 1)
            return orig_advance(self)
        S.Sim.advance = advance
    if name.startswith("arcbonus"):
        S.ARC_ACTIVE_BONUS = float(name[8:])
    if name.startswith("ma08gate"):
        # Lower the High Water entry threshold (water min) to test arc reachability.
        thr = int(name[8:] or 55)
        for cid in ("ma08_01", "ma08_02", "ma08_04"):
            cards[cid]["conditions"]["resources"]["water"]["min"] = thr
    if name == "combo":
        # traffic-coupled drift + water gains capped at +8 (x2) + arc bonus 5
        def advance(self):
            t = self.get_res("traffic")
            if not self.has_flag("sluice_rebuilt"):
                if t <= 35:
                    self.run["res"]["water"] = min(100, self.run["res"]["water"] + 1)
                elif t >= 70:
                    self.run["res"]["water"] = max(0, self.run["res"]["water"] - 1)
            return orig_advance(self)
        S.Sim.advance = advance
        S.ARC_ACTIVE_BONUS = 5.0
        for c in cards.values():
            for side in ("left", "right"):
                res = c[side]["effects"].get("resources", {})
                if res.get("water", 0) > 0:
                    res["water"] = min(8, res["water"] * 2)
    strategies = S.all_strategies()
    lengths, endings_c = [], collections.Counter()
    arcs_completed = collections.Counter()
    for i in range(runs):
        if i % 8 == 0:
            sim.profile = sim.fresh_profile()
        sim.play(seed * 100000 + i, strategies[i % len(strategies)])
        lengths.append(sim.run["watch"])
        endings_c[sim.run["ended"]] += 1
        for a, st in sim.run["arcs"].items():
            if st.get("status") == "completed":
                arcs_completed[a] += 1
    S.Sim.advance = orig_advance
    S.Sim.start_run = orig_start
    water_deaths = endings_c["end_res_water_min"]
    print(f"{name:10s} mean {statistics.mean(lengths):5.1f} median {statistics.median(lengths):5.1f} "
          f"water-death {100 * water_deaths / runs:4.1f}% long-watch {100 * sum(v for k, v in endings_c.items() if k and k.startswith('end_ord')) / runs:4.1f}% "
          f"other-res-death {100 * sum(v for k, v in endings_c.items() if k and k.startswith('end_res') and k != 'end_res_water_min') / runs:4.1f}% "
          f"arcs completed {sum(arcs_completed.values())} ({len(arcs_completed)} distinct)")
    print("   ", endings_c.most_common(8))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=480)
    ap.add_argument("--seed", type=int, default=5)
    ap.add_argument("--variants", default="base,drift_alt,start60")
    args = ap.parse_args()
    for v in args.variants.split(","):
        run_variant(v, args.runs, args.seed)


if __name__ == "__main__":
    main()
