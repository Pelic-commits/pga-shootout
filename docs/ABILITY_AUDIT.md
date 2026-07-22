# PGA TOUR Golf Shootout — Audit de normalisation V2

## Résultat

- Clubs capturés et normalisés : **88 / 88**
- Marques : **9**
- Capacités présentes sur les clubs : **162 occurrences**
- Intitulés uniques : **125**
- Variantes officielles uniques (intitulé + description + icône) : **156**
- Valeurs de tableau converties : **1333 / 1333**
- Valeurs non reconnues : **0**
- Capacités non classées : **0**

> La couche officielle conserve les textes et valeurs du site. La couche sémantique est une interprétation structurée qui reste à valider par des tests dans le jeu.

## Architecture

- `clubs_official.json` : métadonnées, statistiques par niveau et valeurs officielles des capacités.
- `ability_occurrences.json` : une occurrence par capacité et par club, avec texte officiel, valeurs typées et interprétation sémantique.
- `ability_labels.json` : regroupement des 125 intitulés affichés.
- `mechanics_catalog.json` : regroupement des occurrences en effets génériques.
- `semantic_map.json` : carte sémantique stable utilisée pour contrôler les futures mises à jour.
- `assets.json` : correspondance entre icônes, intitulés et familles.
- `normalization_report.json` : contrôles, couverture et points à revoir.

## Familles sémantiques

| Famille | Occurrences |
|---|---:|
| `adjacency_scaling` | 25 |
| `trajectory` | 20 |
| `terrain_bonus` | 20 |
| `stat_modifier` | 14 |
| `terrain_interaction` | 13 |
| `wind` | 11 |
| `chain` | 8 |
| `position` | 7 |
| `ability_modification` | 6 |
| `shot_control` | 6 |
| `stateful_growth` | 5 |
| `random` | 4 |
| `adjacency` | 4 |
| `stat_copy` | 4 |
| `bag_position` | 3 |
| `composition_scaling` | 3 |
| `course_condition` | 2 |
| `previous_shot` | 2 |
| `composition_condition` | 2 |
| `transform` | 2 |
| `identity` | 1 |

## Complexité prévue pour le moteur

| Niveau | Occurrences | Interprétation |
|---|---:|---|
| `generic` | 79 | Opération réutilisable directe. |
| `parameterized` | 54 | Opération générique avec cible, filtre ou condition. |
| `stateful` | 18 | Dépend de l’historique du trou, du coup ou de la partie. |
| `special` | 11 | Transformation, hasard ou copie nécessitant une règle dédiée. |

## Points officiels à vérifier

- **official_description_table_mismatch** — La description officielle annonce +2 à toutes les statistiques, alors que le tableau contient +6 puis +7.
- **official_label_table_mismatch** — L’intitulé et la description annoncent 100 %, tandis que le tableau officiel indique 85 % au niveau 12.
- **official_unit_mismatch** — L’intitulé et la description utilisent les pieds (ft), tandis que le tableau affiche des mètres (m).
- **official_unit_mismatch** — L’intitulé et la description utilisent les pieds (ft), tandis que le tableau affiche des mètres (m).
- **official_description_typo** — La description officielle contient « gains % » sans valeur ou variable avant le symbole %.
- **official_label_evolves_with_levels** — L’intitulé mentionne 50 %, mais plusieurs tableaux montent au-delà de 50 %. Les valeurs de tableau sont conservées comme référence par niveau.
- **formatting_inconsistency** — La valeur Elite est écrite « 3 » sans signe +, contrairement aux autres niveaux.

## Catalogue des effets

