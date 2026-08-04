#!/usr/bin/env python3
"""SHEET 1 of 3 -- the shell. Third-angle: TOP / FRONT / RIGHT SIDE / REAR,
assembled and exploded.

Geometry and dimensions live in enclosure_geom.py; SVG helpers in drawlib.py.
Companion sheets: gen_internals.py (sheet 2), gen_wiring.py (sheet 3).

Render a preview with:
    rsvg-convert -b white -z 2 enclosure-drawing.svg -o enclosure-drawing.png
"""
import math
import os

from drawlib import *
from enclosure_geom import *


def qt_note(bw, bh):
    """Mounting-hole callout for an Adafruit STEMMA QT breakout.

    >>> THE PITCH, NOT THE INSET, AND NOT THROUGH dt(). Written as "4x M2.5
    >>> {dt(QT_HOLE_INSET)} in from each edge" it renders as "4x M2.5 2.5 in from
    >>> each edge" -- dt() gives one decimal, so the 2.54 inset comes out as a
    >>> second 2.5 and the callout has two different 2.5s in six words. The pitch
    >>> is also the thing you can actually put a caliper on to check a board
    >>> against the part; the inset is a derivation of it.
    """
    return (f"4x {chr(216)}{QT_HOLE_D} on {bw - 2*QT_HOLE_INSET:.2f} x "
            f"{bh - 2*QT_HOLE_INSET:.2f}")


# ============================================================== FRONT VIEW






def front_dome():
    """Outer skin, then the LIP inner edge -- that is the visible aperture.
    The front module sits BEHIND the lip, so its own outline is hidden."""
    o = [path(d_profile(0, R_BOT), "obj")]
    o.append(path(d_profile(WALL + LIP_W, max(R_BOT - WALL - LIP_W, 1)), "obj"))
    return o


def front_knob():
    return ([path(knob_profile(W/2, fy(H)), "obj"),
             line(W/2 - KNOB_BOSS_D/2, fy(H), W/2 + KNOB_BOSS_D/2, fy(H), "hid")]
            + knob_bore(W/2, fy(H)))



def front_touch():
    """The shoulder pads, seen head-on. Foreshortened: they wrap the crown."""
    o = []
    for tx in touch_x():
        o.append(rect(tx - TOUCH_PAD_W*0.36, fy(TOUCH_Y) - TOUCH_PAD_W*0.5,
                      TOUCH_PAD_W*0.72, TOUCH_PAD_W, "hid", 3))
    return o


def front_plate(cutouts=True):
    o = [path(d_profile(REVEAL, R_BOT - REVEAL), "hid")]
    if not cutouts:
        return o
    o.append(semi_e(W/2, fy(CRES_Y), CRES_R, CRES_RY))            # crescent diffuser
    o.append(rect(W/2-CLK_W/2, fy(CLK_Y+CLK_H/2), CLK_W, CLK_H, "obj", 2.0))
    for sx in (SPK_X, W-SPK_X):                                   # speaker grilles
        o.append(circ(sx, fy(SPK_Y), SPK_GRILLE))
    for mx in mic_x():                                            # 4x mic ports
        o.append(circ(mx, fy(MIC_Y), MIC_PORT_D))
    return o


def front_bottom_plate(dy=0.0):
    y = fy(0) - BP_T + dy
    return [rect((W-BP_W)/2, y, BP_W, BP_T, "obj", 1.5)]


def front_internals():
    o = []
    o.append(rect(W/2-TRAY_W/2, fy(CLK_Y+TRAY_H/2), TRAY_W, TRAY_H, "hid", 1))
    for sx in (SPK_X, W-SPK_X):
        o.append(rect(sx-SPK_BODY_W/2, fy(SPK_Y1), SPK_BODY_W, SPK_BODY_H, "hid", 2))
    o.append(rect(W/2-MIC_PCB_W/2, fy(MIC_Y+MIC_PCB_H/2), MIC_PCB_W, MIC_PCB_H, "hid"))
    # the UPS stands RIGHT of centre, not on the centreline
    o.append(rect(UPS_WALL_X-UPS_W/2, fy(BP_T+UPS_H), UPS_W, UPS_H, "hid"))
    return o


def front_dims():
    """Dimension columns: left  x=-11 / -19 / -28 / -38   right x=W+12 .. W+48
                          dims below  y=H+10 / H+22 / H+34
                          callouts    y=ROW1 / ROW2 / ROW3."""
    ROW1, ROW2, ROW3 = H + 46, H + 55, H + 64
    o = []
    o.append(cl_v(W/2, -8, H + 8))
    o.append(cl_h(-8, W + 8, fy(SPK_Y)))
    # envelope + plate outline
    o.append(dim_h(0, W, H + 34, ext=H))
    o.append(dim_h(REVEAL, W-REVEAL, H + 22, ext=H-REVEAL))
    o.append(dim_v(0, H, -28, ext=0))
    o.append(dim_v(REVEAL, H-REVEAL, -19, ext=REVEAL))
    # the concentric pair: shell arc R92 and crescent R80 share one centre
    o.append(f'<circle class="ctr" cx="{n(W/2)}" cy="{n(fy(ARCH_Y))}" r="1.6"/>')
    o.append(cl_h(W/2 - CRES_R - 14, W/2 + CRES_R + 14, fy(ARCH_Y)))
    o.append(leader(W/2 + ARCH_R*0.707, fy(ARCH_Y + ARCH_RY*0.707), 30, -44,
                    f"shell arch {dt(ARCH_R)} x {dt(ARCH_RY)} - FLATTENED "
                    f"(k={CROWN_K}), not a semicircle"))
    o.append(leader(W/2 + CRES_R*0.5, fy(ARCH_Y + CRES_RY*0.866), 54, -30,
                    f"diffuser {dt(CRES_R)} x {dt(CRES_RY)}, {dt(CRES_RIM)} rim"))
    # LED_RY, not LED_R, for the vertical offset -- the field is an ellipse, and
    # using the horizontal semi-axis put this leader 26 mm above the arc it
    # points at. There is also no fade band any more (CRES_FADE = 0): the field
    # IS the diffuser, and what matters instead is the clearance to its edge.
    o.append(leader(W/2 - LED_R*0.5, fy(ARCH_Y + LED_RY*0.866), -30, -44,
                    f"{dt(LED_R)} x {dt(LED_RY)} LED field = the diffuser, no "
                    f"fade band - {CRES_PX} px, tightest body-to-edge "
                    f"{dt(crescent_clearance())}", "end"))
    # (no 2xR dimension across the baseline -- it would run straight through the
    #  bottom LED row, and R + concentric + centre height already fix the arc)
    o.append(dim_v(fy(ARCH_Y), fy(0), W + 12, dt(ARCH_Y), ext=W/2+CRES_R))
    o.append(dim_v(fy(CRES_Y + CRES_RY), fy(0), W + 24, dt(CRES_Y+CRES_RY), ext=W/2))
    # clock aperture + matrix pair
    o.append(dim_h(W/2-CLK_W/2, W/2+CLK_W/2, H + 10, dt(CLK_W), ext=H))
    o.append(leader(W/2+CLK_W/2, fy(CLK_Y) - CLK_H/2, 78, -56,
                    f"clock aperture {dt(CLK_W)} x {dt(CLK_H)}"))
    o.append(leader(W/2+TRAY_W/2, fy(CLK_Y)+TRAY_H/2, 76, 20,
                    f"2x matrix {dt(MTX_BOARD_W)} x {dt(TRAY_H)} butted = "
                    f"{dt(TRAY_W)} - posts + clips, no tray"))
    o.append(dim_v(fy(CLK_Y), fy(0), -11, dt(CLK_Y), ext=W/2-CLK_W/2))
    # mic array band, above the clock
    o.append(cl_h(W/2 - MIC_PCB_W/2 - 8, W/2 + MIC_PCB_W/2 + 8, fy(MIC_Y)))
    o.append(dim_h(mic_x()[0], mic_x()[1], fy(MIC_Y) - 8, dt(MIC_PITCH), ext=fy(MIC_Y)))
    o.append(leader(mic_x()[0], fy(MIC_Y), -6, ROW2 - fy(MIC_Y),
                    f"{MIC_N}x {chr(216)}{dt(MIC_PORT_D)} mic port @ {dt(MIC_PITCH)} "
                    "- ReSpeaker Flex linear array (?)"))
    o.append(dim_v(fy(MIC_Y1), fy(MIC_Y0), W + 36, f"{dt(MIC_PCB_H)} mic band",
                   ext=W/2 + MIC_PCB_W/2))
    o.append(dim_v_out(fy(SPK_Y1), fy(MIC_Y0), W + 48, dt(GAP_MIC),
                       ext=W/2 + MIC_PCB_W/2))
    # speakers
    o.append(dim_h(0, SPK_X, H + 10, dt(SPK_X), ext=H))
    _gy = fy(SPK_Y) + SPK_GRILLE*0.354
    o.append(leader(SPK_X - SPK_GRILLE*0.354, _gy, -6, ROW3 - _gy,
                    f"2x grille {chr(216)}{dt(SPK_GRILLE)}  (driver {chr(216)}{dt(SPK_BODY_W)} ?)"))
    o.append(dim_h_out(SPK_X + SPK_BODY_W/2, W/2 - TRAY_W/2, fy(SPK_Y1) - 6,
                       f"{dt(CLR_SPK_TRAY)} clr", ext=fy(SPK_Y)))
    # knob
    o.append(cl_v(W/2, fy(H) - KNOB_H - 8, fy(H) + 6))
    _a, _b, _yc, _w0 = knob_ellipse()
    o.append(leader(W/2 + KNOB_D/2, fy(H) - _yc, 40, -18,
                    f"5  knob {chr(216)}{dt(KNOB_D)} x {dt(KNOB_H)} pebble, "
                    f"{chr(216)}{dt(KNOB_BASE_D)} base flat"))
    o.append(dim_v(fy(H) - KNOB_H, fy(H), W/2 - KNOB_D/2 - 10, dt(KNOB_H),
                   ext=W/2 - KNOB_D/2))
    o.append(dim_v(fy(H) - KNOB_H, fy(0), -38, f"{dt(H+KNOB_H)} over knob", ext=W/2-KNOB_D/2))
    # corner radii + interface
    o.append(leader(W - R_BOT*0.293, H - R_BOT*0.293, 24, 12, f"R{dt(R_BOT)}"))
    o.append(leader(W - WALL - LIP_W, fy(ARCH_Y*0.5), 32, -40,
                    f"lip {dt(LIP_W)} wide, facade {dt(LIP_T)} behind the rim"))
    o.append(leader(W/2 - BP_W/2 + 10, fy(BP_T/2), 6, ROW1 - fy(BP_T/2),
                    f"3  bottom plate {dt(BP_T)} thk"))
    return o


