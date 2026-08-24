# Audit des capacités restantes

> Source détaillée actuelle de la couverture des capacités. Rapport généré depuis SQLite, le catalogue officiel versionné, la carte sémantique et le registre du moteur. Les classes A/B vides et les blocages C–H sont des constats de qualification, pas une roadmap active. Le développement fonctionnel est temporairement gelé.

## État recalculé

| Mesure | Valeur |
|---|---:|
| Clubs du catalogue | 88 |
| Clubs possédés | 80 |
| Occurrences catalogue | 162 |
| Occurrences possédées | 146 |
| Possédées complètement simulées | 84 |
| Possédées partielles | 2 |
| Possédées non résolues hors partielles | 60 |
| Clubs possédés entièrement simulés | 36 |
| Clubs possédés avec au moins une capacité restante | 44 |

## Classification exhaustive

| Classe | Définition | Catalogue | Possédées |
|---|---|---:|---:|
| A | Déterministe / implémentation directe | 0 | 0 |
| B | Déterministe / petite extension générique | 0 | 0 |
| C | Texte ou sémantique ambiguë | 18 | 13 |
| D | Conflit entre sources ou données | 10 | 9 |
| E | Physique ou géométrie non modélisée | 30 | 25 |
| F | Historique de coups ou état temporel complexe | 10 | 10 |
| G | Aléatoire ou transformation | 6 | 3 |
| H | Partiellement simulée | 2 | 2 |

Les classes A et B sont vides : aucune capacité restante ne peut être implémentée sans contredire une qualification existante ou introduire une hypothèse. Aucun handler n'est donc ajouté par ce lot.

## Groupes restants

| Classe | Groupe | Occurrences | Clubs | Clubs possédés | Difficulté | Primitive manquante |
|---|---|---:|---|---|---|---|
| C | `label:alien_relic_left` | 1 | meteor | aucun | special | semantic_qualification |
| C | `label:alien_relic_right` | 1 | meteor | aucun | special | semantic_qualification |
| C | `label:aura_of_death` | 1 | the_reaper | aucun | special | semantic_qualification |
| C | `label:bag_wind_power` | 1 | jetstream | jetstream | special | READ_CONTEXT |
| C | `label:gem_ball_bonus` | 1 | crystallize | crystallize | special | semantic_qualification |
| C | `label:home_turf_southwind` | 1 | ranger | ranger | special | semantic_qualification |
| C | `label:rocket_boosters` | 2 | flashpoint, the_rocket | aucun | special | semantic_qualification |
| C | `label:rough_boosters` | 1 | overgrowth | overgrowth | special | READ_CONTEXT |
| C | `label:scottsdale_boosters` | 1 | rising_flame | rising_flame | special | semantic_qualification |
| C | `label:shared_growth` | 1 | oakheart | oakheart | special | semantic_qualification |
| C | `label:smoke_x` | 1 | catalyst | catalyst | special | semantic_qualification |
| C | `label:solidarity` | 1 | pantheon | pantheon | special | semantic_qualification |
| C | `label:sparks_x` | 1 | catalyst | catalyst | special | semantic_qualification |
| C | `label:stat_fusion` | 1 | fusion | fusion | special | semantic_qualification |
| C | `label:steam_x` | 1 | catalyst | catalyst | special | semantic_qualification |
| C | `label:super_fireball` | 1 | boomstick | boomstick | special | semantic_qualification |
| C | `label:terrain_bonus` | 1 | color_theory | color_theory | special | READ_CONTEXT |
| D | `label:chains_into_itself` | 1 | sparky | sparky | special | aucune primitive suffisante sans donnée externe |
| D | `label:electrodynamics_0_2ft` | 1 | sparky | sparky | special | semantic_qualification |
| D | `label:magnetism_0_15ft` | 1 | magnesis | aucun | special | semantic_qualification |
| D | `label:terrain_resist_50` | 6 | homecoming, dunecrawler, obelisk, hydroforce, sandblast, windstrike | homecoming, dunecrawler, obelisk, hydroforce, sandblast, windstrike | special | semantic_qualification, READ_CONTEXT |
| D | `label:wind_resistance_100` | 1 | stormbringer | stormbringer | special | READ_CONTEXT |
| E | `label:alien_world` | 1 | meteor | aucun | special | READ_CONTEXT |
| E | `label:bag_tree_bonus` | 1 | the_seeker | the_seeker | special | READ_CONTEXT |
| E | `label:bag_tree_passing` | 1 | the_seeker | the_seeker | special | READ_CONTEXT |
| E | `label:bag_water_bonus` | 1 | atlantis | aucun | special | READ_CONTEXT |
| E | `label:bag_water_bounce` | 1 | atlantis | aucun | special | READ_CONTEXT |
| E | `label:boundary_bonus` | 3 | edgewalker, leviathan, windstrike | edgewalker, leviathan, windstrike | special | semantic_qualification |
| E | `label:boundary_rush` | 1 | flashpoint | aucun | special | READ_CONTEXT |
| E | `label:boundary_rush_75` | 1 | skyfury | skyfury | special | validated_physics_effect |
| E | `label:emerald_rush_75` | 1 | green_demon | green_demon | special | validated_physics_effect |
| E | `label:flight_training` | 1 | eagle_s_landing | eagle_s_landing | special | semantic_qualification |
| E | `label:green_grip` | 1 | meanderer | meanderer | special | semantic_qualification |
| E | `label:ground_rush` | 1 | hot_streak | aucun | special | semantic_qualification |
| E | `label:momentum` | 1 | rolling_stone | rolling_stone | special | semantic_qualification |
| E | `label:power_shot` | 4 | dunecrawler, ember, flamethrower, neon_impulse | dunecrawler, ember, flamethrower, neon_impulse | special | semantic_qualification, validated_physics_effect |
| E | `label:shoreline_rush` | 1 | wave | wave | special | validated_physics_effect |
| E | `label:tree_bonus` | 2 | edgewalker, outset | edgewalker, outset | special | READ_CONTEXT |
| E | `label:tree_bonus_x` | 3 | huntsman, ironbark, oakheart | huntsman, ironbark, oakheart | special | READ_CONTEXT |
| E | `label:tree_passing` | 1 | trailblazer | trailblazer | special | READ_CONTEXT |
| E | `label:water_bonus` | 1 | leviathan | leviathan | special | READ_CONTEXT |
| E | `label:water_bonus_x` | 1 | hydroforce | hydroforce | special | READ_CONTEXT |
| E | `label:water_rush` | 1 | leviathan | leviathan | special | validated_physics_effect |
| E | `label:wild_rush_speed` | 1 | explorer | explorer | special | validated_physics_effect |
| F | `label:ability_mirror` | 1 | mimic | mimic | stateful | semantic_qualification |
| F | `label:adventure` | 1 | homecoming | homecoming | stateful | semantic_qualification |
| F | `label:fission` | 1 | supercollider | supercollider | stateful | semantic_qualification |
| F | `label:gravity_reduction_x` | 1 | tierra_hueca | tierra_hueca | stateful | semantic_qualification |
| F | `label:hollow_earth` | 1 | tierra_hueca | tierra_hueca | stateful | semantic_qualification |
| F | `label:palo_control_on_hit_x` | 1 | tierra_hueca | tierra_hueca | stateful | semantic_qualification |
| F | `label:perfect_shot_bag_power` | 1 | flamethrower | flamethrower | stateful | semantic_qualification |
| F | `label:perfect_shot_terrain_bonus_boost` | 1 | color_theory | color_theory | stateful | semantic_qualification |
| F | `label:volt_bounce` | 1 | rebound | rebound | stateful | READ_CONTEXT |
| F | `label:wind_up_toy` | 1 | xlr8r | xlr8r | stateful | READ_CONTEXT |
| G | `label:beast_strength` | 1 | chimera | aucun | special | semantic_qualification |
| G | `label:random_boost_x` | 1 | crystallize | crystallize | special | semantic_qualification |
| G | `label:sacrifice` | 1 | the_reaper | aucun | special | semantic_qualification |
| G | `label:shuffle_up` | 1 | outlaw | outlaw | special | semantic_qualification |
| G | `label:three_heads` | 1 | chimera | aucun | special | semantic_qualification |
| G | `label:trumpet_blast` | 1 | fanfare | fanfare | special | semantic_qualification |
| H | `label:brand_fairway_rush` | 1 | crusader | crusader | special | aucune primitive suffisante sans donnée externe |
| H | `label:forester_power_elite` | 1 | ranger | ranger | special | aucune primitive suffisante sans donnée externe |

## Occurrences détaillées

### Boomstick — Super Fireball

- Identifiant : `boomstick__super_fireball`
- Classe : **C — Texte ou sémantique ambiguë**
- Possédé : oui
- Niveau utilisateur : 7
- Valeur au niveau utilisateur : 85%
- Texte officiel : Stat changes from Fireball are increased by X%.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: 73%; 4: 76%; 5: 79%; 6: 82%; 7: 85%; 8: 88%; 9: 91%; 10: 94%; 11: 97%; 12: 100%; Elite: 100%
- Statut : `ambiguous`
- Raison : The Fireball changes and the stage at which their percentage is increased are not specified here.
- Qualification : `true_semantic_ambiguity`
- Famille technique : `unqualified:super_fireball`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : special
- Confiance : low
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Compare the competing interpretations in a minimal bag and record the exact displayed stat change.

### Catalyst — Smoke +X

- Identifiant : `catalyst__smoke_x`
- Classe : **C — Texte ou sémantique ambiguë**
- Possédé : oui
- Niveau utilisateur : 7
- Valeur au niveau utilisateur : +4
- Texte officiel : While next to a Forester club, both clubs gain +X Power.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: +3; 4: +3; 5: +3; 6: +3; 7: +4; 8: +4; 9: +4; 10: +4; 11: +5; 12: +5; Elite: +5
- Statut : `ambiguous`
- Raison : With two matching neighbors, whether the source bonus stacks once or twice is not specified.
- Qualification : `true_semantic_ambiguity`
- Famille technique : `unqualified:smoke_x`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : special
- Confiance : low
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Compare the competing interpretations in a minimal bag and record the exact displayed stat change.

