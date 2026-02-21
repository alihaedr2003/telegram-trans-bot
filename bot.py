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

# --- 1. تشغيل خادم المنفذ (لحل مشكلة الـ Port في Render) ---
def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"📡 Port {port} is active for Render health check")
        httpd.serve_forever()

threading.Thread(target=run_health_check_server, daemon=True).start()

# --- 2. إعداد الذكاء الاصطناعي بمفتاح جديد وآمن ---
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

def get_best_model():
    try:
        # البحث التلقائي عن الموديل المتوفر لتجنب خطأ 404
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                return genai.GenerativeModel(m.name)
    except Exception as e:
        print(f"⚠️ AI Model Search Error: {e}")
    return genai.GenerativeModel('gemini-1.5-flash')

model = get_best_model()

def ai_translate_academic(text):
    if not model or len(text.strip()) < 10: return text
    prompt = (
        "You are a medical histology professor. Translate this text into professional academic Arabic. "
        "Maintain scientific terms. Output ONLY the Arabic translation:\n\n" + text
    )
    try:
        response = model.generate_content(prompt)
        return response.text if response.text else text
    except Exception as e:
        print(f"❌ Translation Error: {e}")
        return text

def process_arabic(text):
    if not text: return ""
    return get_display(reshape(text))

# --- 3. معالجة الـ PDF ---
async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("🧬 جاري استخدام الذكاء الاصطناعي للترجمة الأكاديمية...")
    
    doc_tg = update.message.document
    in_path = os.path.join("/tmp", doc_tg.file_name)
    out_path = os.path.join("/tmp", f"Medical_AI_{doc_tg.file_name}")

    try:
        file_info = await context.bot.get_file(doc_tg.file_id)
        await file_info.download_to_drive(in_path)

        pdf_in = fitz.open(in_path)
        pdf_out = FPDF()
        # تأكد من رفع ملف الخط alfont_com_arial-1.ttf بجانب الكود في GitHub
        pdf_out.add_font('CustomArial', '', 'alfont_com_arial-1.ttf')
        pdf_out.set_font('CustomArial', size=11)

        for page in pdf_in:
            pdf_out.add_page()
            text_content = page.get_text("text")
            if text_content.strip():
                translated = ai_translate_academic(text_content)
                final_text = process_arabic(translated)
                pdf_out.multi_cell(0, 8, text=final_text, align='R')
            
        pdf_out.output(out_path)
        pdf_in.close()

        with open(out_path, "rb") as f:
            await context.bot.send_document(chat_id=update.message.chat_id, document=f, caption="تمت الترجمة الأكاديمية بنجاح ✅")
        
        await status_msg.delete()
        os.remove(in_path)
        os.remove(out_path)
    except Exception as e:
        await update.message.reply_text(f"حدث خطأ: {str(e)}")

if __name__ == "__main__":
    TOKEN = os.environ.get("BOT_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    print("🚀 البوت انطلق بالمفتاح الجديد وبدعم الـ Port...")
    app.run_polling(drop_pending_updates=True)
