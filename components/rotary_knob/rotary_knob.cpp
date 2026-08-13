#include "rotary_knob.h"
#include "esphome/core/hal.h"
#include "esphome/core/log.h"
#include "esphome/core/helpers.h"
#include <cstdio>

namespace esphome {
namespace rotary_knob {

static const char *const TAG = "rotary_knob";

#define SEESAW_HW_ID_SAMD09 0x55
#define SEESAW_HW_ID_TINY806 0x84
#define SEESAW_HW_ID_TINY807 0x85
#define SEESAW_HW_ID_TINY816 0x86
#define SEESAW_HW_ID_TINY817 0x87
#define SEESAW_HW_ID_TINY1616 0x88
#define SEESAW_HW_ID_TINY1617 0x89

float KnobHub::get_setup_priority() const { return setup_priority::IO; }

static const char *cpuid_to_string(uint8_t id) {
  switch (id) {
   case SEESAW_HW_ID_SAMD09: return "SAMD09";
   case SEESAW_HW_ID_TINY806: return "ATtiny806";
   case SEESAW_HW_ID_TINY807: return "ATtiny807";
   case SEESAW_HW_ID_TINY816: return "ATtiny816";
   case SEESAW_HW_ID_TINY817: return "ATtiny817";
   case SEESAW_HW_ID_TINY1616: return "ATtiny1616";
   case SEESAW_HW_ID_TINY1617: return "ATtiny1617";
   default: return nullptr;
  }
}

void KnobHub::setup() {
  ESP_LOGCONFIG(TAG, "Setting up KnobHub...");
  uint8_t c = 0;
  this->readbuf(SEESAW_STATUS, SEESAW_STATUS_HW_ID, &c, 1);
  this->cpuid_ = c;
  uint8_t buf[4];
  this->readbuf(SEESAW_STATUS, SEESAW_STATUS_VERSION, buf, 4);
  this->version_ = (buf[0] << 24) | (buf[1] << 16) | (buf[2] << 8) | buf[3];
  this->readbuf(SEESAW_STATUS, SEESAW_STATUS_OPTIONS, buf, 4);
  this->options_ = (buf[0] << 24) | (buf[1] << 16) | (buf[2] << 8) | buf[3];
}

void KnobHub::dump_config() {
  ESP_LOGCONFIG(TAG, "KnobHub module:");
  LOG_I2C_DEVICE(this);
  const char *cpu = cpuid_to_string(this->cpuid_);
  if (cpu != nullptr) {
    ESP_LOGCONFIG(TAG, "  CPU: %s", cpu);
  } else {
    ESP_LOGCONFIG(TAG, "  CPU: unknown (%02x)", this->cpuid_);
  }
  uint32_t v = this->version_;
  ESP_LOGCONFIG(TAG, "  Version: %d-%02d-%02d %u", (int) (v & 0x3f), (int) ((v >> 7) & 0xf), (int) ((v >> 11) & 0x1f),
                (unsigned) (v >> 16));
  // The Options word is a bitmask of the modules this seesaw firmware carries
  // (SEESAW_GPIO, SEESAW_NEOPIXEL, SEESAW_ENCODER...). It is dumped raw rather
  // than decoded: this build knows exactly which board it has, and the hex is
  // enough to compare against Adafruit's table if that ever stops being true.
}

void KnobHub::enable_encoder(uint8_t number) {
  this->write8(SEESAW_ENCODER, SEESAW_ENCODER_INTENSET + number, 0x01);
}

int32_t KnobHub::get_encoder_position(uint8_t number) {
  uint8_t buf[4];
  if (this->readbuf(SEESAW_ENCODER, SEESAW_ENCODER_POSITION + number, buf, 4) != i2c::ERROR_OK)
    return 0;
  int32_t value = (buf[0] << 24) + (buf[1] << 16) + (buf[2] << 8) + buf[3];
  return -value;  // make clockwise positive
}

int16_t KnobHub::get_touch_value(uint8_t channel) {
  uint8_t buf[2];
  if (this->readbuf(SEESAW_TOUCH, SEESAW_TOUCH_CHANNEL_OFFSET + channel, buf, 2) != i2c::ERROR_OK)
    return -1;
  return (buf[0] << 8) | buf[1];
}

float KnobHub::get_temperature() {
  uint8_t buf[4];
  if (this->readbuf(SEESAW_STATUS, SEESAW_STATUS_TEMP, buf, 4) != i2c::ERROR_OK)
    return 0;
  int32_t value = (buf[0] << 24) + (buf[1] << 16) + (buf[2] << 8) + buf[3];
  return float(value) / 0x10000;
}

void KnobHub::set_pinmode(uint8_t pin, uint8_t mode) {
  uint32_t pins = 1 << pin;
  switch (mode) {
    case gpio::FLAG_OUTPUT:
    this->write32(SEESAW_GPIO, SEESAW_GPIO_DIRSET_BULK, pins);
    break;
   case gpio::FLAG_INPUT:
    this->write32(SEESAW_GPIO, SEESAW_GPIO_DIRCLR_BULK, pins);
    break;
   case gpio::FLAG_PULLUP:
    this->write32(SEESAW_GPIO, SEESAW_GPIO_DIRCLR_BULK, pins);
    this->write32(SEESAW_GPIO, SEESAW_GPIO_PULLENSET, pins);
    this->write32(SEESAW_GPIO, SEESAW_GPIO_BULK_SET, pins);
    break;
   case gpio::FLAG_PULLDOWN:
    this->write32(SEESAW_GPIO, SEESAW_GPIO_DIRCLR_BULK, pins);
    this->write32(SEESAW_GPIO, SEESAW_GPIO_PULLENSET, pins);
    this->write32(SEESAW_GPIO, SEESAW_GPIO_BULK_CLR, pins);
    break;
  }
}

void KnobHub::set_gpio_interrupt(uint32_t pin, bool enabled) {
  uint32_t pins = 1 << pin;
  if (enabled)
    this->write32(SEESAW_GPIO, SEESAW_GPIO_INTENSET, pins);
  else
    this->write32(SEESAW_GPIO, SEESAW_GPIO_INTENCLR, pins);
}

uint16_t KnobHub::analog_read(uint8_t pin) {
  uint8_t buf[2];
  this->readbuf(SEESAW_ADC, SEESAW_ADC_CHANNEL_OFFSET + pin, buf, 2);
  return (buf[0] << 8) + buf[1];
}

bool KnobHub::digital_read(uint8_t pin) {
  uint32_t pins = 1 << pin;
  uint8_t buf[4];
  this->readbuf(SEESAW_GPIO, SEESAW_GPIO_BULK, buf, 4);
  uint32_t ret = (buf[0] << 24) + (buf[1] << 16) + (buf[2] << 8) + buf[3];
  return ret & pins;
}

void KnobHub::digital_write(uint8_t pin, bool state) {
  // BULK_SET/BULK_CLR take a BITMASK, not a pin number. Upstream passed `pin`
  // here (while computing `pins` and discarding it), so writing pin 24 set
  // seesaw pins 3 and 4 instead. Nothing in this build calls digital_write, so
  // it was latent - but it is a trap for the next person who does.
  uint32_t pins = 1 << pin;
  if (state)
    this->write32(SEESAW_GPIO, SEESAW_GPIO_BULK_SET, pins);
  else
    this->write32(SEESAW_GPIO, SEESAW_GPIO_BULK_CLR, pins);
}

void KnobHub::setup_neopixel(int pin) {
  this->write8(SEESAW_NEOPIXEL, SEESAW_NEOPIXEL_SPEED, 1);
  this->write16(SEESAW_NEOPIXEL, SEESAW_NEOPIXEL_BUF_LENGTH, 3);
  this->write8(SEESAW_NEOPIXEL, SEESAW_NEOPIXEL_PIN, pin);
}

void KnobHub::color_neopixel(uint8_t r, uint8_t g, uint8_t b) {
  uint8_t buf[7] = {SEESAW_NEOPIXEL, SEESAW_NEOPIXEL_BUF, 0, 0, g, r, b};
  this->write(buf, 7);
  buf[1] = SEESAW_NEOPIXEL_SHOW;
  this->write(buf, 2);
}

i2c::ErrorCode KnobHub::write8(ChipModule mod, uint8_t reg, uint8_t value) {
  uint8_t buf[3] = {mod, reg, value};
  return this->write(buf, 3);
}

i2c::ErrorCode KnobHub::write16(ChipModule mod, uint8_t reg, uint16_t value) {
  uint8_t buf[4] = {mod, reg, (uint8_t)(value >> 8), (uint8_t)value};
  return this->write(buf, 4);
}

i2c::ErrorCode KnobHub::write32(ChipModule mod, uint8_t reg, uint32_t value) {
  uint8_t buf[6] = {mod, reg, (uint8_t)(value >> 24), (uint8_t)(value >> 16),
                    (uint8_t)(value >> 8), (uint8_t)value};
  return this->write(buf, 6);
}

i2c::ErrorCode KnobHub::readbuf(ChipModule mod, uint8_t reg, uint8_t *buf, uint8_t len) {
  uint8_t sendbuf[2] = {mod, reg};
  i2c::ErrorCode err = this->write(sendbuf, 2);
  if (err != i2c::ERROR_OK)
    return err;
  return this->read(buf, len);
}

void KnobGPIOPin::setup() { pin_mode(flags_); }

void KnobGPIOPin::pin_mode(gpio::Flags flags) { this->parent_->set_pinmode(this->pin_, flags); }

bool KnobGPIOPin::digital_read() {
  return this->parent_->digital_read(this->pin_) != this->inverted_;
}

void KnobGPIOPin::digital_write(bool value) {
  this->parent_->digital_write(this->pin_, value != this->inverted_);
}

size_t KnobGPIOPin::dump_summary(char *buffer, size_t len) const {
  return snprintf(buffer, len, "%u via SeeSaw", this->pin_);
}

}  // namespace rotary_knob
}  // namespace esphome
