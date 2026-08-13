#include "speaker_amp.h"
#include "esphome/core/log.h"

namespace esphome {
namespace speaker_amp {

static const char *const TAG = "speaker_amp";

void SpeakerAmp::setup() {
  // The amp shares the 5V rail with the Flex, the strip and the ESP itself, so
  // it may still be settling when our setup() runs. Defer the register writes
  // briefly rather than racing its power-on reset.
  this->set_timeout(100, [this]() {
    if (!this->apply()) {
      ESP_LOGE(TAG, "Configuration failed - amp is running on factory defaults (AGC ON)");
      this->mark_failed();
    }
  });
}

bool SpeakerAmp::apply() {
  // ---- ORDER MATTERS. Compression first, gain second. ----
  // With the AGC engaged, the fixed-gain field spans -28..+30 dB. The moment
  // compression is set to 1:1 the hardware restricts it to 0..30 dB. Write the
  // gain first and then disable compression and you are left with whatever
  // survives that clamp, which for any negative value is silence. This is the
  // failure people hit on the TI forum after "disabling the AGC".
  const uint8_t agc = static_cast<uint8_t>((this->max_gain_bits_ << 4) |
                                           (static_cast<uint8_t>(this->compression_) & 0x03));
  if (!this->write_register_(REG_AGC_CONTROL, agc, 0xF3))
    return false;

  int8_t gain = this->gain_db_;
  if (this->compression_ == COMPRESSION_1_1 && gain < 0) {
    ESP_LOGW(TAG, "gain_db %d is negative but compression is 1:1; hardware floor is 0 dB", gain);
    gain = 0;
  }
  if (!this->write_register_(REG_FIXED_GAIN, static_cast<uint8_t>(gain) & 0x3F, 0x3F))
    return false;

  // Output limiter stays ENABLED, but parked high enough that ordinary
  // playback never reaches it. It is a fault stop for a runaway signal, not a
  // dynamics processor -- a limiter that actually engages would reintroduce
  // exactly the time-varying gain the AGC was turned off to avoid.
  uint8_t limiter = this->limiter_bits_ & 0x1F;
  if (!this->limiter_enabled_)
    limiter |= AGC_LIMITER_DISABLE;
  if (!this->write_register_(REG_AGC_LIMITER, limiter, 0x9F))
    return false;

  // Register 1 last: speakers on, software shutdown cleared, noise gate as
  // configured. No verify mask -- bits 4:2 are read-only fault flags.
  uint8_t ic_function = 0;
  if (this->right_enabled_)
    ic_function |= IC_FUNCTION_SPK_EN_R;
  if (this->left_enabled_)
    ic_function |= IC_FUNCTION_SPK_EN_L;
  if (this->noise_gate_)
    ic_function |= IC_FUNCTION_NOISE_GATE;
  if (!this->write_register_(REG_IC_FUNCTION, ic_function, 0x00))
    return false;

  this->configured_ = true;
  ESP_LOGI(TAG, "Configured: compression %s, fixed gain %d dB, limiter %s",
           this->compression_ == COMPRESSION_1_1 ? "1:1 (AGC off)" : "ON", gain,
           this->limiter_enabled_ ? "enabled" : "disabled");
  return true;
}

bool SpeakerAmp::write_register_(uint8_t reg, uint8_t value, uint8_t verify_mask) {
  if (!this->write_byte(reg, value)) {
    ESP_LOGE(TAG, "I2C write to register 0x%02X failed", reg);
    return false;
  }
  if (verify_mask == 0)
    return true;

  uint8_t readback = 0;
  if (!this->read_byte(reg, &readback)) {
    // The write itself was ACKed; a failed readback is worth a warning but not
    // worth failing the component over.
    ESP_LOGW(TAG, "Could not read back register 0x%02X", reg);
    return true;
  }
  if ((readback & verify_mask) != (value & verify_mask)) {
    ESP_LOGE(TAG, "Register 0x%02X: wrote 0x%02X, read 0x%02X (mask 0x%02X)", reg, value, readback,
             verify_mask);
    return false;
  }
  return true;
}

bool SpeakerAmp::read_faults(bool &fault_left, bool &fault_right, bool &thermal) {
  uint8_t value = 0;
  if (!this->read_byte(REG_IC_FUNCTION, &value))
    return false;
  fault_left = (value & IC_FUNCTION_FAULT_L) != 0;
  fault_right = (value & IC_FUNCTION_FAULT_R) != 0;
  thermal = (value & IC_FUNCTION_THERMAL) != 0;
  return true;
}

void SpeakerAmp::dump_config() {
  ESP_LOGCONFIG(TAG, "Speaker amplifier (TPA2016D2):");
  LOG_I2C_DEVICE(this);
  if (this->is_failed()) {
    ESP_LOGE(TAG, "  Communication failed - check the 0x58 wiring and that the amp has 5V");
    return;
  }

  const char *compression = this->compression_ == COMPRESSION_1_1   ? "1:1 (AGC off)"
                            : this->compression_ == COMPRESSION_2_1 ? "2:1"
                            : this->compression_ == COMPRESSION_4_1 ? "4:1"
                                                                    : "8:1";
  ESP_LOGCONFIG(TAG, "  Compression: %s", compression);
  ESP_LOGCONFIG(TAG, "  Fixed gain: %d dB", this->gain_db_);
  if (this->limiter_enabled_) {
    ESP_LOGCONFIG(TAG, "  Output limiter: %.1f dBV", -6.5f + 0.5f * this->limiter_bits_);
  } else {
    ESP_LOGCONFIG(TAG, "  Output limiter: disabled");
  }
  ESP_LOGCONFIG(TAG, "  Noise gate: %s", ONOFF(this->noise_gate_));
  ESP_LOGCONFIG(TAG, "  Channels: %s%s", this->left_enabled_ ? "L" : "-",
                this->right_enabled_ ? "R" : "-");

  // Dump the live register contents; cheapest possible sanity check that the
  // amp is actually the chip at this address and holding our settings.
  uint8_t values[7] = {0};
  bool ok = true;
  for (uint8_t reg = REG_IC_FUNCTION; reg <= REG_AGC_CONTROL && ok; reg++)
    ok = this->read_byte(reg, &values[reg - REG_IC_FUNCTION]);
  if (ok) {
    ESP_LOGCONFIG(TAG, "  Registers 0x01-0x07: %02X %02X %02X %02X %02X %02X %02X", values[0],
                  values[1], values[2], values[3], values[4], values[5], values[6]);
    if (values[0] & (IC_FUNCTION_FAULT_L | IC_FUNCTION_FAULT_R))
      ESP_LOGW(TAG, "  Output fault latched - check for a shorted or commoned speaker lead");
    if (values[0] & IC_FUNCTION_THERMAL)
      ESP_LOGW(TAG, "  Thermal flag set");
  }
}

}  // namespace speaker_amp
}  // namespace esphome
