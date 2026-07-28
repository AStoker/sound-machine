# SOUNDMACHINE.md

The project story in one file. If you are an agent (or a person) loading this
repo cold, read this first: it explains **what we are building, why the pieces
are arranged the way they are, what has already been solved, and what is still
open.** Then use the companions for detail:

- **[`HARDWARE.md`](HARDWARE.md)** — the parts, addresses, pins, power budget.
- **[`CLAUDE.md`](CLAUDE.md)** — how the firmware/repo is structured and the
  rules for editing it safely.
- **[`README.md`](README.md)** — how to build and deploy it.

---

## 1. What we are building

A DIY, polished, bedside **smart sound machine** — nicknamed the **"Faux
Hatch"** because it takes design cues from the Hatch Restore form factor while
being fully custom and locally controlled. It is one integrated device that
combines:

- **Ambient noise** — continuous white / pink / brown noise, generated on-device.
- **A far-field voice assistant** — "Okay Nabu" wake word into Home Assistant,
  robust enough to be heard *over* playing noise.
- **A sunrise light** — an SK6812 crescent that simulates dawn to wake you, plus
  static nightlight / reading presets.
- **A clock** — a 7-segment display that auto-dims to near-black at 3 a.m.
- **Environmental sensing** — ambient light (live), with a time-of-flight
  touchless wake planned.
- **A physical control surface** — a rotary encoder (volume + sound) and a
  capacitive touch pad (light presets).

The whole thing runs on **ESPHome**, integrates with a **local Home Assistant**
instance (Nabu Casa subscription for voice), and is designed so the config is
**hosted on GitHub and pulled by HA as a remote package** — every build compiles
the latest `main`.

**Design values driving the project:** offline-capable (noise, clock, one
flashed track, and a web UI all work with no network), quiet and eye-friendly at
night, acoustically clean enough not to fight the echo canceller, and physically
polished (Fusion 360 enclosure, Glowforge-cut acrylic diffuser).

---

## 2. How the pieces fit together

### The audio chain (the hard part)

```
                                   ┌─────────── noise_source (custom C++) ── white/pink/brown
ESP32-S3 ──I2S──► XVF3800 mics     │
   │              (beamform+AEC)   ├──► mixer ──► AIC3104 DAC ──► TPA2016 amp ──► 2× 4Ω speakers
   │                               │      ▲
   ├──► micro_wake_word "Okay Nabu"│      ├── media pipeline (flashed MP3 / HA URL)
   └──► voice_assistant ───────────┘      └── announcement pipeline (TTS replies)
```

Everything is 48 kHz end to end. Three audio sources (noise, media, TTS
announcements) are summed by an ESPHome **mixer**; the mixer output goes to the
DAC, then the amp. The **XVF3800 provides the mic beamforming and the acoustic
echo cancellation (AEC)** that lets the wake word be heard while the machine is
playing sound — and that single fact constrains everything downstream (see §4).

When the wake word fires, both background channels (noise + media) **duck** for
the turn; the spoken reply rides the announcement channel at full volume; a
watchdog un-ducks when the reply finishes. See `packages/audio.yaml`.

### The light

`packages/lighting.yaml` owns the SK6812 crescent: an Off/On entity plus a
preset dispatcher (a `select`) with **Sunrise** (a timed, animated dawn),
**Nightlight**, and **Morning Light**. The **Circadian Sunrise** is a
keyframe-interpolated effect that fills the crescent from the bottom row upward,
evolving deep-red → amber → blue-enriched cool white over an adjustable duration,
then holding and auto-off. An **Alarm** datetime fires the sunrise at a set time.

### The display

`packages/display.yaml` owns the HT16K33 7-seg. **`render_display` is the single
writer**, rendering one of three things in priority order: a low-battery "LO"
warning → a transient preset code (e.g. "S3", "L1") → the clock. The BH1750
ambient-light sensor auto-dims it on a log curve tuned deliberately dark.

### Power & monitoring

