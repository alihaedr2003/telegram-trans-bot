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

# 1. دالة البورت (المنقذ من الـ Timeout)
def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    # توجيه السيرفر للعمل على المنفذ المطلوب من قبل Render
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"✅ Port {port} is now active.")
        httpd.serve_forever()

# تشغيل دالة البورت في خلفية الكود لكي لا يتوقف البوت
threading.Thread(target=run_health_check_server, daemon=True).start()

# 2. إعداد الذكاء الاصطناعي (Gemini)
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

def get_model():
    try:
        # البحث عن أفضل موديل متاح في حسابك لتجنب خطأ 404
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                return genai.GenerativeModel(m.name)
    except:
        return genai.GenerativeModel('gemini-pro')

model = get_model()

def ai_translate_academic(text):
    if not model or len(text.strip()) < 10: return text
    prompt = (
        "You are a medical professor. Translate this histology text into professional academic Arabic. "
        "Use precise medical terminology. Output ONLY the Arabic text:\n\n" + text
    )
    try:
        response = model.generate_content(prompt)
        return response.text if response.text else text
    except:
        return text

def process_arabic(text):
    return get_display(reshape(text))

# 3. معالجة الملف
async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("🧬 جاري الترجمة الأكاديمية... يرجى الانتظار.")
    
    doc_tg = update.message.document
    in_path = os.path.join("/tmp", doc_tg.file_name)
    out_path = os.path.join("/tmp", f"Academic_{doc_tg.file_name}")

    try:
        file_info = await context.bot.get_file(doc_tg.file_id)
        await file_info.download_to_drive(in_path)

        pdf_in = fitz.open(in_path)
        pdf_out = FPDF()
        # تأكد أن اسم ملف الخط صحيح وموجود في الـ GitHub عندك
        pdf_out.add_font('CustomArial', '', 'alfont_com_arial-1.ttf')
        pdf_out.set_font('CustomArial', size=11)

        for page in pdf_in:
            pdf_out.add_page()
            text_content = page.get_text("text")
            if text_content.strip():
                # الترجمة عبر Gemini
                translated = ai_translate_academic(text_content)
                
                # إصلاح التقديم والتأخير: نقوم بتقسيم النص المترجم لفقرات
                paragraphs = translated.split('\n')
                for para in paragraphs:
                    if para.strip():
                        # معالجة كل فقرة على حدة لضمان عدم تداخل الأسطر
                        final_text = process_arabic(para)
                        # استخدام multi_cell مع تحديد العرض بدقة لمنع الارتداد للسطر الأعلى
                        pdf_out.multi_cell(0, 8, text=final_text, align='R')
                        pdf_out.ln(1) # إضافة فراغ بسيط بين الفقرات للوضوح

            
        pdf_out.output(out_path)
        pdf_in.close()

        with open(out_path, "rb") as f:
            await context.bot.send_document(chat_id=update.message.chat_id, document=f)
        
        await status_msg.delete()
        os.remove(in_path)
        os.remove(out_path)
    except Exception as e:
        await update.message.reply_text(f"حدث خطأ: {str(e)}")

if __name__ == "__main__":
    TOKEN = os.environ.get("BOT_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    print("🚀 البوت انطلق مع دالة البورت ومحرك Gemini...")
    app.run_polling(drop_pending_updates=True)
