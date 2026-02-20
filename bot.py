import os
import threading
import http.server
import socketserver
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# 1. إعداد خادم وهمي لإرضاء Render (Port Binding)
def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"Health check server running on port {port}")
        httpd.serve_forever()

# تشغيل الخادم في Thread منفصل
threading.Thread(target=run_health_check_server, daemon=True).start()

# 2. إعدادات البوت الأساسية
BOT_TOKEN = os.environ.get("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("هلا! ابعثلي ملف PDF لأترجمه.")

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if document.mime_type != "application/pdf":
        await update.message.reply_text("هذا الملف مو PDF.")
        return

    file = await context.bot.get_file(document.file_id)
    # استخدام مجلد tmp للملفات المؤقتة
    file_path = os.path.join("/tmp", document.file_name)
    await file.download_to_drive(file_path)
    await update.message.reply_text(f"تم تحميل: {document.file_name} بنجاح.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"وصلتني رسالتك: {update.message.text}")

if __name__ == "__main__":
    if not BOT_TOKEN:
        print("خطأ: لم يتم العثور على BOT_TOKEN في متغيرات البيئة!")
    else:
        app = ApplicationBuilder().token(BOT_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        
        print("Bot is starting...")
        app.run_polling()
