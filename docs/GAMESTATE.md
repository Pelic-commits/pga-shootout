# GameState Contract

## Status and scope

This document defines the future context contract consumed by the DSL. It does not implement `READ_CONTEXT`, change the current `GameState` dataclass, or qualify any additional ability family.

The contract is derived from the 21 audited semantic families and 55 generic effects in `ABILITY_AUDIT.md`. A field is included only when at least one known family requires it.

## Contract principles

1. `GameState` is an immutable snapshot for one evaluation phase.
2. Every context path is versioned by this contract. A program may not read arbitrary object attributes.
3. Stable identifiers are used for clubs, abilities, courses, holes, effects, and instances. Display names never drive rules.
4. `None` means unknown or not applicable. It is never silently converted to zero, false, an empty collection, or a default terrain.
5. Physical values use typed unit-bearing scalars such as `Distance`, `Speed`, `Angle`, `Duration`, `Ratio`, and `Vector3`.
6. Collections are immutable and deterministically ordered.
7. Raw context and modified/effective context are separate fields when both are required by known mechanics.
8. Historical records are append-only. Active effects never rewrite official club data.
9. In strict mode, a required missing path is an unresolved evaluation. In partial mode, the node is marked unresolved and dependent nodes are skipped.
10. `READ_CONTEXT` only reads. Queries, filters, calculations, state changes, randomness, and effects remain separate primitives.

## Root structure

```text
GameState
├── bag: BagState
├── current_club_id: ClubInstanceId
├── terrain: TerrainState
├── wind: WindState
├── shot: ShotState
├── course: CourseState
├── ball: BallState
├── player: PlayerState
├── effects: EffectState
├── history: HistoryState
└── random: RandomState
```

The proposed root contains **11 fields** and exposes **67 explicitly named context paths** before fields inside reusable records such as `ShotRecord`, `EffectInstance`, and `Vector3`.

| Root field | Type | Description | Known semantic families | `READ_CONTEXT` namespace |
|---|---|---|---|---|
| `bag` | `BagState` | Ordered club instances and their effective catalogue attributes. | adjacency scaling, adjacency, position, bag position, composition scaling, composition condition, stat modifier, random, transform, identity | `bag.*` |
| `current_club_id` | `ClubInstanceId` | Club whose statistics or shot are currently being evaluated. Distinct from the ability source. | position, adjacency, terrain bonus, trajectory, shot control, stat modifier | `current_club_id` |
| `terrain` | `TerrainState` | Current lie, terrain penalty, bounce surface, and nearby hazards. | terrain bonus, terrain interaction, trajectory | `terrain.*` |
| `wind` | `WindState` | Raw and effective wind at the current evaluation phase. | wind, trajectory | `wind.*` |
| `shot` | `ShotState` | Current shot number, phase, input, timing, and measured durations. | shot control, stat modifier, terrain bonus, stateful growth, bag position | `shot.*` |
| `course` | `CourseState` | Course identity, hole identity, geometry references, tee, and pin. | course condition, terrain bonus, trajectory, terrain interaction, wind | `course.*` |
| `ball` | `BallState` | Current ball position, motion, elevation, and target distance. | trajectory, terrain interaction, wind, stateful growth | `ball.*` |
| `player` | `PlayerState` | Player-controlled equipment and persistent game flags required by abilities. | ability modification, course condition | `player.*` |
| `effects` | `EffectState` | Active, temporary, scheduled, flag, stat, and ability modifications. | chain, ability modification, previous shot, stateful growth, transform, terrain interaction | `effects.*` |
| `history` | `HistoryState` | Prior shots and events required by stateful and delayed mechanics. | chain, previous shot, stateful growth, ability modification, trajectory | `history.*` |
| `random` | `RandomState` | Reproducible random stream metadata. | random, transform | `random.*` |

## Shared scalar and identifier types

