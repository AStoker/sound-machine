# 3D-printed parts

Three reference sheets and two printable parts, all generated, all sharing one
source of truth.

| Sheet | File | What it answers |
|---|---|---|
| 1 | [`enclosure-drawing.svg`](enclosure-drawing.svg) | the shell — top / front / side / rear, assembled and exploded |
| 2 | [`enclosure-internals.svg`](enclosure-internals.svg) | the front module, the slide-up joint, the fixings, the chassis |
| 3 | [`enclosure-wiring.svg`](enclosure-wiring.svg) | the I2C chain, direct GPIO, power, and where each board sits |

| Part | File | Status |
|---|---|---|
| Matrix tray | [`matrix-tray.stl`](matrix-tray.stl) | printable — **no longer in the assembly**, the front module carries the matrices itself |
| **Front module** | [`front-module.stl`](front-module.stl) | printable — 250.8 × 182 × 16.7 |
| Dome, bottom plate, knob, LED carrier | — | still to do |

```sh
# sheets (stdlib only)
python3 gen_drawing.py && python3 gen_internals.py && python3 gen_wiring.py
for f in enclosure-drawing enclosure-internals enclosure-wiring; do
  rsvg-convert -b white -z 2 $f.svg -o $f.png
done
# solids (need manifold3d)
../.venv/bin/pip install manifold3d trimesh matplotlib
../.venv/bin/python gen_tray.py && ../.venv/bin/python gen_front_plate.py
```

Code layout — **no sheet and no solid invents a dimension**:

```
enclosure_geom.py   every parameter, every derived value, the part outlines
drawlib.py          SVG primitives, dimensions, leaders, sheet chrome
gen_drawing.py      sheet 1        gen_internals.py    sheet 2
gen_wiring.py       sheet 3        gen_tray.py         matrix-tray.stl
                                   gen_front_plate.py  front-module.stl
```

`enclosure_geom.py` also carries the clearance model. Every generator ends in
`ALL CLEAR` or a problem count: `gen_drawing.py` checks the facade stack and the
rear wall, `gen_internals.py` the fixing lugs, `gen_front_plate.py` the solid
(see below). Change a component and re-run — the envelope re-derives and every
check re-runs.

## How the solids are checked

A render proves nothing. `gen_front_plate.py` validates three ways, and only
prints `ALL CLEAR` if all three pass:

- **Mesh sanity** — watertight, consistent winding, and **exactly one connected
  body** (more means a feature is floating in space).
- **Envelope interference, negative.** Every component that this part carries
  gets its swept volume intersected with the printed solid; the result must be
  *zero* mm³. The matrix pair (with its mounting holes punched out, since the
  posts are *supposed* to be in them), the backpacks behind it, **all 288 LEDs**,
  the acrylic, the air gap, both speaker bodies, all four side nubs, the mic
  board, and the dome's groove band.
- **Feature presence, positive.** Interference tests can't notice a retention
  feature that quietly vanished into a boolean, so a 1 mm probe checks that
  plastic actually *exists* at every locating post, seating pad, rib, spine,
  clip beam and clip hook — that each hook overhangs the board *above* its back
  face but not below — and that the clock aperture is genuinely open.

The LED check earned its keep immediately: it caught the seating pads sitting on
the corner LEDs, which a bounding box around the LED field had waved through.

Plus a containment guard: the whole solid is intersected with the module outline
before export, so a boss can never hang off the edge. It reports how much it
trimmed, and that has to be zero too.

---

# Front module

`front-module.stl` — **250.8 × 182 × 16.7**, one printed part carrying the whole
facade. Print **face down**: the facade is then the bottom layer (the one surface
anyone sees) and every boss, wall and clip grows upward off the bed, so there is
nothing to support. Fits a 256 mm bed with 5.2 mm to spare.