### Catalyst — Sparks +X

- Identifiant : `catalyst__sparks_x`
- Classe : **C — Texte ou sémantique ambiguë**
- Possédé : oui
- Niveau utilisateur : 7
- Valeur au niveau utilisateur : inactive/inconnue
- Texte officiel : While next to a Mythical club, both clubs gain +X Power, +X Control, and +X Spin.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: inactive; 6: inactive; 7: inactive; 8: inactive; 9: inactive; 10: inactive; 11: inactive; 12: inactive; Elite: +2
- Statut : `ambiguous`
- Raison : With two matching neighbors, whether the source bonus stacks once or twice is not specified.
- Qualification : `true_semantic_ambiguity`
- Famille technique : `unqualified:sparks_x`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : special
- Confiance : low
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Compare the competing interpretations in a minimal bag and record the exact displayed stat change.

### Catalyst — Steam +X

- Identifiant : `catalyst__steam_x`
- Classe : **C — Texte ou sémantique ambiguë**
- Possédé : oui
- Niveau utilisateur : 7
- Valeur au niveau utilisateur : +4
- Texte officiel : While next to a Nautilus club, both clubs gain +X Control.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: +3; 4: +3; 5: +3; 6: +3; 7: +4; 8: +4; 9: +4; 10: +4; 11: +5; 12: +5; Elite: +5
- Statut : `ambiguous`
- Raison : With two matching neighbors, whether the source bonus stacks once or twice is not specified.
- Qualification : `true_semantic_ambiguity`
- Famille technique : `unqualified:steam_x`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : special
- Confiance : low
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Compare the competing interpretations in a minimal bag and record the exact displayed stat change.

### Color Theory — Terrain Bonus

- Identifiant : `color_theory__terrain_bonus`
- Classe : **C — Texte ou sémantique ambiguë**
- Possédé : oui
- Niveau utilisateur : 7
- Valeur au niveau utilisateur : +1
- Texte officiel : Rough Bonus +X, Water bonus +X, Tree Bonus +X, Sand Bonus +X
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: +1; 6: +1; 7: +1; 8: +1; 9: +2; 10: +2; 11: +2; 12: +2; Elite: +2
- Statut : `ambiguous`
- Raison : The listed terrain bonuses use proximity/terrain formulas that are not present in the official table.
- Qualification : `true_semantic_ambiguity`
- Famille technique : `terrain_condition`
- Primitives disponibles : SELECT_SELF, READ_LEVEL_VALUE, ADD_STAT
- Primitive/donnée manquante : `READ_CONTEXT`
- Difficulté : special
- Confiance : low
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Compare the competing interpretations in a minimal bag and record the exact displayed stat change.

### Crystallize — Gem Ball Bonus

- Identifiant : `crystallize__gem_ball_bonus`
- Classe : **C — Texte ou sémantique ambiguë**
- Possédé : oui
- Niveau utilisateur : 6
- Valeur au niveau utilisateur : x2
- Texte officiel : Gem Ball bonuses are applied X times while Crystallize is in your bag.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: x2; 6: x2; 7: x2; 8: x2; 9: x3; 10: x3; 11: x3; 12: x3; Elite: x5
- Statut : `ambiguous`
- Raison : The source and stacking order of Gem Ball bonuses are outside the official club table.
- Qualification : `true_semantic_ambiguity`
- Famille technique : `unqualified:gem_ball_bonus`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : special
- Confiance : low
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Compare the competing interpretations in a minimal bag and record the exact displayed stat change.

### Flashpoint — Rocket Boosters

- Identifiant : `flashpoint__rocket_boosters`
- Classe : **C — Texte ou sémantique ambiguë**
- Possédé : non
- Niveau utilisateur : inconnu/non possédé
- Valeur au niveau utilisateur : inactive/inconnue
- Texte officiel : Gain 25% of the power of clubs to its left and right.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: inactive; 6: inactive; 7: +25%; 8: +26%; 9: +27%; 10: +28%; 11: +29%; 12: +30%; Elite: +40%
- Statut : `ambiguous`
- Raison : The text does not establish whether neighboring base stats or final ability-modified stats are copied.
- Qualification : `true_semantic_ambiguity`
- Famille technique : `unqualified:rocket_boosters`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : special
- Confiance : low
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Compare the competing interpretations in a minimal bag and record the exact displayed stat change.

### Fusion — Stat Fusion

- Identifiant : `fusion__stat_fusion`
- Classe : **C — Texte ou sémantique ambiguë**
- Possédé : oui
- Niveau utilisateur : 7
- Valeur au niveau utilisateur : 44%
- Texte officiel : Fusion has bonus Control equal to X% of the Control of the club to its left and bonus Power equal to X% of the Power of the club to its right.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: 40%; 4: 41%; 5: 42%; 6: 43%; 7: 44%; 8: 45%; 9: 46%; 10: 47%; 11: 48%; 12: 50%; Elite: 55%
- Statut : `ambiguous`
- Raison : The text does not establish whether neighboring base stats or final ability-modified stats are copied.
- Qualification : `true_semantic_ambiguity`
- Famille technique : `unqualified:stat_fusion`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : special
- Confiance : low
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Compare the competing interpretations in a minimal bag and record the exact displayed stat change.

### Jetstream — Bag Wind Power

- Identifiant : `jetstream__bag_wind_power`
- Classe : **C — Texte ou sémantique ambiguë**
- Possédé : oui
- Niveau utilisateur : 6
- Valeur au niveau utilisateur : 5.0mph
- Texte officiel : Your clubs gain +1 power for every X mph/kph of wind speed.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: 6.0mph; 6: 5.0mph; 7: 5.0mph; 8: 5.0mph; 9: 5.0mph; 10: 5.0mph; 11: 4.0mph; 12: 4.0mph; Elite: 3.0mph
- Statut : `ambiguous`
- Raison : The rounding rule for incomplete wind-speed intervals and interaction with wind-changing abilities are not specified.
- Qualification : `true_semantic_ambiguity`
- Famille technique : `wind_resistance`
- Primitives disponibles : SELECT_SELF, READ_LEVEL_VALUE, ADD_MODIFIER
- Primitive/donnée manquante : `READ_CONTEXT`
- Difficulté : special
- Confiance : low
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Compare the competing interpretations in a minimal bag and record the exact displayed stat change.

### Meteor — Alien Relic (Left)

- Identifiant : `meteor__alien_relic_left`
- Classe : **C — Texte ou sémantique ambiguë**
- Possédé : non
- Niveau utilisateur : inconnu/non possédé
- Valeur au niveau utilisateur : inactive/inconnue
- Texte officiel : The club to the left of Meteor gains an extra instance of each of its abilities.  - Elite Level: Ability can wrap to the other side of the bag.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: inactive; 6: inactive; 7: inactive; 8: inactive; 9: x2; 10: x2; 11: x2; 12: x2; Elite: x2
- Statut : `ambiguous`
- Raison : Ability duplication, level provenance, wrapping, ordering, and recursion are not validated.
- Qualification : `true_semantic_ambiguity`
- Famille technique : `unqualified:alien_relic_left`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : special
- Confiance : low
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Compare the competing interpretations in a minimal bag and record the exact displayed stat change.

### Meteor — Alien Relic (Right)

- Identifiant : `meteor__alien_relic_right`
- Classe : **C — Texte ou sémantique ambiguë**
- Possédé : non
- Niveau utilisateur : inconnu/non possédé
- Valeur au niveau utilisateur : inactive/inconnue
- Texte officiel : The club to the right of Meteor gains an extra instance of each of its abilities.  - Elite Level: Ability can wrap to the other side of the bag.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: inactive; 6: inactive; 7: inactive; 8: inactive; 9: inactive; 10: x2; 11: x2; 12: x2; Elite: x2
- Statut : `ambiguous`
- Raison : Ability duplication, level provenance, wrapping, ordering, and recursion are not validated.
- Qualification : `true_semantic_ambiguity`
- Famille technique : `unqualified:alien_relic_right`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : special
- Confiance : low
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Compare the competing interpretations in a minimal bag and record the exact displayed stat change.

### Oakheart — Shared Growth

- Identifiant : `oakheart__shared_growth`
- Classe : **C — Texte ou sémantique ambiguë**
- Possédé : oui
- Niveau utilisateur : 6
- Valeur au niveau utilisateur : ✔
- Texte officiel : Clubs next to Oakheart also benefit from Oakheart's Tree Bonus ability.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: ✔; 6: ✔; 7: ✔; 8: ✔; 9: ✔; 10: ✔; 11: ✔; 12: ✔
- Statut : `ambiguous`
- Raison : Whether copied Tree Bonus uses the source level, target level, or evaluated source contribution is not specified.
- Qualification : `true_semantic_ambiguity`
- Famille technique : `unqualified:shared_growth`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : special
- Confiance : low
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Compare the competing interpretations in a minimal bag and record the exact displayed stat change.

### Overgrowth — Rough Boosters

- Identifiant : `overgrowth__rough_boosters`
- Classe : **C — Texte ou sémantique ambiguë**
- Possédé : oui
- Niveau utilisateur : 6
- Valeur au niveau utilisateur : +4
- Texte officiel : Gains up to +X to all stats when hitting from rough or deep rough. - Elite Level: Rough Boosters will apply depending on how much rough area is nearby.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: +4; 6: +4; 7: +5; 8: +5; 9: +6; 10: +6; 11: +7; 12: +7; Elite: +7
- Statut : `ambiguous`
- Raison : At Elite the behavior changes from categorical rough to nearby-area scaling, whose formula is not specified.
- Qualification : `true_semantic_ambiguity`
- Famille technique : `terrain_condition`
- Primitives disponibles : SELECT_SELF, READ_LEVEL_VALUE, ADD_STAT
- Primitive/donnée manquante : `READ_CONTEXT`
- Difficulté : special
- Confiance : low
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Compare the competing interpretations in a minimal bag and record the exact displayed stat change.

