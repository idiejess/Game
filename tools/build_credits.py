#!/usr/bin/env python3
"""Generate CREDITS.md and THIRD_PARTY_NOTICES.md from the asset register and manifests.

Never hand-edit those two files: rerun this after changing
  docs/ASSET_LICENSE_REGISTER.csv   (every externally sourced asset, with provenance)
  assets/art_manifest.csv / assets/audio_manifest.csv
  reports/licenses/godot_copyright.txt (godot --headless --path . --script tools/dump_engine_licenses.gd)

Usage: python3 tools/build_credits.py
"""
import csv
import pathlib
import subprocess
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
REGISTER = ROOT / "docs" / "ASSET_LICENSE_REGISTER.csv"
ART = ROOT / "assets" / "art_manifest.csv"
AUDIO = ROOT / "assets" / "audio_manifest.csv"
ENGINE = ROOT / "reports" / "licenses" / "godot_copyright.txt"

# Licences this project accepts for shipped assets (see docs/ASSET_PRODUCTION_GUIDE.md).
ALLOWED = {"CC0-1.0", "CC0", "Public Domain", "OFL-1.1", "MIT", "Expat", "Apache-2.0", "BSD-2-clause",
           "BSD-3-clause", "Zlib", "Unlicense", "original (repository)"}
FORBIDDEN_MARKERS = ("NC", "ND", "personal", "educational", "non-commercial", "noncommercial")


def read_csv(p):
    if not p.exists():
        return []
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def ensure_engine_dump():
    if ENGINE.exists():
        return
    ENGINE.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(["godot", "--headless", "--path", str(ROOT), "--script", "tools/dump_engine_licenses.gd"],
                       check=True, capture_output=True, timeout=120)
    except Exception as e:  # noqa: BLE001
        print(f"warning: could not dump engine licences ({e}); THIRD_PARTY_NOTICES.md will omit the engine list")


def engine_components():
    if not ENGINE.exists():
        return "", []
    text = ENGINE.read_text(encoding="utf-8")
    head, _, tail = text.partition("THIRD-PARTY COMPONENTS BUNDLED IN THE GODOT ENGINE BINARY")
    comps = []
    cur = None
    for line in tail.splitlines():
        if line.startswith("== "):
            cur = {"name": line[3:].strip(), "copyright": [], "license": []}
            comps.append(cur)
        elif cur and line.strip().startswith("Copyright "):
            cur["copyright"].append(line.strip()[len("Copyright "):])
        elif cur and line.strip().startswith("License: "):
            cur["license"].append(line.strip()[len("License: "):])
    return head.replace("GODOT ENGINE LICENSE", "").strip(), comps


