# Sound Machine

ESPHome firmware for a bedside smart sound machine built on a ReSpeaker Flex
(XVF3800 + XIAO ESP32-S3): white/pink/brown noise, voice assistant, a 7-seg
clock, an SK6812 sunrise crescent, and battery/UPS monitoring.

## Layout

| Path | What |
|------|------|
| `soundmachine.yaml` | Device core + the package manifest (the build entry point) |
| [`packages/README.md`](packages/README.md) | **The architecture map** — start here to change firmware behavior |
| `packages/settings.yaml` | Every tunable in the build, in one documented file |
| `packages/hw/` | One file per physical part (matrix, crescent, knob, UPS, sensors…) |
| `packages/api/` | The abstraction layer — `display`, `sound`, `light`, `indicator` |
| `packages/behavior/` | Operational logic: presets, gestures, announcements, voice |
| `components/` | Custom ESPHome components: `noise_source`, `seesaw`, `tpa2016` |
| `sounds/` | On-device audio baked into flash |
| `soundmachine.min.yaml` | Reference minimal device YAML for Home Assistant |
| `secrets.example.yaml` | The secret keys you must provide locally |

## Running it from Home Assistant (pull latest from GitHub)

The full config lives here on GitHub. Home Assistant keeps only a tiny device
YAML that pulls this repo as an ESPHome **remote package**, so every build
compiles the latest `main`.

1. Copy [`soundmachine.min.yaml`](soundmachine.min.yaml) into your HA ESPHome
   config folder (rename it if you like — the filename becomes the device).
2. Add the keys from [`secrets.example.yaml`](secrets.example.yaml) to that
   folder's `secrets.yaml` with real values.
3. Compile/install from the ESPHome dashboard.

That's it — the device config, the custom `components/`, and the packaged
sub-configs are all fetched from this repo at build time.

### How it works

- Credentials are **substitutions**, not `!secret` — remote packages can't
  contain secret lookups. The minimal device YAML injects them from the local
  `secrets.yaml`, overriding the placeholders in `soundmachine.yaml`.
- The custom components are pulled via a **git** `external_components` source
  (`github://astoker/sound-machine`) so they resolve identically locally and on
  HA. For local component development, push first then build (or temporarily
  switch that source back to `type: local, path: components`).

## Building locally

```sh
# create a secrets.yaml next to soundmachine.yaml with the 5 keys, then:
esphome config soundmachine.yaml     # validate
esphome run soundmachine.yaml        # build + upload
```

## On-device media (the `la_la_sad_source` substitution)

ESPHome resolves a local `file:` path against the config directory of whichever
machine runs the build. When HA pulls this repo as a remote package, that
directory is HA's — not this repo — so a bare `sounds/…` path wouldn't be found
there even though the file lives in the repo. So the media source is a
substitution, `la_la_sad_source`, defaulting to a raw GitHub **URL** that
ESPHome downloads at build time (works everywhere; verified). For local/offline
dev with the repo checked out, override it with the repo-relative path:

```yaml
# in a local dev entry YAML (or temporarily in soundmachine.yaml substitutions)
substitutions:
  la_la_sad_source: sounds/La-la-sad.mp3
```

Any additional flashed audio should follow the same pattern: add a
`<name>_source` substitution (URL default) rather than a bare path.

## Notes

- The UPS monitor I2C address and shunt value in `soundmachine.yaml` are
  placeholders — see the comments in the `substitutions:` block.
