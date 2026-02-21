import os
import time
import fitz
import threading
import http.server
import socketserver
import google.generativeai as genai
from fpdf import FPDF
from arabic_reshaper import reshape
from bidi.algorithm import get_display
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# --- 1. خادم المنفذ لـ Render ---
def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        httpd.serve_forever()

threading.Thread(target=run_health_check_server, daemon=True).start()

# --- 2. إعداد Gemini مع نظام كشف الموديلات ---
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

def get_working_model():
    # محاولة تجربة الموديلات المتاحة لتجنب خطأ 404
    models_to_try = ['gemini-1.5-flash', 'gemini-pro', 'gemini-1.0-pro']
    for m in models_to_try:
        try:
            model = genai.GenerativeModel(m)
            # تجربة فحص بسيطة
            model.generate_content("test")
            return model
        except:
            continue
    return genai.GenerativeModel('gemini-pro')

ai_model = get_working_model()

def translate_safe(text):
    if not text or len(text.strip()) < 5: return text
    prompt = f"Translate to academic medical Arabic. Output ONLY Arabic:\n\n{text}"
    try:
        response = ai_model.generate_content(prompt)
        return response.text if response.text else text
    except Exception as e:
        return f"⚠️ Error: {str(e)[:30]}"

def process_arabic(text):
    return get_display(reshape(text))

# --- 3. معالجة الـ PDF (نظام الـ 8 صفحات والترتيب الصحيح) ---
async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("🔬 جاري الترجمة بجيميني... نظام الترتيب مفعل.")
    
    doc_tg = update.message.document
    in_path = os.path.join("/tmp", doc_tg.file_name)
    out_path = os.path.join("/tmp", f"Medical_Final_{doc_tg.file_name}")

    try:
        file_info = await context.bot.get_file(doc_tg.file_id)
        await file_info.download_to_drive(in_path)

        pdf_in = fitz.open(in_path)
        pdf_out = FPDF()
        pdf_out.add_font('CustomArial', '', 'alfont_com_arial-1.ttf')
        pdf_out.set_font('CustomArial', size=11)

        for page in pdf_in:
            pdf_out.add_page() # الحفاظ على عدد الصفحات الأصلي
            blocks = page.get_text("blocks")
            # الترتيب من الأعلى للأسفل لضمان سلامة النص
            blocks.sort(key=lambda b: b[1]) 

            # تجميع نص الصفحة لتقليل عدد الطلبات (لتجنب الحظر)
            full_text = "\n".join([b[4].strip() for b in blocks if b[4].strip()])
            
            if full_text:
                translated = translate_safe(full_text)
                for line in translated.split('\n'):
                    if line.strip():
                        pdf_out.multi_cell(0, 8, text=process_arabic(line), align='R')
                        pdf_out.ln(1)
            
            time.sleep(3) # تأخير بسيط للحفاظ على استقرار الـ API

        pdf_out.output(out_path)
        pdf_in.close()

        with open(out_path, "rb") as f:
            await context.bot.send_document(chat_id=update.message.chat_id, document=f)
        
        await status_msg.delete()
        os.remove(in_path)
        os.remove(out_path)
    except Exception as e:
        await update.message.reply_text(f"خطأ: {str(e)}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(os.environ.get("BOT_TOKEN")).build()
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    app.run_polling(drop_pending_updates=True)
