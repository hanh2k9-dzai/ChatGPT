import os
import uuid
import base64
from pathlib import Path

from flask import Flask, render_template, request, jsonify, session
from openai import OpenAI

app = Flask(__name__)

# =========================================================
# CONFIG
# =========================================================

app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "change-this-secret-key"
)

API_KEY = os.environ.get("OPENAI_API_KEY")

BASE_URL = "https://openrouter.ai/api/v1"

# Các model free được thử lần lượt.
MODELS = [
    "google/gemma-4-31b-it:free",
    "openai/gpt-oss-20b:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "openrouter/free"
]

MAX_HISTORY = 20

# Giới hạn kích thước upload: 10 MB
MAX_FILE_SIZE = 10 * 1024 * 1024

app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE


# =========================================================
# OPENROUTER CLIENT
# =========================================================

if API_KEY:
    print("OPENROUTER API KEY: OK")

    client = OpenAI(
        api_key=API_KEY,
        base_url=BASE_URL,
        timeout=45.0,
        max_retries=0
    )
else:
    print("ERROR: OPENAI_API_KEY chưa được thiết lập.")
    client = None


# =========================================================
# SESSION / CHAT HISTORY
# =========================================================

def get_history():
    """
    Lấy lịch sử chat của phiên hiện tại.
    """
    if "history" not in session:
        session["history"] = []

    return session["history"]


def save_history(history):
    """
    Lưu lịch sử vào session.
    """
    session["history"] = history[-MAX_HISTORY:]
    session.modified = True


def clear_history():
    session["history"] = []
    session.modified = True


# =========================================================
# BASIC ROUTES
# =========================================================

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({
        "status": "online",
        "api_key_configured": bool(API_KEY),
        "provider": "OpenRouter",
        "models": MODELS
    })


# =========================================================
# CHAT
# =========================================================

@app.route("/chat", methods=["POST"])
def chat():

    if client is None:
        return jsonify({
            "error": "OPENAI_API_KEY chưa được cấu hình trên Render."
        }), 500

    try:
        data = request.get_json(silent=True) or {}

        message = str(
            data.get("message", "")
        ).strip()

        if not message:
            return jsonify({
                "error": "Bạn chưa nhập tin nhắn."
            }), 400

        history = get_history()

        # Thêm tin nhắn người dùng
        history.append({
            "role": "user",
            "content": message
        })

        # Giới hạn lịch sử
        history = history[-MAX_HISTORY:]

        errors = []

        # -------------------------------------------------
        # Thử lần lượt các model
        # -------------------------------------------------

        for model in MODELS:

            try:
                print("Trying model:", model)

                response = client.chat.completions.create(
                    model=model,
                    messages=history,
                    temperature=0.7
                )

                reply = response.choices[0].message.content

                if not reply:
                    raise Exception(
                        "Model không trả về nội dung."
                    )

                # Lưu câu trả lời
                history.append({
                    "role": "assistant",
                    "content": reply
                })

                save_history(history)

                print("SUCCESS:", model)

                return jsonify({
                    "reply": reply,
                    "model": model
                })

            except Exception as e:

                error_text = str(e)

                print(
                    "MODEL ERROR:",
                    model,
                    error_text
                )

                errors.append({
                    "model": model,
                    "error": error_text
                })

                continue

        # Không model nào hoạt động
        # Xóa message cuối để tránh lịch sử bị lệch
        if history and history[-1]["role"] == "user":
            history.pop()

        save_history(history)

        return jsonify({
            "error": "Các model miễn phí hiện đều không phản hồi.",
            "details": errors
        }), 502

    except Exception as e:

        print(
            "CHAT ERROR:",
            repr(e)
        )

        return jsonify({
            "error": str(e)
        }), 500


# =========================================================
# CLEAR CHAT
# =========================================================

@app.route("/clear", methods=["POST"])
def clear_chat():

    clear_history()

    return jsonify({
        "success": True,
        "message": "Đã xóa lịch sử trò chuyện."
    })


# =========================================================
# GET CHAT HISTORY
# =========================================================

@app.route("/history", methods=["GET"])
def history():

    return jsonify({
        "history": get_history()
    })


# =========================================================
# IMAGE / FILE CHAT
# =========================================================

