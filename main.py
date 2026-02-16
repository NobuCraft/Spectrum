import asyncio
import logging
import random
import sqlite3
import datetime
from typing import Optional, Dict, Any, List, Tuple
import aiohttp
import json
import os
import re
from collections import defaultdict
import time
import hashlib
import base64

# Для Telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# Для VK - исправленные импорты
from vkbottle import API, Bot
from vkbottle.bot import Message
from vkbottle_types.events import GroupEventType

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===================== КОНФИГУРАЦИЯ =====================
# Telegram
TELEGRAM_TOKEN = "8326390250:AAFuUVHZ6ucUtLy132Ep1pmteRr6tTk7u0Q"
OWNER_ID_TG = 1732658530
OWNER_USERNAME_TG = "@NobuCraft"

# VK
VK_TOKEN = "vk1.a.sl7q9qebmFwqxkdpMVJTQpLWUtLMsKYPvVInyidaBe1GwkuxkDewfvYss7AcGYPlbw817In-UDgILA38ltHafX3p-t0_xaNWPwXOPpwPezMqq89fx1y9ru6lyde_qFYtu-ll3J-1_vBPPCZ0fHyh4j8qxkiXWCVBgFKtkNhqukNIFTbWqMjX57iMIPbawIdYOr_ngdaXRuGXZAAxzffhbg"
OWNER_ID_VK = 713616259
GROUP_ID_VK = 196406092

# OpenRouter AI (для TG)
OPENROUTER_KEY = "sk-97ac1d0de1844c449852a5470cbcae35"

# Настройки
SPAM_LIMIT = 5
SPAM_WINDOW = 3
SPAM_MUTE_TIME = 120

# Привилегии и цены
PRIVILEGES = {
    "вип": {"price": 5000, "days": 30, "emoji": "🌟", "commands": ["/regen", "/boss_fight", "/daily_x2"]},
    "премиум": {"price": 15000, "days": 30, "emoji": "💎", "commands": ["/heal_all", "/boss_crit", "/daily_x3"]},
    "лорд": {"price": 30000, "days": 30, "emoji": "👑", "commands": ["/god_mode", "/boss_instant", "/daily_x5"]},
    "ультра": {"price": 50000, "days": 60, "emoji": "⚡", "commands": ["/super_attack", "/boss_double", "/daily_x7"]},
    "модератор": {"price": 0, "days": 0, "emoji": "🛡", "commands": ["/mute", "/warn", "/ban", "/unban"]},
    "оператор": {"price": 0, "days": 0, "emoji": "⚙️", "commands": ["/give", "/clear", "/set_rules"]},
    "анти-грифер": {"price": 0, "days": 0, "emoji": "🛑", "commands": ["/antigrief", "/protect", "/lockdown"]},
    "легенда": {"price": 100000, "days": 90, "emoji": "🏆", "commands": ["/legendary_skill", "/boss_legendary", "/daily_x10"]},
    "эврольд": {"price": 200000, "days": 180, "emoji": "🌌", "commands": ["/cosmic_power", "/boss_annihilate", "/daily_x15"]},
    "властелин": {"price": 500000, "days": 365, "emoji": "👾", "commands": ["/master_control", "/boss_wipe", "/daily_x20"]},
    "титан": {"price": 1000000, "days": 365, "emoji": "🗿", "commands": ["/titan_strike", "/boss_obliterate", "/daily_x25"]},
    "терминатор": {"price": 2000000, "days": 365, "emoji": "🤖", "commands": ["/terminate", "/boss_execute", "/daily_x30"]},
    "маг": {"price": 75000, "days": 60, "emoji": "🔮", "commands": ["/spell", "/magic_shield", "/daily_x8"]},
    "хелпер": {"price": 0, "days": 0, "emoji": "🤝", "commands": ["/help_users", "/guide", "/welcome"]},
    "создатель": {"price": 0, "days": 0, "emoji": "⭐", "commands": ["/all_commands", "/global_ban", "/system"]}
}

# Валюты
CURRENCIES = {
    "монеты": {"emoji": "🪙", "name": "Монеты"},
    "алмазы": {"emoji": "💎", "name": "Алмазы"},
    "кристаллы": {"emoji": "🔮", "name": "Кристаллы"},
    "черепки": {"emoji": "💀", "name": "Черепки (для русской рулетки)"}
}

# Боссы
BOSSES = [
    {"id": 1, "name": "🦟 Ядовитый комар", "level": 5, "health": 2780, "max_health": 2780, "damage": 34, "reward": 500, "image": ""},
    {"id": 2, "name": "🐉 Огненный дракон", "level": 10, "health": 5000, "max_health": 5000, "damage": 50, "reward": 1000, "image": ""},
    {"id": 3, "name": "❄️ Ледяной великан", "level": 15, "health": 8000, "max_health": 8000, "damage": 70, "reward": 1500, "image": ""},
    {"id": 4, "name": "⚔️ Темный рыцарь", "level": 20, "health": 12000, "max_health": 12000, "damage": 90, "reward": 2000, "image": ""},
    {"id": 5, "name": "👾 Король демонов", "level": 25, "health": 20000, "max_health": 20000, "damage": 120, "reward": 3000, "image": ""},
    {"id": 6, "name": "💀 Бог разрушения", "level": 30, "health": 30000, "max_health": 30000, "damage": 150, "reward": 5000, "image": ""},
    {"id": 7, "name": "🌌 Космический титан", "level": 35, "health": 50000, "max_health": 50000, "damage": 200, "reward": 10000, "image": ""},
]

# Магазин
SHOP_ITEMS = {
    "зелье_здоровья": {"name": "💊 Зелье здоровья", "price": 50, "currency": "монеты", "effect": "heal", "value": 30},
    "большое_зелье": {"name": "💊 Большое зелье", "price": 100, "currency": "монеты", "effect": "heal", "value": 70},
    "меч": {"name": "⚔️ Меч", "price": 200, "currency": "монеты", "effect": "damage", "value": 10},
    "легендарный_меч": {"name": "⚔️ Легендарный меч", "price": 500, "currency": "монеты", "effect": "damage", "value": 30},
    "щит": {"name": "🛡 Щит", "price": 150, "currency": "монеты", "effect": "armor", "value": 5},
    "доспехи": {"name": "🛡 Доспехи", "price": 400, "currency": "монеты", "effect": "armor", "value": 15},
    "энергетик": {"name": "⚡ Энергетик", "price": 30, "currency": "монеты", "effect": "energy", "value": 20},
    "батарейка": {"name": "🔋 Батарейка", "price": 80, "currency": "монеты", "effect": "energy", "value": 50},
    "алмаз": {"name": "💎 Алмаз", "price": 100, "currency": "монеты", "effect": "add_currency", "value": "алмазы", "amount": 1},
    "кристалл": {"name": "🔮 Кристалл", "price": 500, "currency": "монеты", "effect": "add_currency", "value": "кристаллы", "amount": 1},
}

# Оружие для боссов
BOSS_WEAPONS = {
    1: {"name": "🗡 Деревянный меч", "damage": 50, "price": 100, "currency": "монеты"},
    2: {"name": "⚔️ Стальной меч", "damage": 100, "price": 300, "currency": "монеты"},
    3: {"name": "🔥 Огненный меч", "damage": 200, "price": 800, "currency": "монеты"},
    4: {"name": "❄️ Ледяной клинок", "damage": 350, "price": 1500, "currency": "монеты"},
    5: {"name": "⚡ Громовой молот", "damage": 500, "price": 3000, "currency": "алмазы"},
    6: {"name": "💀 Коса смерти", "damage": 800, "price": 5000, "currency": "алмазы"},
    7: {"name": "🌌 Космический клинок", "damage": 1200, "price": 10000, "currency": "кристаллы"},
}

