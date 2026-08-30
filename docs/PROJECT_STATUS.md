# Project Status

> Inventory totals below are the last versioned audit snapshot, not a live reading of the player's mutable SQLite file. Run `pga-shootout inventory-status` for current totals. The targeted Landing/Wind lot adds no ability handler and makes no coverage claim.

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

Meteor is owned at level 9 in the audited SQLite profile and is already eligible in Build From Scratch. Base stats and qualified incoming synergies are calculated. Alien Relic Left remains unresolved; Right and Alien World are inactive at that level. No copy or physics behavior is invented.

Flashpoint is already present and owned at level 7. It is generically eligible as a non-putter active club or unresolved potential support. Rocket Boosters and Boundary Rush remain unresolved. No inventory/catalogue edits were needed. See the exact texts and level tables in [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md).

## Current phase

The targeted lot preserves the visual Build From Scratch workflow and adds separate Landing/Wind result axes to the existing result projection. Driver/Wood/Hybrid green attacks use the existing landing-relevance policy during support qualification as well as presentation. Wind needs explicit context. Axes are reserved before secondary Power tiers; identical winners share a card and multiple badges. Cards expose relevant secondary metrics, support contributions, unknown deltas and additive-stacking cautions. The Rule Engine, DSL, catalogue, user data and inventory launcher remain unchanged.

Bounded real-inventory benchmark (400 evaluation budget, five requested results, fresh service per run; seconds, before → after): Par 3 Blacksmith 19.708 → 17.103; Par 3 High Flight 27.158 → 27.509; Par 4 long High Flight with wind 13.564 → 17.010; Meteor 17.386 → 18.637; Flashpoint 16.691 → 18.987. These are single observations, not statistical performance guarantees. The wind case now retains two results instead of one. Scripts `validate_context_variants.py` and `validate_context_variants_gui.py` reproduce the audit and Windows acceptance checks without modifying the user's inventory.

Validation for this lot: 574 tests and 168 subtests passed (473.40 s); 38 targeted
tests passed again after the final card readability adjustments. Actual Windows/Tk
runs covered High Flight with/without wind, Meteor and Flashpoint, five-club cards,
partial warnings, relevant contributions, technical details, 1280×800 layout, and
close/relaunch. No callback errors; the original SQLite SHA-256 remained unchanged.
The UI stays asynchronous. No new primitives, ability handlers or physical rules.

## Secondary global coverage

- Groups: 63/125.
- Ability occurrences: 86/162 (53.09%).
- Clubs touched by at least one supported group: 56/88.
