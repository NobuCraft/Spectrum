import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# ========== ТВОЙ НОВЫЙ ТОКЕН ==========
TOKEN = "8326390250:AAG1nTYdy07AuKsYXS3yvDehfU2JuR0RqGo"

# ========== ПРОСТОЙ ОТВЕТЧИК ==========
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"✅ Бот работает!\nТы написал: {update.message.text}")

# ========== ЗАПУСК ==========
async def main():
    print("🚀 Запуск...")
    
    # Создаем приложение
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    
    # Принудительно удаляем вебхук
    print("📡 Удаляем вебхук...")
    await app.bot.delete_webhook(drop_pending_updates=True)
    
    print("✅ Бот запущен! Отправь ему любое сообщение.")
    await app.run_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Бот остановлен")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
