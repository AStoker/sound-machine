# WIP — resume here

**All five generators are `ALL CLEAR`.** Firmware is in sync with the geometry.
Nothing is committed. `HARDWARE.md` and `README.md` are still stale (last
section).

```sh
python3 gen_drawing.py && python3 gen_internals.py && python3 gen_wiring.py
../.venv/bin/python gen_front_plate.py
../.venv/bin/python gen_led_carrier.py
```

## Envelope

| | before | now |
|---|---|---|
| envelope | 202 × 64 × 160.02 | **202 × 64 × 155.69** |
| front aspect | 1.26:1 | 1.30:1 |
| CROWN_K | 0.72 | **0.74** |
| MIC_Y0 / MIC_Y1 | 70.7 / 82.7 | **64.35 / 76.35** |
| CRES_Y | 87.3 | **80.95** |
| crescent ellipse | 89 × 60.72 | **89 × 62.74** |
| LED rows | 10/10/10/8/7/3 = 48 | **10/10/9/8/6/2 = 45** |
| min LED → diffuser | −0.58 (overhang) | **+2.26** |
| front module | 194.8 × 152.4 × 22.2 | **194.8 × 148.1 × 21.33** |
| parts | 5 | **6** (LED carrier added) |

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

**Fixing: 6 × M2.5 into pads on the INSIDE of the cavity wall.** Three
alternatives were considered and cost more:

- *ears reaching outward onto the rim* — only **0.9 mm** of rim is free outside
  the cavity wall before the dome's rib keep-out. Making room means RIM_MIN
  12 → ~16, which shrinks the crescent to 85 × 58.7 and drops it to five rows.
- *pillars from the facade floor* — 12 mm columns inside a lit cavity.
- *captured by the dome, no screws* — locates the plate, never clamps it.

The pads also buttress what is otherwise a 2 mm × 19 mm unsupported fin.

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

## Still open

- `HARDWARE.md` and `3d-print/README.md` still describe the **258-wide, split**
  design: side nubs, array flanked by speakers, semicircular crown, R117/R96
  crescent with a 21 mm fade band, two-piece front module. All wrong.
- Measure `SPK_NUB_H` / `SPK_NUB_PROJ` / `SPK_NUB_W` before printing.
- `DIFF_GAP` (12) is still a guess — tune on a test print. It is the one number
  most likely to need changing, and it moves `CARRIER_Z0` with it.
- The 2-pixel apex row: if it reads badly, CROWN_K 0.80 restores 48 px for
  +6 mm of height.
- `.png` files are NOT regenerated by the scripts — they are rendered separately
  from the `.svg`s (`cairosvg`, scale 3).