# ================================================================ TOP VIEW
def top_dome():
    o = [path(rrect(0, 0, W, D, R_PLAN), "obj")]
    o.append(path(rrect(WALL, WALL, IN_W, IN_D, max(R_PLAN-WALL, 1)), "hid"))
    o.append(circ(W/2, D-ENC_Y, ENC_SHAFT_D, "hid"))
    o.append(circ(W/2, D-ENC_Y, KNOB_BOSS_D, "phan"))
    o.append(circ(TOF_X, D-TOF_Y, TOF_HOLE_D))
    # >>> THE CROWN MOUNTING BOSSES, seen from above, AND FROM crown_boards() --
    # >>> not from a pitch and an axis name. They were not on any sheet at all
    # >>> once, which is why an encoder boss and a ToF boss could overlap by 2.9 mm
    # >>> unnoticed; drawn from a pitch they then showed FOUR bosses as TWO, and
    # >>> the pair that was 0.59 mm from an encoder boss was the pair not drawn.
    # >>> Drawing the shared list means a boss cannot exist and be invisible here.
    for _nm, _cx, _cz, _bw, _bd, _offs, _st in crown_boards():
        for _dx, _dz in _offs:
            o.append(circ(_cx + _dx, D - (_cz + _dz), BOSS_D, "hid"))
        o.append(rect(_cx - _bw/2, D - _cz - _bd/2, _bw, _bd, "phan", 1))
    for tx in touch_x():                       # copper pads, inside face
        o.append(rect(tx - TOUCH_PAD_W/2, D - TOUCH_DEPTH - TOUCH_PAD_L/2,
                      TOUCH_PAD_W, TOUCH_PAD_L, "hid", 3))
    for gx in (WALL, W - WALL - FP_T - SLOT_CLR):   # front-module side groove
        o.append(rect(gx - WALL, D - LIP_T - FP_T - SLOT_CLR,
                      WALL + 0.01, SLOT_W, "obj"))
    # crown ridge line: the top is a cylinder, highest along x = W/2
    o.append(cl_v(W/2, 2, D - 2))
    return o


def top_knob():
    return [circ(W/2, D-ENC_Y, KNOB_D),
            circ(W/2, D-ENC_Y, KNOB_BORE_D, "hid")]


def top_plate():
    return [rect((W-FP_W)/2, D - FP_T, FP_W, FP_T, "obj", 1.0)]


def top_bottom_plate():
    return [path(rrect((W-BP_W)/2, (D-BP_D)/2, BP_W, BP_D, max(R_PLAN-WALL, 1)), "hid")]


def top_internals():
    o = [rect(W/2-TRAY_W/2, D - FP_T - TRAY_D, TRAY_W, TRAY_D, "hid")]
    for sx in (SPK_X, W-SPK_X):
        o.append(rect(sx-SPK_BODY_W/2, FP_T, SPK_BODY_W, SPK_BODY_D, "hid"))
    o.append(rect(UPS_WALL_X-UPS_W/2, D - WALL - UPS_D, UPS_W, UPS_D, "hid"))
    o.append(rect(W/2-ENC_PCB/2, D-ENC_Y-ENC_PCB/2, ENC_PCB, ENC_PCB, "hid"))
    o.append(rect(TOF_X-TOF_PCB_W/2, D-TOF_Y-TOF_PCB_D/2, TOF_PCB_W, TOF_PCB_D, "hid"))
    return o


