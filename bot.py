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

# خادم الـ Health Check
def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        httpd.serve_forever()

threading.Thread(target=run_health_check_server, daemon=True).start()

BOT_TOKEN = os.environ.get("BOT_TOKEN")

# دالة لتجهيز النص العربي للـ PDF
def prepare_arabic(text):
    if not text: return ""
    reshaped = reshape(text) # ربط الحروف
    return get_display(reshaped) # ضبط الاتجاه

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("📱 جاري تجهيز نسخة PDF متوافقة مع الموبايل...")
    
    document_tg = update.message.document
    input_path = os.path.join("/tmp", document_tg.file_name)
    output_path = os.path.join("/tmp", f"Translated_{document_tg.file_name}")

    try:
        tg_file = await context.bot.get_file(document_tg.file_id)
        await tg_file.download_to_drive(input_path)

        pdf_in = fitz.open(input_path)
        pdf_out = FPDF()
        pdf_out.set_auto_page_break(auto=True, margin=15)
        
        # تحميل الخط (تأكد من رفع ملف arial.ttf في GitHub)
        try:
            pdf_out.add_font('Arial', '', 'alfont_com_arial-1.ttf', uni=True)
            pdf_out.set_font('Arial', size=12)
        except:
            await status_msg.edit_text("❌ خطأ: ملف الخط arial.ttf غير موجود في السيرفر.")
            return

        translator = GoogleTranslator(source='auto', target='ar')

        for page in pdf_in:
            pdf_out.add_page()
            # قراءة النصوص ككتل (Blocks) للحفاظ على وحدة الفقرة العلمية
            blocks = page.get_text("blocks")
            blocks.sort(key=lambda b: (b[1], b[0]))

            for b in blocks:
                raw_text = b[4].replace('\n', ' ').strip()
                if len(raw_text) > 30:
                    translated = translator.translate(raw_text)
                    # تحويل النص ليكون صالحاً للـ PDF العربي
                    final_text = prepare_arabic(translated)
                    
                    # كتابة النص مع محاذاة لليمين
                    pdf_out.multi_cell(0, 8, txt=final_text, align='R')
                    pdf_out.ln(3)

        pdf_out.output(output_path)
        pdf_in.close()

        await status_msg.edit_text("✅ تمت الترجمة بنجاح! تفضل ملفك المنسق:")
        with open(output_path, "rb") as f:
            await context.bot.send_document(chat_id=update.message.chat_id, document=f)
        
        os.remove(input_path)
        os.remove(output_path)
        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"حدث خطأ أثناء الإنشاء: {str(e)}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    
    # إضافة drop_pending_updates لتنظيف الرسائل العالقة عند التشغيل
    print("Academic Bot is starting and cleaning old updates...")
    app.run_polling(drop_pending_updates=True)
    
