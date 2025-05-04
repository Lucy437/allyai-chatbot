from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
from flask_cors import CORS
import openai
from openai import OpenAI
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
# openai.api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI()

# ------------------------- AllyAI System Prompt ------------------------- #
ALLYAI_SYSTEM_PROMPT = """
You are AllyAI — a warm, emotionally intelligent coach supporting girls aged 15–25 with relationships, confidence, and mental health.

Speak like a caring older sister or therapist-coach hybrid. Be warm, validating, and empowering. Use short, natural messages — no lectures, no long paragraphs.

Always prioritize emotional safety and empowerment. Never sound robotic or formal.
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
def is_relevant(text):
    return len(text.strip()) > 5
    
def update_user_step(user_id):
    current = user_state[user_id].get("current_step", "")
    next_step_map = {
        "validation_exploration": "psychoeducation",
        "psychoeducation": "empowerment",
        "empowerment": "offer_message_help",
        "offer_message_help": "closing",
        "closing": "closing"  # or optionally restart or suggest another topic
    }
    user_state[user_id]["current_step"] = next_step_map.get(current, "closing")
    
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
    answer_letter = answer_letter.strip().lower()[0]
    score = q["scores"].get(answer_letter, 0)
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
def generate_prompt(current_step, scenario, user_input):
    if current_step == "validation_exploration":
        return f"""
                You are AllyAI — a warm, emotionally intelligent coach speaking like a supportive big sister.
                
                Situation: {scenario}
                User said: {user_input}
                
                TASK:
                - Validate the user's feelings warmly and naturally.
                - Reflect the emotions you hear (without overanalyzing).
                - Ask one short, caring follow-up question.
                - Keep it short (2–4 sentences), warm, and human.
                """
    elif current_step == "psychoeducation":
        return f"""
                You are AllyAI — a warm, emotionally intelligent coach speaking like a supportive big sister.
                
                Situation: {scenario}
                User said: {user_input}
                
                TASK:
                - Gently explain a relatable emotional pattern linked to the user's situation (e.g., anxious attachment, boundaries).
                - Be non-academic, supportive, easy to understand.
                - End by asking a short follow-up question to keep the conversation going.
                - Keep it brief (2–4 sentences).
                """

    elif current_step == "empowerment":
        return f"""
                You are AllyAI — a warm, emotionally intelligent coach speaking like a supportive big sister.
                
                Situation: {scenario}
                User said: {user_input}
                
                TASK:
                - Affirm the user's worth and normalize their feelings.
                - Offer a positive reframe or empowering thought.
                - End by inviting gentle reflection ("How does that feel to you?").
                - Keep it short, tender, motivating.
                """
    elif current_step == "offer_message_help":
        return f"""
                You are AllyAI — a warm, emotionally intelligent coach speaking like a supportive big sister.
                
                Situation: {scenario}
                User said: {user_input}
                
                TASK:
                - Offer to help the user craft a short message, boundary, or plan.
                - Encourage and reassure them.
                - Be very practical, brief, and warm.
                """
    elif current_step == "closing":
        return f"""
                You are AllyAI — a warm, emotionally intelligent coach speaking like a supportive big sister.
                
                Situation: {scenario}
                User said: {user_input}
                
                TASK:
                - Thank the user warmly for opening up.
                - Affirm their strength and growth.
                - Close with a short encouragement to return anytime.
                """
    else:
        return f"""
                You are AllyAI — a warm, emotionally intelligent coach speaking like a supportive big sister.
                
                Respond warmly and naturally to what the user said: {user_input}.
                """        
# WhatsApp bot route
@app.route("/bot", methods=["POST"])
def bot():
    from_number = request.values.get("From")
    incoming_msg = request.values.get("Body", "").strip()
    
    response = MessagingResponse()
    msg = response.message()
   
    # ✅ SAFELY initialize user_state for this number
    if from_number not in user_state:
        user_state[from_number] = {}
    
    state = user_state[from_number]  # now this is safe
    
    # ✅ SAFELY initialize stage if not set yet
    if "stage" not in state:
        state["stage"] = "intro"
        msg.body("Hi, I'm Ally 👋\nI'm here to support you in understanding your relationships and yourself better.\n\nWhat’s your name?")
        return str(response)
    

    if incoming_msg.lower() == "restart":
        user_state[from_number] = {"stage": "intro"}
        msg.body("Let's start over. 👋, What is your Name")
        return str(response)

    if "stage" not in user_state[from_number]:
        user_state[from_number]["stage"] = "intro"
        msg.body("Hi, I'm Ally 👋\nI'm here to support you in understanding your relationships and yourself better.\n\nWhat’s your name?")
        return str(response)
    
    state = user_state[from_number]

    if state["stage"] == "intro":
        user_profiles[from_number] = {"name": incoming_msg.title()}
        user_state[from_number]["stage"] = "choose_path"
        msg.body(f"Nice to meet you, {incoming_msg.title()}!\n\nHow can I help you today?\n1. Ask for advice\n2. Take a quick assessment to understand your relationship style")
        return str(response)

    if state["stage"] == "choose_path":
        if incoming_msg == "1":
            user_state[from_number]["stage"] = "choose_category"
            msg.body("Choose a topic you want to talk about:\n1. Romantic Partner Issues\n2. Friendship Challenges\n3. Family Tensions\n4. Building Self-Confidence\n5. Overcoming Insecurity\n6. Urgent Advice")
        elif incoming_msg == "2":
            user_sessions[from_number] = {"current_q": 0, "answers": []}
            user_state[from_number]["stage"] = "assessment"
            first_q = get_next_assessment_question(from_number)
            msg.body("Let’s begin! ✨\n\n" + first_q)
        else:
            msg.body("Please reply with 1 or 2.")
        return str(response)

    if state["stage"] == "choose_category":
        category_map = {
            "1": "Romantic Partner Issues",
            "2": "Friendship Challenges",
            "3": "Family Tensions",
            "4": "Building Self-Confidence",
            "5": "Overcoming Insecurity",
            "6": "Urgent Advice"
        }
        selected = category_map.get(incoming_msg)
        if selected:
            user_profiles[from_number]["category"] = selected
            user_state[from_number]["stage"] = "choose_scenario"

            options = [s["scenario"] for s in SCENARIOS if s["category"] == selected]
            options.append("Something else — I want to describe my situation in my own words.")

            user_state[from_number]["scenario_options"] = options
            option_text = "\n".join([f"{i+1}. {s}" for i, s in enumerate(options)])
            msg.body(f"Thanks! Here are some common situations under *{selected}*:\n\n{option_text}\n\nReply with the number that fits your situation.")
        else:
            msg.body("Please choose a valid number from the list above.")
        return str(response)

    if state["stage"] == "choose_scenario":
        options = user_state[from_number].get("scenario_options", [])
        try:
            selected_index = int(incoming_msg) - 1
            if 0 <= selected_index < len(options) - 1:
                scenario = options[selected_index]
                user_profiles[from_number]["scenario"] = scenario
                user_state[from_number]["stage"] = "gpt_mode"
                msg.body("Thanks for sharing that. I’m here for you 💛 Just tell me a bit more about what’s been going on, and we’ll work through it together.")
            elif selected_index == len(options) - 1:
                user_state[from_number]["stage"] = "gpt_mode_custom"
                msg.body("No problem — just type out what’s going on and I’ll do my best to help 💬")
            else:
                msg.body("Please choose a valid number from the list.")
        except Exception as e:
            print("[ERROR in choose_scenario]", str(e))
            msg.body("Please reply with the number of your choice.")
        return str(response)

    if state.get("stage") == "assessment" and from_number in user_sessions:
        handle_assessment_answer(from_number, incoming_msg)
        next_q = get_next_assessment_question(from_number)
        if next_q:
            msg.body(next_q)
        else:
            scores = calculate_trait_scores(user_sessions[from_number]["answers"])
            identity = assign_identity(scores)
            feedback = generate_feedback(scores, identity)
    
            # ✅ Offer next options after feedback
            msg.body(
                feedback + 
                "\n\nWhat would you like to do next?\n1. Get advice\n2. Restart"
            )
            del user_sessions[from_number]
    
            # ✅ Reset stage so they can choose what's next
            user_state[from_number]["stage"] = "choose_path"
        return str(response)


    if state["stage"] in ["gpt_mode", "gpt_mode_custom"]:
        scenario = user_profiles.get(from_number, {}).get("scenario", "").strip()
        user_input = incoming_msg.strip()
    
        if state["stage"] == "gpt_mode_custom":
            scenario = user_input
    
        if not scenario:
            msg.body("Hmm, I didn’t quite catch that. Can you describe what’s going on again?")
            return str(response)
    
        if not user_input:
            msg.body("Could you tell me a bit more about what's happening so I can help?")
            return str(response)
            
        # ✅ Check relevance
        if not is_relevant(user_input):
            msg.body("I'm here for you 💛 Could you share a little more about what’s happening so I can support you better?")
            return str(response)
    
        # ✅ Initialize conversation step if not already set
        if "current_step" not in user_state[from_number]:
            user_state[from_number]["current_step"] = "validation_exploration"
        
        current_step = user_state[from_number]["current_step"]
        if "free_chat_mode" not in user_state[from_number]:
            user_state[from_number]["free_chat_mode"] = False

        free_chat_mode = user_state[from_number]["free_chat_mode"]

        # ✅ Add Intent Detection HERE
        def detect_intent(user_input):
            lowered = user_input.lower()
            if any(phrase in lowered for phrase in ["help me", "craft a message", "write a message", "what should i say", "how should i say it"]):
                return "wants_message_help"
            if any(phrase in lowered for phrase in ["advice", "what should i do", "what would you do", "can you advise"]):
                return "wants_advice"
            if any(phrase in lowered for phrase in ["i feel", "it hurts", "i'm sad", "i'm mad", "i'm confused", "i'm upset"]):
                return "emotional_venting"
            return "normal"

        intent = detect_intent(user_input)

        if not free_chat_mode:
            if intent == "wants_message_help":
                user_state[from_number]["current_step"] = "drafting_message"
            elif intent == "wants_advice" and current_step not in ["psychoeducation", "empowerment", "drafting_message", "closing"]:
                user_state[from_number]["current_step"] = "psychoeducation"
            elif intent == "emotional_venting" and current_step != "validation_exploration":
                user_state[from_number]["current_step"] = "validation_exploration"
        
        # ✅ After message help or drafting, move to free chat
        if user_state[from_number]["current_step"] in ["offer_message_help", "drafting_message", "closing"]:
            user_state[from_number]["free_chat_mode"] = True
            free_chat_mode = True
        
        # ✅ Build prompt based on the current step
        prompt = generate_prompt(current_step, scenario, user_input)
        
        try:
            gpt_response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": ALLYAI_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            reply = gpt_response.choices[0].message.content.strip()
            msg.body(reply)
        
            # ✅ After GPT reply, move to next step
            update_user_step(from_number)
        
        except Exception as e:
            print("[ERROR in GPT fallback]", str(e))
            msg.body("Something went wrong while generating a response. Please try again or type 'restart' to start over.")
        
        return str(response)



