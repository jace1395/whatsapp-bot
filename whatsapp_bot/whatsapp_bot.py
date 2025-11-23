import os
import time
import threading
import requests
import mimetypes
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load secret .env file (for local testing only)
load_dotenv()

app = Flask(__name__)

# --- ENABLE CORS ---
CORS(app)

# --- CONFIGURATION ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
VERIFY_TOKEN = "my_secret_password_jace"

# YOUR PHONE NUMBER (To receive contact form alerts)
# Format: CountryCode + Number (No + sign)
ADMIN_PHONE_NUMBER = "919834016312" 

# Initialize Gemini Client
client = genai.Client(api_key=GEMINI_API_KEY)

# --- JACE'S BIO ---
JACE_BIO = """
You are the personal AI assistant for Jace Cadwy Henriques. 
Here is the COMPLETE profile of Jace Henriques:
- **Full Name:** Jace Cadwy Henriques
- **DOB:** April 13, 2007 (Age 18)
- **Location:** Down Mangor, Vasco, Goa, India (403802)
- **Contact:** jacehenriques07@gmail.com | +91 9834016312
- **Education:** B.Voc in Software Technology (Student ID: 2511011).
- **Score:** 90.25% in 12th Grade (HSSC).
- **Skills:** Hardware Expert (PC Builds), AI Enthusiast, Programmer.
INSTRUCTIONS:
- If User is Jace: Be concise and helpful.
- If User is Visitor: Be professional and showcase Jace's skills.
"""

# --- MEMORY STORAGE (RAM) ---
chat_memory = {}

# --- HELPER FUNCTIONS ---

def get_gemini_response(user_id, user_text):
    if "forget" in user_text.lower() or "clear chat" in user_text.lower():
        chat_memory[user_id] = []
        return "Memory cleared."

    if user_id not in chat_memory:
        chat_memory[user_id] = []

    chat_memory[user_id].append({"role": "user", "parts": [{"text": user_text}]})

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash-lite-preview-02-05", 
            config=types.GenerateContentConfig(
                system_instruction=JACE_BIO,
                temperature=0.7
            ),
            contents=chat_memory[user_id]
        )
        bot_reply = response.text
        chat_memory[user_id].append({"role": "model", "parts": [{"text": bot_reply}]})
        return bot_reply
    except Exception as e:
        print(f"Gemini Error: {e}", flush=True)
        return "I encountered an error processing that request."

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
    requests.post(url, headers=headers, json=data)

def send_whatsapp_document(to_number, media_id, filename, caption):
    """Sends a file (document) via WhatsApp"""
    url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "document",
        "document": {
            "id": media_id,
            "caption": caption,
            "filename": filename
        }
    }
    requests.post(url, headers=headers, json=data)

def upload_media_to_whatsapp(file_data, mime_type):
    """Uploads raw file bytes to WhatsApp servers and gets an ID"""
    url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/media"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}"
    }
    
    # WhatsApp API requires specific multipart form data structure for uploads
    files = {
        'file': ('attachment', file_data, mime_type)
    }
    data = {
        'messaging_product': 'whatsapp'
    }
    
    try:
        response = requests.post(url, headers=headers, files=files, data=data)
        if response.status_code == 200:
            return response.json().get("id")
        else:
            print(f"Media Upload Failed: {response.text}", flush=True)
            return None
    except Exception as e:
        print(f"Media Upload Error: {e}", flush=True)
        return None

# --- BACKGROUND NOTIFICATION WORKER ---
def background_notification_task(form_data, file_data, filename, mime_type):
    """Sends WhatsApp notification to Admin (Jace)"""
    print(f"DEBUG: Starting WhatsApp notification task...", flush=True)
    
    # 1. Construct the Message
    alert_message = f"""🔔 *New Website Contact*

*Name:* {form_data.get('fullName')}
*Email:* {form_data.get('email')}
*Subject:* {form_data.get('subject')}

*Message:*
{form_data.get('message')}"""

    # 2. Send Text Notification
    send_whatsapp_message(ADMIN_PHONE_NUMBER, alert_message)
    print("DEBUG: Text notification sent.", flush=True)

    # 3. Handle File Attachment (If exists)
    if file_data and filename:
        print("DEBUG: Uploading attachment to WhatsApp...", flush=True)
        media_id = upload_media_to_whatsapp(file_data, mime_type)
        
        if media_id:
            print(f"DEBUG: Sending document (ID: {media_id})...", flush=True)
            send_whatsapp_document(ADMIN_PHONE_NUMBER, media_id, filename, "Attachment from Contact Form")
        else:
            send_whatsapp_message(ADMIN_PHONE_NUMBER, "⚠️ User attached a file, but upload failed.")

# --- HEARTBEAT ---
def keep_alive():
    while True:
        time.sleep(300)
        try:
            requests.get("http://127.0.0.1:8000/") 
        except:
            pass
threading.Thread(target=keep_alive, daemon=True).start()

# --- ROUTES ---

@app.route("/", methods=["GET"])
def home():
    return "Jace's AI Server is Running.", 200

@app.route("/webhook", methods=["GET", "POST"])
def whatsapp_webhook():
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200
        return "Forbidden", 403
    
    data = request.get_json()
    try:
        if data.get("entry") and data["entry"][0].get("changes"):
            change = data["entry"][0]["changes"][0]
            if change.get("value") and change["value"].get("messages"):
                message_data = change["value"]["messages"][0]
                sender_phone = message_data["from"]
                
                # Only reply if it's text (avoid loops with status updates)
                if "text" in message_data:
                    user_message = message_data["text"]["body"]
                    ai_reply = get_gemini_response(sender_phone, user_message)
                    send_whatsapp_message(sender_phone, ai_reply)
    except Exception as e:
        print(f"Error: {e}", flush=True)
    return jsonify({"status": "success"}), 200

@app.route("/api/chat", methods=["POST"])
def website_chat():
    data = request.get_json()
    user_message = data.get("message")
    ai_reply = get_gemini_response("website_visitor", user_message)
    return jsonify({"reply": ai_reply})

@app.route("/api/contact", methods=["POST"])
def contact_form():
    try:
        print("DEBUG: Contact form request received.", flush=True)
        form_data = request.form.to_dict()
        attachment = request.files.get('attachment')
        
        file_data = None
        filename = None
        mime_type = None
        
        if attachment:
            file_data = attachment.read()
            filename = attachment.filename
            # Guess the mime type (e.g., application/pdf, image/png)
            mime_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'

        thread = threading.Thread(
            target=background_notification_task, 
            args=(form_data, file_data, filename, mime_type)
        )
        thread.start()
        
        return jsonify({"status": "success", "message": "Message sent! Jace will be notified on WhatsApp."}), 200
            
    except Exception as e:
        print(f"DEBUG: Request Failed: {e}", flush=True)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(port=8000)
