import asyncio
import logging
import random
import sqlite3
import datetime
from typing import Optional, Dict, Any
import aiohttp
import json

# Для Telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# Для VK
from vkbottle.bot import Bot, Message
from vkbottle import Keyboard, KeyboardButtonColor, Text

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===================== КОНФИГУРАЦИЯ =====================
# Токены ботов (замените на свои)
TELEGRAM_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
VK_TOKEN = "YOUR_VK_GROUP_TOKEN"

# API для бесплатного ИИ (можно использовать несколько источников)
AI_API_URL = "https://api-free.example.com/v1/chat"  # Замените на реальный API
AI_API_KEY = "your_api_key"

# ===================== БАЗА ДАННЫХ =====================
class Database:
    def __init__(self, db_name="game_bot.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self):
        # Таблица пользователей
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                platform TEXT,
                username TEXT,
                level INTEGER DEFAULT 1,
                exp INTEGER DEFAULT 0,
                coins INTEGER DEFAULT 100,
                energy INTEGER DEFAULT 100,
                last_energy_update TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица браков
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS marriages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user1_id INTEGER,
                user2_id INTEGER,
                user1_platform TEXT,
                user2_platform TEXT,
                married_date TIMESTAMP,
                love_points INTEGER DEFAULT 0,
                gifts_count INTEGER DEFAULT 0,
                FOREIGN KEY (user1_id) REFERENCES users (user_id),
                FOREIGN KEY (user2_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица статистики
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS stats (
                user_id INTEGER,
                platform TEXT,
                messages_count INTEGER DEFAULT 0,
                commands_used INTEGER DEFAULT 0,
                games_played INTEGER DEFAULT 0,
                wins_count INTEGER DEFAULT 0,
                daily_streak INTEGER DEFAULT 0,
                last_daily TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица инвентаря
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                platform TEXT,
                item_name TEXT,
                item_type TEXT,
                quantity INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        self.conn.commit()
    
    def get_user(self, user_id: int, platform: str, username: str = "Player"):
        self.cursor.execute(
            "SELECT * FROM users WHERE user_id = ? AND platform = ?",
            (user_id, platform)
        )
        user = self.cursor.fetchone()
        
        if not user:
            self.cursor.execute(
                "INSERT INTO users (user_id, platform, username) VALUES (?, ?, ?)",
                (user_id, platform, username)
            )
            self.cursor.execute(
                "INSERT INTO stats (user_id, platform) VALUES (?, ?)",
                (user_id, platform)
            )
            self.conn.commit()
            return self.get_user(user_id, platform, username)
        
        return {
            "user_id": user[0],
            "platform": user[1],
            "username": user[2],
            "level": user[3],
            "exp": user[4],
            "coins": user[5],
            "energy": user[6]
        }
    
    def add_exp(self, user_id: int, platform: str, exp: int):
        self.cursor.execute(
            "UPDATE users SET exp = exp + ? WHERE user_id = ? AND platform = ?",
            (exp, user_id, platform)
        )
        
        # Проверка на повышение уровня
        self.cursor.execute(
            "SELECT exp, level FROM users WHERE user_id = ? AND platform = ?",
            (user_id, platform)
        )
        user = self.cursor.fetchone()
        
        exp_needed = user[1] * 100
        if user[0] >= exp_needed:
            self.cursor.execute(
                "UPDATE users SET level = level + 1, exp = exp - ? WHERE user_id = ? AND platform = ?",
                (exp_needed, user_id, platform)
            )
        
        self.conn.commit()
    
    def add_coins(self, user_id: int, platform: str, coins: int):
        self.cursor.execute(
            "UPDATE users SET coins = coins + ? WHERE user_id = ? AND platform = ?",
            (coins, user_id, platform)
        )
        self.conn.commit()
    
    def get_marriage(self, user_id: int, platform: str):
        self.cursor.execute('''
            SELECT * FROM marriages 
            WHERE (user1_id = ? AND user1_platform = ?) 
            OR (user2_id = ? AND user2_platform = ?)
        ''', (user_id, platform, user_id, platform))
        
        return self.cursor.fetchone()
    
    def create_marriage(self, user1_id: int, user2_id: int, platform1: str, platform2: str):
        self.cursor.execute('''
            INSERT INTO marriages (user1_id, user2_id, user1_platform, user2_platform, married_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (user1_id, user2_id, platform1, platform2, datetime.datetime.now()))
        self.conn.commit()
    
    def add_stat(self, user_id: int, platform: str, stat: str, value: int = 1):
        self.cursor.execute(
            f"UPDATE stats SET {stat} = {stat} + ? WHERE user_id = ? AND platform = ?",
            (value, user_id, platform)
        )
        self.conn.commit()
    
    def close(self):
        self.conn.close()

# ===================== ИИ МОДУЛЬ =====================
class AIAssistant:
    def __init__(self):
        self.session = None
        self.contexts = {}  # Хранение контекста для каждого пользователя
    
    async def get_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def get_response(self, user_id: int, message: str) -> str:
        """Получение ответа от ИИ"""
        try:
            session = await self.get_session()
            
            # Получаем или создаем контекст для пользователя
            if user_id not in self.contexts:
                self.contexts[user_id] = [
                    {"role": "system", "content": "Ты дружелюбный помощник в игровом боте. Отвечай кратко и с эмодзи."}
                ]
            
            # Добавляем сообщение пользователя в контекст
            self.contexts[user_id].append({"role": "user", "content": message})
            
            # Ограничиваем длину контекста
            if len(self.contexts[user_id]) > 10:
                self.contexts[user_id] = [self.contexts[user_id][0]] + self.contexts[user_id][-9:]
            
            # Отправляем запрос к API
            headers = {
                "Authorization": f"Bearer {AI_API_KEY}",
                "Content-Type": "application/json"
            }
            
            data = {
                "messages": self.contexts[user_id],
                "max_tokens": 150,
                "temperature": 0.8
            }
            
            # Здесь нужно использовать реальный API
            # Пример с бесплатным API (например, от DeepSeek или через proxy)
            async with session.post(AI_API_URL, json=data, headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    ai_response = result.get("choices", [{}])[0].get("message", {}).get("content", "😊")
                    
                    # Сохраняем ответ в контекст
                    self.contexts[user_id].append({"role": "assistant", "content": ai_response})
                    
                    return ai_response
                else:
                    return self.get_fallback_response()
        
        except Exception as e:
            logger.error(f"AI Error: {e}")
            return self.get_fallback_response()
    
    def get_fallback_response(self):
        """Запасные ответы если ИИ недоступен"""
        responses = [
            "😊 Я пока не могу ответить подробно, но я с тобой!",
            "✨ Спроси меня позже, сейчас я отдыхаю",
            "🌟 Давай лучше поиграем? Напиши /game",
            "💫 Извини, я немного занят. Попробуй /help"
        ]
        return random.choice(responses)
    
    async def close(self):
        if self.session:
            await self.session.close()

# ===================== ОСНОВНОЙ КЛАСС БОТА =====================
class GameBot:
    def __init__(self):
        self.db = Database()
        self.ai = AIAssistant()
        
        # Telegram бот
        self.telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
        self.setup_telegram_handlers()
        
        # VK бот
        self.vk_bot = Bot(token=VK_TOKEN)
        self.setup_vk_handlers()
    
    def setup_telegram_handlers(self):
        """Настройка обработчиков для Telegram"""
        # Команды
        self.telegram_app.add_handler(CommandHandler("start", self.tg_start))
        self.telegram_app.add_handler(CommandHandler("profile", self.tg_profile))
        self.telegram_app.add_handler(CommandHandler("marry", self.tg_marry))
        self.telegram_app.add_handler(CommandHandler("divorce", self.tg_divorce))
        self.telegram_app.add_handler(CommandHandler("game", self.tg_game))
        self.telegram_app.add_handler(CommandHandler("shop", self.tg_shop))
        self.telegram_app.add_handler(CommandHandler("daily", self.tg_daily))
        self.telegram_app.add_handler(CommandHandler("stats", self.tg_stats))
        self.telegram_app.add_handler(CommandHandler("help", self.tg_help))
        
        # Обработчики callback-кнопок
        self.telegram_app.add_handler(CallbackQueryHandler(self.tg_button_callback))
        
        # Обработчик обычных сообщений (для ИИ)
        self.telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.tg_handle_message))
    
    def setup_vk_handlers(self):
        """Настройка обработчиков для VK"""
        
        @self.vk_bot.on.message(text="/start")
        async def vk_start(message: Message):
            await self.vk_send_message(message, await self.get_start_message(message.from_id, "vk"))
        
        @self.vk_bot.on.message(text="/profile")
        async def vk_profile(message: Message):
            await self.vk_send_message(message, await self.get_profile(message.from_id, "vk"))
        
        @self.vk_bot.on.message(text="/marry")
        async def vk_marry(message: Message):
            await self.vk_send_message(message, await self.get_marry_info(message.from_id, "vk"))
        
        @self.vk_bot.on.message(text="/game")
        async def vk_game(message: Message):
            await self.vk_send_message(message, await self.get_game_menu())
        
        @self.vk_bot.on.message(text="/help")
        async def vk_help(message: Message):
            await self.vk_send_message(message, self.get_help_text())
        
        @self.vk_bot.on.message(text="/daily")
        async def vk_daily(message: Message):
            await self.vk_send_message(message, await self.get_daily_reward(message.from_id, "vk"))
        
        # Обработчик обычных сообщений для ИИ
        @self.vk_bot.on.message()
        async def vk_handle_message(message: Message):
            if not message.text.startswith('/'):
                response = await self.ai.get_response(message.from_id, message.text)
                await self.vk_send_message(message, response)
                
                # Начисляем опыт за сообщение
                self.db.add_exp(message.from_id, "vk", 5)
                self.db.add_stat(message.from_id, "vk", "messages_count")
    
    # ==================== МЕТОДЫ ДЛЯ TELEGRAM ====================
    
    async def tg_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        self.db.get_user(user.id, "telegram", user.username or user.first_name)
        
        await update.message.reply_text(
            f"🌟 Добро пожаловать в игровой бот, {user.first_name}!\n\n"
            f"У тебя есть 100 монет для начала. Исследуй мир, женись, играй в игры и общайся со мной!\n\n"
            f"Используй /help для списка команд"
        )
        
        self.db.add_stat(user.id, "telegram", "commands_used")
    
    async def tg_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id, "telegram", user.username or user.first_name)
        
        # Получаем статистику
        self.db.cursor.execute(
            "SELECT * FROM stats WHERE user_id = ? AND platform = ?",
            (user.id, "telegram")
        )
        stats = self.db.cursor.fetchone()
        
        # Проверяем брак
        marriage = self.db.get_marriage(user.id, "telegram")
        married_to = "Нет"
        if marriage:
            if marriage[1] == user.id and marriage[3] == "telegram":
                married_to = f"ID: {marriage[2]} ({marriage[4]})"
            else:
                married_to = f"ID: {marriage[1]} ({marriage[3]})"
        
        profile_text = (
            f"👤 **Профиль игрока**\n"
            f"Имя: {user_data['username']}\n"
            f"Уровень: {user_data['level']}\n"
            f"Опыт: {user_data['exp']}/{user_data['level'] * 100}\n"
            f"Монеты: {user_data['coins']} 🪙\n"
            f"Энергия: {user_data['energy']} ⚡\n\n"
            f"💍 **Семья**\n"
            f"Супруг(а): {married_to}\n\n"
            f"📊 **Статистика**\n"
            f"Сообщений: {stats[3] if stats else 0}\n"
            f"Команд: {stats[4] if stats else 0}\n"
            f"Игр сыграно: {stats[5] if stats else 0}\n"
            f"Побед: {stats[6] if stats else 0}\n"
            f"Дней подряд: {stats[7] if stats else 0}"
        )
        
        await update.message.reply_text(profile_text, parse_mode='Markdown')
        self.db.add_stat(user.id, "telegram", "commands_used")
    
    async def tg_marry(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        # Проверяем, не в браке ли уже
        marriage = self.db.get_marriage(user.id, "telegram")
        if marriage:
            await update.message.reply_text("❌ Ты уже в браке! Используй /divorce для развода")
            return
        
        if not context.args:
            await update.message.reply_text(
                "💍 Чтобы сделать предложение, укажи ID пользователя:\n"
                "/marry 123456789\n\n"
                "ID можно узнать в профиле через /profile"
            )
            return
        
        try:
            partner_id = int(context.args[0])
            
            # Проверяем существование партнера
            partner = self.db.get_user(partner_id, "telegram", "Партнер")
            
            # Создаем клавиатуру для подтверждения
            keyboard = [
                [
                    InlineKeyboardButton("✅ Согласиться", callback_data=f"marry_accept_{user.id}_{partner_id}"),
                    InlineKeyboardButton("❌ Отказаться", callback_data=f"marry_decline_{user.id}_{partner_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"💍 {user.first_name} предлагает тебе выйти замуж/жениться!\n"
                f"Согласен?",
                reply_markup=reply_markup
            )
            
        except ValueError:
            await update.message.reply_text("❌ Неправильный ID пользователя")
    
    async def tg_divorce(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        marriage = self.db.get_marriage(user.id, "telegram")
        if not marriage:
            await update.message.reply_text("❌ Ты не в браке")
            return
        
        # Удаляем брак
        self.db.cursor.execute(
            "DELETE FROM marriages WHERE id = ?",
            (marriage[0],)
        )
        self.db.conn.commit()
        
        await update.message.reply_text("💔 Брак расторгнут. Ты снова свободен!")
    
    async def tg_game(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [
                InlineKeyboardButton("🎲 Кости", callback_data="game_dice"),
                InlineKeyboardButton("🎰 Слоты", callback_data="game_slots")
            ],
            [
                InlineKeyboardButton("✊ Камень-ножницы-бумага", callback_data="game_rps"),
                InlineKeyboardButton("🎯 Угадай число", callback_data="game_number")
            ],
            [
                InlineKeyboardButton("💰 Дуэль (ставка)", callback_data="game_duel")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🎮 **Выбери игру:**\n\n"
            "🎲 Кости - угадай сумму\n"
            "🎰 Слоты - испытай удачу\n"
            "✊ Камень-ножницы-бумага - классика\n"
            "🎯 Угадай число - от 1 до 10\n"
            "💰 Дуэль - сразись с другим игроком",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        self.db.add_stat(user.id, "telegram", "commands_used")
    
    async def tg_shop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [
                InlineKeyboardButton("⚡ Энергия (50🪙)", callback_data="shop_energy"),
                InlineKeyboardButton("💝 Подарок (30🪙)", callback_data="shop_gift")
            ],
            [
                InlineKeyboardButton("🎫 Лотерейный билет (20🪙)", callback_data="shop_lottery"),
                InlineKeyboardButton("📦 Сундук (100🪙)", callback_data="shop_chest")
            ],
            [
                InlineKeyboardButton("🏠 Дом (500🪙)", callback_data="shop_house"),
                InlineKeyboardButton("👑 Премиум (1000🪙)", callback_data="shop_premium")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🏪 **Магазин**\n\n"
            "⚡ Энергия +50 - 50🪙\n"
            "💝 Подарок для любимого - 30🪙\n"
            "🎫 Лотерейный билет - 20🪙\n"
            "📦 Сундук с сокровищами - 100🪙\n"
            "🏠 Дом для семьи - 500🪙\n"
            "👑 Премиум статус - 1000🪙",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        self.db.add_stat(user.id, "telegram", "commands_used")
    
    async def tg_daily(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        result = await self.get_daily_reward(user.id, "telegram")
        await update.message.reply_text(result)
    
    async def tg_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Топ игроков
        self.db.cursor.execute(
            "SELECT username, level, coins FROM users WHERE platform = 'telegram' ORDER BY level DESC, coins DESC LIMIT 10"
        )
        top_players = self.db.cursor.fetchall()
        
        top_text = "🏆 **Топ игроков**\n\n"
        for i, player in enumerate(top_players, 1):
            top_text += f"{i}. {player[0]} - Ур.{player[1]} | {player[2]}🪙\n"
        
        # Статистика браков
        self.db.cursor.execute("SELECT COUNT(*) FROM marriages")
        marriages_count = self.db.cursor.fetchone()[0]
        
        top_text += f"\n💍 Всего браков: {marriages_count}"
        
        await update.message.reply_text(top_text, parse_mode='Markdown')
    
    async def tg_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(self.get_help_text())
    
    async def tg_handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        message_text = update.message.text
        
        # Получаем ответ от ИИ
        response = await self.ai.get_response(user.id, message_text)
        await update.message.reply_text(response)
        
        # Начисляем опыт за сообщение
        self.db.add_exp(user.id, "telegram", 5)
        self.db.add_stat(user.id, "telegram", "messages_count")
    
    async def tg_button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user = update.effective_user
        data = query.data
        
        if data.startswith("marry_accept"):
            parts = data.split('_')
            proposer_id = int(parts[2])
            acceptor_id = int(parts[3])
            
            if user.id != acceptor_id:
                await query.edit_message_text("❌ Это предложение не для тебя")
                return
            
            # Создаем брак
            self.db.create_marriage(proposer_id, acceptor_id, "telegram", "telegram")
            
            await query.edit_message_text(
                f"💖 Поздравляем! Брак заключен!\n"
                f"Теперь вы муж и жена. Любите друг друга!"
            )
        
        elif data.startswith("marry_decline"):
            await query.edit_message_text("💔 Предложение отклонено")
        
        elif data.startswith("game_"):
            game = data[5:]
            await self.play_game(query, user.id, "telegram", game)
        
        elif data.startswith("shop_"):
            item = data[5:]
            await self.buy_item(query, user.id, "telegram", item)
    
    # ==================== МЕТОДЫ ДЛЯ VK ====================
    
    async def vk_send_message(self, message: Message, text: str):
        await message.answer(text)
    
    # ==================== ОБЩИЕ МЕТОДЫ ====================
    
    async def get_start_message(self, user_id: int, platform: str) -> str:
        user = self.db.get_user(user_id, platform)
        
        return (
            f"🌟 Добро пожаловать в игровой бот!\n\n"
            f"У тебя есть {user['coins']} монет для начала. "
            f"Исследуй мир, женись, играй в игры и общайся со мной!\n\n"
            f"Используй /help для списка команд"
        )
    
    async def get_profile(self, user_id: int, platform: str) -> str:
        user_data = self.db.get_user(user_id, platform)
        
        self.db.cursor.execute(
            "SELECT * FROM stats WHERE user_id = ? AND platform = ?",
            (user_id, platform)
        )
        stats = self.db.cursor.fetchone()
        
        marriage = self.db.get_marriage(user_id, platform)
        married_to = "Нет"
        if marriage:
            if marriage[1] == user_id and marriage[3] == platform:
                married_to = f"ID: {marriage[2]} ({marriage[4]})"
            else:
                married_to = f"ID: {marriage[1]} ({marriage[3]})"
        
        return (
            f"👤 Профиль игрока\n"
            f"Имя: {user_data['username']}\n"
            f"Уровень: {user_data['level']}\n"
            f"Опыт: {user_data['exp']}/{user_data['level'] * 100}\n"
            f"Монеты: {user_data['coins']} 🪙\n"
            f"Энергия: {user_data['energy']} ⚡\n\n"
            f"💍 Семья\n"
            f"Супруг(а): {married_to}\n\n"
            f"📊 Статистика\n"
            f"Сообщений: {stats[3] if stats else 0}\n"
            f"Команд: {stats[4] if stats else 0}\n"
            f"Игр сыграно: {stats[5] if stats else 0}\n"
            f"Побед: {stats[6] if stats else 0}\n"
            f"Дней подряд: {stats[7] if stats else 0}"
        )
    
    async def get_marry_info(self, user_id: int, platform: str) -> str:
        marriage = self.db.get_marriage(user_id, platform)
        
        if marriage:
            return "💍 Ты в браке. Используй /divorce для развода"
        else:
            return "💔 Ты не в браке. Используй /marry [ID] чтобы сделать предложение"
    
    async def get_game_menu(self) -> str:
        return (
            "🎮 Доступные игры:\n\n"
            "/dice - Кости\n"
            "/slots - Слоты\n"
            "/rps - Камень-ножницы-бумага\n"
            "/guess - Угадай число\n"
            "/duel - Дуэль"
        )
    
    async def get_daily_reward(self, user_id: int, platform: str) -> str:
        # Проверяем, получал ли сегодня
        self.db.cursor.execute(
            "SELECT last_daily FROM stats WHERE user_id = ? AND platform = ?",
            (user_id, platform)
        )
        last = self.db.cursor.fetchone()
        
        today = datetime.datetime.now().date()
        
        if last and last[0]:
            last_date = datetime.datetime.fromisoformat(last[0]).date()
            if last_date == today:
                return "❌ Ты уже получал награду сегодня. Приходи завтра!"
        
        # Начисляем награду
        coins_reward = random.randint(50, 150)
        exp_reward = random.randint(10, 30)
        
        self.db.add_coins(user_id, platform, coins_reward)
        self.db.add_exp(user_id, platform, exp_reward)
        
        # Обновляем last_daily
        self.db.cursor.execute(
            "UPDATE stats SET last_daily = ?, daily_streak = daily_streak + 1 WHERE user_id = ? AND platform = ?",
            (datetime.datetime.now(), user_id, platform)
        )
        self.db.conn.commit()
        
        return (
            f"🎁 Ежедневная награда:\n"
            f"Монеты: +{coins_reward} 🪙\n"
            f"Опыт: +{exp_reward} ✨"
        )
    
    def get_help_text(self) -> str:
        return (
            "🤖 **Команды бота**\n\n"
            "**Основное:**\n"
            "/start - Начать\n"
            "/profile - Профиль\n"
            "/stats - Статистика и топ\n"
            "/daily - Ежедневная награда\n"
            "/help - Это меню\n\n"
            
            "**Игры:**\n"
            "/game - Меню игр\n"
            "/dice - Кости\n"
            "/slots - Слоты\n"
            "/rps - Камень-ножницы-бумага\n\n"
            
            "**Семья:**\n"
            "/marry [ID] - Сделать предложение\n"
            "/divorce - Развестись\n"
            "/gift [ID] - Подарить подарок\n\n"
            
            "**Магазин:**\n"
            "/shop - Магазин\n"
            "/inventory - Инвентарь\n\n"
            
            "**Общение:**\n"
            "Просто напиши мне сообщение - я отвечу!"
        )
    
    async def play_game(self, query, user_id: int, platform: str, game: str):
        user = self.db.get_user(user_id, platform)
        
        if game == "dice":
            bet = random.randint(1, 6) + random.randint(1, 6)
            result = random.randint(2, 12)
            
            if abs(result - bet) <= 2:
                win = 50
                self.db.add_coins(user_id, platform, win)
                text = f"🎲 Сумма: {result}\n🎉 Ты выиграл {win} монет!"
            else:
                text = f"🎲 Сумма: {result}\n😢 Повезет в следующий раз!"
        
        elif game == "slots":
            symbols = ["🍒", "🍋", "🍊", "7️⃣", "💎", "🎰"]
            spin = [random.choice(symbols) for _ in range(3)]
            
            if len(set(spin)) == 1:
                win = 100
                self.db.add_coins(user_id, platform, win)
                text = f"{' '.join(spin)}\n🎉 ДЖЕКПОТ! +{win} монет!"
            elif len(set(spin)) == 2:
                win = 20
                self.db.add_coins(user_id, platform, win)
                text = f"{' '.join(spin)}\n🎉 Выигрыш! +{win} монет!"
            else:
                text = f"{' '.join(spin)}\n😢 Попробуй еще!"
        
        elif game == "rps":
            choices = ["камень", "ножницы", "бумага"]
            bot_choice = random.choice(choices)
            
            # Здесь нужно получить выбор пользователя через отдельное меню
            # Для примера просто покажем меню
            keyboard = [
                [
                    InlineKeyboardButton("🪨 Камень", callback_data="rps_rock"),
                    InlineKeyboardButton("✂️ Ножницы", callback_data="rps_scissors"),
                    InlineKeyboardButton("📄 Бумага", callback_data="rps_paper")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "Выбери свой ход:",
                reply_markup=reply_markup
            )
            return
        
        else:
            text = "❓ Неизвестная игра"
        
        self.db.add_stat(user_id, platform, "games_played")
        await query.edit_message_text(text)
    
    async def buy_item(self, query, user_id: int, platform: str, item: str):
        user = self.db.get_user(user_id, platform)
        
        prices = {
            "energy": 50,
            "gift": 30,
            "lottery": 20,
            "chest": 100,
            "house": 500,
            "premium": 1000
        }
        
        price = prices.get(item, 0)
        
        if user['coins'] < price:
            await query.edit_message_text("❌ Недостаточно монет!")
            return
        
        # Списываем монеты
        self.db.add_coins(user_id, platform, -price)
        
        # Добавляем предмет в инвентарь
        if item == "energy":
            self.db.cursor.execute(
                "UPDATE users SET energy = energy + 50 WHERE user_id = ? AND platform = ?",
                (user_id, platform)
            )
            self.db.conn.commit()
            text = "⚡ Энергия +50! Теперь у тебя больше сил!"
        
        elif item == "gift":
            self.db.cursor.execute(
                "INSERT INTO inventory (user_id, platform, item_name, item_type) VALUES (?, ?, ?, ?)",
                (user_id, platform, "Подарок", "gift")
            )
            self.db.conn.commit()
            text = "💝 Подарок в инвентаре! Можешь подарить его любимому человеку командой /gift [ID]"
        
        elif item == "lottery":
            # Мгновенный розыгрыш
            win = random.choice([0, 0, 10, 20, 50, 100, 200])
            if win > 0:
                self.db.add_coins(user_id, platform, win)
                text = f"🎫 Ты выиграл {win} монет! Поздравляем!"
            else:
                text = "🎫 К сожалению, ничего не выиграл. Повезет в следующий раз!"
        
        else:
            self.db.cursor.execute(
                "INSERT INTO inventory (user_id, platform, item_name, item_type) VALUES (?, ?, ?, ?)",
                (user_id, platform, item.capitalize(), item)
            )
            self.db.conn.commit()
            text = f"✅ Ты купил {item.capitalize()}! Он в твоем инвентаре."
        
        await query.edit_message_text(text)
    
    # ==================== ЗАПУСК БОТОВ ====================
    
    async def run_telegram(self):
        """Запуск Telegram бота"""
        await self.telegram_app.initialize()
        await self.telegram_app.start()
        await self.telegram_app.updater.start_polling()
        logger.info("Telegram бот запущен")
        
        # Держим бот работающим
        while True:
            await asyncio.sleep(1)
    
    async def run_vk(self):
        """Запуск VK бота"""
        await self.vk_bot.run_polling()
        logger.info("VK бот запущен")
    
    async def run_all(self):
        """Запуск всех ботов одновременно"""
        await asyncio.gather(
            self.run_telegram(),
            self.run_vk()
        )
    
    async def close(self):
        """Закрытие всех соединений"""
        self.db.close()
        await self.ai.close()

# ===================== ЗАПУСК =====================
async def main():
    bot = GameBot()
    
    try:
        await bot.run_all()
    except KeyboardInterrupt:
        logger.info("Остановка ботов...")
        await bot.close()
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await bot.close()

if __name__ == "__main__":
    asyncio.run(main())
