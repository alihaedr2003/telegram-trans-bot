# bot.py
import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# ====== إعداد المتغيرات ======
TOKEN = os.environ.get("BOT_TOKEN")  # خلي التوكن في Environment Variable
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # https://اسم_البوت_هنا.onrender.com

if not TOKEN or not WEBHOOK_URL:
    raise ValueError("Please set BOT_TOKEN and WEBHOOK_URL environment variables!")

# ====== إعداد Flask و Telegram Bot ======
app = Flask(__name__)
application = ApplicationBuilder().token(TOKEN).build()

# ====== دالة الرد ======
from deep_translator import GoogleTranslator

async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    translated = GoogleTranslator(source='auto', target='en').translate(text)

    await update.message.reply_text(translated)

# إضافة Handler لأي رسالة نصية
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, hello))

# ====== Webhook route ======
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    """هذي endpoint للـ Telegram Webhook"""
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    asyncio.run(application.process_update(update))  # معالجة التحديث async
    return "ok", 200

# صفحة رئيسية فقط للتأكد أن الخدمة شغالة
@app.route("/")
def index():
    return "Bot is running ✅", 200

# ====== Main: تهيئة البوت + ضبط webhook ======
async def main():
    await application.initialize()
    await application.bot.set_webhook(f"{WEBHOOK_URL}/{TOKEN}")  # ضبط الـ webhook
    await application.start()

if __name__ == "__main__":
    # شغل Flask + البوت
    asyncio.run(main())
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
