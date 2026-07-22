"""Minimal rule engine orchestrating conditions, mechanisms and Explain."""

from __future__ import annotations

from .conditions import ConditionRegistry, UnknownConditionError, default_condition_registry
from .explain import explain_entry
from .models import Effect, EvaluationMode, EvaluationResult, GameState, Stats
from .registry import MechanismRegistry, UnknownMechanismError, default_mechanism_registry


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

        all_effects = [*effects, *state.active_bonuses]
        for effect in all_effects:
            before = dict(current)
            try:
                applies = self.conditions.evaluate(effect.condition, state, current)
                if applies:
                    current = self.mechanisms.execute(effect, current, state)
                journal.append(
                    explain_entry(
                        effect,
                        applied=applies,
                        before=before,
                        after=current,
                        message="applied" if applies else "condition not satisfied",
                    )
                )
            except (UnknownConditionError, UnknownMechanismError) as exc:
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
                if mode is EvaluationMode.STRICT:
                    result = EvaluationResult(
                        base_stats=base,
                        final_stats=Stats.from_mapping(current),
                        explain=tuple(journal),
                        unresolved=tuple(unresolved),
                        complete=False,
                    )
                    raise EvaluationError(message, result) from exc

        return EvaluationResult(
            base_stats=base,
            final_stats=Stats.from_mapping(current),
            explain=tuple(journal),
            unresolved=tuple(unresolved),
            complete=not unresolved,
        )
