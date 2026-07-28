#!/usr/bin/env python3
"""Snap-in capture tray for two butted IS31FL3731 16x9 CharliePlex matrices +
their two driver backpacks, stacked with a gap. Front face stays flat (LED
windows only); all retention is on the back.

Holds the stack solidly as one unit:
  * matrices seat against the flat front face, LEDs into the light tunnels,
    located + retained by BARBED POSTS through each matrix's 2 diagonal O2.0 holes
  * the matrix<->backpack GAP is set by your own header pins (parameter STACK_GAP)
  * backpacks are retained by flexible CANTILEVER SNAP FINGERS whose bumps flex
    aside as the boards pass, then click behind the backpack's back face
  * wire/connector NOTCHES in the end walls

Needs manifold3d (robust CSG). Build:
  venv/bin/pip install manifold3d trimesh matplotlib
  venv/bin/python gen_tray.py
Outputs models/matrix-tray.stl (+ a cross-section preview PNG in the scratchpad).

>>> MEASURE THESE ON YOUR BUILD and set below <<<
  PCB_T, BP_T   PCB thicknesses (1.6 mm is standard)
  STACK_GAP     clear gap between matrix back and backpack front (header pins)
  LED_D         window Ø - must clear the LED package so the matrix seats flat
"""
import math, os
import manifold3d as m3d
from manifold3d import Manifold, CrossSection

# ---- board geometry (from Adafruit EAGLE files; do not change) ------------
BW, BH   = 43.18, 27.94          # single board outline
NB       = 2                     # boards across (butted)
PITCH    = 2.54
COLS, ROWS = 16, 9
LED_X0, LED_Y0 = 2.413, 3.683    # first LED centre, board-local (y up)
MHOLES   = [(1.905, 26.035), (41.275, 1.905)]   # matrix diagonal holes

# ---- MEASURE / tune -------------------------------------------------------
PCB_T     = 1.6      # matrix thickness
BP_T      = 1.6      # backpack thickness
STACK_GAP = 5.0      # matrix-back -> backpack-front (your header-pin gap)
FACE_T    = 1.5      # front layer = LED tunnel depth (thin = wider viewing angle)
LED_D     = 2.0      # window Ø (must clear the LED package)
WALL      = 2.0
CLR       = 0.30     # per-side clearance around the PCB stack
POST_D    = 1.85     # locating post shaft (into O2.0 hole) -- alignment only, no barb
POST_TIP  = 0.60     # chamfered lead-in tip (self-supporting cone, not a barb)
FINGER_W  = 9.0      # snap-finger width
SLOT_W    = 1.40     # slot each side of a finger (flex clearance)
LIP_REACH = 1.10     # snap-wedge inward reach
LIP_RUN   = 1.10     # retain-face run (== reach => 45 deg, FDM self-supporting)
RAMP_RUN  = 3.00     # lead-in ramp length (gentle insertion)
NOTCH_W   = 18.0     # wire notch width -- clears TWO stacked STEMMA QT ports
SEG       = 32       # facets on round features
# ---------------------------------------------------------------------------

FOOT_X = NB*BW                       # boards footprint
FOOT_Y = BH
OX = FOOT_X + 2*CLR + 2*WALL         # tray outer
OY = FOOT_Y + 2*CLR + 2*WALL
X0 = WALL + CLR                      # board-origin inside tray
Y0 = WALL + CLR
Z_MAT_BACK = FACE_T + PCB_T          # matrix back plane
Z_BP_FRONT = Z_MAT_BACK + STACK_GAP  # backpack front
Z_BP_BACK  = Z_BP_FRONT + BP_T       # backpack back plane
D = Z_BP_BACK + LIP_RUN + RAMP_RUN + 1.0   # total depth (room for snap wedge behind bp)

def cyl(h, r, r2=None):
    return Manifold.cylinder(h, r, r if r2 is None else r2, SEG)

def compose(parts):
    return Manifold.compose(parts) if parts else Manifold()

def wedge(cx, y_face, sgn, width):
    """Triangular snap hook: 45deg retain face (FDM-safe), gentle lead-in ramp.
    Peak reaches LIP_REACH inward from the wall's inner face at the bp-back plane."""
    zb = Z_BP_BACK
    base = y_face - sgn*0.3                 # embed 0.3 into the finger
    peak = y_face + sgn*LIP_REACH
    # entirely at z >= zb so the hook sits BEHIND the backpack back face:
    #   A->B = 45deg retain facet (down-facing overhang, FDM-safe)
    #   B->C = shallow lead-in ramp for insertion
    pts = [(zb, base), (zb + LIP_RUN, peak), (zb + LIP_RUN + RAMP_RUN, base)]
    area = 0.5*sum(pts[i][0]*pts[(i+1) % 3][1] - pts[(i+1) % 3][0]*pts[i][1]
                   for i in range(3))
    if area < 0:
        pts = pts[::-1]                     # CrossSection wants CCW
    solid = CrossSection([pts]).extrude(width).rotate((0, -90, 0))  # local x->z
    return solid.translate((cx + width/2, 0, 0))

# ---- windows (through the flat face) --------------------------------------
windows = []
for b in range(NB):
    for c in range(COLS):
        for r in range(ROWS):
            x = X0 + b*BW + LED_X0 + c*PITCH
            y = Y0 + LED_Y0 + r*PITCH
            windows.append(cyl(FACE_T + 2, LED_D/2).translate((x, y, -1)))

