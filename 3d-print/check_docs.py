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
# >>> EVERY REAR-WALL BOARD MUST REACH A SHEET. The rear elevation used to name
# >>> the UPS and the Flex by hand, so the lux and the RTC -- four bosses each --
# >>> were on no drawing anywhere, and their standoffs were unidentifiable when
# >>> they showed up in a model. Drawing the list means new boards cannot be
# >>> silently omitted; this rule means the list cannot be bypassed again.
draws("3d-print/gen_drawing.py", r"rear_wall_boards\(\)",
      "the rear-wall boards from the shared list")
draws("3d-print/gen_drawing.py", r"RTC_WALL_X", "the RTC, labelled")

# >>> VENDOR GEOMETRY IS NOT NEGOTIABLE, AND THIS ONE HAS ALREADY MOVED ONCE ON A
# >>> VERBAL REPORT. Adafruit's "CharliePlex Grid.brd" declares the matrix's two
# >>> mounting holes outright; they were nonetheless swapped to the other diagonal
# >>> because the posts LOOKED mirrored -- which is what the plate's back face
# >>> always looks like. Assert the published numbers so an eyeball cannot
# >>> overrule them again without someone deleting this rule on purpose.
_ADAFRUIT_MTX_HOLES = [(1.905, 26.035), (41.275, 1.905)]   # Grid.brd <plain>
if sorted(g.MTX_HOLES_BOARD) != sorted(_ADAFRUIT_MTX_HOLES):
    problems.append(
        f"enclosure_geom.py: MTX_HOLES_BOARD = {g.MTX_HOLES_BOARD} but Adafruit's "
        f"board file says {_ADAFRUIT_MTX_HOLES}\n"
        f"      (CharliePlex Grid.brd, <plain>: hole 1.905,26.035 and "
        f"41.275,1.905, drill 2)")
# >>> ...AND THE FLIP INTO PART COORDINATES MUST STILL BE THERE. Asserting only
# >>> the vendor numbers is what let the mirrored version pass review: the source
# >>> was quoted correctly and used in the wrong frame. Check the RESULT too.
_want_part = sorted((hx, round(g.MTX_BOARD_H - hy, 3))
                    for hx, hy in _ADAFRUIT_MTX_HOLES)
if [(a, round(b, 3)) for a, b in sorted(g.MTX_HOLES)] != _want_part:
    problems.append(
        f"enclosure_geom.py: MTX_HOLES = {g.MTX_HOLES}; the board-to-part flip "
        f"gives {_want_part}. The LEDs face FORWARD, so the board's frame is 180 "
        f"deg from the part's and one in-plane axis inverts.")
if (g.MTX_BOARD_W, g.MTX_BOARD_H) != (43.18, 27.94):
    problems.append(
        f"enclosure_geom.py: matrix outline {g.MTX_BOARD_W} x {g.MTX_BOARD_H} "
        f"but the board file's outline wires give 43.18 x 27.94")
if g.MTX_HOLE_D != 2.0:
    problems.append(f"enclosure_geom.py: MTX_HOLE_D = {g.MTX_HOLE_D}, "
                    f"Adafruit drills these 2.0")
# the driver's pattern, from the fab print (1.5 x 0.9 inside 1.7 x 1.1)
_ADAFRUIT_BP_HOLES = [(2.54, 2.54), (2.54, 25.4), (40.64, 2.54), (40.64, 25.4)]
if sorted(g.MTX_BP_HOLES_BOARD) != sorted(_ADAFRUIT_BP_HOLES):
    problems.append(
        f"enclosure_geom.py: MTX_BP_HOLES_BOARD = {g.MTX_BP_HOLES_BOARD} but the fab print "
        f"gives 1.5\" x 0.9\" centred in 1.7\" x 1.1\" = {_ADAFRUIT_BP_HOLES}")
# >>> AND THE TWO PATTERNS MUST STAY NON-COINCIDENT. The whole architecture rests
# >>> on this: driver holes are 0.100" in from the edges, matrix holes 0.075", so
# >>> nothing lines up and the driver cannot be posted through the matrix. If a
# >>> future edit ever makes them agree, the mount can be simplified -- and if
# >>> someone assumes they agree without checking, it cannot.
_closest = min(((dx - mx) ** 2 + (dy - my) ** 2) ** 0.5
               for dx, dy in g.MTX_BP_HOLES for mx, my in g.MTX_HOLES)
