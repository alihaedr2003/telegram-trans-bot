import os
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from PyPDF2 import PdfReader
from deep_translator import GoogleTranslator

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Please set the BOT_TOKEN environment variable!")

app = Flask(__name__)
bot = Bot(token=BOT_TOKEN)
application = ApplicationBuilder().token(BOT_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحبا! أرسل لي ملف PDF للترجمة.")

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = update.message.document
    if not file.file_name.endswith(".pdf"):
        await update.message.reply_text("يرجى إرسال ملف PDF فقط.")
        return

    file_path = f"/tmp/{file.file_name}"
    await file.get_file().download_to_drive(file_path)

    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"

    if not text.strip():
        await update.message.reply_text("عذرًا، لم أتمكن من استخراج نص من هذا الملف.")
        return

    translated_text = GoogleTranslator(source="auto", target="en").translate(text)
    
    if len(translated_text) > 4000:
        for i in range(0, len(translated_text), 4000):
            await update.message.reply_text(translated_text[i:i+4000])
    else:
        await update.message.reply_text(translated_text)

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أرسل لي ملف PDF للترجمة فقط.")

application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.Document.FileExtension("pdf"), handle_pdf))
application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), echo))

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    application.create_task(application.update_queue.put(update))
    return "OK"

@app.route("/")
def index():
    return "Bot is running!"

if __name__ == "__main__":
    webhook_url = f"https://https://telegram-trans-bot-truv.onrender.com/{BOT_TOKEN}"
    bot.set_webhook(webhook_url)
    print("Webhook set to:", webhook_url)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
