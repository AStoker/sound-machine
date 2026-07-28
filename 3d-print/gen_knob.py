#!/usr/bin/env python3
"""KNOB — PART 5. The pebble that caps the seesaw encoder shaft.

An ellipse of revolution truncated by a shallow cut at the bottom, so only a
KNOB_BASE_D flat meets the crown. The widest point is part-way up, not at the
base — that is what makes it read as a pebble rather than a cone, and it is what
gives your fingers something to pull against when you turn it.

    PRINT BASE DOWN, NO SUPPORTS. The flat cut is the bed. Everything above it
    leans outward to the equator and then back in, so the only overhang worth
    checking is at the very first layer, where the ellipse is steepest. This run
    computes that angle and fails if it exceeds OVERHANG_LIMIT.

>>> THE BORE IS A D, NOT A CIRCLE, AND IT IS BLIND. The seesaw's shaft is a 6 mm
>>> D-shaft; a round bore would spin. It stops KNOB_BORE_H up so the top of the
>>> pebble stays solid — a through bore would show the shaft end on the one
>>> surface you look down at.

Geometry comes from enclosure_geom.py. Nothing here re-derives a dimension the
dome also depends on: the boss the knob sits on, the shaft bore and the knob
profile all come from the same constants.

    python3 gen_knob.py     ->  models/knob.stl
"""
import math
import os
import struct

from manifold3d import CrossSection, Manifold

from enclosure_geom import (
    KNOB_BASE_D, KNOB_BORE_D, KNOB_BORE_F, KNOB_BORE_H, KNOB_BOSS_D,
    KNOB_D, KNOB_H, MODEL_DIR, knob_ellipse,
)

SEG = 128
BED = 220.0
OVERHANG_LIMIT = 50.0     # degrees from vertical, before support is needed

# --- print parameters -------------------------------------------------------
BORE_FIT   = 0.25         # per side, bore to shaft -- a press fit, not a clearance
BASE_CHAMF = 0.5          # break on the base edge, so it does not scuff the crown
GRIP_N     = 0            # optional flutes; 0 = plain pebble (see the note below)

_out = []


def say(s):
    _out.append(s)
    print(s)


# ---------------------------------------------------------------------------
# BODY -- a solid of revolution, built as a lathe profile
# ---------------------------------------------------------------------------
A, B, YC, W0 = knob_ellipse()     # semi-axes, centre above the base, base radius

# >>> REVOLVE A PROFILE, DO NOT STACK DISCS. An ellipsoid built from a stack of
# >>> cylinders is faceted in Z as well as around, and the facets land on the one
# >>> surface anybody actually touches. CrossSection.revolve() sweeps the exact
# >>> outline instead, so the only faceting is the angular one SEG controls.
prof = [(0.0, 0.0)]                        # start on the axis, at the base
n_pts = 96
for i in range(n_pts + 1):
    # walk the ellipse from the base cut up and over the top
    y = -YC + (YC + B) * i / n_pts         # ellipse-local y, base cut -> apex
    r = A * math.sqrt(max(1.0 - (y / B) ** 2, 0.0))
    prof.append((r, y + YC))               # part-local: base cut at z=0
prof.append((0.0, KNOB_H))                 # close on the axis at the apex

body = CrossSection([prof]).revolve(circular_segments=SEG)

# --- the D-shaft bore -------------------------------------------------------
# Blind, from the base up. Round bore of KNOB_BORE_D with one side flattened to
# KNOB_BORE_F, matching the shaft.
bore_d = KNOB_BORE_D + 2 * BORE_FIT
flat_f = KNOB_BORE_F + 2 * BORE_FIT
bore = Manifold.cylinder(KNOB_BORE_H, bore_d / 2, bore_d / 2, SEG)
# chop the D-flat: keep everything on one side of a plane at flat_f from the far
# wall, i.e. a slab from -bore_d/2 to (flat_f - bore_d/2)
keep = Manifold.cube((bore_d + 2, bore_d + 2, KNOB_BORE_H + 2), True) \
    .translate((0.0, (flat_f - bore_d / 2) / 2 - (bore_d + 2) / 2 + (bore_d + 2) / 2, 0.0))
slab_lo = -bore_d / 2 - 1.0
slab_hi = flat_f - bore_d / 2
keep = Manifold.cube((bore_d + 2, slab_hi - slab_lo, KNOB_BORE_H + 2)) \
    .translate((-(bore_d + 2) / 2, slab_lo, -1.0))
