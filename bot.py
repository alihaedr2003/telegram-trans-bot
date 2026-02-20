import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from deep_translator import GoogleTranslator
from docx import Document
import PyPDF2

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

TOKEN = "8480545850:AAHN_sG0qKEjdiUAhSbMgY-HjSEplohscus"

def extract_text(file_path):
    text = ""
    logger.info(f"Extracting text from: {file_path}")
    try:
        if file_path.endswith(".txt"):
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
        elif file_path.endswith(".docx"):
            doc = Document(file_path)
            for p in doc.paragraphs:
                text += p.text + "\n"
        elif file_path.endswith(".pdf"):
            pdf = PyPDF2.PdfReader(file_path)
            for page in pdf.pages:
                if page.extract_text():
                    text += page.extract_text() + "\n"
        logger.info(f"Text extracted successfully: {len(text)} chars")
    except Exception as e:
        logger.error(f"Error extracting text: {e}")
    return text

def translate_text(text):
    logger.info(f"Translating {len(text)} characters")
    try:
        translated = GoogleTranslator(source='en', target='ar').translate(text)
        logger.info("Translation successful")
        return translated
    except Exception as e:
        logger.error(f"Translation error: {e}")
        return ""

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"File received from user {update.effective_user.id}")
    try:
        file = await update.message.document.get_file()
        file_path = await file.download_to_drive()
        logger.info(f"File downloaded: {file_path}")

        text = extract_text(file_path)

        if not text.strip():
            logger.warning("No text extracted")
            await update.message.reply_text("ما قدرت أستخرج نص ❌")
            return

        await update.message.reply_text("جاري الترجمة ⏳")

        translated = translate_text(text)

        with open("translated.txt", "w", encoding="utf-8") as f:
            f.write(translated)

        await update.message.reply_document(document=open("translated.txt", "rb"))
        logger.info("Document sent successfully")
    except Exception as e:
        logger.error(f"Error in handle_file: {e}")
        await update.message.reply_text(f"خطأ: {str(e)} ❌")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Start from user {update.effective_user.id}")
    await update.message.reply_text("أرسل ملف حتى أترجمه 📄➡️🇸🇦")

def main():
    logger.info("Initializing bot...")
    try:
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, start))
        
        logger.info("Bot started successfully ✅")
        app.run_polling()
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    main()
