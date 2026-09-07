#!/usr/bin/env python3
"""Narrative continuity audit for major/minor arcs and true-ending routes.

For every arc, checks statically that:
  * the story graph card list matches the cards tagged with the arc;
  * stage numbers are contiguous and stage-1 cards have no `arc_stage` self-requirement;
  * every flag/unlock/counter a stage-N card requires is set by some card of stage < N of the same
    arc, or by a card outside the arc (documented as an external dependency);
  * at least one completion (`status: completed`) and, for major arcs, one failure route exist;
  * no card requires a flag that is only set by a card that requires the first flag (2-cycle).
For every true route, checks that the finale card's prerequisites (unlocks, route flag, allies
flag) have setters and that the ending card is only reachable via the ending pool.

Writes reports/content/arc_audit.json and prints a summary. Exit 1 on blocking problems.
Usage: python3 tools/audit_arcs.py [--verbose]
"""
import argparse
import json
import pathlib
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
ENGINE_FLAGS = set()  # flags the engine sets itself (none today; TurnController uses arc state)


def load():
    cards = {}
    for p in sorted((ROOT / "content" / "cards").glob("*/*.json")):
        for c in json.loads(p.read_text())["cards"]:
            cards[c["id"]] = c
    graph = json.loads((ROOT / "content" / "STORY_GRAPH.json").read_text())
    endings = {e["id"]: e for e in json.loads((ROOT / "content" / "endings" / "endings.json").read_text())["endings"]}
    return cards, graph, endings


def setters(cards):
    flag_set, unlock_set, counter_inc = defaultdict(set), defaultdict(set), defaultdict(set)
    for cid, c in cards.items():
        for side in ("left", "right"):
            eff = c[side]["effects"]
            for f in eff.get("flags_set", []):
                flag_set[f].add(cid)
            for u in eff.get("unlocks", []):
                unlock_set[u].add(cid)
            for k, v in eff.get("counters", {}).items():
                if v > 0:
                    counter_inc[k].add(cid)
            for k in eff.get("counters_set", {}):
                counter_inc[k].add(cid)
    for eid, e in json.loads((ROOT / "content" / "endings" / "endings.json").read_text()).items() if False else []:
        pass
    return flag_set, unlock_set, counter_inc


def requirements(card):
    cond = card.get("conditions", {})
    flags = list(cond.get("flags_all", [])) + list(cond.get("flags_any", []))
    unlocks = list(cond.get("unlocks", []))
    counters = [k for k, rng in cond.get("counters", {}).items() if "min" in rng and rng["min"] > 0]
    return flags, unlocks, counters


def audit_arc(aid, g, cards, flag_set, unlock_set, counter_inc, ending_unlocks, problems, notes):
    arc_cards = {cid: c for cid, c in cards.items() if c.get("arc", {}).get("id") == aid}
    expected = set(g["cards"])
    if set(arc_cards) != expected:
        problems.append(f"{aid}: card set differs from story graph: {sorted(set(arc_cards) ^ expected)}")
    stages = sorted({c["arc"]["stage"] for c in arc_cards.values()})
    want = list(range(1, 6)) if aid.startswith("MA") else list(range(1, 7))
    if stages != want:
        problems.append(f"{aid}: stages {stages} != {want}")
    stage_of = {cid: c["arc"]["stage"] for cid, c in arc_cards.items()}
    completed = any("completed" == c[s]["effects"].get("arc", {}).get(aid, {}).get("status") for c in arc_cards.values() for s in ("left", "right"))
    failed = any("failed" == c[s]["effects"].get("arc", {}).get(aid, {}).get("status") for c in arc_cards.values() for s in ("left", "right"))
    fires_ending = any(c[s]["effects"].get("ending") for c in arc_cards.values() for s in ("left", "right"))
    if not completed and not fires_ending:
        problems.append(f"{aid}: no card completes the arc or fires an ending")
    if aid.startswith("MA") and not failed:
        notes.append(f"{aid}: no explicit failure route (arc can only complete or stall by conditions)")
    # Within a stage the three cards chain (card 1 opens the stage; 2 and 3 require its flag), so at
    # least one stage-1 card must be free of any self-requirement.
    entry_cards = [cid for cid, st in stage_of.items() if st == 1]
    free_entry = [cid for cid in entry_cards if aid not in cards[cid].get("conditions", {}).get("arc_stage", {})]
    if not free_entry:
        problems.append(f"{aid}: every stage-1 card requires its own arc stage; arc can never start")
    external = set()
    for cid, c in arc_cards.items():
        st = stage_of[cid]
        flags, unlocks, counters = requirements(c)
        for f in flags:
            if f.startswith("p_"):
                continue
            src = flag_set.get(f, set())
            if not src:
                problems.append(f"{aid}: {cid} requires flag {f} that no card sets")
                continue
            earlier = {s for s in src if s in stage_of and stage_of[s] < st}
            same = {s for s in src if s in stage_of and stage_of[s] == st and s != cid}
            later = {s for s in src if s in stage_of and stage_of[s] > st}
            outside = src - set(stage_of)
            if not earlier and not outside and not same:
                problems.append(f"{aid}: {cid} (stage {st}) requires {f}, only set by later stage {sorted(later)} or itself")
            if same and not earlier and not outside:
                # same-stage chain: the setter must itself not require f (no 2-cycle)
                for s2 in same:
                    if f in requirements(cards[s2])[0]:
                        problems.append(f"{aid}: {cid} and {s2} both require {f} and only they set it (cycle)")
            if not earlier and outside:
                external.add(f)
        for u in unlocks:
            if not unlock_set.get(u) and u not in ending_unlocks:
                problems.append(f"{aid}: {cid} requires unlock {u} that nothing grants")
            elif not unlock_set.get(u):
                external.add(u + " (ending-granted)")
        for k in counters:
            if not counter_inc.get(k):
                problems.append(f"{aid}: {cid} requires counter {k} that nothing raises")
    if external:
        notes.append(f"{aid}: external prerequisites {sorted(external)}")
    # Every stage N>1 must have at least one card whose requirements are satisfiable from stage N-1
    for st in want[1:]:
        cands = [cid for cid, s in stage_of.items() if s == st]
        ok = False
        for cid in cands:
            cond = cards[cid].get("conditions", {})
            need = cond.get("arc_stage", {}).get(aid, {}).get("min", 0)
            if need <= st - 1:
                ok = True
        if not ok and cands:
            problems.append(f"{aid}: stage {st} has no card reachable from stage {st - 1} (all require arc_stage > {st - 1})")
    return {"cards": len(arc_cards), "stages": stages, "completes": completed, "fails": failed, "external": sorted(external)}


