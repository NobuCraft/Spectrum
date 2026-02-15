import asyncio
import logging
import random
import sqlite3
import datetime
from collections import defaultdict
import time

# Для Telegram
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===================== КОНФИГУРАЦИЯ =====================
TELEGRAM_TOKEN = "8326390250:AAFuUVHZ6ucUtLy132Ep1pmteRr6tTk7u0Q"
OWNER_ID = 1732658530
OWNER_USERNAME = "@NobuCraft"

# Настройки
SPAM_LIMIT = 5
SPAM_WINDOW = 3
SPAM_MUTE_TIME = 120

# ===================== БАЗА ДАННЫХ =====================
class Database:
    def __init__(self, db_name="spectrum_bot.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                coins INTEGER DEFAULT 1000,
                level INTEGER DEFAULT 1,
                exp INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS bosses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                boss_name TEXT,
                boss_level INTEGER,
                boss_health INTEGER,
                boss_max_health INTEGER,
                boss_damage INTEGER,
                boss_reward INTEGER,
                is_alive INTEGER DEFAULT 1
            )
        ''')
        
        self.conn.commit()
        self.init_bosses()
    
    def init_bosses(self):
        self.cursor.execute("SELECT * FROM bosses")
        if not self.cursor.fetchone():
            bosses_data = [
                ("🌲 Лесной тролль", 5, 200, 20, 100),
                ("🐉 Огненный дракон", 10, 500, 40, 250),
                ("❄️ Ледяной великан", 15, 1000, 60, 500),
                ("⚔️ Темный рыцарь", 20, 2000, 80, 1000),
                ("👾 Король демонов", 25, 5000, 150, 2500),
                ("💀 Бог разрушения", 30, 10000, 300, 5000)
            ]
            for name, level, health, damage, reward in bosses_data:
                self.cursor.execute('''
                    INSERT INTO bosses (boss_name, boss_level, boss_health, boss_max_health, boss_damage, boss_reward)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (name, level, health, health, damage, reward))
            self.conn.commit()
    
    def get_user(self, user_id: int, first_name: str = "Player"):
        self.cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = self.cursor.fetchone()
        
        if not user:
            self.cursor.execute('''
                INSERT INTO users (user_id, first_name) VALUES (?, ?)
            ''', (user_id, first_name))
            self.conn.commit()
            return self.get_user(user_id, first_name)
        
        return {
            "user_id": user[0],
            "username": user[1],
            "first_name": user[2],
            "coins": user[3],
            "level": user[4],
            "exp": user[5]
        }
    
    def add_coins(self, user_id: int, coins: int):
        self.cursor.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (coins, user_id))
        self.conn.commit()
    
    def get_bosses(self, alive_only=True):
        if alive_only:
            self.cursor.execute("SELECT * FROM bosses WHERE is_alive = 1")
        else:
            self.cursor.execute("SELECT * FROM bosses")
        return self.cursor.fetchall()
    
    def get_boss(self, boss_id):
        self.cursor.execute("SELECT * FROM bosses WHERE id = ?", (boss_id,))
        return self.cursor.fetchone()
    
    def damage_boss(self, boss_id, damage):
        self.cursor.execute("UPDATE bosses SET boss_health = boss_health - ? WHERE id = ?", (damage, boss_id))
        self.conn.commit()
        
        self.cursor.execute("SELECT boss_health FROM bosses WHERE id = ?", (boss_id,))
        health = self.cursor.fetchone()[0]
        
        if health <= 0:
            self.cursor.execute("UPDATE bosses SET is_alive = 0 WHERE id = ?", (boss_id,))
            self.conn.commit()
            return True
        return False
    
    def respawn_bosses(self):
        self.cursor.execute("UPDATE bosses SET is_alive = 1, boss_health = boss_max_health")
        self.conn.commit()
    
    def close(self):
        self.conn.close()

# ===================== БАЗА ДАННЫХ =====================
db = Database()

# ===================== ПРОСТОЙ ИИ (ЗАГОТОВКИ) =====================
import google.generativeai as genai

