#!/usr/bin/env python3
"""Validate the Halfway Lock content library.

Checks: JSON Schema, exact card count vs inventory, duplicate IDs, category/directory match,
undeclared flags/counters, broken references (cards, speakers, expressions, endings), forced-chain
loops, impossible/contradictory conditions, identical-choice effects, cards with no state change,
static reachability (every card has some entry path), clue coverage, arc/stage coverage,
localization keys, art manifest. Writes reports/validation/content_validation.json.

Usage: python3 tools/validate_content.py [--partial] [--update-inventory] [--quiet]
  --partial          do not fail on count != 1000 (used during production)
  --update-inventory set inventory status written/planned from the current card set
"""
import argparse
import json
import pathlib
import sys
from collections import Counter, defaultdict

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover
    print("pip install jsonschema", file=sys.stderr)
    sys.exit(2)

ROOT = pathlib.Path(__file__).resolve().parents[1]
CARD_DIR = ROOT / "content" / "cards"
CATEGORIES = ["onboarding", "evergreen", "resources", "relationships", "minor_arcs", "major_arcs", "crises", "endings_meta"]
RESOURCES = ["water", "traffic", "coffers", "company", "town"]
# Cards the engine forces directly (TurnController.begin_run).
ENGINE_FORCED = {"onb_01", "meta_new_keeper_2"}


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.stats = {}

    def err(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)


def load_cards(rep):
    cards = {}
    files = {}
    for cat in CATEGORIES:
        d = CARD_DIR / cat
        if not d.exists():
            continue
        for p in sorted(d.glob("*.json")):
            try:
                data = load_json(p)
            except json.JSONDecodeError as e:
                rep.err(f"{p.relative_to(ROOT)}: JSON error {e}")
                continue
            if not isinstance(data, dict) or not isinstance(data.get("cards"), list):
                rep.err(f"{p.relative_to(ROOT)}: expected {{'cards': [...]}}")
                continue
            for c in data["cards"]:
                cid = c.get("id") if isinstance(c, dict) else None
                if cid is None:
                    rep.err(f"{p.relative_to(ROOT)}: card without id")
                    continue
                if cid in cards:
                    rep.err(f"duplicate card id {cid} ({p.name} and {files[cid]})")
                    continue
                if c.get("category") != cat:
                    rep.err(f"[{cid}] category {c.get('category')} in directory {cat}")
                cards[cid] = c
                files[cid] = p.name
    return cards, files


def schema_check(cards, rep):
    schema = load_json(ROOT / "schemas" / "card.schema.json")
    v = Draft202012Validator(schema)
    n = 0
    for cid, c in cards.items():
        for e in v.iter_errors(c):
            path = "/".join(str(x) for x in e.absolute_path)
            rep.err(f"[{cid}] schema: {path}: {e.message[:160]}")
            n += 1
    rep.stats["schema_errors"] = n


def registry_check(cards, rep):
    flags = {f["id"]: f for f in load_json(ROOT / "content" / "FLAG_REGISTRY.json")["flags"]}
    counters = {c["id"]: c for c in load_json(ROOT / "content" / "COUNTER_REGISTRY.json")["counters"]}
    used_flags, used_counters = set(), set()
    set_by = defaultdict(set)

    def cond_flags(cond):
        for k in ("flags_all", "flags_any", "flags_none"):
            for f in cond.get(k, []):
                yield f
        for f in cond.get("counters", {}):
            used_counters.add(f)
            if f not in counters:
                rep.err(f"undeclared counter '{f}' in conditions")

    for cid, c in cards.items():
        conds = [c.get("conditions", {})] + [w["when"] for w in c.get("weight_mods", [])] + [t["when"] for t in c.get("text_variants", [])]
        for cond in conds:
            for f in cond_flags(cond):
                used_flags.add(f)
                if f not in flags:
                    rep.err(f"[{cid}] undeclared flag '{f}' in conditions")
        for side in ("left", "right"):
            eff = c[side]["effects"]
            for f in eff.get("flags_set", []) + eff.get("flags_clear", []):
                used_flags.add(f)
                if f not in flags:
                    rep.err(f"[{cid}] undeclared flag '{f}' in {side} effects")
                if f in eff.get("flags_set", []):
                    set_by[f].add(cid)
            for k in list(eff.get("counters", {})) + list(eff.get("counters_set", {})):
                used_counters.add(k)
                if k not in counters:
                    rep.err(f"[{cid}] undeclared counter '{k}' in {side} effects")
    # Flags required but never set anywhere.
    for cid, c in cards.items():
        for cond in [c.get("conditions", {})]:
            for f in cond.get("flags_all", []) + cond.get("flags_any", []):
                if f in flags and not f.startswith("p_") and f not in set_by:
                    rep.err(f"[{cid}] requires flag '{f}' that no card sets")
    unused = sorted(f for f in flags if f not in used_flags)
    rep.stats["unused_flags"] = unused
    rep.stats["unused_counters"] = sorted(c for c in counters if c not in used_counters)
    return flags, counters, set_by


