#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
СПЕКТР - Официальный бот с полным функционалом Iris + Мафия + Groq AI
Версия 5.0 ULTIMATE
"""

import os
import sys
import logging
import asyncio
import json
import random
import sqlite3
import datetime
from typing import Optional, Dict, Any, List, Tuple
from collections import defaultdict, deque
import time
import hashlib
import re
from enum import Enum

import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from telegram.constants import ParseMode
from telegram.error import TelegramError

# ========== НАСТРОЙКИ ==========
TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_KEY = os.environ.get("GROQ_API_KEY")
OWNER_ID = int(os.environ.get("OWNER_ID", "1732658530"))
OWNER_USERNAME = "@NobuCraft"

if not TOKEN:
    print("❌ ОШИБКА: TELEGRAM_TOKEN не найден в переменных окружения!")
    sys.exit(1)

# AI настройки
AI_CHANCE = 40  # 40% шанс ответа AI на сообщения

# Настройки модерации
SPAM_LIMIT = 5
SPAM_WINDOW = 3
SPAM_MUTE_TIME = 120

# Привилегии
VIP_PRICE = 5000
PREMIUM_PRICE = 15000
VIP_DAYS = 30
PREMIUM_DAYS = 30

# Лимиты
MAX_NICK_LENGTH = 30
MAX_TITLE_LENGTH = 30
MAX_MOTTO_LENGTH = 100
MAX_BIO_LENGTH = 500

# Временные интервалы
DAILY_COOLDOWN = 86400
WEEKLY_COOLDOWN = 604800
MONTHLY_COOLDOWN = 2592000

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== ЭЛЕГАНТНОЕ ОФОРМЛЕНИЕ (КАК У IRIS) ==========
class Style:
    """Классическое оформление как у Iris"""
    
    SEPARATOR = "─" * 28
    SEPARATOR_BOLD = "━" * 28
    SEPARATOR_DOTS = "•" * 28
    
    @classmethod
    def header(cls, title: str, emoji: str = "⚜️") -> str:
        return f"\n{emoji}{emoji} **{title.upper()}** {emoji}{emoji}\n{cls.SEPARATOR_BOLD}\n"
    
    @classmethod
    def section(cls, title: str, emoji: str = "📌") -> str:
        return f"\n{emoji} **{title}**\n{cls.SEPARATOR}\n"
    
    @classmethod
    def subsection(cls, title: str) -> str:
        return f"\n  ▸ **{title}**\n"
    
    @classmethod
    def cmd(cls, cmd: str, desc: str, usage: str = "") -> str:
        if usage:
            return f"▸ `/{cmd} {usage}` — {desc}"
        return f"▸ `/{cmd}` — {desc}"
    
    @classmethod
    def param(cls, name: str, desc: str) -> str:
        return f"  └ {name} — {desc}"
    
    @classmethod
    def example(cls, text: str) -> str:
        return f"  └ Пример: `{text}`"
    
    @classmethod
    def item(cls, text: str, emoji: str = "•") -> str:
        return f"{emoji} {text}"
    
    @classmethod
    def stat(cls, name: str, value: str, emoji: str = "◉") -> str:
        return f"{emoji} **{name}:** {value}"
    
    @classmethod
    def progress(cls, current: int, total: int, length: int = 15) -> str:
        filled = int((current / total) * length)
        bar = "█" * filled + "░" * (length - filled)
        return f"`{bar}` {current}/{total}"
    
    @classmethod
    def success(cls, text: str) -> str:
        return f"✅ **{text}**"
    
    @classmethod
    def error(cls, text: str) -> str:
        return f"❌ **{text}**"
    
    @classmethod
    def warning(cls, text: str) -> str:
        return f"⚠️ **{text}**"
    
    @classmethod
    def info(cls, text: str) -> str:
        return f"ℹ️ **{text}**"
    
    @classmethod
    def code(cls, text: str) -> str:
        return f"`{text}`"
    
    @classmethod
    def bold(cls, text: str) -> str:
        return f"**{text}**"
    
    @classmethod
    def italic(cls, text: str) -> str:
        return f"_{text}_"

s = Style()

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
    def main(cls):
        return cls.make([
            [("👤 ПРОФИЛЬ", "menu_profile"), ("📊 СТАТИСТИКА", "menu_stats")],
            [("🎮 МАФИЯ", "menu_mafia"), ("💰 ЭКОНОМИКА", "menu_economy")],
            [("🎲 ИГРЫ", "menu_games"), ("⚙️ МОДЕРАЦИЯ", "menu_mod")],
            [("💎 ПРИВИЛЕГИИ", "menu_donate"), ("📚 ПОМОЩЬ", "menu_help")]
        ])
    
    @classmethod
    def games(cls):
        return cls.make([
            [("🔫 РУССКАЯ РУЛЕТКА", "game_rr"), ("🎲 КОСТИ", "game_dice")],
            [("🎰 РУЛЕТКА", "game_roulette"), ("🎰 СЛОТЫ", "game_slots")],
            [("✊ КНБ", "game_rps"), ("💣 САПЁР", "game_saper")],
            [("🎯 БЫКИ И КОРОВЫ", "game_bulls"), ("🔢 УГАДАЙ ЧИСЛО", "game_guess")],
            [("🔙 НАЗАД", "menu_back")]
        ])
    
    @classmethod
    def mafia(cls):
        return cls.make([
            [("🎮 НАЧАТЬ ИГРУ", "mafia_start"), ("📋 ПРАВИЛА", "mafia_rules")],
            [("👥 РОЛИ", "mafia_roles"), ("📊 СТАТИСТИКА", "mafia_stats")],
            [("🔙 НАЗАД", "menu_back")]
        ])
    
    @classmethod
    def economy(cls):
        return cls.make([
            [("💰 БАЛАНС", "eco_balance"), ("📦 МАГАЗИН", "eco_shop")],
            [("🎁 БОНУСЫ", "eco_bonus"), ("💳 ПЕРЕВОД", "eco_pay")],
            [("💎 ПРИВИЛЕГИИ", "menu_donate"), ("📊 ТОП", "eco_top")],
            [("🔙 НАЗАД", "menu_back")]
        ])
    
    @classmethod
    def mod(cls):
        return cls.make([
            [("⚠️ ВАРНЫ", "mod_warns"), ("🔇 МУТЫ", "mod_mutes")],
            [("🔨 БАНЫ", "mod_bans"), ("📋 ЧЕРНЫЙ СПИСОК", "mod_blacklist")],
            [("👥 АДМИНЫ", "mod_admins"), ("⚙️ НАСТРОЙКИ", "mod_settings")],
            [("🔙 НАЗАД", "menu_back")]
        ])
    
    @classmethod
    def back(cls):
        return cls.make([[("◀ НАЗАД", "menu_back")]])
    
    @classmethod
    def back_main(cls):
        return cls.make([
            [("◀ НАЗАД", "menu_back"), ("🏠 ГЛАВНАЯ", "menu_main")]
        ])
    
    @classmethod
    def confirm(cls):
        return cls.make([
            [("✅ ДА", "confirm"), ("❌ НЕТ", "cancel")]
        ])
    
    @classmethod
    def rps(cls):
        return cls.make([
            [("🪨 КАМЕНЬ", "rps_rock"), ("✂️ НОЖНИЦЫ", "rps_scissors"), ("📄 БУМАГА", "rps_paper")],
            [("🔙 НАЗАД", "menu_back")]
        ])

kb = Keyboard()

# ========== РАНГИ МОДЕРАЦИИ ==========
RANKS = {
    0: {"name": "Участник", "emoji": "👤"},
    1: {"name": "Младший модератор", "emoji": "🟢"},
    2: {"name": "Старший модератор", "emoji": "🔵"},
    3: {"name": "Младший администратор", "emoji": "🟣"},
    4: {"name": "Старший администратор", "emoji": "🔴"},
    5: {"name": "Создатель", "emoji": "👑"}
}

# ========== ГИФКИ ДЛЯ МАФИИ ==========
MAFIA_GIFS = {
    "day": "https://files.catbox.moe/g9vc7v.mp4",
    "night": "https://files.catbox.moe/lvcm8n.mp4",
    "revolver": "https://files.catbox.moe/pj64wq.gif"
}

# ========== БАЗА ДАННЫХ (ПОЛНАЯ) ==========
class Database:
    def __init__(self):
        self.conn = sqlite3.connect("spectrum.db", check_same_thread=False)
        self.c = self.conn.cursor()
        self.create_tables()
        logger.info("✅ База данных инициализирована")
    
    def create_tables(self):
        # Пользователи (полная таблица)
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                language TEXT DEFAULT 'ru',
                
                -- Ресурсы
                coins INTEGER DEFAULT 1000,
                diamonds INTEGER DEFAULT 0,
                energy INTEGER DEFAULT 100,
                
                -- Прогресс
                level INTEGER DEFAULT 1,
                exp INTEGER DEFAULT 0,
                
                -- Боевые
                health INTEGER DEFAULT 100,
                max_health INTEGER DEFAULT 100,
                damage INTEGER DEFAULT 10,
                armor INTEGER DEFAULT 0,
                crit_chance INTEGER DEFAULT 5,
                crit_multiplier INTEGER DEFAULT 150,
                
                -- Статистика
                messages_count INTEGER DEFAULT 0,
                commands_used INTEGER DEFAULT 0,
                
                -- Игры
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
                
                -- Мафия
                mafia_games INTEGER DEFAULT 0,
                mafia_wins INTEGER DEFAULT 0,
                mafia_losses INTEGER DEFAULT 0,
                mafia_role TEXT,
                
                -- Профиль
                nickname TEXT,
                title TEXT DEFAULT '',
                motto TEXT DEFAULT 'Нет девиза',
                bio TEXT DEFAULT '',
                gender TEXT DEFAULT 'не указан',
                city TEXT DEFAULT 'не указан',
                country TEXT DEFAULT 'не указана',
                birth_date TEXT,
                age INTEGER DEFAULT 0,
                reputation INTEGER DEFAULT 0,
                
                -- Модерация
                role TEXT DEFAULT 'user',
                rank INTEGER DEFAULT 0,
                rank_name TEXT DEFAULT 'Участник',
                warns INTEGER DEFAULT 0,
                warns_list TEXT DEFAULT '[]',
                mute_until TEXT,
                banned INTEGER DEFAULT 0,
                ban_reason TEXT,
                ban_date TEXT,
                ban_admin INTEGER,
                
                -- Привилегии
                vip_until TEXT,
                premium_until TEXT,
                
                -- Бонусы
                daily_streak INTEGER DEFAULT 0,
                last_daily TEXT,
                last_weekly TEXT,
                last_monthly TEXT,
                last_work TEXT,
                last_seen TEXT,
                
                -- Настройки
                notifications INTEGER DEFAULT 1,
                theme TEXT DEFAULT 'light',
                
                -- Метаданные
                registered TEXT DEFAULT CURRENT_TIMESTAMP,
                referrer_id INTEGER
            )
        ''')
        
        # Индексы
        self.c.execute('CREATE INDEX IF NOT EXISTS idx_telegram_id ON users(telegram_id)')
        self.c.execute('CREATE INDEX IF NOT EXISTS idx_username ON users(username)')
        self.c.execute('CREATE INDEX IF NOT EXISTS idx_rank ON users(rank)')
        
        # Логи
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT,
                details TEXT,
                chat_id INTEGER,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Черный список слов
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS blacklist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT UNIQUE,
                added_by INTEGER,
                added_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Настройки чатов
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS chat_settings (
                chat_id INTEGER PRIMARY KEY,
                welcome TEXT,
                rules TEXT,
                antiflood INTEGER DEFAULT 1,
                antispam INTEGER DEFAULT 1,
                antilink INTEGER DEFAULT 0,
                captcha INTEGER DEFAULT 0,
                log_chat INTEGER,
                lang TEXT DEFAULT 'ru'
            )
        ''')
        
        # Игры
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                game_type TEXT,
                players TEXT,
                status TEXT,
                data TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()

    # ===== МЕТОДЫ БАЗЫ ДАННЫХ =====
    
    def get_user(self, telegram_id: int, first_name: str = "Player") -> Dict[str, Any]:
        self.c.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        row = self.c.fetchone()
        
        if not row:
            role = 'owner' if telegram_id == OWNER_ID else 'user'
            rank = 5 if telegram_id == OWNER_ID else 0
            rank_name = RANKS[rank]["name"]
            
            self.c.execute('''
                INSERT INTO users (telegram_id, first_name, role, rank, rank_name, last_seen)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (telegram_id, first_name, role, rank, rank_name, datetime.datetime.now().isoformat()))
            self.conn.commit()
            return self.get_user(telegram_id, first_name)
        
        cols = [d[0] for d in self.c.description]
        user = dict(zip(cols, row))
        
        self.c.execute("UPDATE users SET last_seen = ?, first_name = ? WHERE telegram_id = ?",
                      (datetime.datetime.now().isoformat(), first_name, telegram_id))
        self.conn.commit()
        
        return user
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        self.c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = self.c.fetchone()
        if row:
            cols = [d[0] for d in self.c.description]
            return dict(zip(cols, row))
        return None
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        if username.startswith('@'):
            username = username[1:]
        self.c.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = self.c.fetchone()
        if row:
            cols = [d[0] for d in self.c.description]
            return dict(zip(cols, row))
        return None
    
    def update_user(self, user_id: int, **kwargs) -> bool:
        if not kwargs:
            return False
        for key, value in kwargs.items():
            self.c.execute(f"UPDATE users SET {key} = ? WHERE id = ?", (value, user_id))
        self.conn.commit()
        return True
    
    def add_coins(self, user_id: int, amount: int) -> int:
        self.c.execute("UPDATE users SET coins = coins + ? WHERE id = ?", (amount, user_id))
        self.conn.commit()
        self.c.execute("SELECT coins FROM users WHERE id = ?", (user_id,))
        return self.c.fetchone()[0]
    
    def add_exp(self, user_id: int, amount: int) -> bool:
        self.c.execute("UPDATE users SET exp = exp + ? WHERE id = ?", (amount, user_id))
        self.c.execute("SELECT exp, level FROM users WHERE id = ?", (user_id,))
        exp, level = self.c.fetchone()
        if exp >= level * 100:
            self.c.execute("UPDATE users SET level = level + 1, exp = exp - ? WHERE id = ?", 
                          (level * 100, user_id))
            self.conn.commit()
            return True
        self.conn.commit()
        return False
    
    # ===== МОДЕРАЦИЯ =====
    
    def set_rank(self, user_id: int, rank: int, admin_id: int) -> bool:
        if rank not in RANKS:
            return False
        self.c.execute("UPDATE users SET rank = ?, rank_name = ? WHERE id = ?",
                      (rank, RANKS[rank]["name"], user_id))
        self.conn.commit()
        self.log_action(admin_id, "set_rank", f"{user_id} -> {rank}")
        return True
    
    def add_warn(self, user_id: int, admin_id: int, reason: str) -> int:
        self.c.execute("SELECT warns, warns_list FROM users WHERE id = ?", (user_id,))
        warns, warns_list = self.c.fetchone()
        warns_list = json.loads(warns_list)
        warns_list.append({
            'id': len(warns_list) + 1,
            'admin_id': admin_id,
            'reason': reason,
            'date': datetime.datetime.now().isoformat()
        })
        new_warns = warns + 1
        self.c.execute("UPDATE users SET warns = ?, warns_list = ? WHERE id = ?",
                      (new_warns, json.dumps(warns_list), user_id))
        self.conn.commit()
        self.log_action(admin_id, "add_warn", f"{user_id}: {reason}")
        return new_warns
    
    def get_warns(self, user_id: int) -> List[Dict]:
        self.c.execute("SELECT warns_list FROM users WHERE id = ?", (user_id,))
        row = self.c.fetchone()
        return json.loads(row[0]) if row and row[0] else []
    
    def remove_last_warn(self, user_id: int, admin_id: int) -> Optional[Dict]:
        self.c.execute("SELECT warns, warns_list FROM users WHERE id = ?", (user_id,))
        warns, warns_list = self.c.fetchone()
        warns_list = json.loads(warns_list)
        if not warns_list:
            return None
        removed = warns_list.pop()
        self.c.execute("UPDATE users SET warns = ?, warns_list = ? WHERE id = ?",
                      (warns - 1, json.dumps(warns_list), user_id))
        self.conn.commit()
        self.log_action(admin_id, "remove_warn", f"{user_id}")
        return removed
    
    def mute_user(self, user_id: int, minutes: int, admin_id: int, reason: str = "") -> datetime.datetime:
        until = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
        self.c.execute("UPDATE users SET mute_until = ? WHERE id = ?", (until.isoformat(), user_id))
        self.conn.commit()
        self.log_action(admin_id, "mute", f"{user_id} {minutes}мин: {reason}")
        return until
    
    def is_muted(self, user_id: int) -> bool:
        self.c.execute("SELECT mute_until FROM users WHERE id = ?", (user_id,))
        row = self.c.fetchone()
        if row and row[0]:
            return datetime.datetime.fromisoformat(row[0]) > datetime.datetime.now()
        return False
    
    def unmute_user(self, user_id: int, admin_id: int) -> bool:
        self.c.execute("UPDATE users SET mute_until = NULL WHERE id = ?", (user_id,))
        self.conn.commit()
        self.log_action(admin_id, "unmute", str(user_id))
        return True
    
    def ban_user(self, user_id: int, admin_id: int, reason: str) -> bool:
        self.c.execute('''
            UPDATE users SET banned = 1, ban_reason = ?, ban_date = ?, ban_admin = ?
            WHERE id = ?
        ''', (reason, datetime.datetime.now().isoformat(), admin_id, user_id))
        self.conn.commit()
        self.log_action(admin_id, "ban", f"{user_id}: {reason}")
        return True
    
    def unban_user(self, user_id: int, admin_id: int) -> bool:
        self.c.execute("UPDATE users SET banned = 0, ban_reason = NULL, ban_date = NULL, ban_admin = NULL WHERE id = ?", (user_id,))
        self.conn.commit()
        self.log_action(admin_id, "unban", str(user_id))
        return True
    
    def is_banned(self, user_id: int) -> bool:
        self.c.execute("SELECT banned FROM users WHERE id = ?", (user_id,))
        row = self.c.fetchone()
        return row and row[0] == 1
    
    def get_banlist(self) -> List[Dict]:
        self.c.execute("SELECT id, first_name, username FROM users WHERE banned = 1")
        cols = ['id', 'first_name', 'username']
        return [dict(zip(cols, row)) for row in self.c.fetchall()]
    
    # ===== ЧЕРНЫЙ СПИСОК =====
    
    def add_to_blacklist(self, word: str, admin_id: int) -> bool:
        try:
            self.c.execute("INSERT INTO blacklist (word, added_by) VALUES (?, ?)", (word.lower(), admin_id))
            self.conn.commit()
            self.log_action(admin_id, "add_blacklist", word)
            return True
        except:
            return False
    
    def remove_from_blacklist(self, word: str, admin_id: int) -> bool:
        self.c.execute("DELETE FROM blacklist WHERE word = ?", (word.lower(),))
        self.conn.commit()
        self.log_action(admin_id, "remove_blacklist", word)
        return self.c.rowcount > 0
    
    def get_blacklist(self) -> List[str]:
        self.c.execute("SELECT word FROM blacklist ORDER BY word")
        return [row[0] for row in self.c.fetchall()]
    
    def is_word_blacklisted(self, text: str) -> bool:
        words = self.get_blacklist()
        text_lower = text.lower()
        for word in words:
            if word in text_lower:
                return True
        return False
    
    # ===== ТОПЫ =====
    
    def get_top(self, field: str, limit: int = 10) -> List[Tuple]:
        self.c.execute(f"SELECT first_name, nickname, {field} FROM users ORDER BY {field} DESC LIMIT ?", (limit,))
        return self.c.fetchall()
    
    # ===== ЛОГИ =====
    
    def log_action(self, user_id: int, action: str, details: str = "", chat_id: int = None):
        self.c.execute('''
            INSERT INTO logs (user_id, action, details, chat_id, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, action, details, chat_id, datetime.datetime.now().isoformat()))
        self.conn.commit()
    
    def close(self):
        self.conn.close()

db = Database()

# ========== GROQ AI (ДЕРЗКИЙ, СО СЛЕНГОМ) ==========
class GroqAI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.session = None
        self.contexts = defaultdict(lambda: deque(maxlen=10))
        self.user_last_ai = defaultdict(float)
        self.ai_cooldown = 3
        
        # Дерзкий системный промпт со сленгом
        self.system_prompt = """Ты — Спектр, дерзкий и умный ИИ-бот, который тусуется в Telegram чатах.

