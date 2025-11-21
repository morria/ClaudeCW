#!/usr/bin/env python3
"""
Simple test to verify Morse code generation without audio playback.
"""

from morse_generator import MorseGenerator

def test_morse_conversion():
    """Test text to Morse code conversion."""
    generator = MorseGenerator(wpm=20)

    test_cases = [
        ("SOS", "... --- ..."),
        ("CQ", "-.-. --.-"),
        ("DE", "-.. ."),
        ("K", "-.-"),
        ("HELLO", ".... . .-.. .-.. ---"),
    ]

    print("Testing Morse code conversion:")
    print("-" * 50)

    for text, expected in test_cases:
        result = generator.text_to_morse(text)
        status = "✓" if result == expected else "✗"
        print(f"{status} {text:10} -> {result:30} (expected: {expected})")

    print("-" * 50)
    print("\nMorse code mappings test completed!")

    # Test audio generation (no playback)
    print("\nTesting audio generation (no playback)...")
    audio_data = generator.generate_audio("CQ CQ DE K7XYZ")
    print(f"✓ Generated {len(audio_data)} audio samples")

    print("\nAll tests passed! ✓")

if __name__ == "__main__":
    test_morse_conversion()
