#!/usr/bin/env python3
"""DOC SYNC CHECK -- does the prose still match the geometry?

The repo carries the same numbers in five places: `enclosure_geom.py` (the source
of truth), `packages/hw/crescent.yaml` (the firmware's copy of the LED layout), and
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
    # The session build journal used to be listed here. Prototype 1 is built and
    # the journal now lives only on the v1 release branch; ../RETROSPECTIVE.md
    # carries its conclusions. Nothing asserted against it (it was never in
    # PROSE), so it is simply gone rather than repointed.
    "3d-print/README.md",
    # FUTURE-DEVELOPMENT.md quotes LIVE values (led_max_pct, touch_threshold, the
    # pixel count), so it can go stale exactly like the others and is checked.
    # RETROSPECTIVE.md deliberately is NOT: it is history, and the stale-value
    # rules exist to flag precisely the numbers it is supposed to be talking about.
    "FUTURE-DEVELOPMENT.md",
    "packages/hw/crescent.yaml",
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
row_list_re = re.escape(", ".join(str(c) for c in rows))

# ---------------------------------------------------------------- firmware
# The one place a stale number does more than mislead: ESPHome will happily
# address pixels that do not physically exist.
must("packages/hw/crescent.yaml", rf"num_leds:\s*{g.CRES_PX}\b", "num_leds")
# The row array and the two pitches are SUBSTITUTIONS defined once at the top of
# crescent.yaml, and the effects below expand them. They used to be C++ literals
# repeated in each effect, which is what made the presence-only rule below
# insufficient - see the note there.
must("packages/hw/crescent.yaml", rf'crescent_rows:\s*"{row_list_re}"', "row array")
must("packages/hw/crescent.yaml", rf'crescent_pitch_x:\s*"{re.escape(str(g.LED_PITCH))}"', "LED pitch")
must("packages/hw/crescent.yaml", rf'crescent_pitch_y:\s*"{re.escape(str(g.LED_ROW_PITCH))}"', "row pitch")
must("packages/hw/crescent.yaml", rf"{g.LED_PITCH}mm", "measured LED pitch in prose")
must("packages/hw/crescent.yaml", rf"{g.LED_ROW_PITCH}, NOT", "row pitch in prose")

# ...and there must be no second, hard-coded copy for those rules to miss. An
# effect must expand ${crescent_rows}, never re-type the digits.
must_not("packages/hw/crescent.yaml", r"leds_per_row\[\]\s*=\s*\{\s*\d",
         "a hard-coded row array (use ${crescent_rows})")

# >>> PRESENCE IS NOT ENOUGH, and this file learned that the hard way. must()
# >>> above passed for months while crescent.yaml ALSO carried "rows are 11.0
# >>> apart" in the effect's own comment block -- the one the header points at as
# >>> the authority for the row layout. Both sentences were in the same file. A
# >>> rule that only asks "is the right number in here somewhere" cannot see the
# >>> wrong one sitting next to it, so the row pitch gets a staleness rule too.
# >>> (The array itself is no longer exposed to that failure at all: it is one
# >>> substitution now, and the must_not above keeps it that way.)
# >>> Derived, not hard-coded, for the reason spelled out under _stale_px below.
_stale_row_pitch = "|".join(
    f"{v / 10:.1f}" for v in range(90, 171) if abs(v / 10 - g.LED_ROW_PITCH) > 1e-9
)
for d in ("packages/hw/crescent.yaml", "HARDWARE.md", "3d-print/README.md"):
    must_not(d, rf"\b(?:{_stale_row_pitch})\s*(?:mm\s*)?(?:apart|, NOT)\b",
             f"a row pitch other than {g.LED_ROW_PITCH}")

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
PROSE = ("HARDWARE.md", "SOUNDMACHINE.md", "CLAUDE.md", "3d-print/README.md",
         "FUTURE-DEVELOPMENT.md")

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
# >>> THE CROWN BOARDS COME OFF THE SHARED LIST NOW, like the rear wall's. These
# >>> two rules used to name ENC_HOLE_P and TOF_HOLE_P -- and a rule that greps for
# >>> a deleted name passes silently forever, so they are pointed at the list the
# >>> bosses are actually built from.
draws("3d-print/gen_drawing.py", r"crown_boards\(\)",
      "the crown boards from the shared list")
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
                   ("plate_boards", g.plate_boards()),
                   ("crown_boards", g.crown_boards())):
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

# >>> THE FOUR STEMMA QT BREAKOUTS, ASSERTED AGAINST THEIR VENDOR BOARD FILES.
# >>> Three of these carried a made-up TWO-hole pitch for months -- 20.0, 20.0 and
# >>> 15.0, each marked "(?) MEASURE" and each wrong -- while the boards' own Eagle
# >>> files had said four holes on 0.100" corner insets all along. The matrix rule
# >>> below/above exists for exactly this failure mode; these are the same rule for
# >>> the sensors. Numbers read from the <element MOUNTINGHOLE_*> entries and the
# >>> layer-20 outline wires of the repos named in g.QT_PCB_SRC.
_QT_VENDOR = {
    # name: (outline w, outline h, holes in the BOARD frame, drill)
    "encoder": (25.4, 25.4,
                [(2.54, 2.54), (2.54, 22.86), (22.86, 2.54), (22.86, 22.86)], 2.5),
    "ToF":     (25.4, 17.78,
                [(2.54, 2.54), (2.54, 15.24), (22.86, 2.54), (22.86, 15.24)], 2.5),
    "lux":     (25.4, 17.78,
                [(2.54, 2.54), (2.54, 15.24), (22.86, 2.54), (22.86, 15.24)], 2.5),
    "RTC":     (25.4, 17.78,
                [(2.54, 15.24), (22.86, 15.24)], 3.0),
}
for _nm in _QT_VENDOR:
    if _nm not in g.QT_PCB_SRC:
        problems.append(
            f"enclosure_geom.py: QT_PCB_SRC has no source repo for '{_nm}'. Every "
            f"board whose geometry is asserted here must say where it came from.")

# The outline each board is modelled with, in whatever names that board uses.
for _nm, _got in (("encoder", (g.ENC_PCB, g.ENC_PCB)),
                  # the ToF is stored (short edge, long edge) because it is mounted
                  # longwise; the vendor outline is (long, short).
                  ("ToF", (g.TOF_PCB_D, g.TOF_PCB_W)),
                  ("lux", (g.LUX_PCB_W, g.LUX_PCB_H)),
                  ("RTC", (g.RTC_PCB_W, g.RTC_PCB_H))):
    _w, _h, _holes, _drill = _QT_VENDOR[_nm]
    if (round(_got[0], 2), round(_got[1], 2)) != (_w, _h):
        problems.append(
            f"enclosure_geom.py: the {_nm} board is modelled "
            f"{_got[0]} x {_got[1]}, but {g.QT_PCB_SRC[_nm]} gives {_w} x {_h}.")

# >>> AND THE OFFSETS THAT ACTUALLY DRIVE THE BOSSES, not just the outline. The
# >>> BH1750's guessed 15.0 pitch would have passed an outline-only check with a
# >>> corrected outline and still put all four bosses in the wrong place.
def _want_offsets(nm):
    _w, _h, _holes, _ = _QT_VENDOR[nm]
    return sorted((round(hx - _w / 2, 2), round(abs(hy - _h / 2), 2))
                  for hx, hy in _holes)


def _got_offsets(offs):
    return sorted((round(dx, 2), round(abs(dy), 2)) for dx, dy in offs)


_crown = {r[0]: r[5] for r in g.crown_boards()}
_rear = {r[0]: r[5] for r in g.rear_wall_boards()}
for _nm, _offs, _swap in (("encoder", _crown.get("encoder"), False),
                          # mounted longwise: its (dx, ddepth) is the vendor
                          # pattern's (dy, dx), so compare with the axes swapped.
                          ("ToF", _crown.get("ToF"), True),
                          ("lux", _rear.get("lux"), False)):
    if _offs is None:
        problems.append(f"enclosure_geom.py: no hole list found for the {_nm}.")
        continue
    _cmp = [(dz, dx) for dx, dz in _offs] if _swap else list(_offs)
    if _got_offsets(_cmp) != _want_offsets(_nm):
        problems.append(
            f"enclosure_geom.py: the {_nm}'s hole offsets are {_got_offsets(_cmp)}, "
            f"but {g.QT_PCB_SRC[_nm]} gives {_want_offsets(_nm)} (four Ø"
            f"{_QT_VENDOR[_nm][3]} holes, {g.QT_HOLE_INSET} in from every edge). "
            f"All three of these were once a single invented pitch.")

_r = _QT_VENDOR["RTC"]
if sorted(g.RTC_HOLES) != sorted(_r[2]) or g.RTC_HOLE_D != _r[3]:
    problems.append(
        f"enclosure_geom.py: RTC_HOLES = {g.RTC_HOLES} drill {g.RTC_HOLE_D}, but "
        f"'Adafruit DS3231 STEMMA QT.brd' declares {_r[2]} drill {_r[3]}. The "
        f"DS3231 populates only the TOP pair of the family grid.")
if g.QT_HOLE_INSET != 2.54 or g.QT_HOLE_D != 2.5:
    problems.append(
        f"enclosure_geom.py: QT_HOLE_INSET/QT_HOLE_D = {g.QT_HOLE_INSET}/"
        f"{g.QT_HOLE_D}; Adafruit's MOUNTINGHOLE_2.5_PLATED sits 2.54 (0.100\") in "
        f"from each edge and drills 2.5.")

# >>> THE CROWN BOARDS' BOSSES MUST NOT MERGE. This is checked on the built solid
# >>> in gen_dome.py too, but the SPACING is decided here -- TOF_X is derived from
# >>> BOSS_GAP_MIN -- so a stale derivation should be caught without a build. The
# >>> two boards' hole rows sit at identical depths, so x separation is all there
# >>> is and there is no saving diagonal.
_cb = [(nm, cx + dx, cz + dz)
       for nm, cx, cz, _w, _d, offs, _s in g.crown_boards() for dx, dz in offs]
_gap = min(((ax - bx) ** 2 + (az - bz) ** 2) ** 0.5 - g.BOSS_D
           for an, ax, az in _cb for bn, bx, bz in _cb if an != bn)
if _gap < g.BOSS_GAP_MIN - 1e-6:
    problems.append(
        f"enclosure_geom.py: the nearest encoder/ToF bosses leave {_gap:.2f} mm of "
        f"plastic, under BOSS_GAP_MIN = {g.BOSS_GAP_MIN}. TOF_X is supposed to be "
        f"derived from that gap -- see _resolve_tof_x(). The old 1.5 mm "
        f"BOARD-edge gap left 0.59 mm here, which prints as one blob.")
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

# >>> MEASURE-ME IS TIED TO THE (?) MARKERS, BOTH WAYS. That document is the one
# >>> the human acts on, and it had drifted furthest of anything in the repo: still
# >>> asking for five hole patterns Adafruit's board files had settled, for speaker
# >>> nubs confirmed on a print, and for MTX_SOCKET_H -- a measurement for the
# >>> press-in backpack scheme, which lost to the clips and was never built. Nobody
# >>> noticed because prose has no checks.
# >>> So: every constant still marked (?) in the source must be NAMED in
# >>> MEASURE-ME, and every constant MEASURE-ME names must still be marked (?).
# >>> The second direction is the one that catches stale asks.
import re as _re

_MM = ROOT / "3d-print" / "MEASURE-ME.md"
_mm_text = _MM.read_text()
_unknown = set()
for _fn in ("enclosure_geom.py", "gen_front_plate.py", "gen_dome.py",
            "gen_bottom_plate.py", "gen_led_carrier.py", "gen_knob.py"):
    _path = ROOT / "3d-print" / _fn
    if not _path.exists():
        continue
    for _line in _path.read_text().splitlines():
        _m = _re.match(r"^([A-Z][A-Z_0-9]*(?:\s*,\s*[A-Z][A-Z_0-9]*)*)\s*=.*\(\?\)",
                       _line)
        if _m:
            for _nm in _m.group(1).split(","):
                _unknown.add(_nm.strip())

_named = {_n for _n in _unknown if f"`{_n}`" in _mm_text}
_missing = sorted(_unknown - _named)
if _missing:
    problems.append(
        "MEASURE-ME.md does not mention " + ", ".join(_missing) +
        " -- still marked (?) in the source, so they are still guesses the "
        "human has to resolve, and the document is what they act on.")

# ...and the other way: anything MEASURE-ME asks for must still be unknown.
# >>> AN ASK IS A HEADING, NOT A MENTION. This matched every backticked constant
# >>> anywhere in the document, so simply REFERRING to one -- "the openings are the
# >>> body plus PANEL_FIT" -- registered as a demand to measure it, and the check
# >>> nagged about a value that was never in question. What makes something an ask
# >>> is that the document gives it its own section.
_asked = set()
for _h in _re.findall(r"^#+ .*$", _mm_text, _re.M):
    _asked |= set(_re.findall(r"`([A-Z][A-Z_0-9]*)`", _h))
# >>> THE EXEMPTION IS ONE SECTION, NOT "EVERYTHING AFTER THE HEADING". This read
# >>> _mm_text.split("## Settled")[-1], which swallows the rest of the file -- so a
# >>> stale ask appended at the END of the document was silently exempt, and the
# >>> break test that should have caught it passed. Cut at the next heading.
_settled_section = ""
if "## Settled" in _mm_text:
    _rest = _mm_text.split("## Settled", 1)[1]
    _nxt = _re.search(r"\n## ", _rest)
    _settled_section = _rest[:_nxt.start()] if _nxt else _rest
_stale = sorted(_n for _n in _asked - _unknown
                if f"`{_n}`" not in _settled_section)
if _stale:
    problems.append(
        "MEASURE-ME.md still asks for " + ", ".join(_stale) +
        " -- these are no longer marked (?) in the source. A list that asks for "
        "numbers already settled is how it came to ask for a measurement of a "
        "part that was never built.")

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
