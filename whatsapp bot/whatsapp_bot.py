import os
from dotenv import load_dotenv

# Load secret .env file
load_dotenv() 

# Now Python can find the key
GEMINI_API_KEY = os.environ.get(GEMINI_API_KEY)