Твой характер:
- Используешь современный сленг: крч, зашло, краш, рофл, кринж, база, по факту, рил ток, вайб, хайп, флекс, агриться, душный, токс, сигма, скилл, ганг, бро
- Можешь жестко ответить, если тебя бесят или провоцируют
- Любишь подкалывать, но не переходишь грань
- Если к тебе обращаются нормально — отвечаешь нормально
- Если хамят — можешь и послать (но культурно, в рамках)
- Знаешь все про игры (мафия, русская рулетка, КНБ, кости, слоты)
- Знаешь про экономику (монеты, донат, VIP)
- Знаешь про модерацию (варны, муты, баны)
- Твой создатель: @NobuCraft

Примеры ответов:
- "Окей, зашло, погнали"
- "Это кринж конечно, но ладно"
- "База! Так и думал"
- "Не агрись, бро"
- "Ты че, краш мой что ли?"
- "💀 Ну ты и сказанул"
- "Крч, слушай сюда..."
- "Рил ток? Ну ок"
- "Какой вайб, такие и ответы"

Отвечай кратко, по делу, но с характером. Не будь скучным."""
    
    async def get_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def get_response(self, user_id: int, message: str, username: str = "Пользователь") -> Optional[str]:
        now = time.time()
        if now - self.user_last_ai[user_id] < self.ai_cooldown:
            return None
        self.user_last_ai[user_id] = now
        
        try:
            session = await self.get_session()
            
            history = list(self.contexts[user_id])
            messages = [{"role": "system", "content": self.system_prompt}] + history + [{"role": "user", "content": message}]
            
            data = {
                "model": "llama-3.3-70b-versatile",
                "messages": messages,
                "temperature": 0.85,
                "max_tokens": 250
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            async with session.post(self.api_url, headers=headers, json=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    response = result["choices"][0]["message"]["content"]
                    self.contexts[user_id].append({"role": "user", "content": message})
                    self.contexts[user_id].append({"role": "assistant", "content": response})
                    return response
                else:
                    logger.error(f"Groq API error: {resp.status}")
                    return None
        except Exception as e:
            logger.error(f"Groq error: {e}")
            return None
    
    async def close(self):
        if self.session:
            await self.session.close()

if GROQ_KEY:
    ai = GroqAI(GROQ_KEY)
    print("✅ Groq AI инициализирован (дерзкий режим)")
else:
    ai = None
    print("⚠️ Groq AI не подключен (ключ не найден)")

# ========== ОСНОВНОЙ КЛАСС БОТА ==========
class SpectrumBot:
    def __init__(self):
        self.db = db
        self.ai = ai
        self.spam_tracker = defaultdict(list)
        self.app = Application.builder().token(TOKEN).build()
        self.start_time = datetime.datetime.now()
        self.games_in_progress = {}
        self.mafia_games = {}
        self.setup_handlers()
        logger.info("✅ Бот СПЕКТР инициализирован")
    
    def get_role_emoji(self, rank: int) -> str:
        return RANKS.get(rank, RANKS[0])["emoji"]
    
    def has_permission(self, user_data: Dict, required_rank: int) -> bool:
        user_rank = user_data.get('rank', 0)
        return user_rank >= required_rank
    
    async def check_spam(self, update: Update) -> bool:
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if self.has_permission(user_data, 2):
            return False
        
        now = time.time()
        user_id = user.id
        
        self.spam_tracker[user_id] = [t for t in self.spam_tracker[user_id] if now - t < SPAM_WINDOW]
        self.spam_tracker[user_id].append(now)
        
        if len(self.spam_tracker[user_id]) > SPAM_LIMIT:
            self.db.mute_user(user_data['id'], SPAM_MUTE_TIME, 0, "Авто-спам")
            await update.message.reply_text(s.error(f"Спам! Мут на {SPAM_MUTE_TIME} минут"))
            self.spam_tracker[user_id] = []
            return True
        return False
    
    def setup_handlers(self):
        # ===== ОСНОВНЫЕ КОМАНДЫ =====
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CommandHandler("menu", self.cmd_menu))
        
        # ===== ПРОФИЛЬ =====
        self.app.add_handler(CommandHandler("profile", self.cmd_profile))
        self.app.add_handler(CommandHandler("nick", self.cmd_set_nick))
        self.app.add_handler(CommandHandler("title", self.cmd_set_title))
        self.app.add_handler(CommandHandler("motto", self.cmd_set_motto))
        self.app.add_handler(CommandHandler("bio", self.cmd_set_bio))
        self.app.add_handler(CommandHandler("gender", self.cmd_set_gender))
        self.app.add_handler(CommandHandler("city", self.cmd_set_city))
        self.app.add_handler(CommandHandler("birth", self.cmd_set_birth))
        self.app.add_handler(CommandHandler("id", self.cmd_id))
        self.app.add_handler(CommandHandler("rep", self.cmd_rep))
        
        # ===== СТАТИСТИКА =====
        self.app.add_handler(CommandHandler("stats", self.cmd_stats))
        self.app.add_handler(CommandHandler("top", self.cmd_top))
        
        # ===== МОДЕРАЦИЯ (5 РАНГОВ) =====
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+Модер|^!модер|^повысить'), self.cmd_set_rank))
        self.app.add_handler(MessageHandler(filters.Regex(r'^снять |^разжаловать'), self.cmd_remove_rank))
        self.app.add_handler(CommandHandler("снять_всех", self.cmd_remove_all_ranks))
        self.app.add_handler(CommandHandler("кто_админ", self.cmd_who_admins))
        
        # ===== БАНЫ И ПРЕДУПРЕЖДЕНИЯ =====
        self.app.add_handler(MessageHandler(filters.Regex(r'^варн|^пред'), self.cmd_warn))
        self.app.add_handler(CommandHandler("варны", self.cmd_warns))
        self.app.add_handler(MessageHandler(filters.Regex(r'^снять_варн|^-варн'), self.cmd_unwarn))
        self.app.add_handler(MessageHandler(filters.Regex(r'^мут'), self.cmd_mute))
        self.app.add_handler(CommandHandler("мутлист", self.cmd_mutelist))
        self.app.add_handler(MessageHandler(filters.Regex(r'^размут'), self.cmd_unmute))
        self.app.add_handler(MessageHandler(filters.Regex(r'^бан'), self.cmd_ban))
        self.app.add_handler(CommandHandler("банлист", self.cmd_banlist))
        self.app.add_handler(MessageHandler(filters.Regex(r'^разбан'), self.cmd_unban))
        self.app.add_handler(MessageHandler(filters.Regex(r'^кик'), self.cmd_kick))
        
        # ===== ЧИСТКА ЧАТА =====
        self.app.add_handler(MessageHandler(filters.Regex(r'^чистка'), self.cmd_clear))
        
        # ===== НАСТРОЙКИ ЧАТА =====
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+приветствие'), self.cmd_set_welcome))
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+правила'), self.cmd_set_rules))
        self.app.add_handler(CommandHandler("правила", self.cmd_show_rules))
        self.app.add_handler(MessageHandler(filters.Regex(r'^-приветствие'), self.cmd_remove_welcome))
        self.app.add_handler(MessageHandler(filters.Regex(r'^капча'), self.cmd_set_captcha))
        
        # ===== ЧЕРНЫЙ СПИСОК =====
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+блэклист|^\+чс'), self.cmd_add_blacklist))
        self.app.add_handler(MessageHandler(filters.Regex(r'^-блэклист|^-чс'), self.cmd_remove_blacklist))
        self.app.add_handler(CommandHandler("блэклист", self.cmd_show_blacklist))
        
        # ===== ЭКОНОМИКА =====
        self.app.add_handler(CommandHandler("daily", self.cmd_daily))
        self.app.add_handler(CommandHandler("weekly", self.cmd_weekly))
        self.app.add_handler(CommandHandler("streak", self.cmd_streak))
        self.app.add_handler(CommandHandler("shop", self.cmd_shop))
        self.app.add_handler(CommandHandler("buy", self.cmd_buy))
        self.app.add_handler(CommandHandler("pay", self.cmd_pay))
        self.app.add_handler(CommandHandler("balance", self.cmd_balance))
        self.app.add_handler(CommandHandler("work", self.cmd_work))
        self.app.add_handler(CommandHandler("donate", self.cmd_donate))
        self.app.add_handler(CommandHandler("vip", self.cmd_buy_vip))
        self.app.add_handler(CommandHandler("premium", self.cmd_buy_premium))
        
        # ===== ИГРЫ =====
        self.app.add_handler(CommandHandler("games", self.cmd_games))
        self.app.add_handler(CommandHandler("dice", self.cmd_dice))
        self.app.add_handler(CommandHandler("rr", self.cmd_russian_roulette))
        self.app.add_handler(CommandHandler("roulette", self.cmd_roulette))
        self.app.add_handler(CommandHandler("slots", self.cmd_slots))
        self.app.add_handler(CommandHandler("rps", self.cmd_rps))
        self.app.add_handler(CommandHandler("saper", self.cmd_saper))
        self.app.add_handler(CommandHandler("guess", self.cmd_guess))
        self.app.add_handler(CommandHandler("bulls", self.cmd_bulls))
        
        # ===== МАФИЯ =====
        self.app.add_handler(CommandHandler("mafia", self.cmd_mafia))
        self.app.add_handler(CommandHandler("mafia_start", self.cmd_mafia_start))
        self.app.add_handler(CommandHandler("mafia_join", self.cmd_mafia_join))
        self.app.add_handler(CommandHandler("mafia_leave", self.cmd_mafia_leave))
        self.app.add_handler(CommandHandler("mafia_roles", self.cmd_mafia_roles))
        self.app.add_handler(CommandHandler("mafia_rules", self.cmd_mafia_rules))
        self.app.add_handler(CommandHandler("mafia_stats", self.cmd_mafia_stats))
        self.app.add_handler(MessageHandler(filters.Regex(r'^голосовать '), self.cmd_mafia_vote))
        
        # ===== РАЗВЛЕЧЕНИЯ =====
        self.app.add_handler(CommandHandler("joke", self.cmd_joke))
        self.app.add_handler(CommandHandler("fact", self.cmd_fact))
        self.app.add_handler(CommandHandler("quote", self.cmd_quote))
        self.app.add_handler(CommandHandler("whoami", self.cmd_whoami))
        self.app.add_handler(CommandHandler("advice", self.cmd_advice))
        self.app.add_handler(CommandHandler("choose", self.cmd_choose))
        self.app.add_handler(CommandHandler("random", self.cmd_random))
        self.app.add_handler(CommandHandler("coin", self.cmd_coin))
        
        # ===== ПОЛЕЗНОЕ =====
        self.app.add_handler(CommandHandler("weather", self.cmd_weather))
        self.app.add_handler(CommandHandler("time", self.cmd_time))
        self.app.add_handler(CommandHandler("date", self.cmd_date))
        self.app.add_handler(CommandHandler("calc", self.cmd_calc))
        self.app.add_handler(CommandHandler("ping", self.cmd_ping))
        self.app.add_handler(CommandHandler("uptime", self.cmd_uptime))
        self.app.add_handler(CommandHandler("info", self.cmd_info))
        
        # ===== ОБРАБОТЧИКИ =====
        self.app.add_handler(CallbackQueryHandler(self.button_callback))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, self.handle_new_members))
        self.app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, self.handle_left_member))
        
        self.app.add_error_handler(self.error_handler)
        
        logger.info(f"✅ Зарегистрировано обработчиков: {len(self.app.handlers)}")
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Ошибка: {context.error}")

    # ===== ОСНОВНЫЕ КОМАНДЫ =====
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id, user.first_name)
        
        text = (
            s.header("СПЕКТР") + "\n"
            f"👋 **Привет, {user.first_name}!**\n"
            f"Я — **Спектр**, твой официальный помощник.\n\n"
            f"{s.section('ТВОЙ ПРОФИЛЬ')}"
            f"{s.stat('Монеты', f'{user_data['coins']} 💰')}\n"
            f"{s.stat('Уровень', user_data['level'])}\n"
            f"{s.stat('Ранг', self.get_role_emoji(user_data['rank']) + ' ' + user_data['rank_name'])}\n\n"
            f"{s.section('ЧТО Я УМЕЮ')}"
            f"{s.item('🎮 Игры: мафия, рулетка, кости, КНБ, сапёр')}\n"
            f"{s.item('🤖 AI общение (дерзкий, со сленгом)')}\n"
            f"{s.item('💰 Экономика, донат, VIP')}\n"
            f"{s.item('⚙️ Модерация (5 рангов)')}\n"
            f"{s.item('👥 Кланы, отношения, браки')}\n\n"
            f"{s.section('БЫСТРЫЙ СТАРТ')}"
            f"{s.cmd('profile', 'профиль')}\n"
            f"{s.cmd('games', 'все игры')}\n"
            f"{s.cmd('daily', 'бонус')}\n"
            f"{s.cmd('help', 'все команды')}\n\n"
            f"👑 **Владелец:** {OWNER_USERNAME}"
        )
        
        await update.message.reply_text(text, reply_markup=kb.main(), parse_mode="Markdown")
        self.db.log_action(user_data['id'], 'start')
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            s.header("СПРАВКА") + "\n"
            f"{s.section('ОСНОВНЫЕ')}"
            f"{s.cmd('start', 'начать работу')}\n"
            f"{s.cmd('menu', 'главное меню')}\n"
            f"{s.cmd('profile', 'профиль')}\n"
            f"{s.cmd('stats', 'статистика')}\n"
            f"{s.cmd('top', 'топ игроков')}\n"
            f"{s.cmd('id', 'узнать свой ID')}\n\n"
            
            f"{s.section('МОДЕРАЦИЯ (5 РАНГОВ)')}"
            f"{s.cmd('+Модер @user', '1 ранг (Младший модератор)')}\n"
            f"{s.cmd('+Модер 2 @user', '2 ранг (Старший модератор)')}\n"
            f"{s.cmd('+Модер 3 @user', '3 ранг (Младший админ)')}\n"
            f"{s.cmd('+Модер 4 @user', '4 ранг (Старший админ)')}\n"
            f"{s.cmd('+Модер 5 @user', '5 ранг (Создатель)')}\n"
            f"{s.cmd('повысить @user', 'повысить на 1 ранг')}\n"
            f"{s.cmd('понизить @user', 'понизить на 1 ранг')}\n"
            f"{s.cmd('снять @user', 'снять модератора')}\n"
            f"{s.cmd('снять вышедших', 'снять всех вышедших')}\n"
            f"{s.cmd('!снять всех', 'снять всех модераторов')}\n"
            f"{s.cmd('кто админ', 'список администрации')}\n\n"
            
            f"{s.section('БАНЫ И ПРЕДУПРЕЖДЕНИЯ')}"
            f"{s.cmd('варн @user [причина]', 'выдать предупреждение')}\n"
            f"{s.cmd('варны @user', 'список предупреждений')}\n"
            f"{s.cmd('снять варн @user', 'снять последнее предупреждение')}\n"
            f"{s.cmd('мут @user 30м [причина]', 'заглушить')}\n"
            f"{s.cmd('мутлист', 'список замученных')}\n"
            f"{s.cmd('размут @user', 'снять мут')}\n"
            f"{s.cmd('бан @user [причина]', 'заблокировать')}\n"
            f"{s.cmd('банлист', 'список забаненных')}\n"
            f"{s.cmd('разбан @user', 'разблокировать')}\n"
            f"{s.cmd('кик @user', 'исключить из чата')}\n\n"
            
            f"{s.section('ЧИСТКА ЧАТА')}"
            f"{s.cmd('чистка 50', 'удалить 50 сообщений')}\n"
            f"{s.cmd('чистка всё', 'удалить все сообщения')}\n"
            f"{s.cmd('чистка ботов', 'удалить сообщения ботов')}\n"
            f"{s.cmd('чистка мат', 'удалить сообщения с матом')}\n\n"
            
            f"{s.section('НАСТРОЙКИ ЧАТА')}"
            f"{s.cmd('+приветствие Текст', 'установить приветствие')}\n"
            f"{s.cmd('+правила Текст', 'установить правила')}\n"
            f"{s.cmd('правила', 'показать правила')}\n"
            f"{s.cmd('-приветствие', 'удалить приветствие')}\n"
            f"{s.cmd('капча on/off', 'включить капчу')}\n"
            f"{s.cmd('ссылки on/off', 'запретить ссылки')}\n\n"
            
            f"{s.section('ЧЕРНЫЙ СПИСОК')}"
            f"{s.cmd('+блэклист слово', 'добавить слово')}\n"
            f"{s.cmd('-блэклист слово', 'удалить слово')}\n"
            f"{s.cmd('блэклист', 'показать список')}\n\n"
            
            f"{s.section('ЭКОНОМИКА')}"
            f"{s.cmd('daily', 'ежедневный бонус')}\n"
            f"{s.cmd('weekly', 'недельный бонус')}\n"
            f"{s.cmd('streak', 'текущий стрик')}\n"
            f"{s.cmd('shop', 'магазин')}\n"
            f"{s.cmd('buy [предмет]', 'купить')}\n"
            f"{s.cmd('pay @user сумма', 'перевести монеты')}\n"
            f"{s.cmd('balance', 'баланс')}\n"
            f"{s.cmd('work', 'работать')}\n"
            f"{s.cmd('donate', 'привилегии')}\n"
            f"{s.cmd('vip', 'купить VIP')}\n"
            f"{s.cmd('premium', 'купить PREMIUM')}\n\n"
            
            f"{s.section('ИГРЫ')}"
            f"{s.cmd('games', 'список игр')}\n"
            f"{s.cmd('mafia', 'мафия')}\n"
            f"{s.cmd('rr [ставка]', 'русская рулетка')}\n"
            f"{s.cmd('dice [ставка]', 'кости')}\n"
            f"{s.cmd('roulette [ставка] [цвет]', 'рулетка')}\n"
            f"{s.cmd('slots [ставка]', 'слоты')}\n"
            f"{s.cmd('rps', 'камень-ножницы-бумага')}\n"
            f"{s.cmd('saper', 'сапёр')}\n"
            f"{s.cmd('guess [число]', 'угадай число')}\n"
            f"{s.cmd('bulls [число]', 'быки и коровы')}\n\n"
            
            f"{s.section('РАЗВЛЕЧЕНИЯ')}"
            f"{s.cmd('joke', 'случайная шутка')}\n"
            f"{s.cmd('fact', 'интересный факт')}\n"
            f"{s.cmd('quote', 'цитата')}\n"
            f"{s.cmd('whoami', 'кто я сегодня?')}\n"
            f"{s.cmd('advice', 'совет')}\n"
            f"{s.cmd('choose а б в', 'выбрать из вариантов')}\n"
            f"{s.cmd('random 1 100', 'случайное число')}\n"
            f"{s.cmd('coin', 'монетка')}\n\n"
            
            f"{s.section('ПОЛЕЗНОЕ')}"
            f"{s.cmd('weather [город]', 'погода')}\n"
            f"{s.cmd('time', 'время')}\n"
            f"{s.cmd('date', 'дата')}\n"
            f"{s.cmd('calc 2+2', 'калькулятор')}\n"
            f"{s.cmd('ping', 'проверка бота')}\n"
            f"{s.cmd('uptime', 'время работы')}\n"
            f"{s.cmd('info', 'о боте')}\n\n"
            
            f"👑 **Владелец:** {OWNER_USERNAME}"
        )
        
        await update.message.reply_text(text, reply_markup=kb.back(), parse_mode="Markdown")
    
    async def cmd_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            s.header("ГЛАВНОЕ МЕНЮ") + "\nВыберите раздел:",
            reply_markup=kb.main(),
            parse_mode="Markdown"
        )
    
    async def cmd_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        display_name = user_data.get('nickname') or user.first_name
        title = user_data.get('title', '')
        motto = user_data.get('motto', 'Нет девиза')
        
        vip_status = "✅ VIP" if self.db.is_vip(user_data['id']) else "❌"
        premium_status = "✅ PREMIUM" if self.db.is_premium(user_data['id']) else "❌"
        
        exp_needed = user_data['level'] * 100
        exp_progress = s.progress(user_data['exp'], exp_needed)
        
        warns = "🔴" * user_data['warns'] + "⚪" * (3 - user_data['warns'])
        
        text = (
            s.header("ПРОФИЛЬ") + "\n"
            f"**{display_name}** {title}\n"
            f"_{motto}_\n\n"
            f"{s.section('ХАРАКТЕРИСТИКИ')}"
            f"{s.stat('Ранг', self.get_role_emoji(user_data['rank']) + ' ' + user_data['rank_name'])}\n"
            f"{s.stat('Уровень', user_data['level'])}\n"
            f"{s.stat('Опыт', exp_progress)}\n"
            f"{s.stat('Монеты', f'{user_data['coins']} 💰')}\n"
            f"{s.stat('Алмазы', f'{user_data['diamonds']} 💎')}\n"
            f"{s.stat('Энергия', f'{user_data['energy']}/100 ⚡')}\n\n"
            f"{s.section('СТАТИСТИКА')}"
            f"{s.stat('Сообщений', user_data['messages_count'])}\n"
            f"{s.stat('Команд', user_data['commands_used'])}\n"
            f"{s.stat('Репутация', user_data['reputation'])}\n"
            f"{s.stat('Предупреждения', warns)}\n\n"
            f"{s.section('СТАТУС')}"
            f"{s.item(f'VIP: {vip_status}')}\n"
            f"{s.item(f'PREMIUM: {premium_status}')}\n"
            f"{s.item(f'Пол: {user_data['gender']}')}\n"
            f"{s.item(f'Город: {user_data['city']}')}\n"
            f"{s.item(f'ID: {s.code(str(user.id))}')}"
        )
        
        await update.message.reply_text(text, reply_markup=kb.back(), parse_mode="Markdown")

    # ===== КОМАНДЫ МОДЕРАЦИИ (5 РАНГОВ) =====
    
    async def cmd_set_rank(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установка ранга модератора"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        # Проверка прав (нужен ранг 4+)
        if user_data['rank'] < 4 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав. Нужен ранг 4+"))
            return
        
        # Парсим команду
        match = re.search(r'(?:\+Модер|!модер|повысить)\s*(\d+)?\s*(?:@(\S+)|(\d+))?', text)
        if not match:
            await update.message.reply_text(s.error("❌ Неверный формат. Пример: +Модер 2 @user"))
            return
        
        target_rank = int(match.group(1)) if match.group(1) else 1
        if target_rank > 5:
            target_rank = 5
        
        # Получаем цель
        target_user = None
        if update.message.reply_to_message:
            target_id = update.message.reply_to_message.from_user.id
            target_user = self.db.get_user_by_id(self.db.get_user(target_id)['id'])
        elif match.group(2):
            target_user = self.db.get_user_by_username(match.group(2))
        elif match.group(3):
            target_user = self.db.get_user_by_id(int(match.group(3)))
        
        if not target_user:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        # Проверка, что цель не выше рангом
        if target_user['rank'] >= user_data['rank'] and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Нельзя назначить ранг выше своего"))
            return
        
        # Устанавливаем ранг
        self.db.set_rank(target_user['id'], target_rank, user_data['id'])
        
        rank_info = RANKS[target_rank]
        await update.message.reply_text(
            f"{s.success('Ранг назначен!')}\n\n"
            f"{s.item(f'Пользователь: {target_user["first_name"]}')}\n"
            f"{s.item(f'Ранг: {rank_info["emoji"]} {rank_info["name"]} ({target_rank})')}",
            parse_mode="Markdown"
        )
    
    async def cmd_remove_rank(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Снятие модератора"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 4 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав"))
            return
        
        # Получаем цель
        target_user = None
        if update.message.reply_to_message:
            target_id = update.message.reply_to_message.from_user.id
            target_user = self.db.get_user_by_id(self.db.get_user(target_id)['id'])
        else:
            username = text.replace('снять', '').replace('разжаловать', '').strip().replace('@', '')
            if username:
                target_user = self.db.get_user_by_username(username)
        
        if not target_user:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        if target_user['rank'] >= user_data['rank'] and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Нельзя снять модератора выше рангом"))
            return
        
        self.db.set_rank(target_user['id'], 0, user_data['id'])
        await update.message.reply_text(
            f"{s.success('Модератор снят!')}\n\n"
            f"{s.item(f'Пользователь: {target_user["first_name"]}')}\n"
            f"{s.item('Теперь: 👤 Участник')}",
            parse_mode="Markdown"
        )
    
    async def cmd_remove_all_ranks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """!Снять всех - снять всех модераторов"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data['rank'] < 5 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Только для создателя"))
            return
        
        # Получаем всех модераторов (ранг 1-5)
        self.db.c.execute("SELECT id FROM users WHERE rank > 0")
        mods = self.db.c.fetchall()
        
        for mod_id in mods:
            self.db.set_rank(mod_id[0], 0, user_data['id'])
        
        await update.message.reply_text(
            s.success(f"✅ Снято модераторов: {len(mods)}"),
            parse_mode="Markdown"
        )
    
    async def cmd_who_admins(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Кто админ - список администрации"""
        self.db.c.execute("SELECT first_name, username, rank, rank_name FROM users WHERE rank > 0 ORDER BY rank DESC")
        admins = self.db.c.fetchall()
        
        if not admins:
            await update.message.reply_text(s.info("👥 В чате нет администраторов"))
            return
        
        text = s.header("АДМИНИСТРАЦИЯ") + "\n\n"
        for admin in admins:
            name = admin[0]
            username = f" (@{admin[1]})" if admin[1] else ""
            rank_emoji = RANKS[admin[2]]["emoji"]
            text += f"{s.item(f'{rank_emoji} {name}{username} — {admin[3]}')}\n"
        
        await update.message.reply_text(text, parse_mode="Markdown")

    # ===== СИСТЕМА БАНОВ И ПРЕДУПРЕЖДЕНИЙ =====
    
    async def cmd_warn(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выдать предупреждение"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 1 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав. Нужен ранг 1+"))
            return
        
        # Получаем цель
        target_user = None
        reason = "Нарушение"
        
        if update.message.reply_to_message:
            target_id = update.message.reply_to_message.from_user.id
            target_user = self.db.get_user_by_id(self.db.get_user(target_id)['id'])
            # Причина может быть в следующей строке или в тексте
            parts = text.split('\n', 1)
            if len(parts) > 1 and parts[1].strip():
                reason = parts[1].strip()
        else:
            # Парсим формат: варн @user причина
            match = re.search(r'(?:варн|пред)\s+@?(\S+)(?:\s+(.+))?', text, re.IGNORECASE)
            if match:
                username = match.group(1)
                target_user = self.db.get_user_by_username(username)
                if match.group(2):
                    reason = match.group(2)
        
        if not target_user:
            await update.message.reply_text(s.error("❌ Пользователь не найден. Ответьте на сообщение или укажите @username"))
            return
        
        if target_user['rank'] >= user_data['rank'] and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Нельзя выдать предупреждение модератору выше рангом"))
            return
        
        warns = self.db.add_warn(target_user['id'], user_data['id'], reason)
        
        text = (
            s.header("ПРЕДУПРЕЖДЕНИЕ") + "\n"
            f"{s.item(f'Пользователь: {target_user["first_name"]}')}\n"
            f"{s.item(f'Предупреждений: {warns}/3')}\n"
            f"{s.item(f'Причина: {reason}')}"
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")
        
        # Автоматические наказания
        if warns >= 3:
            self.db.mute_user(target_user['id'], 60, user_data['id'], "3 предупреждения")
            await update.message.reply_text(s.warning(f"⚠️ Достигнут лимит! {target_user['first_name']} замучен на 1 час"))
        if warns >= 5:
            self.db.ban_user(target_user['id'], user_data['id'], "5 предупреждений")
            await update.message.reply_text(s.error(f"🔨 {target_user['first_name']} забанен за 5 предупреждений"))
    
    async def cmd_warns(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список предупреждений"""
        args = context.args
        if not args:
            await update.message.reply_text(s.error("Укажите пользователя: /варны @user"))
            return
        
        username = args[0].replace('@', '')
        target = self.db.get_user_by_username(username)
        
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        warns_list = self.db.get_warns(target['id'])
        target_name = target.get('nickname') or target['first_name']
        
        if not warns_list:
            await update.message.reply_text(s.info(f"У {target_name} нет предупреждений"))
            return
        
        text = s.header(f"ПРЕДУПРЕЖДЕНИЯ: {target_name}") + "\n\n"
        for warn in warns_list:
            admin = self.db.get_user_by_id(warn['admin_id'])
            admin_name = admin.get('first_name', 'Система') if admin else 'Система'
            date = datetime.datetime.fromisoformat(warn['date']).strftime("%d.%m.%Y %H:%M")
            text += (
                f"**ID: {warn['id']}**\n"
                f"{s.item(f'Причина: {warn['reason']}')}\n"
                f"{s.item(f'Админ: {admin_name}')}\n"
                f"{s.item(f'Дата: {date}')}\n\n"
            )
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_unwarn(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Снять предупреждение"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 1 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав"))
            return
        
        # Получаем цель
        target_user = None
        if update.message.reply_to_message:
            target_id = update.message.reply_to_message.from_user.id
            target_user = self.db.get_user_by_id(self.db.get_user(target_id)['id'])
        else:
            match = re.search(r'(?:снять_варн|-варн)\s+@?(\S+)', text, re.IGNORECASE)
            if match:
                username = match.group(1)
                target_user = self.db.get_user_by_username(username)
        
        if not target_user:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        removed = self.db.remove_last_warn(target_user['id'], user_data['id'])
        target_name = target_user.get('nickname') or target_user['first_name']
        
        if not removed:
            await update.message.reply_text(s.info(f"У {target_name} нет предупреждений"))
            return
        
        await update.message.reply_text(s.success(f"✅ Предупреждение снято с {target_name}"))
    
    async def cmd_mute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Заглушить пользователя"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 2 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав. Нужен ранг 2+"))
            return
        
        # Парсим: мут @user 30м спам
        match = re.search(r'мут\s+@?(\S+)(?:\s+(\d+)([мчд]))?(?:\s+(.+))?', text, re.IGNORECASE)
        if not match:
            await update.message.reply_text(s.error("❌ Пример: мут @user 30м спам"))
            return
        
        username = match.group(1)
        amount = int(match.group(2)) if match.group(2) else 60
        unit = match.group(3) if match.group(3) else 'м'
        reason = match.group(4) if match.group(4) else "Нарушение"
        
        # Конвертируем в минуты
        if unit == 'ч':
            minutes = amount * 60
        elif unit == 'д':
            minutes = amount * 1440
        else:  # минуты
            minutes = amount
        
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        if target['rank'] >= user_data['rank'] and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Нельзя замутить модератора выше рангом"))
            return
        
        until = self.db.mute_user(target['id'], minutes, user_data['id'], reason)
        until_str = until.strftime("%d.%m.%Y %H:%M")
        
        text = (
            s.header("МУТ") + "\n"
            f"{s.item(f'Пользователь: {target["first_name"]}')}\n"
            f"{s.item(f'Срок: {amount}{unit} ({minutes} мин)')}\n"
            f"{s.item(f'До: {until_str}')}\n"
            f"{s.item(f'Причина: {reason}')}"
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_mutelist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список замученных"""
        self.db.c.execute("SELECT id, first_name, username, mute_until FROM users WHERE mute_until > ?", 
                         (datetime.datetime.now().isoformat(),))
        muted = self.db.c.fetchall()
        
        if not muted:
            await update.message.reply_text(s.info("Нет пользователей в муте"))
            return
        
        text = s.header("СПИСОК ЗАМУЧЕННЫХ") + "\n\n"
        for user in muted[:10]:
            until = datetime.datetime.fromisoformat(user[3]).strftime("%d.%m.%Y %H:%M")
            name = user[1]
            text += f"{s.item(f'{name} — до {until}')}\n"
        
        if len(muted) > 10:
            text += f"\n... и еще {len(muted) - 10}"
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_unmute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Снять мут"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 2 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав"))
            return
        
        username = text.replace('размут', '').replace('@', '').strip()
        if not username:
            if update.message.reply_to_message:
                target_id = update.message.reply_to_message.from_user.id
                target = self.db.get_user_by_id(self.db.get_user(target_id)['id'])
            else:
                await update.message.reply_text(s.error("❌ Укажите пользователя: размут @user"))
                return
        else:
            target = self.db.get_user_by_username(username)
        
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        if not self.db.is_muted(target['id']):
            await update.message.reply_text(s.info("Пользователь не в муте"))
            return
        
        self.db.unmute_user(target['id'], user_data['id'])
        await update.message.reply_text(s.success(f"✅ Мут снят с {target['first_name']}"))
    
    async def cmd_ban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Заблокировать пользователя"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 2 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав. Нужен ранг 2+"))
            return
        
        # Парсим: бан @user спам
        match = re.search(r'бан\s+@?(\S+)(?:\s+(.+))?', text, re.IGNORECASE)
        if not match:
            await update.message.reply_text(s.error("❌ Пример: бан @user спам"))
            return
        
        username = match.group(1)
        reason = match.group(2) if match.group(2) else "Нарушение"
        
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        if target['rank'] >= user_data['rank'] and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Нельзя забанить модератора выше рангом"))
            return
        
        self.db.ban_user(target['id'], user_data['id'], reason)
        
        text = (
            s.header("БЛОКИРОВКА") + "\n"
            f"{s.item(f'Пользователь: {target["first_name"]}')}\n"
            f"{s.item(f'Причина: {reason}')}"
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")
        
        # Попытка кикнуть из чата
        try:
            await update.effective_chat.ban_member(target['telegram_id'])
        except:
            pass
    
    async def cmd_banlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список забаненных"""
        bans = self.db.get_banlist()
        
        if not bans:
            await update.message.reply_text(s.info("Список забаненных пуст"))
            return
        
        text = s.header("СПИСОК ЗАБАНЕННЫХ") + "\n\n"
        for ban in bans:
            name = ban.get('first_name', 'Неизвестно')
            username = f" (@{ban['username']})" if ban['username'] else ""
            text += f"{s.item(f'{name}{username}')}\n"
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_unban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Разблокировать пользователя"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 2 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав"))
            return
        
        username = text.replace('разбан', '').replace('@', '').strip()
        target = self.db.get_user_by_username(username)
        
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        if not self.db.is_banned(target['id']):
            await update.message.reply_text(s.info("Пользователь не забанен"))
            return
        
        self.db.unban_user(target['id'], user_data['id'])
        await update.message.reply_text(s.success(f"✅ Бан снят с {target['first_name']}"))
    
    async def cmd_kick(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Исключить пользователя (без бана)"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 1 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав"))
            return
        
        username = text.replace('кик', '').replace('@', '').strip()
        target = self.db.get_user_by_username(username)
        
        if not target:
            if update.message.reply_to_message:
                target_id = update.message.reply_to_message.from_user.id
                target = self.db.get_user_by_id(self.db.get_user(target_id)['id'])
            else:
                await update.message.reply_text(s.error("❌ Пользователь не найден"))
                return
        
        try:
            await update.effective_chat.ban_member(target['telegram_id'])
            await update.effective_chat.unban_member(target['telegram_id'])
            await update.message.reply_text(s.success(f"✅ {target['first_name']} исключен"))
        except Exception as e:
            await update.message.reply_text(s.error(f"❌ Ошибка: {e}"))

    # ===== ЧИСТКА ЧАТА =====
    
    async def cmd_clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Очистка сообщений"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 2 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав. Нужен ранг 2+"))
            return
        
        # Парсим количество
        match = re.search(r'чистка\s*(\d+|всё|все|ботов|файлов|ссылки|мат|спам)?', text, re.IGNORECASE)
        if not match:
            await update.message.reply_text(s.error("❌ Пример: чистка 50"))
            return
        
        param = match.group(1) if match.group(1) else "50"
        
        if param == "всё" or param == "все":
            if user_data['rank'] < 5:
                await update.message.reply_text(s.error("⛔️ Чистка всех сообщений только для создателя"))
                return
            await update.message.reply_text(s.success("🧹 Удаляю все сообщения..."))
            # Здесь нужна логика для массовой очистки
        
        elif param == "ботов":
            await update.message.reply_text(s.success("🧹 Удаляю сообщения ботов..."))
        
        elif param == "файлов":
            await update.message.reply_text(s.success("🧹 Удаляю файлы..."))
        
        elif param == "ссылки":
            await update.message.reply_text(s.success("🧹 Удаляю сообщения со ссылками..."))
        
        elif param == "мат":
            await update.message.reply_text(s.success("🧹 Удаляю сообщения с матом..."))
        
        elif param == "спам":
            await update.message.reply_text(s.success("🧹 Удаляю спам..."))
        
        else:
            try:
                amount = int(param)
                if amount > 100:
                    amount = 100
                await update.message.reply_text(f"🧹 Удаляю {amount} сообщений...")
                # Здесь логика очистки
            except:
                await update.message.reply_text(s.error("❌ Неверное количество"))
    
    # ===== НАСТРОЙКИ ЧАТА =====
    
    async def cmd_set_welcome(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установить приветствие"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 2 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав"))
            return
        
        welcome_text = text.replace('+приветствие', '').strip()
        if not welcome_text:
            await update.message.reply_text(s.error("❌ Укажите текст приветствия"))
            return
        
        chat_id = update.effective_chat.id
        self.db.cursor.execute("INSERT OR REPLACE INTO chat_settings (chat_id, welcome) VALUES (?, ?)",
                              (chat_id, welcome_text))
        self.db.conn.commit()
        
        await update.message.reply_text(s.success("✅ Приветствие установлено"))
    
    async def cmd_set_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установить правила"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 2 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав"))
            return
        
        rules_text = text.replace('+правила', '').strip()
        if not rules_text:
            await update.message.reply_text(s.error("❌ Укажите текст правил"))
            return
        
        chat_id = update.effective_chat.id
        self.db.cursor.execute("INSERT OR REPLACE INTO chat_settings (chat_id, rules) VALUES (?, ?)",
                              (chat_id, rules_text))
        self.db.conn.commit()
        
        await update.message.reply_text(s.success("✅ Правила установлены"))
    
    async def cmd_show_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать правила"""
        chat_id = update.effective_chat.id
        self.db.cursor.execute("SELECT rules FROM chat_settings WHERE chat_id = ?", (chat_id,))
        row = self.db.cursor.fetchone()
        
        if row and row[0]:
            await update.message.reply_text(
                f"{s.header('ПРАВИЛА ЧАТА')}\n\n{row[0]}",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(s.info("Правила не установлены"))
    
    async def cmd_remove_welcome(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Удалить приветствие"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data['rank'] < 2 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав"))
            return
        
        chat_id = update.effective_chat.id
        self.db.cursor.execute("UPDATE chat_settings SET welcome = NULL WHERE chat_id = ?", (chat_id,))
        self.db.conn.commit()
        
        await update.message.reply_text(s.success("✅ Приветствие удалено"))
    
    async def cmd_set_captcha(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Включить/выключить капчу"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 3 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав"))
            return
        
        match = re.search(r'капча\s+(on|off)', text, re.IGNORECASE)
        if not match:
            await update.message.reply_text(s.error("❌ Пример: капча on/off"))
            return
        
        value = 1 if match.group(1).lower() == 'on' else 0
        chat_id = update.effective_chat.id
        
        self.db.cursor.execute("UPDATE chat_settings SET captcha = ? WHERE chat_id = ?", (value, chat_id))
        self.db.conn.commit()
        
        await update.message.reply_text(s.success(f"✅ Капча: {match.group(1)}"))

    # ===== ЧЕРНЫЙ СПИСОК =====
    
    async def cmd_add_blacklist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Добавить слово в черный список"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 2 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав. Нужен ранг 2+"))
            return
        
        word = re.sub(r'^\+блэклист|\+чс', '', text, flags=re.IGNORECASE).strip()
        if not word:
            await update.message.reply_text(s.error("❌ Укажите слово: +блэклист слово"))
            return
        
        if self.db.add_to_blacklist(word, user_data['id']):
            await update.message.reply_text(s.success(f"✅ Слово '{word}' добавлено в черный список"))
        else:
            await update.message.reply_text(s.error(f"❌ Слово '{word}' уже в списке"))
    
    async def cmd_remove_blacklist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Удалить слово из черного списка"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 2 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав"))
            return
        
        word = re.sub(r'^-блэклист|-чс', '', text, flags=re.IGNORECASE).strip()
        if not word:
            await update.message.reply_text(s.error("❌ Укажите слово: -блэклист слово"))
            return
        
        if self.db.remove_from_blacklist(word, user_data['id']):
            await update.message.reply_text(s.success(f"✅ Слово '{word}' удалено из черного списка"))
        else:
            await update.message.reply_text(s.error(f"❌ Слово '{word}' не найдено"))
    
    async def cmd_show_blacklist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать черный список"""
        blacklist = self.db.get_blacklist()
        
        if not blacklist:
            await update.message.reply_text(s.info("Черный список пуст"))
            return
        
        text = s.header("ЧЕРНЫЙ СПИСОК") + "\n\n"
        for word in blacklist[:20]:
            text += f"{s.item(word)}\n"
        
        if len(blacklist) > 20:
            text += f"\n... и еще {len(blacklist) - 20}"
        
        await update.message.reply_text(text, parse_mode="Markdown")

    # ===== ЭКОНОМИКА =====
    
    async def cmd_daily(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ежедневный бонус"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data.get('last_daily'):
            last = datetime.datetime.fromisoformat(user_data['last_daily'])
            if (datetime.datetime.now() - last).seconds < DAILY_COOLDOWN:
                remain = DAILY_COOLDOWN - (datetime.datetime.now() - last).seconds
                hours = remain // 3600
                minutes = (remain % 3600) // 60
                await update.message.reply_text(s.warning(f"⏳ Бонус через {hours}ч {minutes}м"))
                return
        
        streak = self.db.add_daily_streak(user_data['id'])
        
        # Базовая награда
        coins = random.randint(100, 300)
        exp = random.randint(20, 60)
        energy = 20
        
        # Множитель от стрика
        coins = int(coins * (1 + min(streak, 30) * 0.05))
        exp = int(exp * (1 + min(streak, 30) * 0.05))
        
        # Множитель от привилегий
        if self.db.is_vip(user_data['id']):
            coins = int(coins * 1.5)
            exp = int(exp * 1.5)
            energy = int(energy * 1.5)
        if self.db.is_premium(user_data['id']):
            coins = int(coins * 2)
            exp = int(exp * 2)
            energy = int(energy * 2)
        
        self.db.add_coins(user_data['id'], coins)
        self.db.add_exp(user_data['id'], exp)
        self.db.add_energy(user_data['id'], energy)
        
        text = (
            s.header("ЕЖЕДНЕВНЫЙ БОНУС") + "\n"
            f"{s.item(f'🔥 Стрик: {streak} дней')}\n"
            f"{s.item(f'💰 Монеты: +{coins}')}\n"
            f"{s.item(f'✨ Опыт: +{exp}')}\n"
            f"{s.item(f'⚡ Энергия: +{energy}')}\n\n"
            f"{s.info('Заходи завтра!')}"
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")
        self.db.log_action(user_data['id'], 'daily', f'+{coins}💰')
    
    async def cmd_weekly(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Недельный бонус"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data.get('last_weekly'):
            last = datetime.datetime.fromisoformat(user_data['last_weekly'])
            if (datetime.datetime.now() - last).days < 7:
                await update.message.reply_text(s.warning("⏳ Бонус раз в неделю!"))
                return
        
        coins = random.randint(1000, 3000)
        diamonds = random.randint(10, 30)
        exp = random.randint(200, 500)
        
        if self.db.is_vip(user_data['id']):
            coins = int(coins * 1.5)
            diamonds = int(diamonds * 1.5)
            exp = int(exp * 1.5)
        if self.db.is_premium(user_data['id']):
            coins = int(coins * 2)
            diamonds = int(diamonds * 2)
            exp = int(exp * 2)
        
        self.db.add_coins(user_data['id'], coins)
        self.db.add_diamonds(user_data['id'], diamonds)
        self.db.add_exp(user_data['id'], exp)
        self.db.update_user(user_data['id'], last_weekly=datetime.datetime.now().isoformat())
        
        text = (
            s.header("НЕДЕЛЬНЫЙ БОНУС") + "\n"
            f"{s.item(f'💰 Монеты: +{coins}')}\n"
            f"{s.item(f'💎 Алмазы: +{diamonds}')}\n"
            f"{s.item(f'✨ Опыт: +{exp}')}\n\n"
            f"{s.info('Через неделю снова!')}"
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_streak(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Текущий стрик"""
        user_data = self.db.get_user(update.effective_user.id)
        streak = user_data.get('daily_streak', 0)
        
        await update.message.reply_text(
            f"🔥 **Текущий стрик:** {streak} дней\n"
            f"📈 **Множитель:** x{1 + min(streak, 30) * 0.05:.2f}",
            parse_mode="Markdown"
        )
    
    async def cmd_shop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Магазин"""
        text = (
            s.header("МАГАЗИН") + "\n"
            f"{s.section('ЗЕЛЬЯ')}"
            f"{s.cmd('buy зелье здоровья', '50 💰 (❤️+30)')}\n"
            f"{s.cmd('buy большое зелье', '100 💰 (❤️+70)')}\n"
            f"{s.cmd('buy эликсир', '200 💰 (❤️+150)')}\n\n"
            f"{s.section('ОРУЖИЕ')}"
            f"{s.cmd('buy меч', '200 💰 (⚔️+10)')}\n"
            f"{s.cmd('buy легендарный меч', '500 💰 (⚔️+30)')}\n"
            f"{s.cmd('buy экскалибур', '1000 💰 (⚔️+50)')}\n\n"
            f"{s.section('БРОНЯ')}"
            f"{s.cmd('buy щит', '150 💰 (🛡️+5)')}\n"
            f"{s.cmd('buy доспехи', '400 💰 (🛡️+15)')}\n"
            f"{s.cmd('buy непробиваемая броня', '800 💰 (🛡️+30)')}\n\n"
            f"{s.section('ЭНЕРГИЯ')}"
            f"{s.cmd('buy энергетик', '30 💰 (⚡+20)')}\n"
            f"{s.cmd('buy батарейка', '80 💰 (⚡+50)')}\n"
            f"{s.cmd('buy атомный реактор', '200 💰 (⚡+100)')}\n\n"
            f"{s.section('ПРИВИЛЕГИИ')}"
            f"{s.cmd('vip', f'VIP статус ({VIP_PRICE} 💰)')}\n"
            f"{s.cmd('premium', f'PREMIUM статус ({PREMIUM_PRICE} 💰)')}"
        )
        
        await update.message.reply_text(text, reply_markup=kb.back(), parse_mode="Markdown")
    
    async def cmd_buy(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Купить предмет"""
        if not context.args:
            await update.message.reply_text(s.error("Что купить? /buy [предмет]"))
            return
        
        item = " ".join(context.args).lower()
        user_data = self.db.get_user(update.effective_user.id)
        
        items = {
            "зелье здоровья": {"price": 50, "heal": 30},
            "большое зелье": {"price": 100, "heal": 70},
            "эликсир": {"price": 200, "heal": 150},
            "меч": {"price": 200, "damage": 10},
            "легендарный меч": {"price": 500, "damage": 30},
            "экскалибур": {"price": 1000, "damage": 50},
            "щит": {"price": 150, "armor": 5},
            "доспехи": {"price": 400, "armor": 15},
            "непробиваемая броня": {"price": 800, "armor": 30},
            "энергетик": {"price": 30, "energy": 20},
            "батарейка": {"price": 80, "energy": 50},
            "атомный реактор": {"price": 200, "energy": 100}
        }
        
        if item not in items:
            await update.message.reply_text(s.error("❌ Такого товара нет"))
            return
        
        item_data = items[item]
        
        if user_data['coins'] < item_data['price']:
            await update.message.reply_text(s.error(f"❌ Недостаточно монет. Нужно {item_data['price']} 💰"))
            return
        
        self.db.add_coins(user_data['id'], -item_data['price'])
        
        if 'heal' in item_data:
            new_health = self.db.heal(user_data['id'], item_data['heal'])
            await update.message.reply_text(s.success(f"✅ Куплено: {item}\n❤️ Здоровье +{item_data['heal']} (теперь {new_health})"))
        elif 'damage' in item_data:
            new_damage = user_data['damage'] + item_data['damage']
            self.db.update_user(user_data['id'], damage=new_damage)
            await update.message.reply_text(s.success(f"✅ Куплено: {item}\n⚔️ Урон +{item_data['damage']} (теперь {new_damage})"))
        elif 'armor' in item_data:
            new_armor = user_data['armor'] + item_data['armor']
            self.db.update_user(user_data['id'], armor=new_armor)
            await update.message.reply_text(s.success(f"✅ Куплено: {item}\n🛡️ Броня +{item_data['armor']} (теперь {new_armor})"))
        elif 'energy' in item_data:
            new_energy = self.db.add_energy(user_data['id'], item_data['energy'])
            await update.message.reply_text(s.success(f"✅ Куплено: {item}\n⚡ Энергия +{item_data['energy']} (теперь {new_energy})"))
        
        self.db.log_action(user_data['id'], 'buy', item)
    
    async def cmd_pay(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Перевести монеты"""
        if len(context.args) < 2:
            await update.message.reply_text(s.error("Использование: /pay @user сумма"))
            return
        
        username = context.args[0].replace('@', '')
        try:
            amount = int(context.args[1])
        except:
            await update.message.reply_text(s.error("❌ Сумма должна быть числом"))
            return
        
        if amount <= 0:
            await update.message.reply_text(s.error("❌ Сумма должна быть больше 0"))
            return
        
        user_data = self.db.get_user(update.effective_user.id)
        
        if user_data['coins'] < amount:
            await update.message.reply_text(s.error(f"❌ Недостаточно монет. Баланс: {user_data['coins']} 💰"))
            return
        
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        if target['id'] == user_data['id']:
            await update.message.reply_text(s.error("❌ Нельзя перевести самому себе"))
            return
        
        self.db.add_coins(user_data['id'], -amount)
        self.db.add_coins(target['id'], amount)
        
        commission_text = ""
        if not self.db.is_premium(user_data['id']):
            commission = int(amount * 0.05)
            self.db.add_coins(user_data['id'], -commission)
            commission_text = f"\n{s.item(f'💸 Комиссия: {commission} (5%)')}"
        
        target_name = target.get('nickname') or target['first_name']
        
        text = (
            s.header("ПЕРЕВОД") + "\n"
            f"{s.item(f'Получатель: {target_name}')}\n"
            f"{s.item(f'Сумма: {amount} 💰')}{commission_text}\n\n"
            f"{s.success('Перевод выполнен!')}"
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")
        self.db.log_action(user_data['id'], 'pay', f"{amount}💰 -> {target['id']}")
    
    async def cmd_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Баланс"""
        user_data = self.db.get_user(update.effective_user.id)
        text = (
            s.header("БАЛАНС") + "\n"
            f"{s.stat('Монеты', f'{user_data['coins']} 💰')}\n"
            f"{s.stat('Алмазы', f'{user_data['diamonds']} 💎')}\n"
            f"{s.stat('Энергия', f'{user_data['energy']}/100 ⚡')}\n"
            f"{s.stat('Здоровье', f'{user_data['health']}/100 ❤️')}"
        )
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_work(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Работать"""
        user_data = self.db.get_user(update.effective_user.id)
        
        if user_data.get('last_work'):
            last = datetime.datetime.fromisoformat(user_data['last_work'])
            if (datetime.datetime.now() - last).seconds < 3600:
                remain = 3600 - (datetime.datetime.now() - last).seconds
                minutes = remain // 60
                await update.message.reply_text(s.warning(f"⏳ Работать можно через {minutes} минут"))
                return
        
        jobs = [
            ("Программист", 500, 100),
            ("Врач", 400, 80),
            ("Учитель", 300, 60),
            ("Строитель", 350, 70),
            ("Водитель", 320, 65),
            ("Продавец", 280, 55)
        ]
        
        job, coins, exp = random.choice(jobs)
        
        if self.db.is_vip(user_data['id']):
            coins = int(coins * 1.5)
            exp = int(exp * 1.5)
        if self.db.is_premium(user_data['id']):
            coins = int(coins * 2)
            exp = int(exp * 2)
        
        self.db.add_coins(user_data['id'], coins)
        self.db.add_exp(user_data['id'], exp)
        self.db.update_user(user_data['id'], last_work=datetime.datetime.now().isoformat())
        
        text = (
            s.header("РАБОТА") + "\n"
            f"{s.item(f'💼 Профессия: {job}')}\n"
            f"{s.item(f'💰 Зарплата: +{coins}')}\n"
            f"{s.item(f'✨ Опыт: +{exp}')}\n\n"
            f"{s.info('Работать можно раз в час')}"
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_donate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о привилегиях"""
        text = (
            s.header("ПРИВИЛЕГИИ") + "\n"
            f"{s.section('VIP СТАТУС')}"
            f"Цена: {VIP_PRICE} 💰 / {VIP_DAYS} дней\n"
            f"{s.item('⚔️ Урон +20%')}\n"
            f"{s.item('💰 Награда +50%')}\n"
            f"{s.item('🎁 Бонус +50%')}\n\n"
            f"{s.section('PREMIUM СТАТУС')}"
            f"Цена: {PREMIUM_PRICE} 💰 / {PREMIUM_DAYS} дней\n"
            f"{s.item('⚔️ Урон +50%')}\n"
            f"{s.item('💰 Награда +100%')}\n"
            f"{s.item('🎁 Бонус +100%')}\n"
            f"{s.item('🚫 Без комиссии')}\n"
            f"{s.item('✨ Особый статус')}\n\n"
            f"{s.cmd('vip', 'купить VIP')}\n"
            f"{s.cmd('premium', 'купить PREMIUM')}"
        )
        
        await update.message.reply_text(text, reply_markup=kb.back(), parse_mode="Markdown")
    
    async def cmd_buy_vip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Купить VIP"""
        user_data = self.db.get_user(update.effective_user.id)
        
        if user_data['coins'] < VIP_PRICE:
            await update.message.reply_text(s.error(f"❌ Нужно {VIP_PRICE} 💰"))
            return
        
        if self.db.is_vip(user_data['id']):
            await update.message.reply_text(s.error("❌ VIP уже активен"))
            return
        
        self.db.add_coins(user_data['id'], -VIP_PRICE)
        until = self.db.set_vip(user_data['id'], VIP_DAYS)
        date_str = until.strftime("%d.%m.%Y")
        
        await update.message.reply_text(
            f"{s.success('VIP АКТИВИРОВАН')}\n\n"
            f"{s.item('Срок: до ' + date_str)}",
            parse_mode="Markdown"
        )
        self.db.log_action(user_data['id'], 'buy_vip')
    
    async def cmd_buy_premium(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Купить PREMIUM"""
        user_data = self.db.get_user(update.effective_user.id)
        
        if user_data['coins'] < PREMIUM_PRICE:
            await update.message.reply_text(s.error(f"❌ Нужно {PREMIUM_PRICE} 💰"))
            return
        
        if self.db.is_premium(user_data['id']):
            await update.message.reply_text(s.error("❌ PREMIUM уже активен"))
            return
        
        self.db.add_coins(user_data['id'], -PREMIUM_PRICE)
        until = self.db.set_premium(user_data['id'], PREMIUM_DAYS)
        date_str = until.strftime("%d.%m.%Y")
        
        await update.message.reply_text(
            f"{s.success('PREMIUM АКТИВИРОВАН')}\n\n"
            f"{s.item('Срок: до ' + date_str)}",
            parse_mode="Markdown"
        )
        self.db.log_action(user_data['id'], 'buy_premium')

    # ===== ИГРЫ =====
    
    async def cmd_games(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Меню игр"""
        await update.message.reply_text(
            s.header("ИГРЫ") + "\nВыберите игру:",
            reply_markup=kb.games(),
            parse_mode="Markdown"
        )
    
    async def cmd_russian_roulette(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Русская рулетка"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        bet = 10
        if context.args:
            try:
                bet = int(context.args[0])
            except:
                await update.message.reply_text(s.error("❌ Ставка должна быть числом"))
                return
        
        if bet > user_data['coins']:
            await update.message.reply_text(s.error(f"❌ Недостаточно монет. Баланс: {user_data['coins']} 💰"))
            return
        
        if bet <= 0:
            await update.message.reply_text(s.error("❌ Ставка должна быть больше 0"))
            return
        
        # Отправляем гифку перезарядки револьвера
        try:
            await context.bot.send_animation(
                chat_id=update.effective_chat.id,
                animation=MAFIA_GIFS["revolver"]
            )
        except:
            pass
        
        # Крутим барабан
        chamber = random.randint(1, 6)
        shot = random.randint(1, 6)
        
        await asyncio.sleep(1)  # Эффект ожидания
        
        if chamber == shot:
            # Проигрыш
            self.db.add_coins(user_data['id'], -bet)
            self.db.update_user(user_data['id'], rr_losses=user_data.get('rr_losses', 0) + 1)
            
            text = (
                s.header("💀 РУССКАЯ РУЛЕТКА") + "\n"
                f"{s.item(f'Ставка: {bet} 💰')}\n"
                f"{s.item('Бах! Выстрел!')}\n\n"
                f"{s.error(f'ПРОИГРЫШ! -{bet} 💰')}"
            )
        else:
            # Выигрыш
            win = bet * 5
            self.db.add_coins(user_data['id'], win)
            self.db.update_user(user_data['id'], rr_wins=user_data.get('rr_wins', 0) + 1)
            
            text = (
                s.header("🔫 РУССКАЯ РУЛЕТКА") + "\n"
                f"{s.item(f'Ставка: {bet} 💰')}\n"
                f"{s.item('Щёлк... Повезло!')}\n\n"
                f"{s.success(f'ВЫИГРЫШ! +{win} 💰')}"
            )
        
        await update.message.reply_text(text, parse_mode="Markdown")
        self.db.log_action(user_data['id'], 'rr', f"{'win' if chamber != shot else 'lose'} {bet}")
    
    async def cmd_dice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Кости"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        bet = 10
        if context.args:
            try:
                bet = int(context.args[0])
            except:
                await update.message.reply_text(s.error("❌ Ставка должна быть числом"))
                return
        
        if bet > user_data['coins']:
            await update.message.reply_text(s.error(f"❌ Недостаточно монет. Баланс: {user_data['coins']} 💰"))
            return
        
        if bet <= 0:
            await update.message.reply_text(s.error("❌ Ставка должна быть больше 0"))
            return
        
        d1 = random.randint(1, 6)
        d2 = random.randint(1, 6)
        total = d1 + d2
        
        if total in [7, 11]:
            win = bet * 2
            self.db.add_coins(user_data['id'], win)
            self.db.update_user(user_data['id'], dice_wins=user_data.get('dice_wins', 0) + 1)
            result = s.success(f"🎉 ВЫИГРЫШ! +{win} 💰")
        elif total in [2, 3, 12]:
            self.db.add_coins(user_data['id'], -bet)
            self.db.update_user(user_data['id'], dice_losses=user_data.get('dice_losses', 0) + 1)
            result = s.error(f"💀 ПРОИГРЫШ! -{bet} 💰")
        else:
            result = s.info(f"🔄 НИЧЬЯ! Ставка возвращена")
        
        text = (
            s.header("🎲 КОСТИ") + "\n"
            f"{s.item(f'Ставка: {bet} 💰')}\n"
            f"{s.item(f'Кубики: {d1} + {d2} = {total}')}\n\n"
            f"{result}"
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_roulette(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Рулетка"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
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
            await update.message.reply_text(s.error(f"❌ Недостаточно монет. Баланс: {user_data['coins']} 💰"))
            return
        
        if bet <= 0:
            await update.message.reply_text(s.error("❌ Ставка должна быть больше 0"))
            return
        
        num = random.randint(0, 36)
        red_numbers = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]
        color = "red" if num in red_numbers else "black" if num != 0 else "green"
        
        win = False
        multiplier = 0
        
        if choice.isdigit() and 0 <= int(choice) <= 36 and int(choice) == num:
            win = True
            multiplier = 36
        elif choice in ["red", "black", "green"] and choice == color:
            win = True
            multiplier = 2 if choice in ["red", "black"] else 36
        
        if win:
            win_amount = bet * multiplier
            self.db.add_coins(user_data['id'], win_amount)
            self.db.update_user(user_data['id'], casino_wins=user_data.get('casino_wins', 0) + 1)
            result = s.success(f"🎉 ВЫИГРЫШ! +{win_amount} 💰")
        else:
            self.db.add_coins(user_data['id'], -bet)
            self.db.update_user(user_data['id'], casino_losses=user_data.get('casino_losses', 0) + 1)
            result = s.error(f"💀 ПРОИГРЫШ! -{bet} 💰")
        
        text = (
            s.header("🎰 РУЛЕТКА") + "\n"
            f"{s.item(f'Ставка: {bet} 💰')}\n"
            f"{s.item(f'Выпало: {num} {color}')}\n\n"
            f"{result}"
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")
        self.db.log_action(user_data['id'], 'roulette', f"{'win' if win else 'lose'} {bet}")
    
    async def cmd_slots(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Слоты"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        bet = 10
        if context.args:
            try:
                bet = int(context.args[0])
            except:
                await update.message.reply_text(s.error("❌ Ставка должна быть числом"))
                return
        
        if bet > user_data['coins']:
            await update.message.reply_text(s.error(f"❌ Недостаточно монет. Баланс: {user_data['coins']} 💰"))
            return
        
        if bet <= 0:
            await update.message.reply_text(s.error("❌ Ставка должна быть больше 0"))
            return
        
        symbols = ["🍒", "🍋", "🍊", "7️⃣", "💎", "🎰"]
        spin = [random.choice(symbols) for _ in range(3)]
        
        if len(set(spin)) == 1:
            if spin[0] == "7️⃣":
                win = bet * 50
            elif spin[0] == "💎":
                win = bet * 30
            else:
                win = bet * 10
            result = s.success(f"🎉 ДЖЕКПОТ! +{win} 💰")
            self.db.update_user(user_data['id'], slots_wins=user_data.get('slots_wins', 0) + 1)
        elif len(set(spin)) == 2:
            win = bet * 2
            result = s.success(f"🎉 ВЫИГРЫШ! +{win} 💰")
            self.db.update_user(user_data['id'], slots_wins=user_data.get('slots_wins', 0) + 1)
        else:
            win = 0
            result = s.error(f"💀 ПРОИГРЫШ! -{bet} 💰")
            self.db.update_user(user_data['id'], slots_losses=user_data.get('slots_losses', 0) + 1)
        
        if win > 0:
            self.db.add_coins(user_data['id'], win)
        else:
            self.db.add_coins(user_data['id'], -bet)
        
        text = (
            s.header("🎰 СЛОТЫ") + "\n"
            f"{' '.join(spin)}\n\n"
            f"{s.item(f'Ставка: {bet} 💰')}\n"
            f"{result}"
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_rps(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Камень-ножницы-бумага"""
        await update.message.reply_text(
            s.header("✊ КАМЕНЬ-НОЖНИЦЫ-БУМАГА") + "\nВыберите жест:",
            reply_markup=kb.rps(),
            parse_mode="Markdown"
        )
    
    async def cmd_saper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сапёр (упрощённая версия)"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        bet = 10
        if context.args:
            try:
                bet = int(context.args[0])
            except:
                await update.message.reply_text(s.error("❌ Ставка должна быть числом"))
                return
        
        if bet > user_data['coins']:
            await update.message.reply_text(s.error(f"❌ Недостаточно монет. Баланс: {user_data['coins']} 💰"))
            return
        
        # Создаём поле 3x3 с 1 миной
        field = [['⬜' for _ in range(3)] for _ in range(3)]
        mine_x, mine_y = random.randint(0, 2), random.randint(0, 2)
        
        game_id = f"saper_{user.id}_{int(time.time())}"
        self.games_in_progress[game_id] = {
            'user_id': user.id,
            'field': field,
            'mine_x': mine_x,
            'mine_y': mine_y,
            'bet': bet,
            'opened': 0
        }
        
        self.db.add_coins(user_data['id'], -bet)  # Забираем ставку
        
        text = (
            s.header("💣 САПЁР") + "\n"
            f"{s.item(f'Ставка: {bet} 💰')}\n"
            f"{s.item('Выберите клетку от 1 до 9')}\n\n"
            f"{' '.join(field[0])}\n"
            f"{' '.join(field[1])}\n"
            f"{' '.join(field[2])}\n\n"
            f"Напишите номер клетки (1-9)"
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_guess(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Угадай число"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        bet = 10
        if context.args:
            try:
                bet = int(context.args[0])
            except:
                bet = 10
        
        if bet > user_data['coins']:
            await update.message.reply_text(s.error(f"❌ Недостаточно монет. Баланс: {user_data['coins']} 💰"))
            return
        
        number = random.randint(1, 100)
        game_id = f"guess_{user.id}_{int(time.time())}"
        self.games_in_progress[game_id] = {
            'user_id': user.id,
            'number': number,
            'attempts': 0,
            'max_attempts': 7,
            'bet': bet
        }
        
        self.db.add_coins(user_data['id'], -bet)
        
        await update.message.reply_text(
            f"{s.header('🔢 УГАДАЙ ЧИСЛО')}\n\n"
            f"{s.item('Я загадал число от 1 до 100')}\n"
            f"{s.item(f'Ставка: {bet} 💰')}\n"
            f"{s.item('Попыток: 7')}\n\n"
            f"✏️ Напиши свой вариант...",
            parse_mode="Markdown"
        )
    
    async def cmd_bulls(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Быки и коровы"""
        user = update.effective_user
        
        digits = random.sample(range(10), 4)
        number = ''.join(map(str, digits))
        
        game_id = f"bulls_{user.id}_{int(time.time())}"
        self.games_in_progress[game_id] = {
            'user_id': user.id,
            'number': number,
            'attempts': [],
            'max_attempts': 10
        }
        
        await update.message.reply_text(
            f"{s.header('🐂 БЫКИ И КОРОВЫ')}\n\n"
            f"{s.item('Я загадал 4-значное число без повторов')}\n"
            f"{s.item('Попыток: 10')}\n"
            f"{s.item('Бык — цифра на своём месте')}\n"
            f"{s.item('Корова — цифра есть, но не на своём месте')}\n\n"
            f"✏️ Напиши свой вариант (4 цифры)...",
            parse_mode="Markdown"
        )

    # ===== МАФИЯ =====
    
    async def cmd_mafia(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Меню мафии"""
        await update.message.reply_text(
            s.header("🔫 МАФИЯ") + "\nВыберите действие:",
            reply_markup=kb.mafia(),
            parse_mode="Markdown"
        )
    
    async def cmd_mafia_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать игру в мафию"""
        chat_id = update.effective_chat.id
        
        if chat_id in self.mafia_games:
            await update.message.reply_text(s.error("❌ Игра уже идёт! Присоединяйтесь: /mafia_join"))
            return
        
        self.mafia_games[chat_id] = {
            'status': 'registration',
            'players': [],
            'roles': {},
            'alive': {},
            'day': 1,
            'phase': 'night',
            'votes': {},
            'mafia_kill': None,
            'doctor_save': None,
            'commissioner_check': None
        }
        
        # Отправляем гифку ночи
        try:
            await context.bot.send_animation(
                chat_id=chat_id,
                animation=MAFIA_GIFS["night"]
            )
        except:
            pass
        
        text = (
            s.header("🔫 МАФИЯ") + "\n"
            f"{s.success('Игра создана!')}\n\n"
            f"{s.item('Участники (0):')}\n"
            f"{s.item('/mafia_join — присоединиться')}\n"
            f"{s.item('/mafia_leave — выйти')}\n"
            f"{s.item('Для старта нужно минимум 4 игрока')}"
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_mafia_join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Присоединиться к игре"""
        chat_id = update.effective_chat.id
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if chat_id not in self.mafia_games:
            await update.message.reply_text(s.error("❌ Игра не создана. Начните: /mafia_start"))
            return
        
        game = self.mafia_games[chat_id]
        
        if game['status'] != 'registration':
            await update.message.reply_text(s.error("❌ Игра уже началась"))
            return
        
        if any(p['id'] == user.id for p in game['players']):
            await update.message.reply_text(s.error("❌ Вы уже в игре"))
            return
        
        game['players'].append({
            'id': user.id,
            'name': user.first_name,
            'username': user.username
        })
        
        text = (
            s.header("🔫 МАФИЯ") + "\n"
            f"{s.success(f'{user.first_name} присоединился!')}\n\n"
            f"{s.item(f'Участники ({len(game["players"])}):')}\n"
        )
        
        for i, p in enumerate(game['players'], 1):
            text += f"{s.item(f'{i}. {p["name"]}')}\n"
        
        text += f"\n{s.info('Нужно минимум 4 игрока')}"
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_mafia_leave(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Покинуть игру"""
        chat_id = update.effective_chat.id
        user = update.effective_user
        
        if chat_id not in self.mafia_games:
            await update.message.reply_text(s.error("❌ Игра не создана"))
            return
        
        game = self.mafia_games[chat_id]
        
        if game['status'] != 'registration':
            await update.message.reply_text(s.error("❌ Нельзя покинуть игру после начала"))
            return
        
        game['players'] = [p for p in game['players'] if p['id'] != user.id]
        
        await update.message.reply_text(
            s.success(f"✅ {user.first_name} покинул игру"),
            parse_mode="Markdown"
        )
    
    async def cmd_mafia_roles(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать роли в мафии"""
        text = (
            s.header("🔫 РОЛИ В МАФИИ") + "\n\n"
            f"{s.section('МАФИЯ')}"
            f"{s.item('👿 Мафиози — ночью убивают')}\n"
            f"{s.item('😈 Дон — глава мафии, проверяет комиссара')}\n\n"
            f"{s.section('ГОРОД')}"
            f"{s.item('👮 Комиссар — ночью проверяет игроков')}\n"
            f"{s.item('👨‍⚕️ Доктор — лечит по ночам')}\n"
            f"{s.item('👤 Мирный житель — ищет мафию днём')}\n"
        )
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_mafia_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Правила мафии"""
        text = (
            s.header("🔫 ПРАВИЛА МАФИИ") + "\n\n"
            f"{s.section('НОЧЬ')}"
            f"{s.item('🌙 Мафия выбирает жертву')}\n"
            f"{s.item('🔍 Комиссар проверяет игрока')}\n"
            f"{s.item('💊 Доктор лечит игрока')}\n\n"
            f"{s.section('ДЕНЬ')}"
            f"{s.item('☀️ Обсуждение')}\n"
            f"{s.item('🗳️ Голосование за исключение')}\n"
            f"{s.item('⚰️ Исключённый раскрывает роль')}\n\n"
            f"{s.section('ЦЕЛЬ ИГРЫ')}"
            f"{s.item('Мафия — убить всех мирных')}\n"
            f"{s.item('Город — найти и исключить всю мафию')}"
        )
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_mafia_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Статистика мафии"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        text = (
            s.header("🔫 СТАТИСТИКА МАФИИ") + "\n\n"
            f"{s.stat('Сыграно игр', user_data['mafia_games'])}\n"
            f"{s.stat('Побед', user_data['mafia_wins'])}\n"
            f"{s.stat('Поражений', user_data['mafia_losses'])}\n"
            f"{s.stat('Процент побед', f'{(user_data["mafia_wins"]/max(1, user_data["mafia_games"])*100):.1f}%')}"
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_mafia_vote(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Голосование в мафии"""
        chat_id = update.effective_chat.id
        user = update.effective_user
        text = update.message.text
        
        if chat_id not in self.mafia_games:
            return
        
        game = self.mafia_games[chat_id]
        
        if game['status'] != 'day':
            await update.message.reply_text(s.error("❌ Сейчас ночь, нельзя голосовать"))
            return
        
        # Парсим голос
        match = re.search(r'голосовать\s+(\d+)', text, re.IGNORECASE)
        if not match:
            await update.message.reply_text(s.error("❌ Пример: голосовать 2"))
            return
        
        vote_num = int(match.group(1))
        if vote_num < 1 or vote_num > len(game['alive']):
            await update.message.reply_text(s.error("❌ Неверный номер игрока"))
            return
        
        # Получаем игрока по номеру
        alive_list = list(game['alive'].keys())
        target_id = alive_list[vote_num - 1]
        
        game['votes'][user.id] = target_id
        
        await update.message.reply_text(
            s.success(f"✅ Голос засчитан!"),
            parse_mode="Markdown"
        )
        
        # Проверяем, все ли проголосовали
        if len(game['votes']) >= len(game['alive']):
            await self.mafia_end_day(chat_id, context)

    # ===== РАЗВЛЕЧЕНИЯ =====
    
    async def cmd_joke(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Случайная шутка"""
        jokes = [
            "Почему программисты путают Хэллоуин и Рождество? Потому что Oct 31 == Dec 25!",
            "Встречаются два программиста: - Ты знаешь, я вчера такой баг нашел... - А размером с чем? - С комара! - Это фича, а не баг.",
            "Жена программиста: - Дорогой, сходи в магазин. - Не могу, у меня компиляция. - Ну пожалуйста! - Ладно, только чур ты за кодом следишь.",
            "Идут два программиста по пустыне. Один другому: - Смотри, змея! - Где? - Вон, под камнем. - Это не змея, это ремень. - Нет, змея! Спорим? - Спорим. Подходят, а это действительно ремень. - Ты выиграл. - Ага, только теперь нам без ремня идти.",
            "Приходит мужик к врачу: - Доктор, у меня что-то с головой не то... - А что именно? - Да понимаете, вчера пошел в магазин, купил хлеб, молоко, и вдруг вижу - девушка красивая идет. Я за ней, она в подъезд, я за ней... Очнулся - лежу в канаве, денег нет, телефона нет. - Ну вы просто влюбились, бывает. - Доктор, я неделю назад женился!"
        ]
        text = f"{s.header('😄 ШУТКА')}\n\n{random.choice(jokes)}"
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_fact(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Интересный факт"""
        facts = [
            "Водка не замерзает в морозилке из-за высокого содержания спирта.",
            "Сердце человека бьется около 100 000 раз в день.",
            "Кошки спят около 70% своей жизни.",
            "Банан — это ягода, а не фрукт.",
            "Осьминоги имеют три сердца.",
            "Страусы могут бежать быстрее лошадей.",
            "У улиток около 25 000 зубов.",
            "Колибри — единственная птица, которая может летать задом наперед.",
            "В Антарктиде есть только один постоянный банкомат.",
            "Язык хамелеона в два раза длиннее его тела."
        ]
        text = f"{s.header('🔍 ИНТЕРЕСНЫЙ ФАКТ')}\n\n{random.choice(facts)}"
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_quote(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Случайная цитата"""
        quotes = [
            "Успех — это способность идти от поражения к поражению, не теряя энтузиазма.",
            "Сложнее всего начать действовать, все остальное зависит только от упорства.",
            "Лучший способ предсказать будущее — создать его.",
            "Не бойтесь, что у вас не получится. Бойтесь, что вы не попробуете.",
            "Будьте собой, остальные роли уже заняты.",
            "Каждый день — это новая возможность изменить свою жизнь.",
            "Единственный способ делать великую работу — любить то, что вы делаете.",
            "Верьте, что вы можете, и вы уже на полпути.",
            "Действие — это ключ к успеху.",
            "Терпение и труд всё перетрут."
        ]
        text = f"{s.header('📝 ЦИТАТА')}\n\n«{random.choice(quotes)}»"
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_whoami(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Кто я сегодня?"""
        roles = [
            "Герой", "Злодей", "Мудрец", "Шут", "Король", "Нищий",
            "Воин", "Маг", "Вор", "Купец", "Поэт", "Художник",
            "Учёный", "Повар", "Водитель", "Врач", "Учитель", "Студент"
        ]
        text = f"{s.header('🎭 КТО Я СЕГОДНЯ?')}\n\n{random.choice(roles)}"
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_advice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Случайный совет"""
        advices = [
            "Никогда не сдавайся!",
            "Пей больше воды.",
            "Высыпайся, это важно.",
            "Делай зарядку по утрам.",
            "Читай книги — это развивает.",
            "Не откладывай на завтра то, что можно сделать сегодня.",
            "Улыбайся чаще!",
            "Слушай своё сердце.",
            "Будь добрее к другим.",
            "Изучай новое каждый день."
        ]
        text = f"{s.header('💡 СОВЕТ')}\n\n{random.choice(advices)}"
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_choose(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбрать из вариантов"""
        if len(context.args) < 2:
            await update.message.reply_text(s.error("❌ Укажи варианты: /choose вариант1 вариант2 ..."))
            return
        
        choice = random.choice(context.args)
        await update.message.reply_text(f"🤔 **Я выбираю:** {choice}", parse_mode="Markdown")
    
    async def cmd_random(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Случайное число"""
        if len(context.args) < 2:
            await update.message.reply_text(s.error("❌ Использование: /random мин макс"))
            return
        
        try:
            min_val = int(context.args[0])
            max_val = int(context.args[1])
            if min_val >= max_val:
                await update.message.reply_text(s.error("❌ min должно быть меньше max"))
                return
            result = random.randint(min_val, max_val)
            await update.message.reply_text(f"🎲 **Случайное число:** {result}", parse_mode="Markdown")
        except:
            await update.message.reply_text(s.error("❌ Неверные числа"))
    
    async def cmd_coin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Монетка"""
        result = random.choice(["Орел", "Решка"])
        await update.message.reply_text(f"🪙 **Монетка:** {result}", parse_mode="Markdown")
    
    # ===== ПОЛЕЗНОЕ =====
    
    async def cmd_weather(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Погода (симуляция)"""
        city = " ".join(context.args) if context.args else "Москва"
        
        weathers = ["☀️ солнечно", "⛅ облачно", "☁️ пасмурно", "🌧 дождь", "⛈ гроза", "❄️ снег"]
        temp = random.randint(-15, 30)
        wind = random.randint(0, 15)
        humidity = random.randint(30, 90)
        weather = random.choice(weathers)
        
        text = (
            s.header(f"🌍 ПОГОДА: {city.upper()}") + "\n\n"
            f"{weather}, {temp}°C\n"
            f"💨 Ветер: {wind} м/с\n"
            f"💧 Влажность: {humidity}%\n"
            f"📅 {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_time(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Текущее время"""
        now = datetime.datetime.now()
        time_str = now.strftime("%H:%M:%S")
        date_str = now.strftime("%d.%m.%Y")
        await update.message.reply_text(f"⏰ **Текущее время:**\n{date_str} {time_str}", parse_mode="Markdown")
    
    async def cmd_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Текущая дата"""
        now = datetime.datetime.now()
        date_str = now.strftime("%d.%m.%Y")
        day_str = now.strftime("%A")
        await update.message.reply_text(f"📅 **Сегодня:** {date_str}\n📆 **День недели:** {day_str}", parse_mode="Markdown")
    
    async def cmd_calc(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Калькулятор"""
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажи выражение: /calc 2+2"))
            return
        
        expr = " ".join(context.args)
        try:
            # Безопасное вычисление (только базовые операции)
            allowed = set("0123456789+-*/(). ")
            if not all(c in allowed for c in expr):
                await update.message.reply_text(s.error("❌ Выражение содержит недопустимые символы"))
                return
            
            result = eval(expr)
            await update.message.reply_text(f"🧮 **Результат:** {result}", parse_mode="Markdown")
        except:
            await update.message.reply_text(s.error("❌ Неверное выражение"))
    
    async def cmd_ping(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Проверка бота"""
        start = time.time()
        msg = await update.message.reply_text("🏓 Pong...")
        end = time.time()
        ping = int((end - start) * 1000)
        uptime = datetime.datetime.now() - self.start_time
        hours = uptime.seconds // 3600
        minutes = (uptime.seconds % 3600) // 60
        
        await msg.edit_text(
            f"{s.header('🏓 ПОНГ')}\n\n"
            f"{s.stat('Задержка', f'{ping} мс')}\n"
            f"{s.stat('Аптайм', f'{uptime.days}д {hours}ч {minutes}м')}\n"
            f"{s.stat('Статус', '✅ Работаю')}",
            parse_mode="Markdown"
        )
    
    async def cmd_uptime(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Время работы бота"""
        uptime = datetime.datetime.now() - self.start_time
        days = uptime.days
        hours = uptime.seconds // 3600
        minutes = (uptime.seconds % 3600) // 60
        
        await update.message.reply_text(
            f"⏱ **Аптайм:**\n{days}д {hours}ч {minutes}м",
            parse_mode="Markdown"
        )
    
    async def cmd_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о боте"""
        users_count = self.db.cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        
        text = (
            s.header("🤖 О БОТЕ") + "\n\n"
            f"**СПЕКТР** v5.0 ULTIMATE\n\n"
            f"{s.section('СТАТИСТИКА')}"
            f"{s.stat('Пользователей', users_count)}\n"
            f"{s.stat('Команд', '200+')}\n"
            f"{s.stat('Модулей', '25+')}\n"
            f"{s.stat('Запущен', self.start_time.strftime('%d.%m.%Y %H:%M'))}\n\n"
            f"{s.section('ВОЗМОЖНОСТИ')}"
            f"{s.item('👥 Модерация (5 рангов)')}\n"
            f"{s.item('🎮 Игры: мафия, рулетка, КНБ и др.')}\n"
            f"{s.item('💰 Экономика, донат, VIP')}\n"
            f"{s.item('🤖 Groq AI с дерзким характером')}\n"
            f"{s.item('👥 Кланы, отношения, браки')}\n"
            f"{s.item('📊 Статистика и топы')}\n\n"
            f"👑 **Владелец:** {OWNER_USERNAME}"
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")

    # ===== CALLBACK КНОПКИ =====
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатий на кнопки"""
        query = update.callback_query
        await query.answer()
        data = query.data
        user = query.from_user
        
        if data == "noop":
            return
        
        elif data == "menu_main":
            await query.edit_message_text(
                s.header("ГЛАВНОЕ МЕНЮ") + "\nВыберите раздел:",
                reply_markup=kb.main(),
                parse_mode="Markdown"
            )
        
        elif data == "menu_back":
            await query.edit_message_text(
                s.header("ГЛАВНОЕ МЕНЮ") + "\nВыберите раздел:",
                reply_markup=kb.main(),
                parse_mode="Markdown"
            )
        
        elif data == "menu_profile":
            context.args = []
            await self.cmd_profile(update, context)
        
        elif data == "menu_stats":
            context.args = []
            await self.cmd_stats(update, context)
        
        elif data == "menu_games":
            await query.edit_message_text(
                s.header("🎮 ИГРЫ") + "\nВыберите игру:",
                reply_markup=kb.games(),
                parse_mode="Markdown"
            )
        
        elif data == "menu_mafia":
            await query.edit_message_text(
                s.header("🔫 МАФИЯ") + "\nВыберите действие:",
                reply_markup=kb.mafia(),
                parse_mode="Markdown"
            )
        
        elif data == "mafia_start":
            context.args = []
            await self.cmd_mafia_start(update, context)
        
        elif data == "mafia_rules":
            await self.cmd_mafia_rules(update, context)
        
        elif data == "mafia_roles":
            await self.cmd_mafia_roles(update, context)
        
        elif data == "mafia_stats":
            await self.cmd_mafia_stats(update, context)
        
        elif data == "menu_economy":
            await query.edit_message_text(
                s.header("💰 ЭКОНОМИКА") + "\nВыберите раздел:",
                reply_markup=kb.economy(),
                parse_mode="Markdown"
            )
        
        elif data == "eco_balance":
            context.args = []
            await self.cmd_balance(update, context)
        
        elif data == "eco_shop":
            context.args = []
            await self.cmd_shop(update, context)
        
        elif data == "eco_bonus":
            await query.edit_message_text(
                f"{s.header('🎁 БОНУСЫ')}\n\n"
                f"{s.cmd('daily', 'ежедневный бонус')}\n"
                f"{s.cmd('weekly', 'недельный бонус')}\n"
                f"{s.cmd('streak', 'текущий стрик')}\n"
                f"{s.cmd('work', 'работать')}",
                reply_markup=kb.back(),
                parse_mode="Markdown"
            )
        
        elif data == "eco_pay":
            await query.edit_message_text(
                f"{s.header('💳 ПЕРЕВОД')}\n\n"
                f"Используйте команду:\n"
                f"{s.cmd('pay @user сумма', 'перевести монеты')}\n"
                f"{s.example('pay @friend 100')}",
                reply_markup=kb.back(),
                parse_mode="Markdown"
            )
        
        elif data == "eco_top":
            context.args = []
            await self.cmd_top(update, context)
        
        elif data == "menu_donate":
            context.args = []
            await self.cmd_donate(update, context)
        
        elif data == "menu_mod":
            await query.edit_message_text(
                s.header("⚙️ МОДЕРАЦИЯ") + "\nВыберите раздел:",
                reply_markup=kb.mod(),
                parse_mode="Markdown"
            )
        
        elif data == "menu_help":
            context.args = []
            await self.cmd_help(update, context)
        
        elif data == "game_rr":
            context.args = []
            await self.cmd_russian_roulette(update, context)
        
        elif data == "game_dice":
            context.args = []
            await self.cmd_dice(update, context)
        
        elif data == "game_roulette":
            context.args = []
            await self.cmd_roulette(update, context)
        
        elif data == "game_slots":
            context.args = []
            await self.cmd_slots(update, context)
        
        elif data == "game_rps":
            await query.edit_message_text(
                s.header("✊ КНБ") + "\nВыберите жест:",
                reply_markup=kb.rps(),
                parse_mode="Markdown"
            )
        
        elif data == "game_saper":
            context.args = []
            await self.cmd_saper(update, context)
        
        elif data == "game_guess":
            context.args = []
            await self.cmd_guess(update, context)
        
        elif data == "game_bulls":
            context.args = []
            await self.cmd_bulls(update, context)
        
        elif data == "mod_warns":
            await query.edit_message_text(
                s.header("⚠️ УПРАВЛЕНИЕ ПРЕДУПРЕЖДЕНИЯМИ") + "\n\n"
                f"{s.cmd('варн @user [причина]', 'выдать предупреждение')}\n"
                f"{s.cmd('варны @user', 'список предупреждений')}\n"
                f"{s.cmd('снять варн @user', 'снять предупреждение')}",
                reply_markup=kb.back(),
                parse_mode="Markdown"
            )
        
        elif data == "mod_mutes":
            await query.edit_message_text(
                s.header("🔇 УПРАВЛЕНИЕ МУТАМИ") + "\n\n"
                f"{s.cmd('мут @user время [причина]', 'заглушить')}\n"
                f"{s.cmd('размут @user', 'снять мут')}\n"
                f"{s.cmd('мутлист', 'список замученных')}",
                reply_markup=kb.back(),
                parse_mode="Markdown"
            )
        
        elif data == "mod_bans":
            await query.edit_message_text(
                s.header("🔨 УПРАВЛЕНИЕ БАНАМИ") + "\n\n"
                f"{s.cmd('бан @user [причина]', 'заблокировать')}\n"
                f"{s.cmd('разбан @user', 'разблокировать')}\n"
                f"{s.cmd('банлист', 'список забаненных')}\n"
                f"{s.cmd('кик @user', 'исключить')}",
                reply_markup=kb.back(),
                parse_mode="Markdown"
            )
        
        elif data == "mod_blacklist":
            await query.edit_message_text(
                s.header("📋 ЧЕРНЫЙ СПИСОК") + "\n\n"
                f"{s.cmd('+блэклист слово', 'добавить слово')}\n"
                f"{s.cmd('-блэклист слово', 'удалить слово')}\n"
                f"{s.cmd('блэклист', 'показать список')}",
                reply_markup=kb.back(),
                parse_mode="Markdown"
            )
        
        elif data == "mod_admins":
            await query.edit_message_text(
                s.header("👥 АДМИНИСТРАТОРЫ") + "\n\n"
                f"{s.cmd('кто админ', 'список админов')}\n"
                f"{s.cmd('+Модер @user [ранг]', 'назначить модератора')}\n"
                f"{s.cmd('снять @user', 'снять модератора')}",
                reply_markup=kb.back(),
                parse_mode="Markdown"
            )
        
        elif data == "mod_settings":
            await query.edit_message_text(
                s.header("⚙️ НАСТРОЙКИ ЧАТА") + "\n\n"
                f"{s.cmd('+приветствие [текст]', 'приветствие')}\n"
                f"{s.cmd('+правила [текст]', 'правила')}\n"
                f"{s.cmd('капча on/off', 'капча')}",
                reply_markup=kb.back(),
                parse_mode="Markdown"
            )
        
        elif data.startswith("rps_"):
            choice = data.split('_')[1]
            bot_choice = random.choice(["rock", "scissors", "paper"])
            
            results = {
                ("rock", "scissors"): "win",
                ("scissors", "paper"): "win",
                ("paper", "rock"): "win",
                ("scissors", "rock"): "lose",
                ("paper", "scissors"): "lose",
                ("rock", "paper"): "lose"
            }
            
            emoji = {"rock": "🪨", "scissors": "✂️", "paper": "📄"}
            names = {"rock": "Камень", "scissors": "Ножницы", "paper": "Бумага"}
            
            text = s.header("✊ КНБ") + "\n\n"
            text += f"{emoji[choice]} **Вы:** {names[choice]}\n"
            text += f"{emoji[bot_choice]} **Бот:** {names[bot_choice]}\n\n"
            
            user_data = self.db.get_user(user.id)
            
            if choice == bot_choice:
                self.db.update_user(user_data['id'], rps_draws=user_data.get('rps_draws', 0) + 1)
                text += s.info("🤝 **НИЧЬЯ!**")
            elif results.get((choice, bot_choice)) == "win":
                self.db.update_user(user_data['id'], rps_wins=user_data.get('rps_wins', 0) + 1)
                reward = random.randint(10, 30)
                self.db.add_coins(user_data['id'], reward)
                text += s.success(f"🎉 **ПОБЕДА!** +{reward} 💰")
            else:
                self.db.update_user(user_data['id'], rps_losses=user_data.get('rps_losses', 0) + 1)
                text += s.error("😢 **ПОРАЖЕНИЕ!**")
            
            await query.edit_message_text(
                text,
                reply_markup=kb.back(),
                parse_mode="Markdown"
            )

    # ===== ОБРАБОТЧИК СООБЩЕНИЙ =====
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        user = update.effective_user
        message_text = update.message.text
        
        if message_text.startswith('/'):
            return
        
        user_data = self.db.get_user(user.id, user.first_name)
        
        # Обновляем статистику
        self.db.update_user(user_data['id'], messages_count=user_data.get('messages_count', 0) + 1)
        
        # Проверка на бан
        if self.db.is_banned(user_data['id']):
            return
        
        # Проверка на мут
        if self.db.is_muted(user_data['id']):
            await update.message.reply_text(s.error("🔇 Ты в муте"))
            return
        
        # Проверка на спам
        if await self.check_spam(update):
            return
        
        # Проверка черного списка
        if self.db.is_word_blacklisted(message_text):
            await update.message.delete()
            await update.message.reply_text(s.warning("⚠️ Запрещенное слово! Сообщение удалено."))
            return
        
        # Проверка на активные игры
        for game_id, game in list(self.games_in_progress.items()):
            if game.get('user_id') == user.id:
                if game_id.startswith('guess_'):
                    # Игра "Угадай число"
                    try:
                        guess = int(message_text)
                        game['attempts'] += 1
                        
                        if guess == game['number']:
                            win = game['bet'] * 2
                            self.db.add_coins(user_data['id'], win)
                            self.db.update_user(user_data['id'], guess_wins=user_data.get('guess_wins', 0) + 1)
                            
                            await update.message.reply_text(
                                s.success(f"🎉 ПОЗДРАВЛЯЮ! Число {game['number']}!\nПопыток: {game['attempts']}\nВыигрыш: {win} 💰"),
                                parse_mode="Markdown"
                            )
                            del self.games_in_progress[game_id]
                        elif game['attempts'] >= game['max_attempts']:
                            self.db.update_user(user_data['id'], guess_losses=user_data.get('guess_losses', 0) + 1)
                            await update.message.reply_text(
                                s.error(f"❌ Попытки кончились! Было число {game['number']}"),
                                parse_mode="Markdown"
                            )
                            del self.games_in_progress[game_id]
                        elif guess < game['number']:
                            await update.message.reply_text(f"📈 Загаданное число **больше** {guess}")
                        else:
                            await update.message.reply_text(f"📉 Загаданное число **меньше** {guess}")
                    except ValueError:
                        await update.message.reply_text(s.error("❌ Введите число от 1 до 100"))
                    return
                
                elif game_id.startswith('bulls_'):
                    if len(message_text) != 4 or not message_text.isdigit():
                        await update.message.reply_text(s.error("❌ Введите 4 цифры"))
                        return
                    
                    guess = message_text
                    if len(set(guess)) != 4:
                        await update.message.reply_text(s.error("❌ Цифры не должны повторяться"))
                        return
                    
                    bulls = 0
                    cows = 0
                    for i in range(4):
                        if guess[i] == game['number'][i]:
                            bulls += 1
                        elif guess[i] in game['number']:
                            cows += 1
                    
                    game['attempts'].append((guess, bulls, cows))
                    
                    if bulls == 4:
                        win = 50
                        self.db.add_coins(user_data['id'], win)
                        self.db.update_user(user_data['id'], bulls_wins=user_data.get('bulls_wins', 0) + 1)
                        
                        await update.message.reply_text(
                            s.success(f"🎉 ПОБЕДА! Число {game['number']}!\nПопыток: {len(game['attempts'])}\nВыигрыш: {win} 💰"),
                            parse_mode="Markdown"
                        )
                        del self.games_in_progress[game_id]
                    elif len(game['attempts']) >= game['max_attempts']:
                        self.db.update_user(user_data['id'], bulls_losses=user_data.get('bulls_losses', 0) + 1)
                        await update.message.reply_text(
                            s.error(f"❌ Попытки кончились! Было число {game['number']}"),
                            parse_mode="Markdown"
                        )
                        del self.games_in_progress[game_id]
                    else:
                        await update.message.reply_text(
                            f"🔍 Быки: {bulls}, Коровы: {cows}\n"
                            f"Осталось попыток: {game['max_attempts'] - len(game['attempts'])}"
                        )
                    return
                
                elif game_id.startswith('saper_'):
                    try:
                        cell = int(message_text)
                        if cell < 1 or cell > 9:
                            await update.message.reply_text(s.error("❌ Введите число от 1 до 9"))
                            return
                        
                        x = (cell - 1) // 3
                        y = (cell - 1) % 3
                        
                        if x == game['mine_x'] and y == game['mine_y']:
                            # Проигрыш
                            self.db.update_user(user_data['id'], slots_losses=user_data.get('slots_losses', 0) + 1)
                            await update.message.reply_text(
                                f"{s.header('💥 БУМ!')}\n\n{s.error('Ты подорвался на мине!')}\n\nПроигрыш: {game['bet']} 💰",
                                parse_mode="Markdown"
                            )
                            del self.games_in_progress[game_id]
                        else:
                            game['opened'] += 1
                            if game['opened'] >= 8:
                                win = game['bet'] * 3
                                self.db.add_coins(user_data['id'], win)
                                self.db.update_user(user_data['id'], slots_wins=user_data.get('slots_wins', 0) + 1)
                                await update.message.reply_text(
                                    s.success(f"🎉 ПОБЕДА! Ты открыл все безопасные клетки!\nВыигрыш: {win} 💰"),
                                    parse_mode="Markdown"
                                )
                                del self.games_in_progress[game_id]
                            else:
                                await update.message.reply_text(s.success("✅ Клетка безопасна! Продолжай..."))
                    except ValueError:
                        await update.message.reply_text(s.error("❌ Введите число от 1 до 9"))
                    return
        
        # AI отвечает с определённой вероятностью
        if self.ai and random.randint(1, 100) <= AI_CHANCE:
            await update.message.chat.send_action(action="typing")
            response = await self.ai.get_response(user.id, message_text, user.first_name)
            if response:
                await update.message.reply_text(f"🤖 **Спектр:** {response}", parse_mode="Markdown")
                return
        
        # Простые ответы если AI не сработал
        msg_lower = message_text.lower()
        
        if any(word in msg_lower for word in ["привет", "здравствуйте", "хай", "здаров"]):
            await update.message.reply_text("👋 Привет! Чем могу помочь?")
        elif any(word in msg_lower for word in ["как дела", "как ты"]):
            await update.message.reply_text("✨ Всё отлично! Работаю в штатном режиме.")
        elif any(word in msg_lower for word in ["спасибо", "благодарю"]):
            await update.message.reply_text("🤝 Всегда пожалуйста!")
        elif any(word in msg_lower for word in ["кто создал", "владелец"]):
            await update.message.reply_text(f"👑 Владелец: {OWNER_USERNAME}")
        else:
            responses = [
                "Используйте /help для списка команд",
                "Напишите /menu для навигации",
                "Чем могу помочь?",
                "Я слушаю..."
            ]
            await update.message.reply_text(random.choice(responses))
    
    async def handle_new_members(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка новых участников"""
        chat_id = update.effective_chat.id
        
        # Получаем приветствие
        self.db.cursor.execute("SELECT welcome FROM chat_settings WHERE chat_id = ?", (chat_id,))
        row = self.db.cursor.fetchone()
        welcome_text = row[0] if row and row[0] else "Добро пожаловать!"
        
        for member in update.message.new_chat_members:
            if member.is_bot:
                continue
            await update.message.reply_text(
                f"👋 {welcome_text}\n\n{member.first_name}, используйте /help для команд!",
                parse_mode="Markdown"
            )
    
    async def handle_left_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ухода участников"""
        member = update.message.left_chat_member
        if member.is_bot:
            return
        await update.message.reply_text(f"👋 {member.first_name} покинул чат...", parse_mode="Markdown")
    
    # ===== ЗАПУСК =====
    
    async def run(self):
        """Запуск бота"""
        try:
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling(drop_pending_updates=True)
            
            logger.info("🚀 Бот СПЕКТР успешно запущен")
            logger.info(f"👑 Владелец: {OWNER_USERNAME}")
            logger.info(f"📊 PID: {os.getpid()}")
            
            while True:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Критическая ошибка: {e}")
            import traceback
            logger.error(traceback.format_exc())
            await asyncio.sleep(5)
            await self.run()
    
    async def close(self):
        """Закрытие бота"""
        logger.info("👋 Завершение работы бота...")
        if self.ai:
            await self.ai.close()
        self.db.close()
        logger.info("✅ Бот остановлен")


# ========== ТОЧКА ВХОДА ==========
async def main():
    """Главная функция"""
    print("=" * 60)
    print("✨ ЗАПУСК БОТА СПЕКТР v5.0 ULTIMATE ✨")
    print("=" * 60)
    print(f"📊 Версия: 5.0 ULTIMATE")
    print(f"📊 Команд: 200+")
    print(f"📊 Модулей: 25+")
    print(f"📊 AI: {'Groq подключен' if GROQ_KEY else 'Не подключен'}")
    print(f"📊 PID: {os.getpid()}")
    print("=" * 60)
    
    bot = SpectrumBot()
    
    try:
        await bot.run()
    except KeyboardInterrupt:
        logger.info("Остановка по запросу пользователя")
        await bot.close()
    except Exception as e:
        logger.error(f"Необработанная ошибка: {e}")
        import traceback
        logger.error(traceback.format_exc())
        await bot.close()

if __name__ == "__main__":
    asyncio.run(main())
