#pragma once

#include "esphome/core/component.h"
#include "esphome/components/sensor/sensor.h"
#include "../rotary_knob.h"

namespace esphome {
namespace rotary_knob {

class KnobTemperature : public sensor::Sensor, public PollingComponent {
 public:
  void setup() override;
  void update() override;

  void set_parent(KnobHub *parent) { parent_ = parent; }

 protected:
  KnobHub *parent_;
};

}  // namespace rotary_knob
}  // namespace esphome
