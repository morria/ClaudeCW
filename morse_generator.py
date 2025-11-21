"""
Morse code audio generation module.
Generates CW (Continuous Wave) audio signals from text.
"""

import numpy as np
from typing import Optional
import pyaudio


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

        # Interrupt flag for stopping playback
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