@app.route("/upload", methods=["POST"])
def upload():

    if client is None:
        return jsonify({
            "error": "OPENAI_API_KEY chưa được cấu hình."
        }), 500

    try:

        message = request.form.get(
            "message",
            ""
        ).strip()

        uploaded_file = request.files.get("file")

        if uploaded_file is None:

            return jsonify({
                "error": "Không tìm thấy file."
            }), 400

        filename = uploaded_file.filename or "file"

        extension = Path(filename).suffix.lower()

        # -------------------------------------------------
        # ẢNH
        # -------------------------------------------------

        image_extensions = {
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
            ".gif"
        }

        if extension in image_extensions:

            image_bytes = uploaded_file.read()

            if not image_bytes:
                return jsonify({
                    "error": "Ảnh rỗng."
                }), 400

            encoded = base64.b64encode(
                image_bytes
            ).decode("utf-8")

            mime_types = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".webp": "image/webp",
                ".gif": "image/gif"
            }

            mime = mime_types.get(
                extension,
                "image/jpeg"
            )

            prompt = message or (
                "Hãy phân tích hình ảnh này và "
                "mô tả những gì bạn nhìn thấy."
            )

            content = [
                {
                    "type": "text",
                    "text": prompt
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": (
                            f"data:{mime};base64,"
                            f"{encoded}"
                        )
                    }
                }
            ]

            history = get_history()

            # Với ảnh, dùng riêng message hiện tại.
            image_messages = [
                {
                    "role": "user",
                    "content": content
                }
            ]

            errors = []

            for model in MODELS:

                try:

                    print(
                        "Trying image model:",
                        model
                    )

                    response = (
                        client.chat.completions.create(
                            model=model,
                            messages=image_messages,
                            temperature=0.7
                        )
                    )

                    reply = (
                        response
                        .choices[0]
                        .message
                        .content
                    )

                    if not reply:
                        raise Exception(
                            "Model không trả lời ảnh."
                        )

                    # Lưu dạng text vào history
                    history.append({
                        "role": "user",
                        "content": (
                            f"[Đã gửi ảnh: {filename}] "
                            f"{prompt}"
                        )
                    })

                    history.append({
                        "role": "assistant",
                        "content": reply
                    })

                    save_history(history)

                    return jsonify({
                        "reply": reply,
                        "filename": filename,
                        "model": model
                    })

                except Exception as e:

                    print(
                        "IMAGE ERROR:",
                        model,
                        str(e)
                    )

                    errors.append({
                        "model": model,
                        "error": str(e)
                    })

                    continue

            return jsonify({
                "error": (
                    "Không có model miễn phí nào "
                    "hiện hỗ trợ ảnh."
                ),
                "details": errors
            }), 502

        # -------------------------------------------------
        # FILE TEXT
        # -------------------------------------------------

        text_extensions = {
            ".txt",
            ".md",
            ".csv",
            ".json",
            ".py",
            ".js",
            ".html",
            ".css"
        }

        if extension in text_extensions:

            raw = uploaded_file.read()

            try:
                text = raw.decode(
                    "utf-8",
                    errors="ignore"
                )
            except Exception:
                text = str(raw)

            if len(text) > 100000:
                text = text[:100000]

            prompt = message or (
                "Hãy đọc và phân tích file này."
            )

            combined = (
                f"{prompt}\n\n"
                f"--- FILE: {filename} ---\n"
                f"{text}"
            )

            history = get_history()

            history.append({
                "role": "user",
                "content": combined
            })

            errors = []

            for model in MODELS:

                try:

                    response = (
                        client
                        .chat
                        .completions
                        .create(
                            model=model,
                            messages=history[-MAX_HISTORY:],
                            temperature=0.7
                        )
                    )

                    reply = (
                        response
                        .choices[0]
                        .message
                        .content
                    )

                    if not reply:
                        raise Exception(
                            "Model không trả lời file."
                        )

                    history.append({
                        "role": "assistant",
                        "content": reply
                    })

                    save_history(history)

                    return jsonify({
                        "reply": reply,
                        "filename": filename,
                        "model": model
                    })

                except Exception as e:

                    print(
                        "FILE ERROR:",
                        model,
                        str(e)
                    )

                    errors.append({
                        "model": model,
                        "error": str(e)
                    })

                    continue

            # Xóa message file nếu thất bại
            if history and history[-1]["role"] == "user":
                history.pop()

            save_history(history)

            return jsonify({
                "error": "Không thể xử lý file.",
                "details": errors
            }), 502

        # -------------------------------------------------
        # FILE KHÔNG HỖ TRỢ
        # -------------------------------------------------

        return jsonify({
            "error": (
                f"Định dạng {extension or 'này'} "
                "chưa được hỗ trợ."
            )
        }), 400

    except Exception as e:

        print(
            "UPLOAD ERROR:",
            repr(e)
        )

        return jsonify({
            "error": str(e)
        }), 500


# =========================================================
# FILE SIZE ERROR
# =========================================================

@app.errorhandler(413)
def too_large(error):

    return jsonify({
        "error": "File quá lớn. Tối đa 10 MB."
    }), 413


# =========================================================
# 404
# =========================================================

@app.errorhandler(404)
def not_found(error):

    return jsonify({
        "error": "Không tìm thấy đường dẫn."
    }), 404


# =========================================================
# START SERVER
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
