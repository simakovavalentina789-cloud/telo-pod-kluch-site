#!/usr/bin/env python3
"""Visual/editorial integrity check for the 7-day illustrative food gallery.

This website is a presentation, NOT the client nutrition generator. Do not
require recipes, quantities, nutrition calculations, or culinary sign-off here.
"""
from collections import Counter
from pathlib import Path
import re
import sys

html = Path(__file__).resolve().parents[1].joinpath("index.html").read_text(encoding="utf-8")
match = re.search(r"const v45Days=\[(.*?)\];", html, re.S)
if not match:
    sys.exit("FAIL: v45Days not found")
rows = re.findall(r"\['([^'\n]+)','([^'\n]+)','([^'\n]+)'\]", match.group(1))
errors = []
if len(rows) != 28:
    errors.append(f"Expected 28 displayed meals, got {len(rows)}")
names = [name.strip() for name, _, _ in rows]
photos = [photo.strip() for _, _, photo in rows]
for label, items in (("dish names", names), ("photo keys", photos)):
    duplicates = [value for value, count in Counter(items).items() if count > 1]
    if duplicates:
        errors.append(f"Repeated {label}: {', '.join(duplicates)}")
if any(not name or not note.strip() or not photo for name, note, photo in rows):
    errors.append("Every display item needs a title, description and photo key")
if "salmon:'assets/hero-01-fish.webp'" not in html:
    errors.append("Founder-approved salmon photo was disconnected")
if "steak:'assets/hero-02-steak.webp'" not in html:
    errors.append("Founder-approved steak photo was disconnected")
if "const fullPhotoPaths=" not in html or "const fullPhotoSrc=fullPhotoPaths[photo]" not in html:
    errors.append("Full-resolution photo resolver missing")
print(f"DEMO VISUAL AUDIT: {len(rows)} cards, {len(set(names))} titles, {len(set(photos))} distinct photo keys")
if errors:
    for error in errors:
        print("FAIL:", error, file=sys.stderr)
    sys.exit(1)
print("PASS: display-name/photo-key integrity (not a manual visual or physical-iPad test)")
