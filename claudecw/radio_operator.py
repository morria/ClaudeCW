"""
Amateur Radio operator AI using Claude API.
Simulates realistic ham radio CQ calls and QSOs.
"""

import random
import anthropic
from typing import Optional


class RadioOperator:
    """AI-powered amateur radio operator."""

    # Realistic callsign prefixes by region
    CALLSIGN_PREFIXES = [
        'W', 'K', 'N',  # USA
        'VE',           # Canada
        'G', 'M',       # UK
        'DL', 'DJ',     # Germany
        'F',            # France
        'I',            # Italy
        'JA', 'JE',     # Japan
        'VK',           # Australia
        'ZL',           # New Zealand
        'PY',           # Brazil
    ]

    SYSTEM_PROMPT = """You are an experienced amateur radio operator engaged in a CW (Morse code) conversation.

Your behavior:
- Keep transmissions VERY brief - aim for 1-2 short sentences maximum per transmission
- Use standard ham radio abbreviations (QTH, RST, WX, RIG, ANT, etc.)
- Use procedural signals: CQ for calling, DE for "from", K for "over", SK for "end of contact"
- Be friendly and conversational but concise (this is CW, not phone!)
- Ask ONE question at a time, then wait for a response - don't ask multiple questions
- Share your own made-up details briefly: location, rig, antenna, experience
- Use the callsign {callsign} in your transmissions
- Start with either calling CQ or responding to a CQ call
- Use proper CW formatting: BT for break, AR for end of message, SK for end of contact
- Wait to be asked about weather, QTH, rig or antenna. Do not offer details without prompting.
- CRITICAL: Keep each response under 15 words - real CW QSOs are quick back-and-forth exchanges!

Common abbreviations to use naturally:
- RST: Readability, Strength, Tone (e.g., "UR RST 599")
- QTH: Location
- WX: Weather
- RIG: Radio equipment
- ANT: Antenna
- PWR: Power
- OP/NAME: Operator name
- HPE CUAGN: Hope to see you again
- 73: Best regards
- 88: Love and kisses (rarely used)
- FB: Fine business (excellent)
- TNX: Thanks
- GM/GA/GE: Good morning/afternoon/evening

Remember: You're having a genuine ragchew (casual conversation) with a fellow ham! Keep it short and give them a chance to respond. Each transmission should feel like a natural turn-taking conversation."""

    def __init__(self, api_key: str, callsign: Optional[str] = None):
        """
        Initialize the radio operator.

        Args:
            api_key: Claude API key
            callsign: Optional callsign (will be generated if not provided)
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.callsign = callsign or self._generate_callsign()
        self.conversation_history = []
        self.model = "claude-sonnet-4-5-20250929"

    def _generate_callsign(self) -> str:
        """Generate a realistic amateur radio callsign."""
        prefix = random.choice(self.CALLSIGN_PREFIXES)

        # Generate suffix (1-3 letters)
        suffix_length = random.choice([2, 3])
        suffix = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=suffix_length))

        # Add a number
        number = random.randint(0, 9)

        return f"{prefix}{number}{suffix}"

    def get_response(self, user_message: str, is_first_message: bool = False) -> str:
        """
        Get a response from the AI operator.

        Args:
            user_message: The user's message
            is_first_message: Whether this is the first message (affects behavior)

        Returns:
            The operator's response
        """
        # Add context for first message
        if is_first_message:
            if user_message.strip().upper().startswith('CQ'):
                context = f"The other station is calling CQ. Respond to their call. Your callsign is {self.callsign}."
            else:
                context = f"Start by calling CQ to establish contact. Your callsign is {self.callsign}."

            system_prompt = self.SYSTEM_PROMPT.format(callsign=self.callsign) + f"\n\n{context}"
        else:
            system_prompt = self.SYSTEM_PROMPT.format(callsign=self.callsign)

        # Add user message to history
        if user_message.strip():
            self.conversation_history.append({
                "role": "user",
                "content": user_message
            })

        # Get response from Claude
        response = self.client.messages.create(
            model=self.model,
            max_tokens=300,
            system=system_prompt,
            messages=self.conversation_history
        )

        assistant_message = response.content[0].text

        # Add assistant response to history
        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_message
        })

        return assistant_message

    def reset_conversation(self) -> None:
        """Reset the conversation and generate a new callsign."""
        self.conversation_history = []
        self.callsign = self._generate_callsign()

    def get_callsign(self) -> str:
        """Get the current callsign."""
        return self.callsign
