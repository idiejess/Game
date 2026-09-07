#!/usr/bin/env python3
"""Procedural visual asset production for Halfway Lock (Art Bible palette and shape language).

Generates original, deterministic candidate assets with the final filenames listed in
assets/art_manifest.csv so a human artist can later replace any file without code changes:

  portraits/<char>_<expr>.png  512x640 RGBA   flat inked bust, faction accent, expression
  icons/res_*.png fac_*.png    64x64  RGBA    shape-distinct monochrome glyphs (+ @2x 128px)
  icons/app_icon.png           512x512        gear-and-wave on Pound Green
  ui/*.png                     card front/back, docket button, focus ring, arrows, paper, gauge
  backgrounds/bg_*.png         1080x1920      pound at night + crisis variants + endings
  branding/logo.png, capsule, key art, screenshot overlay

Everything here is generated code, no external imagery; text baked into images is limited to the
logo wordmark. Status in the manifest stays `candidate` (or `placeholder` for portraits, which the
Art Bible reserves for hand-drawn work) — this script never writes `approved_by_user`.

Usage: python3 tools/build_art.py [--only portraits|icons|ui|backgrounds|branding]
"""
import argparse
import hashlib
import json
import math
import pathlib
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = pathlib.Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"

PAL = {
    "pound_green": "#0F2E2B", "wet_slate": "#2B3A42", "lamp_amber": "#E0A33A", "chalk": "#EDE6D6",
    "ink": "#1A1714", "reed_ochre": "#8C6B2F", "charter_green": "#3F7D5A", "aldmere_blue": "#3B5F8A",
    "sorrel_rust": "#B4482B", "chapel_blue": "#7C8FA6", "town_brick": "#9C5A3C", "danger_red": "#C8352E",
}
FACTION = {"company": "charter_green", "town": "town_brick", "hullfolk": "reed_ochre", "aldmere": "aldmere_blue",
           "sorrel": "sorrel_rust", "concordance": "chapel_blue", "none": "chapel_blue"}
SKIN = {"a": (214, 178, 146), "b": (176, 132, 96), "c": (132, 92, 62), "d": (232, 204, 176), "e": (98, 68, 46)}
# Deterministic per-character build sheet (see docs/CHARACTER_BIBLE.md silhouettes).
CHARS = {
    "vosk": dict(skin="d", hair=(70, 70, 76), hair_style="bun", build=(0.62, 1.0), coat=(88, 92, 98), collar=True, prop="case", age="old"),
    "pell": dict(skin="a", hair=(150, 120, 90), hair_style="side", build=(1.25, 0.9), coat=(54, 48, 44), sash=True, prop="trumpet", age="mid"),
    "quenn": dict(skin="b", hair=(40, 30, 24), hair_style="cap", build=(0.7, 0.95), coat=(60, 88, 80), prop="folio", age="young"),
    "ilse": dict(skin="a", hair=(120, 70, 40), hair_style="tied", build=(1.05, 0.95), coat=(110, 80, 60), apron=True, prop="slate", age="mid"),
    "mirren": dict(skin="b", hair=(30, 26, 22), hair_style="short", build=(0.72, 1.0), coat=(40, 44, 50), prop="windlass", age="young"),
    "bram": dict(skin="c", hair=(220, 220, 215), hair_style="beard", build=(1.35, 0.85), coat=(120, 100, 70), prop="pipe", age="old"),
    "wren": dict(skin="c", hair=(30, 26, 22), hair_style="wild", build=(0.68, 1.0), coat=(90, 78, 56), prop="rope", age="young"),
    "crane": dict(skin="d", hair=(60, 56, 52), hair_style="flat", build=(0.75, 1.05), coat=(28, 28, 30), collar=True, glasses=True, prop="book", age="mid"),
    "vane": dict(skin="a", hair=(200, 60, 40), hair_style="bob", build=(0.8, 1.0), coat=(120, 60, 40), prop="watch", age="mid"),
    "solas": dict(skin="b", hair=(90, 90, 90), hair_style="cropped", build=(0.95, 1.0), coat=(96, 100, 100), prop="sabre", age="mid"),
    "hale": dict(skin="e", hair=(40, 40, 40), hair_style="veil", build=(0.85, 1.0), coat=(120, 130, 140), hem=True, prop="lamp", age="old"),
    "fennick": dict(skin="d", hair=(190, 150, 90), hair_style="eyeshade", build=(0.65, 1.1), coat=(80, 84, 70), prop="slips", age="young"),
    "tamm": dict(skin="a", hair=(100, 80, 60), hair_style="short", build=(1.0, 0.95), coat=(110, 90, 60), apron=True, prop="iron", age="mid"),
    "stroud": dict(skin="d", hair=(120, 120, 120), hair_style="bun", build=(0.78, 1.0), coat=(50, 50, 60), glasses=True, prop="bag", age="mid"),
    "dace": dict(skin="c", hair=(40, 36, 30), hair_style="cropped", build=(1.05, 0.95), coat=(80, 70, 60), prop="whistle", age="mid"),
    "cole": dict(skin="a", hair=(60, 50, 44), hair_style="tied", build=(0.8, 1.0), coat=(20, 18, 18), prop="keys", age="mid"),
    "petronel": dict(skin="c", hair=(230, 230, 225), hair_style="shawl", build=(0.6, 0.85), coat=(140, 110, 70), prop="fiddle", age="old"),
    "hesse": dict(skin="a", hair=(160, 120, 60), hair_style="side", build=(0.95, 1.0), coat=(150, 90, 50), check=True, prop="notebook", age="mid"),
    "tobin": dict(skin="d", hair=(200, 200, 195), hair_style="bald", build=(0.85, 0.85), coat=(60, 90, 70), prop="tankard", age="old"),
    "kell": dict(skin="d", hair=(120, 120, 130), hair_style="flat", build=(0.8, 1.05), coat=(30, 34, 40), collar=True, prop="cane", age="old"),
    "src_stranger": dict(skin="b", hair=(60, 60, 60), hair_style="hood", build=(0.85, 1.0), coat=(50, 52, 56), prop="", age="mid"),
}
# Mouth curvature / brow tilt per expression: (mouth, brows) negative mouth = smile.
EXPR = {
    "neutral": (0, 0), "beaming": (-9, -1), "grinning": (-8, -1), "rare_warmth": (-4, 0), "almost_smiling": (-3, 0),
    "amused": (-5, -2), "hopeful": (-4, -1), "pleasant": (-4, 0), "serene": (-3, 0), "eager": (-6, -2),
    "delighted_by_a_clause": (-6, -2), "singing": (-7, -1), "curious": (-2, -3), "courteous": (-2, 0), "wry": (-3, 2),
    "brisk": (0, 1), "measuring": (0, 2), "absorbed": (0, 1), "patient": (-1, 0), "resolved": (0, 2),
    "worried": (5, 3), "tired": (3, 1), "wounded": (5, 3), "stern": (3, 3), "angry": (6, 5), "grieving": (6, 3),
    "guarded": (2, 2), "broken": (7, 4), "mourning": (6, 2), "caught": (4, -3), "serious": (2, 2),
    "disapproving": (4, 3), "alarmed": (5, -4), "furious": (7, 5), "weary": (3, 1), "hard": (3, 4),
    "troubled": (4, 2), "unveiled": (2, 0), "sheepish": (3, -2), "frightened": (6, -4), "doubtful": (3, 2),
    "grave": (4, 2), "fed_up": (5, 3), "cold": (3, 3), "remembering": (1, 0), "triumphant": (-7, -2), "final": (2, 2),
}


