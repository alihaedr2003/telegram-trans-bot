from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, filters
import os

TOKEN = os.environ.get("BOT_TOKEN")  # ⚠️ خلي TOKEN كمتغير بيئة على Render
bot = Bot(token=TOKEN)
app = Flask(__name__)

# dispatcher بدون asyncio ليشتغل على Render 3.14 مباشرة
dispatcher = Dispatcher(bot=bot, update_queue=None, use_context=True)

def start(update, context):
    update.message.reply_text("هلا! ابعثلي PDF حتى أترجمه.")

def handle_message(update, context):
    text = update.message.text
    update.message.reply_text(f"رسالتك: {text}")  # رح نبدلها بالترجمة بعدين

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

@app.route("/")
def index():
    return "Bot is running!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
