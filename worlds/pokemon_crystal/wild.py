from collections import defaultdict
from dataclasses import replace
from typing import TYPE_CHECKING

from .data import FishData, TreeMonData, EncounterMon, WildRegionType, RockMonData
from .options import RandomizeWilds, EncounterGrouping, BreedingMethodsRequired
from .pokemon import get_random_pokemon, pokemon_convert_friendly_to_ids, get_priority_dexsanity

if TYPE_CHECKING:
    from . import PokemonCrystalWorld


def randomize_wild_pokemon(world: "PokemonCrystalWorld"):
    if world.options.randomize_wilds:

        world.generated_wooper = get_random_pokemon(world, exclude_unown=True)

        required_logical_pokemon = 0
        required_accessible_pokemon = 0
        required_inaccessible_pokemon = 0

        def encounter_list_count(encounters: list[EncounterMon]):
            if world.options.encounter_grouping == EncounterGrouping.option_all_split:
                return len(encounters)
            elif world.options.encounter_grouping == EncounterGrouping.option_one_per_method:
                return 1
            else:
                return len({encounter.pokemon for encounter in encounters})

        for region, wilds in world.generated_wild.grass.items():
            count = encounter_list_count(wilds.day)
            region_type = world.generated_wild_region_types[f"WildGrass_{region}"]
            if region_type is WildRegionType.InLogic:
                required_logical_pokemon += count
            elif region_type is WildRegionType.OutOfLogic:
                required_accessible_pokemon += count
            else:
                required_inaccessible_pokemon += count

        for region, wilds in world.generated_wild.water.items():
            count = encounter_list_count(wilds)
            region_type = world.generated_wild_region_types[f"WildWater_{region}"]
            if region_type is WildRegionType.InLogic:
                required_logical_pokemon += count
            elif region_type is WildRegionType.OutOfLogic:
                required_accessible_pokemon += count
            else:
                required_inaccessible_pokemon += count

        for region, wilds in world.generated_wild.fish.items():
            count = encounter_list_count(wilds.old) + encounter_list_count(wilds.good) + encounter_list_count(
                wilds.super)
            region_type = world.generated_wild_region_types[f"WildFish_{region}"]
            if region_type is WildRegionType.InLogic:
                required_logical_pokemon += count
            elif region_type is WildRegionType.OutOfLogic:
                required_accessible_pokemon += count
            else:
                required_inaccessible_pokemon += count

        for region, wilds in world.generated_wild.tree.items():
            count = encounter_list_count(wilds.common) + encounter_list_count(wilds.rare)
            region_type = world.generated_wild_region_types[f"WildTree_{region}"]
            if region_type is WildRegionType.InLogic:
                required_logical_pokemon += count
            elif region_type is WildRegionType.OutOfLogic:
                required_accessible_pokemon += count
            else:
                required_inaccessible_pokemon += count

        count = encounter_list_count(world.generated_wild.rock.encounters)
        region_type = world.generated_wild_region_types["WildRockSmash"]
        if region_type is WildRegionType.InLogic:
            required_logical_pokemon += count
        elif region_type is WildRegionType.OutOfLogic:
            required_accessible_pokemon += count
        else:
            required_inaccessible_pokemon += count

        logical_pokemon_pool = list[str]()
        accessible_pokemon_pool = list[str]()

        if world.options.randomize_wilds.value == RandomizeWilds.option_base_forms:
            logical_pokemon_pool.extend(
                pokemon_id for pokemon_id, pokemon_data in world.generated_pokemon.items() if pokemon_data.is_base)
        elif world.options.randomize_wilds.value == RandomizeWilds.option_evolution_lines:
            base_pokemon = [pokemon_id for pokemon_id, pokemon_data in world.generated_pokemon.items() if
                            pokemon_data.is_base]
            evo_lines = list[list[str]]()
            for base in base_pokemon:
                line = [base]
                for evo in world.generated_pokemon[base].evolutions:
                    line.append(evo.pokemon)
                    for evo2 in world.generated_pokemon[evo.pokemon].evolutions:
                        line.append(evo2.pokemon)
                evo_lines.append(line)

            logical_pokemon_pool.extend(world.random.choice(evo_line) for evo_line in evo_lines)
        elif world.options.randomize_wilds.option_catch_em_all:
            logical_pokemon_pool.extend(world.generated_pokemon.keys())

        logical_pokemon_pool.extend(get_priority_dexsanity(world))

        global_blocklist = pokemon_convert_friendly_to_ids(world, world.options.wild_encounter_blocklist)

        if global_blocklist:
            logical_pokemon_pool = [pokemon_id for pokemon_id in logical_pokemon_pool if
                                    pokemon_id not in global_blocklist]

        if len(logical_pokemon_pool) > required_logical_pokemon:
            world.random.shuffle(logical_pokemon_pool)
            accessible_pokemon_pool = logical_pokemon_pool[(len(accessible_pokemon_pool) - required_logical_pokemon):]
            logical_pokemon_pool = logical_pokemon_pool[:required_logical_pokemon]

        if len(logical_pokemon_pool) < required_logical_pokemon:
            logical_pokemon_pool.extend(get_random_pokemon(world, blocklist=global_blocklist) for _ in
                                        range(required_logical_pokemon - len(logical_pokemon_pool)))

        if (world.options.breeding_methods_required.value == BreedingMethodsRequired.option_with_ditto
                and "DITTO" not in logical_pokemon_pool):
            accessible_pokemon_pool.append(logical_pokemon_pool.pop())
            logical_pokemon_pool.append("DITTO")

        world.random.shuffle(logical_pokemon_pool)

        if len(accessible_pokemon_pool) > required_accessible_pokemon:
            accessible_pokemon_pool = accessible_pokemon_pool[:required_accessible_pokemon]

        if len(accessible_pokemon_pool) < required_accessible_pokemon:
            accessible_pokemon_pool.extend(get_random_pokemon(world, blocklist=global_blocklist) for _ in
                                           range(required_accessible_pokemon - len(accessible_pokemon_pool)))

        world.random.shuffle(accessible_pokemon_pool)

        inaccessible_pokemon_pool = [get_random_pokemon(world, blocklist=global_blocklist) for _ in
                                     range(required_inaccessible_pokemon)]

        world.random.shuffle(inaccessible_pokemon_pool)

        def get_pokemon_from_pool(pool: list[str], blocklist: set[str] | None = None,
                                  exclude_unown: bool = False) -> str:
            pokemon = pool.pop()
            if exclude_unown and pokemon == "UNOWN":
                pokemon = get_random_pokemon(world, exclude_unown=True, blocklist=global_blocklist)
            if blocklist and pokemon in blocklist:
                pokemon = get_random_pokemon(world, exclude_unown=exclude_unown, blocklist=blocklist | global_blocklist)
            return pokemon

        def randomize_encounter_list(region_id: str, encounter_list: list[EncounterMon], exclude_unown=False):

            region_type = world.generated_wild_region_types[region_id]
            if region_type is WildRegionType.InLogic:
                pokemon_pool = logical_pokemon_pool
            elif region_type is WildRegionType.OutOfLogic:
                pokemon_pool = accessible_pokemon_pool
            else:
                pokemon_pool = inaccessible_pokemon_pool

            new_encounters = list[EncounterMon]()
            if world.options.encounter_grouping.value == EncounterGrouping.option_one_per_method:
                pokemon = get_pokemon_from_pool(pokemon_pool, exclude_unown=exclude_unown)
                for encounter in encounter_list:
                    new_encounters.append(replace(encounter, pokemon=pokemon))

            elif world.options.encounter_grouping.value == EncounterGrouping.option_one_to_one:
                distribution = defaultdict[str, list[int]](lambda: [])
                new_encounters = [encounter for encounter in encounter_list]
                encounter_blocklist = set()
                for i, encounter in enumerate(encounter_list):
                    distribution[encounter.pokemon].append(i)
                for pokemon, slots in distribution.items():
                    pokemon = get_pokemon_from_pool(pokemon_pool, encounter_blocklist, exclude_unown=exclude_unown)
                    encounter_blocklist.add(pokemon)
                    for slot in slots:
                        new_encounters[slot] = replace(new_encounters[slot], pokemon=pokemon)
            else:
                encounter_blocklist = set()
                for encounter in encounter_list:
                    pokemon = get_pokemon_from_pool(pokemon_pool, encounter_blocklist, exclude_unown=exclude_unown)
                    encounter_blocklist.add(pokemon)
                    new_encounters.append(replace(encounter, pokemon=pokemon))

            if region_type is WildRegionType.InLogic:
                world.logically_available_pokemon.update(encounter.pokemon for encounter in new_encounters)
            return new_encounters

        for grass_name, grass_encounters in world.generated_wild.grass.items():
            encounters = randomize_encounter_list(f"WildGrass_{grass_name}", grass_encounters.morn)
            world.generated_wild.grass[grass_name] = replace(
                world.generated_wild.grass[grass_name],
                morn=encounters,
                day=encounters,
                nite=encounters
            )

        for water_name, water_encounters in world.generated_wild.water.items():
            world.generated_wild.water[water_name] = randomize_encounter_list(f"WildWater_{water_name}",
                                                                              water_encounters)

        for fish_name, fish_area in world.generated_wild.fish.items():
            region_id = f"WildFish_{fish_name}"
            world.generated_wild.fish[fish_name] = FishData(
                randomize_encounter_list(region_id, fish_area.old, exclude_unown=True),
                randomize_encounter_list(region_id, fish_area.good, exclude_unown=True),
                randomize_encounter_list(region_id, fish_area.super, exclude_unown=True)
            )

        for tree_name, tree_data in world.generated_wild.tree.items():
            region_id = f"WildTree_{tree_name}"
            world.generated_wild.tree[tree_name] = TreeMonData(
                randomize_encounter_list(region_id, tree_data.common, exclude_unown=True),
                randomize_encounter_list(region_id, tree_data.rare, exclude_unown=True)
            )

        world.generated_wild = replace(
            world.generated_wild,
            rock=RockMonData(
                randomize_encounter_list("WildRockSmash", world.generated_wild.rock.encounters)
            )
        )

        if logical_pokemon_pool: raise AssertionError(
            "Logical Pokemon pool is not empty, something went horribly wrong.")
        if accessible_pokemon_pool: raise AssertionError(
            "Accessible Pokemon pool is not empty, something went horribly wrong.")
        if inaccessible_pokemon_pool: raise AssertionError(
            "Inaccessible Pokemon pool is not empty, something went horribly wrong.")
    else:
        wild_pokemon = set()
        for region, wilds in world.generated_wild.grass.items():
            if world.generated_wild_region_types[f"WildGrass_{region}"] is WildRegionType.InLogic:
                wild_pokemon.update(wild.pokemon for wild in wilds.day)
        for region, wilds in world.generated_wild.water.items():
            if world.generated_wild_region_types[f"WildWater_{region}"] is WildRegionType.InLogic:
                wild_pokemon.update(wild.pokemon for wild in wilds)
        for region, wilds in world.generated_wild.fish.items():
            if world.generated_wild_region_types[f"WildFish_{region}"] is WildRegionType.InLogic:
                wild_pokemon.update(wild.pokemon for wild in wilds.old)
                wild_pokemon.update(wild.pokemon for wild in wilds.good)
                wild_pokemon.update(wild.pokemon for wild in wilds.super)
        for region, wilds in world.generated_wild.tree.items():
            if world.generated_wild_region_types[f"WildTree_{region}"] is WildRegionType.InLogic:
                wild_pokemon.update(wild.pokemon for wild in wilds.common)
                wild_pokemon.update(wild.pokemon for wild in wilds.rare)

        if world.generated_wild_region_types["WildRockSmash"] is WildRegionType.InLogic:
            wild_pokemon.update(wild.pokemon for wild in world.generated_wild.rock.encounters)

        world.logically_available_pokemon.update(wild_pokemon)


def randomize_static_pokemon(world: "PokemonCrystalWorld"):
    if world.options.randomize_static_pokemon:
        blocklist = pokemon_convert_friendly_to_ids(world, world.options.static_blocklist)
        for static_name, pkmn_data in world.generated_static.items():
            priority_pokemon = {poke for poke, data in world.generated_pokemon.items() if
                                data.is_base} if pkmn_data.level_type == "giveegg" else None
            world.generated_static[static_name] = replace(
                world.generated_static[static_name],
                pokemon=get_random_pokemon(world,
                                           exclude_unown=True,
                                           priority_pokemon=priority_pokemon,
                                           blocklist=blocklist),
            )
    else:  # Still randomize the Odd Egg
        pokemon = world.random.choice(["PICHU", "CLEFFA", "IGGLYBUFF", "SMOOCHUM", "MAGBY", "ELEKID", "TYROGUE"])
        world.generated_static["OddEgg"] = replace(world.generated_static["OddEgg"], pokemon=pokemon)

    world.logically_available_pokemon.update(
        static.pokemon for static in world.generated_static.values() if world.generated_wild_region_types[
            f"Static_{static.name}"] is WildRegionType.InLogic)
