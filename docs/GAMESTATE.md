# Minimal GameState Contract

## Product boundary

The first product is a bag comparator. Its primary inputs are official club data, club levels, bag composition, club order, adjacency, brands, types, rarities, and static or deterministic bag abilities.

`GameState` is not a golf physics simulation. The active contract does not model a ball trajectory, hole geometry, exact coordinates, detailed elevation, or a complete course. It must not require users to describe every shot before comparing bags.

The delivery phases are:

1. bag- and club-only abilities;
2. comparison and ranking of the user's available bags;
3. optional simple scenario context for terrain, wind, shot, and history abilities;
4. advanced scenarios only when they provide demonstrated product value.

This document defines a contract only. It does not implement `READ_CONTEXT`, qualify an ability family, or add a calculation.

## Design rules

1. The structural context is the only required input.
2. The complete scenario object and every field inside it are optional and absent by default.
3. A scenario field is added only after an official ability has been semantically validated as requiring it.
4. Context uses identifiers and small categorical or scalar values, never display names as rule switches.
5. Official statistics and attributes remain in the catalogue; the bag stores references and user-owned levels rather than duplicating official data.
6. Missing is distinct from zero, false, an empty event set, or a default terrain.
7. In partial mode, a missing value required by a qualified ability is reported as unresolved and only the dependent pipeline is skipped.
8. In strict mode, that same missing required value stops evaluation. An unused missing field never causes failure.
9. `READ_CONTEXT` may only read declared paths. Filtering, aggregation, calculations, mutations, and fallback guesses remain outside it.
10. New context fields require a validated official use case and a revision of this contract.

## Active root structure

