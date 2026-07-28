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
RIM_MIN_LOOK = 12.0  # smallest rim we'd accept on looks alone
# RIM_MIN itself is DERIVED further down: the diffusion cavity wall stands off
# the back of the crescent, and it has to clear the dome's retaining rib, which
# turns out to bind before the aesthetic minimum does. See BOSS_EDGE.
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
# RIB_W is 3, NOT 5. The rib only has to stop the module tipping forward out of
# the dome -- the bottom plate already traps it -- and 3 mm behind a 4 mm plate
# is ample. It matters because the rib grips the BACK face, so it is a keep-out
# for every boss on the back, and that keep-out is multiplied by four across the
# width (two flanks x two speakers). Going 5 -> 3 gives back 4 mm of body width.
RIB_W     = 3.0      # retaining rib, radial
SLOT_CLR  = 0.4      # groove width clearance
SLOT_W    = FP_T + 2*CLOTH_T + SLOT_CLR   # groove: cloth | module | cloth
BP_T      = 4.0      # bottom plate thickness
BP_CLR    = 0.30     # bottom plate clearance per side
SEAT_W    = 3.0      # continuous ledge the bottom plate lands on
REVEAL    = WALL + FP_CLR + CLOTH_T   # module outline inset, cloth included
LIP       = LIP_W - FP_CLR         # plate edge engaged under the lip

# >>> THE BACK-FACE KEEP-OUT. The module SLIDES UP a groove, and the dome's
# >>> retaining rib grips the outer RIB_W of its BACK face all along both flanks
# >>> and the arc. Anything standing proud of the back face inside that band --
# >>> a speaker post, a stiffening rib, the diffusion cavity wall -- jams the
# >>> module on assembly. A 2D drawing cannot see this: on the flat it looks
# >>> like clearance to the outline, and the outline is not the constraint.
# >>> Every boss is checked against this band in gen_front_plate.py.
BOSS_EDGE = RIB_W + 1.0            # edge -> nearest back-face boss


def _rim_min():
    """The rim is NOT a free aesthetic choice.

    Walking outward from the crescent: the acrylic pocket is DIFF_MARGIN wider
    than the aperture, the cavity wall is CAV_WALL outside that, and the whole
    lot stands proud of the back face -- so it has to stop BOSS_EDGE short of
    the module edge, which is itself REVEAL inside the shell. Add it up and that
    is the smallest rim the shell can physically carry."""
    return max(RIM_MIN_LOOK, REVEAL + BOSS_EDGE + DIFF_MARGIN + CAV_WALL)

# ---- diffusion stack (needed early: it sizes RIM_MIN) ----------------------
# The diffuser is a separate Glowforge-cut opal acrylic that drops into a pocket
# from behind -- you cannot print an even diffuser.
DIFF_T      = 3.0    # (?) opal acrylic thickness
DIFF_REBATE = DIFF_T + 0.2           # pocket depth on the back of the facade
DIFF_MARGIN = 1.5                    # pocket oversize on the crescent radius
CAV_WALL    = 2.0                    # diffusion cavity wall, follows the arc

RIM_MIN   = _rim_min()               # <<< DERIVED, see above -- not a look

# ---- the clock: TWO matrices held DIRECTLY BY THE FRAME --------------------
# >>> THE TWO MATRICES ARE ONLY LOOSELY SOLDERED TO EACH OTHER. They are not a
# >>> rigid unit, so the front module has to locate EACH BOARD independently --
# >>> posts through its own mounting holes -- and clamp the pair down with clips
# >>> on all four sides. Treating the pair as one part is what a pocket alone
# >>> would do, and it would let the joint work loose.
#
# Board geometry is exact, from Adafruit's EAGLE files (same source gen_tray.py
# uses). Do not edit.
MTX_BOARD_W = 43.18                  # one IS31FL3731 16x9 board
MTX_BOARD_H = 27.94
MTX_N       = 2                      # butted side by side
MTX_HOLES   = [(1.905, 26.035), (41.275, 1.905)]   # diagonal pair, board-local
MTX_HOLE_D  = 2.0
MTX_PCB_T   = 1.6                    # matrix thickness
MTX_BP_T    = 1.6                    # driver backpack thickness
MTX_STACK_GAP = 5.0                  # matrix back -> backpack front (headers)
MTX_CLIP_Z  = 2.5                    # clip hook standing behind the backpack

