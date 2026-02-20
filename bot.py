import os
import threading
import http.server
import socketserver
import fitz  # PyMuPDF
from deep_translator import GoogleTranslator
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# 1. خادم الـ Health Check لـ Render
def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        httpd.serve_forever()

threading.Thread(target=run_health_check_server, daemon=True).start()

BOT_TOKEN = os.environ.get("BOT_TOKEN")

# دالة لتقسيم النص (لأن المحركات تحدد عدداً معيناً من الحروف)
def split_text(text, limit=4000):
    return [text[i:i+limit] for i in range(0, len(text), limit)]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أهلاً بك في بوت الترجمة الأكاديمية. أرسل ملف PDF وسأقوم بترجمة محتواه النصي للعربية.")

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sent_message = await update.message.reply_text("جاري استلام الملف ومعالجته أكاديمياً... انتظر قليلاً.")
    
    document = update.message.document
    file = await context.bot.get_file(document.file_id)
    input_path = os.path.join("/tmp", document.file_name)
    await file.download_to_drive(input_path)

    try:
        # قراءة الـ PDF
        doc = fitz.open(input_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text()
        doc.close()

        if not full_text.strip():
            await sent_message.edit_text("لم أستطع استخراج نص من هذا الملف (قد يكون عبارة عن صور).")
            return

        # عملية الترجمة
        await sent_message.edit_text("بدأت عملية الترجمة الأكاديمية...")
        translator = GoogleTranslator(source='auto', target='ar')
        
        # تقسيم النص لضمان عدم حدوث خطأ في حجم الطلب
        chunks = split_text(full_text)
        translated_text = ""
        for chunk in chunks:
            translated_text += translator.translate(chunk) + "\n"

        # حفظ النتيجة في ملف نصي (لأن الـ PDF المترجم يحتاج تنسيقاً معقداً)
        output_filename = f"Translated_{document.file_name.replace('.pdf', '.txt')}"
        output_path = os.path.join("/tmp", output_filename)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(translated_text)

        # إرسال الملف المترجم
        with open(output_path, "rb") as f:
            await context.bot.send_document(chat_id=update.message.chat_id, document=f, caption="تمت الترجمة بنجاح.")
        
        await sent_message.delete()

    except Exception as e:
        await sent_message.edit_text(f"حدث خطأ أثناء المعالجة: {str(e)}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    app.run_polling()
