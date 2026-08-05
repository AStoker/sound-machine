#!/usr/bin/env python3
"""WILL IT TIP OVER BACKWARDS? -- the UPS-on-the-rear-wall question.

    python3 check_stability.py

The machine is a tall slab: 202 wide, 64 deep, 156 tall. Depth is the small
number, the rear wall is where the heavy things are bolted, and the rear feet do
NOT reach the rear wall -- they are 16 mm in from it, so the wall overhangs its
own support. Hanging a 190 g battery pack out there is exactly the move that
makes a device rock when you press its front panel button.

>>> THIS IS A MASS BUDGET, NOT A MEASUREMENT. Component masses are estimates and
>>> are labelled as such; the shell masses come from the real exported solids, so
>>> the part of the sum I control is honest. The conclusion has to survive the
>>> uncertainty in the estimates, so every number is also run at +-30 % on the
>>> battery and the answer is only reported as "fine" if it holds at both ends.

Two failure modes, and they are different:

  TIPPING     the centre of mass passes behind the rear foot line. Static, fatal,
              and a pure geometry question.
  ROCKING     a press on a control lifts the feet on the far side. This is what
              you actually notice, and it happens long before tipping -- but only
              for controls with leverage, i.e. high ones. Every control is
              enumerated from its own placement constant rather than assumed.
"""
import math
import os
import sys

import trimesh

import enclosure_geom as g
import frames

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.join(HERE, "models")

# --- what PLA actually weighs when printed ---------------------------------
# >>> A RANGE, NOT A NUMBER. Solid PLA is 1.24 g/cm^3, but these parts are mostly
# >>> thin wall and the slicer's infill makes the thick regions lighter. The shell
# >>> is BALLAST HERE -- it sits low and forward of the battery -- so a light
# >>> shell is the pessimistic case and a heavy shell flatters the design. Both
# >>> ends get run.
PLA_SOLID = 1.24 / 1000.0        # g per mm^3
INFILL_LIGHT = 0.62              # 3 walls / 15 % gyroid, thick regions
INFILL_HEAVY = 1.00

# --- the printed shell, from the real solids --------------------------------
# (file, depth of its COM from the FRONT face, why)
# >>> THE DOME'S OWN Z IS DEPTH-FROM-THE-FRONT, which was worth checking rather
# >>> than assuming: sampling its volume in z-slabs shows the last 8 mm is 33 %
# >>> full, i.e. the 2.5 mm rear wall, so z = 64 is the REAR. Guessing the other
# >>> way round would have moved the shell's COM 20 mm and reversed the answer.
SHELL = [
    ("dome.stl",         None, "own z is depth from the front"),
    ("bottom-plate.stl", None, "own y is depth; offset by wall + clearance"),
    ("front-module.stl", None, "own z is thickness behind the facade"),
    ("led-carrier.stl",  None, "lies against the inside of the facade"),
    ("matrix-tray.stl",  None, "just behind the facade"),
    ("knob.stl",         None, "on the crown, over the encoder"),
]

# --- the contents ----------------------------------------------------------
# (name, grams, depth of COM from the front, is_estimate, note)
UPS_G = 190.0          # 3 x 18650 at ~47 g + the Waveshare board at ~45
CONTENTS = [
    ("UPS 3S + cells", UPS_G,
     g.D - g.WALL - g.UPS_D / 2, True, "bolted to the rear wall"),
    ("Flex core", 25.0,
     g.D - g.WALL - g.FLEX_CORE_D / 2, True, "rear wall, above the UPS"),
    ("speaker", 40.0, 14.0, True, "front, behind the grille"),
    ("TPA2016", 8.0, g.AMP_DEPTH, True, "floor"),
    ("matrix pair + driver", 14.0, 1.5 + g.MTX_STACK_H / 2, False,
     "clipped to the facade"),
    ("LED strips + wiring", 20.0, 12.0, True, "carrier, low and forward"),
    ("small breakouts", 12.0, g.D - g.WALL - 5.0, True,
     "RTC, lux, encoder, ToF -- all on the rear wall or crown"),
]

# --- the support polygon ----------------------------------------------------
# >>> THE FEET ARE THE FOOTPRINT, NOT THE PLATE. 16 mm in from each wall, Ø12,
# >>> so the rear contact edge is at D - WALL - FOOT_IN + FOOT_D/2 -- and the rear
# >>> wall stands 12.5 mm BEHIND it, cantilevered over nothing.
FOOT_FRONT = g.WALL + g.FOOT_IN - g.FOOT_D / 2
FOOT_REAR = g.D - g.WALL - g.FOOT_IN + g.FOOT_D / 2

_out, bad = [], []


def say(s):
    _out.append(s)
    print(s)


def chk(name, margin, unit="mm"):
    ok = margin > 0
    say(f"  {'ok  ' if ok else 'FAIL'} {margin:8.2f}   {name}")
    if not ok:
        bad.append(name)


