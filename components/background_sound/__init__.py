"""Shared base class for the components that feed a mixer source forever.

Code only - there is nothing to configure here and nothing to put in YAML. Both
`noise_generator` and `ambience_player` AUTO_LOAD this so the header is copied into the
build; see background_sound.h for what it does and why it exists.
"""

import esphome.codegen as cg
import esphome.config_validation as cv

CODEOWNERS = ["@andy"]
DEPENDENCIES = ["speaker"]

background_sound_ns = cg.esphome_ns.namespace("background_sound")
BackgroundSound = background_sound_ns.class_("BackgroundSound", cg.Component)

CONFIG_SCHEMA = cv.Schema({})


async def to_code(config):
    pass
