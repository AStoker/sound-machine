#pragma once

#include "esphome/core/component.h"
#include "esphome/components/i2c/i2c.h"

#include "fonts.h"

#include <string>
#include <vector>

namespace esphome {
namespace clock_display {

// EVERYTHING THE DRIVER IS TOLD, in one value. Whoever decides what to show
// fills this in and hands it over; the driver makes no decisions of its own.
//
// It is a struct rather than a handful of globals so that the contract is a type
// a compiler checks rather than a paragraph two files have to keep agreeing on,
// and so that "has anything changed?" is one comparison instead of a hash over a
// string built for the purpose.
//
// THERE IS NO "KIND" OF TEXT HERE, deliberately. Every channel - a code, a device
// announcement, a sticky alert, a message from Home Assistant - gets the same
// font and the same layout, so nothing on this display looks like it came from a
// different machine. All the driver needs to know is the characters.
struct Frame {
  // Text to render. EMPTY means render the clock.
  std::string text;
  // Exactly 4 characters, '_' for a blank slot, e.g. "_930". EMPTY means the
  // time is not readable and the driver should say so.
  std::string clock;
  // 0..15 brightness from the ambient auto-dim, already clamped by its owner.
  uint8_t level{9};
  // Milliseconds per pixel for text too wide for its scope, already bounded by
  // its owner.
  uint16_t scroll_ms{250};

  bool operator==(const Frame &other) const {
    return this->text == other.text && this->clock == other.clock && this->level == other.level &&
           this->scroll_ms == other.scroll_ms;
  }
  bool operator!=(const Frame &other) const { return !(*this == other); }
};

// ---------------------------------------------------------------------------
// THE CLOCK DISPLAY: 16x9 LED matrix panels tiled into one text surface.
//
// The panels are driven by IS31FL3731 charlieplex chips, which ESPHome has no
// component for, so this talks to them over the shared I2C bus with raw register
// writes. That part number appears nowhere outside this file and its .cpp - the
// rest of the build asks for "the clock display".
//
// THIS COMPONENT MAKES NO DECISIONS ABOUT WHAT TO SHOW - it renders the Frame it
// is handed. What to show is packages/api/display.yaml's job.
//
// TILING. N panels are tiled side by side into one logical framebuffer
// 16*N wide by 9 tall. Panel p owns logical columns [16p .. 16p+15] and is
// pushed to its own I2C address. With one address configured the second is never
// touched, so an unwired second board causes no I2C errors.
//
// THE INTER-PANEL GAP. Two panels butted together are NOT seamless: there is a
// physical dead column between the last column of one and the first of the next.
// So content is laid out in PHYSICAL columns (which include that gap) and mapped
// back to logical columns at draw time - set_px_() drops any pixel landing in the
// gap.
//
// STATIC TEXT NEVER TOUCHES THE SEAM, and it does not have to be shoved into one
// panel to manage it. A glyph sitting STILL on the dead column permanently loses
// that column - an 'O' reduced to two bars with dotted caps - so static text is
// placed in SLOTS: each panel holds `(16 + 1) / pitch` of them, the first panel's
// are right-aligned and the rest are left-aligned, and the result is that the
// spacing between every pair of adjacent slots is exactly one pitch INCLUDING the
// pair either side of the seam. The dead column simply plays the part of the
// blank column that would have separated those two glyphs anyway.
//
// So on a dual panel at 5x7 there are 4 slots at physical columns 5, 11, 17, 23 -
// evenly spaced, none of them crossing column 16, and a 4-character string using
// all of them lands exactly centred. A shorter string takes a centred run of
// slots. THAT IS WHY THE STATIC BUDGET IS 4 CHARACTERS: not a per-channel rule,
// just how many gap-free slots a 32-column display has.
//
// THE ONE COMPROMISE: an ODD-length string cannot be both centred and seam-free,
// because the slots are on a fixed pitch and there is an even number of them. Two
// and four characters land dead centre; one and three sit 3 columns left of it.
// That is the right way round to be wrong - three columns of offset on a
// persistent warning is barely noticeable, where a permanently broken glyph is
// the first thing you see.
//
// TEXT THAT DOES NOT FIT SCROLLS THE FULL WIDTH and ignores the slots. The seam
// stops mattering once the text is moving: each glyph loses its column only while
// crossing the gap, and is legible either side of it. A stationary glyph is
// mangled for as long as it is up; a moving one is not.
//
// (This replaced a "scope" flag that gave persistent text a smaller font in the
// right-hand panel to keep it off the seam, while short-lived codes were centred
// across the whole width and quietly took the damage instead. It made a
// low-battery warning look like it came from a different device, and the codes
// were never actually safe. One layout that is always seam-free removed the flag,
// the second font choice, and the bug.)
//
// SELF-HEALING. The chip has no NVM. A glitch on the shared 5V rail returns it to
// its power-on state: shut down, with every LED disabled. The PWM a repaint sends
// would then land on a chip that draws none of it, and the display would stay
// dark for as long as the device stayed up. So a probe reads one enable register
// back on an interval and re-runs the init if a panel has forgotten it.
//
// CHIP MODEL - IS31FL3731 (from Adafruit's Adafruit_IS31FL3731 base 16x9 class):
//   pixel (x,y) -> LED number = x + y*16   (x: 0..15 cols, y: 0..8 rows)
//   PWM byte for LED n        at register 0x24 + n   (144 LEDs, 0x24..0xB3)
//   LED on/off enable         registers 0x00..0x11   (18 bytes, 8 LEDs each)
//   blink enable              registers 0x12..0x23   (held off)
//   command register 0xFD selects the bank: 0x00 = frame 0 (enable + PWM),
//     0x0B = function register (config / picture-frame / shutdown).
//   Function-bank registers: 0x00 config (0x00 = picture mode),
//     0x01 picture-display-frame, 0x0A shutdown (0 = off, 1 = normal).
// ---------------------------------------------------------------------------
class ClockDisplay : public Component {
 public:
  static constexpr int PANEL_WIDTH = 16;
  static constexpr int PANEL_HEIGHT = 9;
  static constexpr int MAX_PANELS = 2;
  static constexpr int LEDS_PER_PANEL = PANEL_WIDTH * PANEL_HEIGHT;  // 144

