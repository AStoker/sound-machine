#!/usr/bin/env python3
"""DO THE PARTS ACTUALLY MATE? -- the check that did not exist.

    python3 check_assembly.py

Every other check in this repo tests one part against numbers. This one takes the
EXPORTED SOLIDS, moves each into a single shared frame using a transform that is
asserted to be a proper rotation, and asks whether the features that are supposed
to meet actually meet.

>>> IT EXISTS BECAUSE THE BOTTOM PLATE WAS MODELLED AS A MIRROR IMAGE FOR WEEKS AND
>>> EVERY CHECK PASSED. The dome is modelled (x, HEIGHT, DEPTH); the plate was
>>> modelled (x, DEPTH, THICKNESS). Both stored their screw positions as the same
>>> pair of numbers out of SCREWS, and every check compared those NUMBERS and found
>>> them equal -- while the two parts, in space, were mirror images. I even ran a
>>> "do the lugs line up" probe and reported agreement: it read 45.0 from one part
>>> and 45.0 from the other and never noticed that one of those was a depth and the
>>> other a height.
>>>
>>> Comparing coordinates from two frames is not a comparison. The only honest
>>> version transforms both into one frame first, which is what this does -- and
>>> the transform has to be checked for handedness, because a swap of two axes
>>> looks like a rotation until you take its determinant.

THE ASSEMBLY FRAME is the dome's:  x = width, y = height, z = depth.
Every part declares how it maps into it, and every mapping is asserted proper.
"""
import os
import sys

import numpy as np
import trimesh

import enclosure_geom as g
import frames

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.join(HERE, "models")

_out, bad = [], []


def say(s):
    _out.append(s)
    print(s)


def chk(name, ok, detail=""):
    say(f"  {'ok  ' if ok else 'FAIL'}  {name}{('   ' + detail) if detail else ''}")
    if not ok:
        bad.append(name)


# ---------------------------------------------------------------------------
# HOW EACH PART SITS IN THE ASSEMBLY
# ---------------------------------------------------------------------------
# >>> THE TRANSFORMS LIVE IN frames.py, NOT HERE. A second copy of them in the one
# >>> file whose job is to catch frame mistakes would be its own punchline -- and
# >>> the copies would drift the first time an export orientation changed. frames.py
# >>> asserts every determinant at import, so a reflection cannot even load.
T_DOME = frames.TO_ASSEMBLY["dome.stl"]
T_PLATE = frames.TO_ASSEMBLY["bottom-plate.stl"]

PARTS = [("dome.stl", T_DOME), ("bottom-plate.stl", T_PLATE)]

say("part transforms into the assembly frame")
for _fn, _T in PARTS:
    _det = np.linalg.det(_T[:3, :3])
    chk(f"{_fn:18s} transform is a proper rotation", abs(_det - 1.0) < 1e-9,
        f"det = {_det:+.3f}")
say("")


def load(fn, T):
    return frames.to_assembly(trimesh.load(os.path.join(MODELS, fn)), fn)


dome = load("dome.stl", T_DOME)
plate = load("bottom-plate.stl", T_PLATE)
say(f"dome  in assembly: x {dome.bounds[0][0]:6.1f}..{dome.bounds[1][0]:6.1f}  "
    f"y {dome.bounds[0][1]:6.1f}..{dome.bounds[1][1]:6.1f}  "
    f"z {dome.bounds[0][2]:6.1f}..{dome.bounds[1][2]:6.1f}")
say(f"plate in assembly: x {plate.bounds[0][0]:6.1f}..{plate.bounds[1][0]:6.1f}  "
    f"y {plate.bounds[0][1]:6.1f}..{plate.bounds[1][1]:6.1f}  "
    f"z {plate.bounds[0][2]:6.1f}..{plate.bounds[1][2]:6.1f}")
say("")


def solid(mesh, p):
    return bool(mesh.contains(np.array([p]))[0])


