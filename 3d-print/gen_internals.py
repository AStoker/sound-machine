#!/usr/bin/env python3
"""SHEET 2 of 3 -- internals, fixings and the front module.

Shows how the three printed parts actually go together:

  * the FRONT MODULE as one part -- facade + diffuser pocket + diffusion cavity
    + matrix pocket + speaker baffle rings + mic channel -- viewed from behind
  * SECTION A-A on the centreline, through the whole depth stack
  * the BOTTOM PLATE as a chassis carrying the ReSpeaker Flex and the UPS pack
  * the DOME UNDERSIDE, showing where the six M3 bosses can physically go
  * DETAIL B, the slide-up slot joint, at 4:1
  * DETAIL C, the diffuser stack, at 4:1

Assembly order is the point of the sheet:
    1. front module slides UP into the dome's side grooves from below
    2. it seats against the lip; nothing holds it yet
    3. bottom plate goes on and traps its bottom edge
    4. six M3 screws pull the bottom plate up into the dome bosses

Geometry comes from enclosure_geom.py -- this sheet never invents a dimension.

    python3 gen_internals.py
    rsvg-convert -b white -z 2 enclosure-internals.svg -o enclosure-internals.png
"""
import os

from drawlib import *
from enclosure_geom import *

SHEET_W, SHEET_H = 1189.0, 690.0
MARGIN = 15.0

FM_Z0 = LIP_T                      # front module front face, behind the lip
DIFF_R = CRES_R + DIFF_MARGIN      # diffuser pocket radius
CAV_R = DIFF_R + CAV_WALL          # diffusion cavity outer wall


# ------------------------------------------------- front module, from behind
def fm_profile():
    """Front module outline: the D at the sliding inset, bottom cut off at the
    bottom plate's top face (that face is the module's datum)."""
    inset, rb = REVEAL, R_BOT - REVEAL
    x0, x1 = inset, W - inset
    yb, ys = fy(BP_T), fy(ARCH_Y)
    r = ARCH_R - inset
    return (f"M{n(x0)},{n(yb)} V{n(ys)} "
            f"A{n(r)},{n(r)} 0 0 1 {n(x1)},{n(ys)} "
            f"V{n(yb)} Z")


