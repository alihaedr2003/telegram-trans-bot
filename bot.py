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

# --- خادم المنفذ لـ Render ---
def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    with socketserver.TCPServer(("", port), http.server.SimpleHTTPRequestHandler) as httpd:
        httpd.serve_forever()

threading.Thread(target=run_health_check_server, daemon=True).start()

# --- إعداد Gemini المستقر ---
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

def final_translate_logic(text):
    if not text or len(text.strip()) < 10: return text
    # برومبت أكاديمي دقيق
    prompt = f"Translate to medical Arabic. Return ONLY the translation:\n\n{text}"
    
    # محاولة الاستدعاء عبر الموديل الأكثر استقراراً عالمياً
    try:
        model = genai.GenerativeModel('models/gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception:
        try:
            # محاولة احتياطية لموديل برو
            model = genai.GenerativeModel('models/gemini-pro')
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"⚠️ خطأ فني: {str(e)[:30]}"

def process_arabic(text):
    return get_display(reshape(text))

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("🔬 جاري الترجمة.. سأحدثك بعد كل صفحة.")
    doc_tg = update.message.document
    in_path = os.path.join("/tmp", doc_tg.file_name)
    out_path = os.path.join("/tmp", f"Fixed_{doc_tg.file_name}")

    try:
        file_info = await context.bot.get_file(doc_tg.file_id)
        await file_info.download_to_drive(in_path)
        pdf_in = fitz.open(in_path)
        pdf_out = FPDF()
        pdf_out.add_font('CustomArial', '', 'alfont_com_arial-1.ttf')
        pdf_out.set_font('CustomArial', size=11)

        for i, page in enumerate(pdf_in):
            pdf_out.add_page()
            # ترتيب الأسطر كما في ورقة البكتيريا الناجحة
            blocks = page.get_text("blocks")
            blocks.sort(key=lambda b: b[1]) 
            
            page_text = " ".join([b[4].strip() for b in blocks if b[4].strip()])
            if page_text:
                translated = final_translate_logic(page_text)
                pdf_out.multi_cell(0, 10, text=process_arabic(translated), align='R')
            
            await status_msg.edit_text(f"⏳ الصفحة {i+1} من {len(pdf_in)} اكتملت.")
            time.sleep(4)

        pdf_out.output(out_path)
        pdf_in.close()
        with open(out_path, "rb") as f:
            await context.bot.send_document(chat_id=update.message.chat_id, document=f)
        await status_msg.delete()
    except Exception as e:
        await update.message.reply_text(f"🔥 تعذر الإكمال: {str(e)}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(os.environ.get("BOT_TOKEN")).build()
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    app.run_polling()
