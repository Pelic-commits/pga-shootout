# User Inventory Ability Gaps

> Generated automatically by `pga-shootout user-gaps`. Do not edit manually.

## Summary

| Metric | Value |
|---|---:|
| Known inventory clubs | 20 |
| Official ability occurrences | 35 |
| Implemented occurrences | 28 |
| Inventory occurrence coverage | 80.00% |
| Fully implemented clubs | 14 |

## Homestead (`homestead`)

Saved bags: none.

| Official ability | Official text | Pattern | Status | compare-bags impact |
|---|---|---|---|---|
| Brand Loyalty +X (`homestead__brand_loyalty_x`) | Has +X power per Willoughsby club next to Homestead. | `mechanic:dsl_pipeline` | `implemented` | changes a core compared statistic |

## Commonlaw (`commonlaw`)

Saved bags: none.

| Official ability | Official text | Pattern | Status | compare-bags impact |
|---|---|---|---|---|
| Bag Control (`commonlaw__bag_control`) | Your other clubs gain +X control. | `mechanic:dsl_pipeline` | `implemented` | changes a core compared statistic |
| Brand Loyalty +X (`commonlaw__brand_loyalty_x`) | Has +X power per Willoughsby club next to Commonlaw. | `mechanic:dsl_pipeline` | `implemented` | changes a core compared statistic |

## Kinship (`kinship`)

Saved bags: none.

| Official ability | Official text | Pattern | Status | compare-bags impact |
|---|---|---|---|---|
| Chains into Willoughsby (`kinship__chains_into_willoughsby`) | Chains into Willoughsby. (On your next shot, Willoughsby clubs have +X to all stats.) | `delayed_all_stats_by_club_attribute` | `implemented` | included in objective ability contributions |
| Brand Loyalty +X (`kinship__brand_loyalty_x`) | Has +X power per Willoughsby club next to Kinship. | `mechanic:dsl_pipeline` | `implemented` | changes a core compared statistic |

## Groundskeep (`groundskeep`)

Saved bags: none.

| Official ability | Official text | Pattern | Status | compare-bags impact |
|---|---|---|---|---|
| Fairway Affinity (`groundskeep__fairway_affinity`) | Your Willoughsby Clubs have +X to all stats when hitting from the fairway. - Elite Level: Fairway Affinity will now apply on Tee Boxes as well. | `unqualified:fairway_affinity` | `scenario_required` | scenario metric; no effect in the static comparator |
| Brand Loyalty +X (`groundskeep__brand_loyalty_x`) | Has +X power per Willoughsby club next to Groundskeep. | `mechanic:dsl_pipeline` | `implemented` | changes a core compared statistic |

## Sandsend (`sandsend`)

Saved bags: none.

| Official ability | Official text | Pattern | Status | compare-bags impact |
|---|---|---|---|---|
| Brand Loyalty +X (`sandsend__brand_loyalty_x`) | Has +X power per Willoughsby club next to Sandsend. | `mechanic:dsl_pipeline` | `implemented` | changes a core compared statistic |

## Steadfast (`steadfast`)

Saved bags: `par3_divebomb`.

| Official ability | Official text | Pattern | Status | compare-bags impact |
|---|---|---|---|---|
| Bag: Rarity Boost (`steadfast__bag_rarity_boost`) | Common and Rare clubs have +X to all stats. | `filtered_bag_multi_stat_bonus` | `implemented` | included in objective ability contributions |
| Brand Loyalty +X (`steadfast__brand_loyalty_x`) | Has +X power per Willoughsby club next to Steadfast. | `mechanic:dsl_pipeline` | `implemented` | changes a core compared statistic |

## Jumpstart (`jumpstart`)

Saved bags: `par3_divebomb`.

| Official ability | Official text | Pattern | Status | compare-bags impact |
|---|---|---|---|---|
| Power Boost (`jumpstart__power_boost`) | The club to the left of Jumpstart has +X power. | `mechanic:dsl_pipeline` | `implemented` | changes a core compared statistic |

## Cyclotron (`cyclotron`)

Saved bags: `par3_high_flight`.

| Official ability | Official text | Pattern | Status | compare-bags impact |
|---|---|---|---|---|
| Spin Boost (`cyclotron__spin_boost`) | The club to the left of Cyclotron has +X spin. | `mechanic:dsl_pipeline` | `implemented` | changes a core compared statistic |
| Bounce Reduction Boost (`cyclotron__bounce_reduction_boost`) | The club to the left of Cyclotron produces strokes with less bounce. | `static_modifier_targets` | `implemented` | adds or changes a separately compared static metric |

## Neon Impulse (`neon_impulse`)

Saved bags: none.

| Official ability | Official text | Pattern | Status | compare-bags impact |
|---|---|---|---|---|
| Power Shot (`neon_impulse__power_shot`) | Pull all the way back with Neon Impulse for extra range and tougher swing timing. | `unqualified:power_shot` | `ambiguous` | changes a core compared statistic |

## Color Theory (`color_theory`)

Saved bags: none.

| Official ability | Official text | Pattern | Status | compare-bags impact |
|---|---|---|---|---|
| Perfect Shot - Terrain Bonus Boost (`color_theory__perfect_shot_terrain_bonus_boost`) | If your previous shot was a 'Perfect' boost this club's Terrain Bonuses by +X. | `unqualified:perfect_shot_terrain_bonus_boost` | `scenario_required` | scenario metric; no effect in the static comparator |
| Terrain Bonus (`color_theory__terrain_bonus`) | Rough Bonus +X, Water bonus +X, Tree Bonus +X, Sand Bonus +X | `unqualified:terrain_bonus` | `scenario_required` | scenario metric; no effect in the static comparator |

