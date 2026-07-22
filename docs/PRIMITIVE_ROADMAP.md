# Primitive Roadmap

## Scope

This roadmap is derived from the 125 normalized ability groups, the 162 audited occurrences, and the actual DSL registry. It does not qualify or implement any additional gameplay family.

The impact ranking is a baseline from the 21-occurrence Brand Loyalty milestone. Current implementation and coverage status are authoritative in `MECHANIC_COVERAGE.md`; primitives implemented after this baseline, including `MATCH_TYPE` and `FOR_EACH`, must be excluded when using the table for a new architectural decision.

Already available and therefore excluded from the ranking:

- `SELECT_SELF`
- `READ_LEVEL_VALUE`
- `SELECT_ADJACENT`
- `MATCH_BRAND`
- `COUNT`
- `SCALE`
- `ADD_STAT`

The engine currently covers 21 occurrences. The counts below exclude those occurrences and concern the remaining 141.

An occurrence may depend on several primitives and therefore appear in several rows. “Potential coverage” means the share of the complete 162-occurrence catalogue that could use the primitive in a future composition. It does not mean that the primitive alone completes every listed family.

## Impact model

The ranking uses this reproducible score:

```text
impact = occurrences + (2 × semantic families) + (3 × future composition patterns) - (2 × difficulty weight)
```

Difficulty weights:

| Difficulty | Weight |
|---|---:|
| Low | 1 |
| Low–medium | 2 |
| Medium | 3 |
| High | 6 |

Occurrence and club counts are unique unions from the normalized groups attached to each audited semantic family. Composition-pattern counts estimate reuse across selection, filtering, conditional, stateful, trajectory, and transformation pipelines.

## Ranked missing primitives

