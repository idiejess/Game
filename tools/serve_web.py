#!/usr/bin/env python3
"""Serve the Web export locally with the COOP/COEP headers Godot's web build needs.

Usage: python3 tools/serve_web.py [--export] [--port 3000] [--dir export/web]
  --export  run `godot --headless --export-release Web` first (requires templates installed)
"""
import argparse
import http.server
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write("%s\n" % (fmt % args))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--export", action="store_true")
    ap.add_argument("--port", type=int, default=3000)
    ap.add_argument("--dir", default="export/web")
    args = ap.parse_args()
    out = ROOT / args.dir
    if args.export or not (out / "index.html").exists():
        out.mkdir(parents=True, exist_ok=True)
        subprocess.run(["godot", "--headless", "--path", str(ROOT), "--export-release", "Web", str(out / "index.html")], check=True)
    handler = lambda *a, **k: Handler(*a, directory=str(out), **k)  # noqa: E731
    print(f"serving {out} on http://0.0.0.0:{args.port}")
    http.server.ThreadingHTTPServer(("0.0.0.0", args.port), handler).serve_forever()


if __name__ == "__main__":
    main()
