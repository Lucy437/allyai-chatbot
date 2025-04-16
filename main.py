from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)
user_state = {}  # Tracks where each user is in the conversation
user_sessions = {}  # Tracks assessment sessions

# ------------------------- Assessment Setup ------------------------- #
assessment_questions = [
    {
        "id": 1,
        "text": "You just got invited to speak briefly at your school or group meeting about a topic you’re passionate about. What’s your first reaction?",
        "dimension": "Confidence",
        "options": {"a": 1, "b": 2, "c": 3, "d": 4}
    },
    {
        "id": 2,
        "text": "Your friend is upset because she feels left out after you spent more time with another group. She brings it up to you. How do you respond?",
        "dimension": "Empathy",
        "options": {"a": 1, "b": 2, "c": 3, "d": 4}
    },
    {
        "id": 3,
        "text": "After a fight with someone close to you, how do you usually reflect on it?",
        "dimension": "Self-Awareness",
        "options": {"a": 1, "b": 2, "c": 3, "d": 4}
    },
    {
        "id": 4,
        "text": "You’re dating someone who often makes jokes at your expense in front of others. How do you respond?",
        "dimension": "Self-Respect",
        "options": {"a": 1, "b": 2, "c": 3, "d": 4}
    },
    {
        "id": 5,
        "text": "A classmate or coworker takes credit for your idea in a group project. What do you do?",
        "dimension": "Communication",
        "options": {"a": 1, "b": 2, "c": 3, "d": 4}
    },
    {
        "id": 6,
        "text": "A friend constantly calls late at night to vent, even when you’ve told them you’re tired or studying. What do you do?",
        "dimension": "Boundary-Setting",
        "options": {"a": 1, "b": 2, "c": 3, "d": 4}
    }
]

def get_next_assessment_question(user_id):
    session = user_sessions[user_id]
    q_index = session["current_q"]
    if q_index < len(assessment_questions):
        q = assessment_questions[q_index]
        return f"{q['text']}\nA. ...\nB. ...\nC. ...\nD. ..."
    return None

def handle_assessment_answer(user_id, answer_letter):
    session = user_sessions[user_id]
    q_index = session["current_q"]
    q = assessment_questions[q_index]
    score = q["options"].get(answer_letter.lower(), 0)
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
        frozenset(["Confidence", "Communication"]): "The Empowered Queen",
        frozenset(["Self-Awareness", "Empathy"]): "The Healer Oracle",
        frozenset(["Boundary-Setting", "Self-Respect"]): "The Guardian Queen",
    }
    return identity_map.get(combo, "The Growth Explorer")

def generate_feedback(scores, identity):
    bars = "\n".join([f"{trait}: {int(score * 25)}%" for trait, score in scores.items()])
    weakest_trait = min(scores, key=scores.get)
    return (
        f"🌟 Your AllyAI Identity: *{identity}*\n\n"
        f"Here’s your growth profile:\n{bars}\n\n"
        f"You’re strongest in {max(scores, key=scores.get)}.\n"
        f"But we’ll also work on your {weakest_trait} — because that’s how you become unstoppable 💫"
    )

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

    msg.body("If you'd like to start again, type 'restart'.")
    return str(response)
