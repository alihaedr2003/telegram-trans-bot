import os
import threading
import http.server
import socketserver
import fitz 
import google.generativeai as genai
import time
from fpdf import FPDF
from arabic_reshaper import reshape
from bidi.algorithm import get_display
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# --- خادم المنفذ لضمان بقاء البوت حياً ---
def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        httpd.serve_forever()

threading.Thread(target=run_health_check_server, daemon=True).start()

# --- إعداد الذكاء الاصطناعي ---
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

def ai_translate_page(text):
    if not text or len(text.strip()) < 5: return text
    # برومبت مكثف لترجمة صفحة كاملة بطلب واحد
    prompt = f"Translate this text to academic Arabic. Maintain structure. Output only Arabic:\n\n{text}"
    try:
        response = model.generate_content(prompt)
        return response.text if response.text else text
    except Exception as e:
        print(f"⚠️ Error: {e}")
        time.sleep(2) # تأخير بسيط في حال وجود ضغط
        return text

def process_arabic(text):
    return get_display(reshape(text))

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("🔬 جاري المعالجة الأكاديمية... نظام الطلقة الواحدة مفعل.")
    
    doc_tg = update.message.document
    in_path = os.path.join("/tmp", doc_tg.file_name)
    out_path = os.path.join("/tmp", f"Medical_Trans_{doc_tg.file_name}")

    try:
        file_info = await context.bot.get_file(doc_tg.file_id)
        await file_info.download_to_drive(in_path)

        pdf_in = fitz.open(in_path)
        pdf_out = FPDF()
        pdf_out.add_font('CustomArial', '', 'alfont_com_arial-1.ttf')
        pdf_out.set_font('CustomArial', size=11)

        for page in pdf_in:
            pdf_out.add_page()
            # سحب النص ككتل لضمان التنسيق الصحيح
            blocks = page.get_text("blocks")
            blocks.sort(key=lambda b: b[1]) 
            
            # تجميع نص الصفحة لتقليل عدد الطلبات (لأجل الـ 20 مستخدم)
            page_content = "\n".join([b[4].strip() for b in blocks if b[4].strip()])
            
            if page_content:
                translated = ai_translate_page(page_content)
                # تقسيم الناتج لفقرات لعرضه بشكل مريح
                for line in translated.split('\n'):
                    if line.strip():
                        pdf_out.multi_cell(0, 8, text=process_arabic(line), align='R')
                        pdf_out.ln(1)
            
        pdf_out.output(out_path)
        pdf_in.close()

        with open(out_path, "rb") as f:
            await context.bot.send_document(chat_id=update.message.chat_id, document=f)
        await status_msg.delete()
    except Exception as e:
        await update.message.reply_text(f"حدث خطأ: {e}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(os.environ.get("BOT_TOKEN")).build()
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    app.run_polling()