## High Flight (`high_flight`)

Saved bags: `par3_high_flight`.

| Official ability | Official text | Pattern | Status | compare-bags impact |
|---|---|---|---|---|
| Loft Angle +5° (`high_flight__loft_angle_5`) | Launches the ball with a 5° higher angle than other hybrids. | `static_modifier_targets` | `implemented` | adds or changes a separately compared static metric |
| Wind Resist 75% (`high_flight__wind_resist_75`) | High Flight is 75% less affected by wind. | `static_modifier_targets` | `implemented` | included in objective ability contributions |

## Cloudcatcher (`cloudcatcher`)

Saved bags: none.

| Official ability | Official text | Pattern | Status | compare-bags impact |
|---|---|---|---|---|
| Bag Loft Angle +10° (`cloudcatcher__bag_loft_angle_10`) | Your clubs launch the ball with a 10° higher angle. | `static_modifier_targets` | `implemented` | adds or changes a separately compared static metric |
| Bounce Reduction (`cloudcatcher__bounce_reduction`) | Your ball bounces X% less against all terrain | `static_modifier_targets` | `implemented` | adds or changes a separately compared static metric |
| Brand Loyalty +X (`cloudcatcher__brand_loyalty_x`) | Has +X power per Corvid club next to Cloudcatcher. | `mechanic:dsl_pipeline` | `implemented` | changes a core compared statistic |

## Skyfury (`skyfury`)

Saved bags: none.

| Official ability | Official text | Pattern | Status | compare-bags impact |
|---|---|---|---|---|
| Boundary Rush 75% (`skyfury__boundary_rush_75`) | When you hit with Skyfury, as long as the ball is over water or out of bounds, it travels 75% faster and farther. | `unqualified:boundary_rush_75` | `scenario_required` | scenario metric; no effect in the static comparator |

## Rook (`rook`)

Saved bags: none.

| Official ability | Official text | Pattern | Status | compare-bags impact |
|---|---|---|---|---|
| Bag Wind Resist (`rook__bag_wind_resist`) | Shots are X% less affected by wind. | `static_modifier_targets` | `implemented` | included in objective ability contributions |
| Brand Loyalty +X (`rook__brand_loyalty_x`) | Has +X power per Corvid club next to Rook. | `mechanic:dsl_pipeline` | `implemented` | changes a core compared statistic |

## Mirage (`mirage`)

Saved bags: none.

| Official ability | Official text | Pattern | Status | compare-bags impact |
|---|---|---|---|---|
| Sand Bounce (`mirage__sand_bounce`) | Bounces up to X times off of sand. | `static_modifier_targets` | `implemented` | adds or changes a separately compared static metric |
| Water Bounce (`mirage__water_bounce`) | Bounces up to 2 times off of water. | `static_modifier_targets` | `implemented` | adds or changes a separately compared static metric |

## Lodestar (`lodestar`)

Saved bags: none.

| Official ability | Official text | Pattern | Status | compare-bags impact |
|---|---|---|---|---|
| Fade/Draw x2 (`lodestar__fade_draw_x2`) | Your clubs have double fade and draw. | `static_modifier_targets` | `implemented` | adds or changes a separately compared static metric |
| Brand Loyalty +X (`lodestar__brand_loyalty_x`) | Has +X power per PALO club next to Lodestar. | `mechanic:dsl_pipeline` | `implemented` | changes a core compared statistic |

## Green Demon (`green_demon`)

Saved bags: none.

| Official ability | Official text | Pattern | Status | compare-bags impact |
|---|---|---|---|---|
| Emerald Rush 75% (`green_demon__emerald_rush_75`) | When you hit with Green Demon, as long as the ball is over fairway it travels 75% faster and farther. When over green it travels 25% slower. | `unqualified:emerald_rush_75` | `scenario_required` | scenario metric; no effect in the static comparator |

## Outset (`outset`)

Saved bags: none.

| Official ability | Official text | Pattern | Status | compare-bags impact |
|---|---|---|---|---|
| Chains into Wedges (`outset__chains_into_wedges`) | Chains into wedges. (On your next shot, wedges have +X to all stats.) | `delayed_all_stats_by_club_attribute` | `implemented` | included in objective ability contributions |
| Tree Bonus (`outset__tree_bonus`) | Gains up to +X to all stats depending on how many trees are within 25 feet. | `unqualified:tree_bonus` | `ambiguous` | impact cannot be quantified before semantic qualification |

## Into the Breach (`into_the_breach`)

Saved bags: none.

| Official ability | Official text | Pattern | Status | compare-bags impact |
|---|---|---|---|---|
| Bag Recklessness (`into_the_breach__bag_recklessness`) | Your other clubs gain +X power and spin, but lose X control. | `bag_multi_stat_tradeoff` | `implemented` | changes a core compared statistic |
| Brand Loyalty +X (`into_the_breach__brand_loyalty_x`) | Has +X power per Stanchion club next to Into the Breach. | `mechanic:dsl_pipeline` | `implemented` | changes a core compared statistic |

## Conqueror (`conqueror`)

Saved bags: none.

| Official ability | Official text | Pattern | Status | compare-bags impact |
|---|---|---|---|---|
| Chains into Putters (`conqueror__chains_into_putters`) | Chains into putters. (On your next shot, putters have +X to all stats.) | `delayed_all_stats_by_club_attribute` | `implemented` | included in objective ability contributions |
| Brand Loyalty +X (`conqueror__brand_loyalty_x`) | Has +X power per Stanchion club next to Conqueror. | `mechanic:dsl_pipeline` | `implemented` | changes a core compared statistic |