if _closest < 1.5:
    pass          # expected: 0.898 mm. Recorded so the number is visible.
else:
    problems.append(f"enclosure_geom.py: driver/matrix holes are now {_closest:.2f} "
                    f"mm apart; the 'cannot post through the matrix' note is stale")

# >>> ONE HOLE PATTERN PER BOARD, NEVER A PITCH. rear_wall_boards() and
# >>> plate_boards() used to hand out a single hole PITCH and the generators built
# >>> a four-boss square from it. That is only correct for a board with four
# >>> symmetric holes. The DS3231 has TWO, side by side, so two of its bosses stood
# >>> on bare PCB and would have rocked the board off the other two; the UPS has
# >>> four but on 46 x 86, which no single pitch describes. Assert the shape of the
# >>> data, because the bug was in the shape of the data.
for _fn, _rows in (("rear_wall_boards", g.rear_wall_boards()),
                   ("plate_boards", g.plate_boards())):
    for _r in _rows:
        _offs = _r[5]
        if _offs is None:
            continue
        if not isinstance(_offs, (list, tuple)) or (_offs and not
                                                   isinstance(_offs[0], tuple)):
            problems.append(
                f"enclosure_geom.py: {_fn}() gives {_r[0]} hole data {_offs!r}. "
                f"This field is a LIST OF (dx, dy) OFFSETS, not a pitch -- a "
                f"single number cannot describe a hole pattern, and pretending it "
                f"could put two of the DS3231's bosses on bare PCB.")
_rtc_bosses = [len(r[5]) for r in g.rear_wall_boards() if r[0] == "RTC"]
if _rtc_bosses != [2]:
    problems.append(
        f"enclosure_geom.py: the RTC is getting {_rtc_bosses} bosses. Adafruit's "
        f"DS3231 (STEMMA QT version) has exactly TWO mounting holes, at "
        f"{g.RTC_HOLES} on a {g.RTC_HOLE_P} mm pitch. A third or fourth boss lands "
        f"on bare board.")
if len(g.UPS_HOLES) != 4 or g.UPS_HOLE_D < 3.0:
    problems.append(
        f"enclosure_geom.py: UPS_HOLES = {g.UPS_HOLES}, D {g.UPS_HOLE_D}. The "
        f"Waveshare 3S UPS DXF gives four {chr(216)}3.1 holes on 46 x 86.")
if g.REAR_BOARD_SCREW.get("UPS") != 3.0:
    problems.append(
        "enclosure_geom.py: the UPS wants M3 -- its holes are 3.1. Driving every "
        "rear-wall boss from one BOSS_PILOT_D gave a 200 g battery pack four "
        "M2.5 screws in oversize holes.")

# >>> THE AMP HAS ONE HOLE PATTERN AND ONE TRANSFORM. There were two constants for
# >>> its hole spacing: the real 22.86 read out of Adafruit's board file, and a
# >>> stale AMP_HOLE_P = 20.0 "(?) MEASURE" placeholder 800 lines further down --
# >>> and it was the placeholder that every generator imported. Assert the vendor
# >>> numbers, assert the placeholder is gone, and assert the lay-down transform is
# >>> a rigid motion, because the amp lies with its long axis across the machine
# >>> and the bosses did not follow it round.
_ADAFRUIT_AMP_HOLES = [(19.05, 2.54), (19.05, 25.40)]     # TPA2016D2.brd
if sorted(g.AMP_HOLES) != sorted(_ADAFRUIT_AMP_HOLES):
    problems.append(
        f"enclosure_geom.py: AMP_HOLES = {g.AMP_HOLES} but the board file's "
        f"dimension objects snap to {_ADAFRUIT_AMP_HOLES} "
        f"(MOUNTINGHOLE_2.5_PLATED_THICK elements, not <plain> holes)")
if hasattr(g, "AMP_HOLE_P"):
    problems.append(
        "enclosure_geom.py: AMP_HOLE_P is back. It was a placeholder that shadowed "
        "the measured pattern; there must be exactly one amp hole definition.")
