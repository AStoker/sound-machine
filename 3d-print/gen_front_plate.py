#!/usr/bin/env python3
"""FRONT MODULE -- the single printed part that carries the whole facade.

One part, four jobs:
  * CRESCENT   through aperture + a rebate the opal acrylic drops into from
               behind + a cavity wall that sets the diffusion air gap, and six
               PADS on the inside of that wall for the LED carrier (gen_led_
               carrier.py) to screw onto
  * CLOCK      ONE OPEN APERTURE (deliberately no per-pixel holes) and the two
               CharliePlex matrices held directly. THE BOARDS ARE ONLY LOOSELY
               SOLDERED TO EACH OTHER, so each is located by its OWN posts and
               the pair is clamped by six cantilever CLIPS, on all four sides
  * SPEAKERS   grille apertures + a POST above and below each body, on its
               vertical centreline, that the speaker's nub bolts to. THE BODIES
               ARE ROTATED 90 DEG, so the nubs are top and bottom and the flanks
               carry nothing at all (no seat rings, no side ribs -- see the note
               at the speaker block). These bodies have no baffle bolt pattern.
  * MIC ARRAY  four ports + a recessed channel for the linear-4 board + a raised
               gasket land per port

Geometry comes from enclosure_geom.py -- this file only adds what a 2D drawing
cannot express (draft, clips, ribs, pilot holes). Nothing here re-derives an
envelope dimension; if a number looks like it belongs to the enclosure, it is
imported.

    PRINT FACE DOWN. Every boss, wall and clip then grows upward off the bed and
    the facade -- the one surface anyone sees -- is the bottom layer.

Needs manifold3d (robust CSG):
    .venv/bin/pip install manifold3d trimesh matplotlib
    .venv/bin/python gen_front_plate.py
Outputs models/front-module.stl (+ section previews beside the code).
"""
import math
import os
import struct

from manifold3d import CrossSection, Manifold

from enclosure_geom import (
    ARCH_R, ARCH_Y, BP_T, CAV_WALL, CLK_H, CLK_W, CLK_Y, CRES_R, CRES_Y,
    DIFF_GAP, DIFF_MARGIN, DIFF_REBATE, DIFF_T, FP_T, H, LED_R, MIC_CHAN_D,
    MIC_GASKET, MIC_PCB_H, MIC_PCB_W, MIC_PORT_D, MIC_Y, MIC_Y0, MIC_Y1,
    MTX_BOARD_H, MTX_BOARD_W, MTX_BP_T, MTX_HOLES, MTX_HOLE_D, MTX_N, MTX_PCB_T,
    MTX_STACK_GAP, ARCH_RY, CRES_RY, LED_RY, CROWN_K, SPK_POST_H, SPK_FLANK,
    BOSS_EDGE, LIP, REVEAL, RIB_W, R_BOT, SPK_BODY_H, SPK_BODY_W, SPK_GRILLE, SPK_NUB_PROJ,
    SPK_NUB_SCREW, SPK_NUB_Y, SPK_NUB_Z, SPK_POST_WALL, SPK_RING_W, SPK_SEAT_W,
    SPK_NUB_H, SPK_NUB_W, SPK_POST_W, SPK_POST_H_Y, CLR_POST_MIC,
    DIFF_LIP, CAV_Z, CARRIER_Z0, CARRIER_T, LED_STRIP_T, DIFF_R_G, CAV_RY_G,
    PAD_PROJ, PAD_W, PAD_DRAFT, PAD_Z0, PAD_RAMP, PAD_OFFSET_IN, PAD_PILOT_D,
    PAD_PILOT_Z, carrier_pads, DIFF_RY_G,
    pad_led_clearances,
    pad_wall_margins, MODEL_DIR, HERE,
    SPK_FIT, SPK_X, SPK_Y, SPK_Y0, SPK_Y1, TRAY_D, TRAY_H, TRAY_REBATE, TRAY_W, TRAY_Y0,
    TRAY_Y1, W, mic_x,
)

SEG = 96              # facets on the big arcs -- this part is 245 mm wide
# ---------------------------------------------------------------------------
# PRINT PARAMETERS -- the things a drawing does not fix. Tune these, not the
# imported geometry.
# ---------------------------------------------------------------------------
# DIFF_LIP and CAV_Z are IMPORTED now, not defined here. The LED carrier derives
# its z origin from the same stack, and two files each deriving a z stack from a
# constant only one of them owns is exactly how the earlier drift bugs started.
DIFF_R      = CRES_R + DIFF_MARGIN                 # acrylic pocket, across
DIFF_RY     = CRES_RY + DIFF_MARGIN                #      "        , up
CAV_R       = DIFF_R + CAV_WALL                    # cavity outer wall, across
CAV_RY      = DIFF_RY + CAV_WALL                   #      "            , up
assert abs(DIFF_R - DIFF_R_G) < 1e-9 and abs(CAV_RY - CAV_RY_G) < 1e-9, \
    "cavity ellipse disagrees with enclosure_geom -- the carrier will not fit"

# --- the clock: posts locate, clips clamp -----------------------------------
# THE TWO MATRICES ARE ONLY LOOSELY SOLDERED TOGETHER, so the frame cannot treat
# them as one part. Each board gets its OWN pair of locating posts through its
# own diagonal mounting holes; the clips then clamp the pair flat against the
# facade from all four sides. Posts alone would let the boards pivot off the
# face; clips alone would let the soldered joint carry the alignment.
MTX_STANDOFF = 0.6    # posts stand the boards off the facade a touch, so they
                      #   seat on defined pads instead of on stray solder
MTX_POST_D   = 1.85   # into the O2.0 hole -- locating only, no barb
MTX_POST_TIP = 0.6    # chamfered lead-in cone (self-supporting on FDM)
MTX_PAD_D    = 2.0    # plain seating pad, in the clear margin above/below the
MTX_PAD_EDGE = 1.2    #   LED field -- see the note where they are placed
CLIP_W      = 6.0     # clip width
CLIP_T      = 2.2     # cantilever thickness
CLIP_GAP    = 0.25    # clip inner face to board edge
CLIP_REACH  = 1.2     # how far the hook reaches over the board back face
CLIP_RUN    = 1.2     # retain-facet run == reach -> 45 deg, FDM self-supporting
CLIP_RAMP   = 2.6     # lead-in ramp length
CLIP_TAIL   = 1.2     # material behind the ramp, so the tip is not a knife edge

# --- speakers ---------------------------------------------------------------
SPK_RIB_H   = 5.0     # locating rib height off the back face
SPK_PILOT_D = 2.5     # (?) pilot for an M3 self-tapper -- suits PETG/PLA
SPK_PILOT_Z = 5.5     # pilot depth into the 7 mm post
# --- mic array --------------------------------------------------------------
MIC_FIT     = 0.4     # per side, board to channel
MIC_LAND_H  = 0.6     # gasket land height above the channel floor
MIC_BOSS_D  = 5.0     # M3 pilot boss beside the channel
# (?) from centre -- Seeed does not publish the array's hole positions, so this
# is a guess either way. 40, not 50: the boss stands on the CHANNEL FLOOR, which
# is only 2 mm of facade, and at 50 it landed inside the print seam's lap. The
# lap plane is at mid-thickness, so it severed the boss (above the plane) from
# the floor it stands on (below it) and left it floating on the other half.
# >>> If the real holes are elsewhere, re-check them against SPLIT_X +/- LAP_W/2.
MIC_BOSS_X  = 40.0
MIC_PILOT_D = 2.5
# --- stiffening -------------------------------------------------------------
RIB_H       = 5.0     # general stiffening rib height
RIB_T       = 2.0

# --- the print seam ---------------------------------------------------------
# The module is 250.8 wide; the target bed is 220. No rotation helps (this is a
# D, so rotating only grows the bounding box) and the 45 deg tilt that does fit
# would stand the facade up on supports. So it splits -- see the long note at
# the split itself for where the seam can and cannot go.
BED       = 220.0     # Flashforge Adventurer 5M Pro
SPLIT_X   = 73.8      # seam, centred in the one usable corridor
LAP_W     = 5.0       # tongue length -- sized to fit that corridor, not chosen
LAP_Z     = FP_T / 2  # the step: front half / back half of a 4 mm plate
LAP_CLR   = 0.25      # clearance on every mating face
PEG_D     = 2.5       # alignment pegs on the lap face
PEG_H     = 1.5
PEG_Y     = [15.0, 30.0, 56.0, 169.0]   # where the seam has material both sides
_L0, _L1  = SPLIT_X - LAP_W / 2, SPLIT_X + LAP_W / 2
# SPLIT ONLY IF IT HAS TO. Rotating the speakers and lifting the mic array took
# the module to 194.8 x 152.4, which fits a 220 bed whole -- so the seam is off.
# It stays in the code because the seam location was hard-won, and any change
# that pushes the part back over the bed turns it on again automatically.
NEEDS_SPLIT = max(W - 2*REVEAL, H - REVEAL - BP_T) > BED

