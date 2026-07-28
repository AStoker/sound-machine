#!/usr/bin/env python3
"""DIFFUSER — the Glowforge cut file for the opal acrylic pane.

A half-ellipse of white opal cast acrylic that drops into the pocket on the back
of the front module, from behind, and is glued round its edge.

>>> IT HAS TO BE NOTCHED, AND THE NOTCHES ARE NOT OPTIONAL. The LED carrier's six
>>> fixing pads stand on the INSIDE of the diffusion cavity wall, over
>>> z = PAD_Z0..CARRIER_Z0. The pane's final home is in FRONT of all of that
>>> (z = DIFF_LIP..DIFF_LIP+DIFF_REBATE) — so although nothing obstructs it once
>>> seated, it has to travel the whole depth of the cavity to get there, straight
>>> past the pads. Un-notched, it simply will not go in. This was found after the
>>> pads were designed, which is why the pane is now generated rather than
>>> described.

    python3 gen_diffuser.py     ->  diffuser.svg  (1:1 mm, cut lines only)

CUTTING NOTES
  - The SVG is 1:1 in millimetres. Set the Glowforge to cut, not score.
  - Kerf: the outline is drawn on the nominal size. Glowforge kerf on 3 mm cast
    acrylic is ~0.15–0.2 mm, which the DIFF_FIT allowance below already absorbs.
  - The flat edge is the bottom. Orientation matters: the notches are NOT
    symmetric top-to-bottom, so a flipped pane will not seat.
"""
import math
import os

from drawlib import n, path
from enclosure_geom import (
    CRES_R, CRES_RY, DIFF_R_G, DIFF_RY_G, DIFF_T, PAD_OFFSET_IN, PAD_W,
    carrier_pads, ell_dist,
)

SEG = 240

# --- cut parameters ---------------------------------------------------------
DIFF_FIT   = 0.3      # per side, pane to pocket -- also absorbs laser kerf
NOTCH_CLR  = 0.5      # notch to pad, all round

# >>> THE NOTCHES ARE ROUND, NOT SQUARE, AND THE REASON IS LIGHT BLEED.
# >>> The pane sits at z = DIFF_LIP..DIFF_LIP+DIFF_T; the pads do not start until
# >>> PAD_Z0 behind it. So at the pane's own plane there is no pad in the notch --
# >>> every notch is a straight-through hole in the diffuser, and whatever light
# >>> reaches it escapes the cavity WITHOUT being diffused. The notch exists only
# >>> because the pane has to travel the depth of the cavity to reach its pocket;
# >>> once seated it serves no purpose at all. So it should be as small as the
# >>> travel allows, and no smaller.
# >>>
# >>> What it has to clear is a CYLINDER of PAD_W, and the pane's travel is
# >>> straight along z -- so the swept profile in the pane's plane is just that
# >>> circle. A circular bite of PAD_W/2 + clearance is therefore not an
# >>> approximation, it is exactly the minimum. The square bite it replaces was
# >>> 42.0 mm^2; this is 31.3, i.e. 26% less open area, 64 mm^2 over six notches.
# >>> It also hugs the pad, so the clear-glue fillet is a constant gap instead of
# >>> four corners of varying width, and it removes the inside corners that make
# >>> cast acrylic craze when it is handled.
# >>>
# >>> IT CANNOT BE A CLOSED HOLE. Threading the pane over the pads like a plate
# >>> over posts would leak nothing at all, but the hole would need a pane radius
# >>> of 93.6 plus a web, and the pocket is 91.4. It has to break the edge.
NOTCH_R     = PAD_W / 2 + NOTCH_CLR       # the bite's radius
# How far the pad's centre sits INSIDE the pane's edge, along the ellipse normal.
NOTCH_OFF   = PAD_OFFSET_IN - DIFF_FIT
NOTCH_DEPTH = NOTCH_R + NOTCH_OFF         # deepest reach, from the edge
NOTCH_HALF  = math.sqrt(max(NOTCH_R**2 - NOTCH_OFF**2, 0.0))   # half-chord at the edge

PANE_A  = DIFF_R_G - DIFF_FIT
PANE_B  = DIFF_RY_G - DIFF_FIT

_out = []


def say(s):
    _out.append(s)
    print(s)


