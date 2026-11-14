#!/usr/bin/env python3
"""Build-time integrity checks for the Telo Pod Klyuch static website."""
from html.parser import HTMLParser
from pathlib import Path
import re
import sys
import struct

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


def webp_size(path):
    """Read WebP dimensions without third-party packages."""
    with path.open("rb") as fh:
        header = fh.read(30)
    if len(header) < 30 or header[:4] != b"RIFF" or header[8:12] != b"WEBP":
        return None
    kind = header[12:16]
    if kind == b"VP8X":
        return (int.from_bytes(header[24:27], "little") + 1,
                int.from_bytes(header[27:30], "little") + 1)
    if kind == b"VP8 " and header[23:26] == b"\\x9d\\x01\\x2a":
        return (struct.unpack_from("<H", header, 26)[0] & 0x3fff,
                struct.unpack_from("<H", header, 28)[0] & 0x3fff)
    if kind == b"VP8L" and header[20] == 0x2f:
        val = int.from_bytes(header[21:25], "little")
        return ((val & 0x3fff) + 1, ((val >> 14) & 0x3fff) + 1)
    return None


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
    # V47: validate the image pipeline rather than merely checking file existence.
    atlas_resolution = webp_size(atlas) if atlas.is_file() else None
    if atlas_resolution:
        print("V47 photo audit: atlas resolution:", atlas_resolution,
              "effective single-dish pixels:", tuple(x // 2 for x in atlas_resolution))
        if atlas_resolution[0] < 1280 or atlas_resolution[1] < 744:
            print("WARN: photo atlas below Retina 2x for 320x186 cards; replace with dedicated high-res images.")
    else:
        errors.append("Unable to decode V45 food atlas dimensions")
    for asset in ("hero-01-fish.webp", "hero-02-steak.webp", "hero-03-constructor.webp"):
        size = webp_size(ASSETS / asset)
        if not size or min(size) < 700:
            errors.append("Hero photograph has missing or low dimensions: " + asset)
    if re.search(r"\\.v45-meal-photo\\.v45-photo-(?:omelet|chicken|dessert)\\s*\\{[^}]*background-size:\\s*(?:[3-9]\\d\\d|[1-9]\\d{3})%", html):
        errors.append("Excessive meal photo atlas zoom will introduce blur")
    if len(re.findall(r"\\[\\['[^\\n]+?','[^\\n]+?',(?:'omelet'|'chicken'|'salmon'|'dessert'|'steak'|'crab')\\]", html)) < 28:
        print("WARN: 28 meal photo mappings should be reviewed for uniqueness and recipe fidelity")
    print(f"Site QA: {len(parser.ids)} IDs, {len(parser.anchors)} links, {len(set(parser.assets))} assets, {parser.images} images")
    if errors:
        for item in errors:
            print("FAIL:", item, file=sys.stderr)
        sys.exit(1)
    print("PASS: all static integrity checks")


if __name__ == "__main__":
    main()
