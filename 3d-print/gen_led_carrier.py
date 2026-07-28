#!/usr/bin/env python3
"""LED CARRIER -- PART 6. The plate the SK6812 pixels actually live on.

The pixels are CUT STRIP SEGMENTS, one per crescent row, not one continuous run. They have to sit
at a known standoff behind the opal acrylic, because DIFF_GAP is the entire
reason the diffuser reads as an even glow rather than a row of dots. Sticking them to
the inside of a curved cavity wall will not hold that, so they get their own
flat plate which screws onto the back of the front module.

    HOW IT ASSEMBLES (all from behind, module face down):
      1. opal acrylic drops into its pocket
      2. strips are stuck to THIS plate, between the end stops
      3. plate lands on the cavity wall's back face
      4. M2.5 self-tappers into the pads on the wall's inner face

    PRINT FACE DOWN -- "face" being the side the strips stick to. The end stops
    then grow upward off the bed and the strip-bearing surface is the bottom
    layer, so it comes out flat. A warped carrier is a varying air gap, which is
    visible through the diffuser.

>>> THE STOPS ARE STOPS, NOT CHANNELS. LED_ROW_PITCH is 11.0 and the ribbon is
>>> STRIP_W = 10.0, so a dividing wall between rows has 1.0 mm to live in -- half
>>> a millimetre a side, under one nozzle width on a 0.4 mm setup. Blocks at each
>>> row's two ends locate the segments; the adhesive backing holds them.
>>>
>>> AND THEY ARE ONLY STOP_W = 3.0 ACROSS, not the ribbon's full 10. The stops
>>> sit at the row ENDS -- the same perimeter the fixing pads need -- and at full
>>> ribbon width they blocked every usable pad angle below 20 deg. See the band
>>> table this run prints.

Geometry comes from enclosure_geom.py. Nothing here re-derives a dimension that
the front module also depends on -- the two parts bolt together, so every shared
number is imported or asserted.

Needs manifold3d:
    .venv/bin/python gen_led_carrier.py
Outputs led-carrier.stl (+ a preview).
"""
import math
import os

from manifold3d import CrossSection, Manifold

from enclosure_geom import (
    CARRIER_FIX_DEG,
    CARRIER_CLR_D, CARRIER_SKIRT, CARRIER_T, CARRIER_Z0, CAV_R_G, CAV_RY_G,
    CAV_WALL, CRES_PX, CRES_R, CRES_RY, CRES_Y, DIFF_GAP, DIFF_LIP, DIFF_R_G,
    DIFF_REBATE, DIFF_RY_G, LED_D, LED_PITCH, LED_ROW_PITCH, LED_STRIP_T,
    MIC_Y1, PAD_PILOT_D, PAD_W, STOP_H, STOP_T, STOP_W, STRIP_END_CLR, STRIP_W,
    W, carrier_pads, crescent_row_ys, crescent_rows, pad_clearances,
    strip_stops, CARRIER_SCREW, pad_angle_bands,
)

SEG = 96
BED = 220.0           # Flashforge Adventurer 5M Pro

# --- print parameters (things a drawing does not fix) ----------------------
EDGE_CLR   = 0.35     # carrier outline inset from the cavity wall's outer face
STOP_CHAM  = 0.4      # chamfer on the stop's inner top edge, a lead-in for the
                      #   strip so it does not have to be threaded in squarely
CORNER_R   = 1.5      # break on the skirt's two bottom corners

_out = []


def say(s):
    _out.append(s)
    print(s)


# ---------------------------------------------------------------------------
# 2D helpers -- built in CRESCENT coordinates: x from the centreline, y above
# the crescent baseline. That is the frame carrier_pads() and crescent_rows()
# both work in, so nothing needs translating on the way in.
# ---------------------------------------------------------------------------
def poly(pts):
    return CrossSection([[(float(x), float(y)) for x, y in pts]])


def rect2(x0, y0, w, h):
    return poly([(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h)])


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


def outline():
    """Half-ellipse with a skirt, matching the cavity wall's OUTER face inset by
    EDGE_CLR.

    >>> THE SKIRT IS NOT DECORATION. Row 0's centre sits LED_D/2 above the
    >>> crescent baseline, but the RIBBON is STRIP_W wide -- so it hangs
    >>> (STRIP_W - LED_D)/2 = 2.4 mm BELOW the baseline. Without a skirt the
    >>> bottom row is unsupported along its whole lower edge and peels.
    """
    a, b = CAV_R_G - EDGE_CLR, CAV_RY_G - EDGE_CLR
    pts = [(a, 0.0)]
    for i in range(1, SEG):
        t = math.pi * i / SEG
        pts.append((a * math.cos(t), b * math.sin(t)))
    pts.append((-a, 0.0))
    # skirt, with the two bottom corners broken
    yb = -CARRIER_SKIRT
    pts.append((-a, yb + CORNER_R))
    for i in range(1, 6):
        t = math.pi + (math.pi / 2) * i / 6
        pts.append((-a + CORNER_R + CORNER_R * math.cos(t),
                    yb + CORNER_R + CORNER_R * math.sin(t)))
    pts.append((a - CORNER_R, yb))
    for i in range(1, 6):
        t = -math.pi / 2 + (math.pi / 2) * i / 6
        pts.append((a - CORNER_R + CORNER_R * math.cos(t),
                    yb + CORNER_R + CORNER_R * math.sin(t)))
    return poly(pts)


