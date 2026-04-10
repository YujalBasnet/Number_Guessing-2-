from __future__ import annotations

import json
import math
import random
import time
from datetime import datetime
from typing import Any

from game_config import DEFAULT_STATS, DIFFICULTIES, STATS_FILE, Difficulty


class NumberGuessGame:
	def __init__(self) -> None:
		self.stats = self.load_stats()

	def load_stats(self) -> dict[str, Any]:
		if not STATS_FILE.exists():
			return DEFAULT_STATS.copy()

		try:
			with STATS_FILE.open("r", encoding="utf-8") as handle:
				loaded = json.load(handle)
			merged = DEFAULT_STATS.copy()
			merged.update(loaded)
			return merged
		except (json.JSONDecodeError, OSError):
			return DEFAULT_STATS.copy()

	def save_stats(self) -> None:
		with STATS_FILE.open("w", encoding="utf-8") as handle:
			json.dump(self.stats, handle, indent=2)

	@staticmethod
	def ask_int(prompt: str, minimum: int, maximum: int) -> int:
		while True:
			value = input(prompt).strip()
			if value.lstrip("-").isdigit():
				number = int(value)
				if minimum <= number <= maximum:
					return number
			print(f"Enter a whole number between {minimum} and {maximum}.")

	@staticmethod
	def is_prime(value: int) -> bool:
		if value <= 1:
			return False
		if value <= 3:
			return True
		if value % 2 == 0 or value % 3 == 0:
			return False
		factor = 5
		while factor * factor <= value:
			if value % factor == 0 or value % (factor + 2) == 0:
				return False
			factor += 6
		return True

	@staticmethod
	def proximity_text(distance: int, span: int) -> str:
		ratio = distance / max(1, span)
		if ratio <= 0.02:
			return "Scorching hot"
		if ratio <= 0.06:
			return "Hot"
		if ratio <= 0.14:
			return "Warm"
		if ratio <= 0.28:
			return "Cool"
		return "Cold"

	@staticmethod
	def format_duration(seconds: float) -> str:
		seconds = max(0.0, seconds)
		minutes = int(seconds // 60)
		remainder = seconds % 60
		if minutes:
			return f"{minutes}m {remainder:.1f}s"
		return f"{remainder:.1f}s"

	@staticmethod
	def banner() -> None:
		print("\n" + "=" * 64)
		print("          NUMBER GUESSING GAME")
		print("=" * 64)
		print("Modes: Classic, Survival | Commands: hint, quit")
		print("Use clues, read warm/cold feedback, and chase high scores.")
		print("=" * 64 + "\n")

	def show_menu(self) -> str:
		print("Main Menu")
		print("1. Play Classic Mode")
		print("2. Play Survival Mode")
		print("3. View Stats")
		print("4. Reset Stats")
		print("5. Exit")

		while True:
			choice = input("Choose an option (1-5): ").strip()
			if choice in {"1", "2", "3", "4", "5"}:
				return choice
			print("Invalid option. Choose 1 to 5.")

	def choose_difficulty(self) -> Difficulty:
		print("\nClassic Difficulty")
		for key, level in DIFFICULTIES.items():
			print(
				f"{key}. {level.name:<7} | Range: {level.minimum}-{level.maximum} "
				f"| Attempts: {level.attempts} | Multiplier: x{level.multiplier:.2f}"
			)
		print("5. Custom")

		while True:
			choice = input("Select difficulty (1-5): ").strip()
			if choice in DIFFICULTIES:
				return DIFFICULTIES[choice]
			if choice == "5":
				return self.make_custom_difficulty()
			print("Pick a valid option from 1 to 5.")

	def make_custom_difficulty(self) -> Difficulty:
		print("\nCustom Difficulty Setup")
		minimum = self.ask_int("Minimum number: ", -1000000, 1000000)
		maximum = self.ask_int("Maximum number: ", minimum + 5, 1000000)
		attempts = self.ask_int("Attempts (3-30): ", 3, 30)

		span = maximum - minimum + 1
		multiplier = max(1.0, min(3.0, 1.0 + math.log10(max(10, span)) / 2))

		return Difficulty("Custom", minimum, maximum, attempts, round(multiplier, 2))

	def build_hint(
		self,
		target: int,
		minimum: int,
		maximum: int,
		hint_types_used: set[str],
	) -> str:
		midpoint = (minimum + maximum) // 2
		quartile = (maximum - minimum + 1) // 4

		pool: list[tuple[str, str]] = []

		pool.append(("parity", "The number is even." if target % 2 == 0 else "The number is odd."))

		if target > 1:
			pool.append(
				(
					"prime",
					"The number is prime." if self.is_prime(target) else "The number is not prime.",
				)
			)

		if target <= midpoint:
			pool.append(("half", f"The number is in the lower half ({minimum}-{midpoint})."))
		else:
			pool.append(("half", f"The number is in the upper half ({midpoint + 1}-{maximum})."))

		q1 = minimum + quartile
		q2 = minimum + quartile * 2
		q3 = minimum + quartile * 3

		if target <= q1:
			pool.append(("quartile", "The number sits in the first quarter of the range."))
		elif target <= q2:
			pool.append(("quartile", "The number sits in the second quarter of the range."))
		elif target <= q3:
			pool.append(("quartile", "The number sits in the third quarter of the range."))
		else:
			pool.append(("quartile", "The number sits in the fourth quarter of the range."))

		if target % 3 == 0:
			pool.append(("multiple", "The number is divisible by 3."))
		elif target % 5 == 0:
			pool.append(("multiple", "The number is divisible by 5."))
		else:
			pool.append(("multiple", "The number is not divisible by 3 or 5."))

		candidates = [hint for hint in pool if hint[0] not in hint_types_used]
		if not candidates:
			hint_types_used.clear()
			candidates = pool

		key, message = random.choice(candidates)
		hint_types_used.add(key)
		return message

	def calculate_score(
		self,
		difficulty: Difficulty,
		attempts_left: int,
		hints_used: int,
		guesses_used: int,
		elapsed: float,
	) -> int:
		span = difficulty.maximum - difficulty.minimum + 1
		complexity_points = int(math.log2(max(2, span)) * 18 * difficulty.multiplier)
		efficiency_points = int((attempts_left / difficulty.attempts) * 220)
		speed_points = int(max(0.0, 180.0 - elapsed) * difficulty.multiplier)
		precision_points = max(0, (10 - guesses_used) * 12)
		hint_penalty = hints_used * 40

		total = complexity_points + efficiency_points + speed_points + precision_points - hint_penalty
		return max(0, total)

	def play_round(
		self,
		difficulty: Difficulty,
		mode: str,
		level: int = 1,
	) -> dict[str, Any]:
		print("\n" + "-" * 64)
		if mode == "survival":
			print(f"Survival Level {level}")
		print(
			f"Guess a number from {difficulty.minimum} to {difficulty.maximum}. "
			f"You have {difficulty.attempts} attempts."
		)
		print("Type 'hint' for a clue (up to 2). Type 'quit' to forfeit the round.")
		print("-" * 64)

		target = random.randint(difficulty.minimum, difficulty.maximum)
		attempts_left = difficulty.attempts
		guesses_used = 0
		hints_used = 0
		previous_distance: int | None = None
		hint_types_used: set[str] = set()
		start_time = time.time()

		while attempts_left > 0:
			print(f"\nAttempts left: {attempts_left}")
			user_value = input("Your move: ").strip().lower()

			if user_value == "quit":
				elapsed = time.time() - start_time
				return {
					"won": False,
					"forfeit": True,
					"target": target,
					"guesses": guesses_used,
					"hints_used": hints_used,
					"attempts_left": attempts_left,
					"elapsed": elapsed,
					"score": 0,
					"mode": mode,
					"level": level,
				}

			if user_value == "hint":
				if hints_used >= 2:
					print("No hints remaining for this round.")
					continue
				hints_used += 1
				print("Hint:", self.build_hint(target, difficulty.minimum, difficulty.maximum, hint_types_used))
				continue

			if not user_value.lstrip("-").isdigit():
				print("Enter a valid whole number, or use 'hint'/'quit'.")
				continue

			guess = int(user_value)
			if guess < difficulty.minimum or guess > difficulty.maximum:
				print(f"Stay in range: {difficulty.minimum}-{difficulty.maximum}.")
				continue

			attempts_left -= 1
			guesses_used += 1

			if guess == target:
				elapsed = time.time() - start_time
				score = self.calculate_score(difficulty, attempts_left, hints_used, guesses_used, elapsed)
				return {
					"won": True,
					"forfeit": False,
					"target": target,
					"guesses": guesses_used,
					"hints_used": hints_used,
					"attempts_left": attempts_left,
					"elapsed": elapsed,
					"score": score,
					"mode": mode,
					"level": level,
				}

			direction = "Too low" if guess < target else "Too high"
			distance = abs(guess - target)
			warmth = self.proximity_text(distance, difficulty.maximum - difficulty.minimum)

			trend = ""
			if previous_distance is not None:
				if distance < previous_distance:
					trend = " Getting warmer."
				elif distance > previous_distance:
					trend = " Getting colder."
				else:
					trend = " Same distance as your previous guess."
			previous_distance = distance

			print(f"{direction}. {warmth}.{trend}")

			if guesses_used % 3 == 0 and attempts_left > 0:
				window = max(2, (difficulty.maximum - difficulty.minimum) // 8)
				low_bound = max(difficulty.minimum, target - window)
				high_bound = min(difficulty.maximum, target + window)
				print(f"Range pulse: the number is between {low_bound} and {high_bound}.")

		elapsed = time.time() - start_time
		return {
			"won": False,
			"forfeit": False,
			"target": target,
			"guesses": guesses_used,
			"hints_used": hints_used,
			"attempts_left": attempts_left,
			"elapsed": elapsed,
			"score": 0,
			"mode": mode,
			"level": level,
		}

	def update_stats(self, result: dict[str, Any]) -> None:
		mode = result["mode"]
		won = bool(result["won"])
		score = int(result["score"])
		guesses = int(result["guesses"])
		elapsed = float(result["elapsed"])

		self.stats["total_games"] += 1
		self.stats["total_score"] += score
		self.stats["total_guesses"] += guesses
		self.stats["best_score"] = max(self.stats["best_score"], score)
		self.stats["last_played"] = datetime.now().isoformat(timespec="seconds")

		if mode == "classic":
			self.stats["classic_games"] += 1
		elif mode == "survival":
			self.stats["survival_games"] += 1

		if won:
			self.stats["total_wins"] += 1
			self.stats["current_streak"] += 1
			self.stats["longest_streak"] = max(self.stats["longest_streak"], self.stats["current_streak"])

			if mode == "classic":
				self.stats["classic_wins"] += 1
			elif mode == "survival":
				self.stats["survival_successes"] += 1

			fastest = self.stats["fastest_win_seconds"]
			if fastest is None or elapsed < float(fastest):
				self.stats["fastest_win_seconds"] = round(elapsed, 3)
		else:
			self.stats["current_streak"] = 0

		if mode == "survival":
			self.stats["highest_survival_level"] = max(
				self.stats["highest_survival_level"], int(result.get("level", 1))
			)

	def print_round_summary(self, result: dict[str, Any]) -> None:
		print("\n" + "=" * 64)
		if result["won"]:
			print("Round Result: WIN")
			print(f"Score earned: {result['score']}")
			print(f"Guesses used: {result['guesses']}")
			print(f"Hints used: {result['hints_used']}")
			print(f"Time: {self.format_duration(result['elapsed'])}")
		elif result["forfeit"]:
			print("Round Result: FORFEIT")
			print(f"Target was: {result['target']}")
		else:
			print("Round Result: LOSS")
			print(f"Target was: {result['target']}")
			print(f"Guesses made: {result['guesses']}")
			print(f"Hints used: {result['hints_used']}")
		print("=" * 64)

	def play_classic(self) -> None:
		difficulty = self.choose_difficulty()
		result = self.play_round(difficulty, mode="classic", level=1)
		self.update_stats(result)
		self.save_stats()
		self.print_round_summary(result)

	def play_survival(self) -> None:
		print("\nSurvival rules:")
		print("You play escalating levels. Each level raises range size and challenge.")
		print("A miss ends the run. You keep all points earned so far.")

		level = 1
		total_score = 0
		total_guesses = 0
		total_hints = 0
		start_run = time.time()

		while True:
			maximum = 20 + (level - 1) * 30
			attempts = 6 + min(4, level // 2)
			difficulty = Difficulty(
				name=f"Survival L{level}",
				minimum=1,
				maximum=maximum,
				attempts=attempts,
				multiplier=1.0 + level * 0.12,
			)

			result = self.play_round(difficulty, mode="survival", level=level)
			total_guesses += result["guesses"]
			total_hints += result["hints_used"]

			if result["won"]:
				level_bonus = 30 * level
				total_score += result["score"] + level_bonus
				print(
					f"Level {level} cleared. "
					f"Level bonus: {level_bonus}. Running score: {total_score}"
				)
				level += 1
				continue

			reached_level = level - 1
			elapsed = time.time() - start_run
			run_success = reached_level >= 1

			run_result = {
				"won": run_success,
				"forfeit": result["forfeit"],
				"target": result["target"],
				"guesses": total_guesses,
				"hints_used": total_hints,
				"attempts_left": 0,
				"elapsed": elapsed,
				"score": total_score,
				"mode": "survival",
				"level": max(1, reached_level),
			}

			self.update_stats(run_result)
			self.save_stats()

			print("\n" + "=" * 64)
			print("Survival Run Complete")
			print(f"Levels cleared: {reached_level}")
			print(f"Final score: {total_score}")
			print(f"Total guesses: {total_guesses}")
			print(f"Total hints used: {total_hints}")
			print(f"Run time: {self.format_duration(elapsed)}")
			if result["forfeit"]:
				print("Run ended by forfeit.")
			print("=" * 64)
			return

	def show_stats(self) -> None:
		games = self.stats["total_games"]
		wins = self.stats["total_wins"]
		win_rate = (wins / games * 100.0) if games else 0.0
		avg_score = (self.stats["total_score"] / games) if games else 0.0
		avg_guesses = (self.stats["total_guesses"] / games) if games else 0.0

		print("\n" + "=" * 64)
		print("Player Statistics")
		print(f"Games played: {games}")
		print(f"Wins: {wins} ({win_rate:.1f}%)")
		print(f"Best score: {self.stats['best_score']}")
		print(f"Average score per game: {avg_score:.1f}")
		print(f"Average guesses per game: {avg_guesses:.1f}")
		print(f"Current streak: {self.stats['current_streak']}")
		print(f"Longest streak: {self.stats['longest_streak']}")
		print(f"Classic record: {self.stats['classic_wins']} / {self.stats['classic_games']}")
		print(
			"Survival successful runs: "
			f"{self.stats['survival_successes']} / {self.stats['survival_games']}"
		)
		print(f"Highest survival level cleared: {self.stats['highest_survival_level']}")

		fastest = self.stats["fastest_win_seconds"]
		if fastest is not None:
			print(f"Fastest win: {self.format_duration(float(fastest))}")
		else:
			print("Fastest win: N/A")

		if self.stats["last_played"]:
			print(f"Last played: {self.stats['last_played']}")
		else:
			print("Last played: N/A")

		print("=" * 64)

	def reset_stats(self) -> None:
		confirmation = input("Type RESET to clear all stats: ").strip()
		if confirmation == "RESET":
			self.stats = DEFAULT_STATS.copy()
			self.save_stats()
			print("Stats reset successfully.")
		else:
			print("Reset cancelled.")

	def run(self) -> None:
		self.banner()

		while True:
			choice = self.show_menu()

			if choice == "1":
				self.play_classic()
			elif choice == "2":
				self.play_survival()
			elif choice == "3":
				self.show_stats()
			elif choice == "4":
				self.reset_stats()
			elif choice == "5":
				print("Thanks for playing. Goodbye.")
				break
