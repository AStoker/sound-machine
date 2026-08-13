# SOUNDMACHINE.md

The project story in one file. If you are an agent (or a person) loading this
repo cold, read this first: it explains **what we built, why the pieces are
arranged the way they are, what has already been solved, and what is still
open.** Then use the companions for detail:

- **[`HARDWARE.md`](HARDWARE.md)** — the parts, addresses, pins, power budget.
- **[`CLAUDE.md`](CLAUDE.md)** — how the firmware/repo is structured and the
  rules for editing it safely.
- **[`README.md`](README.md)** — how to build and deploy it.
- **[`FUTURE-DEVELOPMENT.md`](FUTURE-DEVELOPMENT.md)** — everything still to do,
  one numbered entry each.
- **[`RETROSPECTIVE.md`](RETROSPECTIVE.md)** — what building v1 taught.

> ## Where the project is
>
> **Prototype 1 is built.** Designed, printed, wired, assembled, and running on
> the bedside table. The enclosure is done and the electronics are in their final
> arrangement — **the work from here is firmware.**
>
> That changes what "open" means below. The remaining items are tuning, polish,
> unverified assumptions and **one hardware fix** — not construction. They are
> tracked in [`FUTURE-DEVELOPMENT.md`](FUTURE-DEVELOPMENT.md).
>
> The v1 development history is distilled in
> [`RETROSPECTIVE.md`](RETROSPECTIVE.md); the raw journals live on the **v1
> release branch**. The enclosure *design system* (`3d-print/`) stays live on
> `main`, because it is still the source of truth for the LED crescent and the
> starting point for any v2.

---

## 1. What we are building

A DIY, polished, bedside **smart sound machine** — nicknamed the **"Faux
Hatch"** because it takes design cues from the Hatch Restore form factor while
being fully custom and locally controlled. It is one integrated device that
combines:

- **Ambient noise** — continuous white / pink / brown noise, generated on-device,
  plus flashed loop ambiences (crickets) for when a colour of noise isn't the mood.
- **A far-field voice assistant** — "Okay Nabu" wake word into Home Assistant,
  robust enough to be heard *over* playing noise.
- **A sunrise light** — an SK6812 crescent that simulates dawn to wake you, plus
  static nightlight / reading presets.
- **A clock** — a tiled LED matrix that auto-dims to near-black at 3 a.m.
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
                                   ┌─────────── noise_generator (custom C++) ── white/pink/brown
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
watchdog un-ducks when the reply finishes. See `packages/behavior/voice.yaml`.

### The light

`packages/hw/crescent.yaml` owns the SK6812 crescent: an Off/On entity plus a
preset dispatcher (a `select`) with **Sunrise** (a timed, animated dawn),
**Nightlight**, **Morning Light**, **Colour Cycle** and **Rainbow Arch**. The
**Circadian Sunrise** is a keyframe-interpolated effect that fills the crescent
from the bottom row upward, evolving deep-red → amber → blue-enriched cool white
over an adjustable duration, then holding and auto-off. An **Alarm** datetime
fires the sunrise at a set time.

Two of the presets are colour rather than function. **Colour Cycle** drifts the
whole crescent round the hue wheel over three minutes; **Rainbow Arch** paints
concentric hue bands — red on the outside, violet at the centre of the flat edge
— by each pixel's *normalised elliptical radius*, which is what makes it read as
an arch rather than as horizontal stripes. Both bake their own brightness in,
because an addressable light stops applying its brightness to pixels a running
effect owns.

The crescent is **48 px** in six cut segments laid out `{10, 10, 9, 8, 7, 4}`
bottom-to-top on a half-ellipse. That layout is **not a firmware choice** —
`3d-print/enclosure_geom.py` computes it from the physical cavity and
`crescent.yaml` carries a copy. Change one without the other and the firmware
addresses pixels that are not there; `3d-print/check_docs.py` is what stops that.

### The display

The display is **policy plus a driver**: `packages/api/display.yaml` owns the
whole policy layer (the transient overlays and their priority, expiring them,
which default view sits underneath, formatting the clock, the tick) and resolves
all of it into an `clock_display::Frame`. `components/clock_display` renders that frame
and decides nothing. The split is not there so the display can be swapped — it is
there because choosing what to show and drawing it are unrelated problems, and
merging them would bury the policy in the middle of 300 lines of fonts and
register bursts. The frame being a struct is what turns the contract between the
two halves into something the compiler checks rather than something two file
headers have to keep agreeing on.