| Rank | Primitive | Role | Dependent semantic families | Occurrences | Clubs | Potential coverage | Difficulty | Impact |
|---:|---|---|---|---:|---:|---:|---|---:|
| 1 | `READ_CONTEXT` | Read a typed value from shot, course, terrain, wind, history, or timing context. | terrain bonus, trajectory, terrain interaction, wind, shot control, stateful growth, bag position, course condition, previous shot | 82 | 55 | 50.62% | Medium | 118 |
| 2 | `MATCH_ATTRIBUTE` | Compare a typed context or object attribute with an expected value. | terrain bonus, trajectory, terrain interaction, wind, shot control, course condition, previous shot | 74 | 51 | 45.68% | Low | 110 |
| 3 | `FOR_EACH` | Execute a sub-pipeline once per selected target while preserving order and Explain. | terrain bonus, stat modifier, adjacency, composition scaling, composition condition, ability modification, chain | 57 | 46 | 35.19% | Medium | 86 |
| 4 | `SELECT_ALL` | Select the complete ordered bag, optionally excluding the source. | terrain bonus, stat modifier, composition scaling, composition condition, ability modification, random, transform, identity | 52 | 43 | 32.10% | Low–medium | 85 |
| 5 | `MULTIPLY` | Multiply typed scalar values without applying an effect. | trajectory, wind, stat copy, ability modification, shot control | 47 | 38 | 29.01% | Low | 73 |
| 6 | `ENABLE_FLAG` | Enable a typed state or behaviour flag with explicit duration. | trajectory, terrain interaction, wind, identity, ability modification | 51 | 40 | 31.48% | Medium | 70 |
| 7 | `CLAMP` | Apply an explicit minimum or maximum to a scalar. | terrain bonus, trajectory, wind | 51 | 41 | 31.48% | Low | 70 |
| 8 | `WHEN` | Execute a branch only when a Boolean input is true. | terrain bonus, composition condition, course condition, previous shot, stateful growth, shot control, bag position | 40 | 33 | 24.69% | Medium | 69 |
| 9 | `ADD_ALL_STATS` | Apply the same delta to an explicit list of target statistics. | terrain bonus, chain, adjacency, random, position | 43 | 35 | 26.54% | Low | 66 |
| 10 | `EMIT_EVENT` | Emit a typed non-statistical gameplay event into the result and Explain. | trajectory, terrain interaction, wind, shot control | 50 | 39 | 30.86% | High | 64 |
| 11 | `READ_ATTRIBUTE` | Read a typed attribute from a club, ability, event, or target reference. | adjacency scaling, stat modifier, composition scaling, composition condition, stat copy, identity, adjacency | 32 | 25 | 19.75% | Low | 62 |
| 12 | `EXISTS` | Return whether a selected collection contains at least one element. | terrain bonus, composition condition, position, bag position, course condition | 34 | 29 | 20.99% | Low | 57 |
| 13 | `SELECT_CURRENT` | Select the club currently being evaluated or played. | position, adjacency scaling, adjacency, terrain bonus | 35 | 29 | 21.60% | Low | 56 |
| 14 | `MATCH_TYPE` | Filter clubs using the official club-type taxonomy. | adjacency scaling, composition scaling, composition condition, chain, terrain interaction | 30 | 25 | 18.52% | Low | 53 |
| 15 | `ROUND` | Apply a named rounding policy at an explicit phase. | trajectory, wind | 31 | 25 | 19.14% | Low | 45 |
| 16 | `SUBTRACT` | Subtract one compatible scalar from another. | stat modifier, previous shot, bag position, shot control | 25 | 21 | 15.43% | Low | 43 |
| 17 | `SELECT_HISTORY` | Select typed prior shots, events, or clubs through a bounded window. | chain, previous shot, stateful growth, ability modification | 21 | 18 | 12.96% | Medium | 38 |
| 18 | `MULTIPLY_STAT` | Multiply a resolved statistic by a factor at an explicit phase. | stat copy, shot control, stat modifier | 24 | 21 | 14.81% | Low–medium | 38 |
| 19 | `SELECT_BY_POSITION` | Select clubs by stable bag positions or ranges. | position, bag position, adjacency, stat copy | 18 | 14 | 11.11% | Low | 36 |
| 20 | `ADD` | Add compatible scalar values without applying an effect. | stat modifier, previous shot, bag position | 19 | 17 | 11.73% | Low | 35 |
| 21 | `SUM` | Sum a typed collection of scalar values. | stat copy, composition scaling, adjacency scaling, random | 15 | 12 | 9.26% | Low | 33 |
| 22 | `ANY` | Return whether any Boolean result in a collection is true. | composition condition, terrain bonus | 22 | 19 | 13.58% | Low | 33 |
| 23 | `SELECT_BEFORE` | Select clubs before a resolved origin while preserving order. | position, bag position, stat copy | 14 | 12 | 8.64% | Low | 27 |
| 24 | `SELECT_AFTER` | Select clubs after a resolved origin while preserving order. | position, bag position, stat copy | 14 | 12 | 8.64% | Low | 27 |
| 25 | `SCHEDULE_EFFECT` | Schedule a typed sub-pipeline for a future trigger or shot. | chain, previous shot, stateful growth | 15 | 13 | 9.26% | High | 24 |
| 26 | `MATCH_RARITY` | Filter clubs using the official rarity taxonomy. | stat modifier | 14 | 13 | 8.64% | Low | 23 |
| 27 | `MATCH_IDENTITY` | Match calculated identity, including validated multi-brand identity. | adjacency scaling, identity, composition scaling | 8 | 5 | 4.94% | Medium | 20 |
| 28 | `SET_STAT` | Replace a resolved statistic with an explicit value. | stat copy, transform | 6 | 5 | 3.70% | Low–medium | 15 |
| 29 | `ALL` | Return whether every Boolean result in a collection is true. | composition condition | 2 | 1 | 1.23% | Low | 8 |
| 30 | `RANDOM_CHOICE` | Choose reproducibly from a collection using an injected RNG. | random, transform | 6 | 5 | 3.70% | High | 7 |
| 31 | `UNLESS` | Execute a branch only when a Boolean input is false. | composition condition | 2 | 1 | 1.23% | Low–medium | 6 |
| 32 | `COPY_ABILITY` | Copy a structured ability with duration and stacking rules. | ability modification | 6 | 5 | 3.70% | High | 5 |
| 33 | `SHUFFLE_CLUBS` | Shuffle a selected set using an injected RNG. | random | 4 | 4 | 2.47% | High | 0 |
| 34 | `REMOVE_CLUB` | Remove a club instance with explicit restoration policy. | random | 4 | 4 | 2.47% | High | 0 |
| 35 | `REPLACE_CLUB` | Replace a club instance while applying an explicit state-retention policy. | transform | 2 | 1 | 1.23% | High | -2 |

