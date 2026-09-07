# Asset Production Guide — Halfway Lock (art)

How to replace the procedural art candidates with final art without touching code.
Read `docs/ART_BIBLE.md` first for the visual language; this file is the workflow.

## Current state
- Every art asset the game references exists on disk and is listed in `assets/art_manifest.csv`
  (165 rows: 69 portraits, 27 icons, 2 app icons, 13 UI, 10 backgrounds, 4 branding, 40 optional ending illustrations).
- 125 files are **procedural candidates** produced by `tools/build_art.py` (deterministic; seed in the
  script). They are original, on-palette and consistent, but they are not final art. The 40 ending
  illustrations are optional; the ending screen falls back to a background when a file is absent.
- Nothing is approved. `user_approval_status` is `pending` on every row and tooling never changes it.
- No external asset has been sourced, so `docs/ASSET_LICENSE_REGISTER.csv` has a header only.

## Pipeline
```
tools/build_manifests.py   content + tables -> assets/art_manifest.csv, assets/audio_manifest.csv, assets/prompts/**
tools/build_art.py         manifest -> procedural PNGs (all, or --only <asset_id>)
tools/build_contact_sheet.py  -> reports/assets/*_sheet.png for visual review
tools/validate_assets.py   manifest <-> files <-> licence register; writes reports/assets/asset_validation.json
tools/build_credits.py     register + manifests -> CREDITS.md, THIRD_PARTY_NOTICES.md
```
In-game review: enable the dev panel (`Main.dev_tools_enabled()`: editor, debug export, or `--dev` on the command line; toggle with F12 as mapped in `toggle_dev_panel`), open
DevPanel → **Asset review** (`game/UI/AssetReview.gd`) to page through every manifest entry at
display size with its status.

## Specifications (from the manifest columns)
| Type | Size | Alpha | Notes |
|---|---|---|---|
| portrait | 512×640 (4:5) | yes | head centre at 42% height; nothing within 24 px of edges; same silhouette across expressions |
| icon (resource/faction) | 64×64, `@2x` 128×128 | yes | readable at 32 px; danger variant changes shape, not only colour |
| ui | per row | yes | dockets: one square corner |
| background | 1080×1920 | no | safe area: centre 1080×1500; the card covers the middle |
| ending_illustration | 1080×1080 | no | optional (`notes` contains "optional"); fallback is a background |
| branding | logo 1024×384, key art 1920×1080, capsule 1232×706, portrait key art 1080×1920, app icon 512/192 | mixed | store assets |

## Producing a final asset
1. Open the prompt file named in the row's `generation_prompt_file` (e.g. `assets/prompts/characters/bram_neutral.txt`).
   It carries the shared style prefix, the character sheet, the expression delta and the negative prompt.
   Prompts name no living artists, no other games, no real people; keep it that way.
2. Produce the image (hand-drawn, or generated with a tool whose output terms permit commercial use and
   do not claim rights over the output). Record the tool and its terms in `notes`.
3. Match the `width`/`height`/`alpha_required` columns exactly. Save as PNG to `destination_path/final_filename`,
   overwriting the candidate. Filenames never change, so no code or scene edits are needed.
4. Set `placeholder_status` to `final` and `generation_method` to what you did. Leave `user_approval_status`
   alone until a human has looked at it in the review gallery, then set it to `approved_by_user`.
5. Run `python3 tools/validate_assets.py` (dimensions, alpha, duplicates, filename pattern) and
   `python3 tools/build_contact_sheet.py`, then `godot --headless --path . game/tests/TestRunner.tscn`
   (`test_portraits_exist_for_every_expression`).

## Sourcing an existing asset (rare; portraits should never be sourced)
Allowed licences: CC0 first; otherwise public domain, MIT/Expat, OFL (fonts), or an explicit
commercial-use licence with attribution. **Never**: any NC/ND Creative Commons, "personal use",
"educational", "free for non-commercial", or an asset whose licence page you cannot link.

For each sourced file add a row to `docs/ASSET_LICENSE_REGISTER.csv` with every column filled
(source page URL, download URL, licence URL, download date, SHA-256 of the *original* download,
`license_evidence` = a quote or screenshot path). `tools/build_credits.py` refuses to run if a
column is empty or the licence contains a forbidden marker, and `tools/validate_assets.py` fails if
a manifest row with `placeholder_status = sourced_candidate` has no register row.
Then regenerate `CREDITS.md`/`THIRD_PARTY_NOTICES.md` with `python3 tools/build_credits.py`.

## Adding a new asset
Add it to the tables in `tools/build_manifests.py` (not to the CSV by hand), rerun the manifest
builder, then produce the file. Manifest ids are referenced by `AssetReview.gd` and the validators.

## Do not
- Rename or move files (the manifest and the scenes point at the current names).
- Change a portrait's silhouette between expressions.
- Add text, logos or watermarks inside images.
- Mark anything `approved_by_user` from a script.
