#!/usr/bin/env python3
"""Generate human-readable reports from validation/simulation JSON and the content library.

  python3 tools/generate_reports.py --content      -> docs/CONTENT_REPORT.md
  python3 tools/generate_reports.py --balance      -> docs/BALANCE_REPORT.md (needs reports/simulations/simulation.json)
  python3 tools/generate_reports.py --localization -> content/localization/cards_en.csv
  python3 tools/generate_reports.py --all
"""
import argparse
import csv
import json
import pathlib
import time
from collections import Counter, defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
CATEGORIES = ["onboarding", "evergreen", "resources", "relationships", "minor_arcs", "major_arcs", "crises", "endings_meta"]


def load_cards():
    cards = {}
    for cat in CATEGORIES:
        for p in sorted((ROOT / "content" / "cards" / cat).glob("*.json")):
            for c in json.loads(p.read_text())["cards"]:
                cards[c["id"]] = c
    return cards


def content_report(cards):
    val = json.loads((ROOT / "reports" / "validation" / "content_validation.json").read_text())
    dia = json.loads((ROOT / "reports" / "content" / "dialogue_analysis.json").read_text())
    graph = json.loads((ROOT / "content" / "STORY_GRAPH.json").read_text())
    chars = {p.stem: json.loads(p.read_text()) for p in (ROOT / "content" / "characters").glob("*.json")}
    by_cat = Counter(c["category"] for c in cards.values())
    by_speaker = Counter(c["speaker"] for c in cards.values())
    by_pool = Counter(c.get("pool", "general") for c in cards.values())
    words = [len(c["text"].split()) for c in cards.values()]
    rel_per_major = Counter(c["speaker"] for c in cards.values() if c["category"] == "relationships")
    res_tag = Counter()
    for c in cards.values():
        if c["category"] == "resources":
            for t in c.get("tags", []):
                if t.startswith("res:"):
                    res_tag[t[4:]] += 1
    clue_setters = val["stats"].get("clue_setters", {})
    unlock_sources = Counter()
    for c in cards.values():
        for side in ("left", "right"):
            for u in c[side]["effects"].get("unlocks", []):
                unlock_sources[u] += 1
    lines = [
        "# Content Report — Halfway Lock", "",
        f"Generated {time.strftime('%Y-%m-%d %H:%M')} by `tools/generate_reports.py --content`.", "",
        "## Totals",
        f"- **Cards: {len(cards)}** (target 1000: {'OK' if len(cards) == 1000 else 'MISMATCH'})",
        f"- Validation errors: {len(val['errors'])}; warnings: {len(val['warnings'])}",
        f"- Dialogue analyzer errors: {len(dia['errors'])}; warnings: {len(dia['warnings'])}",
        f"- Characters: {sum(1 for c in chars.values() if c['tier'] != 'source')} ({sum(1 for c in chars.values() if c['tier'] == 'major')} major, {sum(1 for c in chars.values() if c['tier'] == 'supporting')} supporting) + {sum(1 for c in chars.values() if c['tier'] == 'source')} sources",
        f"- Arcs: {len(graph['major_arcs'])} major, {len(graph['minor_arcs'])} minor; endings: {len(graph['endings'])}; true routes: {len(graph['true_routes'])}", "",
        "## Allocation", "| Category | Count | Target |", "|---|---|---|",
    ]
    targets = {"onboarding": 30, "evergreen": 220, "resources": 150, "relationships": 120, "minor_arcs": 180, "major_arcs": 180, "crises": 70, "endings_meta": 50}
    for cat in CATEGORIES:
        lines.append(f"| {cat} | {by_cat[cat]} | {targets[cat]} |")
    lines += ["", "## Pools", "| Pool | Cards |", "|---|---|"] + [f"| {k} | {v} |" for k, v in sorted(by_pool.items())]
    lines += ["", "## Resource-reactive cards per resource", "| Resource | Cards |", "|---|---|"] + [f"| {k} | {v} |" for k, v in sorted(res_tag.items())]
    lines += ["", "## Relationship cards per major character", "| Character | Cards |", "|---|---|"] + [f"| {k} | {v} |" for k, v in sorted(rel_per_major.items())]
    lines += ["", "## Speaker distribution (all cards)", "| Speaker | Cards |", "|---|---|"] + [f"| {k} | {v} |" for k, v in by_speaker.most_common()]
    s = val["stats"]
    lines += ["", "## Style-guide ratios",
              f"- Tradeoff ratio (ordinary cards): **{s['tradeoff_ratio']:.1%}** (target ≥ 70%)",
              f"- Purely positive/negative (ordinary): **{s['pure_ratio']:.1%}** (target ≤ 20%)",
              f"- Cards with delayed/followup/subdeck effects: **{s['delayed_ratio']:.1%}** (target ≥ 25% including flag resolution; see note)",
              f"- State-reactive cards (have conditions): **{s['reactive_ratio']:.1%}** (target ≥ 30%)",
              f"- Situation length: min {min(words)}, mean {sum(words)/len(words):.1f}, max {max(words)} words", "",
              "Note on delayed consequences: the `delayed_ratio` counts only explicit `delayed`/`followup`/`subdeck` effects. "
              "Delayed consequences in this library are mostly carried by flags and counters (a choice sets `reeds_cargo`, a later card requires it). "
              "Counting cards that either set a flag consumed elsewhere or require a flag set elsewhere gives the figure below."]
    set_by, req_by = defaultdict(set), defaultdict(set)
    for cid, c in cards.items():
        for side in ("left", "right"):
            for f in c[side]["effects"].get("flags_set", []):
                set_by[f].add(cid)
        cond = c.get("conditions", {})
        for f in cond.get("flags_all", []) + cond.get("flags_any", []) + cond.get("flags_none", []):
            req_by[f].add(cid)
    consequence_cards = set()
    for f in set_by:
        if f in req_by and not f.startswith("met_"):
            consequence_cards |= set_by[f] | req_by[f]
    lines.append(f"- Cards that create or resolve a flag-carried consequence (excluding `met_*`): **{len(consequence_cards)/len(cards):.1%}**")
    lines += ["", "## Clue coverage (cards that set each clue flag)", "| Clue | Setters |", "|---|---|"] + [f"| {k} | {v} |" for k, v in sorted(clue_setters.items())]
    lines += ["", "## Unlock sources (cards granting each unlock)", "| Unlock | Cards |", "|---|---|"] + [f"| {k} | {v} |" for k, v in sorted(unlock_sources.items())]
    lines += ["", "## Analyzer warnings (top 30)"] + [f"- {w}" for w in dia["warnings"][:30]]
    lines += ["", "## Unused registry entries", f"- Flags: {', '.join(s.get('unused_flags', [])) or 'none'}", f"- Counters: {', '.join(s.get('unused_counters', [])) or 'none'}"]
    (ROOT / "docs" / "CONTENT_REPORT.md").write_text("\n".join(lines) + "\n")
    print("wrote docs/CONTENT_REPORT.md")


