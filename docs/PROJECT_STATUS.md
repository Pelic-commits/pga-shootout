# Project Status

> Generated from the same audit as `pga-shootout inventory-status`; no totals are maintained here manually.

## What the tool does today

- Loads official club statistics, user inventory and saved bags.
- Evaluates supported deterministic bag abilities in strict or partial mode.
- Compares bags metric by metric with attributed contributions and a factual completeness diagnostic.
- Supports 23/35 owned-club abilities (65.71%).

## What it does not do

- It does not rank bags or compute an aggregate user-value score.
- It does not simulate full trajectory physics, terrain history, random transformations or Meteor's abilities.
- It cannot reproduce Pierre's real club values until their current levels are recorded.

## Inventory

- Known clubs: 20; inventory complete: no.
- Fully simulated clubs: 10/20.
- Fully comparable by engine coverage: Homestead, Commonlaw, Sandsend, Steadfast, Jumpstart, Cyclotron, Cloudcatcher, Mirage, Lodestar, Into the Breach.
- Known current levels: 0/20.

## compare-bags

Operational for explicit level scenarios. It exposes Power, Control, Spin, qualified static modifiers, ability contributions, unresolved abilities and completeness facts. Saved reference bags are regression fixtures, not product priorities.

## Optimizer

The evaluator API exists, but candidate generation, inventory enforcement, normalization, validated weights, multi-club aggregation and ranking are incomplete or missing. No automatic best-bag recommendation is currently produced.

## Meteor

Meteor remains a future, experimentally blocked subject. Alien Relic and Alien World are not implemented and are not among the next three owned-inventory lots.

## Next three development lots

1. **Expose wind resistance as an objective modifier** — High Flight, Rook; +2 owned abilities; difficulty medium; requires scope validation, stacking validation.
2. **Implement next-shot chains** — Kinship, Outset, Conqueror; +3 owned abilities; difficulty medium-high; requires history trigger validation, duration and consumption validation.
3. **Implement simple terrain conditions** — Groundskeep, Color Theory; +2 owned abilities; difficulty medium-high; requires optional terrain context, official condition validation.

## Secondary global coverage

- Groups: 28/125.
- Ability occurrences: 48/162 (29.63%).
- Clubs touched by at least one supported group: 34/88.
