#!/usr/bin/env python3
"""Single source of truth for the Sound Machine enclosure geometry.

Every dimension, every derived value, and the part outlines. All three
sheets import this, so they cannot drift apart:

    gen_drawing.py    sheet 1 - shell: top / front / side / rear
    gen_internals.py  sheet 2 - internals, fixings, front-module section
    gen_wiring.py     sheet 3 - sensor chain and wire routing

>>> W and H are DERIVED, not chosen -- see "facade stack". Values marked
>>> (?) are UNCONFIRMED placeholders; measure before committing geometry.
"""
import math

from drawlib import n, rect, circ

# ---- envelope --------------------------------------------------------------
# ONLY D IS CHOSEN. W and H are both DERIVED from what has to fit on the front
# face (see "facade stack"):
#
#     W = 2 x (plate edge + driver + mic strip half-width)   <- side by side
#     H = W/2 + CRES_Y                                       <- concentric D
#
# >>> WIDENING ALSO HEIGHTENS. The arc radius IS W/2, so every 2 mm of extra
# >>> width adds 1 mm to H. Laying the mic array beside the drivers instead of
# >>> above them lowers CRES_Y, but the wider arc more than eats the saving.
# >>> There is no way around this while the arc stays concentric with the
# >>> crescent -- the numbers are printed at the bottom of the run.
D         = 64.0
WALL      = 2.5      # dome wall
RIM_MIN   = 12.0     # smallest acceptable shell-arc-to-crescent rim
# FORM: a letter "D" lying on its long flat side, extruded along the depth.
# The FRONT silhouette is straight sides + a semicircular top of radius W/2,
# CONCENTRIC with the LED crescent. The SIDE view is therefore a plain box with
# a flat top -- the crown is cylindrical, not spherical.
R_BOT     = 6.0                  # FRONT view bottom corner radius
R_PLAN    = 5.0                  # TOP view corner radius (an extrusion, so small)
R_SIDE    = 4.0                  # SIDE view edge break, top
R_SIDE_B  = 4.0                  # SIDE view edge break, bottom

# ---- plate interface -------------------------------------------------------
# The FRONT MODULE is one printed part: facade + diffuser pocket + diffusion
# cavity + matrix pocket + speaker baffle rings + mic channel. It SLIDES UP into
# a groove in the dome from below, and the bottom plate traps it there. No
# fasteners on the facade.
#
#   dome outer skin  ->  WALL      2.5
#   sliding clear    ->  FP_CLR    0.5     plate outline = inset 3.0
#   lip covers       ->  LIP_W     5.0     visible aperture = inset 7.5
#
# Front-to-back through the joint:  lip (LIP_T) | plate (FP_T) | rib (RIB_T)
FP_T      = 4.0      # front module baffle thickness. 4, NOT 3: two Ø40 drivers
                     #   on an unsupported 3 mm plate will flex and buzz.
FP_CLR    = 0.5      # sliding clearance, module edge to dome inner wall
# The whole front module is WRAPPED in acoustically transparent cloth, so the
# cloth goes through the groove with it and around the edge. Everything the
# module has to fit through grows by a layer of cloth on each face, and the
# module's own outline has to shrink by one layer so the wrapped assembly still
# clears the wall.
CLOTH_T   = 0.6      # (?) grille cloth, per layer -- MEASURE your cloth
LIP_W     = 5.0      # dome lip, radial -- how much it covers the plate edge
LIP_T     = 2.0      # dome lip thickness (sets how deep the facade is recessed)
RIB_T     = 2.5      # retaining rib behind the plate
RIB_W     = 5.0      # retaining rib, radial
SLOT_CLR  = 0.4      # groove width clearance
SLOT_W    = FP_T + 2*CLOTH_T + SLOT_CLR   # groove: cloth | module | cloth
BP_T      = 4.0      # bottom plate thickness
BP_CLR    = 0.30     # bottom plate clearance per side
SEAT_W    = 3.0      # continuous ledge the bottom plate lands on
REVEAL    = WALL + FP_CLR + CLOTH_T   # module outline inset, cloth included
LIP       = LIP_W - FP_CLR         # plate edge engaged under the lip

# ---- matrix tray (exact, from gen_tray.py -- do not edit) -----------------
TRAY_W, TRAY_H = 90.96, 32.54
TRAY_D         = 14.80        # FACE_T+PCB_T+STACK_GAP+BP_T+LIP_RUN+RAMP_RUN+1