# ---------------------------------------------------------------------------
# BODY
# ---------------------------------------------------------------------------
# z = 0 is the STRIP-BEARING FACE. The part is modelled with the stops growing
# in +z, which is also the print orientation.
body = slab(outline(), 0.0, CARRIER_T)

rows = crescent_rows()
ys = crescent_row_ys()

# --- strip end stops --------------------------------------------------------
# A cut segment of n pixels is n FULL pitches of ribbon, not (n-1): the cut lines
# sit half a pitch outboard of the end LEDs. That is the length the stops have to
# bracket, and it is what makes the bottom row the binding case -- see
# enclosure_geom.ribbon_cap.
# strip_stops() is the shared definition -- gen_front_plate.py picks its pad
# angles by clearing these, so the two must not be derived twice.
stops = strip_stops()
adds = [slab(rect2(x - STOP_T / 2, y - STOP_W / 2, STOP_T, STOP_W),
             CARRIER_T, CARRIER_T + STOP_H)
        for x, y in stops]
body = body + union(adds)

# --- screw clearance holes --------------------------------------------------
# Straight through. No counterbore: the plate is only CARRIER_T = 2.5 thick and
# a counterbore in that leaves nothing for the head to pull against. The heads
# stand proud on the back, into ~37 mm of free interior depth.
holes = [cyl(px, py, -1.0, CARRIER_T + 1.0, CARRIER_CLR_D)
         for px, py, _ in carrier_pads()]
body = body - union(holes)

# ---------------------------------------------------------------------------
# EXPORT
# ---------------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))


def write_stl(solid, name):
    import struct
    m = solid.to_mesh()
    V, F = m.vert_properties[:, :3], m.tri_verts
    with open(os.path.join(HERE, name), "wb") as f:
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


part = body.translate((0.0, CARRIER_SKIRT, 0.0))     # origin at its own corner
nf = write_stl(part, "led-carrier.stl")
bb = part.bounding_box()

say(f"wrote led-carrier.stl   {nf} triangles")
say(f"bbox        {bb[3]-bb[0]:.2f} x {bb[4]-bb[1]:.2f} x {bb[5]-bb[2]:.2f} mm")
say(f"plate       {CARRIER_T} thick, skirt {CARRIER_SKIRT} below the baseline")
say(f"seats at    z={CARRIER_Z0} on the front module (back face of the cavity "
    f"wall); strip face is z={CARRIER_Z0} -> LEDs at {DIFF_GAP} behind the acrylic")
say(f"stops       {len(stops)} blocks, {STOP_T} x {STOP_W} x {STOP_H} tall, "
    f"{STRIP_END_CLR} clearance per end")
say(f"fixings     {len(carrier_pads())}x M{CARRIER_SCREW} clearance "
    f"{chr(216)}{CARRIER_CLR_D} into {chr(216)}{PAD_PILOT_D} pilots in the wall pads")
say("")
say(f"strip segments ({CRES_PX} px on {len(rows)} rows at {LED_ROW_PITCH} pitch)")
say(f"  {'row':>3} {'px':>3} {'LED span':>9} {'ribbon':>8} {'stop gap':>9} "
    f"{'y':>7}")
for i, ((chord, n, run), y) in enumerate(zip(rows, ys)):
    seg = run + LED_PITCH
    say(f"  {i:>3} {n:>3} {run:9.1f} {seg:8.1f} "
        f"{seg + 2*STRIP_END_CLR:9.1f} {y:7.2f}")

# ---------------------------------------------------------------------------
# CHECKS
# ---------------------------------------------------------------------------
bad = []


def chk(name, v, lo=0.0):
    ok = v >= lo - 1e-6
    say(f"  {'ok  ' if ok else 'FAIL'} {v:8.2f}   {name}")
    if not ok:
        bad.append(name)


say("")
say("pad angle bands -- where a fixing clears pixels, stops AND ribbons")
say("  (CARRIER_FIX_DEG is picked from this; re-read it, do not nudge by eye)")
for _lo, _hi, _best, _at in pad_angle_bands():
    _used = any(abs(_at - d) <= (_hi - _lo) / 2 + 0.3 for d in CARRIER_FIX_DEG)
    say(f"  {_lo:6.1f} - {_hi:6.1f} deg   best {_best:5.2f} mm at {_at:6.1f}"
        f"{'   <- used' if _used else ''}")
say("  NOTE no band at 90 deg: the top row's ribbon crosses the apex.")

