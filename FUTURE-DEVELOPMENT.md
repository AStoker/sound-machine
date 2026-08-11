# FUTURE DEVELOPMENT

Everything still to do on the sound machine, one entry each. Prototype 1 is built
and in service, so nothing here blocks *use* — these are improvements, unverified
assumptions, and one hardware fix that is currently costing real capability.

Entries are stably numbered so they can be referenced from code comments and
commit messages (`H1`, `C2`, …). **Do not renumber a completed entry** — strike it
and leave the number dead.

| | | |
|---|---|---|
| **[H — Hardware](#h--hardware)** | H1 bulk capacitance · H2 shunt value · H3 touch electrode | needs a soldering iron |
| **[C — Calibration](#c--calibration)** | C1 ToF thresholds · C2 gesture timing · C3 noise gain · C4 dim curve | needs the assembled machine |
| **[V — Validation](#v--validation)** | V1 AEC over noise · V2 sunrise on the final crescent · V3 `(?)` constants | needs measuring, not changing |
| **[F — Features](#f--features)** | F1 touchless wake | not built |
| **[T — Tech debt](#t--tech-debt)** | T1 blanket `except ImportError` · T2 stability foot span | optional |

---

## H — Hardware

### H1. Install the brownout-fix bulk capacitance ⭐ highest value

**The one hardware task left, and it is currently costing three quarters of the
crescent's brightness.**

The ESP32 resets on transient rail sag. The diagnosis is settled; the fix has not
been fitted. What is standing in for it is `led_max_pct: 25%`
([`packages/settings.yaml`](packages/settings.yaml)), which caps the strip at
~0.73 A so the transient stays under the trigger point.

**What to fit**
- 470–1000 µF low-ESR electrolytic **+** 1–10 µF X7R ceramic at the Flex board's
  power input terminals, **physically close to the terminals**.
- An input-side cap on the LED supply.
- Then verify the wiring/feed topology to the strip — a long thin feed is its own
  problem and capacitance will not rescue it.

**Two things that make this counter-intuitive, and are why 25% looks excessive**
1. **The paper budget was never the constraint.** The cap used to be 65% — ~1.9 A
   for the strip, ~3.7 A of a 5 A rail, comfortable — and it still browned out.
   The failure is the *transient*, not the average.
2. **It cannot self-recover.** The SK6812s latch their last frame independently of
   the MCU, so once the rail sags enough to reset the ESP32, the strip keeps
   drawing the same current straight through the reboot loop.

**Acceptance test.** Raise `led_max_pct` in small steps, watching for a reset
during a **sunrise ramp** (worst case — a rising current step across all 48 px)
and during loud audio. Full white at 100% is ~2.9 A for the strip; simply getting
back to 65% is a **2.6× improvement in output**.

**Related tell.** The IS31FL3731 matrices have no NVM and revert to their
power-on state after a rail glitch, so unexplained display corruption is
independent evidence the rail dipped even if the ESP32 survived.

> **Until this is done, `led_max_pct` is a safety limit, not a brightness
> preference.** It is flagged as such in `CLAUDE.md`, `HARDWARE.md` and inline in
> `settings.yaml`, because a dim light invites exactly the wrong fix.

### H2. Verify the UPS shunt value

`ups_shunt_ohms` (`0.01 Ω`) comes from the module's documentation and has never
been measured. The monitor itself is **confirmed** — INA219 at `0x41`, sign
convention correct — so this is the last unverified term in the power chain.

- **What depends on it:** absolute **current** and **power** readings.
- **What does not:** bus voltage, per-cell voltage, and state-of-charge. This is
  why it has survived unmeasured — nothing user-visible is obviously wrong.
- **Current evidence:** ~0.15 A idle, plausible against the estimated draw. That
  estimate is not a measurement, so this is consistency, not verification.
- **How:** meter in series with the pack, compare against `Battery Current`. If
  the reading is ~10× off, this is why.

### H3. Settle which touch electrode is installed, then re-calibrate

**The as-built state is not recorded and should be.** Two different electrodes
are documented and only one is in the machine:

| | Designed | What was calibrated |
|---|---|---|
| Pads | 2 × 40 × 22 mm shoulder strips, one net | 1 × 76 × 76 mm copper tape |
| Wall | thinned locally to 1.6 mm | full 2.5 mm, unthinned |

`touch_threshold: 2500` was measured against the second. If the machine now has
the designed pads, **that number is calibrated for the wrong electrode** — a
smaller pad at a shorter dielectric distance moves both the baseline and the
finger delta.

**How to re-calibrate:** set `touch_setup_mode: "true"`, watch `difference=` in
the logs untouched versus held, set the threshold between the noise ceiling and
the weakest press. Bias **high** within that gap: the realistic false triggers are
a hovering hand and gripping the dome to move it, neither of which shows up in a
quiet bench sample.

> **Check `value` before `difference`.** If it reads exactly **4194303** the
> counter is saturated and no threshold can work — that is the
> `measurement_duration` bug, documented in `packages/hw/touch.yaml`, not a
> wiring fault.

---

## C — Calibration

### C1. Calibrate the ToF proximity thresholds

`tof_near_m` / `tof_far_m` (**0.25 / 0.40 m**) are still guesses, never measured.
The VL53L0X is live in `packages/hw/proximity.yaml` but only pre-illuminates the
knob NeoPixel when a hand comes near.

**How:** watch the **Knob Proximity** binary sensor while reaching for the knob
and adjust until it leads your hand without firing across the room. Low stakes —
the knob-pixel feature degrades gracefully to volume-only if the sensor is absent.

**Three fixes have already landed for "it doesn't see my hand", so try these
before moving a threshold** — a threshold was never the reason:

1. **`long_range: true`.** A palm reflects a few percent of 940 nm; the
   datasheet's white target reflects ~88 %. Short range's 0.25 MCPS signal-rate
   limit was rejecting the return outright. Long range drops it to 0.10.
2. **`timing_budget: 50 ms`** (was the ~33 ms default) — more photons per
   measurement, so a weak return separates from noise.
3. **Unresolved readings are now ignored, not counted as "far".** The component
   publishes the range register without the range-status byte beside it, so a
   failed measurement arrives dressed as a distance of a few centimetres. One of
   those in the middle of a hover reset the confirm counter, and asserting needs
   two *consecutive* near samples — so the assert frequently never happened.
   `tof_min_valid_m` rose 0.03 → 0.05 to catch them, and
   `tof_invalid_hold_samples` (12 ≈ 3 s) leashes how long they may be ignored.

**Diagnose before tuning.** Set `tof_log_level: DEBUG` and read the raw
distances: an idle sensor showing a small fixed number means unresolved reads or
something in its 25° cone; a hand reading nothing at all means sensitivity; a
hand reading the *right* distance with no pixel means the thresholds — and only
then is this entry the thing to work on.

### C2. Widen the gesture timing dead band

`gesture_tap_max` is **0.8 s** and `gesture_hold_min` is **1 s**, so a press
between them matches neither `on_multi_click` timing and **fires nothing**.

A measured quick tap landed at exactly 0.80 s — right on the edge. If taps feel
unreliable, this is the mechanism, not the touch threshold. Deliberately not
changed yet: taps may get shorter once there is feedback to tap against.

Applies to **both** the touch pad and the knob switch — they share these settings
on purpose so the two controls feel identical.

### C3. Tune the brown-noise high-pass makeup gain

Currently set by ear (160 Hz, 12 dB/oct, ×4.00 makeup). Worth a second pass now
that the speakers are in sealed boxes on a braced facade rather than loose on a
bench — the acoustic load has changed.

### C4. Tune the display auto-dim curve

The BH1750 → brightness mapping is a log curve deliberately biased dark, with the
3 a.m. near-black target being the case that matters. Verify in an actually dark
bedroom rather than a dim room.

---

## V — Validation

### V1. Validate AEC / wake word over playing noise, in the enclosure

Wake-word-over-noise is the central audio constraint of the whole design and has
**never been tested in the assembled machine** — which is the only place the
acoustic path is real. The speakers now sit in sealed boxes bolted to a braced
facade with the mic array directly above them; none of that was true on the
bench.

**Re-test whenever anything in the audio chain changes.** In particular the
TPA2016's AGC is off (compression 1:1) *deliberately* — the XVF3800's echo
canceller can only cancel a linear path, and an active compressor downstream of
the DAC makes it time-varying. Do not enable compression without re-running this.

### V2. Re-check the Circadian Sunrise against the final crescent

The effect fills whole rows bottom-up and was written for a fuller apex. The
final layout is 6 rows of `{10, 10, 9, 8, 7, 4}` at 10.4 mm pitch, so vertical
gradients have less travel than the effect assumes and the apex is sparse.

Watch a full sunrise at speed and check the top rows do not band or arrive early.

### V3. Measure the remaining `(?)` constants

`3d-print/MEASURE-ME.md` lists every constant still marked `(?)` in
`enclosure_geom.py`, and `check_docs.py` enforces that list in both directions.

**Prototype 1 was printed with all of them still guesses and it went together** —
which is not the same as the guesses being right. It means nothing that failed
depended on them, and the tolerance they consumed is unknown. They are now easier
to measure on the assembled machine than on the loose parts the list was written
for, and they matter for a reprint or a v2.

---

## F — Features

### F1. Touchless wake gesture

Designed but never implemented. The VL53L0X was originally specified for a
touchless wake — wave a hand to bring the machine up — and today nothing but the
knob NeoPixel reads the sensor (see C1).

The hardware is present and live, so this is purely firmware: a distance
threshold, a debounce, and a decision about what "wake" should do that does not
collide with the existing tap/hold gestures.

---

## T — Tech debt

### T1. Remove the blanket `except ImportError` from the remaining generators

Five generators in `3d-print/` still wrap large blocks in a bare
`except ImportError`. This pattern once silently skipped the dome's **entire**
mesh validation — watertightness, body count, board envelopes — for an unknown
number of runs, because the message named the wrong missing package.

They all pass today because the dependencies are present, which is exactly what
makes it easy to leave. See the retrospective, §1.

### T2. Optional — widen the foot span for stability

~55 gf topples the machine from the top. That is not the battery's fault (mass low
down helps); it is 156 mm of height on a 39 mm foot span. `FOOT_IN` is 16 mm
today; **8 mm gives ~1.5× the shove resistance** and still leaves the foot 2 mm
inside the wall line.

A v2 geometry change, not a repair — the machine is stable in normal use, with
14.6 mm of static tipping margin and 10.6° of backward tilt tolerance.

---

## Done

Kept briefly so a settled question is not re-opened. Detail in
[`RETROSPECTIVE.md`](RETROSPECTIVE.md) and `SOUNDMACHINE.md` §3.

- ~~**Confirm the UPS monitor address and part.**~~ INA219 at `0x41`, confirmed on
  the boot scan and reading consistently; sign convention confirmed (discharge
  negative). Shunt value still open — see H2.
- ~~**Calibrate the capacitive touch threshold.**~~ `touch_threshold: 2500`, from
  64 untouched samples and 5 presses. Re-opens as H3 if the electrode changes.
- ~~**Fix the touch pad never registering.**~~ ESPHome derives
  `charge_times = 65535` from its default `measurement_duration`, saturating the
  S3's 22-bit counter so the delta is permanently 0. `measurement_duration` is now
  set explicitly in `packages/hw/touch.yaml`.
- ~~**Finalise the bottom plate geometry.**~~ Was blocked on the battery-retention
  decision; resolved by the Waveshare 3S UPS, and printed.
