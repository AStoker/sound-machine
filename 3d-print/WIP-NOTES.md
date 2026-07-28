# WIP — resume here

Mid-redesign. **Sheets 1–3 are done and `ALL CLEAR`. `gen_front_plate.py` has 6
failures left.** Nothing is committed.

## What changed and why

Goal was to get the **dome** printable in one piece on a **Flashforge Adventurer
5M Pro (220 cube)**. It was 258 wide. Proven impossible at 258: best of ~40,000
orientations was still 9.2 mm over.

Three changes got there, all of them yours:

1. **Speakers rotated 90°.** The box is 50 × 45 with a nub centred on each 45 mm
   face; standing it on its side puts those nubs **top and bottom**, which takes
   the mounting post out of the WIDTH chain and puts it in the height (where
   there was slack). It also narrows the body 50 → 45. Acoustically free.
2. **Mic array moved above the speakers**, so the middle of the facade only has
   to hold the 86 mm matrix pair, not the 110 mm array.
3. **Crown flattened to a half-ellipse**, `CROWN_K = 0.72`. Necessary because
   `H = CRES_Y + k·W/2` — with a true semicircle the narrower body made the
   front nearly square (1.07:1). Note removing LEDs does *not* affect height;
   that was a dead end.

### Result

| | before | now |
|---|---|---|
| envelope | 258 × 64 × 189.6 | **202 × 64 × 160** |
| front aspect | 1.36:1 | 1.26:1 |
| dome on a 220 bed | no (split needed) | **fits whole** |
| front module | 250.8 × 179, split in 2 | **194.8 × 152.4, whole** |
| tip angle | 28.0° | 27.6° |

`CROWN_K` is 0.72, not the 0.70 you picked: at 0.70 the crescent held exactly
48 px at 100 % fill with the strip rows edge-to-edge. 0.72 buys a 6th row and
92 % fill for 2 mm of height, and 1.26:1 vs 1.28:1 is invisible. Flagged rather
than silently applied.

### Knock-on changes already made

- Crescent is an **ellipse** (89 × 60.7). Row pitch is now **derived** (11.0),
  floored at `STRIP_W + 1` because the strip is a ~10 mm ribbon. 6 rows,
  **10/10/10/8/7/3 = 48**. **No fade band** any more — the LED field *is* the
  diffuser, per your "keep 48 px" choice.
- **UPS and Flex no longer stack** (93 + 70 > 157.5 interior). They sit **side
  by side** on the rear wall — UPS right (x 120–180, on the floor), Flex left
  (x 5–115, lifted to y=16 so it clears the fixing lugs).
- **Barrel jack is now a panel-mount part** on a flying lead, so it stays
  centred even though the UPS moved off centre.
- **TPA2016 moved to the floor**, tucked in the 12 mm slot under the lifted
  Flex. Rear wall has no room left.
- **Both rear fixing lugs are left of centre** (x 55 and 105) — the UPS owns the
  rear-right corner of the floor.
- The front-module **split is now conditional** (`NEEDS_SPLIT`) and currently
  OFF. The seam logic is retained because its placement was hard-won; it
  re-enables automatically if anything pushes the part back over the bed.

## The 6 remaining failures (all `gen_front_plate.py`)

Run: `../.venv/bin/python gen_front_plate.py`

```
FAIL  220.15   matrix pair envelope (front -> back face, holes excepted)
FAIL   10.06   288 LEDs vs facade / pads / posts
FAIL 1341.00   dome groove band - flanks + arc must stay plain
FAIL  solid    clip end L clear below the back face
FAIL  solid    clip end R clear below the back face
FAIL   -2.69   nothing trimmed by the containment guard
```

These are almost certainly **one root cause**, not six. A grid probe located the
offending material:

- **Matrix envelope:** a continuous column at **x ≈ 58.8**, spanning the full
  matrix height (y 23–47), at z = 5.4. Mirrored at x ≈ 136.8–142.8.
  `mtx_x0 = 57.82`, so it is just *inside* the matrix footprint.
- **Groove band:** at **x = 5.1 and 196.9**, spanning y 8–60, at z = 6.
  That is above the 4 mm facade, so it is a *boss*, not the plate.

Ruled out already:
- speaker flank ribs — confirmed removed from the file
- the end clips — their beams sit at x 55.4–57.6, outboard of the matrix, and
  their hooks are above `MTX_ZB`
- the spine — its y range is 53.8–60.4, wrong band for the x≈58.8 hits
- matrix posts/pads — correct positions, and the envelope test punches the holes

**Next step:** find what generates a wall at x ≈ 5.1 / 58.8 and z > 4. Suspect
something in `adds` still built from the pre-rotation speaker model (a
`SPK_SEAT_W`/`SPK_RING_W` leftover), or the `half_disc` skirt. Bisect by
commenting out entries in `adds` one group at a time and re-running the probe —
the diagnostic loop is in the shell history, or re-create it with a
`Manifold.cube` probe against `part_body`.

Also stale once that is fixed: the feature probes still say "left/right
locating rib" but those ribs are gone — they are currently passing by
coincidentally hitting the spine.

## Docs NOT yet updated

`HARDWARE.md` and `3d-print/README.md` still describe the **258-wide, split**
design throughout: side nubs, array flanked by speakers, semicircular crown,
R117/R96 crescent with a 21 mm fade band, two-piece front module. All of that is
now wrong. `packages/lighting.yaml` still carries the old 6-row layout on a
circular arc and needs the new **10/10/10/8/7/3** at an 11.0 mm row pitch.

## Verify everything with

```sh
python3 gen_drawing.py && python3 gen_internals.py && python3 gen_wiring.py
../.venv/bin/python gen_front_plate.py
```

Each ends in `ALL CLEAR` or a problem count.