def fm_rear():
    o = [path(fm_profile(), "obj")]
    # band that runs in the dome groove
    o.append(path(fm_profile(), "phan"))
    o.append(semi(W/2, fy(CRES_Y), DIFF_R, "obj"))        # diffuser pocket
    o.append(semi(W/2, fy(CRES_Y), CAV_R, "obj"))         # cavity outer wall
    o.append(semi(W/2, fy(CRES_Y), LED_R, "hid"))         # LED field arc (< diffuser)
    # the two matrices, the open aperture behind them, and the retention that
    # holds them: each board located by its OWN posts (they are only loosely
    # soldered to each other), the pair clamped by clips on all four sides
    _mx0, _my0 = W/2 - TRAY_W/2, TRAY_Y0
    o.append(rect(_mx0, fy(CLK_Y+TRAY_H/2), TRAY_W, TRAY_H, "phan"))
    o.append(line(W/2, fy(TRAY_Y1), W/2, fy(TRAY_Y0), "phan"))   # the seam
    o.append(rect(W/2-CLK_W/2, fy(CLK_Y+CLK_H/2), CLK_W, CLK_H, "hid", 2))
    for _b in range(MTX_N):
        for _hx, _hy in MTX_HOLES:
            o.append(circ(_mx0 + _b*MTX_BOARD_W + _hx, fy(_my0 + _hy), 1.85))
    for _cx in (W/2 - TRAY_W/4, W/2 + TRAY_W/4):                 # top + bottom
        for _cy, _s in ((TRAY_Y0, -1), (TRAY_Y1, 1)):
            o.append(rect(_cx - 3, fy(_cy + _s*2.45 + (0 if _s < 0 else 0)),
                          6, 2.2, "obj"))
    for _cx, _s in ((_mx0, -1), (_mx0 + TRAY_W, 1)):             # the two ends
        o.append(rect(_cx + (0 if _s > 0 else -2.45), fy(CLK_Y + 3),
                      2.2, 6, "obj"))
    # speaker seats: square body pockets + a SIDE-MOUNT POST beside each flank.
    # The speaker has no baffle bolt pattern -- it hangs off one nub per side,
    # so the module grows a post there instead of a ring of face screws.
    for sx in (SPK_X, W-SPK_X):
        o.append(rect(sx-SPK_BODY_W/2-SPK_SEAT_W, fy(SPK_SEAT_Y1),
                      SPK_BODY_W+2*SPK_SEAT_W, SPK_BODY_H+2*SPK_RING_W, "obj", 3))
        o.append(rect(sx-SPK_BODY_W/2, fy(SPK_Y1), SPK_BODY_W, SPK_BODY_H, "obj", 2))
        o.append(circ(sx, fy(SPK_Y), SPK_GRILLE, "hid"))
        for sgn in (-1, 1):
            px = sx + sgn * (SPK_BODY_W/2 + SPK_NUB_PROJ/2)
            # the post the nub lands on, and its screw
            o.append(rect(px - (SPK_NUB_PROJ + SPK_POST_WALL)/2,
                          fy(SPK_NUB_Y + SPK_NUB_H/2 + 1.5),
                          SPK_NUB_PROJ + SPK_POST_WALL, SPK_NUB_H + 3, "obj", 1))
            o.append(circ(px, fy(SPK_NUB_Y), SPK_NUB_SCREW, "hid"))
            # stiffening ribs -- a 4 mm plate with a sealed box on it will buzz
            o.append(line(sx + sgn*(SPK_BODY_W/2+SPK_SEAT_W), fy(SPK_Y1 - 8),
                          sx + sgn*(SPK_BODY_W/2+SPK_SEAT_W+14), fy(SPK_Y1 - 8), "obj"))
    # mic flex channel + ports
    o.append(rect(W/2-MIC_PCB_W/2-1, fy(MIC_Y1+1), MIC_PCB_W+2, MIC_PCB_H+2, "obj", 1))
    for mx in mic_x():
        o.append(circ(mx, fy(MIC_Y), MIC_PORT_D, "hid"))
        o.append(circ(mx, fy(MIC_Y), MIC_PORT_D + 2*MIC_GASKET, "phan"))
    return o


def fm_dims():
    o = [cl_v(W/2, -10, H + 6)]
    o.append(dim_h(0, W, H + 26, dt(W - 2*REVEAL), ext=H))
    o.append(dim_v(fy(H - REVEAL), fy(BP_T), -22,
                   dt(H - REVEAL - BP_T), ext=W/2 - 30))
    o.append(leader(W/2 - DIFF_R*0.72, fy(CRES_Y + DIFF_R*0.69), -18, -14,
                    f"diffuser pocket R{dt(DIFF_R)} x {dt(DIFF_REBATE)} deep", "end"))
    o.append(leader(W/2 - CAV_R*0.42, fy(CRES_Y + CAV_R*0.9), -14, -26,
                    f"cavity wall {dt(CAV_WALL)}, R{dt(CAV_R)}", "end"))
    o.append(leader(W/2 + LED_R*0.6, fy(CRES_Y + LED_R*0.79), 44, -18,
                    f"SK6812 strip seats at R{dt(LED_R)} - {dt(CRES_FADE)} inside "
                    f"the R{dt(CRES_R)} diffuser, so the glow fades out"))
    o.append(leader(W/2 - TRAY_W/4, fy(TRAY_Y0), -26, 42,
                    f"2x matrix - {2*MTX_N} posts + 6 clips, see note h", "end"))
    o.append(leader(W - SPK_X + (SPK_BODY_W/2+SPK_SEAT_W)*0.71,
                    fy(SPK_Y) - (SPK_BODY_W/2+SPK_SEAT_W)*0.71, 30, -30,
                    f"2x Seeed {dt(SPK_BODY_W)}x{dt(SPK_BODY_H)}x{dt(SPK_BODY_D)}"))
    o.append(leader(W - SPK_X + SPK_BODY_W/2 + SPK_NUB_PROJ/2, fy(SPK_NUB_Y),
                    32, 20, f"side post - see note g"))
    o.append(leader(W/2 - MIC_PCB_W/2, fy(MIC_Y), -22, 30,
                    f"mic flex channel {dt(MIC_CHAN_D)} deep, "
                    f"{dt(MIC_GASKET)} gasket land per port", "end"))
    o.append(leader(REVEAL, fy(ARCH_Y*0.55), -20, -34,
                    f"{dt(LIP_W - FP_CLR)} of edge runs in the dome groove", "end"))
    o.append(leader(W/2 + 30, fy(BP_T), 40, 22,
                    "bottom edge lands on the bottom plate = the datum"))
    return o