| Zone | What the part does |
|---|---|
| **Crescent** | R117 through aperture, a 1.5 mm ledge, then an R118.5 pocket the opal acrylic drops into **from behind**, then a 12 mm air gap inside a 2 mm cavity wall. The wall stands 12.7 mm proud of the back face and is the part's main stiffener. |
| **Clock** | ONE open 84 × 23 aperture — no per-pixel holes. Behind it the two matrices seat on the back face: **2 locating posts + 2 seating pads per board**, then **six clips**, two on each long edge and one at each end. |
| **Speakers** | Ø40 grille through, locating ribs above and below (not on the flanks — the nubs are there), and a 7 mm post beside each flank with a Ø2.5 pilot. The M3 goes in **from behind**, through the speaker's nub, into the post. |
| **Mic array** | 4 × Ø2.5 ports on Ø4.5 raised gasket lands, in a 110.8 × 12.8 × 2 channel, with two M3 pilot bosses. |

## Why there is no tray and no pocket

**The two matrices are only loosely soldered to each other.** A pocket locates
the *pair* — and the pair is exactly the thing that isn't rigid, so the solder
joint would end up carrying the alignment and would work loose. Instead each
board is located by its **own** two posts through its own Ø2.0 diagonal holes,
and the six clips clamp both boards flat against the facade.

The seating pads sit at **mid-width in the strips above and below the LED
field**, not on the board corners: the corners fall inside the LED field's
bounding box, and a pad there lands on the outermost LEDs. The 288-LED
interference check is what caught that.

Room for the clips came free. The matrix/mic cluster used to be squeezed to
1 mm and 2 mm gaps back when it set the enclosure height — it doesn't any more
(the speaker seats do, at y=56), so ~9 mm of slack was sitting unused. Spending
4 mm above and 4 mm below buys clips on all four sides and costs no height.

## ⚠️ Measure these before printing (top of `gen_front_plate.py`)

| Param | Default | What to check |
|---|---|---|
| `SPK_NUB_PROJ` | 4.0 mm | **The important one** — it is a *width driver*. Every +1 mm is +4 mm of body width and +2 mm of height. |
| `MTX_STACK_GAP` | 5.0 mm | Matrix back → backpack front (your header pins). |
| `MIC_BOSS_X` | 50.0 mm | Seeed doesn't publish the linear-4 array's hole positions. |
| `DIFF_GAP` | 12.0 mm | Diffusion air gap — ~0.7 × the LED pitch is the starting point. Test-print a crescent corner. |
| `CLOTH_T` | 0.6 mm | Grille cloth per layer; it goes through the dome groove with the module. |

Snap features can't be simulated for fit. Test-print one corner of the clock
zone and tune `CLIP_REACH`, `CLIP_RAMP`, `CLIP_T` and `CLIP_W`.

---

# Dual CharliePlex matrix snap-in tray

> **⚠️ Superseded in the assembly.** The front module now carries the two
> matrices directly — posts through each board's own holes, six clips all round
> — so there is no tray in the build any more. This part still works and is
> still generated; keep it if you want the matrices as a self-contained module,
> and note that its front face has **per-pixel light tunnels**, which the front
> module deliberately does not.

`matrix-tray.stl` — a mount that holds **two butted Adafruit IS31FL3731 16×9
CharliePlex matrices *and* their two driver backpacks** as one solid unit, with
a **flat front face** (for mounting flush against cloth) and all retention on
the back. No screws, no heat-set inserts — it snaps together.

Generated with `manifold3d`; validated **watertight, 2-manifold, genus-288**
(the 288 light windows) — imports into OrcaSlicer with no repair.

Board geometry is from Adafruit's EAGLE files (LED matrix + STEMMA backpack), so
outlines, LED positions, and hole positions are exact, not estimated.

## How it holds together

Stack, front → back: `cloth │ front face │ matrices │ gap │ backpacks │`

- **Flat front:** 1.5 mm face (`FACE_T`) with one Ø2.0 light window per LED
  (288 total). The matrices sit right behind it, LEDs pointing into the windows.
  Kept thin on purpose — a deep face turns each window into a light pipe and
  kills off-axis visibility (Ø2.0 × 1.5 mm ≈ ±34° half-angle). Raise toward
  ~2 mm for more per-LED isolation / a stiffer face.
- **Matrices:** *located* (not retained) by **4 plain alignment posts** through
  each matrix's two diagonal Ø2.0 holes — the only holes that line up. The posts
  have a small chamfered lead-in tip and **no barb** (barbs are hard to print
  cleanly on FDM). The matrices are held forward by the clamped stack, not by
  the posts.
