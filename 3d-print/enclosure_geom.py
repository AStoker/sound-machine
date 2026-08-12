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
import os

from drawlib import n, rect, circ, line

# ---- output layout ---------------------------------------------------------
# Printable solids go in models/, drawings and cut files stay beside the code.
# One definition, imported by every generator -- the alternative is six copies of
# an os.path.join and a slow drift into three different output directories.
HERE      = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(HERE, "models")
os.makedirs(MODEL_DIR, exist_ok=True)

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
# >>> 64 -> 79, BECAUSE THE SPEAKERS WERE INSIDE THE BATTERY. Andy fitted it and
# >>> found the cans overlapping the UPS pack by about 3 mm. That observation pins
# >>> the STACK even though it cannot say which half of it was wrong:
# >>>     (FP_T + can) + pack  =  D - WALL + 3  =  64.5
# >>> against the 50.0 the two guesses claimed. 14.5 mm of speaker-plus-battery
# >>> that the model did not know about. +15 clears it with 9 mm to spare.
# >>>
# >>> D IS CHOSEN, BUT IT IS NO LONGER UNCHECKED. See depth_stacks() at the bottom
# >>> of this file: the machine is a shallow box with things mounted on BOTH faces,
# >>> and until now nothing tested whether a front-mounted part and a rear-mounted
# >>> part could occupy the same millimetre. The speakers and the UPS pack do.
D         = 79.0
WALL      = 2.5      # dome wall
# THE CROWN IS A FLATTENED ARCH, NOT A SEMICIRCLE.
# A true "D" has H = CRES_Y + W/2 -- the arch height is locked to half the width
# and nothing else can touch it. Once the width came down to 202 (see the
# speaker note below) that made the front nearly square, 1.07:1, against the
# 1.36:1 it started as. Flattening the crown is the ONLY lever on height, so the
# arch is now a half-ELLIPSE: horizontal semi-axis W/2, vertical CROWN_K x W/2.
#
# It is also not purely a looks number: it sets how much crescent there is to
# lay LEDs on. 0.70 held exactly 48 px with the strip rows edge to edge; 0.72
# bought a sixth row.
#
# >>> 0.72 WAS NOT ENOUGH. Measured as a true distance to the ellipse rather
# >>> than by chord and apex, the top LED body at 0.72 sat 0.58 mm OUTSIDE the
# >>> diffuser -- the old checks missed it because they measure horizontally and
# >>> vertically, and the binding case on an ellipse is diagonal. Dropping the
# >>> mic array (see MIC_Y0) freed 6.35 mm of height; 0.74 spends 2.02 of it on
# >>> the crescent, which turns that -0.58 into +2.1 mm of real clearance, and
# >>> banks the other 4.33 as a shorter shell. Front aspect goes 1.26:1 ->
# >>> 1.31:1. The margin is reported as CRES_CLR at the bottom of the run --
# >>> keep it positive.
CROWN_K   = 0.74
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
# >>> THE POCKET OVERSIZE IS ALSO THE RETAINING LEDGE, and it is set as large as
# >>> the shell allows FOR FREE. The acrylic has to be notched to clear the
# >>> carrier pads on its way in (it passes through them to reach the pocket), and
# >>> the ledge is what hides those notches from the front. Every extra mm of
# >>> ledge is a mm less notch on show.
# >>> 2.4, not 1.5, because RIM_MIN = REVEAL + BOSS_EDGE + DIFF_MARGIN + CAV_WALL
# >>> = 3.6 + 4 + 2.4 + 2 = 12.0, which is exactly RIM_MIN_LOOK -- so the pocket
# >>> grows outward into the rim's spare 0.9 and the LIT CRESCENT DOES NOT SHRINK.
# >>> Beyond this it costs pixels: pulling the aperture in to hide the notch
# >>> completely needs 5 mm and takes the crescent from 48 px to 40. Not worth it
# >>> for six 2.9 mm nicks behind opal acrylic and grille cloth.
DIFF_MARGIN = 2.4                    # pocket oversize = the retaining ledge
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
# >>> VERBATIM FROM ADAFRUIT'S BOARD FILE -- IN *BOARD* COORDINATES. Copied out of
# >>> the <plain> section of "Adafruit IS31FL3731 CharliePlex Grid.brd":
# >>>     <hole x="1.905"  y="26.035" drill="2"/>
# >>>     <hole x="41.275" y="1.905"  drill="2"/>
# >>> (the same file's outline wires give 43.18 x 27.94 with R2.54 corners, which
# >>> is where MTX_BOARD_W/H come from).
MTX_HOLES_BOARD = [(1.905, 26.035), (41.275, 1.905)]

# >>> AND THEY MUST BE FLIPPED TO GET INTO PART COORDINATES. This is the step that
# >>> was missed, twice, in opposite directions.
# >>>
# >>> EAGLE's frame is the board seen from its COMPONENT side -- the LED side. The
# >>> board is installed with the LEDs facing the machine's FRONT, so its
# >>> component-side normal points at -z while part z runs front-to-back. The two
# >>> frames are 180 deg apart, and a 180 deg rotation inverts exactly one in-plane
# >>> axis. Reading the EAGLE numbers straight into part coordinates skips that
# >>> inversion and mirrors the pattern.
# >>>
# >>> It does not matter WHICH axis you invert -- rotating about x or about y are
# >>> both physically valid ways to put the board in, they differ by a spin in the
# >>> board's own plane, and a DIAGONAL pair is symmetric under that spin. Both
# >>> give {(1.905, 1.905), (41.275, 26.035)}: bottom-left + top-right.
# >>>
# >>> HISTORY, BECAUSE IT COST TWO WRONG PARTS. The original value was the mirrored
# >>> one. It was corrected on a report from the bench -- correctly -- and then
# >>> "corrected back" when the vendor file turned up, on the reasoning that the
# >>> vendor must outrank an eyeball. The vendor file was right; the reasoning was
# >>> not. Authoritative data still has to be transformed into the frame you are
# >>> using it in, and someone holding the printed part is measuring the frame you
# >>> actually shipped. The flip is applied in code now, so the source stays
# >>> quotable and the transform is visible.
MTX_HOLES = [(hx, MTX_BOARD_H - hy) for hx, hy in MTX_HOLES_BOARD]
MTX_HOLE_D  = 2.0
# ---- the LED grid, for per-pixel windows -----------------------------------
# >>> FROM THE SAME BOARD FILE. 16 x 9 on a 2.54 pitch, first LED centre at
# >>> (2.413, 3.683) board-local. Same board->part flip as the holes: the grid is
# >>> NOT symmetric about the board's mid-height (3.683 from one edge, 3.937 from
# >>> the other), so skipping the flip shifts every window by 0.254 mm.
MTX_LED_COLS, MTX_LED_ROWS = 16, 9
MTX_LED_PITCH = 2.54
MTX_LED_X0, MTX_LED_Y0 = 2.413, 3.683      # board-local, component side
# >>> SQUARE WINDOWS, NOT ROUND. A 1.8 mm square slices cleanly at any nozzle
# >>> width; a Ø1.8 circle gets approximated and the webs between neighbours end
# >>> up over- or under-extruded. Square also passes more light for the same web.
# >>> 2.54 pitch - 1.8 window leaves 0.74 mm of web, which is two 0.4 lines minus
# >>> a whisker. Going to 2.0 would leave 0.54 and force single-extrusion webs.
MTX_WINDOW = 1.8


def mtx_led_xy(board_x0, tray_y0, n_boards=None):
    """Every LED centre in PART coordinates, for the whole butted pair."""
    n = MTX_N if n_boards is None else n_boards
    out = []
    for b in range(n):
        bx = board_x0 + b * MTX_BOARD_W
        for i in range(MTX_LED_COLS):
            for j in range(MTX_LED_ROWS):
                lx = MTX_LED_X0 + i * MTX_LED_PITCH
                ly = MTX_LED_Y0 + j * MTX_LED_PITCH
                out.append((bx + lx, tray_y0 + (MTX_BOARD_H - ly)))
    return out


# ---- the DRIVER ("backpack") board -----------------------------------------
# >>> FROM ADAFRUIT'S FAB PRINT, cross-checked against the .brd. The fab print
# >>> dimensions the hole pattern as 1.5" x 0.9" inside a 1.7" x 1.1" board, i.e.
# >>> 0.1" = 2.54 mm in from every edge; the board file's own dimension objects
# >>> agree (38.10 across, 22.73 up) and its library carries the package
# >>> MOUNTINGHOLE_2.5_PLATED -> <pad drill="2.5" diameter="3.2"/>.
# >>> So: FOUR holes, M2.5, one near each corner.
MTX_BP_HOLES_BOARD = [(2.54, 2.54), (2.54, 25.4), (40.64, 2.54), (40.64, 25.4)]
# same board-to-part flip as the matrix. It happens to be a no-op here -- this
# pattern is symmetric about the board's mid-height -- but it is applied anyway,
# because a pattern that is symmetric today is not necessarily symmetric after
# the next edit, and a silently-skipped transform is what caused the trouble.
MTX_BP_HOLES = [(hx, MTX_BOARD_H - hy) for hx, hy in MTX_BP_HOLES_BOARD]
MTX_BP_HOLE_D = 2.5                  # plated, 3.2 pad
MTX_BP_HOLE_PITCH = (38.10, 22.86)   # 1.5" x 0.9"
# >>> AND THEY DO NOT LINE UP WITH THE MATRIX'S. The matrix is drilled 1.905 mm
# >>> (0.075") in from its edges, the driver 2.54 mm (0.100"), so the closest a
# >>> driver hole ever gets to a matrix hole is 0.898 mm -- and the other two
# >>> driver holes are 23.5 mm from anything. This is the fact that decides the
# >>> architecture: a post rising from the front plate to a driver hole has to
# >>> pass through the MATRIX, which sits in front of it and has no hole there.
# >>> The driver therefore cannot be screwed down to the plate through the stack;
# >>> it has to be held from BEHIND. See the note in gen_front_plate.
# ---- inter-board sockets (the press-in scheme) ------------------------------
# >>> MTX_SOCKET_H WAS DELETED, along with the question it asked. It existed for
# >>> the "solder female headers to the backpack and press the matrix in" scheme,
# >>> which lost to the clip design and was never built. It was still sitting in
# >>> MEASURE-ME as a blocking measurement for a part that does not exist.
MTX_PCB_T   = 1.6                    # matrix thickness
MTX_BP_T    = 1.6                    # driver backpack thickness
# >>> THE STACK HEIGHT IS MEASURED; THE HEADER GAP IS DERIVED FROM IT. It was the
# >>> other way round -- a guessed 5.0 mm header gap, with the overall height
# >>> falling out at 8.2. Measured front-of-matrix to back-of-backpack is 7.0, so
# >>> the gap is really 3.8 and the assumption was 1.2 mm out.
# >>> That 1.2 mm mattered more than anything else here: the front module's six
# >>> retaining clips hook at the BACK OF THIS STACK, so a stack 1.2 mm shorter
# >>> than modelled leaves the boards loose behind hooks they never reach. Record
# >>> the number that was actually measured, not the one that is convenient.
MTX_STACK_H = 7.0                    # MEASURED: matrix front -> backpack back
MTX_STACK_GAP = MTX_STACK_H - MTX_PCB_T - MTX_BP_T   # = 3.8, the header gap
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
LED_PITCH = 16.5     # MEASURED, cut line to cut line. Was 16.7 from the nominal
                     #   60 LED/m figure; the real strip is 16.5.
# >>> CRES_PX IS AN OUTCOME NOW, NOT AN INPUT. It used to be "FIXED -- this is
# >>> the strip you have", on the assumption that 48 px would always be made to
# >>> fit by re-solving the rows. That assumption held only because every check
# >>> measured the LED BODY. The thing that actually has to fit the cavity is
# >>> the RIBBON: a segment of n pixels is n x LED_PITCH long, because the cut
# >>> lines sit half a pitch outboard of the end LEDs and you cannot trim past
# >>> them without losing the solder pads. On the bottom row that ribbon is
# >>> 6.9 mm longer than the LED span, and it did not fit.
# >>> With the rows BUTTING (pitch 10.0 = STRIP_W) the crescent holds exactly 48
# >>> at CROWN_K 0.74. It held only 45 while the pitch carried a 1 mm gap, and
# >>> recovering 48 that way would have needed CROWN_K 0.80 -- a taller shell.
# >>> Closing the row gap was free.
# >>> See crescent_capacity_note() and the ribbon cap in _crescent_row_cap().
CRES_PX   = 48       # DERIVED from the cavity -- see above. The whole reel fits
                     #   again now the rows butt; at an 11.0 pitch it was 45.
LED_D     = 5.2      # SK6812 package, drawn indicatively
STRIP_W   = 10.0     # MEASURED. Ribbon width. Two jobs: it floors the ROW pitch
                     #   and, being wider than the LED, it is what reaches the
                     #   cavity wall first.
