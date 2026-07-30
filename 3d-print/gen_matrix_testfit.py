#!/usr/bin/env python3
"""MATRIX MOUNT TEST COUPON — print this before you print the front module.

A ~102 x 44 x 12 tile carrying the clock mount and nothing else: the recessed
aperture lip, the pocket, the four locating posts and all six retaining clips.
Twenty minutes of filament instead of several hours, so the fit can be wrong
cheaply.

    python3 gen_matrix_testfit.py   ->  models/matrix-testfit.stl

>>> IT IS CUT OUT OF THE REAL PART, NOT REBUILT TO MATCH IT. The obvious way to
>>> write this file is to re-create the lip, posts and clips from the same
>>> constants. That produces a coupon that tests A DIFFERENT PART: the moment
>>> anything in gen_front_plate.py changes -- a clip root, a pocket margin, an
>>> inset -- the copy silently stops representing it, and a test print that
>>> passes tells you nothing about the thing you are going to print.
>>> So this executes gen_front_plate.py and INTERSECTS its finished solid with a
>>> box. Whatever the front module really has in that region is what you get,
>>> including any mistake in it -- which is the entire point of a test print.

    PRINT FACE DOWN, same as the front module: the facade is the bed face, the
    posts and clips grow upward, nothing needs support. Use the SAME layer
    height and the same material you will use for the real part -- the clips are
    a 1.4 % strain design and layer adhesion is what carries it.
"""
import importlib.util
import math
import os
import struct
import sys

from manifold3d import Manifold

HERE = os.path.dirname(os.path.abspath(__file__))

# --- how much plate to keep around the mount --------------------------------
RIM = 6.0        # full-thickness border outside the pocket, to hold and to
                 #   stop the coupon curling off the bed
Z_HEAD = 3.0     # air above the tallest clip

_out = []


def say(s):
    _out.append(s)
    print(s)


# ---------------------------------------------------------------------------
# BUILD -- by running the real generator and taking a bite out of it
# ---------------------------------------------------------------------------
say("running gen_front_plate.py to get the actual part...")
_spec = importlib.util.spec_from_file_location(
    "_fp", os.path.join(HERE, "gen_front_plate.py"))
_fp = importlib.util.module_from_spec(_spec)
_stdout = sys.stdout
try:
    sys.stdout = open(os.devnull, "w")       # its own report, not ours
    _spec.loader.exec_module(_fp)
finally:
    sys.stdout.close()
    sys.stdout = _stdout

full = _fp.part_body                          # assembly coordinates
say(f"  front module built: {full.num_tri()} triangles, "
    f"{full.volume()/1000:.1f} cm^3")

# the window we keep: the board pair, its pocket, and RIM of plate all round
X0 = _fp.MTX_X0 - _fp.MTX_POCKET - RIM
Y0 = _fp.TRAY_Y0 - _fp.MTX_POCKET - RIM
CW = _fp.TRAY_W + 2 * (_fp.MTX_POCKET + RIM)
CH = _fp.TRAY_H + 2 * (_fp.MTX_POCKET + RIM)
CD = _fp.BP_ZB + _fp.CLIP_STACK_CLR + _fp.CLIP_RUN + _fp.CLIP_RAMP \
    + _fp.CLIP_TAIL + Z_HEAD

box = Manifold.cube((CW, CH, CD)).translate((X0, Y0, 0.0))
body = full ^ box

# >>> ...AND THEN CHECK THE BITE ACTUALLY CONTAINS THE FEATURES. An intersection
# >>> always succeeds; it just returns less. Get the window wrong and this file
# >>> cheerfully exports a rectangle of blank facade that prints beautifully and
# >>> proves nothing.
bad = []


def want(name, ok):
    say(f"  {'ok  ' if ok else 'FAIL'}  {name}")
    if not ok:
        bad.append(name)


def solid_at(x, y, z, size=0.25):
    return (body ^ Manifold.cube((size, size, size))
            .translate((x - size / 2, y - size / 2, z - size / 2))).volume() > 1e-9


say("")
say("the coupon must contain every feature the real part has here")
for _i, (_px, _py) in enumerate(_fp.mtx_posts):
    want(f"locating post {_i}", solid_at(_px, _py, _fp.MTX_Z0 + _fp.MTX_PCB_T / 2))