| Type | Contract |
|---|---|
| `ClubId` | Stable official catalogue identifier. |
| `ClubInstanceId` | Stable identifier for one club instance in the current bag; required even when the same `ClubId` occurs twice. |
| `AbilityId` | Stable normalized occurrence or semantic ability identifier. |
| `CourseId`, `HoleId`, `EffectId` | Stable identifiers, never display text. |
| `Distance` | Number plus explicit unit; canonical engine unit to be fixed before implementation. |
| `Speed` | Number plus explicit unit and reference frame. |
| `Angle` | Number plus explicit unit and convention. |
| `Duration` | Number plus explicit unit. |
| `Ratio` | Dimensionless value with declared scale, such as `0..1` or percent. |
| `Vector3` | `{x, y, z, unit, frame}`; immutable position or velocity vector. |
| `ContextValue[T]` | `T | None`; absence retains an explicit reason such as unknown, unavailable, or not applicable in Explain. |

## BagState

`BagState.entries` is the sole ordering authority. A club's array index is not its identity.

| Context path | Type | Description | Known families | Read operation |
|---|---|---|---|---|
| `bag.entries` | `tuple[BagEntryState, ...]` | Ordered club instances in the current bag. | all adjacency, position, composition, bag-wide, random, and transform families | `READ_CONTEXT("bag.entries")` |
| `bag.entries[].instance_id` | `ClubInstanceId` | Unique instance identity, including duplicate catalogue clubs. | position, adjacency, transform, random | `READ_CONTEXT("bag.entries[].instance_id")` |
| `bag.entries[].club_id` | `ClubId` | Stable official catalogue identity. | identity, ability modification, chain | `READ_CONTEXT("bag.entries[].club_id")` |
| `bag.entries[].level` | `int | "Elite"` | Evaluated club level. | every level-valued ability family | `READ_CONTEXT("bag.entries[].level")` |
| `bag.entries[].position` | `int` | Explicit zero-based position in the ordered bag snapshot. | position, bag position, adjacency, stat copy | `READ_CONTEXT("bag.entries[].position")` |
| `bag.entries[].base_brand_id` | `BrandId` | Official catalogue brand before identity effects. | adjacency scaling, composition scaling, stat modifier | `READ_CONTEXT("bag.entries[].base_brand_id")` |
| `bag.entries[].effective_brand_ids` | `frozenset[BrandId]` | Brands after validated identity effects such as “counts as all brands”. | identity, adjacency scaling, composition scaling | `READ_CONTEXT("bag.entries[].effective_brand_ids")` |
| `bag.entries[].club_type` | `ClubType` | Official type taxonomy. | composition scaling, composition condition, chain, terrain interaction | `READ_CONTEXT("bag.entries[].club_type")` |
| `bag.entries[].rarity` | `Rarity` | Official rarity taxonomy. | stat modifier | `READ_CONTEXT("bag.entries[].rarity")` |
| `bag.entries[].ability_ids` | `tuple[AbilityId, ...]` | Effective structured abilities attached to the instance. | ability modification, chain, transform | `READ_CONTEXT("bag.entries[].ability_ids")` |
| `bag.locked_positions` | `frozenset[int]` | Positions excluded from a move or shuffle by an active rule. | random, transform, bag position | `READ_CONTEXT("bag.locked_positions")` |

## TerrainState

Terrain fields describe the current ball environment. Spatial geometry remains referenced by `course.geometry_id`; `READ_CONTEXT` does not perform spatial searches.

| Context path | Type | Description | Known families | Read operation |
|---|---|---|---|---|
| `terrain.lie` | `Lie` | Tee, fairway, rough, deep rough, sand, green, water, out of bounds, or another validated lie. | terrain bonus, terrain interaction, stat modifier, trajectory | `READ_CONTEXT("terrain.lie")` |
| `terrain.penalty_kind` | `PenaltyKind | None` | Slowdown or other terrain penalty currently applicable. | terrain interaction, terrain penalty resistance | `READ_CONTEXT("terrain.penalty_kind")` |
| `terrain.penalty_strength` | `Ratio | None` | Raw terrain penalty before resistance effects. | terrain interaction, terrain penalty resistance | `READ_CONTEXT("terrain.penalty_strength")` |
| `terrain.nearby_tree_count` | `int | None` | Count produced by the validated spatial radius for the current evaluation. | terrain bonus, tree bonus | `READ_CONTEXT("terrain.nearby_tree_count")` |
| `terrain.nearest_tree_distance` | `Distance | None` | Distance to the nearest relevant tree. | terrain bonus, tree passing, trajectory | `READ_CONTEXT("terrain.nearest_tree_distance")` |
| `terrain.boundary_proximity` | `Ratio | None` | Normalized nearby out-of-bounds exposure produced by the course geometry layer. | terrain bonus, boundary bonus | `READ_CONTEXT("terrain.boundary_proximity")` |
| `terrain.nearby_water_distance` | `Distance | None` | Distance to the nearest relevant water region. | terrain bonus, terrain interaction, trajectory | `READ_CONTEXT("terrain.nearby_water_distance")` |
| `terrain.bounce_surface` | `SurfaceKind | None` | Surface used for the next or current bounce calculation. | terrain interaction, trajectory | `READ_CONTEXT("terrain.bounce_surface")` |

