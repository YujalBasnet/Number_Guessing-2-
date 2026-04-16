from __future__ import annotations

import random
import time
from typing import Any

from flask import Flask, redirect, render_template, request, session, url_for

from game_config import DIFFICULTIES, Difficulty, DEFAULT_STATS
from game_core import NumberGuessGame

app = Flask(__name__)
app.secret_key = "number-guess-web-secret"

engine = NumberGuessGame()


def difficulty_to_dict(difficulty: Difficulty) -> dict[str, Any]:
    return {
        "name": difficulty.name,
        "minimum": difficulty.minimum,
        "maximum": difficulty.maximum,
        "attempts": difficulty.attempts,
        "multiplier": difficulty.multiplier,
    }


def difficulty_from_dict(data: dict[str, Any]) -> Difficulty:
    return Difficulty(
        name=str(data["name"]),
        minimum=int(data["minimum"]),
        maximum=int(data["maximum"]),
        attempts=int(data["attempts"]),
        multiplier=float(data["multiplier"]),
    )


def get_state() -> dict[str, Any] | None:
    return session.get("game_state")


def save_state(state: dict[str, Any]) -> None:
    session["game_state"] = state


def clear_state() -> None:
    session.pop("game_state", None)


def get_log() -> list[str]:
    return session.get("log", [])


def append_log(message: str) -> None:
    log = get_log()
    log.append(message)
    session["log"] = log[-250:]


def clear_log() -> None:
    session["log"] = []


