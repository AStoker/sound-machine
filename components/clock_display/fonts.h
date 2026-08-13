#pragma once

#include <cstddef>
#include <cstdint>

namespace esphome {
namespace clock_display {

// Bitmap fonts for the matrix, as row patterns with the MSB as the leftmost
// column. Two sizes: 5x7 for the clock and wide text on a dual panel, 3x5 for
// anything that has to fit inside a single 16-column panel.
//
// A FONT IS DATA, NOT A BRANCH. Both sizes carry the same three tables in the
// same order, so one glyph() serves both and callers pass a Font around rather
// than a width they then have to switch on.
struct Font {
  uint8_t width;
  uint8_t height;
  const uint8_t *digits;  // [10][height],  '0'..'9'
  const uint8_t *alpha;   // [26][height],  'A'..'Z'
  const uint8_t *punct;   // [PUNCTUATION_COUNT][height], in PUNCTUATION order

  // One column of blank between glyphs.
  uint8_t pitch() const { return this->width + 1; }
  // Physical columns `length` glyphs occupy, trailing blank excluded.
  int text_width(size_t length) const {
    return length == 0 ? 0 : static_cast<int>(length) * this->pitch() - 1;
  }
};

// The punctuation both fonts draw, in the order their `punct` tables store it.
extern const char PUNCTUATION[];
extern const uint8_t PUNCTUATION_COUNT;

extern const Font FONT_3X5;
extern const Font FONT_5X7;

// Row bitmaps for `c` in `font`, or nullptr for a space or anything the font
// cannot draw (which the renderer leaves blank). Lower case folds to upper.
const uint8_t *glyph(const Font &font, char c);

}  // namespace clock_display
}  // namespace esphome