def main():
    ensure_engine_dump()
    register = read_csv(REGISTER)
    art = read_csv(ART)
    audio = read_csv(AUDIO)
    problems = []
    for r in register:
        lic = r.get("license", "")
        if any(m.lower() in lic.lower() for m in FORBIDDEN_MARKERS):
            problems.append(f"{r['internal_asset_id']}: licence '{lic}' is not permitted")
        for col in ("source_page_url", "license_url", "download_date", "sha256", "license_evidence"):
            if not r.get(col):
                problems.append(f"{r['internal_asset_id']}: register column '{col}' is empty")
    if problems:
        for p in problems:
            print("ERROR", p)
        raise SystemExit(1)

    stamp = time.strftime("%Y-%m-%d")
    external = {r["internal_asset_id"]: r for r in register}
    proc_art = [a for a in art if a["asset_id"] not in external and (ROOT / a["destination_path"] / a["final_filename"]).exists()]
    proc_audio = [a for a in audio if a["asset_id"] not in external and (ROOT / a["destination"] / a["filename"]).exists()]
    attributions = [r for r in register if r.get("attribution_required", "").lower() in ("yes", "true", "1")]

    credits = [
        "# Credits — Halfway Lock", "",
        f"Generated {stamp} by `tools/build_credits.py` from `docs/ASSET_LICENSE_REGISTER.csv` and the asset manifests. Do not edit by hand.", "",
        "## Game",
        "- Design, writing, code, procedural art and audio: the Halfway Lock project repository (original work).",
        "- Built with the [Godot Engine](https://godotengine.org) 4.7.2 (MIT licence; see `THIRD_PARTY_NOTICES.md`).", "",
        "## Original assets",
        f"- {len(proc_art)} art assets and {len(proc_audio)} audio assets are original to this repository, produced by "
        "`tools/build_art.py` and `tools/build_audio.py` (procedural). They carry no third-party rights.", "",
        "## Externally sourced assets",
    ]
    if not register:
        credits.append("- None. Every shipped asset is original to this repository.")
    else:
        credits += ["| Asset | Title | Creator | Licence | Source |", "|---|---|---|---|---|"]
        for r in register:
            credits.append(f"| {r['internal_asset_id']} | {r['original_title']} | {r['creator']} | {r['license']} | {r['source_page_url']} |")
    credits += ["", "## Attribution notices"]
    if not attributions:
        credits.append("- No shipped asset requires attribution. CC0 and original assets are credited above as a courtesy.")
    else:
        for r in attributions:
            credits.append(f"- \"{r['original_title']}\" by {r['creator']}, licensed {r['license']} ({r['license_url']}); {r['modifications'] or 'unmodified'}.")
    credits += ["", "## Fonts",
                "- Noto Sans (Godot's bundled default font), SIL Open Font License 1.1. No additional fonts are shipped.", ""]
    (ROOT / "CREDITS.md").write_text("\n".join(credits))

    lic_text, comps = engine_components()
    notices = [
        "# Third-Party Notices — Halfway Lock", "",
        f"Generated {stamp} by `tools/build_credits.py`. Do not edit by hand.", "",
        "Halfway Lock ships as a Godot Engine export. The export binary embeds the Godot Engine and the "
        "third-party components listed below, each under its own licence. The game's own code, text, art "
        "and audio are original to this repository unless listed in `CREDITS.md`.", "",
        "## Godot Engine", "", "```", lic_text, "```", "",
        "## Third-party components bundled in the engine binary", "",
        "Copyright holders and licences as reported by `Engine.get_copyright_info()` for Godot 4.7.2. "
        "The full licence texts are available from https://godotengine.org/license and in the Godot source "
        "tree (`COPYRIGHT.txt`, `thirdparty/`).", "",
        "| Component | Licence | Copyright |", "|---|---|---|",
    ]
    for c in comps:
        cp = "; ".join(c["copyright"][:3]) + (" …" if len(c["copyright"]) > 3 else "")
        notices.append(f"| {c['name']} | {', '.join(sorted(set(c['license'])))} | {cp.replace('|', '/')} |")
    notices += ["", "## Externally sourced game assets", ""]
    if not register:
        notices.append("None. See `CREDITS.md`.")
    else:
        for r in register:
            notices += [f"### {r['internal_asset_id']} — {r['original_title']}",
                        f"- Creator: {r['creator']}", f"- Licence: {r['license']} ({r['license_url']})",
                        f"- Source: {r['source_page_url']}", f"- Modifications: {r['modifications'] or 'none'}",
                        f"- SHA-256 of original download: `{r['sha256']}`", ""]
    notices += ["", "## Python tooling (not shipped)",
                "The content pipeline under `tools/` uses Python 3 with `jsonschema` (MIT), `Pillow` (MIT-CMU) and "
                "`numpy` (BSD-3-Clause). These run at development time only and are not part of the game binary.", ""]
    (ROOT / "THIRD_PARTY_NOTICES.md").write_text("\n".join(notices))
    print(f"wrote CREDITS.md ({len(register)} external assets) and THIRD_PARTY_NOTICES.md ({len(comps)} engine components)")


if __name__ == "__main__":
    main()
