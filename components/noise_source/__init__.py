import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import speaker
from esphome.const import CONF_ID

CODEOWNERS = ["@andy"]
DEPENDENCIES = ["speaker", "audio"]

CONF_SPEAKER = "speaker"
CONF_NOISE_TYPE = "noise_type"
CONF_SAMPLE_RATE = "sample_rate"
CONF_GAIN = "gain"
CONF_FADE_LENGTH = "fade_length"

noise_source_ns = cg.esphome_ns.namespace("noise_source")
NoiseSource = noise_source_ns.class_("NoiseSource", cg.Component)

NoiseColor = noise_source_ns.enum("NoiseColor")
NOISE_COLORS = {
    "WHITE": NoiseColor.NOISE_WHITE,
    "PINK": NoiseColor.NOISE_PINK,
    "BROWN": NoiseColor.NOISE_BROWN,
}

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(NoiseSource),
        cv.Required(CONF_SPEAKER): cv.use_id(speaker.Speaker),
        cv.Optional(CONF_NOISE_TYPE, default="WHITE"): cv.enum(
            NOISE_COLORS, upper=True
        ),
        cv.Optional(CONF_SAMPLE_RATE, default=48000): cv.positive_not_null_int,
        cv.Optional(CONF_GAIN, default="30%"): cv.percentage,
        cv.Optional(
            CONF_FADE_LENGTH, default="3s"
        ): cv.positive_time_period_milliseconds,
    }
).extend(cv.COMPONENT_SCHEMA)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)

    spk = await cg.get_variable(config[CONF_SPEAKER])
    cg.add(var.set_speaker(spk))
    cg.add(var.set_noise_type(config[CONF_NOISE_TYPE]))
    cg.add(var.set_sample_rate(config[CONF_SAMPLE_RATE]))
    cg.add(var.set_gain(config[CONF_GAIN]))
    cg.add(var.set_fade_ms(config[CONF_FADE_LENGTH].total_milliseconds))