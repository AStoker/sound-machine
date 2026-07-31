# WIP — resume here

**All nine generators are `ALL CLEAR`, `check_docs.py` is `ALL SYNCED`, and
`verify_exports.py` is `ALL EXPORTS MATCH`.** All six solids are watertight,
one body each. Firmware and all four documents are in sync with the geometry.
Nothing is committed.

## Latest session — the sensor hole patterns were all wrong

The encoder, ToF and BH1750 each had an invented **two**-hole pitch. All three have
**four** holes, and all three vendors publish the Eagle file that says so. Fixing
that turned up two collisions the old model could not see (bosses 0.59 mm apart,
and a 10.7° tilt on the ToF), and closed the last open item on the rear wall. Full
account at **"The hole pitches were never pitches"** at the end of this file.

## Previous session — the three boards are finally *held*

Their hole patterns had been in the docs for a while. Nothing was using them.

**The UPS had no fixing at all.** Four M3 bosses now, on the real 46 × 86
pattern, and boss pilots are sized **per board** (`REAR_BOARD_SCREW`) rather than
from one global `BOSS_PILOT_D` — the UPS drills Ø3.1, so it wants M3, and a 200 g
pack on four M2.5 screws in oversize holes is not a detail to hand-wave.

**A pitch cannot describe a hole pattern.** `rear_wall_boards()` and
`plate_boards()` returned a single `hole_pitch` and the generators built a
**four-boss square** from it. Right for a board with four symmetric holes; wrong
for the DS3231, which has **two**, side by side — so two of its bosses stood on
bare PCB and would have held the board off the two that mattered. Both functions
now return explicit `(dx, dy)` offset lists, and `check_docs.py` asserts the
*shape of the data*, because that is where the bug lived.

**Two independent bugs on the amp, and the first one hid the second.** There were
two constants for its hole spacing: the measured `AMP_HOLE_PITCH = 22.86` read out
of Adafruit's board file, and a stale `AMP_HOLE_P = 20.0  # (?) MEASURE`
placeholder **800 lines further down** — and the placeholder was what every
generator imported. Under that, both bosses sat on the board's **depth
centreline** while both holes are 8.26 mm off it, because the amp lies with its
long axis across the machine and the bosses never followed it round. The board
could not have gone on at any pitch. `amp_holes_part()` is now the one transform,
and it is checked as a **rigid motion**: the hole-to-hole span and each hole's
four edge distances have to survive it. Both broken forms were re-introduced to
confirm the check fails (−6.34 for a swap, −8.25 for the original centreline bug).

## The front module reaches into the dome, and nothing was checking it

Andy spotted it: the crescent baffle runs `CARRIER_Z0` = 18.83 mm back from the
facade, so the first ~19 mm of the dome's interior **is not free space** — but the
encoder and ToF hang from the crown at a depth picked before that baffle existed.
Measured: **encoder 77.8 mm³, ToF 55.4 mm³** of board buried inside the front
module. The leading 1.53 mm of each 25.4 mm board.

Neither part could see it. The dome checks its own features, the front module
checks its own, and the interference lived in the gap between them.

**`ENC_Y`/`TOF_Y` are derived now**: `CROWN_Z = CARRIER_Z0 + CROWN_BAFFLE_CLR +
board/2` = 33.53, up from a hand-picked 30.0. The boards move whenever the baffle
does — and the baffle has moved twice this week. Interference: **0.0 / 0.0**.

Two structural changes came with it:

- **`crown_inner_y()` moved to `enclosure_geom`.** It lived in `gen_dome`, so only
  the dome could ask where its own ceiling is — and the part intruding into that
  space could not check itself against it. A fact only one part can see is a fact
  no cross-part check can use.
- **The check lives in the intruding part.** `gen_front_plate.py` now measures
  every crown board against its own solid, because it is the part that knows how
  far it reaches. Verified by re-breaking to the old depth: `FAIL 179.56` /
  `FAIL 127.71`.

**The lux sensor did not need lowering.** Worth measuring before moving: the
encoder's lowest point is y = 142.20, the lux board's top is 128.89 — **13.31 mm
apart in height, and 10.27 mm in depth**. They clear in both axes at once, so the
move would have bought nothing.

