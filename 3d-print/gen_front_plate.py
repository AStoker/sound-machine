#!/usr/bin/env python3
"""FRONT MODULE -- the single printed part that carries the whole facade.

One part, four jobs:
  * CRESCENT   through aperture + a rebate the opal acrylic drops into from
               behind + a cavity wall that sets the diffusion air gap
  * CLOCK      ONE OPEN APERTURE (deliberately no per-pixel holes) and the two
               CharliePlex matrices held directly. THE BOARDS ARE ONLY LOOSELY
               SOLDERED TO EACH OTHER, so each is located by its OWN posts and
               the pair is clamped by six cantilever CLIPS, on all four sides
  * SPEAKERS   grille apertures + locating ribs + a POST beside each flank that
               the speaker's side nub bolts to (these bodies have no baffle bolt
               pattern -- see HARDWARE.md)
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
Outputs front-module.stl (+ section previews).
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
    MTX_STACK_GAP,
    BOSS_EDGE, LIP, REVEAL, RIB_W, R_BOT, SPK_BODY_H, SPK_BODY_W, SPK_GRILLE, SPK_NUB_PROJ,
    SPK_NUB_SCREW, SPK_NUB_Y, SPK_NUB_Z, SPK_POST_WALL, SPK_RING_W, SPK_SEAT_W,
    SPK_FIT, SPK_X, SPK_Y, SPK_Y0, SPK_Y1, TRAY_D, TRAY_H, TRAY_REBATE, TRAY_W, TRAY_Y0,
    TRAY_Y1, W, mic_x,
)

SEG = 96              # facets on the big arcs -- this part is 245 mm wide
# ---------------------------------------------------------------------------
# PRINT PARAMETERS -- the things a drawing does not fix. Tune these, not the
# imported geometry.
# ---------------------------------------------------------------------------
DIFF_LIP    = 1.5     # facade left in FRONT of the acrylic (the visible rebate)
CAV_Z       = DIFF_LIP + DIFF_REBATE + DIFF_GAP    # back face of the cavity wall
DIFF_R      = CRES_R + DIFF_MARGIN                 # acrylic pocket radius
CAV_R       = DIFF_R + CAV_WALL                    # cavity outer wall

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
MIC_BOSS_X  = 50.0    # (?) from centre -- Seeed does not publish the hole
MIC_PILOT_D = 2.5     #     positions. MEASURE before printing.
# --- stiffening -------------------------------------------------------------
RIB_H       = 5.0     # general stiffening rib height
RIB_T       = 2.0

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


def half_disc(cx, cy, r, skirt=0.0):
    """Upper half of a circle -- the crescent shape, flat side DOWN at cy.
    `skirt` extends the flat side downward, which is how the cavity wall gets
    a bottom to close against."""
    pts = [(cx + r, cy)]
    for i in range(1, SEG):
        t = math.pi * i / SEG
        pts.append((cx + r * math.cos(t), cy + r * math.sin(t)))
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
    r = ARCH_R - REVEAL
    rb = max(R_BOT - REVEAL, 0.8)          # bottom corners
    pts = [(x0 + rb, yb)]
    for i in range(9):                     # bottom-right corner
        t = -math.pi / 2 + (math.pi / 2) * i / 8
        pts.append((x1 - rb + rb * math.cos(t), yb + rb + rb * math.sin(t)))
    pts.append((x1, ys))
    for i in range(1, SEG):                # the arc
        t = math.pi * i / SEG
        pts.append((W / 2 + r * math.cos(t), ys + r * math.sin(t)))
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
cav_wall = (half_disc(W / 2, CRES_Y, CAV_R, skirt=CAV_WALL)
            - half_disc(W / 2, CRES_Y, DIFF_R))
body = body + slab(cav_wall, 0.0, CAV_Z)

cuts = []
cuts.append(slab(half_disc(W / 2, CRES_Y, DIFF_R), DIFF_LIP, CAV_Z + 1))
cuts.append(slab(half_disc(W / 2, CRES_Y, CRES_R), -1.0, DIFF_LIP))

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

# --- speaker locating ribs (top and bottom only) ----------------------------
# NOT a full corral: the side nubs stick out 4 mm at mid-height, so a rib down
# the flanks would foul them. Top+bottom ribs locate in y, the two posts locate
# in x, and that is the whole job.
for sx in (SPK_X, W - SPK_X):
    rw = SPK_BODY_W + 2 * SPK_FIT + 2 * SPK_RING_W
    for yr in (SPK_Y0 - SPK_FIT - SPK_RING_W, SPK_Y1 + SPK_FIT):
        adds.append(slab(rect2(sx - rw / 2, yr, rw, SPK_RING_W),
                         FP_T, FP_T + SPK_RIB_H))
    # --- the side-nub posts -------------------------------------------------
    # The nub lands SPK_NUB_Z behind the speaker's front face, and the front
    # face sits on the back of the facade -- so the post top is at FP_T+NUB_Z
    # and the screw goes in FROM BEHIND, through the nub, into the post.
    pw = SPK_NUB_PROJ + SPK_POST_WALL
    for sgn in (-1, 1):
        px = sx + sgn * (SPK_BODY_W / 2 + SPK_FIT + pw / 2)
        adds.append(slab(rect2(px - pw / 2, SPK_NUB_Y - SPK_BODY_H * 0.30,
                               pw, SPK_BODY_H * 0.60),
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
SPINE_Y0 = SPK_Y1 + SPK_FIT
SPINE_Y1 = CRES_Y - CAV_WALL - 2.0
adds.append(slab(rect2(REVEAL + BOSS_EDGE, SPINE_Y0,
                       W - 2 * (REVEAL + BOSS_EDGE), SPINE_Y1 - SPINE_Y0),
                 FP_T, FP_T + RIB_H))
#  2. Short ribs INBOARD from each speaker towards the tray. Outboard there is
#     no room -- an earlier version ran them out past the module edge.
for sx in (SPK_X, W - SPK_X):
    sgn = 1 if sx < W / 2 else -1
    x0 = sx + sgn * (SPK_BODY_W / 2 + SPK_SEAT_W)
    x1 = sx + sgn * (SPK_BODY_W / 2 + SPK_SEAT_W + 11.0)
    adds.append(slab(rect2(min(x0, x1), SPK_Y - RIB_T / 2,
                           abs(x1 - x0), RIB_T), FP_T, FP_T + RIB_H))

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
    for sgn in (-1, 1):
        px = sx + sgn * (SPK_BODY_W / 2 + SPK_FIT
                         + (SPK_NUB_PROJ + SPK_POST_WALL) / 2)
        pilots.append(cyl(px, SPK_NUB_Y,
                          FP_T + SPK_NUB_Z - SPK_PILOT_Z, FP_T + SPK_NUB_Z + 1,
                          SPK_PILOT_D))
for sgn in (-1, 1):
    pilots.append(cyl(W / 2 + sgn * MIC_BOSS_X, MIC_Y,
                      MIC_Z0 + 0.8, MIC_Z0 + MIC_CHAN_D + 3, MIC_PILOT_D))
for mxc in mic_x():
    pilots.append(cyl(mxc, MIC_Y, -1.0, MIC_Z0 + MIC_LAND_H + 1, MIC_PORT_D))
body = body - union(pilots)

# ---------------------------------------------------------------------------
# EXPORT
# ---------------------------------------------------------------------------
body = body.translate((-REVEAL, -BP_T, 0.0))        # part origin at its corner
mesh = body.to_mesh()
V, F = mesh.vert_properties[:, :3], mesh.tri_verts
base = os.path.dirname(os.path.abspath(__file__))
buf = bytearray(b"\0" * 80 + struct.pack("<I", len(F)))
for f in F:
    a, b, c = V[f[0]], V[f[1]], V[f[2]]
    ux, uy, uz = b - a
    vx, vy, vz = c - a
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    L = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    buf += struct.pack("<12fH", nx / L, ny / L, nz / L, *a, *b, *c, 0)
open(os.path.join(base, "front-module.stl"), "wb").write(buf)

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
say(f"speakers    grille {chr(216)}{SPK_GRILLE} thru; ribs {SPK_RIB_H} tall; "
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
      slab(half_disc(W / 2, CRES_Y, CRES_R + 0.2), DIFF_LIP,
           DIFF_LIP + DIFF_T))
# the diffusion air gap -- must be clear or it is not a diffusion cavity
clash("diffusion air gap",
      slab(half_disc(W / 2, CRES_Y, CRES_R), DIFF_LIP + DIFF_REBATE, CAV_Z))
# each speaker body, plus the nubs sweeping in from behind
for _sx in (SPK_X, W - SPK_X):
    clash(f"speaker body @ x={_sx:.1f}",
          slab(rect2(_sx - SPK_BODY_W / 2, SPK_Y0, SPK_BODY_W, SPK_BODY_H),
               FP_T, FP_T + 22.0))
    for _sgn in (-1, 1):
        _nx = _sx + _sgn * (SPK_BODY_W / 2)
        clash(f"  side nub @ x={_nx:.1f}",
              slab(rect2(min(_nx, _nx + _sgn * SPK_NUB_PROJ),
                         SPK_NUB_Y - 4.0, SPK_NUB_PROJ, 8.0),
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
    for _sgn, flank in ((-1, "outboard" if side == "L" else "inboard"),
                        (1, "inboard" if side == "L" else "outboard")):
        _px = _sx + _sgn * (SPK_BODY_W / 2 + SPK_FIT
                            + (SPK_NUB_PROJ + SPK_POST_WALL) / 2)
        probe(f"speaker {side} {flank} post", _px, SPK_NUB_Y, FP_T + 1.0)
    probe(f"speaker {side} bottom locating rib", _sx,
          SPK_Y0 - SPK_FIT - SPK_RING_W / 2, FP_T + 2.0)
    probe(f"speaker {side} top locating rib", _sx,
          SPK_Y1 + SPK_FIT + SPK_RING_W / 2, FP_T + 2.0)
probe("stiffening spine", W / 2, (SPINE_Y0 + SPINE_Y1) / 2, FP_T + 2.0)
probe("cavity wall at the apex", W / 2, CRES_Y + DIFF_R + CAV_WALL / 2, CAV_Z - 1)
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

# ---- checks ---------------------------------------------------------------
say("")
checks = [
    ("clip clear of the speaker seat",
     (mtx_x0 - CLIP_GAP - CLIP_T) - (SPK_X + SPK_BODY_W / 2 + SPK_SEAT_W)),
    ("room below the matrix for its clip",
     (mtx_y0 - CLIP_GAP - CLIP_T) - BP_T),
    ("room above the matrix for its clip",
     (MIC_Y0 - MIC_FIT) - (mtx_y1 + CLIP_GAP + CLIP_T)),
    ("cavity wall clear of the speaker rib",
     (CRES_Y - CAV_WALL) - (SPK_Y1 + SPK_FIT + SPK_RING_W)),
    ("cavity wall clear of the mic channel", (CRES_Y - CAV_WALL) - MIC_Y1),
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
    ("part fits a 256 mm bed (x)", 256.0 - (W - 2 * REVEAL)),
    ("part fits a 256 mm bed (y)", 256.0 - (H - REVEAL - BP_T)),
    ("bbox x == the module outline", 0.01 - abs(bb[3] - bb[0] - (W - 2*REVEAL))),
    ("bbox y == the module outline", 0.01 - abs(bb[4] - bb[1] - (H - REVEAL - BP_T))),
    ("nothing trimmed by the containment guard", 0.01 - trimmed),
    ("spine clear of the mic channel", SPINE_Y0 - (MIC_Y1 + MIC_FIT)),
    ("spine clear of the cavity wall", (CRES_Y - CAV_WALL) - SPINE_Y1),
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
