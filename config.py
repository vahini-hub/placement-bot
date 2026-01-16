# config.py
import os
from dotenv import load_dotenv
from zoneinfo import ZoneInfo
load_dotenv()
IST = ZoneInfo("Asia/Kolkata")

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORD_FILE = os.path.join(BASE_DIR, "placepment_plan.docx")