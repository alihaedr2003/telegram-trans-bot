import os
import logging
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from deep_translator import GoogleTranslator
from PyPDF2 import PdfReader
import tempfile

# Logging بسيط
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN")  # ⚠️ لازم تحط التوكن في Environment Variables
if not TOKEN:
    raise ValueError("Please set the BOT_TOKEN environment variable!")

app = Flask(__name__)
bot = Bot(TOKEN)

# --- الدوال ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحبا! أرسل لي PDF أو نص لأترجمه.")

async def translate_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    translated = GoogleTranslator(source='auto', target='en').translate(text)
    await update.message.reply_text(translated)

async def translate_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if not document.file_name.endswith(".pdf"):
        await update.message.reply_text("يرجى إرسال ملف PDF فقط.")
        return

    file = await context.bot.get_file(document.file_id)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        await file.download_to_drive(tmp.name)
        reader = PdfReader(tmp.name)
        text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
        if not text:
            await update.message.reply_text("الملف فارغ أو غير قابل للقراءة.")
            return
        translated = GoogleTranslator(source='auto', target='en').translate(text)
        # Telegram limits: 4096 chars
        for i in range(0, len(translated), 4000):
            await update.message.reply_text(translated[i:i+4000])

# --- إنشاء التطبيق ---
application = ApplicationBuilder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, translate_text))
application.add_handler(MessageHandler(filters.Document.PDF, translate_pdf))

# --- Webhook Flask route ---
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, bot)
    application.update_queue.put_nowait(update)
    return "OK"

# --- إعداد Webhook على Telegram ---
@app.before_first_request
def set_webhook():
    url = f"https://telegram-trans-bot-truv.onrender.com/{TOKEN}"
    bot.set_webhook(url=url)
    logger.info(f"Webhook set to: {url}")

# --- تشغيل Flask ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
