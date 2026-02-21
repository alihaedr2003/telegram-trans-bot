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

# --- 1. خادم المنفذ ---
def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        httpd.serve_forever()

threading.Thread(target=run_health_check_server, daemon=True).start()

# --- 2. إعداد Gemini (المجاني والقوي) ---
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

def translate_page_gemini(text):
    if not text or len(text.strip()) < 10: return text
    prompt = f"Translate this medical text to academic Arabic. Return ONLY Arabic:\n\n{text}"
    try:
        response = model.generate_content(prompt)
        return response.text if response.text else text
    except Exception as e:
        return f"⚠️ Gemini Error: {str(e)[:30]}"

def process_arabic(text):
    return get_display(reshape(text))

# --- 3. المعالجة الذكية (منع الـ 80 صفحة وعلاج العكس) ---
async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("🧬 جاري الترجمة بجيميني (نظام الصفحة الواحدة)...")
    
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
            pdf_out.add_page() # صفحة واحدة فقط
            
            blocks = page.get_text("blocks")
            blocks.sort(key=lambda b: b[1]) # حل مشكلة العكس
            
            # تجميع نص الصفحة لتقليل عدد الطلبات (عشان ما ننحظر)
            page_text = "\n".join([b[4].strip() for b in blocks if b[4].strip()])
            
            if page_text:
                translated = translate_page_gemini(page_text)
                for line in translated.split('\n'):
                    if line.strip():
                        pdf_out.multi_cell(0, 8, text=process_arabic(line), align='R')
                        pdf_out.ln(1)
            
            time.sleep(4) # تأخير 4 ثواني لضمان عدم تجاوز الـ 15 طلب في الدقيقة

        pdf_out.output(out_path)
        pdf_in.close()

        with open(out_path, "rb") as f:
            await context.bot.send_document(chat_id=update.message.chat_id, document=f, caption="✅ تمت الترجمة بنجاح وبالمجان!")
        
        await status_msg.delete()
        os.remove(in_path)
        os.remove(out_path)

    except Exception as e:
        await update.message.reply_text(f"🔥 خطأ: {str(e)}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(os.environ.get("BOT_TOKEN")).build()
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    app.run_polling(drop_pending_updates=True)
