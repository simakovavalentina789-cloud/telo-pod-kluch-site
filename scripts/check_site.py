#!/usr/bin/env python3
"""Build-time integrity checks for the Telo Pod Klyuch static website."""
from html.parser import HTMLParser
from pathlib import Path
import re
import sys

BASE = Path(__file__).resolve().parents[1]
HTML = BASE / "index.html"
ASSETS = BASE / "assets"


class SiteParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.anchors = []
        self.assets = []
        self.forms = 0
        self.images = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids.append(attrs["id"])
        if tag == "a":
            self.anchors.append(attrs.get("href", ""))
        if tag == "img":
            self.images += 1
            if "alt" not in attrs:
                raise ValueError("Image without alt attribute: " + str(attrs))
        if tag in ("form", "input", "textarea"):
            self.forms += 1
        for attr in ("src", "href"):
            value = attrs.get(attr, "")
            if value.startswith("assets/"):
                self.assets.append(value)


def main():
    html = HTML.read_text(encoding="utf-8")
    parser = SiteParser()
    parser.feed(html)
    errors = []
    for anchor in parser.anchors:
        if anchor.startswith("#") and anchor[1:] not in parser.ids:
            errors.append("Broken anchor: " + anchor)
    for node_id in sorted(set(parser.ids)):
        if parser.ids.count(node_id) != 1:
            errors.append("Duplicate id: " + node_id)
    for file in sorted(set(parser.assets)):
        target = BASE / file
        if not target.is_file() or target.stat().st_size == 0:
            errors.append("Missing/empty asset: " + file)
    if parser.forms:
        errors.append("Unexpected forms or inputs: " + str(parser.forms))
    if parser.images < 9:
        errors.append("Expected at least nine images: " + str(parser.images))
    if len(re.findall(r'class="v20-card"', html)) != 4:
        errors.append("Four results cards expected")
    if re.search(r"\b(?:localStorage|sessionStorage|gtag\s*\(|fbq\s*\()", html):
        errors.append("Unexpected storage or analytics code")
    if not ASSETS.is_dir():
        errors.append("Missing assets directory")
    # The V45 meals and gallery use CSS background images instead of <img src>.
    atlas = ASSETS / "v45-food-atlas.webp"
    if not atlas.is_file() or atlas.stat().st_size < 1000:
        errors.append("Missing/invalid V45 food photography atlas")
    if len(re.findall(r'data-v45-day="[0-6]"', html)) != 7:
        errors.append("V45 requires seven interactive day buttons")
    if len(re.findall(r'class="v45-meal"', html)) != 4:
        errors.append("V45 requires four photo-based meal cards")
    if 'class="v44-approved-preview"' in html:
        errors.append("Flattened V44 screenshot must not appear")
    print(f"Site QA: {len(parser.ids)} IDs, {len(parser.anchors)} links, {len(set(parser.assets))} assets, {parser.images} images")
    if errors:
        for item in errors:
            print("FAIL:", item, file=sys.stderr)
        sys.exit(1)
    print("PASS: all static integrity checks")


if __name__ == "__main__":
    main()
