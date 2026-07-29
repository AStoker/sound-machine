#!/usr/bin/env python3
"""BOTTOM PLATE — PART 3. The chassis, and the only part with visible screws.

It closes the open bottom of the dome, captures the front module's lower edge,
carries the TPA2016, and takes the four feet. Six M3 screws come up through it
into heat-set inserts in the dome's wall lugs.

    PRINT UNDERSIDE DOWN. The counterbores and the foot pockets then open
    downward and print as plain holes from the first layer; the boss for the amp
    grows upward. Nothing needs support. The underside is also the face people
    see when they pick the machine up, so it wants to be the bed face.

>>> THIS IS THE ONE PART WHERE SCREW HEADS SHOW, AND THEY ARE COUNTERBORED BELOW
>>> THE FEET. SCREW_CBORE x SCREW_CB_T sinks each head far enough that the plate
>>> still rests on rubber, not on steel. If the counterbore ever gets shallower
>>> than the head, the machine rocks on six screw heads.

>>> THE FIXINGS ARE NOT SYMMETRIC, AND CANNOT BE. The floor is fully spoken for:
>>> the speaker boxes own both front corners, the matrix owns the middle, and the
>>> UPS owns the rear-right. There is NO lug on the front edge at all -- the
>>> plate's front edge is captured between the dome's seating ledge and the front
>>> module's bottom edge instead. See SCREWS in enclosure_geom.

    python3 gen_bottom_plate.py   ->  models/bottom-plate.stl
"""
import math
import os
import struct

from manifold3d import CrossSection, Manifold

from enclosure_geom import (
    AMP_D, AMP_DEPTH, AMP_H, AMP_HOLES, AMP_W, AMP_X, BOSS_CHAMF, BOSS_D,
    amp_holes_part,
    BOSS_PILOT_D, BOSS_SCREW, BP_CLR, BP_D, BP_T, BP_W, D, FLEX_WALL_Y,
    FOOT_CLR, FOOT_D, FOOT_IN, FOOT_POCKET_T, IN_D, IN_W, MODEL_DIR, SCREWS,
    SCREW_CBORE, SCREW_CB_T, SCREW_CLR, SPK_BODY_D, SPK_BODY_W, SPK_X, TRAY_D,
    TRAY_W, UPS_D, UPS_W, UPS_WALL_X, W, WALL, FP_T, floor_items,
    LUG_H, LUG_L, dome_floor_intrusions, plate_boards,
)

SEG = 64
BED = 220.0

# --- print parameters -------------------------------------------------------
EDGE_R      = 3.0     # corner radius on the plate outline
AMP_STAND   = 2.0     # standoff under the amp board, so its solder side clears
_out = []


def say(s):
    _out.append(s)
    print(s)


def poly(pts):
    return CrossSection([[(float(x), float(y)) for x, y in pts]])


def rrect(x0, y0, w, h, r):
    pts = []
    for cx, cy, a0 in ((x0 + w - r, y0 + r, -math.pi / 2),
                       (x0 + w - r, y0 + h - r, 0.0),
                       (x0 + r, y0 + h - r, math.pi / 2),
                       (x0 + r, y0 + r, math.pi)):
        for i in range(13):
            a = a0 + (math.pi / 2) * i / 12
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return poly(pts)


def slab(cs, z0, z1):
    return cs.extrude(z1 - z0).translate((0, 0, z0))


def cyl(cx, cy, z0, z1, d):
    return Manifold.cylinder(z1 - z0, d / 2, d / 2, SEG).translate((cx, cy, z0))


def union(parts):
    if not parts:
        return Manifold()
    out = parts[0]
    for p in parts[1:]:
        out = out + p
    return out


# ---------------------------------------------------------------------------
# BODY
# ---------------------------------------------------------------------------
# Part coordinates: x across the machine, y = DEPTH from the front face, z up
# from the plate's underside. The plate sits inside the dome walls with BP_CLR
# clearance per side.
X0, Y0 = WALL + BP_CLR, WALL + BP_CLR
body = slab(rrect(X0, Y0, BP_W, BP_D, EDGE_R), 0.0, BP_T)

# --- the six fixing screws --------------------------------------------------
# Clearance hole all the way through, counterbored from BELOW so the head sinks
# under the feet. SCREWS is (x, depth-from-the-front-face).
cuts = []
for sx, sd in SCREWS:
    cuts.append(cyl(sx, sd, -1.0, BP_T + 1.0, SCREW_CLR))
    cuts.append(cyl(sx, sd, -1.0, SCREW_CB_T, SCREW_CBORE))

