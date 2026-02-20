import os
import threading
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from deep_translator import GoogleTranslator
import PyPDF2
from io import BytesIO

TOKEN = os.environ.get("BOT_TOKEN")  # خلي التوكن بالـ environment variable
if not TOKEN:
    raise ValueError("Please set the BOT_TOKEN environment variable!")

app = Flask(__name__)
bot = Bot(token=TOKEN)
application = ApplicationBuilder().token(TOKEN).build()

# -------------------- Handlers --------------------
async def translate_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if message.document:  # إذا الملف PDF
        file = await message.document.get_file()
        bio = BytesIO()
        await file.download_to_memory(out=bio)
        bio.seek(0)
        reader = PyPDF2.PdfReader(bio)
        text = "\n".join([page.extract_text() or "" for page in reader.pages])
        translated = GoogleTranslator(source='auto', target='en').translate(text)
        await message.reply_text(translated[:4000] or "لا يمكن ترجمة المحتوى.")  # Telegram message limit
    elif message.text:
        translated = GoogleTranslator(source='auto', target='en').translate(message.text)
        await message.reply_text(translated)

application.add_handler(MessageHandler(filters.ALL, translate_text))

# -------------------- Webhook route --------------------
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    application.update_queue.put_nowait(update)
    return "OK", 200

# -------------------- Thread for processing updates --------------------
def run_bot():
    # ⚠️ بدون close_loop على Render
    application.run_polling(poll_interval=0.5)

threading.Thread(target=run_bot).start()

# -------------------- Start Flask --------------------
@app.route("/")
def index():
    return "Bot is running!", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
