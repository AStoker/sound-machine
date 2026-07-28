# HARDWARE.md

Physical hardware for the Sound Machine (the "Faux Hatch"): a bedside smart
sound machine inspired by the Hatch Restore form factor — noise, voice
assistant, sunrise light, 7-seg clock, and environmental sensing.

This file is the single reference for *what the parts are and how they connect*.
For **why the firmware is shaped the way it is**, see [`CLAUDE.md`](CLAUDE.md).
For the **project story and goals**, see [`SOUNDMACHINE.md`](SOUNDMACHINE.md).

> **Ground truth:** the tested configuration in the repo YAML is authoritative,
> not this prose. Where a value below is marked *UNCONFIRMED / placeholder* it
> has not yet been verified on the bench — confirm against the boot I2C scan
> before trusting it.

---

## Compute + audio core

| Block | Part | Notes |
|-------|------|-------|
| MCU | **Seeed XIAO ESP32-S3** (seats into the ReSpeaker Flex) | ESP-IDF framework, octal PSRAM @ 80MHz. `board: esp32-s3-devkitc-1`, `flash_size: 8MB` (16MB only if using the "Plus" variant). A **standard (non-Plus) XIAO ESP32-S3 is a functional drop-in** — only D0, D4/D5, D6–D9 are used, so no rear castellated pads are required. |
| Voice / DSP front end | **ReSpeaker Flex, Linear 4-mic (XVF3800)** | 4-mic beamformer + acoustic echo canceller (AEC). Split architecture: a core board plus a separate **linear-4 array board, 110 mm long with 33 mm mic spacing** (2× M3 mounting holes), joined by a 200 mm 24-pin FPC ribbon. The XIAO seats into the core board via **female headers (removable, not soldered)**. **Core board dimensions are not published** — measure them; the enclosure reserves a bay rather than assuming a size. |
| Codec | **AIC3104** (on the Flex) | I2C `0x18`. ESPHome `audio_dac` platform `aic3104`. |
| Amplifier | **TPA2016D2** stereo Class-D | I2C `0x58`. One 4Ω speaker per channel. See "Amplifier notes" below. |
| Speakers | 2× **Seeed Mono Enclosed Speaker 4Ω 5W** (SS114993346) | **50 × 45 × 22 mm sealed box** — a square-bodied enclosure, not a bare round driver. Bridge-tied outputs (see wiring cautions). The 5W rating is pure headroom — the amp tops out ~2.5W/channel into 4Ω, so the drivers loaf and can't be overdriven. **The 50 mm body width is what sets the enclosure width** — see the drawing set. |

The XVF3800 was **DFU-flashed with the 48 kHz Home Assistant I2S firmware**; the
whole audio pipeline runs at 48 kHz to match.

**Flashing caveat:** the ReSpeaker Flex's internal USB (JST) only exposes the
XVF3800, *not* the ESP32. Flashing the ESP32 therefore requires disassembly to
reach the XIAO's own USB-C. This is an accepted tradeoff.

---

## Light

| Block | Part | Notes |
|-------|------|-------|
| Crescent strip | **SK6812 GRBW**, 60 LED/m | **48 pixels** in **6 cut segments**. MEASURED strip: ribbon **10.0 mm** wide, cut-line pitch **16.5 mm**, **2.13 mm** thick. Data on **GPIO1 / D0**. ESPHome `esp32_rmt_led_strip` (SK6812, `rgb_order: GRB`, `is_rgbw: true`). |
| LED carrier | printed plate, **part 6** | Holds the six segments at the 12 mm standoff; screws to the back of the front module. See [`3d-print/README.md`](3d-print/README.md). |
| Diffuser | Glowforge-cut opal acrylic, **part 7** | 3 mm, generated as [`3d-print/diffuser.svg`](3d-print/diffuser.svg). **Notched** — see below. |

The crescent is a **flattened half-ELLIPSE, 89 × 62.7 semi-axes** — not a half
circle. The crown was flattened (`CROWN_K = 0.74`) to get the dome printable in
one piece on a 220 bed, so the arch is 0.74 × as tall as a true semicircle.

Row layout, bottom row first, flat side down — used by the Circadian Sunrise
effect:

| row | chord | px | ribbon (n × 16.5) | y above baseline |
|-----|-------|----|--------------------|------------------|
| 0 | 177.8 | 10 | 165.0 | 2.60 |
| 1 | 174.1 | 10 | 165.0 | 13.00 |
| 2 | 165.2 | 9 | 148.5 | 23.40 |
| 3 | 150.0 | 8 | 132.0 | 33.80 |
| 4 | 126.3 | 7 | 115.5 | 44.20 |
| 5 | 87.7 | 4 | 66.0 | 54.60 |

**Row pitch is 10.4, not 16.5.** It is derived, not chosen: the flattened crown
leaves only 62.7 mm of height, so the pitch is whatever gets the most pixels on,
floored at the **ribbon width** — the rows BUTT, edge to edge. That floor used to
carry a 1 mm gap and it cost three pixels: at an 11.0 pitch the crescent holds
45, at 10.4 it holds the whole 48-px reel on the same shell height. Closing the
gap was free. The grid is deliberately not square — rows are much closer together
than the pixels within a row.

**There is no fade band.** The LED field *is* the diffuser ellipse; the old
R96-inside-R117 arrangement with a 21 mm unlit band is gone. Tightest
LED-body-to-diffuser-edge gap is **2.95 mm**.

> ### ⚠️ What sets the pixel count: the ribbon, not the LED
> Every earlier layout measured the **LED body**. The thing that has to fit the
> cavity is the **ribbon**: a cut segment of *n* pixels is `n × 16.5 mm` long,
> not `(n−1) ×`, because the cut lines sit half a pitch outboard of the end LEDs
> and you cannot trim past them without losing the solder pads. On the bottom row
> that is 6.9 mm more than the LED span — an 11-pixel row is a 181.5 mm strip
> going into a 181.0 mm cavity. It never fit.
>
> The ribbon is also 10.0 mm tall against the LED's 5.2, so what must fit is a
> **rectangle**, and its binding corner is the top one.
>
> With the rows butting, `CROWN_K = 0.74` holds exactly **48** — the whole reel.
> It held only 45 while the pitch carried a 1 mm gap, and recovering 48 that way
> would have needed `CROWN_K = 0.80` and a taller shell.
>
> The cap lives in `enclosure_geom.ribbon_cap()` and is folded into
> `_crescent_row_cap()`, so it cannot be silently missed again.

> ### ⚠️ The grid is strongly non-square
> Rows are **10.4 mm** apart — butted, ribbon edge to ribbon edge — against
> **16.5 mm** between pixels along a row. A sweep up the crescent therefore
> covers ground far faster than the same sweep across it. **Any effect with
> vertical structure needs re-checking against this**, the Circadian Sunrise
> especially. Row 5 is 4 px, so there is no single-pixel apex.

`packages/lighting.yaml` carries `num_leds: 48` and
`leds_per_row[] = {10, 10, 9, 8, 7, 4}`. `enclosure_geom.crescent_rows()` is the
source of truth; `gen_drawing.py` prints the table on every run.

> **History / drift:** earlier design notes referenced a **144 LED/m** strip, an
> **XL6009 boost converter** and an **R80 / R96 / R117 circular** crescent. The
> current build is **60 LED/m on a flattened ellipse, powered directly from the
> UPS 5V rail** (~1.9 A at the 65% cap). See the reconciliation note in
> [`SOUNDMACHINE.md`](SOUNDMACHINE.md).

---

## Display

