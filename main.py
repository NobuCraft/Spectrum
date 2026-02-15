import asyncio
import logging
import random
import sqlite3
import datetime
from typing import Optional, Dict, Any, List
import aiohttp
import json
import os
import re
from collections import defaultdict
import time

# Для Telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from telegram.error import TelegramError, NetworkError

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

# OpenRouter API
OPENROUTER_KEY = "sk-97ac1d0de1844c449852a5470cbcae35"

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
        self.migrate_tables()
        self.init_data()
    
    def migrate_tables(self):
        try:
            self.cursor.execute("PRAGMA table_info(users)")
            columns = [col[1] for col in self.cursor.fetchall()]
            
            if 'role' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
            if 'warns' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN warns INTEGER DEFAULT 0")
            if 'mute_until' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN mute_until TIMESTAMP")
            if 'banned' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN banned INTEGER DEFAULT 0")
            if 'boss_kills' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN boss_kills INTEGER DEFAULT 0")
            if 'mafia_wins' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN mafia_wins INTEGER DEFAULT 0")
            if 'mafia_games' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN mafia_games INTEGER DEFAULT 0")
            if 'rps_wins' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN rps_wins INTEGER DEFAULT 0")
            if 'rps_losses' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN rps_losses INTEGER DEFAULT 0")
            if 'rps_draws' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN rps_draws INTEGER DEFAULT 0")
            if 'casino_wins' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN casino_wins INTEGER DEFAULT 0")
            if 'casino_losses' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN casino_losses INTEGER DEFAULT 0")
            if 'rr_wins' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN rr_wins INTEGER DEFAULT 0")
            if 'rr_losses' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN rr_losses INTEGER DEFAULT 0")
            self.conn.commit()
        except Exception as e:
            print(f"Ошибка миграции: {e}")
    
    def create_tables(self):
        # Пользователи
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                coins INTEGER DEFAULT 1000,
                energy INTEGER DEFAULT 100,
                level INTEGER DEFAULT 1,
                exp INTEGER DEFAULT 0,
                role TEXT DEFAULT 'user',
                warns INTEGER DEFAULT 0,
                mute_until TIMESTAMP,
                banned INTEGER DEFAULT 0,
                health INTEGER DEFAULT 100,
                armor INTEGER DEFAULT 0,
                damage INTEGER DEFAULT 10,
                boss_kills INTEGER DEFAULT 0,
                mafia_wins INTEGER DEFAULT 0,
                mafia_games INTEGER DEFAULT 0,
                rps_wins INTEGER DEFAULT 0,
                rps_losses INTEGER DEFAULT 0,
                rps_draws INTEGER DEFAULT 0,
                casino_wins INTEGER DEFAULT 0,
                casino_losses INTEGER DEFAULT 0,
                rr_wins INTEGER DEFAULT 0,
                rr_losses INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Статистика
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS stats (
                user_id INTEGER PRIMARY KEY,
                messages_count INTEGER DEFAULT 0,
                commands_used INTEGER DEFAULT 0,
                games_played INTEGER DEFAULT 0,
                daily_streak INTEGER DEFAULT 0,
                last_daily TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Боссы
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS bosses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                boss_name TEXT,
                boss_level INTEGER,
                boss_health INTEGER,
                boss_max_health INTEGER,
                boss_damage INTEGER,
                boss_reward INTEGER,
                is_alive INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Настройки групп
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS group_settings (
                chat_id INTEGER PRIMARY KEY,
                welcome_enabled INTEGER DEFAULT 1,
                welcome_message TEXT DEFAULT '🌟 Добро пожаловать, {user}!',
                goodbye_enabled INTEGER DEFAULT 1,
                goodbye_message TEXT DEFAULT '👋 Пока, {user}!',
                anti_spam INTEGER DEFAULT 1,
                anti_flood INTEGER DEFAULT 1,
                caps_limit INTEGER DEFAULT 10,
                emoji_limit INTEGER DEFAULT 10,
                link_block INTEGER DEFAULT 0,
                language TEXT DEFAULT 'ru',
                rules TEXT DEFAULT '',
                mute_time INTEGER DEFAULT 5,
                warn_limit INTEGER DEFAULT 3
            )
        ''')
        
        # Правила групп
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS group_rules (
                chat_id INTEGER PRIMARY KEY,
                rules_text TEXT DEFAULT '',
                last_updated TIMESTAMP,
                updated_by INTEGER
            )
        ''')
        
        self.conn.commit()
    
    def init_data(self):
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
    
    def respawn_bosses(self):
        self.cursor.execute("UPDATE bosses SET is_alive = 1, boss_health = boss_max_health")
        self.conn.commit()
    
    def get_user(self, user_id: int, first_name: str = "Player", last_name: str = ""):
        self.cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = self.cursor.fetchone()
        
        if not user:
            role = 'owner' if user_id == OWNER_ID else 'user'
            self.cursor.execute('''
                INSERT INTO users (user_id, first_name, last_name, role) 
                VALUES (?, ?, ?, ?)
            ''', (user_id, first_name, last_name, role))
            
            self.cursor.execute('''
                INSERT INTO stats (user_id) VALUES (?)
            ''', (user_id,))
            
            self.conn.commit()
            return self.get_user(user_id, first_name, last_name)
        
        columns = [description[0] for description in self.cursor.description]
        return dict(zip(columns, user))
    
    def add_coins(self, user_id: int, coins: int):
        self.cursor.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (coins, user_id))
        self.conn.commit()
    
    def add_energy(self, user_id: int, energy: int):
        self.cursor.execute("UPDATE users SET energy = energy + ? WHERE user_id = ?", (energy, user_id))
        self.conn.commit()
    
    def add_stat(self, user_id: int, stat: str, value: int = 1):
        self.cursor.execute(f"UPDATE stats SET {stat} = {stat} + ? WHERE user_id = ?", (value, user_id))
        self.conn.commit()
    
    def mute_user(self, user_id: int, minutes: int, admin_id: int = None, reason: str = "Спам"):
        mute_until = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
        self.cursor.execute("UPDATE users SET mute_until = ? WHERE user_id = ?", (mute_until, user_id))
        self.conn.commit()
        return mute_until
    
    def is_muted(self, user_id: int) -> bool:
        self.cursor.execute("SELECT mute_until FROM users WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()
        if result and result[0]:
            mute_until = datetime.datetime.fromisoformat(result[0])
            return datetime.datetime.now() < mute_until
        return False
    
    def get_mute_time(self, user_id: int) -> str:
        self.cursor.execute("SELECT mute_until FROM users WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()
        if result and result[0]:
            mute_until = datetime.datetime.fromisoformat(result[0])
            if datetime.datetime.now() < mute_until:
                remaining = mute_until - datetime.datetime.now()
                minutes = remaining.seconds // 60
                seconds = remaining.seconds % 60
                return f"{minutes} мин {seconds} сек"
        return "0"
    
    def add_warn(self, user_id: int, admin_id: int, reason: str = "Нарушение"):
        self.cursor.execute("UPDATE users SET warns = warns + 1 WHERE user_id = ?", (user_id,))
        self.conn.commit()
        
        self.cursor.execute("SELECT warns FROM users WHERE user_id = ?", (user_id,))
        warns = self.cursor.fetchone()[0]
        
        if warns >= 3:
            self.mute_user(user_id, 1440, admin_id, "3 предупреждения")
            return f"⚠️ Пользователь получил 3 варна и был замучен на 24 часа!"
        return f"⚠️ Пользователь получил варн ({warns}/3)"
    
    def ban_user(self, user_id: int, admin_id: int):
        self.cursor.execute("UPDATE users SET banned = 1 WHERE user_id = ?", (user_id,))
        self.conn.commit()
    
    def unban_user(self, user_id: int):
        self.cursor.execute("UPDATE users SET banned = 0, warns = 0 WHERE user_id = ?", (user_id,))
        self.conn.commit()
    
    def is_banned(self, user_id: int) -> bool:
        self.cursor.execute("SELECT banned FROM users WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()
        return result and result[0] == 1
    
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
    
    def add_boss_kill(self, user_id):
        self.cursor.execute("UPDATE users SET boss_kills = boss_kills + 1 WHERE user_id = ?", (user_id,))
        self.conn.commit()
    
    def get_group_settings(self, chat_id):
        self.cursor.execute("SELECT * FROM group_settings WHERE chat_id = ?", (chat_id,))
        settings = self.cursor.fetchone()
        
        if not settings:
            self.cursor.execute("INSERT INTO group_settings (chat_id) VALUES (?)", (chat_id,))
            self.conn.commit()
            return self.get_group_settings(chat_id)
        
        columns = [description[0] for description in self.cursor.description]
        return dict(zip(columns, settings))
    
    def update_group_setting(self, chat_id, setting, value):
        self.cursor.execute(f"UPDATE group_settings SET {setting} = ? WHERE chat_id = ?", (value, chat_id))
        self.conn.commit()
    
    def get_group_rules(self, chat_id):
        self.cursor.execute("SELECT rules_text FROM group_rules WHERE chat_id = ?", (chat_id,))
        result = self.cursor.fetchone()
        return result[0] if result else ""
    
    def set_group_rules(self, chat_id, rules, admin_id):
        self.cursor.execute('''
            INSERT OR REPLACE INTO group_rules (chat_id, rules_text, last_updated, updated_by)
            VALUES (?, ?, ?, ?)
        ''', (chat_id, rules, datetime.datetime.now(), admin_id))
        self.conn.commit()
    
    def close(self):
        self.conn.close()

# ===================== БАЗА ДАННЫХ =====================
db = Database()

# ===================== OPENROUTER AI =====================
class OpenRouterAI:
    def __init__(self):
        self.api_key = OPENROUTER_KEY
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.session = None
        print("🤖 OpenRouter AI инициализирован")
    
    async def get_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def get_response(self, message: str) -> str:
        try:
            session = await self.get_session()
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://railway.app",
                "X-Title": "Spectrum Bot"
            }
            
            models = [
                "deepseek/deepseek-chat",
                "mistralai/mistral-7b-instruct",
                "openai/gpt-3.5-turbo"
            ]
            
            for model in models:
                try:
                    data = {
                        "model": model,
                        "messages": [
                            {"role": "system", "content": "Ты игровой бот «СПЕКТР». Отвечай кратко, дружелюбно, с эмодзи. Ты помогаешь с играми и просто общаешься."},
                            {"role": "user", "content": message}
                        ],
                        "temperature": 0.7,
                        "max_tokens": 150
                    }
                    
                    async with session.post(self.api_url, json=data, headers=headers, timeout=10) as resp:
                        if resp.status == 200:
                            result = await resp.json()
                            return result["choices"][0]["message"]["content"]
                        else:
                            print(f"❌ Модель {model} ошибка: {resp.status}")
                            continue
                except Exception as e:
                    print(f"❌ Модель {model} исключение: {e}")
                    continue
            
            return None
            
        except Exception as e:
            print(f"❌ OpenRouter ошибка: {e}")
            return None
    
    async def close(self):
        if self.session:
            await self.session.close()

# ===================== ОСНОВНОЙ КЛАСС БОТА =====================
class GameBot:
    def __init__(self):
        self.db = db
        self.ai = OpenRouterAI()
        self.spam_tracker = defaultdict(list)
        self.application = Application.builder().token(TELEGRAM_TOKEN).build()
        self.setup_handlers()
        logger.info("✅ Бот «СПЕКТР» инициализирован")
    
    def setup_handlers(self):
        # Основные
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        self.application.add_handler(CommandHandler("menu", self.cmd_menu))
        
        # Профиль и статистика
        self.application.add_handler(CommandHandler("profile", self.cmd_profile))
        self.application.add_handler(CommandHandler("boss_stats", self.cmd_boss_stats))
        self.application.add_handler(CommandHandler("mafia_stats", self.cmd_mafia_stats))
        self.application.add_handler(CommandHandler("rps_stats", self.cmd_rps_stats))
        self.application.add_handler(CommandHandler("casino_stats", self.cmd_casino_stats))
        self.application.add_handler(CommandHandler("rr_stats", self.cmd_rr_stats))
        self.application.add_handler(CommandHandler("top", self.cmd_top))
        self.application.add_handler(CommandHandler("daily", self.cmd_daily))
        
        # Боссы
        self.application.add_handler(CommandHandler("bosses", self.cmd_boss_list))
        self.application.add_handler(CommandHandler("boss_fight", self.cmd_boss_fight))
        
        # Казино
        self.application.add_handler(CommandHandler("casino", self.cmd_casino))
        self.application.add_handler(CommandHandler("roulette", self.cmd_roulette))
        self.application.add_handler(CommandHandler("dice", self.cmd_dice))
        
        # Камень-ножницы-бумага
        self.application.add_handler(CommandHandler("rps", self.cmd_rps))
        
        # Русская рулетка
        self.application.add_handler(CommandHandler("rr", self.cmd_rr))
        self.application.add_handler(CommandHandler("rr_start", self.cmd_rr_start))
        self.application.add_handler(CommandHandler("rr_shot", self.cmd_rr_shot))
        
        # Админские
        self.application.add_handler(CommandHandler("mute", self.cmd_mute))
        self.application.add_handler(CommandHandler("warn", self.cmd_warn))
        self.application.add_handler(CommandHandler("ban", self.cmd_ban))
        self.application.add_handler(CommandHandler("unban", self.cmd_unban))
        
        # Настройки групп
        self.application.add_handler(CommandHandler("rules", self.cmd_rules))
        self.application.add_handler(CommandHandler("set_rules", self.cmd_set_rules))
        self.application.add_handler(CommandHandler("group_settings", self.cmd_group_settings))
        self.application.add_handler(CommandHandler("set_welcome", self.cmd_set_welcome))
        self.application.add_handler(CommandHandler("set_goodbye", self.cmd_set_goodbye))
        
        # Обработчики
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, self.handle_new_members))
        self.application.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, self.handle_left_member))
        
        logger.info("✅ Все обработчики зарегистрированы")
    
    def is_admin(self, user_id: int) -> bool:
        user = self.db.get_user(user_id)
        return user.get('role', 'user') in ['owner', 'admin']
    
    def is_owner(self, user_id: int) -> bool:
        return user_id == OWNER_ID
    
    def get_role_emoji(self, role):
        emojis = {'owner': '👑', 'admin': '⚜️', 'user': '👤'}
        return emojis.get(role, '👤')
    
    def calc_winrate(self, wins, games):
        if games == 0:
            return 0
        return round((wins / games) * 100, 1)
    
    async def check_spam(self, update: Update) -> bool:
        user_id = update.effective_user.id
        if self.is_admin(user_id) or self.is_owner(user_id):
            return False
        
        current_time = time.time()
        self.spam_tracker[user_id] = [t for t in self.spam_tracker[user_id] if current_time - t < SPAM_WINDOW]
        self.spam_tracker[user_id].append(current_time)
        
        if len(self.spam_tracker[user_id]) > SPAM_LIMIT:
            self.db.mute_user(user_id, SPAM_MUTE_TIME, 0, "Автоматический спам")
            await update.message.reply_text(f"🚫 **СПАМ-ФИЛЬТР**\n\nВы замучены на {SPAM_MUTE_TIME} минут.", parse_mode='Markdown')
            self.spam_tracker[user_id] = []
            return True
        return False
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        self.db.get_user(user.id, user.first_name, user.last_name or "")
        
        text = (
            f"╔══════════════════════════════╗\n"
            f"║  ⚔️ **ДОБРО ПОЖАЛОВАТЬ** ⚔️  ║\n"
            f"╚══════════════════════════════╝\n\n"
            f"🌟 **Привет, {user.first_name}!**\n\n"
            f"Я — **«СПЕКТР»**, твой игровой бот с искусственным интеллектом!\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 **ГЛАВНОЕ МЕНЮ**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 **ПРОФИЛЬ**\n"
            f"└ /profile — твой профиль\n"
            f"└ /top — топ игроков\n"
            f"└ /daily — ежедневная награда\n\n"
            f"📊 **СТАТИСТИКА**\n"
            f"└ /boss_stats — битвы с боссами\n"
            f"└ /rps_stats — КНБ\n"
            f"└ /casino_stats — казино\n\n"
            f"🎮 **ИГРЫ**\n"
            f"└ /bosses — список боссов\n"
            f"└ /casino — казино\n"
            f"└ /rps — камень-ножницы-бумага\n\n"
            f"👑 **ВЛАДЕЛЕЦ:** {OWNER_USERNAME}\n\n"
            f"💡 Напиши /menu для полного меню"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
        self.db.add_stat(user.id, "commands_used")
    
    async def cmd_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("👤 Профиль", callback_data="menu_profile"),
             InlineKeyboardButton("📊 Статистика", callback_data="menu_stats")],
            [InlineKeyboardButton("👾 Боссы", callback_data="menu_bosses"),
             InlineKeyboardButton("🎰 Казино", callback_data="menu_casino")],
            [InlineKeyboardButton("✊ КНБ", callback_data="menu_rps"),
             InlineKeyboardButton("💣 Русская рулетка", callback_data="menu_rr")],
            [InlineKeyboardButton("👥 Группы", callback_data="menu_groups"),
             InlineKeyboardButton("📚 Помощь", callback_data="menu_help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🎮 **ГЛАВНОЕ МЕНЮ**\n\nВыбери раздел:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        text = (
            "╔══════════════════════════════╗\n"
            "║   📚 **ВСЕ КОМАНДЫ БОТА**   ║\n"
            "╚══════════════════════════════╝\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "👤 **ПРОФИЛЬ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ /profile — твой профиль\n"
            "▫️ /boss_stats — статистика боссов\n"
            "▫️ /mafia_stats — статистика мафии\n"
            "▫️ /rps_stats — статистика КНБ\n"
            "▫️ /casino_stats — статистика казино\n"
            "▫️ /rr_stats — статистика русской рулетки\n"
            "▫️ /top — топ игроков\n"
            "▫️ /daily — ежедневная награда\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "👾 **БОССЫ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ /bosses — список боссов\n"
            "▫️ /boss_fight [ID] — сразиться с боссом\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🎰 **КАЗИНО**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ /casino — меню казино\n"
            "▫️ /roulette [ставка] [цвет] — рулетка\n"
            "▫️ /dice [ставка] — кости\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "✊ **КНБ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ /rps — камень-ножницы-бумага\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "💣 **РУССКАЯ РУЛЕТКА**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ /rr — инфо\n"
            "▫️ /rr_start [игроки] [ставка] — создать лобби\n"
            "▫️ /rr_shot — сделать выстрел\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "👥 **ГРУППЫ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ /rules — правила чата\n"
            "▫️ /set_rules [текст] — установить правила\n"
            "▫️ /group_settings — настройки группы\n"
            "▫️ /set_welcome [текст] — приветствие\n"
            "▫️ /set_goodbye [текст] — прощание\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "👑 **АДМИН**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ /mute [ID] [минут] — замутить\n"
            "▫️ /warn [ID] — варн\n"
            "▫️ /ban [ID] — забанить\n"
            "▫️ /unban [ID] — разбанить\n\n"
            
            f"👑 **Владелец:** {OWNER_USERNAME}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
        self.db.add_stat(user.id, "commands_used")
    
    async def cmd_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id, user.first_name, user.last_name or "")
        
        if self.db.is_muted(user.id):
            remaining = self.db.get_mute_time(user.id)
            await update.message.reply_text(f"🔇 Вы замучены. Осталось: {remaining}")
            return
        
        self.db.cursor.execute("SELECT * FROM stats WHERE user_id = ?", (user.id,))
        stats = self.db.cursor.fetchone()
        
        text = (
            f"╔══════════════════════════════╗\n"
            f"║    👤 **ПРОФИЛЬ ИГРОКА**    ║\n"
            f"╚══════════════════════════════╝\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**ОСНОВНОЕ**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"▫️ **Имя:** {user_data.get('first_name', user.first_name)}\n"
            f"▫️ **Роль:** {self.get_role_emoji(user_data.get('role', 'user'))} {user_data.get('role', 'user')}\n"
            f"▫️ **Уровень:** {user_data.get('level', 1)}\n"
            f"▫️ **Опыт:** {user_data.get('exp', 0)}/{user_data.get('level', 1) * 100}\n"
            f"▫️ **Монеты:** {user_data.get('coins', 1000)} 🪙\n"
            f"▫️ **Энергия:** {user_data.get('energy', 100)} ⚡\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**БОЕВЫЕ ХАРАКТЕРИСТИКИ**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"▫️ **Здоровье:** {user_data.get('health', 100)} ❤️\n"
            f"▫️ **Броня:** {user_data.get('armor', 0)} 🛡\n"
            f"▫️ **Урон:** {user_data.get('damage', 10)} ⚔️\n"
            f"▫️ **Боссов убито:** {user_data.get('boss_kills', 0)} 👾\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**СТАТИСТИКА**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"▫️ **Сообщений:** {stats[1] if stats else 0}\n"
            f"▫️ **Команд:** {stats[2] if stats else 0}\n"
            f"▫️ **Игр сыграно:** {stats[3] if stats else 0}\n"
            f"▫️ **Дней подряд:** {stats[4] if stats else 0}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
        self.db.add_stat(user.id, "commands_used")
    
    async def cmd_boss_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        text = (
            f"╔══════════════════════════════╗\n"
            f"║   👾 **СТАТИСТИКА БОССОВ**  ║\n"
            f"╚══════════════════════════════╝\n\n"
            f"▫️ **Игрок:** {user.first_name}\n"
            f"▫️ **Боссов убито:** {user_data.get('boss_kills', 0)} 💀\n"
            f"▫️ **Урон:** {user_data.get('damage', 10)} ⚔️\n"
            f"▫️ **Броня:** {user_data.get('armor', 0)} 🛡\n"
            f"▫️ **Здоровье:** {user_data.get('health', 100)} ❤️"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_mafia_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        wins = user_data.get('mafia_wins', 0)
        games = user_data.get('mafia_games', 0)
        
        text = (
            f"╔══════════════════════════════╗\n"
            f"║   🔪 **СТАТИСТИКА МАФИИ**   ║\n"
            f"╚══════════════════════════════╝\n\n"
            f"▫️ **Игрок:** {user.first_name}\n"
            f"▫️ **Побед:** {wins} 🏆\n"
            f"▫️ **Игр:** {games} 🎮\n"
            f"▫️ **Винрейт:** {self.calc_winrate(wins, games)}% 📊"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_rps_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        wins = user_data.get('rps_wins', 0)
        losses = user_data.get('rps_losses', 0)
        draws = user_data.get('rps_draws', 0)
        total = wins + losses + draws
        
        text = (
            f"╔══════════════════════════════╗\n"
            f"║   ✊ **СТАТИСТИКА КНБ**     ║\n"
            f"╚══════════════════════════════╝\n\n"
            f"▫️ **Игрок:** {user.first_name}\n"
            f"▫️ **Побед:** {wins} 🏆\n"
            f"▫️ **Поражений:** {losses} 💔\n"
            f"▫️ **Ничьих:** {draws} 🤝\n"
            f"▫️ **Всего игр:** {total} 🎮\n"
            f"▫️ **Винрейт:** {self.calc_winrate(wins, total)}% 📊"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_casino_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        wins = user_data.get('casino_wins', 0)
        losses = user_data.get('casino_losses', 0)
        total = wins + losses
        
        text = (
            f"╔══════════════════════════════╗\n"
            f"║   🎰 **СТАТИСТИКА КАЗИНО**  ║\n"
            f"╚══════════════════════════════╝\n\n"
            f"▫️ **Игрок:** {user.first_name}\n"
            f"▫️ **Побед:** {wins} 🏆\n"
            f"▫️ **Поражений:** {losses} 💔\n"
            f"▫️ **Всего игр:** {total} 🎮\n"
            f"▫️ **Винрейт:** {self.calc_winrate(wins, total)}% 📊"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_rr_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        wins = user_data.get('rr_wins', 0)
        losses = user_data.get('rr_losses', 0)
        total = wins + losses
        
        text = (
            f"╔══════════════════════════════╗\n"
            f"║  💣 **СТАТИСТИКА РУЛЕТКИ**  ║\n"
            f"╚══════════════════════════════╝\n\n"
            f"▫️ **Игрок:** {user.first_name}\n"
            f"▫️ **Побед:** {wins} 🏆\n"
            f"▫️ **Поражений:** {losses} 💔\n"
            f"▫️ **Всего игр:** {total} 🎮\n"
            f"▫️ **Винрейт:** {self.calc_winrate(wins, total)}% 📊"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_top(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.db.cursor.execute("SELECT first_name, coins FROM users ORDER BY coins DESC LIMIT 10")
        top_coins = self.db.cursor.fetchall()
        
        self.db.cursor.execute("SELECT first_name, boss_kills FROM users ORDER BY boss_kills DESC LIMIT 10")
        top_boss = self.db.cursor.fetchall()
        
        text = (
            f"╔══════════════════════════════╗\n"
            f"║    🏆 **ТОП ИГРОКОВ**      ║\n"
            f"╚══════════════════════════════╝\n\n"
        )
        
        text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "💰 **ПО МОНЕТАМ**\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        for i, (name, value) in enumerate(top_coins, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
            text += f"{medal} **{i}.** {name} — {value} 🪙\n"
        
        text += "\n━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "👾 **ПО УБИЙСТВУ БОССОВ**\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        for i, (name, value) in enumerate(top_boss, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
            text += f"{medal} **{i}.** {name} — {value} боссов\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_daily(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id, user.first_name, user.last_name or "")
        
        if self.db.is_muted(user.id):
            remaining = self.db.get_mute_time(user.id)
            await update.message.reply_text(f"🔇 Вы замучены. Осталось: {remaining}")
            return
        
        self.db.cursor.execute("SELECT last_daily, daily_streak FROM stats WHERE user_id = ?", (user.id,))
        result = self.db.cursor.fetchone()
        
        today = datetime.datetime.now().date()
        
        if result and result[0]:
            last_date = datetime.datetime.fromisoformat(result[0]).date()
            if last_date == today:
                await update.message.reply_text("❌ Ты уже получал награду сегодня!")
                return
        
        coins = random.randint(100, 300)
        streak = result[1] + 1 if result and result[0] else 1
        coins = int(coins * (1 + streak * 0.1))
        
        self.db.add_coins(user.id, coins)
        self.db.cursor.execute("UPDATE stats SET last_daily = ?, daily_streak = ? WHERE user_id = ?", (datetime.datetime.now(), streak, user.id))
        self.db.conn.commit()
        
        text = (
            f"╔══════════════════════════════╗\n"
            f"║    🎁 **ЕЖЕДНЕВНАЯ НАГРАДА**   ║\n"
            f"╚══════════════════════════════╝\n\n"
            f"▫️ **Стрик:** {streak} дней 🔥\n"
            f"▫️ **Монеты:** +{coins} 🪙\n\n"
            f"🌟 Заходи завтра снова!"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_boss_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        bosses = self.db.get_bosses(alive_only=True)
        
        if not bosses:
            await update.message.reply_text("👾 Все боссы повержены! Ждите возрождения...")
            self.db.respawn_bosses()
            bosses = self.db.get_bosses(alive_only=True)
        
        text = (
            f"╔══════════════════════════════╗\n"
            f"║    👾 **СПИСОК БОССОВ**     ║\n"
            f"╚══════════════════════════════╝\n\n"
        )
        
        for boss in bosses:
            text += f"**{boss[1]}** (ур.{boss[2]})\n"
            text += f"└ ID: {boss[0]} | ❤️ {boss[3]}/{boss[4]} | 💰 {boss[6]}\n\n"
        
        text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "⚔️ **Сразиться:** /boss_fight [ID]"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_boss_fight(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id, user.first_name, user.last_name or "")
        
        if self.db.is_muted(user.id):
            remaining = self.db.get_mute_time(user.id)
            await update.message.reply_text(f"🔇 Вы замучены. Осталось: {remaining}")
            return
        
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
        
        if user_data['energy'] < 10:
            await update.message.reply_text("❌ Нужно 10 энергии!")
            return
        
        self.db.add_energy(user.id, -10)
        
        player_damage = user_data['damage'] + random.randint(-5, 5)
        boss_damage = boss[5] + random.randint(-5, 5)
        player_taken = max(1, boss_damage - user_data['armor'] // 2)
        
        boss_killed = self.db.damage_boss(boss_id, player_damage)
        self.db.damage(user.id, player_taken)
        
        text = f"⚔️ **БИТВА С БОССОМ** ⚔️\n\n"
        text += f"▫️ **Ты нанес:** {player_damage} урона\n"
        text += f"▫️ **Босс нанес:** {player_taken} урона\n\n"
        
        if boss_killed:
            reward = boss[6] * (1 + user_data['level'] // 10)
            self.db.add_coins(user.id, reward)
            self.db.add_boss_kill(user.id)
            text += f"🎉 **ПОБЕДА!**\n💰 **Награда:** {reward} монет"
        else:
            boss_info = self.db.get_boss(boss_id)
            text += f"👾 **Босс еще жив!**\n❤️ **Осталось:** {boss_info[3]} здоровья"
        
        if user_data['health'] <= player_taken:
            self.db.heal(user.id, 50)
            text += "\n\n💀 Ты погиб, но воскрешен с 50❤️"
        
        self.db.add_stat(user.id, "games_played")
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_casino(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("🎰 Рулетка", callback_data="casino_roulette"),
             InlineKeyboardButton("🎲 Кости", callback_data="casino_dice")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🎰 **КАЗИНО «СПЕКТР»** 🎰\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🎰 **Рулетка** — ставь на цвет или число\n"
            "🎲 **Кости** — классическая игра\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Выбери игру:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def cmd_roulette(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id, user.first_name, user.last_name or "")
        
        bet = 10
        choice = "red"
        
        if context.args:
            try:
                bet = int(context.args[0])
                if len(context.args) > 1:
                    choice = context.args[1].lower()
            except:
                pass
        
        if bet > user_data['coins']:
            await update.message.reply_text(f"❌ У тебя только {user_data['coins']} 🪙")
            return
        
        numbers = list(range(0, 37))
        colors = {i: "red" if i in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36] else "black" for i in range(1, 37)}
        colors[0] = "green"
        
        result_num = random.choice(numbers)
        result_color = colors[result_num]
        
        win = False
        multiplier = 0
        
        if choice.isdigit():
            num = int(choice)
            if 0 <= num <= 36:
                if result_num == num:
                    win = True
                    multiplier = 36
        elif choice in ["red", "black", "green"]:
            if result_color == choice:
                win = True
                multiplier = 2 if choice in ["red", "black"] else 36
        
        if win:
            winnings = bet * multiplier
            self.db.add_coins(user.id, winnings)
            self.db.add_stat(user.id, "casino_wins", 1)
            result_text = f"🎉 **Ты выиграл {winnings} 🪙!**"
        else:
            self.db.add_coins(user.id, -bet)
            self.db.add_stat(user.id, "casino_losses", 1)
            result_text = f"😢 **Ты проиграл {bet} 🪙**"
        
        await update.message.reply_text(
            f"🎰 **РУЛЕТКА**\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"▫️ **Ставка:** {bet} 🪙\n"
            f"▫️ **Выбрано:** {choice}\n"
            f"▫️ **Выпало:** {result_num} {result_color}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{result_text}",
            parse_mode='Markdown'
        )
    
    async def cmd_dice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id, user.first_name, user.last_name or "")
        
        bet = 10
        if context.args:
            try:
                bet = int(context.args[0])
            except:
                pass
        
        if bet > user_data['coins']:
            await update.message.reply_text(f"❌ У тебя только {user_data['coins']} 🪙")
            return
        
        dice1 = random.randint(1, 6)
        dice2 = random.randint(1, 6)
        total = dice1 + dice2
        
        if total in [7, 11]:
            win = bet * 2
            result_text = f"🎉 Ты выиграл {win} 🪙!"
        elif total in [2, 3, 12]:
            win = 0
            result_text = f"😢 Ты проиграл {bet} 🪙"
        else:
            win = bet
            result_text = f"🔄 Ничья, ставка возвращена: {bet} 🪙"
        
        if win > 0:
            self.db.add_coins(user.id, win)
            self.db.add_stat(user.id, "casino_wins", 1)
        else:
            self.db.add_coins(user.id, -bet)
            self.db.add_stat(user.id, "casino_losses", 1)
        
        await update.message.reply_text(
            f"🎲 **КОСТИ**\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"▫️ **Ставка:** {bet} 🪙\n"
            f"▫️ **Кубики:** {dice1} + {dice2}\n"
            f"▫️ **Сумма:** {total}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{result_text}",
            parse_mode='Markdown'
        )
    
    async def cmd_rps(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [
                InlineKeyboardButton("🪨 Камень", callback_data="rps_rock"),
                InlineKeyboardButton("✂️ Ножницы", callback_data="rps_scissors"),
                InlineKeyboardButton("📄 Бумага", callback_data="rps_paper")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "✊ **КАМЕНЬ-НОЖНИЦЫ-БУМАГА**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🪨 Камень побеждает Ножницы\n"
            "✂️ Ножницы побеждают Бумагу\n"
            "📄 Бумага побеждает Камень\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "**Выбери свой ход:**",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def cmd_rr(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "💣 **РУССКАЯ РУЛЕТКА**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**Правила:**\n"
            "• Игроки по очереди стреляют\n"
            "• В барабане 1-3 патрона\n"
            "• Кто остался жив — забирает ставки\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "**Команды:**\n"
            "▫️ /rr_start [игроки] [ставка] — создать лобби\n"
            "▫️ /rr_shot — сделать выстрел"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_rr_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("💣 Функция будет доступна в следующем обновлении!")
    
    async def cmd_rr_shot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("💣 Ты выжил! (тест)")
    
    async def cmd_mute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Недостаточно прав")
            return
        
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /mute [ID] [минут]")
            return
        
        try:
            target_id = int(context.args[0])
            minutes = int(context.args[1])
            reason = " ".join(context.args[2:]) if len(context.args) > 2 else "Нарушение"
        except:
            await update.message.reply_text("❌ Неправильный формат")
            return
        
        if target_id == OWNER_ID:
            await update.message.reply_text("❌ Нельзя замутить владельца")
            return
        
        self.db.mute_user(target_id, minutes, update.effective_user.id, reason)
        await update.message.reply_text(f"🔇 Пользователь {target_id} замучен на {minutes} минут")
        
        try:
            await context.bot.send_message(chat_id=target_id, text=f"🔇 Вы замучены на {minutes} минут.\nПричина: {reason}")
        except:
            pass
    
    async def cmd_warn(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Недостаточно прав")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Использование: /warn [ID] [причина]")
            return
        
        try:
            target_id = int(context.args[0])
            reason = " ".join(context.args[1:]) if len(context.args) > 1 else "Нарушение"
        except:
            await update.message.reply_text("❌ Неправильный ID")
            return
        
        if target_id == OWNER_ID:
            await update.message.reply_text("❌ Нельзя выдать варн владельцу")
            return
        
        result = self.db.add_warn(target_id, update.effective_user.id, reason)
        await update.message.reply_text(result)
        
        try:
            await context.bot.send_message(chat_id=target_id, text=f"⚠️ Вам выдано предупреждение.\nПричина: {reason}")
        except:
            pass
    
    async def cmd_ban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Недостаточно прав")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Использование: /ban [ID]")
            return
        
        try:
            target_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ Неправильный ID")
            return
        
        if target_id == OWNER_ID:
            await update.message.reply_text("❌ Нельзя забанить владельца")
            return
        
        self.db.ban_user(target_id, update.effective_user.id)
        await update.message.reply_text(f"🚫 Пользователь {target_id} забанен")
        
        try:
            await context.bot.send_message(chat_id=target_id, text="🚫 Вы забанены в боте.")
        except:
            pass
    
    async def cmd_unban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Недостаточно прав")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Использование: /unban [ID]")
            return
        
        try:
            target_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ Неправильный ID")
            return
        
        self.db.unban_user(target_id)
        await update.message.reply_text(f"✅ Пользователь {target_id} разбанен")
        
        try:
            await context.bot.send_message(chat_id=target_id, text="✅ Вы разбанены в боте.")
        except:
            pass
    
    async def cmd_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        rules = self.db.get_group_rules(chat_id)
        
        if rules:
            await update.message.reply_text(
                f"📜 **ПРАВИЛА ЧАТА**\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"{rules}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "📜 **ПРАВИЛА ЧАТА**\n\n"
                "В этом чате ещё нет правил.\n"
                "Установите их командой:\n"
                "/set_rules [текст]"
            )
    
    async def cmd_set_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        if chat_member.status not in ['creator', 'administrator']:
            await update.message.reply_text("❌ Только администраторы могут устанавливать правила")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Укажи текст правил: /set_rules Текст правил")
            return
        
        rules = " ".join(context.args)
        self.db.set_group_rules(chat_id, rules, user_id)
        
        await update.message.reply_text(
            f"✅ **Правила установлены!**\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{rules}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━"
        )
    
    async def cmd_group_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        if chat_member.status not in ['creator', 'administrator']:
            await update.message.reply_text("❌ Только администраторы могут просматривать настройки")
            return
        
        settings = self.db.get_group_settings(chat_id)
        
        text = (
            f"⚙️ **НАСТРОЙКИ ГРУППЫ**\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👋 **Приветствие:** {'✅ Включено' if settings['welcome_enabled'] else '❌ Выключено'}\n"
            f"📝 **Текст:** {settings['welcome_message']}\n\n"
            f"👋 **Прощание:** {'✅ Включено' if settings['goodbye_enabled'] else '❌ Выключено'}\n"
            f"📝 **Текст:** {settings['goodbye_message']}\n\n"
            f"🚫 **Анти-спам:** {'✅ Вкл' if settings['anti_spam'] else '❌ Выкл'}\n"
            f"🚫 **Лимит капса:** {settings['caps_limit']}\n"
            f"🚫 **Лимит эмодзи:** {settings['emoji_limit']}\n"
            f"🔗 **Блок ссылок:** {'✅ Вкл' if settings['link_block'] else '❌ Выкл'}\n"
            f"🌐 **Язык:** {settings['language']}\n"
            f"⚠️ **Лимит варнов:** {settings['warn_limit']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_set_welcome(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        if chat_member.status not in ['creator', 'administrator']:
            await update.message.reply_text("❌ Только администраторы могут изменять приветствие")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Укажи текст приветствия. Используй {user} для имени")
            return
        
        message = " ".join(context.args)
        self.db.update_group_setting(chat_id, 'welcome_message', message)
        self.db.update_group_setting(chat_id, 'welcome_enabled', 1)
        
        await update.message.reply_text(f"✅ **Приветствие установлено!**\n\n{message}")
    
    async def cmd_set_goodbye(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        if chat_member.status not in ['creator', 'administrator']:
            await update.message.reply_text("❌ Только администраторы могут изменять прощание")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Укажи текст прощания. Используй {user} для имени")
            return
        
        message = " ".join(context.args)
        self.db.update_group_setting(chat_id, 'goodbye_message', message)
        self.db.update_group_setting(chat_id, 'goodbye_enabled', 1)
        
        await update.message.reply_text(f"✅ **Прощание установлено!**\n\n{message}")
    
    async def handle_new_members(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        settings = self.db.get_group_settings(chat_id)
        
        if not settings['welcome_enabled']:
            return
        
        for member in update.message.new_chat_members:
            if member.is_bot:
                continue
            
            welcome = settings['welcome_message'].replace('{user}', f"[{member.first_name}](tg://user?id={member.id})")
            await update.message.reply_text(welcome, parse_mode='Markdown')
    
    async def handle_left_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        settings = self.db.get_group_settings(chat_id)
        
        if not settings['goodbye_enabled']:
            return
        
        member = update.message.left_chat_member
        if member.is_bot:
            return
        
        goodbye = settings['goodbye_message'].replace('{user}', f"[{member.first_name}](tg://user?id={member.id})")
        await update.message.reply_text(goodbye, parse_mode='Markdown')
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        message_text = update.message.text
        
        if self.db.is_banned(user.id):
            return
        
        if self.db.is_muted(user.id):
            remaining = self.db.get_mute_time(user.id)
            await update.message.reply_text(f"🔇 Вы замучены. Осталось: {remaining}")
            return
        
        if await self.check_spam(update):
            return
        
        # Пробуем OpenRouter
        response = await self.ai.get_response(message_text)
        if response:
            await update.message.reply_text(f"🤖 **СПЕКТР:** {response}", parse_mode='Markdown')
            self.db.add_stat(user.id, "messages_count")
            return
        
        # Если OpenRouter не ответил — заготовки
        msg_lower = message_text.lower()
        
        if any(word in msg_lower for word in ["привет", "здравствуй", "хай"]):
            await update.message.reply_text("👋 Привет! Как твои дела?")
        
        elif any(word in msg_lower for word in ["как дела", "как ты"]):
            await update.message.reply_text("⚙️ Всё отлично! А у тебя?")
        
        elif any(word in msg_lower for word in ["спасибо", "благодарю"]):
            await update.message.reply_text("🤝 Всегда пожалуйста!")
        
        elif any(word in msg_lower for word in ["пока", "до свидания"]):
            await update.message.reply_text("👋 До встречи!")
        
        elif any(word in msg_lower for word in ["кто ты", "ты кто"]):
            await update.message.reply_text("🤖 Я — СПЕКТР, твой игровой помощник!")
        
        elif any(word in msg_lower for word in ["что ты умеешь", "твои функции"]):
            await update.message.reply_text("📋 Мои возможности в /help")
        
        elif any(word in msg_lower for word in ["босс", "битва"]):
            await update.message.reply_text("👾 Боссы ждут! /bosses")
        
        elif any(word in msg_lower for word in ["профиль", "статистика"]):
            await update.message.reply_text("📊 Твой профиль: /profile")
        
        elif any(word in msg_lower for word in ["награда", "бонус"]):
            await update.message.reply_text("🎁 Ежедневная награда: /daily")
        
        elif any(word in msg_lower for word in ["помощь", "хелп"]):
            await update.message.reply_text("📚 Все команды: /help")
        
        elif any(word in msg_lower for word in ["кто создал", "владелец"]):
            await update.message.reply_text(f"👑 Владелец: {OWNER_USERNAME}")
        
        else:
            responses = [
                "🤖 Я внимательно слушаю. Можешь уточнить?",
                "🎯 Напиши /help, чтобы увидеть команды.",
                "💡 Хочешь сразиться с боссом? /bosses",
                "📊 Хочешь узнать статистику? /profile",
                "🎁 Не забудь /daily!"
            ]
            await update.message.reply_text(random.choice(responses))
        
        self.db.add_stat(user.id, "messages_count")
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user = update.effective_user
        data = query.data
        
        if data == "menu_profile":
            await self.cmd_profile(update, context)
        elif data == "menu_stats":
            await query.edit_message_text(
                "📊 **СТАТИСТИКА**\n\n"
                "▫️ /boss_stats — боссы\n"
                "▫️ /mafia_stats — мафия\n"
                "▫️ /rps_stats — КНБ\n"
                "▫️ /casino_stats — казино\n"
                "▫️ /rr_stats — русская рулетка",
                parse_mode='Markdown'
            )
        elif data == "menu_bosses":
            await self.cmd_boss_list(update, context)
        elif data == "menu_casino":
            await self.cmd_casino(update, context)
        elif data == "menu_rps":
            await self.cmd_rps(update, context)
        elif data == "menu_rr":
            await self.cmd_rr(update, context)
        elif data == "menu_groups":
            await query.edit_message_text(
                "👥 **ГРУППЫ**\n\n"
                "▫️ /rules — правила\n"
                "▫️ /set_rules — установить правила\n"
                "▫️ /group_settings — настройки\n"
                "▫️ /set_welcome — приветствие\n"
                "▫️ /set_goodbye — прощание",
                parse_mode='Markdown'
            )
        elif data == "menu_help":
            await self.cmd_help(update, context)
        elif data == "casino_roulette":
            await self.cmd_roulette(update, context)
        elif data == "casino_dice":
            await self.cmd_dice(update, context)
        elif data.startswith("rps_"):
            choice = data.split('_')[1]
            bot_choice = random.choice(["rock", "scissors", "paper"])
            
            choices = {"rock": "🪨 Камень", "scissors": "✂️ Ножницы", "paper": "📄 Бумага"}
            
            result_map = {
                ("rock", "scissors"): "win", ("rock", "paper"): "lose",
                ("scissors", "paper"): "win", ("scissors", "rock"): "lose",
                ("paper", "rock"): "win", ("paper", "scissors"): "lose"
            }
            
            if choice == bot_choice:
                result = "draw"
                self.db.cursor.execute("UPDATE users SET rps_draws = rps_draws + 1 WHERE user_id = ?", (user.id,))
                text = f"{choices[choice]} vs {choices[bot_choice]}\n\n🤝 **Ничья!**"
            else:
                result = result_map.get((choice, bot_choice), "lose")
                if result == "win":
                    self.db.cursor.execute("UPDATE users SET rps_wins = rps_wins + 1 WHERE user_id = ?", (user.id,))
                    text = f"{choices[choice]} vs {choices[bot_choice]}\n\n🎉 **Ты выиграл!**"
                else:
                    self.db.cursor.execute("UPDATE users SET rps_losses = rps_losses + 1 WHERE user_id = ?", (user.id,))
                    text = f"{choices[choice]} vs {choices[bot_choice]}\n\n😢 **Ты проиграл!**"
            
            self.db.conn.commit()
            await query.edit_message_text(text, parse_mode='Markdown')
    
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
        if self.ai:
            await self.ai.close()
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