def _balance_assessment(sim):
    """Design-target comparison. Targets come from docs/NARRATIVE_BIBLE.md / DECISION_LOG D-009."""
    runs = sim["runs"] or 1
    ends = sim["endings"]

    def share(pred):
        return sum(v for k, v in ends.items() if k and pred(k)) / runs
    water = ends.get("end_res_water_min", 0) / runs
    in_band = sum(v for k, v in sim["length_distribution"].items()
                  if 40 <= int(k.split("-")[0]) < 120) / runs
    true_share = sum(sim["true_endings"].values()) / runs
    rev_share = share(lambda k: k.startswith("end_rev"))
    major = [a for a in sim["arc_entry_rate"] if a.startswith("MA")]
    major_done = sum(1 for a in major if sim["arc_completion_rate"].get(a, 0) > 0)
    keeper = sim["per_strategy"].get("keeper", {})
    keeper_100 = keeper.get("endings", {}).get("end_ord_long_watch", 0) / max(1, keeper.get("runs", 1))
    distinct = sum(1 for k, v in ends.items() if k and v > 0)
    rows = [
        ("Runs 40–119 watches", f"{in_band:.0%}", "majority", in_band >= 0.5),
        ("Median run length", str(sim["median_length"]), "40–120", 40 <= sim["median_length"] <= 120),
        ("Water-edge deaths (all strategies)", f"{water:.0%}", "dominant but < 70%", water < 0.70),
        ("Keeper strategy reaches watch 100", f"{keeper_100:.0%}", "≥ 30%", keeper_100 >= 0.3),
        ("Distinct endings reached", f"{distinct} / 40", "≥ 20 in 10k scripted runs", distinct >= 20),
        ("Revelation endings", f"{rev_share:.1%}", "1–10%", 0.01 <= rev_share <= 0.10),
        ("True endings", f"{true_share:.2%}", "rare (0.05–2%)", 0.0005 <= true_share <= 0.02),
        ("Major arcs completed at least once", f"{major_done} / {len(major)}", "12 / 12", major_done == len(major)),
        ("Stalls", str(sim["stalls"]), "0", sim["stalls"] == 0),
        ("Fallback-card runs", str(sim["fallback_runs"]), "< 1%", sim["fallback_runs"] / runs < 0.01),
        ("Unseen cards", str(sim["unseen_count"]), "informational", True),
    ]
    out = ["## Assessment against design targets", "| Metric | Value | Target | Status |", "|---|---|---|---|"]
    for name, val, tgt, ok in rows:
        out.append(f"| {name} | {val} | {tgt} | {'OK' if ok else 'ATTENTION'} |")
    out += ["",
            "Notes: strategies are scripted policies, not players; they never read clue text, so mystery "
            "endings and arc completions are lower bounds. Unseen cards are almost all late arc beats or "
            "resource cards gated on states (very high Town, very low Coffers, sustained Water ≥ 62) that "
            "scripted play rarely sustains; they are reachable by construction (see `reports/content/arc_audit.json`). "
            "Rows marked ATTENTION are tracked in `docs/REMAINING_WORK.md`.", ""]
    return out