| Block | Part | Notes |
|-------|------|-------|
| Clock | **Adafruit HT16K33 4-digit 7-segment** ([#1002](https://www.adafruit.com/product/1002)) | I2C `0x70`. **Now an OPTIONAL alternative** to the matrix display — the matrix is the active clock (see Optional/experimental). Driven by **raw I2C writes** (init + rendering both in `packages/display.yaml`), not a stock ESPHome display platform. Auto-dims from the BH1750. Load `display` *or* `matrix`, never both. |

**Power note (open item):** the HT16K33 is a 5V part on a shared 3.3V-logic I2C
bus. Best practice is to power it from a **dedicated 3.3V LDO off the 5V rail**,
*not* the XIAO's 3V3 pin, to avoid loading/level issues on the bus. Confirm the
as-built wiring matches this.

---

## Sensors (STEMMA QT I2C daisy-chain)

| Sensor | Part | Address | Status |
|--------|------|---------|--------|
| Ambient light | **BH1750** | `0x23` | **Implemented** — feeds display auto-dim (`packages/display.yaml`). Mounted rear, behind a light pipe **centred in the back wall** (see the enclosure drawing). |
| Rotary encoder | **Adafruit seesaw rotary encoder** | `0x36` | **Implemented** — volume knob + push (tap/hold) via the vendored `seesaw` component. |
| Real-time clock | **DS3231** (driven as `ds1307`) | `0x68` | **Implemented** — battery-backed time source; HA syncs it when connected. |
| Time-of-flight | **VL53L0X** | `0x29` | **Planned, NOT yet in firmware.** Part of the build — intended for touchless wake (distance in inches). Only a logger line references it today; no `vl53l0x:` sensor exists yet. Mounts on the **crown, just right of the volume knob**, board turned longwise front-to-back to clear the encoder breakout — see the enclosure drawing. |

> The BH1750, seesaw and DS3231 are live in the config. The **VL53L0X is on the
> bus plan and in the address map but has no ESPHome entity yet** — adding it is
> open work (see [`SOUNDMACHINE.md`](SOUNDMACHINE.md)).

---

## Power

| Block | Part | Notes |
|-------|------|-------|
| Pack / UPS | **Waveshare UPS Module 3S** (3× 18650 in series) | **60 × 93 mm board**, M3 mounting holes, cells in holders on the board. Provides the **5V / 5A** rail; runs charge + discharge simultaneously (true UPS). **93 mm will not lie down in a 59 mm interior, so the board STANDS VERTICALLY against the rear wall** (~24 mm deep — confirm with cells fitted). That also puts its barrel jack on the wall that has the cutout. |
| Charge input | **DC barrel jack** on the UPS board, **12.6 V 2 A** | **Not USB-C.** The only USB-C on the build is the XIAO's own flashing port, which is internal (see the flashing caveat above). The enclosure therefore needs a barrel-jack cutout in the rear wall, not a USB opening. Jack body clearance and its height on the board are **UNCONFIRMED** — measure the as-built. |
| Monitor | **INA219** (assumed) | I2C — **address is an UNCONFIRMED placeholder** (`ups_i2c_address`, currently `0x41`). Waveshare boards usually carry an INA219 at `0x40–0x43`; if readings are nonsense the part may be an **INA226** (swap `platform: ina219` → `ina226` in `packages/battery.yaml`). |
| Shunt | series shunt on the UPS board | **UNCONFIRMED** (`ups_shunt_ohms`, currently `0.01 Ω`). If reported current is ~10× off, this value is why. |

**Pack thresholds (3S, pack volts = per-cell × 3):**
full `12.6V` (4.20 V/cell) · low-warn `10.2V` (3.40 V/cell) · empty `9.0V`
(3.00 V/cell) · low-SOC flag at `15%`.

State-of-charge is **estimated from pack voltage** against a Li-ion OCV curve
(no coulomb counter on the board), so it reads low under heavy load (bright
sunrise + loud audio sag the pack) and recovers when the load drops. Treat
`<20%` as "plug it in," not a fuel gauge.

**Sign convention is unverified:** current is filtered `×-1` so discharge reads
negative. Confirm on the bench; if discharge reads positive, flip the comparison
in the `battery_charging` sensor and drop the multiply filter.

> **History / drift:** battery retention was previously an *open decision*
> (candidate: LiPo + USB-C, Qi2 wireless charging already ruled out). It is now
> **resolved in favor of the Waveshare 3S UPS module**, which also fixed the
> earlier undecided 5V-rail source for the LEDs and amp.

### Power budget (5V rail, 5A ceiling)

| Load | Worst-case draw |
|------|-----------------|
| 48× SK6812 RGBW, full all-channel white | ~2.9 A |
| TPA2016 into 2× 4Ω at clipping | ~1.3 A (set by the 4Ω load, not the 5W driver rating) |
| Flex + XVF3800 + ESP32-S3 + sensors | ~0.5 A |

The crescent is **hard-capped at 65% of full white** in firmware
(`led_max_pct`, applied via `color_correct`) → ~1.9 A for the strip, ~3.7 A
total of the 5 A budget. Unchanged by the enclosure work: the pixel count stays
at 48 however the crescent is reshaped. This is a physical PWM ceiling, not just a UI limit,
and it also keeps the sealed dome from overheating.

---

## Pin map

The ReSpeaker Flex fixes the I2S pins; everything else is on **one shared I2C
bus**, so no extra GPIO is consumed per peripheral.

| GPIO | XIAO pin | Function | Owner |
|------|----------|----------|-------|
| GPIO7 | D8 | I2S WS / LRCLK | Flex (fixed) |
| GPIO8 | D9 | I2S BCLK | Flex (fixed) |
| GPIO43 | D6 | I2S mic DIN | Flex (fixed) |
| GPIO44 | D7 | I2S spk DOUT | Flex (fixed) |
| GPIO5 | D4 | **I2C SDA** | shared bus (all sensors, display, codec, amp, XVF3800) |
| GPIO6 | D5 | **I2C SCL** | shared bus |
| GPIO1 | D0 | SK6812 crescent data | LED strip |
| GPIO4 | D3 | Capacitive preset touch — **both** shoulder pads, one net (TOUCH4) | ESP32-S3 native touch (`esp32_touch`) |
| GPIO2 | D1 | *reserved* — TOUCH2, free if the pads ever need splitting | — |

Notes:
- **D4/D5 for the audio/sensor I2C is the tested, source-of-truth mapping** — do
  not "correct" it from schematic-derived assumptions.
- **Verify D0/GPIO1 is exposed and unused** on the Flex breakout pads (the LED
  data line moved here because GPIO43 now belongs to the I2S mic).
- **Two touch pads on ONE pin.** Copper strips (~40 × 22 mm) bonded to the
  *inside* of each upper shoulder, both wired to GPIO4/D3. Self-capacitance
  sensing measures the whole electrode net, so two pads on one net behave as a
  single electrode that happens to be split in two — touching either half gives
  the same delta. One binary sensor, one threshold, no OR logic.
- **Join the two leads at the MCU, not across the crown.** Each pad's lead drops
  down the inside of its own flank to the floor and they meet at the XIAO. The
  wire count is identical either way, and it keeps a ~200 mm antenna out of the
  crown — which is exactly where the SK6812 data line, the I2S lines and the
  STEMMA chain all run. This is the one routing decision that makes or breaks it.
- Sharing costs: the baseline capacitance roughly doubles while the finger delta
  does not, so relative sensitivity drops (still comfortably usable), and a
  side-to-side sensitivity mismatch cannot be trimmed out with per-pad
  thresholds. **GPIO2/D1 (TOUCH2) is kept free as the escape hatch** — splitting
  to two channels later is one wire at the MCU plus a few lines of YAML.
- The touch threshold (`touch_threshold`) must be **calibrated** via
  `esp32_touch: setup_mode: true` before it works reliably. Thin the wall
  locally to ~1.6 mm behind each pad.
- **Watch for false triggers:** the shoulders are also where you grip the device
  to move it. If that bites, require a short hold rather than a tap.
- No SPI is used (the old MAX7219 display was replaced by the I2C HT16K33).

---

## I2C address map (single bus, GPIO5/6 @ 100 kHz)

| Addr | Device | | Addr | Device |
|------|--------|-|------|--------|
| `0x18` | AIC3104 codec | | `0x58` | TPA2016 amp |
| `0x23` | BH1750 ambient light | | `0x68` | DS3231 RTC |
| `0x29` | VL53L0X ToF *(planned)* | | `0x70` | HT16K33 clock |
| `0x2C` | XVF3800 | | `0x41`? | UPS INA219 *(placeholder)* |
| `0x36` | seesaw encoder | | `0x74` | IS31FL3731 matrix *(optional)* |

**Bus tuning:** the bus runs at **100 kHz** with a **1 ms timeout**. The slower
edges tolerate the extra cable capacitance and pull-ups from the STEMMA sensor
chain, which was starving the timing-sensitive XVF3800; the timeout gives the
XVF3800 room to clock-stretch while its firmware boots. If it's still flaky with
everything reconnected, drop toward 10 kHz.

---

## Amplifier (TPA2016) notes — read before touching audio

- **Stereo, bridge-tied outputs.** Every output terminal swings; there is **no
  output ground**. Do **not** common the two speakers' negative leads and do
  **not** tie any output to GND — either shorts half a bridge and can kill the
  amp.
- **Its AGC is deliberately OFF (compression 1:1).** The XVF3800's AEC can only
  cancel a *linear* echo path; an active compressor downstream of the DAC makes
  the gain time-varying and breaks wake-word-over-noise. All volume control
  stays in software (in the AIC3104 upstream).
- The chip has **no NVM** — a 5V-rail glitch reverts it to factory defaults
  (AGC back on). The custom `tpa2016` component rewrites its config at boot, and
  register write **order matters** (compression before gain).

---

## Optional / experimental

- **IS31FL3731 charlieplex 16×9 matrix** (`0x74`, STEMMA QT / I2C): **now the
  active clock display** (the HT16K33 7-seg is kept as a drop-in alternative —
  see the Display section). No native ESPHome component, so `packages/matrix.yaml`
  drives it with raw-I2C register writes. Pixel `(x,y)` → LED `x + y*16`; PWM byte
  at `0x24 + LED` (144 LEDs); enable regs `0x00–0x11`; bank select via command
  reg `0xFD` (`0x00` = frame 0, `0x0B` = function/config). It renders, in priority
  order, a low-battery **"LO"** warning → transient **preset code** (S1–S3 / L1–L3
  / OFF) → the live **RTC clock** (12h, blank leading zero, solid colon), driven
  by the shared 1s tick in `ambient.yaml` and auto-dimmed via `display_brightness`.
  A "Matrix: redraw" button forces a re-init after a glitch.
  - **Single vs dual:** the package tiles N panels side-by-side into one logical
    framebuffer (16·N wide × 9). `matrix_panels: "1"` brings up the left panel
    alone with a compact 3×5 font; `"2"` gives a 32×9 display with a 5×7 font for
    a real clock. Horizontal tiling: panel *p* owns logical columns
    `[16p … 16p+15]`. A second board needs its **ADDR jumper** moved off `0x74`
    (`0x75`/`0x76`/`0x77`) — set `matrix_address_2` to match. In single mode the
    second address is never touched, so an unwired 2nd board causes no I2C errors.
  - **Inter-panel gap:** two panels butted together leave a physical ~1-pixel
    dead column between them (`matrix_panel_gap`, default 1). The renderer lays
    content out in *physical* columns (gap included) and maps back to logical
    columns per draw, so the clock stays centred across the seam and 2-char codes
    fall one-per-panel. Raise/lower `matrix_panel_gap` if your panels sit farther
    apart or flush.

---

## Enclosure (context)

Main body **202 × 64 × 155.7 mm**. Form: a letter **"D" lying on its long flat
side, extruded along the depth** — flat bottom, straight sides, and a **flattened
half-ellipse** top (semi-axes `W/2` × `CROWN_K·W/2`), **concentric with the LED
crescent**. The crown is a *cylinder*, not a sphere: it curves in front view and
is flat in side view. Front facade is acoustic grille cloth over white opal
cast-acrylic (Glowforge-cut). Access is via a bottom slide-in plate. Fusion 360.

> ### ⚠️ The speakers are ROTATED 90°, and that is what made it printable
> The Seeed body is 50 × 45 with a nub centred on each **45 mm** face. Standing it
> on its side puts those nubs **top and bottom** instead of left and right, which
> takes the mounting post out of the WIDTH chain and puts it in the height — where
> there was slack — and narrows the body from 50 to 45. With the mic array also
> moved **above** the speakers, the middle of the facade only carries the 86 mm
> matrix pair rather than the 110 mm array.
>
> Together that took the body from **258 → 202 wide**, which is what lets the dome
> and the front module each print as **one piece** on a 220 bed. At 258 it was
> proven impossible: the best of ~40,000 orientations was still 9.2 mm over.
> Acoustically it is free — a sealed box with a round driver does not care which
> way up it is.
>
> **The flanks now carry nothing.** Two screws on one vertical centreline fix x, y
> and rotation between them, so there are no seat rings and no side ribs. The
> width chain budgets `SPK_FLANK = 1.0 mm` per flank as pure clearance and it
> butts straight onto the dome's rib keep-out — anything appearing there jams the
> module on assembly.

> **W and H are both derived, not chosen.** Width is set by what sits side by side
> on the facade: `W = 2 × (3.6 edge + 4 boss keep-out + 1 flank + 45 body + 1
> flank + 3 gap + 43.18 half-matrix) = 202`.
>
> The arch's horizontal semi-axis *is* `W/2`, so **every 2 mm of width adds
> `CROWN_K` mm of height**. `CROWN_K = 0.74` — flattening the crown is the only
> lever on height once the width is fixed, and it is not purely cosmetic: it also
> sets how much crescent there is to lay LEDs on. See the 45-pixel note above.
>
> ### ⚠️ The edge budget is the dome's RIB, not the outline
> The module **slides up a groove**, and the dome's retaining rib grips the outer
> `RIB_W` of its **back face** along both flanks and the arc. Anything standing
> proud of that back face inside the band — a speaker post, a stiffening rib, the
> diffusion cavity wall — **jams the module on assembly**. A 2D view cannot show
> this: on the flat it just looks like clearance to the outline, and the outline
> is not the constraint. So the width chain spends `BOSS_EDGE = RIB_W + 1`, not a
> driver clearance. Three consequences:
> - **`RIB_W` is 3 mm, not 5.** The rib only has to stop the module tipping
>   forward (the bottom plate already traps it), and the keep-out is multiplied
>   four times across the width. 5 → 3 gave back 4 mm of body width.
> - **`RIM_MIN` is derived, not chosen.** Walking out from the crescent —
>   `DIFF_MARGIN` + `CAV_WALL` + `BOSS_EDGE` + `REVEAL` — gives the smallest rim
>   the shell can physically carry. Only if that comes out under the aesthetic
>   minimum does 12 mm win.
> - **The bottom edge is exempt.** It is the open end the module slides in
>   through, and the bottom plate captures it there instead.
>
> `gen_front_plate.py` intersects every boss with this band and reports the
> volume, so it cannot regress silently.
>
> **The diffuser sits at the concentric maximum, and the LED field IS the
> diffuser.** The diffuser ellipse is `(W/2 − RIM_MIN) × (CROWN_K·W/2 − RIM_MIN)`
> = **89 × 62.7**, so the crescent is as big as the shell allows and the rim stays
> at 12 mm. There is no separate, smaller LED arc any more and no fade band — the
> field fills the ellipse and the glow reaches the edge.
>
> ### ⚠️ Clearance is a TRUE distance to the ellipse, not a chord
> Every earlier check measured how far a pixel sat from the crescent
> *horizontally* (the chord) and, at the apex, *vertically*. On a circle those
> agree with the real distance; **on an ellipse they do not**, and the binding
> case is the diagonal one — an outer pixel two rows down from the apex, where
> the boundary is falling away steeply. That is how a crown shipped with its top
> LED body standing **0.58 mm outside the diffuser** while every check read clear.
> `enclosure_geom.ell_dist()` now returns the true point-to-ellipse distance and
> everything downstream measures with it.

Parts, all generated as STLs in [`3d-print/models/`](3d-print/models/):
**dome** (open front + open bottom, integral rear wall) · **front module** ·
**bottom plate** · **LED carrier** · a printed **pebble knob** on the crown for the encoder. The
front module carries the clock matrices itself, so `matrix-tray.stl` is no longer
in the assembly — it survives as a standalone part.

The **front module is one printed part**: facade + diffuser pocket + diffusion
cavity + matrix posts and clips + speaker seats + mic channel. The diffuser
itself stays a
separate Glowforge-cut opal acrylic that drops into a pocket from behind. It
**slides up** into grooves in the dome and is trapped by the bottom plate — no
fastener touches the facade. The module is **wrapped in acoustically transparent
cloth**, so the groove is sized for cloth + module + cloth (5.6 mm for a 4 mm
module) and the module's own outline is shrunk by one cloth thickness so the
wrapped assembly still slides.

The **bottom plate is the chassis**. Fixing is **6× wall lugs**: pads that
project inward off the dome wall with a blind heat-set hole, so the screw comes
up through the plate and grabs the lug. Lugs sit at the perimeter where the plate
needs support anyway and cost no floor area — which matters, because the floor is
fully spoken for. There is **no lug on the front edge** (the speaker boxes own
both front corners, the tray owns the middle); the plate's front edge is captured
between the seating ledge and the front module's bottom edge instead.

Mounting inside:

| Part | Where | How |
|---|---|---|
| UPS 3S | rear wall, centred | Board **stands vertically**; M3 through its own mounting holes into posts/brackets rising from the bottom plate. Its barrel jack lines up with the rear cutout. |
| ReSpeaker Flex core | **rear wall, above the UPS** | Mounted **vertically**, flat against the wall on 3 mm standoffs, 4× M3. Bare board **52 × 70 × 20 deep** at the XIAO; the 3.5 mm jack and the mic ribbon overhang the two short (52 mm) edges, so reserve a **110 mm envelope** in that direction. Hole pitch **45 × 63** (measured 42 × 60 inside-edge to inside-edge, 2 mm edge to hole outside → Ø3). The rear wall is reachable the moment the front module is out, and this keeps the floor clear. |
| Linear-4 mic array | front module | 2× M3 into the mic channel behind the ports, with a gasket land per port. |
| TPA2016 | **rear wall, flush, beside the UPS** | Not a side wall: the sides are only vertical *below* the springing line and the speaker boxes own all of that; above it the sides are the curved crown, no good for a flat board. |
| Speakers | front module | **Hang on nubs, TOP AND BOTTOM, not a baffle bolt pattern.** The bodies are **rotated 90°**, so the two nubs — one centred on each 45 mm face — point up and down. Their landing face is **7 mm behind the speaker's front face**, so the module carries a **post above and below each body, on its vertical centreline**, 10 × 6 mm, standing 7 mm proud of the back face, with an M3 running front-to-back into it (inserted **from behind**, through the nub). **The flanks carry nothing** — no seat rings, no side ribs; two screws on one line fix x, y and rotation between them. |
| LED carrier | front module, behind the cavity | 2.5 mm plate, **6× M2.5** into ramped pads on the **inside** of the diffusion cavity wall. Screws, not clips — see the note below. |
| Diffuser pane | front module, in its pocket | Drops in **from behind** and is glued round its edge. It must pass the carrier pads on the way, so it carries six **round notches** at the pad angles — round because the pad is a cylinder, which makes the bite 26% smaller than a square one and so leaks 26% less undiffused light. Generated, not hand-drawn. |
| Clock matrices | front module, **directly** | ⚠️ **The two boards are only loosely soldered to each other**, so the frame cannot treat them as one part. Each board is located by its **own two posts** (Ø1.85 through its Ø2.0 diagonal holes) and seats on two pads in the clear margin above and below its LED field; the pair is then clamped by **six cantilever clips — two on each long edge, one at each end**. A pocket would locate the *pair*, and the pair is exactly the thing that is not rigid. No tray, no pocket. |

See sheet 2 of the drawing set for the joint, the fixings and the clearances,
and [`gen_front_plate.py`](3d-print/gen_front_plate.py) for the printable part.

> **The front module prints WHOLE.** At **194.8 × 148.1 mm** it fits a 220 mm bed
> (Flashforge Adventurer 5M Pro) with 25.2 / 71.9 mm to spare. It used to be
> 250.8 wide and had to split at x = 73.8 with a 5 mm Z-lap; rotating the
> speakers and lifting the mic array removed the need. The seam logic is retained
> in `gen_front_plate.py` behind `NEEDS_SPLIT` — currently **off**, and it
> re-enables automatically if anything pushes the part back over the bed.

> ### ⚠️ Why the LED carrier is screwed, not clipped
> A cantilever/snap arrangement is used elsewhere on this part (the clock
> matrices) and would be consistent — but it does not work here, for two
> independent reasons:
>
> **The clips would have nowhere to deflect.** A clip gripping the plate's edge
> has to flex *outward*, and outboard of the cavity wall there is **0.9 mm**
> before the dome's retaining-rib keep-out. That is the same budget that rules
> out outward mounting ears. Clips that deflect *inward* need the plate to sit
> inside the cavity, and then it cannot seat on the wall's back face — which is
> the datum the whole air gap is referenced to.
>
> **Clips hold a plate wherever the worst clip decides.** The carrier's one job
> is a uniform 12 mm standoff across a 185 mm span. Six screws pull it onto a
> hard seat and take up print variation; six clips leave it sitting on whichever
> hook came out proudest. On FDM, over that span, that is the difference between
> an even glow and a visibly brighter band.
>
> Screws also make the strips serviceable, which matters — five soldered
> segment-to-segment joints are the most likely thing on the build to need rework.

**The clock aperture is one open rectangle** — 84 × 23, no per-pixel holes.
Through a 4 mm facade a per-pixel tunnel would be a light pipe and would gut the
viewing angle; one open window avoids that and avoids a registration problem.

**Rear wall** (a true flat face, same "D" profile as the front — the body is an
extrusion). The BH1750 light pipe and the DC barrel jack are **centred on the
width**. The jack is a **panel-mount part on a flying lead**, not the UPS board's
own connector poking through, because the UPS is no longer centred.

> **The UPS and the Flex no longer stack.** The flattened crown took the interior
> height to 157.5 and 93 (UPS) + 70 (Flex) is 163. They sit **side by side** on
> the rear wall instead — UPS right (x 120–180, on the floor), Flex left
> (x 5–115, lifted to y=16 so it clears the fixing lugs). That is the one axis
> that got roomier when the array came off the flanks. The TPA2016 moved to the
> **floor**, in the 12 mm slot under the lifted Flex; the rear wall has no room
> left.

<!-- Canonical current state. check_docs.py asserts these against the geometry;
     do not reword them. Prose elsewhere explains WHY, these say WHAT. -->
**Vent stacks: 1** · **RTC mounts on: rear wall**

> **The rear wall is the most crowded face in the build** — UPS, Flex, amp, lux
> pipe, jack and vents all land on it, so `rear_wall_clearances()` checks every
> pair rather than trusting the eye. Two consequences:
> - **The vents are ONE wide stack above the light pipe.** This was two stacks
>   flanking the UPS, on the reasoning that a centred stack would sit behind the
>   Flex and bake it — true only of a stack placed *level with* the Flex. Lifted
>   clear above it (y 132–144, over the pinhole) a single stack has the same
>   objection answered, and the two flanking stacks were fencing off both upper
>   quadrants of the wall — the largest clear areas on it — for 432 mm² of
>   opening. One stack of 3 × 72 × 2 gives the identical free area and hands both
>   quadrants back. That is what let the RTC come off the bottom plate.
>   Slot height is capped by the louvre, not by space: the anti-peek geometry
>   only works while the slot is no taller than `VENT_RISE`, so the area is
>   bought with **width**, which is free.
> - **Both rear fixing lugs are left of centre** (x 55 and 105). The UPS owns the
>   rear-right corner of the floor. The plate is still carried at six points
>   round the perimeter, just not symmetrically.

Front-face layout, bottom-up: **speakers flank the matrix pair**, the **mic array
sits ABOVE both**, then the crescent, then the crown.

> ### ⚠️ The mic array clears the speaker BODY, not the post
> The array used to sit above `SPK_SEAT_Y1` — the top of the nub post — which
> lifted it 6.35 mm for no reason. The post is only **10 mm wide** and stands on
> the speaker's **centreline** (x = 31.1 and 170.9); the 110 mm mic PCB spans
> x = 46–156. They overlap in y by 3.35 mm and **never in x**, with 9.9 mm to
> spare. So the array only has to clear the body, and that 6.35 mm went into a
> shorter shell and a taller crescent.
>
> This is why post width is sized by the **nub** (`SPK_NUB_H + 2 × wall`) and not
> scaled off the body — a post at 0.60 × body width reaches x = 44.6 and hands
> the whole saving straight back.

> **Drawing set** — three generated sheets in [`3d-print/`](3d-print/), plus the
> README beside them for the constraints they turned up:
> [`enclosure-drawing.svg`](3d-print/enclosure-drawing.svg) (shell),
> [`enclosure-internals.svg`](3d-print/enclosure-internals.svg) (front module,
> joint, fixings, chassis), and
> [`enclosure-wiring.svg`](3d-print/enclosure-wiring.svg) (the I2C chain and
> where each board sits — generated from *this* file).

> **History / drift:** earlier notes described a **five-part** frame (main body,
> front facade, bottom plate, LED bracket, **charging base**) with a **T-shaped**
> diffuser. The charging base is gone — the UPS charges through a rear barrel
> jack — and the diffuser follows the crescent + clock aperture directly.