## The baffle floor is drafted, and the ribbon clash is gone

Row 0's ribbon hangs 2.4 mm below the crescent baseline and sat **703 mm³** inside
the bar closing the bottom of the cavity. Lowering that bar bodily would push it
into the mic array directly beneath, so instead the floor **keeps the baseline at
the facade and slopes outward as it goes back** toward the carrier, where there is
nothing underneath. Measured off the STL:

| z | 2.0 | 5.0 | 8.0 | 12.0 | 16.7 |
|---|---|---|---|---|---|
| drop | 0.02 | 0.08 | 0.84 | 1.84 | **3.02** |

The mic channel ends at z = 5.0, where the drop is 0.08 mm. Interference: **0.00**.

The carrier's skirt grew too: `CARRIER_LIP` is now a named term (1.5 mm past the
ribbon, was 0.6), so the skirt is 3.9 and **overlaps the baffle floor by 0.9 mm**.
That overlap is the light seal — backing the strip stops it peeling, but sealing
it means the skirt must continue past the module's floor so there is no straight
line from the strip's glowing edge to the outside. `gen_led_carrier.py` checks
both numbers together, since the two parts have to move together or not at all.

### The ramp's end point cost 0.6 mm of drop

Built as two lofts and a subtraction — a ring is not convex, so hulling it would
fill the cavity solid; outer and inner are each convex and loft exactly.

First version lofted the inner bore to `CARRIER_Z0 + 1.0`, using the `+1` purely
as a cutting overrun. **But the overrun is inside the loft**, so it stretched the
ramp over 15.13 mm instead of 12.0, and the floor was still 0.02 mm above the
ribbon where the strip begins. 703 mm³ became **0.18** — small enough to look like
a rounding artefact and not be. The ramp now finishes at `CAV_Z`, the shallowest z
the ribbon occupies and therefore the binding one, and holds flat beyond.

## Vents — obround, and following the arch

Three equal 72 mm slots stacked read as a rectangle pasted onto a curved shell.
Now each slot's ends sit a **constant 40 mm in from the arch's inner face** — a
true offset of the contour rather than a scaled copy, so the ends trace the arch
and the stack narrows exactly as the shell does:

| slot | y | length | arch inner half-chord |
|---|---|---|---|
| 0 | 133 | **59.96** | 69.98 |
| 1 | 138 | **45.50** | 62.75 |
| 2 | 143 | **27.60** | 53.80 |

Ends are **obround** — semicircular caps of radius `VENT_HH`, so the profile is a
true stadium rather than a rectangle with dents. A square end is a stress raiser
in a thin shell and the spot where an FDM perimeter doubles back and blobs. Still
one hull of two sections: a stadium is convex, so the hull of the two end stadiums
is exactly the swept slot.

`VENT_W` is **deleted**. There is no single slot width any more, and leaving the
name around would invite something to keep using it — the clearance table, the
drawings and the dome's own "bosses clear every opening" check all read
`vent_slots()` now, so a slot cannot be one size in the solid and another in the
check.

Open area drops **432 → 266 mm²**. Verified off the exported STL by sectioning the
rear wall at mid-thickness: the three loops measure 59.96 / 45.50 / 27.60 × 2.00,
exact, with 53-point outlines where a rectangle would have 4.

## Matrix — pin gutters, and why the inset stopped being a free choice

Two requests that pull against each other: shallower window grid, **and** gutters
for the trimmed header pins. The pins protrude from the board's **LED-side** face,
and the only material in front of that face is the lip — behind the board is
already pocket. So a gutter can only be cut **forward, into the lip**, out of the
same budget the inset is being reduced from. Picking 1.3 by hand and cutting a
0.95 gutter left 0.35 mm of facade and failed the check.

So `MTX_INSET` is now **derived**: `MTX_GUTTER_D + MTX_FACADE_MIN` = **1.40**.
Measure the pins shorter and it drops on its own.

**The real gain is bigger than 1.5 → 1.4.** Today the pins are what the board
rests on, so the LED plane sits at inset + pin height ≈ **2.3 mm** behind the
facade. Gutter them and the PCB face reaches the lip: **1.40**. That is what kills
the light bleed — each LED goes back inside its own window instead of leaking
sideways behind the lip.

