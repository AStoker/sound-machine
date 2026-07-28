# WIP — resume here

**All four generators are `ALL CLEAR`.** The six `gen_front_plate.py` failures
are fixed — root cause below. Nothing is committed. Docs still stale (last
section).

## The six failures were one bug, and it was not where the notes were looking

`gen_front_plate.py` contained **the whole build twice.** Lines 120–323 were a
copy of 324–541: same header, same `body = slab(outline2(), 0.0, FP_T)`, same
`cuts`, same `adds`. Python ran both, and the second copy *reassigned* `body`,
so the first copy's output was silently discarded.

The two copies differed in exactly one block — the speaker mount. The **dead**
copy had it correctly rotated. The **live** copy still had the pre-rotation
version: posts on the flanks at
`px = sx ± (SPK_BODY_W/2 + SPK_FIT + pw/2)` → **x = 5.25 / 56.95** and mirrors
at **145.05 / 196.75**, with locating ribs top and bottom where the nubs now
live.

That is why the previous session's probe kept finding walls at x ≈ 5.1 / 58.8
after the file "confirmed" the ribs were removed: the fix had been applied to
the dead copy. Outboard pair stood in the dome's groove band, inboard pair stood
inside the matrix footprint — four of the six failures, plus the containment
guard and the clip-clear probes.

**Fixed by deleting the duplicate** (the surviving copy is the one with the
stiffening section, which the dead copy lacked) and rotating the mount properly:
posts above and below on the body centreline, no ribs on any face. Two screws
top and bottom fix x, y and rotation between them.

> If a probe ever reports a wall at x ≈ 5 or ≈ 57 again, check the speaker mount
> block first — and check the file only builds `body` once.

### A second, real collision surfaced underneath it

The **short inboard stiffening ribs** ran at `y = SPK_Y ± RIB_T/2`. That was safe
when the matrix sat on the floor. The clock is now *centred on the speakers*, so
`SPK_Y` **is** the matrix mid-height and each rib ran straight through the
boards — 49.8 mm³ into the matrix envelope, into 288 LEDs, and through the end
clips' hook zone. Four failures, one rib.

There is nowhere left to put them: speaker seat to end-clip outer face is
0.77 mm. Replaced with a **second spine in the band below the matrix**, mirroring
the one above it. Symmetric pair braces the plate better than one spine plus two
stubs, and that band is genuinely empty.

## What changed this session

### 1. The mic array came down 6.35 mm

`MIC_Y0` was `SPK_SEAT_Y1 + SPK_MIC_GAP` — the top of the *nub post*. It never
needed to be. The post is `SPK_POST_W` = 10 mm wide and stands on the speaker's
**centreline**, x = 31.1 and 170.9; the mic PCB is 110 mm centred, x = 46–156.
They overlap in y by 3.35 mm and **never in x**, with 9.9 mm to spare
(`CLR_POST_MIC`). So the array only has to clear the speaker **body**.

`MIC_Y0` is now `SPK_Y1 + SPK_MIC_GAP`: 70.7 → **64.35**.

> Post width is set by the nub, not the body. Scaling it off the body
> (0.60 × 45 = 27 wide) reaches x = 44.6 and hands the whole saving straight
> back. `SPK_POST_W = SPK_NUB_H + 2·SPK_POST_WALL`.

### 2. CROWN_K 0.72 → 0.74, and the crescent solver now measures properly

At 0.72 the top LED body sat **0.58 mm outside the diffuser**. Every check read
clear because they all measured horizontally (chord) and vertically (apex) — and
on an ellipse the binding case is **diagonal**, an outer pixel two rows down from
the apex where the boundary is falling away fast.

`ell_dist()` now returns true point-to-ellipse distance (bisected stationary
condition), and `crescent_rows()` allocates on that instead of a chord inset,
with rows forced **non-increasing** bottom-first. Without that constraint the
solver returns things like 10/10/9/10 — every pixel legal, silhouette obviously
wrong.

