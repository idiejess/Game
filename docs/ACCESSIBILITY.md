# Accessibility — Halfway Lock

What the game does for accessibility, how each item was verified, and what still needs a human.
Settings live in `game/autoload/Settings.gd` (persisted at `user://settings.json`, separate from saves)
and are exposed on the Settings screen (`game/UI/Screens.gd::_settings`).

## Implemented and verified automatically

| Feature | Setting key | Where | Verification |
|---|---|---|---|
| Text size 0.8×–1.6× | `text_scale` | `UITheme.build()`, `UITheme.font_size()`; every Label/Button/RichText reads the theme | Screenshot harness at 1.0 and 1.6 (`reports/screenshots/*/02b_longest_card.png`); longest card scrolls rather than clipping |
| High contrast | `high_contrast` | `UITheme.build()` swaps the slate/chalk palette for black/white with the same accent | Screenshot `07_settings.png`; `test_accessibility_settings` asserts label/panel luminance contrast > 0.5 in both modes |
| Reduced motion | `reduced_motion` | `Settings.motion_scale()` used by `CardView`, `ResourceMeter`, `WaterLine`, `Main` | `test_accessibility_settings` asserts `motion_scale()` is 0 when set; every tween duration is multiplied by it |
| Screen shake off | `screen_shake` | `Main._apply_effect_feedback` | Code path guarded; covered by `--smoke` run |
| Decision buttons (no drag required) | `show_buttons` | `Main` left/right buttons mirror the swipe | Buttons used by the smoke test and screenshots `03_preview_right.png` |
| Confirm decisions | `confirm_decisions` | `Main._commit` requires the same side twice | Code path reviewed; no automated test |
| Exact effect numbers | `show_exact_effects` | `ResourceMeter` shows numeric readout and signed preview | Screenshot `05_danger_meters.png` |
| Subtitles for audio cues | `subtitles` | `AudioBus.play()` emits a caption for every cue that has one in `ui_en.csv` (`ui.audio.*`) | `test_accessibility_settings` checks every captioned cue has text in `ui_en.csv` |
| Colour is never the only signal | — | Meters use glyph + name + border + danger text; decision tabs are labelled | Manual review of contact sheets and screenshots |
| Keyboard play | — | ← / A previews left, → / D previews right, release commits; Esc pauses; every screen focuses its first control; focus ring is a 4 px accent border | `--smoke` plays through input actions; `Screens.gd` grabs focus on open |
| Touch targets | — | Buttons ≥ 80–96 px tall on a 1080-wide canvas (≈ 40–48 dp on phones); card accepts full-surface drag | Layout constants in `Screens.gd`; phone/narrow screenshot sets |
| Portrait + landscape + narrow | — | `canvas_items` stretch, `expand` aspect; `CardView` prioritises text over portrait when short on height | `reports/screenshots/{desktop,phone,narrow,narrow_xl}` |
| Content warning before first run | — | `ui.content_warning_text` shown once (`content_warnings_seen`) | Screenshot harness step 1 |
| Save anywhere / resume | — | Autosave every watch; three manual slots | `EngineTests.gd` save/load suite |
| No timers, no reflex requirement | — | Turn-based; cards wait indefinitely | By design |

## Localization readiness
All UI strings go through `Loc.ui()` with an English fallback; card text is mirrored into
`content/localization/cards_en.csv` (see `docs/LOCALIZATION_GUIDE.md`). Only English ships.

## Known limits (need a human or a device)
- **Screen readers**: Godot 4.7 exposes accessibility trees on desktop, but focus order and label
  names have not been checked with NVDA/VoiceOver/Orca. Card text and outcomes are plain Labels,
  so they are readable; decision tabs have text labels.
- **Colour-vision check**: palettes were chosen for luminance separation (see `docs/ART_BIBLE.md`)
  but no simulated-CVD pass has been done on the final procedural art.
- **Dyslexia-friendly font**: not offered. Adding one means shipping an OFL font and a toggle in
  `UITheme.build()`.
- **Haptics**: not implemented (no mobile build has been signed).
- **Real-device testing**: none. Layout was verified only through the headless screenshot harness
  at 1080×1920, 1080×2340, 540×960 and a desktop window.
- Text scale 1.6 with very long crisis situations (≥ 45 words) forces scrolling on phone height;
  this is intentional but has not been user-tested.
