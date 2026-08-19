import os
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)

API_KEY = os.environ.get("OPENAI_API_KEY")

MODELS = [
    "google/gemma-4-31b-it:free",
    "openai/gpt-oss-20b:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "openrouter/free"
]

if API_KEY:
    print("OPENROUTER API KEY: OK")

    client = OpenAI(
        api_key=API_KEY,
        base_url="https://openrouter.ai/api/v1",
        timeout=45.0,
        max_retries=0
    )
else:
    print("ERROR: OPENAI_API_KEY chưa được thiết lập.")
    client = None


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

    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()

    if not message:
        return jsonify({
            "error": "Bạn chưa nhập tin nhắn."
        }), 400

    errors = []

    for model in MODELS:
        try:
            print("Trying model:", model)

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": message
                    }
                ],
                temperature=0.7
            )

            reply = response.choices[0].message.content

            if reply:
                print("SUCCESS:", model)

                return jsonify({
                    "reply": reply,
                    "model": model
                })

        except Exception as e:
            error_text = str(e)
            print("MODEL ERROR:", model, error_text)
            errors.append(f"{model}: {error_text}")

            # thử model free tiếp theo
            continue

    return jsonify({
        "error": "Tất cả model miễn phí hiện đều không phản hồi.",
        "details": errors
    }), 502


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port
    )