_ap = g.amp_holes_part()
_span_b = max(((a[0]-b[0])**2 + (a[1]-b[1])**2)**0.5
              for a in g.AMP_HOLES for b in g.AMP_HOLES)
_span_p = max(((a[0]-b[0])**2 + (a[1]-b[1])**2)**0.5
              for a in _ap for b in _ap)
if abs(_span_b - _span_p) > 0.01:
    problems.append(
        f"enclosure_geom.py: amp_holes_part() moves the holes {_span_p:.2f} mm "
        f"apart from {_span_b:.2f}. Laying the board down rotates it; a rotation "
        f"preserves distances.")
if len({round(y, 3) for _, y in _ap}) != 1 or len({round(x, 3) for x, _ in _ap}) != 2:
    problems.append(
        f"enclosure_geom.py: amp_holes_part() = {_ap}. The amp's long axis runs "
        f"ACROSS the machine, so its two holes must differ in x and share a depth.")
if abs(_ap[0][1]) < 1.0:
    problems.append(
        f"enclosure_geom.py: amp_holes_part() puts the holes {_ap[0][1]:.2f} from "
        f"the board's depth centre. Both are at board x = 19.05, which is 8.26 off "
        f"a 21.59-wide centre -- on the centreline the board cannot go on at all.")

# >>> WHERE THE RTC LIVES IS ASSERTED, NOT DESCRIBED. The docs said "the rear
# >>> wall is FULL and the RTC had to leave it" for the whole time that had
# >>> stopped being true. Tie the prose to RTC_ON_FLOOR so it cannot say one and
# >>> the geometry do the other.
# >>> THESE TWO ARE ASSERTED AS STATE, NOT MATCHED AS PROSE, AND THE FIRST
# >>> ATTEMPT AT THEM IS THE REASON WHY. Written as must_not() against phrases
# >>> like "the vents are two stacks flanking the UPS", both rules passed while
# >>> the geometry said the opposite -- because the sentence that had gone stale
# >>> read "This WAS two stacks...", and "was " is a HISTORY_MARKER. must_not
# >>> deliberately skips lines that talk about the past, which is right, and it
# >>> means a rule aimed at explanatory prose is defeated by the explanation.
# >>> So HARDWARE.md carries one short canonical line of current state, and these
# >>> compare it against the geometry. The prose stays free to explain itself.
_state = {1: "1"}.get(len(g.vent_x()), str(len(g.vent_x())))
must("HARDWARE.md", rf"\*\*Vent stacks: {_state}\*\*",
     f"a current-state line saying there are {len(g.vent_x())} vent stack(s)")
must("HARDWARE.md",
     r"\*\*RTC mounts on: " + ("bottom plate" if g.RTC_ON_FLOOR else "rear wall")
     + r"\*\*",
     "a current-state line saying where the RTC mounts")

# >>> AND THAT THE FDM RAMPS ARE DOCUMENTED WHERE THEY ARE BUILT.
must("3d-print/README.md", r"Printing rear-wall down means \+z is \*down\*",
     "the print-direction section that explains which faces need support")
for _pat, _why in ((r"_ramp_void", "the retaining rib's ramp"),
                   (r"crown_boss_ramp", "the crown standoff buttresses"),
                   (r"overhang audit", "the overhang audit")):
    if not re.search(_pat, load("3d-print/gen_dome.py")):
        problems.append(f"3d-print/gen_dome.py: no longer builds {_why}")

# >>> AND NO RAMP MAY GO BACK TO BEING A STAIRCASE. Stepping is the slicer's job:
# >>> Orca resolves a true 45 deg face to the actual nozzle and layer height far
# >>> better than a staircase frozen into an STL, and the steps cost 12000
# >>> triangles and caused all three of this file's mesh failures.
_dome_src = load("3d-print/gen_dome.py")
for _pat, _why in ((r"RIB_RAMP_STEPS", "the rib ramp"),
                   (r"VENT_STEPS", "the louvres")):
    if re.search(_pat, _dome_src):
        problems.append(f"3d-print/gen_dome.py: {_why} is stepped again "
                        f"({_pat}) -- model true angles, let the slicer step them")
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
