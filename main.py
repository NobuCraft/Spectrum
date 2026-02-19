#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
СПЕКТР v8.0 ULTIMATE - ПОЛНАЯ ВЕРСИЯ
Мафия, игры, модерация, кнопки, AI аватар, реакции как валюта
"""

import os
import sys
import logging
import asyncio
import json
import random
import sqlite3
import datetime
import time
import hashlib
import re
import math
from typing import Optional, Dict, Any, List, Tuple, Union
from collections import defaultdict, deque
from enum import Enum
from io import BytesIO

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

import aiohttp

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, 
    ReplyKeyboardMarkup, KeyboardButton, Dice
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, MessageReactionHandler, filters, ContextTypes
)
from telegram.constants import ParseMode, DiceEmoji
from telegram.error import TelegramError

# ========== GROQ AI ==========
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    print("⚠️ Библиотека groq не установлена, AI будет отключен")

# ========== НАСТРОЙКИ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ==========
TOKEN = os.environ.get("BOT_TOKEN", "7884032312:AAF8A2J6Fp0u-eOHLqLuhV3TkXpFgOBxRw4")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
OWNER_ID = int(os.environ.get("OWNER_ID", "1732658530"))
OWNER_USERNAME = os.environ.get("OWNER_USERNAME", "@NobuCraft")

# ========== КОНСТАНТЫ ==========
BOT_NAME = "Спектр"
BOT_VERSION = "8.0 ULTIMATE"

# Настройки модерации
RANKS = {
    0: {"name": "Участник", "emoji": "👤"},
    1: {"name": "Младший модератор", "emoji": "🟢"},
    2: {"name": "Старший модератор", "emoji": "🔵"},
    3: {"name": "Младший администратор", "emoji": "🟣"},
    4: {"name": "Старший администратор", "emoji": "🔴"},
    5: {"name": "Создатель", "emoji": "👑"}
}

# Настройки игр
MAFIA_MIN_PLAYERS = 6
MAFIA_MAX_PLAYERS = 20
MAFIA_NIGHT_TIME = 60  # секунд
MAFIA_DAY_TIME = 120   # секунд

# Экономика
DAILY_COOLDOWN = 86400  # 24 часа
VIP_PRICE = 5000
PREMIUM_PRICE = 15000
VIP_DAYS = 30
PREMIUM_DAYS = 30

# Антиспам
SPAM_LIMIT = 5
SPAM_WINDOW = 3
SPAM_MUTE_TIME = 10

# AI
AI_COOLDOWN = 2

# Лимиты
MAX_NICK_LENGTH = 30
MAX_TITLE_LENGTH = 30
MAX_MOTTO_LENGTH = 100
MAX_BIO_LENGTH = 500

# Пути к видео (замени на file_id после первой загрузки в ТГ для скорости)
VIDEO_NIGHT_TO_DAY = "night_to_day.mp4" 
VIDEO_DAY_TO_NIGHT = "day_to_night.mp4"

# ========== ЛОГИРОВАНИЕ ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== GROQ AI КЛАСС ==========
class GroqAI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = None
        self.is_available = False
        self.contexts = defaultdict(lambda: deque(maxlen=15))
        self.user_last_ai = defaultdict(float)
        self.ai_cooldown = AI_COOLDOWN
        
        if GROQ_AVAILABLE and api_key:
            try:
                self.client = Groq(api_key=api_key)
                self.is_available = True
                logger.info("✅ Groq AI инициализирован")
            except Exception as e:
                logger.error(f"❌ Ошибка инициализации Groq: {e}")
                self.is_available = False
        
        self.system_prompt = """Ты — Спектр, дружелюбный и умный ИИ-ассистент в Telegram. 