## WindState

| Context path | Type | Description | Known families | Read operation |
|---|---|---|---|---|
| `wind.speed` | `Speed` | Raw wind speed before club and bag modifiers. | wind | `READ_CONTEXT("wind.speed")` |
| `wind.direction` | `Angle` | Raw wind direction in the declared course frame. | wind, trajectory | `READ_CONTEXT("wind.direction")` |
| `wind.toward_pin_component` | `Speed` | Signed projection of raw wind toward the pin. | wind toward hole | `READ_CONTEXT("wind.toward_pin_component")` |
| `wind.effective_speed` | `Speed` | Wind speed after currently active resistance or directional effects. | wind resistance, trajectory | `READ_CONTEXT("wind.effective_speed")` |

## ShotState

Shot fields describe the current shot only. Completed shots move to `HistoryState` as immutable `ShotRecord` values.

| Context path | Type | Description | Known families | Read operation |
|---|---|---|---|---|
| `shot.number` | `int` | One-based shot number on the current hole. | tee bonuses, first-event growth, previous shot | `READ_CONTEXT("shot.number")` |
| `shot.type` | `ShotType` | Tee, approach, recovery, putt, or another validated shot category. | stat modifier, shot control, terrain bonus | `READ_CONTEXT("shot.type")` |
| `shot.phase` | `ShotPhase` | Pre-aim, aiming, pullback, swing, flight, roll, or complete. | shot control, trajectory, stateful growth | `READ_CONTEXT("shot.phase")` |
| `shot.aim_direction` | `Angle | None` | Current aim direction in the course frame. | shot control, wind | `READ_CONTEXT("shot.aim_direction")` |
| `shot.pullback_fraction` | `Ratio | None` | Pullback amount, with full pullback represented explicitly. | power shot | `READ_CONTEXT("shot.pullback_fraction")` |
| `shot.pullback_duration` | `Duration | None` | Time spent at or approaching full pullback. | power shot | `READ_CONTEXT("shot.pullback_duration")` |
| `shot.swing_timing` | `TimingResult | None` | Normalized timing result, distinct from perfect-shot classification. | shot control, perfect-shot triggers | `READ_CONTEXT("shot.swing_timing")` |
| `shot.was_perfect` | `bool | None` | Whether the completed swing met the game's perfect-shot rule. | stat modifier, previous shot, terrain bonus boost | `READ_CONTEXT("shot.was_perfect")` |
| `shot.airtime` | `Duration | None` | Measured flight time for the active or completed shot. | stateful growth, flight training | `READ_CONTEXT("shot.airtime")` |
| `shot.ground_roll_time` | `Duration | None` | Measured time rolling on the ground. | stateful growth, momentum | `READ_CONTEXT("shot.ground_roll_time")` |
| `shot.fade_draw` | `FadeDrawState | None` | Direction and magnitude of fade/draw input. | shot control | `READ_CONTEXT("shot.fade_draw")` |

## CourseState

