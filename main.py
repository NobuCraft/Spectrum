import asyncio
import aiohttp
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# ========== НАСТРОЙКИ ==========
TOKEN = "8326390250:AAEpXRnhLLLi5zUeFC39nfkHDlxR5ZFQ_yQ"
GEMINI_KEY = "AIzaSyBPT4JUIevH0UiwXVY9eQjrY_pTPLeLbNE"

# ========== GEMINI ==========
async def ask_gemini(text):
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={GEMINI_KEY}"
    async with aiohttp.ClientSession() as session:
        data = {"contents": [{"parts": [{"text": text}]}]}
        async with session.post(url, json=data) as resp:
            result = await resp.json()
            return result["candidates"][0]["content"]["parts"][0]["text"]

# ========== TELEGRAM ==========
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    reply = await ask_gemini(msg)
    await update.message.reply_text(f"🤖 {reply}")

# ========== ЗАПУСК ==========
async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    print("✅ Бот запущен! Пиши ему в Telegram...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
