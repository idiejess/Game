# Android playtest APK validation

Date: 2026-09-07

## Build

- Command: `godot --headless --path . --export-debug Android export/android/HalfwayLock-0.1.0-playtest.apk`
- Result: passed with Godot 4.7.2-stable.
- APK: `HalfwayLock-0.1.0-playtest.apk` (31 MiB local build).
- SHA-256: `d3e673d0b86251713d2f6c1546677ae856259da736373f808f51d7b85c1ebbc9`
- Package: `com.halfwaylock.playtest`, version code `1`, version name `0.1.0-playtest`.
- ABI: `arm64-v8a` only.
- Minimum SDK: API 24 (Android 7.0).
- Orientation: portrait (manifest declares `android.hardware.screen.portrait`).

## Package checks

- `aapt dump badging` completed successfully and reports the expected package, label, debug status,
  portrait feature, API 24 minimum SDK, and ARM64 native code.
- `apksigner verify --verbose --print-certs` passed with APK Signature Scheme v2 and v3. The signer is
  a local Android debug certificate; no signing material is in the repository.
- The package declares no custom permissions, including no `INTERNET` permission.

## Device smoke test

No Android emulator or attached ADB device is available in this sandbox. Godot's attempted ADB
connection could not reach an ADB daemon, so installation, launch/title screen, card rendering,
music/SFX, touch/swipe, save/reload, and developer-panel checks could not be performed on Android.
The existing Linux headless end-to-end playtest covers the title screen, a new run, card content,
save/load, and developer-tool gating; it is not a replacement for device validation.

The GitHub Actions workflow packages the APK and `SHA256SUMS.txt` together for device testers.