Details worth remembering:

- **The gutters are derived from the LED field, not from a vendor header
  coordinate.** I don't have the matrix's fab print, so rather than guess where
  the 0.1" row sits, each gutter takes the whole margin between the board edge and
  the first LED window. Any row in that margin is covered wherever it is.
- **Each locating post needed a pedestal.** The posts are 1.905 mm from a
  horizontal board edge — inside the gutter band — and a post is attached to the
  part *only* at its base on the lip. Guttering under one turns it into a loose
  cylinder floating in the pocket. `MTX_POST_COLLAR = 0.7` keeps a Ø3.25 island
  that reaches 0.79 mm past the gutter into solid lip. The "connected bodies == 1"
  check is what would have caught it.
- **0.45 mm of facade is the visible-surface floor, not the structural one.** Two
  layers at 0.2 would hold, but PLA at 0.4 glows and this is the front face. Worth
  a look on the test print: if you see two faint bands along the top and bottom of
  the clock, that is what they are.

### The grid's boundary cells had no walls

Andy spotted it in the model: 288 cells with **0.74 mm** walls between them, and
**0.30 mm** walls closing the top and bottom rows. At a 0.4 nozzle that is one
sub-nozzle trace, so the boundary cells slice as open — the grid visibly stops
having joining walls at its edges.

Cause: `MTX_GUTTER_WEB = 0.3`, a keep-out I picked for the gutter without ever
comparing it to the web the grid already uses. It is now **derived** —
`MTX_LED_PITCH - MTX_WINDOW` — so the perimeter wall is the same wall as every
inner one and cannot become the odd one out again. The gutters narrow to 2.30 /
2.04 mm, still covering a 0.1" header row at 0.5–1.8 mm from the board edge.

### Two checks that were wrong before they were right

- **A tautological one.** `(MTX_INSET - MTX_GUTTER_D) - MTX_FACADE_MIN` reported
  `ok 0.00` the moment `MTX_INSET` became the sum of those two terms — it was
  subtracting a number from itself. Replaced with `_facade_measured`, which walks
  the actual solid backwards from the facade and finds where material stops.
- **The perimeter-web check hit the same trap, twice over.** Comparing
  `MTX_GUTTER_WEB` to `MTX_LED_PITCH - MTX_WINDOW` after deriving the first from
  the second can only ever print `0.00`. It now walks the solid outward from the
  gutter edge until material runs out, so a gutter that overran and merged with the
  outermost row of windows would show up. Verified by re-breaking: 0.300 → `FAIL
  -0.44`, 0.060 → `FAIL -0.68`.
- **And it immediately caught a frame bug in itself.** The first version read
  `body` instead of `part_body`. Those differ by the STL export shift
  `(-REVEAL, -BP_T)`, so it was measuring 2.5 mm sideways into solid lip, happily
  reporting the full 1.40 and passing — while the probe three lines above, which
  does use `part_body`, said the gutter was open. **Two measurements of the same
  point disagreeing is the only reason it got noticed.** Verified after the fix by
  forcing `MTX_INSET = 1.0`: measured 0.050, `FAIL -0.40`.

## Stability — `check_stability.py`, and the load case it made up

Answering "does the UPS on the rear wall put too much weight back there?"
**No — it makes the machine harder to tip, not easier.** The pack is heavy but
low, and mass low down buys more restoring moment than its 7.4 mm of rearward COM
shift costs: 53 gf → 56 gf to shove the top over. Static tipping has 14.6 mm of
margin at the worst corner of the assumption box (light shell, +30 % battery) and
survives 10.6° of backward tilt.

Two things this script got wrong first, both worth keeping visible:

- **It invented its load case.** It reported a scary 85 gf to lift the front feet
  by pressing "the front-panel button at z = 100". There is no front-panel button;
  the height came from a `getattr(g, "SW_Y", 100.0)` fallback that fired silently
  because the constant is `SW_WALL_Y`. A default masquerading as geometry. The
  real controls are a rear-wall button 12 mm up (pressing it pushes the machine
  *forward*, and takes >1 kgf) and two **capacitive** crown pads that need no
  force at all — which is precisely why the one high control is safe.