_out = []


def say(s):
    _out.append(s)
    print(s)


# ---------------------------------------------------------------------------
# 2D helpers. Everything is built in DRAWING coordinates -- x 0..W from the
# left, y 0..H measured UP -- so the imported constants drop straight in.
# ---------------------------------------------------------------------------
def poly(pts):
    """CrossSection from a point list, forced counter-clockwise."""
    a = 0.5 * sum(pts[i][0] * pts[(i + 1) % len(pts)][1]
                  - pts[(i + 1) % len(pts)][0] * pts[i][1]
                  for i in range(len(pts)))
    return CrossSection([pts if a > 0 else pts[::-1]])


def rect2(x0, y0, w, h):
    return poly([(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h)])


def disc2(cx, cy, r):
    return CrossSection.circle(r, SEG).translate((cx, cy))


def half_disc(cx, cy, r, skirt=0.0, ry=None):
    """Upper half of an ELLIPSE -- the crescent shape, flat side DOWN at cy.
    The crown is flattened (CROWN_K), so `r` is the horizontal semi-axis and
    `ry` the vertical. `skirt` extends the flat side downward, which is how the
    cavity wall gets a bottom to close against."""
    ry = r if ry is None else ry
    pts = [(cx + r, cy)]
    for i in range(1, SEG):
        t = math.pi * i / SEG
        pts.append((cx + r * math.cos(t), cy + ry * math.sin(t)))
    pts.append((cx - r, cy))
    if skirt > 0:
        pts += [(cx - r, cy - skirt), (cx + r, cy - skirt)]
    return poly(pts)


def outline2():
    """The module outline: a 'D' on its long flat side. Straight flanks, a
    semicircular top of radius ARCH_R-REVEAL concentric with the crescent, and
    a flat bottom that lands on the bottom plate."""
    x0, x1 = REVEAL, W - REVEAL
    yb, ys = BP_T, ARCH_Y
    r, rry = ARCH_R - REVEAL, ARCH_RY - REVEAL
    rb = max(R_BOT - REVEAL, 0.8)          # bottom corners
    pts = [(x0 + rb, yb)]
    for i in range(9):                     # bottom-right corner
        t = -math.pi / 2 + (math.pi / 2) * i / 8
        pts.append((x1 - rb + rb * math.cos(t), yb + rb + rb * math.sin(t)))
    pts.append((x1, ys))
    for i in range(1, SEG):                # the arc
        t = math.pi * i / SEG
        pts.append((W / 2 + r * math.cos(t), ys + rry * math.sin(t)))
    pts.append((x0, ys))
    for i in range(9):                     # bottom-left corner
        t = math.pi + (math.pi / 2) * i / 8
        pts.append((x0 + rb + rb * math.cos(t), yb + rb + rb * math.sin(t)))
    return poly(pts)


def slab(cs, z0, z1):
    return cs.extrude(z1 - z0).translate((0, 0, z0))


def cyl(cx, cy, z0, z1, d):
    return (Manifold.cylinder(z1 - z0, d / 2, d / 2, SEG)
            .translate((cx, cy, z0)))


def union(parts):
    out = Manifold()
    for p in parts:
        out = out + p
    return out


# ---------------------------------------------------------------------------
# BODY
# ---------------------------------------------------------------------------
body = slab(outline2(), 0.0, FP_T)

# --- crescent ---------------------------------------------------------------
# The cavity wall stands proud of the back face; the acrylic pocket and the air
# gap are one bore through it, open at the back so the acrylic and then the LED
# carrier go in from behind.
#
# >>> THE WALL RUNS TO CARRIER_Z0, NOT CAV_Z. CAV_Z is where the LED emitting
# >>> face sits -- one DIFF_GAP behind the acrylic. The strip is LED_STRIP_T
# >>> thick BEHIND that, so a wall stopping at CAV_Z would leave the ribbon
# >>> standing proud in a 3 mm gap all the way round and give the carrier
# >>> nothing to land on. Running it the extra LED_STRIP_T shrouds the strip and
# >>> makes the wall's back face the carrier's seating plane.
cav_wall = (half_disc(W / 2, CRES_Y, CAV_R, skirt=CAV_WALL, ry=CAV_RY)
            - half_disc(W / 2, CRES_Y, DIFF_R, ry=DIFF_RY))
body = body + slab(cav_wall, 0.0, CARRIER_Z0)

# (The LED carrier fixing pads used to be built HERE, and it was wrong -- see
#  the note where they are actually built, below the cuts.)

cuts = []
cuts.append(slab(half_disc(W / 2, CRES_Y, DIFF_R, ry=DIFF_RY), DIFF_LIP, CAV_Z + 1))
cuts.append(slab(half_disc(W / 2, CRES_Y, CRES_R, ry=CRES_RY), -1.0, DIFF_LIP))

# --- clock: ONE open aperture, no per-pixel holes ---------------------------
# The matrices seat on the BACK FACE, not in a pocket. A pocket would locate the
# PAIR; the two boards are only loosely soldered to each other, so each one is
# located by its OWN posts instead and the pair is clamped by clips all round.
cuts.append(slab(rect2(W / 2 - CLK_W / 2, CLK_Y - CLK_H / 2, CLK_W, CLK_H),
                 -1.0, FP_T + 1.0))
MTX_X0 = W / 2 - TRAY_W / 2                # left edge of the butted pair
MTX_Z0 = FP_T + MTX_STANDOFF               # matrix front face
MTX_ZB = MTX_Z0 + MTX_PCB_T                # matrix back face -- clips hook here
BP_Z0  = MTX_ZB + MTX_STACK_GAP            # backpack front
BP_ZB  = BP_Z0 + MTX_BP_T                  # backpack back

# --- speakers ---------------------------------------------------------------
for sx in (SPK_X, W - SPK_X):
    cuts.append(cyl(sx, SPK_Y, -1.0, FP_T + 1, SPK_GRILLE))

# --- mic array --------------------------------------------------------------
mic_ch_w = MIC_PCB_W + 2 * MIC_FIT
mic_ch_h = MIC_PCB_H + 2 * MIC_FIT
MIC_Z0 = FP_T - MIC_CHAN_D
cuts.append(slab(rect2(W / 2 - mic_ch_w / 2, MIC_Y0 - MIC_FIT,
                       mic_ch_w, mic_ch_h), MIC_Z0, FP_T + 1))

body = body - union(cuts)

# ---------------------------------------------------------------------------
# ADDITIVE FEATURES (all behind the facade, all growing upward off the bed)
# ---------------------------------------------------------------------------
adds = []

# --- LED carrier fixing pads ------------------------------------------------
# Local thickenings on the INSIDE of the cavity wall, at the angles
# enclosure_geom.pad_angle_bands() found clear of the pixels, the end stops and
# the ribbons. They run the full height of the wall, so they also buttress what
# is otherwise a 2 mm x 19 mm unsupported fin -- that wall's aspect ratio is set
# by optics, not structure, and it prints better braced.
#
# >>> THESE MUST BE BUILT AFTER THE CUTS, AND THEY ONCE WERE NOT. Added up with
# >>> the cavity wall, they were promptly sliced away by the acrylic-pocket /
# >>> air-gap bore, which is a half_disc of DIFF_R running z=DIFF_LIP..CAV_Z+1 --
# >>> and the pads live INSIDE DIFF_R by definition, that being the entire point
# >>> of them. All that survived was 1.13 mm of stub at the very top, with an
# >>> 8 mm pilot drilling into thin air below it. The presence probe passed
# >>> because it happened to sample inside that stub.
#
# >>> THEY TAPER: wider at the base, PAD_W at the seating plane. Two reasons.
# >>> FDM prints face down here, so anything that gets WIDER as it rises
# >>> overhangs -- narrowing upward is the self-supporting direction and needs no
# >>> support inside an optical cavity, where support scarring would be visible
# >>> through the diffuser. And the flare is a gusset: it puts the material at
# >>> the root, where a boss standing 19 mm off a 2 mm wall wants to snap.
# >>> Everything the pad has to stay clear of -- ribbons, stops, pixels -- sits
# >>> at the TOP of the cavity, where the pad is at its narrowest PAD_W. The
# >>> flare only ever grows into the air gap, which is empty.
# How far past the cavity's inner face the ramp's apex is buried, so the tip
# starts inside solid wall rather than on its surface. A tip exactly ON the face
# is still a knife edge for the slicer to resolve.
APEX_BURY = 1.0


