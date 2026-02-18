#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import asyncio
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ТВОИ ДАННЫЕ (уже вставил)
TOKEN = "8353336074:AAEg6F4BGcTRZXd7r0FN77uAMLZj7YPWGaE"
GEMINI_KEY = "AIzaSyD3Brb2oAuFNWA7JBMrmd6WWrZ6JzK57HE"

# Настройка Gemini
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-pro')

# ========== ФУНКЦИЯ ДЛЯ GEMINI ==========
async def ask_gemini(question: str) -> str:
    """Спросить у Gemini"""
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
    await update.message.reply_text("✅ Бот работает!\n🤖 Gemini подключен")

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
    print(f"🔑 Gemini: {'Подключен' if GEMINI_KEY else 'Нет ключа'}")
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ask", ask))
    app.add_handler(CommandHandler("test", test))
    app.add_handler(CommandHandler("id", id_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ Бот запущен! Напиши /start в Telegram")
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
