import os
import threading
import http.server
import socketserver
import fitz  # PyMuPDF
import google.generativeai as genai
from fpdf import FPDF
from arabic_reshaper import reshape
from bidi.algorithm import get_display
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# --- الإعداد الجديد لتجاوز أخطاء الـ 404 ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# استخدام Flash لأنه الأحدث والأكثر دعماً في المناطق الجغرافية المختلفة
model = genai.GenerativeModel(
    model_name='gemini-1.5-flash'
)

def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        httpd.serve_forever()

threading.Thread(target=run_health_check_server, daemon=True).start()

def ai_translate(text):
    if not text or len(text.strip()) < 10: return text
    
    # تحسين البرومبت ليكون أوضح للـ AI
    prompt = f"Translate the following medical text into professional Arabic. Output only the Arabic translation:\n\n{text}"
    
    try:
        # محاولة التوليد
        response = model.generate_content(prompt)
        if response and response.text:
            return response.text
        return text
    except Exception as e:
        # هذا سيطبع لك السبب الحقيقي في اللوك إذا فشل
        print(f"❌ AI connection failure: {str(e)}")
        return text

def process_arabic(text):
    if not text: return ""
    return get_display(reshape(text))

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("🧠 جاري الترجمة الأكاديمية (Gemini 1.5)...")
    
    doc_tg = update.message.document
    in_path = os.path.join("/tmp", doc_tg.file_name)
    out_path = os.path.join("/tmp", f"AI_Fixed_{doc_tg.file_name}")

    try:
        file_info = await context.bot.get_file(doc_tg.file_id)
        await file_info.download_to_drive(in_path)

        pdf_in = fitz.open(in_path)
        pdf_out = FPDF()
        
        # استخدام خطك المرتب
        font_file = "alfont_com_arial-1.ttf"
        pdf_out.add_font('CustomArial', '', font_file)
        pdf_out.set_font('CustomArial', size=11)

        for page in pdf_in:
            pdf_out.add_page()
            text_content = page.get_text("text")
            
            if text_content.strip():
                # إرسال النص للـ AI
                translated = ai_translate(text_content)
                final_text = process_arabic(translated)
                pdf_out.multi_cell(0, 8, text=final_text, align='R')
            else:
                pdf_out.ln(10)

        pdf_out.output(out_path)
        pdf_in.close()

        with open(out_path, "rb") as f:
            await context.bot.send_document(chat_id=update.message.chat_id, document=f)
        
        await status_msg.delete()
        os.remove(in_path)
        os.remove(out_path)

    except Exception as e:
        print(f"💥 Critical Error: {e}")
        await update.message.reply_text(f"خطأ: {str(e)[:50]}")

if __name__ == "__main__":
    TOKEN = os.environ.get("BOT_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    print("🚀 تم إطلاق النسخة الداعمة لـ Gemini 1.5 Flash...")
    app.run_polling(drop_pending_updates=True)
