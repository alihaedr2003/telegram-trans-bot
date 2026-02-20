from telegram.ext import Updater, MessageHandler, Filters
from deep_translator import GoogleTranslator
from docx import Document
import PyPDF2
import os

TOKEN = "8480545850:AAHN_sG0qKEjdiUAhSbMgY-HjSEplohscus"

def translate_text(text):
    return GoogleTranslator(source='en', target='ar').translate(text)

def extract_text(file_path):
    text = ""

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

    return text

def handle_file(update, context):
    file = update.message.document.get_file()
    file_path = file.download()

    text = extract_text(file_path)

    if not text.strip():
        update.message.reply_text("ما قدرت أستخرج نص ❌")
        return

    update.message.reply_text("جاري الترجمة ⏳")

    translated = translate_text(text)

    with open("translated.txt", "w", encoding="utf-8") as f:
        f.write(translated)

    update.message.reply_document(open("translated.txt", "rb"))

def start(update, context):
    update.message.reply_text("أرسل ملف حتى أترجمه من الإنكليزي للعربي 📄➡️🇸🇦")

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(MessageHandler(Filters.document, handle_file))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, start))

    PORT = int(os.environ.get("PORT", 10000))

    updater.start_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN)
    updater.bot.setWebhook("https://telegram-trans-bot-truv.onrender.com" + TOKEN)

    updater.idle()

main()