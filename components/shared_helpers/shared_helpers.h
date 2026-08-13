#pragma once

#include "esphome/components/select/select.h"

#include <string>

namespace esphome {
namespace shared_helpers {

// ---------------------------------------------------------------------------
// SOUND MACHINE SHARED HELPERS - the small pieces of logic that more than one
// YAML lambda needs.
//
// WHY THIS IS A COMPONENT AND NOT AN `includes:` FILE. ESPHome merges every
// lambda into one generated main.cpp, which includes the header of every
// component in the config - so a free function declared here is callable from
// any lambda in any package. The obvious alternative, `esphome: includes:`,
// resolves its path against the BUILD MACHINE's config directory, which breaks
// the moment this config is pulled onto Home Assistant as a remote package (the
// same trap documented for media file: paths and for `type: local` components).
// A git-sourced component has no such problem.
//
// WHAT BELONGS HERE: logic that is genuinely shared between packages and cannot
// be a script, because ESPHome scripts return nothing and cannot take an id as a
// parameter. That is a narrow bar - keep it narrow. Anything that belongs to one
// subsystem belongs in that subsystem's package.
// ---------------------------------------------------------------------------

// ---- Colour ----------------------------------------------------------------

// Fully-saturated hue as red/green/blue, each 0..1.
//
// IN FLOAT, DELIBERATELY, rather than via light::ESPHSVColor, whose hue is a
// uint8 (1.4 degrees per count). Both callers need finer steps than that:
// api/indicator.yaml sweeps the knob pixel smoothly across the whole wheel as
// the volume changes, and hw/crescent.yaml's Colour Cycle spreads its pixels a
// few degrees apart so they straddle an output quantisation step (its own
// comment block explains why). Quantising the hue first would collapse both.
struct Rgb {
  float red;
  float green;
  float blue;
};
Rgb hue_to_rgb(float hue_degrees);

// ---- Selects ---------------------------------------------------------------

// Advance a select that is laid out as "Off, then N things", and perform the
// change.
//
// THE MODEL, which both the Sound select and the Crescent Preset select use:
// option 0 is Off and is reachable only by a deliberate act (a long press), so
// cycling never lands on darkness or silence by accident. From any ON option
// this advances to the next one and wraps back to option 1. From Off it RESUMES
// `resume_index` - the caller's memory of the last ON option - rather than
// restarting the cycle at 1.
//
// The select knows its own options, their order and how many there are, so this
// needs no count setting and no name table: `size()` and `active_index()` are
// the whole implementation. That is what keeps the option list the single source
// of truth for the order.
void cycle_to_next_option(select::Select *select, int resume_index);

}  // namespace shared_helpers
}  // namespace esphome
