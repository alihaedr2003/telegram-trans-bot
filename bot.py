import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# Logging بسيط
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = "8480545850:AAHN_sG0qKEjdiUAhSbMgY-HjSEplohscus"

async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رد بسيط: مرحبا"""
    logger.info(f"Message from {update.effective_user.id}: {update.message.text}")
    await update.message.reply_text(f"مرحبا! 👋")

def main():
    logger.info("Starting bot...")
    app = ApplicationBuilder().token(TOKEN).build()
    
    # أي رسالة نصية = الدالة hello
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, hello))
    
    logger.info("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
