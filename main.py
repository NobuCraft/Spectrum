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
import math

# Для Telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# Для VK
try:
    from vkbottle import API, Bot
    from vkbottle.bot import Message
    from vkbottle_types.events import GroupEventType
    VKBOTTLE_AVAILABLE = True
except ImportError:
    VKBOTTLE_AVAILABLE = False
    print("⚠️ vkbottle не установлен. VK бот будет отключен.")

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===================== КОНФИГУРАЦИЯ =====================
# Telegram
TELEGRAM_TOKEN = "8326390250:AAEpXRnhLLLi5zUeFC39nfkHDlxR5ZFQ_yQ"
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

# Ранги модераторов (как в Iris)
MODER_RANKS = {
    0: "👤 Пользователь",
    1: "🛡️ Младший модератор",
    2: "⚔️ Старший модератор",
    3: "👑 Младший администратор",
    4: "💎 Старший администратор",
    5: "⭐ Создатель"
}

# Привилегии (ваши)
PRIVILEGES = {
    "вип": {"price": 5000, "days": 30, "emoji": "🌟", "commands": ["/regen_x2", "/boss_fight_x2"]},
    "премиум": {"price": 15000, "days": 30, "emoji": "💎", "commands": ["/regen_x3", "/boss_fight_x3", "/heal_all"]},
    "лорд": {"price": 30000, "days": 30, "emoji": "👑", "commands": ["/god_mode", "/boss_instant"]},
    "ультра": {"price": 50000, "days": 60, "emoji": "⚡", "commands": ["/super_attack", "/boss_double"]},
    "легенда": {"price": 100000, "days": 90, "emoji": "🏆", "commands": ["/legendary_skill"]},
    "эврольд": {"price": 200000, "days": 180, "emoji": "🌌", "commands": ["/cosmic_power"]},
    "властелин": {"price": 500000, "days": 365, "emoji": "👾", "commands": ["/master_control"]},
    "титан": {"price": 1000000, "days": 365, "emoji": "🗿", "commands": ["/titan_strike"]},
    "терминатор": {"price": 2000000, "days": 365, "emoji": "🤖", "commands": ["/terminate"]},
    "маг": {"price": 75000, "days": 60, "emoji": "🔮", "commands": ["/spell", "/magic_shield"]}
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
    {"id": 1, "name": "🦟 Ядовитый комар", "level": 5, "health": 2780, "max_health": 2780, "damage": 34, "reward": 500},
    {"id": 2, "name": "🐉 Огненный дракон", "level": 10, "health": 5000, "max_health": 5000, "damage": 50, "reward": 1000},
    {"id": 3, "name": "❄️ Ледяной великан", "level": 15, "health": 8000, "max_health": 8000, "damage": 70, "reward": 1500},
    {"id": 4, "name": "⚔️ Темный рыцарь", "level": 20, "health": 12000, "max_health": 12000, "damage": 90, "reward": 2000},
    {"id": 5, "name": "👾 Король демонов", "level": 25, "health": 20000, "max_health": 20000, "damage": 120, "reward": 3000},
    {"id": 6, "name": "💀 Бог разрушения", "level": 30, "health": 30000, "max_health": 30000, "damage": 150, "reward": 5000}
]