# ---- facade features (FRONT view, y measured UP from the bottom) ----------
# The crescent SCALES WITH THE BODY. Its radius is derived so the concentric rim
# stays at RIM_MIN no matter how wide the parts push W. That keeps the look
# fixed -- but it changes the LED COUNT, which is a firmware change: see
# crescent_rows() and the run summary.
LED_PITCH = 16.7     # SK6812 60 LED/m
CRES_PX   = 48       # FIXED -- this is the strip you have. The crescent
                     #   RADIUS scales with the body, so the row layout has
                     #   to be re-solved to spend exactly 48 pixels on it.
LED_D     = 5.2      # SK6812 package, drawn indicatively
CLK_W     = 84.0     # clock aperture (LED span 81.3 + margin)
CLK_H     = 23.0     #   "        "   (LED span 20.3 + margin)
# Seeed Mono Enclosed Speaker 4R 5W (SS114993346): the body is a SQUARE-ish
# sealed box, not a bare round driver. 50 x 45 x 22, round cone inside.
SPK_BODY_W = 50.0    # body width  -- datasheet
SPK_BODY_H = 45.0    # body height -- datasheet
SPK_BODY_D = 22.0    # body depth  -- datasheet
SPK_GRILLE = 40.0    # (?) open cone diameter, inside the 45 body height
SPK_FIX    = 4       # (?) body mounting holes -- "built-in mounting holes"
SPK_FIX_W  = 44.0    # (?) hole pitch across the 50 body -- MEASURE
SPK_FIX_H  = 39.0    # (?) hole pitch up the 45 body    -- MEASURE
SPK_RING_W = 3.0     # raised baffle seat around each speaker body
# ---- ReSpeaker Flex linear 4-mic array, in the band above the clock -------
MIC_N      = 4
MIC_PITCH  = 33.0    # reSpeaker Flex Linear-4: 33 mm spacing -- Seeed wiki
MIC_PCB_W  = 110.0   # array board length 110 mm -- Seeed
MIC_PORT_D = 2.5     # (?) acoustic port through the front plate
MIC_PCB_H  = 12.0    # (?) array board width -- not published, MEASURE
MIC_FIX    = 2       # 2x M3 mounting holes on the linear array -- Seeed wiki

# ---- facade stack ----------------------------------------------------------
# LAYOUT: the clock and the mic array stack tightly into one central cluster,
# and the drivers flank that cluster. So the mic band only has to clear the
# TRAY vertically; it clears the drivers HORIZONTALLY instead, which is what
# sets W. Assembled bottom-up so nothing can silently overlap.
TRAY_GAP  = 1.0      # tray bottom clearance over the bottom plate
SPK_CLR   = 1.0      # clearance around a driver
GAP_MIC   = 2.0      # mic array clears the tray below it -- keep SMALL,
                     #   the tight matrix+mic cluster is the whole layout
SPK_MIC_GAP = 4.0    # gap between a speaker seat and the mic array
GAP_CRES  = 2.0      # crescent baseline clears the mic strip

FLOOR_Y  = BP_T                              # top face of the bottom plate
# THE CLUSTER: matrix tray with the mic array tight above it. This pairing is
# the whole point of the layout -- keep GAP_MIC small.
TRAY_Y0  = FLOOR_Y + TRAY_GAP
TRAY_Y1  = TRAY_Y0 + TRAY_H
MIC_Y0   = TRAY_Y1 + GAP_MIC                 # tight above the clock
MIC_Y1   = MIC_Y0 + MIC_PCB_H
# The speaker boxes FLANK that cluster, so they clear it horizontally and never
# push the mic band up. Their raised seat has to clear the bottom plate.
SPK_SEAT_Y0 = FLOOR_Y + SPK_CLR
SPK_Y0      = SPK_SEAT_Y0 + SPK_RING_W
SPK_Y1      = SPK_Y0 + SPK_BODY_H
SPK_SEAT_Y1 = SPK_Y1 + SPK_RING_W
# CRES_Y is the LED ROW CENTRE, so the bottom row hangs LED_D/2 below it.
# Without that term the bottom row of pixels buries itself in the speaker
# seats -- which is exactly what "losing the bottom pixels" looks like.
CRES_Y   = max(MIC_Y1, SPK_SEAT_Y1) + GAP_CRES + LED_D/2
ARCH_Y   = CRES_Y                            # concentric: same centre

