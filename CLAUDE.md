# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

ESPHome firmware for a bedside smart sound machine built on a ReSpeaker Flex
(XVF3800 + XIAO ESP32-S3): white/pink/brown noise, a voice assistant, a HT16K33
7-seg clock, an SK6812 sunrise crescent, and Waveshare UPS battery monitoring.

The config is designed to be **hosted on GitHub and pulled by Home Assistant as
a remote ESPHome package** — this constraint shapes several non-obvious design
choices (see "Remote-hosting constraints" below). Repo slug: `astoker/sound-machine`.

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
| `packages/settings.yaml` | **every tunable in the build**, grouped into 13 documented sections. The single place to change a value. |
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
   `on_power_state_changed`, `on_audio_ready`. Script ids resolve at validate
   time, so an unmet contract is a build error, by design.

**The display is pluggable.** `api/display.yaml` owns the whole display-agnostic
layer — four content channels and their priority, expiring the timed ones,
formatting the clock, and the single tick — and resolves them into a *frame*
(`display_frame_*` globals). The active driver provides one script,
`display_paint`, which renders that frame and makes no decisions. Load exactly
one driver (`hw/matrix.yaml` **or** `hw/seg7.yaml`); both define `display_paint`,
so loading both collides. Swap the `hw_display:` line in the manifest.

**Custom C++ components** in `components/` (`noise_source`, `seesaw`, `tpa2016`)
follow standard ESPHome layout (`__init__.py` codegen + `.h`/`.cpp`). `seesaw`
is vendored locally (patched `dump_summary()` for ESPHome 2026.7.x); the upstream
ssieb git source is left commented in `external_components`.

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
  caller of `display_paint`, and the loaded driver
  (`packages/hw/matrix.yaml` today, or `packages/hw/seg7.yaml` for the 7-seg) is
  the only code that touches the display's I2C address. Priority lives in the api
  layer, once, rather than being re-implemented per driver: **message → status →
  alert → code → clock**. Nothing else writes the display; callers use a channel:
  - `display_show_code(text)` — short codes ("L1", "S3", "OFF", a volume
    percentage) from a user action.
  - `display_show_status(text, seconds)` — timed device announcements (today:
    `behavior/power.yaml` announcing "CHG"/"BATT" when External Power flips).
  - `display_set_alert(text)` — a *sticky* condition; pass `""` to clear (today:
    the low-battery warning).
  - `display_show_message(text, seconds)` — Home-Assistant-authored text.
- **Drivers must self-throttle.** The api ticks at `display_tick_ms` (250 ms) and
  calls `display_paint` every time; each driver hashes or compares what it is
  about to draw and returns before touching I2C when nothing changed. ~300 bytes
  on this 100 kHz bus is ~30 ms of bus time.
- **4 characters is the budget for the COMPACT channels** (status and alert). The
  matrix draws them inside a SINGLE panel (the right-hand one) in the compact 3x5
  font, so they can never straddle the inter-panel gap — which is why no
  seam-alignment logic is needed. 4 chars = 15px inside 16 columns. Longer strings
  still work but fall back to scrolling the full width, and a pass takes far
  longer than the few seconds a status is meant to occupy. The 7-seg alternative
  has 4 digits, so the same budget happens to apply there.
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

## Hardware placeholders

The UPS monitor I2C address (`ups_i2c_address`) and shunt (`ups_shunt_ohms`) in
`packages/settings.yaml` are UNCONFIRMED placeholders — confirm against the boot
I2C scan. INA219 vs INA226 may need swapping in `packages/hw/power.yaml`.
