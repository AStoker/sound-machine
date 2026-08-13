#pragma once

#include "esphome/components/background_sound/background_sound.h"

namespace esphome {
namespace noise_generator {

enum NoiseColor : uint8_t {
  NOISE_WHITE = 0,
  NOISE_PINK = 1,
  NOISE_BROWN = 2,
};

// White/pink/brown noise, generated straight into one mixer source.
//
// The route into the mixer - own a source, start it once, push samples forever,
// carry a short write over to the next pass - is background_sound::BackgroundSound's job and
// is shared with ambience_player. What is left here is the generator itself: the
// PRNG, the two colour filters, and the output high-pass.
class NoiseGenerator : public background_sound::BackgroundSound {
 public:
  void setup() override;
  void dump_config() override;
  // Run after the speaker/mixer components are set up.
  float get_setup_priority() const override { return setup_priority::LATE; }

  // --- Set from YAML ---
  void set_noise_type(NoiseColor color) { this->color_ = color; }
  // Runtime color switch by index (0=white, 1=pink, 2=brown). Safe to call at
  // any time, including while playing: the next chunk picks up the new color,
  // so the change is seamless with no stream restart.
  void set_color_index(uint8_t index) {
    this->color_ = index == 1 ? NOISE_PINK : index == 2 ? NOISE_BROWN : NOISE_WHITE;
  }
  void set_sample_rate(uint32_t sample_rate) { this->sample_rate_ = sample_rate; }
  void set_gain(float gain) { this->gain_ = gain; }
  // Corner frequency of the output high-pass, in Hz. 0 disables it entirely.
  void set_high_pass_freq(float frequency_hz) { this->hp_frequency_hz_ = frequency_hz; }
  // Makeup gain applied to the BROWN branch only, after the high-pass and
  // before soft saturation. High-passing brown removes most of its energy, so
  // without makeup it sounds much quieter than white/pink at the same volume.
  void set_high_pass_makeup(float gain) { this->hp_makeup_gain_ = gain; }

  // --- Runtime control (called from api/sound.yaml) ---
  void start();
  void stop();

 protected:
  bool fill_chunk_(const uint8_t **data, size_t *bytes) override;

  float generate_white_();
  // Two cascaded one-pole high-pass sections (12 dB/octave). See the .cpp for
  // the difference equation.
  float high_pass_(float input_sample);
  // Applies the output high-pass (if enabled) and, for brown noise only,
  // restores the level the filter removed and soft-saturates. Centralizing
  // both steps here (rather than checking hp_enabled_ and color_ separately at
  // each call site) is what guarantees that high_pass_frequency: 0 reproduces
  // the pre-filter output exactly: the makeup gain below only ever applies
  // when the filter actually ran.
  float process_sample_(float sample);

  NoiseColor color_{NOISE_WHITE};
  uint32_t sample_rate_{48000};
  float gain_{0.3f};  // base amplitude / mixing headroom

  // Fast xorshift32 PRNG state (any non-zero seed).
  uint32_t rng_state_{0x2545F491u};

  // Paul Kellet economical pink-noise filter state.
  float pink_b0_{0.0f}, pink_b1_{0.0f}, pink_b2_{0.0f}, pink_b3_{0.0f};
  float pink_b4_{0.0f}, pink_b5_{0.0f}, pink_b6_{0.0f};
  // Brown-noise integrator state.
  float brown_{0.0f};

  // Output high-pass. The Adafruit 3W 4Ohm enclosed speaker produces
  // essentially nothing below ~300-400 Hz, so content down there becomes cone
  // excursion, distortion and amplifier current instead of sound. The filter
  // runs on every color, not just brown: white and pink are barely touched by
  // it (a 160 Hz corner removes well under 1% of white's band), and running
  // it continuously keeps the filter state warm so a color switch mid-playback
  // stays seamless instead of starting from a cold filter and thumping.
  float hp_frequency_hz_{160.0f};
  // Gain re-applied to brown noise after the high-pass, to compensate for the
  // level the filter removes. Only meaningful while the filter is enabled --
  // process_sample_() forces it to a no-op otherwise.
  float hp_makeup_gain_{1.0f};
  // One-pole filter coefficient, derived in setup() from hp_frequency_hz_ and
  // the configured sample rate. Shared by both cascaded stages below.
  float hp_coefficient_{0.0f};
  bool hp_enabled_{false};

  // Per-stage state for the cascaded one-pole high-pass (see high_pass_() in
  // the .cpp for the difference equation). Two stages give a 12 dB/octave
  // slope, needed because brown noise itself falls off at 6 dB/octave -- a
  // single stage would only flatten that slope rather than actually removing
  // low-frequency energy.
  struct HighPassStageState {
    float previous_input{0.0f};
    float previous_output{0.0f};
  };
  HighPassStageState hp_stages_[2];

  static const size_t BUFFER_SAMPLES = 512;  // mono int16 samples per chunk
  int16_t buffer_[BUFFER_SAMPLES];
};

}  // namespace noise_generator
}  // namespace esphome