# W: plate edge | clr | speaker body | clr | mic array ... mirrored.
# The 110 array is wider than the 91 tray, so the array sets the middle.
# edge | clr | seat ring | body | seat ring | gap | half the mic array
W_FROM_SPK  = 2 * (REVEAL + SPK_CLR + SPK_RING_W + SPK_BODY_W + SPK_RING_W
                   + SPK_MIC_GAP + MIC_PCB_W/2)
W_FROM_TRAY = 2 * (REVEAL + SPK_CLR + SPK_RING_W + SPK_BODY_W + SPK_RING_W
                   + SPK_MIC_GAP + TRAY_W/2)
W        = 2 * math.ceil(max(W_FROM_SPK, W_FROM_TRAY) / 2)   # <<< DERIVED width
ARCH_R   = W/2                               # arc radius = half the width
CRES_R   = ARCH_R - RIM_MIN                  # <<< crescent follows the body
H        = ARCH_Y + ARCH_R                   # <<< DERIVED height

CLK_Y    = (TRAY_Y0 + TRAY_Y1) / 2
MIC_Y    = (MIC_Y0 + MIC_Y1) / 2
SPK_X    = REVEAL + SPK_CLR + SPK_RING_W + SPK_BODY_W/2   # body centre
SPK_Y    = (SPK_Y0 + SPK_Y1) / 2

# Clearances the stack cannot enforce (all checked at the bottom of the run):
CLR_SPK_TRAY = (W/2 - TRAY_W/2) - (SPK_X + SPK_BODY_W/2)     # body -> tray
CLR_SPK_MIC  = (W/2 - MIC_PCB_W/2) - (SPK_X + SPK_BODY_W/2 + SPK_RING_W)
CLR_SPK_EDGE = (SPK_X - SPK_BODY_W/2 - SPK_RING_W) - REVEAL  # seat -> edge
CLR_SPK_CRES = CRES_Y - SPK_SEAT_Y1                          # seat -> crescent
SPK_W_MAX    = W/2 - MIC_PCB_W/2 - REVEAL - 2*SPK_CLR        # widest body

# ---- top surface controls --------------------------------------------------
# The knob is PART 5: a printed pebble that caps the seesaw encoder shaft. It
# seats on a flat boss milled into the cylindrical crown, on the top ridge.
ENC_SHAFT_D = 7.0    # clearance bore through the shell for the encoder shaft
ENC_Y       = 30.0   # knob centre, from the front face, in plan
ENC_PCB     = 25.4   # (?) Adafruit seesaw rotary breakout, 1.0" square
# The knob is a FULL pebble: an ellipse of revolution truncated by a shallow cut
# at the bottom, so only a small flat meets the crown. KNOB_BASE_D sets how much
# of the pebble is cut away -- closer to KNOB_D = more of a hemisphere.
KNOB_D      = 34.0   # widest diameter (occurs part-way up, not at the base)
KNOB_H      = 20.0   # total height above the boss
KNOB_BASE_D = 28.0   # diameter of the flat where it meets the crown
KNOB_BORE_D = 6.0    # (?) encoder shaft -- Adafruit seesaw is a 6 mm D-shaft
KNOB_BORE_F = 4.5    # (?) across the D-flat
KNOB_BORE_H = 15.0   # blind bore depth
KNOB_BOSS_D = 30.0   # flat seating pad on the crown, under the knob
# ---- capacitive touch: TWO pads, one on each upper shoulder --------------
# Tap either side to cycle presets. BOTH PADS SHARE ONE PIN (GPIO4 / D3,
# TOUCH4): self-capacitance sensing measures the whole electrode net, so two
# pads on one net behave exactly like one electrode that happens to be split in
# two. Touching either half adds the same delta.
#
# >>> THE ROUTING RULE THAT MAKES IT WORK: join the two leads AT THE MCU, not
# >>> by running a wire across the crown. Each pad's lead drops down the inside
# >>> of its own flank to the floor and they meet at the XIAO. Wire count is
# >>> identical either way, and it keeps a ~200 mm antenna out of the crown --
# >>> which is exactly where the SK6812 data line, the I2S lines and the STEMMA
# >>> chain all run.
#
# Cost of sharing: baseline capacitance roughly doubles while the finger delta
# stays the same, so relative sensitivity drops (still comfortably usable), and
# a side-to-side sensitivity mismatch cannot be trimmed out with per-pad
# thresholds. GPIO2 / D1 (TOUCH2) is kept FREE as the escape hatch -- splitting
# to two channels later is a one-wire change at the MCU plus a few lines of YAML.
TOUCH_SHARED_PIN = True
# The crown is a CYLINDER, so a flat copper strip wraps onto it with no
# distortion as long as its long axis runs front-to-back.
TOUCH_N      = 2
TOUCH_PAD_L  = 40.0  # along the depth (the developable direction)
TOUCH_PAD_W  = 22.0  # across the arc
TOUCH_Y      = 112.0 # height on the front view where the pad centre sits
TOUCH_DEPTH  = 38.0  # pad centre from the front face -- just behind the ToF
TOUCH_WALL   = 1.6   # local wall thinning behind each pad, from WALL
# ---- VL53L0X ToF, on the crown just to the right of the knob --------------
# Mounted LONGWISE front-to-back so the 17.8 mm edge clears the encoder board.
TOF_HOLE_D  = 3.5    # pinhole aperture through the crown (clears the 25 deg FoV)
TOF_PCB_W   = 17.8   # (?) Adafruit VL53L0X STEMMA QT breakout, short edge
TOF_PCB_D   = 25.4   # (?)   "                                  long edge
TOF_X       = W/2 + ENC_PCB/2 + 1.5 + TOF_PCB_W/2   # clears the encoder board
TOF_Y       = ENC_Y  # same front-offset as the knob, so it sits alongside

