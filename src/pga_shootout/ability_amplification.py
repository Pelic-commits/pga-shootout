"""One-pass native ability transformations, independent of clubs and families.

Only additive stat magnitudes are qualified. Numeric-looking modifiers are not
automatically linear in the game: their extra instance stays unresolved.
"""
from dataclasses import asdict, replace
from typing import Mapping

from .models import Effect, ExplainEntry
from .registry import MechanismExecutionError


MAGNITUDE_INPUTS = {"ADD_STAT": "delta", "SCHEDULE_EFFECT": "amount"}
STRUCTURAL_OPERATIONS = frozenset({
    "SELECT_SELF", "READ_LEVEL_VALUE", "SELECT_ALL", "SELECT_ADJACENT", "SELECT_FARTHEST",
    "MATCH_BRAND", "MATCH_TYPE", "MATCH_RARITY", "COUNT", "EXISTS", "SCALE", "FOR_EACH", "UNLESS",
})


def is_transformation(effect):
    return effect.parameters.get("phase") == "ability_transform"


def _nodes(program):
    for node in program.get("nodes", ()):
        yield node
        nested = node.get("parameters", {}).get("program")
        if isinstance(nested, Mapping):
            yield from _nodes(nested)


def amplification_policy(effect):
    """Explicit safety classification by mechanism shape, never by ability name."""
    if is_transformation(effect):
        return "transformation recursion is not qualified"
    if effect.mechanism in {"add_stat", "add_all_stats"}:
        return None
    if effect.mechanism != "dsl_pipeline":
        return "target effect is not implemented"
    nodes = tuple(_nodes(effect.parameters.get("program", {})))
    operations = {node.get("operation") for node in nodes}
    if not operations & MAGNITUDE_INPUTS.keys():
        return "extra instance of this modifier or non-numeric effect is not qualified"
    if operations - STRUCTURAL_OPERATIONS - MAGNITUDE_INPUTS.keys():
        return "extra instance of this modifier or mixed effect is not qualified"
    for node in nodes:
        if node.get("operation") == "SCHEDULE_EFFECT" and node.get("parameters", {}).get("effect_mechanism", "add_all_stats") not in {"add_stat", "add_all_stats"}:
            return "delayed effect magnitude is not qualified"
    return None


def _trace(source, stats, outputs, *, message, applied):
    return ExplainEntry(source, "ABILITY_AMPLIFICATION", "native ability transformation", applied,
                        dict(stats), {}, dict(stats), message, {}, outputs)


def prepare_abilities(effects, state, stats, mechanisms, conditions):
    """Resolve selectors first, transform an immutable native snapshot once.

    Multiple amplifiers of one owner are deliberately unresolved (not x3/x4).
    No transformed ability can produce further transformation requests.
    """
    requests, journal, unresolved = [], [], []
    transformations = [effect for effect in effects if is_transformation(effect)]
    ordinary = [effect for effect in effects if not is_transformation(effect)]
    if not transformations:
        return ordinary, journal, unresolved
    for effect in transformations:
        try:
            applies = conditions.evaluate(effect.condition, state, stats)
            if not applies:
                journal.append(_trace(effect.source, stats, {}, message="transformation condition not satisfied", applied=False))
                continue
            execution = mechanisms.execute(effect, stats, state)
            if execution.stats != stats or execution.scheduled_effects:
                raise MechanismExecutionError("Transformation phase may not change stats or schedule shots")
            journal.extend(execution.explain)
            requests.extend(execution.amplifications)
        except (LookupError, MechanismExecutionError) as error:
            message = f"Unresolved amplification: {error}"
            unresolved.append(message)
            journal.append(_trace(effect.source, stats, {}, message=message, applied=False))
    owners = {effect.source: (entry.club.identifier, ability.identifier)
              for entry in state.bag.entries for ability in entry.club.abilities for effect in ability.effects}
    native_ids = {id(effect) for entry in state.bag.entries for ability in entry.club.abilities for effect in ability.effects}
    requests = tuple(dict.fromkeys(requests))
    by_target = {}
    for request in requests:
        by_target.setdefault(request.target_club_id, []).append(request)
    transformed = []
    for effect in effects:
        owner, ability_id = owners.get(effect.source, (effect.parameters.get("source_club_id"), effect.parameters.get("ability_id", effect.source)))
        relevant = by_target.get(owner, ())
        reason = amplification_policy(effect) if relevant else None
        if relevant and id(effect) not in native_ids:
            reason = "temporary or non-native effect amplification is not qualified"
        if len(relevant) > 1:
            reason = "multiple amplifiers of the same club: stacking is not qualified"
        if any(request.source_club_id == owner for request in relevant):
            reason = "self amplification is not qualified"
        for request in relevant:
            facts = {**asdict(request), "target_ability_id": ability_id,
                     "target_ability_source": effect.source, "status": "unresolved" if reason else "planned"}
            message = f"Unresolved amplification: {ability_id}: {reason}" if reason else "native additive ability magnitude will be amplified"
            journal.append(_trace(request.source, stats, facts, message=message, applied=not reason))
            if reason:
                unresolved.append(message)
        if is_transformation(effect):
            continue
        if relevant and not reason:
            request = relevant[0]
            parameters = {**effect.parameters, "_amplification": {**asdict(request), "target_ability_id": ability_id}}
            if effect.mechanism in {"add_stat", "add_all_stats"}:
                parameters["amount"] = float(parameters["amount"]) * request.multiplier
                parameters["_original_amount"] = effect.parameters["amount"]
            effect = replace(effect, parameters=parameters)
        transformed.append(effect)
    return transformed, journal, list(dict.fromkeys(unresolved))


def amplify_inputs(operation, inputs, effect):
    amplification = effect.parameters.get("_amplification")
    field = MAGNITUDE_INPUTS.get(operation)
    if not amplification or field is None:
        return inputs
    result = {**inputs, field: float(inputs[field]) * amplification["multiplier"]}
    if operation == "SCHEDULE_EFFECT":
        result.update({"_amplification": amplification, "_original_amount": inputs[field]})
    return result


def amplification_trace(effect, operation, original, amplified, parameters, stats):
    amplification = effect.parameters.get("_amplification")
    field = MAGNITUDE_INPUTS.get(operation)
    if not amplification or field is None:
        return ()
    facts = {**amplification, "target_ability_source": effect.source,
             "status": "scheduled" if operation == "SCHEDULE_EFFECT" else "resolved",
             "original": original[field], "amplified": amplified[field],
             "metric": parameters.get("stat", "all_stats"),
             "final_target": amplified.get("target"), "operation": operation}
    return (_trace(amplification["source"], stats, facts,
                   message="amplified magnitude applied by its original ability; not an extra stat contribution", applied=True),)