# ------------------------------------------------------------- SECTION A-A
# Centreline vertical section, viewed from the right: x = depth, y = height.
def sec_dome():
    o = [path(rrect(0, 0, D, H, R_SIDE, R_SIDE, R_SIDE_B, R_SIDE_B), "obj")]
    o.append(path(rrect(WALL, WALL, D - 2*WALL, H - 2*WALL,
                        max(R_SIDE-WALL, 1)), "obj"))
    o.append(rect(0, 0, LIP_T, WALL + LIP_W, "obj"))            # top lip in section
    o.append(rect(FM_Z0 + FP_T + SLOT_CLR, 0, RIB_T, WALL + RIB_W, "obj"))
    return o


def sec_front_module():
    o = []
    z = FM_Z0
    o.append(rect(z, fy(H - REVEAL), FP_T, H - REVEAL - BP_T, "obj"))   # facade
    # crescent: acrylic, air gap, LED strip, cavity back wall
    cy0, cy1 = fy(CRES_Y + CRES_R), fy(CRES_Y)
    o.append(rect(z + FP_T, cy0, DIFF_T, cy1 - cy0, "obj"))             # acrylic
    o.append(rect(z + FP_T + DIFF_REBATE + DIFF_GAP, cy0, LED_STRIP_T,
                  cy1 - cy0, "hid"))                                     # LED strip
    o.append(line(z + FM_DEPTH, cy0, z + FM_DEPTH, cy1, "obj"))
    # clock: tray behind the aperture
    ty0, ty1 = fy(TRAY_Y1), fy(TRAY_Y0)
    o.append(rect(z + FP_T, ty0, TRAY_D, ty1 - ty0, "hid"))
    # mic flex
    o.append(rect(z + FP_T, fy(MIC_Y1), MIC_CHAN_D, MIC_PCB_H, "obj"))
    return o


def sec_internals():
    o = [rect((D-BP_D)/2, fy(BP_T), BP_D, BP_T, "obj")]                  # plate
    o.append(rect(D - WALL - UPS_D, fy(BP_T + UPS_H),
                  UPS_D, UPS_H, "hid"))                                  # UPS
    o.append(rect(D - WALL - AMP_H, fy(AMP_WALL_Y + AMP_D/2),
                  AMP_H, AMP_D, "hid"))                                  # amp, flush
    # Flex on the rear wall: standoff, then the 20 deep board (deepest at XIAO)
    o.append(rect(D - WALL - FLEX_STANDOFF - FLEX_D, fy(FLEX_WALL_Y + FLEX_H),
                  FLEX_D, FLEX_H, "hid"))
    for _hy in (FLEX_WALL_Y + FLEX_H/2 - FLEX_HOLE_PY/2,
                FLEX_WALL_Y + FLEX_H/2 + FLEX_HOLE_PY/2):
        o.append(rect(D - WALL - FLEX_STANDOFF, fy(_hy + FLEX_BOSS_D/2),
                      FLEX_STANDOFF, FLEX_BOSS_D, "obj"))
    # a rear-wall lug, sectioned
    o.append(rect(D - WALL - LUG_L, fy(BP_T + LUG_H), LUG_L, LUG_H, "obj"))
    o.append(rect(D - WALL - LUG_L/2 - INSERT_D/2, fy(BP_T + 6), INSERT_D, 6, "hid"))
    o.append(rect(D - WALL - LUG_L/2 - SCREW_D/2, fy(BP_T + 5), SCREW_D, 5 + BP_T, "hid"))
    return o


