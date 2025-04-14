from flask import Flask, request
import openai
from twilio.twiml.messaging_response import MessagingResponse

openai.api_key = "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"

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
    