# TRAY_* is the CLOCK MODULE FOOTPRINT -- now the bare matrix pair, not the
# separate snap-in tray. matrix-tray.stl remains a valid standalone part, but
# the front module carries the boards itself: one less part, and 4.6 mm of
# facade height back.
TRAY_W, TRAY_H = MTX_N * MTX_BOARD_W, MTX_BOARD_H          # 86.36 x 27.94
TRAY_D         = MTX_PCB_T + MTX_STACK_GAP + MTX_BP_T + MTX_CLIP_Z

# ---- facade features (FRONT view, y measured UP from the bottom) ----------
# The crescent SCALES WITH THE BODY. Its radius is derived so the concentric rim
# stays at RIM_MIN no matter how wide the parts push W. That keeps the look
# fixed -- but it changes the LED COUNT, which is a firmware change: see
# crescent_rows() and the run summary.
LED_PITCH = 16.7     # SK6812 60 LED/m -- FIXED by the strip, along a row
CRES_PX   = 48       # FIXED -- this is the strip you have. The crescent
                     #   RADIUS scales with the body, so the row layout has
                     #   to be re-solved to spend exactly 48 pixels on it.
LED_D     = 5.2      # SK6812 package, drawn indicatively
# ROW pitch is the one spacing we actually control: within a row the strip fixes
# it at LED_PITCH, but the gap BETWEEN rows is ours to choose. Earlier revisions
# derived it by stretching however many rows we had across the full radius,
# which gave 20.6 mm rows against 16.7 mm columns -- visibly stretched. Now it
# is set, and the RADIUS is solved to suit (see CRES_R below).
LED_ROW_PITCH = LED_PITCH            # square grid; drop to 0.866x for hex
# THE LED FIELD AND THE DIFFUSER ARE TWO DIFFERENT RADII.
#
#   CRES_R  the diffuser arc -- what you SEE. Sits at the concentric maximum,
#           so the rim stays at RIM_MIN and the crescent is as big as the shell
#           allows.
#   LED_R   the arc the 48 pixels are laid out on. Smaller, sized so the strip
#           actually fills its rows at a sane density.
#
# The band between them is UNLIT ON PURPOSE. Trying to light the diffuser right
# out to its edge with only 48 pixels means spreading them thin; letting the
# glow die out before the edge gives a natural fade-off instead, and the acrylic
# does the work. CRES_FADE is how much fade you get at the apex.
#
# CRES_FILL_MIN sizes the LED field: how much of that arc's pixel capacity the
# 48 have to occupy.
#   0.84 -> LED_R 96, rows 10/10/9/8/7/4            <-- default
#   0.94 -> denser still, smaller lit area
#   0.00 -> LED field expands to the diffuser arc (no fade band, sparse rows)
CRES_FILL_MIN = 0.84
CLK_W     = 84.0     # clock aperture (LED span 81.3 + margin)
CLK_H     = 23.0     #   "        "   (LED span 20.3 + margin)
# Seeed Mono Enclosed Speaker 4R 5W (SS114993346): the body is a SQUARE-ish
# sealed box, not a bare round driver. 50 x 45 x 22, round cone inside.
SPK_BODY_W = 50.0    # body width  -- datasheet
SPK_BODY_H = 45.0    # body height -- datasheet
SPK_BODY_D = 22.0    # body depth  -- datasheet
SPK_GRILLE = 40.0    # (?) open cone diameter, inside the 45 body height
SPK_RING_W = 3.0     # raised baffle seat around each speaker body
# MOUNTING IS ON THE SIDES, NOT THE FACE. Each body carries one NUB per side --
# a little ear that sticks out past the 50 mm body, centred on the 45 mm side
# height, its face set back 7 mm from the speaker's front face. So the front
# module does NOT get a bolt pattern on the baffle; it gets a POST beside each
# flank, standing SPK_NUB_Z proud of the module's back face, that the nub lands
# on and a screw goes into.
#
# >>> THIS IS A WIDTH DRIVER. The nubs, not the body, are the widest part of the
# >>> speaker, and each one needs a post beside it. Every +1 mm of nub
# >>> projection costs +4 mm of body width (2 sides x 2 speakers) and, because
# >>> the arc radius is W/2, +2 mm of height. Measure SPK_NUB_PROJ before you
# >>> commit the print.
SPK_FIX      = 2     # fixings per speaker: one nub per side
SPK_NUB_Z    = 7.0   # front face -> nub landing face  -- MEASURED
SPK_NUB_PROJ = 4.0   # (?) how far a nub stands off the 50 body -- MEASURE
SPK_NUB_W    = 8.0   # (?) nub size along the depth   -- MEASURE
SPK_NUB_H    = 6.0   # (?) nub size up the side       -- MEASURE
SPK_NUB_SCREW = 3.0  # (?) M3 through the nub
SPK_POST_WALL = 2.0  # material outboard of the screw, in the module post
SPK_FIT       = 0.35 # per side, body to its locating rib / post
# The seat has to be wide enough for the post beside the nub, so it is derived
# from the nub, not chosen. This is what actually sets the speaker's footprint.
# SPK_FIT is in here because the post sits OUTSIDE the fit gap, not inside it --
# leaving it out made the derivation 0.35 short and put the post into the dome's
# rib band.
SPK_SEAT_W = max(SPK_RING_W, SPK_FIT + SPK_NUB_PROJ + SPK_POST_WALL)
SPK_MOUNT_W = SPK_BODY_W + 2 * SPK_NUB_PROJ      # widest point of the speaker
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
# Room BELOW the matrix and ABOVE it, for the retention clips to root. This used
# to be 1.0 / 2.0 -- tight on purpose, back when the cluster set the height. It
# no longer does (the speaker seats do, at 56), so there is ~9 mm of slack in
# the stack and it costs nothing to spend it on somewhere to put the clips.
TRAY_GAP  = 4.0      # module bottom edge -> matrix, room for a bottom clip
SPK_CLR   = 1.0      # clearance around a driver
GAP_MIC   = 4.0      # matrix -> mic array, room for a top clip (see TRAY_GAP)
SPK_MIC_GAP = 3.0    # gap between a speaker seat and the mic array
GAP_CRES  = 2.0      # crescent baseline clears the mic strip

