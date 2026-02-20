import logging
from googletrans import Translator
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'

async def extract_text(file):
    logger.info('Extracting text from file...')
    # Logic to extract text from .txt, .docx, .pdf files goes here.
    logger.info('Text extraction complete.')
    return extracted_text

async def translate_text(text):
    logger.info('Translating text...')
    translator = Translator()
    translated_text = translator.translate(text).text
    logger.info('Translation complete.')
    return translated_text

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info('Handling file...')
    file = update.effective_message.document.get_file()
    logger.info(f'Retrieved file: {file.file_id}')
    file.download('downloaded_file')
    text = await extract_text('downloaded_file')
    translated = await translate_text(text)
    await update.message.reply_text(translated)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info('Bot started.')
    await update.message.reply_text('Send me a file to translate!')

def main():
    logger.info('Starting bot...')
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, start))
    app.add_handler(MessageHandler(filters.DOCUMENT, handle_file))
    app.run_polling()

if __name__ == '__main__':
    main()