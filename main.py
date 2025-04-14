from flask import Flask, request, session
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)
app.secret_key = 'lucy-unicef-secret-key'

# Structured conversation flows
flows = {
    "1": [
        "Thanks for sharing that. It sounds like your friend is joking about things you’re sensitive about. That’s hard, especially when it makes you feel small.\n\nDo you feel like she knows this really bothers you? (Yes / No / Not sure)",
        "When she makes those jokes, how do you usually feel — angry, embarrassed, hurt?",
        "You’re not 'too sensitive.' You’re being honest about what’s hurtful. That’s a strength.\n\nWould you like help finding the words to talk to her? (Yes / No)",
        "In a strong friendship, you should feel safe — not like you're the punchline. You deserve kindness and respect, and it’s okay to say when something crosses the line."
    ],
    "2": [
        "That kind of emotional withdrawal can be really painful. Can I ask—how do you feel when he pulls away like that?",
        "Do you think he does it to pressure you into changing your mind?",
        "That behavior is sometimes called emotional manipulation. You have the right to set boundaries.\n\nWould you like help preparing a conversation?",
        "When someone withdraws love or attention as a punishment, that’s not love. That’s control."
    ],
    "3": [
        "Thank you for being honest. Not feeling confident in groups is something so many people experience.\n\nCan I ask—what usually holds you back from speaking?",
        "Being thoughtful is a strength—but your ideas deserve to be heard. Do you sometimes feel like you need people to agree with you to feel valid?",
        "Try starting small: ask a question, share one idea. Over time, you’ll realize your presence matters, even when it’s quiet.",
        "Confidence doesn’t start with being loud. It starts with trusting that your voice deserves space."
    ],
    "4": [
        "Feeling like you have to filter yourself to keep your partner happy can be really draining.\n\nCan I ask—have you ever told him how this makes you feel?",
        "A relationship that requires you to shrink is not one that helps you grow. Do you feel like you're slowly losing yourself?",
        "In healthy relationships, both people grow together—not one shaping the other to their mold.",
        "You can love someone and still protect your identity. Let’s talk through how to express this to him if you're ready."
    ]
}

@app.route("/bot", methods=["POST"])
def bot():
    incoming_msg = request.values.get('Body', '').strip().lower()
    response = MessagingResponse()
    msg = response.message()

    # Allow user to restart the menu at any time
    if incoming_msg in ["restart", "menu", "hi", "hello"]:
        session.pop('current_flow', None)
        session.pop('step', None)

    # Step 1: Show the menu if no flow is started
    if 'current_flow' not in session:
        if incoming_msg in flows:
            session['current_flow'] = incoming_msg
            session['step'] = 0
            msg.body(flows[incoming_msg][0])
        else:
            msg.body(
                "Hi, I’m Ally 👋\nI’m here to help with tricky relationship and friendship situations.\n\nChoose one to begin:\n\n"
                "1️⃣ A friend keeps joking about things that hurt me\n"
                "2️⃣ My partner pulls away when I say no\n"
                "3️⃣ I don’t feel confident speaking up in groups\n"
                "4️⃣ My partner controls what I wear or say\n\n"