FLOOR_Y  = BP_T                              # top face of the bottom plate
# THE CLUSTER: the matrix pair with the mic array above it. The pairing still
# drives the LAYOUT (they share the facade's middle band, drivers flanking), but
# it no longer drives the HEIGHT -- the speaker seats do. So the gaps above and
# below the matrix are spent on clip roots rather than squeezed to nothing.
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
# The nubs are centred on the side, so they add nothing vertically -- they only
# push the seat out sideways, which is handled in the width derivation below.
SPK_NUB_Y   = (SPK_Y0 + SPK_Y1) / 2
# CRES_Y is the LED ROW CENTRE, so the bottom row hangs LED_D/2 below it.
# Without that term the bottom row of pixels buries itself in the speaker
# seats -- which is exactly what "losing the bottom pixels" looks like.
CRES_Y   = max(MIC_Y1, SPK_SEAT_Y1) + GAP_CRES + LED_D/2
ARCH_Y   = CRES_Y                            # concentric: same centre

# W: plate edge | clr | speaker body | clr | mic array ... mirrored.
# The 110 array is wider than the 91 tray, so the array sets the middle.
# edge | BOSS_EDGE | seat+post | body | seat+post | gap | half the mic array
# SPK_SEAT_W (not SPK_RING_W) is the lateral budget each flank needs, because
# the mounting nub and its post live there.
#
# >>> The edge term is BOSS_EDGE, not SPK_CLR. The speaker seat is a BOSS on the
# >>> back face, so what it has to clear is the dome's retaining rib band, not
# >>> the module outline. Using the 1 mm driver clearance here put the outboard
# >>> post 4.35 mm inside the rib -- the module would not have slid into the
# >>> dome, and nothing in the 2D views could show it.
W_FROM_SPK  = 2 * (REVEAL + BOSS_EDGE + SPK_SEAT_W + SPK_BODY_W + SPK_SEAT_W
                   + SPK_MIC_GAP + MIC_PCB_W/2)
