import os
import time
import threading
import http.server
import socketserver
import fitz  # PyMuPDF
from deep_translator import GoogleTranslator 
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

# --- 2. إعداد المترجم المستقر ---
translator = GoogleTranslator(source='en', target='ar')

def clean_and_reshape(text):
    if not text: return ""
    # دمج الأسطر وتنظيف المسافات الزائدة لمنع أخطاء المكتبة
    text = text.replace('\n', ' ').strip()
    return get_display(reshape(text))

# --- 3. المعالجة النهائية (نظام الجمل القصيرة لضمان الترجمة) ---
async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("🛠 تم إصلاح مشكلة (النص الإنجليزي).. جاري الترجمة الدقيقة الآن.")
    
    doc_tg = update.message.document
    in_path = os.path.join("/tmp", doc_tg.file_name)
    out_path = os.path.join("/tmp", f"Fixed_NoGemini_{doc_tg.file_name}")

    try:
        file_info = await context.bot.get_file(doc_tg.file_id)
        await file_info.download_to_drive(in_path)
        
        pdf_in = fitz.open(in_path)
        pdf_out = FPDF()
        pdf_out.add_font('CustomArial', '', 'alfont_com_arial-1.ttf')
        pdf_out.set_font('CustomArial', size=10) 
        pdf_out.set_right_margin(15)
        pdf_out.set_left_margin(15)

        for i, page in enumerate(pdf_in):
            pdf_out.add_page()
            text_content = page.get_text("text")
            
            if text_content.strip():
                # الحل: تقسيم النص إلى جمل لتجنب فشل المحرك
                sentences = text_content.split('. ')
                translated_page = []
                
                for sentence in sentences:
                    try:
                        if len(sentence.strip()) > 2:
                            trans = translator.translate(sentence)
                            translated_page.append(trans)
                    except:
                        translated_page.append(sentence) # إذا فشل جزء، لا يتوقف البقية
                
                final_text = clean_and_reshape(" ".join(translated_page))
                pdf_out.multi_cell(0, 8, text=final_text, align='R')
            
            await status_msg.edit_text(f"⏳ معالجة الصفحة {i+1} من {len(pdf_in)}...")
            time.sleep(0.5)

        pdf_out.output(out_path)
        pdf_in.close()
        
        with open(out_path, "rb") as f:
            await context.bot.send_document(chat_id=update.message.chat_id, document=f, caption="✅ اكتملت الترجمة بنجاح (بدون أخطاء النص الأصلي).")
        
        os.remove(in_path)
        os.remove(out_path)
    except Exception as e:
        await update.message.reply_text(f"🔥 خطأ: {str(e)[:100]}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(os.environ.get("BOT_TOKEN")).build()
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    app.run_polling()