# ---------------------------------------------------------------------------
# where the shell's mass is
# ---------------------------------------------------------------------------
say("printed shell, measured off the exported solids")
shell_parts = []
for fn, _, why in SHELL:
    path = os.path.join(MODELS, fn)
    if not os.path.exists(path):
        say(f"  --   {fn} not exported; skipped")
        continue
    m = trimesh.load(path)
    # >>> INTO THE ASSEMBLY FRAME FIRST. This used to read each file's raw z (or,
    # >>> for the plate, its raw y plus an offset) and call the result a depth. That
    # >>> silently became wrong the moment the dome started exporting rear-wall-down
    # >>> -- it put the dome's centre of mass 30 mm from where it is, in the one
    # >>> calculation that is entirely about where mass sits front-to-back.
    # >>> frames.py owns the transforms; nothing here guesses.
    if fn in frames.TO_ASSEMBLY:
        frames.to_assembly(m, fn)
    vol = m.volume
    com = m.center_mass
    if fn == "knob.stl":
        depth = g.ENC_Y                # sits on the crown, over the encoder
    else:
        depth = float(com[2])          # assembly z IS depth, for every part
    shell_parts.append((fn, vol, depth))
    say(f"  {fn:20s} {vol/1000:6.1f} cm^3   COM {depth:5.1f} mm from the front")

say("")
say(f"support     feet contact from {FOOT_FRONT:.1f} to {FOOT_REAR:.1f} mm deep; "
    f"the rear wall is at {g.D - g.WALL:.1f}")
say(f"            so the wall overhangs its own support by "
    f"{(g.D - g.WALL) - FOOT_REAR:.1f} mm")


def budget(infill, ups_g):
    """Total mass and COM depth for one set of assumptions."""
    items = [(fn, vol * PLA_SOLID * infill, d) for fn, vol, d in shell_parts]
    for nm, gm, d, _est, _n in CONTENTS:
        items.append((nm, ups_g if nm.startswith("UPS") else gm, d))
    M = sum(gm for _, gm, _ in items)
    com = sum(gm * d for _, gm, d in items) / M
    return M, com, items


# ---------------------------------------------------------------------------
# the four corners of the assumption box
# ---------------------------------------------------------------------------
say("")
say("centre of mass, across the assumptions")
worst_com, worst_case = -1e9, None
rows = []
for infill, iname in ((INFILL_LIGHT, "light shell"), (INFILL_HEAVY, "solid shell")):
    for f, fname in ((0.7, "-30 % UPS"), (1.0, "nominal"), (1.3, "+30 % UPS")):
        M, com, _ = budget(infill, UPS_G * f)
        rows.append((iname, fname, M, com))
        say(f"  {iname:12s} {fname:10s}  {M:6.0f} g   COM {com:5.1f} mm deep  "
            f"({FOOT_REAR - com:+5.1f} from the rear foot line)")
        if com > worst_com:
            worst_com, worst_case = com, f"{iname}, {fname}"
say(f"  worst case for tipping: {worst_case}, COM {worst_com:.1f} mm deep")

M_nom, com_nom, items = budget(INFILL_LIGHT, UPS_G)

# ---------------------------------------------------------------------------
# the two failure modes
# ---------------------------------------------------------------------------
say("")
say("1. static tipping -- does it stand up on its own?")
chk("COM is forward of the rear foot line (worst case)", FOOT_REAR - worst_com)
_tip_angle = math.degrees(math.atan2(FOOT_REAR - worst_com, g.H / 2))
say(f"  ----  {_tip_angle:7.2f}   deg of backward tilt before it goes over "
    f"(COM at half height)")
chk("survives a 5 deg tilt -- a soft mattress edge, a rug", _tip_angle - 5.0)

say("")
say("2. rocking -- what can actually push it over?")
# >>> THE FIRST VERSION OF THIS CHECK INVENTED ITS LOAD CASE. It computed the force
# >>> needed to lift the front feet by pressing a front-panel button at z = 100 --
# >>> and reported a scary 85 gf. There is no front-panel button. The height came
# >>> from a `getattr(g, "SW_Y", 100.0)` fallback that silently fired because the
# >>> constant is called SW_WALL_Y, so the number was a default masquerading as
# >>> geometry. Enumerate the controls that EXIST instead, from the constants that
# >>> place them.
_G = 9.81e-3                                    # N per gram
_lever_rear = FOOT_REAR - com_nom               # resists rotating backward
_lever_front = com_nom - FOOT_FRONT             # resists rotating forward