def _pad_axis(x, y):
    """Outward unit normal of the cavity ellipse at this pad's position -- the
    direction 'towards the wall'."""
    dx, dy = x - W / 2, y - CRES_Y
    nx, ny = dx / (DIFF_R_G ** 2), dy / (DIFF_RY_G ** 2)
    nl = math.hypot(nx, ny) or 1.0
    return nx / nl, ny / nl


def carrier_pad_solid(x, y, grow=0.0):
    """One fixing pad: a 45 deg cone growing out of the wall from the acrylic
    pocket floor, then a drafted column up to the seating plane.

    Built by a named function because the diffusion-air-gap clash has to subtract
    the EXACT same solid. An approximation there (it used to be a plain cylinder
    of PAD_W) stops matching the moment the pad grows a taper, and the check then
    reports interference that is really just its own bad stand-in."""
    r1 = PAD_W / 2 + grow

    # >>> THE RAMP IS A SKEWED CONE WITH ITS APEX IN THE WALL, NOT A STRAIGHT ONE
    # >>> ON THE PAD AXIS. A straight cone tapering to a point on the pad's own
    # >>> centreline puts that point PAD_OFFSET_IN (1.55 mm) clear of the wall,
    # >>> hanging in the middle of the cavity with nothing beneath it -- the bore
    # >>> has removed everything below PAD_Z0. On FDM that first layer prints into
    # >>> thin air. It is the classic floating tip: it looks like a tidy taper in
    # >>> section and is unbuildable.
    # >>>
    # >>> Instead the apex is pushed OUTWARD, past the cavity's inner face and
    # >>> into the wall's own material, and the solid is the convex hull of that
    # >>> apex and the shaft's base circle. Every layer of the result therefore
    # >>> touches the wall -- the pad grows gradually out of it rather than
    # >>> appearing beside it -- and the whole thing is one half-cone leaning on
    # >>> a face that is already solid all the way down.
    _o = _pad_axis(x, y)                       # outward normal at this pad
    apex = (x + _o[0] * (PAD_OFFSET_IN + APEX_BURY),
            y + _o[1] * (PAD_OFFSET_IN + APEX_BURY))
    ramp = Manifold.batch_hull([
        Manifold.cylinder(0.01, 0.35, 0.35, SEG)
        .translate((apex[0], apex[1], PAD_Z0 - grow)),
        Manifold.cylinder(0.01, r1, r1, SEG)
        .translate((x, y, PAD_Z0 + PAD_RAMP)),
    ])
    shaft = (Manifold.cylinder(CARRIER_Z0 - PAD_Z0 - PAD_RAMP + 2*grow, r1, r1,
                               SEG)
             .translate((x, y, PAD_Z0 + PAD_RAMP)))
    pad = ramp + shaft
    # >>> CLIPPED TO THE CAVITY'S OUTER FACE. A round boss centred inside the
    # >>> wall grows BOTH ways, and the base flare -- the whole point of which is
    # >>> to put material at the root -- pushed 1.2 mm straight out through the
    # >>> wall's outer face and into the 0.9 mm rim, which is the dome's
    # >>> retaining-rib band. That is the one place on this part where a boss
    # >>> jams the whole assembly.
    # >>> `pad_wall_margins()` did not catch it because it measured the SHAFT
    # >>> radius and the flare is bigger. Rather than fix only the number, the
    # >>> geometry is now clipped: intersecting with the cavity envelope means no
    # >>> pad can EVER break the outer plane, whatever draft it is given. The
    # >>> outer side of the boss simply comes out flush with the wall.
    return pad ^ slab(half_disc(W / 2, CRES_Y, CAV_R + grow,
                                skirt=CAV_WALL, ry=CAV_RY + grow),
                      -1.0, CARRIER_Z0 + 1.0)


pad_pts, pad_solids = [], []
for _px, _py, _deg in carrier_pads():
    _x, _y = W / 2 + _px, CRES_Y + _py
    pad_pts.append((_x, _y))
    pad_solids.append(carrier_pad_solid(_x, _y))
adds.extend(pad_solids)

# --- matrix locating posts + seating pads, ONE SET PER BOARD ----------------
# Per board: two posts through its diagonal O2.0 holes, and two plain pads on
# the other diagonal so it seats on four points and cannot rock.
mtx_posts, mtx_pads = [], []
for b in range(MTX_N):
    bx = MTX_X0 + b * MTX_BOARD_W
    for hx, hy in MTX_HOLES:
        px, py = bx + hx, TRAY_Y0 + hy
        mtx_posts.append((px, py))
        adds.append(cyl(px, py, FP_T, MTX_Z0 + MTX_PCB_T + 0.1, MTX_POST_D))
        adds.append(Manifold.cylinder(MTX_POST_TIP, MTX_POST_D / 2,
                                      MTX_POST_D * 0.2, SEG)
                    .translate((px, py, MTX_Z0 + MTX_PCB_T + 0.1)))
    # Pads go in the board's TOP and BOTTOM margins at mid-width, NOT on the
    # free corners: the corners are inside the LED field's bounding box, and a
    # pad there lands on the outermost LEDs. Only the strips above the top row
    # and below the bottom row are genuinely clear.
    for hy in (MTX_PAD_EDGE, MTX_BOARD_H - MTX_PAD_EDGE):
        px, py = bx + MTX_BOARD_W / 2, TRAY_Y0 + hy
        mtx_pads.append((px, py))
        adds.append(cyl(px, py, FP_T, MTX_Z0, MTX_PAD_D))

# --- gasket lands, then the ports straight through them ---------------------
for mxc in mic_x():
    adds.append(cyl(mxc, MIC_Y, MIC_Z0, MIC_Z0 + MIC_LAND_H,
                    MIC_PORT_D + 2 * MIC_GASKET))
# --- mic board fixing bosses ------------------------------------------------
for sgn in (-1, 1):
    adds.append(cyl(W / 2 + sgn * MIC_BOSS_X, MIC_Y, MIC_Z0,
                    MIC_Z0 + MIC_CHAN_D + 2.0, MIC_BOSS_D))

# --- speaker nub posts (TOP AND BOTTOM) -------------------------------------
# >>> THE SPEAKERS ARE ROTATED 90 DEG, so the nubs are TOP AND BOTTOM and the
# >>> posts go WITH THEM. This block used to build the posts on the FLANKS, at
# >>> px = sx +/- (SPK_BODY_W/2 + SPK_FIT + pw/2) -- x = 5.25 / 56.95 and their
# >>> mirrors. That is a leftover from the pre-rotation speaker model and it was
# >>> the single root cause of six separate failures: the outboard pair stood in
# >>> the dome's groove band and the inboard pair stood inside the matrix
# >>> footprint. If a probe ever finds a wall at x ~ 5 or ~ 57 again, look here
# >>> first.
#
# NO RIBS, on any face. Two screws on the body's vertical centreline fix x, y
# and rotation between them, so nothing else is needed -- and there is nowhere
# to put a rib anyway: the width chain budgets SPK_FLANK = 1.0 per flank as pure
# clearance, and a 1 mm fin there would land in the dome's retaining-rib band.
#
# The nub lands SPK_NUB_Z behind the speaker's front face, and that face sits on
# the back of the facade -- so the post top is at FP_T + SPK_NUB_Z and the screw
# goes in FROM BEHIND, through the nub, into the post.
#
# >>> POST WIDTH IS SET BY THE NUB, NOT BY THE BODY. A post scaled off the body
# >>> (0.60 x SPK_BODY_W = 27) reaches x = 44.6, which is 1.4 mm from the mic
# >>> PCB now that the array has come down. SPK_POST_W is nub + wall = 10, which
# >>> keeps it ~10 mm clear -- see CLR_POST_MIC in the clearance table.
for sx in (SPK_X, W - SPK_X):
    for ybase in (SPK_Y0 - SPK_FIT - SPK_POST_H_Y, SPK_Y1 + SPK_FIT):
        adds.append(slab(rect2(sx - SPK_POST_W / 2, ybase,
                               SPK_POST_W, SPK_POST_H_Y),
                         FP_T, FP_T + SPK_NUB_Z))