def make_survival_difficulty(level: int) -> Difficulty:
    maximum = 20 + (level - 1) * 30
    attempts = 6 + min(4, level // 2)
    return Difficulty(
        name=f"Survival L{level}",
        minimum=1,
        maximum=maximum,
        attempts=attempts,
        multiplier=1.0 + level * 0.12,
    )


def start_round(mode: str, difficulty: Difficulty, level: int, state: dict[str, Any]) -> None:
    state["active"] = True
    state["mode"] = mode
    state["level"] = level
    state["difficulty"] = difficulty_to_dict(difficulty)
    state["target"] = random.randint(difficulty.minimum, difficulty.maximum)
    state["attempts_left"] = difficulty.attempts
    state["guesses_used"] = 0
    state["hints_used"] = 0
    state["previous_distance"] = None
    state["hint_types_used"] = []
    state["round_start"] = time.time()


def finish_classic_round(state: dict[str, Any], result: dict[str, Any]) -> None:
    engine.update_stats(result)
    engine.save_stats()

    state["active"] = False

    if result["won"]:
        append_log("=" * 68)
        append_log("Result: WIN")
        append_log(f"Score earned: {result['score']}")
        append_log(f"Guesses used: {result['guesses']}")
        append_log(f"Hints used: {result['hints_used']}")
        append_log(f"Time: {engine.format_duration(float(result['elapsed']))}")
        append_log("=" * 68)
    elif result["forfeit"]:
        append_log("=" * 68)
        append_log("Result: FORFEIT")
        append_log(f"Target was: {result['target']}")
        append_log("=" * 68)
    else:
        append_log("=" * 68)
        append_log("Result: LOSS")
        append_log(f"Target was: {result['target']}")
        append_log(f"Guesses made: {result['guesses']}")
        append_log(f"Hints used: {result['hints_used']}")
        append_log("=" * 68)


def finish_survival_run(state: dict[str, Any], last_result: dict[str, Any]) -> None:
    reached_level = int(state.get("survival_level", 1)) - 1
    elapsed = time.time() - float(state.get("survival_start", time.time()))
    run_success = reached_level >= 1

    run_result = {
        "won": run_success,
        "forfeit": bool(last_result["forfeit"]),
        "target": int(last_result["target"]),
        "guesses": int(state.get("survival_total_guesses", 0)),
        "hints_used": int(state.get("survival_total_hints", 0)),
        "attempts_left": 0,
        "elapsed": elapsed,
        "score": int(state.get("survival_total_score", 0)),
        "mode": "survival",
        "level": max(1, reached_level),
    }

    engine.update_stats(run_result)
    engine.save_stats()

    state["active"] = False

    append_log("=" * 68)
    append_log("Survival run complete")
    append_log(f"Levels cleared: {reached_level}")
    append_log(f"Final score: {state.get('survival_total_score', 0)}")
    append_log(f"Total guesses: {state.get('survival_total_guesses', 0)}")
    append_log(f"Total hints used: {state.get('survival_total_hints', 0)}")
    append_log(f"Run time: {engine.format_duration(elapsed)}")

    if bool(last_result["forfeit"]):
        append_log("Run ended by forfeit.")
    else:
        append_log(f"Final level target was: {last_result['target']}")
    append_log("=" * 68)


@app.get("/")
def index() -> str:
    state = get_state() or {}
    difficulty = None

    if state.get("difficulty"):
        difficulty = difficulty_from_dict(state["difficulty"])

    return render_template(
        "index.html",
        state=state,
        difficulty=difficulty,
        difficulties=DIFFICULTIES,
        log=get_log(),
    )


@app.post("/start")
def start_game() -> Any:
    mode = request.form.get("mode", "classic")
    difficulty_key = request.form.get("difficulty", "2")

    state: dict[str, Any] = {}
    clear_log()

    if mode == "classic":
        difficulty = DIFFICULTIES.get(difficulty_key, DIFFICULTIES["2"])
        append_log("-" * 68)
        append_log(
            f"Classic round started: {difficulty.name} | "
            f"Range {difficulty.minimum}-{difficulty.maximum} | Attempts {difficulty.attempts}"
        )
        append_log("Use Guess, Hint, or Forfeit.")
        start_round(mode="classic", difficulty=difficulty, level=1, state=state)
    else:
        state["survival_level"] = 1
        state["survival_total_score"] = 0
        state["survival_total_guesses"] = 0
        state["survival_total_hints"] = 0
        state["survival_start"] = time.time()

        append_log("=" * 68)
        append_log("Survival run started. One miss ends the run.")
        append_log("=" * 68)

        level = int(state["survival_level"])
        difficulty = make_survival_difficulty(level)
        append_log("-" * 68)
        append_log(
            f"Survival level {level}: "
            f"Range {difficulty.minimum}-{difficulty.maximum} | Attempts {difficulty.attempts}"
        )
        append_log("Use Guess, Hint, or Forfeit.")
        start_round(mode="survival", difficulty=difficulty, level=level, state=state)

    save_state(state)
    return redirect(url_for("index"))


@app.post("/guess")
def submit_guess() -> Any:
    state = get_state()
    if not state or not state.get("active"):
        append_log("Start a game first.")
        return redirect(url_for("index"))

    difficulty = difficulty_from_dict(state["difficulty"])
    raw_value = request.form.get("guess", "").strip()

    if not raw_value:
        append_log("Enter a number.")
        return redirect(url_for("index"))

    if not raw_value.lstrip("-").isdigit():
        append_log("Enter a whole number.")
        return redirect(url_for("index"))

    guess = int(raw_value)
    if guess < difficulty.minimum or guess > difficulty.maximum:
        append_log(f"Stay in range: {difficulty.minimum}-{difficulty.maximum}.")
        return redirect(url_for("index"))

    state["attempts_left"] = int(state["attempts_left"]) - 1
    state["guesses_used"] = int(state["guesses_used"]) + 1

    target = int(state["target"])

    if guess == target:
        elapsed = time.time() - float(state["round_start"])
        score = engine.calculate_score(
            difficulty=difficulty,
            attempts_left=int(state["attempts_left"]),
            hints_used=int(state["hints_used"]),
            guesses_used=int(state["guesses_used"]),
            elapsed=elapsed,
        )

        result = {
            "won": True,
            "forfeit": False,
            "target": target,
            "guesses": int(state["guesses_used"]),
            "hints_used": int(state["hints_used"]),
            "attempts_left": int(state["attempts_left"]),
            "elapsed": elapsed,
            "score": score,
            "mode": state["mode"],
            "level": int(state["level"]),
        }

        if state["mode"] == "classic":
            finish_classic_round(state, result)
            save_state(state)
            return redirect(url_for("index"))

        state["survival_total_guesses"] = int(state.get("survival_total_guesses", 0)) + int(
            state["guesses_used"]
        )
        state["survival_total_hints"] = int(state.get("survival_total_hints", 0)) + int(state["hints_used"])

        level = int(state.get("survival_level", 1))
        level_bonus = 30 * level
        state["survival_total_score"] = int(state.get("survival_total_score", 0)) + score + level_bonus

        append_log(
            f"Level {level} cleared. Round score: {score}, "
            f"bonus: {level_bonus}, running total: {state['survival_total_score']}."
        )

        state["survival_level"] = level + 1
        next_level = int(state["survival_level"])
        next_difficulty = make_survival_difficulty(next_level)

        append_log("-" * 68)
        append_log(
            f"Survival level {next_level}: "
            f"Range {next_difficulty.minimum}-{next_difficulty.maximum} | "
            f"Attempts {next_difficulty.attempts}"
        )

        start_round(mode="survival", difficulty=next_difficulty, level=next_level, state=state)
        save_state(state)
        return redirect(url_for("index"))

    direction = "Too low" if guess < target else "Too high"
    distance = abs(guess - target)
    warmth = engine.proximity_text(distance, difficulty.maximum - difficulty.minimum)

    trend = ""
    previous_distance = state.get("previous_distance")
    if previous_distance is not None:
        previous_distance_int = int(previous_distance)
        if distance < previous_distance_int:
            trend = " Getting warmer."
        elif distance > previous_distance_int:
            trend = " Getting colder."
        else:
            trend = " Same distance as your previous guess."

    state["previous_distance"] = distance
    append_log(f"{direction}. {warmth}.{trend}")

    if int(state["guesses_used"]) % 3 == 0 and int(state["attempts_left"]) > 0:
        window = max(2, (difficulty.maximum - difficulty.minimum) // 8)
        low_bound = max(difficulty.minimum, target - window)
        high_bound = min(difficulty.maximum, target + window)
        append_log(f"Range pulse: the number is between {low_bound} and {high_bound}.")

    if int(state["attempts_left"]) <= 0:
        elapsed = time.time() - float(state["round_start"])
        result = {
            "won": False,
            "forfeit": False,
            "target": target,
            "guesses": int(state["guesses_used"]),
            "hints_used": int(state["hints_used"]),
            "attempts_left": 0,
            "elapsed": elapsed,
            "score": 0,
            "mode": state["mode"],
            "level": int(state["level"]),
        }

        if state["mode"] == "classic":
            finish_classic_round(state, result)
            save_state(state)
            return redirect(url_for("index"))

        state["survival_total_guesses"] = int(state.get("survival_total_guesses", 0)) + int(
            state["guesses_used"]
        )
        state["survival_total_hints"] = int(state.get("survival_total_hints", 0)) + int(state["hints_used"])

        finish_survival_run(state, result)
        save_state(state)
        return redirect(url_for("index"))

    save_state(state)
    return redirect(url_for("index"))


@app.post("/hint")
def request_hint() -> Any:
    state = get_state()
    if not state or not state.get("active"):
        append_log("Start a game first.")
        return redirect(url_for("index"))

    if int(state["hints_used"]) >= 2:
        append_log("No hints remaining for this round.")
        return redirect(url_for("index"))

    difficulty = difficulty_from_dict(state["difficulty"])

    hint_types_used = set(state.get("hint_types_used", []))
    hint = engine.build_hint(
        int(state["target"]),
        difficulty.minimum,
        difficulty.maximum,
        hint_types_used,
    )

    state["hints_used"] = int(state["hints_used"]) + 1
    state["hint_types_used"] = sorted(hint_types_used)

    append_log(f"Hint: {hint}")
    save_state(state)
    return redirect(url_for("index"))


@app.post("/forfeit")
def forfeit_round() -> Any:
    state = get_state()
    if not state or not state.get("active"):
        append_log("Start a game first.")
        return redirect(url_for("index"))

    elapsed = time.time() - float(state["round_start"])
    result = {
        "won": False,
        "forfeit": True,
        "target": int(state["target"]),
        "guesses": int(state["guesses_used"]),
        "hints_used": int(state["hints_used"]),
        "attempts_left": int(state["attempts_left"]),
        "elapsed": elapsed,
        "score": 0,
        "mode": state["mode"],
        "level": int(state["level"]),
    }

    if state["mode"] == "classic":
        finish_classic_round(state, result)
        save_state(state)
        return redirect(url_for("index"))

    state["survival_total_guesses"] = int(state.get("survival_total_guesses", 0)) + int(
        state["guesses_used"]
    )
    state["survival_total_hints"] = int(state.get("survival_total_hints", 0)) + int(state["hints_used"])

    finish_survival_run(state, result)
    save_state(state)
    return redirect(url_for("index"))


@app.post("/new")
def start_new() -> Any:
    clear_state()
    clear_log()
    return redirect(url_for("index"))


@app.get("/stats")
def stats() -> str:
    games = engine.stats["total_games"]
    wins = engine.stats["total_wins"]
    win_rate = (wins / games * 100.0) if games else 0.0
    avg_score = (engine.stats["total_score"] / games) if games else 0.0
    avg_guesses = (engine.stats["total_guesses"] / games) if games else 0.0

    fastest = engine.stats["fastest_win_seconds"]
    fastest_text = "N/A" if fastest is None else engine.format_duration(float(fastest))

    return render_template(
        "stats.html",
        stats=engine.stats,
        win_rate=win_rate,
        avg_score=avg_score,
        avg_guesses=avg_guesses,
        fastest_text=fastest_text,
    )


@app.post("/reset-stats")
def reset_stats() -> Any:
    engine.stats = DEFAULT_STATS.copy()
    engine.save_stats()
    append_log("Stats reset successfully.")
    return redirect(url_for("stats"))


def launch_web(debug: bool = True) -> None:
    app.run(debug=debug)


if __name__ == "__main__":
    launch_web(debug=True)