- **It failed on a proxy while the real metric improved.** A 5 mm cap on the COM
  shift failed at 7.4 mm in the same run that showed the shove force getting
  better. A threshold invented to look rigorous, contradicting the outcome it
  stood in for. Removed; the shift is reported as information.

**~55 gf to topple it from the top is low, and it is not the battery's fault** —
it is 156 mm of height on a 39 mm foot span. The free variable is `FOOT_IN`
(16 mm today): 8 mm would give **1.5×** the shove resistance and still leave the
foot 2 mm inside the wall line. Your call.

## Earlier session — the RTC, the vents, and printing rear-wall down

**The reported bug was real but not where it looked.** The bottom plate's screw
holes were clean — every one of the six is an unobstructed cylinder through the
plate. What was wrong is that the RTC's **board** (25.4 mm, on a 20 mm boss
pitch) was 0.9 mm inside the dome's left wall rail and 1.0 mm into a rear tab.
Nothing on the plate could see it: every check on that part compared Ø6 **boss
posts**, and `RTC_PCB_W` was imported into `gen_bottom_plate.py` and never once
referenced.

**The RTC is back on the rear wall at (43, 114)**, 9.0 mm clear. It had been
moved to the floor because a rear-wall search reported "no viable position" —
a search run against the *old* vent stacks and the *old* amp depth, never re-run
after either moved. Re-run it finds **67 151** positions. *A negative result
carries no expiry date; nothing about it announces that its inputs have moved.*

**The vents are now one wide stack above the light pipe** (3 × 72 × 2 = the same
432 mm² as the two old stacks). The two flanking stacks had been fencing off both
upper quadrants of the rear wall — the largest clear areas on it. That is what
took the best available RTC position from 2.5 mm to 9.0 mm.

**FDM ramps, printing rear-wall down** (bed at z=D, build runs toward z=0, so
+z is *down*): the retaining rib's rear face and the crown standoffs' rear halves
were unsupported and now have 45° ramps. The front lip's rear face **cannot** be
ramped — a ramp there reaches inside `REVEAL` and fouls the module as it slides
up — and is reported separately.

### Checks added, and what each one had to learn

| check | where | the mistake it encodes |
|---|---|---|
| `dome_floor_intrusions()` | `enclosure_geom.py` | The plate had no description of what the dome reaches down into it. Two parts sharing a volume must share the description of it. |
| board **outlines** vs those intrusions | `gen_bottom_plate.py` | Bosses are not boards. Re-running the old RTC position reports −1.00 and fails. |
| board envelope vs the built shell | `gen_dome.py` | The board's datum is the **boss tip** plane (`STANDOFF_H + 2`), not the wall — getting that wrong reports a board buried in its own standoffs. |
| overhang audit | `gen_dome.py` | Three iterations: **width not area** (a staircase has the same area as the shelf it replaces); **connected regions not coplanar facets** (a cylinder has no flat facet, so curved overhangs were invisible); **bores are bridges not cantilevers** (excluded by name with their spans asserted, not by raising the threshold). |
| rear-wall boards drawn from the shared list | `gen_drawing.py` | The lux and the RTC were on **no sheet at all**, which is why an unlabelled pair of standoffs was unidentifiable. |
| canonical state lines | `check_docs.py` / `HARDWARE.md` | Written first as `must_not()` against prose, both rules passed while the geometry said the opposite — the stale sentence read "This **was** two stacks", and `"was "` is a `HISTORY_MARKER`. A rule aimed at explanatory prose is defeated by the explanation. |

Both ramps and both doc rules are verified by deliberate re-breaking.

### Ramps are true angles now, not staircases
Orca handles stepping, so the model carries real geometry. The rib ramp, the
crown buttresses and the louvres were each a stack of ~12 thin slabs; all three
are now **single lofted solids** — `loft()` takes the convex hull of two convex
sections, whose lateral surface *is* the straight rule between them, so the
result is exact rather than approximated. Dome went from **43 646 to 31 754
triangles**, and the ramp band now contains **zero** horizontal terrace facets.

The audit threshold moved from 45° to **46°**: the limit is 45 and the ramps are
*built* at 45, so a strict `> 45` flagged 1757 mm² of correct surface. (The rib
ramp measures 44.6–45.0° across the arch because `d_outline` insets its semi-axes
rather than truly offsetting them.) `check_docs.py` now fails if either ramp goes
back to being stepped.

