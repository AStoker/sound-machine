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
> crescent — pixel count, row layout, row pitch. `packages/lighting.yaml` carries
> a *copy* of that output (`num_leds` and `leds_per_row[]`). **If you change the
> crescent, re-run `gen_drawing.py` and re-sync those two values**, or the
> firmware will address pixels that are not there. Currently **48 px**,
> `{10, 10, 9, 8, 7, 4}`.
>
> `3d-print/check_docs.py` enforces this — run it after any geometry change.

## Commands

```sh
# Validate the full merged config (packages + git external_components + media):
esphome config soundmachine.yaml

# Build + upload:
esphome run soundmachine.yaml
```

- `esphome config` needs **no** local `secrets.yaml` — credentials are
  substitutions with valid placeholder defaults (see below). It *does* need
  network + the GitHub repo to exist, because it clones the custom components
  and downloads the flashed media at validate time.
- `.esphome/` is the build cache (gitignored). It can end up with read-only
  files; if `rm -rf .esphome` fails, run `chmod -R u+w .esphome && rm -rf .esphome`.

## Architecture

**`soundmachine.yaml` is the entry point** and holds only the device core:
the `substitutions:` block (the single source of truth for every tunable),
the `packages:` includes, and shared infrastructure (esphome/boot, esp32, wifi/
api/ota, `i2c` bus, `external_components`, `time`). It is intentionally kept
small; feature logic lives in packages.

**Feature packages** in `packages/` — `audio`, `lighting`, `battery`, `ambient`
(the display substrate), plus **one** display package: `matrix` (IS31FL3731
charlieplex, the active default) or `display` (HT16K33 7-seg, kept as a drop-in
alternative) — are each a self-contained slice. Every package file starts with a
header documenting the ids it **defines** vs **consumes**. Read those headers
before editing: after ESPHome merges all packages, **all ids are global**, so
cross-package references (e.g. the Sound select setting the display's
`preset_code`) work but each id must be defined exactly once. Top-level list keys
(`sensor:`, `binary_sensor:`, `script:`, `globals:`, etc.) concatenate across
packages.

**The display is pluggable.** `ambient.yaml` owns the display-agnostic layer —
the BH1750 auto-dim (`display_brightness`), the `preset_code`/`showing_preset`
state, `show_preset_code`, and the single 1s render tick — and calls a
`render_display` script that the active *display* package provides. Load exactly
one display package (`matrix` **or** `display`); both define `render_display`, so
loading both collides. Swap them in the `packages:` block of `soundmachine.yaml`.

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
> `packages/knob.yaml` and only to pre-light the knob NeoPixel. The
> **touchless-wake** gesture the hardware notes describe is still *not*
> implemented — don't assume any behavior beyond the knob pixel reads it.

**The knob NeoPixel is driven from a lambda, not the seesaw `light:` platform,
on purpose.** `packages/knob.yaml` calls the component's `color_neopixel()`
directly from a 20 Hz interval that writes only on a change. Going through the
`light:` platform would instead write the pixel over I2C once per *main-loop
iteration* for the whole of every transition — hundreds of writes/second onto
the bus this build already had to slow to 100 kHz to stop starving the XVF3800.
If you switch it to the stock platform, that regression is what you are buying.

Cross-file invariants worth knowing before changing behavior:
- **Display is single-owner.** The active display package's `render_display`
  (`packages/matrix.yaml` today, or `packages/display.yaml` for the 7-seg) is the
  ONLY writer of the display. It renders one thing, in priority order:
  HA-authored message → device status message → low-battery warning → transient
  preset code → clock. Other packages never write the display directly; they go
  through one of the two transient channels in `ambient.yaml`:
  - `preset_code`/`showing_preset` + `show_preset_code` — short codes ("L1",
    "S3", "OFF") from a user turning a knob or picking a select.
  - `show_status_message(text, seconds)` — short announcements from device events
    (today: `battery.yaml` announcing "CHG"/"BATT" when External Power flips).
    Keep new callers here, **not** on a display-specific id, or the documented
    matrix ↔ 7-seg swap stops compiling.
- **4 characters is the static budget for a status message.** The matrix draws it
  inside a SINGLE panel (the right-hand one) in the compact 3x5 font, so it can
  never straddle the inter-panel gap — which is why no seam-alignment logic is
  needed for it. 4 chars = 15px inside 16 columns. Longer strings still work but
  fall back to scrolling the full width, and a pass takes far longer than the few
  seconds a status is meant to occupy. The 7-seg alternative has 4 digits, so the
  same budget happens to apply there.
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
`soundmachine.yaml` substitutions are UNCONFIRMED placeholders — confirm against
the boot I2C scan. INA219 vs INA226 may need swapping in `packages/battery.yaml`.