### Pantheon — Solidarity

- Identifiant : `pantheon__solidarity`
- Classe : **C — Texte ou sémantique ambiguë**
- Possédé : oui
- Niveau utilisateur : inconnu/non possédé
- Valeur au niveau utilisateur : inactive/inconnue
- Texte officiel : Pantheon counts as being all brands.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: inactive; 6: inactive; 7: inactive; 8: inactive; 9: inactive; 10: inactive; 11: inactive; 12: inactive; Elite: ✔
- Statut : `ambiguous`
- Raison : Interactions between multi-brand identity and every brand filter require a validated matching contract.
- Qualification : `true_semantic_ambiguity`
- Famille technique : `unqualified:solidarity`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : special
- Confiance : low
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Compare the competing interpretations in a minimal bag and record the exact displayed stat change.

### Ranger — Home Turf: Southwind

- Identifiant : `ranger__home_turf_southwind`
- Classe : **C — Texte ou sémantique ambiguë**
- Possédé : oui
- Niveau utilisateur : 7
- Valeur au niveau utilisateur : ✔
- Texte officiel : The Forester Power ability is doubled on Southwind.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: ✔; 6: ✔; 7: ✔; 8: ✔; 9: ✔; 10: ✔; 11: ✔; 12: ✔; Elite: ✔
- Statut : `ambiguous`
- Raison : The official course identity and exact doubling stage of Forester Power must be validated.
- Qualification : `true_semantic_ambiguity`
- Famille technique : `unqualified:home_turf_southwind`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : special
- Confiance : low
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Compare the competing interpretations in a minimal bag and record the exact displayed stat change.

### Rising Flame — Scottsdale Boosters

- Identifiant : `rising_flame__scottsdale_boosters`
- Classe : **C — Texte ou sémantique ambiguë**
- Possédé : oui
- Niveau utilisateur : 7
- Valeur au niveau utilisateur : ✔
- Texte officiel : The Phoenix Power ability is doubled on Scottsdale.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: ✔; 6: ✔; 7: ✔; 8: ✔; 9: ✔; 10: ✔; 11: ✔; 12: ✔
- Statut : `ambiguous`
- Raison : The exact doubling stage of Phoenix Power and official course identity must be validated.
- Qualification : `true_semantic_ambiguity`
- Famille technique : `unqualified:scottsdale_boosters`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : special
- Confiance : low
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Compare the competing interpretations in a minimal bag and record the exact displayed stat change.

### The Reaper — Aura of Death

- Identifiant : `the_reaper__aura_of_death`
- Classe : **C — Texte ou sémantique ambiguë**
- Possédé : non
- Niveau utilisateur : inconnu/non possédé
- Valeur au niveau utilisateur : inactive/inconnue
- Texte officiel : Other clubs have X% of Reaper's stats.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: inactive; 6: inactive; 7: inactive; 8: inactive; 9: 10%; 10: 12%; 11: 14%; 12: 17%
- Statut : `ambiguous`
- Raison : The text does not establish base-versus-final source stats or ability-order interactions.
- Qualification : `true_semantic_ambiguity`
- Famille technique : `unqualified:aura_of_death`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : special
- Confiance : low
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Compare the competing interpretations in a minimal bag and record the exact displayed stat change.

### The Rocket — Rocket Boosters

- Identifiant : `the_rocket__rocket_boosters`
- Classe : **C — Texte ou sémantique ambiguë**
- Possédé : non
- Niveau utilisateur : inconnu/non possédé
- Valeur au niveau utilisateur : inactive/inconnue
- Texte officiel : The Rocket gains % of the power of the clubs to its left and right
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: 55%; 6: 56%; 7: 58%; 8: 59%; 9: 61%; 10: 62%; 11: 64%; 12: 65%; Elite: 68%
- Statut : `ambiguous`
- Raison : The text does not establish whether neighboring base stats or final ability-modified stats are copied.
- Qualification : `true_semantic_ambiguity`
- Famille technique : `unqualified:rocket_boosters`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : special
- Confiance : low
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Compare the competing interpretations in a minimal bag and record the exact displayed stat change.

### Dunecrawler — Terrain Resist +50%

- Identifiant : `dunecrawler__terrain_resist_50`
- Classe : **D — Conflit entre sources ou données**
- Possédé : oui
- Niveau utilisateur : 6
- Valeur au niveau utilisateur : 53%
- Texte officiel : Resistant but not immune to Slow Down effects like Rough, Deep Rough, Fairway, etc.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: 50%; 6: 53%; 7: 55%; 8: 58%; 9: 61%; 10: 64%; 11: 67%; 12: 70%; Elite: 75%
- Statut : `ambiguous`
- Raison : The shared label contains level-varying values and an Elite 60% value that conflicts with one club text stating 50%.
- Qualification : `official_text_table_conflict`
- Famille technique : `terrain_condition`
- Primitives disponibles : SELECT_SELF, READ_LEVEL_VALUE, ADD_STAT
- Primitive/donnée manquante : `READ_CONTEXT`
- Difficulté : special
- Confiance : blocked
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Compare the displayed in-game ability value and resulting modifier at the conflicting level.

### Homecoming — Terrain Resist +50%

- Identifiant : `homecoming__terrain_resist_50`
- Classe : **D — Conflit entre sources ou données**
- Possédé : oui
- Niveau utilisateur : 8
- Valeur au niveau utilisateur : 50%
- Texte officiel : Homecoming ignores 50% of penalties when hitting from unfavorable ground types.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: 50%; 4: 50%; 5: 50%; 6: 50%; 7: 50%; 8: 50%; 9: 50%; 10: 50%; 11: 50%; 12: 50%; Elite: 50%
- Statut : `ambiguous`
- Raison : The shared label contains level-varying values and an Elite 60% value that conflicts with one club text stating 50%.
- Qualification : `official_text_table_conflict`
- Famille technique : `unqualified:terrain_resist_50`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : special
- Confiance : blocked
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Compare the displayed in-game ability value and resulting modifier at the conflicting level.

### Hydroforce — Terrain Resist +50%

- Identifiant : `hydroforce__terrain_resist_50`
- Classe : **D — Conflit entre sources ou données**
- Possédé : oui
- Niveau utilisateur : 6
- Valeur au niveau utilisateur : 50%
- Texte officiel : Hydroforce ignores 50% of penalties when hitting from unfavorable ground types.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: 50%; 4: 50%; 5: 50%; 6: 50%; 7: 50%; 8: 50%; 9: 50%; 10: 50%; 11: 50%; 12: 50%; Elite: 60%
- Statut : `ambiguous`
- Raison : The shared label contains level-varying values and an Elite 60% value that conflicts with one club text stating 50%.
- Qualification : `official_text_table_conflict`
- Famille technique : `unqualified:terrain_resist_50`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : special
- Confiance : blocked
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Compare the displayed in-game ability value and resulting modifier at the conflicting level.

### Magnesis — Magnetism 0.15ft

- Identifiant : `magnesis__magnetism_0_15ft`
- Classe : **D — Conflit entre sources ou données**
- Possédé : non
- Niveau utilisateur : inconnu/non possédé
- Valeur au niveau utilisateur : inactive/inconnue
- Texte officiel : Magnetized to the hole within a 0.15ft radius.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: inactive; 6: inactive; 7: 0.15m; 8: 0.17m; 9: 0.19m; 10: 0.2m; 11: 0.21m; 12: 0.21m
- Statut : `ambiguous`
- Raison : The official text uses feet while normalized table values are marked as metres.
- Qualification : `official_text_table_conflict`
- Famille technique : `unqualified:magnetism_0_15ft`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : special
- Confiance : blocked
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Compare the displayed in-game ability value and resulting modifier at the conflicting level.

### Obelisk — Terrain Resist +50%

- Identifiant : `obelisk__terrain_resist_50`
- Classe : **D — Conflit entre sources ou données**
- Possédé : oui
- Niveau utilisateur : 7
- Valeur au niveau utilisateur : 50%
- Texte officiel : Resistant but not immune to Slow Down effects like Rough, Deep Rough, Fairway, etc.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: 50%; 4: 50%; 5: 50%; 6: 50%; 7: 50%; 8: 50%; 9: 50%; 10: 50%; 11: 50%; 12: 50%; Elite: 50%
- Statut : `ambiguous`
- Raison : The shared label contains level-varying values and an Elite 60% value that conflicts with one club text stating 50%.
- Qualification : `official_text_table_conflict`
- Famille technique : `terrain_condition`
- Primitives disponibles : SELECT_SELF, READ_LEVEL_VALUE, ADD_STAT
- Primitive/donnée manquante : `READ_CONTEXT`
- Difficulté : special
- Confiance : blocked
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Compare the displayed in-game ability value and resulting modifier at the conflicting level.

### Sandblast — Terrain Resist +50%

- Identifiant : `sandblast__terrain_resist_50`
- Classe : **D — Conflit entre sources ou données**
- Possédé : oui
- Niveau utilisateur : 7
- Valeur au niveau utilisateur : 50%
- Texte officiel : Sandblast ignores 50% of penalties when hitting from unfavorable ground types.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: 50%; 4: 50%; 5: 50%; 6: 50%; 7: 50%; 8: 50%; 9: 50%; 10: 50%; 11: 50%; 12: 50%
- Statut : `ambiguous`
- Raison : The shared label contains level-varying values and an Elite 60% value that conflicts with one club text stating 50%.
- Qualification : `official_text_table_conflict`
- Famille technique : `unqualified:terrain_resist_50`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : special
- Confiance : blocked
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Compare the displayed in-game ability value and resulting modifier at the conflicting level.

### Sparky — Chains into Itself

