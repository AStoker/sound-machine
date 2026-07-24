#include "noise_source.h"
#include "esphome/core/log.h"
#include <cmath>

namespace esphome {
namespace noise_source {

static const char *const TAG = "noise_source";
static const float TWO_PI_F = 6.28318530718f;

void NoiseSource::setup() {
  if (this->speaker_ == nullptr) {
    ESP_LOGE(TAG, "No speaker configured");
    this->mark_failed();
    return;
  }

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

void NoiseSource::dump_config() {
  ESP_LOGCONFIG(TAG, "Noise Source:");
  const char *color = this->color_ == NOISE_WHITE   ? "white"
                      : this->color_ == NOISE_PINK  ? "pink"
                                                    : "brown";
  ESP_LOGCONFIG(TAG, "  Color: %s", color);
  ESP_LOGCONFIG(TAG, "  Sample rate: %u Hz", this->sample_rate_);
  ESP_LOGCONFIG(TAG, "  Gain: %.2f", this->gain_);
  if (this->hp_enabled_) {
    ESP_LOGCONFIG(TAG, "  High-pass: %.0f Hz (12 dB/oct), brown makeup x%.2f", this->hp_frequency_hz_,
                  this->hp_makeup_gain_);
  } else {
    ESP_LOGCONFIG(TAG, "  High-pass: disabled");
  }
}

void NoiseSource::start() {
  if (this->speaker_ == nullptr || this->active_)
    return;
  // Begin the fade-in envelope (or jump straight to full if fade disabled).
  this->fading_ = this->fade_ms_ > 0;
  this->envelope_ = this->fading_ ? 0.0f : 1.0f;
  this->fade_start_ms_ = millis();
  // Any samples left over from the previous run are stale; drop them so the
  // fresh stream starts at a buffer boundary.
  this->pending_bytes_ = 0;
  this->pending_offset_ = 0;
  // Declare our stream format before feeding raw samples: 16-bit, mono.
  // The mixer duplicates mono to match its output channel count.
  this->speaker_->set_audio_stream_info(audio::AudioStreamInfo(16, 1, this->sample_rate_));
  this->speaker_->start();
  this->active_ = true;
  ESP_LOGD(TAG, "Noise started");
}

void NoiseSource::stop() {
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

void NoiseSource::set_volume(float volume) {
  this->volume_ = volume < 0.0f ? 0.0f : (volume > 1.0f ? 1.0f : volume);
}

float NoiseSource::generate_white_() {
  // xorshift32 -> float in [-1.0, 1.0)
  uint32_t rng_value = this->rng_state_;
  rng_value ^= rng_value << 13;
  rng_value ^= rng_value >> 17;
  rng_value ^= rng_value << 5;
  this->rng_state_ = rng_value;
  return (static_cast<int32_t>(rng_value >> 8) - 0x800000) / static_cast<float>(0x800000);
}

float NoiseSource::high_pass_(float input_sample) {
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

float NoiseSource::process_sample_(float sample) {
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

void NoiseSource::fill_buffer_() {
  const float amp = this->gain_ * this->volume_ * this->envelope_ * 32767.0f;
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
}

void NoiseSource::loop() {
  if (!this->active_ || this->speaker_ == nullptr)
    return;

  // Advance the fade-in envelope toward 1.0 based on elapsed time.
  if (this->fading_) {
    uint32_t elapsed = millis() - this->fade_start_ms_;
    if (elapsed >= this->fade_ms_) {
      this->envelope_ = 1.0f;
      this->fading_ = false;
    } else {
      this->envelope_ = (float) elapsed / (float) this->fade_ms_;
    }
  }

  // Greedily top up the mixer input's ring buffer. play() returns the bytes it
  // actually accepted; a SHORT write is not an error, it means the ring buffer
  // filled mid-chunk. Anything it did not take is carried over in pending_* and
  // offered again on the next loop() rather than being discarded -- discarding
  // it would let the generator run ahead of playback and skip a section of the
  // correlated brown-noise integrator, which pops.
  const size_t chunk_bytes = BUFFER_SAMPLES * sizeof(int16_t);
  const uint8_t *raw = reinterpret_cast<const uint8_t *>(this->buffer_);

  for (int iter = 0; iter < 6; iter++) {
    if (this->pending_bytes_ == 0) {
      this->fill_buffer_();
      this->pending_bytes_ = chunk_bytes;
      this->pending_offset_ = 0;
    }
    const size_t written = this->speaker_->play(raw + this->pending_offset_, this->pending_bytes_);
    this->pending_offset_ += written;
    this->pending_bytes_ -= written;
    if (this->pending_bytes_ > 0)
      break;  // ring buffer is full; resume from the same spot next loop()
  }
}

}  // namespace noise_source
}  // namespace esphome