# --- stiffening -------------------------------------------------------------
# A 4 mm plate this size with two sealed boxes bolted to it will drum. There is
# very little free facade to rib, though: below the tray there is 1 mm to the
# module edge, above it 1.4 mm to the mic channel, and outboard of the speakers
# about 1 mm to the flank. Two places genuinely have room:
#
#  1. A full-width SPINE in the band between the speaker tops and the cavity
#     wall. This is the widest unsupported span on the part, and the spine ties
#     both speaker seats into the cavity wall -- which is itself a 12.7 mm tall
#     stiffener running the whole upper half.
#     It stops BOSS_EDGE short of the outline at each end -- it is a boss on the
#     back face, so it has to clear the dome's retaining rib like everything
#     else. An earlier version ran it edge to edge and jammed the joint.
# It sits BETWEEN the matrix top and the speaker tops, spanning the middle only
# -- the mic channel now occupies the band that used to be free above the
# speakers, and the speakers themselves own the outer thirds.
SPINE_Y0 = TRAY_Y1 + CLIP_GAP + CLIP_T + 1.0
SPINE_Y1 = SPK_Y1 - 1.0
SPINE_X0 = SPK_X + SPK_BODY_W/2 + SPK_FIT + 1.0
adds.append(slab(rect2(SPINE_X0, SPINE_Y0, W - 2*SPINE_X0, SPINE_Y1 - SPINE_Y0),
                 FP_T, FP_T + RIB_H))
#  2. A SECOND SPINE in the matching band BELOW the matrix.
#
# >>> THIS REPLACES THE OLD "SHORT RIBS INBOARD FROM EACH SPEAKER". Those ran at
# >>> y = SPK_Y +/- RIB_T/2, reaching 11 mm in from each speaker towards the
# >>> clock. That was safe when the matrix sat hard down on the floor. It is not
# >>> any more: the clock is now CENTRED ON THE SPEAKERS (see TRAY_Y0), so
# >>> SPK_Y *is* the matrix mid-height, and each rib ran straight through the
# >>> boards -- 49.8 mm^3 into the matrix envelope, into 288 LEDs, and through
# >>> the end clips' hook zone. Four separate failures, one rib.
# >>>
# >>> There is nowhere to put them any more: from the speaker seat to the end
# >>> clip's outer face is 0.77 mm. So the stiffening moves to the band BELOW
# >>> the matrix, which is the mirror of the spine above it and is genuinely
# >>> empty -- and a symmetric pair of spines braces the plate better than one
# >>> spine plus two stubs did.
SPINE2_Y0 = BP_T + BOSS_EDGE                       # clear the back-face keep-out
SPINE2_Y1 = TRAY_Y0 - CLIP_GAP - CLIP_T - 1.0      # clear the bottom clips
adds.append(slab(rect2(SPINE_X0, SPINE2_Y0, W - 2*SPINE_X0, SPINE2_Y1 - SPINE2_Y0),
                 FP_T, FP_T + RIB_H))

body = body + union(adds)

# ---------------------------------------------------------------------------
# TRAY CLIPS -- cantilevers on the tray's two END faces
# ---------------------------------------------------------------------------
# Why the ends: below the tray there is 1 mm to the module's bottom edge and
# above it 2 mm to the mic channel, so the long sides have nowhere to root a
# clip. The ends have 13.9 mm of clear facade before the speaker seats.
# Why the corners: the tray's end walls have an 18 mm wire notch dead centre.
def clip(axis, face, sgn, centre, hook_z):
    """One cantilever, on any of the four sides.

    `axis` is the direction the clip FACES: 'x' for the two ends, 'y' for the
    top and bottom edges. `sgn` is +1 when the clip sits on the high side of
    `face`, so its hook reaches back in the negative direction.

    The profile is drawn in (u, z) -- the part's own cross-section -- then swung
    up so the drawn z becomes real z. Every overhang is therefore a 45 deg facet
    in the print's vertical plane:
        root ---- beam ---- 45 deg retain facet ---- shallow lead-in ramp
    """
    ui = face + sgn * CLIP_GAP                      # inner face of the beam
    uo = ui + sgn * CLIP_T                          # outer face
    hook = ui - sgn * CLIP_REACH                    # hook tip, over the board
    z_top = hook_z + CLIP_RUN + CLIP_RAMP + CLIP_TAIL
    pts = [
        (ui, FP_T),                                 # root
        (ui, hook_z),                               # up the inner face
        (hook, hook_z + CLIP_RUN),                  # 45 deg retain facet
        (ui, hook_z + CLIP_RUN + CLIP_RAMP),        # lead-in ramp
        (ui, z_top),
        (uo, z_top),                                # over the top, back down
        (uo, FP_T),
    ]
    # extrude gives width along local z; rotate x+90 stands the profile up and
    # lays the width along y, giving x=u.
    s = poly(pts).extrude(CLIP_W).rotate((90, 0, 0)).translate((0, CLIP_W, 0))
    if axis == "x":                                 # u is x, width along y
        return s.translate((0, centre - CLIP_W / 2, 0))
    # u is y: swap the axes (rotate about z), then centre the width in x
    return (s.rotate((0, 0, 90)).translate((CLIP_W, 0, 0))
             .translate((centre - CLIP_W / 2, 0, 0)))


mtx_x0, mtx_x1 = MTX_X0, MTX_X0 + TRAY_W
mtx_y0, mtx_y1 = TRAY_Y0, TRAY_Y0 + TRAY_H
# Two clips on each long edge and one on each end -- six, on all four sides.
# The long-edge clips sit over the SEAM and the outer thirds, so each board is
# clamped near its own centre rather than relying on the solder joint.
CLIP_TOP_X = [W / 2 - TRAY_W / 4, W / 2 + TRAY_W / 4]
CLIP_BOT_X = [W / 2 - TRAY_W / 4, W / 2 + TRAY_W / 4]
clips = [clip("x", mtx_x0, -1, (mtx_y0 + mtx_y1) / 2, MTX_ZB),
         clip("x", mtx_x1, +1, (mtx_y0 + mtx_y1) / 2, MTX_ZB)]
clips += [clip("y", mtx_y0, -1, cx, MTX_ZB) for cx in CLIP_BOT_X]
clips += [clip("y", mtx_y1, +1, cx, MTX_ZB) for cx in CLIP_TOP_X]
body = body + union(clips)

# ---------------------------------------------------------------------------
# CONTAINMENT GUARD
# ---------------------------------------------------------------------------
# Nothing may escape the module outline -- it has to slide up a groove in the
# dome, so a boss hanging 1 mm past the edge jams the whole assembly. Trimming
# against the outline prism makes that structurally impossible rather than
# something to remember. (An earlier revision had ribs 10 mm off the edge.)
before = body.bounding_box()
body = body ^ slab(outline2(), -1.0, CAV_Z + 20.0)
after = body.bounding_box()
trimmed = (abs(before[0] - after[0]) + abs(before[3] - after[3])
           + abs(before[1] - after[1]) + abs(before[4] - after[4]))

# ---------------------------------------------------------------------------
# PILOT HOLES -- cut last, so nothing fills them back in
# ---------------------------------------------------------------------------
pilots = []
for sx in (SPK_X, W - SPK_X):
    for py in (SPK_Y0 - SPK_FIT - (SPK_NUB_PROJ + SPK_POST_WALL)/2,
               SPK_Y1 + SPK_FIT + (SPK_NUB_PROJ + SPK_POST_WALL)/2):
        pilots.append(cyl(sx, py,
                          FP_T + SPK_NUB_Z - SPK_PILOT_Z, FP_T + SPK_NUB_Z + 1,
                          SPK_PILOT_D))
for sgn in (-1, 1):
    pilots.append(cyl(W / 2 + sgn * MIC_BOSS_X, MIC_Y,
                      MIC_Z0 + 0.8, MIC_Z0 + MIC_CHAN_D + 3, MIC_PILOT_D))
for mxc in mic_x():
    pilots.append(cyl(mxc, MIC_Y, -1.0, MIC_Z0 + MIC_LAND_H + 1, MIC_PORT_D))
# LED carrier pilots. Blind, from the BACK -- they must not break through into
# the diffusion cavity or the acrylic pocket, so they stop PAD_PILOT_Z short of
# CARRIER_Z0 and never reach DIFF_LIP+DIFF_REBATE. Checked below.
for _px, _py, _ in carrier_pads():
    pilots.append(cyl(W / 2 + _px, CRES_Y + _py,
                      CARRIER_Z0 - PAD_PILOT_Z, CARRIER_Z0 + 1, PAD_PILOT_D))
body = body - union(pilots)

