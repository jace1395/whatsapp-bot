import os
import time
import threading
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS  # Import CORS for website connection
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load secret .env file (for local testing only)
load_dotenv()

app = Flask(__name__)

# --- ENABLE CORS ---
# This is the "Security Pass" that allows your InfinityFree website
# (jacecadwyhenriques.ct.ws) to talk to this Render server.
CORS(app)

# --- CONFIGURATION ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
VERIFY_TOKEN = "my_secret_password_jace"

# Initialize Gemini Client
client = genai.Client(api_key=GEMINI_API_KEY)

# --- JACE'S BIO (System Instruction) ---
# The AI will always keep this in mind.
JACE_BIO = """
You are the personal AI assistant for Jace Cadwy Henriques. 
You serve two purposes: 
1. Answering Jace on WhatsApp (be helpful, formal, and concise).
2. Answering visitors on his Portfolio Website (be professional, impressive, and informative about Jace).

Here is the COMPLETE profile of Jace Henriques:

**PERSONAL IDENTITY**
- **Full Name:** Jace Cadwy Henriques
- **DOB:** April 13, 2007 (Age 18)
- **Location:** Down Mangor, Vasco, Goa, India (403802)
- **Contact:** jacehenriques07@gmail.com | +91 9834016312
- **Personality:** A relentless learner. "When I like something, I don't give up easily. When I don't like something, I still grasp its fundamentals."

**ACADEMIC BACKGROUND**
- **Current:** B.Voc in Software Technology at Shree Damodar College of Commerce and Economics, Margao. (Student ID: 2511011).
- **12th Grade (HSSC):** Computer Techniques at M.E.S Higher Secondary School (2023-2025). **Score: 90.25%**.
- **10th Grade (SSC):** Deepvihar High School (2017-2023). **Score: 80.16% (Distinction)**.

**TECHNICAL CERTIFICATIONS & TRAINING**
- **Networking & Windows Server:** Digicom (Feb-Apr 2025).
- **Next Gen UI/UX Winter School:** Padre Conceicao College of Engineering (Nov 2024). Learned Figma, Color Theory, Netflix Clone Project.
- **PC Hardware Course:** Digicom (May-Jun 2024). Expert in assembly and troubleshooting.
- **On-The-Job Training:** VTECH (Mar-Apr 2024). Practical industry experience.
- **Python Certifications (Great Learning, May 2024):** Functions in Python, Programming Basics, Python Jobs, Python Practice Code.

**SKILLS & INTERESTS**
- **Hardware Expert:** Deep understanding of GPUs, PSUs, and System Architecture. Planning a future-proof PC build in 2028 for local LLMs.
- **AI Enthusiast:** Fascinated by the mathematics (matrices) behind Generative AI and GPTs.
- **Sports:** Soccer (Center-back position), Table Tennis.
- **Music:** Plays Acoustic Guitar, enjoys singing.
- **Gaming:** Avid FIFA player.

**INSTRUCTIONS FOR AI:**
- If the user is Jace (on WhatsApp): Prioritize his hardware queries and coding tasks.
- If the user is a Website Visitor: Speak as Jace's digital representative. Showcase his achievements (like the 90.25% score) and skills.
"""

# --- MEMORY STORAGE (RAM) ---
chat_memory = {}

# --- HELPER: Get Response from Gemini ---
def get_gemini_response(user_id, user_text):
    # 1. Check for clear commands
    if "forget" in user_text.lower() or "clear chat" in user_text.lower():
        chat_memory[user_id] = []
        return "Memory cleared. I am ready to start fresh."

    # 2. Initialize memory if new user
    if user_id not in chat_memory:
        chat_memory[user_id] = []

    # 3. Add User Message to history
    chat_memory[user_id].append({"role": "user", "parts": [{"text": user_text}]})

    try:
        # 4. Call Gemini with System Instruction (Bio) & New Model
        response = client.models.generate_content(
            model="gemini-2.0-flash-lite-preview-02-05", # High speed model
            config=types.GenerateContentConfig(
                system_instruction=JACE_BIO, # Injecting your bio here
                temperature=0.7
            ),
            contents=chat_memory[user_id]
        )
        
        bot_reply = response.text

        # 5. Add AI Reply to Memory
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

# --- HEARTBEAT (Keep Alive) ---
def keep_alive():
    while True:
        time.sleep(300) # Ping every 5 mins
        try:
            # Self-ping to keep Render awake
            requests.get("http://127.0.0.1:8000/") 
        except:
            pass
threading.Thread(target=keep_alive, daemon=True).start()

# --- ROUTES ---

@app.route("/", methods=["GET"])
def home():
    return "Jace's AI Server is Running.", 200

# 1. WHATSAPP ROUTE
@app.route("/webhook", methods=["GET", "POST"])
def whatsapp_webhook():
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200
        return "Forbidden", 403
    
    # Handle POST
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

# 2. WEBSITE ROUTE (For your InfinityFree site)
@app.route("/api/chat", methods=["POST"])
def website_chat():
    data = request.get_json()
    user_message = data.get("message")
    
    # We use a generic ID for website visitors
    ai_reply = get_gemini_response("website_visitor", user_message)
    
    return jsonify({"reply": ai_reply})

if __name__ == "__main__":
    app.run(port=8000)
