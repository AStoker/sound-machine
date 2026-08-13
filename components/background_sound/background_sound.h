#pragma once

#include "esphome/core/component.h"
#include "esphome/components/speaker/speaker.h"

namespace esphome {
namespace background_sound {

// ---------------------------------------------------------------------------
// THE SHARED SHAPE OF AN AMBIENCE SOURCE
//
// This device plays two kinds of endless background sound - generated noise
// (components/noise_generator) and decoded MP3 loops (components/ambience_player) -
// and they reach the speaker exactly the same way: own one mixer source, start
// it once, and push PCM into it forever. Nothing about them ends, which is what
// makes them immune to the pipeline-restart failures a media_player hits
// (FUTURE-DEVELOPMENT T3-T5).
//
// "Push PCM into it forever" is fiddlier than it sounds, and it was written
// twice before this existed:
//
//   * `play()` may accept LESS than it was offered - the mixer's ring buffer
//     filled mid-chunk. That is normal, not an error, and the remainder has to
//     be offered again next time FROM THE SAME PLACE. Dropping it lets the
//     source run ahead of playback, which for correlated audio (a brown-noise
//     integrator, a decoded frame) is an audible pop rather than a lost
//     millisecond.
//   * One loop() should top the buffer up greedily but still yield, or a source
//     that can always produce will starve everything else in the main loop.
//   * Both sources want the same fade-in when they start, and neither wants one
//     at any other time.
//
// So the base owns the pump and the envelope; a subclass owns only the part
// that is actually different - where the samples come from. Neither subclass
// defines loop() at all any more.
//
// WHAT A SUBCLASS DOES
//   1. call require_speaker_() from setup()
//   2. set active_ = true when it should be heard, false when it should not
//   3. call begin_fade_() when playback starts (or switches)
//   4. implement fill_chunk_()
//   5. multiply its samples by envelope() while filling
// ---------------------------------------------------------------------------
class BackgroundSound : public Component {
 public:
  // The mixer source speaker this component owns. It must be a source nothing
  // else writes to: ownership is what removes the start/stop races.
  void set_speaker(speaker::Speaker *spk) { this->speaker_ = spk; }
  void set_fade_ms(uint32_t fade_ms) { this->fade_ms_ = fade_ms; }

  // Advances the fade envelope and pumps the mixer source. Subclasses do not
  // override this; they implement fill_chunk_() instead.
  void loop() override;

 protected:
  // Hand back the next chunk of 16-bit PCM, which the subclass keeps in its own
  // buffer (the two subclasses need very different buffer sizes, so the base
  // deliberately does not own one). Return false when nothing is available this
  // pass - that is not an error, the mixer source is holding ~100 ms and the
  // next loop() will ask again.
  //
  // The returned pointer must stay valid until the chunk has been fully
  // accepted, i.e. until the next call to fill_chunk_().
  virtual bool fill_chunk_(const uint8_t **data, size_t *bytes) = 0;

  // Fail the component if no speaker was configured. Call from setup().
  bool require_speaker_();

  // Start (or restart) the fade-in. A fade of 0 lands at full volume at once.
  void begin_fade_();
  // Throw away a partially-accepted chunk. Call when the sound being fed is
  // replaced, so the new one starts at a chunk boundary instead of resuming
  // into the middle of the old one's bytes.
  void discard_pending_() { this->pending_bytes_ = 0; }

  // The fade-in envelope, 0.0 .. 1.0. Subclasses multiply their samples by it.
  float envelope() const { return this->envelope_; }

  speaker::Speaker *speaker_{nullptr};
  // Should this source be contributing to the mix right now? Owned by the
  // subclass, because starting and stopping mean different things to a
  // generator and to a file (see AmbiencePlayer::stop()).
  bool active_{false};

 private:
  uint32_t fade_ms_{0};
  uint32_t fade_start_ms_{0};
  float envelope_{1.0f};
  bool fading_{false};

  // The chunk fill_chunk_() last handed over, advanced as the speaker accepts
  // it. pending_bytes_ == 0 means "ask for another".
  const uint8_t *pending_data_{nullptr};
  size_t pending_bytes_{0};
};

}  // namespace background_sound
}  // namespace esphome
