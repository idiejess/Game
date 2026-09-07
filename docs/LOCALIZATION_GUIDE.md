# Localization Guide — Halfway Lock

Only English ships. The pipeline is ready for more languages; nothing has been translated.

## How text reaches the screen
- **UI strings**: `content/localization/ui_<lang>.csv` (`key,text`), hand-authored, keys `ui.*`.
  Code calls `Loc.ui("key", "English fallback")`; a missing key shows the fallback, never the key.
- **Card text**: authored in the card JSON (`content/cards/**`). `tools/generate_reports.py --localization`
  mirrors every card's `text`, `text_variants`, `left`/`right` labels and outcomes to
  `content/localization/cards_<lang>.csv` with keys `card.<id>.<field>`. In-game, `Loc.card_text()`
  returns the CSV string for any language other than `en`, else the authored JSON.
- Both CSVs are marked `importer="keep"` so Godot ships them as plain files (see `.import` files).
  The game reads them with `FileAccess`, not Godot's `TranslationServer`.
- Language is `Settings.language`; changing it calls `Loc.load_language()`. There is no language
  picker in the Settings screen yet because there is only one language.

## Adding a language
1. Copy `ui_en.csv` to `ui_<lang>.csv` and translate the `text` column. Keep keys and `%s`/`%d`
   placeholders. Lines with an empty key are ignored.
2. Run `python3 tools/generate_reports.py --localization` to refresh `cards_en.csv`, copy it to
   `cards_<lang>.csv`, and translate the `text` column. Keys are stable (card IDs never change).
3. Add a `.import` file mirroring `ui_en.csv.import` (`importer="keep"`) or open the project once in
   the editor and set the import mode to *Keep File*.
4. Expose the language in the Settings screen (`Screens.gd::_settings`) with a `Settings.set_value("language", code)`
   control, then call `Loc.load_language(code)` and rebuild the current screen.
5. Run the engine tests; `test_localization_keys_present` should be extended to the new file.

## What is not yet localizable (known gaps)
- Ending titles and epilogues, arc titles in the Objectives screen, and character names/roles in
  the Gallery are read straight from `content/endings/endings.json`, `STORY_GRAPH.json` and
  `content/characters/*.json`. They need `loc_key` mirrors in the exporter and `Loc` lookups in
  `Screens.gd` (lines that call `.get("title", …)` and `ch["name"]`).
- Credits text and the content warning are in `ui_en.csv` already.
- Number formatting uses `%d`; no plural rules are needed by current strings.

## Style constraints for translators
- Card text is capped at ~48 words for crises and arc beats, 40 for ordinary cards; decision
  labels at 6 words. The card scrolls beyond that on phone height, but labels are truncated.
- Character voice notes are in `docs/CHARACTER_BIBLE.md`; telegrams are uppercase with STOP.
- Do not translate proper nouns listed in `docs/WORLD_BIBLE.md` unless the target language convention
  requires it; keep "Halfway", "Meridian", "Marrow Cut", "Hullfolk" consistent across all files.
