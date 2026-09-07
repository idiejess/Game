# Remaining Work — Halfway Lock

Only genuine open items are listed here. Completed work is recorded in `PROJECT_STATE.md`;
release status per area is in `docs/RELEASE_CHECKLIST.md`.

## Requires a human
- **Visual approval** of every art candidate (125 files; `assets/art_manifest.csv`, DevPanel → Asset review).
  Then final production per `docs/ASSET_PRODUCTION_GUIDE.md`. Tooling never sets `approved_by_user`.
- **Listening approval** of the 30 audio candidates, then final production per `docs/AUDIO_PRODUCTION_GUIDE.md`.
- **Real-device testing** (phones, tablets, Steam Deck landscape), screen-reader pass, colour-vision simulation.
- **Signed builds**: Windows code signing; Android keystore + SDK; iOS/macOS presets and Apple credentials.
- **Legal review** of `PRIVACY.md`, `CREDITS.md`, `THIRD_PARTY_NOTICES.md`; host the privacy policy publicly.
- **Store assets**: real screenshots on devices, trailer, final key art (procedural candidates exist).
- Optional professional proofreading of the 1,000 cards (562 analyzer warnings are length guidelines, not errors).

## Engineering / design (agent-doable, not done)
- **MA08 (High Water) and MA12 (the final convergence) complete 0 times in 10k scripted runs.**
  Both are reachable by construction (arc audit) and MA12 is meant to be rare, but MA08 entry needs
  sustained Water ≥ 62 which scripted policies never hold (experiment `ma08gate52/56` showed the
  threshold is not the limiting factor; the policies simply do not raise Water). Needs either a
  smarter simulator strategy that plays for the arc, or a human playthrough to confirm.
- 67 cards unseen in 10k scripted runs (late arc beats, high-Town / low-Coffers resource cards).
  Reachable by construction; see `docs/BALANCE_REPORT.md`.
- Water-driven low-pass on ambient music (described in `docs/AUDIO_BIBLE.md`) is not implemented.
- Ending titles, arc titles and character names bypass `Loc` (`docs/LOCALIZATION_GUIDE.md`); no language picker.
- Optional ending illustrations (40) not produced; backgrounds used as fallback.
- Web export: verify interactive play in a WebGL 2 browser (blocked in the sandbox, not by the build).
- Windows preset `application/product_version` / `file_version` empty; bump version from 0.1.0 at release.
- Playtest harness leaks 4 ObjectDB instances at quit (harness teardown, cosmetic).
