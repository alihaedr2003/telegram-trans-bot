import os
import threading
import http.server
import socketserver
import fitz  # PyMuPDF
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt
from deep_translator import GoogleTranslator
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# --- 1. خادم لضمان استمرار الخدمة على Render ---
def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        httpd.serve_forever()

threading.Thread(target=run_health_check_server, daemon=True).start()

# --- 2. إعدادات البوت ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحباً بك في نظام الترجمة الأكاديمية. أرسل ملف PDF وسأقوم بتحويله لملف Word مترجم ومنسق.")

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("⌛ جاري تحليل النص الأكاديمي وتجميع الفقرات...")
    
    document_tg = update.message.document
    input_path = os.path.join("/tmp", document_tg.file_name)
    output_filename = f"Translated_{document_tg.file_name.replace('.pdf', '.docx')}"
    output_path = os.path.join("/tmp", output_filename)

    try:
        tg_file = await context.bot.get_file(document_tg.file_id)
        await tg_file.download_to_drive(input_path)

        # فتح PDF وإنشاء Word
        pdf_doc = fitz.open(input_path)
        word_doc = Document()
        
        translator = GoogleTranslator(source='auto', target='ar')
        
        # استخراج النص بذكاء (تجميع الفقرات المقطعة)
        full_academic_text = ""
        for page in pdf_doc:
            # استخدام get_text("text") يسحب النص بترتيبه الطبيعي
            full_academic_text += page.get_text("text") + " "

        # تنظيف النص من التقطعات السطرية الزائدة التي تسببها ملفات الـ PDF
        clean_text = full_academic_text.replace('\n', ' ').replace('  ', ' ')
        
        # تقسيم النص لفقرات كبيرة لترجمتها (كل 1500 حرف لضمان السياق)
        chunks = [clean_text[i:i+1500] for i in range(0, len(clean_text), 1500)]
        
        await status_msg.edit_text(f"🚀 جاري ترجمة {len(chunks)} كتلة نصية...")

        for chunk in chunks:
            if len(chunk.strip()) > 10:
                translated_part = translator.translate(chunk)
                
                # إضافة الفقرة للـ Word مع تنسيق احترافي
                p = word_doc.add_paragraph(translated_part)
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                # تحسين الخط ليكون مريحاً للقراءة الأكاديمية
                run = p.runs[0]
                run.font.size = Pt(12)
                run.font.name = 'Arial'

        word_doc.save(output_path)
        pdf_doc.close()

        await status_msg.edit_text("✅ اكتملت الترجمة. جاري رفع ملف الـ Word...")
        with open(output_path, "rb") as f:
            await context.bot.send_document(chat_id=update.message.chat_id, document=f)
        
        await status_msg.delete()
        os.remove(input_path)
        os.remove(output_path)

    except Exception as e:
        await status_msg.edit_text(f"❌ عذراً، حدث خطأ: {str(e)}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    app.run_polling()