# ---- rear-wall features (see the REAR view; y up from the bottom) ---------
# The rear face is the same "D" as the front -- the body is an extrusion -- so
# the rear view is a true flat face. Everything on it is CENTRED in width.
LP_D, LP_Y      = 4.0, 100.0        # BH1750 light pipe ("lux"), centred
# The Waveshare UPS 3S charges through a DC-005 BARREL JACK, not USB-C. Height
# is set by where the jack lands on the UPS board -- confirm on the as-built.
BARREL_D        = 11.0              # (?) clearance for the DC-005 jack body
BARREL_Y        = 14.0              # (?) jack centre height, centred in width
VENT_W, VENT_HH = 40.0, 2.5         # rear vent slots
VENT_N, VENT_P  = 4, 7.0            # count, pitch
VENT_Y          = 118.0

# ---- internals shown for reference ----------------------------------------
# 3S pack, cells STANDING (18.5 dia x 65 long, 3 in a row). Lying flat the pack
# is 65 x 57 in plan, which collides with both speakers AND the matrix tray in
# a 179 x 59 floor -- see note (c). Standing, it tucks against the rear wall.
UPS_W, UPS_D, UPS_H = 57.0, 20.0, 65.0   # (?) 3x 18650 upright + holder
UPS_BACK            = 3.0                # gap from the interior rear wall
FOOT_D, FOOT_IN     = 12.0, 16.0         # rubber feet
SPK_BODY_D          = 22.0               # (?) speaker can depth

# ---- front module: diffuser + cavity + mounts ------------------------------
# The printed part is the FRAME and the diffusion cavity. The diffuser itself
# stays a separate Glowforge-cut white opal acrylic that drops into a pocket
# from behind -- you cannot print an even diffuser.
DIFF_T      = 3.0    # (?) opal acrylic thickness
DIFF_REBATE = DIFF_T + 0.2           # pocket depth on the back of the facade
DIFF_MARGIN = 1.5                    # pocket oversize on the crescent radius
# Air gap between the acrylic and the LEDs. Too small and you see 48 dots
# through the diffuser; ~0.7x the 16.7 mm LED pitch is the usual rule.
DIFF_GAP    = 12.0                   # (?) TUNE ON A TEST PRINT
LED_STRIP_T = 3.0                    # (?) SK6812 strip + adhesive
CAV_WALL    = 2.0                    # diffusion cavity wall, follows the arc
TRAY_REBATE = 2.0                    # pocket the matrix tray front face sits in
TRAY_FIT    = 0.20                   # interference on the tray pocket
SPK_BOLT    = 4                      # driver screws per side
SPK_BC      = 46.0   # (?) driver bolt circle -- MEASURE
MIC_CHAN_D  = 2.0                    # flex channel depth on the back
MIC_GASKET  = 1.0                    # foam gasket land around each port
# Depth of the front module at its deepest (the crescent zone):
FM_DEPTH    = FP_T + DIFF_REBATE + DIFF_GAP + LED_STRIP_T