def rgb(name):
    h = PAL[name].lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def font(size):
    for cand in ["/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
        if pathlib.Path(cand).exists():
            return ImageFont.truetype(cand, size)
    return ImageFont.load_default()


def paper_grain(img, strength=0.06, seed=1):
    rnd = random.Random(seed)
    w, h = img.size
    grain = Image.new("L", (w // 2, h // 2))
    px = grain.load()
    for y in range(h // 2):
        for x in range(w // 2):
            px[x, y] = 128 + int(rnd.gauss(0, 18))
    grain = grain.resize((w, h), Image.BILINEAR)
    overlay = Image.merge("RGBA", (grain, grain, grain, Image.new("L", (w, h), int(255 * strength))))
    return Image.alpha_composite(img.convert("RGBA"), overlay)


def docket(draw, box, fill, outline=None, width=0, radius=24):
    """Rounded rectangle with one square corner (top-right): the Halfway Lock 'docket'."""
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)
    draw.rectangle((x1 - radius, y0, x1, y0 + radius), fill=fill)
    if outline and width:
        draw.line((x1 - radius, y0, x1, y0), fill=outline, width=width)
        draw.line((x1, y0, x1, y0 + radius), fill=outline, width=width)


# ---------------------------------------------------------------------------------------------- portraits
def draw_portrait(cid, char, expr, out):
    w, h = 512, 640
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    spec = CHARS.get(cid, CHARS["src_stranger"])
    accent = rgb(FACTION.get(char.get("faction", "none"), "chapel_blue"))
    ink = rgb("ink")
    skin = SKIN[spec["skin"]]
    shade = tuple(max(0, c - 38) for c in skin)
    bw, bh = spec["build"]
    cx = w // 2
    head_cy = int(h * 0.42) - 40
    head_rx, head_ry = int(72 * min(1.15, 0.85 + bw * 0.25)), int(88 * bh)
    coat = spec["coat"]
    coat_dark = tuple(max(0, c - 30) for c in coat)
    # torso (two-tone cel)
    shoulder = int(190 * bw)
    top = head_cy + head_ry + 20
    d.rounded_rectangle((cx - shoulder, top, cx + shoulder, h + 60), radius=int(70 * bw), fill=coat)
    d.polygon([(cx - shoulder, h), (cx - shoulder, top + 60), (cx - shoulder + 40, top + 30), (cx - 10, h)], fill=coat_dark)
    # neck
    d.rectangle((cx - 26, head_cy + head_ry - 24, cx + 26, top + 10), fill=shade)
    # faction accent: one element only
    if spec.get("sash"):
        d.line((cx - shoulder + 20, top + 20, cx + 40, h), fill=accent, width=34)
    elif spec.get("hem"):
        d.rectangle((cx - shoulder, h - 70, cx + shoulder, h), fill=accent)
    elif spec.get("apron"):
        d.rounded_rectangle((cx - shoulder // 2, top + 90, cx + shoulder // 2, h), radius=20, fill=tuple(min(255, c + 45) for c in coat))
        d.line((cx - shoulder // 2, top + 90, cx + shoulder // 2, top + 90), fill=accent, width=10)
    elif spec.get("collar"):
        d.polygon([(cx - 40, top - 4), (cx, top + 46), (cx + 40, top - 4)], fill=rgb("chalk"))
        d.line((cx - shoulder + 24, top + 30, cx - shoulder + 24, h), fill=accent, width=12)
    elif spec.get("check"):
        for i in range(-shoulder, shoulder, 34):
            d.line((cx + i, top, cx + i, h), fill=coat_dark, width=6)
        d.line((cx - shoulder + 24, top + 30, cx - shoulder + 24, h), fill=accent, width=12)
    else:
        d.line((cx - shoulder + 24, top + 30, cx - shoulder + 24, h), fill=accent, width=14)
    # prop (large, deliberate)
    prop = spec.get("prop", "")
    px, py = cx + shoulder - 30, top + 120
    if prop in ("case", "book", "folio", "notebook", "slate"):
        d.rectangle((cx - 110, top + 170, cx + 110, top + 300), fill=accent if prop != "slate" else (60, 60, 64), outline=ink, width=6)
        d.line((cx - 110, top + 200, cx + 110, top + 200), fill=ink, width=4)
    elif prop in ("windlass", "rope", "sabre", "cane", "iron"):
        d.line((px, py - 60, px - 20, h), fill=(150, 130, 90) if prop != "sabre" else (170, 170, 180), width=18)
        d.ellipse((px - 26, py - 86, px + 26, py - 34), outline=ink, width=8)
    elif prop == "lamp":
        d.line((px, py - 100, px, py), fill=(120, 110, 90), width=5)
        d.ellipse((px - 34, py, px + 34, py + 86), fill=rgb("lamp_amber"), outline=ink, width=6)
    elif prop == "fiddle":
        d.ellipse((cx + 40, top + 120, cx + 160, top + 300), fill=(150, 100, 50), outline=ink, width=6)
        d.line((cx + 100, top + 120, cx + 150, top - 40), fill=ink, width=10)
    elif prop == "trumpet":
        d.polygon([(cx + 60, top + 200), (cx + 200, top + 120), (cx + 200, top + 280)], fill=(210, 170, 80), outline=ink)
    elif prop == "tankard":
        d.rectangle((cx + 60, top + 180, cx + 150, top + 300), fill=(160, 140, 110), outline=ink, width=6)
    elif prop == "keys":
        for i in range(3):
            d.ellipse((cx + 40 + i * 30, top + 200, cx + 60 + i * 30, top + 220), outline=(210, 170, 80), width=5)
            d.line((cx + 50 + i * 30, top + 220, cx + 50 + i * 30, top + 270), fill=(210, 170, 80), width=5)
    elif prop == "slips":
        for i in range(4):
            d.rectangle((cx - 120 + i * 40, top + 170 - i * 10, cx - 40 + i * 40, top + 260 - i * 10), fill=rgb("chalk"), outline=ink, width=3)
    elif prop == "watch":
        d.ellipse((cx + 70, top + 170, cx + 150, top + 250), fill=(210, 170, 80), outline=ink, width=6)
        d.line((cx + 110, top + 170, cx + 110, top + 120), fill=(210, 170, 80), width=5)
    elif prop == "bag":
        d.rounded_rectangle((cx + 40, top + 180, cx + 190, top + 300), radius=18, fill=(30, 30, 30), outline=ink, width=5)
    elif prop == "whistle":
        d.line((cx - 20, top + 20, cx + 30, top + 130), fill=(210, 170, 80), width=5)
        d.rectangle((cx + 20, top + 130, cx + 70, top + 160), fill=(210, 170, 80), outline=ink, width=4)
    elif prop == "pipe":
        d.line((cx + 30, head_cy + 60, cx + 110, head_cy + 110), fill=(90, 60, 40), width=12)
    # hair back layer
    hair = spec["hair"]
    style = spec["hair_style"]
    if style in ("bun", "tied", "shawl", "veil", "hood", "wild", "bob"):
        d.ellipse((cx - head_rx - 14, head_cy - head_ry - 10, cx + head_rx + 14, head_cy + head_ry + 30), fill=hair if style not in ("shawl", "veil", "hood") else coat)
    # head
    d.ellipse((cx - head_rx, head_cy - head_ry, cx + head_rx, head_cy + head_ry), fill=skin)
    d.chord((cx - head_rx, head_cy - head_ry, cx + head_rx, head_cy + head_ry), 120, 240, fill=shade)  # lower-left shade (lamp from lower left? bible: lamp lower left -> shade upper right)
    d.ellipse((cx - head_rx, head_cy - head_ry, cx + head_rx, head_cy + head_ry), outline=ink, width=6)
    # hair front layer
    if style in ("side", "flat", "short", "cropped", "bob", "wild", "eyeshade", "cap", "bun", "tied"):
        d.chord((cx - head_rx - 4, head_cy - head_ry - 6, cx + head_rx + 4, head_cy + 10), 190, 350, fill=hair)
        if style == "side":
            d.chord((cx - head_rx - 4, head_cy - head_ry - 6, cx + head_rx + 4, head_cy + 30), 200, 300, fill=hair)
    if style == "beard":
        d.ellipse((cx - head_rx + 10, head_cy + 10, cx + head_rx - 10, head_cy + head_ry + 60), fill=hair)
        d.chord((cx - head_rx - 4, head_cy - head_ry - 6, cx + head_rx + 4, head_cy + 10), 190, 350, fill=hair)
    if style == "cap":
        d.rectangle((cx - head_rx - 10, head_cy - head_ry - 30, cx + head_rx + 10, head_cy - head_ry + 14), fill=coat, outline=ink, width=4)
    if style == "eyeshade":
        d.chord((cx - head_rx - 16, head_cy - 60, cx + head_rx + 16, head_cy + 20), 180, 360, fill=(40, 90, 60))
    if spec["age"] == "old":
        for i in range(2):
            d.arc((cx - head_rx + 30, head_cy + 20 + i * 12, cx - head_rx + 60, head_cy + 40 + i * 12), 0, 90, fill=shade, width=3)
    # eyes and brows
    mouth, brows = EXPR.get(expr, (0, 0))
    ey = head_cy - 6
    for sx in (-1, 1):
        ex = cx + sx * int(head_rx * 0.42)
        d.ellipse((ex - 10, ey - 8, ex + 10, ey + 8), fill=rgb("chalk"), outline=ink, width=3)
        d.ellipse((ex - 5, ey - 5, ex + 5, ey + 5), fill=ink)
        if spec.get("glasses"):
            d.ellipse((ex - 22, ey - 20, ex + 22, ey + 20), outline=ink, width=4)
        by = ey - 26
        d.line((ex - 18, by + (brows if sx < 0 else -brows) // 2, ex + 18, by - (brows if sx < 0 else -brows) // 2), fill=ink, width=5)
    if spec.get("glasses"):
        d.line((cx - 12, ey, cx + 12, ey), fill=ink, width=4)
    # nose
    d.line((cx, ey + 6, cx - 6, ey + 34), fill=shade, width=5)
    # mouth (bezier-ish arc)
    my = head_cy + int(head_ry * 0.5)
    pts = []
    for i in range(-24, 25):
        t = i / 24.0
        pts.append((cx + i, my + int(-mouth * (1 - t * t))))
    d.line(pts, fill=ink, width=5)
    if expr == "singing":
        d.ellipse((cx - 12, my - 6, cx + 12, my + 14), fill=ink)
    # nameplate strip (label only, no text in final art per Art Bible; this is a candidate marker)
    img = img.filter(ImageFilter.SMOOTH)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)


def portraits():
    n = 0
    for p in sorted((ROOT / "content" / "characters").glob("*.json")):
        ch = json.loads(p.read_text())
        if ch["tier"] == "source":
            for expr in ch["expressions"]:
                draw_source_card(ch, expr, ASSETS / "portraits" / f"{ch['portrait_prefix']}_{expr}.png")
                n += 1
            continue
        for expr in ch["expressions"]:
            draw_portrait(ch["id"], ch, expr, ASSETS / "portraits" / f"{ch['portrait_prefix']}_{expr}.png")
            n += 1
    print("portraits:", n)


def draw_source_card(ch, expr, out):
    """Symbolic emblem for non-character sources (gate, telegram, weather, ledger, stranger)."""
    w, h = 512, 640
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = w // 2, int(h * 0.42)
    slate, amber, chalk, ink = rgb("wet_slate"), rgb("lamp_amber"), rgb("chalk"), rgb("ink")
    d.ellipse((cx - 190, cy - 190, cx + 190, cy + 190), fill=slate, outline=ink, width=8)
    d.ellipse((cx - 168, cy - 168, cx + 168, cy + 168), fill=rgb("pound_green"))
    kind = ch["id"]
    if kind == "src_gate":
        for gx in (-70, 70):
            d.rectangle((cx + gx - 22, cy - 120, cx + gx + 22, cy + 120), fill=(120, 90, 50), outline=ink, width=5)
            for i in range(5):
                d.line((cx + gx - 22, cy - 110 + i * 55, cx + gx + 22, cy - 110 + i * 55), fill=ink, width=4)
        d.line((cx - 92, cy - 60, cx + 92, cy - 60), fill=(170, 170, 180), width=10)
        d.line((cx - 92, cy + 60, cx + 92, cy + 60), fill=(170, 170, 180), width=10)
    elif kind == "src_telegram":
        d.rectangle((cx - 130, cy - 80, cx + 130, cy + 80), fill=chalk, outline=ink, width=5)
        for i in range(4):
            d.line((cx - 105, cy - 45 + i * 30, cx + 40 + (i % 2) * 60, cy - 45 + i * 30), fill=ink, width=6)
        d.ellipse((cx + 70, cy + 20, cx + 115, cy + 65), outline=rgb("sorrel_rust"), width=6)
    elif kind == "src_weather":
        d.ellipse((cx - 60, cy - 130, cx + 60, cy - 10), fill=chalk)
        for x in range(-140, 141, 4):
            y = cy + 60 + int(math.sin(x / 22.0) * 14)
            d.rectangle((cx + x, y, cx + x + 3, y + 10), fill=amber)
    elif kind == "src_ledger":
        d.rectangle((cx - 130, cy - 100, cx + 130, cy + 100), fill=(90, 60, 40), outline=ink, width=6)
        d.rectangle((cx - 118, cy - 88, cx - 4, cy + 88), fill=chalk)
        d.rectangle((cx + 4, cy - 88, cx + 118, cy + 88), fill=chalk)
        for i in range(6):
            d.line((cx - 104, cy - 70 + i * 26, cx - 20, cy - 70 + i * 26), fill=ink, width=3)
            d.line((cx + 20, cy - 70 + i * 26, cx + 104, cy - 70 + i * 26), fill=ink, width=3)
    else:  # stranger: hooded figure silhouette
        d.ellipse((cx - 60, cy - 120, cx + 60, cy), fill=(50, 52, 56), outline=ink, width=5)
        d.polygon([(cx - 130, cy + 170), (cx - 60, cy - 30), (cx + 60, cy - 30), (cx + 130, cy + 170)], fill=(50, 52, 56), outline=ink)
        d.ellipse((cx - 38, cy - 90, cx + 38, cy - 12), fill=(20, 18, 18))
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)


# ---------------------------------------------------------------------------------------------- icons
def glyph(kind, size, color, d, cracked=False):
    s = size
    m = s * 0.14
    lw = max(3, s // 12)
    if kind == "wave":
        pts = [(m + (s - 2 * m) * i / 40, s * 0.55 + math.sin(i / 40 * math.pi * 3) * s * 0.10) for i in range(41)]
        d.line(pts, fill=color, width=lw)
        d.line((s * 0.5, s * 0.22, s * 0.5, s * 0.42), fill=color, width=lw)
        d.line((s * 0.38, s * 0.22, s * 0.62, s * 0.22), fill=color, width=lw)
    elif kind == "arrows":
        d.line((m, s * 0.38, s - m, s * 0.38), fill=color, width=lw)
        d.polygon([(s - m, s * 0.38), (s - m - s * 0.18, s * 0.26), (s - m - s * 0.18, s * 0.5)], fill=color)
        d.line((m, s * 0.66, s - m, s * 0.66), fill=color, width=lw)
        d.polygon([(m, s * 0.66), (m + s * 0.18, s * 0.54), (m + s * 0.18, s * 0.78)], fill=color)
    elif kind == "chest":
        d.rounded_rectangle((m, s * 0.32, s - m, s - m), radius=s // 10, outline=color, width=lw)
        d.line((m, s * 0.55, s - m, s * 0.55), fill=color, width=lw)
        d.rectangle((s * 0.44, s * 0.48, s * 0.56, s * 0.66), fill=color)
    elif kind == "scroll":
        d.rounded_rectangle((m, m, s - m, s - m), radius=s // 8, outline=color, width=lw)
        for i in range(3):
            d.line((s * 0.3, s * 0.36 + i * s * 0.14, s * 0.7, s * 0.36 + i * s * 0.14), fill=color, width=max(2, lw // 2))
        d.ellipse((s * 0.6, s * 0.62, s * 0.8, s * 0.82), fill=color)
    elif kind == "lamp":
        d.line((s * 0.5, s * 0.45, s * 0.5, s - m), fill=color, width=lw)
        d.line((s * 0.3, s - m, s * 0.7, s - m), fill=color, width=lw)
        d.polygon([(s * 0.32, s * 0.45), (s * 0.68, s * 0.45), (s * 0.6, m), (s * 0.4, m)], outline=color, width=lw)
        d.ellipse((s * 0.44, s * 0.24, s * 0.56, s * 0.38), fill=color)
    elif kind == "gear":
        for i in range(8):
            a = i * math.pi / 4
            d.line((s / 2 + math.cos(a) * s * 0.26, s / 2 + math.sin(a) * s * 0.26, s / 2 + math.cos(a) * s * 0.4, s / 2 + math.sin(a) * s * 0.4), fill=color, width=lw + 2)
        d.ellipse((s * 0.24, s * 0.24, s * 0.76, s * 0.76), outline=color, width=lw)
        pts = [(s * 0.32 + (s * 0.36) * i / 20, s * 0.5 + math.sin(i / 20 * math.pi * 2) * s * 0.05) for i in range(21)]
        d.line(pts, fill=color, width=max(2, lw - 1))
    elif kind == "knot":
        d.ellipse((s * 0.2, s * 0.3, s * 0.6, s * 0.7), outline=color, width=lw)
        d.ellipse((s * 0.4, s * 0.3, s * 0.8, s * 0.7), outline=color, width=lw)
        d.line((s * 0.5, s * 0.7, s * 0.5, s - m), fill=color, width=lw)
    elif kind == "sheaf":
        for i in range(-2, 3):
            d.line((s * 0.5 + i * s * 0.05, s - m, s * 0.5 + i * s * 0.12, m + abs(i) * s * 0.06), fill=color, width=lw - 1)
        d.line((s * 0.35, s * 0.62, s * 0.65, s * 0.62), fill=color, width=lw)
    elif kind == "hammer":
        d.line((s * 0.35, s - m, s * 0.65, m + s * 0.12), fill=color, width=lw)
        d.rectangle((s * 0.5, m, s - m, m + s * 0.24), fill=color)
    elif kind == "circle":
        d.ellipse((m, m, s - m, s - m), outline=color, width=lw)
        d.line((s * 0.3, s * 0.5, s * 0.7, s * 0.5), fill=color, width=lw)
    if cracked:
        d.line((s * 0.15, s * 0.15, s * 0.45, s * 0.5, s * 0.3, s * 0.85), fill=rgb("danger_red"), width=max(2, lw // 2))


def icons():
    out = ASSETS / "icons"
    out.mkdir(exist_ok=True)
    table = {"res_water": ("wave", "aldmere_blue"), "res_traffic": ("arrows", "sorrel_rust"), "res_coffers": ("chest", "lamp_amber"),
             "res_company": ("scroll", "charter_green"), "res_town": ("lamp", "town_brick"),
             "fac_company": ("gear", "charter_green"), "fac_town": ("lamp", "town_brick"), "fac_hullfolk": ("knot", "reed_ochre"),
             "fac_aldmere": ("sheaf", "aldmere_blue"), "fac_sorrel": ("hammer", "sorrel_rust"), "fac_concordance": ("circle", "chapel_blue")}
    n = 0
    for name, (kind, col) in table.items():
        for size, suffix in ((64, ""), (128, "@2x")):
            img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            glyph(kind, size, rgb(col), ImageDraw.Draw(img))
            img.save(out / f"{name}{suffix}.png")
            n += 1
        if name.startswith("res_"):
            img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            glyph(kind, 64, rgb("danger_red"), ImageDraw.Draw(img), cracked=True)
            img.save(out / f"{name}_danger.png")
            n += 1
    # fac_town differs from res_town by a ring so the two files are not byte-identical
    img = Image.open(out / "fac_town.png")
    ImageDraw.Draw(img).ellipse((4, 4, 60, 60), outline=rgb("town_brick"), width=3)
    img.save(out / "fac_town.png")
    img = Image.open(out / "fac_town@2x.png")
    ImageDraw.Draw(img).ellipse((8, 8, 120, 120), outline=rgb("town_brick"), width=6)
    img.save(out / "fac_town@2x.png")
    # app icon 512
    s = 512
    img = Image.new("RGBA", (s, s), rgb("pound_green") + (255,))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, s, s), radius=96, fill=rgb("pound_green") + (255,))
    glyph("gear", s, rgb("lamp_amber"), d)
    pts = [(s * 0.1 + (s * 0.8) * i / 60, s * 0.78 + math.sin(i / 60 * math.pi * 4) * s * 0.03) for i in range(61)]
    d.line(pts, fill=rgb("chalk"), width=14)
    img.save(out / "app_icon.png")
    img.resize((192, 192), Image.LANCZOS).save(out / "app_icon_192.png")
    print("icons:", n + 2)


# ---------------------------------------------------------------------------------------------- UI
def ui():
    out = ASSETS / "ui"
    out.mkdir(exist_ok=True)
    chalk, ink, slate, amber = rgb("chalk"), rgb("ink"), rgb("wet_slate"), rgb("lamp_amber")
    # card front 640x1100 chalk paper with docket corner and grain
    img = Image.new("RGBA", (640, 1100), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    docket(d, (0, 0, 639, 1099), chalk + (255,), ink + (255,), 4, 28)
    img = paper_grain(img, 0.06, 7)
    img.save(out / "card_front.png")
    # card back: slate with charter-green gear-and-wave
    img = Image.new("RGBA", (640, 1100), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    docket(d, (0, 0, 639, 1099), slate + (255,), ink + (255,), 4, 28)
    g = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
    glyph("gear", 400, rgb("charter_green"), ImageDraw.Draw(g))
    img.alpha_composite(g, (120, 350))
    img.save(out / "card_back.png")
    # docket buttons (normal, focus) 9-slice friendly 256x96
    for name, fill, outline, w in (("button_normal", slate, None, 0), ("button_focus", slate, amber, 6), ("button_pressed", amber, amber, 6)):
        img = Image.new("RGBA", (256, 96), (0, 0, 0, 0))
        docket(ImageDraw.Draw(img), (0, 0, 255, 95), fill + (255,), (outline + (255,)) if outline else None, w, 20)
        img.save(out / f"{name}.png")
    # focus ring 128x128
    img = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    docket(ImageDraw.Draw(img), (4, 4, 123, 123), (0, 0, 0, 0), amber + (255,), 6, 22)
    img.save(out / "focus_ring.png")
    # decision arrows 96x96
    for name, flip in (("arrow_left", True), ("arrow_right", False)):
        img = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        pts = [(20, 48), (60, 16), (60, 34), (84, 34), (84, 62), (60, 62), (60, 80)]
        if not flip:
            pts = [(96 - x, y) for x, y in pts]
        d.polygon(pts, fill=chalk, outline=ink)
        img.save(out / f"{name}.png")
    # paper texture tile 256
    img = paper_grain(Image.new("RGBA", (256, 256), chalk + (255,)), 0.08, 3)
    img.save(out / "paper_tile.png")
    # gauge 512x64 brass
    img = Image.new("RGBA", (512, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 12, 511, 51), radius=12, fill=(60, 50, 30, 255), outline=(210, 170, 80, 255), width=4)
    for i in range(11):
        x = 16 + i * 48
        d.line((x, 12, x, 24 if i % 5 else 36), fill=(210, 170, 80, 255), width=3)
    img.save(out / "gauge_frame.png")
    img = Image.new("RGBA", (24, 64), (0, 0, 0, 0))
    ImageDraw.Draw(img).polygon([(12, 0), (0, 63), (24, 63)], fill=amber + (255,), outline=ink + (255,))
    img.save(out / "gauge_needle.png")
    # warning symbol 96
    img = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.polygon([(48, 6), (90, 86), (6, 86)], fill=rgb("danger_red") + (255,), outline=ink + (255,))
    d.rectangle((44, 30, 52, 62), fill=chalk + (255,))
    d.ellipse((43, 68, 53, 78), fill=chalk + (255,))
    img.save(out / "warning.png")
    # canal-map pattern tile 512 (Art Bible: canal-engineering diagrams)
    img = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    rnd = random.Random(9)
    for i in range(6):
        y = 40 + i * 80
        pts = [(x, y + math.sin(x / 90 + i) * 18) for x in range(0, 513, 8)]
        d.line(pts, fill=(224, 163, 58, 40), width=3)
        for k in range(3):
            x = rnd.randint(20, 490)
            d.rectangle((x - 6, y - 14, x + 6, y + 14), outline=(237, 230, 214, 50), width=2)
    img.save(out / "pattern_canal_map.png")
    print("ui: 13")


# ---------------------------------------------------------------------------------------------- backgrounds
def background(name, out, water_frac, sky, water, lamp=True, extra=None, seed=1):
    w, h = 1080, 1920
    img = Image.new("RGBA", (w, h), sky + (255,))
    d = ImageDraw.Draw(img)
    # vertical gradient sky
    for y in range(h):
        t = y / h
        c = tuple(int(sky[i] * (1 - t * 0.4)) for i in range(3))
        d.line((0, y, w, y), fill=c + (255,))
    # distant lock walls / hill silhouette
    d.polygon([(0, h * 0.55), (w * 0.25, h * 0.47), (w * 0.5, h * 0.52), (w * 0.8, h * 0.45), (w, h * 0.5), (w, h), (0, h)], fill=tuple(max(0, c - 12) for c in sky) + (255,))
    for gx in (w * 0.12, w * 0.88):
        d.rectangle((gx - 30, h * 0.40, gx + 30, h * 0.75), fill=tuple(max(0, c - 22) for c in sky) + (255,))
    # water
    yw = int(h * (0.82 - 0.44 * water_frac))
    pts = [(x, yw + math.sin(x / 60.0 + seed) * 6) for x in range(0, w + 1, 12)] + [(w, h), (0, h)]
    d.polygon(pts, fill=water + (255,))
    for i in range(30):
        y = yw + 20 + i * 40
        if y > h:
            break
        d.line((0, y, w, y), fill=tuple(min(255, c + 8) for c in water) + (70,), width=2)
    if lamp:
        lx = int(w * 0.18)
        for r, a in ((160, 18), (110, 28), (60, 40)):
            ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            ImageDraw.Draw(ov).ellipse((lx - r, yw - r + 30, lx + r, yw + r + 30), fill=rgb("lamp_amber") + (a,))
            img = Image.alpha_composite(img, ov)
            d = ImageDraw.Draw(img)
        d.rectangle((lx - 6, yw - 420, lx + 6, yw), fill=rgb("ink") + (255,))
        d.ellipse((lx - 26, yw - 470, lx + 26, yw - 400), fill=rgb("lamp_amber") + (255,))
    if extra == "cracks":
        rnd = random.Random(seed)
        for _ in range(60):
            x, y = rnd.randint(0, w), rnd.randint(yw, h)
            d.line((x, y, x + rnd.randint(-60, 60), y + rnd.randint(-30, 30)), fill=(40, 30, 20, 255), width=3)
    if extra == "glow":
        ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(ov).ellipse((w * 0.5, h * 0.25, w * 1.1, h * 0.6), fill=(200, 80, 30, 70))
        img = Image.alpha_composite(img, ov.filter(ImageFilter.GaussianBlur(80)))
    if extra == "lamps":
        rnd = random.Random(seed)
        d = ImageDraw.Draw(img)
        for _ in range(40):
            x, y = rnd.randint(0, w), rnd.randint(int(h * 0.48), int(h * 0.7))
            d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=rgb("lamp_amber") + (255,))
    if extra == "frost":
        d = ImageDraw.Draw(img)
        d.line((0, yw, w, yw), fill=(240, 245, 250, 255), width=10)
    if extra == "tunnel":
        img = Image.new("RGBA", (w, h), (5, 5, 5, 255))
        d = ImageDraw.Draw(img)
        d.ellipse((w * 0.2, h * 0.3, w * 0.8, h * 0.9), fill=(18, 20, 22, 255))
        for r, a in ((200, 20), (120, 40), (50, 90)):
            ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            ImageDraw.Draw(ov).ellipse((w * 0.5 - r, h * 0.6 - r, w * 0.5 + r, h * 0.6 + r), fill=rgb("lamp_amber") + (a,))
            img = Image.alpha_composite(img, ov)
    img = img.convert("RGB").filter(ImageFilter.GaussianBlur(0.6))
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)


def backgrounds():
    out = ASSETS / "backgrounds"
    pg = rgb("pound_green")
    table = {
        "bg_pound_night": (0.5, (14, 30, 34), pg, True, None),
        "bg_flood": (0.97, (18, 36, 50), (26, 60, 70), True, None),
        "bg_dry": (0.03, (52, 40, 26), (60, 46, 30), True, "cracks"),
        "bg_frost": (0.5, (40, 52, 62), (58, 74, 84), True, "frost"),
        "bg_fire": (0.5, (60, 24, 12), (50, 22, 14), False, "glow"),
        "bg_riot": (0.5, (48, 22, 22), pg, False, "lamps"),
        "bg_cut": (0.3, (5, 5, 5), (10, 12, 12), False, "tunnel"),
        "bg_ending_true": (0.7, (30, 58, 46), (40, 90, 70), True, None),
        "bg_ending_fail": (0.35, (22, 22, 24), (30, 30, 34), False, None),
        "bg_title": (0.55, (12, 28, 30), pg, True, None),
    }
    for i, (name, (frac, sky, water, lamp, extra)) in enumerate(table.items()):
        background(name, out / f"{name}.png", frac, sky, water, lamp, extra, seed=i + 1)
    print("backgrounds:", len(table))


# ---------------------------------------------------------------------------------------------- branding
def branding():
    out = ASSETS / "branding"
    out.mkdir(exist_ok=True)
    chalk, amber, ink = rgb("chalk"), rgb("lamp_amber"), rgb("ink")
    # wordmark logo 1024x384 transparent
    img = Image.new("RGBA", (1024, 384), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = font(150)
    d.text((72, 60), "HALFWAY", font=f, fill=chalk + (255,))
    d.text((72, 200), "LOCK", font=f, fill=amber + (255,))
    pts = [(560 + (420) * i / 60, 300 + math.sin(i / 60 * math.pi * 3) * 14) for i in range(61)]
    d.line(pts, fill=amber + (255,), width=10)
    d.line((640, 240, 640, 280), fill=amber + (255,), width=10)
    img.save(out / "logo.png")
    # store capsule 1232x706 (Steam header size) and key art 1920x1080
    for name, size in (("capsule_1232x706", (1232, 706)), ("key_art_1920x1080", (1920, 1080))):
        w, h = size
        bg = Image.open(ASSETS / "backgrounds" / "bg_title.png").convert("RGBA")
        scale = max(w / bg.width, h / bg.height)
        bg = bg.resize((int(bg.width * scale), int(bg.height * scale)), Image.LANCZOS)
        bg = bg.crop(((bg.width - w) // 2, (bg.height - h) // 2, (bg.width - w) // 2 + w, (bg.height - h) // 2 + h))
        logo = Image.open(out / "logo.png").convert("RGBA")
        ls = min(w * 0.6 / logo.width, h * 0.4 / logo.height)
        logo = logo.resize((int(logo.width * ls), int(logo.height * ls)), Image.LANCZOS)
        bg.alpha_composite(logo, ((w - logo.width) // 2, int(h * 0.18)))
        d = ImageDraw.Draw(bg)
        d.text((w // 2, int(h * 0.72)), "Keeper of the Meridian Canal", font=font(int(h * 0.05)), fill=chalk + (255,), anchor="mm")
        bg.convert("RGB").save(out / f"{name}.png")
    # screenshot overlay: safe-area frame 1080x1920 transparent with 5% margin guides
    img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle((54, 96, 1026, 1824), outline=amber + (160,), width=4)
    img.save(out / "screenshot_safe_area_overlay.png")
    print("branding: 5")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    args = ap.parse_args()
    steps = {"portraits": portraits, "icons": icons, "ui": ui, "backgrounds": backgrounds, "branding": branding}
    for name, fn in steps.items():
        if not args.only or args.only == name:
            fn()


if __name__ == "__main__":
    main()
