# Number Guessing Game

A feature-rich number guessing game written in Python with CLI, desktop GUI, and website modes.

## Features

- Multiple modes:
  - Classic mode with Easy, Medium, Hard, Insane, and Custom difficulty
  - Survival mode with escalating levels
- Rich feedback system:
  - Too high or too low guidance
  - Temperature clues (cold, cool, warm, hot)
  - Warmer or colder trend against previous guess
  - Periodic range pulse narrowing
- Hint engine (up to 2 hints per round):
  - Parity
  - Prime or non-prime
  - Half-range and quartile clues
  - Divisibility clues
- Scoring system based on:
  - Range complexity
  - Attempts left
  - Guess efficiency
  - Time taken
  - Hint penalties
- Persistent player stats saved in stats.json:
  - Win rate, streaks, best score, fastest win
  - Mode records
  - Highest survival level

## Requirements

- Python 3.10 or later
- Flask (for website mode)

Install dependencies:

pip install -r requirements.txt

## Run

From this folder, run:

CLI version:

python number_guess.py

Desktop GUI version:

python number_guess.py --gui

Or directly:

python number_guess_gui.py

Website version:

python number_guess.py --web

Or directly:

python web_app.py

Then open this in your browser:

http://127.0.0.1:5000

## Controls During a Round

- Enter a number to guess
- Type hint to get a clue
- Type quit to forfeit the current round

## Files

- number_guess.py: main entry point (run this file)
- game_core.py: gameplay engine and menu flow
- game_config.py: shared models, difficulty presets, and stats defaults
- number_guess_gui.py: Tkinter desktop GUI (Classic + Survival + Stats)
- web_app.py: Flask website backend and gameplay routes
- templates/: website pages (game + stats)
- static/styles.css: website styling
- requirements.txt: Python package dependencies
- stats.json: auto-generated stats file after first run