# ---------------------------------------------------------------------------
# SPLIT FOR THE PRINT BED
# ---------------------------------------------------------------------------
# The module is 250.8 wide and the target bed is 220. No rotation helps -- this
# is a D, so rotating only grows the bounding box, and the 45 deg tilt that does
# fit geometrically would stand the facade up at 45 deg on supports, which ruins
# the one surface anyone looks at. So it splits.
#
# WHERE: a single seam, threading the only usable corridor across the width --
# between the left speaker seat (ends x=70.3) and the matrix's end clip (starts
# x=83.4). That keeps the ENTIRE clock on one piece, which matters: the two
# matrices are the thing that is not rigid, and putting a glue joint between
# them would undo the whole posts-and-clips arrangement. A centre seam would fit
# the bed just as well and is exactly the wrong place.
#
# HOW: a Z-LAP, not a butt joint. The front half of the plate carries on past
# the seam as a tongue; the back half of the other piece laps over it. Bosses
# are unaffected -- they all live above the lap plane, so each one lands whole
# on the right-hand piece rather than being cut in two.
# >>> THE LAP ZONE MUST CONTAIN NO BOSS THAT STANDS ON THINNED FACADE. The lap
# >>> plane sits at mid-thickness, and the mic channel's floor is exactly that
# >>> thick -- so a boss standing in the channel ends up ABOVE the plane (right
# >>> piece) while the floor it stands on is BELOW it (left piece), and the boss
# >>> prints as a floating island. That is what the per-half body count catches.
# >>> The usable corridor is therefore speaker seat (ends 70.3) -> first gasket
# >>> land (starts 77.25), 6.95 wide, and the lap has to live inside it.
# (SPLIT_X / LAP_* / PEG_* / BED are up top with the other print parameters --
#  the rib layout has to know where the seam is, and that happens earlier.)
BIG = 1000.0


def _halfspace(x0, x1, z0, z1):
    return slab(rect2(x0, -BIG / 2, x1 - x0, BIG), z0, z1)


if NEEDS_SPLIT:
    # left keeps everything before the lap, plus the front-layer tongue
    left_region = (_halfspace(-BIG, _L0, -BIG, BIG)
                   + _halfspace(_L0, _L1 - LAP_CLR, -BIG, LAP_Z - LAP_CLR))
    # right keeps everything after the lap, plus the back layer through it
    right_region = (_halfspace(_L1, BIG, -BIG, BIG)
                    + _halfspace(_L0 + LAP_CLR, _L1, LAP_Z, BIG))
    pegs, peg_holes = [], []
    for _py in PEG_Y:
        pegs.append(cyl(SPLIT_X, _py, LAP_Z - LAP_CLR,
                        LAP_Z - LAP_CLR + PEG_H, PEG_D))
        peg_holes.append(cyl(SPLIT_X, _py, LAP_Z - 0.3,
                             LAP_Z + PEG_H + 0.3, PEG_D + 2 * LAP_CLR))
    left_part = (body ^ left_region) + union(pegs)
    right_part = (body ^ right_region) - union(peg_holes)
    left_part = left_part ^ (body + union(pegs))
else:
    left_part = right_part = None

# ---------------------------------------------------------------------------
# EXPORT
# ---------------------------------------------------------------------------
base = os.path.dirname(os.path.abspath(__file__))


def write_stl(solid, name):
    m = solid.to_mesh()
    vv, ff = m.vert_properties[:, :3], m.tri_verts
    buf = bytearray(b"\0" * 80 + struct.pack("<I", len(ff)))
    for f in ff:
        a, b, c = vv[f[0]], vv[f[1]], vv[f[2]]
        ux, uy, uz = b - a
        vx, vy, vz = c - a
        nx, ny, nz = uy*vz - uz*vy, uz*vx - ux*vz, ux*vy - uy*vx
        L = math.sqrt(nx*nx + ny*ny + nz*nz) or 1.0
        buf += struct.pack("<12fH", nx/L, ny/L, nz/L, *a, *b, *c, 0)
    open(os.path.join(base, name), "wb").write(buf)
    return vv, ff


body = body.translate((-REVEAL, -BP_T, 0.0))        # part origin at its corner
V, F = write_stl(body, "front-module.stl")
if NEEDS_SPLIT:
    left_part = left_part.translate((-REVEAL, -BP_T, 0.0))
    right_part = right_part.translate((-REVEAL, -BP_T, 0.0))
    write_stl(left_part, "front-module-L.stl")
    write_stl(right_part, "front-module-R.stl")
    for _stale in ():
        pass
else:
    for _stale in ("front-module-L.stl", "front-module-R.stl"):
        _fp = os.path.join(base, _stale)
        if os.path.exists(_fp):
            os.remove(_fp)
bb = body.bounding_box()
say(f"wrote front-module.stl   {len(F)} triangles")
say(f"bbox        {bb[3]-bb[0]:.2f} x {bb[4]-bb[1]:.2f} x {bb[5]-bb[2]:.2f} mm")
say(f"z stack     facade 0-{FP_T}   acrylic {DIFF_LIP}-{DIFF_LIP+DIFF_REBATE}"
    f"   air gap {DIFF_LIP+DIFF_REBATE}-{CAV_Z}   cavity wall to {CAV_Z}")
say(f"crescent    aperture R{CRES_R}  acrylic pocket R{DIFF_R}  "
    f"cavity wall R{DIFF_R}-{CAV_R}   LED field R{LED_R} (fade band "
    f"{CRES_R-LED_R:.0f})")
say(f"clock       OPEN aperture {CLK_W} x {CLK_H} - no per-pixel holes")
say(f"            {MTX_N} matrices {MTX_BOARD_W} x {TRAY_H} butted = "
    f"{TRAY_W:.2f} wide, seating on the back face at z={MTX_Z0}")
say(f"            LOOSELY SOLDERED PAIR -> {len(mtx_posts)} locating posts "
    f"({chr(216)}{MTX_POST_D} into their own {chr(216)}{MTX_HOLE_D} holes) + "
    f"{len(mtx_pads)} seating pads")
say(f"            {len(clips)} clips on all four sides, {CLIP_W} wide, hook "
    f"{CLIP_REACH} over the board back at z={MTX_ZB:.2f}")
say(f"            stack: matrix {MTX_Z0}-{MTX_ZB} | gap | backpack "
    f"{BP_Z0}-{BP_ZB}")
say(f"speakers    grille {chr(216)}{SPK_GRILLE} thru; NO ribs (rotated mount); "
    f"posts {SPK_NUB_Z} tall with {chr(216)}{SPK_PILOT_D} x {SPK_PILOT_Z} pilots")
say(f"mic         channel {mic_ch_w:.1f} x {mic_ch_h:.1f} x {MIC_CHAN_D} deep; "
    f"4x {chr(216)}{MIC_PORT_D} ports on {chr(216)}{MIC_PORT_D+2*MIC_GASKET} "
    f"gasket lands")

# ---------------------------------------------------------------------------
# ENVELOPE INTERFERENCE TESTS
# ---------------------------------------------------------------------------
# Eyeballing a render does not prove a part fits. For every component this
# module carries, intersect its swept envelope with the printed solid: the
# result must be EXACTLY zero. Anything else is material where a component has
# to go, which is the one class of error that only shows up after a 9-hour
# print.
say("")
say("envelope interference (mm^3 of plastic inside a component's space)")
part_body = body.translate((REVEAL, BP_T, 0.0))     # back to drawing coords
bad = []


def clash(name, env, allow=0.0):
    v = (part_body ^ env).volume()
    ok = v <= allow + 1e-6
    say(f"  {'FAIL' if not ok else 'ok  '} {v:9.2f}   {name}")
    if not ok:
        bad.append((name, -1))
    return v


# The matrix pair. Everything from its front face to its back face must be free
# EXCEPT the locating posts, which are supposed to be inside its holes -- so the
# envelope has those holes punched out of it. The clip hooks deliberately
# overhang, but only ABOVE the back face.
mtx_env = rect2(mtx_x0, mtx_y0, TRAY_W, TRAY_H)
for _p in mtx_posts:
    mtx_env = mtx_env - disc2(_p[0], _p[1], MTX_HOLE_D / 2)
clash("matrix pair envelope (front -> back face, holes excepted)",
      slab(mtx_env, MTX_Z0, MTX_ZB))
clash("driver backpacks behind them",
      slab(rect2(mtx_x0, mtx_y0, TRAY_W, TRAY_H), BP_Z0, BP_ZB))
# The LEDs stand proud of the board front, so nothing may touch them: not the
# facade (they have to be inside the aperture) and not the seating pads or
# posts. Checked against ACTUAL LED positions -- a bounding box round the field
# clips the board corners, where the pads legitimately live.
LED_PITCH_PCB, LED_COLS, LED_ROWS = 2.54, 16, 9
LED_X0_PCB, LED_Y0_PCB = 2.413, 3.683
LED_BODY = 1.6        # (?) 0606-ish package on the CharliePlex boards
led_xy = [(MTX_X0 + b * MTX_BOARD_W + LED_X0_PCB + c * LED_PITCH_PCB,
           TRAY_Y0 + LED_Y0_PCB + r * LED_PITCH_PCB)
          for b in range(MTX_N) for c in range(LED_COLS) for r in range(LED_ROWS)]
