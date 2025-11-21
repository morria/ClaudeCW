#!/usr/bin/env python3
"""
Curses-based chat interface for the CW Practice Bot.
Features a Slack-like interface with bot messages hidden by block characters.
Integrated with Morse code audio playback.
"""

import curses
import textwrap
import yaml
import threading
import time
from typing import List, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path

from morse_generator import MorseGenerator, PlaybackControl
from radio_operator import RadioOperator


@dataclass
class Message:
    """Represents a single chat message."""
    sender: str
    text: str
    is_bot: bool


class CursesChatInterface:
    """A curses-based chat interface similar to Slack with CW audio playback."""

    BLOCK_CHAR = '█'

    def __init__(self, stdscr, config_path: str = "config.yaml"):
        """
        Initialize the curses chat interface.

        Args:
            stdscr: The curses standard screen object
            config_path: Path to the configuration file
        """
        self.stdscr = stdscr
        self.messages: List[Message] = []
        self.input_buffer = ""
        self.cursor_pos = 0
        self.show_bot_messages = False  # Start with bot messages hidden
        self.scroll_offset = 0
        self.running = True

        # Load configuration
        self.config = self._load_config(config_path)

        # Initialize Morse generator and AI operator
        self.morse_generator: Optional[MorseGenerator] = None
        self.operator: Optional[RadioOperator] = None
        self.is_first_message = True
        self.morse_playing = False
        self.morse_paused = False
        self.playback_thread: Optional[threading.Thread] = None

        # Initialize colors
        curses.start_color()
        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)    # User messages
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)   # Bot messages
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # Input line
        curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_BLUE)    # Status bar

        # Configure curses
        curses.curs_set(1)  # Show cursor
        self.stdscr.keypad(True)
        self.stdscr.nodelay(False)  # Blocking mode for getch

        # Setup components
        self._setup_components()
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

        welcome = "═" * 70
        title = "Amateur Radio CW Practice Bot - Curses Interface".center(70)
        help_text = f"""{welcome}
{title}
{welcome}

Configuration: {self.config['morse']['wpm']} WPM | Operator: {callsign}

Commands:
  'new' - Start new conversation with new operator
  'callsign' - Show current operator's callsign
  'quit' or ESC - Exit

Controls:
  TAB - Toggle bot message visibility
  Ctrl-P - Pause/Resume CW playback
  Ctrl-B - Pause 1s and go back one word
  Arrow Keys - Scroll chat history

Tip: Try 'CQ CQ CQ DE <your callsign>' or just say hello!
{welcome}"""

        self.add_message("SYSTEM", help_text, is_bot=False)

    def add_message(self, sender: str, text: str, is_bot: bool = False):
        """
        Add a message to the chat log.

        Args:
            sender: The sender's name/callsign
            text: The message text
            is_bot: Whether this is a bot message
        """
        self.messages.append(Message(sender=sender, text=text, is_bot=is_bot))
        # Auto-scroll to bottom when new message arrives
        self.scroll_offset = 0

        # Play CW for bot messages (but not SYSTEM messages)
        if is_bot and sender != "SYSTEM" and self.morse_generator:
            self._play_morse_async(text)

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

    def _backup_word(self):
        """Pause for 1 second and go back one word."""
        if not self.morse_playing:
            return

        # Backup one word
        self.morse_generator.set_control_command(PlaybackControl.BACKUP)
        # Pause for 1 second
        self.morse_generator.set_control_command(PlaybackControl.PAUSE)
        self.morse_paused = True

        # Resume after 1 second (in a background thread so we don't block UI)
        def resume_after_delay():
            time.sleep(1.0)
            if self.morse_paused:
                self.morse_generator.set_control_command(PlaybackControl.CONTINUE)
                self.morse_paused = False

        threading.Thread(target=resume_after_delay, daemon=True).start()

    def _get_display_lines(self) -> List[Tuple[str, int]]:
        """
        Get the formatted display lines with color pairs.

        Returns:
            List of (line_text, color_pair) tuples
        """
        height, width = self.stdscr.getmaxyx()
        chat_height = height - 2  # Reserve 2 lines for input and separator

        lines = []

        for msg in self.messages:
            # Format sender
            sender_line = f"[{msg.sender}]"
            color = 2 if msg.is_bot else 1
            lines.append((sender_line, color))

            # Format message text
            if msg.is_bot and not self.show_bot_messages:
                # Replace text with block characters, preserving length and spaces
                display_text = ''.join(
                    ' ' if c == ' ' or c == '\n' else self.BLOCK_CHAR
                    for c in msg.text
                )
            else:
                display_text = msg.text

            # Wrap text to fit width
            wrapped = textwrap.wrap(display_text, width - 2) or ['']
            for line in wrapped:
                lines.append((f"  {line}", color))

            # Add blank line between messages
            lines.append(("", 0))

        return lines

    def _draw_chat_area(self):
        """Draw the chat message area."""
        height, width = self.stdscr.getmaxyx()
        chat_height = height - 2

        # Get all display lines
        all_lines = self._get_display_lines()

        # Calculate which lines to show based on scroll offset
        total_lines = len(all_lines)
        start_idx = max(0, total_lines - chat_height - self.scroll_offset)
        end_idx = total_lines - self.scroll_offset
        visible_lines = all_lines[start_idx:end_idx]

        # Draw lines from bottom up
        y = chat_height - 1
        for line_text, color_pair in reversed(visible_lines):
            if y < 0:
                break
            self.stdscr.move(y, 0)
            self.stdscr.clrtoeol()
            if color_pair > 0:
                self.stdscr.addstr(y, 0, line_text[:width-1], curses.color_pair(color_pair))
            else:
                self.stdscr.addstr(y, 0, line_text[:width-1])
            y -= 1

        # Clear any remaining lines at top
        while y >= 0:
            self.stdscr.move(y, 0)
            self.stdscr.clrtoeol()
            y -= 1

    def _draw_separator(self):
        """Draw separator line between chat and input."""
        height, width = self.stdscr.getmaxyx()
        sep_y = height - 2
        separator = "─" * (width - 1)
        self.stdscr.addstr(sep_y, 0, separator, curses.color_pair(4))

    def _draw_input_line(self):
        """Draw the input line at the bottom."""
        height, width = self.stdscr.getmaxyx()
        input_y = height - 1

        # Clear the line
        self.stdscr.move(input_y, 0)
        self.stdscr.clrtoeol()

        # Draw prompt
        prompt = "You: "
        self.stdscr.addstr(input_y, 0, prompt, curses.color_pair(3))

        # Draw input buffer
        display_text = self.input_buffer
        max_input_width = width - len(prompt) - 1

        # Handle text scrolling if input is too long
        if len(display_text) > max_input_width:
            # Show the end of the input that includes cursor
            start = max(0, self.cursor_pos - max_input_width + 1)
            display_text = display_text[start:start + max_input_width]
            display_cursor_pos = min(self.cursor_pos - start, max_input_width - 1)
        else:
            display_cursor_pos = self.cursor_pos

        self.stdscr.addstr(input_y, len(prompt), display_text)

        # Position cursor
        self.stdscr.move(input_y, len(prompt) + display_cursor_pos)

    def _draw_status(self):
        """Draw status information."""
        height, width = self.stdscr.getmaxyx()
        status_y = height - 2

        # Build status string
        status_parts = []
        status_parts.append(f"TAB: {'Hide' if self.show_bot_messages else 'Show'} bot text")

        if self.morse_playing:
            if self.morse_paused:
                status_parts.append("CW: PAUSED")
            else:
                status_parts.append("CW: Playing")

        status = " | ".join(status_parts) + " "
        status_x = max(0, width - len(status) - 1)

        try:
            self.stdscr.addstr(status_y, status_x, status, curses.color_pair(4))
        except curses.error:
            pass  # Ignore if status doesn't fit

    def refresh_display(self):
        """Refresh the entire display."""
        self.stdscr.clear()
        self._draw_chat_area()
        self._draw_separator()
        self._draw_status()
        self._draw_input_line()
        self.stdscr.refresh()

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
            self.add_message("SYSTEM", farewell, is_bot=False)
            return True

        elif cmd == 'new':
            self.operator.reset_conversation()
            self.is_first_message = True
            new_callsign = self.operator.get_callsign()
            self.add_message("SYSTEM",
                f"New conversation started. New operator: {new_callsign}", is_bot=False)
            return False

        elif cmd == 'callsign':
            current_callsign = self.operator.get_callsign()
            self.add_message("SYSTEM",
                f"Current operator: {current_callsign}", is_bot=False)
            return False

        return False

    def _send_message(self, message: str):
        """
        Send a message and get a response.

        Args:
            message: The user's message
        """
        try:
            # Get AI response
            response = self.operator.get_response(message, is_first_message=self.is_first_message)
            self.is_first_message = False

            # Add bot response to chat (this will trigger CW playback)
            callsign = self.operator.get_callsign()
            self.add_message(callsign, response, is_bot=True)

        except Exception as e:
            self.add_message("ERROR", f"Failed to get response: {str(e)}", is_bot=False)

    def handle_input(self, key) -> str:
        """
        Handle keyboard input.

        Args:
            key: The key code from curses

        Returns:
            The entered message if Enter was pressed, empty string otherwise
        """
        height, width = self.stdscr.getmaxyx()
        max_input_width = width - len("You: ") - 1

        # Ctrl-P (16) - Pause/Resume
        if key == 16:
            self._toggle_pause()
            return ""

        # Ctrl-B (2) - Backup word
        if key == 2:
            self._backup_word()
            return ""

        if key == ord('\n'):  # Enter key
            message = self.input_buffer
            self.input_buffer = ""
            self.cursor_pos = 0
            return message

        elif key == ord('\t'):  # Tab key - toggle visibility
            self.show_bot_messages = not self.show_bot_messages
            return ""

        elif key == curses.KEY_BACKSPACE or key == 127 or key == 8:  # Backspace
            if self.cursor_pos > 0:
                self.input_buffer = (
                    self.input_buffer[:self.cursor_pos-1] +
                    self.input_buffer[self.cursor_pos:]
                )
                self.cursor_pos -= 1
            return ""

        elif key == curses.KEY_DC:  # Delete key
            if self.cursor_pos < len(self.input_buffer):
                self.input_buffer = (
                    self.input_buffer[:self.cursor_pos] +
                    self.input_buffer[self.cursor_pos+1:]
                )
            return ""

        elif key == curses.KEY_LEFT:  # Left arrow
            if self.cursor_pos > 0:
                self.cursor_pos -= 1
            return ""

        elif key == curses.KEY_RIGHT:  # Right arrow
            if self.cursor_pos < len(self.input_buffer):
                self.cursor_pos += 1
            return ""

        elif key == curses.KEY_HOME:  # Home key
            self.cursor_pos = 0
            return ""

        elif key == curses.KEY_END:  # End key
            self.cursor_pos = len(self.input_buffer)
            return ""

        elif key == curses.KEY_UP:  # Scroll up
            self.scroll_offset += 1
            return ""

        elif key == curses.KEY_DOWN:  # Scroll down
            if self.scroll_offset > 0:
                self.scroll_offset -= 1
            return ""

        elif key == curses.KEY_PPAGE:  # Page up
            height, _ = self.stdscr.getmaxyx()
            self.scroll_offset += height - 3
            return ""

        elif key == curses.KEY_NPAGE:  # Page down
            height, _ = self.stdscr.getmaxyx()
            self.scroll_offset = max(0, self.scroll_offset - (height - 3))
            return ""

        elif 32 <= key <= 126:  # Printable characters
            self.input_buffer = (
                self.input_buffer[:self.cursor_pos] +
                chr(key) +
                self.input_buffer[self.cursor_pos:]
            )
            self.cursor_pos += 1
            return ""

        return ""

    def run(self):
        """Run the main application loop."""
        while self.running:
            self.refresh_display()

            try:
                key = self.stdscr.getch()

                # ESC key to quit
                if key == 27:
                    break

                # Ctrl-C (3) to quit
                if key == 3:
                    break

                # Handle input
                message = self.handle_input(key)

                if message:
                    # Check if it's a command
                    if self._handle_command(message):
                        break

                    # Add user message to chat
                    self.add_message("You", message, is_bot=False)

                    # Send message and get response
                    self._send_message(message)

            except KeyboardInterrupt:
                break

        # Cleanup
        if self.morse_generator:
            self.morse_generator.close()


def main(stdscr):
    """Main function for curses application."""
    import sys

    config_file = "config.yaml"

    # Allow custom config file as command line argument
    if len(sys.argv) > 1:
        config_file = sys.argv[1]

    try:
        interface = CursesChatInterface(stdscr, config_file)
        interface.run()
    except FileNotFoundError as e:
        # Can't use print in curses mode, so we need to handle this differently
        stdscr.clear()
        stdscr.addstr(0, 0, f"Error: {e}")
        stdscr.addstr(1, 0, "Press any key to exit...")
        stdscr.refresh()
        stdscr.getch()
    except KeyError as e:
        stdscr.clear()
        stdscr.addstr(0, 0, f"Error: Missing configuration key: {e}")
        stdscr.addstr(1, 0, "Please check your config.yaml file.")
        stdscr.addstr(2, 0, "Press any key to exit...")
        stdscr.refresh()
        stdscr.getch()
    except Exception as e:
        stdscr.clear()
        stdscr.addstr(0, 0, f"Error: {e}")
        stdscr.addstr(1, 0, "Press any key to exit...")
        stdscr.refresh()
        stdscr.getch()


if __name__ == "__main__":
    import curses
    curses.wrapper(main)
