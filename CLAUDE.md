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

**Feature packages** in `packages/` — `audio`, `lighting`, `display`, `battery`
— are each a self-contained slice. Every package file starts with a header
documenting the ids it **defines** vs **consumes**. Read those headers before
editing: after ESPHome merges all packages, **all ids are global**, so cross-
package references (e.g. the Sound select setting the display's `preset_code`)
work but each id must be defined exactly once. Top-level list keys (`sensor:`,
`binary_sensor:`, `script:`, `globals:`, etc.) concatenate across packages.

**Custom C++ components** in `components/` (`noise_source`, `seesaw`, `tpa2016`)
follow standard ESPHome layout (`__init__.py` codegen + `.h`/`.cpp`). `seesaw`
is vendored locally (patched `dump_summary()` for ESPHome 2026.7.x); the upstream
ssieb git source is left commented in `external_components`.

**Sensors & controls live across packages, on one shared I2C bus.** Implemented
today: BH1750 ambient light (display auto-dim), seesaw rotary encoder (volume +
tap/hold sound control), DS3231 RTC (time source), plus an ESP32 native
capacitive touch pad (light-preset cycle). See `HARDWARE.md` for the full map.

> **Gotcha:** the hardware map and the `logger:` block reference a **VL53L0X
> ToF** (`0x29`, planned touchless wake), but it has no ESPHome entity yet — it
> is wired-in intent, not live config. Don't assume a `vl53l0x:` sensor exists;
> adding it is open work.

Cross-file invariants worth knowing before changing behavior:
- **Display is single-owner.** `render_display` (in `packages/display.yaml`) is
  the ONLY writer of the 7-seg. It renders one of three things in priority
  order: low-battery "LO" warning → transient preset code → clock. Preset
  selects in other packages set `preset_code`/`showing_preset` and call
  `show_preset_code`; they never write the display directly.
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
