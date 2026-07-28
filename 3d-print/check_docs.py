#!/usr/bin/env python3
"""DOC SYNC CHECK -- does the prose still match the geometry?

The repo carries the same numbers in five places: `enclosure_geom.py` (the source
of truth), `packages/lighting.yaml` (the firmware's copy of the LED layout), and
three markdown docs that describe the build. Geometry changes ripple, and prose
does not fail a unit test -- so every previous rework left a trail of documents
describing a machine that no longer existed. The 258-wide split enclosure was
still documented as current three revisions after it stopped being built.

This is the cheap fix: assert the facts, and treat a stale doc as a build error.

    python3 check_docs.py        # ends in ALL SYNCED or a problem count

WHAT IT DOES NOT DO: judge whether prose is *good*, or notice a paragraph that
has quietly become misleading without containing a wrong number. It only catches
numbers and named features. Read the diff as well.

>>> HISTORY IS ALLOWED. Every doc deliberately keeps "this used to be X, and here
>>> is why it changed" notes -- that context is the most valuable thing in them.
>>> So a stale-value rule only fires when the old value appears OUTSIDE a line
>>> that marks it as historical. Keep using the markers below when you write one.
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import enclosure_geom as g                                   # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent

# A line carrying any of these is understood to be talking about the past.
HISTORY_MARKERS = (
    # explicitly past tense
    "history", "historical", "used to", "was ", "were ", "before ", "earlier",
    "old ", "drift", "superseded", "removed", "would ", "it never fit",
    # explicitly negating the stale term -- "there is no fade band" must not be
    # flagged for containing "fade band". This is the common case by far: the
    # most useful sentence about a dead feature is the one that kills it.
    "no longer", "is gone", "any more", "there is no", "no separate",
    "not 48", "and not 48", "reel", "circular", "split in two",
)

problems = []


def load(rel):
    p = ROOT / rel
    if not p.exists():
        problems.append(f"{rel}: MISSING FILE")
        return ""
    return p.read_text()


DOCS = {r: load(r) for r in (
    "HARDWARE.md", "SOUNDMACHINE.md", "CLAUDE.md",
    "3d-print/README.md", "3d-print/WIP-NOTES.md",
    "packages/lighting.yaml",
)}


def must(doc, pattern, why):
    """This fact has to appear somewhere in this document."""
    if not re.search(pattern, DOCS.get(doc, "")):
        problems.append(f"{doc}: missing {why}   /{pattern}/")


def must_not(doc, pattern, why):
    """This value is stale. Flag it unless the line calls itself history."""
    hits = []
    for i, line in enumerate(DOCS.get(doc, "").split("\n"), 1):
        if not re.search(pattern, line):
            continue
        if any(m in line.lower() for m in HISTORY_MARKERS):
            continue
        hits.append(f"line {i}: {line.strip()[:90]}")
    for h in hits:
        problems.append(f"{doc}: STALE {why}\n      {h}")


rows = [c for _, c, _ in g.crescent_rows()]
row_re = re.escape(str(rows).replace("[", "{").replace("]", "}"))

# ---------------------------------------------------------------- firmware
# The one place a stale number does more than mislead: ESPHome will happily
# address pixels that do not physically exist.
must("packages/lighting.yaml", rf"num_leds:\s*{g.CRES_PX}\b", "num_leds")
must("packages/lighting.yaml", rf"leds_per_row\[\] = {row_re}", "row array")
must("packages/lighting.yaml", rf"{g.LED_PITCH}mm", "measured LED pitch")
must("packages/lighting.yaml", rf"{g.LED_ROW_PITCH}, NOT", "row pitch")

# ------------------------------------------------------------------- docs
must("HARDWARE.md", rf"\*\*{g.CRES_PX} pixels\*\*", "pixel count")
must("HARDWARE.md", rf"{g.W} × {g.D:g} × {g.H:.1f}", "envelope")
must("HARDWARE.md", rf"{g.CRES_R:g} × {g.CRES_RY:.1f}", "crescent ellipse")
must("HARDWARE.md", r"rotated 90", "the speaker rotation")
# The LED clearance figure is quoted in prose and drifted twice unnoticed --
# it is the number the whole ellipse-distance rework exists to protect.
must("HARDWARE.md", rf"\*\*{g.crescent_clearance():.2f} mm\*\*",
     "the LED-to-diffuser clearance")
must("3d-print/README.md", rf"{g.W-2*g.REVEAL:.1f} × {g.H-g.REVEAL-g.BP_T:.1f}",
     "front module size")
must("3d-print/README.md", rf"{g.W} × {g.D:g} × {g.H:.1f}", "envelope")
must("3d-print/README.md", r"led-carrier\.stl", "the LED carrier part")
must("SOUNDMACHINE.md", rf"{g.CRES_PX} px", "pixel count")
must("CLAUDE.md", rf"\*\*{g.CRES_PX} px\*\*", "pixel count")
must("CLAUDE.md", r"3d-print/README\.md", "the enclosure doc link")

# --------------------------------------------------------------- staleness
PROSE = ("HARDWARE.md", "SOUNDMACHINE.md", "CLAUDE.md", "3d-print/README.md")

# >>> DERIVE THE STALE SET, DO NOT HARD-CODE IT. The first version of this rule
# >>> literally banned "48 px" because 48 happened to be the superseded value
# >>> that week. The count then went back to 48 and the checker started failing
# >>> every correct document. A staleness rule keyed to a fixed number is itself
# >>> a thing that goes stale -- so the banned set is every plausible count
# >>> EXCEPT the one the geometry currently produces.
_stale_px = "|".join(str(v) for v in range(38, 56) if v != g.CRES_PX)
for d in PROSE:
    must_not(d, rf"\b(?:{_stale_px})\s*(?:px|pixels|LEDs)\b",
             f"a pixel count other than {g.CRES_PX}")
    must_not(d, r"\b258\s*(?:mm|×|x)\b|258×64|258 × 64", "258 mm wide body")
    must_not(d, r"\bR117\b|\bR96\b|\bR80\b", "circular crescent radii")
    must_not(d, r"16\.7\s*mm", "16.7 mm LED pitch (measured 16.5)")
    must_not(d, r"front-module-[LR]\.stl", "the split front module")
    # NOT "side nub" -- the nubs still exist, they are just rotated, and
    # SPK_NUB_Z = 7 "behind the front face" is still a true measured fact.
    must_not(d, r"beside each flank|post beside each|nub per side", "pre-rotation mount")
    must_not(d, r"fade band", "the fade band")

# --------------------------------------------------------- drawing drift
# >>> THE SHEETS DRIFT SILENTLY, because a drawing that is wrong still renders.
# >>> The rear view drew the UPS and the Flex on the CENTRELINE for several
# >>> revisions after they went side by side, and no sheet drew the power switch
# >>> or the crown bosses at all -- which is how an encoder boss and a ToF boss
# >>> came to overlap by 2.9 mm without anyone seeing it. These rules assert that
# >>> each generator at least REFERENCES the feature, so a new part cannot be
# >>> added to the model and left off the drawings.
DRAW = {r: load(r) for r in ("3d-print/gen_drawing.py",
                             "3d-print/gen_internals.py")}


def draws(doc, pattern, why):
    if not re.search(pattern, DRAW.get(doc, "")):
        problems.append(f"{doc}: does not draw {why}   /{pattern}/")


def not_centred(doc, pattern, why):
    """A rear-wall feature that is NOT on the centreline must not be drawn at
    W/2. This is the exact bug the UPS and the Flex had."""
    for i, line in enumerate(DRAW.get(doc, "").split("\n"), 1):
        if re.search(pattern, line) and re.search(r"\bW\s*/\s*2\b", line):
            problems.append(f"{doc}: {why} drawn on the centreline\n"
                            f"      line {i}: {line.strip()[:88]}")


draws("3d-print/gen_drawing.py", r"SW_WALL_X", "the UPS power switch")
draws("3d-print/gen_drawing.py", r"ENC_HOLE_P", "the encoder crown bosses")
draws("3d-print/gen_drawing.py", r"TOF_HOLE_P", "the ToF crown bosses")
draws("3d-print/gen_drawing.py", r"LOUVRE", "the vents as louvres")
draws("3d-print/gen_internals.py", r"SPK_POST_W", "the rotated speaker posts")
not_centred("3d-print/gen_drawing.py", r"UPS_W", "the UPS")
not_centred("3d-print/gen_drawing.py", r"FLEX_PCB_W|FLEX_HOLE_PX|FLEX_W\b", "the Flex")

print(f"geometry: {g.W} x {g.D:g} x {g.H:.2f}   {g.CRES_PX} px {rows}   "
      f"pitch {g.LED_PITCH}/{g.LED_ROW_PITCH}   CROWN_K {g.CROWN_K}")
print(f"checked:  {len(DOCS)} documents")
print("")
if problems:
    for p in problems:
        print(f"  FAIL  {p}")
    print(f"\n*** {len(problems)} PROBLEM(S) ***")
    sys.exit(1)
print("ALL SYNCED")
