#!/usr/bin/env python3
"""
Amateur Radio CW Practice Bot

An interactive CW (Morse code) practice tool that uses Claude AI to simulate
realistic amateur radio conversations. The bot acts as a ham radio operator,
responding to your messages in Morse code audio.
"""

import sys
import yaml
from pathlib import Path
from typing import Optional
import signal

from morse_generator import MorseGenerator, PlaybackControl
from radio_operator import RadioOperator
from pynput import keyboard


class CWPracticeBot:
    """Main CW practice bot application."""

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize the CW practice bot.

        Args:
            config_path: Path to the configuration file
        """
        self.config = self._load_config(config_path)
        self.morse_generator: Optional[MorseGenerator] = None
        self.operator: Optional[RadioOperator] = None
        self.running = False
        self.keyboard_listener: Optional[keyboard.Listener] = None
        self.is_paused = False

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

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(sig, frame):
            # If we're playing CW, signal shutdown to stop playback
            if self.morse_generator:
                self.morse_generator.set_control_command(PlaybackControl.SHUTDOWN)
            print("\n\n73! (Exiting...)")
            self.running = False
            # Don't exit immediately, let cleanup happen
            # sys.exit(0) will be called after cleanup

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def _on_key_press(self, key) -> None:
        """
        Handle keyboard input during CW playback.

        Controls:
            spacebar: pause/resume
            '<': backup one word
            return: stop transmission and await input
            ctrl-c: end transmission and shutdown (handled by signal handler)
        """
        try:
            # Handle character keys
            if hasattr(key, 'char') and key.char is not None:
                if key.char == ' ':
                    # Toggle pause
                    self.is_paused = not self.is_paused
                    if self.is_paused:
                        self.morse_generator.set_control_command(PlaybackControl.PAUSE)
                        print("\n[Paused - press spacebar to resume]")
                    else:
                        self.morse_generator.set_control_command(PlaybackControl.CONTINUE)
                        print("[Resumed]")
                elif key.char == '<':
                    # Backup one word
                    self.morse_generator.set_control_command(PlaybackControl.BACKUP)
                    print("\n[Backing up one word...]")

            # Handle special keys
            if key == keyboard.Key.enter:
                # Stop transmission
                self.morse_generator.set_control_command(PlaybackControl.STOP)
                print("\n[Transmission stopped]")
        except AttributeError:
            pass

    def _start_keyboard_listener(self) -> None:
        """Start the keyboard listener for playback controls."""
        if self.keyboard_listener is None or not self.keyboard_listener.running:
            self.keyboard_listener = keyboard.Listener(on_press=self._on_key_press)
            self.keyboard_listener.start()

    def _stop_keyboard_listener(self) -> None:
        """Stop the keyboard listener."""
        if self.keyboard_listener is not None and self.keyboard_listener.running:
            self.keyboard_listener.stop()
            self.keyboard_listener = None

    def _print_header(self) -> None:
        """Print the welcome header."""
        print("=" * 70)
        print("Amateur Radio CW Practice Bot".center(70))
        print("=" * 70)
        print()
        print(f"Configuration:")
        print(f"  Speed: {self.config['morse']['wpm']} WPM")
        print(f"  Farnsworth: {self.config['morse']['farnsworth_wpm']} WPM")
        print(f"  Frequency: {self.config['morse']['frequency']} Hz")
        print(f"  AI Operator Callsign: {self.operator.get_callsign()}")
        print()
        print("Commands:")
        print("  Type your message and press Enter to transmit")
        print("  'quit' or 'exit' - End the session")
        print("  'new' - Start a new conversation with a new operator")
        print("  'callsign' - Show the current operator's callsign")
        print()
        print("Playback Controls (during CW transmission):")
        print("  Spacebar - Pause/Resume")
        print("  '<' - Backup one word")
        print("  Return - Stop transmission and await input")
        print("  Ctrl-C - End transmission and shutdown")
        print()
        print("Tip: Try starting with 'CQ CQ CQ DE <your callsign>' or just say hello!")
        print("=" * 70)
        print()

    def _send_message(self, message: str, is_first: bool = False) -> bool:
        """
        Send a message and get a response.

        Args:
            message: The user's message
            is_first: Whether this is the first message

        Returns:
            True if should continue, False if should shutdown
        """
        # Get AI response
        print(f"\n[{self.operator.get_callsign()}]: ", end='', flush=True)
        response = self.operator.get_response(message, is_first_message=is_first)
        print(response)

        # Reset pause state
        self.is_paused = False

        # Play the response in Morse code with controls
        print("\n[Playing CW... (spacebar=pause, <=backup, return=stop, ctrl-c=shutdown)]")
        self._start_keyboard_listener()

        result = self.morse_generator.play_with_controls(response)

        # Handle the result
        if result == PlaybackControl.SHUTDOWN:
            print("\n[Shutdown requested]")
            return False
        elif result == PlaybackControl.STOP:
            print("[CW transmission stopped]\n")
        else:
            print("[CW transmission complete]\n")

        return True

    def run(self) -> None:
        """Run the main bot loop."""
        self._setup_signal_handlers()

        # Initialize components
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

        self._print_header()
        self.running = True
        is_first_message = True

        try:
            while self.running:
                try:
                    # Get user input
                    user_input = input("You: ").strip()

                    if not user_input:
                        continue

                    # Handle commands
                    command = user_input.lower()

                    if command in ('quit', 'exit', 'q'):
                        print("\n73 de {}! Hope to catch you again soon!".format(
                            self.operator.get_callsign()
                        ))
                        break

                    elif command == 'new':
                        print("\n[Starting new conversation...]")
                        self.operator.reset_conversation()
                        is_first_message = True
                        print(f"[New operator callsign: {self.operator.get_callsign()}]\n")
                        continue

                    elif command == 'callsign':
                        print(f"\n[Current operator: {self.operator.get_callsign()}]\n")
                        continue

                    # Send message and get response
                    should_continue = self._send_message(user_input, is_first=is_first_message)
                    if not should_continue:
                        break
                    is_first_message = False

                except EOFError:
                    break
                except Exception as e:
                    print(f"\n[Error: {e}]")
                    print("Please try again.\n")

        finally:
            # Cleanup
            self._stop_keyboard_listener()
            if self.morse_generator:
                self.morse_generator.close()

            # Exit if running was set to False
            if not self.running:
                sys.exit(0)


def main():
    """Main entry point."""
    config_file = "config.yaml"

    # Allow custom config file as command line argument
    if len(sys.argv) > 1:
        config_file = sys.argv[1]

    try:
        bot = CWPracticeBot(config_file)
        bot.run()
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyError as e:
        print(f"Error: Missing configuration key: {e}", file=sys.stderr)
        print("Please check your config.yaml file.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
