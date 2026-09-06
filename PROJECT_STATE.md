# PROJECT STATE — Halfway Lock

Last updated: 2026-09-06 (Phase 0/1 in progress)

## What this is
An original, data-driven narrative decision game built in Godot 4.7.2 (GDScript).
The player is the Keeper of Summit Lock No. 9 ("Halfway") on the Meridian Canal.
Every card is a vessel, petitioner, order or emergency demanding one of two decisions.
Exactly 1,000 playable decision cards are planned (see `content/CARD_INVENTORY.json`).

## Environment facts (verified in sandbox)
- Godot 4.7.2 stable, headless-capable, installed at `/usr/local/bin/godot`.
- Export templates 4.7.2 installed under `~/.local/share/godot/export_templates/4.7.2.stable`.
- Python 3.12 with `jsonschema` 4.26 for tooling.
- No image or audio generation tool is available in this sandbox. Placeholders are used and clearly labeled.

## Phase status
| Phase | Status | Notes |
|---|---|---|
| 0 Repository inspection | done | Repo was empty except `.hoplite/settings.json`. |
| 1 Creative foundation | done | Concept: **Halfway Lock**. All bibles written. |
| 2 Technical/narrative architecture | done | Schemas, registries, 1000-id inventory, story graph. |
| 3 Vertical slice | done | Engine, UI, save, selector, dev panel, tests, placeholders. |
| 4 Production tooling | done | validate_content, analyze_dialogue, simulate_runs, set_card_text, build_placeholders. |
| 5 Full content production | in progress | 591 / 1000 cards (onboarding 30, evergreen 220, resources 150, relationships 120, mi01 6, MA02 15, endings_meta 50). Remaining: 29 minor arcs (174), 11 major arcs (165), crises (70). |
| 6 Art and audio pipeline | pending | |
| 7 Balancing and narrative QA | pending | |
| 8 Polish and accessibility | pending | |
| 9 Release candidate | pending | |

## How to resume
1. Read `docs/IMPLEMENTATION_PLAN.md` for the phase checklist.
2. Read `docs/DECISION_LOG.md` for why things are the way they are.
3. Run `python3 tools/validate_content.py` (once created) to check content health.
4. Run `godot --headless --path . --script game/tests/run_tests.gd` (once created) for engine tests.
5. Check `docs/REMAINING_WORK.md` for open items.

## Key commands
- Run editor-less game: `godot --path .`
- Headless tests: `godot --headless --path . --script game/tests/run_tests.gd`
- Validate content: `python3 tools/validate_content.py`
- Simulate: `python3 tools/simulate_runs.py --runs 100000`
