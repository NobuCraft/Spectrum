import asyncio
import aiohttp
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# ===================== ТОКЕНЫ =====================
TELEGRAM_TOKEN = "8326390250:AAEpXRnhLLLi5zUeFC39nfkHDlxR5ZFQ_yQ"
HF_TOKEN = "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"  # Твой токен

# ===================== HUGGING FACE AI =====================
class HuggingFaceAI:
    def __init__(self):
        self.api_url = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.1"
        self.headers = {"Authorization": f"Bearer {HF_TOKEN}"}
        print("🤖 Hugging Face AI инициализирован")
    
    async def get_response(self, message: str) -> str:
        try:
            prompt = f"<s>[INST] Ты дружелюбный AI помощник. Ответь на сообщение кратко и с эмодзи: {message} [/INST]"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, headers=self.headers, json={
                    "inputs": prompt,
                    "parameters": {
                        "max_new_tokens": 100,
                        "temperature": 0.7,
                        "top_p": 0.95,
                    }
                }, timeout=30) as resp:
                    
                    if resp.status == 200:
                        result = await resp.json()
                        if isinstance(result, list) and len(result) > 0:
                            text = result[0].get("generated_text", "")
                            response = text.split("[/INST]")[-1] if "[/INST]" in text else text
                            return response.strip()
                    elif resp.status == 503:
                        return "⏳ Модель загружается, подожди немного..."
                    else:
                        return f"😊 Ошибка {resp.status}, но я всё равно тебя слышу!"
        except Exception as e:
            return f"🤗 Привет! Я тебя слышу! (Ошибка: {str(e)[:50]}...)"

# ===================== СОЗДАЕМ AI =====================
ai = HuggingFaceAI()

# ===================== ОБРАБОТЧИК СООБЩЕНИЙ =====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.message.text
    
    print(f"📨 Получено от {user.first_name}: {message}")
    
    # Показываем "печатает"
    await update.message.chat.send_action(action="typing")
    
    # Получаем ответ от Hugging Face
    response = await ai.get_response(message)
    
    # Отправляем ответ
    await update.message.reply_text(f"🤖 **Hugging Face:** {response}")
    print(f"📤 Ответ: {response}")

# ===================== ЗАПУСК =====================
async def main():
    print("🚀 Запуск тестового бота с Hugging Face...")
    
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    print("✅ Бот запущен! Отправь ему любое сообщение!")
    
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