# --- feet -------------------------------------------------------------------
# >>> RECESSED, NOT STUCK ON A FLAT. A pocket locates each foot exactly, stops it
# >>> creeping sideways under load, and -- the part that matters -- guarantees it
# >>> cannot be stuck down overlapping a screw counterbore, which is easy to do
# >>> by eye on a plain plate.
FEET = [(WALL + FOOT_IN, WALL + FOOT_IN),
        (W - WALL - FOOT_IN, WALL + FOOT_IN),
        (WALL + FOOT_IN, D - WALL - FOOT_IN),
        (W - WALL - FOOT_IN, D - WALL - FOOT_IN)]
for fx, fy in FEET:
    cuts.append(cyl(fx, fy, -1.0, FOOT_POCKET_T, FOOT_D + 2 * FOOT_CLR))

body = body - union(cuts)

# --- TPA2016 mount ----------------------------------------------------------
# The amp is on the FLOOR, in the 12 mm slot under the lifted Flex -- the rear
# wall is full. Two bosses on the board's hole pitch, plus a standoff pad so the
# solder side clears the plate.
# >>> THE RTC IS NOT HERE ANY MORE, AND IT SHOULD NEVER HAVE BEEN. It was put on
# >>> this plate because a rear-wall search reported no viable position -- a search
# >>> that had been run against the OLD vent stacks and the OLD amp position and
# >>> was never re-run after either moved. Re-run, the wall offers 67151 positions.
# >>>
# >>> While it was here it cost two moves and shipped a defect anyway: (20,44) put
# >>> two bosses 4.5 mm on top of the left fixing screws, and (26.3,43.7) buried
# >>> the BOARD 0.9 mm inside the dome's left wall rail. Nothing on this part could
# >>> see the second one, because every check compared Ø6 BOSS POSTS and the board
# >>> that sits on them was never modelled -- RTC_PCB_W was imported here and never
# >>> used. See "board outlines" in the checks below.
adds = []
board_holes = []
# >>> ONE BOSS PER REAL HOLE, from the board file, through the lay-down transform
# >>> in amp_holes_part(). This loop used to spread two bosses +-pitch/2 in x ON
# >>> THE BOARD'S DEPTH CENTRELINE, using a placeholder pitch. Both holes are
# >>> actually 8.26 mm off that centreline.
for nm, bx, bd, offs in (("amp", AMP_X, AMP_DEPTH, amp_holes_part()),):
    for dx, dy in offs:
        hx, hy = bx + dx, bd + dy
        board_holes.append((nm, hx, hy))
        adds.append(cyl(hx, hy, BP_T, BP_T + AMP_STAND + BOSS_CHAMF, BOSS_D))
amp_holes = [(x, y) for n, x, y in board_holes if n == "amp"]
body = body + union(adds)
body = body - union([cyl(hx, hy, BP_T + 0.5, BP_T + AMP_STAND + BOSS_CHAMF + 1,
                         BOSS_PILOT_D) for _, hx, hy in board_holes])

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


nf = write_stl(body, "bottom-plate.stl")
bb = body.bounding_box()

say(f"wrote models/bottom-plate.stl   {nf} triangles")
say(f"bbox        {bb[3]-bb[0]:.2f} x {bb[4]-bb[1]:.2f} x {bb[5]-bb[2]:.2f} mm")
say(f"plate       {BP_W:.1f} x {BP_D:.1f} x {BP_T}, {BP_CLR} clearance per side")
say(f"screws      {len(SCREWS)} x M3 clearance {chr(216)}{SCREW_CLR}, counterbored "
    f"{chr(216)}{SCREW_CBORE} x {SCREW_CB_T} from BELOW")
say(f"feet        4 x {chr(216)}{FOOT_D} in {FOOT_POCKET_T} deep pockets, "
    f"{FOOT_IN} in from the walls")
say(f"amp         {len(amp_holes)} x M{BOSS_SCREW} at "
    + " and ".join(f"({x:.2f}, {y:.2f})" for x, y in amp_holes)
    + f"; board centre x={AMP_X} depth={AMP_DEPTH}")
say("RTC         not on this part -- it is on the dome's rear wall")
say("")

bad = []


def chk(name, v, lo=0.0):
    ok = v >= lo - 1e-6
    say(f"  {'ok  ' if ok else 'FAIL'} {v:8.2f}   {name}")
    if not ok:
        bad.append(name)