# (name, height of the load, which way it pushes, lever that resists it)
LOADS = [
    ("UPS push button (rear wall, SW_WALL_Y)", g.SW_WALL_Y, "forward", _lever_front),
    ("barrel jack / USB cable tug (rear, low)", g.BARREL_WALL_Y
     if hasattr(g, "BARREL_WALL_Y") else g.SW_WALL_Y, "backward", _lever_rear),
]
for nm, z, direction, lever in LOADS:
    F = M_nom * _G * lever / max(z, 1.0)        # N at that height
    say(f"  ---- {F*102:8.0f}   gf {direction} at z={z:.0f} to start lifting "
        f"-- {nm}")
    chk(f"{nm}: needs over 500 gf", F * 102 - 500.0)

# >>> The capacitive pads take NO force at all, which is the point of them -- they
# >>> are the only controls up on the crown where a press would have leverage.
say(f"  ----      n/a   the {g.TOUCH_N} crown pads are capacitive: no force, so "
    f"the one high control cannot rock it")

# ---------------------------------------------------------------------------
# 3. THE QUESTION THAT WAS ACTUALLY ASKED
# ---------------------------------------------------------------------------
# >>> "DOES THE UPS ON THE REAR WALL PUT TOO MUCH WEIGHT BACK THERE?" is a
# >>> comparison, not an absolute -- and it has to be answered as one. A shove on
# >>> the top of ANY object 156 mm tall standing on a 39 mm foot span goes over
# >>> easily; quoting that number as a UPS problem would blame the battery for the
# >>> proportions. Measure the DELTA the battery is responsible for.
say("")
say("3. the UPS's own contribution -- with it versus without it")


def shove(M, com, z):
    """gf of backward push at height z that starts to lift the front feet."""
    return M * _G * (FOOT_REAR - com) / z * 102


M_no, com_no, _ = budget(INFILL_LIGHT, 0.0)
_z = g.H
say(f"  without the UPS   {M_no:5.0f} g   COM {com_no:5.1f} mm   "
    f"{shove(M_no, com_no, _z):4.0f} gf to shove the top over")
say(f"  with the UPS      {M_nom:5.0f} g   COM {com_nom:5.1f} mm   "
    f"{shove(M_nom, com_nom, _z):4.0f} gf to shove the top over")
_shift = com_nom - com_no
say(f"  the battery moves the COM {_shift:+.1f} mm rearward and changes the shove "
    f"force by {shove(M_nom, com_nom, _z) - shove(M_no, com_no, _z):+.0f} gf")
# >>> A 5 mm CAP ON THE COM SHIFT USED TO BE CHECKED HERE, and it FAILED at 7.4
# >>> while the thing it was standing in for -- the force needed to shove the
# >>> machine over -- got BETTER. That is a proxy threshold, invented to look
# >>> rigorous, contradicting the outcome it was a proxy for. Checks that cry wolf
# >>> are worse than no check: keep the outcome, report the shift as information.
chk("the UPS does not make the machine easier to shove over",
    shove(M_nom, com_nom, _z) - shove(M_no, com_no, _z))
say("  >>> it gets HARDER, not easier: the pack is heavy but it is also LOW, and")
say("      adding mass low down buys more restoring moment than the few mm of")
say("      rearward COM shift costs. The rear wall is the right place for it.")

# ---------------------------------------------------------------------------
# 4. WHAT WOULD ACTUALLY HELP
# ---------------------------------------------------------------------------
# >>> ~55 gf to topple it from the top is low, and it is NOT the battery's fault --
# >>> it is 156 mm of height on a 39 mm foot span. The one free variable is where
# >>> the feet go: FOOT_IN is 16 mm, and every mm it comes in is a mm of lever.
say("")
say(f"4. foot inset is the cheap lever (FOOT_IN is {g.FOOT_IN} today)")
for _fi in (16.0, 12.0, 8.0, 5.0):
    _fr = g.D - g.WALL - _fi + g.FOOT_D / 2
    _f = M_nom * _G * (_fr - com_nom) / g.H * 102
    _over = (g.D - g.WALL) - _fr
    say(f"  FOOT_IN {_fi:4.1f} -> rear contact {_fr:5.1f} mm, {_f:4.0f} gf to "
        f"shove over ({_f/56.0:.1f}x), wall overhang {_over:+5.1f} mm")
say("  the limit is the wall itself: once the foot's rear edge passes the wall")
say("  line the foot is hanging off the plate, so FOOT_IN 8 is about the floor.")

say("")
say("what the numbers say")
_pull = sum(gm * (d - com_nom) for nm, gm, d in items if d > FOOT_REAR)
say(f"  the mass BEHIND the rear feet is "
    f"{sum(gm for nm, gm, d in items if d > FOOT_REAR):.0f} g of {M_nom:.0f} g")
say(f"  the dome shell alone is {shell_parts[0][1]*PLA_SOLID*INFILL_LIGHT:.0f} g "
    f"at {shell_parts[0][2]:.0f} mm, which is most of the ballast")

say("")
say("ALL CLEAR" if not bad else f"*** {len(bad)} PROBLEM(S) ***")
if bad:
    sys.exit(1)
