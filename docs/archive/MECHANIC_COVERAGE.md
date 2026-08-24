> **HISTORIQUE — NE DÉCRIT PAS L'ÉTAT ACTUEL DU PROJET.** Consultez le [README principal](../../README.md) et l'[audit documentaire](../DOCUMENTATION_AUDIT.md).

# Mechanic Coverage

> Generated automatically by `pga-shootout coverage`. Do not edit manually.

## Summary

| Metric | Value |
|---|---:|
| Structural groups | 125 |
| Ability occurrences | 162 |
| Clubs represented | 88 |
| Groups mapped to a registered handler | 63 |
| Occurrence coverage | 53.09% |
| Club coverage | 63.64% |
| Interpreted groups | 63 |
| Unclassified groups | 0 |

Registered handlers: `add_stat, add_all_stats, dsl_pipeline`.

## Top 20 potential coverage gains

| Rank | Structural group | Mechanic | Occurrences | Clubs | Difficulty | Dependencies | Handler |
|---:|---|---|---:|---:|---|---|---|
| 1 | `terrain_resist_50` | uninterpreted | 6 | 6 | special | official_data_resolution | no |
| 2 | `power_shot` | uninterpreted | 4 | 4 | special | validated_geometry_or_physics | no |
| 3 | `boundary_bonus` | uninterpreted | 3 | 3 | special | validated_geometry_or_physics | no |
| 4 | `tree_bonus_x` | uninterpreted | 3 | 3 | special | validated_geometry_or_physics | no |
| 5 | `rocket_boosters` | uninterpreted | 2 | 2 | special | in_game_validation | no |
| 6 | `tree_bonus` | uninterpreted | 2 | 2 | special | validated_geometry_or_physics | no |
| 7 | `ability_mirror` | uninterpreted | 1 | 1 | stateful | validated_trigger_lifetime | no |
| 8 | `adventure` | uninterpreted | 1 | 1 | stateful | validated_trigger_lifetime | no |
| 9 | `alien_relic_left` | uninterpreted | 1 | 1 | special | in_game_validation | no |
| 10 | `alien_relic_right` | uninterpreted | 1 | 1 | special | in_game_validation | no |
| 11 | `alien_world` | uninterpreted | 1 | 1 | special | validated_geometry_or_physics | no |
| 12 | `aura_of_death` | uninterpreted | 1 | 1 | special | in_game_validation | no |
| 13 | `bag_tree_bonus` | uninterpreted | 1 | 1 | special | validated_geometry_or_physics | no |
| 14 | `bag_tree_passing` | uninterpreted | 1 | 1 | special | validated_geometry_or_physics | no |
| 15 | `bag_water_bonus` | uninterpreted | 1 | 1 | special | validated_geometry_or_physics | no |
| 16 | `bag_water_bounce` | uninterpreted | 1 | 1 | special | validated_geometry_or_physics | no |
| 17 | `bag_wind_power` | uninterpreted | 1 | 1 | special | in_game_validation | no |
| 18 | `beast_strength` | uninterpreted | 1 | 1 | special | random_or_transformation_model | no |
| 19 | `boundary_rush` | uninterpreted | 1 | 1 | special | validated_geometry_or_physics | no |
| 20 | `boundary_rush_75` | uninterpreted | 1 | 1 | special | validated_geometry_or_physics | no |

## Roadmap

### Remaining semantic qualification

Validate mechanic ID, complexity and dependencies for the 62 remaining uninterpreted groups in ranking order.

### Qualified coverage

63 qualified group(s) currently map to a registered handler. Uninterpreted groups are never treated as implementation-ready.

## Complete group coverage

