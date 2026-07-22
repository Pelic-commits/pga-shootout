"""Data-driven simulation foundations for PGA TOUR Golf Shootout."""

from .engine import RuleEngine
from .models import Ability, Bag, Club, EvaluationMode, EvaluationResult, GameState, Stats

__all__ = [
    "Ability",
    "Bag",
    "Club",
    "EvaluationMode",
    "EvaluationResult",
    "GameState",
    "RuleEngine",
    "Stats",
]

__version__ = "0.1.0"
