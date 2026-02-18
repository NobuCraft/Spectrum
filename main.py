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
AI_CHANCE = 40

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

# ========== ЭЛЕГАНТНОЕ ОФОРМЛЕНИЕ ==========
class Style:
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

# ========== БАЗА ДАННЫХ ==========
class Database:
    def __init__(self):
        self.conn = sqlite3.connect("spectrum.db", check_same_thread=False)
        self.c = self.conn.cursor()
        self.create_tables()
        logger.info("✅ База данных инициализирована")
    
    def create_tables(self):
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                language TEXT DEFAULT 'ru',
                coins INTEGER DEFAULT 1000,
                diamonds INTEGER DEFAULT 0,
                energy INTEGER DEFAULT 100,
                level INTEGER DEFAULT 1,
                exp INTEGER DEFAULT 0,
                health INTEGER DEFAULT 100,
                max_health INTEGER DEFAULT 100,
                damage INTEGER DEFAULT 10,
                armor INTEGER DEFAULT 0,
                crit_chance INTEGER DEFAULT 5,
                crit_multiplier INTEGER DEFAULT 150,
                messages_count INTEGER DEFAULT 0,
                commands_used INTEGER DEFAULT 0,
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
                mafia_games INTEGER DEFAULT 0,
                mafia_wins INTEGER DEFAULT 0,
                mafia_losses INTEGER DEFAULT 0,
                mafia_role TEXT,
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
                vip_until TEXT,
                premium_until TEXT,
                daily_streak INTEGER DEFAULT 0,
                last_daily TEXT,
                last_weekly TEXT,
                last_monthly TEXT,
                last_work TEXT,
                last_seen TEXT,
                notifications INTEGER DEFAULT 1,
                theme TEXT DEFAULT 'light',
                registered TEXT DEFAULT CURRENT_TIMESTAMP,
                referrer_id INTEGER
            )
        ''')
        
        self.c.execute('CREATE INDEX IF NOT EXISTS idx_telegram_id ON users(telegram_id)')
        self.c.execute('CREATE INDEX IF NOT EXISTS idx_username ON users(username)')
        self.c.execute('CREATE INDEX IF NOT EXISTS idx_rank ON users(rank)')
        
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
        
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS blacklist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT UNIQUE,
                added_by INTEGER,
                added_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
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
    
    def add_energy(self, user_id: int, amount: int) -> int:
        self.c.execute("UPDATE users SET energy = MIN(100, energy + ?) WHERE id = ?", (amount, user_id))
        self.conn.commit()
        self.c.execute("SELECT energy FROM users WHERE id = ?", (user_id,))
        return self.c.fetchone()[0]
    
    def heal(self, user_id: int, amount: int) -> int:
        self.c.execute("UPDATE users SET health = MIN(max_health, health + ?) WHERE id = ?", (amount, user_id))
        self.conn.commit()
        self.c.execute("SELECT health FROM users WHERE id = ?", (user_id,))
        return self.c.fetchone()[0]
    
    def damage(self, user_id: int, amount: int) -> int:
        self.c.execute("UPDATE users SET health = MAX(0, health - ?) WHERE id = ?", (amount, user_id))
        self.conn.commit()
        self.c.execute("SELECT health FROM users WHERE id = ?", (user_id,))
        return self.c.fetchone()[0]
    
    def is_vip(self, user_id: int) -> bool:
        self.c.execute("SELECT vip_until FROM users WHERE id = ?", (user_id,))
        row = self.c.fetchone()
        if row and row[0]:
            return datetime.datetime.fromisoformat(row[0]) > datetime.datetime.now()
        return False
    
    def is_premium(self, user_id: int) -> bool:
        self.c.execute("SELECT premium_until FROM users WHERE id = ?", (user_id,))
        row = self.c.fetchone()
        if row and row[0]:
            return datetime.datetime.fromisoformat(row[0]) > datetime.datetime.now()
        return False
    
    def set_vip(self, user_id: int, days: int) -> datetime.datetime:
        until = datetime.datetime.now() + datetime.timedelta(days=days)
        self.c.execute("UPDATE users SET vip_until = ?, role = 'vip' WHERE id = ?",
                      (until.isoformat(), user_id))
        self.conn.commit()
        return until
    
    def set_premium(self, user_id: int, days: int) -> datetime.datetime:
        until = datetime.datetime.now() + datetime.timedelta(days=days)
        self.c.execute("UPDATE users SET premium_until = ?, role = 'premium' WHERE id = ?",
                      (until.isoformat(), user_id))
        self.conn.commit()
        return until
    
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
    
    def get_top(self, field: str, limit: int = 10) -> List[Tuple]:
        self.c.execute(f"SELECT first_name, nickname, {field} FROM users ORDER BY {field} DESC LIMIT ?", (limit,))
        return self.c.fetchall()
    
    def log_action(self, user_id: int, action: str, details: str = "", chat_id: int = None):
        self.c.execute('''
            INSERT INTO logs (user_id, action, details, chat_id, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, action, details, chat_id, datetime.datetime.now().isoformat()))
        self.conn.commit()
    
    def close(self):
        self.conn.close()

