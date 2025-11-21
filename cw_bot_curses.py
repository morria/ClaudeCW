#!/usr/bin/env python3
"""
Curses-based Amateur Radio CW Practice Bot.
Integrates the CW bot with a Slack-like curses interface.
"""

import sys
import yaml
import curses
import threading
from pathlib import Path
from typing import Optional

from morse_generator import MorseGenerator, PlaybackControl
from radio_operator import RadioOperator
from curses_chat import CursesChatInterface


class CWBotCursesInterface:
    """Curses-based CW Practice Bot with integrated chat interface."""

    def __init__(self, stdscr, config_path: str = "config.yaml"):
        """
        Initialize the curses CW bot.

        Args:
            stdscr: The curses standard screen object
            config_path: Path to the configuration file
        """
        self.stdscr = stdscr
        self.config = self._load_config(config_path)
        self.chat_interface = CursesChatInterface(stdscr)
        self.morse_generator: Optional[MorseGenerator] = None
        self.operator: Optional[RadioOperator] = None
        self.is_first_message = True
        self.morse_playing = False
        self.morse_paused = False
        self.playback_thread: Optional[threading.Thread] = None

        # Initialize components
        self._setup_components()

        # Add welcome message
        self._show_welcome()

    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file."""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {config_path}\n"
                "Please create config.yaml with your settings."
            )

        with path.open('r') as f:
            return yaml.safe_load(f)

    def _setup_components(self):
        """Initialize the Morse generator and AI operator."""
        morse_config = self.config['morse']
        audio_config = self.config['audio']

        self.morse_generator = MorseGenerator(
            wpm=morse_config['wpm'],
            farnsworth_wpm=morse_config['farnsworth_wpm'],
            frequency=morse_config['frequency'],
            sample_rate=audio_config['sample_rate'],
            volume=audio_config['volume']
        )

        self.operator = RadioOperator(
            api_key=self.config['claude']['api_key']
        )

    def _show_welcome(self):
        """Show welcome message and instructions."""
        callsign = self.operator.get_callsign()

        welcome = f"""╔════════════════════════════════════════════════════════════════════╗
║          Amateur Radio CW Practice Bot - Curses Interface         ║
╚════════════════════════════════════════════════════════════════════╝"""

        self.chat_interface.add_message("SYSTEM", welcome, is_bot=False)
        self.chat_interface.add_message("SYSTEM",
            f"Configuration: {self.config['morse']['wpm']} WPM | "
            f"Operator: {callsign}", is_bot=False)
        self.chat_interface.add_message("SYSTEM",
            "Commands: 'new' = new operator | 'callsign' = show callsign | "
            "'quit' or ESC = exit", is_bot=False)
        self.chat_interface.add_message("SYSTEM",
            "Press TAB to toggle bot message visibility | Arrow keys to scroll | "
            "SPACE to pause/resume | Ctrl-C to quit", is_bot=False)
        self.chat_interface.add_message("SYSTEM",
            "Tip: Try 'CQ CQ CQ DE <your callsign>' or just say hello!",
            is_bot=False)

    def _play_morse_async(self, text: str):
        """Play Morse code in a background thread with pause/resume support."""
        def play():
            self.morse_playing = True
            self.morse_paused = False
            try:
                self.morse_generator.play_with_controls(text)
            finally:
                self.morse_playing = False
                self.morse_paused = False

        self.playback_thread = threading.Thread(target=play, daemon=True)
        self.playback_thread.start()

    def _toggle_pause(self):
        """Toggle pause/resume of Morse playback."""
        if not self.morse_playing:
            return

        if self.morse_paused:
            # Resume
            self.morse_generator.set_control_command(PlaybackControl.CONTINUE)
            self.morse_paused = False
        else:
            # Pause
            self.morse_generator.set_control_command(PlaybackControl.PAUSE)
            self.morse_paused = True

    def _handle_command(self, command: str) -> bool:
        """
        Handle special commands.

        Args:
            command: The command to handle

        Returns:
            True if should quit, False otherwise
        """
        cmd = command.lower().strip()

        if cmd in ('quit', 'exit', 'q'):
            farewell = f"73 de {self.operator.get_callsign()}! Hope to catch you again soon!"
            self.chat_interface.add_message("SYSTEM", farewell, is_bot=False)
            return True

        elif cmd == 'new':
            self.operator.reset_conversation()
            self.is_first_message = True
            new_callsign = self.operator.get_callsign()
            self.chat_interface.add_message("SYSTEM",
                f"New conversation started. New operator: {new_callsign}", is_bot=False)
            return False

        elif cmd == 'callsign':
            current_callsign = self.operator.get_callsign()
            self.chat_interface.add_message("SYSTEM",
                f"Current operator: {current_callsign}", is_bot=False)
            return False

        return False

    def _send_message(self, message: str):
        """
        Send a message and get a response.

        Args:
            message: The user's message
        """
        # Get AI response
        response = self.operator.get_response(message, is_first_message=self.is_first_message)
        self.is_first_message = False

        # Add bot response to chat
        callsign = self.operator.get_callsign()
        self.chat_interface.add_message(callsign, response, is_bot=True)

        # Play Morse code asynchronously
        self._play_morse_async(response)

    def run(self):
        """Run the main bot loop."""
        while self.chat_interface.running:
            self.chat_interface.refresh_display()

            try:
                key = self.stdscr.getch()

                # ESC key to quit
                if key == 27:
                    break

                # Ctrl-C to quit
                if key == 3:  # Ctrl-C
                    break

                # Spacebar to pause/resume
                if key == ord(' '):
                    self._toggle_pause()
                    continue

                # Handle input
                message = self.chat_interface.handle_input(key)

                if message:
                    # Check if it's a command
                    if self._handle_command(message):
                        break

                    # Add user message to chat
                    self.chat_interface.add_message("You", message, is_bot=False)

                    # Send message and get response
                    try:
                        self._send_message(message)
                    except Exception as e:
                        self.chat_interface.add_message("ERROR", str(e), is_bot=False)

            except KeyboardInterrupt:
                break

        # Cleanup
        if self.morse_generator:
            self.morse_generator.close()


def main(stdscr):
    """Main entry point for curses application."""
    config_file = "config.yaml"

    # Allow custom config file as command line argument
    if len(sys.argv) > 1:
        config_file = sys.argv[1]

    try:
        bot = CWBotCursesInterface(stdscr, config_file)
        bot.run()
    except FileNotFoundError as e:
        # Can't use print in curses mode, so we need to handle this differently
        stdscr.addstr(0, 0, f"Error: {e}")
        stdscr.addstr(1, 0, "Press any key to exit...")
        stdscr.refresh()
        stdscr.getch()
    except KeyError as e:
        stdscr.addstr(0, 0, f"Error: Missing configuration key: {e}")
        stdscr.addstr(1, 0, "Please check your config.yaml file.")
        stdscr.addstr(2, 0, "Press any key to exit...")
        stdscr.refresh()
        stdscr.getch()
    except Exception as e:
        stdscr.addstr(0, 0, f"Error: {e}")
        stdscr.addstr(1, 0, "Press any key to exit...")
        stdscr.refresh()
        stdscr.getch()


if __name__ == "__main__":
    curses.wrapper(main)
