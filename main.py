import asyncio
import aiohttp
import random
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# ===================== ТОКЕНЫ =====================
TELEGRAM_TOKEN = "8326390250:AAEpXRnhLLLi5zUeFC39nfkHDlxR5ZFQ_yQ"
HF_TOKEN = "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"

# ===================== HUGGING FACE AI =====================
class HuggingFaceAI:
    def __init__(self):
        # Пробуем разные бесплатные модели
        self.models = [
            "microsoft/phi-2",  # Очень быстрая
            "google/flan-t5-large",  # Надёжная
            "EleutherAI/gpt-neo-125M",  # Лёгкая
            "distilgpt2",  # Самая маленькая
        ]
        self.current_model = 0
        self.headers = {"Authorization": f"Bearer {HF_TOKEN}"}
        print("🤖 Hugging Face AI инициализирован")
        print(f"📡 Используем модель: {self.models[self.current_model]}")
    
    async def get_response(self, message: str) -> str:
        # Пробуем каждую модель по очереди
        for attempt in range(len(self.models)):
            model = self.models[self.current_model]
            api_url = f"https://api-inference.huggingface.co/models/{model}"
            
            try:
                print(f"🔄 Пробуем модель: {model}")
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(api_url, headers=self.headers, json={
                        "inputs": message,
                        "parameters": {
                            "max_new_tokens": 50,
                            "temperature": 0.8,
                            "top_p": 0.95,
                        }
                    }, timeout=10) as resp:
                        
                        if resp.status == 200:
                            result = await resp.json()
                            if isinstance(result, list) and len(result) > 0:
                                if isinstance(result[0], dict) and 'generated_text' in result[0]:
                                    return result[0]['generated_text'].strip()
                                elif isinstance(result[0], str):
                                    return result[0].strip()
                            return "😊 Понял тебя!"
                        
                        elif resp.status == 503:
                            print(f"⏳ Модель {model} загружается...")
                            # Переключаем на следующую модель
                            self.current_model = (self.current_model + 1) % len(self.models)
                            await asyncio.sleep(1)
                            continue
                        else:
                            print(f"❌ Ошибка {resp.status} для модели {model}")
                            self.current_model = (self.current_model + 1) % len(self.models)
                            
            except Exception as e:
                print(f"❌ Ошибка с моделью {model}: {e}")
                self.current_model = (self.current_model + 1) % len(self.models)
                continue
        
        # Если все модели не сработали - используем локальные ответы
        return self._get_local_response(message)
    
    def _get_local_response(self, message: str) -> str:
        """Запасные ответы если API не работает"""
        message_lower = message.lower()
        
        responses = {
            "привет": ["Привет!", "Здравствуй!", "Хай!"],
            "как дела": ["Хорошо! А у тебя?", "Отлично!", "Нормально"],
            "что делаешь": ["Общаюсь с тобой", "Думаю о жизни", "Отвечаю на вопросы"],
            "пока": ["До встречи!", "Пока!", "Удачи!"],
            "спасибо": ["Пожалуйста!", "Не за что!", "Рад помочь!"],
            "кто ты": ["Я Спектр - твой AI помощник!", "Искусственный интеллект"],
        }
        
        for key, answers in responses.items():
            if key in message_lower:
                return random.choice(answers)
        
        return random.choice([
            "Интересно...",
            "Понятно",
            "Расскажи подробнее",
            "Давай поговорим",
            "Я тебя слушаю",
            "Хорошо, продолжай"
        ])

# ===================== СОЗДАЕМ AI =====================
ai = HuggingFaceAI()

# ===================== ОБРАБОТЧИК СООБЩЕНИЙ =====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.message.text
    
    print(f"📨 Получено от {user.first_name}: {message}")
    
    await update.message.chat.send_action(action="typing")
    response = await ai.get_response(message)
    await update.message.reply_text(f"🤖 **Спектр:** {response}")
    print(f"📤 Ответ: {response}")

# ===================== КОМАНДА СТАРТ =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 **Спектр AI запущен!**\n\n"
        "Просто напиши мне любое сообщение - я отвечу!"
    )

# ===================== ЗАПУСК =====================
async def main():
    print("🚀 Запуск тестового бота...")
    
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    print("✅ Бот запущен! Отправь ему любое сообщение!")
    print("📡 Пробуем разные модели Hugging Face...")
    
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
