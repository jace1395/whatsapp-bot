import os
import time
import threading
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
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
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")

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

# --- HELPER: Get Response from Gemini ---
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
        print(f"Gemini Error: {e}")
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

def send_email_notification(form_data, attachment):
    if not EMAIL_USER or not EMAIL_PASSWORD:
        print("Email credentials not set.")
        return False

    msg = MIMEMultipart()
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_USER  # Send to yourself
    msg['Subject'] = f"New Portfolio Contact: {form_data.get('subject')}"

    body = f"""
    You have a new message from your portfolio website!
    
    Name: {form_data.get('fullName')}
    Email: {form_data.get('email')}
    
    Message:
    {form_data.get('message')}
    """
    msg.attach(MIMEText(body, 'plain'))

    # Handle Attachment
    if attachment:
        try:
            filename = attachment.filename
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename= {filename}")
            msg.attach(part)
        except Exception as e:
            print(f"Error attaching file: {e}")

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(EMAIL_USER, EMAIL_USER, text)
        server.quit()
        return True
    except Exception as e:
        print(f"SMTP Error: {e}")
        return False

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
                user_message = message_data["text"]["body"]
                ai_reply = get_gemini_response(sender_phone, user_message)
                send_whatsapp_message(sender_phone, ai_reply)
    except Exception as e:
        print(f"Error: {e}")
    return jsonify({"status": "success"}), 200

@app.route("/api/chat", methods=["POST"])
def website_chat():
    data = request.get_json()
    user_message = data.get("message")
    ai_reply = get_gemini_response("website_visitor", user_message)
    return jsonify({"reply": ai_reply})

# --- NEW CONTACT FORM ROUTE ---
@app.route("/api/contact", methods=["POST"])
def contact_form():
    try:
        # Access form fields
        form_data = request.form
        # Access file (if any)
        attachment = request.files.get('attachment')
        
        success = send_email_notification(form_data, attachment)
        
        if success:
            return jsonify({"status": "success", "message": "Email sent successfully!"}), 200
        else:
            return jsonify({"status": "error", "message": "Failed to send email."}), 500
            
    except Exception as e:
        print(f"Contact Form Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(port=8000)
