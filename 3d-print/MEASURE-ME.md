# Measure these before you print

Every value below is still a **guess** in `enclosure_geom.py`, marked `(?)` at its
declaration. Nothing else is: if a constant is not on this list, it came from a
vendor board file, a datasheet, or something you already measured.

> `check_docs.py` now asserts this list against the code — every `(?)` constant
> must appear here, and nothing here may claim to be unknown once the `(?)` comes
> off. The list drifted badly before that rule existed: it was still asking for
> five hole patterns that Adafruit's own board files had already settled, for
> speaker nubs you had confirmed on a print, and for a socket height belonging to
> a design that was never built.

---

## 1. The one that blocks a print you want to do now

### `MTX_PIN_H` — trimmed header pins on the clock matrix, **assumed 0.8**

How far the pins stand above the board's **LED-side** face after your trim. Sit a
straight edge across them and caliper the standoff, or measure board-face to pin
tip.

It sets the recess depth, because the gutter must swallow the pin and the facade
in front of it must stay ≥ 0.45 mm thick:

| pins measure | gutter | matrix inset |
|---|---|---|
| 0.5 | 0.65 | **1.10** |
| 0.8 *(assumed)* | 0.95 | **1.40** |
| 1.1 | 1.25 | **1.70** |

Shorter trim buys viewing angle directly. The inset is derived, so tell me the
number and everything downstream follows.

**The test coupon checks this for you** — print `matrix-testfit.stl` and see
whether the boards sit flush.

---

## 2. Will not assemble if wrong

### `CLOTH_T` — grille cloth, **one** layer, assumed 0.6

Measure a single layer with calipers, gently: cloth compresses, so don't clamp.
The groove that traps the front module is sized around two thicknesses.

### `INSERT_D` — heat-set insert hole, assumed Ø4.0

For M3 × 5.0 brass inserts. The number that matters is the **hole** the insert
wants, which the insert's own spec gives — usually 0.1–0.2 mm under its knurl.

### `BARREL_NUT_D`, `SW_NUT_D` — across the nuts, both assumed 16.0

Across the **corners**, not the flats, on the panel nuts for the DC jack and the
UPS button. They set the flat land each one tightens against. The panel holes
themselves are settled (Ø7 and Ø12, from your measurements).

### `KNOB_BORE_D` / `KNOB_BORE_F` — encoder shaft, assumed 6.0 with a 4.5 flat

Caliper the D-shaft: full diameter, and across the flat. A press fit is designed
in, so 0.2 mm out here is the difference between a knob that presses on and one
that splits.

---

## 3. Will assemble but won't work properly

### `SPK_BODY_D`, `SPK_GRILLE`, `SPK_BC` — the speaker

Assumed 22.0 deep, 40.0 open cone, 46.0 bolt circle. Depth sets whether the driver
clears the crescent; the bolt circle sets the mounting. *(The nubs themselves are
confirmed — you said they're perfect on a print.)*

### `MIC_PORT_D`, `MIC_PCB_H` — the mic array

Assumed Ø2.5 acoustic port and a 12.0 board width. The board width is not
published anywhere I can find. The port diameter matters for the seal against your
foam tape.

### `DIFF_T` — opal acrylic thickness, assumed 3.0

Whatever you actually buy. The pocket is cut to `DIFF_T + 0.2`.

### `UPS_D` — pack depth with cells in, assumed 24.0

Width and height (60 × 93) are from the DXF and are right. Only the depth is a
guess, and it drives how far the pack stands off the rear wall.

---

## 4. Tune on a test print — don't measure

### `DIFF_GAP` — air gap behind the diffuser, currently 12.0

How far the LEDs sit behind the acrylic. Too close and you see 48 dots; too far and
the crescent goes dim and muddy. This is a *look* you judge by eye, not a
dimension, and it is the biggest single lever on how the crescent reads.

### `SPK_PILOT_D`, `LED_BODY` — 2.5 and 1.6

Pilot for an M3 self-tapper, and the 0603 LED package's long axis. Both only matter
if a fit comes out tight.

---

## 5. Assembly steps the model can't do for you

- **Mic port gaskets.** Thin foam tape between the array and the facade, holes cut
  for the ports. The screw bosses are deliberately short so the board can be pulled
  down onto it.
- **The encoder board goes in one way round.** Four holes on a square pitch and a
  central shaft mean it drops in happily at 180° out. Fit it with the **NeoPixel
  edge toward the FRONT** — the edge with the pixel in line with the two mounting
  holes. Backwards puts the crown's light window at the back of the knob.
- **The matrix pair.** Both boards drop onto their own posts; the clips hook the
  whole stack. If a board won't go on, stop — don't force it.

---

## Settled — do not re-measure

Kept short on purpose. The full reasoning for each lives at its constant.

| | source |
|---|---|
| All five breakout hole patterns (encoder, ToF, lux, RTC, matrix + driver) | Adafruit board files |
| TPA2016 outline **and** its two M2.5 holes at (19.05, 2.54 / 25.40) | `Adafruit TPA2016D2.brd` |
| UPS 3S: 60 × 93, four Ø3.1 on 46 × 86 | your DXF |
| Flex core: 52 × 70 × 20, four Ø3.0 on 63 × 45 | you measured |
| Matrix stack height 7.0, mic hole edges at 22.0 | you measured |
| Panel holes: barrel Ø7, rotary Ø7, button Ø12 | you measured |
| Speaker nubs — projection, width, height, screw | confirmed on your print |
| NeoPixel at board (12.7, 22.86) — in line with the top screw holes | #4991 fab print |

---

## When you have the numbers

Give them to me in any form — a list, a photo of your notes, whatever. I'll update
`enclosure_geom.py`, take the `(?)` off, re-run everything, and tell you which
clearances moved.
