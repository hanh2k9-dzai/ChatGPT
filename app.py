import os
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)

API_KEY = os.environ.get("OPENAI_API_KEY")

if API_KEY:
    print("OPENROUTER API KEY: OK")
else:
    print("ERROR: OPENAI_API_KEY chưa được thiết lập.")

client = OpenAI(
    api_key=API_KEY,
    base_url="https://openrouter.ai/api/v1",
    timeout=60.0
) if API_KEY else None


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({
        "status": "online",
        "api_key_configured": bool(API_KEY),
        "provider": "OpenRouter"
    })


@app.route("/chat", methods=["POST"])
def chat():
    if client is None:
        return jsonify({
            "error": "OpenRouter API key chưa được cấu hình."
        }), 500

    try:
        data = request.get_json(silent=True) or {}
        message = str(data.get("message", "")).strip()

        if not message:
            return jsonify({
                "error": "Bạn chưa nhập tin nhắn."
            }), 400

        response = client.chat.completions.create(
            model="openrouter/free",
            messages=[
                {
                    "role": "user",
                    "content": message
                }
            ],
            temperature=0.7
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
