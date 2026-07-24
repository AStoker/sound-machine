# Sound Machine

ESPHome firmware for a bedside smart sound machine built on a ReSpeaker Flex
(XVF3800 + XIAO ESP32-S3): white/pink/brown noise, voice assistant, a 7-seg
clock, an SK6812 sunrise crescent, and battery/UPS monitoring.

## Layout

| Path | What |
|------|------|
| `faux-hatch.yaml` | Device core + feature package includes (the build entry point) |
| `packages/` | `audio`, `lighting`, `display`, `battery` — one slice each |
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
  `secrets.yaml`, overriding the placeholders in `faux-hatch.yaml`.
- The custom components are pulled via a **git** `external_components` source
  (`github://astoker/sound-machine`) so they resolve identically locally and on
  HA. For local component development, push first then build (or temporarily
  switch that source back to `type: local, path: components`).

## Building locally

```sh
# create a secrets.yaml next to faux-hatch.yaml with the 5 keys, then:
esphome config faux-hatch.yaml     # validate
esphome run faux-hatch.yaml        # build + upload
```

## Notes

- On-device media (`sounds/La-la-sad.mp3`) is referenced by a repo-relative
  path. On the very first HA build, confirm it resolves from the pulled repo. If
  it doesn't, either drop the file into your HA ESPHome folder under `sounds/`,
  or point the `file:` in `packages/audio.yaml` at the raw GitHub URL.
- The UPS monitor I2C address and shunt value in `faux-hatch.yaml` are
  placeholders — see the comments in the `substitutions:` block.