# >>> ROWS BUTT. The pitch floor is STRIP_W exactly, not STRIP_W + 1 -- adjacent
# >>> ribbons are allowed to touch edge to edge. The old 1 mm gap was pure
# >>> caution and it cost three pixels: at an 11.0 pitch the crescent holds 45,
# >>> at 10.0 it holds 48, which is the whole reel, on the same shell height.
# >>> There is no manufacturing slack left in the row direction, so if the tape
# >>> measures over 10.0 the rows overlap -- STRIP_W is the number to re-measure
# >>> if the layout ever looks wrong.
STRIP_ROW_GAP = 0.0  # designed gap between adjacent ribbons
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
#   LED_R   the arc the pixels are laid out on. Smaller, sized so the strip
#           actually fills its rows at a sane density.
#
# The band between them is UNLIT ON PURPOSE. Trying to light the diffuser right
# out to its edge with so few pixels means spreading them thin; letting the
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
# >>> THE SPEAKERS ARE ROTATED 90 DEGREES. The box is 50 x 45 with a nub in the
# >>> centre of each of the two 45 mm faces. Standing it on its side puts those
# >>> nubs TOP AND BOTTOM instead of left and right, which takes the mounting
# >>> post out of the WIDTH chain and puts it in the height -- where there is
# >>> slack. It also narrows the body from 50 to 45. Between them that is 46 mm
# >>> off the width, which is what lets the dome and the front module each print
# >>> as ONE PIECE on a 220 bed. Acoustically it is free: a sealed box with a
# >>> round driver does not care which way up it is.
SPK_BODY_W = 45.0    # body width  as mounted (the datasheet's 45 mm face)
SPK_BODY_H = 50.0    # body height as mounted (the datasheet's 50 mm face)
SPK_BODY_D = 22.0    # body depth  -- datasheet
SPK_GRILLE = 40.0    # (?) open cone diameter, inside the 45 body height
SPK_RING_W = 3.0     # VESTIGIAL. Was a raised baffle seat around each body,
                     #   from the pre-rotation mount. There is no seat ring now:
                     #   the flanks are bare and the body is held by two screws
                     #   top and bottom. Kept only so old drawings still import;
                     #   nothing in the built geometry reads it. Do not size
                     #   anything from it -- use SPK_POST_W / SPK_POST_H_Y.
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
SPK_NUB_PROJ = 4.0   # CONFIRMED on a test print -- "the speaker nubs are perfect"
SPK_NUB_W    = 8.0   # CONFIRMED, same print
SPK_NUB_H    = 6.0   # CONFIRMED, same print
SPK_NUB_SCREW = 3.0  # CONFIRMED, same print
SPK_POST_WALL = 2.0  # material outboard of the screw, in the module post
SPK_FIT       = 0.35 # per side, body to its locating rib / post
# The nub+post budget. With the speaker rotated this is spent VERTICALLY, above
# and below the body, instead of on the flanks. SPK_FIT is in here because the
# post sits OUTSIDE the fit gap, not inside it.
SPK_POST_H = SPK_FIT + SPK_NUB_PROJ + SPK_POST_WALL
# The post's own two dimensions, now that it stands above/below the body rather
# than beside it. Both are set BY THE NUB, not by the body: SPK_NUB_H is the
# nub's 6 mm dimension, which ran up the 45 mm side before the rotation and runs
# ACROSS, in x, after it.
#
# >>> THIS IS WHAT LETS THE MIC ARRAY COME DOWN. The post is 10 mm wide on the
# >>> speaker's CENTRELINE (x = 31.1 and 170.9); the 110 mm mic PCB spans
# >>> x = 46..156. They never meet, so the array only has to clear the speaker
# >>> BODY in y, not the post -- which is the whole 6.35 mm. Scaling the post
# >>> off the body instead (0.60 x 45 = 27 wide) would reach x = 44.6 and give
# >>> that saving straight back. See CLR_POST_MIC.
SPK_POST_W   = SPK_NUB_H + 2 * SPK_POST_WALL     # across, in x
SPK_POST_H_Y = SPK_NUB_PROJ + SPK_POST_WALL      # up, in y
# The flanks now only need clearance to slide the box in: the two screws (top
# and bottom) fully locate it in x, y and rotation, so no side ribs. That is the
# whole saving -- SPK_SEAT_W used to be 6.35 per flank.
SPK_FLANK  = 1.0
SPK_SEAT_W = SPK_FLANK            # what the WIDTH chain spends per flank
SPK_MOUNT_H = SPK_BODY_H + 2 * SPK_NUB_PROJ      # tallest point, nubs included
SPK_MOUNT_W = SPK_BODY_W                         # the flanks are now plain
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
# >>> THE BAFFLE FLOOR IS DRAFTED, NOT DROPPED. Row 0's ribbon hangs 2.4 mm below
# >>> the crescent baseline and ran straight into the bar that closes the bottom of
# >>> the cavity -- 703 mm^3 of interference. Lowering that bar bodily would push it
# >>> into the mic array, which sits directly beneath. So the floor stays at the
# >>> baseline where the mic is (at the FACADE) and slopes outward as it goes back
# >>> toward the LED carrier, where there is nothing below to hit. The mic channel
# >>> ends at z=5.0 and the ramp starts at 4.7, so it sees 0.06 mm of the drop.
BAFFLE_DROP = 3.0    # how far the floor falls by the time it reaches the carrier

FLOOR_Y  = BP_T                              # top face of the bottom plate
# THE SPEAKERS come first now: with the nubs rotated to top and bottom, their
# posts are what the vertical stack has to carry, and they are what the mic
# array has to clear.
SPK_SEAT_Y0 = FLOOR_Y + SPK_CLR              # bottom of the lower post
SPK_Y0      = SPK_SEAT_Y0 + SPK_POST_H
SPK_Y1      = SPK_Y0 + SPK_BODY_H
SPK_SEAT_Y1 = SPK_Y1 + SPK_POST_H            # top of the upper post
SPK_NUB_Y_LO = SPK_Y0 - SPK_NUB_PROJ/2       # nub centres, below and above
SPK_NUB_Y_HI = SPK_Y1 + SPK_NUB_PROJ/2
# THE MIC ARRAY sits ABOVE the speakers, not between them. That is the other
# half of the width saving: its 110 mm no longer has to fit between two driver
# boxes, so the middle of the facade only has to hold the 86 mm matrix pair.
# The cost is height, and the flattened crown pays it back with interest.
#
# >>> IT CLEARS THE BODY, NOT THE POST. This used to sit on SPK_SEAT_Y1 -- the
# >>> top of the nub post -- which lifted it a further SPK_POST_H = 6.35 for no
# >>> reason. The post is only SPK_POST_W = 10 mm wide and it stands on the
# >>> speaker's CENTRELINE, at x = 31.1 and 170.9. The mic PCB is 110 mm centred,
# >>> x = 46..156. The two overlap in y and never in x, so the array only has to
# >>> clear the speaker BODY. That is the 6.35 mm; CROWN_K spends 2.02 of it on
# >>> LED clearance and the shell keeps the other 4.33.
# >>> The x clearance this rests on is CLR_POST_MIC -- if that ever goes
# >>> negative this reverts to SPK_SEAT_Y1.
MIC_Y0   = SPK_Y1 + SPK_MIC_GAP
MIC_Y1   = MIC_Y0 + MIC_PCB_H
# THE CLOCK is flanked by the speakers, centred on them -- with the array gone
# from this band there is no reason to keep it hard down on the floor, and
# centring it reads better against the drivers either side.
TRAY_Y0  = (SPK_Y0 + SPK_Y1)/2 - TRAY_H/2
TRAY_Y1  = TRAY_Y0 + TRAY_H
# CRES_Y is the LED ROW CENTRE, so the bottom row hangs LED_D/2 below it.
CRES_Y   = max(MIC_Y1, SPK_SEAT_Y1) + GAP_CRES + LED_D/2
ARCH_Y   = CRES_Y                            # concentric: same centre

# W: edge | boss keep-out | clr | speaker body | clr | gap | half the MATRIX.
# With the array lifted clear, the matrix pair (86) sets the middle instead of
# the array (110), and the flanks cost 1.0 of clearance instead of a 6.35 post.
W_FROM_SPK  = 2 * (REVEAL + BOSS_EDGE + SPK_FLANK + SPK_BODY_W + SPK_FLANK
                   + SPK_MIC_GAP + TRAY_W/2)
# ...but the array still has to fit the shell somewhere, so it sets a floor.
W_FROM_MIC  = 2 * (REVEAL + BOSS_EDGE + MIC_PCB_W/2)
W_FROM_TRAY = W_FROM_SPK
W        = 2 * math.ceil(max(W_FROM_SPK, W_FROM_MIC) / 2)    # <<< DERIVED width

# The crown is a half-ELLIPSE (see CROWN_K): ARCH_R across, ARCH_RY up.
ARCH_R   = W/2                               # horizontal semi-axis
ARCH_RY  = CROWN_K * ARCH_R                  # vertical semi-axis
H        = ARCH_Y + ARCH_RY                  # <<< DERIVED height

# The diffuser is the same ellipse, inset by the rim on both axes.
CRES_R   = ARCH_R - RIM_MIN                  # diffuser, horizontal semi-axis
CRES_RY  = ARCH_RY - RIM_MIN                 # diffuser, vertical semi-axis
CRES_RIM = RIM_MIN


def ell_half_chord(y, a=None, b=None):
    """Half-width of the crescent ellipse at height y above its baseline."""
    a = CRES_R if a is None else a
    b = CRES_RY if b is None else b
    return a * max(1.0 - (y/b)**2, 0.0) ** 0.5