def sec_dims():
    o = [dim_h(0, D, -20, ext=0), dim_v(0, H, D + 22, ext=D)]
    o.append(dim_h(FM_Z0, FM_Z0 + FM_DEPTH, fy(CRES_Y + CRES_R) - 8,
                   f"{dt(FM_DEPTH)} front module", ext=fy(CRES_Y + CRES_R)))
    o.append(dim_h(FM_Z0 + FP_T + DIFF_REBATE, FM_Z0 + FP_T + DIFF_REBATE + DIFF_GAP,
                   fy(CRES_Y + CRES_R*0.55), f"{dt(DIFF_GAP)} air", ext=None))
    o.append(leader(FM_Z0 + FM_DEPTH, fy(CRES_Y + CRES_R*0.3), 30, -20,
                    "clear of the UPS by "
                    f"{dt(D - WALL - UPS_D - FM_Z0 - FM_DEPTH)}"))
    o.append(leader(D - WALL - UPS_D, fy(BP_T + UPS_H), 26, -22,
                    f"UPS 3S board {dt(UPS_W)} x {dt(UPS_H)}, STANDING"))
    # everything on the rear wall calls out to the RIGHT -- to the left is the
    # FRONT MODULE panel, and long text with an "end" anchor lands on top of it
    o.append(leader(D - WALL, fy(AMP_WALL_Y), 30, 26,
                    "TPA2016 FLUSH on the rear wall"))
    o.append(leader(D - WALL - LUG_L, fy(BP_T + LUG_H), -26, 26,
                    f"wall LUG {dt(LUG_L)}x{dt(LUG_W)}x{dt(LUG_H)}", "end"))
    o.append(leader(D - WALL - FLEX_STANDOFF - FLEX_D, fy(FLEX_WALL_Y + FLEX_H),
                    36, -24,
                    f"ReSpeaker Flex {dt(FLEX_PCB_W)} x {dt(FLEX_PCB_H)} x "
                    f"{dt(FLEX_D)} deep at the XIAO"))
    o.append(leader(D - WALL - FLEX_STANDOFF, fy(FLEX_WALL_Y + FLEX_H*0.62), 30, -12,
                    f"vertical, on {dt(FLEX_STANDOFF)} standoffs "
                    f"({dt(FLEX_W)} wide over its connectors)"))
    return o


# --------------------------------------------------- bottom plate, from above
def bp_plan():
    o = [path(rrect(0, 0, BP_W, BP_D, max(R_PLAN - WALL, 1)), "obj")]
    ox, oy = (IN_W - BP_W)/2 - (WALL - WALL), (IN_D - BP_D)/2
    for name, x0, x1, d0, d1 in floor_items():
        if name.startswith("driver") or name == "matrix pair":
            cls = "phan"
        else:
            cls = "hid"
        o.append(rect(x0 - WALL - BP_CLR, d0 - WALL - BP_CLR,
                      x1 - x0, d1 - d0, cls))
    for sx, sy in SCREWS:
        cx, cy = sx - WALL - BP_CLR, sy - WALL - BP_CLR
        o.append(circ(cx, cy, SCREW_CLR, "obj"))
        o.append(circ(cx, cy, SCREW_CBORE, "obj"))
    for fx in (FOOT_IN, BP_W - FOOT_IN):
        for fy_ in (FOOT_IN, BP_D - FOOT_IN):
            o.append(circ(fx, fy_, FOOT_D, "phan"))
    return o


def bp_dims():
    o = [dim_h(0, BP_W, -12, ext=0), dim_v(0, BP_D, -14, ext=0)]
    o.append(txt(BP_W/2, BP_D + 32, "Flex and amp are NOT on the floor - both "
                 "mount on the rear wall. The floor carries the UPS only.",
                 "note", "middle"))
    o.append(leader(W/2 - WALL - BP_CLR, D - WALL - UPS_D - WALL - BP_CLR,
                    -30, -14, f"UPS 3S {dt(UPS_W)} x {dt(UPS_D)} footprint, board "
                    f"STANDS {dt(UPS_H)} tall", "end"))
    o.append(leader(SCREWS[0][0] - WALL - BP_CLR + SCREW_CBORE/2,
                    SCREWS[0][1] - WALL - BP_CLR, 20, 44,
                    f"6x {chr(216)}{dt(SCREW_CLR)} thru, "
                    f"{chr(216)}{dt(SCREW_CBORE)} c'bore {dt(SCREW_CB_T)} deep"))
    o.append(leader(FOOT_IN, BP_D - FOOT_IN + FOOT_D/2, -18, 22,
                    f"4x {chr(216)}{dt(FOOT_D)} feet", "end"))
    o.append(txt(BP_W/2, BP_D + 26,
                 "dashed = what sits on it   phantom = what hangs over it",
                 "note", "middle"))
    return o