- Identifiant : `sparky__chains_into_itself`
- Classe : **D — Conflit entre sources ou données**
- Possédé : oui
- Niveau utilisateur : 9
- Valeur au niveau utilisateur : inactive/inconnue
- Texte officiel : Chains into Itself. (On your next shot, this club has +2 to all stats.)
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: inactive; 6: inactive; 7: inactive; 8: inactive; 9: inactive; 10: inactive; 11: +6; 12: +7; Elite: inactive
- Statut : `ambiguous`
- Raison : The official text says +2 to all stats while the level table contains +6 and +7.
- Qualification : `official_text_table_conflict`
- Famille technique : `chain_next_shot`
- Primitives disponibles : SELECT_SELF, READ_LEVEL_VALUE, SCHEDULE_EFFECT
- Primitive/donnée manquante : `validation_or_external_model`
- Difficulté : special
- Confiance : blocked
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Compare the displayed in-game ability value and resulting modifier at the conflicting level.

### Sparky — Electrodynamics 0.2ft

- Identifiant : `sparky__electrodynamics_0_2ft`
- Classe : **D — Conflit entre sources ou données**
- Possédé : oui
- Niveau utilisateur : 9
- Valeur au niveau utilisateur : 0.2m
- Texte officiel : Magnetized to the hole within a 0.2ft radius. This radius is increased by 0.2 ft for each time you've hit with a chain bonus this game.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: inactive; 6: inactive; 7: inactive; 8: inactive; 9: 0.2m; 10: 0.22m; 11: 0.23m; 12: 0.24m; Elite: 0.26m
- Statut : `ambiguous`
- Raison : The official text uses feet while normalized table values are marked as metres, and the chain-hit increment duration is stateful.
- Qualification : `official_text_table_conflict`
- Famille technique : `unqualified:electrodynamics_0_2ft`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : special
- Confiance : blocked
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Compare the displayed in-game ability value and resulting modifier at the conflicting level.

### Stormbringer — Wind Resistance 100%

- Identifiant : `stormbringer__wind_resistance_100`
- Classe : **D — Conflit entre sources ou données**
- Possédé : oui
- Niveau utilisateur : 8
- Valeur au niveau utilisateur : inactive/inconnue
- Texte officiel : Stormbringer is 100% less affected by wind.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: inactive; 6: inactive; 7: inactive; 8: inactive; 9: inactive; 10: inactive; 11: inactive; 12: 85%
- Statut : `ambiguous`
- Raison : The official text says 100% while the normalized level table contains 85%.
- Qualification : `official_text_table_conflict`
- Famille technique : `wind_resistance`
- Primitives disponibles : SELECT_SELF, READ_LEVEL_VALUE, ADD_MODIFIER
- Primitive/donnée manquante : `READ_CONTEXT`
- Difficulté : special
- Confiance : blocked
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Compare the displayed in-game ability value and resulting modifier at the conflicting level.

### Windstrike — Terrain Resist +50%

- Identifiant : `windstrike__terrain_resist_50`
- Classe : **D — Conflit entre sources ou données**
- Possédé : oui
- Niveau utilisateur : 8
- Valeur au niveau utilisateur : 50%
- Texte officiel : Windstrike ignores 50% of penalties when hitting from unfavorable ground types.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: 50%; 4: 50%; 5: 50%; 6: 50%; 7: 50%; 8: 50%; 9: 50%; 10: 50%; 11: 50%; 12: 50%
- Statut : `ambiguous`
- Raison : The shared label contains level-varying values and an Elite 60% value that conflicts with one club text stating 50%.
- Qualification : `official_text_table_conflict`
- Famille technique : `unqualified:terrain_resist_50`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : special
- Confiance : blocked
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Compare the displayed in-game ability value and resulting modifier at the conflicting level.

### Atlantis — Bag Water Bonus

- Identifiant : `atlantis__bag_water_bonus`
- Classe : **E — Physique ou géométrie non modélisée**
- Possédé : non
- Niveau utilisateur : inconnu/non possédé
- Valeur au niveau utilisateur : inactive/inconnue
- Texte officiel : All clubs gain up to +X to all stats depending on how close you are to water.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: inactive; 6: inactive; 7: +1; 8: +1; 9: +2; 10: +2; 11: +3; 12: +3; Elite: +3
- Statut : `physics_required`
- Raison : The official effect depends on proximity, trajectory phase, collision, timing, or physical speed/distance behavior that the static context does not contain.
- Qualification : `geometry_or_trajectory_required`
- Famille technique : `terrain_condition`
- Primitives disponibles : SELECT_SELF, READ_LEVEL_VALUE, ADD_STAT
- Primitive/donnée manquante : `READ_CONTEXT`
- Difficulté : special
- Confiance : high_dependency_confidence
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Record the relevant distance/time/terrain phase and the before/after in-game result across boundary cases.

### Atlantis — Bag Water Bounce

- Identifiant : `atlantis__bag_water_bounce`
- Classe : **E — Physique ou géométrie non modélisée**
- Possédé : non
- Niveau utilisateur : inconnu/non possédé
- Valeur au niveau utilisateur : inactive/inconnue
- Texte officiel : Your clubs gain the ability to bounce off water X amount of times.  - Elite Level: Ability will add an additional bounce to adjacent clubs.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: inactive; 6: inactive; 7: x1; 8: x1; 9: x1; 10: x1; 11: x1; 12: x1; Elite: x1
- Statut : `physics_required`
- Raison : The official effect depends on proximity, trajectory phase, collision, timing, or physical speed/distance behavior that the static context does not contain.
- Qualification : `geometry_or_trajectory_required`
- Famille technique : `terrain_condition`
- Primitives disponibles : SELECT_SELF, READ_LEVEL_VALUE, ADD_STAT
- Primitive/donnée manquante : `READ_CONTEXT`
- Difficulté : special
- Confiance : high_dependency_confidence
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Record the relevant distance/time/terrain phase and the before/after in-game result across boundary cases.

### Dunecrawler — Power Shot

- Identifiant : `dunecrawler__power_shot`
- Classe : **E — Physique ou géométrie non modélisée**
- Possédé : oui
- Niveau utilisateur : 6
- Valeur au niveau utilisateur : ✔
- Texte officiel : When you aim and pull back all the way, this club gradually hits further but is harder to control.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: ✔; 6: ✔; 7: ✔; 8: ✔; 9: ✔; 10: ✔; 11: ✔; 12: ✔; Elite: ✔
- Statut : `physics_required`
- Raison : The official effect depends on proximity, trajectory phase, collision, timing, or physical speed/distance behavior that the static context does not contain.
- Qualification : `geometry_or_trajectory_required`
- Famille technique : `unqualified:power_shot`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : special
- Confiance : high_dependency_confidence
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Record the relevant distance/time/terrain phase and the before/after in-game result across boundary cases.

### Eagle's Landing — Flight Training

- Identifiant : `eagle_s_landing__flight_training`
- Classe : **E — Physique ou géométrie non modélisée**
- Possédé : oui
- Niveau utilisateur : 3
- Valeur au niveau utilisateur : +1
- Texte officiel : For every 2.5 seconds the ball is in the air, Eagle's Landing gains +1 control.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: +1; 4: +1; 5: +1; 6: +1; 7: +1; 8: +1; 9: +1; 10: +1; 11: +1; 12: +1
- Statut : `physics_required`
- Raison : The official effect depends on proximity, trajectory phase, collision, timing, or physical speed/distance behavior that the static context does not contain.
- Qualification : `geometry_or_trajectory_required`
- Famille technique : `unqualified:flight_training`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : special
- Confiance : high_dependency_confidence
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Record the relevant distance/time/terrain phase and the before/after in-game result across boundary cases.

### Edgewalker — Boundary Bonus

- Identifiant : `edgewalker__boundary_bonus`
- Classe : **E — Physique ou géométrie non modélisée**
- Possédé : oui
- Niveau utilisateur : 7
- Valeur au niveau utilisateur : +3
- Texte officiel : Gains up to +X to all stats depending on how much out of bounds area is nearby.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: +2; 4: +3; 5: +3; 6: +3; 7: +3; 8: +4; 9: +4; 10: +4; 11: +4; 12: +5; Elite: +7
- Statut : `physics_required`
- Raison : The official effect depends on proximity, trajectory phase, collision, timing, or physical speed/distance behavior that the static context does not contain.
- Qualification : `geometry_or_trajectory_required`
- Famille technique : `unqualified:boundary_bonus`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : special
- Confiance : high_dependency_confidence
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Record the relevant distance/time/terrain phase and the before/after in-game result across boundary cases.

### Edgewalker — Tree Bonus

- Identifiant : `edgewalker__tree_bonus`
- Classe : **E — Physique ou géométrie non modélisée**
- Possédé : oui
- Niveau utilisateur : 7
- Valeur au niveau utilisateur : +3
- Texte officiel : Gains up to +X to all stats depending on how many trees are within 25 feet.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: +2; 6: +3; 7: +3; 8: +3; 9: +3; 10: +3; 11: +3; 12: +4; Elite: +6
- Statut : `physics_required`
- Raison : The official effect depends on proximity, trajectory phase, collision, timing, or physical speed/distance behavior that the static context does not contain.
- Qualification : `geometry_or_trajectory_required`
- Famille technique : `terrain_proximity_bonus`
- Primitives disponibles : SELECT_SELF, READ_LEVEL_VALUE, ADD_STAT
- Primitive/donnée manquante : `READ_CONTEXT`
- Difficulté : special
- Confiance : high_dependency_confidence
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Record the relevant distance/time/terrain phase and the before/after in-game result across boundary cases.

### Ember — Power Shot