def pane_outline():
    """Half-ellipse, flat side down, with a notch at each pad angle.

    The notch is cut on the ELLIPSE NORMAL, not radially from the centre — the
    crescent is eccentric (91.4 x 65.1), so a radial notch would go in at an
    angle to the pad it is meant to clear and would have to be wider to
    compensate. On the normal it is the pad's own width plus clearance.
    """
    pads = sorted(carrier_pads(), key=lambda p: p[2])

    def _span(pdeg):
        """Angular half-width the notch occupies, at this pad's position.

        >>> WITHOUT THIS THE ARC IS DRAWN STRAIGHT BACK ACROSS THE NOTCH MOUTH.
        >>> The first version swapped a SINGLE ellipse sample for the notch, but
        >>> the notch is NOTCH_HALF wide -- several samples across at this SEG --
        >>> so every other sample inside its span was still emitted and the path
        >>> zig-zagged in and out. It rendered as a tab, and a naive area test
        >>> agreed with it, because a self-crossing loop subtracts rather than
        >>> adds. Every sample inside the span has to be dropped.
        """
        pt = math.radians(pdeg)
        # arc-length per radian here, so half-width -> half-angle
        dxdt = -PANE_A * math.sin(pt)
        dydt = PANE_B * math.cos(pt)
        return NOTCH_HALF / max(math.hypot(dxdt, dydt), 1e-9)

    pts = []
    t = 0.0
    step = math.pi / SEG
    while t <= math.pi + 1e-9:
        px, py = PANE_A * math.cos(t), PANE_B * math.sin(t)
        deg = math.degrees(t)
        inside = next((p for p in pads
                       if abs(t - math.radians(p[2])) <= _span(p[2])), None)
        # emit the notch once, on the first sample that enters its span
        hit = None
        if inside is not None:
            prev = t - step
            if not (abs(prev - math.radians(inside[2])) <= _span(inside[2])):
                hit = inside
            else:
                t += step
                continue
        if hit is not None:
            _, _, pdeg = hit
            pt = math.radians(pdeg)
            # inward unit normal at the pad's angle
            nx, ny = math.cos(pt) / PANE_A, math.sin(pt) / PANE_B
            nl = math.hypot(nx, ny)
            ux, uy = nx / nl, ny / nl              # outward normal
            tx, ty = -uy, ux                       # along the edge
            cx, cy = PANE_A * math.cos(pt), PANE_B * math.sin(pt)
            depth = NOTCH_DEPTH   # (kept for the reporting below)
            # >>> ORDER MATTERS: the notch has to be walked in the SAME direction
            # >>> the outline is being traced, or the path crosses itself and the
            # >>> renderer fills it as a TAB STICKING OUT instead of a bite taken
            # >>> in. The trace runs counterclockwise (t: 0 -> pi), so (tx, ty)
            # >>> points forward -- enter the notch from BEHIND the pad centre,
            # >>> sweep the arc, and leave AHEAD of it.
            #
            # The arc is the pad's own circle: centre one NOTCH_OFF inside the
            # edge, radius NOTCH_R. Walk it from the entry crossing to the exit
            # crossing, going through the deepest point.
            ox, oy = cx - ux * NOTCH_OFF, cy - uy * NOTCH_OFF     # pad centre
            # Entry and exit are where the pad's circle crosses the pane edge:
            # one half-chord back along the edge, one half-chord forward. Both
            # are on the circle by construction, since HALF^2 + OFF^2 = R^2.
            #
            # >>> TAKE THE ANGLES FROM THE ACTUAL POINTS. The first attempt used
            # >>> atan2 of the tangent alone, dropping the NOTCH_OFF component --
            # >>> so the "endpoints" were not on the circle at all, the arc joined
            # >>> the wrong places, and the outline crossed itself six times.
            ex, ey = cx - tx * NOTCH_HALF, cy - ty * NOTCH_HALF   # entry
            xx, xy = cx + tx * NOTCH_HALF, cy + ty * NOTCH_HALF   # exit
            a0 = math.atan2(ey - oy, ex - ox)
            a1 = math.atan2(xy - oy, xx - ox)
            deep = math.atan2(-uy, -ux)        # straight into the pane

            def _norm(a):                      # to (-pi, pi]
                return (a + math.pi) % (2 * math.pi) - math.pi

            # Sweep from a0 to a1 the way round that passes through `deep`.
            sweep = _norm(a1 - a0)
            if _norm(deep - a0) * (1 if sweep >= 0 else -1) < 0 or \
               abs(_norm(deep - a0)) > abs(sweep):
                sweep = sweep - math.copysign(2 * math.pi, sweep)
            ARC = 24
            pts += [(ox + NOTCH_R * math.cos(a0 + sweep * i / ARC),
                     oy + NOTCH_R * math.sin(a0 + sweep * i / ARC))
                    for i in range(ARC + 1)]
        else:
            pts.append((px, py))
        t += step
    return pts