# ------------------------------------------------- dome underside, looking up
def dome_under():
    o = [path(rrect(0, 0, W, D, R_PLAN), "obj")]
    o.append(path(rrect(WALL, WALL, IN_W, IN_D, max(R_PLAN - WALL, 1)), "obj"))
    o.append(path(rrect(WALL + SEAT_W, WALL + SEAT_W, IN_W - 2*SEAT_W,
                        IN_D - 2*SEAT_W, max(R_PLAN - WALL - SEAT_W, 1)), "hid"))
    # the front groove the module slides in
    o.append(rect(WALL, LIP_T, IN_W, FP_T + SLOT_CLR, "obj"))
    for sx, sy in SCREWS:
        onwall_x = sx < W/2
        if abs(sy - (D - WALL - LUG_L/2)) < 0.1:          # rear-wall lug
            o.append(rect(sx - LUG_W/2, D - WALL - LUG_L, LUG_W, LUG_L, "obj", 1))
        else:                                              # end-wall lug
            x0 = WALL if onwall_x else W - WALL - LUG_L
            o.append(rect(x0, sy - LUG_W/2, LUG_L, LUG_W, "obj", 1))
        o.append(circ(sx, sy, INSERT_D, "hid"))
    return o


def dome_under_dims():
    o = [dim_h(0, W, -12, ext=0), dim_v(0, D, -14, ext=0)]
    o.append(leader(WALL + SEAT_W, D/2, -20, 24,
                    f"{dt(SEAT_W)} continuous seating ledge, all round", "end"))
    o.append(leader(W/2, LIP_T + FP_T + SLOT_CLR, 0, 30,
                    f"front groove {dt(FP_T + SLOT_CLR)} wide - module slides UP"))
    for i, (sx, sy) in enumerate(SCREWS):
        o.append(txt(sx, sy + 1.2, str(i + 1), "dtx", "middle"))
    o.append(leader(SCREWS[1][0], SCREWS[1][1], 22, -26,
                    f"6x wall lug {dt(LUG_L)} x {dt(LUG_W)} x {dt(LUG_H)}, "
                    f"{chr(216)}{dt(INSERT_D)} for M{dt(SCREW_D)} heat-set"))
    o.append(txt(W/2, D + 30, "no lug on the FRONT edge - the speakers own both "
                 "corners and the matrix owns the middle. It does not need one:",
                 "note", "middle"))
    o.append(txt(W/2, D + 35, "the plate's front edge is captured between the "
                 "seating ledge and the front module's bottom edge.",
                 "note", "middle"))
    return o


# ------------------------------------------------------------------ details
SC = 5.0            # detail scale


