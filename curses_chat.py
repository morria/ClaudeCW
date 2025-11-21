#!/usr/bin/env python3
"""
Curses-based chat interface for the CW Practice Bot.
Features a Slack-like interface with bot messages hidden by block characters.
"""

import curses
import textwrap
from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class Message:
    """Represents a single chat message."""
    sender: str
    text: str
    is_bot: bool


class CursesChatInterface:
    """A curses-based chat interface similar to Slack."""

    BLOCK_CHAR = '█'

    def __init__(self, stdscr):
        """
        Initialize the curses chat interface.

        Args:
            stdscr: The curses standard screen object
        """
        self.stdscr = stdscr
        self.messages: List[Message] = []
        self.input_buffer = ""
        self.cursor_pos = 0
        self.show_bot_messages = False  # Start with bot messages hidden
        self.scroll_offset = 0
        self.running = True

        # Initialize colors
        curses.start_color()
        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)    # User messages
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)   # Bot messages
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # Input line
        curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_BLUE)    # Status bar

        # Configure curses
        curses.curs_set(1)  # Show cursor
        self.stdscr.keypad(True)

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

        # Show toggle status on the right side of separator
        status = f" TAB: {'Hide' if self.show_bot_messages else 'Show'} bot text "
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

    def run_test(self):
        """Run a simple test of the interface."""
        # Add some test messages
        self.add_message("W1ABC", "CQ CQ CQ DE W1ABC K", is_bot=False)
        self.add_message("K2XYZ", "W1ABC DE K2XYZ GM UR RST 599 QTH BOSTON MA NAME JOHN K", is_bot=True)
        self.add_message("W1ABC", "K2XYZ DE W1ABC TNX FB RST 599 HR QTH SEATTLE WA NAME ALICE K", is_bot=False)
        self.add_message("K2XYZ", "ALICE FB WX HR SUNNY 73 DE K2XYZ SK", is_bot=True)

        # Main loop
        while self.running:
            self.refresh_display()

            try:
                key = self.stdscr.getch()

                # Check for quit command
                if key == 27:  # ESC key
                    break

                message = self.handle_input(key)

                if message:
                    # Add user message
                    self.add_message("You", message, is_bot=False)

                    # Add mock bot response
                    if message.lower() in ('quit', 'exit'):
                        self.add_message("Bot", "73! SK", is_bot=True)
                        break
                    else:
                        self.add_message("Bot", f"TNX FOR MSG: {message.upper()} K", is_bot=True)

            except KeyboardInterrupt:
                break


def main(stdscr):
    """Main function for curses application."""
    interface = CursesChatInterface(stdscr)
    interface.run_test()


if __name__ == "__main__":
    curses.wrapper(main)