**The api layer is the single writer**, and it resolves one thing out of two
tiers. First the **overlays**, all transient and all timed, in priority order: a
message typed from Home Assistant → a **device status message** → a transient
code (e.g. "S3", "L1"). If none is live, it falls through to the **default
view** — what the display rests on when nothing has just happened. Normally that
is the clock; while the pack is low it is the sticky **alert** instead.

That tiering is deliberate. An alert used to sit *above* the codes, which meant a
flat battery pinned "LOW" to the display and swallowed every volume readout and
preset code — the machine looked broken rather than low. A sticky condition is
not an event competing for the same instant; it is a statement about what the
display should say when it has nothing better to do, so it displaces the clock
and only the clock. The same slot is where a time-of-day face or any other
resting view would go.

The BH1750 ambient-light sensor auto-dims all of it on a log curve tuned
deliberately dark.

Status messages are the channel for things the *device* wants to say rather than a
code echoing a knob turn — today, "CHG" / "BATT" when the power source changes.
They are drawn in the compact 3x5 font inside the **right-hand panel only**, which
keeps them clear of the physical gap between the two panels; a word centred across
both would lose a column of whichever glyph landed on the seam, and on a 3x5 glyph
that can be fatal (a 'T' reduced to its top bar). The cost is a four-character
budget — anything longer falls back to scrolling the full width, which takes far
longer than anyone wants to watch for a status glance.

### Power & monitoring

