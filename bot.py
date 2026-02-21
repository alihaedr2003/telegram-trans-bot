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

# إعداد الذكاء الاصطناعي
genai.configure(api_key=os.environ.get("AIzaSyA6QhTcf4g0TxV99m0xczGiKLY9pGs4chk"))
model = genai.GenerativeModel('gemini-pro')

def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    with socketserver.TCPServer(("", port), http.server.SimpleHTTPRequestHandler) as httpd:
        httpd.serve_forever()

threading.Thread(target=run_health_check_server, daemon=True).start()

def ai_translate(text):
    """ترجمة أكاديمية باستخدام الذكاء الاصطناعي"""
    prompt = f"ترجم النص الطبي التالي إلى لغة عربية أكاديمية رصينة ومفهومة، مع الحفاظ على المصطلحات العلمية بين قوسين عند الضرورة: \n\n {text}"
    try:
        response = model.generate_content(prompt)
        return response.text
    except:
        return text # العودة للنص الأصلي في حال الفشل

def process_arabic(text):
    if not text: return ""
    return get_display(reshape(text))

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("🧠 جاري الترجمة باستخدام الذكاء الاصطناعي لجميع صفحات الملف...")
    
    doc_tg = update.message.document
    in_path = os.path.join("/tmp", doc_tg.file_name)
    out_path = os.path.join("/tmp", f"AI_Translated_{doc_tg.file_name}")

    try:
        file_info = await context.bot.get_file(doc_tg.file_id)
        await file_info.download_to_drive(in_path)

        pdf_in = fitz.open(in_path)
        pdf_out = FPDF()
        pdf_out.add_font('CustomArial', '', 'alfont_com_arial-1.ttf', uni=True)
        pdf_out.set_font('CustomArial', size=11)

        # معالجة كافة الصفحات
        for page_num in range(len(pdf_in)):
            page = pdf_in[page_num]
            pdf_out.add_page()
            
            blocks = page.get_text("blocks")
            blocks.sort(key=lambda b: (b[1], b[0]))

            for b in blocks:
                raw_text = b[4].replace('\n', ' ').strip()
                if len(raw_text) > 30:
                    # استخدام الذكاء الاصطناعي هنا
                    translated = ai_translate(raw_text)
                    final_text = process_arabic(translated)
                    pdf_out.multi_cell(0, 8, txt=final_text, align='R')
                    pdf_out.ln(4)

        pdf_out.output(out_path)
        pdf_in.close()

        await context.bot.send_document(chat_id=update.message.chat_id, document=open(out_path, "rb"))
        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"خطأ: {str(e)}")

if __name__ == "__main__":
    TOKEN = os.environ.get("BOT_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    app.run_polling(drop_pending_updates=True)
