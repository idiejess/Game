#!/usr/bin/env python3
"""Balance probe built on simulate_runs.Sim: resource trajectories, danger-band occupancy and
per-card resource contribution. Cheaper than a full simulation; used to reason about balance.

Usage: python3 tools/sim_probe.py [--runs 600] [--seed 3]
"""
import argparse
import collections
import statistics
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import simulate_runs as S  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=600)
    ap.add_argument("--seed", type=int, default=3)
    args = ap.parse_args()
    cards, chars, endings, counters = S.load_content()
    sim = S.Sim(cards, chars, endings, counters)
    strategies = S.all_strategies()
    traj = collections.defaultdict(lambda: collections.defaultdict(list))  # res -> watch -> values
    low = collections.Counter()
    high = collections.Counter()
    contrib = collections.defaultdict(collections.Counter)  # res -> card -> total delta
    lengths = []
    for i in range(args.runs):
        strat = strategies[i % len(strategies)]
        if i % 8 == 0:
            sim.profile = sim.fresh_profile()
        # Manual play loop to sample resources every watch.
        sim.start_run(args.seed * 100000 + i)
        r = sim.run
        steps = 0
        while r["ended"] is None and steps < 400:
            cid = sim.next_card()
            if cid is None:
                break
            r["current"] = cid
            r["appear"][cid] += 1
            sim.profile["discovered"].add(cid)
            card = cards[cid]
            side = strat.choose(sim, card)
            eff = card[side]["effects"]
            for res, v in eff.get("resources", {}).items():
                contrib[res][cid] += v
            ending = sim.apply(eff)
            r["history"].append({"card": cid, "watch": r["watch"], "choice": side})
            if card.get("cooldown"):
                r["cooldowns"][cid] = card["cooldown"]
            r["current"] = None
            if "arc" in card:
                a = card["arc"]["id"]
                if sim.arc_status(a) == "inactive":
                    sim.set_arc(a, card["arc"]["stage"], "active")
                elif sim.arc_status(a) == "active":
                    sim.set_arc(a, max(sim.arc_stage(a), card["arc"]["stage"]))
            if r["pending_ending"]:
                sim.end_run(r["pending_ending"])
                break
            if not ending:
                ending = sim.advance()
            for res in S.RESOURCES:
                v = sim.get_res(res)
                traj[res][r["watch"]].append(v)
                if v <= 30:
                    low[res] += 1
                if v >= 70:
                    high[res] += 1
            if not ending:
                ending = sim.check_triggered_endings()
            if not ending and r["watch"] >= S.LONG_WATCH and (not sim.has_flag("allies_gathered") or r["watch"] >= S.HARD_WATCH_LIMIT):
                ending = sim.long_watch_ending()
            if ending:
                e = endings.get(ending, {})
                ecard = e.get("card")
                if ecard and ecard in cards:
                    r["pending_ending"] = ending
                    r["forced"].insert(0, ecard)
                else:
                    sim.end_run(ending)
            steps += 1
        lengths.append(r["watch"])
    total_watches = sum(lengths)
    print(f"runs {args.runs}, mean length {statistics.mean(lengths):.1f}, watches {total_watches}")
    print("resource  mean@10  mean@20  mean@30  mean@40  mean@50   %watches<=30  %watches>=70")
    for res in S.RESOURCES:
        means = [statistics.mean(traj[res][w]) if traj[res][w] else float('nan') for w in (10, 20, 30, 40, 50)]
        print(f"{res:8s} " + " ".join(f"{m:8.1f}" for m in means) + f"   {100 * low[res] / total_watches:6.1f}%      {100 * high[res] / total_watches:6.1f}%")
    for res in S.RESOURCES:
        top = contrib[res].most_common(5)
        bottom = contrib[res].most_common()[:-6:-1]
        print(f"{res}: biggest raisers {top} | biggest lowerers {bottom}")


if __name__ == "__main__":
    main()
