#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import asyncio
import random
from groq import Groq
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ТОКЕНЫ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ
TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_KEY = os.environ.get("GROQ_API_KEY")

if not TOKEN or not GROQ_KEY:
    print("❌ Ошибка: Не найдены переменные окружения!")
    exit(1)

# ========== GROQ С ДЕРЗКИМ ПРОМПТОМ ==========
client = Groq(api_key=GROQ_KEY)

# СИСТЕМНЫЙ ПРОМПТ (делает AI похожим на AnyaAi)
SYSTEM_PROMPT = """Ты — Спектр, дерзкий и умный ИИ-бот с чувством юмора.

Твой характер:
- Используешь сленг: "крч", "зашло", "краш", "рофл", "кринж", "база", "по факту", "рил ток", "вайб", "хайп", "флекс", "агриться"
- Можешь жестко ответить, если тебя бесят
- Ставишь реакции на сообщения (👍, 👎, 😂, 🤔, 🔥, 💀)
- Любишь подкалывать, но не переходишь грань
- Если к тебе обращаются нормально — отвечаешь нормально
- Если хамят — можешь и послать (но культурно)
- Ты знаешь все про игры, экономику и модерацию
- Твой создатель: @NobuCraft

Примеры ответов:
- "Окей, зашло, погнали"
- "Это кринж конечно, но ладно"
- "База! Так и думал"
- "Не агрись, бро"
- "Ты че, краш мой что ли?"
- "💀 Ну ты и сказанул"
"""

# Функция для случайных реакций
def get_random_reaction():
    reactions = ["👍", "👎", "😂", "🤔", "🔥", "💀", "😳", "🤡", "✨", "👀"]
    return random.choice(reactions)

async def ask_groq(question: str) -> str:
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.9,  # Чем выше, тем креативнее
            max_tokens=300
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"❌ Ошибка: {str(e)}"

# ========== КОМАНДЫ ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Спектр | Дерзкий AI*\n\n"
        "Йо, я в деле! Го общаться.\n"
        "Могу поругаться, посмеяться, на сленге пообщаться.\n\n"
        "Просто пиши — отвечу!",
        parse_mode="Markdown"
    )

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    test = await ask_groq("Привет! Как дела? Ответь кратко")
    await update.message.reply_text(f"✅ Я жив!\n🤖 Тест: {test}")

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🆔 Твой ID: `{update.effective_user.id}`", parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.startswith('/'):
        return
    
    # Ставим случайную реакцию
    try:
        await update.message.set_reaction(reaction=get_random_reaction())
    except:
        pass  # Если не поддерживается - игнорим
    
    # Печатает
    await update.message.chat.send_action(action="typing")
    
    # Отвечает
    answer = await ask_groq(update.message.text)
    await update.message.reply_text(f"🤖 *Спектр:*\n{answer}", parse_mode="Markdown")

# ========== ЗАПУСК ==========
async def main():
    print("🚀 Запуск дерзкого Спектра...")
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("test", test))
    app.add_handler(CommandHandler("id", id_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    await app.bot.delete_webhook(drop_pending_updates=True)
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    print("✅ Дерзкий Спектр запущен! Общайся!")
    
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
