import os
import time
import threading
import http.server
import socketserver
import fitz  # PyMuPDF
from deep_translator import GoogleTranslator # المحرك الجديد
from fpdf import FPDF
from arabic_reshaper import reshape
from bidi.algorithm import get_display
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# --- 1. خادم المنفذ لـ Render ---
def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    with socketserver.TCPServer(("", port), http.server.SimpleHTTPRequestHandler) as httpd:
        httpd.serve_forever()

threading.Thread(target=run_health_check_server, daemon=True).start()

# --- 2. إعداد المترجم المستقل ---
# هذا المترجم يستخدم نفس خوارزميات موقع جوجل التي أعجبتك
translator = GoogleTranslator(source='en', target='ar')

def process_arabic(text):
    if not text: return ""
    # تنظيف النص لضمان عدم خروجه عن حدود الصفحة
    clean_text = text.replace('\n', ' ').strip()
    return get_display(reshape(clean_text))

# --- 3. المعالجة النهائية ---
async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("🚀 بدأنا! نستخدم الآن محرك Google المباشر (بدون حدود Gemini)...")
    
    doc_tg = update.message.document
    in_path = os.path.join("/tmp", doc_tg.file_name)
    out_path = os.path.join("/tmp", f"GoogleTrans_{doc_tg.file_name}")

    try:
        file_info = await context.bot.get_file(doc_tg.file_id)
        await file_info.download_to_drive(in_path)
        
        pdf_in = fitz.open(in_path)
        pdf_out = FPDF()
        pdf_out.add_font('CustomArial', '', 'alfont_com_arial-1.ttf')
        pdf_out.set_font('CustomArial', size=10) # حجم خط مثالي لمنع ضيق المساحة

        total = len(pdf_in)
        for i, page in enumerate(pdf_in):
            pdf_out.add_page()
            pdf_out.set_right_margin(10)
            pdf_out.set_left_margin(10)
            
            # سحب النص ككتلة واحدة للحفاظ على السياق وجمالية الترجمة
            text_content = page.get_text("text")
            
            if text_content.strip():
                # الترجمة هنا فورية ومجانية ولا تتبع نظام Gemini
                translated = translator.translate(text_content)
                final_text = process_arabic(translated)
                pdf_out.multi_cell(0, 8, text=final_text, align='R')
            
            await status_msg.edit_text(f"⏳ تمت معالجة الصفحة {i+1} من {total}...")
            # انتظار بسيط جداً فقط لعدم إجهاد السيرفر
            time.sleep(1)

        pdf_out.output(out_path)
        pdf_in.close()
        
        with open(out_path, "rb") as f:
            await context.bot.send_document(chat_id=update.message.chat_id, document=f, caption="✅ اكتملت الترجمة بمحرك Google المستقل.")
        
        os.remove(in_path)
        os.remove(out_path)
    except Exception as e:
        await update.message.reply_text(f"🔥 خطأ: {str(e)[:100]}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(os.environ.get("BOT_TOKEN")).build()
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    app.run_polling()
