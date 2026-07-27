#!/usr/bin/env python3
"""Generate a front-plate for two butted IS31FL3731 16x9 CharliePlex LED
matrices, as both an SVG and a watertight binary STL (identical geometry).

  matrix-front-plate.stl   ready to import straight into OrcaSlicer.
  matrix-front-plate.svg   flattened single filled path (SVG-tool -> extrude).

STL needs `mapbox_earcut` + numpy (polygon-with-holes triangulation):
    python3 -m venv venv && venv/bin/pip install mapbox_earcut numpy
    venv/bin/python gen_plate.py
Without earcut the script still writes the SVG.

Geometry from Adafruit's EAGLE "CharliePlex Grid" .brd (the LED matrix module):
  outline 43.18 x 27.94 mm, corner r 2.54
  holes   O2.0, 2 diagonal (top-left + bottom-right), inset 1.905 mm
  LEDs    16 x 9 @ 2.54 mm pitch, cols x 2.413..40.513, rows y 3.683..24.003
Coordinates are built in the SVG frame (origin top-left, +y DOWN); the STL
flips y so the part sits the same way up.
"""
import math, struct, os

# ---- tunables -------------------------------------------------------------
PITCH       = 2.54
LED_DIA     = 1.8
BOARD_W     = 43.18
BOARD_H     = 27.94
BOARD_PITCH = 43.18       # butted edge-to-edge
PAD         = 3.0
PLATE_R     = 3.0
THICK       = 4.0         # plate thickness (STL); set this in OrcaSlicer for SVG
SCREW_DIA   = 2.4         # M2 clearance (PCB holes are O2.0)
COLS, ROWS  = 16, 9
LED_X0, LED_Y0 = 2.413, 3.937
HOLES = [(1.905, 1.905), (41.275, 26.035)]   # 2 diagonal, board-local
LED_SEG, SCREW_SEG, CORNER_SEG = 24, 28, 8
# ---------------------------------------------------------------------------

PLATE_W = 2 * BOARD_W + 2 * PAD
PLATE_H = BOARD_H + 2 * PAD
BOFF = [PAD, PAD + BOARD_PITCH]

def circle_pts(cx, cy, r, seg):
    return [(cx + r*math.cos(2*math.pi*i/seg), cy + r*math.sin(2*math.pi*i/seg))
            for i in range(seg)]

def rounded_rect_pts(w, h, r, seg):
    corners = [((w-r, r),   -90,   0), ((w-r, h-r),   0,  90),
               ((r,   h-r),  90, 180), ((r,   r),   180, 270)]
    pts = []
    for (cx, cy), a0, a1 in corners:
        for i in range(seg+1):
            a = math.radians(a0 + (a1-a0)*i/seg)
            pts.append((cx + r*math.cos(a), cy + r*math.sin(a)))
    return pts

def merge_circles(cA, rA, cB, rB, seg):
    """Star-shaped union outline of two overlapping circles (about their midpoint)."""
    mx, my = (cA[0]+cB[0])/2, (cA[1]+cB[1])/2
    pts = []
    for (cx, cy), r, (ox, oy), orr in ((cA, rA, cB, rB), (cB, rB, cA, rA)):
        for x, y in circle_pts(cx, cy, r, seg):
            if math.hypot(x-ox, y-oy) >= orr - 1e-6:      # keep arc outside the other
                pts.append((x, y))
    pts.sort(key=lambda p: math.atan2(p[1]-my, p[0]-mx))
    return pts

# ---- build hole polygons (SVG frame), merging screw holes into corner LEDs -
leds, screws = [], []
for bx in BOFF:
    for c in range(COLS):
        for r in range(ROWS):
            leds.append((bx + LED_X0 + c*PITCH, PAD + LED_Y0 + r*PITCH))
    for hx, hy in HOLES:
        screws.append((bx + hx, PAD + hy))

rs, rl = SCREW_DIA/2, LED_DIA/2
merged_led = set()
hole_polys = []
for sx, sy in screws:
    # find the (single) LED this screw overlaps and merge them
    near = min(range(len(leds)), key=lambda i: math.hypot(leds[i][0]-sx, leds[i][1]-sy))
    lx, ly = leds[near]
    if math.hypot(lx-sx, ly-sy) < rs + rl + 0.05:
        hole_polys.append(merge_circles((sx, sy), rs, (lx, ly), rl, SCREW_SEG))
        merged_led.add(near)
    else:
        hole_polys.append(circle_pts(sx, sy, rs, SCREW_SEG))