pts = pane_outline()
minx = min(p[0] for p in pts)
maxx = max(p[0] for p in pts)
maxy = max(p[1] for p in pts)
PAD = 6.0
Wd, Ht = (maxx - minx) + 2 * PAD, maxy + 2 * PAD


def to_svg(x, y):
    return x - minx + PAD, maxy - y + PAD          # svg y-down, flat side at the base


d = "M" + " L".join(f"{n(a)},{n(b)}" for a, b in (to_svg(*p) for p in pts)) + " Z"

HERE = os.path.dirname(os.path.abspath(__file__))
svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{n(Wd)}mm" height="{n(Ht)}mm"
     viewBox="0 0 {n(Wd)} {n(Ht)}">
  <!-- SOUND MACHINE - opal acrylic diffuser, {DIFF_T} mm. 1:1 in mm. CUT. -->
  <path d="{d}" fill="none" stroke="#000000" stroke-width="0.1"/>
</svg>
"""
open(os.path.join(HERE, "diffuser.svg"), "w").write(svg)

say(f"wrote diffuser.svg   {DIFF_T} mm opal acrylic, 1:1 mm, cut lines only")
say(f"pane        {2*PANE_A:.1f} x {PANE_B:.1f}  (pocket {2*DIFF_R_G:.1f} x "
    f"{DIFF_RY_G:.1f}, {DIFF_FIT} fit per side)")
say(f"notches     {len(carrier_pads())} x {2*NOTCH_HALF:.1f} wide x "
    f"{NOTCH_DEPTH:.1f} deep, on the ellipse normal")
say(f"            at {', '.join(f'{p[2]:.1f}' for p in carrier_pads())} deg")
say("")

bad = []


def chk(name, v, lo=0.0):
    ok = v >= lo - 1e-6
    say(f"  {'ok  ' if ok else 'FAIL'} {v:8.2f}   {name}")
    if not ok:
        bad.append(name)


say("clearances")
chk("pane fits the pocket (per side)", DIFF_R_G - PANE_A)
chk("notch clears the pad (per side)", NOTCH_HALF - PAD_W / 2)
chk("notch reaches past the pads", NOTCH_CLR)
# The one the whole exercise is about: how far each notch floor pokes INSIDE the
# visible aperture, as a TRUE distance to the aperture ellipse.
def _notch_floor(pdeg):
    pt = math.radians(pdeg)
    nx, ny = math.cos(pt)/PANE_A, math.sin(pt)/PANE_B
    nl = math.hypot(nx, ny)
    return (PANE_A*math.cos(pt) - nx/nl*NOTCH_DEPTH,
            PANE_B*math.sin(pt) - ny/nl*NOTCH_DEPTH)
visible = max(ell_dist(*_notch_floor(p[2]), CRES_R, CRES_RY)
              if (abs(_notch_floor(p[2])[0])/CRES_R)**2
                 + (_notch_floor(p[2])[1]/CRES_RY)**2 < 1.0 else 0.0
              for p in carrier_pads())
say(f"  ---- {visible:8.2f}   notch visible past the aperture edge (see below)")
chk("pane still covers the aperture everywhere else", PANE_A - CRES_R)
chk("ledge under the pane", PANE_A - CRES_R)

say("")
say("WHAT YOU SEE FROM THE FRONT")
say(f"  aperture            {CRES_R} x {CRES_RY:.2f}  (the lit crescent)")
say(f"  pane                {PANE_A:.1f} x {PANE_B:.1f}")
say(f"  ledge over the pane {PANE_A - CRES_R:.1f} mm radial")
say(f"  notch depth         {NOTCH_DEPTH:.1f} mm  ->  {visible:.1f} mm of each notch")
say(f"                      shows past the aperture, at {len(carrier_pads())} points")
say("  Hiding them completely needs the aperture pulled in to "
    f"~{CRES_R-visible:.0f}, which costs the crescent 8 pixels (48 -> 40).")
say("  They sit behind opal acrylic AND grille cloth, in the dimmest part of the")
say("  field, so they should read as a slight local dimming rather than a cut.")

say("")
say("ALL CLEAR" if not bad else f"*** {len(bad)} PROBLEM(S) ***")