class SimpleAI:
    def __init__(self):
        print("🔄 Инициализация Gemini...")
        try:
            # Твой API ключ
            self.api_key = "AIzaSyBG0pZQqm8JXhhmfosxh0G4ksddcDe6P5M"
            genai.configure(api_key=self.api_key)
            
            # Пробуем разные названия моделей
            models_to_try = [
                'gemini-1.5-pro',
                'gemini-1.0-pro',
                'gemini-pro',
                'models/gemini-1.5-pro'
            ]
            
            self.model = None
            for model_name in models_to_try:
                try:
                    print(f"🔄 Пробую модель: {model_name}")
                    self.model = genai.GenerativeModel(model_name)
                    # Пробный запрос
                    test = self.model.generate_content("test")
                    print(f"✅ Модель {model_name} работает!")
                    break
                except Exception as e:
                    print(f"❌ Модель {model_name} не подходит: {e}")
                    continue
            
            if self.model is None:
                raise Exception("Ни одна модель не работает")
            
            print("✅ Gemini готов к работе!")
            
        except Exception as e:
            print(f"❌ Ошибка инициализации Gemini: {e}")
            self.model = None
    
    async def get_response(self, message: str) -> str:
        if self.model is None:
            return await self.fallback_response(message)
        
        try:
            # Отправляем запрос в Gemini
            response = self.model.generate_content(
                f"Ты игровой бот «СПЕКТР». Отвечай кратко, дружелюбно, с эмодзи. Вот сообщение пользователя: {message}"
            )
            
            if response and response.text:
                print(f"✅ Gemini ответил: {response.text[:50]}...")
                return f"🤖 **СПЕКТР:** {response.text}"
            else:
                return await self.fallback_response(message)
                
        except Exception as e:
            print(f"❌ Ошибка Gemini: {e}")
            return await self.fallback_response(message)
    
    async def fallback_response(self, message: str) -> str:
        """Запасные ответы если Gemini не работает"""
        msg = message.lower().strip()
        
        if any(word in msg for word in ["привет", "здравствуй", "хай"]):
            return "👋 Привет! Как твои дела?"
        
        elif any(word in msg for word in ["как дела", "как ты"]):
            return "⚙️ Всё отлично! А у тебя?"
        
        elif any(word in msg for word in ["стих", "стихи"]):
            return "В мире «СПЕКТРА» живут игроки,\nСражаются с боссами, ловки и легки! ✨"
        
        elif any(word in msg for word in ["кто ты", "ты кто"]):
            return "🤖 Я — СПЕКТР, твой игровой помощник!"
        
        elif any(word in msg for word in ["что ты умеешь"]):
            return "📋 Мои команды: /bosses, /profile, /daily, /help"
        
        elif any(word in msg for word in ["босс", "битва"]):
            return "👾 Боссы ждут! /bosses"
        
        elif any(word in msg for word in ["профиль", "статистика"]):
            return "📊 Твой профиль: /profile"
        
        elif any(word in msg for word in ["награда", "бонус"]):
            return "🎁 Ежедневная награда: /daily"
        
        else:
            return random.choice([
                "🤖 Я внимательно слушаю. Можешь уточнить?",
                "🎯 Хочешь сразиться с боссом? /bosses",
                "📊 Хочешь узнать статистику? /profile",
                "🎁 Не забудь /daily!"
            ])
