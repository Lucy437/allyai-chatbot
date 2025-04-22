from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
from flask_cors import CORS
import openai
import os
# Load all scenario scripts from JSON
with open("scenarios.json", "r", encoding="utf-8") as f:
    SCENARIOS = json.load(f)

app = Flask(__name__)
CORS(app)
user_state = {}  # Tracks where each user is in the conversation
def get_scenario_script(category, scenario_text):
    for entry in SCENARIOS:
        if entry["category"] == category and scenario_text.strip().lower() in entry["scenario"].lower():
            return entry["steps"]
    return None

def get_next_step(user_id):
    state = user_state[user_id]
    script = get_scenario_script(state["category"], state["scenario"])
    index = state.get("step_index", 0)

    if index < len(script):
        step = script[index]
        user_state[user_id]["step_index"] += 1  # Move to next step
        return step
    else:
        return {"type": "end", "bot": "That’s all for now. If you want to talk about something else, just say 'menu' 💬"}
user_sessions = {}  # Tracks assessment sessions
user_profiles = {}  # Tracks names and states for flow

openai.api_key = os.getenv("OPENAI_API_KEY")

# ------------------------- AllyAI System Prompt ------------------------- #
ALLYAI_SYSTEM_PROMPT = """
You are AllyAI — a warm, emotionally intelligent AI coach designed to support girls aged 15–25 navigating challenges in romantic relationships, friendships, family dynamics, confidence, and mental health.

Your tone should be kind, supportive, non-judgmental, and emotionally validating — like a wise older sister or therapist-coach hybrid. Use simple, safe, and relatable language. Your role is to make the user feel seen, heard, and gently empowered.

Always follow this 5-step AllyAI flow in your responses:

1. Emotional Validation — Acknowledge and name the emotion behind the user’s message.
2. Gentle Exploration — Ask a short follow-up question to help the user reflect. Offer 3–4 tapable choices plus one open option.
3. Psychoeducation — Share a short insight using psychological principles (e.g. boundaries, anxious attachment).
4. Empowerment & Reframe — Affirm their worth and agency.
5. Optional Support — Offer help crafting a message, calming down, or practicing a boundary.

Prioritize emotional safety and use a tone that is soft, clear, and empowering.
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

# WhatsApp bot route
@app.route("/bot", methods=["POST"])
def bot():
    incoming_msg = request.values.get('Body', '').strip().lower()
    from_number = request.values.get('From')
    response = MessagingResponse()
    msg = response.message()

    if incoming_msg == "restart":
        user_state[from_number] = {"stage": "intro"}
        msg.body("Let's start over. 👋")
        return str(response)

    if from_number not in user_state:
        user_state[from_number] = {"stage": "intro"}

    state = user_state[from_number]

    if incoming_msg == "start assessment":
        user_sessions[from_number] = {"current_q": 0, "answers": []}
        first_q = get_next_assessment_question(from_number)
        msg.body("Let’s begin! ✨\n\n" + first_q)
        return str(response)

    if from_number in user_sessions:
        handle_assessment_answer(from_number, incoming_msg)
        next_q = get_next_assessment_question(from_number)
        if next_q:
            msg.body(next_q)
        else:
            scores = calculate_trait_scores(user_sessions[from_number]["answers"])
            identity = assign_identity(scores)
            feedback = generate_feedback(scores, identity)
            del user_sessions[from_number]
            msg.body(feedback)
        return str(response)

    if state["stage"] == "intro":
        msg.body("Hi, I'm Ally 👋\nI'm here to support you in understanding your relationships and yourself better.\n\nWould you like to:\n1. Ask me a question\n2. Take a quick assessment to learn more about yourself\n\nReply with 1 or 2.")
        state["stage"] = "choose_path"
        return str(response)

    if state["stage"] == "choose_path":
        if incoming_msg == "1":
            msg.body("Great! What’s on your mind? Type your question.")
            state["stage"] = "greeting"
        elif incoming_msg == "2":
            user_sessions[from_number] = {"current_q": 0, "answers": []}
            first_q = get_next_assessment_question(from_number)
            msg.body("Let’s begin! ✨\n\n" + first_q)
        else:
            msg.body("Please reply with 1 or 2 to choose.")
        return str(response)

  if state["stage"] == "choose_scenario":
    category = user_profiles[from_number].get("category")

    scenario_map = {
        "Romantic Partner Issues": [
            "He ghosts me every time we argue.",
            "I have to ask permission to see friends.",
            "He likes other girls’ photos and it makes me insecure.",
            "I feel nervous saying no to him."
        ],
        "Friendship Challenges": [
            "My friend makes fun of me in front of others.",
            "She ignores me in group settings.",
            "She tells others my secrets.",
            "I’m always the one initiating."
        ],
        "Family Tensions": [
            "My family criticizes how I look.",
            "They compare me to cousins and say I’m not enough.",
            "They don’t support my career dreams.",
            "They don’t let me have social media."
        ],
        "Building Self-Confidence": [
            "I freeze in large groups.",
            "I’m scared to try new things.",
            "Everyone seems more confident than me.",
            "I want to say no, but I’m afraid."
        ],
        "Overcoming Insecurity": [
            "I compare myself constantly.",
            "I don’t like the way I look.",
            "I overthink everything.",
            "I feel like I’m not enough."
        ],
        "Urgent Advice": [
            "My boyfriend said he’ll hurt himself if I leave.",
            "I feel anxious and frozen.",
            "I think I made a huge mistake.",
            "My boyfriend hit me but apologized."
        ]
    }

    try:
        selected_index = int(incoming_msg) - 1
        scenario = scenario_map[category][selected_index]
        user_profiles[from_number]["scenario"] = scenario
        user_state[from_number]["stage"] = "chat_mode"
        user_state[from_number]["step_index"] = 0

        steps = get_scenario_script(category, scenario)
        first_step = steps[0]

        options_text = ""
        if "options" in first_step:
            options_text = "\n\n" + "\n".join([f"- {opt}" for opt in first_step["options"]])

        msg.body(first_step["bot"] + options_text)

    except Exception as e:
        print("Error in choose_scenario block:", e)
        msg.body("Something went wrong. Please reply with a valid number.")

    return str(response)
