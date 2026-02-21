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
    with socketserver.TCPServer(("", port), http.server.SimpleHTTPRequestHandler) as httpd:
        httpd.serve_forever()

threading.Thread(target=run_health_check_server, daemon=True).start()

# --- 2. إعداد Gemini مع نظام "توفير الحصة" ---
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-pro')

def translate_bulk(text_list):
    if not text_list: return []
    # دمج الفقرات في طلب واحد ضخم لتقليل عدد الطلبات (Requests)
    combined_text = "\n---\n".join(text_list)
    try:
        response = model.generate_content(f"Translate these medical paragraphs to Arabic, separate with '---':\n{combined_text}")
        if response and response.text:
            return response.text.split("---")
        return text_list
    except Exception as e:
        if "429" in str(e):
            print("🚨 Quota Hit! Waiting 30 seconds...")
            time.sleep(30) # انتظار طويل لتصفير العداد
        return text_list

def process_arabic(text):
    return get_display(reshape(text))

# --- 3. المعالجة الذكية ---
async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("🛠 نظام (توفير الحصة) مفعل. سأترجم الملف ببطء لضمان النجاح...")
    
    doc_tg = update.message.document
    in_path = os.path.join("/tmp", doc_tg.file_name)
    out_path = os.path.join("/tmp", f"Medical_Stable_{doc_tg.file_name}")

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
            blocks = page.get_text("blocks")
            blocks.sort(key=lambda b: b[1]) # الحفاظ على الترتيب الأكاديمي
            
            # تجميع نصوص الصفحة ومعالجتها كدفعة واحدة (Bulk)
            texts_to_translate = [b[4].strip() for b in blocks if b[4].strip()]
            
            if texts_to_translate:
                translated_list = translate_bulk(texts_to_translate)
                for text in translated_list:
                    pdf_out.multi_cell(0, 8, text=process_arabic(text), align='R')
            
            await status_msg.edit_text(f"⏳ الصفحة {i+1} من {total}.. نظام التبريد يعمل.")
            # انتظار قسري بين الصفحات لتجنب الحظر
            time.sleep(12) 

        pdf_out.output(out_path)
        pdf_in.close()

        with open(out_path, "rb") as f:
            await context.bot.send_document(chat_id=update.message.chat_id, document=f, caption="✅ اكتملت الترجمة بنظام توفير الحصة.")
        
        await status_msg.delete()
        os.remove(in_path)
        os.remove(out_path)
    except Exception as e:
        await update.message.reply_text(f"🔥 توقف مؤقت: {str(e)[:100]}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(os.environ.get("BOT_TOKEN")).build()
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    app.run_polling()
