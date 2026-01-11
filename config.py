# config.py
import os
import pytz
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))

IST = pytz.timezone("Asia/Kolkata")

WORD_FILE = r"C:\Users\malip\OneDrive\Documents\placepment\placepment plan.docx"
