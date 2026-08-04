# Project Status

> Generated from the same audit as `pga-shootout inventory-status`; no totals are maintained here manually.

## What the tool does today

- Loads official club statistics, user inventory and saved bags.
- Evaluates supported deterministic bag abilities in strict or partial mode.
- Compares bags metric by metric with attributed contributions and a factual completeness diagnostic.
- Supports 56/138 owned-club abilities (40.58%).

## What it does not do

- It does not rank bags or compute an aggregate user-value score.
- It does not simulate full trajectory physics, terrain history, random transformations or Meteor's abilities.
- It cannot reproduce Pierre's real club values until their current levels are recorded.

## Inventory

- Known clubs: 75; inventory complete: no.
- Fully simulated clubs: 25/75.
- Fully comparable clubs: 24/75: Homestead, Commonlaw, Kinship, Sandsend, Steadfast, Jumpstart, Cyclotron, High Flight, Cloudcatcher, Rook, Mirage, Lodestar, Into the Breach, Conqueror, Earthquake, Sunstorm, Galvanizer, Lowball, Maelstrom, Endeavor, People's Champion, Rampart, Saber, Steward.
- Comparable with warning: 14/75.
- Not currently comparable: 37/75.
- Known current levels: 72/75.

## compare-bags

Operational for explicit level scenarios. It exposes Power, Control, Spin, qualified static modifiers, ability contributions, unresolved abilities and completeness facts. Saved reference bags are regression fixtures, not product priorities.

## Optimizer

The evaluator API exists, but candidate generation, inventory enforcement, normalization, validated weights, multi-club aggregation and ranking are incomplete or missing. No automatic best-bag recommendation is currently produced.

## Meteor

Meteor remains a future, experimentally blocked subject. Alien Relic and Alien World are not implemented and are not among the next three owned-inventory lots.

## Next three development lots

1. **Expose wind resistance as an objective modifier** — Into the Blue, Jetstream, Obelisk, Stormbringer, XLR8R; +7 owned abilities; difficulty medium; requires scope validation, stacking validation.
2. **Implement next-shot chains** — Conspiracy, Sparky, Navigator; +4 owned abilities; difficulty medium-high; requires history trigger validation, duration and consumption validation.
3. **Implement simple terrain conditions** — Groundskeep, Color Theory, Dunecrawler, Hydroforce, Obelisk, Overgrowth, Ranger, Rebound, Trailblazer, Leviathan, Bushwhacker, Hero, New Frontier; +13 owned abilities; difficulty medium-high; requires optional terrain context, official condition validation.

## Secondary global coverage

- Groups: 35/125.
- Ability occurrences: 57/162 (35.19%).
- Clubs touched by at least one supported group: 39/88.
