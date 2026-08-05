#!/usr/bin/env python3
"""WHICH WAY ROUND EACH EXPORTED FILE IS. One source of truth.

THE ASSEMBLY FRAME is the dome's own:

    x = width   (0 .. W, left to right)
    y = height  (0 at the bottom plate's underside, up)
    z = depth   (0 at the front face, back toward the rear wall)

Every .stl on disk is written in its PRINT orientation, which is not that frame.
This module says how to get each one back, and nothing else may guess.

>>> THE BOTTOM PLATE WAS A MIRROR IMAGE OF ITSELF FOR WEEKS AND EVERY CHECK PASSED.
>>> The dome is modelled (x, HEIGHT, DEPTH); the plate was modelled (x, DEPTH,
>>> THICKNESS). Both wrote their six screw positions from the same SCREWS list, so
>>> every check compared 45.0 against 45.0 and called it agreement -- never noticing
>>> that one of those numbers was a depth and the other a height. The implied
>>> mapping between the two frames is the axis swap (x, y, z) -> (x, z, y), whose
>>> determinant is -1: a REFLECTION, which is not something you can do to a printed
>>> part. Andy found it by trying to assemble the thing.
>>>
>>> Two rules came out of it, and they are why this file exists:
>>>   1. Comparing coordinates from two frames is not a comparison. Transform into
>>>      one frame FIRST.
>>>   2. Check the determinant. An axis swap looks exactly like a rotation until
>>>      you take it, and every transform here is asserted at import.
"""
import numpy as np

import enclosure_geom as g


def _rot_x(deg):
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    return np.array([[1, 0, 0, 0],
                     [0, c, -s, 0],
                     [0, s, c, 0],
                     [0, 0, 0, 1]], float)


def _move(x, y, z):
    T = np.eye(4)
    T[:3, 3] = (x, y, z)
    return T


# file on disk -> assembly frame
TO_ASSEMBLY = {
    # Written rear-wall-down so it needs no turning in the slicer. Undo with the
    # same 180 deg about X that put it there -- the transform is its own inverse.
    "dome.stl": _move(0, g.H, g.D) @ _rot_x(180),
    # Written flat, underside on the bed: (x, depth, thickness). Standing it into
    # the machine is -90 about X. THIS is the rotation whose forced negation of the
    # depth axis the plate's layout has to account for.
    "bottom-plate.stl": _move(0, 0, g.D) @ _rot_x(-90),
}

# Parts still exported directly in the assembly frame need no entry; ask for one
# explicitly rather than defaulting, so a missing entry is loud.
IDENTITY = np.eye(4)


for _name, _T in TO_ASSEMBLY.items():
    _det = float(np.linalg.det(_T[:3, :3]))
    assert abs(_det - 1.0) < 1e-9, (
        f"{_name}: transform into the assembly frame has determinant {_det:+.3f}. "
        f"That is a reflection, not a rotation -- the part is handed wrongly and "
        f"no amount of moving it will make it fit.")


def to_assembly(mesh, filename):
    """Move a loaded trimesh from its file's frame into the assembly frame."""
    T = TO_ASSEMBLY.get(filename)
    if T is None:
        raise KeyError(
            f"{filename} has no declared frame in frames.py. Add one -- do not "
            f"assume the file is already in assembly coordinates, which is the "
            f"assumption that hid a mirrored part for weeks.")
    mesh.apply_transform(T)
    return mesh
