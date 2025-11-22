"""
Morse code audio generation module.
Generates CW (Continuous Wave) audio signals from text.
"""

import numpy as np
from typing import Optional, List, Tuple
import pyaudio
import threading
from enum import Enum


class PlaybackControl(Enum):
    """Playback control commands."""
    CONTINUE = 0
    PAUSE = 1
    STOP = 2
    BACKUP = 3
    SHUTDOWN = 4


class MorseGenerator:
    """Generate and play Morse code audio signals."""

    # International Morse Code mappings
    MORSE_CODE = {
        'A': '.-',    'B': '-...',  'C': '-.-.',  'D': '-..',   'E': '.',
        'F': '..-.',  'G': '--.',   'H': '....',  'I': '..',    'J': '.---',
        'K': '-.-',   'L': '.-..',  'M': '--',    'N': '-.',    'O': '---',
        'P': '.--.',  'Q': '--.-',  'R': '.-.',   'S': '...',   'T': '-',
        'U': '..-',   'V': '...-',  'W': '.--',   'X': '-..-',  'Y': '-.--',
        'Z': '--..',
        '0': '-----', '1': '.----', '2': '..---', '3': '...--', '4': '....-',
        '5': '.....', '6': '-....', '7': '--...', '8': '---..', '9': '----.',
        '.': '.-.-.-', ',': '--..--', '?': '..--..', '/': '-..-.',
        '-': '-....-', '=': '-...-',  '+': '.-.-.', '@': '.--.-.',
        ' ': ' ',
    }

    def __init__(self, wpm: int = 20, farnsworth_wpm: Optional[int] = None,
                 frequency: int = 700, sample_rate: int = 44100, volume: float = 0.3):
        """
        Initialize the Morse code generator.

        Args:
            wpm: Words per minute (character speed)
            farnsworth_wpm: Effective WPM (lower means more spacing between chars/words)
            frequency: Audio tone frequency in Hz
            sample_rate: Audio sample rate
            volume: Audio volume (0.0 to 1.0)
        """
        self.wpm = wpm
        self.farnsworth_wpm = farnsworth_wpm or wpm
        self.frequency = frequency
        self.sample_rate = sample_rate
        self.volume = volume

        # Calculate timing units in seconds
        # Standard: PARIS is 50 dit units, so 1 word = 50 units
        # At N WPM: 50N units per minute = 50N/60 units per second
        # Therefore 1 dit = 60/(50*WPM) = 1.2/WPM seconds
        self.dit_duration = 1.2 / self.wpm
        self.dah_duration = 3 * self.dit_duration

        # For Farnsworth timing, character speed stays at wpm,
        # but word spacing uses farnsworth_wpm
        self.char_space_duration = 3 * (1.2 / self.farnsworth_wpm)
        self.word_space_duration = 7 * (1.2 / self.farnsworth_wpm)

        # Initialize PyAudio
        self.audio = pyaudio.PyAudio()
        self.stream = None

        # Keyboard control state
        self.control_command = PlaybackControl.CONTINUE
        self.control_lock = threading.Lock()

        # Interrupt flag for backwards compatibility
        self.interrupted = False

    def _generate_tone(self, duration: float) -> np.ndarray:
        """Generate a sine wave tone."""
        samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, samples, False)

        # Generate sine wave
        wave = np.sin(2 * np.pi * self.frequency * t)

        # Apply envelope to reduce clicking (5ms rise/fall)
        envelope_samples = int(self.sample_rate * 0.005)
        if samples > 2 * envelope_samples:
            # Rise
            wave[:envelope_samples] *= np.linspace(0, 1, envelope_samples)
            # Fall
            wave[-envelope_samples:] *= np.linspace(1, 0, envelope_samples)

        return (wave * self.volume * 32767).astype(np.int16)

    def _generate_silence(self, duration: float) -> np.ndarray:
        """Generate silence."""
        samples = int(self.sample_rate * duration)
        return np.zeros(samples, dtype=np.int16)

    def text_to_morse(self, text: str) -> str:
        """Convert text to Morse code representation."""
        morse = []
        for char in text.upper():
            if char in self.MORSE_CODE:
                morse.append(self.MORSE_CODE[char])
            elif char == ' ':
                morse.append(' ')
        return ' '.join(morse)

    def generate_audio(self, text: str) -> np.ndarray:
        """Generate audio data for the given text."""
        audio_data = []
        morse_text = text.upper()

        previous_was_space = False
        for i, char in enumerate(morse_text):
            if char not in self.MORSE_CODE:
                continue

            if char == ' ':
                # Word space (we already have char space, so add remaining)
                if not previous_was_space:
                    audio_data.append(self._generate_silence(
                        self.word_space_duration - self.char_space_duration
                    ))
                    previous_was_space = True
                continue

            previous_was_space = False
            morse = self.MORSE_CODE[char]

            # Generate the character
            for j, symbol in enumerate(morse):
                if symbol == '.':
                    audio_data.append(self._generate_tone(self.dit_duration))
                elif symbol == '-':
                    audio_data.append(self._generate_tone(self.dah_duration))

                # Add inter-element space (between dits/dahs)
                if j < len(morse) - 1:
                    audio_data.append(self._generate_silence(self.dit_duration))

            # Add inter-character space (if not last character and next isn't space)
            if i < len(morse_text) - 1 and morse_text[i + 1] != ' ':
                audio_data.append(self._generate_silence(self.char_space_duration))

        return np.concatenate(audio_data) if audio_data else np.array([], dtype=np.int16)

    def play(self, text: str) -> None:
        """Generate and play Morse code for the given text."""
        if not text.strip():
            return

        # Reset interrupt flag
        self.interrupted = False

        audio_data = self.generate_audio(text)

        if len(audio_data) == 0:
            return

        # Open stream if not already open
        if self.stream is None:
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                output=True
            )

        # Play the audio in chunks to allow interruption
        chunk_size = self.sample_rate // 4  # 0.25 second chunks
        audio_bytes = audio_data.tobytes()
        bytes_per_sample = 2  # paInt16 = 2 bytes per sample
        chunk_bytes = chunk_size * bytes_per_sample

        for i in range(0, len(audio_bytes), chunk_bytes):
            if self.interrupted:
                break
            chunk = audio_bytes[i:i + chunk_bytes]
            self.stream.write(chunk)

    def stop(self) -> None:
        """Stop the current playback."""
        self.interrupted = True
        self.set_control_command(PlaybackControl.STOP)

    def _generate_word_audio(self, word: str, add_word_space: bool = True) -> np.ndarray:
        """
        Generate audio for a single word.

        Args:
            word: The word to generate audio for
            add_word_space: Whether to add word spacing after the word

        Returns:
            Audio data as numpy array
        """
        audio_data = []

        for i, char in enumerate(word.upper()):
            if char not in self.MORSE_CODE or char == ' ':
                continue

            morse = self.MORSE_CODE[char]

            # Generate the character
            for j, symbol in enumerate(morse):
                if symbol == '.':
                    audio_data.append(self._generate_tone(self.dit_duration))
                elif symbol == '-':
                    audio_data.append(self._generate_tone(self.dah_duration))

                # Add inter-element space (between dits/dahs)
                if j < len(morse) - 1:
                    audio_data.append(self._generate_silence(self.dit_duration))

            # Add inter-character space (if not last character)
            if i < len(word) - 1:
                audio_data.append(self._generate_silence(self.char_space_duration))

        # Add word space at the end if requested
        if add_word_space and audio_data:
            audio_data.append(self._generate_silence(self.word_space_duration))

        return np.concatenate(audio_data) if audio_data else np.array([], dtype=np.int16)

    def _split_into_words(self, text: str) -> List[str]:
        """Split text into words, preserving spaces as separate elements."""
        words = []
        current_word = []

        for char in text:
            if char == ' ':
                if current_word:
                    words.append(''.join(current_word))
                    current_word = []
            else:
                current_word.append(char)

        # Add the last word if any
        if current_word:
            words.append(''.join(current_word))

        return words

    def set_control_command(self, command: PlaybackControl) -> None:
        """Set the control command for playback."""
        with self.control_lock:
            self.control_command = command

    def get_control_command(self) -> PlaybackControl:
        """Get the current control command."""
        with self.control_lock:
            return self.control_command

    def play_with_controls(self, text: str, on_control: Optional[callable] = None) -> PlaybackControl:
        """
        Play Morse code with support for keyboard controls.

        Args:
            text: The text to play
            on_control: Optional callback for control events

        Returns:
            The final control command that stopped playback
        """
        if not text.strip():
            return PlaybackControl.CONTINUE

        # Reset control state
        self.set_control_command(PlaybackControl.CONTINUE)

        # Split text into words
        words = self._split_into_words(text)
        if not words:
            return PlaybackControl.CONTINUE

        # Open stream if not already open
        if self.stream is None:
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                output=True
            )

        word_index = 0

        while word_index < len(words):
            # Check control command
            cmd = self.get_control_command()

            if cmd == PlaybackControl.STOP:
                if on_control:
                    on_control(cmd)
                return cmd

            if cmd == PlaybackControl.SHUTDOWN:
                if on_control:
                    on_control(cmd)
                return cmd

            if cmd == PlaybackControl.BACKUP:
                # Back up one word
                word_index = max(0, word_index - 1)
                self.set_control_command(PlaybackControl.CONTINUE)
                if on_control:
                    on_control(cmd)
                continue

            if cmd == PlaybackControl.PAUSE:
                # Wait until unpaused
                import time
                time.sleep(0.05)
                continue

            # Play the current word
            word = words[word_index]
            is_last_word = (word_index == len(words) - 1)
            audio_data = self._generate_word_audio(word, add_word_space=not is_last_word)

            if len(audio_data) > 0:
                # Play in smaller chunks to be more responsive
                chunk_size = self.sample_rate // 10  # 100ms chunks
                for i in range(0, len(audio_data), chunk_size):
                    # Check for pause or stop between chunks
                    cmd = self.get_control_command()
                    if cmd in (PlaybackControl.PAUSE, PlaybackControl.STOP,
                              PlaybackControl.SHUTDOWN, PlaybackControl.BACKUP):
                        break

                    chunk = audio_data[i:i+chunk_size]
                    self.stream.write(chunk.tobytes())

            word_index += 1

        return PlaybackControl.CONTINUE

    def close(self) -> None:
        """Clean up audio resources."""
        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        self.audio.terminate()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