- **The gap** between matrix and backpack is set by *your own* inter-board
  header pins — the tray just spans it (parameter `STACK_GAP`).
- **Backpacks:** retained by **4 cantilever snap fingers** on the long walls.
  Each finger tip is a **triangular hook**: a shallow lead-in ramp the board
  rides over, then a 45° retaining facet that clicks behind the backpack's back
  face and pulls the whole stack forward against the front. 45° keeps the
  overhang FDM-printable; the angled facet gives more hold-down than a round bump.
- **Wires:** notches in both end walls, **18 mm wide to clear both STEMMA QT
  ports** on each backpack.

Everything is captured between the flat front and the rear snaps, so the stack
can't fall apart and the wires aren't stressed.

## Print & assemble

1. Import `matrix-tray.stl` into OrcaSlicer. Print **front-face-down** on the
   bed — gives the smoothest flat face against the cloth, and the posts/fingers
   print upward with no supports.
2. Push each **matrix** in from the back until its two holes snap onto the
   posts and it seats against the front face.
3. Push each **backpack** in until the snap fingers click behind it.

## ⚠️ Measure these before printing (top of `gen_tray.py`)

The design is exact for the boards, but three things depend on *your* build:

| Param | Default | What to check |
|---|---|---|
| `STACK_GAP` | 5.0 mm | **The important one.** Clear gap between matrix back and backpack front (your header-pin height). If this is wrong the snaps won't clamp. |
| `PCB_T` / `BP_T` | 1.6 mm | PCB thicknesses (calipers). |
| `LED_D` | 2.0 mm | Window Ø. Must clear the LED package so the matrix seats flat — measure an LED; enlarge if they don't nest into the tunnels. |

Also confirm: **two backpacks** (one per matrix)? And which wall the connectors
exit — I notched both ends; tell me if a side wall needs a slot instead.

Snap features can't be simulated for fit — **test-print one corner** (or the
whole thing) and tune if needed: `LIP_REACH` (how far the hook grabs),
`RAMP_RUN` (insertion ease), `FINGER_W`/`SLOT_W` (finger stiffness). The matrix
posts are `POST_D` (loosen if they bind in the Ø2.0 holes).

## Regenerating

```sh
python3 -m venv venv
venv/bin/pip install manifold3d trimesh matplotlib scipy
venv/bin/python gen_tray.py       # writes matrix-tray.stl (+ section preview)
```

All dimensions are parameters at the top of `gen_tray.py`.

---

# Enclosure reference drawing

`enclosure-drawing.svg` — a 1:1, third-angle drawing of the **shell**, for
modelling in Fusion 360. Not a released drawing; it is a dimensioned reference
that also does the packaging arithmetic. Regenerate with:

```sh
python3 gen_drawing.py                     # no dependencies
rsvg-convert -b white -z 2 enclosure-drawing.svg -o enclosure-drawing.png
```

## The form

A letter **"D" lying on its long flat side, extruded along the depth**: flat
bottom, straight sides, and a semicircular top of radius `W/2`. The crown is
therefore a **cylinder**, not a sphere — it curves in FRONT and is flat in SIDE.

The one rule that drives everything: **the shell arc and the LED crescent are
concentric**, both centred on `(W/2, CRES_Y)`. So the arc radius *is* `W/2`, and
the rim between shell and crescent is `W/2 − CRES_R`.

## Nothing is hand-set — W and H are derived

Only **D** is chosen. The facade is assembled bottom-up and the envelope falls
out of it, which is what makes collisions impossible by construction:

```
W = 2 × (plate edge + clr + speaker body + clr + half the tray)
H = W/2 + CRES_Y                                          concentric D
CRES_Y = floor + max(tray, speaker seat) + gap + mic array + gap
```

**⚠️ Widening also heightens.** Because the arc radius is `W/2`, every 2 mm of
extra width adds 1 mm of height. The **50 mm speaker body** is what sets W:

| If the speaker body were | W | H |
|---|---|---|
| 40 wide | 238 | 179.6 |
| 45 wide | 248 | 184.6 |
| **50 wide (actual)** | **258** | **189.6** |
| 55 wide | 268 | 194.6 |

…and the **speaker's side nub is a width driver in its own right**, because each
one needs a post beside it. This is the number still to be measured:

| Nub projection | Seat/post width | W | H |
|---|---|---|---|
| 2.0 | 4.35 | 250 | 185.6 |
| 3.0 | 5.35 | 254 | 187.6 |
| **4.0 (assumed)** | **6.35** | **258** | **189.6** |
| 5.0 | 7.35 | 262 | 191.6 |
| 6.0 | 8.35 | 266 | 193.6 |

### The diffuser and the LED field are two different radii

| | value | what it is |
|---|---|---|
| `CRES_R` | **R117** | the **diffuser** arc — the concentric maximum, 12 mm rim. What you see. |
| `LED_R` | **R96** | the arc the **48 pixels** sit on. Solved for density. |
| `CRES_FADE` | **21 mm** | the gap between them at the apex — **unlit on purpose** |

48 px cannot fill R117 without spreading thin (rows would stop ~40 mm short). Rather than shrink the visible crescent to match, the diffuser
stays full-size and the LED field sits inside it: the glow dies out before the
edge and the acrylic turns that into a soft falloff instead of a hard boundary.
Per-row fade to the diffuser edge runs **40–54 mm**.

`CRES_FILL_MIN` sizes the LED field (0.84 → R96); set it to `0` to push the LEDs
out to the diffuser arc and kill the fade. Two related fixes:
**row pitch is now 16.7** (it used to be stretched to 20.6 against 16.7 columns),
and **row counts are solved for a constant end margin** rather than
proportionally — proportional let one row reach within 3 mm of the arc while its
neighbours stopped 18 mm short. `gen_drawing.py` prints the table every run.

Width is set by what sits side by side on the facade:
`edge | clr | seat+post | 50 body | seat+post | gap | half the 110 array`. The
**seat counts** — an early version had the ring hanging off the edge of the
module. The **110 mm array sits 2 mm above the matrix tray**, one tight cluster,
with the speaker boxes flanking the whole thing.

The module is **wrapped in cloth**, so the groove takes cloth + module + cloth
(5.6 for a 4 mm module) and the module outline shrinks by one cloth thickness.

## Clearance check

Every run prints the facade stack and a pass/fail clearance table, ending in
`ALL CLEAR` or `*** n COLLISION(S) ***`. Change any component and re-run: the
envelope re-derives and the table re-checks.

## Sheet layout

Two blocks, everything grouped for Inkscape/Illustrator or as a
Fusion canvas underlay:

```
ASSEMBLED   ASM-TOP, -FRONT, -SIDE, -REAR
EXPLODED    EXP-TOP, -FRONT, -SIDE
  each: dome | knob | front-plate | crescent-leds | bottom-plate
        matrix-tray | internals | trajectory | balloons | dims
```

The **REAR** view is a true flat face — the body is an extrusion, so the back is
the same "D" as the front. Everything on it is **centred on the width**: the Ø4
light pipe for the BH1750 lux sensor, the Ø11 DC barrel jack (which lines up with
the centred UPS pack), and the 4 vent slots above them. It sits bottom-centre on
the sheet, out of projection, because there is no room for it beside the side
view; it is labelled as such.

Parts: **1** dome · **2** front module · **3** bottom plate · **4** matrix tray
(the sub-assembly above) · **5** knob.

## The front module is one part — but the diffuser is not

**Yes, make it one piece.** Everything that has to stay in register with
everything else — matrix aperture, speaker grilles, mic ports, diffuser opening —
now lives on a single part, so there are no tolerances stacking across a frame,
a bracket and a baffle. It also becomes a proper speaker baffle.

Two things that fall out of that decision:

- **The facade went 3 → 4 mm.** Two Ø40 drivers bolted to an unsupported 3 mm
  plate will flex and buzz. There are also ribs from each baffle ring out to the
  perimeter. It is a baffle now, not a cover.
- **The diffuser stays separate.** You cannot print an even diffuser. The printed
  part is the *frame and the diffusion cavity*; the Glowforge-cut white opal
  acrylic drops into a pocket from behind, then the LED strip seats on the back
  of the cavity. Stack is facade 4 │ acrylic 3 │ **air gap 12** │ strip 3.

**The air gap is the number most likely to be wrong.** 12 mm is ~0.7× the 16.7 mm
LED pitch, the usual starting point for not seeing 48 individual dots through
opal. Test-print one corner of the crescent before committing.