### PLA: the matrix clips were unbuildable, and nothing checked it
Peak strain in a snap-fit cantilever is `1.5·t·y/L²` — thickness × deflection
over the **square** of free length. The clip was 2.2 thick, had to move 1.2, and
was rooted 2.2 mm below its hook: **82 % strain**, against ~2 % for PLA. It would
not have flexed, it would have shattered. Every check in that file is about
*clearance*, and a clip that cannot bend still fits perfectly.

Length is the only real lever because it is squared, so the hook now grips the
**back of the whole stack** rather than the back of the matrix board — which is
what `enclosure_geom` always intended (`MTX_CLIP_Z`, "clip hook standing behind
the backpack", is already in the `TRAY_D` budget). Beam 2.2 → **9.3 mm**, thickness
2.2 → **1.6**, reach 1.2 → **0.5**: **1.39 %**. It also clamps the sandwich properly
instead of pinching one 1.6 mm board. There is now a strain check, and restoring
the old numbers fails it.

### The matrix is recessed now, and the stack was measured
- **Stack height measured at 7.0 mm** (matrix front → backpack back), against 8.2
  assumed. The header gap is derived from it (3.8, not 5.0). This is the clips'
  **lever arm**, so the 1.2 mm error moved their strain 1.20 % → 1.83 %.
- **Engagement, not reach, is the primary clip number.** `CLIP_REACH` is measured
  from the beam's *inner face*, which stands `CLIP_GAP` off the board — so a
  0.4 reach was only **0.15 mm** of actual grip, and the check that should have
  caught it tested reach, so it passed. Reach is now derived from engagement.
- **Boards recessed 2.0 mm into the facade.** The aperture is cut through only
  the front 2 mm; the boards sit in a pocket behind it and seat on the lip.
  Vertical view angle **16° → 34°** — the old well was 4.6 mm deep with 1.34 mm
  of vertical margin, so the top and bottom rows vanished at 16° off-axis on a
  clock you look down at. Not a clearance problem, so nothing flagged it.
- **Clips root in the pocket floor**, so root and hook move together and the
  strain no longer depends on the recess depth at all.
- **`probe()` takes a size now.** Its 1 mm cube is wider than a 0.35 mm hook and
  was reporting both false solids and false empties; small features get small
  cubes, and the hook probe samples near the tip of the 45° facet rather than
  half way up it, where the facet has only reached half its engagement.

### Two coordinate traps worth remembering
- **`MTX_HOLES` was on the wrong diagonal.** Corrected to bottom-left +
  top-right, read from the board's component side. A mirrored diagonal is
  invisible in every view except the one that matters.
- **The front module's STL is not in assembly coordinates.** It is shifted by
  `(-REVEAL, -BP_T)` = (-3.6, -4.0) so the part corner is the origin. Probing the
  STL with assembly coordinates reported the matrix clips entirely missing —
  they were fine; the scan was 3.6 and 4.0 mm out. Use `part_body`, or add the
  shift; the run now prints it.

### Still to measure — see `MEASURE-ME.md`
Written out in plain language with what breaks if each is wrong. The tightest is
**grille cloth thickness**: the groove leaves 0.40 mm total, so anything over
0.80 mm per layer and the front module will not go in.

### Mesh traps hit while building the ramps
All three produced a **valid manifold solid and a broken exported surface** —
`manifold` reported one clean body while `trimesh` reported 27–271:
1. **Unioning steps that share a face.** Twelve ramp steps meeting on shared
   planes → 36 disconnected bodies. Fixed by adding one block and *cutting* the
   staircase out of it, so no plane carries more than one pair of faces.
2. **Tangency.** A buttress exactly `BOSS_D` wide has side planes tangent to the
   Ø6 boss cylinder → 532 zero-area triangles. Pulled in 1.2 mm so the planes cut
   it transversally.
3. **Coplanar caps.** The buttress underside sat exactly on the boss's flat tip
   cap, so a rim circle and a straight edge had to be triangulated in one plane →
   298 more. 0.2 mm of daylight removed it.


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

### ~~Still to measure~~ — the board holes are RESOLVED (see the later pass)
`ENC_HOLE_P`, `TOF_HOLE_P`, `RTC_HOLE_P`, `AMP_HOLE_P`, `LUX_HOLE_P` were all
`(?)` guesses at 20/15 mm. **They are gone.** Every one of these boards publishes
its Eagle `.brd`, and the files give four Ø2.5 holes 2.54 mm in from every edge
(two on the DS3231). See "The hole pitches were never pitches" below and
[`../HARDWARE.md`](../HARDWARE.md).

Still genuinely unmeasured: `SW_D`, `SW_NUT_D`, `BARREL_NUT_D`.


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

> **Superseded — the pair was never a pair.** See "The hole pitches were never
> pitches" below. Both crown boards have **four** holes; the 10.5 mm of clearance
> claimed here was really **0.59 mm** once the real patterns went in.

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


## The spines became ribs — and found a worse bug

The two "unused protrusions" above and below the matrix were stiffening spines,
doing a real job (the 4 mm facade has two sealed speaker boxes bolted to it and
will drum) but shaped by the leftover space rather than by the job: 5 mm-proud
PADS filling their whole band, 92 × 6.6 and 92 × 10.9.

Now **three 3 × 9 ribs** — one above, two below. Per 10 mm of length a 9 mm solid
pad gives I = 608 mm⁴ for 90 mm² of material; a 3 × 9 rib on the same plate gives
**917 for 67**. Half again the stiffness for a quarter less plastic.

Two things went wrong on the way, both caught:

- **Two ribs at 1/3 and 2/3 of the lower band left a 0.65 mm gap** — narrower
  than a nozzle, so it prints as one blob with a defect down the middle and
  stiffens like a single fat rib. Pushed to the band's edges the gap is 4.9 mm.
  There is a check on it now.
- **The presence probes sampled the band's midpoint**, which was solid only
  because the old pad filled the whole band. They aim at the ribs now, plus one
  probe asserting the space between them is *open* — which is the entire point of
  the change.

### And the one that mattered: the exported file was not the validated model

Chasing a 0.6 cm³ discrepancy between the volume the run reported and the volume
of the file turned up this: **`gen_front_plate.py` kept its own `base` pointing at
the script directory.** When solids moved into `models/`, every other generator
followed and that one did not. It had been writing `3d-print/front-module.stl`
while `models/front-module.stl` sat there **three hours stale** — 19032 faces
against the run's 19046.

Every check passed the whole time. They were all validating a solid in memory
that never reached the disk.

**`verify_exports.py`** now re-runs each generator, reads back what it actually
wrote, and compares the face count against what the run claimed — and fails on
any solid found outside `models/`. Verified it catches the original bug by
re-breaking the path.

> Checks had been added for geometry, for prose, and for drawings. The last link
> — model to file — was the one nobody was watching, and it is the only one where
> being wrong means printing the wrong part.


## The RTC was sitting on a screw

Two of the RTC's four standoffs overlapped the left-hand fixing screws by
**4.5 mm** — the screw's clearance hole bored straight through them.

The cause is the same one as last time, one level down. When the RTC was moved to
the floor its position was searched against the **floor items** (speakers, matrix,
UPS, amp) and the **plate edges**. Nobody compared it to the six **screws** —
which are the one thing on that plate that cannot move, since the dome's tabs set
them. Moved to (26.3, 43.7): 2.0 mm to the nearest floor item, 1.8 to the nearest
counterbore, 1.8 to the plate edge. Tight because the floor genuinely is.

### Stop writing checks one pair at a time

Three bugs on this part have now been the same shape: A was checked against B and
C, and nobody compared it to D. So the plate now enumerates **every feature with a
footprint** — screw holes, counterbores, foot pockets, board bosses — and compares
all of them: 22 features, 165 pairs. A new feature joins the list and is checked
against everything else for free.

**It has to know about Z.** The first version compared footprints only and
instantly "found" a foot pocket overlapping a boss — which is fine: the pocket is
cut 1 mm from *below*, the boss stands on *top*, and there is 3 mm of plate
between them. A planar check on a part with features on both faces reports
collisions that do not exist, and a check that cries wolf is worse than no check,
because you start ignoring it. Each feature carries its z span now and only
overlapping spans are compared.

Note the two radii are not interchangeable either: the **counterbore** (r=3) only
reaches 2 mm up from the underside, but the **clearance hole** (r=1.7) runs the
full thickness — so it is the hole, not the counterbore, that reaches a boss on
the top face. Checking the wrong one of those two would have passed.

Verified both ways: putting the RTC back at (20, 44) reports −3.20 mm and fails.


## The hole pitches were never pitches

The encoder, the ToF and the BH1750 each carried a made-up **two**-hole pitch —
`ENC_HOLE_P = 20.0`, `TOF_HOLE_P = 20.0`, `LUX_HOLE_P = 15.0`, every one marked
`(?) MEASURE`. All three boards have **four** holes, and all three vendors publish
the board file that says so. The numbers were sitting in public Eagle files the
whole time:

| | outline | holes |
|---|---|---|
| #4991 I2C QT Rotary Encoder | 25.40 × 25.40 | 4 × Ø2.5, 20.32 × 20.32 |
| #3317 VL53L0X STEMMA QT | 25.40 × 17.78 | 4 × Ø2.5, 20.32 × 12.70 |
| #4681 BH1750 STEMMA QT | 25.40 × 17.78 | 4 × Ø2.5, 20.32 × 12.70 |
| #5188 DS3231 STEMMA QT | 25.40 × 17.78 | **2** × Ø3.0, 20.32 — top pair only |

One footprint family: holes 2.54 mm (0.100″) in from every edge of a 25.4 mm-wide
blank. The DS3231 is the only board that does not populate all four.

**Look for the vendor's board file before reaching for the calipers.** This is the
third time on this part that a published number beat a measured or inferred one —
the matrix's holes, the amp's holes, and now these. `check_docs.py` asserts all
four patterns against their repos, so a guess cannot come back.

### Three real consequences, not just tidier constants

**The bosses were about to merge.** Both crown boards' hole rows are 20.32 along
the depth and both boards are centred on the same depth, so the encoder's
right-hand bosses and the ToF's left-hand bosses sit at **identical depths** —
separated in x alone, with no diagonal to help. Against the old 1.5 mm board-edge
gap that left **0.59 mm** between two Ø6 posts. That is not an intersection, so the
existing "bosses do not intersect" check passed it; 0.59 mm of PETG between two
posts prints as one blob. `TOF_X` is now *derived* from a required boss gap
(`BOSS_GAP_MIN = 2.0`) rather than from a board-edge gap, and the check compares
all 16 pairs with real clearance in it. **The bosses are the binding constraint,
not the board** — the same sentence the RTC's wall search had already written down.

**The ToF was going to tilt 10.7°.** Two bosses on one x cannot tilt a board.
Four spanning 12.7 mm of x can, and the ToF is the one board that is **off the
apex** — dx 16.7 to 30.9, where the ceiling falls 2.6 mm across its hole span. Its
pinhole is a **vertical** bore and its FoV a 25° cone, so following the arch would
have aimed half the cone into the side of its own hole. The board that most needed
to sit flush was the one the arch treated worst — and the old note arguing the flat
was unnecessary had measured the **encoder**, which is centred on the apex and sits
flat either way. *An argument for skipping something is only as good as the case it
was made about.*

Each crown board's four boss tips are now built **coplanar**, at the lowest of its
own local ceilings less its standoff. That is the milled flat's whole benefit bought
with **added** material instead of removed — no lens, no knife edge, none of the
mesh trouble that made cutting a flat a dead end. The dead flat machinery
(`crown_flat_cut`, `ENC_FLAT_*`, `TOF_FLAT_*`, `CROWN_FLAT_R`,
`FLAT_MARGIN_LOCAL`) is deleted: `gen_dome.py` imported all four constants and
called none of them, which left a feature the part does not have looking live.

**A buttress came out through the skin.** Everything that reaches up into the wall
to fuse was written as `local ceiling + a constant`, measured at the feature's
**centre**. Fine near the apex. Out on the shoulder the skin has fallen away by the
time you reach the feature's outboard corner, and the ToF's outer buttress
overshot by 2.0 and left the machine by 0.19 mm. The containment guard caught it —
which is what the guard is for — but a feature that has to be trimmed to be legal
is built wrong. There is now a `crown_outer_y()` to clamp against, and the ramp
raises a hard error if the clamp ever eats the whole overlap.

### Two checks that were passing for the wrong reason

`chk("ToF hole pitch fits its own board", TOF_PCB_D - TOF_HOLE_P)` tested a pitch
against a board. With a corner inset that comparison cannot fail, so it was
replaced by one that can: every hole must lie on its own board, which catches a
board handed its pattern the **wrong way round** — the live risk now that the ToF
is mounted longwise and its (dx, ddepth) is the vendor pattern's (dy, dx).

The flatness check was worse — first written as
`min(crown_inner_y(...)) - standoff` per hole, which is the same formula the
builder uses, so it reported 0.000° no matter what the part did. It reads the
**recorded tip** of each built boss now. Verified by injection: reverting all five
values (the two board outlines, the RTC's y, the old 1.5 mm gap, and the ToF
pattern rotated) fails five separate assertions.

### Also stale, on the sheet rather than in the solid

The rear elevation called the DS3231 up as "4x M2.5 @ 20.3" while the dome
correctly built **two** bosses — a hardcoded count next to a hole list that knew
better. The label derives it now. And the RTC's own holes were 0.51 mm out (y =
14.73, read off a fab print) and drilled Ø2.5 where the board says Ø3.0; the Ø3.0
is a **clearance** hole, so the M2.5 self-tapper into the boss is unchanged. That
was the last open item blocking the rear wall.

