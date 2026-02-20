import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from PyPDF2 import PdfReader
from deep_translator import GoogleTranslator

# Logging بسيط
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Please set the BOT_TOKEN environment variable!")

async def translate_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يستقبل ملف PDF ويترجمه"""
    message = update.message
    if not message.document or not message.document.file_name.endswith(".pdf"):
        await message.reply_text("من فضلك أرسل ملف PDF فقط!")
        return

    file = await message.document.get_file()
    file_path = f"/tmp/{message.document.file_name}"
    await file.download_to_drive(file_path)

    # قراءة النص من PDF
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"

    if not text.strip():
        await message.reply_text("الملف فارغ أو لا يمكن قراءة النص منه.")
        return

    # ترجمة النص
    translated = GoogleTranslator(source="auto", target="ar").translate(text)
    await message.reply_text(translated[:4000])  # Telegram يقبل نص طويل حتى 4096 حرف

def main():
    logger.info("Starting bot...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # أي رسالة فيها ملف PDF = الدالة translate_pdf
    app.add_handler(MessageHandler(filters.Document.ALL, translate_pdf))

    logger.info("Bot is running...")
    # ⚡ شغالة مباشرة على Render بدون Flask
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        url_path=BOT_TOKEN,
        webhook_url=f"https://{os.environ.get('RENDER_EXTERNAL_URL')}/{BOT_TOKEN}"
    )

if __name__ == "__main__":
    main()
