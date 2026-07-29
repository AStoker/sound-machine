#!/usr/bin/env python3
"""DOME — PART 1. The shell: open front, open bottom, integral rear wall.

A "D" lying on its long flat side, extruded along the depth. It carries the joint
that the front module slides up into, the ledge and lugs the bottom plate screws
to, every rear-wall board and opening, and the crown controls.

    PRINT REAR WALL DOWN. That makes the rear wall the first layer -- a big flat
    face, and the one that carries the most features -- and every boss standing
    off it then grows straight up off the bed with no overhang at all. The side
    walls and the crown come out vertical.

>>> WHAT THAT ORIENTATION COSTS: anything projecting inward off a SIDE wall or
>>> off the CROWN is horizontal, i.e. an unsupported shelf. That is the four side
>>> lugs and the two crown board mounts. Every one of them gets a 45 deg gusset
>>> underneath -- see gusset(). Without them the slicer either bridges into space
>>> or fills the interior with support that has to be picked out of a shell you
>>> can barely reach into.

>>> NO SCREW ENTERS FROM OUTSIDE. Every boss here is BLIND: it stands proud of
>>> the INNER surface and its pilot stops short of the skin, so nothing shows on
>>> the outside of the machine. Screws go in from inside, towards the shell. The
>>> six that hold the bottom plate are the only fasteners you can see, and they
>>> are on the underside.

>>> EVERY BOARD GETS A FLAT. The crown is a cylinder and the walls curve above
>>> the springing line, so a PCB laid straight on either rocks and skews its
>>> connectors. Boards on curved surfaces sit in a shallow pocket milled into the
>>> INSIDE -- never the outside, which stays smooth. Depth is derived from the
>>> arch's own sagitta, see enclosure_geom.flat_depth().

    python3 gen_dome.py     ->  models/dome.stl
"""
import math
import os
import struct

from manifold3d import CrossSection, Manifold

from enclosure_geom import (
    ARCH_R, ARCH_RY, ARCH_Y, BARREL_D, BARREL_LAND_D, BARREL_NUT_D, BARREL_Y,
    BOSS_CHAMF, BOSS_D, BOSS_MIN_WALL, BOSS_PILOT_D, BOSS_SCREW, BP_T, D,
    ENC_FLAT_D, ENC_FLAT_W, ENC_HOLE_P, ENC_HOLE_AXIS, ENC_PCB, ENC_SHAFT_D, ENC_Y,
    FLEX_BOSS_D, FLEX_HOLE_D, FLEX_STANDOFF, FLEX_WALL_Y, H, IN_D, IN_W, INSERT_D,
    KNOB_BOSS_D, LIP_T, LIP_W, LP_D, LP_Y, LUG_H, LUG_L, LUG_W, MODEL_DIR,
    RIB_T, RIB_W, R_BOT, REVEAL, FP_CLR, FP_T, SCREWS, SEAT_W, SLOT_W, STANDOFF_H, SW_RIB,
    SW_D, SW_NUT_D, SW_WALL_X, SW_WALL_Y, VENT_RISE, TOF_FLAT_D, TOF_FLAT_W,
    TOF_HOLE_D, TOF_HOLE_P, TOF_HOLE_AXIS,
    TOF_PCB_D, TOF_PCB_W, TOF_X, TOF_Y, TOUCH_DEPTH, TOUCH_PAD_L, TOUCH_PAD_W,
    TOUCH_WALL, TOUCH_Y, VENT_HH, VENT_N, VENT_P, VENT_W, VENT_Y, W, WALL,
    flat_depth, flex_holes, rear_wall_boards, touch_x, vent_x,
    REAR_BOARD_SCREW, REAR_PILOT_D,
)

SEG = 128
BED = 220.0

# --- print parameters -------------------------------------------------------
SEAT_LEDGE_T = 2.0    # thickness of the bottom-plate seating ledge
GUSSET       = 45.0   # degrees; the support-free angle everything is built to
LUG_GUSSET   = 6.0    # how far a lug's gusset reaches down the wall
CROWN_FLAT_R = 3.0    # corner radius on a crown mounting flat
FLAT_MARGIN_LOCAL = 1.6   # extra depth beyond the computed sagitta
BOSS_OVERLAP = 1.0        # how far a crown boss reaches into the ceiling
RAMP_STEP    = 0.5        # step size on a 45 deg support ramp
RAMP_MIN     = 2.0        # least section a ramp step may be built with
TOF_STAND    = 2.0        # ToF board standoff -- short, to sit near the skin

_out = []


def say(s):
    _out.append(s)
    print(s)


# ---------------------------------------------------------------------------
# 2D helpers -- FRONT-view coordinates: x 0..W from the left, y 0..H measured UP
# ---------------------------------------------------------------------------
def poly(pts):
    return CrossSection([[(float(x), float(y)) for x, y in pts]])


def rect2(x0, y0, w, h):
    return poly([(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h)])


# >>> WHEN YOU SUBTRACT ONE OUTLINE FROM ANOTHER, GIVE THEM DIFFERENT BOTTOMS.
# >>> Both dropped to the same ybot means their flat bottom edges are COINCIDENT,
# >>> and the boolean produces zero-width slivers there. At full width that
# >>> passes; once a ramp step shrinks the annulus to ~2 mm it degenerates into
# >>> an invalid manifold (volume 0, infinite bbox) and takes the whole union
# >>> with it. YBOT_OUT / YBOT_IN keep the two edges apart.
YBOT_OUT = -10.0
YBOT_IN  = -14.0


def annulus(inset_a, inset_b):
    """The band of material between two insets, open at the bottom."""
    return d_outline(inset_a, ybot=YBOT_OUT) - d_outline(inset_b, ybot=YBOT_IN)


def loft(pts_a, za, pts_b, zb):
    """The straight-ruled solid between two CONVEX sections at two depths.

    >>> TRUE ANGLED GEOMETRY, NOT A STAIRCASE. Every ramp and every louvre in
    >>> this part was originally built as a stack of 12 thin slabs approximating
    >>> a slope. That is the slicer's job, not the model's: Orca resolves a real
    >>> 45 deg face to the nozzle and layer height far better than a 0.25 mm
    >>> staircase baked into the STL ever can, and the steps were actively
    >>> harmful -- they tripled the triangle count, they made the overhang audit
    >>> measure the wrong thing (a staircase has the same downward AREA as the
    >>> shelf it replaces), and every one of the three mesh failures in this file
    >>> came from stacked slabs sharing faces.
    >>>
    >>> For CONVEX sections the convex hull of the two boundaries IS the loft --
    >>> its lateral surface is exactly the straight rule between them. The D
    >>> outline is convex (flat bottom, rounded corners, straight flanks,
    >>> elliptical crown), and so is every rectangle here, so one hull_points call
    >>> gives geometry that is exact rather than approximated.
    """
    P = [(float(x), float(y), float(za)) for x, y in pts_a]
    P += [(float(x), float(y), float(zb)) for x, y in pts_b]
    return Manifold.hull_points(P)


def d_points(inset, ybot=None):
    """d_outline's vertices, for lofting between two insets."""
    return d_outline(inset, ybot).to_polygons()[0]


def d_outline(inset, ybot=None):
    """The 'D': flat bottom, straight flanks, flattened half-ellipse on top.

    `inset` shrinks it uniformly -- 0 is the outer skin, WALL the inner surface.
    `ybot` overrides the bottom edge, which is how the BOTTOM IS LEFT OPEN: the
    inner cutout is given a bottom below the part, so no floor is ever formed.
    """
    yb = inset if ybot is None else ybot
    rb = max(R_BOT - inset, 0.6)
    x0, x1 = inset, W - inset
    a, b = ARCH_R - inset, ARCH_RY - inset
    pts = [(x0 + rb, yb)]
    for i in range(9):                              # bottom-right corner
        t = -math.pi / 2 + (math.pi / 2) * i / 8
        pts.append((x1 - rb + rb * math.cos(t), yb + rb + rb * math.sin(t)))
    pts.append((x1, ARCH_Y))
    for i in range(1, SEG):                         # the arch
        t = math.pi * i / SEG
        pts.append((W / 2 + a * math.cos(t), ARCH_Y + b * math.sin(t)))
    pts.append((x0, ARCH_Y))
    for i in range(9):                              # bottom-left corner
        t = math.pi + (math.pi / 2) * i / 8
        pts.append((x0 + rb + rb * math.cos(t), yb + rb + rb * math.sin(t)))
    return poly(pts)


