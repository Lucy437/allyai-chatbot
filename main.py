from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
from flask_cors import CORS
import openai
import os
import json 
# Load all scenario scripts from JSON
with open("scenarios.json", "r", encoding="utf-8") as f:
    SCENARIOS = json.load(f)

app = Flask(__name__)
CORS(app)
# Track user states
user_state = {}
user_profiles = {}
user_sessions = {}

# OpenAI API Key
openai.api_key = os.getenv("OPENAI_API_KEY")

# ------------------------- AllyAI System Prompt ------------------------- #
ALLYAI_SYSTEM_PROMPT = """
You are AllyAI — a warm, emotionally intelligent AI coach who supports girls aged 15–25 navigating challenges in relationships, self-worth, confidence, and mental health.

You speak like a wise older sister or therapist-coach hybrid. You are emotionally safe, relatable, and empowering.

Use short, human, natural-sounding messages. You are texting — avoid long paragraphs. Be warm, clear, and never robotic.

Always follow this 5-step AllyAI structure:

1. **Emotional Validation** — Acknowledge how the user feels and name the emotion.
2. **Gentle Exploration** — Ask a short follow-up question. Offer 2–4 simple tap-worthy replies (plus “Type your own…”).
3. **Psychoeducation** — Briefly explain the concept (like ghosting, boundaries, anxious attachment) in a non-academic, supportive way.
4. **Empowerment & Reframe** — Affirm the user's worth. Normalize their experience and offer a new perspective.
5. **Optional Support** — Offer to help write a message, plan next steps, or practice a boundary.

You never give advice like a lecture. You ask questions that help the user come to their own decision.

Your goal is to help the user feel:
- Seen and supported
- Gently challenged
- Ready to make their next move

You never overwhelm — keep it simple and kind.
"""
# ------------------------- Assessment Setup ------------------------- #
assessment_questions = [
    {
        "id": 1,
        "text": "You just got invited to speak briefly at your school or group meeting about a topic you’re passionate about. What’s your first reaction?",
        "dimension": "Confidence",
        "options": {
            "a": "I'm not good at public speaking. I’ll just pass.",
            "b": "I could do it if I have time to prepare, but I’m not sure I’ll be taken seriously.",
            "c": "I’ll try! Even if it’s not perfect, it’s a good learning experience.",
            "d": "Absolutely! I love speaking up and sharing my thoughts."
        },
        "scores": {"a": 1, "b": 2, "c": 3, "d": 4}
    },
    {
        "id": 2,
        "text": "Your friend is upset because she feels left out after you spent more time with another group. She brings it up to you. How do you respond?",
        "dimension": "Empathy",
        "options": {
            "a": "Ugh, I didn’t do anything wrong — she’s overreacting.",
            "b": "I say sorry quickly, just to end the drama.",
            "c": "I try to understand where she’s coming from and talk it through.",
            "d": "I ask her more about how she feels and tell her I want us both to feel included."
        },
        "scores": {"a": 1, "b": 2, "c": 3, "d": 4}
    },
    {
        "id": 3,
        "text": "After a fight with someone close to you, how do you usually reflect on it?",
        "dimension": "Self-Awareness",
        "options": {
            "a": "I don’t really think about it — I move on fast.",
            "b": "I overthink it for days and wonder what they must think of me.",
            "c": "I try to look at what triggered me and how I reacted.",
            "d": "I notice my emotions, patterns, and talk to someone to get perspective."
        },
        "scores": {"a": 1, "b": 2, "c": 3, "d": 4}
    },
    {
        "id": 4,
        "text": "You’re dating someone who often makes jokes at your expense in front of others. How do you respond?",
        "dimension": "Self-Respect",
        "options": {
            "a": "It’s not a big deal — I laugh along to keep things cool.",
            "b": "It hurts, but I stay quiet and try to ignore it.",
            "c": "I bring it up later and say it made me uncomfortable.",
            "d": "I call it out calmly in the moment and let them know it’s not okay."
        },
        "scores": {"a": 1, "b": 2, "c": 3, "d": 4}
    },
    {
        "id": 5,
        "text": "A classmate or coworker takes credit for your idea in a group project. What do you do?",
        "dimension": "Communication",
        "options": {
            "a": "I keep quiet — I don’t want to seem rude or jealous.",
            "b": "I hint that it was actually my idea, hoping others notice.",
            "c": "I talk to them one-on-one and explain how it made me feel.",
            "d": "I address it respectfully in front of the group to clarify."
        },
        "scores": {"a": 1, "b": 2, "c": 3, "d": 4}
    },
    {
        "id": 6,
        "text": "A friend constantly calls late at night to vent, even when you’ve told them you’re tired or studying. What do you do?",
        "dimension": "Boundary-Setting",
        "options": {
            "a": "I always pick up — they need me.",
            "b": "I ignore the call but feel guilty after.",
            "c": "I let them know I care, but can’t talk at night anymore.",
            "d": "I set a firm boundary and suggest specific times to talk instead."
        },
        "scores": {"a": 1, "b": 2, "c": 3, "d": 4}
    }
]

