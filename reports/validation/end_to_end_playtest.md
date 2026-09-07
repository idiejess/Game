# End-to-End Playtest — Halfway Lock

Date: 2026-09-07 · Godot 4.7.2-stable headless · branch `hoplite/phleious-16c2ad27`
Machine-readable result: `reports/validation/end_to_end_playtest.json` (47 checks, 0 failures).

## Method
`game/tests/Playtest.tscn` drives the **real `Main` scene** (theme, HUD, CardView, Screens, AudioBus
subtitles) rather than the bare engine. Decisions go through `Main._request_decision()`, the same
entry point the swipe, the on-screen buttons and the A/D / arrow keys use, and the harness waits
for the card commit tween to finish before checking state. A simple "keeper" policy (nudge the
resource furthest from 50, favour Water) picks sides. Run with:
```
godot --headless --path . game/tests/Playtest.tscn        # options: -- --seed N --slot 3 --max-watches 400
```
It uses save slot 3 and deletes it afterwards; player settings are restored.

## Flow exercised and results
| Step | What happened | Result |
|---|---|---|
| First launch | Content warning shown; "Understood" persists `content_warnings_seen`; title follows | pass |
| New run | `onb_01` first; card visible; all five meters equal state | pass |
| Decide (preview → commit) | Watch advanced, history recorded | pass |
| Confirm-decisions setting | First press only previews and shows the hint; second press commits | pass |
| Screens mid-run | pause, settings, history, objectives, gallery, archive, ending history open and close back to play | pass |
| Live theme change | Text scale 1.6 + high contrast rebuild the theme immediately | pass |
| Save → title → continue | After 10 more watches: resources, watch, history and the *same card* (`mi13_2`) restored | pass |
| Play to an ending | `end_res_water_min` (The Dry Summit) at watch 63 after 52 further decisions; ending card then ending screen; card hidden; Ledger records the ending | pass |
| Second Keeper | Run 2 opens `onb_01` then `meta_new_keeper_2`; unlocks persist | pass |
| Ending history / credits | Screens render with a recorded ending | pass |
| Reload from disk | Run 2 resumes mid-run; Ledger ending history survives | pass |
| Audio captions | 14 subtitle emissions over the session (telegram, warning, death cue, music changes) | observed |
| Fallback cards | 0 drawn | pass |

## Observations (not failures)
- The scripted policy died to Water at watch 63, consistent with the balance report (median 50,
  Water the dominant edge). It never triggered an unlock notice in one run; unlocks are tied to arc
  progress that a 63-watch run under a resource-only policy rarely reaches.
- Godot reports 4 leaked ObjectDB instances at exit; these come from the harness quitting while
  `Main` still holds screen nodes, not from gameplay (the engine test runner exits clean).

## What this does not cover
- Real input devices (touch drag, gamepad), real screen sizes, audio audibility — see
  `docs/ACCESSIBILITY.md` "Known limits". The screenshot harness covers layout only.
- Web export interactivity (sandbox browser lacks WebGL 2); Linux export verified via `--smoke`.
- True-ending routes end to end; they are verified by construction (`tools/audit_arcs.py`), by
  `test_true_ending_trigger_from_card`, and by 17 true endings in the 10k simulation, but not by
  this UI-level run.