def ring(mesh, x, z, y, r, n=16):
    """How many of n points on a circle of radius r about (x,z) at height y are
    inside the mesh."""
    th = np.linspace(0, 2 * np.pi, n, endpoint=False)
    P = np.column_stack([x + r * np.cos(th), np.full(n, y), z + r * np.sin(th)])
    return int(mesh.contains(P).sum())


# ---------------------------------------------------------------------------
# THE SIX SCREWS -- a lug above, a clearance hole below, sharing an axis
# ---------------------------------------------------------------------------
say("the six fixings: does each dome lug sit over its plate hole?")
for _sx, _sd in g.SCREWS:
    # the dome's lug is solid material around the insert bore, above the plate
    _lug = ring(dome, _sx, _sd, g.BP_T + 3.0, g.INSERT_D / 2 + 1.5)
    # the plate has a clearance hole ON THE SAME AXIS, at mid-thickness
    _open = not solid(plate, (_sx, g.BP_T / 2, _sd))
    # ...and material around it, so the screw has something to pull on
    _land = ring(plate, _sx, _sd, g.BP_T / 2, g.SCREW_CBORE / 2 + 1.0)
    chk(f"x={_sx:6.1f} depth={_sd:5.1f}  lug over hole",
        _lug >= 14 and _open and _land >= 14,
        f"lug {_lug:2d}/16, hole {'open' if _open else 'BLOCKED'}, "
        f"land {_land:2d}/16")

# ---------------------------------------------------------------------------
# AND THE PARTS MUST NOT OCCUPY THE SAME SPACE
# ---------------------------------------------------------------------------
# >>> A MIRRORED PLATE STILL PASSES A HOLE-BY-HOLE TEST IF THE PATTERN HAPPENS TO
# >>> BE SYMMETRIC. The interference test does not care about patterns: it asks
# >>> whether the two solids overlap, which a wrong-handed part does immediately
# >>> and obviously.
say("")
say("solid interference between the two parts")
# >>> A 50 mm^3 TOLERANCE HID A REAL COLLISION. Two parts that touch produce a lot
# >>> of ZERO-VOLUME coplanar fragments where the plate rests on its ledge, so a
# >>> blanket allowance looked reasonable -- and it swallowed 27 mm^3 of genuine
# >>> interference: the switch and barrel-jack nut lands reaching 1.5-2.0 mm through
# >>> the plate. Andy found it by trying to close the box.
# >>>
# >>> The two are not the same thing and must not share a threshold. Contact is
# >>> flat: many pieces, each with no volume. A collision is one lump with volume.
# >>> So split the intersection and judge the LARGEST PIECE, at an epsilon that only
# >>> covers mesh noise -- not at a number big enough to hide a feature.
try:
    inter = dome.intersection(plate)
    _pieces = ([] if inter is None or not len(inter.faces)
               else sorted(inter.split(only_watertight=False),
                           key=lambda p: -abs(p.volume)))
except Exception as _e:                        # pragma: no cover
    _pieces = None
    say(f"  (boolean failed: {_e})")
if _pieces is None:
    chk("dome and plate do not overlap", False, "boolean failed")
else:
    _worst = abs(_pieces[0].volume) if _pieces else 0.0
    _flat = sum(1 for p in _pieces if abs(p.volume) <= 0.05)
    say(f"  ----  {len(_pieces)} contact region(s), {_flat} of them flat "
        f"(zero volume -- the plate resting on its ledge)")
    for _p in _pieces[:3]:
        if abs(_p.volume) > 0.05:
            _b = _p.bounds
            say(f"        SOLID {_p.volume:7.2f} mm^3 at x {_b[0][0]:.1f}-{_b[1][0]:.1f}, "
                f"y {_b[0][1]:.2f}-{_b[1][1]:.2f}")
    chk("no piece of the dome is INSIDE the plate", _worst <= 0.05,
        f"largest {_worst:.3f} mm^3")

say("")
say("ALL CLEAR" if not bad else f"*** {len(bad)} PROBLEM(S) ***")
if bad:
    sys.exit(1)
