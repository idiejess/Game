#!/usr/bin/env python3
"""Generate clearly-labeled procedural placeholder art and audio with final filenames.

Portraits: 512x640 PNG, transparent background, faction accent, silhouette hint, label text.
Icons: 64x64 PNG. Backgrounds: 1080x1920 PNG. Audio: short synthesized WAV cues; music = silence.
Everything is regenerable and never marked approved in the manifests.
Requires only the Python standard library (zlib, struct, wave, math).
"""
import json
import math
import pathlib
import struct
import wave
import zlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"

# 5x7 bitmap font for labels (uppercase, digits, a few symbols)
FONT = {
    'A': ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    'B': ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    'C': ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
    'D': ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    'E': ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    'F': ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    'G': ["01111", "10000", "10000", "10111", "10001", "10001", "01111"],
    'H': ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    'I': ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    'J': ["11111", "00010", "00010", "00010", "00010", "10010", "01100"],
    'K': ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    'L': ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    'M': ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    'N': ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    'O': ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    'P': ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    'Q': ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    'R': ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    'S': ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    'T': ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    'U': ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    'V': ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    'W': ["10001", "10001", "10001", "10101", "10101", "10101", "01010"],
    'X': ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    'Y': ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    'Z': ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
    '_': ["00000", "00000", "00000", "00000", "00000", "00000", "11111"],
    '-': ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    ' ': ["00000"] * 7,
    '0': ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    '1': ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    '2': ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    '3': ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
    '4': ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    '5': ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    '6': ["00110", "01000", "10000", "11110", "10001", "10001", "01110"],
    '7': ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    '8': ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    '9': ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
}


def hex_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


class Canvas:
    def __init__(self, w, h, bg=(0, 0, 0, 0)):
        self.w, self.h = w, h
        self.px = bytearray(bg * (w * h))

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 4
            a = c[3] / 255.0 if len(c) == 4 else 1.0
            if a >= 1.0:
                self.px[i:i + 4] = bytes(list(c[:3]) + [255])
            else:
                for k in range(3):
                    self.px[i + k] = int(self.px[i + k] * (1 - a) + c[k] * a)
                self.px[i + 3] = max(self.px[i + 3], int(a * 255))

    def rect(self, x0, y0, x1, y1, c):
        for y in range(max(0, y0), min(self.h, y1)):
            for x in range(max(0, x0), min(self.w, x1)):
                self.set(x, y, c)

    def ellipse(self, cx, cy, rx, ry, c):
        for y in range(int(cy - ry), int(cy + ry) + 1):
            for x in range(int(cx - rx), int(cx + rx) + 1):
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
                    self.set(x, y, c)

    def text(self, x, y, s, c, scale=3):
        cx = x
        for ch in s.upper():
            glyph = FONT.get(ch, FONT[' '])
            for gy, row in enumerate(glyph):
                for gx, bit in enumerate(row):
                    if bit == '1':
                        self.rect(cx + gx * scale, y + gy * scale, cx + (gx + 1) * scale, y + (gy + 1) * scale, c)
            cx += 6 * scale

    def text_width(self, s, scale=3):
        return len(s) * 6 * scale

    def save(self, path):
        raw = b''.join(b'\x00' + bytes(self.px[y * self.w * 4:(y + 1) * self.w * 4]) for y in range(self.h))

        def chunk(tag, data):
            c = struct.pack('>I', len(data)) + tag + data
            return c + struct.pack('>I', zlib.crc32(tag + data) & 0xFFFFFFFF)

        png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', self.w, self.h, 8, 6, 0, 0, 0))
        png += chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b'')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(png)


INK = (26, 23, 20, 255)
CHALK = (237, 230, 214, 255)
LABEL = (200, 53, 46, 255)

SILHOUETTES = {
    # (head_rx, head_ry, shoulder_w, torso_h, hat_h, accessory)
    "vosk": (44, 56, 150, 260, 0, "case"), "pell": (52, 58, 240, 280, 0, "sash"), "quenn": (42, 50, 150, 230, 18, "folio"),
    "ilse": (48, 54, 200, 260, 0, "slate"), "mirren": (42, 52, 150, 250, 0, "windlass"), "bram": (56, 60, 280, 300, 0, "pipe"),
    "wren": (40, 50, 140, 240, 0, "rope"), "crane": (44, 54, 160, 270, 0, "book"), "vane": (44, 54, 170, 260, 0, "watch"),
    "solas": (46, 54, 190, 270, 8, "sabre"), "hale": (44, 54, 180, 280, 30, "lamp"), "fennick": (42, 56, 140, 270, 12, "slips"),
    "tamm": (46, 52, 200, 250, 0, ""), "stroud": (44, 52, 160, 250, 0, "bag"), "dace": (46, 52, 210, 250, 0, ""),
    "cole": (44, 52, 170, 260, 0, "keys"), "petronel": (40, 46, 130, 210, 20, "fiddle"), "hesse": (46, 54, 190, 260, 10, "notebook"),
    "tobin": (46, 52, 180, 230, 0, "tankard"), "kell": (44, 56, 170, 280, 0, "cane"),
    "src_gate": (0, 0, 0, 0, 0, "boat"), "src_telegram": (0, 0, 0, 0, 0, "slip"), "src_weather": (0, 0, 0, 0, 0, "wave"),
    "src_ledger": (0, 0, 0, 0, 0, "book"), "src_stranger": (44, 54, 170, 260, 0, ""),
}