## How it goes together

1. Front module **slides UP** into the dome's side grooves from below. Nothing
   retains it yet.
2. It seats against the lip — 4.5 mm of its edge captured all round, 0.5 mm
   sliding clearance.
3. **Bottom plate goes on.** Its top face is the module's datum: the module's
   bottom edge lands on it and can no longer drop.
4. **Six M3 screws** pull the bottom plate up into heat-set inserts in the dome
   bosses. No fastener touches the facade.

⚠️ **The fixings cannot be symmetric.** The floor is fully occupied, so every
boss is threaded into a gap between the drivers, the matrix tray, the UPS and the
Flex. `gen_internals.py` prints each boss's tightest clearance. The rear-right
pocket is 74 mm wide between the UPS and the wall — a 66 mm Flex leaves no room
for a boss beside it, so the right rear is unclamped. If the measured Flex is
≤60 mm, a seventh boss fits there.

The **TPA2016 does not go on the floor** — there is no room left. It mounts on
the rear wall above the UPS, which also gives the shortest speaker leads.

## Two touch pads, one per shoulder

Copper strips ~40 × 22 mm bonded to the *inside* of each upper shoulder at
y = 112, just behind the ToF, so you can tap either side of the device.

**Both pads share one pin** (`GPIO4/D3`, TOUCH4). Self-capacitance sensing
measures the whole electrode net, so two pads on one net behave as a single
electrode that happens to be split in two — touching either half gives the same
delta. One binary sensor, one threshold, no OR logic.

⚠️ **Join the two leads at the MCU, not across the crown.** Each lead drops down
the inside of its own flank to the floor and they meet at the XIAO. The wire
count is identical either way, and it keeps a ~200 mm antenna out of the crown —
which is exactly where the SK6812 data line, the I2S lines and the STEMMA chain
all run. A wire taken straight across the crown would couple all of that
directly into the sensor. This is the decision that makes or breaks it.

What sharing costs: baseline capacitance roughly doubles while the finger delta
does not, so relative sensitivity drops (still comfortably usable), and a
side-to-side mismatch can't be trimmed out with per-pad thresholds.
**`GPIO2/D1` (TOUCH2) is kept free as the escape hatch** — if one side ends up
noticeably duller, splitting to two channels is one wire at the MCU plus a few
lines of YAML.

The crown is a **cylinder**, so a flat strip wraps onto it with no distortion as
long as its long axis runs front-to-back — which is why the pads are 40 mm along
the depth and only 22 mm across the arc.

Practical notes: thin the wall locally to ~1.6 mm behind each pad; calibrate with
`esp32_touch: setup_mode: true`. And watch for false triggers — the shoulders are
also where you grip the device to move it. If that bites, require a short hold
rather than a tap.

The **knob** is a full pebble — an ellipse of revolution truncated by a shallow
cut, Ø34 at its widest, meeting the crown on a Ø28 flat, 20 mm tall, blind Ø6 ×
15 bore with a D-flat. `KNOB_BASE_D` controls how much of the pebble is cut away;
raise it toward `KNOB_D` for more of a hemisphere.

The **ToF** sits on the crown just right of the knob, board turned **longwise
front-to-back** so its 17.8 mm edge clears the 25.4 mm encoder breakout.

## ⚠️ What the drawing found

