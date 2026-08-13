#include "esphome/core/hal.h"
#include "knob_button.h"
#include "esphome/core/log.h"

namespace esphome {
namespace rotary_knob {

static const char *const TAG = "rotary_knob.button";

void KnobButton::setup() {
  this->parent_->set_pinmode(this->pin_, gpio::FLAG_PULLUP);
  this->parent_->set_gpio_interrupt(this->pin_, true);
  this->publish_initial_state(this->parent_->digital_read(this->pin_));
}

void KnobButton::dump_config() {
  LOG_BINARY_SENSOR("", "KnobHub Binary Sensor", this);
  ESP_LOGCONFIG(TAG, "  Pin: %d", this->pin_);
}

void KnobButton::loop() { this->publish_state(!this->parent_->digital_read(this->pin_)); }

}  // namespace rotary_knob
}  // namespace esphome