def slab(cs, z0, z1):
    return cs.extrude(z1 - z0).translate((0, 0, z0))


def cyl(cx, cy, z0, z1, d, segs=SEG):
    return Manifold.cylinder(z1 - z0, d / 2, d / 2, segs).translate((cx, cy, z0))


def ycyl(cx, cz, y0, y1, d, segs=SEG):
    """A cylinder on the VERTICAL (y) axis -- the axis every crown feature uses.

    >>> EVERY HOLE THROUGH THE CROWN IS ROUND, AND THIS IS WHY IT HAS A HELPER.
    >>> slab() extrudes an (x,y) section along z, so anything built with it and
    >>> aimed at the crown comes out SQUARE. The shaft bore, the ToF pinhole and
    >>> the knob's seating pad were all boxes for exactly that reason.
    >>> manifold3d's rotate() is applied about the ORIGIN, so the order matters:
    >>> rotate FIRST (which maps +z to +y), translate SECOND. Doing it the other
    >>> way swings the feature somewhere else entirely -- that is what produced
    >>> the 219-body mess earlier.
    """
    return (Manifold.cylinder(y1 - y0, d / 2, d / 2, segs)
            .rotate((-90, 0, 0))
            .translate((cx, y0, cz)))


def crown_inner_y(x):
    """Height of the crown's INNER surface at this x -- what a board mounted up
    there actually lands on."""
    a, b = ARCH_R - WALL, ARCH_RY - WALL
    return ARCH_Y + b * math.sqrt(max(1.0 - ((x - W / 2) / a) ** 2, 0.0))


def union(parts, what="solid"):
    """Union, with every part checked first.

    >>> AN INVALID MANIFOLD IN A UNION DESTROYS THE WHOLE RESULT. manifold3d
    >>> signals failure by returning an object with volume 0 and an INFINITE
    >>> bounding box, and unioning one of those yields nothing at all -- the dome
    >>> silently became a 0-triangle STL. It is worth failing loudly here rather
    >>> than exporting an empty file that looks like a modelling mistake.
    """
    good = []
    for i, p in enumerate(parts):
        bb = p.bounding_box()
        if p.volume() <= 0.0 or not all(abs(v) < 1e6 for v in bb):
            raise ValueError(f"{what}[{i}] is not a valid solid: "
                             f"volume={p.volume()} bbox={bb}")
        good.append(p)
    if not good:
        return Manifold()
    out = good[0]
    for p in good[1:]:
        out = out + p
    return out


def boss(cx, cy, h, pilot_z, d=BOSS_D, pilot=BOSS_PILOT_D, face=None):
    """A blind mounting boss standing INWARD off the rear wall.

    >>> IT GROWS IN -Z, TOWARDS THE FRONT. The first version grew in +z, i.e.
    >>> straight into the rear wall's own material. The board would have had
    >>> nothing to sit on, and -- the part that actually failed -- the pilot ended
    >>> up drilled entirely inside solid plastic, a sealed void with no opening.
    >>> Eleven of those turned up as eleven extra "connected bodies" with NEGATIVE
    >>> volume, which is how the mesh check caught it.

    Returns (solid, pilot_cut) so the pilot is always cut LAST, after every
    additive step, and cannot be filled back in.
    """
    face = (D - WALL) if face is None else face
    tip = face - h                                   # the free end, forward
    body = cyl(cx, cy, tip, face, d)
    # chamfered lead-in on the FREE end, so a board drops on without catching
    body = body + Manifold.cylinder(BOSS_CHAMF, d / 2 - BOSS_CHAMF, d / 2, SEG) \
        .translate((cx, cy, tip))
    return body, cyl(cx, cy, tip - 1.0, tip + pilot_z, pilot)


# ---------------------------------------------------------------------------
# BODY
# ---------------------------------------------------------------------------
# z is DEPTH: 0 at the front face, D at the back of the rear wall.
body = slab(d_outline(0.0), 0.0, D)

# Hollow it. The cutout's bottom is dropped below the part, so the shell is OPEN
# at the bottom -- that is how the plate and the front module get in.
CAV_Z0, CAV_Z1 = LIP_T, D - WALL
body = body - slab(d_outline(WALL, ybot=-10.0), CAV_Z0, CAV_Z1)
# ...and open the front, through the lip's aperture.
# >>> THE LIP'S REAR FACE IS THE ONE OVERHANG THAT CANNOT BE RAMPED, and it is
# >>> worth being explicit about why, because it looks like exactly the same
# >>> problem as the retaining rib and it is not.
# >>>
# >>> Printed rear-wall-down it is a LIP_W-wide (5 mm) shelf projecting inward
# >>> over the groove with nothing below it -- geometrically the same fault the
# >>> rib had. But the rib is BEHIND the module and the lip is IN FRONT of it. A
# >>> 45 deg ramp on the lip's rear face would have to occupy z = LIP_T..LIP_T+5,
# >>> and the module lives at z = 2.5..6.5 and has to SLIDE UP through that band
# >>> with its rim at inset REVEAL. Any ramp there reaches inside REVEAL long
# >>> before it has run its 5 mm, so it fouls the rim -- the identical mistake the
# >>> seating ledge made when it ran across the groove.
# >>>
# >>> So it stays square, and the audit reports it separately rather than
# >>> pretending it is not there. It is the LAST 2 mm of the print, it is a closed
# >>> ring so the droop is uniform, and the face it droops onto is the BACK of the
# >>> bezel -- hidden by the module that seats against it. Print it with support
# >>> on the front face if the finish matters; nothing structural depends on it.
body = body - slab(d_outline(WALL + LIP_W, ybot=-10.0), -1.0, CAV_Z0)

# --- retaining rib ----------------------------------------------------------
# Grips the outer RIB_W of the front module's BACK face, along both flanks and
# the arc. NOT across the bottom: that is the open end the module slides up
# through, and every point of the flanks has to travel past this rib on the way.
RIB_Z0 = LIP_T + SLOT_W
rib = annulus(WALL, WALL + RIB_W)
rib = rib - rect2(0.0, -10.0, W, BP_T + SEAT_LEDGE_T + 10.0)
body = body + slab(rib, RIB_Z0, RIB_Z0 + RIB_T)

# >>> AND A RAMP BEHIND IT, BECAUSE OF THE PRINT ORIENTATION. Printed rear-wall
# >>> down, the build direction runs from z=D towards z=0 -- so a face pointing
# >>> at +z is a face pointing at the BED, and it needs something underneath it.
# >>> The rib's rear face (z = RIB_Z0+RIB_T) is exactly that: a RIB_W-wide shelf
# >>> projecting into open cavity with nothing below it, all the way round both
# >>> flanks and the arch.
# >>>
# >>> So the rib now GROWS IN gradually from further back: zero projection at
# >>> RIB_W behind it, full projection where the rib proper starts. That is a 45
# >>> deg underside, which prints unsupported.
# >>>
# >>> RAMP BACKWARDS, NEVER FORWARDS. The rib's FRONT face is what grips the
# >>> module, and everything in front of it at z = LIP_T..RIB_Z0 is the groove the
# >>> module slides up through. A ramp on that side would both spoil the grip and
# >>> stick into the one path the joint exists for -- the same mistake the seating
# >>> ledge made. Behind the rib there is nothing but cavity, so it is free.
# >>> ONE BLOCK, THEN ONE LOFTED VOID -- a real 45 deg cone, not twelve steps.
# >>> The void's near cap is the rib's own inner boundary (so it removes nothing
# >>> where the rib proper is) and its far cap is the cavity wall (so by the end
# >>> of the ramp the whole band is gone). Between them the hull's lateral
# >>> surface is the straight rule joining the two, which is the ramp.
_ramp_z0 = RIB_Z0 + RIB_T
_ramp_z1 = _ramp_z0 + RIB_W
# the block: full-width, from inside the rib out to the ramp's far end
_blk = annulus(WALL, WALL + RIB_W) - rect2(0.0, -10.0, W, BP_T + 10.0)
body = body + slab(_blk, RIB_Z0, _ramp_z1)
# >>> THE VOID STOPS ABOVE THE SEATING LEDGE. It reaches out to inset WALL, which
# >>> is exactly where the ledge is, so carving it full height would eat the ledge
# >>> away at the very place the bottom plate lands on it.
_ramp_void = loft(d_points(WALL + RIB_W), _ramp_z0, d_points(WALL), _ramp_z1)
_ramp_void = _ramp_void - slab(rect2(0.0, -20.0, W, BP_T + SEAT_LEDGE_T + 20.0),
                               _ramp_z0 - 1.0, _ramp_z1 + 1.0)
