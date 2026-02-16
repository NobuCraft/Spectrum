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
import requests
from io import BytesIO
import base64

# --- Библиотеки для Telegram ---
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from telegram.error import TelegramError

# --- Библиотеки для VK ---
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.utils import get_random_id
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== КОНФИГУРАЦИЯ ==========
# --- Telegram ---
TELEGRAM_TOKEN = "8326390250:AAFuUVHZ6ucUtLy132Ep1pmteRr6tTk7u0Q"
OWNER_ID = 1732658530
OWNER_USERNAME = "@NobuCraft"

# --- VK ---
VK_GROUP_TOKEN = "vk1.a.sl7q9qebmFwqxkdpMVJTQpLWUtLMsKYPvVInyidaBe1GwkuxkDewfvYss7AcGYPlbw817In-UDgILA38ltHafX3p-t0_xaNWPwXOPpwPezMqq89fx1y9ru6lyde_qFYtu-ll3J-1_vBPPCZ0fHyh4j8qxkiXWCVBgFKtkNhqukNIFTbWqMjX57iMIPbawIdYOr_ngdaXRuGXZAAxzffhbg"
VK_GROUP_ID = 212157160  # ID твоего сообщества (без минуса)
OWNER_VK_ID = 713616259

# --- Hugging Face AI (твой токен) ---
HUGGINGFACE_TOKEN = "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"
HF_MODEL = "mistralai/Mistral-7B-Instruct-v0.1"
HF_IMAGE_MODEL = "black-forest-labs/FLUX.1-schnell"

# Настройки
SPAM_LIMIT = 5
SPAM_WINDOW = 3
SPAM_MUTE_TIME = 120

# Цены и длительности
VIP_PRICE = 5000
PREMIUM_PRICE = 15000
DIAMOND_PRICE = 100

VIP_DAYS = 30
PREMIUM_DAYS = 30