_face = _fp.TRAY_Y0 + _fp.TRAY_H
_hook_z = _fp.BP_ZB + _fp.CLIP_STACK_CLR + _fp.CLIP_RUN * 0.95
for _i, _cx in enumerate(_fp.CLIP_TOP_X):
    want(f"top clip {_i} hook",
         solid_at(_cx, _face - _fp.CLIP_ENGAGE / 2, _hook_z, _fp.CLIP_ENGAGE / 3))
for _i, _cx in enumerate(_fp.CLIP_BOT_X):
    want(f"bottom clip {_i} hook",
         solid_at(_cx, _fp.TRAY_Y0 + _fp.CLIP_ENGAGE / 2, _hook_z,
                  _fp.CLIP_ENGAGE / 3))
# >>> AND THE ENDS MUST STAY EMPTY. There are deliberately no end clips: the
# >>> driver's STEMMA QT ports are on the short edges. Assert the absence, so a
# >>> clip cannot quietly come back and block the cables.
_ymid = _fp.TRAY_Y0 + _fp.TRAY_H / 2
want("left end is CLEAR for the STEMMA QT cable",
     not solid_at(_fp.MTX_X0 - 0.6, _ymid, _hook_z, 0.4))
want("right end is CLEAR for the STEMMA QT cable",
     not solid_at(_fp.MTX_X0 + _fp.TRAY_W + 0.6, _ymid, _hook_z, 0.4))
# >>> PER-PIXEL WINDOWS NOW, not one open aperture. Check a WINDOW is open and a
# >>> WEB is solid: either alone is satisfiable by the wrong geometry (a fully
# >>> open hole passes the first, a blank sheet passes the second). The pair is
# >>> what says a grid was actually cut.
_leds = _fp.led_xy
want("an LED window is open through the lip",
     not solid_at(_leds[0][0], _leds[0][1], _fp.MTX_INSET / 2, 0.3))
want("the web between two windows is solid",
     solid_at((_leds[0][0] + _leds[_fp.MTX_LED_ROWS][0]) / 2, _leds[0][1],
              _fp.MTX_INSET / 2, 0.3))
# >>> THE PIN GUTTERS ARE THE WHOLE POINT OF THIS REPRINT, so the coupon has to
# >>> prove it carries them. Three probes again: open behind the facade, NOT open
# >>> through it, and each post still standing on its pedestal -- a gutter that ate
# >>> a post base gives you a loose pin in the pocket on assembly, not at print.
_gz_mid = _fp.MTX_INSET - _fp.MTX_GUTTER_D / 2
for _i, (_gy0, _gy1) in enumerate(_fp.MTX_GUTTERS):
    _nm = "bottom" if _i == 0 else "top"
    _gy = (_gy0 + _gy1) / 2
    want(f"{_nm} pin gutter is open", not solid_at(
        _fp.MTX_X0 + _fp.TRAY_W / 2, _gy, _gz_mid, 0.3))
    want(f"{_nm} pin gutter has not broken through the facade", solid_at(
        _fp.MTX_X0 + _fp.TRAY_W / 2, _gy,
        (_fp.MTX_INSET - _fp.MTX_GUTTER_D) / 2, 0.2))
for _i, (_px, _py) in enumerate(_fp.mtx_posts):
    want(f"post {_i} pedestal is solid under it", solid_at(_px, _py, _gz_mid, 0.3))

want("facade lip is present outside the LED field",
     solid_at(_fp.MTX_X0 + 0.8, _fp.TRAY_Y0 + 0.8, _fp.MTX_INSET / 2))
want("pocket floor is at the inset, not the back face",
     not solid_at(_fp.W / 2 - _fp.CLK_W / 2 - 1.0, _fp.CLK_Y,
                  _fp.MTX_INSET + 0.5))
want("coupon has a solid rim to hold",
     solid_at(X0 + RIM / 2, Y0 + RIM / 2, _fp.FP_T / 2))

# ---------------------------------------------------------------------------
# EXPORT
# ---------------------------------------------------------------------------
body = body.translate((-X0, -Y0, 0.0))        # corner to the origin


