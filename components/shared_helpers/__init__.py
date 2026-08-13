"""Sound Machine shared helpers - free functions callable from any YAML lambda.

Code only; there is nothing to configure. Listing `shared_helpers:` in the config is
what gets the header into the generated main.cpp, which is how a lambda in one
package can call a function another package also uses. See shared_helpers.h for what
lives here and, more importantly, what does not.
"""

import esphome.codegen as cg
import esphome.config_validation as cv

CODEOWNERS = ["@andy"]
DEPENDENCIES = ["select"]

shared_helpers_ns = cg.esphome_ns.namespace("shared_helpers")

CONFIG_SCHEMA = cv.Schema({})


async def to_code(config):
    pass
