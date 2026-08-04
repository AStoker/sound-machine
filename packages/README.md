# The package layout

The firmware is split into three layers. The split exists so that a change has
exactly one plausible home: a new sensor is a `hw/` file, a new way to reach an
existing subsystem is a verb in `api/`, and a new *rule* about when things happen
is a `behavior/` file.

```
soundmachine.yaml        device core: platform, WiFi/API/OTA, the I2C bus, the manifest
packages/settings.yaml   every tunable in the build, grouped and documented

packages/hw/             THE PARTS.      One file per physical device.
packages/api/            THE ABSTRACTION. One file per subsystem.
packages/behavior/       THE LOGIC.      What the device actually does.
```

## The three layers

### `hw/` — one file per part

Owns a device's component config and the only register/pin-level talk to it.
Also owns *hardware interpretation*: lux to a brightness level, metres to "a hand
is near", volts to a state of charge. Interpretation belongs here because it is
about the physics, not about this device's choices.

A `hw/` file contains no policy. It never decides that a low battery deserves a
warning or that a knob turn means volume.

### `api/` — one file per subsystem

The abstraction layer. Everything else reaches a subsystem **through these
scripts**, never through its hardware. Each api file is the single writer of the
hardware behind it, which is what makes the invariants enforceable:

| api file | is the only writer of | key verbs |
|---|---|---|
| `api/display.yaml`   | the display driver        | `display_show_code`, `display_show_status`, `display_set_alert`, `display_show_message` |
| `api/sound.yaml`     | the audio chain           | `noise_play`, `noise_stop`, `media_*`, `volume_apply`, `sound_duck`/`sound_unduck` |
| `api/light.yaml`     | the crescent strip        | `crescent_off`, `crescent_static`, `crescent_effect` |
| `api/indicator.yaml` | the knob NeoPixel         | `indicator_set_hue`, `indicator_flash`, `indicator_glow_set` |

An api file may also own the *mechanism* that its hardware needs and callers
should not have to think about: the display's channel priority and heartbeat, the
indicator's fade and I2C write-throttling, the audio stack's boot gate.

### `behavior/` — the operational logic

Presets, gestures, announcements, boot restores, and the Home Assistant control
surface (selects, switches, numbers, buttons, text). Behavior decides; api does.

## The two rules

**1. Writes go through the api. Reads do not.**

A behavior package must not start the noise generator, build a `LightCall`, or
write an I2C register — it calls a verb. But reading state is free and expected:
`external_media_player->volume`, `id(battery_low).state`, `id(hand_near)`,
`media_player.is_announcing`. Routing reads through scripts would buy nothing —
ESPHome scripts cannot return a value — and would cost a lot of clarity.

**2. Hardware raises events; behavior implements them.**

A `hw/` file with an input on it calls one script per event, named after the
event. The handler is defined in the matching `behavior/` file. That way hardware
declares a contract without knowing who fulfils it, and remapping a control never
touches anything that talks to a bus.

| event script | raised by | implemented in |
|---|---|---|
| `on_knob_turn(clicks)` / `on_knob_tap` / `on_knob_hold` | `hw/knob.yaml` | `behavior/sound.yaml` |
| `on_touch_tap` / `on_touch_hold` | `hw/touch.yaml` | `behavior/light.yaml` |
| `on_hand_near_changed` | `hw/proximity.yaml` | `behavior/sound.yaml` |
| `on_external_power_changed` / `on_battery_low_changed` | `hw/power.yaml` | `behavior/power.yaml` |
| `on_audio_ready` | `api/sound.yaml` | `behavior/sound.yaml` |

These are hard dependencies: ESPHome resolves script ids at validate time, so
dropping a `behavior/` file whose events are still raised fails the build. That
is deliberate — it is the compiler telling you a contract is unmet.

**One event per fact, not one event per subsystem.** `hw/power.yaml` raises a
separate event for each of its two sensors. It used to share one, and the handler
then had to reconstruct *what* had changed from sensor state — which cost a
`has_state()` guard, an extra global, and a paragraph of explanation. A
binary_sensor's `on_state` is already edge-triggered, so one event per sensor
makes "this changed" the event itself.

## Things worth knowing before you edit

**All ids are global after the merge.** ESPHome merges every package into one
config, so a cross-package `id()` reference works — but each id must be defined
exactly *once*. Every file's header lists what it DEFINES and what it CONSUMES;
read those two lines before adding anything.

**Top-level list keys concatenate.** `sensor:`, `script:`, `globals:`,
`interval:`, `esphome.on_boot:` and friends accumulate across packages. That is
how several files can each add their own boot step or their own tick.

**Substitutions are global too, and local wins.** `settings.yaml` is a package
like any other, so the tiny device YAML on Home Assistant can override any value
in it. ESPHome merges packages *before* it expands `${...}`, which is why a
setting defined in one file is usable in all of them.

**The display is split across two files, and not for pluggability.**
`api/display.yaml` decides *what* to show — priority between four competing
sources, expiry, clock formatting — and `hw/matrix.yaml` draws it. There is one
display and no plan for another; the split earns its keep because those are two
unrelated problems, and merging them would bury 60 lines of policy in the middle
of 300 lines of fonts and register bursts.

**The driver must self-throttle.** `api/display.yaml` ticks several times a
second and calls `display_paint` every time. The driver hashes what it is about to
draw and returns before touching I2C when nothing changed. ~300 bytes on this
100 kHz bus is ~30 ms of bus time, on a bus that had to be slowed down for the
XVF3800 in the first place.

**Chips with no NVM repair themselves.** The matrix, the seesaw's NeoPixel and the
amp all lose their configuration to a glitch on the shared 5V rail, and in every
case the symptom is silent (a dark display, a dead pixel, an amp with its AGC
back on). Each one re-asserts: `hw/matrix.yaml` probes an enable register on a
tick, `api/indicator.yaml` re-sends the pin config whenever the pixel settles at
black, `hw/audio_chain.yaml` re-writes the amp's four registers on a tick. If you
add an I2C part that has to be configured, give it one of these.

**The crescent's pixel count is not a setting.** It is derived from the enclosure
geometry and lives in `hw/crescent.yaml`. `3d-print/check_docs.py` fails the
build if it drifts from `3d-print/enclosure_geom.py`. See the note in
`../CLAUDE.md`.

## Where to add a thing

| I want to… | Do this |
|---|---|
| tune a number | `settings.yaml`, in the matching section |
| add a sensor or chip | a new `hw/` file; raise events, don't handle them |
| let something new drive the display | call an `api/display.yaml` verb — never `display_paint` |
| add a display channel | a row in `api/display.yaml`'s priority table + a setter |
| add a light preset | an option in `behavior/light.yaml`'s select + a row in its colour table |
| add a noise colour | an option in `behavior/sound.yaml`'s Sound select |
| add a flashed track | a `files:` entry in `hw/audio_chain.yaml` + a `media_play_*` verb in `api/sound.yaml` + an option in `behavior/sound.yaml` |
| change what a button does | the event handler in `behavior/` — the `hw/` file stays put |
