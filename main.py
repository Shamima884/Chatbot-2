"""Personal chatbot web app.

Runs a small Flask server on http://127.0.0.1:5000 that chats with the Groq API.
The bot's personality/knowledge comes from the MY_INFO.md file in this folder.
"""

import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from groq import Groq

load_dotenv()

app = Flask(__name__)

INFO_FILE = "MY_INFO.md"

SYSTEM_PROMPT_TEMPLATE = (
    "You are a friendly personal assistant chatbot. You answer questions about the "
    "user using the information provided below. If the information does not contain "
    "an answer, say you are not sure rather than guessing. Be concise, warm and helpful.\n\n"
    "=== USER INFORMATION ===\n"
)


def load_personal_info() -> str:
    """Read the user's personal info file, returning an empty string if it is missing."""
    try:
        with open(INFO_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""


# Groq client + model from the .env file
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# In-memory conversation history (last 20 messages = 10 turns)
HISTORY: list[dict[str, str]] = []
HISTORY_LIMIT = 20


@app.route("/")
def index():
    return render_template("index.html", personal_info=load_personal_info())


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()
    if not user_message:
        return jsonify({"error": "Message cannot be empty."}), 400

    # Build the prompt with the latest info file contents
    personal_info = load_personal_info()
    if not personal_info:
        personal_info = "(No information has been added to MY_INFO.md yet.)"
    system_prompt = SYSTEM_PROMPT_TEMPLATE + personal_info

    messages = [{"role": "system", "content": system_prompt}]
    messages += HISTORY
    messages.append({"role": "user", "content": user_message})

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=1024,
        )
        reply = response.choices[0].message.content
    except Exception as exc:  # surface any upstream error to the UI
        return jsonify({"error": f"Groq API error: {exc}"}), 502

    HISTORY.append({"role": "user", "content": user_message})
    HISTORY.append({"role": "assistant", "content": reply})
    if len(HISTORY) > HISTORY_LIMIT:
        del HISTORY[: len(HISTORY) - HISTORY_LIMIT]

    return jsonify({"reply": reply})


@app.route("/api/reset", methods=["POST"])
def reset():
    HISTORY.clear()
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