body = body - _ramp_void

# --- bottom-plate seating ledge ---------------------------------------------
# A continuous shelf all round. The plate is WIDER than the gap between the
# ledges, so it cannot pass -- it comes up from below, stops here, and the six
# screws pull it up against the lugs.
# >>> IT STARTS BEHIND THE GROOVE, NOT AT THE FRONT FACE. The front module
# >>> slides UP through the groove at z = LIP_T..LIP_T+SLOT_W, and its edge sits
# >>> REVEAL (3.6) in from the skin. The ledge reaches WALL+SEAT_W (5.5) in --
# >>> so run across the groove it stuck 1.9 mm into the module's path and the
# >>> module simply could not go in. It was blocking the one assembly move the
# >>> whole joint exists for.
# >>> Nothing is lost: the plate's FRONT edge was never carried by the ledge. It
# >>> is captured between the seating ledge behind it and the front module's own
# >>> bottom edge in front -- which is exactly what the notes always said.
LEDGE_Z0 = LIP_T + SLOT_W
ledge = annulus(WALL, WALL + SEAT_W)
ledge = ledge ^ rect2(0.0, BP_T, W, SEAT_LEDGE_T)
body = body + slab(ledge, LEDGE_Z0, CAV_Z1)

adds, cuts, pilots = [], [], []

# --- bottom-plate fixing tabs ----------------------------------------------
# >>> A CONTINUOUS LIP PLUS LOCAL TABS -- NOT SIX FREE-STANDING BLOCKS. The
# >>> earlier version built each lug as a rectangle hung off the wall with a
# >>> stepped ramp under it, and the result looked exactly like what it was:
# >>> weird blocks cluttering the bottom of the shell, doing nothing a lip could
# >>> not do better.
# >>>
# >>> The LIP is already there -- the continuous seating ledge the plate lands
# >>> against, running the full perimeter. A tab is simply that lip made locally
# >>> TALLER where a screw goes, so the screw has depth to bite into. The plate
# >>> comes up from below and the screw runs UP through it into the tab.
# >>>
# >>> It also prints better. The lip runs the whole depth of the shell, so in the
# >>> rear-wall-down orientation it is a continuous vertical fin with no
# >>> unsupported face anywhere. A tab growing out of it needs only a 45 deg ramp
# >>> at its bed-facing end, and the rear tabs need nothing at all -- they
# >>> project forward in z, which is straight up off the bed.
# >>> SIX DISTINCT TABS: two on each side wall, two on the rear. Each one is a
# >>> plain block on the surface it grows from -- nothing clever.
# >>>
# >>> THE RAMPS ARE GONE, AND THAT IS WHAT THE "NOTCH" WAS. Each side tab had a
# >>> 45 deg support ramp trailing it toward the bed, LUG_L deep. But the two
# >>> side tabs sit only 4 mm apart (spans 29..43 and 47..61), and a 12 mm ramp
# >>> off the first ran straight through the second. The two merged into one long
# >>> blob with a step in it -- which is exactly what a notch looks like. There is
# >>> no room for both: 61.5 - 29 = 32.5 mm of usable depth against 14 + 12 + 14
# >>> = 40 mm of tab-plus-ramp.
# >>>
# >>> So the ramps go and these six overhang. That is the right trade here: they
# >>> are small, they sit at the OPEN BOTTOM of the shell, and support under them
# >>> is the most accessible support anywhere in the part -- you can reach every
# >>> one with a finger. A merged blob you cannot fix; two minutes with pliers you
# >>> can.
# >>> ONE RAIL PER SIDE, NOT TWO TABS -- and this is a straight reversal of the
# >>> last change. Six distinct tabs sounded right, and printed rear-wall-down it
# >>> is wrong: two separate shelves on the same wall leave an ISLAND ofvoid between
# >>> them that the slicer has to support off nothing, in a pocket you cannot
# >>> reach into once the shell is up.
# >>>
# >>> A single rail spanning both screws, running back to meet the REAR WALL, is
# >>> strictly better: in this orientation it is a continuous vertical fin growing
# >>> off the bed, so it has NO overhang anywhere and needs no support at all. It
# >>> is also stiffer, and it still gives exactly the two screw points per side.
# >>> The rear pair stay as separate blocks -- they project forward off the rear
# >>> wall, which is straight up off the bed.
tab_holes = []
_side_depths = sorted({sd for sx, sd in SCREWS
                       if abs(sd - (D - WALL - LUG_L / 2)) >= 0.1})
for sx, sd in SCREWS:
    rear = abs(sd - (D - WALL - LUG_L / 2)) < 0.1
    if rear:
        adds.append(slab(rect2(sx - LUG_W / 2, BP_T, LUG_W, LUG_H),
                         D - WALL - LUG_L, D - WALL))
    tab_holes.append((sx, sd))
    pilots.append(ycyl(sx, sd, BP_T - 1.0, BP_T + LUG_H - BOSS_MIN_WALL,
                       INSERT_D))

RAIL_Z0 = min(_side_depths) - LUG_W / 2
for _left in (True, False):
    _x0 = 0.0 if _left else W - (WALL + LUG_L)
    _prof = rect2(_x0, BP_T, WALL + LUG_L, LUG_H) ^ d_outline(0.0)
    adds.append(slab(_prof, RAIL_Z0, D - WALL))

# --- rear wall: openings ----------------------------------------------------
RW0, RW1 = D - WALL, D
cuts.append(cyl(W / 2, BARREL_Y, RW0 - 1, RW1 + 1, BARREL_D))
cuts.append(cyl(W / 2, LP_Y, RW0 - 1, RW1 + 1, LP_D))
# >>> LOUVRED, NOT DRILLED STRAIGHT THROUGH. Each slot RISES by VENT_RISE across
# >>> the wall's thickness -- outer opening low, inner opening high. A level line
# >>> of sight therefore enters the outer opening and lands on the slot's own top
# >>> face; you can only see in from below the machine. Straight-through slots
# >>> this size are windows onto the UPS.
# >>> A SHEARED BOX, NOT A STAIRCASE. This was 12 stacked slabs stepping the
# >>> section's y as z advanced -- the same shape as a tilt, but delivered to the
# >>> slicer as 12 little terraces per slot, 36 per stack. A louvre is a plain
# >>> rectangular slot translated as it crosses the wall, so it is the hull of its
# >>> two end rectangles: two convex sections, straight rule between them, exact.
# >>> The slot's own axis is not 45 deg and not the wall normal -- it rises
# >>> VENT_RISE across (WALL + 1) -- so both ends are computed from that one
# >>> parameterisation and extrapolated past each face to guarantee a clean cut.
def _vent_f(f, vy):
    """(z, y-centre) at fraction f along a louvre's own axis. f=0 inner."""
    return RW0 - 1.0 + (WALL + 1.0) * f, vy + VENT_RISE * (1.0 - f)