def top_dims():
    o = [cl_v(W/2, -10, D + 10), cl_h(-10, W + 10, D - ENC_Y)]
    o.append(dim_h(0, W, -30, ext=0))
    o.append(dim_v(0, D, -14, ext=0))
    o.append(leader(W/2 + KNOB_D/2, D-ENC_Y, 34, -52,
                    f"5  knob {chr(216)}{dt(KNOB_D)}, bore {chr(216)}{dt(KNOB_BORE_D)} "
                    f"with {dt(KNOB_BORE_F)} D-flat (?)"))
    o.append(leader(W/2 - KNOB_BOSS_D/2*0.71, D-ENC_Y + KNOB_BOSS_D/2*0.71, 20, 26,
                    f"{chr(216)}{dt(KNOB_BOSS_D)} flat boss on the crown, "
                    f"{chr(216)}{dt(ENC_SHAFT_D)} shaft bore"))
    o.append(dim_v(D-ENC_Y, D, W + 12, dt(ENC_Y), ext=W-14))
    o.append(dim_v_out(D - FP_T, D, W + 26, dt(FP_T), ext=W-6))
    o.append(leader(touch_x()[1], D - TOUCH_DEPTH - TOUCH_PAD_L/2, 20, -40,
                    f"2x copper touch pad {dt(TOUCH_PAD_L)} x {dt(TOUCH_PAD_W)} on the inside face - one per shoulder"))
    o.append(leader(W - WALL, D - LIP_T - FP_T/2, 26, -44,
                    f"inset side groove {dt(SLOT_W)} wide = module {dt(FP_T)} + 2x cloth "
                    f"{dt(CLOTH_T)} + {dt(SLOT_CLR)} clr"))
    # ToF, alongside the knob
    o.append(cl_v(TOF_X, D-TOF_Y-TOF_PCB_D/2 - 5, D-TOF_Y+TOF_PCB_D/2 + 5))
    o.append(leader(TOF_X, D-TOF_Y-TOF_HOLE_D/2, 56, -36,
                    f"{chr(216)}{dt(TOF_HOLE_D)} ToF pinhole (VL53L0X, planned)"))
    o.append(leader(TOF_X+TOF_PCB_W/2, D-TOF_Y+TOF_PCB_D/2, 26, 32,
                    f"board {dt(TOF_PCB_W)} x {dt(TOF_PCB_D)} LONGWISE front-to-back, "
                    f"{qt_note(TOF_PCB_W, TOF_PCB_D)}"))
    o.append(leader(W/2 - ENC_PCB/2, D - ENC_Y - ENC_PCB/2, -32, -26,
                    f"encoder {dt(ENC_PCB)} sq, {qt_note(ENC_PCB, ENC_PCB)}",
                    "end"))
    # >>> THE BOARD GAP IS DIMENSIONED AS A RESULT, not called up as a fit. It is
    # >>> whatever leaves BOSS_GAP_MIN between the two boards' nearest bosses.
    o.append(leader(W/2 + ENC_PCB/2 + TOF_BOARD_GAP/2, D - ENC_Y + ENC_PCB/2,
                    -8, 46,
                    f"{dt(TOF_BOARD_GAP)} board gap = whatever leaves "
                    f"{dt(BOSS_GAP_MIN)} between bosses"))
    o.append(dim_h(W/2, TOF_X, -20, dt(TOF_X - W/2), ext=D-ENC_Y))
    o.append(leader(R_PLAN*0.293, R_PLAN*0.293, -14, -10, f"R{dt(R_PLAN)}", "end"))
    o.append(leader(WALL, D*0.28, -30, -18, f"wall {dt(WALL)}", "end"))
    o.append(leader(UPS_WALL_X-UPS_W/2, D - WALL, -10, 52,
                    f"UPS 3S pack {dt(UPS_W)} x {dt(UPS_D)}, cells upright (?)", "end"))
    return o


# =============================================================== SIDE VIEW
# right-side view, third angle: object FRONT is on the LEFT, x -> rearward.
def side_dome():
    o = [path(rrect(0, 0, D, H, R_SIDE, R_SIDE, R_SIDE_B, R_SIDE_B), "obj")]
    o.append(line(FP_T, REVEAL + LIP, FP_T, H - REVEAL - LIP, "hid"))
    o.append(line(D-ENC_Y-KNOB_BOSS_D/2, fy(H), D-ENC_Y+KNOB_BOSS_D/2, fy(H), "hid"))
    return o + side_vents()


def side_knob():
    return [path(knob_profile(D - ENC_Y, fy(H)), "obj")] + knob_bore(D - ENC_Y, fy(H))


def side_vents():
    """Rear-wall features are centred in width, so in SIDE view they are behind
    the wall: draw them as hidden extents at the rear edge. The REAR view is the
    true one for anything on this face."""
    o = []
    for yc, hgt in ((LP_Y, LP_D), (BARREL_Y, BARREL_D)):
        o.append(rect(D - WALL, fy(yc + hgt/2), WALL, hgt, "hid"))
    for i in range(VENT_N):
        o.append(rect(D - WALL, fy(VENT_Y + i*VENT_P) - VENT_HH/2, WALL, VENT_HH, "hid"))
    return o


# =============================================================== REAR VIEW
# The body is an extrusion, so the rear face is the SAME "D" as the front --
# a true flat face, no plate, no reveal. Everything on it is centred in width.
# Mirrored left-to-right relative to FRONT, but every feature here is on the
# centreline, so nothing actually swaps sides.

def rear_dome():
    o = [path(d_profile(0, R_BOT), "obj")]
    o.append(path(d_profile(WALL, max(R_BOT - WALL, 1)), "hid"))      # inner wall
    o.append(circ(W/2, fy(LP_Y), LP_D))                               # lux
    o.append(circ(W/2, fy(BARREL_Y), BARREL_D))                       # barrel jack
    # the UPS 5V switch -- a ROUND panel button, low and left
    o.append(circ(SW_WALL_X, fy(SW_WALL_Y), SW_D))
    o.append(circ(SW_WALL_X, fy(SW_WALL_Y), SW_NUT_D, "phan"))
    # >>> EACH SLOT DRAWN AT ITS OWN LENGTH, from vent_slots(). They taper with the
    # >>> arch now, so a shared width would draw a rectangle the part does not have.
    for vx, vy, hl, hh in vent_slots():
        o.append(rect(vx - hl, fy(vy) - hh, 2*hl, 2*hh, "obj", hh))
    return o


def rear_internals():
    """What is mounted ON the rear wall, seen through it."""
    # >>> THE UPS AND THE FLEX ARE NOT CENTRED, AND HAVE NOT BEEN FOR A WHILE.
    # >>> This view drew both on W/2 long after they went SIDE BY SIDE -- UPS
    # >>> right at x=150, Flex left at x=60 -- so the sheet showed them stacked
    # >>> on top of each other in the middle of a wall they no longer share that
    # >>> way. Draw them where rear_wall_items() says they are.
    # >>> AND EVERY BOARD IS DRAWN FROM rear_wall_boards(), NOT BY HAND. This view
    # >>> listed the UPS and the Flex and nothing else, so the LUX and the RTC --
    # >>> both real, both with four bosses each -- appeared on no sheet at all. The
    # >>> RTC's standoffs were unidentifiable when they turned up in a model,
    # >>> because there was nowhere to look them up. Anything added to
    # >>> rear_wall_boards() from now on draws itself.
    o = [rect(AMP_X - AMP_W/2, fy(AMP_H + AMP_D/2), AMP_W, AMP_D, "phan")]
    for nm, cx, cy, bw, bh, offs in rear_wall_boards():
        o.append(rect(cx - bw/2, fy(cy + bh/2), bw, bh, "hid"))
        for dx, dy in (offs or []):
            o.append(circ(cx + dx, fy(cy + dy), BOSS_PILOT_D, "obj"))
            o.append(circ(cx + dx, fy(cy + dy), BOSS_D, "phan"))
    # the Flex additionally needs the 110 envelope its connectors want
    o.append(rect(FLEX_WALL_X - FLEX_W/2, fy(FLEX_WALL_Y + FLEX_H),
                  FLEX_W, FLEX_H, "phan"))
    for hx, hy in flex_holes():                       # 4x M3, 45 x 63 pitch
        o.append(circ(hx, fy(hy), FLEX_HOLE_D, "obj"))
        o.append(circ(hx, fy(hy), FLEX_BOSS_D, "phan"))
    return o


