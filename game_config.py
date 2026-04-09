from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

STATS_FILE = Path(__file__).resolve().parent / "stats.json"


@dataclass(frozen=True)
class Difficulty:
    name: str
    minimum: int
    maximum: int
    attempts: int
    multiplier: float


DEFAULT_STATS: dict[str, Any] = {
    "total_games": 0,
    "total_wins": 0,
    "classic_games": 0,
    "classic_wins": 0,
    "survival_games": 0,
    "survival_successes": 0,
    "best_score": 0,
    "total_score": 0,
    "total_guesses": 0,
    "fastest_win_seconds": None,
    "current_streak": 0,
    "longest_streak": 0,
    "highest_survival_level": 0,
    "last_played": None,
}


DIFFICULTIES: dict[str, Difficulty] = {
    "1": Difficulty("Easy", 1, 50, 10, 1.0),
    "2": Difficulty("Medium", 1, 100, 9, 1.25),
    "3": Difficulty("Hard", 1, 300, 10, 1.6),
    "4": Difficulty("Insane", 1, 1000, 12, 2.2),
}
