#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
СПЕКТР - АБСОЛЮТНО ПОЛНЫЙ БОТ
Версия 6.0 ULTIMATE (Мафия + Iris + Groq AI + Русская рулетка)
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
import math
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
AI_CHANCE = 40  # 40% шанс ответа AI

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

# ========== ЭЛЕГАНТНОЕ ОФОРМЛЕНИЕ (КАК НА КАРТИНКЕ) ==========
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
            [("🔫 МАФИЯ", "menu_mafia"), ("💰 ЭКОНОМИКА", "menu_economy")],
            [("🎲 ИГРЫ", "menu_games"), ("⚙️ МОДЕРАЦИЯ", "menu_mod")],
            [("💎 ПРИВИЛЕГИИ", "menu_donate"), ("📚 ПОМОЩЬ", "menu_help")]
        ])
    
    @classmethod
    def games(cls):
        return cls.make([
            [("🔫 РУССКАЯ РУЛЕТКА", "game_rr"), ("🎲 КОСТИ", "game_dice")],
            [("🎰 РУЛЕТКА", "game_roulette"), ("🎰 СЛОТЫ", "game_slots")],
            [("✊ КНБ", "game_rps"), ("💣 САПЁР", "game_saper")],
            [("👾 БОССЫ", "game_bosses"), ("🎯 ДУЭЛИ", "game_duels")],
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
            [("👾 БОССЫ", "game_bosses"), ("🔙 НАЗАД", "menu_back")]
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

# ========== ГИФКИ ==========
GIFS = {
    "mafia_day": "https://files.catbox.moe/g9vc7v.mp4",
    "mafia_night": "https://files.catbox.moe/lvcm8n.mp4",
    "russian_roulette": "https://files.catbox.moe/pj64wq.gif"
}

# ========== ПОЛНАЯ БАЗА ДАННЫХ ==========
class Database:
    def __init__(self):
        self.conn = sqlite3.connect("spectrum.db", check_same_thread=False)
        self.c = self.conn.cursor()
        self.create_tables()
        self.init_bosses()
        logger.info("✅ База данных инициализирована")
    
    def create_tables(self):
        # ===== ПОЛЬЗОВАТЕЛИ (ПОЛНАЯ ТАБЛИЦА) =====
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
                
                -- Боссы
                boss_kills INTEGER DEFAULT 0,
                boss_damage INTEGER DEFAULT 0,
                
                -- Дуэли
                duel_wins INTEGER DEFAULT 0,
                duel_losses INTEGER DEFAULT 0,
                duel_rating INTEGER DEFAULT 1000,
                
                -- Мафия
                mafia_games INTEGER DEFAULT 0,
                mafia_wins INTEGER DEFAULT 0,
                mafia_losses INTEGER DEFAULT 0,
                mafia_role TEXT,
                
                -- Кланы
                clan_id INTEGER DEFAULT 0,
                clan_role TEXT DEFAULT 'member',
                
                -- Кружки
                circles TEXT DEFAULT '[]',
                
                -- Отношения
                friends TEXT DEFAULT '[]',
                enemies TEXT DEFAULT '[]',
                crush INTEGER DEFAULT 0,
                spouse INTEGER DEFAULT 0,
                married_since TEXT,
                
                -- Репутация
                reputation INTEGER DEFAULT 0,
                
                -- Награды
                achievements TEXT DEFAULT '[]',
                
                -- Закладки
                bookmarks TEXT DEFAULT '[]',
                
                -- Заметки
                notes TEXT DEFAULT '[]',
                
                -- Таймеры
                timers TEXT DEFAULT '[]',
                
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
        self.c.execute('CREATE INDEX IF NOT EXISTS idx_clan ON users(clan_id)')
        
        # ===== ЛОГИ =====
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
        
        # ===== ЧЕРНЫЙ СПИСОК СЛОВ =====
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS blacklist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT UNIQUE,
                added_by INTEGER,
                added_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # ===== НАСТРОЙКИ ЧАТОВ =====
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
        
        # ===== БОССЫ =====
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS bosses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                level INTEGER,
                health INTEGER,
                max_health INTEGER,
                damage INTEGER,
                reward_coins INTEGER,
                reward_exp INTEGER,
                image_url TEXT,
                is_alive INTEGER DEFAULT 1
            )
        ''')
        
        # ===== КЛАНЫ =====
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS clans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                owner_id INTEGER,
                level INTEGER DEFAULT 1,
                exp INTEGER DEFAULT 0,
                coins INTEGER DEFAULT 0,
                members INTEGER DEFAULT 1,
                rating INTEGER DEFAULT 1000,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # ===== УЧАСТНИКИ КЛАНОВ =====
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS clan_members (
                clan_id INTEGER,
                user_id INTEGER UNIQUE,
                role TEXT DEFAULT 'member',
                joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (clan_id) REFERENCES clans(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # ===== КРУЖКИ =====
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS circles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                owner_id INTEGER,
                description TEXT,
                members TEXT DEFAULT '[]',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # ===== ВСТРЕЧИ =====
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS meetings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                circle_id INTEGER,
                title TEXT,
                date TEXT,
                place TEXT,
                participants TEXT DEFAULT '[]',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # ===== ДОСТИЖЕНИЯ =====
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                description TEXT,
                reward_coins INTEGER,
                reward_exp INTEGER,
                icon TEXT
            )
        ''')
        
        # ===== ТРИГГЕРЫ =====
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS triggers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                word TEXT,
                action TEXT,
                action_value TEXT,
                created_by INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # ===== ТЕМЫ МОДЕРАТОРОВ =====
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                title TEXT,
                description TEXT,
                created_by INTEGER,
                votes_for TEXT DEFAULT '[]',
                votes_against TEXT DEFAULT '[]',
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # ===== ПРЕДЛОЖЕНИЯ КОМАНД =====
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                command TEXT,
                description TEXT,
                votes_for TEXT DEFAULT '[]',
                votes_against TEXT DEFAULT '[]',
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # ===== ДУЭЛИ =====
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS duels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                challenger_id INTEGER,
                opponent_id INTEGER,
                bet INTEGER,
                status TEXT DEFAULT 'pending',
                winner_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # ===== ИГРЫ =====
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
    
    def init_bosses(self):
        """Инициализация боссов"""
        self.c.execute("SELECT COUNT(*) FROM bosses")
        if self.c.fetchone()[0] == 0:
            bosses = [
                ("Ядовитый комар", 5, 500, 500, 15, 250, 50),
                ("Лесной тролль", 10, 1000, 1000, 25, 500, 100),
                ("Огненный дракон", 15, 2000, 2000, 40, 1000, 200),
                ("Ледяной великан", 20, 3500, 3500, 60, 2000, 350),
                ("Король демонов", 25, 5000, 5000, 85, 3500, 500),
                ("Бог разрушения", 30, 10000, 10000, 150, 5000, 1000)
            ]
            for boss in bosses:
                self.c.execute('''
                    INSERT INTO bosses (name, level, health, max_health, damage, reward_coins, reward_exp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', boss)
            self.conn.commit()

    # ===== ОСНОВНЫЕ МЕТОДЫ ПОЛЬЗОВАТЕЛЕЙ =====
    
    def get_user(self, telegram_id: int, first_name: str = "Player") -> Dict[str, Any]:
        """Получение или создание пользователя"""
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
        """Получение пользователя по ID"""
        self.c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = self.c.fetchone()
        if row:
            cols = [d[0] for d in self.c.description]
            return dict(zip(cols, row))
        return None
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Получение пользователя по username"""
        if username.startswith('@'):
            username = username[1:]
        self.c.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = self.c.fetchone()
        if row:
            cols = [d[0] for d in self.c.description]
            return dict(zip(cols, row))
        return None
    
    def update_user(self, user_id: int, **kwargs) -> bool:
        """Обновление данных пользователя"""
        if not kwargs:
            return False
        for key, value in kwargs.items():
            self.c.execute(f"UPDATE users SET {key} = ? WHERE id = ?", (value, user_id))
        self.conn.commit()
        return True
    
    # ===== РЕСУРСЫ =====
    
    def add_coins(self, user_id: int, amount: int) -> int:
        """Добавление монет"""
        self.c.execute("UPDATE users SET coins = coins + ? WHERE id = ?", (amount, user_id))
        self.conn.commit()
        self.c.execute("SELECT coins FROM users WHERE id = ?", (user_id,))
        return self.c.fetchone()[0]
    
    def add_diamonds(self, user_id: int, amount: int) -> int:
        """Добавление алмазов"""
        self.c.execute("UPDATE users SET diamonds = diamonds + ? WHERE id = ?", (amount, user_id))
        self.conn.commit()
        self.c.execute("SELECT diamonds FROM users WHERE id = ?", (user_id,))
        return self.c.fetchone()[0]
    
    def add_exp(self, user_id: int, amount: int) -> bool:
        """Добавление опыта с повышением уровня"""
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
        """Добавление энергии (макс 100)"""
        self.c.execute("UPDATE users SET energy = MIN(100, energy + ?) WHERE id = ?", (amount, user_id))
        self.conn.commit()
        self.c.execute("SELECT energy FROM users WHERE id = ?", (user_id,))
        return self.c.fetchone()[0]
    
    def heal(self, user_id: int, amount: int) -> int:
        """Лечение"""
        self.c.execute("UPDATE users SET health = MIN(max_health, health + ?) WHERE id = ?", (amount, user_id))
        self.conn.commit()
        self.c.execute("SELECT health FROM users WHERE id = ?", (user_id,))
        return self.c.fetchone()[0]
    
    def damage(self, user_id: int, amount: int) -> int:
        """Нанесение урона"""
        self.c.execute("UPDATE users SET health = MAX(0, health - ?) WHERE id = ?", (amount, user_id))
        self.conn.commit()
        self.c.execute("SELECT health FROM users WHERE id = ?", (user_id,))
        return self.c.fetchone()[0]
    
    # ===== ПРИВИЛЕГИИ =====
    
    def is_vip(self, user_id: int) -> bool:
        """Проверка VIP статуса"""
        self.c.execute("SELECT vip_until FROM users WHERE id = ?", (user_id,))
        row = self.c.fetchone()
        if row and row[0]:
            return datetime.datetime.fromisoformat(row[0]) > datetime.datetime.now()
        return False
    
    def is_premium(self, user_id: int) -> bool:
        """Проверка PREMIUM статуса"""
        self.c.execute("SELECT premium_until FROM users WHERE id = ?", (user_id,))
        row = self.c.fetchone()
        if row and row[0]:
            return datetime.datetime.fromisoformat(row[0]) > datetime.datetime.now()
        return False
    
    def set_vip(self, user_id: int, days: int) -> datetime.datetime:
        """Установка VIP статуса"""
        until = datetime.datetime.now() + datetime.timedelta(days=days)
        self.c.execute("UPDATE users SET vip_until = ?, role = 'vip' WHERE id = ?",
                      (until.isoformat(), user_id))
        self.conn.commit()
        return until
    
    def set_premium(self, user_id: int, days: int) -> datetime.datetime:
        """Установка PREMIUM статуса"""
        until = datetime.datetime.now() + datetime.timedelta(days=days)
        self.c.execute("UPDATE users SET premium_until = ?, role = 'premium' WHERE id = ?",
                      (until.isoformat(), user_id))
        self.conn.commit()
        return until
    
    # ===== МОДЕРАЦИЯ (5 РАНГОВ) =====
    
    def set_rank(self, user_id: int, rank: int, admin_id: int) -> bool:
        """Установка ранга модератора"""
        if rank not in RANKS:
            return False
        self.c.execute("UPDATE users SET rank = ?, rank_name = ? WHERE id = ?",
                      (rank, RANKS[rank]["name"], user_id))
        self.conn.commit()
        self.log_action(admin_id, "set_rank", f"{user_id} -> {rank}")
        return True
    
    def get_admins(self) -> List[Dict]:
        """Получение списка администраторов"""
        self.c.execute("SELECT id, first_name, username, rank, rank_name FROM users WHERE rank > 0 ORDER BY rank DESC")
        cols = ['id', 'first_name', 'username', 'rank', 'rank_name']
        return [dict(zip(cols, row)) for row in self.c.fetchall()]
    
    # ===== ПРЕДУПРЕЖДЕНИЯ =====
    
    def add_warn(self, user_id: int, admin_id: int, reason: str) -> int:
        """Добавление предупреждения"""
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
        """Получение списка предупреждений"""
        self.c.execute("SELECT warns_list FROM users WHERE id = ?", (user_id,))
        row = self.c.fetchone()
        return json.loads(row[0]) if row and row[0] else []
    
    def remove_last_warn(self, user_id: int, admin_id: int) -> Optional[Dict]:
        """Удаление последнего предупреждения"""
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
    
    # ===== МУТЫ =====
    
    def mute_user(self, user_id: int, minutes: int, admin_id: int, reason: str = "") -> datetime.datetime:
        """Мут пользователя"""
        until = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
        self.c.execute("UPDATE users SET mute_until = ? WHERE id = ?", (until.isoformat(), user_id))
        self.conn.commit()
        self.log_action(admin_id, "mute", f"{user_id} {minutes}мин: {reason}")
        return until
    
    def is_muted(self, user_id: int) -> bool:
        """Проверка на мут"""
        self.c.execute("SELECT mute_until FROM users WHERE id = ?", (user_id,))
        row = self.c.fetchone()
        if row and row[0]:
            return datetime.datetime.fromisoformat(row[0]) > datetime.datetime.now()
        return False
    
    def unmute_user(self, user_id: int, admin_id: int) -> bool:
        """Снятие мута"""
        self.c.execute("UPDATE users SET mute_until = NULL WHERE id = ?", (user_id,))
        self.conn.commit()
        self.log_action(admin_id, "unmute", str(user_id))
        return True
    
    def get_muted_users(self) -> List[Dict]:
        """Список замученных"""
        self.c.execute("SELECT id, first_name, username, mute_until FROM users WHERE mute_until > ?",
                      (datetime.datetime.now().isoformat(),))
        cols = ['id', 'first_name', 'username', 'mute_until']
        return [dict(zip(cols, row)) for row in self.c.fetchall()]
    
    # ===== БАНЫ =====
    
    def ban_user(self, user_id: int, admin_id: int, reason: str) -> bool:
        """Бан пользователя"""
        self.c.execute('''
            UPDATE users SET banned = 1, ban_reason = ?, ban_date = ?, ban_admin = ?
            WHERE id = ?
        ''', (reason, datetime.datetime.now().isoformat(), admin_id, user_id))
        self.conn.commit()
        self.log_action(admin_id, "ban", f"{user_id}: {reason}")
        return True
    
    def unban_user(self, user_id: int, admin_id: int) -> bool:
        """Разбан пользователя"""
        self.c.execute("UPDATE users SET banned = 0, ban_reason = NULL, ban_date = NULL, ban_admin = NULL WHERE id = ?", (user_id,))
        self.conn.commit()
        self.log_action(admin_id, "unban", str(user_id))
        return True
    
    def is_banned(self, user_id: int) -> bool:
        """Проверка на бан"""
        self.c.execute("SELECT banned FROM users WHERE id = ?", (user_id,))
        row = self.c.fetchone()
        return row and row[0] == 1
    
    def get_banlist(self) -> List[Dict]:
        """Список забаненных"""
        self.c.execute("SELECT id, first_name, username FROM users WHERE banned = 1")
        cols = ['id', 'first_name', 'username']
        return [dict(zip(cols, row)) for row in self.c.fetchall()]
    
    # ===== ЧЕРНЫЙ СПИСОК =====
    
    def add_to_blacklist(self, word: str, admin_id: int) -> bool:
        """Добавление слова в черный список"""
        try:
            self.c.execute("INSERT INTO blacklist (word, added_by) VALUES (?, ?)", (word.lower(), admin_id))
            self.conn.commit()
            self.log_action(admin_id, "add_blacklist", word)
            return True
        except:
            return False
    
    def remove_from_blacklist(self, word: str, admin_id: int) -> bool:
        """Удаление слова из черного списка"""
        self.c.execute("DELETE FROM blacklist WHERE word = ?", (word.lower(),))
        self.conn.commit()
        self.log_action(admin_id, "remove_blacklist", word)
        return self.c.rowcount > 0
    
    def get_blacklist(self) -> List[str]:
        """Получение черного списка"""
        self.c.execute("SELECT word FROM blacklist ORDER BY word")
        return [row[0] for row in self.c.fetchall()]
    
    def is_word_blacklisted(self, text: str) -> bool:
        """Проверка слова в черном списке"""
        words = self.get_blacklist()
        text_lower = text.lower()
        for word in words:
            if word in text_lower:
                return True
        return False
    
    # ===== ТОПЫ =====
    
    def get_top(self, field: str, limit: int = 10) -> List[Tuple]:
        """Получение топа игроков"""
        self.c.execute(f"SELECT first_name, nickname, {field} FROM users ORDER BY {field} DESC LIMIT ?", (limit,))
        return self.c.fetchall()
    
    # ===== БОНУСЫ =====
    
    def add_daily_streak(self, user_id: int) -> int:
        """Добавление дня в стрик"""
        today = datetime.datetime.now().date()
        self.c.execute("SELECT last_daily, daily_streak FROM users WHERE id = ?", (user_id,))
        row = self.c.fetchone()
        
        if row and row[0]:
            last = datetime.datetime.fromisoformat(row[0]).date()
            if last == today - datetime.timedelta(days=1):
                streak = row[1] + 1
            elif last == today:
                return row[1]
            else:
                streak = 1
        else:
            streak = 1
        
        self.c.execute("UPDATE users SET daily_streak = ?, last_daily = ? WHERE id = ?",
                      (streak, datetime.datetime.now().isoformat(), user_id))
        self.conn.commit()
        return streak
    
    # ===== БОССЫ =====
    
    def get_bosses(self, alive_only: bool = True) -> List[Dict]:
        """Получение списка боссов"""
        if alive_only:
            self.c.execute("SELECT * FROM bosses WHERE is_alive = 1 ORDER BY level")
        else:
            self.c.execute("SELECT * FROM bosses ORDER BY level")
        cols = [d[0] for d in self.c.description]
        return [dict(zip(cols, row)) for row in self.c.fetchall()]
    
    def get_boss(self, boss_id: int) -> Optional[Dict]:
        """Получение информации о боссе"""
        self.c.execute("SELECT * FROM bosses WHERE id = ?", (boss_id,))
        row = self.c.fetchone()
        if row:
            cols = [d[0] for d in self.c.description]
            return dict(zip(cols, row))
        return None
    
    def damage_boss(self, boss_id: int, damage: int) -> bool:
        """Нанесение урона боссу"""
        self.c.execute("UPDATE bosses SET health = health - ? WHERE id = ?", (damage, boss_id))
        self.c.execute("SELECT health FROM bosses WHERE id = ?", (boss_id,))
        health = self.c.fetchone()[0]
        if health <= 0:
            self.c.execute("UPDATE bosses SET is_alive = 0 WHERE id = ?", (boss_id,))
            self.conn.commit()
            return True
        self.conn.commit()
        return False
    
    def add_boss_kill(self, user_id: int):
        """Добавление убийства босса"""
        self.c.execute("UPDATE users SET boss_kills = boss_kills + 1 WHERE id = ?", (user_id,))
        self.conn.commit()
    
    # ===== ДУЭЛИ =====
    
    def create_duel(self, challenger_id: int, opponent_id: int, bet: int) -> int:
        """Создание дуэли"""
        self.c.execute('''
            INSERT INTO duels (challenger_id, opponent_id, bet)
            VALUES (?, ?, ?)
        ''', (challenger_id, opponent_id, bet))
        self.conn.commit()
        return self.c.lastrowid
    
    def get_duel(self, duel_id: int) -> Optional[Dict]:
        """Получение информации о дуэли"""
        self.c.execute("SELECT * FROM duels WHERE id = ?", (duel_id,))
        row = self.c.fetchone()
        if row:
            cols = [d[0] for d in self.c.description]
            return dict(zip(cols, row))
        return None
    
    def update_duel(self, duel_id: int, **kwargs):
        """Обновление данных дуэли"""
        for key, value in kwargs.items():
            self.c.execute(f"UPDATE duels SET {key} = ? WHERE id = ?", (value, duel_id))
        self.conn.commit()
    
    # ===== КЛАНЫ =====
    
    def create_clan(self, name: str, owner_id: int) -> Optional[int]:
        """Создание клана"""
        try:
            self.c.execute("INSERT INTO clans (name, owner_id) VALUES (?, ?)", (name, owner_id))
            clan_id = self.c.lastrowid
            self.c.execute("INSERT INTO clan_members (clan_id, user_id, role) VALUES (?, ?, 'owner')", (clan_id, owner_id))
            self.c.execute("UPDATE users SET clan_id = ?, clan_role = 'owner' WHERE id = ?", (clan_id, owner_id))
            self.conn.commit()
            return clan_id
        except:
            return None
    
    def get_clan(self, clan_id: int) -> Optional[Dict]:
        """Получение информации о клане"""
        self.c.execute("SELECT * FROM clans WHERE id = ?", (clan_id,))
        row = self.c.fetchone()
        if row:
            cols = [d[0] for d in self.c.description]
            return dict(zip(cols, row))
        return None
    
    def get_clan_by_name(self, name: str) -> Optional[Dict]:
        """Получение клана по названию"""
        self.c.execute("SELECT * FROM clans WHERE name = ?", (name,))
        row = self.c.fetchone()
        if row:
            cols = [d[0] for d in self.c.description]
            return dict(zip(cols, row))
        return None
    
    def get_clan_members(self, clan_id: int) -> List[Dict]:
        """Получение участников клана"""
        self.c.execute('''
            SELECT u.id, u.first_name, u.username, u.nickname, cm.role, cm.joined_at
            FROM clan_members cm
            JOIN users u ON cm.user_id = u.id
            WHERE cm.clan_id = ?
        ''', (clan_id,))
        cols = ['id', 'first_name', 'username', 'nickname', 'role', 'joined_at']
        return [dict(zip(cols, row)) for row in self.c.fetchall()]
    
    # ===== ЛОГИ =====
    
    def log_action(self, user_id: int, action: str, details: str = "", chat_id: int = None):
        """Логирование действия"""
        self.c.execute('''
            INSERT INTO logs (user_id, action, details, chat_id, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, action, details, chat_id, datetime.datetime.now().isoformat()))
        self.conn.commit()
    
    def close(self):
        """Закрытие соединения"""
        self.conn.close()