def rear_dims():
    o = [cl_v(W/2, -12, H + 12)]
    o.append(dim_h(0, W, H + 22, ext=H))
    o.append(dim_v(0, H, -20, ext=0))
    # heights, all off the same centreline
    o.append(dim_v(fy(BARREL_Y), fy(0), W + 14, dt(BARREL_Y), ext=W/2 + BARREL_D/2))
    o.append(dim_v(fy(LP_Y), fy(0), W + 26, dt(LP_Y), ext=W/2 + LP_D/2))
    # >>> ONE VENT STACK NOW, CENTRED. This sheet indexed _vx in five
    # >>> places, from when there were two stacks either side of the UPS.
    _vx = vent_x()[-1]
    _vhl = [hl for _v, _y, hl, _h in vent_slots()]
    o.append(dim_v(fy(vent_y(0)), fy(0), W + 38, dt(VENT_Y),
                   ext=_vx + _vhl[0]))
    o.append(leader(W/2 + BARREL_D/2, fy(BARREL_Y), 46, 26,
                    f"{chr(216)}{dt(BARREL_D)} DC barrel jack - UPS 3S charge in (?)"))
    o.append(leader(W/2 + LP_D/2, fy(LP_Y), 62, 62,
                    f"{chr(216)}{dt(LP_D)} light pipe - BH1750 lux"))
    o.append(leader(_vx + _vhl[-1], fy(vent_y(VENT_N - 1)), 30, -26,
                    f"{VENT_N} OBROUND LOUVRE "
                    f"{'/'.join(dt(2*h) for h in _vhl)} x {dt(2*VENT_HH)} @ "
                    f"{dt(VENT_P)} - ends follow the arch, {dt(VENT_INSET)} in "
                    f"from its inner face; rises {dt(VENT_RISE)} inward, so a "
                    f"level line of sight is blocked"))
    o.append(leader(RTC_WALL_X + RTC_PCB_W/2, fy(RTC_WALL_Y), 34, -34,
                    # >>> THE COUNT COMES FROM THE HOLE LIST. This read a hardcoded
                    # >>> "4x" while the dome built the correct TWO bosses, so the
                    # >>> sheet and the solid disagreed and only the sheet was
                    # >>> wrong -- the one a human works from. And Ø3.0 is the
                    # >>> board's CLEARANCE hole; the screw into the boss is M2.5.
                    f"DS3231 RTC {dt(RTC_PCB_W)} x {dt(RTC_PCB_H)}, "
                    f"{len(RTC_HOLES)}x {chr(216)}{dt(RTC_HOLE_D)} @ "
                    f"{dt(RTC_HOLE_P)} (TOP pair only) for M{BOSS_SCREW} "
                    f"- I2C 0x68. ON THIS WALL, not the bottom plate"))
    o.append(leader(LUX_WALL_X + LUX_PCB_W/2, fy(LUX_WALL_Y), 44, 18,
                    f"BH1750 lux {dt(LUX_PCB_W)} x {dt(LUX_PCB_H)}, "
                    f"{qt_note(LUX_PCB_W, LUX_PCB_H)} - looks through the pipe"))
    o.append(leader(SW_WALL_X - SW_NUT_D/2, fy(SW_WALL_Y), -26, 34,
                    f"{chr(216)}{dt(SW_D)} UPS 5V switch - ROUND panel button, "
                    f"on a {chr(216)}{dt(SW_NUT_D + 2*SW_RIB)} land", "end"))
    o.append(dim_h(_vx - _vhl[0], _vx + _vhl[0],
                   fy(vent_y(0)) + 10, dt(2*_vhl[0]), ext=fy(vent_y(0))))
    o.append(dim_h(_vx - _vhl[-1], _vx + _vhl[-1],
                   fy(vent_y(VENT_N-1)) - 9, dt(2*_vhl[-1])))
    o.append(leader(UPS_WALL_X - UPS_W/2, fy(BP_T + UPS_H*0.30), -16, 18,
                    f"UPS 3S {dt(UPS_W)} x {dt(UPS_H)}, standing (jack lands here)",
                    "end"))
    o.append(leader(FLEX_WALL_X + FLEX_PCB_W/2, fy(FLEX_WALL_Y + FLEX_PCB_H), 40, -30,
                    f"ReSpeaker Flex board {dt(FLEX_PCB_W)} x {dt(FLEX_PCB_H)} x "
                    f"{dt(FLEX_D)} deep - VERTICAL on this wall, above the UPS"))
    o.append(leader(FLEX_WALL_X + FLEX_W/2, fy(FLEX_WALL_Y + FLEX_H*0.62), 34, -46,
                    f"{dt(FLEX_W)} envelope - the 3.5 mm jack and the mic ribbon "
                    "overhang the short edges"))
    o.append(dim_h(FLEX_WALL_X - FLEX_HOLE_PX/2, FLEX_WALL_X + FLEX_HOLE_PX/2,
                   fy(FLEX_WALL_Y + FLEX_H/2), dt(FLEX_HOLE_PX)))
    o.append(leader(FLEX_WALL_X - FLEX_HOLE_PX/2, fy(FLEX_WALL_Y + FLEX_H/2 + FLEX_HOLE_PY/2),
                    -30, -18,
                    f"4x M{n(FLEX_HOLE_D)} boss @ {dt(FLEX_HOLE_PX)} x "
                    f"{dt(FLEX_HOLE_PY)}, {dt(FLEX_STANDOFF)} standoff", "end"))
    o.append(leader(AMP_WALL_X - AMP_W/2, fy(AMP_WALL_Y), -22, 34,
                    f"TPA2016 {dt(AMP_W)} x {dt(AMP_D)}, FLUSH"))
    o.append(txt(W/2, H + 38, "lux CENTRED on the width; "
                 "UPS right + Flex left, side by side; jack and switch LOW",
                 "note", "middle"))
    return o


def side_plate(dx=0.0):
    return [path(rrect(dx, REVEAL, FP_T, FP_H, 1.0), "obj")]


def side_bottom_plate(dy=0.0):
    return [rect((D-BP_D)/2, fy(0) - BP_T + dy, BP_D, BP_T, "obj", 1.0)]


def side_tray(dx=0.0):
    return [rect(FP_T + dx, fy(CLK_Y + TRAY_H/2), TRAY_D, TRAY_H, "obj")]


def side_internals():
    o = [rect(FP_T, fy(CLK_Y + TRAY_H/2), TRAY_D, TRAY_H, "hid")]
    o.append(rect(FP_T, fy(SPK_Y + SPK_BODY_W/2), SPK_BODY_D, SPK_BODY_W, "hid"))
    o.append(rect(D - WALL - UPS_D, fy(BP_T + UPS_H), UPS_D, UPS_H, "hid"))
    # crescent LED panel rides the facade plane
    o.append(line(FP_T, fy(CRES_Y), FP_T, fy(CRES_Y + CRES_RY), "hid"))
    # mic strip, right behind the plate in the band above the clock
    o.append(rect(FP_T, fy(MIC_Y + MIC_PCB_H/2), 4.0, MIC_PCB_H, "hid"))
    # encoder + ToF boards share the depth band under the crown
    o.append(rect(D - ENC_Y - ENC_PCB/2, fy(H) + WALL + 6, ENC_PCB, 2.0, "hid"))
    return o


def side_dims():
    o = [cl_h(-10, D + 10, fy(SPK_Y))]
    o.append(dim_h(0, D, -30, ext=0))
    o.append(dim_v(0, H, D + 40, ext=D))
    o.append(dim_h_out(0, FP_T, H + 12, dt(FP_T), ext=H, side=-1))
    o.append(dim_v_out(fy(BP_T), fy(0), -14, dt(BP_T), ext=(D-BP_D)/2))
    o.append(leader(D-R_SIDE*0.293, R_SIDE*0.293, 24, -8, f"R{dt(R_SIDE)} edge break"))
    o.append(leader(D - TOUCH_DEPTH, fy(TOUCH_Y + TOUCH_PAD_W/2), -22, -20,
                    "copper touch pad (far + near shoulder)", "end"))
    o.append(leader(LIP_T + FP_T, fy(ARCH_Y*0.75), -20, 30,
                    f"side groove, {dt(ARCH_Y - REVEAL)} of straight travel", "end"))
    o.append(leader(D, fy(vent_y(VENT_N - 1)), 24, -10,
                    "rear wall: vents, lux, barrel jack"))
    o.append(leader(D, fy(LP_Y), 24, 6, "- see REAR view"))
    o.append(leader(FP_T + TRAY_D, fy(CLK_Y) + TRAY_H/2, -14, 52,
                    f"4  matrix stack, depth {dt(TRAY_D)}", "end"))
    o.append(dim_h(FP_T, FP_T + TRAY_D, fy(CLK_Y) + TRAY_H/2 + 7, dt(TRAY_D),
                   ext=fy(CLK_Y)+TRAY_H/2))
    o.append(dim_v(fy(BP_T + UPS_H), fy(BP_T), D + 22, dt(UPS_H), ext=D - WALL))
    # knob
    o.append(cl_v(D - ENC_Y, fy(H) - KNOB_H - 6, fy(H) + 6))
    o.append(dim_h(0, D - ENC_Y, fy(H) - KNOB_H - 5, dt(D - ENC_Y), ext=fy(H)))
    o.append(leader(D - ENC_Y + KNOB_D/2, fy(H) - KNOB_H*0.55, 30, -6, "5  knob"))
    o.append(txt(D/2, H + 30, "flat top - the crown is a cylinder,", "note", "middle"))
    o.append(txt(D/2, H + 35, "so it only curves in FRONT", "note", "middle"))
    return o


