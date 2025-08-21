# guardrail.py
import asyncio
from openai import AsyncOpenAI

client = AsyncOpenAI()

GUARDRAIL_SYSTEM_PROMPT = """
You are AllyAI’s Safety Guardrail Agent.
Classify if the user’s message and recent chat history 
show emotional distress, self-harm, abuse, or suicidal risk.

Output only one label:
SAFE / DISTRESS / CRISIS
"""

async def classify_message_async(history, new_input):
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
