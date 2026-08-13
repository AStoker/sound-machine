# `rotary_knob` — the I2C rotary encoder board

Drives an Adafruit I2C QT Rotary Encoder (product #4991): a quadrature encoder, a
push switch, and a single NeoPixel, all reached over I2C through one hub.

## Provenance and the name

This is a **vendored, renamed copy of [ssieb](https://github.com/ssieb/esphome_components)'s
`seesaw` component.** "Seesaw" is Adafruit's name for the firmware their I2C
bridge chips run — accurate, but it tells a reader nothing about what this device
uses it for, so the component is named for its job here instead. The chip's own
vocabulary (the `SEESAW_*` register constants, `ChipModule`) is kept *inside* the
component, where it is the right vocabulary.

Local changes on top of upstream:

- `dump_summary()` patched for ESPHome 2026.7.x.
- `digital_write()` fixed to pass a bitmask rather than a pin number — upstream
  computed the mask and then discarded it, so writing pin 24 set pins 3 and 4.
- Renamed throughout (`Seesaw` → `KnobHub`, and so on).

To diff against upstream, fetch `ssieb/esphome_components` and compare
`seesaw/` with this directory; the commented-out git source in
`soundmachine.yaml` records where it came from.

## What this build actually uses

Only the **encoder** sensor and the **push switch** binary_sensor are configured
(see `packages/hw/knob.yaml`). The NeoPixel is driven by `packages/api/indicator.yaml`
calling `color_neopixel()` directly rather than through the `light:` platform
below — that file's header explains why, and it is a deliberate choice about I2C
traffic, not an oversight.

The analog-input, temperature and touch sensors and the light platform are carried
from upstream but unused here.

## Usage

```yaml
rotary_knob:
  id: knob_hub
  address: 0x36

sensor:
  - platform: rotary_knob
    id: encoder
    type: encoder
    name: "Volume knob"
    number: 0            # optional, defaults to 0
  - platform: rotary_knob
    type: temperature
  - platform: rotary_knob
    type: touch
    channel: 5
  - platform: rotary_knob
    type: adc
    pin: 2

binary_sensor:
  - platform: rotary_knob
    id: button
    name: "Knob press"
    pin: 24

light:
  - platform: rotary_knob
    id: pixel
    name: "Knob LED"
    pin: 6
```
