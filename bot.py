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

# --- 1. خادم المنفذ لـ Render ---
def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        httpd.serve_forever()

threading.Thread(target=run_health_check_server, daemon=True).start()

# --- 2. إعداد Gemini Pro (النسخة المستقرة) ---
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
# العودة للموديل المضمون لضمان عدم حدوث 404
model = genai.GenerativeModel('gemini-pro')

def ai_translate_pro(text):
    if not text or len(text.strip()) < 10: return text
    try:
        # طلب ترجمة مباشر لتقليل استهلاك الـ Tokens وتجنب الـ 429
        response = model.generate_content(f"Translate to professional Arabic:\n{text}")
        if response and response.text:
            return response.text
        return text
    except Exception as e:
        if "429" in str(e):
            time.sleep(15) # انتظار قسري عند الوصول للحد الأقصى
        return text

def process_arabic(text):
    # إزالة أي رموز غريبة قد تكسر المساحة الأفقية
    clean_text = text.replace('\n', ' ').strip()
    return get_display(reshape(clean_text))

# --- 3. معالجة الـ PDF بنظام المساحة الواسعة ---
async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("⚖️ يتم الآن استخدام Gemini Pro بنظام المساحة الواسعة...")
    
    doc_tg = update.message.document
    in_path = os.path.join("/tmp", doc_tg.file_name)
    out_path = os.path.join("/tmp", f"Stable_Pro_{doc_tg.file_name}")

    try:
        file_info = await context.bot.get_file(doc_tg.file_id)
        await file_info.download_to_drive(in_path)
        
        pdf_in = fitz.open(in_path)
        pdf_out = FPDF()
        pdf_out.add_font('CustomArial', '', 'alfont_com_arial-1.ttf')
        
        # استخدام خط أصغر (9) وتوسيع الهوامش لحل مشكلة المساحة
        pdf_out.set_font('CustomArial', size=9)
        pdf_out.set_auto_page_break(auto=True, margin=15)

        total = len(pdf_in)
        for i, page in enumerate(pdf_in):
            pdf_out.add_page()
            # هوامش جانبية لمنع خطأ الـ Horizontal Space
            pdf_out.set_left_margin(10)
            pdf_out.set_right_margin(10)
            
            # ترتيب النصوص لضمان الجودة
            blocks = page.get_text("blocks")
            blocks.sort(key=lambda b: b[1])
            
            full_page_text = " ".join([b[4].strip() for b in blocks if b[4].strip()])
            
            if full_page_text:
                translated = ai_translate_pro(full_page_text)
                final_text = process_arabic(translated)
                # multi_cell مع عرض (0) يأخذ كامل مساحة الصفحة المتاحة
                pdf_out.multi_cell(0, 8, text=final_text, align='R')
            
            await status_msg.edit_text(f"⏳ معالجة الصفحة {i+1} من {total} (Gemini Pro)...")
            time.sleep(8) # تبريد لضمان الصمود ضد 429

        pdf_out.output(out_path)
        pdf_in.close()
        
        with open(out_path, "rb") as f:
            await context.bot.send_document(chat_id=update.message.chat_id, document=f, caption="✅ اكتملت الترجمة بنجاح.")
        
        os.remove(in_path)
        os.remove(out_path)
    except Exception as e:
        await update.message.reply_text(f"🔥 توقف: {str(e)[:50]}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(os.environ.get("BOT_TOKEN")).build()
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    app.run_polling()
