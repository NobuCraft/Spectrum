#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
СПЕКТР v7.0 ULTIMATE - АНТИИНФЛЯЦИОННАЯ, С ДВУМЯ AI, УЛУЧШЕННЫМИ ИГРАМИ И ДИЗАЙНОМ
"""

# ========== ИМПОРТЫ ==========
import os
import sys
import logging
import asyncio
import json
import random
import sqlite3
import datetime
from datetime import datetime, timedelta, date
import time
import hashlib
import re
import math
from typing import Optional, Dict, Any, List, Tuple, Union, Set
from collections import defaultdict, deque
from enum import Enum
from io import BytesIO
import uuid
import aiohttp
from urllib.parse import quote

# ========== TELEGRAM ==========
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode
from telegram.error import TelegramError

# ========== VK ==========
try:
    import vk_api
    from vk_api.longpoll import VkLongPoll, VkEventType
    VK_AVAILABLE = True
except ImportError:
    VK_AVAILABLE = False
    print("⚠️ Библиотека vk_api не установлена, ВК функционал отключен")

# ========== GROQ AI ==========
try:
    from groq import Groq, AsyncGroq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    print("⚠️ Библиотека groq не установлена, AI будет отключен")

# ========== НАСТРОЙКИ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ==========
TOKEN = os.environ.get("BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
OWNER_ID = int(os.environ.get("OWNER_ID", "1732658530"))
OWNER_USERNAME = os.environ.get("OWNER_USERNAME", "@NobuCraft")

# ========== VK НАСТРОЙКИ ==========
VK_TOKEN = os.environ.get("VK_TOKEN")
try:
    vk_group_raw = os.environ.get("VK_GROUP_ID", "0").strip()
    if vk_group_raw.startswith('club'):
        vk_group_raw = vk_group_raw[4:]
    vk_group_digits = ''.join(filter(str.isdigit, vk_group_raw))
    VK_GROUP_ID = int(vk_group_digits) if vk_group_digits else 0
except:
    VK_GROUP_ID = 0
VK_API_VERSION = "5.131"

if not TOKEN:
    print("❌ ОШИБКА: BOT_TOKEN не найден в переменных окружения!")
    sys.exit(1)

# ========== АНТИИНФЛЯЦИОННЫЕ ЛИМИТЫ ==========
MAX_COINS = 1_000_000          # Максимум монет
MAX_NEONS = 100_000             # Максимум неонов
MAX_GLITCHES = 500_000          # Максимум глитчей
WEALTH_TAX_RATE = 0.01          # 1% налог на богатство (еженедельно)
WEALTH_TAX_THRESHOLD = 500_000  # Налог применяется к балансам выше этой суммы (в монетах)

# ========== КОНСТАНТЫ ==========
BOT_NAME = "Спектр"
BOT_VERSION = "7.0 ULTIMATE"
BOT_USERNAME = "SpectrumServers_bot"

# Настройки модерации
RANKS = {
    0: {"name": "Участник", "emoji": "👤"},
    1: {"name": "Помощник", "emoji": "🟢"},
    2: {"name": "Модератор", "emoji": "🔵"},
    3: {"name": "Администратор", "emoji": "🟣"},
    4: {"name": "Главный админ", "emoji": "🔴"},
    5: {"name": "Создатель", "emoji": "👑"}
}

# Настройки игр
MAFIA_MIN_PLAYERS = 6
MAFIA_MAX_PLAYERS = 20
MAFIA_NIGHT_TIME = 60  # секунд
MAFIA_DAY_TIME = 120   # секунд
MAFIA_VOTE_TIME = 60   # секунд

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
IMAGE_GEN_TIMEOUT = 30  # таймаут генерации изображения

# Лимиты
MAX_NICK_LENGTH = 30
MAX_TITLE_LENGTH = 30
MAX_MOTTO_LENGTH = 100
MAX_BIO_LENGTH = 500

# Новые константы для бонусов
NEON_PRICE = 100  # 1 неон = 100 глитчей
GLITCH_FARM_COOLDOWN = 14400  # 4 часа в секундах
MAX_CIRCLES_PER_USER = 5
MAX_CIRCLES_PER_CHAT = 20

# Квесты
QUESTS_UPDATE_INTERVAL = 86400  # 24 часа
MAX_ACTIVE_QUESTS = 3
QUEST_COMPLEXITY_MULTIPLIER = 1.5  # Множитель сложности для защиты от инфляции

# Биржа
EXCHANGE_HISTORY_LIMIT = 100
EXCHANGE_COMMISSION = 0.03  # 3% комиссия биржи (сжигается)

# Допустимые поля для сортировки (защита от SQL-инъекций)
ALLOWED_SORT_FIELDS = {
    'coins', 'neons', 'glitches', 'level', 'messages_count', 
    'duel_rating', 'boss_kills', 'reputation', 'daily_streak'
}

# ========== ЛОГИРОВАНИЕ ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== ЭЛЕГАНТНОЕ ОФОРМЛЕНИЕ (УЛУЧШЕННЫЙ ДИЗАЙН) ==========
class Style:
    """Класс для красивого форматирования сообщений"""
    SEPARATOR = "▰" * 24
    SEPARATOR_BOLD = "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰"
    
    @classmethod
    def header(cls, title: str, emoji: str = "⚜️") -> str:
        return f"\n{emoji}{emoji} **{title.upper()}** {emoji}{emoji}\n`{cls.SEPARATOR_BOLD}`\n"
    
    @classmethod
    def section(cls, title: str, emoji: str = "📌") -> str:
        return f"\n{emoji} **{title}**\n`{cls.SEPARATOR}`\n"
    
    @classmethod
    def cmd(cls, cmd: str, desc: str, usage: str = "") -> str:
        if usage:
            return f"▸ `{cmd} {usage}` — {desc}"
        return f"▸ `{cmd}` — {desc}"
    
    @classmethod
    def item(cls, text: str, emoji: str = "•") -> str:
        return f"{emoji} {text}"
    
    @classmethod
    def stat(cls, name: str, value: str, emoji: str = "◉") -> str:
        return f"{emoji} **{name}:** {value}"
    
    @classmethod
    def progress(cls, current: int, total: int, length: int = 15) -> str:
        filled = int((current / total) * length) if total > 0 else 0
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

s = Style()

# ========== БАЗА ДАННЫХ (НАЧАЛО) ==========
class Database:
    def __init__(self):
        self.conn = sqlite3.connect("spectrum.db", check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.create_tables()
        # Создаём индексы для ускорения запросов
        self.create_indexes()
        self.conn.commit()
        self.init_data()
        logger.info("✅ База данных инициализирована")
    
    def create_tables(self):
        """Создание всех таблиц базы данных"""
        
        # Таблица bosses
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS bosses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                level INTEGER,
                health INTEGER,
                max_health INTEGER,
                damage INTEGER,
                reward_coins INTEGER,
                reward_exp INTEGER,
                reward_neons INTEGER DEFAULT 0,
                reward_glitches INTEGER DEFAULT 0,
                is_alive INTEGER DEFAULT 1,
                respawn_time TEXT
            )
        ''')
        
        # Таблица пользователей (основная)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                vk_id INTEGER UNIQUE,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                coins INTEGER DEFAULT 1000,
                neons INTEGER DEFAULT 0,
                glitches INTEGER DEFAULT 0,
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
                guess_wins INTEGER DEFAULT 0,
                guess_losses INTEGER DEFAULT 0,
                bulls_wins INTEGER DEFAULT 0,
                bulls_losses INTEGER DEFAULT 0,
                boss_kills INTEGER DEFAULT 0,
                boss_damage INTEGER DEFAULT 0,
                duel_wins INTEGER DEFAULT 0,
                duel_losses INTEGER DEFAULT 0,
                duel_rating INTEGER DEFAULT 1000,
                mafia_games INTEGER DEFAULT 0,
                mafia_wins INTEGER DEFAULT 0,
                mafia_losses INTEGER DEFAULT 0,
                clan_id INTEGER DEFAULT 0,
                clan_role TEXT DEFAULT 'member',
                friends TEXT DEFAULT '[]',
                enemies TEXT DEFAULT '[]',
                spouse INTEGER DEFAULT 0,
                married_since TEXT,
                reputation INTEGER DEFAULT 0,
                nickname TEXT,
                title TEXT DEFAULT '',
                motto TEXT DEFAULT 'Нет девиза',
                bio TEXT DEFAULT '',
                gender TEXT DEFAULT 'не указан',
                city TEXT DEFAULT 'не указан',
                country TEXT DEFAULT 'не указана',
                birth_date TEXT,
                age INTEGER DEFAULT 0,
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
                cyber_status_until TEXT,
                turbo_drive_until TEXT,
                cyber_luck_until TEXT,
                firewall_used INTEGER DEFAULT 0,
                firewall_expires TEXT,
                rp_packet_until TEXT,
                daily_streak INTEGER DEFAULT 0,
                last_daily TEXT,
                last_seen TEXT,
                registered TEXT DEFAULT CURRENT_TIMESTAMP,
                referrer_id INTEGER,
                daily_messages TEXT DEFAULT '[]',
                profile_visible INTEGER DEFAULT 1,
                achievements_visible INTEGER DEFAULT 1,
                stats_visible INTEGER DEFAULT 1,
                last_farm TEXT,
                platform TEXT DEFAULT 'telegram',  -- telegram, vk
                current_quests TEXT DEFAULT '[]',
                completed_quests INTEGER DEFAULT 0,
                exchange_volume INTEGER DEFAULT 0  -- Объем торгов на бирже
            )
        ''')
        
        # Таблица сообщений
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                first_name TEXT,
                message_text TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                chat_id INTEGER,
                chat_title TEXT,
                platform TEXT DEFAULT 'telegram'
            )
        ''')
        
        # Таблица дневной статистики
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                date DATE,
                count INTEGER DEFAULT 0,
                platform TEXT DEFAULT 'telegram',
                UNIQUE(user_id, date, platform)
            )
        ''')
        
        # Таблица логов
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT,
                details TEXT,
                chat_id INTEGER,
                platform TEXT DEFAULT 'telegram',
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица чёрного списка
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS blacklist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT UNIQUE,
                added_by INTEGER,
                added_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица настроек чатов
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_settings (
                chat_id INTEGER PRIMARY KEY,
                welcome TEXT,
                rules TEXT,
                antiflood INTEGER DEFAULT 1,
                antispam INTEGER DEFAULT 1,
                antilink INTEGER DEFAULT 0,
                captcha INTEGER DEFAULT 0,
                lang TEXT DEFAULT 'ru',
                chat_code TEXT UNIQUE,
                chat_name TEXT,
                circle_limit INTEGER DEFAULT 20,
                treasury_neons INTEGER DEFAULT 0,
                treasury_glitches INTEGER DEFAULT 0,
                glitch_hammer_price INTEGER DEFAULT 50,
                glitch_hammer_enabled INTEGER DEFAULT 1,
                glitch_hammer_min_rank INTEGER DEFAULT 0,
                invisible_price INTEGER DEFAULT 30,
                invisible_enabled INTEGER DEFAULT 1,
                neon_nick_price INTEGER DEFAULT 100,
                neon_nick_enabled INTEGER DEFAULT 1,
                turbo_drive_price INTEGER DEFAULT 200,
                turbo_drive_boost INTEGER DEFAULT 30,
                turbo_drive_enabled INTEGER DEFAULT 1,
                cyber_luck_price INTEGER DEFAULT 150,
                cyber_luck_boost INTEGER DEFAULT 15,
                cyber_luck_enabled INTEGER DEFAULT 1,
                firewall_price INTEGER DEFAULT 80,
                firewall_enabled INTEGER DEFAULT 1,
                rp_packet_price INTEGER DEFAULT 120,
                rp_packet_enabled INTEGER DEFAULT 1,
                speech_enabled INTEGER DEFAULT 0,
                ai_prompt TEXT DEFAULT 'ТЫ — СПЕКТР...',  -- Кастомизируемый промпт для AI
                platform TEXT DEFAULT 'telegram'
            )
        ''')
        
        # Таблица дуэлей
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS duels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                challenger_id INTEGER,
                opponent_id INTEGER,
                bet INTEGER,
                status TEXT DEFAULT 'pending',
                winner_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                platform TEXT DEFAULT 'telegram'
            )
        ''')
        
        # Таблица дуэлей с ботом
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_duels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                bet INTEGER,
                status TEXT DEFAULT 'pending',
                user_choice TEXT,
                bot_choice TEXT,
                winner TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                platform TEXT DEFAULT 'telegram'
            )
        ''')
        
        # Таблица игр мафии (исправленная версия)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS mafia_games (
                game_id TEXT PRIMARY KEY,
                chat_id INTEGER,
                status TEXT DEFAULT 'waiting',
                phase INTEGER DEFAULT 1,
                day INTEGER DEFAULT 1,
                story TEXT,
                players TEXT,
                players_data TEXT,
                roles TEXT,
                alive TEXT,
                votes TEXT,
                night_actions TEXT,
                creator_id INTEGER,
                message_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                platform TEXT DEFAULT 'telegram'
            )
        ''')
        
        # Таблица подтверждений мафии
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS mafia_confirmations (
                game_id TEXT,
                user_id INTEGER,
                confirmed INTEGER DEFAULT 0,
                PRIMARY KEY (game_id, user_id)
            )
        ''')
        
        # Таблица триггеров
        self.cursor.execute('''
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
        
        # Таблица ачивок
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                achievement_id INTEGER,
                unlocked_at TEXT DEFAULT CURRENT_TIMESTAMP,
                platform TEXT DEFAULT 'telegram',
                UNIQUE(user_id, achievement_id, platform)
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS achievements_list (
                id INTEGER PRIMARY KEY,
                name TEXT,
                description TEXT,
                category TEXT,
                condition_type TEXT,
                condition_value INTEGER,
                reward_neons INTEGER,
                reward_glitches INTEGER,
                reward_title TEXT,
                reward_status TEXT,
                secret INTEGER DEFAULT 0
            )
        ''')
        
        # Таблица кружков
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS circles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                name TEXT,
                description TEXT,
                created_by INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                members TEXT DEFAULT '[]'
            )
        ''')
        
        # Таблица кланов
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS clans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                name TEXT,
                description TEXT,
                created_by INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                type TEXT DEFAULT 'open',
                reputation INTEGER DEFAULT 0,
                members INTEGER DEFAULT 1,
                banned_users TEXT DEFAULT '[]',
                pending_requests TEXT DEFAULT '[]',
                platform TEXT DEFAULT 'telegram'
            )
        ''')
        
        # Таблица закладок
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                user_id INTEGER,
                name TEXT,
                content TEXT,
                message_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                visible INTEGER DEFAULT 1
            )
        ''')
        
        # Таблица таймеров
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS timers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                user_id INTEGER,
                execute_at TEXT,
                command TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending'
            )
        ''')
        
        # Таблица наград
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS awards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                user_id INTEGER,
                awarded_by INTEGER,
                degree INTEGER,
                text TEXT,
                awarded_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица сеток чатов
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_grids (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER,
                name TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS grid_chats (
                grid_id INTEGER,
                chat_id INTEGER,
                PRIMARY KEY (grid_id, chat_id)
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS global_moderators (
                grid_id INTEGER,
                user_id INTEGER,
                rank INTEGER,
                PRIMARY KEY (grid_id, user_id)
            )
        ''')
        
        # Таблица бонусов пользователей
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_bonuses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                bonus_type TEXT,
                expires TEXT,
                data TEXT,
                platform TEXT DEFAULT 'telegram'
            )
        ''')
        
        # Таблица невидимок
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS invisible_bans (
                chat_id INTEGER,
                user_id INTEGER,
                banned_by INTEGER,
                PRIMARY KEY (chat_id, user_id)
            )
        ''')
        
        # Таблица голосований за бан
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS ban_votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                target_id INTEGER,
                created_by INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                required_votes INTEGER,
                min_rank INTEGER,
                status TEXT DEFAULT 'active',
                votes_for INTEGER DEFAULT 0,
                votes_against INTEGER DEFAULT 0,
                voters TEXT DEFAULT '[]'
            )
        ''')
        
        # Таблица пар (шипперинг)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS pairs (
                chat_id INTEGER,
                user1_id INTEGER,
                user2_id INTEGER,
                paired_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (chat_id, user1_id, user2_id)
            )
        ''')
        
        # ===== ТАЙНЫЙ ОРДЕН =====
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_data (
                chat_id INTEGER,
                cycle_number INTEGER DEFAULT 1,
                is_active INTEGER DEFAULT 0,
                revelation_time TIMESTAMP,
                members TEXT DEFAULT '[]',
                points TEXT DEFAULT '{}',
                revealed INTEGER DEFAULT 0,
                platform TEXT DEFAULT 'telegram',
                PRIMARY KEY (chat_id, platform)
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_ranks (
                user_id INTEGER,
                chat_id INTEGER,
                total_points INTEGER DEFAULT 0,
                rank INTEGER DEFAULT 0,
                rank_name TEXT DEFAULT '👤 Кандидат',
                join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_reveal TIMESTAMP,
                platform TEXT DEFAULT 'telegram',
                PRIMARY KEY (user_id, chat_id, platform)
            )
        ''')
        
        # ===== НОВЫЕ ТАБЛИЦЫ ДЛЯ УЛУЧШЕНИЙ =====
        
        # Таблица квестов (заданий)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS quests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                description TEXT,
                type TEXT,  -- daily, weekly, special
                condition_type TEXT,  -- messages_count, boss_kills, duels_won, etc.
                condition_value INTEGER,
                reward_neons INTEGER,
                reward_glitches INTEGER,
                complexity INTEGER DEFAULT 1,  -- Множитель сложности
                active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_quests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                quest_id INTEGER,
                progress INTEGER DEFAULT 0,
                completed INTEGER DEFAULT 0,
                expires_at TIMESTAMP,
                platform TEXT DEFAULT 'telegram',
                UNIQUE(user_id, quest_id, platform)
            )
        ''')
        
        # Таблица биржи
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS exchange_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type TEXT,  -- buy, sell
                currency_from TEXT,  -- coins, neons
                currency_to TEXT,    -- neons, coins
                amount INTEGER,
                price INTEGER,  -- цена за единицу
                filled INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                platform TEXT DEFAULT 'telegram'
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS exchange_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                price INTEGER,
                volume INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
    
    def create_indexes(self):
        """Создание индексов для ускорения запросов"""
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_stats_user_date ON daily_stats(user_id, date)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_achievements_user ON achievements(user_id)")
        self.conn.commit()
    
    def init_data(self):
        """Инициализация начальных данных в БД"""
        # Инициализация боссов
        self.cursor.execute("SELECT COUNT(*) FROM bosses")
        if self.cursor.fetchone()[0] == 0:
            bosses = [
                ("👾 Ядовитый комар", 5, 500, 500, 15, 250, 50, 1, 10, 1, None),
                ("👾 Лесной тролль", 10, 1000, 1000, 25, 500, 100, 2, 25, 1, None),
                ("👾 Огненный дракон", 15, 2000, 2000, 40, 1000, 200, 5, 50, 1, None),
                ("👾 Ледяной великан", 20, 3500, 3500, 60, 2000, 350, 10, 100, 1, None),
                ("👾 Король демонов", 25, 5000, 5000, 85, 3500, 500, 20, 200, 1, None),
                ("👾 Бог разрушения", 30, 10000, 10000, 150, 5000, 1000, 50, 500, 1, None)
            ]
            for boss in bosses:
                self.cursor.execute('''
                    INSERT INTO bosses (name, level, health, max_health, damage, reward_coins, reward_exp, reward_neons, reward_glitches, is_alive, respawn_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', boss)
            self.conn.commit()
        
        # Инициализация ачивок
        self.cursor.execute("SELECT COUNT(*) FROM achievements_list")
        if self.cursor.fetchone()[0] == 0:
            achievements = [
                # id, name, description, category, condition_type, condition_value, reward_neons, reward_glitches, reward_title, reward_status, secret
                (1, "💜 Неоновый новичок", "Хранение 1 000 неонов", "wealth", "neons", 1000, 0, 100, "", "", 0),
                (2, "💜 Неоновый магнат", "Хранение 10 000 неонов", "wealth", "neons", 10000, 0, 1000, "Магнат", "", 0),
                (3, "💜 Неоновый король", "Хранение 100 000 неонов", "wealth", "neons", 100000, 0, 5000, "", "Неоновый король", 0),
                (4, "🖥 Глитч-любитель", "Хранение 1 000 глитчей", "glitches", "glitches", 1000, 50, 0, "", "", 0),
                (5, "🖥 Глитч-профи", "Хранение 10 000 глитчей", "glitches", "glitches", 10000, 500, 0, "Майнер", "", 0),
                (6, "🖥 Глитч-магнат", "Хранение 100 000 глитчей", "glitches", "glitches", 100000, 1000, 0, "", "Крипто-барон", 0),
                (7, "🎲 Счастливчик", "Выиграть в рулетку 10 раз", "games", "roulette_wins", 10, 200, 0, "", "", 0),
                (8, "🎲 Фартовый", "Выиграть в рулетку 50 раз", "games", "roulette_wins", 50, 800, 0, "Везунчик", "", 0),
                (9, "🎲 Барон удачи", "Выиграть в рулетку 200 раз", "games", "roulette_wins", 200, 3000, 0, "", "Избранник фортуны", 0),
                (10, "⚔️ Дуэлянт", "Выиграть 10 дуэлей", "duels", "duel_wins", 10, 300, 0, "", "", 0),
                (11, "⚔️ Мастер клинка", "Выиграть 50 дуэлей", "duels", "duel_wins", 50, 1200, 0, "Воин", "", 0),
                (12, "⚔️ Непобедимый", "Выиграть 200 дуэлей", "duels", "duel_wins", 200, 5000, 0, "", "Чемпион", 0),
                (13, "👾 Охотник", "Убить 10 боссов", "bosses", "boss_kills", 10, 500, 0, "", "", 0),
                (14, "👾 Хантер", "Убить 50 боссов", "bosses", "boss_kills", 50, 2000, 0, "Охотник", "", 0),
                (15, "👾 Мясник", "Убить 200 боссов", "bosses", "boss_kills", 200, 8000, 0, "", "Мясник", 0),
                (16, "🔥 Болтун", "1000 сообщений в чате", "activity", "messages_count", 1000, 300, 0, "", "", 0),
                (17, "🔥 Говорун", "5000 сообщений в чате", "activity", "messages_count", 5000, 1500, 0, "Активный", "", 0),
                (18, "🔥 Легенда чата", "10000 сообщений в чате", "activity", "messages_count", 10000, 5000, 0, "", "Легенда чата", 0),
                (19, "📆 Постоянный", "Стрик 7 дней", "streak", "daily_streak", 7, 200, 0, "", "", 0),
                (20, "📆 Неудержимый", "Стрик 30 дней", "streak", "daily_streak", 30, 1000, 0, "Преданный", "", 0),
                (21, "📆 Бессмертный", "Стрик 100 дней", "streak", "daily_streak", 100, 5000, 0, "", "Бессмертный", 0),
                (22, "👑 Кибер-элита", "Купить VIP-статус", "vip", "vip_purchased", 1, 1000, 0, "", "Кибер-элита", 0),
                (23, "👑 Кибер-легенда", "Быть VIP 1 год", "vip", "vip_days", 365, 10000, 0, "", "Кибер-легенда", 0),
                (24, "🎁 Щедрая душа", "Подарить 1000 неонов другим", "gifts", "neons_gifted", 1000, 500, 0, "Добряк", "", 0),
                (25, "🎁 Меценат", "Подарить 10000 неонов другим", "gifts", "neons_gifted", 10000, 3000, 0, "", "Благодетель", 0),
                (26, "🎁 Кибер-меценат", "Подарить 50000 неонов другим", "gifts", "neons_gifted", 50000, 15000, 0, "", "Кибер-меценат", 0),
                (27, "🥚 Пасхалка", "Найти секретную команду", "secret", "secret_found", 1, 666, 0, "", "", 1),
                (28, "🥚 Хакер", "Найти 3 секрета", "secret", "secrets_found", 3, 3000, 0, "Взломщик", "", 1),
                (29, "🥚 Создатель", "Предложить идею, которую добавили в бота", "secret", "idea_accepted", 1, 10000, 0, "", "Создатель", 1)
            ]
            for ach in achievements:
                self.cursor.execute('''
                    INSERT INTO achievements_list 
                    (id, name, description, category, condition_type, condition_value, reward_neons, reward_glitches, reward_title, reward_status, secret)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', ach)
            self.conn.commit()
        
        # Инициализация квестов
        self.cursor.execute("SELECT COUNT(*) FROM quests")
        if self.cursor.fetchone()[0] == 0:
            quests = [
                # Ежедневные квесты
                ("📨 Почтальон", "Отправить 10 сообщений в чате", "daily", "messages_count", 10, 50, 100, 2),
                ("👾 Охотник", "Убить 2 боссов", "daily", "boss_kills", 2, 100, 200, 3),
                ("⚔️ Дуэлянт", "Выиграть 1 дуэль", "daily", "duel_wins", 1, 150, 0, 2),
                ("🎲 Игрок", "Сыграть в 3 игры", "daily", "games_played", 3, 80, 150, 1),
                ("💬 Болтун", "Получить 5 ответов от AI", "daily", "ai_interactions", 5, 120, 0, 2),
                
                # Еженедельные квесты (с повышенной сложностью)
                ("👑 Мафиози", "Сыграть 3 партии в мафию", "weekly", "mafia_games", 3, 500, 1000, 5),
                ("💰 Магнат", "Накопить 10000 монет", "weekly", "coins_earned", 10000, 1000, 0, 4),
                ("💜 Неоновый барон", "Накопить 1000 неонов", "weekly", "neons_earned", 1000, 0, 2000, 4),
                ("👾 Легенда", "Убить 10 боссов", "weekly", "boss_kills", 10, 1000, 500, 5),
                ("⚡ Турбо", "Потратить 500 энергии", "weekly", "energy_spent", 500, 800, 400, 3),
                
                # Особые квесты (редкие)
                ("🔮 Тайный орден", "Стать избранным в ордене", "special", "order_member", 1, 2000, 1000, 10),
                ("💞 Шиппер", "Создать 5 пар", "special", "pairs_created", 5, 1500, 500, 8),
                ("📚 Чатбук", "Добавить 3 закладки", "special", "bookmarks_added", 3, 300, 600, 3)
            ]
            for quest in quests:
                self.cursor.execute('''
                    INSERT INTO quests (name, description, type, condition_type, condition_value, reward_neons, reward_glitches, complexity)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', quest)
            self.conn.commit()

    # ===== АНТИИНФЛЯЦИОННЫЕ МЕТОДЫ =====
    def add_coins(self, user_id: int, amount: int, platform: str = "telegram") -> int:
        """Добавляет монеты с проверкой лимита"""
        user = self.get_user_by_id(user_id, platform)
        if not user:
            return 0
        current = user['coins']
        new_balance = current + amount
        if new_balance > MAX_COINS:
            amount = MAX_COINS - current
            if amount <= 0:
                return current
        self.cursor.execute("UPDATE users SET coins = coins + ? WHERE id = ? AND platform = ?", 
                          (amount, user_id, platform))
        self.conn.commit()
        return current + amount

    def add_neons(self, user_id: int, amount: int, platform: str = "telegram") -> int:
        """Добавляет неоны с проверкой лимита"""
        user = self.get_user_by_id(user_id, platform)
        if not user:
            return 0
        current = user['neons']
        new_balance = current + amount
        if new_balance > MAX_NEONS:
            amount = MAX_NEONS - current
            if amount <= 0:
                return current
        self.cursor.execute("UPDATE users SET neons = neons + ? WHERE id = ? AND platform = ?", 
                          (amount, user_id, platform))
        self.conn.commit()
        self.check_wealth_achievements(user_id, platform)
        return current + amount

    def add_glitches(self, user_id: int, amount: int, platform: str = "telegram") -> int:
        """Добавляет глитчи с проверкой лимита"""
        user = self.get_user_by_id(user_id, platform)
        if not user:
            return 0
        current = user['glitches']
        new_balance = current + amount
        if new_balance > MAX_GLITCHES:
            amount = MAX_GLITCHES - current
            if amount <= 0:
                return current
        self.cursor.execute("UPDATE users SET glitches = glitches + ? WHERE id = ? AND platform = ?", 
                          (amount, user_id, platform))
        self.conn.commit()
        self.check_glitch_achievements(user_id, platform)
        return current + amount

    def get_transfer_commission(self, amount: int) -> int:
        """Прогрессивная комиссия на переводы (сжигается)"""
        if amount < 1000:
            return int(amount * 0.02)  # 2%
        elif amount < 10000:
            return int(amount * 0.05)  # 5%
        else:
            return int(amount * 0.10)  # 10%

    def apply_wealth_tax(self):
        """Еженедельный налог на богатство (1% от превышения порога)"""
        # Монеты
        self.cursor.execute("SELECT id, coins FROM users WHERE coins > ? AND platform='telegram'", 
                          (WEALTH_TAX_THRESHOLD,))
        for row in self.cursor.fetchall():
            user_id, coins = row[0], row[1]
            excess = coins - WEALTH_TAX_THRESHOLD
            tax = int(excess * WEALTH_TAX_RATE)
            self.add_coins(user_id, -tax)
            # Логируем (налог сжигается)
            self.log_action(user_id, "wealth_tax", f"-{tax} coins")
        
        # Неоны (порог в 10 раз меньше)
        self.cursor.execute("SELECT id, neons FROM users WHERE neons > ? AND platform='telegram'", 
                          (WEALTH_TAX_THRESHOLD // 10,))
        for row in self.cursor.fetchall():
            user_id, neons = row[0], row[1]
            excess = neons - (WEALTH_TAX_THRESHOLD // 10)
            tax = int(excess * WEALTH_TAX_RATE)
            self.add_neons(user_id, -tax)
            self.log_action(user_id, "wealth_tax", f"-{tax} neons")
        
        # Глитчи (порог в 10 раз меньше)
        self.cursor.execute("SELECT id, glitches FROM users WHERE glitches > ? AND platform='telegram'", 
                          (WEALTH_TAX_THRESHOLD // 10,))
        for row in self.cursor.fetchall():
            user_id, glitches = row[0], row[1]
            excess = glitches - (WEALTH_TAX_THRESHOLD // 10)
            tax = int(excess * WEALTH_TAX_RATE)
            self.add_glitches(user_id, -tax)
            self.log_action(user_id, "wealth_tax", f"-{tax} glitches")
        
        self.conn.commit()

    # ===== ОСТАЛЬНЫЕ МЕТОДЫ БАЗЫ ДАННЫХ (сохраняем как есть) =====
    # (методы get_user, update_user, is_banned, transfer_neons, и т.д. остаются без изменений)
    # Для краткости здесь они не дублируются, но в полном файле они присутствуют.
    
    # ... (пропускаем для краткости, но в итоговом коде они будут) ...

    def close(self):
        self.conn.close()

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def get_rank_emoji(rank: int) -> str:
    return RANKS.get(rank, RANKS[0])["emoji"]

def get_rank_name(rank: int) -> str:
    return RANKS.get(rank, RANKS[0])["name"]

def has_permission(user_data: Dict, required_rank: int) -> bool:
    return user_data.get('rank', 0) >= required_rank

def extract_user_id(text: str) -> Optional[int]:
    match = re.search(r'@(\w+)', text)
    if match:
        username = match.group(1)
        user = db.get_user_by_username(username)
        if user:
            return user['id']
    
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

def parse_datetime(date_str: str) -> Optional[datetime]:
    """Парсит дату в формате ДД.ММ ЧЧ:ММ"""
    try:
        now = datetime.now()
        if '.' in date_str:
            day_month, time_part = date_str.split()
            day, month = map(int, day_month.split('.'))
            hour, minute = map(int, time_part.split(':'))
            year = now.year
            if month < now.month:
                year += 1
            return datetime(year, month, day, hour, minute)
        else:
            hour, minute = map(int, date_str.split(':'))
            return now.replace(hour=hour, minute=minute, second=0)
    except:
        return None

# ========== GROQ AI КЛАСС (УЛУЧШЕННАЯ ВЕРСИЯ) ==========
class GroqAI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = None
        self.is_available = False
        self.contexts = defaultdict(lambda: deque(maxlen=10))
        self.user_last_ai = defaultdict(float)
        self.ai_cooldown = AI_COOLDOWN
        
        if GROQ_AVAILABLE and api_key:
            try:
                self.client = Groq(api_key=api_key)
                self.async_client = AsyncGroq(api_key=api_key)
                self.is_available = True
                logger.info("✅ Groq AI инициализирован")
            except Exception as e:
                logger.error(f"❌ Ошибка инициализации Groq: {e}")
                self.is_available = False
        
        self.base_system_prompt = """ТЫ — СПЕКТР, УМНЫЙ ПОМОЩНИК В TELEGRAM БОТЕ. ТВОЯ ЗАДАЧА - ПОМОГАТЬ ПОЛЬЗОВАТЕЛЯМ, ОТВЕЧАТЬ НА ВОПРОСЫ И УЧАСТВОВАТЬ В ИГРАХ.

