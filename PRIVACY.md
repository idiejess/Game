# Privacy Policy — Halfway Lock

Last updated: 2026-09-06. Applies to every build produced from this repository (desktop, web, mobile).

## Summary
Halfway Lock collects no personal data, has no accounts, no analytics, no advertising, no
telemetry and no network features. Everything the game stores stays on your device.

## What the game stores locally
| Data | Where | Why | Remove it |
|---|---|---|---|
| Settings (text size, contrast, volumes, language, "content warning seen") | `user://settings.json` | Remember your preferences | Settings → Reset settings, or delete the file |
| Saves: the current run and the Keeper's Ledger (unlocked clues, endings seen, run count), one file per slot plus a `.bak` backup | `user://save_<slot>.json`, `user://save_<slot>.bak.json` | Resume play and carry discoveries between runs | Delete a slot from the load screen, or delete the files |

`user://` is Godot's per-user data directory: `%APPDATA%\Godot\app_userdata\Halfway Lock` on Windows,
`~/.local/share/godot/app_userdata/Halfway Lock` on Linux, `~/Library/Application Support/Godot/app_userdata/Halfway Lock`
on macOS, the app's private storage on Android/iOS, and the browser's IndexedDB for the web build.

None of this data identifies you. It contains only game state (resource values, card ids, flags, a
random seed) and your settings. It is never transmitted.

## Network
The game makes no network requests. The engine binary does not contact any server. The web build
is downloaded from wherever it is hosted and then runs entirely in your browser; the hosting site's
own privacy policy governs that download.

## Third parties
No third-party SDKs are included (no analytics, crash reporting, ads, or social login). The game is
built with the open-source Godot Engine; see `THIRD_PARTY_NOTICES.md` for its components. Storefronts
(itch.io, Steam, app stores) may collect data under their own policies when you download or launch
the game through them; that collection is outside this game's control.

## Children
The game is rated for ages 13 and up because of its themes (see the in-game content warning). It
collects no data from anyone, including children.

## Changes
Any future feature that transmits data (for example cloud saves or crash reports) would require an
update to this document and an in-game notice before the feature is enabled.

## Contact
Questions about this policy should go to the publisher contact listed on the store page.
