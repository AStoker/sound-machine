#pragma once

#include "esphome/components/background_sound/background_sound.h"
#include "esphome/components/audio/audio.h"

#include <micro_mp3/mp3_decoder.h>

#include <memory>
#include <string>
#include <vector>

namespace esphome {
namespace ambience_player {

// Flashed MP3s played as ENDLESS AMBIENCES, by the same route noise_generator uses:
// own one mixer source, start it once, and push samples into it forever. The
// route itself lives in background_sound::BackgroundSound and is shared with the noise
// generator; what is here is only the decoding and the loop.
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
// ---------------------------------------------------------------------------
// WHY THE MIXER SOURCE IS NEVER STOPPED
//
// Learned the hard way: stopping it made an ambience play once and then never
// again. `SourceSpeaker::stop()` is graceful. The source enters STATE_STOPPING
// and only reaches STOPPED once `pending_playback_frames_` drains to zero - and
// that counter is decremented only AFTER `playback_delay_frames_`, the handicap
// a source is given for starting while the output pipeline already held frames
// (mixer_speaker.cpp, the output callback). An ambience always starts into a
// pipeline still holding the previous sound's ~150 ms, so it always carries a
// handicap. If that handicap outlives the callbacks the counter freezes short of
// zero and the source sits in STOPPING for good: `play()` will not auto-restart
// it (it is not *stopped*), its ring buffer was already released by
// `enter_stopping_state_()`, and every later write is discarded. Silent until
// reboot, while noise on its own source is fine.
//
// Worse: after STOPPING_TIMEOUT_MS (5 s) a stuck source calls `stop()` on the
// SHARED OUTPUT SPEAKER, taking the noise generator and the voice reply with it.
//
// So the source is started once and left running for the life of the device.
// `timeout: never` in hw/audio_chain.yaml is what makes that legal: with no
// timeout and no graceful-stop request, STATE_RUNNING never leaves itself, and a
// running source with an empty buffer contributes nothing to the mix. Stopping
// an ambience is therefore just: stop feeding it. Cost is up to `buffer_duration`
// (100 ms) of already-buffered audio still playing out - a tail, not a glitch.
// ---------------------------------------------------------------------------
//
// WHY ONE COMPONENT HOLDS SEVERAL FILES
//
// The ambiences are mutually exclusive - only one sound plays at a time - so
// they share a mixer source, and switching between them is a pointer swap
// rather than a stop and a start. That removes the last start/stop race in the
// path, and it is also why `ambience_play(name)` can be ONE parameterised verb:
// an `audio::AudioFile` id cannot be a script parameter, but the name of one can.
//
// FILES ARE ADDRESSED BY NAME, NOT BY POSITION. An earlier version took an index
// into `files:`, which made the list ORDER a silent API contract between three
// files - reorder `files:` and the wrong ambience plays, with every check still
// passing. A name cannot be reordered into a different sound, so the contract is
// enforced by the lookup rather than by three comments asking people to be
// careful. An unknown name logs and changes nothing.
//
// WHY THE WRAP IS SAMPLE-EXACT
//
// The decoder's gapless state is single-use: `vbr_header_checked_` latches
// after the first frame, and the Xing frame count arms an end-trim that counts
// down to zero. A decoder merely re-fed from byte 0 would therefore emit
// nothing. `reset()` re-arms both, so every pass trims the encoder's priming
// samples and end padding exactly as the first pass did, and the file's last
// sample is followed by its first with nothing in between. Whether that *sounds*
// seamless is then a property of the file - see sounds/README.md.
//
// SCOPE: MP3 only, and every file must already match the mixer source it feeds
// (mono, at `sample_rate`). There is no resampler in this path - that is the
// point - so a mismatched file is refused rather than played at the wrong speed.
class AmbiencePlayer : public background_sound::BackgroundSound {
 public:
  void setup() override;
  void dump_config() override;
  // Run after the speaker/mixer components are set up.
  float get_setup_priority() const override { return setup_priority::LATE; }

  // --- Set from YAML ---
  void add_file(const std::string &name, audio::AudioFile *file) {
    this->ambiences_.push_back(Ambience{name, file});
  }
  void set_gain(float gain) { this->gain_ = gain; }
  // The rate the mixer source expects, and the rate every file MUST be encoded
  // at; a mismatch is a hard error rather than a resample.
  void set_sample_rate(uint32_t sample_rate) { this->sample_rate_ = sample_rate; }

  // --- Runtime control (called from api/sound.yaml) ---
  // Start the named ambience, or switch to it if another is already playing.
  // An unknown name logs a warning and leaves playback untouched.
  //
  // NEITHER a switch NOR a stop takes the mixer source down: it is started once,
  // on the first call, and left running for the life of the device - see the
  // block above.
  void start(const std::string &name);
  void stop();
  // Is there an ambience by this name? This is what lets behavior/sound.yaml ask
  // "is this Sound option a flashed ambience or a noise colour?" without keeping
  // its own copy of the list - `files:` is the only place they are named.
  bool has(const std::string &name) const { return this->index_of_(name) >= 0; }

 protected:
  struct Ambience {
    std::string name;
    audio::AudioFile *file;
  };

  bool fill_chunk_(const uint8_t **data, size_t *bytes) override;

  // Decodes frames until one yields PCM, rewinding at end-of-file. Returns 0
  // when this pass produced nothing, which is not an error - the mixer source
  // holds 100 ms and the next loop() will try again.
  size_t decode_frame_();
  // Rewind to byte 0 and re-arm the decoder's gapless trim. This is the whole
  // loop mechanism.
  void rewind_();
  // Check the decoded stream against what the mixer source can accept, and fail
  // the component if they disagree. Runs on EVERY format report, not just the
  // first: a mid-stream change to stereo would otherwise be adopted silently and
  // played into a mono source at the wrong speed.
  bool check_format_();
  // Applies gain * fade envelope in place over the decoded frame.
  void apply_gain_(size_t bytes);
  // Point the decoder at an ambience from its first byte, discarding anything
  // decoded from the previous one.
  void select_(int index);
  // Position of `name` in ambiences_, or -1 if there is no such ambience.
  int index_of_(const std::string &name) const;
  audio::AudioFile *file_() const { return this->ambiences_[this->current_].file; }

  std::vector<Ambience> ambiences_;
  std::unique_ptr<micro_mp3::Mp3Decoder> decoder_;

  uint32_t sample_rate_{48000};
  float gain_{1.0f};     // static level trim from YAML
  bool started_{false};  // has the mixer source ever been started? (never unset)
  int current_{-1};

  // Read position within the current file's data, in bytes. The loop is `= 0`.
  size_t read_pos_{0};
  uint32_t passes_{0};  // completed loops of the current ambience, for diagnostics

  uint8_t channels_{1};

  // One decoded MP3 frame. MP3_MIN_OUTPUT_BUFFER_BYTES (4608) covers the worst
  // case (MPEG1 stereo); a mono 48 kHz file uses half of it.
  uint8_t pcm_[micro_mp3::MP3_MIN_OUTPUT_BUFFER_BYTES];
};

}  // namespace ambience_player
}  // namespace esphome