# ===================== БАЗА ДАННЫХ =====================
class Database:
    def __init__(self, db_name="spectrum_bot.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
        self.migrate_tables()
        self.init_data()
    
    def create_tables(self):
        # Пользователи
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT,
                platform_id TEXT UNIQUE,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                coins INTEGER DEFAULT 1000,
                diamonds INTEGER DEFAULT 0,
                crystals INTEGER DEFAULT 0,
                rr_money INTEGER DEFAULT 100,
                energy INTEGER DEFAULT 100,
                level INTEGER DEFAULT 1,
                exp INTEGER DEFAULT 0,
                role TEXT DEFAULT 'user',
                privilege TEXT DEFAULT 'user',
                privilege_until TIMESTAMP,
                warns INTEGER DEFAULT 0,
                mute_until TIMESTAMP,
                banned INTEGER DEFAULT 0,
                ban_reason TEXT,
                ban_date TIMESTAMP,
                banned_by INTEGER,
                health INTEGER DEFAULT 100,
                max_health INTEGER DEFAULT 100,
                armor INTEGER DEFAULT 0,
                damage INTEGER DEFAULT 10,
                boss_kills INTEGER DEFAULT 0,
                last_activity TIMESTAMP,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                regen_available TIMESTAMP,
                messages_count INTEGER DEFAULT 0,
                commands_used INTEGER DEFAULT 0,
                games_played INTEGER DEFAULT 0,
                reputation INTEGER DEFAULT 0,
                reputation_given INTEGER DEFAULT 0,
                bookmarks TEXT DEFAULT '[]',
                awards TEXT DEFAULT '[]',
                description TEXT DEFAULT ''
            )
        ''')
        
        # Баны
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS bans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT,
                platform_id TEXT,
                username TEXT,
                reason TEXT,
                banned_by INTEGER,
                banned_by_name TEXT,
                ban_date TIMESTAMP,
                ban_duration TEXT,
                ban_until TIMESTAMP,
                is_permanent INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # Муты
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS mutes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT,
                platform_id TEXT,
                username TEXT,
                reason TEXT,
                muted_by INTEGER,
                muted_by_name TEXT,
                mute_date TIMESTAMP,
                mute_duration TEXT,
                mute_until TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # Варны
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS warns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT,
                platform_id TEXT,
                username TEXT,
                reason TEXT,
                warned_by INTEGER,
                warned_by_name TEXT,
                warn_date TIMESTAMP,
                warn_count INTEGER DEFAULT 1
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
                boss_image TEXT,
                is_alive INTEGER DEFAULT 1,
                current_boss INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Транзакции
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_id TEXT,
                to_id TEXT,
                amount INTEGER,
                currency TEXT,
                reason TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Сообщения
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT,
                platform_id TEXT,
                message TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Закладки
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT,
                platform_id TEXT,
                description TEXT,
                message_link TEXT,
                message_text TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Награды
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS awards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT,
                platform_id TEXT,
                award_name TEXT,
                award_description TEXT,
                awarded_by INTEGER,
                awarded_by_name TEXT,
                award_date TIMESTAMP
            )
        ''')
        
        # Настройки групп
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS group_settings (
                chat_id TEXT PRIMARY KEY,
                platform TEXT,
                welcome_enabled INTEGER DEFAULT 1,
                welcome_message TEXT DEFAULT '🌟 Добро пожаловать, {user}!',
                goodbye_enabled INTEGER DEFAULT 1,
                goodbye_message TEXT DEFAULT '👋 Пока, {user}!',
                anti_spam INTEGER DEFAULT 1,
                auto_message_enabled INTEGER DEFAULT 0,
                auto_message_text TEXT DEFAULT '',
                auto_message_interval INTEGER DEFAULT 60,
                rules TEXT DEFAULT '',
                language TEXT DEFAULT 'ru'
            )
        ''')
        
        self.conn.commit()
    
    def migrate_tables(self):
        try:
            # Добавляем недостающие колонки
            columns_to_add = {
                'users': [
                    ('privilege', "ALTER TABLE users ADD COLUMN privilege TEXT DEFAULT 'user'"),
                    ('privilege_until', "ALTER TABLE users ADD COLUMN privilege_until TIMESTAMP"),
                    ('regen_available', "ALTER TABLE users ADD COLUMN regen_available TIMESTAMP"),
                    ('bookmarks', "ALTER TABLE users ADD COLUMN bookmarks TEXT DEFAULT '[]'"),
                    ('awards', "ALTER TABLE users ADD COLUMN awards TEXT DEFAULT '[]'"),
                    ('description', "ALTER TABLE users ADD COLUMN description TEXT DEFAULT ''"),
                ]
            }
            
            for table, columns in columns_to_add.items():
                self.cursor.execute(f"PRAGMA table_info({table})")
                existing = [col[1] for col in self.cursor.fetchall()]
                
                for col_name, sql in columns:
                    if col_name not in existing:
                        try:
                            self.cursor.execute(sql)
                            print(f"✅ Добавлена колонка {col_name} в {table}")
                        except Exception as e:
                            print(f"Ошибка добавления {col_name}: {e}")
            
            self.conn.commit()
        except Exception as e:
            print(f"Ошибка миграции: {e}")
    
    def init_data(self):
        # Инициализация боссов
        self.cursor.execute("SELECT COUNT(*) FROM bosses")
        count = self.cursor.fetchone()[0]
        
        if count == 0:
            for boss in BOSSES:
                self.cursor.execute('''
                    INSERT INTO bosses (boss_name, boss_level, boss_health, boss_max_health, boss_damage, boss_reward, boss_image)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (boss['name'], boss['level'], boss['health'], boss['max_health'], boss['damage'], boss['reward'], boss['image']))
            self.conn.commit()
            print("✅ Боссы инициализированы")
    
    def get_user(self, platform: str, platform_id: str, username: str = "", first_name: str = "", last_name: str = ""):
        self.cursor.execute(
            "SELECT * FROM users WHERE platform = ? AND platform_id = ?",
            (platform, platform_id)
        )
        user = self.cursor.fetchone()
        
        if not user:
            # Новый пользователь
            role = 'owner' if (platform == 'tg' and int(platform_id) == OWNER_ID_TG) or (platform == 'vk' and int(platform_id) == OWNER_ID_VK) else 'user'
            
            self.cursor.execute('''
                INSERT INTO users (platform, platform_id, username, first_name, last_name, role, first_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (platform, platform_id, username, first_name, last_name, role, datetime.datetime.now()))
            self.conn.commit()
            
            # Возвращаем нового пользователя
            return self.get_user(platform, platform_id, username, first_name, last_name)
        
        # Преобразуем в словарь
        columns = [description[0] for description in self.cursor.description]
        return dict(zip(columns, user))
    
    def update_activity(self, platform: str, platform_id: str):
        self.cursor.execute(
            "UPDATE users SET last_activity = ? WHERE platform = ? AND platform_id = ?",
            (datetime.datetime.now(), platform, platform_id)
        )
        self.conn.commit()
    
    def add_message_count(self, platform: str, platform_id: str):
        self.cursor.execute(
            "UPDATE users SET messages_count = messages_count + 1 WHERE platform = ? AND platform_id = ?",
            (platform, platform_id)
        )
        self.conn.commit()
    
    def add_command_count(self, platform: str, platform_id: str):
        self.cursor.execute(
            "UPDATE users SET commands_used = commands_used + 1 WHERE platform = ? AND platform_id = ?",
            (platform, platform_id)
        )
        self.conn.commit()
    
    def add_coins(self, platform: str, platform_id: str, amount: int, currency: str = "coins"):
        if currency == "coins":
            self.cursor.execute(
                "UPDATE users SET coins = coins + ? WHERE platform = ? AND platform_id = ?",
                (amount, platform, platform_id)
            )
        elif currency == "diamonds":
            self.cursor.execute(
                "UPDATE users SET diamonds = diamonds + ? WHERE platform = ? AND platform_id = ?",
                (amount, platform, platform_id)
            )
        elif currency == "crystals":
            self.cursor.execute(
                "UPDATE users SET crystals = crystals + ? WHERE platform = ? AND platform_id = ?",
                (amount, platform, platform_id)
            )
        elif currency == "rr_money":
            self.cursor.execute(
                "UPDATE users SET rr_money = rr_money + ? WHERE platform = ? AND platform_id = ?",
                (amount, platform, platform_id)
            )
        
        self.conn.commit()
    
    def transfer_money(self, from_platform: str, from_id: str, to_platform: str, to_id: str, amount: int, currency: str = "coins"):
        # Проверяем баланс
        from_user = self.get_user(from_platform, from_id)
        
        if currency == "coins" and from_user['coins'] < amount:
            return False, "Недостаточно монет"
        elif currency == "diamonds" and from_user['diamonds'] < amount:
            return False, "Недостаточно алмазов"
        
        # Снимаем у отправителя
        self.add_coins(from_platform, from_id, -amount, currency)
        
        # Добавляем получателю
        self.add_coins(to_platform, to_id, amount, currency)
        
        # Записываем транзакцию
        self.cursor.execute('''
            INSERT INTO transactions (from_id, to_id, amount, currency, reason)
            VALUES (?, ?, ?, ?, ?)
        ''', (f"{from_platform}:{from_id}", f"{to_platform}:{to_id}", amount, currency, "transfer"))
        self.conn.commit()
        
        return True, f"Переведено {amount} {CURRENCIES[currency]['emoji']}"
    
    def add_exp(self, platform: str, platform_id: str, exp: int):
        self.cursor.execute(
            "UPDATE users SET exp = exp + ? WHERE platform = ? AND platform_id = ?",
            (exp, platform, platform_id)
        )
        
        # Проверка на повышение уровня
        self.cursor.execute(
            "SELECT exp, level FROM users WHERE platform = ? AND platform_id = ?",
            (platform, platform_id)
        )
        user = self.cursor.fetchone()
        
        if user:
            exp_needed = user[1] * 100
            if user[0] >= exp_needed:
                self.cursor.execute(
                    "UPDATE users SET level = level + 1, exp = exp - ? WHERE platform = ? AND platform_id = ?",
                    (exp_needed, platform, platform_id)
                )
        
        self.conn.commit()
    
    def damage_user(self, platform: str, platform_id: str, damage: int):
        self.cursor.execute(
            "UPDATE users SET health = health - ? WHERE platform = ? AND platform_id = ?",
            (damage, platform, platform_id)
        )
        
        # Проверка на смерть
        self.cursor.execute(
            "SELECT health FROM users WHERE platform = ? AND platform_id = ?",
            (platform, platform_id)
        )
        health = self.cursor.fetchone()[0]
        
        if health <= 0:
            self.cursor.execute(
                "UPDATE users SET health = max_health WHERE platform = ? AND platform_id = ?",
                (platform, platform_id)
            )
        
        self.conn.commit()
        return health > 0
    
    def heal_user(self, platform: str, platform_id: str, amount: int):
        self.cursor.execute(
            "UPDATE users SET health = health + ? WHERE platform = ? AND platform_id = ?",
            (amount, platform, platform_id)
        )
        
        # Не превышаем максимум
        self.cursor.execute(
            "UPDATE users SET health = max_health WHERE health > max_health AND platform = ? AND platform_id = ?",
            (platform, platform_id)
        )
        
        self.conn.commit()
    
    def regen_available(self, platform: str, platform_id: str) -> bool:
        self.cursor.execute(
            "SELECT regen_available FROM users WHERE platform = ? AND platform_id = ?",
            (platform, platform_id)
        )
        result = self.cursor.fetchone()
        
        if result and result[0]:
            regen_time = datetime.datetime.fromisoformat(result[0])
            return datetime.datetime.now() >= regen_time
        return True
    
    def use_regen(self, platform: str, platform_id: str, cooldown_minutes: int = 5):
        regen_until = datetime.datetime.now() + datetime.timedelta(minutes=cooldown_minutes)
        self.cursor.execute(
            "UPDATE users SET regen_available = ? WHERE platform = ? AND platform_id = ?",
            (regen_until, platform, platform_id)
        )
        self.conn.commit()
    
    def get_boss(self) -> dict:
        self.cursor.execute("SELECT * FROM bosses WHERE is_alive = 1 ORDER BY id LIMIT 1")
        boss = self.cursor.fetchone()
        
        if not boss:
            # Возрождаем боссов
            self.cursor.execute("UPDATE bosses SET is_alive = 1, boss_health = boss_max_health")
            self.conn.commit()
            return self.get_boss()
        
        columns = [description[0] for description in self.cursor.description]
        return dict(zip(columns, boss))
    
    def damage_boss(self, boss_id: int, damage: int) -> Tuple[bool, int]:
        self.cursor.execute("UPDATE bosses SET boss_health = boss_health - ? WHERE id = ?", (damage, boss_id))
        self.conn.commit()
        
        self.cursor.execute("SELECT boss_health FROM bosses WHERE id = ?", (boss_id,))
        health = self.cursor.fetchone()[0]
        
        if health <= 0:
            self.cursor.execute("UPDATE bosses SET is_alive = 0 WHERE id = ?", (boss_id,))
            self.conn.commit()
            return True, 0
        
        return False, health
    
    def get_next_boss(self) -> Optional[dict]:
        self.cursor.execute("SELECT * FROM bosses WHERE is_alive = 1 ORDER BY id LIMIT 1")
        boss = self.cursor.fetchone()
        
        if boss:
            columns = [description[0] for description in self.cursor.description]
            return dict(zip(columns, boss))
        return None
    
    def add_boss_kill(self, platform: str, platform_id: str):
        self.cursor.execute(
            "UPDATE users SET boss_kills = boss_kills + 1 WHERE platform = ? AND platform_id = ?",
            (platform, platform_id)
        )
        self.conn.commit()
    
    def get_player_count(self) -> int:
        self.cursor.execute("SELECT COUNT(*) FROM users WHERE last_activity > ?", 
                           (datetime.datetime.now() - datetime.timedelta(days=7),))
        return self.cursor.fetchone()[0]
    
    def get_top(self, by: str = "coins", limit: int = 10):
        self.cursor.execute(f"SELECT username, first_name, {by} FROM users ORDER BY {by} DESC LIMIT ?", (limit,))
        return self.cursor.fetchall()
    
    def get_user_by_username(self, platform: str, username: str):
        self.cursor.execute(
            "SELECT * FROM users WHERE platform = ? AND (username LIKE ? OR first_name LIKE ?)",
            (platform, f"%{username}%", f"%{username}%")
        )
        return self.cursor.fetchone()
    
    def add_bookmark(self, platform: str, platform_id: str, description: str, message_link: str, message_text: str):
        self.cursor.execute('''
            INSERT INTO bookmarks (platform, platform_id, description, message_link, message_text)
            VALUES (?, ?, ?, ?, ?)
        ''', (platform, platform_id, description, message_link, message_text))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_bookmarks(self, platform: str, platform_id: str):
        self.cursor.execute(
            "SELECT * FROM bookmarks WHERE platform = ? AND platform_id = ? ORDER BY timestamp DESC",
            (platform, platform_id)
        )
        return self.cursor.fetchall()
    
    def add_award(self, platform: str, platform_id: str, award_name: str, award_description: str, awarded_by: int, awarded_by_name: str):
        self.cursor.execute('''
            INSERT INTO awards (platform, platform_id, award_name, award_description, awarded_by, awarded_by_name, award_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (platform, platform_id, award_name, award_description, awarded_by, awarded_by_name, datetime.datetime.now()))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_awards(self, platform: str, platform_id: str):
        self.cursor.execute(
            "SELECT * FROM awards WHERE platform = ? AND platform_id = ? ORDER BY award_date DESC",
            (platform, platform_id)
        )
        return self.cursor.fetchall()
    
    def set_description(self, platform: str, platform_id: str, description: str):
        self.cursor.execute(
            "UPDATE users SET description = ? WHERE platform = ? AND platform_id = ?",
            (description, platform, platform_id)
        )
        self.conn.commit()
    
    def is_muted(self, platform: str, platform_id: str) -> bool:
        self.cursor.execute(
            "SELECT mute_until FROM users WHERE platform = ? AND platform_id = ?",
            (platform, platform_id)
        )
        result = self.cursor.fetchone()
        if result and result[0]:
            mute_until = datetime.datetime.fromisoformat(result[0])
            return datetime.datetime.now() < mute_until
        return False
    
    def mute_user(self, platform: str, platform_id: str, username: str, minutes: int, reason: str, muted_by: int, muted_by_name: str):
        mute_until = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
        
        # Обновляем в users
        self.cursor.execute(
            "UPDATE users SET mute_until = ? WHERE platform = ? AND platform_id = ?",
            (mute_until, platform, platform_id)
        )
        
        # Добавляем запись в mutes
        duration = f"{minutes} мин" if minutes < 60 else f"{minutes//60} ч" if minutes < 1440 else f"{minutes//1440} д"
        self.cursor.execute('''
            INSERT INTO mutes (platform, platform_id, username, reason, muted_by, muted_by_name, mute_date, mute_duration, mute_until, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (platform, platform_id, username, reason, muted_by, muted_by_name, datetime.datetime.now(), duration, mute_until, 1))
        
        self.conn.commit()
        return mute_until
    
    def unmute_user(self, platform: str, platform_id: str):
        self.cursor.execute(
            "UPDATE users SET mute_until = NULL WHERE platform = ? AND platform_id = ?",
            (platform, platform_id)
        )
        self.cursor.execute(
            "UPDATE mutes SET is_active = 0 WHERE platform = ? AND platform_id = ? AND is_active = 1",
            (platform, platform_id)
        )
        self.conn.commit()
    
    def add_warn(self, platform: str, platform_id: str, username: str, reason: str, warned_by: int, warned_by_name: str):
        self.cursor.execute(
            "UPDATE users SET warns = warns + 1 WHERE platform = ? AND platform_id = ?",
            (platform, platform_id)
        )
        
        self.cursor.execute('''
            INSERT INTO warns (platform, platform_id, username, reason, warned_by, warned_by_name, warn_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (platform, platform_id, username, reason, warned_by, warned_by_name, datetime.datetime.now()))
        
        self.conn.commit()
        
        # Проверяем количество варнов
        self.cursor.execute(
            "SELECT warns FROM users WHERE platform = ? AND platform_id = ?",
            (platform, platform_id)
        )
        warns = self.cursor.fetchone()[0]
        
        return warns
    
    def ban_user(self, platform: str, platform_id: str, username: str, reason: str, duration: str, banned_by: int, banned_by_name: str):
        is_permanent = duration.lower() == "навсегда"
        ban_until = None
        
        if not is_permanent:
            # Парсим длительность
            match = re.match(r'(\d+)\s*([дчм])', duration.lower())
            if match:
                value = int(match.group(1))
                unit = match.group(2)
                if unit == 'д':
                    ban_until = datetime.datetime.now() + datetime.timedelta(days=value)
                elif unit == 'ч':
                    ban_until = datetime.datetime.now() + datetime.timedelta(hours=value)
                elif unit == 'м':
                    ban_until = datetime.datetime.now() + datetime.timedelta(minutes=value)
            else:
                ban_until = datetime.datetime.now() + datetime.timedelta(days=365)
        
        # Обновляем в users
        self.cursor.execute(
            "UPDATE users SET banned = 1, ban_reason = ?, ban_date = ?, banned_by = ? WHERE platform = ? AND platform_id = ?",
            (reason, datetime.datetime.now(), banned_by, platform, platform_id)
        )
        
        # Добавляем запись в bans
        self.cursor.execute('''
            INSERT INTO bans (platform, platform_id, username, reason, banned_by, banned_by_name, ban_date, ban_duration, ban_until, is_permanent, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (platform, platform_id, username, reason, banned_by, banned_by_name, datetime.datetime.now(), duration, ban_until, 1 if is_permanent else 0, 1))
        
        self.conn.commit()
        return True
    
    def unban_user(self, platform: str, platform_id: str):
        self.cursor.execute(
            "UPDATE users SET banned = 0, ban_reason = NULL WHERE platform = ? AND platform_id = ?",
            (platform, platform_id)
        )
        self.cursor.execute(
            "UPDATE bans SET is_active = 0 WHERE platform = ? AND platform_id = ? AND is_active = 1",
            (platform, platform_id)
        )
        self.conn.commit()
    
    def is_banned(self, platform: str, platform_id: str) -> bool:
        self.cursor.execute(
            "SELECT banned FROM users WHERE platform = ? AND platform_id = ?",
            (platform, platform_id)
        )
        result = self.cursor.fetchone()
        return result and result[0] == 1
    
    def get_banned_users(self, page: int = 1, per_page: int = 20):
        offset = (page - 1) * per_page
        self.cursor.execute('''
            SELECT * FROM bans WHERE is_active = 1 ORDER BY ban_date DESC LIMIT ? OFFSET ?
        ''', (per_page, offset))
        return self.cursor.fetchall()
    
    def get_muted_users(self, page: int = 1, per_page: int = 20):
        offset = (page - 1) * per_page
        self.cursor.execute('''
            SELECT * FROM mutes WHERE is_active = 1 ORDER BY mute_date DESC LIMIT ? OFFSET ?
        ''', (per_page, offset))
        return self.cursor.fetchall()
    
    def get_warned_users(self, page: int = 1, per_page: int = 20):
        offset = (page - 1) * per_page
        self.cursor.execute('''
            SELECT * FROM warns ORDER BY warn_date DESC LIMIT ? OFFSET ?
        ''', (per_page, offset))
        return self.cursor.fetchall()
    
    def has_privilege(self, platform: str, platform_id: str, privilege: str) -> bool:
        if privilege == "создатель" and int(platform_id) in [OWNER_ID_TG, OWNER_ID_VK]:
            return True
        
        self.cursor.execute(
            "SELECT role, privilege, privilege_until FROM users WHERE platform = ? AND platform_id = ?",
            (platform, platform_id)
        )
        user = self.cursor.fetchone()
        
        if not user:
            return False
        
        role, priv, until = user
        
        # Проверяем роль
        if role in ['owner', 'admin']:
            return True
        
        # Проверяем привилегию
        if priv == privilege and until:
            until_time = datetime.datetime.fromisoformat(until)
            if datetime.datetime.now() < until_time:
                return True
        
        return False
    
    def set_privilege(self, platform: str, platform_id: str, privilege: str, days: int):
        until = datetime.datetime.now() + datetime.timedelta(days=days) if days > 0 else None
        self.cursor.execute(
            "UPDATE users SET privilege = ?, privilege_until = ? WHERE platform = ? AND platform_id = ?",
            (privilege, until, platform, platform_id)
        )
        self.conn.commit()
    
    def close(self):
        self.conn.close()

# ===================== ИНИЦИАЛИЗАЦИЯ БАЗЫ =====================
db = Database()

# ===================== ОСНОВНОЙ КЛАСС БОТА =====================
class GameBot:
    def __init__(self):
        self.db = db
        self.tg_application = None
        self.vk_bot = None
        self.vk_api = None
        self.last_activity = defaultdict(dict)
        
        # Инициализация Telegram
        if TELEGRAM_TOKEN:
            self.tg_application = Application.builder().token(TELEGRAM_TOKEN).build()
            self.setup_tg_handlers()
            logger.info("✅ Telegram бот инициализирован")
        
        # Инициализация VK
        if VK_TOKEN:
            self.vk_bot = Bot(VK_TOKEN)
            self.vk_api = API(VK_TOKEN)
            self.setup_vk_handlers()
            logger.info("✅ VK бот инициализирован")
    
    # ===================== TELEGRAM ОБРАБОТЧИКИ =====================
    def setup_tg_handlers(self):
        # Основные
        self.tg_application.add_handler(CommandHandler("start", self.tg_cmd_start))
        self.tg_application.add_handler(CommandHandler("menu", self.tg_cmd_menu))
        self.tg_application.add_handler(CommandHandler("help", self.tg_cmd_help))
        
        # Профиль и статистика
        self.tg_application.add_handler(CommandHandler("profile", self.tg_cmd_profile))
        self.tg_application.add_handler(CommandHandler("top", self.tg_cmd_top))
        self.tg_application.add_handler(CommandHandler("players", self.tg_cmd_players))
        
        # Боссы
        self.tg_application.add_handler(CommandHandler("boss", self.tg_cmd_boss))
        self.tg_application.add_handler(CommandHandler("boss_fight", self.tg_cmd_boss_fight))
        self.tg_application.add_handler(CommandHandler("regen", self.tg_cmd_regen))
        self.tg_application.add_handler(CommandHandler("shop", self.tg_cmd_shop))
        
        # Экономика
        self.tg_application.add_handler(CommandHandler("payd", self.tg_cmd_pay_d))
        self.tg_application.add_handler(CommandHandler("payh", self.tg_cmd_pay_h))
        
        # Команды
        self.tg_application.add_handler(CommandHandler("cmd", self.tg_cmd_privilege_commands))
        self.tg_application.add_handler(CommandHandler("donate", self.tg_cmd_donate))
        self.tg_application.add_handler(CommandHandler("rules", self.tg_cmd_rules))
        self.tg_application.add_handler(CommandHandler("set_rules", self.tg_cmd_set_rules))
        
        # Админские
        self.tg_application.add_handler(CommandHandler("mute", self.tg_cmd_mute))
        self.tg_application.add_handler(CommandHandler("unmute", self.tg_cmd_unmute))
        self.tg_application.add_handler(CommandHandler("warn", self.tg_cmd_warn))
        self.tg_application.add_handler(CommandHandler("ban", self.tg_cmd_ban))
        self.tg_application.add_handler(CommandHandler("unban", self.tg_cmd_unban))
        self.tg_application.add_handler(CommandHandler("banlist", self.tg_cmd_banlist))
        self.tg_application.add_handler(CommandHandler("mutelist", self.tg_cmd_mutelist))
        self.tg_application.add_handler(CommandHandler("warnlist", self.tg_cmd_warnlist))
        
        # Интерактивные кнопки
        self.tg_application.add_handler(CallbackQueryHandler(self.tg_button_callback))
        
        # Обработка сообщений
        self.tg_application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.tg_handle_message))
        
        # Обработка новых участников
        self.tg_application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, self.tg_handle_new_members))
        
        logger.info("✅ Telegram обработчики зарегистрированы")
    
    async def tg_cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    platform_id = str(user.id)
    
    # Получаем или создаем пользователя
    db.get_user('tg', platform_id, user.username or "", user.first_name, user.last_name or "")
    db.update_activity('tg', platform_id)
    db.add_command_count('tg', platform_id)
    
    text = (
        f"╔══════════════════════════════╗\n"
        f"║   ⚔️ **СПЕКТР БОТ** ⚔️       ║\n"
        f"╚══════════════════════════════╝\n\n"
        f"🌟 **Привет, {user.first_name}!**\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"**ОСНОВНЫЕ КОМАНДЫ**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 /profile - твой профиль\n"
        f"👾 /boss - битва с боссом\n"
        f"💰 /shop - магазин\n"
        f"💎 /donate - привилегии\n"
        f"📊 /top - топ игроков\n"
        f"👥 /players - онлайн\n"
        f"📚 /help - все команды\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 Владелец: {OWNER_USERNAME_TG}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━"
    )
    
    keyboard = [
        [InlineKeyboardButton("👤 Профиль", callback_data="profile"),
         InlineKeyboardButton("👾 Босс", callback_data="boss")],
        [InlineKeyboardButton("💰 Магазин", callback_data="shop"),
         InlineKeyboardButton("💎 Привилегии", callback_data="donate")],
        [InlineKeyboardButton("📊 Топ", callback_data="top"),
         InlineKeyboardButton("👥 Онлайн", callback_data="players")],
        [InlineKeyboardButton("📚 Команды", callback_data="help"),
         InlineKeyboardButton("📖 Правила", callback_data="rules")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def tg_cmd_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    platform_id = str(user.id)
    db.update_activity('tg', platform_id)
    db.add_command_count('tg', platform_id)
    
    keyboard = [
        [InlineKeyboardButton("👤 Профиль", callback_data="profile"),
         InlineKeyboardButton("👾 Босс", callback_data="boss")],
        [InlineKeyboardButton("💰 Магазин", callback_data="shop"),
         InlineKeyboardButton("💎 Привилегии", callback_data="donate")],
        [InlineKeyboardButton("📊 Топ", callback_data="top"),
         InlineKeyboardButton("👥 Онлайн", callback_data="players")],
        [InlineKeyboardButton("📚 Команды", callback_data="help"),
         InlineKeyboardButton("📖 Правила", callback_data="rules")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🎮 **ГЛАВНОЕ МЕНЮ**\n\nВыберите раздел:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    async def tg_cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        db.update_activity('tg', platform_id)
        db.add_command_count('tg', platform_id)
        
        text = (
            "📚 **ВСЕ КОМАНДЫ БОТА**\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**ОСНОВНЫЕ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/start - запуск бота\n"
            "/menu - главное меню\n"
            "/help - эта справка\n"
            "/profile - твой профиль\n"
            "/player [ник] - профиль игрока\n"
            "/top - топ игроков\n"
            "/players - количество игроков\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**БИТВА С БОССОМ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/boss - информация о боссе\n"
            "/boss_fight - ударить босса\n"
            "/regen - восстановить здоровье\n"
            "/shop 3 - магазин оружия\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**ЭКОНОМИКА**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/shop - магазин\n"
            "/payd [ник] [сумма] - перевести монеты\n"
            "/payh [ник] [сумма] - перевести алмазы\n"
            "/donate - привилегии\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**КОМАНДЫ ПРИВИЛЕГИЙ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/cmd [привилегия] - команды доната\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**АДМИН-КОМАНДЫ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/mute [ник] [время] [причина] - мут\n"
            "/unmute [ник] - снять мут\n"
            "/warn [ник] [причина] - предупреждение\n"
            "/ban [ник] [время] [причина] - бан\n"
            "/unban [ник] - разбан\n"
            "/banlist - список банов\n"
            "/mutelist - список мутов\n"
            "/warnlist - список варнов\n"
            "/set_rules [текст] - установить правила\n"
            "/rules - показать правила\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**ДРУГОЕ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/sms [ник] [текст] - личное сообщение\n"
            "/eng free - получить бесплатную энергию\n"
            "/namutebuy - снять мут за монеты\n"
            "/automes on/off - автосообщение"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def tg_cmd_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        
        user_data = db.get_user('tg', platform_id, user.username or "", user.first_name, user.last_name or "")
        db.update_activity('tg', platform_id)
        db.add_command_count('tg', platform_id)
        
        # Проверка на бан
        if db.is_banned('tg', platform_id):
            await update.message.reply_text("🚫 Вы забанены в боте.")
            return
        
        # Проверка на мут
        if db.is_muted('tg', platform_id):
            await update.message.reply_text("🔇 Вы замучены.")
            return
        
        # Получаем привилегию
        privilege = user_data.get('privilege', 'user')
        privilege_emoji = PRIVILEGES.get(privilege, {}).get('emoji', '👤') if privilege != 'user' else '👤'
        
        # Получаем последнюю активность
        last_activity = "Неизвестно"
        if user_data.get('last_activity'):
            last = datetime.datetime.fromisoformat(user_data['last_activity'])
            delta = datetime.datetime.now() - last
            if delta.days > 0:
                last_activity = f"{delta.days} дн назад"
            elif delta.seconds > 3600:
                last_activity = f"{delta.seconds // 3600} ч назад"
            elif delta.seconds > 60:
                last_activity = f"{delta.seconds // 60} мин назад"
            else:
                last_activity = "только что"
        
        text = (
            f"╔══════════════════════════════╗\n"
            f"║   👤 **ПРОФИЛЬ ИГРОКА**      ║\n"
            f"╚══════════════════════════════╝\n\n"
            
            f"**{user.first_name}** {privilege_emoji}\n"
            f"ID: {user.id}\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**РЕСУРСЫ**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🪙 Монеты: {user_data['coins']:,}\n"
            f"💎 Алмазы: {user_data['diamonds']:,}\n"
            f"🔮 Кристаллы: {user_data['crystals']:,}\n"
            f"💀 Черепки: {user_data['rr_money']}\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**ХАРАКТЕРИСТИКИ**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"❤️ Здоровье: {user_data['health']}/{user_data['max_health']}\n"
            f"⚔️ Урон: {user_data['damage']}\n"
            f"🛡 Броня: {user_data['armor']}\n"
            f"⚡ Энергия: {user_data['energy']}\n"
            f"📊 Уровень: {user_data['level']}\n"
            f"✨ Опыт: {user_data['exp']}/{user_data['level'] * 100}\n"
            f"👾 Боссов убито: {user_data['boss_kills']}\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**СТАТИСТИКА**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📝 Сообщений: {user_data['messages_count']}\n"
            f"⌨️ Команд: {user_data['commands_used']}\n"
            f"🎮 Игр: {user_data['games_played']}\n"
            f"⭐ Репутация: {user_data['reputation']}\n"
            f"⏱ Последний визит: {last_activity}\n"
            f"📅 Первое появление: {user_data['first_seen'][:10] if user_data['first_seen'] else 'Неизвестно'}"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="menu_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def tg_cmd_boss(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        
        user_data = db.get_user('tg', platform_id, user.username or "", user.first_name, user.last_name or "")
        db.update_activity('tg', platform_id)
        db.add_command_count('tg', platform_id)
        
        boss = db.get_boss()
        
        if not boss:
            await update.message.reply_text("👾 Все боссы повержены! Ожидайте возрождения...")
            return
        
        # Рассчитываем урон игрока с учетом бонусов
        player_damage = user_data['damage'] * (user_data['level'] / 10 + 1)
        
        text = (
            f"╔══════════════════════════════╗\n"
            f"║   👾 **БИТВА С БОССОМ**      ║\n"
            f"╚══════════════════════════════╝\n\n"
            
            f"**{boss['boss_name']}**\n"
            f"Уровень: {boss['boss_level']}\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**ХАРАКТЕРИСТИКИ**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💀 Здоровье: {boss['boss_health']} / {boss['boss_max_health']} HP\n"
            f"⚔️ Урон босса: {boss['boss_damage']} HP\n"
            f"💰 Награда: {boss['boss_reward']} 🪙\n\n"
            
            f"**ТВОИ ХАРАКТЕРИСТИКИ**\n"
            f"❤️ Твое здоровье: {user_data['health']} HP\n"
            f"🗡 Твой урон: {player_damage:.1f} ({user_data['damage']} базовый)\n"
            f"📊 Уровень силы: {((player_damage / boss['boss_damage']) * 100):.1f}%\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**ДЕЙСТВИЯ**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👊 /boss_fight - ударить босса\n"
            f"➕ /regen - регенерация здоровья\n"
            f"🗡 /shop 3 - магазин оружия"
        )
        
        keyboard = [
            [InlineKeyboardButton("👊 Ударить", callback_data="boss_fight"),
             InlineKeyboardButton("➕ Регенерация", callback_data="regen")],
            [InlineKeyboardButton("🗡 Магазин оружия", callback_data="boss_shop"),
             InlineKeyboardButton("🔙 Назад", callback_data="menu_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def tg_cmd_boss_fight(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        
        user_data = db.get_user('tg', platform_id, user.username or "", user.first_name, user.last_name or "")
        db.update_activity('tg', platform_id)
        db.add_command_count('tg', platform_id)
        
        boss = db.get_boss()
        
        if not boss:
            await update.message.reply_text("👾 Все боссы повержены! Ожидайте возрождения...")
            return
        
        if user_data['health'] <= 0:
            await update.message.reply_text("💀 У вас нет здоровья! Используйте /regen")
            return
        
        if user_data['energy'] < 5:
            await update.message.reply_text("⚡ Недостаточно энергии! Нужно 5 ⚡")
            return
        
        # Расход энергии
        db.add_coins('tg', platform_id, -5, "energy")
        
        # Рассчитываем урон игрока
        player_damage = user_data['damage'] * (1 + user_data['level'] * 0.1)
        
        # Бонусы за привилегии
        if db.has_privilege('tg', platform_id, "премиум"):
            player_damage *= 1.5
        elif db.has_privilege('tg', platform_id, "вип"):
            player_damage *= 1.2
        elif db.has_privilege('tg', platform_id, "лорд"):
            player_damage *= 2.0
        
        player_damage = int(player_damage)
        boss_damage = boss['boss_damage']
        
        # Урон по боссу
        killed, health_left = db.damage_boss(boss['id'], player_damage)
        
        # Урон по игроку
        db.damage_user('tg', platform_id, boss_damage)
        
        text = f"⚔️ **БИТВА С БОССОМ** ⚔️\n\n"
        text += f"**{boss['boss_name']}**\n\n"
        text += f"▫️ **Твой урон:** {player_damage} HP\n"
        text += f"▫️ **Урон босса:** {boss_damage} HP\n\n"
        
        if killed:
            # Босс побежден
            reward = boss['boss_reward']
            
            # Бонусы за привилегии
            if db.has_privilege('tg', platform_id, "премиум"):
                reward = int(reward * 2)
            elif db.has_privilege('tg', platform_id, "вип"):
                reward = int(reward * 1.5)
            
            db.add_coins('tg', platform_id, reward, "coins")
            db.add_boss_kill('tg', platform_id)
            db.add_exp('tg', platform_id, boss['boss_level'] * 10)
            
            next_boss = db.get_next_boss()
            
            text += f"🎉 **БОСС ПОВЕРЖЕН!**\n"
            text += f"💰 **Награда:** {reward} 🪙\n"
            text += f"✨ **Опыт:** +{boss['boss_level'] * 10}\n\n"
            
            if next_boss:
                text += f"👾 **Следующий босс:** {next_boss['boss_name']}"
            else:
                text += f"👾 **Все боссы побеждены!** Ожидайте возрождения..."
        else:
            text += f"👾 **Босс еще жив!**\n"
            text += f"💀 **Осталось:** {health_left} HP\n\n"
        
        # Проверка здоровья игрока
        user_data = db.get_user('tg', platform_id)
        if user_data['health'] <= 0:
            text += f"💀 **Ты погиб в бою!** Используй /regen для восстановления."
        
        keyboard = [
            [InlineKeyboardButton("👊 Еще удар", callback_data="boss_fight"),
             InlineKeyboardButton("➕ Регенерация", callback_data="regen")],
            [InlineKeyboardButton("🔙 К боссу", callback_data="boss")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def tg_cmd_regen(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        
        user_data = db.get_user('tg', platform_id, user.username or "", user.first_name, user.last_name or "")
        db.update_activity('tg', platform_id)
        db.add_command_count('tg', platform_id)
        
        # Проверяем доступность регенерации
        if not db.regen_available('tg', platform_id):
            await update.message.reply_text("❌ Регенерация еще не доступна! Подождите немного.")
            return
        
        # Восстанавливаем здоровье
        if user_data['health'] < user_data['max_health']:
            heal_amount = user_data['max_health'] - user_data['health']
            db.heal_user('tg', platform_id, heal_amount)
            
            # Устанавливаем кулдаун
            cooldown = 1 if db.has_privilege('tg', platform_id, "премиум") else 3 if db.has_privilege('tg', platform_id, "вип") else 5
            db.use_regen('tg', platform_id, cooldown)
            
            await update.message.reply_text(
                f"➕ **РЕГЕНЕРАЦИЯ**\n\n"
                f"❤️ Здоровье восстановлено!\n"
                f"Текущее здоровье: {user_data['max_health']}/{user_data['max_health']}\n\n"
                f"⏱ Следующая регенерация через {cooldown} мин."
            )
        else:
            await update.message.reply_text("❤️ У тебя уже полное здоровье!")
    
    async def tg_cmd_shop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        
        db.update_activity('tg', platform_id)
        db.add_command_count('tg', platform_id)
        
        # Проверяем, есть ли аргумент для магазина оружия
        if context.args and context.args[0] == "3":
            # Магазин оружия для боссов
            text = "🗡 **МАГАЗИН ОРУЖИЯ**\n\n"
            
            for weapon_id, weapon in BOSS_WEAPONS.items():
                currency_emoji = CURRENCIES.get(weapon['currency'], {}).get('emoji', '🪙')
                text += f"**{weapon_id}. {weapon['name']}**\n"
                text += f"└ ⚔️ Урон: +{weapon['damage']}\n"
                text += f"└ 💰 Цена: {weapon['price']} {currency_emoji}\n\n"
            
            text += "Купить: /buy_weapon [номер]"
            
            keyboard = []
            for i in range(1, len(BOSS_WEAPONS) + 1, 3):
                row = []
                for j in range(3):
                    if i + j <= len(BOSS_WEAPONS):
                        row.append(InlineKeyboardButton(f"{i+j}", callback_data=f"buy_weapon_{i+j}"))
                keyboard.append(row)
            
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="boss")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
            return
        
        # Основной магазин
        text = (
            "💰 **МАГАЗИН «СПЕКТР»**\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "💊 **ЗЕЛЬЯ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ Зелье здоровья — 50 🪙 (❤️+30)\n"
            "▫️ Большое зелье — 100 🪙 (❤️+70)\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚔️ **ОРУЖИЕ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ Меч — 200 🪙 (⚔️+10)\n"
            "▫️ Легендарный меч — 500 🪙 (⚔️+30)\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🛡 **БРОНЯ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ Щит — 150 🪙 (🛡+5)\n"
            "▫️ Доспехи — 400 🪙 (🛡+15)\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚡ **ЭНЕРГИЯ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ Энергетик — 30 🪙 (⚡+20)\n"
            "▫️ Батарейка — 80 🪙 (⚡+50)\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "💎 **ВАЛЮТА**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ Алмаз — 100 🪙 (💎+1)\n"
            "▫️ Кристалл — 500 🪙 (🔮+1)\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🗡 **ОРУЖИЕ ДЛЯ БОССОВ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ /shop 3 - магазин оружия\n\n"
            
            "🛒 Купить: /buy [название]"
        )
        
        keyboard = [
            [InlineKeyboardButton("💊 Зелья", callback_data="buy_potions"),
             InlineKeyboardButton("⚔️ Оружие", callback_data="buy_weapons")],
            [InlineKeyboardButton("🛡 Броня", callback_data="buy_armor"),
             InlineKeyboardButton("⚡ Энергия", callback_data="buy_energy")],
            [InlineKeyboardButton("🗡 Оружие боссов", callback_data="boss_shop"),
             InlineKeyboardButton("🔙 Назад", callback_data="menu_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def tg_cmd_pay_d(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /payd [ник] [сумма]")
            return
        
        target_name = context.args[0]
        try:
            amount = int(context.args[1])
        except:
            await update.message.reply_text("❌ Сумма должна быть числом")
            return
        
        user = update.effective_user
        platform_id = str(user.id)
        
        user_data = db.get_user('tg', platform_id)
        db.update_activity('tg', platform_id)
        db.add_command_count('tg', platform_id)
        
        if amount <= 0:
            await update.message.reply_text("❌ Сумма должна быть положительной")
            return
        
        if user_data['coins'] < amount:
            await update.message.reply_text(f"❌ Недостаточно монет! У вас {user_data['coins']} 🪙")
            return
        
        # Ищем получателя
        target_user = db.get_user_by_username('tg', target_name)
        
        if not target_user:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        target_id = target_user[2]  # platform_id
        
        # Переводим монеты
        success, message = db.transfer_money('tg', platform_id, 'tg', target_id, amount, "coins")
        
        if success:
            await update.message.reply_text(f"✅ {message}\nПолучатель: {target_user[4]}")
            
            # Уведомляем получателя
            try:
                await context.bot.send_message(
                    chat_id=int(target_id),
                    text=f"💰 {user.first_name} перевел вам {amount} 🪙!"
                )
            except:
                pass
        else:
            await update.message.reply_text(f"❌ {message}")
    
    async def tg_cmd_pay_h(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /payh [ник] [сумма]")
            return
        
        target_name = context.args[0]
        try:
            amount = int(context.args[1])
        except:
            await update.message.reply_text("❌ Сумма должна быть числом")
            return
        
        user = update.effective_user
        platform_id = str(user.id)
        
        user_data = db.get_user('tg', platform_id)
        db.update_activity('tg', platform_id)
        db.add_command_count('tg', platform_id)
        
        if amount <= 0:
            await update.message.reply_text("❌ Сумма должна быть положительной")
            return
        
        if user_data['diamonds'] < amount:
            await update.message.reply_text(f"❌ Недостаточно алмазов! У вас {user_data['diamonds']} 💎")
            return
        
        # Ищем получателя
        target_user = db.get_user_by_username('tg', target_name)
        
        if not target_user:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        target_id = target_user[2]  # platform_id
        
        # Переводим алмазы
        success, message = db.transfer_money('tg', platform_id, 'tg', target_id, amount, "diamonds")
        
        if success:
            await update.message.reply_text(f"✅ {message}\nПолучатель: {target_user[4]}")
            
            # Уведомляем получателя
            try:
                await context.bot.send_message(
                    chat_id=int(target_id),
                    text=f"💎 {user.first_name} перевел вам {amount} 💎!"
                )
            except:
                pass
        else:
            await update.message.reply_text(f"❌ {message}")
    
    async def tg_cmd_privilege_commands(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(
                "❌ Укажите привилегию:\n"
                "/cmd вип\n"
                "/cmd премиум\n"
                "/cmd лорд\n"
                "/cmd ультра\n"
                "/cmd модератор\n"
                "/cmd оператор\n"
                "/cmd анти-грифер\n"
                "/cmd легенда\n"
                "/cmd эврольд\n"
                "/cmd властелин\n"
                "/cmd титан\n"
                "/cmd терминатор\n"
                "/cmd маг\n"
                "/cmd хелпер\n"
                "/cmd создатель"
            )
            return
        
        privilege = context.args[0].lower()
        
        if privilege not in PRIVILEGES:
            await update.message.reply_text("❌ Неизвестная привилегия")
            return
        
        priv_data = PRIVILEGES[privilege]
        
        text = (
            f"{priv_data['emoji']} **КОМАНДЫ {privilege.upper()}** {priv_data['emoji']}\n\n"
        )
        
        for cmd in priv_data['commands']:
            text += f"▫️ {cmd}\n"
        
        if privilege in ['модератор', 'оператор', 'анти-грифер', 'хелпер']:
            text += "\n▫️ /mute [ник] [время] [причина]\n"
            text += "▫️ /warn [ник] [причина]\n"
            text += "▫️ /ban [ник] [время] [причина]\n"
            text += "▫️ /unban [ник]\n"
            text += "▫️ /banlist\n"
            text += "▫️ /mutelist\n"
            text += "▫️ /warnlist\n"
        
        if privilege == 'создатель':
            text += "\n▫️ /give [ник] [сумма]\n"
            text += "▫️ /set_privilege [ник] [привилегия]\n"
            text += "▫️ /global_ban [ник]\n"
            text += "▫️ /system [команда]\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def tg_cmd_donate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "💎 **ПРИВИЛЕГИИ «СПЕКТР»** 💎\n\n"
        )
        
        for priv_name, priv_data in PRIVILEGES.items():
            if priv_data['price'] > 0:
                text += f"{priv_data['emoji']} **{priv_name.upper()}**\n"
                text += f"└ 💰 Цена: {priv_data['price']} 🪙\n"
                text += f"└ 📅 Длительность: {priv_data['days']} дн\n"
                text += f"└ 📋 Команды: /cmd {priv_name}\n\n"
        
        text += "👑 **АДМИН-ПРИВИЛЕГИИ** (не продаются)\n"
        text += "модератор, оператор, анти-грифер, хелпер, создатель\n\n"
        text += f"💳 Приобрести: напишите {OWNER_USERNAME_TG}"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="menu_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def tg_cmd_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = str(update.effective_chat.id)
        
        # Получаем правила для чата
        db.cursor.execute("SELECT rules FROM group_settings WHERE chat_id = ? AND platform = 'tg'", (chat_id,))
        result = db.cursor.fetchone()
        rules = result[0] if result else "Правила не установлены. Админ может установить их через /set_rules"
        
        await update.message.reply_text(f"📖 **ПРАВИЛА ЧАТА**\n\n{rules}", parse_mode='Markdown')
    
    async def tg_cmd_set_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Проверяем права
        user_id = update.effective_user.id
        chat_id = str(update.effective_chat.id)
        
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        if chat_member.status not in ['creator', 'administrator'] and not db.has_privilege('tg', str(user_id), 'создатель'):
            await update.message.reply_text("❌ Только администраторы могут устанавливать правила")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Использование: /set_rules [текст правил]")
            return
        
        rules = " ".join(context.args)
        
        # Сохраняем правила
        db.cursor.execute('''
            INSERT OR REPLACE INTO group_settings (chat_id, platform, rules)
            VALUES (?, ?, ?)
        ''', (chat_id, 'tg', rules))
        db.conn.commit()
        
        await update.message.reply_text(f"✅ Правила установлены!")
    
    async def tg_cmd_mute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        
        # Проверяем права
        if not db.has_privilege('tg', user_id, 'модератор') and not db.has_privilege('tg', user_id, 'создатель'):
            await update.message.reply_text("❌ Недостаточно прав")
            return
        
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /mute [ник] [время] [причина]")
            return
        
        target_name = context.args[0]
        time_str = context.args[1]
        reason = " ".join(context.args[2:]) if len(context.args) > 2 else "Нарушение"
        
        # Парсим время
        minutes = 5  # По умолчанию
        match = re.match(r'(\d+)([мчд])', time_str)
        if match:
            value = int(match.group(1))
            unit = match.group(2)
            if unit == 'м':
                minutes = value
            elif unit == 'ч':
                minutes = value * 60
            elif unit == 'д':
                minutes = value * 1440
        else:
            try:
                minutes = int(time_str)
            except:
                minutes = 5
        
        # Ищем пользователя
        target_user = db.get_user_by_username('tg', target_name)
        
        if not target_user:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        target_id = target_user[2]
        target_username = target_user[3] or target_user[4]
        
        mute_until = db.mute_user('tg', target_id, target_username, minutes, reason, update.effective_user.id, update.effective_user.first_name)
        
        await update.message.reply_text(
            f"🔇 **Пользователь замучен**\n\n"
            f"👤 {target_username}\n"
            f"⏱ Время: {minutes} мин\n"
            f"💬 Причина: {reason}\n"
            f"👮 Модератор: {update.effective_user.first_name}"
        )
        
        # Уведомляем пользователя
        try:
            await context.bot.send_message(
                chat_id=int(target_id),
                text=f"🔇 Вы замучены на {minutes} минут.\nПричина: {reason}"
            )
        except:
            pass
    
    async def tg_cmd_unmute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        
        if not db.has_privilege('tg', user_id, 'модератор') and not db.has_privilege('tg', user_id, 'создатель'):
            await update.message.reply_text("❌ Недостаточно прав")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Использование: /unmute [ник]")
            return
        
        target_name = context.args[0]
        
        target_user = db.get_user_by_username('tg', target_name)
        
        if not target_user:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        target_id = target_user[2]
        
        db.unmute_user('tg', target_id)
        
        await update.message.reply_text(f"✅ Мут снят с {target_name}")
        
        try:
            await context.bot.send_message(
                chat_id=int(target_id),
                text="✅ Ваш мут снят"
            )
        except:
            pass
    
    async def tg_cmd_warn(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        
        if not db.has_privilege('tg', user_id, 'модератор') and not db.has_privilege('tg', user_id, 'создатель'):
            await update.message.reply_text("❌ Недостаточно прав")
            return
        
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /warn [ник] [причина]")
            return
        
        target_name = context.args[0]
        reason = " ".join(context.args[1:])
        
        target_user = db.get_user_by_username('tg', target_name)
        
        if not target_user:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        target_id = target_user[2]
        target_username = target_user[3] or target_user[4]
        
        warns = db.add_warn('tg', target_id, target_username, reason, update.effective_user.id, update.effective_user.first_name)
        
        await update.message.reply_text(
            f"⚠️ **Предупреждение выдано**\n\n"
            f"👤 {target_username}\n"
            f"⚠️ Варнов: {warns}/3\n"
            f"💬 Причина: {reason}\n"
            f"👮 Модератор: {update.effective_user.first_name}"
        )
        
        if warns >= 3:
            # Автоматический мут при 3 варнах
            db.mute_user('tg', target_id, target_username, 1440, "3 предупреждения", update.effective_user.id, update.effective_user.first_name)
            await update.message.reply_text(f"⚠️ Пользователь получил 3 варна и замучен на 24 часа!")
        
        try:
            await context.bot.send_message(
                chat_id=int(target_id),
                text=f"⚠️ Вам выдано предупреждение ({warns}/3)\nПричина: {reason}"
            )
        except:
            pass
    
    async def tg_cmd_ban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        
        if not db.has_privilege('tg', user_id, 'модератор') and not db.has_privilege('tg', user_id, 'создатель'):
            await update.message.reply_text("❌ Недостаточно прав")
            return
        
        if len(context.args) < 3:
            await update.message.reply_text("❌ Использование: /ban [ник] [время] [причина]")
            return
        
        target_name = context.args[0]
        duration = context.args[1]
        reason = " ".join(context.args[2:])
        
        target_user = db.get_user_by_username('tg', target_name)
        
        if not target_user:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        target_id = target_user[2]
        target_username = target_user[3] or target_user[4]
        
        db.ban_user('tg', target_id, target_username, reason, duration, update.effective_user.id, update.effective_user.first_name)
        
        await update.message.reply_text(
            f"🚫 **Пользователь забанен**\n\n"
            f"👤 {target_username}\n"
            f"⏱ Срок: {duration}\n"
            f"💬 Причина: {reason}\n"
            f"👮 Модератор: {update.effective_user.first_name}"
        )
        
        try:
            await context.bot.send_message(
                chat_id=int(target_id),
                text=f"🚫 Вы забанены.\nСрок: {duration}\nПричина: {reason}"
            )
        except:
            pass
    
    async def tg_cmd_unban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        
        if not db.has_privilege('tg', user_id, 'модератор') and not db.has_privilege('tg', user_id, 'создатель'):
            await update.message.reply_text("❌ Недостаточно прав")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Использование: /unban [ник]")
            return
        
        target_name = context.args[0]
        
        target_user = db.get_user_by_username('tg', target_name)
        
        if not target_user:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        target_id = target_user[2]
        
        db.unban_user('tg', target_id)
        
        await update.message.reply_text(f"✅ Пользователь {target_name} разбанен")
        
        try:
            await context.bot.send_message(
                chat_id=int(target_id),
                text="✅ Вы разбанены"
            )
        except:
            pass
    
    async def tg_cmd_banlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        
        if not db.has_privilege('tg', user_id, 'модератор') and not db.has_privilege('tg', user_id, 'создатель'):
            await update.message.reply_text("❌ Недостаточно прав")
            return
        
        page = 1
        if context.args:
            try:
                page = int(context.args[0])
            except:
                pass
        
        bans = db.get_banned_users(page, 10)
        
        if not bans:
            await update.message.reply_text("📭 Список банов пуст")
            return
        
        text = f"🚫 **СПИСОК ЗАБАНЕННЫХ** (стр. {page})\n\n"
        
        for i, ban in enumerate(bans, 1):
            username = ban[3] or f"ID {ban[2]}"
            reason = ban[4] or "Не указана"
            banned_by = ban[6] or "Неизвестно"
            ban_date = ban[7][:10] if ban[7] else "Неизвестно"
            duration = "Навсегда" if ban[10] else ban[8]
            
            text += f"{i}. {username}\n"
            text += f"   ⏱ {duration}\n"
            text += f"   💬 {reason}\n"
            text += f"   👮 {banned_by}\n"
            text += f"   📅 {ban_date}\n\n"
        
        keyboard = []
        nav_row = []
        if page > 1:
            nav_row.append(InlineKeyboardButton("⬅️", callback_data=f"banlist_{page-1}"))
        nav_row.append(InlineKeyboardButton(f"{page}", callback_data="noop"))
        nav_row.append(InlineKeyboardButton("➡️", callback_data=f"banlist_{page+1}"))
        keyboard.append(nav_row)
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def tg_cmd_mutelist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        
        if not db.has_privilege('tg', user_id, 'модератор') and not db.has_privilege('tg', user_id, 'создатель'):
            await update.message.reply_text("❌ Недостаточно прав")
            return
        
        page = 1
        if context.args:
            try:
                page = int(context.args[0])
            except:
                pass
        
        mutes = db.get_muted_users(page, 10)
        
        if not mutes:
            await update.message.reply_text("📭 Список мутов пуст")
            return
        
        text = f"🔇 **СПИСОК ЗАМУЧЕННЫХ** (стр. {page})\n\n"
        
        for i, mute in enumerate(mutes, 1):
            username = mute[3] or f"ID {mute[2]}"
            reason = mute[4] or "Не указана"
            muted_by = mute[6] or "Неизвестно"
            mute_date = mute[7][:10] if mute[7] else "Неизвестно"
            duration = mute[8]
            
            text += f"{i}. {username}\n"
            text += f"   ⏱ {duration}\n"
            text += f"   💬 {reason}\n"
            text += f"   👮 {muted_by}\n"
            text += f"   📅 {mute_date}\n\n"
        
        keyboard = []
        nav_row = []
        if page > 1:
            nav_row.append(InlineKeyboardButton("⬅️", callback_data=f"mutelist_{page-1}"))
        nav_row.append(InlineKeyboardButton(f"{page}", callback_data="noop"))
        nav_row.append(InlineKeyboardButton("➡️", callback_data=f"mutelist_{page+1}"))
        keyboard.append(nav_row)
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def tg_cmd_warnlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        
        if not db.has_privilege('tg', user_id, 'модератор') and not db.has_privilege('tg', user_id, 'создатель'):
            await update.message.reply_text("❌ Недостаточно прав")
            return
        
        page = 1
        if context.args:
            try:
                page = int(context.args[0])
            except:
                pass
        
        warns = db.get_warned_users(page, 10)
        
        if not warns:
            await update.message.reply_text("📭 Список предупреждений пуст")
            return
        
        text = f"⚠️ **СПИСОК ПРЕДУПРЕЖДЕНИЙ** (стр. {page})\n\n"
        
        for i, warn in enumerate(warns, 1):
            username = warn[3] or f"ID {warn[2]}"
            reason = warn[4] or "Не указана"
            warned_by = warn[6] or "Неизвестно"
            warn_date = warn[7][:10] if warn[7] else "Неизвестно"
            count = warn[8]
            
            text += f"{i}. {username}\n"
            text += f"   ⚠️ Варн #{count}\n"
            text += f"   💬 {reason}\n"
            text += f"   👮 {warned_by}\n"
            text += f"   📅 {warn_date}\n\n"
        
        keyboard = []
        nav_row = []
        if page > 1:
            nav_row.append(InlineKeyboardButton("⬅️", callback_data=f"warnlist_{page-1}"))
        nav_row.append(InlineKeyboardButton(f"{page}", callback_data="noop"))
        nav_row.append(InlineKeyboardButton("➡️", callback_data=f"warnlist_{page+1}"))
        keyboard.append(nav_row)
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def tg_cmd_top(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        top_coins = db.get_top("coins", 10)
        top_level = db.get_top("level", 10)
        top_boss = db.get_top("boss_kills", 10)
        
        text = (
            f"╔══════════════════════════════╗\n"
            f"║    🏆 **ТОП ИГРОКОВ**        ║\n"
            f"╚══════════════════════════════╝\n\n"
        )
        
        text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "💰 **ПО МОНЕТАМ**\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        for i, (username, first_name, value) in enumerate(top_coins, 1):
            name = first_name or username or f"Игрок {i}"
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} {name} — {value:,} 🪙\n"
        
        text += "\n━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "📊 **ПО УРОВНЮ**\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        for i, (username, first_name, value) in enumerate(top_level, 1):
            name = first_name or username or f"Игрок {i}"
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} {name} — {value} ур.\n"
        
        text += "\n━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "👾 **ПО УБИЙСТВУ БОССОВ**\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        for i, (username, first_name, value) in enumerate(top_boss, 1):
            name = first_name or username or f"Игрок {i}"
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} {name} — {value} боссов\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def tg_cmd_players(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        count = db.get_player_count()
        await update.message.reply_text(f"👥 **Активных игроков:** {count}", parse_mode='Markdown')
    
    async def tg_handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        message_text = update.message.text
        
        # Получаем пользователя
        user_data = db.get_user('tg', platform_id, user.username or "", user.first_name, user.last_name or "")
        db.update_activity('tg', platform_id)
        db.add_message_count('tg', platform_id)
        
        # Проверяем бан
        if db.is_banned('tg', platform_id):
            return
        
        # Проверяем мут
        if db.is_muted('tg', platform_id):
            return
        
        # Сохраняем сообщение для закладок
        db.cursor.execute('''
            INSERT INTO messages (platform, platform_id, message)
            VALUES (?, ?, ?)
        ''', ('tg', platform_id, message_text[:500]))
        db.conn.commit()
        
        # Проверяем на команду регенерации в чате
        if message_text.lower() == "регенерация":
            await self.tg_cmd_regen(update, context)
            return
        
        # Проверяем на длительное молчание
        last_msg_time = self.last_activity['tg'].get(platform_id, 0)
        current_time = time.time()
        
        if last_msg_time > 0 and current_time - last_msg_time > 30 * 24 * 3600:  # 30 дней
            await update.message.reply_text(
                f"⚡️⚡️⚡️ Святые угодники!\n"
                f"[id{user.id}|{user.first_name}] заговорил после более, чем месячного молчания!!! Поприветствуйте молчуна! 👏"
            )
        
        self.last_activity['tg'][platform_id] = current_time
        
        # Приветствие для новых
        if user_data['messages_count'] == 1:
            await update.message.reply_text(f"🌟 Добро пожаловать, {user.first_name}! Используй /help для списка команд.")
    
    async def tg_handle_new_members(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = str(update.effective_chat.id)
        
        # Получаем настройки чата
        db.cursor.execute("SELECT welcome_message FROM group_settings WHERE chat_id = ? AND platform = 'tg'", (chat_id,))
        result = db.cursor.fetchone()
        welcome = result[0] if result else "🌟 Добро пожаловать, {user}!"
        
        for member in update.message.new_chat_members:
            if member.is_bot:
                continue
            
            welcome_text = welcome.replace('{user}', f"[{member.first_name}](tg://user?id={member.id})")
            await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    async def tg_button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    # Обработка основных кнопок меню
    if data == "profile":
        await self.tg_cmd_profile(update, context)
    elif data == "boss":
        await self.tg_cmd_boss(update, context)
    elif data == "shop":
        await self.tg_cmd_shop(update, context)
    elif data == "donate":
        await self.tg_cmd_donate(update, context)
    elif data == "top":
        await self.tg_cmd_top(update, context)
    elif data == "players" or data == "online":
        await self.tg_cmd_players(update, context)
    elif data == "help" or data == "commands":
        await self.tg_cmd_help(update, context)
    elif data == "rules":
        await self.tg_cmd_rules(update, context)
    elif data == "boss_fight":
        await self.tg_cmd_boss_fight(update, context)
    elif data == "regen":
        await self.tg_cmd_regen(update, context)
    elif data == "boss_shop":
        context.args = ["3"]
        await self.tg_cmd_shop(update, context)
    elif data == "menu_back":
        # Главное меню
        keyboard = [
            [InlineKeyboardButton("👤 Профиль", callback_data="profile"),
             InlineKeyboardButton("👾 Босс", callback_data="boss")],
            [InlineKeyboardButton("💰 Магазин", callback_data="shop"),
             InlineKeyboardButton("💎 Привилегии", callback_data="donate")],
            [InlineKeyboardButton("📊 Топ", callback_data="top"),
             InlineKeyboardButton("👥 Онлайн", callback_data="players")],
            [InlineKeyboardButton("📚 Команды", callback_data="help"),
             InlineKeyboardButton("📖 Правила", callback_data="rules")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🎮 **ГЛАВНОЕ МЕНЮ**\n\nВыберите раздел:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    elif data.startswith("banlist_"):
        page = int(data.split("_")[1])
        context.args = [str(page)]
        await self.tg_cmd_banlist(update, context)
    elif data.startswith("mutelist_"):
        page = int(data.split("_")[1])
        context.args = [str(page)]
        await self.tg_cmd_mutelist(update, context)
    elif data.startswith("warnlist_"):
        page = int(data.split("_")[1])
        context.args = [str(page)]
        await self.tg_cmd_warnlist(update, context)
    elif data.startswith("buy_potions"):
        await query.edit_message_text("💊 Выберите зелье:\n/use зелье_здоровья - 50 🪙\n/use большое_зелье - 100 🪙")
    elif data.startswith("buy_weapons"):
        await query.edit_message_text("⚔️ Выберите оружие:\n/use меч - 200 🪙\n/use легендарный_меч - 500 🪙")
    elif data.startswith("buy_armor"):
        await query.edit_message_text("🛡 Выберите броню:\n/use щит - 150 🪙\n/use доспехи - 400 🪙")
    elif data.startswith("buy_energy"):
        await query.edit_message_text("⚡ Выберите энергию:\n/use энергетик - 30 🪙\n/use батарейка - 80 🪙")
    elif data.startswith("admin_menu"):
        await query.edit_message_text("👑 **АДМИН МЕНЮ**\n\nИспользуйте команды:\n/banlist\n/mutelist\n/warnlist\n/mute\n/unmute\n/ban\n/unban\n/warn")
    elif data == "noop":
        # Пустая кнопка, ничего не делаем
        pass
    else:
        # Если неизвестная кнопка, показываем главное меню
        keyboard = [
            [InlineKeyboardButton("👤 Профиль", callback_data="profile"),
             InlineKeyboardButton("👾 Босс", callback_data="boss")],
            [InlineKeyboardButton("💰 Магазин", callback_data="shop"),
             InlineKeyboardButton("💎 Привилегии", callback_data="donate")],
            [InlineKeyboardButton("📊 Топ", callback_data="top"),
             InlineKeyboardButton("👥 Онлайн", callback_data="players")],
            [InlineKeyboardButton("📚 Команды", callback_data="help"),
             InlineKeyboardButton("📖 Правила", callback_data="rules")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🎮 **ГЛАВНОЕ МЕНЮ**\n\nВыберите раздел:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        elif data.startswith("banlist_"):
            page = int(data.split("_")[1])
            context.args = [str(page)]
            await self.tg_cmd_banlist(update, context)
        elif data.startswith("mutelist_"):
            page = int(data.split("_")[1])
            context.args = [str(page)]
            await self.tg_cmd_mutelist(update, context)
        elif data.startswith("warnlist_"):
            page = int(data.split("_")[1])
            context.args = [str(page)]
            await self.tg_cmd_warnlist(update, context)
    
    # ===================== VK ОБРАБОТЧИКИ =====================
    def setup_vk_handlers(self):
        @self.vk_bot.on.message()
        async def vk_message_handler(message: Message):
            await self.vk_handle_message(message)
        
        @self.vk_bot.on.message(text=["/start", "!start"])
        async def vk_cmd_start(message: Message):
            await self.vk_cmd_start(message)
        
        @self.vk_bot.on.message(text=["/menu", "!menu"])
        async def vk_cmd_menu(message: Message):
            await self.vk_cmd_menu(message)
        
        @self.vk_bot.on.message(text=["/help", "!help", "/помощь"])
        async def vk_cmd_help(message: Message):
            await self.vk_cmd_help(message)
        
        @self.vk_bot.on.message(text=["/profile", "!profile", "/профиль"])
        async def vk_cmd_profile(message: Message):
            await self.vk_cmd_profile(message)
        
        @self.vk_bot.on.message(text=["/boss", "!boss", "/босс"])
        async def vk_cmd_boss(message: Message):
            await self.vk_cmd_boss(message)
        
        @self.vk_bot.on.message(text=["/boss_fight", "!boss_fight", "/удар"])
        async def vk_cmd_boss_fight(message: Message):
            await self.vk_cmd_boss_fight(message)
        
        @self.vk_bot.on.message(text=["/regen", "!regen", "/реген"])
        async def vk_cmd_regen(message: Message):
            await self.vk_cmd_regen(message)
        
        @self.vk_bot.on.message(text=["/shop", "!shop", "/магазин"])
        async def vk_cmd_shop(message: Message):
            await self.vk_cmd_shop(message)
        
        @self.vk_bot.on.message(text=["/top", "!top", "/топ"])
        async def vk_cmd_top(message: Message):
            await self.vk_cmd_top(message)
        
        @self.vk_bot.on.message(text=["/players", "!players", "/игроки"])
        async def vk_cmd_players(message: Message):
            await self.vk_cmd_players(message)
        
        @self.vk_bot.on.message(text=["/payd", "!payd"])
        async def vk_cmd_payd(message: Message):
            args = message.text.split()[1:] if len(message.text.split()) > 1 else []
            await self.vk_cmd_payd(message, args)
        
        @self.vk_bot.on.message(text=["/payh", "!payh"])
        async def vk_cmd_payh(message: Message):
            args = message.text.split()[1:] if len(message.text.split()) > 1 else []
            await self.vk_cmd_payh(message, args)
        
        @self.vk_bot.on.message(text=["/cmd", "!cmd"])
        async def vk_cmd_privilege_commands(message: Message):
            args = message.text.split()[1:] if len(message.text.split()) > 1 else []
            await self.vk_cmd_privilege_commands(message, args)
        
        @self.vk_bot.on.message(text=["/donate", "!donate", "/донат"])
        async def vk_cmd_donate(message: Message):
            await self.vk_cmd_donate(message)
        
        @self.vk_bot.on.message(text=["/rules", "!rules", "/правила"])
        async def vk_cmd_rules(message: Message):
            await self.vk_cmd_rules(message)
        
        @self.vk_bot.on.message(text=["/set_rules", "!set_rules"])
        async def vk_cmd_set_rules(message: Message):
            args = message.text.split()[1:] if len(message.text.split()) > 1 else []
            await self.vk_cmd_set_rules(message, args)
        
        @self.vk_bot.on.message(text=["/mute", "!mute"])
        async def vk_cmd_mute(message: Message):
            args = message.text.split()[1:] if len(message.text.split()) > 1 else []
            await self.vk_cmd_mute(message, args)
        
        @self.vk_bot.on.message(text=["/unmute", "!unmute"])
        async def vk_cmd_unmute(message: Message):
            args = message.text.split()[1:] if len(message.text.split()) > 1 else []
            await self.vk_cmd_unmute(message, args)
        
        @self.vk_bot.on.message(text=["/warn", "!warn"])
        async def vk_cmd_warn(message: Message):
            args = message.text.split()[1:] if len(message.text.split()) > 1 else []
            await self.vk_cmd_warn(message, args)
        
        @self.vk_bot.on.message(text=["/ban", "!ban"])
        async def vk_cmd_ban(message: Message):
            args = message.text.split()[1:] if len(message.text.split()) > 1 else []
            await self.vk_cmd_ban(message, args)
        
        @self.vk_bot.on.message(text=["/unban", "!unban"])
        async def vk_cmd_unban(message: Message):
            args = message.text.split()[1:] if len(message.text.split()) > 1 else []
            await self.vk_cmd_unban(message, args)
        
        @self.vk_bot.on.message(text=["/banlist", "!banlist"])
        async def vk_cmd_banlist(message: Message):
            args = message.text.split()[1:] if len(message.text.split()) > 1 else []
            await self.vk_cmd_banlist(message, args)
        
        @self.vk_bot.on.message(text=["/mutelist", "!mutelist"])
        async def vk_cmd_mutelist(message: Message):
            args = message.text.split()[1:] if len(message.text.split()) > 1 else []
            await self.vk_cmd_mutelist(message, args)
        
        @self.vk_bot.on.message(text=["/warnlist", "!warnlist"])
        async def vk_cmd_warnlist(message: Message):
            args = message.text.split()[1:] if len(message.text.split()) > 1 else []
            await self.vk_cmd_warnlist(message, args)
        
        @self.vk_bot.on.message(text=["/sms", "!sms"])
        async def vk_cmd_sms(message: Message):
            args = message.text.split()[1:] if len(message.text.split()) > 1 else []
            await self.vk_cmd_sms(message, args)
        
        @self.vk_bot.on.message(text=["/eng", "!eng"])
        async def vk_cmd_eng(message: Message):
            args = message.text.split()[1:] if len(message.text.split()) > 1 else []
            await self.vk_cmd_eng(message, args)
        
        @self.vk_bot.on.message(text=["/namutebuy", "!namutebuy"])
        async def vk_cmd_namutebuy(message: Message):
            await self.vk_cmd_namutebuy(message)
        
        @self.vk_bot.on.message(text=["/automes", "!automes"])
        async def vk_cmd_automes(message: Message):
            args = message.text.split()[1:] if len(message.text.split()) > 1 else []
            await self.vk_cmd_automes(message, args)
        
        @self.vk_bot.on.message(text=["/player", "!player"])
        async def vk_cmd_player(message: Message):
            args = message.text.split()[1:] if len(message.text.split()) > 1 else []
            await self.vk_cmd_player(message, args)
        
        @self.vk_bot.on.message(text=["+закладка"])
        async def vk_cmd_add_bookmark(message: Message):
            args = message.text.split()[1:] if len(message.text.split()) > 1 else []
            await self.vk_cmd_add_bookmark(message, args)
        
        @self.vk_bot.on.message(text=["закладки"])
        async def vk_cmd_bookmarks(message: Message):
            args = message.text.split()[1:] if len(message.text.split()) > 1 else []
            await self.vk_cmd_bookmarks(message, args)
        
        @self.vk_bot.on.message(text=["моя статья"])
        async def vk_cmd_my_article(message: Message):
            await self.vk_cmd_my_article(message)
        
        @self.vk_bot.on.message(text=["кто я"])
        async def vk_cmd_whoami(message: Message):
            await self.vk_cmd_whoami(message)
        
        logger.info("✅ VK обработчики зарегистрированы")
    
    async def vk_handle_message(self, message: Message):
        user_id = str(message.from_id)
        user_info = await self.vk_api.users.get(user_ids=user_id)
        user = user_info[0] if user_info else None
        
        if not user:
            return
        
        platform_id = str(user.id)
        first_name = user.first_name
        last_name = user.last_name or ""
        
        # Получаем пользователя
        user_data = db.get_user('vk', platform_id, user.domain or "", first_name, last_name)
        db.update_activity('vk', platform_id)
        db.add_message_count('vk', platform_id)
        
        # Проверяем бан
        if db.is_banned('vk', platform_id):
            return
        
        # Проверяем мут
        if db.is_muted('vk', platform_id):
            return
        
        # Сохраняем сообщение для закладок
        db.cursor.execute('''
            INSERT INTO messages (platform, platform_id, message)
            VALUES (?, ?, ?)
        ''', ('vk', platform_id, message.text[:500]))
        db.conn.commit()
        
        # Проверяем на команду регенерации в чате
        if message.text.lower() == "регенерация":
            await self.vk_cmd_regen(message)
            return
        
        # Проверяем на длительное молчание
        last_msg_time = self.last_activity['vk'].get(platform_id, 0)
        current_time = time.time()
        
        if last_msg_time > 0 and current_time - last_msg_time > 30 * 24 * 3600:  # 30 дней
            await message.reply(
                f"⚡️⚡️⚡️ Святые угодники!\n"
                f"[id{user.id}|{first_name}] заговорил после более, чем месячного молчания!!! Поприветствуйте молчуна! 👏"
            )
        
        self.last_activity['vk'][platform_id] = current_time
        
        # Приветствие для новых
        if user_data['messages_count'] == 1:
            await message.reply(f"🌟 Добро пожаловать, {first_name}! Используй /help для списка команд.")
    
    async def vk_cmd_start(self, message: Message):
        user_id = str(message.from_id)
        user_info = await self.vk_api.users.get(user_ids=user_id)
        user = user_info[0] if user_info else None
        
        if not user:
            return
        
        platform_id = str(user.id)
        
        db.get_user('vk', platform_id, user.domain or "", user.first_name, user.last_name or "")
        db.update_activity('vk', platform_id)
        db.add_command_count('vk', platform_id)
        
        text = (
            f"╔══════════════════════════════╗\n"
            f"║   ⚔️ СПЕКТР БОТ ⚔️            ║\n"
            f"╚══════════════════════════════╝\n\n"
            f"🌟 Привет, {user.first_name}!\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"ОСНОВНЫЕ КОМАНДЫ\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"/profile - твой профиль\n"
            f"/boss - битва с боссом\n"
            f"/shop - магазин\n"
            f"/donate - привилегии\n"
            f"/top - топ игроков\n"
            f"/players - онлайн\n"
            f"/help - все команды\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👑 Владелец: [id{OWNER_ID_VK}|NobuCraft]\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━"
        )
        
        await message.reply(text)
    
    async def vk_cmd_menu(self, message: Message):
        text = (
            "🎮 ГЛАВНОЕ МЕНЮ\n\n"
            "1. 👤 Профиль - /profile\n"
            "2. 👾 Босс - /boss\n"
            "3. 💰 Магазин - /shop\n"
            "4. 💎 Привилегии - /donate\n"
            "5. 📊 Топ - /top\n"
            "6. 👥 Онлайн - /players\n"
            "7. 📚 Команды - /help\n"
            "8. 📖 Правила - /rules\n\n"
            "Выберите команду:"
        )
        
        await message.reply(text)
    
    async def vk_cmd_help(self, message: Message):
        text = (
            "📚 ВСЕ КОМАНДЫ БОТА\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "ОСНОВНЫЕ\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/start - запуск бота\n"
            "/menu - главное меню\n"
            "/help - эта справка\n"
            "/profile - твой профиль\n"
            "/player [ник] - профиль игрока\n"
            "/top - топ игроков\n"
            "/players - количество игроков\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "БИТВА С БОССОМ\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/boss - информация о боссе\n"
            "/boss_fight - ударить босса\n"
            "/regen - восстановить здоровье\n"
            "/shop 3 - магазин оружия\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "ЭКОНОМИКА\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/shop - магазин\n"
            "/payd [ник] [сумма] - перевести монеты\n"
            "/payh [ник] [сумма] - перевести алмазы\n"
            "/donate - привилегии\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "АДМИН-КОМАНДЫ\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/mute [ник] [время] [причина] - мут\n"
            "/unmute [ник] - снять мут\n"
            "/warn [ник] [причина] - предупреждение\n"
            "/ban [ник] [время] [причина] - бан\n"
            "/unban [ник] - разбан\n"
            "/banlist - список банов\n"
            "/mutelist - список мутов\n"
            "/warnlist - список варнов\n"
            "/set_rules [текст] - установить правила\n"
            "/rules - показать правила\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "ДРУГОЕ\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/sms [ник] [текст] - личное сообщение\n"
            "/eng free - получить бесплатную энергию\n"
            "/namutebuy - снять мут за монеты\n"
            "/automes on/off - автосообщение\n"
            "/cmd [привилегия] - команды доната\n"
            "+закладка [описание] - создать закладку\n"
            "закладки [номер] - показать закладки\n"
            "моя статья - случайная статья\n"
            "кто я - информация о себе"
        )
        
        await message.reply(text)
    
    async def vk_cmd_profile(self, message: Message):
        user_id = str(message.from_id)
        user_info = await self.vk_api.users.get(user_ids=user_id)
        user = user_info[0] if user_info else None
        
        if not user:
            return
        
        platform_id = str(user.id)
        
        user_data = db.get_user('vk', platform_id, user.domain or "", user.first_name, user.last_name or "")
        db.update_activity('vk', platform_id)
        db.add_command_count('vk', platform_id)
        
        if db.is_banned('vk', platform_id):
            await message.reply("🚫 Вы забанены в боте.")
            return
        
        # Получаем привилегию
        privilege = user_data.get('privilege', 'user')
        privilege_emoji = PRIVILEGES.get(privilege, {}).get('emoji', '👤') if privilege != 'user' else '👤'
        
        # Получаем последнюю активность
        last_activity = "Неизвестно"
        if user_data.get('last_activity'):
            last = datetime.datetime.fromisoformat(user_data['last_activity'])
            delta = datetime.datetime.now() - last
            if delta.days > 0:
                last_activity = f"{delta.days} дн назад"
            elif delta.seconds > 3600:
                last_activity = f"{delta.seconds // 3600} ч назад"
            elif delta.seconds > 60:
                last_activity = f"{delta.seconds // 60} мин назад"
            else:
                last_activity = "только что"
        
        text = (
            f"╔══════════════════════════════╗\n"
            f"║   👤 ПРОФИЛЬ ИГРОКА           ║\n"
            f"╚══════════════════════════════╝\n\n"
            
            f"[id{user.id}|{user.first_name}] {privilege_emoji}\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"РЕСУРСЫ\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🪙 Монеты: {user_data['coins']:,}\n"
            f"💎 Алмазы: {user_data['diamonds']:,}\n"
            f"🔮 Кристаллы: {user_data['crystals']:,}\n"
            f"💀 Черепки: {user_data['rr_money']}\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"ХАРАКТЕРИСТИКИ\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"❤️ Здоровье: {user_data['health']}/{user_data['max_health']}\n"
            f"⚔️ Урон: {user_data['damage']}\n"
            f"🛡 Броня: {user_data['armor']}\n"
            f"⚡ Энергия: {user_data['energy']}\n"
            f"📊 Уровень: {user_data['level']}\n"
            f"✨ Опыт: {user_data['exp']}/{user_data['level'] * 100}\n"
            f"👾 Боссов убито: {user_data['boss_kills']}\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"СТАТИСТИКА\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📝 Сообщений: {user_data['messages_count']}\n"
            f"⌨️ Команд: {user_data['commands_used']}\n"
            f"🎮 Игр: {user_data['games_played']}\n"
            f"⭐ Репутация: {user_data['reputation']}\n"
            f"⏱ Последний визит: {last_activity}\n"
            f"📅 Первое появление: {user_data['first_seen'][:10] if user_data['first_seen'] else 'Неизвестно'}"
        )
        
        await message.reply(text)
    
    async def vk_cmd_boss(self, message: Message):
        user_id = str(message.from_id)
        user_info = await self.vk_api.users.get(user_ids=user_id)
        user = user_info[0] if user_info else None
        
        if not user:
            return
        
        platform_id = str(user.id)
        
        user_data = db.get_user('vk', platform_id, user.domain or "", user.first_name, user.last_name or "")
        db.update_activity('vk', platform_id)
        db.add_command_count('vk', platform_id)
        
        boss = db.get_boss()
        
        if not boss:
            await message.reply("👾 Все боссы повержены! Ожидайте возрождения...")
            return
        
        # Рассчитываем урон игрока с учетом бонусов
        player_damage = user_data['damage'] * (user_data['level'] / 10 + 1)
        
        text = (
            f"╔══════════════════════════════╗\n"
            f"║   👾 БИТВА С БОССОМ           ║\n"
            f"╚══════════════════════════════╝\n\n"
            
            f"🔥 Текущий босс: {boss['boss_name']}\n"
            f"💫 Урон от босса: {boss['boss_damage']} HP\n"
            f"🖤 Жизни босса: {boss['boss_health']} HP\n"
            f"🗡 Ваш уровень силы: {((player_damage / boss['boss_damage']) * 100):.1f}%\n"
            f"❤️ Ваше здоровье: {user_data['health']} HP\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"КОМАНДЫ\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👊 /boss_fight - ударить босса\n"
            f"➕ /regen - регенерация здоровья\n"
            f"🗡 /shop 3 - магазин оружия"
        )
        
        await message.reply(text)
    
    async def vk_cmd_boss_fight(self, message: Message):
        user_id = str(message.from_id)
        user_info = await self.vk_api.users.get(user_ids=user_id)
        user = user_info[0] if user_info else None
        
        if not user:
            return
        
        platform_id = str(user.id)
        
        user_data = db.get_user('vk', platform_id, user.domain or "", user.first_name, user.last_name or "")
        db.update_activity('vk', platform_id)
        db.add_command_count('vk', platform_id)
        
        boss = db.get_boss()
        
        if not boss:
            await message.reply("👾 Все боссы повержены! Ожидайте возрождения...")
            return
        
        if user_data['health'] <= 0:
            await message.reply("💀 У вас нет здоровья! Используйте /regen")
            return
        
        if user_data['energy'] < 5:
            await message.reply("⚡ Недостаточно энергии! Нужно 5 ⚡")
            return
        
        # Расход энергии
        db.add_coins('vk', platform_id, -5, "energy")
        
        # Рассчитываем урон игрока
        player_damage = user_data['damage'] * (1 + user_data['level'] * 0.1)
        
        # Бонусы за привилегии
        if db.has_privilege('vk', platform_id, "премиум"):
            player_damage *= 1.5
        elif db.has_privilege('vk', platform_id, "вип"):
            player_damage *= 1.2
        
        player_damage = int(player_damage)
        boss_damage = boss['boss_damage']
        
        # Урон по боссу
        killed, health_left = db.damage_boss(boss['id'], player_damage)
        
        # Урон по игроку
        db.damage_user('vk', platform_id, boss_damage)
        
        text = f"⚔️ БИТВА С БОССОМ ⚔️\n\n"
        text += f"🔥 Босс: {boss['boss_name']}\n\n"
        text += f"▫️ Твой урон: {player_damage} HP\n"
        text += f"▫️ Урон босса: {boss_damage} HP\n\n"
        
        if killed:
            # Босс побежден
            reward = boss['boss_reward']
            
            # Бонусы за привилегии
            if db.has_privilege('vk', platform_id, "премиум"):
                reward = int(reward * 2)
            elif db.has_privilege('vk', platform_id, "вип"):
                reward = int(reward * 1.5)
            
            db.add_coins('vk', platform_id, reward, "coins")
            db.add_boss_kill('vk', platform_id)
            db.add_exp('vk', platform_id, boss['boss_level'] * 10)
            
            next_boss = db.get_next_boss()
            
            text += f"🎉 БОСС ПОВЕРЖЕН!\n"
            text += f"💰 Награда: {reward} 🪙\n"
            text += f"✨ Опыт: +{boss['boss_level'] * 10}\n\n"
            
            if next_boss:
                text += f"👾 Следующий босс: {next_boss['boss_name']}"
            else:
                text += f"👾 Все боссы побеждены! Ожидайте возрождения..."
        else:
            text += f"👾 Босс еще жив!\n"
            text += f"💀 Осталось: {health_left} HP\n\n"
        
        # Проверка здоровья игрока
        user_data = db.get_user('vk', platform_id)
        if user_data['health'] <= 0:
            text += f"💀 Ты погиб в бою! Используй /regen для восстановления."
        
        await message.reply(text)
    
    async def vk_cmd_regen(self, message: Message):
        user_id = str(message.from_id)
        user_info = await self.vk_api.users.get(user_ids=user_id)
        user = user_info[0] if user_info else None
        
        if not user:
            return
        
        platform_id = str(user.id)
        
        user_data = db.get_user('vk', platform_id, user.domain or "", user.first_name, user.last_name or "")
        db.update_activity('vk', platform_id)
        db.add_command_count('vk', platform_id)
        
        if not db.regen_available('vk', platform_id):
            await message.reply("❌ Регенерация еще не доступна! Подождите немного.")
            return
        
        if user_data['health'] < user_data['max_health']:
            heal_amount = user_data['max_health'] - user_data['health']
            db.heal_user('vk', platform_id, heal_amount)
            
            cooldown = 1 if db.has_privilege('vk', platform_id, "премиум") else 3 if db.has_privilege('vk', platform_id, "вип") else 5
            db.use_regen('vk', platform_id, cooldown)
            
            await message.reply(
                f"➕ РЕГЕНЕРАЦИЯ\n\n"
                f"❤️ Здоровье восстановлено!\n"
                f"Текущее здоровье: {user_data['max_health']}/{user_data['max_health']}\n\n"
                f"⏱ Следующая регенерация через {cooldown} мин."
            )
        else:
            await message.reply("❤️ У тебя уже полное здоровье!")
    
    async def vk_cmd_shop(self, message: Message):
        user_id = str(message.from_id)
        db.update_activity('vk', user_id)
        db.add_command_count('vk', user_id)
        
        text = (
            "💰 МАГАЗИН «СПЕКТР»\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "💊 ЗЕЛЬЯ\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ Зелье здоровья — 50 🪙 (❤️+30)\n"
            "▫️ Большое зелье — 100 🪙 (❤️+70)\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚔️ ОРУЖИЕ\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ Меч — 200 🪙 (⚔️+10)\n"
            "▫️ Легендарный меч — 500 🪙 (⚔️+30)\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🛡 БРОНЯ\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ Щит — 150 🪙 (🛡+5)\n"
            "▫️ Доспехи — 400 🪙 (🛡+15)\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚡ ЭНЕРГИЯ\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ Энергетик — 30 🪙 (⚡+20)\n"
            "▫️ Батарейка — 80 🪙 (⚡+50)\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "💎 ВАЛЮТА\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ Алмаз — 100 🪙 (💎+1)\n"
            "▫️ Кристалл — 500 🪙 (🔮+1)\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🗡 ОРУЖИЕ ДЛЯ БОССОВ\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ /shop 3 - магазин оружия\n\n"
            
            "🛒 Купить: /buy [название]"
        )
        
        await message.reply(text)
    
    async def vk_cmd_top(self, message: Message):
        top_coins = db.get_top("coins", 10)
        top_level = db.get_top("level", 10)
        top_boss = db.get_top("boss_kills", 10)
        
        text = (
            f"╔══════════════════════════════╗\n"
            f"║    🏆 ТОП ИГРОКОВ             ║\n"
            f"╚══════════════════════════════╝\n\n"
        )
        
        text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "💰 ПО МОНЕТАМ\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        for i, (username, first_name, value) in enumerate(top_coins, 1):
            name = first_name or username or f"Игрок {i}"
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} {name} — {value:,} 🪙\n"
        
        text += "\n━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "📊 ПО УРОВНЮ\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        for i, (username, first_name, value) in enumerate(top_level, 1):
            name = first_name or username or f"Игрок {i}"
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} {name} — {value} ур.\n"
        
        text += "\n━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "👾 ПО УБИЙСТВУ БОССОВ\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        for i, (username, first_name, value) in enumerate(top_boss, 1):
            name = first_name or username or f"Игрок {i}"
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} {name} — {value} боссов\n"
        
        await message.reply(text)
    
    async def vk_cmd_players(self, message: Message):
        count = db.get_player_count()
        await message.reply(f"👥 Активных игроков: {count}")
    
    async def vk_cmd_payd(self, message: Message, args):
        if len(args) < 2:
            await message.reply("❌ Использование: /payd [ник] [сумма]")
            return
        
        target_name = args[0]
        try:
            amount = int(args[1])
        except:
            await message.reply("❌ Сумма должна быть числом")
            return
        
        user_id = str(message.from_id)
        user_info = await self.vk_api.users.get(user_ids=user_id)
        user = user_info[0] if user_info else None
        
        if not user:
            return
        
        platform_id = str(user.id)
        
        user_data = db.get_user('vk', platform_id)
        db.update_activity('vk', platform_id)
        db.add_command_count('vk', platform_id)
        
        if amount <= 0:
            await message.reply("❌ Сумма должна быть положительной")
            return
        
        if user_data['coins'] < amount:
            await message.reply(f"❌ Недостаточно монет! У вас {user_data['coins']} 🪙")
            return
        
        # Ищем получателя
        target_user = db.get_user_by_username('vk', target_name)
        
        if not target_user:
            await message.reply("❌ Пользователь не найден")
            return
        
        target_id = target_user[2]  # platform_id
        
        # Переводим монеты
        success, msg = db.transfer_money('vk', platform_id, 'vk', target_id, amount, "coins")
        
        if success:
            await message.reply(f"✅ {msg}\nПолучатель: {target_user[4]}")
        else:
            await message.reply(f"❌ {msg}")
    
    async def vk_cmd_payh(self, message: Message, args):
        if len(args) < 2:
            await message.reply("❌ Использование: /payh [ник] [сумма]")
            return
        
        target_name = args[0]
        try:
            amount = int(args[1])
        except:
            await message.reply("❌ Сумма должна быть числом")
            return
        
        user_id = str(message.from_id)
        user_info = await self.vk_api.users.get(user_ids=user_id)
        user = user_info[0] if user_info else None
        
        if not user:
            return
        
        platform_id = str(user.id)
        
        user_data = db.get_user('vk', platform_id)
        db.update_activity('vk', platform_id)
        db.add_command_count('vk', platform_id)
        
        if amount <= 0:
            await message.reply("❌ Сумма должна быть положительной")
            return
        
        if user_data['diamonds'] < amount:
            await message.reply(f"❌ Недостаточно алмазов! У вас {user_data['diamonds']} 💎")
            return
        
        # Ищем получателя
        target_user = db.get_user_by_username('vk', target_name)
        
        if not target_user:
            await message.reply("❌ Пользователь не найден")
            return
        
        target_id = target_user[2]  # platform_id
        
        # Переводим алмазы
        success, msg = db.transfer_money('vk', platform_id, 'vk', target_id, amount, "diamonds")
        
        if success:
            await message.reply(f"✅ {msg}\nПолучатель: {target_user[4]}")
        else:
            await message.reply(f"❌ {msg}")
    
    async def vk_cmd_privilege_commands(self, message: Message, args):
        if not args:
            await message.reply(
                "❌ Укажите привилегию:\n"
                "/cmd вип\n"
                "/cmd премиум\n"
                "/cmd лорд\n"
                "/cmd ультра\n"
                "/cmd модератор\n"
                "/cmd оператор\n"
                "/cmd анти-грифер\n"
                "/cmd легенда\n"
                "/cmd эврольд\n"
                "/cmd властелин\n"
                "/cmd титан\n"
                "/cmd терминатор\n"
                "/cmd маг\n"
                "/cmd хелпер\n"
                "/cmd создатель"
            )
            return
        
        privilege = args[0].lower()
        
        if privilege not in PRIVILEGES:
            await message.reply("❌ Неизвестная привилегия")
            return
        
        priv_data = PRIVILEGES[privilege]
        
        text = f"{priv_data['emoji']} КОМАНДЫ {privilege.upper()} {priv_data['emoji']}\n\n"
        
        for cmd in priv_data['commands']:
            text += f"▫️ {cmd}\n"
        
        if privilege in ['модератор', 'оператор', 'анти-грифер', 'хелпер']:
            text += "\n▫️ /mute [ник] [время] [причина]\n"
            text += "▫️ /warn [ник] [причина]\n"
            text += "▫️ /ban [ник] [время] [причина]\n"
            text += "▫️ /unban [ник]\n"
            text += "▫️ /banlist\n"
            text += "▫️ /mutelist\n"
            text += "▫️ /warnlist\n"
        
        if privilege == 'создатель':
            text += "\n▫️ /give [ник] [сумма]\n"
            text += "▫️ /set_privilege [ник] [привилегия]\n"
            text += "▫️ /global_ban [ник]\n"
        
        await message.reply(text)
    
    async def vk_cmd_donate(self, message: Message):
        text = "💎 ПРИВИЛЕГИИ «СПЕКТР» 💎\n\n"
        
        for priv_name, priv_data in PRIVILEGES.items():
            if priv_data['price'] > 0:
                text += f"{priv_data['emoji']} {priv_name.upper()}\n"
                text += f"└ 💰 Цена: {priv_data['price']} 🪙\n"
                text += f"└ 📅 Длительность: {priv_data['days']} дн\n"
                text += f"└ 📋 Команды: /cmd {priv_name}\n\n"
        
        text += "👑 АДМИН-ПРИВИЛЕГИИ (не продаются)\n"
        text += "модератор, оператор, анти-грифер, хелпер, создатель\n\n"
        text += f"💳 Приобрести: напишите [id{OWNER_ID_VK}|NobuCraft]"
        
        await message.reply(text)
    
    async def vk_cmd_rules(self, message: Message):
        chat_id = str(message.peer_id)
        
        db.cursor.execute("SELECT rules FROM group_settings WHERE chat_id = ? AND platform = 'vk'", (chat_id,))
        result = db.cursor.fetchone()
        rules = result[0] if result else "Правила не установлены. Админ может установить их через /set_rules"
        
        await message.reply(f"📖 ПРАВИЛА ЧАТА\n\n{rules}")
    
    async def vk_cmd_set_rules(self, message: Message, args):
        user_id = str(message.from_id)
        
        if not db.has_privilege('vk', user_id, 'модератор') and not db.has_privilege('vk', user_id, 'создатель'):
            await message.reply("❌ Недостаточно прав")
            return
        
        if not args:
            await message.reply("❌ Использование: /set_rules [текст правил]")
            return
        
        rules = " ".join(args)
        chat_id = str(message.peer_id)
        
        db.cursor.execute('''
            INSERT OR REPLACE INTO group_settings (chat_id, platform, rules)
            VALUES (?, ?, ?)
        ''', (chat_id, 'vk', rules))
        db.conn.commit()
        
        await message.reply(f"✅ Правила установлены!")
    
    async def vk_cmd_mute(self, message: Message, args):
        user_id = str(message.from_id)
        
        if not db.has_privilege('vk', user_id, 'модератор') and not db.has_privilege('vk', user_id, 'создатель'):
            await message.reply("❌ Недостаточно прав")
            return
        
        if len(args) < 2:
            await message.reply("❌ Использование: /mute [ник] [время] [причина]")
            return
        
        target_name = args[0]
        time_str = args[1]
        reason = " ".join(args[2:]) if len(args) > 2 else "Нарушение"
        
        # Парсим время
        minutes = 5
        match = re.match(r'(\d+)([мчд])', time_str)
        if match:
            value = int(match.group(1))
            unit = match.group(2)
            if unit == 'м':
                minutes = value
            elif unit == 'ч':
                minutes = value * 60
            elif unit == 'д':
                minutes = value * 1440
        else:
            try:
                minutes = int(time_str)
            except:
                minutes = 5
        
        # Ищем пользователя
        target_user = db.get_user_by_username('vk', target_name)
        
        if not target_user:
            await message.reply("❌ Пользователь не найден")
            return
        
        target_id = target_user[2]
        target_username = target_user[3] or target_user[4]
        
        mute_until = db.mute_user('vk', target_id, target_username, minutes, reason, message.from_id, user_id)
        
        await message.reply(
            f"🔇 Пользователь замучен\n\n"
            f"👤 {target_username}\n"
            f"⏱ Время: {minutes} мин\n"
            f"💬 Причина: {reason}\n"
            f"👮 Модератор: [id{user_id}|{user_id}]"
        )
    
    async def vk_cmd_unmute(self, message: Message, args):
        user_id = str(message.from_id)
        
        if not db.has_privilege('vk', user_id, 'модератор') and not db.has_privilege('vk', user_id, 'создатель'):
            await message.reply("❌ Недостаточно прав")
            return
        
        if not args:
            await message.reply("❌ Использование: /unmute [ник]")
            return
        
        target_name = args[0]
        
        target_user = db.get_user_by_username('vk', target_name)
        
        if not target_user:
            await message.reply("❌ Пользователь не найден")
            return
        
        target_id = target_user[2]
        
        db.unmute_user('vk', target_id)
        
        await message.reply(f"✅ Мут снят с {target_name}")
    
    async def vk_cmd_warn(self, message: Message, args):
        user_id = str(message.from_id)
        
        if not db.has_privilege('vk', user_id, 'модератор') and not db.has_privilege('vk', user_id, 'создатель'):
            await message.reply("❌ Недостаточно прав")
            return
        
        if len(args) < 2:
            await message.reply("❌ Использование: /warn [ник] [причина]")
            return
        
        target_name = args[0]
        reason = " ".join(args[1:])
        
        target_user = db.get_user_by_username('vk', target_name)
        
        if not target_user:
            await message.reply("❌ Пользователь не найден")
            return
        
        target_id = target_user[2]
        target_username = target_user[3] or target_user[4]
        
        warns = db.add_warn('vk', target_id, target_username, reason, message.from_id, user_id)
        
        await message.reply(
            f"⚠️ Предупреждение выдано\n\n"
            f"👤 {target_username}\n"
            f"⚠️ Варнов: {warns}/3\n"
            f"💬 Причина: {reason}\n"
            f"👮 Модератор: [id{user_id}|{user_id}]"
        )
        
        if warns >= 3:
            db.mute_user('vk', target_id, target_username, 1440, "3 предупреждения", message.from_id, user_id)
            await message.reply(f"⚠️ Пользователь получил 3 варна и замучен на 24 часа!")
    
    async def vk_cmd_ban(self, message: Message, args):
        user_id = str(message.from_id)
        
        if not db.has_privilege('vk', user_id, 'модератор') and not db.has_privilege('vk', user_id, 'создатель'):
            await message.reply("❌ Недостаточно прав")
            return
        
        if len(args) < 3:
            await message.reply("❌ Использование: /ban [ник] [время] [причина]")
            return
        
        target_name = args[0]
        duration = args[1]
        reason = " ".join(args[2:])
        
        target_user = db.get_user_by_username('vk', target_name)
        
        if not target_user:
            await message.reply("❌ Пользователь не найден")
            return
        
        target_id = target_user[2]
        target_username = target_user[3] or target_user[4]
        
        db.ban_user('vk', target_id, target_username, reason, duration, message.from_id, user_id)
        
        await message.reply(
            f"🚫 Пользователь забанен\n\n"
            f"👤 {target_username}\n"
            f"⏱ Срок: {duration}\n"
            f"💬 Причина: {reason}\n"
            f"👮 Модератор: [id{user_id}|{user_id}]"
        )
    
    async def vk_cmd_unban(self, message: Message, args):
        user_id = str(message.from_id)
        
        if not db.has_privilege('vk', user_id, 'модератор') and not db.has_privilege('vk', user_id, 'создатель'):
            await message.reply("❌ Недостаточно прав")
            return
        
        if not args:
            await message.reply("❌ Использование: /unban [ник]")
            return
        
        target_name = args[0]
        
        target_user = db.get_user_by_username('vk', target_name)
        
        if not target_user:
            await message.reply("❌ Пользователь не найден")
            return
        
        target_id = target_user[2]
        
        db.unban_user('vk', target_id)
        
        await message.reply(f"✅ Пользователь {target_name} разбанен")
    
    async def vk_cmd_banlist(self, message: Message, args):
        user_id = str(message.from_id)
        
        if not db.has_privilege('vk', user_id, 'модератор') and not db.has_privilege('vk', user_id, 'создатель'):
            await message.reply("❌ Недостаточно прав")
            return
        
        page = 1
        if args:
            try:
                page = int(args[0])
            except:
                pass
        
        bans = db.get_banned_users(page, 20)
        
        if not bans:
            await message.reply("📭 Список банов пуст")
            return
        
        text = f"🚫 СПИСОК ЗАБАНЕННЫХ (стр. {page})\n\n"
        
        for i, ban in enumerate(bans, 1):
            username = ban[3] or f"ID {ban[2]}"
            reason = ban[4] or "Не указана"
            banned_by = ban[6] or "Неизвестно"
            ban_date = ban[7][:10] if ban[7] else "Неизвестно"
            duration = "Навсегда" if ban[10] else ban[8]
            
            text += f"{i}. {username}\n"
            text += f"   ⏱ {duration}\n"
            text += f"   💬 {reason}\n"
            text += f"   👮 {banned_by}\n"
            text += f"   📅 {ban_date}\n\n"
        
        text += f"\nСтраница {page}. Для навигации: /banlist [номер]"
        
        await message.reply(text)
    
    async def vk_cmd_mutelist(self, message: Message, args):
        user_id = str(message.from_id)
        
        if not db.has_privilege('vk', user_id, 'модератор') and not db.has_privilege('vk', user_id, 'создатель'):
            await message.reply("❌ Недостаточно прав")
            return
        
        page = 1
        if args:
            try:
                page = int(args[0])
            except:
                pass
        
        mutes = db.get_muted_users(page, 20)
        
        if not mutes:
            await message.reply("📭 Список мутов пуст")
            return
        
        text = f"🔇 СПИСОК ЗАМУЧЕННЫХ (стр. {page})\n\n"
        
        for i, mute in enumerate(mutes, 1):
            username = mute[3] or f"ID {mute[2]}"
            reason = mute[4] or "Не указана"
            muted_by = mute[6] or "Неизвестно"
            mute_date = mute[7][:10] if mute[7] else "Неизвестно"
            duration = mute[8]
            
            text += f"{i}. {username}\n"
            text += f"   ⏱ {duration}\n"
            text += f"   💬 {reason}\n"
            text += f"   👮 {muted_by}\n"
            text += f"   📅 {mute_date}\n\n"
        
        text += f"\nСтраница {page}. Для навигации: /mutelist [номер]"
        
        await message.reply(text)
    
    async def vk_cmd_warnlist(self, message: Message, args):
        user_id = str(message.from_id)
        
        if not db.has_privilege('vk', user_id, 'модератор') and not db.has_privilege('vk', user_id, 'создатель'):
            await message.reply("❌ Недостаточно прав")
            return
        
        page = 1
        if args:
            try:
                page = int(args[0])
            except:
                pass
        
        warns = db.get_warned_users(page, 20)
        
        if not warns:
            await message.reply("📭 Список предупреждений пуст")
            return
        
        text = f"⚠️ СПИСОК ПРЕДУПРЕЖДЕНИЙ (стр. {page})\n\n"
        
        for i, warn in enumerate(warns, 1):
            username = warn[3] or f"ID {warn[2]}"
            reason = warn[4] or "Не указана"
            warned_by = warn[6] or "Неизвестно"
            warn_date = warn[7][:10] if warn[7] else "Неизвестно"
            count = warn[8]
            
            text += f"{i}. {username}\n"
            text += f"   ⚠️ Варн #{count}\n"
            text += f"   💬 {reason}\n"
            text += f"   👮 {warned_by}\n"
            text += f"   📅 {warn_date}\n\n"
        
        text += f"\nСтраница {page}. Для навигации: /warnlist [номер]"
        
        await message.reply(text)
    
    async def vk_cmd_sms(self, message: Message, args):
        if len(args) < 2:
            await message.reply("❌ Использование: /sms [ник] [текст]")
            return
        
        target_name = args[0]
        sms_text = " ".join(args[1:])
        
        user_id = str(message.from_id)
        user_info = await self.vk_api.users.get(user_ids=user_id)
        user = user_info[0] if user_info else None
        
        if not user:
            return
        
        # Ищем получателя
        target_user = db.get_user_by_username('vk', target_name)
        
        if not target_user:
            await message.reply("❌ Пользователь не найден")
            return
        
        target_id = target_user[2]
        
        await message.reply(f"✅ Сообщение отправлено пользователю {target_name}")
        
        try:
            await self.vk_api.messages.send(
                peer_id=int(target_id),
                message=f"💬 Личное сообщение от [id{user.id}|{user.first_name}]:\n{sms_text}",
                random_id=0
            )
        except:
            pass
    
    async def vk_cmd_eng(self, message: Message, args):
        user_id = str(message.from_id)
        
        if not args or args[0] != "free":
            await message.reply("❌ Использование: /eng free")
            return
        
        user_data = db.get_user('vk', user_id)
        
        if user_data['energy'] < 100:
            db.add_coins('vk', user_id, 50, "energy")
            await message.reply("⚡ Вы получили 50 бесплатной энергии!")
        else:
            await message.reply("❌ У вас уже достаточно энергии!")
    
    async def vk_cmd_namutebuy(self, message: Message):
        user_id = str(message.from_id)
        
        if not db.is_muted('vk', user_id):
            await message.reply("❌ Вы не замучены")
            return
        
        user_data = db.get_user('vk', user_id)
        
        if user_data['coins'] < 500:
            await message.reply(f"❌ Недостаточно монет! Нужно 500 🪙")
            return
        
        db.add_coins('vk', user_id, -500, "coins")
        db.unmute_user('vk', user_id)
        
        await message.reply("✅ Мут снят за 500 🪙")
    
    async def vk_cmd_automes(self, message: Message, args):
        user_id = str(message.from_id)
        
        if not db.has_privilege('vk', user_id, 'модератор') and not db.has_privilege('vk', user_id, 'создатель'):
            await message.reply("❌ Недостаточно прав")
            return
        
        if not args or args[0] not in ['on', 'off']:
            await message.reply("❌ Использование: /automes on/off")
            return
        
        chat_id = str(message.peer_id)
        enabled = 1 if args[0] == 'on' else 0
        
        db.cursor.execute('''
            UPDATE group_settings SET auto_message_enabled = ? WHERE chat_id = ? AND platform = 'vk'
        ''', (enabled, chat_id))
        db.conn.commit()
        
        await message.reply(f"✅ Автосообщение {'включено' if enabled else 'выключено'}")
    
    async def vk_cmd_player(self, message: Message, args):
        if not args:
            await message.reply("❌ Использование: /player [ник]")
            return
        
        target_name = args[0]
        
        target_user = db.get_user_by_username('vk', target_name)
        
        if not target_user:
            await message.reply("❌ Пользователь не найден")
            return
        
        # Получаем информацию из VK
        try:
            vk_user_info = await self.vk_api.users.get(user_ids=target_user[2])
            vk_user = vk_user_info[0] if vk_user_info else None
        except:
            vk_user = None
        
        first_name = target_user[4] or (vk_user.first_name if vk_user else "Неизвестно")
        platform_id = target_user[2]
        
        # Получаем привилегию
        privilege = target_user[13] if len(target_user) > 13 else 'user'  # privilege
        privilege_emoji = PRIVILEGES.get(privilege, {}).get('emoji', '👤') if privilege != 'user' else '👤'
        
        # Получаем последнюю активность
        last_activity = "Неизвестно"
        if target_user[20]:  # last_activity
            last = datetime.datetime.fromisoformat(target_user[20])
            delta = datetime.datetime.now() - last
            if delta.days > 0:
                last_activity = f"{delta.days} дн назад"
            elif delta.seconds > 3600:
                last_activity = f"{delta.seconds // 3600} ч назад"
            elif delta.seconds > 60:
                last_activity = f"{delta.seconds // 60} мин назад"
            else:
                last_activity = "только что"
        
        text = (
            f"╔══════════════════════════════╗\n"
            f"║   👤 ПРОФИЛЬ ИГРОКА           ║\n"
            f"╚══════════════════════════════╝\n\n"
            
            f"[id{platform_id}|{first_name}] {privilege_emoji}\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"РЕСУРСЫ\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🪙 Монеты: {target_user[6]:,}\n"
            f"💎 Алмазы: {target_user[7]:,}\n"
            f"🔮 Кристаллы: {target_user[8]:,}\n"
            f"💀 Черепки: {target_user[9]}\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"ХАРАКТЕРИСТИКИ\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"❤️ Здоровье: {target_user[16]}/{target_user[17]}\n"
            f"⚔️ Урон: {target_user[19]}\n"
            f"🛡 Броня: {target_user[18]}\n"
            f"⚡ Энергия: {target_user[10]}\n"
            f"📊 Уровень: {target_user[11]}\n"
            f"👾 Боссов убито: {target_user[20]}\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"СТАТИСТИКА\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📝 Сообщений: {target_user[24]}\n"
            f"⌨️ Команд: {target_user[25]}\n"
            f"🎮 Игр: {target_user[26]}\n"
            f"⭐ Репутация: {target_user[27]}\n"
            f"⏱ Последний визит: {last_activity}\n"
            f"📅 Первое появление: {target_user[23][:10] if target_user[23] else 'Неизвестно'}"
        )
        
        await message.reply(text)
    
    async def vk_cmd_add_bookmark(self, message: Message, args):
        if not args:
            await message.reply("❌ Использование: +закладка [описание]")
            return
        
        description = " ".join(args)
        user_id = str(message.from_id)
        
        # Получаем ссылку на сообщение
        message_link = f"https://vk.com/im?sel={user_id}&msgid={message.conversation_message_id}"
        
        db.add_bookmark('vk', user_id, description, message_link, message.text)
        
        await message.reply(f"✅ Закладка создана: {description}")
    
    async def vk_cmd_bookmarks(self, message: Message, args):
        user_id = str(message.from_id)
        
        bookmarks = db.get_bookmarks('vk', user_id)
        
        if not bookmarks:
            await message.reply("📭 У вас нет закладок")
            return
        
        if args:
            try:
                num = int(args[0])
                if 1 <= num <= len(bookmarks):
                    bookmark = bookmarks[num-1]
                    await message.reply(
                        f"📌 Закладка #{num}\n\n"
                        f"Описание: {bookmark[3]}\n"
                        f"Дата: {bookmark[5][:16]}\n"
                        f"Ссылка: {bookmark[4]}"
                    )
                    return
            except:
                pass
        
        text = "📌 ВАШИ ЗАКЛАДКИ\n\n"
        
        for i, bookmark in enumerate(bookmarks, 1):
            text += f"{i}. {bookmark[3]} — {bookmark[5][:16]}\n"
        
        text += "\nДля просмотра: закладки [номер]"
        
        await message.reply(text)
    
    async def vk_cmd_my_article(self, message: Message):
        # Список статей УК РФ
        articles = [
            "105. Убийство",
            "111. Умышленное причинение тяжкого вреда здоровью",
            "112. Умышленное причинение средней тяжести вреда здоровью",
            "115. Умышленное причинение легкого вреда здоровью",
            "116. Побои",
            "119. Угроза убийством",
            "126. Похищение человека",
            "127. Незаконное лишение свободы",
            "131. Изнасилование",
            "132. Насильственные действия сексуального характера",
            "158. Кража",
            "159. Мошенничество",
            "160. Присвоение или растрата",
            "161. Грабеж",
            "162. Разбой",
            "163. Вымогательство",
            "166. Неправомерное завладение автомобилем",
            "167. Умышленное уничтожение имущества",
            "205. Террористический акт",
            "206. Захват заложника",
            "207. Заведомо ложное сообщение об акте терроризма",
            "213. Хулиганство",
            "214. Вандализм",
            "222. Незаконный оборот оружия",
            "228. Незаконный оборот наркотиков",
            "261. Уничтожение или повреждение лесных насаждений",
            "282. Возбуждение ненависти либо вражды",
            "290. Получение взятки",
            "291. Дача взятки",
            "319. Оскорбление представителя власти"
        ]
        
        article = random.choice(articles)
        user_id = str(message.from_id)
        user_info = await self.vk_api.users.get(user_ids=user_id)
        user = user_info[0] if user_info else None
        
        if user:
            days = random.randint(1, 30)
            text = f"🤷‍♂️ Сегодня [id{user.id}|{user.first_name}] приговаривается к статье {article} на срок {days} день"
            await message.reply(text)
    
    async def vk_cmd_whoami(self, message: Message):
        user_id = str(message.from_id)
        user_info = await self.vk_api.users.get(user_ids=user_id)
        user = user_info[0] if user_info else None
        
        if not user:
            return
        
        user_data = db.get_user('vk', user_id, user.domain or "", user.first_name, user.last_name or "")
        
        # Получаем привилегию
        privilege = user_data.get('privilege', 'user')
        privilege_emoji = PRIVILEGES.get(privilege, {}).get('emoji', '👤') if privilege != 'user' else '👤'
        
        # Получаем награды
        awards = db.get_awards('vk', user_id)
        awards_text = ""
        if awards:
            awards_text = "🏅 Награды:\n"
            for award in awards[:3]:
                awards_text += f"   • {award[3]}\n"
        
        # Получаем описание
        description = user_data.get('description', '')
        if description:
            description = f"📝 Описание: {description}\n"
        
        # Получаем первое появление
        first_seen = user_data.get('first_seen', '')
        if first_seen:
            first_date = datetime.datetime.fromisoformat(first_seen)
            now = datetime.datetime.now()
            delta = now - first_date
            years = delta.days // 365
            months = (delta.days % 365) // 30
            days = delta.days % 30
            
            first_seen_text = f"{first_date.strftime('%d.%m.%Y')} ({years} г {months} мес {days} дн)"
        else:
            first_seen_text = "Неизвестно"
        
        # Получаем последнюю активность
        last_activity = user_data.get('last_activity', '')
        if last_activity:
            last = datetime.datetime.fromisoformat(last_activity)
            delta = datetime.datetime.now() - last
            if delta.days > 0:
                last_activity_text = f"{delta.days} дн назад"
            elif delta.seconds > 3600:
                last_activity_text = f"{delta.seconds // 3600} ч назад"
            elif delta.seconds > 60:
                last_activity_text = f"{delta.seconds // 60} мин назад"
            else:
                last_activity_text = "только что"
        else:
            last_activity_text = "Неизвестно"
        
        text = (
            f"Это [id{user.id}|{user.first_name}]\n"
            f"{privilege_emoji} [{user_data['level']}] Ранг: {privilege.upper() if privilege != 'user' else 'Пользователь'}\n"
            f"Репутация: ✨ {user_data['reputation']} | ➕ {user_data['reputation_given']}\n"
            f"{description}"
            f"Первое появление: {first_seen_text}\n"
            f"Последний актив: {last_activity_text}\n"
            f"Актив (д|н|м|весь): {user_data['messages_count']} | {user_data['commands_used']} | {user_data['games_played']} | {delta.days if 'delta' in locals() else 0}\n"
            f"{awards_text}"
        )
        
        await message.reply(text)
    
    # ===================== ЗАПУСК БОТОВ =====================
    async def run(self):
        # Запуск Telegram бота
        if self.tg_application:
            await self.tg_application.initialize()
            await self.tg_application.start()
            await self.tg_application.updater.start_polling()
            logger.info("🚀 Telegram бот запущен!")
        
        # Запуск VK бота отдельно
        if self.vk_bot:
            logger.info("🚀 VK бот запускается...")
            # Запускаем VK бот в отдельной задаче
            asyncio.create_task(self.vk_bot.run_polling())
            logger.info("🚀 VK бот запущен!")
        
        # Держим бот активным
        while True:
            await asyncio.sleep(1)
    
    async def close(self):
        if self.tg_application:
            await self.tg_application.stop()
        if self.vk_bot:
            # В vkbottle нет прямого метода stop, но мы можем просто позволить задаче завершиться
            logger.info("VK бот остановлен")
        db.close()
        logger.info("👋 Боты остановлены")

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
