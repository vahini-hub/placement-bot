# ================= FORCE IPV4 (CRITICAL FIX) =================
import socket
# Force python-telegram-bot to use only IPv4
socket._orig_getaddrinfo = socket.getaddrinfo
socket.getaddrinfo = lambda *args, **kwargs: [
    addr for addr in socket._orig_getaddrinfo(*args, **kwargs)
    if addr[0] == socket.AF_INET
]
# tracker_cloud_ready.py
import os
from datetime import datetime, time as dt_time
from docx import Document
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    ContextTypes,
)
from reports import register_reports
from config import WORD_FILE, CHAT_ID, IST,BOT_TOKEN
from drive import upload_to_drive
import shutil
if not os.path.exists(WORD_FILE):
    shutil.copy("placepment_plan.docx", WORD_FILE)
    print("📄 Word file copied to volume")
import time
START_DATE = "2026-01-12"
evening_RETRY_JOB = "evening_retry"
HARD_TOPIC_TIMEOUT_JOB = "hard_topic_timeout"

def upload_with_retry(local_file, filename, retries=3, delay=2):
    for attempt in range(1, retries + 1):
        success = upload_to_drive(local_file, filename)
        if success:
            print(f"☁️ Drive sync successful (attempt {attempt})")
            return True

        print(f"⚠️ Drive sync failed (attempt {attempt}/{retries})")
        if attempt < retries:
            time.sleep(delay)

    print("❌ Drive sync failed after all retries")
    return False

# ===== HELPERS =====
def get_day_number():
    start = datetime.strptime(START_DATE, "%Y-%m-%d").date()
    today = datetime.now(IST).date()
    if today < start:
        return None
    return (today - start).days + 1

def get_table_and_row(doc, day):
    table_index = (day - 1) // 7
    row_index = ((day - 1) % 7) + 1
    if table_index >= len(doc.tables):
        return None, None
    return doc.tables[table_index], row_index


def update_status_in_word(symbol):
    day = get_day_number()
    if day is None:
        return

    doc = Document(WORD_FILE)
    table, row = get_table_and_row(doc, day)

    status_col = None
    for i, cell in enumerate(table.rows[0].cells):
        if cell.text.strip().lower() == "status":
            status_col = i
            break

    if status_col is None or row >= len(table.rows):
        return

    table.rows[row].cells[status_col].text = symbol
    doc.save(WORD_FILE)
    upload_to_drive(WORD_FILE, "placepment_plan.docx")
    success = upload_to_drive(WORD_FILE, "placepment_plan.docx")
    if not success:
        print("⚠️ Local Word updated, but Drive sync failed after retries")

    print(f"✅ Status updated: Day {day}")
