from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import os

# ⚠️ التوكن يُقرأ من متغير البيئة في Render
BOT_TOKEN = os.environ["BOT_TOKEN"]

# دالة الرد على /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "هلا! ابعثلي ملف PDF لأترجمه أو أي رسالة نصية للتجربة."
    )

# دالة التعامل مع ملفات PDF
async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if document.mime_type != "application/pdf":
        await update.message.reply_text("هذا الملف مو PDF. حاول ترسل PDF.")
        return

    file = await context.bot.get_file(document.file_id)
    file_path = f"./{document.file_name}"
    await file.download_to_drive(file_path)
    await update.message.reply_text(f"استلمت الملف: {document.file_name}\nهسه نقدر نبدأ الترجمة.")

# دالة التعامل مع النصوص العادية
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    await update.message.reply_text(f"رسالتك: {text}\nابعتلي PDF حتى أترجمه.")

# بناء التطبيق
app = ApplicationBuilder().token(BOT_TOKEN).build()

# إضافة الهاندلرز
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

# تشغيل البوت (polling)
if __name__ == "__main__":
    print("Bot is running...")
    app.run_polling()