```text
GameState
|-- bag: BagState
|-- current_club_id: ClubInstanceId
`-- scenario: ScenarioContext | None = None
```

| Root field | Type | Required | Role | Consumers |
|---|---|---:|---|---|
| `bag` | `BagState` | yes | Ordered user bag used by composition, order, adjacency, and bag-wide rules. | Phase 1 bag and club families |
| `current_club_id` | `ClubInstanceId` | yes | Club instance currently being evaluated. | Target selection and self-relative rules |
| `scenario` | `ScenarioContext | None` | no | Small set of user-supplied contextual facts for qualified abilities. | Phase 3 contextual families only |

The active contract therefore has **two required structural fields** and **one optional scenario container**.

## Structural context

### BagState

`BagState.entries` is the single ordering authority. Each entry refers to official catalogue data; it does not copy official statistics, brand, type, rarity, or ability text into runtime state.

| Path | Type | Required | Description | DSL use |
|---|---|---:|---|---|
| `bag.entries` | `tuple[BagEntryState, ...]` | yes | Ordered club instances. | selection, adjacency, counting, bag-wide targeting |
| `bag.entries[].instance_id` | `ClubInstanceId` | yes | Identity of this bag occurrence, distinct from catalogue identity. | self, adjacency, position, duplicate-safe targeting |
| `bag.entries[].club_id` | `ClubId` | yes | Stable official catalogue reference. | official data resolution |
| `bag.entries[].level` | `int | "Elite" | None` | yes | User-owned level; `None` explicitly means unknown. | official level-stat and ability-value resolution |
| `bag.entries[].position` | `int` | yes | Zero-based position in the ordered bag. | adjacency and positional selection |

The official catalogue resolver supplies the club's base statistics, brand, type, rarity, and normalized abilities from `club_id`. Identity-changing effects, when eventually qualified, belong to evaluation output or an explicit effect layer rather than overwriting catalogue data.

The structural context is sufficient for Phase 1. Bag comparison must work without a scenario.

## Optional scenario context

`ScenarioContext` is a flat, sparse input object. A caller provides only values known for the comparison scenario. No default object is constructed merely to fill fields.

| Path | Type | Default | Description | Official family category justifying the path | Future read |
|---|---|---|---|---|---|
| `scenario.terrain` | `TerrainCategory | None` | `None` | Categorical lie such as tee, fairway, rough, bunker, or green. | terrain condition and terrain bonus | `READ_CONTEXT("scenario.terrain")` |
| `scenario.wind_speed` | `float | None` | `None` | Wind speed using a single documented unit. No direction or vector is implied. | wind modifier and wind resistance | `READ_CONTEXT("scenario.wind_speed")` |
| `scenario.shot_number` | `int | None` | `None` | One-based shot number on the current hole. | first-shot, tee-shot, and shot-count conditions | `READ_CONTEXT("scenario.shot_number")` |
| `scenario.shot_type` | `ShotType | None` | `None` | Small validated category such as tee, approach, recovery, or putt. | shot-type stat conditions | `READ_CONTEXT("scenario.shot_type")` |
| `scenario.previous_club_id` | `ClubInstanceId | None` | `None` | Club instance used for the immediately preceding shot. | previous-club and chain conditions | `READ_CONTEXT("scenario.previous_club_id")` |
| `scenario.previous_shot_result` | `ShotResultCategory | None` | `None` | Validated categorical outcome, for example perfect or non-perfect. | previous-shot and perfect-shot conditions | `READ_CONTEXT("scenario.previous_shot_result")` |
| `scenario.events` | `frozenset[EventId] | None` | `None` | Explicit simple events already observed, without trajectory reconstruction. | event-triggered and first-event conditions | `READ_CONTEXT("scenario.events")` |
| `scenario.flags` | `Mapping[FlagId, bool] | None` | `None` | Narrow validated booleans required by qualified abilities. | simple state conditions | `READ_CONTEXT("scenario.flags.<flag>")` |
| `scenario.course_id` | `CourseId | None` | `None` | Stable course identifier only when a named-course ability requires it. It is not a course database. | course-specific condition | `READ_CONTEXT("scenario.course_id")` |
| `scenario.special_ball_id` | `BallId | None` | `None` | Stable special-ball identifier only when an official ability requires it. | special-ball ability condition | `READ_CONTEXT("scenario.special_ball_id")` |

These ten paths are an allow-list for future qualification, not a requirement to collect ten inputs. Until a family using a path is implemented, the field may remain unused and absent.

## Missing-context behaviour

For a qualified pipeline that requires `scenario.terrain`:

- no terrain-dependent pipeline is selected: evaluation succeeds in both modes;
- the pipeline is selected and terrain is present: evaluation proceeds normally;
- the pipeline is selected and terrain is absent in partial mode: Explain records the missing path, marks that pipeline unresolved, and continues with independent pipelines;
- the pipeline is selected and terrain is absent in strict mode: evaluation fails at the unresolved read.

The engine must never infer terrain, wind, shot history, course, or special-ball state from a club name or substitute a neutral value.

## Deferred or excluded context

The following fields are outside the active contract:

| Deferred or excluded field | Reason |
|---|---|
| exact ball position and previous position | Requires coordinate capture and trajectory modelling outside the bag-comparison product. |
| pin and tee coordinates | Requires hole geometry and precise spatial data. |
| detailed elevation | Physical simulation concern; no Phase 1 requirement. |
| velocity, airtime, roll time, aim direction, swing phase, and pullback timing | Per-shot physics or input telemetry, not practical bag-comparison inputs. |
| wind direction, vectors, and pin-relative wind components | Requires geometry and directional shot state. Only simple speed is retained. |
| course geometry, hole geometry, tree distance, water distance, and boundary proximity | Would require a course database or spatial engine. |
| generic `player_state` | Too broad; only a specifically justified field such as `special_ball_id` may enter scenario context. |
| full shot history and generic event payloads | Excessive input burden; only the immediately previous club/result and simple event identifiers are retained. |
| active, temporary, scheduled, stat, and ability override collections as input context | These are engine evaluation state or outputs, not user-supplied scenario facts. |
| random seed, stream position, and algorithm | Random and transformation scenarios are deferred until they provide comparator value. |
| ball-to-pin distance and other continuous spatial measurements | Deferred with advanced scenarios; not required for the active product. |

Nothing in this table reserves an implementation. A deferred field can enter the contract only through a concrete, validated ability and a demonstrated product need.

## Compatibility with the current runtime model

The existing Python `GameState` predates this narrowed contract. No new context dataclasses were created with the earlier documentation, so no code migration is required in this correction.

| Current runtime field | Contract status |
|---|---|
| `bag` | active structural field |
| `current_club_id` | active structural field |
| `previous_club_id` | future `scenario.previous_club_id` |
| `terrain` | future `scenario.terrain` |
| `wind` | future `scenario.wind_speed` |
| `distance` | legacy placeholder; deferred from the active contract |
| `shot_history` | legacy placeholder; full history is deferred |
| `active_bonuses` | internal evaluation state used by the current engine, not user scenario context |

These legacy fields remain temporarily for backward compatibility. They do not authorize new handlers to depend on them. A code migration should occur only when `READ_CONTEXT` or the first validated Phase 3 family is implemented and tested.

## Future READ_CONTEXT boundary

A future node declares one allow-listed path and whether that path is required for its own pipeline:

```json
{
  "operation": "READ_CONTEXT",
  "parameters": {
    "path": "scenario.terrain",
    "expected_type": "TerrainCategory",
    "required": true
  }
}
```

Explain must record the requested path, expected type, supplied value, and presence status. `READ_CONTEXT` must not calculate, mutate, search geometry, invent defaults, or make an optional field globally mandatory.
