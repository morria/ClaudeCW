# Amateur Radio CW Practice Bot

An interactive Morse code (CW) practice tool that uses Claude AI to simulate realistic amateur radio conversations. The bot acts as an experienced ham radio operator, engaging in authentic QSOs (conversations) complete with proper procedure, abbreviations, and Morse code audio playback.

## Features

- **AI-Powered Conversations**: Uses Claude AI to generate realistic amateur radio conversations
- **Authentic CW Experience**: Plays responses as actual Morse code audio through your speakers
- **Configurable Speed**: Adjustable WPM (words per minute) and Farnsworth timing
- **Realistic Behavior**: The bot calls CQ, uses proper procedures, and follows ham radio conventions
- **Unique Callsigns**: Generates realistic callsigns from various countries for each conversation
- **Standard Abbreviations**: Uses authentic ham radio Q-codes and abbreviations (RST, QTH, WX, etc.)

## Requirements

- Python 3.8 or higher
- A Claude API key from Anthropic
- Audio output device (speakers/headphones)

## Installation

1. Clone this repository or download the files

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

**Note**: On some systems, you may need to install PortAudio for PyAudio:

- **Linux**: `sudo apt-get install portaudio19-dev python3-pyaudio`
- **macOS**: `brew install portaudio`
- **Windows**: PyAudio should install directly from pip

3. Configure the bot by copying the example config and adding your API key:
```bash
cp config.yaml.example config.yaml
# Edit config.yaml with your favorite editor and add your API key
```

The configuration file should look like this:
```yaml
claude:
  api_key: "your-api-key-here"  # Get from https://console.anthropic.com/

morse:
  wpm: 20                        # Character speed in words per minute
  farnsworth_wpm: 15             # Effective speed (lower = more spacing)
  frequency: 700                 # Audio tone frequency in Hz

audio:
  sample_rate: 44100
  volume: 0.3                    # 0.0 to 1.0
```

## Usage

Run the bot:
```bash
python3 cw_bot.py
```

Or with a custom config file:
```bash
python3 cw_bot.py my_config.yaml
```

### Commands

While running:
- Type your message and press Enter to transmit
- `quit` or `exit` - End the session
- `new` - Start a new conversation with a new operator (new callsign)
- `callsign` - Show the current operator's callsign

### Example Session

```
You: CQ CQ CQ DE W1ABC W1ABC K

[AI Operator]: W1ABC DE K7XYZ K7XYZ UR RST 599 599 QTH SEATTLE WA NAME MIKE MIKE HW COPY? K

[Playing CW...]

You: K7XYZ DE W1ABC FB MIKE UR 599 TOO QTH BOSTON MA NAME SARAH OP 5 YEARS WX SUNNY 72F RIG ICOM 7300 100W HW? K

[AI Operator]: FB SARAH TNX FER CALL NICE WX HR CLOUDY 65F RUNNING YAESU FT991A 100W TO DIPOLE ANT HPE CUAGN 73 DE K7XYZ SK
```

## Configuration Guide

### WPM Settings

- **wpm**: Controls the speed of individual characters (dit/dah timing)
- **farnsworth_wpm**: Controls overall effective speed by adding spacing between characters
  - Set equal to `wpm` for uniform timing
  - Set lower than `wpm` to give more time to recognize characters (Farnsworth timing)

Example: `wpm: 20, farnsworth_wpm: 15` means characters are sent at 20 WPM but spaced to achieve an effective rate of 15 WPM.

### Frequency

Typical CW frequencies range from 400-800 Hz. Common choices:
- 600 Hz - Lower, mellower tone
- 700 Hz - Standard (default)
- 800 Hz - Higher, crisper tone

### Volume

Set between 0.0 (silent) and 1.0 (maximum). Start with 0.3 and adjust to taste.

## Understanding the Bot

The AI operator behaves like a real ham radio operator:

- Uses standard procedural signals (CQ, DE, K, SK, etc.)
- Employs common abbreviations and Q-codes
- Shares location, equipment details, and weather
- Maintains conversational but concise style (CW is work!)
- Generates a unique callsign for each conversation

### Common Abbreviations

- **CQ**: General call to all stations
- **DE**: From (identifying transmission)
- **K**: Over (invitation to transmit)
- **SK**: End of contact
- **RST**: Signal report (Readability, Strength, Tone)
- **QTH**: Location
- **WX**: Weather
- **RIG**: Radio equipment
- **ANT**: Antenna
- **FB**: Fine Business (great/excellent)
- **TNX**: Thanks
- **73**: Best regards
- **HPE CUAGN**: Hope to see you again

## Project Structure

```
ClaudeCW/
├── cw_bot.py          # Main application
├── morse_generator.py # Morse code audio generation
├── radio_operator.py  # Claude AI integration
├── config.yaml        # Configuration file
├── requirements.txt   # Python dependencies
└── README.md         # This file
```

## Troubleshooting

### Audio Issues

If you don't hear any sound:
1. Check your system volume
2. Adjust the `volume` setting in config.yaml
3. Try a different frequency (some frequencies may be harder to hear)
4. Ensure PyAudio is properly installed with PortAudio support

### API Issues

If you get API errors:
1. Verify your API key is correct in config.yaml
2. Check your internet connection
3. Ensure you have API credits available at https://console.anthropic.com/

### Import Errors

If you get import errors:
1. Ensure all requirements are installed: `pip install -r requirements.txt`
2. Check you're using Python 3.8 or higher: `python3 --version`

## License

This project is provided as-is for educational and practice purposes.

## Contributing

Contributions are welcome! Feel free to submit issues or pull requests.

## Acknowledgments

- Anthropic for the Claude API
- The amateur radio community for inspiration and standards
- Python audio libraries (NumPy, PyAudio) for making CW generation possible

73 de ClaudeCW! 🎵📻