Ты помогаешь пользователям, отвечаешь на вопросы, шутишь и поддерживаешь беседу.
Твой характер: дружелюбный, отзывчивый, с чувством юмора.
Отвечай кратко, по делу, используй эмодзи умеренно."""
    
    async def get_response(self, user_id: int, message: str, username: str = "Пользователь") -> Optional[str]:
        if not self.is_available:
            return None
            
        now = time.time()
        if now - self.user_last_ai[user_id] < self.ai_cooldown:
            return None
        self.user_last_ai[user_id] = now
        
        try:
            loop = asyncio.get_event_loop()
            
            history = list(self.contexts[user_id])
            messages = [
                {"role": "system", "content": self.system_prompt},
                *history,
                {"role": "user", "content": message}
            ]
            
            def sync_request():
                return self.client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages,
                    temperature=0.9,
                    max_tokens=300,
                    top_p=0.95
                )
            
            chat_completion = await loop.run_in_executor(None, sync_request)
            response = chat_completion.choices[0].message.content
            
            self.contexts[user_id].append({"role": "user", "content": message})
            self.contexts[user_id].append({"role": "assistant", "content": response})
            
            return response
            
        except Exception as e:
            logger.error(f"Groq error: {e}")
            return None
    
    async def close(self):
        pass

# Инициализация AI
ai = None
if GROQ_API_KEY and GROQ_AVAILABLE:
    try:
        ai = GroqAI(GROQ_API_KEY)
        logger.info("✅ Groq AI инициализирован")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации AI: {e}")
        ai = None
else:
    logger.warning("⚠️ Groq AI не подключен")

# ========== КЛАССЫ МАФИИ ==========
class MafiaRole(str, Enum):
    MAFIA = "😈 Мафия"
    COMMISSIONER = "👮 Комиссар"
    DOCTOR = "👨‍⚕️ Доктор"
    MANIAC = "🔪 Маньяк"
    BOSS = "👑 Босс"
    CITIZEN = "👤 Мирный"

class MafiaGame:
    def __init__(self, chat_id: int, game_id: str, creator_id: int):
        self.chat_id = chat_id
        self.game_id = game_id
        self.creator_id = creator_id
        self.status = "waiting"
        self.players: List[int] = []
        self.players_data: Dict[int, Dict[str, Any]] = {}
        self.roles: Dict[int, str] = {}
        self.alive: Dict[int, bool] = {}
        self.day = 1
        self.phase = "night"
        self.votes: Dict[int, int] = {}
        self.night_actions: Dict[str, Optional[int]] = {
            "mafia_kill": None,
            "doctor_save": None,
            "commissioner_check": None,
            "maniac_kill": None
        }
        self.message_id: Optional[int] = None
        self.start_time: Optional[datetime] = None
    
    def add_player(self, user_id: int, name: str, username: str = "") -> bool:
        if user_id in self.players:
            return False
        self.players.append(user_id)
        self.players_data[user_id] = {
            "name": name,
            "username": username,
            "confirmed": False
        }
        return True
    
    def remove_player(self, user_id: int) -> bool:
        if user_id not in self.players:
            return False
        self.players.remove(user_id)
        if user_id in self.players_data:
            del self.players_data[user_id]
        return True
    
    def confirm_player(self, user_id: int) -> bool:
        if user_id not in self.players_data:
            return False
        self.players_data[user_id]["confirmed"] = True
        return True
    
    def all_confirmed(self) -> bool:
        return all(p["confirmed"] for p in self.players_data.values()) and len(self.players) >= 6
    
    def assign_roles(self):
        num_players = len(self.players)
        
        if num_players <= 7:
            num_mafia = 2
        elif num_players <= 10:
            num_mafia = 3
        else:
            num_mafia = 4
        
        roles = [MafiaRole.MAFIA] * num_mafia
        roles.append(MafiaRole.COMMISSIONER)
        roles.append(MafiaRole.DOCTOR)
        
        remaining = num_players - len(roles)
        roles.extend([MafiaRole.CITIZEN] * remaining)
        
        random.shuffle(roles)
        
        for i, player_id in enumerate(self.players):
            self.roles[player_id] = roles[i]
            self.alive[player_id] = True
    
    def get_role_description(self, role: str) -> str:
        descriptions = {
            MafiaRole.MAFIA: "Ночью вы можете убивать мирных жителей.",
            MafiaRole.COMMISSIONER: "Ночью вы можете проверять игроков.",
            MafiaRole.DOCTOR: "Ночью вы можете спасать одного игрока.",
            MafiaRole.MANIAC: "Ночью вы можете убивать.",
            MafiaRole.BOSS: "Вы - глава мафии.",
            MafiaRole.CITIZEN: "У вас нет особых способностей."
        }
        return descriptions.get(role, "Ошибка")
    
    def get_alive_players(self) -> List[int]:
        return [pid for pid in self.players if self.alive.get(pid, False)]
    
    def check_win(self) -> Optional[str]:
        alive = self.get_alive_players()
        if not alive:
            return None
        
        mafia_count = 0
        citizen_count = 0
        
        for pid in alive:
            role = self.roles[pid]
            if role in [MafiaRole.MAFIA, MafiaRole.BOSS]:
                mafia_count += 1
            else:
                citizen_count += 1
        
        if mafia_count == 0:
            return "citizens"
        if mafia_count >= citizen_count:
            return "mafia"
        return None
    
    def process_night(self) -> Dict[str, Any]:
        killed = self.night_actions.get("mafia_kill")
        saved = self.night_actions.get("doctor_save")
        
        if saved and saved == killed:
            killed = None
        
        result = {
            "killed": killed,
        }
        
        self.night_actions = {
            "mafia_kill": None,
            "doctor_save": None,
            "commissioner_check": None,
            "maniac_kill": None
        }
        
        return result
    
    def process_voting(self) -> Optional[int]:
        if not self.votes:
            return None
        
        vote_count = {}
        for target in self.votes.values():
            vote_count[target] = vote_count.get(target, 0) + 1
        
        max_votes = max(vote_count.values())
        candidates = [pid for pid, votes in vote_count.items() if votes == max_votes]
        
        if len(candidates) == 1:
            executed = candidates[0]
            self.alive[executed] = False
            self.votes = {}
            return executed
        
        self.votes = {}
        return None

# ========== СТИЛИЗАЦИЯ ==========
class s:
    SEPARATOR = "─" * 28
    SEPARATOR_BOLD = "━" * 28
    
    @staticmethod
    def header(text): return f"┏━━ {text.upper()} ━━┓\n"
    
    @staticmethod
    def footer(): return "\n┗━━━━━━━━━━━━━━━┛"
    
    @staticmethod
    def stat(n, v, e="🔹"): return f"{e} **{n}:** `{v}`\n"
    
    @staticmethod
    def section(title: str, emoji: str = "📌") -> str:
        return f"\n{emoji} **{title}**\n"
    
    @staticmethod
    def item(text: str, emoji: str = "•") -> str:
        return f"{emoji} {text}\n"
    
    @staticmethod
    def success(text): return f"✅ **{text}**"
    
    @staticmethod
    def error(text): return f"❌ **{text}**"
    
    @staticmethod
    def warning(text): return f"⚠️ **{text}**"
    
    @staticmethod
    def info(text): return f"ℹ️ {text}"
    
    @staticmethod
    def code(text: str) -> str:
        return f"`{text}`"
    
    @staticmethod
    def progress(cur, tot, length=10):
        filled = int((cur / tot) * length) if tot > 0 else 0
        return f"|{'█' * filled}{'░' * (length - filled)}| {cur}/{tot}"

# ========== КЛАВИАТУРЫ ==========
class Keyboard:
    @staticmethod
    def make(buttons: List[List[Tuple[str, str]]]) -> InlineKeyboardMarkup:
        keyboard = []
        for row in buttons:
            kb_row = []
            for text, cb in row:
                kb_row.append(InlineKeyboardButton(text, callback_data=cb))
            keyboard.append(kb_row)
        return InlineKeyboardMarkup(keyboard)
    
    @classmethod
    def main_inline(cls):
        return cls.make([
            [("👤 ПРОФИЛЬ", "menu_profile"), ("📊 ТОП", "menu_top")],
            [("⚔️ БОСС", "boss_info"), ("🎰 КАЗИНО", "game_slots")],
            [("🔫 МАФИЯ", "menu_mafia"), ("🎁 DAILY", "menu_daily")],
            [("📈 МОЙ ГРАФИК", "menu_chart"), ("🤖 АВАТАР", "menu_avatar")]
        ])
    
    @classmethod
    def reply_main(cls):
        return ReplyKeyboardMarkup([
            [KeyboardButton("🏠 ГЛАВНОЕ"), KeyboardButton("👤 ПРОФИЛЬ")],
            [KeyboardButton("⚔️ БОСС"), KeyboardButton("🎰 СЛОТЫ")],
            [KeyboardButton("🔫 МАФИЯ"), KeyboardButton("📊 ТОП")],
            [KeyboardButton("❓ ПОМОЩЬ"), KeyboardButton("🎁 DAILY")]
        ], resize_keyboard=True)
    
    @classmethod
    def mafia_inline(cls):
        return cls.make([
            [("🎮 НАЧАТЬ ИГРУ", "mafia_start"), ("📋 ПРАВИЛА", "mafia_rules")],
            [("👥 РОЛИ", "mafia_roles"), ("🔙 НАЗАД", "menu_main")]
        ])
    
    @classmethod
    def mafia_confirm(cls, chat_id: int):
        return cls.make([[(f"✅ ПОДТВЕРДИТЬ", f"mafia_confirm_{chat_id}")]])
    
    @classmethod
    def duel_accept(cls, duel_id: int):
        return cls.make([
            [("✅ ПРИНЯТЬ", f"accept_duel_{duel_id}"),
             ("❌ ОТКЛОНИТЬ", f"reject_duel_{duel_id}")]
        ])
    
    @classmethod
    def back(cls):
        return cls.make([[("◀ НАЗАД", "menu_back")]])
    
    @classmethod
    def back_main(cls):
        return cls.make([
            [("◀ НАЗАД", "menu_back"), ("🏠 ГЛАВНАЯ", "menu_main")]
        ])

kb = Keyboard()

# ========== БАЗА ДАННЫХ ==========
class Database:
    def __init__(self):
        self.conn = sqlite3.connect("spectre_v8.db", check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self._init_db()

    def _init_db(self):
        # Пользователи
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            coins INTEGER DEFAULT 1000,
            energy INTEGER DEFAULT 100,
            reputation INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            exp INTEGER DEFAULT 0,
            messages_count INTEGER DEFAULT 0,
            commands_used INTEGER DEFAULT 0,
            boss_damage INTEGER DEFAULT 0,
            boss_kills INTEGER DEFAULT 0,
            duel_wins INTEGER DEFAULT 0,
            duel_losses INTEGER DEFAULT 0,
            duel_rating INTEGER DEFAULT 1000,
            mafia_games INTEGER DEFAULT 0,
            mafia_wins INTEGER DEFAULT 0,
            mafia_losses INTEGER DEFAULT 0,
            rps_wins INTEGER DEFAULT 0,
            rps_losses INTEGER DEFAULT 0,
            rps_draws INTEGER DEFAULT 0,
            casino_wins INTEGER DEFAULT 0,
            casino_losses INTEGER DEFAULT 0,
            dice_wins INTEGER DEFAULT 0,
            dice_losses INTEGER DEFAULT 0,
            rr_wins INTEGER DEFAULT 0,
            rr_losses INTEGER DEFAULT 0,
            slots_wins INTEGER DEFAULT 0,
            slots_losses INTEGER DEFAULT 0,
            nickname TEXT,
            title TEXT DEFAULT '',
            motto TEXT DEFAULT 'Нет девиза',
            bio TEXT DEFAULT '',
            gender TEXT DEFAULT 'не указан',
            city TEXT DEFAULT 'не указан',
            country TEXT DEFAULT 'не указана',
            birth_date TEXT,
            age INTEGER DEFAULT 0,
            rank INTEGER DEFAULT 0,
            rank_name TEXT DEFAULT 'Участник',
            warns INTEGER DEFAULT 0,
            warns_list TEXT DEFAULT '[]',
            mute_until TEXT,
            banned INTEGER DEFAULT 0,
            vip_until TEXT,
            premium_until TEXT,
            daily_streak INTEGER DEFAULT 0,
            last_daily TEXT,
            last_seen TEXT,
            registered TEXT DEFAULT CURRENT_TIMESTAMP,
            referrer_id INTEGER,
            inventory TEXT DEFAULT '[]',
            friends TEXT DEFAULT '[]',
            enemies TEXT DEFAULT '[]',
            spouse INTEGER DEFAULT 0,
            married_since TEXT,
            clan_id INTEGER DEFAULT 0,
            clan_role TEXT DEFAULT 'member'
        )''')
        
        # Сообщения
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            first_name TEXT,
            message_text TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            chat_id INTEGER,
            chat_title TEXT
        )''')
        
        # Логи
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            details TEXT,
            chat_id INTEGER,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Боссы
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS bosses (
            id INTEGER PRIMARY KEY,
            name TEXT,
            hp INTEGER,
            max_hp INTEGER,
            damage INTEGER DEFAULT 50,
            reward_coins INTEGER DEFAULT 1000,
            reward_exp INTEGER DEFAULT 100,
            is_alive INTEGER DEFAULT 1,
            level INTEGER DEFAULT 1
        )''')
        
        # Дуэли
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS duels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            challenger_id INTEGER,
            opponent_id INTEGER,
            bet INTEGER,
            status TEXT DEFAULT 'pending',
            winner_id INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Триггеры
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS triggers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            word TEXT,
            action TEXT,
            action_value TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Чёрный список
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS blacklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT UNIQUE,
            added_by INTEGER,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Настройки чатов
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS chat_settings (
            chat_id INTEGER PRIMARY KEY,
            welcome TEXT,
            rules TEXT,
            antiflood INTEGER DEFAULT 1,
            antispam INTEGER DEFAULT 1,
            antilink INTEGER DEFAULT 0,
            captcha INTEGER DEFAULT 0,
            lang TEXT DEFAULT 'ru'
        )''')
        
        # Кланы
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS clans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            owner_id INTEGER,
            level INTEGER DEFAULT 1,
            exp INTEGER DEFAULT 0,
            coins INTEGER DEFAULT 0,
            members INTEGER DEFAULT 1,
            rating INTEGER DEFAULT 1000,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS clan_members (
            clan_id INTEGER,
            user_id INTEGER UNIQUE,
            role TEXT DEFAULT 'member',
            joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (clan_id) REFERENCES clans(id),
            FOREIGN KEY (user_id) REFERENCES users(telegram_id)
        )''')
        
        # Создаем босса, если его нет
        self.cursor.execute("INSERT OR IGNORE INTO bosses VALUES (1, '🔥 Древний Дракон', 5000, 5000, 50, 1000, 100, 1, 1)")
        self.conn.commit()

    def get_user(self, uid: int, name: str = "Игрок", uname: str = "") -> Dict:
        self.cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (uid,))
        row = self.cursor.fetchone()
        if not row:
            role = 'owner' if uid == OWNER_ID else 'user'
            rank = 5 if uid == OWNER_ID else 0
            rank_name = RANKS[rank]["name"]
            
            self.cursor.execute(
                "INSERT INTO users (telegram_id, first_name, username, role, rank, rank_name) VALUES (?, ?, ?, ?, ?, ?)",
                (uid, name, uname, role, rank, rank_name)
            )
            self.conn.commit()
            return self.get_user(uid)
        
        cols = [column[0] for column in self.cursor.description]
        return dict(zip(cols, row))

    def update_user(self, uid: int, **kwargs):
        for key, value in kwargs.items():
            if isinstance(value, str) and value.startswith(("+", "-")):
                self.cursor.execute(f"UPDATE users SET {key} = {key} {value} WHERE telegram_id = ?", (uid,))
            else:
                self.cursor.execute(f"UPDATE users SET {key} = ? WHERE telegram_id = ?", (value, uid))
        self.conn.commit()
    
    def add_coins(self, uid: int, amount: int) -> int:
        self.cursor.execute("UPDATE users SET coins = coins + ? WHERE telegram_id = ?", (amount, uid))
        self.conn.commit()
        self.cursor.execute("SELECT coins FROM users WHERE telegram_id = ?", (uid,))
        return self.cursor.fetchone()[0]
    
    def add_exp(self, uid: int, amount: int) -> bool:
        self.cursor.execute("UPDATE users SET exp = exp + ? WHERE telegram_id = ?", (amount, uid))
        self.cursor.execute("SELECT exp, level FROM users WHERE telegram_id = ?", (uid,))
        row = self.cursor.fetchone()
        exp, level = row[0], row[1]
        if exp >= level * 100:
            self.cursor.execute("UPDATE users SET level = level + 1, exp = exp - ? WHERE telegram_id = ?", 
                              (level * 100, uid))
            self.conn.commit()
            return True
        self.conn.commit()
        return False
    
    def add_energy(self, uid: int, amount: int) -> int:
        self.cursor.execute("UPDATE users SET energy = MIN(100, energy + ?) WHERE telegram_id = ?", (amount, uid))
        self.conn.commit()
        self.cursor.execute("SELECT energy FROM users WHERE telegram_id = ?", (uid,))
        return self.cursor.fetchone()[0]
    
    def heal(self, uid: int, amount: int) -> int:
        self.cursor.execute("UPDATE users SET energy = MIN(100, energy + ?) WHERE telegram_id = ?", (amount, uid))
        self.conn.commit()
        self.cursor.execute("SELECT energy FROM users WHERE telegram_id = ?", (uid,))
        return self.cursor.fetchone()[0]
    
    def is_vip(self, uid: int) -> bool:
        self.cursor.execute("SELECT vip_until FROM users WHERE telegram_id = ?", (uid,))
        row = self.cursor.fetchone()
        if row and row[0]:
            return datetime.fromisoformat(row[0]) > datetime.now()
        return False
    
    def is_premium(self, uid: int) -> bool:
        self.cursor.execute("SELECT premium_until FROM users WHERE telegram_id = ?", (uid,))
        row = self.cursor.fetchone()
        if row and row[0]:
            return datetime.fromisoformat(row[0]) > datetime.now()
        return False
    
    def set_vip(self, uid: int, days: int) -> datetime:
        until = datetime.now() + timedelta(days=days)
        self.cursor.execute("UPDATE users SET vip_until = ? WHERE telegram_id = ?",
                          (until.isoformat(), uid))
        self.conn.commit()
        return until
    
    def set_premium(self, uid: int, days: int) -> datetime:
        until = datetime.now() + timedelta(days=days)
        self.cursor.execute("UPDATE users SET premium_until = ? WHERE telegram_id = ?",
                          (until.isoformat(), uid))
        self.conn.commit()
        return until
    
    def add_daily_streak(self, uid: int) -> int:
        today = datetime.now().date()
        self.cursor.execute("SELECT last_daily, daily_streak FROM users WHERE telegram_id = ?", (uid,))
        row = self.cursor.fetchone()
        
        if row and row[0]:
            last = datetime.fromisoformat(row[0]).date()
            if last == today - timedelta(days=1):
                streak = row[1] + 1
            elif last == today:
                return row[1]
            else:
                streak = 1
        else:
            streak = 1
        
        self.cursor.execute("UPDATE users SET daily_streak = ?, last_daily = ? WHERE telegram_id = ?",
                          (streak, datetime.now().isoformat(), uid))
        self.conn.commit()
        return streak
    
    def get_top(self, field: str, limit: int = 10) -> List[Tuple]:
        self.cursor.execute(f"SELECT first_name, nickname, {field} FROM users ORDER BY {field} DESC LIMIT ?", (limit,))
        return self.cursor.fetchall()
    
    def get_boss(self, boss_id: int):
        self.cursor.execute("SELECT * FROM bosses WHERE id = ?", (boss_id,))
        row = self.cursor.fetchone()
        return {"id": row[0], "name": row[1], "hp": row[2], "max_hp": row[3], 
                "damage": row[4], "reward_coins": row[5], "reward_exp": row[6], 
                "alive": row[7], "level": row[8]} if row else None
    
    def damage_boss(self, boss_id: int, damage: int) -> bool:
        self.cursor.execute("UPDATE bosses SET hp = hp - ? WHERE id = ?", (damage, boss_id))
        self.cursor.execute("SELECT hp FROM bosses WHERE id = ?", (boss_id,))
        hp = self.cursor.fetchone()[0]
        if hp <= 0:
            self.cursor.execute("UPDATE bosses SET is_alive = 0 WHERE id = ?", (boss_id,))
            self.conn.commit()
            return True
        self.conn.commit()
        return False
    
    def respawn_boss(self, boss_id: int):
        self.cursor.execute("SELECT max_hp FROM bosses WHERE id = ?", (boss_id,))
        max_hp = self.cursor.fetchone()[0]
        self.cursor.execute("UPDATE bosses SET hp = ?, is_alive = 1 WHERE id = ?", (max_hp, boss_id))
        self.conn.commit()
    
    def add_to_inventory(self, uid: int, item: str):
        self.cursor.execute("SELECT inventory FROM users WHERE telegram_id = ?", (uid,))
        inv = json.loads(self.cursor.fetchone()[0])
        inv.append(item)
        self.cursor.execute("UPDATE users SET inventory = ? WHERE telegram_id = ?", (json.dumps(inv), uid))
        self.conn.commit()
    
    def log_action(self, uid: int, action: str, details: str = "", chat_id: int = None):
        self.cursor.execute('''
            INSERT INTO logs (user_id, action, details, chat_id, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (uid, action, details, chat_id, datetime.now().isoformat()))
        self.conn.commit()
    
    def close(self):
        self.conn.close()

db = Database()

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def get_rank_emoji(rank: int) -> str:
    return RANKS.get(rank, RANKS[0])["emoji"]

def get_rank_name(rank: int) -> str:
    return RANKS.get(rank, RANKS[0])["name"]

def extract_user_id(text: str) -> Optional[int]:
    match = re.search(r'@(\w+)', text)
    if match:
        username = match.group(1)
        user = db.cursor.execute("SELECT telegram_id FROM users WHERE username = ?", (username,)).fetchone()
        if user:
            return user[0]
    
    match = re.search(r'tg://user\?id=(\d+)', text)
    if match:
        return int(match.group(1))
    
    match = re.search(r'(\d+)', text)
    if match:
        return int(match.group(1))
    
    return None

def parse_time(time_str: str) -> Optional[int]:
    match = re.match(r'(\d+)([мчд])', time_str)
    if not match:
        return None
    
    amount = int(match.group(1))
    unit = match.group(2)
    
    if unit == 'м':
        return amount
    elif unit == 'ч':
        return amount * 60
    elif unit == 'д':
        return amount * 1440
    
    return None

# ========== ОСНОВНЫЕ КОМАНДЫ ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    user_data = db.get_user(u.id, u.first_name, u.username)
    
    # Обработка рефералов
    if context.args and context.args[0].isdigit():
        referrer_id = int(context.args[0])
        if referrer_id != u.id:
            db.add_coins(referrer_id, 500)
            db.update_user(u.id, referrer_id=referrer_id)
            try:
                await context.bot.send_message(
                    referrer_id,
                    s.success(f"🎉 По вашей ссылке зарегистрировался {u.first_name}! +500 💰")
                )
            except:
                pass
    
    ai_status = "✅ Подключен" if ai and ai.is_available else "❌ Не подключен"
    
    txt = (
        s.header("СПЕКТР v8.0") + 
        f"👋 **Привет, {u.first_name}!**\n"
        f"Я готов к работе.\n\n"
        f"{s.section('ТВОЙ ПРОФИЛЬ')}"
        f"{s.stat('Монеты', user_data['coins'])}"
        f"{s.stat('Уровень', user_data['level'])}"
        f"{s.stat('Ранг', get_rank_emoji(user_data['rank']) + ' ' + user_data['rank_name'])}"
        f"{s.stat('Энергия', f'{user_data["energy"]}/100')}\n"
        f"{s.section('ЧТО Я УМЕЮ')}"
        f"{s.item('🤖 AI: ' + ai_status)}"
        f"{s.item('🔫 Мафия с перемоткой времени')}"
        f"{s.item('⚔️ Битва с боссом и артефакты')}"
        f"{s.item('🎰 Казино через Dice')}"
        f"{s.item('❤️ Реакции как валюта')}"
        f"{s.item('⚙️ Модерация (5 рангов)')}"
        f"{s.item('💰 Экономика, VIP')}"
    )
    
    await update.message.reply_text(
        txt,
        reply_markup=kb.reply_main(),
        parse_mode=ParseMode.MARKDOWN
    )
    await update.message.reply_text(
        "🔹 **Или выбери раздел:**",
        reply_markup=kb.main_inline(),
        parse_mode=ParseMode.MARKDOWN
    )
    
    db.log_action(u.id, 'start')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (
        s.header("СПРАВКА") + "\n"
        f"{s.section('📌 ОСНОВНЫЕ')}"
        f"{s.cmd('start', 'начать')}\n"
        f"{s.cmd('menu', 'главное меню')}\n"
        f"{s.cmd('profile', 'профиль')}\n"
        f"{s.cmd('id', 'узнать свой ID')}\n\n"
        
        f"{s.section('🤖 ИСКУССТВЕННЫЙ ИНТЕЛЛЕКТ')}"
        f"{s.cmd('Спектр [вопрос]', 'задать вопрос AI (в группах)')}\n"
        f"{s.cmd('[любое сообщение]', 'AI отвечает в личке')}\n"
        f"{s.cmd('avatar', 'сгенерировать аватар')}\n\n"
        
        f"{s.section('⚙️ МОДЕРАЦИЯ')}"
        f"{s.cmd('+Модер @user', '1 ранг')}\n"
        f"{s.cmd('варн @user [причина]', 'предупреждение')}\n"
        f"{s.cmd('мут @user 30м [причина]', 'заглушить')}\n"
        f"{s.cmd('бан @user [причина]', 'заблокировать')}\n"
        f"{s.cmd('админы', 'список администрации')}\n\n"
        
        f"{s.section('💰 ЭКОНОМИКА')}"
        f"{s.cmd('balance', 'баланс')}\n"
        f"{s.cmd('daily', 'ежедневный бонус')}\n"
        f"{s.cmd('shop', 'магазин')}\n"
        f"{s.cmd('vip', 'VIP статус')}\n"
        f"{s.cmd('premium', 'PREMIUM статус')}\n\n"
        
        f"{s.section('🎮 ИГРЫ')}"
        f"{s.cmd('games', 'меню игр')}\n"
        f"{s.cmd('slots', 'игровые автоматы')}\n"
        f"{s.cmd('rr [ставка]', 'русская рулетка')}\n"
        f"{s.cmd('dicebet [ставка]', 'кости')}\n"
        f"{s.cmd('rps', 'камень-ножницы-бумага')}\n"
        f"{s.cmd('duel @user [ставка]', 'вызвать на дуэль')}\n\n"
        
        f"{s.section('👾 БОССЫ')}"
        f"{s.cmd('bosses', 'список боссов')}\n"
        f"{s.cmd('boss [ID]', 'атаковать босса')}\n"
        f"{s.cmd('regen', 'восстановить энергию')}\n\n"
        
        f"{s.section('🎭 МАФИЯ')}"
        f"{s.cmd('mafia', 'меню мафии')}\n"
        f"{s.cmd('mafiastart', 'начать игру')}\n"
        f"{s.cmd('mafiajoin', 'присоединиться')}\n\n"
        
        f"{s.section('📊 ГРАФИКИ')}"
        f"{s.cmd('chart', 'мой график активности')}\n"
        f"{s.cmd('profile', 'профиль со статистикой')}\n\n"
        
        f"👑 **Владелец:** {OWNER_USERNAME}"
    )
    
    await update.message.reply_text(txt, reply_markup=kb.back(), parse_mode=ParseMode.MARKDOWN)

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        s.header("ГЛАВНОЕ МЕНЮ") + "\nВыберите раздел:",
        reply_markup=kb.main_inline(),
        parse_mode=ParseMode.MARKDOWN
    )

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    user_data = db.get_user(u.id)
    
    display_name = user_data.get('nickname') or u.first_name
    title = user_data.get('title', '')
    motto = user_data.get('motto', 'Нет девиза')
    bio = user_data.get('bio', '')
    
    vip_status = "✅ VIP" if db.is_vip(u.id) else "❌"
    premium_status = "✅ PREMIUM" if db.is_premium(u.id) else "❌"
    
    exp_needed = user_data['level'] * 100
    exp_progress = s.progress(user_data['exp'], exp_needed)
    
    warns = "🔴" * user_data['warns'] + "⚪" * (3 - user_data['warns'])
    
    # Инвентарь
    inventory = json.loads(user_data.get('inventory', '[]'))
    inv_text = ", ".join(inventory[:5]) if inventory else "пусто"
    
    # Друзья и враги
    friends = json.loads(user_data.get('friends', '[]'))
    enemies = json.loads(user_data.get('enemies', '[]'))
    
    registered = datetime.fromisoformat(user_data['registered']) if user_data.get('registered') else datetime.now()
    days_in_chat = (datetime.now() - registered).days
    
    text = (
        f"# Спектр | Профиль\n\n"
        f"👤 **{display_name}** {title}\n"
        f"_{motto}_\n"
        f"{bio}\n\n"
        f"📊 **Характеристики**\n"
        f"• Ранг: {get_rank_emoji(user_data['rank'])} {user_data['rank_name']}\n"
        f"• Уровень: {user_data['level']} ({exp_progress})\n"
        f"• Монеты: {user_data['coins']:,} 💰\n"
        f"• Энергия: {user_data['energy']}/100 ⚡\n\n"
        
        f"📈 **Статистика**\n"
        f"• Сообщений: {user_data['messages_count']:,} 💬\n"
        f"• Репутация: {user_data['reputation']} ⭐\n"
        f"• Предупреждения: {warns}\n"
        f"• Боссов убито: {user_data['boss_kills']} 👾\n"
        f"• Дуэлей: {user_data['duel_wins']}/{user_data['duel_losses']}\n\n"
        
        f"💎 **Статус**\n"
        f"• VIP: {vip_status}\n"
        f"• PREMIUM: {premium_status}\n"
        f"• В чате: {days_in_chat} дней\n"
        f"• ID: `{u.id}`\n\n"
        
        f"📦 **Инвентарь:** {inv_text}"
    )
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# ===== ГРАФИК АКТИВНОСТИ =====

async def chart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    await update.message.chat.send_action(action="upload_photo")
    
    # Получаем статистику сообщений за последние 30 дней
    db.cursor.execute('''
        SELECT DATE(timestamp) as date, COUNT(*) as count
        FROM messages
        WHERE user_id = ? AND timestamp >= DATE('now', '-30 days')
        GROUP BY DATE(timestamp)
        ORDER BY date
    ''', (user.id,))
    
    data = db.cursor.fetchall()
    
    if not data or len(data) < 2:
        await update.message.reply_text(s.info("📊 Недостаточно данных для графика. Напиши ещё сообщений!"))
        return
    
    try:
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(10, 5))
        fig.patch.set_facecolor('#1a1a1a')
        ax.set_facecolor('#2a2a2a')
        
        dates = [row[0] for row in data]
        counts = [row[1] for row in data]
        
        ax.plot(dates, counts, color='#ff9900', linewidth=2.5, marker='o', markersize=4)
        ax.fill_between(dates, counts, alpha=0.3, color='#ff9900')
        
        ax.set_xlabel('Дата', color='white', fontsize=10)
        ax.set_ylabel('Сообщений', color='white', fontsize=10)
        ax.tick_params(colors='white', labelsize=8)
        ax.grid(True, alpha=0.2, color='gray', linestyle='--', linewidth=0.5)
        
        for spine in ax.spines.values():
            spine.set_color('#444444')
        
        ax.set_title(f'📊 Активность за 30 дней', color='white', fontsize=14, fontweight='bold', pad=20)
        
        total = sum(counts)
        avg = total / 30
        max_count = max(counts)
        
        stats_text = f"Всего: {total} | В день: {avg:.1f} | Пик: {max_count}"
        ax.text(0.5, 0.95, stats_text, transform=ax.transAxes,
                fontsize=9, ha='center', color='white',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='#333333', edgecolor='#ff9900'))
        
        plt.tight_layout()
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight',
                   facecolor=fig.get_facecolor())
        buf.seek(0)
        plt.close(fig)
        
        await update.message.reply_photo(
            photo=buf,
            caption="📈 Твоя активность за последние 30 дней"
        )
        
    except Exception as e:
        logger.error(f"Ошибка графика: {e}")
        await update.message.reply_text(s.error("❌ Не удалось создать график"))

# ===== РЕАКЦИИ КАК ВАЛЮТА =====

async def handle_reactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        react = update.message_reaction
        uid = react.user.id
        
        # Проверяем, есть ли новые реакции
        if react.new_reaction:
            # Начисляем репутацию и энергию за реакцию
            db.update_user(uid, reputation="+1", energy="+5")
            
            # Каждая 10-я реакция дает монету
            db.cursor.execute("SELECT reputation FROM users WHERE telegram_id = ?", (uid,))
            rep = db.cursor.fetchone()[0]
            if rep % 10 == 0:
                db.add_coins(uid, 50)
                try:
                    await context.bot.send_message(
                        uid,
                        s.success(f"🎉 За 10 реакций получено +50 монет!")
                    )
                except:
                    pass
    except Exception as e:
        logger.error(f"Ошибка обработки реакции: {e}")

# ===== АНИМИРОВАННОЕ КАЗИНО (DICE) =====

async def play_slots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = db.get_user(uid)
    
    # Проверка ставки
    bet = 50
    if context.args:
        try:
            bet = int(context.args[0])
            if bet < 10:
                bet = 10
            if bet > 1000:
                bet = 1000
        except:
            pass
    
    if user['coins'] < bet:
        return await update.message.reply_text(s.error(f"❌ Недостаточно монет! Нужно {bet}"))

    msg = await update.message.reply_dice(emoji=DiceEmoji.SLOT_MACHINE)
    val = msg.dice.value
    
    # Выигрышные комбинации в ТГ для слотов: 1, 22, 43, 64 (три в ряд)
    winners = [1, 22, 43, 64]
    
    await asyncio.sleep(3.5)  # Ждем пока анимация остановится
    
    if val in winners:
        win_amount = bet * 5
        db.add_coins(uid, win_amount)
        db.update_user(uid, slots_wins=f"+1")
        await update.message.reply_text(
            f"{s.success('🎰 ДЖЕКПОТ!')}\n"
            f"Выигрыш: +{win_amount} монет!",
            parse_mode=ParseMode.MARKDOWN
        )
    elif val % 10 == 0:
        # Частичный выигрыш
        win_amount = bet * 2
        db.add_coins(uid, win_amount)
        db.update_user(uid, slots_wins=f"+1")
        await update.message.reply_text(
            f"{s.success('🎰 ВЫИГРЫШ!')}\n"
            f"Выигрыш: +{win_amount} монет!",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        db.add_coins(uid, -bet)
        db.update_user(uid, slots_losses=f"+1")
        await update.message.reply_text(
            s.info(f"🎰 Мимо. -{bet} монет. Попробуй еще!"),
            parse_mode=ParseMode.MARKDOWN
        )

async def play_dice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = db.get_user(uid)
    
    bet = 20
    if context.args:
        try:
            bet = int(context.args[0])
            if bet < 5:
                bet = 5
            if bet > 500:
                bet = 500
        except:
            pass
    
    if user['coins'] < bet:
        return await update.message.reply_text(s.error(f"❌ Недостаточно монет! Нужно {bet}"))

    msg = await update.message.reply_dice(emoji=DiceEmoji.DICE)
    val = msg.dice.value
    
    await asyncio.sleep(3)
    
    if val == 6:
        win_amount = bet * 3
        db.add_coins(uid, win_amount)
        db.update_user(uid, dice_wins=f"+1")
        await update.message.reply_text(
            f"{s.success('🎲 6! ДЖЕКПОТ!')}\n"
            f"Выигрыш: +{win_amount} монет!",
            parse_mode=ParseMode.MARKDOWN
        )
    elif val >= 4:
        win_amount = bet * 2
        db.add_coins(uid, win_amount)
        db.update_user(uid, dice_wins=f"+1")
        await update.message.reply_text(
            f"{s.success(f'🎲 {val}! ВЫИГРЫШ!')}\n"
            f"Выигрыш: +{win_amount} монет!",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        db.add_coins(uid, -bet)
        db.update_user(uid, dice_losses=f"+1")
        await update.message.reply_text(
            s.info(f"🎲 {val}. -{bet} монет."),
            parse_mode=ParseMode.MARKDOWN
        )

# ===== БИТВА С БОССОМ =====

async def bosses_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    boss = db.get_boss(1)
    
    if not boss['alive']:
        db.respawn_boss(1)
        boss = db.get_boss(1)
    
    text = (
        s.header("👾 БОССЫ") + "\n"
        f"**{boss['name']}** (ур.{boss['level']})\n"
        f"{s.item(f'❤️ {s.progress(boss["hp"], boss["max_hp"], 15)}')}\n"
        f"{s.item(f'⚔️ Урон: {boss["damage"]}')}\n"
        f"{s.item(f'💰 Награда: {boss["reward_coins"]} 💰, ✨ {boss["reward_exp"]}')}\n\n"
    )
    
    user_data = db.get_user(update.effective_user.id)
    text += (
        f"{s.section('ТВОИ ПОКАЗАТЕЛИ')}\n"
        f"{s.stat('❤️ Здоровье', f'{user_data["energy"]}/100')}\n"
        f"{s.stat('⚔️ Урон', user_data.get("boss_damage", 10))}\n"
        f"{s.stat('👾 Боссов убито', user_data["boss_kills"])}\n\n"
        f"{s.section('КОМАНДЫ')}\n"
        f"{s.cmd('boss', 'атаковать босса')}\n"
        f"{s.cmd('regen', 'восстановить энергию')}"
    )
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def boss_fight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = db.get_user(uid)
    boss = db.get_boss(1)
    
    if not boss:
        return await update.message.reply_text(s.error("❌ Босс не найден"))
    
    if not boss['alive']:
        db.respawn_boss(1)
        boss = db.get_boss(1)
    
    if user['energy'] < 10:
        return await update.message.reply_text(s.error("❌ Недостаточно энергии. Используй /regen"))
    
    # Тратим энергию
    db.update_user(uid, energy="-10")
    
    # Расчет урона
    base_damage = user.get("boss_damage", 10) + random.randint(5, 20)
    
    if db.is_vip(uid):
        base_damage = int(base_damage * 1.2)
    if db.is_premium(uid):
        base_damage = int(base_damage * 1.3)
    
    crit = random.randint(1, 100) <= 10  # 10% шанс крита
    if crit:
        player_damage = base_damage * 2
        crit_text = "💥 КРИТИЧЕСКИЙ УДАР! "
    else:
        player_damage = base_damage
        crit_text = ""
    
    # Урон босса
    boss_damage = boss['damage'] + random.randint(-10, 10)
    energy_taken = max(1, boss_damage)
    
    killed = db.damage_boss(1, player_damage)
    db.update_user(uid, energy=f"-{energy_taken}", boss_damage=f"+{player_damage}")
    
    text = s.header("⚔️ БИТВА С БОССОМ") + "\n\n"
    text += f"{s.item(f'{crit_text}Твой урон: {player_damage}')}\n"
    text += f"{s.item(f'Урон босса: {energy_taken}')}\n\n"
    
    if killed:
        # Босс убит
        reward_coins = boss['reward_coins']
        reward_exp = boss['reward_exp']
        
        if db.is_vip(uid):
            reward_coins = int(reward_coins * 1.5)
            reward_exp = int(reward_exp * 1.5)
        if db.is_premium(uid):
            reward_coins = int(reward_coins * 2)
            reward_exp = int(reward_exp * 2)
        
        db.add_coins(uid, reward_coins)
        leveled_up = db.add_exp(uid, reward_exp)
        db.update_user(uid, boss_kills=f"+1")
        
        # Артефакт (1 из 5)
        artifact = random.choice([
            "💎 Око Бездны",
            "🗡 Клинок Спектра", 
            "🛡 Плащ Ночи",
            "👑 Корона Тьмы",
            "⚡ Перчатка Грома"
        ])
        db.add_to_inventory(uid, artifact)
        
        text += f"{s.success('ПОБЕДА!')}\n"
        text += f"{s.item(f'💰 Монеты: +{reward_coins}')}\n"
        text += f"{s.item(f'✨ Опыт: +{reward_exp}')}\n"
        text += f"{s.item(f'🏆 Артефакт: {artifact}')}\n"
        
        if leveled_up:
            text += f"{s.success(f'✨ УРОВЕНЬ ПОВЫШЕН!')}\n"
        
        # Респаун босса
        db.respawn_boss(1)
    else:
        boss_info = db.get_boss(1)
        text += f"{s.warning('Босс ещё жив!')}\n"
        text += f"❤️ Осталось: {boss_info['hp']} здоровья\n"
    
    if user['energy'] <= energy_taken:
        db.update_user(uid, energy="+50")
        text += f"\n{s.info('Ты погиб и воскрешён с 50❤️')}"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    db.log_action(uid, 'boss_fight', f"Урон {player_damage}")

async def regen_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = db.get_user(uid)
    
    cost = 50
    if user['coins'] < cost:
        return await update.message.reply_text(s.error(f"❌ Недостаточно монет. Нужно {cost} 💰"))
    
    db.add_coins(uid, -cost)
    db.update_user(uid, energy="+30")
    
    await update.message.reply_text(
        f"{s.success('✅ Регенерация завершена!')}\n\n"
        f"{s.item('⚡ Энергия +30')}\n"
        f"{s.item(f'💰 Потрачено: {cost}')}",
        parse_mode=ParseMode.MARKDOWN
    )

# ===== ДУЭЛИ =====

async def duel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = db.get_user(uid)
    
    if len(context.args) < 2:
        return await update.message.reply_text(s.error("❌ Использование: /duel @user ставка"))
    
    username = context.args[0].replace('@', '')
    try:
        bet = int(context.args[1])
    except:
        return await update.message.reply_text(s.error("❌ Ставка должна быть числом"))
    
    if bet <= 0:
        return await update.message.reply_text(s.error("❌ Ставка должна быть больше 0"))
    
    if bet > user['coins']:
        return await update.message.reply_text(s.error(f"❌ Недостаточно монет. Баланс: {user['coins']} 💰"))
    
    # Получаем противника
    db.cursor.execute("SELECT telegram_id FROM users WHERE username = ?", (username,))
    target_row = db.cursor.fetchone()
    
    if not target_row:
        return await update.message.reply_text(s.error("❌ Пользователь не найден"))
    
    target_id = target_row[0]
    
    if target_id == uid:
        return await update.message.reply_text(s.error("❌ Нельзя вызвать на дуэль самого себя"))
    
    # Проверяем, нет ли уже активной дуэли
    db.cursor.execute("SELECT id FROM duels WHERE (challenger_id = ? OR opponent_id = ?) AND status = 'pending'",
                     (uid, uid))
    if db.cursor.fetchone():
        return await update.message.reply_text(s.error("❌ У тебя уже есть активная дуэль"))
    
    duel_id = db.cursor.execute(
        "INSERT INTO duels (challenger_id, opponent_id, bet) VALUES (?, ?, ?) RETURNING id",
        (uid, target_id, bet)
    ).fetchone()[0]
    db.conn.commit()
    
    # Блокируем ставку
    db.add_coins(uid, -bet)
    
    target_data = db.get_user(target_id)
    target_name = target_data.get('nickname') or target_data['first_name']
    
    await update.message.reply_text(
        f"# Спектр | Дуэль\n\n"
        f"⚔️ **{user['first_name']}** VS **{target_name}** ⚔️\n"
        f"💰 Ставка: **{bet}** іс\n\n"
        f"{user['first_name']} вызывает на дуэль!\n\n"
        f"{target_name}, прими вызов:",
        reply_markup=kb.duel_accept(duel_id),
        parse_mode=ParseMode.MARKDOWN
    )

async def duel_rating_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.cursor.execute("SELECT first_name, nickname, duel_rating FROM users WHERE duel_rating > 0 ORDER BY duel_rating DESC LIMIT 10")
    top = db.cursor.fetchall()
    
    if not top:
        return await update.message.reply_text(s.info("Рейтинг пуст"))
    
    text = s.header("⚔️ ТОП ДУЭЛЯНТОВ") + "\n\n"
    for i, row in enumerate(top, 1):
        name = row[1] or row[0]
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        text += f"{medal} **{name}** — {row[2]} очков\n"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# ===== ЕЖЕДНЕВНЫЙ БОНУС =====

async def daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = db.get_user(uid)
    
    if user.get('last_daily'):
        last = datetime.fromisoformat(user['last_daily'])
        if (datetime.now() - last).seconds < DAILY_COOLDOWN:
            remain = DAILY_COOLDOWN - (datetime.now() - last).seconds
            hours = remain // 3600
            minutes = (remain % 3600) // 60
            return await update.message.reply_text(s.warning(f"⏳ Бонус через {hours}ч {minutes}м"))
    
    streak = db.add_daily_streak(uid)
    
    # Базовая награда
    coins = random.randint(100, 300)
    exp = random.randint(20, 60)
    energy = 20
    
    # Множитель от стрика
    coins = int(coins * (1 + min(streak, 30) * 0.05))
    exp = int(exp * (1 + min(streak, 30) * 0.05))
    
    # Множитель от привилегий
    if db.is_vip(uid):
        coins = int(coins * 1.5)
        exp = int(exp * 1.5)
        energy = int(energy * 1.5)
    if db.is_premium(uid):
        coins = int(coins * 2)
        exp = int(exp * 2)
        energy = int(energy * 2)
    
    db.add_coins(uid, coins)
    db.add_exp(uid, exp)
    db.update_user(uid, energy=f"+{energy}")
    
    text = (
        f"# Спектр | Ежедневный бонус\n\n"
        f"🎉 **{update.effective_user.first_name}**, вы получили бонус!\n\n"
        f"💰 Награда: **{coins}** іс\n"
        f"🔥 Стрик: **{streak}** дней\n"
        f"✨ Опыт: +{exp}\n"
        f"⚡ Энергия: +{energy}\n\n"
        f"⏳ Следующий бонус через: **24 часа**"
    )
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    db.log_action(uid, 'daily', f'+{coins}💰')

# ===== БАЛАНС =====

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = db.get_user(uid)
    
    vip_status = "✅ Активен" if db.is_vip(uid) else "❌ Не активен"
    vip_until = ""
    if db.is_vip(uid):
        db.cursor.execute("SELECT vip_until FROM users WHERE telegram_id = ?", (uid,))
        vip_until = datetime.fromisoformat(db.cursor.fetchone()[0]).strftime("%d.%m.%Y")
    
    premium_status = "✅ Активен" if db.is_premium(uid) else "❌ Не активен"
    
    text = (
        f"# Спектр | Кошелёк пользователя **{update.effective_user.first_name}**\n\n"
        f"💰 Баланс: **{user['coins']:,}** іс 🪙\n"
        f"💎 VIP статус: **{vip_status}**\n"
        f"{f'📅 VIP до: **{vip_until}**' if db.is_vip(uid) else ''}\n"
        f"👑 PREMIUM: **{premium_status}**\n\n"
        f"🔥 Стрик: **{user['daily_streak']}** дней\n"
        f"⚡ Энергия: **{user['energy']}/100**\n"
        f"🎁 /daily — доступно"
    )
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# ===== AI АВАТАР =====

async def avatar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = db.get_user(update.effective_user.id)
    name = u.get('nickname') or update.effective_user.first_name
    
    prompt = f"Digital portrait of {name}, fantasy RPG hero, level {u['level']}, glowing mystical eyes, detailed, masterpiece, trending on artstation"
    
    if GROQ_API_KEY and ai and ai.is_available:
        # Используем AI для улучшения промпта
        ai_response = await ai.get_response(
            update.effective_user.id,
            f"Улучши этот промпт для генерации аватара, сделай его более детальным и эпичным: {prompt}"
        )
        if ai_response:
            prompt = ai_response
    
    await update.message.reply_text(
        s.header("🤖 ГЕНЕРАЦИЯ АВАТАРА") + 
        f"🎨 **Промпт для твоего аватара:**\n"
        f"`{prompt}`\n\n"
        f"✨ Скоро будет доступна прямая генерация через AI!",
        parse_mode=ParseMode.MARKDOWN
    )

# ===== МАФИЯ С ПЕРЕМОТКОЙ ВРЕМЕНИ =====

games_in_progress = {}

async def mafia_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        s.header("🔫 МАФИЯ") + "\nВыберите действие:",
        reply_markup=kb.mafia_inline(),
        parse_mode=ParseMode.MARKDOWN
    )

async def mafia_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    if chat_id in games_in_progress:
        return await update.message.reply_text(s.error("❌ Игра уже идёт! Присоединяйтесь: /mafiajoin"))
    
    game_id = f"mafia_{chat_id}_{int(time.time())}"
    game = MafiaGame(chat_id, game_id, update.effective_user.id)
    games_in_progress[chat_id] = game
    
    text = (
        s.header("🔫 МАФИЯ") + "\n\n"
        f"{s.success('🎮 Игра создана!')}\n\n"
        f"{s.item('Участники (0):')}\n"
        f"{s.item('/mafiajoin — присоединиться')}\n"
        f"{s.item('/mafialeave — выйти')}\n\n"
        f"{s.info('Игра будет проходить в ЛС с ботом')}"
    )
    
    msg = await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    game.message_id = msg.message_id

async def mafia_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    if chat_id not in games_in_progress:
        return await update.message.reply_text(s.error("❌ Игра не создана. Начните: /mafiastart"))
    
    game = games_in_progress[chat_id]
    
    if game.status != "waiting":
        return await update.message.reply_text(s.error("❌ Игра уже началась"))
    
    if not game.add_player(user.id, user.first_name, user.username or ""):
        return await update.message.reply_text(s.error("❌ Вы уже в игре"))
    
    try:
        await context.bot.send_message(
            user.id,
            f"{s.header('🔫 МАФИЯ')}\n\n"
            f"{s.item('Вы присоединились к игре!')}\n"
            f"{s.item('Нажмите кнопку для подтверждения')}\n\n"
            f"{s.info('После подтверждения вы получите свою роль в ЛС')}",
            reply_markup=kb.mafia_confirm(chat_id),
            parse_mode=ParseMode.MARKDOWN
        )
        
        await update.message.reply_text(s.success(f"✅ {user.first_name}, проверьте ЛС для подтверждения!"))
    except:
        await update.message.reply_text(s.error(f"❌ {user.first_name}, не удалось отправить сообщение в ЛС"))
        game.remove_player(user.id)
        return
    
    players_list = "\n".join([f"{i+1}. {game.players_data[pid]['name']}" for i, pid in enumerate(game.players)])
    confirmed = sum(1 for p in game.players if game.players_data[p]['confirmed'])
    
    text = (
        s.header("🔫 МАФИЯ") + "\n\n"
        f"{s.item(f'Участники ({len(game.players)}):')}\n"
        f"{players_list}\n\n"
        f"{s.item(f'Подтвердили: {confirmed}/{len(game.players)}')}\n"
        f"{s.item('/mafiajoin — присоединиться')}\n"
        f"{s.item('/mafialeave — выйти')}\n\n"
        f"{s.info('Для старта нужно минимум 6 игроков')}"
    )
    
    try:
        await context.bot.edit_message_text(
            text,
            chat_id=chat_id,
            message_id=game.message_id,
            parse_mode=ParseMode.MARKDOWN
        )
    except:
        pass

async def mafia_leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    if chat_id not in games_in_progress:
        return await update.message.reply_text(s.error("❌ Игра не создана"))
    
    game = games_in_progress[chat_id]
    
    if game.status != "waiting":
        return await update.message.reply_text(s.error("❌ Нельзя покинуть игру после начала"))
    
    if not game.remove_player(user.id):
        return await update.message.reply_text(s.error("❌ Вас нет в игре"))
    
    await update.message.reply_text(s.success(f"✅ {user.first_name} покинул игру"))
    
    if game.players:
        players_list = "\n".join([f"{i+1}. {game.players_data[pid]['name']}" for i, pid in enumerate(game.players)])
        confirmed = sum(1 for p in game.players if game.players_data[p]['confirmed'])
        
        text = (
            s.header("🔫 МАФИЯ") + "\n\n"
            f"{s.item(f'Участники ({len(game.players)}):')}\n"
            f"{players_list}\n\n"
            f"{s.item(f'Подтвердили: {confirmed}/{len(game.players)}')}\n"
            f"{s.item('/mafiajoin — присоединиться')}\n"
            f"{s.item('/mafialeave — выйти')}\n\n"
            f"{s.info('Для старта нужно минимум 6 игроков')}"
        )
    else:
        text = (
            s.header("🔫 МАФИЯ") + "\n\n"
            f"{s.item('Участников нет')}\n"
            f"{s.item('/mafiajoin — присоединиться')}"
        )
    
    try:
        await context.bot.edit_message_text(
            text,
            chat_id=chat_id,
            message_id=game.message_id,
            parse_mode=ParseMode.MARKDOWN
        )
    except:
        pass

async def mafia_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Демонстрация перемотки времени"""
    msg = await update.message.reply_text("🏙 День подходит к концу... Город засыпает.")
    await asyncio.sleep(1)
    
    # В реальности тут отправляется видео-файл
    await update.message.reply_text("🌙 **[ПЕРЕХОД В НОЧЬ]**\nПросыпается мафия...")
    await asyncio.sleep(2)
    
    await update.message.reply_text("☀️ **[ПЕРЕХОД В ДЕНЬ]**\nГород просыпается...")