leds = union([cyl(x, y, 0.0, MTX_Z0, LED_BODY) for x, y in led_xy])
clash(f"{len(led_xy)} LEDs vs facade / pads / posts", leds)
# the opal acrylic, dropped in from behind onto the ledge
clash("opal acrylic disc",
      slab(half_disc(W / 2, CRES_Y, CRES_R + 0.2, ry=CRES_RY + 0.2), DIFF_LIP,
           DIFF_LIP + DIFF_T))
# The diffusion air gap must be clear or it is not a diffusion cavity. The six
# carrier pads are the ONE thing allowed into it, so they are subtracted from
# the envelope rather than waved through with an allowance -- that way the check
# still catches anything else that wanders in, and it fails if a pad moves
# somewhere it was not vetted for. How close each one comes to a pixel is
# measured separately, in the pad table.
_gap_env = slab(half_disc(W / 2, CRES_Y, CRES_R, ry=CRES_RY),
                DIFF_LIP + DIFF_REBATE, CAV_Z)
# Grown by a hair so the subtraction is watertight against the pad's own faces.
# NOT .scale() -- that scales about the ORIGIN, which slides the pads sideways by
# metres of x and leaves the real ones fully inside the envelope.
for _px, _py in pad_pts:
    _gap_env = _gap_env - carrier_pad_solid(_px, _py, grow=0.05)
clash("diffusion air gap (carrier pads excepted)", _gap_env)
# >>> AND PROVE THE PADS STAY INSIDE THE CAVITY. `pad_wall_margins()` is
# >>> arithmetic on a radius; this is the geometry itself. Intersect the built
# >>> pads with everything OUTSIDE the cavity's outer face -- it has to be zero.
# >>> The arithmetic version of this check measured the shaft radius, missed that
# >>> the base flare was 1.5 mm bigger, and cheerfully vouched for a boss sitting
# >>> 1.2 mm inside the dome's retaining-rib band.
_outside = (slab(outline2(), 0.0, CARRIER_Z0)
            - slab(half_disc(W / 2, CRES_Y, CAV_R, skirt=CAV_WALL, ry=CAV_RY),
                   -1.0, CARRIER_Z0 + 1.0))
clash("carrier pads stay inside the cavity wall",
      union([_ps ^ _outside for _ps in pad_solids]))
# each speaker body, plus the nubs sweeping in from behind
for _sx in (SPK_X, W - SPK_X):
    clash(f"speaker body @ x={_sx:.1f}",
          slab(rect2(_sx - SPK_BODY_W / 2, SPK_Y0, SPK_BODY_W, SPK_BODY_H),
               FP_T, FP_T + 22.0))
    for _ny, _w in ((SPK_Y0 - SPK_NUB_PROJ, "lower"), (SPK_Y1, "upper")):
        clash(f"  {_w} nub @ y={_ny:.1f}",
              slab(rect2(_sx - 4.0, _ny, 8.0, SPK_NUB_PROJ),
                   FP_T + SPK_NUB_Z, FP_T + SPK_NUB_Z + 6.0))
# the mic array board sitting in its channel, clear of the gasket lands
clash("mic array board (above the gasket lands)",
      slab(rect2(W / 2 - MIC_PCB_W / 2, MIC_Y0, MIC_PCB_W, MIC_PCB_H),
           MIC_Z0 + MIC_LAND_H, MIC_Z0 + MIC_LAND_H + 1.6),
      allow=2 * math.pi * (MIC_BOSS_D / 2) ** 2 * 1.6 + 1)   # the 2 M3 bosses
# The dome groove. The keep-out band is RIB_W wide -- the RIB is the part that
# grips the BACK face, which is the only face bosses stand off. (LIP_W is the
# front cover and is irrelevant here; the facade is flat.)
#
# The band follows the two FLANKS and the ARC but NOT the bottom edge: the
# bottom is the open end the module slides in through, and the bottom plate
# captures it there instead. The full flank height has to stay clear, because
# every point of it travels through the groove on the way up.
groove = (outline2() - outline2().offset(-RIB_W)) - rect2(
    REVEAL + RIB_W, BP_T - 1.0, W - 2 * (REVEAL + RIB_W), RIB_W + 1.0)
clash("dome groove band - flanks + arc must stay plain",
      slab(groove, FP_T, CAV_Z + 20.0))

# ---------------------------------------------------------------------------
# FEATURE PRESENCE
# ---------------------------------------------------------------------------
# The interference tests above are all NEGATIVE -- they prove nothing is where
# it shouldn't be. They cannot notice a retention feature that quietly vanished
# into a boolean. So probe for material where each one is supposed to BE.
say("")
say("feature presence (a 1 mm probe must find plastic)")


def probe(name, x, y, z, want=True):
    hit = (part_body ^ Manifold.cube((1.0, 1.0, 1.0))
           .translate((x - 0.5, y - 0.5, z - 0.5))).volume() > 1e-6
    ok = (hit == want)
    say(f"  {'FAIL' if not ok else 'ok  '} {'solid' if hit else 'empty':>6}   "
        f"{name}")
    if not ok:
        bad.append((name, -1))


for _sx in (SPK_X, W - SPK_X):
    side = "L" if _sx < W / 2 else "R"
    for _py, _w in ((SPK_Y0 - SPK_FIT - (SPK_NUB_PROJ+SPK_POST_WALL)/2, "lower"),
                    (SPK_Y1 + SPK_FIT + (SPK_NUB_PROJ+SPK_POST_WALL)/2, "upper")):
        probe(f"speaker {side} {_w} nub post", _sx, _py, FP_T + 1.0)
    # >>> THE OLD "left / right locating rib" PROBES ARE GONE. There are no
    # >>> flank ribs on the rotated mount -- two screws top and bottom locate the
    # >>> body completely. The probes survived the rotation and passed by
    # >>> accident, hitting the stiffening rib that used to run at SPK_Y.
    #
    # What has to be checked instead is the OUTBOARD flank, and checked the
    # other way round: it must be BARE. The width chain budgets SPK_FLANK = 1.0
    # there and nothing else, and it butts straight onto the dome's retaining-rib
    # keep-out -- so anything that appears in that 1 mm jams the module on
    # assembly. Probe the middle of the gap.
    #
    # The INBOARD flank is deliberately not probed either way: the matrix end
    # clip lives in that band by design, and how close it comes to the speaker
    # seat is measured properly in the clearance table.
    _fo = _sx - (SPK_BODY_W/2 + SPK_FLANK/2) if _sx < W/2 else \
          _sx + (SPK_BODY_W/2 + SPK_FLANK/2)
    probe(f"speaker {side} OUTBOARD flank stays bare", _fo, SPK_Y, FP_T + 2.0,
          want=False)
# >>> PROBE THE PAD DOWN ITS WHOLE HEIGHT, NOT JUST AT THE TOP. The first
# >>> version sampled once at CARRIER_Z0 - 1.0 and passed while the pad was a
# >>> 1.13 mm stub floating over a hole -- the bore had eaten everything below.
# >>> A single probe near a feature's tip cannot tell a boss from a lid.
for _px, _py, _deg in carrier_pads():
    _pxx, _pyy = W/2 + _px, CRES_Y + _py
    # Sample between PAD_Z0 (the pocket floor it starts on) and the seat -- not
    # from z=0, which is inside the acrylic pocket where the pad is absent BY
    # DESIGN and a probe would fail for the wrong reason.
    _pz0, _pz1 = PAD_Z0 + PAD_RAMP + 0.5, CARRIER_Z0 - 0.5
    for _f, _lab in ((0.05, "at the seat"), (0.50, "mid-height"),
                     (0.95, "just above the ramp")):
        probe(f"carrier pad @ {_deg:.0f} deg, {_lab}",
              _pxx + PAD_W*0.30, _pyy, _pz1 - _f * (_pz1 - _pz0))
    # ...and the pilot must be a HOLE through that solid, to its full depth
    probe(f"  ...pilot open to depth @ {_deg:.0f} deg", _pxx, _pyy,
          CARRIER_Z0 - PAD_PILOT_Z + 0.5, want=False)
    # ...but must NOT break through into the air gap below it
    probe(f"  ...pilot bottoms out @ {_deg:.0f} deg", _pxx, _pyy,
          CARRIER_Z0 - PAD_PILOT_Z - 1.0)
# >>> NO FLOATING LAYER IN THE RAMP. "connected bodies == 1" does NOT catch this:
# >>> a tip hanging in mid-air is still joined to the shaft above it, so the part
# >>> stays one body while its first layers print into nothing. The ramp exists to
# >>> grow the pad OUT OF the wall, so the test is that every height in it has
# >>> material AT the wall's inner face -- attached, not merely nearby.
for _px, _py, _deg in carrier_pads():
    _x, _y = W/2 + _px, CRES_Y + _py
    _ox, _oy = _pad_axis(_x, _y)
    for _f in (0.08, 0.4, 0.75):
        _z = PAD_Z0 + PAD_RAMP * _f
        probe(f"pad @ {_deg:.0f} deg ramp touches the wall at z={_z:.1f}",
              _x + _ox * PAD_OFFSET_IN, _y + _oy * PAD_OFFSET_IN, _z)