def write_stl(solid, name):
    m = solid.to_mesh()
    V, F = m.vert_properties[:, :3], m.tri_verts
    with open(os.path.join(_fp.MODEL_DIR, name), "wb") as f:
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


nf = write_stl(body, "matrix-testfit.stl")
bb = body.bounding_box()
say("")
say(f"wrote models/matrix-testfit.stl   {nf} triangles")
say(f"coupon      {bb[3]-bb[0]:.1f} x {bb[4]-bb[1]:.1f} x {bb[5]-bb[2]:.1f} mm, "
    f"{body.volume()/1000:.1f} cm^3")
say(f"            (the front module is {full.volume()/1000:.1f} cm^3 -- "
    f"{full.volume()/body.volume():.0f}x this)")
say("")
say("what it is testing")
say(f"  recess      matrix front face {_fp.MTX_INSET} mm behind the facade")
say(f"  windows     {len(_fp.led_xy)} squares {_fp.MTX_WINDOW} x {_fp.MTX_WINDOW}, "
    f"web {_fp.MTX_LED_PITCH - _fp.MTX_WINDOW:.2f} mm")
say(f"  lip         board seats on the back of the {_fp.MTX_INSET} mm aperture lip")
say(f"  gutters     {len(_fp.MTX_GUTTERS)} x {_fp.MTX_GUTTER_D:.2f} deep along the "
    f"long edges, for the trimmed header pins")
say(f"              (assumes the pins stand {_fp.MTX_PIN_H} mm above the LED-side")
say(f"               PCB face -- MEASURE THIS, it sets the inset)")
say(f"  posts       {len(_fp.mtx_posts)} x {chr(216)}{_fp.MTX_POST_D} into the "
    f"boards' own {chr(216)}{_fp.MTX_HOLE_D} diagonal holes")
say(f"  clips       {len(_fp.CLIP_TOP_X)+len(_fp.CLIP_BOT_X)} x {_fp.CLIP_T} thk, "
    f"gripping {_fp.CLIP_ENGAGE} onto the back of the stack at "
    f"z={_fp.BP_ZB:.2f}")
import enclosure_geom as _g
say(f"  stack       assumes {_g.MTX_STACK_H} mm matrix-front to backpack-back "
    f"(measured), header gap {_g.MTX_STACK_GAP:.1f}")
say("")
say("what to check when it comes off the bed")
say("  1. do both boards drop onto their posts without forcing?")
say("     -> if not, MTX_HOLES is on the wrong diagonal (see enclosure_geom)")
say("  2. do the boards sit FLAT on the lip, with no rock?")
say("  3. do the clips snap over the backpack, and hold it when inverted?")
say(f"     -> they should move about {_fp.CLIP_ENGAGE} mm and no more")
say("  4. any clip that whitens, creaks or snaps = too much strain; tell me")
say(f"  5. gap behind the backpack: {_fp.CLIP_STACK_CLR} mm is designed in")
say(f"  6. does the board now sit FLUSH on the lip, with the pins in the gutters?")
say(f"     -> that was the light-bleed cause: pins holding it "
    f"{_fp.MTX_PIN_H} mm off")
say("     -> if it still rocks or stands proud, the pins are longer than "
    f"{_fp.MTX_GUTTER_D:.2f}; tell me the real number")
say("  7. do the STEMMA QT cables clear the ENDS? There are deliberately no")
say("     end clips -- Adafruit puts the ports on the two short edges, and")
say("     gen_tray.py has notched around them since it was written.")
say("")

try:
    import trimesh
    tm = trimesh.load(os.path.join(_fp.MODEL_DIR, "matrix-testfit.stl"))
    say("")
    say(f"watertight={tm.is_watertight}  bodies={len(tm.split(only_watertight=False))}"
        f"  (must be 1)")
    if not tm.is_watertight:
        bad.append("not watertight")
    if len(tm.split(only_watertight=False)) != 1:
        bad.append("disconnected bodies")
except ImportError:
    pass

say("")
say("ALL CLEAR" if not bad else f"*** {len(bad)} PROBLEM(S) ***")
if bad:
    sys.exit(1)
