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
| Voice / DSP front end | **ReSpeaker Flex, Linear 4-mic (XVF3800)** | 4-mic beamformer + acoustic echo canceller (AEC). The XIAO seats into it via **female headers (removable, not soldered)**. |
| Codec | **AIC3104** (on the Flex) | I2C `0x18`. ESPHome `audio_dac` platform `aic3104`. |
| Amplifier | **TPA2016D2** stereo Class-D | I2C `0x58`. One 4Ω speaker per channel. See "Amplifier notes" below. |
| Speakers | 2× 4Ω drivers | Bridge-tied outputs (see wiring cautions). |

The XVF3800 was **DFU-flashed with the 48 kHz Home Assistant I2S firmware**; the
whole audio pipeline runs at 48 kHz to match.

**Flashing caveat:** the ReSpeaker Flex's internal USB (JST) only exposes the
XVF3800, *not* the ESP32. Flashing the ESP32 therefore requires disassembly to
reach the XIAO's own USB-C. This is an accepted tradeoff.

---

## Light

| Block | Part | Notes |
|-------|------|-------|
| Crescent strip | **SK6812 GRBW**, 60 LED/m (16.7 mm pitch) | **48 pixels** arranged as a half-circle crescent. Data on **GPIO1 / D0**. Driven by ESPHome `esp32_rmt_led_strip` (chipset SK6812, `rgb_order: GRB`, `is_rgbw: true`). |

Row layout (bottom row first, flat side down), used by the Circadian Sunrise
effect: widths 160/158/151/139/119/88/20 mm → **9 / 9 / 9 / 8 / 7 / 5 / 1 = 48**.

> **History / drift:** earlier design notes referenced a **144 LED/m** strip and
> an **XL6009 boost converter** for the LED rail. The current build is **60 LED/m,
> 48 px, powered directly from the UPS 5V rail** — the boost converter is no
> longer part of the power path. See the reconciliation note in
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
| Ambient light | **BH1750** | `0x23` | **Implemented** — feeds display auto-dim (`packages/display.yaml`). Mounted rear, behind a light pipe. |
| Rotary encoder | **Adafruit seesaw rotary encoder** | `0x36` | **Implemented** — volume knob + push (tap/hold) via the vendored `seesaw` component. |
| Real-time clock | **DS3231** (driven as `ds1307`) | `0x68` | **Implemented** — battery-backed time source; HA syncs it when connected. |
| Time-of-flight | **VL53L0X** | `0x29` | **Planned, NOT yet in firmware.** Part of the build — intended for touchless wake (distance in inches). Only a logger line references it today; no `vl53l0x:` sensor exists yet. |

> The BH1750, seesaw and DS3231 are live in the config. The **VL53L0X is on the
> bus plan and in the address map but has no ESPHome entity yet** — adding it is
> open work (see [`SOUNDMACHINE.md`](SOUNDMACHINE.md)).

---

## Power

| Block | Part | Notes |
|-------|------|-------|
| Pack / UPS | **Waveshare UPS Module 3S** (3× 18650 in series) | Provides the **5V / 5A** rail. Runs charge + discharge simultaneously (true UPS). |
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
| TPA2016 into 2× 4Ω at clipping | ~1.3 A |
| Flex + XVF3800 + ESP32-S3 + sensors | ~0.5 A |

The crescent is **hard-capped at 65% of full white** in firmware
(`led_max_pct`, applied via `color_correct`) → ~1.9 A for the strip, ~3.7 A
total of the 5 A budget. This is a physical PWM ceiling, not just a UI limit,
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
| GPIO4 | D3 | Capacitive preset touch pad | ESP32-S3 native touch (`esp32_touch`) |

Notes:
- **D4/D5 for the audio/sensor I2C is the tested, source-of-truth mapping** — do
  not "correct" it from schematic-derived assumptions.
- **Verify D0/GPIO1 is exposed and unused** on the Flex breakout pads (the LED
  data line moved here because GPIO43 now belongs to the I2S mic).
- The capacitive touch threshold (`touch_threshold`) must be **calibrated** via
  `esp32_touch: setup_mode: true` before it works reliably.
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

Five-part frame architecture, main body ~184×64×135 mm: main body, front
facade, bottom plate, LED bracket, charging base. Zone-based internal layout
(crescent LED panel zone → mid clock zone → lower speaker zone → floor). Front
facade is acoustic grille cloth over a T-shaped white opal cast-acrylic diffuser
(Glowforge-cut). Access is via a bottom slide-in plate. CAD in Fusion 360.
