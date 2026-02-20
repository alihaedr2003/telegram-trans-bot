import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from deep_translator import GoogleTranslator
import PyPDF2
import io

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# استخدم environment variable أو حط التوكن هنا مؤقتاً
import os
TOKEN = os.environ.get("BOT_TOKEN")  # خليه بالمتغيرات على Render

# الرد على النصوص العادية
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Message from {update.effective_user.id}: {update.message.text}")
    await update.message.reply_text("مرحبا! 👋\nارسل ملف PDF لأتمكن من ترجمته 📄➡️🇦🇪")

# ترجمة ملفات PDF
async def translate_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.document:
        file = await context.bot.get_file(update.message.document.file_id)
        pdf_bytes = await file.download_as_bytearray()
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

        if text.strip() == "":
            await update.message.reply_text("الملف فارغ أو لا يمكن قراءته 😕")
            return

        translated = GoogleTranslator(source="auto", target="ar").translate(text)
        # Telegram يحد الرسائل بـ 4096 حرف، فنقسم الرسالة إذا طويلة
        for i in range(0, len(translated), 4000):
            await update.message.reply_text(translated[i:i+4000])
    else:
        await update.message.reply_text("ارسل ملف PDF لأتمكن من ترجمته 📄➡️🇦🇪")

# الدالة الرئيسية async
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # أي رسالة نصية → الرد النصي
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    # أي ملف PDF → الترجمة
    app.add_handler(MessageHandler(filters.Document.PDF, translate_pdf))

    logger.info("Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