say("clearances")
chk("plate fits inside the dome walls (x)", IN_W - BP_W)
chk("plate fits inside the dome walls (depth)", IN_D - BP_D)
chk("head sinks below the feet", FOOT_POCKET_T + 2.0 - SCREW_CB_T, -1e-6)
chk("material left under a counterbore", BP_T - SCREW_CB_T - 1.0)

# >>> EVERY FOOT MUST CLEAR EVERY COUNTERBORE. Both are pockets in the same face;
# >>> if they overlap, the foot sits on a hole and the plate rocks.
_worst = min(math.hypot(fx - sx, fy - sd) - (FOOT_D + 2 * FOOT_CLR) / 2
             - SCREW_CBORE / 2
             for fx, fy in FEET for sx, sd in SCREWS)
chk("feet clear the screw counterbores", _worst)

# The amp bosses must not collide with anything else standing on the floor.
_amp_worst = 1e9
for name, ox0, ox1, od0, od1 in floor_items():
    if name.startswith("TPA2016"):
        continue
    for _n, hx, hy in board_holes:
        gap = max(max(ox0 - (hx + BOSS_D / 2), (hx - BOSS_D / 2) - ox1),
                  max(od0 - (hy + BOSS_D / 2), (hy - BOSS_D / 2) - od1))
        _amp_worst = min(_amp_worst, gap)
chk("floor bosses clear everything else on the floor", _amp_worst)
# every boss must land ON the plate, not off its edge
_edge = min(min(hx - (WALL + BP_CLR), (W - WALL - BP_CLR) - hx,
                hy - (WALL + BP_CLR), (D - WALL - BP_CLR) - hy)
            for _n, hx, hy in board_holes) - BOSS_D / 2
chk("every floor boss lands on the plate", _edge)

# >>> BOSSES vs THE SIX FIXING SCREWS -- the check that was missing. The RTC's
# >>> position had been searched against the floor items and the plate edges, but
# >>> nothing compared it to the screws, and two of its four bosses ended up
# >>> sitting ON a counterbore with 4.5 mm of overlap. The screws are the one
# >>> thing on this plate that cannot move: they are set by the dome's tabs.
_scr = min(math.hypot(hx - sx, hy - sd) - BOSS_D / 2 - SCREW_CBORE / 2
           for _n, hx, hy in board_holes for sx, sd in SCREWS)
chk("floor bosses clear the fixing screw counterbores", _scr)

# >>> AND NOW EVERY PAIR, EXHAUSTIVELY -- BUT IN 3D. Three separate bugs on this
# >>> part were the same shape: feature A was checked against B and C, and nobody
# >>> ever compared it to D. Feet vs counterbores was checked; bosses vs the screw
# >>> holes was not, and two bosses ended up bored through.
# >>>
# >>> IT HAS TO KNOW ABOUT Z. The first version compared footprints only and
# >>> immediately "found" a foot pocket overlapping a boss -- which is fine: the
# >>> pocket is cut 1 mm from BELOW and the boss stands on TOP, with 3 mm of plate
# >>> between them. A planar check on a part with features on both faces reports
# >>> collisions that do not exist, and that is how a check loses its authority.
# >>> Each feature therefore carries its z span, and only overlapping spans are
# >>> compared.
_feat = []
for sx, sd in SCREWS:
    # the clearance hole runs the FULL thickness -- it is what reaches a boss
    _feat.append((f"screwhole({sx:.0f},{sd:.0f})", sx, sd, SCREW_CLR / 2,
                  -1.0, BP_T + 1.0))
    _feat.append((f"cbore({sx:.0f},{sd:.0f})", sx, sd, SCREW_CBORE / 2,
                  -1.0, SCREW_CB_T))
for fx, fy in FEET:
    _feat.append((f"foot({fx:.0f},{fy:.0f})", fx, fy,
                  (FOOT_D + 2 * FOOT_CLR) / 2, -1.0, FOOT_POCKET_T))
for _n, hx, hy in board_holes:
    _feat.append((f"{_n}boss({hx:.0f},{hy:.0f})", hx, hy, BOSS_D / 2,
                  BP_T, BP_T + AMP_STAND + BOSS_CHAMF))

_worst_pair, _who, _pairs = 1e9, "", 0
for _i in range(len(_feat)):
    for _j in range(_i + 1, len(_feat)):
        _na, _ax, _ay, _ar, _az0, _az1 = _feat[_i]
        _nb, _bx, _by, _br, _bz0, _bz1 = _feat[_j]
        if _na.split("(")[0] == _nb.split("(")[0] == "cbore":
            pass
        if min(_az1, _bz1) - max(_az0, _bz0) <= 0:
            continue                       # they never meet in z
        if (_ax, _ay) == (_bx, _by):
            continue                       # concentric by design (hole in cbore)
        _pairs += 1
        _g = math.hypot(_ax - _bx, _ay - _by) - _ar - _br
        if _g < _worst_pair:
            _worst_pair, _who = _g, f"{_na} <-> {_nb}"
