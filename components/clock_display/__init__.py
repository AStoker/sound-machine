"""The clock display: 16x9 LED matrix panels tiled into one text/clock surface.

Renders a `Frame` - text or a clock, at a brightness - and makes no decisions
about what that frame should contain. See clock_display.h for the tiling, the
inter-panel gap and the self-healing probe, and packages/api/display.yaml for who
decides what to show.

The panels are IS31FL3731 charlieplex drivers, which ESPHome has no component
for; that part number and its register map are the only things in here that need
to know it.
"""

import esphome.codegen as cg
from esphome.components import i2c
import esphome.config_validation as cv
from esphome.const import CONF_ID

CODEOWNERS = ["@andy"]
DEPENDENCIES = ["i2c"]

CONF_ADDRESSES = "addresses"
CONF_PANEL_GAP = "panel_gap"
CONF_PWM_MIN = "pwm_min"
CONF_PWM_MAX = "pwm_max"
CONF_PROBE_INTERVAL = "probe_interval"

clock_display_ns = cg.esphome_ns.namespace("clock_display")
ClockDisplay = clock_display_ns.class_("ClockDisplay", cg.Component)

MAX_PANELS = 2

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(ClockDisplay),
        cv.GenerateID(i2c.CONF_I2C_ID): cv.use_id(i2c.I2CBus),
        # ONE ADDRESS PER PANEL, left to right. The count of these IS the panel
        # count - listing one is the single-panel bring-up mode, and the second
        # address is then never touched, so an unwired board causes no I2C
        # errors. This replaces a separate "how many panels" setting that could
        # disagree with the addresses beside it.
        cv.Required(CONF_ADDRESSES): cv.All(
            cv.ensure_list(cv.i2c_address), cv.Length(min=1, max=MAX_PANELS)
        ),
        # Physical dead columns between adjacent panels. Two panels butted
        # together are NOT seamless; the driver lays content out in physical
        # columns that include this gap and maps back at draw time.
        cv.Optional(CONF_PANEL_GAP, default=1): cv.int_range(min=0, max=8),
        # Lit-pixel PWM at the darkest and brightest ends of the ambient
        # auto-dim. The minimum is never 0 - digits must stay readable.
        cv.Optional(CONF_PWM_MIN, default=3): cv.int_range(min=1, max=255),
        cv.Optional(CONF_PWM_MAX, default=40): cv.int_range(min=1, max=255),
        # How often to check the panels still hold the configuration they were
        # given. One 1-byte register read per panel, so this is cheap to run
        # often; it is the ceiling on how long a reset display could stay dark.
        cv.Optional(
            CONF_PROBE_INTERVAL, default="10s"
        ): cv.positive_time_period_milliseconds,
    }
).extend(cv.COMPONENT_SCHEMA)


def _validate_pwm_range(config):
    if config[CONF_PWM_MIN] > config[CONF_PWM_MAX]:
        raise cv.Invalid(
            f"{CONF_PWM_MIN} ({config[CONF_PWM_MIN]}) must not exceed "
            f"{CONF_PWM_MAX} ({config[CONF_PWM_MAX]})"
        )
    return config


FINAL_VALIDATE_SCHEMA = _validate_pwm_range


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)

    bus = await cg.get_variable(config[i2c.CONF_I2C_ID])
    cg.add(var.set_i2c_bus(bus))
    for address in config[CONF_ADDRESSES]:
        cg.add(var.add_address(address))
    cg.add(var.set_panel_gap(config[CONF_PANEL_GAP]))
    cg.add(var.set_pwm_range(config[CONF_PWM_MIN], config[CONF_PWM_MAX]))
    cg.add(var.set_probe_interval(config[CONF_PROBE_INTERVAL].total_milliseconds))
