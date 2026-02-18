#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import asyncio
from groq import Groq
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ТОКЕНЫ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ
TOKEN = os.environ.get("TELEGRAM_TOKEN")  # Берем из Railway переменных
GROQ_KEY = os.environ.get("GROQ_API_KEY") # Берем из Railway переменных

if not TOKEN or not GROQ_KEY:
    print("❌ Ошибка: Не найдены переменные окружения!")
    print("Добавь в Railway:")
    print("  TELEGRAM_TOKEN = твой_токен")
    print("  GROQ_API_KEY = твой_groq_ключ")
    exit(1)

# ========== GROQ ==========
client = Groq(api_key=GROQ_KEY)

async def ask_groq(question: str) -> str:
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Ты полезный ассистент. Отвечай кратко."},
                {"role": "user", "content": question}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=500
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"❌ Ошибка: {str(e)}"

# ========== КОМАНДЫ ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Groq AI Bot*\n\n"
        "Привет! Я использую Groq Cloud.\n\n"
        "📝 *Команды:*\n"
        "• /ask [вопрос] — спросить AI\n"
        "• /test — проверить работу\n"
        "• /id — узнать свой ID",
        parse_mode="Markdown"
    )

async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❓ Напиши вопрос после /ask")
        return
    
    question = " ".join(context.args)
    await update.message.chat.send_action(action="typing")
    
    answer = await ask_groq(question)
    await update.message.reply_text(f"🤖 *Groq:*\n{answer}", parse_mode="Markdown")

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    test = await ask_groq("Ответь одним словом: ОК")
    await update.message.reply_text(f"✅ Бот работает!\n🤖 Тест: {test}")

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🆔 Твой ID: `{update.effective_user.id}`", parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.startswith('/'):
        return
    
    await update.message.chat.send_action(action="typing")
    answer = await ask_groq(update.message.text)
    await update.message.reply_text(f"🤖 *Groq:*\n{answer}", parse_mode="Markdown")

# ========== ЗАПУСК ==========
async def main():
    print("🚀 Запуск Groq бота...")
    print(f"🤖 Токен: {TOKEN[:10]}...")
    print(f"🔑 Groq: Подключен")
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ask", ask))
    app.add_handler(CommandHandler("test", test))
    app.add_handler(CommandHandler("id", id_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    await app.bot.delete_webhook(drop_pending_updates=True)
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    print("✅ Бот работает! Напиши /start")
    
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
