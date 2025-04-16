import os
from flask import Flask, request, jsonify, render_template, redirect
from dotenv import load_dotenv
import requests
import firebase_admin
from firebase_admin import credentials, firestore, auth

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__, template_folder="templates", static_folder="static")

# Firebase credentials and initialization
cred = credentials.Certificate("serviceAccount.json")
firebase_admin.initialize_app(cred)
db = firestore.client()
convo_collection = db.collection("conversations")

# ------------------------ Core Logic ------------------------

def choose_model(message=None, is_image=False):
    if is_image:
        return "llama-3.2-90b-vision-preview"
    if message:
        msg = message.lower()
        if any(x in msg for x in ["prove", "derive", "explain", "why", "therefore", "if", "then", "analyze"]):
            return "deepseek-r1-distill-llama-70b"
        elif len(message.split()) > 100 or any(x in msg for x in ["essay", "write a story", "long"]):
            return "meta-llama/llama-4-maverick-17b-128e-instruct"
        elif any(x in msg for x in ["code", "debug", "python", "function", "algorithm", "compile", "error"]):
            return "mistral-saba-24b"
    return "llama3-70b-8192"

def load_conversation(user_id, name):
    doc = convo_collection.document(user_id).collection("chats").document(name).get()
    return doc.to_dict().get("messages", []) if doc.exists else []

def save_conversation(user_id, name, messages):
    convo_collection.document(user_id).collection("chats").document(name).set({"messages": messages})

def delete_conversation(user_id, name):
    convo_collection.document(user_id).collection("chats").document(name).delete()

def list_all_chats(user_id):
    return [doc.id for doc in convo_collection.document(user_id).collection("chats").stream()]

def query_groq(messages, is_image=False, image_data=None):
    user_message = messages[-1]["content"] if messages else ""
    model = choose_model(message=user_message, is_image=is_image)

    headers = {
        "Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}",
        "Content-Type": "application/json"
    }

    if is_image and image_data:
        data = {
            "model": model,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": user_message},
                    {"type": "image_url", "image_url": {"url": image_data}}
                ]
            }]
        }
    else:
        data = {
            "model": model,
            "messages": [{"role": "user", "content": user_message}]
        }

    try:
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.HTTPError as e:
        print("Groq API error:", e.response.text)
        return f"Error: {e.response.text}"

def verify_token(id_token):
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token['uid']
    except Exception as e:
        print(f"Token verification failed: {e}")
        return None

# ------------------------ Routes ------------------------

@app.route("/")
def index():
    user_id = request.cookies.get('user_id')
    if not user_id:
        return redirect("/login")
    return render_template("index.html")

@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/api/login", methods=["POST"])
def login():
    id_token = request.json.get("id_token")
    user_id = verify_token(id_token)

    if user_id is None:
        return jsonify({"error": "Invalid token"}), 401

    response = jsonify({"message": f"Logged in as {user_id}", "user_id": user_id})
    response.set_cookie('user_id', user_id, httponly=True)
    return response

@app.route("/api/chat", methods=["POST"])
def create_chat():
    user_id = request.cookies.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    chat_name = data.get("chat_name")
    user_message = data.get("message")
    image_url = data.get("image_url", None)

    if not chat_name or not user_message:
        return jsonify({"error": "Chat name and message required"}), 400

    existing_messages = load_conversation(user_id, chat_name)
    existing_messages.append({"role": "user", "content": user_message})

    ai_response = query_groq(existing_messages, is_image=bool(image_url), image_data=image_url)
    existing_messages.append({"role": "assistant", "content": ai_response})

    save_conversation(user_id, chat_name, existing_messages)

    return jsonify({"response": ai_response})

@app.route("/api/chats", methods=["GET"])
def list_chats():
    user_id = request.cookies.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    chat_names = list_all_chats(user_id)
    return jsonify({"chats": chat_names})

# ------------------------ Main Entry --------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)