| Effet | Famille(s) | Occurrences | Exemples |
|---|---|---:|---|
| `add_stat` | `position`, `stat_modifier` | 15 | Forester Power, Forester Power (Elite) |
| `add_stats` | `position` | 1 | Plasma Arc +X |
| `add_stats_next_shot` | `chain` | 8 | Chains into Corvid, Chains into Putters |
| `adjacent_stat_bonus_with_filter_multiplier` | `adjacency` | 1 | Fellowship |
| `aim_arrow_speed_multiplier` | `shot_control` | 1 | Swing Speed x2 |
| `bag_stat_and_trajectory_modifier` | `bag_position` | 2 | First Gear, Top Gear |
| `bag_stat_bonus_if_absent_types` | `composition_condition` | 1 | Exclusion Zone |
| `bag_stat_tradeoff_after_source` | `previous_shot` | 1 | Hollow Earth |
| `bounce_reduction` | `position`, `trajectory` | 3 | Bounce Reduction, Bag Bounce Reduction |
| `brand_control_increase_on_hit` | `stateful_growth` | 1 | Palo Control On Hit +X |
| `conditional_stat_bonus` | `terrain_bonus` | 20 | Boundary Bonus, Tree Bonus |
| `control_per_airtime` | `stateful_growth` | 1 | Flight Training |
| `copy_adjacent_stat_percent` | `stat_copy` | 2 | Rocket Boosters, Rocket Boosters |
| `copy_directional_stats_percent` | `stat_copy` | 1 | Stat Fusion |
| `copy_last_used_club_abilities` | `ability_modification` | 1 | Ability Mirror |
| `counts_as_all_brands` | `identity` | 1 | Solidarity |
| `destroy_random_club_and_steal_stats` | `random` | 1 | Sacrifice |
| `duplicate_ability_instances` | `ability_modification` | 2 | Alien Relic (Left), Alien Relic (Right) |
| `fade_draw_multiplier` | `shot_control` | 1 | Fade/Draw x2 |
| `first_hazard_or_tree_event_stat_growth` | `stateful_growth` | 1 | Adventure |
| `gem_ball_bonus_multiplier` | `ability_modification` | 1 | Gem Ball Bonus |
| `grant_source_base_stats_to_replacements` | `transform` | 1 | Beast Strength |
| `gravity_reduction` | `bag_position` | 1 | Gravity Reduction |
| `groundspin_multiplier` | `trajectory` | 2 | Groundspin x3, Groundspin x4 |
| `hole_magnetism_radius` | `trajectory` | 2 | Magnetism 0.15ft, Electrodynamics 0.2ft |
| `loft_angle_delta` | `trajectory` | 4 | Bag Loft Angle +10°, Loft Angle +5° |
| `multi_stat_tradeoff` | `stat_modifier` | 1 | Bag Recklessness |
| `mutual_adjacent_stat_bonus` | `adjacency` | 3 | Smoke +X, Steam +X |
| `named_ability_multiplier_on_course` | `course_condition` | 2 | Home Turf: Southwind, Scottsdale Boosters |
| `named_ability_value_multiplier` | `ability_modification` | 1 | Super Fireball |
| `power_per_ground_roll_time` | `stateful_growth` | 1 | Momentum |
| `power_per_wind_speed` | `wind` | 1 | Bag Wind Power |
| `pullback_power_tradeoff` | `shot_control` | 4 | Power Shot, Power Shot |
| `random_stat_bonus` | `random` | 2 | Random Boost +X, Trumpet Blast |
| `replace_source_with_random_clubs` | `transform` | 1 | Three Heads |
| `self_stat_bonus_if_absent_types` | `composition_condition` | 1 | Iron + Wedge Exclusion |
| `self_stat_per_adjacent_filter` | `adjacency_scaling` | 22 | Brand Loyalty +X, Brand Loyalty +X |
| `self_stats_increase_after_hit` | `stateful_growth` | 1 | Fission |
| `share_named_ability_with_adjacent` | `ability_modification` | 1 | Shared Growth |
| `share_source_stats_percent` | `stat_copy` | 1 | Aura of Death |
| `shuffle_bag_positions` | `random` | 1 | Shuffle Up |
| `source_and_each_matching_adjacent_stat_bonus` | `adjacency_scaling` | 1 | Nautilus Boost |
| `source_and_each_matching_club_stat_bonus` | `composition_scaling` | 1 | Alloy |
| `source_and_type_stat_per_type_count` | `composition_scaling` | 2 | Overdrive, Overaim |
| `speed_and_distance_modifier_over_terrain` | `trajectory` | 8 | Boundary Rush 75%, Wild Rush Speed |
| `speed_reduction_over_terrain` | `trajectory` | 1 | Green Grip |
| `stacking_gravity_reduction` | `trajectory` | 1 | Gravity Reduction X% |
| `stat_per_adjacent_same_brand` | `adjacency_scaling` | 2 | Combined Power, Combined Spin |
| `tee_stat_bonus` | `stat_modifier` | 3 | Tee Off Power, Blazing Flight |
| `terrain_bonus_boost_after_perfect` | `previous_shot` | 1 | Perfect Shot - Terrain Bonus Boost |
| `terrain_bounce` | `terrain_interaction` | 4 | Bag Water Bounce, Sand Bounce |
| `terrain_bounce_then_bag_bonus` | `terrain_interaction` | 1 | Volt Bounce |
| `terrain_penalty_resistance` | `terrain_interaction` | 6 | Terrain Resist +50%, Terrain Resist +50% |
| `tree_passing` | `terrain_interaction` | 2 | Bag Tree Passing, Tree Passing |
| `wind_resistance` | `wind` | 7 | Bag Wind Resist, Corvid Wind Resist |
| `wind_toward_hole` | `wind` | 3 | Zephyr +X mph, Wind-Up Toy |

