# Project Status

> Generated from the same audit as `pga-shootout inventory-status`; no totals are maintained here manually.

## What the tool does today

- Loads official club statistics, user inventory and saved bags.
- Evaluates supported deterministic bag abilities in strict or partial mode.
- Compares bags metric by metric with attributed contributions and a factual completeness diagnostic.
- Supports 84/146 owned-club abilities (57.53%).

## What it does not do

- It does not rank bags or compute an aggregate user-value score.
- It does not simulate full trajectory physics, terrain history, random transformations or Meteor's abilities.
- It cannot reproduce Pierre's real club values until their current levels are recorded.

## Inventory

- Known clubs: 80; inventory complete: no.
- Fully simulated clubs: 36/80.
- Fully comparable clubs: 30/80: Homestead, Commonlaw, Kinship, Sandsend, Steadfast, Jumpstart, Cyclotron, High Flight, Cloudcatcher, Rook, Mirage, Lodestar, Into the Breach, Conqueror, Earthquake, Conspiracy, Divebomb, Into the Blue, Sunstorm, Triumph, Galvanizer, Lowball, Maelstrom, Navigator, Endeavor, People's Champion, Rampart, Saber, Steward, Gearshift.
- Comparable with warning: 23/80.
- Not currently comparable: 27/80.
- Known current levels: 79/80.

## compare-bags

Operational for explicit level scenarios. It exposes Power, Control, Spin, qualified static modifiers, ability contributions, unresolved abilities and completeness facts. Saved reference bags are regression fixtures, not product priorities.

## Optimizer

The evaluator API exists, but candidate generation, inventory enforcement, normalization, validated weights, multi-club aggregation and ranking are incomplete or missing. No automatic best-bag recommendation is currently produced.

## Meteor

Meteor remains a future, experimentally blocked subject. Alien Relic and Alien World are not implemented and are not among the next three owned-inventory lots.

## Next three development lots

1. **Resolve official text/table conflicts** — Dunecrawler, Homecoming, Hydroforce, Obelisk, Sparky, Stormbringer, Sandblast, Windstrike; +9 owned abilities; difficulty validation; requires in-game value capture, official source reconciliation.
2. **Validate dependency and stacking semantics** — Color Theory, Jetstream, Oakheart, Overgrowth, Pantheon, Ranger, Catalyst, Crystallize, Fusion, Rising Flame, Boomstick; +13 owned abilities; difficulty validation; requires minimal in-game comparison, stacking or provenance decision.
3. **Measure geometry and trajectory effects** — Neon Impulse, Skyfury, Green Demon, Outset, Eagle's Landing, Dunecrawler, Edgewalker, Ember, Huntsman, Hydroforce, Ironbark, Oakheart, Trailblazer, Flamethrower, Leviathan, Windstrike, Meanderer, Rolling Stone, Wave, The Seeker, Explorer; +25 owned abilities; difficulty experimental-high; requires validated physics contract, in-game measurements.

## Secondary global coverage

- Groups: 63/125.
- Ability occurrences: 86/162 (53.09%).
- Clubs touched by at least one supported group: 56/88.
