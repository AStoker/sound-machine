# Measure these before you print

---

# ⛔ BLOCKING THE BASE — read this first

## Settled since this list was written

| Part | Now confirmed | Source |
|---|---|---|
| **UPS 3S** | 60 × 93, four **Ø3.1 holes on a 46 × 86 pitch** (7.0 in from long edges, 3.5 from short). A lone Ø2.5 near top-centre is **not** a fixing. | Your DXF |
| **Flex core** | 52 × 70 × **20** (incl. seated XIAO); holes **Ø3.0 inset 3.5**, 63 × 45 pitch — which is what the model already had. 110 mm corridor for array + ribbon. | Your measurement, corroborated by the STEP |
| **Panel holes** | charge jack **7**, encoder **7**, button **12** | Your measurement |
| **DS3231** | Adafruit #5188, **25.4 × 17.8 × 7.8**, **two** mounting holes | Adafruit product page |
| **TPA2016** | **21.59 × 27.94**, R2.54 corners — was modelled 26 × 20, wrong on both axes | `Adafruit TPA2016D2.brd` |
| **STEP files** | The "linear" file **is** the linear array. Both it and the circular one are internally named `44mm_circular` — Seeed's export naming, not a mix-up. Geometry differs: circular ≈ 67 × 66 round-ish, linear is a long thin strip. | Compared directly |

## ⚠️ One number I need: how far the trimmed pins stand off the matrix

**`MTX_PIN_H`, assumed 0.8 mm.** The header pins on the LED side of the matrix,
after your trim — measured from the PCB's LED-side face to the highest pin tip.
Easiest way: sit a steel rule or a flat edge across the pins and see how far it
stands off the board, or caliper from the board face to a pin tip.

It matters more than it looks, because **it sets the recess depth**. The gutter
has to swallow the pin, the facade in front of the gutter has to stay at least
0.45 mm thick, so the inset is the sum of the two:

| If the pins measure | gutter | facade left | matrix inset |
|---|---|---|---|
| 0.5 mm | 0.65 | 0.45 | **1.10** |
| 0.8 mm *(assumed)* | 0.95 | 0.45 | **1.40** |
| 1.1 mm | 1.25 | 0.45 | **1.70** |

So a shorter trim buys viewing angle directly. Tell me the number and the inset
follows automatically — it is derived in the code, not typed.

## Every board now has a confirmed hole pattern

| Board | Holes | Source |
|---|---|---|
| **TPA2016** | 2 × **M2.5** at **(19.05, 2.54)** and **(19.05, 25.40)** — same x, 0.9" apart, centres 2.54 from the right edge | `MOUNTINGHOLE_2.5_PLATED_THICK` elements + the .brd's own `<dimension>` objects |
| **DS3231 QT** | 2 × **M2.5** at **(2.54, 14.73)** and **(22.86, 14.73)** — 0.80" apart, 0.12" down from the *top* edge | STEMMA QT fab print |
| **UPS 3S** | 4 × Ø3.1, 46 × 86 pitch | Waveshare DXF |
| **Flex core** | 4 × Ø3.0, 63 × 45 pitch | Measured |
| **Matrix / driver** | Ø2.0 diagonal pair / 4 × Ø2.5 at 2.54 inset | Adafruit .brd + fab print |

> ### ⚠️ I reported the TPA2016 as having no mounting holes. It was wrong.
> The claim came from grepping the board file's `<plain>` section, finding no
> `<hole>`, and reporting that as fact. The holes are placed as **elements**
> further down the same file, using `MOUNTINGHOLE_2.5_PLATED_THICK` — which is
> precisely where the CharliePlex driver's holes were, after that identical
> mistake had already been made once on that board.
>
> **Absence in the part of a file you happened to read is not absence.** The
> honest report would have been "I can't see them in the section I can reach",
> which is what I'd said about the driver and then failed to say here.

### All three are now actually mounted

The patterns were known for a while; the parts weren't holding anything. As of
this pass:

- **UPS** — four M3 bosses on the rear wall, on the real 46 × 86 pattern. It had
  *no* fixing at all before, despite the holes being in the table above. M3, not
  M2.5: its holes are Ø3.1, and boss pilots are now sized per board rather than
  from one global constant.
- **DS3231** — **two** bosses. The dome was building a four-boss square from a
  single pitch, so two of them stood on bare PCB and would have held the board
  off the two that mattered.
- **TPA2016** — two floor bosses on the correct pattern. Two bugs here: a stale
  `AMP_HOLE_P = 20.0` placeholder, 800 lines below the measured 22.86, was what
  every generator actually imported; and both bosses sat on the board's depth
  centreline when both holes are 8.26 mm off it. The board could not have gone on
  at any pitch.

