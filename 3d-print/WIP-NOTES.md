# WIP — resume here

**All nine generators are `ALL CLEAR`, and `check_docs.py` is `ALL SYNCED`.**
Firmware and all four documents are in sync with the geometry.
Nothing is committed.


```sh
python3 gen_drawing.py && python3 gen_internals.py && python3 gen_wiring.py
../.venv/bin/python gen_front_plate.py
../.venv/bin/python gen_led_carrier.py
python3 check_docs.py          # <- prose vs geometry; ends in ALL SYNCED
```

## `check_docs.py` — new, and the reason it exists

Numbers live in five places: `enclosure_geom.py` (truth),
`packages/lighting.yaml` (the firmware's copy of the LED layout), and three
markdown docs. Prose does not fail a unit test, so every rework left documents
describing a machine that no longer existed — the 258-wide split enclosure was
still documented as current three revisions after it stopped being built.

`check_docs.py` asserts the facts and flags stale values, and **history is
allowed**: a stale-value rule only fires when the old value appears outside a
line that marks itself historical ("used to", "no longer", "there is no", …).
Keep using those markers when writing a why-it-changed note. It does not judge
whether prose is *good* — read the diff too.

## Envelope

| | before | now |
|---|---|---|
| envelope | 202 × 64 × 160.02 | **202 × 64 × 155.69** |
| front aspect | 1.26:1 | 1.30:1 |
| CROWN_K | 0.72 | **0.74** |
| MIC_Y0 / MIC_Y1 | 70.7 / 82.7 | **64.35 / 76.35** |
| CRES_Y | 87.3 | **80.95** |
| crescent ellipse | 89 × 60.72 | **89 × 62.74** |
| LED rows | 10/10/10/8/7/3 = 48 | **10/10/9/8/7/4 = 48** |
| row pitch | 11.0 (1 mm gap) | **10.4 — the ribbons BUTT** |
| pocket ledge | 1.5 | **2.4** (free; hides the acrylic notches) |
| min LED → diffuser | −0.58 (overhang) | **+2.95** |
| front module | 194.8 × 152.4 × 22.2 | **194.8 × 148.1 × 21.33** |
| parts | 5 | **7** (LED carrier + generated diffuser) |

Both printed parts fit a 220 bed whole. Front module mesh: watertight, one
connected body, 70.3 cm³. Carrier: watertight, one body, 25.2 cm³.

## The six failures were one bug, and not where the notes were looking

`gen_front_plate.py` contained **the whole build twice.** Lines 120–323 were a
copy of 324–541; Python ran both and the second copy *reassigned* `body`, so the
first copy's output was silently discarded.

The two copies differed in exactly one block — the speaker mount. The **dead**
copy had it correctly rotated. The **live** copy still had posts on the flanks at
`px = sx ± (SPK_BODY_W/2 + SPK_FIT + pw/2)` → **x = 5.25 / 56.95** and mirrors.
That is why the previous session's probe kept finding walls at x ≈ 5.1 / 58.8
after the file "confirmed" the ribs were gone: the fix had landed on the dead
copy.

Fixed by deleting the duplicate and rotating the live mount: posts above and
below on the body centreline, no ribs on any face.

> If a probe reports a wall at x ≈ 5 or ≈ 57 again, check the speaker mount block
> first — and check the file only builds `body` once.

**A second, real collision was hiding under it.** The short inboard stiffening
ribs ran at `y = SPK_Y`, which *is* the matrix mid-height now that the clock is
centred on the speakers — 49.8 mm³ straight through the boards, into 288 LEDs
and through the end clips. Nowhere left to put them (0.77 mm to the end clip), so
they are replaced by a **second spine below the matrix**, mirroring the one above.

## Measured values that were guesses

Four `(?)` constants became real numbers this session, and two of them moved:

| | was | measured |
|---|---|---|
| `LED_PITCH` | 16.7 (nominal 60 LED/m) | **16.5** (cut line to cut line) |
| `STRIP_W` | 10.0 (?) | **10.0** confirmed |
| `LED_STRIP_T` | 3.0 (?) | **2.13** |

`SPK_NUB_PROJ`, `SPK_NUB_W`, `SPK_NUB_H`, `CLOTH_T`, `DIFF_T` and `DIFF_GAP` are
still `(?)`. **`SPK_NUB_H` now sets `SPK_POST_W`**, which is what buys the mic
clearance — measure it before printing.

## Why 45 pixels, not 48

Every earlier layout measured the **LED body**. The thing that has to fit the
cavity is the **ribbon**: a cut segment of n pixels is `n × LED_PITCH` long, not
`(n−1) ×`, because the cut lines sit half a pitch outboard of the end LEDs and
you cannot trim past them without losing the solder pads. On the bottom row that
is 6.9 mm more than the LED span, and it did not fit — 11 px is a 181.5 mm strip
into a 181.0 mm cavity.

The ribbon is also `STRIP_W` tall against the LED's 5.2, so what must fit is a
**rectangle**, and its binding corner is the top one.

That cap is now in `ribbon_cap()` and folded into `_crescent_row_cap()`, so it
cannot be missed again. Capacity at CROWN_K 0.74 is **45**. Fitting 48 needs
0.80 → H 161.75, which is *taller* than the design was before this session. 45
was the deliberate call; three pixels get cut off the 48-px reel and not laid.

`_solve_row_pitch()` also had to change: it used to stop at the first pitch whose
*chord-based* capacity beat a target, which after the ribbon cap went in still
read "enough room" at 11.5 while the real layout held only 42. It now maximises
true capacity and lands on 11.0.

## The crescent solver measures true distance now

At CROWN_K 0.72 the top LED body sat **0.58 mm outside** the diffuser. Every
check read clear because they all measured horizontally (chord) and vertically
(apex) — and on an ellipse the binding case is **diagonal**.

`ell_dist()` returns true point-to-ellipse distance (bisected stationary
condition). `crescent_rows()` allocates on that, with rows forced
**non-increasing** bottom-first — without that constraint the solver returns
things like 10/10/9/10: every pixel legal, silhouette obviously wrong.

## Part 6 — the LED carrier (`gen_led_carrier.py` → `led-carrier.stl`)

A 2.5 mm plate carrying the five strip segments at a controlled standoff, screwed
to the back of the front module. Print **face down** (strip side on the bed) — a
warped carrier is a varying air gap and that is visible through the diffuser.

Z stack from the facade's front face:

```
facade front        0
acrylic front       1.50   DIFF_LIP
acrylic back        4.70   + DIFF_REBATE
LED emitting face  16.70   + DIFF_GAP    = CAV_Z, cavity wall back
strip back          18.83   + LED_STRIP_T = CARRIER_Z0, carrier seat
carrier back        21.33   + CARRIER_T   == FM_DEPTH
```

The cavity wall runs to `CARRIER_Z0`, not `CAV_Z` — one strip thickness past the
LED plane — so it shrouds the ribbon and its back face is the carrier's seat.
`DIFF_LIP` and `CAV_Z` moved into `enclosure_geom.py`; two files each deriving a
z stack from a constant only one of them owned is how the last drift bugs started.

**Fixing: 6 × M2.5 into pads on the INSIDE of the cavity wall.** Alternatives
considered and rejected:

- *ears reaching outward onto the rim* — only **0.9 mm** of rim is free outside
  the cavity wall before the dome's rib keep-out. Making room means RIM_MIN
  12 → ~16, which shrinks the crescent to 85 × 58.7 and drops it to five rows.
- *pillars from the facade floor* — 12 mm columns inside a lit cavity.
- *captured by the dome, no screws* — locates the plate, never clamps it.
- *cantilever / snap fit*, as used for the clock matrices — **does not work
  here.** A clip gripping the plate's edge must flex *outward*, into that same
  0.9 mm. Clips deflecting *inward* need the plate inside the cavity, and then it
  cannot seat on the wall's back face, which is the air gap's datum. And clips
  hold a plate wherever the worst clip decides: over a 185 mm span on FDM, six
  screws pulling onto a hard seat is the difference between an even glow and a
  bright band. Screws also keep the five soldered segment joints serviceable.

The pads also buttress what is otherwise a 2 mm × 19 mm unsupported fin.

**Pad shape is FDM-driven.** The module prints face down, so anything widening as
it rises overhangs. Each pad starts at the acrylic pocket floor on a **45°
underside ramp** growing out of the wall (self-supporting — no support inside the
optical cavity, where scarring would show through the acrylic), then **narrows**
going up: Ø9.5 at the base, Ø6.5 at the seat. The flare is a gusset at the root.

Three things the pads got wrong first, all now fixed and all now checked:

1. **Built before the cuts** — the acrylic-pocket / air-gap bore sliced them away,
   leaving a 1.13 mm stub with an 8 mm pilot drilling into air. The presence
   probe passed because it sampled inside that stub. *A single probe near a
   feature's tip cannot tell a boss from a lid.* Now sampled at three heights
   plus a pilot depth/breakthrough pair.
2. **Ran down to the facade** — 607 mm³ into the opal acrylic's pocket; the disc
   could not drop in.
3. **The air-gap clash subtracted a plain cylinder** as a stand-in. Once the pad
   grew a taper the stand-in stopped matching and the check reported its own
   approximation error. It now subtracts the exact solid the part is built from.

**M2.5, not M3, deliberately.** An M3 pad is 8 mm across and at 8 mm the lowest
usable angle is 20°, which leaves the plate's bottom corners — and the widest,
most visible LED row — hanging off a fixing 19 mm away. M2.5 shrinks the pad to
6.5 and opens a band at 7.5°, right beside those corners.

**Stops, not channels, and only 3 mm across.** Row pitch 11.0 against a 10.0
ribbon leaves 1.0 mm for a dividing wall — 0.5 mm a side, under one nozzle width.
And a stop the full ribbon width (12) blocked *every* usable pad angle below 20°,
because the stops live at the row ends, which is exactly the perimeter the pads
need. A 3 mm nub at the row's centre height stops the segment just as well.

**There is no pad at the apex.** 90° has the most room from the pixels of
anywhere on the wall — and the top row's **ribbon** runs straight through it. A
check that looked at pixels alone passed it; the preview caught it. `pad_
clearances()` now tests pixels, end stops **and** ribbons, and `pad_angle_bands()`
prints the viable bands each run. **Re-read that table rather than nudging
`CARRIER_FIX_DEG` by eye.**

## Checks that were measuring the wrong thing

- `CLR_SPK_MIC` was `MIC_Y0 − SPK_SEAT_Y1`; now `MIC_Y0 − SPK_Y1` — body to
  array, vertical.
- `CLR_NUB_MIC` was the same y check. The array passes *beside* the post now, so
  it aliases `CLR_POST_MIC` — an **x** check (9.9 mm).
- "cavity wall clear of the speaker **rib**" measured `SPK_RING_W` (3.0). There is
  no rib; the tallest thing above the body is the post at `SPK_POST_H_Y` (6.0).
  It read 3 mm more clearance than the part had.
- The `left / right locating rib` presence probes are gone — those ribs do not
  exist and were passing by accidentally hitting the stiffening rib at `SPK_Y`.
  Replaced with an **outboard flank must be bare** probe.
- `gen_wiring.py` drew the crescent with `semi()` — a true **semicircle** of
  radius `CRES_R` — making it 26 mm taller on sheet 3 than on sheets 1 and 2.
- `SPK_RING_W` is marked vestigial in `enclosure_geom.py`. Nothing built reads
  it. Do not size anything from it.

## Firmware — done

`packages/lighting.yaml`: `num_leds: 45`, `leds_per_row[] = {10, 10, 9, 8, 6, 2}`,
comment block rewritten for the measured strip and the ribbon constraint.
`soundmachine.yaml` header no longer says "half-circle".

> **Row 5 is 2 pixels** (was 4 on the old circular arc). The apex is nearly bare,
> and rows are only 11 mm apart, so vertical gradients have ~2/3 the travel they
> used to. **The Circadian Sunrise effect should be re-checked against this** —
> it fills whole rows bottom-up and was written for a fuller apex.

## Drawings now show the ribbon, not just the dots

`crescent_leds()` draws each row's **tape outline with its cut lines** — one per
pixel, LED centred in its own segment. Drawn as circles alone, an over-long row
looked fine on every sheet while its tape was 0.5 mm too long for the cavity.
The carrier preview does the same.

Also fixed on the sheets: `gen_internals.py` was drawing the **pre-rotation
speaker mount** (side posts on the horizontal axis, flank seat rings, flank
stiffening ribs) and note g still read "hangs on side nubs". `gen_wiring.py` drew
the crescent with `semi()` — a true **semicircle** — making it 26 mm taller on
sheet 3 than on sheets 1 and 2.

## Still open

- Measure `SPK_NUB_H` / `SPK_NUB_PROJ` / `SPK_NUB_W` before printing.
- `DIFF_GAP` (12) is still a guess — tune on a test print. It is the one number
  most likely to need changing, and it moves `CARRIER_Z0` with it.
- The 2-pixel apex row: if it reads badly, CROWN_K 0.80 restores 48 px for
  +6 mm of height.
- `.png` files are NOT regenerated by the scripts — they are rendered separately
  from the `.svg`s (`cairosvg`, scale 3).


## Late changes (same session)

**Rows butt now.** The pitch floor was `STRIP_W + 1`; it is `STRIP_W` +
`STRIP_ROW_GAP` (0), and the solver lands on **10.4**. That recovered the three
pixels lost to the ribbon constraint — **48 again**, on the same shell height.
Recovering them via `CROWN_K` would have cost 6 mm of height.

**The acrylic could not be fitted, and nothing had noticed.** The carrier pads
stand inside the cavity wall over z = 4.7..18.8. The pane's *home* is in front of
all of it, but it has to travel the full depth of the cavity to get there — past
the pads. Un-notched it simply will not go in.

Fixed as **ledge + notches**:
- `DIFF_MARGIN` 1.5 → **2.4**, which is free: `RIM_MIN = REVEAL + BOSS_EDGE +
  DIFF_MARGIN + CAV_WALL` = 12.0 = exactly `RIM_MIN_LOOK`, so the pocket grows
  outward into the rim's spare 0.9 and **the lit crescent does not shrink**.
- `PAD_DRAFT` 1.5 → **0**. A round flare grows both ways: outward through the
  wall (1.2 mm into the dome's rib band) and inward, 1.5 mm deeper into the
  pane's path — i.e. 1.5 mm more notch on show. The 45° ramp already is the
  gusset, so the flare went.
- New **`gen_diffuser.py` → `diffuser.svg`**, a 1:1 Glowforge cut file with the
  six notches placed from the same `carrier_pads()` the module is built from.

**3.5 mm of each notch still shows past the aperture**, at six points. Hiding
them completely needs the aperture pulled in ~5 mm, which costs 8 pixels
(48 → 40). They sit behind opal acrylic *and* grille cloth in the dimmest part of
the field, so they should read as slight local dimming rather than as cuts.

### Three more checks that were lying

1. **The pads were built before the cuts** — the air-gap bore sliced them to a
   1.13 mm stub over a hole, with an 8 mm pilot drilling into air. The presence
   probe passed because it sampled inside the stub.
2. **`pad_wall_margins()` measured the shaft radius**, not the base flare, and
   reported +0.3 while the flare was 1.2 mm out through the wall. There is now a
   geometric clash test as well, and the pad is *clipped* to the cavity envelope
   so it cannot break the outer plane whatever draft it is given.
3. **`check_docs.py` banned "48 px"** because 48 was the superseded value that
   day. When the count went back to 48 it failed every correct document. The
   stale set is derived from the geometry now.

The pattern is the same each time: **the check was written around the answer it
expected, not around the thing it was meant to prove.**


## Pad ramp + notch shape (final pass)

**The ramp had a floating tip.** A straight cone on the pad's own axis tapers to
a point `PAD_OFFSET_IN` = 1.55 mm clear of the wall, with nothing under it — the
bore removed everything below `PAD_Z0`. Unbuildable on FDM, and it looked fine in
section. The apex is now buried `APEX_BURY` into the wall and the ramp is the
convex hull of that apex and the shaft base — a skewed half-cone that grows out
of the wall, every layer attached.

> `connected bodies == 1` does NOT catch a floating tip: it is still joined to
> the shaft above it. New probe: at three heights up each ramp there must be
> material AT the wall's inner face.

**The diffuser notches are round.** The pane sits in front of the pads, so each
notch is a straight-through hole in the diffuser that leaks undiffused light. It
only has to clear a cylinder, and the pane travels straight along z — so a
circular bite of `PAD_W/2 + clearance` is the exact minimum. 31.3 mm² vs 42.0 for
the square bite: **26% less open area**, 186 mm² instead of 252 over six. It also
hugs the pad, so the clear-glue fillet is a constant gap.

Getting `gen_diffuser.py` right took four attempts, each caught by a check rather
than by eye: depth measured from the origin instead of along the normal (notches
came out as *tabs*); wrong winding order (self-crossing path); arc samples still
drawn across the notch mouth; and arc endpoints taken from the tangent alone, so
they were not on the circle. Verified by area against closed form, a
self-intersection sweep, and a pad-clearance check — the last of which failed
once for comparing SVG-space points against model-space pads.


## Parts 1, 3 and 5 — dome, bottom plate, knob

All solids now live in **`models/`**; drawings, cut files and previews stay
beside the code. `enclosure_geom.MODEL_DIR` is the one definition.

| part | file | size | vol |
|---|---|---|---|
| dome | `models/dome.stl` | 202 × 155.7 × 64 | 146.8 cm³ |
| front module | `models/front-module.stl` | 194.8 × 148.1 × 18.8 | 71.4 cm³ |
| bottom plate | `models/bottom-plate.stl` | 196.4 × 58.4 × 6.6 | 45.3 cm³ |
| LED carrier | `models/led-carrier.stl` | 186.1 × 69.8 × 4.7 | 25.8 cm³ |
| knob | `models/knob.stl` | Ø34 × 20 | 13.2 cm³ |

All watertight, one connected body each, all on a 220 bed.

### Decisions taken
- **Power switch**: rear wall, low and left. Open since the original layout; that
  band was empty (below the Flex at y=16, above the floor) and it keeps the leads
  short to the UPS.
- **Feet**: recessed pockets, 12 Ø × 1 deep. Locates them and guarantees they
  cannot be stuck over a screw counterbore.
- **Board fixings**: M2.5 self-tappers into printed bosses. The bottom plate
  keeps M3 heat-set inserts — that joint gets opened repeatedly.

### The RTC had to leave the rear wall
Placed at (178, 108) one of its four bosses landed **outside the shell** — the
arch is down to a 73 mm half-width there and the boss wanted 87. A search over
the whole wall then found **no** position clearing the UPS, Flex, both vent
stacks, the jack and the lux pipe. It is on the **floor** now, left of the amp,
which is also a shorter I2C hop.

### Three dome bugs, all caught by the mesh check
1. **Bosses grew into the wall** (+z instead of −z), so every pilot was drilled
   inside solid plastic — sealed voids, which showed up as eleven extra connected
   bodies with *negative* volume.
2. **Gussets in the wrong axis.** Printed rear-wall-down the vertical axis is
   DEPTH; the first version ramped in y, where nothing was unsupported, and
   pushed into the bottom plate's space.
3. **Gussets escaped the envelope** — the rear pair ran 8.6 mm out behind the
   machine. Bounding box read 72.6 against a 64 design depth. There is now a
   containment guard and a bbox assertion, matching the front module's.

Plus: crown bosses floated because the flat cut removed the ceiling they hung
from, leaving coplanar faces. Fixed by cutting the flats first and letting the
bosses overlap into the remaining material.

### Still to measure
`ENC_HOLE_P`, `TOF_HOLE_P`, `RTC_HOLE_P`, `AMP_HOLE_P`, `LUX_HOLE_P` are all
`(?)` guesses at 20/15 mm, and `SW_W`/`SW_H`, `BARREL_NUT_D`, `RTC_PCB_*`,
`LUX_PCB_*` likewise. **Every board mount depends on them.** Measure before
printing the dome or the plate — the crown mounts especially, since a wrong hole
pitch there means reprinting the whole shell.


## Rear wall and bottom, reworked

Five corrections, all from looking at the part rather than the numbers:

- **Barrel jack moved LOW** (y 95 → 12), centred in width. A lead entering half
  way up the back of a bedside object drapes across it. This forced the **Flex up
  from y=16 to y=22** to clear it — which also deepens the amp's floor slot from
  12 to 18 mm, pure gain.
- **The switch is round.** It is a panel-mount push button, not a rocker; a
  rectangular cutout left four gaps around a circular bezel and nothing flat and
  concentric for its nut. Now Ø12 with a Ø19 land.
- **Vents are louvred and much smaller** — 18 × 2.0 instead of 30 × 5, twelve
  instead of eight, and each slot RISES a full wall thickness going inward. A
  level line of sight enters the outer opening and lands on the slot's own top
  face; you can only see in from ~35° below. Verified on the built solid: 9/9
  level sight-lines blocked, and the channel open along its own axis.
- **Touch pads are pockets, not holes.** The first version cut the full wall and
  put two 22 mm windows in the top of the machine. It now removes the annulus
  between the inner surface and `d_outline(TOUCH_WALL)`, thinning 2.5 → 1.6 and
  leaving the outer skin untouched. Verified by probing along the arch normal.
- **The bottom is a continuous LIP with local TABS**, not six free-standing
  blocks with stepped ramps under them. The lip is the seating ledge the plate
  already lands on; a tab is that lip made locally taller where a screw goes.
  The screw runs UP through the plate into the tab. It also prints better: the
  lip is a continuous fin over the full depth, so only the tabs' bed-facing ends
  need a ramp, and the rear tabs need nothing at all.

### Three modelling traps, all now guarded
1. **An invalid manifold in a union destroys everything.** manifold3d signals
   failure with volume 0 and an *infinite* bounding box; unioning one yields
   nothing, and the dome silently exported a 0-triangle STL. `union()` now
   validates every part and raises with the offending index.
2. **Subtracting two outlines with the same `ybot`** puts coincident edges on
   their flat bottoms. Fine at full width; once a ramp step shrinks the annulus
   to ~2 mm it degenerates. `YBOT_OUT` / `YBOT_IN` keep them apart.
3. **The perimeter band does not exist across the bottom middle.** Both outlines
   run to the floor there, so their difference is empty — and the two rear tabs
   at x=55 and 105 sit exactly in that gap. They are plain blocks on the rear
   wall now.

A check that samples the wrong line is worse than no check: the louvre's axis
rises `VENT_RISE` across `WALL + 1`, not at 45°, and a 45° ray reported it
blocked when it was open.


## Dome, second correction pass

- **Rear tabs moved off the barrel jack** (x 55/105 → 45/82). The jack dropped to
  y=12 with a 20 mm land spanning x 91..111 and the tab at 105 sat right behind
  it. That in turn pushed the **amp forward** (depth 50 → 34): the tab at 82
  reaches to depth 49.5 and the amp spanned 40..60, a 10.5 mm overlap.
- **The tabs now have screw holes.** They were cut with `cyl()` — a *Z*-axis
  cylinder — using each tab's DEPTH as though it were a height. The "hole" was a
  horizontal bore floating in the wrong place and the tabs were solid. The screw
  comes UP through the plate, so the hole runs along **y**.
- **The side-tab notch is gone.** It was never designed: the profile intersected
  the perimeter band with a rect spanning the WHOLE width, so one tab produced
  material on BOTH flanks and the bottom corner radius carved a notch out of
  each. Now one clean block per side.
- **Round holes.** The encoder shaft, the ToF pinhole and the knob's seating pad
  were all built with `slab()`, which extrudes an (x,y) section along z — fine
  for the rear wall, square for anything aimed at the crown. New `ycyl()` helper
  puts them on the vertical axis. Verified by measuring each bore on its axes
  *and* its diagonal.
- **No more floating ToF tabs, and no crown flats at all.** A flat is the lens
  between a plane and the curved inner surface, and it has a knife edge where
  they meet. Cutting one severed its own bosses — they reach up through it — and
  every attempt to trim the cut around them left coincident or near-tangent
  faces: two bodies, then a non-watertight mesh that three parameter sweeps could
  not clear. It was not buying anything either: across the encoder's 20 mm hole
  pitch the crown falls **0.367 mm**, so an unflattened board tilts 1.05°, moving
  the shaft 0.28 mm over its 15 mm bore against 0.50 mm of clearance. Both boards
  now simply follow the arch, each boss tip the same short standoff below its own
  local ceiling — which is what was wanted for the ToF anyway. The knob still
  lands square on its own round pocket in the **outer** skin.

### `manifold3d` conventions, learned the hard way
- `rotate()` is applied about the ORIGIN. Rotate first, translate second.
- `rotate((-90, 0, 0))` maps +z to +y.
- An invalid result has volume 0 and an **infinite** bounding box, and unioning
  one destroys everything downstream. `union()` validates and raises.
- Subtracting two outlines that share a `ybot` puts coincident edges on their
  flat bottoms; thin results degenerate.

Six new checks guard all of this: bore roundness on axes vs diagonal, one run of
material per side tab, and a screw hole up every tab.


## Third correction pass — tabs, crown, drawings

**Six distinct tabs, and the ramps are what the "notch" was.** Each side tab had
a 45° support ramp trailing it toward the bed, `LUG_L` deep. The two side tabs
sit only 4 mm apart (spans 29..43 and 47..61), so a 12 mm ramp off the first ran
straight through the second and the pair merged into one long blob with a step in
it. There is no room for both: 32.5 mm of usable depth against 40 mm of
tab-plus-ramp.

The ramps are gone. Those six now overhang, and that is the right trade — they
are small, they sit at the **open bottom** of the shell, and support under them
is the most accessible support anywhere in the part. A merged blob you cannot
fix; two minutes with pliers you can.

**The ToF's hole pair was on the wrong axis.** The board is mounted LONGWISE so
its narrow edge clears the encoder, which means its holes are separated along the
**depth**. Treated as an x separation, one ToF boss landed 2.9 mm *inside* an
encoder boss — and both sat outside the board's own 17.8 mm width. A hole pitch
wider than the board it belongs to is impossible; that was the tell. Now 10.5 mm
of clearance.

**Drawings.** Three things were never on any sheet, and one was drawn wrong:

- the **power switch** — not drawn at all;
- the **crown bosses** — not drawn at all, which is precisely why the ToF/encoder
  overlap went unseen;
- the **vents** — drawn as plain rectangles with no hint they are louvres;
- the **UPS and the Flex** — drawn on the CENTRELINE in both the front and rear
  views, several revisions after they went side by side.

All fixed, and `check_docs.py` now has drawing-drift rules: each generator must
*reference* the switch, the crown bosses, the louvres and the rotated speaker
posts, and no off-centre rear-wall board may be drawn at `W/2`. That last rule
caught a second stale UPS in the front view immediately after being written.

Six more geometric checks on the dome: bore roundness measured on axes *and*
diagonal, one run of material per side tab, exactly two separate tabs per side
wall, crown bosses not intersecting, and each hole pitch fitting its own board.


## Fourth pass — the rail, and the groove that was blocked

**One rail per side, not two tabs — a straight reversal.** Six distinct tabs
sounded right and, printed rear-wall-down, was wrong: two separate shelves on the
same wall leave an unsupportable island between them, in a pocket you cannot
reach into once the shell is up.

A single rail spanning both screws and running back to meet the **rear wall** is
strictly better. In this orientation it is a continuous vertical fin growing off
the bed, so it has **no overhang at all** and needs no support — where even the
two-tab version needed some. It is stiffer, and it still gives two screw points
per side. The rear pair stay separate blocks; they project forward off the rear
wall, which is straight up off the bed.

> The check that asserted "exactly 2 separate tabs" now asserts "ONE continuous
> rail that reaches the rear wall". Worth noting a check can encode a decision
> that later turns out wrong — it is not automatically right just because it is
> automated.

**The seating ledge was blocking the front module.** It ran the full depth, and
across the groove it reached `WALL + SEAT_W` = 5.5 mm in while the module's edge
sits at `REVEAL` = 3.6 — so it stuck **1.9 mm into the module's path** and the
module could not slide up at all. It blocked the single assembly move the whole
joint exists for, and every other check passed while it did.

The ledge now starts at `LIP_T + SLOT_W`, behind the groove. Nothing is lost: the
plate's front edge was never carried by the ledge — it is captured between the
ledge behind it and the front module's own bottom edge in front, exactly as the
notes always said.

**New check: the module's swept travel.** Its outline, extruded through the
groove's z band and dragged from below the shell up to its seated height, must
intersect zero dome material. Verified it fails correctly: putting the ledge back
across the groove reports 16 mm³ in the way.

That is the check this part most needed and never had. Fit was being inferred
from static clearances; nothing tested the *motion*.
