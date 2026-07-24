import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import i2c
from esphome.const import CONF_ID

CODEOWNERS = ["@andy"]
DEPENDENCIES = ["i2c"]

CONF_COMPRESSION = "compression"
CONF_GAIN_DB = "gain_db"
CONF_MAX_GAIN_DB = "max_gain_db"
CONF_LIMITER = "limiter"
CONF_LIMITER_LEVEL = "limiter_level"
CONF_NOISE_GATE = "noise_gate"
CONF_LEFT_ENABLED = "left_enabled"
CONF_RIGHT_ENABLED = "right_enabled"

tpa2016_ns = cg.esphome_ns.namespace("tpa2016")
TPA2016 = tpa2016_ns.class_("TPA2016", cg.Component, i2c.I2CDevice)

Compression = tpa2016_ns.enum("Compression")
COMPRESSION_RATIOS = {
    "1:1": Compression.COMPRESSION_1_1,
    "2:1": Compression.COMPRESSION_2_1,
    "4:1": Compression.COMPRESSION_4_1,
    "8:1": Compression.COMPRESSION_8_1,
}

CONFIG_SCHEMA = (
    cv.Schema(
        {
            cv.GenerateID(): cv.declare_id(TPA2016),
            # 1:1 disables the AGC. Anything else reintroduces time-varying
            # gain downstream of the DSP's echo reference and will degrade
            # acoustic echo cancellation.
            cv.Optional(CONF_COMPRESSION, default="1:1"): cv.enum(COMPRESSION_RATIOS),
            # Fixed analog gain. Hardware range is -28..30 dB with compression
            # on, but only 0..30 dB once compression is 1:1.
            cv.Optional(CONF_GAIN_DB, default=6): cv.int_range(min=-28, max=30),
            # Ceiling the AGC may ramp to. Ignored when compression is 1:1.
            cv.Optional(CONF_MAX_GAIN_DB, default=30): cv.int_range(min=18, max=30),
            cv.Optional(CONF_LIMITER, default=True): cv.boolean,
            # Output limiter threshold in dBV, -6.5 to 9.0 in 0.5 dB steps.
            cv.Optional(CONF_LIMITER_LEVEL, default=9.0): cv.float_range(
                min=-6.5, max=9.0
            ),
            # Only functions when compression is enabled; off by default.
            cv.Optional(CONF_NOISE_GATE, default=False): cv.boolean,
            cv.Optional(CONF_LEFT_ENABLED, default=True): cv.boolean,
            cv.Optional(CONF_RIGHT_ENABLED, default=True): cv.boolean,
        }
    )
    .extend(cv.COMPONENT_SCHEMA)
    .extend(i2c.i2c_device_schema(0x58))
)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await i2c.register_i2c_device(var, config)

    cg.add(var.set_compression(config[CONF_COMPRESSION]))
    cg.add(var.set_gain_db(config[CONF_GAIN_DB]))
    # Register 7 bits 7:4 hold (max_gain_dB - 18).
    cg.add(var.set_max_gain_bits(config[CONF_MAX_GAIN_DB] - 18))
    cg.add(var.set_limiter_enabled(config[CONF_LIMITER]))
    # Register 6 bits 4:0: level_dBV = -6.5 + 0.5 * bits.
    cg.add(var.set_limiter_bits(int(round((config[CONF_LIMITER_LEVEL] + 6.5) * 2))))
    cg.add(var.set_noise_gate(config[CONF_NOISE_GATE]))
    cg.add(var.set_left_enabled(config[CONF_LEFT_ENABLED]))
    cg.add(var.set_right_enabled(config[CONF_RIGHT_ENABLED]))
