# helpers.py
# Utilities for AllyAI: persona prompt, relevance check, step progression,
# lightweight intent detection, and step-aware prompt generation.

from typing import Dict

# -------- Persona / System Prompt -------- #
ALLYAI_SYSTEM_PROMPT = """
You are AllyAI — a warm, emotionally intelligent coach supporting girls aged 15–25
with relationships, confidence, and mental health.

Speak like a caring older sister or therapist-coach hybrid. Be warm, validating,
and empowering. Use short, natural messages — no lectures, no long paragraphs.

Always prioritize emotional safety and empowerment. Never sound robotic or formal.
""".strip()


# -------- Lightweight helpers -------- #
def is_relevant(text: str) -> bool:
    """Return True if the user text is non-trivial (prevents empty/very short replies)."""
    return bool(text) and len(text.strip()) > 5


def detect_intent(user_input: str) -> str:
    """
    Very simple intent detector to steer the step machine.
    Returns one of: 'wants_message_help', 'wants_advice', 'emotional_venting', 'normal'
    """
    t = (user_input or "").lower()

    message_help_phrases = [
        "help me", "craft a message", "write a message",
        "what should i say", "how should i say it", "can you write"
    ]
    advice_phrases = [
        "advice", "what should i do", "what would you do", "can you advise"
    ]
    venting_phrases = [
        "i feel", "it hurts", "i'm sad", "i am sad", "i'm mad", "i am mad",
        "i'm confused", "i am confused", "i'm upset", "i am upset"
    ]

    if any(p in t for p in message_help_phrases):
        return "wants_message_help"
    if any(p in t for p in advice_phrases):
        return "wants_advice"
    if any(p in t for p in venting_phrases):
        return "emotional_venting"
    return "normal"


# -------- Step machine -------- #
_STEP_NEXT = {
    "validation_exploration": "psychoeducation",
    "psychoeducation": "empowerment",
    "empowerment": "offer_message_help",
    "offer_message_help": "closing",
    "drafting_message": "closing",
    "closing": "closing",
}

def update_user_step(user_state: Dict[str, dict], user_id: str) -> None:
    """
    Advance the user's conversation step in the in-memory user_state.
    Usage (in your /bot route):  update_user_step(user_state, from_number)
    """
    if user_id not in user_state:
        user_state[user_id] = {"current_step": "validation_exploration"}
    current = user_state[user_id].get("current_step") or "validation_exploration"
    user_state[user_id]["current_step"] = _STEP_NEXT.get(current, "closing")


# -------- Prompt builder -------- #
def generate_prompt(current_step: str, scenario: str, user_input: str) -> str:
    """
    Build a concise, step-aware prompt for the LLM.
    Steps: validation_exploration | psychoeducation | empowerment | offer_message_help | closing
    """
    base = (
        "You are AllyAI — a warm, emotionally intelligent coach speaking like a supportive big sister.\n\n"
        f"Situation: {scenario}\n"
        f"User said: {user_input}\n\n"
        "TASK:\n"
    )

    if current_step == "validation_exploration":
        return base + (
            "- Validate the user's feelings warmly and naturally.\n"
            "- Reflect the emotions you hear (without overanalyzing).\n"
            "- Ask one short, caring follow-up question.\n"
            "- Keep it short (2–4 sentences)."
        )

    if current_step == "psychoeducation":
        return base + (
            "- Gently explain a relatable emotional pattern linked to the user's situation (e.g., boundaries, attachment).\n"
            "- Be non-academic, supportive, and easy to understand.\n"
            "- End with one short follow-up question.\n"
            "- Keep it brief (2–4 sentences)."
        )

    if current_step == "empowerment":
        return base + (
            "- Affirm the user's worth and normalize their feelings.\n"
            "- Offer a positive reframe or empowering thought.\n"
            "- Invite gentle reflection (e.g., 'How does that feel to you?').\n"
            "- Keep it short, tender, and motivating."
        )

    if current_step == "offer_message_help" or current_step == "drafting_message":
        return base + (
            "- Offer to help the user craft a short message, boundary, or plan.\n"
            "- Be very practical, specific, and reassuring.\n"
            "- Keep it concise."
        )

    if current_step == "closing":
        return base + (
            "- Thank the user warmly for opening up.\n"
            "- Affirm their strength and any progress they've made.\n"
            "- Close with a short encouragement to return anytime."
        )

    # Fallback
    return (
        "You are AllyAI — be warm, validating, and brief.\n"
        f"Respond naturally to: {user_input}"
    )