EXPR_MOUTH = {  # dy for mouth curve ends (negative = smile)
    "neutral": 0, "beaming": -8, "grinning": -8, "rare_warmth": -4, "almost_smiling": -3, "amused": -5, "hopeful": -4,
    "pleasant": -4, "serene": -3, "eager": -6, "delighted_by_a_clause": -6, "singing": -6, "curious": -2, "courteous": -2,
    "wry": -3, "brisk": 0, "measuring": 0, "absorbed": 0, "patient": -1, "resolved": 0, "worried": 5, "tired": 3,
    "wounded": 5, "stern": 3, "angry": 6, "grieving": 6, "guarded": 2, "broken": 7, "mourning": 6, "caught": 4,
    "serious": 2, "disapproving": 4, "alarmed": 5, "furious": 7, "weary": 3, "hard": 3, "troubled": 4, "unveiled": 2,
    "sheepish": 3, "frightened": 6, "doubtful": 3, "grave": 4, "fed_up": 5, "cold": 3, "remembering": 1, "triumphant": -7,
    "final": 2,
}


def portrait(char, expr, out):
    w, h = 512, 640
    c = Canvas(w, h)
    accent = hex_rgb(char["accent_color"]) + (255,)
    sil = SILHOUETTES.get(char["id"], (44, 54, 170, 260, 0, ""))
    hrx, hry, shw, th, hat, acc = sil
    cx = w // 2
    if char["tier"] == "source":
        # Symbolic source cards
        c.ellipse(cx, 300, 170, 170, (43, 58, 66, 255))
        c.ellipse(cx, 300, 150, 150, (15, 46, 43, 255))
        if acc == "boat":
            c.rect(cx - 110, 300, cx + 110, 340, INK)
            c.rect(cx - 10, 180, cx + 10, 300, INK)
        elif acc == "slip":
            c.rect(cx - 120, 240, cx + 120, 360, CHALK)
            for i in range(4):
                c.rect(cx - 100, 262 + i * 24, cx + 60 + (i % 2) * 30, 268 + i * 24, INK)
        elif acc == "wave":
            for x in range(cx - 130, cx + 130):
                y = 300 + int(math.sin(x / 18.0) * 14)
                c.rect(x, y, x + 1, y + 8, (224, 163, 58, 255))
        elif acc == "book":
            c.rect(cx - 110, 230, cx + 110, 370, CHALK)
            c.rect(cx - 2, 230, cx + 2, 370, INK)
    else:
        neck_y = 260
        # torso
        c.ellipse(cx, neck_y + th // 2 + 60, shw // 2, th // 2, (43, 58, 66, 255))
        c.rect(cx - shw // 2, neck_y + th // 2 + 60, cx + shw // 2, h, (43, 58, 66, 255))
        # accent element
        if acc == "sash":
            for i in range(-shw // 2, shw // 2):
                y = neck_y + 100 + int(i * 0.6)
                c.rect(cx + i, y, cx + i + 1, y + 26, accent)
        elif acc in ("case", "book", "folio", "slate", "notebook"):
            c.rect(cx - 90, neck_y + 200, cx + 90, neck_y + 330, accent)
        elif acc == "lamp":
            c.ellipse(cx + 130, neck_y + 260, 26, 34, (224, 163, 58, 255))
        elif acc in ("windlass", "rope", "sabre", "cane", "fiddle", "pipe", "keys", "watch", "bag", "tankard", "slips"):
            c.rect(cx + 90, neck_y + 120, cx + 108, neck_y + 380, accent)
        else:
            c.rect(cx - shw // 2, neck_y + 80, cx - shw // 2 + 24, h, accent)
        # neck & head
        c.rect(cx - 22, neck_y - 20, cx + 22, neck_y + 40, (200, 170, 140, 255))
        c.ellipse(cx, 200, hrx * 1.6, hry * 1.6, (200, 170, 140, 255))
        if hat:
            c.rect(int(cx - hrx * 1.8), 200 - int(hry * 1.6) - hat, int(cx + hrx * 1.8), 200 - int(hry * 1.6) + 12, accent)
        # eyes
        c.ellipse(cx - 28, 190, 7, 9, INK)
        c.ellipse(cx + 28, 190, 7, 9, INK)
        # mouth
        dy = EXPR_MOUTH.get(expr, 0)
        for i in range(-26, 27):
            t = i / 26.0
            y = 240 + int(-dy * (1 - t * t))
            c.rect(cx + i, y, cx + i + 1, y + 4, INK)
    # labels
    c.rect(0, h - 70, w, h, (0, 0, 0, 200))
    lab = "PLACEHOLDER"
    c.text((w - c.text_width(lab, 3)) // 2, h - 62, lab, LABEL, 3)
    ident = f"{char['id']}_{expr}"[:26]
    c.text((w - c.text_width(ident, 2)) // 2, h - 32, ident, CHALK, 2)
    c.save(out)


def icon(name, color, out, shape):
    c = Canvas(64, 64)
    col = hex_rgb(color) + (255,)
    cx = cy = 32
    if shape == "wave":
        for x in range(6, 58):
            y = 34 + int(math.sin(x / 5.0) * 6)
            c.rect(x, y, x + 1, y + 5, col)
        c.rect(6, 14, 58, 17, col)
    elif shape == "arrows":
        c.rect(8, 20, 48, 26, col); c.rect(16, 38, 56, 44, col)
        for i in range(8):
            c.rect(48 + i, 23 - (8 - i), 49 + i, 23 + (8 - i), col)
            c.rect(16 - i, 41 - (8 - i), 17 - i, 41 + (8 - i), col)
    elif shape == "chest":
        c.rect(10, 22, 54, 52, col); c.rect(8, 16, 56, 24, col); c.rect(28, 30, 36, 40, INK)
    elif shape == "scroll":
        c.rect(14, 10, 50, 50, col); c.rect(20, 18, 44, 21, INK); c.rect(20, 26, 44, 29, INK); c.ellipse(32, 52, 8, 8, INK)
    elif shape == "lamp":
        c.rect(30, 10, 34, 56, col); c.ellipse(32, 18, 10, 10, (224, 163, 58, 255)); c.rect(18, 54, 46, 58, col)
    elif shape == "gear":
        c.ellipse(cx, cy, 20, 20, col); c.ellipse(cx, cy, 8, 8, (0, 0, 0, 0))
        for k in range(8):
            a = k * math.pi / 4
            c.ellipse(cx + math.cos(a) * 22, cy + math.sin(a) * 22, 5, 5, col)
    elif shape == "knot":
        c.ellipse(cx, cy, 20, 20, col); c.ellipse(cx, cy, 12, 12, (0, 0, 0, 0)); c.rect(28, 8, 36, 56, col)
    elif shape == "sheaf":
        for k in range(-2, 3):
            c.rect(cx + k * 6 - 2, 12 + abs(k) * 6, cx + k * 6 + 2, 52, col)
        c.rect(18, 40, 46, 46, col)
    elif shape == "hammer":
        c.rect(30, 20, 36, 56, col); c.rect(14, 10, 50, 24, col)
    elif shape == "circle":
        c.ellipse(cx, cy, 22, 22, col); c.ellipse(cx, cy, 16, 16, (0, 0, 0, 0)); c.rect(10, 31, 54, 34, col)
    elif shape == "app":
        c.rect(0, 0, 64, 64, (15, 46, 43, 255)); c.rect(6, 6, 58, 58, (43, 58, 66, 255))
        for x in range(8, 56):
            y = 36 + int(math.sin(x / 5.0) * 4)
            c.rect(x, y, x + 1, y + 6, (224, 163, 58, 255))
        c.rect(30, 10, 34, 34, (237, 230, 214, 255))
    c.save(out)


def background(name, out, water_frac, tint):
    w, h = 1080, 1920
    c = Canvas(w, h, (0, 0, 0, 255))
    top = hex_rgb("#081A18")
    for y in range(h):
        t = y / h
        col = tuple(int(top[k] * (1 - t) + tint[k] * t) for k in range(3)) + (255,)
        c.rect(0, y, w, y + 1, col)
    wy = int(h * (0.82 - 0.44 * water_frac))
    c.rect(0, wy, w, h, hex_rgb("#0F2E2B") + (255,))
    c.rect(0, wy, w, wy + 4, hex_rgb("#E0A33A") + (255,))
    c.rect(0, h - 90, w, h, (0, 0, 0, 200))
    lab = f"PLACEHOLDER {name}"[:30]
    c.text((w - c.text_width(lab, 4)) // 2, h - 70, lab, LABEL, 4)
    c.save(out)


def tone(path, seconds, freqs, kind="sine", volume=0.4, decay=True):
    sr = 22050
    n = int(sr * seconds)
    frames = bytearray()
    for i in range(n):
        t = i / sr
        env = (1.0 - t / seconds) if decay else 1.0
        v = 0.0
        if kind == "noise":
            import random
            random.seed(i)
            v = random.uniform(-1, 1)
        else:
            for k, f in enumerate(freqs):
                seg = seconds / max(1, len(freqs))
                if seg * k <= t < seg * (k + 1) or len(freqs) == 1:
                    v += math.sin(2 * math.pi * f * t)
        s = int(max(-1, min(1, v * volume * env)) * 32767)
        frames += struct.pack('<h', s)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), 'wb') as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr); wf.writeframes(bytes(frames))


def silence(path, seconds):
    tone(path, seconds, [1], volume=0.0, decay=False)


def main():
    chars = [json.loads(p.read_text()) for p in sorted((ROOT / "content" / "characters").glob("*.json"))]
    n = 0
    for ch in chars:
        for expr in ch["expressions"]:
            portrait(ch, expr, ASSETS / "portraits" / f"{ch['portrait_prefix']}_{expr}.png")
            n += 1
    print("portraits:", n)
    icons = {"res_water": ("#3B5F8A", "wave"), "res_traffic": ("#B4482B", "arrows"), "res_coffers": ("#E0A33A", "chest"),
             "res_company": ("#3F7D5A", "scroll"), "res_town": ("#9C5A3C", "lamp"),
             "fac_company": ("#3F7D5A", "gear"), "fac_town": ("#9C5A3C", "lamp"), "fac_hullfolk": ("#8C6B2F", "knot"),
             "fac_aldmere": ("#3B5F8A", "sheaf"), "fac_sorrel": ("#B4482B", "hammer"), "fac_concordance": ("#7C8FA6", "circle")}
    for name, (col, shape) in icons.items():
        icon(name, col, ASSETS / "icons" / f"{name}.png", shape)
    icon("app_icon", "#E0A33A", ASSETS / "icons" / "app_icon.png", "app")
    print("icons:", len(icons) + 1)
    bgs = {"bg_pound_night": (0.5, hex_rgb("#0F2E2B")), "bg_flood": (0.95, hex_rgb("#1A2E3A")), "bg_dry": (0.05, hex_rgb("#3A2E1A")),
           "bg_frost": (0.5, hex_rgb("#2E3A42")), "bg_fire": (0.5, hex_rgb("#4A2010")), "bg_riot": (0.5, hex_rgb("#3A1A1A")),
           "bg_cut": (0.3, hex_rgb("#050505")), "bg_ending_true": (0.6, hex_rgb("#1F3A2E")), "bg_ending_fail": (0.4, hex_rgb("#1A1A1A"))}
    for name, (frac, tint) in bgs.items():
        background(name, ASSETS / "backgrounds" / f"{name}.png", frac, tint)
    print("backgrounds:", len(bgs))
    a = ASSETS / "audio"
    tone(a / "sfx_card_drag.wav", 0.12, [1], kind="noise", volume=0.08)
    tone(a / "sfx_card_tilt.wav", 0.06, [880], volume=0.2)
    tone(a / "sfx_card_commit.wav", 0.3, [220, 110], volume=0.3)
    tone(a / "sfx_card_snap.wav", 0.15, [330], volume=0.15)
    tone(a / "sfx_res_up.wav", 0.25, [523, 659], volume=0.25)
    tone(a / "sfx_res_down.wav", 0.25, [659, 523], volume=0.25)
    tone(a / "sfx_warning.wav", 0.6, [196], volume=0.35)
    tone(a / "sfx_death.wav", 1.2, [98, 65], volume=0.4)
    tone(a / "sfx_unlock.wav", 0.8, [784, 1046, 1318], volume=0.25)
    tone(a / "sfx_telegram.wav", 0.4, [1200, 1200, 1200, 1200], volume=0.15)
    tone(a / "sfx_water_drift.wav", 0.2, [1500], volume=0.1)
    for m in ["mus_title", "mus_ambient", "mus_crisis", "mus_ending_fail", "mus_ending_true"]:
        silence(a / f"{m}.wav", 2.0)
    print("audio cues written (placeholders; music is silence)")


if __name__ == "__main__":
    main()