async def mafia_roles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        s.header("🔫 РОЛИ В МАФИИ") + "\n\n"
        f"{s.section('😈 МАФИЯ')}"
        f"{s.item('😈 Мафиози — ночью убивают')}\n"
        f"{s.item('👑 Босс — глава мафии')}\n\n"
        f"{s.section('👼 ГОРОД')}"
        f"{s.item('👮 Комиссар — проверяет ночью')}\n"
        f"{s.item('👨‍⚕️ Доктор — лечит ночью')}\n"
        f"{s.item('👤 Мирный — ищет мафию')}\n\n"
        f"{s.section('🎭 ОСОБЫЕ')}"
        f"{s.item('🔪 Маньяк — убивает один')}"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def mafia_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        s.header("🔫 ПРАВИЛА МАФИИ") + "\n\n"
        f"{s.section('🌙 НОЧЬ')}"
        f"{s.item('1. Мафия выбирает жертву')}\n"
        f"{s.item('2. Доктор выбирает, кого спасти')}\n"
        f"{s.item('3. Комиссар проверяет')}\n\n"
        f"{s.section('☀️ ДЕНЬ')}"
        f"{s.item('1. Объявление жертв ночи')}\n"
        f"{s.item('2. Обсуждение')}\n"
        f"{s.item('3. Голосование за исключение')}\n\n"
        f"{s.section('🏆 ЦЕЛЬ')}"
        f"{s.item('Мафия — убить всех мирных')}\n"
        f"{s.item('Город — найти всю мафию')}"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# ===== ТОП =====

