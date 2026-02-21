import os
import threading
import http.server
import socketserver
import fitz
import requests # سنحتاج هذه المكتبة للاتصال بـ DeepSeek
from fpdf import FPDF
from arabic_reshaper import reshape
from bidi.algorithm import get_display
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# --- 1. خادم المنفذ ---
def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        httpd.serve_forever()

threading.Thread(target=run_health_check_server, daemon=True).start()

# --- 2. دالة ترجمة DeepSeek الجديدة ---
def deepseek_translate(text):
    if not text or len(text.strip()) < 5: return text
    
    # استبدل بمفتاح DeepSeek الخاص بك في إعدادات Render
    api_key = os.environ.get("DEEPSEEK_API_KEY") 
    url = "https://api.deepseek.com/v1/chat/completions" # رابط الـ API الخاص بهم
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a medical professor. Translate to academic Arabic. Return ONLY translation."},
            {"role": "user", "content": text}
        ],
        "stream": False
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        result = response.json()
        return result['choices'][0]['message']['content']
    except Exception as e:
        print(f"❌ DeepSeek Error: {e}")
        return text # يعيد النص الأصلي إذا فشل الاتصال

def process_arabic(text):
    return get_display(reshape(text))

# --- 3. معالجة الـ PDF ---
async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("🚀 جاري التجربة باستخدام موديل DeepSeek الجديد...")
    
    doc_tg = update.message.document
    in_path = os.path.join("/tmp", doc_tg.file_name)
    out_path = os.path.join("/tmp", f"DeepSeek_{doc_tg.file_name}")

    try:
        file_info = await context.bot.get_file(doc_tg.file_id)
        await file_info.download_to_drive(in_path)

        pdf_in = fitz.open(in_path)
        pdf_out = FPDF()
        pdf_out.add_font('CustomArial', '', 'alfont_com_arial-1.ttf')
        pdf_out.set_font('CustomArial', size=11)

        for page in pdf_in:
            pdf_out.add_page()
            blocks = page.get_text("blocks")
            # الحفاظ على ترتيب الأسطر الذي اكتشفناه في ورقة البكتيريا
            blocks.sort(key=lambda b: b[1]) 

            for b in blocks:
                content = b[4].strip()
                if content:
                    translated = deepseek_translate(content)
                    final_text = process_arabic(translated)
                    pdf_out.multi_cell(0, 8, text=final_text, align='R')
                    pdf_out.ln(1)
            
        pdf_out.output(out_path)
        pdf_in.close()

        with open(out_path, "rb") as f:
            await context.bot.send_document(chat_id=update.message.chat_id, document=f)
        await status_msg.delete()
    except Exception as e:
        await update.message.reply_text(f"خطأ: {e}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(os.environ.get("BOT_TOKEN")).build()
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    app.run_polling()
