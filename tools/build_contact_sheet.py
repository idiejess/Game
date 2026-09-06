#!/usr/bin/env python3
"""Tile PNGs into a labelled contact sheet.

Usage:
  python3 tools/build_contact_sheet.py --glob "reports/screenshots/phone/*.png" --out reports/screenshots/sheets/phone.png [--cols 7] [--width 270]
  python3 tools/build_contact_sheet.py --glob "assets/portraits/*.png" --out reports/assets/portraits_sheet.png --cols 10 --width 128
"""
import argparse
import glob
import pathlib

from PIL import Image, ImageDraw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cols", type=int, default=7)
    ap.add_argument("--width", type=int, default=270)
    args = ap.parse_args()
    files = sorted(glob.glob(args.glob))
    if not files:
        raise SystemExit("no files matched " + args.glob)
    tiles = []
    for f in files:
        im = Image.open(f).convert("RGBA")
        scale = args.width / im.width
        tile = im.resize((args.width, max(1, int(im.height * scale))))
        tiles.append((pathlib.Path(f).stem, tile))
    th = max(t.height for _, t in tiles) + 18
    cols = min(args.cols, len(tiles))
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * args.width, rows * th), (24, 24, 24))
    draw = ImageDraw.Draw(sheet)
    for i, (name, t) in enumerate(tiles):
        x, y = (i % cols) * args.width, (i // cols) * th
        bg = Image.new("RGBA", t.size, (60, 60, 60, 255))
        bg.alpha_composite(t)
        sheet.paste(bg.convert("RGB"), (x, y))
        draw.text((x + 4, y + t.height + 2), name[:34], fill=(230, 220, 200))
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print(out, sheet.size, len(tiles), "tiles")


if __name__ == "__main__":
    main()
