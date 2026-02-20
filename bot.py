import os
import logging
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # تحطه في Render

app = Flask(__name__)
bot = Bot(token=TOKEN)
application = ApplicationBuilder().token(TOKEN).build()

# دالة الرد
async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحبا 👋")

application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, hello))

# Flask route (لازم يكون بنفس مسار التوكن)
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    application.process_update(update)
    return "ok"

# تفعيل webhook عند التشغيل
@app.route("/")
def index():
    return "Bot is running"

async def setup_webhook():
    await bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")

if __name__ == "__main__":
    import asyncio

    asyncio.run(setup_webhook())
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
