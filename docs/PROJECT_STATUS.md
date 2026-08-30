# Project Status

> Inventory totals below are versioned audit snapshots, not a live reading of the player's mutable SQLite file. Run `pga-shootout inventory-status` for current totals. The amplification lot qualifies an additive subset of Alien Relic, not every possible interaction.

## What the tool does today

- Loads official club statistics, user inventory and saved bags.
- Evaluates supported deterministic bag abilities in strict or partial mode.
- Compares bags metric by metric with attributed contributions and a factual completeness diagnostic.
- Builds ordered five-club bags from an empty bag and the live inventory, independently of saved bags, with required clubs, metric constraints and allowed brands.
- Fully qualifies 86/162 catalogue ability occurrences (53.09%); partial coverage is reported separately below.

## What it does not do

- It does not compute an aggregate user-value score.
- It does not simulate full trajectory physics, terrain history, random transformations or Alien World.
- It cannot prove real shot distance or a physically successful shot from Power alone.

## Inventory — historical snapshot before this lot

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

Meteor is owned at level 9 in the audited SQLite profile. Alien Relic Left now amplifies qualified native additive ability magnitudes of its left neighbor before their normal resolution. The neighbor keeps its own level, conditions and final targets. Right unlocks at level 10 and uses the same DSL pattern; Elite alone enables wrapping. Alien World is inactive at level 9 and remains unresolved at its unlocked levels. Non-additive modifiers, temporary abilities, recursive amplification and multiple amplifiers of one owner remain explicitly unresolved, with native supported effects preserved in partial mode.

Flashpoint is already present and owned at level 7. It is generically eligible as a non-putter active club or unresolved potential support. Rocket Boosters and Boundary Rush remain unresolved. No inventory/catalogue edits were needed. See the exact texts and level tables in [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md).

## Current phase: generic ability amplification

The new `ABILITY_EFFECT_MULTIPLIER` primitive requests a one-pass native ability transformation. It does not multiply final club statistics. Existing additive effects and additive Chains payloads reuse their existing resolution mechanisms; the transformed payload is not doubled a second time on its later trigger. No club-name rule, GameState expansion, new physical rule, Stormbringer/XLR8R interaction or inventory edit was introduced.

Build From Scratch recognizes amplifiers as structural support candidates and evaluates their actual contribution through the existing counterfactual analysis. Cards identify the amplified neighbor, original ability, magnitude change and final target; the full provenance remains in technical details. Example at real levels: Blacksmith / Meteor / Commonlaw / Sunstorm / Gearshift, Blacksmith **23 Power / 11 Control / 7 Spin**, with Texas Tee **5 → 10 Power**. A High Flight Landing proposal without Meteor remains retained: Gearshift / Maelstrom / High Flight / Cyclotron / Homestead.

Bounded real-inventory benchmark (400 evaluations, five results, fresh service per run; before → after):

| Primary club | Seconds | Proposals containing Meteor | Power-max proposal: attack Power/Control/Spin |
|---|---:|---:|---|
| Blacksmith | 16.077 → 16.542 | 0/5 → 3/5 | 21/11/7 → 23/11/7 |
| High Flight | 23.887 → 26.498 | 0/5 → 4/5 | 27/14/11 → 28/15/12 |
| Divebomb | 26.680 → 28.438 | 0/5 → 5/5 | 19/11/10 → 20/12/11 |
| Meteor (explicit primary) | 15.825 → 19.055 | 5/5 → 5/5 | 8/6/7 → 8/6/7 |

These are single observations, not statistical performance guarantees or exhaustive maxima. The additional transformation and provenance work has a measurable cost. `scripts/validate_ability_amplification.py` reproduces the current benchmark; the before/after measurements for this run are in ignored local `logs/amplification/` reports.

Actual Windows/Tk validation used the live Build From Scratch controls for Blacksmith and High Flight, checked five-club cards, amplified support provenance, a retained proposal without Meteor, technical details, 1280×800 layout and close/relaunch. No callback errors; the original SQLite SHA-256 remained `0bc680873668a451712e3f4d79e1bbd57b5fd310a4548ac5678cb3f81bf2fcfb`. Reproduce with `scripts/validate_context_variants_gui.py --amplification` (desktop capture runtime required).

Final validation: **602 tests and 168 subtests passed in 453.67 s**, including 28 new synthetic/official-data amplification cases. The targeted amplification/registry/audit/coverage selection passed 57 tests and 4 subtests. On Windows the full run used `PYTHONUTF8=1` inherited by subprocesses: setting `-X utf8` only on the parent had caused one launcher-test output decoding failure, not a calculation failure. All five launcher tests passed independently with the inherited setting. No launcher change was needed.

Coverage is intentionally conservative: catalogue full occurrences stay **86/162 (53.09%)**, partial occurrences **2 → 4**, wholly unresolved occurrences **74 → 72**. The current audit's inventory-entry snapshot has **84/151** full, **2 → 4** partial and **65 → 63** unresolved occurrences, with **36** fully simulated clubs unchanged. This report currently includes all 82 known inventory entries under its historical “owned” label; the live UI has 81 marked owned. These are catalogue qualification counts, not a promise that every scenario or future level is fully comparable. The older inventory summary above remains its separately dated snapshot.

## Previous phase: Landing/Wind result axes

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