say("")
say("clearances")
# The plate has to reach the pads, and the pads have to be under the plate.
_pad_r = max(math.hypot(px, py) for px, py, _ in carrier_pads())
chk("every pad falls inside the carrier outline",
    min((CAV_R_G - EDGE_CLR) - abs(px) for px, py, _ in carrier_pads()))
chk("screw head land: hole to plate edge",
    min(_edge for _edge in [
        min(math.hypot(px - (CAV_R_G - EDGE_CLR) * math.cos(t),
                       py - (CAV_RY_G - EDGE_CLR) * math.sin(t))
            for t in [j * math.pi / 400 for j in range(401)])
        for px, py, _ in carrier_pads()]) - CARRIER_CLR_D / 2)
chk("skirt supports row 0's ribbon",
    CARRIER_SKIRT - (STRIP_W / 2 - LED_D / 2))
chk("skirt clear of the mic channel",
    (CRES_Y - CARRIER_SKIRT) - MIC_Y1)
# Stops must not foul the cavity wall they sit inside, and must not shade a pixel.
chk("stops inside the cavity wall",
    min((DIFF_R_G) - (abs(x) + STOP_T / 2) for x, y in stops))
chk("row pitch vs ribbon width (why there are no channels)",
    LED_ROW_PITCH - STRIP_W)
chk("stop shorter than the air gap", DIFF_GAP - (LED_STRIP_T + STOP_H))
chk("fits the bed (x)", BED - (bb[3] - bb[0]))
chk("fits the bed (y)", BED - (bb[4] - bb[1]))

# The pads are round bosses on an elliptical wall; a stop landing on one would
# stand the strip off the plate. Check every stop against every pad.
# True rectangle-to-circle gap, not circumscribed radii: the stop is 1.6 x 3.0,
# so a bounding circle overstates it by 1.7 mm and would reject good layouts.
chk("stops clear of the fixing pads", min(ds for _, _, ds, _ in pad_clearances()))
chk("pads clear of the pixels",       min(dl for _, dl, _, _ in pad_clearances()))
chk("pads clear of the ribbons",      min(dr for _, _, _, dr in pad_clearances()))

try:
    import trimesh
    tm = trimesh.load(os.path.join(HERE, "led-carrier.stl"))
    say("")
    say(f"watertight={tm.is_watertight}  winding_ok={tm.is_winding_consistent}  "
        f"volume={tm.volume/1000:.1f} cm^3")
    n_bodies = len(tm.split(only_watertight=False))
    say(f"connected bodies={n_bodies}  (must be 1)")
    if not tm.is_watertight:
        bad.append("not watertight")
    if n_bodies != 1:
        bad.append(f"{n_bodies} disconnected bodies")
except ImportError:
    say("validate skipped: no trimesh")

say("")
say("ALL CLEAR" if not bad else f"*** {len(bad)} PROBLEM(S) ***")


# ---------------------------------------------------------------------------
# PREVIEW
# ---------------------------------------------------------------------------
def preview():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import Circle, Rectangle
    except ImportError:
        return
    fig, ax = plt.subplots(figsize=(13, 6))
    a, b = CAV_R_G - EDGE_CLR, CAV_RY_G - EDGE_CLR
    t = [i * math.pi / 200 for i in range(201)]
    ax.plot([a * math.cos(u) for u in t], [b * math.sin(u) for u in t],
            color="#334", lw=1.4)
    ax.plot([-a, -a, a, a], [0, -CARRIER_SKIRT, -CARRIER_SKIRT, 0],
            color="#334", lw=1.4)
    ax.plot([CRES_R * math.cos(u) for u in t], [CRES_RY * math.sin(u) for u in t],
            color="#c66", lw=0.9, ls="--")
    for (chord, n, run), y in zip(rows, ys):
        seg = run + LED_PITCH
        ax.add_patch(Rectangle((-seg / 2, y - STRIP_W / 2), seg, STRIP_W,
                               fc="#dde6f2", ec="#8899aa", lw=0.6))
        for i in range(n):
            x = (-run / 2 + i * LED_PITCH) if n > 1 else 0.0
            ax.add_patch(Circle((x, y), LED_D / 2, fc="#ffd", ec="#aa8", lw=0.5))
    for x, y in stops:
        ax.add_patch(Rectangle((x - STOP_T / 2, y - STOP_W / 2), STOP_T, STOP_W,
                               fc="#556", ec="none"))
    for px, py, deg in carrier_pads():
        ax.add_patch(Circle((px, py), PAD_W / 2, fc="none", ec="#3a7", lw=1.0))
        ax.add_patch(Circle((px, py), CARRIER_CLR_D / 2, fc="#3a7", ec="none"))
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("LED carrier - strips, end stops, fixings\n"
                 "red dashed = diffuser edge   green = fixing pads",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "led-carrier.png"), dpi=170)
    print("preview -> led-carrier.png")


preview()
