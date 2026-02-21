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

# إعداد Gemini
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash') # استخدام flash لأنه أسرع للترجمة

def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    with socketserver.TCPServer(("", port), http.server.SimpleHTTPRequestHandler) as httpd:
        httpd.serve_forever()

threading.Thread(target=run_health_check_server, daemon=True).start()

def ai_translate(text):
    """ترجمة أكاديمية طبية باستخدام ذكاء اصطناعي يفهم السياق"""
    prompt = (
        "You are an expert medical translator. Translate the following text into professional, "
        "academic Arabic. Keep medical terms in English between parentheses. "
        "Ensure the flow is natural and not literal: \n\n" + text
    )
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"AI Error: {e}")
        return text

def process_arabic(text):
    if not text: return ""
    return get_display(reshape(text))

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("🧠 بدأت الترجمة بالذكاء الاصطناعي... قد يستغرق الأمر دقيقة للملفات الطويلة.")
    
    doc_tg = update.message.document
    in_path = os.path.join("/tmp", doc_tg.file_name)
    out_path = os.path.join("/tmp", f"Medical_AI_{doc_tg.file_name}")

    try:
        file_info = await context.bot.get_file(doc_tg.file_id)
        await file_info.download_to_drive(in_path)

        pdf_in = fitz.open(in_path)
        pdf_out = FPDF()
        # تحديث المعاملات لتجنب التحذيرات (حذف uni=True واستخدام text بدلاً من txt)
        pdf_out.add_font('CustomArial', '', 'alfont_com_arial-1.ttf') 
        pdf_out.set_font('CustomArial', size=11)

        for page in pdf_in:
            pdf_out.add_page()
            text_content = page.get_text("text") # قراءة الصفحة كاملة لتحسين سياق الذكاء الاصطناعي
            
            if text_content.strip():
                # ترجمة الصفحة ككتلة واحدة لتسريع العملية وفهم السياق بشكل أفضل
                translated = ai_translate(text_content)
                final_text = process_arabic(translated)
                
                # استخدام 'text' بدلاً من 'txt' لتجنب التحذير في السجلات
                pdf_out.multi_cell(0, 8, text=final_text, align='R')

        pdf_out.output(out_path)
        pdf_in.close()

        with open(out_path, "rb") as f:
            await context.bot.send_document(chat_id=update.message.chat_id, document=f, caption="تمت الترجمة الطبية بواسطة AI")
        
        await status_msg.delete()
        os.remove(in_path)
        os.remove(out_path)

    except Exception as e:
        print(f"Critical Error: {e}")
        await update.message.reply_text(f"حدث خطأ أثناء المعالجة: {str(e)}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(os.environ.get("BOT_TOKEN")).build()
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    print("🚀 البوت انطلق بالنسخة المحدثة (AI + Fast)...")
    app.run_polling(drop_pending_updates=True)
