#pragma once

#include "esphome/core/component.h"
#include "esphome/components/sensor/sensor.h"
#include "../rotary_knob.h"

namespace esphome {
namespace rotary_knob {

class KnobTouch : public sensor::Sensor, public PollingComponent {
 public:
  void setup() override;
  void update() override;

  void set_parent(KnobHub *parent) { parent_ = parent; }
  void set_channel(uint8_t channel) { channel_ = channel; }

 protected:
  KnobHub *parent_;
  uint8_t channel_;
};

}  // namespace rotary_knob
}  // namespace esphome
