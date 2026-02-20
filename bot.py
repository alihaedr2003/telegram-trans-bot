import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

app = Flask(__name__)

application = ApplicationBuilder().token(TOKEN).build()

async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحبا 👋")

application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, hello))

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    asyncio.run(application.process_update(update))
    return "ok", 200

@app.route("/")
def index():
    return "Bot is running", 200

async def main():
    await application.initialize()
    await application.bot.set_webhook(f"{WEBHOOK_URL}/{TOKEN}")
    await application.start()

if __name__ == "__main__":
    asyncio.run(main())
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
