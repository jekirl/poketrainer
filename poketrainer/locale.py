from __future__ import absolute_import

import json
from os import path

LOCALE = ''
POKEMON_NAMES = {}


def change_locale(set_locale):
    global LOCALE
    if set_locale != LOCALE:
        LOCALE = set_locale
        _load_all()


def _load_pokemon_names():
    _names_file = "pokemon"
    if LOCALE != '':
        _names_file += "." + LOCALE
    _names_file += ".json"

    _names_file_path = path.join(path.dirname(path.dirname(__file__)), "resources", "locales", _names_file)
    if not path.isfile(_names_file_path):
        return

    with open(_names_file_path) as json_file:
        POKEMON_NAMES.update(json.load(json_file))


def _load_all():
    _load_pokemon_names()


_load_all()
