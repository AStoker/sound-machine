# FUTURE DEVELOPMENT

Everything still to do on the sound machine, one entry each. Prototype 1 is built
and in service, so nothing here blocks *use* — these are improvements, unverified
assumptions, and one hardware fix that is currently costing real capability.

Entries are stably numbered so they can be referenced from code comments and
commit messages (`H1`, `C2`, …). **Do not renumber a completed entry** — strike it
and leave the number dead.

| | | |
|---|---|---|
| **[H — Hardware](#h--hardware)** | H1 bulk capacitance · H2 shunt value · H3 touch electrode · H4 ToF pinhole | needs a soldering iron |
| **[C — Calibration](#c--calibration)** | C1 ToF deviation thresholds · C2 gesture timing · C3 noise gain · C4 dim curve | needs the assembled machine |
| **[V — Validation](#v--validation)** | V1 AEC over noise · V2 sunrise on the final crescent · V3 `(?)` constants · V4 crescent green glitch | needs measuring, not changing |
| **[F — Features](#f--features)** | F1 touchless wake | not built |
| **[T — Tech debt](#t--tech-debt)** | T1 blanket `except ImportError` · T2 stability foot span · T3 mixer drain-wait fallback | optional |

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

### H4. Open up the ToF pinhole — it is blinding the sensor

**Diagnosed from a DEBUG log on the assembled machine; the fix is a print
change.** The VL53L0X reports a fixed **0.024 m, forever** — every sample between
0.020 and 0.030 over two minutes, sd ~0.0015. There is nothing 24 mm above the
crown. That reading is **optical crosstalk**: the emitter and the receiver share
one **3.5 mm** bore through the crown (`TOF_HOLE_D` in
[`3d-print/enclosure_geom.py`](3d-print/enclosure_geom.py)) with no barrier
between them, so emitted light reaches the receiver off the bore itself and the
chip ranges its own aperture. ST's guidance for a shared window is a larger
opening **and** a light-tight septum between the two optical paths.

**What to change** — one or both, cheapest first:

1. **Widen the bore** to ≥ 6 mm, chamfered on the inside so the wall leaves the
   25° cone immediately.
2. **Split it into two apertures** with a septum between emitter and receiver —
   the proper fix, and the one that survives a wider cone.
3. **Drop `TOF_STAND` (2.0 mm)** so the board sits against the skin. Every
   millimetre of standoff is another millimetre of tube in front of the cone;
   the file already says so.

**Until then, C1's baseline-deviation detector is what makes the feature work** —
it reads the *change* in the crosstalk return, which a hand does perturb by 10–20
mm against 1.5 mm of noise. That workaround should be **deleted** when this is
fixed, and plain distance thresholds put back; it is 40 lines of cleverness
standing in for a 3 mm drill.

**Acceptance test:** with the space above the knob empty, DEBUG shows
`Distance is out of range` (not a number). That is the sensor seeing the room.

---

## C — Calibration

### C1. ~~Calibrate the ToF proximity thresholds~~ → tune the deviation thresholds

**Superseded by measurement. There are no distance thresholds any more, because
the sensor does not measure distance in this enclosure** — see **H4**. It ranges
its own pinhole at a fixed ~0.024 m, so `tof_near_m` / `tof_far_m` are gone and
`packages/hw/proximity.yaml` now detects *deviation from a learned baseline*.

**Measured, from a 2-minute DEBUG log on the assembled machine:**

| | Reading | Deviation |
|---|---|---|
| idle (129 samples) | 0.020–0.030, mean 0.0245, sd ~0.0015 | ≤ 0.0055 |
| hand arriving | 0.036, 0.046 | +0.012, +0.022 |
| hand held over the knob | 0.011–0.019 | −0.013 to −0.006 |
| hand leaving | 0.028–0.038 | +0.003 to +0.013 |

`tof_deviation_near_m` **0.010** sits nearly 2× above the worst idle excursion
and below the weakest hand signal. Replayed against that log it produces **zero**
false fires across the idle stretch, asserts on the *second* sample of the hand
arriving, and releases 2.5 s after it leaves.

**Confirmed on hardware, and one thing it turned up.** A second log
(`soundmachine-logs-10`) shows the detector firing on every gesture — and
*chattering* through the middle of them: ON at 20:59:31.6, OFF at 36.6, ON again
at 37.0. The cause is that **the swing is not monotonic**. A hand hovering high
reads 0.030–0.049 and genuinely tracks height; a hand on the knob reads
0.010–0.020. So a descending hand's reading rises, then falls back *through* the
0.024 baseline — three or four samples of near-zero deviation in the middle of a
real gesture, which to a `|deviation|` test is an empty room.

`tof_release_samples` is therefore **8 (2 s)**, not 3 (0.75 s). Replaying that log
sample-by-sample: at 0.75 s the four gestures produce five lit spans (one split);
at 2 s they produce four, one per gesture, with ~2 s of tail. Longer merges
gestures that were a second apart.

**What to tune, and which way:** pixel lights on its own → raise
`tof_deviation_near_m`. Slow hand missed → lower it, or lower
`tof_confirm_samples`. Pixel drops out *mid-reach* → raise
`tof_release_samples`, that is the baseline crossing above. Pixel drops while the
hand rests there → the baseline is being dragged; lower `tof_baseline_alpha`.

**Also landed here, and worth keeping whatever happens to the optics:**

- The floor (`tof_min_valid_m`) rejects failed measurements — the component
  publishes the range register without the range-status byte beside it, so a
  failure arrives dressed as a distance. It is **0.005**, deliberately far below
  what a hand produces; it was briefly 0.05 on room-sensor reasoning and rejected
  every single sample.
- Unusable readings are *ignored*, not counted as "far", so one dropped sample
  mid-hover no longer resets the run of consecutive near samples that asserting
  depends on. `tof_invalid_hold_samples` (12 ≈ 3 s) leashes that.
- A **`heartbeat: 60s`** filter on the entity. Without it a live sensor seeing
  nothing and a sensor that died at setup were the identical entity — one number,
  never updating.
- **The entity can now show a hand at all.** It published on a `delta` of 0.02 m
  at 2 decimals — a gate *larger than the whole signal*, and a resolution at which
  the idle baseline and a hand on the knob both render as `0.02`. Ten minutes of
  log produced a handful of `0.02`s and looked broken. Now `delta` **0.002** and
  **3** decimals. Display-only either way — the debounce always ran off the raw
  value and was detecting hands the whole time — but a dead-looking entity is the
  first thing anyone checks, so it cost more than it saved.

> `tof_log_level` is on **DEBUG** while this is being watched. Put it back to
> `WARN` once you trust it; it is four log lines a second.

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

### V4. Confirm whether the RMT change fixed the crescent's green glitch

**A fix is applied and unverified.** Under Rainbow Arch, the top of the crescent
occasionally flashes green for well under a second. The diagnosis is settled; which
of two causes it is, is not.

**Why it is a transmission fault, not a rendering one.** Three facts, and they only
fit one way:
1. The effect *cannot* paint green there. Hue is `270° × (1 − radius)` and the top
   rows sit at `radius ≈ 1`, so they are hue 0 — **pure red**. Green needs
   `radius ≈ 0.55`, the mid-band.
2. Red is `00 7F 00 00` on a GRB + W strip. Slip the byte stream by **one byte**
   and `0x7F` lands in the green slot. The right bytes are arriving in the wrong
   slots.
3. Rows are in *data order, bottom row first*, so the top row is pixels 44–47 —
   the **tail of the chain**, which is where corruption in a WS28xx chain lands.

**What was changed** (`packages/hw/crescent.yaml`) — `use_dma: true`,
`use_psram: false`, `rmt_symbols: 1024`. The default non-DMA RMT ping-pongs on half
of 192 symbols, giving the encoder ISR ~115 µs of runway per refill with the buffer
in PSRAM; SK6812 latches on any gap over ~80 µs, so one late refill makes every
pixel downstream re-latch mid-stream, byte-shifted. That ISR competes with WiFi, the
I2S path and a busy 100 kHz I2C bus. 1024 symbols is sized so a *surviving* glitch
rules the RMT out rather than leaving it half-tested.

**Acceptance test.** Run Rainbow Arch for a long stretch, and specifically *with
noise playing and during voice-assistant activity* — ISR starvation correlates with
audio, so an idle-only test proves little.

**If it survives, stop tuning RMT numbers — it is the other cause.** GPIO1 drives
the strip at **3.3 V** into a part that wants VIH = 0.7 × VDD = **3.5 V**, with no
level shifter anywhere in `HARDWARE.md`, and the data line runs the crown beside the
I2S clocks and the STEMMA chain. Each pixel regenerates imperfectly, so edge jitter
accumulates over 48 hops and the tail misreads first — which matches the symptom
just as well. Fixes, cheapest first: 330–470 Ω series resistor at GPIO1 plus 0.1 µF
at the first pixel; one series diode on the strip's 5 V to bring VDD to ~4.4 V so
3.3 V clears the threshold; or a 74AHCT125 as the proper answer.

**Related:** [H1](#h1-install-the-brownout-fix-bulk-capacitance--highest-value) is a
plausible contributor either way — VIH is referenced to VDD, so rail sag moves the
threshold under a fixed 3.3 V drive.

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

### T3. Fallback if the mixer drain-wait stops holding track looping together

Track looping depends on the media pipeline reporting PLAYING → STOPPED at
end-of-file, which a mixer source only does once its `pending_playback_frames_`
counter drains to zero. The current fix makes every track wait for
`mixing_speaker->get_frames_in_pipeline()` to reach zero before starting, so the
source is never handicapped by a pre-existing backlog it cannot drain. Written
up in `packages/api/sound.yaml`; symptoms and mechanism in `SOUNDMACHINE.md` §3.

**It is a workaround for upstream behaviour, and upstream is not going to change
it** — [esphome/esphome#14641](https://github.com/esphome/esphome/issues/14641)
is closed as not planned, and as of 2026.7.2 `mixer_speaker.cpp`,
`resampler_speaker.cpp`, `speaker_media_player.cpp` and `audio_pipeline.cpp` are
all byte-identical to upstream `dev`. So an ESPHome upgrade could regress this
without any change here.

**The tell:** a track plays once, the media player entity stays at "playing"
forever, and every later track is silent until reboot — while noise still works.
That exact triple is this failure and nothing else.

**If it comes back**, the remaining option is to vendor `mixer` into
`components/` the way `seesaw` already is, and let `SourceSpeaker::loop()` leave
`STATE_RUNNING` on `stop_gracefully_` without also requiring
`pending_playback_frames_ == 0`. Worth pricing against the alternative of
dropping flashed tracks in favour of generated beds, which need no decoder and
so never touch this path.

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