def cres_capacity(pitch, a=None, b=None):
    """How many pixels the crescent holds at a given ROW pitch. Returns
    (total, per-row list).

    >>> BOTH LIMITS, NOT JUST THE OPTICAL ONE. This used to count how many LED
    >>> BODIES fitted inside the chord, which overstates it -- the ribbon is a
    >>> full LED_PITCH longer than the span between its end pixels, and that is
    >>> what has to fit the cavity. Defined below _crescent_row_cap so it can
    >>> reuse it; the a/b arguments are kept for callers that probe a
    >>> hypothetical crescent."""
    if a is None and b is None:
        return (lambda c: (sum(c), c))([_crescent_row_cap(y)
                                        for y in _row_ys_at(pitch)])
    a = CRES_R if a is None else a
    b = CRES_RY if b is None else b
    caps, y = [], LED_D / 2
    while y <= b - LED_D/2 + 1e-9:
        usable = 2 * (ell_half_chord(y, a, b) - LED_D/2)
        caps.append(max(int(usable // LED_PITCH) + 1, 1))
        y += pitch
    return (sum(caps) if caps else 0), (caps or [0])


# How full the crescent may be. NOT the same knob as the old fade band -- there
# is no fade now. This is manufacturing slack: at 100% every row is filled to
# its exact geometric limit, so any tolerance slip pushes an LED out past the
# diffuser. Leaving ~8% spare means each row can lose a pixel and still look
# right.
CRES_FILL_TARGET = 0.92


def _row_ys_at(pitch, b=None):
    b = CRES_RY if b is None else b
    ys, y = [], LED_D / 2
    while y <= b - LED_D / 2 + 1e-9:
        ys.append(y)
        y += pitch
    return ys or [LED_D / 2]


def _solve_row_pitch():
    """The row pitch that gets the MOST pixels onto the crescent, largest wins
    on a tie.

    On the flattened crown the pitch is not ours to pick freely: the crescent is
    short, so the pitch is whatever gets the pixels on. The floor is STRIP_W + 1
    -- the strip is a physical ribbon and rows any closer overlap.

    >>> IT MAXIMISES CAPACITY, IT DOES NOT STOP AT A TARGET. The old version
    >>> walked the pitch down and returned the first one whose capacity beat
    >>> CRES_PX/CRES_FILL_TARGET, using a CHORD-based capacity that ignored the
    >>> ribbon. Once the ribbon cap went in, that measure still reported enough
    >>> room at 11.5 while the real layout only held 42 -- so it stopped early
    >>> and threw away three pixels. Capacity here is the true per-row cap, both
    >>> limits applied.
    """
    lo = STRIP_W + STRIP_ROW_GAP
    best, best_p = -1, lo
    p = LED_PITCH
    while p >= lo - 1e-9:
        tot = sum(_crescent_row_cap(y) for y in _row_ys_at(round(p, 1)))
        if tot > best:                       # strictly >, so ties keep the
            best, best_p = tot, round(p, 1)  #   LARGER pitch found first
        p -= 0.1
    return best_p


# LED_ROW_PITCH is resolved at the BOTTOM of this file, not here: the pitch
# solver now measures true capacity, which needs ell_dist / ribbon_cap /
# _crescent_row_cap -- all defined further down. Anything above that point
# must not read LED_ROW_PITCH at import time.
LED_ROW_PITCH = None
# The LED field IS the diffuser ellipse -- no fade band. At this size the px
# fill it about 92%, so the glow reaches the edge instead of dying out early.
LED_R    = CRES_R
LED_RY   = CRES_RY
CRES_FADE = 0.0

CLK_Y    = (TRAY_Y0 + TRAY_Y1) / 2
MIC_Y    = (MIC_Y0 + MIC_Y1) / 2
SPK_X    = REVEAL + BOSS_EDGE + SPK_FLANK + SPK_BODY_W/2   # body centre
SPK_Y    = (SPK_Y0 + SPK_Y1) / 2
SPK_NUB_Y = SPK_Y                            # (kept: the drawings ask for one)

# Clearances the stack cannot enforce (all checked at the bottom of the run):
CLR_SPK_TRAY = (W/2 - TRAY_W/2) - (SPK_X + SPK_BODY_W/2)     # body -> matrix
CLR_SPK_MIC  = MIC_Y0 - SPK_Y1                               # BODY -> array, y
CLR_SPK_EDGE = (SPK_X - SPK_BODY_W/2 - SPK_FLANK) - REVEAL   # body -> edge
CLR_SPK_CRES = CRES_Y - SPK_SEAT_Y1                          # post -> crescent
CLR_NUB_EDGE = (SPK_X - SPK_BODY_W/2) - (REVEAL + BOSS_EDGE)
# >>> THE NUB CHECK IS AN X CHECK NOW, NOT A Y CHECK. It used to be
# >>> MIC_Y0 - SPK_SEAT_Y1: the array had to sit above the post. It does not any
# >>> more -- it passes BESIDE it -- so the meaningful clearance is horizontal.
# >>> Defined just below as CLR_POST_MIC; aliased here so the drawings keep
# >>> reporting a "nub -> mic array" line, but reporting the right one.
# >>> THE ONE THAT PAYS FOR THE LOWERED MIC ARRAY. The upper nub post and the
# >>> mic PCB now overlap in y on purpose; this is the x gap that makes that
# >>> safe. Negative means the post is fouling the array and MIC_Y0 has to go
# >>> back to clearing SPK_SEAT_Y1.
CLR_POST_MIC = (W/2 - MIC_PCB_W/2) - (SPK_X + SPK_POST_W/2)
CLR_NUB_MIC  = CLR_POST_MIC
# Does the post actually overlap the array in y? If not, CLR_POST_MIC is moot.
POST_MIC_Y_OVERLAP = min(SPK_SEAT_Y1, MIC_Y1) - max(SPK_Y1 + SPK_FIT, MIC_Y0)
SPK_W_MAX    = W/2 - TRAY_W/2 - REVEAL - BOSS_EDGE - 2*SPK_FLANK

# ---- top surface controls --------------------------------------------------
# The knob is PART 5: a printed pebble that caps the seesaw encoder shaft. It
# seats on a flat boss milled into the cylindrical crown, on the top ridge.
ENC_SHAFT_D = 7.0    # clearance bore through the shell for the encoder shaft
# >>> ENC_Y IS DEFINED FURTHER DOWN NOW, next to CARRIER_Z0, because it is
# >>> DERIVED FROM IT. It was 30.0 by hand, chosen before the crescent baffle
# >>> existed; the baffle now reaches CARRIER_Z0 into the dome and the encoder's
# >>> 25.4 mm board started at depth 17.3 -- 77.8 mm^3 of it inside the front
# >>> module, with the ToF 55.4 mm^3 in beside it. See CROWN_Z.
ENC_PCB     = 25.4   # Adafruit #4991, 1.0" square -- CONFIRMED, see QT_PCB_SRC
# >>> THE ENCODER BODY IS TALLER THAN THE BARE STANDOFF ALLOWED FOR. The board hangs
# >>> under the crown and the encoder can sits BETWEEN the two, so the standoff has
# >>> to be the can's height, not a generic spacer. +5 over STANDOFF_H, measured off
# >>> the real part. The ToF keeps its own TOF_STAND -- it has nothing on that face.
ENC_STAND   = 8.0    # = STANDOFF_H + 5.0, for the encoder can under the board
# The knob is a FULL pebble: an ellipse of revolution truncated by a shallow cut
# at the bottom, so only a small flat meets the crown. KNOB_BASE_D sets how much
# of the pebble is cut away -- closer to KNOB_D = more of a hemisphere.
KNOB_D      = 34.0   # widest diameter (occurs part-way up, not at the base)
# >>> THE KNOB GREW BECAUSE THE BORE DID. A 20 mm blind bore in a 20 mm pebble
# >>> leaves 0.5 mm of cap over the shaft -- the one surface you look down at. The
# >>> cap is measured on the axis (apex minus bore top), so the height is the bore
# >>> plus a cap, and KNOB_CAP_MIN says how much cap counts as a cap.
KNOB_CAP_MIN = 3.0   # material over the top of the blind bore, on the axis
# >>> BACK TO 20.0. It went to 23 only to keep a cap over a 20 mm blind bore. The
# >>> bore is now sized to the SHAFT rather than guessed, and the shaft is 12 mm,
# >>> so the reason for the extra 3 mm is gone and the pebble returns to the
# >>> proportion it was designed with.
KNOB_H      = 20.0   # total height above the boss
KNOB_BASE_D = 28.0   # diameter of the flat where it meets the crown
KNOB_BORE_D = 6.0    # (?) encoder shaft -- Adafruit seesaw is a 6 mm D-shaft
KNOB_BORE_F = 4.5    # (?) across the D-flat
# >>> THE SHAFT IS TWO DIFFERENT THINGS AND THE BORE HAS TO BE TOO. MEASURED:
# >>> 12 mm of shaft stands above the dome, and only the TOP 5 mm of it is
# >>> D-flatted. The 7 mm below that is the round threaded bushing -- with the nut
# >>> on it. A single Ø6.2 bore therefore lands on the bushing and holds the knob
# >>> 7 mm proud, which is what "not flush" was.
# >>>
# >>> So: a wide counterbore for the round part, then the D-bore above it, and the
# >>> knob drops until its base meets the dome. The previous recess was 3.5 deep --
# >>> sized for the NUT alone, when the nut is only the bottom 3 mm of a 7 mm
# >>> obstruction.
KNOB_SHAFT_H  = 12.0   # MEASURED, dome surface to the top of the shaft
KNOB_D_LEN    = 5.0    # MEASURED, the D-flatted length at the TOP
KNOB_ROUND_LEN = KNOB_SHAFT_H - KNOB_D_LEN   # 7.0 of round bushing below it
KNOB_TIP_CLR  = 0.5    # air above the shaft tip, so the knob seats on the DOME
KNOB_BORE_H = KNOB_SHAFT_H + KNOB_TIP_CLR    # 12.5 total
# >>> AND THE SHAFT NUT NEEDS SOMEWHERE TO GO. The encoder's bushing is fastened
# >>> with a nut that sits ON TOP of the crown, 12 mm across and 3 mm tall, right
# >>> where the knob's base flat wants to be. Without a counterbore the knob simply
# >>> perches on the nut. Concentric with the shaft, so rotation is a non-issue.
KNOB_NUT_D  = 12.0   # nut across corners -- the widest thing in the round section
KNOB_NUT_CLR = 0.5   # on the diameter
# The counterbore clears the whole round section, not just the nut.
KNOB_CB_D   = KNOB_NUT_D + KNOB_NUT_CLR      # 12.5
KNOB_CB_H   = KNOB_ROUND_LEN                 # 7.0 -- where the D-flat begins
KNOB_BOSS_D = 30.0   # flat seating pad on the crown, under the knob
# ---- the encoder's NeoPixel, and a way for its light to get out -------------
# >>> POSITION FROM THE FAB PRINT: the NeoPixel sits centred across the board and
# >>> IN LINE WITH THE TWO TOP MOUNTING HOLES -- board-local (12.7, 22.86), i.e.
# >>> exactly (0, +10.16) from the board centre. That it lands on the same 10.16
# >>> radius as the screw holes is a useful cross-check on the reading.
ENC_PIXEL_OFF = (0.0, 10.16)   # from the BOARD CENTRE, board coordinates
ENC_PIXEL_D   = 4.5            # light hole through the crown
# >>> THE BOARD IS SYMMETRIC, SO WHICH WAY IT FACES IS AN ASSEMBLY INSTRUCTION.
# >>> Four holes on a square pitch and a central shaft mean it drops in happily
# >>> at 180 deg out, which would put the pixel -- and the hole that lights it --
# >>> at the BACK of the knob instead of the front. Fitted with the NeoPixel edge
# >>> FORWARD, so the glow shows on the side you look at.
ENC_PIXEL_FORWARD = True
# >>> NO CHANGE TO THE KNOB. A rotationally-symmetric light gap was cut into the
# >>> knob's base and then removed: the seam between the knob and the crown already
# >>> leaks plenty, so lifting the knob off its seat bought nothing and cost the
# >>> seating area. The window in the crown is the whole feature.
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
# Height is RELATIVE to the arch now -- on the flattened crown a fixed 112 put
# the pads out at the extreme edge of the shell instead of up on the shoulder.
TOUCH_FRAC   = 0.55  # up the arch, 0 = springing line, 1 = apex
TOUCH_Y      = ARCH_Y + TOUCH_FRAC * ARCH_RY
TOUCH_DEPTH  = 38.0  # pad centre from the front face -- just behind the ToF
TOUCH_WALL   = 1.6   # local wall thinning behind each pad, from WALL
# ---- VL53L0X ToF, on the crown just to the right of the knob --------------
# Mounted LONGWISE front-to-back so the 17.8 mm edge clears the encoder board.
TOF_HOLE_D  = 3.5    # pinhole aperture through the crown (clears the 25 deg FoV)
# >>> 3.5 IS TOO SMALL, AND IT IS MEASURED, NOT SUSPECTED. Clearing the cone is
# >>> not the only requirement: emitter and receiver share this one bore with no
# >>> barrier between them, so light crosses over inside it and the assembled
# >>> machine ranges its own aperture at a fixed 0.024 m instead of the room.
# >>> The firmware works around it (packages/hw/proximity.yaml detects deviation
# >>> from that constant rather than distance). The real fix is >=6 mm chamfered,
# >>> or two bores with a septum -- tracked as H4 in FUTURE-DEVELOPMENT.md. Left
# >>> at 3.5 here because the dome is PRINTED: changing it reprints the dome.
TOF_PCB_W   = 17.78  # Adafruit #3317 STEMMA QT, short edge -- CONFIRMED
TOF_PCB_D   = 25.4   #   "                      long edge  -- CONFIRMED
# >>> TOF_X IS NOT A BOARD-EDGE GAP ANY MORE, SO IT IS RESOLVED LATER. It used to
# >>> be W/2 + ENC_PCB/2 + 1.5 + TOF_PCB_W/2 -- "leave 1.5 mm between the two
# >>> boards" -- which is the wrong constraint: what actually collides is the
# >>> BOSSES, and they stand outboard of nothing and inboard of the board edges.
# >>> With both boards' real four-hole patterns the 1.5 mm board gap put an
# >>> encoder boss and a ToF boss 0.59 mm apart at IDENTICAL depth. See
# >>> _resolve_tof_x(), which solves for the gap that matters. BOSS_D does not
# >>> exist yet at this point in the file, which is why this cannot be done here.
TOF_X       = None   # resolved by _resolve_tof_x(), from boss clearance
# TOF_Y is set with ENC_Y from CROWN_Z, below -- they sit side by side.

# ---- rear-wall features (see the REAR view; y up from the bottom) ---------
# >>> THE UPS AND THE FLEX NO LONGER STACK. The flattened crown took the
# >>> interior height down to 157.5, and 93 (UPS) + 70 (Flex) is 163. They sit
# >>> SIDE BY SIDE instead -- 60 + 110 = 170 in a 197 wide wall, which is the
# >>> one axis that got roomier when the array came off the flanks.
#
# That moves the UPS off centre, and its barrel jack with it. So the jack is now
# a PANEL-MOUNT part wired to the UPS input on a short lead, rather than the
# board's own connector poking through. It costs one flying lead and keeps the
# jack centred as intended -- and it decouples the jack from wherever the UPS
# ends up, which has now moved twice.
LP_D, LP_Y      = 4.0, 120.0        # BH1750 light pipe ("lux"), centred, above
                                    #   both boards now that the middle is free
# >>> MEASURED: the charging port and the encoder both take a 7 mm hole, the
# >>> push button 12 mm. BARREL_D was 11.0 -- a guess at a panel-mount DC-005 --
# >>> which would have left a 4 mm gap round the jack in the visible rear wall.
# >>> COMPONENT SIZE AND HOLE SIZE ARE DIFFERENT NUMBERS, and conflating them is
# >>> what made both of these too tight to fit. BARREL_D and SW_D are what Andy
# >>> CALIPERED -- 7 and 12 -- and they were then cut as the openings themselves,
# >>> at nominal, with nothing for the fit. A printed hole comes out under size
# >>> anyway (elephant's foot, first-layer squish, and the perimeter's own
# >>> compensation), so nominal is the worst case, not the average one.
# >>> The measurements stay true; PANEL_FIT is what makes them assemble.
PANEL_FIT       = 1.0               # on the diameter of a panel-mount opening
BARREL_D        = 7.0               # MEASURED body of the charge jack
BARREL_HOLE_D   = BARREL_D + PANEL_FIT   # the opening actually cut
# >>> THE JACK IS LOW, NOT MID-WALL. A barrel lead entering half way up the back
# >>> of a bedside object drapes across it; entering just above the desk it runs
# >>> straight down behind. It was at y=95 only because the Flex started at y=16
# >>> and the two big boards filled everything below. Lifting the Flex to y=22
# >>> opens the whole strip under it, and the jack drops to just clear the plate.
BARREL_Y        = 12.0              # jack centre, centred in width, LOW
# Vents: TWO STACKS, high on the rear wall above both boards. Everything below
# is now occupied wall-to-wall, so the free band is up in the arch.
# >>> THE VENTS ARE LOUVRED, AND SIZED SO YOU CANNOT SEE IN. 30 x 5 mm slots cut
# >>> straight through are windows: from directly behind you look past the wall
# >>> and straight at the UPS. Each slot is now 2.0 mm tall and RISES going
# >>> inward by a full wall thickness, so a horizontal line of sight enters the
# >>> outer opening and lands on the slot's own top face. You can only see in
# >>> from below the machine, which is where nobody looks. Air still convects
# >>> straight up through them.
# >>> ONE WIDE STACK ABOVE THE LIGHT PIPE, NOT TWO NARROW ONES EITHER SIDE.
# >>> The old layout put an 18 x 12..123 stack at x=59 and another at x=143, which
# >>> between them fenced off both upper quadrants of the rear wall -- the two
# >>> largest clear areas on it -- for 432 mm^2 of opening. Stacking the same area
# >>> in ONE wider block directly above the pinhole costs nothing aerodynamically
# >>> (it is the same free area over the same hot part) and hands both quadrants
# >>> back for boards. That is what let the RTC come off the floor.
# >>>
# >>> HEIGHT IS CAPPED BY THE LOUVRE, NOT BY SPACE. Each slot rises VENT_RISE
# >>> across the wall so a level sight line lands on the slot's own top face; that
# >>> only works while 2*VENT_HH <= VENT_RISE. Going taller and fewer would have
# >>> been simpler and would have turned the vent back into a window onto the UPS.
# >>> So the area is bought with WIDTH, which is free, and the slots stay 2.0 tall.
# >>> THE SLOTS FOLLOW THE ARCH NOW, AND EACH HAS ITS OWN LENGTH. Three equal
# >>> 72 mm slots stacked read as a rectangle pasted onto a curved shell. Their
# >>> ends now sit a CONSTANT distance in from the arch's inner face, which is a
# >>> true offset of the contour rather than a scaled copy of it -- the ends trace
# >>> the arch, so the stack narrows exactly as the shell does.
# >>> VENT_W is gone: there is no single slot width any more, and leaving the name
# >>> around would invite something to keep using it.
VENT_HH = 1.0                       # HALF-height (so 2.0 tall)
VENT_INSET = 40.0                   # slot end, in from the arch's INNER face
VENT_LEN_MIN = 12.0                 # never let the top slot vanish to a dot
VENT_N, VENT_P  = 3, 5.0            # count, pitch -- ONE stack, centred
# >>> CLEAR OF THE LUX BOARD, NOT JUST THE LUX PINHOLE. 128 cleared the Ø4 pipe
# >>> by 6 mm and put louvre 0 straight through the BH1750's upper mounting
# >>> bosses, which stand 7.5 mm above the pipe on the hole pitch plus 3 mm of
# >>> boss. The opening in the wall is the small part of that board's footprint.
VENT_Y          = 133.0             # bottom slot, above the lux board's bosses
VENT_RISE       = 2.5               # how far a slot climbs across the wall
                                    #   (== WALL -> 45 deg, fully blocks level sight)

# ---- internals shown for reference ----------------------------------------
FOOT_D, FOOT_IN     = 12.0, 16.0         # rubber feet
# >>> 22.0 WAS NOT CLOSE. Inferred from the fit-up: the cans overlapped the UPS by
# >>> ~3 mm at D=64, so (FP_T + can) + UPS_D = 64.5. Holding UPS_D at its own guess
# >>> of 24 gives a 36.5 mm can -- 14.5 more than modelled. Still (?) because the
# >>> observation constrains the SUM, not this term alone: if the pack turns out
# >>> deeper than 24, this is correspondingly less. Caliper either one and the other
# >>> follows.
SPK_BODY_D          = 36.5               # (?) speaker can depth -- INFERRED, see above

# ---- front module: diffuser + cavity + mounts ------------------------------
# DIFF_T / DIFF_REBATE / DIFF_MARGIN / CAV_WALL are defined UP TOP, next to
# BOSS_EDGE -- they have to exist before RIM_MIN can be derived from them.
# Air gap between the acrylic and the LEDs. Too small and you see 48 dots
# through the diffuser; ~0.7x the LED pitch is the usual rule.
DIFF_GAP    = 12.0                   # (?) TUNE ON A TEST PRINT
LED_STRIP_T = 2.13                   # MEASURED. SK6812 ribbon + adhesive.
TRAY_REBATE = 2.0                    # pocket the matrix tray front face sits in
TRAY_FIT    = 0.20                   # (superseded: the tray is a clearance fit
                                     #  with clips now -- see gen_front_plate)
SPK_BOLT    = 4                      # driver screws per side
SPK_BC      = 46.0   # (?) driver bolt circle -- MEASURE
MIC_CHAN_D  = 2.4                    # channel depth on the back -- deepened to
                                     #   bring the array closer to the facade
MIC_GASKET  = 1.0                    # foam gasket land around each port
# Depth of the front module at its deepest (the crescent zone):
FM_DEPTH    = FP_T + DIFF_REBATE + DIFF_GAP + LED_STRIP_T

# ---- LED carrier: PART 6 ---------------------------------------------------
# The pixels are cut strip segments, one per row. They have to be held at a KNOWN
# standoff behind the acrylic -- DIFF_GAP is the whole reason the diffuser looks
# even -- and adhesive tape onto a curved cavity wall will not do that. So they
# go on their own flat plate that screws onto the back of the front module.
#
# >>> WHY IT MOUNTS TO PADS ON THE INSIDE OF THE CAVITY WALL. Three other places
# >>> were considered and all of them cost more:
# >>>   - ears reaching OUTWARD onto the rim: there is only 0.9 mm of rim free
# >>>     outside the cavity wall before the dome's rib keep-out. Making room
# >>>     means RIM_MIN 12 -> ~16, which shrinks the crescent to 85 x 58.7 and
# >>>     drops it to five rows -- 48 px would no longer fit.
# >>>   - pillars up from the facade floor: 12 mm columns standing inside a lit
# >>>     cavity, straight across the light path.
# >>>   - captured by the dome, no screws: locates the plate but never clamps it,
# >>>     and the strips hang off it at a 12 mm standoff.
# >>> Pads on the wall put the fixings at the perimeter, where the diffuser is
# >>> dimmest anyway, and they double as buttresses for what is otherwise a
# >>> 2 mm x 20 mm tall unsupported fin.
#
# Z STACK, from the front face of the facade:
#   facade front            0
#   acrylic front           DIFF_LIP                 1.5
#   acrylic back            DIFF_LIP + DIFF_REBATE   4.7
#   LED emitting face       + DIFF_GAP              16.70  = CAV_Z, wall back
#   strip back / carrier    + LED_STRIP_T           18.83  = CARRIER_Z0
#   carrier back            + CARRIER_T             21.33  == FM_DEPTH
# CARRIER_T is 2.5 BECAUSE that lands the assembly exactly on FM_DEPTH, which is
# the number every other sheet already quotes as the module's depth.
CARRIER_T      = 2.5
# DIFF_LIP lives here rather than in gen_front_plate.py now: the carrier's z
# origin is derived from it, and two files deriving a z stack from a constant
# defined in only one of them is how the last set of drift bugs started.
DIFF_LIP       = 1.5                 # facade left in FRONT of the acrylic
CAV_Z          = DIFF_LIP + DIFF_REBATE + DIFF_GAP   # cavity wall back face
CARRIER_Z0     = CAV_Z + LED_STRIP_T                 # carrier front face

# ---- crown boards: BEHIND the baffle, not beside it -------------------------
# >>> THE FRONT MODULE REACHES INTO THE DOME, AND THE CROWN BOARDS DID NOT KNOW.
# >>> The crescent cavity wall runs from the facade back to CARRIER_Z0, so the
# >>> first CARRIER_Z0 mm of the dome's interior is not free space at all. The
# >>> encoder and the ToF were placed at a hand-picked depth of 30.0 from before
# >>> that wall existed, which put the leading 1.53 mm of both boards inside it.
# >>> Deriving the depth means the boards move whenever the baffle does -- and the
# >>> baffle has moved twice this week.
# >>> AND THE BAFFLE IS NOT THE LAST THING IN THE WAY. Clearing the cavity wall by
# >>> 2.0 left the encoder's front bosses at depth 23.37 against a carrier whose
# >>> BACK FACE is at 21.33 -- 2.04 mm, all of which the carrier's own fixing screws
# >>> stand up into. With the front face and LED plate screwed in they touch. The
# >>> stack is what has to be cleared, so the stack is what the depth is built from:
# >>> the cavity wall, the carrier plate on it, and the heads of the screws holding
# >>> the carrier down.
CARRIER_SCREW_H  = 2.0                # M2.5 pan head standing off the carrier
# >>> 1.5 -> 5.0, NOW THAT THE SHELL IS 79 DEEP. 1.5 mm was the tightest margin
# >>> left in the machine and it sat on top of CARRIER_SCREW_H, which is my estimate
# >>> of an M2.5 pan head rather than a measurement -- a 3 mm head would have eaten
# >>> two thirds of it. There are 26 mm of unused depth behind these boards, so the
# >>> margin was expensive to keep and free to fix. Costs nothing but moving the
# >>> knob 3.5 mm further back along the crown.
CROWN_CLR        = 5.0                # air after all of that
CROWN_Z = (CARRIER_Z0 + CARRIER_T + CARRIER_SCREW_H + CROWN_CLR
           + max(ENC_PCB, TOF_PCB_D) / 2.0)
ENC_Y = CROWN_Z       # knob/encoder centre, from the front face, in plan
TOF_Y = CROWN_Z       # same front-offset as the knob, so it sits alongside
CARRIER_Z1     = CARRIER_Z0 + CARRIER_T

# The strip ribbon is STRIP_W wide and the bottom row's CENTRE is only LED_D/2
# above the crescent baseline, so the ribbon hangs (STRIP_W - LED_D)/2 = 2.4 mm
# BELOW it. The plate needs a skirt or row 0 is unsupported along its bottom
# edge. Checked against the mic channel in the carrier's own run.
# >>> THE SKIRT IS A LIGHT SEAL, NOT JUST A BACKING. It was ribbon-overhang + 0.6,
# >>> i.e. just enough to stop row 0 peeling. 0.6 mm of overlap seals nothing: the
# >>> strip's own edge glows sideways and there was no lip in front of it. The lip
# >>> is the term that matters, so it is named.
CARRIER_LIP    = 1.5      # skirt BEYOND the ribbon -- the light seal
CARRIER_SKIRT  = STRIP_W / 2 - LED_D / 2 + CARRIER_LIP

# End stops: a block at each end of each row. NOT full-length channels -- the
# row pitch is LED_ROW_PITCH (11.0) against a STRIP_W (10.0) ribbon, so a
# dividing wall between rows would be 1.0 mm total, i.e. 0.5 mm a side. That is
# under one nozzle width on a 0.4 mm setup. The stops locate each segment's ends
# and the adhesive backing does the holding.
STOP_T         = 1.6                 # stop thickness, along the row
STOP_H         = 2.2                 # how far it stands off the carrier face
# >>> STOP_W IS 3.0, NOT STRIP_W + 2. A stop the full width of the ribbon (12)
# >>> looks like the obvious choice and it is the wrong one: the stops sit at the
# >>> row ENDS, which is exactly the perimeter real estate the fixing pads need,
# >>> and a 12 mm stop blocked every usable pad angle below 20 deg. A 3 mm nub at
# >>> the row's centre height stops the segment sliding just as well -- nothing
# >>> pushes it sideways, and the adhesive backing holds it down -- while leaving
# >>> the perimeter free. See the band table in the carrier's run.
STOP_W         = 3.0                 # across the row, centred on it
STRIP_END_CLR  = 0.5                 # per end, cut segment to stop

# Six fixings, symmetric. The angles are NOT chosen for looks: each is the best
# point of a band from pad_angle_bands(), which is the set of angles where a pad
# clears the pixels, the end stops AND the ribbons. The carrier's run prints that
# table -- move a row count or a stop size and the bands move with it, so re-read
# it rather than nudging these by eye.
#
# >>> THERE IS NO PAD AT THE APEX, and that is not an oversight. 90 deg looks
# >>> like the obvious spot -- it has the most room from the pixels of anywhere
# >>> on the wall -- but the top row's RIBBON runs right through it. The row is
# >>> only 2 px, so the LEDs are nowhere near, which is exactly why a check that
# >>> looked at pixels alone waved it through and the preview did not.
CARRIER_FIX_DEG = [7.0, 33.2, 61.8, 118.2, 146.8, 173.0]
# >>> M2.5, NOT M3, AND THIS IS THE REASON. Everything else on the build is M3,
# >>> but an M3 pad is 8 mm across and at 8 mm the lowest usable band is 20 deg
# >>> -- which leaves the plate's two bottom corners, and with them the widest
# >>> and most visible LED row, hanging off a fixing 19 mm away. Dropping to
# >>> M2.5 shrinks the pad to 6.5 and opens a band at 7.3 deg, right down beside
# >>> those corners. A smaller screw in a better place beats a bigger one in a
# >>> worse one; nothing here is structural, it only has to hold a flat standoff.
PAD_W          = 6.5                 # pad diameter -- a round boss, so this is
                                     #   both its width along the wall and its
                                     #   radial thickness
# >>> A PAD MUST NOT POKE OUT PAST THE CAVITY'S OUTER FACE. There is 0.9 mm of
# >>> rim beyond it before the dome's retaining-rib keep-out, and a boss in that
# >>> band jams the module on assembly -- which is precisely the failure the
# >>> speaker posts caused. So the pad centre is offset inward along the true
# >>> ELLIPSE NORMAL by (PAD_W/2 - CAV_WALL), which puts the boss's outer edge
# >>> flush with the wall's outer face. Offsetting by scaling the semi-axes
# >>> instead would be wrong here: the crescent is eccentric (90.5 x 64.2), so a
# >>> scaled offset and a normal offset diverge badly near the ends.
# The +0.3: CAV_R/CAV_RY are the DIFF ellipse with CAV_WALL added to each
# semi-axis, which is a scaled offset, not a normal one -- so the wall's true
# normal thickness dips a hair under CAV_WALL at some angles and a pad sized to
# exactly CAV_WALL lands 0.03 proud. Nudge it in and the margin goes positive.
PAD_WALL_CLR   = 0.3
PAD_OFFSET_IN  = PAD_W / 2 - CAV_WALL + PAD_WALL_CLR
PAD_PROJ       = PAD_W - CAV_WALL + PAD_WALL_CLR   # DERIVED inward projection
# >>> THE PAD IS A TAPERED BOSS, NOT A STRAIGHT EXTRUSION. It is PAD_W across at
# >>> the seating plane and PAD_W + 2*PAD_DRAFT at the facade. The module prints
# >>> FACE DOWN, so features that widen as they rise overhang; narrowing upward
# >>> is the self-supporting direction, and supports inside a diffusion cavity
# >>> would leave scarring visible through the acrylic. The flare doubles as a
# >>> gusset at the root, where a boss standing CARRIER_Z0 tall off a 2 mm wall
# >>> wants to snap off.
# >>> 1.5 over 18.83 is about 4.6 deg -- gentle, but it is the whole bottom of
# >>> the boss rather than a token fillet, and it costs nothing: everything the
# >>> pad must clear sits at the TOP of the cavity, where it is narrowest.
# >>> PAD_DRAFT IS 0. It was 1.5, which put a gusset at the boss root -- good --
# >>> but a round flare grows BOTH ways: outward through the cavity wall (now
# >>> clipped) and INWARD, 1.5 mm deeper into the disc's path. That inward 1.5
# >>> became 1.5 mm of extra notch depth on the acrylic, i.e. 1.5 mm more nick
# >>> showing past the ledge. The 45 deg underside ramp already IS the gusset and
# >>> costs the disc nothing, so the flare went and the ramp stayed.
PAD_DRAFT      = 0.0                 # extra radius at the base, per side
# >>> AND IT STARTS ABOVE THE ACRYLIC, ON A 45 DEG RAMP. A pad running all the
# >>> way down to the facade sits squarely in the opal acrylic's pocket -- the
# >>> disc is CRES_R + 0.2 across and the pad reaches 4.8 mm inside DIFF_R, so
# >>> the acrylic simply cannot drop in past it (607 mm^3 of interference). The
# >>> alternative was scalloping the acrylic, but that makes a hand-cut part
# >>> depend on six boss positions, and it is a part you may recut.
# >>> So the pad begins at the pocket floor and grows OUT OF THE WALL on a 45 deg
# >>> underside ramp: zero projection at PAD_Z0, full section one pad-radius
# >>> later. 45 deg is self-supporting on FDM, so the underside needs no support
# >>> inside the optical cavity. This is the "gradual rise" -- the boss is never
# >>> a square shelf hanging off the wall at any height.
PAD_Z0         = DIFF_LIP + DIFF_REBATE          # pocket floor: clear of acrylic
PAD_RAMP       = PAD_W / 2 + PAD_DRAFT           # 45 deg -> rise == radius
PAD_PILOT_D    = 2.1                 # M2.5 self-tapping pilot
PAD_PILOT_Z    = 8.0                 # pilot depth into the pad
CARRIER_SCREW  = 2.5                 # M2.5 -- see the note on PAD_W
CARRIER_CLR_D  = 2.9                 # clearance hole in the carrier
# The cavity's inner and outer ellipses, needed by carrier_pads(). gen_front_
# plate.py derives the same two locally as DIFF_R/DIFF_RY and CAV_R/CAV_RY.
DIFF_R_G       = CRES_R  + DIFF_MARGIN
DIFF_RY_G      = CRES_RY + DIFF_MARGIN
CAV_R_G        = DIFF_R_G  + CAV_WALL
CAV_RY_G       = DIFF_RY_G + CAV_WALL

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
# Both rear lugs are LEFT of centre: the UPS stands on the floor from x=120 to
# x=180, so the rear-right corner is spoken for. The plate is still carried at
# six points round the perimeter, just not symmetrically.
# >>> THE REAR PAIR MOVED OFF THE BARREL JACK. They were at x=55 and 105; the
# >>> jack dropped to y=12 with a 20 mm land spanning x 91..111, and the tab at
# >>> 105 sat directly behind it. The switch land takes x 16.5..35.5 and the UPS
# >>> owns everything past x=120, which leaves x 36..90 -- so 45 and 82.
# >>> "BEHIND THE SPEAKERS" STOPPED BEING TRUE WHEN THE SPEAKERS GOT DEEPER. At a
# >>> 22 mm can these sat 10 mm clear; at the real 36.5 they are 5.9 mm INSIDE it.
# >>> The comment was right about the intent and silently wrong about the number,
# >>> which is what a hard-coded depth next to a "behind the X" rationale always
# >>> risks. Derived from the can now, so it stays behind it.
# >>> AND THE LUG HAS LENGTH -- its FRONT EDGE is what meets the speaker, not its
# >>> centre. Deriving from the centre put it 3 mm inside the can anyway; the first
# >>> fix was as wrong as the thing it fixed, just by less.
SPK_LUG_CLR = 4.0                                          # lug edge to can
SCREW_FRONT_Y = FP_T + SPK_BODY_D + LUG_L / 2 + SPK_LUG_CLR   # 51.5 at a 36.5 can
SCREW_REAR_Y  = D - WALL - LUG_L / 2                          # hard against the wall
SCREWS = [(_LX, SCREW_FRONT_Y), (W - _LX, SCREW_FRONT_Y),  # behind the speakers
          (_LX, SCREW_REAR_Y),  (W - _LX, SCREW_REAR_Y),   # side walls, rear
          (45.0,  D - WALL - LUG_L/2),            # rear wall, left of the jack
          (82.0,  D - WALL - LUG_L/2)]            # rear wall, right of the jack

# ---- what goes where inside --------------------------------------------------
# Waveshare UPS Module 3S: a 60 x 93 board with the three 18650 holders on it,
# charged from a 12.6 V 2 A barrel jack. 93 mm will NOT lie down in a 59 mm
# interior, so the whole board STANDS VERTICALLY against the rear wall -- but it
# no longer stands in the MIDDLE of it. See the rear-wall note: it shares the
# wall with the Flex, side by side, and the jack became a panel-mount part.
# >>> SPLIT SO THE (?) LANDS ON THE ONE VALUE THAT IS ACTUALLY A GUESS. All three
# >>> shared a line and a single "(?)", so the doc check quite reasonably demanded
# >>> that MEASURE-ME ask for the width and height too -- which the DXF settled
# >>> long ago. A marker on a tuple marks everything in it.
UPS_W, UPS_H = 60.0, 93.0                # board outline, from the Waveshare DXF
UPS_D        = 24.0                      # (?) board + cells, front to back -- MEASURE
# >>> MOUNTING HOLES, READ OUT OF WAVESHARE'S OWN DXF. Four Ø3.1 holes, 7.0 mm in
# >>> from each long edge and 3.5 mm from each short edge, so a 46.0 x 86.0 pitch
# >>> inside the 60 x 93 board. There is also a lone Ø2.5 near the top centre
# >>> (30.0, 89.2) which is NOT a fixing -- do not build to it.
# >>> Waveshare's page gives "60 x 93, mounting hole 3.0" and nothing else; the
# >>> positions only exist in the DXF.
UPS_HOLES     = [(7.0, 3.5), (53.0, 3.5), (7.0, 89.5), (53.0, 89.5)]
UPS_HOLE_D    = 3.1
UPS_HOLE_PITCH = (46.0, 86.0)
UPS_BACK            = 0.0                # stands hard against the rear wall

# ReSpeaker Flex core -- MEASURED, no longer a guess.
# The BARE BOARD is 52 x 70 x 20 deep (20 at the XIAO, its tallest point). The
# 3.5 mm jack and the mic-ribbon connector overhang the two SHORT (52 mm) edges,
# so the assembly needs a 110 mm envelope in that direction. Mounted with the
# 52 mm dimension HORIZONTAL: 110 wide (with overhangs) x 70 tall x 20 deep.
#
# It mounts VERTICALLY on the inside of the REAR WALL, BESIDE the UPS (they no
# longer stack -- see the rear-wall note): that face is reachable the moment the
# front module is out, and it keeps the floor clear.
# >>> MEASURED OFF SEEED'S OWN STEP MODEL (reSpeaker_xvf3800_flex_Separate.step).
# >>> The core board is 70.50 x 52.20, with FOUR mounting holes 4.0 mm in from
# >>> every corner -- a 62.5 x 44.2 pitch -- Ø3.3 drilled on a Ø6.1 pad, and a
# >>> 1.0 mm corner radius. Components stand up to 4.8 mm proud of the board.
# >>> Seeed publishes none of this; it was extracted from the CAD. The old
# >>> FLEX_PCB_W/H guess (52 x 70) was the right SIZE with the axes swapped --
# >>> the board is landscape, 70.5 across and 52.2 up.
# >>> RECONCILED WITH THE MEASURED BOARD, WHICH WINS. The STEP gave 70.50 x 52.20
# >>> with holes 4.0 in from each corner; the measured board is 52 x 70 x 20 with
# >>> holes whose OUTER edges sit 2.0 from each corner and whose INNER edges are
# >>> 60 and 42 apart. Those two numbers solve, on BOTH axes independently, to a
# >>> Ø3.0 hole inset 3.5 -- a 63 x 45 pitch, which is exactly what FLEX_HOLE_PX/PY
# >>> already held. The STEP's 4.0/62.5x44.2 sits inside the ~0.8 mm uncertainty in
# >>> where I judged the board's origin, so the agreement is real, not luck.
# >>> The 20 mm depth is the one thing neither the STEP nor the guess had: that is
# >>> the board PLUS the XIAO in its sockets, and it is what the rear wall has to
# >>> give up out of a 59 mm interior.
FLEX_CORE_W, FLEX_CORE_H = 52.0, 70.0   # MEASURED
FLEX_CORE_D = 20.0                      # MEASURED, incl. the seated XIAO
FLEX_CORE_HOLE_D = 3.0                  # solved from the edge measurements
FLEX_CORE_HOLE_INSET = 3.5              # centre, from each edge
FLEX_CORE_HOLES = [(3.5, 3.5), (48.5, 3.5), (3.5, 66.5), (48.5, 66.5)]
FLEX_CORE_TALL = 4.8                    # tallest component, from the STEP
# >>> AND THE ARRAY + RIBBON NEED ~110 mm OF CLEAR RUN. That is what FLEX_W has
# >>> always reserved; it is not the board, it is the corridor the 110 mm linear
# >>> array and its FPC need in order not to be pinched.
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
# Both boards now sit low on the wall, side by side, with the free band ABOVE
# them for the lux pipe and the vents. The rear wall curves in above the
# springing line, so the 110 mm envelope still has to fit the ARC at the Flex's
# TOP edge -- checked in flex_wall_fit() and in the clearance table.
# Where they sit is set by the FIXING LUGS, not by taste. The UPS goes to the
# floor, so it has to leave the right-hand lug band clear; the Flex is lifted
# clear of lug height instead, which lets it overhang the left-hand lugs.
UPS_WALL_X             = 150.0    # UPS centre -- right of centre, clear of the
                                  #   right lug band at x 186.5..200.5
FLEX_WALL_X            = 60.0     # Flex centre -- left, 5 mm off the UPS
# >>> RAISED FROM 16 TO 22 TO CLEAR THE BARREL JACK. The jack now sits at y=12
# >>> with an 11 mm body; at 16 the Flex overlapped it. 22 also deepens the floor
# >>> slot the amp lives in from 12 to 18 mm, which is pure gain.
FLEX_WALL_Y            = 22.0     # bottom edge, above the jack and the lugs

# The TPA2016 mounts FLUSH on the rear wall beside the UPS. Not a side wall:
# the sides are only vertical below the springing line, and the speaker boxes
# own all of that. Above the springing the sides are the curved crown, which is
# no good for a flat board.
# The TPA2016 is on the FLOOR now, not the rear wall. Lifting the Flex clear of
# the lugs left a 12 mm slot underneath it, and the amp is only 8 tall -- it
# tucks in there, which is also the shortest run to both speakers. The rear wall
# has no room left: Flex and UPS fill it wall-to-wall below y=97.
# >>> ADAFRUIT TPA2016 (#1712), FROM ITS OWN BOARD FILE. The outline wires in
# >>> "Adafruit TPA2016D2.brd" <plain> give 21.59 x 27.94 (0.85" x 1.1") with
# >>> 2.54 corner radii. It was modelled 26.0 x 20.0 -- wrong on both axes, and
# >>> the wrong shape: the real board is TALLER than it is wide, not shorter.
# >>> Laid with its long axis across the machine to keep the floor depth down.
AMP_W, AMP_D, AMP_H = 27.94, 21.59, 8.0      # Adafruit #1712, from the .brd
# >>> IT HAS TWO M2.5 MOUNTING HOLES, AND I CLAIMED IT HAD NONE. That claim came
# >>> from grepping the board file's <plain> section, finding no <hole>, and
# >>> reporting absence as fact. The holes are placed as ELEMENTS using the
# >>> package MOUNTINGHOLE_2.5_PLATED_THICK, which is in the same file, further
# >>> down -- exactly where the CharliePlex driver's holes were too, after that
# >>> same mistake had already been made once on that board.
# >>> Absence in the part of a file you happened to read is not absence.
# >>>
# >>> POSITIONS FROM THE FILE, NOT FROM READING THE PICTURE. x was 18.03 (0.71")
# >>> with a note reconciling the print's 0.1" as an edge-to-edge distance. That
# >>> reconciliation was built to fit the guess: 0.71" locates the TERMINAL
# >>> BLOCKS, not the holes -- the other dimension object at that same x,
# >>>   <dimension x1="18.034" y1="17.78" x2="18.034" y2="10.16">  -> 0.3"
# >>> is the terminal pitch.
# >>> Eagle <dimension> objects SNAP to what they measure, and the two that land
# >>> on the holes are:
# >>>   <dimension x1="19.05" y1="25.4" x2="19.05" y2="2.54">   -> 0.9"  pitch
# >>>   <dimension x1="19.05" y1="25.4" x2="21.59" y2="25.4">   -> 0.1"  to the edge
# >>> So the centres are at x = 19.05, i.e. 2.54 from the right edge -- and 0.1"
# >>> is centre-to-edge, not edge-to-edge. 19.05/21.59 = 88% across, which is
# >>> where they sit in the print; 18.03 would be 83.5%.
AMP_HOLES     = [(19.05, 2.54), (19.05, 25.40)]   # board-local, from the .brd
AMP_HOLE_D    = 2.5
AMP_HOLE_PITCH = 22.86                            # 0.9", vertical; both same x
# >>> MOVED FORWARD, OFF THE REAR TAB. At depth 50 the amp spanned 40..60 and the
# >>> rear fixing tab at x=82 reaches forward to depth 49.5 -- a 10.5 mm overlap.
# >>> Depth 34 puts it in the open floor band between the matrix (ends 14.7) and
# >>> the tabs (start 49.5), which is also easier to get a screwdriver to.
AMP_X, AMP_DEPTH    = 80.0, 34.0             # floor, forward of the rear tabs


def amp_holes_part():
    """The amp's two holes as (x, depth) offsets from the board CENTRE.

    >>> THE AMP IS LAID DOWN, SO ITS AXES SWAP -- and the bosses did not. The .brd
    >>> frame is 21.59 WIDE x 27.94 TALL; the board is fitted with its long axis
    >>> ACROSS the machine, so board-y becomes part-x and board-x becomes DEPTH.
    >>> The old code placed both bosses at hy = AMP_DEPTH, i.e. on the board's
    >>> depth centreline, and spread them +-pitch/2 in x. The spread axis was
    >>> right; the centreline was not. Both holes are at board x = 19.05, which is
    >>> 8.26 mm off the 21.59-wide centre -- so the board could not have gone on
    >>> over those bosses at all, at any pitch.
    >>> It lies COMPONENT SIDE UP, which is a rotation and not a flip, so nothing
    >>> inverts here; contrast the wall boards, which face into the wall.
    >>> Sign chosen so the terminal-block edge (board +x, the same edge the holes
    >>> are near) points FORWARD, at the speaker it drives.
    """
    return [(by - AMP_W / 2.0, -(bx - AMP_D / 2.0)) for bx, by in AMP_HOLES]
AMP_WALL_X, AMP_WALL_Y = AMP_X, AMP_H/2      # (kept for the drawings)

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
    half = ARCH_R * max(1.0 - (dy/ARCH_RY)**2, 0.0) ** 0.5 if dy > 0 else ARCH_R
    return [W/2 - half, W/2 + half]


def arc_width(y):
    """Interior width of the shell at height y. Below the springing line the
    flanks are straight; above it they follow the arc and pinch in fast."""
    if y <= ARCH_Y:
        return IN_W
    dy = y - ARCH_Y
    if dy >= ARCH_RY:
        return 0.0
    return 2 * (ARCH_R * (1.0 - (dy/ARCH_RY)**2) ** 0.5 - WALL)


def flex_wall_fit():
    """Does the 110 mm Flex envelope fit the rear wall where we put it?
    The TOP edge is the binding case -- that is where the arc is narrowest.
    Returns (available_width_at_top, needed, slack)."""
    avail = arc_width(FLEX_WALL_Y + FLEX_H)
    return avail, FLEX_W, avail - FLEX_W


def flex_holes():
    """The four M3 mounting holes, as (x, y) on the rear wall, centred in
    width. Pitch 45 x 63 from the measured 42 x 60 inside-edge spacing."""
    return [(FLEX_WALL_X + sx * FLEX_HOLE_PX/2,
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
        ("UPS 3S (upright)", UPS_WALL_X - UPS_W/2, UPS_WALL_X + UPS_W/2,
         D - WALL - UPS_D, D - WALL),
        ("TPA2016 (floor)", AMP_X - AMP_W/2, AMP_X + AMP_W/2,
         AMP_DEPTH - AMP_D/2, AMP_DEPTH + AMP_D/2),
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
    """The 'D' on its long flat side: flat bottom, straight sides, and a
    FLATTENED half-ellipse on top (semi-axes ARCH_R x ARCH_RY, both inset).
    Not a semicircle -- see CROWN_K."""
    x0, x1 = inset, W - inset
    yb, ys = fy(inset), fy(ARCH_Y)
    a, b = ARCH_R - inset, ARCH_RY - inset
    return (f"M{n(x0)},{n(yb-rb)} V{n(ys)} "
            f"A{n(a)},{n(b)} 0 0 1 {n(x1)},{n(ys)} "
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
    """LED-row CENTRE heights above the baseline, at the solved LED_ROW_PITCH.

    The crown is a flattened ellipse now, so the usable height is LED_RY, not a
    radius, and the pitch was solved to get CRES_PX onto it with slack."""
    y0, apex = LED_D / 2, LED_RY - LED_D / 2
    ys, y = [], y0
    while y <= apex + 1e-9:
        ys.append(y)
        y += LED_ROW_PITCH
    if not ys:
        ys = [y0]
    if n_rows is not None:
        ys = ys[:n_rows] if n_rows <= len(ys) else ys
    return ys


def ell_dist(px, py, a, b):
    """TRUE distance from (px, py) to the ellipse boundary (semi-axes a, b).

    >>> THE CHORD IS NOT THE CLEARANCE. Every earlier version measured how far
    >>> an LED sat from the ellipse HORIZONTALLY (the chord) and, at the apex,
    >>> VERTICALLY. On a circle those agree with the real distance; on an
    >>> ellipse they do not, and the binding case is the diagonal one -- an
    >>> outer pixel two rows down from the apex, where the boundary is falling
    >>> away steeply. That is how the 0.72 crown shipped a top row whose LED body
    >>> stood 0.58 mm OUTSIDE the diffuser while every chord check read clear.
    >>> Everything downstream now measures with this instead.

    Bisects the stationary condition of the squared distance on the first
    quadrant; the ellipse is symmetric so |px| is enough.
    """
    px, py = abs(px), abs(py)
    lo, hi = 0.0, math.pi / 2

    def dF(t):
        s, c = math.sin(t), math.cos(t)
        return (b*b - a*a) * s * c + a * px * s - b * py * c

    if dF(hi) <= 0.0:
        t = hi
    elif dF(lo) >= 0.0:
        t = lo
    else:
        for _ in range(60):
            mid = (lo + hi) / 2
            if dF(mid) < 0.0:
                lo = mid
            else:
                hi = mid
        t = (lo + hi) / 2
    return math.hypot(px - a * math.cos(t), py - b * math.sin(t))


def led_clearance(n, y, a=None, b=None):
    """Gap between the OUTERMOST LED body in an n-pixel row at height y and the
    diffuser ellipse. Negative means the package pokes out past the acrylic."""
    a = LED_R if a is None else a
    b = LED_RY if b is None else b
    return ell_dist((n - 1) * LED_PITCH / 2, y, a, b) - LED_D / 2


def ribbon_cap(y):
    """Most pixels whose RIBBON fits the cavity in the row at height y.

    >>> THIS IS THE CONSTRAINT EVERY EARLIER VERSION MISSED, AND IT BINDS BEFORE
    >>> THE OPTICAL ONE. A cut segment of n pixels is n x LED_PITCH long, not
    >>> (n-1) x LED_PITCH: the cut lines sit half a pitch outboard of the end
    >>> LEDs, and trimming past them takes the solder pads with it. So the strip
    >>> is a full pitch longer than the span between its end pixels -- 6.9 mm on
    >>> the bottom row -- and it is the RIBBON, not the LED, that reaches the
    >>> cavity wall first. The old layout put 11 px on row 0: a 181.5 mm strip
    >>> into a 181.0 mm cavity.
    >>>
    >>> The ribbon is also STRIP_W tall, so what has to fit is a RECTANGLE, and
    >>> its binding corner is the TOP one (the ellipse narrows going up). Below
    >>> the baseline the cavity wall is a straight skirt, hence the min().
    """
    y_top = y + STRIP_W / 2
    lim = DIFF_R_G if y_top <= 0 else min(
        DIFF_R_G, ell_half_chord(y_top, DIFF_R_G, DIFF_RY_G))
    usable = lim - STRIP_END_CLR - STOP_T          # the end stop lives here too
    return max(int(2 * usable // LED_PITCH), 0)


def _crescent_row_cap(y):
    """Most pixels that fit in the row at height y: the tighter of the OPTICAL
    limit (LED body inside the diffuser, true distance not chord) and the
    PHYSICAL one (ribbon + end stop inside the cavity)."""
    n = 0
    for k in range(1, 40):
        if led_clearance(k, y) >= 0.0:
            n = k
        else:
            break
    return max(min(n, ribbon_cap(y)), 0)


def crescent_rows():
    """Lay exactly CRES_PX pixels onto the crescent ellipse.

    Both spacings are fixed -- LED_PITCH along a row, LED_ROW_PITCH between rows
    -- so the row count falls out of LED_RY and the only free variable left is
    how many pixels go in each row.

    ALLOCATION IS CONSTANT-MARGIN, not proportional. Proportional-to-capacity
    looks reasonable in a table and bad on the part: it lets one row run out to
    within 3 mm of the edge while its neighbours stop far short, so the lit
    field bulges. Instead, solve for the single end margin M that spends exactly
    CRES_PX pixels when every row is filled out to M from the edge. The outer
    pixels then trace a curve concentric with the crescent, which is what makes
    it read as a crescent rather than a stack of rows.

    >>> THE MARGIN IS A TRUE DISTANCE TO THE ELLIPSE, NOT A CHORD INSET. See
    >>> ell_dist. Measuring it horizontally lets the diagonal rows creep out
    >>> past the acrylic while the table still reads clear, and it also makes
    >>> the outer pixels trace an offset chord rather than an offset ellipse --
    >>> so the lit field bulges at the shoulders even when the count is right.
    >>>
    >>> ROWS ARE FORCED NON-INCREASING. Bottom-first, each row may hold no more
    >>> than the one below it. Without it the solver will happily return
    >>> 10/10/9/10/... -- every pixel legal, and an obviously wrong silhouette,
    >>> because a row that sits just under a pitch boundary picks up a pixel its
    >>> neighbour just missed.

    Returns (chord_width, count, strip_run) per row, bottom-first.
    """
    ys = crescent_row_ys()
    n_rows = len(ys)
    cap = [_crescent_row_cap(y) for y in ys]
    chord = [2 * ell_half_chord(y, LED_R, LED_RY) for y in ys]

    def at_margin(m):
        out = [0] * n_rows
        for i, y in enumerate(ys):
            k = 0
            for n in range(1, cap[i] + 1):
                if led_clearance(n, y) >= m:
                    k = n
                else:
                    break
            out[i] = min(k, cap[i])          # cap[i] already carries the ribbon
        for i in range(1, n_rows):            # non-increasing, bottom-first
            out[i] = min(out[i], out[i - 1])
        return out

    lo, hi = 0.0, LED_R              # bisect: bigger M -> fewer pixels
    for _ in range(60):
        mid = (lo + hi) / 2
        if sum(at_margin(mid)) >= CRES_PX:
            lo = mid
        else:
            hi = mid
    cnt = at_margin(lo)

    # Bisection lands on the largest margin that still SEATS CRES_PX, so the
    # count is >= the target; give the surplus back from whichever row has the
    # most room left, keeping the sequence non-increasing.
    while sum(cnt) > CRES_PX:
        cand = [i for i in range(n_rows)
                if cnt[i] > 0 and (i == n_rows - 1 or cnt[i] - 1 >= cnt[i + 1])]
        if not cand:
            break
        i = max(cand, key=lambda j: led_clearance(cnt[j], ys[j]))
        cnt[i] -= 1

    short = CRES_PX - sum(cnt)       # ...or top it up, if the crescent is tight
    while short > 0:
        cand = [i for i in range(n_rows)
                if cnt[i] < cap[i] and (i == 0 or cnt[i] + 1 <= cnt[i - 1])]
        if not cand:
            break
        i = max(cand, key=lambda j: led_clearance(cnt[j] + 1, ys[j]))
        cnt[i] += 1
        short -= 1
    return [(chord[i], cnt[i], max(cnt[i] - 1, 0) * LED_PITCH)
            for i in range(n_rows)]


def crescent_led_xy():
    """Every pixel centre as (x, y) RELATIVE to the crescent centre -- x from the
    centreline, y above the baseline. The carrier and the pad placement both
    work in this frame."""
    o = []
    for (_, k, run), y in zip(crescent_rows(), crescent_row_ys()):
        for i in range(k):
            o.append(((-run/2 + i * LED_PITCH) if k > 1 else 0.0, y))
    return o


def carrier_pads():
    """The six screw pads, as (x, y, angle) in the crescent frame.

    Each sits on the cavity wall's INNER face -- the ellipse DIFF_R x DIFF_RY --
    at a chosen angle, and grows PAD_PROJ inward from there. The angles are not
    aesthetic: they are the local maxima of the clearance sweep in
    pad_led_clearances(), i.e. the gaps between the row ends where the crescent
    has no pixels near its edge. Move one and re-read that table."""
    o = []
    a, b = DIFF_R_G, DIFF_RY_G
    for deg in CARRIER_FIX_DEG:
        t = math.radians(deg)
        px, py = a * math.cos(t), b * math.sin(t)
        # true outward unit normal of the ellipse at t
        nx, ny = math.cos(t) / a, math.sin(t) / b
        nl = math.hypot(nx, ny)
        o.append((px - PAD_OFFSET_IN * nx / nl,
                  py - PAD_OFFSET_IN * ny / nl, deg))
    return o


def pad_wall_margins():
    """How far each pad's OUTER edge stays inside the cavity wall's outer face.

    >>> MEASURED AT THE PAD'S WIDEST RADIUS, WHICH IS THE BASE, NOT THE SHAFT.
    >>> This used to subtract PAD_W/2 and reported a comfortable +0.3 while the
    >>> base flare -- PAD_DRAFT bigger -- was 1.2 mm out through the wall and into
    >>> the dome's rib band. A margin check against the wrong radius is worse
    >>> than no check: it actively vouched for the failure.
    >>>
    >>> The geometry is clipped to the cavity envelope now, so this can no longer
    >>> go negative in the built part. It is kept as the DESIGN margin -- if it
    >>> reads negative the boss is being silently trimmed, which means the screw
    >>> has less meat around it than the numbers here suggest.
    """
    return [(deg, ell_dist(px, py, CAV_R_G, CAV_RY_G) - PAD_W / 2)
            for px, py, deg in carrier_pads()]


def pad_flare_trim():
    """How much of the BASE FLARE the cavity envelope clips off, per pad.

    Positive here is expected and intended: the flare is a gusset that only needs
    to exist on the INBOARD side, where there is room. Growing it as a full
    circle and clipping the outboard half flush is the simplest way to get "a
    reverse cone that does not break the outside plane" -- the alternative,
    pushing the whole boss further in so the untrimmed circle fits, would spend
    PAD_DRAFT of clearance at the TOP of the cavity, which is the one place the
    pad has none to spare.

    What must stay true is that the SHAFT -- the part with the screw in it -- is
    NOT being trimmed. That is `pad_wall_margins()`, and it must be >= 0."""
    r_max = PAD_W / 2 + PAD_DRAFT
    return [(deg, max(0.0, r_max - ell_dist(px, py, CAV_R_G, CAV_RY_G)))
            for px, py, deg in carrier_pads()]


def strip_stops():
    """Every end stop as (x, y) in the crescent frame -- two per non-empty row.

    A cut segment of n pixels is n * LED_PITCH of ribbon (see ribbon_cap), so the
    stops bracket that, not the LED span."""
    o = []
    for (_, n, run), y in zip(crescent_rows(), crescent_row_ys()):
        if n == 0:
            continue
        seg = run + LED_PITCH
        for sgn in (-1, 1):
            o.append((sgn * (seg/2 + STRIP_END_CLR + STOP_T/2), y))
    return o


def strip_rects():
    """Each row's RIBBON as (half_len, y, half_width) in the crescent frame.

    >>> THE RIBBON IS AN OBSTACLE IN ITS OWN RIGHT, not just its LEDs and its end
    >>> stops. It is STRIP_W (10) tall against the LED's 5.2, so it reaches
    >>> 2.4 mm further up and down than any pixel does -- and at the apex, where
    >>> the crescent is only 62.7 tall, that is the difference between a pad
    >>> sitting in clear space and a pad sitting on the strip. A pad on the
    >>> ribbon holds the plate off its seat and skews the whole air gap."""
    return [((n * LED_PITCH) / 2, y, STRIP_W / 2)
            for (_, n, _r), y in zip(crescent_rows(), crescent_row_ys()) if n]


def pad_clearances():
    """For each pad: (deg, gap to nearest LED, gap to nearest END STOP, gap to
    nearest RIBBON). Negative means the pad is standing on something.

    >>> ALL THREE, NOT JUST THE PIXELS. The first version checked only LEDs,
    >>> picked six angles with 3-8 mm of pixel clearance, and three of them
    >>> landed on a STOP -- the stops live at the row ends, which is exactly the
    >>> quiet perimeter the pads were chosen for. The second version added the
    >>> stops and the apex pad then landed on the RIBBON of the top row, which
    >>> the preview caught and the checks did not. Every obstacle, or the check
    >>> is worthless."""
    leds, stops, rects = crescent_led_xy(), strip_stops(), strip_rects()
    out = []
    for px, py, deg in carrier_pads():
        dl = min(math.hypot(px - lx, py - ly) for lx, ly in leds) \
             - LED_D/2 - PAD_W/2
        ds = min(math.hypot(max(abs(px - sx) - STOP_T/2, 0.0),
                            max(abs(py - sy) - STOP_W/2, 0.0))
                 for sx, sy in stops) - PAD_W/2
        dr = min(math.hypot(max(abs(px) - hl, 0.0), max(abs(py - ry) - hw, 0.0))
                 for hl, ry, hw in rects) - PAD_W/2
        out.append((deg, dl, ds, dr))
    return out


def pad_led_clearances():
    """(deg, worst of all three) per pad."""
    return [(deg, min(dl, ds, dr)) for deg, dl, ds, dr in pad_clearances()]


def _pad_xy(deg):
    """Where a pad at this angle lands -- the ellipse point pulled in along the
    true normal. Same maths as carrier_pads(), for one angle."""
    t = math.radians(deg)
    a, b = DIFF_R_G, DIFF_RY_G
    px, py = a * math.cos(t), b * math.sin(t)
    nx, ny = math.cos(t) / a, math.sin(t) / b
    nl = math.hypot(nx, ny)
    return px - PAD_OFFSET_IN * nx / nl, py - PAD_OFFSET_IN * ny / nl


def pad_angle_bands(step=0.25, need=1.2):
    """Every angular band where a pad clears the pixels, the end stops AND the
    ribbons by at least `need`. This is what CARRIER_FIX_DEG is picked from -- if
    a row count or a stop size changes, re-read this rather than nudging angles.

    The obstacles are gathered ONCE. Rebuilding them per angle re-solves the
    whole crescent a thousand times and takes minutes."""
    leds, stops, rects = crescent_led_xy(), strip_stops(), strip_rects()

    def worst(px, py):
        dl = min(math.hypot(px - lx, py - ly) for lx, ly in leds) - LED_D/2
        ds = min(math.hypot(max(abs(px - sx) - STOP_T/2, 0.0),
                            max(abs(py - sy) - STOP_W/2, 0.0))
                 for sx, sy in stops)
        dr = min(math.hypot(max(abs(px) - hl, 0.0), max(abs(py - ry) - hw, 0.0))
                 for hl, ry, hw in rects)
        return min(dl, ds, dr) - PAD_W/2

    bands, cur, d = [], [], 2.0
    while d <= 178.0:
        w = worst(*_pad_xy(d))
        if w >= need:
            cur.append((d, w))
        elif cur:
            bands.append(cur)
            cur = []
        d = round(d + step, 3)
    if cur:
        bands.append(cur)
    return [(b[0][0], b[-1][0], max(x[1] for x in b),
             max(b, key=lambda x: x[1])[0]) for b in bands]


def crescent_capacity_note():
    """(capacity, fitted, per-row cap). Capacity is what the crescent physically
    holds -- optical AND ribbon limits applied. If fitted < CRES_PX the target is
    not achievable at this CROWN_K and the shell has to get taller."""
    caps = [_crescent_row_cap(y) for y in crescent_row_ys()]
    return sum(caps), sum(c for _, c, _ in crescent_rows()), caps


def crescent_clearance():
    """The tightest LED-body-to-diffuser gap anywhere in the field. This is the
    number that has to stay positive -- and comfortably so, since LED_D, STRIP_W
    and DIFF_MARGIN are all still marked (?)."""
    ys = crescent_row_ys()
    return min((led_clearance(c, y)
                for (_, c, _), y in zip(crescent_rows(), ys) if c), default=0.0)


def crescent_px():
    return sum(c for _, c, _ in crescent_rows())


def crescent_leds(with_ribbon=True):
    """The crescent LEDs, and by default the RIBBON they are cut from.

    >>> DRAW THE RIBBON, NOT JUST THE DOTS. Circles alone show where the light
    >>> comes from and hide the thing that actually constrains the layout: the
    >>> strip is STRIP_W wide and each pixel carries half a pitch of ribbon
    >>> either side of it, so a row of n pixels is n * LED_PITCH of physical tape
    >>> -- a full pitch longer than the span between the end LEDs. Drawn as dots,
    >>> an 11-pixel bottom row looked fine on every sheet while its tape was
    >>> 0.5 mm too long for the cavity. Each row is now drawn as its outline with
    >>> the CUT LINES marked, one per pixel, LED centred in its own segment.
    """
    o = []
    for (w, k, run), y in zip(crescent_rows(), crescent_row_ys()):
        if k == 0:
            continue
        cy = fy(CRES_Y + y)
        if with_ribbon:
            seg = k * LED_PITCH                       # the physical tape
            x0 = W/2 - seg/2
            o.append(rect(x0, cy - STRIP_W/2, seg, STRIP_W, "phan"))
            for i in range(k + 1):                    # every cut line, ends too
                cx = x0 + i * LED_PITCH
                o.append(line(cx, cy - STRIP_W/2, cx, cy + STRIP_W/2, "hid"))
        for i in range(k):
            x = W/2 - run/2 + i * LED_PITCH if k > 1 else W/2
            o.append(circ(x, cy, LED_D, "led"))
    return o


def mic_x():
    return [W/2 + (i - (MIC_N-1)/2) * MIC_PITCH for i in range(MIC_N)]


def vent_y(i):
    return VENT_Y + i * VENT_P


def enc_pixel_xy():
    """The NeoPixel's centre in PART coordinates, as (x, depth).

    >>> ONE FLIP, IN ONE PLACE. The board hangs component-side UP under the crown,
    >>> so looking down at it you see the fab print's own view -- no mirroring.
    >>> Only the 180 deg mounting choice matters, and ENC_PIXEL_FORWARD is it.
    """
    dx, dy = ENC_PIXEL_OFF
    return (W / 2 + dx, ENC_Y + (-dy if ENC_PIXEL_FORWARD else dy))


def crown_inner_y(x):
    """Height of the crown's INNER surface at this x -- what a board mounted up
    there actually lands on.

    >>> MOVED HERE FROM gen_dome. It lived in the dome, so only the dome could ask
    >>> where its ceiling is -- and the front module, which reaches CARRIER_Z0 into
    >>> that same space, could not check its own boards against it. Shared geometry
    >>> belongs in the shared module; a fact only one part can see is a fact no
    >>> cross-part check can use.
    """
    a, b = ARCH_R - WALL, ARCH_RY - WALL
    return ARCH_Y + b * math.sqrt(max(1.0 - ((x - W / 2) / a) ** 2, 0.0))


def arch_half_chord(y, r=None, ry=None):
    """Half-width of the arch ellipse at height y (0 below the springing line)."""
    r = ARCH_R if r is None else r
    ry = ARCH_RY if ry is None else ry
    t = (y - ARCH_Y) / ry
    return r * math.sqrt(max(0.0, 1.0 - t * t)) if t <= 1.0 else 0.0


def vent_half_len(y):
    """Half-length of the louvre at height y -- a constant inset from the arch's
    INNER face, so the slot ends follow the shell's own curve."""
    return max(VENT_LEN_MIN / 2.0, arch_half_chord(y) - WALL - VENT_INSET)


def vent_slots():
    """Every louvre as (x_centre, y_centre, half_length, half_height).
    ONE list, used by the dome's cut, its clearance table, the drawings and the
    rear-wall item map -- so a slot cannot be one size in the solid and another
    in the check."""
    return [(vx, vent_y(i), vent_half_len(vent_y(i)), VENT_HH)
            for vx in vent_x() for i in range(VENT_N)]


def vent_x():
    """Centre x of each vent stack. ONE stack now, centred above the light
    pipe -- kept as a list so the dome's build loop is unchanged."""
    return [W/2]


def rear_wall_items():
    """Everything competing for the REAR WALL, as (name, x0, x1, y0, y1).
    Two features clear each other if they clear in EITHER axis."""
    o = [("UPS 3S",   UPS_WALL_X - UPS_W/2,  UPS_WALL_X + UPS_W/2,
          FLOOR_Y, FLOOR_Y + UPS_H),
         ("Flex",     FLEX_WALL_X - FLEX_W/2, FLEX_WALL_X + FLEX_W/2,
          FLEX_WALL_Y, FLEX_WALL_Y + FLEX_H),
         ("lux pipe", W/2 - LP_D/2,   W/2 + LP_D/2,   LP_Y - LP_D/2, LP_Y + LP_D/2),
         ("barrel jack", W/2 - BARREL_HOLE_D/2, W/2 + BARREL_HOLE_D/2,
          BARREL_Y - BARREL_HOLE_D/2, BARREL_Y + BARREL_HOLE_D/2)]
    for k, vx in enumerate(vent_x()):
        nm = "vent stack" if len(vent_x()) == 1 else f"vent stack {'LR'[k]}"
        # >>> THE HEIGHT USED TO BE WRONG. VENT_HH is a HALF-height, so the stack
        # >>> reaches VENT_HH above the top slot and below the bottom one, not
        # >>> VENT_HH/2. It under-reported the stack by 1 mm at each end -- which
        # >>> is exactly the kind of slack that lets a board look like it fits.
        # >>> THE WIDEST SLOT BOUNDS THE STACK, and that is the BOTTOM one now that
        # >>> they taper. Using any single slot's length would under-report the
        # >>> footprint for the others.
        _hl = max(hl for _vx, _vy, hl, _hh in vent_slots() if _vx == vx)
        o.append((nm, vx - _hl, vx + _hl,
                  vent_y(0) - VENT_HH, vent_y(VENT_N - 1) + VENT_HH))
    return o


def dome_floor_intrusions():
    """Everything the DOME reaches down into the bottom plate's airspace, as
    (name, x0, x1, d0, d1) in PLATE coordinates -- x across, d = depth from the
    front face. Anything mounted on the plate must clear all of it.

    >>> THIS EXISTS BECAUSE THE PLATE COULD NOT SEE THE DOME. The RTC was put on
    >>> the floor at (26.3, 43.7) clear of every floor item, every plate edge and
    >>> every one of the six screws -- and was still buried 0.9 mm inside the
    >>> dome's left wall rail, because no list the plate consulted contained the
    >>> rail. Two parts that share a volume have to share the description of it,
    >>> or each one is checked against a world the other is not in.
    """
    side_depths = sorted({sd for sx, sd in SCREWS
                          if abs(sd - (D - WALL - LUG_L/2)) >= 0.1})
    rail_d0 = min(side_depths) - LUG_W/2
    out = [("dome rail L", 0.0, WALL + LUG_L, rail_d0, D - WALL),
           ("dome rail R", W - WALL - LUG_L, W, rail_d0, D - WALL)]
    for sx, sd in SCREWS:
        if abs(sd - (D - WALL - LUG_L/2)) < 0.1:
            out.append((f"dome rear tab x={sx:.0f}",
                        sx - LUG_W/2, sx + LUG_W/2, D - WALL - LUG_L, D - WALL))
    # the seating ledge is a band round the whole perimeter, sitting directly on
    # top of the plate -- so it is in the way of anything standing on the plate
    b = WALL + SEAT_W
    out += [("dome seat ledge front", 0.0, W, 0.0, b),
            ("dome seat ledge rear",  0.0, W, D - b, D),
            ("dome seat ledge left",  0.0, b, 0.0, D),
            ("dome seat ledge right", W - b, W, 0.0, D)]
    return out


def plate_boards():
    """Boards mounted on the BOTTOM PLATE, as (name, cx, cd, w, d, hole_offsets).
    The RTC used to be here; it is on the rear wall now."""
    return [("TPA2016", AMP_X, AMP_DEPTH, AMP_W, AMP_D, amp_holes_part())]


SPK_UPS_CLR = 3.0    # air wanted between a speaker magnet and the battery pack
CROWN_REAR_CLR = 2.0 # air wanted behind a crown board


def depth_stacks():
    """Things that queue up along the DEPTH axis, as
    (name, front-mounted reach, rear-mounted reach, wanted air).

    >>> THIS IS THE AXIS NOTHING WAS CHECKING. Every clearance table in this file
    >>> works IN PLAN -- x against y -- because that is where most of the crowding
    >>> is. But the machine is only D deep with parts hung off BOTH faces, and two
    >>> things can clear beautifully in plan while sharing the same depth. The
    >>> speaker cans hang off the front module; the UPS hangs off the rear wall;
    >>> they overlap in x (148-193 against 120-180) and in y, so depth is the ONLY
    >>> thing keeping them apart -- and no check looked at it.
    >>>
    >>> Reach is measured from the face the part is mounted on, so a stack fits iff
    >>>     front_reach + air + rear_reach  <=  D - 2 * WALL_ish
    >>> and the required D falls straight out of the ones that do not.
    """
    return [
        # name                 front reach            rear reach   air
        ("speaker vs UPS",     FP_T + SPK_BODY_D,     UPS_D,       SPK_UPS_CLR),
        ("crown board vs wall", CROWN_Z + max(ENC_PCB, TOF_PCB_D) / 2.0, 0.0,
         CROWN_REAR_CLR),
    ]


def depth_required():
    """The smallest D that satisfies every depth stack."""
    return max(front + air + rear + WALL for _n, front, rear, air in depth_stacks())


def rear_wall_clearances():
    """Pairwise clearance on the rear wall. The barrel jack is EXPECTED to sit
    inside the UPS footprint -- the jack is on that board -- so that pair is
    skipped rather than reported as a collision."""
    items, out = rear_wall_items(), []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, b = items[i], items[j]
            if {a[0], b[0]} == {"UPS 3S", "barrel jack"}:
                continue          # (historical: the jack was ON the UPS board)
            gap = max(gap_1d(a[1], a[2], b[1], b[2]),
                      gap_1d(a[3], a[4], b[3], b[4]))
            out.append((f"{a[0]} <-> {b[0]}", gap))
    return out



# ---------------------------------------------------------------------------
# LATE RESOLUTION
# ---------------------------------------------------------------------------
# The row pitch depends on the true per-row capacity, which depends on ell_dist,
# ribbon_cap and _crescent_row_cap -- so it cannot be solved where it is
# declared. Solve it here, once everything it needs exists.
LED_ROW_PITCH = _solve_row_pitch()


# ===========================================================================
# BOARD MOUNTING -- the features every printed part needs so a PCB has
# something flat and square to land on.
# ===========================================================================
# >>> TWO RULES DRIVE ALL OF THIS.
# >>>
# >>> 1. EVERY BOARD GETS A FLAT. The crown is a cylinder and the shell walls are
# >>>    curved above the springing line; a PCB laid on either rocks on two edges
# >>>    and its connectors end up at an angle to the hole they poke through. So
# >>>    anything that mounts on a curved surface gets a local flat MILLED INTO
# >>>    THE INSIDE -- never the outside, which stays smooth.
# >>>
# >>> 2. NO SCREW HEAD IS VISIBLE EXCEPT ON THE BOTTOM. Every boss is BLIND: it
# >>>    stands proud of the inner surface and its pilot stops short of breaking
# >>>    through. Screws go in from inside, towards the shell. The only fasteners
# >>>    you can see on the finished machine are the six that pull the bottom
# >>>    plate up into the dome.
#
# M2.5 self-tappers for boards; the bottom plate keeps M3 heat-set inserts,
# because that is the joint that gets opened over and over.
BOSS_SCREW   = 2.5
BOSS_PILOT_D = 2.1        # self-tapping pilot in PETG/PLA
BOSS_D       = 6.0        # boss outer diameter -- 1.95 wall round the pilot
BOSS_MIN_WALL = 1.2       # least material left over a blind pilot
BOSS_CHAMF   = 0.6        # lead-in chamfer on the boss top

# A board sits on standoffs so its solder side clears the surface.
STANDOFF_H   = 3.0
# >>> THE ToF SITS CLOSER TO THE SKIN THAN ANYTHING ELSE, on purpose: its pinhole
# >>> is a bore through the crown and every millimetre of standoff is another
# >>> millimetre of tube in front of a 25 deg cone. It lived in gen_dome.py, which
# >>> was fine while gen_dome.py was the only thing that placed crown boards --
# >>> crown_boards() is shared now, so the standoff has to be shared too.
TOF_STAND    = 2.0        # ToF board standoff -- short, to sit near the skin

# ---- local flats on curved surfaces ---------------------------------------
# The flat is a shallow pocket cut into the INSIDE of the shell, deep enough to
# swallow the curvature across the board plus a little margin, so the board lands
# on a true plane. Depth is DERIVED from the sagitta -- see crown_sag().
FLAT_MARGIN  = 0.4        # extra depth beyond the computed sagitta
FLAT_EDGE    = 2.0        # flat oversize around the board footprint


def crown_sag(width, a=None, b=None):
    """How far the arch falls away across a chord of `width`, centred on the
    apex-most point of the span. This is the depth a local flat has to remove.

    A 25 mm board on a 101 x 74.7 arch only sags ~0.6 mm -- small, and exactly
    the kind of small that leaves a board rocking and a connector skewed."""
    a = ARCH_R if a is None else a
    b = ARCH_RY if b is None else b
    h = width / 2.0
    if h >= a:
        return b
    return b - b * math.sqrt(1.0 - (h / a) ** 2)


def flat_depth(width):
    """Pocket depth for a local mounting flat across a board of `width`."""
    return round(crown_sag(width) + FLAT_MARGIN, 2)


# ---- the Adafruit STEMMA QT mounting-hole family ---------------------------
# >>> FOUR HOLES, NOT TWO, AND THE SAME FOUR ON EVERY BOARD BUT ONE. The encoder,
# >>> the ToF and the BH1750 were each modelled with a TWO-hole pitch -- one
# >>> "(?) MEASURE" guess apiece (20.0, 20.0, 15.0). All three actually carry four
# >>> plated Ø2.5 holes, one per corner, 0.100" in from every edge, and the vendor
# >>> board files say so outright. Read out of Eagle, from the repos in QT_PCB_SRC:
# >>>
# >>>   #4991 I2C QT Rotary Encoder  25.40 x 25.40  holes 2.54/22.86 x 2.54/22.86
# >>>   #3317 VL53L0X STEMMA QT      25.40 x 17.78  holes 2.54/22.86 x 2.54/15.24
# >>>   #4681 BH1750 STEMMA QT       25.40 x 17.78  holes 2.54/22.86 x 2.54/15.24
# >>>   #5188 DS3231 STEMMA QT       25.40 x 17.78  holes 2.54/22.86 x 15.24 ONLY
# >>>
# >>> So one inset describes all of them, and the DS3231 is the sole exception --
# >>> it has the same 25.4 x 17.78 outline and the same grid, but Adafruit only
# >>> populates the TOP pair (and drills those Ø3.0, not Ø2.5). Do not "tidy" the
# >>> DS3231 into qt_hole_offsets(): the bottom pair is not there.
QT_PCB_SRC = {
    # board -> the Adafruit PCB repo the outline and holes were read out of
    "encoder": "github.com/adafruit/Adafruit-I2C-QT-Rotary-Encoder-PCB",
    "ToF":     "github.com/adafruit/Adafruit-VL53L0X-ToF-Distance-Sensor-PCB",
    "lux":     "github.com/adafruit/Adafruit-BH1750-PCB",
    "RTC":     "github.com/adafruit/Adafruit-DS3231-Precision-RTC-Breakout-PCB",
}
QT_HOLE_INSET = 2.54      # 0.100" in from EVERY edge -- the whole family
QT_HOLE_D     = 2.5       # MOUNTINGHOLE_2.5_PLATED, drill 2.5, pad 3.2


def qt_hole_offsets(bw, bh, inset=QT_HOLE_INSET):
    """The four corner mounting holes of an Adafruit STEMMA QT breakout, as
    offsets from the board CENTRE.

    >>> THESE NEED NO BOARD-TO-PART FLIP, and that is a property of the pattern
    >>> rather than an oversight worth copying. The four holes sit `inset` in from
    >>> every edge, so the set is symmetric about both centre lines and mirroring
    >>> it maps it onto itself. board_holes_part() still exists and is still
    >>> required for patterns that are NOT symmetric -- the DS3231's two holes sit
    >>> high on the board and DO flip.
    """
    return [(sx * (bw / 2.0 - inset), sy * (bh / 2.0 - inset))
            for sx in (-1, 1) for sy in (-1, 1)]


# ---- crown-mounted boards --------------------------------------------------
# The seesaw encoder sits under the knob; the ToF sits alongside it, turned
# longwise front-to-back so its short edge clears the encoder board.
# >>> ENC_FLAT_W/D AND TOF_FLAT_W/D ARE GONE, and so is gen_dome's
# >>> crown_flat_cut(). They sized a milled flat under each crown board -- an
# >>> approach abandoned long ago because the flat is a LENS with a knife edge
# >>> where its plane meets the curved inner surface, and cutting one severed the
# >>> bosses that reach up through it. gen_dome.py imported all four and called
# >>> none of them, which left four live-looking constants describing a feature the
# >>> part does not have. What actually keeps a crown board flat now is that its
# >>> four boss tips are built COPLANAR -- added material instead of removed, so
# >>> there is no lens and no knife edge. See gen_dome.py's crown board mounts.
# Offsets in PART axes: (dx across the machine, ddepth front-to-back).
# The encoder is square, so its pattern is the same either way round. The ToF is
# mounted LONGWISE -- its 25.4 axis is the DEPTH, its 17.78 axis is x -- so its
# pattern goes in that way round and NOT the other.
ENC_HOLES    = qt_hole_offsets(ENC_PCB, ENC_PCB)
TOF_HOLES    = qt_hole_offsets(TOF_PCB_W, TOF_PCB_D)

# >>> HOW FAR APART THE BOARDS GO IS SET BY THE BOSSES, NOT THE BOARD EDGES. This
# >>> is the same lesson the RTC's wall search recorded -- "the bosses are the
# >>> binding constraint, not the board" -- and the crown had not learnt it. Two
# >>> Ø6 posts need real plastic between them or they print as one blob, and the
# >>> two boards' hole rows sit at the SAME two depths (both patterns are 20.32
# >>> along the depth, both boards centred on ENC_Y), so the bosses are dead in
# >>> line and x separation is all there is.
BOSS_GAP_MIN = 2.0        # least plastic between two neighbouring bosses


def _resolve_tof_x():
    """Place the ToF outboard of the encoder by BOSS clearance.

    The encoder's outermost boss column is at W/2 + (ENC_PCB/2 - QT_HOLE_INSET);
    the ToF's innermost is TOF_X - (TOF_PCB_W/2 - QT_HOLE_INSET). Solve for the
    TOF_X that leaves BOSS_GAP_MIN between the two Ø BOSS_D posts."""
    global TOF_X
    enc_out = W / 2 + (ENC_PCB / 2 - QT_HOLE_INSET)
    tof_in = enc_out + BOSS_D + BOSS_GAP_MIN
    TOF_X = round(tof_in + (TOF_PCB_W / 2 - QT_HOLE_INSET), 2)


_resolve_tof_x()

# What the derivation above actually leaves between the two BOARD edges. Reported
# on the drawing so the number is visible; it is a RESULT now, not an input.
TOF_BOARD_GAP = round((TOF_X - TOF_PCB_W / 2) - (W / 2 + ENC_PCB / 2), 2)


def crown_boards():
    """Every board that mounts under the crown, as
    (name, centre_x, centre_depth, w_x, d_z, hole_offsets, standoff).

    >>> A LIST OF HOLES, LIKE THE REAR WALL AND THE PLATE. The crown was the last
    >>> place still describing a board with a PITCH plus an AXIS name, and it was
    >>> the only one of the three that could not represent what these boards
    >>> actually have. Two bosses under a four-hole board do not just leave two
    >>> holes empty -- they let the board pivot on the line joining them, which on
    >>> the ToF is a sensor pointing somewhere other than where its pinhole is.
    """
    return [
        ("encoder", W / 2, ENC_Y, ENC_PCB,    ENC_PCB,   ENC_HOLES, ENC_STAND),
        ("ToF",     TOF_X, TOF_Y, TOF_PCB_W,  TOF_PCB_D, TOF_HOLES, TOF_STAND),
    ]

# ---- rear-wall boards ------------------------------------------------------
# The RTC and the lux sensor had no defined mount at all until now; both are
# STEMMA QT breakouts that need somewhere flat and square on the rear wall.
# >>> ADAFRUIT DS3231 PRECISION RTC - STEMMA QT (#5188): 25.4 x 17.8 x 7.8 mm,
# >>> published on the product page. It was modelled as 25.4 SQUARE, so the board
# >>> was 7.6 mm too tall -- which only ever made the rear wall look tighter than
# >>> it is, but it was still wrong.
# >>> IT HAS **TWO** MOUNTING HOLES, NOT FOUR -- AND THAT IS NOW CONFIRMED, NOT
# >>> INFERRED FROM A PHOTO CAPTION. "Adafruit DS3231 STEMMA QT.brd" declares
# >>> exactly two: MOUNTINGHOLE_3.0_PLATEDTHIN at (2.54, 15.24) and (22.86, 15.24)
# >>> in a 25.4 x 17.78 outline. So the DS3231 sits on the same family grid as the
# >>> other three breakouts with its BOTTOM pair simply not populated. This was the
# >>> open item that held up the rear wall; it is closed.
# >>> TWO THINGS THE FAB-PRINT READING HAD WRONG: y was 14.73, not 15.24 -- half a
# >>> millimetre of boss offset, read off a drawing instead of the board -- and the
# >>> drill is Ø3.0, not Ø2.5. The Ø3.0 does NOT change the screw: these are
# >>> CLEARANCE holes and M2.5 through Ø3.0 is a normal fit, so REAR_BOARD_SCREW
# >>> keeps the RTC on M2.5 and the boss stays tapped for it.
RTC_PCB_W, RTC_PCB_H = 25.4, 17.78    # Adafruit #5188 board file -- CONFIRMED
RTC_PCB_T            = 7.8            # including the coin cell holder
RTC_HOLE_N           = 2
RTC_HOLES            = [(2.54, 15.24), (22.86, 15.24)]
RTC_HOLE_D           = 3.0            # MOUNTINGHOLE_3.0_PLATEDTHIN, drill 3.0
RTC_HOLE_P           = 20.32          # 0.8", horizontal
# >>> THE RTC IS ON THE REAR WALL. IT WENT TO THE FLOOR AND BACK, AND THE ROUND
# >>> TRIP IS WORTH RECORDING, BECAUSE THE FLOOR TRIP WAS BASED ON A SEARCH THAT
# >>> HAD GONE STALE.
# >>>
# >>> The wall search was first run when the vent slots were 18 x 8 stacked six
# >>> deep and the amp was at depth 50. It reported NO viable position and the RTC
# >>> was moved to the floor on the strength of that. But the vents were later cut
# >>> to VENT_HH 1.0 on a 4.5 pitch and the amp moved forward to depth 34 -- and
# >>> nobody re-ran the search. It was re-run and there are 294 viable positions.
# >>> A "no solution" result is only as good as the constants it was run against,
# >>> and it silently rots the moment any of them move.
# >>>
# >>> THE FLOOR WAS NEVER A GOOD HOME ANYWAY. It cost two moves -- (20,44) put two
# >>> bosses 4.5 mm ON TOP of the left fixing screws, and (26.3,43.7) then buried
# >>> the BOARD 0.9 mm inside the dome's left wall rail. That second one was
# >>> invisible to every check on the part, because the plate only ever compared
# >>> Ø6 BOSS POSTS and never the 25.4 mm board sitting on them: RTC_PCB_W was
# >>> imported into gen_bottom_plate and never once used.
# >>>
# >>> Chosen by a search over board AND all four bosses, requiring 3 mm of shell
# >>> around every boss rim and ranking on worst-case clearance. The bosses are the
# >>> binding constraint, not the board: 20 mm pitch + Ø6 spans 26 mm, wider than
# >>> the 25.4 board.
# >>>
# >>> CONSOLIDATING THE VENTS IS WHAT MADE THIS COMFORTABLE. Against the two old
# >>> vent stacks the best the wall offered was 2.5 mm, from 294 viable positions.
# >>> With the same free area stacked once above the light pipe there are 67151,
# >>> and the best is 9.0 mm -- in the upper-LEFT quadrant, which the old vent
# >>> stack L had been sitting on.
RTC_ON_FLOOR         = False
RTC_WALL_X, RTC_WALL_Y = 43.0, 114.0  # rear wall, upper left, above the Flex
                                      #   9.0 mm to the nearest neighbour
# >>> ADAFRUIT BH1750 - STEMMA QT (#4681): 25.4 x 17.78, FOUR Ø2.5 holes on the
# >>> family grid -- read out of "Adafruit BH1750.brd". It was modelled 20.0 x 18.0
# >>> on a 15.0 "(?)" square pitch: 5.4 mm too narrow, and a pitch that exists on
# >>> no Adafruit board. The real pattern is 20.32 x 12.70, which is WIDER than the
# >>> guess in x and NARROWER in y, so the four bosses moved in both axes -- the
# >>> guess was not even conservative.
LUX_PCB_W, LUX_PCB_H = 25.4, 17.78    # Adafruit #4681 -- CONFIRMED
LUX_HOLES            = qt_hole_offsets(LUX_PCB_W, LUX_PCB_H)
# The lux sensor looks through the light pipe, so its board is centred on it.
LUX_WALL_X, LUX_WALL_Y = None, None   # resolved below, from the pipe

# ---- panel-mount barrel jack ----------------------------------------------
# A flat land on the INSIDE of the rear wall, so the jack's nut pulls up square
# against a plane rather than a curve, plus clearance for the nut itself.
BARREL_LAND_D = 20.0      # flat land diameter, inside face
BARREL_NUT_D  = 16.0      # (?) across the nut's corners -- MEASURE

# ---- UPS 5V power switch ---------------------------------------------------
# >>> RESOLVED: rear wall, low and left. It was an open item from the original
# >>> layout. Low-left is below the Flex and above the floor line, reachable
# >>> without tipping the machine, invisible from the front, and it keeps the
# >>> leads short to the UPS on the right. It does not compete with anything --
# >>> that band was empty.
# >>> IT IS A ROUND BUTTON, SO THE HOLE IS ROUND. The Waveshare switch is a
# >>> panel-mount push button, not a rocker -- a rectangular cutout would leave
# >>> four visible gaps around a circular bezel and nothing for its nut to pull
# >>> against.
SW_D         = 12.0       # MEASURED body of the push button (see PANEL_FIT)
SW_HOLE_D    = SW_D + PANEL_FIT     # the opening actually cut
SW_NUT_D     = 16.0       # (?) across the nut, for the land -- MEASURE
SW_WALL_X    = 26.0       # rear wall, left of the Flex
SW_WALL_Y    = 12.0       # low, level with the jack
SW_RIB       = 1.5        # retaining land around the opening, inside
# >>> THE LANDS HAVE TO STOP ABOVE THE BOTTOM PLATE. Both the switch and the barrel
# >>> jack sit at y=12 with lands ~20 across, so their pads reach down to y=2.5 and
# >>> y=2.0 -- straight through the plate, whose top face is BP_T=4. The plate then
# >>> rides 1.5-2 mm proud on two little rings, which is what Andy felt.
# >>> They cannot simply be made narrower: the land exists to give the NUT a flat
# >>> seat, so it has to be at least the nut across corners (16), which already
# >>> reaches exactly y=4. So the pads are CLIPPED FLAT where the plate is instead;
# >>> a nut loses the bottom sliver of its seat and gains a machine that closes.
LAND_PLATE_CLR = 0.3      # air between a clipped land and the plate's top face

# ---- bottom plate ----------------------------------------------------------
FOOT_POCKET_T = 1.0       # recess depth for a stick-on foot
FOOT_CLR      = 0.4       # pocket oversize on the foot diameter
# >>> AMP_HOLE_P (a 20.0 "(?) MEASURE" guess) USED TO LIVE HERE, and it is what
# >>> every consumer actually imported -- 800 lines below the real 22.86 that had
# >>> already been read out of the board file. Two names for one dimension, and
# >>> the placeholder won. Deleted: there is now exactly one amp hole pattern,
# >>> AMP_HOLES, and one transform that puts it in part coordinates.


def _resolve_lux():
    global LUX_WALL_X, LUX_WALL_Y
    LUX_WALL_X, LUX_WALL_Y = W / 2, LP_Y


_resolve_lux()


# >>> SCREW SIZE PER BOARD, because the boards do not agree. The UPS is drilled
# >>> Ø3.1 -- M3 -- while the little STEMMA breakouts are Ø2.5. Driving them all
# >>> from one BOSS_PILOT_D gave the UPS an M2.5 pilot under an M3 hole: the screw
# >>> would go in, but a 200 g battery pack hanging on four sloppy fits is not
# >>> something to leave to chance.
REAR_BOARD_SCREW = {"UPS": 3.0, "lux": 2.5, "RTC": 2.5}
REAR_PILOT_D = {3.0: 2.5, 2.5: 2.1}          # self-tapper pilot per screw size


def board_holes_part(holes, bw, bh):
    """Board-local hole coordinates -> offsets from the board CENTRE, in part
    coordinates.

    >>> THIS EXISTS BECAUSE THE FLIP HAS BEEN MISSED TWICE. Vendor files give hole
    >>> positions in the board's own frame, seen from the COMPONENT side. Every
    >>> board in this build is installed with its component side facing the
    >>> machine's FRONT -- the matrix's LEDs point out, the rear-wall boards stand
    >>> off the wall facing forward -- so each board's frame is 180 deg from the
    >>> part's and one in-plane axis inverts on the way in.
    >>> Skipping it mirrors the pattern. On the matrix that put the posts on the
    >>> wrong diagonal; on a two-hole board like the DS3231, whose holes sit on one
    >>> horizontal line 5.83 above centre, it would put them 5.83 BELOW.
    >>> One function, so there is one place to be right.
    """
    return [(hx - bw / 2.0, -(hy - bh / 2.0)) for hx, hy in holes]


def rear_wall_boards():
    """Every board that mounts on the rear wall, as
    (name, centre_x, centre_y, w, h, hole_offsets). Used by the dome to place
    bosses and by the clearance table to prove they do not overlap.

    >>> hole_offsets IS AN EXPLICIT LIST NOW, NOT A PITCH. It used to be a single
    >>> number and the dome built a FOUR-boss square from it -- fine for a board
    >>> with four symmetric holes, wrong for anything else. The DS3231 has TWO
    >>> holes on one horizontal line, so two of its four bosses were standing on
    >>> bare PCB. A pitch cannot express a hole pattern; a list of holes can.
    """
    return [
        ("Flex",  FLEX_WALL_X, FLEX_WALL_Y + FLEX_H / 2, FLEX_PCB_W, FLEX_PCB_H,
         None),
        ("UPS",   UPS_WALL_X,  FLOOR_Y + UPS_H / 2,      UPS_W,      UPS_H,
         board_holes_part(UPS_HOLES, UPS_W, UPS_H)),
        ("lux",   LUX_WALL_X,  LUX_WALL_Y,               LUX_PCB_W,  LUX_PCB_H,
         LUX_HOLES),
        ("RTC",   RTC_WALL_X,  RTC_WALL_Y,               RTC_PCB_W,  RTC_PCB_H,
         board_holes_part(RTC_HOLES, RTC_PCB_W, RTC_PCB_H)),
    ]
