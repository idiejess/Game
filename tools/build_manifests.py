#!/usr/bin/env python3
"""Generate assets/art_manifest.csv, assets/audio_manifest.csv and the prompt files under
assets/prompts/ from the content (characters, endings) and the asset tables in this script.

The manifests are the contract between code and art: final assets must use these filenames and
dimensions and can then be dropped in with no code changes. Status columns:
  placeholder_status   placeholder | procedural_candidate | sourced_candidate | external_candidate | final
  user_approval_status never set to approved by tooling; only a human edits this to `approved_by_user`
  integration_status   integrated | missing
Existing approval/notes columns are preserved when the manifest is regenerated.

Usage: python3 tools/build_manifests.py
"""
import csv
import hashlib
import json
import pathlib

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
PROMPTS = ASSETS / "prompts"

ART_FIELDS = ["asset_id", "asset_type", "character_id", "expression", "narrative_purpose", "final_filename", "destination_path",
              "width", "height", "aspect_ratio", "alpha_required", "safe_area", "generation_method", "generation_prompt_file",
              "negative_prompt_file", "reference_requirement", "source_url", "license", "sha256", "placeholder_status",
              "candidate_status", "user_approval_status", "integration_status", "notes"]
AUDIO_FIELDS = ["asset_id", "type", "filename", "destination", "narrative_purpose", "mood", "instrumentation_source", "duration_target_s",
                "loop_required", "loop_notes", "loudness_target", "format", "sample_rate", "channels", "production_method",
                "production_prompt_file", "source_url", "creator", "license", "attribution", "sha256", "placeholder_status",
                "candidate_status", "user_approval_status", "integration_status", "notes"]
PRESERVE = {"user_approval_status", "notes"}

STYLE = ("Flat inked bust portrait, uniform medium ink line slightly rough as if printed, two-tone cel shading, no gradients on "
         "the figure, single warm lamp from the lower left and cool ambient from water, chest-up framing at eye level with the "
         "head centre at 42% of the height, transparent background, 512x640, one faction accent colour only, no text.")
NEGATIVE = ("photorealistic, gradients on clothing, crowns, thrones, heraldry, medieval royalty, text, watermark, logo, extra fingers, "
            "extra limbs, deformed hands, blurry, cropped head, multiple people, modern clothing, resemblance to any existing game or "
            "franchise character, resemblance to a real person")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def load_existing(path, key):
    if not path.exists():
        return {}
    with path.open() as f:
        return {r[key]: r for r in csv.DictReader(f)}


def write_prompt(rel, text):
    p = PROMPTS / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text.strip() + "\n")
    return str(p.relative_to(ROOT))


