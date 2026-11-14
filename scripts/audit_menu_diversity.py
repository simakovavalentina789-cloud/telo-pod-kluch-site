#!/usr/bin/env python3
"""Editorial audit of the seven-day demonstration menu.

This is an advisory report until unique verified recipes and their exact
photographs have replaced all legacy repeated slots. Never confuse distinct
names with distinct recipes.
"""
from collections import defaultdict
from pathlib import Path
import re
import sys
import unicodedata

html=Path(__file__).resolve().parents[1].joinpath("index.html").read_text(encoding="utf-8")
match=re.search(r"const v45Days=\[(.*?)\];",html,re.S)
if not match:
    sys.exit("FAIL: v45Days not found")
raw=match.group(1)
rows=re.findall(r"\['([^'\n]+)','([^'\n]+)','([^'\n]+)'\]",raw)
if len(rows)!=28:
    sys.exit(f"FAIL: expected 28 menu entries, found {len(rows)}")
days=["Понедельник","Вторник","Среда","Четверг","Пятница","Суббота","Воскресенье"]
roles=["Завтрак","Обед","Ужин","Перекус"]
# Conservative editorial-family mapping: sauces/greens and word changes are
# not sufficient to create a separate recipe. Manual verification is required.
FAMILIES={
    "омлет": "омлет",
    "фриттат": "фриттата",
    "стейк": "стейк из говядины с овощами",
    "говяжий стейк": "стейк из говядины с овощами",
    "краб": "крабовый салат",
    "куриц": "курица с крупой и овощами",
    "лосос": "лосось с овощами",
    "мусс": "творожный/ягодный мусс",
    "десерт": "творожный/ягодный мусс",
}
families=defaultdict(list)
photos=defaultdict(list)
exact=defaultdict(list)
for ix,(name,note,photo) in enumerate(rows):
    role=roles[ix%4];day=days[ix//4]
    n=unicodedata.normalize("NFKC",name.lower())
    family=next((v for k,v in FAMILIES.items() if k in n),"другое")
    families[family].append((day,role,name))
    exact[n].append((day,role))
    photos[photo].append((day,role,name))
print("MENU DIVERSITY AUDIT | 7 days × 4 meals")
print("Unique exact names:",len(exact),"/ 28")
print("Unique broad recipe families:",len(families),"/ 28")
print("Unique photo keys:",len(photos),"/ 28")
for title,groups in (("REPEATED RECIPE FAMILIES",families),
                     ("REPEATED PHOTO KEYS",photos),
                     ("IDENTICAL NAMES",exact)):
    print("\n"+title)
    for key,items in groups.items():
        if len(items)>1:
            print(f"  {key}: {len(items)}")
            for item in items: print("   - "+" | ".join(item))
# Explicit prohibition on releasing a claim of 28 distinct recipes unless
# each is independently reviewed and matched to its unique recipe/photo ID.
if len(families)!=28 or len(photos)!=28:
    print("\nSTATUS: NEEDS_EDITORIAL_REWORK. Do not claim 28 distinct recipes.")
    if "--strict" in sys.argv:
        sys.exit(1)
else:
    print("\nSTATUS: DIVERSITY CANDIDATE ONLY; still requires recipe-level audit.")