db = Database()

# ========== GROQ AI ==========
class GroqAI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.session = None
        self.contexts = defaultdict(lambda: deque(maxlen=10))
        self.user_last_ai = defaultdict(float)
        self.ai_cooldown = 3
        
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
    print("✅ Groq AI инициализирован")
else:
    ai = None
    print("⚠️ Groq AI не подключен")

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
        """Регистрация всех обработчиков"""
        
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
        self.app.add_handler(MessageHandler(filters.Regex(r'^!снять всех|^снять_всех'), self.cmd_remove_all_ranks))
        self.app.add_handler(MessageHandler(filters.Regex(r'^кто админ'), self.cmd_who_admins))
        
        # ===== БАНЫ И ПРЕДУПРЕЖДЕНИЯ =====
        self.app.add_handler(MessageHandler(filters.Regex(r'^варн|^пред'), self.cmd_warn))
        self.app.add_handler(MessageHandler(filters.Regex(r'^варны'), self.cmd_warns))
        self.app.add_handler(MessageHandler(filters.Regex(r'^снять варн|^-варн'), self.cmd_unwarn))
        self.app.add_handler(MessageHandler(filters.Regex(r'^мут'), self.cmd_mute))
        self.app.add_handler(MessageHandler(filters.Regex(r'^мутлист'), self.cmd_mutelist))
        self.app.add_handler(MessageHandler(filters.Regex(r'^размут'), self.cmd_unmute))
        self.app.add_handler(MessageHandler(filters.Regex(r'^бан'), self.cmd_ban))
        self.app.add_handler(MessageHandler(filters.Regex(r'^банлист'), self.cmd_banlist))
        self.app.add_handler(MessageHandler(filters.Regex(r'^разбан'), self.cmd_unban))
        self.app.add_handler(MessageHandler(filters.Regex(r'^кик'), self.cmd_kick))
        
        # ===== ЧИСТКА ЧАТА =====
        self.app.add_handler(MessageHandler(filters.Regex(r'^чистка'), self.cmd_clear))
        
        # ===== НАСТРОЙКИ ЧАТА =====
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+приветствие'), self.cmd_set_welcome))
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+правила'), self.cmd_set_rules))
        self.app.add_handler(MessageHandler(filters.Regex(r'^правила'), self.cmd_show_rules))
        self.app.add_handler(MessageHandler(filters.Regex(r'^-приветствие'), self.cmd_remove_welcome))
        self.app.add_handler(MessageHandler(filters.Regex(r'^капча'), self.cmd_set_captcha))
        
        # ===== ЧЕРНЫЙ СПИСОК =====
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+блэклист|^\+чс'), self.cmd_add_blacklist))
        self.app.add_handler(MessageHandler(filters.Regex(r'^-блэклист|^-чс'), self.cmd_remove_blacklist))
        self.app.add_handler(MessageHandler(filters.Regex(r'^блэклист'), self.cmd_show_blacklist))
        
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
            f"{s.item('🤖 AI общение')}\n"
            f"{s.item('💰 Экономика, донат, VIP')}\n"
            f"{s.item('⚙️ Модерация (5 рангов)')}\n\n"
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
            f"{s.cmd('капча on/off', 'включить капчу')}\n\n"
            
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
    
    # ===== ПРОФИЛЬ МЕТОДЫ =====
    
    async def cmd_set_nick(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажи ник: /nick [ник]"))
            return
        
        nick = " ".join(context.args)
        if len(nick) > MAX_NICK_LENGTH:
            await update.message.reply_text(s.error(f"❌ Максимум {MAX_NICK_LENGTH} символов"))
            return
        
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], nickname=nick)
        await update.message.reply_text(s.success(f"✅ Ник установлен: {nick}"))
    
    async def cmd_set_title(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажи титул: /title [титул]"))
            return
        
        title = " ".join(context.args)
        if len(title) > MAX_TITLE_LENGTH:
            await update.message.reply_text(s.error(f"❌ Максимум {MAX_TITLE_LENGTH} символов"))
            return
        
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], title=title)
        await update.message.reply_text(s.success(f"✅ Титул установлен: {title}"))
    
    async def cmd_set_motto(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажи девиз: /motto [девиз]"))
            return
        
        motto = " ".join(context.args)
        if len(motto) > MAX_MOTTO_LENGTH:
            await update.message.reply_text(s.error(f"❌ Максимум {MAX_MOTTO_LENGTH} символов"))
            return
        
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], motto=motto)
        await update.message.reply_text(s.success(f"✅ Девиз установлен: _{motto}_"))
    
    async def cmd_set_bio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажи био: /bio [текст]"))
            return
        
        bio = " ".join(context.args)
        if len(bio) > MAX_BIO_LENGTH:
            await update.message.reply_text(s.error(f"❌ Максимум {MAX_BIO_LENGTH} символов"))
            return
        
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], bio=bio)
        await update.message.reply_text(s.success("✅ Био установлено"))
    
    async def cmd_set_gender(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args or context.args[0].lower() not in ['м', 'ж']:
            await update.message.reply_text(s.error("❌ Укажи /gender м или /gender ж"))
            return
        
        gender = "мужской" if context.args[0].lower() == 'м' else "женский"
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], gender=gender)
        await update.message.reply_text(s.success(f"✅ Пол установлен: {gender}"))
    
    async def cmd_set_city(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажи город: /city [город]"))
            return
        
        city = " ".join(context.args)
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], city=city)
        await update.message.reply_text(s.success(f"✅ Город установлен: {city}"))
    
    async def cmd_set_birth(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажи дату: /birth ДД.ММ.ГГГГ"))
            return
        
        date_str = context.args[0]
        try:
            datetime.datetime.strptime(date_str, "%d.%m.%Y")
            user_data = self.db.get_user(update.effective_user.id)
            self.db.update_user(user_data['id'], birth_date=date_str)
            await update.message.reply_text(s.success(f"✅ Дата рождения установлена: {date_str}"))
        except:
            await update.message.reply_text(s.error("❌ Неверный формат. Используй: ДД.ММ.ГГГГ"))
    
    async def cmd_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        await update.message.reply_text(f"🆔 **Ваш ID:** {s.code(str(user.id))}", parse_mode="Markdown")
    
    async def cmd_rep(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text(s.error("❌ Использование: /rep @ник +/-"))
            return
        
        username = context.args[0].replace('@', '')
        action = context.args[1]
        
        if action not in ['+', '-']:
            await update.message.reply_text(s.error("❌ Используй + или -"))
            return
        
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        change = 1 if action == '+' else -1
        new_rep = target['reputation'] + change
        self.db.update_user(target['id'], reputation=new_rep)
        
        action_text = "повысил" if action == '+' else "понизил"
        await update.message.reply_text(
            s.success(f"✅ Ты {action_text} репутацию {target['first_name']} (теперь {new_rep})"),
            parse_mode="Markdown"
        )
    
    # ===== СТАТИСТИКА =====
    
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)
        
        text = (
            s.header("СТАТИСТИКА") + "\n"
            f"{s.section('ОБЩАЯ')}"
            f"{s.stat('Сообщений', user_data['messages_count'])}\n"
            f"{s.stat('Команд', user_data['commands_used'])}\n"
            f"{s.stat('Дней в боте', (datetime.datetime.now() - datetime.datetime.fromisoformat(user_data['registered'])).days)}\n\n"
            f"{s.section('ИГРЫ')}"
            f"{s.stat('КНБ побед', user_data['rps_wins'])}\n"
            f"{s.stat('Кости побед', user_data['dice_wins'])}\n"
            f"{s.stat('Русская рулетка побед', user_data['rr_wins'])}\n"
            f"{s.stat('Слоты побед', user_data['slots_wins'])}"
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_top(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        top_coins = self.db.get_top("coins", 10)
        top_level = self.db.get_top("level", 10)
        top_reputation = self.db.get_top("reputation", 10)
        
        text = s.header("ТОП ИГРОКОВ") + "\n"
        
        text += f"{s.section('ПО МОНЕТАМ')}\n"
        for i, row in enumerate(top_coins, 1):
            name = row[1] or row[0]
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} **{name}** — {row[2]} 💰\n"
        
        text += f"\n{s.section('ПО УРОВНЮ')}\n"
        for i, row in enumerate(top_level, 1):
            name = row[1] or row[0]
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} **{name}** — {row[2]} ур.\n"
        
        text += f"\n{s.section('ПО РЕПУТАЦИИ')}\n"
        for i, row in enumerate(top_reputation, 1):
            name = row[1] or row[0]
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} **{name}** — {row[2]} ⭐\n"
        
        await update.message.reply_text(text, reply_markup=kb.back(), parse_mode="Markdown")

    # ===== ЧИСТКА ЧАТА =====
    
    async def cmd_clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Очистка сообщений"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 2 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав. Нужен ранг 2+"))
            return
        
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
            except:
                await update.message.reply_text(s.error("❌ Неверное количество"))
    
    # ===== НАСТРОЙКИ ЧАТА =====
    
    async def cmd_set_welcome(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установка приветствия"""
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
        """Установка правил"""
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
        
        coins = random.randint(100, 300)
        exp = random.randint(20, 60)
        energy = 20
        
        coins = int(coins * (1 + min(streak, 30) * 0.05))
        exp = int(exp * (1 + min(streak, 30) * 0.05))
        
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
    
    async def cmd_shop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Магазин"""
        text = (
            s.header("МАГАЗИН") + "\n"
            f"{s.section('ЗЕЛЬЯ')}"
            f"{s.cmd('buy зелье здоровья', '50 💰 (❤️+30)')}\n"
            f"{s.cmd('buy большое зелье', '100 💰 (❤️+70)')}\n\n"
            f"{s.section('ЭНЕРГИЯ')}"
            f"{s.cmd('buy энергетик', '30 💰 (⚡+20)')}\n"
            f"{s.cmd('buy батарейка', '80 💰 (⚡+50)')}\n\n"
            f"{s.section('ПРИВИЛЕГИИ')}"
            f"{s.cmd('vip', f'VIP ({VIP_PRICE} 💰)')}\n"
            f"{s.cmd('premium', f'PREMIUM ({PREMIUM_PRICE} 💰)')}"
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
            "энергетик": {"price": 30, "energy": 20},
            "батарейка": {"price": 80, "energy": 50}
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
            f"{s.stat('Энергия', f'{user_data['energy']}/100 ⚡')}\n"
            f"{s.stat('Здоровье', f'{user_data['health']}/100 ❤️')}"
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
            f"{s.item('🚫 Без комиссии')}\n\n"
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
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Ошибка: {context.error}")
        try:
            if update and update.effective_message:
                await update.effective_message.reply_text(s.error("Произошла внутренняя ошибка"))
        except:
            pass
    
    async def run(self):
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
        logger.info("👋 Завершение работы бота...")
        if self.ai:
            await self.ai.close()
        self.db.close()
        logger.info("✅ Бот остановлен")


# ========== ТОЧКА ВХОДА ==========
async def main():
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
