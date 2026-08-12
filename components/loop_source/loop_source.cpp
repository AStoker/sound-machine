#include "loop_source.h"
#include "esphome/core/log.h"

namespace esphome {
namespace loop_source {

static const char *const TAG = "loop_source";

// How many decode() calls one loop() may spend trying to produce PCM. A rewind
// costs a reset, a format probe and the Xing header frame before any samples
// come out, and the end of a file yields a few fully-trimmed frames - so the
// budget has to cover a wrap, but must stay bounded so a pathological file
// cannot hold the main loop.
static const int MAX_DECODE_ATTEMPTS = 12;
// How many frames one loop() may hand the speaker. Matches noise_source: enough
// to keep the mixer's ring buffer topped up, few enough to yield promptly.
static const int MAX_FEED_ITERATIONS = 6;

void LoopSource::setup() {
  if (this->speaker_ == nullptr) {
    ESP_LOGE(TAG, "No speaker configured");
    this->mark_failed();
    return;
  }
  if (this->files_.empty()) {
    ESP_LOGE(TAG, "No files configured");
    this->mark_failed();
    return;
  }
  for (size_t i = 0; i < this->files_.size(); i++) {
    audio::AudioFile *file = this->files_[i];
    if (file == nullptr || file->data == nullptr || file->length == 0) {
      ESP_LOGE(TAG, "Ambience %u is empty", (unsigned) i);
      this->mark_failed();
      return;
    }
    if (file->file_type != audio::AudioFileType::MP3) {
      ESP_LOGE(TAG, "Ambience %u is %s; this component decodes MP3 only", (unsigned) i,
               audio::audio_file_type_to_string(file->file_type));
      this->mark_failed();
      return;
    }
  }
}

void LoopSource::dump_config() {
  ESP_LOGCONFIG(TAG, "Loop Source:");
  ESP_LOGCONFIG(TAG, "  Sample rate: %u Hz (mono, no resampler in this path)", (unsigned) this->sample_rate_);
  ESP_LOGCONFIG(TAG, "  Gain: %.2f", this->gain_);
  if (this->fade_ms_ > 0) {
    ESP_LOGCONFIG(TAG, "  Fade-in: %u ms (on start and on switch; the wrap is never faded)",
                  (unsigned) this->fade_ms_);
  }
  for (size_t i = 0; i < this->files_.size(); i++) {
    ESP_LOGCONFIG(TAG, "  Ambience %u: %u bytes, MP3", (unsigned) i, (unsigned) this->files_[i]->length);
  }
}

void LoopSource::select_(int index) {
  this->current_ = index;
  this->read_pos_ = 0;
  this->passes_ = 0;
  this->format_checked_ = false;
  this->pending_bytes_ = 0;
  this->pending_offset_ = 0;
  // A fresh decoder per file. The constructor allocates nothing - the first
  // decode() does - so this is cheap, and it guarantees no gapless trim state
  // survives from the file we were playing before.
  this->decoder_ = make_unique<micro_mp3::Mp3Decoder>();

  this->fading_ = this->fade_ms_ > 0;
  this->envelope_ = this->fading_ ? 0.0f : 1.0f;
  this->fade_start_ms_ = millis();
}

void LoopSource::start(int index) {
  if (this->speaker_ == nullptr || this->is_failed())
    return;
  if (index < 0 || static_cast<size_t>(index) >= this->files_.size()) {
    ESP_LOGW(TAG, "No ambience %d configured", index);
    return;
  }
  if (this->active_ && this->current_ == index)
    return;  // already playing this one

  const bool switching = this->active_;
  this->select_(index);

  if (!switching) {
    // Declare the stream format before feeding samples. This is asserted, not
    // discovered: the mixer source is one channel at this rate and there is no
    // resampler in front of it, so adopt_format_() refuses a file that
    // disagrees rather than letting it play at the wrong speed.
    this->speaker_->set_audio_stream_info(audio::AudioStreamInfo(16, 1, this->sample_rate_));
    this->speaker_->start();
    this->active_ = true;
    ESP_LOGD(TAG, "Ambience %d started", index);
  } else {
    // Deliberately NOT stopping and restarting the speaker. Every file here is
    // the same format, so the running stream stays valid and the switch costs
    // nothing but a rewind - which is the whole reason the ambiences share one mixer
    // source.
    ESP_LOGD(TAG, "Switched to ambience %d", index);
  }
}

void LoopSource::stop() {
  // If we never started there is nothing to stop. The guard matters: a restore
  // at boot can call this before the mixer source's task exists, and stopping
  // it then aborts.
  if (!this->active_)
    return;
  this->active_ = false;
  if (this->speaker_ != nullptr)
    this->speaker_->stop();
  // Hand the decoder's working memory back while the ambience is off.
  this->decoder_ = nullptr;
  ESP_LOGD(TAG, "Ambience %d stopped after %u pass(es)", this->current_, (unsigned) this->passes_);
  this->current_ = -1;
}

void LoopSource::set_volume(float volume) {
  if (volume < 0.0f)
    volume = 0.0f;
  if (volume > 1.0f)
    volume = 1.0f;
  this->volume_ = volume;
}

void LoopSource::rewind_() {
  // THE LOOP. reset() is not housekeeping - it is what makes the wrap
  // sample-exact. The decoder's gapless state is single-use (the Xing header is
  // checked once, and its frame count arms an end-trim that counts down to
  // zero), so a decoder re-fed from byte 0 without it would emit nothing at all.
  this->decoder_->reset();
  this->read_pos_ = 0;
  this->passes_++;
}

void LoopSource::adopt_format_() {
  this->channels_ = this->decoder_->get_channels();
  const uint32_t rate = this->decoder_->get_sample_rate();
  if (this->format_checked_)
    return;
  this->format_checked_ = true;
  if (rate != this->sample_rate_ || this->channels_ != 1) {
    ESP_LOGE(TAG,
             "Ambience %d is %u Hz / %u channel(s); this feeds a mixer source directly and needs %u Hz mono. "
             "Re-encode it (ffmpeg -ac 1 -ar %u) - there is no resampler in this path.",
             this->current_, (unsigned) rate, (unsigned) this->channels_, (unsigned) this->sample_rate_,
             (unsigned) this->sample_rate_);
    this->mark_failed();
    this->stop();
  }
}

bool LoopSource::decode_frame_() {
  for (int attempt = 0; attempt < MAX_DECODE_ATTEMPTS; attempt++) {
    if (!this->active_)
      return false;
    audio::AudioFile *file = this->file_();
    if (this->read_pos_ >= file->length)
      this->rewind_();

    size_t consumed = 0;
    size_t samples = 0;
    const micro_mp3::Mp3Result result = this->decoder_->decode(
        file->data + this->read_pos_, file->length - this->read_pos_, this->pcm_, sizeof(this->pcm_), consumed, samples);
    this->read_pos_ += consumed;

    switch (result) {
      case micro_mp3::MP3_OK:
        // samples == 0 is normal and not an end condition: the Xing/Info header
        // frame decodes to nothing, and so do the padding frames the end-trim
        // has already accounted for. Keep going.
        if (samples == 0)
          break;
        this->pending_bytes_ = samples * this->channels_ * sizeof(int16_t);
        this->pending_offset_ = 0;
        this->apply_gain_();
        return true;

      case micro_mp3::MP3_STREAM_INFO_READY:
      case micro_mp3::MP3_STREAM_INFO_CHANGED:
        this->adopt_format_();
        break;

      case micro_mp3::MP3_NEED_MORE_DATA:
        // There is no "more" - the whole file is in flash and handed over in one
        // span. So this means either end-of-file (rewind), or that the decoder
        // consumed non-audio bytes it reports separately, such as the ID3v2 tag
        // at the head of the file (just continue). Distinguishing them matters:
        // rewinding on the ID3 skip would spin here forever.
        if (this->read_pos_ >= file->length) {
          this->rewind_();
        } else if (consumed == 0) {
          // No progress with data still available - give the main loop its turn
          // rather than burning the attempt budget.
          return false;
        }
        break;

      case micro_mp3::MP3_DECODE_ERROR:
        ESP_LOGW(TAG, "Skipped a corrupt frame at byte %u", (unsigned) this->read_pos_);
        break;

      default:
        ESP_LOGE(TAG, "Decoder failed: %d", static_cast<int>(result));
        this->stop();
        this->mark_failed();
        return false;
    }
  }
  return false;
}

void LoopSource::apply_gain_() {
  const float scale = this->gain_ * this->volume_ * this->envelope_;
  // Unity is the common case (files are encoded at the level the rest of the
  // chain is tuned against), and skipping it keeps the frame byte-for-byte as
  // decoded.
  if (scale > 0.9999f && scale < 1.0001f)
    return;

  int16_t *samples = reinterpret_cast<int16_t *>(this->pcm_);
  const size_t count = this->pending_bytes_ / sizeof(int16_t);
  for (size_t i = 0; i < count; i++) {
    float scaled = static_cast<float>(samples[i]) * scale;
    if (scaled > 32767.0f)
      scaled = 32767.0f;
    if (scaled < -32768.0f)
      scaled = -32768.0f;
    samples[i] = static_cast<int16_t>(scaled);
  }
}

void LoopSource::loop() {
  if (!this->active_ || this->speaker_ == nullptr)
    return;

  // Advance the fade-in envelope toward 1.0. It is applied per decoded frame
  // (24 ms at 1152 samples / 48 kHz), which is fine for a multi-second fade.
  if (this->fading_) {
    const uint32_t elapsed = millis() - this->fade_start_ms_;
    if (elapsed >= this->fade_ms_) {
      this->envelope_ = 1.0f;
      this->fading_ = false;
    } else {
      this->envelope_ = static_cast<float>(elapsed) / static_cast<float>(this->fade_ms_);
    }
  }

  // Greedily top up the mixer input's ring buffer. play() returns the bytes it
  // actually accepted; a short write means the ring buffer filled mid-frame, so
  // the remainder is carried in pending_* and offered again next loop().
  for (int iter = 0; iter < MAX_FEED_ITERATIONS; iter++) {
    if (this->pending_bytes_ == 0) {
      if (!this->decode_frame_())
        break;
    }
    const size_t written = this->speaker_->play(this->pcm_ + this->pending_offset_, this->pending_bytes_);
    this->pending_offset_ += written;
    this->pending_bytes_ -= written;
    if (this->pending_bytes_ > 0)
      break;  // ring buffer is full; resume from the same spot next loop()
  }
}

}  // namespace loop_source
}  // namespace esphome
