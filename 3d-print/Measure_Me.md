# Measure these before you print

Every number below is a **guess I made from datasheets or eyeballing**, and each
one is baked into printed geometry. They're sorted by what happens if the guess
is wrong, not by how hard they are to measure.

Where a value lives: all of them are in `3d-print/enclosure_geom.py`, each marked
`(?)`. Change the number, re-run the generators, and every drawing, solid and
clearance check updates together.

A general note on **how** to measure: for board mounting holes, measure
**centre-to-centre between opposite holes**, not the board edge. For panel-mount
parts (the jack, the switch) measure the **threaded barrel**, not the bezel you
see from outside.

---

## 1. Will not assemble at all if wrong

### The grille cloth — thickness of ONE layer
**This is the tightest number in the whole build.** The front module slides into
a 5.6 mm groove. The module is 4 mm, and the cloth wraps around it, so there are
*two* layers of cloth in the groove — one front, one back. That leaves **0.40 mm
of total slack**. If your cloth is thicker than **0.80 mm per layer**, the module
physically will not go in, and there is no way to fix it after printing.

Measure a single layer with calipers, gently — cloth compresses, so don't clamp
it. If in doubt measure a folded stack of 4 layers and divide.

### ~~Board mounting-hole spacing — five boards~~ — RESOLVED, DO NOT MEASURE

**All five came out of the vendors' own PCB files. Nothing to measure here.**
Every board on this list is an Adafruit or Adafruit-style breakout whose Eagle
`.brd` is published, and the board file states its outline and every mounting hole
outright — which is better than a caliper on a sample, because it is the same
number for every unit.

| Board | Outline | Holes | Source |
|---|---|---|---|
| Rotary encoder (#4991) | 25.4 × 25.4 | **4** × Ø2.5, 20.32 × 20.32 | [Adafruit-I2C-QT-Rotary-Encoder-PCB](https://github.com/adafruit/Adafruit-I2C-QT-Rotary-Encoder-PCB) |
| Time-of-flight (#3317) | 25.4 × 17.78 | **4** × Ø2.5, 20.32 × 12.70 | [Adafruit-VL53L0X-ToF-Distance-Sensor-PCB](https://github.com/adafruit/Adafruit-VL53L0X-ToF-Distance-Sensor-PCB) |
| Light sensor (#4681) | 25.4 × 17.78 | **4** × Ø2.5, 20.32 × 12.70 | [Adafruit-BH1750-PCB](https://github.com/adafruit/Adafruit-BH1750-PCB) |
| Real-time clock (#5188) | 25.4 × 17.78 | **2** × Ø3.0, 20.32, top pair only | [Adafruit-DS3231-Precision-RTC-Breakout-PCB](https://github.com/adafruit/Adafruit-DS3231-Precision-RTC-Breakout-PCB) |
| Amplifier (TPA2016) | — | **2** × Ø2.5, 22.86 vertical | its own `.brd` (see `AMP_HOLES`) |

> **Every guess on the old list was wrong, and three of them were wrong in the
> same way.** The encoder, ToF and light sensor were each given a **two**-hole
> pitch (20, 20 and 15 mm) when all three carry **four** holes on the shared
> STEMMA QT grid — 2.54 mm in from every edge. Two posts under a four-hole board
> do not just leave two holes empty: the board pivots on the line joining them.
>
> The old "slack" note said the encoder and ToF had **10.5 mm of growing room**
> before their posts collided. With the real patterns they had **0.59 mm** — the
> two boards' hole rows sit at identical depths, so the bosses were dead in line
> and there was no diagonal to save them. The gap between the boards is now
> *derived* from that boss clearance (`_resolve_tof_x()`), not chosen.
>
> **The lesson worth keeping: look for the vendor's board file before reaching for
> the calipers.** `3d-print/check_docs.py` now asserts all of the above against
> these repos, so a future edit cannot quietly reintroduce a guess.

### The two holes you can't re-drill
Both go through the outer skin, so a wrong hole is a scrapped dome.

- **DC charging socket** — the diameter of the *threaded barrel*, and the width
  of its nut **across the corners** (not the flats). Guessed 11 mm and 16 mm;
  the flat pad behind it has 4 mm of spare room for the nut.
- **UPS power button** — same two numbers for the round panel button. Guessed
  12 mm hole, 16 mm nut.

### Heat-set insert hole
The six screws that hold the bottom plate go into brass inserts melted into the
dome. I've guessed a **4.0 mm hole for an M3 × 5 mm insert**. Check the size your
inserts actually want — too big and they spin, too small and they split the post.
There's 4.8 mm of spare depth, so length is not critical; diameter is.

---

## 2. Will assemble but won't work properly

### The encoder shaft, for the knob
Two numbers: the **shaft diameter** and the **width across the flat** of the
D-shape. Guessed 6.0 mm and 4.5 mm. Get the flat wrong and the knob either won't
push on or will slip when you turn it. The hole in the shell has only 0.5 mm of
slack around the shaft, so if your shaft is fatter than 6 mm tell me.

### Speaker mounting nubs
The three dimensions of the little tabs on the sides of the speaker: **how far
each stands off the body**, and its **width and height**. Guessed 4 × 8 × 6 mm.
These set the whole height of the machine — the microphone array sits 3 mm above
the speaker *body*, and if the nubs are bigger than I think, the front plate's
posts land in the wrong place.

Also worth checking: the **bolt-circle diameter** of the driver (46 mm guessed),
the **open cone diameter** you can see through the grille (40 mm), and **how deep
the speaker can is** front-to-back (22 mm, in a 59 mm interior).

### Diffuser acrylic thickness
Guessed 3.0 mm opal acrylic. It sits in a printed pocket; wrong thickness means
it rattles or won't seat.

### Microphone array
The **width of the array board** (12 mm guessed — this isn't published anywhere,
so it needs measuring) and the **diameter of the acoustic port holes** through
the front plate (2.5 mm guessed).

---

## 3. Tune on a test print, don't measure

### The air gap behind the diffuser
Currently 12 mm. This is the distance from the LEDs to the acrylic and it decides
whether you see 48 distinct dots or one smooth arc. There's no right answer on
paper — print a small test piece with two or three gaps and look at it in a dark
room. Too small and it's dotty; too large and it's dim and the machine gets
deeper.

---

## 4. Nice to confirm, low risk

- **Board outlines** — the overall width and height of the RTC (25.4 mm square
  guessed), light sensor (20 × 18), ToF (17.8 × 25.4) and encoder (25.4 square)
  breakouts. These only matter for the clearance checks, not for anything printed
  — but the RTC's *posts* span 26 mm, wider than the board itself, so the posts
  are what actually binds.
- **Amplifier board size** — 26 × 20 × 8 mm guessed.
- **UPS pack depth** — 24 mm guessed for board plus cells. Width and height (60 ×
  93) are from the product page and are probably right.

---

## When you have the numbers

Give them to me in any form — a list, a photo of your notes, whatever. I'll
update `enclosure_geom.py`, re-run everything, and tell you which clearances
moved and whether anything now fails. Several of these interact (the nub size
feeds the overall height, the cloth feeds the groove), so it's worth doing them
as one batch rather than one at a time.