def art_rows():
    rows = []
    chars = [json.loads(p.read_text()) for p in sorted((ROOT / "content" / "characters").glob("*.json"))]
    palette = "Palette: Pound Green #0F2E2B, Wet Slate #2B3A42, Lamp Amber #E0A33A, Company Chalk #EDE6D6, Ink #1A1714."
    write_prompt("UI/STYLE.md", "# Shared style prefix\n\n" + STYLE + "\n\n" + palette + "\n\n# Shared negative prompt\n\n" + NEGATIVE)
    for ch in chars:
        cid = ch["id"]
        is_source = ch["tier"] == "source"
        for expr in ch["expressions"]:
            fn = f"{ch['portrait_prefix']}_{expr}.png"
            if is_source:
                prompt = (f"Symbolic emblem for the '{ch['name']}' source card: {ch.get('role', '')}. Circular wet-slate medallion on "
                          f"transparent background, a single clear object silhouette in chalk and lamp amber, engraving-like line work. {STYLE}")
            else:
                prompt = (f"{ch['name']}, {ch.get('role', '')}. Silhouette: {ch.get('silhouette', '')} Faction accent: {ch.get('accent_color', '')} "
                          f"({ch.get('faction', '')}). Expression: {expr.replace('_', ' ')} — change only the face and hands; keep silhouette, "
                          f"clothing, age, skin tone and hair identical to the neutral reference. {STYLE}")
            pf = write_prompt(f"characters/{cid}_{expr}.txt", prompt + "\n\nNEGATIVE: " + NEGATIVE)
            path = ASSETS / "portraits" / fn
            rows.append(dict(asset_id=f"portrait_{cid}_{expr}", asset_type="portrait", character_id=cid, expression=expr,
                             narrative_purpose=f"Speaker portrait for {ch['name']} ({expr})", final_filename=fn, destination_path="assets/portraits/",
                             width=512, height=640, aspect_ratio="4:5", alpha_required="yes", safe_area="head centre at 42% height; nothing within 24px of edges",
                             generation_method="procedural (tools/build_art.py); target: hand-drawn or generated from neutral reference",
                             generation_prompt_file=pf, negative_prompt_file="assets/prompts/UI/STYLE.md", reference_requirement="neutral" if expr != "neutral" and not is_source else "none",
                             source_url="", license="original (repository)", sha256=sha(path), placeholder_status="procedural_candidate",
                             candidate_status="candidate", user_approval_status="pending", integration_status="integrated" if path.exists() else "missing", notes=""))
    icons = {"res_water": "Water: wave with level tick", "res_traffic": "Traffic: two opposed arrows", "res_coffers": "Coffers: strapped chest",
             "res_company": "Company: sealed charter scroll", "res_town": "Town: lamp on post", "fac_company": "Company gear-and-wave",
             "fac_town": "Town lamp (ringed)", "fac_hullfolk": "Hullfolk reed knot", "fac_aldmere": "Aldmere sheaf", "fac_sorrel": "Sorrel hammer",
             "fac_concordance": "Concordance still-water circle"}
    for name, desc in icons.items():
        for suffix, size in (("", 64), ("@2x", 128)):
            fn = f"{name}{suffix}.png"
            path = ASSETS / "icons" / fn
            pf = write_prompt(f"UI/{name}.txt", f"Monochrome {size}px icon, {desc}. Shape-distinct silhouette readable at 32px, uniform stroke, transparent background, no text. {palette}\n\nNEGATIVE: {NEGATIVE}")
            rows.append(dict(asset_id=f"icon_{name}{suffix.replace('@', '_')}", asset_type="icon", character_id="", expression="", narrative_purpose=desc,
                             final_filename=fn, destination_path="assets/icons/", width=size, height=size, aspect_ratio="1:1", alpha_required="yes", safe_area="14% margin",
                             generation_method="procedural (tools/build_art.py)", generation_prompt_file=pf, negative_prompt_file="assets/prompts/UI/STYLE.md",
                             reference_requirement="none", source_url="", license="original (repository)", sha256=sha(path), placeholder_status="procedural_candidate",
                             candidate_status="candidate", user_approval_status="pending", integration_status="integrated" if path.exists() else "missing", notes=""))
        if name.startswith("res_"):
            fn = f"{name}_danger.png"
            path = ASSETS / "icons" / fn
            rows.append(dict(asset_id=f"icon_{name}_danger", asset_type="icon", character_id="", expression="", narrative_purpose=desc + " — critical state, cracked outline",
                             final_filename=fn, destination_path="assets/icons/", width=64, height=64, aspect_ratio="1:1", alpha_required="yes", safe_area="14% margin",
                             generation_method="procedural (tools/build_art.py)", generation_prompt_file=f"assets/prompts/UI/{name}.txt", negative_prompt_file="assets/prompts/UI/STYLE.md",
                             reference_requirement="none", source_url="", license="original (repository)", sha256=sha(path), placeholder_status="procedural_candidate",
                             candidate_status="candidate", user_approval_status="pending", integration_status="integrated" if path.exists() else "missing", notes=""))
    for fn, size, purpose in (("app_icon.png", 512, "Application icon: gear-and-wave on Pound Green"), ("app_icon_192.png", 192, "Android launcher icon")):
        path = ASSETS / "icons" / fn
        rows.append(dict(asset_id=fn.replace(".png", ""), asset_type="app_icon", character_id="", expression="", narrative_purpose=purpose, final_filename=fn,
                         destination_path="assets/icons/", width=size, height=size, aspect_ratio="1:1", alpha_required="no", safe_area="10% margin",
                         generation_method="procedural (tools/build_art.py)", generation_prompt_file="assets/prompts/UI/app_icon.txt", negative_prompt_file="assets/prompts/UI/STYLE.md",
                         reference_requirement="none", source_url="", license="original (repository)", sha256=sha(path), placeholder_status="procedural_candidate",
                         candidate_status="candidate", user_approval_status="pending", integration_status="integrated" if path.exists() else "missing", notes=""))
    write_prompt("UI/app_icon.txt", f"App icon: brass gear with a chalk wave through it on Pound Green, rounded square, no text. {palette}\n\nNEGATIVE: {NEGATIVE}")
    ui = {"card_front": (640, 1100, "yes", "Card front: chalk paper, docket corner, ≤6% grain"), "card_back": (640, 1100, "yes", "Card back: wet slate with charter-green gear-and-wave"),
          "button_normal": (256, 96, "yes", "Docket button, normal"), "button_focus": (256, 96, "yes", "Docket button, amber focus ring"), "button_pressed": (256, 96, "yes", "Docket button, pressed"),
          "focus_ring": (128, 128, "yes", "Keyboard focus indicator"), "arrow_left": (96, 96, "yes", "Decision arrow left"), "arrow_right": (96, 96, "yes", "Decision arrow right"),
          "paper_tile": (256, 256, "no", "Tileable paper grain"), "gauge_frame": (512, 64, "yes", "Brass gauge frame"), "gauge_needle": (24, 64, "yes", "Gauge needle"),
          "warning": (96, 96, "yes", "Warning symbol"), "pattern_canal_map": (512, 512, "yes", "Canal-engineering diagram pattern tile")}
    for name, (w, h, alpha, purpose) in ui.items():
        path = ASSETS / "ui" / f"{name}.png"
        pf = write_prompt(f"UI/{name}.txt", f"{purpose}. Halfway Lock interface element; rounded rectangle with one square (docket) corner where applicable; no text. {palette}\n\nNEGATIVE: {NEGATIVE}")
        rows.append(dict(asset_id=f"ui_{name}", asset_type="ui", character_id="", expression="", narrative_purpose=purpose, final_filename=f"{name}.png", destination_path="assets/ui/",
                         width=w, height=h, aspect_ratio=f"{w}:{h}", alpha_required=alpha, safe_area="n/a", generation_method="procedural (tools/build_art.py)", generation_prompt_file=pf,
                         negative_prompt_file="assets/prompts/UI/STYLE.md", reference_requirement="none", source_url="", license="original (repository)", sha256=sha(path),
                         placeholder_status="procedural_candidate", candidate_status="candidate", user_approval_status="pending", integration_status="integrated" if path.exists() else "missing", notes=""))
    bgs = {"bg_pound_night": "Main background: the Summit Pound at night from the Keeper's window, lamp lower left, water line at card midline",
           "bg_title": "Title background: pound at dusk", "bg_flood": "Crisis: flood, water high with amber reflections", "bg_dry": "Crisis: drought, exposed sills and cracked mud",
           "bg_frost": "Crisis: frost, white ice line", "bg_fire": "Crisis: boatyard fire glow", "bg_riot": "Crisis: riot, lamps in the town", "bg_cut": "The Marrow Cut: black tunnel, one lamp",
           "bg_ending_true": "True endings: the river returned, green water", "bg_ending_fail": "Failure endings: dark, still"}
    for name, purpose in bgs.items():
        path = ASSETS / "backgrounds" / f"{name}.png"
        pf = write_prompt(f"backgrounds/{name}.txt", f"{purpose}. Painted canal engineering-era scene, lamplit brass and wet stone at altitude, soft gradients allowed for water and lamplight, "
                          f"portrait 1080x1920, quiet composition leaving the centre third free for a card, no people, no text. {palette}\n\nNEGATIVE: {NEGATIVE}")
        rows.append(dict(asset_id=name, asset_type="background", character_id="", expression="", narrative_purpose=purpose, final_filename=f"{name}.png", destination_path="assets/backgrounds/",
                         width=1080, height=1920, aspect_ratio="9:16", alpha_required="no", safe_area="centre third free of detail; 5% edge margin", generation_method="procedural (tools/build_art.py)",
                         generation_prompt_file=pf, negative_prompt_file="assets/prompts/UI/STYLE.md", reference_requirement="none", source_url="", license="original (repository)", sha256=sha(path),
                         placeholder_status="procedural_candidate", candidate_status="candidate", user_approval_status="pending", integration_status="integrated" if path.exists() else "missing", notes=""))
    endings = json.loads((ROOT / "content" / "endings" / "endings.json").read_text())["endings"]
    for e in endings:
        fn = f"ending_{e['id'].removeprefix('end_')}.png"
        path = ASSETS / "endings" / fn
        pf = write_prompt(f"endings/{e['id']}.txt", f"Ending illustration for '{e['title']}': {e['epilogue']} Painted scene, 1080x1080, no text, no faces of real people. {palette}\n\nNEGATIVE: {NEGATIVE}")
        rows.append(dict(asset_id=f"ending_{e['id']}", asset_type="ending_illustration", character_id="", expression="", narrative_purpose=f"Ending screen: {e['title']}", final_filename=fn,
                         destination_path="assets/endings/", width=1080, height=1080, aspect_ratio="1:1", alpha_required="no", safe_area="5% margin", generation_method="not produced (optional); falls back to background",
                         generation_prompt_file=pf, negative_prompt_file="assets/prompts/UI/STYLE.md", reference_requirement="none", source_url="", license="", sha256=sha(path),
                         placeholder_status="placeholder", candidate_status="not_started", user_approval_status="pending", integration_status="integrated" if path.exists() else "missing",
                         notes="optional; Screens.gd shows the ending's background when the illustration is absent"))
    branding = {"logo": (1024, 384, "yes", "Wordmark logo"), "capsule_1232x706": (1232, 706, "no", "Store capsule"), "key_art_1920x1080": (1920, 1080, "no", "Promotional key art"),
                "screenshot_safe_area_overlay": (1080, 1920, "yes", "Screenshot safe-area overlay (dev aid)")}
    for name, (w, h, alpha, purpose) in branding.items():
        path = ASSETS / "branding" / f"{name}.png"
        pf = write_prompt(f"UI/branding_{name}.txt", f"{purpose} for Halfway Lock. Original wordmark and imagery only; no third-party marks. {palette}\n\nNEGATIVE: {NEGATIVE}")
        rows.append(dict(asset_id=f"brand_{name}", asset_type="branding", character_id="", expression="", narrative_purpose=purpose, final_filename=f"{name}.png", destination_path="assets/branding/",
                         width=w, height=h, aspect_ratio=f"{w}:{h}", alpha_required=alpha, safe_area="10% margin", generation_method="procedural (tools/build_art.py)", generation_prompt_file=pf,
                         negative_prompt_file="assets/prompts/UI/STYLE.md", reference_requirement="none", source_url="", license="original (repository)", sha256=sha(path),
                         placeholder_status="procedural_candidate", candidate_status="candidate", user_approval_status="pending", integration_status="integrated" if path.exists() else "missing", notes=""))
    return rows