# ---- dome <-> bottom plate fixings -----------------------------------------
# LUGS, not free-standing bosses: little pads that project INWARD off the dome
# wall, each with a blind hole for a heat-set insert. The screw goes up through
# the bottom plate and grabs the lug. This is better than a boss in the middle
# of the floor -- lugs live at the perimeter where the plate needs support
# anyway, and they cost no floor real estate.
SCREW_D     = 3.0                    # M3
SCREW_CLR   = 3.4                    # clearance hole in the bottom plate
SCREW_CBORE = 6.0                    # counterbore so heads sit below the feet
SCREW_CB_T  = 2.0
INSERT_D    = 4.0                    # (?) M3 x 5.0 heat-set insert hole
LUG_L       = 12.0                   # how far a lug reaches in off the wall
LUG_W       = 14.0                   # along the wall
LUG_H       = 9.0                    # thickness, above the bottom plate face

# Lug screw centres (x from left, depth from the front face). The FRONT edge
# gets none: the speaker bodies own both front corners and the tray owns the
# middle. It does not need any -- the plate's front edge is captured between
# the seating ledge and the front module's bottom edge.
_LX = WALL + LUG_L/2
SCREWS = [(_LX,     36.0), (W - _LX,     36.0),   # side walls, behind the speakers
          (_LX,     54.0), (W - _LX,     54.0),   # side walls, rear
          (55.0,  D - WALL - LUG_L/2),            # rear wall, outboard of the UPS
          (W - 55.0, D - WALL - LUG_L/2)]

# ---- what goes where inside --------------------------------------------------
# Waveshare UPS Module 3S: a 60 x 93 board with the three 18650 holders on it,
# charged from a 12.6 V 2 A barrel jack. 93 mm will NOT lie down in a 59 mm
# interior, so the whole board STANDS VERTICALLY against the rear wall -- which
# also puts its barrel jack on the wall that has the cutout.
UPS_W, UPS_D, UPS_H = 60.0, 24.0, 93.0   # 60x93 board; 24 deep = board + cells (?)
UPS_BACK            = 0.0                # stands hard against the rear wall

# The ReSpeaker Flex core is about a credit card, ~19 deep where the XIAO sits.
# It mounts VERTICALLY on the inside of the REAR WALL, above the UPS: that face
# is reachable the moment the front module is out, and it keeps the floor clear.
FLEX_W, FLEX_H, FLEX_D = 86.0, 54.0, 19.0    # (?) credit-card-ish -- MEASURE
FLEX_WALL_Y            = 103.0               # bottom edge, above the UPS

# The TPA2016 mounts FLUSH on the rear wall beside the UPS. Not a side wall:
# the sides are only vertical below the springing line, and the speaker boxes
# own all of that. Above the springing the sides are the curved crown, which is
# no good for a flat board.
AMP_W, AMP_D, AMP_H = 26.0, 20.0, 8.0        # (?) TPA2016 breakout
AMP_WALL_X, AMP_WALL_Y = 43.0, 40.0          # centre on the rear wall

# ---- explode offsets (drawing only) ---------------------------------------
EX_PLATE, EX_TRAY, EX_BOTTOM, EX_KNOB = 40.0, 18.0, 38.0, 20.0

# ---- sheet 1 chrome --------------------------------------------------------
SHEET_W, SHEET_H = 1189.0, 790.0
MARGIN           = 15.0
TITLE            = "SOUND MACHINE - ENCLOSURE SHELL"
SUBTITLE         = "dome / front module / bottom plate"

# ---- derived ---------------------------------------------------------------
IN_W  = W - 2*WALL                 # interior width
IN_D  = D - 2*WALL                 # interior depth
FP_W  = W - 2*REVEAL               # front module outline
FP_H  = H - 2*REVEAL
BP_W  = IN_W - 2*BP_CLR            # bottom plate
BP_D  = IN_D - 2*BP_CLR
APER_W = W - 2*(WALL + LIP_W)      # visible aperture inside the lip
APER_H = H - 2*(WALL + LIP_W)


