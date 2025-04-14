from flask import Flask, request, session
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)
app.secret_key = 'lucy-unicef-secret-key'

flows = {
    "1": {
        "messages": [
            "Thanks for sharing that. It sounds like your friend is joking about things you’re sensitive about. That’s hard, especially when it makes you feel small.\n\nDo you feel like she knows this really bothers you? (Yes / No / Not sure)",
            "When she makes those jokes, how do you usually feel — angry, embarrassed, hurt?",
            "You’re not 'too sensitive.' You’re being honest about what’s hurtful. That’s a strength.\n\nWould you like help finding the words to talk to her? (Yes / No)",
            "In a strong friendship, you should feel safe — not like you're the punchline. You deserve kindness and respect, and it’s okay to say when something crosses the line."
        ],
        "yes_response": "Here’s something you could say:\n\n“Hey, can I share something with you? Sometimes when you joke about [insert topic], it hits a sensitive spot for me. I know you probably don’t mean to hurt me, but it really affects how I feel. I value our friendship, and I’d appreciate it if we could talk about this.” 💛"
    },
    "2": {
        "messages": [
            "That kind of emotional withdrawal can be really painful. Can I ask—how do you feel when he pulls away like that?",
            "Do you think he does it to pressure you into changing your mind?",
            "That behavior is sometimes called emotional manipulation. You have the right to set boundaries.\n\nWould you like help preparing a conversation?",
            "When someone withdraws love or attention as a punishment, that’s not love. That’s control."
        ],
        "yes_response": "Here’s a message you could use to open a dialogue with your partner:\n\n“I’ve noticed that when I say no or express how I feel, there’s distance between us afterward. It leaves me feeling like I can’t speak up without losing connection. I want a relationship where we can disagree and still feel close. Can we talk about this?” 💬"
    },
    "3": {
        "messages": [
            "Thank you for being honest. Not feeling confident in groups is something so many people experience.\n\nCan I ask—what usually holds you back from speaking?",
            "Being thoughtful is a strength—but your ideas deserve to be heard. Do you sometimes feel like you need people to agree with you to feel valid?",
            "Try starting small: ask a question, share one idea. Over time, you’ll realize your presence matters, even when it’s quiet.",
            "Confidence doesn’t start with being loud. It starts with trusting that your voice deserves space."
        ],
        "yes_response": "Here’s something gentle you could say to your group of friends or classmates:\n\n“Hey, I’ve realized I often stay quiet in our group because I second-guess myself. I’m working on building confidence, and I’d love if we could create space where everyone’s voice is heard — including mine. Just wanted to share that with you.” 🌱"
    },
    "4": {
        "messages": [
            "Feeling like you have to filter yourself to keep your partner happy can be really draining.\n\nCan I ask—have you ever told him how this makes you feel?",
            "A relationship that requires you to shrink is not one that helps you grow. Do you feel like you're slowly losing yourself?",
            "In healthy relationships, both people grow together—not one shaping the other to their mold.",
            "You can love someone and still protect your identity. Let’s talk through how to express this to him if you're ready."
        ],
        "yes_response": "Here’s a gentle but assertive message you can use to begin setting a boundary:\n\n“I’ve been changing how I dress and what I say to avoid upsetting you. But lately, I feel like I’m losing parts of myself. I love being in a relationship where we support each other — not where I feel like I need to shrink. Can we talk about this?” 🌻"
    }
}

@app.route("/bot", methods=["POST"])
def bot():
    incoming_msg = request.values.get('Body', '').strip().lower()
    response = MessagingResponse()
    msg = response.message()

    if incoming_msg in ["restart", "menu", "hi", "hello"]:
        session.pop('current_flow', None)
        session.pop('step', None)

    if 'current_flow' not in session:
        if incoming_msg in flows:
            session['current_flow'] = incoming_msg
            session['step'] = 0
            msg.body(flows[incoming_msg]["messages"][0])
        else:
            msg.body(
                "Hi, I’m Ally 👋\nI’m here to help with tricky relationship and friendship situations.\n\n"
                "Choose one to begin:\n\n"
                "1️⃣ A friend keeps joking about things that hurt me\n"
                "2️⃣ My partner pulls away when I say no\n"
                "3️⃣ I don’t feel confident speaking up in groups\n"
                "4️⃣ My partner controls what I wear or say\n\n"
                "Reply with a number (1–4) to start.\n\n"
                "Type 'restart' at any time to return to the menu 💛"
            )
    else:
        flow_id = session['current_flow']
        step = session.get('step', 0)

        if incoming_msg == "yes" and step == 2:
            msg.body(flows[flow_id]["yes_response"])
            return str(response)

        step += 1
        session['step'] = step

        if step < len(flows[flow_id]["messages"]):
            msg.body(flows[flow_id]["messages"][step])
        else:
            msg.body(
                "Thank you for sharing with me 💛 If you'd like to talk about something else, just type 'restart' to see the menu again."
            )
            session.pop('current_flow', None)
            session.pop('step', None)

    return str(response)

