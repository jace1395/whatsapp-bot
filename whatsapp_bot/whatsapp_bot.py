import os
import time
import threading
import requests
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from google import genai
from google.genai import types

# --- SETUP ---
load_dotenv()
app = Flask(__name__)

# Configuration from Environment Variables
# (Render automatically provides these, but .env is needed for local testing)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")

# YOUR RENDER URL (For the heartbeat)
# Update this to your actual Render URL
MY_RENDER_URL = "https://jace-whatsapp-bot.onrender.com" 

# Initialize Gemini Client (New Style)
client = genai.Client(api_key=GEMINI_API_KEY)

# --- MEMORY STORAGE ---
# Dictionary to store chat history. 
# Format: { "phone_number": [message1, message2] }
# Note: On Render Free Tier, this wipes if the server restarts (every ~24h).
user_conversations = {}

# --- HEARTBEAT (Keep Alive) ---
def keep_alive():
    """Pings the server every 14 minutes to prevent Render free tier from sleeping."""
    while True:
        try:
            # Render sleeps after 15 mins of inactivity, so we ping every 14 mins (840 seconds)
            time.sleep(840) 
            response = requests.get(MY_RENDER_URL)
            print(f"❤️ Heartbeat sent. Status: {response.status_code}")
        except Exception as e:
            print(f"Heartbeat failed: {e}")

# Start the heartbeat in a background thread
threading.Thread(target=keep_alive, daemon=True).start()

# --- HELPER FUNCTIONS ---
def get_gemini_response(phone_number, user_text):
    try:
        # 1. Check for "Clear Memory" command
        if user_text.strip().lower() in ["clear", "clear chat", "forget", "reset", "restart"]:
            user_conversations[phone_number] = []
            return "🧠 Memory cleared! I have forgotten our previous conversation."

        # 2. Retrieve or Initialize History
        if phone_number not in user_conversations:
            user_conversations[phone_number] = []
        
        conversation_history = user_conversations[phone_number]

        # 3. Prepare the Model Name
        # Note: 'gemini-3-pro-preview' might not be public yet. 
        # If this fails, change it to "gemini-2.0-flash-exp" or "gemini-1.5-flash"
        model_name = "gemini-2.0-flash-lite-preview-02-05" 

        # 4. Send Chat to Gemini (History + New Message)
        # We add the new user message to the temporary list to send to AI
        current_chat = conversation_history + [
            types.Content(role="user", parts=[types.Part.from_text(text=user_text)])
        ]

        response = client.models.generate_content(
            model=model_name,
            contents=current_chat
        )

        ai_text = response.text

        # 5. Update Memory (Only if successful)
        # Add User Message
        user_conversations[phone_number].append(
            types.Content(role="user", parts=[types.Part.from_text(text=user_text)])
        )
        # Add AI Response
        user_conversations[phone_number].append(
            types.Content(role="model", parts=[types.Part.from_text(text=ai_text)])
        )

        return ai_text

    except Exception as e:
        print(f"Gemini Error: {e}")
        return "I'm having trouble connecting to my brain right now. Try again in a moment!"

def send_whatsapp_message(to_number, message_text):
    url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": message_text}
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
    except Exception as e:
        print(f"WhatsApp Send Error: {e}")

# --- FLASK ROUTES ---
@app.route("/", methods=["GET"])
def home():
    return "Jace's AI Bot is Breathing! ❤️", 200

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    # Meta verification
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    
    # Make sure this matches the password you set in Meta Dashboard
    VERIFY_TOKEN = "my_secret_password_jace" 

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Forbidden", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    
    # Basic check to see if it's a message
    try:
        if data.get("entry") and data["entry"][0].get("changes"):
            change = data["entry"][0]["changes"][0]
            if change.get("value") and change["value"].get("messages"):
                message_data = change["value"]["messages"][0]
                
                sender_phone = message_data["from"]
                user_message = message_data["text"]["body"]
                
                print(f"📩 Message from {sender_phone}: {user_message}")

                # Get AI response (with memory)
                ai_reply = get_gemini_response(sender_phone, user_message)
                
                # Send back to WhatsApp
                send_whatsapp_message(sender_phone, ai_reply)
                
    except Exception as e:
        print(f"Error processing webhook: {e}")

    return jsonify({"status": "success"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)