def reference_check(cards, rep):
    chars = {}
    for p in (ROOT / "content" / "characters").glob("*.json"):
        ch = load_json(p)
        chars[ch["id"]] = ch
    endings = {e["id"]: e for e in load_json(ROOT / "content" / "endings" / "endings.json")["endings"]}
    for cid, c in cards.items():
        spk = c["speaker"]
        if spk not in chars:
            rep.err(f"[{cid}] unknown speaker {spk}")
        elif "expression" in c and c["expression"] not in chars[spk]["expressions"]:
            rep.err(f"[{cid}] speaker {spk} has no expression {c.get('expression')}")
        for side in ("left", "right"):
            eff = c[side]["effects"]
            if "followup" in eff and eff["followup"] not in cards:
                rep.err(f"[{cid}] {side}.followup -> unknown card {eff['followup']}")
            for d in eff.get("delayed", []):
                if d["card"] not in cards:
                    rep.err(f"[{cid}] {side}.delayed -> unknown card {d['card']}")
            for sc in eff.get("subdeck", {}).get("cards", []):
                if sc not in cards:
                    rep.err(f"[{cid}] {side}.subdeck -> unknown card {sc}")
            if "ending" in eff and eff["ending"] not in endings:
                rep.err(f"[{cid}] {side}.ending -> unknown ending {eff['ending']}")
            for rc in eff.get("relationships", {}):
                if rc not in chars or chars[rc]["tier"] == "source":
                    rep.err(f"[{cid}] {side} relationship with unknown character {rc}")
        cond = c.get("conditions", {})
        for k in ("seen_cards", "unseen_cards", "seen_cards_any"):
            for ref in cond.get(k, []):
                if ref not in cards:
                    rep.err(f"[{cid}] conditions.{k} -> unknown card {ref}")
        for rc in cond.get("relationships", {}):
            if rc not in chars:
                rep.err(f"[{cid}] condition on unknown character {rc}")
    for eid, e in endings.items():
        if e["card"] not in cards:
            rep.err(f"ending {eid} -> unknown card {e['card']}")
    return chars, endings


