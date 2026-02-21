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

# --- 1. ضمان بقاء السيرفر حياً ---
def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    with socketserver.TCPServer(("", port), http.server.SimpleHTTPRequestHandler) as httpd:
        httpd.serve_forever()

threading.Thread(target=run_health_check_server, daemon=True).start()

# --- 2. إعداد Gemini (النسخة اللي جانت تشتغل عندك) ---
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
# سنستخدم 'gemini-pro' كونه الأكثر استقراراً في الكود القديم الخاص بك
model = genai.GenerativeModel('gemini-pro')

def translate_logic(text):
    if not text or len(text.strip()) < 10: return text
    try:
        # نظام الطلب الواحد المركز لكل صفحة لضمان عدم الرجوع للإنجليزية
        response = model.generate_content(f"Translate the following medical text to academic Arabic. Return ONLY the translation:\n\n{text}")
        if response and response.text:
            return response.text
        return text # في حال فشل الاستجابة يرجع النص الأصلي كحماية
    except Exception as e:
        print(f"Error: {e}")
        return text

def process_arabic(text):
    return get_display(reshape(text))

# --- 3. المعالجة مع نظام العداد ومنظم النبضات ---
async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("🧬 تم استلام الملف. جاري المعالجة بنظام (الصفحة المستقلة)...")
    
    doc_tg = update.message.document
    in_path = os.path.join("/tmp", doc_tg.file_name)
    out_path = os.path.join("/tmp", f"Translated_{doc_tg.file_name}")

    try:
        file_info = await context.bot.get_file(doc_tg.file_id)
        await file_info.download_to_drive(in_path)
        
        pdf_in = fitz.open(in_path)
        pdf_out = FPDF()
        pdf_out.add_font('CustomArial', '', 'alfont_com_arial-1.ttf')
        pdf_out.set_font('CustomArial', size=11)

        total = len(pdf_in)
        for i, page in enumerate(pdf_in):
            pdf_out.add_page()
            
            # التعديل المهم: ترتيب الأسطر لمنع العكس
            blocks = page.get_text("blocks")
            blocks.sort(key=lambda b: b[1]) 
            
            # تجميع نص الصفحة بالكامل في طلب واحد لضمان جودة الترجمة
            page_text = " ".join([b[4].strip() for b in blocks if b[4].strip()])
            
            if page_text:
                # ترجمة الصفحة كاملةً
                translated = translate_logic(page_text)
                pdf_out.multi_cell(0, 10, text=process_arabic(translated), align='R')
            
            # تحديث العداد للمستخدم لكي لا ينتظر على الفراغ
            await status_msg.edit_text(f"⏳ معالجة الصفحة {i+1} من {total}...")
            
            # "منظم النبضات": تأخير 6 ثوانٍ لضمان عدم تجاوز حد 15 طلب/دقيقة في Gemini المجاني
            time.sleep(6)

        pdf_out.output(out_path)
        pdf_in.close()
        
        with open(out_path, "rb") as f:
            await context.bot.send_document(chat_id=update.message.chat_id, document=f, caption="✅ اكتملت الترجمة الأكاديمية بنجاح.")
        
        await status_msg.delete()
        os.remove(in_path)
        os.remove(out_path)
        
    except Exception as e:
        await update.message.reply_text(f"🔥 توقف البوت بسبب: {str(e)}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(os.environ.get("BOT_TOKEN")).build()
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    app.run_polling()
