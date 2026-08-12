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
  if (this->speaker_ == nullptr)
    return;
  if (this->is_failed()) {
    ESP_LOGW(TAG, "Refusing to start ambience %d: this component failed earlier", index);
    return;
  }
  if (index < 0 || static_cast<size_t>(index) >= this->files_.size()) {
    ESP_LOGW(TAG, "No ambience %d configured", index);
    return;
  }
  if (this->active_ && this->current_ == index)
    return;  // already playing this one

  const bool was_active = this->active_;
  this->select_(index);
  this->active_ = true;

  if (!this->started_) {
    // FIRST START ONLY, for the life of the device - see stop() for why the
    // mixer source is never taken down again. Declare the stream format before
    // feeding samples: asserted, not discovered, because the mixer source is one
    // channel at this rate and there is no resampler in front of it, so
    // adopt_format_() refuses a file that disagrees rather than letting it play
    // at the wrong speed.
    this->speaker_->set_audio_stream_info(audio::AudioStreamInfo(16, 1, this->sample_rate_));
    this->speaker_->start();
    this->started_ = true;
    ESP_LOGD(TAG, "Ambience %d started (mixer source up)", index);
  } else {
    ESP_LOGD(TAG, "Ambience %d %s", index, was_active ? "switched in" : "resumed");
  }
}

void LoopSource::stop() {
  if (!this->active_)
    return;
  this->active_ = false;
  // ---------------------------------------------------------------------
  // THE MIXER SOURCE IS DELIBERATELY NOT STOPPED. Same lesson as the decoder,
  // one layer up, and learned the hard way: stopping it here made an ambience
  // play once and then never again.
  //
  // `SourceSpeaker::stop()` is graceful. The source enters STATE_STOPPING and
  // only reaches STOPPED once `pending_playback_frames_` drains to zero - and
  // that counter is decremented only AFTER `playback_delay_frames_`, the
  // handicap a source is given for starting while the output pipeline already
  // held frames (mixer_speaker.cpp, the output callback). An ambience always
  // starts into a pipeline still holding the previous sound's ~150 ms, so it
  // always carries a handicap. If that handicap outlives the callbacks the
  // counter freezes short of zero and the source sits in STOPPING for good:
  // `play()` will not auto-restart it (it is not *stopped*), its ring buffer was
  // already released by `enter_stopping_state_()`, and every later write is
  // discarded. Silent until reboot, while noise on its own source is fine.
  //
  // Worse: after STOPPING_TIMEOUT_MS (5 s) a stuck source calls `stop()` on the
  // SHARED OUTPUT SPEAKER, taking the noise generator and the voice reply with
  // it.
  //
  // So the source is started once and left running for the life of the device.
  // `timeout: never` in hw/audio_chain.yaml is what makes that legal: with no
  // timeout and no graceful-stop request, STATE_RUNNING never leaves itself, and
  // a running source with an empty buffer contributes nothing to the mix.
  // Stopping an ambience is therefore just: stop feeding it.
  //
  // Cost: up to `buffer_duration` (100 ms) of already-buffered audio still plays
  // out after this returns. That is a tail, not a glitch.
  // ---------------------------------------------------------------------
  this->decoder_ = nullptr;  // hand the decoder's working memory back
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