- Identifiant : `ember__power_shot`
- Classe : **E — Physique ou géométrie non modélisée**
- Possédé : oui
- Niveau utilisateur : 8
- Valeur au niveau utilisateur : ✔
- Texte officiel : Pull all the way back with Ember for extra range and tougher swing timing.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: ✔; 4: ✔; 5: ✔; 6: ✔; 7: ✔; 8: ✔; 9: ✔; 10: ✔; 11: ✔; 12: ✔
- Statut : `physics_required`
- Raison : The official effect depends on proximity, trajectory phase, collision, timing, or physical speed/distance behavior that the static context does not contain.
- Qualification : `geometry_or_trajectory_required`
- Famille technique : `trajectory_physics`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `validated_physics_effect`
- Difficulté : special
- Confiance : high_dependency_confidence
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Record the relevant distance/time/terrain phase and the before/after in-game result across boundary cases.

### Explorer — Wild Rush Speed

- Identifiant : `explorer__wild_rush_speed`
- Classe : **E — Physique ou géométrie non modélisée**
- Possédé : oui
- Niveau utilisateur : 7
- Valeur au niveau utilisateur : 100%
- Texte officiel : When you hit with Explorer as long as the ball is over Rough, Deep Rough, Water or Cart Path it travels X% faster and farther.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: inactive; 6: inactive; 7: 100%; 8: 125%; 9: 150%; 10: 150%; 11: 175%; 12: 200%
- Statut : `physics_required`
- Raison : The official effect depends on proximity, trajectory phase, collision, timing, or physical speed/distance behavior that the static context does not contain.
- Qualification : `geometry_or_trajectory_required`
- Famille technique : `trajectory_physics`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `validated_physics_effect`
- Difficulté : special
- Confiance : high_dependency_confidence
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Record the relevant distance/time/terrain phase and the before/after in-game result across boundary cases.

### Flamethrower — Power Shot

- Identifiant : `flamethrower__power_shot`
- Classe : **E — Physique ou géométrie non modélisée**
- Possédé : oui
- Niveau utilisateur : 7
- Valeur au niveau utilisateur : ✔
- Texte officiel : When you aim and pull back all the way, Flamethrower gradually hits further but is harder to control.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: ✔; 6: ✔; 7: ✔; 8: ✔; 9: ✔; 10: ✔; 11: ✔; 12: ✔; Elite: ✔
- Statut : `physics_required`
- Raison : The official effect depends on proximity, trajectory phase, collision, timing, or physical speed/distance behavior that the static context does not contain.
- Qualification : `geometry_or_trajectory_required`
- Famille technique : `unqualified:power_shot`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : special
- Confiance : high_dependency_confidence
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Record the relevant distance/time/terrain phase and the before/after in-game result across boundary cases.

### Flashpoint — Boundary Rush

- Identifiant : `flashpoint__boundary_rush`
- Classe : **E — Physique ou géométrie non modélisée**
- Possédé : non
- Niveau utilisateur : inconnu/non possédé
- Valeur au niveau utilisateur : inactive/inconnue
- Texte officiel : Shots from this club travel X% further and faster over water or out of bounds.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: inactive; 6: inactive; 7: +50%; 8: +50%; 9: +50%; 10: +50%; 11: +50%; 12: +50%; Elite: +50%
- Statut : `physics_required`
- Raison : The official effect depends on proximity, trajectory phase, collision, timing, or physical speed/distance behavior that the static context does not contain.
- Qualification : `geometry_or_trajectory_required`
- Famille technique : `terrain_condition`
- Primitives disponibles : SELECT_SELF, READ_LEVEL_VALUE, ADD_STAT
- Primitive/donnée manquante : `READ_CONTEXT`
- Difficulté : special
- Confiance : high_dependency_confidence
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Record the relevant distance/time/terrain phase and the before/after in-game result across boundary cases.

### Green Demon — Emerald Rush 75%

- Identifiant : `green_demon__emerald_rush_75`
- Classe : **E — Physique ou géométrie non modélisée**
- Possédé : oui
- Niveau utilisateur : 8
- Valeur au niveau utilisateur : 75%/25%
- Texte officiel : When you hit with Green Demon, as long as the ball is over fairway it travels 75% faster and farther. When over green it travels 25% slower.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: inactive; 6: inactive; 7: 75%/25%; 8: 75%/25%; 9: 75%/25%; 10: 75%/25%; 11: 75%/25%; 12: 75%/25%
- Statut : `physics_required`
- Raison : The official effect depends on proximity, trajectory phase, collision, timing, or physical speed/distance behavior that the static context does not contain.
- Qualification : `geometry_or_trajectory_required`
- Famille technique : `trajectory_physics`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `validated_physics_effect`
- Difficulté : special
- Confiance : high_dependency_confidence
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Record the relevant distance/time/terrain phase and the before/after in-game result across boundary cases.

### Hot Streak — Ground Rush

- Identifiant : `hot_streak__ground_rush`
- Classe : **E — Physique ou géométrie non modélisée**
- Possédé : non
- Niveau utilisateur : inconnu/non possédé
- Valeur au niveau utilisateur : inactive/inconnue
- Texte officiel : Shots from this club travel X% further and faster over any ground.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: inactive; 6: inactive; 7: 75%; 8: 75%; 9: 75%; 10: 75%; 11: 75%; 12: 75%; Elite: 75%
- Statut : `physics_required`
- Raison : The official effect depends on proximity, trajectory phase, collision, timing, or physical speed/distance behavior that the static context does not contain.
- Qualification : `geometry_or_trajectory_required`
- Famille technique : `unqualified:ground_rush`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : special
- Confiance : high_dependency_confidence
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Record the relevant distance/time/terrain phase and the before/after in-game result across boundary cases.

### Huntsman — Tree Bonus +X

- Identifiant : `huntsman__tree_bonus_x`
- Classe : **E — Physique ou géométrie non modélisée**
- Possédé : oui
- Niveau utilisateur : 7
- Valeur au niveau utilisateur : +3
- Texte officiel : Gains up to +X to all stats depending on how many trees are within 25 feet.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: +2; 4: +2; 5: +2; 6: +3; 7: +3; 8: +3; 9: +3; 10: +3; 11: +3; 12: +4; Elite: +7
- Statut : `physics_required`
- Raison : The official effect depends on proximity, trajectory phase, collision, timing, or physical speed/distance behavior that the static context does not contain.
- Qualification : `geometry_or_trajectory_required`
- Famille technique : `terrain_proximity_bonus`
- Primitives disponibles : SELECT_SELF, READ_LEVEL_VALUE, ADD_STAT
- Primitive/donnée manquante : `READ_CONTEXT`
- Difficulté : special
- Confiance : high_dependency_confidence
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Record the relevant distance/time/terrain phase and the before/after in-game result across boundary cases.

### Hydroforce — Water Bonus +X

- Identifiant : `hydroforce__water_bonus_x`
- Classe : **E — Physique ou géométrie non modélisée**
- Possédé : oui
- Niveau utilisateur : 6
- Valeur au niveau utilisateur : +9
- Texte officiel : Gains up to +X to Power and Control stats depending on how close you are to water, and Spin gains half as much.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: +7; 4: +8; 5: +8; 6: +9; 7: +9; 8: +10; 9: +10; 10: +11; 11: +11; 12: +12; Elite: +14
- Statut : `physics_required`
- Raison : The official effect depends on proximity, trajectory phase, collision, timing, or physical speed/distance behavior that the static context does not contain.
- Qualification : `geometry_or_trajectory_required`
- Famille technique : `terrain_condition`
- Primitives disponibles : SELECT_SELF, READ_LEVEL_VALUE, ADD_STAT
- Primitive/donnée manquante : `READ_CONTEXT`
- Difficulté : special
- Confiance : high_dependency_confidence
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Record the relevant distance/time/terrain phase and the before/after in-game result across boundary cases.

### Ironbark — Tree Bonus +X

- Identifiant : `ironbark__tree_bonus_x`
- Classe : **E — Physique ou géométrie non modélisée**
- Possédé : oui
- Niveau utilisateur : 7
- Valeur au niveau utilisateur : +4
- Texte officiel : Gains up to +X to all stats depending on how many trees are within 25 feet.
- Valeurs par niveau : 1: +2; 2: +3; 3: +3; 4: +3; 5: +3; 6: +3; 7: +4; 8: +4; 9: +4; 10: +4; 11: +4; 12: +5; Elite: +7
- Statut : `physics_required`
- Raison : The official effect depends on proximity, trajectory phase, collision, timing, or physical speed/distance behavior that the static context does not contain.
- Qualification : `geometry_or_trajectory_required`
- Famille technique : `terrain_proximity_bonus`
- Primitives disponibles : SELECT_SELF, READ_LEVEL_VALUE, ADD_STAT
- Primitive/donnée manquante : `READ_CONTEXT`
- Difficulté : special
- Confiance : high_dependency_confidence
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Record the relevant distance/time/terrain phase and the before/after in-game result across boundary cases.

### Leviathan — Boundary Bonus

- Identifiant : `leviathan__boundary_bonus`
- Classe : **E — Physique ou géométrie non modélisée**
- Possédé : oui
- Niveau utilisateur : 5
- Valeur au niveau utilisateur : +6
- Texte officiel : Gains up to +X to all stats depending on how much out of bounds area is nearby.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: +6; 6: +6; 7: +6; 8: +7; 9: +7; 10: +8; 11: +8; 12: +8
- Statut : `physics_required`
- Raison : The official effect depends on proximity, trajectory phase, collision, timing, or physical speed/distance behavior that the static context does not contain.
- Qualification : `geometry_or_trajectory_required`
- Famille technique : `unqualified:boundary_bonus`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : special
- Confiance : high_dependency_confidence
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Record the relevant distance/time/terrain phase and the before/after in-game result across boundary cases.

### Leviathan — Water Bonus

- Identifiant : `leviathan__water_bonus`
- Classe : **E — Physique ou géométrie non modélisée**
- Possédé : oui
- Niveau utilisateur : 5
- Valeur au niveau utilisateur : +2
- Texte officiel : Gains up to +X to all stats depending on how close you are to water.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: +2; 6: +3; 7: +3; 8: +3; 9: +3; 10: +3; 11: +3; 12: +4
- Statut : `physics_required`
- Raison : The official effect depends on proximity, trajectory phase, collision, timing, or physical speed/distance behavior that the static context does not contain.
- Qualification : `geometry_or_trajectory_required`
- Famille technique : `terrain_condition`
- Primitives disponibles : SELECT_SELF, READ_LEVEL_VALUE, ADD_STAT
- Primitive/donnée manquante : `READ_CONTEXT`
- Difficulté : special
- Confiance : high_dependency_confidence
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Record the relevant distance/time/terrain phase and the before/after in-game result across boundary cases.