for vx in vent_x():
    for i in range(VENT_N):
        vy = VENT_Y + i * VENT_P
        P = []
        for f in (-0.25, 1.25):                  # past both faces, so it cuts
            z, yc = _vent_f(f, vy)
            P += [(x, y, z) for x in (vx - VENT_W / 2, vx + VENT_W / 2)
                  for y in (yc - VENT_HH, yc + VENT_HH)]
        cuts.append(Manifold.hull_points(P))
# >>> THE POWER SWITCH -- resolved to rear wall, low and left. It was an open
# >>> item from the original layout. This band was empty: below the Flex (which
# >>> starts at y=16) and above the floor, on the opposite side from the UPS.
# >>> ROUND. It is a panel-mount PUSH BUTTON, not a rocker: a rectangular cutout
# >>> would leave four gaps around a circular bezel and give its nut nothing flat
# >>> and concentric to pull against.
cuts.append(cyl(SW_WALL_X, SW_WALL_Y, RW0 - 1, RW1 + 1, SW_D))
_sw_land, _ = boss(SW_WALL_X, SW_WALL_Y, SW_RIB, 0.0, d=SW_NUT_D + 2 * SW_RIB)
adds.append(_sw_land - cyl(SW_WALL_X, SW_WALL_Y, RW0 - 2, RW1 + 1, SW_D))

# --- rear wall: a flat land for the barrel jack's nut ------------------------
# The jack is a panel-mount part; its nut has to pull up against a plane. The
# rear wall IS flat, so the land is just a raised pad giving the nut room to turn
# clear of the vents and the lux pipe.
_land, _ = boss(W / 2, BARREL_Y, 1.2, 0.0, d=BARREL_LAND_D)
adds.append(_land - cyl(W / 2, BARREL_Y, RW0 - 2, RW1 + 1, BARREL_D))

# --- rear wall: board bosses ------------------------------------------------
# All standing forward in +z off the inside of the rear wall -- straight up off
# the bed in the print orientation, so none of these need a gusset.
board_bosses = []
for hx, hy in flex_holes():
    b, p = boss(hx, hy, FLEX_STANDOFF + 2.0, FLEX_STANDOFF + 1.0,
                d=FLEX_BOSS_D)
    adds.append(b)
    pilots.append(p)
    board_bosses.append(("Flex", hx, hy))
# >>> ONE BOSS PER ACTUAL HOLE. This used to take a single pitch and build a
# >>> four-boss square from it, which is only right for a board with four
# >>> symmetric holes. The DS3231 has two, on one horizontal line, so two of its
# >>> bosses were standing on bare PCB -- they would have held the board off its
# >>> other two and rocked it. The UPS has four but on a 46 x 86 pattern that no
# >>> single pitch describes either.
for nm, cx, cy, bw, bh, offs in rear_wall_boards():
    if not offs:
        continue
    _scr = REAR_BOARD_SCREW.get(nm, BOSS_SCREW)
    _pil = REAR_PILOT_D.get(_scr, BOSS_PILOT_D)
    for dx, dy in offs:
        hx, hy = cx + dx, cy + dy
        b, p = boss(hx, hy, STANDOFF_H + 2.0, STANDOFF_H + 1.0, pilot=_pil)
        adds.append(b)
        pilots.append(p)
        board_bosses.append((nm, hx, hy))

# --- the crown --------------------------------------------------------------
# The knob's seating pad is the ONE external feature, and it is a pad, not a
# fastener: a flat milled into the crown for the pebble to sit square on.
def crown_pt(depth):
    """Where the crown's apex is, at a given depth from the front face."""
    return W / 2, H, depth


# The shaft bore and the knob boss are on the apex; the encoder board hangs
# under it inside. Work in the (x, depth) plane at the top of the arch.
KNOB_Z = ENC_Y
# >>> ALL THREE OF THESE ARE ROUND, and all three used to be square. They were
# >>> built with slab(), which extrudes an (x,y) section along z -- perfectly
# >>> good for the rear wall, and wrong for anything aimed at the crown, where
# >>> the axis is VERTICAL. A round shaft in a square bore rattles, a square
# >>> pinhole vignettes the ToF's cone, and a square pad under a round pebble is
# >>> just visible. ycyl() puts them on the y axis where they belong.
_pad_depth = flat_depth(KNOB_BOSS_D)
# the knob's seating pad: a shallow ROUND pocket in the outer skin
cuts.append(ycyl(W / 2, KNOB_Z, H - _pad_depth, H + 1.0, KNOB_BOSS_D))
# the encoder shaft, straight down through the crown
cuts.append(ycyl(W / 2, KNOB_Z, H - 25.0, H + 1.0, ENC_SHAFT_D))
# the ToF pinhole
cuts.append(ycyl(TOF_X, TOF_Y, H - 25.0, H + 1.0, TOF_HOLE_D, segs=48))

# --- touch pads: local wall thinning ----------------------------------------
# Copper strips bond to the INSIDE of each shoulder; thinning the wall behind
# them raises sensitivity. The crown is a cylinder, so a flat strip wraps onto it
# without distortion as long as its long axis runs front-to-back.
# >>> A POCKET IN THE INNER FACE, NOT A HOLE THROUGH THE CROWN. The first
# >>> version cut the full wall thickness and put two 22 mm windows in the top of
# >>> the machine. The copper tape bonds to the INSIDE; all it needs is less
# >>> plastic between it and your finger. Removing the annulus between the inner
# >>> surface and d_outline(TOUCH_WALL) thins the wall from WALL to TOUCH_WALL
# >>> and leaves the outer skin completely untouched.
_thin = d_outline(TOUCH_WALL, ybot=YBOT_OUT) - d_outline(WALL, ybot=YBOT_IN)
for tx in touch_x():
    _fp = rect2(tx - TOUCH_PAD_W, TOUCH_Y - TOUCH_PAD_W,
                2 * TOUCH_PAD_W, 2 * TOUCH_PAD_W)
    cuts.append(slab(_thin ^ _fp,
                     TOUCH_DEPTH - TOUCH_PAD_L / 2,
                     TOUCH_DEPTH + TOUCH_PAD_L / 2))

# --- crown board mounts -----------------------------------------------------
# >>> BOSSES GO IN BEFORE THE FLAT IS CUT, NOT AFTER. A boss added afterwards can
# >>> only ever TOUCH the new ceiling plane -- coplanar faces, which manifold
# >>> reports as separate bodies, and the ToF's pair ended up floating in mid-air.
# >>> Built first and extended UP INTO the wall, the boss is fused with the shell
# >>> before anything is removed; the flat then trims boss and ceiling together
# >>> out of one solid, and they cannot come apart.
def crown_flat_cut(cx, cz, fw, fd):
    """Mill a flat into the INSIDE of the crown. Confined to the cavity so the
    outer skin is never touched. Returns (cut, flat_y)."""
    dx = abs(cx - W / 2) + fw / 2
    a, b = ARCH_R - WALL, ARCH_RY - WALL
    y_low = ARCH_Y + b * math.sqrt(max(1.0 - (dx / a) ** 2, 0.0))
    y_flat = y_low - FLAT_MARGIN_LOCAL
    box = slab(rect2(cx - fw / 2, y_flat, fw, H + 2 - y_flat),
               cz - fd / 2, cz + fd / 2)
    return box ^ slab(d_outline(WALL, ybot=YBOT_OUT), CAV_Z0, CAV_Z1), y_flat


def crown_boss(cx, cz, tip_y, top_y):
    """A boss hanging off the crown. Reaches UP into the wall so it fuses."""
    return (ycyl(cx, cz, tip_y, top_y, BOSS_D),
            ycyl(cx, cz, tip_y - 1.0, tip_y + (top_y - tip_y) - BOSS_MIN_WALL,
                 BOSS_PILOT_D, segs=48))