bore = bore ^ keep
body = body - bore.translate((0.0, 0.0, -0.5))     # break out through the base

# --- base edge break --------------------------------------------------------
# A 45 deg chamfer, cut as a cone -- self-supporting and it keeps the knob from
# scuffing the crown boss as it is pushed on.
cham = Manifold.cylinder(BASE_CHAMF, W0 + BASE_CHAMF, W0, SEG)
body = body - (Manifold.cylinder(BASE_CHAMF, W0 + 8, W0 + 8, SEG)
               .translate((0, 0, 0.0)) - cham)

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


nf = write_stl(body, "knob.stl")
bb = body.bounding_box()

say(f"wrote models/knob.stl   {nf} triangles")
say(f"bbox        {bb[3]-bb[0]:.2f} x {bb[4]-bb[1]:.2f} x {bb[5]-bb[2]:.2f} mm")
say(f"pebble      {chr(216)}{KNOB_D} widest, {KNOB_H} tall, on a "
    f"{chr(216)}{KNOB_BASE_D} base flat")
say(f"ellipse     semi-axes {A:.2f} x {B:.2f}, centre {YC:.2f} above the base")
say(f"bore        {chr(216)}{bore_d:.2f} with a {flat_f:.2f} D-flat, "
    f"{KNOB_BORE_H} deep, BLIND")
say(f"seats on    the {chr(216)}{KNOB_BOSS_D} flat boss on the crown")
say("")

bad = []


def chk(name, v, lo=0.0):
    ok = v >= lo - 1e-6
    say(f"  {'ok  ' if ok else 'FAIL'} {v:8.2f}   {name}")
    if not ok:
        bad.append(name)


say("clearances and printability")
# The steepest overhang is at the base cut, where the ellipse leans out hardest.
# dr/dz there, converted to an angle from vertical.
slope = (A * A * YC) / (B * B * W0)          # |dr/dz| at the base cut
ang = math.degrees(math.atan(slope))
say(f"  ---- {ang:8.2f}   base overhang, degrees from vertical")
chk("base overhang within the support-free limit", OVERHANG_LIMIT - ang)
chk("bore does not break through the top", KNOB_H - KNOB_BORE_H - 1.0)
chk("material around the bore at the base", W0 - bore_d / 2 - 1.0)
# >>> COMPARE THE BORE TO THE SHAFT, NOT TO THE SHELL'S CLEARANCE HOLE.
# >>> ENC_SHAFT_D (7.0) is the hole through the CROWN that the shaft passes
# >>> through; the shaft itself is KNOB_BORE_D (6.0). Checking the knob's bore
# >>> against the shell hole compares two things that never touch and happened to
# >>> read exactly 0.00 -- a passing number that meant nothing.
chk("bore takes the shaft with a press fit", bore_d - KNOB_BORE_D)
# >>> THE BOSS IS BIGGER THAN THE KNOB BASE ON PURPOSE, and the first version of
# >>> this check asserted the reverse. If the boss were smaller, the knob's rim
# >>> would overhang the CURVED crown and leave a gap that varies all the way
# >>> round. Larger means the knob always lands on flat material, and what shows
# >>> is a clean concentric ring.
chk("crown boss is at least as big as the knob base",
    KNOB_BOSS_D - KNOB_BASE_D)
chk("...but not so much bigger that it reads as a collar",
    4.0 - (KNOB_BOSS_D - KNOB_BASE_D))
chk("fits the bed (x)", BED - (bb[3] - bb[0]))
chk("fits the bed (z)", BED - (bb[5] - bb[2]))
chk("widest point is ABOVE the base (it is a pebble, not a cone)",
    KNOB_D - KNOB_BASE_D)

try:
    import trimesh
    tm = trimesh.load(os.path.join(MODEL_DIR, "knob.stl"))
    n_bodies = len(tm.split(only_watertight=False))
    say("")
    say(f"watertight={tm.is_watertight}  winding_ok={tm.is_winding_consistent}  "
        f"volume={tm.volume/1000:.2f} cm^3")
    say(f"connected bodies={n_bodies}  (must be 1)")
    if not tm.is_watertight:
        bad.append("not watertight")
    if n_bodies != 1:
        bad.append(f"{n_bodies} disconnected bodies")
except ImportError:
    say("validate skipped: no trimesh")

say("")
say("ALL CLEAR" if not bad else f"*** {len(bad)} PROBLEM(S) ***")