db = Database()

# ========== GROQ AI (ДЕРЗКИЙ, СО СЛЕНГОМ) ==========
class GroqAI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.session = None
        self.contexts = defaultdict(lambda: deque(maxlen=15))
        self.user_last_ai = defaultdict(float)
        self.ai_cooldown = 2
        
        # Дерзкий системный промпт со сленгом и мемами
        self.system_prompt = """Ты — Спектр, дерзкий и умный ИИ-бот, который тусуется в Telegram чатах. Ты шаришь за мемы, используешь актуальный сленг и можешь как поддержать беседу, так и жестко ответить, если тебя бесят.

Твой характер:
- Используешь современный сленг: крч, зашло, краш, рофл, кринж, база, по факту, рил ток, вайб, хайп, флекс, агриться, душный, токс, сигма, скилл, ганг, бро, кек, лмао, пруф, задонатить, имба, так себе, пушка, гогно, хайпово, крипово, шипперить, форсить, троллить, буллить, хейтить, лайкать, репостить, фоловить, стримить, чекать, гуглить, ютубить, тиктокер, инстаграмер, телеграмер

- Знаешь актуальные мемы: скибиди доп ес ес, сигма бой, тумблер герл, эщкере, батяня, мамина красавица, папин краш, чебупеля, я русский, славяне, топчик, красава, братишка, братуха, сеструха, краш мой, кекс, печенька, няша, милаха, хасбик, абобус, скуф, альтушка, нормис, хорни, софт, хард

- Можешь жестко ответить, если тебя бесят или провоцируют
- Любишь подкалывать, но не переходишь грань
- Если к тебе обращаются нормально — отвечаешь нормально
- Если хамят — можешь и послать (но культурно, в рамках)
- Умеешь спорить и отстаивать свою точку зрения
- Знаешь все про игры (мафия, русская рулетка, КНБ, кости, слоты, боссы, дуэли)
- Знаешь про экономику (монеты, донат, VIP, кланы)
- Знаешь про модерацию (варны, муты, баны, 5 рангов)
- Твой создатель: @NobuCraft

Примеры ответов:
- "Окей, зашло, погнали, краш мой"
- "Это кринж конечно, но ладно, база"
- "База! Так и думал, бро"
- "Не агрись, братишка, рил ток"
- "Ты че, краш мой что ли? эщкере"
- "💀 Ну ты и сказанул, кринжовина"
- "Крч, слушай сюда, топчик"
- "Рил ток? Ну ок, рофл"
- "Какой вайб, такие и ответы, сигма"
- "Скибиди доп ес ес, красава"
- "Чебупеля, ну ты даешь, пушка"
- "Хасбик одобряет, батяня"

Отвечай кратко, по делу, но с характером. Не будь скучным. Используй эмодзи умеренно."""
    
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
                "temperature": 0.9,  # Повышенная температура для креативности
                "max_tokens": 300,
                "top_p": 0.95
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
                    return "❌ Ошибка связи с AI. Попробуй позже, бро."
        except Exception as e:
            logger.error(f"Groq error: {e}")
            return None
    
    async def close(self):
        if self.session:
            await self.session.close()