  void setup() override;
  void dump_config() override;
  float get_setup_priority() const override { return setup_priority::HARDWARE; }

  // --- Set from YAML ---
  void set_i2c_bus(i2c::I2CBus *bus) { this->bus_ = bus; }
  void add_address(uint8_t address) { this->addresses_.push_back(address); }
  void set_panel_gap(uint8_t gap) { this->panel_gap_ = gap; }
  void set_pwm_range(uint8_t minimum, uint8_t maximum) {
    this->pwm_min_ = minimum;
    this->pwm_max_ = maximum;
  }
  void set_probe_interval(uint32_t milliseconds) { this->probe_interval_ = milliseconds; }

  // Draw `frame`, or return without touching I2C if it resolves to exactly what
  // is already on the panels.
  //
  // SELF-THROTTLING IS THIS COMPONENT'S JOB, not its caller's. api/display.yaml
  // ticks several times a second and calls this every time; a full repaint is
  // ~300 bytes on a 100 kHz bus (~30 ms of bus time) on a bus this build already
  // had to slow down for the XVF3800, so an unchanged frame must cost nothing.
  void paint(const Frame &frame);

 protected:
  // What a frame's text needs in order to be drawn: which font, how wide it
  // comes out, how many gap-free slots there are to put it in, and whether it is
  // too long for them and so has to move.
  struct Layout {
    const Font *font;
    int text_width;
    int slots;
    bool scrolling;
  };

  int panels() const { return static_cast<int>(this->addresses_.size()); }
  // Physical columns per panel including the dead gap after it.
  int block_width() const { return PANEL_WIDTH + this->panel_gap_; }
  // Total physical width, gaps included; the coordinate space text is laid out in.
  int physical_width() const {
    return PANEL_WIDTH * this->panels() + this->panel_gap_ * (this->panels() - 1);
  }

  Layout plan_(const Frame &frame) const;
  uint8_t pwm_for_level_(uint8_t level) const;
  // How many glyphs of `font` fit on one panel without any of them reaching the
  // dead column at its edge.
  int glyphs_per_panel_(const Font &font) const;
  // Physical column of gap-free slot `slot`, counted left to right across every
  // panel. See "STATIC TEXT NEVER TOUCHES THE SEAM" above.
  int slot_x_(int slot, const Font &font) const;

  bool write_register_(uint8_t address, uint8_t reg, uint8_t value);
  void init_panels_();
  void probe_();

  void clear_();
  // Place a pixel by PHYSICAL column, dropping anything off the display or in an
  // inter-panel gap. Every draw helper works in physical columns, which is also
  // what lets text scroll cleanly off both edges.
  void set_px_(int physical_x, int y, uint8_t value);
  void draw_glyph_(const Font &font, const uint8_t *rows, int x, int y, uint8_t value);
  void draw_string_(const Font &font, const std::string &text, int x, int y, uint8_t value);
  void draw_text_(const Frame &frame, const Layout &layout, int phase, uint8_t value);
  void draw_clock_(const std::string &clock, uint8_t value);
  void flush_();

  i2c::I2CBus *bus_{nullptr};
  std::vector<uint8_t> addresses_;
  uint8_t panel_gap_{1};
  uint8_t pwm_min_{3};
  uint8_t pwm_max_{40};
  uint32_t probe_interval_{10000};

  // Panels are configured once, not per frame - a repaint only pushes PWM.
  bool configured_{false};

  // What was last drawn, for the dedup in paint(). The scroll phase and the
  // resolved PWM are kept beside the frame because they are what the frame turns
  // into: two frames that differ only in a level that maps to the same PWM look
  // identical on the glass.
  Frame last_frame_;
  int last_phase_{0};
  uint8_t last_pwm_{0};
  bool have_last_{false};

  uint8_t framebuffer_[PANEL_HEIGHT][PANEL_WIDTH * MAX_PANELS];
};

}  // namespace clock_display
}  // namespace esphome