def audit_true_routes(graph, cards, endings, flag_set, unlock_set, problems, notes):
    out = {}
    for eid, route in graph["true_routes"].items():
        e = endings.get(eid)
        if not e:
            problems.append(f"true route {eid}: ending missing")
            continue
        finale = [cid for cid, c in cards.items() if any(c[s]["effects"].get("ending") == eid for s in ("left", "right"))]
        if not finale:
            problems.append(f"true route {eid}: no card fires the ending")
        for cid in finale:
            if cards[cid].get("pool") == "ending":
                problems.append(f"true route {eid}: finale {cid} is in the ending pool and can never be drawn")
        if cards.get(e["card"], {}).get("pool") != "ending":
            problems.append(f"true route {eid}: ending card {e['card']} must be pool 'ending'")
        rf = route.get("route_flag")
        if rf and not flag_set.get(rf):
            problems.append(f"true route {eid}: route flag {rf} never set")
        for u in route.get("requires_unlocks_all", []):
            granted = unlock_set.get(u) or any(u in x.get("unlocks", []) for x in endings.values())
            if not granted:
                problems.append(f"true route {eid}: unlock {u} never granted")
        two_of = route.get("requires_unlocks_two_of", [])
        granted = [u for u in two_of if unlock_set.get(u) or any(u in x.get("unlocks", []) for x in endings.values())]
        if len(granted) < 2:
            problems.append(f"true route {eid}: fewer than two of {two_of} can be granted")
        if not flag_set.get("allies_gathered"):
            problems.append("allies_gathered never set")
        out[eid] = {"finale_cards": finale, "route_flag_setters": sorted(flag_set.get(rf, [])), "unlocks_granted_by_cards": {u: sorted(unlock_set.get(u, [])) for u in route.get("requires_unlocks_all", []) + two_of}}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    cards, graph, endings = load()
    flag_set, unlock_set, counter_inc = setters(cards)
    ending_unlocks = {u for e in endings.values() for u in e.get("unlocks", [])}
    problems, notes, arcs = [], [], {}
    for aid, g in list(graph["major_arcs"].items()) + list(graph["minor_arcs"].items()):
        arcs[aid] = audit_arc(aid, g, cards, flag_set, unlock_set, counter_inc, ending_unlocks, problems, notes)
    routes = audit_true_routes(graph, cards, endings, flag_set, unlock_set, problems, notes)
    # Ending cards must never be in a drawable pool; forced cards must be referenced.
    for eid, e in endings.items():
        c = cards.get(e["card"])
        if c is None:
            problems.append(f"ending {eid}: card {e['card']} missing")
        elif c.get("pool") != "ending":
            problems.append(f"ending {eid}: card {e['card']} pool is {c.get('pool', 'general')}, expected 'ending'")
    report = {"problems": problems, "notes": notes, "arcs": arcs, "true_routes": routes}
    out = ROOT / "reports" / "content" / "arc_audit.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1) + "\n")
    for p in problems:
        print("PROBLEM:", p)
    if args.verbose:
        for n in notes:
            print("note:", n)
    print(f"arc audit: {len(arcs)} arcs, {len(routes)} true routes, {len(problems)} problems, {len(notes)} notes -> {out.relative_to(ROOT)}")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
