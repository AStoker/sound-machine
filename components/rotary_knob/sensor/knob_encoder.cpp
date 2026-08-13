#include "knob_encoder.h"
#include "esphome/core/log.h"

namespace esphome {
namespace rotary_knob {

static const char *const TAG = "rotary_knob.encoder";

void KnobEncoder::setup() {
  ESP_LOGCONFIG(TAG, "Setting up KnobHub rotary encoder...");
  this->parent_->enable_encoder(this->number_);
  this->publish_state(0);
}

void KnobEncoder::loop() {
  int32_t new_value = this->parent_->get_encoder_position(this->number_);
  if (new_value < this->min_value_)
    new_value = this->min_value_;
  if (new_value > this->max_value_)
    new_value = this->max_value_;
  if (new_value == this->value_)
    return;
  this->value_ = new_value;
  this->publish_state(new_value);
}

}  // namespace rotary_knob
}  // namespace esphome
