import os
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

app = Flask(__name__)

# بوت التليگرام
application = ApplicationBuilder().token(TOKEN).build()

# رد بسيط
async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحبا 👋")

application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, hello))

# مسار الاستقبال من تليگرام
@app.route(f"/{TOKEN}", methods=["POST"])
async def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return "ok", 200  # 🔴 مهم جداً

# مسار رئيسي حتى ما يعطي 500
@app.route("/")
def index():
    return "Bot is running", 200

if __name__ == "__main__":
    import asyncio

    async def main():
        await application.initialize()
        await application.bot.set_webhook(f"{WEBHOOK_URL}/{TOKEN}")
        await application.start()

    asyncio.run(main())

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