### Leviathan — Water Rush

- Identifiant : `leviathan__water_rush`
- Classe : **E — Physique ou géométrie non modélisée**
- Possédé : oui
- Niveau utilisateur : 5
- Valeur au niveau utilisateur : 100%
- Texte officiel : When you hit with Leviathan as long as the ball is over Water it travels X% faster and farther.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: 100%; 6: 100%; 7: 100%; 8: 100%; 9: 100%; 10: 100%; 11: 100%; 12: 100%
- Statut : `physics_required`
- Raison : The official effect depends on proximity, trajectory phase, collision, timing, or physical speed/distance behavior that the static context does not contain.
- Qualification : `geometry_or_trajectory_required`
- Famille technique : `trajectory_physics`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `validated_physics_effect`
- Difficulté : special
- Confiance : high_dependency_confidence
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Record the relevant distance/time/terrain phase and the before/after in-game result across boundary cases.

### Meanderer — Green Grip

- Identifiant : `meanderer__green_grip`
- Classe : **E — Physique ou géométrie non modélisée**
- Possédé : oui
- Niveau utilisateur : 8
- Valeur au niveau utilisateur : 60%
- Texte officiel : When you hit with Meanderer, as long as the ball is over green it travels X% slower.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: inactive; 6: inactive; 7: 60%; 8: 60%; 9: 60%; 10: 60%; 11: 60%; 12: 60%; Elite: 75%
- Statut : `physics_required`
- Raison : The official effect depends on proximity, trajectory phase, collision, timing, or physical speed/distance behavior that the static context does not contain.
- Qualification : `geometry_or_trajectory_required`
- Famille technique : `unqualified:green_grip`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : special
- Confiance : high_dependency_confidence
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Record the relevant distance/time/terrain phase and the before/after in-game result across boundary cases.

### Meteor — Alien World

- Identifiant : `meteor__alien_world`
- Classe : **E — Physique ou géométrie non modélisée**
- Possédé : non
- Niveau utilisateur : inconnu/non possédé
- Valeur au niveau utilisateur : inactive/inconnue
- Texte officiel : When you hit with Meteor, the ball bounces off of fairway. (Forever.)
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: inactive; 6: inactive; 7: inactive; 8: inactive; 9: inactive; 10: inactive; 11: inactive; 12: ✔; Elite: ✔
- Statut : `physics_required`
- Raison : The official effect depends on proximity, trajectory phase, collision, timing, or physical speed/distance behavior that the static context does not contain.
- Qualification : `geometry_or_trajectory_required`
- Famille technique : `terrain_condition`
- Primitives disponibles : SELECT_SELF, READ_LEVEL_VALUE, ADD_STAT
- Primitive/donnée manquante : `READ_CONTEXT`
- Difficulté : special
- Confiance : high_dependency_confidence
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Record the relevant distance/time/terrain phase and the before/after in-game result across boundary cases.

### Neon Impulse — Power Shot

- Identifiant : `neon_impulse__power_shot`
- Classe : **E — Physique ou géométrie non modélisée**
- Possédé : oui
- Niveau utilisateur : 7
- Valeur au niveau utilisateur : ✔
- Texte officiel : Pull all the way back with Neon Impulse for extra range and tougher swing timing.
- Valeurs par niveau : 1: ✔; 2: ✔; 3: ✔; 4: ✔; 5: ✔; 6: ✔; 7: ✔; 8: ✔; 9: ✔; 10: ✔; 11: ✔; 12: ✔; Elite: ✔
- Statut : `physics_required`
- Raison : The official effect depends on proximity, trajectory phase, collision, timing, or physical speed/distance behavior that the static context does not contain.
- Qualification : `geometry_or_trajectory_required`
- Famille technique : `trajectory_physics`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `validated_physics_effect`
- Difficulté : special
- Confiance : high_dependency_confidence
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Record the relevant distance/time/terrain phase and the before/after in-game result across boundary cases.

### Oakheart — Tree Bonus +X

- Identifiant : `oakheart__tree_bonus_x`
- Classe : **E — Physique ou géométrie non modélisée**
- Possédé : oui
- Niveau utilisateur : 6
- Valeur au niveau utilisateur : +3
- Texte officiel : Gains up to +X to all stats depending on how many trees are within 25 feet.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: +3; 6: +3; 7: +3; 8: +4; 9: +4; 10: +4; 11: +4; 12: +5
- Statut : `physics_required`
- Raison : The official effect depends on proximity, trajectory phase, collision, timing, or physical speed/distance behavior that the static context does not contain.
- Qualification : `geometry_or_trajectory_required`
- Famille technique : `terrain_proximity_bonus`
- Primitives disponibles : SELECT_SELF, READ_LEVEL_VALUE, ADD_STAT
- Primitive/donnée manquante : `READ_CONTEXT`
- Difficulté : special
- Confiance : high_dependency_confidence
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Record the relevant distance/time/terrain phase and the before/after in-game result across boundary cases.

### Outset — Tree Bonus

- Identifiant : `outset__tree_bonus`
- Classe : **E — Physique ou géométrie non modélisée**
- Possédé : oui
- Niveau utilisateur : 8
- Valeur au niveau utilisateur : +3
- Texte officiel : Gains up to +X to all stats depending on how many trees are within 25 feet.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: +2; 6: +3; 7: +3; 8: +3; 9: +3; 10: +3; 11: +3; 12: +4
- Statut : `physics_required`
- Raison : The official effect depends on proximity, trajectory phase, collision, timing, or physical speed/distance behavior that the static context does not contain.
- Qualification : `geometry_or_trajectory_required`
- Famille technique : `terrain_proximity_bonus`
- Primitives disponibles : SELECT_SELF, READ_LEVEL_VALUE, ADD_STAT
- Primitive/donnée manquante : `READ_CONTEXT`
- Difficulté : special
- Confiance : high_dependency_confidence
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Record the relevant distance/time/terrain phase and the before/after in-game result across boundary cases.

### Rolling Stone — Momentum

- Identifiant : `rolling_stone__momentum`
- Classe : **E — Physique ou géométrie non modélisée**
- Possédé : oui
- Niveau utilisateur : 7
- Valeur au niveau utilisateur : 1.05
- Texte officiel : For every X seconds the ball is on the ground rolling, Rolling Stone and adjacent clubs gain +1 Power.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: 1.82; 4: 1.54; 5: 1.33; 6: 1.18; 7: 1.05; 8: 0.95; 9: 0.87; 10: 0.8; 11: 0.74; 12: 0.7
- Statut : `physics_required`
- Raison : The official effect depends on proximity, trajectory phase, collision, timing, or physical speed/distance behavior that the static context does not contain.
- Qualification : `geometry_or_trajectory_required`
- Famille technique : `unqualified:momentum`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : special
- Confiance : high_dependency_confidence
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Record the relevant distance/time/terrain phase and the before/after in-game result across boundary cases.

### Skyfury — Boundary Rush 75%

- Identifiant : `skyfury__boundary_rush_75`
- Classe : **E — Physique ou géométrie non modélisée**
- Possédé : oui
- Niveau utilisateur : 7
- Valeur au niveau utilisateur : 75%
- Texte officiel : When you hit with Skyfury, as long as the ball is over water or out of bounds, it travels 75% faster and farther.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: 75%; 6: 75%; 7: 75%; 8: 75%; 9: 75%; 10: 75%; 11: 75%; 12: 75%; Elite: 75%
- Statut : `physics_required`
- Raison : The official effect depends on proximity, trajectory phase, collision, timing, or physical speed/distance behavior that the static context does not contain.
- Qualification : `geometry_or_trajectory_required`
- Famille technique : `trajectory_physics`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `validated_physics_effect`
- Difficulté : special
- Confiance : high_dependency_confidence
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Record the relevant distance/time/terrain phase and the before/after in-game result across boundary cases.

### The Seeker — Bag Tree Bonus

- Identifiant : `the_seeker__bag_tree_bonus`
- Classe : **E — Physique ou géométrie non modélisée**
- Possédé : oui
- Niveau utilisateur : 7
- Valeur au niveau utilisateur : inactive/inconnue
- Texte officiel : All clubs gain up to +4 to all stats depending on how many trees are within 82 feet.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: inactive; 6: inactive; 7: inactive; 8: inactive; 9: inactive; 10: inactive; 11: inactive; 12: +4
- Statut : `physics_required`
- Raison : The official effect depends on proximity, trajectory phase, collision, timing, or physical speed/distance behavior that the static context does not contain.
- Qualification : `geometry_or_trajectory_required`
- Famille technique : `terrain_proximity_bonus`
- Primitives disponibles : SELECT_SELF, READ_LEVEL_VALUE, ADD_STAT
- Primitive/donnée manquante : `READ_CONTEXT`
- Difficulté : special
- Confiance : high_dependency_confidence
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Record the relevant distance/time/terrain phase and the before/after in-game result across boundary cases.

### The Seeker — Bag Tree Passing

- Identifiant : `the_seeker__bag_tree_passing`
- Classe : **E — Physique ou géométrie non modélisée**
- Possédé : oui
- Niveau utilisateur : 7
- Valeur au niveau utilisateur : ✔
- Texte officiel : Balls hit by all of your clubs move through trees without slowing down.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: inactive; 6: inactive; 7: ✔; 8: ✔; 9: ✔; 10: ✔; 11: ✔; 12: ✔
- Statut : `physics_required`
- Raison : The official effect depends on proximity, trajectory phase, collision, timing, or physical speed/distance behavior that the static context does not contain.
- Qualification : `geometry_or_trajectory_required`
- Famille technique : `terrain_condition`
- Primitives disponibles : SELECT_SELF, READ_LEVEL_VALUE, ADD_STAT
- Primitive/donnée manquante : `READ_CONTEXT`
- Difficulté : special
- Confiance : high_dependency_confidence
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Record the relevant distance/time/terrain phase and the before/after in-game result across boundary cases.