### And the mesh validation had not been running

Adding two bosses per crown board turned the dome into **two connected bodies**.
The second one was a **zero-volume, four-face flap** on the left wall at
`y = BP_T`, `z = 24.1..29.0` — no material in it, and nothing to do with the crown.

The cause: `ledge = annulus(WALL, WALL + SEAT_W)` put the seating ledge's outer
face *exactly* on the cavity boundary — the plane the cavity had just been cut on.
Coincident faces, which this part has already paid for three times (the buttresses'
tangent planes, their tip caps, the stepped louvres). Nothing about the ledge had
to change for the flap to appear: **the union order decides which side of the plane
it lands on, and four more bosses in `adds` was enough to flip it.** The ledge now
reaches `LEDGE_BURY` (0.5) *into* the wall so the union overlaps solid material
instead of meeting it. Volume and bounding box are unchanged to four decimals —
only the topology moves.

The rib and its ramp block are written the same way and **must not** get the same
treatment: `_ramp_void` lofts its far section to `d_points(WALL)`, so material
pushed outboard of that would not be cut away and the 45° ramp would come back as
a shelf. Only the ledge is free to be buried.

**The reason this was invisible is worse than the bug.** The whole validation block
sat inside `except ImportError: say("validate skipped: no trimesh")` — a ~180-line
try with imports inside it. trimesh was installed and fine; **scipy** was missing,
and `trimesh.split()` needs it for connected components. So every run printed "no
trimesh" and skipped watertightness, the body count and the board-envelope test.
Removing the blanket handler immediately surfaced a *second* missing dependency,
**rtree**, which the ray intersector needs — so even more had been skipped than the
body count.

Imports are hoisted and named now, a missing one says *which*, and the checks can
no longer be skipped: a missing dependency is a **failure**, not a shrug. With all
four installed the dome reports watertight, one body, all three rear-wall board
envelopes clear of the shell (including the BH1750, now 25.4 wide rather than 20),
and the overhang audit passes at 0.87 mm against a 1.0 limit.

> **A blanket `except ImportError` around a large block does not just report the
> wrong cause — it silently skips work nobody chose to skip.** Five other
> generators are written the same way; they all pass now that the dependencies are
> present, but the pattern is worth removing from them too.

Stale figures found while re-measuring, now corrected in the parts table: the dome
was listed at 146.8 cm³ (really 153.2 after the extra bosses), the front module at
70.3 (68.2) with a 21.3 thickness (18.8), the LED carrier at 25.2 (23.2) and
185.0 × 69.2 × 4.7 (186.1 × 70.7 × 2.5), the plate at 45.3 (45.0). `check_docs.py`
asserts the envelope and the front-module face size but not part volumes, which is
why these drifted.
