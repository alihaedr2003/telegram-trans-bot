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
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# خادم الـ Health Check
def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    with socketserver.TCPServer(("", port), http.server.SimpleHTTPRequestHandler) as httpd:
        httpd.serve_forever()

threading.Thread(target=run_health_check_server, daemon=True).start()

def process_arabic_text(text):
    if not text: return ""
    # دمج السطور المكسورة لضمان جملة مفهومة
    text = text.replace('\n', ' ').strip()
    reshaped = reshape(text)
    return get_display(reshaped)

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("⏳ جاري الترجمة والترتيب (النسخة المستقرة)...")
    
    doc_tg = update.message.document
    in_path = os.path.join("/tmp", doc_tg.file_name)
    out_path = os.path.join("/tmp", f"Final_{doc_tg.file_name}")

    try:
        file_info = await context.bot.get_file(doc_tg.file_id)
        await file_info.download_to_drive(in_path)

        pdf_in = fitz.open(in_path)
        pdf_out = FPDF()
        
        # التأكد من الخط
        font_file = "alfont_com_arial-1.ttf"
        pdf_out.add_font('CustomArial', '', font_file)
        pdf_out.set_font('CustomArial', size=11)

        # المترجم المستقر (لا يحتاج API Key)
        translator = GoogleTranslator(source='auto', target='ar')

        for page in pdf_in:
            pdf_out.add_page()
            # استخراج النص كـ 'blocks' للحفاظ على الهيكل
            blocks = page.get_text("blocks")
            blocks.sort(key=lambda b: (b[1], b[0])) # ترتيب من الأعلى للأسفل

            for b in blocks:
                raw_text = b[4].strip()
                if len(raw_text) > 10:
                    try:
                        # ترجمة الكتلة النصية كاملة
                        translated = translator.translate(raw_text)
                        final_text = process_arabic_text(translated)
                        
                        # طباعة النص بـ محاذاة لليمين 'R'
                        pdf_out.multi_cell(0, 8, text=final_text, align='R')
                        pdf_out.ln(2)
                    except:
                        # إذا فشلت الترجمة لسبب ما، لا تتركها إنجليزية بل اكتب تنبيه
                        pdf_out.multi_cell(0, 8, text="[خطأ في ترجمة هذه الفقرة]", align='R')

        pdf_out.output(out_path)
        pdf_in.close()

        with open(out_path, "rb") as f:
            await context.bot.send_document(chat_id=update.message.chat_id, document=f, caption="تم التنسيق والترجمة بنجاح ✅")
        
        await status_msg.delete()
        os.remove(in_path)
        os.remove(out_path)

    except Exception as e:
        await update.message.reply_text(f"خطأ: {str(e)}")

if __name__ == "__main__":
    TOKEN = os.environ.get("BOT_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    print("🚀 البوت المنقذ انطلق...")
    app.run_polling(drop_pending_updates=True)
