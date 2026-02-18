#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import asyncio
import time
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ТВОИ ДАННЫЕ
TOKEN = "8353336074:AAEg6F4BGcTRZXd7r0FN77uAMLZj7YPWGaE"
GEMINI_KEY = "AIzaSyCTcr54eVB2QRy3YII7sfI0bdEyKraQ5Wo"

# ========== УБИВАЕМ СТАРЫЕ ПРОЦЕССЫ ==========
os.system(f"pkill -f '{TOKEN[:20]}' || true")
os.system("pkill -f 'python.*bot' || true")
time.sleep(2)

# ========== GEMINI (ТОЧНАЯ РАБОЧАЯ МОДЕЛЬ) ==========
genai.configure(api_key=GEMINI_KEY)

# ЭТА МОДЕЛЬ ТОЧНО РАБОТАЕТ - БЕРИ!
model = genai.GenerativeModel('models/gemini-2.0-flash')

async def ask_gemini(question: str) -> str:
    try:
        response = model.generate_content(question)
        return response.text
    except Exception as e:
        return f"❌ Ошибка: {str(e)}"

# ========== КОМАНДЫ ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Gemini Test Bot*\n\n"
        "Привет! Я тестовый бот с Google Gemini AI.\n\n"
        "📝 *Команды:*\n"
        "• /ask [вопрос] — спросить AI\n"
        "• /test — проверить работу\n"
        "• /id — узнать свой ID",
        parse_mode="Markdown"
    )

async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❓ Напиши вопрос после /ask\nПример: `/ask как дела?`", parse_mode="Markdown")
        return
    
    question = " ".join(context.args)
    await update.message.chat.send_action(action="typing")
    
    answer = await ask_gemini(question)
    await update.message.reply_text(f"🤖 *Gemini:*\n{answer}", parse_mode="Markdown")

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Тест Gemini
    test_response = await ask_gemini("Ответь одним словом: ОК")
    await update.message.reply_text(f"✅ Бот работает!\n🤖 Gemini тест: {test_response}")

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🆔 Твой ID: `{update.effective_user.id}`", parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.startswith('/'):
        return
    
    await update.message.chat.send_action(action="typing")
    answer = await ask_gemini(update.message.text)
    await update.message.reply_text(f"🤖 *Gemini:*\n{answer}", parse_mode="Markdown")

# ========== ЗАПУСК ==========
async def main():
    print("🚀 Запуск Gemini бота...")
    print(f"🤖 Токен: {TOKEN[:10]}...")
    print(f"🔑 Gemini: Подключен")
    print(f"📊 Модель: {model.model_name}")
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ask", ask))
    app.add_handler(CommandHandler("test", test))
    app.add_handler(CommandHandler("id", id_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Удаляем вебхук
    await app.bot.delete_webhook(drop_pending_updates=True)
    
    print("✅ Бот запущен! Напиши /start в Telegram")
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