# ============================================================ sheet assembly
def build():
    o = []
    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" version="1.1" '
             f'width="{n(SHEET_W)}mm" height="{n(SHEET_H)}mm" '
             f'viewBox="0 0 {n(SHEET_W)} {n(SHEET_H)}">')
    o.append(f"""<defs>
<marker id="arw" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="3.4"
        markerHeight="3.4" orient="auto-start-reverse" markerUnits="userSpaceOnUse">
  <path d="M0,1.4 L10,5 L0,8.6 z" fill="#1b1b1b"/>
</marker>
<style>
  text {{ font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; fill:#1b1b1b; }}
  .obj  {{ fill:none; stroke:#1b1b1b; stroke-width:0.55; }}
  .hid  {{ fill:none; stroke:#7a7a7a; stroke-width:0.35; stroke-dasharray:2.6 1.6; }}
  .phan {{ fill:none; stroke:#9a9a9a; stroke-width:0.32; stroke-dasharray:7 1.6 1.2 1.6; }}
  .led  {{ fill:none; stroke:#9a9a9a; stroke-width:0.3; }}
  .ctr  {{ fill:none; stroke:#b03a3a; stroke-width:0.3;  stroke-dasharray:9 1.8 1.6 1.8; }}
  .dim  {{ fill:none; stroke:#1b1b1b; stroke-width:0.3; }}
  .ext  {{ fill:none; stroke:#1b1b1b; stroke-width:0.25; }}
  .traj {{ fill:none; stroke:#4a6fa5; stroke-width:0.35; stroke-dasharray:5 2; }}
  .bal  {{ fill:#ffffff; stroke:#1b1b1b; stroke-width:0.45; }}
  .dtx  {{ font-size:3.1px; }}
  .balt {{ font-size:4.4px; font-weight:600; }}
  .note {{ font-size:3.4px; }}
  .lbl  {{ font-size:4.6px; font-weight:600; letter-spacing:0.6px; }}
  .blk  {{ font-size:6.4px; font-weight:700; letter-spacing:1.4px; fill:#4a6fa5; }}
  .ttl  {{ font-size:9px;   font-weight:700; letter-spacing:1px; }}
  .sub  {{ font-size:4.4px; fill:#555; }}
  .frame{{ fill:none; stroke:#1b1b1b; stroke-width:0.5; }}
  .tb   {{ fill:none; stroke:#1b1b1b; stroke-width:0.35; }}
</style>
</defs>
<rect x="0" y="0" width="{n(SHEET_W)}" height="{n(SHEET_H)}" fill="#ffffff"/>""")

    o.append(f'<rect class="frame" x="{n(MARGIN)}" y="{n(MARGIN)}" '
             f'width="{n(SHEET_W-2*MARGIN)}" height="{n(SHEET_H-2*MARGIN)}"/>')

    # ---------------------------------------------------------- ASSEMBLED
    at_x, at_y = 70.0, 90.0                    # top view
    af_x, af_y = 70.0, 250.0           # front view
    as_x, as_y = 430.0, af_y                   # side view
    ar_x, ar_y = 620.0, 555.0                  # rear view (out of projection)

    asm = []
    asm.append(txt(at_x - 6, at_y - 46, "ASSEMBLED", "blk"))
    asm.append(g("ASM-TOP", [
        txt(0, -38, "TOP", "lbl"),
        g("asm-top-dome", top_dome()),
        g("asm-top-knob", top_knob()),
        g("asm-top-front-plate", top_plate()),
        g("asm-top-bottom-plate", top_bottom_plate()),
        g("asm-top-internals", top_internals()),
        g("asm-top-dims", top_dims()),
    ], at_x, at_y))
    asm.append(g("ASM-FRONT", [
        txt(0, -52, "FRONT", "lbl"),
        g("asm-front-dome", front_dome()),
        g("asm-front-knob", front_knob()),
        g("asm-front-front-plate", front_plate()),
        g("asm-front-crescent-leds", crescent_leds()),
        g("asm-front-bottom-plate", front_bottom_plate()),
        g("asm-front-internals", front_internals()),
        g("asm-front-dims", front_dims()),
    ], af_x, af_y))
    asm.append(g("ASM-REAR", [
        txt(0, -30, "REAR", "lbl"),
        txt(0, -24, "(mirrored from FRONT; placed out of projection to fit the sheet)",
            "note"),
        g("asm-rear-dome", rear_dome()),
        g("asm-rear-bottom-plate", front_bottom_plate()),
        g("asm-rear-internals", rear_internals()),
        g("asm-rear-dims", rear_dims()),
    ], ar_x, ar_y))
    asm.append(g("ASM-SIDE", [
        txt(0, -52, "RIGHT SIDE", "lbl"),
        txt(0, -46, "(front at left)", "note"),
        g("asm-side-dome", side_dome()),
        g("asm-side-knob", side_knob()),
        g("asm-side-front-plate", side_plate()),
        g("asm-side-bottom-plate", side_bottom_plate()),
        g("asm-side-internals", side_internals()),
        g("asm-side-dims", side_dims()),
    ], as_x, as_y))
    o.append(g("ASSEMBLED", asm))

    # ----------------------------------------------------------- EXPLODED
    et_x, et_y = 660.0, 90.0
    ef_x, ef_y = 660.0, 270.0
    es_x, es_y = ef_x + W + 30 + EX_PLATE, ef_y

    exp = []
    exp.append(txt(et_x - 6, et_y - 46, "EXPLODED", "blk"))

    # --- exploded TOP: front plate + tray pulled forward (down the page)
    etop = [txt(0, -38, "TOP", "lbl")]
    etop.append(g("exp-top-dome", top_dome()))
    etop.append(g("exp-top-knob", [circ(W/2, D-ENC_Y, KNOB_D, "obj")]))
    etop.append(g("exp-top-matrix-tray",
                  [rect(W/2-TRAY_W/2, D - FP_T - TRAY_D + EX_TRAY + 14, TRAY_W, TRAY_D, "obj")]))
    etop.append(g("exp-top-front-plate", [rect((W-FP_W)/2, D - FP_T + EX_PLATE, FP_W, FP_T, "obj", 1.0)]))
    etop.append(g("exp-top-bottom-plate", top_bottom_plate()))
    etop.append(g("exp-top-trajectory", [
        traj(W/2 - FP_W/2 + 8, D - FP_T, W/2 - FP_W/2 + 8, D - FP_T + EX_PLATE),
        traj(W/2 + FP_W/2 - 8, D - FP_T, W/2 + FP_W/2 - 8, D - FP_T + EX_PLATE),
        traj(W/2, D - FP_T - TRAY_D, W/2, D - FP_T - TRAY_D + EX_TRAY + 14),
        dim_v(D - FP_T, D - FP_T + EX_PLATE, W + 18, f"explode {dt(EX_PLATE)}"),
    ]))
    etop.append(g("exp-top-balloons", [
        balloon(W*0.78, WALL + 3, 1, W + 26, -14),
        balloon(W/2 + KNOB_D/2*0.71, D - ENC_Y - KNOB_D/2*0.71, 5, W + 26, -1),
        balloon(W*0.80, D - FP_T + EX_PLATE + FP_T/2, 2, W + 26, D + EX_PLATE + 6),
        balloon(W/2 - TRAY_W/2 + 6, D - FP_T - TRAY_D + EX_TRAY + 14 + TRAY_D/2, 4, -24, D + 14),
    ]))
    exp.append(g("EXP-TOP", etop, et_x, et_y))

    # --- exploded FRONT: bottom plate drops; plate/tray shown in place (Z is normal)
    efr = [txt(0, -62, "FRONT", "lbl")]
    efr.append(g("exp-front-dome", front_dome()))
    efr.append(g("exp-front-knob", [path(knob_profile(W/2, fy(H) - EX_KNOB), "obj")]))
    efr.append(g("exp-front-front-plate", front_plate()))
    efr.append(g("exp-front-bottom-plate", front_bottom_plate(EX_BOTTOM)))
    efr.append(g("exp-front-trajectory", [
        traj((W-BP_W)/2 + 10, fy(0), (W-BP_W)/2 + 10, fy(0) + EX_BOTTOM),
        traj(W - (W-BP_W)/2 - 10, fy(0), W - (W-BP_W)/2 - 10, fy(0) + EX_BOTTOM),
        traj(W/2, fy(H) - EX_KNOB, W/2, fy(H) + 4),
        dim_v(fy(0), fy(0) + EX_BOTTOM, -18, f"drop {dt(EX_BOTTOM)}"),
        txt(W/2, fy(0) + EX_BOTTOM + 16, "front plate + tray separate along Z - see TOP / SIDE",
            "note", "middle"),
    ]))
    efr.append(g("exp-front-balloons", [
        balloon(W/2 - KNOB_D/2, fy(H) - EX_KNOB - KNOB_H*0.5, 5, -26, fy(H) - EX_KNOB - 4),
        balloon(REVEAL/2, fy(ARCH_Y*0.75), 1, -26, fy(ARCH_Y*0.95)),
        balloon(W/2 - CRES_R*0.86, fy(CRES_Y + 14), 2, -26, fy(CRES_Y + 30)),
        balloon(W/2 - BP_W/2 + 18, fy(0) + EX_BOTTOM + BP_T/2, 3, -26, fy(0) + EX_BOTTOM + 4),
    ]))
    exp.append(g("EXP-FRONT", efr, ef_x, ef_y))

    # --- exploded SIDE: plate + tray forward (left), bottom plate down
    esd = [txt(0, -62, "RIGHT SIDE", "lbl")]
    esd.append(g("exp-side-dome", side_dome()))
    esd.append(g("exp-side-knob", [path(knob_profile(D - ENC_Y, fy(H) - EX_KNOB), "obj")]))
    esd.append(g("exp-side-front-plate", side_plate(-EX_PLATE)))
    esd.append(g("exp-side-matrix-tray", side_tray(-EX_TRAY - 6)))
    esd.append(g("exp-side-bottom-plate", side_bottom_plate(EX_BOTTOM)))
    esd.append(g("exp-side-trajectory", [
        traj(-EX_PLATE, fy(ARCH_Y*0.9), FP_T + 2, fy(ARCH_Y*0.9)),
        traj(FP_T - EX_TRAY - 6, fy(CLK_Y), FP_T + 2, fy(CLK_Y)),
        traj((D-BP_D)/2 + 6, fy(0), (D-BP_D)/2 + 6, fy(0) + EX_BOTTOM),
        traj(D - (D-BP_D)/2 - 6, fy(0), D - (D-BP_D)/2 - 6, fy(0) + EX_BOTTOM),
        traj(D - ENC_Y, fy(H) - EX_KNOB, D - ENC_Y, fy(H) + 4),
        dim_h(-EX_PLATE, 0, fy(H) - EX_KNOB - KNOB_H - 10, f"explode {dt(EX_PLATE)}"),
        dim_v(fy(0), fy(0) + EX_BOTTOM, D + 18, f"drop {dt(EX_BOTTOM)}"),
    ]))
    esd.append(g("exp-side-balloons", [
        balloon(D - ENC_Y + KNOB_D/2, fy(H) - EX_KNOB - KNOB_H*0.5, 5, D + 18, fy(H) - EX_KNOB - 6),
        balloon(D - 6, fy(ARCH_Y*1.4), 1, D + 18, fy(ARCH_Y*1.05)),
        balloon(-EX_PLATE + FP_T/2, fy(ARCH_Y*1.25), 2, -EX_PLATE - 20, fy(ARCH_Y*1.5)),
        balloon((D-BP_D)/2 + BP_D*0.7, fy(0) + EX_BOTTOM + BP_T/2, 3, D + 18, fy(0) + EX_BOTTOM + 6),
        balloon(FP_T - EX_TRAY - 6 + TRAY_D/2, fy(CLK_Y), 4, -EX_PLATE - 20, fy(CLK_Y) + 26),
    ]))
    exp.append(g("EXP-SIDE", esd, es_x, es_y))
    o.append(g("EXPLODED", exp))

    # -------------------------------------------------------------- notes
    nx, ny = 70.0, 545.0
    L, ln = [], [0.0]

    def nl(s, cls="note", step=4.7):
        L.append(txt(0, ln[0], s, cls))
        ln[0] += step

    nl("(parts key: see the LEGEND box)", "note", 6.6)
    nl("NOTES", "lbl", 6.6)
    nl("a   Third-angle projection, mm, 1:1. (?) marks an unconfirmed value - measure it "
       "before you commit geometry.")
    nl(f"b   THE FORM IS DRIVEN BY THE CRESCENT. The shell arc R{dt(ARCH_R)} and the LED "
       f"crescent R{dt(CRES_R)} are CONCENTRIC about")
    nl(f"    ({dt(W/2)}, {dt(ARCH_Y)}), giving a constant {dt(ARCH_R-CRES_R)} mm rim - "
       f"{dt(ARCH_R-CRES_R-REVEAL)} of it on the front plate. The arc radius is W/2, so")
    nl(f"    the rim is set by W alone: rim = W/2 - {dt(CRES_R)}. Widen the body and the "
       "rim widens with it.")
    nl(f"c   The crown is a CYLINDER, not a sphere - it curves in FRONT only. SIDE is a flat-"
       f"topped box with an R{dt(R_SIDE)} edge break.")
    nl(f"d   W AND H ARE BOTH DERIVED, NOT CHOSEN. Bottom-up: floor {dt(FLOOR_Y)} | "
       f"tray {dt(TRAY_Y0)}-{dt(TRAY_Y1)} and speakers {dt(SPK_Y0)}-{dt(SPK_Y1)} "
       f"side by side |")
    nl(f"    mic array {dt(MIC_Y0)}-{dt(MIC_Y1)} spanning above them | crescent from "
       f"{dt(CRES_Y)}. W is then set by the SPEAKER BODY: it has to fit")
    nl(f"    between the plate edge and the {dt(TRAY_W)} tray, so W = 2 x (edge + "
       f"clr + {dt(SPK_BODY_W)} + clr + half-tray) = {dt(W)}.")
    nl(f"e   >>> WIDENING ALSO HEIGHTENS. The arc radius IS W/2, so H = W/2 + "
       f"{dt(CRES_Y)} = {dt(H)}. Every +2 mm of width buys +1 mm of height.")
    nl(f"    The {dt(MIC_PCB_W)} array is WIDER than the {dt(TRAY_W)} tray, so it "
       "cannot sit between the speakers - it spans above the whole cluster.")
    nl(f"    That is the cheaper arrangement: outboard would need W = 220 and a "
       f"30 mm rim; above gives W = {dt(W)} and a {dt(ARCH_R-CRES_R)} mm rim for "
       "3.5 mm more height.")
    nl(f"f   Speakers are Seeed Mono Enclosed 4R 5W: a SEALED BOX "
       f"{dt(SPK_BODY_W)} x {dt(SPK_BODY_H)} x {dt(SPK_BODY_D)}, not a bare cone. "
       f"They clear the tray by {dt(CLR_SPK_TRAY)} mm and")
    nl(f"    the crescent by {dt(CLR_SPK_CRES)} mm and the mic array by "
       f"{dt(CLR_SPK_MIC)} mm. A wider body grows W and H together.")
    nl(f"g   UPS 3S BOARD STANDS VERTICALLY. It is a {dt(UPS_W)} x {dt(UPS_H)} "
       f"board and {dt(UPS_H)} will not lie down in a {dt(IN_D)} interior, so the")
    nl(f"    whole board stands against the rear wall, {dt(UPS_D)} deep (?). That "
       "also puts its 12.6 V barrel jack on the wall that has the cutout.")
    nl(f"h   Clock zone eats {dt(FP_T+TRAY_D)} of the {dt(D)} depth (plate {dt(FP_T)} + "
       f"tray {dt(TRAY_D)}); ReSpeaker Flex + XIAO sit in the remaining "
       f"{dt(D - WALL - FP_T - TRAY_D - UPS_D)} mm.")
    nl(f"i   Charge input is a DC BARREL JACK on the Waveshare UPS 3S board - not USB-C. "
       "The only USB-C on the build is the XIAO's own")
    nl("    flashing port, which is internal and needs disassembly to reach (HARDWARE.md). "
       "Set the jack height off the as-built board.")
    nl(f"j   Knob is a full pebble: {chr(216)}{dt(KNOB_D)} at its widest, cut to a "
       f"{chr(216)}{dt(KNOB_BASE_D)} flat where it meets a {chr(216)}{dt(KNOB_BOSS_D)} boss "
       "on the crown.")
    nl(f"    Blind {chr(216)}{dt(KNOB_BORE_D)} bore x {dt(KNOB_BORE_H)} with a "
       f"{dt(KNOB_BORE_F)} D-flat. The encoder board mounts to a rib under the ridge.")
    nl(f"k   ToF sits on the crown beside the knob, board turned LONGWISE front-to-back so "
       f"its {dt(TOF_PCB_W)} edge clears the {dt(ENC_PCB)} encoder")
    nl(f"    board by {dt(TOF_BOARD_GAP)} mm - which is not a chosen gap but whatever "
       f"leaves {dt(BOSS_GAP_MIN)} mm between the two boards' nearest")
    nl(f"    bosses. Both carry FOUR {chr(216)}{QT_HOLE_D} holes {QT_HOLE_INSET} in from "
       f"every edge, and their hole rows sit at the same two depths, so the")
    nl(f"    bosses are separated in x alone. Pinhole lands "
       f"{dt(TOF_X - W/2 - KNOB_D/2)} mm right of the knob's widest point. Confirm where the "
       "chip sits on YOUR")
    nl("    breakout - the drawing assumes it is centred on the board.")
    nl(f"    Each crown board's four boss tips are COPLANAR, so the board sits flat "
       f"instead of following the arch: the ToF would")
    nl(f"    otherwise tilt 10.7 deg, aiming its 25 deg cone into the side of its own "
       f"vertical pinhole.")
    nl(f"l   Front plate seats into a rebate in the dome lip ({dt(LIP)} wide, "
       f"{dt(REVEAL)} reveal all round).")
    o.append(g("NOTES", L, nx, ny))

    o.append(g("PARTS-LEGEND", legend([
        f"DOME - 'D' extruded along the depth, open front + open bottom, "
        f"wall {dt(WALL)}",
        f"FRONT MODULE - one part: facade {dt(FP_T)}, diffuser pocket, "
        "diffusion cavity, matrix pocket, speaker nub posts, mic channel",
        f"BOTTOM PLATE - chassis: ReSpeaker Flex + UPS 3S, 6x M{dt(SCREW_D)}, "
        f"{dt(BP_CLR)} clearance/side",
        "MATRIX PAIR - 2x IS31FL3731, held by the front module itself",
        f"KNOB - pebble {chr(216)}{dt(KNOB_D)} x {dt(KNOB_H)} on a "
        f"{chr(216)}{dt(KNOB_BASE_D)} base flat",
        f"LED CARRIER - {dt(CARRIER_T)} plate, {CRES_PX} px in "
        f"{len([1 for _, n, _ in crescent_rows() if n])} cut segments, "
        f"{len(carrier_pads())}x M{dt(CARRIER_SCREW)} into the cavity wall",
    ], "PARTS"), 330.0, 560.0))

    # -------------------------------------------------------- title block
    tx0, ty0, tw, th = 936.0, 640.0, 238.0, 90.0
    tb = [
        f'<rect class="tb" x="0" y="0" width="{n(tw)}" height="{n(th)}"/>',
        line(0, 26, tw, 26, "tb"),
        line(0, 46, tw, 46, "tb"),
        line(0, 64, tw, 64, "tb"),
        line(tw*0.5, 46, tw*0.5, th, "tb"),
        line(tw*0.5, 26, tw*0.5, 46, "tb"),
        txt(6, 12, TITLE, "ttl"),
        txt(6, 20, SUBTITLE, "sub"),
        txt(6, 34, "PROJECTION   third angle", "note"),
        txt(6, 41, "UNITS   mm        SCALE   1:1", "note"),
        txt(tw*0.5 + 6, 34, "ENVELOPE", "note"),
        txt(tw*0.5 + 6, 41, f"{dt(W)} W x {dt(D)} D x {dt(H)} H", "note"),
        txt(6, 56, "PROJECT   Sound Machine (Faux Hatch)", "note"),
        txt(tw*0.5 + 6, 56, "CAD   Fusion 360", "note"),
        txt(6, 74, "GENERATED BY   3d-print/gen_drawing.py", "note"),
        txt(6, 82, "REFERENCE ONLY - not a released drawing", "note"),
        txt(tw*0.5 + 6, 74, "SHEET   1 of 1", "note"),
        txt(tw*0.5 + 6, 82, "REV   A", "note"),
    ]
    o.append(g("TITLE-BLOCK", tb, tx0, ty0))

    o.append("</svg>")
    return "\n".join(o)


