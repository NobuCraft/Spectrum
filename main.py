import os
import aiohttp
import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# ========== ТВОИ КЛЮЧИ ==========
TOKEN = "8326390250:AAG1nTYdy07AuKsYXS3yvDehfU2JuR0RqGo"
GEMINI_KEY = "AIzaSyBPT4JUIevH0UiwXVY9eQjrY_pTPLeLbNE"

# ========== GEMINI С ПРАВИЛЬНЫМ URL ==========
async def ask_gemini(text):
    # ПРАВИЛЬНЫЙ URL для Gemini API
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_KEY}"
    
    async with aiohttp.ClientSession() as session:
        data = {
            "contents": [{
                "parts": [{"text": text}]
            }]
        }
        
        async with session.post(url, json=data) as resp:
            if resp.status == 200:
                result = await resp.json()
                try:
                    return result["candidates"][0]["content"]["parts"][0]["text"]
                except:
                    return "😕 Не удалось получить ответ от Gemini"
            else:
                error_text = await resp.text()
                return f"❌ Ошибка Gemini API: {resp.status}"

# ========== ОБРАБОТЧИК ==========
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    reply = await ask_gemini(update.message.text)
    await update.message.reply_text(f"🤖 {reply}")

# ========== ЗАПУСК ==========
def main():
    print("🚀 Запуск бота...")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    print("✅ Бот готов!")
    app.run_polling()

if __name__ == "__main__":
    main()
