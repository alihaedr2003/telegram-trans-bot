import logging
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("Please set the BOT_TOKEN environment variable!")

async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Message from {update.effective_user.id}: {update.message.text}")
    await update.message.reply_text("مرحبا! 👋")

async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, hello))
    logger.info("Bot is running...")
    await app.run_polling()

# هذي الطريقة الجديدة، ما نستعمل get_event_loop
if __name__ == "__main__":
    asyncio.run(main())
