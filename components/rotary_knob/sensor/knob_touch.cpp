#include "knob_touch.h"
#include "esphome/core/log.h"

namespace esphome {
namespace rotary_knob {

static const char *const TAG = "rotary_knob.touch";

void KnobTouch::setup() {
  ESP_LOGCONFIG(TAG, "Setting up KnobHub touch sensor...");
}

void KnobTouch::update() {
  // Signed, deliberately: get_touch_value() returns -1 on an I2C failure. Held
  // in a uint16_t that sentinel becomes 65535 and the check below never fires.
  int16_t value = this->parent_->get_touch_value(this->channel_);
  if (value == -1)
    ESP_LOGW(TAG, "touch reading failed for channel %d", this->channel_);
  else
    this->publish_state(value);
}

}  // namespace rotary_knob
}  // namespace esphome
