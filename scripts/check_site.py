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
    if kind == b"VP8 " and header[23:26] == bytes((0x9d, 0x01, 0x2a)):
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
    # V51: original high-resolution photos must be present in the deployed assets.
    for dish in ("omelet", "frittata", "crab", "chicken"):
        file = ASSETS / "food-v51" / (dish + ".webp")
        size = webp_size(file) if file.is_file() else None
        if not size or size[0] < 1200 or size[1] < 675:
            errors.append("Missing/undersized original food photograph: " + str(file))
        if "assets/food-v51/" + dish + ".webp" not in html:
            errors.append("Food photograph is not connected to site: " + dish)
    # V52: six new independently generated food photographs, each at Retina resolution.
    v52_names = ("dessert-mousse", "dessert-berries", "omelet-tomato",
                 "omelet-baked", "frittata-greens", "chicken-quinoa")
    for dish in v52_names:
        asset = ASSETS / "food-v52" / (dish + ".webp")
        dimensions = webp_size(asset) if asset.is_file() else None
        if not dimensions or dimensions[0] < 1200 or dimensions[1] < 675:
            errors.append("V52 image missing or below Retina resolution: " + str(asset))
        if "v45-photo-" + dish not in html:
            errors.append("V52 dish photo is not connected to a meal: " + dish)
        if dish + ".webp" not in html:
            # JavaScript intentionally constructs the filename from a stable mapping.
            if "'assets/food-v52/'+n+'.webp'" not in html:
                errors.append("V52 image path is not found in code: " + dish)
    # V53: six unique food photographs and corresponding menu slots.
    v53_names = ("syrniki-berries","avocado-poached-egg","turkey-bulgur","chicken-buckwheat","greek-yogurt-berries","chia-mango")
    for dish in v53_names:
        asset = ASSETS / "food-v53" / (dish + ".webp")
        dimensions = webp_size(asset) if asset.is_file() else None
        if not dimensions or dimensions[0] < 1200 or dimensions[1] < 675:
            errors.append("V53 photograph missing/low-resolution: " + str(asset))
        if "'"+dish+"'" not in html:
            errors.append("V53 dish photo not mapped in weekly menu: " + dish)
    if "assets/food-v53/" not in html:
        errors.append("V53 photo URL mapping missing")
    if "salmon:'assets/hero-01-fish.webp'" not in html or "steak:'assets/hero-02-steak.webp'" not in html:
        errors.append("Approved salmon or steak photos were changed")
    # V54: independent, non-repeated photos for six precise menu slots.
    v54_names = ("oatmeal-berries","turkey-pumpkin","stuffed-peppers","zucchini-ricotta","apple-crumble","pumpkin-soup")
    for dish in v54_names:
        asset = ASSETS / "food-v54" / (dish + ".webp")
        dims = webp_size(asset) if asset.is_file() else None
        expected_width = 1200 if dish == "turkey-pumpkin" else 500
        if not dims or dims[0] < expected_width or dims[1] < 450:
            errors.append("V54 photograph missing or undersized: " + str(asset))
        if "'"+dish+"'" not in html:
            errors.append("V54 unique dish mapping missing: " + dish)
    if "assets/food-v54/" not in html:
        errors.append("V54 photo URL mapping missing")
    # V55: all six images are independently generated original Retina assets.
    v55_names = ("shakshuka", "buckwheat-egg-mushrooms", "beef-meatballs-bulgur", "cod-rice-broccoli", "cottage-peach-berries", "baked-pears-yogurt")
    for dish in v55_names:
        asset = ASSETS / "food-v55" / (dish + ".webp")
        dimensions = webp_size(asset) if asset.is_file() else None
        if not dimensions or dimensions[0] < 1600 or dimensions[1] < 900:
            errors.append("V55 missing/undersized Retina photograph: " + str(asset))
        if "'" + dish + "'" not in html:
            errors.append("V55 meal mapping missing: " + dish)
    if "assets/food-v55/" not in html:
        errors.append("V55 food image URL resolver missing")
    if "salmon:'assets/hero-01-fish.webp'" not in html or "steak:'assets/hero-02-steak.webp'" not in html:
        errors.append("Previously approved salmon/steak asset replaced")
    # V56 release gate: each demo slot has a distinct displayed name and photo key.
    unique_beef = ASSETS / "food-v56" / "braised-beef-potato.webp"
    dimensions = webp_size(unique_beef) if unique_beef.is_file() else None
    if not dimensions or dimensions[0] < 1600 or dimensions[1] < 900:
        errors.append("Saturday braised beef photo missing or below Retina resolution")
    if "'Томлёная говядина с картофелем и морковью'" not in html:
        errors.append("Saturday dinner must be unique braised beef")
    if "braised-beef-potato:'assets/food-v56/braised-beef-potato.webp'" not in html and "'braised-beef-potato':'assets/food-v56/braised-beef-potato.webp'" not in html:
        errors.append("Saturday dinner photo mapping missing")
    # V57: dedicated full-resolution replacement for the old oatmeal crop.
    crisp_oatmeal = ASSETS / "food-v57" / "oatmeal-berries.webp"
    crisp_size = webp_size(crisp_oatmeal) if crisp_oatmeal.is_file() else None
    if not crisp_size or crisp_size[0] < 1600 or crisp_size[1] < 900:
        errors.append("V57 oatmeal image missing or below full Retina resolution")
    if "'oatmeal-berries':'assets/food-v57/oatmeal-berries.webp'" not in html:
        errors.append("V57 oatmeal must be mapped to the original full-res asset")
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
    if re.search(r"\.v45-meal-photo\.v45-photo-(?:omelet|chicken|dessert)\s*\{[^}]*background-size:\s*(?:[3-9]\d\d|[1-9]\d{3})%", html):
        errors.append("Excessive meal photo atlas zoom will introduce blur")
    photo_mappings = re.findall(r"\['[^'\n]+','[^'\n]+','(omelet|chicken|salmon|dessert|steak|crab|frittata|dessert-mousse|dessert-berries|omelet-tomato|omelet-baked|frittata-greens|chicken-quinoa|syrniki-berries|avocado-poached-egg|turkey-bulgur|chicken-buckwheat|greek-yogurt-berries|chia-mango|oatmeal-berries|turkey-pumpkin|stuffed-peppers|zucchini-ricotta|apple-crumble|pumpkin-soup|shakshuka|buckwheat-egg-mushrooms|beef-meatballs-bulgur|cod-rice-broccoli|cottage-peach-berries|baked-pears-yogurt|braised-beef-potato)'\]", html)
    if len(photo_mappings) != 28:
        errors.append("Expected 28 weekly menu meal-to-photo mappings; found: " + str(len(photo_mappings)))
    if len(photo_mappings) >= 5 and photo_mappings[0] == photo_mappings[4]:
        errors.append("Monday and Tuesday breakfast photos must not be identical")
    if 'Фриттата с зеленью и луком' not in html or "'frittata'" not in html:
        errors.append("Dedicated Tuesday frittata mapping missing")
    all_demo_meals = re.findall(r"\['([^'\n]+)','[^'\n]+','([^'\n]+)'\]", html[html.index("const v45Days="):html.index("const v45Names=")])
    if len(all_demo_meals) != 28:
        errors.append("Demo must contain exactly 28 meals")
    elif len({name.casefold() for name, _ in all_demo_meals}) != 28:
        errors.append("Demo contains duplicate dish names")
    elif len({photo for _, photo in all_demo_meals}) != 28:
        errors.append("Demo contains photo-key reuse, each card must be visually unique")
    if len(set(photo_mappings)) < 7:
        print("WARN: only", len(set(photo_mappings)), "distinct food photos serve 28 menu entries")
    if 'const selectV45Day=' not in html or "event.key==='ArrowRight'" not in html:
        errors.append("Weekly menu keyboard navigation missing")
    print(f"Site QA: {len(parser.ids)} IDs, {len(parser.anchors)} links, {len(set(parser.assets))} assets, {parser.images} images")
    if errors:
        for item in errors:
            print("FAIL:", item, file=sys.stderr)
        sys.exit(1)
    print("PASS: all static integrity checks")


if __name__ == "__main__":
    main()
