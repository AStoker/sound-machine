import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import binary_sensor
from esphome.const import CONF_ID, CONF_PIN
from .. import rotary_knob_ns, KnobHub, CONF_ROTARY_KNOB

KnobButton = rotary_knob_ns.class_(
    "KnobButton", binary_sensor.BinarySensor, cg.Component
)

CONFIG_SCHEMA = binary_sensor.binary_sensor_schema(KnobButton).extend(
    {
        cv.GenerateID(CONF_ROTARY_KNOB): cv.use_id(KnobHub),
        cv.Required(CONF_PIN): cv.int_range(0, 31),
    }
).extend(cv.COMPONENT_SCHEMA)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await binary_sensor.register_binary_sensor(var, config)
    hub = await cg.get_variable(config[CONF_ROTARY_KNOB])
    cg.add(var.set_parent(hub))
    cg.add(var.set_pin(config[CONF_PIN]))

