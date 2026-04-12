from __future__ import annotations

import random
import time
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

from game_config import DEFAULT_STATS, DIFFICULTIES, Difficulty
from game_core import NumberGuessGame


class NumberGuessGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Number Guess Game - GUI")
        self.geometry("860x640")
        self.minsize(760, 560)

        self.game = NumberGuessGame()

        self.mode_var = tk.StringVar(value="classic")
        self.status_var = tk.StringVar(value="Choose a mode, then click Start Game.")
        self.range_var = tk.StringVar(value="Range: -")
        self.attempts_var = tk.StringVar(value="Attempts left: -")
        self.hints_var = tk.StringVar(value="Hints used: -")

        self.difficulty_map = {
            f"{difficulty.name} ({difficulty.minimum}-{difficulty.maximum}, {difficulty.attempts} attempts)": difficulty
            for difficulty in DIFFICULTIES.values()
        }
        self.difficulty_var = tk.StringVar(value=next(iter(self.difficulty_map.keys())))

        self.game_active = False
        self.current_mode = "classic"
        self.current_level = 1
        self.current_difficulty: Difficulty | None = None
        self.target = 0
        self.attempts_left = 0
        self.guesses_used = 0
        self.hints_used = 0
        self.previous_distance: int | None = None
        self.hint_types_used: set[str] = set()
        self.round_start = 0.0

        self.survival_level = 1
        self.survival_total_score = 0
        self.survival_total_guesses = 0
        self.survival_total_hints = 0
        self.survival_start = 0.0

        self._build_ui()
        self._set_play_controls(active=False)

    def _build_ui(self) -> None:
        container = ttk.Frame(self, padding=14)
        container.pack(fill="both", expand=True)

        title = ttk.Label(
            container,
            text="Number Guessing Game",
            font=("Segoe UI", 20, "bold"),
        )
        title.pack(anchor="w")

        subtitle = ttk.Label(
            container,
            text="Play Classic or Survival mode with hints, warm/cold clues, and persistent stats.",
            font=("Segoe UI", 10),
        )
        subtitle.pack(anchor="w", pady=(2, 12))

        mode_frame = ttk.LabelFrame(container, text="Game Setup", padding=10)
        mode_frame.pack(fill="x")

        mode_row = ttk.Frame(mode_frame)
        mode_row.pack(fill="x")

        ttk.Radiobutton(
            mode_row,
            text="Classic",
            value="classic",
            variable=self.mode_var,
            command=self._on_mode_change,
        ).pack(side="left", padx=(0, 14))

        ttk.Radiobutton(
            mode_row,
            text="Survival",
            value="survival",
            variable=self.mode_var,
            command=self._on_mode_change,
        ).pack(side="left")

        diff_row = ttk.Frame(mode_frame)
        diff_row.pack(fill="x", pady=(10, 0))

        ttk.Label(diff_row, text="Classic difficulty:").pack(side="left", padx=(0, 8))
        self.difficulty_combo = ttk.Combobox(
            diff_row,
            textvariable=self.difficulty_var,
            values=list(self.difficulty_map.keys()),
            state="readonly",
            width=42,
        )
        self.difficulty_combo.pack(side="left")

        controls = ttk.Frame(container)
        controls.pack(fill="x", pady=(12, 10))

        self.start_button = ttk.Button(controls, text="Start Game", command=self.start_game)
        self.start_button.pack(side="left", padx=(0, 8))

        self.hint_button = ttk.Button(controls, text="Hint", command=self.request_hint)
        self.hint_button.pack(side="left", padx=(0, 8))

        self.forfeit_button = ttk.Button(controls, text="Forfeit", command=self.forfeit_round)
        self.forfeit_button.pack(side="left", padx=(0, 8))

        ttk.Button(controls, text="Show Stats", command=self.show_stats).pack(side="left", padx=(0, 8))
        ttk.Button(controls, text="Reset Stats", command=self.reset_stats).pack(side="left")

        guess_frame = ttk.LabelFrame(container, text="Make a Guess", padding=10)
        guess_frame.pack(fill="x")

        self.guess_entry = ttk.Entry(guess_frame, width=20)
        self.guess_entry.pack(side="left", padx=(0, 8))
        self.guess_entry.bind("<Return>", self.submit_guess)

        self.guess_button = ttk.Button(guess_frame, text="Submit Guess", command=self.submit_guess)
        self.guess_button.pack(side="left")

        info_frame = ttk.Frame(container)
        info_frame.pack(fill="x", pady=(10, 8))

        ttk.Label(info_frame, textvariable=self.status_var, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        ttk.Label(info_frame, textvariable=self.range_var).pack(anchor="w")
        ttk.Label(info_frame, textvariable=self.attempts_var).pack(anchor="w")
        ttk.Label(info_frame, textvariable=self.hints_var).pack(anchor="w")

        log_frame = ttk.LabelFrame(container, text="Game Log", padding=8)
        log_frame.pack(fill="both", expand=True)

        self.log_text = tk.Text(
            log_frame,
            wrap="word",
            state="disabled",
            height=20,
            font=("Consolas", 10),
        )
        self.log_text.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=scrollbar.set)

    def _on_mode_change(self) -> None:
        if self.mode_var.get() == "classic":
            self.difficulty_combo.configure(state="readonly")
        else:
            self.difficulty_combo.configure(state="disabled")

    def _set_play_controls(self, active: bool) -> None:
        state = "normal" if active else "disabled"
        self.guess_entry.configure(state=state)
        self.guess_button.configure(state=state)
        self.hint_button.configure(state=state)
        self.forfeit_button.configure(state=state)

        if active:
            self.guess_entry.focus_set()
        else:
            self.guess_entry.delete(0, "end")

    def _append_log(self, message: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _update_round_labels(self) -> None:
        self.range_var.set(
            f"Range: {self.current_difficulty.minimum}-{self.current_difficulty.maximum}"
            if self.current_difficulty
            else "Range: -"
        )
        self.attempts_var.set(f"Attempts left: {self.attempts_left}")
        self.hints_var.set(f"Hints used: {self.hints_used}/2")

    def start_game(self) -> None:
        if self.game_active:
            restart = messagebox.askyesno(
                "Restart round",
                "A round is currently running. Restart with new settings?",
            )
            if not restart:
                return

        if self.mode_var.get() == "classic":
            difficulty = self.difficulty_map[self.difficulty_var.get()]
            self.current_mode = "classic"
            self.current_level = 1
            self._start_round(difficulty, mode="classic", level=1)
        else:
            self.current_mode = "survival"
            self.survival_level = 1
            self.survival_total_score = 0
            self.survival_total_guesses = 0
            self.survival_total_hints = 0
            self.survival_start = time.time()
            self._append_log("=" * 70)
            self._append_log("Survival run started. Miss once and the run ends.")
            self._append_log("=" * 70)
            self._start_next_survival_level()

    def _start_round(self, difficulty: Difficulty, mode: str, level: int) -> None:
        self.game_active = True
        self.current_mode = mode
        self.current_level = level
        self.current_difficulty = difficulty
        self.target = random.randint(difficulty.minimum, difficulty.maximum)
        self.attempts_left = difficulty.attempts
        self.guesses_used = 0
        self.hints_used = 0
        self.previous_distance = None
        self.hint_types_used = set()
        self.round_start = time.time()

        self._set_play_controls(active=True)
        self._update_round_labels()

        if mode == "classic":
            self.status_var.set(f"Classic mode: {difficulty.name}")
            self._append_log("-" * 70)
            self._append_log(
                f"Classic round started: {difficulty.name} | "
                f"Range {difficulty.minimum}-{difficulty.maximum} | Attempts {difficulty.attempts}"
            )
        else:
            self.status_var.set(f"Survival mode: Level {level}")
            self._append_log("-" * 70)
            self._append_log(
                f"Survival level {level}: Range {difficulty.minimum}-{difficulty.maximum} | "
                f"Attempts {difficulty.attempts}"
            )

        self._append_log("Type a number and press Enter. Use Hint for clues or Forfeit to quit.")

    def _start_next_survival_level(self) -> None:
        maximum = 20 + (self.survival_level - 1) * 30
        attempts = 6 + min(4, self.survival_level // 2)
        difficulty = Difficulty(
            name=f"Survival L{self.survival_level}",
            minimum=1,
            maximum=maximum,
            attempts=attempts,
            multiplier=1.0 + self.survival_level * 0.12,
        )
        self._start_round(difficulty, mode="survival", level=self.survival_level)

    def submit_guess(self, _event: tk.Event | None = None) -> None:
        if not self.game_active or not self.current_difficulty:
            messagebox.showinfo("No active game", "Start a game first.")
            return

        raw_value = self.guess_entry.get().strip()
        self.guess_entry.delete(0, "end")

        if not raw_value:
            return

        if not raw_value.lstrip("-").isdigit():
            self._append_log("Enter a whole number.")
            return

        guess = int(raw_value)
        minimum = self.current_difficulty.minimum
        maximum = self.current_difficulty.maximum

        if guess < minimum or guess > maximum:
            self._append_log(f"Stay in range: {minimum}-{maximum}.")
            return

        self.attempts_left -= 1
        self.guesses_used += 1

        if guess == self.target:
            self._handle_round_win()
            return

        direction = "Too low" if guess < self.target else "Too high"
        distance = abs(guess - self.target)
        warmth = self.game.proximity_text(distance, maximum - minimum)

        trend = ""
        if self.previous_distance is not None:
            if distance < self.previous_distance:
                trend = " Getting warmer."
            elif distance > self.previous_distance:
                trend = " Getting colder."
            else:
                trend = " Same distance as your previous guess."
        self.previous_distance = distance

        self._append_log(f"{direction}. {warmth}.{trend}")

        if self.guesses_used % 3 == 0 and self.attempts_left > 0:
            window = max(2, (maximum - minimum) // 8)
            low_bound = max(minimum, self.target - window)
            high_bound = min(maximum, self.target + window)
            self._append_log(f"Range pulse: the number is between {low_bound} and {high_bound}.")

        if self.attempts_left <= 0:
            self._handle_round_loss()
            return

        self._update_round_labels()

    def request_hint(self) -> None:
        if not self.game_active or not self.current_difficulty:
            messagebox.showinfo("No active game", "Start a game first.")
            return

        if self.hints_used >= 2:
            self._append_log("No hints remaining for this round.")
            return

        self.hints_used += 1
        hint = self.game.build_hint(
            self.target,
            self.current_difficulty.minimum,
            self.current_difficulty.maximum,
            self.hint_types_used,
        )
        self._append_log(f"Hint: {hint}")
        self._update_round_labels()

    def forfeit_round(self) -> None:
        if not self.game_active:
            messagebox.showinfo("No active game", "Start a game first.")
            return

        confirmed = messagebox.askyesno("Forfeit", "End this round now?")
        if not confirmed:
            return

        elapsed = time.time() - self.round_start
        result = {
            "won": False,
            "forfeit": True,
            "target": self.target,
            "guesses": self.guesses_used,
            "hints_used": self.hints_used,
            "attempts_left": self.attempts_left,
            "elapsed": elapsed,
            "score": 0,
            "mode": self.current_mode,
            "level": self.current_level,
        }

        if self.current_mode == "classic":
            self._finish_classic_round(result)
            return

        self.survival_total_guesses += self.guesses_used
        self.survival_total_hints += self.hints_used
        self._finish_survival_run(last_result=result)

    def _handle_round_win(self) -> None:
        if self.current_difficulty is None:
            return

        elapsed = time.time() - self.round_start
        score = self.game.calculate_score(
            difficulty=self.current_difficulty,
            attempts_left=self.attempts_left,
            hints_used=self.hints_used,
            guesses_used=self.guesses_used,
            elapsed=elapsed,
        )

        result = {
            "won": True,
            "forfeit": False,
            "target": self.target,
            "guesses": self.guesses_used,
            "hints_used": self.hints_used,
            "attempts_left": self.attempts_left,
            "elapsed": elapsed,
            "score": score,
            "mode": self.current_mode,
            "level": self.current_level,
        }

        if self.current_mode == "classic":
            self._finish_classic_round(result)
            return

        self.survival_total_guesses += self.guesses_used
        self.survival_total_hints += self.hints_used

        level_bonus = 30 * self.survival_level
        self.survival_total_score += score + level_bonus

        self._append_log(
            f"Level {self.survival_level} cleared. Round score: {score}, "
            f"bonus: {level_bonus}, running total: {self.survival_total_score}."
        )

        self.survival_level += 1
        self._start_next_survival_level()

    def _handle_round_loss(self) -> None:
        elapsed = time.time() - self.round_start
        result = {
            "won": False,
            "forfeit": False,
            "target": self.target,
            "guesses": self.guesses_used,
            "hints_used": self.hints_used,
            "attempts_left": 0,
            "elapsed": elapsed,
            "score": 0,
            "mode": self.current_mode,
            "level": self.current_level,
        }

        if self.current_mode == "classic":
            self._finish_classic_round(result)
            return

        self.survival_total_guesses += self.guesses_used
        self.survival_total_hints += self.hints_used
        self._finish_survival_run(last_result=result)

    def _finish_classic_round(self, result: dict[str, Any]) -> None:
        self.game.update_stats(result)
        self.game.save_stats()

        self.game_active = False
        self._set_play_controls(active=False)
        self._update_round_labels()

        if result["won"]:
            self.status_var.set("Classic round won")
            self._append_log("=" * 70)
            self._append_log("Result: WIN")
            self._append_log(f"Score: {result['score']}")
            self._append_log(f"Guesses: {result['guesses']}")
            self._append_log(f"Hints: {result['hints_used']}")
            self._append_log(f"Time: {self.game.format_duration(float(result['elapsed']))}")
            self._append_log("=" * 70)
        elif result["forfeit"]:
            self.status_var.set("Classic round forfeited")
            self._append_log("=" * 70)
            self._append_log("Result: FORFEIT")
            self._append_log(f"Target was: {result['target']}")
            self._append_log("=" * 70)
        else:
            self.status_var.set("Classic round lost")
            self._append_log("=" * 70)
            self._append_log("Result: LOSS")
            self._append_log(f"Target was: {result['target']}")
            self._append_log(f"Guesses made: {result['guesses']}")
            self._append_log(f"Hints used: {result['hints_used']}")
            self._append_log("=" * 70)

    def _finish_survival_run(self, last_result: dict[str, Any]) -> None:
        reached_level = self.survival_level - 1
        elapsed = time.time() - self.survival_start
        run_success = reached_level >= 1

        run_result = {
            "won": run_success,
            "forfeit": bool(last_result["forfeit"]),
            "target": int(last_result["target"]),
            "guesses": self.survival_total_guesses,
            "hints_used": self.survival_total_hints,
            "attempts_left": 0,
            "elapsed": elapsed,
            "score": self.survival_total_score,
            "mode": "survival",
            "level": max(1, reached_level),
        }

        self.game.update_stats(run_result)
        self.game.save_stats()

        self.game_active = False
        self._set_play_controls(active=False)
        self._update_round_labels()

        self.status_var.set("Survival run finished")
        self._append_log("=" * 70)
        self._append_log("Survival run complete")
        self._append_log(f"Levels cleared: {reached_level}")
        self._append_log(f"Final score: {self.survival_total_score}")
        self._append_log(f"Total guesses: {self.survival_total_guesses}")
        self._append_log(f"Total hints used: {self.survival_total_hints}")
        self._append_log(f"Run time: {self.game.format_duration(elapsed)}")

        if bool(last_result["forfeit"]):
            self._append_log("Run ended by forfeit.")
        else:
            self._append_log(f"Final level target was: {last_result['target']}")

        self._append_log("=" * 70)

    def show_stats(self) -> None:
        stats_text = self._format_stats_text()
        messagebox.showinfo("Player Statistics", stats_text)
        self._append_log("Stats viewed.")

    def _format_stats_text(self) -> str:
        games = self.game.stats["total_games"]
        wins = self.game.stats["total_wins"]
        win_rate = (wins / games * 100.0) if games else 0.0
        avg_score = (self.game.stats["total_score"] / games) if games else 0.0
        avg_guesses = (self.game.stats["total_guesses"] / games) if games else 0.0

        fastest = self.game.stats["fastest_win_seconds"]
        if fastest is None:
            fastest_text = "N/A"
        else:
            fastest_text = self.game.format_duration(float(fastest))

        last_played = self.game.stats["last_played"] or "N/A"

        lines = [
            f"Games played: {games}",
            f"Wins: {wins} ({win_rate:.1f}%)",
            f"Best score: {self.game.stats['best_score']}",
            f"Average score per game: {avg_score:.1f}",
            f"Average guesses per game: {avg_guesses:.1f}",
            f"Current streak: {self.game.stats['current_streak']}",
            f"Longest streak: {self.game.stats['longest_streak']}",
            f"Classic record: {self.game.stats['classic_wins']} / {self.game.stats['classic_games']}",
            "Survival successful runs: "
            f"{self.game.stats['survival_successes']} / {self.game.stats['survival_games']}",
            f"Highest survival level cleared: {self.game.stats['highest_survival_level']}",
            f"Fastest win: {fastest_text}",
            f"Last played: {last_played}",
        ]
        return "\n".join(lines)

    def reset_stats(self) -> None:
        confirmed = messagebox.askyesno(
            "Reset stats",
            "Clear all saved stats? This cannot be undone.",
        )
        if not confirmed:
            return

        self.game.stats = DEFAULT_STATS.copy()
        self.game.save_stats()
        self._append_log("Stats reset successfully.")
        self.status_var.set("Stats reset")


def launch_gui() -> None:
    app = NumberGuessGUI()
    app.mainloop()


if __name__ == "__main__":
    launch_gui()
