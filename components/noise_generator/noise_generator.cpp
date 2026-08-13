#include "noise_generator.h"
#include "esphome/core/log.h"
#include <cmath>

namespace esphome {
namespace noise_generator {

static const char *const TAG = "noise_generator";
static const float TWO_PI_F = 6.28318530718f;

void NoiseGenerator::setup() {
  if (!this->require_speaker_())
    return;

  // One-pole high-pass coefficient: coefficient = sample_rate / (sample_rate +
  // 2*pi*corner_frequency). Two sections are cascaded in high_pass_() for a
  // 12 dB/octave slope, which actually removes low-frequency energy from brown
  // noise rather than merely flattening it (brown falls at 6 dB/octave, so a
  // single pole would only cancel the slope).
  if (this->hp_frequency_hz_ > 0.0f) {
    const float sample_rate_hz = static_cast<float>(this->sample_rate_);
    this->hp_coefficient_ = sample_rate_hz / (sample_rate_hz + TWO_PI_F * this->hp_frequency_hz_);
    this->hp_enabled_ = true;
  }
}

void NoiseGenerator::dump_config() {
  ESP_LOGCONFIG(TAG, "Noise Source:");
  const char *color = this->color_ == NOISE_WHITE   ? "white"
                      : this->color_ == NOISE_PINK  ? "pink"
                                                    : "brown";
  ESP_LOGCONFIG(TAG, "  Color: %s", color);
  ESP_LOGCONFIG(TAG, "  Sample rate: %u Hz", (unsigned) this->sample_rate_);
  ESP_LOGCONFIG(TAG, "  Gain: %.2f", this->gain_);
  if (this->hp_enabled_) {
    ESP_LOGCONFIG(TAG, "  High-pass: %.0f Hz (12 dB/oct), brown makeup x%.2f", this->hp_frequency_hz_,
                  this->hp_makeup_gain_);
  } else {
    ESP_LOGCONFIG(TAG, "  High-pass: disabled");
  }
}

void NoiseGenerator::start() {
  if (this->speaker_ == nullptr || this->active_)
    return;
  // Begins the fade-in envelope, and drops any chunk the speaker had not
  // finished taking, so the fresh stream starts at a buffer boundary.
  this->begin_fade_();
  // Declare our stream format before feeding raw samples: 16-bit, mono.
  // The mixer duplicates mono to match its output channel count.
  this->speaker_->set_audio_stream_info(audio::AudioStreamInfo(16, 1, this->sample_rate_));
  this->speaker_->start();
  this->active_ = true;
  ESP_LOGD(TAG, "Noise started");
}

void NoiseGenerator::stop() {
  // If we never started, there is nothing to stop. This guard is essential:
  // a switch with RESTORE_DEFAULT_OFF fires on_turn_off during setup(), before
  // the mixer source's task/event group exists, and stopping it then aborts.
  if (!this->active_)
    return;
  this->active_ = false;
  if (this->speaker_ != nullptr)
    this->speaker_->stop();
  ESP_LOGD(TAG, "Noise stopped");
}

float NoiseGenerator::generate_white_() {
  // xorshift32 -> float in [-1.0, 1.0)
  uint32_t rng_value = this->rng_state_;
  rng_value ^= rng_value << 13;
  rng_value ^= rng_value >> 17;
  rng_value ^= rng_value << 5;
  this->rng_state_ = rng_value;
  return (static_cast<int32_t>(rng_value >> 8) - 0x800000) / static_cast<float>(0x800000);
}

float NoiseGenerator::high_pass_(float input_sample) {
  // Standard one-pole HPF difference equation, applied twice in cascade:
  //   output[n] = coefficient * (output[n-1] + input[n] - input[n-1])
  float stage_input = input_sample;
  for (HighPassStageState &stage : this->hp_stages_) {
    const float stage_output =
        this->hp_coefficient_ * (stage.previous_output + stage_input - stage.previous_input);
    stage.previous_input = stage_input;
    stage.previous_output = stage_output;
    stage_input = stage_output;
  }
  return stage_input;
}

float NoiseGenerator::process_sample_(float sample) {
  if (this->hp_enabled_)
    sample = this->high_pass_(sample);

  if (this->color_ == NOISE_BROWN) {
    // Brown loses most of its level to the high-pass; restore it, then soft-
    // saturate. The makeup gain only applies while the filter actually ran --
    // this is what makes high_pass_frequency: 0 reproduce the pre-filter
    // output exactly, regardless of how high_pass_makeup is configured.
    const float makeup_gain = this->hp_enabled_ ? this->hp_makeup_gain_ : 1.0f;
    // tanh rolls rare peaks off smoothly toward +/-1 with no discontinuity,
    // where a hard clamp would flat-top a run of samples and click audibly.
    sample = std::tanh(sample * makeup_gain);
  }
  return sample;
}

bool NoiseGenerator::fill_chunk_(const uint8_t **data, size_t *bytes) {
  // A generator always has something to give, so this never returns false.
  const float amp = this->gain_ * this->envelope() * 32767.0f;
  for (size_t sample_index = 0; sample_index < BUFFER_SAMPLES; sample_index++) {
    const float white = this->generate_white_();
    float sample;
    switch (this->color_) {
      case NOISE_PINK: {
        // Paul Kellet's economical pink-noise approximation.
        this->pink_b0_ = 0.99886f * this->pink_b0_ + white * 0.0555179f;
        this->pink_b1_ = 0.99332f * this->pink_b1_ + white * 0.0750759f;
        this->pink_b2_ = 0.96900f * this->pink_b2_ + white * 0.1538520f;
        this->pink_b3_ = 0.86650f * this->pink_b3_ + white * 0.3104856f;
        this->pink_b4_ = 0.55000f * this->pink_b4_ + white * 0.5329522f;
        this->pink_b5_ = -0.7616f * this->pink_b5_ - white * 0.0168980f;
        float pink = this->pink_b0_ + this->pink_b1_ + this->pink_b2_ + this->pink_b3_ +
                     this->pink_b4_ + this->pink_b5_ + this->pink_b6_ + white * 0.5362f;
        this->pink_b6_ = white * 0.115926f;
        sample = pink * 0.20f;  // bring roughly into [-1, 1]
        break;
      }
      case NOISE_BROWN: {
        // Leaky integrator (Paul Kellet): the /1.02 bleeds off a little of the
        // accumulated value each sample so the random walk stays centered near
        // zero. Without the leak, brown_ drifts into the +/-1 clamp and the
        // *3.5 hard-clips it into a broken, buzzy signal.
        this->brown_ = (this->brown_ + 0.02f * white) / 1.02f;
        // Saturation is deliberately NOT applied here -- process_sample_()
        // applies it after the high-pass, so the limiter acts on the
        // band-limited signal the driver will actually see rather than on
        // bass that gets filtered out a moment later.
        sample = this->brown_ * 3.5f;
        break;
      }
      case NOISE_WHITE:
      default:
        sample = white;
        break;
    }

    sample = this->process_sample_(sample);

    if (sample > 1.0f)
      sample = 1.0f;
    if (sample < -1.0f)
      sample = -1.0f;
    this->buffer_[sample_index] = static_cast<int16_t>(sample * amp);
  }

  *data = reinterpret_cast<const uint8_t *>(this->buffer_);
  *bytes = BUFFER_SAMPLES * sizeof(int16_t);
  return true;
}

}  // namespace noise_generator
}  // namespace esphome
