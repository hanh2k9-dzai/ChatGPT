import os
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)

# Kiểm tra API key nhưng không bao giờ in key ra log
api_key = os.environ.get("OPENAI_API_KEY")

if not api_key:
    print("ERROR: OPENAI_API_KEY chưa được thiết lập trên Render.")
else:
    print("OPENAI_API_KEY: OK")

client = OpenAI(api_key=api_key) if api_key else None


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    if client is None:
        return jsonify({
            "error": "Server chưa được cấu hình OPENAI_API_KEY."
        }), 500

    try:
        data = request.get_json(silent=True) or {}
        message = str(data.get("message", "")).strip()

        if not message:
            return jsonify({
                "error": "Bạn chưa nhập tin nhắn."
            }), 400

        response = client.responses.create(
            model="gpt-5.6-luna",
            input=message
        )

        return jsonify({
            "reply": response.output_text
        })

    except Exception as e:
        print("CHAT ERROR:", str(e))

        return jsonify({
            "error": "AI gặp lỗi khi xử lý yêu cầu."
        }), 500


@app.route("/health")
def health():
    return jsonify({
        "status": "online",
        "api_key_configured": client is not None
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port
    )