def get_next_assessment_question(user_id):
    session = user_sessions[user_id]
    q_index = session["current_q"]
    if q_index < len(assessment_questions):
        q = assessment_questions[q_index]
        options_text = "\n".join([f"{opt.upper()}. {text}" for opt, text in q["options"].items()])
        return f"{q['text']}\n\n{options_text}"
    return None

def handle_assessment_answer(user_id, answer_letter):
    session = user_sessions[user_id]
    q_index = session["current_q"]
    q = assessment_questions[q_index]
    score = q["scores"].get(answer_letter.lower(), 0)
    session["answers"].append({"dimension": q["dimension"], "score": score})
    session["current_q"] += 1

def calculate_trait_scores(answers):
    scores = {}
    for a in answers:
        scores[a["dimension"]] = scores.get(a["dimension"], 0) + a["score"]
    return scores

def assign_identity(scores):
    top_two = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:2]
    combo = frozenset([t[0] for t in top_two])
    identity_map = {
        frozenset(["Confidence", "Communication"]): "👑 The Empowered Queen\nYou own your voice and lead with unapologetic strength. When you speak, people listen. You turn your truth into action and your presence into power.",
        frozenset(["Self-Awareness", "Empathy"]): "🪞 The Healer Oracle\nYou see into the hearts of others and the depths of your own soul. Your empathy is matched only by your inner wisdom — a powerful combo that brings light to the darkest places.",
        frozenset(["Boundary-Setting", "Self-Respect"]): "🛡️ The Guardian Queen\nYou are the sovereign of your space. With grace and steel, you defend your peace, protect your heart, and teach others what it means to honor you.",
    }
    return identity_map.get(combo, "👑 The Growth Queen\nYou're on a beautiful path of self-discovery. You’re growing in multiple areas and becoming more aware of your inner power. Keep showing up — your transformation is already happening.")

def generate_feedback(scores, identity):
    bars = "\n".join([f"{trait}: {int(score * 25)}%" for trait, score in scores.items()])
    weakest_trait = min(scores, key=scores.get)
    return (
        f"🌟 Your AllyAI Identity:\n{identity}\n\n"
        f"Here’s your growth profile:\n{bars}\n\n"
        f"You’re strongest in {max(scores, key=scores.get)}.\n"
        f"But we’ll also work on your {weakest_trait} — because that’s how you become unstoppable 💫"
    )

@app.route("/bot", methods=["POST"])
def bot():
    from_number = request.values.get("From")
    incoming_msg = request.values.get("Body", "").strip()

    response = MessagingResponse()
    msg = response.message()

    if incoming_msg.lower() == "test gpt":
        try:
            completion = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a friendly chatbot."},
                    {"role": "user", "content": "Say hello in a warm and short way."}
                ],
                temperature=0.5
            )
            reply = completion.choices[0].message["content"].strip()
            msg.body(f"✅ GPT works!\n\n{reply}")
        except Exception as e:
            msg.body(f"❌ GPT failed: {str(e)}")
        return str(response)

    msg.body("Type 'test gpt' to run a GPT check.")
    return str(response)


# # WhatsApp bot route
# @app.route("/bot", methods=["POST"])
# def bot():
#     incoming_msg = request.values.get('Body', '').strip()
#     from_number = request.values.get('From')
#     response = MessagingResponse()
#     msg = response.message()

#     if incoming_msg.lower() == "restart":
#         user_state[from_number] = {"stage": "intro"}
#         msg.body("Let's start over. 👋")
#         return str(response)

#     if from_number not in user_state:
#         user_state[from_number] = {"stage": "intro"}
#         msg.body("Hi, I'm Ally 👋\nI'm here to support you in understanding your relationships and yourself better.\n\nWhat’s your name?")
#         return str(response)

#     state = user_state[from_number]

#     if state["stage"] == "intro":
#         user_profiles[from_number] = {"name": incoming_msg.title()}
#         user_state[from_number]["stage"] = "choose_path"
#         msg.body(f"Nice to meet you, {incoming_msg.title()}!\n\nHow can I help you today?\n1. Ask for advice\n2. Take a quick assessment to understand your relationship style")
#         return str(response)

