#pragma once

#include "esphome/core/component.h"
#include "esphome/components/audio/audio.h"
#include "esphome/components/speaker/speaker.h"

namespace esphome {
namespace noise_source {

enum NoiseColor : uint8_t {
  NOISE_WHITE = 0,
  NOISE_PINK = 1,
  NOISE_BROWN = 2,
};

class NoiseSource : public Component {
 public:
  void setup() override;
  void loop() override;
  void dump_config() override;
  // Run after the speaker/mixer components are set up.
  float get_setup_priority() const override { return setup_priority::LATE; }

  // --- Set from YAML ---
  void set_speaker(speaker::Speaker *spk) { this->speaker_ = spk; }
  void set_noise_type(NoiseColor color) { this->color_ = color; }
  // Runtime color switch by index (0=white, 1=pink, 2=brown). Safe to call at
  // any time, including while playing: loop() picks up the new color on its
  // next buffer, so the change is seamless with no stream restart.
  void set_color_index(uint8_t index) {
    this->color_ = index == 1 ? NOISE_PINK : index == 2 ? NOISE_BROWN : NOISE_WHITE;
  }
  void set_sample_rate(uint32_t sample_rate) { this->sample_rate_ = sample_rate; }
  void set_gain(float gain) { this->gain_ = gain; }
  void set_fade_ms(uint32_t fade_ms) { this->fade_ms_ = fade_ms; }

  // --- Runtime control (call from lambdas / the switch) ---
  void start();
  void stop();
  bool is_active() const { return this->active_; }
  // Optional independent volume multiplier, 0.0-1.0. Leave at 1.0 if you are
  // controlling loudness with the media player's master volume instead.
  void set_volume(float volume);

 protected:
  void fill_buffer_();
  float generate_white_();

  speaker::Speaker *speaker_{nullptr};
  NoiseColor color_{NOISE_WHITE};
  uint32_t sample_rate_{48000};
  float gain_{0.3f};    // base amplitude / mixing headroom
  float volume_{1.0f};  // runtime multiplier
  bool active_{false};

  // Fade-in envelope: ramps 0.0 -> 1.0 over fade_ms_ when playback starts.
  uint32_t fade_ms_{3000};
  uint32_t fade_start_ms_{0};
  float envelope_{1.0f};
  bool fading_{false};

  // Fast xorshift32 PRNG state (any non-zero seed).
  uint32_t rng_state_{0x2545F491u};

  // Paul Kellet economical pink-noise filter state.
  float pink_b0_{0.0f}, pink_b1_{0.0f}, pink_b2_{0.0f}, pink_b3_{0.0f};
  float pink_b4_{0.0f}, pink_b5_{0.0f}, pink_b6_{0.0f};
  // Brown-noise integrator state.
  float brown_{0.0f};

  static const size_t BUFFER_SAMPLES = 512;  // mono int16 samples per chunk
  int16_t buffer_[BUFFER_SAMPLES];
  // Bytes of buffer_ generated but not yet accepted by the speaker, held across
  // loop() calls. Dropping unsent samples would let the generator run ahead of
  // playback and jump the correlated brown-noise integrator, causing pops.
  size_t pending_bytes_{0};
  size_t pending_offset_{0};
};

}  // namespace noise_source
}  // namespace esphome