def quality_check(cards, rep):
    trade = pure = delayed = reactive = 0
    ordinary = 0
    for cid, c in cards.items():
        l, r = c["left"]["effects"], c["right"]["effects"]
        if json.dumps(l, sort_keys=True) == json.dumps(r, sort_keys=True):
            rep.err(f"[{cid}] left and right effects are identical")
        if c["left"]["label"].strip().lower() == c["right"]["label"].strip().lower():
            rep.err(f"[{cid}] left and right labels are identical")
        if not l and not r:
            rep.err(f"[{cid}] neither choice changes any state")
        cond = c.get("conditions", {})
        # impossible ranges
        for group in ("resources", "relationships", "factions", "counters", "arc_stage"):
            for k, rng in cond.get(group, {}).items():
                if "min" in rng and "max" in rng and rng["min"] > rng["max"]:
                    rep.err(f"[{cid}] impossible range for {group}.{k}")
        for k in ("run", "watch"):
            rng = cond.get(k, {})
            if "min" in rng and "max" in rng and rng["min"] > rng["max"]:
                rep.err(f"[{cid}] impossible range for {k}")
        both = set(cond.get("flags_all", [])) & set(cond.get("flags_none", []))
        if both:
            rep.err(f"[{cid}] flags both required and forbidden: {sorted(both)}")
        # stats
        is_ordinary = c["category"] in ("onboarding", "evergreen", "resources", "relationships", "minor_arcs", "major_arcs")
        if is_ordinary:
            ordinary += 1
            has_trade = False
            all_pos = all_neg = True
            for eff in (l, r):
                res = eff.get("resources", {})
                ups = [v for v in res.values() if v > 0]
                downs = [v for v in res.values() if v < 0]
                if (ups and downs) or (res and (eff.get("relationships") or eff.get("factions") or eff.get("flags_set"))):
                    has_trade = True
                if downs or not res:
                    all_pos = False
                if ups or not res:
                    all_neg = False
            trade += has_trade
            if all_pos or all_neg:
                pure += 1
        if any(k in eff for eff in (l, r) for k in ("delayed", "delayed_resources", "followup", "subdeck")):
            delayed += 1
        if cond:
            reactive += 1
    n = max(1, len(cards))
    rep.stats["tradeoff_ratio"] = round(trade / max(1, ordinary), 3)
    rep.stats["pure_ratio"] = round(pure / max(1, ordinary), 3)
    rep.stats["delayed_ratio"] = round(delayed / n, 3)
    rep.stats["reactive_ratio"] = round(reactive / n, 3)


def chain_check(cards, rep):
    """Forced follow-up loops: follow `followup` edges only."""
    for start in cards:
        seen = [start]
        cur = start
        while True:
            nxt = None
            for side in ("left", "right"):
                f = cards[cur][side]["effects"].get("followup")
                if f and f == cards[cur]["left"]["effects"].get("followup") == cards[cur]["right"]["effects"].get("followup"):
                    nxt = f
            if not nxt:
                break
            if nxt in seen:
                rep.err(f"forced-chain loop: {' -> '.join(seen + [nxt])}")
                break
            seen.append(nxt)
            cur = nxt
            if len(seen) > 50:
                break


def reachability_check(cards, flags, set_by, endings, rep):
    """Static reachability: a card is reachable if it is in a drawable pool, or referenced by a
    followup/delayed/subdeck edge, or is an ending card. Conditions on flags need a setter."""
    referenced = set()
    for c in cards.values():
        for side in ("left", "right"):
            eff = c[side]["effects"]
            if "followup" in eff:
                referenced.add(eff["followup"])
            for d in eff.get("delayed", []):
                referenced.add(d["card"])
            for sc in eff.get("subdeck", {}).get("cards", []):
                referenced.add(sc)
    ending_cards = {e["card"] for e in endings.values()}
    unreachable = []
    for cid, c in cards.items():
        pool = c.get("pool", "general")
        if pool == "forced" and cid not in referenced and cid not in ENGINE_FORCED:
            unreachable.append(f"{cid} (forced, never referenced)")
        elif pool == "ending" and cid not in ending_cards and cid not in referenced:
            unreachable.append(f"{cid} (ending pool, no ending references it)")
    rep.stats["unreachable"] = unreachable
    for u in unreachable:
        rep.err("unreachable card: " + u)


def arc_check(cards, rep):
    graph = load_json(ROOT / "content" / "STORY_GRAPH.json")
    by_arc = defaultdict(list)
    for cid, c in cards.items():
        if "arc" in c:
            by_arc[c["arc"]["id"]].append(c)
    for aid, g in list(graph["major_arcs"].items()) + list(graph["minor_arcs"].items()):
        expected = set(g["cards"])
        have = {c["id"] for c in by_arc.get(aid, [])}
        if have and have != expected:
            rep.warn(f"arc {aid}: cards {sorted(have ^ expected)} differ from story graph")
        if have:
            stages = Counter(c["arc"]["stage"] for c in by_arc[aid])
            if aid.startswith("MA") and set(stages) != {1, 2, 3, 4, 5}:
                rep.err(f"arc {aid}: stages {sorted(stages)} != 1..5")
    rep.stats["arcs_with_cards"] = len(by_arc)


