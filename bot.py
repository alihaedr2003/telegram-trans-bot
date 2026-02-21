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

# --- 1. خادم المنفذ لـ Render ---
def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"📡 Port {port} is active for health check")
        httpd.serve_forever()

threading.Thread(target=run_health_check_server, daemon=True).start()

# --- 2. إعداد Gemini مع نظام الاختيار التلقائي ---
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

def translate_page_smart(text):
    if not text or len(text.strip()) < 10: return text
    # برومبت أكاديمي صارم
    prompt = f"You are a medical professor. Translate this text to academic Arabic. Keep scientific terms. Output ONLY the Arabic translation:\n\n{text}"
    
    # محاولة استخدام الموديلات المتاحة لتجنب 404
    for model_name in ['gemini-1.5-flash', 'gemini-pro']:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            if response.text:
                return response.text
        except:
            continue
    return f"⚠️ Translation Failed for this section"

def process_arabic(text):
    if not text: return ""
    return get_display(reshape(text))

# --- 3. معالجة الـ PDF مع ميزة "التواصل اللحظي" ---
async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("🧬 بدأت المعالجة.. سأخبرك بعد كل صفحة.")
    
    doc_tg = update.message.document
    in_path = os.path.join("/tmp", doc_tg.file_name)
    out_path = os.path.join("/tmp", f"Academic_Final_{doc_tg.file_name}")

    try:
        file_info = await context.bot.get_file(doc_tg.file_id)
        await file_info.download_to_drive(in_path)

        pdf_in = fitz.open(in_path)
        pdf_out = FPDF()
        pdf_out.add_font('CustomArial', '', 'alfont_com_arial-1.ttf')
        pdf_out.set_font('CustomArial', size=11)

        total_pages = len(pdf_in)
        for i, page in enumerate(pdf_in):
            pdf_out.add_page() # صفحة واحدة فقط
            
            blocks = page.get_text("blocks")
            # الترتيب المكاني لمنع التقديم والتأخير
            blocks.sort(key=lambda b: b[1]) 
            
            # تجميع نص الصفحة لتقليل الطلبات
            page_content = "\n".join([b[4].strip() for b in blocks if b[4].strip()])
            
            if page_content:
                translated = translate_page_smart(page_content)
                for line in translated.split('\n'):
                    if line.strip():
                        pdf_out.multi_cell(0, 8, text=process_arabic(line), align='R')
                        pdf_out.ln(1)
            
            # طمأنة المستخدم
            await status_msg.edit_text(f"⏳ تمت ترجمة {i+1} من أصل {total_pages} صفحات...")
            time.sleep(2) # حماية من الحظر (Rate Limit)

        pdf_out.output(out_path)
        pdf_in.close()

        with open(out_path, "rb") as f:
            await context.bot.send_document(chat_id=update.message.chat_id, document=f, caption="✅ اكتملت الترجمة بنجاح.")
        
        os.remove(in_path)
        os.remove(out_path)

    except Exception as e:
        await update.message.reply_text(f"🔥 خطأ تقني: {str(e)[:100]}")

if __name__ == "__main__":
    TOKEN = os.environ.get("BOT_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    print("🚀 البوت انطلق بنظام المراقبة اللحظية...")
    app.run_polling(drop_pending_updates=True)
