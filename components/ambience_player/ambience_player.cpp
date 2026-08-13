#include "ambience_player.h"
#include "esphome/core/log.h"

namespace esphome {
namespace ambience_player {

static const char *const TAG = "ambience_player";

// How many decode() calls one chunk may spend trying to produce PCM. A rewind
// costs a reset, a format probe and the Xing header frame before any samples
// come out, and the end of a file yields a few fully-trimmed frames - so the
// budget has to cover a wrap, but must stay bounded so a pathological file
// cannot hold the main loop.
static const int MAX_DECODE_ATTEMPTS = 12;

void AmbiencePlayer::setup() {
  if (!this->require_speaker_())
    return;
  if (this->ambiences_.empty()) {
    ESP_LOGE(TAG, "No files configured");
    this->mark_failed();
    return;
  }
  for (const Ambience &ambience : this->ambiences_) {
    const audio::AudioFile *file = ambience.file;
    if (file == nullptr || file->data == nullptr || file->length == 0) {
      ESP_LOGE(TAG, "Ambience '%s' is empty", ambience.name.c_str());
      this->mark_failed();
      return;
    }
    if (file->file_type != audio::AudioFileType::MP3) {
      ESP_LOGE(TAG, "Ambience '%s' is %s; this component decodes MP3 only", ambience.name.c_str(),
               audio::audio_file_type_to_string(file->file_type));
      this->mark_failed();
      return;
    }
  }
}

void AmbiencePlayer::dump_config() {
  ESP_LOGCONFIG(TAG, "Loop Source:");
  ESP_LOGCONFIG(TAG, "  Sample rate: %u Hz (mono, no resampler in this path)", (unsigned) this->sample_rate_);
  ESP_LOGCONFIG(TAG, "  Gain: %.2f", this->gain_);
  for (const Ambience &ambience : this->ambiences_) {
    ESP_LOGCONFIG(TAG, "  Ambience '%s': %u bytes, MP3", ambience.name.c_str(),
                  (unsigned) ambience.file->length);
  }
}

int AmbiencePlayer::index_of_(const std::string &name) const {
  for (size_t i = 0; i < this->ambiences_.size(); i++) {
    if (this->ambiences_[i].name == name)
      return static_cast<int>(i);
  }
  return -1;
}

void AmbiencePlayer::select_(int index) {
  this->current_ = index;
  this->read_pos_ = 0;
  this->passes_ = 0;
  // A fresh decoder per file. The constructor allocates nothing - the first
  // decode() does - so this is cheap, and it guarantees no gapless trim state
  // survives from the file we were playing before.
  this->decoder_ = make_unique<micro_mp3::Mp3Decoder>();
  // Fades in, and drops any bytes of the previous ambience the speaker had not
  // yet taken.
  this->begin_fade_();
}

void AmbiencePlayer::start(const std::string &name) {
  if (this->speaker_ == nullptr)
    return;
  if (this->is_failed()) {
    ESP_LOGW(TAG, "Refusing to start ambience '%s': this component failed earlier", name.c_str());
    return;
  }
  const int index = this->index_of_(name);
  if (index < 0) {
    ESP_LOGW(TAG, "No ambience named '%s' - check the `files:` list in hw/audio_chain.yaml",
             name.c_str());
    return;
  }
  if (this->active_ && this->current_ == index)
    return;  // already playing this one

  const bool was_active = this->active_;
  this->select_(index);
  this->active_ = true;

  if (!this->started_) {
    // FIRST START ONLY, for the life of the device - see the header for why the
    // mixer source is never taken down again. Declare the stream format before
    // feeding samples: asserted, not discovered, because the mixer source is one
    // channel at this rate and there is no resampler in front of it, so
    // check_format_() refuses a file that disagrees rather than letting it play
    // at the wrong speed.
    this->speaker_->set_audio_stream_info(audio::AudioStreamInfo(16, 1, this->sample_rate_));
    this->speaker_->start();
    this->started_ = true;
    ESP_LOGD(TAG, "Ambience '%s' started (mixer source up)", name.c_str());
  } else {
    ESP_LOGD(TAG, "Ambience '%s' %s", name.c_str(), was_active ? "switched in" : "resumed");
  }
}

void AmbiencePlayer::stop() {
  if (!this->active_)
    return;
  // Just stop feeding it. The mixer source stays up for good - the header
  // explains at length why taking it down is what broke this before.
  this->active_ = false;
  this->discard_pending_();
  this->decoder_ = nullptr;  // hand the decoder's working memory back
  ESP_LOGD(TAG, "Ambience '%s' stopped after %u pass(es)", this->ambiences_[this->current_].name.c_str(),
           (unsigned) this->passes_);
  this->current_ = -1;
}

void AmbiencePlayer::rewind_() {
  // THE LOOP. reset() is not housekeeping - it is what makes the wrap
  // sample-exact. The decoder's gapless state is single-use (the Xing header is
  // checked once, and its frame count arms an end-trim that counts down to
  // zero), so a decoder re-fed from byte 0 without it would emit nothing at all.
  this->decoder_->reset();
  this->read_pos_ = 0;
  this->passes_++;
}

bool AmbiencePlayer::check_format_() {
  const uint32_t rate = this->decoder_->get_sample_rate();
  const uint8_t channels = this->decoder_->get_channels();
  if (rate != this->sample_rate_ || channels != 1) {
    ESP_LOGE(TAG,
             "Ambience '%s' is %u Hz / %u channel(s); this feeds a mixer source directly and needs %u Hz mono. "
             "Re-encode it (ffmpeg -ac 1 -ar %u) - there is no resampler in this path.",
             this->ambiences_[this->current_].name.c_str(), (unsigned) rate, (unsigned) channels,
             (unsigned) this->sample_rate_, (unsigned) this->sample_rate_);
    this->stop();
    this->mark_failed();
    return false;
  }
  this->channels_ = channels;
  return true;
}

size_t AmbiencePlayer::decode_frame_() {
  // Watched across the WHOLE attempt budget rather than per attempt: a single
  // decode() may legitimately consume nothing (the first format probe does), so
  // only a run of attempts that moves neither the read position nor the pass
  // counter is a genuine stall.
  const size_t entry_pos = this->read_pos_;
  const uint32_t entry_passes = this->passes_;

  for (int attempt = 0; attempt < MAX_DECODE_ATTEMPTS; attempt++) {
    if (!this->active_)
      return 0;
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
        return samples * this->channels_ * sizeof(int16_t);

      case micro_mp3::MP3_STREAM_INFO_READY:
      case micro_mp3::MP3_STREAM_INFO_CHANGED:
        if (!this->check_format_())
          return 0;
        break;

      case micro_mp3::MP3_NEED_MORE_DATA:
        // There is no "more" - the whole file is in flash and handed over in one
        // span. So this means end-of-file (rewind), or that the decoder consumed
        // non-audio bytes it reports separately, such as the ID3v2 tag at the
        // head of the file (just continue). Distinguishing them matters:
        // rewinding on the ID3 skip would spin here forever.
        if (this->read_pos_ >= file->length)
          this->rewind_();
        break;

      case micro_mp3::MP3_DECODE_ERROR:
        ESP_LOGW(TAG, "Skipped a corrupt frame at byte %u", (unsigned) this->read_pos_);
        break;

      default:
        ESP_LOGE(TAG, "Decoder failed: %d", static_cast<int>(result));
        this->stop();
        this->mark_failed();
        return 0;
    }
  }

