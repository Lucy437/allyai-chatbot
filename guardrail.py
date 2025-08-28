# guardrail.py
import os
import asyncio
import threading
from openai import AsyncOpenAI
from twilio.rest import Client as TwilioClient

# Init async OpenAI + Twilio clients
client = AsyncOpenAI()
twilio_client = TwilioClient(
    os.getenv("TWILIO_SID"),
    os.getenv("TWILIO_AUTH_TOKEN")
)

TWILIO_NUMBER = "whatsapp:+14155238886"  # replace with your Twilio number whatsapp:+ 18335661105

GUARDRAIL_SYSTEM_PROMPT = """
You are AllyAI’s Safety Guardrail Agent.

Your task is to classify if the user's latest message (considering recent context)
shows clear, explicit red flags of self-harm/suicide or ongoing violent abuse.

Output ONLY ONE of these labels (exactly):
SAFE / DISTRESS / CRISIS

Use these STRICT rules:
- SAFE: Everyday venting, sadness, relationship drama, frustration, or strong emotion
  WITHOUT explicit self-harm/suicide plan/intent/means/timing AND WITHOUT active violent abuse.
  If you are unsure, or cannot cite a concrete phrase that clearly indicates CRISIS,
  choose SAFE and keep assessing the chat history.
- DISTRESS: Notable distress (e.g., “I feel hopeless,” “I can’t cope,” “I hate myself”)
  but NO explicit plan/intent/means/timing AND no active violent abuse. (Do NOT interrupt chat.)
- CRISIS: Explicit, current, or imminent risk (plan/means/intent/time) for self-harm/suicide
  OR active ongoing violent abuse/endangerment. Examples:
  “I will kill myself tonight,” “I took pills to end it,” “He is hitting me now,”
  “He says he'll kill me if I leave.”

Ambiguity rule:
- If you cannot cite a concrete phrase that clearly indicates CRISIS,
  choose SAFE and continue monitoring the ongoing conversation.

Only return the label (SAFE, DISTRESS, or CRISIS) as plain text.
"""

async def classify_message_async(history, new_input):
    """Classify message into SAFE / DISTRESS / CRISIS using LLM"""
    prompt = f"""
Conversation so far:
{history}

Latest message:
{new_input}

Classify into: SAFE / DISTRESS / CRISIS
(Choose SAFE unless there is clear, explicit crisis per the rules.)
"""
    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": GUARDRAIL_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )
    return resp.choices[0].message.content.strip().upper()

def launch_guardrail_check(user_id, history, user_input):
    """Run guardrail in a background thread so it never blocks Flask"""

    async def runner():
        classification = await classify_message_async(history, user_input)

        # Only interrupt on CRISIS; do not interrupt on DISTRESS (minimal change).
        if classification == "CRISIS":
            twilio_client.messages.create(
                body=(
                    "💛 I hear how heavy this feels. Please know you’re not alone.\n\n"
                    "📞 If you’re in immediate danger or thinking of hurting yourself, "
                    "consider contacting local emergency services, or visit https://findahelpline.com "
                    "to find support in your area."
                ),
                from_=TWILIO_NUMBER,
                to=user_id
            )

        # If SAFE or DISTRESS: do nothing here (no interruption).
        # If you want the main chat to adapt tone, you can store `classification` in session state.

    def run_in_thread():
        asyncio.run(runner())

    threading.Thread(target=run_in_thread, daemon=True).start()