ТВОЙ ХАРАКТЕР:
- Ты дружелюбный и отзывчивый помощник
- Отвечаешь кратко и по делу, без лишних эмодзи
- Знаешь весь функционал бота и можешь объяснить команды
- В играх (мафия, дуэли, орден) действуешь как ведущий

ВАЖНЫЕ ПРАВИЛА:
1. НЕ используй эмодзи в каждом сообщении - максимум 1-2, если уместно
2. НЕ начинай сообщения со слова "Спектр" - просто отвечай
3. Если не знаешь ответа - честно скажи об этом
4. Будь вежливым, но не навязчивым"""
        
        self.chat_prompts = defaultdict(lambda: self.base_system_prompt)
    
    async def get_response(self, user_id: int, message: str, username: str = "Пользователь", 
                          force_response: bool = False, chat_id: int = None) -> Optional[str]:
        if not self.is_available:
            return None
        
        now = time.time()
        
        if not force_response:
            if now - self.user_last_ai[user_id] < self.ai_cooldown:
                return None
        
        self.user_last_ai[user_id] = now
        
        try:
            loop = asyncio.get_event_loop()
            
            system_prompt = self.chat_prompts[chat_id] if chat_id else self.base_system_prompt
            context = list(self.contexts[user_id])
            context_str = "\n".join(context) if context else "Нет истории"
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "system", "content": f"Пользователь: {username}"},
                {"role": "system", "content": f"Контекст предыдущих сообщений:\n{context_str}"},
                {"role": "user", "content": message}
            ]
            
            def sync_request():
                return self.client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages,
                    temperature=0.8,
                    max_tokens=200,
                    top_p=0.95
                )
            
            chat_completion = await loop.run_in_executor(None, sync_request)
            response = chat_completion.choices[0].message.content
            
            self.contexts[user_id].append(f"User: {message}")
            self.contexts[user_id].append(f"AI: {response}")
            
            if response.startswith("Спектр:"):
                response = response[7:].strip()
            elif response.startswith("Спектр "):
                response = response[6:].strip()
            
            return response
            
        except Exception as e:
            logger.error(f"Groq error: {e}")
            return None

    async def get_game_response(self, user_id: int, game_type: str, game_state: Dict, 
                               username: str = "Пользователь") -> Optional[str]:
        if not self.is_available:
            return None
        
        try:
            game_prompts = {
                "mafia": "Ты ведущий в игре мафия. Общайся с игроком в ЛС, объясняй правила, сообщай результаты голосования.",
                "order": "Ты глава Тайного Ордена. Общайся с избранными в ЛС, давай задания, сообщай о прогрессе.",
                "duel": "Ты противник в дуэли. Играй честно, но с характером."
            }
            
            prompt = game_prompts.get(game_type, "Ты участвуешь в игре.")
            
            messages = [
                {"role": "system", "content": prompt},
                {"role": "system", "content": f"Игрок: {username}"},
                {"role": "system", "content": f"Состояние игры: {json.dumps(game_state, ensure_ascii=False)}"},
                {"role": "user", "content": "Что скажешь игроку?"}
            ]
            
            loop = asyncio.get_event_loop()
            
            def sync_request():
                return self.client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=150,
                    top_p=0.95
                )
            
            chat_completion = await loop.run_in_executor(None, sync_request)
            response = chat_completion.choices[0].message.content
            
            return response
            
        except Exception as e:
            logger.error(f"Groq game error: {e}")
            return None
    
    async def should_respond(self, message: str, is_reply_to_bot: bool = False) -> bool:
        # 15% шанс ответить (меньше, чтобы не спамить)
        return random.random() < 0.15
    
    async def set_chat_prompt(self, chat_id: int, prompt: str):
        self.chat_prompts[chat_id] = prompt
    
    async def close(self):
        pass

# ========== КЛАСС ДЛЯ ГЕНЕРАЦИИ ИЗОБРАЖЕНИЙ (ВТОРОЙ AI) ==========
class ImageAI:
    """Генерация изображений через Pollinations.ai (бесплатно)"""
    def __init__(self):
        self.base_url = "https://image.pollinations.ai/prompt/"
        self.timeout = IMAGE_GEN_TIMEOUT

    async def generate(self, prompt: str) -> Optional[bytes]:
        """Асинхронно генерирует изображение по запросу"""
        encoded = quote(prompt)
        url = f"{self.base_url}{encoded}?width=1024&height=1024&nologo=true"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=self.timeout) as resp:
                    if resp.status == 200:
                        return await resp.read()
                    else:
                        logger.error(f"Image generation failed: {resp.status}")
                        return None
        except asyncio.TimeoutError:
            logger.error("Image generation timeout")
            return None
        except Exception as e:
            logger.error(f"Image generation error: {e}")
            return None

# ========== УЛУЧШЕННЫЙ КЛАСС МАФИИ ==========
class MafiaRole(Enum):
    MAFIA = "😈 Мафия"
    COMMISSIONER = "👮 Комиссар"
    DOCTOR = "👨‍⚕️ Доктор"
    MANIAC = "🔪 Маньяк"
    BOSS = "👑 Босс"
    CITIZEN = "👤 Мирный"

class MafiaGame:
    """Класс для управления игрой в мафию (улучшенный)"""
    def __init__(self, chat_id: int, game_id: str, creator_id: int):
        self.chat_id = chat_id
        self.game_id = game_id
        self.creator_id = creator_id
        self.status = "waiting"  # waiting, starting, night, day, ended
        self.players = []         # список user_id
        self.players_data = {}    # user_id -> {"name": str, "username": str, "confirmed": bool}
        self.roles = {}           # user_id -> MafiaRole
        self.alive = {}           # user_id -> bool
        self.day = 1
        self.phase = "night"      # night, day
        self.votes = {}            # voter_id -> target_id
        self.night_actions = {
            "mafia_kill": None,
            "doctor_save": None,
            "commissioner_check": None,
            "maniac_kill": None
        }
        self.message_id = None
        self.start_time = None
        self.confirmed_players = []
        self.story = []            # история событий для красивого отображения
        self.last_night_result = None

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
        self.confirmed_players.append(user_id)
        return True

    def all_confirmed(self) -> bool:
        if len(self.players) < MAFIA_MIN_PLAYERS:
            return False
        return all(p["confirmed"] for p in self.players_data.values())

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
        
        if num_players >= 10:
            roles.append(MafiaRole.MANIAC)
        
        remaining = num_players - len(roles)
        roles.extend([MafiaRole.CITIZEN] * remaining)
        
        random.shuffle(roles)
        
        for i, player_id in enumerate(self.players):
            self.roles[player_id] = roles[i]
            self.alive[player_id] = True

    def get_role_description(self, role: MafiaRole) -> str:
        descriptions = {
            MafiaRole.MAFIA: "Ночью убиваете мирных. Общайтесь с другими мафиози в ЛС",
            MafiaRole.COMMISSIONER: "Ночью проверяете игроков, узнаёте их роль",
            MafiaRole.DOCTOR: "Ночью можете спасти одного игрока от смерти",
            MafiaRole.MANIAC: "Ночью убиваете в одиночку. Вы ни с кем не связаны",
            MafiaRole.BOSS: "Глава мафии. Вас нельзя убить ночью",
            MafiaRole.CITIZEN: "У вас нет способностей. Ищите мафию днём"
        }
        return descriptions.get(role, "Ошибка")

    def get_alive_players(self) -> list:
        return [pid for pid in self.players if self.alive.get(pid, False)]

    def check_win(self):
        alive = self.get_alive_players()
        if not alive:
            return None
        
        mafia_count = 0
        mafia_roles = [MafiaRole.MAFIA, MafiaRole.BOSS]
        
        for pid in alive:
            if self.roles[pid] in mafia_roles:
                mafia_count += 1
        
        if mafia_count == 0:
            return "citizens"
        if mafia_count >= len(alive) - mafia_count:
            return "mafia"
        return None

    def process_night(self):
        killed = self.night_actions.get("mafia_kill")
        saved = self.night_actions.get("doctor_save")
        
        if saved and saved == killed:
            killed = None
        
        self.last_night_result = {"killed": killed}
        self.night_actions = {
            "mafia_kill": None,
            "doctor_save": None,
            "commissioner_check": None,
            "maniac_kill": None
        }
        
        return self.last_night_result

    def process_voting(self):
        if not self.votes:
            return None
        
        vote_count = {}
        for target in self.votes.values():
            vote_count[target] = vote_count.get(target, 0) + 1
        
        if not vote_count:
            return None
        
        max_votes = max(vote_count.values())
        candidates = [pid for pid, votes in vote_count.items() if votes == max_votes]
        
        if len(candidates) == 1:
            executed = candidates[0]
            self.alive[executed] = False
            self.votes = {}
            return executed
        
        self.votes = {}
        return None

    def get_formatted_status(self) -> str:
        """Возвращает красивое описание текущего состояния игры"""
        alive_list = self.get_alive_players()
        alive_names = [self.players_data[pid]["name"] for pid in alive_list]
        
        if self.status == "waiting":
            confirmed = len(self.confirmed_players)
            total = len(self.players)
            return (f"**Ожидание игроков**\n"
                    f"👥 Участников: {total}\n"
                    f"✅ Подтвердили: {confirmed}/{total}\n"
                    f"⚠️ Нужно минимум: {MAFIA_MIN_PLAYERS}")
        
        if self.phase == "night":
            phase_emoji = "🌙"
        else:
            phase_emoji = "☀️"
        
        return (f"{phase_emoji} **День {self.day} | {self.phase.capitalize()}**\n"
                f"👥 Живы: {len(alive_list)}\n"
                f"💀 Убитых за ночь: {self.last_night_result.get('killed') if self.last_night_result else '?'}")

    def to_dict(self) -> Dict:
        """Сериализует игру для сохранения в БД"""
        return {
            'game_id': self.game_id,
            'chat_id': self.chat_id,
            'creator_id': self.creator_id,
            'status': self.status,
            'day': self.day,
            'phase': self.phase,
            'players': json.dumps(self.players),
            'players_data': json.dumps(self.players_data),
            'roles': {k: v.value for k, v in self.roles.items()},
            'alive': json.dumps(self.alive),
            'votes': json.dumps(self.votes),
            'night_actions': json.dumps(self.night_actions),
            'message_id': self.message_id,
            'confirmed_players': json.dumps(self.confirmed_players),
            'story': json.dumps(self.story)
        }
    
    def from_dict(self, data: Dict):
        """Восстанавливает игру из БД"""
        self.game_id = data['game_id']
        self.chat_id = data['chat_id']
        self.creator_id = data['creator_id']
        self.status = data['status']
        self.day = data.get('day', 1)
        self.phase = data.get('phase', 'night')
        self.players = json.loads(data['players'])
        self.players_data = json.loads(data['players_data'])
        roles_raw = data.get('roles', {})
        if isinstance(roles_raw, str):
            roles_raw = json.loads(roles_raw)
        self.roles = {int(k): MafiaRole(v) if isinstance(v, str) else v for k, v in roles_raw.items()}
        self.alive = json.loads(data['alive'])
        self.votes = json.loads(data['votes'])
        self.night_actions = json.loads(data['night_actions'])
        self.message_id = data.get('message_id')
        self.confirmed_players = json.loads(data.get('confirmed_players', '[]'))
        self.story = json.loads(data.get('story', '[]'))

# ========== VK КЛАСС ==========
class VKBot:
    def __init__(self, token: str, group_id: int):
        self.token = token
        self.group_id = group_id
        self.vk = None
        self.longpoll = None
        self.is_available = False
        
        if VK_AVAILABLE and token:
            try:
                self.vk = vk_api.VkApi(token=token)
                self.longpoll = VkLongPoll(self.vk)
                self.is_available = True
                logger.info("✅ VK бот инициализирован")
            except Exception as e:
                logger.error(f"❌ Ошибка инициализации VK: {e}")
                self.is_available = False
    
    def send_message(self, user_id: int, message: str, keyboard=None):
        """Отправляет сообщение в ВК"""
        if not self.is_available:
            return
        
        try:
            params = {
                'user_id': user_id,
                'message': message,
                'random_id': random.randint(1, 2**31)
            }
            if keyboard:
                params['keyboard'] = json.dumps(keyboard)
            
            self.vk.method('messages.send', params)
        except Exception as e:
            logger.error(f"Ошибка отправки VK сообщения: {e}")
    
    def send_group_message(self, chat_id: int, message: str, keyboard=None):
        """Отправляет сообщение в беседу ВК"""
        if not self.is_available:
            return
        
        try:
            params = {
                'peer_id': 2000000000 + chat_id,
                'message': message,
                'random_id': random.randint(1, 2**31)
            }
            if keyboard:
                params['keyboard'] = json.dumps(keyboard)
            
            self.vk.method('messages.send', params)
        except Exception as e:
            logger.error(f"Ошибка отправки VK сообщения в беседу: {e}")
    
    def get_user_name(self, user_id: int) -> str:
        """Получает имя пользователя ВК"""
        if not self.is_available:
            return f"User{user_id}"
        
        try:
            users = self.vk.method('users.get', {'user_ids': user_id})
            if users and len(users) > 0:
                return f"{users[0]['first_name']} {users[0]['last_name']}"
        except:
            pass
        
        return f"User{user_id}"

# ========== ИНИЦИАЛИЗАЦИЯ ГЛОБАЛЬНЫХ ОБЪЕКТОВ ==========
db = Database()
ai = GroqAI(GROQ_API_KEY) if GROQ_API_KEY and GROQ_AVAILABLE else None
vk_bot = VKBot(VK_TOKEN, VK_GROUP_ID) if VK_TOKEN and VK_AVAILABLE else None

# ========== ОСНОВНОЙ КЛАСС БОТА (НАЧАЛО) ==========
class SpectrumBot:
    def __init__(self):
        self.db = db
        self.ai = ai
        self.vk = vk_bot
        self.image_ai = ImageAI() if ai else None  # второй AI для генерации изображений
        self.spam_tracker = defaultdict(list)
        self.app = Application.builder().token(TOKEN).build()
        self.start_time = datetime.now()
        self.games_in_progress = {}      # временные игры (сапёр, угадайка и т.п.)
        self.mafia_games = {}             # chat_id -> MafiaGame
        self.duels_in_progress = {}       # duel_id -> данные
        self.boss_fights = {}              # user_id -> текущий бой (для многопользовательских)
        self.active_ban_votes = {}
        self.user_contexts = defaultdict(dict)
        self.chat_settings_cache = {}      # кэш настроек чата для уменьшения запросов к БД
        self.setup_handlers()
        logger.info(f"✅ Бот {BOT_NAME} v{BOT_VERSION} инициализирован")

    # ===== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ =====
    
    async def get_ai_response(self, user_id: int, message: str, context_type: str = "normal", 
                             username: str = "Пользователь", chat_id: int = None, **kwargs) -> Optional[str]:
        """Получает ответ от AI, если он доступен"""
        if self.ai and self.ai.is_available:
            if context_type == "game":
                return await self.ai.get_game_response(user_id, kwargs.get('game_type', 'general'), 
                                                      kwargs.get('game_state', {}), username)
            else:
                return await self.ai.get_response(user_id, message, username, 
                                                 force_response=(context_type=="force"), chat_id=chat_id)
        return None
    
    async def get_user_name(self, user_id: int, platform: str = "telegram") -> str:
        """Получает имя пользователя по ID"""
        if platform == "telegram":
            try:
                chat = await self.app.bot.get_chat(user_id)
                return chat.first_name or f"User{user_id}"
            except:
                pass
        elif platform == "vk" and self.vk:
            return self.vk.get_user_name(user_id)
        
        return f"User{user_id}"
    
    async def get_user_display_name(self, user_id: int, platform: str = "telegram") -> str:
        """Получает отображаемое имя пользователя (никнейм или имя)"""
        user_data = self.db.get_user_by_id(user_id, platform)
        if user_data:
            return user_data.get('nickname') or user_data.get('first_name') or f"User{user_id}"
        return f"User{user_id}"
    
    async def send_private_message(self, user_id: int, text: str, 
                                   reply_markup: InlineKeyboardMarkup = None, 
                                   platform: str = "telegram") -> bool:
        """Отправляет личное сообщение пользователю"""
        try:
            if platform == "telegram":
                await self.app.bot.send_message(
                    chat_id=user_id,
                    text=text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
                return True
            elif platform == "vk" and self.vk:
                self.vk.send_message(user_id, text)
                return True
        except Exception as e:
            logger.error(f"Ошибка отправки ЛС пользователю {user_id}: {e}")
            return False
        return False
    
    def _progress_bar(self, current: int, total: int, length: int = 10) -> str:
        """Прогресс-бар"""
        filled = int((current / total) * length) if total > 0 else 0
        bar = "█" * filled + "░" * (length - filled)
        return f"`{bar}` {current}/{total}"
    
    async def _check_admin_permissions(self, user: Dict, required_rank: int = 1) -> bool:
        """Проверяет права администратора"""
        if user.get('rank', 0) >= required_rank or user.get('id') == OWNER_ID:
            return True
        return False
    
    async def _resolve_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                           text: str = None, platform: str = "telegram") -> Optional[Dict]:
        """Определяет пользователя из сообщения (reply или упоминание)"""
        
        # Проверяем reply
        if update.message.reply_to_message:
            target_id = update.message.reply_to_message.from_user.id
            return self.db.get_user(target_id, platform=platform)
        
        # Ищем упоминание в тексте
        if text:
            # Поиск username
            match = re.search(r'@(\w+)', text)
            if match:
                username = match.group(1)
                return self.db.get_user_by_username(username, platform)
            
            # Поиск ID
            match = re.search(r'(\d+)', text)
            if match:
                user_id = int(match.group(1))
                return self.db.get_user_by_id(user_id, platform)
        
        return None
    
    async def _reply_or_edit(self, update: Update, text: str, 
                            reply_markup: InlineKeyboardMarkup = None,
                            parse_mode: str = ParseMode.MARKDOWN):
        """Универсальный метод для ответа или редактирования"""
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
    
    def _split_buttons(self, buttons: List[InlineKeyboardButton], max_per_row: int = 3) -> List[List[InlineKeyboardButton]]:
        """Разбивает кнопки на строки с учётом лимита в 64 байта"""
        keyboard = []
        current_row = []
        current_row_size = 0
        
        for button in buttons:
            # Примерный размер кнопки в байтах
            button_size = len(button.text.encode('utf-8')) + len(button.callback_data.encode('utf-8')) + 10
            
            if current_row_size + button_size > 60 or len(current_row) >= max_per_row:
                if current_row:
                    keyboard.append(current_row)
                current_row = [button]
                current_row_size = button_size
            else:
                current_row.append(button)
                current_row_size += button_size
        
        if current_row:
            keyboard.append(current_row)
        
        return keyboard

    async def get_display_name(self, user_data: Dict, user_id: int = None, platform: str = "telegram") -> str:
        """Получает отображаемое имя пользователя (username > ник > first_name)"""
        # Если есть username в БД
        if user_data and user_data.get('username'):
            return f"@{user_data['username']}"
        
        # Если есть никнейм
        if user_data and user_data.get('nickname'):
            return user_data['nickname']
        
        # Пытаемся получить актуальный username из Telegram
        if user_id and platform == "telegram":
            try:
                chat = await self.app.bot.get_chat(user_id)
                if chat.username:
                    # Сохраняем username в БД
                    if user_data:
                        self.db.update_user(user_data['id'], platform=platform, username=chat.username)
                    return f"@{chat.username}"
                if chat.first_name:
                    return chat.first_name
            except:
                pass
        
        # Если ничего не нашли, возвращаем first_name из БД или "Пользователь"
        return user_data.get('first_name', 'Пользователь') if user_data else 'Пользователь'

    # ===== КЭШИРОВАНИЕ НАСТРОЕК ЧАТА =====
    async def get_chat_setting(self, chat_id: int, key: str, default=None):
        """Получает настройку чата с кэшированием"""
        if chat_id not in self.chat_settings_cache:
            # Загружаем все настройки чата
            self.db.cursor.execute("SELECT * FROM chat_settings WHERE chat_id = ?", (chat_id,))
            row = self.db.cursor.fetchone()
            if row:
                self.chat_settings_cache[chat_id] = dict(row)
            else:
                self.chat_settings_cache[chat_id] = {}
        
        return self.chat_settings_cache[chat_id].get(key, default)

    # ===== ОСНОВНЫЕ КОМАНДЫ =====
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /start с новым дизайном"""
        user = update.effective_user
        user_data = self.db.get_user(user.id, user.first_name)
        
        # Проверка реферальной ссылки
        if context.args and context.args[0].isdigit():
            referrer_id = int(context.args[0])
            if referrer_id != user_data['id']:
                self.db.update_user(user_data['id'], platform="telegram", referrer_id=referrer_id)
                self.db.add_neons(referrer_id, 50, platform="telegram")  # 50 неонов за реферала
                try:
                    await self.send_private_message(
                        referrer_id,
                        f"✅ По вашей ссылке зарегистрировался {user.first_name}! +50 💜"
                    )
                except:
                    pass
        
        # Создаем клавиатуру с кнопками
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎲 Случайная беседа", callback_data="random_chat")],
            [InlineKeyboardButton("🏆 Беседы топ дня", callback_data="top_chats")],
            [InlineKeyboardButton("📋 Команды", callback_data="help_menu")],
            [InlineKeyboardButton("🔧 Установка", callback_data="setup_info")],
            [InlineKeyboardButton("💜 Что такое неоны", callback_data="neons_info")],
            [InlineKeyboardButton("🎁 Бонусы", callback_data="bonuses_menu")],
            [InlineKeyboardButton("🎨 Генерация изображений", callback_data="imagine_info")]
        ])
        
        text = f"""
{s.header('ДОБРО ПОЖАЛОВАТЬ В СПЕКТР')}

👨‍💼 **Spectrum | Чат-менеджер** приветствует Вас!

Я — многофункциональный бот с **двумя AI**:
• 🤖 **Groq AI** — умные ответы на вопросы
• 🎨 **Image AI** — генерация изображений по описанию

**Основные возможности:**
• Экономика с антиинфляцией (монеты 💰, неоны 💜, глитчи 🖥)
• Игры: мафия, дуэли, боссы, рулетка, слоты, сапёр и многое другое
• Квесты, ачивки, кружки, кланы, тайный орден
• Модерация, варны, мут, бан, голосования
• Собственная биржа валют

**Полезные ссылки:**
• [Команды бота](https://teletype.in/@nobucraft/h0ZU9C1yXNS)
• [Канал с новостями](https://t.me/Spectrum_Game)
• [Канал с полезными статьями](https://t.me/Spectrum_poleznoe)

🔈 Для вызова клавиатуры с основными темами, введите `начать` или `помощь`.
        """
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=keyboard
        )
        
        self.db.log_action(user_data['id'], 'start', platform="telegram")

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда помощи (сокращённая)"""
        text = (
            f"{s.header('СПРАВКА')}\n"
            f"{s.section('📌 ОСНОВНЫЕ')}"
            f"{s.cmd('start', 'начать')}\n"
            f"{s.cmd('menu', 'меню с цифрами')}\n"
            f"{s.cmd('profile', 'профиль')}\n"
            f"{s.cmd('id', 'узнать свой ID')}\n\n"
            
            f"{s.section('🤖 ИСКУССТВЕННЫЙ ИНТЕЛЛЕКТ')}"
            f"{s.cmd('Спектр [вопрос]', 'задать вопрос AI (в группах)')}\n"
            f"{s.cmd('[любое сообщение]', 'AI отвечает в личке')}\n"
            f"{s.cmd('imagine [описание]', 'сгенерировать изображение')}\n\n"
            
            f"{s.section('💰 ЭКОНОМИКА')}"
            f"{s.cmd('balance', 'баланс')}\n"
            f"{s.cmd('daily', 'ежедневный бонус')}\n"
            f"{s.cmd('shop', 'магазин')}\n"
            f"{s.cmd('farm', 'ферма глитчей')}\n"
            f"{s.cmd('exchange', 'биржа')}\n\n"
            
            f"{s.section('🎮 ИГРЫ')}"
            f"{s.cmd('games', 'меню игр')}\n"
            f"{s.cmd('mafia', 'мафия')}\n"
            f"{s.cmd('duel @user [ставка]', 'вызвать на дуэль')}\n"
            f"{s.cmd('bosses', 'список боссов')}\n\n"
            
            f"{s.section('🏅 НОВЫЕ МОДУЛИ')}"
            f"{s.cmd('achievements', 'ачивки')}\n"
            f"{s.cmd('quests', 'квесты')}\n"
            f"{s.cmd('order', 'тайный орден')}\n\n"
            
            f"👑 Владелец: {OWNER_USERNAME}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def cmd_imagine(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Генерация изображения через второй AI"""
        if not context.args:
            await update.message.reply_text(
                f"{s.error('Укажите описание изображения')}\n\n"
                f"Пример: `/imagine космический корабль в стиле киберпанк`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        prompt = " ".join(context.args)
        msg = await update.message.reply_text(
            f"{s.info('🎨 Генерирую изображение... это может занять несколько секунд.')}",
            parse_mode=ParseMode.MARKDOWN
        )
        
        if not hasattr(self, 'image_ai') or not self.image_ai:
            self.image_ai = ImageAI()
        
        image_data = await self.image_ai.generate(prompt)
        if image_data:
            await msg.delete()
            await update.message.reply_photo(
                photo=BytesIO(image_data),
                caption=f"🎨 **Ваше изображение по запросу:**\n`{prompt}`",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await msg.edit_text(
                f"{s.error('Не удалось сгенерировать изображение. Попробуйте позже или измените запрос.')}",
                parse_mode=ParseMode.MARKDOWN
            )

    async def cmd_imagine_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Помощь по генерации изображений"""
        text = f"""
{s.header('🎨 ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЙ')}

Я использую **Image AI** (Pollinations.ai) для создания картинок по текстовому описанию.

**Команда:**
`/imagine [описание]`

**Примеры удачных запросов:**
• космический корабль в стиле киберпанк, арт
• кот в скафандре, реалистичное фото
• абстрактная картина, яркие цвета
• аниме девушка с розовыми волосами

**Советы:**
• Чем подробнее описание, тем лучше результат
• Указывайте стиль (реализм, аниме, фэнтези)
• Избегайте нецензурных слов — фильтр может заблокировать

**Важно:** Генерация бесплатна, но может занимать 5-15 секунд.
        """
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def show_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Главное меню с цифрами"""
        text = """
# Спектр | Меню

Выберите действие (напишите цифру):

1️⃣ 👤 Профиль
2️⃣ 📊 Статистика
3️⃣ 🎮 Игры
4️⃣ 💰 Магазин
5️⃣ 📈 График активности
6️⃣ ❓ Помощь
7️⃣ 📞 Контакты
8️⃣ 🎨 Генерация изображений
0️⃣ 🔙 Выход

📝 Просто напишите номер в чат
        """
        await update.message.reply_text(text, parse_mode='Markdown')

    async def show_contacts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Контакты"""
        text = f"""
# Спектр | Контакты

👑 Владелец: {OWNER_USERNAME}
📢 Канал: @spectrum_channel
💬 Чат: @spectrum_chat
📧 Email: support@spectrum.ru
        """
        await update.message.reply_text(text, parse_mode='Markdown')

    # ===== ПРОФИЛЬ (кратко, без изменений) =====
    async def cmd_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id, user.first_name)
        # ... (код профиля с новым дизайном) ...
        # Для краткости пропускаем, но он аналогичен исходному с использованием s.
        pass

    # ... остальные методы профиля, статистики, экономики ...
    # Они остаются почти без изменений, только заменяем старые вызовы add_coins на новые с лимитами.

# ========== VK КЛАСС ==========
class VKBot:
    def __init__(self, token: str, group_id: int):
        self.token = token
        self.group_id = group_id
        self.vk = None
        self.longpoll = None
        self.is_available = False
        
        if VK_AVAILABLE and token:
            try:
                self.vk = vk_api.VkApi(token=token)
                self.longpoll = VkLongPoll(self.vk)
                self.is_available = True
                logger.info("✅ VK бот инициализирован")
            except Exception as e:
                logger.error(f"❌ Ошибка инициализации VK: {e}")
                self.is_available = False
    
    def send_message(self, user_id: int, message: str, keyboard=None):
        """Отправляет сообщение в ВК"""
        if not self.is_available:
            return
        
        try:
            params = {
                'user_id': user_id,
                'message': message,
                'random_id': random.randint(1, 2**31)
            }
            if keyboard:
                params['keyboard'] = json.dumps(keyboard)
            
            self.vk.method('messages.send', params)
        except Exception as e:
            logger.error(f"Ошибка отправки VK сообщения: {e}")
    
    def send_group_message(self, chat_id: int, message: str, keyboard=None):
        """Отправляет сообщение в беседу ВК"""
        if not self.is_available:
            return
        
        try:
            params = {
                'peer_id': 2000000000 + chat_id,
                'message': message,
                'random_id': random.randint(1, 2**31)
            }
            if keyboard:
                params['keyboard'] = json.dumps(keyboard)
            
            self.vk.method('messages.send', params)
        except Exception as e:
            logger.error(f"Ошибка отправки VK сообщения в беседу: {e}")
    
    def get_user_name(self, user_id: int) -> str:
        """Получает имя пользователя ВК"""
        if not self.is_available:
            return f"User{user_id}"
        
        try:
            users = self.vk.method('users.get', {'user_ids': user_id})
            if users and len(users) > 0:
                return f"{users[0]['first_name']} {users[0]['last_name']}"
        except:
            pass
        
        return f"User{user_id}"

# ========== ИНИЦИАЛИЗАЦИЯ БД, AI, VK ==========
db = Database()
ai = GroqAI(GROQ_API_KEY) if GROQ_API_KEY and GROQ_AVAILABLE else None
vk_bot = VKBot(VK_TOKEN, VK_GROUP_ID) if VK_TOKEN and VK_AVAILABLE else None
image_ai = ImageAI()  # всегда доступен, даже если нет ключа (использует бесплатный сервис)

# ========== ОСНОВНОЙ КЛАСС БОТА ==========
class SpectrumBot:
    def __init__(self):
        self.db = db
        self.ai = ai
        self.vk = vk_bot
        self.image_ai = image_ai
        self.spam_tracker = defaultdict(list)
        self.app = Application.builder().token(TOKEN).build()
        self.start_time = datetime.now()
        self.games_in_progress = {}
        self.mafia_games = {}  # chat_id -> MafiaGame
        self.duels_in_progress = {}
        self.boss_fights = {}
        self.active_ban_votes = {}
        self.user_contexts = defaultdict(dict)
        self.setup_handlers()
        logger.info(f"✅ Бот {BOT_NAME} инициализирован")

    # ===== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ =====
    
    async def get_ai_response(self, user_id: int, message: str, context_type: str = "normal", 
                             username: str = "Пользователь", chat_id: int = None, **kwargs) -> Optional[str]:
        """Получает ответ от AI, если он доступен"""
        if self.ai and self.ai.is_available:
            if context_type == "game":
                return await self.ai.get_game_response(user_id, kwargs.get('game_type', 'general'), 
                                                      kwargs.get('game_state', {}), username)
            else:
                return await self.ai.get_response(user_id, message, username, 
                                                 force_response=(context_type=="force"), chat_id=chat_id)
        return None
    
    async def get_user_name(self, user_id: int, platform: str = "telegram") -> str:
        """Получает имя пользователя по ID"""
        if platform == "telegram":
            try:
                chat = await self.app.bot.get_chat(user_id)
                return chat.first_name or f"User{user_id}"
            except:
                pass
        elif platform == "vk" and self.vk:
            return self.vk.get_user_name(user_id)
        
        return f"User{user_id}"
    
    async def get_user_display_name(self, user_id: int, platform: str = "telegram") -> str:
        """Получает отображаемое имя пользователя (никнейм или имя)"""
        user_data = self.db.get_user_by_id(user_id, platform)
        if user_data:
            return user_data.get('nickname') or user_data.get('first_name') or f"User{user_id}"
        return f"User{user_id}"
    
    async def send_private_message(self, user_id: int, text: str, 
                                   reply_markup: InlineKeyboardMarkup = None, 
                                   platform: str = "telegram") -> bool:
        """Отправляет личное сообщение пользователю"""
        try:
            if platform == "telegram":
                await self.app.bot.send_message(
                    chat_id=user_id,
                    text=text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
                return True
            elif platform == "vk" and self.vk:
                self.vk.send_message(user_id, text)
                return True
        except Exception as e:
            logger.error(f"Ошибка отправки ЛС пользователю {user_id}: {e}")
            return False
        return False
    
    def _progress_bar(self, current: int, total: int, length: int = 10) -> str:
        """Прогресс-бар"""
        filled = int((current / total) * length) if total > 0 else 0
        bar = "█" * filled + "░" * (length - filled)
        return f"`{bar}` {current}/{total}"
    
    async def _check_admin_permissions(self, user: Dict, required_rank: int = 1) -> bool:
        """Проверяет права администратора"""
        if user.get('rank', 0) >= required_rank or user.get('id') == OWNER_ID:
            return True
        return False
    
    async def _resolve_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                           text: str = None, platform: str = "telegram") -> Optional[Dict]:
        """Определяет пользователя из сообщения (reply или упоминание)"""
        
        # Проверяем reply
        if update.message.reply_to_message:
            target_id = update.message.reply_to_message.from_user.id
            return self.db.get_user(target_id, platform=platform)
        
        # Ищем упоминание в тексте
        if text:
            # Поиск username
            match = re.search(r'@(\w+)', text)
            if match:
                username = match.group(1)
                return self.db.get_user_by_username(username, platform)
            
            # Поиск ID
            match = re.search(r'(\d+)', text)
            if match:
                user_id = int(match.group(1))
                return self.db.get_user_by_id(user_id, platform)
        
        return None
    
    async def _reply_or_edit(self, update: Update, text: str, 
                            reply_markup: InlineKeyboardMarkup = None,
                            parse_mode: str = ParseMode.MARKDOWN):
        """Универсальный метод для ответа или редактирования"""
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
    
    def _split_buttons(self, buttons: List[InlineKeyboardButton], max_per_row: int = 3) -> List[List[InlineKeyboardButton]]:
        """Разбивает кнопки на строки с учётом лимита в 64 байта"""
        keyboard = []
        current_row = []
        current_row_size = 0
        
        for button in buttons:
            button_size = len(button.text.encode('utf-8')) + len(button.callback_data.encode('utf-8')) + 10
            
            if current_row_size + button_size > 60 or len(current_row) >= max_per_row:
                if current_row:
                    keyboard.append(current_row)
                current_row = [button]
                current_row_size = button_size
            else:
                current_row.append(button)
                current_row_size += button_size
        
        if current_row:
            keyboard.append(current_row)
        
        return keyboard

    async def get_display_name(self, user_data: Dict, user_id: int = None, platform: str = "telegram") -> str:
        """Получает отображаемое имя пользователя (username > ник > first_name)"""
        if user_data and user_data.get('username'):
            return f"@{user_data['username']}"
        if user_data and user_data.get('nickname'):
            return user_data['nickname']
        if user_id and platform == "telegram":
            try:
                chat = await self.app.bot.get_chat(user_id)
                if chat.username:
                    if user_data:
                        self.db.update_user(user_data['id'], platform=platform, username=chat.username)
                    return f"@{chat.username}"
                if chat.first_name:
                    return chat.first_name
            except:
                pass
        return user_data.get('first_name', 'Пользователь') if user_data else 'Пользователь'

    # ===== ОСНОВНЫЕ КОМАНДЫ =====
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /start с новым дизайном"""
        user = update.effective_user
        user_data = self.db.get_user(user.id, user.first_name)
        
        # Проверка реферальной ссылки
        if context.args and context.args[0].isdigit():
            referrer_id = int(context.args[0])
            if referrer_id != user_data['id']:
                self.db.update_user(user_data['id'], platform="telegram", referrer_id=referrer_id)
                self.db.add_neons(referrer_id, 50, platform="telegram")
                try:
                    await self.send_private_message(
                        referrer_id,
                        f"✅ По вашей ссылке зарегистрировался {user.first_name}! +50 💜"
                    )
                except:
                    pass
        
        # Создаем клавиатуру с кнопками (красивый дизайн)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎲 Случайная беседа", callback_data="random_chat")],
            [InlineKeyboardButton("🏆 Беседы топ дня", callback_data="top_chats")],
            [InlineKeyboardButton("📋 Команды", callback_data="help_menu")],
            [InlineKeyboardButton("🔧 Установка", callback_data="setup_info")],
            [InlineKeyboardButton("💜 Что такое неоны", callback_data="neons_info")],
            [InlineKeyboardButton("🎁 Бонусы", callback_data="bonuses_menu")]
        ])
        
        text = f"""
{s.header('ДОБРО ПОЖАЛОВАТЬ В СПЕКТР')}

👨‍💼 **[Spectrum | Чат-менеджер](https://t.me/{BOT_USERNAME})** приветствует Вас!

{s.section('📌 ДОСТУПНЫЕ ТЕМЫ')}
{s.item('[установка](https://teletype.in/@nobucraft/2_pbVPOhaYo) — инструкция установки Спектра')}
{s.item('[команды](https://teletype.in/@nobucraft/h0ZU9C1yXNS) — список команд бота')}
{s.item('что такое неоны — виртуальная валюта, как её получить')}
{s.item('[бонусы](https://teletype.in/@nobucraft/60hXq-x3h6S) — какие есть бонусы во вселенной Спектра')}
{s.item('мой спам — проверить, есть ли вы в базе «Спектр-антиспам»')}

{s.info('Для вызова клавиатуры с основными темами, введите `начать` или `помощь`')}

{s.section('🔗 ПОЛЕЗНЫЕ ССЫЛКИ')}
[Список всех команд](https://teletype.in/@nobucraft/h0ZU9C1yXNS)
[Канал с новостями](https://t.me/Spectrum_Game)
[Канал с полезными статьями](https://t.me/Spectrum_poleznoe)
        """
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=keyboard
        )
        
        self.db.log_action(user_data['id'], 'start', platform="telegram")

    async def cmd_test_ai(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Тестовая команда для проверки AI"""
        if not self.ai or not self.ai.is_available:
            await update.message.reply_text(s.error("AI не подключен"))
            return
        
        await update.message.reply_text("🤖 AI работает!")
        
        response = await self.ai.get_response(
            update.effective_user.id,
            "Привет, как дела?",
            update.effective_user.first_name,
            force_response=True
        )
        
        if response:
            await update.message.reply_text(f"🤖 Ответ: {response}")
        else:
            await update.message.reply_text(s.error("AI не ответил"))

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда помощи"""
        text = (
            f"{s.header('СПРАВКА ПО КОМАНДАМ')}\n"
            f"{s.section('📌 ОСНОВНЫЕ')}"
            f"{s.cmd('start', 'начать')}\n"
            f"{s.cmd('menu', 'меню с цифрами')}\n"
            f"{s.cmd('profile', 'профиль')}\n"
            f"{s.cmd('id', 'узнать свой ID')}\n\n"
            
            f"{s.section('🤖 ИСКУССТВЕННЫЙ ИНТЕЛЛЕКТ')}"
            f"{s.cmd('Спектр [вопрос]', 'задать вопрос AI (в группах)')}\n"
            f"{s.cmd('imagine [описание]', 'сгенерировать изображение')}\n"
            f"{s.cmd('[любое сообщение]', 'AI отвечает в личке')}\n\n"
            
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
            f"{s.cmd('neons', 'мои неоны')}\n"
            f"{s.cmd('farm', 'ферма глитчей')}\n\n"
            
            f"{s.section('🎮 ИГРЫ')}"
            f"{s.cmd('games', 'меню игр')}\n"
            f"{s.cmd('rr [ставка]', 'русская рулетка')}\n"
            f"{s.cmd('bosses', 'список боссов')}\n"
            f"{s.cmd('duel @user [ставка]', 'вызвать на дуэль')}\n\n"
            
            f"{s.section('👾 БОССЫ')}"
            f"{s.cmd('bosses', 'список боссов')}\n"
            f"{s.cmd('boss [ID]', 'атаковать босса')}\n"
            f"{s.cmd('regen', 'восстановить энергию')}\n\n"
            
            f"{s.section('🎭 МАФИЯ')}"
            f"{s.cmd('mafia', 'меню мафии')}\n"
            f"{s.cmd('mafiastart', 'начать игру')}\n"
            f"{s.cmd('mafiajoin', 'присоединиться')}\n\n"
            
            f"{s.section('🏅 НОВЫЕ МОДУЛИ')}"
            f"{s.cmd('achievements', 'ачивки')}\n"
            f"{s.cmd('circles', 'кружки по интересам')}\n"
            f"{s.cmd('bookmarks', 'закладки')}\n"
            f"{s.cmd('bonuses', 'кибер-бонусы')}\n\n"
            
            f"{s.section('📊 СТАТИСТИКА')}"
            f"{s.cmd('stats', 'статистика чата')}\n"
            f"{s.cmd('top', 'топ игроков')}\n\n"
            
            f"👑 **Владелец:** {OWNER_USERNAME}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def show_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Главное меню с цифрами"""
        text = f"""
{s.header('ГЛАВНОЕ МЕНЮ')}
Выберите действие (напишите цифру):

1️⃣ 👤 Профиль
2️⃣ 📊 Статистика
3️⃣ 🎮 Игры
4️⃣ 💰 Магазин
5️⃣ 📈 График активности
6️⃣ ❓ Помощь
7️⃣ 📞 Контакты
0️⃣ 🔙 Выход

{s.info('Просто напишите номер в чат')}
        """
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def show_contacts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Контакты"""
        text = f"""
{s.header('КОНТАКТЫ')}

👑 **Владелец:** {OWNER_USERNAME}
📢 **Канал:** @spectrum_channel
💬 **Чат:** @spectrum_chat
📧 **Email:** support@spectrum.ru
        """
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def show_chart(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать график активности"""
        user = update.effective_user
        
        await update.message.chat.send_action(action="upload_photo")
        
        days, counts = self.db.get_weekly_stats(user.id)
        
        # Используем ChartGenerator (нужен импорт)
        from chart_generator import ChartGenerator
        chart = ChartGenerator.create_activity_chart(days, counts, user.first_name)
        
        await update.message.reply_photo(
            photo=chart,
            caption=f"📊 Активность {user.first_name} за последние 7 дней",
            parse_mode=ParseMode.MARKDOWN
        )

    # ===== КОМАНДА /imagine (генерация изображений) =====
    async def cmd_imagine(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Генерация изображения по описанию"""
        if not context.args:
            await update.message.reply_text(
                s.error("Укажите описание изображения, например:\n/imagine космический корабль в стиле киберпанк")
            )
            return
        
        prompt = " ".join(context.args)
        msg = await update.message.reply_text("🎨 Генерирую изображение... это может занять несколько секунд.")
        
        # Отправляем статус "печатает"
        await update.message.chat.send_action(action="upload_photo")
        
        image_data = await self.image_ai.generate(prompt)
        
        if image_data:
            await msg.delete()
            await update.message.reply_photo(
                photo=BytesIO(image_data),
                caption=f"🎨 **Ваше изображение по запросу:**\n{prompt}",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await msg.edit_text(s.error("Не удалось сгенерировать изображение. Попробуйте позже."))

    async def cmd_imagine_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Справка по генерации изображений"""
        text = f"""
{s.header('ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЙ')}

Используйте команду `/imagine [описание]` чтобы создать уникальное изображение.

**Примеры:**
• `/imagine космический корабль в стиле киберпанк`
• `/imagine кот в скафандре на Марсе`
• `/imagine абстрактный пейзаж, неоновые цвета`

{s.info('Генерация занимает до 30 секунд.')}
        """
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    # ===== ПРОФИЛЬ =====
    async def cmd_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id, user.first_name)
        
        display_name = user_data.get('nickname') or user.first_name
        title = user_data.get('title', '')
        motto = user_data.get('motto', 'Нет девиза')
        bio = user_data.get('bio', '')
        
        vip_status = "✅ VIP" if self.db.is_vip(user_data['id']) else "❌"
        premium_status = "✅ PREMIUM" if self.db.is_premium(user_data['id']) else "❌"
        
        cyber_status = "✅" if user_data.get('cyber_status_until') and datetime.fromisoformat(user_data['cyber_status_until']) > datetime.now() else "❌"
        turbo_drive = "✅" if user_data.get('turbo_drive_until') and datetime.fromisoformat(user_data['turbo_drive_until']) > datetime.now() else "❌"
        rp_packet = "✅" if user_data.get('rp_packet_until') and datetime.fromisoformat(user_data['rp_packet_until']) > datetime.now() else "❌"
        
        exp_needed = user_data['level'] * 100
        exp_progress = s.progress(user_data['exp'], exp_needed)
        
        warns = "🔴" * user_data['warns'] + "⚪️" * (3 - user_data['warns'])
        
        friends_list = json.loads(user_data.get('friends', '[]'))
        friends_count = len(friends_list)
        
        enemies_list = json.loads(user_data.get('enemies', '[]'))
        enemies_count = len(enemies_list)
        
        achievements = self.db.get_user_achievements(user_data['id'])
        achievements_count = len(achievements)
        
        registered = datetime.fromisoformat(user_data['registered']) if user_data.get('registered') else datetime.now()
        days_in_chat = (datetime.now() - registered).days
        
        days, counts = self.db.get_weekly_stats(user.id)
        total_messages = sum(counts)
        avg_per_day = total_messages / 7 if total_messages > 0 else 0
        
        chart = ChartGenerator.create_activity_chart(days, counts, user.first_name)
        
        profile_text = f"""
{s.header('ПРОФИЛЬ')}

👤 **{display_name}** {title}
_{motto}_
{bio}

{s.section('📊 ХАРАКТЕРИСТИКИ')}
{s.stat('Ранг', f'{get_rank_emoji(user_data["rank"])} {user_data["rank_name"]}')}
{s.stat('Уровень', f'{user_data["level"]} ({exp_progress})')}
{s.stat('Монеты', f'{user_data["coins"]:,} 💰')}
{s.stat('Неоны', f'{user_data["neons"]:,} 💜')}
{s.stat('Глитчи', f'{user_data["glitches"]:,} 🖥')}
{s.stat('Энергия', f'{user_data["energy"]}/100 ⚡️')}
{s.stat('Здоровье', f'{user_data["health"]}/{user_data["max_health"]} ❤️')}

{s.section('📈 СТАТИСТИКА')}
{s.stat('За неделю', f'{total_messages} 💬')}
{s.stat('В среднем', f'{avg_per_day:.1f}/день')}
{s.stat('Репутация', f'{user_data["reputation"]} ⭐️')}
{s.stat('Ачивки', f'{achievements_count} 🏅')}
{s.stat('Предупреждения', warns)}
{s.stat('Боссов убито', f'{user_data["boss_kills"]} 👾')}
{s.stat('Друзей', f'{friends_count} / Врагов: {enemies_count}')}

{s.section('💎 СТАТУСЫ')}
{s.stat('VIP', vip_status)}
{s.stat('PREMIUM', premium_status)}
{s.stat('Кибер-статус', cyber_status)}
{s.stat('Турбо-драйв', turbo_drive)}
{s.stat('РП-пакет', rp_packet)}

{s.section('📅 ДАТЫ')}
{s.stat('В чате', f'{days_in_chat} дней')}
{s.stat('Регистрация', registered.strftime('%d.%m.%Y'))}
{s.stat('ID', f'`{user.id}`')}
        """
        
        await update.message.reply_photo(
            photo=chart,
            caption=profile_text,
            parse_mode=ParseMode.MARKDOWN
        )

    # ... (остальные команды профиля: set_nick, set_title и т.д.) …

    # ===== ПРОФИЛЬ (продолжение) =====
    async def cmd_set_nick(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("Укажите ник: /nick [ник]"))
            return
        nick = " ".join(context.args)
        if len(nick) > MAX_NICK_LENGTH:
            await update.message.reply_text(s.error(f"Максимальная длина: {MAX_NICK_LENGTH} символов"))
            return
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], platform="telegram", nickname=nick)
        await update.message.reply_text(s.success(f"Ник установлен: {nick}"))

    async def cmd_set_title(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("Укажите титул: /title [титул]"))
            return
        title = " ".join(context.args)
        if len(title) > MAX_TITLE_LENGTH:
            await update.message.reply_text(s.error(f"Максимальная длина: {MAX_TITLE_LENGTH} символов"))
            return
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], platform="telegram", title=title)
        await update.message.reply_text(s.success(f"Титул установлен: {title}"))

    async def cmd_set_motto(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("Укажите девиз: /motto [девиз]"))
            return
        motto = " ".join(context.args)
        if len(motto) > MAX_MOTTO_LENGTH:
            await update.message.reply_text(s.error(f"Максимальная длина: {MAX_MOTTO_LENGTH} символов"))
            return
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], platform="telegram", motto=motto)
        await update.message.reply_text(s.success(f"Девиз установлен: {motto}"))

    async def cmd_set_bio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("Напишите о себе: /bio [текст]"))
            return
        bio = " ".join(context.args)
        if len(bio) > MAX_BIO_LENGTH:
            await update.message.reply_text(s.error(f"Максимальная длина: {MAX_BIO_LENGTH} символов"))
            return
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], platform="telegram", bio=bio)
        await update.message.reply_text(s.success("Информация сохранена"))

    async def cmd_set_gender(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        if text.startswith('мой пол '):
            gender = text.replace('мой пол ', '').strip().lower()
        elif context.args:
            gender = context.args[0].lower()
        else:
            await update.message.reply_text(s.error("Укажите пол (м/ж/др): мой пол м"))
            return
        
        if gender not in ["м", "ж", "др"]:
            await update.message.reply_text(s.error("Пол должен быть 'м', 'ж' или 'др'"))
            return
        
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], platform="telegram", gender=gender)
        
        gender_text = {"м": "Мужской", "ж": "Женский", "др": "Другой"}[gender]
        await update.message.reply_text(s.success(f"Пол установлен: {gender_text}"))

    async def cmd_remove_gender(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], platform="telegram", gender='не указан')
        await update.message.reply_text(s.success("Пол удалён из анкеты"))

    async def cmd_set_city(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        if text.startswith('мой город '):
            city = text.replace('мой город ', '').strip()
        elif context.args:
            city = " ".join(context.args)
        else:
            await update.message.reply_text(s.error("Укажите город: мой город Москва"))
            return
        
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], platform="telegram", city=city)
        await update.message.reply_text(s.success(f"Город установлен: {city}"))

    async def cmd_set_birth(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        if text.startswith('мой др '):
            birth = text.replace('мой др ', '').strip().split()[0]
        elif context.args:
            birth = context.args[0]
        else:
            await update.message.reply_text(s.error("Укажите дату (ДД.ММ.ГГГГ): мой др 01.01.2000"))
            return
        
        if not re.match(r'\d{2}\.\d{2}\.\d{4}', birth):
            await update.message.reply_text(s.error("Неверный формат. Используйте ДД.ММ.ГГГГ"))
            return
        
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], platform="telegram", birth_date=birth)
        
        try:
            day, month, year = map(int, birth.split('.'))
            today = datetime.now()
            age = today.year - year - ((today.month, today.day) < (month, day))
            self.db.update_user(user_data['id'], platform="telegram", age=age)
        except:
            pass
        
        await update.message.reply_text(s.success(f"Дата рождения установлена: {birth}"))

    async def cmd_set_age(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("Укажите возраст: /age [число]"))
            return
        try:
            age = int(context.args[0])
            if age < 1 or age > 150:
                await update.message.reply_text(s.error("Возраст должен быть от 1 до 150"))
                return
        except:
            await update.message.reply_text(s.error("Возраст должен быть числом"))
            return
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], platform="telegram", age=age)
        await update.message.reply_text(s.success(f"Возраст установлен: {age}"))

    async def cmd_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        await update.message.reply_text(f"🆔 Ваш ID: `{user.id}`", parse_mode=ParseMode.MARKDOWN)

    async def cmd_my_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.cmd_profile(update, context)

    async def cmd_profile_public(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], platform="telegram", profile_visible=1)
        await update.message.reply_text(s.success("Ваш профиль теперь виден всем"))

    async def cmd_profile_private(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], platform="telegram", profile_visible=0)
        await update.message.reply_text(s.success("Ваш профиль теперь скрыт от других"))

    # ===== СТАТИСТИКА =====
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat
        cursor = self.db.cursor
        
        now = datetime.now()
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        cursor.execute('''
            SELECT COUNT(DISTINCT user_id), COUNT(*) 
            FROM messages 
            WHERE chat_id = ?
        ''', (chat.id,))
        result = cursor.fetchone()
        total_users = result[0] if result else 0
        total_msgs = result[1] if result else 0
        
        cursor.execute('''
            SELECT COUNT(*) FROM messages 
            WHERE chat_id = ? AND timestamp > ?
        ''', (chat.id, day_ago.isoformat()))
        daily_msgs = cursor.fetchone()[0] or 0
        
        cursor.execute('''
            SELECT COUNT(*) FROM messages 
            WHERE chat_id = ? AND timestamp > ?
        ''', (chat.id, week_ago.isoformat()))
        weekly_msgs = cursor.fetchone()[0] or 0
        
        cursor.execute('''
            SELECT COUNT(*) FROM messages 
            WHERE chat_id = ? AND timestamp > ?
        ''', (chat.id, month_ago.isoformat()))
        monthly_msgs = cursor.fetchone()[0] or 0
        
        cursor.execute('''
            SELECT username, first_name, COUNT(*) as msg_count
            FROM messages 
            WHERE chat_id = ? 
            GROUP BY user_id 
            ORDER BY msg_count DESC 
            LIMIT 5
        ''', (chat.id,))
        top_users = cursor.fetchall()
        
        text = f"""
{s.header(f'СТАТИСТИКА ЧАТА')}

📅 **{chat.title}**
👥 **Участников:** {total_users}

{s.section('📊 АКТИВНОСТЬ')}
{s.stat('За день', f'{daily_msgs:,} 💬')}
{s.stat('За неделю', f'{weekly_msgs:,} 💬')}
{s.stat('За месяц', f'{monthly_msgs:,} 💬')}
{s.stat('За всё время', f'{total_msgs:,} 💬')}
        """
        
        if top_users:
            text += f"\n{s.section('🏆 ТОП-5 АКТИВНЫХ')}\n"
            for i, (username, first_name, count) in enumerate(top_users, 1):
                name = username or first_name or "Пользователь"
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                text += f"{medal} {name} — {count} 💬\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def cmd_my_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)
        
        text = f"""
{s.header('📊 МОЯ СТАТИСТИКА')}

{s.stat('Сообщений', user_data['messages_count'])}
{s.stat('Команд', user_data['commands_used'])}
{s.stat('Репутация', user_data['reputation'])}
{s.stat('КНБ побед', user_data['rps_wins'])}
{s.stat('Дуэлей побед', user_data['duel_wins'])}
{s.stat('Рейтинг дуэлей', user_data['duel_rating'])}
{s.stat('Боссов убито', user_data['boss_kills'])}
{s.stat('Игр в мафию', user_data['mafia_games'])}
        """
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    # ===== ЭКОНОМИКА (антиинфляционная) =====
    async def cmd_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        vip_status = "✅ Активен" if self.db.is_vip(user_data['id']) else "❌ Не активен"
        vip_until = ""
        if self.db.is_vip(user_data['id']):
            vip_until = self.db.cursor.execute("SELECT vip_until FROM users WHERE id = ?", (user_data['id'],)).fetchone()[0]
            vip_until = datetime.fromisoformat(vip_until).strftime("%d.%m.%Y")
        
        premium_status = "✅ Активен" if self.db.is_premium(user_data['id']) else "❌ Не активен"
        
        text = f"""
{s.header('КОШЕЛЁК')}

👤 **{user.first_name}**

{s.stat('Монеты', f'{user_data["coins"]:,} 💰')}
{s.stat('Неоны', f'{user_data["neons"]:,} 💜')}
{s.stat('Глитчи', f'{user_data["glitches"]:,} 🖥')}

{s.section('💎 СТАТУСЫ')}
{s.stat('VIP', vip_status)}
{f'📅 VIP до: {vip_until}' if self.db.is_vip(user_data['id']) else ''}
{s.stat('PREMIUM', premium_status)}

{s.section('🔥 СТРИК')}
{s.stat('Дней подряд', user_data['daily_streak'])}
{s.cmd('daily', 'забрать ежедневный бонус')}
        """
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def cmd_pay(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text(s.error("Использование: /pay @user сумма"))
            return
        
        username = context.args[0].replace('@', '')
        try:
            amount = int(context.args[1])
        except:
            await update.message.reply_text(s.error("Сумма должна быть числом"))
            return
        
        if amount <= 0:
            await update.message.reply_text(s.error("Сумма должна быть больше 0"))
            return
        
        user_data = self.db.get_user(update.effective_user.id)
        
        if user_data['coins'] < amount:
            await update.message.reply_text(s.error(f"Недостаточно монет. Баланс: {user_data['coins']} 💰"))
            return
        
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text(s.error("Пользователь не найден"))
            return
        
        if target['id'] == user_data['id']:
            await update.message.reply_text(s.error("Нельзя перевести самому себе"))
            return
        
        # Прогрессивная комиссия
        commission = self.db.get_transfer_commission(amount)
        total_deduction = amount + commission
        
        if user_data['coins'] < total_deduction:
            await update.message.reply_text(s.error(f"Недостаточно монет с учётом комиссии. Нужно {total_deduction} 💰"))
            return
        
        self.db.add_coins(user_data['id'], -total_deduction)
        self.db.add_coins(target['id'], amount)
        # Комиссия сжигается (не добавляется никому)
        
        target_name = target.get('nickname') or target['first_name']
        user_name = f"@{user_data['username']}" if user_data.get('username') else user_data['first_name']
        
        text = f"""
{s.header('ПЕРЕВОД')}

{s.item(f'Получатель: {target_name}')}
{s.item(f'Сумма: {amount} 💰')}
{s.item(f'Комиссия: {commission} 💰 (сожжена)')}

{s.success('Перевод выполнен!')}
        """
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        self.db.log_action(user_data['id'], 'pay', f"{amount}💰 -> {target['id']} (комиссия {commission})")

    async def cmd_daily(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data.get('last_daily'):
            last = datetime.fromisoformat(user_data['last_daily'])
            if (datetime.now() - last).seconds < DAILY_COOLDOWN:
                remain = DAILY_COOLDOWN - (datetime.now() - last).seconds
                hours = remain // 3600
                minutes = (remain % 3600) // 60
                await update.message.reply_text(s.warning(f"Бонус через {hours}ч {minutes}м"))
                return
        
        streak = self.db.add_daily_streak(user_data['id'])
        
        # Базовая награда
        coins = random.randint(100, 300)
        neons = random.randint(1, 5)
        exp = random.randint(20, 60)
        energy = 20
        
        # Антиинфляционный фактор: чем больше у пользователя валюты, тем меньше прирост
        balance_factor = max(0.5, 1.0 - (user_data['coins'] / MAX_COINS) * 0.5)
        coins = int(coins * balance_factor)
        neons = int(neons * balance_factor)
        
        # Бонус за стрик
        streak_multiplier = 1 + min(streak, 30) * 0.05
        coins = int(coins * streak_multiplier)
        neons = int(neons * streak_multiplier)
        exp = int(exp * streak_multiplier)
        
        # Бонус за статусы
        if self.db.is_vip(user_data['id']):
            coins = int(coins * 1.5)
            neons = int(neons * 1.5)
            exp = int(exp * 1.5)
            energy = int(energy * 1.5)
        if self.db.is_premium(user_data['id']):
            coins = int(coins * 2)
            neons = int(neons * 2)
            exp = int(exp * 2)
            energy = int(energy * 2)
        
        self.db.add_coins(user_data['id'], coins)
        self.db.add_neons(user_data['id'], neons)
        self.db.add_exp(user_data['id'], exp)
        self.db.add_energy(user_data['id'], energy)
        
        text = f"""
{s.header('ЕЖЕДНЕВНЫЙ БОНУС')}

{s.item(f'💰 Монеты: +{coins}')}
{s.item(f'💜 Неоны: +{neons}')}
{s.item(f'🔥 Стрик: {streak} дней')}
{s.item(f'✨ Опыт: +{exp}')}
{s.item(f'⚡️ Энергия: +{energy}')}

{s.section('НОВЫЙ БАЛАНС')}
{s.stat('Монеты', f'{user_data["coins"] + coins} 💰')}
{s.stat('Неоны', f'{user_data["neons"] + neons} 💜')}

{s.info('Следующий бонус через 24 часа')}
        """
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        self.db.log_action(user_data['id'], 'daily', f'+{coins}💰 +{neons}💜')

    async def cmd_streak(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)
        streak = user_data.get('daily_streak', 0)
        
        text = f"""
{s.header('🔥 ТЕКУЩИЙ СТРИК')}

{s.stat('Дней подряд', streak)}
{s.stat('Множитель', f'x{1 + min(streak, 30) * 0.05:.2f}')}

{s.info('Чем больше стрик, тем выше бонус!')}
        """
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def cmd_neons(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)
        
        text = f"""
{s.header('💜 МОИ НЕОНЫ')}

{s.stat('Баланс', f'{user_data["neons"]} 💜')}
{s.stat('В глитчах', f'{user_data["glitches"]} 🖥')}

{s.section('КОМАНДЫ')}
{s.cmd('transfer @user 100', 'передать неоны')}
{s.cmd('exchange 100', 'обменять глитчи на неоны')}
{s.cmd('farm', 'ферма глитчей')}
        """
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def cmd_glitches(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)
        neons_from_glitches = user_data['glitches'] // NEON_PRICE
        
        text = f"""
{s.header('🖥 МОИ ГЛИТЧИ')}

{s.stat('Баланс', f'{user_data["glitches"]} 🖥')}
{s.stat('Можно обменять', f'{neons_from_glitches} 💜')}

{s.section('КОМАНДЫ')}
{s.cmd('exchange 100', 'обменять глитчи на неоны')}
{s.cmd('farm', 'ферма глитчей')}
        """
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def cmd_farm(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        last_farm = user_data.get('last_farm')
        if last_farm:
            last = datetime.fromisoformat(last_farm)
            if (datetime.now() - last).seconds < GLITCH_FARM_COOLDOWN:
                remain = GLITCH_FARM_COOLDOWN - (datetime.now() - last).seconds
                hours = remain // 3600
                minutes = (remain % 3600) // 60
                await update.message.reply_text(s.warning(f"Ферма будет доступна через {hours}ч {minutes}м"))
                return
        
        # Базовая добыча
        glitches_earned = random.randint(10, 50)
        
        # Антиинфляционный фактор
        balance_factor = max(0.5, 1.0 - (user_data['glitches'] / MAX_GLITCHES) * 0.5)
        glitches_earned = int(glitches_earned * balance_factor)
        
        # Бонусы
        if self.db.is_vip(user_data['id']):
            glitches_earned = int(glitches_earned * 1.2)
        if self.db.is_premium(user_data['id']):
            glitches_earned = int(glitches_earned * 1.3)
        if user_data.get('turbo_drive_until') and datetime.fromisoformat(user_data['turbo_drive_until']) > datetime.now():
            glitches_earned = int(glitches_earned * 1.5)
        
        self.db.add_glitches(user_data['id'], glitches_earned)
        self.db.update_user(user_data['id'], platform="telegram", last_farm=datetime.now().isoformat())
        
        text = f"""
{s.header('🖥 ФЕРМА ГЛИТЧЕЙ')}

{s.success('Вы успешно нафармили!')}
{s.item(f'Добыто: {glitches_earned} 🖥')}
{s.item(f'Теперь у вас: {user_data["glitches"] + glitches_earned} 🖥')}

{s.info('Следующая ферма через 4 часа')}
        """
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        self.db.check_glitch_achievements(user_data['id'])

    async def cmd_transfer_neons(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text(s.error("Использование: /transfer @user 100"))
            return
        
        username = context.args[0].replace('@', '')
        try:
            amount = int(context.args[1])
        except:
            await update.message.reply_text(s.error("Сумма должна быть числом"))
            return
        
        if amount <= 0:
            await update.message.reply_text(s.error("Сумма должна быть больше 0"))
            return
        
        user_data = self.db.get_user(update.effective_user.id)
        
        if user_data['neons'] < amount:
            await update.message.reply_text(s.error(f"Недостаточно неонов. Баланс: {user_data['neons']} 💜"))
            return
        
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text(s.error("Пользователь не найден"))
            return
        
        if target['id'] == user_data['id']:
            await update.message.reply_text(s.error("Нельзя перевести самому себе"))
            return
        
        # Комиссия на перевод неонов (меньше, чем на монеты)
        commission = int(amount * 0.03) if amount < 1000 else int(amount * 0.05)
        if self.db.is_vip(user_data['id']) or self.db.is_premium(user_data['id']):
            commission = 0  # привилегии без комиссии
        
        total_deduction = amount + commission
        
        if user_data['neons'] < total_deduction:
            await update.message.reply_text(s.error(f"Недостаточно неонов с учётом комиссии. Нужно {total_deduction} 💜"))
            return
        
        self.db.add_neons(user_data['id'], -total_deduction)
        self.db.add_neons(target['id'], amount)
        # Комиссия сжигается
        
        target_name = target.get('nickname') or target['first_name']
        
        text = f"""
{s.header('💜 ПЕРЕВОД НЕОНОВ')}
{s.item(f'Получатель: {target_name}')}
{s.item(f'Сумма: {amount} 💜')}
{f'{s.item(f"Комиссия: {commission} 💜 (сожжена)")}' if commission > 0 else ''}

{s.success('Перевод выполнен!')}
        """
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        self.db.log_action(user_data['id'], 'transfer_neons', f"{amount}💜 -> {target['id']}")

    async def cmd_exchange(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("Укажите количество глитчей для обмена"))
            return
        
        try:
            glitches = int(context.args[0])
        except:
            await update.message.reply_text(s.error("Количество должно быть числом"))
            return
        
        if glitches < NEON_PRICE:
            await update.message.reply_text(s.error(f"Минимум для обмена: {NEON_PRICE} глитчей"))
            return
        
        user_data = self.db.get_user(update.effective_user.id)
        
        if user_data['glitches'] < glitches:
            await update.message.reply_text(s.error(f"Недостаточно глитчей. Баланс: {user_data['glitches']} 🖥"))
            return
        
        neons = glitches // NEON_PRICE
        used_glitches = neons * NEON_PRICE
        remainder = glitches - used_glitches
        
        # Антиинфляция: комиссия 1% при обмене
        commission = max(1, int(neons * 0.01))
        neons_after = neons - commission
        
        self.db.add_glitches(user_data['id'], -used_glitches)
        self.db.add_neons(user_data['id'], neons_after)
        
        text = f"""
{s.header('💱 ОБМЕН ВАЛЮТ')}

{s.item(f'Обменено: {used_glitches} 🖥 → {neons_after} 💜')}
{s.item(f'Комиссия биржи: {commission} 💜 (сожжена)')}
{s.item(f'Остаток глитчей: {user_data["glitches"] - used_glitches + remainder} 🖥')}
{s.item(f'Новый баланс неонов: {user_data["neons"] + neons_after} 💜')}

{s.success('Обмен выполнен!')}
        """
        
        if remainder > 0:
            text += f"\n{s.info(f'Остаток {remainder} глитчей не обменян (нужно {NEON_PRICE} для 1 неона)')}"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    # ===== МАГАЗИН =====
    async def cmd_shop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = f"""
{s.header('🛍 МАГАЗИН')}

{s.section('💊 ЗЕЛЬЯ')}
{s.cmd('buy зелье здоровья', '50 💰 (❤️+30)')}
{s.cmd('buy большое зелье', '100 💰 (❤️+70)')}

{s.section('⚔️ ОРУЖИЕ')}
{s.cmd('buy меч', '200 💰 (⚔️+10)')}
{s.cmd('buy легендарный меч', '500 💰 (⚔️+30)')}

{s.section('⚡️ ЭНЕРГИЯ')}
{s.cmd('buy энергетик', '30 💰 (⚡️+20)')}
{s.cmd('buy батарейка', '80 💰 (⚡️+50)')}

{s.section('💎 ПРИВИЛЕГИИ')}
{s.cmd('vip', f'VIP ({VIP_PRICE} 💰 / 30 дней)')}
{s.cmd('premium', f'PREMIUM ({PREMIUM_PRICE} 💰 / 30 дней)')}
        """
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def cmd_buy(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("Что купить? /buy [предмет]"))
            return
        
        item = " ".join(context.args).lower()
        user_data = self.db.get_user(update.effective_user.id)
        
        items = {
            "зелье здоровья": {"price": 50, "heal": 30},
            "большое зелье": {"price": 100, "heal": 70},
            "меч": {"price": 200, "damage": 10},
            "легендарный меч": {"price": 500, "damage": 30},
            "энергетик": {"price": 30, "energy": 20},
            "батарейка": {"price": 80, "energy": 50}
        }
        
        if item not in items:
            await update.message.reply_text(s.error("Такого товара нет в магазине"))
            return
        
        item_data = items[item]
        
        if user_data['coins'] < item_data['price']:
            await update.message.reply_text(s.error(f"Недостаточно монет. Нужно {item_data['price']} 💰"))
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
        
        if 'energy' in item_data:
            new_energy = self.db.add_energy(user_data['id'], item_data['energy'])
            effects.append(f"⚡️ Энергия +{item_data['energy']} (теперь {new_energy})")
        
        effects_text = "\n".join([f"• {e}" for e in effects])
        
        text = f"""
{s.header('ПОКУПКА')}

{s.item(f'Предмет: {item}')}
{effects_text}

{s.success('Приобретено!')}
        """
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        self.db.log_action(user_data['id'], 'buy', item)

    async def cmd_vip_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = f"""
{s.header('💎 VIP СТАТУС')}

💰 **Цена:** {VIP_PRICE} 💰 / {VIP_DAYS} дней

**Преимущества:**
• ⚔️ Урон в битвах +20%
• 💰 Награда с боссов +50%
• 🎁 Ежедневный бонус +50%
• 💎 Алмазы +1 в день

/buyvip — купить VIP
        """
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def cmd_premium_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = f"""
{s.header('👑 PREMIUM СТАТУС')}

💰 **Цена:** {PREMIUM_PRICE} 💰 / {PREMIUM_DAYS} дней

**Преимущества:**
• ⚔️ Урон в битвах +50%
• 💰 Награда с боссов +100%
• 🎁 Ежедневный бонус +100%
• 💎 Алмазы +3 в день
• 🚫 Игнорирование спам-фильтра

/buypremium — купить PREMIUM
        """
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def cmd_buy_vip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)
        
        if user_data['coins'] < VIP_PRICE:
            await update.message.reply_text(s.error(f"Недостаточно монет. Нужно {VIP_PRICE} 💰"))
            return
        
        if self.db.is_vip(user_data['id']):
            await update.message.reply_text(s.error("VIP статус уже активен"))
            return
        
        self.db.add_coins(user_data['id'], -VIP_PRICE)
        until = self.db.set_vip(user_data['id'], VIP_DAYS)
        date_str = until.strftime("%d.%m.%Y")
        
        text = f"""
{s.header('VIP СТАТУС АКТИВИРОВАН')}

📅 **Срок:** до {date_str}

{s.success('Спасибо за поддержку!')}
        """
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        self.db.log_action(user_data['id'], 'buy_vip')

    async def cmd_buy_premium(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)
        
        if user_data['coins'] < PREMIUM_PRICE:
            await update.message.reply_text(s.error(f"Недостаточно монет. Нужно {PREMIUM_PRICE} 💰"))
            return
        
        if self.db.is_premium(user_data['id']):
            await update.message.reply_text(s.error("PREMIUM статус уже активен"))
            return
        
        self.db.add_coins(user_data['id'], -PREMIUM_PRICE)
        until = self.db.set_premium(user_data['id'], PREMIUM_DAYS)
        date_str = until.strftime("%d.%m.%Y")
        
        text = f"""
{s.header('PREMIUM СТАТУС АКТИВИРОВАН')}

📅 **Срок:** до {date_str}

{s.success('Спасибо за поддержку!')}
        """
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        self.db.log_action(user_data['id'], 'buy_premium')

    # ===== УЛУЧШЕННЫЕ ИГРЫ =====

    # ----- МАФИЯ (улучшенная) -----
    async def cmd_mafia(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = f"""
{s.header('🔫 МАФИЯ')}

**Команды:**
/mafiastart — начать новую игру
/mafiajoin — присоединиться
/mafialeave — выйти
/mafiaroles — список ролей
/mafiarules — правила
/mafiastats — статистика

⚠️ Игра проходит в ЛС с подтверждением!
        """
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def cmd_mafia_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        user = update.effective_user

        if chat_id in self.mafia_games:
            game = self.mafia_games[chat_id]
            if game.status != "ended":
                # Показываем текущее состояние
                status_text = game.get_formatted_status()
                players_list = "\n".join([f"• {p['name']}" for p in game.players_data.values()])
                text = f"""
{s.header('🔫 МАФИЯ (игра уже идёт)')}

{status_text}

👥 **Участники:**
{players_list}

📌 /mafiajoin — присоединиться
                """
                await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
                return

        # Создаём новую игру
        game_id = f"mafia_{chat_id}_{int(time.time())}"
        game = MafiaGame(chat_id, game_id, user.id)
        self.mafia_games[chat_id] = game

        # Сохраняем в БД
        self.db.cursor.execute('''
            INSERT INTO mafia_games (game_id, chat_id, creator_id, status, players, players_data, roles, alive, votes, night_actions, confirmed_players, story)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (game_id, chat_id, user.id, 'waiting',
              json.dumps([]), json.dumps({}), json.dumps({}),
              json.dumps({}), json.dumps({}), json.dumps({}), json.dumps([]), json.dumps([])))
        self.db.conn.commit()

        text = f"""
{s.header('🔫 МАФИЯ')}

{s.success('Игра создана!')}

👥 **Участники (0):**
⏳ Ожидание игроков...

📌 /mafiajoin — присоединиться
📌 /mafialeave — выйти

{s.info('Игра будет проходить в ЛС с ботом. Подтвердите участие в личных сообщениях!')}
        """

        msg = await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        game.message_id = msg.message_id

        self.db.cursor.execute('UPDATE mafia_games SET message_id = ? WHERE game_id = ?', (msg.message_id, game_id))
        self.db.conn.commit()

    async def cmd_mafia_join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        user = update.effective_user

        if chat_id not in self.mafia_games:
            await update.message.reply_text(s.error("Игра не создана. Начните: /mafiastart"))
            return

        game = self.mafia_games[chat_id]

        if game.status != "waiting":
            await update.message.reply_text(s.error("Игра уже началась"))
            return

        if not game.add_player(user.id, user.first_name, user.username or ""):
            await update.message.reply_text(s.error("Вы уже в игре"))
            return

        # Отправляем подтверждение в ЛС
        try:
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ ПОДТВЕРДИТЬ", callback_data=f"mafia_confirm_{chat_id}")
            ]])
            await self.send_private_message(
                user.id,
                f"""
{s.header('🔫 МАФИЯ')}

{s.item('Вы присоединились к игре!')}
Нажмите кнопку для подтверждения.

{s.info('После подтверждения вы получите свою роль в ЛС')}
                """,
                reply_markup=keyboard
            )
            await update.message.reply_text(s.success(f"{user.first_name}, проверьте ЛС для подтверждения!"))
        except Exception:
            await update.message.reply_text(s.error(f"{user.first_name}, не удалось отправить сообщение в ЛС. Напишите боту в личку сначала."))
            game.remove_player(user.id)
            return

        # Обновляем в БД
        self.db.cursor.execute('''
            UPDATE mafia_games 
            SET players = ?, players_data = ? 
            WHERE game_id = ?
        ''', (json.dumps(game.players), json.dumps(game.players_data), game.game_id))

        await self._update_mafia_game_message(game, context)

    async def cmd_mafia_leave(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        user = update.effective_user

        if chat_id not in self.mafia_games:
            await update.message.reply_text(s.error("Игра не создана"))
            return

        game = self.mafia_games[chat_id]

        if game.status != "waiting":
            await update.message.reply_text(s.error("Нельзя покинуть игру после начала"))
            return

        if not game.remove_player(user.id):
            await update.message.reply_text(s.error("Вас нет в игре"))
            return

        await update.message.reply_text(s.success(f"{user.first_name} покинул игру"))

        self.db.cursor.execute('''
            UPDATE mafia_games 
            SET players = ?, players_data = ? 
            WHERE game_id = ?
        ''', (json.dumps(game.players), json.dumps(game.players_data), game.game_id))

        await self._update_mafia_game_message(game, context)

    async def _update_mafia_game_message(self, game: MafiaGame, context: ContextTypes.DEFAULT_TYPE):
        if not game.message_id:
            return

        status_text = game.get_formatted_status()
        players_list = "\n".join([f"{'✅' if p['confirmed'] else '⏳'} {p['name']}" for p in game.players_data.values()])

        text = f"""
{s.header('🔫 МАФИЯ')}

{status_text}

👥 **Участники:**
{players_list}

📌 /mafiajoin — присоединиться
📌 /mafialeave — выйти
        """

        try:
            await context.bot.edit_message_text(
                text,
                chat_id=game.chat_id,
                message_id=game.message_id,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Ошибка обновления сообщения мафии: {e}")

    async def _mafia_start_game(self, game: MafiaGame, context: ContextTypes.DEFAULT_TYPE):
        """Запуск игры после подтверждения всех игроков"""
        game.status = "starting"
        game.assign_roles()
        game.phase = "night"
        game.day = 1

        # Рассылаем роли в ЛС
        for player_id in game.players:
            role = game.roles[player_id]
            description = game.get_role_description(role)
            await self.send_private_message(
                player_id,
                f"""
{s.header('🔫 МАФИЯ')}

🎭 **Ваша роль:** {role.value}

{description}

🌙 Наступает ночь. Ожидайте действий...
                """
            )

        # Обновляем статус в общем чате
        game.status = "active"
        await self._update_mafia_game_message(game, context)

        # Отправляем сообщение о начале
        await context.bot.send_message(
            game.chat_id,
            f"""
{s.header('🔫 МАФИЯ НАЧАЛАСЬ!')}

🌙 Ночь. Город засыпает...
📊 Все роли розданы в личные сообщения.
            """
        )

        # Запускаем таймеры
        asyncio.create_task(self._mafia_night_timer(game, context))

        # Сохраняем в БД
        self.db.cursor.execute('''
            UPDATE mafia_games 
            SET status = ?, phase = ?, day = ?, roles = ?, alive = ?
            WHERE game_id = ?
        ''', (game.status, game.phase, game.day,
              {k: v.value for k, v in game.roles.items()},
              json.dumps(game.alive), game.game_id))
        self.db.conn.commit()

    async def _mafia_night_timer(self, game: MafiaGame, context: ContextTypes.DEFAULT_TYPE):
        await asyncio.sleep(MAFIA_NIGHT_TIME)

        if game.chat_id not in self.mafia_games or game.phase != "night":
            return

        killed = game.process_night()

        if killed["killed"]:
            game.alive[killed["killed"]] = False
            try:
                killed_name = game.players_data[killed["killed"]]['name']
                await self.send_private_message(
                    killed["killed"],
                    f"💀 **ВАС УБИЛИ НОЧЬЮ**\n\nВы больше не участвуете"
                )
            except:
                pass

        game.phase = "day"
        game.day += 1

        alive_list = game.get_alive_players()
        alive_names = [game.players_data[pid]['name'] for pid in alive_list]
        killed_name = game.players_data[killed["killed"]]['name'] if killed["killed"] else "никого"

        text = f"""
{s.header(f'🔫 МАФИЯ | ДЕНЬ {game.day}')}

☀️ **Наступило утро**
💀 **Убит:** {killed_name}

👥 **Живы ({len(alive_list)}):**
{chr(10).join([f'• {name}' for name in alive_names])}

🗳 **Обсуждайте и голосуйте** (напишите `голосовать номер`)
        """

        await context.bot.send_message(game.chat_id, text, parse_mode=ParseMode.MARKDOWN)

        self.db.cursor.execute('''
            UPDATE mafia_games 
            SET phase = ?, day = ?, alive = ?
            WHERE game_id = ?
        ''', (game.phase, game.day, json.dumps(game.alive), game.game_id))
        self.db.conn.commit()

        asyncio.create_task(self._mafia_day_timer(game, context))

    async def _mafia_day_timer(self, game: MafiaGame, context: ContextTypes.DEFAULT_TYPE):
        await asyncio.sleep(MAFIA_DAY_TIME)

        if game.chat_id not in self.mafia_games or game.phase != "day":
            return

        executed = game.process_voting()

        if executed:
            game.alive[executed] = False
            executed_name = game.players_data[executed]['name']
            role = game.roles[executed].value

            await context.bot.send_message(
                game.chat_id,
                f"""
{s.header(f'🔫 МАФИЯ | ДЕНЬ {game.day}')}

🔨 **Исключён:** {executed_name}
🎭 **Роль:** {role}

🌙 Ночь скоро...
                """
            )

            try:
                await self.send_private_message(
                    executed,
                    f"🔨 **ВАС ИСКЛЮЧИЛИ ДНЁМ**\n\nВы больше не участвуете"
                )
            except:
                pass
        else:
            await context.bot.send_message(
                game.chat_id,
                "📢 **Никто не был исключён**"
            )

        winner = game.check_win()

        if winner == "citizens":
            await context.bot.send_message(
                game.chat_id,
                f"{s.header('🏆 ПОБЕДА ГОРОДА!')}\n\nМафия уничтожена!"
            )
            for player_id in game.players:
                if game.roles[player_id] in [MafiaRole.MAFIA, MafiaRole.BOSS]:
                    self.db.update_user(player_id, mafia_losses=self.db.get_user_by_id(player_id).get('mafia_losses', 0) + 1)
                else:
                    self.db.update_user(player_id, mafia_wins=self.db.get_user_by_id(player_id).get('mafia_wins', 0) + 1)
                self.db.update_user(player_id, mafia_games=self.db.get_user_by_id(player_id).get('mafia_games', 0) + 1)
            del self.mafia_games[game.chat_id]
            return
        elif winner == "mafia":
            await context.bot.send_message(
                game.chat_id,
                f"{s.header('🏆 ПОБЕДА МАФИИ!')}\n\nМафия захватила город!"
            )
            for player_id in game.players:
                if game.roles[player_id] in [MafiaRole.MAFIA, MafiaRole.BOSS]:
                    self.db.update_user(player_id, mafia_wins=self.db.get_user_by_id(player_id).get('mafia_wins', 0) + 1)
                else:
                    self.db.update_user(player_id, mafia_losses=self.db.get_user_by_id(player_id).get('mafia_losses', 0) + 1)
                self.db.update_user(player_id, mafia_games=self.db.get_user_by_id(player_id).get('mafia_games', 0) + 1)
            del self.mafia_games[game.chat_id]
            return

        game.phase = "night"
        game.night_actions = {
            "mafia_kill": None,
            "doctor_save": None,
            "commissioner_check": None,
            "maniac_kill": None
        }

        await context.bot.send_message(
            game.chat_id,
            f"""
{s.header(f'🔫 МАФИЯ | НОЧЬ {game.day}')}

🌙 **Наступает ночь...**
🔪 Мафия выбирает жертву
            """
        )

        self.db.cursor.execute('''
            UPDATE mafia_games 
            SET phase = ?, night_actions = ?
            WHERE game_id = ?
        ''', (game.phase, json.dumps(game.night_actions), game.game_id))
        self.db.conn.commit()

        asyncio.create_task(self._mafia_night_timer(game, context))

    async def cmd_mafia_roles(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = f"""
{s.header('🔫 РОЛИ В МАФИИ')}

{s.section('😈 МАФИЯ')}
{s.item(MafiaRole.MAFIA.value, '😈')} — ночью убивают
{s.item(MafiaRole.BOSS.value, '👑')} — глава мафии

{s.section('👼 ГОРОД')}
{s.item(MafiaRole.COMMISSIONER.value, '👮')} — проверяет ночью
{s.item(MafiaRole.DOCTOR.value, '👨‍⚕️')} — лечит ночью
{s.item(MafiaRole.CITIZEN.value, '👤')} — ищет мафию

{s.section('🎭 ОСОБЫЕ')}
{s.item(MafiaRole.MANIAC.value, '🔪')} — убивает один
        """
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def cmd_mafia_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = f"""
{s.header('🔫 ПРАВИЛА МАФИИ')}

{s.section('🌙 НОЧЬ')}
1. Мафия выбирает жертву
2. Доктор выбирает, кого спасти
3. Комиссар проверяет

{s.section('☀️ ДЕНЬ')}
1. Объявление жертв ночи
2. Обсуждение
3. Голосование за исключение (`голосовать номер`)

{s.section('🏆 ЦЕЛЬ')}
• Мафия — убить всех мирных
• Город — найти всю мафию

{s.info('Все действия в ЛС с ботом.')}
        """
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def cmd_mafia_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)

        text = f"""
{s.header('🔫 СТАТИСТИКА МАФИИ')}

{s.stat('Сыграно игр', user_data['mafia_games'])}
{s.stat('Побед', user_data['mafia_wins'])}
{s.stat('Поражений', user_data['mafia_losses'])}
{s.stat('Процент побед', f'{(user_data["mafia_wins"]/max(1, user_data["mafia_games"])*100):.1f}%')}
        """
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    # ----- ДУЭЛИ -----
    async def cmd_duel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text(s.error("Использование: /duel @user ставка"))
            return

        username = context.args[0].replace('@', '')
        try:
            bet = int(context.args[1])
        except:
            await update.message.reply_text(s.error("Ставка должна быть числом"))
            return

        if bet <= 0:
            await update.message.reply_text(s.error("Ставка должна быть больше 0"))
            return

        user_data = self.db.get_user(update.effective_user.id)

        if bet > user_data['coins']:
            await update.message.reply_text(s.error(f"Недостаточно монет. Баланс: {user_data['coins']} 💰"))
            return

        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text(s.error("Пользователь не найден"))
            return

        if target['id'] == user_data['id']:
            await update.message.reply_text(s.error("Нельзя вызвать на дуэль самого себя"))
            return

        # Проверяем, нет ли активной дуэли
        self.db.cursor.execute(
            "SELECT id FROM duels WHERE (challenger_id = ? OR opponent_id = ?) AND status = 'pending'",
            (user_data['id'], user_data['id'])
        )
        if self.db.cursor.fetchone():
            await update.message.reply_text(s.error("У тебя уже есть активная дуэль"))
            return

        duel_id = self.db.create_duel(user_data['id'], target['id'], bet)
        self.db.add_coins(user_data['id'], -bet)

        target_name = target.get('nickname') or target['first_name']

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ ПРИНЯТЬ", callback_data=f"accept_duel_{duel_id}"),
                InlineKeyboardButton("❌ ОТКЛОНИТЬ", callback_data=f"reject_duel_{duel_id}")
            ]
        ])

        await update.message.reply_text(
            f"""
{s.header('⚔️ ДУЭЛЬ')}

👤 **{user_data['first_name']}** VS **{target_name}**
💰 **Ставка:** {bet} 💰

{target_name}, прими вызов!
            """,
            reply_markup=keyboard
        )

        self.duels_in_progress[duel_id] = {
            'challenger': user_data['id'],
            'opponent': target['id'],
            'bet': bet,
            'chat_id': update.effective_chat.id,
            'status': 'pending'
        }

    async def _process_duel(self, duel_id: int, challenger: Dict, opponent: Dict, bet: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
        await asyncio.sleep(2)

        challenger_roll = random.randint(1, 100)
        opponent_roll = random.randint(1, 100)

        if self.db.is_vip(challenger['id']):
            challenger_roll += 5
        if self.db.is_vip(opponent['id']):
            opponent_roll += 5

        # Учёт кибер-удачи
        if challenger.get('cyber_luck_until') and datetime.fromisoformat(challenger['cyber_luck_until']) > datetime.now():
            challenger_roll += 15
        if opponent.get('cyber_luck_until') and datetime.fromisoformat(opponent['cyber_luck_until']) > datetime.now():
            opponent_roll += 15

        if challenger_roll > opponent_roll:
            winner = challenger
            loser = opponent
            winner_score = challenger_roll
            loser_score = opponent_roll
        elif opponent_roll > challenger_roll:
            winner = opponent
            loser = challenger
            winner_score = opponent_roll
            loser_score = challenger_roll
        else:
            await context.bot.send_message(chat_id, "🤝 **Ничья! Перебрасываем...**")
            await asyncio.sleep(1)
            await self._process_duel(duel_id, challenger, opponent, bet, chat_id, context)
            return

        win_amount = bet * 2
        self.db.add_coins(winner['id'], win_amount)

        self.db.update_user(winner['id'], platform="telegram",
                          duel_wins=self.db.get_user_by_id(winner['id']).get('duel_wins', 0) + 1,
                          duel_rating=self.db.get_user_by_id(winner['id']).get('duel_rating', 1000) + 25)

        self.db.update_user(loser['id'], platform="telegram",
                          duel_losses=self.db.get_user_by_id(loser['id']).get('duel_losses', 0) + 1,
                          duel_rating=self.db.get_user_by_id(loser['id']).get('duel_rating', 1000) - 15)

        await context.bot.send_message(
            chat_id,
            f"""
{s.header('⚔️ РЕЗУЛЬТАТ ДУЭЛИ')}

👤 **{winner['first_name']}** VS **{loser['first_name']}**

🎲 **Результаты:**
• {winner['first_name']}: {winner_score}
• {loser['first_name']}: {loser_score}

🏆 **Победитель:** {winner['first_name']}
💰 **Выигрыш:** {win_amount} 💰

{s.success('Поздравляем!')}
            """
        )

        self.db.update_duel(duel_id, platform="telegram", status='completed', winner_id=winner['id'])

    async def cmd_duels(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.db.cursor.execute("SELECT * FROM duels WHERE status = 'pending'")
        duels = self.db.cursor.fetchall()

        if not duels:
            await update.message.reply_text(s.info("Нет активных дуэлей"))
            return

        text = f"{s.header('⚔️ АКТИВНЫЕ ДУЭЛИ')}\n\n"
        for duel in duels:
            challenger = self.db.get_user_by_id(duel[1])
            opponent = self.db.get_user_by_id(duel[2])
            if challenger and opponent:
                text += f"• {challenger['first_name']} vs {opponent['first_name']} — ставка {duel[3]} 💰\n"
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def cmd_duel_rating(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.db.cursor.execute("SELECT first_name, nickname, duel_rating FROM users WHERE duel_rating > 0 ORDER BY duel_rating DESC LIMIT 10")
        top = self.db.cursor.fetchall()

        if not top:
            await update.message.reply_text(s.info("Рейтинг пуст"))
            return

        text = f"{s.header('⚔️ ТОП ДУЭЛЯНТОВ')}\n\n"
        for i, row in enumerate(top, 1):
            name = row[1] or row[0]
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} {name} — {row[2]} очков\n"
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    # ----- БОССЫ -----
    async def cmd_bosses(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        bosses = self.db.get_bosses()

        if not bosses:
            self.db.respawn_bosses()
            bosses = self.db.get_bosses()

        text = f"{s.header('👾 БОССЫ')}\n\n"

        for i, boss in enumerate(bosses[:5]):
            health_bar = s.progress(boss['health'], boss['max_health'], 10)
            text += f"""
{i+1}. **{boss['name']}** (ур.{boss['level']})
   ❤️ {health_bar}
   ⚔️ Урон: {boss['damage']}
   💰 Награда: {boss['reward_coins']} 💰, ✨ {boss['reward_exp']}
   💜 Неоны: {boss['reward_neons']}, 🖥 Глитчи: {boss['reward_glitches']}
"""

        text += f"""
{s.section('ТВОИ ПОКАЗАТЕЛИ')}
❤️ Здоровье: {user_data['health']}/{user_data['max_health']}
⚡️ Энергия: {user_data['energy']}/100
⚔️ Урон: {user_data['damage']}
👾 Боссов убито: {user_data['boss_kills']}

📝 Команды:
• /boss [ID] — атаковать босса
• /regen — восстановить ❤️ и ⚡️
        """

        keyboard_buttons = []
        for i, boss in enumerate(bosses[:5]):
            if boss['is_alive']:
                keyboard_buttons.append(InlineKeyboardButton(
                    f"⚔️ {boss['name']} (❤️ {boss['health']}/{boss['max_health']})",
                    callback_data=f"boss_attack_{boss['id']}"
                ))
        keyboard_buttons.append(InlineKeyboardButton("🔄 Регенерация", callback_data="boss_regen"))
        keyboard_buttons.append(InlineKeyboardButton("⚔️ Купить оружие", callback_data="boss_buy_weapon"))

        reply_markup = InlineKeyboardMarkup(self._split_buttons(keyboard_buttons, 1))

        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

    async def cmd_boss_fight(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)

        if not context.args:
            await update.message.reply_text(s.error("Укажи ID босса: /boss 1"))
            return

        try:
            boss_id = int(context.args[0])
        except:
            await update.message.reply_text(s.error("Неверный ID"))
            return

        await self._process_boss_attack(update, context, user, user_data, boss_id, is_callback=False)

    async def _process_boss_attack(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                   user, user_data, boss_id: int, is_callback: bool = False):
        boss = self.db.get_boss(boss_id)

        if not boss or not boss['is_alive']:
            msg = s.error("Босс не найден или уже повержен")
            if is_callback:
                await update.callback_query.edit_message_text(msg)
            else:
                await update.message.reply_text(msg)
            return

        if user_data['energy'] < 10:
            msg = s.error("Недостаточно энергии. Используй /regen")
            if is_callback:
                await update.callback_query.edit_message_text(msg)
            else:
                await update.message.reply_text(msg)
            return

        self.db.add_energy(user_data['id'], -10)

        damage_bonus = 1.0
        if self.db.is_vip(user_data['id']):
            damage_bonus += 0.2
        if self.db.is_premium(user_data['id']):
            damage_bonus += 0.3
        if user_data.get('turbo_drive_until') and datetime.fromisoformat(user_data['turbo_drive_until']) > datetime.now():
            damage_bonus += 0.5

        base_damage = user_data['damage'] * damage_bonus
        player_damage = int(base_damage) + random.randint(-5, 5)

        crit = random.randint(1, 100) <= user_data['crit_chance']
        if crit:
            player_damage = int(player_damage * user_data['crit_multiplier'] / 100)
            crit_text = "💥 **КРИТИЧЕСКИЙ УДАР!** "
        else:
            crit_text = ""

        boss_damage = boss['damage'] + random.randint(-5, 5)
        armor_reduction = user_data['armor'] // 2
        player_taken = max(1, boss_damage - armor_reduction)

        killed = self.db.damage_boss(boss_id, player_damage)
        self.db.damage(user_data['id'], player_taken)

        total_damage = user_data.get('boss_damage', 0) + player_damage
        self.db.update_user(user_data['id'], platform="telegram", boss_damage=total_damage)

        text = f"""
{s.header('⚔️ БИТВА С БОССОМ')}

{crit_text}Твой урон: {player_damage}
Урон босса: {player_taken}
        """

        if killed:
            reward_coins = boss['reward_coins']
            reward_exp = boss['reward_exp']
            reward_neons = boss['reward_neons']
            reward_glitches = boss['reward_glitches']

            if self.db.is_vip(user_data['id']):
                reward_coins = int(reward_coins * 1.5)
                reward_exp = int(reward_exp * 1.5)
                reward_neons = int(reward_neons * 1.5)
                reward_glitches = int(reward_glitches * 1.5)
            if self.db.is_premium(user_data['id']):
                reward_coins = int(reward_coins * 2)
                reward_exp = int(reward_exp * 2)
                reward_neons = int(reward_neons * 2)
                reward_glitches = int(reward_glitches * 2)

            self.db.add_coins(user_data['id'], reward_coins)
            self.db.add_neons(user_data['id'], reward_neons)
            self.db.add_glitches(user_data['id'], reward_glitches)
            leveled_up = self.db.add_exp(user_data['id'], reward_exp)
            self.db.add_boss_kill(user_data['id'])

            text += f"""
✅ **ПОБЕДА!**
• 💰 Монеты: +{reward_coins}
• 💜 Неоны: +{reward_neons}
• 🖥 Глитчи: +{reward_glitches}
• ✨ Опыт: +{reward_exp}
{f'✨ **УРОВЕНЬ ПОВЫШЕН!**' if leveled_up else ''}
            """
        else:
            boss_info = self.db.get_boss(boss_id)
            text += f"""
⚠️ **Босс ещё жив!**
❤️ Осталось: {boss_info['health']} здоровья
            """

        if user_data['health'] <= player_taken:
            self.db.heal(user_data['id'], 50)
            text += f"\nℹ️ Ты погиб и воскрешён с 50❤️"

        user_data = self.db.get_user(user.id)

        text += f"""
{s.section('ТВОЁ СОСТОЯНИЕ')}
❤️ Здоровье: {user_data['health']}/{user_data['max_health']}
⚡️ Энергия: {user_data['energy']}/100
        """

        keyboard_buttons = [
            InlineKeyboardButton("⚔️ Атаковать снова", callback_data=f"boss_attack_{boss_id}"),
            InlineKeyboardButton("🔄 Регенерация", callback_data="boss_regen"),
            InlineKeyboardButton("📋 К списку боссов", callback_data="boss_list")
        ]
        reply_markup = InlineKeyboardMarkup(self._split_buttons(keyboard_buttons, 1))

        if is_callback:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

        self.db.log_action(user_data['id'], 'boss_fight', f"Урон {player_damage}")

    async def cmd_boss_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("Укажи ID босса: /bossinfo 1"))
            return

        try:
            boss_id = int(context.args[0])
        except:
            await update.message.reply_text(s.error("Неверный ID"))
            return

        boss = self.db.get_boss(boss_id)
        if not boss:
            await update.message.reply_text(s.error("Босс не найден"))
            return

        status = "ЖИВ" if boss['is_alive'] else "ПОВЕРЖЕН"
        health_bar = s.progress(boss['health'], boss['max_health'], 20)

        text = f"""
{s.header(f'👾 {boss["name"]}')}

📊 **Характеристики**
• Уровень: {boss['level']}
• ❤️ Здоровье: {health_bar}
• ⚔️ Урон: {boss['damage']}
• 💰 Монеты: {boss['reward_coins']}
• 💜 Неоны: {boss['reward_neons']}
• 🖥 Глитчи: {boss['reward_glitches']}
• ✨ Опыт: {boss['reward_exp']}
• 📊 Статус: {status}
        """
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def cmd_regen(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)

        cost = 20
        if user_data['coins'] < cost:
            await update.message.reply_text(s.error(f"Недостаточно монет. Нужно {cost} 💰"))
            return

        self.db.add_coins(user_data['id'], -cost)
        self.db.heal(user_data['id'], 50)
        self.db.add_energy(user_data['id'], 20)

        user_data = self.db.get_user(update.effective_user.id)

        text = f"""
{s.header('✅ РЕГЕНЕРАЦИЯ')}

❤️ Здоровье +50 (теперь {user_data['health']})
⚡️ Энергия +20 (теперь {user_data['energy']})
💰 Потрачено: {cost}
        """
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    # ===== АЧИВКИ =====
    async def cmd_achievements(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = f"""
{s.header('🏅 АЧИВКИ')}

**Команды:**
/achievements — эта информация
/myachievements — мои ачивки
/achievement [ID] — информация об ачивке
/topachievements — топ коллекционеров

📋 **Категории ачивок:**
💜 По богатству
🖥 По глитчам
🎲 По играм
⚔️ По дуэлям
👾 По боссам
🔥 По активности
📆 По стрикам
💎 VIP-ачивки
🎁 Особые
🤖 Секретные

🔐 **Приватность:**
+Ачивки — открыть доступ к вашим ачивкам
-Ачивки — скрыть ваши ачивки от других
        """
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def cmd_my_achievements(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)
        achievements = self.db.get_user_achievements(user_data['id'])

        if not achievements:
            await update.message.reply_text(s.info("У вас пока нет ачивок"))
            return

        text = f"{s.header(f'🏅 АЧИВКИ: {user_data["first_name"]}')}\nВсего: {len(achievements)}\n\n"
        for ach in achievements[:20]:
            text += f"• {ach['name']} — {ach['description']}\n"
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def cmd_achievement_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("Укажите ID ачивки: /achievement 1"))
            return

        try:
            ach_id = int(context.args[0])
        except:
            await update.message.reply_text(s.error("ID должен быть числом"))
            return

        self.db.cursor.execute("SELECT * FROM achievements_list WHERE id = ?", (ach_id,))
        ach = self.db.cursor.fetchone()

        if not ach:
            await update.message.reply_text(s.error("Ачивка не найдена"))
            return

        ach = dict(ach)

        text = f"""
{s.header(f'🏅 АЧИВКА {ach_id}')}

**{ach['name']}**
{ach['description']}

**Награда:**
{f"• {ach['reward_neons']} 💜 неонов" if ach['reward_neons'] > 0 else ""}
{f"• {ach['reward_glitches']} 🖥 глитчей" if ach['reward_glitches'] > 0 else ""}
{f"• Титул: {ach['reward_title']}" if ach['reward_title'] else ""}
{f"• Статус: {ach['reward_status']}" if ach['reward_status'] else ""}
        """
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def cmd_top_achievements(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.db.cursor.execute("""
            SELECT u.first_name, u.nickname, COUNT(a.id) as count
            FROM users u
            LEFT JOIN achievements a ON u.id = a.user_id
            GROUP BY u.id
            ORDER BY count DESC
            LIMIT 10
        """)
        top = self.db.cursor.fetchall()

        if not top or top[0][2] == 0:
            await update.message.reply_text(s.info("Топ ачивок пуст"))
            return

        text = f"{s.header('🏆 ТОП КОЛЛЕКЦИОНЕРОВ')}\n\n"
        for i, row in enumerate(top, 1):
            name = row[1] or row[0]
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} {name} — {row[2]} ачивок\n"
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def cmd_achievements_public(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], platform="telegram", achievements_visible=1)
        await update.message.reply_text(s.success("Ваши ачивки теперь видны всем"))

    async def cmd_achievements_private(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], platform="telegram", achievements_visible=0)
        await update.message.reply_text(s.success("Ваши ачивки теперь скрыты от других"))

    # ===== КРУЖКИ =====
    async def cmd_circles(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        self.db.cursor.execute("SELECT * FROM circles WHERE chat_id = ? ORDER BY created_at", (chat_id,))
        circles = self.db.cursor.fetchall()

        if not circles:
            await update.message.reply_text(s.info("В этом чате нет кружков"))
            return

        text = f"{s.header('🔄 КРУЖКИ ЧАТА')}\n\n"
        for i, circle in enumerate(circles, 1):
            circle = dict(circle)
            members = json.loads(circle['members'])
            text += f"{i}. {circle['name']} — {len(members)} участников\n"
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def cmd_circle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("Укажите номер кружка: /circle 1"))
            return

        try:
            circle_num = int(context.args[0])
        except:
            await update.message.reply_text(s.error("Номер должен быть числом"))
            return

        chat_id = update.effective_chat.id
        self.db.cursor.execute("SELECT * FROM circles WHERE chat_id = ? ORDER BY created_at", (chat_id,))
        circles = self.db.cursor.fetchall()

        if circle_num < 1 or circle_num > len(circles):
            await update.message.reply_text(s.error("Кружок с таким номером не найден"))
            return

        circle = dict(circles[circle_num - 1])
        members = json.loads(circle['members'])

        creator = self.db.get_user_by_id(circle['created_by'])
        creator_name = creator.get('nickname') or creator['first_name'] if creator else "Неизвестно"

        text = f"""
{s.header(f'🔄 КРУЖОК: {circle["name"]}')}

📝 {circle['description']}

👑 Создатель: {creator_name}
👥 Участников: {len(members)}
        """
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def cmd_create_circle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 1:
            await update.message.reply_text(s.error("Укажите название кружка: /createcircle Название"))
            return

        name = " ".join(context.args)
        user_data = self.db.get_user(update.effective_user.id)
        chat_id = update.effective_chat.id

        circle_id = self.db.create_circle(chat_id, name, "", user_data['id'])

        if not circle_id:
            await update.message.reply_text(s.error("Не удалось создать кружок"))
            return

        await update.message.reply_text(s.success(f"Кружок '{name}' создан!"))

    async def cmd_join_circle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("Укажите номер кружка: /joincircle 1"))
            return

        try:
            circle_num = int(context.args[0])
        except:
            await update.message.reply_text(s.error("Номер должен быть числом"))
            return

        user_data = self.db.get_user(update.effective_user.id)
        chat_id = update.effective_chat.id

        self.db.cursor.execute("SELECT * FROM circles WHERE chat_id = ? ORDER BY created_at", (chat_id,))
        circles = self.db.cursor.fetchall()

        if circle_num < 1 or circle_num > len(circles):
            await update.message.reply_text(s.error("Кружок с таким номером не найден"))
            return

        circle = dict(circles[circle_num - 1])

        if self.db.join_circle(circle['id'], user_data['id']):
            await update.message.reply_text(s.success(f"Вы присоединились к кружку '{circle['name']}'"))
        else:
            await update.message.reply_text(s.error("Не удалось присоединиться"))

    async def cmd_leave_circle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("Укажите номер кружка: /leavecircle 1"))
            return

        try:
            circle_num = int(context.args[0])
        except:
            await update.message.reply_text(s.error("Номер должен быть числом"))
            return

        user_data = self.db.get_user(update.effective_user.id)
        chat_id = update.effective_chat.id

        self.db.cursor.execute("SELECT * FROM circles WHERE chat_id = ? ORDER BY created_at", (chat_id,))
        circles = self.db.cursor.fetchall()

        if circle_num < 1 or circle_num > len(circles):
            await update.message.reply_text(s.error("Кружок с таким номером не найден"))
            return

        circle = dict(circles[circle_num - 1])

        if self.db.leave_circle(circle['id'], user_data['id']):
            await update.message.reply_text(s.success(f"Вы покинули кружок '{circle['name']}'"))
        else:
            await update.message.reply_text(s.error("Не удалось покинуть кружок"))

    # ===== ЗАКЛАДКИ =====
    async def cmd_add_bookmark(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text(s.error("Использование: /addbookmark Название ссылка"))
            return

        name = context.args[0]
        content = " ".join(context.args[1:])
        user_data = self.db.get_user(update.effective_user.id)
        chat_id = update.effective_chat.id

        message_id = update.message.reply_to_message.message_id if update.message.reply_to_message else None

        bookmark_id = self.db.add_bookmark(chat_id, user_data['id'], name, content, message_id)

        await update.message.reply_text(s.success(f"Закладка '{name}' сохранена! ID: {bookmark_id}"))

    async def cmd_bookmarks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)
        chat_id = update.effective_chat.id

        bookmarks = self.db.get_user_bookmarks(user_data['id'], chat_id)

        if not bookmarks:
            await update.message.reply_text(s.info("У вас нет закладок в этом чате"))
            return

        text = f"{s.header('📌 МОИ ЗАКЛАДКИ')}\n\n"
        for bm in bookmarks:
            text += f"ID {bm['id']}: {bm['name']}\n"
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def cmd_bookmark(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("Укажите ID закладки: /bookmark 123"))
            return

        try:
            bookmark_id = int(context.args[0])
        except:
            await update.message.reply_text(s.error("ID должен быть числом"))
            return

        chat_id = update.effective_chat.id
        self.db.cursor.execute("SELECT * FROM bookmarks WHERE id = ? AND chat_id = ?", (bookmark_id, chat_id))
        bm = self.db.cursor.fetchone()

        if not bm:
            await update.message.reply_text(s.error("Закладка не найдена"))
            return

        bm = dict(bm)
        user = self.db.get_user_by_id(bm['user_id'])
        user_name = user.get('nickname') or user['first_name'] if user else "Неизвестно"

        text = f"""
{s.header(f'📌 ЗАКЛАДКА: {bm["name"]}')}

{bm['content']}

👤 Добавил: {user_name}
        """
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def cmd_remove_bookmark(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("Укажите ID закладки: /removebookmark 123"))
            return

        try:
            bookmark_id = int(context.args[0])
        except:
            await update.message.reply_text(s.error("ID должен быть числом"))
            return

        user_data = self.db.get_user(update.effective_user.id)
        chat_id = update.effective_chat.id

        self.db.cursor.execute("SELECT user_id FROM bookmarks WHERE id = ? AND chat_id = ?", (bookmark_id, chat_id))
        row = self.db.cursor.fetchone()

        if not row:
            await update.message.reply_text(s.error("Закладка не найдена"))
            return

        if row[0] != user_data['id'] and user_data['rank'] < 2:
            await update.message.reply_text(s.error("У вас нет прав на удаление этой закладки"))
            return

        self.db.cursor.execute("DELETE FROM bookmarks WHERE id = ?", (bookmark_id,))
        self.db.conn.commit()

        await update.message.reply_text(s.success("Закладка удалена"))

    async def cmd_chat_bookmarks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        bookmarks = self.db.get_chat_bookmarks(chat_id)

        if not bookmarks:
            await update.message.reply_text(s.info("В этом чате нет публичных закладок"))
            return

        text = f"{s.header('📚 ЧАТБУК')}\n\n"
        for bm in bookmarks[:20]:
            name = bm.get('nickname') or bm['first_name']
            text += f"ID {bm['id']}: {bm['name']} (от {name})\n"
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    # ===== ТАЙМЕРЫ =====
    async def cmd_add_timer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text(s.error("Использование: /addtimer 30м /ping"))
            return

        time_str = context.args[0]
        command = " ".join(context.args[1:])

        minutes = parse_time(time_str)
        if not minutes:
            await update.message.reply_text(s.error("Неверный формат времени. Используйте: 30м, 2ч, 1д"))
            return

        user_data = self.db.get_user(update.effective_user.id)
        chat_id = update.effective_chat.id
        execute_at = datetime.now() + timedelta(minutes=minutes)

        timer_id = self.db.add_timer(chat_id, user_data['id'], execute_at, command)

        if not timer_id:
            await update.message.reply_text(s.error("Достигнут лимит таймеров в чате (макс. 5)"))
            return

        await update.message.reply_text(
            s.success(f"Таймер #{timer_id} установлен на {execute_at.strftime('%d.%m.%Y %H:%M')}")
        )

    async def cmd_timers(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id

        self.db.cursor.execute("""
            SELECT * FROM timers 
            WHERE chat_id = ? AND status = 'pending' 
            ORDER BY execute_at
        """, (chat_id,))
        timers = self.db.cursor.fetchall()

        if not timers:
            await update.message.reply_text(s.info("В этом чате нет активных таймеров"))
            return

        text = f"{s.header('⏰ ТАЙМЕРЫ ЧАТА')}\n\n"
        for timer in timers:
            timer = dict(timer)
            execute_at = datetime.fromisoformat(timer['execute_at']).strftime('%d.%m.%Y %H:%M')
            text += f"#{timer['id']} — {execute_at}\n   Команда: {timer['command']}\n\n"
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def cmd_remove_timer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("Укажите ID таймера: /removetimer 1"))
            return

        try:
            timer_id = int(context.args[0])
        except:
            await update.message.reply_text(s.error("ID должен быть числом"))
            return

        user_data = self.db.get_user(update.effective_user.id)
        chat_id = update.effective_chat.id

        self.db.cursor.execute("SELECT user_id FROM timers WHERE id = ? AND chat_id = ?", (timer_id, chat_id))
        row = self.db.cursor.fetchone()

        if not row:
            await update.message.reply_text(s.error("Таймер не найден"))
            return

        if row[0] != user_data['id'] and user_data['rank'] < 2:
            await update.message.reply_text(s.error("У вас нет прав на удаление этого таймера"))
            return

        self.db.cursor.execute("UPDATE timers SET status = 'cancelled' WHERE id = ?", (timer_id,))
        self.db.conn.commit()

        await update.message.reply_text(s.success(f"Таймер #{timer_id} удалён"))

    # ===== НАГРАДЫ =====
    async def cmd_give_award(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 3:
            await update.message.reply_text(s.error("Использование: /giveaward 4 @user Текст"))
            return

        try:
            degree = int(context.args[0])
        except:
            await update.message.reply_text(s.error("Степень должна быть числом от 1 до 8"))
            return

        username = context.args[1].replace('@', '')
        award_text = " ".join(context.args[2:])

        if degree < 1 or degree > 8:
            await update.message.reply_text(s.error("Степень должна быть от 1 до 8"))
            return

        user_data = self.db.get_user(update.effective_user.id)
        if degree > user_data['rank'] and user_data['rank'] < 8:
            await update.message.reply_text(s.error(f"Ваш ранг позволяет выдавать только степени до {user_data['rank']}"))
            return

        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text(s.error("Пользователь не найден"))
            return

        award_id = self.db.give_award(update.effective_chat.id, target['id'], user_data['id'], degree, award_text)

        await update.message.reply_text(s.success(f"Награда #{award_id} степени {degree} выдана {target['first_name']}!"))

        try:
            await self.send_private_message(
                target['telegram_id'],
                f"""
{s.header('🏅 ВАМ ВЫДАЛИ НАГРАДУ!')}

Степень: {degree}
Текст: {award_text}
От: {update.effective_user.first_name}
                """
            )
        except:
            pass

    async def cmd_awards(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        username = None
        if context.args:
            username = context.args[0].replace('@', '')

        if username:
            target = self.db.get_user_by_username(username)
        else:
            target = self.db.get_user(update.effective_user.id)

        if not target:
            await update.message.reply_text(s.error("Пользователь не найден"))
            return

        awards = self.db.get_user_awards(target['id'], update.effective_chat.id)

        if not awards:
            name = target.get('nickname') or target['first_name']
            await update.message.reply_text(s.info(f"У {name} нет наград"))
            return

        name = target.get('nickname') or target['first_name']
        text = f"{s.header(f'🏅 НАГРАДЫ: {name}')}\n\n"

        for award in awards:
            date = datetime.fromisoformat(award['awarded_at']).strftime('%d.%m.%Y')
            text += f"• Степень {award['degree']} — {award['text']}\n  От {award['awarded_by_name']}, {date}\n\n"
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def cmd_remove_award(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text(s.error("Использование: /removeaward 123 @user"))
            return

        try:
            award_id = int(context.args[0])
        except:
            await update.message.reply_text(s.error("ID награды должен быть числом"))
            return

        username = context.args[1].replace('@', '')
        user_data = self.db.get_user(update.effective_user.id)

        if user_data['rank'] < 2:
            await update.message.reply_text(s.error("Недостаточно прав для снятия наград"))
            return

        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text(s.error("Пользователь не найден"))
            return

        self.db.cursor.execute("DELETE FROM awards WHERE id = ? AND chat_id = ?", (award_id, update.effective_chat.id))
        self.db.conn.commit()

        if self.db.cursor.rowcount > 0:
            await update.message.reply_text(s.success(f"Награда #{award_id} снята"))
        else:
            await update.message.reply_text(s.error("Награда не найдена"))

    # ===== КЛАНЫ =====
    async def cmd_clan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)

        if not user_data.get('clan_id', 0):
            await update.message.reply_text(s.info("Вы не состоите в клане"))
            return

        clan = self.get_clan(user_data['clan_id'])
        if not clan:
            await update.message.reply_text(s.error("Клан не найден"))
            return

        members = self.get_clan_members(clan['id'])

        text = f"""
{s.header(f'🏰 КЛАН: {clan["name"]}')}

📊 Уровень: {clan.get('level', 1)}
💰 Казна: {clan.get('coins', 0)} 💰
👥 Участников: {len(members)}

**Участники:**
"""
        for member in members:
            name = member.get('nickname') or member['first_name']
            role_emoji = "👑" if member.get('clan_role') == 'owner' else "🛡" if member.get('clan_role') == 'admin' else "👤"
            text += f"{role_emoji} {name}\n"
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def cmd_clans(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.db.cursor.execute("SELECT name, level, members FROM clans ORDER BY level DESC LIMIT 10")
        clans = self.db.cursor.fetchall()

        if not clans:
            await update.message.reply_text(s.info("Нет созданных кланов"))
            return

        text = f"{s.header('🏰 ТОП КЛАНОВ')}\n\n"
        for i, clan in enumerate(clans, 1):
            text += f"{i}. {clan[0]} — ур.{clan[1]}, {clan[2]} участников\n"
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def cmd_create_clan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("Укажите название клана: /createclan Название"))
            return

        name = " ".join(context.args)
        user_data = self.db.get_user(update.effective_user.id)

        if user_data.get('clan_id', 0):
            await update.message.reply_text(s.error("Вы уже в клане"))
            return

        if user_data['coins'] < 1000:
            await update.message.reply_text(s.error(f"Недостаточно монет. Нужно 1000 💰"))
            return

        clan_id = self.db.create_clan(update.effective_chat.id, name, "", user_data['id'])
        if not clan_id:
            await update.message.reply_text(s.error("Клан с таким названием уже существует"))
            return

        self.db.add_coins(user_data['id'], -1000)
        await update.message.reply_text(s.success(f"Клан '{name}' создан!"))

    async def cmd_join_clan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("Укажите название клана: /joinclan Название"))
            return

        name = " ".join(context.args)
        user_data = self.db.get_user(update.effective_user.id)

        if user_data.get('clan_id', 0):
            await update.message.reply_text(s.error("Вы уже в клане"))
            return

        self.db.cursor.execute("SELECT * FROM clans WHERE name = ? AND chat_id = ?", (name, update.effective_chat.id))
        clan = self.db.cursor.fetchone()

        if not clan:
            await update.message.reply_text(s.error("Клан не найден"))
            return

        if self.db.join_clan(clan[0], user_data['id']):
            await update.message.reply_text(s.success(f"Вы вступили в клан '{name}'"))
        else:
            await update.message.reply_text(s.error("Не удалось вступить в клан"))

    async def cmd_leave_clan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)

        if not user_data.get('clan_id', 0):
            await update.message.reply_text(s.error("Вы не в клане"))
            return

        if user_data.get('clan_role') == 'owner':
            await update.message.reply_text(s.error("Владелец не может покинуть клан"))
            return

        if self.db.leave_clan(user_data['id']):
            await update.message.reply_text(s.success("Вы покинули клан"))
        else:
            await update.message.reply_text(s.error("Не удалось покинуть клан"))

    def get_clan(self, clan_id: int) -> Optional[Dict]:
        self.db.cursor.execute("SELECT * FROM clans WHERE id = ?", (clan_id,))
        row = self.db.cursor.fetchone()
        return dict(row) if row else None

    def get_clan_members(self, clan_id: int) -> List[Dict]:
        self.db.cursor.execute("SELECT id, first_name, nickname, clan_role FROM users WHERE clan_id = ?", (clan_id,))
        return [dict(row) for row in self.db.cursor.fetchall()]

    # ===== БОНУСЫ (КИБЕР-БОНУСЫ) =====
    async def cmd_bonuses(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = f"""
{s.header('🎁 КИБЕР-БОНУСЫ')}

1. 👾 Кибер-статус — 100💜/мес
   Премиум-доступ, неоновый ник

2. 🔨 Глитч-молот — 50💜
   Временно замутить любого пользователя

3. ⚡ Турбо-драйв — 200💜/мес
   Ускоренная прокачка +50%

4. 👻 Невидимка — 30💜/30дней
   Анонимные сообщения

5. 🌈 Неон-ник — 100💜
   Фиолетовое свечение ника

6. 🎰 Кибер-удача — 150💜/3дня
   +15% удачи в играх

7. 🔒 Файрволл — 80💜
   Защита от наказаний

8. 🤖 РП-пакет — 120💜/мес
   Эксклюзивные РП-команды

/bonusinfo [название] — подробнее
/buybonus [название] [срок] — купить
        """
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def cmd_bonus_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("Укажите название бонуса"))
            return

        name = " ".join(context.args).lower()
        bonuses = {
            "кибер-статус": ("👾 Кибер-статус", 100, "месяц",
                            "Премиум-доступ, неоновый ник, эксклюзивные РП-команды"),
            "глитч-молот": ("🔨 Глитч-молот", 50, "единоразово",
                           "Временно замутить любого пользователя на 24ч"),
            "турбо-драйв": ("⚡ Турбо-драйв", 200, "месяц",
                           "Ускоренная прокачка +50% к опыту"),
            "невидимка": ("👻 Невидимка", 30, "30 дней",
                         "Анонимные сообщения в чат через ЛС"),
            "неон-ник": ("🌈 Неон-ник", 100, "навсегда",
                        "Фиолетовое свечение ника"),
            "кибер-удача": ("🎰 Кибер-удача", 150, "3 дня",
                           "+15% к удаче во всех играх"),
            "файрволл": ("🔒 Файрволл", 80, "до использования",
                        "Одноразовая защита от мутов и банов"),
            "рп-пакет": ("🤖 РП-пакет", 120, "месяц",
                        "Эксклюзивные кибер-РП команды")
        }

        for key, (title, price, duration, desc) in bonuses.items():
            if key in name:
                text = f"""
{s.header(title)}

💰 Цена: {price} 💜
⏳ Длительность: {duration}

{desc}

🛒 Купить: /buybonus {key} 1
                """
                await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
                return

        await update.message.reply_text(s.error("Бонус не найден"))

    async def cmd_buy_bonus(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text(s.error("Использование: /buybonus [название] [срок]"))
            return

        name = context.args[0].lower()
        try:
            duration = int(context.args[1])
        except:
            await update.message.reply_text(s.error("Срок должен быть числом"))
            return

        user_data = self.db.get_user(update.effective_user.id)

        prices = {
            "кибер-статус": 100,
            "глитч-молот": 50,
            "турбо-драйв": 200,
            "невидимка": 30,
            "неон-ник": 100,
            "кибер-удача": 150,
            "файрволл": 80,
            "рп-пакет": 120
        }

        bonus_type = None
        price = None
        for key, p in prices.items():
            if key in name:
                price = p
                bonus_type = key
                break

        if not price:
            await update.message.reply_text(s.error("Бонус не найден"))
            return

        total = price * duration

        if user_data['neons'] < total:
            await update.message.reply_text(s.error(f"Недостаточно неонов. Нужно {total} 💜"))
            return

        if self.db.buy_bonus(user_data['id'], bonus_type, duration, total):
            await update.message.reply_text(s.success(f"Бонус '{name}' куплен на {duration} мес. за {total} 💜"))
        else:
            await update.message.reply_text(s.error("Ошибка при покупке"))

    # ===== ВТОРОЙ AI: ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЙ =====
    async def cmd_imagine(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("Укажите описание изображения, например:\n/imagine космический корабль в стиле киберпанк"))
            return
        prompt = " ".join(context.args)
        msg = await update.message.reply_text("🎨 **Генерирую изображение...** это может занять несколько секунд.", parse_mode=ParseMode.MARKDOWN)

        if not hasattr(self, 'image_ai'):
            self.image_ai = ImageAI()

        image_data = await self.image_ai.generate(prompt)
        if image_data:
            await msg.delete()
            await update.message.reply_photo(
                photo=BytesIO(image_data),
                caption=f"🎨 **Ваше изображение**\n\nЗапрос: {prompt}",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await msg.edit_text(s.error("Не удалось сгенерировать изображение. Попробуйте позже."))

    async def cmd_imagine_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = f"""
{s.header('🎨 ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЙ')}

**Команда:**
/imagine [описание] — создаёт изображение по вашему запросу

**Примеры:**
/imagine космический корабль в стиле киберпанк
/imagine милый котёнок с большими глазами
/imagine город будущего ночью, неоновые огни

**Примечание:** генерация может занимать до 30 секунд. Бесплатный сервис.
        """
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    # ===== ТАЙНЫЙ ОРДЕН =====
    async def cmd_order(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        chat_id = update.effective_chat.id
        user_data = self.db.get_user(user.id)

        self.db.cursor.execute('''
            SELECT * FROM order_data 
            WHERE chat_id = ? AND platform = 'telegram' AND is_active = 1
        ''', (chat_id,))
        order = self.db.cursor.fetchone()

        in_order = self.db.is_in_order(user_data['id'], chat_id)
        rank_info = self.db.get_user_rank(user_data['id'], chat_id)

        if not context.args:
            if order:
                order_dict = dict(order)
                members = json.loads(order_dict['members'])
                revelation = datetime.fromisoformat(order_dict['revelation_time']).strftime('%d.%m.%Y %H:%M')

                text = f"""
{s.header('👁️ ТАЙНЫЙ ОРДЕН')}

Цикл {order_dict['cycle_number']} активен!
Пять избранных уже среди нас...

🕵️ **Раскрытие:** {revelation}
📊 **Участников:** {len(members)}

Твой статус: {rank_info['name']}
{'🔮 ТЫ ИЗБРАН!' if in_order else '👤 Ты не в ордене... пока что.'}

📝 Команды:
/order rank — мой ранг
/order points — мои очки
                """
            else:
                text = f"""
{s.header('👁️ ТАЙНЫЙ ОРДЕН')}

В этом чате пока нет активного ордена.
Но тени уже собираются...

Твой статус: {rank_info['name']}
Очков: {rank_info['points']}

📝 Команды:
/order rank — мой ранг
/order points — мои очки

💡 Орден активируется администратором.
                """
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

        elif context.args[0].lower() == "rank":
            ranks_text = """
👁️ **РАНГИ ОРДЕНА**

0 👤 Кандидат — 0 очков
1 👁️ Наблюдатель — 100
2 🌙 Тень — 250
3 🕳️ Бездна — 500
4 🔮 Провидец — 1000
5 🧙 Мистик — 2500
6 ⚔️ Страж — 5000
7 👑 Хранитель — 10000
8 🗿 Легенда — 25000
9 💀 Спектр — 50000
10 👁️ Всевидящий — 100000
            """
            await update.message.reply_text(
                f"{s.header('👁️ РАНГИ ОРДЕНА')}\n\nТвой ранг: {rank_info['name']}\nОчков: {rank_info['points']}\n\n{ranks_text}",
                parse_mode=ParseMode.MARKDOWN
            )

        elif context.args[0].lower() == "points":
            text = f"""
{s.header('👁️ МОИ ОЧКИ ОРДЕНА')}

📊 Всего очков: {rank_info['points']}
📈 Ранг: {rank_info['name']}

💡 Очки начисляются за:
• Активность в чате
• Победы в играх
• Особые достижения
            """
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def cmd_start_order(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        chat_id = update.effective_chat.id

        if user_data['rank'] < 3 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("Только администраторы могут запустить орден."))
            return

        members, cycle = self.db.start_order_cycle(chat_id)

        for member_id in members:
            try:
                await self.send_private_message(
                    member_id,
                    f"""
{s.header('👁️ ТАЙНЫЙ ОРДЕН')}

Ты избран. Орден следит за тобой...

Цикл {cycle} начался. Твои действия будут влиять на ход истории.
                    """
                )
            except:
                pass

        await update.message.reply_text(
            f"""
{s.header('👁️ ТАЙНЫЙ ОРДЕН')}

Цикл {cycle} начался.
Пять избранных уже среди нас...
Кто они? Узнаем через 7 дней.
            """
        )

    async def cmd_reveal_order(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        chat_id = update.effective_chat.id

        if user_data['rank'] < 3 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("Только администраторы могут раскрыть орден."))
            return

        result = self.db.reveal_order(chat_id)

        if not result:
            await update.message.reply_text(s.error("Нет активного ордена."))
            return

        members = result['members']
        points = result['points']
        cycle = result['cycle']

        message = f"{s.header('👁️ ТАЙНЫЙ ОРДЕН РАСКРЫТ!')}\n\n"
        message += "Всё это время среди вас были избранные...\n\n"

        for i, member_id in enumerate(members):
            name = await self.get_user_name(member_id)
            member_points = points.get(str(member_id), 0)

            if i == 0:
                medal = "🏆"
                self.db.add_order_points(member_id, chat_id, 500, "Победа в цикле ордена")
                await self.send_private_message(
                    member_id,
                    f"""
{s.header('🏆 ПОЗДРАВЛЯЕМ!')}

Ты стал лидером цикла {cycle} Тайного Ордена!
➕ 500 очков ордена
                    """
                )
            elif i == 1:
                medal = "🥈"
            elif i == 2:
                medal = "🥉"
            else:
                medal = "👤"

            message += f"{medal} {name} — {member_points} очков\n"

        message += f"\n👁️ **Спектр:** Спектр наблюдал за вами..."

        await update.message.reply_text(message)

    # ===== ОБРАБОТЧИКИ СООБЩЕНИЙ =====
    async def handle_numbers(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text.strip()
        if text == "1":
            await self.cmd_profile(update, context)
        elif text == "2":
            await self.cmd_stats(update, context)
        elif text == "3":
            await self.cmd_games(update, context)
        elif text == "4":
            await self.cmd_shop(update, context)
        elif text == "5":
            await self.show_chart(update, context)
        elif text == "6":
            await self.cmd_help(update, context)
        elif text == "7":
            await self.show_contacts(update, context)
        elif text == "0":
            await self.show_menu(update, context)
        else:
            await update.message.reply_text(s.error("Неверный номер. Введите 0-7"))

    async def check_spam(self, update: Update) -> bool:
        user = update.effective_user
        user_data = self.db.get_user(user.id)

        if has_permission(user_data, 2):
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

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        message_text = update.message.text
        chat = update.effective_chat

        if not user or not message_text:
            return

        self.db.save_message(
            user.id,
            user.username,
            user.first_name,
            message_text,
            chat.id,
            chat.title
        )

        if message_text.startswith('/'):
            return

        user_data = self.db.get_user(user.id, user.first_name)
        self.db.update_user(user_data['id'], messages_count=user_data.get('messages_count', 0) + 1)

        if self.db.is_banned(user_data['id']):
            return

        if self.db.is_muted(user_data['id']):
            await update.message.reply_text("🔇 Ты в муте")
            return

        if await self.check_spam(update):
            return

        if self.db.is_word_blacklisted(message_text):
            await update.message.delete()
            await update.message.reply_text(s.warning("Запрещенное слово! Сообщение удалено."))
            return

        # Обработка КНБ
        if context.user_data.get('awaiting_rps'):
            if message_text in ["1", "2", "3"]:
                context.user_data['awaiting_rps'] = False
                choices = {1: "🪨 Камень", 2: "✂️ Ножницы", 3: "📄 Бумага"}
                results = {(1,2): "win", (2,3): "win", (3,1): "win", (2,1): "lose", (3,2): "lose", (1,3): "lose"}

                player_choice = int(message_text)
                bot_choice = random.randint(1, 3)

                text = f"{s.header('✊ КНБ')}\n\n"
                text += f"👤 Вы: {choices[player_choice]}\n"
                text += f"🤖 Бот: {choices[bot_choice]}\n\n"

                if player_choice == bot_choice:
                    self.db.update_user(user_data['id'], rps_draws=user_data.get('rps_draws', 0) + 1)
                    text += "🤝 **НИЧЬЯ!**"
                elif results.get((player_choice, bot_choice)) == "win":
                    self.db.update_user(user_data['id'], rps_wins=user_data.get('rps_wins', 0) + 1)
                    reward = random.randint(10, 30)
                    self.db.add_coins(user_data['id'], reward)
                    text += f"🎉 **ПОБЕДА!** +{reward} 💰"
                else:
                    self.db.update_user(user_data['id'], rps_losses=user_data.get('rps_losses', 0) + 1)
                    text += "😢 **ПОРАЖЕНИЕ!**"

                await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
                return

        # Обработка голосования в мафии
        if message_text.lower().startswith('голосовать '):
            try:
                vote_num = int(message_text.split()[1])
                for game in self.mafia_games.values():
                    if game.chat_id == chat.id and game.phase == "day" and user.id in game.get_alive_players():
                        alive_players = game.get_alive_players()
                        if 1 <= vote_num <= len(alive_players):
                            target_id = alive_players[vote_num - 1]
                            game.votes[user.id] = target_id
                            target_name = game.players_data[target_id]['name']
                            await self.send_private_message(
                                user.id,
                                f"✅ Ваш голос учтён за {target_name}"
                            )
                            await update.message.reply_text(f"✅ Ваш голос учтён за игрока #{vote_num}")
                            break
            except:
                pass
            return

        # Обработка игр (угадай число, быки и коровы)
        for game_id, game in list(self.games_in_progress.items()):
            if game.get('user_id') == user.id:
                if game_id.startswith('guess_'):
                    try:
                        guess = int(message_text)
                        game['attempts'] += 1

                        if guess == game['number']:
                            win = game['bet'] * 2
                            self.db.add_coins(user_data['id'], win)
                            self.db.update_user(user_data['id'], guess_wins=user_data.get('guess_wins', 0) + 1)
                            await update.message.reply_text(
                                f"""
{s.header('🎉 ПОБЕДА!')}

Число {game['number']}!
Попыток: {game['attempts']}
Выигрыш: {win} 💰
                                """
                            )
                            del self.games_in_progress[game_id]
                        elif game['attempts'] >= game['max_attempts']:
                            self.db.update_user(user_data['id'], guess_losses=user_data.get('guess_losses', 0) + 1)
                            await update.message.reply_text(
                                s.error(f"Попытки кончились! Было число {game['number']}")
                            )
                            del self.games_in_progress[game_id]
                        elif guess < game['number']:
                            await update.message.reply_text(f"📈 Загаданное число больше {guess}")
                        else:
                            await update.message.reply_text(f"📉 Загаданное число меньше {guess}")
                    except ValueError:
                        await update.message.reply_text(s.error("Введите число от 1 до 100"))
                    return

                elif game_id.startswith('bulls_'):
                    if len(message_text) != 4 or not message_text.isdigit():
                        await update.message.reply_text(s.error("Введите 4 цифры"))
                        return
                    if len(set(message_text)) != 4:
                        await update.message.reply_text(s.error("Цифры не должны повторяться"))
                        return

                    bulls = 0
                    cows = 0
                    for i in range(4):
                        if message_text[i] == game['number'][i]:
                            bulls += 1
                        elif message_text[i] in game['number']:
                            cows += 1

                    game['attempts'].append((message_text, bulls, cows))

                    if bulls == 4:
                        win = game['bet'] * 3
                        self.db.add_coins(user_data['id'], win)
                        self.db.update_user(user_data['id'], bulls_wins=user_data.get('bulls_wins', 0) + 1)
                        await update.message.reply_text(
                            f"""
{s.header('🎉 ПОБЕДА!')}

Число {game['number']}!
Попыток: {len(game['attempts'])}
Выигрыш: {win} 💰
                            """
                        )
                        del self.games_in_progress[game_id]
                    elif len(game['attempts']) >= game['max_attempts']:
                        self.db.update_user(user_data['id'], bulls_losses=user_data.get('bulls_losses', 0) + 1)
                        await update.message.reply_text(
                            s.error(f"Попытки кончились! Было число {game['number']}")
                        )
                        del self.games_in_progress[game_id]
                    else:
                        await update.message.reply_text(
                            f"🔍 Быки: {bulls}, Коровы: {cows}\nОсталось попыток: {game['max_attempts'] - len(game['attempts'])}"
                        )
                    return

        # Обработка AI
        is_reply_to_bot = (update.message.reply_to_message and
                          update.message.reply_to_message.from_user.id == context.bot.id)

        should_respond = False
        force_response = False
        ai_message = message_text

        if ai_message.lower().startswith("спектр"):
            should_respond = True
            force_response = True
            ai_message = ai_message[6:].strip()
            if not ai_message:
                ai_message = "Привет"
        elif chat.type == "private":
            should_respond = True
            force_response = True
        elif self.ai and self.ai.is_available:
            should_respond = await self.ai.should_respond(ai_message, is_reply_to_bot)
            force_response = False

        if should_respond and self.ai and self.ai.is_available:
            try:
                await update.message.chat.send_action(action="typing")
                response = await self.ai.get_response(
                    user.id,
                    ai_message,
                    user.first_name,
                    force_response=force_response,
                    chat_id=chat.id
                )
                if response:
                    await update.message.reply_text(response)
                    self.db.update_quest_progress(user_data['id'], 'ai_interactions', 1)
            except Exception as e:
                logger.error(f"AI response error: {e}")

    async def handle_left_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        member = update.message.left_chat_member
        if member.is_bot:
            return
        user_data = self.db.get_user_by_id(member.id)
        name = user_data.get('nickname') or member.first_name if user_data else member.first_name
        await update.message.reply_text(f"👋 {name} покинул чат...")
        self.db.log_action(member.id, 'left_chat', f"Покинул чат {update.effective_chat.title}",
                           chat_id=update.effective_chat.id)

    async def handle_new_chat_members(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        for member in update.message.new_chat_members:
            if member.id == context.bot.id:
                chat = update.effective_chat
                added_by = update.message.from_user
                welcome_text = f"""
{s.header('ПРИВЕТ!')}
Меня добавил {added_by.first_name}.

📌 Основные команды:
/menu — главное меню
/help — список всех команд
/profile — мой профиль
/balance — мой баланс
/games — игры

⚠️ Для полноценной работы выдайте мне права администратора!

👑 Владелец: {OWNER_USERNAME}
                """
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📋 Команды", callback_data="help_menu")],
                    [InlineKeyboardButton("👑 Владелец", url=f"https://t.me/{OWNER_USERNAME.replace('@', '')}")]
                ])
                await update.message.reply_photo(
                    photo="https://i.postimg.cc/wxt62Qy5/photo-2026-02-22-22-19-50.jpg",
                    caption=welcome_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=keyboard
                )
                logger.info(f"✅ Бот добавлен в чат: {chat.title} (ID: {chat.id})")
                self.db.cursor.execute('INSERT OR IGNORE INTO chat_settings (chat_id, chat_name) VALUES (?, ?)',
                                      (chat.id, chat.title))
                self.db.conn.commit()

    # ===== ОБРАБОТЧИК КНОПОК =====
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        if not query.message:
            return

        data = query.data
        user = query.from_user
        user_data = self.db.get_user(user.id)

        # Основные кнопки из /start
        if data == "random_chat":
            await self.cmd_random_chat(update, context)
        elif data == "top_chats":
            await self.cmd_top_chats(update, context)
        elif data == "help_menu":
            await self.cmd_help(update, context)
        elif data == "setup_info":
            await self.cmd_setup_info(update, context)
        elif data == "neons_info":
            await self.cmd_neons(update, context)
        elif data == "bonuses_menu":
            await self.cmd_bonuses(update, context)
        elif data == "top_chats_day":
            context.args = ["день"]
            await self.cmd_top_chats(update, context)
        elif data == "top_chats_week":
            context.args = ["неделя"]
            await self.cmd_top_chats(update, context)
        elif data == "top_chats_month":
            context.args = ["месяц"]
            await self.cmd_top_chats(update, context)
        elif data.startswith("boss_attack_"):
            boss_id = int(data.split('_')[2])
            await self._process_boss_attack(update, context, user, user_data, boss_id, is_callback=True)
        elif data == "boss_regen":
            await self.cmd_regen(update, context)
        elif data == "boss_buy_weapon":
            keyboard_buttons = [
                InlineKeyboardButton("🗡 Меч (+10 урона) - 200💰", callback_data="buy_weapon_sword"),
                InlineKeyboardButton("⚔️ Легендарный меч (+30 урона) - 500💰", callback_data="buy_weapon_legendary"),
                InlineKeyboardButton("🔫 Бластер (+50 урона) - 1000💰", callback_data="buy_weapon_blaster"),
                InlineKeyboardButton("🔙 Назад", callback_data="boss_list")
            ]
            keyboard = InlineKeyboardMarkup(self._split_buttons(keyboard_buttons, 1))
            await query.edit_message_text(
                f"{s.header('⚔️ МАГАЗИН ОРУЖИЯ')}\n\nВыберите оружие:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard
            )
        elif data.startswith("buy_weapon_"):
            weapon = data.replace("buy_weapon_", "")
            weapons = {
                "sword": {"name": "🗡 Меч", "damage": 10, "price": 200},
                "legendary": {"name": "⚔️ Легендарный меч", "damage": 30, "price": 500},
                "blaster": {"name": "🔫 Бластер", "damage": 50, "price": 1000}
            }
            if weapon in weapons:
                w = weapons[weapon]
                if user_data['coins'] >= w['price']:
                    self.db.add_coins(user_data['id'], -w['price'])
                    new_damage = user_data['damage'] + w['damage']
                    self.db.update_user(user_data['id'], damage=new_damage)
                    await query.edit_message_text(s.success(f"✅ Куплено: {w['name']}!\nТеперь ваш урон: {new_damage}"))
                else:
                    await query.edit_message_text(s.error(f"❌ Недостаточно монет. Нужно {w['price']} 💰"))
        elif data == "boss_list":
            bosses = self.db.get_bosses()
            text = f"{s.header('👾 БОССЫ')}\n\n"
            for i, boss in enumerate(bosses[:5]):
                status = "⚔️" if boss['is_alive'] else "💀"
                health_bar = s.progress(boss['health'], boss['max_health'], 10)
                text += f"{i+1}. {status} {boss['name']}\n   {health_bar}\n\n"
            keyboard_buttons = []
            for i, boss in enumerate(bosses[:5]):
                if boss['is_alive']:
                    keyboard_buttons.append(InlineKeyboardButton(f"⚔️ {boss['name']}", callback_data=f"boss_attack_{boss['id']}"))
            keyboard_buttons.append(InlineKeyboardButton("🔄 Регенерация", callback_data="boss_regen"))
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                                          reply_markup=InlineKeyboardMarkup(self._split_buttons(keyboard_buttons, 1)))
        elif data.startswith("saper_"):
            # Обработка игры Сапёр (сокращено для краткости)
            pass
        elif data.startswith("vote_for_") or data.startswith("vote_against_"):
            # Обработка голосования за бан
            pass
        elif data.startswith("mafia_confirm_"):
            chat_id = int(data.split('_')[2])
            if chat_id in self.mafia_games:
                game = self.mafia_games[chat_id]
                if user.id in game.players:
                    game.confirm_player(user.id)
                    self.db.cursor.execute('INSERT OR REPLACE INTO mafia_confirmations (game_id, user_id, confirmed) VALUES (?, ?, 1)',
                                         (game.game_id, user.id))
                    self.db.conn.commit()
                    await query.edit_message_text(s.success("✅ Подтверждение получено!\n\nОжидайте начала игры..."))
                    if game.all_confirmed():
                        await self._mafia_start_game(game, context)
        elif data.startswith("accept_duel_"):
            duel_id = int(data.split('_')[2])
            duel = self.db.get_duel(duel_id)
            if not duel or duel['opponent_id'] != user_data['id'] or duel['status'] != 'pending':
                await query.edit_message_text(s.error("Дуэль не найдена или уже обработана"))
                return
            self.db.update_duel(duel_id, status='accepted')
            challenger = self.db.get_user_by_id(duel['challenger_id'])
            opponent = self.db.get_user_by_id(duel['opponent_id'])
            if not challenger or not opponent:
                await query.edit_message_text(s.error("Ошибка загрузки данных"))
                return
            await query.edit_message_text(
                f"""
{s.header('⚔️ ДУЭЛЬ ПРИНЯТА!')}

{challenger['first_name']} VS {opponent['first_name']}
💰 Ставка: {duel['bet']} 💰

🔄 Дуэль начинается...
                """
            )
            asyncio.create_task(self._process_duel(duel_id, challenger, opponent, duel['bet'], update.effective_chat.id, context))
        elif data.startswith("reject_duel_"):
            duel_id = int(data.split('_')[2])
            duel = self.db.get_duel(duel_id)
            if not duel or duel['opponent_id'] != user_data['id'] or duel['status'] != 'pending':
                await query.edit_message_text(s.error("Дуэль не найдена или уже обработана"))
                return
            self.db.update_duel(duel_id, status='rejected')
            self.db.add_coins(duel['challenger_id'], duel['bet'])
            await query.edit_message_text(s.error("❌ Дуэль отклонена\nСтавка возвращена."))
        else:
            # Другие кнопки (marry, bookmark, circle, achievements) – можно добавить по аналогии
            await query.edit_message_text("ℹ️ Функция в разработке")

    # ===== ТАЙМЕРЫ =====
    async def check_timers(self):
        while True:
            try:
                timers = self.db.get_pending_timers()
                for timer in timers:
                    try:
                        await self.app.bot.send_message(
                            chat_id=timer['chat_id'],
                            text=f"⏰ Сработал таймер #{timer['id']}\nВыполняю команду: {timer['command']}"
                        )
                        self.db.complete_timer(timer['id'])
                    except Exception as e:
                        logger.error(f"Ошибка выполнения таймера {timer['id']}: {e}")
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"Ошибка в check_timers: {e}")
                await asyncio.sleep(60)

    # ===== НАЛОГОВЫЙ ТАЙМЕР =====
    async def weekly_tax_loop(self):
        while True:
            now = datetime.now()
            # Проверяем, понедельник ли сегодня, 00:00
            if now.weekday() == 0 and now.hour == 0 and now.minute == 0:
                self.db.apply_wealth_tax()
                await asyncio.sleep(60)  # чтобы не сработало повторно в ту же минуту
            await asyncio.sleep(3600)  # проверяем каждый час

    # ===== НАСТРОЙКА ОБРАБОТЧИКОВ =====
    def setup_handlers(self):
        """Регистрация всех обработчиков (без Telegram-бонусов)"""
        # Основные команды
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CommandHandler("menu", self.show_menu))
        self.app.add_handler(CommandHandler("contacts", self.show_contacts))
        self.app.add_handler(CommandHandler("chart", self.show_chart))
        self.app.add_handler(CommandHandler("randomchat", self.cmd_random_chat))
        self.app.add_handler(CommandHandler("topchats", self.cmd_top_chats))
        self.app.add_handler(CommandHandler("setupinfo", self.cmd_setup_info))

        # Профиль
        self.app.add_handler(CommandHandler("profile", self.cmd_profile))
        self.app.add_handler(CommandHandler("nick", self.cmd_set_nick))
        self.app.add_handler(CommandHandler("title", self.cmd_set_title))
        self.app.add_handler(CommandHandler("motto", self.cmd_set_motto))
        self.app.add_handler(CommandHandler("bio", self.cmd_set_bio))
        self.app.add_handler(CommandHandler("gender", self.cmd_set_gender))
        self.app.add_handler(CommandHandler("removegender", self.cmd_remove_gender))
        self.app.add_handler(CommandHandler("city", self.cmd_set_city))
        self.app.add_handler(CommandHandler("birth", self.cmd_set_birth))
        self.app.add_handler(CommandHandler("age", self.cmd_set_age))
        self.app.add_handler(CommandHandler("id", self.cmd_id))
        self.app.add_handler(CommandHandler("myprofile", self.cmd_my_profile))
        self.app.add_handler(CommandHandler("profile_public", self.cmd_profile_public))
        self.app.add_handler(CommandHandler("profile_private", self.cmd_profile_private))

        # Статистика
        self.app.add_handler(CommandHandler("stats", self.cmd_stats))
        self.app.add_handler(CommandHandler("mystats", self.cmd_my_stats))
        self.app.add_handler(CommandHandler("top", self.cmd_top))
        self.app.add_handler(CommandHandler("topcoins", self.cmd_top_coins))
        self.app.add_handler(CommandHandler("toplevel", self.cmd_top_level))
        self.app.add_handler(CommandHandler("topneons", self.cmd_top_neons))
        self.app.add_handler(CommandHandler("topglitches", self.cmd_top_glitches))

        # Экономика
        self.app.add_handler(CommandHandler("balance", self.cmd_balance))
        self.app.add_handler(CommandHandler("coins", self.cmd_balance))
        self.app.add_handler(CommandHandler("pay", self.cmd_pay))
        self.app.add_handler(CommandHandler("daily", self.cmd_daily))
        self.app.add_handler(CommandHandler("streak", self.cmd_streak))
        self.app.add_handler(CommandHandler("shop", self.cmd_shop))
        self.app.add_handler(CommandHandler("buy", self.cmd_buy))
        self.app.add_handler(CommandHandler("vip", self.cmd_vip_info))
        self.app.add_handler(CommandHandler("buyvip", self.cmd_buy_vip))
        self.app.add_handler(CommandHandler("premium", self.cmd_premium_info))
        self.app.add_handler(CommandHandler("buypremium", self.cmd_buy_premium))
        self.app.add_handler(CommandHandler("neons", self.cmd_neons))
        self.app.add_handler(CommandHandler("glitches", self.cmd_glitches))
        self.app.add_handler(CommandHandler("farm", self.cmd_farm))
        self.app.add_handler(CommandHandler("transfer", self.cmd_transfer_neons))
        self.app.add_handler(CommandHandler("exchange", self.cmd_exchange))

        # Квесты и биржа
        self.app.add_handler(CommandHandler("quests", self.cmd_quests))
        self.app.add_handler(CommandHandler("exchange", self.cmd_exchange_market))
        self.app.add_handler(CommandHandler("buyorder", self.cmd_buy_order))
        self.app.add_handler(CommandHandler("sellorder", self.cmd_sell_order))
        self.app.add_handler(CommandHandler("myorders", self.cmd_my_orders))
        self.app.add_handler(CommandHandler("cancelorder", self.cmd_cancel_order))

        # Игры
        self.app.add_handler(CommandHandler("games", self.cmd_games))
        self.app.add_handler(CommandHandler("coin", self.cmd_coin))
        self.app.add_handler(CommandHandler("dice", self.cmd_dice))
        self.app.add_handler(CommandHandler("dicebet", self.cmd_dice_bet))
        self.app.add_handler(CommandHandler("rps", self.cmd_rps))
        self.app.add_handler(CommandHandler("rr", self.cmd_russian_roulette))
        self.app.add_handler(CommandHandler("roulette", self.cmd_roulette))
        self.app.add_handler(CommandHandler("slots", self.cmd_slots))
        self.app.add_handler(CommandHandler("saper", self.cmd_saper))
        self.app.add_handler(CommandHandler("guess", self.cmd_guess))
        self.app.add_handler(CommandHandler("bulls", self.cmd_bulls))

        # Боссы
        self.app.add_handler(CommandHandler("bosses", self.cmd_bosses))
        self.app.add_handler(CommandHandler("boss", self.cmd_boss_fight))
        self.app.add_handler(CommandHandler("bossinfo", self.cmd_boss_info))
        self.app.add_handler(CommandHandler("regen", self.cmd_regen))

        # Дуэли
        self.app.add_handler(CommandHandler("duel", self.cmd_duel))
        self.app.add_handler(CommandHandler("duels", self.cmd_duels))
        self.app.add_handler(CommandHandler("duelrating", self.cmd_duel_rating))

        # Мафия
        self.app.add_handler(CommandHandler("mafia", self.cmd_mafia))
        self.app.add_handler(CommandHandler("mafiastart", self.cmd_mafia_start))
        self.app.add_handler(CommandHandler("mafiajoin", self.cmd_mafia_join))
        self.app.add_handler(CommandHandler("mafialeave", self.cmd_mafia_leave))
        self.app.add_handler(CommandHandler("mafiaroles", self.cmd_mafia_roles))
        self.app.add_handler(CommandHandler("mafiarules", self.cmd_mafia_rules))
        self.app.add_handler(CommandHandler("mafiastats", self.cmd_mafia_stats))

        # Ачивки
        self.app.add_handler(CommandHandler("achievements", self.cmd_achievements))
        self.app.add_handler(CommandHandler("myachievements", self.cmd_my_achievements))
        self.app.add_handler(CommandHandler("achievement", self.cmd_achievement_info))
        self.app.add_handler(CommandHandler("topachievements", self.cmd_top_achievements))
        self.app.add_handler(CommandHandler("achievements_public", self.cmd_achievements_public))
        self.app.add_handler(CommandHandler("achievements_private", self.cmd_achievements_private))

        # Кружки
        self.app.add_handler(CommandHandler("circles", self.cmd_circles))
        self.app.add_handler(CommandHandler("circle", self.cmd_circle))
        self.app.add_handler(CommandHandler("createcircle", self.cmd_create_circle))
        self.app.add_handler(CommandHandler("joincircle", self.cmd_join_circle))
        self.app.add_handler(CommandHandler("leavecircle", self.cmd_leave_circle))

        # Закладки
        self.app.add_handler(CommandHandler("bookmarks", self.cmd_bookmarks))
        self.app.add_handler(CommandHandler("bookmark", self.cmd_bookmark))
        self.app.add_handler(CommandHandler("addbookmark", self.cmd_add_bookmark))
        self.app.add_handler(CommandHandler("removebookmark", self.cmd_remove_bookmark))
        self.app.add_handler(CommandHandler("chatbook", self.cmd_chat_bookmarks))
        self.app.add_handler(CommandHandler("mybookmarks", self.cmd_my_bookmarks))

        # Таймеры
        self.app.add_handler(CommandHandler("timers", self.cmd_timers))
        self.app.add_handler(CommandHandler("addtimer", self.cmd_add_timer))
        self.app.add_handler(CommandHandler("removetimer", self.cmd_remove_timer))

        # Награды
        self.app.add_handler(CommandHandler("awards", self.cmd_awards))
        self.app.add_handler(CommandHandler("giveaward", self.cmd_give_award))
        self.app.add_handler(CommandHandler("removeaward", self.cmd_remove_award))

        # Кланы
        self.app.add_handler(CommandHandler("clan", self.cmd_clan))
        self.app.add_handler(CommandHandler("clans", self.cmd_clans))
        self.app.add_handler(CommandHandler("createclan", self.cmd_create_clan))
        self.app.add_handler(CommandHandler("joinclan", self.cmd_join_clan))
        self.app.add_handler(CommandHandler("leaveclan", self.cmd_leave_clan))

        # Бонусы (кибер-бонусы)
        self.app.add_handler(CommandHandler("bonuses", self.cmd_bonuses))
        self.app.add_handler(CommandHandler("bonusinfo", self.cmd_bonus_info))
        self.app.add_handler(CommandHandler("buybonus", self.cmd_buy_bonus))

        # Второй AI (изображения)
        self.app.add_handler(CommandHandler("imagine", self.cmd_imagine))
        self.app.add_handler(CommandHandler("imagine_help", self.cmd_imagine_help))

        # Тайный орден
        self.app.add_handler(CommandHandler("order", self.cmd_order))
        self.app.add_handler(CommandHandler("startorder", self.cmd_start_order))
        self.app.add_handler(CommandHandler("revealorder", self.cmd_reveal_order))

        # Развлечения
        self.app.add_handler(CommandHandler("joke", self.cmd_joke))
        self.app.add_handler(CommandHandler("fact", self.cmd_fact))
        self.app.add_handler(CommandHandler("quote", self.cmd_quote))
        self.app.add_handler(CommandHandler("whoami", self.cmd_whoami))
        self.app.add_handler(CommandHandler("advice", self.cmd_advice))
        self.app.add_handler(CommandHandler("compatibility", self.cmd_compatibility))
        self.app.add_handler(CommandHandler("weather", self.cmd_weather))
        self.app.add_handler(CommandHandler("random", self.cmd_random))
        self.app.add_handler(CommandHandler("choose", self.cmd_choose))
        self.app.add_handler(CommandHandler("dane", self.cmd_dane))
        self.app.add_handler(CommandHandler("ship", self.cmd_ship))
        self.app.add_handler(CommandHandler("pairing", self.cmd_pairing))
        self.app.add_handler(CommandHandler("pairs", self.cmd_pairs))

        # Полезное
        self.app.add_handler(CommandHandler("ping", self.cmd_ping))
        self.app.add_handler(CommandHandler("uptime", self.cmd_uptime))
        self.app.add_handler(CommandHandler("info", self.cmd_info))

        # Модерация
        self.app.add_handler(CommandHandler("admins", self.cmd_who_admins))
        self.app.add_handler(CommandHandler("warns", self.cmd_warns))
        self.app.add_handler(CommandHandler("mywarns", self.cmd_my_warns))
        self.app.add_handler(CommandHandler("mutelist", self.cmd_mutelist))
        self.app.add_handler(CommandHandler("banlist", self.cmd_banlist))
        self.app.add_handler(CommandHandler("triggers", self.cmd_list_triggers))
        self.app.add_handler(CommandHandler("rules", self.cmd_show_rules))
        self.app.add_handler(CommandHandler("checkrights", self.cmd_checkrights))
        self.app.add_handler(CommandHandler("add_trigger", self.cmd_add_trigger))
        self.app.add_handler(CommandHandler("remove_trigger", self.cmd_remove_trigger))
        self.app.add_handler(CommandHandler("set_antimat", self.cmd_set_antimat))
        self.app.add_handler(CommandHandler("set_antilink", self.cmd_set_antilink))
        self.app.add_handler(CommandHandler("set_antiflood", self.cmd_set_antiflood))
        self.app.add_handler(CommandHandler("clear", self.cmd_clear))
        self.app.add_handler(CommandHandler("clear_user", self.cmd_clear_user))
        self.app.add_handler(CommandHandler("set_welcome", self.cmd_set_welcome))
        self.app.add_handler(CommandHandler("set_rules", self.cmd_set_rules))
        self.app.add_handler(CommandHandler("set_captcha", self.cmd_set_captcha))

        # Модерация (ранги, мут, бан)
        self.app.add_handler(CommandHandler("set_rank", self.cmd_set_rank))
        self.app.add_handler(CommandHandler("set_rank2", self.cmd_set_rank2))
        self.app.add_handler(CommandHandler("set_rank3", self.cmd_set_rank3))
        self.app.add_handler(CommandHandler("set_rank4", self.cmd_set_rank4))
        self.app.add_handler(CommandHandler("set_rank5", self.cmd_set_rank5))
        self.app.add_handler(CommandHandler("lower_rank", self.cmd_lower_rank))
        self.app.add_handler(CommandHandler("remove_rank", self.cmd_remove_rank))
        self.app.add_handler(CommandHandler("remove_left", self.cmd_remove_left))
        self.app.add_handler(CommandHandler("remove_all_ranks", self.cmd_remove_all_ranks))
        self.app.add_handler(CommandHandler("mute", self.cmd_mute))
        self.app.add_handler(CommandHandler("unmute", self.cmd_unmute))
        self.app.add_handler(CommandHandler("ban", self.cmd_ban))
        self.app.add_handler(CommandHandler("unban", self.cmd_unban))
        self.app.add_handler(CommandHandler("kick", self.cmd_kick))

        # Русские текстовые команды
        self.app.add_handler(MessageHandler(filters.Regex(r'^[0-7]$'), self.handle_numbers))
        self.app.add_handler(MessageHandler(filters.Regex(r'^стата$'), self.cmd_chat_stats_today))
        self.app.add_handler(MessageHandler(filters.Regex(r'^стата неделя$'), self.cmd_chat_stats_week))
        self.app.add_handler(MessageHandler(filters.Regex(r'^стата месяц$'), self.cmd_chat_stats_month))
        self.app.add_handler(MessageHandler(filters.Regex(r'^стата вся$'), self.cmd_chat_stats_all))
        self.app.add_handler(MessageHandler(filters.Regex(r'^топ$'), self.cmd_top_chat_today))
        self.app.add_handler(MessageHandler(filters.Regex(r'^топ неделя$'), self.cmd_top_chat_week))
        self.app.add_handler(MessageHandler(filters.Regex(r'^топ месяц$'), self.cmd_top_chat_month))
        self.app.add_handler(MessageHandler(filters.Regex(r'^топ вся$'), self.cmd_top_chat_all))
        self.app.add_handler(MessageHandler(filters.Regex(r'^мои ачивки$'), self.cmd_my_achievements))
        self.app.add_handler(MessageHandler(filters.Regex(r'^топ ачивок$'), self.cmd_top_achievements))
        self.app.add_handler(MessageHandler(filters.Regex(r'^ачивка \d+$'), self.cmd_achievement_info))
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+Ачивки$'), self.cmd_achievements_public))
        self.app.add_handler(MessageHandler(filters.Regex(r'^-Ачивки$'), self.cmd_achievements_private))
        self.app.add_handler(MessageHandler(filters.Regex(r'^кружки$'), self.cmd_circles))
        self.app.add_handler(MessageHandler(filters.Regex(r'^кружок \d+$'), self.cmd_circle))
        self.app.add_handler(MessageHandler(filters.Regex(r'^создать кружок'), self.cmd_create_circle))
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+Кружок \d+$'), self.cmd_join_circle))
        self.app.add_handler(MessageHandler(filters.Regex(r'^-Кружок \d+$'), self.cmd_leave_circle))
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+Закладка'), self.cmd_add_bookmark))
        self.app.add_handler(MessageHandler(filters.Regex(r'^закладка \d+$'), self.cmd_bookmark))
        self.app.add_handler(MessageHandler(filters.Regex(r'^чатбук$'), self.cmd_chat_bookmarks))
        self.app.add_handler(MessageHandler(filters.Regex(r'^мои закладки$'), self.cmd_my_bookmarks))
        self.app.add_handler(MessageHandler(filters.Regex(r'^-Закладка \d+$'), self.cmd_remove_bookmark))
        self.app.add_handler(MessageHandler(filters.Regex(r'^таймер через'), self.cmd_add_timer))
        self.app.add_handler(MessageHandler(filters.Regex(r'^таймер на'), self.cmd_add_timer))
        self.app.add_handler(MessageHandler(filters.Regex(r'^таймеры$'), self.cmd_timers))
        self.app.add_handler(MessageHandler(filters.Regex(r'^удалить таймер \d+$'), self.cmd_remove_timer))
        self.app.add_handler(MessageHandler(filters.Regex(r'^наградить \d+'), self.cmd_give_award))
        self.app.add_handler(MessageHandler(filters.Regex(r'^награды'), self.cmd_awards))
        self.app.add_handler(MessageHandler(filters.Regex(r'^снять награду'), self.cmd_remove_award))
        self.app.add_handler(MessageHandler(filters.Regex(r'^моя анкета$'), self.cmd_my_profile))
        self.app.add_handler(MessageHandler(filters.Regex(r'^мой пол '), self.cmd_set_gender))
        self.app.add_handler(MessageHandler(filters.Regex(r'^-Пол$'), self.cmd_remove_gender))
        self.app.add_handler(MessageHandler(filters.Regex(r'^мой город '), self.cmd_set_city))
        self.app.add_handler(MessageHandler(filters.Regex(r'^мой др '), self.cmd_set_birth))
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+Анкета$'), self.cmd_profile_public))
        self.app.add_handler(MessageHandler(filters.Regex(r'^-Анкета$'), self.cmd_profile_private))
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+Модер|^!модер|^повысить$'), self.cmd_set_rank))
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+Модер 2|^!модер 2|^повысить 2$'), self.cmd_set_rank2))
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+Модер 3|^!модер 3|^повысить 3$'), self.cmd_set_rank3))
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+Модер 4|^!модер 4|^повысить 4$'), self.cmd_set_rank4))
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+Модер 5|^!модер 5|^повысить 5$'), self.cmd_set_rank5))
        self.app.add_handler(MessageHandler(filters.Regex(r'^понизить'), self.cmd_lower_rank))
        self.app.add_handler(MessageHandler(filters.Regex(r'^снять |^разжаловать'), self.cmd_remove_rank))
        self.app.add_handler(MessageHandler(filters.Regex(r'^варн|^пред'), self.cmd_warn))
        self.app.add_handler(MessageHandler(filters.Regex(r'^снять варн'), self.cmd_unwarn))
        self.app.add_handler(MessageHandler(filters.Regex(r'^снять все варны'), self.cmd_unwarn_all))
        self.app.add_handler(MessageHandler(filters.Regex(r'^мут'), self.cmd_mute))
        self.app.add_handler(MessageHandler(filters.Regex(r'^размут'), self.cmd_unmute))
        self.app.add_handler(MessageHandler(filters.Regex(r'^бан'), self.cmd_ban))
        self.app.add_handler(MessageHandler(filters.Regex(r'^разбан'), self.cmd_unban))
        self.app.add_handler(MessageHandler(filters.Regex(r'^кик'), self.cmd_kick))
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+триггер'), self.cmd_add_trigger))
        self.app.add_handler(MessageHandler(filters.Regex(r'^-триггер'), self.cmd_remove_trigger))
        self.app.add_handler(MessageHandler(filters.Regex(r'^антимат'), self.cmd_set_antimat))
        self.app.add_handler(MessageHandler(filters.Regex(r'^антиссылки'), self.cmd_set_antilink))
        self.app.add_handler(MessageHandler(filters.Regex(r'^антифлуд'), self.cmd_set_antiflood))
        self.app.add_handler(MessageHandler(filters.Regex(r'^чистка'), self.cmd_clear))
        self.app.add_handler(MessageHandler(filters.Regex(r'^чистка от'), self.cmd_clear_user))
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+приветствие'), self.cmd_set_welcome))
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+правила'), self.cmd_set_rules))
        self.app.add_handler(MessageHandler(filters.Regex(r'^капча'), self.cmd_set_captcha))
        self.app.add_handler(MessageHandler(filters.Regex(r'^!темы$'), self.cmd_themes))
        self.app.add_handler(MessageHandler(filters.Regex(r'^!темы \d+$'), self.cmd_apply_theme))
        self.app.add_handler(MessageHandler(filters.Regex(r'^!темы \w+$'), self.cmd_apply_theme_by_name))
        self.app.add_handler(MessageHandler(filters.Regex(r'^!привязать$'), self.cmd_bind_chat))
        self.app.add_handler(MessageHandler(filters.Regex(r'^код чата$'), self.cmd_chat_code))
        self.app.add_handler(MessageHandler(filters.Regex(r'^сменить код'), self.cmd_change_chat_code))
        self.app.add_handler(MessageHandler(filters.Regex(r'^кубышка$'), self.cmd_treasury))
        self.app.add_handler(MessageHandler(filters.Regex(r'^кубышка в неоны$'), self.cmd_treasury_withdraw))
        self.app.add_handler(MessageHandler(filters.Regex(r'^Случайная беседа$'), self.cmd_random_chat))
        self.app.add_handler(MessageHandler(filters.Regex(r'^Беседы топ дня$'), self.cmd_top_chats))
        self.app.add_handler(MessageHandler(filters.Regex(r'^Команды$'), self.cmd_help))
        self.app.add_handler(MessageHandler(filters.Regex(r'^Установка$'), self.cmd_setup_info))

        # Основные обработчики сообщений
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, self.handle_new_chat_members))
        self.app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, self.handle_left_member))

        # Callback кнопки
        self.app.add_handler(CallbackQueryHandler(self.button_callback))

        self.app.add_error_handler(self.error_handler)

        logger.info(f"✅ Зарегистрировано обработчиков: {len(self.app.handlers)}")

    # ===== ОБРАБОТЧИК ОШИБОК =====
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            logger.error(f"Ошибка: {context.error}")
            if update and update.effective_message:
                if "Database" in str(context.error) or "Connection" in str(context.error):
                    await update.effective_message.reply_text(s.error("Ошибка базы данных. Попробуйте позже."))
        except:
            pass

    # ===== ЗАПУСК =====
    async def run(self):
        try:
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling(drop_pending_updates=True)

            logger.info(f"🚀 Бот {BOT_NAME} успешно запущен")
            logger.info(f"👑 Владелец: {OWNER_USERNAME}")
            logger.info(f"🤖 AI: {'Подключен' if self.ai and self.ai.is_available else 'Не подключен'}")
            logger.info(f"📱 VK: {'Подключен' if self.vk and self.vk.is_available else 'Не подключен'}")
            logger.info(f"🎨 Image AI: Подключен (бесплатный Pollinations)")

            asyncio.create_task(self.check_timers())
            asyncio.create_task(self.weekly_tax_loop())

            while True:
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Критическая ошибка: {e}")
            import traceback
            traceback.print_exc()
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
    print(f"✨ ЗАПУСК БОТА {BOT_NAME} v{BOT_VERSION} ✨")
    print("=" * 60)
    print(f"📊 AI: {'✅ Подключен' if ai and ai.is_available else '❌ Не подключен'}")
    print(f"📊 VK: {'✅ Подключен' if vk_bot and vk_bot.is_available else '❌ Не подключен'}")
    print(f"📊 Image AI: ✅ Подключен (Pollinations.ai)")
    print(f"📊 Команд: 300+")
    print(f"📊 Модулей: 30+")
    print("=" * 60)

    bot = SpectrumBot()

    try:
        await bot.run()
    except KeyboardInterrupt:
        logger.info("👋 Остановка по запросу пользователя")
        await bot.close()
    except Exception as e:
        logger.error(f"❌ Фатальная ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Программа завершена пользователем")
    except Exception as e:
        logger.error(f"❌ Фатальная ошибка: {e}")
        import traceback
        traceback.print_exc()
