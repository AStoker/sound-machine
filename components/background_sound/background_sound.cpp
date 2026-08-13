#include "background_sound.h"
#include "esphome/core/log.h"

namespace esphome {
namespace background_sound {

static const char *const TAG = "background_sound";

// How many chunks one loop() may hand the speaker. Enough to keep the mixer's
// ring buffer topped up from empty, few enough that a source which can always
// produce still yields to the rest of the main loop.
static const int MAX_FEED_ITERATIONS = 6;

bool BackgroundSound::require_speaker_() {
  if (this->speaker_ != nullptr)
    return true;
  ESP_LOGE(TAG, "No speaker configured");
  this->mark_failed();
  return false;
}

void BackgroundSound::begin_fade_() {
  this->fading_ = this->fade_ms_ > 0;
  this->envelope_ = this->fading_ ? 0.0f : 1.0f;
  this->fade_start_ms_ = millis();
  // A new sound starts at a chunk boundary; whatever the speaker had not yet
  // taken belongs to the old one.
  this->discard_pending_();
}

void BackgroundSound::loop() {
  if (!this->active_ || this->speaker_ == nullptr)
    return;

  // Advance the fade envelope toward 1.0. Once per loop() rather than per
  // chunk: a chunk is ~10-25 ms and a fade is seconds, so the step is
  // imperceptible either way and this keeps the envelope constant across the
  // chunks a single pass produces.
  if (this->fading_) {
    const uint32_t elapsed = millis() - this->fade_start_ms_;
    if (elapsed >= this->fade_ms_) {
      this->envelope_ = 1.0f;
      this->fading_ = false;
    } else {
      this->envelope_ = static_cast<float>(elapsed) / static_cast<float>(this->fade_ms_);
    }
  }

  for (int iteration = 0; iteration < MAX_FEED_ITERATIONS; iteration++) {
    if (this->pending_bytes_ == 0) {
      const uint8_t *data = nullptr;
      size_t bytes = 0;
      if (!this->fill_chunk_(&data, &bytes) || data == nullptr || bytes == 0)
        return;  // nothing available this pass; try again next loop()
      this->pending_data_ = data;
      this->pending_bytes_ = bytes;
    }
    // A SHORT WRITE IS NORMAL - it means the ring buffer filled mid-chunk. What
    // it did not take is offered again next time from the same offset, because
    // dropping it would let this source run ahead of playback and skip audio.
    const size_t written = this->speaker_->play(this->pending_data_, this->pending_bytes_);
    this->pending_data_ += written;
    this->pending_bytes_ -= written;
    if (this->pending_bytes_ > 0)
      return;  // ring buffer is full; resume from the same spot next loop()
  }
}

}  // namespace background_sound
}  // namespace esphome
