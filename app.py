import os
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)

API_KEY = os.environ.get("OPENAI_API_KEY")

if API_KEY:
    print("API KEY: OK")
else:
    print("API KEY: NOT FOUND")

client = OpenAI(
    api_key=API_KEY,
    base_url="https://llm.thesparkdaily.com/v1"
)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({
        "status": "online",
        "api_key": bool(API_KEY),
        "endpoint": "https://llm.thesparkdaily.com/v1"
    })


@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        message = data.get("message", "").strip()

        if not message:
            return jsonify({
                "error": "Chưa nhập tin nhắn."
            }), 400

        response = client.chat.completions.create(
            model="GPT-5.4-MINI",
            messages=[
                {
                    "role": "user",
                    "content": message
                }
            ]
        )

        reply = response.choices[0].message.content

        return jsonify({
            "reply": reply
        })

    except Exception as e:
        print("CHAT ERROR:", repr(e))

        return jsonify({
            "error": str(e)
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port
    )