def touch_x():
    """Where each shoulder pad lands in the FRONT view. The pad sits on the arc
    at height TOUCH_Y, so its x follows the arc, not the straight flank."""
    dy = TOUCH_Y - ARCH_Y
    half = (ARCH_R**2 - dy**2) ** 0.5
    return [W/2 - half, W/2 + half]


def floor_items():
    """Everything competing for the bottom-plate footprint, in PLAN:
    (name, x0, x1, depth0, depth1)."""
    return [
        ("speaker L",  SPK_X - SPK_BODY_W/2,     SPK_X + SPK_BODY_W/2,
         FP_T, FP_T + SPK_BODY_D),
        ("speaker R",  W - SPK_X - SPK_BODY_W/2, W - SPK_X + SPK_BODY_W/2,
         FP_T, FP_T + SPK_BODY_D),
        ("matrix tray", W/2 - TRAY_W/2, W/2 + TRAY_W/2, FP_T, FP_T + TRAY_D),
        ("UPS 3S (upright)", W/2 - UPS_W/2, W/2 + UPS_W/2,
         D - WALL - UPS_D, D - WALL),
    ]


def gap_1d(a0, a1, b0, b1):
    """Clearance between two 1-D spans; negative means they overlap."""
    return max(b0 - a1, a0 - b1)


def boss_clearances():
    """For each fixing LUG, its tightest clearance to anything on the floor.
    Two boxes in plan clear each other if they clear in EITHER axis, so the lug
    clearance is the better of the two gaps. The Flex bay is excluded -- it is
    an envelope bounded BY the lugs, not an obstacle."""
    out = []
    for bx, by in SCREWS:
        if abs(by - (D - WALL - LUG_L/2)) < 0.1:            # rear wall
            x0, x1 = bx - LUG_W/2, bx + LUG_W/2
            d0, d1 = D - WALL - LUG_L, D - WALL
        elif bx < W/2:                                       # left wall
            x0, x1 = WALL, WALL + LUG_L
            d0, d1 = by - LUG_W/2, by + LUG_W/2
        else:                                                # right wall
            x0, x1 = W - WALL - LUG_L, W - WALL
            d0, d1 = by - LUG_W/2, by + LUG_W/2
        worst, who = 1e9, ""
        for name, ox0, ox1, od0, od1 in floor_items():
            if name == "Flex bay":
                continue
            gap = max(gap_1d(x0, x1, ox0, ox1), gap_1d(d0, d1, od0, od1))
            if gap < worst:
                worst, who = gap, name
        out.append(((bx, by), worst, who))
    return out

def fy(y):
    """front-view: y measured UP from the envelope bottom -> svg y-down."""
    return H - y


def d_profile(inset, rb):
    """The 'D' on its long flat side: flat bottom, straight sides, semicircular
    top of radius ARCH_R - inset, all offset `inset` inward from the envelope."""
    x0, x1 = inset, W - inset
    yb, ys = fy(inset), fy(ARCH_Y)
    r = ARCH_R - inset
    return (f"M{n(x0)},{n(yb-rb)} V{n(ys)} "
            f"A{n(r)},{n(r)} 0 0 1 {n(x1)},{n(ys)} "
            f"V{n(yb-rb)} A{n(rb)},{n(rb)} 0 0 1 {n(x1-rb)},{n(yb)} "
            f"H{n(x0+rb)} A{n(rb)},{n(rb)} 0 0 1 {n(x0)},{n(yb-rb)} Z")


def knob_ellipse():
    """Semi-axes of the pebble, and how far its centre sits above the base cut.
    Solving w0 = a*sqrt(1-(yc/b)^2) with yc + b = KNOB_H."""
    a, w0 = KNOB_D/2, KNOB_BASE_D/2
    k = (1 - (w0/a) ** 2) ** 0.5
    b = KNOB_H / (1 + k)
    return a, b, b*k, w0            # a, b, centre-above-base, base half-width


def knob_profile(cx, base_y):
    """Full pebble: an ellipse truncated by a shallow cut at the bottom, so only
    a KNOB_BASE_D flat meets the crown. Large-arc, because the kept portion is
    more than half the ellipse."""
    a, b, _, w0 = knob_ellipse()
    return (f"M{n(cx-w0)},{n(base_y)} "
            f"A{n(a)},{n(b)} 0 1 1 {n(cx+w0)},{n(base_y)} Z")


