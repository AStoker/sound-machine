#include "clock_display.h"
#include "esphome/core/hal.h"
#include "esphome/core/log.h"

namespace esphome {
namespace clock_display {

static const char *const TAG = "clock_display";

// Register map - see the CHIP MODEL note in the header.
static const uint8_t REG_COMMAND = 0xFD;
static const uint8_t BANK_FRAME_0 = 0x00;
static const uint8_t BANK_FUNCTION = 0x0B;
static const uint8_t FUNC_CONFIG = 0x00;
static const uint8_t FUNC_PICTURE_FRAME = 0x01;
static const uint8_t FUNC_SHUTDOWN = 0x0A;
static const uint8_t REG_ENABLE_FIRST = 0x00;  // LED enable, 18 bytes
static const uint8_t REG_ENABLE_LAST = 0x11;
static const uint8_t REG_BLINK_FIRST = 0x12;  // blink enable, 18 bytes
static const uint8_t REG_BLINK_LAST = 0x23;
static const uint8_t REG_PWM_FIRST = 0x24;  // 144 PWM bytes

void ClockDisplay::setup() {
  if (this->bus_ == nullptr || this->addresses_.empty()) {
    ESP_LOGE(TAG, "No I2C bus or no panel addresses configured");
    this->mark_failed();
    return;
  }
  // The panels are brought up on the first paint() rather than here, because the
  // same path has to run again after a rail glitch - see probe_().
  this->set_interval("probe", this->probe_interval_, [this]() { this->probe_(); });
}

void ClockDisplay::dump_config() {
  ESP_LOGCONFIG(TAG, "ClockDisplay matrix:");
  ESP_LOGCONFIG(TAG, "  Panels: %d (%dx%d logical, %d physical columns)", this->panels(),
                PANEL_WIDTH * this->panels(), PANEL_HEIGHT, this->physical_width());
  for (size_t i = 0; i < this->addresses_.size(); i++)
    ESP_LOGCONFIG(TAG, "    Panel %u at 0x%02X", (unsigned) i, this->addresses_[i]);
  ESP_LOGCONFIG(TAG, "  Inter-panel gap: %u dead column(s)", this->panel_gap_);
  ESP_LOGCONFIG(TAG, "  PWM range: %u (darkest) .. %u (brightest)", this->pwm_min_, this->pwm_max_);
  ESP_LOGCONFIG(TAG, "  Config probe every %u ms", (unsigned) this->probe_interval_);
}

// ---- panel configuration --------------------------------------------------

bool ClockDisplay::write_register_(uint8_t address, uint8_t reg, uint8_t value) {
  const uint8_t payload[2] = {reg, value};
  return this->bus_->write(address, payload, 2) == i2c::ERROR_OK;
}

void ClockDisplay::init_panels_() {
  for (uint8_t address : this->addresses_) {
    this->write_register_(address, REG_COMMAND, BANK_FUNCTION);
    this->write_register_(address, FUNC_SHUTDOWN, 0x00);  // shutdown
    delay(10);
    this->write_register_(address, FUNC_SHUTDOWN, 0x01);       // normal operation
    this->write_register_(address, FUNC_CONFIG, 0x00);         // picture mode
    this->write_register_(address, FUNC_PICTURE_FRAME, 0x00);  // display frame 0
    this->write_register_(address, REG_COMMAND, BANK_FRAME_0);
    for (uint8_t reg = REG_ENABLE_FIRST; reg <= REG_ENABLE_LAST; reg++)
      this->write_register_(address, reg, 0xFF);  // enable every LED
    for (uint8_t reg = REG_BLINK_FIRST; reg <= REG_BLINK_LAST; reg++)
      this->write_register_(address, reg, 0x00);  // blink off
  }
  this->configured_ = true;
  // Whatever was on the glass is gone, so the next paint must not be deduped
  // against it.
  this->have_last_ = false;
}

void ClockDisplay::probe_() {
  if (!this->configured_)
    return;  // already due for an init

  // Reads back the first LED-enable register, which init sets to 0xFF. The bank
  // does not need selecting first: init leaves bank 0 current, and a chip that
  // has reset is back on bank 0 anyway - so either the read lands on the register
  // we mean, or the panel needs re-initialising regardless.
  //
  // A BUS ERROR IS NOT A RESET. If the read fails outright the panel is not
  // answering at all and re-initialising cannot help; treating that as "needs
  // init" would thrash 74 register writes per probe against a dead or missing
  // board. Only a panel that answers with the WRONG value is repaired.
  for (size_t panel = 0; panel < this->addresses_.size(); panel++) {
    const uint8_t reg = REG_ENABLE_FIRST;
    uint8_t value = 0;
    if (this->bus_->write_readv(this->addresses_[panel], &reg, 1, &value, 1) != i2c::ERROR_OK)
      continue;
    if (value != 0xFF) {
      ESP_LOGW(TAG, "panel %u lost its configuration (enable reg = 0x%02X); re-initialising",
               (unsigned) panel, value);
      this->configured_ = false;
      return;
    }
  }
}

// ---- resolving a frame ----------------------------------------------------

uint8_t ClockDisplay::pwm_for_level_(uint8_t level) const {
  if (level > 15)
    level = 15;
  // Never reaches 0: the floor is what keeps digits readable in a dark room.
  return this->pwm_min_ + static_cast<uint8_t>((this->pwm_max_ - this->pwm_min_) * level / 15);
}

int ClockDisplay::glyphs_per_panel_(const Font &font) const {
  // A glyph needs `width` columns; the blank column after it may fall on the
  // panel edge, so the last glyph on a panel can end flush at column 15.
  return (PANEL_WIDTH + 1) / font.pitch();
}

int ClockDisplay::slot_x_(int slot, const Font &font) const {
  const int per_panel = this->glyphs_per_panel_(font);
  const int panel = slot / per_panel;
  const int index = slot % per_panel;
  // THE FIRST PANEL IS RIGHT-ALIGNED AND THE REST ARE LEFT-ALIGNED, which is
  // what makes the spacing between EVERY pair of adjacent slots exactly one
  // pitch - including the pair that straddles the seam. The last glyph on panel
  // 0 ends flush at column 15, the first on panel 1 starts at 17, and the dead
  // column 16 in between is the blank column that would have been there anyway.
  const int align = (panel == 0) ? (PANEL_WIDTH + 1 - per_panel * font.pitch()) : 0;
  return panel * this->block_width() + align + index * font.pitch();
}

ClockDisplay::Layout ClockDisplay::plan_(const Frame &frame) const {
  Layout layout{};
  // One font per display size, for every channel: 5x7 on a tiled display, the
  // narrow 3x5 when there is only one panel to work with. Nothing about WHAT is
  // being shown changes the font any more - see "STATIC TEXT NEVER TOUCHES THE
  // SEAM" in the header.
  layout.font = (this->panels() < 2) ? &FONT_3X5 : &FONT_5X7;
  layout.text_width = layout.font->text_width(frame.text.size());
  layout.slots = this->glyphs_per_panel_(*layout.font) * this->panels();
  // Text that fits the gap-free slots sits still; anything longer scrolls rather
  // than being truncated or mangled on the seam.
  layout.scrolling = static_cast<int>(frame.text.size()) > layout.slots;
  return layout;
}

void ClockDisplay::paint(const Frame &frame) {
  if (this->is_failed())
    return;
  if (!this->configured_)
    this->init_panels_();

  const Layout layout = this->plan_(frame);
  const uint8_t pwm = this->pwm_for_level_(frame.level);
  // Only a scrolling frame changes with time. Pinning the phase to 0 otherwise is
  // what lets a still frame dedup at all.
  const int phase =
      layout.scrolling ? static_cast<int>(millis() / (frame.scroll_ms > 0 ? frame.scroll_ms : 1)) : 0;

  if (this->have_last_ && phase == this->last_phase_ && pwm == this->last_pwm_ &&
      frame == this->last_frame_)
    return;
  this->last_frame_ = frame;
  this->last_phase_ = phase;
  this->last_pwm_ = pwm;
  this->have_last_ = true;

  this->clear_();
  if (frame.text.empty()) {
    this->draw_clock_(frame.clock, pwm);
  } else {
    this->draw_text_(frame, layout, phase, pwm);
  }
  this->flush_();
}

// ---- drawing --------------------------------------------------------------

void ClockDisplay::clear_() {
  for (int y = 0; y < PANEL_HEIGHT; y++)
    for (int x = 0; x < PANEL_WIDTH * MAX_PANELS; x++)
      this->framebuffer_[y][x] = 0;
}

void ClockDisplay::set_px_(int physical_x, int y, uint8_t value) {
  if (physical_x < 0 || physical_x >= this->physical_width() || y < 0 || y >= PANEL_HEIGHT)
    return;
  const int panel = physical_x / this->block_width();
  const int within = physical_x - panel * this->block_width();
  if (within >= PANEL_WIDTH)
    return;  // in the dead gap between panels
  this->framebuffer_[y][panel * PANEL_WIDTH + within] = value;
}

void ClockDisplay::draw_glyph_(const Font &font, const uint8_t *rows, int x, int y, uint8_t value) {
  if (rows == nullptr)
    return;  // space / undrawable
  for (int row = 0; row < font.height; row++)
    for (int column = 0; column < font.width; column++)
      if (rows[row] & (1 << (font.width - 1 - column)))
        this->set_px_(x + column, y + row, value);
}

void ClockDisplay::draw_string_(const Font &font, const std::string &text, int x, int y, uint8_t value) {
  for (size_t i = 0; i < text.size(); i++)
    this->draw_glyph_(font, glyph(font, text[i]), x + static_cast<int>(i) * font.pitch(), y, value);
}

void ClockDisplay::draw_text_(const Frame &frame, const Layout &layout, int phase, uint8_t value) {
  const Font &font = *layout.font;
  const int top = (PANEL_HEIGHT - font.height) / 2;

  if (layout.scrolling) {
    // A moving glyph loses its column only while it is crossing the seam, and is
    // legible either side of it, so scrolling text ignores the slots and just
    // runs the full width. Travel is the text's width plus the display's, so it
    // goes off one edge and back on the other.
    const int travel = layout.text_width + this->physical_width();
    const int offset = this->physical_width() - (phase % (travel > 0 ? travel : 1));
    this->draw_string_(font, frame.text, offset, top, value);
    return;
  }

  // Static text goes in the gap-free slots, taking a run of them centred in the
  // slot list - so a full-width string is exactly centred and a shorter one is
  // as close to centred as a seam-avoiding layout allows.
  const int length = static_cast<int>(frame.text.size());
  const int first_slot = (layout.slots - length) / 2;
  for (int i = 0; i < length; i++)
    this->draw_glyph_(font, glyph(font, frame.text[i]), this->slot_x_(first_slot + i, font), top, value);
}

void ClockDisplay::draw_clock_(const std::string &clock, uint8_t value) {
  // A dash in every slot is how an unreadable RTC looks - clearly "no time"
  // rather than a dead display. The length check is belt and braces: the caller
  // always sends 4 characters or none.
  const bool valid = clock.size() >= 4;
  const std::string digits = valid ? clock : std::string("----");

  if (this->panels() >= 2) {
    // HH on the left panel, MM on the right, colon at the seam. MM is pulled
    // toward the seam by the gap so the colon sits symmetric across it.
    const Font &font = FONT_5X7;
    const int top = 1;  // 7-tall band, rows 1..7
    const int slot_x[4] = {2, 8, PANEL_WIDTH + this->panel_gap_ + 1, PANEL_WIDTH + this->panel_gap_ + 7};
    for (int i = 0; i < 4; i++)
      if (digits[i] != '_')
        this->draw_glyph_(font, glyph(font, digits[i]), slot_x[i], top, value);
    if (valid) {
      this->set_px_(PANEL_WIDTH - 1, top + 2, value);
      this->set_px_(PANEL_WIDTH - 1, top + 4, value);
    }
    return;
  }

  // Single panel: compact font, no seam to worry about.
  const Font &font = FONT_3X5;
  const int top = 2;  // 5-tall band, rows 2..6
  const int slot_x[4] = {0, 4, 9, 13};
  for (int i = 0; i < 4; i++)
    if (digits[i] != '_')
      this->draw_glyph_(font, glyph(font, digits[i]), slot_x[i], top, value);
  if (valid) {
    this->set_px_(7, top + 1, value);
    this->set_px_(7, top + 3, value);
  }
}

void ClockDisplay::flush_() {
  // Auto-incrementing 16-byte bursts (9 per panel): [start-reg, b0, ... b15].
  for (int panel = 0; panel < this->panels(); panel++) {
    for (int first = 0; first < LEDS_PER_PANEL; first += PANEL_WIDTH) {
      uint8_t burst[1 + PANEL_WIDTH];
      burst[0] = REG_PWM_FIRST + first;
      for (int i = 0; i < PANEL_WIDTH; i++) {
        const int led = first + i;  // LED number = x + y*16
        burst[1 + i] = this->framebuffer_[led / PANEL_WIDTH][panel * PANEL_WIDTH + (led % PANEL_WIDTH)];
      }
      this->bus_->write(this->addresses_[panel], burst, sizeof(burst));
    }
  }
}

}  // namespace clock_display
}  // namespace esphome
