"""Chatbot web app for Tairunnessa Memorial Medical College & Hospital (TMMCH).

Runs a small Flask server on http://127.0.0.1:5000 that chats with the Groq API.
The bot's knowledge comes from the MY_INFO.md file in this folder.
"""

import os
import time

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from groq import Groq

load_dotenv()

app = Flask(__name__)

INFO_FILE = "MY_INFO.md"

SYSTEM_PROMPT_TEMPLATE = (
    "You are the official virtual assistant of Tairunnessa Memorial Medical College "
    "& Hospital (TMMCH) in Gazipur, Bangladesh. Answer user questions using only the "
    "knowledge base below.\n"
    "Rules:\n"
    "1. Keep answers SHORT: 1-3 sentences, or a brief list only when the question "
    "clearly needs one. Never write long paragraphs.\n"
    "2. Give only the final answer. Do not show reasoning, notes, explanations of "
    "how you found the information, or any meta commentary.\n"
    "3. Never mention or reveal the knowledge base, files, tools, systems, models, "
    "or APIs used to answer. If asked what you are, say only: 'I am the TMMCH "
    "virtual assistant.'\n"
    "4. Be professional, polite and helpful.\n"
    "5. If the answer is not in the knowledge base, say you don't have that "
    "information and suggest contacting the college by phone or emailing "
    "admin@tmmch.com.\n\n"
    "=== KNOWLEDGE BASE ===\n"
)


def load_knowledge_base() -> str:
    """Read the bot's knowledge file, returning an empty string if it is missing."""
    try:
        with open(INFO_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""


# Groq client is created lazily inside the request handler so the app always
# starts, even if GROQ_API_KEY is temporarily unset. Model comes from .env.
DEFAULT_MODEL = "groq/compound"

# In-memory conversation history (last 20 messages = 10 turns)
HISTORY: list[dict[str, str]] = []
HISTORY_LIMIT = 20


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()
    if not user_message:
        return jsonify({"error": "Message cannot be empty."}), 400

    # Build the prompt with the latest knowledge file contents
    knowledge_base = load_knowledge_base()
    if not knowledge_base:
        knowledge_base = "(The knowledge file MY_INFO.md is currently empty.)"
    system_prompt = SYSTEM_PROMPT_TEMPLATE + knowledge_base

    messages = [{"role": "system", "content": system_prompt}]
    messages += HISTORY
    messages.append({"role": "user", "content": user_message})

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return jsonify({"error": "GROQ_API_KEY is not set on the server."}), 500

    try:
        client = Groq(api_key=api_key)
        model = os.getenv("GROQ_MODEL") or DEFAULT_MODEL
        attempts = 0
        while True:
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.4,
                    max_tokens=500,
                )
                break
            except Exception:
                # Retry transient Groq API failures (e.g. rate limits) with backoff
                attempts += 1
                if attempts >= 3:
                    raise
                time.sleep(2**attempts)
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
