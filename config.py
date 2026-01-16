# config.py
import os
from dotenv import load_dotenv
from zoneinfo import ZoneInfo
load_dotenv()
IST = ZoneInfo("Asia/Kolkata")

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))

WORD_FILE = "/data/placepment_plan.docx"
