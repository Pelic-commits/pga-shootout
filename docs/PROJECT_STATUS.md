# Project Status

> Generated from the same audit as `pga-shootout inventory-status`; no totals are maintained here manually.

## What the tool does today

- Loads official club statistics, user inventory and saved bags.
- Evaluates supported deterministic bag abilities in strict or partial mode.
- Compares bags metric by metric with attributed contributions and a factual completeness diagnostic.
- Supports 28/35 owned-club abilities (80.00%).

## What it does not do

- It does not rank bags or compute an aggregate user-value score.
- It does not simulate full trajectory physics, terrain history, random transformations or Meteor's abilities.
- It cannot reproduce Pierre's real club values until their current levels are recorded.

## Inventory

- Known clubs: 20; inventory complete: no.
- Fully simulated clubs: 14/20.
- Fully comparable by engine coverage: Homestead, Commonlaw, Kinship, Sandsend, Steadfast, Jumpstart, Cyclotron, High Flight, Cloudcatcher, Rook, Mirage, Lodestar, Into the Breach, Conqueror.
- Known current levels: 0/20.

## compare-bags

Operational for explicit level scenarios. It exposes Power, Control, Spin, qualified static modifiers, ability contributions, unresolved abilities and completeness facts. Saved reference bags are regression fixtures, not product priorities.

## Optimizer

The evaluator API exists, but candidate generation, inventory enforcement, normalization, validated weights, multi-club aggregation and ranking are incomplete or missing. No automatic best-bag recommendation is currently produced.

## Meteor

Meteor remains a future, experimentally blocked subject. Alien Relic and Alien World are not implemented and are not among the next three owned-inventory lots.

## Next three development lots

1. **Implement simple terrain conditions** — Groundskeep, Color Theory; +2 owned abilities; difficulty medium-high; requires optional terrain context, official condition validation.
2. **Qualify deterministic trajectory modifiers** — Neon Impulse, Skyfury, Green Demon; +3 owned abilities; difficulty high; requires validated physics contract, in-game measurements.
3. **Qualify tree-proximity bonuses** — Outset; +1 owned abilities; difficulty high; requires in-game distance formula validation, optional tree-proximity context.

## Secondary global coverage

- Groups: 33/125.
- Ability occurrences: 55/162 (33.95%).
- Clubs touched by at least one supported group: 37/88.
