# Audio Production Guide — Halfway Lock

How to replace the procedural audio candidates with final recordings without touching code.
`docs/AUDIO_BIBLE.md` describes the musical language; this file is the workflow.

## Current state
- 30 cues are referenced by `AudioBus.gd` and listed in `assets/audio_manifest.csv`: 24 SFX (WAV,
  44.1 kHz, 16-bit, mono) and 6 music tracks (OGG Vorbis q5, stereo). Extra `_v1/_v2/_v3` variants
  of drag/commit exist for round-robin. All are **procedural candidates** synthesized by
  `tools/build_audio.py` (numpy; deterministic with `--seed 9`; music transcoded with ffmpeg).
- Technical validation passes: no clipping, no silent files, no duplicate binaries, loop seams
  measured (`reports/assets/audio_validation.json`). RMS sits around −18 to −22 dBFS for music and
  peaks ≤ 0.7 for SFX.
- No human has listened to them. `user_approval_status` is `pending` on every row.
- Nothing is sourced; the licence register is empty.

## Pipeline
```
tools/build_manifests.py   -> assets/audio_manifest.csv + assets/prompts/audio/<id>.txt (brief per cue)
tools/build_audio.py [--only <id>] [--seed N]   -> assets/audio/<id>.wav|.ogg
tools/validate_assets.py   -> technical checks, manifest <-> files <-> register
tools/build_credits.py     -> CREDITS.md / THIRD_PARTY_NOTICES.md
```
In-game: DevPanel → **Asset review** plays each cue and shows its manifest row; the Settings screen
has independent music/SFX sliders. Subtitles: every cue with narrative meaning has a caption
(`AudioBus._sub_keys` → `ui.audio.*` in `ui_en.csv`, checked by `test_accessibility_settings`).

## Specifications
| Column | Meaning |
|---|---|
| `duration_target_s` | Target length. SFX 0.1–1.5 s; music per the bible (title 45 s, ambient 92 s, crisis 32 s loops; endings 12–40 s one-shots). |
| `loop_required` | Music loops must be seamless: end on the same phase/chord as the start or bake a crossfade. Seam delta is measured by the validator. |
| `loudness_target` | Music ≈ −20 LUFS integrated (crisis −18); SFX peak ≤ −3 dBFS. Keep 6 dB headroom; the game mixes at runtime. |
| `format` / `sample_rate` / `channels` | Match exactly: WAV PCM16 44.1 kHz mono for SFX; OGG Vorbis q5 44.1 kHz stereo for music. |
| `production_prompt_file` | The brief: mood, instrumentation, motif references (The Pound, The River, The Charter), what it must not sound like. |

## Producing a final cue
1. Read the brief in `assets/prompts/audio/<id>.txt` and the motif rules in `docs/AUDIO_BIBLE.md`.
2. Record or compose. Original composition only; sample libraries must be royalty-free for
   commercial use with no attribution burden you are unwilling to carry in `CREDITS.md`.
3. Export to the exact filename and format in the manifest (`destination/filename`), overwriting the
   candidate. Godot re-imports on next open; the `.import` files do not need edits.
4. Set `placeholder_status` to `final`, `production_method` to what you did (DAW, instruments), and
   fill `creator`. Leave `user_approval_status` alone until someone has listened in-game.
5. Run `python3 tools/validate_assets.py` and `godot --headless --path . game/tests/TestRunner.tscn`
   (`test_audio_assets_exist`).

## Sourcing an existing recording
Same rules as art (`docs/ASSET_PRODUCTION_GUIDE.md`): CC0 first, otherwise public domain or an
explicit commercial licence; never NC/ND, "personal", "educational", or a recording of a
copyrighted composition. Add a fully populated row to `docs/ASSET_LICENSE_REGISTER.csv` (URLs,
licence URL, download date, SHA-256 of the original, evidence), set `placeholder_status = sourced_candidate`,
then run `tools/validate_assets.py` and `tools/build_credits.py`. Performances of traditional tunes
still need a licence for the *recording*.

## Adaptive behaviour to preserve
`Main` switches `mus_ambient` → `mus_crisis` whenever any resource is in a danger band and back when
it leaves (`AudioBus.play_music` restarts only when the track changes), and plays the ending's
`music` field from `content/endings/endings.json` on the ending screen (`tools/retarget_ending_music.py`
maintains those fields). The Water-driven low-pass described in the Audio Bible is **not implemented**;
it is listed in `docs/REMAINING_WORK.md`.
