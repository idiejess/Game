# Halfway Lock — Keeper of the Meridian Canal

An original narrative decision game for phone, desktop and web, built in Godot 4.7.2 (GDScript).
You are the Keeper of Summit Lock No. 9. Every card is a vessel, petitioner, order or emergency;
drag it left or right. Keep five two-sided resources out of their danger bands, and stay in post long
enough to learn why the water is falling.

- 1,000 hand-written cards · 20 characters · 12 major and 30 minor storylines · 40 endings (3 true)
- Fully offline, no accounts, no tracking (`PRIVACY.md`)
- Accessibility options built in (`docs/ACCESSIBILITY.md`)

## Status
Release-candidate content and engine; **art and audio are original procedural candidates awaiting
human approval and final production**. See `docs/RELEASE_CHECKLIST.md` for the exact go/no-go state
and `docs/REMAINING_WORK.md` for open items.

## Play / build
```
godot --headless --import --path .     # once
godot --path .                         # play (F12 dev panel in editor/debug; `-- --dev` in exports)
godot --headless --path . game/tests/TestRunner.tscn   # engine tests
```
Exports, smoke test and web hosting: `docs/BUILD_AND_EXPORT.md`. Pre-built artefacts are not
committed; `export/` is ignored.

## Repository map
| Path | Contents |
|---|---|
| `game/` | Godot project code: autoloads (`ContentDB`, `GameState`, `CardSelector`, `SaveManager`, `AudioBus`, `Loc`, `Settings`), `systems/`, `UI/`, `scenes/`, `tests/` |
| `content/` | All game data: `cards/<category>/*.json`, `characters/`, `endings/endings.json`, `STORY_GRAPH.json`, registries, `localization/*.csv` |
| `schemas/` | JSON Schema for cards and content |
| `assets/` | Portraits, icons, UI, backgrounds, branding, audio; `art_manifest.csv`, `audio_manifest.csv`, `prompts/` |
| `tools/` | Python pipeline: validation, dialogue analysis, arc audit, simulation, report generation, asset builders, credits |
| `docs/` | Creative/world/character/narrative bibles, system docs, reports, production guides, release docs |
| `reports/` | Machine-readable validation, simulation and asset reports (screenshots are ignored) |

## Key documents
- Design: `docs/CREATIVE_BIBLE.md`, `docs/NARRATIVE_BIBLE.md`, `docs/WORLD_BIBLE.md`, `docs/CHARACTER_BIBLE.md`, `docs/WRITING_STYLE_GUIDE.md`
- Systems: `docs/NARRATIVE_SYSTEM.md`, `docs/CARD_SCHEMA.md`
- Quality: `docs/CONTENT_REPORT.md`, `docs/BALANCE_REPORT.md`, `reports/BASELINE_AUDIT.md`, `reports/validation/end_to_end_playtest.md`
- Production: `docs/ART_BIBLE.md`, `docs/AUDIO_BIBLE.md`, `docs/ASSET_PRODUCTION_GUIDE.md`, `docs/AUDIO_PRODUCTION_GUIDE.md`, `docs/LOCALIZATION_GUIDE.md`
- Release: `docs/BUILD_AND_EXPORT.md`, `docs/RELEASE_CHECKLIST.md`, `docs/STORE_COPY.md`, `docs/STORE_SUBMISSION_CHECKLIST.md`, `PRIVACY.md`, `CREDITS.md`, `THIRD_PARTY_NOTICES.md`
- History: `docs/DECISION_LOG.md`, `PROJECT_STATE.md`

## Content workflow
Edit card JSON (never rename ids), then:
```
python3 tools/validate_content.py && python3 tools/analyze_dialogue.py && python3 tools/audit_arcs.py
python3 tools/generate_reports.py --all
```
Asset workflow and licensing rules: `docs/ASSET_PRODUCTION_GUIDE.md`. Only CC0/original assets by
default; every sourced file must be recorded in `docs/ASSET_LICENSE_REGISTER.csv`.

## Licence
Game code, text, art and audio in this repository are original works of the project. Engine and
bundled component licences: `THIRD_PARTY_NOTICES.md`.