def crown_boss_ramp(cx, cz, tip_y, ceil_y, step=0.5):
    """A 45 deg buttress on the REAR side of a crown boss.

    >>> THESE ARE THE WORST OVERHANGS IN THE PART, AND THE LEAST REACHABLE. A
    >>> crown boss is a post hanging off the ceiling, and printed rear-wall-down
    >>> the build direction is horizontal to it -- so the post is printed lying on
    >>> its side, and its whole rear half hangs over open cavity at the very top
    >>> of the shell. Support there is a tower rising the entire depth of the part,
    >>> inside a closed dome, which you then cannot get a hand in to remove.
    >>>
    >>> The buttress fills the wedge between the ceiling and the boss's rear face:
    >>> nothing at STANDOFF_H behind the boss, growing to the full drop where the
    >>> boss starts. Every added layer then lands on the one before it.
    >>>
    >>> IT ONLY GOES ON THE REAR SIDE. The front face of the boss (smaller z) is
    >>> printed LAST -- it faces away from the bed and is self-supporting. A
    >>> buttress there would be dead plastic in the board's way.
    >>>
    >>> A SINGLE LOFTED WEDGE. This was a block plus a staircase of voids, which
    >>> put every step's near face on the boss's rear tangent plane and produced
    >>> degenerate faces at z=23, 33 and 43 -- the three crown bosses -- and
    >>> stopped the STL being watertight while manifold still reported one clean
    >>> solid. As a hull of three rectangles it is one convex solid with a real
    >>> 45 deg underside and nothing to go wrong.

    Returns the wedge, or None where there is no drop to buttress.
    """
    drop = ceil_y - tip_y
    if drop <= 0.05:
        return None
    z0 = cz + BOSS_D / 2
    # >>> NARROWER THAN THE BOSS, DELIBERATELY. At exactly BOSS_D the buttress's
    # >>> two side planes are TANGENT to the Ø6 boss cylinder -- they touch it
    # >>> along a line instead of cutting through it -- and a tangency is a sliver
    # >>> factory: 532 zero-area triangles and 272 non-manifold edges, every one of
    # >>> them within a millimetre of an encoder boss. manifold reported a single
    # >>> valid solid throughout; it was only the exported surface that was broken.
    # >>> Pulled in 1.2 mm, the planes cut the cylinder transversally and the
    # >>> intersection is an honest curve.
    RW = BOSS_D - 1.2
    # >>> AND ITS UNDERSIDE STOPS SHORT OF THE BOSS TIP. Run down to tip_y exactly
    # >>> and the buttress's bottom face is COPLANAR with the boss's flat tip cap;
    # >>> the cap's rim circle and the block's straight edge then have to be
    # >>> triangulated together in one plane, and every one of the 298 remaining
    # >>> zero-area faces was there -- all at y=149.8168 and 149.1754, the two
    # >>> tip planes, on the rim circles. 0.2 mm of daylight removes the shared
    # >>> plane; the boss's last 0.2 mm of rear face is a trivial overhang.
    TIP_GAP = 0.2
    x0, x1 = cx - RW / 2, cx + RW / 2
    y_bot, y_top = tip_y + TIP_GAP, ceil_y + 2.0
    # full height from the boss centre to its rear tangent, then a true 45 deg
    # taper back up to the ceiling over `drop`.
    P = [(x, y, z) for z in (cz, z0) for x in (x0, x1) for y in (y_bot, y_top)]
    P += [(x, y, z0 + drop) for x in (x0, x1) for y in (ceil_y, y_top)]
    return Manifold.hull_points(P)


crown_mounts = []

# >>> NEITHER CROWN BOARD GETS A MILLED FLAT, AND THAT IS A DELIBERATE RETREAT.
# >>> A flat is a LENS -- the sliver between a plane and the curved inner surface
# >>> -- and it has a knife edge wherever the two meet. Cutting one severed its
# >>> own bosses (they reach up through it), and every attempt to fix that by
# >>> trimming the cut around them left coincident or near-tangent faces: two
# >>> connected bodies, then a non-watertight mesh that three parameter sweeps
# >>> could not clear.
# >>>
# >>> It was not buying anything. Across the encoder's 20 mm hole pitch the crown
# >>> falls 0.367 mm, so an unflattened board tilts 1.05 deg -- which moves the
# >>> shaft 0.28 mm over its 15 mm bore against 0.50 mm of radial clearance. And
# >>> the KNOB does not care either way: it seats on its own round pocket milled
# >>> into the OUTER skin, which is what keeps the visible part square.
# >>>
# >>> So both boards simply follow the arch. Each boss tip sits the same short
# >>> standoff below its OWN local ceiling, so the board tilts to match the crown
# >>> and sits as flush as it can -- which is what was wanted for the ToF anyway.
# >>> EACH BOARD'S HOLE PAIR RUNS ON ITS OWN AXIS. The ToF is mounted LONGWISE
# >>> front-to-back so its narrow edge clears the encoder -- so its holes are
# >>> separated along the DEPTH. Treating that pitch as an x separation put one
# >>> ToF boss 2.9 mm INSIDE an encoder boss, and put both of them outside the
# >>> ToF board's own 17.8 mm width. A hole pitch wider than its own board is
# >>> impossible; that was the tell, and the axis was the cause.
_crown_bosses = []
for _nm, _cx, _cz, _hp, _axis, _stand in (
        ("encoder", W / 2, ENC_Y, ENC_HOLE_P, ENC_HOLE_AXIS, STANDOFF_H),
        ("ToF", TOF_X, TOF_Y, TOF_HOLE_P, TOF_HOLE_AXIS, TOF_STAND)):
    for _s in (-1, 1):
        _bx = _cx + (_s * _hp / 2 if _axis == "x" else 0.0)
        _bz = _cz + (_s * _hp / 2 if _axis == "depth" else 0.0)
        _ceil = crown_inner_y(_bx)
        _b, _p = crown_boss(_bx, _bz, _ceil - _stand, _ceil + 1.2)
        adds.append(_b)
        _rblk = crown_boss_ramp(_bx, _bz, _ceil - _stand, _ceil)
        if _rblk is not None:
            adds.append(_rblk)
        pilots.append(_p)
        _crown_bosses.append((_nm, _bx, _bz))
    crown_mounts.append((_nm, _cx, _cz, crown_inner_y(_cx) - _stand))

body = body + union(adds, 'adds')
body = body - union(cuts, 'cuts')
# Crown bosses last, so the flats they hang from already exist.
body = body - union(pilots, 'pilots')

# --- containment guard ------------------------------------------------------
# >>> NOTHING MAY LEAVE THE ENVELOPE. The front module has had this since the
# >>> day a boss hung off its edge; the dome needed it for the same reason and
# >>> did not have it. Intersecting with the outer profile makes escape
# >>> impossible, and the trimmed volume is reported so a feature cannot be
# >>> quietly amputated either.
_before = body.volume()
body = body ^ slab(d_outline(0.0), 0.0, D)
_trimmed = _before - body.volume()

# ---------------------------------------------------------------------------
# EXPORT
# ---------------------------------------------------------------------------
def write_stl(solid, name):
    m = solid.to_mesh()
    V, F = m.vert_properties[:, :3], m.tri_verts
    with open(os.path.join(MODEL_DIR, name), "wb") as f:
        f.write(b"\0" * 80)
        f.write(struct.pack("<I", len(F)))
        for a, b_, c in F:
            p, q, r = V[a], V[b_], V[c]
            u, v = q - p, r - p
            nx = u[1] * v[2] - u[2] * v[1]
            ny = u[2] * v[0] - u[0] * v[2]
            nz = u[0] * v[1] - u[1] * v[0]
            ln = (nx * nx + ny * ny + nz * nz) ** 0.5 or 1.0
            f.write(struct.pack("<3f", nx / ln, ny / ln, nz / ln))
            for w in (p, q, r):
                f.write(struct.pack("<3f", *[float(t) for t in w]))
            f.write(b"\0\0")
    return len(F)


nf = write_stl(body, "dome.stl")
bb = body.bounding_box()

say(f"wrote models/dome.stl   {nf} triangles")
say(f"bbox        {bb[3]-bb[0]:.2f} x {bb[4]-bb[1]:.2f} x {bb[5]-bb[2]:.2f} mm")
say(f"shell       {W} x {D} x {H:.1f}, wall {WALL}; interior {IN_W} x {IN_D}")
say(f"joint       lip {LIP_W}x{LIP_T} | groove {SLOT_W:.1f} | rib {RIB_W}x{RIB_T}")
say(f"ledge       {SEAT_W} continuous, top of the plate at y={BP_T}")
say(f"lugs        {len(SCREWS)} x {LUG_L}x{LUG_W}x{LUG_H}, "
    f"{chr(216)}{INSERT_D} blind for M3 heat-set")
