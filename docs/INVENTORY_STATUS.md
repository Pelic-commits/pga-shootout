# User Inventory Status

> Generated from official, normalized, engine-registry and user data by `pga-shootout inventory-status --write-reports`.

## Summary

| Measure | Value |
|---|---:|
| Known inventory clubs | 20 |
| Inventory declared complete | no |
| Known user levels | 0/20 |
| Official owned-club abilities | 35 |
| Engine-supported owned-club abilities | 21 |
| Unresolved owned-club abilities | 14 |
| Owned-ability coverage | 60.00% |
| Fully simulated owned clubs | 8/20 |

## Clubs

| Club | Brand | Type | Rarity | User level | Abilities | Fully simulated | compare-bags | Static optimizer |
|---|---|---|---|---:|---:|---|---|---|
| Homestead (`homestead`) | Willoughsby | Putter | Common | unknown | 1/1 | yes | yes | partially |
| Commonlaw (`commonlaw`) | Willoughsby | Iron | Epic | unknown | 2/2 | yes | yes | partially |
| Kinship (`kinship`) | Willoughsby | Iron | Rare | unknown | 1/2 | no | partially | partially |
| Groundskeep (`groundskeep`) | Willoughsby | Wood | Rare | unknown | 1/2 | no | partially | partially |
| Sandsend (`sandsend`) | Willoughsby | Wedge | Common | unknown | 1/1 | yes | yes | partially |
| Steadfast (`steadfast`) | Willoughsby | Wedge | Epic | unknown | 2/2 | yes | yes | partially |
| Jumpstart (`jumpstart`) | Ryusei | Wood | Rare | unknown | 1/1 | yes | yes | partially |
| Cyclotron (`cyclotron`) | Ryusei | Driver | Rare | unknown | 1/2 | no | partially | partially |
| Neon Impulse (`neon_impulse`) | Ryusei | Wood | Common | unknown | 0/1 | no | partially | partially |
| Color Theory (`color_theory`) | Ryusei | Iron | Epic | unknown | 0/2 | no | partially | partially |
| High Flight (`high_flight`) | Corvid | Hybrid | Common | unknown | 1/2 | no | partially | partially |
| Cloudcatcher (`cloudcatcher`) | Corvid | Iron | Epic | unknown | 3/3 | yes | yes | partially |
| Skyfury (`skyfury`) | Corvid | Driver | Epic | unknown | 0/1 | no | partially | partially |
| Rook (`rook`) | Corvid | Putter | Common | unknown | 1/2 | no | partially | partially |
| Mirage (`mirage`) | PALO | Hybrid | Common | unknown | 2/2 | yes | yes | partially |
| Lodestar (`lodestar`) | PALO | Iron | Epic | unknown | 1/2 | no | partially | partially |
| Green Demon (`green_demon`) | PALO | Driver | Legendary | unknown | 0/1 | no | partially | partially |
| Outset (`outset`) | Forester | Driver | Rare | unknown | 0/2 | no | partially | partially |
| Into the Breach (`into_the_breach`) | Stanchion | Iron | Epic | unknown | 2/2 | yes | yes | partially |
| Conqueror (`conqueror`) | Stanchion | Driver | Rare | unknown | 1/2 | no | partially | partially |

### Homestead

| Official ability | Official text | Activates | Status | Metrics | Reason | Needed | Technical family |
|---|---|---:|---|---|---|---|---|
| Brand Loyalty +X (`homestead__brand_loyalty_x`) | Has +X power per Willoughsby club next to Homestead. | 3 | `missing_user_level` | `power` | The engine supports this ability, but the user's current club level is unknown. | `current_level` | `dsl_pipeline` |

### Commonlaw

| Official ability | Official text | Activates | Status | Metrics | Reason | Needed | Technical family |
|---|---|---:|---|---|---|---|---|
| Bag Control (`commonlaw__bag_control`) | Your other clubs gain +X control. | 5 | `missing_user_level` | `control` | The engine supports this ability, but the user's current club level is unknown. | `current_level` | `dsl_pipeline` |
| Brand Loyalty +X (`commonlaw__brand_loyalty_x`) | Has +X power per Willoughsby club next to Commonlaw. | 5 | `missing_user_level` | `power` | The engine supports this ability, but the user's current club level is unknown. | `current_level` | `dsl_pipeline` |

### Kinship

