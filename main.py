import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# ========== НОВЫЙ ТОКЕН (РАБОЧИЙ) ==========
TOKEN = "8326390250:AAG1nTYdy07AuKsYXS3yvDehfU2JuR0RqGo"

# ========== ПРОСТОЙ ОТВЕТЧИК ==========
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"✅ Бот работает с НОВЫМ токеном!\nТы написал: {update.message.text}")

# ========== ЗАПУСК ==========
async def main():
    print("🚀 Запуск с НОВЫМ токеном...")
    print(f"🔑 Токен: {TOKEN}")
    print("✅ Должно работать!")
    
    # Создаем приложение
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    
    # Удаляем вебхук
    await app.bot.delete_webhook(drop_pending_updates=True)
    
    print("✅ Бот запущен! Отправь ему любое сообщение.")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
    