def detail_slot():
    """DETAIL B -- the slide-up joint, sectioned through a side wall.
    x = radial (into the enclosure), y = depth (front face at the top)."""
    sc, wall_len, edge = SC, 14.0, 17.0
    o = [rect(0, 0, WALL*sc, wall_len*sc, "obj")]                    # dome skin
    o.append(rect(WALL*sc, 0, LIP_W*sc, LIP_T*sc, "obj"))            # lip
    o.append(rect(WALL*sc, (LIP_T + FP_T + SLOT_CLR)*sc,
                  RIB_W*sc, RIB_T*sc, "obj"))                        # rib
    o.append(rect((WALL + FP_CLR)*sc, LIP_T*sc, edge*sc, FP_T*sc, "obj"))
    o.append(line((WALL + FP_CLR + edge)*sc, LIP_T*sc,
                  (WALL + FP_CLR + edge)*sc, (LIP_T + FP_T)*sc, "phan"))
    o.append(leader(WALL*sc/2, wall_len*sc*0.8, -16, 14,
                    f"dome wall {dt(WALL)}", "end"))
    o.append(leader((WALL + LIP_W*0.6)*sc, 0, 22, -26,
                    f"lip {dt(LIP_W)} x {dt(LIP_T)} covers the edge"))
    o.append(leader((WALL + RIB_W*0.6)*sc, (LIP_T + FP_T + SLOT_CLR + RIB_T)*sc,
                    26, 20, f"rib {dt(RIB_W)} x {dt(RIB_T)}"))
    o.append(leader((WALL + LIP_W + 6)*sc, (LIP_T + FP_T)*sc, 20, 34,
                    f"front module, {dt(FP_T)} thk"))
    o.append(dim_v(LIP_T*sc, (LIP_T + FP_T + SLOT_CLR)*sc,
                   (WALL + FP_CLR + edge + 4)*sc, f"{dt(FP_T + SLOT_CLR)} groove"))
    o.append(dim_h(WALL*sc, (WALL + LIP_W)*sc, -10, dt(LIP_W), ext=0))
    o.append(txt(0, wall_len*sc + 16,
                 f"module slides UP out of the page; {dt(FP_CLR)} clearance "
                 "on the wall", "note"))
    return o


def detail_diffuser():
    """DETAIL C -- the diffusion stack, sectioned normal to the facade.
    x = depth (front face at the left), y = a slice of the crescent."""
    sc, hgt = SC, 17.0
    o, z = [], 0.0
    o.append(rect(0, 0, FP_T*sc, hgt*sc, "obj"))                       # facade
    z = FP_T
    o.append(rect(z*sc, 0, DIFF_T*sc, hgt*sc, "obj"))                  # acrylic
    o.append(line((z + DIFF_REBATE)*sc, 0, (z + DIFF_REBATE)*sc, hgt*sc, "hid"))
    z += DIFF_REBATE + DIFF_GAP
    o.append(rect(z*sc, 0, LED_STRIP_T*sc, hgt*sc, "hid"))             # strip
    o.append(rect(0, hgt*sc, (z + LED_STRIP_T)*sc, CAV_WALL*sc, "obj"))
    rows = [(FP_T/2, f"facade {dt(FP_T)}"),
            (FP_T + DIFF_T/2, f"opal acrylic {dt(DIFF_T)} (?), in a "
                              f"{dt(DIFF_REBATE)} pocket"),
            (FP_T + DIFF_REBATE + DIFF_GAP/2,
             f"air gap {dt(DIFF_GAP)} (?)  TUNE ON A TEST PRINT"),
            (z + LED_STRIP_T/2, f"SK6812 strip {dt(LED_STRIP_T)}")]
    for i, (xc, lab) in enumerate(rows):
        o.append(leader(xc*sc, 0, 0, -(20 + i*10), lab))
    o.append(leader((z + LED_STRIP_T)*sc*0.4, (hgt + CAV_WALL)*sc, -12, 22,
                    f"cavity wall {dt(CAV_WALL)}, follows the arc", "end"))
    o.append(dim_h(0, (z + LED_STRIP_T)*sc, (hgt + CAV_WALL)*sc + 34,
                   f"{dt(FM_DEPTH)} total"))
    return o