## Still open

- **Speaker nubs** — you said they're perfect, so untouched.
- Two secondary dimensions I could not reconcile off the rasters (TPA2016's 0.06"
  and 0.3", DS3231's 0.51"). They don't affect the holes, but if either is a hole
  reference rather than a component callout, tell me.

---

# Original blockers

Four things stop the base being designed correctly. Everything else on it I can
either look up from Adafruit/Seeed/Waveshare or derive. These four I cannot.

### 1. The ReSpeaker Flex CORE board — outline, thickness, 4 hole positions
**The single biggest blocker.** Seeed does not publish the core board's
dimensions (HARDWARE.md has said so all along). Every other board on the rear
wall is placed *around* it, so if it's wrong, the whole wall is wrong.

Currently guessed: a 52 × 70 mm PCB inside a 110 × 70 envelope, holes on a
45 × 63 pitch. Measure: overall W × H, board thickness, the **four mounting hole
centres** (from one corner), and how far the tallest connector stands proud.

### 2. The Waveshare UPS 3S — hole positions, and depth with cells in
Waveshare publishes **60 × 93 mm** and **Ø3.0 mounting holes** — but not where
they are, and not the depth with cells fitted (assumed 24 mm).

> **And right now nothing mounts it at all.** It's the heaviest single item —
> ~250 g with three 18650s — standing vertically against the rear wall with no
> bosses, brackets or captures anywhere in the model. That's a genuine gap in the
> base, not a tolerance issue, and I need the hole positions to close it.

Measure: the hole centres from one corner, and the depth over the cells.

### 3. The panel-mount barrel jack and power switch
Both are **holes in the visible shell** — no fixing them after printing.
Currently Ø11 jack / Ø16 nut, Ø12 switch / Ø16 nut, all guesses.

Measure, on the actual parts: the **threaded barrel diameter** and the **nut
across the corners** for each. (Not the bezel you see from outside.)

### 4. The speaker nubs — projection, width, height
Currently 4 × 8 × 6 mm. These set the front module's posts *and* the floor seats,
and they drive the machine's overall height. The Seeed body is confirmed
50 × 45 × 22; it's the nubs that aren't.

---

## What I'll look up rather than ask you for

TPA2016 breakout, DS3231, BH1750, VL53L0X, seesaw encoder, XIAO ESP32-S3, the
linear-4 mic array, and the speaker body — all published. **Tell me which DS3231
you have** (Adafruit sell several) and I'll pull the right one.

---

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

### Board mounting-hole spacing — five boards
For each of these I print a pair or a square of posts that the board bolts onto.
If the spacing is wrong the board simply doesn't line up, and the posts are
solid printed plastic.

| Board | What it is | Currently guessed |
|---|---|---|
| Rotary encoder | the Adafruit seesaw breakout under the knob | 20 mm across |
| Time-of-flight | the VL53L0X distance sensor on the crown | 20 mm, front-to-back |
| Real-time clock | the DS3231, upper-left of the rear wall | 20 mm square |
| Light sensor | the BH1750, behind the pinhole | 15 mm square |
| Amplifier | the TPA2016, on the floor | 20 mm across |

Slack: the RTC's pitch could grow to about 38 mm before it hits anything. The
encoder and ToF sit closest — about **10.5 mm** of growing room before their
posts collide with each other, and neither pitch can exceed its own board.

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

> ✅ **Done — the clock matrix stack height.** Measured at **7.0 mm from the front
> face of the matrix to the back of the joined backpack**. The model had assumed
> 8.2 (two 1.6 boards plus a guessed 5.0 header gap); the real gap is 3.8.
> That 1.2 mm was the single most consequential number in the part: the six
> retaining clips hook the *back* of this stack, so it is their lever arm, and
> strain goes as 1/L². It moved them from 1.20 % to 1.83 % — past the PLA limit —
> and the clips had to be retuned. It is recorded as the height you measured,
> with the header gap derived from it.

