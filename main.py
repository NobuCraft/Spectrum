import asyncio
import aiohttp
import random
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# ===================== ТВОЙ ТОКЕН =====================
TOKEN = "8326390250:AAEpXRnhLLLi5zUeFC39nfkHDlxR5ZFQ_yQ"

# ===================== ПРОСТОЙ AI КЛАСС =====================
class SimpleAI:
    def __init__(self):
        self.api_token = "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"
        print("✅ AI инициализирован")
    
    async def get_response(self, message: str) -> str:
        """Получить ответ от AI"""
        message_lower = message.lower().strip()
        
        # Простые локальные ответы
        if "привет" in message_lower:
            return random.choice(["Привет!", "Здравствуй!", "Хай!"])
        elif "как дела" in message_lower:
            return random.choice(["Хорошо! А у тебя?", "Отлично!", "Нормально"])
        elif "что делаешь" in message_lower:
            return random.choice(["Общаюсь с тобой", "Отвечаю на вопросы", "Думаю о жизни"])
        elif "пока" in message_lower:
            return random.choice(["До встречи!", "Пока!", "Удачи!"])
        elif "спасибо" in message_lower:
            return random.choice(["Пожалуйста!", "Не за что!", "Рад помочь!"])
        elif "кто ты" in message_lower:
            return "Я тестовый бот с AI!"
        else:
            return random.choice(["Интересно...", "Понятно", "Расскажи подробнее", "Давай поговорим"])

# ===================== СОЗДАЕМ AI =====================
ai = SimpleAI()

# ===================== ОБРАБОТЧИК СООБЩЕНИЙ =====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отвечает на любое сообщение"""
    user = update.effective_user
    message = update.message.text
    
    print(f"📨 Получено от {user.first_name}: {message}")
    
    # Показываем "печатает"
    await update.message.chat.send_action(action="typing")
    await asyncio.sleep(1)
    
    # Получаем ответ
    response = await ai.get_response(message)
    
    # Отправляем ответ
    await update.message.reply_text(f"🤖 **AI:** {response}")
    print(f"📤 Ответ: {response}")

# ===================== ЗАПУСК =====================
async def main():
    print("🚀 Запуск тестового бота...")
    
    # Создаем приложение
    app = Application.builder().token(TOKEN).build()
    
    # Добавляем обработчик на ВСЕ сообщения
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запускаем
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    print("✅ Бот запущен! Напиши ему любое сообщение!")
    
    # Держим бот активным
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
