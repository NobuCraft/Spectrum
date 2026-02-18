#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import asyncio
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ТВОИ ДАННЫЕ
TOKEN = "8353336074:AAEg6F4BGcTRZXd7r0FN77uAMLZj7YPWGaE"
GEMINI_KEY = "AIzaSyD3Brb2oAuFNWA7JBMrmd6WWrZ6JzK57HE"

# ========== ПРОСТАЯ ЗАЩИТА ==========
LOCK_FILE = "/tmp/bot.lock"
if os.path.exists(LOCK_FILE):
    print("❌ Бот уже запущен (найден lock файл)")
    sys.exit(1)
with open(LOCK_FILE, 'w') as f:
    f.write(str(os.getpid()))

# ========== GEMINI ==========
genai.configure(api_key=GEMINI_KEY)
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
        "🤖 *Gemini Bot*\n\nПривет! Я работаю!\n/ask [вопрос] — спросить",
        parse_mode="Markdown"
    )

async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Напиши вопрос после /ask")
        return
    
    question = " ".join(context.args)
    await update.message.chat.send_action(action="typing")
    answer = await ask_gemini(question)
    await update.message.reply_text(f"🤖 *Gemini:*\n{answer}", parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.startswith('/'):
        return
    await update.message.chat.send_action(action="typing")
    answer = await ask_gemini(update.message.text)
    await update.message.reply_text(f"🤖 *Gemini:*\n{answer}", parse_mode="Markdown")

# ========== ЗАПУСК ==========
async def main():
    print("🚀 Запуск...")
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ask", ask))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Простой запуск
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    print("✅ Бот работает!")
    
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