`packages/hw/power.yaml` reads the Waveshare 3S UPS via an INA219 and derives
voltage, current, per-cell voltage, an estimated state-of-charge, a "charging"
flag, and a latching "low battery" flag (with hysteresis so it can't chatter).
The display and other logic key off those flags.

"Charging" and "on mains" are **not** the same thing here: a full pack on the
charger tapers to near-zero current, so the mains detector (`external_power`) is
defined as *not discharging* rather than as charging.

Getting *"not discharging"* right took a second pass. The first version compared
the instantaneous current against a deliberately large 200 mA deadband, sized to
ignore the brief excursions a full pack makes on the charger. But this device's
whole idle draw from an 11–12 V pack is only ~100–180 mA — under that deadband —
so unplugging it changed nothing and `external_power` reported **"Plugged In"
while running on battery**. Shrinking the deadband alone just brings the flapping
back. What actually separates the two cases is **duration**: a charger excursion
lasts a sample or two, a real mains loss lasts forever. So the detector now
thresholds a **60 s moving average** of the current (`battery_current_avg`)
against a small 50 mA deadband — a one-sample blip averages down to nothing,
while a sustained draw crosses within two or three samples.

That flag drives the "CHG" / "BATT" announcement, and the averaging window sits
in front of `ups_confirm_time` (30s), so the message can land up to ~90s after
the plug actually moves — the price of never crying "mains lost" at a healthy
full battery.

### The control surface

A **seesaw rotary encoder**: twist = volume (variable step — coarse when quiet,
fine when loud), tap = next sound, hold = sound off. A **capacitive touch pad**:
tap = next light preset, hold = light off. Both drive the same `select` entities
the UI uses, so physical, HA, and web controls stay in sync.

"Next sound" walks **one** list — the noise colours and the flashed tracks are
options in the same `select`, so a tap goes White → Pink → Brown → La La →
Crickets. They were briefly two selects that kept each other switched off by
publishing `Off` into one another; merging them makes the mutual exclusion a
property of the data structure instead of a protocol both sides have to observe.

### The two front ends

1. **Home Assistant** — full control + voice, when the network is up.
2. **Embedded web server** (`web_server:` in `soundmachine.yaml`) — served from
   flash at `http://soundmachine.local/`, works with no internet.

### How the repo is organized

`soundmachine.yaml` is the entry point and holds **only** the device core — the
I2C bus, connectivity, the external components, and the `packages:` manifest.
Everything else is split three ways, and the split is the point: `packages/hw/`
is one file per physical part, `packages/api/` is the abstraction layer that is
the only writer of that hardware, and `packages/behavior/` is the operational
logic that decides what should happen. Every tunable in the build lives in
`packages/settings.yaml`. After ESPHome merges the packages **all ids are
global**, so the wiring is by id — but each layer only reaches *down* through an
api verb (`display_show_code`, `noise_play`, `crescent_static`), never straight
into a device. Custom C++ lives in `components/`.

[`packages/README.md`](packages/README.md) is the architecture map — the layer
rules, the hardware→behavior event contracts, and where to add a new thing. See
`CLAUDE.md` for the editing rules and the invariants.

---

## 3. Roadblocks we have already overcome

These were real problems, diagnosed and solved. Don't re-litigate them without a
reason — and if you change the relevant area, re-test the thing that broke.

**Gapless noise.** A file-loop approach caused audible restarts at the loop
seam. Solved by writing a custom `noise_generator` C++ component that continuously
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
software (AIC3104). The amp is written once at boot by the custom `speaker_amp`
component, with register **write order enforced** (compression before gain, or
the gain gets clamped to a silent amp).

**HA's "Wake word" selects showed up `unavailable`.** Detection worked fine, but
Home Assistant's two wake-word select entities were permanently unavailable. Cause:
`voice_assistant:` never linked the mww instance. `VoiceAssistant::get_configuration()`
answers HA's config request from its `micro_wake_word_` pointer — null means it
advertises zero available wake words and `max_active_wake_words = 0`, and HA's
selects (which it creates **two** of, always, regardless of model count) are
available only when they hold more than the "no wake word" option. Local detection
never needed the link, since `on_wake_word_detected` → `voice_assistant.start:`
never leaves the device. Fix: **`micro_wake_word: mww` under `voice_assistant:`**.
Consequence to remember: HA now **owns** which models are enabled — on connect it
disables every model and re-enables only what the selects name, and that bit is
**persisted in flash**. After a fresh flash, set the select to "Okay Nabu", or the
wake word stays off across reboots.

**Transient brownouts crashed the ESP invisibly — WORKED AROUND, NOT FIXED.**
They don't show on a multimeter but are enough to reset the ESP32. The diagnosis
holds: the proper fix is bulk capacitance at the load — **470–1000 µF low-ESR
electrolytic + 1–10 µF X7R ceramic** at the Flex board's power input terminals,
close to the terminals, plus an input-side cap on the LED supply.

**That capacitance has not been installed.** What is actually in service is a
firmware workaround: the crescent's current ceiling (`led_max_pct`) is held at
**25%**, which keeps the transient small enough not to trigger it. This is why
the light is dimmer than the hardware can drive. Two things make it more than a
cosmetic compromise:

- **The paper budget was never the constraint.** At 65% the strip draws ~1.9 A
  and the whole machine ~3.7 A of a 5 A rail — comfortable — and it browned out
  anyway. The failure is transient, not average.
- **It cannot self-recover.** The SK6812s latch their last frame independently of
  the MCU, so once the rail sags enough to reset the ESP32 the strip keeps
  drawing the same current through the entire reboot loop.

See §4 for the TODO. Until it is done, `led_max_pct` is load-bearing — treat it
as a safety limit, not a preference.

**I2C bus was starving the XVF3800.** The STEMMA sensor chain added enough cable
capacitance / pull-up load to break the timing-sensitive XVF3800. Fix: run the
shared bus at **100 kHz with a 1 ms timeout** (room to clock-stretch during its
firmware boot). Drop toward 10 kHz if it's still flaky fully assembled.

**Broken idle reporting on the media pipeline.** The mixer suppresses the media
pipeline's PLAYING → STOPPED transition, so looping/un-ducking can't rely on the
player's idle state. Un-ducking is solved by a **`duck_watchdog`** keyed off
`is_announcing` (not idle).

Looping was *thought* to be solved by **`media_player.repeat_one`**, on the
belief that it keys off the decoder's own EOF. **It does not** — it is
implemented in `SpeakerMediaPlayer::loop()` and restarts the file on exactly the
transition the mixer suppresses, so it was built on the thing that had already
been ruled out. Symptom: a track plays once, the media player entity sits at
"playing" forever, and every later track is silent until reboot — while noise,
on its own mixer source, is unaffected.

The cause is frame accounting. A mixer source only leaves `STATE_RUNNING` once
`pending_playback_frames_` hits zero; that counter is drained by the i2s output
callback, which fires only for buffers holding real audio, and a source that
starts contributing while the pipeline already holds frames is handicapped by
that backlog first. When a track ends with nothing else making sound, the
callbacks stop before the handicap is paid, the counter freezes, and the source
is stuck in `STATE_STOPPING`. Noise escapes it by first contributing at boot,
when the pipeline is empty.

The first fix was to make **every track wait for
`mixing_speaker->get_frames_in_pipeline()` to reach zero before starting**, which
buys it the same zero handicap noise gets. It half-worked, and could not do
better: `repeat_one` calls `start_file()` straight from
`SpeakerMediaPlayer::loop()`, so the wait protected the *first* start and no
later one. On hardware that meant a gap at every loop and a dead channel after a
pass or two.

**The actual fix was to stop using the media player for this at all.** Every
flashed sound is now a **ambience**: `components/ambience_player` decodes it straight into
its own mixer source, which starts once and never stops, and looping is a read
pointer returning to zero — no end-of-file, no pipeline, nothing to restart. That
deleted the drain-wait, the per-file verbs, the repeat flag and the arbitration
global along with the bug. The media player keeps what it is good at: the TTS
reply and whatever Home Assistant streams, neither of which loops.

This is upstream behaviour, not a local bug — [esphome/esphome#14641](https://github.com/esphome/esphome/issues/14641)
is closed as not planned — so **anything put back on the media player and looped
will fail the same way**. FUTURE-DEVELOPMENT T3–T5 records the whole thing.

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

**Every open item lives in [`FUTURE-DEVELOPMENT.md`](FUTURE-DEVELOPMENT.md)**,
one numbered entry each, so it can be referenced from code and commits. Summary:

| | |
|---|---|
| **H1** | Install the brownout-fix bulk capacitance — **the highest-value item.** It is currently costing three quarters of the crescent's brightness, because `led_max_pct: 25%` is standing in for it. |
| **H2 / H3** | Verify the UPS shunt value; settle which touch electrode is actually installed and re-calibrate if needed. |
| **C1–C4** | Calibrate the ToF thresholds and the gesture dead band; tune the brown-noise makeup gain and the auto-dim curve. |
| **V1–V3** | Validate wake-word-over-noise in the enclosure; re-check the sunrise against the final crescent; measure the remaining `(?)` geometry constants. |
| **F1** | Touchless wake — designed, never built. |
| **T1 / T2** | Tech debt: blanket `except ImportError` in the generators; the optional foot-span stability lever. |

### Settled since assembly

**UPS monitoring is live and reading correctly.** The boot I2C scan finds the
monitor at **`0x41`** and the INA219 platform talks to it — pack 12.46 V,
4.153 V/cell across 3S, 98 % SOC, all mutually consistent. The **sign convention
is confirmed**: discharging reads negative, and `External Power` / `Battery
Charging` agree with the actual plug state. The shunt value is still assumed —
that is H2.

**The capacitive touch pad works and is calibrated.** `touch_threshold` is
**2500**, from 64 untouched samples and 5 presses on the assembled machine:
untouched noise sd 34 with a worst excursion of +50, presses 6363–12731. Getting
there also turned up an ESPHome bug worth knowing — `measurement_duration` must
be set explicitly or the S3's touch counter saturates and no threshold can ever
fire. Both are documented in `packages/settings.yaml` §7 and
`packages/hw/touch.yaml`.

**The enclosure is built.** The bottom-plate geometry that was historically
blocked on the battery-retention decision was resolved by the Waveshare 3S UPS,
printed, and assembled.

---

## 5. History

**[`RETROSPECTIVE.md`](RETROSPECTIVE.md)** — what building v1 taught, distilled.
Mostly *not* about enclosures: the ways a check can pass for the wrong reason,
why interference lives in the gap between parts, the physical facts worth not
rediscovering, and a table of what changed from the original design and why.

Read it before re-opening a settled decision. If an old idea resurfaces — 144
LED/m, a boost converter, a 258 mm body, an SHT40, a PWA — each was killed there
for a reason, and §4 of the retrospective records it.

The raw session-by-session build journal is **not on `main`**. It is preserved on
the **v1 release branch**; `main` carries only the conclusions.

**Still live, not history:** `3d-print/` — the enclosure geometry, its generators
and its checks. `enclosure_geom.py` remains the source of truth for the LED
crescent, and `3d-print/check_docs.py` still enforces that this document,
`HARDWARE.md`, `CLAUDE.md` and the firmware all agree with it.
