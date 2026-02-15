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

# Настройки
SPAM_LIMIT = 5
SPAM_WINDOW = 3
SPAM_MUTE_TIME = 120

# Цены на привилегии
VIP_PRICE = 5000
PREMIUM_PRICE = 15000
VIP_DAYS = 30
PREMIUM_DAYS = 30

# ===================== БАЗА ДАННЫХ =====================
class Database:
    def __init__(self, db_name="spectrum_bot.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
        self.migrate_tables()
        self.init_bosses()
    
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
            if 'health' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN health INTEGER DEFAULT 100")
            if 'armor' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN armor INTEGER DEFAULT 0")
            if 'damage' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN damage INTEGER DEFAULT 10")
            if 'boss_kills' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN boss_kills INTEGER DEFAULT 0")
            if 'vip_until' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN vip_until TIMESTAMP")
            if 'premium_until' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN premium_until TIMESTAMP")
            if 'clan_id' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN clan_id INTEGER DEFAULT 0")
            if 'clan_role' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN clan_role TEXT DEFAULT 'member'")
            self.conn.commit()
        except Exception as e:
            print(f"Ошибка миграции: {e}")
    
    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                level INTEGER DEFAULT 1,
                exp INTEGER DEFAULT 0,
                coins INTEGER DEFAULT 1000,
                energy INTEGER DEFAULT 100,
                reputation INTEGER DEFAULT 0,
                role TEXT DEFAULT 'user',
                warns INTEGER DEFAULT 0,
                mute_until TIMESTAMP,
                banned INTEGER DEFAULT 0,
                health INTEGER DEFAULT 100,
                armor INTEGER DEFAULT 0,
                damage INTEGER DEFAULT 10,
                boss_kills INTEGER DEFAULT 0,
                vip_until TIMESTAMP,
                premium_until TIMESTAMP,
                clan_id INTEGER DEFAULT 0,
                clan_role TEXT DEFAULT 'member',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
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
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS bosses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                boss_name TEXT,
                boss_level INTEGER,
                boss_health INTEGER,
                boss_max_health INTEGER,
                boss_damage INTEGER,
                boss_reward INTEGER,
                boss_image TEXT,
                is_alive INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS clans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                owner_id INTEGER,
                level INTEGER DEFAULT 1,
                exp INTEGER DEFAULT 0,
                members INTEGER DEFAULT 1,
                rating INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS clan_members (
                clan_id INTEGER,
                user_id INTEGER,
                role TEXT DEFAULT 'member',
                joined_at TIMESTAMP,
                FOREIGN KEY (clan_id) REFERENCES clans (id),
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        self.conn.commit()
    
    def init_bosses(self):
        self.cursor.execute("SELECT * FROM bosses")
        if not self.cursor.fetchone():
            bosses_data = [
                ("🌲 Лесной тролль", 5, 200, 20, 100, ""),
                ("🐉 Огненный дракон", 10, 500, 40, 250, ""),
                ("❄️ Ледяной великан", 15, 1000, 60, 500, ""),
                ("⚔️ Темный рыцарь", 20, 2000, 80, 1000, ""),
                ("👾 Король демонов", 25, 5000, 150, 2500, ""),
                ("💀 Бог разрушения", 30, 10000, 300, 5000, "")
            ]
            for name, level, health, damage, reward, image in bosses_data:
                self.cursor.execute('''
                    INSERT INTO bosses (boss_name, boss_level, boss_health, boss_max_health, boss_damage, boss_reward, boss_image)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (name, level, health, health, damage, reward, image))
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
    
    def add_exp(self, user_id: int, exp: int):
        self.cursor.execute("UPDATE users SET exp = exp + ? WHERE user_id = ?", (exp, user_id))
        
        self.cursor.execute("SELECT exp, level FROM users WHERE user_id = ?", (user_id,))
        user = self.cursor.fetchone()
        
        exp_needed = user[1] * 100
        if user[0] >= exp_needed:
            self.cursor.execute("UPDATE users SET level = level + 1, exp = exp - ? WHERE user_id = ?", (exp_needed, user_id))
        self.conn.commit()
    
    def add_energy(self, user_id: int, energy: int):
        self.cursor.execute("UPDATE users SET energy = energy + ? WHERE user_id = ?", (energy, user_id))
        self.conn.commit()
    
    def add_stat(self, user_id: int, stat: str, value: int = 1):
        self.cursor.execute(f"UPDATE stats SET {stat} = {stat} + ? WHERE user_id = ?", (value, user_id))
        self.conn.commit()
    
    def damage(self, user_id: int, amount: int):
        self.cursor.execute("UPDATE users SET health = health - ? WHERE user_id = ?", (amount, user_id))
        self.conn.commit()
    
    def heal(self, user_id: int, amount: int):
        self.cursor.execute("UPDATE users SET health = health + ? WHERE user_id = ?", (amount, user_id))
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
    
    def is_vip(self, user_id: int) -> bool:
        self.cursor.execute("SELECT vip_until FROM users WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()
        if result and result[0]:
            vip_until = datetime.datetime.fromisoformat(result[0])
            return datetime.datetime.now() < vip_until
        return False
    
    def is_premium(self, user_id: int) -> bool:
        self.cursor.execute("SELECT premium_until FROM users WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()
        if result and result[0]:
            premium_until = datetime.datetime.fromisoformat(result[0])
            return datetime.datetime.now() < premium_until
        return False
    
    def set_vip(self, user_id: int, days: int):
        vip_until = datetime.datetime.now() + datetime.timedelta(days=days)
        self.cursor.execute("UPDATE users SET vip_until = ?, role = 'vip' WHERE user_id = ?", (vip_until, user_id))
        self.conn.commit()
    
    def set_premium(self, user_id: int, days: int):
        premium_until = datetime.datetime.now() + datetime.timedelta(days=days)
        self.cursor.execute("UPDATE users SET premium_until = ?, role = 'premium' WHERE user_id = ?", (premium_until, user_id))
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
    
    def add_boss_kill(self, user_id):
        self.cursor.execute("UPDATE users SET boss_kills = boss_kills + 1 WHERE user_id = ?", (user_id,))
        self.conn.commit()
    
    def get_top(self, by="coins", limit=10):
        self.cursor.execute(f"SELECT first_name, {by} FROM users ORDER BY {by} DESC LIMIT ?", (limit,))
        return self.cursor.fetchall()
    
    def create_clan(self, name, owner_id):
        try:
            self.cursor.execute("INSERT INTO clans (name, owner_id) VALUES (?, ?)", (name, owner_id))
            self.conn.commit()
            clan_id = self.cursor.lastrowid
            self.cursor.execute("INSERT INTO clan_members (clan_id, user_id, role, joined_at) VALUES (?, ?, ?, ?)", (clan_id, owner_id, 'owner', datetime.datetime.now()))
            self.cursor.execute("UPDATE users SET clan_id = ?, clan_role = 'owner' WHERE user_id = ?", (clan_id, owner_id))
            self.conn.commit()
            return clan_id
        except:
            return None
    
    def get_clan(self, clan_id):
        self.cursor.execute("SELECT * FROM clans WHERE id = ?", (clan_id,))
        return self.cursor.fetchone()
    
    def get_user_clan(self, user_id):
        self.cursor.execute("SELECT clan_id FROM users WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()
        if result and result[0]:
            return self.get_clan(result[0])
        return None
    
    def get_clan_members(self, clan_id):
        self.cursor.execute('''
            SELECT u.user_id, u.first_name, u.last_name, u.level, u.damage, cm.role
            FROM clan_members cm
            JOIN users u ON cm.user_id = u.user_id
            WHERE cm.clan_id = ?
        ''', (clan_id,))
        return self.cursor.fetchall()
    
    def join_clan(self, user_id, clan_id):
        self.cursor.execute("INSERT INTO clan_members (clan_id, user_id, role, joined_at) VALUES (?, ?, ?, ?)", (clan_id, user_id, 'member', datetime.datetime.now()))
        self.cursor.execute("UPDATE users SET clan_id = ?, clan_role = 'member' WHERE user_id = ?", (clan_id, user_id))
        self.cursor.execute("UPDATE clans SET members = members + 1 WHERE id = ?", (clan_id,))
        self.conn.commit()
    
    def leave_clan(self, user_id, clan_id):
        self.cursor.execute("DELETE FROM clan_members WHERE clan_id = ? AND user_id = ?", (clan_id, user_id))
        self.cursor.execute("UPDATE users SET clan_id = 0, clan_role = 'member' WHERE user_id = ?", (user_id,))
        self.cursor.execute("UPDATE clans SET members = members - 1 WHERE id = ?", (clan_id,))
        self.conn.commit()
    
    def close(self):
        self.conn.close()

# ===================== БАЗА ДАННЫХ =====================
db = Database()

# ===================== УМНЫЙ ИИ (ЛОКАЛЬНЫЙ) =====================
class SpectrumAI:
    def __init__(self):
        import google.generativeai as genai
        self.api_key = "AIzaSyBG0pZQqm8JXhhmfosxh0G4ksddcDe6P5M"
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        self.chats = {}
        print("🤖 Gemini ИНИЦИАЛИЗИРОВАН!")
    
    async def get_response(self, user_id: int, message: str) -> str:
        print(f"📨 Получено сообщение: {message}")
        
        # Пробуем Gemini
        try:
            # Создаем чат если нужно
            if user_id not in self.chats:
                self.chats[user_id] = self.model.start_chat()
            
            # Отправляем запрос
            response = self.chats[user_id].send_message(
                f"Ты игровой бот «СПЕКТР». Отвечай кратко и дружелюбно. Вопрос: {message}"
            )
            
            if response and response.text:
                print(f"✅ Gemini ответил: {response.text[:50]}...")
                return f"🤖 **СПЕКТР:** {response.text}"
            else:
                print("❌ Gemini вернул пустой ответ")
                
        except Exception as e:
            print(f"❌ Ошибка Gemini: {e}")
        
        # Если Gemini не сработал
        return "❌ Gemini временно недоступен. Попробуй позже."
    
    async def close(self):
        pass
# ===================== ОСНОВНОЙ КЛАСС БОТА =====================
class GameBot:
    def __init__(self):
        self.db = db
        self.ai = SpectrumAI()
        self.spam_tracker = defaultdict(list)
        self.application = Application.builder().token(TELEGRAM_TOKEN).build()
        self.setup_handlers()
        logger.info("✅ Бот «СПЕКТР» инициализирован")
    
    def setup_handlers(self):
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        self.application.add_handler(CommandHandler("profile", self.cmd_profile))
        self.application.add_handler(CommandHandler("top", self.cmd_top))
        self.application.add_handler(CommandHandler("daily", self.cmd_daily))
        self.application.add_handler(CommandHandler("bosses", self.cmd_boss_list))
        self.application.add_handler(CommandHandler("boss_fight", self.cmd_boss_fight))
        self.application.add_handler(CommandHandler("shop", self.cmd_shop))
        self.application.add_handler(CommandHandler("buy", self.cmd_buy))
        self.application.add_handler(CommandHandler("donate", self.cmd_donate))
        self.application.add_handler(CommandHandler("vip", self.cmd_vip))
        self.application.add_handler(CommandHandler("premium", self.cmd_premium))
        self.application.add_handler(CommandHandler("clan", self.cmd_clan))
        self.application.add_handler(CommandHandler("clan_create", self.cmd_clan_create))
        self.application.add_handler(CommandHandler("clan_join", self.cmd_clan_join))
        self.application.add_handler(CommandHandler("clan_leave", self.cmd_clan_leave))
        self.application.add_handler(CommandHandler("mute", self.cmd_mute))
        self.application.add_handler(CommandHandler("warn", self.cmd_warn))
        self.application.add_handler(CommandHandler("ban", self.cmd_ban))
        self.application.add_handler(CommandHandler("unban", self.cmd_unban))
        self.application.add_handler(CommandHandler("give", self.cmd_give))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        logger.info("✅ Все обработчики зарегистрированы")
    
    def is_admin(self, user_id: int) -> bool:
        user = self.db.get_user(user_id)
        return user.get('role', 'user') in ['owner', 'admin']
    
    def is_owner(self, user_id: int) -> bool:
        return user_id == OWNER_ID
    
    def is_vip(self, user_id: int) -> bool:
        return self.db.is_vip(user_id) or self.is_admin(user_id)
    
    def is_premium(self, user_id: int) -> bool:
        return self.db.is_premium(user_id) or self.is_admin(user_id)
    
    def get_role_emoji(self, role):
        emojis = {
            'owner': '👑',
            'admin': '⚜️',
            'premium': '💎',
            'vip': '🌟',
            'user': '👤'
        }
        return emojis.get(role, '👤')
    
    def calc_winrate(self, wins, games):
        if games == 0:
            return 0
        return round((wins / games) * 100, 1)
    
    async def check_spam(self, update: Update) -> bool:
        user_id = update.effective_user.id
        if self.is_admin(user_id) or self.is_owner(user_id) or self.is_premium(user_id):
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
            f"⚔️ **ДОБРО ПОЖАЛОВАТЬ В «СПЕКТР», {user.first_name}!** ⚔️\n\n"
            f"🎮 **Твой статус:** {self.get_role_emoji('user')} user\n"
            f"💰 **Монеты:** 1000 🪙\n\n"
            f"**ОСНОВНЫЕ КОМАНДЫ:**\n"
            f"👤 /profile - Твой профиль\n"
            f"🏆 /top - Топ игроков\n"
            f"🎁 /daily - Ежедневная награда\n"
            f"👾 /bosses - Битвы с боссами\n"
            f"🛍 /shop - Магазин\n"
            f"💎 /donate - Привилегии\n"
            f"👥 /clan - Кланы\n"
            f"📚 /help - Все команды\n\n"
            f"👑 **Владелец:** {OWNER_USERNAME}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
        self.db.add_stat(user.id, "commands_used")
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        text = (
            "📚 **ВСЕ КОМАНДЫ БОТА «СПЕКТР»**\n\n"
            
            "👤 **ПРОФИЛЬ**\n"
            "/profile - Твой профиль\n"
            "/top - Топ игроков\n"
            "/daily - Ежедневная награда\n\n"
            
            "👾 **БОССЫ**\n"
            "/bosses - Список боссов\n"
            "/boss_fight [ID] - Сразиться с боссом\n\n"
            
            "🛍 **МАГАЗИН**\n"
            "/shop - Магазин\n"
            "/buy [предмет] - Купить предмет\n"
            "/donate - Привилегии\n"
            "/vip - Купить VIP (5000 🪙)\n"
            "/premium - Купить Premium (15000 🪙)\n\n"
            
            "👥 **КЛАНЫ**\n"
            "/clan - Инфо о клане\n"
            "/clan_create [название] - Создать клан\n"
            "/clan_join [ID] - Вступить в клан\n"
            "/clan_leave - Покинуть клан\n\n"
            
            "👑 **АДМИН КОМАНДЫ**\n"
            "/mute [ID] [минут] - Замутить\n"
            "/warn [ID] - Выдать варн\n"
            "/ban [ID] - Забанить\n"
            "/unban [ID] - Разбанить\n"
            "/give [ID] [сумма] - Выдать монеты\n\n"
            
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
        
        vip_status = "✅ Активен" if self.is_vip(user.id) else "❌ Нет"
        premium_status = "✅ Активен" if self.is_premium(user.id) else "❌ Нет"
        
        clan = self.db.get_user_clan(user.id)
        clan_name = clan[1] if clan else "Нет"
        
        text = (
            f"👤 **ПРОФИЛЬ ИГРОКА**\n\n"
            f"**Основное:**\n"
            f"Имя: {user_data.get('first_name', user.first_name)}\n"
            f"Роль: {self.get_role_emoji(user_data.get('role', 'user'))} {user_data.get('role', 'user')}\n"
            f"Уровень: {user_data.get('level', 1)}\n"
            f"Опыт: {user_data.get('exp', 0)}/{user_data.get('level', 1) * 100}\n"
            f"Монеты: {user_data.get('coins', 1000)} 🪙\n"
            f"Энергия: {user_data.get('energy', 100)} ⚡\n\n"
            
            f"**Боевые характеристики:**\n"
            f"Здоровье: {user_data.get('health', 100)} ❤️\n"
            f"Броня: {user_data.get('armor', 0)} 🛡\n"
            f"Урон: {user_data.get('damage', 10)} ⚔️\n"
            f"Боссов убито: {user_data.get('boss_kills', 0)} 👾\n\n"
            
            f"**Привилегии:**\n"
            f"VIP: {vip_status}\n"
            f"Premium: {premium_status}\n\n"
            
            f"**Клан:**\n"
            f"Название: {clan_name}\n"
            f"Роль в клане: {user_data.get('clan_role', 'member')}\n\n"
            
            f"**Статистика:**\n"
            f"Сообщений: {stats[1] if stats else 0}\n"
            f"Команд: {stats[2] if stats else 0}\n"
            f"Игр сыграно: {stats[3] if stats else 0}\n"
            f"Дней подряд: {stats[4] if stats else 0}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
        self.db.add_stat(user.id, "commands_used")
    
    async def cmd_top(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        top_coins = self.db.get_top("coins", 10)
        top_level = self.db.get_top("level", 10)
        top_boss = self.db.get_top("boss_kills", 10)
        
        text = "🏆 **ТОП ИГРОКОВ**\n\n"
        
        text += "💰 **По монетам:**\n"
        for i, (name, value) in enumerate(top_coins, 1):
            text += f"{i}. {name} - {value} 🪙\n"
        
        text += "\n📊 **По уровню:**\n"
        for i, (name, value) in enumerate(top_level, 1):
            text += f"{i}. {name} - {value} ур.\n"
        
        text += "\n👾 **По убийству боссов:**\n"
        for i, (name, value) in enumerate(top_boss, 1):
            text += f"{i}. {name} - {value} боссов\n"
        
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
        exp = random.randint(20, 60)
        energy = random.randint(10, 30)
        
        streak = result[1] + 1 if result and result[0] else 1
        
        coins = int(coins * (1 + streak * 0.1))
        exp = int(exp * (1 + streak * 0.1))
        
        if self.is_vip(user.id):
            coins = int(coins * 1.5)
            exp = int(exp * 1.5)
        if self.is_premium(user.id):
            coins = int(coins * 2)
            exp = int(exp * 2)
        
        self.db.add_coins(user.id, coins)
        self.db.add_exp(user.id, exp)
        self.db.add_energy(user.id, energy)
        
        self.db.cursor.execute("UPDATE stats SET last_daily = ?, daily_streak = ? WHERE user_id = ?", (datetime.datetime.now(), streak, user.id))
        self.db.conn.commit()
        
        await update.message.reply_text(
            f"🎁 **ЕЖЕДНЕВНАЯ НАГРАДА**\n\n"
            f"🔥 Стрик: {streak} дней\n"
            f"💰 +{coins} монет\n"
            f"✨ +{exp} опыта\n"
            f"⚡ +{energy} энергии",
            parse_mode='Markdown'
        )
    
    async def cmd_boss_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        bosses = self.db.get_bosses(alive_only=True)
        
        if not bosses:
            await update.message.reply_text("👾 Все боссы повержены! Ждите возрождения...")
            self.db.respawn_bosses()
            bosses = self.db.get_bosses(alive_only=True)
            if not bosses:
                await update.message.reply_text("❌ Не удалось возродить боссов")
                return
        
        text = "👾 **СПИСОК БОССОВ**\n\n"
        for boss in bosses[:10]:
            text += f"**{boss[1]}** (ур.{boss[2]})\n"
            text += f"ID: {boss[0]} | ❤️ {boss[3]}/{boss[4]} | 💰 {boss[6]}\n\n"
        
        text += "Сразиться: /boss_fight [ID]"
        
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
        
        if not boss or not boss[8]:
            await update.message.reply_text("❌ Босс уже повержен или не найден")
            return
        
        if user_data['energy'] < 10:
            await update.message.reply_text("❌ Нужно 10 энергии для битвы!")
            return
        
        self.db.add_energy(user.id, -10)
        
        player_damage = user_data['damage'] + random.randint(-5, 5)
        boss_damage = boss[5] + random.randint(-5, 5)
        player_taken = max(1, boss_damage - user_data['armor'] // 2)
        
        if self.is_vip(user.id):
            player_damage = int(player_damage * 1.2)
        if self.is_premium(user.id):
            player_damage = int(player_damage * 1.5)
        
        boss_killed = self.db.damage_boss(boss_id, player_damage)
        self.db.damage(user.id, player_taken)
        
        text = f"⚔️ **БИТВА С БОССОМ** ⚔️\n\n"
        text += f"Ты нанес {player_damage} урона!\n"
        text += f"Босс нанес тебе {player_taken} урона!\n\n"
        
        if boss_killed:
            reward = boss[6] * (1 + user_data['level'] // 10)
            if self.is_vip(user.id):
                reward = int(reward * 1.5)
            if self.is_premium(user.id):
                reward = int(reward * 2)
            
            self.db.add_coins(user.id, reward)
            self.db.add_boss_kill(user.id)
            self.db.add_exp(user.id, boss[2] * 10)
            
            text += f"🎉 **ПОБЕДА!**\n"
            text += f"💰 Награда: {reward} монет\n"
            text += f"✨ Опыт: +{boss[2] * 10}"
        else:
            boss_info = self.db.get_boss(boss_id)
            text += f"👾 Босс еще жив! Осталось {boss_info[3]}❤️"
        
        if user_data['health'] <= player_taken:
            self.db.heal(user.id, 50)
            text += "\n\n💀 Ты погиб в бою, но воскрешен с 50❤️"
        
        self.db.add_stat(user.id, "games_played")
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_shop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "🏪 **МАГАЗИН «СПЕКТР»**\n\n"
            
            "💊 **ЗЕЛЬЯ**\n"
            "• Зелье здоровья - 50 🪙 (❤️+30)\n"
            "• Большое зелье - 100 🪙 (❤️+70)\n\n"
            
            "⚔️ **ОРУЖИЕ**\n"
            "• Меч - 200 🪙 (⚔️+10)\n"
            "• Легендарный меч - 500 🪙 (⚔️+30)\n\n"
            
            "🛡 **БРОНЯ**\n"
            "• Щит - 150 🪙 (🛡+5)\n"
            "• Доспехи - 400 🪙 (🛡+15)\n\n"
            
            "⚡ **ЭНЕРГИЯ**\n"
            "• Энергетик - 30 🪙 (⚡+20)\n"
            "• Батарейка - 80 🪙 (⚡+50)\n\n"
            
            "Купить: /buy [название]"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_buy(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id, user.first_name, user.last_name or "")
        
        if self.db.is_muted(user.id):
            remaining = self.db.get_mute_time(user.id)
            await update.message.reply_text(f"🔇 Вы замучены. Осталось: {remaining}")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Укажи предмет: /buy меч")
            return
        
        item = " ".join(context.args).lower()
        
        items = {
            "зелье здоровья": {"price": 50, "heal": 30},
            "большое зелье": {"price": 100, "heal": 70},
            "меч": {"price": 200, "damage": 10},
            "легендарный меч": {"price": 500, "damage": 30},
            "щит": {"price": 150, "armor": 5},
            "доспехи": {"price": 400, "armor": 15},
            "энергетик": {"price": 30, "energy": 20},
            "батарейка": {"price": 80, "energy": 50}
        }
        
        if item not in items:
            await update.message.reply_text("❌ Такого предмета нет в магазине")
            return
        
        item_data = items[item]
        
        if user_data['coins'] < item_data['price']:
            await update.message.reply_text(f"❌ Недостаточно монет! Нужно {item_data['price']} 🪙")
            return
        
        self.db.add_coins(user.id, -item_data['price'])
        
        if 'heal' in item_data:
            self.db.heal(user.id, item_data['heal'])
            await update.message.reply_text(f"✅ Здоровье +{item_data['heal']}❤️")
        
        elif 'damage' in item_data:
            self.db.cursor.execute("UPDATE users SET damage = damage + ? WHERE user_id = ?", (item_data['damage'], user.id))
            self.db.conn.commit()
            await update.message.reply_text(f"✅ Урон +{item_data['damage']}⚔️")
        
        elif 'armor' in item_data:
            self.db.cursor.execute("UPDATE users SET armor = armor + ? WHERE user_id = ?", (item_data['armor'], user.id))
            self.db.conn.commit()
            await update.message.reply_text(f"✅ Броня +{item_data['armor']}🛡")
        
        elif 'energy' in item_data:
            self.db.add_energy(user.id, item_data['energy'])
            await update.message.reply_text(f"✅ Энергия +{item_data['energy']}⚡")
    
    async def cmd_donate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "💎 **ПРИВИЛЕГИИ «СПЕКТР»** 💎\n\n"
            
            "🌟 **VIP СТАТУС**\n"
            f"• Цена: {VIP_PRICE} 🪙\n"
            f"• Длительность: {VIP_DAYS} дней\n"
            "• Бонусы:\n"
            "  - Урон в битвах +20%\n"
            "  - Награда с боссов +50%\n"
            "  - Ежедневный бонус +50%\n"
            "  - Нет спам-фильтра\n"
            f"• Купить: /vip\n\n"
            
            "💎 **PREMIUM СТАТУС**\n"
            f"• Цена: {PREMIUM_PRICE} 🪙\n"
            f"• Длительность: {PREMIUM_DAYS} дней\n"
            "• Бонусы:\n"
            "  - Все бонусы VIP\n"
            "  - Урон в битвах +50%\n"
            "  - Награда с боссов +100%\n"
            "  - Ежедневный бонус +100%\n\n"
            
            f"👑 По вопросам доната: {OWNER_USERNAME}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_vip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id, user.first_name, user.last_name or "")
        
        if user_data['coins'] < VIP_PRICE:
            await update.message.reply_text(f"❌ Недостаточно монет! Нужно {VIP_PRICE} 🪙")
            return
        
        if self.is_vip(user.id):
            await update.message.reply_text("❌ У тебя уже есть VIP статус!")
            return
        
        self.db.add_coins(user.id, -VIP_PRICE)
        self.db.set_vip(user.id, VIP_DAYS)
        
        await update.message.reply_text(f"🌟 **ПОЗДРАВЛЯЮ!**\n\nТеперь у тебя VIP статус на {VIP_DAYS} дней!", parse_mode='Markdown')
    
    async def cmd_premium(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id, user.first_name, user.last_name or "")
        
        if user_data['coins'] < PREMIUM_PRICE:
            await update.message.reply_text(f"❌ Недостаточно монет! Нужно {PREMIUM_PRICE} 🪙")
            return
        
        if self.is_premium(user.id):
            await update.message.reply_text("❌ У тебя уже есть Premium статус!")
            return
        
        self.db.add_coins(user.id, -PREMIUM_PRICE)
        self.db.set_premium(user.id, PREMIUM_DAYS)
        
        await update.message.reply_text(f"💎 **ПОЗДРАВЛЯЮ!**\n\nТеперь у тебя PREMIUM статус на {PREMIUM_DAYS} дней!", parse_mode='Markdown')
    
    async def cmd_clan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        clan = self.db.get_user_clan(user.id)
        
        if not clan:
            await update.message.reply_text(
                "👥 Ты не состоишь в клане.\n"
                "Создать: /clan_create [название]\n"
                "Присоединиться: /clan_join [ID]"
            )
            return
        
        members = self.db.get_clan_members(clan[0])
        
        text = (
            f"👥 **КЛАН «{clan[1]}»**\n\n"
            f"📊 Уровень: {clan[3]}\n"
            f"✨ Опыт: {clan[4]}/{clan[3] * 500}\n"
            f"👤 Участников: {clan[5]}\n"
            f"⭐ Рейтинг: {clan[6]}\n\n"
            f"**Участники:**\n"
        )
        
        for member in members:
            role_emoji = "👑" if member[5] == 'owner' else "🛡" if member[5] == 'admin' else "👤"
            text += f"{role_emoji} {member[1]} (ур.{member[3]})\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_clan_create(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Укажи название: /clan_create Название")
            return
        
        name = " ".join(context.args)
        user = update.effective_user
        user_data = self.db.get_user(user.id, user.first_name, user.last_name or "")
        
        if len(name) > 30:
            await update.message.reply_text("❌ Название слишком длинное (макс 30 символов)")
            return
        
        if self.db.get_user_clan(user.id):
            await update.message.reply_text("❌ Ты уже в клане")
            return
        
        if user_data['level'] < 5:
            await update.message.reply_text("❌ Для создания клана нужен 5 уровень!")
            return
        
        if user_data['coins'] < 1000:
            await update.message.reply_text("❌ Для создания клана нужно 1000 🪙")
            return
        
        clan_id = self.db.create_clan(name, user.id)
        
        if clan_id:
            self.db.add_coins(user.id, -1000)
            await update.message.reply_text(f"✅ Клан «{name}» создан! ID: {clan_id}")
        else:
            await update.message.reply_text("❌ Клан с таким названием уже существует")
    
    async def cmd_clan_join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Укажи ID клана: /clan_join 1")
            return
        
        try:
            clan_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ Неправильный ID")
            return
        
        user = update.effective_user
        
        if self.db.get_user_clan(user.id):
            await update.message.reply_text("❌ Ты уже в клане")
            return
        
        clan = self.db.get_clan(clan_id)
        
        if not clan:
            await update.message.reply_text("❌ Клан не найден")
            return
        
        if clan[5] >= 50:
            await update.message.reply_text("❌ В клане нет мест (максимум 50)")
            return
        
        self.db.join_clan(user.id, clan_id)
        await update.message.reply_text(f"✅ Ты вступил в клан «{clan[1]}»!")
    
    async def cmd_clan_leave(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        clan = self.db.get_user_clan(user.id)
        
        if not clan:
            await update.message.reply_text("❌ Ты не в клане")
            return
        
        if clan[2] == user.id:
            await update.message.reply_text("❌ Владелец не может покинуть клан.")
            return
        
        self.db.leave_clan(user.id, clan[0])
        await update.message.reply_text("✅ Ты покинул клан")
    
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
        
        await update.message.reply_text(f"🔇 Пользователь {target_id} замучен на {minutes} минут\nПричина: {reason}")
        
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
    
    async def cmd_give(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Недостаточно прав")
            return
        
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /give [ID] [сумма]")
            return
        
        try:
            target_id = int(context.args[0])
            amount = int(context.args[1])
        except:
            await update.message.reply_text("❌ Неправильный формат")
            return
        
        self.db.add_coins(target_id, amount)
        await update.message.reply_text(f"✅ Пользователю {target_id} выдано {amount} 🪙")
        
        try:
            await context.bot.send_message(chat_id=target_id, text=f"💰 Вам начислено {amount} 🪙 от администрации!")
        except:
            pass
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        message_text = update.message.text
        
        if self.db.is_banned(user.id):
            await update.message.reply_text("🚫 Вы забанены в боте.")
            return
        
        if self.db.is_muted(user.id):
            remaining = self.db.get_mute_time(user.id)
            await update.message.reply_text(f"🔇 Вы замучены. Осталось: {remaining}")
            return
        
        if await self.check_spam(update):
            return
        
        # Получаем ответ от ИИ
        response = await self.ai.get_response(user.id, message_text)
        await update.message.reply_text(response, parse_mode='Markdown')
        
        self.db.add_exp(user.id, 1)
        self.db.add_stat(user.id, "messages_count")
    
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
