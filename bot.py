import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from deep_translator import GoogleTranslator
from docx import Document
import PyPDF2

TOKEN = "8480545850:AAHN_sG0qKEjdiUAhSbMgY-HjSEplohscus"

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

def translate_text(text):
    return GoogleTranslator(source='en', target='ar').translate(text)

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()
    file_path = await file.download_to_drive()

    text = extract_text(file_path)

    if not text.strip():
        await update.message.reply_text("ما قدرت أستخرج نص ❌")
        return

    await update.message.reply_text("جاري الترجمة ⏳")

    translated = translate_text(text)

    with open("translated.txt", "w", encoding="utf-8") as f:
        f.write(translated)

    await update.message.reply_document(document=open("translated.txt", "rb"))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أرسل ملف حتى أترجمه 📄➡️🇸🇦")

import asyncio

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, start))

    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()



