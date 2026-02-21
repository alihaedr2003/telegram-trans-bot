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

# خادم الـ Health Check لـ Render
def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        httpd.serve_forever()

threading.Thread(target=run_health_check_server, daemon=True).start()

BOT_TOKEN = os.environ.get("BOT_TOKEN")

def process_arabic_text(text):
    """معالجة النص ليكون مرتباً من اليمين لليسار وبحروف متصلة"""
    if not text: return ""
    reshaped = reshape(text)  # ربط الحروف
    bidi_text = get_display(reshaped)  # ضبط اتجاه الجملة (عربي + إنجليزي)
    return bidi_text

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"📥 ملف جديد من: {update.message.chat_id}")
    status_msg = await update.message.reply_text("📏 جاري إعادة ترتيب وترجمة النص أكاديمياً...")
    
    document_tg = update.message.document
    input_path = os.path.join("/tmp", document_tg.file_name)
    output_path = os.path.join("/tmp", f"Fixed_{document_tg.file_name}")

    try:
        tg_file = await context.bot.get_file(document_tg.file_id)
        await tg_file.download_to_drive(input_path)

        pdf_in = fitz.open(input_path)
        pdf_out = FPDF()
        pdf_out.set_auto_page_break(auto=True, margin=15)
        
        # استخدام اسم الخط الخاص بك
        font_name = "alfont_com_arial-1.ttf"
        try:
            pdf_out.add_font('CustomArial', '', font_name, uni=True)
            pdf_out.set_font('CustomArial', size=11)
        except Exception as e:
            await status_msg.edit_text(f"❌ خطأ: لم يتم العثور على ملف الخط {font_name}")
            return

        translator = GoogleTranslator(source='auto', target='ar')

        for page in pdf_in:
            pdf_out.add_page()
            # استخراج النص كـ 'blocks' للحفاظ على ترتيب الفقرات
            blocks = page.get_text("blocks")
            blocks.sort(key=lambda b: (b[1], b[0])) # الترتيب من الأعلى للأسفل

            for b in blocks:
                # b[4] هو النص، نقوم بإزالة الفواصل السطرية الزائدة لدمج الفقرة
                raw_text = b[4].replace('\n', ' ').strip()
                
                if len(raw_text) > 20: # تجاهل الرموز والكلمات المفردة المبعثرة
                    translated = translator.translate(raw_text)
                    # تحويل النص ليكون مرتباً (Right-to-Left)
                    final_text = process_arabic_text(translated)
                    
                    # الكتابة في الـ PDF مع محاذاة لليمين 'R'
                    pdf_out.multi_cell(0, 7, txt=final_text, align='R')
                    pdf_out.ln(2) # مسافة بسيطة بين الكتل

        pdf_out.output(output_path)
        pdf_in.close()

        await status_msg.edit_text("✅ اكتملت الترجمة والترتيب.")
        with open(output_path, "rb") as f:
            await context.bot.send_document(chat_id=update.message.chat_id, document=f)
        
        os.remove(input_path)
        os.remove(output_path)
        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"حدث خطأ في التنسيق: {str(e)}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    
    print("🚀 البوت انطلق بالنسخة المرتبة...")
    # تنظيف أي رسائل سابقة لمنع التداخل
    app.run_polling(drop_pending_updates=True)