def balance_report(cards):
    p = ROOT / "reports" / "simulations" / "simulation.json"
    if not p.exists():
        print("no simulation.json; run tools/simulate_runs.py first")
        return
    sim = json.loads(p.read_text())
    lines = ["# Balance Report — Halfway Lock", "",
             f"Generated {time.strftime('%Y-%m-%d %H:%M')} from `{p.relative_to(ROOT)}` ({sim['runs']} runs, {sim['seconds']}s, {len(sim['strategies'])} strategies).", ""]
    lines += _balance_assessment(sim)
    lines += ["## Run length", f"- Mean: **{sim['mean_length']}** watches; median: **{sim['median_length']}**",
             "", "| Watches | Runs |", "|---|---|"] + [f"| {k} | {v} |" for k, v in sim["length_distribution"].items()]
    lines += ["", "## Endings", "| Ending | Runs | Share |", "|---|---|---|"] + [f"| {k} | {v} | {v/sim['runs']:.1%} |" for k, v in sim["endings"].items()]
    lines += ["", "## Deaths by resource edge", "| Resource | Runs | Share of deaths |", "|---|---|---|"]
    total_deaths = sum(sim["death_by_resource"].values()) or 1
    for k, v in sorted(sim["death_by_resource"].items()):
        lines.append(f"| {k} | {v} | {v/total_deaths:.1%} |")
    lines += ["", f"## True endings reached: {sim['true_endings'] or 'none'}",
              "", f"## Stalls (no eligible card and no fallback): **{sim['stalls']}**",
              f"## Fallback-card runs: **{sim['fallback_runs']}** ({sim['fallback_total']} draws)",
              f"## Selection sources: {sim['selection_sources']}", "",
              f"## Unseen cards across all runs: **{sim['unseen_count']}**"] + [f"- {c}" for c in sim["unseen_cards"][:80]]
    lines += ["", f"## Rare cards (< 0.5% of runs): **{sim['rare_count']}**"] + [f"- {c}" for c in sim["rare_cards"][:40]]
    lines += ["", "## Most frequent cards", "| Card | Appearances |", "|---|---|"] + [f"| {c} | {n} |" for c, n in sim["overrepresented"]]
    lines += ["", "## Arc entry / completion rate", "| Arc | Entered | Completed |", "|---|---|---|"] + [f"| {a} | {sim['arc_entry_rate'][a]:.1%} | {sim['arc_completion_rate'].get(a, 0):.1%} |" for a in sim["arc_entry_rate"]]
    lines += ["", "## Character appearance rate (share of runs)", "| Speaker | Rate |", "|---|---|"] + [f"| {c} | {r:.1%} |" for c, r in sorted(sim["character_appearance_rate"].items(), key=lambda x: -x[1])]
    lines += ["", "## Unlock rate (share of runs with unlock in profile)", "| Unlock | Rate |", "|---|---|"] + [f"| {u} | {r:.1%} |" for u, r in sim["unlock_rate"].items()]
    lines += ["", "## Per strategy", "| Strategy | Runs | Mean length | Top endings |", "|---|---|---|---|"] + [f"| {n} | {d['runs']} | {d['mean_length']} | {', '.join(f'{k} {v}' for k, v in list(d['endings'].items())[:3])} |" for n, d in sim["per_strategy"].items()]
    (ROOT / "docs" / "BALANCE_REPORT.md").write_text("\n".join(lines) + "\n")
    print("wrote docs/BALANCE_REPORT.md")


def localization(cards):
    out = ROOT / "content" / "localization" / "cards_en.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["key", "text"])
        for cid in sorted(cards):
            c = cards[cid]
            prefix = c.get("loc_key", f"card.{cid}")
            w.writerow([f"{prefix}.text", c["text"]])
            for i, tv in enumerate(c.get("text_variants", [])):
                w.writerow([f"{prefix}.text_variant{i}", tv["text"]])
            for side in ("left", "right"):
                w.writerow([f"{prefix}.{side}", c[side]["label"]])
                if c[side].get("outcome"):
                    w.writerow([f"{prefix}.{side}_outcome", c[side]["outcome"]])
    print(f"wrote {out.relative_to(ROOT)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--content", action="store_true")
    ap.add_argument("--balance", action="store_true")
    ap.add_argument("--localization", action="store_true")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    cards = load_cards()
    if a.content or a.all:
        content_report(cards)
    if a.balance or a.all:
        balance_report(cards)
    if a.localization or a.all:
        localization(cards)


if __name__ == "__main__":
    main()
