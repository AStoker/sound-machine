#pragma once

#include "esphome/core/component.h"
#include "esphome/components/light/light_output.h"
#include "../rotary_knob.h"

namespace esphome {
namespace rotary_knob {

class KnobPixel : public light::LightOutput, public Component {
 public:
  void setup() override;
  void set_parent(KnobHub *parent) { parent_ = parent; }
  void set_pin(int pin) { this->pin_ = pin; }
  light::LightTraits get_traits() override;
  void write_state(light::LightState *state) override;
 protected:
  KnobHub *parent_;
  int pin_;
};

}  // namespace rotary_knob
}  // namespace esphome
