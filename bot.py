import os
import time
import requests
import fitz
import threading
import http.server
import socketserver
from fpdf import FPDF
from arabic_reshaper import reshape
from bidi.algorithm import get_display
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# --- 1. خادم المنفذ لضمان بقاء البوت حياً في Render ---
def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"📡 Port {port} is active")
        httpd.serve_forever()

threading.Thread(target=run_health_check_server, daemon=True).start()

# --- 2. دالة الترجمة مع نظام كشف الأخطاء ---
def deepseek_translate_debug(text):
    if not text or len(text.strip()) < 5: return text
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    url = "https://api.deepseek.com/v1/chat/completions"
    
    try:
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "Translate to academic Arabic. ONLY Arabic."},
                {"role": "user", "content": text}
            ],
            "timeout": 40
        }
        response = requests.post(url, json=payload, headers={"Authorization": f"Bearer {api_key}"})
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return f"⚠️ API Error {response.status_code}: {response.text[:30]}"
    except Exception as e:
        return f"❌ Error: {str(e)[:30]}"

def process_arabic(text):
    return get_display(reshape(text))

# --- 3. معالجة الـ PDF (النسخة المنضبطة 8 صفحات) ---
async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("🔍 جاري المعالجة (نظام الترتيب الصحيح وكشف الأخطاء)...")
    
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

        for page in pdf_in:
            pdf_out.add_page() # صفحة واحدة لكل صفحة أصلية
            blocks = page.get_text("blocks")
            blocks.sort(key=lambda b: b[1]) # الترتيب من الأعلى للأسفل

            for b in blocks:
                content = b[4].strip()
                if content:
                    translated = deepseek_translate_debug(content)
                    final_text = process_arabic(translated)
                    pdf_out.multi_cell(0, 8, text=final_text, align='R')
                    pdf_out.ln(1)
            
            time.sleep(0.5)

        pdf_out.output(out_path)
        pdf_in.close()

        # إرسال الملف المترجم للمستخدم
        with open(out_path, "rb") as f:
            await context.bot.send_document(chat_id=update.message.chat_id, document=f, caption="✅ اكتملت الترجمة الأكاديمية بنجاح.")
        
        await status_msg.delete()
        os.remove(in_path)
        os.remove(out_path)

    except Exception as e:
        await update.message.reply_text(f"🔥 خطأ تقني: {str(e)}")

# --- 4. تشغيل البوت ---
if __name__ == "__main__":
    TOKEN = os.environ.get("BOT_TOKEN")
    if not TOKEN:
        print("❌ Missing BOT_TOKEN")
    else:
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
        print("🚀 البوت يعمل الآن بكامل طاقته...")
        app.run_polling(drop_pending_updates=True)
