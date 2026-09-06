# PROJECT STATE — Halfway Lock

Last updated: 2026-09-06 — milestone 2 (save/load repair) on branch `hoplite/phleious-16c2ad27`.

## What this is
An original, data-driven narrative decision game built in Godot 4.7.2 (GDScript).
The player is the Keeper of Summit Lock No. 9 ("Halfway") on the Meridian Canal.
Every card is a vessel, petitioner, order or emergency demanding one of two decisions.
Exactly 1,000 playable decision cards ship (see `content/CARD_INVENTORY.json`).

## Verified status (fresh runs, see `reports/BASELINE_AUDIT.md`)
| Item | Status |
|---|---|
| Cards | **1000 / 1000** — onboarding 30, evergreen 220, resources 150, relationships 120, minor_arcs 180, major_arcs 180, crises 70, endings_meta 50 |
| Characters / arcs / endings | 25 records; 12 major (15 cards) + 30 minor (6 cards); 40 endings, 3 true routes |
| Content validation | 0 errors, 1 warning (art manifest missing — pending milestone 7) |
| Dialogue analysis | 0 errors, 592 warnings (mostly length guideline; targeted QA pending) |
| Engine tests | **202 checks, 0 failures**, run twice from clean state |
| Save/load | Fixed: JSON float→int coercion (`SaveManager._coerce_numbers`); full-state + RNG-continuation regression tests added |
| Simulation | 200-run smoke: 0 stalls, 0 fallbacks; large run pending |
| Exports | No presets yet (milestone 8) |
| Visual assets | Procedural placeholders only, labelled; no manifest yet |
| Audio assets | Procedural placeholders; music files are silence; no manifest yet |
| Human approval needed | All visual and audio assets |

## Environment facts (verified in sandbox)
- Godot 4.7.2 stable is **not** preinstalled; `.hoplite/settings.json` setup installs it plus
  Linux/Windows/Web export templates.
- Python 3.12 with `jsonschema`, `pillow`, `numpy`.
- No image or audio generation service is available; placeholders are procedural and labelled.

## Key commands
- Import resources (first run): `godot --headless --import --path .`
- Run the game: `godot --path .`
- Engine tests: `godot --headless --path . game/tests/TestRunner.tscn`
- Smoke play: `godot --headless --path . game/tests/Smoke.tscn`
- Validate content: `python3 tools/validate_content.py`
- Dialogue analysis: `python3 tools/analyze_dialogue.py`
- Simulate: `python3 tools/simulate_runs.py --runs 10000 --out reports/simulations/simulation.json`
- Reports/localization: `python3 tools/generate_reports.py`

## How to resume
1. Read `docs/REMAINING_WORK.md` for open items.
2. Read `docs/DECISION_LOG.md` for why things are the way they are.
3. Run the key commands above before changing anything.