# ---------------------------------------------------------- sheet assembly
def build():
    o = [svg_header(SHEET_W, SHEET_H), sheet_frame(SHEET_W, SHEET_H, MARGIN)]

    o.append(g("FRONT-MODULE", [
        txt(0, -46, "FRONT MODULE", "blk"),
        txt(0, -34, "from BEHIND (mirrored) - one printed part", "lbl"),
        g("fm-body", fm_rear()),
        g("fm-dims", fm_dims()),
    ], 90.0, 122.0))

    o.append(g("SECTION-AA", [
        txt(0, -46, "SECTION A-A", "blk"),
        txt(0, -34, "on the centreline, front at left", "lbl"),
        g("sec-dome", sec_dome()),
        g("sec-front-module", sec_front_module()),
        g("sec-internals", sec_internals()),
        g("sec-dims", sec_dims()),
    ], 400.0, 122.0))

    o.append(g("BOTTOM-PLATE", [
        txt(0, -36, "BOTTOM PLATE", "blk"),
        txt(0, -26, "from above - the chassis: Flex + UPS + 6 fixings", "lbl"),
        g("bp-body", bp_plan()),
        g("bp-dims", bp_dims()),
    ], 600.0, 132.0))

    o.append(g("DOME-UNDERSIDE", [
        txt(0, -36, "DOME UNDERSIDE", "blk"),
        txt(0, -26, "looking up into the dome", "lbl"),
        g("du-body", dome_under()),
        g("du-dims", dome_under_dims()),
    ], 600.0, 268.0))

    o.append(g("BOSS-LEGEND", legend(
        [(i + 1, f"x {dt(bx)}, depth {dt(by)}   -   {dt(gap)} clear of {who}")
         for i, ((bx, by), gap, who) in enumerate(boss_clearances())],
        "FIXING LUGS  M3 into heat-set inserts"), 836.0, 300.0))

    o.append(g("DETAIL-B", [
        txt(0, -20, "DETAIL B   slot joint   5:1", "blk"),
        g("det-b", detail_slot()),
    ], 600.0, 432.0))

    o.append(g("DETAIL-C", [
        txt(0, -62, "DETAIL C   diffusion stack   5:1", "blk"),
        g("det-c", detail_diffuser()),
    ], 836.0, 432.0))

    # ----------------------------------------------------------- notes
    L, ln = [], [0.0]

    def nl(s, cls="note", step=4.7):
        L.append(txt(0, ln[0], s, cls))
        ln[0] += step

    nl("ASSEMBLY", "lbl", 6.6)
    nl("1   Front module slides UP into the dome's side grooves from below. "
       "Nothing retains it at this point.")
    nl(f"2   It seats against the lip; {dt(LIP_W - FP_CLR)} mm of its edge is "
       f"captured all round, with {dt(FP_CLR)} sliding clearance.")
    nl("3   Bottom plate goes on. Its top face is the module's datum - the "
       "module's bottom edge lands on it and can no longer drop.")
    nl(f"4   Six M{dt(SCREW_D)} screws pull the bottom plate up into the dome "
       f"bosses. No fastener touches the facade.", step=10)
    nl("NOTES", "lbl", 6.6)
    nl("a   ONE FRONT PIECE, YES - but the diffuser stays separate. You cannot "
       "print an even diffuser; the printed part is the frame and")
    nl("    the cavity, and the Glowforge-cut opal acrylic drops into a pocket "
       "from behind. Everything that must stay in register with")
    nl("    everything else - matrix aperture, grilles, mic ports, diffuser - "
       "is now on ONE part, so there are no stacked tolerances.")
    nl(f"b   The facade went {dt(3.0)} -> {dt(FP_T)} mm. Two "
       f"{dt(SPK_BODY_W)}x{dt(SPK_BODY_H)} sealed boxes on an unsupported 3 mm plate will flex "
       "and buzz; it is a baffle now, not a cover.")
    nl("    Ribs run from each baffle ring out to the perimeter for the same "
       "reason.")
    nl(f"c   AIR GAP IS A GUESS. {dt(DIFF_GAP)} mm is ~0.7x the "
       f"{dt(16.7)} mm LED pitch, the usual starting point for not seeing 48 "
       "dots through opal.")
    nl("    Test-print the crescent corner before committing - this is the one "
       "number most likely to need changing.")
    nl("d   FIXINGS ARE WALL LUGS, NOT FLOOR BOSSES. Each lug is a pad that "
       "projects inward off the dome wall with a blind heat-set hole; the")
    nl("    screw comes up through the bottom plate and grabs it. Lugs live at "
       "the perimeter where the plate needs support anyway, and they")
    nl("    cost no floor area - which matters, because the floor is fully "
       "spoken for. Clearances per lug are in the key beside the plan.")
    nl("e   NO LUG ON THE FRONT EDGE. The speaker bodies own both front corners "
       "and the matrix owns the middle, so there is nowhere to put one.")
    nl("    It does not need one: the plate's front edge is captured between "
       "the seating ledge and the front module's bottom edge.")
    nl(f"f   TPA2016 moved to the REAR WALL at y={dt(AMP_WALL_Y)}. There is no "
       "floor left for it, and the speaker leads are shortest from there.")
    nl("    Bridge-tied outputs: do NOT common the two speakers' negatives "
       "(HARDWARE.md).")
    nl(f"g   SPEAKERS HANG ON SIDE NUBS, not on a baffle bolt pattern. Each body "
       f"has one nub per side, centred on the {dt(SPK_BODY_H)} mm side, its "
       f"landing face {dt(SPK_NUB_Z)} mm behind the")
    nl(f"    speaker's front face. So the module carries a POST beside each "
       f"flank, standing {dt(SPK_NUB_Z)} proud of its back face, and an "
       f"M{n(SPK_NUB_SCREW)} runs front-to-back into it.")
    nl(f"    NUB PROJECTION IS A GUESS ({dt(SPK_NUB_PROJ)} mm) and it is a width "
       f"driver: the post needs {dt(SPK_SEAT_W)} mm beside each flank, so every "
       f"+1 mm of nub costs +4 mm of body width")
    nl(f"    and +2 mm of height. Measure it before you print. The seat ring is "
       f"sized from it ({dt(SPK_SEAT_W)} = nub {dt(SPK_NUB_PROJ)} + "
       f"{dt(SPK_POST_WALL)} wall), not chosen.")
    nl(f"h   THE TWO MATRICES ARE ONLY LOOSELY SOLDERED TOGETHER, so the frame "
       f"cannot treat them as one part. Each board is located by its OWN two "
       f"posts through its")
    nl(f"    own {chr(216)}{dt(MTX_HOLE_D)} diagonal holes, seats on two pads in "
       f"the clear margin above and below its LED field, and the pair is clamped "
       f"by SIX clips - two on")
    nl(f"    each long edge and one at each end. There is no tray and no pocket: "
       f"a pocket would locate the PAIR, and the pair is exactly the thing that "
       f"is not rigid.")
    nl(f"    The clock aperture is ONE OPEN {dt(CLK_W)} x {dt(CLK_H)} rectangle - "
       f"no per-pixel holes. Through a {dt(FP_T)} mm facade a per-pixel tunnel "
       f"would kill the viewing angle.")
    o.append(g("NOTES", L, 90.0, 372.0))

    o.append(title_block(
        936.0, 570.0, 238.0, 90.0,
        "SOUND MACHINE - INTERNALS", "front module / fixings / chassis",
        [("PROJECTION third angle", "ENVELOPE"),
         ("UNITS mm   SCALE 1:1 (details 5:1)",
          f"{dt(W)} W x {dt(D)} D x {dt(H)} H"),
         ("GENERATED BY 3d-print/gen_internals.py", "SHEET 2 of 3"),
         ("REFERENCE ONLY - not a released drawing", "REV A")], 2))

    o.append("</svg>")
    return "\n".join(o)


