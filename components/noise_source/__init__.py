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
CONF_HIGH_PASS_FREQUENCY = "high_pass_frequency"
CONF_HIGH_PASS_MAKEUP = "high_pass_makeup"

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
        # Output high-pass corner in Hz. Set to 0 to disable the filter and get
        # the pre-filter behaviour back byte for byte -- the C++ side forces the
        # makeup gain below to a no-op whenever the filter is disabled, so it is
        # safe to leave high_pass_makeup untouched while toggling this to 0 for
        # an A/B comparison.
        cv.Optional(CONF_HIGH_PASS_FREQUENCY, default=160.0): cv.float_range(
            min=0.0, max=2000.0
        ),
        # Level restored to the brown branch after the high-pass removes most of
        # its energy. Only takes effect while the filter above is enabled. Tune
        # by ear against white/pink at the same volume setting.
        cv.Optional(CONF_HIGH_PASS_MAKEUP, default=1.0): cv.float_range(
            min=0.1, max=64.0
        ),
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
    cg.add(var.set_high_pass_freq(config[CONF_HIGH_PASS_FREQUENCY]))
    cg.add(var.set_high_pass_makeup(config[CONF_HIGH_PASS_MAKEUP]))