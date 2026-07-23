# Reference Bag Ability Matrix

> Generated automatically by `pga-shootout reference-gaps`. Do not edit manually.

## Coverage

| Bag | Implemented | Total | Coverage |
|---|---:|---:|---:|
| `par3_divebomb` | 5 | 8 | 62.50% |
| `par3_high_flight` | 8 | 9 | 88.89% |

## Ability matrix

| Club | User level | Official ability and text | Normalized pattern | Status | Required data | Confidence | compare-bags impact | Bags |
|---|---:|---|---|---|---|---|---|---|
| Divebomb (`divebomb`) | null | **Chains into Putters** — Chains into putters. (On your next shot, putters have +X to all stats.) (`divebomb__chains_into_putters`) | `unqualified:chains_into_putters` | `scenario_required` | `ability_level_value`, `shot_history`, `previous_club` | medium | may change Power, Control or Spin totals and their ability contributions | `par3_divebomb` |
| Divebomb (`divebomb`) | null | **Corvid Wind Resist** — Your Corvid clubs are X% less affected by wind. (`divebomb__corvid_wind_resist`) | `unqualified:corvid_wind_resist` | `scenario_required` | `ability_level_value`, `wind_speed`, `ordered_bag` | medium | requires a wind scenario; unresolved in static comparison | `par3_divebomb` |
| Jumpstart (`jumpstart`) | null | **Power Boost** — The club to the left of Jumpstart has +X power. (`jumpstart__power_boost`) | `mechanic:dsl_pipeline` | `implemented` | `ordered_bag`, `source_club`, `ability_level_value` | high | may change Power, Control or Spin totals and their ability contributions | `par3_divebomb` |
| Steadfast (`steadfast`) | null | **Bag: Rarity Boost** — Common and Rare clubs have +X to all stats. (`steadfast__bag_rarity_boost`) | `filtered_bag_multi_stat_bonus` | `implemented` | `ordered_bag`, `club_rarity`, `source_club`, `ability_level_value`, `resolved_targets` | high | may change Power, Control or Spin totals and their ability contributions | `par3_divebomb` |
| Steadfast (`steadfast`) | null | **Brand Loyalty +X** — Has +X power per Willoughsby club next to Steadfast. (`steadfast__brand_loyalty_x`) | `mechanic:dsl_pipeline` | `implemented` | `ordered_bag`, `source_club`, `club_brand`, `ability_level_value` | medium | may change Power, Control or Spin totals and their ability contributions | `par3_divebomb` |
| Ember (`ember`) | null | **Power Shot** — Pull all the way back with Ember for extra range and tougher swing timing. (`ember__power_shot`) | `unqualified:power_shot` | `unsupported` | `ability_level_value`, `static_metric_or_physics_contract` | medium | outside the deterministic static comparator | `par3_divebomb`, `par3_high_flight` |
| Ember (`ember`) | null | **Alloy** — For each Hybrid club in your bag, that club and Ember each gain +X Power. (`ember__alloy`) | `matching_targets_and_source_per_match` | `implemented` | `ordered_bag`, `source_club`, `ability_level_value`, `resolved_targets` | high | may change Power, Control or Spin totals and their ability contributions | `par3_divebomb`, `par3_high_flight` |
| Sunstorm (`sunstorm`) | null | **Plasma Arc +X** — The farthest club from Sunstorm has +X stats. (`sunstorm__plasma_arc_x`) | `unique_farthest_multi_stat_bonus` | `implemented` | `ordered_bag`, `source_club`, `ability_level_value`, `unique_farthest_target`, `resolved_targets` | high | included in the current objective comparison | `par3_divebomb`, `par3_high_flight` |
| High Flight (`high_flight`) | null | **Loft Angle +5°** — Launches the ball with a 5° higher angle than other hybrids. (`high_flight__loft_angle_5`) | `static_modifier_targets` | `implemented` | `source_club`, `ability_level_value`, `resolved_targets`, `static_modifiers` | high | included in the current objective comparison | `par3_high_flight` |
| High Flight (`high_flight`) | null | **Wind Resist 75%** — High Flight is 75% less affected by wind. (`high_flight__wind_resist_75`) | `static_modifier_targets` | `implemented` | `source_club`, `ability_level_value`, `resolved_targets`, `static_modifiers` | high | requires a wind scenario; unresolved in static comparison | `par3_high_flight` |
| Cyclotron (`cyclotron`) | null | **Spin Boost** — The club to the left of Cyclotron has +X spin. (`cyclotron__spin_boost`) | `mechanic:dsl_pipeline` | `implemented` | `ordered_bag`, `source_club`, `ability_level_value` | high | may change Power, Control or Spin totals and their ability contributions | `par3_high_flight` |
| Cyclotron (`cyclotron`) | null | **Bounce Reduction Boost** — The club to the left of Cyclotron produces strokes with less bounce. (`cyclotron__bounce_reduction_boost`) | `static_modifier_targets` | `implemented` | `ordered_bag`, `source_club`, `ability_level_value`, `resolved_targets`, `static_modifiers` | high | may add a bounce metric and change the unresolved-bonus count | `par3_high_flight` |
| Maelstrom (`maelstrom`) | null | **Bag Bounce Reduction** — Shots from Drivers, Woods, and Hybrids bounce X% less. (`maelstrom__bag_bounce_reduction`) | `filtered_static_modifier_targets` | `implemented` | `ordered_bag`, `source_club`, `ability_level_value`, `club_type`, `resolved_targets`, `static_modifiers` | high | may add a bounce metric and change the unresolved-bonus count | `par3_high_flight` |
| Maelstrom (`maelstrom`) | null | **Bag Spin Bonus** — All clubs in your bag gain +X Spin (`maelstrom__bag_spin_bonus`) | `mechanic:dsl_pipeline` | `implemented` | `ordered_bag`, `source_club`, `ability_level_value`, `resolved_targets` | high | may change Power, Control or Spin totals and their ability contributions | `par3_high_flight` |