if __name__ == "__main__":
    base = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(base, "enclosure-drawing.svg")
    open(out, "w").write(build())
    print(f"wrote {out}")
    print(f"envelope    {dt(W)} x {dt(D)} x {dt(H)} mm   wall {dt(WALL)}")
    print(f"front plate {dt(FP_W)} x {dt(FP_H)} x {dt(FP_T)}")
    print(f"bottom plate{dt(BP_W)} x {dt(BP_D)} x {dt(BP_T)}")
    print(f"interior    {dt(IN_W)} x {dt(IN_D)} x {dt(H-BP_T)}")
    print(f"crescent    {dt(CRES_R)} x {dt(CRES_RY)} ellipse, apex at "
          f"y={dt(CRES_Y+CRES_RY)} ({dt(H-CRES_Y-CRES_RY)} below the top)")
    print(f"knob        {chr(216)}{dt(KNOB_D)} x {dt(KNOB_H)} pebble on a "
          f"{chr(216)}{dt(KNOB_BASE_D)} flat; over-knob height {dt(H+KNOB_H)}")
    print(f"\nfacade stack (y up from the bottom of the envelope)")
    for lo, hi, what in [(0, BP_T, "bottom plate"),
                         (TRAY_Y0, TRAY_Y1, "matrix pair"),
                         (SPK_SEAT_Y0, SPK_SEAT_Y1, f"speaker seats ({dt(SPK_BODY_W)}x{dt(SPK_BODY_H)} bodies)"),
                         (MIC_Y0, MIC_Y1, "mic strip"),
                         (CRES_Y, CRES_Y + CRES_RY, "crescent"),
                         (H, H + KNOB_H, "knob")]:
        print(f"  {lo:7.2f} .. {hi:7.2f}   {what}")

    checks = [
        ("speaker -> floor",            SPK_Y0 - FLOOR_Y),
        ("speaker seat -> crescent",    CLR_SPK_CRES),
        # The array clears the speaker BODY vertically and the nub POST
        # horizontally -- it passes beside the post, not above it, which is
        # where the 6.35 mm of height came from. Two different axes on purpose.
        ("speaker body -> mic array (vert)", CLR_SPK_MIC),
        ("speaker NUB POST -> mic array (horiz)", CLR_NUB_MIC),
        ("  ...post/array y-overlap it covers", POST_MIC_Y_OVERLAP),
        ("min LED body -> diffuser edge", crescent_clearance()),
        ("speaker NUB -> plate edge",   CLR_NUB_EDGE),
        ("speaker -> plate edge",       SPK_X - SPK_BODY_W/2 - REVEAL),
        ("speaker -> tray (horiz)",     CLR_SPK_TRAY),
        ("tray -> mic strip",           MIC_Y0 - TRAY_Y1),
        ("mic strip -> crescent",       CRES_Y - MIC_Y1),
        ("crescent -> plate edge",      (ARCH_R - REVEAL) - CRES_R),
        ("crescent -> plate top",       (ARCH_RY - REVEAL) - CRES_RY),
        ("tray -> floor",               TRAY_Y0 - FLOOR_Y),
        ("pack -> side wall",           (IN_W - UPS_W)/2),
        ("pack -> matrix (depth)",      (D - WALL - UPS_D) - (FP_T + TRAY_D)),
        # the Flex is 110 wide on a wall that curves in above the springing line,
        # so the check is against the arc at its TOP edge, not at the floor
        ("Flex 110 -> arc at its top",  flex_wall_fit()[2]),
        # (Flex <-> UPS is HORIZONTAL now -- covered by the rear-wall pairs)
        ("Flex -> crown (vertical)",    H - WALL - (FLEX_WALL_Y + FLEX_H)),
        ("Flex depth -> tray",          (D - WALL - FLEX_D) - (FP_T + TRAY_D)),
    ]
    print("\nclearances")
    bad = [c for c in checks if c[1] < 0]
    for name, v in checks:
        print(f"  {'FAIL' if v < 0 else 'ok  '}  {v:7.2f}   {name}")
    # The rear wall is its own packing problem -- UPS, Flex, amp, lux, vents and
    # the jack all land on one face, so check every pair rather than eyeballing.
    rear = rear_wall_clearances()
    bad += [c for c in rear if c[1] < 0]
    print("\nrear wall (every pair)")
    for name, v in sorted(rear, key=lambda c: c[1]):
        print(f"  {'FAIL' if v < 0 else 'ok  '}  {v:7.2f}   {name}")
    print(f"W driven by  "
          + ("speaker + mic array" if W_FROM_SPK >= W_FROM_TRAY else "speaker + tray")
          + f"   (mic {dt(W_FROM_SPK)} vs tray {dt(W_FROM_TRAY)})")
    _cap, _rowcaps = cres_capacity(LED_ROW_PITCH)
    print(f"rim          {dt(CRES_RIM)} mm -- shell arch {dt(ARCH_R)} x {dt(ARCH_RY)}, "
          f"diffuser {dt(CRES_R)} x {dt(CRES_RY)}")
    print(f"crown        FLATTENED to k={CROWN_K} (a true semicircle would be "
          f"k=1.0 and H={dt(CRES_Y + ARCH_R)})")
    print(f"             aspect {W/H:.2f}:1 -- flattening is the ONLY lever on "
          f"height, since H = CRES_Y + k*W/2")
    print(f"\nCRESCENT  {dt(CRES_R)} x {dt(CRES_RY)} ellipse, {crescent_px()} px "
          f"(fixed) -- ROW LAYOUT for packages/hw/crescent.yaml:")
    print("   row      y     chord    px   strip run   end margin")
    for (w, c, run), yy in zip(crescent_rows(), crescent_row_ys()):
        print(f"        {yy:6.1f}  {w:7.1f}   {c:3d}   {run:7.1f}     {(w-run)/2:7.1f}")
    print(f"  row pitch {dt(LED_ROW_PITCH)} -- DERIVED, not chosen. The flattened "
          f"crown leaves only {dt(CRES_RY)} of")
    print(f"  height, so the pitch is whatever gets {CRES_PX} px on, floored at "
          f"the {dt(STRIP_W)} strip width + 1.")
    print(f"  capacity {_cap} px over {len(_rowcaps)} rows -> {CRES_PX} fitted = "
          f"{100*CRES_PX/_cap:.0f}% full (target {100*CRES_FILL_TARGET:.0f}%).")
    print(f"  NO FADE BAND any more: the LED field IS the diffuser ellipse, so "
          f"the glow reaches the edge.")

    def _w_for(body_w, flank):
        base = REVEAL + BOSS_EDGE + flank + body_w + flank + SPK_MIC_GAP
        return 2 * math.ceil(max(2*(base + TRAY_W/2),
                                 2*(REVEAL + BOSS_EDGE + MIC_PCB_W/2)) / 2)

    print(f"\nWIDTH<->HEIGHT COUPLING: H = CRES_Y + k*W/2 = {dt(CRES_Y)} + "
          f"{CROWN_K}*W/2. Every +2 on W is +{CROWN_K} on H.")
    print(f"  The speakers are ROTATED 90 deg so the nubs are TOP/BOTTOM: their "
          f"posts cost {dt(SPK_POST_H)} of")
    print(f"  HEIGHT each end instead of {dt(SPK_POST_H)} of WIDTH each flank, "
          f"and the body reads {dt(SPK_BODY_W)} wide not {dt(SPK_BODY_H)}.")
    for bw in (40.0, 45.0, 50.0):
        w = _w_for(bw, SPK_FLANK)
        flag = "  <-- actual (rotated)" if abs(bw - SPK_BODY_W) < 0.01 else ""
        print(f"  body {bw:5.1f} wide -> W {w:6.1f} -> H {CROWN_K*w/2 + CRES_Y:6.1f}"
              f"   bed 220: {'ok' if max(w, CROWN_K*w/2+CRES_Y) <= 220 else 'NO'}{flag}")
    print(f"\nWHAT THE ROTATION BOUGHT (nubs side-to-side would need a "
          f"{dt(SPK_FIT + SPK_NUB_PROJ + SPK_POST_WALL)} post per flank):")
    _side = _w_for(SPK_BODY_H, SPK_FIT + SPK_NUB_PROJ + SPK_POST_WALL)
    print(f"  nubs SIDE, {dt(SPK_BODY_H)} wide body  -> W {_side:6.1f}   "
          f"bed 220: {'ok' if _side <= 220 else 'NO'}")
    print(f"  nubs TOP/BOT, {dt(SPK_BODY_W)} wide body -> W {dt(W)}   bed 220: ok")
    print(f"\nBED FIT (Flashforge Adventurer 5M Pro, 220 cube) -- both parts WHOLE:")
    print(f"  dome           {dt(W)} x {dt(H)} x {dt(D)}  (lying on its back)")
    print(f"  front module   {dt(W-2*REVEAL)} x {dt(H-REVEAL-BP_T)} "
          f"-> {dt(220-(W-2*REVEAL))} / {dt(220-(H-REVEAL-BP_T))} mm to spare")
    print("\nALL CLEAR" if not bad else f"\n*** {len(bad)} COLLISION(S) ***")
