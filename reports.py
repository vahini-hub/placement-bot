from datetime import datetime, timedelta, time as dt_time
from docx import Document
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from config import WORD_FILE, CHAT_ID, IST
import matplotlib.pyplot as plt
from collections import Counter

# ================= INTERNAL HELPERS =================
def _get_table():
    doc = Document(WORD_FILE)
    table = doc.tables[0]

    headers = {}
    for row in table.rows:
        cells = [c.text.strip().lower() for c in row.cells]
        if "date" in cells and "status" in cells:
            for i, h in enumerate(cells):
                headers[h] = i
            break

    required = ["date", "status", "hard topic"]
    for r in required:
        if r not in headers:
            raise ValueError(f"Missing column: {r}")

    return table, headers


def _parse_date(row, headers):
    try:
        return datetime.strptime(
            row.cells[headers["date"]].text.strip(), "%Y-%m-%d"
        ).date()
    except:
        return None


# ================= PDF CORE =================
def generate_pdf(start_date, end_date, title):
    table, headers = _get_table()

    pdf_path = f"{title.replace(' ', '_')}.pdf"
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4

    y = height - 2 * cm
    c.setFont("Helvetica-Bold", 14)
    c.drawString(2 * cm, y, title)
    y -= 1.5 * cm
    c.setFont("Helvetica", 10)

    for row in table.rows:
        d = _parse_date(row, headers)
        if not d or not (start_date <= d <= end_date):
            continue

        raw_status = row.cells[headers["status"]].text.strip()
        status="DONE" if "✅"in raw_status else "MISS" if "❌" in raw_status else "-"
        hard = row.cells[headers["hard topic"]].text.strip() or "None"
        x =2* cm
        
        c.setFillColor(colors.black)
        c.drawString(x, y, f"{d} | ")
        x += c.stringWidth(f"{d} | ", "Helvetica", 10)
        
        if status == "DONE":
            c.setFillColor(colors.green)
        elif status == "MISS":
            c.setFillColor(colors.red)
        else:
            c.setFillColor(colors.black)
        c.drawString(x, y, status)
        x += c.stringWidth(status, "Helvetica", 10)

        # Rest (black)
        c.setFillColor(colors.black)
        c.drawString(x, y, f" | Hard: {hard}")
        y -= 0.8 * cm

        if y < 2 * cm:
            c.showPage()
            y = height - 2 * cm

    c.save()
    return pdf_path


# ================= WEEKLY PDF =================
async def send_weekly_report(context):
    today = datetime.now(IST).date()
    start = today - timedelta(days=6)
    pdf = generate_pdf(start, today, "Weekly Study Report")
    await context.bot.send_document(chat_id=CHAT_ID, document=open(pdf, "rb"))


# ================= MONTHLY PDF =================
async def send_monthly_report(context):
    today = datetime.now(IST).date()
    first = today.replace(day=1)
    last_end = first - timedelta(days=1)
    last_start = last_end.replace(day=1)

    pdf = generate_pdf(
        last_start,
        last_end,
        f"Monthly Report {last_start.strftime('%B %Y')}",
    )
    await context.bot.send_document(chat_id=CHAT_ID, document=open(pdf, "rb"))


async def monthly_checker(context):
    if (datetime.now(IST).date() + timedelta(days=1)).day == 1:
        await send_monthly_report(context)


# ================= SUNDAY SUMMARY =================
async def send_sunday_summary(context):
    today = datetime.now(IST).date()
    start = today - timedelta(days=6)

    table, headers = _get_table()
    done = miss = 0
    hard_topics = []

    for row in table.rows:
        d = _parse_date(row, headers)
        if not d or not (start <= d <= today):
            continue

        s = row.cells[headers["status"]].text
        h = row.cells[headers["hard topic"]].text

        if "✅" in s:
            done += 1
        elif "❌" in s:
            miss += 1

        if h and h.lower() != "none":
            hard_topics.append(f"• {d}: {h}")

    msg = (
        f"📌 *Weekly Summary*\n\n"
        f"✅ Done: {done}\n"
        f"❌ Missed: {miss}\n\n"
        f"🧠 *Hard Topics*\n"
        + ("\n".join(hard_topics) if hard_topics else "None 🎉")
    )

    await context.bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")


# ================= GRAPHS =================
def _plot_and_send(x, y, title, file, caption, context):
    plt.figure()
    plt.plot(x, y, marker="o")
    plt.yticks([0, 1], ["❌", "✅"])
    plt.title(title)
    plt.grid(True)
    plt.savefig(file)
    plt.close()

    return context.bot.send_photo(
        chat_id=CHAT_ID, photo=open(file, "rb"), caption=caption
    )


async def send_weekly_graph(context):
    today = datetime.now(IST).date()
    start = today - timedelta(days=6)

    table, headers = _get_table()
    x, y = [], []

    for row in table.rows:
        d = _parse_date(row, headers)
        if not d or not (start <= d <= today):
            continue

        x.append(d.strftime("%a"))
        y.append(1 if "✅" in row.cells[headers["status"]].text else 0)

    if x:
        await _plot_and_send(x, y, "Weekly Progress", "weekly.png", "📈 Weekly Progress", context)


async def send_monthly_graph(context):
    today = datetime.now(IST).date()
    first = today.replace(day=1)
    lm_end = first - timedelta(days=1)
    lm_start = lm_end.replace(day=1)

    table, headers = _get_table()
    x, y = [], []

    for row in table.rows:
        d = _parse_date(row, headers)
        if not d or not (lm_start <= d <= lm_end):
            continue

        x.append(d.day)
        y.append(1 if "✅" in row.cells[headers["status"]].text else 0)

    if x:
        await _plot_and_send(
            x,
            y,
            f"Monthly Progress {lm_start.strftime('%B')}",
            "monthly.png",
            "📊 Monthly Progress",
            context,
        )


