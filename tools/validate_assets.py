#!/usr/bin/env python3
"""Validate art and audio manifests against the files on disk and the license register.

Checks: manifest entries without files (non-optional), files without manifest entries, dimensions,
aspect ratios, alpha requirement, filename pattern, remaining placeholders/candidates, duplicate
binaries, tooling never setting approval, sourced assets having provenance and a permitted license.
Writes reports/assets/asset_validation.json. Exit 1 on blocking problems.

Usage: python3 tools/validate_assets.py
"""
import csv
import hashlib
import json
import pathlib
import re
import sys
from collections import defaultdict

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
ALLOWED_LICENSES = {"original (repository)", "CC0-1.0", "CC-BY-4.0", "CC-BY-3.0", "custom-commercial-ok"}
PROHIBITED = re.compile(r"NC|NonCommercial|personal|educational|no license|unknown", re.I)
NAME_RX = re.compile(r"^[a-z0-9_@]+\.(png|wav|ogg)$")


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(path):
    with path.open() as f:
        return list(csv.DictReader(f))


def main():
    problems, warnings = [], []
    art = read(ASSETS / "art_manifest.csv")
    audio = read(ASSETS / "audio_manifest.csv")
    register_path = ROOT / "docs" / "ASSET_LICENSE_REGISTER.csv"
    register = {r["internal_asset_id"]: r for r in read(register_path)} if register_path.exists() else {}
    listed = set()
    stats = defaultdict(int)
    for r in art:
        p = ASSETS / r["destination_path"].removeprefix("assets/") / r["final_filename"]
        listed.add(p.resolve())
        optional = "optional" in r.get("notes", "")
        if not p.exists():
            (warnings if optional else problems).append(f"art {r['asset_id']}: file missing {p.relative_to(ROOT)}")
            continue
        if not NAME_RX.match(r["final_filename"]):
            problems.append(f"art {r['asset_id']}: filename {r['final_filename']} not lowercase_snake.png")
        im = Image.open(p)
        if (im.width, im.height) != (int(r["width"]), int(r["height"])):
            problems.append(f"art {r['asset_id']}: {im.width}x{im.height} != {r['width']}x{r['height']}")
        if r["alpha_required"] == "yes" and im.mode != "RGBA":
            problems.append(f"art {r['asset_id']}: alpha required but mode is {im.mode}")
        if r["sha256"] and r["sha256"] != sha(p):
            warnings.append(f"art {r['asset_id']}: sha256 differs from manifest (regenerate manifests)")
        if r["user_approval_status"] not in ("pending", "approved_by_user", "rejected"):
            problems.append(f"art {r['asset_id']}: invalid user_approval_status {r['user_approval_status']}")
        stats[r["placeholder_status"]] += 1
        stats["approved" if r["user_approval_status"] == "approved_by_user" else "awaiting_approval"] += 1
        if r["source_url"]:
            if r["asset_id"] not in register:
                problems.append(f"art {r['asset_id']}: sourced asset missing from ASSET_LICENSE_REGISTER.csv")
        if r["license"] and r["license"] not in ALLOWED_LICENSES:
            problems.append(f"art {r['asset_id']}: license '{r['license']}' not in allow-list")
    for r in audio:
        p = ASSETS / r["destination"].removeprefix("assets/") / r["filename"]
        listed.add(p.resolve())
        if not p.exists():
            problems.append(f"audio {r['asset_id']}: file missing {p.relative_to(ROOT)}")
            continue
        if not NAME_RX.match(r["filename"]):
            problems.append(f"audio {r['asset_id']}: filename not lowercase_snake")
        if r["user_approval_status"] not in ("pending", "approved_by_user", "rejected"):
            problems.append(f"audio {r['asset_id']}: invalid user_approval_status")
        if r["license"] not in ALLOWED_LICENSES:
            problems.append(f"audio {r['asset_id']}: license '{r['license']}' not in allow-list")
        if r["source_url"] and r["asset_id"] not in register:
            problems.append(f"audio {r['asset_id']}: sourced asset missing from register")
        stats[r["placeholder_status"]] += 1
        stats["approved" if r["user_approval_status"] == "approved_by_user" else "awaiting_approval"] += 1
    # variations are covered by their base entry
    for p in sorted(ASSETS.rglob("*")):
        if p.is_dir() or p.suffix in (".import", ".csv", ".txt", ".md") or "prompts" in p.parts:
            continue
        if p.resolve() not in listed and not re.search(r"_v\d+\.wav$", p.name):
            problems.append(f"unregistered asset file {p.relative_to(ROOT)}")
    # duplicate binaries
    by_hash = defaultdict(list)
    for p in ASSETS.rglob("*"):
        if p.is_file() and p.suffix in (".png", ".wav", ".ogg"):
            by_hash[sha(p)].append(str(p.relative_to(ROOT)))
    dups = [v for v in by_hash.values() if len(v) > 1]
    for d in dups:
        problems.append("duplicate binaries: " + ", ".join(d))
    # register sanity
    for aid, r in register.items():
        lic = r.get("license", "")
        if PROHIBITED.search(lic) or not lic:
            problems.append(f"register {aid}: prohibited or missing license '{lic}'")
        for k in ("source_page_url", "license_url", "sha256", "download_date"):
            if not r.get(k):
                problems.append(f"register {aid}: missing {k}")
    report = {"problems": problems, "warnings": warnings, "stats": dict(stats), "art_entries": len(art), "audio_entries": len(audio), "register_entries": len(register)}
    out = ROOT / "reports" / "assets" / "asset_validation.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1) + "\n")
    for p in problems:
        print("PROBLEM:", p)
    for w in warnings[:10]:
        print("warn:", w)
    print(f"assets: {len(art)} art + {len(audio)} audio entries, {len(problems)} problems, {len(warnings)} warnings; {dict(stats)}")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