## Audit des intitulés

| Intitulé officiel | Occurrences | Famille / effet | Clubs exemples |
|---|---:|---|---|
| Ability Mirror | 1 | `ability_modification` / `copy_last_used_club_abilities` | Mimic |
| Adjacent Power | 2 | `position` / `add_stat` | Outlaw, Rampart |
| Adventure | 1 | `stateful_growth` / `first_hazard_or_tree_event_stat_growth` | Homecoming |
| Alien Relic (Left) | 1 | `ability_modification` / `duplicate_ability_instances` | Meteor |
| Alien Relic (Right) | 1 | `ability_modification` / `duplicate_ability_instances` | Meteor |
| Alien World | 1 | `terrain_interaction` / `terrain_bounce` | Meteor |
| Alloy | 1 | `composition_scaling` / `source_and_each_matching_club_stat_bonus` | Ember |
| Aura of Death | 1 | `stat_copy` / `share_source_stats_percent` | The Reaper |
| Bag Bounce Reduction | 1 | `trajectory` / `bounce_reduction` | Maelstrom |
| Bag Control | 1 | `stat_modifier` / `add_stat` | Commonlaw |
| Bag Loft Angle +10° | 1 | `trajectory` / `loft_angle_delta` | Cloudcatcher |
| Bag: Rarity Boost | 1 | `stat_modifier` / `add_stat` | Steadfast |
| Bag Recklessness | 1 | `stat_modifier` / `multi_stat_tradeoff` | Into the Breach |
| Bag Rough Power | 1 | `stat_modifier` / `add_stat` | New Frontier |
| Bag Sand Bonus | 1 | `stat_modifier` / `add_stat` | Dunecrawler |
| Bag Spin Bonus | 1 | `stat_modifier` / `add_stat` | Maelstrom |
| Bag Tree Bonus | 1 | `terrain_bonus` / `conditional_stat_bonus` | The Seeker |
| Bag Tree Passing | 1 | `terrain_interaction` / `tree_passing` | The Seeker |
| Bag Water Bonus | 1 | `terrain_bonus` / `conditional_stat_bonus` | Atlantis |
| Bag Water Bounce | 1 | `terrain_interaction` / `terrain_bounce` | Atlantis |
| Bag Wind Power | 1 | `wind` / `power_per_wind_speed` | Jetstream |
| Bag Wind Resist | 2 | `wind` / `wind_resistance` | Conspiracy, Rook |
| Beast Strength | 1 | `transform` / `grant_source_base_stats_to_replacements` | Chimera |
| Blazing Flight | 1 | `stat_modifier` / `tee_stat_bonus` | Hot Streak |
| Bounce Reduction | 1 | `trajectory` / `bounce_reduction` | Cloudcatcher |
| Bounce Reduction Boost | 1 | `position` / `bounce_reduction` | Cyclotron |
| Boundary Bonus | 3 | `terrain_bonus` / `conditional_stat_bonus` | Edgewalker, Leviathan, Windstrike |
| Boundary Rush | 1 | `trajectory` / `speed_and_distance_modifier_over_terrain` | Flashpoint |
| Boundary Rush 75% | 1 | `trajectory` / `speed_and_distance_modifier_over_terrain` | Skyfury |
| Brand Fairway Rush | 1 | `trajectory` / `speed_and_distance_modifier_over_terrain` | Crusader |
| Brand Loyalty | 1 | `adjacency_scaling` / `self_stat_per_adjacent_filter` | Steward |
| Brand Loyalty +X | 20 | `adjacency_scaling` / `self_stat_per_adjacent_filter` | Cloudcatcher, Rook, Trailblazer, Lodestar… |
| Chains into Corvid | 1 | `chain` / `add_stats_next_shot` | Conspiracy |
| Chains into Irons + Putters + Wedges + Drivers | 1 | `chain` / `add_stats_next_shot` | Navigator |
| Chains into Itself | 1 | `chain` / `add_stats_next_shot` | Sparky |
| Chains into Putters | 2 | `chain` / `add_stats_next_shot` | Divebomb, Conqueror |
| Chains into Wedges | 1 | `chain` / `add_stats_next_shot` | Outset |
| Chains into Willoughsby | 1 | `chain` / `add_stats_next_shot` | Kinship |
| Chains into Woods + Hybrids | 1 | `chain` / `add_stats_next_shot` | Navigator |
| Combined Power | 1 | `adjacency_scaling` / `stat_per_adjacent_same_brand` | Pantheon |
| Combined Spin | 1 | `adjacency_scaling` / `stat_per_adjacent_same_brand` | Pantheon |
| Control Boost | 1 | `position` / `add_stat` | Galvanizer |
| Corvid Wind Resist | 1 | `wind` / `wind_resistance` | Divebomb |
| Driver Loyalty | 1 | `adjacency_scaling` / `self_stat_per_adjacent_filter` | People's Champion |
| Electrodynamics 0.2ft | 1 | `trajectory` / `hole_magnetism_radius` | Sparky |
| Emerald Rush 75% | 1 | `trajectory` / `speed_and_distance_modifier_over_terrain` | Green Demon |
| Exclusion Zone | 1 | `composition_condition` / `bag_stat_bonus_if_absent_types` | Earthquake |
| Fade/Draw x2 | 1 | `shot_control` / `fade_draw_multiplier` | Lodestar |
| Fairway Affinity | 1 | `terrain_bonus` / `conditional_stat_bonus` | Groundskeep |
| Fellowship | 1 | `adjacency` / `adjacent_stat_bonus_with_filter_multiplier` | Steward |
| First Gear | 1 | `bag_position` / `bag_stat_and_trajectory_modifier` | Gearshift |
| Fission | 1 | `stateful_growth` / `self_stats_increase_after_hit` | Supercollider |
| Flight Training | 1 | `stateful_growth` / `control_per_airtime` | Eagle's Landing |
| Forester Power | 1 | `stat_modifier` / `add_stat` | Ranger |
| Forester Power (Elite) | 1 | `stat_modifier` / `add_stat` | Ranger |
| Gem Ball Bonus | 1 | `ability_modification` / `gem_ball_bonus_multiplier` | Crystallize |
| Gravity Reduction | 1 | `bag_position` / `gravity_reduction` | Into the Blue |
| Gravity Reduction X% | 1 | `trajectory` / `stacking_gravity_reduction` | Tierra Hueca |
| Green Grip | 1 | `trajectory` / `speed_reduction_over_terrain` | Meanderer |
| Ground Rush | 1 | `trajectory` / `speed_and_distance_modifier_over_terrain` | Hot Streak |
| Groundspin x3 | 1 | `trajectory` / `groundspin_multiplier` | Sidewinder |
| Groundspin x4 | 1 | `trajectory` / `groundspin_multiplier` | Meanderer |
| Hollow Earth | 1 | `previous_shot` / `bag_stat_tradeoff_after_source` | Tierra Hueca |
| Home Turf: Southwind | 1 | `course_condition` / `named_ability_multiplier_on_course` | Ranger |
| Iron + Wedge Exclusion | 1 | `composition_condition` / `self_stat_bonus_if_absent_types` | Earthquake |
| Loft Angle +10° | 1 | `trajectory` / `loft_angle_delta` | Into the Blue |
| Loft Angle -3° | 1 | `trajectory` / `loft_angle_delta` | Rebound |
| Loft Angle +5° | 1 | `trajectory` / `loft_angle_delta` | High Flight |
| Ludicrous Mode | 1 | `wind` / `wind_toward_hole` | XLR8R |
| Magnetism 0.15ft | 1 | `trajectory` / `hole_magnetism_radius` | Magnesis |
| Momentum | 1 | `stateful_growth` / `power_per_ground_roll_time` | Rolling Stone |
| Nautilus Boost | 1 | `adjacency_scaling` / `source_and_each_matching_adjacent_stat_bonus` | Wave |
| Off-Green Power | 1 | `terrain_bonus` / `conditional_stat_bonus` | Homecoming |
| Overaim | 1 | `composition_scaling` / `source_and_type_stat_per_type_count` | Triumph |
| Overdrive | 1 | `composition_scaling` / `source_and_type_stat_per_type_count` | Triumph |
| Palo Control On Hit +X | 1 | `stateful_growth` / `brand_control_increase_on_hit` | Tierra Hueca |
| Perfect Shot: Bag Power | 1 | `stat_modifier` / `add_stat` | Flamethrower |
| Perfect Shot - Terrain Bonus Boost | 1 | `previous_shot` / `terrain_bonus_boost_after_perfect` | Color Theory |
| Phoenix Power | 1 | `stat_modifier` / `add_stat` | Rising Flame |
| Plasma Arc +X | 1 | `position` / `add_stats` | Sunstorm |
| Power Boost | 1 | `position` / `add_stat` | Jumpstart |
| Power Shot | 4 | `shot_control` / `pullback_power_tradeoff` | Dunecrawler, Ember, Flamethrower, Neon Impulse |
| Random Boost +X | 1 | `random` / `random_stat_bonus` | Crystallize |
| Rocket Boosters | 2 | `stat_copy` / `copy_adjacent_stat_percent` | Flashpoint, The Rocket |
| Rough Bonus | 1 | `terrain_bonus` / `conditional_stat_bonus` | Bushwhacker |
| Rough Boosters | 1 | `terrain_bonus` / `conditional_stat_bonus` | Overgrowth |
| Rough Power | 1 | `terrain_bonus` / `conditional_stat_bonus` | Hero |
| Sacrifice | 1 | `random` / `destroy_random_club_and_steal_stats` | The Reaper |
| Sand Bonus | 1 | `terrain_bonus` / `conditional_stat_bonus` | Sandblast |
| Sand Bonus +X | 1 | `terrain_bonus` / `conditional_stat_bonus` | Obelisk |
| Sand Bounce | 1 | `terrain_interaction` / `terrain_bounce` | Mirage |
| Scottsdale Boosters | 1 | `course_condition` / `named_ability_multiplier_on_course` | Rising Flame |
| Shared Growth | 1 | `ability_modification` / `share_named_ability_with_adjacent` | Oakheart |
| Shoreline Rush | 1 | `trajectory` / `speed_and_distance_modifier_over_terrain` | Wave |
| Shuffle Up | 1 | `random` / `shuffle_bag_positions` | Outlaw |
| Smoke +X | 1 | `adjacency` / `mutual_adjacent_stat_bonus` | Catalyst |
| Solidarity | 1 | `identity` / `counts_as_all_brands` | Pantheon |
| Sparks +X | 1 | `adjacency` / `mutual_adjacent_stat_bonus` | Catalyst |
| Spin Boost | 1 | `position` / `add_stat` | Cyclotron |
| Stanchion Power | 1 | `stat_modifier` / `add_stat` | Saber |
| Stat Fusion | 1 | `stat_copy` / `copy_directional_stats_percent` | Fusion |
| Steam +X | 1 | `adjacency` / `mutual_adjacent_stat_bonus` | Catalyst |
| Super Fireball | 1 | `ability_modification` / `named_ability_value_multiplier` | Boomstick |
| Swing Speed x2 | 1 | `shot_control` / `aim_arrow_speed_multiplier` | Magnesis |
| Tee Off Power | 1 | `stat_modifier` / `tee_stat_bonus` | Sidewinder |
| Terrain Bonus | 1 | `terrain_bonus` / `conditional_stat_bonus` | Color Theory |
| Terrain Resist +50% | 6 | `terrain_interaction` / `terrain_penalty_resistance` | Homecoming, Dunecrawler, Obelisk, Hydroforce… |
| Texas Tee | 1 | `stat_modifier` / `tee_stat_bonus` | Blacksmith |
| Three Heads | 1 | `transform` / `replace_source_with_random_clubs` | Chimera |
| Top Gear | 1 | `bag_position` / `bag_stat_and_trajectory_modifier` | Gearshift |
| Tree Bonus | 2 | `terrain_bonus` / `conditional_stat_bonus` | Edgewalker, Outset |
| Tree Bonus +X | 3 | `terrain_bonus` / `conditional_stat_bonus` | Huntsman, Ironbark, Oakheart |
| Tree Passing | 1 | `terrain_interaction` / `tree_passing` | Trailblazer |
| Trumpet Blast | 1 | `random` / `random_stat_bonus` | Fanfare |
| Volt Bounce | 1 | `terrain_interaction` / `terrain_bounce_then_bag_bonus` | Rebound |
| Water Bonus | 1 | `terrain_bonus` / `conditional_stat_bonus` | Leviathan |
| Water Bonus +X | 1 | `terrain_bonus` / `conditional_stat_bonus` | Hydroforce |
| Water Bounce | 1 | `terrain_interaction` / `terrain_bounce` | Mirage |
| Water Rush | 1 | `trajectory` / `speed_and_distance_modifier_over_terrain` | Leviathan |
| Wild Rush Speed | 1 | `trajectory` / `speed_and_distance_modifier_over_terrain` | Explorer |
| Wind Resist | 2 | `wind` / `wind_resistance` | Into the Blue, Obelisk |
| Wind Resist 75% | 1 | `wind` / `wind_resistance` | High Flight |
| Wind Resistance 100% | 1 | `wind` / `wind_resistance` | Stormbringer |
| Wind-Up Toy | 1 | `wind` / `wind_toward_hole` | XLR8R |
| Zephyr +X mph | 1 | `wind` / `wind_toward_hole` | Stormbringer |

## Statut

La normalisation structurelle est complète. La prochaine étape n’est pas de modifier les données, mais de valider les règles sémantiques avec des sacs et situations de référence avant de les brancher au moteur fidèle.