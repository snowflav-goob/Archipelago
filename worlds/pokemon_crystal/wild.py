from typing import TYPE_CHECKING

from .data import FishData, TreeMonData, EncounterMon
from .options import RandomizeWilds
from .pokemon import get_random_pokemon

if TYPE_CHECKING:
    from . import PokemonCrystalWorld


def randomize_wild_pokemon(world: "PokemonCrystalWorld"):
    priority_list = set()

    if world.options.randomize_wilds.value == RandomizeWilds.option_catch_em_all:
        priority_list = set(world.generated_pokemon.keys())

    world.generated_wooper = get_random_pokemon(world, exclude_unown=True)

    def randomize_encounter_list(encounter_list: list[EncounterMon], exclude_unown=False):
        new_encounters = []
        for encounter in encounter_list:
            pokemon = get_random_pokemon(world, priority_list=priority_list, exclude_unown=exclude_unown)
            priority_list.discard(pokemon)
            new_encounters.append(encounter._replace(pokemon=pokemon))
        return new_encounters

    for grass_name, grass_encounters in world.generated_wild.grass.items():
        world.generated_wild.grass[grass_name] = randomize_encounter_list(grass_encounters)

    for water_name, water_encounters in world.generated_wild.water.items():
        world.generated_wild.water[water_name] = randomize_encounter_list(water_encounters)

    for fish_name, fish_area in world.generated_wild.fish.items():
        world.generated_wild.fish[fish_name] = FishData(
            randomize_encounter_list(fish_area.old, exclude_unown=True),
            randomize_encounter_list(fish_area.good, exclude_unown=True),
            randomize_encounter_list(fish_area.super, exclude_unown=True)
        )

    for tree_name, tree_data in world.generated_wild.tree.items():
        world.generated_wild.tree[tree_name] = TreeMonData(
            randomize_encounter_list(tree_data.common, exclude_unown=True),
            randomize_encounter_list(tree_data.rare, exclude_unown=True)
        )


def randomize_static_pokemon(world: "PokemonCrystalWorld"):
    for static_name, pkmn_data in world.generated_static.items():
        world.generated_static[static_name] = pkmn_data._replace(pokemon=get_random_pokemon(world, exclude_unown=True))