| Context path | Type | Description | Known families | Read operation |
|---|---|---|---|---|
| `course.course_id` | `CourseId` | Stable course identity. | course condition | `READ_CONTEXT("course.course_id")` |
| `course.tags` | `frozenset[CourseTag]` | Validated course classifications used by named course effects. | course condition | `READ_CONTEXT("course.tags")` |
| `course.hole_id` | `HoleId` | Stable hole identity. | course condition, history | `READ_CONTEXT("course.hole_id")` |
| `course.hole_number` | `int` | Display/order number for the current hole. | history, random-at-hole-start | `READ_CONTEXT("course.hole_number")` |
| `course.par` | `int` | Par for the current hole. | player and hole evaluation | `READ_CONTEXT("course.par")` |
| `course.tee_position` | `Vector3` | Active tee position. | tee bonus, trajectory | `READ_CONTEXT("course.tee_position")` |
| `course.pin_position` | `Vector3` | Active pin/cup position. | wind direction, magnetism, trajectory | `READ_CONTEXT("course.pin_position")` |
| `course.geometry_id` | `GeometryId` | Immutable reference to validated surface, boundary, water, and tree geometry. | terrain bonus, terrain interaction, trajectory | `READ_CONTEXT("course.geometry_id")` |

## BallState

| Context path | Type | Description | Known families | Read operation |
|---|---|---|---|---|
| `ball.position` | `Vector3` | Current ball position. | terrain, trajectory, magnetism, boundary and tree bonuses | `READ_CONTEXT("ball.position")` |
| `ball.previous_position` | `Vector3 | None` | Position at the previous evaluation phase. | trajectory, terrain events | `READ_CONTEXT("ball.previous_position")` |
| `ball.elevation` | `Distance` | Current elevation in the course frame. | trajectory, gravity | `READ_CONTEXT("ball.elevation")` |
| `ball.velocity` | `Vector3 | None` | Current velocity vector. | trajectory, rush, slowdown, bounce | `READ_CONTEXT("ball.velocity")` |
| `ball.is_airborne` | `bool` | Whether the ball is currently airborne. | trajectory, flight training, ground effects | `READ_CONTEXT("ball.is_airborne")` |
| `ball.distance_to_pin` | `Distance` | Current distance to the pin. | magnetism, shot evaluation | `READ_CONTEXT("ball.distance_to_pin")` |
| `ball.special_ball_tags` | `frozenset[BallTag]` | Active special-ball classifications, including gem-ball identity. | ability modification | `READ_CONTEXT("ball.special_ball_tags")` |

## PlayerState

| Context path | Type | Description | Known families | Read operation |
|---|---|---|---|---|
| `player.special_ball_id` | `BallId | None` | Stable active special-ball identity. | ability modification, gem ball bonus | `READ_CONTEXT("player.special_ball_id")` |
| `player.game_flags` | `Mapping[FlagId, bool]` | Validated game-scoped flags not owned by a club effect. | course condition, ability modification | `READ_CONTEXT("player.game_flags.<flag>")` |

## EffectState

Every collection contains immutable `EffectInstance` records with at least `effect_id`, `source_club_instance_id`, `ability_id`, `program_id`, `start_phase`, `expiry`, `stack_count`, and typed `payload` fields.

| Context path | Type | Description | Known families | Read operation |
|---|---|---|---|---|
| `effects.active_effects` | `tuple[EffectInstance, ...]` | Effects active in the current evaluation phase. | all stateful, trajectory, wind, and terrain interactions | `READ_CONTEXT("effects.active_effects")` |
| `effects.temporary_buffs` | `tuple[EffectInstance, ...]` | Time- or shot-limited statistical buffs. | chain, previous shot, stateful growth | `READ_CONTEXT("effects.temporary_buffs")` |
| `effects.scheduled_effects` | `tuple[EffectInstance, ...]` | Effects awaiting a future trigger. | chain, previous shot, stateful growth | `READ_CONTEXT("effects.scheduled_effects")` |
| `effects.enabled_flags` | `frozenset[FlagId]` | Effective behaviour flags such as tree passing or bounce rules. | terrain interaction, trajectory, identity | `READ_CONTEXT("effects.enabled_flags")` |
| `effects.stat_overrides` | `Mapping[ClubInstanceId, Mapping[Stat, Scalar]]` | Explicit effective stat replacements or multipliers. | stat copy, shot control, transform | `READ_CONTEXT("effects.stat_overrides")` |
| `effects.ability_overrides` | `Mapping[ClubInstanceId, tuple[AbilityId, ...]]` | Effective copied, shared, or multiplied abilities. | ability modification, transform | `READ_CONTEXT("effects.ability_overrides")` |

