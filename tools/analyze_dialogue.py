#!/usr/bin/env python3
"""Semantic/style analysis of card text per docs/WRITING_STYLE_GUIDE.md.

Checks: situation length 6-32 words (endings_meta up to 60), label length 1-8 words,
banned phrases, slang, mechanics words, per-speaker prohibited phrases, exclamation rules,
punctuation density, repeated openers (>3% same first two words), exact duplicate texts,
near-duplicate texts (token Jaccard >= 0.8), repeated choice labels (>6 uses).
Writes reports/content/dialogue_analysis.json. Exit 1 on errors (warnings do not fail).

Usage: python3 tools/analyze_dialogue.py [--files a.json b.json] [--strict]
"""
import argparse
import json
import pathlib
import re
import sys
from collections import Counter, defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
BANNED = ["the air is thick", "little did", "a chill ran", "you can't help but", "in a world where", "delve", "tapestry",
          "testament to", "palpable", "unbeknownst", "a testament"]
SLANG = ["okay", "guys", "cool.", "yeah", "hey,", "bro", "whatever", "no way"]
MECHANICS = ["resource", "flag", " stat ", "points", "level up", "unlock", "cooldown"]
NO_EXCLAIM = {"vosk", "bram", "solas", "crane"}


def words(s):
    return re.findall(r"[A-Za-z']+", s)


def tokens(s):
    return set(w.lower() for w in words(s) if len(w) > 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", nargs="*")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()
    chars = {p.stem: json.loads(p.read_text()) for p in (ROOT / "content" / "characters").glob("*.json")}
    files = [pathlib.Path(f) for f in args.files] if args.files else sorted((ROOT / "content" / "cards").glob("*/*.json"))
    cards = []
    for p in files:
        try:
            cards += json.loads(p.read_text())["cards"]
        except Exception as e:  # noqa
            print("ERROR:", p, e)
            sys.exit(1)
    errors, warnings = [], []
    openers = Counter()
    texts = {}
    labels = Counter()
    for c in cards:
        cid, t = c["id"], c["text"]
        low = t.lower()
        n = len(words(t))
        limit = {"endings_meta": 60, "relationships": 40, "major_arcs": 40}.get(c["category"], 32)
        if n < 6 or n > limit:
            (errors if n > limit + 8 or n < 4 else warnings).append(f"[{cid}] situation {n} words (6-{limit})")
        for side in ("left", "right"):
            lab = c[side]["label"]
            ln = len(words(lab))
            if ln < 1 or ln > 8:
                errors.append(f"[{cid}] {side} label {ln} words")
            labels[lab.strip().lower()] += 1
            out = c[side].get("outcome", "")
            if len(words(out)) > 24:
                warnings.append(f"[{cid}] {side} outcome {len(words(out))} words (>24)")
        for b in BANNED:
            if b in low:
                errors.append(f"[{cid}] banned phrase '{b}'")
        for s in SLANG:
            if re.search(r"\b" + re.escape(s.strip(".,")) + r"\b", low):
                warnings.append(f"[{cid}] slang '{s.strip()}'")
        if c["speaker"] != "src_ledger":
            for m in MECHANICS:
                if m in low and "unlock" not in low.replace("unlocked the", ""):
                    warnings.append(f"[{cid}] mechanics word '{m.strip()}'")
        spk = c["speaker"]
        ch = chars.get(spk, {})
        for ph in ch.get("prohibited_phrases", []):
            if ph == "!":
                continue
            if ph.lower() in low:
                warnings.append(f"[{cid}] {spk} uses prohibited phrase '{ph}'")
        if spk in NO_EXCLAIM and "!" in t:
            errors.append(f"[{cid}] {spk} never exclaims")
        if t.count("!") > 1:
            warnings.append(f"[{cid}] {t.count('!')} exclamation marks")
        if t.count("...") + t.count("\u2026") + t.count("\u2014") > 1:
            warnings.append(f"[{cid}] too many ellipses/dashes")
        qs = t.count("?")
        if qs > 1 and spk not in ("mirren", "fennick"):
            warnings.append(f"[{cid}] {qs} questions")
        first_two = " ".join(words(t)[:2]).lower()
        openers[first_two] += 1
        key = re.sub(r"\W+", " ", low).strip()
        if key in texts:
            errors.append(f"[{cid}] duplicate text of {texts[key]}")
        texts[key] = cid
    # near duplicates
    toks = [(c["id"], tokens(c["text"])) for c in cards]
    for i in range(len(toks)):
        for j in range(i + 1, len(toks)):
            a, b = toks[i][1], toks[j][1]
            if len(a) > 5 and len(b) > 5:
                jac = len(a & b) / len(a | b)
                if jac >= 0.8:
                    warnings.append(f"near-duplicate {toks[i][0]} ~ {toks[j][0]} ({jac:.2f})")
    total = max(1, len(cards))
    for op, k in openers.most_common(10):
        if k / total > 0.03 and k > 3:
            warnings.append(f"opener '{op}' used by {k} cards ({k / total:.1%})")
    for lab, k in labels.most_common(20):
        if k > 6:
            warnings.append(f"label '{lab}' used {k} times")
    speakers = Counter(c["speaker"] for c in cards)
    report = {"cards": len(cards), "errors": errors, "warnings": warnings, "speakers": dict(speakers),
              "top_openers": openers.most_common(10), "top_labels": labels.most_common(10)}
    out = ROOT / "reports" / "content" / "dialogue_analysis.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    for e in errors:
        print("ERROR:", e)
    for w in warnings[:60]:
        print("WARN:", w)
    print(f"dialogue: {len(cards)} cards, {len(errors)} errors, {len(warnings)} warnings")
    sys.exit(1 if errors or (args.strict and warnings) else 0)


if __name__ == "__main__":
    main()