| Rank | Group | Mechanic | Occurrences | Clubs | Club list | Coverage | Difficulty | Dependencies |
|---:|---|---|---:|---:|---|---:|---|---|
| 1 | `terrain_resist_50` | uninterpreted | 6 | 6 | Homecoming (`homecoming`), Dunecrawler (`dunecrawler`), Obelisk (`obelisk`), Hydroforce (`hydroforce`), Sandblast (`sandblast`), Windstrike (`windstrike`) | 0% | special | official_data_resolution |
| 2 | `power_shot` | uninterpreted | 4 | 4 | Dunecrawler (`dunecrawler`), Ember (`ember`), Flamethrower (`flamethrower`), Neon Impulse (`neon_impulse`) | 0% | special | validated_geometry_or_physics |
| 3 | `boundary_bonus` | uninterpreted | 3 | 3 | Edgewalker (`edgewalker`), Leviathan (`leviathan`), Windstrike (`windstrike`) | 0% | special | validated_geometry_or_physics |
| 4 | `tree_bonus_x` | uninterpreted | 3 | 3 | Huntsman (`huntsman`), Ironbark (`ironbark`), Oakheart (`oakheart`) | 0% | special | validated_geometry_or_physics |
| 5 | `rocket_boosters` | uninterpreted | 2 | 2 | Flashpoint (`flashpoint`), The Rocket (`the_rocket`) | 0% | special | in_game_validation |
| 6 | `tree_bonus` | uninterpreted | 2 | 2 | Edgewalker (`edgewalker`), Outset (`outset`) | 0% | special | validated_geometry_or_physics |
| 7 | `ability_mirror` | uninterpreted | 1 | 1 | Mimic (`mimic`) | 0% | stateful | validated_trigger_lifetime |
| 8 | `adventure` | uninterpreted | 1 | 1 | Homecoming (`homecoming`) | 0% | stateful | validated_trigger_lifetime |
| 9 | `alien_relic_left` | uninterpreted | 1 | 1 | Meteor (`meteor`) | 0% | special | in_game_validation |
| 10 | `alien_relic_right` | uninterpreted | 1 | 1 | Meteor (`meteor`) | 0% | special | in_game_validation |
| 11 | `alien_world` | uninterpreted | 1 | 1 | Meteor (`meteor`) | 0% | special | validated_geometry_or_physics |
| 12 | `aura_of_death` | uninterpreted | 1 | 1 | The Reaper (`the_reaper`) | 0% | special | in_game_validation |
| 13 | `bag_tree_bonus` | uninterpreted | 1 | 1 | The Seeker (`the_seeker`) | 0% | special | validated_geometry_or_physics |
| 14 | `bag_tree_passing` | uninterpreted | 1 | 1 | The Seeker (`the_seeker`) | 0% | special | validated_geometry_or_physics |
| 15 | `bag_water_bonus` | uninterpreted | 1 | 1 | Atlantis (`atlantis`) | 0% | special | validated_geometry_or_physics |
| 16 | `bag_water_bounce` | uninterpreted | 1 | 1 | Atlantis (`atlantis`) | 0% | special | validated_geometry_or_physics |
| 17 | `bag_wind_power` | uninterpreted | 1 | 1 | Jetstream (`jetstream`) | 0% | special | in_game_validation |
| 18 | `beast_strength` | uninterpreted | 1 | 1 | Chimera (`chimera`) | 0% | special | random_or_transformation_model |
| 19 | `boundary_rush` | uninterpreted | 1 | 1 | Flashpoint (`flashpoint`) | 0% | special | validated_geometry_or_physics |
| 20 | `boundary_rush_75` | uninterpreted | 1 | 1 | Skyfury (`skyfury`) | 0% | special | validated_geometry_or_physics |
| 21 | `brand_fairway_rush` | uninterpreted | 1 | 1 | Crusader (`crusader`) | 0% | special | physics_contract |
| 22 | `chains_into_itself` | uninterpreted | 1 | 1 | Sparky (`sparky`) | 0% | special | official_data_resolution |
| 23 | `electrodynamics_0_2ft` | uninterpreted | 1 | 1 | Sparky (`sparky`) | 0% | special | official_data_resolution |
| 24 | `emerald_rush_75` | uninterpreted | 1 | 1 | Green Demon (`green_demon`) | 0% | special | validated_geometry_or_physics |
| 25 | `fission` | uninterpreted | 1 | 1 | Supercollider (`supercollider`) | 0% | stateful | validated_trigger_lifetime |
| 26 | `flight_training` | uninterpreted | 1 | 1 | Eagle's Landing (`eagle_s_landing`) | 0% | special | validated_geometry_or_physics |
| 27 | `forester_power_elite` | uninterpreted | 1 | 1 | Ranger (`ranger`) | 0% | special | physics_contract |
| 28 | `gem_ball_bonus` | uninterpreted | 1 | 1 | Crystallize (`crystallize`) | 0% | special | in_game_validation |
| 29 | `gravity_reduction_x` | uninterpreted | 1 | 1 | Tierra Hueca (`tierra_hueca`) | 0% | stateful | validated_trigger_lifetime |
| 30 | `green_grip` | uninterpreted | 1 | 1 | Meanderer (`meanderer`) | 0% | special | validated_geometry_or_physics |
| 31 | `ground_rush` | uninterpreted | 1 | 1 | Hot Streak (`hot_streak`) | 0% | special | validated_geometry_or_physics |
| 32 | `hollow_earth` | uninterpreted | 1 | 1 | Tierra Hueca (`tierra_hueca`) | 0% | stateful | validated_trigger_lifetime |
| 33 | `home_turf_southwind` | uninterpreted | 1 | 1 | Ranger (`ranger`) | 0% | special | in_game_validation |
| 34 | `magnetism_0_15ft` | uninterpreted | 1 | 1 | Magnesis (`magnesis`) | 0% | special | official_data_resolution |
| 35 | `momentum` | uninterpreted | 1 | 1 | Rolling Stone (`rolling_stone`) | 0% | special | validated_geometry_or_physics |
| 36 | `palo_control_on_hit_x` | uninterpreted | 1 | 1 | Tierra Hueca (`tierra_hueca`) | 0% | stateful | validated_trigger_lifetime |
| 37 | `perfect_shot_bag_power` | uninterpreted | 1 | 1 | Flamethrower (`flamethrower`) | 0% | stateful | validated_trigger_lifetime |
| 38 | `perfect_shot_terrain_bonus_boost` | uninterpreted | 1 | 1 | Color Theory (`color_theory`) | 0% | stateful | validated_trigger_lifetime |
| 39 | `random_boost_x` | uninterpreted | 1 | 1 | Crystallize (`crystallize`) | 0% | special | random_or_transformation_model |
| 40 | `rough_boosters` | uninterpreted | 1 | 1 | Overgrowth (`overgrowth`) | 0% | special | in_game_validation |
| 41 | `sacrifice` | uninterpreted | 1 | 1 | The Reaper (`the_reaper`) | 0% | special | random_or_transformation_model |
| 42 | `scottsdale_boosters` | uninterpreted | 1 | 1 | Rising Flame (`rising_flame`) | 0% | special | in_game_validation |
| 43 | `shared_growth` | uninterpreted | 1 | 1 | Oakheart (`oakheart`) | 0% | special | in_game_validation |
| 44 | `shoreline_rush` | uninterpreted | 1 | 1 | Wave (`wave`) | 0% | special | validated_geometry_or_physics |
| 45 | `shuffle_up` | uninterpreted | 1 | 1 | Outlaw (`outlaw`) | 0% | special | random_or_transformation_model |
| 46 | `smoke_x` | uninterpreted | 1 | 1 | Catalyst (`catalyst`) | 0% | special | in_game_validation |
| 47 | `solidarity` | uninterpreted | 1 | 1 | Pantheon (`pantheon`) | 0% | special | in_game_validation |
| 48 | `sparks_x` | uninterpreted | 1 | 1 | Catalyst (`catalyst`) | 0% | special | in_game_validation |
| 49 | `stat_fusion` | uninterpreted | 1 | 1 | Fusion (`fusion`) | 0% | special | in_game_validation |
| 50 | `steam_x` | uninterpreted | 1 | 1 | Catalyst (`catalyst`) | 0% | special | in_game_validation |
| 51 | `super_fireball` | uninterpreted | 1 | 1 | Boomstick (`boomstick`) | 0% | special | in_game_validation |
| 52 | `terrain_bonus` | uninterpreted | 1 | 1 | Color Theory (`color_theory`) | 0% | special | in_game_validation |
| 53 | `three_heads` | uninterpreted | 1 | 1 | Chimera (`chimera`) | 0% | special | random_or_transformation_model |
| 54 | `tree_passing` | uninterpreted | 1 | 1 | Trailblazer (`trailblazer`) | 0% | special | validated_geometry_or_physics |
| 55 | `trumpet_blast` | uninterpreted | 1 | 1 | Fanfare (`fanfare`) | 0% | special | random_or_transformation_model |
| 56 | `volt_bounce` | uninterpreted | 1 | 1 | Rebound (`rebound`) | 0% | stateful | validated_trigger_lifetime |
| 57 | `water_bonus` | uninterpreted | 1 | 1 | Leviathan (`leviathan`) | 0% | special | validated_geometry_or_physics |
| 58 | `water_bonus_x` | uninterpreted | 1 | 1 | Hydroforce (`hydroforce`) | 0% | special | validated_geometry_or_physics |
| 59 | `water_rush` | uninterpreted | 1 | 1 | Leviathan (`leviathan`) | 0% | special | validated_geometry_or_physics |
| 60 | `wild_rush_speed` | uninterpreted | 1 | 1 | Explorer (`explorer`) | 0% | special | validated_geometry_or_physics |
| 61 | `wind_resistance_100` | uninterpreted | 1 | 1 | Stormbringer (`stormbringer`) | 0% | special | official_data_resolution |
| 62 | `wind_up_toy` | uninterpreted | 1 | 1 | XLR8R (`xlr8r`) | 0% | stateful | validated_trigger_lifetime |
| 63 | `adjacent_power` | `dsl_pipeline` | 2 | 2 | Outlaw (`outlaw`), Rampart (`rampart`) | 100% | parameterized | ordered_bag, source_club, ability_level_value, resolved_targets |
| 64 | `alloy` | `dsl_pipeline` | 1 | 1 | Ember (`ember`) | 100% | parameterized | ordered_bag, source_club, ability_level_value, resolved_targets |
| 65 | `bag_bounce_reduction` | `dsl_pipeline` | 1 | 1 | Maelstrom (`maelstrom`) | 100% | parameterized | ordered_bag, source_club, ability_level_value, club_type, resolved_targets, static_modifiers |
| 66 | `bag_control` | `dsl_pipeline` | 1 | 1 | Commonlaw (`commonlaw`) | 100% | parameterized | ordered_bag, source_club, ability_level_value, resolved_targets |
| 67 | `bag_loft_angle_10` | `dsl_pipeline` | 1 | 1 | Cloudcatcher (`cloudcatcher`) | 100% | parameterized | ordered_bag, source_club, ability_level_value, resolved_targets, static_modifiers |
| 68 | `bag_rarity_boost` | `dsl_pipeline` | 1 | 1 | Steadfast (`steadfast`) | 100% | parameterized | ordered_bag, club_rarity, source_club, ability_level_value, resolved_targets |
| 69 | `bag_recklessness` | `dsl_pipeline` | 1 | 1 | Into the Breach (`into_the_breach`) | 100% | parameterized | ordered_bag, source_club, ability_level_components, resolved_targets |
| 70 | `bag_rough_power` | `dsl_pipeline` | 1 | 1 | New Frontier (`new_frontier`) | 100% | parameterized | ordered_bag, source_club, ability_level_value |
| 71 | `bag_sand_bonus` | `dsl_pipeline` | 1 | 1 | Dunecrawler (`dunecrawler`) | 100% | parameterized | ordered_bag, source_club, ability_level_value |
| 72 | `bag_spin_bonus` | `dsl_pipeline` | 1 | 1 | Maelstrom (`maelstrom`) | 100% | parameterized | ordered_bag, source_club, ability_level_value, resolved_targets |
| 73 | `bag_wind_resist` | `dsl_pipeline` | 2 | 2 | Conspiracy (`conspiracy`), Rook (`rook`) | 100% | parameterized | ordered_bag, source_club, ability_level_value, resolved_targets, static_modifiers |
| 74 | `blazing_flight` | `dsl_pipeline` | 1 | 1 | Hot Streak (`hot_streak`) | 100% | parameterized | source_club, ability_level_value, terrain |
| 75 | `bounce_reduction` | `dsl_pipeline` | 1 | 1 | Cloudcatcher (`cloudcatcher`) | 100% | parameterized | ordered_bag, source_club, ability_level_value, resolved_targets, static_modifiers |
| 76 | `bounce_reduction_boost` | `dsl_pipeline` | 1 | 1 | Cyclotron (`cyclotron`) | 100% | parameterized | ordered_bag, source_club, ability_level_value, resolved_targets, static_modifiers |
| 77 | `brand_loyalty` | `dsl_pipeline` | 1 | 1 | Steward (`steward`) | 100% | parameterized | ordered_bag, source_club, club_brand, ability_level_value |
| 78 | `brand_loyalty_x` | `dsl_pipeline` | 20 | 20 | Cloudcatcher (`cloudcatcher`), Rook (`rook`), Trailblazer (`trailblazer`), Lodestar (`lodestar`), Lowball (`lowball`), Conqueror (`conqueror`), Into the Breach (`into_the_breach`), People's Champion (`people_s_champion`), Rampart (`rampart`), Saber (`saber`), Commonlaw (`commonlaw`), Crusader (`crusader`), Endeavor (`endeavor`), Groundskeep (`groundskeep`), Homestead (`homestead`), Kinship (`kinship`), Meanderer (`meanderer`), Rolling Stone (`rolling_stone`), Sandsend (`sandsend`), Steadfast (`steadfast`) | 100% | parameterized | ordered_bag, source_club, club_brand, ability_level_value |
| 79 | `chains_into_corvid` | `dsl_pipeline` | 1 | 1 | Conspiracy (`conspiracy`) | 100% | parameterized | ordered_bag, source_club, ability_level_value |
| 80 | `chains_into_irons_putters_wedges_drivers` | `dsl_pipeline` | 1 | 1 | Navigator (`navigator`) | 100% | parameterized | ordered_bag, source_club, ability_level_value |
| 81 | `chains_into_putters` | `dsl_pipeline` | 2 | 2 | Divebomb (`divebomb`), Conqueror (`conqueror`) | 100% | stateful | source_club, ability_level_value, pending_effects, current_club_type |
| 82 | `chains_into_wedges` | `dsl_pipeline` | 1 | 1 | Outset (`outset`) | 100% | stateful | source_club, ability_level_value, pending_effects, current_club_type |
| 83 | `chains_into_willoughsby` | `dsl_pipeline` | 1 | 1 | Kinship (`kinship`) | 100% | stateful | source_club, ability_level_value, pending_effects, current_club_brand |
| 84 | `chains_into_woods_hybrids` | `dsl_pipeline` | 1 | 1 | Navigator (`navigator`) | 100% | parameterized | ordered_bag, source_club, ability_level_value |
| 85 | `combined_power` | `dsl_pipeline` | 1 | 1 | Pantheon (`pantheon`) | 100% | parameterized | ordered_bag, source_club, ability_level_value |
| 86 | `combined_spin` | `dsl_pipeline` | 1 | 1 | Pantheon (`pantheon`) | 100% | parameterized | ordered_bag, source_club, ability_level_value |
| 87 | `control_boost` | `dsl_pipeline` | 1 | 1 | Galvanizer (`galvanizer`) | 100% | parameterized | ordered_bag, source_club, ability_level_value |
| 88 | `corvid_wind_resist` | `dsl_pipeline` | 1 | 1 | Divebomb (`divebomb`) | 100% | parameterized | ordered_bag, source_club, ability_level_value |
| 89 | `driver_loyalty` | `dsl_pipeline` | 1 | 1 | People's Champion (`people_s_champion`) | 100% | parameterized | ordered_bag, source_club, club_type, ability_level_value |
| 90 | `exclusion_zone` | `dsl_pipeline` | 1 | 1 | Earthquake (`earthquake`) | 100% | parameterized | ordered_bag, source_club, ability_level_value, official_club_types |
| 91 | `fade_draw_x2` | `dsl_pipeline` | 1 | 1 | Lodestar (`lodestar`) | 100% | parameterized | ordered_bag, source_club, ability_level_value, resolved_targets, static_modifiers |
| 92 | `fairway_affinity` | `dsl_pipeline` | 1 | 1 | Groundskeep (`groundskeep`) | 100% | parameterized | ordered_bag, source_club, ability_level_value |
| 93 | `fellowship` | `dsl_pipeline` | 1 | 1 | Steward (`steward`) | 100% | parameterized | ordered_bag, source_club, club_brand, ability_level_value, resolved_targets |
| 94 | `first_gear` | `dsl_pipeline` | 1 | 1 | Gearshift (`gearshift`) | 100% | parameterized | ordered_bag, source_club, ability_level_components |
| 95 | `forester_power` | `dsl_pipeline` | 1 | 1 | Ranger (`ranger`) | 100% | parameterized | ordered_bag, source_club, club_brand, ability_level_value, resolved_targets |
| 96 | `gravity_reduction` | `dsl_pipeline` | 1 | 1 | Into the Blue (`into_the_blue`) | 100% | parameterized | ordered_bag, source_club, ability_level_value |
| 97 | `groundspin_x3` | `dsl_pipeline` | 1 | 1 | Sidewinder (`sidewinder`) | 100% | parameterized | ordered_bag, source_club, ability_level_value |
| 98 | `groundspin_x4` | `dsl_pipeline` | 1 | 1 | Meanderer (`meanderer`) | 100% | parameterized | ordered_bag, source_club, ability_level_value |
| 99 | `iron_wedge_exclusion` | `dsl_pipeline` | 1 | 1 | Earthquake (`earthquake`) | 100% | parameterized | ordered_bag, source_club, ability_level_value, official_club_types |
| 100 | `loft_angle_10` | `dsl_pipeline` | 1 | 1 | Into the Blue (`into_the_blue`) | 100% | parameterized | ordered_bag, source_club, ability_level_value |
| 101 | `loft_angle_3` | `dsl_pipeline` | 1 | 1 | Rebound (`rebound`) | 100% | parameterized | ordered_bag, source_club, ability_level_value |
| 102 | `loft_angle_5` | `dsl_pipeline` | 1 | 1 | High Flight (`high_flight`) | 100% | parameterized | source_club, ability_level_value, resolved_targets, static_modifiers |
| 103 | `ludicrous_mode` | `dsl_pipeline` | 1 | 1 | XLR8R (`xlr8r`) | 100% | parameterized | ordered_bag, source_club, ability_level_value |
| 104 | `nautilus_boost` | `dsl_pipeline` | 1 | 1 | Wave (`wave`) | 100% | parameterized | ordered_bag, source_club, ability_level_value, resolved_targets |
| 105 | `off_green_power` | `dsl_pipeline` | 1 | 1 | Homecoming (`homecoming`) | 100% | parameterized | ordered_bag, source_club, ability_level_value |
| 106 | `overaim` | `dsl_pipeline` | 1 | 1 | Triumph (`triumph`) | 100% | parameterized | ordered_bag, source_club, ability_level_value |
| 107 | `overdrive` | `dsl_pipeline` | 1 | 1 | Triumph (`triumph`) | 100% | parameterized | ordered_bag, source_club, ability_level_value |
| 108 | `phoenix_power` | `dsl_pipeline` | 1 | 1 | Rising Flame (`rising_flame`) | 100% | parameterized | ordered_bag, source_club, club_brand, ability_level_value, resolved_targets |
| 109 | `plasma_arc_x` | `dsl_pipeline` | 1 | 1 | Sunstorm (`sunstorm`) | 100% | parameterized | ordered_bag, source_club, ability_level_value, unique_farthest_target, resolved_targets |
| 110 | `power_boost` | `dsl_pipeline` | 1 | 1 | Jumpstart (`jumpstart`) | 100% | parameterized | ordered_bag, source_club, ability_level_value |
| 111 | `rough_bonus` | `dsl_pipeline` | 1 | 1 | Bushwhacker (`bushwhacker`) | 100% | parameterized | ordered_bag, source_club, ability_level_value |
| 112 | `rough_power` | `dsl_pipeline` | 1 | 1 | Hero (`hero`) | 100% | parameterized | ordered_bag, source_club, ability_level_value |
| 113 | `sand_bonus` | `dsl_pipeline` | 1 | 1 | Sandblast (`sandblast`) | 100% | parameterized | ordered_bag, source_club, ability_level_value |
| 114 | `sand_bonus_x` | `dsl_pipeline` | 1 | 1 | Obelisk (`obelisk`) | 100% | parameterized | ordered_bag, source_club, ability_level_value |
| 115 | `sand_bounce` | `dsl_pipeline` | 1 | 1 | Mirage (`mirage`) | 100% | parameterized | source_club, ability_level_value, resolved_targets, static_modifiers |
| 116 | `spin_boost` | `dsl_pipeline` | 1 | 1 | Cyclotron (`cyclotron`) | 100% | parameterized | ordered_bag, source_club, ability_level_value |
| 117 | `stanchion_power` | `dsl_pipeline` | 1 | 1 | Saber (`saber`) | 100% | parameterized | ordered_bag, source_club, club_brand, ability_level_value, resolved_targets |
| 118 | `swing_speed_x2` | `dsl_pipeline` | 1 | 1 | Magnesis (`magnesis`) | 100% | parameterized | ordered_bag, source_club, ability_level_value |
| 119 | `tee_off_power` | `dsl_pipeline` | 1 | 1 | Sidewinder (`sidewinder`) | 100% | parameterized | source_club, ability_level_value, optional_terrain_context |
| 120 | `texas_tee` | `dsl_pipeline` | 1 | 1 | Blacksmith (`blacksmith`) | 100% | parameterized | source_club, ability_level_value, optional_terrain_context |
| 121 | `top_gear` | `dsl_pipeline` | 1 | 1 | Gearshift (`gearshift`) | 100% | parameterized | ordered_bag, source_club, ability_level_components |
| 122 | `water_bounce` | `dsl_pipeline` | 1 | 1 | Mirage (`mirage`) | 100% | parameterized | source_club, ability_level_value, resolved_targets, static_modifiers |
| 123 | `wind_resist` | `dsl_pipeline` | 2 | 2 | Into the Blue (`into_the_blue`), Obelisk (`obelisk`) | 100% | parameterized | ordered_bag, source_club, ability_level_value |
| 124 | `wind_resist_75` | `dsl_pipeline` | 1 | 1 | High Flight (`high_flight`) | 100% | parameterized | source_club, ability_level_value, resolved_targets, static_modifiers |
| 125 | `zephyr_x_mph` | `dsl_pipeline` | 1 | 1 | Stormbringer (`stormbringer`) | 100% | parameterized | ordered_bag, source_club, ability_level_value |
