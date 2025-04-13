import os
import json
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import requests

load_dotenv()
app = Flask(__name__, template_folder="templates", static_folder="static")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
CONVO_DIR = "conversations"

if not os.path.exists(CONVO_DIR):
    os.makedirs(CONVO_DIR)

def get_convo_path(name):
    return os.path.join(CONVO_DIR, f"{name}.json")

def load_conversation(name):
    path = get_convo_path(name)
    return json.load(open(path)) if os.path.exists(path) else []

def save_conversation(name, messages):
    path = get_convo_path(name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(messages, f, indent=2)

def query_groq(messages):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama3-70b-8192",
        "messages": messages
    }
    response = requests.post(GROQ_API_URL, headers=headers, json=data)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

@app.route("/api/chat", methods=["POST"])
def create_chat():
    data = request.get_json()
    name = data.get("name")
    if not name:
        return jsonify({"error": "Chat name is required"}), 400

    convo = load_conversation(name)
    if convo:  # Chat already exists
        return jsonify({"error": "Chat already exists"}), 400

    save_conversation(name, [])  # Create an empty conversation
    return jsonify({"message": "Chat created successfully", "name": name})

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/chats", methods=["GET"])
def list_chats():
    return jsonify([f.replace(".json", "") for f in os.listdir(CONVO_DIR) if f.endswith(".json")])

@app.route("/api/chat/<name>", methods=["GET"])
def get_chat(name):
    return jsonify(load_conversation(name))

@app.route("/api/chat/<name>", methods=["POST"])
def send_message(name):
    user_msg = request.json.get("message")
    if not user_msg:
        return jsonify({"error": "Empty message"}), 400

    convo = load_conversation(name)
    convo.append({"role": "user", "content": user_msg})

    try:
        bot_reply = query_groq(convo)
    except Exception as e:
        bot_reply = f"Error: {e}"

    convo.append({"role": "assistant", "content": bot_reply})
    save_conversation(name, convo)
    return jsonify({"role": "assistant", "content": bot_reply})

@app.route("/conversations/<name>.json", methods=["DELETE"])
def delete_chat(name):
    path = get_convo_path(name)
    if os.path.exists(path):
        os.remove(path)
        return '', 204
    return jsonify({"error": "Chat not found"}), 404

if __name__ == "__main__":
    app.run(debug=True, port=5050)
