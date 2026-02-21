import os
import time
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

# 1. دالة البورت (لضمان بقاء السيرفر حياً في Render)
def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"✅ Port {port} is now active.")
        httpd.serve_forever()

threading.Thread(target=run_health_check_server, daemon=True).start()

# 2. إعداد Gemini (المحرك الذي تفضله)
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

def get_model():
    # نظام البحث التلقائي عن الموديل المتاح لتجنب خطأ 404
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if 'flash' in m.name or 'pro' in m.name:
                    return genai.GenerativeModel(m.name)
    except:
        return genai.GenerativeModel('gemini-pro')

model = get_model()

def ai_translate_academic(text):
    if not text or len(text.strip()) < 10: return text
    # برومبت أكاديمي كما طلبت في شخصيتك المفضلة
    prompt = (
        "You are a medical professor. Translate this medical text into professional academic Arabic. "
        "Return ONLY the Arabic translation. Keep medical terms in brackets if necessary:\n\n" + text
    )
    try:
        # نظام المحاولة لضمان عدم إرجاع نص إنجليزي
        response = model.generate_content(prompt)
        if response and response.text:
            return response.text
        return "⚠️ فشل في استلام الترجمة"
    except Exception as e:
        print(f"API Error: {e}")
        return "⚠️ خطأ في الاتصال بالذكاء الاصطناعي"

def process_arabic(text):
    return get_display(reshape(text))

# 3. معالجة الملف بنظام "العداد" ومنع التكرار
async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("🧬 جاري التحليل والترجمة الأكاديمية (صفحة بصفحة)...")
    
    doc_tg = update.message.document
    in_path = os.path.join("/tmp", doc_tg.file_name)
    out_path = os.path.join("/tmp", f"Academic_Fixed_{doc_tg.file_name}")

    try:
        file_info = await context.bot.get_file(doc_tg.file_id)
        await file_info.download_to_drive(in_path)

        pdf_in = fitz.open(in_path)
        pdf_out = FPDF()
        pdf_out.add_font('CustomArial', '', 'alfont_com_arial-1.ttf')
        pdf_out.set_font('CustomArial', size=11)

        total_pages = len(pdf_in)
        for i, page in enumerate(pdf_in):
            pdf_out.add_page()
            
            # ترتيب النصوص لضمان البداية من العنوان (حل مشكلة الخربطة)
            blocks = page.get_text("blocks")
            blocks.sort(key=lambda b: b[1]) # ترتيب من الأعلى للأسفل
            
            text_to_translate = "\n".join([b[4].strip() for b in blocks if b[4].strip()])
            
            if text_to_translate:
                translated = ai_translate_academic(text_to_translate)
                # إذا فشلت الترجمة، نضع رسالة واضحة بدلاً من الإنجليزية
                final_text = process_arabic(translated)
                pdf_out.multi_cell(0, 8, text=final_text, align='R')
            
            # تحديث العداد لكي لا تنتظر على الفراغ
            await status_msg.edit_text(f"⏳ تمت ترجمة {i+1} من أصل {total_pages} صفحات...")
            
            # أهم تعديل: انتظار 5 ثوانٍ بين الصفحات لضمان عدم حظر Gemini
            time.sleep(5)
            
        pdf_out.output(out_path)
        pdf_in.close()

        with open(out_path, "rb") as f:
            await context.bot.send_document(chat_id=update.message.chat_id, document=f, caption="✅ تم الانتهاء من الترجمة الطبية.")
        
        await status_msg.delete()
        os.remove(in_path)
        os.remove(out_path)
    except Exception as e:
        await update.message.reply_text(f"حدث خطأ فني: {str(e)}")

if __name__ == "__main__":
    TOKEN = os.environ.get("BOT_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    print("🚀 البوت انطلق بالنسخة المستقرة...")
    app.run_polling(drop_pending_updates=True)