if __name__ == "__main__":
    base = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(base, "enclosure-internals.svg")
    open(out, "w").write(build())
    print(f"wrote {out}")
    print(f"front module   {dt(W - 2*REVEAL)} x {dt(H - REVEAL - BP_T)} x "
          f"{dt(FM_DEPTH)} deep")
    print(f"  facade {dt(FP_T)} | acrylic {dt(DIFF_T)} | air {dt(DIFF_GAP)} | "
          f"strip {dt(LED_STRIP_T)}")
    print(f"  clear of the UPS by "
          f"{dt(D - WALL - UPS_D - LIP_T - FM_DEPTH)} mm")
    print(f"joint          lip {dt(LIP_W)}x{dt(LIP_T)} | groove "
          f"{dt(FP_T + SLOT_CLR)} | rib {dt(RIB_W)}x{dt(RIB_T)} | "
          f"engagement {dt(LIP_W - FP_CLR)}")
    print("\nfixings (M%s into heat-set inserts)" % dt(SCREW_D))
    for i, ((bx, by), gap, who) in enumerate(boss_clearances()):
        flag = "FAIL" if gap < 0 else "ok  "
        print(f"  {flag} {i+1}  x {bx:6.1f}  depth {by:5.1f}   "
              f"{gap:6.2f} clear of {who}")
    bad = [c for c in boss_clearances() if c[1] < 0]
    print("\nALL CLEAR" if not bad else f"\n*** {len(bad)} BOSS COLLISION(S) ***")