say(f"rear wall   barrel {chr(216)}{BARREL_D} on a {chr(216)}{BARREL_LAND_D} land | "
    f"lux {chr(216)}{LP_D} | {len(vent_x())*VENT_N} louvres "
    f"{VENT_W}x{2*VENT_HH} | "
    f"switch {chr(216)}{SW_D} @ ({SW_WALL_X},{SW_WALL_Y})")
say(f"bosses      {len(board_bosses)} board bosses, all blind; "
    + ", ".join(f"{_n} M{REAR_BOARD_SCREW.get(_n, BOSS_SCREW)}"
                for _n in dict.fromkeys(n for n, _, _ in board_bosses)))
say("")

bad = []


def chk(name, v, lo=0.0):
    ok = v >= lo - 1e-6
    say(f"  {'ok  ' if ok else 'FAIL'} {v:8.2f}   {name}")
    if not ok:
        bad.append(name)


say("clearances")
chk("groove takes the module plus cloth both sides", SLOT_W - 4.0 - 2 * 0.6)
chk("rib clears the module's back face", RIB_T)
chk("ledge is under the lugs, not level with them", LUG_H - SEAT_LEDGE_T)
chk("insert hole stops short of the lug top", LUG_H - BOSS_MIN_WALL - 3.0)
chk("switch is below the Flex", FLEX_WALL_Y - (SW_WALL_Y + SW_D / 2))
chk("switch is above the floor", (SW_WALL_Y - SW_D / 2) - BP_T)
chk("barrel land clears the nut", BARREL_LAND_D - BARREL_NUT_D)
chk("touch pad thinning leaves wall", TOUCH_WALL)
chk("nothing trimmed by the containment guard", 0.01 - _trimmed)
chk("bbox depth == the design depth", 0.01 - abs((bb[5] - bb[2]) - D))
chk("bbox width == the design width", 0.01 - abs((bb[3] - bb[0]) - W))
chk("fits the bed (x)", BED - (bb[3] - bb[0]))
chk("fits the bed (y)", BED - (bb[4] - bb[1]))
chk("fits the bed (z, printed rear-wall-down)", BED - (bb[5] - bb[2]))

# every rear-wall boss must sit on the wall, not in an opening
# >>> AS RECTANGLES. The louvres used to be modelled here as CIRCLES of radius
# >>> max(VENT_W, VENT_HH)/2 -- fine while a slot was 18 wide, absurd once one is
# >>> 72: a Ø72 disc centred on the stack swallows most of the upper wall and
# >>> reported the LUX bosses, 8 mm away and perfectly clear, as 28 mm inside a
# >>> vent. A slot is 72 x 2, and approximating it by its longest dimension in
# >>> BOTH axes is a 36x overstatement of its height.
_open = [("barrel", W / 2 - BARREL_D / 2, W / 2 + BARREL_D / 2,
          BARREL_Y - BARREL_D / 2, BARREL_Y + BARREL_D / 2),
         ("lux", W / 2 - LP_D / 2, W / 2 + LP_D / 2, LP_Y - LP_D / 2, LP_Y + LP_D / 2),
         ("switch", SW_WALL_X - SW_D / 2, SW_WALL_X + SW_D / 2,
          SW_WALL_Y - SW_D / 2, SW_WALL_Y + SW_D / 2)]
for vx in vent_x():
    for i in range(VENT_N):
        _vy = VENT_Y + i * VENT_P
        _open.append((f"louvre {i}", vx - VENT_W / 2, vx + VENT_W / 2,
                      _vy - VENT_HH, _vy + VENT_HH))
_bw, _bwho = 1e9, ""
for nm, hx, hy in board_bosses:
    for onm, ox0, ox1, oy0, oy1 in _open:
        _g = max(ox0 - (hx + BOSS_D / 2), (hx - BOSS_D / 2) - ox1,
                 oy0 - (hy + BOSS_D / 2), (hy - BOSS_D / 2) - oy1)
        if _g < _bw:
            _bw, _bwho = _g, f"{nm} boss <-> {onm}"
say(f"  ---- {_bw:8.2f}   tightest: {_bwho}")
chk("board bosses clear every rear-wall opening", _bw)

# >>> THE FRONT MODULE HAS TO BE ABLE TO GET IN, and nothing checked that.
# >>> It slides UP the groove from below, so its outline must sweep the whole
# >>> travel without meeting dome material. The seating ledge ran the full depth
# >>> and reached 1.9 mm INTO that path, right across the groove -- it blocked
# >>> the single assembly move the entire joint exists for, and every other check
# >>> passed while it did. This is a swept-volume test: the module's own outline,
# >>> extruded through the groove's z band and dragged from below the shell up to
# >>> its seated height.
_mod = d_outline(REVEAL, ybot=-10.0) - d_outline(REVEAL + 1.0, ybot=-14.0)
_travel = slab(_mod, LIP_T + FP_CLR, LIP_T + FP_CLR + FP_T)
_swept = union([_travel.translate((0.0, -_t, 0.0))
                for _t in [0.0, 4.0, 8.0, 14.0, 22.0, 32.0, 44.0]], "travel")
chk("front module can slide UP into its groove (mm^3 in the way)",
    -(_swept ^ body).volume())

# >>> THE TWO CROWN BOARDS MUST NOT SHARE A BOSS. The ToF's pair was placed on
# >>> the x axis when it belongs on the depth axis, which drove one of its bosses
# >>> 2.9 mm INSIDE an encoder boss.
_cw = min(math.hypot(_ax - _bx2, _az - _bz2) - BOSS_D
          for _an, _ax, _az in _crown_bosses
          for _bn, _bx2, _bz2 in _crown_bosses if _an != _bn)
chk("encoder and ToF bosses do not intersect", _cw)
# ...and each board's hole pitch has to fit the board it belongs to
chk("ToF hole pitch fits its own board", TOF_PCB_D - TOF_HOLE_P)
chk("encoder hole pitch fits its own board", ENC_PCB - ENC_HOLE_P)

# >>> THE LOUVRE HAS TO DO BOTH JOBS, so both are checked on the built solid, not
# >>> assumed from the numbers. A slot that blocks the view but is not actually
# >>> open is a decoration, and one that is open but visible is a window.
def _solid(x, y, z, sz=0.25):
    return (Manifold.cube((sz, sz, sz), True).translate((x, y, z))
            ^ body).volume() > 1e-12


_vx = vent_x()[0]
_vy = VENT_Y + 2 * VENT_P
_blocked = sum(
    1 for _oy in [_vy - VENT_HH + 0.2 * _i for _i in range(1, 10)]
    if any(_solid(_vx, _oy, _z) for _z in [D - 0.2 - 0.2 * _k for _k in range(12)]))
chk("every level sight-line into a louvre is blocked", _blocked - 9)
# ...and open along its OWN axis. That axis is not 45 deg and not the wall
# normal: the slot's centre is at vy + VENT_RISE*(1-f) where f runs 0 at the
# inner opening to 1 at the outer, so it rises VENT_RISE across (WALL + 1). A
# check that samples any other line reports a blockage that is not there --
# which is exactly what a 45 deg ray did.
_z0, _zspan = RW0 - 1.0, WALL + 1.0
_open = 0
for _k in range(10):
    _f = 0.08 + 0.84 * _k / 9.0
    _z = _z0 + _zspan * _f
    _yc = _vy + VENT_RISE * (1.0 - _f)
    if not _solid(_vx, _yc, _z):
        _open += 1
chk("the louvre is actually open along its axis", _open - 10)

