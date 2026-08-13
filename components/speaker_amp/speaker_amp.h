#pragma once

#include "esphome/core/component.h"
#include "esphome/components/i2c/i2c.h"

namespace esphome {
namespace speaker_amp {

// TPA2016D2 register map (TI SLOS655). The part number lives here and in the
// .cpp, and nowhere else in the build - callers ask for "the speaker amp".
static const uint8_t REG_IC_FUNCTION = 0x01;
static const uint8_t REG_AGC_ATTACK = 0x02;
static const uint8_t REG_AGC_RELEASE = 0x03;
static const uint8_t REG_AGC_HOLD = 0x04;
static const uint8_t REG_FIXED_GAIN = 0x05;
static const uint8_t REG_AGC_LIMITER = 0x06;
static const uint8_t REG_AGC_CONTROL = 0x07;

// Register 1 bit fields. Bits 4:2 are read-only fault/thermal flags.
static const uint8_t IC_FUNCTION_SPK_EN_R = 0x80;
static const uint8_t IC_FUNCTION_SPK_EN_L = 0x40;
static const uint8_t IC_FUNCTION_SHUTDOWN = 0x20;
static const uint8_t IC_FUNCTION_FAULT_R = 0x10;
static const uint8_t IC_FUNCTION_FAULT_L = 0x08;
static const uint8_t IC_FUNCTION_THERMAL = 0x04;
static const uint8_t IC_FUNCTION_NOISE_GATE = 0x01;

// Register 6 bit 7 DISABLES the output limiter when set.
static const uint8_t AGC_LIMITER_DISABLE = 0x80;

enum Compression : uint8_t {
  COMPRESSION_1_1 = 0,  // AGC effectively off
  COMPRESSION_2_1 = 1,
  COMPRESSION_4_1 = 2,
  COMPRESSION_8_1 = 3,
};

// This device is an analog amplifier with a configuration-only I2C interface.
// It is written once at boot and then left alone, deliberately: the XVF3800
// derives its acoustic echo reference from what ESPHome hands the DAC, so any
// time-varying gain downstream of that point makes the echo path non-linear,
// and non-linear paths cannot be cancelled. That is why the AGC is turned off
// rather than merely tuned, and why all volume control stays in software.
class SpeakerAmp : public Component, public i2c::I2CDevice {
 public:
  void setup() override;
  void dump_config() override;
  // Runs after the I2C bus (setup_priority::BUS) and before the audio stack.
  float get_setup_priority() const override { return setup_priority::HARDWARE; }

  // --- Set from YAML ---
  void set_compression(Compression compression) { this->compression_ = compression; }
  void set_gain_db(int8_t gain_db) { this->gain_db_ = gain_db; }
  void set_max_gain_bits(uint8_t bits) { this->max_gain_bits_ = bits; }
  void set_limiter_enabled(bool enabled) { this->limiter_enabled_ = enabled; }
  void set_limiter_bits(uint8_t bits) { this->limiter_bits_ = bits; }
  void set_noise_gate(bool enabled) { this->noise_gate_ = enabled; }
  void set_left_enabled(bool enabled) { this->left_enabled_ = enabled; }
  void set_right_enabled(bool enabled) { this->right_enabled_ = enabled; }

  // Rewrite the whole configuration. Public so a lambda can re-run it if the
  // amp ever loses its registers (it has no NVM -- a power glitch on the 5V
  // rail returns it to factory defaults, which means AGC back ON).
  bool apply();
  bool is_configured() const { return this->configured_; }

  // Read the live fault flags. Useful on the bench; both faults latch until
  // the register is read.
  bool read_faults(bool &fault_left, bool &fault_right, bool &thermal);

 protected:
  // verify_mask selects which bits are compared on readback; pass 0 to skip
  // verification entirely (register 1 carries read-only flags that will never
  // match what we wrote).
  bool write_register_(uint8_t reg, uint8_t value, uint8_t verify_mask);

  Compression compression_{COMPRESSION_1_1};
  int8_t gain_db_{6};
  uint8_t max_gain_bits_{12};  // (18 + bits) dB, only meaningful when AGC is on
  bool limiter_enabled_{true};
  uint8_t limiter_bits_{31};  // -6.5 + 0.5 * bits, in dBV
  bool noise_gate_{false};
  bool left_enabled_{true};
  bool right_enabled_{true};
  bool configured_{false};
};

}  // namespace speaker_amp
}  // namespace esphome
