# main.py
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from guardrail import launch_guardrail_check
from flask_cors import CORS
from openai import OpenAI
from analytics import init_db, log_event, create_or_update_user, get_user_profile
import os
import json

# --- Imports from helpers and assessment (moved out of this file) ---
from helpers import (
    ALLYAI_SYSTEM_PROMPT,
    is_relevant,
    update_user_step,
    generate_prompt,
    detect_intent,
)
from assessment import (
    assessment_questions,
    get_next_assessment_question,
    handle_assessment_answer,
    calculate_trait_scores,
    assign_identity,
    generate_feedback,
)

# Load all scenario scripts from JSON
with open("scenarios.json", "r", encoding="utf-8") as f:
    SCENARIOS = json.load(f)

app = Flask(__name__)
CORS(app)

# Initialize DB (only once when app starts)
try:
    init_db()
except Exception as e:
    print(f"DB Init failed: {e}")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE_DIR, "tracks.json"), "r", encoding="utf-8") as f:
    TRACKS = json.load(f)

# Track user states
user_state = {}
user_profiles = {}
user_sessions = {}

# OpenAI client
client = OpenAI()

# WhatsApp bot route
@app.route("/bot", methods=["POST"])
def bot():
    from_number = request.values.get("From")
    incoming_msg = request.values.get("Body", "").strip()
    log_event(from_number, "message_received", {
        "input": incoming_msg,
        "stage": user_state.get(from_number, {}).get("stage", "unknown")
    })

    response = MessagingResponse()
    msg = response.message()

    # ✅ Restart handling
    if incoming_msg.lower() == "restart":
        log_event(from_number, "user_restarted", {})

        # Reset in-memory state
        user_state[from_number] = {"stage": "choose_path"}
        user_sessions.pop(from_number, None)  # clear any unfinished assessments

        # Fetch saved name from DB
        profile = get_user_profile(from_number)
        if profile and profile.get("name"):
            msg.body(
                f"Hi {profile['name']} 👋 Starting fresh!\n\n"
                "How can I help you today?\n"
                "1. Ask for advice\n"
                "2. Take a quick assessment\n"
                "3. Play 'What Would You Do?'"
            )
        else:
            msg.body("Let's start over. 👋 What’s your name?")

        return str(response)

    print(f"📲 from_number = {from_number}")
    print(f"📥 incoming_msg = {incoming_msg}")

    if not from_number or from_number.strip() == "":
        msg.body("Oops — I couldn’t detect your phone number. Try again later.")
        return str(response)

    if from_number not in user_state:
        profile = get_user_profile(from_number)
        if profile and profile.get("name"):
            # Returning user with a saved name
            msg.body(
                f"Hi {profile['name']} 👋 Welcome back! 💛\n\n"
                "How can I help you today?\n"
                "1. Ask for advice\n"
                "2. Take a quick assessment\n"
                "3. Play 'What Would You Do?'"
            )
            user_state[from_number] = {"stage": "choose_path"}
            return str(response)
        else:
            # New user
            log_event(from_number, "user_started_session", {})
            print("🆕 New user detected:", from_number)
            user_state[from_number] = {"stage": "intro"}
            user_profiles[from_number] = {}
            msg.body("Hi, I'm Ally 👋\nI'm here to support you in understanding your relationships and yourself better.\n\nWhat’s your name?")
            return str(response)

    # ✅ Fallback if stage is missing
    if "stage" not in user_state[from_number]:
        user_state[from_number]["stage"] = "intro"
        msg.body("Hi, I'm Ally 👋\nWhat’s your name?")
        return str(response)

    state = user_state[from_number]

    # ✅ Only respond to name once during intro
    if state["stage"] == "intro":
        profile = get_user_profile(from_number)
        if not profile or not profile.get("name"):
            name = incoming_msg.title()
            # ✅ Save directly to DB
            create_or_update_user(from_number, name=name)
            user_state[from_number]["stage"] = "choose_path"
            msg.body(
                f"Nice to meet you, {name}!\n\nHow can I help you today?\n"
                "1. Ask for advice\n"
                "2. Take a quick assessment to understand your relationship style\n"
                "3. Play 'What Would You Do?'"
            )
        else:
            # Prevent weird behavior if they say "Hi" again
            msg.body(
                "Just reply with 1, 2, or 3 to continue:\n"
                "1. Ask for advice\n"
                "2. Take a quick assessment\n"
                "3. Play 'What Would You Do?'"
            )
        return str(response)

    if state["stage"] == "choose_path":
        if incoming_msg == "1":
            user_state[from_number]["stage"] = "choose_category"
            msg.body("Choose a topic you want to talk about:\n1. Romantic Partner Issues\n2. Friendship Challenges\n3. Family Tensions\n4. Building Self-Confidence\n5. Overcoming Insecurity\n6. Urgent Advice")
        elif incoming_msg == "2":
            user_sessions[from_number] = {"current_q": 0, "answers": []}
            user_state[from_number]["stage"] = "assessment"
            first_q = get_next_assessment_question(user_sessions, from_number)
            msg.body("Let’s begin! ✨\n\n" + first_q)
            log_event(from_number, "assessment_started", {})
        elif incoming_msg == "3":
            profile = get_user_profile(from_number)
            track = profile.get("chosen_track")
            day = profile.get("current_day", 1)
            points = profile.get("points", 0)
            TOTAL_DAYS = 4

            if track and day > TOTAL_DAYS:
                # ✅ Finished all lessons
                msg.body(
                    f"🎉 You’ve already completed all {TOTAL_DAYS} lessons in *{track}*! 💛\n"
                    f"Final Score: {points} points 🎯\n\n"
                    "Back to the main menu:\n"
                    "1. Ask for advice\n"
                    "2. Take a quick assessment\n"
                    "3. Play 'What Would You Do?'"
                )
                user_state[from_number]["stage"] = "choose_path"

            elif track and day <= TOTAL_DAYS:
                # ✅ Already in progress
                msg.body(
                    f"✨ You’re currently on *Day {day}* of the *{track}* track.\n\n"
                    "What would you like to do?\n"
                    "1. Continue to your next lesson\n"
                    "2. Back to main menu"
                )
                user_state[from_number]["stage"] = "track_progress_options"

            else:
                # ✅ No track chosen yet
                user_state[from_number]["stage"] = "choose_track"
                msg.body(
                    "🎲 Welcome to *What Would You Do?*\n\n"
                    "Pick a growth path:\n"
                    "1. Building Confidence\n"
                    "2. Recognizing Red Flags\n"
                    "3. Setting Boundaries & Saying No"
                )

            return str(response)
        else:
            msg.body("Please reply with 1, 2, or 3.")
        return str(response)

    if state["stage"] == "choose_track":
        track_map = {
            "1": "Building Confidence",
            "2": "Recognizing Red Flags",
            "3": "Setting Boundaries & Saying No"
        }
        selected = track_map.get(incoming_msg)
        if selected and selected in TRACKS and len(TRACKS[selected]) > 0:
            # ✅ Save progress directly to DB
            create_or_update_user(
                from_number,
                chosen_track=selected,
                current_day=1,
                points=0,
                streak=0
            )

            # Load Day 1 lesson
            day_data = TRACKS[selected][0]
            options_text = "\n".join([f"{opt}) {text}" for opt, text in day_data["options"].items()])

            msg.body(
                f"🎯 You chose *{selected}*!\n\n"
                f"📘 Day 1 — {day_data['scenario']}\n\n"
                f"{options_text}\n\n"
                "👉 Reply with A, B, or C"
            )
            user_state[from_number]["stage"] = "track_active"
        else:
            msg.body("Please choose a valid track: 1, 2, or 3.")
        return str(response)

    if state["stage"] == "track_progress_options":
        profile = get_user_profile(from_number)
        track = profile.get("chosen_track")
        day = profile.get("current_day", 1)
        points = profile.get("points", 0)

        if incoming_msg == "1":  # Go to next lesson
            TOTAL_DAYS = 4
            if day <= TOTAL_DAYS:
                lesson = TRACKS[track][day-1]
                title = lesson.get("title", lesson["scenario"])

                msg.body(
                    f"📘 Day {day}: {title}\n\n"
                    f"{lesson['scenario']}\n\n"
                    f"A) {lesson['options']['A']}\n"
                    f"B) {lesson['options']['B']}\n"
                    f"C) {lesson['options']['C']}\n\n"
                    "👉 Reply with A, B, or C"
                )
                user_state[from_number]["stage"] = "track_active"
            else:
                msg.body(
                    f"🎉 You’ve already completed all {TOTAL_DAYS} lessons! 💛\n"
                    f"Final Score: {points} points 🎯\n\n"
                    "Back to the main menu:\n"
                    "1. Ask for advice\n"
                    "2. Take a quick assessment\n"
                    "3. Play 'What Would You Do?'"
                )
                user_state[from_number]["stage"] = "choose_path"

        elif incoming_msg == "2":  # Back to main menu
            msg.body(
                "Okay 💛 Sending you back to the main menu!\n\n"
                "1. Ask for advice\n"
                "2. Take a quick assessment\n"
                "3. Play 'What Would You Do?'"
            )
            user_state[from_number]["stage"] = "choose_path"

        else:
            msg.body("Please reply with 1 or 2.")

        return str(response)

    if state["stage"] == "track_active":
        profile = get_user_profile(from_number)
        track = profile.get("chosen_track")
        day = profile.get("current_day", 1)
        points = profile.get("points", 0)

        # Fetch the lesson
        lesson = TRACKS[track][day-1]

        choice = incoming_msg.strip().upper()
        if choice not in ["A", "B", "C"]:
            msg.body("Please reply with A, B, or C.")
            return str(response)

        # Award points
        points += 10
        feedback = lesson["feedback"][choice]

        # Update DB progress
        next_day = day + 1
        create_or_update_user(
            from_number,
            chosen_track=track,
            current_day=next_day,
            points=points
        )

        TOTAL_DAYS = 4
        if next_day <= TOTAL_DAYS:
            msg.body(
                f"💡 Feedback:\n{feedback}\n\n"
                f"📘 Mini Lesson:\n{lesson['mini_lesson']}\n\n"
                f"🔥 Challenge:\n{lesson['challenge']}\n\n"
                f"🏆 You earned +10 points! (Total: {points})\n\n"
                "✨ What would you like to do?\n"
                "1. Go to the next lesson\n"
                "2. Back to the main menu"
            )
            user_state[from_number]["stage"] = "track_progress_options"
        else:
            msg.body(
                f"💡 Feedback:\n{feedback}\n\n"
                f"📘 Mini Lesson:\n{lesson['mini_lesson']}\n\n"
                f"🔥 Challenge:\n{lesson['challenge']}\n\n"
                f"🏆 You earned +10 points! (Final: {points})\n\n"
                f"🎉 Congratulations! You’ve completed all lessons in this track! 💛\n\n"
                "Back to the main menu:\n"
                "1. Ask for advice\n"
                "2. Take a quick assessment\n"
                "3. Play 'What Would You Do?'"
            )
            user_state[from_number]["stage"] = "choose_path"

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
            # ✅ only save in memory, don’t push to DB
            user_state[from_number]["category"] = selected

            user_state[from_number]["stage"] = "choose_scenario"

            options = [s["scenario"] for s in SCENARIOS if s["category"] == selected]
            options.append("Something else — I want to describe my situation in my own words.")

            user_state[from_number]["scenario_options"] = options
            option_text = "\n".join([f"{i+1}. {s}" for i, s in enumerate(options)])
            msg.body(
                f"Thanks! Here are some common situations under *{selected}*:\n\n"
                f"{option_text}\n\n"
                "Reply with the number that fits your situation."
            )
            log_event(from_number, "category_selected", {"category": selected})
        else:
            msg.body("Please choose a valid number from the list above.")
        return str(response)

    if state["stage"] == "choose_scenario":
        options = user_state[from_number].get("scenario_options", [])
        try:
            selected_index = int(incoming_msg) - 1
            if 0 <= selected_index < len(options) - 1:
                scenario = options[selected_index]

                # ✅ Save only in memory, not DB
                user_state[from_number]["scenario"] = scenario
                user_state[from_number]["stage"] = "gpt_mode"

                log_event(from_number, "scenario_selected", {
                    "category": user_state[from_number].get("category"),
                    "scenario": scenario
                })

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
        session = user_sessions[from_number]
        q_index = session["current_q"]  # get current question index BEFORE it's incremented

        log_event(from_number, "assessment_answered", {
            "question": assessment_questions[q_index]["text"],
            "answer": incoming_msg
        })
        handle_assessment_answer(user_sessions, from_number, incoming_msg)
        next_q = get_next_assessment_question(user_sessions, from_number)
        if next_q:
            msg.body(next_q)
        else:
            scores = calculate_trait_scores(user_sessions[from_number]["answers"])
            identity = assign_identity(scores)
            feedback = generate_feedback(scores, identity)
            log_event(from_number, "assessment_completed", {
                "scores": scores,
                "identity": identity
            })

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
        scenario = user_state[from_number].get("scenario", "").strip()
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
        if "free_chat_mode" not in user_state[from_number]:
            user_state[from_number]["free_chat_mode"] = False

        current_step = user_state[from_number]["current_step"]
        free_chat_mode = user_state[from_number]["free_chat_mode"]

        # ✅ Intent detection (from helpers)
        intent = detect_intent(user_input)
        log_event(from_number, "gpt_step", {
            "step": user_state[from_number]["current_step"],
            "intent": intent,
            "input": user_input
        })

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
            log_event(from_number, "gpt_reply_sent", {
                "step": current_step,
                "reply": reply
            })

            # ✅ After GPT reply, move to next step
            update_user_step(user_state, from_number)

        except Exception as e:
            print("[ERROR in GPT fallback]", str(e))
            msg.body("Something went wrong while generating a response. Please try again or type 'restart' to start over.")

        # ✅ Launch guardrail check in background
        history = user_state[from_number].get("history", [])
        history.append(f"User: {user_input}")
        user_state[from_number]["history"] = history

        launch_guardrail_check(from_number, history, user_input)

        return str(response)

    # default
    msg.body("Let’s start over — type 'restart'.")
    return str(response)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # fallback to 5000 if running locally
    app.run(host="0.0.0.0", port=port)