| | Constraint |
|---|---|
| **Width ↔ height are coupled** | The arc radius *is* `W/2`, so you cannot trade height for width — see above. |
| **The speaker body sizes the box** | 50 × 45 × 22 sealed boxes, not bare cones. The 50 mm width sets W, which sets H. |
| **The mic array spans above the cluster** | At 110 mm it is wider than the 91 mm tray, so it cannot sit between the speakers. |
| **The UPS board must stand up** | It is 60 × 93; 93 mm will not lie down in a 59 mm interior. Standing also aligns its barrel jack with the rear cutout. |
| **The floor carries only the UPS** | Flex and amp both mount on the *rear wall* — the Flex vertically above the UPS, the amp flush beside it. The sides are only vertical below the springing, and the speakers own all of that. |
| **Bottom-row pixels were burying themselves** | The crescent baseline is a row *centre*, so it has to clear the speaker seats by the LED radius as well as the gap. |
| **Speakers hang on side nubs** | Not a baffle bolt pattern. One nub per side, landing 7 mm behind the front face, so the module grows a post beside each flank — and the post, not the body, is the widest point. |
| **48 px can't fill a rim-maximal crescent** | Capacity grows with area but the strip doesn't. So the diffuser (R117) and the LED field (R96) are separate radii, and the 21 mm between them is an intentional fade band. |
| **A centred vent stack sits behind the Flex** | It would block the slots and bake the board. The vents are two stacks flanking the UPS, which also puts them right above the amp. |
| **The lux pipe has a ~5 mm slot to live in** | UPS to y=97, Flex from y=102. A centred pipe gets exactly that gap — Ø3, 1 mm clear each side. Any tighter and it has to move to the crown. |
| **Fixings are wall lugs, and asymmetric** | The floor is fully spoken for. No lug fits on the front edge at all — the plate's front edge is captured by the ledge and the module instead. |
| **Charge is a barrel jack** | 12.6 V 2 A, not USB-C. The only USB-C is the XIAO's internal flashing port. |

### …and what the *solid* found, which the drawing could not

Building the real part surfaced a class of error the 2D views are blind to:

| | Constraint |
|---|---|
| **The edge budget is the dome's RIB, not the outline** | The module slides up a groove, so the outer `RIB_W` of its **back face** must stay plain along both flanks and the arc. On the flat, a boss 1 mm inside the outline looks fine; in reality it jams the assembly. Four features were inside the band — a speaker post by 4.35 mm, the spine by the full 5, the speaker ribs by 1.35, the cavity wall by 0.10. |
| **`RIM_MIN` is derived, not an aesthetic choice** | `REVEAL + BOSS_EDGE + DIFF_MARGIN + CAV_WALL` is the smallest rim the shell can carry, because the diffusion cavity wall has to clear that same rib band. The 12 mm "look" minimum only wins when it is larger. |
| **`RIB_W` 5 → 3 paid for itself** | The keep-out is multiplied four times across the width, so 2 mm off the rib gave back 4 mm of body. A 3 mm rib behind a 4 mm plate is ample — the bottom plate already traps the module. |
| **The bottom edge is exempt from all of it** | It is the open end the module slides in through. Treating the keep-out as a plain ring around the outline flagged 2143 mm³ of false positives until the bottom strip was excluded. |
| **The two matrices are not one part** | They are only loosely soldered to each other, so a pocket — which locates the *pair* — is the wrong tool. Each board gets its own locating posts, and six clips on all four sides clamp the pair. |
| **Pads cannot go on the board corners** | The corners are inside the LED field's bounding box; a Ø4 pad there lands on the outermost LEDs. Only the strips above the top row and below the bottom row are genuinely clear, so the pads sit at mid-width. |
| **Clip roots need real estate the tight cluster had spent** | 1 mm below the matrix and 2 mm above it was fine when the cluster set the height. It does not — the speaker seats do, at y=56 — so ~9 mm of slack was sitting unused. Spending 4 mm above and below buys clips on all four sides for free. |
| **A rib down the speaker flanks would foul the nubs** | The nubs stand 4 mm off the body at mid-height. Locating ribs are top-and-bottom only; the posts do the locating in x. |

### Sourced vs. still guessed

Sourced from datasheets: speaker **50 × 45 × 22**, mic array **110 mm / 33 mm
pitch**, UPS board **60 × 93**, charger **12.6 V 2 A**.

Measured off the actual parts: **speaker side nub 7 mm behind the front face**;
**Flex core 52 × 70 × 20 deep**, **110 mm** over its jack and mic-ribbon
connectors, holes **45 × 63** pitch (from 42 × 60 inside-edge to inside-edge with
2 mm edge-to-hole-outside, which gives Ø3 on both axes — a consistency check that
passed).

Still marked **(?)** and able to move real geometry: the **speaker nub
projection** (4 mm assumed — worth ±4 mm of body width per mm, see the table
above), the **UPS depth with cells fitted** (~24 assumed), the **mic array board
width**, the **diffuser air gap**, and **where the sensor chip sits on your
VL53L0X breakout**.
