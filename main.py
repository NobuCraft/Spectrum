#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ПРОСТОЙ ТЕСТОВЫЙ БОТ С DEEPSEEK
"""

import asyncio
import aiohttp
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# ========== КОНФИГУРАЦИЯ ==========
TELEGRAM_TOKEN = "8326390250:AAEpXRnhLLLi5zUeFC39nfkHDlxR5ZFQ_yQ"
DEEPSEEK_API_KEY = "sk-f1661a5df02844c8a2a41227c28d1bc7"

# ========== ПРОСТОЙ КЛАСС ДЛЯ DEEPSEEK ==========
class DeepSeekAI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        print("🤖 DeepSeek готов к работе!")

    async def get_response(self, message):
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "Ты дружелюбный бот СПЕКТР. Отвечай кратко и с эмодзи."},
                    {"role": "user", "content": message}
                ],
                "temperature": 0.8,
                "max_tokens": 150
            }
            
            async with session.post(self.api_url, json=data, headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result["choices"][0]["message"]["content"]
                return f"❌ Ошибка API: {resp.status}"

# ========== ОБРАБОТЧИК СООБЩЕНИЙ ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    
    # Показываем что печатает
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    # Получаем ответ от DeepSeek
    response = await context.bot_data['ai'].get_response(text)
    
    # Отправляем ответ
    await update.message.reply_text(f"🤖 **СПЕКТР:** {response}", parse_mode='Markdown')

# ========== ЗАПУСК ==========
async def main():
    # Создаем бота
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Добавляем AI в данные бота
    app.bot_data['ai'] = DeepSeekAI(DEEPSEEK_API_KEY)
    
    # Добавляем обработчик сообщений
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запускаем
    print("🚀 Бот запущен...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    # Держим бота запущенным
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
