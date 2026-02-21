import os
import threading
import http.server
import socketserver
import fitz  # PyMuPDF
from fpdf import FPDF
from arabic_reshaper import reshape
from bidi.algorithm import get_display
from deep_translator import GoogleTranslator
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# 1. خادم الـ Health Check لضمان استمرارية الخدمة على Render
def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        httpd.serve_forever()

threading.Thread(target=run_health_check_server, daemon=True).start()

# 2. إعدادات البوت والترجمة
BOT_TOKEN = os.environ.get("BOT_TOKEN")

def prepare_arabic_for_pdf(text):
    """إعادة تشكيل النص العربي ليظهر بشكل صحيح في الـ PDF"""
    if not text: return ""
    reshaped_text = reshape(text)
    bidi_text = get_display(reshaped_text)
    return bidi_text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ النظام جاهز الآن.\n"
        "أرسل ملف PDF البحثي، وسأقوم بترجمته وإعادة بنائه كملف PDF منسق يدعم القراءة من الموبايل."
    )

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"📥 استلام ملف من: {update.message.chat_id}")
    status_msg = await update.message.reply_text("⌛ جاري تحليل الورقة البحثية وترجمتها أكاديمياً...")
    
    document_tg = update.message.document
    input_path = os.path.join("/tmp", document_tg.file_name)
    output_filename = f"Translated_{document_tg.file_name}"
    output_path = os.path.join("/tmp", output_filename)

    try:
        # تحميل الملف
        tg_file = await context.bot.get_file(document_tg.file_id)
        await tg_file.download_to_drive(input_path)

        # إعداد محرك الـ PDF والترجمة
        pdf_in = fitz.open(input_path)
        pdf_out = FPDF()
        pdf_out.set_auto_page_break(auto=True, margin=15)
        
        # تحميل الخط العربي (يجب رفع ملف arial.ttf بجانب الكود)
        try:
            pdf_out.add_font('Arial', '', 'alfont_com_arial-1.ttf', uni=True)
            pdf_out.set_font('Arial', size=11)
        except:
            await status_msg.edit_text("❌ خطأ: ملف الخط arial.ttf غير موجود في المستودع.")
            return

        translator = GoogleTranslator(source='auto', target='ar')

        for page in pdf_in:
            pdf_out.add_page()
            # استخراج النصوص ككتل للحفاظ على سياق الفقرة
            blocks = page.get_text("blocks")
            blocks.sort(key=lambda b: (b[1], b[0])) # ترتيب من الأعلى للأسفل

            for b in blocks:
                original_text = b[4].replace('\n', ' ').strip()
                # معالجة النصوص الطويلة فقط (تجاهل الأرقام والهوامش المبعثرة)
                if len(original_text) > 35:
                    try:
                        translated_text = translator.translate(original_text)
                        # تجهيز النص للعربية (Reshape + Bidi)
                        final_text = prepare_arabic_for_pdf(translated_text)
                        
                        # إضافة النص للـ PDF مع محاذاة لليمين
                        pdf_out.multi_cell(0, 8, txt=final_text, align='R')
                        pdf_out.ln(3) # مسافة بين الفقرات
                    except:
                        continue

        pdf_out.output(output_path)
        pdf_in.close()

        await status_msg.edit_text("✅ اكتملت الترجمة بنجاح!")
        with open(output_path, "rb") as f:
            await context.bot.send_document(
                chat_id=update.message.chat_id, 
                document=f,
                caption="تفضل، نسخة الـ PDF المترجمة والمنسقة للموبايل."
            )
        
        # تنظيف الملفات المؤقتة
        os.remove(input_path)
        os.remove(output_path)
        await status_msg.delete()

    except Exception as e:
        print(f"Error: {e}")
        await status_msg.edit_text(f"حدث خطأ تقني: {str(e)}")

if __name__ == "__main__":
    if not BOT_TOKEN:
        print("❌ Error: BOT_TOKEN is missing!")
    else:
        app = ApplicationBuilder().token(BOT_TOKEN).build()
        
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
        
        print("🚀 البوت يعمل الآن بنظام Polling مستقر...")
        # تنظيف أي رسائل قديمة لضمان عدم حدوث Conflict
        app.run_polling(drop_pending_updates=True)
