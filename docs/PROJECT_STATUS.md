# Project Status

> Inventory totals below are the last versioned audit snapshot, not a live reading of the player's mutable SQLite file. Run `pga-shootout inventory-status` for current totals. The UI description is updated separately; this UX lot does not recalculate coverage.

## What the tool does today

- Loads official club statistics, user inventory and saved bags.
- Evaluates supported deterministic bag abilities in strict or partial mode.
- Compares bags metric by metric with attributed contributions and a factual completeness diagnostic.
- Builds ordered five-club bags from an empty bag and the live inventory, independently of saved bags, with required clubs, metric constraints and allowed brands.
- Supports 84/146 owned-club abilities (57.53%).

## What it does not do

- It does not compute an aggregate user-value score.
- It does not simulate full trajectory physics, terrain history, random transformations or Meteor's abilities.
- It cannot prove real shot distance or a physically successful shot from Power alone.

## Inventory

- Known clubs: 80; inventory complete: no.
- Fully simulated clubs: 36/80.
- Fully comparable clubs: 30/80: Homestead, Commonlaw, Kinship, Sandsend, Steadfast, Jumpstart, Cyclotron, High Flight, Cloudcatcher, Rook, Mirage, Lodestar, Into the Breach, Conqueror, Earthquake, Conspiracy, Divebomb, Into the Blue, Sunstorm, Triumph, Galvanizer, Lowball, Maelstrom, Navigator, Endeavor, People's Champion, Rampart, Saber, Steward, Gearshift.
- Comparable with warning: 23/80.
- Not currently comparable: 27/80.
- Known current levels: 79/80.

## compare-bags

Operational for real inventory levels and explicit scenarios. It exposes Power, Control, Spin, qualified static modifiers, ability contributions, unresolved abilities and completeness facts without an opaque score.

## Optimizer

Operational through the Windows GUI and CLI. Build From Scratch is the primary workflow; saved-bag improvement and replacement remain secondary. Final proposals expose a reason for every slot, preserve meaningful tradeoffs and label bounded searches as MEILLEUR TROUVÉ rather than MAXIMUM PROUVÉ.

## Meteor

Meteor remains experimentally blocked. Alien Relic and Alien World are not implemented; no behavior is invented.

## Current phase

The UI/UX lot focuses on independent Build From Scratch: a short form, five-club visual cards with packaged icons and brand accents, shot-labelled final statistics, factual deltas and concise contributions. Advanced settings are collapsed; historical tools and technical detail are secondary windows. This lot does not change the Rule Engine, DSL, search algorithm, catalogue or user data.

## Secondary global coverage

- Groups: 63/125.
- Ability occurrences: 86/162 (53.09%).
- Clubs touched by at least one supported group: 56/88.