# ===== evening =====
async def evening_buttons(context: ContextTypes.DEFAULT_TYPE):
    retries = context.bot_data.get("evening_retry_count", 0)
    if retries >= 2:
        context.bot_data["evening_retry_count"] = 0
        return
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes", callback_data="evening_yes"),
            InlineKeyboardButton("❌ No", callback_data="evening_no"),
        ]
    ]
    await context.bot.send_message(
        chat_id=CHAT_ID,
        text="Have you started studying 📔 ?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    context.bot_data["evening_retry_count"] = retries + 1
    # remove old retry jobs
    for job in context.job_queue.get_jobs_by_name(evening_RETRY_JOB):
        job.schedule_removal()

    # retry after 1 minutes
    context.job_queue.run_once(
        evening_buttons,
        when=60,
        name=evening_RETRY_JOB
    )

# ===== NIGHT =====
async def night_buttons(context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes", callback_data="night_yes"),
            InlineKeyboardButton("❌ No", callback_data="night_no"),
        ]
    ]
    await context.bot.send_message(
        chat_id=CHAT_ID,
        text="Did you complete today’s portion?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

# ===== CALLBACK =====
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # evening
    if query.data == "evening_yes":
        context.bot_data["evening_retry_count"] = 0
        for job in context.job_queue.get_jobs_by_name(evening_RETRY_JOB):
            job.schedule_removal()
        await query.edit_message_text("👍 Good, start studying 💪")

    elif query.data == "evening_no":
        await query.edit_message_text("⏳ Okay, I’ll remind you again in 5 minutes.")

    # NIGHT
    elif query.data == "night_yes":
        update_status_in_word("✅")
        context.user_data["awaiting_hard_topic"] = True 
        for job in context.job_queue.get_jobs_by_name(HARD_TOPIC_TIMEOUT_JOB):
            job.schedule_removal()
    # schedule 2-minute timeout
        context.job_queue.run_once(
            hard_topic_timeout,
            when=120,  # 2 minutes
            name=HARD_TOPIC_TIMEOUT_JOB,
            user_id=query.from_user.id,
            chat_id=query.message.chat_id,
        )
        await query.edit_message_text("🎉 Marked as COMPLETED ✅\n\nWhich topic did you find hard today ")
    elif query.data == "night_no":
        update_status_in_word("❌")
        await query.edit_message_text("⚠️ Marked as NOT completed ❌\nTry again tomorrow 💪")
# ===== HARD TOPIC HANDLER (STEP 2) =====
from telegram.ext import MessageHandler, filters
async def hard_topic_timeout(context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_hard_topic"):
        return

    day = get_day_number()
    if day is None:
        return

    doc = Document(WORD_FILE)
    if not doc.tables:
        return
    table, row = get_table_and_row(doc, day)
    if table is None:
        return

    hard_col = None
    for i, cell in enumerate(table.rows[0].cells):
        if cell.text.strip().lower() == "hard topic":
            hard_col = i
            break

    if hard_col is not None and row < len(table.rows):
        table.rows[row].cells[hard_col].text = "None"
        doc.save(WORD_FILE)
        upload_to_drive(WORD_FILE, "placepment_plan.docx")
        success = upload_to_drive(WORD_FILE, "placepment_plan.docx")
        if not success:
            print("⚠️ Local Word updated, but Drive sync failed after retries")
    context.user_data["awaiting_hard_topic"] = False

    await context.bot.send_message(
        chat_id=context.job.chat_id,
        text="⏰ No response received. Hard topic marked as *None*.",
        parse_mode="Markdown",
    )

async def hard_topic_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_hard_topic"):
        return

    topic = update.message.text
    day = get_day_number()
    if day is None:
        return

    doc = Document(WORD_FILE)
    table, row = get_table_and_row(doc, day)
    if table is None:
        return

    hard_col = None
    for i, cell in enumerate(table.rows[0].cells):
        if cell.text.strip().lower() == "hard topic":
            hard_col = i
            break

    if hard_col is not None and row < len(table.rows):
        table.rows[row].cells[hard_col].text = topic
        doc.save(WORD_FILE)
        upload_to_drive(WORD_FILE, "placepment_plan.docx")
        success = upload_to_drive(WORD_FILE, "placepment_plan.docx")
        if not success:
            print("⚠️ Local Word updated, but Drive sync failed after retries")

    context.user_data["awaiting_hard_topic"] = False
    await update.message.reply_text("📝 Hard topic saved successfully ✅")

# ===== APP =====

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CallbackQueryHandler(button_callback))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, hard_topic_handler))
register_reports(app)
# IST timezone
#app.job_queue.scheduler.configure(timezone=IST)

# ===== SCHEDULE =====
# evening 6:25 PM
ALL_DAYS = (0, 1, 2, 3, 4, 5, 6)
app.job_queue.run_daily(
    evening_buttons,
    time=dt_time(hour=17, minute=30,tzinfo=IST),
    days=ALL_DAYS

)

# Night 9:05 PM
ALL_DAYS = (0, 1, 2, 3, 4, 5, 6)
app.job_queue.run_daily(
    night_buttons,
    time=dt_time(hour=22, minute=30,tzinfo=IST),
    days=ALL_DAYS

)
# ===== START =====
print("Bot running...")
app.run_polling(drop_pending_updates=True)