import os
import threading
import http.server
import socketserver
import fitz  # PyMuPDF
from fpdf import FPDF
from arabic_reshaper import reshape
from bidi.algorithm import get_display
from deep_translator import GoogleTranslator
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# 1. خادم الـ Health Check لـ Render
def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        httpd.serve_forever()

threading.Thread(target=run_health_check_server, daemon=True).start()

BOT_TOKEN = os.environ.get("BOT_TOKEN")

# دالة لمعالجة النص العربي ليظهر بشكل صحيح في الـ PDF
def format_arabic(text):
    reshaped_text = reshape(text)
    bidi_text = get_display(reshaped_text)
    return bidi_text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أهلاً بك. أرسل ملف PDF وسأقوم بترجمته وإعادته لك بصيغة PDF منسقة.")

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("⏳ جاري ترجمة البحث وإعادة بناء ملف الـ PDF...")
    
    document_tg = update.message.document
    input_path = os.path.join("/tmp", document_tg.file_name)
    output_filename = f"Translated_{document_tg.file_name}"
    output_path = os.path.join("/tmp", output_filename)

    try:
        tg_file = await context.bot.get_file(document_tg.file_id)
        await tg_file.download_to_drive(input_path)

        pdf_in = fitz.open(input_path)
        pdf_out = FPDF()
        pdf_out.set_auto_page_break(auto=True, margin=15)
        
        # ملاحظة: يجب توفير ملف خط Arial.ttf في المستودع لدعم العربية
        # إذا لم يتوفر الخط، سيستخدم البوت الخط الافتراضي (وقد لا يظهر النص العربي)
        # سأفترض هنا أنك رفعت ملف خط باسم 'arial.ttf' مع الكود
        try:
            pdf_out.add_font('Arial', '', 'arial.ttf', uni=True)
            pdf_out.set_font('Arial', size=12)
        except:
            pdf_out.set_font("Helvetica", size=12)

        translator = GoogleTranslator(source='auto', target='ar')

        for page in pdf_in:
            pdf_out.add_page()
            text_blocks = page.get_text("blocks")
            text_blocks.sort(key=lambda b: (b[1], b[0]))

            for b in text_blocks:
                original = b[4].replace('\n', ' ').strip()
                if len(original) > 20:
                    translated = translator.translate(original)
                    # معالجة النص للظهور من اليمين لليسار
                    final_text = format_arabic(translated)
                    pdf_out.multi_cell(0, 10, txt=final_text, align='R')
                    pdf_out.ln(2)

        pdf_out.output(output_path)
        pdf_in.close()

        await status_msg.edit_text("✅ اكتملت الترجمة بصيغة PDF.")
        with open(output_path, "rb") as f:
            await context.bot.send_document(chat_id=update.message.chat_id, document=f)
        
        os.remove(input_path)
        os.remove(output_path)
        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"خطأ في الإنشاء: {str(e)}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    app.run_polling()
