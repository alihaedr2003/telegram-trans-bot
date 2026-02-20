import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from deep_translator import GoogleTranslator
import PyPDF2
import io
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحبا! أرسل PDF للترجمة.")

async def translate_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.document:
        file = await context.bot.get_file(update.message.document.file_id)
        pdf_bytes = await file.download_as_bytearray()
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        text = ""
        for page in pdf_reader.pages:
            if page.extract_text():
                text += page.extract_text() + "\n"
        if not text.strip():
            await update.message.reply_text("الملف فارغ أو لا يمكن قراءته.")
            return
        translated = GoogleTranslator(source="auto", target="ar").translate(text)
        for i in range(0, len(translated), 4000):
            await update.message.reply_text(translated[i:i+4000])
    else:
        await update.message.reply_text("ارسل ملف PDF فقط.")

# ⚡ هنا ما نستعمل asyncio.run()
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
app.add_handler(MessageHandler(filters.Document.PDF, translate_pdf))

logger.info("Bot is running...")
app.run_polling(close_loop=False)  # ⚠️ close_loop=False مهم على Render
