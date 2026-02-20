import logging
import os
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# Logging بسيط
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# التوكن ناخذه من Environment Variable (حتى ما نحط التوكن بالGitHub)
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("Please set the BOT_TOKEN environment variable!")

# دالة الرد على أي رسالة نصية
async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Message from {update.effective_user.id}: {update.message.text}")
    await update.message.reply_text("مرحبا! 👋")

# الدالة الأساسية لتشغيل البوت
async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, hello))
    logger.info("Bot is running...")
    await app.run_polling()

# نستخدم الـ loop الحالي لـ Render
loop = asyncio.get_event_loop()
loop.create_task(main())
loop.run_forever()
