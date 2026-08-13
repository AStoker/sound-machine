#include "knob_analog_input.h"
#include "esphome/core/log.h"

namespace esphome {
namespace rotary_knob {

static const char *const TAG = "rotary_knob.analog";

void KnobAnalogInput::setup() {
  ESP_LOGCONFIG(TAG, "Setting up KnobHub touch sensor...");
}

void KnobAnalogInput::update() {
  uint16_t value = this->parent_->analog_read(this->pin_);
  this->publish_state(value);
}

}  // namespace rotary_knob
}  // namespace esphome