for i, (lx, ly) in enumerate(leds):
    if i not in merged_led:
        hole_polys.append(circle_pts(lx, ly, rl, LED_SEG))

outer_poly = rounded_rect_pts(PLATE_W, PLATE_H, PLATE_R, CORNER_SEG)

def sarea(p):
    return 0.5*sum(p[i][0]*p[(i+1) % len(p)][1] - p[(i+1) % len(p)][0]*p[i][1]
                   for i in range(len(p)))

# ---- SVG: outer CW(screen), holes opposite ---------------------------------
def orient(p, positive):
    return p if (sarea(p) > 0) == positive else p[::-1]

def nfmt(v): return f"{v:.4f}".rstrip("0").rstrip(".")
def d_of(p):
    s = f"M {nfmt(p[0][0])} {nfmt(p[0][1])}" + "".join(
        f" L {nfmt(x)} {nfmt(y)}" for x, y in p[1:])
    return s + " Z"

outer_svg = orient(outer_poly, True)
paths = [d_of(outer_svg)] + [d_of(orient(h, False)) for h in hole_polys]
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{nfmt(PLATE_W)}mm" '
       f'height="{nfmt(PLATE_H)}mm" viewBox="0 0 {nfmt(PLATE_W)} {nfmt(PLATE_H)}">\n'
       f'  <path fill="#000000" fill-rule="evenodd" d="{" ".join(paths)}"/>\n</svg>\n')

base = os.path.dirname(os.path.abspath(__file__))
open(os.path.join(base, "matrix-front-plate.svg"), "w").write(svg)

# ---- STL: earcut top/bottom faces + vertical walls -------------------------
def write_stl():
    try:
        import numpy as np, mapbox_earcut as earcut
    except ImportError:
        print("(earcut/numpy not available -> STL skipped; SVG written)")
        return
    # mesh frame: flip y so the part is upright; enforce outer CCW, holes CW
    def to_mesh(p): return [(x, PLATE_H - y) for x, y in p]
    def orient_m(p, ccw):
        return p if (sarea(p) > 0) == ccw else p[::-1]
    outer = orient_m(to_mesh(outer_poly), True)
    holes = [orient_m(to_mesh(h), False) for h in hole_polys]

    verts, ends = list(outer), []
    ends.append(len(verts))
    for h in holes:
        verts.extend(h); ends.append(len(verts))
    V = np.array(verts, dtype=np.float64)
    idx = earcut.triangulate_float64(V, np.array(ends, dtype=np.uint32))

    T = THICK
    tris = []
    # top (z=T, +z) and bottom (z=0, -z)
    for i in range(0, len(idx), 3):
        a, b, c = (V[idx[i]], V[idx[i+1]], V[idx[i+2]])
        tris.append(((a[0], a[1], T), (b[0], b[1], T), (c[0], c[1], T)))
        tris.append(((a[0], a[1], 0), (c[0], c[1], 0), (b[0], b[1], 0)))
    # walls: outer CCW / holes CW -> solid on the left, outward normal = (dy,-dx)
    for ring in [outer] + holes:
        m = len(ring)
        for i in range(m):
            ax, ay = ring[i]; bx2, by2 = ring[(i+1) % m]
            A0, B0 = (ax, ay, 0), (bx2, by2, 0)
            A1, B1 = (ax, ay, T), (bx2, by2, T)
            tris.append((A0, B0, B1)); tris.append((A0, B1, A1))

    def normal(a, b, c):
        ux, uy, uz = b[0]-a[0], b[1]-a[1], b[2]-a[2]
        vx, vy, vz = c[0]-a[0], c[1]-a[1], c[2]-a[2]
        nx, ny, nz = uy*vz-uz*vy, uz*vx-ux*vz, ux*vy-uy*vx
        L = math.sqrt(nx*nx+ny*ny+nz*nz) or 1.0
        return nx/L, ny/L, nz/L

    buf = bytearray(b"\0"*80 + struct.pack("<I", len(tris)))
    for a, b, c in tris:
        buf += struct.pack("<12fH", *normal(a, b, c), *a, *b, *c, 0)
    open(os.path.join(base, "matrix-front-plate.stl"), "wb").write(buf)
    print(f"STL: {len(tris)} triangles, {len(hole_polys)} holes "
          f"({len(merged_led)} merged with screws)")

print(f"plate {nfmt(PLATE_W)} x {nfmt(PLATE_H)} x {nfmt(THICK)} mm")
write_stl()
print("wrote matrix-front-plate.svg" + (" + .stl" if os.path.exists(
    os.path.join(base, "matrix-front-plate.stl")) else ""))