  // Out of attempts with no PCM. If NOTHING moved in all of them - not one byte
  // consumed, not one rewind - the decoder is stuck on these bytes and will be
  // just as stuck next pass. That used to be a silent dead channel: the
  // NEED_MORE_DATA branch returned quietly and the DECODE_ERROR branch logged
  // the same warning forever. Give up loudly instead.
  if (this->read_pos_ == entry_pos && this->passes_ == entry_passes) {
    ESP_LOGE(TAG, "Ambience '%s' is stuck at byte %u - stopping", this->ambiences_[this->current_].name.c_str(),
             (unsigned) this->read_pos_);
    this->stop();
    this->mark_failed();
  }
  return 0;
}

void AmbiencePlayer::apply_gain_(size_t bytes) {
  const float scale = this->gain_ * this->envelope();
  // Unity is the common case (files are encoded at the level the rest of the
  // chain is tuned against), and skipping it keeps the frame byte-for-byte as
  // decoded.
  if (scale > 0.9999f && scale < 1.0001f)
    return;

  int16_t *samples = reinterpret_cast<int16_t *>(this->pcm_);
  const size_t count = bytes / sizeof(int16_t);
  for (size_t i = 0; i < count; i++) {
    float scaled = static_cast<float>(samples[i]) * scale;
    if (scaled > 32767.0f)
      scaled = 32767.0f;
    if (scaled < -32768.0f)
      scaled = -32768.0f;
    samples[i] = static_cast<int16_t>(scaled);
  }
}

bool AmbiencePlayer::fill_chunk_(const uint8_t **data, size_t *bytes) {
  const size_t decoded = this->decode_frame_();
  if (decoded == 0)
    return false;
  this->apply_gain_(decoded);
  *data = this->pcm_;
  *bytes = decoded;
  return true;
}

}  // namespace ambience_player
}  // namespace esphome