### Trailblazer — Tree Passing

- Identifiant : `trailblazer__tree_passing`
- Classe : **E — Physique ou géométrie non modélisée**
- Possédé : oui
- Niveau utilisateur : 7
- Valeur au niveau utilisateur : ✔
- Texte officiel : Balls hit by Trailblazer move through trees without slowing down.  - Elite Level: Tree Passing also applies to the club to the right of Trailblazer.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: ✔; 6: ✔; 7: ✔; 8: ✔; 9: ✔; 10: ✔; 11: ✔; 12: ✔; Elite: ✔
- Statut : `physics_required`
- Raison : The official effect depends on proximity, trajectory phase, collision, timing, or physical speed/distance behavior that the static context does not contain.
- Qualification : `geometry_or_trajectory_required`
- Famille technique : `terrain_condition`
- Primitives disponibles : SELECT_SELF, READ_LEVEL_VALUE, ADD_STAT
- Primitive/donnée manquante : `READ_CONTEXT`
- Difficulté : special
- Confiance : high_dependency_confidence
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Record the relevant distance/time/terrain phase and the before/after in-game result across boundary cases.

### Wave — Shoreline Rush

- Identifiant : `wave__shoreline_rush`
- Classe : **E — Physique ou géométrie non modélisée**
- Possédé : oui
- Niveau utilisateur : 7
- Valeur au niveau utilisateur : 125%
- Texte officiel : When you hit with Wave as long as the ball is over Water or Sand it travels X% faster and farther.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: inactive; 6: inactive; 7: 125%; 8: 130%; 9: 135%; 10: 140%; 11: 145%; 12: 150%
- Statut : `physics_required`
- Raison : The official effect depends on proximity, trajectory phase, collision, timing, or physical speed/distance behavior that the static context does not contain.
- Qualification : `geometry_or_trajectory_required`
- Famille technique : `trajectory_physics`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `validated_physics_effect`
- Difficulté : special
- Confiance : high_dependency_confidence
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Record the relevant distance/time/terrain phase and the before/after in-game result across boundary cases.

### Windstrike — Boundary Bonus

- Identifiant : `windstrike__boundary_bonus`
- Classe : **E — Physique ou géométrie non modélisée**
- Possédé : oui
- Niveau utilisateur : 8
- Valeur au niveau utilisateur : +10
- Texte officiel : Gains up to +X to Power and Control stats depending on how close you are to the boundary, and Spin gains half as much.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: +7; 4: +8; 5: +8; 6: +9; 7: +9; 8: +10; 9: +10; 10: +11; 11: +11; 12: +12
- Statut : `physics_required`
- Raison : The official effect depends on proximity, trajectory phase, collision, timing, or physical speed/distance behavior that the static context does not contain.
- Qualification : `geometry_or_trajectory_required`
- Famille technique : `unqualified:boundary_bonus`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : special
- Confiance : high_dependency_confidence
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Record the relevant distance/time/terrain phase and the before/after in-game result across boundary cases.

### Color Theory — Perfect Shot - Terrain Bonus Boost

- Identifiant : `color_theory__perfect_shot_terrain_bonus_boost`
- Classe : **F — Historique de coups ou état temporel complexe**
- Possédé : oui
- Niveau utilisateur : 7
- Valeur au niveau utilisateur : +1
- Texte officiel : If your previous shot was a 'Perfect' boost this club's Terrain Bonuses by +X.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: +1; 6: +1; 7: +1; 8: +1; 9: +2; 10: +2; 11: +2; 12: +2; Elite: +4
- Statut : `history_required`
- Raison : The trigger is identifiable, but duration, reset, consumption, or stacking semantics are not fully specified by the official text.
- Qualification : `state_duration_or_trigger_unknown`
- Famille technique : `previous_shot_condition`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : stateful
- Confiance : medium
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Trigger the effect once, change club, repeat it, and observe persistence, reset, and stacking separately.

### Flamethrower — Perfect Shot: Bag Power

- Identifiant : `flamethrower__perfect_shot_bag_power`
- Classe : **F — Historique de coups ou état temporel complexe**
- Possédé : oui
- Niveau utilisateur : 7
- Valeur au niveau utilisateur : +4
- Texte officiel : When you score a Perfect Shot with this club, your clubs gain +X Power.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: +3; 6: +3; 7: +4; 8: +4; 9: +5; 10: +5; 11: +6; 12: +6; Elite: +6
- Statut : `history_required`
- Raison : The trigger is identifiable, but duration, reset, consumption, or stacking semantics are not fully specified by the official text.
- Qualification : `state_duration_or_trigger_unknown`
- Famille technique : `previous_shot_condition`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : stateful
- Confiance : medium
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Trigger the effect once, change club, repeat it, and observe persistence, reset, and stacking separately.

### Homecoming — Adventure

- Identifiant : `homecoming__adventure`
- Classe : **F — Historique de coups ou état temporel complexe**
- Possédé : oui
- Niveau utilisateur : 8
- Valeur au niveau utilisateur : +3
- Texte officiel : The first time each of your shots hits a tree or lands in a hazard, Homecoming gains +X to all stats.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: inactive; 6: inactive; 7: +3; 8: +3; 9: +4; 10: +4; 11: +4; 12: +4; Elite: +6
- Statut : `history_required`
- Raison : The trigger is identifiable, but duration, reset, consumption, or stacking semantics are not fully specified by the official text.
- Qualification : `state_duration_or_trigger_unknown`
- Famille technique : `unqualified:adventure`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : stateful
- Confiance : medium
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Trigger the effect once, change club, repeat it, and observe persistence, reset, and stacking separately.

### Mimic — Ability Mirror

- Identifiant : `mimic__ability_mirror`
- Classe : **F — Historique de coups ou état temporel complexe**
- Possédé : oui
- Niveau utilisateur : 7
- Valeur au niveau utilisateur : ✔
- Texte officiel : Mimic has the abilities of the last club you hit with this hole.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: ✔; 6: ✔; 7: ✔; 8: ✔; 9: ✔; 10: ✔; 11: ✔; 12: ✔
- Statut : `history_required`
- Raison : The trigger is identifiable, but duration, reset, consumption, or stacking semantics are not fully specified by the official text.
- Qualification : `state_duration_or_trigger_unknown`
- Famille technique : `unqualified:ability_mirror`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : stateful
- Confiance : medium
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Trigger the effect once, change club, repeat it, and observe persistence, reset, and stacking separately.

### Rebound — Volt Bounce

- Identifiant : `rebound__volt_bounce`
- Classe : **F — Historique de coups ou état temporel complexe**
- Possédé : oui
- Niveau utilisateur : 7
- Valeur au niveau utilisateur : +4
- Texte officiel : Bounces once off of Fairway. When you do, clubs in your bag gain +X Power and Control.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: +3; 4: +4; 5: +4; 6: +4; 7: +4; 8: +5; 9: +5; 10: +5; 11: +5; 12: +6; Elite: +7
- Statut : `history_required`
- Raison : The trigger is identifiable, but duration, reset, consumption, or stacking semantics are not fully specified by the official text.
- Qualification : `state_duration_or_trigger_unknown`
- Famille technique : `terrain_condition`
- Primitives disponibles : SELECT_SELF, READ_LEVEL_VALUE, ADD_STAT
- Primitive/donnée manquante : `READ_CONTEXT`
- Difficulté : stateful
- Confiance : medium
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Trigger the effect once, change club, repeat it, and observe persistence, reset, and stacking separately.

### Supercollider — Fission

- Identifiant : `supercollider__fission`
- Classe : **F — Historique de coups ou état temporel complexe**
- Possédé : oui
- Niveau utilisateur : 7
- Valeur au niveau utilisateur : +22
- Texte officiel : After hitting with Supercollider increase its power by X, its control by X, and its spin by X.
- Valeurs par niveau : 1: +12; 2: +15; 3: +16; 4: +18; 5: +19; 6: +21; 7: +22; 8: +24; 9: +25; 10: +27; 11: +28; 12: +30
- Statut : `history_required`
- Raison : The trigger is identifiable, but duration, reset, consumption, or stacking semantics are not fully specified by the official text.
- Qualification : `state_duration_or_trigger_unknown`
- Famille technique : `unqualified:fission`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : stateful
- Confiance : medium
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Trigger the effect once, change club, repeat it, and observe persistence, reset, and stacking separately.

### Tierra Hueca — Gravity Reduction X%

- Identifiant : `tierra_hueca__gravity_reduction_x`
- Classe : **F — Historique de coups ou état temporel complexe**
- Possédé : oui
- Niveau utilisateur : 7
- Valeur au niveau utilisateur : 15%
- Texte officiel : When you hit with Tierra Hueca, reduce gravity by X%. This effect stacks.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: inactive; 6: inactive; 7: 15%; 8: 16%; 9: 17%; 10: 18%; 11: 19%; 12: 20%; Elite: 23%
- Statut : `history_required`
- Raison : The trigger is identifiable, but duration, reset, consumption, or stacking semantics are not fully specified by the official text.
- Qualification : `state_duration_or_trigger_unknown`
- Famille technique : `unqualified:gravity_reduction_x`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : stateful
- Confiance : medium
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Trigger the effect once, change club, repeat it, and observe persistence, reset, and stacking separately.

### Tierra Hueca — Hollow Earth

