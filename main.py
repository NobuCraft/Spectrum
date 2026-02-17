import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Логирование
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен (поменяй на свой)
TOKEN = "8326390250:AAEpXRnhLLLi5zUeFC39nfkHDlxR5ZFQ_yQ"
PORT = int(os.environ.get('PORT', 8080))

# Простые команды
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Railway тест работает!\n/id - узнать свой ID")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📚 Команды:\n/start\n/help\n/id")

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(f"🆔 Твой ID: `{user_id}`", parse_mode="Markdown")

def main():
    """Запуск бота"""
    print("=" * 50)
    print("🚀 ЗАПУСК ТЕСТОВОГО БОТА")
    print("=" * 50)
    print(f"📊 Порт: {PORT}")
    print("=" * 50)
    
    # Создаем приложение
    app = Application.builder().token(TOKEN).build()
    
    # Добавляем команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("id", id_command))
    
    # Запускаем через webhook для Railway
    print("✅ Бот запускается...")
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=f"https://{os.environ.get('RAILWAY_STATIC_URL', '')}/{TOKEN}"
    )

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Ошибка: {e}")
