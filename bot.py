import os
import time
import requests
import fitz
from fpdf import FPDF
from arabic_reshaper import reshape
from bidi.algorithm import get_display
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

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
            # بدلاً من النص الأصلي، نرجع تفاصيل الخطأ
            return f"⚠️ API Error {response.status_code}: {response.text[:50]}"
            
    except Exception as e:
        return f"❌ Connection Error: {str(e)[:50]}"

def process_arabic(text):
    return get_display(reshape(text))

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("🔍 جاري التحليل والترجمة مع نظام كشف الأخطاء...")
    
    doc_tg = update.message.document
    in_path = os.path.join("/tmp", doc_tg.file_name)
    out_path = os.path.join("/tmp", f"Debug_Trans_{doc_tg.file_name}")

    try:
        file_info = await context.bot.get_file(doc_tg.file_id)
        await file_info.download_to_drive(in_path)

        pdf_in = fitz.open(in_path)
        pdf_out = FPDF()
        pdf_out.add_font('CustomArial', '', 'alfont_com_arial-1.ttf')
        pdf_out.set_font('CustomArial', size=11)

        for page in pdf_in:
            # إضافة صفحة واحدة فقط لكل صفحة أصلية (منع تحويل 8 لـ 80)
            pdf_out.add_page()
            
            blocks = page.get_text("blocks")
            # ترتيب الأسطر لضمان بداية الورقة بشكل صحيح
            blocks.sort(key=lambda b: b[1]) 

            for b in blocks:
                content = b[4].strip()
                if content:
                    translated = deepseek_translate_debug(content)
                    final_text = process_arabic(translated)
                    # الكتابة في نفس الصفحة الحالية
                    pdf_out.multi_cell(0, 8, text=final_text, align='R')
                    pdf_out.ln(1)
            
            time.sleep(0.5) # حماية من الحظر

        pdf_out.output(out_path)
        pdf_in.close()

        with open(out_path, "rb") as f:
            await context.bot.send_document(chat_id=update.message.chat_id, document=f)
        await status_msg.delete()
        
    except Exception as e:
        await update.message.reply_text(f"خطأ في معالجة الملف: {str(e)}")

# ... كود الـ Main والـ Port كما هو سابقاً ...