- Identifiant : `tierra_hueca__hollow_earth`
- Classe : **F — Historique de coups ou état temporel complexe**
- Possédé : oui
- Niveau utilisateur : 7
- Valeur au niveau utilisateur : inactive/inconnue
- Texte officiel : If your last shot was with Tierra Hueca, other clubs have -X power and +X control.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: inactive; 6: inactive; 7: inactive; 8: inactive; 9: inactive; 10: inactive; 11: inactive; 12: inactive; Elite: +8
- Statut : `history_required`
- Raison : The trigger is identifiable, but duration, reset, consumption, or stacking semantics are not fully specified by the official text.
- Qualification : `state_duration_or_trigger_unknown`
- Famille technique : `unqualified:hollow_earth`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : stateful
- Confiance : medium
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Trigger the effect once, change club, repeat it, and observe persistence, reset, and stacking separately.

### Tierra Hueca — Palo Control On Hit +X

- Identifiant : `tierra_hueca__palo_control_on_hit_x`
- Classe : **F — Historique de coups ou état temporel complexe**
- Possédé : oui
- Niveau utilisateur : 7
- Valeur au niveau utilisateur : +1
- Texte officiel : When you hit with Tierra Hueca, increase the control of PALO clubs by X.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: inactive; 6: inactive; 7: +1; 8: +1; 9: +1; 10: +1; 11: +1; 12: +2; Elite: +3
- Statut : `history_required`
- Raison : The trigger is identifiable, but duration, reset, consumption, or stacking semantics are not fully specified by the official text.
- Qualification : `state_duration_or_trigger_unknown`
- Famille technique : `unqualified:palo_control_on_hit_x`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : stateful
- Confiance : medium
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Trigger the effect once, change club, repeat it, and observe persistence, reset, and stacking separately.

### XLR8R — Wind-Up Toy

- Identifiant : `xlr8r__wind_up_toy`
- Classe : **F — Historique de coups ou état temporel complexe**
- Possédé : oui
- Niveau utilisateur : 7
- Valeur au niveau utilisateur : 11
- Texte officiel : When you hit with XLR8R, the wind starts blowing Xmph faster in the direction of the hole.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: inactive; 6: inactive; 7: 11; 8: 12.6; 9: 13.8; 10: 14.6; 11: 15.2; 12: 15.7; Elite: 17
- Statut : `history_required`
- Raison : The trigger is identifiable, but duration, reset, consumption, or stacking semantics are not fully specified by the official text.
- Qualification : `state_duration_or_trigger_unknown`
- Famille technique : `wind_resistance`
- Primitives disponibles : SELECT_SELF, READ_LEVEL_VALUE, ADD_MODIFIER
- Primitive/donnée manquante : `READ_CONTEXT`
- Difficulté : stateful
- Confiance : medium
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Trigger the effect once, change club, repeat it, and observe persistence, reset, and stacking separately.

### Chimera — Beast Strength

- Identifiant : `chimera__beast_strength`
- Classe : **G — Aléatoire ou transformation**
- Possédé : non
- Niveau utilisateur : inconnu/non possédé
- Valeur au niveau utilisateur : inactive/inconnue
- Texte officiel : Hole Start: The random clubs gain Chimera's base stats.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: inactive; 6: inactive; 7: inactive; 8: inactive; 9: inactive; 10: ✔; 11: ✔; 12: ✔
- Statut : `unsupported`
- Raison : The ability performs random selection, destruction, replacement, or bag transformation outside deterministic comparison.
- Qualification : `random_or_transformational`
- Famille technique : `unqualified:beast_strength`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : special
- Confiance : high_dependency_confidence
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : aucune expérience qualifiée

### Chimera — Three Heads

- Identifiant : `chimera__three_heads`
- Classe : **G — Aléatoire ou transformation**
- Possédé : non
- Niveau utilisateur : inconnu/non possédé
- Valeur au niveau utilisateur : inactive/inconnue
- Texte officiel : Hole Start: Replace Chimera with three random clubs.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: inactive; 6: inactive; 7: inactive; 8: inactive; 9: ✔; 10: ✔; 11: ✔; 12: ✔
- Statut : `unsupported`
- Raison : The ability performs random selection, destruction, replacement, or bag transformation outside deterministic comparison.
- Qualification : `random_or_transformational`
- Famille technique : `unqualified:three_heads`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : special
- Confiance : high_dependency_confidence
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : aucune expérience qualifiée

### Crystallize — Random Boost +X

- Identifiant : `crystallize__random_boost_x`
- Classe : **G — Aléatoire ou transformation**
- Possédé : oui
- Niveau utilisateur : 6
- Valeur au niveau utilisateur : +2
- Texte officiel : Gives 3 random clubs in your bag +X Power.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: +2; 6: +2; 7: +2; 8: +3; 9: +3; 10: +3; 11: +4; 12: +4; Elite: +4
- Statut : `unsupported`
- Raison : The ability performs random selection, destruction, replacement, or bag transformation outside deterministic comparison.
- Qualification : `random_or_transformational`
- Famille technique : `unqualified:random_boost_x`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : special
- Confiance : high_dependency_confidence
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : aucune expérience qualifiée

### Fanfare — Trumpet Blast

- Identifiant : `fanfare__trumpet_blast`
- Classe : **G — Aléatoire ou transformation**
- Possédé : oui
- Niveau utilisateur : 7
- Valeur au niveau utilisateur : +6
- Texte officiel : Applies a Power Stat bonus to a random club in your bag at the start of the game (including to Fanfare itself). - Elite Level:  Trumpet Blast will apply to 2 random clubs.
- Valeurs par niveau : 1: +5; 2: +5; 3: +5; 4: +6; 5: +6; 6: +6; 7: +6; 8: +7; 9: +7; 10: +7; 11: +7; 12: +8; Elite: +8
- Statut : `unsupported`
- Raison : The ability performs random selection, destruction, replacement, or bag transformation outside deterministic comparison.
- Qualification : `random_or_transformational`
- Famille technique : `unqualified:trumpet_blast`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : special
- Confiance : high_dependency_confidence
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : aucune expérience qualifiée

### Outlaw — Shuffle Up

- Identifiant : `outlaw__shuffle_up`
- Classe : **G — Aléatoire ou transformation**
- Possédé : oui
- Niveau utilisateur : 7
- Valeur au niveau utilisateur : ✔
- Texte officiel : At the start of each hole, shuffle your hand except for the leftmost and rightmost clubs (randomize the position of each club).
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: inactive; 6: inactive; 7: ✔; 8: ✔; 9: ✔; 10: ✔; 11: ✔; 12: ✔; Elite: ✔
- Statut : `unsupported`
- Raison : The ability performs random selection, destruction, replacement, or bag transformation outside deterministic comparison.
- Qualification : `random_or_transformational`
- Famille technique : `unqualified:shuffle_up`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : special
- Confiance : high_dependency_confidence
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : aucune expérience qualifiée

### The Reaper — Sacrifice

- Identifiant : `the_reaper__sacrifice`
- Classe : **G — Aléatoire ou transformation**
- Possédé : non
- Niveau utilisateur : inconnu/non possédé
- Valeur au niveau utilisateur : inactive/inconnue
- Texte officiel : At the start of the game, destroy another random club. The Reaper steals its stats.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: inactive; 6: inactive; 7: inactive; 8: inactive; 9: ✔; 10: ✔; 11: ✔; 12: ✔
- Statut : `unsupported`
- Raison : The ability performs random selection, destruction, replacement, or bag transformation outside deterministic comparison.
- Qualification : `random_or_transformational`
- Famille technique : `unqualified:sacrifice`
- Primitives disponibles : aucune
- Primitive/donnée manquante : `semantic_qualification`
- Difficulté : special
- Confiance : high_dependency_confidence
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : aucune expérience qualifiée

### Crusader — Brand Fairway Rush

- Identifiant : `crusader__brand_fairway_rush`
- Classe : **H — Partiellement simulée**
- Possédé : oui
- Niveau utilisateur : 5
- Valeur au niveau utilisateur : 2/17%
- Texte officiel : Your Willoughsby clubs have +X Power. Additionally, shots from Willoughsby clubs fly X% faster and farther over Fairway.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: 1/15%; 4: 1/16%; 5: 2/17%; 6: 2/18%; 7: 2/20%; 8: 2/21%; 9: 2/22%; 10: 2/23%; 11: 2/24%; 12: 3/25%; Elite: 3/50%
- Statut : `partial`
- Raison : The Willoughsby Power component is exact; fairway speed/distance still requires a physics contract.
- Qualification : `clear_component_plus_physics`
- Famille technique : `composed_partial`
- Primitives disponibles : SELECT_SELF, READ_LEVEL_VALUE, SELECT_ALL, MATCH_BRAND, FOR_EACH, ADD_STAT
- Primitive/donnée manquante : `validation_or_external_model`
- Difficulté : special
- Confiance : high_for_resolved_component_only
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Measure the speed/distance or tree-collision component independently in game.

### Ranger — Forester Power (Elite)

- Identifiant : `ranger__forester_power_elite`
- Classe : **H — Partiellement simulée**
- Possédé : oui
- Niveau utilisateur : 7
- Valeur au niveau utilisateur : inactive/inconnue
- Texte officiel : Forester clubs have +X Power and pass through trees.
- Valeurs par niveau : 1: inactive; 2: inactive; 3: inactive; 4: inactive; 5: inactive; 6: inactive; 7: inactive; 8: inactive; 9: inactive; 10: inactive; 11: inactive; 12: inactive; Elite: +3
- Statut : `partial`
- Raison : The Forester Power component is exact; tree passing still requires collision semantics.
- Qualification : `clear_component_plus_physics`
- Famille technique : `composed_partial`
- Primitives disponibles : SELECT_SELF, READ_LEVEL_VALUE, SELECT_ALL, MATCH_BRAND, FOR_EACH, ADD_STAT
- Primitive/donnée manquante : `validation_or_external_model`
- Difficulté : special
- Confiance : high_for_resolved_component_only
- Provenance : `official_versioned_catalog_and_qualified_semantic_map`
- Validation proposée : Measure the speed/distance or tree-collision component independently in game.