## Dependencies and delivery constraints

### Context and conditions

| Primitive | Required foundation |
|---|---|
| `READ_CONTEXT` | Versioned `GameState` context schema; typed paths; required/optional policy; stable units. |
| `MATCH_ATTRIBUTE` | `READ_CONTEXT` or `READ_ATTRIBUTE`; typed operator registry; missing-value policy. |
| `WHEN`, `UNLESS` | Boolean outputs; branch executor; skipped-node Explain semantics. |
| `EXISTS`, `ANY`, `ALL` | Typed collections; empty-collection policy; deterministic Explain. |

### Selection and iteration

| Primitive | Required foundation |
|---|---|
| `SELECT_ALL` | Ordered `Bag`; source inclusion policy. |
| `SELECT_CURRENT` | Explicit distinction between ability source and evaluated club. |
| `SELECT_BY_POSITION`, `SELECT_BEFORE`, `SELECT_AFTER` | Stable instance positions, including duplicate club identifiers. |
| `FOR_EACH` | Nested execution; deterministic ordering; atomicity policy; per-target Explain. |
| `SELECT_HISTORY` | Structured shot/event history with bounded queries. |

### Typed filters and values

| Primitive | Required foundation |
|---|---|
| `READ_ATTRIBUTE` | Reference resolver and versioned object schemas. |
| `MATCH_TYPE` | Official club-type taxonomy. |
| `MATCH_RARITY` | Official rarity taxonomy. |
| `MATCH_IDENTITY` | Validated identity registry, especially “counts as all brands”. |
| `ADD`, `SUBTRACT`, `MULTIPLY`, `SUM` | Unit compatibility and numeric error policy. |
| `CLAMP`, `ROUND` | Validated bounds, rounding modes, precision, and application phase. |

### Effects and state

| Primitive | Required foundation |
|---|---|
| `ADD_ALL_STATS`, `SET_STAT`, `MULTIPLY_STAT` | Resolved targets; explicit stat list; effect ordering phase. |
| `ENABLE_FLAG` | Versioned flag schema; duration and stacking policy. |
| `EMIT_EVENT` | Event schema; `EvaluationResult` event channel; Explain serialization. |
| `SCHEDULE_EFFECT` | Trigger dispatcher; persistence and consumption rules; structured history. |

### Randomness and transformations

| Primitive | Required foundation |
|---|---|
| `RANDOM_CHOICE`, `SHUFFLE_CLUBS` | Injected RNG, explicit seed, distribution, and replay tests. |
| `REMOVE_CLUB`, `REPLACE_CLUB` | Stable club-instance identity, restoration rules, and bag constraints. |
| `COPY_ABILITY` | Structured ability identity, stacking, duration, and recursion protection. |

## Priority recommendation

`READ_CONTEXT` is the highest-impact missing primitive.

It is referenced by nine semantic families and 82 remaining occurrences across 55 clubs:

- terrain bonus;
- trajectory;
- terrain interaction;
- wind;
- shot control;
- stateful growth;
- bag position;
- course condition;
- previous shot.

Its potential reach is 50.62% of the complete catalogue, or 58.16% of the 141 currently uncovered occurrences. It also supplies the typed inputs needed by `MATCH_ATTRIBUTE`, `WHEN`, `CLAMP`, `EMIT_EVENT`, and `SCHEDULE_EFFECT` pipelines.

Estimated difficulty: **medium**. The primitive itself is read-only, but it must first freeze a versioned context schema and unit policy. It should not be implemented until those contracts and their strict/partial Explain behaviour are specified.

## Explicitly deferred DSL inventory

The frozen DSL also names `LITERAL`, `REFERENCE_OUTPUT`, and `SEQUENCE`. Their behaviour is already implicit in literal node parameters, output references, and ordered node execution, so they are not counted as missing gameplay primitives. `MIN`, `MAX`, `DIVIDE`, `DISABLE_FLAG`, and `MOVE_CLUB` have no demonstrated dependency in the current audited families and are therefore excluded until a concrete family proves the need.
