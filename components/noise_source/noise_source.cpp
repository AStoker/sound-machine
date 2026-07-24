#include "noise_source.h"
#include "esphome/core/log.h"
#include <cmath>

namespace esphome {
namespace noise_source {

static const char *const TAG = "noise_source";

void NoiseSource::setup() {
  if (this->speaker_ == nullptr) {
    ESP_LOGE(TAG, "No speaker configured");
    this->mark_failed();
    return;
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
}

void NoiseSource::start() {
  if (this->speaker_ == nullptr || this->active_)
    return;
  // Begin the fade-in envelope (or jump straight to full if fade disabled).
  this->fading_ = this->fade_ms_ > 0;
  this->envelope_ = this->fading_ ? 0.0f : 1.0f;
  this->fade_start_ms_ = millis();
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
  uint32_t x = this->rng_state_;
  x ^= x << 13;
  x ^= x >> 17;
  x ^= x << 5;
  this->rng_state_ = x;
  return (static_cast<int32_t>(x >> 8) - 0x800000) / static_cast<float>(0x800000);
}

void NoiseSource::fill_buffer_() {
  const float amp = this->gain_ * this->volume_ * this->envelope_ * 32767.0f;
  for (size_t i = 0; i < BUFFER_SAMPLES; i++) {
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
        // Soft-saturate rather than hard-clamp. Brown is low-frequency, so a
        // hard clamp flat-tops a run of samples and clicks audibly; tanh rolls
        // rare peaks off smoothly toward +/-1 with no discontinuity.
        sample = std::tanh(this->brown_ * 3.5f);
        break;
      }
      case NOISE_WHITE:
      default:
        sample = white;
        break;
    }
    if (sample > 1.0f)
      sample = 1.0f;
    if (sample < -1.0f)
      sample = -1.0f;
    this->buffer_[i] = static_cast<int16_t>(sample * amp);
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
  // actually accepted; a short write means the buffer is full, so we stop until
  // the next loop() and let the mixer drain it. This self-paces to 48 kHz with
  // no fixed timer, so there is no underrun seam and no pipeline restart.
  const size_t chunk_bytes = BUFFER_SAMPLES * sizeof(int16_t);
  for (int iter = 0; iter < 6; iter++) {
    this->fill_buffer_();
    size_t written = this->speaker_->play(reinterpret_cast<const uint8_t *>(this->buffer_), chunk_bytes);
    if (written < chunk_bytes)
      break;
  }
}

}  // namespace noise_source
}  // namespace esphome
