#include "knob_temperature.h"
#include "esphome/core/log.h"

namespace esphome {
namespace rotary_knob {

static const char *const TAG = "rotary_knob.temperature";

void KnobTemperature::setup() {
  ESP_LOGCONFIG(TAG, "Setting up KnobHub temperature...");
}

void KnobTemperature::update() {
  float value = this->parent_->get_temperature();
  this->publish_state(value);
}

}  // namespace rotary_knob
}  // namespace esphome
