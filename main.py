import asyncio
import aiohttp
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# ТВОИ КЛЮЧИ
TELEGRAM_TOKEN = "8326390250:AAEpXRnhLLLi5zUeFC39nfkHDlxR5ZFQ_yQ"
GEMINI_KEY = "AIzaSyBPT4JUIevH0UiwXVY9eQjrY_pTPLeLbNE"

class Gemini:
    def __init__(self, key):
        # Пробуем gemini-pro
        self.url = f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={key}"

    async def ask(self, text):
        async with aiohttp.ClientSession() as session:
            data = {
                "contents": [{
                    "parts": [{"text": text}]
                }]
            }
            async with session.post(self.url, json=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result["candidates"][0]["content"]["parts"][0]["text"]
                else:
                    error = await resp.text()
                    return f"❌ Ошибка {resp.status}"

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply = await context.bot_data['ai'].ask(update.message.text)
    await update.message.reply_text(f"🤖 {reply}")

async def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.bot_data['ai'] = Gemini(GEMINI_KEY)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    
    print("✅ Бот запущен!")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
