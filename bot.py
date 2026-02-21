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
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        httpd.serve_forever()

threading.Thread(target=run_health_check_server, daemon=True).start()

# --- إعداد Gemini المستقر (gemini-pro) ---
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
# نستخدم gemini-pro لأنه الأكثر استقراراً حالياً وتجنباً لخطأ 404
model = genai.GenerativeModel('gemini-pro')

def translate_page(text):
    if not text or len(text.strip()) < 10: return text
    prompt = f"Translate this medical text to professional Arabic. Return ONLY Arabic:\n\n{text}"
    try:
        # محاولة الترجمة مع مهلة انتظار
        response = model.generate_content(prompt)
        if response and response.text:
            return response.text
        return "⚠️ لم يتم استلام استجابة من الموديل"
    except Exception as e:
        return f"⚠️ خطأ في الاتصال: {str(e)[:50]}"

def process_arabic(text):
    return get_display(reshape(text))

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("🔬 جاري محاولة الترجمة باستخدام الموديل المستقر (gemini-pro)...")
    
    doc_tg = update.message.document
    in_path = os.path.join("/tmp", doc_tg.file_name)
    out_path = os.path.join("/tmp", f"Fixed_Trans_{doc_tg.file_name}")

    try:
        file_info = await context.bot.get_file(doc_tg.file_id)
        await file_info.download_to_drive(in_path)

        pdf_in = fitz.open(in_path)
        pdf_out = FPDF()
        pdf_out.add_font('CustomArial', '', 'alfont_com_arial-1.ttf')
        pdf_out.set_font('CustomArial', size=11)

        for i, page in enumerate(pdf_in):
            pdf_out.add_page()
            blocks = page.get_text("blocks")
            blocks.sort(key=lambda b: b[1]) # الحفاظ على الترتيب الصحيح

            # تجميع النص لتقليل الطلبات
            page_content = " ".join([b[4].strip() for b in blocks if b[4].strip()])
            
            if page_content:
                translated = translate_page(page_content)
                final_text = process_arabic(translated)
                pdf_out.multi_cell(0, 10, text=final_text, align='R')
            
            await status_msg.edit_text(f"⏳ معالجة الصفحة {i+1} من {len(pdf_in)}...")
            time.sleep(5) # تأخير كافٍ لتجنب الحظر المجاني

        pdf_out.output(out_path)
        pdf_in.close()

        with open(out_path, "rb") as f:
            await context.bot.send_document(chat_id=update.message.chat_id, document=f, caption="✅ تمت الترجمة بالموديل المستقر.")
        
        await status_msg.delete()
        os.remove(in_path)
        os.remove(out_path)
    except Exception as e:
        await update.message.reply_text(f"🔥 خطأ فني: {str(e)}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(os.environ.get("BOT_TOKEN")).build()
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    app.run_polling(drop_pending_updates=True)