| Official ability | Official text | Activates | Status | Metrics | Reason | Needed | Technical family |
|---|---|---:|---|---|---|---|---|
| Chains into Willoughsby (`kinship__chains_into_willoughsby`) | Chains into Willoughsby. (On your next shot, Willoughsby clubs have +X to all stats.) | 3 | `history_required` | none | The ability depends on a previous or future shot and the history scheduler is not implemented. | `shot_history`, `trigger_and_consumption_validation` | `chain_next_shot` |
| Brand Loyalty +X (`kinship__brand_loyalty_x`) | Has +X power per Willoughsby club next to Kinship. | 5 | `missing_user_level` | `power` | The engine supports this ability, but the user's current club level is unknown. | `current_level` | `dsl_pipeline` |

### Groundskeep

| Official ability | Official text | Activates | Status | Metrics | Reason | Needed | Technical family |
|---|---|---:|---|---|---|---|---|
| Fairway Affinity (`groundskeep__fairway_affinity`) | Your Willoughsby Clubs have +X to all stats when hitting from the fairway. - Elite Level: Fairway Affinity will now apply on Tee Boxes as well. | 3 | `scenario_required` | none | The ability requires an explicit terrain scenario that is absent from the static comparator. | `terrain` | `terrain_condition` |
| Brand Loyalty +X (`groundskeep__brand_loyalty_x`) | Has +X power per Willoughsby club next to Groundskeep. | 6 | `missing_user_level` | `power` | The engine supports this ability, but the user's current club level is unknown. | `current_level` | `dsl_pipeline` |

### Sandsend

| Official ability | Official text | Activates | Status | Metrics | Reason | Needed | Technical family |
|---|---|---:|---|---|---|---|---|
| Brand Loyalty +X (`sandsend__brand_loyalty_x`) | Has +X power per Willoughsby club next to Sandsend. | 3 | `missing_user_level` | `power` | The engine supports this ability, but the user's current club level is unknown. | `current_level` | `dsl_pipeline` |

### Steadfast

| Official ability | Official text | Activates | Status | Metrics | Reason | Needed | Technical family |
|---|---|---:|---|---|---|---|---|
| Bag: Rarity Boost (`steadfast__bag_rarity_boost`) | Common and Rare clubs have +X to all stats. | 5 | `missing_user_level` | `control`, `power`, `spin` | The engine supports this ability, but the user's current club level is unknown. | `current_level` | `filtered_bag_multi_stat_bonus` |
| Brand Loyalty +X (`steadfast__brand_loyalty_x`) | Has +X power per Willoughsby club next to Steadfast. | 8 | `missing_user_level` | `power` | The engine supports this ability, but the user's current club level is unknown. | `current_level` | `dsl_pipeline` |

### Jumpstart

| Official ability | Official text | Activates | Status | Metrics | Reason | Needed | Technical family |
|---|---|---:|---|---|---|---|---|
| Power Boost (`jumpstart__power_boost`) | The club to the left of Jumpstart has +X power. | 3 | `missing_user_level` | `power` | The engine supports this ability, but the user's current club level is unknown. | `current_level` | `dsl_pipeline` |

### Cyclotron

| Official ability | Official text | Activates | Status | Metrics | Reason | Needed | Technical family |
|---|---|---:|---|---|---|---|---|
| Spin Boost (`cyclotron__spin_boost`) | The club to the left of Cyclotron has +X spin. | 3 | `missing_user_level` | `spin` | The engine supports this ability, but the user's current club level is unknown. | `current_level` | `dsl_pipeline` |
| Bounce Reduction Boost (`cyclotron__bounce_reduction_boost`) | The club to the left of Cyclotron produces strokes with less bounce. | 5 | `ambiguous` | none | The text omits the numeric placeholder and the bounce stacking rule is not qualified. | `official_text_table_validation`, `stacking_validation` | `static_bounce_modifier` |

### Neon Impulse

| Official ability | Official text | Activates | Status | Metrics | Reason | Needed | Technical family |
|---|---|---:|---|---|---|---|---|
| Power Shot (`neon_impulse__power_shot`) | Pull all the way back with Neon Impulse for extra range and tougher swing timing. | 1 | `physics_required` | none | The official effect changes trajectory, range or timing and needs a validated physics contract. | `physics_contract`, `in_game_validation` | `trajectory_physics` |

### Color Theory

| Official ability | Official text | Activates | Status | Metrics | Reason | Needed | Technical family |
|---|---|---:|---|---|---|---|---|
| Perfect Shot - Terrain Bonus Boost (`color_theory__perfect_shot_terrain_bonus_boost`) | If your previous shot was a 'Perfect' boost this club's Terrain Bonuses by +X. | 5 | `history_required` | none | The ability depends on a previous or future shot and the history scheduler is not implemented. | `shot_history`, `trigger_and_consumption_validation` | `previous_shot_condition` |
| Terrain Bonus (`color_theory__terrain_bonus`) | Rough Bonus +X, Water bonus +X, Tree Bonus +X, Sand Bonus +X | 5 | `scenario_required` | none | The ability requires an explicit terrain scenario that is absent from the static comparator. | `terrain` | `terrain_condition` |