# >>> AND THE TOUCH PADS MUST BE POCKETS, NOT HOLES. The first version cut the
# >>> full wall and put two 22 mm windows in the top of the machine.
_worst_skin = 9e9
for _tx in touch_x():
    _dx, _dy = _tx - W / 2, TOUCH_Y - ARCH_Y
    _nx, _ny = _dx / ARCH_R ** 2, _dy / ARCH_RY ** 2
    _nl = math.hypot(_nx, _ny)
    _mat = [0.1 * _k for _k in range(-40, 20)
            if _solid(_tx + _nx / _nl * 0.1 * _k, TOUCH_Y + _ny / _nl * 0.1 * _k,
                      TOUCH_DEPTH)]
    _worst_skin = min(_worst_skin, (max(_mat) - min(_mat)) if _mat else -1.0)
chk("touch pad leaves skin (a pocket, not a hole)", _worst_skin - 1.0)

# >>> ROUND MEANS ROUND, AND IT IS MEASURED. Everything aimed at the crown used
# >>> to be built with slab(), which extrudes an (x,y) section along z and comes
# >>> out SQUARE. Measuring each bore on its axes AND its diagonal is the only
# >>> way to tell the difference from a pass/fail line.
def _bore(cx, cz, yp, rmax):
    def _open(ang):
        for _k in range(1, int(rmax / 0.05)):
            _r = 0.05 * _k
            if _solid(cx + _r * math.cos(ang), yp, cz + _r * math.sin(ang)):
                return _r
        return None
    return _open(0.0), _open(math.pi / 4), _open(math.pi / 2)


for _nm, _cx, _cz, _yp in (("encoder shaft", W / 2, ENC_Y,
                            crown_inner_y(W / 2) + 1.0),
                           ("ToF pinhole", TOF_X, TOF_Y,
                            crown_inner_y(TOF_X) + 1.0)):
    _a, _d, _b = _bore(_cx, _cz, _yp, 10.0)
    if _a and _d and _b:
        chk(f"{_nm} is round, not square",
            0.07 - max(abs(_d / _a - 1), abs(_b / _a - 1)))
    else:
        chk(f"{_nm} bore found", -1.0)

# >>> AND EACH SIDE TAB IS ONE BLOCK. The previous version intersected the
# >>> perimeter band with a full-width rect, so one "tab" made material on BOTH
# >>> flanks and the bottom corner radius carved a notch out of each. Probing
# >>> across the flank AWAY from the screw hole counts the runs of material.
for _sd in (36.0, 54.0):
    _xs = [0.25 * _k for _k in range(0, 90)
           if _solid(0.25 * _k, BP_T + LUG_H / 2, _sd + 5.0)]
    _runs = []
    for _x in _xs:
        if _runs and abs(_x - _runs[-1][-1]) <= 0.4:
            _runs[-1].append(_x)
        else:
            _runs.append([_x])
    chk(f"side tab at depth {_sd:.0f} is one clean block (no notch)",
        1.5 - len(_runs))

# >>> AND THE TABS MUST BE SIX SEPARATE BLOCKS. Sweeping the flank ALONG the
# >>> depth counts them: the ramps used to bridge the two side tabs into one long
# >>> blob with a step in it, which reads as a notch and is what this catches.
for _side, _px in (("left", WALL + LUG_L - 1.0), ("right", W - WALL - LUG_L + 1.0)):
    _zs = [0.5 * _k for _k in range(0, int(D / 0.5))
           if _solid(_px, BP_T + LUG_H / 2, 0.5 * _k)]
    _runs = []
    for _z in _zs:
        if _runs and abs(_z - _runs[-1][-1]) <= 0.75:
            _runs[-1].append(_z)
        else:
            _runs.append([_z])
    # >>> ONE CONTINUOUS RUN, and this check asserted the opposite one revision
    # >>> ago. Two separate tabs was the wrong call for a rear-wall-down print:
    # >>> it leaves an unsupportable island between them. A single rail reaching
    # >>> the rear wall is a vertical fin with no overhang at all.
    chk(f"{_side} wall carries ONE continuous rail", -abs(len(_runs) - 1))
    if _runs:
        chk(f"{_side} rail reaches the rear wall",
            _runs[-1][-1] - (D - WALL - 1.0))

# ...and each tab actually has a screw hole running UP it.
for _sx, _sd in SCREWS:
    _depth = sum(0.5 for _k in range(0, int(LUG_H / 0.5))
                 if not _solid(_sx, BP_T + 0.5 * _k, _sd))
    chk(f"tab ({_sx:.0f},{_sd:.0f}) has a screw hole up it",
        _depth - (LUG_H - BOSS_MIN_WALL - 1.0))

