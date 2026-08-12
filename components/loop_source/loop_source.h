#pragma once

#include "esphome/core/component.h"
#include "esphome/core/helpers.h"
#include "esphome/components/audio/audio.h"
#include "esphome/components/speaker/speaker.h"

#include <micro_mp3/mp3_decoder.h>

#include <memory>
#include <vector>

namespace esphome {
namespace loop_source {

// Flashed MP3s played as ENDLESS AMBIENCES, by the same route noise_source uses: own
// one mixer source, start it once, and push samples into it forever.
//
// WHY THIS EXISTS RATHER THAN `media_player` + `repeat_one`
//
// `speaker.media_player` is built for one-shot announcements and network
// streams. Looping through it means `repeat_one`, which does not loop inside
// the pipeline - it tears the pipeline down at end-of-file and calls
// `start_file()` again. On this build that restart costs ~300 ms of silence,
// re-allocates a 1 MB ring buffer, restarts the i2s speaker task and stalls the
// microphone read; and because the restart re-enters the mixer with a non-empty
// output pipeline, the source speaker is handed a `playback_delay_frames_`
// handicap it cannot always drain, which kills the media channel outright after
// a pass or two. The config's drain-wait protected the FIRST start and nothing
// after it, because `repeat_one` never went near it. See FUTURE-DEVELOPMENT
// T3/T4/T5.
//
// None of that is inherent to "play a loop". Here the speaker is started once
// and never stopped, so there is no end-of-file, no pipeline teardown and no
// handicap. Looping is a rewind of a read pointer.
//
// WHY ONE COMPONENT HOLDS SEVERAL FILES
//
// The ambiences are mutually exclusive - only one sound plays at a time - so they
// share a mixer source, and switching between them is a pointer swap rather than
// a stop and a start. That removes the last start/stop race in the path, and it
// is also why `ambience_play(index)` can be ONE parameterised verb: an
// `audio::AudioFile` id cannot be a script parameter, but an index into this
// list can. The media player needed a verb per track for exactly that reason.
//
// WHY THE WRAP IS SAMPLE-EXACT
//
// The decoder's gapless state is single-use: `vbr_header_checked_` latches
// after the first frame, and the Xing frame count arms an end-trim that counts
// down to zero. A decoder merely re-fed from byte 0 would therefore emit
// nothing. `reset()` re-arms both, so every pass trims the encoder's priming
// samples and end padding exactly as the first pass did, and the file's last
// sample is followed by its first with nothing in between. Whether that *sounds*
// seamless is then a property of the file - see the format rules in
// packages/settings.yaml section 11.
//
// SCOPE: MP3 only, and every file must already match the mixer source it feeds
// (mono, at `sample_rate`). There is no resampler in this path - that is the
// point - so a mismatched file is refused at its first frame rather than played
// at the wrong speed.
class LoopSource : public Component {
 public:
  void setup() override;
  void loop() override;
  void dump_config() override;
  // Run after the speaker/mixer components are set up.
  float get_setup_priority() const override { return setup_priority::LATE; }

  // --- Set from YAML ---
  void set_speaker(speaker::Speaker *spk) { this->speaker_ = spk; }
  void add_file(audio::AudioFile *file) { this->files_.push_back(file); }
  void set_gain(float gain) { this->gain_ = gain; }
  void set_fade_ms(uint32_t fade_ms) { this->fade_ms_ = fade_ms; }
  // The rate the mixer source expects, and the rate every file MUST be encoded
  // at; a mismatch is a hard error rather than a resample.
  void set_sample_rate(uint32_t sample_rate) { this->sample_rate_ = sample_rate; }

  // --- Runtime control (call from lambdas / the api layer) ---
  // Start ambience `index`, or switch to it if another is already playing.
  // NEITHER a switch NOR a stop takes the mixer source down: it is started once,
  // on the first call, and left running for the life of the device. stop()
  // documents why at length - it is the difference between an ambience that can
  // be re-selected and one that plays exactly once.
  void start(int index);
  void stop();
  bool is_active() const { return this->active_; }
  int current_index() const { return this->current_; }
  // Optional independent volume multiplier, 0.0-1.0. Leave at 1.0 if loudness
  // is being controlled with the media player's master volume instead.
  void set_volume(float volume);

 protected:
  // Decodes frames until one yields PCM, rewinding at end-of-file. Returns
  // false when this pass produced nothing, which is not an error - the mixer
  // source holds 100 ms and the next loop() will try again.
  bool decode_frame_();
  // Rewind to byte 0 and re-arm the decoder's gapless trim. This is the whole
  // loop mechanism.
  void rewind_();
  // Adopt (and, on the first frame of a file, validate) the stream format.
  void adopt_format_();
  // Applies gain * volume * fade envelope in place over the decoded frame.
  void apply_gain_();
  // Point the decoder at files_[index] from its first byte, discarding anything
  // decoded from the previous one.
  void select_(int index);
  audio::AudioFile *file_() const { return this->files_[this->current_]; }

  speaker::Speaker *speaker_{nullptr};
  std::vector<audio::AudioFile *> files_;
  std::unique_ptr<micro_mp3::Mp3Decoder> decoder_;

  uint32_t sample_rate_{48000};
  float gain_{1.0f};    // static level trim from YAML
  float volume_{1.0f};  // runtime multiplier
  bool active_{false};   // are we feeding the mixer source right now?
  bool started_{false};  // has the mixer source ever been started? (never unset)
  int current_{-1};

  // Fade-in envelope: ramps 0.0 -> 1.0 over fade_ms_ when an ambience starts OR when
  // one ambience is switched for another. There is deliberately NO fade at the wrap -
  // that is what the loop point of the file itself is for, and a fade here would
  // put back the hole this component exists to remove.
  uint32_t fade_ms_{0};
  uint32_t fade_start_ms_{0};
  float envelope_{1.0f};
  bool fading_{false};

  // Read position within the current file's data, in bytes. The loop is `= 0`.
  size_t read_pos_{0};
  uint32_t passes_{0};  // completed loops of the current ambience, for diagnostics

  bool format_checked_{false};
  uint8_t channels_{1};

  // One decoded MP3 frame. MP3_MIN_OUTPUT_BUFFER_BYTES (4608) covers the worst
  // case (MPEG1 stereo); a mono 48 kHz file uses half of it.
  uint8_t pcm_[micro_mp3::MP3_MIN_OUTPUT_BUFFER_BYTES];
  // Decoded bytes not yet accepted by the speaker, held across loop() calls. A
  // short write is normal - it means the mixer's ring buffer filled mid-frame -
  // and dropping the remainder would skip audio, so it is offered again next
  // time from the same offset.
  size_t pending_bytes_{0};
  size_t pending_offset_{0};
};

}  // namespace loop_source
}  // namespace esphome
