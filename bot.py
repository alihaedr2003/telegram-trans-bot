import os
import google.generativeai as genai
import fitz
from fpdf import FPDF
from arabic_reshaper import reshape
from bidi.algorithm import get_display
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# --- إعداد المحرك مع فحص الأخطاء ---
def setup_ai():
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        genai.configure(api_key=api_key)
        # محاولة سرد الموديلات المتاحة للتأكد من الاتصال
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                return genai.GenerativeModel(m.name)
    except Exception as e:
        print(f"❌ AI Setup Error: {e}")
    return None

model = setup_ai()

def ai_translate_academic(text):
    if not model or len(text.strip()) < 10: return text
    
    # برومبت (Prompt) طبي صارم
    prompt = (
        "You are a medical professor. Translate this histology text into professional academic Arabic. "
        "Use precise medical terminology (e.g., Mucosa -> الغشاء المخاطي). "
        "Keep the scientific structure. Output ONLY the Arabic text:\n\n" + text
    )
    try:
        response = model.generate_content(prompt)
        return response.text if response.text else text
    except:
        return text

def process_arabic(text):
    return get_display(reshape(text))

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("🔬 جاري التحقق من محرك الذكاء الاصطناعي والترجمة...")
    
    doc_tg = update.message.document
    in_path = os.path.join("/tmp", doc_tg.file_name)
    out_path = os.path.join("/tmp", f"Academic_Ar_{doc_tg.file_name}")

    try:
        file_info = await context.bot.get_file(doc_tg.file_id)
        await file_info.download_to_drive(in_path)

        pdf_in = fitz.open(in_path)
        pdf_out = FPDF()
        pdf_out.add_font('CustomArial', '', 'alfont_com_arial-1.ttf')
        pdf_out.set_font('CustomArial', size=11)

        for page in pdf_in:
            pdf_out.add_page()
            text_content = page.get_text("text")
            if text_content.strip():
                # الترجمة عبر Gemini
                translated = ai_translate_academic(text_content)
                final_text = process_arabic(translated)
                pdf_out.multi_cell(0, 8, text=final_text, align='R')
            
        pdf_out.output(out_path)
        pdf_in.close()

        with open(out_path, "rb") as f:
            await context.bot.send_document(chat_id=update.message.chat_id, document=f)
        
        await status_msg.delete()
    except Exception as e:
        await update.message.reply_text(f"تنبيه: {str(e)}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(os.environ.get("BOT_TOKEN")).build()
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    app.run_polling(drop_pending_updates=True)