`packages/battery.yaml` reads the Waveshare 3S UPS via an INA219 and derives
voltage, current, per-cell voltage, an estimated state-of-charge, a "charging"
flag, and a latching "low battery" flag (with hysteresis so it can't chatter).
The display and other logic key off those flags.

### The control surface

A **seesaw rotary encoder**: twist = volume (variable step — coarse when quiet,
fine when loud), tap = next sound, hold = sound off. A **capacitive touch pad**:
tap = next light preset, hold = light off. Both drive the same `select` entities
the UI uses, so physical, HA, and web controls stay in sync.

### The two front ends

1. **Home Assistant** — full control + voice, when the network is up.
2. **Embedded web server** (`web_server:` in `soundmachine.yaml`) — served from
   flash at `http://soundmachine.local/`, works with no internet.

### How the repo is organized

`soundmachine.yaml` is the entry point and holds **only** the device core — the
`substitutions:` block (the single source of truth for every tunable), the I2C
bus, connectivity, boot, and the `packages:` includes. Each **feature package**
(`audio`, `lighting`, `display`, `battery`) is a self-contained slice; after
ESPHome merges them, **all ids are global**, so cross-package wiring works by id
(e.g. the Sound select sets the display's `preset_code`). Custom C++ lives in
`components/`. See `CLAUDE.md` for the editing rules.

---

## 3. Roadblocks we have already overcome

These were real problems, diagnosed and solved. Don't re-litigate them without a
reason — and if you change the relevant area, re-test the thing that broke.

**Gapless noise.** A file-loop approach caused audible restarts at the loop
seam. Solved by writing a custom `noise_source` C++ component that continuously
injects PCM — white, pink (Paul Kellet filter), and brown (leaky integrator with
`std::tanh()` soft saturation). Color switches mid-stream with no restart.

**Starting noise crashed the ESP at boot.** Starting the generator during setup
dereferenced an uninitialized event group. Fixed by deferring the resume to
`on_boot` **priority -100 + a 2 s delay** (a `booted` global gates the Sound
select from touching the audio engine before then).

**Wake word over playing noise (the central audio constraint).** The XVF3800's
AEC can only cancel a **linear** echo path. So the **TPA2016 amp's AGC is turned
OFF** (compression 1:1) rather than tuned — an active compressor downstream of
the DAC makes the echo path time-varying and un-cancellable. All volume lives in
software (AIC3104). The amp is written once at boot by the custom `tpa2016`
component, with register **write order enforced** (compression before gain, or
the gain gets clamped to a silent amp).

**Transient brownouts crashed the ESP invisibly.** They don't show on a
multimeter but are enough to reset the ESP32. Fix: bulk capacitance at the load
— **470–1000 µF low-ESR electrolytic + 1–10 µF X7R ceramic** at the Flex board's
power input terminals, close to the terminals (and an input-side cap on the LED
supply). *Verify this is present in the as-built.*

**I2C bus was starving the XVF3800.** The STEMMA sensor chain added enough cable
capacitance / pull-up load to break the timing-sensitive XVF3800. Fix: run the
shared bus at **100 kHz with a 1 ms timeout** (room to clock-stretch during its
firmware boot). Drop toward 10 kHz if it's still flaky fully assembled.

**Broken idle reporting on the media pipeline.** The mixer + `timeout: never`
permanently suppresses idle-state reporting, so looping/un-ducking can't rely on
it. Solutions: **`media_player.repeat_one`** (keys off the decoder's own EOF) for
looping, and a **`duck_watchdog`** keyed off `is_announcing` (not idle) for
un-ducking after a voice turn.

**ESPHome 2026.7.x churn.** `select` lost `.state` (use `current_option()` wrapped
in `std::string()`); persisted selections are tracked in `restore_value` globals
instead. `on_tts_stream_end` is unavailable in `media_player:` mode. The seesaw
component was vendored locally with a patched `dump_summary()` (upstream PR #100
on the ssieb repo).

**SD card ruled out.** ESPHome's speaker/mixer pipeline has no SD media source,
so on-device audio is either flashed into the ESP or streamed from HA; runtime
track swapping goes through the HA media library.

**Remote-package hosting.** Because HA pulls this repo as a remote ESPHome
package, `!secret` is forbidden in the config (credentials are substitutions the
local device YAML overrides), custom components must load via a **git**
`external_components` source, and flashed media must default to a **URL** rather
than a bare repo path. See `CLAUDE.md` → "Remote-hosting constraints."

---

## 4. What is still open

**Bench-verify the UPS monitoring.** `ups_i2c_address` (`0x41`) and
`ups_shunt_ohms` (`0.01 Ω`) are **placeholders** — confirm against the boot I2C
scan, and confirm the part is an INA219 (vs INA226, which needs a platform
swap). Also verify the **current sign convention** on the bench.

**Implement the ToF sensor.** The **VL53L0X** (touchless wake) is part of the
build and is in the hardware/address map, and a leftover `logger:` line
references it, but it **has no ESPHome entity yet.** The wake gesture (output in
inches, ×39.3701 multiply) was designed historically but is not in the current
firmware.

**AEC / channel-assignment bench test.** Wake-word-over-playing-noise still needs
a proper bench validation with the final channel assignment.

**Confirm as-built power wiring.** The HT16K33 should be powered from a dedicated
**3.3V LDO off the 5V rail** (not the XIAO 3V3 pin) to avoid loading the shared
bus; and the brownout-fix bulk capacitance should be confirmed installed.

**Enclosure geometry.** The five-part frame is designed, but the **bottom plate
geometry** was historically blocked on the battery-retention decision — now that
the Waveshare 3S UPS is chosen, that geometry can be finalized.

**Calibration.** The capacitive touch threshold (`touch_threshold`) needs
`esp32_touch: setup_mode: true` calibration; the brown-noise high-pass makeup
gain is tuned by ear.

---

## 5. Memory reconciliation (history vs. current code)

The project has evolved; a few things in older conversation memory no longer
match the code in this repo. Current code wins. The notable drifts:

| Topic | Historical note | Current repo (authoritative) |
|-------|-----------------|------------------------------|
| **Power** | Battery retention was an *open decision* (LiPo + USB-C candidate; Qi2 already dropped) | **Resolved: Waveshare UPS Module 3S** (3× 18650), 5V/5A rail, INA219 monitoring |
| **LED strip** | SK6812 **144 LED/m**, powered via an **XL6009 boost converter** | SK6812 **60 LED/m, 48 px in 6 cut segments**, powered directly from the **UPS 5V rail** (no boost converter) |
| **Crescent shape** | A half **circle** — diffuser R117 with the LED field on a smaller R96 and a 21 mm unlit fade band between them | A flattened half-**ellipse**, **89 × 62.7** (`CROWN_K = 0.74`). **The LED field IS the diffuser** — no fade band. Row counts are limited by the physical **ribbon** (n × 16.5 mm), not the LED bodies, which is what sets the row counts; the rows BUTT so the whole 48-px reel fits |
| **Enclosure size** | **258 × 64 × 190**, front module split in two for the bed | **202 × 64 × 155.7**, both printed parts fit a 220 bed **whole**. Speakers rotated 90° (nubs top/bottom), mic array moved above them, crown flattened |
| **Printed parts** | dome, front module, bottom plate, knob | …plus an **LED carrier** (part 6) and a generated **notched acrylic diffuser** (part 7) — a plate holding the six strip segments at the 12 mm standoff, screwed to pads inside the diffusion cavity wall |
| **MCU** | XIAO ESP32-S3 **Plus** | Either works; **standard XIAO ESP32-S3 is a confirmed drop-in** (`board: esp32-s3-devkitc-1`, 8MB flash) |
| **ToF sensor** | VL53L0X treated as part of the sensor stack | **Kept**, but **not yet implemented** in firmware — on the bus map only |
| **SHT40 temp/hum** | Part of the planned sensor stack | **Removed** from the design entirely |
| **Front ends** | HA + embedded web server (a standalone PWA was tried) | **HA + embedded web server**; the standalone PWA was **removed** |

**Working principles that still hold** (carry these forward): search project
history before reasoning from memory on this hardware — pin maps and part choices
have changed a lot; the **tested D4/D5 audio-I2C mapping is the source of
truth**, not schematic-derived guesses; **bench-first** before soldering; and
Andy prefers **complete updated files** after a change (not diffs), and uses
`git diff` against known-good commits to catch regressions.
