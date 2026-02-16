#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ПРОСТОЙ ТЕСТОВЫЙ БОТ С OPENROUTER (БЕСПЛАТНО)
"""

import asyncio
import aiohttp
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# ========== КОНФИГУРАЦИЯ ==========
TELEGRAM_TOKEN = "8326390250:AAEpXRnhLLLi5zUeFC39nfkHDlxR5ZFQ_yQ"
OPENROUTER_API_KEY = "sk-or-v1-64a6d8d8c5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5"  # Получи на openrouter.ai

class OpenRouterAI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        print("🤖 OpenRouter готов к работе!")

    async def get_response(self, message):
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://t.me/your_bot",
                "X-Title": "Spectrum Bot"
            }
            
            # Используем бесплатную модель
            data = {
                "model": "mistralai/mistral-7b-instruct:free",
                "messages": [
                    {"role": "system", "content": "Ты дружелюбный бот СПЕКТР. Отвечай кратко и с эмодзи."},
                    {"role": "user", "content": message}
                ]
            }
            
            async with session.post(self.api_url, json=data, headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    error = await resp.text()
                    return f"❌ Ошибка {resp.status}: {error[:100]}"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    response = await context.bot_data['ai'].get_response(text)
    await update.message.reply_text(f"🤖 **СПЕКТР:** {response}", parse_mode='Markdown')

async def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.bot_data['ai'] = OpenRouterAI(OPENROUTER_API_KEY)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🚀 Бот запущен... Жди сообщения!")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
