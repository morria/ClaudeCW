"""
Amateur Radio CW Practice Bot

An interactive Morse code (CW) practice tool that uses Claude AI to simulate
realistic amateur radio conversations.
"""

__version__ = "1.0.0"

from .morse_generator import MorseGenerator, PlaybackControl
from .radio_operator import RadioOperator
from .curses_chat import CursesChatInterface

__all__ = [
    "MorseGenerator",
    "PlaybackControl",
    "RadioOperator",
    "CursesChatInterface",
]
