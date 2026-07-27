# 3D-printed parts

Three reference sheets, all generated, all sharing one source of truth:

| Sheet | File | What it answers |
|---|---|---|
| 1 | [`enclosure-drawing.svg`](enclosure-drawing.svg) | the shell — top / front / side / rear, assembled and exploded |
| 2 | [`enclosure-internals.svg`](enclosure-internals.svg) | the front module, the slide-up joint, the fixings, the chassis |
| 3 | [`enclosure-wiring.svg`](enclosure-wiring.svg) | the I2C chain, direct GPIO, power, and where each board sits |

```sh
python3 gen_drawing.py && python3 gen_internals.py && python3 gen_wiring.py
for f in enclosure-drawing enclosure-internals enclosure-wiring; do
  rsvg-convert -b white -z 2 $f.svg -o $f.png
done
```

Code layout — **no sheet invents a dimension**:

```
enclosure_geom.py   every parameter, every derived value, the part outlines
drawlib.py          SVG primitives, dimensions, leaders, sheet chrome
gen_drawing.py      sheet 1        gen_internals.py  sheet 2
gen_wiring.py       sheet 3        gen_tray.py       matrix-tray.stl
```

`enclosure_geom.py` also carries the clearance model. `gen_drawing.py` prints the
facade-stack check and `gen_internals.py` prints the fixing-lug check; both end
in `ALL CLEAR` or a collision count. Change a component and re-run — the envelope
re-derives and both checks re-run.

---

# Dual CharliePlex matrix snap-in tray

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
the rim between shell and crescent is `W/2 − 80`.

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

| If the speaker body were | W | H | Crescent R |
|---|---|---|---|
| 40 wide | 200 | 160 | R88 |
| 45 wide | 210 | 165 | R93 |
| **50 wide (actual)** | **220** | **170** | **R98** |
| 55 wide | 230 | 175 | R103 |

The **crescent scales with the body** (`R = W/2 − 12`) so the concentric rim stays
at 12 mm however wide the parts push things. That keeps the look fixed — but it
changes the pixel count, which is a **firmware change**: at R98 the crescent is
**58 px, not 48**, and draws ~2.3 A instead of ~1.9 A at the 65% cap.
`gen_drawing.py` prints the new row table every run.

The **110 mm mic array sits 2 mm above the matrix tray** — one tight cluster —
and the speaker boxes flank the whole thing. Putting the array above the
speakers instead would save width but waste facade height, which is the trade
this layout deliberately refuses.

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
| **Fixings are wall lugs, and asymmetric** | The floor is fully spoken for. No lug fits on the front edge at all — the plate's front edge is captured by the ledge and the module instead. |
| **Charge is a barrel jack** | 12.6 V 2 A, not USB-C. The only USB-C is the XIAO's internal flashing port. |

### Sourced vs. still guessed

Sourced from datasheets: speaker **50 × 45 × 22**, mic array **110 mm / 33 mm
pitch**, UPS board **60 × 93**, charger **12.6 V 2 A**.

Still marked **(?)** and able to move real geometry: the **UPS depth with cells
fitted** (~24 assumed), the **ReSpeaker Flex core board size** (Seeed doesn't
publish it — the design reserves a ~52 × 31 bay instead of a fitted pocket), the
**speaker fixing-hole pitch**, the **mic array board width**, the **diffuser air
gap**, and **where the sensor chip sits on your VL53L0X breakout**.