0.74 spends 2.02 mm of the 6.35 on the crescent and banks the other 4.33 as a
shorter shell. `crescent_clearance()` reports the tightest gap; keep it positive
and comfortably so — `LED_D`, `STRIP_W` and `DIFF_MARGIN` are all still `(?)`.

### 3. Checks that were measuring the wrong thing

- `CLR_SPK_MIC` was `MIC_Y0 - SPK_SEAT_Y1`. Now `MIC_Y0 - SPK_Y1` — body to
  array, vertical.
- `CLR_NUB_MIC` was the same y check. The array passes *beside* the post now,
  not above it, so it aliases `CLR_POST_MIC` — an **x** check.
- The `left / right locating rib` presence probes are gone. Those ribs do not
  exist on the rotated mount; they had been passing by accidentally hitting the
  stiffening rib at `SPK_Y`. Replaced with an **outboard flank must be bare**
  probe (the 1 mm `SPK_FLANK` budget butts onto the dome's rib keep-out, so
  anything appearing there jams assembly). The inboard flank is deliberately not
  probed — the matrix end clip lives there by design and its clearance is
  measured in the table.

### Result

| | before | now |
|---|---|---|
| envelope | 202 × 64 × 160.02 | **202 × 64 × 155.69** |
| front aspect | 1.26:1 | 1.30:1 |
| MIC_Y0 / MIC_Y1 | 70.7 / 82.7 | **64.35 / 76.35** |
| CRES_Y | 87.3 | **80.95** |
| crescent ellipse | 89 × 60.72 | **89 × 62.74** |
| LED rows | 10/10/10/8/7/3 | **11/10/10/8/7/2** |
| min LED → diffuser | **−0.58 (overhang)** | **+2.11** |
| front module | 194.8 × 152.4 | **194.8 × 148.1** |
| dome on a 220 bed | whole | whole, 25.2 / 71.9 to spare |

Front module mesh: watertight, winding OK, 68.3 cm³, 13 578 triangles.

The apex row is **2 px**, down from 3. That was the accepted cost of favouring
height at K = 0.74 — K = 0.76 would have restored 10/10/10/8/7/3 with 3.35 mm
clearance for 2 mm more height, if the 2-pixel apex reads badly on a test print.

## Next

**`packages/lighting.yaml` is now wrong and it is a one-line fix.** Line 274
still carries the pre-rotation circular-arc layout:

```cpp
static const uint8_t leds_per_row[] = {10, 10, 9, 8, 7, 4};
```

Should be:

```cpp
static const uint8_t leds_per_row[] = {11, 10, 10, 8, 7, 2};
```

Row chords are now **177.8 / 173.8 / 163.7 / 146.6 / 119.2 / 70.6 mm** at an
**11.0 mm** row pitch (not 16.7 — the flattened crown forces it to the
`STRIP_W + 1` floor). The comment block at lines 234 and 261–274 quotes the old
192/188/178/160/133/85 chords and claims "row 5 is 4 pixels, not 1" — both
stale. Capacity is 52 px over 6 rows, 48 fitted = 92.3 % full.

`HARDWARE.md` and `3d-print/README.md` still describe the **258-wide, split**
design: side nubs, array flanked by speakers, semicircular crown, R117/R96
crescent with a 21 mm fade band, two-piece front module. All wrong.

Also still open from before: `SPK_NUB_PROJ`, `SPK_NUB_W`, `SPK_NUB_H`, `STRIP_W`
and `CLOTH_T` are all unmeasured `(?)`. `SPK_NUB_H` now sets `SPK_POST_W`, which
is what buys the mic clearance — measure it before printing.

## Verify everything with

```sh
python3 gen_drawing.py && python3 gen_internals.py && python3 gen_wiring.py
../.venv/bin/python gen_front_plate.py
```

Each ends in `ALL CLEAR` or a problem count. `gen_front_plate.py` additionally
prints a trimesh validation line if trimesh is installed.