def audio_rows():
    A = ASSETS / "audio"
    table = [
        # id, type, purpose, mood, instrumentation, duration, loop, loudness
        ("mus_title", "music", "Title screen", "still, breathing", "harmonium drone D/A, drips, fiddle fragment of The River", 45, "yes", "-20 LUFS approx"),
        ("mus_ambient", "music", "Ordinary play", "quiet, mechanical", "harmonium, filtered water noise, gear clicks at 52 bpm", 92, "yes", "-20 LUFS approx"),
        ("mus_crisis", "music", "Crisis pool active / danger bands", "urgent, regular", "harmonium pulse 120 bpm, plucked bass, bell every 4 bars", 32, "yes", "-18 LUFS approx"),
        ("mus_ending_ordinary", "music", "Ordinary and false endings", "settled, ambiguous", "plucked D-F-A arpeggio, harmonium pad, bell", 20, "no", "-20 LUFS approx"),
        ("mus_ending_fail", "music", "Deaths and dismissals", "final", "tubular bell, decaying harmonium", 12, "no", "-22 LUFS approx"),
        ("mus_ending_true", "music", "True endings", "release", "The River motif (D Dorian) on solo fiddle, pad, bell", 40, "no", "-18 LUFS approx"),
        ("sfx_card_drag", "sfx", "Drag start", "paper", "band-passed noise, 3 variations (_v1.._v3)", 0.14, "no", "-22 dBFS RMS"),
        ("sfx_card_tilt", "sfx", "Passing the commit threshold", "click", "pitch-swept sine", 0.05, "no", "-16 dBFS RMS"),
        ("sfx_card_snap", "sfx", "Card returns to centre", "rubbery", "pitch sweep + noise", 0.16, "no", "-15 dBFS RMS"),
        ("sfx_card_commit", "sfx", "Decision committed", "wooden thud", "slap + gate thud + chain, 2 variations", 0.3, "no", "-14 dBFS RMS"),
        ("sfx_ui_nav", "sfx", "Menu navigation", "brass tick", "sine", 0.05, "no", "-19 dBFS RMS"),
        ("sfx_ui_confirm", "sfx", "Menu confirmation", "brass", "two sines", 0.16, "no", "-17 dBFS RMS"),
        ("sfx_save", "sfx", "Save confirmation", "brass", "two rising sines", 0.25, "no", "-19 dBFS RMS"),
        ("sfx_res_up", "sfx", "Resource increase", "bell up", "two-note bell", 0.28, "no", "-17 dBFS RMS"),
        ("sfx_res_down", "sfx", "Resource decrease", "bell down", "two-note bell", 0.28, "no", "-17 dBFS RMS"),
        ("sfx_res_danger", "sfx", "Resource enters danger band", "low pulse", "beating harmonium", 0.7, "no", "-12 dBFS RMS"),
        ("sfx_warning", "sfx", "General warning", "struck iron", "partials + reverb", 0.6, "no", "-17 dBFS RMS"),
        ("sfx_unlock", "sfx", "Ledger unlock", "three bells", "rising bell partials", 0.9, "no", "-18 dBFS RMS"),
        ("sfx_revelation", "sfx", "Revelation beat", "swell", "sines + shimmer noise", 1.6, "no", "-18 dBFS RMS"),
        ("sfx_death", "sfx", "Death / dismissal", "bell + drone", "bell partials + descending drone", 1.6, "no", "-17 dBFS RMS"),
        ("sfx_success", "sfx", "Success stinger", "plucked", "pluck + bell", 1.0, "no", "-17 dBFS RMS"),
        ("sfx_telegram", "sfx", "Telegram card", "clicks", "noise bursts in rhythm", 0.5, "no", "-28 dBFS RMS"),
        ("sfx_mech_click", "sfx", "Mechanical click / ratchet", "click", "noise burst", 0.04, "no", "-21 dBFS RMS"),
        ("sfx_gate_move", "sfx", "Lock-gate movement", "groan", "low sweep + rumble + creak", 1.4, "no", "-11 dBFS RMS"),
        ("sfx_chain", "sfx", "Chain tension", "metallic rattle", "sine bursts", 0.8, "no", "-19 dBFS RMS"),
        ("sfx_water_loop", "sfx", "Water movement (loop)", "water", "filtered noise, crossfaded loop", 2.75, "yes", "-23 dBFS RMS"),
        ("sfx_water_drift", "sfx", "Water drift tick", "water", "band-passed noise", 0.25, "no", "-25 dBFS RMS"),
        ("sfx_wood_impact", "sfx", "Wooden impact", "wood", "pitch sweep + noise", 0.22, "no", "-14 dBFS RMS"),
        ("sfx_metal_impact", "sfx", "Metal impact", "metal", "inharmonic partials", 0.7, "no", "-17 dBFS RMS"),
        ("sfx_bell", "sfx", "Summit bell", "bell", "tubular bell partials", 2.2, "no", "-16 dBFS RMS"),
    ]
    rows = []
    for aid, typ, purpose, mood, instr, dur, loop, loud in table:
        ext = ".ogg" if typ == "music" and (A / f"{aid}.ogg").exists() else ".wav"
        path = A / f"{aid}{ext}"
        pf = write_prompt(f"audio/{aid}.txt", f"{purpose}. Mood: {mood}. Instrumentation/source: {instr}. Duration ≈ {dur}s. Loop: {loop}. "
                          f"Original composition only; no copyrighted samples; no imitation of an identifiable work or living composer. See docs/AUDIO_BIBLE.md.")
        rows.append(dict(asset_id=aid, type=typ, filename=f"{aid}{ext}", destination="assets/audio/", narrative_purpose=purpose, mood=mood, instrumentation_source=instr,
                         duration_target_s=dur, loop_required=loop, loop_notes="crossfaded seam; validated in reports/assets/audio_validation.json" if loop == "yes" else "one-shot",
                         loudness_target=loud, format="OGG Vorbis q5" if ext == ".ogg" else "WAV PCM16", sample_rate=44100, channels=2 if typ == "music" else 1,
                         production_method="procedural synthesis (tools/build_audio.py, seed 9)", production_prompt_file=pf, source_url="", creator="repository (procedural)",
                         license="original (repository)", attribution="none required", sha256=sha(path), placeholder_status="procedural_candidate", candidate_status="candidate",
                         user_approval_status="pending", integration_status="integrated" if path.exists() else "missing", notes="requires human listening review"))
    return rows


def write_csv(path, fields, rows, key):
    existing = load_existing(path, key)
    for r in rows:
        old = existing.get(r[key])
        if old:
            for k in PRESERVE:
                if old.get(k):
                    r[k] = old[k]
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(path.relative_to(ROOT), len(rows), "rows")


def main():
    write_csv(ASSETS / "art_manifest.csv", ART_FIELDS, art_rows(), "asset_id")
    write_csv(ASSETS / "audio_manifest.csv", AUDIO_FIELDS, audio_rows(), "asset_id")


if __name__ == "__main__":
    main()
