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

TWILIO_NUMBER = "whatsapp:+18335661105"  # replace with your Twilio number

GUARDRAIL_SYSTEM_PROMPT = """
You are AllyAI’s Safety Guardrail Agent.
Classify if the user’s message and recent chat history 
show emotional distress, self-harm, abuse, or suicidal risk.

Output only one label:
SAFE / DISTRESS / CRISIS
"""

async def classify_message_async(history, new_input):
    """Classify message into SAFE / DISTRESS / CRISIS using LLM"""
    prompt = f"""
    Conversation so far:
    {history}

    Latest message:
    {new_input}

    Classify into: SAFE / DISTRESS / CRISIS
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

        if classification == "CRISIS":
            twilio_client.messages.create(
                body=(
                    "💛 I hear how heavy this feels. Please know you’re not alone.\n\n"
                    "📞 If you’re in danger or thinking of hurting yourself, "
                    "call your local hotline or visit https://findahelpline.com"
                ),
                from_=TWILIO_NUMBER,
                to=user_id
            )

        elif classification == "DISTRESS":
            twilio_client.messages.create(
                body=(
                    "💛 I hear you’re going through something tough. "
                    "Remember you can always reach out to real people if it feels overwhelming."
                ),
                from_=TWILIO_NUMBER,
                to=user_id
            )

    def run_in_thread():
        asyncio.run(runner())

    threading.Thread(target=run_in_thread, daemon=True).start()