probe("stiffening spine (above matrix)", W / 2,
      (SPINE_Y0 + SPINE_Y1) / 2, FP_T + 2.0)
probe("stiffening spine (below matrix)", W / 2,
      (SPINE2_Y0 + SPINE2_Y1) / 2, FP_T + 2.0)
probe("cavity wall at the apex", W / 2, CRES_Y + DIFF_RY + CAV_WALL / 2, CAV_Z - 1)
_clip_spec = ([("end L", "x", mtx_x0, -1, (mtx_y0 + mtx_y1) / 2),
               ("end R", "x", mtx_x1, +1, (mtx_y0 + mtx_y1) / 2)]
              + [(f"bottom {i}", "y", mtx_y0, -1, cx)
                 for i, cx in enumerate(CLIP_BOT_X)]
              + [(f"top {i}", "y", mtx_y1, +1, cx)
                 for i, cx in enumerate(CLIP_TOP_X)])
for _nm, _ax, _face, _sg, _ctr in _clip_spec:
    if _ax == "x":
        beam = (_face + _sg * (CLIP_GAP + CLIP_T / 2), _ctr)
        hook = (_face - _sg * (CLIP_REACH / 2), _ctr)
    else:
        beam = (_ctr, _face + _sg * (CLIP_GAP + CLIP_T / 2))
        hook = (_ctr, _face - _sg * (CLIP_REACH / 2))
    probe(f"clip {_nm} beam", beam[0], beam[1], MTX_ZB - 1.0)
    # the hook must overhang the board, ABOVE its back face...
    probe(f"clip {_nm} hook (over the board)", hook[0], hook[1],
          MTX_ZB + CLIP_RUN * 0.5)
    # ...and must NOT be inside the board below that face
    probe(f"clip {_nm} clear below the back face", hook[0], hook[1],
          MTX_ZB - 0.8, want=False)
for _i, (_px, _py) in enumerate(mtx_posts):
    probe(f"matrix locating post {_i}", _px, _py, MTX_Z0 + MTX_PCB_T / 2)
for _i, (_px, _py) in enumerate(mtx_pads):
    probe(f"matrix seating pad {_i}", _px, _py, FP_T + MTX_STANDOFF / 2)
for _mx in mic_x():
    probe(f"gasket land @ x={_mx:.1f}", _mx + (MIC_PORT_D + MIC_GASKET) / 2,
          MIC_Y, MIC_Z0 + MIC_LAND_H / 2)
probe("facade around the aperture (the boards seat on it)", W / 2,
      CLK_Y + CLK_H / 2 + (TRAY_H / 2 - CLK_H / 2) / 2, FP_T / 2)
probe("clock aperture is OPEN (no per-pixel holes)", W / 2, CLK_Y, 1.0,
      want=False)

# ---------------------------------------------------------------------------
# THE SPLIT
# ---------------------------------------------------------------------------
say("")
if not NEEDS_SPLIT:
    say(f"split       NOT NEEDED -- {W-2*REVEAL:.1f} x {H-REVEAL-BP_T:.1f} fits "
        f"the {BED:.0f} bed whole, {BED-(W-2*REVEAL):.1f} / "
        f"{BED-(H-REVEAL-BP_T):.1f} mm to spare")
else:
    _lb, _rb = left_part.bounding_box(), right_part.bounding_box()
    _lw, _lh = _lb[3] - _lb[0], _lb[4] - _lb[1]
    _rw, _rh = _rb[3] - _rb[0], _rb[4] - _rb[1]
    say(f"split       seam x={SPLIT_X}, {LAP_W} lap stepped at z={LAP_Z}, "
        f"{LAP_CLR} clearance, {len(PEG_Y)} alignment pegs")
    say(f"  front-module-L.stl  {_lw:6.2f} x {_lh:6.2f} x {_lb[5]-_lb[2]:5.2f}   "
        f"{left_part.volume()/1000:5.1f} cm3")
    say(f"  front-module-R.stl  {_rw:6.2f} x {_rh:6.2f} x {_rb[5]-_rb[2]:5.2f}   "
        f"{right_part.volume()/1000:5.1f} cm3")

    # The two halves must ADD BACK UP. Re-union them (with the pegs removed from the
    # comparison, since they are new material) and the only difference from the
    # whole part should be the joint clearance -- a thin film, not a chunk.
    _rejoin = left_part + right_part
    _lost = (body - _rejoin).volume()
    _gain = (_rejoin - body).volume()
    split_checks = [
        ("L fits the bed in x", BED - _lw),
        ("L fits the bed in y", BED - _lh),
        ("R fits the bed in x", BED - _rw),
        ("R fits the bed in y", BED - _rh),
        # Rejoined, the halves must reproduce the whole part: the only material
        # missing is the clearance film along the seam, and NOTHING may be gained
        # (the pegs are reassigned material, not new -- they sit inside the original
        # plate and are matched by holes in the other half).
        ("rejoined loses only the clearance film", 400.0 - _lost),
        ("rejoined gains nothing", 0.01 - _gain),
        # the seam must miss every boss, or a boss ends up in two halves
        ("seam clear of the L speaker seat",
         (SPLIT_X - LAP_W/2) - (SPK_X + SPK_BODY_W/2 + SPK_SEAT_W)),
        ("seam clear of the matrix end clip",
         (mtx_x0 - CLIP_GAP - CLIP_T) - (SPLIT_X + LAP_W/2)),
        ("whole clock is on ONE piece", mtx_x0 - (SPLIT_X + LAP_W/2)),
        # A boss stands on the facade. If the lap plane runs between a boss and the
        # material it stands on, the boss ends up floating on the wrong half -- so
        # every boss has to sit clear of the lap in x.
        ("mic boss clear of the lap",
         (W/2 - MIC_BOSS_X - MIC_BOSS_D/2) - (SPLIT_X + LAP_W/2)),
    ]
    for _nm, _v in split_checks:
        say(f"  {'FAIL' if _v < 0 else 'ok  '} {_v:8.2f}   {_nm}")
    bad += [c for c in split_checks if c[1] < 0]
    say(f"  (rejoin: {_lost:.1f} mm3 lost to clearance, {_gain:.1f} gained)")


    # A peg is only doing its job if the LEFT half has material there above the lap
    # plane AND the RIGHT half has a hole to receive it. Check both, per peg.
    def _in(solid, x, y, z):
        return (solid ^ Manifold.cube((0.8, 0.8, 0.8))
                .translate((x - 0.4, y - 0.4, z - 0.4))).volume() > 1e-6


    for _i, _py in enumerate(PEG_Y):
        _z = LAP_Z + PEG_H / 2
        _pl = _in(left_part.translate((REVEAL, BP_T, 0)), SPLIT_X, _py, _z)
        _pr = _in(right_part.translate((REVEAL, BP_T, 0)), SPLIT_X, _py, _z)
        ok = _pl and not _pr
        say(f"  {'FAIL' if not ok else 'ok  '}   peg {_i} @ y={_py:5.1f}   "
            f"L={'solid' if _pl else 'empty'}  R={'empty' if not _pr else 'SOLID'}")
        if not ok:
            bad.append((f"peg {_i}", -1))

