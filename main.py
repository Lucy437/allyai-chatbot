from flask import Flask, request
import openai
import os
from twilio.twiml.messaging_response import MessagingResponse

openai.api_key = os.environ.get("OPENAI_API_KEY")

app = Flask(__name__)

@app.route("/bot", methods=["POST"])
def bot():
    incoming_msg = request.values.get('Body', '')
    response = MessagingResponse()
    msg = response.message()

    # AI reply using ChatGPT
    chat = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a warm, emotionally intelligent relationship coach for girls aged 16-25."},
            {"role": "user", "content": incoming_msg}
        ]
    )

    reply = chat.choices[0].message.content
    msg.body(reply)
    return str(response)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=81)
    
