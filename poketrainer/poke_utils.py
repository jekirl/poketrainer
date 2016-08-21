from __future__ import absolute_import

from library.api.pgoapi.protos.POGOProtos.Inventory import \
    Item_pb2 as Enum_Items
from library.api.pgoapi.protos.POGOProtos.Networking import \
    Responses_pb2 as Enum_Responses
from poketrainer.pokemon import Pokemon


def get_item_name(s_item_id):
    available_items = Enum_Items.ItemId.DESCRIPTOR.values_by_number.items()
    for (item_id, item) in available_items:
        if item_id == s_item_id:
            return item.name.replace('ITEM_', '', 1)
    return 'Unknown'


def get_response_text(request, field, value):
    # convert snake_case to CamelCase and add '*Response'
    # example: nickname_pokemon = NicknamePokemonResponse
    request = request.lower().split('_')
    request = "".join(x.title() for x in request) + 'Response'
    # read descriptor
    try:
        response = Enum_Responses.DESCRIPTOR.\
            message_types_by_name[request].\
            fields_by_name[field].enum_type.\
            values_by_number.items()
        # search value
        for (number, field) in response:
            if number == value:
                return field.name
    except Exception as e:
        return 'TXT not found: ' + str(e)
    return 'TXT not found'


def pokemon_iv_percentage(pokemon):
    return ((pokemon.get('individual_attack', 0) + pokemon.get('individual_stamina', 0) + pokemon.get(
        'individual_defense', 0) + 0.0) / 45.0) * 100.0


def create_capture_probability(capture_probability):
    capture_balls = capture_probability.get('pokeball_type', [])
    capture_rate = capture_probability.get('capture_probability', [])
    if not capture_probability or not capture_rate or len(capture_balls) != len(capture_rate):
        return None
    else:
        return dict(zip(capture_balls, capture_rate))


def get_pokemon_by_long_id(pokemon_id, res):
    for inventory_item in res:
        pokemon_data = inventory_item['inventory_item_data'].get('pokemon_data', {})
        if not pokemon_data.get('is_egg', False) and str(pokemon_data.get('id', 'NA')) == str(pokemon_id):
            return Pokemon(pokemon_data)
    return None

DISK_ENCOUNTER = {0: "UNKNOWN",
                  1: "SUCCESS",
                  2: "NOT_AVAILABLE",
                  3: "NOT_IN_RANGE",
                  4: "ENCOUNTER_ALREADY_FINISHED"}
