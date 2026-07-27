# Dual CharliePlex matrix front plate

A light-isolating front plate for **two butted Adafruit IS31FL3731 16×9
CharliePlex LED matrices**. One circular aperture per LED (288 total) plus the
matrix's 2 diagonal M2 holes per board. Two files, same geometry:

- **`matrix-front-plate.stl`** — ready to import straight into OrcaSlicer. Use
  this. Validated watertight, 2-manifold, correctly oriented (genus 288 = all
  288 through-holes closed cleanly), 29 380 triangles.
- **`matrix-front-plate.svg`** — the flattened profile, if you'd rather use
  OrcaSlicer's SVG tool and set the height yourself.

Geometry is taken from Adafruit's EAGLE **CharliePlex Grid** `.brd` — the LED
matrix module itself, not the driver breakout
([Adafruit-IS31FL3731-CharliePlex-LED-Breakout-PCB](https://github.com/adafruit/Adafruit-IS31FL3731-CharliePlex-LED-Breakout-PCB)),
so it fits the real matrix, not an estimate.

## Board facts (per matrix)

| Item | Value |
|---|---|
| PCB outline | 43.18 × 27.94 mm, 2.54 mm corner radius |
| Mounting holes | **Ø2.0 mm, only 2 (diagonal)** — top-left + bottom-right, inset 1.905 mm from edges |
| LED array | 16 × 9 on **2.54 mm (0.1") pitch**; cols x 2.413–40.513, rows y 3.683–24.003 (EAGLE frame) |

The Ø2.0 holes take **M2** screws (an M2.5 shaft won't pass). The plate is
**92.36 × 33.94 × 4 mm**.

Two boards **butted edge-to-edge** → board pitch 43.18 mm. The LED gap across
the seam is **5.08 mm (2 pitches)** — this is physical, not a design choice
(board edge margins can't overlap).

## OrcaSlicer workflow (STL)

1. **File → Import → Import STL** → `matrix-front-plate.stl` (or drag it in).
2. It arrives at true size in mm (92.36 × 33.94 × 4). Place it flat, slice,
   print. The 4 mm thickness is the depth of each round LED "tunnel" that
   isolates one LED from its neighbours. No repair step needed.

Prefer to set the height yourself? Use the **SVG** tool → **Load SVG** →
`matrix-front-plate.svg`, extrude to 4 mm, solid. The SVG is one flattened
filled path (holes wound opposite the outline) so it imports as a real face.

Because the plate is one thickness, there is **no counterbore** — use
flat/countersunk M2 screws, or pan-head screws sitting slightly proud, or
recess them from behind with standoffs.

## Tunables (edit `gen_plate.py`, re-run)

- `LED_DIA` (1.8 mm) — aperture size. Web between apertures = `PITCH − LED_DIA`
  = 0.74 mm at default. Drop to ~1.6 mm for thicker walls, raise toward 2.2 mm
  for more light / thinner walls.
- `PAD` (3 mm) plate border, `PLATE_R` (3 mm) corner radius.
- `BOARD_PITCH` (43.18 mm) — increase to add an air gap between boards.
- `SCREW_DIA` (2.4 mm) — clearance hole for a different fastener.

## Caveats

- **Only 2 holes per board.** The matrix module has just the top-left and
  bottom-right mounting holes (diagonal). With both boards butted, that's 4
  screws total holding the pair. If the long unsupported middle bows, add a
  clip or standoff at the seam — there's no PCB hole there to use.
- **M2, not M2.5.** Driven by the module's Ø2.0 holes. Keep M2.5 only if you
  plan to drill the PCB holes out to 2.5 mm first.
- **Printability.** Ø1.8 holes with 0.74 mm webs, 4 mm deep, over ~38×20 mm ×2:
  fine on resin; on FDM use a 0.4 mm nozzle, 0.12 mm layers, and expect the
  webs to be 1–2 perimeters. Bump `LED_DIA` down slightly if webs come out weak.
- **Merged corners.** Each mounting hole sits so close to its nearest corner
  LED (centres 1.9–2.1 mm apart) that the two openings **overlap**. Rather than
  leave a hairline wall, the generator fuses each screw hole with that one
  corner LED into a single figure-8 opening (4 places). The corner LED still
  shines and the screw still passes — that corner LED just isn't individually
  walled from the screw hole.

## Regenerating

The SVG needs only Python 3. The STL also needs `mapbox_earcut` + `numpy`:

```sh
python3 -m venv venv
venv/bin/pip install mapbox_earcut numpy
venv/bin/python gen_plate.py     # writes both .stl and .svg
```

Plain `python3 gen_plate.py` (no earcut) still writes the SVG and skips the STL.
