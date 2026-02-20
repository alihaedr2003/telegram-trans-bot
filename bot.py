import os
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters,
)
from deep_translator import GoogleTranslator
from PyPDF2 import PdfReader

# 🔹 إعدادات
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # https://your-app.onrender.com

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# 🔹 إنشاء تطبيق البوت
application = ApplicationBuilder().token(TOKEN).build()

# =========================
# ✨ ترجمة النصوص
# =========================
async def translate_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    translated = GoogleTranslator(source="auto", target="en").translate(text)

    await update.message.reply_text(translated)


# =========================
# ✨ ترجمة ملفات PDF
# =========================
async def translate_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()

    file_path = f"{update.message.document.file_id}.pdf"
    await file.download_to_drive(file_path)

    text = ""

    reader = PdfReader(file_path)
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"

    if not text.strip():
        await update.message.reply_text("ما كدر أستخرج نص من الـ PDF")
        os.remove(file_path)
        return

    translated = GoogleTranslator(source="auto", target="en").translate(text[:4000])

    await update.message.reply_text(translated)

    os.remove(file_path)


# =========================
# 🔹 إضافة الـ handlers
# =========================
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, translate_text))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, hello))


# =========================
# 🔹 Webhook route
# =========================
@app.route(f"/{TOKEN}", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.process_update(update)
    return "ok"


# =========================
# 🔹 تشغيل السيرفر + تعيين webhook
# =========================
@app.route("/")
def home():
    return "Bot is running!"


if __name__ == "__main__":
    application.bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")
    app.run(host="0.0.0.0", port=10000)