# ================= CONSISTENCY =================
async def send_consistency_score(context):
    table, headers = _get_table()
    total = done = 0

    for row in table.rows:
        s = row.cells[headers["status"]].text
        if "✅" in s or "❌" in s:
            total += 1
            if "✅" in s:
                done += 1

    if total:
        pct = round((done / total) * 100, 2)
        await context.bot.send_message(
            chat_id=CHAT_ID, text=f"📈 *Consistency*: {pct}%", parse_mode="Markdown"
        )


# ================= BEST STREAK =================
async def send_best_streak(context):
    table, headers = _get_table()
    best = cur = 0

    for row in table.rows:
        if "✅" in row.cells[headers["status"]].text:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0

    await context.bot.send_message(
        chat_id=CHAT_ID, text=f"🏆 *Best Streak*: {best} days", parse_mode="Markdown"
    )


# ================= STUDY SCORE =================
async def send_study_score(context):
    table, headers = _get_table()
    score = max_score = 0

    for row in table.rows:
        s = row.cells[headers["status"]].text
        h = row.cells[headers["hard topic"]].text.lower()

        if "✅" in s or "❌" in s:
            max_score += 10
            if "✅" in s:
                score += max(10 - (2 if h != "none" else 0), 0)

    if max_score:
        pct = round((score / max_score) * 100, 2)
        await context.bot.send_message(
            chat_id=CHAT_ID, text=f"🧮 *Study Score*: {pct}%", parse_mode="Markdown"
        )


# ================= HARD TOPIC ANALYTICS =================
async def send_hard_topic_analytics(context):
    table, headers = _get_table()
    topics = []

    for row in table.rows:
        h = row.cells[headers["hard topic"]].text
        if h and h.lower() != "none":
            topics.append(h)

    if not topics:
        msg = "🧠 *Hard Topics*: None 🎉"
    else:
        c = Counter(topics).most_common(5)
        msg = "🧠 *Hard Topic Analytics*\n\n" + "\n".join(
            f"• {t} → {n}" for t, n in c
        )

    await context.bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")


# ================= MONTH COMPARISON =================
async def send_month_comparison(context):
    table, headers = _get_table()
    today = datetime.now(IST).date()

    first = today.replace(day=1)
    lm_end = first - timedelta(days=1)
    lm_start = lm_end.replace(day=1)
    pm_end = lm_start - timedelta(days=1)
    pm_start = pm_end.replace(day=1)

    def count(start, end):
        c = 0
        for row in table.rows:
            d = _parse_date(row, headers)
            if d and start <= d <= end and "✅" in row.cells[headers["status"]].text:
                c += 1
        return c

    lm, pm = count(lm_start, lm_end), count(pm_start, pm_end)
    trend = "📈 Improved" if lm > pm else "📉 Declined" if lm < pm else "➖ Same"

    msg = (
        f"🏅 *Month Comparison*\n\n"
        f"{pm_start.strftime('%B')}: {pm}\n"
        f"{lm_start.strftime('%B')}: {lm}\n\n"
        f"Trend: *{trend}*"
    )

    await context.bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")


# ================= AI MOTIVATION =================
async def send_ai_motivation(context):
    table, headers = _get_table()
    score = max_score = 0

    for row in table.rows:
        s = row.cells[headers["status"]].text
        h = row.cells[headers["hard topic"]].text.lower()

        if "✅" in s or "❌" in s:
            max_score += 10
            if "✅" in s:
                score += max(10 - (2 if h != "none" else 0), 0)

    if not max_score:
        return

    pct = (score / max_score) * 100

    if pct >= 85:
        msg = "🔥 Elite consistency! Keep dominating 🚀"
    elif pct >= 70:
        msg = "💪 Great job! Push a little harder."
    elif pct >= 50:
        msg = "🙂 Decent start. Reduce missed days."
    else:
        msg = "⚠️ Reset time. Small wins daily."

    await context.bot.send_message(
        chat_id=CHAT_ID, text=f"🤖 *AI Motivation*\n\n{msg}", parse_mode="Markdown"
    )


# ================= COMMAND =================
async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start = datetime.strptime(context.args[0], "%Y-%m-%d").date()
    end = datetime.strptime(context.args[1], "%Y-%m-%d").date()
    pdf = generate_pdf(start, end, f"Study Report {start} to {end}")
    await update.message.reply_document(open(pdf, "rb"))


# ================= REGISTER =================
def register_reports(app):
    app.add_handler(CommandHandler("report", report_command))

    app.job_queue.run_daily(send_weekly_report, dt_time(21, 0), days=(6,))
    app.job_queue.run_daily(send_sunday_summary, dt_time(21, 2), days=(6,))
    app.job_queue.run_daily(send_weekly_graph, dt_time(21, 4), days=(6,))
    app.job_queue.run_daily(send_consistency_score, dt_time(21, 5), days=(6,))
    app.job_queue.run_daily(send_best_streak, dt_time(21, 6), days=(6,))
    app.job_queue.run_daily(send_study_score, dt_time(21, 8), days=(6,))
    app.job_queue.run_daily(send_hard_topic_analytics, dt_time(21, 10), days=(6,))
    app.job_queue.run_daily(send_ai_motivation, dt_time(21, 12))
    app.job_queue.run_daily(monthly_checker, dt_time(21, 14))
    app.job_queue.run_daily(send_monthly_graph, dt_time(21, 15))
    app.job_queue.run_daily(send_month_comparison, dt_time(21, 16))
