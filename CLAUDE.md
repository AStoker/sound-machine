# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

ESPHome firmware for a bedside smart sound machine built on a ReSpeaker Flex
(XVF3800 + XIAO ESP32-S3): white/pink/brown noise, a voice assistant, an
IS31FL3731 LED-matrix clock, an SK6812 sunrise crescent, and Waveshare UPS
battery monitoring.

The config is designed to be **hosted on GitHub and pulled by Home Assistant as
a remote ESPHome package** — this constraint shapes several non-obvious design
choices (see "Remote-hosting constraints" below). Repo slug: `astoker/sound-machine`.

> **Prototype 1 is built and assembled — this is a firmware repo now.** The
> enclosure is printed, the electronics are in their final arrangement, and the
> machine is in service. Expect changes here to be behavior, tuning and polish.
> `3d-print/` is still live and still authoritative for the crescent geometry (see
> the coupling note below), but it is no longer where the work is. Open work is
> tracked in [`FUTURE-DEVELOPMENT.md`](FUTURE-DEVELOPMENT.md); the v1 development
> history is distilled in [`RETROSPECTIVE.md`](RETROSPECTIVE.md), with the raw
> journals preserved on the **v1 release branch** rather than on `main`.

## Companion docs

- **[`HARDWARE.md`](HARDWARE.md)** — every physical part, the I2C address map,
  pin map, power budget, and wiring cautions. Start here for "what is this pin /
  chip / address."
- **[`SOUNDMACHINE.md`](SOUNDMACHINE.md)** — the project narrative: goals, how
  the pieces fit, roadblocks already overcome, and open work. Start here to
  understand *why* the project is the way it is before changing behavior.
- **[`3d-print/README.md`](3d-print/README.md)** — the enclosure: generated
  drawing sheets and printable solids, the constraints they turned up, and how
  each part is validated. Start here for anything about the physical shell.
- **[`FUTURE-DEVELOPMENT.md`](FUTURE-DEVELOPMENT.md)** — every open item, one
  numbered entry each (`H1`, `C2`, …), referenceable from code and commits.
  Check here before starting work, and add an entry rather than a stray TODO.
- **[`RETROSPECTIVE.md`](RETROSPECTIVE.md)** — what building v1 taught: mostly how
  checks fail, plus a table of what changed from the original design and why.
  Read it before re-opening a settled decision; it is history, not current state.

> **The enclosure geometry and the firmware are coupled, and the coupling is
> one-way.** `3d-print/enclosure_geom.py` is the source of truth for the LED
> crescent — pixel count, row layout, row pitch. `packages/hw/crescent.yaml` carries
> a *copy* of that output (`num_leds` and `leds_per_row[]`). **If you change the
> crescent, re-run `gen_drawing.py` and re-sync those two values**, or the
> firmware will address pixels that are not there. Currently **48 px**,
> `{10, 10, 9, 8, 7, 4}`.
>
> `3d-print/check_docs.py` enforces this — run it after any geometry change.

## Commands

```sh
# Validate the full merged config (packages + git external_components + media):
./scripts/esphome config soundmachine.yaml

# Build + upload:
./scripts/esphome run soundmachine.yaml
```