# ========== БАЗА ДАННЫХ ==========
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
            
            required_columns = {
                'role': "ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'",
                'warns': "ALTER TABLE users ADD COLUMN warns INTEGER DEFAULT 0",
                'mute_until': "ALTER TABLE users ADD COLUMN mute_until TIMESTAMP",
                'banned': "ALTER TABLE users ADD COLUMN banned INTEGER DEFAULT 0",
                'health': "ALTER TABLE users ADD COLUMN health INTEGER DEFAULT 100",
                'armor': "ALTER TABLE users ADD COLUMN armor INTEGER DEFAULT 0",
                'damage': "ALTER TABLE users ADD COLUMN damage INTEGER DEFAULT 10",
                'boss_kills': "ALTER TABLE users ADD COLUMN boss_kills INTEGER DEFAULT 0",
                'vip_until': "ALTER TABLE users ADD COLUMN vip_until TIMESTAMP",
                'premium_until': "ALTER TABLE users ADD COLUMN premium_until TIMESTAMP",
                'clan_id': "ALTER TABLE users ADD COLUMN clan_id INTEGER DEFAULT 0",
                'clan_role': "ALTER TABLE users ADD COLUMN clan_role TEXT DEFAULT 'member'",
                'mafia_wins': "ALTER TABLE users ADD COLUMN mafia_wins INTEGER DEFAULT 0",
                'mafia_games': "ALTER TABLE users ADD COLUMN mafia_games INTEGER DEFAULT 0",
                'rps_wins': "ALTER TABLE users ADD COLUMN rps_wins INTEGER DEFAULT 0",
                'rps_losses': "ALTER TABLE users ADD COLUMN rps_losses INTEGER DEFAULT 0",
                'rps_draws': "ALTER TABLE users ADD COLUMN rps_draws INTEGER DEFAULT 0",
                'casino_wins': "ALTER TABLE users ADD COLUMN casino_wins INTEGER DEFAULT 0",
                'casino_losses': "ALTER TABLE users ADD COLUMN casino_losses INTEGER DEFAULT 0",
                'rr_wins': "ALTER TABLE users ADD COLUMN rr_wins INTEGER DEFAULT 0",
                'rr_losses': "ALTER TABLE users ADD COLUMN rr_losses INTEGER DEFAULT 0",
                'rr_games': "ALTER TABLE users ADD COLUMN rr_games INTEGER DEFAULT 0",
                'rr_money': "ALTER TABLE users ADD COLUMN rr_money INTEGER DEFAULT 100",
                'ttt_wins': "ALTER TABLE users ADD COLUMN ttt_wins INTEGER DEFAULT 0",
                'ttt_losses': "ALTER TABLE users ADD COLUMN ttt_losses INTEGER DEFAULT 0",
                'ttt_draws': "ALTER TABLE users ADD COLUMN ttt_draws INTEGER DEFAULT 0",
                'cases': "ALTER TABLE users ADD COLUMN cases INTEGER DEFAULT 0",
                'keys': "ALTER TABLE users ADD COLUMN keys INTEGER DEFAULT 0",
                'gender': "ALTER TABLE users ADD COLUMN gender TEXT DEFAULT 'unknown'",
                'nickname': "ALTER TABLE users ADD COLUMN nickname TEXT",
                'birthday': "ALTER TABLE users ADD COLUMN birthday TEXT",
                'city': "ALTER TABLE users ADD COLUMN city TEXT",
                'bio': "ALTER TABLE users ADD COLUMN bio TEXT",
                'marry_id': "ALTER TABLE users ADD COLUMN marry_id INTEGER DEFAULT 0",
                'marry_date': "ALTER TABLE users ADD COLUMN marry_date TIMESTAMP",
                'love_points': "ALTER TABLE users ADD COLUMN love_points INTEGER DEFAULT 0",
                'children': "ALTER TABLE users ADD COLUMN children INTEGER DEFAULT 0",
                'rep': "ALTER TABLE users ADD COLUMN rep INTEGER DEFAULT 0",
                'warns_count': "ALTER TABLE users ADD COLUMN warns_count INTEGER DEFAULT 0",
                'mutes_count': "ALTER TABLE users ADD COLUMN mutes_count INTEGER DEFAULT 0",
                'bans_count': "ALTER TABLE users ADD COLUMN bans_count INTEGER DEFAULT 0",
                'last_seen': "ALTER TABLE users ADD COLUMN last_seen TIMESTAMP",
                'voice_count': "ALTER TABLE users ADD COLUMN voice_count INTEGER DEFAULT 0",
                'photo_count': "ALTER TABLE users ADD COLUMN photo_count INTEGER DEFAULT 0",
                'sticker_count': "ALTER TABLE users ADD COLUMN sticker_count INTEGER DEFAULT 0",
                'referrals': "ALTER TABLE users ADD COLUMN referrals INTEGER DEFAULT 0",
                'referral_link': "ALTER TABLE users ADD COLUMN referral_link TEXT",
                'daily_streak': "ALTER TABLE users ADD COLUMN daily_streak INTEGER DEFAULT 0",
                'last_daily': "ALTER TABLE users ADD COLUMN last_daily TIMESTAMP",
                'diamonds': "ALTER TABLE users ADD COLUMN diamonds INTEGER DEFAULT 0",
                'active_days': "ALTER TABLE users ADD COLUMN active_days INTEGER DEFAULT 0",
                'active_weeks': "ALTER TABLE users ADD COLUMN active_weeks INTEGER DEFAULT 0",
                'active_months': "ALTER TABLE users ADD COLUMN active_months INTEGER DEFAULT 0",
                'total_active_days': "ALTER TABLE users ADD COLUMN total_active_days INTEGER DEFAULT 0",
                'automes_enabled': "ALTER TABLE users ADD COLUMN automes_enabled INTEGER DEFAULT 0",
                'platform': "ALTER TABLE users ADD COLUMN platform TEXT DEFAULT 'tg'",
                'platform_id': "ALTER TABLE users ADD COLUMN platform_id TEXT",
            }
            
            for col, sql in required_columns.items():
                if col not in columns:
                    self.cursor.execute(sql)
            
            self.conn.commit()
        except Exception as e:
            print(f"Ошибка миграции: {e}")
    
    def create_tables(self):
        # Основная таблица пользователей
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                coins INTEGER DEFAULT 1000,
                diamonds INTEGER DEFAULT 0,
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
                vip_until TIMESTAMP,
                premium_until TIMESTAMP,
                clan_id INTEGER DEFAULT 0,
                clan_role TEXT DEFAULT 'member',
                mafia_wins INTEGER DEFAULT 0,
                mafia_games INTEGER DEFAULT 0,
                rps_wins INTEGER DEFAULT 0,
                rps_losses INTEGER DEFAULT 0,
                rps_draws INTEGER DEFAULT 0,
                casino_wins INTEGER DEFAULT 0,
                casino_losses INTEGER DEFAULT 0,
                rr_wins INTEGER DEFAULT 0,
                rr_losses INTEGER DEFAULT 0,
                rr_games INTEGER DEFAULT 0,
                rr_money INTEGER DEFAULT 100,
                ttt_wins INTEGER DEFAULT 0,
                ttt_losses INTEGER DEFAULT 0,
                ttt_draws INTEGER DEFAULT 0,
                cases INTEGER DEFAULT 0,
                keys INTEGER DEFAULT 0,
                gender TEXT DEFAULT 'unknown',
                nickname TEXT,
                birthday TEXT,
                city TEXT,
                bio TEXT,
                marry_id INTEGER DEFAULT 0,
                marry_date TIMESTAMP,
                love_points INTEGER DEFAULT 0,
                children INTEGER DEFAULT 0,
                rep INTEGER DEFAULT 0,
                warns_count INTEGER DEFAULT 0,
                mutes_count INTEGER DEFAULT 0,
                bans_count INTEGER DEFAULT 0,
                last_seen TIMESTAMP,
                voice_count INTEGER DEFAULT 0,
                photo_count INTEGER DEFAULT 0,
                sticker_count INTEGER DEFAULT 0,
                referrals INTEGER DEFAULT 0,
                referral_link TEXT,
                daily_streak INTEGER DEFAULT 0,
                last_daily TIMESTAMP,
                active_days INTEGER DEFAULT 0,
                active_weeks INTEGER DEFAULT 0,
                active_months INTEGER DEFAULT 0,
                total_active_days INTEGER DEFAULT 0,
                automes_enabled INTEGER DEFAULT 0,
                platform TEXT DEFAULT 'tg',
                platform_id TEXT,
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
                boss_image TEXT,
                is_alive INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Кланы
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS clans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                owner_id INTEGER,
                level INTEGER DEFAULT 1,
                exp INTEGER DEFAULT 0,
                members INTEGER DEFAULT 1,
                rating INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Члены клана
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
        
        # Инвентарь
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                item_name TEXT,
                item_type TEXT,
                item_desc TEXT,
                quantity INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Питомцы
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS pets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER,
                pet_name TEXT,
                pet_type TEXT,
                health INTEGER DEFAULT 100,
                max_health INTEGER DEFAULT 100,
                attack INTEGER DEFAULT 10,
                experience INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                created_at TIMESTAMP,
                FOREIGN KEY (owner_id) REFERENCES users (user_id)
            )
        ''')
        
        # Закладки
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                text TEXT,
                message_link TEXT,
                created_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        self.conn.commit()
    
    def init_data(self):
        self.init_bosses()
    
    def init_bosses(self):
        self.cursor.execute("SELECT * FROM bosses")
        if not self.cursor.fetchone():
            bosses_data = [
                ("🦟 Ядовитый комар", 5, 500, 15, 250, ""),
                ("🌲 Лесной тролль", 10, 1000, 25, 500, ""),
                ("🐉 Огненный дракон", 15, 2000, 40, 1000, ""),
                ("❄️ Ледяной великан", 20, 3500, 60, 2000, ""),
                ("👾 Король демонов", 25, 5000, 85, 3500, ""),
                ("💀 Бог разрушения", 30, 10000, 150, 5000, "")
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
    
    def get_or_create_user(self, platform: str, platform_id: str, first_name: str = "Player") -> Dict:
        """Получает или создает пользователя по платформе и ID"""
        # Ищем по платформе и platform_id
        self.cursor.execute(
            "SELECT * FROM users WHERE platform = ? AND platform_id = ?",
            (platform, platform_id)
        )
        user = self.cursor.fetchone()
        
        if not user:
            # Создаем нового пользователя
            role = 'owner' if (platform == 'tg' and int(platform_id) == OWNER_ID) or (platform == 'vk' and int(platform_id) == OWNER_VK_ID) else 'user'
            self.cursor.execute('''
                INSERT INTO users (platform, platform_id, first_name, role, referral_link, last_seen) 
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (platform, platform_id, first_name, role, f"ref_{platform}_{platform_id}_{int(time.time())}", datetime.datetime.now()))
            
            user_id = self.cursor.lastrowid
            
            self.cursor.execute('''
                INSERT INTO stats (user_id) VALUES (?)
            ''', (user_id,))
            
            self.conn.commit()
            return self.get_user_by_id(user_id)
        
        # Обновляем last_seen
        self.cursor.execute(
            "UPDATE users SET last_seen = ? WHERE platform = ? AND platform_id = ?",
            (datetime.datetime.now(), platform, platform_id)
        )
        self.conn.commit()
        
        # Получаем полные данные
        return self.get_user_by_id(user[0])
    
    def get_user_by_id(self, user_id: int) -> Dict:
        self.cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = self.cursor.fetchone()
        if not user:
            return {}
        
        columns = [description[0] for description in self.cursor.description]
        return dict(zip(columns, user))
    
    def get_user_by_name(self, name_query: str, platform: str = None) -> Optional[Dict]:
        """Ищет пользователя по нику или имени"""
        self.cursor.execute(
            "SELECT user_id FROM users WHERE nickname = ? OR first_name LIKE ? ORDER BY last_seen DESC LIMIT 1",
            (name_query, f'%{name_query}%')
        )
        result = self.cursor.fetchone()
        if result:
            return self.get_user_by_id(result[0])
        return None
    
    def get_user_by_platform_id(self, platform: str, platform_id: str) -> Optional[Dict]:
        self.cursor.execute(
            "SELECT user_id FROM users WHERE platform = ? AND platform_id = ?",
            (platform, platform_id)
        )
        result = self.cursor.fetchone()
        if result:
            return self.get_user_by_id(result[0])
        return None
    
    def get_players_count(self) -> int:
        self.cursor.execute("SELECT COUNT(*) FROM users")
        return self.cursor.fetchone()[0]
    
    def add_coins(self, user_id: int, coins: int):
        self.cursor.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (coins, user_id))
        self.conn.commit()
    
    def add_diamonds(self, user_id: int, amount: int):
        self.cursor.execute("UPDATE users SET diamonds = diamonds + ? WHERE user_id = ?", (amount, user_id))
        self.conn.commit()
    
    def add_exp(self, user_id: int, exp: int):
        self.cursor.execute("UPDATE users SET exp = exp + ? WHERE user_id = ?", (exp, user_id))
        
        self.cursor.execute("SELECT exp, level FROM users WHERE user_id = ?", (user_id,))
        user = self.cursor.fetchone()
        
        if user:
            exp_needed = user[1] * 100
            if user[0] >= exp_needed:
                self.cursor.execute("UPDATE users SET level = level + 1, exp = exp - ? WHERE user_id = ?", (exp_needed, user_id))
        
        self.conn.commit()
    
    def add_energy(self, user_id: int, energy: int):
        self.cursor.execute("UPDATE users SET energy = energy + ? WHERE user_id = ?", (energy, user_id))
        self.conn.commit()
    
    def damage(self, user_id: int, amount: int):
        self.cursor.execute("UPDATE users SET health = health - ? WHERE user_id = ?", (amount, user_id))
        self.conn.commit()
    
    def heal(self, user_id: int, amount: int):
        current_health = self.get_user_by_id(user_id).get('health', 100)
        new_health = min(100, current_health + amount)
        self.cursor.execute("UPDATE users SET health = ? WHERE user_id = ?", (new_health, user_id))
        self.conn.commit()
    
    def mute_user(self, user_id: int, minutes: int, admin_id: int = None, reason: str = "Спам"):
        mute_until = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
        self.cursor.execute("UPDATE users SET mute_until = ?, mutes_count = mutes_count + 1 WHERE user_id = ?", (mute_until, user_id))
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
        self.cursor.execute("UPDATE users SET warns = warns + 1, warns_count = warns_count + 1 WHERE user_id = ?", (user_id,))
        self.conn.commit()
        
        self.cursor.execute("SELECT warns FROM users WHERE user_id = ?", (user_id,))
        warns = self.cursor.fetchone()[0]
        
        if warns >= 3:
            self.mute_user(user_id, 1440, admin_id, "3 предупреждения")
            return f"⚠️ Пользователь получил 3 варна и был замучен на 24 часа!"
        return f"⚠️ Пользователь получил варн ({warns}/3)"
    
    def ban_user(self, user_id: int, admin_id: int, reason: str = "Нарушение"):
        self.cursor.execute("UPDATE users SET banned = 1, bans_count = bans_count + 1 WHERE user_id = ?", (user_id,))
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
    
    def get_banlist(self, page=1, limit=10):
        offset = (page - 1) * limit
        self.cursor.execute('''
            SELECT user_id, first_name, banned, bans_count, last_seen 
            FROM users WHERE banned = 1 ORDER BY last_seen DESC LIMIT ? OFFSET ?
        ''', (limit, offset))
        return self.cursor.fetchall()
    
    def get_mutelist(self, page=1, limit=10):
        offset = (page - 1) * limit
        self.cursor.execute('''
            SELECT user_id, first_name, mute_until, mutes_count 
            FROM users WHERE mute_until IS NOT NULL AND mute_until > ? ORDER BY mute_until DESC LIMIT ? OFFSET ?
        ''', (datetime.datetime.now(), limit, offset))
        return self.cursor.fetchall()
    
    def get_warnlist(self, page=1, limit=10):
        offset = (page - 1) * limit
        self.cursor.execute('''
            SELECT user_id, first_name, warns, warns_count 
            FROM users WHERE warns > 0 ORDER BY warns DESC LIMIT ? OFFSET ?
        ''', (limit, offset))
        return self.cursor.fetchall()
    
    def add_bookmark(self, user_id: int, text: str, message_link: str):
        self.cursor.execute('''
            INSERT INTO bookmarks (user_id, text, message_link, created_at)
            VALUES (?, ?, ?, ?)
        ''', (user_id, text, message_link, datetime.datetime.now()))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_bookmarks(self, user_id: int):
        self.cursor.execute("SELECT id, text, message_link, created_at FROM bookmarks WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        return self.cursor.fetchall()
    
    def create_pet(self, user_id: int, pet_name: str, pet_type: str):
        self.cursor.execute('''
            INSERT INTO pets (owner_id, pet_name, pet_type, health, max_health, attack, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, pet_name, pet_type, 100, 100, random.randint(10, 20), datetime.datetime.now()))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_user_pets(self, user_id: int):
        self.cursor.execute("SELECT * FROM pets WHERE owner_id = ?", (user_id,))
        return self.cursor.fetchall()
    
    def feed_pet(self, pet_id: int):
        self.cursor.execute("UPDATE pets SET health = max_health WHERE id = ?", (pet_id,))
        self.conn.commit()
    
    def add_daily_streak(self, user_id: int) -> int:
        today = datetime.datetime.now().date()
        self.cursor.execute("SELECT last_daily, daily_streak FROM users WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()
        
        if result and result[0]:
            last = datetime.datetime.fromisoformat(result[0]).date()
            if last == today - datetime.timedelta(days=1):
                streak = result[1] + 1
            elif last == today:
                return result[1]
            else:
                streak = 1
        else:
            streak = 1
        
        self.cursor.execute("UPDATE users SET daily_streak = ?, last_daily = ? WHERE user_id = ?", (streak, datetime.datetime.now(), user_id))
        self.conn.commit()
        return streak
    
    def close(self):
        self.conn.close()

# Инициализация БД
db = Database()

# ========== УМНЫЙ ИИ (Hugging Face) ==========
class HuggingFaceAI:
    def __init__(self, token: str, model: str = HF_MODEL):
        self.api_key = token
        self.model = model
        self.api_url = f"https://api-inference.huggingface.co/models/{self.model}"
        self.image_api_url = f"https://api-inference.huggingface.co/models/{HF_IMAGE_MODEL}"
        self.session = None
        self.contexts = defaultdict(list)
        logger.info(f"🤖 HuggingFace AI инициализирован с моделью {self.model}")

    async def get_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession(headers={"Authorization": f"Bearer {self.api_key}"})
        return self.session

    async def get_response(self, user_id: int, message: str, platform: str = "tg") -> str:
        try:
            session = await self.get_session()

            system_prompt = (
                "Ты — СПЕКТР (Spectrum), умный, дерзкий, саркастичный, но дружелюбный кибер-спутник. "
                "Ты помогаешь с играми, кланами, экономикой и просто общаешься. Ты — лучший друг для пользователя. "
                "Любишь подкалывать, но в меру. Отвечай кратко, но по делу, используй эмодзи. "
                f"Сейчас с тобой говорит пользователь платформы {'Telegram' if platform=='tg' else 'ВКонтакте'}."
            )

            if user_id not in self.contexts:
                self.contexts[user_id] = [
                    {"role": "system", "content": system_prompt}
                ]

            self.contexts[user_id].append({"role": "user", "content": message})

            if len(self.contexts[user_id]) > 11:
                self.contexts[user_id] = [self.contexts[user_id][0]] + self.contexts[user_id][-10:]

            # Форматируем историю для модели
            formatted_messages = []
            for msg in self.contexts[user_id]:
                if msg['role'] == 'system':
                    formatted_messages.append(f"<s>[INST] {msg['content']} [/INST]</s>")
                elif msg['role'] == 'user':
                    formatted_messages.append(f"[INST] {msg['content']} [/INST]")
                else:
                    formatted_messages.append(f" {msg['content']} </s><s>")

            full_prompt = " ".join(formatted_messages)

            payload = {
                "inputs": full_prompt,
                "parameters": {
                    "max_new_tokens": 250,
                    "temperature": 0.8,
                    "top_p": 0.95,
                    "do_sample": True,
                    "return_full_text": False
                }
            }

            async with session.post(self.api_url, json=payload, timeout=30) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if isinstance(result, list) and len(result) > 0:
                        ai_response = result[0].get('generated_text', '').strip()
                    else:
                        ai_response = result.get('generated_text', '').strip()

                    if ai_response:
                        ai_response = re.sub(r'\[/INST\]|</s>|<s>|\[INST\]', '', ai_response).strip()
                        self.contexts[user_id].append({"role": "assistant", "content": ai_response})
                        return ai_response
                else:
                    error_text = await resp.text()
                    logger.error(f"Ошибка HuggingFace API: {resp.status} - {error_text}")
                    return await self.try_fallback_model(user_id, message, platform)

        except asyncio.TimeoutError:
            logger.error("Таймаут при запросе к HuggingFace")
            return "🤖 ИИ немного тормозит... Попробуй еще раз через минутку."
        except Exception as e:
            logger.error(f"Ошибка HuggingFace: {e}")
            return None
        return None

    async def try_fallback_model(self, user_id: int, message: str, platform: str) -> Optional[str]:
        fallback_models = [
            "microsoft/DialoGPT-medium",
            "google/flan-t5-base"
        ]
        for model in fallback_models:
            try:
                logger.info(f"Пробую запасную модель: {model}")
                fallback_url = f"https://api-inference.huggingface.co/models/{model}"
                payload = {"inputs": message}
                session = await self.get_session()
                async with session.post(fallback_url, json=payload, timeout=15) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        if isinstance(result, list) and len(result) > 0:
                            if 'generated_text' in result[0]:
                                return result[0]['generated_text']
                            elif isinstance(result[0], dict) and 'text' in result[0]:
                                return result[0]['text']
                    break
            except:
                continue
        return None

    async def generate_image(self, prompt: str) -> Optional[bytes]:
        try:
            session = await self.get_session()
            payload = {"inputs": prompt}
            async with session.post(self.image_api_url, json=payload, timeout=60) as resp:
                if resp.status == 200:
                    return await resp.read()
                else:
                    logger.error(f"Ошибка генерации картинки: {resp.status}")
                    return None
        except Exception as e:
            logger.error(f"Ошибка при генерации картинки: {e}")
            return None

    async def close(self):
        if self.session:
            await self.session.close()

# ========== ОСНОВНОЙ ИГРОВОЙ КЛАСС ==========
class GameBot:
    def __init__(self, db_instance: Database, ai_instance: HuggingFaceAI):
        self.db = db_instance
        self.ai = ai_instance
        self.spam_tracker = defaultdict(list)
        self.inactive_alerts = {}  # Для отслеживания неактивных
        logger.info("✅ Игровое ядро «СПЕКТР» инициализировано")

    def has_permission(self, user_data: Dict, required_role: str) -> bool:
        role_hierarchy = ['user', 'vip', 'premium', 'lord', 'ultra', 'moderator', 
                         'operator', 'anti-griefer', 'legend', 'overlord', 'sovereign', 
                         'titan', 'terminator', 'mage', 'helper', 'creator', 'admin', 'owner']
        
        user_role = user_data.get('role', 'user')
        if user_role not in role_hierarchy:
            return False
        
        user_level = role_hierarchy.index(user_role)
        required_level = role_hierarchy.index(required_role)
        return user_level >= required_level

    def get_role_emoji(self, role: str) -> str:
        emojis = {
            'owner': '👑', 'admin': '⚜️', 'creator': '⭐', 'helper': '🌀', 'mage': '⚡',
            'terminator': '🦈', 'titan': '🐲', 'sovereign': '🐋', 'overlord': '👾',
            'legend': '🐝', 'anti-griefer': '🐙', 'operator': '🐌', 'moderator': '🐠',
            'ultra': '🦅', 'lord': '🦀', 'premium': '🐊', 'vip': '🐛', 'user': '👤'
        }
        return emojis.get(role, '👤')

    async def check_spam(self, user_data: Dict) -> bool:
        user_id = user_data['user_id']
        if self.has_permission(user_data, 'premium'):
            return False
        
        current_time = time.time()
        self.spam_tracker[user_id] = [t for t in self.spam_tracker[user_id] if current_time - t < SPAM_WINDOW]
        self.spam_tracker[user_id].append(current_time)
        
        return len(self.spam_tracker[user_id]) > SPAM_LIMIT

    async def process_command(self, platform: str, platform_user_id: str, command: str, 
                            args: List[str], message_text: str = "", photo_bytes: bytes = None) -> Tuple[Optional[str], Optional[List], Optional[bytes]]:
        """Главный метод обработки команд"""
        
        user_data = self.db.get_or_create_user(platform, platform_user_id, f"Player_{platform_user_id[-4:]}")
        
        # Проверка на бан
        if self.db.is_banned(user_data['user_id']):
            return "🚫 Вы забанены в боте.", None, None
        
        # Проверка на мут
        if self.db.is_muted(user_data['user_id']):
            remaining = self.db.get_mute_time(user_data['user_id'])
            return f"🔇 Вы замучены. Осталось: {remaining}", None, None
        
        # Обработка обычных сообщений (не команд)
        if not command:
            if await self.check_spam(user_data):
                self.db.mute_user(user_data['user_id'], SPAM_MUTE_TIME, 0, "Автоматический спам")
                return f"🚫 Спам-фильтр. Вы замучены на {SPAM_MUTE_TIME} минут.", None, None
            
            # Проверка на неактивность
            last_seen = user_data.get('last_seen')
            if last_seen:
                last_seen_dt = datetime.datetime.fromisoformat(last_seen)
                days_inactive = (datetime.datetime.now() - last_seen_dt).days
                if days_inactive > 30 and user_data['user_id'] not in self.inactive_alerts:
                    self.inactive_alerts[user_data['user_id']] = True
                    name = user_data.get('first_name', 'Пользователь')
                    return f"⚡️⚡️⚡️ Святые угодники!\n[{platform}:{platform_user_id}|{name}] заговорил после более, чем месячного молчания!!! Поприветствуйте молчуна! 👏", None, None
            
            # Отправляем в ИИ
            ai_response = await self.ai.get_response(user_data['user_id'], message_text, platform)
            if ai_response:
                return f"🤖 **СПЕКТР:** {ai_response}", None, None
            else:
                return self.simple_response(message_text), None, None
        
        # Обработка команд
        cmd = command.lower()
        
        # === ОСНОВНЫЕ КОМАНДЫ ===
        if cmd in ["start", "help"]:
            return self.cmd_help(user_data), self.get_main_menu_keyboard(), None
        
        elif cmd == "menu":
            return "🎮 **ГЛАВНОЕ МЕНЮ**\n\nВыбери раздел:", self.get_main_menu_keyboard(), None
        
        elif cmd in ["profile", "whois", "player"]:
            return self.cmd_profile(user_data, args, platform), None, None
        
        elif cmd == "editprofile":
            return self.cmd_edit_profile(), None, None
        
        elif cmd == "top":
            return self.cmd_top(), None, None
        
        elif cmd == "daily":
            return self.cmd_daily(user_data), None, None
        
        elif cmd == "weekly":
            return self.cmd_weekly(user_data), None, None
        
        elif cmd == "streak":
            return self.cmd_streak(user_data), None, None
        
        elif cmd == "rep":
            return self.cmd_rep(user_data, args, platform), None, None
        
        # === МАГАЗИН И ЭКОНОМИКА ===
        elif cmd == "shop":
            return self.cmd_shop(), self.get_shop_keyboard(), None
        
        elif cmd in ["buy", "buy_market"]:
            return self.cmd_buy(user_data, args), None, None
        
        elif cmd == "inventory":
            return self.cmd_inventory(user_data), None, None
        
        elif cmd == "use":
            return self.cmd_use(user_data, args), None, None
        
        elif cmd == "market":
            return self.cmd_market(), None, None
        
        elif cmd == "sell":
            return self.cmd_sell(user_data, args), None, None
        
        elif cmd in ["pay", "payd"]:
            return self.cmd_pay(user_data, args, "coins"), None, None
        
        elif cmd in ["payh", "paydiamonds"]:
            return self.cmd_pay(user_data, args, "diamonds"), None, None
        
        elif cmd == "donate":
            return self.cmd_donate(), self.get_donate_keyboard(), None
        
        elif cmd == "vip":
            return self.cmd_buy_privilege(user_data, "vip"), None, None
        
        elif cmd == "premium":
            return self.cmd_buy_privilege(user_data, "premium"), None, None
        
        # === БОССЫ ===
        elif cmd in ["bosses", "boss"]:
            return self.cmd_boss_list(user_data), self.get_boss_keyboard(), None
        
        elif cmd in ["boss_fight", "boss st"]:
            return self.cmd_boss_fight(user_data, args), None, None
        
        elif cmd == "boss_info":
            return self.cmd_boss_info(args), None, None
        
        elif cmd == "regen":
            return self.cmd_regen(user_data), None, None
        
        # === ИГРЫ ===
        elif cmd == "casino":
            return self.cmd_casino(), self.get_casino_keyboard(), None
        
        elif cmd == "roulette":
            return self.cmd_roulette(user_data, args), None, None
        
        elif cmd == "dice":
            return self.cmd_dice(user_data, args), None, None
        
        elif cmd == "blackjack":
            return self.cmd_blackjack(user_data, args), None, None
        
        elif cmd == "slots":
            return self.cmd_slots(user_data, args), None, None
        
        elif cmd == "rps":
            return self.cmd_rps(), self.get_rps_keyboard(), None
        
        elif cmd in ["rr", "rr_start"]:
            return self.cmd_rr_start(user_data, args), None, None
        
        elif cmd == "rr_join":
            return self.cmd_rr_join(user_data, args), None, None
        
        elif cmd == "rr_shot":
            return self.cmd_rr_shot(user_data), None, None
        
        elif cmd in ["ttt", "tictactoe"]:
            return self.cmd_ttt(), None, None
        
        elif cmd == "ttt_challenge":
            return self.cmd_ttt_challenge(user_data, args, platform), None, None
        
        elif cmd == "memory":
            return self.cmd_memory(user_data), None, None
        
        elif cmd in ["minesweeper", "сапер"]:
            return self.cmd_minesweeper(user_data, args), None, None
        
        # === СТАТИСТИКА ===
        elif cmd == "boss_stats":
            return self.cmd_boss_stats(user_data), None, None
        
        elif cmd == "mafia_stats":
            return self.cmd_mafia_stats(user_data), None, None
        
        elif cmd == "rps_stats":
            return self.cmd_rps_stats(user_data), None, None
        
        elif cmd == "casino_stats":
            return self.cmd_casino_stats(user_data), None, None
        
        elif cmd == "rr_stats":
            return self.cmd_rr_stats(user_data), None, None
        
        elif cmd == "ttt_stats":
            return self.cmd_ttt_stats(user_data), None, None
        
        # === КЛАНЫ ===
        elif cmd == "clan":
            return self.cmd_clan(user_data), self.get_clan_keyboard(), None
        
        elif cmd == "clan_create":
            return self.cmd_clan_create(user_data, args), None, None
        
        elif cmd == "clan_join":
            return self.cmd_clan_join(user_data, args), None, None
        
        elif cmd == "clan_leave":
            return self.cmd_clan_leave(user_data), None, None
        
        elif cmd == "clan_top":
            return self.cmd_clan_top(), None, None
        
        elif cmd == "clan_war":
            return self.cmd_clan_war(user_data), None, None
        
        # === МАФИЯ ===
        elif cmd == "mafia":
            return self.cmd_mafia(), self.get_mafia_keyboard(), None
        
        elif cmd == "mafia_create":
            return self.cmd_mafia_create(user_data), None, None
        
        elif cmd == "mafia_join":
            return self.cmd_mafia_join(user_data, args), None, None
        
        # === ПИТОМЦЫ ===
        elif cmd == "pet":
            return self.cmd_pet(user_data), self.get_pet_keyboard(), None
        
        elif cmd == "pet_buy":
            return self.cmd_pet_buy(user_data, args), None, None
        
        elif cmd == "pet_feed":
            return self.cmd_pet_feed(user_data, args), None, None
        
        elif cmd == "pet_fight":
            return self.cmd_pet_fight(user_data, args), None, None
        
        # === ДОСТИЖЕНИЯ ===
        elif cmd == "achievements":
            return self.cmd_achievements(user_data), None, None
        
        # === ТУРНИРЫ ===
        elif cmd == "tournament":
            return self.cmd_tournament(), None, None
        
        elif cmd == "rating":
            return self.cmd_rating(), None, None
        
        elif cmd == "bet":
            return self.cmd_bet(user_data, args), None, None
        
        # === ПОГОДА, НОВОСТИ, ЦИТАТЫ ===
        elif cmd == "weather":
            return self.cmd_weather(args), None, None
        
        elif cmd == "news":
            return self.cmd_news(), None, None
        
        elif cmd == "quote":
            return self.cmd_quote(), None, None
        
        # === ОПРОСЫ ===
        elif cmd == "poll":
            return self.cmd_poll(user_data, args), None, None
        
        # === ОТНОШЕНИЯ ===
        elif cmd == "marry":
            return self.cmd_marry(user_data, args, platform), self.get_marry_keyboard(args), None
        
        elif cmd == "divorce":
            return self.cmd_divorce(user_data), None, None
        
        elif cmd == "love":
            return self.cmd_love(user_data), None, None
        
        elif cmd == "children":
            return self.cmd_children(user_data), None, None
        
        # === ДОЛГИ ===
        elif cmd == "debt":
            return self.cmd_debt(user_data, args), None, None
        
        elif cmd == "debts":
            return self.cmd_debts(user_data), None, None
        
        elif cmd == "paydebt":
            return self.cmd_pay_debt(user_data, args), None, None
        
        # === ЗАКЛАДКИ ===
        elif cmd in ["add_bookmark", "+закладка"]:
            return self.cmd_add_bookmark(user_data, args, platform), None, None
        
        elif cmd in ["bookmarks", "закладки"]:
            return self.cmd_bookmarks(user_data, args), None, None
        
        # === АДМИНСКИЕ ===
        elif cmd == "mute":
            return self.cmd_mute(user_data, args, platform), None, None
        
        elif cmd == "warn":
            return self.cmd_warn(user_data, args, platform), None, None
        
        elif cmd == "ban":
            return self.cmd_ban(user_data, args, platform), None, None
        
        elif cmd == "unban":
            return self.cmd_unban(user_data, args, platform), None, None
        
        elif cmd == "banlist":
            page = int(args[0]) if args and args[0].isdigit() else 1
            return self.cmd_banlist(page), self.get_pagination_keyboard("ban", page), None
        
        elif cmd == "mutelist":
            page = int(args[0]) if args and args[0].isdigit() else 1
            return self.cmd_mutelist(page), self.get_pagination_keyboard("mute", page), None
        
        elif cmd == "warnlist":
            page = int(args[0]) if args and args[0].isdigit() else 1
            return self.cmd_warnlist(page), self.get_pagination_keyboard("warn", page), None
        
        elif cmd == "give":
            return self.cmd_give(user_data, args, platform), None, None
        
        elif cmd == "clear":
            return "⚠️ Для очистки сообщений используйте функцию удаления в чате.", None, None
        
        # === КОМАНДЫ ДОНАТЕРОВ ===
        elif cmd in ["cmd", "команды"]:
            return self.cmd_donor_commands(user_data, args), None, None
        
        # === ПРОЧЕЕ ===
        elif cmd in ["players", "кол-во игроков"]:
            return self.cmd_players(), None, None
        
        elif cmd in ["eng", "eng free"]:
            return self.cmd_eng_free(user_data), None, None
        
        elif cmd == "sms":
            return self.cmd_sms(user_data, args, platform), None, None
        
        elif cmd in ["mycrime", "моя статья"]:
            return self.cmd_mycrime(user_data), None, None
        
        elif cmd == "automes":
            return self.cmd_automes(user_data, args), None, None
        
        elif cmd == "namutebuy":
            return self.cmd_namutebuy(user_data), None, None
        
        elif cmd in ["draw", "generate"]:
            if photo_bytes:
                return "🎨 Обрабатываю твою картинку...", None, None
            elif args:
                prompt = " ".join(args)
                img_bytes = await self.ai.generate_image(prompt)
                if img_bytes:
                    return "🎨 Вот что у меня получилось:", None, img_bytes
                else:
                    return "❌ Не удалось сгенерировать картинку.", None, None
            else:
                return "❌ Напиши, что нарисовать: `/draw кот в космосе`", None, None
        
        # === НЕИЗВЕСТНАЯ КОМАНДА ===
        else:
            return f"❌ Неизвестная команда. Напиши /help", None, None

    # === ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ===
    def simple_response(self, text: str) -> str:
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["привет", "здравствуй", "ку", "хай"]):
            return "👋 Привет! Чего хочешь? Напиши /help если что."
        
        if any(word in text_lower for word in ["как дела", "как ты", "чё как"]):
            return "⚙️ В шоколаде! А у тебя как? Играем?"
        
        if any(word in text_lower for word in ["спасибо", "благодарю", "пасиб"]):
            return "🤝 Обращайся, братан!"
        
        if any(word in text_lower for word in ["кто создал", "владелец", "создатель"]):
            return f"👑 Мой создатель: {OWNER_USERNAME}"
        
        if any(word in text_lower for word in ["игра", "поиграть", "хочу играть"]):
            return "🎮 Отлично! Могу предложить боссов /bosses, казино /casino или КНБ /rps"
        
        return "🤖 Я тебя слушаю. Если нужна помощь - пиши /help"

    # === КОМАНДЫ ===
    def cmd_help(self, user_data: Dict) -> str:
        return (f"╔══════════════════════════════╗\n"
                f"║   📚 **СПРАВКА**           ║\n"
                f"╚══════════════════════════════╝\n\n"
                f"👤 **Твой профиль:** /profile\n"
                f"👾 **Боссы:** /bosses\n"
                f"🎰 **Казино:** /casino\n"
                f"👥 **Кланы:** /clan\n"
                f"🎁 **Магазин:** /shop\n"
                f"💎 **Донат:** /donate\n\n"
                f"📋 **Все команды:** выбери в меню")

    def cmd_profile(self, user_data: Dict, args: List[str], platform: str) -> str:
        target_data = user_data
        target_name = user_data.get('first_name', 'Игрок')
        
        if args:
            query = " ".join(args)
            found_user = self.db.get_user_by_name(query, platform)
            if found_user:
                target_data = found_user
                target_name = target_data.get('nickname') or target_data.get('first_name', 'Игрок')
            else:
                return f"❌ Пользователь '{query}' не найден."

        role_emoji = self.get_role_emoji(target_data.get('role', 'user'))
        
        # Форматируем даты
        join_date = target_data.get('created_at', '')
        if join_date:
            join_date = datetime.datetime.fromisoformat(join_date).strftime("%d.%m.%Y")
        else:
            join_date = "неизвестно"
        
        last_seen = target_data.get('last_seen', '')
        if last_seen:
            last_dt = datetime.datetime.fromisoformat(last_seen)
            delta = datetime.datetime.now() - last_dt
            if delta.days > 0:
                last_seen = f"{delta.days} дн назад"
            elif delta.seconds > 3600:
                last_seen = f"{delta.seconds // 3600} ч назад"
            else:
                last_seen = f"{delta.seconds // 60} мин назад"
        else:
            last_seen = "никогда"

        platform_link = f"tg://user?id={target_data.get('platform_id')}" if platform == 'tg' else f"https://vk.com/id{target_data.get('platform_id')}"
        
        return (f"**[{platform_link}|{target_name}]**\n"
                f"{role_emoji} Ранг: **{target_data.get('role')}**\n"
                f"Репутация: ✨ {target_data.get('rep', 0)} | ➕ 0\n"
                f"Первое появление: {join_date}\n"
                f"Последний актив: {last_seen}\n"
                f"Актив (д|н|м|весь): {target_data.get('active_days', 0)} | {target_data.get('active_weeks', 0)} | {target_data.get('active_months', 0)} | {target_data.get('total_active_days', 0)}")

    def cmd_edit_profile(self) -> str:
        return ("✏️ **РЕДАКТИРОВАНИЕ ПРОФИЛЯ**\n\n"
                "`.nick [ник]` — установить никнейм\n"
                "`.gender [м/ж]` — установить пол\n"
                "`.city [город]` — город\n"
                "`.bio [текст]` — о себе")

    def cmd_top(self) -> str:
        top_coins = self.db.get_top("coins", 10)
        top_level = self.db.get_top("level", 10)
        top_boss = self.db.get_top("boss_kills", 10)
        
        text = "╔══════════════════════════════╗\n║    🏆 **ТОП ИГРОКОВ**      ║\n╚══════════════════════════════╝\n\n"
        
        text += "━━━━━━━━━━━━━━━━━━━━━━━\n💰 **ПО МОНЕТАМ**\n━━━━━━━━━━━━━━━━━━━━━━━\n"
        for i, (name, value) in enumerate(top_coins, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
            text += f"{medal} **{i}.** {name} — {value} 🪙\n"
        
        text += "\n━━━━━━━━━━━━━━━━━━━━━━━\n📊 **ПО УРОВНЮ**\n━━━━━━━━━━━━━━━━━━━━━━━\n"
        for i, (name, value) in enumerate(top_level, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
            text += f"{medal} **{i}.** {name} — {value} ур.\n"
        
        text += "\n━━━━━━━━━━━━━━━━━━━━━━━\n👾 **ПО УБИЙСТВУ БОССОВ**\n━━━━━━━━━━━━━━━━━━━━━━━\n"
        for i, (name, value) in enumerate(top_boss, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
            text += f"{medal} **{i}.** {name} — {value} боссов\n"
        
        return text

    def cmd_daily(self, user_data: Dict) -> str:
        user_id = user_data['user_id']
        
        streak = self.db.add_daily_streak(user_id)
        
        coins = random.randint(100, 300) * (1 + min(streak, 30) * 0.05)
        exp = random.randint(20, 60) * (1 + min(streak, 30) * 0.05)
        
        if self.db.is_vip(user_id):
            coins *= 1.5
            exp *= 1.5
        if self.db.is_premium(user_id):
            coins *= 2
            exp *= 2
        
        coins = int(coins)
        exp = int(exp)
        
        self.db.add_coins(user_id, coins)
        self.db.add_exp(user_id, exp)
        
        return (f"╔══════════════════════════════╗\n"
                f"║    🎁 **ЕЖЕДНЕВНАЯ НАГРАДА**   ║\n"
                f"╚══════════════════════════════╝\n\n"
                f"🔥 **Стрик:** {streak} дней\n"
                f"💰 **Монеты:** +{coins} 🪙\n"
                f"✨ **Опыт:** +{exp}\n\n"
                f"🌟 Заходи завтра!")

    def cmd_weekly(self, user_data: Dict) -> str:
        user_id = user_data['user_id']
        
        # Проверка, прошла ли неделя
        last_weekly = user_data.get('last_weekly')
        if last_weekly:
            last = datetime.datetime.fromisoformat(last_weekly)
            if (datetime.datetime.now() - last).days < 7:
                return "❌ Ты уже получал недельный бонус! Приходи через неделю."
        
        coins = random.randint(1000, 3000)
        diamonds = random.randint(10, 30)
        
        if self.db.is_vip(user_id):
            coins = int(coins * 1.5)
            diamonds = int(diamonds * 1.5)
        if self.db.is_premium(user_id):
            coins = int(coins * 2)
            diamonds = int(diamonds * 2)
        
        self.db.add_coins(user_id, coins)
        self.db.add_diamonds(user_id, diamonds)
        
        # Обновляем last_weekly
        self.db.cursor.execute("UPDATE users SET last_weekly = ? WHERE user_id = ?", 
                              (datetime.datetime.now(), user_id))
        self.db.conn.commit()
        
        return (f"📅 **НЕДЕЛЬНЫЙ БОНУС**\n\n"
                f"💰 **Монеты:** +{coins} 🪙\n"
                f"💎 **Алмазы:** +{diamonds} 💎\n\n"
                f"Возвращайся через неделю!")

    def cmd_streak(self, user_data: Dict) -> str:
        streak = user_data.get('daily_streak', 0)
        last_daily = user_data.get('last_daily', 'никогда')
        
        if last_daily != 'никогда':
            last = datetime.datetime.fromisoformat(last_daily)
            days_missed = (datetime.datetime.now() - last).days
        else:
            days_missed = 0
        
        return (f"🔥 **ТВОЙ СТРИК**\n\n"
                f"Дней подряд: {streak}\n"
                f"Последний вход: {last_daily[:10] if last_daily != 'никогда' else 'никогда'}\n"
                f"Пропущено дней: {days_missed}")

    def cmd_rep(self, user_data: Dict, args: List[str], platform: str) -> str:
        if not args:
            return "❌ Укажи ID или ник: /rep @username"
        
        query = args[0]
        target_data = self.db.get_user_by_name(query, platform)
        
        if not target_data:
            return f"❌ Пользователь не найден"
        
        if target_data['user_id'] == user_data['user_id']:
            return "❌ Нельзя дать репутацию самому себе"
        
        self.db.cursor.execute("UPDATE users SET rep = rep + 1 WHERE user_id = ?", (target_data['user_id'],))
        self.db.conn.commit()
        
        return f"⭐ Репутация пользователя повышена!"

    # === МАГАЗИН ===
    def cmd_shop(self) -> str:
        return ("🏪 **МАГАЗИН «СПЕКТР»**\n\n"
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
                "Купить: /buy [название]")

    def cmd_buy(self, user_data: Dict, args: List[str]) -> str:
        if not args:
            return "❌ Укажи предмет: /buy меч"
        
        item = " ".join(args).lower()
        user_id = user_data['user_id']
        
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
            return "❌ Такого предмета нет в магазине"
        
        item_data = items[item]
        
        if user_data['coins'] < item_data['price']:
            return f"❌ Недостаточно монет! Нужно {item_data['price']} 🪙"
        
        self.db.add_coins(user_id, -item_data['price'])
        
        if 'heal' in item_data:
            self.db.heal(user_id, item_data['heal'])
            return f"✅ Здоровье +{item_data['heal']}❤️"
        
        elif 'damage' in item_data:
            self.db.cursor.execute("UPDATE users SET damage = damage + ? WHERE user_id = ?", 
                                 (item_data['damage'], user_id))
            self.db.conn.commit()
            return f"✅ Урон +{item_data['damage']}⚔️"
        
        elif 'armor' in item_data:
            self.db.cursor.execute("UPDATE users SET armor = armor + ? WHERE user_id = ?", 
                                 (item_data['armor'], user_id))
            self.db.conn.commit()
            return f"✅ Броня +{item_data['armor']}🛡"
        
        elif 'energy' in item_data:
            self.db.add_energy(user_id, item_data['energy'])
            return f"✅ Энергия +{item_data['energy']}⚡"
        
        return "✅ Покупка совершена!"

    def cmd_inventory(self, user_data: Dict) -> str:
        items = self.db.get_inventory(user_data['user_id'])
        
        if not items:
            return "📦 Твой инвентарь пуст"
        
        text = "📦 **ТВОЙ ИНВЕНТАРЬ**\n\n"
        for item_id, name, item_type, desc, qty in items:
            text += f"**ID: {item_id}** — {name} x{qty}\n"
            if desc:
                text += f"└ {desc}\n"
            text += "\n"
        
        text += "Использовать: /use [ID]"
        return text

    def cmd_use(self, user_data: Dict, args: List[str]) -> str:
        if not args:
            return "❌ Укажи ID предмета: /use 1"
        
        try:
            item_id = int(args[0])
        except:
            return "❌ Неправильный ID"
        
        used_item = self.db.use_item(user_data['user_id'], item_id)
        
        if used_item:
            return f"✅ Использован предмет: {used_item}"
        return "❌ У тебя нет такого предмета"

    def cmd_market(self) -> str:
        return "🏪 Торговая площадка скоро откроется!"

    def cmd_sell(self, user_data: Dict, args: List[str]) -> str:
        return "📦 Функция продажи временно недоступна"

    def cmd_pay(self, user_data: Dict, args: List[str], currency: str) -> str:
        if len(args) < 2:
            return f"❌ Использование: /pay [ник] [сумма]"
        
        query = args[0]
        try:
            amount = int(args[1])
        except:
            return "❌ Сумма должна быть числом"
        
        target_data = self.db.get_user_by_name(query)
        if not target_data:
            return f"❌ Пользователь не найден"
        
        if target_data['user_id'] == user_data['user_id']:
            return "❌ Нельзя перевести самому себе"
        
        balance_key = 'coins' if currency == 'coins' else 'diamonds'
        if user_data[balance_key] < amount:
            return f"❌ Недостаточно {'монет' if currency=='coins' else 'алмазов'}! У тебя {user_data[balance_key]}"
        
        if currency == 'coins':
            self.db.add_coins(user_data['user_id'], -amount)
            self.db.add_coins(target_data['user_id'], amount)
            return f"💰 Перевод выполнен! {amount} 🪙 отправлено пользователю {target_data.get('first_name')}"
        else:
            self.db.add_diamonds(user_data['user_id'], -amount)
            self.db.add_diamonds(target_data['user_id'], amount)
            return f"💎 Перевод выполнен! {amount} 💎 отправлено пользователю {target_data.get('first_name')}"

    def cmd_donate(self) -> str:
        return (f"💎 **ПРИВИЛЕГИИ «СПЕКТР»** 💎\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🌟 **VIP СТАТУС** — {VIP_PRICE} 🪙\n"
                f"▫️ Урон +20%, награда +50%, бонус +50%\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💎 **PREMIUM СТАТУС** — {PREMIUM_PRICE} 🪙\n"
                f"▫️ Все бонусы VIP, урон +50%, награда +100%\n\n"
                f"👑 Владелец: {OWNER_USERNAME}")

    def cmd_buy_privilege(self, user_data: Dict, priv_type: str) -> str:
        user_id = user_data['user_id']
        
        if priv_type == "vip":
            price = VIP_PRICE
            days = VIP_DAYS
            if self.db.is_vip(user_id):
                return "❌ У тебя уже есть VIP статус!"
        else:
            price = PREMIUM_PRICE
            days = PREMIUM_DAYS
            if self.db.is_premium(user_id):
                return "❌ У тебя уже есть Premium статус!"
        
        if user_data['coins'] < price:
            return f"❌ Недостаточно монет! Нужно {price} 🪙"
        
        self.db.add_coins(user_id, -price)
        
        if priv_type == "vip":
            self.db.set_vip(user_id, days)
            return f"🌟 Поздравляю! Теперь у тебя VIP статус на {days} дней!"
        else:
            self.db.set_premium(user_id, days)
            return f"💎 Поздравляю! Теперь у тебя PREMIUM статус на {days} дней!"

    # === БОССЫ ===
    def cmd_boss_list(self, user_data: Dict) -> str:
        bosses = self.db.get_bosses(alive_only=True)
        
        if not bosses:
            self.db.respawn_bosses()
            bosses = self.db.get_bosses(alive_only=True)
        
        damage_bonus = 1.0
        if self.db.is_vip(user_data['user_id']):
            damage_bonus += 0.2
        if self.db.is_premium(user_data['user_id']):
            damage_bonus += 0.3
        
        player_damage = user_data.get('damage', 10) * damage_bonus
        
        text = f"👊 **АРЕНА БОССА** 👊\n"
        text += f"↪️ Твоя цель: убить босса.\n"
        
        if bosses:
            boss = bosses[0]
            text += f"💀 **Текущий босс:** {boss[1]} (ур. {boss[2]})\n"
            text += f"💫 Урон от босса: {max(1, boss[5]-5)}-{boss[5]+5} HP.\n"
            text += f"🖤 Жизни босса: {boss[3]}/{boss[4]} ❤️\n"
            text += f"🗡 Твой урон: {player_damage:.1f}⚔️ (сила: {damage_bonus*100:.0f}%)\n"
        
        text += f"▰▰▰▰▰▰▰▰▰▰▰▰\n"
        text += f"⏺ **Команды:**\n"
        text += f"👊 /boss_fight [ID] — атаковать!\n"
        text += f"➕ /regen — восстановить здоровье.\n"
        text += f"🗡 /shop — купить оружие."
        
        return text

    def cmd_boss_fight(self, user_data: Dict, args: List[str]) -> str:
        if not args:
            return "❌ Укажи ID босса: /boss_fight 1"
        
        try:
            boss_id = int(args[0])
        except:
            return "❌ Неправильный ID босса."
        
        boss = self.db.get_boss(boss_id)
        if not boss or not boss[8]:
            return "❌ Босс уже повержен или не найден."
        
        user_id = user_data['user_id']
        
        if user_data['energy'] < 10:
            return "❌ Нужно 10 энергии для битвы! Используй /regen"
        
        self.db.add_energy(user_id, -10)
        
        damage_bonus = 1.0
        if self.db.is_vip(user_id):
            damage_bonus += 0.2
        if self.db.is_premium(user_id):
            damage_bonus += 0.3
        
        player_damage = int(user_data['damage'] * damage_bonus) + random.randint(-5, 5)
        boss_damage = boss[5] + random.randint(-5, 5)
        player_taken = max(1, boss_damage - user_data['armor'] // 2)
        
        boss_killed = self.db.damage_boss(boss_id, player_damage)
        self.db.damage(user_id, player_taken)
        
        result = f"⚔️ **БИТВА С БОССОМ** ⚔️\n\n"
        result += f"▫️ **Ты нанес:** {player_damage} урона\n"
        result += f"▫️ **Босс нанес:** {player_taken} урона\n\n"
        
        if boss_killed:
            reward = boss[6] * (1 + user_data['level'] // 10)
            if self.db.is_vip(user_id):
                reward = int(reward * 1.5)
            if self.db.is_premium(user_id):
                reward = int(reward * 2)
            
            self.db.add_coins(user_id, reward)
            self.db.add_boss_kill(user_id)
            self.db.add_exp(user_id, boss[2] * 10)
            result += f"🎉 **ПОБЕДА!**\n💰 **Награда:** {reward} монет\n✨ **Опыт:** +{boss[2] * 10}"
        else:
            boss_info = self.db.get_boss(boss_id)
            result += f"👾 **Босс еще жив!**\n❤️ **Осталось:** {boss_info[3]} здоровья"
        
        if user_data['health'] <= player_taken:
            self.db.heal(user_id, 50)
            result += "\n\n💀 Ты погиб в бою, но воскрешен с 50❤️"
        
        return result

    def cmd_boss_info(self, args: List[str]) -> str:
        if not args:
            return "❌ Укажи ID босса: /boss_info 1"
        
        try:
            boss_id = int(args[0])
        except:
            return "❌ Неправильный ID"
        
        boss = self.db.get_boss(boss_id)
        if not boss:
            return "❌ Босс не найден"
        
        status = "👾 ЖИВ" if boss[8] else "💀 ПОВЕРЖЕН"
        
        return (f"**{boss[1]}** (Уровень {boss[2]})\n\n"
                f"❤️ Здоровье: {boss[3]}/{boss[4]}\n"
                f"⚔️ Урон: {boss[5]}\n"
                f"💰 Награда: {boss[6]} 🪙\n"
                f"📊 Статус: {status}")

    def cmd_regen(self, user_data: Dict) -> str:
        user_id = user_data['user_id']
        cost = 20
        
        if user_data['coins'] < cost:
            return f"❌ Недостаточно монет! Нужно {cost} 🪙"
        
        self.db.add_coins(user_id, -cost)
        self.db.heal(user_id, 50)
        self.db.add_energy(user_id, 20)
        
        return f"✅ Регенерация завершена! +50❤️ здоровья, +20⚡ энергии"

    # === КАЗИНО ===
    def cmd_casino(self) -> str:
        return ("🎰 **КАЗИНО «СПЕКТР»** 🎰\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━\n"
                "🎰 Рулетка — /roulette [ставка] [цвет/число]\n"
                "🎲 Кости — /dice [ставка]\n"
                "🃏 Блэкджек — /blackjack [ставка]\n"
                "🎰 Слоты — /slots [ставка]")

    def cmd_roulette(self, user_data: Dict, args: List[str]) -> str:
        bet = 10
        choice = "red"
        
        if args:
            try:
                bet = int(args[0])
                if len(args) > 1:
                    choice = args[1].lower()
            except:
                pass
        
        if bet > user_data['coins']:
            return f"❌ У тебя только {user_data['coins']} 🪙"
        
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
            self.db.add_coins(user_data['user_id'], winnings)
            result_text = f"🎉 **Ты выиграл {winnings} 🪙!**"
        else:
            self.db.add_coins(user_data['user_id'], -bet)
            result_text = f"😢 **Ты проиграл {bet} 🪙**"
        
        return (f"🎰 **РУЛЕТКА**\n\n"
                f"▫️ **Ставка:** {bet} 🪙\n"
                f"▫️ **Выбрано:** {choice}\n"
                f"▫️ **Выпало:** {result_num} {result_color}\n\n"
                f"{result_text}")

    def cmd_dice(self, user_data: Dict, args: List[str]) -> str:
        bet = 10
        if args:
            try:
                bet = int(args[0])
            except:
                pass
        
        if bet > user_data['coins']:
            return f"❌ У тебя только {user_data['coins']} 🪙"
        
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
            self.db.add_coins(user_data['user_id'], win)
        
        return (f"🎲 **КОСТИ**\n\n"
                f"▫️ **Ставка:** {bet} 🪙\n"
                f"▫️ **Кубики:** {dice1} + {dice2}\n"
                f"▫️ **Сумма:** {total}\n\n"
                f"{result_text}")

    def cmd_blackjack(self, user_data: Dict, args: List[str]) -> str:
        bet = 10
        if args:
            try:
                bet = int(args[0])
            except:
                pass
        
        if bet > user_data['coins']:
            return f"❌ У тебя только {user_data['coins']} 🪙"
        
        player_card1 = random.randint(1, 11)
        player_card2 = random.randint(1, 11)
        player_total = player_card1 + player_card2
        
        dealer_card1 = random.randint(1, 11)
        dealer_card2 = random.randint(1, 11)
        dealer_total = dealer_card1 + dealer_card2
        
        if player_total > 21:
            result = "lose"
            result_text = f"😢 **Ты проиграл {bet} 🪙**"
        elif dealer_total > 21:
            result = "win"
            win = bet * 2
            result_text = f"🎉 **Ты выиграл {win} 🪙!**"
        elif player_total > dealer_total:
            result = "win"
            win = bet * 2
            result_text = f"🎉 **Ты выиграл {win} 🪙!**"
        elif player_total < dealer_total:
            result = "lose"
            result_text = f"😢 **Ты проиграл {bet} 🪙**"
        else:
            result = "draw"
            result_text = f"🔄 **Ничья, ставка возвращена:** {bet} 🪙"
        
        if result == "win":
            self.db.add_coins(user_data['user_id'], win)
        elif result == "lose":
            self.db.add_coins(user_data['user_id'], -bet)
        
        return (f"🃏 **БЛЭКДЖЕК**\n\n"
                f"**Твои карты:** {player_card1} + {player_card2} = {player_total}\n"
                f"**Карты дилера:** {dealer_card1} + {dealer_card2} = {dealer_total}\n\n"
                f"{result_text}")

    def cmd_slots(self, user_data: Dict, args: List[str]) -> str:
        bet = 10
        if args:
            try:
                bet = int(args[0])
            except:
                pass
        
        if bet > user_data['coins']:
            return f"❌ У тебя только {user_data['coins']} 🪙"
        
        symbols = ["🍒", "🍋", "🍊", "7️⃣", "💎", "🎰", "⭐", "👑"]
        spin = [random.choice(symbols) for _ in range(3)]
        
        if len(set(spin)) == 1:
            if spin[0] == "👑":
                win = bet * 100
            elif spin[0] == "7️⃣":
                win = bet * 50
            elif spin[0] == "💎":
                win = bet * 30
            else:
                win = bet * 10
            result_text = "🎉 **ДЖЕКПОТ!**"
        elif len(set(spin)) == 2:
            win = bet * 2
            result_text = "🎉 **Маленький выигрыш!**"
        else:
            win = 0
            result_text = "😢 **Не повезло...**"
        
        if win > 0:
            self.db.add_coins(user_data['user_id'], win)
        else:
            self.db.add_coins(user_data['user_id'], -bet)
        
        return (f"🎰 **СЛОТЫ**\n\n"
                f"**{' '.join(spin)}**\n\n"
                f"{result_text}\n"
                f"{'💰 +' + str(win) + ' 🪙' if win > 0 else '💸 -' + str(bet) + ' 🪙'}")

    def cmd_rps(self) -> str:
        return ("✊ **КАМЕНЬ-НОЖНИЦЫ-БУМАГА**\n\n"
                "Выбери: /rps_rock, /rps_scissors, /rps_paper")

    def cmd_rps_stats(self, user_data: Dict) -> str:
        wins = user_data.get('rps_wins', 0)
        losses = user_data.get('rps_losses', 0)
        draws = user_data.get('rps_draws', 0)
        total = wins + losses + draws
        
        return (f"╔══════════════════════════════╗\n"
                f"║   ✊ **СТАТИСТИКА КНБ**     ║\n"
                f"╚══════════════════════════════╝\n\n"
                f"▫️ **Побед:** {wins} 🏆\n"
                f"▫️ **Поражений:** {losses} 💔\n"
                f"▫️ **Ничьих:** {draws} 🤝\n"
                f"▫️ **Всего игр:** {total} 🎮")

    def cmd_casino_stats(self, user_data: Dict) -> str:
        wins = user_data.get('casino_wins', 0)
        losses = user_data.get('casino_losses', 0)
        total = wins + losses
        
        return (f"╔══════════════════════════════╗\n"
                f"║   🎰 **СТАТИСТИКА КАЗИНО**  ║\n"
                f"╚══════════════════════════════╝\n\n"
                f"▫️ **Побед:** {wins} 🏆\n"
                f"▫️ **Поражений:** {losses} 💔\n"
                f"▫️ **Всего игр:** {total} 🎮")

    def cmd_boss_stats(self, user_data: Dict) -> str:
        return (f"╔══════════════════════════════╗\n"
                f"║   👾 **СТАТИСТИКА БОССОВ**  ║\n"
                f"╚══════════════════════════════╝\n\n"
                f"▫️ **Боссов убито:** {user_data.get('boss_kills', 0)} 💀\n"
                f"▫️ **Урон:** {user_data.get('damage', 10)} ⚔️\n"
                f"▫️ **Броня:** {user_data.get('armor', 0)} 🛡\n"
                f"▫️ **Здоровье:** {user_data.get('health', 100)} ❤️")

    def cmd_mafia_stats(self, user_data: Dict) -> str:
        wins = user_data.get('mafia_wins', 0)
        games = user_data.get('mafia_games', 0)
        
        return (f"╔══════════════════════════════╗\n"
                f"║   🔪 **СТАТИСТИКА МАФИИ**   ║\n"
                f"╚══════════════════════════════╝\n\n"
                f"▫️ **Побед:** {wins} 🏆\n"
                f"▫️ **Игр:** {games} 🎮")

    def cmd_rr_stats(self, user_data: Dict) -> str:
        wins = user_data.get('rr_wins', 0)
        losses = user_data.get('rr_losses', 0)
        total = wins + losses
        
        return (f"╔══════════════════════════════╗\n"
                f"║  💣 **СТАТИСТИКА РУЛЕТКИ**  ║\n"
                f"╚══════════════════════════════╝\n\n"
                f"▫️ **Побед:** {wins} 🏆\n"
                f"▫️ **Поражений:** {losses} 💔\n"
                f"▫️ **Всего игр:** {total} 🎮")

    def cmd_ttt_stats(self, user_data: Dict) -> str:
        wins = user_data.get('ttt_wins', 0)
        losses = user_data.get('ttt_losses', 0)
        draws = user_data.get('ttt_draws', 0)
        total = wins + losses + draws
        
        return (f"╔══════════════════════════════╗\n"
                f"║  ⭕ **СТАТИСТИКА TTT**      ║\n"
                f"╚══════════════════════════════╝\n\n"
                f"▫️ **Побед:** {wins} 🏆\n"
                f"▫️ **Поражений:** {losses} 💔\n"
                f"▫️ **Ничьих:** {draws} 🤝\n"
                f"▫️ **Всего игр:** {total} 🎮")

    # === КЛАНЫ ===
    def cmd_clan(self, user_data: Dict) -> str:
        clan = self.db.get_user_clan(user_data['user_id'])
        
        if not clan:
            return ("👥 Ты не состоишь в клане.\n\n"
                    "Создать: /clan_create [название]\n"
                    "Присоединиться: /clan_join [ID]")
        
        members = self.db.get_clan_members(clan[0])
        
        text = (f"╔══════════════════════════════╗\n"
                f"║    👥 **КЛАН «{clan[1]}»**   ║\n"
                f"╚══════════════════════════════╝\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"**ИНФОРМАЦИЯ**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"▫️ **Уровень:** {clan[3]}\n"
                f"▫️ **Участников:** {clan[5]}\n"
                f"▫️ **Рейтинг:** {clan[6]}\n"
                f"▫️ **Побед/Поражений:** {clan[8]}/{clan[9]}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"**УЧАСТНИКИ**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n")
        
        for member in members:
            role_emoji = "👑" if member[5] == 'owner' else "🛡" if member[5] == 'admin' else "👤"
            text += f"{role_emoji} {member[1]} (ур.{member[3]})\n"
        
        return text

    def cmd_clan_create(self, user_data: Dict, args: List[str]) -> str:
        if not args:
            return "❌ Укажи название: /clan_create Название"
        
        name = " ".join(args)
        user_id = user_data['user_id']
        
        if len(name) > 30:
            return "❌ Название слишком длинное (макс 30 символов)"
        
        if self.db.get_user_clan(user_id):
            return "❌ Ты уже в клане"
        
        if user_data['level'] < 5:
            return "❌ Для создания клана нужен 5 уровень!"
        
        if user_data['coins'] < 1000:
            return "❌ Для создания клана нужно 1000 🪙"
        
        clan_id = self.db.create_clan(name, user_id)
        
        if clan_id:
            self.db.add_coins(user_id, -1000)
            return f"✅ Клан «{name}» создан! ID: {clan_id}"
        else:
            return "❌ Клан с таким названием уже существует"

    def cmd_clan_join(self, user_data: Dict, args: List[str]) -> str:
        if not args:
            return "❌ Укажи ID клана: /clan_join 1"
        
        try:
            clan_id = int(args[0])
        except:
            return "❌ Неправильный ID"
        
        user_id = user_data['user_id']
        
        if self.db.get_user_clan(user_id):
            return "❌ Ты уже в клане"
        
        clan = self.db.get_clan(clan_id)
        if not clan:
            return "❌ Клан не найден"
        
        if clan[5] >= 50:
            return "❌ В клане нет мест (максимум 50)"
        
        self.db.join_clan(user_id, clan_id)
        return f"✅ Ты вступил в клан «{clan[1]}»!"

    def cmd_clan_leave(self, user_data: Dict) -> str:
        user_id = user_data['user_id']
        clan = self.db.get_user_clan(user_id)
        
        if not clan:
            return "❌ Ты не в клане"
        
        if clan[2] == user_id:
            return "❌ Владелец не может покинуть клан."
        
        self.db.leave_clan(user_id, clan[0])
        return "✅ Ты покинул клан"

    def cmd_clan_top(self) -> str:
        self.db.cursor.execute(
            "SELECT name, level, members, rating, wins FROM clans ORDER BY rating DESC, level DESC LIMIT 10"
        )
        clans = self.db.cursor.fetchall()
        
        text = (f"╔══════════════════════════════╗\n"
                f"║    🏆 **ТОП КЛАНОВ**        ║\n"
                f"╚══════════════════════════════╝\n\n")
        
        for i, (name, level, members, rating, wins) in enumerate(clans, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
            text += f"{medal} **{i}. {name}** — {level} ур., {members} уч., {rating} ⭐, {wins} побед\n"
        
        return text

    def cmd_clan_war(self, user_data: Dict) -> str:
        return "⚔️ Клановые войны будут доступны в следующем обновлении!"

    # === МАФИЯ ===
    def cmd_mafia(self) -> str:
        return ("🔪 **МАФИЯ**\n\n"
                "**Команды:**\n"
                "▫️ /mafia_create — создать игру\n"
                "▫️ /mafia_join [ID] — присоединиться")

    def cmd_mafia_create(self, user_data: Dict) -> str:
        game_id = self.db.create_mafia_game(user_data['user_id'])
        return (f"🔪 **ИГРА МАФИЯ СОЗДАНА!**\n\n"
                f"▫️ **ID игры:** {game_id}\n"
                f"▫️ **Создатель:** {user_data.get('first_name')}\n"
                f"▫️ **Игроков:** 1/10\n\n"
                f"Присоединиться: /mafia_join {game_id}")

    def cmd_mafia_join(self, user_data: Dict, args: List[str]) -> str:
        if not args:
            return "❌ Укажи ID игры: /mafia_join 1"
        
        try:
            game_id = int(args[0])
        except:
            return "❌ Неправильный ID"
        
        game = self.db.get_mafia_game(game_id)
        if not game:
            return "❌ Игра не найдена"
        
        if game[2] != 'waiting':
            return "❌ Игра уже началась"
        
        players = eval(game[3])
        if len(players) >= 10:
            return "❌ В игре уже максимальное количество игроков"
        
        if user_data['user_id'] in players:
            return "❌ Ты уже в игре"
        
        if self.db.join_mafia_game(game_id, user_data['user_id']):
            return f"✅ Ты присоединился к игре {game_id}!"
        return "❌ Не удалось присоединиться"

    # === ПИТОМЦЫ ===
    def cmd_pet(self, user_data: Dict) -> str:
        pets = self.db.get_user_pets(user_data['user_id'])
        
        if not pets:
            return ("🐾 **ПИТОМЦЫ**\n\n"
                    "У тебя пока нет питомцев.\n"
                    "Купить: /pet_buy [имя] [тип]\n"
                    "Типы: 🐶 собака, 🐱 кошка, 🐉 дракон")
        
        text = "🐾 **ТВОИ ПИТОМЦЫ**\n\n"
        for pet in pets:
            health_bar = "█" * (pet[3] // 10) + "░" * (10 - pet[3] // 10)
            text += (f"**{pet[2]}** ({pet[1]})\n"
                    f"❤️ Здоровье: {pet[3]}/{pet[4]} {health_bar}\n"
                    f"⚔️ Атака: {pet[5]}\n"
                    f"📊 Уровень: {pet[7]}\n\n")
        
        text += "Покормить: /pet_feed [ID]\nБитва: /pet_fight [ID_противника]"
        return text

    def cmd_pet_buy(self, user_data: Dict, args: List[str]) -> str:
        if len(args) < 2:
            return "❌ Использование: /pet_buy [имя] [тип]\nТипы: dog, cat, dragon"
        
        name = args[0]
        pet_type = args[1].lower()
        
        price = 500
        if user_data['coins'] < price:
            return f"❌ Недостаточно монет! Нужно {price} 🪙"
        
        type_emoji = {"dog": "🐶", "cat": "🐱", "dragon": "🐉"}.get(pet_type, "🐾")
        
        self.db.add_coins(user_data['user_id'], -price)
        pet_id = self.db.create_pet(user_data['user_id'], name, f"{type_emoji} {pet_type}")
        
        return f"✅ Питомец {type_emoji} {name} куплен! ID: {pet_id}"

    def cmd_pet_feed(self, user_data: Dict, args: List[str]) -> str:
        if not args:
            return "❌ Укажи ID питомца: /pet_feed 1"
        
        try:
            pet_id = int(args[0])
        except:
            return "❌ Неправильный ID"
        
        price = 50
        if user_data['coins'] < price:
            return f"❌ Недостаточно монет! Нужно {price} 🪙"
        
        self.db.add_coins(user_data['user_id'], -price)
        self.db.feed_pet(pet_id)
        
        return f"✅ Питомец накормлен! ❤️ восстановлено"

    def cmd_pet_fight(self, user_data: Dict, args: List[str]) -> str:
        return "⚔️ Битва питомцев скоро будет доступна!"

    # === ДОСТИЖЕНИЯ ===
    def cmd_achievements(self, user_data: Dict) -> str:
        user_id = user_data['user_id']
        
        # Простые достижения на основе данных
        achievements = []
        
        if user_data.get('boss_kills', 0) >= 10:
            achievements.append("👾 **Охотник на боссов** — убито 10 боссов")
        if user_data.get('boss_kills', 0) >= 50:
            achievements.append("👾 **Легендарный охотник** — убито 50 боссов")
        
        if user_data.get('level', 1) >= 10:
            achievements.append("📈 **Опытный** — достиг 10 уровня")
        if user_data.get('level', 1) >= 25:
            achievements.append("📈 **Ветеран** — достиг 25 уровня")
        
        casino_games = user_data.get('casino_wins', 0) + user_data.get('casino_losses', 0)
        if casino_games >= 50:
            achievements.append("🎰 **Игроман** — сыграно 50 игр в казино")
        
        if user_data.get('clan_id', 0) != 0:
            achievements.append("👥 **Социальный** — вступил в клан")
        
        if user_data.get('marry_id', 0) != 0:
            achievements.append("💍 **Семьянин** — вступил в брак")
        
        if not achievements:
            return "🏆 У тебя пока нет достижений. Играй и открывай новые!"
        
        text = "🏆 **ТВОИ ДОСТИЖЕНИЯ**\n\n"
        for ach in achievements:
            text += f"▫️ {ach}\n"
        
        return text

    # === ТУРНИРЫ ===
    def cmd_tournament(self) -> str:
        return ("🏆 **ТУРНИРЫ**\n\n"
                "Еженедельные турниры скоро начнутся!\n"
                "Следи за обновлениями.")

    def cmd_rating(self) -> str:
        return self.cmd_top()

    def cmd_bet(self, user_data: Dict, args: List[str]) -> str:
        return "🎲 Ставки на турниры временно недоступны"

    # === ПОГОДА, НОВОСТИ, ЦИТАТЫ ===
    def cmd_weather(self, args: List[str]) -> str:
        city = " ".join(args) if args else "Москва"
        # Здесь можно добавить реальный API погоды
        weathers = ["☀️ солнечно", "☁️ облачно", "🌧 дождь", "❄️ снег", "⛈ гроза"]
        temp = random.randint(-10, 30)
        weather = random.choice(weathers)
        
        return (f"🌍 **ПОГОДА В {city.upper()}**\n\n"
                f"{weather}, {temp}°C\n"
                f"💨 Ветер: {random.randint(0, 10)} м/с\n"
                f"💧 Влажность: {random.randint(30, 90)}%")

    def cmd_news(self) -> str:
        news_list = [
            "🎮 Новое обновление бота! Добавлены питомцы!",
            "👾 Новый босс «Король демонов» уже на арене!",
            "🏆 Начинается еженедельный турнир!",
            "💎 Скидки на VIP статус до конца недели!",
            "🐾 Купи питомца и стань лучшим!"
        ]
        return f"📰 **НОВОСТИ**\n\n{random.choice(news_list)}"

    def cmd_quote(self) -> str:
        quotes = [
            "Жизнь — как коробка шоколадных конфет: никогда не знаешь, какая начинка тебе попадётся.",
            "Сложнее всего начать действовать, все остальное зависит только от упорства.",
            "Успех — это способность идти от поражения к поражению, не теряя энтузиазма.",
            "Лучший способ предсказать будущее — создать его.",
            "Не бойтесь, что у вас не получится. Бойтесь, что вы не попробуете."
        ]
        return f"📝 **ЦИТАТА ДНЯ**\n\n«{random.choice(quotes)}»"

    # === ОПРОСЫ ===
    def cmd_poll(self, user_data: Dict, args: List[str]) -> str:
        return "📊 Для создания опроса используй функцию платформы."

    # === ОТНОШЕНИЯ ===
    def cmd_marry(self, user_data: Dict, args: List[str], platform: str) -> str:
        if not args:
            return "❌ Укажи ID пользователя: /marry @username"
        
        query = args[0]
        target_data = self.db.get_user_by_name(query, platform)
        
        if not target_data:
            return "❌ Пользователь не найден"
        
        user_id = user_data['user_id']
        
        if user_data.get('marry_id', 0) != 0:
            return "❌ Ты уже в браке!"
        
        if user_data['level'] < 5:
            return "❌ Для брака нужен 5 уровень!"
        
        if target_data.get('marry_id', 0) != 0:
            return "❌ Этот пользователь уже в браке"
        
        return f"💍 Предложение отправлено пользователю {target_data.get('first_name')}!"

    def cmd_divorce(self, user_data: Dict) -> str:
        if self.db.divorce(user_data['user_id']):
            self.db.add_coins(user_data['user_id'], -500)
            return "💔 Брак расторгнут. Штраф: -500 🪙"
        return "❌ Ты не в браке"

    def cmd_love(self, user_data: Dict) -> str:
        marry_id = user_data.get('marry_id', 0)
        
        if marry_id == 0:
            return "❌ Ты не в браке"
        
        partner = self.db.get_user_by_id(marry_id)
        partner_name = partner.get('first_name', f"ID {marry_id}")
        
        return (f"💕 **ОЧКИ ЛЮБВИ**\n\n"
                f"▫️ **Супруг(а):** {partner_name}\n"
                f"▫️ **Очки любви:** {user_data.get('love_points', 0)} 💕\n"
                f"▫️ **Детей:** {user_data.get('children', 0)} 👶")

    def cmd_children(self, user_data: Dict) -> str:
        if user_data.get('marry_id', 0) == 0:
            return "❌ Ты не в браке"
        
        if user_data.get('love_points', 0) < 100:
            return "❌ Нужно 100 очков любви!"
        
        if user_data.get('children', 0) >= 5:
            return "❌ У вас уже 5 детей (максимум)"
        
        chance = min(0.3 + user_data['love_points'] / 1000, 0.7)
        
        if random.random() < chance:
            self.db.add_child(user_data['user_id'])
            self.db.add_love_points(user_data['user_id'], 50)
            children = user_data.get('children', 0) + 1
            gender = random.choice(["мальчик", "девочка"])
            
            return (f"👶 **ПОЗДРАВЛЯЮ!**\n\n"
                    f"У вас родился {gender}!\n"
                    f"Теперь у вас {children} детей!\n"
                    f"+50 💕 за пополнение в семье!")
        else:
            return "😢 Пока не получилось... Попробуй еще раз"

    # === ДОЛГИ ===
    def cmd_debt(self, user_data: Dict, args: List[str]) -> str:
        if len(args) < 3:
            return "❌ Использование: /debt [ник] [сумма] [причина]"
        
        query = args[0]
        try:
            amount = int(args[1])
            reason = " ".join(args[2:])
        except:
            return "❌ Неправильный формат"
        
        target_data = self.db.get_user_by_name(query)
        if not target_data:
            return "❌ Пользователь не найден"
        
        if target_data['user_id'] == user_data['user_id']:
            return "❌ Нельзя дать в долг самому себе"
        
        if user_data['coins'] < amount:
            return f"❌ У тебя только {user_data['coins']} 🪙"
        
        self.db.add_coins(user_data['user_id'], -amount)
        debt_id = self.db.create_debt(target_data['user_id'], user_data['user_id'], amount, reason)
        
        return f"💰 Долг оформлен! ID: {debt_id}"

    def cmd_debts(self, user_data: Dict) -> str:
        debts = self.db.get_debts(user_data['user_id'])
        
        if not debts:
            return "💰 У тебя нет активных долгов"
        
        text = "💰 **ТВОИ ДОЛГИ**\n\n"
        
        for debt in debts:
            debtor_id, creditor_id, amount, reason, created, deadline, is_paid = debt[1:8]
            
            if debtor_id == user_data['user_id']:
                role = "Ты должен"
                other_id = creditor_id
            else:
                role = "Должны тебе"
                other_id = debtor_id
            
            other = self.db.get_user_by_id(other_id)
            other_name = other.get('first_name', f"ID {other_id}")
            
            created_str = datetime.datetime.fromisoformat(created).strftime("%d.%m.%Y")
            
            text += f"**ID: {debt[0]}** — {role} {other_name}\n"
            text += f"└ Сумма: {amount} 🪙, Причина: {reason}, Создан: {created_str}\n\n"
        
        text += "Оплатить: /paydebt [ID]"
        return text

    def cmd_pay_debt(self, user_data: Dict, args: List[str]) -> str:
        if not args:
            return "❌ Укажи ID долга: /paydebt 1"
        
        try:
            debt_id = int(args[0])
        except:
            return "❌ Неправильный ID"
        
        self.db.cursor.execute("SELECT * FROM debts WHERE id = ?", (debt_id,))
        debt = self.db.cursor.fetchone()
        
        if not debt:
            return "❌ Долг не найден"
        
        debtor_id, creditor_id, amount, reason, created, deadline, is_paid = debt[1:8]
        
        if is_paid:
            return "❌ Долг уже оплачен"
        
        if debtor_id != user_data['user_id']:
            return "❌ Это не твой долг"
        
        if user_data['coins'] < amount:
            return f"❌ Недостаточно монет! Нужно {amount} 🪙"
        
        self.db.add_coins(user_data['user_id'], -amount)
        self.db.add_coins(creditor_id, amount)
        self.db.pay_debt(debt_id)
        
        return f"✅ Долг оплачен! Переведено {amount} 🪙"

    # === ЗАКЛАДКИ ===
    def cmd_add_bookmark(self, user_data: Dict, args: List[str], platform: str) -> str:
        if not args:
            return "❌ Укажи текст закладки: +закладка [текст]"
        
        text = " ".join(args)
        user_id = user_data['user_id']
        
        # Создаем ссылку на сообщение (заглушка)
        message_link = f"https://{'t.me' if platform=='tg' else 'vk.com'}/закладка/{user_id}/{int(time.time())}"
        
        bookmark_id = self.db.add_bookmark(user_id, text, message_link)
        
        return f"✅ Закладка сохранена! ID: {bookmark_id}"

    def cmd_bookmarks(self, user_data: Dict, args: List[str]) -> str:
        bookmarks = self.db.get_bookmarks(user_data['user_id'])
        
        if not bookmarks:
            return f"📌 У {user_data.get('first_name')} пока нет закладок."
        
        if args and args[0].isdigit():
            # Показываем конкретную закладку
            idx = int(args[0]) - 1
            if 0 <= idx < len(bookmarks):
                b_id, text, link, created = bookmarks[idx]
                created_str = datetime.datetime.fromisoformat(created).strftime("%d.%m.%Y %H:%M")
                return (f"📌 **ЗАКЛАДКА #{idx+1}**\n\n"
                        f"📝 {text}\n"
                        f"🔗 [Ссылка]({link})\n"
                        f"📅 {created_str}")
            else:
                return "❌ Закладка не найдена"
        
        # Показываем список
        text = f"📌 **ЗАКЛАДКИ {user_data.get('first_name').upper()}**\n\n"
        for i, (b_id, b_text, b_link, b_created) in enumerate(bookmarks, 1):
            created_short = datetime.datetime.fromisoformat(b_created).strftime("%d.%m.%Y")
            text += f"**{i}.** {b_text[:50]}... — {created_short}\n"
        
        text += f"\n💬 Для просмотра: закладки [номер]"
        return text

    # === АДМИНСКИЕ ===
    def cmd_mute(self, admin_data: Dict, args: List[str], platform: str) -> str:
        if not self.has_permission(admin_data, 'moderator'):
            return "❌ Недостаточно прав"
        
        if len(args) < 2:
            return "❌ Использование: /mute [ник] [минут]"
        
        query = args[0]
        try:
            minutes = int(args[1])
            reason = " ".join(args[2:]) if len(args) > 2 else "Нарушение"
        except:
            return "❌ Неправильный формат"
        
        target_data = self.db.get_user_by_name(query, platform)
        if not target_data:
            return "❌ Пользователь не найден"
        
        self.db.mute_user(target_data['user_id'], minutes, admin_data['user_id'], reason)
        
        return f"🔇 Пользователь {target_data.get('first_name')} замучен на {minutes} минут\nПричина: {reason}"

    def cmd_warn(self, admin_data: Dict, args: List[str], platform: str) -> str:
        if not self.has_permission(admin_data, 'moderator'):
            return "❌ Недостаточно прав"
        
        if not args:
            return "❌ Использование: /warn [ник] [причина]"
        
        query = args[0]
        reason = " ".join(args[1:]) if len(args) > 1 else "Нарушение"
        
        target_data = self.db.get_user_by_name(query, platform)
        if not target_data:
            return "❌ Пользователь не найден"
        
        result = self.db.add_warn(target_data['user_id'], admin_data['user_id'], reason)
        return result

    def cmd_ban(self, admin_data: Dict, args: List[str], platform: str) -> str:
        if not self.has_permission(admin_data, 'moderator'):
            return "❌ Недостаточно прав"
        
        if not args:
            return "❌ Использование: /ban [ник]"
        
        query = args[0]
        reason = " ".join(args[1:]) if len(args) > 1 else "Нарушение правил"
        
        target_data = self.db.get_user_by_name(query, platform)
        if not target_data:
            return "❌ Пользователь не найден"
        
        self.db.ban_user(target_data['user_id'], admin_data['user_id'])
        
        return f"🚫 Пользователь {target_data.get('first_name')} забанен\nПричина: {reason}"

    def cmd_unban(self, admin_data: Dict, args: List[str], platform: str) -> str:
        if not self.has_permission(admin_data, 'moderator'):
            return "❌ Недостаточно прав"
        
        if not args:
            return "❌ Использование: /unban [ник]"
        
        query = args[0]
        
        target_data = self.db.get_user_by_name(query, platform)
        if not target_data:
            return "❌ Пользователь не найден"
        
        self.db.unban_user(target_data['user_id'])
        
        return f"✅ Пользователь {target_data.get('first_name')} разбанен"

    def cmd_banlist(self, page: int = 1) -> str:
        bans = self.db.get_banlist(page)
        total_pages = (self.db.cursor.execute("SELECT COUNT(*) FROM users WHERE banned = 1").fetchone()[0] + 9) // 10
        
        if not bans:
            return "📋 Список забаненных пуст"
        
        text = f"🗓 **Список забаненных:** (стр. {page}/{total_pages})\n\n"
        
        for i, (user_id, name, banned, bans_count, last_seen) in enumerate(bans, 1):
            if last_seen:
                last = datetime.datetime.fromisoformat(last_seen).strftime("%d.%m.%Y")
            else:
                last = "неизвестно"
            
            text += f"{i}. {name} [ID: {user_id}]\n"
            text += f"⏱ Бан навсегда\n"
            text += f"📅 Последний визит: {last}\n\n"
        
        return text

    def cmd_mutelist(self, page: int = 1) -> str:
        mutes = self.db.get_mutelist(page)
        total_pages = (self.db.cursor.execute(
            "SELECT COUNT(*) FROM users WHERE mute_until IS NOT NULL AND mute_until > ?", 
            (datetime.datetime.now(),)
        ).fetchone()[0] + 9) // 10
        
        if not mutes:
            return "📋 Список замученных пуст"
        
        text = f"🔇 **Список замученных:** (стр. {page}/{total_pages})\n\n"
        
        for user_id, name, mute_until, mutes_count in mutes:
            if mute_until:
                until = datetime.datetime.fromisoformat(mute_until).strftime("%d.%m.%Y %H:%M")
            else:
                until = "неизвестно"
            
            text += f"▫️ {name} [ID: {user_id}]\n"
            text += f"⏱ До: {until}\n"
            text += f"⚠️ Всего мутов: {mutes_count}\n\n"
        
        return text

    def cmd_warnlist(self, page: int = 1) -> str:
        warns = self.db.get_warnlist(page)
        total_pages = (self.db.cursor.execute(
            "SELECT COUNT(*) FROM users WHERE warns > 0"
        ).fetchone()[0] + 9) // 10
        
        if not warns:
            return "📋 Список предупреждений пуст"
        
        text = f"⚠️ **Список предупреждений:** (стр. {page}/{total_pages})\n\n"
        
        for user_id, name, warns, warns_count in warns:
            text += f"▫️ {name} [ID: {user_id}]\n"
            text += f"⚠️ Текущих варнов: {warns}/3\n"
            text += f"📊 Всего варнов: {warns_count}\n\n"
        
        return text

    def cmd_give(self, admin_data: Dict, args: List[str], platform: str) -> str:
        if not self.has_permission(admin_data, 'admin'):
            return "❌ Недостаточно прав"
        
        if len(args) < 2:
            return "❌ Использование: /give [ник] [сумма]"
        
        query = args[0]
        try:
            amount = int(args[1])
        except:
            return "❌ Сумма должна быть числом"
        
        target_data = self.db.get_user_by_name(query, platform)
        if not target_data:
            return "❌ Пользователь не найден"
        
        self.db.add_coins(target_data['user_id'], amount)
        
        return f"✅ Пользователю {target_data.get('first_name')} выдано {amount} 🪙"

    # === КОМАНДЫ ДОНАТЕРОВ ===
    def cmd_donor_commands(self, user_data: Dict, args: List[str]) -> str:
        role = user_data.get('role', 'user')
        
        donor_commands = {
            'vip': ["🎮 /boss_fight — бонус +20% урона", "💰 /daily — бонус +50%"],
            'premium': ["🎮 /boss_fight — бонус +50% урона", "💰 /daily — бонус +100%", "💎 /payh — перевод алмазов"],
            'moderator': ["🔨 /mute — замутить", "⚠️ /warn — предупредить", "🚫 /ban — забанить"],
            'admin': ["💸 /give — выдать монеты", "👑 Все права модератора"],
            'owner': ["⚙️ Полный доступ к боту"]
        }
        
        if args and args[0].lower() in donor_commands:
            cmd_list = donor_commands[args[0].lower()]
            return f"📋 **Команды {args[0].upper()}**\n\n" + "\n".join(cmd_list)
        
        text = f"📋 **Твои команды ({role})**\n\n"
        
        for r, cmds in donor_commands.items():
            if self.has_permission(user_data, r):
                text += f"**{r.upper()}**\n" + "\n".join(cmds) + "\n\n"
        
        text += "\n📘 Подробнее: /cmd [привилегия]"
        return text

    # === ПРОЧИЕ КОМАНДЫ ===
    def cmd_players(self) -> str:
        count = self.db.get_players_count()
        return f"👥 **Всего игроков:** {count}"

    def cmd_eng_free(self, user_data: Dict) -> str:
        user_id = user_data['user_id']
        
        # Проверка, можно ли получить бесплатно
        last_free = user_data.get('last_free_energy')
        if last_free:
            last = datetime.datetime.fromisoformat(last_free)
            if (datetime.datetime.now() - last).seconds < 3600:  # Раз в час
                remaining = 3600 - (datetime.datetime.now() - last).seconds
                minutes = remaining // 60
                return f"❌ Бесплатную энергию можно получать раз в час. Осталось: {minutes} мин"
        
        energy = 20
        self.db.add_energy(user_id, energy)
        
        self.db.cursor.execute("UPDATE users SET last_free_energy = ? WHERE user_id = ?", 
                              (datetime.datetime.now(), user_id))
        self.db.conn.commit()
        
        return f"🔋 Ты получил {energy} ⚡ энергии!"

    def cmd_sms(self, user_data: Dict, args: List[str], platform: str) -> str:
        if len(args) < 2:
            return "❌ Использование: /sms [ник] [сообщение]"
        
        query = args[0]
        message = " ".join(args[1:])
        
        target_data = self.db.get_user_by_name(query, platform)
        if not target_data:
            return "❌ Пользователь не найден"
        
        # Здесь нужно отправить личное сообщение через платформу
        # В Telegram это будет сделано через адаптер, в VK тоже
        
        return f"💬 Сообщение для {target_data.get('first_name')} отправлено!"

    def cmd_mycrime(self, user_data: Dict) -> str:
        crimes = [
            ("158", "Кража"),
            ("161", "Грабеж"),
            ("162", "Разбой"),
            ("163", "Вымогательство"),
            ("205", "Террористический акт"),
            ("228", "Незаконный оборот наркотиков"),
            ("261", "Уничтожение лесных насаждений"),
            ("105", "Убийство"),
            ("111", "Умышленное причинение тяжкого вреда здоровью"),
            ("131", "Изнасилование"),
            ("158", "Мошенничество"),
            ("213", "Хулиганство")
        ]
        
        article_num, article_name = random.choice(crimes)
        sentence = random.randint(1, 15)
        
        today = datetime.datetime.now().strftime("%d.%m.%Y")
        name = user_data.get('first_name', 'Неизвестный')
        
        return (f"🤷‍♂️ Сегодня {today} {name} приговаривается к статье {article_num}. {article_name}\n"
                f"⏱ Срок: {sentence} {'год' if sentence==1 else 'года' if sentence<5 else 'лет'}")

    def cmd_automes(self, user_data: Dict, args: List[str]) -> str:
        if not args or args[0].lower() not in ['on', 'off']:
            return "❌ Использование: /automes on/off"
        
        state = 1 if args[0].lower() == 'on' else 0
        
        self.db.cursor.execute("UPDATE users SET automes_enabled = ? WHERE user_id = ?", 
                              (state, user_data['user_id']))
        self.db.conn.commit()
        
        return f"💬 Автосообщения {'включены' if state else 'выключены'}"

    def cmd_namutebuy(self, user_data: Dict) -> str:
        user_id = user_data['user_id']
        
        if not self.db.is_muted(user_id):
            return "❌ Ты не в муте"
        
        price = 200
        if user_data['coins'] < price:
            return f"❌ Недостаточно монет! Нужно {price} 🪙"
        
        self.db.add_coins(user_id, -price)
        self.db.cursor.execute("UPDATE users SET mute_until = NULL WHERE user_id = ?", (user_id,))
        self.db.conn.commit()
        
        return f"✅ Мут снят за {price} 🪙"

    # === КЛАВИАТУРЫ ===
    def get_main_menu_keyboard(self) -> List[List[Dict]]:
        return [
            [{"text": "👤 Профиль", "callback": "profile"}, {"text": "💍 Отношения", "callback": "marry"}],
            [{"text": "👾 Боссы", "callback": "bosses"}, {"text": "🎰 Казино", "callback": "casino"}],
            [{"text": "👥 Кланы", "callback": "clan"}, {"text": "🐾 Питомцы", "callback": "pet"}],
            [{"text": "🏆 Достижения", "callback": "achievements"}, {"text": "🛍 Магазин", "callback": "shop"}],
            [{"text": "💎 Привилегии", "callback": "donate"}, {"text": "📊 Топ", "callback": "top"}],
            [{"text": "📚 Помощь", "callback": "help"}]
        ]

    def get_boss_keyboard(self) -> List[List[Dict]]:
        return [
            [{"text": "👊 Атаковать", "callback": "boss_fight_1"}, {"text": "➕ Регенерация", "callback": "regen"}],
            [{"text": "🗡 Купить оружие", "callback": "shop"}, {"text": "📊 Статистика", "callback": "boss_stats"}],
            [{"text": "🔙 Назад", "callback": "menu_back"}]
        ]

    def get_casino_keyboard(self) -> List[List[Dict]]:
        return [
            [{"text": "🎰 Рулетка", "callback": "roulette"}, {"text": "🎲 Кости", "callback": "dice"}],
            [{"text": "🃏 Блэкджек", "callback": "blackjack"}, {"text": "🎰 Слоты", "callback": "slots"}],
            [{"text": "✊ КНБ", "callback": "rps"}, {"text": "📊 Статистика", "callback": "casino_stats"}],
            [{"text": "🔙 Назад", "callback": "menu_back"}]
        ]

    def get_rps_keyboard(self) -> List[List[Dict]]:
        return [
            [{"text": "🪨 Камень", "callback": "rps_rock"}, {"text": "✂️ Ножницы", "callback": "rps_scissors"}],
            [{"text": "📄 Бумага", "callback": "rps_paper"}, {"text": "📊 Статистика", "callback": "rps_stats"}],
            [{"text": "🔙 Назад", "callback": "menu_back"}]
        ]

    def get_clan_keyboard(self) -> List[List[Dict]]:
        return [
            [{"text": "📊 Инфо", "callback": "clan"}, {"text": "🏆 Топ", "callback": "clan_top"}],
            [{"text": "➕ Создать", "callback": "clan_create"}, {"text": "🚪 Выйти", "callback": "clan_leave"}],
            [{"text": "🔙 Назад", "callback": "menu_back"}]
        ]

    def get_pet_keyboard(self) -> List[List[Dict]]:
        return [
            [{"text": "🐾 Мои питомцы", "callback": "pet"}, {"text": "🛒 Купить", "callback": "pet_buy"}],
            [{"text": "🍖 Покормить", "callback": "pet_feed"}, {"text": "⚔️ Битва", "callback": "pet_fight"}],
            [{"text": "🔙 Назад", "callback": "menu_back"}]
        ]

    def get_shop_keyboard(self) -> List[List[Dict]]:
        return [
            [{"text": "💊 Зелья", "callback": "shop_potions"}, {"text": "⚔️ Оружие", "callback": "shop_weapons"}],
            [{"text": "🛡 Броня", "callback": "shop_armor"}, {"text": "⚡ Энергия", "callback": "shop_energy"}],
            [{"text": "🔙 Назад", "callback": "menu_back"}]
        ]

    def get_donate_keyboard(self) -> List[List[Dict]]:
        return [
            [{"text": "🌟 VIP", "callback": "vip"}, {"text": "💎 Premium", "callback": "premium"}],
            [{"text": "📋 Команды донатеров", "callback": "cmd"}, {"text": "👑 Владелец", "callback": "owner_info"}],
            [{"text": "🔙 Назад", "callback": "menu_back"}]
        ]

    def get_mafia_keyboard(self) -> List[List[Dict]]:
        return [
            [{"text": "🔪 Создать игру", "callback": "mafia_create"}, {"text": "🎮 Присоединиться", "callback": "mafia_join"}],
            [{"text": "📊 Статистика", "callback": "mafia_stats"}, {"text": "🔙 Назад", "callback": "menu_back"}]
        ]

    def get_marry_keyboard(self, args: List[str]) -> Optional[List[List[Dict]]]:
        if not args:
            return None
        return [
            [{"text": "💍 Согласиться", "callback": f"marry_accept_{args[0]}"},
             {"text": "💔 Отказаться", "callback": f"marry_decline_{args[0]}"}]
        ]

    def get_pagination_keyboard(self, list_type: str, page: int) -> List[List[Dict]]:
        keyboard = []
        
        # Подсчет страниц
        if list_type == "ban":
            total = (self.db.cursor.execute("SELECT COUNT(*) FROM users WHERE banned = 1").fetchone()[0] + 9) // 10
        elif list_type == "mute":
            total = (self.db.cursor.execute(
                "SELECT COUNT(*) FROM users WHERE mute_until IS NOT NULL AND mute_until > ?", 
                (datetime.datetime.now(),)
            ).fetchone()[0] + 9) // 10
        else:  # warn
            total = (self.db.cursor.execute("SELECT COUNT(*) FROM users WHERE warns > 0").fetchone()[0] + 9) // 10
        
        nav_row = []
        if page > 1:
            nav_row.append({"text": "⏪ Начало", "callback": f"{list_type}list_1"})
            nav_row.append({"text": "◀️ Назад", "callback": f"{list_type}list_{page-1}"})
        
        if page < total:
            nav_row.append({"text": "Вперед ▶️", "callback": f"{list_type}list_{page+1}"})
            nav_row.append({"text": "Конец ⏩", "callback": f"{list_type}list_{total}"})
        
        if nav_row:
            keyboard.append(nav_row)
        
        keyboard.append([{"text": "🔙 Назад", "callback": "menu_back"}])
        return keyboard

    def get_ttt_challenge_keyboard(self, args: List[str]) -> Optional[List[List[Dict]]]:
        if not args:
            return None
        return [
            [{"text": "✅ Принять", "callback": f"ttt_accept_{args[0]}"},
             {"text": "❌ Отклонить", "callback": f"ttt_decline_{args[0]}"}]
        ]

# ========== АДАПТЕР ДЛЯ TELEGRAM ==========
class TelegramBot:
    def __init__(self, token: str, game_bot: GameBot):
        self.game_bot = game_bot
        self.application = Application.builder().token(token).build()
        self.setup_handlers()
        logger.info("✅ Telegram адаптер инициализирован")

    def setup_handlers(self):
        self.application.add_handler(CommandHandler("start", self.handle_command))
        self.application.add_handler(CommandHandler("help", self.handle_command))
        self.application.add_handler(CommandHandler("menu", self.handle_command))
        self.application.add_handler(MessageHandler(filters.COMMAND, self.handle_command))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        self.application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, self.handle_new_members))

    async def handle_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        message = update.message.text
        command = message.split()[0][1:] if message.startswith('/') else ""
        args = message.split()[1:] if len(message.split()) > 1 else []

        if command == "start" and context.args:
            args = context.args

        response, keyboard_data, photo_bytes = await self.game_bot.process_command(
            platform="tg",
            platform_user_id=str(user.id),
            command=command,
            args=args,
            message_text=message
        )

        if response:
            reply_markup = self.convert_keyboard(keyboard_data) if keyboard_data else None
            if photo_bytes:
                await update.message.reply_photo(photo=photo_bytes, caption=response, parse_mode='Markdown')
            else:
                await update.message.reply_text(response, reply_markup=reply_markup, parse_mode='Markdown')

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        message = update.message.text

        response, keyboard_data, photo_bytes = await self.game_bot.process_command(
            platform="tg",
            platform_user_id=str(user.id),
            command="",
            args=[],
            message_text=message
        )

        if response:
            reply_markup = self.convert_keyboard(keyboard_data) if keyboard_data else None
            await update.message.reply_text(response, reply_markup=reply_markup, parse_mode='Markdown')

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user = query.from_user
        data = query.data

        # Разбираем callback
        if data == "menu_back":
            response, keyboard_data, _ = await self.game_bot.process_command("tg", str(user.id), "menu", [], "")
            reply_markup = self.convert_keyboard(keyboard_data) if keyboard_data else None
            await query.edit_message_text(response, reply_markup=reply_markup, parse_mode='Markdown')
        
        elif data == "profile":
            response, keyboard_data, _ = await self.game_bot.process_command("tg", str(user.id), "profile", [], "")
            await query.edit_message_text(response, parse_mode='Markdown')
        
        elif data == "bosses":
            response, keyboard_data, _ = await self.game_bot.process_command("tg", str(user.id), "bosses", [], "")
            reply_markup = self.convert_keyboard(keyboard_data) if keyboard_data else None
            await query.edit_message_text(response, reply_markup=reply_markup, parse_mode='Markdown')
        
        elif data == "casino":
            response, keyboard_data, _ = await self.game_bot.process_command("tg", str(user.id), "casino", [], "")
            reply_markup = self.convert_keyboard(keyboard_data) if keyboard_data else None
            await query.edit_message_text(response, reply_markup=reply_markup, parse_mode='Markdown')
        
        elif data == "clan":
            response, keyboard_data, _ = await self.game_bot.process_command("tg", str(user.id), "clan", [], "")
            reply_markup = self.convert_keyboard(keyboard_data) if keyboard_data else None
            await query.edit_message_text(response, reply_markup=reply_markup, parse_mode='Markdown')
        
        elif data == "pet":
            response, keyboard_data, _ = await self.game_bot.process_command("tg", str(user.id), "pet", [], "")
            reply_markup = self.convert_keyboard(keyboard_data) if keyboard_data else None
            await query.edit_message_text(response, reply_markup=reply_markup, parse_mode='Markdown')
        
        elif data == "achievements":
            response, _, _ = await self.game_bot.process_command("tg", str(user.id), "achievements", [], "")
            await query.edit_message_text(response, parse_mode='Markdown')
        
        elif data == "shop":
            response, keyboard_data, _ = await self.game_bot.process_command("tg", str(user.id), "shop", [], "")
            reply_markup = self.convert_keyboard(keyboard_data) if keyboard_data else None
            await query.edit_message_text(response, reply_markup=reply_markup, parse_mode='Markdown')
        
        elif data == "donate":
            response, keyboard_data, _ = await self.game_bot.process_command("tg", str(user.id), "donate", [], "")
            reply_markup = self.convert_keyboard(keyboard_data) if keyboard_data else None
            await query.edit_message_text(response, reply_markup=reply_markup, parse_mode='Markdown')
        
        elif data == "top":
            response, _, _ = await self.game_bot.process_command("tg", str(user.id), "top", [], "")
            await query.edit_message_text(response, parse_mode='Markdown')
        
        elif data == "help":
            response, keyboard_data, _ = await self.game_bot.process_command("tg", str(user.id), "help", [], "")
            reply_markup = self.convert_keyboard(keyboard_data) if keyboard_data else None
            await query.edit_message_text(response, reply_markup=reply_markup, parse_mode='Markdown')
        
        elif data == "regen":
            response, _, _ = await self.game_bot.process_command("tg", str(user.id), "regen", [], "")
            await query.edit_message_text(response, parse_mode='Markdown')
        
        elif data == "boss_stats":
            response, _, _ = await self.game_bot.process_command("tg", str(user.id), "boss_stats", [], "")
            await query.edit_message_text(response, parse_mode='Markdown')
        
        elif data == "casino_stats":
            response, _, _ = await self.game_bot.process_command("tg", str(user.id), "casino_stats", [], "")
            await query.edit_message_text(response, parse_mode='Markdown')
        
        elif data == "rps_stats":
            response, _, _ = await self.game_bot.process_command("tg", str(user.id), "rps_stats", [], "")
            await query.edit_message_text(response, parse_mode='Markdown')
        
        elif data == "mafia_stats":
            response, _, _ = await self.game_bot.process_command("tg", str(user.id), "mafia_stats", [], "")
            await query.edit_message_text(response, parse_mode='Markdown')
        
        elif data.startswith("boss_fight_"):
            boss_id = data.split('_')[2]
            response, _, _ = await self.game_bot.process_command("tg", str(user.id), "boss_fight", [boss_id], "")
            await query.edit_message_text(response, parse_mode='Markdown')
        
        elif data.startswith("rps_"):
            choice = data.split('_')[1]
            response, _, _ = await self.game_bot.process_command("tg", str(user.id), "rps", [], f"rps_{choice}")
            await query.edit_message_text(response, parse_mode='Markdown')
        
        elif data.startswith("clan_"):
            if data == "clan_top":
                response, _, _ = await self.game_bot.process_command("tg", str(user.id), "clan_top", [], "")
                await query.edit_message_text(response, parse_mode='Markdown')
            elif data == "clan_leave":
                response, _, _ = await self.game_bot.process_command("tg", str(user.id), "clan_leave", [], "")
                await query.edit_message_text(response, parse_mode='Markdown')
        
        elif data.startswith("pet_"):
            if data == "pet_buy":
                response, _, _ = await self.game_bot.process_command("tg", str(user.id), "pet_buy", [], "")
                await query.edit_message_text(response, parse_mode='Markdown')
            elif data == "pet_feed":
                response, _, _ = await self.game_bot.process_command("tg", str(user.id), "pet_feed", [], "")
                await query.edit_message_text(response, parse_mode='Markdown')
        
        elif data.startswith("shop_"):
            if data == "shop_potions":
                response, _, _ = await self.game_bot.process_command("tg", str(user.id), "shop", [], "")
                await query.edit_message_text(response + "\n\nВыбери товар: /buy [название]", parse_mode='Markdown')
        
        elif data == "vip":
            response, _, _ = await self.game_bot.process_command("tg", str(user.id), "vip", [], "")
            await query.edit_message_text(response, parse_mode='Markdown')
        
        elif data == "premium":
            response, _, _ = await self.game_bot.process_command("tg", str(user.id), "premium", [], "")
            await query.edit_message_text(response, parse_mode='Markdown')
        
        elif data == "cmd":
            response, _, _ = await self.game_bot.process_command("tg", str(user.id), "cmd", [], "")
            await query.edit_message_text(response, parse_mode='Markdown')
        
        elif data.startswith("mafia_"):
            if data == "mafia_create":
                response, _, _ = await self.game_bot.process_command("tg", str(user.id), "mafia_create", [], "")
                await query.edit_message_text(response, parse_mode='Markdown')
            elif data == "mafia_join":
                response, _, _ = await self.game_bot.process_command("tg", str(user.id), "mafia_join", [], "")
                await query.edit_message_text(response, parse_mode='Markdown')
        
        elif data.startswith(("banlist_", "mutelist_", "warnlist_")):
            parts = data.split('_')
            list_type = parts[0]
            page = int(parts[1]) if len(parts) > 1 else 1
            response, keyboard_data, _ = await self.game_bot.process_command("tg", str(user.id), list_type, [str(page)], "")
            reply_markup = self.convert_keyboard(keyboard_data) if keyboard_data else None
            await query.edit_message_text(response, reply_markup=reply_markup, parse_mode='Markdown')

    def convert_keyboard(self, keyboard_data: List[List[Dict]]) -> Optional[InlineKeyboardMarkup]:
        if not keyboard_data:
            return None
        keyboard = []
        for row in keyboard_data:
            keyboard_row = []
            for button in row:
                keyboard_row.append(InlineKeyboardButton(button['text'], callback_data=button['callback']))
            keyboard.append(keyboard_row)
        return InlineKeyboardMarkup(keyboard)

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()

        response, _, _ = await self.game_bot.process_command(
            platform="tg",
            platform_user_id=str(user.id),
            command="draw",
            args=[],
            message_text="",
            photo_bytes=photo_bytes
        )

        if response:
            await update.message.reply_text(response)

    async def handle_new_members(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        for member in update.message.new_chat_members:
            if member.is_bot:
                continue
            await update.message.reply_text(f"🌟 Добро пожаловать, {member.first_name}!")

    async def run(self):
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        logger.info("🚀 Telegram бот запущен")

    async def close(self):
        await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()

# ========== АДАПТЕР ДЛЯ VK ==========
class VKBot:
    def __init__(self, token: str, group_id: int, game_bot: GameBot):
        self.game_bot = game_bot
        self.vk_session = vk_api.VkApi(token=token)
        self.vk = self.vk_session.get_api()
        self.longpoll = VkBotLongPoll(self.vk_session, group_id)
        self.group_id = group_id
        logger.info("✅ VK адаптер инициализирован")

    def convert_keyboard(self, keyboard_data: List[List[Dict]]) -> Optional[str]:
        if not keyboard_data:
            return None
        
        keyboard = {
            "one_time": False,
            "inline": True,
            "buttons": []
        }
        
        for row in keyboard_data:
            buttons_row = []
            for button in row:
                buttons_row.append({
                    "action": {
                        "type": "callback",
                        "label": button['text'],
                        "payload": json.dumps({"command": button['callback']})
                    },
                    "color": "primary"
                })
            keyboard["buttons"].append(buttons_row)
        
        return json.dumps(keyboard, ensure_ascii=False)

    def run(self):
        logger.info("🚀 VK бот запущен, ожидаем события...")
        
        for event in self.longpoll.listen():
            try:
                if event.type == VkBotEventType.MESSAGE_NEW:
                    self.handle_message(event)
                elif event.type == VkBotEventType.MESSAGE_EVENT:
                    self.handle_callback(event)
            except Exception as e:
                logger.error(f"Ошибка в VK: {e}")

    def handle_message(self, event):
        msg = event.object['message']
        user_id = msg['from_id']
        peer_id = msg['peer_id']
        text = msg['text']

        command = ""
        args = []
        if text.startswith('/') or text.startswith('!'):
            parts = text[1:].split()
            command = parts[0]
            args = parts[1:]

        # Создаем новый цикл событий для асинхронного вызова
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            response, keyboard_data, photo_bytes = loop.run_until_complete(
                self.game_bot.process_command(
                    platform="vk",
                    platform_user_id=str(user_id),
                    command=command,
                    args=args,
                    message_text=text
                )
            )
        finally:
            loop.close()

        if response:
            keyboard_json = self.convert_keyboard(keyboard_data)
            
            # Отправляем сообщение
            self.vk.messages.send(
                peer_id=peer_id,
                message=response,
                random_id=get_random_id(),
                keyboard=keyboard_json
            )

    def handle_callback(self, event):
        obj = event.object
        user_id = obj['user_id']
        peer_id = obj['peer_id']
        payload = json.loads(obj['payload'])
        command = payload.get('command', '')

        # Здесь обрабатываем callback аналогично Telegram
        # Для упрощения просто показываем, что кнопка нажата
        self.vk.messages.sendMessageEventAnswer(
            event_id=obj['event_id'],
            user_id=user_id,
            peer_id=peer_id,
            event_data=json.dumps({"type": "show_snackbar", "text": "Команда принята!"})
        )

    async def run_async(self):
        # Запускаем в отдельном потоке, так как longpoll синхронный
        import threading
        thread = threading.Thread(target=self.run)
        thread.daemon = True
        thread.start()
        logger.info("🔄 VK бот запущен в отдельном потоке")

    async def close(self):
        pass

# ========== ТОЧКА ВХОДА ==========
async def main():
    # Инициализация компонентов
    ai = HuggingFaceAI(HUGGINGFACE_TOKEN)
    game_core = GameBot(db, ai)
    
    tg_bot = TelegramBot(TELEGRAM_TOKEN, game_core)
    vk_bot = VKBot(VK_GROUP_TOKEN, VK_GROUP_ID, game_core)
    
    # Запуск
    try:
        await tg_bot.run()
        await vk_bot.run_async()
        
        # Держим программу запущенной
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Остановка ботов...")
        await tg_bot.close()
        await vk_bot.close()
        await ai.close()
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
