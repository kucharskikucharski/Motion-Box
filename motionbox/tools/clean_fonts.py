#!/usr/bin/env python3
"""Keeps only the Inter fonts Motion Box uses (Regular + SemiBold) inside fonts/ and offers to delete everything else.
Run from the project folder:  python3 tools/clean_fonts.py"""
import os

FONTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts")
KEEP = ("regular", "semibold")


def wanted(name):
    n = name.lower()
    return n.endswith((".ttf", ".otf")) and "inter" in n and "italic" not in n and any(k in n for k in KEEP)


files = [os.path.join(r, f) for r, _, fs in os.walk(FONTS) for f in fs if f.lower().endswith((".ttf", ".otf", ".woff", ".woff2", ".txt", ".md", ".html", ".css"))]
keep = {}
for p in sorted(files):                       # one file per style: the first match wins
    n = os.path.basename(p).lower()
    if wanted(n):
        style = "semibold" if "semibold" in n else "regular"
        keep.setdefault(style, p)
remove = [p for p in files if p not in keep.values()]
print("KEEP:")
for p in keep.values():
    print("  ", os.path.relpath(p, FONTS))
print(f"DELETE ({len(remove)} files):")
for p in remove[:40]:
    print("  ", os.path.relpath(p, FONTS))
if len(remove) > 40:
    print("   ...")
if remove and input("Delete these files? [y/N] ").strip().lower() == "y":
    for p in remove:
        os.remove(p)
    print("Done.")