# ===================== ОСНОВНОЙ КЛАСС БОТА =====================
class GameBot:
    def __init__(self):
        print("🚀 GameBot инициализация начата...")
        
        self.db = db
        self.ai = SimpleAI()
        self.spam_tracker = defaultdict(list)
        
        print("📱 Создание приложения Telegram...")
        self.application = Application.builder().token(TELEGRAM_TOKEN).build()
        
        self.setup_handlers()
        print("✅ GameBot инициализация завершена")
    
    def setup_handlers(self):
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        self.application.add_handler(CommandHandler("profile", self.cmd_profile))
        self.application.add_handler(CommandHandler("bosses", self.cmd_bosses))
        self.application.add_handler(CommandHandler("boss_fight", self.cmd_boss_fight))
        self.application.add_handler(CommandHandler("daily", self.cmd_daily))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        logger.info("✅ Все обработчики зарегистрированы")
    
    async def check_spam(self, user_id: int) -> bool:
        current_time = time.time()
        self.spam_tracker[user_id] = [t for t in self.spam_tracker[user_id] if current_time - t < SPAM_WINDOW]
        self.spam_tracker[user_id].append(current_time)
        
        return len(self.spam_tracker[user_id]) > SPAM_LIMIT
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        self.db.get_user(user.id, user.first_name)
        
        text = (
            f"⚔️ **ДОБРО ПОЖАЛОВАТЬ В «СПЕКТР», {user.first_name}!** ⚔️\n\n"
            f"💰 Монеты: 1000 🪙\n\n"
            f"**КОМАНДЫ:**\n"
            f"👤 /profile - Твой профиль\n"
            f"👾 /bosses - Битвы с боссами\n"
            f"🎁 /daily - Ежедневная награда\n"
            f"📚 /help - Все команды\n\n"
            f"👑 Владелец: {OWNER_USERNAME}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "📚 **ВСЕ КОМАНДЫ БОТА**\n\n"
            "/start - Начать\n"
            "/profile - Твой профиль\n"
            "/bosses - Список боссов\n"
            "/boss_fight [ID] - Сразиться с боссом\n"
            "/daily - Ежедневная награда\n"
            "/help - Это меню"
        )
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id, user.first_name)
        
        text = (
            f"👤 **ПРОФИЛЬ**\n\n"
            f"Имя: {user_data['first_name']}\n"
            f"Уровень: {user_data['level']}\n"
            f"Опыт: {user_data['exp']}/{user_data['level'] * 100}\n"
            f"Монеты: {user_data['coins']} 🪙"
        )
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_bosses(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        bosses = self.db.get_bosses(alive_only=True)
        
        if not bosses:
            await update.message.reply_text("👾 Все боссы повержены! Ждите возрождения...")
            self.db.respawn_bosses()
            bosses = self.db.get_bosses(alive_only=True)
        
        text = "👾 **СПИСОК БОССОВ**\n\n"
        for boss in bosses:
            text += f"**{boss[1]}** (ур.{boss[2]})\n"
            text += f"ID: {boss[0]} | ❤️ {boss[3]}/{boss[4]} | 💰 {boss[6]}\n\n"
        
        text += "Сразиться: /boss_fight [ID]"
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_boss_fight(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id, user.first_name)
        
        if not context.args:
            await update.message.reply_text("❌ Укажи ID босса: /boss_fight 1")
            return
        
        try:
            boss_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ Неправильный ID")
            return
        
        boss = self.db.get_boss(boss_id)
        
        if not boss or not boss[7]:
            await update.message.reply_text("❌ Босс уже повержен")
            return
        
        player_damage = 10 + random.randint(-5, 5)
        boss_damage = boss[5] + random.randint(-5, 5)
        player_taken = max(1, boss_damage)
        
        boss_killed = self.db.damage_boss(boss_id, player_damage)
        
        text = f"⚔️ **БИТВА** ⚔️\n\n"
        text += f"Ты нанес {player_damage} урона!\n"
        text += f"Босс нанес тебе {player_taken} урона!\n\n"
        
        if boss_killed:
            reward = boss[6]
            self.db.add_coins(user.id, reward)
            text += f"🎉 **ПОБЕДА!**\n💰 Награда: {reward} монет"
        else:
            boss_info = self.db.get_boss(boss_id)
            text += f"👾 Босс еще жив! Осталось {boss_info[3]}❤️"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_daily(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id, user.first_name)
        
        coins = random.randint(50, 150)
        self.db.add_coins(user.id, coins)
        
        await update.message.reply_text(
            f"🎁 **ЕЖЕДНЕВНАЯ НАГРАДА**\n\n"
            f"💰 +{coins} монет",
            parse_mode='Markdown'
        )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        message_text = update.message.text
        
        if await self.check_spam(user.id):
            return
        
        response = await self.ai.get_response(message_text)
        await update.message.reply_text(response, parse_mode='Markdown')
    
    async def run(self):
        try:
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            logger.info("🚀 Бот «СПЕКТР» запущен!")
            while True:
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await asyncio.sleep(5)
            await self.run()
    
    async def close(self):
        self.db.close()
        logger.info("👋 Бот остановлен")

# ===================== ТОЧКА ВХОДА =====================
async def main():
    bot = GameBot()
    try:
        await bot.run()
    except KeyboardInterrupt:
        await bot.close()
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await bot.close()

if __name__ == "__main__":
    asyncio.run(main())