W_FROM_TRAY = 2 * (REVEAL + BOSS_EDGE + SPK_SEAT_W + SPK_BODY_W + SPK_SEAT_W
                   + SPK_MIC_GAP + TRAY_W/2)
W        = 2 * math.ceil(max(W_FROM_SPK, W_FROM_TRAY) / 2)   # <<< DERIVED width
ARCH_R   = W/2                               # arc radius = half the width
H        = ARCH_Y + ARCH_R                   # <<< DERIVED height


def cres_capacity(r):
    """How many pixels a crescent of radius r holds, at LED_ROW_PITCH rows and
    LED_PITCH columns, with every LED BODY inside the box. Returns (total, rows)
    where rows is the per-row capacity list, bottom-first."""
    caps, y = [], LED_D / 2
    apex = r - LED_D / 2
    while y <= apex + 1e-9:
        usable = 2 * (max(r**2 - y**2, 0.0) ** 0.5 - LED_D / 2)
        caps.append(max(int(usable // LED_PITCH) + 1, 1))
        y += LED_ROW_PITCH
    if not caps:
        caps = [1]
    return sum(caps), caps


def _solve_led_r():
    """Largest radius that 48 pixels can actually FILL, for the LED field.

    The diffuser arc is a separate, bigger radius (CRES_R). Here the binding
    constraint is density: capacity grows with area, so a big radius means the
    48 pixels cover a small fraction of each row. Walk down from the diffuser
    arc until the fill fraction clears CRES_FILL_MIN."""
    r_max = ARCH_R - RIM_MIN
    if CRES_FILL_MIN <= 0:
        return r_max
    r = r_max
    while r > 20.0:
        total, _ = cres_capacity(r)
        if total >= CRES_PX and CRES_PX / total >= CRES_FILL_MIN:
            return round(r, 1)
        r -= 0.5
    return r_max


CRES_R   = ARCH_R - RIM_MIN          # <<< the DIFFUSER arc -- concentric max
CRES_RIM = ARCH_R - CRES_R           # rim between shell and diffuser
LED_R    = _solve_led_r()            # <<< the arc the 48 PIXELS sit on
CRES_FADE = CRES_R - LED_R           # unlit fade band at the apex

CLK_Y    = (TRAY_Y0 + TRAY_Y1) / 2
MIC_Y    = (MIC_Y0 + MIC_Y1) / 2
SPK_X    = REVEAL + BOSS_EDGE + SPK_SEAT_W + SPK_BODY_W/2  # body centre
SPK_Y    = (SPK_Y0 + SPK_Y1) / 2

# Clearances the stack cannot enforce (all checked at the bottom of the run):
CLR_SPK_TRAY = (W/2 - TRAY_W/2) - (SPK_X + SPK_BODY_W/2)     # body -> tray
CLR_SPK_MIC  = (W/2 - MIC_PCB_W/2) - (SPK_X + SPK_BODY_W/2 + SPK_SEAT_W)
CLR_SPK_EDGE = (SPK_X - SPK_BODY_W/2 - SPK_SEAT_W) - REVEAL  # seat -> edge
CLR_SPK_CRES = CRES_Y - SPK_SEAT_Y1                          # seat -> crescent
CLR_NUB_MIC  = (W/2 - MIC_PCB_W/2) - (SPK_X + SPK_MOUNT_W/2) # nub tip -> array
CLR_NUB_EDGE = (SPK_X - SPK_MOUNT_W/2) - REVEAL              # nub tip -> edge
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
# The rear wall is CROWDED: the UPS stands up the middle to y=97 and the Flex
# board covers the middle from y=102 up. The light pipe has to thread the band
# between them, which is only about 5 mm tall -- hence the small pipe. It stays
# centred in WIDTH as asked; the BH1750 itself sits in front of the UPS (there
# is 31 mm of free depth there) with a short pipe up to the wall.
#
# >>> IF THIS BAND GETS ANY TIGHTER, move the lux to the crown. It is the one
# >>> rear feature with nowhere else to go on this wall.
LP_D, LP_Y      = 3.0, 99.5         # BH1750 light pipe ("lux"), centred
# The Waveshare UPS 3S charges through a DC-005 BARREL JACK, not USB-C. Height
# is set by where the jack lands on the UPS board -- confirm on the as-built.
BARREL_D        = 11.0              # (?) clearance for the DC-005 jack body
BARREL_Y        = 14.0              # (?) jack centre height, centred in width
# Vents: TWO STACKS FLANKING the UPS, not one centred stack. A centred stack
# would sit directly behind the Flex board, which both blocks the slots and
# bakes the board. Out on the flanks they are clear of the Flex envelope AND of
# the UPS, and they sit right above the amp -- which is where the heat is.
VENT_W, VENT_HH = 30.0, 2.5         # rear vent slots
VENT_N, VENT_P  = 4, 7.0            # count, pitch, per stack
VENT_Y          = 62.0              # bottom slot
VENT_X_OFF      = 75.0              # stack centre, either side of W/2

# ---- internals shown for reference ----------------------------------------
# 3S pack, cells STANDING (18.5 dia x 65 long, 3 in a row). Lying flat the pack
# is 65 x 57 in plan, which collides with both speakers AND the matrix tray in
# a 179 x 59 floor -- see note (c). Standing, it tucks against the rear wall.
UPS_W, UPS_D, UPS_H = 57.0, 20.0, 65.0   # (?) 3x 18650 upright + holder
UPS_BACK            = 3.0                # gap from the interior rear wall
FOOT_D, FOOT_IN     = 12.0, 16.0         # rubber feet
SPK_BODY_D          = 22.0               # (?) speaker can depth

# ---- front module: diffuser + cavity + mounts ------------------------------
# DIFF_T / DIFF_REBATE / DIFF_MARGIN / CAV_WALL are defined UP TOP, next to
# BOSS_EDGE -- they have to exist before RIM_MIN can be derived from them.
# Air gap between the acrylic and the LEDs. Too small and you see 48 dots
# through the diffuser; ~0.7x the 16.7 mm LED pitch is the usual rule.
DIFF_GAP    = 12.0                   # (?) TUNE ON A TEST PRINT
LED_STRIP_T = 3.0                    # (?) SK6812 strip + adhesive
TRAY_REBATE = 2.0                    # pocket the matrix tray front face sits in
TRAY_FIT    = 0.20                   # (superseded: the tray is a clearance fit
                                     #  with clips now -- see gen_front_plate)
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

# ReSpeaker Flex core -- MEASURED, no longer a guess.
# The BARE BOARD is 52 x 70 x 20 deep (20 at the XIAO, its tallest point). The
# 3.5 mm jack and the mic-ribbon connector overhang the two SHORT (52 mm) edges,
# so the assembly needs a 110 mm envelope in that direction. Mounted with the
# 52 mm dimension HORIZONTAL: 110 wide (with overhangs) x 70 tall x 20 deep.
#
# It mounts VERTICALLY on the inside of the REAR WALL, above the UPS: that face
# is reachable the moment the front module is out, and it keeps the floor clear.
FLEX_PCB_W = 52.0    # bare board, short edge (horizontal as mounted)
FLEX_PCB_H = 70.0    # bare board, long edge  (vertical as mounted)
FLEX_W     = 110.0   # envelope incl. the jack + ribbon overhangs
FLEX_H     = FLEX_PCB_H
FLEX_D     = 20.0    # deepest point, at the XIAO
# Mounting holes, from the measurement: inside-edge to inside-edge 60 x 42, and
# 2 mm from board edge to the OUTSIDE of each hole. Both axes agree on a 3 mm
# hole -- (52 - 2*2 - 42)/2 = 3 and (70 - 2*2 - 60)/2 = 3 -- so these are M3.
FLEX_HOLE_D    = 3.0
FLEX_HOLE_PX   = 42.0 + FLEX_HOLE_D          # 45.0 centre pitch, across the 52
FLEX_HOLE_PY   = 60.0 + FLEX_HOLE_D          # 63.0 centre pitch, along the 70
FLEX_HOLE_EDGE = 2.0 + FLEX_HOLE_D / 2       # 3.5 board edge -> hole centre
FLEX_BOSS_D    = 7.0                         # standoff boss on the rear wall
FLEX_STANDOFF  = 3.0                         # clears the solder side
# Bottom edge, above the UPS. The rear wall curves in above the springing line,
# so the 110 mm envelope has to fit the ARC at the TOP edge -- checked in
# flex_wall_fit() and in the clearance table.
FLEX_WALL_Y            = 102.0

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


def arc_width(y):
    """Interior width of the shell at height y. Below the springing line the
    flanks are straight; above it they follow the arc and pinch in fast."""
    if y <= ARCH_Y:
        return IN_W
    dy = y - ARCH_Y
    if dy >= ARCH_R:
        return 0.0
    return 2 * ((ARCH_R**2 - dy**2) ** 0.5 - WALL)


def flex_wall_fit():
    """Does the 110 mm Flex envelope fit the rear wall where we put it?
    The TOP edge is the binding case -- that is where the arc is narrowest.
    Returns (available_width_at_top, needed, slack)."""
    avail = arc_width(FLEX_WALL_Y + FLEX_H)
    return avail, FLEX_W, avail - FLEX_W


def flex_holes():
    """The four M3 mounting holes, as (x, y) on the rear wall, centred in
    width. Pitch 45 x 63 from the measured 42 x 60 inside-edge spacing."""
    return [(W/2 + sx * FLEX_HOLE_PX/2,
             FLEX_WALL_Y + FLEX_H/2 + sy * FLEX_HOLE_PY/2)
            for sx in (-1, 1) for sy in (-1, 1)]


def spk_nubs():
    """Speaker side-mount nubs, as (x, y) in the FRONT view -- one per flank of
    each body, centred on the 45 mm side. The screw runs front-to-back into a
    post on the front module standing SPK_NUB_Z proud of its back face."""
    o = []
    for cx in (SPK_X, W - SPK_X):
        for sgn in (-1, 1):
            o.append((cx + sgn * (SPK_BODY_W/2 + SPK_NUB_PROJ/2), SPK_NUB_Y))
    return o


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
def crescent_row_ys(n_rows=None):
    """LED-row CENTRE heights above the baseline, at the FIXED LED_ROW_PITCH.

    Rows stack up from the baseline at a real spacing instead of being stretched
    to land exactly on the apex. The row count therefore falls out of the
    radius, and LED_R was solved so that count carries 48 px at a decent fill.
    """
    y0, apex = LED_D / 2, LED_R - LED_D / 2
    ys, y = [], y0
    while y <= apex + 1e-9:
        ys.append(y)
        y += LED_ROW_PITCH
    if not ys:
        ys = [y0]
    if n_rows is not None:
        ys = ys[:n_rows] if n_rows <= len(ys) else ys
    return ys


def _crescent_row_cap(y, apex=False):
    """Most pixels that fit in the row at height y, keeping the outer pixel
    LED_D/2 clear of the arc (so the whole body stays inside the box)."""
    usable = 2 * (max(LED_R**2 - y**2, 0.0) ** 0.5 - LED_D / 2)
    return max(int(usable // LED_PITCH) + 1, 1)


def crescent_rows():
    """Lay exactly CRES_PX pixels onto the derived crescent radius.

    Both spacings are now fixed -- LED_PITCH along a row, LED_ROW_PITCH between
    rows -- so the row count falls out of LED_R and the only free variable left
    is how many pixels go in each row.

    ALLOCATION IS CONSTANT-MARGIN, not proportional. Proportional-to-capacity
    looks reasonable in a table and bad on the part: it lets one row run out to
    within 3 mm of the arc while its neighbours stop 18 mm short, so the lit
    field bulges. Instead, solve for the single end margin M that spends exactly
    CRES_PX pixels when every row is filled out to M from the arc. The outer
    pixels then trace a curve concentric with the crescent, which is what makes
    it read as a crescent rather than a stack of rows.

    Returns (chord_width, count, strip_run) per row, bottom-first. chord_width
    is the true geometric chord at the (inset) row centre, so crescent_leds()
    recovers the same row height from it.
    """
    ys = crescent_row_ys()
    n_rows = len(ys)
    cap = [_crescent_row_cap(y) for y in ys]
    chord = [2 * max(LED_R**2 - y**2, 0.0) ** 0.5 for y in ys]

    def at_margin(m):
        return [min(max(int((c - 2*m) // LED_PITCH) + 1, 0), k)
                for c, k in zip(chord, cap)]

    # bisect the margin: bigger M -> fewer pixels, monotonically
    lo, hi = 0.0, LED_R
    for _ in range(60):
        mid = (lo + hi) / 2
        if sum(at_margin(mid)) > CRES_PX:
            lo = mid
        else:
            hi = mid
    cnt = at_margin(hi)

    # the margin lands between integers, so a few pixels are usually left over.
    # Spend them on whichever row currently reaches least far out.
    short = CRES_PX - sum(cnt)
    while short > 0:
        cand = [i for i in range(n_rows) if cnt[i] < cap[i]]
        if not cand:
            break
        i = max(cand, key=lambda j: chord[j] - cnt[j] * LED_PITCH)
        cnt[i] += 1
        short -= 1
    rows = []
    for i in range(n_rows):
        chord = 2 * max(LED_R**2 - ys[i]**2, 0.0) ** 0.5
        rows.append((chord, cnt[i], max(cnt[i] - 1, 0) * LED_PITCH))
    return rows


def crescent_px():
    return sum(c for _, c, _ in crescent_rows())


def crescent_leds():
    """The LED positions, laid out on the crescent (indicative)."""
    o = []
    for w, k, run in crescent_rows():
        ry = (LED_R**2 - (w/2)**2) ** 0.5
        for i in range(k):
            x = W/2 - run/2 + i * LED_PITCH if k > 1 else W/2
            o.append(circ(x, fy(CRES_Y + ry), LED_D, "led"))
    return o


def mic_x():
    return [W/2 + (i - (MIC_N-1)/2) * MIC_PITCH for i in range(MIC_N)]


def vent_y(i):
    return VENT_Y + i * VENT_P


def vent_x():
    """Centre x of each vent stack -- one either side of the UPS."""
    return [W/2 - VENT_X_OFF, W/2 + VENT_X_OFF]


def rear_wall_items():
    """Everything competing for the REAR WALL, as (name, x0, x1, y0, y1).
    Two features clear each other if they clear in EITHER axis."""
    o = [("UPS 3S",   W/2 - UPS_W/2,  W/2 + UPS_W/2,  FLOOR_Y, FLOOR_Y + UPS_H),
         ("Flex",     W/2 - FLEX_W/2, W/2 + FLEX_W/2,
          FLEX_WALL_Y, FLEX_WALL_Y + FLEX_H),
         ("lux pipe", W/2 - LP_D/2,   W/2 + LP_D/2,   LP_Y - LP_D/2, LP_Y + LP_D/2),
         ("amp",      AMP_WALL_X - AMP_W/2, AMP_WALL_X + AMP_W/2,
          AMP_WALL_Y - AMP_D/2, AMP_WALL_Y + AMP_D/2),
         ("barrel jack", W/2 - BARREL_D/2, W/2 + BARREL_D/2,
          BARREL_Y - BARREL_D/2, BARREL_Y + BARREL_D/2)]
    for k, vx in enumerate(vent_x()):
        o.append((f"vent stack {'LR'[k]}", vx - VENT_W/2, vx + VENT_W/2,
                  vent_y(0) - VENT_HH/2, vent_y(VENT_N - 1) + VENT_HH/2))
    return o


def rear_wall_clearances():
    """Pairwise clearance on the rear wall. The barrel jack is EXPECTED to sit
    inside the UPS footprint -- the jack is on that board -- so that pair is
    skipped rather than reported as a collision."""
    items, out = rear_wall_items(), []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, b = items[i], items[j]
            if {a[0], b[0]} == {"UPS 3S", "barrel jack"}:
                continue
            gap = max(gap_1d(a[1], a[2], b[1], b[2]),
                      gap_1d(a[3], a[4], b[3], b[4]))
            out.append((f"{a[0]} <-> {b[0]}", gap))
    return out