### High Flight

| Official ability | Official text | Activates | Status | Metrics | Reason | Needed | Technical family |
|---|---|---:|---|---|---|---|---|
| Loft Angle +5° (`high_flight__loft_angle_5`) | Launches the ball with a 5° higher angle than other hybrids. | 1 | `missing_user_level` | `loft_angle_degrees` | The engine supports this ability, but the user's current club level is unknown. | `current_level` | `static_modifier_targets` |
| Wind Resist 75% (`high_flight__wind_resist_75`) | High Flight is 75% less affected by wind. | 5 | `scenario_required` | none | The ability needs wind context; its static descriptor and stacking policy are not yet qualified. | `wind_speed`, `stacking_validation` | `wind_resistance` |

### Cloudcatcher

| Official ability | Official text | Activates | Status | Metrics | Reason | Needed | Technical family |
|---|---|---:|---|---|---|---|---|
| Bag Loft Angle +10° (`cloudcatcher__bag_loft_angle_10`) | Your clubs launch the ball with a 10° higher angle. | 5 | `missing_user_level` | `loft_angle_degrees` | The engine supports this ability, but the user's current club level is unknown. | `current_level` | `static_modifier_targets` |
| Bounce Reduction (`cloudcatcher__bounce_reduction`) | Your ball bounces X% less against all terrain | 6 | `missing_user_level` | `bounce_reduction_percent` | The engine supports this ability, but the user's current club level is unknown. | `current_level` | `static_modifier_targets` |
| Brand Loyalty +X (`cloudcatcher__brand_loyalty_x`) | Has +X power per Corvid club next to Cloudcatcher. | 7 | `missing_user_level` | `power` | The engine supports this ability, but the user's current club level is unknown. | `current_level` | `dsl_pipeline` |

### Skyfury

| Official ability | Official text | Activates | Status | Metrics | Reason | Needed | Technical family |
|---|---|---:|---|---|---|---|---|
| Boundary Rush 75% (`skyfury__boundary_rush_75`) | When you hit with Skyfury, as long as the ball is over water or out of bounds, it travels 75% faster and farther. | 5 | `physics_required` | none | The official effect changes trajectory, range or timing and needs a validated physics contract. | `physics_contract`, `in_game_validation` | `trajectory_physics` |

### Rook

| Official ability | Official text | Activates | Status | Metrics | Reason | Needed | Technical family |
|---|---|---:|---|---|---|---|---|
| Bag Wind Resist (`rook__bag_wind_resist`) | Shots are X% less affected by wind. | 1 | `scenario_required` | none | The ability needs wind context; its static descriptor and stacking policy are not yet qualified. | `wind_speed`, `stacking_validation` | `wind_resistance` |
| Brand Loyalty +X (`rook__brand_loyalty_x`) | Has +X power per Corvid club next to Rook. | 3 | `missing_user_level` | `power` | The engine supports this ability, but the user's current club level is unknown. | `current_level` | `dsl_pipeline` |

### Mirage

| Official ability | Official text | Activates | Status | Metrics | Reason | Needed | Technical family |
|---|---|---:|---|---|---|---|---|
| Sand Bounce (`mirage__sand_bounce`) | Bounces up to X times off of sand. | 1 | `missing_user_level` | `sand_bounce_count` | The engine supports this ability, but the user's current club level is unknown. | `current_level` | `static_modifier_targets` |
| Water Bounce (`mirage__water_bounce`) | Bounces up to 2 times off of water. | 5 | `missing_user_level` | `water_bounce_count` | The engine supports this ability, but the user's current club level is unknown. | `current_level` | `static_modifier_targets` |

### Lodestar

| Official ability | Official text | Activates | Status | Metrics | Reason | Needed | Technical family |
|---|---|---:|---|---|---|---|---|
| Fade/Draw x2 (`lodestar__fade_draw_x2`) | Your clubs have double fade and draw. | 5 | `ambiguous` | none | The fade/draw base metric and multiplication/stacking rule are not qualified. | `metric_contract`, `stacking_validation` | `static_shot_control_modifier` |
| Brand Loyalty +X (`lodestar__brand_loyalty_x`) | Has +X power per PALO club next to Lodestar. | 7 | `missing_user_level` | `power` | The engine supports this ability, but the user's current club level is unknown. | `current_level` | `dsl_pipeline` |

### Green Demon

