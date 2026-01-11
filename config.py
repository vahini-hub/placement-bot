# config.py
import os
import pytz
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))

IST = pytz.timezone("Asia/Kolkata")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORD_FILE = os.path.join(BASE_DIR, "placement_plan.docx")