- **On macOS, always go through `./scripts/esphome`, not bare `esphome`.** macOS
  26/27 has a bug in Network.framework's `pthread_atfork` child handler that
  segfaults forked children before `exec`, so ESPHome steps fail intermittently
  with `returncode=-11` — most often the ESP-IDF Python-env check ("Can't create
  Python virtual environment for ESP-IDF"), but any of the ~20 subprocesses a
  build spawns can hit it. The wrapper loads
  `scripts/macos-forkfix/sitecustomize.py`, which routes `subprocess` through
  `posix_spawn` (no atfork handlers, so the crash can't happen); that file
  documents the mechanism and how to verify whether the OS bug is still present.
  A bare `esphome` invocation is not wrong, just unprotected — if one fails with
  `-11`, it's this bug, not the config.
- `esphome config` needs **no** local `secrets.yaml` — credentials are
  substitutions with valid placeholder defaults (see below). It *does* need
  network + the GitHub repo to exist, because it clones the custom components
  and downloads the flashed media at validate time.
- `.esphome/` is the build cache (gitignored). It can end up with read-only
  files; if `rm -rf .esphome` fails, run `chmod -R u+w .esphome && rm -rf .esphome`.

## Architecture

**Read [`packages/README.md`](packages/README.md) first** — it is the
authoritative map of the layer scheme, the two rules, the event-script contracts,
and a "where do I add a thing" table. The summary below is orientation only.

**Three layers, plus a core and a settings file:**

| Path | Holds |
| --- | --- |
| `soundmachine.yaml` | device core only: platform, wifi/api/ota, the `i2c` bus, `external_components`, and the `packages:` manifest. No tunables, no feature logic, no `on_boot`. |
| `packages/settings.yaml` | **every tunable in the build**, grouped into 12 documented sections. The single place to change a value. |
| `packages/hw/*.yaml` | one file per physical part. Component config, register-level talk, and *hardware interpretation* (lux → level, metres → "hand near", volts → SOC). No policy. |
| `packages/api/*.yaml` | one file per subsystem. The abstraction layer, and the **only writer** of the hardware behind it. Everything else calls its verbs. |
| `packages/behavior/*.yaml` | operational logic: presets, gestures, announcements, boot restores, and the Home Assistant control surface. Decides; never touches hardware. |

Every file starts with a header listing what it **DEFINES**, what it
**CONSUMES**, and what it **REQUIRES**. Read those before editing: after ESPHome
merges all packages **all ids are global**, so cross-package references work but
each id must be defined exactly once. Top-level list keys (`sensor:`, `script:`,
`globals:`, `interval:`, `esphome.on_boot:` …) concatenate across packages.

**The two rules** (details in `packages/README.md`):

1. **Writes go through the api; reads do not.** A behavior package calls
   `noise_play(1)` rather than `id(noise).start()`, but reads
   `external_media_player->volume` or `id(battery_low).state` freely — ESPHome
   scripts can't return values, so routing reads through them buys nothing.
2. **Hardware raises events; behavior implements them.** `hw/knob.yaml` calls
   `on_knob_turn(clicks)`; `behavior/sound.yaml` defines it. Same for
   `on_touch_tap`/`on_touch_hold`, `on_hand_near_changed`,
   `on_external_power_changed`/`on_battery_low_changed`, `on_audio_ready`. Script
   ids resolve at validate time, so an unmet contract is a build error, by design.
   Raise **one event per fact**, not one per subsystem — a shared event forces the
   handler to work out what changed.

**The display is two files, split by concern rather than for pluggability.**
`api/display.yaml` decides *what* to show — the transient overlays and their
priority, expiring them, which default view rests underneath, formatting the
clock, and the single tick — and resolves them into a *frame*
(`display_frame_*` globals). `hw/matrix.yaml`
provides one script, `display_paint`, which renders that frame and makes no
decisions. There is one display and no plan for another; the split stands because
policy over strings and 300 lines of fonts/panel geometry/register bursts are
unrelated problems.

**Custom C++ components** in `components/` (`noise_source`, `loop_source`,
`seesaw`, `tpa2016`) follow standard ESPHome layout (`__init__.py` codegen +
`.h`/`.cpp`). `seesaw` is vendored locally (patched `dump_summary()` for ESPHome
2026.7.x); the upstream ssieb git source is left commented in
`external_components`.

> **EVERY FLASHED SOUND IS AN AMBIENCE, AND THE MEDIA PLAYER HAS NO `files:` LIST.**
> Anything meant to play until something turns it off — the noise colours, the
> crickets, La La — owns a mixer source outright via `noise_source` /
> `loop_source`: started once, never stopped, no decoder pipeline, so there is
> nothing to restart and no end-of-file. `external_media_player` carries only the
> TTS reply and Home Assistant's audio, neither of which loops. Looping through
> it means `repeat_one`, which restarts the whole pipeline every pass — that gaps
> audibly and, after a pass or two, wedges the media channel for good
> (FUTURE-DEVELOPMENT T3–T5, resolved by removal, not by a fix). **Do not put a
> flashed file back on the media player.** The two mechanisms are laid out at the
> top of `packages/hw/audio_chain.yaml`.
>
> **Adding audio? The format is a hard requirement: MP3, mono, 48 kHz, peak
> ≤ −2.4 dBFS, Xing header intact.** There is no resampler in the ambience path, so a
> mismatched file is refused at its first frame rather than played at the wrong
> speed. Full rules and the ffmpeg recipe are under "ADDING AUDIO" in
> `packages/settings.yaml` §11.

**Sensors & controls live across packages, on one shared I2C bus.** Implemented
today: BH1750 ambient light (display auto-dim), seesaw rotary encoder (volume +
tap/hold sound control, plus its built-in NeoPixel), DS3231 RTC (time source),
VL53L0X ToF (knob proximity), plus an ESP32 native capacitive touch pad
(light-preset cycle). See `HARDWARE.md` for the full map.

> **Gotcha:** the **VL53L0X** (`0x29`) is now live, but only in
> `packages/hw/proximity.yaml` and only to pre-light the knob NeoPixel. The
> **touchless-wake** gesture the hardware notes describe is still *not*
> implemented — don't assume any behavior beyond the knob pixel reads it.

**The knob NeoPixel is driven from a lambda, not the seesaw `light:` platform,
on purpose.** `packages/api/indicator.yaml` calls the component's
`color_neopixel()` directly from a 20 Hz interval that writes only on a change.
Going through the `light:` platform would instead write the pixel over I2C once
per *main-loop iteration* for the whole of every transition — hundreds of
writes/second onto the bus this build already had to slow to 100 kHz to stop
starving the XVF3800. If you switch it to the stock platform, that regression is
what you are buying.

Cross-file invariants worth knowing before changing behavior:
- **Display is single-owner, in two stages.** `api/display.yaml` is the only
  caller of `display_paint`, and `packages/hw/matrix.yaml` is the only code that
  touches the display's I2C address. Content is two tables in the api layer, so
  adding to either is a row plus a setter, not a new branch:
  **overlays** (transient, always timed) **message → status → code**, resolved
  over a **default view** — what the display rests on with no overlay up —
  **alert → clock**. A sticky condition like a flat battery is a *default view*:
  it replaces the clock and nothing else, so codes and announcements still show
  over it. Nothing else writes the display; callers use a channel:
  - `display_show_code(text)` — short codes ("L1", "S3", "OFF", a volume
    percentage) from a user action.
  - `display_show_status(text, seconds)` — timed device announcements (today:
    `behavior/power.yaml` announcing "CHG"/"BATT" when External Power flips).
  - `display_set_alert(text)` — a *sticky* condition shown **in place of the
    clock**, not over the top of everything; pass `""` to clear (today: the
    low-battery warning).
  - `display_show_message(text, seconds)` — Home-Assistant-authored text.
- **The driver must self-throttle.** The api ticks at `display_tick_ms` (250 ms)
  and calls `display_paint` every time; the driver hashes what it is about to draw
  and returns before touching I2C when nothing changed. ~300 bytes on this 100 kHz
  bus is ~30 ms of bus time.
- **4 characters is the budget for the COMPACT channels** (status and alert). A
  compact string that fits sits still inside one panel, where it cannot straddle
  the inter-panel gap — a stationary glyph on the seam permanently loses a column.
  Anything longer scrolls the **full width**, like any other overflowing text: the
  seam stops mattering once the text is moving. So exceeding the budget is not
  broken, just slow — a scrolling pass takes far longer than the few seconds a
  status is meant to occupy. Full rationale in `packages/hw/matrix.yaml` under
  "WHY COMPACT SCOPE EXISTS"; that file is the one place it is spelled out.
- **The matrix has a physical inter-panel gap.** Two tiled panels aren't
  seamless — there's a ~1px dead column between them (`matrix_panel_gap`). The
  matrix lays content out in *physical* columns that include the gap and maps
  back to logical columns at draw time, so the clock stays centred across the
  seam. Don't assume the two 16-wide panels are one contiguous 32-wide surface.
- **The TPA2016 amp runs with its AGC OFF (compression 1:1) deliberately.** The
  XVF3800's acoustic echo canceller can only cancel a *linear* echo path, and an
  active compressor downstream of the DAC makes it time-varying. Do not enable
  compression/AGC without re-testing wake-word-over-noise. Register write order
  (compression before gain) is handled inside the component and matters.

## Remote-hosting constraints (do not regress these)

These exist because the config is pulled onto Home Assistant as a remote package:

1. **No `!secret` in the config.** Remote packages forbid `!secret` lookups.
   Credentials (`wifi_ssid`, `wifi_password`, `ap_password`, `ota_password`,
   `api_key`) are `substitutions:` with placeholder defaults; the local HA
   device YAML (`soundmachine.min.yaml`) overrides them with `!secret` values
   from HA's own `secrets.yaml`. Local substitutions win over package ones. Keep
   new credentials as substitutions, never `!secret`, in this repo.
2. **Custom components via git source.** `external_components` uses
   `github://astoker/sound-machine@main` (a `type: local, path: components`
   source would resolve against the *build machine's* config dir, which HA
   doesn't have). Tradeoff: editing a component requires push-then-build; for a
   fast local loop, temporarily switch that one source back to `type: local`.
3. **Flashed media via a `*_source` substitution defaulting to a URL.** ESPHome
   resolves a local `file:` path against the build machine's config dir, so on
   HA a bare `sounds/...` path is not found even though the file is in the repo.
   `la_la_sad_source` defaults to a raw GitHub URL (downloaded at build time);
   override it with `sounds/La-la-sad.mp3` for local/offline dev. Any new
   flashed audio must follow this pattern.

## Home Assistant side

`soundmachine.min.yaml` is the reference for the tiny device YAML that lives in
HA's ESPHome folder: it injects secrets as substitutions and pulls
`soundmachine.yaml` from this repo with `refresh: 0s` (always latest `main`).
`secrets.example.yaml` lists the five required keys.

## Hardware calibration state

On an assembled machine, most of this is settled. What is *not* settled is worth
knowing before you trust a number.

**Confirmed on hardware:**
- **UPS monitor** — `ups_i2c_address` **`0x41`**, INA219 (not INA226), confirmed
  against the boot I2C scan and reading consistently (12.46 V pack / 4.153 V per
  cell across 3S / 98 % SOC). Sign convention confirmed: discharge is negative.
- **Touch pad** — `touch_threshold` **2500**, derived from measured noise and
  press deltas; see the working in `packages/settings.yaml` §7.

> **`led_max_pct: 25%` IS A SAFETY LIMIT, NOT A BRIGHTNESS PREFERENCE. Do not
> raise it.** The brownout-fix bulk capacitance has **not** been installed; this
> cap is the workaround standing in for it. 65% was tried and still reset the
> ESP32, at ~3.7 A of a 5 A rail — the average draw was never the constraint, the
> transient is. And the failure does not self-clear: the SK6812s latch their last
> frame independently of the MCU, so a rail sag that resets the ESP32 leaves the
> strip drawing the same current through the whole reboot loop. If the crescent
> looks dim and you are tempted to fix it in firmware, that is this. See the
> hardware TODO in `SOUNDMACHINE.md` §4.

**Still assumed, so do not build on it:**
- **`ups_shunt_ohms` (`0.01 Ω`)** is inherited from the module's documentation,
  not measured. Bus voltage and SOC do not depend on it; **absolute current and
  power do.** The idle reading (~0.15 A) is plausible but that is not verification.
- **The ToF measures its own pinhole, not the room** — a fixed ~0.024 m of
  optical crosstalk through the 3.5 mm shared bore. So `hw/proximity.yaml`
  detects *deviation from a learned baseline* rather than distance, and there are
  no `tof_near_m` / `tof_far_m` settings. The deviation thresholds ARE measured
  (see FUTURE-DEVELOPMENT C1); the enclosure fix that would make plain distance
  work again is H4. Don't add a distance threshold back before that lands.
- **Touch, again** — 2500 is calibrated against a bench pad behind the unthinned
  2.5 mm wall, not the designed 40 × 22 mm pads behind 1.6 mm. Re-calibrate when
  those go in.

> **The ESP32-S3 touch peripheral needs `measurement_duration` set explicitly.**
> ESPHome's default derives `charge_times = 65535` (the hardware maximum, against
> a driver default of 500), which saturates the 22-bit counter: every reading pins
> at 4194303, the benchmark follows it, and the delta is permanently 0 so the pad
> can never fire. `packages/hw/touch.yaml` sets it. A pad reading exactly 4194303
> is this bug, not a wiring fault.