## HistoryState

`ShotRecord` contains the stable shot number, club instance, start and end lie, perfect-shot result, airtime, ground-roll time, chain state, and typed terrain/event identifiers. The record stores observed facts, not recomputed rules.

| Context path | Type | Description | Known families | Read operation |
|---|---|---|---|---|
| `history.previous_shot` | `ShotRecord | None` | Immediately preceding completed shot; includes the previous club. | previous shot, chain, terrain bonus boost | `READ_CONTEXT("history.previous_shot")` |
| `history.shots` | `tuple[ShotRecord, ...]` | Ordered completed shots for the current hole or configured scope. | stateful growth, previous shot, chain, trajectory | `READ_CONTEXT("history.shots")` |
| `history.events` | `tuple[GameEvent, ...]` | Ordered typed events such as first tree or hazard contact. | stateful growth, ability modification, terrain interaction | `READ_CONTEXT("history.events")` |
| `history.clubs_used` | `tuple[ClubInstanceId, ...]` | Ordered club instances used in completed shots. | ability mirror, chain, previous shot | `READ_CONTEXT("history.clubs_used")` |
| `history.chain_count` | `int` | Number of validated chain bonuses consumed in the configured scope. | chain, magnetism | `READ_CONTEXT("history.chain_count")` |
| `history.perfect_shot_count` | `int` | Number of validated perfect shots in the configured scope. | stat modifier, previous shot | `READ_CONTEXT("history.perfect_shot_count")` |

## RandomState

Randomness is context, not a global side effect. A random primitive must consume and return stream state explicitly.

| Context path | Type | Description | Known families | Read operation |
|---|---|---|---|---|
| `random.seed` | `int | str` | Replayable seed for the game or simulation. | random, transform | `READ_CONTEXT("random.seed")` |
| `random.stream_position` | `int` | Current deterministic position in the random stream. | random, transform | `READ_CONTEXT("random.stream_position")` |
| `random.algorithm` | `RngAlgorithmId` | Versioned random algorithm identifier. | random, transform | `READ_CONTEXT("random.algorithm")` |

## Derived values and prohibited shortcuts

The following are derived, not independent state fields:

- `is_first_shot` derives from `shot.number`;
- previous club derives from `history.previous_shot.club_instance_id`;
- adjacency derives from `bag.entries[].position`;
- elevation difference derives from `ball.position` and `course.pin_position`;
- wind toward the pin may be supplied as `wind.toward_pin_component`, but its source values remain available;
- same-brand, type, rarity, and identity matches belong to filter primitives;
- tree, water, and boundary queries belong to the geometry layer; `GameState` stores only validated query outputs needed by the current snapshot;
- final statistics are outputs of evaluation and are not copied back into base catalogue data.

No family name, club name, course display name, or undocumented string path may be used as a rule switch.

## Compatibility with the current model

The existing fields map without changing current behaviour:

| Current field | Future path |
|---|---|
| `bag` | `bag.entries` |
| `current_club_id` | `current_club_id` |
| `previous_club_id` | `history.previous_shot.club_instance_id` |
| `terrain` | `terrain.lie` |
| `wind` | `wind.speed` plus `wind.direction` when known |
| `distance` | `ball.distance_to_pin` |
| `shot_history` | `history.shots` and `history.events` |
| `active_bonuses` | `effects.active_effects` or `effects.temporary_buffs` according to duration |

This is a migration map only. It does not authorize changing the current dataclass before `READ_CONTEXT`, serialization, and backward-compatibility behaviour are specified and tested.

## READ_CONTEXT contract boundary

A future `READ_CONTEXT` node must declare:

```json
{
  "operation": "READ_CONTEXT",
  "parameters": {
    "path": "terrain.penalty_strength",
    "expected_type": "Ratio",
    "required": true
  }
}
```

Its Explain entry must include the requested path, expected type, resolved value and unit, presence status, and snapshot phase. It must never perform filtering, aggregation, geometry lookup, fallback calculation, mutation, or random selection.
