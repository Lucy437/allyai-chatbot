from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)
user_state = {}  # Tracks where each user is in the conversation

# Helper functions
def get_scenarios_for_category(category):
    if category == "1":
        return ("Which situation best describes what you're going through?\n"
                "1. He ghosts me after arguments.\n"
                "2. I need permission to see friends.\n"
                "3. He likes other girls' photos online.")
    elif category == "2":
        return ("Choose a scenario:\n"
                "1. My friend jokes about my insecurities.\n"
                "2. I feel left out in group settings.")
    elif category == "3":
        return ("Choose a scenario:\n"
                "1. My family constantly comments on how I look.\n"
                "2. I feel left out because I'm not allowed on social media.")
    elif category == "4":
        return ("Choose a scenario:\n"
                "1. I'm scared to speak up in groups.\n"
                "2. I'm afraid to try new things because I might fail.")
    elif category == "5":
        return ("Choose a scenario:\n"
                "1. I don’t like how I look.\n"
                "2. I compare myself to people online and feel behind.")
    elif category == "6":
        return ("Choose a scenario:\n"
                "1. I feel very anxious and can't calm down.\n"
                "2. Nothing makes sense anymore.\n"
                "3. My boyfriend threatened me.\n"
                "4. He hit me, but said sorry.")
    else:
        return "Please enter a valid category number."

def get_flow_for_scenario(category, scenario):
    if category == "1" and scenario == "1":
        return ("That sounds so frustrating. Feeling ignored after a disagreement can really hurt — especially when you're just trying to work things out.\n\nHas this happened more than once?")
    elif category == "1" and scenario == "2":
        return ("It makes sense that you're feeling stuck. You shouldn't have to choose between your relationship and your friends.\n\nWhat does he usually say when you want to hang out with others?")
    elif category == "1" and scenario == "3":
        return ("It's totally normal to feel insecure when your partner engages with others online. You're not alone in this.\n\nHave you talked to him about how this makes you feel?")
    elif category == "2" and scenario == "1":
        return ("When someone laughs off our feelings or calls us 'too sensitive,' it can really hurt.\n\nWhat does your friend usually say that bothers you the most?")
    elif category == "2" and scenario == "2":
        return ("Feeling invisible around a close friend is painful.\n\nHas this been happening often or only in certain situations?")
    # Add more flows here as you expand
    else:
        return "Please enter a valid scenario number."

# WhatsApp webhook
@app.route("/bot", methods=["POST"])
def bot():
    incoming_msg = request.values.get('Body', '').strip().lower()
    from_number = request.values.get('From')
    response = MessagingResponse()
    msg = response.message()

    # Track user session
    if from_number not in user_state:
        user_state[from_number] = {"stage": "greeting"}

    state = user_state[from_number]

    # Step 1: Greet user and show categories
    if state["stage"] == "greeting":
        msg.body("Hi, I'm Ally 👋\nI'm here to support you.\n\nWhat do you want to talk about today?\n\n"
                 "1. Romantic Partner Issues\n"
                 "2. Friendship Challenges\n"
                 "3. Family Tensions\n"
                 "4. Building Self-Confidence\n"
                 "5. Overcoming Insecurity\n"
                 "6. Urgent Advice\n\nPlease reply with the number.")
        state["stage"] = "category"
        return str(response)

    # Step 2: Handle category selection
    elif state["stage"] == "category":
        if incoming_msg in ["1", "2", "3", "4", "5", "6"]:
            state["category"] = incoming_msg
            state["stage"] = "scenario"
            msg.body(get_scenarios_for_category(incoming_msg))
        else:
            msg.body("Please enter a number from 1 to 6 to choose a category.")
        return str(response)

    # Step 3: Handle scenario selection
    elif state["stage"] == "scenario":
        category = state["category"]
        scenario = incoming_msg
        flow = get_flow_for_scenario(category, scenario)
        if "Please enter a valid" in flow:
            msg.body(flow)
        else:
            msg.body(flow)
            state["stage"] = "completed"
        return str(response)

    # Optional reset
    elif incoming_msg == "restart":
        user_state[from_number] = {"stage": "greeting"}
        msg.body("Let's start over. 👋")
        return str(response)

    else:
        msg.body("If you'd like to start again, type 'restart'.")
        return str(response)

