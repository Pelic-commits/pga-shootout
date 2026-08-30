"""Minimal rule engine orchestrating conditions, mechanisms and Explain."""

from __future__ import annotations

from .conditions import ConditionRegistry, UnknownConditionError, default_condition_registry
from .explain import explain_entry
from .models import Effect, EvaluationMode, EvaluationResult, ExplainEntry, GameState, Stats
from .registry import MechanismExecutionError, MechanismRegistry, UnknownMechanismError, default_mechanism_registry
from .ability_amplification import prepare_abilities, amplification_trace


class EvaluationError(RuntimeError):
    def __init__(self, message: str, result: EvaluationResult | None = None) -> None:
        super().__init__(message)
        self.result = result


class RuleEngine:
    def __init__(
        self,
        mechanisms: MechanismRegistry | None = None,
        conditions: ConditionRegistry | None = None,
    ) -> None:
        self.mechanisms = mechanisms or default_mechanism_registry()
        self.conditions = conditions or default_condition_registry()

    def evaluate(
        self,
        state: GameState,
        effects: tuple[Effect, ...] | list[Effect] = (),
        *,
        mode: EvaluationMode = EvaluationMode.STRICT,
    ) -> EvaluationResult:
        base = state.current_entry.club.stats_at(state.current_entry.level)
        current = base.as_dict()
        journal = []
        unresolved: list[str] = []
        scheduled_effects = []
        remaining_effects = []
        consumed_effect_ids: list[str] = []

        for delayed in state.pending_effects:
            before = dict(current)
            try:
                applies = self.conditions.evaluate(delayed.trigger, state, current)
                trigger_parameters = dict(delayed.trigger.parameters)
                journal.append(
                    ExplainEntry(
                        source=delayed.source,
                        mechanism="DELAYED_TRIGGER",
                        condition=delayed.trigger.description or delayed.trigger.kind,
                        applied=applies,
                        before=before,
                        modification={name: 0.0 for name in before},
                        after=dict(current),
                        message="compatible club matched" if applies else "current club is not compatible; effect remains pending",
                        inputs={
                            "effect_id": delayed.identifier,
                            "current_club": state.current_entry.club.name,
                            "filter_field": trigger_parameters.get("field"),
                            "filter_value": trigger_parameters.get("value"),
                        },
                        outputs={"matched": applies, "consumed": False},
                    )
                )
                if not applies:
                    remaining_effects.append(delayed)
                    continue

                execution = self.mechanisms.execute(delayed.effect, current, state)
                current = execution.stats
                journal.extend(execution.explain)
                scheduled_effects.extend(execution.scheduled_effects)
                if "_original_amount" in delayed.effect.parameters and current != before:
                    journal.extend(amplification_trace(delayed.effect, "ADD_STAT",
                        {"delta": delayed.effect.parameters["_original_amount"]},
                        {"delta": delayed.effect.parameters["amount"], "target": state.current_club_id},
                        {"stat": delayed.effect.parameters.get("stat", "all_stats")}, current))
                journal.append(
                    explain_entry(
                        delayed.effect,
                        applied=True,
                        before=before,
                        after=current,
                        message="delayed effect resolved",
                    )
                )
                if delayed.consume_on_trigger:
                    consumed_effect_ids.append(delayed.identifier)
                    journal.append(
                        ExplainEntry(
                            source=delayed.source,
                            mechanism="CONSUME_DELAYED_EFFECT",
                            condition="effect resolved successfully",
                            applied=True,
                            before=dict(current),
                            modification={name: 0.0 for name in current},
                            after=dict(current),
                            message="delayed effect consumed",
                            inputs={"effect_id": delayed.identifier},
                            outputs={"consumed": True},
                        )
                    )
                else:
                    remaining_effects.append(delayed)
            except (UnknownConditionError, UnknownMechanismError, MechanismExecutionError) as exc:
                message = f"Unresolved {exc.__class__.__name__}: {exc}"
                unresolved.append(message)
                remaining_effects.append(delayed)
                journal.append(
                    ExplainEntry(
                        source=delayed.source,
                        mechanism="DELAYED_TRIGGER",
                        condition=delayed.trigger.description or delayed.trigger.kind,
                        applied=False,
                        before=before,
                        modification={name: 0.0 for name in before},
                        after=dict(current),
                        message=message,
                        inputs={"effect_id": delayed.identifier},
                        outputs={"matched": False, "consumed": False},
                    )
                )
                if mode is EvaluationMode.STRICT:
                    result = EvaluationResult(
                        base_stats=base,
                        final_stats=Stats.from_mapping(current),
                        explain=tuple(journal),
                        modifiers={name: value for name, value in current.items() if name not in base.as_dict()},
                        unresolved=tuple(unresolved),
                        complete=False,
                        scheduled_effects=tuple(scheduled_effects),
                        pending_effects=tuple([*remaining_effects, *scheduled_effects]),
                        consumed_effect_ids=tuple(consumed_effect_ids),
                    )
                    raise EvaluationError(message, result) from exc

        all_effects = [*effects, *state.active_bonuses]
        all_effects, transformation_journal, transformation_unknowns = prepare_abilities(
            all_effects, state, current, self.mechanisms, self.conditions,
        )
        journal.extend(transformation_journal)
        unresolved.extend(transformation_unknowns)
        if transformation_unknowns and mode is EvaluationMode.STRICT:
            result = EvaluationResult(base, Stats.from_mapping(current), tuple(journal),
                                      {name: value for name, value in current.items() if name not in base.as_dict()},
                                      tuple(unresolved), False, tuple(scheduled_effects),
                                      tuple([*remaining_effects, *scheduled_effects]), tuple(consumed_effect_ids))
            raise EvaluationError(transformation_unknowns[0], result)
        for effect in all_effects:
            before = dict(current)
            try:
                applies = self.conditions.evaluate(effect.condition, state, current)
                if applies:
                    execution = self.mechanisms.execute(effect, current, state)
                    current = execution.stats
                    journal.extend(execution.explain)
                    scheduled_effects.extend(execution.scheduled_effects)
                    if "_original_amount" in effect.parameters and current != before:
                        journal.extend(amplification_trace(effect, "ADD_STAT",
                            {"delta": effect.parameters["_original_amount"]},
                            {"delta": effect.parameters["amount"], "target": state.current_club_id},
                            {"stat": effect.parameters.get("stat", "all_stats")}, current))
                journal.append(
                    explain_entry(
                        effect,
                        applied=applies,
                        before=before,
                        after=current,
                        message="applied" if applies else "condition not satisfied",
                    )
                )
                journal[-1] = self._with_condition_details(journal[-1], effect, state, applies)
            except (UnknownConditionError, UnknownMechanismError, MechanismExecutionError) as exc:
                message = f"Unresolved {exc.__class__.__name__}: {exc}"
                unresolved.append(message)
                journal.append(
                    explain_entry(
                        effect,
                        applied=False,
                        before=before,
                        after=current,
                        message=message,
                    )
                )
                journal[-1] = self._with_condition_details(journal[-1], effect, state, False)
                if mode is EvaluationMode.STRICT:
                    result = EvaluationResult(
                        base_stats=base,
                        final_stats=Stats.from_mapping(current),
                        explain=tuple(journal),
                        modifiers={name: value for name, value in current.items() if name not in base.as_dict()},
                        unresolved=tuple(unresolved),
                        complete=False,
                        scheduled_effects=tuple(scheduled_effects),
                        pending_effects=tuple([*remaining_effects, *scheduled_effects]),
                        consumed_effect_ids=tuple(consumed_effect_ids),
                    )
                    raise EvaluationError(message, result) from exc

        return EvaluationResult(
            base_stats=base,
            final_stats=Stats.from_mapping(current),
            explain=tuple(journal),
            modifiers={name: value for name, value in current.items() if name not in base.as_dict()},
            unresolved=tuple(unresolved),
            complete=not unresolved,
            scheduled_effects=tuple(scheduled_effects),
            pending_effects=tuple([*remaining_effects, *scheduled_effects]),
            consumed_effect_ids=tuple(consumed_effect_ids),
        )

    @staticmethod
    def _with_condition_details(
        entry: ExplainEntry,
        effect: Effect,
        state: GameState,
        matched: bool,
    ) -> ExplainEntry:
        """Expose generic scenario-condition facts without coupling Explain to a family."""

        parameters = dict(effect.condition.parameters)
        field = parameters.get("field")
        if not isinstance(field, str):
            return entry
        expected = parameters.get("values", parameters.get("value"))
        inputs = dict(entry.inputs)
        inputs.update({"context_field": field, "expected": expected, "observed": getattr(state, field, None)})
        outputs = dict(entry.outputs)
        outputs["condition_matched"] = matched
        return ExplainEntry(
            source=entry.source,
            mechanism=entry.mechanism,
            condition=entry.condition,
            applied=entry.applied,
            before=entry.before,
            modification=entry.modification,
            after=entry.after,
            message=entry.message,
            inputs=inputs,
            outputs=outputs,
        )
