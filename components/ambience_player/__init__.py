"""Flashed MP3s played as endless ambiences, straight into one mixer source.

The counterpart to `noise_generator`: same shape, same route into the mixer (both
extend `background_sound::BackgroundSound`, which owns that route), but the samples come from
decoded files instead of a generator. It exists because looping through
`speaker.media_player` means `repeat_one`, which restarts the whole pipeline at
end-of-file - see the comment block at the top of ambience_player.h, and
FUTURE-DEVELOPMENT T3/T4/T5.

One instance holds SEVERAL files because the ambiences are mutually exclusive:
they share a mixer source, switching between them is a rewind rather than a stop
and a start, and `ambience_play(name)` can be one parameterised verb instead of a
verb per file.
"""

import esphome.codegen as cg
from esphome.components import audio, background_sound, speaker
import esphome.config_validation as cv
from esphome.const import CONF_FILES, CONF_ID, CONF_NAME, CONF_SAMPLE_RATE

CODEOWNERS = ["@andy"]
DEPENDENCIES = ["speaker", "audio"]
# The shared "own a mixer source and push samples into it forever" base, which
# owns loop(), the short-write carry-over and the fade envelope. Shared with
# noise_generator; see components/background_sound/background_sound.h.
AUTO_LOAD = ["background_sound"]
MULTI_CONF = True

CONF_SPEAKER = "speaker"
CONF_GAIN = "gain"
CONF_FADE_LENGTH = "fade_length"
CONF_FILE = "file"

ambience_player_ns = cg.esphome_ns.namespace("ambience_player")
AmbiencePlayer = ambience_player_ns.class_("AmbiencePlayer", background_sound.BackgroundSound)

# One ambience: a name the rest of the config plays it by, and the audio_file it
# decodes. THE NAME IS THE API - `ambience_play(name)` takes it, and it is what
# behavior/sound.yaml puts in the Sound select. An earlier version addressed
# these by their position in the list, which made the list ORDER a silent
# contract across three files: reorder it and the wrong sound played with every
# check still passing. A name cannot be reordered into a different sound.
AMBIENCE_SCHEMA = cv.Schema(
    {
        cv.Required(CONF_NAME): cv.string_strict,
        cv.Required(CONF_FILE): cv.use_id(audio.AudioFile),
    }
)

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(AmbiencePlayer),
        # The mixer source speaker these ambiences own. It must be a source
        # nothing else writes to: this component starts it once and never stops
        # it, which is the whole reason the loop has no gap.
        cv.Required(CONF_SPEAKER): cv.use_id(speaker.Speaker),
        cv.Required(CONF_FILES): cv.All(
            cv.ensure_list(AMBIENCE_SCHEMA), cv.Length(min=1)
        ),
        # Asserted, not discovered. There is no resampler between this and the
        # mixer, so every file must already be mono at this rate; the component
        # refuses one that disagrees rather than playing it at the wrong speed.
        cv.Optional(CONF_SAMPLE_RATE, default=48000): cv.positive_not_null_int,
        # Leave at 100% when the files are already encoded at the level the rest
        # of the chain is tuned against - the C++ side then skips the multiply
        # and passes decoded frames through byte for byte.
        cv.Optional(CONF_GAIN, default="100%"): cv.percentage,
        # Applied when an ambience starts, and when one ambience is switched for
        # another. There is deliberately no fade at the loop point.
        cv.Optional(
            CONF_FADE_LENGTH, default="0s"
        ): cv.positive_time_period_milliseconds,
    }
).extend(cv.COMPONENT_SCHEMA)


def _request_codecs(config):
    # Pull in micro-mp3 and USE_AUDIO_MP3_SUPPORT independently of whether a
    # media_player also happens to want them, so this component stands alone.
    # Final validation runs before any codegen, which is when the audio
    # component reads these requests.
    audio.request_mp3_support()
    return config


FINAL_VALIDATE_SCHEMA = _request_codecs


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)

    spk = await cg.get_variable(config[CONF_SPEAKER])
    cg.add(var.set_speaker(spk))
    for ambience in config[CONF_FILES]:
        media_file = await cg.get_variable(ambience[CONF_FILE])
        cg.add(var.add_file(ambience[CONF_NAME], media_file))
    cg.add(var.set_sample_rate(config[CONF_SAMPLE_RATE]))
    cg.add(var.set_gain(config[CONF_GAIN]))
    cg.add(var.set_fade_ms(config[CONF_FADE_LENGTH].total_milliseconds))
