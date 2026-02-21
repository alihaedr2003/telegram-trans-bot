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

# 1. إعداد الذكاء الاصطناعي (الموديل المستقر gemini-pro)
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-pro')

# 2. خادم الـ Health Check لـ Render
def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        httpd.serve_forever()

threading.Thread(target=run_health_check_server, daemon=True).start()

def ai_translate(text):
    """ترجمة أكاديمية احترافية باستخدام Gemini Pro"""
    if len(text.strip()) < 10: return text
    
    prompt = (
        "Translate this medical/academic text into professional Arabic. "
        "Keep the scientific tone. Put technical English terms in parentheses. "
        "Output ONLY the translated Arabic text: \n\n" + text
    )
    try:
        response = model.generate_content(prompt)
        # التأكد من استلام نص صالح
        if response and response.text:
            return response.text
        return text
    except Exception as e:
        print(f"❌ AI Error: {str(e)}")
        return text

def process_arabic(text):
    """إصلاح الحروف العربية واتجاه النص"""
    if not text: return ""
    reshaped = reshape(text)
    return get_display(reshaped)

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("🧠 جاري الترجمة الأكاديمية بواسطة AI... يرجى الانتظار.")
    
    doc_tg = update.message.document
    in_path = os.path.join("/tmp", doc_tg.file_name)
    out_path = os.path.join("/tmp", f"Translated_{doc_tg.file_name}")

    try:
        # تحميل الملف
        file_info = await context.bot.get_file(doc_tg.file_id)
        await file_info.download_to_drive(in_path)

        pdf_in = fitz.open(in_path)
        pdf_out = FPDF()
        
        # إعداد الخط الخاص بك (تأكد من وجود الملف في GitHub)
        font_file = "alfont_com_arial-1.ttf"
        pdf_out.add_font('CustomArial', '', font_file)
        pdf_out.set_font('CustomArial', size=11)

        # ترجمة كافة الصفحات
        for page in pdf_in:
            pdf_out.add_page()
            # استخراج النص كفقرات كاملة لتحسين جودة ترجمة الـ AI
            text_content = page.get_text("text")
            
            if text_content.strip():
                # إرسال النص للذكاء الاصطناعي
                translated = ai_translate(text_content)
                # معالجة النص للعربية (Reshape + Bidi)
                final_text = process_arabic(translated)
                
                # كتابة النص بـ محاذاة لليمين 'R'
                pdf_out.multi_cell(0, 8, text=final_text, align='R')
            else:
                # إذا كانت الصفحة فارغة أو صورة فقط
                pdf_out.cell(0, 10, text="[صفحة تحتوي على رسومات أو فارغة]", align='R')

        pdf_out.output(out_path)
        pdf_in.close()

        # إرسال الملف النهائي
        with open(out_path, "rb") as f:
            await context.bot.send_document(
                chat_id=update.message.chat_id, 
                document=f,
                caption="✅ تمت الترجمة الأكاديمية بنجاح."
            )
        
        await status_msg.delete()
        os.remove(in_path)
        os.remove(out_path)

    except Exception as e:
        print(f"💥 Error: {e}")
        await update.message.reply_text(f"عذراً، حدث خطأ: {str(e)}")

if __name__ == "__main__":
    TOKEN = os.environ.get("BOT_TOKEN")
    if not TOKEN:
        print("❌ BOT_TOKEN missing!")
    else:
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
        
        print("🚀 البوت يعمل الآن بموديل Gemini Pro المستقر...")
        # تنظيف التحديثات القديمة لإنهاء الـ Conflict
        app.run_polling(drop_pending_updates=True)
