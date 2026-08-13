#include "knob_pixel.h"
#include "esphome/core/log.h"

namespace esphome {
namespace rotary_knob {

static const char *const TAG = "rotary_knob.pixel";

void KnobPixel::setup() {
  this->parent_->setup_neopixel(this->pin_);
}

light::LightTraits KnobPixel::get_traits() {
  auto traits = light::LightTraits();
  traits.set_supported_color_modes({light::ColorMode::RGB});
  return traits;
}
void KnobPixel::write_state(light::LightState *state) {
  float red, green, blue;
  state->current_values_as_rgb(&red, &green, &blue);
  this->parent_->color_neopixel(red * 255, green * 255, blue * 255);
}

}  // namespace rotary_knob
}  // namespace esphome