def knob_bore(cx, base_y):
    return [rect(cx - KNOB_BORE_D/2, base_y - KNOB_BORE_H,
                 KNOB_BORE_D, KNOB_BORE_H, "hid")]


# The LED has a physical body (LED_D), so a pixel's CENTRE cannot sit on the
# crescent arc or on the flat baseline -- half the package would hang outside
# the diffusion box. Every row centre is therefore inset by the LED radius:
# baseline row at y = LED_D/2 (body resting on the floor), apex row at
# y = CRES_R - LED_D/2 (body touching the arc), and each row's outer pixel kept
# LED_D/2 clear of the chord. Without this inset the bottom row and the apex
# pixel both overhang the box by LED_D/2.
def _crescent_row_ys(n_rows):
    """n_rows LED-row CENTRE heights above the baseline, body-inset both ends."""
    y0, y1 = LED_D / 2, CRES_R - LED_D / 2
    if n_rows == 1:
        return [y0]
    return [y0 + i * (y1 - y0) / (n_rows - 1) for i in range(n_rows)]


def _crescent_row_cap(y, apex=False):
    """Most pixels that fit in the row at height y, keeping the outer pixel
    LED_D/2 clear of the arc (so the whole body stays inside the box)."""
    if apex:
        return 1
    usable = 2 * (max(CRES_R**2 - y**2, 0.0) ** 0.5 - LED_D / 2)
    return max(int(usable // LED_PITCH) + 1, 1)


def crescent_rows():
    """Lay exactly CRES_PX pixels onto the derived crescent radius.

    The strip pitch is fixed at LED_PITCH, so the only free variables are how
    many ROWS to use and how many pixels to put in each. Pick the fewest rows
    that could hold 48 while keeping every pixel BODY inside the diffusion box
    (see the inset note above), then trim proportionally to land on exactly 48.

    Returns (chord_width, count, strip_run) per row, bottom-first. chord_width
    is the true geometric chord at the (inset) row centre, so crescent_leds()
    recovers the same row height from it.
    """
    n_rows, ys, cap = None, None, None
    for n in range(4, 14):
        yy = _crescent_row_ys(n)
        caps = [_crescent_row_cap(y, apex=(i == n - 1)) for i, y in enumerate(yy)]
        if sum(caps) >= CRES_PX:
            n_rows, ys, cap = n, yy, caps
            break
    if n_rows is None:                       # radius too small for 48 -- fill it
        n_rows = 7
        ys = _crescent_row_ys(n_rows)
        cap = [_crescent_row_cap(y, apex=(i == n_rows - 1))
               for i, y in enumerate(ys)]

    # proportional trim to exactly CRES_PX, largest-remainder, apex stays at 1
    total = sum(cap)
    scale = CRES_PX / total
    exact = [c * scale for c in cap]
    cnt = [max(int(e), 1) for e in exact]
    cnt[-1] = 1
    short = CRES_PX - sum(cnt)
    order = sorted(range(n_rows - 1), key=lambda i: exact[i] - cnt[i], reverse=True)
    k = 0
    while short > 0:
        i = order[k % len(order)]
        if cnt[i] < cap[i]:
            cnt[i] += 1
            short -= 1
        k += 1
        if k > 400:
            break
    rows = []
    for i in range(n_rows):
        chord = 2 * max(CRES_R**2 - ys[i]**2, 0.0) ** 0.5
        rows.append((chord, cnt[i], max(cnt[i] - 1, 0) * LED_PITCH))
    return rows


def crescent_px():
    return sum(c for _, c, _ in crescent_rows())


def crescent_leds():
    """The LED positions, laid out on the crescent (indicative)."""
    o = []
    for w, k, run in crescent_rows():
        ry = (CRES_R**2 - (w/2)**2) ** 0.5
        for i in range(k):
            x = W/2 - run/2 + i * LED_PITCH if k > 1 else W/2
            o.append(circ(x, fy(CRES_Y + ry), LED_D, "led"))
    return o


def mic_x():
    return [W/2 + (i - (MIC_N-1)/2) * MIC_PITCH for i in range(MIC_N)]


def vent_y(i):
    return VENT_Y + i * VENT_P


