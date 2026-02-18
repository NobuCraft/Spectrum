#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
import asyncio
import aiohttp
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройки
TOKEN = os.environ.get("TELEGRAM_TOKEN", "8326390250:AAEpXRnhLLLi5zUeFC39nfkHDlxR5ZFQ_yQ")
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_KEY", "sk-4c18a0f28fce421482cbcedcc33cb18d")

# Логирование
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== DEEPSEEK AI ==========
async def ask_deepseek(question: str) -> str:
    """Спросить у DeepSeek"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": "Ты — полезный ассистент. Отвечай кратко и по делу."},
                        {"role": "user", "content": question}
                    ],
                    "temperature": 0.7
                }
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    return f"❌ Ошибка API: {resp.status}"
    except Exception as e:
        logger.error(f"DeepSeek error: {e}")
        return "😵 Ошибка связи с AI. Попробуй позже."

# ========== КОМАНДЫ ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    await update.message.reply_text(
        "🤖 *DeepSeek Bot*\n\n"
        "Привет! Я тестовый бот с DeepSeek AI.\n\n"
        "📝 *Команды:*\n"
        "• /ask [вопрос] — спросить AI\n"
        "• /test — проверить работу\n"
        "• /id — узнать свой ID",
        parse_mode="Markdown"
    )

async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /ask - спросить AI"""
    if not context.args:
        await update.message.reply_text(
            "❓ Напиши вопрос после /ask\n"
            "Пример: `/ask как дела?`",
            parse_mode="Markdown"
        )
        return
    
    question = " ".join(context.args)
    await update.message.chat.send_action(action="typing")
    
    answer = await ask_deepseek(question)
    await update.message.reply_text(f"🤖 *DeepSeek:*\n{answer}", parse_mode="Markdown")

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /test"""
    await update.message.reply_text("✅ Бот работает!\n🤖 DeepSeek подключен")

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /id"""
    user_id = update.effective_user.id
    await update.message.reply_text(f"🆔 Твой ID: `{user_id}`", parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ответ на любое сообщение"""
    if update.message.text.startswith('/'):
        return
    
    await update.message.chat.send_action(action="typing")
    answer = await ask_deepseek(update.message.text)
    await update.message.reply_text(f"🤖 *DeepSeek:*\n{answer}", parse_mode="Markdown")

# ========== ЗАПУСК ==========
async def main():
    """Запуск бота"""
    print("🚀 Запуск DeepSeek бота...")
    
    app = Application.builder().token(TOKEN).build()
    
    # Регистрируем команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ask", ask))
    app.add_handler(CommandHandler("test", test))
    app.add_handler(CommandHandler("id", id_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print(f"✅ Бот запущен!")
    print(f"🤖 DeepSeek: {'Подключен' if DEEPSEEK_KEY else 'Нет ключа'}")
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    # Держим бот запущенным
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