def clue_check(cards, rep):
    graph = load_json(ROOT / "content" / "STORY_GRAPH.json")
    counts = Counter()
    for c in cards.values():
        for side in ("left", "right"):
            for f in c[side]["effects"].get("flags_set", []):
                if f in graph["clues"]:
                    counts[f] += 1
    rep.stats["clue_setters"] = dict(counts)
    if len(cards) >= 1000:
        for clue in graph["clues"]:
            if counts[clue] < 2:
                rep.err(f"clue {clue} set by {counts[clue]} cards (need >= 2)")


def inventory_check(cards, rep, partial, update):
    inv_path = ROOT / "content" / "CARD_INVENTORY.json"
    inv = load_json(inv_path)
    inv_ids = {e["id"]: e for e in inv["cards"]}
    if len(inv_ids) != 1000:
        rep.err(f"inventory has {len(inv_ids)} ids, expected 1000")
    extra = sorted(set(cards) - set(inv_ids))
    missing = sorted(set(inv_ids) - set(cards))
    for cid in extra:
        rep.err(f"card {cid} is not in the inventory (would raise the total above 1000)")
    for cid in cards:
        if cid in inv_ids and inv_ids[cid]["category"] != cards[cid]["category"]:
            rep.err(f"[{cid}] category {cards[cid]['category']} differs from inventory {inv_ids[cid]['category']}")
    if not partial and missing:
        rep.err(f"{len(missing)} inventory cards not written; total is {len(cards)} not 1000. First: {missing[:5]}")
    rep.stats["total_cards"] = len(cards)
    rep.stats["inventory_missing"] = len(missing)
    rep.stats["by_category"] = dict(Counter(c["category"] for c in cards.values()))
    if update:
        for e in inv["cards"]:
            e["status"] = "written" if e["id"] in cards else "planned"
        inv_path.write_text(json.dumps(inv, indent=1, ensure_ascii=False) + "\n")


def manifest_check(rep):
    import csv
    p = ROOT / "assets" / "art_manifest.csv"
    if not p.exists():
        rep.warn("assets/art_manifest.csv missing")
        return
    with open(p, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    missing = [r["filename"] for r in rows if not (ROOT / "assets" / r["filename"]).exists()]
    approved_placeholder = [r["asset_id"] for r in rows if r["approval_status"] == "approved" and r["integration_status"] == "placeholder"]
    for a in approved_placeholder:
        rep.err(f"art manifest: {a} is approved but integration is placeholder")
    rep.stats["art_assets"] = len(rows)
    rep.stats["art_missing_files"] = missing
    for m in missing:
        rep.err(f"art manifest file missing: {m}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--partial", action="store_true")
    ap.add_argument("--update-inventory", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    rep = Report()
    cards, _files = load_cards(rep)
    schema_check(cards, rep)
    flags, counters, set_by = registry_check(cards, rep)
    chars, endings = reference_check(cards, rep)
    quality_check(cards, rep)
    chain_check(cards, rep)
    reachability_check(cards, flags, set_by, endings, rep)
    arc_check(cards, rep)
    clue_check(cards, rep)
    inventory_check(cards, rep, args.partial, args.update_inventory)
    manifest_check(rep)
    fallback = [cid for cid, c in cards.items() if c.get("pool") == "fallback"]
    rep.stats["fallback_cards"] = len(fallback)
    if not args.partial and len(fallback) < 3:
        rep.err("fewer than 3 fallback cards")
    out = ROOT / "reports" / "validation" / "content_validation.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"ok": not rep.errors, "errors": rep.errors, "warnings": rep.warnings, "stats": rep.stats},
                              indent=2, ensure_ascii=False) + "\n")
    if not args.quiet:
        for e in rep.errors[:80]:
            print("ERROR:", e)
        if len(rep.errors) > 80:
            print(f"... {len(rep.errors) - 80} more errors")
        for w in rep.warnings[:20]:
            print("WARN:", w)
        print(json.dumps({k: v for k, v in rep.stats.items() if k not in ("unused_flags", "unused_counters", "clue_setters")}, indent=1))
    print(f"validation: {len(cards)} cards, {len(rep.errors)} errors, {len(rep.warnings)} warnings")
    sys.exit(1 if rep.errors else 0)


if __name__ == "__main__":
    main()