# ---- barbed locating posts (into matrix diagonal holes) -------------------
posts = []
for b in range(NB):
    for hx, hy in MHOLES:
        x, y = X0 + b*BW + hx, Y0 + hy
        shaft = cyl(PCB_T + 0.1, POST_D/2).translate((x, y, FACE_T - 0.1))
        tip   = cyl(POST_TIP, POST_D/2, POST_D*0.2).translate((x, y, Z_MAT_BACK))
        posts.append(shaft + tip)

# ---- wire notches in the two end walls ------------------------------------
notch_h = D - Z_MAT_BACK + 1
notches = []
for xc in (0.0, OX - WALL):
    notches.append(Manifold.cube((WALL + 1, NOTCH_W, notch_h))
                   .translate((xc - 0.5, (OY - NOTCH_W)/2, Z_MAT_BACK)))

# ---- cantilever snap fingers on the two long walls ------------------------
finger_root = Z_MAT_BACK          # free from here to the back
slots, bumps = [], []
finger_x = [OX*0.28, OX*0.72]
walls_y = [(0.0, WALL, +1), (OY, OY - WALL, -1)]   # (outer, inner, inward-sign)
for cx in finger_x:
    for y_out, y_in, sgn in walls_y:
        # two slots isolate the finger
        for sx in (cx - FINGER_W/2 - SLOT_W, cx + FINGER_W/2):
            slots.append(Manifold.cube((SLOT_W, WALL + 2, D - finger_root + 1))
                         .translate((sx, y_out - 1, finger_root)))
        # triangular snap hook on the finger's inner face
        bumps.append(wedge(cx, y_in, sgn, FINGER_W*0.7))

# ---- assemble --------------------------------------------------------------
tray = Manifold.cube((OX, OY, D))
cavity = Manifold.cube((FOOT_X + 2*CLR, FOOT_Y + 2*CLR, D - FACE_T + 1)) \
    .translate((WALL, WALL, FACE_T))
tray = tray - cavity - compose(windows) - compose(notches) - compose(slots)
tray = tray + compose(posts) + compose(bumps)

mesh = tray.to_mesh()
tris = len(mesh.tri_verts)

# ---- write binary STL ------------------------------------------------------
import struct
V = mesh.vert_properties[:, :3]
F = mesh.tri_verts
from enclosure_geom import MODEL_DIR
base = os.path.dirname(os.path.abspath(__file__))
buf = bytearray(b"\0"*80 + struct.pack("<I", len(F)))
for f in F:
    a, b, c = V[f[0]], V[f[1]], V[f[2]]
    ux, uy, uz = b - a
    vx, vy, vz = c - a
    nx, ny, nz = uy*vz-uz*vy, uz*vx-ux*vz, ux*vy-uy*vx
    L = math.sqrt(nx*nx+ny*ny+nz*nz) or 1.0
    buf += struct.pack("<12fH", nx/L, ny/L, nz/L, *a, *b, *c, 0)
open(os.path.join(MODEL_DIR, "matrix-tray.stl"), "wb").write(buf)

print(f"tray outer  {OX:.2f} x {OY:.2f} x {D:.2f} mm")
print(f"z-levels    face 0-{FACE_T}  matrix {FACE_T}-{Z_MAT_BACK}  "
      f"gap {Z_MAT_BACK}-{Z_BP_FRONT}  backpack {Z_BP_FRONT}-{Z_BP_BACK}")
print(f"triangles   {tris}   windows {len(windows)}  posts {len(posts)}  "
      f"fingers {len(finger_x)*2}")

# ---- validate + cross-section preview -------------------------------------
try:
    import trimesh, numpy as np
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    tm = trimesh.Trimesh(vertices=np.asarray(V), faces=np.asarray(F), process=False)
    print(f"watertight={tm.is_watertight}  winding_ok={tm.is_winding_consistent}  "
          f"volume={tm.volume/1000:.2f} cm^3  euler={tm.euler_number}")
    sp = os.environ.get("PREVIEW_DIR", base)
    zs = [FACE_T/2, (FACE_T+Z_MAT_BACK)/2, (Z_MAT_BACK+Z_BP_FRONT)/2,
          (Z_BP_FRONT+Z_BP_BACK)/2, Z_BP_BACK + LIP_RUN*0.5]
    names = ["face+windows", "matrix+posts", "gap", "backpack", "snap wedges"]
    fig, ax = plt.subplots(len(zs), 1, figsize=(11, 1.9*len(zs)))
    for a, z, nm in zip(ax, zs, names):
        sec = tm.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        a.set_title(f"z={z:.1f}  {nm}", fontsize=9, loc="left")
        if sec is not None:
            p2, _ = sec.to_planar()
            for ent in p2.entities:
                pts = p2.vertices[ent.points]
                a.plot(pts[:, 0], pts[:, 1], "k", lw=0.8)
        a.set_aspect("equal"); a.set_xlim(-2, OX+2); a.set_ylim(-2, OY+2)
        a.tick_params(labelsize=6)
    fig.tight_layout(); fig.savefig(os.path.join(sp, "tray_sections.png"), dpi=110)
    print("preview -> tray_sections.png")
except Exception as e:
    print("preview/validate skipped:", e)
