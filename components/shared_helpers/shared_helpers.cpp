#include "shared_helpers.h"

#include <cmath>

namespace esphome {
namespace shared_helpers {

Rgb hue_to_rgb(float hue_degrees) {
  float hue = fmodf(hue_degrees, 360.0f);
  if (hue < 0.0f)
    hue += 360.0f;

  // Six 60-degree sectors. At full saturation one channel is always at full,
  // one is always at zero, and the third ramps across the sector.
  const float sextant = hue / 60.0f;
  const int sector = static_cast<int>(sextant) % 6;
  const float ramp = sextant - floorf(sextant);
  const float ramp_down = 1.0f - ramp;

  switch (sector) {
    case 0:
      return {1.0f, ramp, 0.0f};
    case 1:
      return {ramp_down, 1.0f, 0.0f};
    case 2:
      return {0.0f, 1.0f, ramp};
    case 3:
      return {0.0f, ramp_down, 1.0f};
    case 4:
      return {ramp, 0.0f, 1.0f};
    default:
      return {1.0f, 0.0f, ramp_down};
  }
}

void cycle_to_next_option(select::Select *select, int resume_index) {
  if (select == nullptr || select->size() < 2)
    return;

  const size_t on_count = select->size() - 1;  // every option except Off
  const size_t current = select->active_index().value_or(0);

  size_t next;
  if (current == 0) {
    // Coming back from Off: resume what was last on, guarding a resume index
    // that no longer names an option (the list can shrink between builds).
    next = (resume_index >= 1 && static_cast<size_t>(resume_index) <= on_count)
               ? static_cast<size_t>(resume_index)
               : 1;
  } else {
    next = (current % on_count) + 1;
  }

  select->make_call().set_index(next).perform();
}

}  // namespace shared_helpers
}  // namespace esphome
