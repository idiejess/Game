# Release Checklist — Halfway Lock

Status legend: **[x]** verified automatically in this repository · **[H]** requires a human ·
**[ ]** not done. Last audited 2026-09-06 on branch `hoplite/phleious-16c2ad27`.

## Content
- [x] Exactly 1,000 cards; allocation per category matches `CARD_INVENTORY.json` (`tools/validate_content.py`, 0 errors, 0 warnings)
- [x] Every flag/counter in registries; every ending has a trigger and a card; 40 endings reachable by construction
- [x] Arc audit: 42 arcs, 3 true routes, 0 problems (`reports/content/arc_audit.json`)
- [x] Dialogue analyzer: 0 errors; 562 warnings remain (long crisis/arc situations; UI scrolls) — see `docs/CONTENT_REPORT.md`
- [H] Proofread the 1,000 cards (typos, voice consistency) — optional but recommended
- [x] Content warning text reviewed against `docs/CREATIVE_BIBLE.md` §18

## Engine
- [x] Engine tests: 250 checks, 0 failures, run twice from clean import
- [x] Save/load: full state + RNG continuation, migration v1→v2, corrupt-file recovery, future-version rejection
- [x] Engine/simulator parity pinned (`test_engine_matches_python_simulator`)
- [x] 10,000-run simulation: 0 stalls, 1 fallback run, median 50 watches; see `docs/BALANCE_REPORT.md`
- [ ] MA08 and MA12 completed 0 times by scripted strategies (reachable by construction; needs a human playthrough or a smarter policy) — tracked in `docs/REMAINING_WORK.md`
- [x] `--smoke` passes on the Linux export

## UI / accessibility
- [x] Text scale, high contrast, reduced motion, shake toggle, decision buttons, confirm, exact effects, subtitles (`docs/ACCESSIBILITY.md`)
- [x] Keyboard play end-to-end; focus on every screen
- [x] Layout at 1080×1920, 1080×2340, 540×960, desktop (`reports/screenshots/`)
- [H] Real-device pass (phone, tablet), screen-reader pass, colour-vision simulation
- [x] Dev panel gated (`dev_tools_enabled()`), F12

## Assets
- [x] Every referenced file exists; manifests validate (`tools/validate_assets.py`, 0 problems)
- [x] All art/audio original (procedural); no external asset sourced; licence register empty by design
- [H] Visual approval of 125 art candidates (`assets/art_manifest.csv`, DevPanel → Asset review)
- [H] Listening approval of 30 audio candidates
- [H] Replace candidates with final production (`docs/ASSET_PRODUCTION_GUIDE.md`, `docs/AUDIO_PRODUCTION_GUIDE.md`)
- [ ] Optional ending illustrations (40) — fallback backgrounds in use

## Legal / documentation
- [x] `CREDITS.md`, `THIRD_PARTY_NOTICES.md` generated from register + engine copyright info (`tools/build_credits.py`)
- [x] `PRIVACY.md` (no data collection); in-game credits state the same
- [H] Legal review of PRIVACY.md and notices before publication
- [x] `README.md`, `docs/BUILD_AND_EXPORT.md`, `docs/LOCALIZATION_GUIDE.md`, `docs/STORE_COPY.md`, `docs/STORE_SUBMISSION_CHECKLIST.md`
- [x] Decision log current (`docs/DECISION_LOG.md`)

## Builds
- [x] Linux x86_64 release export built and smoke-tested
- [x] Windows x86_64 release export built (unsigned, not executed)
- [x] Web export built; loads to title (interactive verification blocked in sandbox: no WebGL 2)
- [ ] Android: preset only; needs SDK + keystore
- [ ] iOS/macOS: no preset; needs Apple credentials
- [H] Code signing (Windows, macOS), notarisation
- [ ] Version bump from 0.1.0 and `application/product_version` in Windows preset

## Repository hygiene
- [x] No secrets, no absolute paths in tracked files (`rg` check in final verification)
- [x] `export/`, `.godot/`, `reports/screenshots/` ignored; `export/.gdignore` present
- [x] Working branch + draft PR; `main` untouched (no `main` existed on the remote — D-008)

## Go / no-go
Automated gates are green. The build is **not** releasable to the public until the [H] items are
done: asset approval/production, device testing, legal review and signing. It is releasable today
as an internal playtest build (Linux/Windows/Web) with procedural art and audio.
