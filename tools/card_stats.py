#!/usr/bin/env python3
"""Compact statistics over the card library for writing QA (no card text is dumped).

Reports identical labels, identical effects, opener repetition, label repetition, text length
extremes, UI-fit risks (character counts) and per-speaker counts. Read-only.

Usage: python3 tools/card_stats.py [--json out.json]
"""
import argparse
import collections
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]


def words(s):
    return re.findall(r"[A-Za-z']+", s)


def load_cards():
    cards = []
    for p in sorted((ROOT / "content" / "cards").glob("*/*.json")):
        cards += json.loads(p.read_text())["cards"]
    return cards


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    args = ap.parse_args()
    cards = load_cards()
    same_label = [c["id"] for c in cards if c["left"]["label"].strip().lower() == c["right"]["label"].strip().lower()]
    same_eff = [c["id"] for c in cards if json.dumps(c["left"]["effects"], sort_keys=True) == json.dumps(c["right"]["effects"], sort_keys=True)]
    openers2 = collections.Counter(" ".join(words(c["text"])[:2]).lower() for c in cards)
    openers3 = collections.Counter(" ".join(words(c["text"])[:3]).lower() for c in cards)
    labels = collections.Counter(c[s]["label"].strip().lower() for c in cards for s in ("left", "right"))
    lengths = [len(words(c["text"])) for c in cards]
    text_chars = sorted(((len(c["text"]), c["id"]) for c in cards), reverse=True)
    label_chars = sorted(((len(c[s]["label"]), c["id"], s) for c in cards for s in ("left", "right")), reverse=True)
    outcome_chars = sorted(((len(c[s].get("outcome", "")), c["id"], s) for c in cards for s in ("left", "right")), reverse=True)
    speakers = collections.Counter(c["speaker"] for c in cards)
    excl = [c["id"] for c in cards if c["text"].count("!") > 1]
    report = {
        "cards": len(cards),
        "same_label_both_sides": same_label,
        "same_effects_both_sides": same_eff,
        "top_openers_2": openers2.most_common(15),
        "top_openers_3": openers3.most_common(15),
        "top_labels": labels.most_common(15),
        "situation_words": {"max": max(lengths), "over_40": sum(1 for x in lengths if x > 40), "over_45": sum(1 for x in lengths if x > 45), "over_50": sum(1 for x in lengths if x > 50)},
        "longest_text_chars": text_chars[:10],
        "longest_label_chars": label_chars[:10],
        "longest_outcome_chars": outcome_chars[:10],
        "multi_exclamation": excl,
        "speakers": dict(speakers),
    }
    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(report, indent=1) + "\n")
    for k, v in report.items():
        print(k, ":", v)


if __name__ == "__main__":
    main()