# ===================== БАЗА ДАННЫХ =====================
class Database:
    def __init__(self, db_name="spectrum_bot.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
        self.init_bosses()
    
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
                mod_rank INTEGER DEFAULT 0,
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
                description TEXT DEFAULT '',
                gender TEXT DEFAULT 'unknown',
                nickname TEXT DEFAULT '',
                birthday TEXT DEFAULT '',
                city TEXT DEFAULT '',
                mafia_wins INTEGER DEFAULT 0,
                mafia_games INTEGER DEFAULT 0,
                rps_wins INTEGER DEFAULT 0,
                rps_losses INTEGER DEFAULT 0,
                rps_draws INTEGER DEFAULT 0,
                casino_wins INTEGER DEFAULT 0,
                casino_losses INTEGER DEFAULT 0,
                ttt_wins INTEGER DEFAULT 0,
                ttt_losses INTEGER DEFAULT 0,
                ttt_draws INTEGER DEFAULT 0,
                rr_wins INTEGER DEFAULT 0,
                rr_losses INTEGER DEFAULT 0,
                minesweeper_wins INTEGER DEFAULT 0,
                minesweeper_games INTEGER DEFAULT 0
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
                warn_expire TIMESTAMP
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
                is_alive INTEGER DEFAULT 1
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
                rules TEXT DEFAULT '',
                warns_limit INTEGER DEFAULT 3,
                warns_ban_period TEXT DEFAULT '1 день',
                warns_period TEXT DEFAULT '30 дней',
                mute_period TEXT DEFAULT '1 неделя',
                ban_period TEXT DEFAULT 'навсегда',
                language TEXT DEFAULT 'ru'
            )
        ''')
        
        # Русская рулетка - лобби
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS rr_lobbies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_id TEXT,
                max_players INTEGER,
                bet INTEGER,
                players TEXT,
                status TEXT DEFAULT 'waiting',
                created_at TIMESTAMP
            )
        ''')
        
        # Русская рулетка - игры
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS rr_games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lobby_id INTEGER,
                players TEXT,
                current_player INTEGER,
                cylinder_size INTEGER,
                bullets INTEGER,
                positions TEXT,
                alive_players TEXT,
                phase TEXT,
                items TEXT,
                started_at TIMESTAMP
            )
        ''')
        
        # Предметы для русской рулетки
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS rr_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                item_name TEXT,
                item_type TEXT,
                quantity INTEGER DEFAULT 1
            )
        ''')
        
        # Крестики-нолики 3D - игры
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS ttt_games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_x TEXT,
                player_o TEXT,
                current_player TEXT,
                main_board TEXT,
                sub_boards TEXT,
                last_move INTEGER,
                status TEXT,
                started_at TIMESTAMP
            )
        ''')
        
        # Мафия - игры
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS mafia_games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_id TEXT,
                players TEXT,
                roles TEXT,
                phase TEXT DEFAULT 'night',
                day_count INTEGER DEFAULT 1,
                status TEXT DEFAULT 'waiting',
                created_at TIMESTAMP
            )
        ''')
        
        # Сапёр - игры
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS minesweeper_games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                width INTEGER,
                height INTEGER,
                mines INTEGER,
                board TEXT,
                revealed TEXT,
                flags TEXT,
                status TEXT,
                started_at TIMESTAMP,
                last_move TIMESTAMP
            )
        ''')
        
        self.conn.commit()
    
    def init_bosses(self):
        self.cursor.execute("SELECT COUNT(*) FROM bosses")
        if self.cursor.fetchone()[0] == 0:
            for boss in BOSSES:
                self.cursor.execute('''
                    INSERT INTO bosses (boss_name, boss_level, boss_health, boss_max_health, boss_damage, boss_reward)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (boss['name'], boss['level'], boss['health'], boss['max_health'], boss['damage'], boss['reward']))
            self.conn.commit()
    
    def respawn_bosses(self):
        self.cursor.execute("UPDATE bosses SET is_alive = 1, boss_health = boss_max_health")
        self.conn.commit()
    
    def get_user(self, platform, platform_id, username="", first_name="", last_name=""):
        self.cursor.execute(
            "SELECT * FROM users WHERE platform = ? AND platform_id = ?",
            (platform, platform_id)
        )
        user = self.cursor.fetchone()
        
        if not user:
            mod_rank = 5 if (platform == 'tg' and int(platform_id) == OWNER_ID_TG) or (platform == 'vk' and int(platform_id) == OWNER_ID_VK) else 0
            self.cursor.execute('''
                INSERT INTO users (platform, platform_id, username, first_name, last_name, mod_rank, first_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (platform, platform_id, username, first_name, last_name, mod_rank, datetime.datetime.now()))
            self.conn.commit()
            return self.get_user(platform, platform_id, username, first_name, last_name)
        
        columns = [description[0] for description in self.cursor.description]
        return dict(zip(columns, user))
    
    def update_activity(self, platform, platform_id):
        self.cursor.execute(
            "UPDATE users SET last_activity = ? WHERE platform = ? AND platform_id = ?",
            (datetime.datetime.now(), platform, platform_id)
        )
        self.conn.commit()
    
    def add_coins(self, platform, platform_id, amount, currency="coins"):
        if currency == "coins":
            self.cursor.execute("UPDATE users SET coins = coins + ? WHERE platform = ? AND platform_id = ?", (amount, platform, platform_id))
        elif currency == "diamonds":
            self.cursor.execute("UPDATE users SET diamonds = diamonds + ? WHERE platform = ? AND platform_id = ?", (amount, platform, platform_id))
        elif currency == "rr_money":
            self.cursor.execute("UPDATE users SET rr_money = rr_money + ? WHERE platform = ? AND platform_id = ?", (amount, platform, platform_id))
        elif currency == "energy":
            self.cursor.execute("UPDATE users SET energy = energy + ? WHERE platform = ? AND platform_id = ?", (amount, platform, platform_id))
        self.conn.commit()
    
    def transfer_money(self, from_platform, from_id, to_platform, to_id, amount, currency="coins"):
        from_user = self.get_user(from_platform, from_id)
        if currency == "coins" and from_user['coins'] < amount:
            return False, "Недостаточно монет"
        if currency == "diamonds" and from_user['diamonds'] < amount:
            return False, "Недостаточно алмазов"
        
        self.add_coins(from_platform, from_id, -amount, currency)
        self.add_coins(to_platform, to_id, amount, currency)
        
        self.cursor.execute('''
            INSERT INTO transactions (from_id, to_id, amount, currency, reason)
            VALUES (?, ?, ?, ?, ?)
        ''', (f"{from_platform}:{from_id}", f"{to_platform}:{to_id}", amount, currency, "transfer"))
        self.conn.commit()
        
        return True, f"Переведено {amount} {currency}"
    
    def add_exp(self, platform, platform_id, exp):
        self.cursor.execute(
            "UPDATE users SET exp = exp + ? WHERE platform = ? AND platform_id = ?",
            (exp, platform, platform_id)
        )
        self.cursor.execute(
            "SELECT exp, level FROM users WHERE platform = ? AND platform_id = ?",
            (platform, platform_id)
        )
        user = self.cursor.fetchone()
        if user and user[0] >= user[1] * 100:
            self.cursor.execute(
                "UPDATE users SET level = level + 1, exp = exp - ? WHERE platform = ? AND platform_id = ?",
                (user[1] * 100, platform, platform_id)
            )
        self.conn.commit()
    
    def damage_user(self, platform, platform_id, damage):
        self.cursor.execute(
            "UPDATE users SET health = health - ? WHERE platform = ? AND platform_id = ?",
            (damage, platform, platform_id)
        )
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
    
    def heal_user(self, platform, platform_id, amount):
        self.cursor.execute(
            "UPDATE users SET health = health + ? WHERE platform = ? AND platform_id = ?",
            (amount, platform, platform_id)
        )
        self.cursor.execute(
            "UPDATE users SET health = max_health WHERE health > max_health AND platform = ? AND platform_id = ?",
            (platform, platform_id)
        )
        self.conn.commit()
    
    def regen_available(self, platform, platform_id):
        self.cursor.execute("SELECT regen_available FROM users WHERE platform = ? AND platform_id = ?", (platform, platform_id))
        result = self.cursor.fetchone()
        if result and result[0]:
            return datetime.datetime.now() >= datetime.datetime.fromisoformat(result[0])
        return True
    
    def use_regen(self, platform, platform_id, cooldown_minutes=5):
        regen_until = datetime.datetime.now() + datetime.timedelta(minutes=cooldown_minutes)
        self.cursor.execute("UPDATE users SET regen_available = ? WHERE platform = ? AND platform_id = ?", (regen_until, platform, platform_id))
        self.conn.commit()
    
    def get_boss(self):
        self.cursor.execute("SELECT * FROM bosses WHERE is_alive = 1 ORDER BY id LIMIT 1")
        boss = self.cursor.fetchone()
        if not boss:
            self.respawn_bosses()
            return self.get_boss()
        columns = [description[0] for description in self.cursor.description]
        return dict(zip(columns, boss))
    
    def get_next_boss(self):
        self.cursor.execute("SELECT * FROM bosses WHERE is_alive = 1 ORDER BY id LIMIT 1")
        boss = self.cursor.fetchone()
        if boss:
            columns = [description[0] for description in self.cursor.description]
            return dict(zip(columns, boss))
        return None
    
    def damage_boss(self, boss_id, damage):
        self.cursor.execute("UPDATE bosses SET boss_health = boss_health - ? WHERE id = ?", (damage, boss_id))
        self.conn.commit()
        self.cursor.execute("SELECT boss_health FROM bosses WHERE id = ?", (boss_id,))
        health = self.cursor.fetchone()[0]
        if health <= 0:
            self.cursor.execute("UPDATE bosses SET is_alive = 0 WHERE id = ?", (boss_id,))
            self.conn.commit()
            return True, 0
        return False, health
    
    def add_boss_kill(self, platform, platform_id):
        self.cursor.execute("UPDATE users SET boss_kills = boss_kills + 1 WHERE platform = ? AND platform_id = ?", (platform, platform_id))
        self.conn.commit()
    
    def get_player_count(self):
        week_ago = datetime.datetime.now() - datetime.timedelta(days=7)
        self.cursor.execute("SELECT COUNT(*) FROM users WHERE last_activity > ?", (week_ago,))
        return self.cursor.fetchone()[0]
    
    def get_top(self, by="coins", limit=10):
        self.cursor.execute(f"SELECT username, first_name, {by} FROM users ORDER BY {by} DESC LIMIT ?", (limit,))
        return self.cursor.fetchall()
    
    def get_user_by_username(self, platform, username):
        username = username.lstrip('@')
        self.cursor.execute(
            "SELECT * FROM users WHERE platform = ? AND (username LIKE ? OR first_name LIKE ?)",
            (platform, f"%{username}%", f"%{username}%")
        )
        return self.cursor.fetchone()
    
    def get_user_by_id(self, platform, platform_id):
        self.cursor.execute(
            "SELECT * FROM users WHERE platform = ? AND platform_id = ?",
            (platform, platform_id)
        )
        return self.cursor.fetchone()
    
    def add_bookmark(self, platform, platform_id, description, message_link, message_text):
        self.cursor.execute('''
            INSERT INTO bookmarks (platform, platform_id, description, message_link, message_text)
            VALUES (?, ?, ?, ?, ?)
        ''', (platform, platform_id, description, message_link, message_text))
        self.conn.commit()
    
    def get_bookmarks(self, platform, platform_id):
        self.cursor.execute(
            "SELECT * FROM bookmarks WHERE platform = ? AND platform_id = ? ORDER BY timestamp DESC",
            (platform, platform_id)
        )
        return self.cursor.fetchall()
    
    def add_award(self, platform, platform_id, award_name, award_description, awarded_by, awarded_by_name):
        self.cursor.execute('''
            INSERT INTO awards (platform, platform_id, award_name, award_description, awarded_by, awarded_by_name, award_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (platform, platform_id, award_name, award_description, awarded_by, awarded_by_name, datetime.datetime.now()))
        self.conn.commit()
    
    def get_awards(self, platform, platform_id):
        self.cursor.execute(
            "SELECT * FROM awards WHERE platform = ? AND platform_id = ? ORDER BY award_date DESC",
            (platform, platform_id)
        )
        return self.cursor.fetchall()
    
    def is_muted(self, platform, platform_id):
        self.cursor.execute("SELECT mute_until FROM users WHERE platform = ? AND platform_id = ?", (platform, platform_id))
        result = self.cursor.fetchone()
        if result and result[0]:
            return datetime.datetime.now() < datetime.datetime.fromisoformat(result[0])
        return False
    
    def mute_user(self, platform, platform_id, username, minutes, reason, muted_by, muted_by_name):
        mute_until = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
        self.cursor.execute("UPDATE users SET mute_until = ? WHERE platform = ? AND platform_id = ?", (mute_until, platform, platform_id))
        self.cursor.execute('''
            INSERT INTO mutes (platform, platform_id, username, reason, muted_by, muted_by_name, mute_date, mute_duration, mute_until, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (platform, platform_id, username, reason, muted_by, muted_by_name, datetime.datetime.now(), f"{minutes} мин", mute_until, 1))
        self.conn.commit()
        return mute_until
    
    def unmute_user(self, platform, platform_id):
        self.cursor.execute("UPDATE users SET mute_until = NULL WHERE platform = ? AND platform_id = ?", (platform, platform_id))
        self.cursor.execute("UPDATE mutes SET is_active = 0 WHERE platform = ? AND platform_id = ?", (platform, platform_id))
        self.conn.commit()
    
    def add_warn(self, platform, platform_id, username, reason, warned_by, warned_by_name, days=30):
        warn_expire = datetime.datetime.now() + datetime.timedelta(days=days)
        self.cursor.execute("UPDATE users SET warns = warns + 1 WHERE platform = ? AND platform_id = ?", (platform, platform_id))
        self.cursor.execute('''
            INSERT INTO warns (platform, platform_id, username, reason, warned_by, warned_by_name, warn_date, warn_expire)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (platform, platform_id, username, reason, warned_by, warned_by_name, datetime.datetime.now(), warn_expire))
        self.conn.commit()
        self.cursor.execute("SELECT warns FROM users WHERE platform = ? AND platform_id = ?", (platform, platform_id))
        return self.cursor.fetchone()[0]
    
    def remove_warn(self, platform, platform_id, warn_id=None):
        if warn_id:
            self.cursor.execute("DELETE FROM warns WHERE id = ?", (warn_id,))
        else:
            self.cursor.execute("DELETE FROM warns WHERE platform = ? AND platform_id = ? ORDER BY warn_date DESC LIMIT 1", (platform, platform_id))
        self.cursor.execute("UPDATE users SET warns = warns - 1 WHERE platform = ? AND platform_id = ? AND warns > 0", (platform, platform_id))
        self.conn.commit()
    
    def get_warns(self, platform, platform_id):
        self.cursor.execute("SELECT * FROM warns WHERE platform = ? AND platform_id = ? ORDER BY warn_date DESC", (platform, platform_id))
        return self.cursor.fetchall()
    
    def get_warned_users(self, page=1, per_page=10):
        offset = (page - 1) * per_page
        self.cursor.execute('''
            SELECT * FROM warns ORDER BY warn_date DESC LIMIT ? OFFSET ?
        ''', (per_page, offset))
        return self.cursor.fetchall()
    
    def ban_user(self, platform, platform_id, username, reason, duration, banned_by, banned_by_name):
        is_permanent = duration.lower() == "навсегда"
        ban_until = None
        if not is_permanent:
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
        
        self.cursor.execute("UPDATE users SET banned = 1, ban_reason = ?, ban_date = ?, banned_by = ? WHERE platform = ? AND platform_id = ?", 
                           (reason, datetime.datetime.now(), banned_by, platform, platform_id))
        self.cursor.execute('''
            INSERT INTO bans (platform, platform_id, username, reason, banned_by, banned_by_name, ban_date, ban_duration, ban_until, is_permanent, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (platform, platform_id, username, reason, banned_by, banned_by_name, datetime.datetime.now(), duration, ban_until, 1 if is_permanent else 0, 1))
        self.conn.commit()
    
    def unban_user(self, platform, platform_id):
        self.cursor.execute("UPDATE users SET banned = 0, ban_reason = NULL WHERE platform = ? AND platform_id = ?", (platform, platform_id))
        self.cursor.execute("UPDATE bans SET is_active = 0 WHERE platform = ? AND platform_id = ?", (platform, platform_id))
        self.conn.commit()
    
    def is_banned(self, platform, platform_id):
        self.cursor.execute("SELECT banned FROM users WHERE platform = ? AND platform_id = ?", (platform, platform_id))
        result = self.cursor.fetchone()
        return result and result[0] == 1
    
    def get_banned_users(self, page=1, per_page=10):
        offset = (page - 1) * per_page
        self.cursor.execute('''
            SELECT * FROM bans WHERE is_active = 1 ORDER BY ban_date DESC LIMIT ? OFFSET ?
        ''', (per_page, offset))
        return self.cursor.fetchall()
    
    def get_muted_users(self, page=1, per_page=10):
        offset = (page - 1) * per_page
        self.cursor.execute('''
            SELECT * FROM mutes WHERE is_active = 1 ORDER BY mute_date DESC LIMIT ? OFFSET ?
        ''', (per_page, offset))
        return self.cursor.fetchall()
    
    def get_mod_rank(self, platform, platform_id):
        self.cursor.execute("SELECT mod_rank FROM users WHERE platform = ? AND platform_id = ?", (platform, platform_id))
        result = self.cursor.fetchone()
        return result[0] if result else 0
    
    def set_mod_rank(self, platform, platform_id, rank, setter_id):
        self.cursor.execute("UPDATE users SET mod_rank = ? WHERE platform = ? AND platform_id = ?", (rank, platform, platform_id))
        self.conn.commit()
    
    def get_moderators(self, platform):
        self.cursor.execute("SELECT platform_id, first_name, username, mod_rank FROM users WHERE platform = ? AND mod_rank > 0 ORDER BY mod_rank DESC", (platform,))
        return self.cursor.fetchall()
    
    def get_group_settings(self, chat_id, platform):
        self.cursor.execute("SELECT * FROM group_settings WHERE chat_id = ? AND platform = ?", (chat_id, platform))
        settings = self.cursor.fetchone()
        if not settings:
            self.cursor.execute('''
                INSERT INTO group_settings (chat_id, platform) VALUES (?, ?)
            ''', (chat_id, platform))
            self.conn.commit()
            return self.get_group_settings(chat_id, platform)
        columns = [description[0] for description in self.cursor.description]
        return dict(zip(columns, settings))
    
    def update_group_setting(self, chat_id, platform, setting, value):
        self.cursor.execute(f"UPDATE group_settings SET {setting} = ? WHERE chat_id = ? AND platform = ?", (value, chat_id, platform))
        self.conn.commit()
    
    def has_privilege(self, platform, platform_id, privilege):
        if int(platform_id) in [OWNER_ID_TG, OWNER_ID_VK]:
            return True
        self.cursor.execute("SELECT mod_rank, privilege, privilege_until FROM users WHERE platform = ? AND platform_id = ?", (platform, platform_id))
        user = self.cursor.fetchone()
        if not user:
            return False
        if user[0] >= 3:
            return True
        if user[1] == privilege and user[2]:
            return datetime.datetime.now() < datetime.datetime.fromisoformat(user[2])
        return False
    
    # ===================== РУССКАЯ РУЛЕТКА =====================
    def rr_create_lobby(self, creator_id, max_players, bet):
        self.cursor.execute('''
            INSERT INTO rr_lobbies (creator_id, max_players, bet, players, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (creator_id, max_players, bet, json.dumps([creator_id]), datetime.datetime.now()))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def rr_join_lobby(self, lobby_id, user_id):
        self.cursor.execute("SELECT players, max_players FROM rr_lobbies WHERE id = ? AND status = 'waiting'", (lobby_id,))
        result = self.cursor.fetchone()
        if result:
            players = json.loads(result[0])
            if user_id not in players and len(players) < result[1]:
                players.append(user_id)
                self.cursor.execute("UPDATE rr_lobbies SET players = ? WHERE id = ?", (json.dumps(players), lobby_id))
                self.conn.commit()
                return True
        return False
    
    def rr_start_game(self, lobby_id):
        self.cursor.execute("SELECT * FROM rr_lobbies WHERE id = ?", (lobby_id,))
        lobby = self.cursor.fetchone()
        if not lobby:
            return None
        
        columns = [description[0] for description in self.cursor.description]
        lobby_dict = dict(zip(columns, lobby))
        
        players = json.loads(lobby_dict['players'])
        bet = lobby_dict['bet']
        
        cylinder_size = random.randint(6, 10)
        bullets = random.randint(1, 3)
        
        positions = [False] * cylinder_size
        for pos in random.sample(range(cylinder_size), bullets):
            positions[pos] = True
        
        random.shuffle(players)
        
        self.cursor.execute('''
            INSERT INTO rr_games (lobby_id, players, current_player, cylinder_size, bullets, positions, alive_players, phase, items, started_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (lobby_id, json.dumps(players), 0, cylinder_size, bullets, json.dumps(positions), json.dumps(players), 'playing', json.dumps({}), datetime.datetime.now()))
        game_id = self.cursor.lastrowid
        
        self.cursor.execute("UPDATE rr_lobbies SET status = 'playing' WHERE id = ?", (lobby_id,))
        self.conn.commit()
        
        return game_id, players, cylinder_size, bullets, positions
    
    def rr_get_game(self, game_id):
        self.cursor.execute("SELECT * FROM rr_games WHERE id = ?", (game_id,))
        game = self.cursor.fetchone()
        if game:
            columns = [description[0] for description in self.cursor.description]
            return dict(zip(columns, game))
        return None
    
    def rr_make_shot(self, game_id, user_id):
        game = self.rr_get_game(game_id)
        if not game:
            return None
        
        players = json.loads(game['players'])
        current_player = game['current_player']
        positions = json.loads(game['positions'])
        alive_players = json.loads(game['alive_players'])
        
        if players[current_player] != user_id:
            return "not_your_turn"
        
        shot_result = positions[0]
        
        if shot_result:
            alive_players.remove(user_id)
            result = "dead"
            
            if len(alive_players) == 1:
                winner_id = alive_players[0]
                self.cursor.execute("UPDATE rr_games SET phase = 'finished' WHERE id = ?", (game_id,))
                self.conn.commit()
                return "game_over", winner_id
        else:
            result = "alive"
            positions = positions[1:] + [False]
        
        if alive_players:
            current_player = (current_player + 1) % len(alive_players)
        
        self.cursor.execute("UPDATE rr_games SET current_player = ?, positions = ?, alive_players = ? WHERE id = ?", 
                           (current_player, json.dumps(positions), json.dumps(alive_players), game_id))
        self.conn.commit()
        
        return result
    
    # ===================== КРЕСТИКИ-НОЛИКИ 3D =====================
    def ttt_create_game(self, player_x, player_o):
        main_board = [[0, 0, 0] for _ in range(3)]
        sub_boards = [[[0, 0, 0] for _ in range(3)] for _ in range(9)]
        
        self.cursor.execute('''
            INSERT INTO ttt_games (player_x, player_o, current_player, main_board, sub_boards, last_move, status, started_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (player_x, player_o, player_x, json.dumps(main_board), json.dumps(sub_boards), -1, 'playing', datetime.datetime.now()))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def ttt_make_move(self, game_id, user_id, main_row, main_col, sub_row, sub_col):
        self.cursor.execute("SELECT * FROM ttt_games WHERE id = ?", (game_id,))
        game = self.cursor.fetchone()
        if not game:
            return None
        
        columns = [description[0] for description in self.cursor.description]
        game_dict = dict(zip(columns, game))
        
        main_board = json.loads(game_dict['main_board'])
        sub_boards = json.loads(game_dict['sub_boards'])
        current_player = game_dict['current_player']
        
        if current_player != user_id:
            return "not_your_turn"
        
        if sub_boards[main_row * 3 + main_col][sub_row][sub_col] != 0:
            return "cell_occupied"
        
        marker = 1 if user_id == game_dict['player_x'] else 2
        sub_boards[main_row * 3 + main_col][sub_row][sub_col] = marker
        
        sub_winner = self.ttt_check_winner(sub_boards[main_row * 3 + main_col])
        if sub_winner:
            main_board[main_row][main_col] = sub_winner
        
        main_winner = self.ttt_check_winner(main_board)
        if main_winner:
            status = 'finished'
            winner = game_dict['player_x'] if main_winner == 1 else game_dict['player_o']
        else:
            status = 'playing'
            winner = None
            current_player = game_dict['player_o'] if current_player == game_dict['player_x'] else game_dict['player_x']
        
        self.cursor.execute('''
            UPDATE ttt_games SET main_board = ?, sub_boards = ?, current_player = ?, status = ? WHERE id = ?
        ''', (json.dumps(main_board), json.dumps(sub_boards), current_player, status, game_id))
        self.conn.commit()
        
        return {
            'status': status,
            'winner': winner,
            'main_board': main_board,
            'sub_boards': sub_boards,
            'current_player': current_player
        }
    
    def ttt_check_winner(self, board):
        for i in range(3):
            if board[i][0] != 0 and board[i][0] == board[i][1] == board[i][2]:
                return board[i][0]
        for j in range(3):
            if board[0][j] != 0 and board[0][j] == board[1][j] == board[2][j]:
                return board[0][j]
        if board[0][0] != 0 and board[0][0] == board[1][1] == board[2][2]:
            return board[0][0]
        if board[0][2] != 0 and board[0][2] == board[1][1] == board[2][0]:
            return board[0][2]
        return 0
    
    # ===================== МАФИЯ =====================
    def mafia_create_game(self, creator_id):
        self.cursor.execute('''
            INSERT INTO mafia_games (creator_id, players, created_at)
            VALUES (?, ?, ?)
        ''', (creator_id, json.dumps([creator_id]), datetime.datetime.now()))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def mafia_join_game(self, game_id, user_id):
        self.cursor.execute("SELECT players FROM mafia_games WHERE id = ? AND status = 'waiting'", (game_id,))
        result = self.cursor.fetchone()
        if result:
            players = json.loads(result[0])
            if user_id not in players and len(players) < 10:
                players.append(user_id)
                self.cursor.execute("UPDATE mafia_games SET players = ? WHERE id = ?", (json.dumps(players), game_id))
                self.conn.commit()
                return True
        return False
    
    def mafia_start_game(self, game_id):
        self.cursor.execute("SELECT players FROM mafia_games WHERE id = ?", (game_id,))
        result = self.cursor.fetchone()
        if not result:
            return None
        
        players = json.loads(result[0])
        if len(players) < 4:
            return "not_enough_players"
        
        mafia_count = max(1, len(players) // 3)
        roles = ['mafia'] * mafia_count + ['civilian'] * (len(players) - mafia_count)
        random.shuffle(roles)
        
        roles_dict = {players[i]: roles[i] for i in range(len(players))}
        
        self.cursor.execute('''
            UPDATE mafia_games SET roles = ?, status = 'playing', phase = 'night' WHERE id = ?
        ''', (json.dumps(roles_dict), game_id))
        self.conn.commit()
        
        return roles_dict
    
    def mafia_get_game(self, game_id):
        self.cursor.execute("SELECT * FROM mafia_games WHERE id = ?", (game_id,))
        game = self.cursor.fetchone()
        if game:
            columns = [description[0] for description in self.cursor.description]
            return dict(zip(columns, game))
        return None
    
    # ===================== САПЁР =====================
    def minesweeper_create_game(self, user_id, width=8, height=8, mines=10):
        board = [[0 for _ in range(width)] for _ in range(height)]
        revealed = [[False for _ in range(width)] for _ in range(height)]
        flags = [[False for _ in range(width)] for _ in range(height)]
        
        positions = [(x, y) for x in range(width) for y in range(height)]
        mine_positions = random.sample(positions, mines)
        
        for x, y in mine_positions:
            board[y][x] = -1
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    if dy == 0 and dx == 0:
                        continue
                    ny, nx = y + dy, x + dx
                    if 0 <= nx < width and 0 <= ny < height and board[ny][nx] != -1:
                        board[ny][nx] += 1
        
        self.cursor.execute('''
            INSERT INTO minesweeper_games (user_id, width, height, mines, board, revealed, flags, status, started_at, last_move)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, width, height, mines, json.dumps(board), json.dumps(revealed), json.dumps(flags), 'playing', datetime.datetime.now(), datetime.datetime.now()))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def minesweeper_get_game(self, game_id):
        self.cursor.execute("SELECT * FROM minesweeper_games WHERE id = ?", (game_id,))
        game = self.cursor.fetchone()
        if game:
            columns = [description[0] for description in self.cursor.description]
            return dict(zip(columns, game))
        return None
    
    def minesweeper_reveal(self, game_id, x, y):
        game = self.minesweeper_get_game(game_id)
        if not game or game['status'] != 'playing':
            return None
        
        board = json.loads(game['board'])
        revealed = json.loads(game['revealed'])
        flags = json.loads(game['flags'])
        
        if revealed[y][x] or flags[y][x]:
            return "already_revealed"
        
        if board[y][x] == -1:
            revealed[y][x] = True
            status = 'lost'
            result = "mine"
        else:
            self.minesweeper_flood_fill(board, revealed, x, y)
            status = 'won' if self.minesweeper_check_win(board, revealed) else 'playing'
            result = "safe"
        
        self.cursor.execute('''
            UPDATE minesweeper_games SET revealed = ?, status = ?, last_move = ? WHERE id = ?
        ''', (json.dumps(revealed), status, datetime.datetime.now(), game_id))
        self.conn.commit()
        
        return {
            'status': status,
            'result': result,
            'board': board,
            'revealed': revealed,
            'flags': flags
        }
    
    def minesweeper_flood_fill(self, board, revealed, x, y):
        width = len(board[0])
        height = len(board)
        
        if x < 0 or x >= width or y < 0 or y >= height:
            return
        if revealed[y][x] or board[y][x] == -1:
            return
        
        revealed[y][x] = True
        
        if board[y][x] == 0:
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    if dy == 0 and dx == 0:
                        continue
                    self.minesweeper_flood_fill(board, revealed, x + dx, y + dy)
    
    def minesweeper_toggle_flag(self, game_id, x, y):
        game = self.minesweeper_get_game(game_id)
        if not game or game['status'] != 'playing':
            return None
        
        flags = json.loads(game['flags'])
        revealed = json.loads(game['revealed'])
        
        if revealed[y][x]:
            return "already_revealed"
        
        flags[y][x] = not flags[y][x]
        
        self.cursor.execute('''
            UPDATE minesweeper_games SET flags = ?, last_move = ? WHERE id = ?
        ''', (json.dumps(flags), datetime.datetime.now(), game_id))
        self.conn.commit()
        
        return flags
    
    def minesweeper_check_win(self, board, revealed):
        width = len(board[0])
        height = len(board)
        
        for y in range(height):
            for x in range(width):
                if board[y][x] != -1 and not revealed[y][x]:
                    return False
        return True
    
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
        self.spam_tracker = defaultdict(list)
        
        if TELEGRAM_TOKEN:
            self.tg_application = Application.builder().token(TELEGRAM_TOKEN).build()
            self.setup_tg_handlers()
            logger.info("✅ Telegram бот инициализирован")
        
        if VK_TOKEN and VKBOTTLE_AVAILABLE:
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
        self.tg_application.add_handler(CommandHandler("whoami", self.tg_cmd_whoami))
        self.tg_application.add_handler(CommandHandler("top", self.tg_cmd_top))
        self.tg_application.add_handler(CommandHandler("players", self.tg_cmd_players))
        
        # Боссы
        self.tg_application.add_handler(CommandHandler("boss", self.tg_cmd_boss))
        self.tg_application.add_handler(CommandHandler("boss_fight", self.tg_cmd_boss_fight))
        self.tg_application.add_handler(CommandHandler("regen", self.tg_cmd_regen))
        
        # Экономика
        self.tg_application.add_handler(CommandHandler("shop", self.tg_cmd_shop))
        self.tg_application.add_handler(CommandHandler("donate", self.tg_cmd_donate))
        self.tg_application.add_handler(CommandHandler("pay", self.tg_cmd_pay))
        self.tg_application.add_handler(CommandHandler("cmd", self.tg_cmd_privilege_commands))
        
        # Система модерации (Iris-like)
        self.tg_application.add_handler(CommandHandler("moder", self.tg_cmd_moder))
        self.tg_application.add_handler(CommandHandler("moder2", self.tg_cmd_moder2))
        self.tg_application.add_handler(CommandHandler("moder3", self.tg_cmd_moder3))
        self.tg_application.add_handler(CommandHandler("moder4", self.tg_cmd_moder4))
        self.tg_application.add_handler(CommandHandler("moder5", self.tg_cmd_moder5))
        self.tg_application.add_handler(CommandHandler("promote", self.tg_cmd_promote))
        self.tg_application.add_handler(CommandHandler("demote", self.tg_cmd_demote))
        self.tg_application.add_handler(CommandHandler("remove_moder", self.tg_cmd_remove_moder))
        self.tg_application.add_handler(CommandHandler("staff", self.tg_cmd_staff))
        self.tg_application.add_handler(CommandHandler("who_invited", self.tg_cmd_who_invited))
        
        # Предупреждения (варны)
        self.tg_application.add_handler(CommandHandler("warn", self.tg_cmd_warn))
        self.tg_application.add_handler(CommandHandler("warns", self.tg_cmd_warns))
        self.tg_application.add_handler(CommandHandler("my_warns", self.tg_cmd_my_warns))
        self.tg_application.add_handler(CommandHandler("warnlist", self.tg_cmd_warnlist))
        self.tg_application.add_handler(CommandHandler("remove_warn", self.tg_cmd_remove_warn))
        self.tg_application.add_handler(CommandHandler("clear_warns", self.tg_cmd_clear_warns))
        
        # Мут
        self.tg_application.add_handler(CommandHandler("mute", self.tg_cmd_mute))
        self.tg_application.add_handler(CommandHandler("unmute", self.tg_cmd_unmute))
        self.tg_application.add_handler(CommandHandler("mutelist", self.tg_cmd_mutelist))
        self.tg_application.add_handler(CommandHandler("check_mute", self.tg_cmd_check_mute))
        
        # Бан
        self.tg_application.add_handler(CommandHandler("ban", self.tg_cmd_ban))
        self.tg_application.add_handler(CommandHandler("unban", self.tg_cmd_unban))
        self.tg_application.add_handler(CommandHandler("banlist", self.tg_cmd_banlist))
        
        # Правила и настройки
        self.tg_application.add_handler(CommandHandler("rules", self.tg_cmd_rules))
        self.tg_application.add_handler(CommandHandler("set_rules", self.tg_cmd_set_rules))
        self.tg_application.add_handler(CommandHandler("warns_limit", self.tg_cmd_warns_limit))
        self.tg_application.add_handler(CommandHandler("mute_period", self.tg_cmd_mute_period))
        self.tg_application.add_handler(CommandHandler("ban_period", self.tg_cmd_ban_period))
        
        # Русская рулетка
        self.tg_application.add_handler(CommandHandler("rr", self.tg_cmd_rr))
        self.tg_application.add_handler(CommandHandler("rr_start", self.tg_cmd_rr_start))
        self.tg_application.add_handler(CommandHandler("rr_join", self.tg_cmd_rr_join))
        self.tg_application.add_handler(CommandHandler("rr_shot", self.tg_cmd_rr_shot))
        
        # Крестики-нолики 3D
        self.tg_application.add_handler(CommandHandler("ttt", self.tg_cmd_ttt))
        self.tg_application.add_handler(CommandHandler("ttt_challenge", self.tg_cmd_ttt_challenge))
        self.tg_application.add_handler(CommandHandler("ttt_move", self.tg_cmd_ttt_move))
        
        # Мафия
        self.tg_application.add_handler(CommandHandler("mafia", self.tg_cmd_mafia))
        self.tg_application.add_handler(CommandHandler("mafia_create", self.tg_cmd_mafia_create))
        self.tg_application.add_handler(CommandHandler("mafia_join", self.tg_cmd_mafia_join))
        self.tg_application.add_handler(CommandHandler("mafia_start", self.tg_cmd_mafia_start))
        
        # Сапёр
        self.tg_application.add_handler(CommandHandler("minesweeper", self.tg_cmd_minesweeper))
        self.tg_application.add_handler(CommandHandler("ms_reveal", self.tg_cmd_ms_reveal))
        self.tg_application.add_handler(CommandHandler("ms_flag", self.tg_cmd_ms_flag))
        
        # Камень-ножницы-бумага
        self.tg_application.add_handler(CommandHandler("rps", self.tg_cmd_rps))
        
        # Полезные команды
        self.tg_application.add_handler(CommandHandler("info", self.tg_cmd_info))
        self.tg_application.add_handler(CommandHandler("holidays", self.tg_cmd_holidays))
        self.tg_application.add_handler(CommandHandler("fact", self.tg_cmd_fact))
        self.tg_application.add_handler(CommandHandler("wisdom", self.tg_cmd_wisdom))
        self.tg_application.add_handler(CommandHandler("population", self.tg_cmd_population))
        self.tg_application.add_handler(CommandHandler("bitcoin", self.tg_cmd_bitcoin))
        
        # Закладки и награды
        self.tg_application.add_handler(CommandHandler("bookmark", self.tg_cmd_add_bookmark))
        self.tg_application.add_handler(CommandHandler("bookmarks", self.tg_cmd_bookmarks))
        self.tg_application.add_handler(CommandHandler("award", self.tg_cmd_add_award))
        self.tg_application.add_handler(CommandHandler("awards", self.tg_cmd_awards))
        
        # Интерактивные кнопки
        self.tg_application.add_handler(CallbackQueryHandler(self.tg_button_callback))
        
        # Обработка сообщений
        self.tg_application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.tg_handle_message))
        self.tg_application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, self.tg_handle_new_members))
        self.tg_application.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, self.tg_handle_left_member))
        
        logger.info("✅ Telegram обработчики зарегистрированы")
    
    # ===================== TELEGRAM КОМАНДЫ =====================
    async def tg_cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        
        db.get_user('tg', platform_id, user.username or "", user.first_name, user.last_name or "")
        db.update_activity('tg', platform_id)
        
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
            f"🛡️ /staff - список модераторов\n"
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
            [InlineKeyboardButton("🛡️ Модерация", callback_data="moderation"),
             InlineKeyboardButton("🎮 Игры", callback_data="games")],
            [InlineKeyboardButton("📚 Команды", callback_data="help"),
             InlineKeyboardButton("📖 Правила", callback_data="rules")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def tg_cmd_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        db.update_activity('tg', platform_id)
        
        keyboard = [
            [InlineKeyboardButton("👤 Профиль", callback_data="profile"),
             InlineKeyboardButton("👾 Босс", callback_data="boss")],
            [InlineKeyboardButton("💰 Магазин", callback_data="shop"),
             InlineKeyboardButton("💎 Привилегии", callback_data="donate")],
            [InlineKeyboardButton("📊 Топ", callback_data="top"),
             InlineKeyboardButton("👥 Онлайн", callback_data="players")],
            [InlineKeyboardButton("🛡️ Модерация", callback_data="moderation"),
             InlineKeyboardButton("🎮 Игры", callback_data="games")],
            [InlineKeyboardButton("📚 Команды", callback_data="help"),
             InlineKeyboardButton("📖 Правила", callback_data="rules")],
            [InlineKeyboardButton("📌 Закладки", callback_data="bookmarks_menu"),
             InlineKeyboardButton("🏅 Награды", callback_data="awards_menu")]
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
        
        text = (
            "📚 **ВСЕ КОМАНДЫ БОТА**\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**ОСНОВНЫЕ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/start - запуск бота\n"
            "/menu - главное меню\n"
            "/help - эта справка\n"
            "/profile - твой профиль\n"
            "/whoami - информация о себе\n"
            "/top - топ игроков\n"
            "/players - количество игроков\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**БИТВА С БОССОМ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/boss - информация о боссе\n"
            "/boss_fight [id] - ударить босса\n"
            "/regen - восстановить здоровье\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**ЭКОНОМИКА**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/shop - магазин\n"
            "/donate - привилегии\n"
            "/pay [ник] [сумма] - перевести монеты\n"
            "/cmd [привилегия] - команды доната\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**СИСТЕМА МОДЕРАЦИИ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/staff - список модераторов\n"
            "/moder [ссылка] - назначить младшим модератором\n"
            "/promote [ссылка] - повысить ранг\n"
            "/demote [ссылка] - понизить ранг\n"
            "/remove_moder [ссылка] - снять модератора\n"
            "/who_invited [ссылка] - кто назначил\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**ПРЕДУПРЕЖДЕНИЯ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/warn [ссылка] [время] [причина] - выдать варн\n"
            "/warns [ссылка] - список варнов\n"
            "/my_warns - мои варны\n"
            "/warnlist - список последних варнов\n"
            "/remove_warn [ссылка] - снять последний варн\n"
            "/clear_warns [ссылка] - снять все варны\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**МУТ И БАН**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/mute [ссылка] [время] [причина] - замутить\n"
            "/unmute [ссылка] - снять мут\n"
            "/mutelist - список замученных\n"
            "/check_mute [ссылка] - проверить мут\n"
            "/ban [ссылка] [время] [причина] - забанить\n"
            "/unban [ссылка] - разбанить\n"
            "/banlist - список банов\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**ИГРЫ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/rr - русская рулетка\n"
            "/ttt - крестики-нолики 3D\n"
            "/mafia - мафия\n"
            "/minesweeper [сложность] - сапёр\n"
            "/rps - камень-ножницы-бумага\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**ПОЛЕЗНОЕ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/info [событие] - правдивость события\n"
            "/holidays - праздники сегодня\n"
            "/fact - случайный факт\n"
            "/wisdom - мудрая цитата\n"
            "/population - население Земли\n"
            "/bitcoin - курс биткоина\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**ЗАКЛАДКИ И НАГРАДЫ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/bookmark [описание] - создать закладку\n"
            "/bookmarks - список закладок\n"
            "/award [ник] [название] - дать награду (админ)\n"
            "/awards - список наград\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**ПРАВИЛА**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/rules - показать правила\n"
            "/set_rules [текст] - установить правила (админ)"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def tg_cmd_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        
        user_data = db.get_user('tg', platform_id, user.username or "", user.first_name, user.last_name or "")
        db.update_activity('tg', platform_id)
        
        if db.is_banned('tg', platform_id):
            await update.message.reply_text("🚫 Вы забанены в боте.")
            return
        
        if db.is_muted('tg', platform_id):
            mute_until = datetime.datetime.fromisoformat(user_data['mute_until'])
            remaining = mute_until - datetime.datetime.now()
            minutes = remaining.seconds // 60
            await update.message.reply_text(f"🔇 Вы замучены. Осталось: {minutes} мин")
            return
        
        mod_rank = user_data.get('mod_rank', 0)
        rank_name = MODER_RANKS.get(mod_rank, "👤 Пользователь")
        
        privilege = user_data.get('privilege', 'user')
        privilege_text = f" | {PRIVILEGES.get(privilege, {}).get('emoji', '')} {privilege}" if privilege != 'user' else ""
        
        last_activity = "Неизвестно"
        if user_data.get('last_activity'):
            last = datetime.datetime.fromisoformat(user_data['last_activity'])
            delta = datetime.datetime.now() - last
            if delta.days > 0:
                last_activity = f"{delta.days} дн назад"
            elif delta.seconds > 3600:
                last_activity = f"{delta.seconds // 3600} ч назад"
            else:
                last_activity = f"{delta.seconds // 60} мин назад"
        
        first_seen = "Неизвестно"
        if user_data.get('first_seen'):
            first = datetime.datetime.fromisoformat(user_data['first_seen'])
            delta = datetime.datetime.now() - first
            years = delta.days // 365
            months = (delta.days % 365) // 30
            days = delta.days % 30
            first_seen = f"{first.strftime('%d.%m.%Y')} ({years} г {months} мес {days} дн)"
        
        text = (
            f"╔══════════════════════════════╗\n"
            f"║   👤 **ПРОФИЛЬ ИГРОКА**      ║\n"
            f"╚══════════════════════════════╝\n\n"
            
            f"**{user_data.get('nickname') or user.first_name}**\n"
            f"{rank_name}{privilege_text}\n"
            f"ID: {user.id}\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**РЕСУРСЫ**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🪙 Монеты: {user_data['coins']:,}\n"
            f"💎 Алмазы: {user_data['diamonds']:,}\n"
            f"💀 Черепки: {user_data['rr_money']}\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**ХАРАКТЕРИСТИКИ**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"❤️ Здоровье: {user_data['health']}/{user_data['max_health']}\n"
            f"⚔️ Урон: {user_data['damage']}\n"
            f"⚡ Энергия: {user_data['energy']}\n"
            f"📊 Уровень: {user_data['level']}\n"
            f"👾 Боссов убито: {user_data['boss_kills']}\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**СТАТИСТИКА ИГР**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔪 Мафия: {user_data['mafia_wins']}/{user_data['mafia_games']}\n"
            f"✊ КНБ: {user_data['rps_wins']}-{user_data['rps_losses']}-{user_data['rps_draws']}\n"
            f"⭕ TTT: {user_data['ttt_wins']}-{user_data['ttt_losses']}-{user_data['ttt_draws']}\n"
            f"💣 Рулетка: {user_data['rr_wins']}-{user_data['rr_losses']}\n"
            f"💥 Сапёр: {user_data['minesweeper_wins']}/{user_data['minesweeper_games']}\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**АКТИВНОСТЬ**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📝 Сообщений: {user_data['messages_count']}\n"
            f"⌨️ Команд: {user_data['commands_used']}\n"
            f"⭐ Репутация: {user_data['reputation']}\n"
            f"⚠️ Варнов: {user_data['warns']}\n"
            f"⏱ Последний визит: {last_activity}\n"
            f"📅 Первое появление: {first_seen}"
        )
        
        if user_data.get('description'):
            text += f"\n\n📝 **О себе:** {user_data['description']}"
        
        keyboard = [
            [InlineKeyboardButton("🏅 Награды", callback_data="awards"),
             InlineKeyboardButton("📌 Закладки", callback_data="bookmarks_menu")],
            [InlineKeyboardButton("🔙 Назад", callback_data="menu_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def tg_cmd_whoami(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        
        user_data = db.get_user('tg', platform_id, user.username or "", user.first_name, user.last_name or "")
        
        mod_rank = user_data.get('mod_rank', 0)
        rank_name = MODER_RANKS.get(mod_rank, "👤 Пользователь")
        
        privilege = user_data.get('privilege', 'user')
        privilege_text = f" | {privilege}" if privilege != 'user' else ""
        
        awards = db.get_awards('tg', platform_id)
        awards_text = ""
        if awards:
            awards_text = "\n🏅 Награды:\n"
            for award in awards[:3]:
                awards_text += f"   • {award[3]}\n"
        
        first_seen = "Неизвестно"
        if user_data.get('first_seen'):
            first = datetime.datetime.fromisoformat(user_data['first_seen'])
            delta = datetime.datetime.now() - first
            years = delta.days // 365
            months = (delta.days % 365) // 30
            days = delta.days % 30
            first_seen = f"{first.strftime('%d.%m.%Y')} ({years} г {months} мес {days} дн)"
        
        last_activity = "Неизвестно"
        if user_data.get('last_activity'):
            last = datetime.datetime.fromisoformat(user_data['last_activity'])
            delta = datetime.datetime.now() - last
            if delta.days > 0:
                last_activity = f"{delta.days} дн назад"
            elif delta.seconds > 3600:
                last_activity = f"{delta.seconds // 3600} ч назад"
            else:
                last_activity = f"{delta.seconds // 60} мин назад"
        
        text = (
            f"Это [{user.id}|{user.first_name}]\n"
            f"{rank_name}{privilege_text}\n"
            f"Репутация: ✨ {user_data['reputation']} | ➕ {user_data['reputation_given']}\n"
            f"⚠️ Варнов: {user_data['warns']}\n"
            f"Первое появление: {first_seen}\n"
            f"Последний актив: {last_activity}\n"
            f"Актив (д|н|м|весь): {user_data['messages_count']} | {user_data['commands_used']} | {user_data['games_played']} | {delta.days if 'delta' in locals() else 0}"
            f"{awards_text}"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="menu_back")]]
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
    
    # ===================== КОМАНДЫ БОССОВ =====================
    async def tg_cmd_boss(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        
        user_data = db.get_user('tg', platform_id, user.username or "", user.first_name, user.last_name or "")
        db.update_activity('tg', platform_id)
        
        if db.is_banned('tg', platform_id):
            await update.message.reply_text("🚫 Вы забанены в боте.")
            return
        
        if db.is_muted('tg', platform_id):
            mute_until = datetime.datetime.fromisoformat(user_data['mute_until'])
            remaining = mute_until - datetime.datetime.now()
            minutes = remaining.seconds // 60
            await update.message.reply_text(f"🔇 Вы замучены. Осталось: {minutes} мин")
            return
        
        boss = db.get_boss()
        
        if not boss:
            await update.message.reply_text("👾 Все боссы повержены! Ожидайте возрождения...")
            db.respawn_bosses()
            boss = db.get_boss()
        
        player_damage = user_data['damage'] * (1 + user_data['level'] * 0.1)
        
        text = (
            f"╔══════════════════════════════╗\n"
            f"║   👾 **БИТВА С БОССОМ**      ║\n"
            f"╚══════════════════════════════╝\n\n"
            
            f"🔥 **{boss['boss_name']}**\n"
            f"Уровень: {boss['boss_level']}\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**ХАРАКТЕРИСТИКИ БОССА**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💀 Здоровье: {boss['boss_health']} / {boss['boss_max_health']} HP\n"
            f"⚔️ Урон: {boss['boss_damage']} HP\n"
            f"💰 Награда: {boss['boss_reward']} 🪙\n\n"
            
            f"**ТВОИ ХАРАКТЕРИСТИКИ**\n"
            f"❤️ Здоровье: {user_data['health']} HP\n"
            f"🗡 Урон: {player_damage:.1f} ({user_data['damage']} базовый)\n"
            f"📊 Сила: {((player_damage / boss['boss_damage']) * 100):.1f}%\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**ДЕЙСТВИЯ**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👊 /boss_fight {boss['id']} - ударить босса\n"
            f"➕ /regen - восстановить здоровье"
        )
        
        keyboard = [
            [InlineKeyboardButton("👊 Ударить", callback_data=f"boss_fight_{boss['id']}"),
             InlineKeyboardButton("➕ Регенерация", callback_data="regen")],
            [InlineKeyboardButton("🔙 Назад", callback_data="menu_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def tg_cmd_boss_fight(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        
        if not context.args:
            await update.message.reply_text("❌ Использование: /boss_fight [id]")
            return
        
        try:
            boss_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ Неправильный ID")
            return
        
        user_data = db.get_user('tg', platform_id, user.username or "", user.first_name, user.last_name or "")
        db.update_activity('tg', platform_id)
        
        if db.is_banned('tg', platform_id):
            await update.message.reply_text("🚫 Вы забанены в боте.")
            return
        
        if db.is_muted('tg', platform_id):
            mute_until = datetime.datetime.fromisoformat(user_data['mute_until'])
            remaining = mute_until - datetime.datetime.now()
            minutes = remaining.seconds // 60
            await update.message.reply_text(f"🔇 Вы замучены. Осталось: {minutes} мин")
            return
        
        if user_data['health'] <= 0:
            await update.message.reply_text("💀 У вас нет здоровья! Используйте /regen")
            return
        
        if user_data['energy'] < 5:
            await update.message.reply_text("⚡ Недостаточно энергии! Нужно 5 ⚡")
            return
        
        db.add_coins('tg', platform_id, -5, "energy")
        
        player_damage = int(user_data['damage'] * (1 + user_data['level'] * 0.1))
        
        boss = db.get_boss()
        if not boss or boss['id'] != boss_id:
            await update.message.reply_text("❌ Босс не найден или уже повержен")
            return
        
        killed, health_left = db.damage_boss(boss_id, player_damage)
        db.damage_user('tg', platform_id, boss['boss_damage'])
        
        text = f"⚔️ **БИТВА С БОССОМ** ⚔️\n\n"
        text += f"**{boss['boss_name']}**\n\n"
        text += f"▫️ **Твой урон:** {player_damage} HP\n"
        text += f"▫️ **Урон босса:** {boss['boss_damage']} HP\n\n"
        
        if killed:
            reward = boss['boss_reward']
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
                db.respawn_bosses()
        else:
            text += f"👾 **Босс еще жив!**\n"
            text += f"💀 **Осталось:** {health_left} HP"
        
        user_data = db.get_user('tg', platform_id)
        if user_data['health'] <= 0:
            text += f"\n\n💀 **Ты погиб в бою!** Используй /regen для восстановления."
        
        keyboard = [[InlineKeyboardButton("🔙 К боссу", callback_data="boss")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def tg_cmd_regen(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        
        user_data = db.get_user('tg', platform_id, user.username or "", user.first_name, user.last_name or "")
        db.update_activity('tg', platform_id)
        
        if db.is_banned('tg', platform_id):
            await update.message.reply_text("🚫 Вы забанены в боте.")
            return
        
        if db.is_muted('tg', platform_id):
            mute_until = datetime.datetime.fromisoformat(user_data['mute_until'])
            remaining = mute_until - datetime.datetime.now()
            minutes = remaining.seconds // 60
            await update.message.reply_text(f"🔇 Вы замучены. Осталось: {minutes} мин")
            return
        
        if not db.regen_available('tg', platform_id):
            await update.message.reply_text("❌ Регенерация еще не доступна! Подождите немного.")
            return
        
        if user_data['health'] < user_data['max_health']:
            heal_amount = user_data['max_health'] - user_data['health']
            db.heal_user('tg', platform_id, heal_amount)
            
            cooldown = 5
            if db.has_privilege('tg', platform_id, 'премиум'):
                cooldown = 1
            elif db.has_privilege('tg', platform_id, 'вип'):
                cooldown = 3
            
            db.use_regen('tg', platform_id, cooldown)
            
            await update.message.reply_text(
                f"➕ **РЕГЕНЕРАЦИЯ**\n\n"
                f"❤️ Здоровье восстановлено!\n"
                f"Текущее здоровье: {user_data['max_health']}/{user_data['max_health']}\n\n"
                f"⏱ Следующая регенерация через {cooldown} мин."
            )
        else:
            await update.message.reply_text("❤️ У тебя уже полное здоровье!")
    
    # ===================== ЭКОНОМИКА =====================
    async def tg_cmd_shop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        db.update_activity('tg', platform_id)
        
        if db.is_banned('tg', platform_id):
            await update.message.reply_text("🚫 Вы забанены в боте.")
            return
        
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
            "⚡ **ЭНЕРГИЯ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ Энергетик — 30 🪙 (⚡+20)\n"
            "▫️ Батарейка — 80 🪙 (⚡+50)\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "💎 **ВАЛЮТА**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ Алмаз — 100 🪙 (💎+1)\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**ПРЕДМЕТЫ ДЛЯ РУЛЕТКИ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ Монета Демона — 500 🪙\n"
            "▫️ Кровавый Глаз — 300 🪙\n"
            "▫️ Маска Клоуна — 1000 🪙\n\n"
            
            "🛒 Купить: /buy [название]"
        )
        
        keyboard = [
            [InlineKeyboardButton("💊 Зелья", callback_data="buy_potions"),
             InlineKeyboardButton("⚔️ Оружие", callback_data="buy_weapons")],
            [InlineKeyboardButton("⚡ Энергия", callback_data="buy_energy"),
             InlineKeyboardButton("💎 Алмазы", callback_data="buy_diamonds")],
            [InlineKeyboardButton("🎲 Предметы рулетки", callback_data="buy_rr_items"),
             InlineKeyboardButton("🔙 Назад", callback_data="menu_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def tg_cmd_donate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        db.update_activity('tg', platform_id)
        
        if db.is_banned('tg', platform_id):
            await update.message.reply_text("🚫 Вы забанены в боте.")
            return
        
        text = "💎 **ПРИВИЛЕГИИ «СПЕКТР»** 💎\n\n"
        
        for priv_name, priv_data in PRIVILEGES.items():
            text += f"{priv_data['emoji']} **{priv_name.upper()}**\n"
            text += f"└ 💰 Цена: {priv_data['price']} 🪙\n"
            text += f"└ 📅 Длительность: {priv_data['days']} дн\n"
            for cmd in priv_data['commands']:
                text += f"└ {cmd}\n"
            text += "\n"
        
        text += "👑 **АДМИН-ПРИВИЛЕГИИ** (ранги модерации)\n"
        text += "🛡️ Младший модератор, ⚔️ Старший модератор, 👑 Администратор\n\n"
        text += f"💳 Приобрести: напишите {OWNER_USERNAME_TG}"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="menu_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def tg_cmd_pay(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /pay [ник] [сумма]")
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
        
        if db.is_banned('tg', platform_id):
            await update.message.reply_text("🚫 Вы забанены в боте.")
            return
        
        if db.is_muted('tg', platform_id):
            mute_until = datetime.datetime.fromisoformat(user_data['mute_until'])
            remaining = mute_until - datetime.datetime.now()
            minutes = remaining.seconds // 60
            await update.message.reply_text(f"🔇 Вы замучены. Осталось: {minutes} мин")
            return
        
        if amount <= 0:
            await update.message.reply_text("❌ Сумма должна быть положительной")
            return
        
        if user_data['coins'] < amount:
            await update.message.reply_text(f"❌ Недостаточно монет! У вас {user_data['coins']} 🪙")
            return
        
        target_user = db.get_user_by_username('tg', target_name)
        
        if not target_user:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        target_id = target_user[2]
        
        success, message = db.transfer_money('tg', platform_id, 'tg', target_id, amount, "coins")
        
        if success:
            await update.message.reply_text(f"✅ {message}\nПолучатель: {target_user[4]}")
            
            try:
                await context.bot.send_message(
                    chat_id=int(target_id),
                    text=f"💰 {user.first_name} перевел вам {amount} 🪙!"
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
                "/cmd легенда\n"
                "/cmd эврольд\n"
                "/cmd властелин\n"
                "/cmd титан\n"
                "/cmd терминатор\n"
                "/cmd маг"
            )
            return
        
        privilege = context.args[0].lower()
        
        if privilege in PRIVILEGES:
            priv_data = PRIVILEGES[privilege]
            text = f"{priv_data['emoji']} **КОМАНДЫ {privilege.upper()}** {priv_data['emoji']}\n\n"
            for cmd in priv_data['commands']:
                text += f"▫️ {cmd}\n"
        else:
            text = "❌ Неизвестная привилегия"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    # ===================== СИСТЕМА МОДЕРАЦИИ =====================
    async def _resolve_mention(self, update: Update, context: ContextTypes.DEFAULT_TYPE, mention: str) -> Optional[str]:
        """Преобразует упоминание (@username или ссылку) в ID пользователя"""
        if mention.isdigit():
            return mention
        
        if mention.startswith('@'):
            username = mention[1:]
            user = db.get_user_by_username('tg', username)
            if user:
                return user[2]
        
        if update.message.reply_to_message:
            return str(update.message.reply_to_message.from_user.id)
        
        return None
    
    async def _check_moder_rank(self, update: Update, required_rank: int) -> bool:
        """Проверяет, имеет ли пользователь достаточный ранг"""
        user_id = str(update.effective_user.id)
        rank = db.get_mod_rank('tg', user_id)
        if rank >= required_rank:
            return True
        await update.message.reply_text("❌ Недостаточно прав")
        return False
    
    async def tg_cmd_moder(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Назначить младшим модератором (ранг 1)"""
        await self._assign_moder_rank(update, context, 1)
    
    async def tg_cmd_moder2(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Назначить старшим модератором (ранг 2)"""
        await self._assign_moder_rank(update, context, 2)
    
    async def tg_cmd_moder3(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Назначить младшим администратором (ранг 3)"""
        await self._assign_moder_rank(update, context, 3)
    
    async def tg_cmd_moder4(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Назначить старшим администратором (ранг 4)"""
        await self._assign_moder_rank(update, context, 4)
    
    async def tg_cmd_moder5(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Назначить создателем (ранг 5)"""
        await self._assign_moder_rank(update, context, 5)
    
    async def _assign_moder_rank(self, update: Update, context: ContextTypes.DEFAULT_TYPE, rank: int):
        if not await self._check_moder_rank(update, 5):
            return
        
        if not context.args:
            await update.message.reply_text(f"❌ Использование: /moder{'' if rank == 1 else f'{rank}'} [ссылка]")
            return
        
        target_link = context.args[0]
        target_id = await self._resolve_mention(update, context, target_link)
        
        if not target_id:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        target_user = db.get_user('tg', target_id)
        target_name = target_user.get('first_name', f"ID {target_id}")
        
        db.set_mod_rank('tg', target_id, rank, update.effective_user.id)
        
        await update.message.reply_text(
            f"✅ {MODER_RANKS[rank]} назначен для {target_name}"
        )
    
    async def tg_cmd_promote(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Повысить ранг модератора на 1"""
        if not await self._check_moder_rank(update, 5):
            return
        
        if not context.args:
            await update.message.reply_text("❌ Использование: /promote [ссылка]")
            return
        
        target_link = context.args[0]
        target_id = await self._resolve_mention(update, context, target_link)
        
        if not target_id:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        current_rank = db.get_mod_rank('tg', target_id)
        if current_rank >= 5:
            await update.message.reply_text("❌ Нельзя повысить создателя")
            return
        
        new_rank = min(current_rank + 1, 5)
        db.set_mod_rank('tg', target_id, new_rank, update.effective_user.id)
        
        target_user = db.get_user('tg', target_id)
        target_name = target_user.get('first_name', f"ID {target_id}")
        
        await update.message.reply_text(
            f"✅ {target_name} повышен до {MODER_RANKS[new_rank]}"
        )
    
    async def tg_cmd_demote(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Понизить ранг модератора на 1"""
        if not await self._check_moder_rank(update, 5):
            return
        
        if not context.args:
            await update.message.reply_text("❌ Использование: /demote [ссылка]")
            return
        
        target_link = context.args[0]
        target_id = await self._resolve_mention(update, context, target_link)
        
        if not target_id:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        current_rank = db.get_mod_rank('tg', target_id)
        if current_rank <= 0:
            await update.message.reply_text("❌ Пользователь не является модератором")
            return
        
        if current_rank >= 5:
            await update.message.reply_text("❌ Нельзя понизить создателя")
            return
        
        new_rank = max(current_rank - 1, 0)
        db.set_mod_rank('tg', target_id, new_rank, update.effective_user.id)
        
        target_user = db.get_user('tg', target_id)
        target_name = target_user.get('first_name', f"ID {target_id}")
        
        rank_name = MODER_RANKS[new_rank] if new_rank > 0 else "👤 Пользователь"
        await update.message.reply_text(
            f"✅ {target_name} понижен до {rank_name}"
        )
    
    async def tg_cmd_remove_moder(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Снять модератора (понизить до 0 ранга)"""
        if not await self._check_moder_rank(update, 5):
            return
        
        if not context.args:
            await update.message.reply_text("❌ Использование: /remove_moder [ссылка]")
            return
        
        target_link = context.args[0]
        target_id = await self._resolve_mention(update, context, target_link)
        
        if not target_id:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        current_rank = db.get_mod_rank('tg', target_id)
        if current_rank <= 0:
            await update.message.reply_text("❌ Пользователь не является модератором")
            return
        
        if current_rank >= 5:
            await update.message.reply_text("❌ Нельзя снять создателя")
            return
        
        db.set_mod_rank('tg', target_id, 0, update.effective_user.id)
        
        target_user = db.get_user('tg', target_id)
        target_name = target_user.get('first_name', f"ID {target_id}")
        
        await update.message.reply_text(
            f"✅ С {target_name} снят статус модератора"
        )
    
    async def tg_cmd_staff(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать список модераторов"""
        mods = db.get_moderators('tg')
        
        if not mods:
            await update.message.reply_text("📭 В этом чате нет модераторов")
            return
        
        text = "🛡️ **СПИСОК МОДЕРАТОРОВ**\n\n"
        
        for mod in mods:
            platform_id, first_name, username, rank = mod
            status = "🟢"
            name = first_name or username or f"ID {platform_id}"
            text += f"{status} {name} — {MODER_RANKS[rank]}\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def tg_cmd_who_invited(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Кто назначил модератора"""
        if not context.args:
            await update.message.reply_text("❌ Использование: /who_invited [ссылка]")
            return
        
        target_link = context.args[0]
        target_id = await self._resolve_mention(update, context, target_link)
        
        if not target_id:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        await update.message.reply_text("ℹ️ Информация о назначении будет доступна в следующем обновлении")
    
    # ===================== ВАРНЫ =====================
    async def tg_cmd_warn(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выдать предупреждение пользователю"""
        if not await self._check_moder_rank(update, 1):
            return
        
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /warn [ссылка] [время] [причина]")
            return
        
        target_link = context.args[0]
        duration = context.args[1]
        reason = " ".join(context.args[2:]) if len(context.args) > 2 else "Нарушение"
        
        target_id = await self._resolve_mention(update, context, target_link)
        
        if not target_id:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        target_user = db.get_user('tg', target_id)
        target_name = target_user.get('first_name', f"ID {target_id}")
        
        settings = db.get_group_settings(str(update.effective_chat.id), 'tg')
        warns_limit = settings.get('warns_limit', 3)
        
        days = 30
        match = re.match(r'(\d+)\s*(д|день|дней|дня)', duration.lower())
        if match:
            days = int(match.group(1))
        
        warns = db.add_warn('tg', target_id, target_name, reason, update.effective_user.id, update.effective_user.first_name, days)
        
        await update.message.reply_text(
            f"⚠️ **Предупреждение выдано**\n\n"
            f"👤 {target_name}\n"
            f"⚠️ Варнов: {warns}/{warns_limit}\n"
            f"💬 Причина: {reason}"
        )
        
        if warns >= warns_limit:
            ban_period = settings.get('warns_ban_period', '1 день')
            db.ban_user('tg', target_id, target_name, f"Достигнут лимит предупреждений ({warns})", ban_period, update.effective_user.id, update.effective_user.first_name)
            await update.message.reply_text(f"🚫 Пользователь {target_name} забанен на {ban_period} (достигнут лимит варнов)")
        
        try:
            await context.bot.send_message(
                chat_id=int(target_id),
                text=f"⚠️ Вам выдано предупреждение ({warns}/{warns_limit})\nПричина: {reason}"
            )
        except:
            pass
    
    async def tg_cmd_warns(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать предупреждения пользователя"""
        if not context.args:
            await update.message.reply_text("❌ Использование: /warns [ссылка]")
            return
        
        target_link = context.args[0]
        target_id = await self._resolve_mention(update, context, target_link)
        
        if not target_id:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        target_user = db.get_user('tg', target_id)
        target_name = target_user.get('first_name', f"ID {target_id}")
        
        warns = db.get_warns('tg', target_id)
        
        if not warns:
            await update.message.reply_text(f"✅ У {target_name} нет предупреждений")
            return
        
        text = f"⚠️ **ПРЕДУПРЕЖДЕНИЯ {target_name.upper()}**\n\n"
        
        for i, warn in enumerate(warns, 1):
            reason = warn[4] or "Не указана"
            warned_by = warn[6] or "Неизвестно"
            warn_date = warn[7][:16] if warn[7] else "Неизвестно"
            text += f"{i}. {reason}\n   👮 {warned_by} — {warn_date}\n\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def tg_cmd_my_warns(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать свои предупреждения"""
        user = update.effective_user
        platform_id = str(user.id)
        
        warns = db.get_warns('tg', platform_id)
        
        if not warns:
            await update.message.reply_text("✅ У вас нет предупреждений")
            return
        
        text = f"⚠️ **ВАШИ ПРЕДУПРЕЖДЕНИЯ**\n\n"
        
        for i, warn in enumerate(warns, 1):
            reason = warn[4] or "Не указана"
            warned_by = warn[6] or "Неизвестно"
            warn_date = warn[7][:16] if warn[7] else "Неизвестно"
            text += f"{i}. {reason}\n   👮 {warned_by} — {warn_date}\n\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def tg_cmd_warnlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список последних предупреждений"""
        if not await self._check_moder_rank(update, 1):
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
            
            text += f"{i}. {username}\n"
            text += f"   💬 {reason}\n"
            text += f"   👮 {warned_by}\n"
            text += f"   📅 {warn_date}\n\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def tg_cmd_remove_warn(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Снять последнее предупреждение"""
        if not await self._check_moder_rank(update, 1):
            return
        
        if not context.args:
            await update.message.reply_text("❌ Использование: /remove_warn [ссылка]")
            return
        
        target_link = context.args[0]
        target_id = await self._resolve_mention(update, context, target_link)
        
        if not target_id:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        db.remove_warn('tg', target_id)
        
        target_user = db.get_user('tg', target_id)
        target_name = target_user.get('first_name', f"ID {target_id}")
        
        await update.message.reply_text(f"✅ Последнее предупреждение снято с {target_name}")
    
    async def tg_cmd_clear_warns(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Снять все предупреждения"""
        if not await self._check_moder_rank(update, 1):
            return
        
        if not context.args:
            await update.message.reply_text("❌ Использование: /clear_warns [ссылка]")
            return
        
        target_link = context.args[0]
        target_id = await self._resolve_mention(update, context, target_link)
        
        if not target_id:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        warns = db.get_warns('tg', target_id)
        for warn in warns:
            db.remove_warn('tg', target_id, warn[0])
        
        target_user = db.get_user('tg', target_id)
        target_name = target_user.get('first_name', f"ID {target_id}")
        
        await update.message.reply_text(f"✅ Все предупреждения сняты с {target_name}")
    
    # ===================== МУТ =====================
    async def tg_cmd_mute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Замутить пользователя"""
        if not await self._check_moder_rank(update, 1):
            return
        
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /mute [ссылка] [время] [причина]")
            return
        
        target_link = context.args[0]
        try:
            minutes = int(context.args[1])
        except:
            await update.message.reply_text("❌ Время должно быть числом (минуты)")
            return
        
        reason = " ".join(context.args[2:]) if len(context.args) > 2 else "Нарушение"
        
        target_id = await self._resolve_mention(update, context, target_link)
        
        if not target_id:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        target_user = db.get_user('tg', target_id)
        target_name = target_user.get('first_name', f"ID {target_id}")
        
        db.mute_user('tg', target_id, target_name, minutes, reason, update.effective_user.id, update.effective_user.first_name)
        
        await update.message.reply_text(
            f"🔇 **Пользователь замучен**\n\n"
            f"👤 {target_name}\n"
            f"⏱ Время: {minutes} мин\n"
            f"💬 Причина: {reason}"
        )
        
        try:
            await context.bot.send_message(
                chat_id=int(target_id),
                text=f"🔇 Вы замучены на {minutes} минут.\nПричина: {reason}"
            )
        except:
            pass
    
    async def tg_cmd_unmute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Снять мут"""
        if not await self._check_moder_rank(update, 1):
            return
        
        if not context.args:
            await update.message.reply_text("❌ Использование: /unmute [ссылка]")
            return
        
        target_link = context.args[0]
        target_id = await self._resolve_mention(update, context, target_link)
        
        if not target_id:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        db.unmute_user('tg', target_id)
        
        target_user = db.get_user('tg', target_id)
        target_name = target_user.get('first_name', f"ID {target_id}")
        
        await update.message.reply_text(f"✅ Мут снят с {target_name}")
        
        try:
            await context.bot.send_message(
                chat_id=int(target_id),
                text="✅ Ваш мут снят"
            )
        except:
            pass
    
    async def tg_cmd_mutelist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список замученных"""
        if not await self._check_moder_rank(update, 1):
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
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def tg_cmd_check_mute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Проверить, замучен ли пользователь"""
        if not context.args:
            await update.message.reply_text("❌ Использование: /check_mute [ссылка]")
            return
        
        target_link = context.args[0]
        target_id = await self._resolve_mention(update, context, target_link)
        
        if not target_id:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        if db.is_muted('tg', target_id):
            user_data = db.get_user('tg', target_id)
            mute_until = datetime.datetime.fromisoformat(user_data['mute_until'])
            remaining = mute_until - datetime.datetime.now()
            minutes = remaining.seconds // 60
            await update.message.reply_text(f"🔇 Пользователь замучен. Осталось: {minutes} мин")
        else:
            await update.message.reply_text("✅ Пользователь не замучен")
    
    # ===================== БАН =====================
    async def tg_cmd_ban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Забанить пользователя"""
        if not await self._check_moder_rank(update, 2):
            return
        
        if len(context.args) < 3:
            await update.message.reply_text("❌ Использование: /ban [ссылка] [время] [причина]")
            return
        
        target_link = context.args[0]
        duration = context.args[1]
        reason = " ".join(context.args[2:])
        
        target_id = await self._resolve_mention(update, context, target_link)
        
        if not target_id:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        target_user = db.get_user('tg', target_id)
        target_name = target_user.get('first_name', f"ID {target_id}")
        
        db.ban_user('tg', target_id, target_name, reason, duration, update.effective_user.id, update.effective_user.first_name)
        
        await update.message.reply_text(
            f"🚫 **Пользователь забанен**\n\n"
            f"👤 {target_name}\n"
            f"⏱ Срок: {duration}\n"
            f"💬 Причина: {reason}"
        )
        
        try:
            await context.bot.send_message(
                chat_id=int(target_id),
                text=f"🚫 Вы забанены.\nСрок: {duration}\nПричина: {reason}"
            )
        except:
            pass
    
    async def tg_cmd_unban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Разбанить пользователя"""
        if not await self._check_moder_rank(update, 2):
            return
        
        if not context.args:
            await update.message.reply_text("❌ Использование: /unban [ссылка]")
            return
        
        target_link = context.args[0]
        target_id = await self._resolve_mention(update, context, target_link)
        
        if not target_id:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        db.unban_user('tg', target_id)
        
        target_user = db.get_user('tg', target_id)
        target_name = target_user.get('first_name', f"ID {target_id}")
        
        await update.message.reply_text(f"✅ Пользователь {target_name} разбанен")
        
        try:
            await context.bot.send_message(
                chat_id=int(target_id),
                text="✅ Вы разбанены"
            )
        except:
            pass
    
    async def tg_cmd_banlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список забаненных"""
        if not await self._check_moder_rank(update, 1):
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
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    # ===================== ПРАВИЛА И НАСТРОЙКИ =====================
    async def tg_cmd_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать правила чата"""
        chat_id = str(update.effective_chat.id)
        settings = db.get_group_settings(chat_id, 'tg')
        rules = settings.get('rules', 'Правила не установлены')
        
        await update.message.reply_text(f"📖 **ПРАВИЛА ЧАТА**\n\n{rules}", parse_mode='Markdown')
    
    async def tg_cmd_set_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установить правила чата"""
        if not await self._check_moder_rank(update, 3):
            return
        
        if not context.args:
            await update.message.reply_text("❌ Использование: /set_rules [текст правил]")
            return
        
        rules = " ".join(context.args)
        chat_id = str(update.effective_chat.id)
        
        db.update_group_setting(chat_id, 'tg', 'rules', rules)
        
        await update.message.reply_text(f"✅ Правила установлены!")
    
    async def tg_cmd_warns_limit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установить лимит предупреждений"""
        if not await self._check_moder_rank(update, 3):
            return
        
        if not context.args:
            await update.message.reply_text("❌ Использование: /warns_limit [число]")
            return
        
        try:
            limit = int(context.args[0])
        except:
            await update.message.reply_text("❌ Введите число")
            return
        
        chat_id = str(update.effective_chat.id)
        db.update_group_setting(chat_id, 'tg', 'warns_limit', limit)
        
        await update.message.reply_text(f"✅ Лимит предупреждений установлен: {limit}")
    
    async def tg_cmd_mute_period(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установить срок мута по умолчанию"""
        if not await self._check_moder_rank(update, 3):
            return
        
        if not context.args:
            await update.message.reply_text("❌ Использование: /mute_period [время]")
            return
        
        period = " ".join(context.args)
        chat_id = str(update.effective_chat.id)
        db.update_group_setting(chat_id, 'tg', 'mute_period', period)
        
        await update.message.reply_text(f"✅ Срок мута по умолчанию установлен: {period}")
    
    async def tg_cmd_ban_period(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установить срок бана по умолчанию"""
        if not await self._check_moder_rank(update, 3):
            return
        
        if not context.args:
            await update.message.reply_text("❌ Использование: /ban_period [время]")
            return
        
        period = " ".join(context.args)
        chat_id = str(update.effective_chat.id)
        db.update_group_setting(chat_id, 'tg', 'ban_period', period)
        
        await update.message.reply_text(f"✅ Срок бана по умолчанию установлен: {period}")
    
    # ===================== РУССКАЯ РУЛЕТКА =====================
    async def tg_cmd_rr(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о русской рулетке"""
        text = (
            "💣 **РУССКАЯ РУЛЕТКА**\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**ПРАВИЛА**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "• В барабане 1-3 патрона\n"
            "• Размер барабана: 6-10 позиций\n"
            "• Игроки по очереди стреляют\n"
            "• Победитель забирает все ставки\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**КОМАНДЫ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/rr_start [игроки] [ставка] - создать лобби\n"
            "/rr_join [ID] - присоединиться\n"
            "/rr_shot - сделать выстрел"
        )
        
        keyboard = [
            [InlineKeyboardButton("🎲 Создать игру", callback_data="rr_create")],
            [InlineKeyboardButton("🔙 Назад", callback_data="games_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def tg_cmd_rr_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Создать лобби для русской рулетки"""
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /rr_start [игроки (2-6)] [ставка]")
            return
        
        try:
            max_players = int(context.args[0])
            bet = int(context.args[1])
        except:
            await update.message.reply_text("❌ Неправильный формат")
            return
        
        if max_players < 2 or max_players > 6:
            await update.message.reply_text("❌ Количество игроков должно быть от 2 до 6")
            return
        
        user = update.effective_user
        platform_id = str(user.id)
        
        user_data = db.get_user('tg', platform_id)
        
        if user_data['rr_money'] < bet:
            await update.message.reply_text(f"❌ Недостаточно черепков! У тебя {user_data['rr_money']} 💀")
            return
        
        db.add_coins('tg', platform_id, -bet, "rr_money")
        lobby_id = db.rr_create_lobby(platform_id, max_players, bet)
        
        await update.message.reply_text(
            f"💣 **ЛОББИ СОЗДАНО!**\n\n"
            f"▫️ **ID:** {lobby_id}\n"
            f"▫️ **Создатель:** {user.first_name}\n"
            f"▫️ **Игроков:** 1/{max_players}\n"
            f"▫️ **Ставка:** {bet} 💀\n\n"
            f"Присоединиться: /rr_join {lobby_id}",
            parse_mode='Markdown'
        )
    
    async def tg_cmd_rr_join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Присоединиться к лобби русской рулетки"""
        if not context.args:
            await update.message.reply_text("❌ Укажи ID лобби: /rr_join 1")
            return
        
        try:
            lobby_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ Неправильный ID")
            return
        
        user = update.effective_user
        platform_id = str(user.id)
        
        if db.rr_join_lobby(lobby_id, platform_id):
            await update.message.reply_text(f"✅ Ты присоединился к лобби {lobby_id}!")
            
            db.cursor.execute("SELECT players, max_players, bet FROM rr_lobbies WHERE id = ?", (lobby_id,))
            result = db.cursor.fetchone()
            if result:
                players = json.loads(result[0])
                max_players = result[1]
                
                if len(players) == max_players:
                    game_data = db.rr_start_game(lobby_id)
                    if game_data:
                        game_id, players, cylinder_size, bullets, positions = game_data
                        
                        for player_id in players:
                            try:
                                await context.bot.send_message(
                                    chat_id=int(player_id),
                                    text=f"💣 **ИГРА НАЧАЛАСЬ!**\n\n"
                                         f"Барабан: {cylinder_size} позиций\n"
                                         f"Патронов: {bullets}\n\n"
                                         f"Первый ходит: {players[0]}"
                                )
                            except:
                                pass
        else:
            await update.message.reply_text("❌ Не удалось присоединиться")
    
    async def tg_cmd_rr_shot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сделать выстрел в русской рулетке"""
        user = update.effective_user
        platform_id = str(user.id)
        
        db.cursor.execute(
            "SELECT * FROM rr_games WHERE players LIKE ? AND phase = 'playing'",
            (f'%{platform_id}%',)
        )
        game = db.cursor.fetchone()
        
        if not game:
            await update.message.reply_text("❌ Ты не участвуешь в активной игре")
            return
        
        columns = [description[0] for description in db.cursor.description]
        game_dict = dict(zip(columns, game))
        
        result = db.rr_make_shot(game_dict['id'], platform_id)
        
        if result == "not_your_turn":
            await update.message.reply_text("❌ Сейчас не твой ход")
        elif result == "dead":
            await update.message.reply_text("💀 **БАХ!** Ты погиб...")
        elif result == "alive":
            await update.message.reply_text("✅ **ЩЕЛК!** Ты выжил!")
        elif isinstance(result, tuple) and result[0] == "game_over":
            winner_id = result[1]
            winner_data = await context.bot.get_chat(int(winner_id))
            
            # Начисляем выигрыш
            db.cursor.execute("SELECT bet FROM rr_lobbies WHERE id = ?", (game_dict['lobby_id'],))
            bet = db.cursor.fetchone()[0]
            total_pot = bet * len(json.loads(game_dict['players']))
            db.add_coins('tg', winner_id, total_pot, "rr_money")
            
            await update.message.reply_text(
                f"🏆 **ИГРА ОКОНЧЕНА!**\n\n"
                f"Победитель: {winner_data.first_name}\n"
                f"💰 Выигрыш: {total_pot} 💀",
                parse_mode='Markdown'
            )
    
    # ===================== КРЕСТИКИ-НОЛИКИ 3D =====================
    async def tg_cmd_ttt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о крестиках-ноликах 3D"""
        text = (
            "⭕ **КРЕСТИКИ-НОЛИКИ 3D**\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**ПРАВИЛА**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "• В каждой клетке поля находится ещё одно поле\n"
            "• Нужно выиграть на 3 малых полях в ряд\n"
            "• Победа на малом поле делает его вашим\n"
            "• Игра продолжается пока кто-то не победит\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**КОМАНДЫ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/ttt_challenge [ник] - вызвать игрока\n"
            "/ttt_move [клетка] - сделать ход (клетка: ряд_колонка_подряд_подколонка, например 1_1_2_2)"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="games_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def tg_cmd_ttt_challenge(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Вызвать игрока на крестики-нолики 3D"""
        if not context.args:
            await update.message.reply_text("❌ Использование: /ttt_challenge [ник]")
            return
        
        target_name = context.args[0]
        user = update.effective_user
        platform_id = str(user.id)
        
        target_user = db.get_user_by_username('tg', target_name)
        
        if not target_user:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        target_id = target_user[2]
        
        game_id = db.ttt_create_game(platform_id, target_id)
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Принять", callback_data=f"ttt_accept_{game_id}"),
                InlineKeyboardButton("❌ Отклонить", callback_data=f"ttt_decline_{game_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await context.bot.send_message(
                chat_id=int(target_id),
                text=f"⭕ {user.first_name} вызывает тебя на игру в крестики-нолики 3D!\n\nСогласен?",
                reply_markup=reply_markup
            )
            await update.message.reply_text("✅ Запрос отправлен!")
        except:
            await update.message.reply_text("❌ Не удалось отправить запрос")
    
    async def tg_cmd_ttt_move(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сделать ход в крестики-нолики 3D"""
        if len(context.args) < 1:
            await update.message.reply_text("❌ Использование: /ttt_move [клетка] (например 1_1_2_2)")
            return
        
        try:
            parts = context.args[0].split('_')
            if len(parts) != 4:
                raise ValueError
            main_row, main_col, sub_row, sub_col = map(int, parts)
        except:
            await update.message.reply_text("❌ Неправильный формат. Используй: ряд_колонка_подряд_подколонка (1_1_2_2)")
            return
        
        user = update.effective_user
        platform_id = str(user.id)
        
        db.cursor.execute(
            "SELECT * FROM ttt_games WHERE (player_x = ? OR player_o = ?) AND status = 'playing'",
            (platform_id, platform_id)
        )
        game = db.cursor.fetchone()
        
        if not game:
            await update.message.reply_text("❌ У тебя нет активной игры")
            return
        
        columns = [description[0] for description in db.cursor.description]
        game_dict = dict(zip(columns, game))
        
        result = db.ttt_make_move(game_dict['id'], platform_id, main_row-1, main_col-1, sub_row-1, sub_col-1)
        
        if result == "not_your_turn":
            await update.message.reply_text("❌ Сейчас не твой ход")
        elif result == "cell_occupied":
            await update.message.reply_text("❌ Эта клетка уже занята")
        elif result and result['status'] == 'finished':
            winner = "Ты" if result['winner'] == platform_id else "Противник"
            await update.message.reply_text(f"🏆 **Игра окончена!**\n\nПобедитель: {winner}")
        else:
            await update.message.reply_text("✅ Ход сделан!")
    
    # ===================== МАФИЯ =====================
    async def tg_cmd_mafia(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о мафии"""
        text = (
            "🔪 **МАФИЯ**\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**ПРАВИЛА**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "• Игроки делятся на мафию и мирных\n"
            "• Ночью мафия убивает, днем все обсуждают\n"
            "• Цель мафии - убить всех мирных\n"
            "• Цель мирных - найти мафию\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**ФАЗЫ ИГРЫ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🌙 **Ночь** - мафия выбирает жертву\n"
            "☀️ **День** - обсуждение и голосование\n"
            "⚰️ **Смерть** - игрок покидает игру\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**КОМАНДЫ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/mafia_create - создать игру\n"
            "/mafia_join [ID] - присоединиться\n"
            "/mafia_start - начать игру"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="games_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def tg_cmd_mafia_create(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Создать игру в мафию"""
        user = update.effective_user
        platform_id = str(user.id)
        
        game_id = db.mafia_create_game(platform_id)
        
        await update.message.reply_text(
            f"🔪 **ИГРА МАФИЯ СОЗДАНА!**\n\n"
            f"▫️ **ID игры:** {game_id}\n"
            f"▫️ **Создатель:** {user.first_name}\n"
            f"▫️ **Игроков:** 1/10\n\n"
            f"Присоединиться: /mafia_join {game_id}",
            parse_mode='Markdown'
        )
    
    async def tg_cmd_mafia_join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Присоединиться к игре в мафию"""
        if not context.args:
            await update.message.reply_text("❌ Укажи ID игры: /mafia_join 1")
            return
        
        try:
            game_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ Неправильный ID")
            return
        
        user = update.effective_user
        platform_id = str(user.id)
        
        if db.mafia_join_game(game_id, platform_id):
            await update.message.reply_text(f"✅ Ты присоединился к игре {game_id}!")
        else:
            await update.message.reply_text("❌ Не удалось присоединиться")
    
    async def tg_cmd_mafia_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать игру в мафию"""
        user = update.effective_user
        platform_id = str(user.id)
        
        db.cursor.execute("SELECT * FROM mafia_games WHERE creator_id = ? AND status = 'waiting'", (platform_id,))
        game = db.cursor.fetchone()
        
        if not game:
            await update.message.reply_text("❌ У тебя нет созданной игры")
            return
        
        columns = [description[0] for description in db.cursor.description]
        game_dict = dict(zip(columns, game))
        
        roles = db.mafia_start_game(game_dict['id'])
        
        if roles == "not_enough_players":
            await update.message.reply_text("❌ Недостаточно игроков (нужно минимум 4)")
            return
        
        players = json.loads(game_dict['players'])
        
        for player_id in players:
            role = roles[player_id]
            role_text = "🔪 Мафия" if role == 'mafia' else "👨‍🌾 Мирный"
            
            try:
                if player_id == platform_id:
                    await update.message.reply_text(f"🔪 **ИГРА НАЧАЛАСЬ!**\n\nТвоя роль: {role_text}")
                else:
                    await context.bot.send_message(
                        chat_id=int(player_id),
                        text=f"🔪 **ИГРА НАЧАЛАСЬ!**\n\nТвоя роль: {role_text}"
                    )
            except:
                pass
        
        await update.message.reply_text("🌙 **Наступила ночь**\nМафия просыпается и выбирает жертву...")
    
    # ===================== САПЁР =====================
    async def tg_cmd_minesweeper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать игру в сапёра"""
        user = update.effective_user
        platform_id = str(user.id)
        
        difficulty = "новичок"
        if context.args:
            difficulty = context.args[0].lower()
        
        sizes = {
            "новичок": (8, 8, 10),
            "любитель": (12, 12, 30),
            "профи": (16, 16, 50)
        }
        
        if difficulty not in sizes:
            await update.message.reply_text("❌ Сложность должна быть: новичок, любитель или профи")
            return
        
        width, height, mines = sizes[difficulty]
        
        game_id = db.minesweeper_create_game(platform_id, width, height, mines)
        
        board_display = self._format_minesweeper_board(game_id, width, height)
        
        await update.message.reply_text(
            f"💣 **САПЁР** (сложность: {difficulty})\n\n"
            f"{board_display}\n\n"
            f"Команды:\n"
            f"/ms_reveal X Y - открыть клетку\n"
            f"/ms_flag X Y - поставить флаг",
            parse_mode='Markdown'
        )
    
    def _format_minesweeper_board(self, game_id, width, height):
        """Форматирует поле сапёра для отображения"""
        game = db.minesweeper_get_game(game_id)
        if not game:
            return "Игра не найдена"
        
        revealed = json.loads(game['revealed'])
        flags = json.loads(game['flags'])
        status = game['status']
        
        if status == 'lost':
            board = json.loads(game['board'])
        
        header = "   " + " ".join([f"{i:2}" for i in range(width)]) + "\n"
        board_display = header
        
        for y in range(height):
            row = f"{y:2} "
            for x in range(width):
                if flags[y][x]:
                    row += "🚩 "
                elif revealed[y][x]:
                    if status == 'lost' and board[y][x] == -1:
                        row += "💣 "
                    elif board[y][x] == 0:
                        row += "⬜ "
                    else:
                        row += f"{board[y][x]}  "
                else:
                    row += "⬛ "
            board_display += row + "\n"
        
        return board_display
    
    async def tg_cmd_ms_reveal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Открыть клетку в сапёре"""
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /ms_reveal X Y")
            return
        
        try:
            x = int(context.args[0])
            y = int(context.args[1])
        except:
            await update.message.reply_text("❌ Координаты должны быть числами")
            return
        
        user = update.effective_user
        platform_id = str(user.id)
        
        db.cursor.execute(
            "SELECT * FROM minesweeper_games WHERE user_id = ? AND status = 'playing' ORDER BY last_move DESC LIMIT 1",
            (platform_id,)
        )
        game = db.cursor.fetchone()
        
        if not game:
            await update.message.reply_text("❌ У тебя нет активной игры. Начни новую через /minesweeper")
            return
        
        columns = [description[0] for description in db.cursor.description]
        game_dict = dict(zip(columns, game))
        
        result = db.minesweeper_reveal(game_dict['id'], x, y)
        
        if result == "already_revealed":
            await update.message.reply_text("❌ Эта клетка уже открыта или помечена флагом")
            return
        
        board_display = self._format_minesweeper_board(game_dict['id'], game_dict['width'], game_dict['height'])
        
        if result['status'] == 'lost':
            await update.message.reply_text(
                f"💥 **Ты проиграл!**\n\n{board_display}",
                parse_mode='Markdown'
            )
        elif result['status'] == 'won':
            db.cursor.execute("UPDATE users SET minesweeper_wins = minesweeper_wins + 1, minesweeper_games = minesweeper_games + 1 WHERE platform = ? AND platform_id = ?", ('tg', platform_id))
            db.conn.commit()
            await update.message.reply_text(
                f"🏆 **ПОБЕДА!**\n\n{board_display}",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"✅ Ход сделан\n\n{board_display}",
                parse_mode='Markdown'
            )
    
    async def tg_cmd_ms_flag(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Поставить/снять флаг в сапёре"""
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /ms_flag X Y")
            return
        
        try:
            x = int(context.args[0])
            y = int(context.args[1])
        except:
            await update.message.reply_text("❌ Координаты должны быть числами")
            return
        
        user = update.effective_user
        platform_id = str(user.id)
        
        db.cursor.execute(
            "SELECT * FROM minesweeper_games WHERE user_id = ? AND status = 'playing' ORDER BY last_move DESC LIMIT 1",
            (platform_id,)
        )
        game = db.cursor.fetchone()
        
        if not game:
            await update.message.reply_text("❌ У тебя нет активной игры. Начни новую через /minesweeper")
            return
        
        columns = [description[0] for description in db.cursor.description]
        game_dict = dict(zip(columns, game))
        
        result = db.minesweeper_toggle_flag(game_dict['id'], x, y)
        
        if result == "already_revealed":
            await update.message.reply_text("❌ Нельзя поставить флаг на открытую клетку")
            return
        
        board_display = self._format_minesweeper_board(game_dict['id'], game_dict['width'], game_dict['height'])
        await update.message.reply_text(f"🚩 Флаг обновлен\n\n{board_display}", parse_mode='Markdown')
    
    # ===================== КАМЕНЬ-НОЖНИЦЫ-БУМАГА =====================
    async def tg_cmd_rps(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Игра в камень-ножницы-бумагу с ботом"""
        keyboard = [
            [
                InlineKeyboardButton("🪨 Камень", callback_data="rps_rock"),
                InlineKeyboardButton("✂️ Ножницы", callback_data="rps_scissors"),
                InlineKeyboardButton("📄 Бумага", callback_data="rps_paper")
            ],
            [InlineKeyboardButton("🔙 Назад", callback_data="games_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "✊ **КАМЕНЬ-НОЖНИЦЫ-БУМАГА**\n\n"
            "Выбери свой ход:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    # ===================== ПОЛЕЗНЫЕ КОМАНДЫ =====================
    async def tg_cmd_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Правдивость события"""
        if not context.args:
            await update.message.reply_text("❌ Использование: /info [событие]")
            return
        
        event = " ".join(context.args)
        probability = random.randint(0, 100)
        
        await update.message.reply_text(
            f"📊 **ПРАВДИВОСТЬ СОБЫТИЯ**\n\n"
            f"Событие: {event}\n"
            f"Вероятность: {probability}%",
            parse_mode='Markdown'
        )
    
    async def tg_cmd_holidays(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Праздники сегодня"""
        today = datetime.datetime.now()
        
        holidays = {
            "01-01": "🎄 Новый год",
            "01-07": "🎅 Рождество",
            "02-23": "🎖️ День защитника Отечества",
            "03-08": "🌸 Международный женский день",
            "05-01": "🌷 Праздник Весны и Труда",
            "05-09": "🎗️ День Победы",
            "06-12": "🇷🇺 День России",
            "11-04": "🤝 День народного единства"
        }
        
        date_key = today.strftime("%m-%d")
        
        if date_key in holidays:
            await update.message.reply_text(f"📅 **Сегодня:** {holidays[date_key]}", parse_mode='Markdown')
        else:
            await update.message.reply_text("📅 Сегодня нет праздников", parse_mode='Markdown')
    
    async def tg_cmd_fact(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Случайный факт"""
        facts = [
            "🐝 Пчелы могут узнавать человеческие лица.",
            "🌍 В Антарктиде есть только один постоянный вид насекомых.",
            "🦑 Кальмары имеют три сердца.",
            "🐘 Слоны - единственные млекопитающие, которые не могут прыгать.",
            "🍌 Бананы технически являются ягодами.",
            "🌊 Океаны покрывают 71% поверхности Земли.",
            "🚀 Следы на Луне останутся на миллионы лет.",
            "💧 Человек может прожить без еды около месяца, но без воды только неделю.",
            "🧠 Мозг человека генерирует достаточно электричества, чтобы зажечь лампочку.",
            "👁️ Человеческий глаз может различать около 10 миллионов цветов."
        ]
        
        fact = random.choice(facts)
        
        await update.message.reply_text(f"📌 **СЛУЧАЙНЫЙ ФАКТ**\n\n{fact}", parse_mode='Markdown')
    
    async def tg_cmd_wisdom(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Мудрая цитата"""
        quotes = [
            "🌟 Жизнь - это то, что с тобой происходит, пока ты строишь планы.",
            "💫 Будь тем изменением, которое хочешь увидеть в мире.",
            "✨ Счастье не в том, чтобы делать всегда, что хочешь, а в том, чтобы всегда хотеть того, что делаешь.",
            "⭐ Самая большая слава не в том, чтобы никогда не падать, а в том, чтобы вставать каждый раз, когда падаешь.",
            "☀️ Жизнь измеряется не количеством вдохов, а количеством моментов, от которых захватывает дух."
        ]
        
        quote = random.choice(quotes)
        
        await update.message.reply_text(f"💭 **МУДРАЯ МЫСЛЬ**\n\n{quote}", parse_mode='Markdown')
    
    async def tg_cmd_population(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Население Земли"""
        world_pop = 7_900_000_000
        
        await update.message.reply_text(
            f"🌍 **НАСЕЛЕНИЕ ЗЕМЛИ**\n\n"
            f"Примерно: {world_pop:,} человек",
            parse_mode='Markdown'
        )
    
    async def tg_cmd_bitcoin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Курс биткоина"""
        price_usd = random.randint(40000, 70000)
        price_rub = price_usd * 91.5
        
        await update.message.reply_text(
            f"₿ **КУРС БИТКОИНА**\n\n"
            f"USD: ${price_usd:,}\n"
            f"RUB: ₽{int(price_rub):,}",
            parse_mode='Markdown'
        )
    
    # ===================== ЗАКЛАДКИ И НАГРАДЫ =====================
    async def tg_cmd_add_bookmark(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Создать закладку"""
        if not context.args:
            await update.message.reply_text("❌ Использование: /bookmark [описание]")
            return
        
        description = " ".join(context.args)
        user = update.effective_user
        platform_id = str(user.id)
        
        message_link = f"https://t.me/c/{str(update.effective_chat.id)[4:]}/{update.message.message_id}"
        message_text = update.message.text
        
        db.add_bookmark('tg', platform_id, description, message_link, message_text)
        
        await update.message.reply_text(f"✅ Закладка создана: {description}")
    
    async def tg_cmd_bookmarks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список закладок"""
        user = update.effective_user
        platform_id = str(user.id)
        
        bookmarks = db.get_bookmarks('tg', platform_id)
        
        if not bookmarks:
            await update.message.reply_text(
                "📭 У вас нет закладок.\n\n"
                "💬 Для создания закладки используйте:\n"
                "/bookmark [описание]"
            )
            return
        
        text = "📌 **ВАШИ ЗАКЛАДКИ**\n\n"
        
        for i, bookmark in enumerate(bookmarks, 1):
            text += f"{i}. {bookmark[3]} — [ссылка]({bookmark[4]})\n"
        
        await update.message.reply_text(text, parse_mode='Markdown', disable_web_page_preview=True)
    
    async def tg_cmd_add_award(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выдать награду (для админов)"""
        if not await self._check_moder_rank(update, 3):
            return
        
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /award [ник] [название награды]")
            return
        
        target_name = context.args[0]
        award_name = " ".join(context.args[1:])
        
        target_user = db.get_user_by_username('tg', target_name)
        
        if not target_user:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        target_id = target_user[2]
        
        db.add_award('tg', target_id, award_name, award_name, update.effective_user.id, update.effective_user.first_name)
        
        await update.message.reply_text(f"✅ Награда '{award_name}' выдана пользователю {target_name}")
        
        try:
            await context.bot.send_message(
                chat_id=int(target_id),
                text=f"🏅 Вам выдана награда: {award_name}"
            )
        except:
            pass
    
    async def tg_cmd_awards(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список наград"""
        user = update.effective_user
        platform_id = str(user.id)
        
        awards = db.get_awards('tg', platform_id)
        
        if not awards:
            await update.message.reply_text("🏅 У вас пока нет наград")
            return
        
        text = "🏅 **ВАШИ НАГРАДЫ**\n\n"
        
        for award in awards:
            award_date = datetime.datetime.fromisoformat(award[6]).strftime("%d.%m.%Y")
            text += f"▫️ **{award[3]}** — от {award[5]} ({award_date})\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    # ===================== ОБРАБОТКА СООБЩЕНИЙ =====================
    async def tg_handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка обычных сообщений"""
        user = update.effective_user
        platform_id = str(user.id)
        message_text = update.message.text
        
        user_data = db.get_user('tg', platform_id, user.username or "", user.first_name, user.last_name or "")
        db.update_activity('tg', platform_id)
        db.add_message_count('tg', platform_id)
        
        if db.is_banned('tg', platform_id) or db.is_muted('tg', platform_id):
            return
        
        # Проверка на длительное молчание
        last_msg_time = self.last_activity['tg'].get(platform_id, 0)
        current_time = time.time()
        
        if last_msg_time > 0 and current_time - last_msg_time > 30 * 24 * 3600:
            await update.message.reply_text(
                f"⚡️⚡️⚡️ Святые угодники!\n"
                f"{user.first_name} заговорил после более, чем месячного молчания!!! Поприветствуйте молчуна! 👏"
            )
        
        self.last_activity['tg'][platform_id] = current_time
        
        if user_data['messages_count'] == 1:
            await update.message.reply_text(f"🌟 Добро пожаловать, {user.first_name}! Используй /help для списка команд.")
    
    async def tg_handle_new_members(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Приветствие новых участников"""
        chat_id = str(update.effective_chat.id)
        settings = db.get_group_settings(chat_id, 'tg')
        
        if not settings.get('welcome_enabled', 1):
            return
        
        welcome = settings.get('welcome_message', '🌟 Добро пожаловать, {user}!')
        
        for member in update.message.new_chat_members:
            if member.is_bot:
                continue
            
            welcome_text = welcome.replace('{user}', f"[{member.first_name}](tg://user?id={member.id})")
            await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    async def tg_handle_left_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Прощание с участниками"""
        chat_id = str(update.effective_chat.id)
        settings = db.get_group_settings(chat_id, 'tg')
        
        if not settings.get('goodbye_enabled', 1):
            return
        
        goodbye = settings.get('goodbye_message', '👋 Пока, {user}!')
        member = update.message.left_chat_member
        
        if member.is_bot:
            return
        
        goodbye_text = goodbye.replace('{user}', f"[{member.first_name}](tg://user?id={member.id})")
        await update.message.reply_text(goodbye_text, parse_mode='Markdown')
    
    # ===================== ОБРАБОТКА КНОПОК =====================
    async def tg_button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатий на инлайн-кнопки"""
        query = update.callback_query
        await query.answer()
        data = query.data
        
        # Главное меню
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
        elif data == "players":
            await self.tg_cmd_players(update, context)
        elif data == "help":
            await self.tg_cmd_help(update, context)
        elif data == "rules":
            await self.tg_cmd_rules(update, context)
        elif data == "moderation":
            keyboard = [
                [InlineKeyboardButton("🛡️ Модераторы", callback_data="staff"),
                 InlineKeyboardButton("⚠️ Варны", callback_data="warn_menu")],
                [InlineKeyboardButton("🔇 Муты", callback_data="mutelist"),
                 InlineKeyboardButton("🚫 Баны", callback_data="banlist")],
                [InlineKeyboardButton("📖 Правила", callback_data="rules"),
                 InlineKeyboardButton("🔙 Назад", callback_data="menu_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "🛡️ **МОДЕРАЦИЯ**\n\nВыберите раздел:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        elif data == "games":
            keyboard = [
                [InlineKeyboardButton("💣 Русская рулетка", callback_data="rr"),
                 InlineKeyboardButton("⭕ Крестики-нолики 3D", callback_data="ttt")],
                [InlineKeyboardButton("🔪 Мафия", callback_data="mafia"),
                 InlineKeyboardButton("💥 Сапёр", callback_data="minesweeper")],
                [InlineKeyboardButton("✊ КНБ", callback_data="rps"),
                 InlineKeyboardButton("🔙 Назад", callback_data="menu_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "🎮 **ИГРЫ**\n\nВыберите игру:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        elif data == "bookmarks_menu":
            await self.tg_cmd_bookmarks(update, context)
        elif data == "awards_menu":
            await self.tg_cmd_awards(update, context)
        elif data == "staff":
            await self.tg_cmd_staff(update, context)
        elif data == "warn_menu":
            keyboard = [
                [InlineKeyboardButton("📋 Список варнов", callback_data="warnlist"),
                 InlineKeyboardButton("👤 Мои варны", callback_data="my_warns")],
                [InlineKeyboardButton("🔙 Назад", callback_data="moderation")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "⚠️ **ПРЕДУПРЕЖДЕНИЯ**\n\nВыберите действие:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        elif data == "warnlist":
            context.args = []
            await self.tg_cmd_warnlist(update, context)
        elif data == "my_warns":
            await self.tg_cmd_my_warns(update, context)
        elif data == "mutelist":
            context.args = []
            await self.tg_cmd_mutelist(update, context)
        elif data == "banlist":
            context.args = []
            await self.tg_cmd_banlist(update, context)
        
        # Босс
        elif data.startswith("boss_fight_"):
            boss_id = data.split("_")[2]
            context.args = [boss_id]
            await self.tg_cmd_boss_fight(update, context)
        elif data == "regen":
            await self.tg_cmd_regen(update, context)
        
        # Магазин
        elif data == "buy_potions":
            await query.edit_message_text(
                "💊 **ЗЕЛЬЯ**\n\n"
                "▫️ Зелье здоровья — 50 🪙 (❤️+30)\n"
                "▫️ Большое зелье — 100 🪙 (❤️+70)\n\n"
                "Купить: /buy [название]"
            )
        elif data == "buy_weapons":
            await query.edit_message_text(
                "⚔️ **ОРУЖИЕ**\n\n"
                "▫️ Меч — 200 🪙 (⚔️+10)\n"
                "▫️ Легендарный меч — 500 🪙 (⚔️+30)\n\n"
                "Купить: /buy [название]"
            )
        elif data == "buy_energy":
            await query.edit_message_text(
                "⚡ **ЭНЕРГИЯ**\n\n"
                "▫️ Энергетик — 30 🪙 (⚡+20)\n"
                "▫️ Батарейка — 80 🪙 (⚡+50)\n\n"
                "Купить: /buy [название]"
            )
        elif data == "buy_diamonds":
            await query.edit_message_text(
                "💎 **АЛМАЗЫ**\n\n"
                "▫️ Алмаз — 100 🪙 (💎+1)\n\n"
                "Купить: /buy алмаз"
            )
        elif data == "buy_rr_items":
            await query.edit_message_text(
                "🎲 **ПРЕДМЕТЫ ДЛЯ РУЛЕТКИ**\n\n"
                "▫️ Монета Демона — 500 🪙\n"
                "▫️ Кровавый Глаз — 300 🪙\n"
                "▫️ Маска Клоуна — 1000 🪙\n\n"
                "Купить: /buy [название]"
            )
        
        # Игры
        elif data == "rr":
            await self.tg_cmd_rr(update, context)
        elif data == "ttt":
            await self.tg_cmd_ttt(update, context)
        elif data == "mafia":
            await self.tg_cmd_mafia(update, context)
        elif data == "minesweeper":
            context.args = ["новичок"]
            await self.tg_cmd_minesweeper(update, context)
        elif data == "rps":
            await self.tg_cmd_rps(update, context)
        elif data == "rr_create":
            await query.edit_message_text(
                "💣 **СОЗДАНИЕ ИГРЫ**\n\n"
                "Используй команду:\n"
                "/rr_start [игроки] [ставка]\n\n"
                "Пример: /rr_start 4 100"
            )
        
        # Крестики-нолики
        elif data.startswith("ttt_accept_"):
            game_id = int(data.split("_")[2])
            await query.edit_message_text("✅ Ты принял вызов! Игра начинается...")
        elif data.startswith("ttt_decline_"):
            await query.edit_message_text("❌ Ты отклонил вызов")
        
        # КНБ
        elif data.startswith("rps_"):
            user_choice = data.split("_")[1]
            bot_choice = random.choice(["rock", "scissors", "paper"])
            
            choices = {"rock": "🪨 Камень", "scissors": "✂️ Ножницы", "paper": "📄 Бумага"}
            
            result_map = {
                ("rock", "scissors"): "win", ("rock", "paper"): "lose",
                ("scissors", "paper"): "win", ("scissors", "rock"): "lose",
                ("paper", "rock"): "win", ("paper", "scissors"): "lose"
            }
            
            if user_choice == bot_choice:
                result = "draw"
                db.cursor.execute("UPDATE users SET rps_draws = rps_draws + 1 WHERE platform = ? AND platform_id = ?", ('tg', str(update.effective_user.id)))
                text = f"{choices[user_choice]} vs {choices[bot_choice]}\n\n🤝 **Ничья!**"
            else:
                result = result_map.get((user_choice, bot_choice), "lose")
                if result == "win":
                    db.cursor.execute("UPDATE users SET rps_wins = rps_wins + 1 WHERE platform = ? AND platform_id = ?", ('tg', str(update.effective_user.id)))
                    text = f"{choices[user_choice]} vs {choices[bot_choice]}\n\n🎉 **Ты выиграл!**"
                else:
                    db.cursor.execute("UPDATE users SET rps_losses = rps_losses + 1 WHERE platform = ? AND platform_id = ?", ('tg', str(update.effective_user.id)))
                    text = f"{choices[user_choice]} vs {choices[bot_choice]}\n\n😢 **Ты проиграл!**"
            
            db.conn.commit()
            
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="games")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
        # Навигация
        elif data == "menu_back":
            keyboard = [
                [InlineKeyboardButton("👤 Профиль", callback_data="profile"),
                 InlineKeyboardButton("👾 Босс", callback_data="boss")],
                [InlineKeyboardButton("💰 Магазин", callback_data="shop"),
                 InlineKeyboardButton("💎 Привилегии", callback_data="donate")],
                [InlineKeyboardButton("📊 Топ", callback_data="top"),
                 InlineKeyboardButton("👥 Онлайн", callback_data="players")],
                [InlineKeyboardButton("🛡️ Модерация", callback_data="moderation"),
                 InlineKeyboardButton("🎮 Игры", callback_data="games")],
                [InlineKeyboardButton("📚 Команды", callback_data="help"),
                 InlineKeyboardButton("📖 Правила", callback_data="rules")],
                [InlineKeyboardButton("📌 Закладки", callback_data="bookmarks_menu"),
                 InlineKeyboardButton("🏅 Награды", callback_data="awards_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "🎮 **ГЛАВНОЕ МЕНЮ**\n\nВыберите раздел:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        elif data == "games_menu":
            keyboard = [
                [InlineKeyboardButton("💣 Русская рулетка", callback_data="rr"),
                 InlineKeyboardButton("⭕ Крестики-нолики 3D", callback_data="ttt")],
                [InlineKeyboardButton("🔪 Мафия", callback_data="mafia"),
                 InlineKeyboardButton("💥 Сапёр", callback_data="minesweeper")],
                [InlineKeyboardButton("✊ КНБ", callback_data="rps"),
                 InlineKeyboardButton("🔙 Назад", callback_data="menu_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "🎮 **ИГРЫ**\n\nВыберите игру:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        elif data == "noop":
            pass
        else:
            await query.edit_message_text(
                "❌ Неизвестная команда",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="menu_back")]])
            )
    
    # ===================== VK ОБРАБОТЧИКИ =====================
    def setup_vk_handlers(self):
        """Настройка обработчиков для VK"""
        if not VKBOTTLE_AVAILABLE or not self.vk_bot:
            return
        
        @self.vk_bot.on.message()
        async def vk_message_handler(message: Message):
            await self.vk_handle_message(message)
        
        logger.info("✅ VK обработчики зарегистрированы")
    
    async def vk_handle_message(self, message: Message):
        """Обработка сообщений VK"""
        # Базовая заглушка для VK
        if message.text and message.text.startswith('/start'):
            await message.reply("👋 Привет! Я бот Спектр. Полная поддержка VK будет добавлена позже.")
    
    # ===================== ЗАПУСК =====================
    async def run(self):
        """Запуск ботов"""
        if self.tg_application:
            await self.tg_application.initialize()
            await self.tg_application.start()
            await self.tg_application.updater.start_polling()
            logger.info("🚀 Telegram бот запущен!")
        
        if self.vk_bot and VKBOTTLE_AVAILABLE:
            asyncio.create_task(self.vk_bot.run_polling())
            logger.info("🚀 VK бот запущен!")
        
        while True:
            await asyncio.sleep(1)
    
    async def close(self):
        """Остановка ботов"""
        if self.tg_application:
            await self.tg_application.stop()
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