say(f"  ---- {_worst_pair:8.2f}   tightest pair anywhere: {_who}")
chk(f"every feature pair that shares depth clears "
    f"({len(_feat)} features, {_pairs} pairs)", _worst_pair)
# >>> BOARD OUTLINES, NOT BOSS POSTS -- and against the DOME, not just this part.
# >>> Every check above compares Ø6 bosses. A board is bigger than its bosses (the
# >>> RTC was 25.4 mm on a 20 mm pitch) and it is the board that hits things. It
# >>> was RTC_PCB_W, imported into this file and never referenced, that let the
# >>> board end up 0.9 mm inside the dome's left rail while every check passed.
say("")
say("board outlines vs the dome's own intrusions")
_bw = 1e9
for _bn, _bx, _bd, _bw_, _bd_, _offs in plate_boards():
    _x0, _x1 = _bx - _bw_ / 2, _bx + _bw_ / 2
    _d0, _d1 = _bd - _bd_ / 2, _bd + _bd_ / 2
    for _dn, _ox0, _ox1, _od0, _od1 in dome_floor_intrusions():
        _g = max(_ox0 - _x1, _x0 - _ox1, _od0 - _d1, _d0 - _od1)
        if _g < _bw:
            _bw, _bwho = _g, f"{_bn} <-> {_dn}"
    # and the bosses it stands on, which can reach past the board outline
    for _dx, _dy in _offs:
        _hx, _hy = _bx + _dx, _bd + _dy
        for _dn, _ox0, _ox1, _od0, _od1 in dome_floor_intrusions():
            _g = max(_ox0 - (_hx + BOSS_D / 2), (_hx - BOSS_D / 2) - _ox1,
                     _od0 - (_hy + BOSS_D / 2), (_hy - BOSS_D / 2) - _od1)
            if _g < _bw:
                _bw, _bwho = _g, f"{_bn} boss <-> {_dn}"
say(f"  ---- {_bw:8.2f}   tightest: {_bwho}")
chk("every plate board clears every dome intrusion", _bw)

# >>> AND CHECK THE LAY-DOWN TRANSFORM, not just the clearances around it. A wrong
# >>> swap or a wrong sign still yields two bosses on a plausible-looking plate,
# >>> and every clearance check above passes happily -- that is exactly how two
# >>> bosses ended up 8.26 mm off the holes they were for. The transform is a
# >>> RIGID MOTION, so it must preserve distances: the boss-to-boss span and each
# >>> hole's set of distances to the four board edges have to come out the same in
# >>> board coordinates and in part coordinates.
say("")
say("amp board->part transform is a rigid motion")
_span_board = max(math.dist(a, b) for a in AMP_HOLES for b in AMP_HOLES)
_span_part = max(math.dist(a, b) for a in amp_holes for b in amp_holes)
chk(f"hole span preserved ({_span_board:.2f} mm on the board)",
    0.01 - abs(_span_part - _span_board))
for _i, ((_bx_, _by_), (_px_, _py_)) in enumerate(zip(AMP_HOLES, amp_holes)):
    _in_board = sorted([_bx_, AMP_D - _bx_, _by_, AMP_W - _by_])
    _in_part = sorted([_px_ - (AMP_X - AMP_W / 2), (AMP_X + AMP_W / 2) - _px_,
                       _py_ - (AMP_DEPTH - AMP_D / 2),
                       (AMP_DEPTH + AMP_D / 2) - _py_])
    chk(f"hole {_i} edge distances preserved "
        f"({', '.join(f'{v:.2f}' for v in _in_board)})",
        0.01 - max(abs(a - b) for a, b in zip(_in_board, _in_part)))
    chk(f"hole {_i} lands on the board, not off it", min(_in_part))

chk("amp board clears the lifted Flex above it", FLEX_WALL_Y - AMP_H)
chk("amp bosses clear the plate edge (depth)",
    (D - WALL - BP_CLR) - (AMP_DEPTH + AMP_D / 2))
chk("fits the bed (x)", BED - (bb[3] - bb[0]))
chk("fits the bed (y)", BED - (bb[4] - bb[1]))

try:
    import trimesh
    tm = trimesh.load(os.path.join(MODEL_DIR, "bottom-plate.stl"))
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