| Official ability | Official text | Activates | Status | Metrics | Reason | Needed | Technical family |
|---|---|---:|---|---|---|---|---|
| Emerald Rush 75% (`green_demon__emerald_rush_75`) | When you hit with Green Demon, as long as the ball is over fairway it travels 75% faster and farther. When over green it travels 25% slower. | 7 | `physics_required` | none | The official effect changes trajectory, range or timing and needs a validated physics contract. | `physics_contract`, `in_game_validation` | `trajectory_physics` |

### Outset

| Official ability | Official text | Activates | Status | Metrics | Reason | Needed | Technical family |
|---|---|---:|---|---|---|---|---|
| Chains into Wedges (`outset__chains_into_wedges`) | Chains into wedges. (On your next shot, wedges have +X to all stats.) | 3 | `history_required` | none | The ability depends on a previous or future shot and the history scheduler is not implemented. | `shot_history`, `trigger_and_consumption_validation` | `chain_next_shot` |
| Tree Bonus (`outset__tree_bonus`) | Gains up to +X to all stats depending on how many trees are within 25 feet. | 5 | `ambiguous` | none | The distance-to-tree formula behind the official 'up to' value is not specified. | `in_game_validation`, `terrain_proximity` | `terrain_proximity_bonus` |

### Into the Breach

| Official ability | Official text | Activates | Status | Metrics | Reason | Needed | Technical family |
|---|---|---:|---|---|---|---|---|
| Bag Recklessness (`into_the_breach__bag_recklessness`) | Your other clubs gain +X power and spin, but lose X control. | 5 | `missing_user_level` | `control`, `power`, `spin` | The engine supports this ability, but the user's current club level is unknown. | `current_level` | `bag_multi_stat_tradeoff` |
| Brand Loyalty +X (`into_the_breach__brand_loyalty_x`) | Has +X power per Stanchion club next to Into the Breach. | 7 | `missing_user_level` | `power` | The engine supports this ability, but the user's current club level is unknown. | `current_level` | `dsl_pipeline` |

### Conqueror

| Official ability | Official text | Activates | Status | Metrics | Reason | Needed | Technical family |
|---|---|---:|---|---|---|---|---|
| Chains into Putters (`conqueror__chains_into_putters`) | Chains into putters. (On your next shot, putters have +X to all stats.) | 3 | `history_required` | none | The ability depends on a previous or future shot and the history scheduler is not implemented. | `shot_history`, `trigger_and_consumption_validation` | `chain_next_shot` |
| Brand Loyalty +X (`conqueror__brand_loyalty_x`) | Has +X power per Stanchion club next to Conqueror. | 5 | `missing_user_level` | `power` | The engine supports this ability, but the user's current club level is unknown. | `current_level` | `dsl_pipeline` |

## Reference bags (regression only)

| Bag | Supported abilities | Coverage |
|---|---:|---:|
| `par3_divebomb` | 5/8 | 62.50% |
| `par3_high_flight` | 6/9 | 66.67% |

## Missing user data

- Current levels: Homestead, Commonlaw, Kinship, Groundskeep, Sandsend, Steadfast, Jumpstart, Cyclotron, Neon Impulse, Color Theory, High Flight, Cloudcatcher, Skyfury, Rook, Mirage, Lodestar, Green Demon, Outset, Into the Breach, Conqueror.
- Inventory completeness: the inventory is explicitly partial.

## Recommended next lots

### 1. Qualify owned-club static modifiers

- Abilities: Bounce Reduction Boost, Fade/Draw x2.
- Owned clubs: Cyclotron, Lodestar.
- Expected ability coverage gain: +2.
- Clubs becoming fully simulated: Cyclotron, Lodestar.
- Difficulty: medium.
- Required: metric and stacking validation.
- Priority: Adds deterministic comparison metrics using the existing target-selection and modifier pipeline.

### 2. Expose wind resistance as an objective modifier

- Abilities: Wind Resist 75%, Bag Wind Resist.
- Owned clubs: High Flight, Rook.
- Expected ability coverage gain: +2.
- Clubs becoming fully simulated: High Flight, Rook.
- Difficulty: medium.
- Required: scope validation, stacking validation.
- Priority: Improves owned par-3 clubs without requiring a full wind simulation for the static descriptor.

### 3. Implement next-shot chains

- Abilities: Chains into Willoughsby, Chains into Wedges, Chains into Putters.
- Owned clubs: Kinship, Outset, Conqueror.
- Expected ability coverage gain: +3.
- Clubs becoming fully simulated: Kinship, Conqueror.
- Difficulty: medium-high.
- Required: history trigger validation, duration and consumption validation.
- Priority: Covers the largest remaining owned-club cluster after deterministic static modifiers.
