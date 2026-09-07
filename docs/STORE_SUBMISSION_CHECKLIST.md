# Store Submission Checklist — Halfway Lock

Per-storefront steps. Everything here needs a human with store accounts; the repository provides
the inputs listed. Copy text from `docs/STORE_COPY.md`; never paste it from memory.

## Common inputs (in repo)
| Input | Location | Status |
|---|---|---|
| Title, tagline, short/long description, bullets, tags | `docs/STORE_COPY.md` | ready |
| Content descriptors / ratings answers | `docs/STORE_COPY.md` → Content descriptors | ready |
| Privacy policy URL text | `PRIVACY.md` (host it publicly and link) | ready, needs hosting |
| Credits / notices | `CREDITS.md`, `THIRD_PARTY_NOTICES.md` | generated |
| App icon 512 / 192 | `assets/icons/app_icon.png`, `app_icon_192.png` | procedural candidate — needs approval |
| Logo, key art, capsule | `assets/branding/` | procedural candidates — need approval |
| Screenshots | capture on device/desktop (see STORE_COPY.md list) | not done |
| Trailer | none | not done |
| Builds | `docs/BUILD_AND_EXPORT.md` | Linux/Windows/Web build; unsigned |

## itch.io
1. Create project; kind = HTML (web) and Downloadable (desktop). Classification: Game; genre Interactive Fiction.
2. Upload `export/web` zipped as the HTML build. Viewport 540×960 (portrait) or "fullscreen button" on; mobile-friendly on.
   Do **not** tick SharedArrayBuffer unless the preset is switched to the threaded template.
3. Upload Linux and Windows zips; mark platforms.
4. Paste short and long description; tags from STORE_COPY.md; set content rating to Teen.
5. Cover image 630×500 (crop from key art after approval); screenshots ≥ 3.
6. Pricing/visibility; publish as Restricted first for a playtest round.

## Steam (if pursued)
- Steamworks account and app fee; build uploaded via SteamPipe (depots for Windows, Linux).
- Store assets: header 460×215, capsule 231×87 / 616×353 / 1232×706 (candidate exists), hero 3840×1240, logo, library assets; all need final art.
- Steam Deck: portrait game in landscape shell — verify layout at 1280×800 (the game adapts, but not tested).
- Content survey: mature-content questionnaire answers from STORE_COPY.md; "some mature content: violence/gore? no; adult themes: death, alcohol references".
- Achievements/cloud: not implemented; do not tick.

## Google Play
- Build an AAB (`export_presets.cfg` Android preset; needs SDK, templates, release keystore; set `package/unique_name` to a real reverse-DNS id).
- Target API level per current Play policy; Godot 4.7 templates meet it at time of writing — recheck.
- Data safety form: "No data collected, no data shared" (PRIVACY.md). Ads: none. IARC questionnaire from content descriptors.
- Feature graphic 1024×500; phone screenshots (≥ 2) in portrait; icon 512.
- Internal testing track first.

## Apple App Store
- Requires Apple Developer account, iOS export preset (not created), Xcode signing.
- Privacy Nutrition Label: "Data Not Collected". Age rating 12+ (infrequent/mild mature themes).
- Screenshots per required device classes.

## Pre-submission gate (all stores)
- [ ] All `[H]` items in `docs/RELEASE_CHECKLIST.md` under Assets and Legal complete
- [ ] Version bumped; changelog written
- [ ] Builds signed where required and smoke-tested on the target OS
- [ ] Privacy policy hosted at a public URL
- [ ] Store page reviewed against `docs/STORE_COPY.md` "Do not" list
