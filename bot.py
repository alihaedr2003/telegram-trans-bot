import os
import threading
import http.server
import socketserver
import fitz  # PyMuPDF
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from deep_translator import GoogleTranslator
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# --- 1. إعداد خادم وهمي لإبقاء البوت حياً على Render ---
def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"Health check server running on port {port}")
        httpd.serve_forever()

# تشغيل الخادم في Thread منفصل لتجنب إيقاف البوت
threading.Thread(target=run_health_check_server, daemon=True).start()

# --- 2. إعدادات البوت والترجمة ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "أهلاً بك في نظام الترجمة الأكاديمية.\n\n"
        "قم بإرسال ملف PDF، وسأقوم بترجمة محتواه بدقة مع الحفاظ على ترتيب الفقرات، "
        "وسأرسل لك النتيجة في ملف Word منسق."
    )

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # رسالة انتظار للمستخدم
    status_msg = await update.message.reply_text("📥 جاري استلام الملف وتحليله أكاديمياً...")
    
    document_tg = update.message.document
    if document_tg.mime_type != "application/pdf":
        await status_msg.edit_text("عذراً، يجب أن يكون الملف بصيغة PDF فقط.")
        return

    # مسارات الملفات المؤقتة في رندر
    input_path = os.path.join("/tmp", document_tg.file_name)
    output_filename = f"Translated_{document_tg.file_name.replace('.pdf', '.docx')}"
    output_path = os.path.join("/tmp", output_filename)

    try:
        # تحميل الملف من تليجرام
        tg_file = await context.bot.get_file(document_tg.file_id)
        await tg_file.download_to_drive(input_path)

        # فتح الـ PDF
        pdf_doc = fitz.open(input_path)
        word_doc = Document()
        
        # إعداد المترجم
        translator = GoogleTranslator(source='auto', target='ar')
        
        await status_msg.edit_text("📖 جاري استخراج الفقرات وترجمتها... قد يستغرق ذلك وقتاً حسب حجم الملف.")

        for page in pdf_doc:
            # قراءة النصوص على شكل كتل (Blocks) للحفاظ على السياق العلمي
            blocks = page.get_text("blocks")
            # ترتيب الكتل من الأعلى للأسفل لضمان منطقية القراءة
            blocks.sort(key=lambda b: (b[1], b[0])) 

            for b in blocks:
                original_text = b[4].replace('\n', ' ').strip()
                
                # ترجمة الكتل النصية التي تحتوي على محتوى حقيقي فقط
                if len(original_text) > 20:
                    try:
                        translated_text = translator.translate(original_text)
                        
                        # إضافة الفقرة لملف Word وتنسيقها للعربية
                        p = word_doc.add_paragraph(translated_text)
                        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT # محاذاة من اليمين لليسار
                    except:
                        continue # في حال فشلت ترجمة كتلة معينة يستمر في الباقي

        # حفظ ملف الـ Word النهائي
        word_doc.save(output_path)
        pdf_doc.close()

        # إرسال الملف المترجم للمستخدم
        await status_msg.edit_text("✅ تمت الترجمة بنجاح! جاري رفع الملف...")
        with open(output_path, "rb") as f:
            await context.bot.send_document(
                chat_id=update.message.chat_id,
                document=f,
                caption="تفضل، هذا ملفك المترجم منسق بصيغة Word."
            )
        
        # حذف الملفات المؤقتة لتوفير المساحة
        if os.path.exists(input_path): os.remove(input_path)
        if os.path.exists(output_path): os.remove(output_path)
        await status_msg.delete()

    except Exception as e:
        print(f"Error: {e}")
        await status_msg.edit_text(f"حدث خطأ تقني أثناء المعالجة: {str(e)}")

# --- 3. تشغيل التطبيق ---
if __name__ == "__main__":
    if not BOT_TOKEN:
        print("Error: BOT_TOKEN is missing!")
    else:
        # بناء التطبيق
        application = ApplicationBuilder().token(BOT_TOKEN).build()
        
        # إضافة المعالجات
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
        
        print("Academic Bot is live and running...")
        application.run_polling()