async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = s.header("🏆 ТОП ИГРОКОВ") + "\n\n"
    
    top_coins = db.get_top("coins", 5)
    text += s.section("💰 ПО МОНЕТАМ")
    for i, row in enumerate(top_coins, 1):
        name = row[1] or row[0]
        text += f"{i}. **{name}** — {row[2]} 💰\n"
    
    top_level = db.get_top("level", 5)
    text += "\n" + s.section("📊 ПО УРОВНЮ")
    for i, row in enumerate(top_level, 1):
        name = row[1] or row[0]
        text += f"{i}. **{name}** — {row[2]} уровень\n"
    
    top_rep = db.get_top("reputation", 5)
    text += "\n" + s.section("⭐ ПО РЕПУТАЦИИ")
    for i, row in enumerate(top_rep, 1):
        name = row[1] or row[0]
        text += f"{i}. **{name}** — {row[2]} ⭐\n"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# ===== ОБРАБОТЧИК ТЕКСТОВЫХ СООБЩЕНИЙ =====

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message_text = update.message.text
    chat = update.effective_chat
    
    # Сохраняем сообщение в БД
    db.cursor.execute('''
        INSERT INTO messages (user_id, username, first_name, message_text, chat_id, chat_title)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user.id, user.username, user.first_name, message_text, chat.id, chat.title))
    db.conn.commit()
    
    # Обновляем статистику
    db.update_user(user.id, messages_count="+1")
    
    if message_text.startswith('/'):
        return
    
    # Обработка reply-кнопок
    if message_text == "🏠 ГЛАВНОЕ":
        await menu_command(update, context)
        return
    elif message_text == "👤 ПРОФИЛЬ":
        await profile_command(update, context)
        return
    elif message_text == "⚔️ БОСС":
        await bosses_command(update, context)
        return
    elif message_text == "🎰 СЛОТЫ":
        await play_slots(update, context)
        return
    elif message_text == "🔫 МАФИЯ":
        await mafia_command(update, context)
        return
    elif message_text == "📊 ТОП":
        await top_command(update, context)
        return
    elif message_text == "❓ ПОМОЩЬ":
        await help_command(update, context)
        return
    elif message_text == "🎁 DAILY":
        await daily_command(update, context)
        return
    
    # AI отвечает только если:
    # 1. Это личка (чат с ботом) - всегда отвечает
    # 2. В группе - только если сообщение начинается со слова "Спектр"
    should_respond = False
    
    if chat.type == "private":
        should_respond = True
    elif message_text.lower().startswith("спектр"):
        # Убираем слово "Спектр" из запроса
        message_text = message_text[6:].strip()
        if not message_text:
            message_text = "Привет"
        should_respond = True
    
    if should_respond and ai and ai.is_available:
        try:
            await update.message.chat.send_action(action="typing")
            response = await ai.get_response(user.id, message_text, user.first_name)
            if response:
                await update.message.reply_text(f"🤖 **Спектр:** {response}", parse_mode=ParseMode.MARKDOWN)
                return
        except Exception as e:
            logger.error(f"AI response error: {e}")
            await update.message.reply_text(s.error("❌ AI временно недоступен"))

# ===== CALLBACK КНОПКИ =====

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user
    
    if data == "menu_main":
        await query.edit_message_text(
            s.header("ГЛАВНОЕ МЕНЮ") + "\nВыберите раздел:",
            reply_markup=kb.main_inline(),
            parse_mode=ParseMode.MARKDOWN
        )
    elif data == "menu_back":
        await query.edit_message_text(
            s.header("ГЛАВНОЕ МЕНЮ") + "\nВыберите раздел:",
            reply_markup=kb.main_inline(),
            parse_mode=ParseMode.MARKDOWN
        )
    elif data == "menu_profile":
        await profile_command(update, context)
    elif data == "menu_top":
        await top_command(update, context)
    elif data == "boss_info":
        boss = db.get_boss(1)
        txt = s.header("Рейд-Босс") + s.stat("Имя", boss['name']) + s.stat("Здоровье", "")
        txt += s.progress(boss['hp'], boss['max_hp'])
        kb_boss = InlineKeyboardMarkup([[InlineKeyboardButton("⚔️ НАНЕСТИ УДАР", callback_data="boss_attack")]])
        await query.edit_message_text(txt, reply_markup=kb_boss, parse_mode=ParseMode.MARKDOWN)
    elif data == "boss_attack":
        uid = user.id
        user_data = db.get_user(uid)
        boss = db.get_boss(1)
        
        if not boss['alive']:
            db.respawn_boss(1)
            boss = db.get_boss(1)
        
        if user_data['energy'] < 10:
            await query.edit_message_text(s.error("❌ Недостаточно энергии!"))
            return
        
        db.update_user(uid, energy="-10")
        
        dmg = random.randint(50, 200)
        if db.is_vip(uid):
            dmg = int(dmg * 1.2)
        
        killed = db.damage_boss(1, dmg)
        db.update_user(uid, boss_damage=f"+{dmg}", exp="+10")
        
        if killed:
            # Генерация Артефакта
            art = random.choice(["💎 Око Бездны", "🗡 Клинок Спектра", "🛡 Плащ Ночи", "👑 Корона Тьмы"])
            db.add_to_inventory(uid, art)
            db.add_coins(uid, boss['reward_coins'])
            db.add_exp(uid, boss['reward_exp'])
            db.update_user(uid, boss_kills=f"+1")
            
            await query.message.reply_text(s.success(f"БОСС ПАЛ! Твоя награда: {art}"))
            db.respawn_boss(1)
            boss = db.get_boss(1)
        
        txt = s.header("БИТВА") + s.stat("Ты нанес", dmg, "💥") + s.progress(boss['hp'], boss['max_hp'])
        kb_attack = InlineKeyboardMarkup([[InlineKeyboardButton("⚔️ БИТЬ СНОВА", callback_data="boss_attack")]])
        await query.edit_message_text(txt, reply_markup=kb_attack, parse_mode=ParseMode.MARKDOWN)
    
    elif data == "menu_mafia":
        await query.edit_message_text(
            s.header("🔫 МАФИЯ") + "\nВыберите действие:",
            reply_markup=kb.mafia_inline(),
            parse_mode=ParseMode.MARKDOWN
        )
    elif data == "mafia_start":
        await mafia_start(update, context)
    elif data == "mafia_rules":
        await mafia_rules(update, context)
    elif data == "mafia_roles":
        await mafia_roles(update, context)
    elif data == "game_slots":
        await play_slots(update, context)
    elif data == "menu_chart":
        await chart_command(update, context)
    elif data == "menu_avatar":
        await avatar_command(update, context)
    elif data == "menu_daily":
        await daily_command(update, context)
    elif data.startswith("mafia_confirm_"):
        chat_id = int(data.split('_')[2])
        if chat_id in games_in_progress:
            game = games_in_progress[chat_id]
            if user.id in game.players:
                game.confirm_player(user.id)
                await query.edit_message_text(
                    f"{s.success('✅ Подтверждение получено!')}\n\n"
                    f"{s.info('Ожидайте начала игры...')}",
                    parse_mode=ParseMode.MARKDOWN
                )
    elif data.startswith("accept_duel_"):
        duel_id = int(data.split('_')[2])
        db.cursor.execute("SELECT * FROM duels WHERE id = ?", (duel_id,))
        duel = db.cursor.fetchone()
        
        if duel and duel[2] == user.id and duel[3] == 'pending':
            db.cursor.execute("UPDATE duels SET status = 'accepted' WHERE id = ?", (duel_id,))
            db.conn.commit()
            
            # Простая логика дуэли (50/50)
            winner = random.choice([duel[1], duel[2]])
            loser = duel[2] if winner == duel[1] else duel[1]
            
            db.add_coins(winner, duel[3])
            db.update_user(winner, duel_wins="+1", duel_rating="+50")
            db.update_user(loser, duel_losses="+1", duel_rating="-30")
            
            winner_data = db.get_user(winner)
            loser_data = db.get_user(loser)
            
            await query.edit_message_text(
                f"# Спектр | Дуэль\n\n"
                f"⚔️ **{winner_data['first_name']}** ПОБЕДИЛ!\n"
                f"💰 Выигрыш: {duel[3]} іс\n\n"
                f"🏆 Новый рейтинг победителя: {winner_data['duel_rating']}",
                parse_mode=ParseMode.MARKDOWN
            )

# ===== ОБРАБОТЧИК НОВЫХ УЧАСТНИКОВ =====

async def handle_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    db.cursor.execute("SELECT welcome FROM chat_settings WHERE chat_id = ?", (chat_id,))
    row = db.cursor.fetchone()
    welcome_text = row[0] if row and row[0] else "Добро пожаловать!"
    
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        
        db.get_user(member.id, member.first_name, member.username or "")
        
        await update.message.reply_text(
            f"👋 {welcome_text}\n\n{member.first_name}, используй /help для команд!",
            parse_mode=ParseMode.MARKDOWN
        )

# ===== ОБРАБОТЧИК ОШИБОК =====

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Ошибка: {context.error}")
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(s.error("❌ Произошла внутренняя ошибка"))
    except:
        pass

# ===== ЗАПУСК =====

def main():
    app = Application.builder().token(TOKEN).build()

    # Основные команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("menu", menu_command))
    
    # Профиль
    app.add_handler(CommandHandler("profile", profile_command))
    app.add_handler(CommandHandler("chart", chart_command))
    app.add_handler(CommandHandler("id", lambda u, c: u.message.reply_text(f"🆔 Ваш ID: `{u.effective_user.id}`")))
    
    # Экономика
    app.add_handler(CommandHandler("balance", balance_command))
    app.add_handler(CommandHandler("daily", daily_command))
    app.add_handler(CommandHandler("vip", lambda u, c: u.message.reply_text(s.info("VIP статус - 5000 монет/30дней"))))
    
    # Игры
    app.add_handler(CommandHandler("slots", play_slots))
    app.add_handler(CommandHandler("dice", play_dice))
    app.add_handler(CommandHandler("duel", duel_command))
    app.add_handler(CommandHandler("duelrating", duel_rating_command))
    
    # Боссы
    app.add_handler(CommandHandler("bosses", bosses_command))
    app.add_handler(CommandHandler("boss", boss_fight))
    app.add_handler(CommandHandler("regen", regen_command))
    
    # Мафия
    app.add_handler(CommandHandler("mafia", mafia_command))
    app.add_handler(CommandHandler("mafiastart", mafia_start))
    app.add_handler(CommandHandler("mafiajoin", mafia_join))
    app.add_handler(CommandHandler("mafialeave", mafia_leave))
    app.add_handler(CommandHandler("mafiatime", mafia_time))
    app.add_handler(CommandHandler("mafiaroles", mafia_roles))
    app.add_handler(CommandHandler("mafiarules", mafia_rules))
    
    # Топ
    app.add_handler(CommandHandler("top", top_command))
    app.add_handler(CommandHandler("topcoins", lambda u, c: u.message.reply_text("Используй /top")))
    
    # AI
    app.add_handler(CommandHandler("avatar", avatar_command))
    
    # Обработчики реакций и кнопок
    app.add_handler(MessageReactionHandler(handle_reactions))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Обработчики сообщений
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_members))
    
    # Обработчик ошибок
    app.add_error_handler(error_handler)
    
    print("💎 Спектр v8.0 Ультимейт запущен успешно!")
    print(f"🤖 AI: {'Подключен' if ai and ai.is_available else 'Не подключен'}")
    print(f"👑 Владелец: {OWNER_USERNAME}")
    
    app.run_polling()

if __name__ == "__main__":
    main()
