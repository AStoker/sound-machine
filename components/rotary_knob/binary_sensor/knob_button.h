#pragma once

#include "esphome/core/component.h"
#include "esphome/components/binary_sensor/binary_sensor.h"
#include "../rotary_knob.h"

namespace esphome {
namespace rotary_knob {

class KnobButton : public binary_sensor::BinarySensor, public Component {
 public:
  void setup() override;
  void dump_config() override;
  void loop() override;
  void set_parent(KnobHub *parent) { this->parent_ = parent; }
  void set_pin(int pin) { this->pin_ = pin; }

 protected:
  KnobHub *parent_;
  int pin_;
};

}  // namespace rotary_knob
}  // namespace esphome
