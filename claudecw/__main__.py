#!/usr/bin/env python3
"""
Main entry point for the ClaudeCW application.
"""

import curses
from .curses_chat import main


def cli_main():
    """CLI entry point wrapper for setup.py console_scripts."""
    curses.wrapper(main)


if __name__ == "__main__":
    cli_main()