#     if state["stage"] == "choose_path":
#         if incoming_msg == "1":
#             user_state[from_number]["stage"] = "choose_category"
#             msg.body("Choose a topic you want to talk about:\n1. Romantic Partner Issues\n2. Friendship Challenges\n3. Family Tensions\n4. Building Self-Confidence\n5. Overcoming Insecurity\n6. Urgent Advice")
#         elif incoming_msg == "2":
#             user_sessions[from_number] = {"current_q": 0, "answers": []}
#             first_q = get_next_assessment_question(from_number)
#             msg.body("Let’s begin! ✨\n\n" + first_q)
#         else:
#             msg.body("Please reply with 1 or 2.")
#         return str(response)

#     if state["stage"] == "choose_category":
#         category_map = {
#             "1": "Romantic Partner Issues",
#             "2": "Friendship Challenges",
#             "3": "Family Tensions",
#             "4": "Building Self-Confidence",
#             "5": "Overcoming Insecurity",
#             "6": "Urgent Advice"
#         }
#         selected = category_map.get(incoming_msg)
#         if selected:
#             user_profiles[from_number]["category"] = selected
#             state["stage"] = "choose_scenario"

#             options = [s["scenario"] for s in SCENARIOS if s["category"] == selected]
#             options.append("Something else — I want to describe my situation in my own words.")

#             user_state[from_number]["scenario_options"] = options
#             option_text = "\n".join([f"{i+1}. {s}" for i, s in enumerate(options)])
#             msg.body(f"Thanks! Here are some common situations under *{selected}*:\n\n{option_text}\n\nReply with the number that fits your situation.")
#         else:
#             msg.body("Please choose a valid number from the list above.")
#         return str(response)

#     if state["stage"] == "choose_scenario":
#         options = user_state[from_number].get("scenario_options", [])
#         try:
#             selected_index = int(incoming_msg) - 1
#             if selected_index < len(options) - 1:
#                 scenario = options[selected_index]
#                 user_profiles[from_number]["scenario"] = scenario
#                 user_state[from_number]["stage"] = "gpt_mode"
#                 msg.body("Thanks for sharing that. I’m here for you 💛 Just tell me a bit more about what’s been going on, and we’ll work through it together.")
#             elif selected_index == len(options) - 1:
#                 user_state[from_number]["stage"] = "gpt_mode_custom"
#                 msg.body("No problem — just type out what’s going on and I’ll do my best to help 💬")
#             else:
#                 msg.body("Please choose a valid number from the list.")
#         except:
#             msg.body("Please reply with the number of your choice.")
#         return str(response)

#     if from_number in user_sessions:
#         handle_assessment_answer(from_number, incoming_msg)
#         next_q = get_next_assessment_question(from_number)
#         if next_q:
#             msg.body(next_q)
#         else:
#             scores = calculate_trait_scores(user_sessions[from_number]["answers"])
#             identity = assign_identity(scores)
#             feedback = generate_feedback(scores, identity)
#             del user_sessions[from_number]
#             msg.body(feedback)
#         return str(response)

#     if state["stage"] in ["gpt_mode", "gpt_mode_custom"]:
#         scenario = user_profiles.get(from_number, {}).get("scenario", "").strip()
#         user_input = incoming_msg.strip()
    
#         if state["stage"] == "gpt_mode_custom":
#             scenario = user_input
    
#         # 🛡️ NEW fallback if scenario is missing
#         if not scenario:
#             msg.body("Hmm, I didn’t quite catch that. Can you describe what’s going on again?")
#             return str(response)
    
#         # 🛡️ NEW fallback if user didn’t say anything
#         if not user_input:
#             msg.body("Could you tell me a bit more about what's happening so I can help?")
#             return str(response)
    
#         prompt = f"""{ALLYAI_SYSTEM_PROMPT}
    
#     The user described this situation: {scenario}
#     Now they said: {user_input}
#     Continue the AllyAI coaching conversation using the 5-step structure."""
    
#         try:
#             completion = openai.ChatCompletion.create(
#                 model="gpt-4",
#                 messages=[
#                     {"role": "system", "content": ALLYAI_SYSTEM_PROMPT},
#                     {"role": "user", "content": prompt}
#                 ],
#                 temperature=0.7
#             )
#             reply = completion.choices[0].message["content"].strip()
#             msg.body(reply)
#         except Exception:
#             msg.body("Something went wrong while generating a response. Please try again or type 'restart' to start over.")
    
#         return str(response)