> ✅ **Done — the array's screw holes.** Measured at **22 mm from the end of the
> board to the near edge of the hole**. The boss centres moved from a guessed
> 40 mm to **31.4 mm** from centre (22 + half of an M3 clearance hole, measured
> back from the 110 mm board's half-length). The figure recorded in the source is
> the edge distance you measured, with the centre derived from it — so it can be
> re-checked against the board rather than taken on trust.

---

## 3. Tune on a test print, don't measure

### The air gap behind the diffuser
Currently 12 mm. This is the distance from the LEDs to the acrylic and it decides
whether you see 48 distinct dots or one smooth arc. There's no right answer on
paper — print a small test piece with two or three gaps and look at it in a dark
room. Too small and it's dotty; too large and it's dim and the machine gets
deeper.

---

## 4. Settled from Adafruit's own board files — do not re-measure

These came out of the EAGLE sources on Adafruit's GitHub, so they are exact and
`check_docs.py` now asserts them.

| Value | From | Notes |
|---|---|---|
| Matrix outline **43.18 × 27.94**, R2.54 | `CharliePlex Grid.brd` outline wires | The driver is identical — lady ada's guide says they deliberately made it "as large as our 0603-LED 16x9 matrix grids". |
| Matrix holes **Ø2.0 at (1.905, 26.035) and (41.275, 1.905)** | `Grid.brd` `<plain>`, verbatim `<hole>` tags | **Top-left + bottom-right**, board seen from the LED side. |
| Driver mounting holes **Ø2.5 plated, 3.2 pad** | `Breakout.brd`, package `MOUNTINGHOLE_2.5_PLATED` | So **M2.5** screws. Positions still unknown — see below. |

> ### ⚠️ The matrix diagonal went wrong twice, in opposite directions
> Adafruit's file gives the holes in **board** coordinates — the board seen from
> its component side, the LED side. The board is installed with the LEDs facing
> **forward**, so its frame is 180° from the part's and one in-plane axis has to
> invert on the way in. Reading the vendor numbers straight into part coordinates
> skips that inversion and mirrors the pattern.
>
> That is exactly what happened. The original was mirrored; it was corrected from
> the bench (rightly); then "corrected back" when the vendor file surfaced, on the
> reasoning that published data outranks an eyeball. **The data did outrank the
> eyeball — but data still has to be transformed into the frame you are using it
> in, and the person holding the printed part is measuring the frame you actually
> shipped.**
>
> Part-frame answer: **bottom-left + top-right**, which is what you see from the
> back — the view the slicer gives you with the facade on the bed. The flip is now
> applied in code, so the vendor numbers stay quotable *and* the transform is
> visible; `check_docs.py` asserts both the source values and the flipped result.

---

### Still needed: where the driver's Ø2.5 holes actually are
Confirmed they exist (plated, Ø2.5 drill, 3.2 mm pad — M2.5 screws). Their
**positions** are placed as `<element>` entries near the end of the board file,
and every fetch of that file truncates before them, so I could not read them.

Fastest ways to settle it, in order:

1. Open the **fab print** on the [downloads
   page](https://learn.adafruit.com/i31fl3731-16x9-charliplexed-pwm-led-driver/downloads)
   — "STEMMA QT Schematic and Fab Print", the second image. It is dimensioned in
   inches and will show the hole centres directly.
2. Or just measure the board: centre-to-centre both ways, and from one corner.
3. Or open `Adafruit IS31FL3731 STEMMA QT.brd` in EAGLE/Fusion and read them off.

Needed before the backpack-mounted version can be built, along with the **mated
height** of your female header plus the matrix's pins — that sets the boss
height, and a guessed stack height is what caused the last round of trouble.

---

## 5. Assembly steps the model can't do for you

### Mic port gaskets — needed, not optional
The array **deliberately does not sit flat** on the floor of its channel. It
seats on four raised Ø4.5 rings, one around each Ø2.5 port, leaving a 0.6 mm gap
everywhere else. That gap is there for a **thin adhesive foam gasket** on each
land (about 1 mm uncompressed, with a Ø2.5 hole punched through).

Printed plastic pressed against a PCB does not seal — it leaks through the layer
lines. A leaking port lets sound reach the microphone by two paths at slightly
different times, which is precisely what the XVF3800's beamforming and echo
canceller assume isn't happening. The port itself is fine (Ø2.5 × 2.6 mm long,
first resonance ~23 kHz, well above anything that matters), so the gasket is the
only thing standing between this working and not.

Two of the four ports sit 18 mm outboard of the nearest fixing screw, so the
board's ends are held flat by the lands rather than pressed onto them — another
reason to use a compliant foam rather than relying on contact.

---

## 6. Nice to confirm, low risk

- **Board outlines** — the light sensor (20 × 18), ToF (17.8 × 25.4) and encoder
  (25.4 square) breakouts. These only matter for the clearance checks, not for
  anything printed. The RTC (25.4 × 17.8) and the amp (21.59 × 27.94) are no
  longer guesses — both came out of vendor files.
- **UPS pack depth** — 24 mm guessed for board plus cells. Width and height (60 ×
  93) are from the DXF.

---

## When you have the numbers

Give them to me in any form — a list, a photo of your notes, whatever. I'll
update `enclosure_geom.py`, re-run everything, and tell you which clearances
moved and whether anything now fails. Several of these interact (the nub size
feeds the overall height, the cloth feeds the groove), so it's worth doing them
as one batch rather than one at a time.
