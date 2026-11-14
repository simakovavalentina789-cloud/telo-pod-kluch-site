#!/usr/bin/env python3
"""Download licensed editorial food photographs once; commit generated WebP files.
Source photos remain independently credited, never stretched from a 2x2 atlas.
This script is intended for GitHub Actions (network permitted)."""
from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen
from PIL import Image, ImageOps

OUT=Path("assets/food-v51")
# Unsplash License / Pexels License: free use; photographer and source are recorded below.
SOURCES={
    "omelet": ("https://images.unsplash.com/photo-1510693206972-df098062cb71?auto=format&fit=crop&w=2000&q=90", "Eaters Collective", "https://unsplash.com/photos/6rtm6a_aVyE"),
    "frittata": ("https://images.unsplash.com/photo-1637036124319-4fa1881c9ce6?auto=format&fit=crop&w=2000&q=90", "Elena Leya", "https://unsplash.com/photos/-KgQ-bDTreA"),
    "chicken": ("https://images.unsplash.com/photo-1763219802762-1d34ee0907c5?auto=format&fit=crop&w=2000&q=90", "Emmanuel M", "https://unsplash.com/photos/fslrfR2fp-A"),
    "dessert": ("https://images.unsplash.com/photo-1455099675745-a442989ac8bf?auto=format&fit=crop&w=2000&q=90", "Sambazon", "https://unsplash.com/photos/86Xd_vAyFv4"),
    "crab": ("https://images.pexels.com/photos/20095290/pexels-photo-20095290/free-photo-of-close-up-of-a-healthy-seafood-dish.jpeg?auto=compress&w=2000", "Nadin Sh", "https://www.pexels.com/photo/20095290/"),
}
OUT.mkdir(parents=True,exist_ok=True)
for name,(url,author,source) in SOURCES.items():
    path=OUT/(name+".webp")
    if path.is_file() and path.stat().st_size>12000:
        with Image.open(path) as existing:
            if existing.width>=1000 and existing.height>=600:
                print("SKIP existing:",name,existing.size)
                continue
    req=Request(url,headers={"User-Agent":"Mozilla/5.0 (TPK website image optimization)"})
    with urlopen(req,timeout=40) as stream:
        data=stream.read(15_000_000)
    with Image.open(BytesIO(data)) as src:
        src=ImageOps.exif_transpose(src).convert("RGB")
        if src.width<1000 or src.height<600:
            raise ValueError(f"{name}: source too small: {src.size}")
        image=ImageOps.fit(src,(1200,700),method=Image.Resampling.LANCZOS,centering=(0.5,0.5))
        image.save(path,"WEBP",quality=88,method=6)
    if path.stat().st_size<12000:
        raise ValueError(f"{name}: unexpectedly small result")
    print("CREATED",path,path.stat().st_size,author,source)
print("PHOTO PIPELINE OK")