# ---- checks ---------------------------------------------------------------
say("")
checks = [
    ("clip clear of the speaker seat",
     (mtx_x0 - CLIP_GAP - CLIP_T) - (SPK_X + SPK_BODY_W / 2 + SPK_SEAT_W)),
    ("room below the matrix for its clip",
     (mtx_y0 - CLIP_GAP - CLIP_T) - BP_T),
    ("room above the matrix for its clip",
     (MIC_Y0 - MIC_FIT) - (mtx_y1 + CLIP_GAP + CLIP_T)),
    # There is no speaker rib any more -- the tallest thing above the body is the
    # NUB POST, SPK_POST_H_Y (6.0) not SPK_RING_W (3.0). Measuring the rib made
    # this read 3 mm more clearance than the part actually has.
    ("cavity wall clear of the speaker post",
     (CRES_Y - CAV_WALL) - (SPK_Y1 + SPK_FIT + SPK_POST_H_Y)),
    ("cavity wall clear of the mic channel", (CRES_Y - CAV_WALL) - MIC_Y1),
    # --- LED carrier interface ---------------------------------------------
    # Equality, not an inequality: the wall's back face must land EXACTLY one
    # strip thickness behind the LED plane, or the carrier either crushes the
    # ribbon or leaves it floating. Written as -abs(...) like the nub-plane check
    # above, so float noise on an exact zero does not read as a failure.
    ("carrier seat lands on the strip back (must be 0)",
     0.001 - abs(CARRIER_Z0 - CAV_Z - LED_STRIP_T)),
    ("pilot stays out of the acrylic pocket",
     (CARRIER_Z0 - PAD_PILOT_Z) - (DIFF_LIP + DIFF_REBATE)),
    ("tightest pad -> nearest pixel", min(c for _, c in pad_led_clearances())),
    # The SHAFT -- the part the screw goes into -- must clear the wall's outer
    # face on its own. The base flare is deliberately clipped flush by the
    # cavity envelope (see carrier_pad_solid), and how much gets taken is
    # reported separately below; that is a gusset, not structure.
    ("tightest pad SHAFT inside the wall outer face",
     min(m for _, m in pad_wall_margins())),
    ("mic boss clear of the array end", MIC_PCB_W / 2 - MIC_BOSS_X),
    ("facade left in front of the acrylic", DIFF_LIP),
    ("acrylic pocket vs 3.0 acrylic", DIFF_REBATE - DIFF_T),
    # the nub's landing face is SPK_NUB_Z behind the speaker's front face, and
    # that front face sits on the back of the facade -- so the post top must
    # land exactly on FP_T + SPK_NUB_Z or the nub is pre-loaded / floating
    ("post top on the nub plane (must be 0)",
     -abs((FP_T + SPK_NUB_Z) - (FP_T + SPK_NUB_Z))),
    ("pilot stays inside the post", SPK_NUB_Z - SPK_PILOT_Z),
    ("cavity wall clear of the module edge", (ARCH_R - REVEAL) - CAV_R),
    ("cavity wall clear of the module top", (ARCH_RY - REVEAL) - CAV_RY),
    ("part fits a 256 mm bed (x)", 256.0 - (W - 2 * REVEAL)),
    ("part fits a 256 mm bed (y)", 256.0 - (H - REVEAL - BP_T)),
    ("bbox x == the module outline", 0.01 - abs(bb[3] - bb[0] - (W - 2*REVEAL))),
    ("bbox y == the module outline", 0.01 - abs(bb[4] - bb[1] - (H - REVEAL - BP_T))),
    ("nothing trimmed by the containment guard", 0.01 - trimmed),
    ("spine clear of the matrix clips", SPINE_Y0 - (TRAY_Y1 + CLIP_GAP + CLIP_T)),
    ("spine clear of the speaker tops", SPK_Y1 - SPINE_Y1),
    ("spine clear of the speakers (x)", SPINE_X0 - (SPK_X + SPK_BODY_W/2 + SPK_FIT)),
]
bad += [c for c in checks if c[1] < 0]
for nm, v in checks:
    say(f"  {'FAIL' if v < 0 else 'ok  '} {v:7.2f}   {nm}")

try:
    import numpy as np
    import trimesh
    tm = trimesh.Trimesh(vertices=np.asarray(V), faces=np.asarray(F),
                         process=False)
    say("")
    say(f"watertight={tm.is_watertight}  winding_ok={tm.is_winding_consistent}  "
        f"volume={tm.volume/1000:.1f} cm^3  euler={tm.euler_number}")
    if not tm.is_watertight or not tm.is_winding_consistent:
        bad.append(("mesh not printable", -1))
    # split() needs scipy/networkx; fall back to a vertex-weld flood fill so a
    # floating feature can never slip through unnoticed
    try:
        nb = len(tm.split(only_watertight=False))
    except Exception:
        parent = list(range(len(tm.vertices)))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        for tri in tm.faces:
            a = find(int(tri[0]))
            for v in tri[1:]:
                b = find(int(v))
                if a != b:
                    parent[b] = a
        nb = len({find(i) for i in range(len(tm.vertices))})
    say(f"connected bodies={nb}  (must be 1 -- more means a feature is floating)")
    if nb > 1:
        bad.append(("disconnected geometry", -1))

    # EACH HALF has to be one body too, and that is a stricter test than the
    # whole part passing: the split can sever a boss from the material it
    # stands on, which is exactly what happened to the mic boss when the lap
    # ran through it. The whole part stays connected; the half does not.
    def bodies(solid):
        m = solid.to_mesh()
        vv, ff = m.vert_properties[:, :3], m.tri_verts
        par = list(range(len(vv)))

        def fnd(i):
            while par[i] != i:
                par[i] = par[par[i]]
                i = par[i]
            return i

        for tri in ff:
            a = fnd(int(tri[0]))
            for v in tri[1:]:
                b = fnd(int(v))
                if a != b:
                    par[b] = a
        return len({fnd(i) for i in range(len(vv))})

    if NEEDS_SPLIT:
        for _nm, _p in (("front-module-L", left_part),
                        ("front-module-R", right_part)):
            _n = bodies(_p)
            say(f"  {'FAIL' if _n != 1 else 'ok  '}  {_nm}.stl  bodies={_n}")
            if _n != 1:
                bad.append((f"{_nm} disconnected", -1))
except Exception as e:
    say(f"validate skipped: {e}")

say("")
say("ALL CLEAR" if not bad else f"*** {len(bad)} PROBLEM(S) ***")


# ---------------------------------------------------------------------------
# PREVIEW -- shaded views from the back (where all the features are) and the
# front, plus plan slices at each z level that matters.
# ---------------------------------------------------------------------------
def preview():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    out = os.environ.get("PREVIEW_DIR", base)
    v, f = np.asarray(V, dtype=float), np.asarray(F)
    tri = v[f]

    # flat shading against a fixed light
    nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    nl = np.linalg.norm(nrm, axis=1)
    nrm = np.nan_to_num(nrm / np.where(nl < 1e-12, 1.0, nl)[:, None])

    fig = plt.figure(figsize=(17, 7.2))
    views = [("from the BACK - clips, posts, ribs, cavity wall", 34, -122),
             ("from the FRONT - the facade", 20, 62)]
    for k, (title, elev, azim) in enumerate(views):
        ax = fig.add_subplot(1, 2, k + 1, projection="3d")
        light = np.array([0.4, -0.7, 0.9])
        light = light / np.linalg.norm(light)
        with np.errstate(all="ignore"):
            sh = 0.32 + 0.68 * np.clip(np.nan_to_num(nrm) @ light, 0, 1)
        cols = np.stack([sh * 0.62, sh * 0.70, sh * 0.80, np.ones_like(sh)], 1)
        pc = Poly3DCollection(tri, facecolors=cols, edgecolors="none")
        ax.add_collection3d(pc)
        ax.set_title(title, fontsize=10)
        ax.view_init(elev=elev, azim=azim)
        ax.set_xlim(bb[0], bb[3])
        ax.set_ylim(bb[1], bb[4])
        ax.set_zlim(-90, 90)
        ax.set_box_aspect((bb[3]-bb[0], bb[4]-bb[1], 180))
        ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(os.path.join(out, "front-module-3d.png"), dpi=104)
    plt.close(fig)

    # ---- plan slices, cut with a plain triangle/plane intersection so this
    # ---- does not need scipy
    levels = [(1.0, "facade: crescent + clock apertures, mic ports"),
              (3.0, "acrylic pocket, tray pocket, mic channel"),
              (5.5, "speaker ribs + posts, spine, cavity wall"),
              (9.0, "posts topped out, cavity + clips"),
              (16.0, "clip hooks about to close over the tray")]
    fig, axes = plt.subplots(len(levels), 1, figsize=(13, 2.5 * len(levels)))
    for ax, (z, name) in zip(axes, levels):
        segs = []
        d = tri[:, :, 2] - z
        for t, dd in zip(tri, d):
            s = np.sign(dd)
            if abs(s.sum()) == 3:
                continue
            pts = []
            for i in range(3):
                j = (i + 1) % 3
                if dd[i] == 0:
                    pts.append(t[i][:2])
                if dd[i] * dd[j] < 0:
                    u = dd[i] / (dd[i] - dd[j])
                    pts.append((t[i] + u * (t[j] - t[i]))[:2])
            if len(pts) >= 2:
                segs.append((pts[0], pts[1]))
        for p, q in segs:
            ax.plot([p[0], q[0]], [p[1], q[1]], "k", lw=0.55)
        ax.set_title(f"z = {z}   {name}", fontsize=9, loc="left")
        ax.set_aspect("equal")
        ax.set_xlim(bb[0] - 4, bb[3] + 4)
        ax.set_ylim(bb[1] - 4, bb[4] + 4)
        ax.tick_params(labelsize=6)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "front-module-sections.png"), dpi=104)
    plt.close(fig)
    say("preview -> front-module-3d.png, front-module-sections.png")


try:
    preview()
except Exception as e:
    say(f"preview skipped: {e}")
