import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import light
from esphome.const import CONF_OUTPUT_ID, CONF_PIN
from .. import rotary_knob_ns, KnobHub, CONF_ROTARY_KNOB

KnobPixel = rotary_knob_ns.class_("KnobPixel", light.LightOutput, cg.Component)

CONFIG_SCHEMA = light.light_schema(KnobPixel, light.LightType.RGB).extend(
    {
        cv.GenerateID(CONF_ROTARY_KNOB): cv.use_id(KnobHub),
        cv.Required(CONF_PIN): cv.int_range(0, 31),
    }
)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_OUTPUT_ID])
    await cg.register_component(var, config)
    await light.register_light(var, config)
    hub = await cg.get_variable(config[CONF_ROTARY_KNOB])
    cg.add(var.set_parent(hub))
    cg.add(var.set_pin(config[CONF_PIN]))

