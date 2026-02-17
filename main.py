import os
import asyncio
import aiohttp
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# ========== ПЕРЕМЕННЫЕ ==========
TOKEN = "8326390250:AAG1nTYdy07AuKsYXS3yvDehfU2JuR0RqGo"
GEMINI_KEY = "AIzaSyBPT4JUIevH0UiwXVY9eQjrY_pTPLeLbNE"

print(f"🔑 Токен загружен: {TOKEN[:15]}...")

# ========== GEMINI ==========
async def ask_gemini(text):
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={GEMINI_KEY}"
    async with aiohttp.ClientSession() as session:
        data = {"contents": [{"parts": [{"text": text}]}]}
        async with session.post(url, json=data) as resp:
            if resp.status == 200:
                result = await resp.json()
                return result["candidates"][0]["content"]["parts"][0]["text"]
            return f"Ошибка API: {resp.status}"

# ========== TELEGRAM ==========
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    reply = await ask_gemini(update.message.text)
    await update.message.reply_text(f"🤖 {reply}")

# ========== ЗАПУСК (БЕЗ asyncio.run) ==========
def main():
    print("🚀 Запуск бота...")
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    
    print("✅ Бот готов к работе!")
    
    # Запускаем без asyncio.run()
    app.run_polling()

if __name__ == "__main__":
    main()  # Убрали asyncio.run()
