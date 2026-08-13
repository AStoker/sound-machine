#pragma once

#include "esphome/core/component.h"
#include "esphome/components/sensor/sensor.h"
#include "../rotary_knob.h"

namespace esphome {
namespace rotary_knob {

class KnobAnalogInput : public sensor::Sensor, public PollingComponent {
 public:
  void setup() override;
  void update() override;

  void set_parent(KnobHub *parent) { this->parent_ = parent; }
  void set_pin(uint8_t pin) { this->pin_ = pin; }

 protected:
  KnobHub *parent_;
  uint8_t pin_;
};

}  // namespace rotary_knob
}  // namespace esphome