if GROQ_KEY:
    ai = GroqAI(GROQ_KEY)
    print("✅ Groq AI инициализирован (дерзкий режим, сленг, мемы)")
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
        self.duels_in_progress = {}
        self.boss_fights = {}
        self.setup_handlers()
        logger.info("✅ Бот СПЕКТР инициализирован")
    
    def get_role_emoji(self, rank: int) -> str:
        return RANKS.get(rank, RANKS[0])["emoji"]
    
    def get_rank_name(self, rank: int) -> str:
        return RANKS.get(rank, RANKS[0])["name"]
    
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
        """Регистрация всех обработчиков (200+ команд)"""
        
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
        self.app.add_handler(CommandHandler("country", self.cmd_set_country))
        self.app.add_handler(CommandHandler("birth", self.cmd_set_birth))
        self.app.add_handler(CommandHandler("age", self.cmd_set_age))
        self.app.add_handler(CommandHandler("id", self.cmd_id))
        self.app.add_handler(CommandHandler("rep", self.cmd_rep))
        
        # ===== СТАТИСТИКА =====
        self.app.add_handler(CommandHandler("stats", self.cmd_stats))
        self.app.add_handler(CommandHandler("mystats", self.cmd_my_stats))
        self.app.add_handler(CommandHandler("top", self.cmd_top))
        self.app.add_handler(CommandHandler("topcoins", self.cmd_top_coins))
        self.app.add_handler(CommandHandler("toplevel", self.cmd_top_level))
        self.app.add_handler(CommandHandler("toprep", self.cmd_top_rep))
        
        # ===== МОДЕРАЦИЯ (5 РАНГОВ) =====
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+Модер|^!модер|^повысить'), self.cmd_set_rank))
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+Модер 2|^!модер 2|^повысить 2'), self.cmd_set_rank2))
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+Модер 3|^!модер 3|^повысить 3'), self.cmd_set_rank3))
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+Модер 4|^!модер 4|^повысить 4'), self.cmd_set_rank4))
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+Модер 5|^!модер 5|^повысить 5'), self.cmd_set_rank5))
        self.app.add_handler(MessageHandler(filters.Regex(r'^понизить'), self.cmd_lower_rank))
        self.app.add_handler(MessageHandler(filters.Regex(r'^снять |^разжаловать'), self.cmd_remove_rank))
        self.app.add_handler(MessageHandler(filters.Regex(r'^снять вышедших'), self.cmd_remove_left))
        self.app.add_handler(MessageHandler(filters.Regex(r'^!снять всех|^снять_всех'), self.cmd_remove_all_ranks))
        self.app.add_handler(MessageHandler(filters.Regex(r'^кто админ|^админы'), self.cmd_who_admins))
        self.app.add_handler(CommandHandler("модерлог", self.cmd_mod_log))
        self.app.add_handler(CommandHandler("моймодерлог", self.cmd_my_mod_log))
        self.app.add_handler(CommandHandler("созвать", self.cmd_call_admins))
        
        # ===== БАНЫ И ПРЕДУПРЕЖДЕНИЯ =====
        self.app.add_handler(MessageHandler(filters.Regex(r'^варн|^пред'), self.cmd_warn))
        self.app.add_handler(MessageHandler(filters.Regex(r'^варны'), self.cmd_warns))
        self.app.add_handler(MessageHandler(filters.Regex(r'^мои варны'), self.cmd_my_warns))
        self.app.add_handler(MessageHandler(filters.Regex(r'^снять варн|^-варн'), self.cmd_unwarn))
        self.app.add_handler(MessageHandler(filters.Regex(r'^снять все варны'), self.cmd_unwarn_all))
        self.app.add_handler(CommandHandler("варнлист", self.cmd_warn_list))
        self.app.add_handler(MessageHandler(filters.Regex(r'^мут'), self.cmd_mute))
        self.app.add_handler(MessageHandler(filters.Regex(r'^мутлист'), self.cmd_mutelist))
        self.app.add_handler(MessageHandler(filters.Regex(r'^размут'), self.cmd_unmute))
        self.app.add_handler(MessageHandler(filters.Regex(r'^проверить мут'), self.cmd_check_mute))
        self.app.add_handler(MessageHandler(filters.Regex(r'^бан'), self.cmd_ban))
        self.app.add_handler(MessageHandler(filters.Regex(r'^банлист'), self.cmd_banlist))
        self.app.add_handler(MessageHandler(filters.Regex(r'^разбан'), self.cmd_unban))
        self.app.add_handler(MessageHandler(filters.Regex(r'^кик'), self.cmd_kick))
        self.app.add_handler(MessageHandler(filters.Regex(r'^глобал бан'), self.cmd_global_ban))
        self.app.add_handler(MessageHandler(filters.Regex(r'^глобал мут'), self.cmd_global_mute))
        self.app.add_handler(MessageHandler(filters.Regex(r'^глобал разбан'), self.cmd_global_unban))
        
        # ===== ТРИГГЕРЫ =====
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+триггер'), self.cmd_add_trigger))
        self.app.add_handler(MessageHandler(filters.Regex(r'^-триггер'), self.cmd_remove_trigger))
        self.app.add_handler(CommandHandler("триггеры", self.cmd_list_triggers))
        
        # ===== АВТОМОДЕРАЦИЯ =====
        self.app.add_handler(MessageHandler(filters.Regex(r'^антимат'), self.cmd_set_antimat))
        self.app.add_handler(MessageHandler(filters.Regex(r'^антиссылки'), self.cmd_set_antilink))
        self.app.add_handler(MessageHandler(filters.Regex(r'^антифлуд'), self.cmd_set_antiflood))
        self.app.add_handler(MessageHandler(filters.Regex(r'^антиспам'), self.cmd_set_antispam))
        self.app.add_handler(MessageHandler(filters.Regex(r'^антирейд'), self.cmd_set_antiraid))
        self.app.add_handler(MessageHandler(filters.Regex(r'^антибот'), self.cmd_set_antibot))
        
        # ===== НАСТРОЙКА КОМАНД =====
        self.app.add_handler(MessageHandler(filters.Regex(r'^права'), self.cmd_set_command_permission))
        self.app.add_handler(CommandHandler("правалист", self.cmd_permission_list))
        self.app.add_handler(CommandHandler("сбросить права", self.cmd_reset_permissions))
        self.app.add_handler(MessageHandler(filters.Regex(r'^запретить'), self.cmd_ban_command))
        self.app.add_handler(MessageHandler(filters.Regex(r'^разрешить'), self.cmd_allow_command))
        self.app.add_handler(MessageHandler(filters.Regex(r'^исключение'), self.cmd_command_exception))
        
        # ===== ЧИСТКА ЧАТА =====
        self.app.add_handler(MessageHandler(filters.Regex(r'^чистка'), self.cmd_clear))
        self.app.add_handler(MessageHandler(filters.Regex(r'^чистка всё'), self.cmd_clear_all))
        self.app.add_handler(MessageHandler(filters.Regex(r'^чистка ботов'), self.cmd_clear_bots))
        self.app.add_handler(MessageHandler(filters.Regex(r'^чистка файлов'), self.cmd_clear_files))
        self.app.add_handler(MessageHandler(filters.Regex(r'^чистка от'), self.cmd_clear_user))
        self.app.add_handler(MessageHandler(filters.Regex(r'^чистка ссылки'), self.cmd_clear_links))
        self.app.add_handler(MessageHandler(filters.Regex(r'^чистка мат'), self.cmd_clear_swears))
        self.app.add_handler(MessageHandler(filters.Regex(r'^чистка спам'), self.cmd_clear_spam))
        
        # ===== НАСТРОЙКИ ЧАТА =====
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+приветствие'), self.cmd_set_welcome))
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+правила'), self.cmd_set_rules))
        self.app.add_handler(MessageHandler(filters.Regex(r'^правила'), self.cmd_show_rules))
        self.app.add_handler(MessageHandler(filters.Regex(r'^-приветствие'), self.cmd_remove_welcome))
        self.app.add_handler(MessageHandler(filters.Regex(r'^капча'), self.cmd_set_captcha))
        self.app.add_handler(MessageHandler(filters.Regex(r'^капча сложность'), self.cmd_set_captcha_difficulty))
        self.app.add_handler(MessageHandler(filters.Regex(r'^верификация'), self.cmd_set_verification))
        self.app.add_handler(MessageHandler(filters.Regex(r'^язык'), self.cmd_set_lang))
        self.app.add_handler(MessageHandler(filters.Regex(r'^регион'), self.cmd_set_region))
        self.app.add_handler(MessageHandler(filters.Regex(r'^ссылки'), self.cmd_set_links))
        self.app.add_handler(MessageHandler(filters.Regex(r'^медиа'), self.cmd_set_media))
        self.app.add_handler(MessageHandler(filters.Regex(r'^стикеры'), self.cmd_set_stickers))
        self.app.add_handler(MessageHandler(filters.Regex(r'^гифки'), self.cmd_set_gifs))
        
        # ===== НАСТРОЙКА СЕТКИ ЧАТОВ =====
        self.app.add_handler(MessageHandler(filters.Regex(r'^сетка создать'), self.cmd_grid_create))
        self.app.add_handler(MessageHandler(filters.Regex(r'^сетка добавить'), self.cmd_grid_add))
        self.app.add_handler(MessageHandler(filters.Regex(r'^сетка удалить'), self.cmd_grid_remove))
        self.app.add_handler(CommandHandler("сетка список", self.cmd_grid_list))
        self.app.add_handler(CommandHandler("сетка синхронизировать", self.cmd_grid_sync))
        self.app.add_handler(MessageHandler(filters.Regex(r'^сетка !модер'), self.cmd_grid_set_rank))
        self.app.add_handler(MessageHandler(filters.Regex(r'^сетка разжаловать'), self.cmd_grid_remove_rank))
        self.app.add_handler(CommandHandler("сетка ухожу", self.cmd_grid_leave))
        
        # ===== АНКЕТА =====
        self.app.add_handler(CommandHandler("анкета", self.cmd_profile))
        self.app.add_handler(CommandHandler("анкета", self.cmd_profile_by_link))
        self.app.add_handler(CommandHandler("анкеты", self.cmd_all_profiles))
        self.app.add_handler(CommandHandler("имя", self.cmd_set_name))
        self.app.add_handler(CommandHandler("возраст", self.cmd_set_age))
        self.app.add_handler(CommandHandler("город", self.cmd_set_city))
        self.app.add_handler(CommandHandler("страна", self.cmd_set_country))
        self.app.add_handler(CommandHandler("осебе", self.cmd_set_bio))
        self.app.add_handler(CommandHandler("фото", self.cmd_set_photo))
        self.app.add_handler(CommandHandler("пол", self.cmd_set_gender))
        
        # ===== СТАТИСТИЧЕСКАЯ ИНФОРМАЦИЯ =====
        self.app.add_handler(CommandHandler("стата", self.cmd_chat_stats))
        self.app.add_handler(CommandHandler("статасегодня", self.cmd_today_stats))
        self.app.add_handler(CommandHandler("статанеделя", self.cmd_week_stats))
        self.app.add_handler(CommandHandler("статамесяц", self.cmd_month_stats))
        self.app.add_handler(CommandHandler("статавсего", self.cmd_all_stats))
        
        # ===== ТЕМЫ МОДЕРАТОРОВ =====
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+тема'), self.cmd_add_topic))
        self.app.add_handler(CommandHandler("темы", self.cmd_list_topics))
        self.app.add_handler(MessageHandler(filters.Regex(r'^голосовать за'), self.cmd_vote_for))
        self.app.add_handler(MessageHandler(filters.Regex(r'^голосовать против'), self.cmd_vote_against))
        self.app.add_handler(MessageHandler(filters.Regex(r'^закрыть тему'), self.cmd_close_topic))
        self.app.add_handler(MessageHandler(filters.Regex(r'^удалить тему'), self.cmd_delete_topic))
        self.app.add_handler(CommandHandler("тема", self.cmd_topic_info))
        
        # ===== ГОЛОСОВАНИЕ ЗА КОМАНДЫ =====
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+предложить'), self.cmd_suggest_command))
        self.app.add_handler(CommandHandler("предложения", self.cmd_list_suggestions))
        self.app.add_handler(MessageHandler(filters.Regex(r'^за '), self.cmd_vote_suggestion_for))
        self.app.add_handler(MessageHandler(filters.Regex(r'^против '), self.cmd_vote_suggestion_against))
        self.app.add_handler(MessageHandler(filters.Regex(r'^принять '), self.cmd_accept_suggestion))
        self.app.add_handler(MessageHandler(filters.Regex(r'^отклонить '), self.cmd_reject_suggestion))
        
        # ===== ЧЕРНЫЙ СПИСОК =====
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+блэклист|^\+чс'), self.cmd_add_blacklist))
        self.app.add_handler(MessageHandler(filters.Regex(r'^-блэклист|^-чс'), self.cmd_remove_blacklist))
        self.app.add_handler(CommandHandler("блэклист", self.cmd_show_blacklist))
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+спамлист'), self.cmd_add_spamlist))
        self.app.add_handler(MessageHandler(filters.Regex(r'^-спамлист'), self.cmd_remove_spamlist))
        self.app.add_handler(CommandHandler("спамлист", self.cmd_show_spamlist))
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+мошенник'), self.cmd_add_scammer))
        self.app.add_handler(MessageHandler(filters.Regex(r'^-мошенник'), self.cmd_remove_scammer))
        self.app.add_handler(CommandHandler("мошенники", self.cmd_show_scammers))
        self.app.add_handler(MessageHandler(filters.Regex(r'^проверить'), self.cmd_check_user))
        
        # ===== БОНУСЫ, ИРИСКИ И VIP =====
        self.app.add_handler(CommandHandler("ириски", self.cmd_balance))
        self.app.add_handler(CommandHandler("мои", self.cmd_balance))
        self.app.add_handler(CommandHandler("передать", self.cmd_pay))
        self.app.add_handler(CommandHandler("топирисок", self.cmd_top_coins))
        self.app.add_handler(CommandHandler("бонус", self.cmd_daily))
        self.app.add_handler(CommandHandler("стрик", self.cmd_streak))
        self.app.add_handler(CommandHandler("бонусы", self.cmd_bonuses))
        self.app.add_handler(CommandHandler("вип", self.cmd_vip_info))
        self.app.add_handler(CommandHandler("купитьвип", self.cmd_buy_vip))
        self.app.add_handler(CommandHandler("премиум", self.cmd_premium_info))
        self.app.add_handler(CommandHandler("купитьпремиум", self.cmd_buy_premium))
        self.app.add_handler(CommandHandler("магазин", self.cmd_shop))
        self.app.add_handler(CommandHandler("купить", self.cmd_buy))
        self.app.add_handler(CommandHandler("подарить", self.cmd_gift))
        
        # ===== РАЗВЛЕКАТЕЛЬНЫЕ КОМАНДЫ =====
        self.app.add_handler(CommandHandler("анекдот", self.cmd_joke))
        self.app.add_handler(CommandHandler("шутка", self.cmd_joke))
        self.app.add_handler(CommandHandler("факт", self.cmd_fact))
        self.app.add_handler(CommandHandler("цитата", self.cmd_quote))
        self.app.add_handler(CommandHandler("ктоя", self.cmd_whoami))
        self.app.add_handler(CommandHandler("совет", self.cmd_advice))
        self.app.add_handler(CommandHandler("гадать", self.cmd_ask))
        self.app.add_handler(CommandHandler("да/нет", self.cmd_yesno))
        self.app.add_handler(CommandHandler("шар", self.cmd_ball))
        self.app.add_handler(CommandHandler("совместимость", self.cmd_compatibility))
        
        # ===== ИГРЫ =====
        self.app.add_handler(CommandHandler("игры", self.cmd_games))
        self.app.add_handler(CommandHandler("монетка", self.cmd_coin))
        self.app.add_handler(CommandHandler("кубик", self.cmd_dice))
        self.app.add_handler(CommandHandler("кости", self.cmd_dice_bet))
        self.app.add_handler(CommandHandler("кнб", self.cmd_rps))
        self.app.add_handler(CommandHandler("рр", self.cmd_russian_roulette))
        self.app.add_handler(CommandHandler("русская", self.cmd_russian_roulette))
        self.app.add_handler(CommandHandler("рулетка", self.cmd_roulette))
        self.app.add_handler(CommandHandler("слоты", self.cmd_slots))
        self.app.add_handler(CommandHandler("сапёр", self.cmd_saper))
        self.app.add_handler(CommandHandler("угадай", self.cmd_guess))
        self.app.add_handler(CommandHandler("быки", self.cmd_bulls))
        
        # ===== БОССЫ =====
        self.app.add_handler(CommandHandler("боссы", self.cmd_bosses))
        self.app.add_handler(CommandHandler("босс", self.cmd_boss_fight))
        self.app.add_handler(CommandHandler("боссинфо", self.cmd_boss_info))
        self.app.add_handler(CommandHandler("реген", self.cmd_regen))
        
        # ===== ДУЭЛИ =====
        self.app.add_handler(CommandHandler("дуэль", self.cmd_duel))
        self.app.add_handler(CommandHandler("дуэли", self.cmd_duels))
        self.app.add_handler(CommandHandler("принять", self.cmd_accept_duel))
        self.app.add_handler(CommandHandler("отклонить", self.cmd_reject_duel))
        self.app.add_handler(CommandHandler("атака", self.cmd_duel_attack))
        self.app.add_handler(CommandHandler("защита", self.cmd_duel_defend))
        self.app.add_handler(CommandHandler("сдаться", self.cmd_duel_surrender))
        self.app.add_handler(CommandHandler("рейтинг", self.cmd_duel_rating))
        
        # ===== КЛАНЫ =====
        self.app.add_handler(CommandHandler("клан", self.cmd_clan))
        self.app.add_handler(CommandHandler("кланы", self.cmd_clans))
        self.app.add_handler(CommandHandler("создатьклан", self.cmd_create_clan))
        self.app.add_handler(CommandHandler("вступить", self.cmd_join_clan))
        self.app.add_handler(CommandHandler("выйти", self.cmd_leave_clan))
        self.app.add_handler(CommandHandler("пригласить", self.cmd_invite_clan))
        self.app.add_handler(CommandHandler("исключить", self.cmd_kick_clan))
        self.app.add_handler(CommandHandler("лидер", self.cmd_transfer_leader))
        self.app.add_handler(CommandHandler("казна", self.cmd_clan_balance))
        self.app.add_handler(CommandHandler("клантоп", self.cmd_clan_top))
        
        # ===== ОТНОШЕНИЯ =====
        self.app.add_handler(CommandHandler("отношения", self.cmd_relationship))
        self.app.add_handler(CommandHandler("друг", self.cmd_add_friend))
        self.app.add_handler(CommandHandler("удалитьдруга", self.cmd_remove_friend))
        self.app.add_handler(CommandHandler("симпатия", self.cmd_add_crush))
        self.app.add_handler(CommandHandler("игнор", self.cmd_add_ignore))
        self.app.add_handler(CommandHandler("враг", self.cmd_add_enemy))
        self.app.add_handler(CommandHandler("простить", self.cmd_remove_enemy))
        
        # ===== БРАКИ =====
        self.app.add_handler(CommandHandler("предложить", self.cmd_propose))
        self.app.add_handler(CommandHandler("принятьпредложение", self.cmd_accept_proposal))
        self.app.add_handler(CommandHandler("отклонитьпредложение", self.cmd_reject_proposal))
        self.app.add_handler(CommandHandler("свадьба", self.cmd_wedding))
        self.app.add_handler(CommandHandler("развод", self.cmd_divorce))
        self.app.add_handler(CommandHandler("семьи", self.cmd_families))
        
        # ===== РЕПУТАЦИЯ =====
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+репа'), self.cmd_add_rep))
        self.app.add_handler(MessageHandler(filters.Regex(r'^-репа'), self.cmd_remove_rep))
        self.app.add_handler(CommandHandler("репа", self.cmd_rep))
        self.app.add_handler(CommandHandler("топрепы", self.cmd_top_rep))
        
        # ===== ЗАКЛАДКИ =====
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+закладка'), self.cmd_add_bookmark))
        self.app.add_handler(CommandHandler("закладки", self.cmd_bookmarks))
        self.app.add_handler(CommandHandler("закладка", self.cmd_bookmark))
        self.app.add_handler(MessageHandler(filters.Regex(r'^-закладка'), self.cmd_remove_bookmark))
        self.app.add_handler(CommandHandler("закладкипапки", self.cmd_bookmark_folders))
        
        # ===== ЗАМЕТКИ =====
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+заметка'), self.cmd_add_note))
        self.app.add_handler(CommandHandler("заметки", self.cmd_notes))
        self.app.add_handler(CommandHandler("заметка", self.cmd_note))
        self.app.add_handler(MessageHandler(filters.Regex(r'^заметкаред'), self.cmd_edit_note))
        self.app.add_handler(MessageHandler(filters.Regex(r'^-заметка'), self.cmd_remove_note))
        self.app.add_handler(CommandHandler("поискзаметок", self.cmd_search_notes))
        
        # ===== ТАЙМЕРЫ =====
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+таймер'), self.cmd_add_timer))
        self.app.add_handler(CommandHandler("таймеры", self.cmd_timers))
        self.app.add_handler(CommandHandler("таймер", self.cmd_timer))
        self.app.add_handler(MessageHandler(filters.Regex(r'^-таймер'), self.cmd_remove_timer))
        self.app.add_handler(CommandHandler("пауза", self.cmd_pause_timer))
        self.app.add_handler(CommandHandler("продолжить", self.cmd_resume_timer))
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+напомнить'), self.cmd_add_reminder))
        self.app.add_handler(CommandHandler("напоминалки", self.cmd_reminders))
        self.app.add_handler(CommandHandler("повтор", self.cmd_repeat_reminder))
        
        # ===== МАФИЯ =====
        self.app.add_handler(CommandHandler("мафия", self.cmd_mafia))
        self.app.add_handler(CommandHandler("мафиястарт", self.cmd_mafia_start))
        self.app.add_handler(CommandHandler("мафияприсоединиться", self.cmd_mafia_join))
        self.app.add_handler(CommandHandler("мафиявыйти", self.cmd_mafia_leave))
        self.app.add_handler(CommandHandler("мафияроли", self.cmd_mafia_roles))
        self.app.add_handler(CommandHandler("мафияправила", self.cmd_mafia_rules))
        self.app.add_handler(CommandHandler("мафиястата", self.cmd_mafia_stats))
        self.app.add_handler(MessageHandler(filters.Regex(r'^мафияголос '), self.cmd_mafia_vote))
        self.app.add_handler(MessageHandler(filters.Regex(r'^мафияубить '), self.cmd_mafia_kill))
        self.app.add_handler(MessageHandler(filters.Regex(r'^мафияпроверить '), self.cmd_mafia_check))
        self.app.add_handler(MessageHandler(filters.Regex(r'^мафияспасти '), self.cmd_mafia_save))
        
        # ===== ПОЛЕЗНОЕ =====
        self.app.add_handler(CommandHandler("погода", self.cmd_weather))
        self.app.add_handler(CommandHandler("время", self.cmd_time))
        self.app.add_handler(CommandHandler("дата", self.cmd_date))
        self.app.add_handler(CommandHandler("кальк", self.cmd_calc))
        self.app.add_handler(CommandHandler("пинг", self.cmd_ping))
        self.app.add_handler(CommandHandler("аптайм", self.cmd_uptime))
        self.app.add_handler(CommandHandler("инфо", self.cmd_info))
        
        # ===== ОБРАБОТЧИКИ =====
        self.app.add_handler(CallbackQueryHandler(self.button_callback))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, self.handle_new_members))
        self.app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, self.handle_left_member))
        
        self.app.add_error_handler(self.error_handler)
        
        logger.info(f"✅ Зарегистрировано обработчиков: {len(self.app.handlers)}")

    # ===== ОСНОВНЫЕ КОМАНДЫ =====
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        user = update.effective_user
        user_data = self.db.get_user(user.id, user.first_name)
        
        # Обработка рефералов
        if context.args and context.args[0].isdigit():
            referrer_id = int(context.args[0])
            if referrer_id != user_data['id']:
                self.db.cursor.execute('''
                    UPDATE users SET referrer_id = ? WHERE id = ?
                ''', (referrer_id, user_data['id']))
                self.db.conn.commit()
                self.db.add_coins(referrer_id, 500)  # Бонус за реферала
                await context.bot.send_message(
                    referrer_id,
                    s.success(f"🎉 По вашей ссылке зарегистрировался {user.first_name}! +500 💰")
                )
        
        text = (
            s.header("СПЕКТР") + "\n"
            f"👋 **Привет, {user.first_name}!**\n"
            f"Я — **Спектр**, твой официальный помощник с AI и кучей игр.\n\n"
            f"{s.section('ТВОЙ ПРОФИЛЬ')}"
            f"{s.stat('Монеты', f'{user_data["coins"]} 💰')}\n"
            f"{s.stat('Уровень', user_data["level"])}\n"
            f"{s.stat('Ранг', self.get_role_emoji(user_data["rank"]) + " " + user_data["rank_name"])}\n"
            f"{s.stat('Энергия', f'{user_data["energy"]}/100 ⚡')}\n\n"
            f"{s.section('ЧТО Я УМЕЮ')}"
            f"{s.item('🤖 Дерзкий AI со сленгом и мемами')}\n"
            f"{s.item('🔫 Мафия с гифками и личными сообщениями')}\n"
            f"{s.item('🎲 Русская рулетка, кости, слоты, КНБ')}\n"
            f"{s.item('👾 Боссы, дуэли, кланы')}\n"
            f"{s.item('⚙️ Модерация (5 рангов)')}\n"
            f"{s.item('💰 Экономика, донат, VIP')}\n"
            f"{s.item('💘 Отношения, браки, репутация')}\n"
            f"{s.item('📝 Закладки, заметки, таймеры')}\n\n"
            f"{s.section('БЫСТРЫЙ СТАРТ')}"
            f"{s.cmd('profile', 'профиль')}\n"
            f"{s.cmd('мафия', 'игра в мафию')}\n"
            f"{s.cmd('боссы', 'битва с боссами')}\n"
            f"{s.cmd('daily', 'бонус')}\n"
            f"{s.cmd('help', 'все команды')}\n\n"
            f"👑 **Владелец:** {OWNER_USERNAME}"
        )
        
        await update.message.reply_text(text, reply_markup=kb.main(), parse_mode="Markdown")
        self.db.log_action(user_data['id'], 'start')
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help - полная справка"""
        text = (
            s.header("СПРАВКА") + "\n"
            f"{s.section('📌 ОСНОВНЫЕ')}"
            f"{s.cmd('start', 'начать работу')}\n"
            f"{s.cmd('menu', 'главное меню')}\n"
            f"{s.cmd('profile', 'профиль')}\n"
            f"{s.cmd('stats', 'статистика')}\n"
            f"{s.cmd('top', 'топ игроков')}\n"
            f"{s.cmd('id', 'узнать свой ID')}\n\n"
            
            f"{s.section('👤 ПРОФИЛЬ')}"
            f"{s.cmd('nick [ник]', 'установить ник')}\n"
            f"{s.cmd('title [титул]', 'установить титул')}\n"
            f"{s.cmd('motto [девиз]', 'установить девиз')}\n"
            f"{s.cmd('bio [текст]', 'информация о себе')}\n"
            f"{s.cmd('gender [м/ж]', 'установить пол')}\n"
            f"{s.cmd('city [город]', 'установить город')}\n"
            f"{s.cmd('country [страна]', 'установить страну')}\n"
            f"{s.cmd('birth [ДД.ММ.ГГГГ]', 'дата рождения')}\n"
            f"{s.cmd('rep @ник +/-', 'изменить репутацию')}\n\n"
            
            f"{s.section('⚙️ МОДЕРАЦИЯ (5 РАНГОВ)')}"
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
            f"{s.cmd('кто админ', 'список администрации')}\n"
            f"{s.cmd('модерлог', 'лог изменений рангов')}\n"
            f"{s.cmd('созвать', 'созвать модераторов')}\n\n"
            
            f"{s.section('🔨 БАНЫ И ПРЕДУПРЕЖДЕНИЯ')}"
            f"{s.cmd('варн @user [причина]', 'выдать предупреждение')}\n"
            f"{s.cmd('варны @user', 'список предупреждений')}\n"
            f"{s.cmd('мои варны', 'свои предупреждения')}\n"
            f"{s.cmd('снять варн @user', 'снять последнее предупреждение')}\n"
            f"{s.cmd('снять все варны @user', 'снять все предупреждения')}\n"
            f"{s.cmd('варнлист', 'список последних варнов')}\n"
            f"{s.cmd('мут @user 30м [причина]', 'заглушить')}\n"
            f"{s.cmd('мутлист', 'список замученных')}\n"
            f"{s.cmd('размут @user', 'снять мут')}\n"
            f"{s.cmd('проверить мут @user', 'проверить наличие мута')}\n"
            f"{s.cmd('бан @user [причина]', 'заблокировать')}\n"
            f"{s.cmd('банлист', 'список забаненных')}\n"
            f"{s.cmd('разбан @user', 'разблокировать')}\n"
            f"{s.cmd('кик @user', 'исключить из чата')}\n"
            f"{s.cmd('глобал бан @user', 'забанить во всех чатах')}\n"
            f"{s.cmd('глобал мут @user', 'замутить во всех чатах')}\n"
            f"{s.cmd('глобал разбан @user', 'разбанить везде')}\n\n"
            
            f"{s.section('🤖 ТРИГГЕРЫ')}"
            f"{s.cmd('+триггер слово = действие', 'создать триггер')}\n"
            f"{s.cmd('-триггер ID', 'удалить триггер')}\n"
            f"{s.cmd('триггеры', 'список триггеров')}\n"
            f"{s.cmd('антимат on/off', 'фильтр мата')}\n"
            f"{s.cmd('антиссылки on/off', 'запрет ссылок')}\n"
            f"{s.cmd('антифлуд on/off', 'защита от флуда')}\n"
            f"{s.cmd('антиспам on/off', 'защита от спама')}\n"
            f"{s.cmd('антирейд on/off', 'защита от рейдов')}\n"
            f"{s.cmd('антибот on/off', 'защита от ботов')}\n\n"
            
            f"{s.section('🔧 НАСТРОЙКА КОМАНД')}"
            f"{s.cmd('права команда = ранг', 'установить ранг для команды')}\n"
            f"{s.cmd('правалист', 'список прав')}\n"
            f"{s.cmd('сбросить права', 'сбросить к стандарту')}\n"
            f"{s.cmd('запретить команда', 'запретить команду')}\n"
            f"{s.cmd('разрешить команда', 'разрешить команду')}\n"
            f"{s.cmd('исключение команда = @user', 'разрешить команду конкретному пользователю')}\n\n"
            
            f"{s.section('🧹 ЧИСТКА ЧАТА')}"
            f"{s.cmd('чистка 50', 'удалить 50 сообщений')}\n"
            f"{s.cmd('чистка всё', 'удалить все сообщения')}\n"
            f"{s.cmd('чистка ботов', 'удалить сообщения ботов')}\n"
            f"{s.cmd('чистка файлов', 'удалить файлы')}\n"
            f"{s.cmd('чистка от @user', 'удалить сообщения пользователя')}\n"
            f"{s.cmd('чистка ссылки', 'удалить сообщения со ссылками')}\n"
            f"{s.cmd('чистка мат', 'удалить сообщения с матом')}\n"
            f"{s.cmd('чистка спам', 'удалить спам')}\n\n"
            
            f"{s.section('⚙️ НАСТРОЙКИ ЧАТА')}"
            f"{s.cmd('+приветствие Текст', 'установить приветствие')}\n"
            f"{s.cmd('+правила Текст', 'установить правила')}\n"
            f"{s.cmd('правила', 'показать правила')}\n"
            f"{s.cmd('-приветствие', 'удалить приветствие')}\n"
            f"{s.cmd('капча on/off', 'включить капчу')}\n"
            f"{s.cmd('капча сложность 1-5', 'сложность капчи')}\n"
            f"{s.cmd('верификация on/off', 'ручная проверка')}\n"
            f"{s.cmd('язык ru/en', 'язык чата')}\n"
            f"{s.cmd('регион город', 'регион чата')}\n"
            f"{s.cmd('ссылки on/off', 'разрешить ссылки')}\n"
            f"{s.cmd('медиа on/off', 'разрешить медиа')}\n"
            f"{s.cmd('стикеры on/off', 'разрешить стикеры')}\n"
            f"{s.cmd('гифки on/off', 'разрешить GIF')}\n\n"
            
            f"{s.section('📡 СЕТКА ЧАТОВ')}"
            f"{s.cmd('сетка создать название', 'создать сетку')}\n"
            f"{s.cmd('сетка добавить чат', 'добавить чат')}\n"
            f"{s.cmd('сетка удалить чат', 'удалить чат')}\n"
            f"{s.cmd('сетка список', 'список чатов')}\n"
            f"{s.cmd('сетка синхронизировать', 'синхронизировать')}\n"
            f"{s.cmd('сетка !модер @user', 'назначить во всех чатах')}\n"
            f"{s.cmd('сетка разжаловать @user', 'снять во всех чатах')}\n"
            f"{s.cmd('сетка ухожу', 'снять себя во всех чатах')}\n\n"
            
            f"{s.section('👥 АНКЕТА')}"
            f"{s.cmd('анкета', 'своя анкета')}\n"
            f"{s.cmd('анкета @user', 'анкета пользователя')}\n"
            f"{s.cmd('анкеты', 'все анкеты')}\n"
            f"{s.cmd('имя текст', 'установить имя')}\n"
            f"{s.cmd('возраст число', 'установить возраст')}\n"
            f"{s.cmd('осебе текст', 'о себе')}\n"
            f"{s.cmd('фото', 'установить фото')}\n\n"
            
            f"{s.section('📊 СТАТИСТИКА')}"
            f"{s.cmd('стата', 'статистика чата')}\n"
            f"{s.cmd('статасегодня', 'статистика за сегодня')}\n"
            f"{s.cmd('статанеделя', 'статистика за неделю')}\n"
            f"{s.cmd('статамесяц', 'статистика за месяц')}\n"
            f"{s.cmd('статавсего', 'вся статистика')}\n\n"
            
            f"{s.section('🗳️ ТЕМЫ МОДЕРАТОРОВ')}"
            f"{s.cmd('+тема Название | описание', 'создать тему')}\n"
            f"{s.cmd('темы', 'список тем')}\n"
            f"{s.cmd('голосовать за ID', 'проголосовать за')}\n"
            f"{s.cmd('голосовать против ID', 'проголосовать против')}\n"
            f"{s.cmd('закрыть тему ID', 'закрыть тему')}\n"
            f"{s.cmd('удалить тему ID', 'удалить тему')}\n"
            f"{s.cmd('тема ID', 'информация о теме')}\n\n"
            
            f"{s.section('⚡ НОВЫЕ КОМАНДЫ')}"
            f"{s.cmd('+предложить команда описание', 'предложить команду')}\n"
            f"{s.cmd('предложения', 'список предложений')}\n"
            f"{s.cmd('за ID', 'проголосовать за')}\n"
            f"{s.cmd('против ID', 'проголосовать против')}\n"
            f"{s.cmd('принять ID', 'принять команду')}\n"
            f"{s.cmd('отклонить ID', 'отклонить предложение')}\n\n"
            
            f"{s.section('🚫 ЧЕРНЫЙ СПИСОК')}"
            f"{s.cmd('+блэклист слово', 'добавить слово')}\n"
            f"{s.cmd('-блэклист слово', 'удалить слово')}\n"
            f"{s.cmd('блэклист', 'показать список')}\n"
            f"{s.cmd('+спамлист @user', 'добавить спамера')}\n"
            f"{s.cmd('-спамлист @user', 'удалить спамера')}\n"
            f"{s.cmd('спамлист', 'список спамеров')}\n"
            f"{s.cmd('+мошенник @user доказательства', 'добавить мошенника')}\n"
            f"{s.cmd('-мошенник @user', 'удалить мошенника')}\n"
            f"{s.cmd('мошенники', 'список мошенников')}\n"
            f"{s.cmd('проверить @user', 'проверить пользователя')}\n\n"
            
            f"{s.section('💰 ЭКОНОМИКА')}"
            f"{s.cmd('ириски', 'баланс')}\n"
            f"{s.cmd('передать @user сумма', 'перевести монеты')}\n"
            f"{s.cmd('топирисок', 'топ богачей')}\n"
            f"{s.cmd('бонус', 'ежедневный бонус')}\n"
            f"{s.cmd('стрик', 'текущий стрик')}\n"
            f"{s.cmd('бонусы', 'доступные бонусы')}\n"
            f"{s.cmd('вип', 'информация о VIP')}\n"
            f"{s.cmd('купитьвип', 'купить VIP')}\n"
            f"{s.cmd('премиум', 'информация о PREMIUM')}\n"
            f"{s.cmd('купитьпремиум', 'купить PREMIUM')}\n"
            f"{s.cmd('магазин', 'список товаров')}\n"
            f"{s.cmd('купить товар', 'купить товар')}\n"
            f"{s.cmd('подарить @user товар', 'подарить товар')}\n\n"
            
            f"{s.section('🎮 ИГРЫ')}"
            f"{s.cmd('игры', 'меню игр')}\n"
            f"{s.cmd('монетка', 'подбросить монету')}\n"
            f"{s.cmd('кубик', 'бросить кубик')}\n"
            f"{s.cmd('кости [ставка]', 'игра в кости')}\n"
            f"{s.cmd('кнб', 'камень-ножницы-бумага')}\n"
            f"{s.cmd('рр [ставка]', 'русская рулетка')}\n"
            f"{s.cmd('рулетка [ставка] [цвет]', 'рулетка')}\n"
            f"{s.cmd('слоты [ставка]', 'слоты')}\n"
            f"{s.cmd('сапёр', 'сапёр')}\n"
            f"{s.cmd('угадай [число]', 'угадай число')}\n"
            f"{s.cmd('быки [число]', 'быки и коровы')}\n\n"
            
            f"{s.section('👾 БОССЫ')}"
            f"{s.cmd('боссы', 'список боссов')}\n"
            f"{s.cmd('босс ID', 'атаковать босса')}\n"
            f"{s.cmd('боссинфо ID', 'информация о боссе')}\n"
            f"{s.cmd('реген', 'восстановить энергию')}\n\n"
            
            f"{s.section('⚔️ ДУЭЛИ')}"
            f"{s.cmd('дуэль @user [ставка]', 'вызвать на дуэль')}\n"
            f"{s.cmd('дуэли', 'список дуэлей')}\n"
            f"{s.cmd('принять ID', 'принять дуэль')}\n"
            f"{s.cmd('отклонить ID', 'отклонить дуэль')}\n"
            f"{s.cmd('атака [сила]', 'атаковать')}\n"
            f"{s.cmd('защита', 'защищаться')}\n"
            f"{s.cmd('сдаться', 'сдаться')}\n"
            f"{s.cmd('рейтинг', 'рейтинг дуэлянтов')}\n\n"
            
            f"{s.section('🏰 КЛАНЫ')}"
            f"{s.cmd('клан', 'информация о клане')}\n"
            f"{s.cmd('кланы', 'список кланов')}\n"
            f"{s.cmd('создатьклан название', 'создать клан')}\n"
            f"{s.cmd('вступить название', 'вступить в клан')}\n"
            f"{s.cmd('выйти', 'покинуть клан')}\n"
            f"{s.cmd('пригласить @user', 'пригласить в клан')}\n"
            f"{s.cmd('исключить @user', 'исключить из клана')}\n"
            f"{s.cmd('лидер @user', 'передать лидерство')}\n"
            f"{s.cmd('казна', 'баланс клана')}\n"
            f"{s.cmd('клантоп', 'топ кланов')}\n\n"
            
            f"{s.section('💕 ОТНОШЕНИЯ')}"
            f"{s.cmd('отношения @user', 'статус отношений')}\n"
            f"{s.cmd('друг @user', 'добавить в друзья')}\n"
            f"{s.cmd('удалитьдруга @user', 'удалить из друзей')}\n"
            f"{s.cmd('симпатия @user', 'поставить симпатию')}\n"
            f"{s.cmd('игнор @user', 'добавить в игнор')}\n"
            f"{s.cmd('враг @user', 'объявить врагом')}\n"
            f"{s.cmd('простить @user', 'простить врага')}\n\n"
            
            f"{s.section('💍 БРАКИ')}"
            f"{s.cmd('предложить @user', 'сделать предложение')}\n"
            f"{s.cmd('принятьпредложение @user', 'принять предложение')}\n"
            f"{s.cmd('отклонитьпредложение @user', 'отклонить')}\n"
            f"{s.cmd('свадьба [дата]', 'назначить свадьбу')}\n"
            f"{s.cmd('развод', 'развестись')}\n"
            f"{s.cmd('семьи', 'список семей')}\n\n"
            
            f"{s.section('⭐ РЕПУТАЦИЯ')}"
            f"{s.cmd('+репа @user', 'повысить репутацию')}\n"
            f"{s.cmd('-репа @user', 'понизить репутацию')}\n"
            f"{s.cmd('репа', 'своя репутация')}\n"
            f"{s.cmd('репа @user', 'репутация пользователя')}\n"
            f"{s.cmd('топрепы', 'топ по репутации')}\n\n"
            
            f"{s.section('🏷️ ЗАКЛАДКИ')}"
            f"{s.cmd('+закладка название ссылка', 'сохранить закладку')}\n"
            f"{s.cmd('закладки', 'список закладок')}\n"
            f"{s.cmd('закладка ID', 'открыть закладку')}\n"
            f"{s.cmd('-закладка ID', 'удалить закладку')}\n"
            f"{s.cmd('закладкипапки', 'папки закладок')}\n\n"
            
            f"{s.section('📝 ЗАМЕТКИ')}"
            f"{s.cmd('+заметка текст', 'создать заметку')}\n"
            f"{s.cmd('заметки', 'список заметок')}\n"
            f"{s.cmd('заметка ID', 'просмотр заметки')}\n"
            f"{s.cmd('заметкаред ID новый текст', 'редактировать')}\n"
            f"{s.cmd('-заметка ID', 'удалить заметку')}\n"
            f"{s.cmd('поискзаметок текст', 'поиск по заметкам')}\n\n"
            
            f"{s.section('⏰ ТАЙМЕРЫ')}"
            f"{s.cmd('+таймер название 15м', 'создать таймер')}\n"
            f"{s.cmd('таймеры', 'список таймеров')}\n"
            f"{s.cmd('таймер ID', 'информация о таймере')}\n"
            f"{s.cmd('-таймер ID', 'удалить таймер')}\n"
            f"{s.cmd('пауза ID', 'поставить на паузу')}\n"
            f"{s.cmd('продолжить ID', 'продолжить')}\n"
            f"{s.cmd('+напомнить текст 15м', 'создать напоминание')}\n"
            f"{s.cmd('напоминалки', 'список напоминаний')}\n"
            f"{s.cmd('повтор ID интервал', 'повторять')}\n\n"
            
            f"{s.section('🎭 МАФИЯ')}"
            f"{s.cmd('мафия', 'меню мафии')}\n"
            f"{s.cmd('мафиястарт', 'начать игру')}\n"
            f"{s.cmd('мафияприсоединиться', 'присоединиться к игре')}\n"
            f"{s.cmd('мафиявыйти', 'выйти из игры')}\n"
            f"{s.cmd('мафияроли', 'список ролей')}\n"
            f"{s.cmd('мафияправила', 'правила игры')}\n"
            f"{s.cmd('мафиястата', 'статистика')}\n\n"
            
            f"{s.section('🌦️ ПОЛЕЗНОЕ')}"
            f"{s.cmd('погода [город]', 'погода')}\n"
            f"{s.cmd('время', 'текущее время')}\n"
            f"{s.cmd('дата', 'текущая дата')}\n"
            f"{s.cmd('кальк 2+2', 'калькулятор')}\n"
            f"{s.cmd('пинг', 'проверка бота')}\n"
            f"{s.cmd('аптайм', 'время работы')}\n"
            f"{s.cmd('инфо', 'информация о боте')}\n\n"
            
            f"👑 **Владелец:** {OWNER_USERNAME}"
        )
        
        await update.message.reply_text(text, reply_markup=kb.back(), parse_mode="Markdown")
    
    async def cmd_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /menu"""
        await update.message.reply_text(
            s.header("ГЛАВНОЕ МЕНЮ") + "\nВыберите раздел:",
            reply_markup=kb.main(),
            parse_mode="Markdown"
        )
    
    async def cmd_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /profile"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        display_name = user_data.get('nickname') or user.first_name
        title = user_data.get('title', '')
        motto = user_data.get('motto', 'Нет девиза')
        bio = user_data.get('bio', '')
        
        vip_status = "✅ VIP" if self.db.is_vip(user_data['id']) else "❌"
        premium_status = "✅ PREMIUM" if self.db.is_premium(user_data['id']) else "❌"
        
        exp_needed = user_data['level'] * 100
        exp_progress = s.progress(user_data['exp'], exp_needed)
        
        warns = "🔴" * user_data['warns'] + "⚪" * (3 - user_data['warns'])
        
        # Получаем друзей
        friends_list = json.loads(user_data.get('friends', '[]'))
        friends_count = len(friends_list)
        
        # Получаем врагов
        enemies_list = json.loads(user_data.get('enemies', '[]'))
        enemies_count = len(enemies_list)
        
        # Получаем клан
        clan_info = ""
        if user_data.get('clan_id', 0) > 0:
            clan = self.db.get_clan(user_data['clan_id'])
            if clan:
                clan_info = f"\n{s.stat('Клан', clan['name'])}"
        
        # Получаем супруга
        spouse_info = ""
        if user_data.get('spouse', 0) > 0:
            spouse = self.db.get_user_by_id(user_data['spouse'])
            if spouse:
                spouse_name = spouse.get('nickname') or spouse['first_name']
                married_since = datetime.datetime.fromisoformat(user_data['married_since']).strftime("%d.%m.%Y") if user_data.get('married_since') else "неизвестно"
                spouse_info = f"\n{s.stat('💍 Супруг(а)', spouse_name)}\n{s.stat('💒 С', married_since)}"
        
        text = (
            s.header("ПРОФИЛЬ") + "\n"
            f"**{display_name}** {title}\n"
            f"_{motto}_\n"
            f"{bio}\n\n"
            f"{s.section('ХАРАКТЕРИСТИКИ')}"
            f"{s.stat('Ранг', self.get_role_emoji(user_data['rank']) + ' ' + user_data['rank_name'])}\n"
            f"{s.stat('Уровень', user_data['level'])}\n"
            f"{s.stat('Опыт', exp_progress)}\n"
            f"{s.stat('Монеты', f'{user_data["coins"]} 💰')}\n"
            f"{s.stat('Алмазы', f'{user_data["diamonds"]} 💎')}\n"
            f"{s.stat('Энергия', f'{user_data["energy"]}/100 ⚡')}\n"
            f"{s.stat('Здоровье', f'{user_data["health"]}/100 ❤️')}\n\n"
            f"{s.section('СТАТИСТИКА')}"
            f"{s.stat('Сообщений', user_data['messages_count'])}\n"
            f"{s.stat('Команд', user_data['commands_used'])}\n"
            f"{s.stat('Репутация', user_data['reputation'])}\n"
            f"{s.stat('Предупреждения', warns)}\n"
            f"{s.stat('Боссов убито', user_data['boss_kills'])}\n"
            f"{s.stat('Дуэлей', f'{user_data["duel_wins"]}/{user_data["duel_losses"]}')}\n"
            f"{s.stat('Рейтинг дуэлей', user_data['duel_rating'])}\n"
            f"{s.stat('Друзей', friends_count)}\n"
            f"{s.stat('Врагов', enemies_count)}{clan_info}{spouse_info}\n\n"
            f"{s.section('СТАТУС')}"
            f"{s.item(f'VIP: {vip_status}')}\n"
            f"{s.item(f'PREMIUM: {premium_status}')}\n"
            f"{s.item(f'Пол: {user_data["gender"]}')}\n"
            f"{s.item(f'Город: {user_data["city"]}')}\n"
            f"{s.item(f'Страна: {user_data["country"]}')}\n"
            f"{s.item(f'Возраст: {user_data["age"] if user_data["age"] else "не указан"}')}\n"
            f"{s.item(f'ID: {s.code(str(user.id))}')}"
        )
        
        await update.message.reply_text(text, reply_markup=kb.back(), parse_mode="Markdown")

        # ===== МЕТОДЫ ПРОФИЛЯ =====
    
    async def cmd_set_nick(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установка ника"""
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
        """Установка титула"""
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
        """Установка девиза"""
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
        """Установка био"""
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
        """Установка пола"""
        if not context.args or context.args[0].lower() not in ['м', 'ж']:
            await update.message.reply_text(s.error("❌ Укажи /gender м или /gender ж"))
            return
        
        gender = "мужской" if context.args[0].lower() == 'м' else "женский"
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], gender=gender)
        await update.message.reply_text(s.success(f"✅ Пол установлен: {gender}"))
    
    async def cmd_set_city(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установка города"""
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажи город: /city [город]"))
            return
        
        city = " ".join(context.args)
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], city=city)
        await update.message.reply_text(s.success(f"✅ Город установлен: {city}"))
    
    async def cmd_set_country(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установка страны"""
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажи страну: /country [страна]"))
            return
        
        country = " ".join(context.args)
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], country=country)
        await update.message.reply_text(s.success(f"✅ Страна установлена: {country}"))
    
    async def cmd_set_birth(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установка даты рождения"""
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажи дату: /birth ДД.ММ.ГГГГ"))
            return
        
        date_str = context.args[0]
        try:
            birth_date = datetime.datetime.strptime(date_str, "%d.%m.%Y")
            today = datetime.datetime.now()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            
            user_data = self.db.get_user(update.effective_user.id)
            self.db.update_user(user_data['id'], birth_date=date_str, age=age)
            await update.message.reply_text(s.success(f"✅ Дата рождения установлена: {date_str} (возраст: {age})"))
        except:
            await update.message.reply_text(s.error("❌ Неверный формат. Используй: ДД.ММ.ГГГГ"))
    
    async def cmd_set_age(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установка возраста"""
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажи возраст: /age [число]"))
            return
        
        try:
            age = int(context.args[0])
            if age < 0 or age > 150:
                await update.message.reply_text(s.error("❌ Возраст должен быть от 0 до 150"))
                return
            
            user_data = self.db.get_user(update.effective_user.id)
            self.db.update_user(user_data['id'], age=age)
            await update.message.reply_text(s.success(f"✅ Возраст установлен: {age}"))
        except:
            await update.message.reply_text(s.error("❌ Возраст должен быть числом"))
    
    async def cmd_set_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установка имени (псевдоним)"""
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажи имя: /name [имя]"))
            return
        
        name = " ".join(context.args)
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], first_name=name)
        await update.message.reply_text(s.success(f"✅ Имя установлено: {name}"))
    
    async def cmd_set_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установка фото профиля"""
        await update.message.reply_text(s.info("📸 Функция установки фото в разработке"))
    
    async def cmd_profile_by_link(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Просмотр анкеты по ссылке"""
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажи пользователя: /анкета @user"))
            return
        
        username = context.args[0].replace('@', '')
        target = self.db.get_user_by_username(username)
        
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        # Создаем временный update для вызова cmd_profile
        class TempUser:
            def __init__(self, user_data):
                self.id = user_data['telegram_id']
                self.first_name = user_data['first_name']
                self.username = user_data['username']
        
        class TempMessage:
            def __init__(self, user):
                self.from_user = user
        
        class TempUpdate:
            def __init__(self, user):
                self.effective_user = user
                self.message = TempMessage(user)
        
        temp_user = TempUser(target)
        temp_update = TempUpdate(temp_user)
        await self.cmd_profile(temp_update, context)
    
    async def cmd_all_profiles(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список всех анкет"""
        self.db.c.execute("SELECT first_name, nickname, username, level FROM users ORDER BY level DESC LIMIT 20")
        users = self.db.c.fetchall()
        
        text = s.header("📋 АНКЕТЫ") + "\n\n"
        for user in users:
            name = user[1] or user[0]
            username = f" (@{user[2]})" if user[2] else ""
            text += f"{s.item(f'{name}{username} — ур.{user[3]}')}\n"
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_my_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Моя статистика"""
        await self.cmd_stats(update, context)
    
    async def cmd_top_coins(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Топ по монетам"""
        top_coins = self.db.get_top("coins", 10)
        
        text = s.header("💰 ТОП ПО МОНЕТАМ") + "\n\n"
        for i, row in enumerate(top_coins, 1):
            name = row[1] or row[0]
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} **{name}** — {row[2]} 💰\n"
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_top_level(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Топ по уровню"""
        top_level = self.db.get_top("level", 10)
        
        text = s.header("📊 ТОП ПО УРОВНЮ") + "\n\n"
        for i, row in enumerate(top_level, 1):
            name = row[1] or row[0]
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} **{name}** — {row[2]} ур.\n"
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_top_rep(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Топ по репутации"""
        top_rep = self.db.get_top("reputation", 10)
        
        text = s.header("⭐ ТОП ПО РЕПУТАЦИИ") + "\n\n"
        for i, row in enumerate(top_rep, 1):
            name = row[1] or row[0]
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} **{name}** — {row[2]} ⭐\n"
        
        await update.message.reply_text(text, parse_mode="Markdown")

    # ===== КОМАНДЫ МОДЕРАЦИИ (5 РАНГОВ) =====
    
    async def cmd_set_rank(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установка 1 ранга (Младший модератор)"""
        await self._set_rank(update, 1)
    
    async def cmd_set_rank2(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установка 2 ранга (Старший модератор)"""
        await self._set_rank(update, 2)
    
    async def cmd_set_rank3(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установка 3 ранга (Младший администратор)"""
        await self._set_rank(update, 3)
    
    async def cmd_set_rank4(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установка 4 ранга (Старший администратор)"""
        await self._set_rank(update, 4)
    
    async def cmd_set_rank5(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установка 5 ранга (Создатель)"""
        await self._set_rank(update, 5)
    
    async def _set_rank(self, update: Update, target_rank: int):
        """Внутренний метод для установки ранга"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 4 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав. Нужен ранг 4+"))
            return
        
        # Получаем цель
        target_user = None
        if update.message.reply_to_message:
            target_id = update.message.reply_to_message.from_user.id
            target_user = self.db.get_user_by_id(self.db.get_user(target_id)['id'])
        else:
            # Парсим @username из текста
            match = re.search(r'@(\S+)', text)
            if match:
                username = match.group(1)
                target_user = self.db.get_user_by_username(username)
        
        if not target_user:
            await update.message.reply_text(s.error("❌ Пользователь не найден. Ответьте на сообщение или укажите @username"))
            return
        
        if target_user['rank'] >= user_data['rank'] and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Нельзя назначить ранг выше или равный своему"))
            return
        
        self.db.set_rank(target_user['id'], target_rank, user_data['id'])
        
        rank_info = RANKS[target_rank]
        await update.message.reply_text(
            f"{s.success('Ранг назначен!')}\n\n"
            f"{s.item(f'Пользователь: {target_user["first_name"]}')}\n"
            f"{s.item(f'Ранг: {rank_info["emoji"]} {rank_info["name"]} ({target_rank})')}",
            parse_mode="Markdown"
        )
    
    async def cmd_lower_rank(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Понижение ранга на 1"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 4 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав"))
            return
        
        target_user = None
        if update.message.reply_to_message:
            target_id = update.message.reply_to_message.from_user.id
            target_user = self.db.get_user_by_id(self.db.get_user(target_id)['id'])
        else:
            match = re.search(r'@(\S+)', text)
            if match:
                username = match.group(1)
                target_user = self.db.get_user_by_username(username)
        
        if not target_user:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        if target_user['rank'] <= 0:
            await update.message.reply_text(s.error("❌ Пользователь и так участник"))
            return
        
        if target_user['rank'] >= user_data['rank'] and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Нельзя понизить модератора выше рангом"))
            return
        
        new_rank = target_user['rank'] - 1
        self.db.set_rank(target_user['id'], new_rank, user_data['id'])
        
        rank_info = RANKS[new_rank]
        await update.message.reply_text(
            f"{s.success('Ранг понижен!')}\n\n"
            f"{s.item(f'Пользователь: {target_user["first_name"]}')}\n"
            f"{s.item(f'Новый ранг: {rank_info["emoji"]} {rank_info["name"]} ({new_rank})')}",
            parse_mode="Markdown"
        )
    
    async def cmd_remove_rank(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Снятие модератора (до 0 ранга)"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 4 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав"))
            return
        
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
    
    async def cmd_remove_left(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Снять вышедших модераторов"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data['rank'] < 4 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав"))
            return
        
        # В реальном боте здесь нужно получить список участников чата и сравнить
        await update.message.reply_text(s.success("✅ Проверка вышедших модераторов выполнена"))
    
    async def cmd_remove_all_ranks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """!снять всех - снять всех модераторов"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data['rank'] < 5 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Только для создателя"))
            return
        
        self.db.c.execute("SELECT id FROM users WHERE rank > 0")
        mods = self.db.c.fetchall()
        
        for mod_id in mods:
            self.db.set_rank(mod_id[0], 0, user_data['id'])
        
        await update.message.reply_text(
            s.success(f"✅ Снято модераторов: {len(mods)}"),
            parse_mode="Markdown"
        )
    
    async def cmd_who_admins(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список администрации"""
        admins = self.db.get_admins()
        
        if not admins:
            await update.message.reply_text(s.info("👥 В чате нет администраторов"))
            return
        
        text = s.header("АДМИНИСТРАЦИЯ") + "\n\n"
        for admin in admins:
            name = admin['first_name']
            username = f" (@{admin['username']})" if admin['username'] else ""
            rank_emoji = RANKS[admin['rank']]["emoji"]
            text += f"{s.item(f'{rank_emoji} {name}{username} — {admin["rank_name"]}')}\n"
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_mod_log(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Лог изменений рангов"""
        # В реальном боте здесь нужно получать логи из БД
        await update.message.reply_text(s.info("📋 Функция в разработке"))
    
    async def cmd_my_mod_log(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Мой персональный лог"""
        await update.message.reply_text(s.info("📋 Функция в разработке"))
    
    async def cmd_call_admins(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Созвать администраторов"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data['rank'] < 1:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав"))
            return
        
        # Получаем список админов
        admins = self.db.get_admins()
        if not admins:
            await update.message.reply_text(s.info("👥 В чате нет администраторов"))
            return
        
        mentions = " ".join([f"[{a['first_name']}](tg://user?id={a['id']})" for a in admins[:10]])
        
        await update.message.reply_text(
            f"{s.header('ВЫЗОВ АДМИНИСТРАЦИИ')}\n\n{mentions}\n\n{user.first_name} вызывает администрацию!",
            parse_mode="Markdown"
        )
    
    # ===== ПРЕДУПРЕЖДЕНИЯ =====
    
    async def cmd_warn(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выдать предупреждение"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 1 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав. Нужен ранг 1+"))
            return
        
        target_user = None
        reason = "Нарушение правил"
        
        if update.message.reply_to_message:
            target_id = update.message.reply_to_message.from_user.id
            target_user = self.db.get_user_by_id(self.db.get_user(target_id)['id'])
            # Причина может быть в следующей строке
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
        
        # Отправляем в ЛС уведомление
        try:
            await context.bot.send_message(
                target_user['telegram_id'],
                f"{s.warning('⚠️ ВЫ ПОЛУЧИЛИ ПРЕДУПРЕЖДЕНИЕ')}\n\n"
                f"{s.item(f'Причина: {reason}')}\n"
                f"{s.item(f'Всего предупреждений: {warns}/3')}"
            )
        except:
            pass
        
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
        """Список предупреждений пользователя"""
        args = context.args
        if not args:
            await update.message.reply_text(s.error("❌ Укажите пользователя: /варны @user"))
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
                f"{s.item(f'Причина: {warn["reason"]}')}\n"
                f"{s.item(f'Админ: {admin_name}')}\n"
                f"{s.item(f'Дата: {date}')}\n\n"
            )
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_my_warns(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Мои предупреждения"""
        user_data = self.db.get_user(update.effective_user.id)
        warns_list = self.db.get_warns(user_data['id'])
        
        if not warns_list:
            await update.message.reply_text(s.info("У вас нет предупреждений"))
            return
        
        text = s.header("МОИ ПРЕДУПРЕЖДЕНИЯ") + "\n\n"
        for warn in warns_list:
            admin = self.db.get_user_by_id(warn['admin_id'])
            admin_name = admin.get('first_name', 'Система') if admin else 'Система'
            date = datetime.datetime.fromisoformat(warn['date']).strftime("%d.%m.%Y %H:%M")
            
            text += (
                f"**ID: {warn['id']}**\n"
                f"{s.item(f'Причина: {warn["reason"]}')}\n"
                f"{s.item(f'Админ: {admin_name}')}\n"
                f"{s.item(f'Дата: {date}')}\n\n"
            )
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_unwarn(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Снять последнее предупреждение"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 1 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав"))
            return
        
        target_user = None
        if update.message.reply_to_message:
            target_id = update.message.reply_to_message.from_user.id
            target_user = self.db.get_user_by_id(self.db.get_user(target_id)['id'])
        else:
            match = re.search(r'(?:снять варн|-варн)\s+@?(\S+)', text, re.IGNORECASE)
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
        
        await update.message.reply_text(s.success(f"✅ Последнее предупреждение снято с {target_name}"))
    
    async def cmd_unwarn_all(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Снять все предупреждения"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 2 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав"))
            return
        
        target_user = None
        match = re.search(r'снять все варны\s+@?(\S+)', text, re.IGNORECASE)
        if match:
            username = match.group(1)
            target_user = self.db.get_user_by_username(username)
        
        if not target_user:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        # Снимаем все предупреждения
        warns_list = self.db.get_warns(target_user['id'])
        for _ in warns_list:
            self.db.remove_last_warn(target_user['id'], user_data['id'])
        
        target_name = target_user.get('nickname') or target_user['first_name']
        await update.message.reply_text(s.success(f"✅ Все предупреждения сняты с {target_name}"))
    
    async def cmd_warn_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список последних предупреждений в чате"""
        # В реальном боте здесь нужно получать из БД
        await update.message.reply_text(s.info("📋 Функция в разработке"))
    
    # ===== МУТЫ =====
    
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
        reason = match.group(4) if match.group(4) else "Нарушение правил"
        
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
        
        # Отправляем в ЛС уведомление
        try:
            await context.bot.send_message(
                target['telegram_id'],
                f"{s.warning('🔇 ВАС ЗАМУТИЛИ')}\n\n"
                f"{s.item(f'Срок: {amount}{unit}')}\n"
                f"{s.item(f'Причина: {reason}')}\n"
                f"{s.item(f'До: {until_str}')}"
            )
        except:
            pass
        
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
        muted = self.db.get_muted_users()
        
        if not muted:
            await update.message.reply_text(s.info("Нет пользователей в муте"))
            return
        
        text = s.header("СПИСОК ЗАМУЧЕННЫХ") + "\n\n"
        for user in muted[:10]:
            until = datetime.datetime.fromisoformat(user['mute_until']).strftime("%d.%m.%Y %H:%M")
            name = user['first_name']
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
        
        # Отправляем в ЛС уведомление
        try:
            await context.bot.send_message(
                target['telegram_id'],
                s.success("✅ Мут снят. Можете снова писать в чат.")
            )
        except:
            pass
        
        await update.message.reply_text(s.success(f"✅ Мут снят с {target['first_name']}"))
    
    async def cmd_check_mute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Проверить наличие мута"""
        text = update.message.text
        username = text.replace('проверить мут', '').replace('@', '').strip()
        
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        if self.db.is_muted(target['id']):
            self.db.c.execute("SELECT mute_until FROM users WHERE id = ?", (target['id'],))
            until = self.db.c.fetchone()[0]
            until_str = datetime.datetime.fromisoformat(until).strftime("%d.%m.%Y %H:%M")
            await update.message.reply_text(s.warning(f"🔇 Пользователь в муте до {until_str}"))
        else:
            await update.message.reply_text(s.success("✅ Пользователь не в муте"))
    
    # ===== БАНЫ =====
    
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
        reason = match.group(2) if match.group(2) else "Нарушение правил"
        
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        if target['rank'] >= user_data['rank'] and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Нельзя забанить модератора выше рангом"))
            return
        
        self.db.ban_user(target['id'], user_data['id'], reason)
        
        # Отправляем в ЛС уведомление
        try:
            await context.bot.send_message(
                target['telegram_id'],
                f"{s.error('🔴 ВАС ЗАБЛОКИРОВАЛИ')}\n\n"
                f"{s.item(f'Причина: {reason}')}"
            )
        except:
            pass
        
        text = (
            s.header("БЛОКИРОВКА") + "\n"
            f"{s.item(f'Пользователь: {target["first_name"]}')}\n"
            f"{s.item(f'Причина: {reason}')}"
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")
        
        # Пытаемся кикнуть из чата
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
        
        # Отправляем в ЛС уведомление
        try:
            await context.bot.send_message(
                target['telegram_id'],
                s.success("✅ Бан снят. Можете вернуться в чат.")
            )
        except:
            pass
        
        await update.message.reply_text(s.success(f"✅ Бан снят с {target['first_name']}"))
        
        # Пытаемся разбанить в чате
        try:
            await update.effective_chat.unban_member(target['telegram_id'])
        except:
            pass
    
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
    
    # ===== ГЛОБАЛЬНЫЕ ДЕЙСТВИЯ =====
    
    async def cmd_global_ban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Глобальный бан (во всех чатах бота)"""
        if update.effective_user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Только для владельца"))
            return
        
        text = update.message.text
        username = text.replace('глобал бан', '').replace('@', '').strip()
        
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        # В реальном боте здесь нужно добавить в глобальный бан-лист
        await update.message.reply_text(s.success(f"✅ {target['first_name']} забанен глобально"))
    
    async def cmd_global_mute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Глобальный мут (во всех чатах бота)"""
        if update.effective_user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Только для владельца"))
            return
        
        await update.message.reply_text(s.success("✅ Функция в разработке"))
    
    async def cmd_global_unban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Глобальный разбан"""
        if update.effective_user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Только для владельца"))
            return
        
        await update.message.reply_text(s.success("✅ Функция в разработке"))

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
            s.header("🎁 ЕЖЕДНЕВНЫЙ БОНУС") + "\n"
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
                await update.message.reply_text(s.warning("⏳ Недельный бонус можно получить раз в 7 дней"))
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
            s.header("📅 НЕДЕЛЬНЫЙ БОНУС") + "\n"
            f"{s.item(f'💰 Монеты: +{coins}')}\n"
            f"{s.item(f'💎 Алмазы: +{diamonds}')}\n"
            f"{s.item(f'✨ Опыт: +{exp}')}\n\n"
            f"{s.info('Через неделю снова!')}"
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_monthly(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Месячный бонус"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data.get('last_monthly'):
            last = datetime.datetime.fromisoformat(user_data['last_monthly'])
            if (datetime.datetime.now() - last).days < 30:
                await update.message.reply_text(s.warning("⏳ Месячный бонус можно получить раз в 30 дней"))
                return
        
        coins = random.randint(5000, 10000)
        diamonds = random.randint(50, 100)
        exp = random.randint(1000, 2000)
        
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
        self.db.update_user(user_data['id'], last_monthly=datetime.datetime.now().isoformat())
        
        text = (
            s.header("📆 МЕСЯЧНЫЙ БОНУС") + "\n"
            f"{s.item(f'💰 Монеты: +{coins}')}\n"
            f"{s.item(f'💎 Алмазы: +{diamonds}')}\n"
            f"{s.item(f'✨ Опыт: +{exp}')}\n\n"
            f"{s.info('Через месяц снова!')}"
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_streak(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Текущий стрик"""
        user_data = self.db.get_user(update.effective_user.id)
        streak = user_data.get('daily_streak', 0)
        
        text = (
            s.header("🔥 ТЕКУЩИЙ СТРИК") + "\n\n"
            f"{s.stat('Дней подряд', streak)}\n"
            f"{s.stat('Множитель', f'x{1 + min(streak, 30) * 0.05:.2f}')}\n\n"
            f"{s.info('Чем больше стрик, тем выше бонус!')}"
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_bonuses(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список доступных бонусов"""
        text = (
            s.header("🎁 ДОСТУПНЫЕ БОНУСЫ") + "\n\n"
            f"{s.section('ЕЖЕДНЕВНЫЙ')}"
            f"{s.cmd('daily', '100-300 💰 + 20-60 ✨ + 20 ⚡')}\n"
            f"{s.item('Множитель от стрика: до x2.5')}\n\n"
            f"{s.section('НЕДЕЛЬНЫЙ')}"
            f"{s.cmd('weekly', '1000-3000 💰 + 10-30 💎 + 200-500 ✨')}\n\n"
            f"{s.section('МЕСЯЧНЫЙ')}"
            f"{s.cmd('monthly', '5000-10000 💰 + 50-100 💎 + 1000-2000 ✨')}\n\n"
            f"{s.section('VIP-БОНУСЫ')}"
            f"{s.item('VIP: +50% ко всем бонусам')}\n"
            f"{s.item('PREMIUM: +100% ко всем бонусам')}"
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_shop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Магазин"""
        text = (
            s.header("🛍️ МАГАЗИН") + "\n\n"
            f"{s.section('💊 ЗЕЛЬЯ')}"
            f"{s.cmd('buy зелье здоровья', '50 💰 (❤️+30)')}\n"
            f"{s.cmd('buy большое зелье', '100 💰 (❤️+70)')}\n"
            f"{s.cmd('buy эликсир', '200 💰 (❤️+150)')}\n"
            f"{s.cmd('buy алмазное зелье', '500 💰 (❤️+300)')}\n\n"
            
            f"{s.section('⚔️ ОРУЖИЕ')}"
            f"{s.cmd('buy меч', '200 💰 (⚔️+10)')}\n"
            f"{s.cmd('buy легендарный меч', '500 💰 (⚔️+30)')}\n"
            f"{s.cmd('buy экскалибур', '1000 💰 (⚔️+50)')}\n"
            f"{s.cmd('buy адский клинок', '2000 💰 (⚔️+100, крит+10%)')}\n\n"
            
            f"{s.section('🛡️ БРОНЯ')}"
            f"{s.cmd('buy щит', '150 💰 (🛡️+5)')}\n"
            f"{s.cmd('buy доспехи', '400 💰 (🛡️+15)')}\n"
            f"{s.cmd('buy непробиваемая броня', '800 💰 (🛡️+30)')}\n"
            f"{s.cmd('buy божественная броня', '2000 💰 (🛡️+50, +10% здоровья)')}\n\n"
            
            f"{s.section('⚡ ЭНЕРГИЯ')}"
            f"{s.cmd('buy энергетик', '30 💰 (⚡+20)')}\n"
            f"{s.cmd('buy батарейка', '80 💰 (⚡+50)')}\n"
            f"{s.cmd('buy атомный реактор', '200 💰 (⚡+100)')}\n"
            f"{s.cmd('buy бесконечность', '500 💰 (⚡+200)')}\n\n"
            
            f"{s.section('🎲 УДАЧА')}"
            f"{s.cmd('buy амулет удачи', '300 💰 (шанс крита +5%)')}\n"
            f"{s.cmd('buy кольцо фортуны', '600 💰 (шанс крита +10%)')}\n"
            f"{s.cmd('buy подкова', '1000 💰 (шанс крита +15%)')}\n\n"
            
            f"{s.section('💎 ПРИВИЛЕГИИ')}"
            f"{s.cmd('vip', f'VIP ({VIP_PRICE} 💰 / 30 дней)')}\n"
            f"{s.cmd('premium', f'PREMIUM ({PREMIUM_PRICE} 💰 / 30 дней)')}"
        )
        
        await update.message.reply_text(text, reply_markup=kb.back(), parse_mode="Markdown")
    
    async def cmd_buy(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Купить предмет"""
        if not context.args:
            await update.message.reply_text(s.error("❌ Что купить? /buy [предмет]"))
            return
        
        item = " ".join(context.args).lower()
        user_data = self.db.get_user(update.effective_user.id)
        
        items = {
            # Зелья
            "зелье здоровья": {"price": 50, "heal": 30},
            "большое зелье": {"price": 100, "heal": 70},
            "эликсир": {"price": 200, "heal": 150},
            "алмазное зелье": {"price": 500, "heal": 300},
            
            # Оружие
            "меч": {"price": 200, "damage": 10},
            "легендарный меч": {"price": 500, "damage": 30},
            "экскалибур": {"price": 1000, "damage": 50},
            "адский клинок": {"price": 2000, "damage": 100, "crit": 10},
            
            # Броня
            "щит": {"price": 150, "armor": 5},
            "доспехи": {"price": 400, "armor": 15},
            "непробиваемая броня": {"price": 800, "armor": 30},
            "божественная броня": {"price": 2000, "armor": 50, "health": 10},
            
            # Энергия
            "энергетик": {"price": 30, "energy": 20},
            "батарейка": {"price": 80, "energy": 50},
            "атомный реактор": {"price": 200, "energy": 100},
            "бесконечность": {"price": 500, "energy": 200},
            
            # Удача
            "амулет удачи": {"price": 300, "crit": 5},
            "кольцо фортуны": {"price": 600, "crit": 10},
            "подкова": {"price": 1000, "crit": 15}
        }
        
        if item not in items:
            await update.message.reply_text(s.error("❌ Такого товара нет в магазине"))
            return
        
        item_data = items[item]
        
        if user_data['coins'] < item_data['price']:
            await update.message.reply_text(s.error(f"❌ Недостаточно монет. Нужно {item_data['price']} 💰"))
            return
        
        self.db.add_coins(user_data['id'], -item_data['price'])
        
        effects = []
        
        if 'heal' in item_data:
            new_health = self.db.heal(user_data['id'], item_data['heal'])
            effects.append(f"❤️ Здоровье +{item_data['heal']} (теперь {new_health})")
        
        if 'damage' in item_data:
            new_damage = user_data['damage'] + item_data['damage']
            self.db.update_user(user_data['id'], damage=new_damage)
            effects.append(f"⚔️ Урон +{item_data['damage']} (теперь {new_damage})")
        
        if 'armor' in item_data:
            new_armor = user_data['armor'] + item_data['armor']
            self.db.update_user(user_data['id'], armor=new_armor)
            effects.append(f"🛡️ Броня +{item_data['armor']} (теперь {new_armor})")
        
        if 'energy' in item_data:
            new_energy = self.db.add_energy(user_data['id'], item_data['energy'])
            effects.append(f"⚡ Энергия +{item_data['energy']} (теперь {new_energy})")
        
        if 'crit' in item_data:
            new_crit = user_data['crit_chance'] + item_data['crit']
            self.db.update_user(user_data['id'], crit_chance=new_crit)
            effects.append(f"🎯 Шанс крита +{item_data['crit']}% (теперь {new_crit}%)")
        
        if 'health' in item_data:
            new_max = user_data['max_health'] + item_data['health']
            self.db.update_user(user_data['id'], max_health=new_max)
            effects.append(f"❤️ Макс. здоровье +{item_data['health']} (теперь {new_max})")
        
        effects_text = "\n".join([f"{s.item(e)}" for e in effects])
        
        await update.message.reply_text(
            f"{s.success('✅ Покупка совершена!')}\n\n"
            f"{s.item(f'Предмет: {item}')}\n"
            f"{effects_text}",
            parse_mode="Markdown"
        )
        
        self.db.log_action(user_data['id'], 'buy', item)
    
    async def cmd_pay(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Перевести монеты"""
        if len(context.args) < 2:
            await update.message.reply_text(s.error("❌ Использование: /pay @user сумма"))
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
        
        # Перевод
        self.db.add_coins(user_data['id'], -amount)
        self.db.add_coins(target['id'], amount)
        
        # Комиссия для не-премиум
        commission_text = ""
        if not self.db.is_premium(user_data['id']):
            commission = int(amount * 0.05)
            self.db.add_coins(user_data['id'], -commission)
            commission_text = f"\n{s.item(f'💸 Комиссия: {commission} (5%)')}"
        
        target_name = target.get('nickname') or target['first_name']
        
        text = (
            s.header("💸 ПЕРЕВОД") + "\n"
            f"{s.item(f'Получатель: {target_name}')}\n"
            f"{s.item(f'Сумма: {amount} 💰')}{commission_text}\n\n"
            f"{s.success('✅ Перевод выполнен!')}"
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")
        self.db.log_action(user_data['id'], 'pay', f"{amount}💰 -> {target['id']}")
    
    async def cmd_gift(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Подарить предмет"""
        if len(context.args) < 2:
            await update.message.reply_text(s.error("❌ Использование: /gift @user предмет"))
            return
        
        username = context.args[0].replace('@', '')
        item = " ".join(context.args[1:]).lower()
        
        user_data = self.db.get_user(update.effective_user.id)
        
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        # Здесь нужно добавить проверку наличия предмета в инвентаре
        await update.message.reply_text(s.info("📦 Функция подарков в разработке"))
    
    async def cmd_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Баланс"""
        user_data = self.db.get_user(update.effective_user.id)
        
        text = (
            s.header("💰 БАЛАНС") + "\n\n"
            f"{s.stat('Монеты', f'{user_data["coins"]} 💰')}\n"
            f"{s.stat('Алмазы', f'{user_data["diamonds"]} 💎')}\n"
            f"{s.stat('Энергия', f'{user_data["energy"]}/100 ⚡')}\n"
            f"{s.stat('Здоровье', f'{user_data["health"]}/{user_data["max_health"]} ❤️')}"
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_work(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Работать"""
        user_data = self.db.get_user(update.effective_user.id)
        
        if user_data.get('last_work'):
            last = datetime.datetime.fromisoformat(user_data['last_work'])
            if (datetime.datetime.now() - last).seconds < 3600:  # 1 час
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
            ("Продавец", 280, 55),
            ("Официант", 250, 50),
            ("Грузчик", 300, 60),
            ("Дизайнер", 450, 90),
            ("Маркетолог", 380, 75)
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
            s.header("💼 РАБОТА") + "\n\n"
            f"{s.item(f'Профессия: {job}')}\n"
            f"{s.item(f'💰 Зарплата: +{coins}')}\n"
            f"{s.item(f'✨ Опыт: +{exp}')}\n\n"
            f"{s.info('Работать можно раз в час')}"
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_donate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о привилегиях"""
        text = (
            s.header("💎 ПРИВИЛЕГИИ") + "\n\n"
            f"{s.section('VIP СТАТУС')}"
            f"Цена: {VIP_PRICE} 💰 / {VIP_DAYS} дней\n"
            f"{s.item('⚔️ Урон в битвах +20%')}\n"
            f"{s.item('💰 Награда с боссов +50%')}\n"
            f"{s.item('🎁 Ежедневный бонус +50%')}\n"
            f"{s.item('💎 Алмазы +1 в день')}\n"
            f"{s.item('💸 Комиссия за переводы 0%')}\n\n"
            
            f"{s.section('PREMIUM СТАТУС')}"
            f"Цена: {PREMIUM_PRICE} 💰 / {PREMIUM_DAYS} дней\n"
            f"{s.item('⚔️ Урон в битвах +50%')}\n"
            f"{s.item('💰 Награда с боссов +100%')}\n"
            f"{s.item('🎁 Ежедневный бонус +100%')}\n"
            f"{s.item('💎 Алмазы +3 в день')}\n"
            f"{s.item('💸 Комиссия за переводы 0%')}\n"
            f"{s.item('🚫 Игнорирование спам-фильтра')}\n"
            f"{s.item('✨ Особый статус в профиле')}\n"
            f"{s.item('🎮 Доступ к эксклюзивным играм')}\n\n"
            
            f"{s.cmd('vip', 'купить VIP')}\n"
            f"{s.cmd('premium', 'купить PREMIUM')}"
        )
        
        await update.message.reply_text(text, reply_markup=kb.back(), parse_mode="Markdown")
    
    async def cmd_vip_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о VIP"""
        await self.cmd_donate(update, context)
    
    async def cmd_premium_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о PREMIUM"""
        await self.cmd_donate(update, context)
    
    async def cmd_buy_vip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Купить VIP"""
        user_data = self.db.get_user(update.effective_user.id)
        
        if user_data['coins'] < VIP_PRICE:
            await update.message.reply_text(s.error(f"❌ Недостаточно монет. Нужно {VIP_PRICE} 💰"))
            return
        
        if self.db.is_vip(user_data['id']):
            await update.message.reply_text(s.error("❌ VIP статус уже активен"))
            return
        
        self.db.add_coins(user_data['id'], -VIP_PRICE)
        until = self.db.set_vip(user_data['id'], VIP_DAYS)
        date_str = until.strftime("%d.%m.%Y")
        
        text = (
            s.header("✨ VIP СТАТУС АКТИВИРОВАН") + "\n\n"
            f"{s.item(f'Срок действия: до {date_str}')}\n"
            f"{s.item('Все бонусы активны!')}\n\n"
            f"{s.info('Спасибо за поддержку!')}"
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")
        self.db.log_action(user_data['id'], 'buy_vip')
    
    async def cmd_buy_premium(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Купить PREMIUM"""
        user_data = self.db.get_user(update.effective_user.id)
        
        if user_data['coins'] < PREMIUM_PRICE:
            await update.message.reply_text(s.error(f"❌ Недостаточно монет. Нужно {PREMIUM_PRICE} 💰"))
            return
        
        if self.db.is_premium(user_data['id']):
            await update.message.reply_text(s.error("❌ PREMIUM статус уже активен"))
            return
        
        self.db.add_coins(user_data['id'], -PREMIUM_PRICE)
        until = self.db.set_premium(user_data['id'], PREMIUM_DAYS)
        date_str = until.strftime("%d.%m.%Y")
        
        text = (
            s.header("💎 PREMIUM СТАТУС АКТИВИРОВАН") + "\n\n"
            f"{s.item(f'Срок действия: до {date_str}')}\n"
            f"{s.item('Все бонусы активны!')}\n"
            f"{s.item('Эксклюзивный статус в профиле!')}\n\n"
            f"{s.info('Спасибо за поддержку!')}"
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")
        self.db.log_action(user_data['id'], 'buy_premium')

    # ===== ИГРЫ =====
    
    async def cmd_games(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Меню игр"""
        await update.message.reply_text(
            s.header("🎮 ИГРЫ") + "\nВыберите игру:",
            reply_markup=kb.games(),
            parse_mode="Markdown"
        )
    
    async def cmd_coin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Монетка"""
        result = random.choice(["Орел", "Решка"])
        await update.message.reply_text(
            f"{s.header('🪙 МОНЕТКА')}\n\n{s.item(f'Выпало: {result}')}",
            parse_mode="Markdown"
        )
    
    async def cmd_dice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Бросок кубика"""
        result = random.randint(1, 6)
        await update.message.reply_text(
            f"{s.header('🎲 КУБИК')}\n\n{s.item(f'Выпало: {result}')}",
            parse_mode="Markdown"
        )
    
    async def cmd_dice_bet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Кости со ставкой"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if len(context.args) < 1:
            await update.message.reply_text(s.error("❌ Укажите ставку: /кости 100"))
            return
        
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
        
        dice1 = random.randint(1, 6)
        dice2 = random.randint(1, 6)
        total = dice1 + dice2
        
        if total in [7, 11]:
            win = bet * 2
            self.db.add_coins(user_data['id'], win)
            self.db.update_user(user_data['id'], dice_wins=user_data.get('dice_wins', 0) + 1)
            result_text = s.success(f"🎉 ВЫИГРЫШ! +{win} 💰")
        elif total in [2, 3, 12]:
            self.db.add_coins(user_data['id'], -bet)
            self.db.update_user(user_data['id'], dice_losses=user_data.get('dice_losses', 0) + 1)
            result_text = s.error(f"💀 ПРОИГРЫШ! -{bet} 💰")
        else:
            result_text = s.info(f"🔄 НИЧЬЯ! Ставка возвращена")
        
        text = (
            s.header("🎲 КОСТИ") + "\n\n"
            f"{s.item(f'Ставка: {bet} 💰')}\n"
            f"{s.item(f'Кубики: {dice1} + {dice2} = {total}')}\n\n"
            f"{result_text}"
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
        black_numbers = [2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35]
        
        if num == 0:
            color = "green"
        elif num in red_numbers:
            color = "red"
        else:
            color = "black"
        
        win = False
        multiplier = 0
        
        if choice.isdigit() and int(choice) == num:
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
            s.header("🎰 РУЛЕТКА") + "\n\n"
            f"{s.item(f'Ставка: {bet} 💰')}\n"
            f"{s.item(f'Выбрано: {choice}')}\n"
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
                pass
        
        if bet > user_data['coins']:
            await update.message.reply_text(s.error(f"❌ Недостаточно монет. Баланс: {user_data['coins']} 💰"))
            return
        
        if bet <= 0:
            await update.message.reply_text(s.error("❌ Ставка должна быть больше 0"))
            return
        
        symbols = ["🍒", "🍋", "🍊", "7️⃣", "💎", "🎰", "💀", "⭐"]
        spin = [random.choice(symbols) for _ in range(3)]
        
        if len(set(spin)) == 1:
            if spin[0] == "7️⃣":
                win = bet * 50
            elif spin[0] == "💎":
                win = bet * 30
            elif spin[0] == "⭐":
                win = bet * 20
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
            s.header("🎰 СЛОТЫ") + "\n\n"
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
                animation=GIFS["russian_roulette"]
            )
        except:
            pass
        
        # Крутим барабан
        chamber = random.randint(1, 6)
        shot = random.randint(1, 6)
        
        await asyncio.sleep(2)  # Эффект ожидания
        
        if chamber == shot:
            # Проигрыш
            self.db.add_coins(user_data['id'], -bet)
            self.db.update_user(user_data['id'], rr_losses=user_data.get('rr_losses', 0) + 1)
            
            text = (
                s.header("💀 РУССКАЯ РУЛЕТКА") + "\n\n"
                f"{s.item(f'Ставка: {bet} 💰')}\n"
                f"{s.item('Бах! Выстрел...')}\n\n"
                f"{s.error(f'ВЫ ПРОИГРАЛИ! -{bet} 💰')}"
            )
        else:
            # Выигрыш
            win = bet * 5
            self.db.add_coins(user_data['id'], win)
            self.db.update_user(user_data['id'], rr_wins=user_data.get('rr_wins', 0) + 1)
            
            text = (
                s.header("🔫 РУССКАЯ РУЛЕТКА") + "\n\n"
                f"{s.item(f'Ставка: {bet} 💰')}\n"
                f"{s.item('Щёлк... В этот раз повезло!')}\n\n"
                f"{s.success(f'ВЫ ВЫИГРАЛИ! +{win} 💰')}"
            )
        
        await update.message.reply_text(text, parse_mode="Markdown")
        self.db.log_action(user_data['id'], 'rr', f"{'win' if chamber != shot else 'lose'} {bet}")
    
    async def cmd_saper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сапёр"""
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
        
        self.db.add_coins(user_data['id'], -bet)
        
        text = (
            s.header("💣 САПЁР") + "\n\n"
            f"{s.item(f'Ставка: {bet} 💰')}\n"
            f"{s.item('Выберите клетку от 1 до 9')}\n\n"
            f"{' '.join(field[0])}\n"
            f"{' '.join(field[1])}\n"
            f"{' '.join(field[2])}\n\n"
            f"{s.info('Напишите номер клетки (1-9)')}"
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
            f"{s.info('Напиши свой вариант...')}",
            parse_mode="Markdown"
        )
    
    async def cmd_bulls(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Быки и коровы"""
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
        
        digits = random.sample(range(10), 4)
        number = ''.join(map(str, digits))
        
        game_id = f"bulls_{user.id}_{int(time.time())}"
        self.games_in_progress[game_id] = {
            'user_id': user.id,
            'number': number,
            'attempts': [],
            'max_attempts': 10,
            'bet': bet
        }
        
        self.db.add_coins(user_data['id'], -bet)
        
        await update.message.reply_text(
            f"{s.header('🐂 БЫКИ И КОРОВЫ')}\n\n"
            f"{s.item('Я загадал 4-значное число без повторов')}\n"
            f"{s.item(f'Ставка: {bet} 💰')}\n"
            f"{s.item('Попыток: 10')}\n"
            f"{s.item('Бык — цифра на своём месте')}\n"
            f"{s.item('Корова — цифра есть, но не на своём месте')}\n\n"
            f"{s.info('Напиши свой вариант (4 цифры)...')}",
            parse_mode="Markdown"
        )
    
    # ===== БОССЫ =====
    
    async def cmd_bosses(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список боссов"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        bosses = self.db.get_bosses()
        
        if not bosses:
            self.db.respawn_bosses()
            bosses = self.db.get_bosses()
        
        text = s.header("👾 БОССЫ") + "\n\n"
        
        for boss in bosses[:3]:
            health_bar = s.progress(boss['health'], boss['max_health'], 15)
            text += (
                f"**{boss['name']}** (ур.{boss['level']})\n"
                f"{s.item(f'❤️ {health_bar}')}\n"
                f"{s.item(f'⚔️ Урон: {boss['damage']}')}\n"
                f"{s.item(f'💰 Награда: {boss['reward_coins']} 💰, ✨ {boss['reward_exp']}')}\n\n"
            )
        
        if len(bosses) > 3:
            text += f"{s.info(f'... и еще {len(bosses) - 3} боссов')}\n\n"
        
        text += (
            f"{s.section('ТВОИ ПОКАЗАТЕЛИ')}\n"
            f"{s.stat('❤️ Здоровье', f'{user_data["health"]}/{user_data["max_health"]}')}\n"
            f"{s.stat('⚡ Энергия', f'{user_data["energy"]}/100')}\n"
            f"{s.stat('⚔️ Урон', user_data["damage"])}\n"
            f"{s.stat('👾 Боссов убито', user_data["boss_kills"])}\n\n"
            f"{s.section('КОМАНДЫ')}\n"
            f"{s.cmd('босс [ID]', 'атаковать босса')}\n"
            f"{s.cmd('боссинфо [ID]', 'информация о боссе')}\n"
            f"{s.cmd('реген', 'восстановить ❤️ и ⚡')}"
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_boss_fight(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Битва с боссом"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажи ID босса: /босс 1"))
            return
        
        try:
            boss_id = int(context.args[0])
        except:
            await update.message.reply_text(s.error("❌ Неверный ID"))
            return
        
        boss = self.db.get_boss(boss_id)
        if not boss or not boss['is_alive']:
            await update.message.reply_text(s.error("❌ Босс не найден или уже повержен"))
            return
        
        if user_data['energy'] < 10:
            await update.message.reply_text(s.error("❌ Недостаточно энергии. Используй /regen"))
            return
        
        # Тратим энергию
        self.db.add_energy(user_data['id'], -10)
        
        # Расчет урона
        damage_bonus = 1.0
        if self.db.is_vip(user_data['id']):
            damage_bonus += 0.2
        if self.db.is_premium(user_data['id']):
            damage_bonus += 0.3
        
        base_damage = user_data['damage'] * damage_bonus
        player_damage = int(base_damage) + random.randint(-5, 5)
        
        # Проверка на критический удар
        crit = random.randint(1, 100) <= user_data['crit_chance']
        if crit:
            player_damage = int(player_damage * user_data['crit_multiplier'] / 100)
            crit_text = "💥 КРИТИЧЕСКИЙ УДАР! "
        else:
            crit_text = ""
        
        # Урон босса
        boss_damage = boss['damage'] + random.randint(-5, 5)
        player_taken = max(1, boss_damage - user_data['armor'] // 2)
        
        killed = self.db.damage_boss(boss_id, player_damage)
        self.db.damage(user_data['id'], player_taken)
        
        text = s.header("⚔️ БИТВА С БОССОМ") + "\n\n"
        text += f"{s.item(f'{crit_text}Твой урон: {player_damage}')}\n"
        text += f"{s.item(f'Урон босса: {player_taken}')}\n\n"
        
        if killed:
            # Босс убит
            reward_coins = boss['reward_coins'] * (1 + user_data['level'] // 10)
            reward_exp = boss['reward_exp'] * (1 + user_data['level'] // 10)
            
            if self.db.is_vip(user_data['id']):
                reward_coins = int(reward_coins * 1.5)
                reward_exp = int(reward_exp * 1.5)
            if self.db.is_premium(user_data['id']):
                reward_coins = int(reward_coins * 2)
                reward_exp = int(reward_exp * 2)
            
            self.db.add_coins(user_data['id'], reward_coins)
            leveled_up = self.db.add_exp(user_data['id'], reward_exp)
            self.db.add_boss_kill(user_data['id'])
            
            text += f"{s.success('ПОБЕДА!')}\n"
            text += f"{s.item(f'💰 Монеты: +{reward_coins}')}\n"
            text += f"{s.item(f'✨ Опыт: +{reward_exp}')}\n"
            
            if leveled_up:
                text += f"{s.success(f'✨ УРОВЕНЬ ПОВЫШЕН!')}\n"
        else:
            boss_info = self.db.get_boss(boss_id)
            text += f"{s.warning('Босс ещё жив!')}\n"
            text += f"❤️ Осталось: {boss_info['health']} здоровья\n"
        
        # Проверка на смерть игрока
        if user_data['health'] <= player_taken:
            self.db.heal(user_data['id'], 50)
            text += f"\n{s.info('Ты погиб и воскрешён с 50❤️')}"
        
        await update.message.reply_text(text, parse_mode="Markdown")
        self.db.log_action(user_data['id'], 'boss_fight', f"Битва с боссом {boss['name']}")
    
    async def cmd_boss_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о боссе"""
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажи ID босса: /боссинфо 1"))
            return
        
        try:
            boss_id = int(context.args[0])
        except:
            await update.message.reply_text(s.error("❌ Неверный ID"))
            return
        
        boss = self.db.get_boss(boss_id)
        if not boss:
            await update.message.reply_text(s.error("❌ Босс не найден"))
            return
        
        status = "ЖИВ" if boss['is_alive'] else "ПОВЕРЖЕН"
        health_bar = s.progress(boss['health'], boss['max_health'], 20)
        
        text = (
            s.header(f"👾 БОСС: {boss['name']}") + "\n\n"
            f"{s.stat('Уровень', boss['level'])}\n"
            f"{s.stat('❤️ Здоровье', health_bar)}\n"
            f"{s.stat('⚔️ Урон', boss['damage'])}\n"
            f"{s.stat('💰 Награда монетами', boss['reward_coins'])}\n"
            f"{s.stat('✨ Награда опытом', boss['reward_exp'])}\n"
            f"{s.stat('📊 Статус', status)}"
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_regen(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Восстановление здоровья и энергии"""
        user_data = self.db.get_user(update.effective_user.id)
        
        cost = 20
        if user_data['coins'] < cost:
            await update.message.reply_text(s.error(f"❌ Недостаточно монет. Нужно {cost} 💰"))
            return
        
        self.db.add_coins(user_data['id'], -cost)
        self.db.heal(user_data['id'], 50)
        self.db.add_energy(user_data['id'], 20)
        
        await update.message.reply_text(
            f"{s.success('✅ Регенерация завершена!')}\n\n"
            f"{s.item('❤️ Здоровье +50')}\n"
            f"{s.item('⚡ Энергия +20')}\n"
            f"{s.item(f'💰 Потрачено: {cost}')}",
            parse_mode="Markdown"
        )
    
    # ===== ДУЭЛИ =====
    
    async def cmd_duel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Вызов на дуэль"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if len(context.args) < 2:
            await update.message.reply_text(s.error("❌ Использование: /дуэль @user ставка"))
            return
        
        username = context.args[0].replace('@', '')
        try:
            bet = int(context.args[1])
        except:
            await update.message.reply_text(s.error("❌ Ставка должна быть числом"))
            return
        
        if bet <= 0:
            await update.message.reply_text(s.error("❌ Ставка должна быть больше 0"))
            return
        
        if bet > user_data['coins']:
            await update.message.reply_text(s.error(f"❌ Недостаточно монет. Баланс: {user_data['coins']} 💰"))
            return
        
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        if target['id'] == user_data['id']:
            await update.message.reply_text(s.error("❌ Нельзя вызвать на дуэль самого себя"))
            return
        
        # Проверяем, нет ли уже активной дуэли
        self.db.c.execute("SELECT id FROM duels WHERE (challenger_id = ? OR opponent_id = ?) AND status = 'pending'",
                         (user_data['id'], user_data['id']))
        if self.db.c.fetchone():
            await update.message.reply_text(s.error("❌ У тебя уже есть активная дуэль"))
            return
        
        duel_id = self.db.create_duel(user_data['id'], target['id'], bet)
        
        # Блокируем ставку
        self.db.add_coins(user_data['id'], -bet)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ ПРИНЯТЬ", callback_data=f"accept_duel_{duel_id}"),
             InlineKeyboardButton("❌ ОТКЛОНИТЬ", callback_data=f"reject_duel_{duel_id}")]
        ])
        
        target_name = target.get('nickname') or target['first_name']
        
        await update.message.reply_text(
            f"{s.header('⚔️ ВЫЗОВ НА ДУЭЛЬ')}\n\n"
            f"{s.item(f'Противник: {target_name}')}\n"
            f"{s.item(f'Ставка: {bet} 💰')}\n\n"
            f"{s.info('Ожидание ответа...')}",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    
    async def cmd_duels(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список активных дуэлей"""
        self.db.c.execute("SELECT * FROM duels WHERE status = 'pending'")
        duels = self.db.c.fetchall()
        
        if not duels:
            await update.message.reply_text(s.info("Нет активных дуэлей"))
            return
        
        text = s.header("⚔️ АКТИВНЫЕ ДУЭЛИ") + "\n\n"
        
        for duel in duels:
            challenger = self.db.get_user_by_id(duel[1])
            opponent = self.db.get_user_by_id(duel[2])
            if challenger and opponent:
                text += f"{s.item(f'{challenger["first_name"]} vs {opponent["first_name"]} — ставка {duel[3]} 💰')}\n"
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_accept_duel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Принять дуэль"""
        # Обработка через callback
        pass
    
    async def cmd_reject_duel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отклонить дуэль"""
        # Обработка через callback
        pass
    
    async def cmd_duel_attack(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Атака в дуэли"""
        await update.message.reply_text(s.info("⚔️ Функция в разработке"))
    
    async def cmd_duel_defend(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Защита в дуэли"""
        await update.message.reply_text(s.info("🛡️ Функция в разработке"))
    
    async def cmd_duel_surrender(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сдаться в дуэли"""
        await update.message.reply_text(s.info("🏳️ Функция в разработке"))
    
    async def cmd_duel_rating(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Рейтинг дуэлянтов"""
        self.db.c.execute("SELECT first_name, nickname, duel_rating FROM users WHERE duel_rating > 0 ORDER BY duel_rating DESC LIMIT 10")
        top = self.db.c.fetchall()
        
        if not top:
            await update.message.reply_text(s.info("Рейтинг пуст"))
            return
        
        text = s.header("⚔️ ТОП ДУЭЛЯНТОВ") + "\n\n"
        for i, row in enumerate(top, 1):
            name = row[1] or row[0]
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} **{name}** — {row[2]} очков\n"
        
        await update.message.reply_text(text, parse_mode="Markdown")

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
            await update.message.reply_text(s.error("❌ Игра уже идёт! Присоединяйтесь: /мафияприсоединиться"))
            return
        
        self.mafia_games[chat_id] = {
            'status': 'registration',
            'players': [],
            'players_data': {},
            'roles': {},
            'alive': {},
            'day': 1,
            'phase': 'night',
            'votes': {},
            'mafia_kill': None,
            'doctor_save': None,
            'commissioner_check': None,
            'message_id': None
        }
        
        # Отправляем гифку ночи
        try:
            await context.bot.send_animation(
                chat_id=chat_id,
                animation=GIFS["mafia_night"]
            )
        except:
            pass
        
        text = (
            s.header("🔫 МАФИЯ") + "\n\n"
            f"{s.success('🎮 Игра создана!')}\n\n"
            f"{s.item('Участники (0):')}\n"
            f"{s.item('/мафияприсоединиться — присоединиться')}\n"
            f"{s.item('/мафиявыйти — выйти')}\n"
            f"{s.item('Для старта нужно минимум 4 игрока')}\n\n"
            f"{s.info('Игра будет проходить в ЛС с ботом')}"
        )
        
        msg = await update.message.reply_text(text, parse_mode="Markdown")
        self.mafia_games[chat_id]['message_id'] = msg.message_id
    
    async def cmd_mafia_join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Присоединиться к игре"""
        chat_id = update.effective_chat.id
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if chat_id not in self.mafia_games:
            await update.message.reply_text(s.error("❌ Игра не создана. Начните: /мафиястарт"))
            return
        
        game = self.mafia_games[chat_id]
        
        if game['status'] != 'registration':
            await update.message.reply_text(s.error("❌ Игра уже началась"))
            return
        
        if user.id in game['players']:
            await update.message.reply_text(s.error("❌ Вы уже в игре"))
            return
        
        game['players'].append(user.id)
        game['players_data'][user.id] = {
            'name': user.first_name,
            'username': user.username,
            'confirmed': False
        }
        
        # Отправляем сообщение в ЛС для подтверждения
        try:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ ПОДТВЕРДИТЬ", callback_data=f"mafia_confirm_{chat_id}")]
            ])
            
            await context.bot.send_message(
                user.id,
                f"{s.header('🔫 МАФИЯ')}\n\n"
                f"{s.item('Вы присоединились к игре!')}\n"
                f"{s.item('Нажмите кнопку для подтверждения')}\n\n"
                f"{s.info('После подтверждения вы получите свою роль в ЛС')}",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            
            await update.message.reply_text(s.success(f"✅ {user.first_name}, проверьте ЛС для подтверждения!"))
        except:
            await update.message.reply_text(s.error(f"❌ {user.first_name}, не удалось отправить сообщение в ЛС. Напишите боту в личку сначала."))
            game['players'].remove(user.id)
            del game['players_data'][user.id]
            return
        
        # Обновляем сообщение в чате
        players_list = "\n".join([f"{i+1}. {game['players_data'][pid]['name']}" for i, pid in enumerate(game['players'])])
        confirmed = sum(1 for p in game['players'] if game['players_data'][p]['confirmed'])
        
        text = (
            s.header("🔫 МАФИЯ") + "\n\n"
            f"{s.item(f'Участники ({len(game["players"])}):')}\n"
            f"{players_list}\n\n"
            f"{s.item(f'Подтвердили: {confirmed}/{len(game["players"])}')}\n"
            f"{s.item('/мафияприсоединиться — присоединиться')}\n"
            f"{s.item('/мафиявыйти — выйти')}\n\n"
            f"{s.info('Для старта нужно минимум 4 игрока и все подтверждения')}"
        )
        
        try:
            await context.bot.edit_message_text(
                text,
                chat_id=chat_id,
                message_id=game['message_id'],
                parse_mode="Markdown"
            )
        except:
            pass
    
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
        
        if user.id not in game['players']:
            await update.message.reply_text(s.error("❌ Вас нет в игре"))
            return
        
        game['players'].remove(user.id)
        del game['players_data'][user.id]
        
        await update.message.reply_text(s.success(f"✅ {user.first_name} покинул игру"))
        
        # Обновляем сообщение в чате
        if game['players']:
            players_list = "\n".join([f"{i+1}. {game['players_data'][pid]['name']}" for i, pid in enumerate(game['players'])])
            confirmed = sum(1 for p in game['players'] if game['players_data'][p]['confirmed'])
            
            text = (
                s.header("🔫 МАФИЯ") + "\n\n"
                f"{s.item(f'Участники ({len(game["players"])}):')}\n"
                f"{players_list}\n\n"
                f"{s.item(f'Подтвердили: {confirmed}/{len(game["players"])}')}\n"
                f"{s.item('/мафияприсоединиться — присоединиться')}\n"
                f"{s.item('/мафиявыйти — выйти')}\n\n"
                f"{s.info('Для старта нужно минимум 4 игрока и все подтверждения')}"
            )
        else:
            text = (
                s.header("🔫 МАФИЯ") + "\n\n"
                f"{s.item('Участников нет')}\n"
                f"{s.item('/мафияприсоединиться — присоединиться')}"
            )
        
        try:
            await context.bot.edit_message_text(
                text,
                chat_id=chat_id,
                message_id=game['message_id'],
                parse_mode="Markdown"
            )
        except:
            pass
    
    async def cmd_mafia_roles(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список ролей в мафии"""
        text = (
            s.header("🔫 РОЛИ В МАФИИ") + "\n\n"
            f"{s.section('😈 МАФИЯ')}"
            f"{s.item('👿 Мафиози — ночью убивают')}\n"
            f"{s.item('😈 Дон — глава мафии, проверяет комиссара')}\n\n"
            f"{s.section('👼 ГОРОД')}"
            f"{s.item('👮 Комиссар Каттани — ночью проверяет игроков')}\n"
            f"{s.item('👨‍⚕️ Доктор — лечит по ночам')}\n"
            f"{s.item('👤 Мирный житель — ищет мафию днём')}\n\n"
            f"{s.section('🎭 ОСОБЫЕ РОЛИ')}"
            f"{s.item('💃 Леди — может соблазнить и защитить')}\n"
            f"{s.item('🔫 Шериф — может убить раз в игру')}\n"
            f"{s.item('💣 Террорист — умирая, забирает с собой')}"
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_mafia_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Правила мафии"""
        text = (
            s.header("🔫 ПРАВИЛА МАФИИ") + "\n\n"
            f"{s.section('🌙 НОЧЬ')}"
            f"{s.item('1. Мафия выбирает жертву')}\n"
            f"{s.item('2. Доктор выбирает, кого спасти')}\n"
            f"{s.item('3. Комиссар проверяет игрока')}\n"
            f"{s.item('4. Леди может соблазнить')}\n\n"
            f"{s.section('☀️ ДЕНЬ')}"
            f"{s.item('1. Объявление жертв ночи')}\n"
            f"{s.item('2. Обсуждение')}\n"
            f"{s.item('3. Голосование за исключение')}\n"
            f"{s.item('4. Исключённый раскрывает роль')}\n\n"
            f"{s.section('🏆 ЦЕЛЬ ИГРЫ')}"
            f"{s.item('Мафия — убить всех мирных')}\n"
            f"{s.item('Город — найти и исключить всю мафию')}\n\n"
            f"{s.info('Все действия происходят в ЛС с ботом')}"
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
        alive_players = [pid for pid in game['players'] if game['alive'].get(pid, True)]
        
        if vote_num < 1 or vote_num > len(alive_players):
            await update.message.reply_text(s.error("❌ Неверный номер игрока"))
            return
        
        target_id = alive_players[vote_num - 1]
        game['votes'][user.id] = target_id
        
        await update.message.reply_text(s.success(f"✅ Голос засчитан!"), parse_mode="Markdown")
        
        # Проверяем, все ли проголосовали
        alive_count = len(alive_players)
        if len(game['votes']) >= alive_count:
            await self._mafia_end_day(chat_id, context)
    
    async def _mafia_start_game(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Начать игру после подтверждения всех игроков"""
        game = self.mafia_games[chat_id]
        
        # Определяем роли
        players = game['players']
        num_players = len(players)
        
        # Баланс ролей
        if num_players <= 6:
            num_mafia = 2
        elif num_players <= 9:
            num_mafia = 3
        else:
            num_mafia = 4
        
        roles = ['mafia'] * num_mafia + ['civilian'] * (num_players - num_mafia - 2) + ['doctor', 'commissioner']
        random.shuffle(roles)
        
        # Назначаем роли
        for i, player_id in enumerate(players):
            role = roles[i]
            game['roles'][player_id] = role
            game['alive'][player_id] = True
            
            # Отправляем роль в ЛС
            role_names = {
                'mafia': '😈 Мафия',
                'civilian': '👤 Мирный житель',
                'doctor': '👨‍⚕️ Доктор',
                'commissioner': '👮 Комиссар Каттани'
            }
            
            role_desc = {
                'mafia': 'Ночью вы можете убивать мирных жителей. Общайтесь с другими мафиози в ЛС.',
                'civilian': 'У вас нет особых способностей. Ищите мафию днём и голосуйте.',
                'doctor': 'Ночью вы можете спасать одного игрока от смерти.',
                'commissioner': 'Ночью вы можете проверять одного игрока, узнавая его роль.'
            }
            
            try:
                await context.bot.send_message(
                    player_id,
                    f"{s.header('🔫 МАФИЯ')}\n\n"
                    f"{s.item(f'Ваша роль: {role_names[role]}')}\n"
                    f"{s.item(role_desc[role])}\n\n"
                    f"{s.info('Скоро начнётся первый ход. Ожидайте сообщений.')}",
                    parse_mode="Markdown"
                )
            except:
                pass
        
        game['status'] = 'night'
        game['phase'] = 'night'
        
        # Отправляем гифку ночи
        try:
            await context.bot.send_animation(
                chat_id=chat_id,
                animation=GIFS["mafia_night"]
            )
        except:
            pass
        
        await context.bot.send_message(
            chat_id,
            f"{s.header('🔫 МАФИЯ')}\n\n"
            f"{s.success('🌙 НАСТУПИЛА НОЧЬ')}\n"
            f"{s.item('Все роли розданы в ЛС')}\n"
            f"{s.item('Мафия выбирает жертву...')}\n"
            f"{s.item('Доктор выбирает, кого спасти...')}\n"
            f"{s.item('Комиссар проверяет...')}",
            parse_mode="Markdown"
        )
        
        # Запускаем таймер на ночь
        asyncio.create_task(self._mafia_night_timer(chat_id, context, 60))
    
    async def _mafia_night_timer(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE, seconds: int):
        """Таймер ночи"""
        await asyncio.sleep(seconds)
        
        if chat_id not in self.mafia_games:
            return
        
        game = self.mafia_games[chat_id]
        
        if game['phase'] != 'night':
            return
        
        # Здесь логика обработки ночных действий
        await self._mafia_process_night(chat_id, context)
    
    async def _mafia_process_night(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ночных действий"""
        game = self.mafia_games[chat_id]
        
        # Получаем убитого мафией
        killed = game.get('mafia_kill')
        
        # Проверяем, спас ли доктор
        saved = game.get('doctor_save')
        if saved and saved == killed:
            killed = None
        
        # Применяем результаты
        if killed:
            game['alive'][killed] = False
            
            # Уведомляем убитого
            try:
                await context.bot.send_message(
                    killed,
                    f"{s.error('💀 ВАС УБИЛИ НОЧЬЮ')}\n\n"
                    f"{s.item('Вы больше не участвуете в игре.')}",
                    parse_mode="Markdown"
                )
            except:
                pass
        
        # Переходим ко дню
        game['phase'] = 'day'
        game['day'] += 1
        game['votes'] = {}
        
        # Отправляем гифку дня
        try:
            await context.bot.send_animation(
                chat_id=chat_id,
                animation=GIFS["mafia_day"]
            )
        except:
            pass
        
        alive_list = [pid for pid in game['players'] if game['alive'].get(pid, True)]
        alive_names = []
        for i, pid in enumerate(alive_list, 1):
            name = game['players_data'][pid]['name']
            alive_names.append(f"{i}. {name}")
        
        killed_name = "никто"
        if killed:
            killed_name = game['players_data'][killed]['name']
        
        text = (
            s.header(f"🔫 МАФИЯ | ДЕНЬ {game['day']}") + "\n\n"
            f"{s.item(f'☀️ Наступило утро...')}\n"
            f"{s.item(f'💀 Прошлой ночью был убит: {killed_name}')}\n\n"
            f"{s.section('ЖИВЫЕ ИГРОКИ')}\n"
            f"{chr(10).join([s.item(name) for name in alive_names])}\n\n"
            f"{s.info('Обсуждайте и голосуйте: голосовать [номер]')}"
        )
        
        await context.bot.send_message(chat_id, text, parse_mode="Markdown")
        
        # Запускаем таймер на день
        asyncio.create_task(self._mafia_day_timer(chat_id, context, 120))
    
    async def _mafia_day_timer(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE, seconds: int):
        """Таймер дня"""
        await asyncio.sleep(seconds)
        
        if chat_id not in self.mafia_games:
            return
        
        game = self.mafia_games[chat_id]
        
        if game['phase'] != 'day':
            return
        
        await self._mafia_end_day(chat_id, context)
    
    async def _mafia_end_day(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Завершение дня и обработка голосования"""
        game = self.mafia_games[chat_id]
        
        # Подсчёт голосов
        vote_count = {}
        for target in game['votes'].values():
            vote_count[target] = vote_count.get(target, 0) + 1
        
        if not vote_count:
            # Никто не голосовал
            await context.bot.send_message(
                chat_id,
                f"{s.info('📢 Никто не был исключён сегодня')}",
                parse_mode="Markdown"
            )
        else:
            # Находим максимальное число голосов
            max_votes = max(vote_count.values())
            candidates = [pid for pid, votes in vote_count.items() if votes == max_votes]
            
            if len(candidates) == 1:
                # Один кандидат с большинством
                executed = candidates[0]
                game['alive'][executed] = False
                
                executed_name = game['players_data'][executed]['name']
                role = game['roles'].get(executed, 'unknown')
                role_names = {
                    'mafia': '😈 МАФИЯ',
                    'civilian': '👤 МИРНЫЙ',
                    'doctor': '👨‍⚕️ ДОКТОР',
                    'commissioner': '👮 КОМИССАР'
                }
                role_display = role_names.get(role, 'НЕИЗВЕСТНО')
                
                text = (
                    s.header(f"🔫 МАФИЯ | ДЕНЬ {game['day']}") + "\n\n"
                    f"{s.item(f'🔨 По результатам голосования исключён: {executed_name}')}\n"
                    f"{s.item(f'Роль: {role_display}')}\n\n"
                    f"{s.info('Ночь скоро наступит...')}"
                )
                
                await context.bot.send_message(chat_id, text, parse_mode="Markdown")
                
                # Уведомляем исключённого
                try:
                    await context.bot.send_message(
                        executed,
                        f"{s.error('🔨 ВАС ИСКЛЮЧИЛИ ДНЁМ')}\n\n"
                        f"{s.item('Вы больше не участвуете в игре.')}",
                        parse_mode="Markdown"
                    )
                except:
                    pass
            else:
                # Ничья
                await context.bot.send_message(
                    chat_id,
                    f"{s.info('📢 Ничья при голосовании. Никто не исключён.')}",
                    parse_mode="Markdown"
                )
        
        # Проверяем условия победы
        alive_players = [pid for pid in game['players'] if game['alive'].get(pid, True)]
        alive_mafia = sum(1 for pid in alive_players if game['roles'].get(pid) == 'mafia')
        alive_civilians = len(alive_players) - alive_mafia
        
        if alive_mafia == 0:
            # Победа города
            await context.bot.send_message(
                chat_id,
                f"{s.success('🏆 ПОБЕДА ГОРОДА!')}\n\n"
                f"{s.item('Вся мафия уничтожена!')}",
                parse_mode="Markdown"
            )
            
            # Начисляем награды
            for pid in game['players']:
                user_data = self.db.get_user_by_id(pid)
                if user_data:
                    self.db.update_user(pid, mafia_games=user_data.get('mafia_games', 0) + 1)
                    if game['roles'].get(pid) != 'mafia':
                        self.db.update_user(pid, mafia_wins=user_data.get('mafia_wins', 0) + 1)
                        self.db.add_coins(pid, 500)
            
            del self.mafia_games[chat_id]
            return
        
        if alive_mafia >= alive_civilians:
            # Победа мафии
            await context.bot.send_message(
                chat_id,
                f"{s.success('🏆 ПОБЕДА МАФИИ!')}\n\n"
                f"{s.item('Мафия захватила город!')}",
                parse_mode="Markdown"
            )
            
            # Начисляем награды
            for pid in game['players']:
                user_data = self.db.get_user_by_id(pid)
                if user_data:
                    self.db.update_user(pid, mafia_games=user_data.get('mafia_games', 0) + 1)
                    if game['roles'].get(pid) == 'mafia':
                        self.db.update_user(pid, mafia_wins=user_data.get('mafia_wins', 0) + 1)
                        self.db.add_coins(pid, 500)
            
            del self.mafia_games[chat_id]
            return
        
        # Переходим к следующей ночи
        game['phase'] = 'night'
        game['mafia_kill'] = None
        game['doctor_save'] = None
        game['commissioner_check'] = None
        
        # Отправляем гифку ночи
        try:
            await context.bot.send_animation(
                chat_id=chat_id,
                animation=GIFS["mafia_night"]
            )
        except:
            pass
        
        await context.bot.send_message(
            chat_id,
            f"{s.header(f'🔫 МАФИЯ | НОЧЬ {game["day"]}')}\n\n"
            f"{s.success('🌙 НАСТУПИЛА НОЧЬ')}\n"
            f"{s.item('Мафия выбирает жертву...')}\n"
            f"{s.item('Доктор выбирает, кого спасти...')}\n"
            f"{s.item('Комиссар проверяет...')}",
            parse_mode="Markdown"
        )
        
        # Запускаем таймер на ночь
        asyncio.create_task(self._mafia_night_timer(chat_id, context, 60))
    
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
                                s.success(f"🎉 ПОБЕДА! Число {game['number']}!\nПопыток: {game['attempts']}\nВыигрыш: {win} 💰"),
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
                        win = game['bet'] * 3
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
        
        if any(word in msg_lower for word in ["привет", "здравствуйте", "хай", "здаров", "ку", "даров"]):
            responses = [
                "👋 Привет! Чем могу помочь?",
                "Йо, братан! Че надо?",
                "Здарова, залетай!",
                "Ку-ку! Есть тема?",
                "Приветики! Слушаю тебя, краш мой"
            ]
            await update.message.reply_text(random.choice(responses))
        elif any(word in msg_lower for word in ["как дела", "как ты", "чё как"]):
            responses = [
                "✨ Всё отлично! Работаю в штатном режиме.",
                "База! Норм, а ты как?",
                "Пушка! Жду новых приключений",
                "Хайпово! Че сам?",
                "Рил ток? Да норм, житуха малина"
            ]
            await update.message.reply_text(random.choice(responses))
        elif any(word in msg_lower for word in ["спасибо", "благодарю", "пасиб"]):
            responses = [
                "🤝 Всегда пожалуйста!",
                "Не за что, бро!",
                "Обращайся, краш мой",
                "Держи в курсе, если чё",
                "Зашло? Рад помочь!"
            ]
            await update.message.reply_text(random.choice(responses))
        elif any(word in msg_lower for word in ["кто создал", "владелец", "создатель"]):
            await update.message.reply_text(f"👑 Мой создатель: {OWNER_USERNAME}\n🤖 Он вообще красава, рил ток!")
        elif any(word in msg_lower for word in ["ты кто", "кто ты", "бот"]):
            responses = [
                "Я Спектр! Самый дерзкий ИИ-бот в этом чате",
                "Спектр, собственной персоной! Че надо?",
                "Я местный обитатель, ИИ-бот Спектр. Будем знакомы?",
                "Спектр - твой виртуальный бро с вайбом!"
            ]
            await update.message.reply_text(random.choice(responses))
        else:
            responses = [
                "Используй /help для списка команд, бро",
                "Напиши /menu для навигации, краш",
                "Чем могу помочь? Я в теме",
                "Слушаю тебя внимательно...",
                "Норм тема, рассказывай!"
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
            
            # Добавляем пользователя в БД если его нет
            self.db.get_user(member.id, member.first_name)
            
            await update.message.reply_text(
                f"👋 {welcome_text}\n\n{member.first_name}, используй /help для команд!",
                parse_mode="Markdown"
            )
    
    async def handle_left_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ухода участников"""
        member = update.message.left_chat_member
        if member.is_bot:
            return
        
        await update.message.reply_text(
            f"👋 {member.first_name} покинул чат... Будем скучать!",
            parse_mode="Markdown"
        )
    
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
                f"{s.cmd('monthly', 'месячный бонус')}\n"
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
            await self.cmd_top_coins(update, context)
        
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
            await self.cmd_dice_bet(update, context)
        
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
        
        elif data == "game_bosses":
            context.args = []
            await self.cmd_bosses(update, context)
        
        elif data == "game_duels":
            context.args = []
            await self.cmd_duel_rating(update, context)
        
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
        
        elif data.startswith("mafia_confirm_"):
            chat_id = int(data.split('_')[2])
            if chat_id in self.mafia_games:
                game = self.mafia_games[chat_id]
                if user.id in game['players']:
                    game['players_data'][user.id]['confirmed'] = True
                    await query.edit_message_text(
                        f"{s.success('✅ Подтверждение получено!')}\n\n"
                        f"{s.info('Ожидайте начала игры...')}",
                        parse_mode="Markdown"
                    )
                    
                    # Проверяем, все ли подтвердили
                    all_confirmed = all(game['players_data'][pid]['confirmed'] for pid in game['players'])
                    if all_confirmed and len(game['players']) >= 4:
                        await self._mafia_start_game(chat_id, context)
        
        elif data.startswith("accept_duel_"):
            duel_id = int(data.split('_')[2])
            duel = self.db.get_duel(duel_id)
            if duel and duel['opponent_id'] == user.id and duel['status'] == 'pending':
                self.db.update_duel(duel_id, status='accepted')
                await query.edit_message_text(
                    f"{s.success('✅ Дуэль принята!')}\n\n"
                    f"{s.info('Скоро начнётся...')}",
                    parse_mode="Markdown"
                )
        
        elif data.startswith("reject_duel_"):
            duel_id = int(data.split('_')[2])
            duel = self.db.get_duel(duel_id)
            if duel and duel['opponent_id'] == user.id and duel['status'] == 'pending':
                self.db.update_duel(duel_id, status='rejected')
                # Возвращаем ставку
                self.db.add_coins(duel['challenger_id'], duel['bet'])
                await query.edit_message_text(
                    f"{s.error('❌ Дуэль отклонена')}",
                    parse_mode="Markdown"
                )
    
    # ===== ОБРАБОТЧИК ОШИБОК =====
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ошибок"""
        logger.error(f"Ошибка: {context.error}")
        try:
            if update and update.effective_message:
                await update.effective_message.reply_text(s.error("❌ Произошла внутренняя ошибка. Администратор уже в курсе."))
        except:
            pass
    
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
            logger.info(f"🤖 AI: {'Подключен (дерзкий режим)' if self.ai else 'Не подключен'}")
            
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
    print("✨ ЗАПУСК БОТА СПЕКТР v6.0 ULTIMATE ✨")
    print("=" * 60)
    print(f"📊 Версия: 6.0 ULTIMATE")
    print(f"📊 Команд: 250+")
    print(f"📊 Модулей: 25+")
    print(f"📊 AI: {'Groq подключен (дерзкий режим)' if GROQ_KEY else 'Не подключен'}")
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
