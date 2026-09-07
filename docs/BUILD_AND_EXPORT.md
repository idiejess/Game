# Build and Export — Halfway Lock

## Requirements
- Godot **4.7.2-stable** (GDScript only, no C#/GDExtension). Export templates 4.7.2.stable for Linux,
  Windows and Web. `.hoplite/settings.json` `scripts.setup` installs both on Linux x86_64.
- Python 3.10+ with `jsonschema`, `pillow`, `numpy` for the content/asset tooling (not needed to play).
- `ffmpeg` only if you regenerate music (`tools/build_audio.py`); WAV fallback otherwise.

## First run
```
godot --headless --import --path .          # imports resources into .godot/ (required once)
godot --headless --path . game/tests/TestRunner.tscn   # 250 checks, exit 0
godot --path .                               # play
```

## Verification suite (what CI or a reviewer should run)
```
python3 tools/validate_content.py            # schema, registries, allocation, endings reachable
python3 tools/analyze_dialogue.py            # voice/length/repetition analyzer (warnings only)
python3 tools/audit_arcs.py                  # arc continuity, prerequisites, true routes
python3 tools/validate_assets.py             # manifests <-> files <-> licence register
godot --headless --path . game/tests/TestRunner.tscn
python3 tools/simulate_runs.py --runs 2000 --out reports/simulations/simulation.json   # ~2 min
python3 tools/generate_reports.py --all      # docs/CONTENT_REPORT.md, docs/BALANCE_REPORT.md, cards_en.csv
python3 tools/build_credits.py               # CREDITS.md, THIRD_PARTY_NOTICES.md
```
`.hoplite/settings.json` `scripts.check` runs the first two and the engine tests.

## Exporting
Presets live in `export_presets.cfg` (Web, Linux, Windows, Android). Exclude filters keep
`reports/`, `tools/`, `docs/`, Markdown and Python out of the PCK; `content/**` JSON/CSV and the
asset manifests are included explicitly.

```
mkdir -p export/linux export/windows export/web
godot --headless --path . --export-release Linux   export/linux/halfway_lock.x86_64
godot --headless --path . --export-release Windows export/windows/halfway_lock.exe
godot --headless --path . --export-release Web     export/web/index.html
```
`export/` is git-ignored and carries a `.gdignore` so the editor never imports build output.

### Smoke test an export
Every build accepts `--smoke` (a user argument after `--`), which starts a run on a fixed seed,
plays 30 watches, saves to slot 3, reloads and compares state, then exits 0/1:
```
export/linux/halfway_lock.x86_64 --headless -- --smoke
```
Use `--dev` the same way to enable the dev panel (F12) in a release build.

### Web
Godot's web build needs cross-origin isolation headers. Serve with
`python3 tools/serve_web.py --port 3000` (adds COOP/COEP; `--export` rebuilds first). The preset is
single-threaded (`variant/thread_support=false`) so it works without SharedArrayBuffer on hosts that
cannot set headers, and uses the GL Compatibility renderer (WebGL 2). itch.io: upload the `export/web`
folder zipped, tick "SharedArrayBuffer support" only if you switch to the threaded template.

### Windows
Unsigned. `application/*` version fields are empty in the preset; fill `product_version`/`file_version`
before a public build. Code signing (`codesign/*`) needs a certificate the repository does not hold.
rcedit is not required for an unsigned build.

### Android (not built)
Preset exists (`package/unique_name=com.halfwaylock.$genname`, version 0.1.0/1). Needs the Android
SDK, a debug or release keystore and the Android export templates; none are in the sandbox.
Orientation is portrait (`display/window/handheld/orientation=4`).

### iOS / macOS (no preset)
Not attempted: both need Apple developer credentials. The project has no platform-specific code, so
adding a preset in the editor is the only step besides signing.

## Versioning
`project.godot` `config/version` and the Android `version/name` are both `0.1.0`; bump together.
Save files carry `SaveManager.SAVE_VERSION` (currently 2); extend `SaveManager.migrate()` when the schema changes (`test_save_migration_v1` covers the v1→v2 path).

## Results of the last export attempt (2026-09-06, sandbox)
| Target | Result | Verified by |
|---|---|---|
| Linux x86_64 | built (79 MB) | `--smoke` passes: 1000 cards, 30 watches, save/load round-trip |
| Windows x86_64 | built (115 MB, unsigned) | not executed (no Windows host); same PCK as Linux |
| Web | built (index.wasm 39 MB, index.pck 5.7 MB) | loads to title screen under `serve_web.py`; interactive play not verified because the sandbox browser has no WebGL 2 |
| Android | not built | no SDK/keystore |