try:
    import trimesh
    tm = trimesh.load(os.path.join(MODEL_DIR, "dome.stl"))
    n_bodies = len(tm.split(only_watertight=False))
    say("")
    say(f"watertight={tm.is_watertight}  winding_ok={tm.is_winding_consistent}  "
        f"volume={tm.volume/1000:.1f} cm^3")
    say(f"connected bodies={n_bodies}  (must be 1)")
    if not tm.is_watertight:
        bad.append("not watertight")
    if n_bodies != 1:
        bad.append(f"{n_bodies} disconnected bodies")

    # >>> EVERY REAR-WALL BOARD'S ENVELOPE, AGAINST THE BUILT SOLID. The board
    # >>> outlines are checked pairwise against each other by
    # >>> rear_wall_clearances(), and against the arch analytically -- but nothing
    # >>> put the actual PCB volume against the actual shell. The equivalent gap on
    # >>> the bottom plate is exactly how the RTC ended up 0.9 mm inside a rail.
    # >>> The board's datum is the BOSS TIP plane, not the wall: the rear-wall
    # >>> bosses stand STANDOFF_H + 2 proud, and getting that wrong reports a
    # >>> board buried in its own standoffs.
    import numpy as _np
    _tip = D - WALL - (STANDOFF_H + 2.0)
    _bt = 1.6 + 3.0                       # PCB + tallest component, generous
    _wb = 0
    for _nm, _cx, _cy, _bw, _bh, _offs in rear_wall_boards():
        if not _offs:
            continue
        _P = _np.array([[_x, _y, _z]
                        for _x in _np.linspace(_cx - _bw/2, _cx + _bw/2, 13)
                        for _y in _np.linspace(_cy - _bh/2, _cy + _bh/2, 13)
                        for _z in _np.linspace(_tip - _bt + 0.05, _tip - 0.05, 4)])
        _hit = int(tm.contains(_P).sum())
        _wb += _hit
        say(f"  {'ok  ' if not _hit else 'FAIL'} {_nm} board envelope vs the shell "
            f"({_hit}/{len(_P)} points in material)")
        if _hit:
            bad.append(f"{_nm} board is inside the shell")

    # >>> OVERHANG AUDIT -- MEASURED OFF THE SOLID, NOT REASONED ABOUT.
    # >>> Two of this part's overhangs (the retaining rib's rear face, the crown
    # >>> bosses' rear halves) were found by reading the code and picturing the
    # >>> print. That does not scale and it does not survive the next edit: any
    # >>> new inward feature reintroduces the same fault silently, because no
    # >>> clearance check has an opinion about which way is down.
    # >>>
    # >>> PRINTED REAR-WALL DOWN, THE BED IS AT z=D AND THE BUILD RUNS TOWARDS
    # >>> z=0. So a facet whose normal points at +z is pointing at the bed, and if
    # >>> it is within 45 deg of facing straight down it needs support. Area is
    # >>> reported per z band so a regression says WHERE.
    # >>> IT MEASURES WIDTH, NOT AREA, AND THAT IS THE WHOLE POINT. The first
    # >>> version summed downward-facing area, and by that measure the ramp is
    # >>> WORTHLESS: a 3 mm ledge broken into twelve 0.25 mm steps has exactly the
    # >>> same area as the 3 mm ledge it replaced. Area cannot tell a staircase
    # >>> from a shelf. What decides whether a slicer needs support is how far a
    # >>> ledge reaches out from whatever holds it up -- its WIDTH.
    # >>>
    # >>> So the downward faces are grouped into connected coplanar patches and
    # >>> each patch's mean width is taken as 2*area/perimeter, which is exact for
    # >>> a long strip and is what every one of these is. The lip ring reports
    # >>> ~4 mm; each ramp step reports 0.25.
    # >>>
    # >>> AND THE BED FACE IS NOT AN OVERHANG. The rear wall's outer face points
    # >>> straight at the bed and is the largest downward face in the part by an
    # >>> order of magnitude -- 25431 mm^2 of it, which swamped every real finding.
    # >>> It is the first layer. It is lying ON the bed.
    # >>> CONNECTED COMPONENTS, NOT COPLANAR FACETS. Grouping by trimesh's
    # >>> `facets` (adjacent AND coplanar) catches the rib's flat shelf but is
    # >>> BLIND TO CURVED OVERHANGS: deleting the crown buttresses left every boss
    # >>> hanging over open cavity by its whole rear half, and the audit still said
    # >>> ALL CLEAR -- because a cylinder has no flat facet, so the region came
    # >>> apart into dozens of slivers each a fraction of a millimetre "wide".
    # >>> The overhanging region is whatever is CONNECTED and facing the bed,
    # >>> curved or not, so that is what gets grouped.
    import numpy as _np
    from scipy.sparse import coo_matrix as _coo
    from scipy.sparse.csgraph import connected_components as _cc
    # >>> 46 deg, NOT 45, AND THE ONE DEGREE IS THE POINT. The limit is 45 and the
    # >>> ramps are BUILT at 45, so a threshold of exactly 45 flags the very
    # >>> geometry that fixes the problem -- the rib ramp measures 44.6..45.0 deg
    # >>> across the arch (the D outline insets its semi-axes rather than truly
    # >>> offsetting, so the slope varies by a few tenths) and a strict `> 45`
    # >>> caught 1757 mm^2 of correct, self-supporting surface. One degree of slack
    # >>> distinguishes "designed at the limit" from "shallower than the limit".
    _DOWN = math.sin(math.radians(46.0))
    _down = tm.face_normals[:, 2] > _DOWN
    _down &= tm.triangles_center[:, 2] <= D - 0.05      # not the bed face
    _adj = tm.face_adjacency
    _keep = _down[_adj[:, 0]] & _down[_adj[:, 1]]
    _e = _adj[_keep]
    _nf = len(tm.faces)
    _g = _coo((_np.ones(len(_e)), (_e[:, 0], _e[:, 1])), shape=(_nf, _nf))
    _ncomp, _lab = _cc(_g, directed=False)
    # >>> A BORE'S ROOF IS A BRIDGE, NOT A CANTILEVER, AND THAT IS THE WHOLE
    # >>> DISTINCTION. Every hole whose axis is perpendicular to the build -- the
    # >>> six Ø4 heat-set bores up the tabs, the Ø3.5 ToF pinhole, the encoder
    # >>> shaft -- has an unsupported roof, and by pure downward-facing-area those
    # >>> look exactly like the rib's shelf. They are not the same thing: a roof is
    # >>> anchored on BOTH sides and spans its own diameter, and 4 mm of bridge is
    # >>> nothing. A ledge is anchored on one side only and droops.
    # >>> So bores are excluded BY NAME, with their diameters asserted small -- not
    # >>> by raising the threshold until they stop complaining, which would have
    # >>> blinded the check to the 2.24 mm ledges it is actually for.
    # >>> EACH EXCLUSION IS A CYLINDER WITH A HEIGHT RANGE, NOT A DISC. The knob's
    # >>> seating pocket is Ø30 and centred at (W/2, ENC_Y) -- and so are the two
    # >>> ENCODER BOSSES, 10 mm either side of that same axis. Excusing the pocket
    # >>> by (x,z) proximity alone would have swallowed them whole, and deleting
    # >>> the crown buttresses would then have gone unnoticed: the check would have
    # >>> been excusing the very thing it exists to find. The pocket is up at the
    # >>> outer skin (y ~155) and the bosses hang off the inner ceiling (y ~150),
    # >>> so the height is what separates them.
    _pd = flat_depth(KNOB_BOSS_D)
    _bores = [(sx, sd, INSERT_D / 2, BP_T - 1.5, BP_T + LUG_H + 0.5, "insert bore")
              for sx, sd in SCREWS]
    _bores += [(TOF_X, TOF_Y, TOF_HOLE_D / 2, H - 26.0, H + 1.5, "ToF pinhole"),
               (W / 2, KNOB_Z, ENC_SHAFT_D / 2, H - 26.0, H + 1.5, "encoder shaft"),
               (W / 2, KNOB_Z, KNOB_BOSS_D / 2, H - _pd - 0.3, H + 0.3,
                "knob seating pocket")]
    _bores += [(_bx, _bz, BOSS_PILOT_D / 2, crown_inner_y(_bx) - 6.0,
                crown_inner_y(_bx) + 2.0, "crown pilot")
               for _n, _bx, _bz in _crown_bosses]
    # >>> AND THE TEST IS THE BRIDGE SPAN, NOT THE DIAMETER. A round hole lying
    # >>> across the build direction closes gradually: the widest gap its topmost
    # >>> layer must span is the chord 2*sqrt(2*r*t), not 2*r. For the Ø30 knob
    # >>> pocket that is 4.9 mm, not 30 -- which is why a diameter limit rejected
    # >>> it and a span limit accepts it, correctly.
    _LAYER = 0.2
    for _bx, _bz, _br, _y0, _y1, _bn in _bores:
        _span = 2.0 * math.sqrt(2.0 * _br * _LAYER)
        if _span > 10.0:
            bad.append(f"{_bn} bridges {_span:.1f} mm -- too far to excuse")

    _worst, _wworst, _lip, _nbore = 0.0, "", 0.0, 0
    for _c in range(_ncomp):
        _fi = _np.where((_lab == _c) & _down)[0]
        if not len(_fi):
            continue
        _ar = float(tm.area_faces[_fi].sum())
        if _ar < 0.5:
            continue
        _ctr = tm.triangles_center[_fi].mean(axis=0)
        if any(math.hypot(_ctr[0] - _bx, _ctr[2] - _bz) <= _br + 0.4
               and _y0 <= _ctr[1] <= _y1
               for _bx, _bz, _br, _y0, _y1, _bn in _bores):
            _nbore += 1
            continue
        _cz = float(tm.triangles_center[_fi][:, 2].mean())
        _edges = tm.edges_sorted[_np.concatenate(
            [_np.arange(3) + 3 * _f for _f in _fi])]
        _uniq, _cnt = _np.unique(_edges, axis=0, return_counts=True)
        _bnd = _uniq[_cnt == 1]
        _per = float(_np.linalg.norm(
            tm.vertices[_bnd[:, 0]] - tm.vertices[_bnd[:, 1]], axis=1).sum())
        _wid = 2.0 * _ar / _per if _per > 1e-9 else 0.0
        if _cz < LIP_T + 0.05:
            _lip = max(_lip, _wid)
        elif _wid > _worst:
            _worst, _wworst = _wid, f"{_ar:.0f} mm^2 region at z={_cz:.2f}"
    say("")
    say(f"overhang audit (build runs z={D} -> 0; faces pointing at the bed)")
    say(f"  front lip's rear face      width {_lip:5.2f} mm   (unavoidable, see note)")
    say(f"  bore roofs skipped         {_nbore:5d}      bridges, not cantilevers")
    say(f"  worst elsewhere            width {_worst:5.2f} mm   {_wworst}")
    # >>> THE THRESHOLD IS 1.0 mm, AND IT IS NOT ARBITRARY. The widest thing left
    # >>> behind the lip is the touch pocket's leading end wall -- the 0.9 mm step
    # >>> where the thinned wall goes back to full thickness -- and a 0.9 mm ledge
    # >>> bridges without support on any FDM machine. Setting the bar below that
    # >>> would mean chamfering a feature that does not need it, and a check that
    # >>> fails on things that are fine is a check people learn to ignore.
    chk("no unsupported ledge wider than 1 mm behind the front lip", 1.00 - _worst)
except ImportError:
    say("validate skipped: no trimesh")

say("")
say("ALL CLEAR" if not bad else f"*** {len(bad)} PROBLEM(S) ***")
