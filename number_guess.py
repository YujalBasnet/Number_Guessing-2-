import argparse

from game_core import NumberGuessGame
from number_guess_gui import launch_gui
from web_app import launch_web


def main() -> None:
    parser = argparse.ArgumentParser(description="Number Guessing Game")
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Launch the desktop GUI version.",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Launch the browser website version.",
    )
    args = parser.parse_args()

    if args.gui:
        launch_gui()
        return

    if args.web:
        launch_web(debug=True)
        return

    game = NumberGuessGame()
    game.run()


if __name__ == "__main__":
    main()
