# Baseline Audit — Halfway Lock

- Date: 2026-09-06
- Branch: `hoplite/phleious-16c2ad27` (thread working branch; created from the imported snapshot tip)
- Initial commit SHA: `fdb5631a0afbca6e43cad4e2eec00d9d2502206e`
- Remote: `https://github.com/idiejess/Game.git`
- Note: the remote had **no `main` branch** at audit time; the only remote branch was
  `hoplite/aitna-17a46edb`, whose tip is identical to the imported snapshot. The draft PR
  therefore targets the repository's configured base branch rather than a literal `main`.
- Godot: 4.7.2.stable.official (`ed1daf0bf`) — **not preinstalled** in the sandbox despite
  `PROJECT_STATE.md` claiming otherwise; installed to `/usr/local/bin/godot` and recorded in
  `.hoplite/settings.json` setup script together with desktop/web export templates.
- Python: 3.12.3 (`jsonschema` 4.26, `pillow` 12.3, `numpy` 2.5 installed for tooling)

## Content
| Metric | Value |
|---|---|
| Cards | **1000** (inventory 1000, 0 missing) |
| onboarding / evergreen / resources / relationships | 30 / 220 / 150 / 120 |
| minor_arcs / major_arcs / crises / endings_meta | 180 / 180 / 70 / 50 |
| Character/source records | 25 |
| Major arcs / minor arcs | 12 (15 cards each) / 30 (6 cards each) |
| Endings | 40 (10 resource_death, 10 revelation, 6 ordinary, 6 false, 5 crisis, 3 true) |
| True-ending routes | 3 (`end_true_river`, `end_true_ledger`, `end_true_cut`) |
| Flags / counters declared | 164 / 29 |
| Localization | `cards_en.csv` 5024 rows, `ui_en.csv` 106 rows |

## Fresh tool runs
| Check | Command | Result |
|---|---|---|
| Content validation | `python3 tools/validate_content.py` | 1000 cards, **0 errors**, 1 warning (`assets/art_manifest.csv missing`) |
| Dialogue analysis | `python3 tools/analyze_dialogue.py` | 0 errors, **592 warnings** (523 situation-length >40 words, 40 outcome-length >24 words, 17 slang, 5 exclamation, 1 mechanics term, ~6 opener/voice) |
| Engine tests | `godot --headless --path . game/tests/TestRunner.tscn` | 169 checks, **4 failures** (documented `run_tests.gd` command with `--script` is wrong: the runner is a scene) |
| Smoke simulation | `python3 tools/simulate_runs.py --runs 200 --seed 1` | 192 runs, mean 56 watches, 0 stalls, 0 fallback runs, 296 cards unseen at this size |
| Godot startup | `godot --headless --path . --quit-after 120` | exits 0, no script errors |
| Export presets | `export_presets.cfg` | **missing** |

## Reproduced engine failures (all in the save system)
1. `test_save_load_roundtrip` — watch restored
2. `test_save_load_roundtrip` — resources restored
3. `test_save_load_roundtrip` — rng state restored
4. `test_save_migration_v1` — run number preserved

Root cause (single): Godot's `JSON.parse` returns every number as `float`. `SaveManager._sanitize_run`
and `_ensure_profile_keys` compare `typeof(value) != typeof(default)` against integer defaults, so
`watch`, `seed`, `rng_state`, `run_number`, `total_watches` and the whole `resources` dictionary
(float values `!=` int snapshot) were replaced by defaults on load. Flags/unlocks/history passed
because arrays keep their type. Fix: `SaveManager._read` now coerces whole-valued floats back to
ints recursively (`_coerce_numbers`), preserving atomic writes, backups, migration and rejection.
After the fix: 169 checks, 0 failures.

## Assets
- Portraits: 69 × 512×640 RGBA procedural placeholders (labelled). Backgrounds: 9 × 1080×1920. Icons: 12 × 64×64.
- Audio: 16 WAV mono 22050 Hz placeholders; all 5 music files are byte-identical 2 s silence.
- Duplicate binaries: `res_town.png` == `fac_town.png`; all five `mus_*.wav` identical.
- Missing: `assets/art_manifest.csv`, `assets/audio_manifest.csv`, prompts, contact sheets, license register.

## Stale or missing documentation
- `PROJECT_STATE.md` reports 591/1000 cards and Godot as preinstalled — both wrong.
- `docs/IMPLEMENTATION_PLAN.md` has almost every box unchecked despite completed work.
- Missing: `README.md`, `docs/REMAINING_WORK.md`, `docs/TEST_PLAN.md`, `docs/NARRATIVE_SYSTEM.md`,
  `docs/ACCESSIBILITY.md`, `docs/CONTENT_REPORT.md`, `docs/BALANCE_REPORT.md`, `docs/LOCALIZATION_GUIDE.md`,
  build/export/release/store docs, `PRIVACY.md`, `CREDITS.md`, `THIRD_PARTY_NOTICES.md`.
- `reports/simulations/probe.json` (2400 runs) predates the final content and shows 3 fallback runs.

## Highest-priority defects (ordered)
1. Save/load silently resets run state (fixed in this branch).
2. No export presets; no exports ever attempted.
3. `README.md`/`PROJECT_STATE.md` misleading about environment and progress.
4. Missing art/audio manifests and asset validator; music placeholders are silence.
5. Simulation: water-min death dominates (~75% of endings at small sample); true endings rare — needs large run.
6. Dialogue warnings: crisis-card situations routinely exceed the 40-word guideline; a few slang hits.
