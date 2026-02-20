import os
import logging
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from deep_translator import GoogleTranslator
import PyPDF2
import io

# -------- Logging --------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------- Config --------
TOKEN = os.getenv("BOT_TOKEN")  # ⚠️ ضع التوكن بالـ Environment Variables على Render
bot = Bot(TOKEN)
app = Flask(__name__)

# -------- Helper: extract text from PDF --------
def extract_pdf_text(file_bytes):
    reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

# -------- Telegram Handler --------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Received message from {update.effective_user.id}")

    # PDF
    if update.message.document:
        file = await context.bot.get_file(update.message.document.file_id)
        file_bytes = await file.download_as_bytearray()
        text = extract_pdf_text(file_bytes)
        logger.info(f"Extracted PDF text ({len(text)} chars)")

        if not text.strip():
            await update.message.reply_text("PDF فارغ أو لا يحتوي على نص يمكن ترجمته.")
            return

        # ترجمة
        translated = GoogleTranslator(source='auto', target='ar').translate(text)
        await update.message.reply_text(translated[:4000])  # Telegram limit
        logger.info("PDF translated and sent")

    # نص عادي
    elif update.message.text:
        translated = GoogleTranslator(source='auto', target='ar').translate(update.message.text)
        await update.message.reply_text(translated)
        logger.info("Text translated and sent")

# -------- Flask route for webhook --------
@app.route(f"/{TOKEN}", methods=["POST"])
async def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), bot)
        await handle_message(update, ContextTypes.DEFAULT_TYPE(bot=bot))
        return "OK", 200
    except Exception as e:
        logger.error(f"Error handling update: {e}")
        return "Error", 500

# -------- Health check --------
@app.route("/", methods=["GET"])
def index():
    return "Bot is running!", 200

# -------- Main --------
if __name__ == "__main__":
    logger.info("Starting Flask app for Telegram webhook...")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
