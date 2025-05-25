from collections import defaultdict
from typing import TYPE_CHECKING

from .data import FishData, TreeMonData, EncounterMon
from .options import RandomizeWilds, EncounterGrouping, BreedingMethodsRequired
from .pokemon import get_random_pokemon

if TYPE_CHECKING:
    from . import PokemonCrystalWorld


def randomize_wild_pokemon(world: "PokemonCrystalWorld"):
    if world.options.randomize_wilds:
        priority_pokemon = set()

        if world.options.randomize_wilds.value == RandomizeWilds.option_catch_em_all:
            priority_pokemon = set(world.generated_pokemon.keys())
        elif world.options.randomize_wilds.value == RandomizeWilds.option_base_forms:
            priority_pokemon = set([pokemon_id for pokemon_id, pokemon_data in world.generated_pokemon.items() if
                                    pokemon_data.is_base])

        world.generated_wooper = get_random_pokemon(world, exclude_unown=True)

        if world.options.breeding_methods_required.value == BreedingMethodsRequired.option_with_ditto:
            priority_pokemon |= {"DITTO"}  # Ensure Ditto appears in the wild at least once if required for breeding

        def randomize_encounter_list(encounter_list: list[EncounterMon], exclude_unown=False):
            new_encounters = list[EncounterMon]()
            if world.options.encounter_grouping.value == EncounterGrouping.option_one_per_method:
                pokemon = get_random_pokemon(world, priority_pokemon=priority_pokemon, exclude_unown=exclude_unown)
                priority_pokemon.discard(pokemon)
                for encounter in encounter_list:
                    new_encounters.append(encounter._replace(pokemon=pokemon))
            elif world.options.encounter_grouping.value == EncounterGrouping.option_one_to_one:
                distribution = defaultdict[str, list[int]](lambda: [])
                new_encounters = [encounter for encounter in encounter_list]
                for i, encounter in enumerate(encounter_list):
                    distribution[encounter.pokemon] += [i]
                for pokemon, slots in distribution.items():
                    pokemon = get_random_pokemon(world, priority_pokemon=priority_pokemon, exclude_unown=exclude_unown)
                    priority_pokemon.discard(pokemon)
                    for slot in slots:
                        new_encounters[slot] = new_encounters[slot]._replace(pokemon=pokemon)
            else:
                for encounter in encounter_list:
                    pokemon = get_random_pokemon(world, priority_pokemon=priority_pokemon, exclude_unown=exclude_unown)
                    priority_pokemon.discard(pokemon)
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

    wild_pokemon = set()

    for region, wilds in world.generated_wild.grass.items():
        if f"WildGrass_{region}" in world.available_wild_regions:
            for wild in wilds:
                wild_pokemon.add(wild.pokemon)
    for region, wilds in world.generated_wild.water.items():
        if f"WildWater_{region}" in world.available_wild_regions:
            for wild in wilds:
                wild_pokemon.add(wild.pokemon)
    for region, wilds in world.generated_wild.fish.items():
        if f"WildFish_{region}" in world.available_wild_regions:
            for wild in wilds.old:
                wild_pokemon.add(wild.pokemon)
            for wild in wilds.good:
                wild_pokemon.add(wild.pokemon)
            for wild in wilds.super:
                wild_pokemon.add(wild.pokemon)
    for region, wilds in world.generated_wild.tree.items():
        region_id = "WildRockSmash" if region == "Rock" else f"WildTree_{region}"
        if region_id in world.available_wild_regions:
            for wild in wilds.common:
                wild_pokemon.add(wild.pokemon)
            if region != "Rock":
                for wild in wilds.rare:
                    wild_pokemon.add(wild.pokemon)

    world.logically_available_pokemon |= wild_pokemon


def randomize_static_pokemon(world: "PokemonCrystalWorld"):
    if world.options.randomize_static_pokemon:
        for static_name, pkmn_data in world.generated_static.items():
            world.generated_static[static_name] = pkmn_data._replace(
                pokemon=get_random_pokemon(world, exclude_unown=True))

    static_pokemon = set()

    for static in world.generated_static.values():
        if f"Static_{static.name}" in world.available_wild_regions:
            static_pokemon.add(static.pokemon)

    world.logically_available_pokemon |= static_pokemon
