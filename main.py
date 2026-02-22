#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
СПЕКТР v3.0 ULTIMATE - ИСПРАВЛЕННАЯ И УЛУЧШЕННАЯ ВЕРСИЯ
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
from typing import Optional, Dict, Any, List, Tuple, Union
from collections import defaultdict, deque
from enum import Enum
from io import BytesIO
import uuid

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

# ========== КОНСТАНТЫ ==========
BOT_NAME = "Спектр"
BOT_VERSION = "6.0 ULTIMATE"
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
EXCHANGE_COMMISSION = 0.02  # 2% комиссия биржи

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

# ========== КЛАСС ДЛЯ ГРАФИКОВ ==========
class ChartGenerator:
    @staticmethod
    def create_activity_chart(days: list, counts: list, username: str = "Игрок"):
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from datetime import datetime, timedelta
        
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(8, 4))
        fig.patch.set_facecolor('#1a1a1a')
        ax.set_facecolor('#2a2a2a')
        
        ax.plot(days, counts, marker='o', linestyle='-', color='#00d4ff', linewidth=2, markersize=6)
        ax.fill_between(days, counts, color='#00d4ff', alpha=0.1)
        
        ax.set_title(f"АКТИВНОСТЬ {username.upper()}", fontsize=14, fontweight='bold', pad=20, color='white')
        ax.set_ylabel("Сообщения", color='white')
        ax.tick_params(colors='white')
        ax.grid(True, linestyle='--', alpha=0.3, color='gray')
        
        for spine in ax.spines.values():
            spine.set_visible(False)
        
        buf = BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=100, facecolor=fig.get_facecolor())
        buf.seek(0)
        plt.close(fig)
        return buf

# ========== ЭЛЕГАНТНОЕ ОФОРМЛЕНИЕ ==========
class Style:
    SEPARATOR = "─" * 28
    SEPARATOR_BOLD = "━" * 28
    
    @classmethod
    def header(cls, title: str, emoji: str = "⚜️") -> str:
        return f"\n{emoji}{emoji} {title.upper()} {emoji}{emoji}\n{cls.SEPARATOR_BOLD}\n"
    
    @classmethod
    def section(cls, title: str, emoji: str = "📌") -> str:
        return f"\n{emoji} {title}\n{cls.SEPARATOR}\n"
    
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
        return f"{emoji} {name}: {value}"
    
    @classmethod
    def progress(cls, current: int, total: int, length: int = 15) -> str:
        filled = int((current / total) * length) if total > 0 else 0
        bar = "█" * filled + "░" * (length - filled)
        return f"`{bar}` {current}/{total}"
    
    @classmethod
    def success(cls, text: str) -> str:
        return f"✅ {text}"
    
    @classmethod
    def error(cls, text: str) -> str:
        return f"❌ {text}"
    
    @classmethod
    def warning(cls, text: str) -> str:
        return f"⚠️ {text}"
    
    @classmethod
    def info(cls, text: str) -> str:
        return f"ℹ️ {text}"
    
    @classmethod
    def code(cls, text: str) -> str:
        return f"`{text}`"

s = Style()

# ========== БАЗА ДАННЫХ ==========
class Database:
    def __init__(self):
        self.conn = sqlite3.connect("spectrum.db", check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.create_tables()
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
        
        # Таблица пользователей
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
    
    # ===== ОСНОВНЫЕ МЕТОДЫ =====
    
    def get_user(self, telegram_id: int, first_name: str = None, platform: str = "telegram") -> Dict[str, Any]:
        """Получить или создать пользователя"""
        id_field = "telegram_id" if platform == "telegram" else "vk_id"
        
        self.cursor.execute(f"SELECT * FROM users WHERE {id_field} = ? AND platform = ?", (telegram_id, platform))
        row = self.cursor.fetchone()
        
        if not row:
            name = first_name if first_name else f"User{telegram_id}"
            
            role = 'owner' if (platform == "telegram" and telegram_id == OWNER_ID) else 'user'
            rank = 5 if (platform == "telegram" and telegram_id == OWNER_ID) else 0
            rank_name = RANKS[rank]["name"]
            
            self.cursor.execute(f'''
                INSERT INTO users ({id_field}, first_name, role, rank, rank_name, last_seen, platform)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (telegram_id, name, role, rank, rank_name, datetime.now().isoformat(), platform))
            self.conn.commit()
            return self.get_user(telegram_id, name, platform)
        
        user = dict(row)
        
        if first_name and user['first_name'] != first_name and (user['first_name'] == 'Player' or user['first_name'].startswith('User')):
            self.cursor.execute(f"UPDATE users SET first_name = ? WHERE {id_field} = ? AND platform = ?",
                              (first_name, telegram_id, platform))
            user['first_name'] = first_name
        
        self.cursor.execute(f"UPDATE users SET last_seen = ? WHERE {id_field} = ? AND platform = ?",
                          (datetime.now().isoformat(), telegram_id, platform))
        self.conn.commit()
        
        return user
    
    def get_user_by_id(self, user_id: int, platform: str = "telegram") -> Optional[Dict[str, Any]]:
        self.cursor.execute("SELECT * FROM users WHERE id = ? AND platform = ?", (user_id, platform))
        row = self.cursor.fetchone()
        return dict(row) if row else None
    
    def get_user_by_username(self, username: str, platform: str = "telegram") -> Optional[Dict[str, Any]]:
        if username.startswith('@'):
            username = username[1:]
        # Добавляем platform в запрос для безопасности
        self.cursor.execute("SELECT * FROM users WHERE username = ? AND platform = ?", (username, platform))
        row = self.cursor.fetchone()
        return dict(row) if row else None
    
    def update_user(self, user_id: int, platform: str = "telegram", kwargs) -> bool:
        if not kwargs:
            return False
        for key, value in kwargs.items():
            self.cursor.execute(f"UPDATE users SET {key} = ? WHERE id = ? AND platform = ?", (value, user_id, platform))
        self.conn.commit()
        return True
    
    def is_banned(self, user_id: int, platform: str = "telegram") -> bool:
        """Проверка, забанен ли пользователь"""
        self.cursor.execute("SELECT banned FROM users WHERE id = ? AND platform = ?", (user_id, platform))
        row = self.cursor.fetchone()
        return row and row[0] == 1
    
    # ===== ВАЛЮТЫ =====
    
    def add_coins(self, user_id: int, amount: int, platform: str = "telegram") -> int:
        self.cursor.execute("UPDATE users SET coins = coins + ? WHERE id = ? AND platform = ?", (amount, user_id, platform))
        self.conn.commit()
        self.cursor.execute("SELECT coins FROM users WHERE id = ? AND platform = ?", (user_id, platform))
        return self.cursor.fetchone()[0]
    
    def add_neons(self, user_id: int, amount: int, platform: str = "telegram") -> int:
        self.cursor.execute("UPDATE users SET neons = neons + ? WHERE id = ? AND platform = ?", (amount, user_id, platform))
        self.conn.commit()
        self.check_wealth_achievements(user_id, platform)
        self.cursor.execute("SELECT neons FROM users WHERE id = ? AND platform = ?", (user_id, platform))
        return self.cursor.fetchone()[0]
    
    def add_glitches(self, user_id: int, amount: int, platform: str = "telegram") -> int:
        self.cursor.execute("UPDATE users SET glitches = glitches + ? WHERE id = ? AND platform = ?", (amount, user_id, platform))
        self.conn.commit()
        self.check_glitch_achievements(user_id, platform)
        self.cursor.execute("SELECT glitches FROM users WHERE id = ? AND platform = ?", (user_id, platform))
        return self.cursor.fetchone()[0]
    
    def transfer_neons(self, from_id: int, to_id: int, amount: int, commission: int = 0, platform: str = "telegram") -> bool:
        self.cursor.execute("UPDATE users SET neons = neons - ? WHERE id = ? AND platform = ?", (amount + commission, from_id, platform))
        self.cursor.execute("UPDATE users SET neons = neons + ? WHERE id = ? AND platform = ?", (amount, to_id, platform))
        if commission > 0:
            owner = self.get_user(OWNER_ID, platform=platform)
            self.cursor.execute("UPDATE users SET neons = neons + ? WHERE id = ? AND platform = ?", (commission, owner['id'], platform))
        self.conn.commit()
        return True
    
    # ===== МЕТОДЫ ДЛЯ АЧИВОК =====
    def check_wealth_achievements(self, user_id: int, platform: str = "telegram"):
        user = self.get_user_by_id(user_id, platform)
        if not user:
            return
        
        neons = user.get('neons', 0)
        
        thresholds = [
            (1, 1000),
            (2, 10000),
            (3, 100000)
        ]
        
        for ach_id, threshold in thresholds:
            if neons >= threshold:
                self.unlock_achievement(user_id, ach_id, platform)
    
    def check_glitch_achievements(self, user_id: int, platform: str = "telegram"):
        user = self.get_user_by_id(user_id, platform)
        if not user:
            return
        
        glitches = user.get('glitches', 0)
        
        thresholds = [
            (4, 1000),
            (5, 10000),
            (6, 100000)
        ]
        
        for ach_id, threshold in thresholds:
            if glitches >= threshold:
                self.unlock_achievement(user_id, ach_id, platform)
    
    def unlock_achievement(self, user_id: int, achievement_id: int, platform: str = "telegram") -> bool:
        self.cursor.execute("SELECT id FROM achievements WHERE user_id = ? AND achievement_id = ? AND platform = ?",
                          (user_id, achievement_id, platform))
        if self.cursor.fetchone():
            return False
        
        self.cursor.execute("SELECT * FROM achievements_list WHERE id = ?", (achievement_id,))
        ach = self.cursor.fetchone()
        if not ach:
            return False
        
        self.cursor.execute("INSERT INTO achievements (user_id, achievement_id, platform) VALUES (?, ?, ?)",
                          (user_id, achievement_id, platform))
        
        ach = dict(ach)
        if ach['reward_neons'] > 0:
            self.add_neons(user_id, ach['reward_neons'], platform)
        if ach['reward_glitches'] > 0:
            self.add_glitches(user_id, ach['reward_glitches'], platform)
        if ach['reward_title']:
            user = self.get_user_by_id(user_id, platform)
            self.update_user(user_id, platform, title=ach['reward_title'])
        if ach['reward_status']:
            pass
        
        self.conn.commit()
        return True
    
    def get_user_achievements(self, user_id: int, platform: str = "telegram") -> List[Dict]:
        self.cursor.execute("""
            SELECT a.*, al.name, al.description, al.category, al.reward_neons, al.reward_glitches, al.secret
            FROM achievements a
            JOIN achievements_list al ON a.achievement_id = al.id
            WHERE a.user_id = ? AND a.platform = ?
            ORDER BY a.unlocked_at
        """, (user_id, platform))
        return [dict(row) for row in self.cursor.fetchall()]
    
    # ===== МЕТОДЫ ДЛЯ КРУЖКОВ =====
    def create_circle(self, chat_id: int, name: str, description: str, creator_id: int) -> Optional[int]:
        self.cursor.execute("SELECT COUNT(*) FROM circles WHERE created_by = ?", (creator_id,))
        if self.cursor.fetchone()[0] >= MAX_CIRCLES_PER_USER:
            return None
        
        self.cursor.execute("SELECT circle_limit FROM chat_settings WHERE chat_id = ?", (chat_id,))
        row = self.cursor.fetchone()
        limit = row[0] if row else MAX_CIRCLES_PER_CHAT
        
        self.cursor.execute("SELECT COUNT(*) FROM circles WHERE chat_id = ?", (chat_id,))
        if self.cursor.fetchone()[0] >= limit:
            return None
        
        self.cursor.execute("""
            INSERT INTO circles (chat_id, name, description, created_by, members)
            VALUES (?, ?, ?, ?, ?)
        """, (chat_id, name, description, creator_id, json.dumps([creator_id])))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def join_circle(self, circle_id: int, user_id: int) -> bool:
        self.cursor.execute("SELECT members FROM circles WHERE id = ?", (circle_id,))
        row = self.cursor.fetchone()
        if not row:
            return False
        
        members = json.loads(row[0])
        if user_id in members:
            return False
        
        members.append(user_id)
        self.cursor.execute("UPDATE circles SET members = ? WHERE id = ?", (json.dumps(members), circle_id))
        self.conn.commit()
        return True
    
    def leave_circle(self, circle_id: int, user_id: int) -> bool:
        self.cursor.execute("SELECT members, created_by FROM circles WHERE id = ?", (circle_id,))
        row = self.cursor.fetchone()
        if not row:
            return False
        
        members = json.loads(row[0])
        if user_id not in members:
            return False
        
        if user_id == row[1] and len(members) > 1:
            return False
        
        members.remove(user_id)
        self.cursor.execute("UPDATE circles SET members = ? WHERE id = ?", (json.dumps(members), circle_id))
        self.conn.commit()
        return True
    
    # ===== МЕТОДЫ ДЛЯ КЛАНОВ =====
    def create_clan(self, chat_id: int, name: str, description: str, creator_id: int, platform: str = "telegram") -> Optional[int]:
        user = self.get_user_by_id(creator_id, platform)
        if user.get('clan_id', 0) != 0:
            return None
        
        self.cursor.execute("""
            INSERT INTO clans (chat_id, name, description, created_by, platform)
            VALUES (?, ?, ?, ?, ?)
        """, (chat_id, name, description, creator_id, platform))
        clan_id = self.cursor.lastrowid
        
        self.update_user(creator_id, platform, clan_id=clan_id, clan_role='owner')
        self.conn.commit()
        return clan_id
    
    def join_clan(self, clan_id: int, user_id: int, platform: str = "telegram") -> bool:
        user = self.get_user_by_id(user_id, platform)
        if user.get('clan_id', 0) != 0:
            self.leave_clan(user_id, platform)
        
        self.cursor.execute("SELECT type, members FROM clans WHERE id = ? AND platform = ?", (clan_id, platform))
        row = self.cursor.fetchone()
        if not row:
            return False
        
        clan_type, members = row[0], row[1]
        
        if clan_type == 'closed':
            pending = json.loads(self.cursor.execute("SELECT pending_requests FROM clans WHERE id = ? AND platform = ?", (clan_id, platform)).fetchone()[0])
            if user_id not in pending:
                pending.append(user_id)
                self.cursor.execute("UPDATE clans SET pending_requests = ? WHERE id = ? AND platform = ?", (json.dumps(pending), clan_id, platform))
                self.conn.commit()
            return False
        
        self.update_user(user_id, platform, clan_id=clan_id, clan_role='member')
        self.cursor.execute("UPDATE clans SET members = members + 1 WHERE id = ? AND platform = ?", (clan_id, platform))
        self.conn.commit()
        return True
    
    def leave_clan(self, user_id: int, platform: str = "telegram") -> bool:
        user = self.get_user_by_id(user_id, platform)
        if not user or user.get('clan_id', 0) == 0:
            return False
        
        clan_id = user['clan_id']
        
        if user.get('clan_role') == 'owner':
            self.cursor.execute("SELECT id FROM users WHERE clan_id = ? AND id != ? AND platform = ? LIMIT 1", (clan_id, user_id, platform))
            new_owner = self.cursor.fetchone()
            if new_owner:
                self.update_user(new_owner[0], platform, clan_role='owner')
        
        self.update_user(user_id, platform, clan_id=0, clan_role='member')
        self.cursor.execute("UPDATE clans SET members = members - 1 WHERE id = ? AND platform = ?", (clan_id, platform))
        self.conn.commit()
        return True
    
    # ===== МЕТОДЫ ДЛЯ ЗАКЛАДОК =====
    def add_bookmark(self, chat_id: int, user_id: int, name: str, content: str, message_id: int = None) -> int:
        self.cursor.execute("""
            INSERT INTO bookmarks (chat_id, user_id, name, content, message_id)
            VALUES (?, ?, ?, ?, ?)
        """, (chat_id, user_id, name, content, message_id))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_chat_bookmarks(self, chat_id: int) -> List[Dict]:
        self.cursor.execute("""
            SELECT b.*, u.first_name, u.username
            FROM bookmarks b
            JOIN users u ON b.user_id = u.id
            WHERE b.chat_id = ? AND b.visible = 1
            ORDER BY b.created_at DESC
        """, (chat_id,))
        return [dict(row) for row in self.cursor.fetchall()]
    
    def get_user_bookmarks(self, user_id: int, chat_id: int = None) -> List[Dict]:
        if chat_id:
            self.cursor.execute("""
                SELECT * FROM bookmarks
                WHERE user_id = ? AND chat_id = ?
                ORDER BY created_at DESC
            """, (user_id, chat_id))
        else:
            self.cursor.execute("""
                SELECT * FROM bookmarks
                WHERE user_id = ?
                ORDER BY created_at DESC
            """, (user_id,))
        return [dict(row) for row in self.cursor.fetchall()]
    
    # ===== МЕТОДЫ ДЛЯ ТАЙМЕРОВ =====
    def add_timer(self, chat_id: int, user_id: int, execute_at: datetime, command: str) -> Optional[int]:
        self.cursor.execute("SELECT COUNT(*) FROM timers WHERE chat_id = ? AND status = 'pending'", (chat_id,))
        if self.cursor.fetchone()[0] >= 5:
            return None
        
        self.cursor.execute("""
            INSERT INTO timers (chat_id, user_id, execute_at, command)
            VALUES (?, ?, ?, ?)
        """, (chat_id, user_id, execute_at.isoformat(), command))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_pending_timers(self) -> List[Dict]:
        now = datetime.now().isoformat()
        self.cursor.execute("""
            SELECT * FROM timers
            WHERE status = 'pending' AND execute_at <= ?
        """, (now,))
        return [dict(row) for row in self.cursor.fetchall()]
    
    def complete_timer(self, timer_id: int):
        self.cursor.execute("UPDATE timers SET status = 'completed' WHERE id = ?", (timer_id,))
        self.conn.commit()
    
    # ===== МЕТОДЫ ДЛЯ НАГРАД =====
    def give_award(self, chat_id: int, user_id: int, awarded_by: int, degree: int, text: str) -> int:
        self.cursor.execute("""
            INSERT INTO awards (chat_id, user_id, awarded_by, degree, text)
            VALUES (?, ?, ?, ?, ?)
        """, (chat_id, user_id, awarded_by, degree, text))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_user_awards(self, user_id: int, chat_id: int = None) -> List[Dict]:
        if chat_id:
            self.cursor.execute("""
                SELECT a.*, u.first_name as awarded_by_name
                FROM awards a
                JOIN users u ON a.awarded_by = u.id
                WHERE a.user_id = ? AND a.chat_id = ?
                ORDER BY a.degree DESC, a.awarded_at DESC
            """, (user_id, chat_id))
        else:
            self.cursor.execute("""
                SELECT a.*, u.first_name as awarded_by_name
                FROM awards a
                JOIN users u ON a.awarded_by = u.id
                WHERE a.user_id = ?
                ORDER BY a.degree DESC, a.awarded_at DESC
            """, (user_id,))
        return [dict(row) for row in self.cursor.fetchall()]
    
    # ===== МЕТОДЫ ДЛЯ СЕТОК ЧАТОВ =====
    def create_grid(self, owner_id: int, name: str) -> int:
        self.cursor.execute("INSERT INTO chat_grids (owner_id, name) VALUES (?, ?)", (owner_id, name))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def add_chat_to_grid(self, grid_id: int, chat_id: int) -> bool:
        try:
            self.cursor.execute("INSERT INTO grid_chats (grid_id, chat_id) VALUES (?, ?)", (grid_id, chat_id))
            self.conn.commit()
            return True
        except:
            return False
    
    def get_user_grids(self, user_id: int) -> List[Dict]:
        self.cursor.execute("""
            SELECT * FROM chat_grids WHERE owner_id = ?
        """, (user_id,))
        return [dict(row) for row in self.cursor.fetchall()]
    
    # ===== МЕТОДЫ ДЛЯ БОНУСОВ =====
    def buy_bonus(self, user_id: int, bonus_type: str, duration_days: int, price_neons: int, platform: str = "telegram") -> bool:
        user = self.get_user_by_id(user_id, platform)
        if user.get('neons', 0) < price_neons:
            return False
        
        expires = (datetime.now() + timedelta(days=duration_days)).isoformat()
        
        field_map = {
            'cyber_status': 'cyber_status_until',
            'turbo_drive': 'turbo_drive_until',
            'cyber_luck': 'cyber_luck_until',
            'rp_packet': 'rp_packet_until'
        }
        
        if bonus_type in field_map:
            self.update_user(user_id, platform, {field_map[bonus_type]: expires})
        elif bonus_type == 'glitch_hammer':
            self.cursor.execute("""
                INSERT INTO user_bonuses (user_id, bonus_type, expires, data, platform)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, 'glitch_hammer', expires, json.dumps({'uses_left': 1}), platform))
        elif bonus_type == 'firewall':
            expires = (datetime.now() + timedelta(days=30)).isoformat()
            self.update_user(user_id, platform, firewall_used=0, firewall_expires=expires)
        elif bonus_type == 'invisible':
            self.cursor.execute("""
                INSERT INTO user_bonuses (user_id, bonus_type, expires, data, platform)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, 'invisible', expires, json.dumps({'uses_left': 999}), platform))
        
        self.add_neons(user_id, -price_neons, platform)
        self.conn.commit()
        return True
    
    def use_glitch_hammer(self, user_id: int, chat_id: int, target_id: int, platform: str = "telegram") -> bool:
        self.cursor.execute("""
            SELECT * FROM user_bonuses 
            WHERE user_id = ? AND bonus_type = 'glitch_hammer' AND platform = ? AND (expires IS NULL OR expires > ?)
        """, (user_id, platform, datetime.now().isoformat()))
        bonus = self.cursor.fetchone()
        
        if not bonus:
            return False
        
        data = json.loads(bonus[5])
        if data.get('uses_left', 0) <= 0:
            return False
        
        data['uses_left'] -= 1
        if data['uses_left'] <= 0:
            self.cursor.execute("DELETE FROM user_bonuses WHERE id = ?", (bonus[0],))
        else:
            self.cursor.execute("UPDATE user_bonuses SET data = ? WHERE id = ?", (json.dumps(data), bonus[0]))
        
        self.conn.commit()
        return True
    
    def has_invisible_bonus(self, user_id: int, platform: str = "telegram") -> bool:
        self.cursor.execute("""
            SELECT * FROM user_bonuses 
            WHERE user_id = ? AND bonus_type = 'invisible' AND platform = ? AND (expires IS NULL OR expires > ?)
        """, (user_id, platform, datetime.now().isoformat()))
        return self.cursor.fetchone() is not None
    
    def is_invisible_banned(self, chat_id: int, user_id: int) -> bool:
        self.cursor.execute("SELECT * FROM invisible_bans WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
        return self.cursor.fetchone() is not None
    
    # ===== МЕТОДЫ ДЛЯ ГОЛОСОВАНИЙ =====
    def create_ban_vote(self, chat_id: int, target_id: int, created_by: int, required_votes: int, min_rank: int) -> int:
        self.cursor.execute("""
            INSERT INTO ban_votes (chat_id, target_id, created_by, required_votes, min_rank)
            VALUES (?, ?, ?, ?, ?)
        """, (chat_id, target_id, created_by, required_votes, min_rank))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def vote_for_ban(self, vote_id: int, user_id: int, vote: bool) -> bool:
        """Проголосовать за бан"""
        self.cursor.execute("SELECT * FROM ban_votes WHERE id = ? AND status = 'active'", (vote_id,))
        vote_data = self.cursor.fetchone()
        if not vote_data:
            return False
        
        voters = json.loads(vote_data[9])
        if user_id in voters:
            return False
        
        voters.append(user_id)
        
        if vote:
            new_for = vote_data[7] + 1
            new_against = vote_data[8]
        else:
            new_for = vote_data[7]
            new_against = vote_data[8] + 1
        
        self.cursor.execute("""
            UPDATE ban_votes 
            SET votes_for = ?, votes_against = ?, voters = ?
            WHERE id = ?
        """, (new_for, new_against, json.dumps(voters), vote_id))
        self.conn.commit()
        return True
    
    # ===== МЕТОДЫ ДЛЯ ПАР (ШИППЕРИНГ) =====
    def create_pair(self, chat_id: int, user1_id: int, user2_id: int) -> bool:
        try:
            self.cursor.execute("""
                INSERT INTO pairs (chat_id, user1_id, user2_id)
                VALUES (?, ?, ?)
            """, (chat_id, user1_id, user2_id))
            self.conn.commit()
            return True
        except:
            return False
    
    def get_chat_pairs(self, chat_id: int) -> List[Dict]:
        self.cursor.execute("""
            SELECT p.*, u1.first_name as name1, u2.first_name as name2
            FROM pairs p
            JOIN users u1 ON p.user1_id = u1.id
            JOIN users u2 ON p.user2_id = u2.id
            WHERE p.chat_id = ?
        """, (chat_id,))
        return [dict(row) for row in self.cursor.fetchall()]
    
    # ===== СООБЩЕНИЯ =====
    def save_message(self, user_id: int, username: str, first_name: str, text: str, chat_id: int, chat_title: str, platform: str = "telegram"):
        self.cursor.execute('''
            INSERT INTO messages (user_id, username, first_name, message_text, chat_id, chat_title, platform)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, text, chat_id, chat_title, platform))
        
        today = datetime.now().date().isoformat()
        
        # ИСПРАВЛЕНО: вместо ON CONFLICT используем проверку
        self.cursor.execute('''
            SELECT id FROM daily_stats 
            WHERE user_id = ? AND date = ? AND platform = ?
        ''', (user_id, today, platform))
        exists = self.cursor.fetchone()
        
        if exists:
            self.cursor.execute('''
                UPDATE daily_stats SET count = count + 1 
                WHERE user_id = ? AND date = ? AND platform = ?
            ''', (user_id, today, platform))
        else:
            self.cursor.execute('''
                INSERT INTO daily_stats (user_id, date, count, platform)
                VALUES (?, ?, 1, ?)
            ''', (user_id, today, platform))
        
        # ИСПРАВЛЕНО: для users тоже
        self.cursor.execute('''
            SELECT id FROM users WHERE telegram_id = ? AND platform = ?
        ''', (user_id, platform))
        user_exists = self.cursor.fetchone()
        
        if user_exists:
            self.cursor.execute('''
                UPDATE users SET 
                    last_seen = CURRENT_TIMESTAMP,
                    messages_count = messages_count + 1,
                    username = ?,
                    first_name = ?
                WHERE telegram_id = ? AND platform = ?
            ''', (username, first_name, user_id, platform))
        else:
            self.cursor.execute('''
                INSERT INTO users (telegram_id, username, first_name, last_seen, messages_count, platform)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, 1, ?)
            ''', (user_id, username, first_name, platform))
        
        self.conn.commit()
        
        user = self.get_user_by_id(user_id, platform)
        if user:
            msg_count = user.get('messages_count', 0) + 1
            if msg_count >= 1000:
                self.unlock_achievement(user_id, 16, platform)
            if msg_count >= 5000:
                self.unlock_achievement(user_id, 17, platform)
            if msg_count >= 10000:
                self.unlock_achievement(user_id, 18, platform)
    
    def get_weekly_stats(self, user_id: int, platform: str = "telegram") -> Tuple[List[str], List[int]]:
        days = []
        counts = []
        
        for i in range(6, -1, -1):
            date = (datetime.now() - timedelta(days=i)).date()
            day_name = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][date.weekday()]
            days.append(day_name)
            
            self.cursor.execute('''
                SELECT count FROM daily_stats
                WHERE user_id = ? AND date = ? AND platform = ?
            ''', (user_id, date.isoformat(), platform))
            row = self.cursor.fetchone()
            counts.append(row[0] if row else 0)
        
        return days, counts
    
    def add_exp(self, user_id: int, amount: int, platform: str = "telegram") -> bool:
        self.cursor.execute("UPDATE users SET exp = exp + ? WHERE id = ? AND platform = ?", (amount, user_id, platform))
        self.cursor.execute("SELECT exp, level FROM users WHERE id = ? AND platform = ?", (user_id, platform))
        row = self.cursor.fetchone()
        exp, level = row[0], row[1]
        if exp >= level * 100:
            self.cursor.execute("UPDATE users SET level = level + 1, exp = exp - ? WHERE id = ? AND platform = ?", 
                              (level * 100, user_id, platform))
            self.conn.commit()
            return True
        self.conn.commit()
        return False
    
    def add_energy(self, user_id: int, amount: int, platform: str = "telegram") -> int:
        self.cursor.execute("UPDATE users SET energy = MIN(100, energy + ?) WHERE id = ? AND platform = ?", (amount, user_id, platform))
        self.conn.commit()
        self.cursor.execute("SELECT energy FROM users WHERE id = ? AND platform = ?", (user_id, platform))
        return self.cursor.fetchone()[0]
    
    def heal(self, user_id: int, amount: int, platform: str = "telegram") -> int:
        self.cursor.execute("UPDATE users SET health = MIN(max_health, health + ?) WHERE id = ? AND platform = ?", (amount, user_id, platform))
        self.conn.commit()
        self.cursor.execute("SELECT health FROM users WHERE id = ? AND platform = ?", (user_id, platform))
        return self.cursor.fetchone()[0]
    
    def damage(self, user_id: int, amount: int, platform: str = "telegram") -> int:
        self.cursor.execute("UPDATE users SET health = MAX(0, health - ?) WHERE id = ? AND platform = ?", (amount, user_id, platform))
        self.conn.commit()
        self.cursor.execute("SELECT health FROM users WHERE id = ? AND platform = ?", (user_id, platform))
        return self.cursor.fetchone()[0]
    
    def is_vip(self, user_id: int, platform: str = "telegram") -> bool:
        self.cursor.execute("SELECT vip_until FROM users WHERE id = ? AND platform = ?", (user_id, platform))
        row = self.cursor.fetchone()
        if row and row[0]:
            return datetime.fromisoformat(row[0]) > datetime.now()
        return False
    
    def is_premium(self, user_id: int, platform: str = "telegram") -> bool:
        self.cursor.execute("SELECT premium_until FROM users WHERE id = ? AND platform = ?", (user_id, platform))
        row = self.cursor.fetchone()
        if row and row[0]:
            return datetime.fromisoformat(row[0]) > datetime.now()
        return False
    
    def set_vip(self, user_id: int, days: int, platform: str = "telegram") -> datetime:
        until = datetime.now() + timedelta(days=days)
        self.cursor.execute("UPDATE users SET vip_until = ?, role = 'vip' WHERE id = ? AND platform = ?",
                          (until.isoformat(), user_id, platform))
        self.conn.commit()
        self.unlock_achievement(user_id, 22, platform)
        return until
    
    def set_premium(self, user_id: int, days: int, platform: str = "telegram") -> datetime:
        until = datetime.now() + timedelta(days=days)
        self.cursor.execute("UPDATE users SET premium_until = ?, role = 'premium' WHERE id = ? AND platform = ?",
                          (until.isoformat(), user_id, platform))
        self.conn.commit()
        return until
    
    def set_rank(self, user_id: int, rank: int, admin_id: int, platform: str = "telegram") -> bool:
        if rank not in RANKS:
            return False
        self.cursor.execute("UPDATE users SET rank = ?, rank_name = ? WHERE id = ? AND platform = ?",
                          (rank, RANKS[rank]["name"], user_id, platform))
        self.conn.commit()
        self.log_action(admin_id, "set_rank", f"{user_id} -> {rank}", platform=platform)
        return True
    
    def get_admins(self, platform: str = "telegram") -> List[Dict]:
        self.cursor.execute("SELECT id, first_name, username, rank, rank_name FROM users WHERE rank > 0 AND platform = ? ORDER BY rank DESC", (platform,))
        return [dict(row) for row in self.cursor.fetchall()]
    
    def add_warn(self, user_id: int, admin_id: int, reason: str, platform: str = "telegram") -> int:
        self.cursor.execute("SELECT warns, warns_list FROM users WHERE id = ? AND platform = ?", (user_id, platform))
        row = self.cursor.fetchone()
        warns, warns_list = row[0], json.loads(row[1])
        warns_list.append({
            'id': len(warns_list) + 1,
            'admin_id': admin_id,
            'reason': reason,
            'date': datetime.now().isoformat()
        })
        new_warns = warns + 1
        self.cursor.execute("UPDATE users SET warns = ?, warns_list = ? WHERE id = ? AND platform = ?",
                          (new_warns, json.dumps(warns_list), user_id, platform))
        self.conn.commit()
        self.log_action(admin_id, "add_warn", f"{user_id}: {reason}", platform=platform)
        return new_warns
    
    def get_warns(self, user_id: int, platform: str = "telegram") -> List[Dict]:
        self.cursor.execute("SELECT warns_list FROM users WHERE id = ? AND platform = ?", (user_id, platform))
        row = self.cursor.fetchone()
        return json.loads(row[0]) if row and row[0] else []
    
    def remove_last_warn(self, user_id: int, admin_id: int, platform: str = "telegram") -> Optional[Dict]:
        self.cursor.execute("SELECT warns, warns_list FROM users WHERE id = ? AND platform = ?", (user_id, platform))
        row = self.cursor.fetchone()
        warns, warns_list = row[0], json.loads(row[1])
        if not warns_list:
            return None
        removed = warns_list.pop()
        self.cursor.execute("UPDATE users SET warns = ?, warns_list = ? WHERE id = ? AND platform = ?",
                          (warns - 1, json.dumps(warns_list), user_id, platform))
        self.conn.commit()
        self.log_action(admin_id, "remove_warn", f"{user_id}", platform=platform)
        return removed
    
    def mute_user(self, user_id: int, minutes: int, admin_id: int, reason: str = "", platform: str = "telegram") -> datetime:
        until = datetime.now() + timedelta(minutes=minutes)
        self.cursor.execute("UPDATE users SET mute_until = ? WHERE id = ? AND platform = ?", (until.isoformat(), user_id, platform))
        self.conn.commit()
        self.log_action(admin_id, "mute", f"{user_id} {minutes}мин: {reason}", platform=platform)
        return until
    
    def is_muted(self, user_id: int, platform: str = "telegram") -> bool:
        self.cursor.execute("SELECT mute_until FROM users WHERE id = ? AND platform = ?", (user_id, platform))
        row = self.cursor.fetchone()
        if row and row[0]:
            return datetime.fromisoformat(row[0]) > datetime.now()
        return False
    
    def unmute_user(self, user_id: int, admin_id: int, platform: str = "telegram") -> bool:
        self.cursor.execute("UPDATE users SET mute_until = NULL WHERE id = ? AND platform = ?", (user_id, platform))
        self.conn.commit()
        self.log_action(admin_id, "unmute", str(user_id), platform=platform)
        return True
    
    def get_muted_users(self, platform: str = "telegram") -> List[Dict]:
        self.cursor.execute("SELECT id, first_name, username, mute_until FROM users WHERE mute_until > ? AND platform = ?",
                          (datetime.now().isoformat(), platform))
        return [dict(row) for row in self.cursor.fetchall()]
    
    def ban_user(self, user_id: int, admin_id: int, reason: str, platform: str = "telegram") -> bool:
        try:
            now = datetime.now().isoformat()
            self.cursor.execute('''
                UPDATE users SET 
                    banned = 1,
                    ban_reason = ?,
                    ban_date = ?,
                    ban_admin = ?
                WHERE id = ? AND platform = ?
            ''', (reason, now, admin_id, user_id, platform))
            self.conn.commit()
            self.log_action(admin_id, "ban", f"{user_id}: {reason}", platform=platform)
            return True
        except Exception as e:
            logger.error(f"Ошибка при бане в БД (user_id: {user_id}): {e}")
            return False
    
    def unban_user(self, user_id: int, admin_id: int, platform: str = "telegram") -> bool:
        try:
            self.cursor.execute('''
                UPDATE users SET 
                    banned = 0,
                    ban_reason = NULL,
                    ban_date = NULL,
                    ban_admin = NULL
                WHERE id = ? AND platform = ?
            ''', (user_id, platform))
            self.conn.commit()
            self.log_action(admin_id, "unban", str(user_id), platform=platform)
            return True
        except Exception as e:
            logger.error(f"Ошибка при разбане в БД (user_id: {user_id}): {e}")
            return False
    
    def get_banlist(self, platform: str = "telegram") -> List[Dict]:
        self.cursor.execute("SELECT id, first_name, username FROM users WHERE banned = 1 AND platform = ? ORDER BY ban_date DESC", (platform,))
        return [dict(row) for row in self.cursor.fetchall()]
    
    def add_to_blacklist(self, word: str, admin_id: int, platform: str = "telegram") -> bool:
        try:
            self.cursor.execute("INSERT INTO blacklist (word, added_by) VALUES (?, ?)", (word.lower(), admin_id))
            self.conn.commit()
            self.log_action(admin_id, "add_blacklist", word, platform=platform)
            return True
        except:
            return False
    
    def remove_from_blacklist(self, word: str, admin_id: int, platform: str = "telegram") -> bool:
        self.cursor.execute("DELETE FROM blacklist WHERE word = ?", (word.lower(),))
        self.conn.commit()
        self.log_action(admin_id, "remove_blacklist", word, platform=platform)
        return self.cursor.rowcount > 0
    
    def get_blacklist(self) -> List[str]:
        self.cursor.execute("SELECT word FROM blacklist ORDER BY word")
        return [row[0] for row in self.cursor.fetchall()]
    
    def is_word_blacklisted(self, text: str) -> bool:
        words = self.get_blacklist()
        text_lower = text.lower()
        for word in words:
            if word in text_lower:
                return True
        return False
    
    def get_top(self, field: str, limit: int = 10, platform: str = "telegram") -> List[Tuple]:
        # Защита от SQL-инъекций - проверяем, что поле допустимо
        if field not in ALLOWED_SORT_FIELDS:
            field = 'coins'  # Значение по умолчанию
        
        self.cursor.execute(f"SELECT first_name, nickname, {field} FROM users WHERE platform = ? ORDER BY {field} DESC LIMIT ?", (platform, limit))
        return self.cursor.fetchall()
    
    def add_daily_streak(self, user_id: int, platform: str = "telegram") -> int:
        today = datetime.now().date()
        self.cursor.execute("SELECT last_daily, daily_streak FROM users WHERE id = ? AND platform = ?", (user_id, platform))
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
        
        self.cursor.execute("UPDATE users SET daily_streak = ?, last_daily = ? WHERE id = ? AND platform = ?",
                          (streak, datetime.now().isoformat(), user_id, platform))
        self.conn.commit()
        
        if streak >= 7:
            self.unlock_achievement(user_id, 19, platform)
        if streak >= 30:
            self.unlock_achievement(user_id, 20, platform)
        if streak >= 100:
            self.unlock_achievement(user_id, 21, platform)
        
        return streak
    
    def get_bosses(self, alive_only: bool = True) -> List[Dict]:
        if alive_only:
            self.cursor.execute("SELECT * FROM bosses WHERE is_alive = 1 ORDER BY level")
        else:
            self.cursor.execute("SELECT * FROM bosses ORDER BY level")
        return [dict(row) for row in self.cursor.fetchall()]
    
    def get_boss(self, boss_id: int) -> Optional[Dict]:
        self.cursor.execute("SELECT * FROM bosses WHERE id = ?", (boss_id,))
        row = self.cursor.fetchone()
        return dict(row) if row else None
    
    def damage_boss(self, boss_id: int, damage: int) -> bool:
        self.cursor.execute("UPDATE bosses SET health = health - ? WHERE id = ?", (damage, boss_id))
        self.cursor.execute("SELECT health FROM bosses WHERE id = ?", (boss_id,))
        health = self.cursor.fetchone()[0]
        if health <= 0:
            self.cursor.execute("UPDATE bosses SET is_alive = 0, respawn_time = ? WHERE id = ?",
                              ((datetime.now() + timedelta(hours=1)).isoformat(), boss_id))
            self.conn.commit()
            return True
        self.conn.commit()
        return False
    
    def respawn_bosses(self):
        self.cursor.execute("UPDATE bosses SET health = max_health, is_alive = 1, respawn_time = NULL")
        self.conn.commit()
    
    def add_boss_kill(self, user_id: int, platform: str = "telegram"):
        self.cursor.execute("UPDATE users SET boss_kills = boss_kills + 1 WHERE id = ? AND platform = ?", (user_id, platform))
        self.conn.commit()
        
        user = self.get_user_by_id(user_id, platform)
        kills = user.get('boss_kills', 0) + 1
        if kills >= 10:
            self.unlock_achievement(user_id, 13, platform)
        if kills >= 50:
            self.unlock_achievement(user_id, 14, platform)
        if kills >= 200:
            self.unlock_achievement(user_id, 15, platform)
    
    def create_duel(self, challenger_id: int, opponent_id: int, bet: int, platform: str = "telegram") -> int:
        self.cursor.execute('''
            INSERT INTO duels (challenger_id, opponent_id, bet, platform)
            VALUES (?, ?, ?, ?)
        ''', (challenger_id, opponent_id, bet, platform))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_duel(self, duel_id: int, platform: str = "telegram") -> Optional[Dict]:
        self.cursor.execute("SELECT * FROM duels WHERE id = ? AND platform = ?", (duel_id, platform))
        row = self.cursor.fetchone()
        return dict(row) if row else None
    
    def update_duel(self, duel_id: int, platform: str = "telegram", kwargs):
        for key, value in kwargs.items():
            self.cursor.execute(f"UPDATE duels SET {key} = ? WHERE id = ? AND platform = ?", (value, duel_id, platform))
        self.conn.commit()
    
    def log_action(self, user_id: int, action: str, details: str = "", chat_id: int = None, platform: str = "telegram"):
        self.cursor.execute('''
            INSERT INTO logs (user_id, action, details, chat_id, platform, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, action, details, chat_id, platform, datetime.now().isoformat()))
        self.conn.commit()
    
    # ===== ТАЙНЫЙ ОРДЕН =====
    def is_in_order(self, user_id: int, chat_id: int, platform: str = "telegram") -> bool:
        """Проверяет, состоит ли пользователь в ордене"""
        self.cursor.execute('''
            SELECT members FROM order_data 
            WHERE chat_id = ? AND platform = ? AND is_active = 1
        ''', (chat_id, platform))
        row = self.cursor.fetchone()
        
        if not row:
            return False
        
        members = json.loads(row[0])
        return user_id in members
    
    def get_user_rank(self, user_id: int, chat_id: int, platform: str = "telegram") -> Dict:
        """Получает ранг пользователя в ордене"""
        self.cursor.execute('''
            SELECT rank, rank_name, total_points FROM order_ranks
            WHERE user_id = ? AND chat_id = ? AND platform = ?
        ''', (user_id, chat_id, platform))
        row = self.cursor.fetchone()
        
        if row:
            return {"rank": row[0], "name": row[1], "points": row[2]}
        
        return {"rank": 0, "name": "👤 Кандидат", "points": 0}
    
    def calculate_rank(self, points: int) -> Dict:
        """Определяет ранг по количеству очков"""
        ranks = [
            (0, 0, "👤 Кандидат"),
            (100, 1, "👁️ Наблюдатель"),
            (250, 2, "🌙 Тень"),
            (500, 3, "🕳️ Бездна"),
            (1000, 4, "🔮 Провидец"),
            (2500, 5, "🧙 Мистик"),
            (5000, 6, "⚔️ Страж"),
            (10000, 7, "👑 Хранитель"),
            (25000, 8, "🗿 Легенда"),
            (50000, 9, "💀 Спектр"),
            (100000, 10, "👁️ Всевидящий")
        ]
        
        for min_points, rank_num, rank_name in reversed(ranks):
            if points >= min_points:
                return {"rank": rank_num, "name": rank_name}
        
        return {"rank": 0, "name": "👤 Кандидат"}
    
    def add_order_points(self, user_id: int, chat_id: int, points: int, reason: str = "", platform: str = "telegram"):
        """Начисляет очки ордена пользователю"""
        self.cursor.execute('''
            SELECT total_points FROM order_ranks
            WHERE user_id = ? AND chat_id = ? AND platform = ?
        ''', (user_id, chat_id, platform))
        row = self.cursor.fetchone()
        
        if row:
            new_total = row[0] + points
            new_rank = self.calculate_rank(new_total)
            
            self.cursor.execute('''
                UPDATE order_ranks 
                SET total_points = ?, rank = ?, rank_name = ?
                WHERE user_id = ? AND chat_id = ? AND platform = ?
            ''', (new_total, new_rank["rank"], new_rank["name"], user_id, chat_id, platform))
        else:
            new_rank = self.calculate_rank(points)
            self.cursor.execute('''
                INSERT INTO order_ranks (user_id, chat_id, total_points, rank, rank_name, platform)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, chat_id, points, new_rank["rank"], new_rank["name"], platform))
        
        self.conn.commit()
        return new_rank
    
    def start_order_cycle(self, chat_id: int, platform: str = "telegram") -> Tuple[List[int], int]:
        """Запускает новый цикл ордена"""
        self.cursor.execute('''
            SELECT DISTINCT user_id FROM messages
            WHERE chat_id = ? AND platform = ?
            GROUP BY user_id
            HAVING COUNT(*) > 5
            ORDER BY RANDOM()
            LIMIT 5
        ''', (chat_id, platform))
        
        members = [row[0] for row in self.cursor.fetchall()]
        
        if len(members) < 5:
            self.cursor.execute('''
                SELECT DISTINCT user_id FROM messages
                WHERE chat_id = ? AND platform = ?
                ORDER BY RANDOM()
                LIMIT ?
            ''', (chat_id, platform, 5 - len(members)))
            more_members = [row[0] for row in self.cursor.fetchall()]
            members.extend(more_members)
        
        self.cursor.execute('''
            SELECT cycle_number FROM order_data WHERE chat_id = ? AND platform = ?
        ''', (chat_id, platform))
        row = self.cursor.fetchone()
        
        if row:
            cycle = row[0] + 1
            self.cursor.execute('''
                UPDATE order_data 
                SET cycle_number = ?, is_active = 1, members = ?, revealed = 0,
                    revelation_time = datetime('now', '+7 days')
                WHERE chat_id = ? AND platform = ?
            ''', (cycle, json.dumps(members), chat_id, platform))
        else:
            cycle = 1
            self.cursor.execute('''
                INSERT INTO order_data (chat_id, cycle_number, is_active, members, revelation_time, platform)
                VALUES (?, ?, 1, ?, datetime('now', '+7 days'), ?)
            ''', (chat_id, cycle, json.dumps(members), platform))
        
        self.conn.commit()
        
        return members, cycle
    
    def reveal_order(self, chat_id: int, platform: str = "telegram") -> Optional[Dict]:
        """Раскрывает орден досрочно"""
        self.cursor.execute('''
            SELECT members, points, cycle_number FROM order_data 
            WHERE chat_id = ? AND platform = ? AND is_active = 1
        ''', (chat_id, platform))
        row = self.cursor.fetchone()
        
        if not row:
            return None
        
        members = json.loads(row[0])
        points_data = json.loads(row[1]) if row[1] else {}
        cycle = row[2]
        
        sorted_members = sorted(members, key=lambda x: points_data.get(str(x), 0), reverse=True)
        
        self.cursor.execute('''
            UPDATE order_data SET revealed = 1, is_active = 0
            WHERE chat_id = ? AND platform = ?
        ''', (chat_id, platform))
        self.conn.commit()
        
        return {
            "members": sorted_members,
            "points": points_data,
            "cycle": cycle
        }
    
    # ===== НОВЫЕ МЕТОДЫ ДЛЯ КВЕСТОВ =====
    
    def assign_daily_quests(self, user_id: int, platform: str = "telegram") -> List[Dict]:
        """Назначает ежедневные квесты пользователю"""
        # Очищаем старые ежедневные квесты
        self.cursor.execute('''
            DELETE FROM user_quests 
            WHERE user_id = ? AND platform = ? AND quest_id IN 
            (SELECT id FROM quests WHERE type = 'daily')
        ''', (user_id, platform))
        
        # Получаем случайные ежедневные квесты
        self.cursor.execute('''
            SELECT * FROM quests 
            WHERE type = 'daily' AND active = 1
            ORDER BY RANDOM()
            LIMIT ?
        ''', (MAX_ACTIVE_QUESTS,))
        
        quests = self.cursor.fetchall()
        assigned = []
        
        expires_at = (datetime.now() + timedelta(days=1)).isoformat()
        
        for quest in quests:
            quest_dict = dict(quest)
            self.cursor.execute('''
                INSERT INTO user_quests (user_id, quest_id, expires_at, platform)
                VALUES (?, ?, ?, ?)
            ''', (user_id, quest_dict['id'], expires_at, platform))
            assigned.append(quest_dict)
        
        self.conn.commit()
        return assigned
    
    def assign_weekly_quests(self, user_id: int, platform: str = "telegram") -> List[Dict]:
        """Назначает еженедельные квесты пользователю"""
        # Очищаем старые еженедельные квесты
        self.cursor.execute('''
            DELETE FROM user_quests 
            WHERE user_id = ? AND platform = ? AND quest_id IN 
            (SELECT id FROM quests WHERE type = 'weekly')
        ''', (user_id, platform))
        
        # Получаем случайные еженедельные квесты
        self.cursor.execute('''
            SELECT * FROM quests 
            WHERE type = 'weekly' AND active = 1
            ORDER BY RANDOM()
            LIMIT 2
        ''')
        
        quests = self.cursor.fetchall()
        assigned = []
        
        expires_at = (datetime.now() + timedelta(days=7)).isoformat()
        
        for quest in quests:
            quest_dict = dict(quest)
            self.cursor.execute('''
                INSERT INTO user_quests (user_id, quest_id, expires_at, platform)
                VALUES (?, ?, ?, ?)
            ''', (user_id, quest_dict['id'], expires_at, platform))
            assigned.append(quest_dict)
        
        self.conn.commit()
        return assigned
    
    def get_user_quests(self, user_id: int, platform: str = "telegram") -> List[Dict]:
        """Получает активные квесты пользователя"""
        now = datetime.now().isoformat()
        self.cursor.execute('''
            SELECT uq.*, q.name, q.description, q.type, q.condition_type, q.condition_value, 
                   q.reward_neons, q.reward_glitches, q.complexity
            FROM user_quests uq
            JOIN quests q ON uq.quest_id = q.id
            WHERE uq.user_id = ? AND uq.platform = ? AND uq.completed = 0 AND uq.expires_at > ?
        ''', (user_id, platform, now))
        return [dict(row) for row in self.cursor.fetchall()]
    
    def update_quest_progress(self, user_id: int, condition_type: str, amount: int = 1, platform: str = "telegram"):
        """Обновляет прогресс квестов пользователя"""
        quests = self.get_user_quests(user_id, platform)
        
        for quest in quests:
            if quest['condition_type'] == condition_type:
                new_progress = quest['progress'] + amount
                self.cursor.execute('''
                    UPDATE user_quests 
                    SET progress = ? 
                    WHERE id = ?
                ''', (new_progress, quest['id']))
                
                # Проверяем выполнение квеста
                if new_progress >= quest['condition_value']:
                    self.complete_quest(quest['id'], user_id, platform)
        
        self.conn.commit()
    
    def complete_quest(self, quest_id: int, user_id: int, platform: str = "telegram"):
        """Завершает квест и выдаёт награду"""
        self.cursor.execute('''
            SELECT q.* FROM user_quests uq
            JOIN quests q ON uq.quest_id = q.id
            WHERE uq.id = ?
        ''', (quest_id,))
        quest = self.cursor.fetchone()
        
        if not quest:
            return
        
        quest_dict = dict(quest)
        
        # Применяем множитель сложности для защиты от инфляции
        reward_neons = int(quest_dict['reward_neons'] * (1 + (quest_dict['complexity'] - 1) * 0.2))
        reward_glitches = int(quest_dict['reward_glitches'] * (1 + (quest_dict['complexity'] - 1) * 0.2))
        
        # Выдаём награду
        if reward_neons > 0:
            self.add_neons(user_id, reward_neons, platform)
        if reward_glitches > 0:
            self.add_glitches(user_id, reward_glitches, platform)
        
        # Обновляем статус квеста
        self.cursor.execute('''
            UPDATE user_quests 
            SET completed = 1, progress = condition_value
            WHERE id = ?
        ''', (quest_id,))
        
        # Увеличиваем счётчик выполненных квестов
        self.cursor.execute('''
            UPDATE users 
            SET completed_quests = completed_quests + 1
            WHERE id = ? AND platform = ?
        ''', (user_id, platform))
        
        self.conn.commit()
    
    # ===== НОВЫЕ МЕТОДЫ ДЛЯ БИРЖИ =====
    
    def create_exchange_order(self, user_id: int, order_type: str, currency_from: str, 
                             currency_to: str, amount: int, price: int, platform: str = "telegram") -> Optional[int]:
        """Создаёт ордер на бирже"""
        user = self.get_user_by_id(user_id, platform)
        
        # Проверяем баланс
        if currency_from == 'coins' and user['coins'] < amount:
            return None
        elif currency_from == 'neons' and user['neons'] < amount:
            return None
        
        # Блокируем средства
        if currency_from == 'coins':
            self.add_coins(user_id, -amount, platform)
        else:
            self.add_neons(user_id, -amount, platform)
        
        self.cursor.execute('''
            INSERT INTO exchange_orders (user_id, type, currency_from, currency_to, amount, price, platform)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, order_type, currency_from, currency_to, amount, price, platform))
        
        order_id = self.cursor.lastrowid
        self.conn.commit()
        
        # Пытаемся выполнить ордер
        asyncio.create_task(self.match_exchange_orders())
        
        return order_id
    
    def match_exchange_orders(self):
        """Сопоставляет ордера на бирже"""
        # Получаем активные ордера на покупку и продажу
        self.cursor.execute('''
            SELECT * FROM exchange_orders 
            WHERE status = 'active' AND filled < amount
            ORDER BY price DESC, created_at ASC
        ''')
        orders = self.cursor.fetchall()
        
        buy_orders = [o for o in orders if o[2] == 'buy']
        sell_orders = [o for o in orders if o[2] == 'sell']
        
        for buy in buy_orders:
            for sell in sell_orders:
                if buy[4] != sell[4]:  # Разные валютные пары
                    continue
                
                if buy[5] >= sell[5]:  # Цена покупки >= цены продажи
                    # Совершаем сделку по цене продажи
                    price = sell[5]
                    max_amount = min(buy[6] - buy[7], sell[6] - sell[7])
                    
                    if max_amount > 0:
                        self.execute_exchange_trade(buy[0], sell[0], price, max_amount)
                        break
        
        self.conn.commit()
    
    def execute_exchange_trade(self, buy_order_id: int, sell_order_id: int, price: int, amount: int):
        """Исполняет сделку на бирже"""
        self.cursor.execute("SELECT * FROM exchange_orders WHERE id = ?", (buy_order_id,))
        buy = self.cursor.fetchone()
        
        self.cursor.execute("SELECT * FROM exchange_orders WHERE id = ?", (sell_order_id,))
        sell = self.cursor.fetchone()
        
        if not buy or not sell:
            return
        
        # Рассчитываем комиссию
        commission = int(amount * price * EXCHANGE_COMMISSION)
        
        # Переводим средства
        if buy[3] == 'coins':  # Покупаем неоны за монеты
            total_cost = amount * price
            # Продавец получает монеты (за вычетом комиссии)
            self.add_coins(sell[1], total_cost - commission, sell[9])
            # Покупатель получает неоны
            self.add_neons(buy[1], amount, buy[9])
        else:  # Покупаем монеты за неоны
            total_cost = amount * price
            # Продавец получает неоны (за вычетом комиссии)
            self.add_neons(sell[1], total_cost - commission, sell[9])
            # Покупатель получает монеты
            self.add_coins(buy[1], amount, buy[9])
        
        # Обновляем ордера
        new_filled_buy = buy[7] + amount
        new_filled_sell = sell[7] + amount
        
        self.cursor.execute('''
            UPDATE exchange_orders 
            SET filled = ?, status = CASE WHEN filled >= amount THEN 'completed' ELSE 'active' END
            WHERE id = ?
        ''', (new_filled_buy, buy_order_id))
        
        self.cursor.execute('''
            UPDATE exchange_orders 
            SET filled = ?, status = CASE WHEN filled >= amount THEN 'completed' ELSE 'active' END
            WHERE id = ?
        ''', (new_filled_sell, sell_order_id))
        
        # Сохраняем в историю
        self.cursor.execute('''
            INSERT INTO exchange_history (price, volume)
            VALUES (?, ?)
        ''', (price, amount))
        
        # Обновляем объём торгов пользователей
        self.cursor.execute('''
            UPDATE users SET exchange_volume = exchange_volume + ? WHERE id = ?
        ''', (amount * price, buy[1]))
        
        self.cursor.execute('''
            UPDATE users SET exchange_volume = exchange_volume + ? WHERE id = ?
        ''', (amount * price, sell[1]))
        
        self.conn.commit()
    
    def get_exchange_stats(self) -> Dict:
        """Получает статистику биржи"""
        # Текущий курс (средняя цена последних сделок)
        self.cursor.execute('''
            SELECT AVG(price) FROM exchange_history 
            ORDER BY created_at DESC LIMIT 10
        ''')
        avg_price = self.cursor.fetchone()[0] or 10  # Начальный курс: 10 монет за неон
        
        # Объём за последние 24 часа
        day_ago = (datetime.now() - timedelta(days=1)).isoformat()
        self.cursor.execute('''
            SELECT SUM(volume) FROM exchange_history 
            WHERE created_at > ?
        ''', (day_ago,))
        volume_24h = self.cursor.fetchone()[0] or 0
        
        # Активные ордера
        self.cursor.execute('''
            SELECT COUNT(*) FROM exchange_orders WHERE status = 'active'
        ''')
        active_orders = self.cursor.fetchone()[0]
        
        return {
            'price': round(avg_price, 2),
            'volume_24h': volume_24h,
            'active_orders': active_orders
        }
    
    def cancel_exchange_order(self, order_id: int, user_id: int, platform: str = "telegram") -> bool:
        """Отменяет ордер и возвращает средства"""
        self.cursor.execute('''
            SELECT * FROM exchange_orders 
            WHERE id = ? AND user_id = ? AND platform = ? AND status = 'active'
        ''', (order_id, user_id, platform))
        order = self.cursor.fetchone()
        
        if not order:
            return False
        
        # Возвращаем неизрасходованные средства
        remaining = order[6] - order[7]
        if remaining > 0:
            if order[3] == 'coins':
                self.add_coins(user_id, remaining, platform)
            else:
                self.add_neons(user_id, remaining, platform)
        
        self.cursor.execute('''
            UPDATE exchange_orders SET status = 'cancelled' WHERE id = ?
        ''', (order_id,))
        self.conn.commit()
        
        return True
    
    def close(self):
        self.conn.close()

# ========== ИНИЦИАЛИЗАЦИЯ БД ==========
db = Database()

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
        self.toxic_users = defaultdict(int)
        self.blocked_users = set()
        
        if GROQ_AVAILABLE and api_key:
            try:
                self.client = Groq(api_key=api_key)
                self.async_client = AsyncGroq(api_key=api_key)
                self.is_available = True
                logger.info("✅ Groq AI инициализирован (УЛУЧШЕННАЯ ВЕРСИЯ)")
            except Exception as e:
                logger.error(f"❌ Ошибка инициализации Groq: {e}")
                self.is_available = False
        
        # Базовый системный промпт
        self.base_system_prompt = """ТЫ — СПЕКТР, УМНЫЙ ПОМОЩНИК В TELEGRAM БОТЕ. ТВОЯ ЗАДАЧА - ПОМОГАТЬ ПОЛЬЗОВАТЕЛЯМ, ОТВЕЧАТЬ НА ВОПРОСЫ И УЧАСТВОВАТЬ В ИГРАХ.

ТВОЙ ХАРАКТЕР:
- Ты дружелюбный и отзывчивый помощник
- Отвечаешь кратко и по делу, без лишних эмодзи
- Знаешь весь функционал бота и можешь объяснить команды
- В играх (мафия, дуэли, орден) действуешь как ведущий

ВАЖНЫЕ ПРАВИЛА:
1. НЕ используй эмодзи в каждом сообщении - максимум 1-2, если уместно
2. НЕ начинай сообщения со слова "Спектр" - просто отвечай
3. В мафии и ордене общайся с игроками в ЛС, а не в общем чате
4. Если не знаешь ответа - честно скажи об этом
5. Будь вежливым, но не навязчивым"""
        
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
            
            # Получаем промпт для чата (если есть кастомный)
            system_prompt = self.chat_prompts[chat_id] if chat_id else self.base_system_prompt
            
            # Добавляем информацию о пользователе и контекст
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
            
            # Сохраняем в контекст
            self.contexts[user_id].append(f"User: {message}")
            self.contexts[user_id].append(f"AI: {response}")
            
            # Убираем возможное "Спектр:" в начале ответа
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
        """Получает ответ от AI для игровых сценариев"""
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
        """Устанавливает кастомный промпт для чата"""
        self.chat_prompts[chat_id] = prompt
    
    async def get_reaction(self, message: str) -> str:
        """Возвращает эмодзи-реакцию для сообщения (только для важных случаев)"""
        msg_lower = message.lower()
        
        # Только для особых случаев
        if '?' in message:
            return '❓'
        elif any(word in msg_lower for word in ['победа', 'выиграл', 'красава']):
            return '🏆'
        elif any(word in msg_lower for word in ['поздравь', 'спасибо']):
            return '✨'
        
        return ''
    
    async def close(self):
        pass

# ========== ИНИЦИАЛИЗАЦИЯ AI ==========
ai = None
if GROQ_API_KEY and GROQ_AVAILABLE:
    try:
        ai = GroqAI(GROQ_API_KEY)
        logger.info("✅ Groq AI инициализирован (УЛУЧШЕННАЯ ВЕРСИЯ)")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации AI: {e}")
        ai = None
else:
    logger.warning("⚠️ Groq AI не подключен (нет API ключа)")

# ========== КЛАСС МАФИИ (УЛУЧШЕННАЯ ВЕРСИЯ) ==========
class MafiaRole:
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
        self.status = "waiting"  # waiting, starting, night, day, ended
        self.players = []
        self.players_data = {}
        self.roles = {}
        self.alive = {}
        self.day = 1
        self.phase = "night"
        self.votes = {}
        self.night_actions = {
            "mafia_kill": None,
            "doctor_save": None,
            "commissioner_check": None,
            "maniac_kill": None
        }
        self.message_id = None
        self.start_time = None
        self.confirmed_players = []
    
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
    
    def get_role_description(self, role: str) -> str:
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
        
        self.night_actions = {
            "mafia_kill": None,
            "doctor_save": None,
            "commissioner_check": None,
            "maniac_kill": None
        }
        
        return {"killed": killed}
    
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
            'roles': json.dumps(self.roles),
            'alive': json.dumps(self.alive),
            'votes': json.dumps(self.votes),
            'night_actions': json.dumps(self.night_actions),
            'message_id': self.message_id,
            'confirmed_players': json.dumps(self.confirmed_players)
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
        self.roles = json.loads(data['roles'])
        self.alive = json.loads(data['alive'])
        self.votes = json.loads(data['votes'])
        self.night_actions = json.loads(data['night_actions'])
        self.message_id = data.get('message_id')
        self.confirmed_players = json.loads(data.get('confirmed_players', '[]'))

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

# ========== ИНИЦИАЛИЗАЦИЯ VK ==========
vk_bot = None
if VK_TOKEN and VK_AVAILABLE:
    try:
        vk_bot = VKBot(VK_TOKEN, VK_GROUP_ID)
        logger.info("✅ VK бот готов к работе")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации VK: {e}")
        vk_bot = None

# ========== ОСНОВНОЙ КЛАСС БОТА ==========
class SpectrumBot:
    def __init__(self):
        self.db = db
        self.ai = ai
        self.vk = vk_bot
        self.spam_tracker = defaultdict(list)
        self.app = Application.builder().token(TOKEN).build()
        self.start_time = datetime.now()
        self.games_in_progress = {}
        self.mafia_games = {}  # chat_id -> MafiaGame (новая версия)
        self.duels_in_progress = {}
        self.boss_fights = {}
        self.active_ban_votes = {}
        self.user_contexts = defaultdict(dict)
        self.setup_handlers()
        logger.info(f"✅ Бот {BOT_NAME} инициализирован")

    # ===== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ =====
    
    async def get_ai_response(self, user_id: int, message: str, context_type: str = "normal", 
                             username: str = "Пользователь", chat_id: int = None, kwargs) -> Optional[str]:
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
        user = None
        
        # Проверяем reply
        if update.message.reply_to_message:
            target_id = update.message.reply_to_message.from_user.id
            target_data = self.db.get_user(target_id, platform=platform)
            return self.db.get_user_by_id(target_data['id'], platform)
        
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
            [InlineKeyboardButton("🎁 Бонусы", callback_data="bonuses_menu")]
        ])
        
        text = f"""
👨‍💼 [Spectrum | Чат-менеджер](https://t.me/{BOT_USERNAME}) приветствует Вас!

Я могу предложить следующие темы:

1). [установка](https://teletype.in/@nobucraft/2_pbVPOhaYo) — инструкция установки Спектра;
2). [команды](https://teletype.in/@nobucraft/h0ZU9C1yXNS) — список команд бота;
3). что такое неоны — неоны, виртуальная валюта, как её получить;
4). [бонусы](https://teletype.in/@nobucraft/60hXq-x3h6S) — какие есть бонусы во вселенной Спектра;
5). мой спам — проверить, есть ли вы в базе «Спектр-антиспам».

[Список всех команд с их описанием](https://teletype.in/@nobucraft/h0ZU9C1yXNS)
[Канал](https://t.me/Spectrum_Game) с важными новостями.
[Канал с полезными статьями](https://t.me/Spectrum_poleznoe)

🔈 Для вызова клавиатуры с основными темами, введите `начать` или `помощь`.
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
            await update.message.reply_text("❌ AI не подключен")
            return
        
        await update.message.reply_text("🤖 AI работает!")
        
        # Тестовый запрос
        response = await self.ai.get_response(
            update.effective_user.id,
            "Привет, как дела?",
            update.effective_user.first_name,
            force_response=True
        )
        
        if response:
            await update.message.reply_text(f"🤖 Ответ: {response}")
        else:
            await update.message.reply_text("❌ AI не ответил")
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда помощи"""
        text = (
            f"{s.header('СПРАВКА')}\n"
            f"{s.section('📌 ОСНОВНЫЕ')}"
            f"{s.cmd('start', 'начать')}\n"
            f"{s.cmd('menu', 'меню с цифрами')}\n"
            f"{s.cmd('profile', 'профиль')}\n"
            f"{s.cmd('id', 'узнать свой ID')}\n\n"
            
            f"{s.section('🤖 ИСКУССТВЕННЫЙ ИНТЕЛЛЕКТ')}"
            f"{s.cmd('Спектр [вопрос]', 'задать вопрос AI (в группах)')}\n"
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
            
            f"👑 Владелец: {OWNER_USERNAME}"
        )
        
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
    
    async def show_chart(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать график активности"""
        user = update.effective_user
        
        await update.message.chat.send_action(action="upload_photo")
        
        days, counts = self.db.get_weekly_stats(user.id)
        
        chart = ChartGenerator.create_activity_chart(days, counts, user.first_name)
        
        await update.message.reply_photo(
            photo=chart,
            caption=f"📊 Активность {user.first_name} за последние 7 дней",
            parse_mode='Markdown'
        )
    
    async def cmd_random_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Поиск случайной беседы как в Ирисе"""
        
        # Получаем случайный чат из базы
        self.db.cursor.execute("""
            SELECT cs.chat_id, cs.chat_name, cs.chat_code, 
                   COUNT(DISTINCT m.user_id) as members,
                   MIN(m.timestamp) as created,
                   SUM(CASE WHEN m.timestamp > datetime('now', '-1 day') THEN 1 ELSE 0 END) as day_active,
                   SUM(CASE WHEN m.timestamp > datetime('now', '-7 day') THEN 1 ELSE 0 END) as week_active,
                   SUM(CASE WHEN m.timestamp > datetime('now', '-30 day') THEN 1 ELSE 0 END) as month_active,
                   COUNT(m.id) as total_messages
            FROM chat_settings cs
            LEFT JOIN messages m ON cs.chat_id = m.chat_id
            WHERE cs.chat_code IS NOT NULL
            GROUP BY cs.chat_id
            ORDER BY RANDOM()
            LIMIT 1
        """)
        
        row = self.db.cursor.fetchone()
        
        if not row:
            await update.message.reply_text(
                "🍬 В базе пока нет бесед**\n\n"
                "Добавьте бота в чат и введите `!привязать`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        chat = dict(row)
        
        # Форматируем дату создания
        created_date = datetime.fromisoformat(chat['created']).strftime("%d.%m.%Y") if chat['created'] else "неизвестно"
        
        # Определяем тип чата (заглушка, в реальности нужно получать из Telegram)
        chat_type = "открытый" if random.choice([True, False]) else "закрытый"
        entry_type = "свободный" if random.choice([True, False]) else "по заявкам"
        
        # Форматируем активность
        day_active = chat['day_active'] or 0
        week_active = chat['week_active'] or 0
        month_active = chat['month_active'] or 0
        total = chat['total_messages'] or 0
        
        # Создаем клавиатуру
        keyboard_buttons = [
            InlineKeyboardButton("📩 Попроситься в чат", url=f"https://t.me/{chat['chat_name']}" if chat['chat_name'] else None),
            InlineKeyboardButton("📇 Карточка в каталоге", callback_data=f"chat_card_{chat['chat_id']}"),
            InlineKeyboardButton("🔄 Другую беседу", callback_data="random_chat")
        ]
        
        keyboard = InlineKeyboardMarkup(self._split_buttons(keyboard_buttons, 1))
        
        text = (
            f"🍬 Случайная беседа\n\n"
            f"📢 Чат «{chat['chat_name'] or 'Без названия'}»\n"
            f"👤 Попроситься в чат: [ссылка]\n"
            f"📇 Карточка в Спектр-каталоге\n\n"
            f"🏆 Спектр-коин рейтинг: {random.randint(100000, 999999):,}\n"
            f"📅 Создан: {created_date}\n"
            f"👥 Участников: {chat['members'] or 0} участника\n"
            f"🔒 Тип: {chat_type}, вход {entry_type}\n"
            f"📊 Актив: {day_active} | {week_active} | {month_active} | {total:,}"
        )
        
        await update.message.reply_text(
            text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def cmd_top_chats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Топ бесед по активности"""
        
        period = "день"
        if context.args:
            if context.args[0] in ["день", "неделя", "месяц", "всё"]:
                period = context.args[0]
        
        time_filter = {
            "день": "datetime('now', '-1 day')",
            "неделя": "datetime('now', '-7 day')",
            "месяц": "datetime('now', '-30 day')",
            "всё": "datetime('2000-01-01')"
        }.get(period, "datetime('now', '-1 day')")
        
        self.db.cursor.execute(f"""
            SELECT cs.chat_name, COUNT(m.id) as msg_count
            FROM chat_settings cs
            LEFT JOIN messages m ON cs.chat_id = m.chat_id AND m.timestamp > {time_filter}
            WHERE cs.chat_code IS NOT NULL
            GROUP BY cs.chat_id
            HAVING msg_count > 0
            ORDER BY msg_count DESC
            LIMIT 10
        """)
        
        chats = self.db.cursor.fetchall()
        
        if not chats:
            await update.message.reply_text(
                f"📊 Нет данных за {period}",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        text = f"🏆 ТОП БЕСЕД ЗА {period.upper()}**\n\n"
        
        for i, chat in enumerate(chats, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            name = chat[0] or f"Чат {i}"
            text += f"{medal} {name} — {chat[1]} 💬\n"
        
        keyboard_buttons = [
            InlineKeyboardButton("📅 День", callback_data="top_chats_day"),
            InlineKeyboardButton("📆 Неделя", callback_data="top_chats_week"),
            InlineKeyboardButton("📆 Месяц", callback_data="top_chats_month"),
            InlineKeyboardButton("🔄 Случайная беседа", callback_data="random_chat")
        ]
        
        keyboard = InlineKeyboardMarkup(self._split_buttons(keyboard_buttons, 2))
        
        await update.message.reply_text(
            text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )

    async def cmd_setup_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация об установке"""
        text = (
            "🔧 УСТАНОВКА БОТА\n\n"
            "1️⃣ Добавьте бота в группу\n"
            "2️⃣ Сделайте бота администратором\n"
            "3️⃣ Введите `!привязать` для привязки чата\n"
            "4️⃣ Настройте приветствие: `+приветствие Текст`\n"
            "5️⃣ Настройте правила: `+правила Текст`\n\n"
            "📚 Подробнее: https://telegra.ph/Iris-bot-setup"
        )
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
        
        # Ачивки
        achievements = self.db.get_user_achievements(user_data['id'])
        achievements_count = len(achievements)
        
        # Дата регистрации
        registered = datetime.fromisoformat(user_data['registered']) if user_data.get('registered') else datetime.now()
        days_in_chat = (datetime.now() - registered).days
        
        # Получаем дневную статистику
        days, counts = self.db.get_weekly_stats(user.id)
        total_messages = sum(counts)
        avg_per_day = total_messages / 7 if total_messages > 0 else 0
        
        # Генерируем график
        chart = ChartGenerator.create_activity_chart(days, counts, user.first_name)
        
        # Текст профиля
        profile_text = (
            f"# Спектр | Профиль\n\n"
            f"👤 {display_name} {title}\n"
            f"_{motto}_\n"
            f"{bio}\n\n"
            f"📊 Характеристики\n"
            f"• Ранг: {get_rank_emoji(user_data['rank'])} {user_data['rank_name']}\n"
            f"• Уровень: {user_data['level']} ({exp_progress})\n"
            f"• Монеты: {user_data['coins']:,} 💰\n"
            f"• Неоны: {user_data['neons']:,} 💜\n"
            f"• Глитчи: {user_data['glitches']:,} 🖥\n"
            f"• Энергия: {user_data['energy']}/100 ⚡️\n"
            f"• Здоровье: {user_data['health']}/{user_data['max_health']} ❤️\n\n"
            
            f"📈 Статистика\n"
            f"• За неделю: {total_messages} 💬\n"
            f"• В среднем: {avg_per_day:.1f}/день\n"
            f"• Репутация: {user_data['reputation']} ⭐️\n"
            f"• Ачивки: {achievements_count} 🏅\n"
            f"• Предупреждения: {warns}\n"
            f"• Боссов убито: {user_data['boss_kills']} 👾\n"
            f"• Друзей: {friends_count} / Врагов: {enemies_count}\n\n"
            
            f"💎 Статусы\n"
            f"• VIP: {vip_status}\n"
            f"• PREMIUM: {premium_status}\n"
            f"• Кибер-статус: {cyber_status}\n"
            f"• Турбо-драйв: {turbo_drive}\n"
            f"• РП-пакет: {rp_packet}\n\n"
            
            f"📅 Даты\n"
            f"• В чате: {days_in_chat} дней\n"
            f"• Регистрация: {registered.strftime('%d.%m.%Y')}\n"
            f"• ID: `{user.id}`"
        )
        
        # Отправляем фото с диаграммой и текстом
        await update.message.reply_photo(
            photo=chart,
            caption=profile_text,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def cmd_set_nick(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Укажите ник: /nick [ник]")
            return
        nick = " ".join(context.args)
        if len(nick) > MAX_NICK_LENGTH:
            await update.message.reply_text(f"❌ Максимальная длина: {MAX_NICK_LENGTH} символов")
            return
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], platform="telegram", nickname=nick)
        await update.message.reply_text(f"✅ Ник установлен: {nick}")
    
    async def cmd_set_title(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Укажите титул: /title [титул]")
            return
        title = " ".join(context.args)
        if len(title) > MAX_TITLE_LENGTH:
            await update.message.reply_text(f"❌ Максимальная длина: {MAX_TITLE_LENGTH} символов")
            return
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], platform="telegram", title=title)
        await update.message.reply_text(f"✅ Титул установлен: {title}")
    
    async def cmd_set_motto(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Укажите девиз: /motto [девиз]")
            return
        motto = " ".join(context.args)
        if len(motto) > MAX_MOTTO_LENGTH:
            await update.message.reply_text(f"❌ Максимальная длина: {MAX_MOTTO_LENGTH} символов")
            return
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], platform="telegram", motto=motto)
        await update.message.reply_text(f"✅ Девиз установлен: {motto}")
    
    async def cmd_set_bio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Напишите о себе: /bio [текст]")
            return
        bio = " ".join(context.args)
        if len(bio) > MAX_BIO_LENGTH:
            await update.message.reply_text(f"❌ Максимальная длина: {MAX_BIO_LENGTH} символов")
            return
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], platform="telegram", bio=bio)
        await update.message.reply_text("✅ Информация сохранена")
    
    async def cmd_set_gender(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        if text.startswith('мой пол '):
            gender = text.replace('мой пол ', '').strip().lower()
        elif context.args:
            gender = context.args[0].lower()
        else:
            await update.message.reply_text("❌ Укажите пол (м/ж/др): мой пол м")
            return
        
        if gender not in ["м", "ж", "др"]:
            await update.message.reply_text("❌ Пол должен быть 'м', 'ж' или 'др'")
            return
        
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], platform="telegram", gender=gender)
        
        gender_text = {"м": "Мужской", "ж": "Женский", "др": "Другой"}[gender]
        await update.message.reply_text(f"✅ Пол установлен: {gender_text}")
    
    async def cmd_remove_gender(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], platform="telegram", gender='не указан')
        await update.message.reply_text("✅ Пол удалён из анкеты")
    
    async def cmd_set_city(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        if text.startswith('мой город '):
            city = text.replace('мой город ', '').strip()
        elif context.args:
            city = " ".join(context.args)
        else:
            await update.message.reply_text("❌ Укажите город: мой город Москва")
            return
        
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], platform="telegram", city=city)
        await update.message.reply_text(f"✅ Город установлен: {city}")
    
    async def cmd_set_country(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Укажите страну: /country [страна]")
            return
        country = " ".join(context.args)
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], platform="telegram", country=country)
        await update.message.reply_text(f"✅ Страна установлена: {country}")
    
    async def cmd_set_birth(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        if text.startswith('мой др '):
            birth = text.replace('мой др ', '').strip().split()[0]
        elif context.args:
            birth = context.args[0]
        else:
            await update.message.reply_text("❌ Укажите дату (ДД.ММ.ГГГГ): мой др 01.01.2000")
            return
        
        if not re.match(r'\d{2}\.\d{2}\.\d{4}', birth):
            await update.message.reply_text("❌ Неверный формат. Используйте ДД.ММ.ГГГГ")
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
        
        await update.message.reply_text(f"✅ Дата рождения установлена: {birth}")
    
    async def cmd_set_age(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Укажите возраст: /age [число]")
            return
        try:
            age = int(context.args[0])
            if age < 1 or age > 150:
                await update.message.reply_text("❌ Возраст должен быть от 1 до 150")
                return
        except:
            await update.message.reply_text("❌ Возраст должен быть числом")
            return
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], platform="telegram", age=age)
        await update.message.reply_text(f"✅ Возраст установлен: {age}")
    
    async def cmd_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        await update.message.reply_text(f"🆔 Ваш ID: `{user.id}`", parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_my_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.cmd_profile(update, context)
    
    async def cmd_profile_public(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], platform="telegram", profile_visible=1)
        await update.message.reply_text("✅ Ваш профиль теперь виден всем")
    
    async def cmd_profile_private(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], platform="telegram", profile_visible=0)
        await update.message.reply_text("✅ Ваш профиль теперь скрыт от других")

    # ===== СТАТИСТИКА =====
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat
        cursor = self.db.cursor
        
        now = datetime.now()
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        # Общая статистика
        cursor.execute('''
            SELECT COUNT(DISTINCT user_id), COUNT(*) 
            FROM messages 
            WHERE chat_id = ?
        ''', (chat.id,))
        result = cursor.fetchone()
        total_users = result[0] if result else 0
        total_msgs = result[1] if result else 0
        
        # Статистика за день
        cursor.execute('''
            SELECT COUNT(*) FROM messages 
            WHERE chat_id = ? AND timestamp > ?
        ''', (chat.id, day_ago.isoformat()))
        daily_msgs = cursor.fetchone()[0] or 0
        
        # Статистика за неделю
        cursor.execute('''
            SELECT COUNT(*) FROM messages 
            WHERE chat_id = ? AND timestamp > ?
        ''', (chat.id, week_ago.isoformat()))
        weekly_msgs = cursor.fetchone()[0] or 0
        
        # Статистика за месяц
        cursor.execute('''
            SELECT COUNT(*) FROM messages 
            WHERE chat_id = ? AND timestamp > ?
        ''', (chat.id, month_ago.isoformat()))
        monthly_msgs = cursor.fetchone()[0] or 0
        
        # Топ пользователей
        cursor.execute('''
            SELECT username, first_name, COUNT(*) as msg_count
            FROM messages 
            WHERE chat_id = ? 
            GROUP BY user_id 
            ORDER BY msg_count DESC 
            LIMIT 5
        ''', (chat.id,))
        top_users = cursor.fetchall()
        
        text = (
            f"# Спектр | Статистика чата\n\n"
            f"📅 {chat.title}\n"
            f"👥 Участников: {total_users}\n\n"
            
            f"📊 Активность\n"
            f"• За день: {daily_msgs:,} 💬\n"
            f"• За неделю: {weekly_msgs:,} 💬\n"
            f"• За месяц: {monthly_msgs:,} 💬\n"
            f"• За всё время: {total_msgs:,} 💬\n\n"
        )
        
        if top_users:
            text += "🏆 Топ-5 активных:\n"
            for i, (username, first_name, count) in enumerate(top_users, 1):
                name = username or first_name or "Пользователь"
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                text += f"{medal} {name} — {count} 💬\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_my_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)
        
        text = (
            f"{s.header('📊 МОЯ СТАТИСТИКА')}\n\n"
            f"{s.stat('Сообщений', user_data['messages_count'])}\n"
            f"{s.stat('Команд', user_data['commands_used'])}\n"
            f"{s.stat('Репутация', user_data['reputation'])}\n"
            f"{s.stat('КНБ побед', user_data['rps_wins'])}\n"
            f"{s.stat('Дуэлей побед', user_data['duel_wins'])}\n"
            f"{s.stat('Рейтинг дуэлей', user_data['duel_rating'])}\n"
            f"{s.stat('Боссов убито', user_data['boss_kills'])}\n"
            f"{s.stat('Игр в мафию', user_data['mafia_games'])}"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    # ===== ЭКОНОМИКА =====
    async def cmd_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        vip_status = "✅ Активен" if self.db.is_vip(user_data['id']) else "❌ Не активен"
        vip_until = ""
        if self.db.is_vip(user_data['id']):
            vip_until = self.db.cursor.execute("SELECT vip_until FROM users WHERE id = ?", (user_data['id'],)).fetchone()[0]
            vip_until = datetime.fromisoformat(vip_until).strftime("%d.%m.%Y")
        
        premium_status = "✅ Активен" if self.db.is_premium(user_data['id']) else "❌ Не активен"
        
        text = (
            f"💰 Кошелёк пользователя {user.first_name}\n\n"
            f"💰 Монеты: {user_data['coins']:,}\n"
            f"💜 Неоны: {user_data['neons']:,}\n"
            f"🖥 Глитчи: {user_data['glitches']:,}\n\n"
            f"💎 VIP статус: {vip_status}\n"
            f"{f'📅 VIP до: {vip_until}' if self.db.is_vip(user_data['id']) else ''}\n"
            f"👑 PREMIUM: {premium_status}\n\n"
            f"🔥 Стрик: {user_data['daily_streak']} дней\n"
            f"🎁 /daily — доступно"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_coins(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.cmd_balance(update, context)
    
    async def cmd_pay(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /pay @user сумма")
            return
        
        username = context.args[0].replace('@', '')
        try:
            amount = int(context.args[1])
        except:
            await update.message.reply_text("❌ Сумма должна быть числом")
            return
        
        if amount <= 0:
            await update.message.reply_text("❌ Сумма должна быть больше 0")
            return
        
        user_data = self.db.get_user(update.effective_user.id)
        
        if user_data['coins'] < amount:
            await update.message.reply_text(f"❌ Недостаточно монет. Баланс: {user_data['coins']} 💰")
            return
        
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        if target['id'] == user_data['id']:
            await update.message.reply_text("❌ Нельзя перевести самому себе")
            return
        
        self.db.add_coins(user_data['id'], -amount)
        self.db.add_coins(target['id'], amount)
        
        commission_text = ""
        if not self.db.is_premium(user_data['id']):
            commission = int(amount * 0.05)
            self.db.add_coins(user_data['id'], -commission)
            commission_text = f"\n💸 Комиссия: {commission} (5%)"
        
        target_name = target.get('nickname') or target['first_name']
        user_name = f"@{user_data['username']}" if user_data.get('username') else user_data['first_name']
        
        await update.message.reply_text(
            f"💸 ПЕРЕВОД\n\n"
            f"👤 Получатель: {target_name}\n"
            f"💰 Сумма: {amount} 💰{commission_text}\n\n"
            f"✅ Перевод выполнен!"
        )
        self.db.log_action(user_data['id'], 'pay', f"{amount}💰 -> {target['id']}")
    
    async def cmd_daily(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data.get('last_daily'):
            last = datetime.fromisoformat(user_data['last_daily'])
            if (datetime.now() - last).seconds < DAILY_COOLDOWN:
                remain = DAILY_COOLDOWN - (datetime.now() - last).seconds
                hours = remain // 3600
                minutes = (remain % 3600) // 60
                await update.message.reply_text(f"⏳ Бонус через {hours}ч {minutes}м")
                return
        
        streak = self.db.add_daily_streak(user_data['id'])
        
        coins = random.randint(100, 300)
        neons = random.randint(1, 5)
        exp = random.randint(20, 60)
        energy = 20
        
        coins = int(coins * (1 + min(streak, 30) * 0.05))
        neons = int(neons * (1 + min(streak, 30) * 0.05))
        exp = int(exp * (1 + min(streak, 30) * 0.05))
        
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
        
        text = (
            f"🎁 Ежедневный бонус\n\n"
            f"💰 Монеты: +{coins}\n"
            f"💜 Неоны: +{neons}\n"
            f"🔥 Стрик: {streak} дней\n"
            f"✨ Опыт: +{exp}\n"
            f"⚡️ Энергия: +{energy}\n\n"
            f"💰 Новый баланс: {user_data['coins'] + coins} 💰\n"
            f"💜 Новые неоны: {user_data['neons'] + neons}\n\n"
            f"⏳ Следующий бонус через: 24 часа"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        self.db.log_action(user_data['id'], 'daily', f'+{coins}💰 +{neons}💜')
    
    async def cmd_streak(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)
        streak = user_data.get('daily_streak', 0)
        
        text = (
            f"{s.header('🔥 ТЕКУЩИЙ СТРИК')}\n\n"
            f"{s.stat('Дней подряд', streak)}\n"
            f"{s.stat('Множитель', f'x{1 + min(streak, 30) * 0.05:.2f}')}\n\n"
            f"{s.info('Чем больше стрик, тем выше бонус!')}"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_shop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            f"{s.header('🛍 МАГАЗИН')}\n\n"
            f"{s.section('💊 ЗЕЛЬЯ')}"
            f"{s.cmd('buy зелье здоровья', '50 💰 (❤️+30)')}\n"
            f"{s.cmd('buy большое зелье', '100 💰 (❤️+70)')}\n\n"
            f"{s.section('⚔️ ОРУЖИЕ')}"
            f"{s.cmd('buy меч', '200 💰 (⚔️+10)')}\n"
            f"{s.cmd('buy легендарный меч', '500 💰 (⚔️+30)')}\n\n"
            f"{s.section('⚡️ ЭНЕРГИЯ')}"
            f"{s.cmd('buy энергетик', '30 💰 (⚡️+20)')}\n"
            f"{s.cmd('buy батарейка', '80 💰 (⚡️+50)')}\n\n"
            f"{s.section('💎 ПРИВИЛЕГИИ')}"
            f"{s.cmd('vip', f'VIP ({VIP_PRICE} 💰 / 30 дней)')}\n"
            f"{s.cmd('premium', f'PREMIUM ({PREMIUM_PRICE} 💰 / 30 дней)')}"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_buy(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Что купить? /buy [предмет]")
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
            await update.message.reply_text("❌ Такого товара нет в магазине")
            return
        
        item_data = items[item]
        
        if user_data['coins'] < item_data['price']:
            await update.message.reply_text(f"❌ Недостаточно монет. Нужно {item_data['price']} 💰")
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
        
        await update.message.reply_text(
            f"✅ Покупка совершена!\n\n"
            f"📦 Предмет:** {item}\n"
            f"{effects_text}"
        )
        self.db.log_action(user_data['id'], 'buy', item)
    
    async def cmd_vip_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            f"💎 VIP СТАТУС\n\n"
            f"💰 Цена: {VIP_PRICE} 💰 / {VIP_DAYS} дней\n\n"
            f"⚔️ Урон в битвах +20%\n"
            f"💰 Награда с боссов +50%\n"
            f"🎁 Ежедневный бонус +50%\n"
            f"💎 Алмазы +1 в день\n\n"
            f"/buyvip — купить VIP"
        )
    
    async def cmd_premium_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            f"👑 PREMIUM СТАТУС\n\n"
            f"💰 Цена: {PREMIUM_PRICE} 💰 / {PREMIUM_DAYS} дней\n\n"
            f"⚔️ Урон в битвах +50%\n"
            f"💰 Награда с боссов +100%\n"
            f"🎁 Ежедневный бонус +100%\n"
            f"💎 Алмазы +3 в день\n"
            f"🚫 Игнорирование спам-фильтра\n\n"
            f"/buypremium — купить PREMIUM"
        )
    
    async def cmd_buy_vip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)
        
        if user_data['coins'] < VIP_PRICE:
            await update.message.reply_text(f"❌ Недостаточно монет. Нужно {VIP_PRICE} 💰")
            return
        
        if self.db.is_vip(user_data['id']):
            await update.message.reply_text("❌ VIP статус уже активен")
            return
        
        self.db.add_coins(user_data['id'], -VIP_PRICE)
        until = self.db.set_vip(user_data['id'], VIP_DAYS)
        date_str = until.strftime("%d.%m.%Y")
        
        await update.message.reply_text(
            f"✨ VIP СТАТУС АКТИВИРОВАН\n\n"
            f"📅 Срок: до {date_str}\n\n"
            f"ℹ️ Спасибо за поддержку!"
        )
        self.db.log_action(user_data['id'], 'buy_vip')
    
    async def cmd_buy_premium(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)
        
        if user_data['coins'] < PREMIUM_PRICE:
            await update.message.reply_text(f"❌ Недостаточно монет. Нужно {PREMIUM_PRICE} 💰")
            return
        
        if self.db.is_premium(user_data['id']):
            await update.message.reply_text("❌ PREMIUM статус уже активен")
            return
        
        self.db.add_coins(user_data['id'], -PREMIUM_PRICE)
        until = self.db.set_premium(user_data['id'], PREMIUM_DAYS)
        date_str = until.strftime("%d.%m.%Y")
        
        await update.message.reply_text(
            f"✨ PREMIUM СТАТУС АКТИВИРОВАН\n\n"
            f"📅 Срок: до {date_str}\n\n"
            f"ℹ️ Спасибо за поддержку!"
        )
        self.db.log_action(user_data['id'], 'buy_premium')

    # ===== НОВАЯ ЭКОНОМИКА (НЕОНЫ, ГЛИТЧИ) =====
    async def cmd_neons(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)
        
        text = (
            f"{s.header('💜 МОИ НЕОНЫ')}\n\n"
            f"{s.stat('Баланс', f'{user_data["neons"]} 💜')}\n"
            f"{s.stat('В глитчах', f'{user_data["glitches"]} 🖥')}\n\n"
            f"{s.section('КОМАНДЫ')}"
            f"{s.cmd('transfer @user 100', 'передать неоны')}\n"
            f"{s.cmd('exchange 100', 'обменять глитчи на неоны')}\n"
            f"{s.cmd('farm', 'ферма глитчей')}"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_glitches(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)
        neons_from_glitches = user_data['glitches'] // NEON_PRICE
        
        text = (
            f"{s.header('🖥 МОИ ГЛИТЧИ')}\n\n"
            f"{s.stat('Баланс', f'{user_data["glitches"]} 🖥')}\n"
            f"{s.stat('Можно обменять', f'{neons_from_glitches} 💜')}\n\n"
            f"{s.section('КОМАНДЫ')}"
            f"{s.cmd('exchange 100', 'обменять глитчи на неоны')}\n"
            f"{s.cmd('farm', 'ферма глитчей')}"
        )
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
                await update.message.reply_text(f"⏳ Ферма будет доступна через {hours}ч {minutes}м")
                return
        
        glitches_earned = random.randint(10, 50)
        
        if self.db.is_vip(user_data['id']):
            glitches_earned = int(glitches_earned * 1.2)
        if self.db.is_premium(user_data['id']):
            glitches_earned = int(glitches_earned * 1.3)
        if user_data.get('turbo_drive_until') and datetime.fromisoformat(user_data['turbo_drive_until']) > datetime.now():
            glitches_earned = int(glitches_earned * 1.5)
        
        self.db.add_glitches(user_data['id'], glitches_earned)
        self.db.update_user(user_data['id'], platform="telegram", last_farm=datetime.now().isoformat())
        
        text = (
            f"{s.header('🖥 ФЕРМА ГЛИТЧЕЙ')}\n\n"
            f"{s.success('✅ Вы успешно нафармили!')}\n"
            f"{s.item(f'Добыто: {glitches_earned} 🖥')}\n\n"
            f"{s.item(f'Теперь у вас: {user_data["glitches"] + glitches_earned} 🖥')}\n\n"
            f"{s.info('Следующая ферма через 4 часа')}"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        self.db.check_glitch_achievements(user_data['id'])
    
    async def cmd_transfer_neons(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /transfer @user 100")
            return
        
        username = context.args[0].replace('@', '')
        try:
            amount = int(context.args[1])
        except:
            await update.message.reply_text("❌ Сумма должна быть числом")
            return
        
        if amount <= 0:
            await update.message.reply_text("❌ Сумма должна быть больше 0")
            return
        
        user_data = self.db.get_user(update.effective_user.id)
        
        if user_data['neons'] < amount:
            await update.message.reply_text(f"❌ Недостаточно неонов. Баланс: {user_data['neons']} 💜")
            return
        
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        if target['id'] == user_data['id']:
            await update.message.reply_text("❌ Нельзя перевести самому себе")
            return
        
        commission = 0
        if not self.db.is_vip(user_data['id']) and not self.db.is_premium(user_data['id']):
            commission = int(amount * 0.05)
        
        self.db.transfer_neons(user_data['id'], target['id'], amount, commission)
        
        target_name = target.get('nickname') or target['first_name']
        
        text = (
            f"{s.header('💜 ПЕРЕВОД НЕОНОВ')}\n"
            f"{s.item(f'Получатель: {target_name}')}\n"
            f"{s.item(f'Сумма: {amount} 💜')}\n"
        )
        
        if commission > 0:
            text += f"{s.item(f'Комиссия: {commission} 💜 (5%)')}\n"
        
        text += f"\n{s.success('✅ Перевод выполнен!')}"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        self.db.log_action(user_data['id'], 'transfer_neons', f"{amount}💜 -> {target['id']}")
    
    async def cmd_exchange(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Укажите количество глитчей для обмена")
            return
        
        try:
            glitches = int(context.args[0])
        except:
            await update.message.reply_text("❌ Количество должно быть числом")
            return
        
        if glitches < NEON_PRICE:
            await update.message.reply_text(f"❌ Минимум для обмена: {NEON_PRICE} глитчей")
            return
        
        user_data = self.db.get_user(update.effective_user.id)
        
        if user_data['glitches'] < glitches:
            await update.message.reply_text(f"❌ Недостаточно глитчей. Баланс: {user_data['glitches']} 🖥")
            return
        
        neons = glitches // NEON_PRICE
        used_glitches = neons * NEON_PRICE
        remainder = glitches - used_glitches
        
        self.db.add_glitches(user_data['id'], -used_glitches)
        self.db.add_neons(user_data['id'], neons)
        
        text = (
            f"{s.header('💱 ОБМЕН ВАЛЮТ')}\n\n"
            f"{s.item(f'Обменено: {used_glitches} 🖥 → {neons} 💜')}\n"
            f"{s.item(f'Остаток глитчей: {user_data["glitches"] - used_glitches + remainder} 🖥')}\n"
            f"{s.item(f'Новый баланс неонов: {user_data["neons"] + neons} 💜')}\n\n"
            f"{s.success('✅ Обмен выполнен!')}"
        )
        
        if remainder > 0:
            text += f"\n{s.info(f'Остаток {remainder} глитчей не обменян (нужно {NEON_PRICE} для 1 неона)')}"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    # ===== НОВЫЕ МОДУЛИ (КВЕСТЫ, БИРЖА) =====
    
    async def cmd_quests(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает активные квесты пользователя"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        # Получаем или назначаем квесты
        quests = self.db.get_user_quests(user_data['id'])
        
        if not quests:
            # Назначаем новые квесты
            daily = self.db.assign_daily_quests(user_data['id'])
            weekly = self.db.assign_weekly_quests(user_data['id'])
            quests = daily + weekly
        
        if not quests:
            await update.message.reply_text("ℹ️ Нет доступных квестов")
            return
        
        text = f"{s.header('🎯 АКТИВНЫЕ КВЕСТЫ')}\n\n"
        
        for quest in quests:
            progress_bar = self._progress_bar(quest['progress'], quest['condition_value'], 10)
            text += (
                f"**{quest['name']}**\n"
                f"{quest['description']}\n"
                f"{progress_bar}\n"
                f"Награда: {quest['reward_neons']} 💜, {quest['reward_glitches']} 🖥\n\n"
            )
        
        text += f"✅ Выполнено квестов: {user_data.get('completed_quests', 0)}"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_exchange_market(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает состояние биржи"""
        stats = self.db.get_exchange_stats()
        
        text = (
            f"{s.header('💱 БИРЖА')}\n\n"
            f"Текущий курс: {stats['price']} 💰 за 1 💜\n"
            f"Объём за 24ч: {stats['volume_24h']} 💰\n"
            f"Активных ордеров: {stats['active_orders']}\n\n"
            f"{s.section('КОМАНДЫ')}"
            f"{s.cmd('buyorder 100 10', 'купить 100 неонов по 10💰 за штуку')}\n"
            f"{s.cmd('sellorder 50 12', 'продать 50 неонов по 12💰 за штуку')}\n"
            f"{s.cmd('myorders', 'мои ордера')}\n"
            f"{s.cmd('cancelorder 1', 'отменить ордер')}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_buy_order(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Создаёт ордер на покупку"""
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /buyorder [количество] [цена]")
            return
        
        try:
            amount = int(context.args[0])
            price = int(context.args[1])
        except:
            await update.message.reply_text("❌ Количество и цена должны быть числами")
            return
        
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        # Проверяем баланс
        total_cost = amount * price
        if user_data['coins'] < total_cost:
            await update.message.reply_text(f"❌ Недостаточно монет. Нужно {total_cost} 💰")
            return
        
        order_id = self.db.create_exchange_order(
            user_data['id'], 'buy', 'coins', 'neons', amount, price
        )
        
        if order_id:
            await update.message.reply_text(
                f"✅ Ордер на покупку #{order_id} создан!\n"
                f"Куплю {amount} 💜 по {price} 💰 за штуку"
            )
        else:
            await update.message.reply_text("❌ Не удалось создать ордер")
    
    async def cmd_sell_order(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Создаёт ордер на продажу"""
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /sellorder [количество] [цена]")
            return
        
        try:
            amount = int(context.args[0])
            price = int(context.args[1])
        except:
            await update.message.reply_text("❌ Количество и цена должны быть числами")
            return
        
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        # Проверяем баланс
        if user_data['neons'] < amount:
            await update.message.reply_text(f"❌ Недостаточно неонов. Баланс: {user_data['neons']} 💜")
            return
        
        order_id = self.db.create_exchange_order(
            user_data['id'], 'sell', 'neons', 'coins', amount, price
        )
        
        if order_id:
            await update.message.reply_text(
                f"✅ Ордер на продажу #{order_id} создан!\n"
                f"Продам {amount} 💜 по {price} 💰 за штуку"
            )
        else:
            await update.message.reply_text("❌ Не удалось создать ордер")
    
    async def cmd_my_orders(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает активные ордера пользователя"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        self.db.cursor.execute('''
            SELECT * FROM exchange_orders 
            WHERE user_id = ? AND status = 'active'
            ORDER BY created_at DESC
        ''', (user_data['id'],))
        
        orders = self.db.cursor.fetchall()
        
        if not orders:
            await update.message.reply_text("ℹ️ У вас нет активных ордеров")
            return
        
        text = f"{s.header('📊 МОИ ОРДЕРА')}\n\n"
        
        for order in orders:
            order_dict = dict(order)
            order_type = "📈 ПОКУПКА" if order_dict['type'] == 'buy' else "📉 ПРОДАЖА"
            remaining = order_dict['amount'] - order_dict['filled']
            text += (
                f"#{order_dict['id']} {order_type}\n"
                f"{remaining}/{order_dict['amount']} {order_dict['currency_to']}\n"
                f"Цена: {order_dict['price']} 💰\n\n"
            )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_cancel_order(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отменяет ордер"""
        if not context.args:
            await update.message.reply_text("❌ Укажите ID ордера: /cancelorder 1")
            return
        
        try:
            order_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ ID должен быть числом")
            return
        
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if self.db.cancel_exchange_order(order_id, user_data['id']):
            await update.message.reply_text(f"✅ Ордер #{order_id} отменён")
        else:
            await update.message.reply_text("❌ Ордер не найден или уже исполнен")

    # ===== ИГРЫ =====
    async def cmd_games(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = """
🎮 ИГРЫ

🔫 /rr [ставка] — Русская рулетка
🎲 /dicebet [ставка] — Кости
🎰 /slots [ставка] — Слоты
✊ /rps — Камень-ножницы-бумага
💣 /saper [ставка] — Сапёр
🔢 /guess [ставка] — Угадай число
🐂 /bulls [ставка] — Быки и коровы

💰 Баланс: /balance
        """
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_coin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Подбросить монетку"""
        result = random.choice(["Орёл", "Решка"])
        await update.message.reply_text(f"🪙 МОНЕТКА\n\n• Выпало: {result}")
    
    async def cmd_dice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Бросить кубик"""
        result = random.randint(1, 6)
        await update.message.reply_text(f"🎲 КУБИК\n\n• Выпало: {result}")
    
    async def cmd_dice_bet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Кости на деньги"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if not context.args:
            await update.message.reply_text("❌ Укажите ставку: /dicebet 100")
            return
        
        try:
            bet = int(context.args[0])
        except:
            await update.message.reply_text("❌ Ставка должна быть числом")
            return
        
        if bet > user_data['coins']:
            await update.message.reply_text(f"❌ Недостаточно монет. Баланс: {user_data['coins']} 💰")
            return
        
        if bet <= 0:
            await update.message.reply_text("❌ Ставка должна быть больше 0")
            return
        
        dice1 = random.randint(1, 6)
        dice2 = random.randint(1, 6)
        total = dice1 + dice2
        
        win_multiplier = 1
        if total in [7, 11]:
            win_multiplier = 2
            self.db.update_user(user_data['id'], dice_wins=user_data.get('dice_wins', 0) + 1)
            result_text = "🎉 ВЫИГРЫШ!"
        elif total in [2, 3, 12]:
            win_multiplier = 0
            self.db.update_user(user_data['id'], dice_losses=user_data.get('dice_losses', 0) + 1)
            result_text = "💀 ПРОИГРЫШ!"
        else:
            win_multiplier = 1
            result_text = "🔄 НИЧЬЯ!"
        
        win_amount = bet * win_multiplier if win_multiplier > 0 else -bet
        
        if win_multiplier > 0:
            self.db.add_coins(user_data['id'], win_amount - bet if win_multiplier > 1 else 0)
        else:
            self.db.add_coins(user_data['id'], -bet)
        
        text = (
            f"🎲 КОСТИ**\n\n"
            f"👤 Игрок: {user.first_name}\n"
            f"💰 Ставка: {bet} 💰\n\n"
            f"🎲 {dice1} + {dice2} = {total}\n\n"
            f"{result_text}\n"
        )
        
        if win_multiplier > 1:
            text += f"+{win_amount - bet} 💰\n"
        elif win_multiplier == 0:
            text += f"-{bet} 💰\n"
        else:
            text += f"Ставка возвращена\n"
        
        text += f"\n💰 Новый баланс: {user_data['coins'] + (win_amount - bet if win_multiplier > 1 else -bet if win_multiplier == 0 else 0)} 💰"
        
        await update.message.reply_text(text)
    
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
            await update.message.reply_text(f"❌ Недостаточно монет. Баланс: {user_data['coins']} 💰")
            return
        
        if bet <= 0:
            await update.message.reply_text("❌ Ставка должна быть больше 0")
            return
        
        num = random.randint(0, 36)
        red_numbers = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]
        
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
            result = f"🎉 ВЫИГРЫШ! +{win_amount} 💰"
        else:
            self.db.add_coins(user_data['id'], -bet)
            self.db.update_user(user_data['id'], casino_losses=user_data.get('casino_losses', 0) + 1)
            result = f"💀 ПРОИГРЫШ! -{bet} 💰"
        
        await update.message.reply_text(
            f"🎰 РУЛЕТКА\n\n"
            f"👤 Игрок: {user.first_name}\n"
            f"💰 Ставка: {bet} 💰\n"
            f"🎯 Выбрано: {choice}\n\n"
            f"🎰 Выпало: {num} {color}\n\n"
            f"{result}\n\n"
            f"💰 Новый баланс: {user_data['coins'] + (win_amount if win else -bet)} 💰"
        )
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
            await update.message.reply_text(f"❌ Недостаточно монет. Баланс: {user_data['coins']} 💰")
            return
        
        if bet <= 0:
            await update.message.reply_text("❌ Ставка должна быть больше 0")
            return
        
        symbols = ["🍒", "🍋", "🍊", "7️⃣", "💎", "⭐️"]
        spin = [random.choice(symbols) for _ in range(3)]
        
        if len(set(spin)) == 1:
            if spin[0] == "7️⃣":
                win = bet * 50
            elif spin[0] == "💎":
                win = bet * 30
            elif spin[0] == "⭐️":
                win = bet * 20
            else:
                win = bet * 10
            result = f"🎉 ДЖЕКПОТ! +{win} 💰"
            self.db.update_user(user_data['id'], slots_wins=user_data.get('slots_wins', 0) + 1)
        elif len(set(spin)) == 2:
            win = bet * 2
            result = f"🎉 ВЫИГРЫШ! +{win} 💰"
            self.db.update_user(user_data['id'], slots_wins=user_data.get('slots_wins', 0) + 1)
        else:
            win = 0
            result = f"💀 ПРОИГРЫШ! -{bet} 💰"
            self.db.update_user(user_data['id'], slots_losses=user_data.get('slots_losses', 0) + 1)
        
        if win > 0:
            self.db.add_coins(user_data['id'], win)
        else:
            self.db.add_coins(user_data['id'], -bet)
        
        await update.message.reply_text(
            f"🎰 СЛОТЫ\n\n"
            f"👤 Игрок: {user.first_name}\n"
            f"💰 Ставка: {bet} 💰\n\n"
            f"[ {' | '.join(spin)} ]\n\n"
            f"{result}\n\n"
            f"💰 Новый баланс: {user_data['coins'] + (win if win > 0 else -bet)} 💰"
        )
    
    async def cmd_rps(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Камень-ножницы-бумага"""
        text = """
✊ КАМЕНЬ-НОЖНИЦЫ-БУМАГА

Выберите жест (напишите цифру):

1️⃣ 🪨 Камень
2️⃣ ✂️ Ножницы
3️⃣ 📄 Бумага
        """
        await update.message.reply_text(text, parse_mode='Markdown')
        context.user_data['awaiting_rps'] = True
    
    async def cmd_russian_roulette(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Русская рулетка"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        bet = 10
        if context.args:
            try:
                bet = int(context.args[0])
            except:
                await update.message.reply_text("❌ Ставка должна быть числом")
                return
        
        if bet > user_data['coins']:
            await update.message.reply_text(f"❌ Недостаточно монет. Баланс: {user_data['coins']} 💰")
            return
        
        if bet <= 0:
            await update.message.reply_text("❌ Ставка должна быть больше 0")
            return
        
        chamber = random.randint(1, 6)
        shot = random.randint(1, 6)
        
        await asyncio.sleep(2)
        
        if chamber == shot:
            self.db.add_coins(user_data['id'], -bet)
            self.db.update_user(user_data['id'], rr_losses=user_data.get('rr_losses', 0) + 1)
            result_text = "💥 *Бах!* Выстрел..."
            win_text = f"💀 ВЫ ПРОИГРАЛИ! -{bet} 💰"
        else:
            win = bet * 5
            self.db.add_coins(user_data['id'], win)
            self.db.update_user(user_data['id'], rr_wins=user_data.get('rr_wins', 0) + 1)
            result_text = "🔫 *Щёлк...* В этот раз повезло!"
            win_text = f"🎉 ВЫ ВЫИГРАЛИ! +{win} 💰"
        
        await update.message.reply_text(
            f"🔫 РУССКАЯ РУЛЕТКА\n\n"
            f"👤 Игрок: {user.first_name}\n"
            f"💰 Ставка: {bet} 💰\n\n"
            f"{result_text}\n\n"
            f"{win_text}\n\n"
            f"💰 Новый баланс: {user_data['coins'] + (win if chamber != shot else -bet)} 💰"
        )
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
            await update.message.reply_text(f"❌ Недостаточно монет. Баланс: {user_data['coins']} 💰")
            return
        
        field = [['⬜️' for _ in range(3)] for _ in range(3)]
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
        
        keyboard_buttons = []
        for i in range(3):
            for j in range(3):
                cell_num = i * 3 + j + 1
                keyboard_buttons.append(InlineKeyboardButton(f"⬜️", callback_data=f"saper_{game_id}_{cell_num}"))
        
        keyboard = InlineKeyboardMarkup(self._split_buttons(keyboard_buttons, 3))
        
        await update.message.reply_text(
            f"💣 САПЁР\n\n"
            f"💰 Ставка: {bet} 💰\n"
            f"🎯 Выберите клетку:\n\n"
            f"ℹ️ Нажимайте на кнопки, чтобы открыть клетки",
            reply_markup=keyboard
        )
    
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
            await update.message.reply_text(f"❌ Недостаточно монет. Баланс: {user_data['coins']} 💰")
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
            f"🔢 УГАДАЙ ЧИСЛО\n\n"
            f"🎯 Я загадал число от 1 до 100\n"
            f"💰 Ставка: {bet} 💰\n"
            f"📊 Попыток: 7\n\n"
            f"💬 Напиши свой вариант..."
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
            await update.message.reply_text(f"❌ Недостаточно монет. Баланс: {user_data['coins']} 💰")
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
            f"🐂 БЫКИ И КОРОВЫ\n\n"
            f"🎯 Я загадал 4-значное число без повторов\n"
            f"💰 Ставка: {bet} 💰\n"
            f"📊 Попыток: 10\n"
            f"🐂 Бык — цифра на своём месте\n"
            f"🐄 Корова — цифра есть, но не на своём месте\n\n"
            f"💬 Напиши свой вариант (4 цифры)..."
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
        
        text = "👾 БОССЫ\n\n"
        
        for i, boss in enumerate(bosses[:5]):
            health_bar = self._progress_bar(boss['health'], boss['max_health'])
            text += (
                f"{i+1}. {boss['name']} (ур.{boss['level']})\n"
                f"   ❤️ {health_bar}\n"
                f"   ⚔️ Урон: {boss['damage']}\n"
                f"   💰 Награда: {boss['reward_coins']} 💰, ✨ {boss['reward_exp']}\n"
                f"   💜 Неоны: {boss['reward_neons']}, 🖥 Глитчи: {boss['reward_glitches']}\n\n"
            )
        
        text += (
            f"**ТВОИ ПОКАЗАТЕЛИ**\n"
            f"❤️ Здоровье: {user_data['health']}/{user_data['max_health']}\n"
            f"⚡️ Энергия: {user_data['energy']}/100\n"
            f"⚔️ Урон: {user_data['damage']}\n"
            f"👾 Боссов убито: {user_data['boss_kills']}\n\n"
            f"📝 Команды:\n"
            f"• /boss [ID] — атаковать босса\n"
            f"• /regen — восстановить ❤️ и ⚡️"
        )
        
        keyboard_buttons = []
        for i, boss in enumerate(bosses[:5]):
            status = "⚔️" if boss['is_alive'] else "💀"
            keyboard_buttons.append(InlineKeyboardButton(
                f"{status} {boss['name']} (❤️ {boss['health']}/{boss['max_health']})",
                callback_data=f"boss_attack_{boss['id']}"
            ))
        
        keyboard_buttons.append(InlineKeyboardButton("🔄 Регенерация", callback_data="boss_regen"))
        keyboard_buttons.append(InlineKeyboardButton("⚔️ Купить оружие", callback_data="boss_buy_weapon"))
        
        reply_markup = InlineKeyboardMarkup(self._split_buttons(keyboard_buttons, 1))
        
        await update.message.reply_text(text, reply_markup=reply_markup)
    
    async def cmd_boss_fight(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Атаковать босса"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if not context.args:
            await update.message.reply_text("❌ Укажи ID босса: /boss 1")
            return
        
        try:
            boss_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ Неверный ID")
            return
        
        await self._process_boss_attack(update, context, user, user_data, boss_id, False)
    
    async def _process_boss_attack(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                   user, user_data, boss_id: int, is_callback: bool = False):
        """Общая логика атаки босса"""
        boss = self.db.get_boss(boss_id)
        
        if not boss or not boss['is_alive']:
            msg = "❌ Босс не найден или уже повержен"
            if is_callback:
                await update.callback_query.edit_message_text(msg)
            else:
                await update.message.reply_text(msg)
            return
        
        if user_data['energy'] < 10:
            msg = "❌ Недостаточно энергии. Используй /regen"
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
        
        base_damage = user_data['damage'] * damage_bonus
        player_damage = int(base_damage) + random.randint(-5, 5)
        
        crit = random.randint(1, 100) <= user_data['crit_chance']
        if crit:
            player_damage = int(player_damage * user_data['crit_multiplier'] / 100)
            crit_text = "💥 КРИТИЧЕСКИЙ УДАР! "
        else:
            crit_text = ""
        
        boss_damage = boss['damage'] + random.randint(-5, 5)
        armor_reduction = user_data['armor'] // 2
        player_taken = max(1, boss_damage - armor_reduction)
        
        killed = self.db.damage_boss(boss_id, player_damage)
        self.db.damage(user_data['id'], player_taken)
        
        total_damage = user_data.get('boss_damage', 0) + player_damage
        self.db.update_user(user_data['id'], platform="telegram", boss_damage=total_damage)
        
        text = f"⚔️ БИТВА С БОССОМ\n\n"
        text += f"• {crit_text}Твой урон: {player_damage}\n"
        text += f"• Урон босса: {player_taken}\n\n"
        
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
            
            text += f"✅ ПОБЕДА!\n"
            text += f"• 💰 Монеты: +{reward_coins}\n"
            text += f"• 💜 Неоны: +{reward_neons}\n"
            text += f"• 🖥 Глитчи: +{reward_glitches}\n"
            text += f"• ✨ Опыт: +{reward_exp}\n"
            
            if leveled_up:
                text += f"✨ УРОВЕНЬ ПОВЫШЕН!\n"
        else:
            boss_info = self.db.get_boss(boss_id)
            text += f"⚠️ Босс ещё жив!\n"
            text += f"❤️ Осталось: {boss_info['health']} здоровья\n"
        
        if user_data['health'] <= player_taken:
            self.db.heal(user_data['id'], 50)
            text += f"\nℹ️ Ты погиб и воскрешён с 50❤️"
        
        user_data = self.db.get_user(user.id)
        
        text += f"\n• ❤️ Твое здоровье: {user_data['health']}/{user_data['max_health']}"
        text += f"\n• ⚡️ Энергия: {user_data['energy']}/100"
        
        keyboard_buttons = [
            InlineKeyboardButton("⚔️ Атаковать снова", callback_data=f"boss_attack_{boss_id}"),
            InlineKeyboardButton("🔄 Регенерация", callback_data="boss_regen"),
            InlineKeyboardButton("📋 К списку боссов", callback_data="boss_list")
        ]
        
        reply_markup = InlineKeyboardMarkup(self._split_buttons(keyboard_buttons, 1))
        
        if is_callback:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
        
        self.db.log_action(user_data['id'], 'boss_fight', f"Урон {player_damage}")
    
    async def cmd_boss_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о боссе"""
        if not context.args:
            await update.message.reply_text("❌ Укажи ID босса: /bossinfo 1")
            return
        
        try:
            boss_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ Неверный ID")
            return
        
        boss = self.db.get_boss(boss_id)
        if not boss:
            await update.message.reply_text("❌ Босс не найден")
            return
        
        status = "ЖИВ" if boss['is_alive'] else "ПОВЕРЖЕН"
        health_bar = self._progress_bar(boss['health'], boss['max_health'], 20)
        
        await update.message.reply_text(
            f"👾 {boss['name']}\n\n"
            f"📊 Характеристики\n"
            f"• Уровень: {boss['level']}\n"
            f"• ❤️ Здоровье: {health_bar}\n"
            f"• ⚔️ Урон: {boss['damage']}\n"
            f"• 💰 Монеты: {boss['reward_coins']}\n"
            f"• 💜 Неоны: {boss['reward_neons']}\n"
            f"• 🖥 Глитчи: {boss['reward_glitches']}\n"
            f"• ✨ Опыт: {boss['reward_exp']}\n"
            f"• 📊 Статус: {status}"
        )
    
    async def cmd_regen(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Регенерация"""
        user_data = self.db.get_user(update.effective_user.id)
        
        cost = 20
        if user_data['coins'] < cost:
            await update.message.reply_text(f"❌ Недостаточно монет. Нужно {cost} 💰")
            return
        
        self.db.add_coins(user_data['id'], -cost)
        self.db.heal(user_data['id'], 50)
        self.db.add_energy(user_data['id'], 20)
        
        user_data = self.db.get_user(update.effective_user.id)
        
        await update.message.reply_text(
            f"✅ Регенерация завершена!\n\n"
            f"❤️ Здоровье +50 (теперь {user_data['health']})\n"
            f"⚡️ Энергия +20 (теперь {user_data['energy']})\n"
            f"💰 Потрачено: {cost}"
        )

    # ===== ДУЭЛИ =====
    async def cmd_duel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Вызвать на дуэль"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /duel @user ставка")
            return
        
        username = context.args[0].replace('@', '')
        try:
            bet = int(context.args[1])
        except:
            await update.message.reply_text("❌ Ставка должна быть числом")
            return
        
        if bet <= 0:
            await update.message.reply_text("❌ Ставка должна быть больше 0")
            return
        
        if bet > user_data['coins']:
            await update.message.reply_text(f"❌ Недостаточно монет. Баланс: {user_data['coins']} 💰")
            return
        
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        if target['id'] == user_data['id']:
            await update.message.reply_text("❌ Нельзя вызвать на дуэль самого себя")
            return
        
        self.db.cursor.execute(
            "SELECT id FROM duels WHERE (challenger_id = ? OR opponent_id = ?) AND status = 'pending'",
            (user_data['id'], user_data['id'])
        )
        if self.db.cursor.fetchone():
            await update.message.reply_text("❌ У тебя уже есть активная дуэль")
            return
        
        duel_id = self.db.create_duel(user_data['id'], target['id'], bet)
        self.db.add_coins(user_data['id'], -bet)
        
        target_name = target.get('nickname') or target['first_name']
        
        keyboard_buttons = [
            InlineKeyboardButton("✅ ПРИНЯТЬ", callback_data=f"accept_duel_{duel_id}"),
            InlineKeyboardButton("❌ ОТКЛОНИТЬ", callback_data=f"reject_duel_{duel_id}")
        ]
        
        keyboard = InlineKeyboardMarkup(self._split_buttons(keyboard_buttons, 2))
        
        await update.message.reply_text(
            f"⚔️ ДУЭЛЬ\n\n"
            f"👤 {user.first_name} VS {target_name}\n"
            f"💰 Ставка: {bet} 💰\n\n"
            f"{target_name}, прими вызов!",
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
        """Обработка дуэли"""
        await asyncio.sleep(2)
        
        challenger_roll = random.randint(1, 100)
        opponent_roll = random.randint(1, 100)
        
        if self.db.is_vip(challenger['id']):
            challenger_roll += 5
        if self.db.is_vip(opponent['id']):
            opponent_roll += 5
        
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
            await context.bot.send_message(chat_id, "🤝 Ничья! Перебрасываем...")
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
            f"⚔️ РЕЗУЛЬТАТ ДУЭЛИ\n\n"
            f"👤 {winner['first_name']} VS {loser['first_name']}\n\n"
            f"🎲 Результаты:\n"
            f"• {winner['first_name']}: {winner_score}\n"
            f"• {loser['first_name']}: {loser_score}\n\n"
            f"🏆 Победитель: {winner['first_name']}\n"
            f"💰 Выигрыш: {win_amount} 💰\n\n"
            f"✅ Поздравляем!"
        )
        
        self.db.update_duel(duel_id, platform="telegram", status='completed', winner_id=winner['id'])
    
    async def cmd_duels(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список активных дуэлей"""
        self.db.cursor.execute("SELECT * FROM duels WHERE status = 'pending'")
        duels = self.db.cursor.fetchall()
        
        if not duels:
            await update.message.reply_text("ℹ️ Нет активных дуэлей")
            return
        
        text = "⚔️ АКТИВНЫЕ ДУЭЛИ\n\n"
        for duel in duels:
            challenger = self.db.get_user_by_id(duel[1])
            opponent = self.db.get_user_by_id(duel[2])
            if challenger and opponent:
                text += f"• {challenger['first_name']} vs {opponent['first_name']} — ставка {duel[3]} 💰\n"
        
        await update.message.reply_text(text)
    
    async def cmd_duel_rating(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Рейтинг дуэлянтов"""
        self.db.cursor.execute("SELECT first_name, nickname, duel_rating FROM users WHERE duel_rating > 0 ORDER BY duel_rating DESC LIMIT 10")
        top = self.db.cursor.fetchall()
        
        if not top:
            await update.message.reply_text("ℹ️ Рейтинг пуст")
            return
        
        text = "⚔️ ТОП ДУЭЛЯНТОВ\n\n"
        for i, row in enumerate(top, 1):
            name = row[1] or row[0]
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} {name} — {row[2]} очков\n"
        
        await update.message.reply_text(text)

    # ===== МАФИЯ (УЛУЧШЕННАЯ ВЕРСИЯ) =====
    async def cmd_mafia(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = """
# Спектр | Мафия

🎮 Команды мафии:

/mafiastart — начать новую игру
/mafiajoin — присоединиться к игре
/mafialeave — выйти из игры
/mafiaroles — список ролей
/mafiarules — правила игры
/mafiastats — статистика

⚠️ Игра проходит в ЛС с подтверждением! Все события в личных сообщениях.
        """
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_mafia_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        user = update.effective_user
        
        # Проверяем, не идёт ли уже игра
        if chat_id in self.mafia_games:
            game = self.mafia_games[chat_id]
            if game.status != "ended":
                # Показываем текущее состояние игры
                players_list = []
                for pid in game.players:
                    p = game.players_data[pid]
                    players_list.append(f"• {p['name']}")
                
                players_text = "\n".join(players_list)
                confirmed = sum(1 for p in game.players if game.players_data[p]['confirmed'])
                
                await update.message.reply_text(
                    f"🔫 МАФИЯ (игра уже идёт)\n\n"
                    f"👥 Участники ({len(game.players)}):\n"
                    f"{players_text}\n\n"
                    f"✅ Подтвердили: {confirmed}/{len(game.players)}\n"
                    f"📌 /mafiajoin — присоединиться"
                )
                return
        
        # Создаём новую игру
        game_id = f"mafia_{chat_id}_{int(time.time())}"
        game = MafiaGame(chat_id, game_id, user.id)
        self.mafia_games[chat_id] = game
        
        # Сохраняем в БД
        self.db.cursor.execute('''
            INSERT INTO mafia_games (game_id, chat_id, creator_id, status, players, players_data, roles, alive, votes, night_actions, confirmed_players)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (game_id, chat_id, user.id, 'waiting', 
              json.dumps([]), json.dumps({}), json.dumps({}), 
              json.dumps({}), json.dumps({}), json.dumps({}), json.dumps([])))
        self.db.conn.commit()
        
        text = (
            f"{s.header('🔫 МАФИЯ')}\n\n"
            f"{s.success('🎮 Игра создана!')}\n\n"
            f"{s.item('Участники (0):')}\n"
            f"{s.item('/mafiajoin — присоединиться')}\n"
            f"{s.item('/mafialeave — выйти')}\n\n"
            f"{s.info('Игра будет проходить в ЛС с ботом. Все события в личных сообщениях!')}"
        )
        
        msg = await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        game.message_id = msg.message_id
        
        # Обновляем в БД
        self.db.cursor.execute('UPDATE mafia_games SET message_id = ? WHERE game_id = ?', (msg.message_id, game_id))
        self.db.conn.commit()
    
    async def cmd_mafia_join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        user = update.effective_user
        
        if chat_id not in self.mafia_games:
            await update.message.reply_text(s.error("❌ Игра не создана. Начните: /mafiastart"))
            return
        
        game = self.mafia_games[chat_id]
        
        if game.status != "waiting":
            await update.message.reply_text(s.error("❌ Игра уже началась"))
            return
        
        if not game.add_player(user.id, user.first_name, user.username or ""):
            await update.message.reply_text(s.error("❌ Вы уже в игре"))
            return
        
        # Отправляем подтверждение в ЛС
        try:
            keyboard_buttons = [
                InlineKeyboardButton("✅ ПОДТВЕРДИТЬ", callback_data=f"mafia_confirm_{chat_id}")
            ]
            keyboard = InlineKeyboardMarkup(self._split_buttons(keyboard_buttons, 1))
            
            await self.send_private_message(
                user.id,
                f"{s.header('🔫 МАФИЯ')}\n\n"
                f"{s.item('Вы присоединились к игре!')}\n"
                f"{s.item('Нажмите кнопку для подтверждения')}\n\n"
                f"{s.info('После подтверждения вы получите свою роль в ЛС')}",
                reply_markup=keyboard
            )
            
            await update.message.reply_text(s.success(f"✅ {user.first_name}, проверьте ЛС для подтверждения!"))
        except Exception as e:
            await update.message.reply_text(
                s.error(f"❌ {user.first_name}, не удалось отправить сообщение в ЛС. Напишите боту в личку сначала.")
            )
            game.remove_player(user.id)
            return
        
        # Обновляем в БД
        self.db.cursor.execute('''
            UPDATE mafia_games 
            SET players = ?, players_data = ? 
            WHERE game_id = ?
        ''', (json.dumps(game.players), json.dumps(game.players_data), game.game_id))
        
        # Обновляем сообщение в чате
        await self._update_mafia_game_message(game, context)
    
    async def cmd_mafia_leave(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        user = update.effective_user
        
        if chat_id not in self.mafia_games:
            await update.message.reply_text(s.error("❌ Игра не создана"))
            return
        
        game = self.mafia_games[chat_id]
        
        if game.status != "waiting":
            await update.message.reply_text(s.error("❌ Нельзя покинуть игру после начала"))
            return
        
        if not game.remove_player(user.id):
            await update.message.reply_text(s.error("❌ Вас нет в игре"))
            return
        
        await update.message.reply_text(s.success(f"✅ {user.first_name} покинул игру"))
        
        # Обновляем в БД
        self.db.cursor.execute('''
            UPDATE mafia_games 
            SET players = ?, players_data = ? 
            WHERE game_id = ?
        ''', (json.dumps(game.players), json.dumps(game.players_data), game.game_id))
        
        await self._update_mafia_game_message(game, context)
    
    async def _update_mafia_game_message(self, game: MafiaGame, context: ContextTypes.DEFAULT_TYPE):
        """Обновляет сообщение с информацией об игре"""
        if not game.message_id:
            return
        
        if game.players:
            players_list = []
            for pid in game.players:
                p = game.players_data[pid]
                status = "✅" if p['confirmed'] else "⏳"
                players_list.append(f"{status} {p['name']}")
            
            players_text = "\n".join(players_list)
            confirmed = sum(1 for p in game.players if game.players_data[p]['confirmed'])
            
            status_text = "🟢 НАБОР ИГРОКОВ**" if game.status == "waiting" else f"🔴 ИГРА ИДЁТ (фаза: {game.phase})"
            
            text = (
                f"🔫 МАФИЯ\n\n"
                f"{status_text}\n\n"
                f"👥 Участники ({len(game.players)}):\n"
                f"{players_text}\n\n"
                f"✅ Подтвердили: {confirmed}/{len(game.players)}\n"
                f"❌ Нужно минимум: {MAFIA_MIN_PLAYERS} игроков\n\n"
            )
            
            if game.status == "waiting":
                text += (
                    f"📌 /mafiajoin — присоединиться\n"
                    f"📌 /mafialeave — выйти"
                )
            else:
                text += f"📊 День: {game.day} | Живых: {len(game.get_alive_players())}"
        else:
            text = (
                f"🔫 МАФИЯ**\n\n"
                f"👥 Участников нет\n"
                f"📌 /mafiajoin — присоединиться"
            )
        
        try:
            await context.bot.edit_message_text(
                text,
                chat_id=game.chat_id,
                message_id=game.message_id,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Ошибка обновления сообщения мафии: {e}")
    
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
                    f"💀 ВАС УБИЛИ НОЧЬЮ**\n\nВы больше не участвуете"
                )
            except:
                pass
        
        game.phase = "day"
        game.day += 1
        
        alive_list = game.get_alive_players()
        alive_names = []
        for pid in alive_list:
            name = game.players_data[pid]['name']
            alive_names.append(f"• {name}")
        
        killed_name = "никого"
        if killed["killed"]:
            killed_name = game.players_data[killed["killed"]]['name']
        
        text = (
            f"🔫 МАФИЯ | ДЕНЬ {game.day}\n\n"
            f"☀️ Наступило утро\n"
            f"💀 Убит: {killed_name}\n\n"
            f"👥 Живы ({len(alive_list)}):\n"
            f"{chr(10).join(alive_names)}\n\n"
            f"🗳 Обсуждайте и голосуйте"
        )
        
        await context.bot.send_message(game.chat_id, text, parse_mode=ParseMode.MARKDOWN)
        
        # Сохраняем в БД
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
            role = game.roles.get(executed, "неизвестно")
            
            await context.bot.send_message(
                game.chat_id,
                f"🔫 МАФИЯ | ДЕНЬ {game.day}\n\n"
                f"🔨 Исключён: {executed_name}\n"
                f"🎭 Роль: {role}\n\n"
                f"🌙 Ночь скоро..."
            )
            
            try:
                await self.send_private_message(
                    executed,
                    f"🔨 ВАС ИСКЛЮЧИЛИ ДНЁМ**\n\nВы больше не участвуете"
                )
            except:
                pass
        else:
            await context.bot.send_message(
                game.chat_id,
                "📢 Никто не был исключён"
            )
        
        winner = game.check_win()
        
        if winner == "citizens":
            await context.bot.send_message(
                game.chat_id,
                "🏆 ПОБЕДА ГОРОДА!**\n\nМафия уничтожена!"
            )
            # Обновляем статистику игроков
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
                "🏆 ПОБЕДА МАФИИ!**\n\nМафия захватила город!"
            )
            # Обновляем статистику игроков
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
            f"🔫 МАФИЯ | НОЧЬ {game.day}\n\n"
            f"🌙 Наступает ночь...\n"
            f"🔪 Мафия выбирает жертву",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Сохраняем в БД
        self.db.cursor.execute('''
            UPDATE mafia_games 
            SET phase = ?, night_actions = ?
            WHERE game_id = ?
        ''', (game.phase, json.dumps(game.night_actions), game.game_id))
        self.db.conn.commit()
        
        asyncio.create_task(self._mafia_night_timer(game, context))
    
    async def cmd_mafia_roles(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            f"{s.header('🔫 РОЛИ В МАФИИ')}\n\n"
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
    
    async def cmd_mafia_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            f"{s.header('🔫 ПРАВИЛА МАФИИ')}\n\n"
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
            f"{s.item('Город — найти всю мафию')}\n\n"
            f"{s.info('Все действия в ЛС с ботом. Подтверждение обязательно!')}"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_mafia_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        text = (
            f"{s.header('🔫 СТАТИСТИКА МАФИИ')}\n\n"
            f"{s.stat('Сыграно игр', user_data['mafia_games'])}\n"
            f"{s.stat('Побед', user_data['mafia_wins'])}\n"
            f"{s.stat('Поражений', user_data['mafia_losses'])}\n"
            f"{s.stat('Процент побед', f'{(user_data["mafia_wins"]/max(1, user_data["mafia_games"])*100):.1f}%')}"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    # ===== АЧИВКИ =====
    async def cmd_achievements(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = """
# Спектр | Ачивки

🏅 Команды:

/achievements — эта информация
/myachievements — мои ачивки
/achievement [ID] — информация об ачивке
/topachievements — топ коллекционеров

📋 Категории ачивок:
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

🔐 Приватность:
+Ачивки — открыть доступ к вашим ачивкам
-Ачивки — скрыть ваши ачивки от других
        """
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_my_achievements(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)
        achievements = self.db.get_user_achievements(user_data['id'])
        
        if not achievements:
            await update.message.reply_text(s.info("У вас пока нет ачивок"))
            return
        
        text = f"{s.header(f'🏅 АЧИВКИ: {user_data['first_name']}')}\nВсего: {len(achievements)}\n\n"
        for ach in achievements[:20]:
            text += f"• {ach['name']} — {ach['description']}\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_achievement_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажите ID ачивки: /achievement 1"))
            return
        
        try:
            ach_id = int(context.args[0])
        except:
            await update.message.reply_text(s.error("❌ ID должен быть числом"))
            return
        
        self.db.cursor.execute("SELECT * FROM achievements_list WHERE id = ?", (ach_id,))
        ach = self.db.cursor.fetchone()
        
        if not ach:
            await update.message.reply_text(s.error("❌ Ачивка не найдена"))
            return
        
        ach = dict(ach)
        
        text = (
            f"# Спектр | Ачивка {ach_id}\n\n"
            f"🏅 {ach['name']}\n"
            f"📝 {ach['description']}\n\n"
            f"🎁 Награда:\n"
        )
        
        if ach['reward_neons'] > 0:
            text += f"• {ach['reward_neons']} 💜 неонов\n"
        if ach['reward_glitches'] > 0:
            text += f"• {ach['reward_glitches']} 🖥 глитчей\n"
        if ach['reward_title']:
            text += f"• Титул: {ach['reward_title']}\n"
        if ach['reward_status']:
            text += f"• Статус: {ach['reward_status']}\n"
        
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
        await update.message.reply_text(s.success("✅ Ваши ачивки теперь видны всем"))
    
    async def cmd_achievements_private(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], platform="telegram", achievements_visible=0)
        await update.message.reply_text(s.success("✅ Ваши ачивки теперь скрыты от других"))

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
            await update.message.reply_text(s.error("❌ Укажите номер кружка: /circle 1"))
            return
        
        try:
            circle_num = int(context.args[0])
        except:
            await update.message.reply_text(s.error("❌ Номер должен быть числом"))
            return
        
        chat_id = update.effective_chat.id
        self.db.cursor.execute("SELECT * FROM circles WHERE chat_id = ? ORDER BY created_at", (chat_id,))
        circles = self.db.cursor.fetchall()
        
        if circle_num < 1 or circle_num > len(circles):
            await update.message.reply_text(s.error("❌ Кружок с таким номером не найден"))
            return
        
        circle = dict(circles[circle_num - 1])
        members = json.loads(circle['members'])
        
        creator = self.db.get_user_by_id(circle['created_by'])
        creator_name = creator.get('nickname') or creator['first_name'] if creator else "Неизвестно"
        
        text = (
            f"{s.header(f'🔄 КРУЖОК: {circle['name']}')}\n\n"
            f"📝 {circle['description']}\n\n"
            f"👑 Создатель: {creator_name}\n"
            f"👥 Участников: {len(members)}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_create_circle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 1:
            await update.message.reply_text(s.error("❌ Укажите название кружка: /createcircle Название"))
            return
        
        name = " ".join(context.args)
        user_data = self.db.get_user(update.effective_user.id)
        chat_id = update.effective_chat.id
        
        circle_id = self.db.create_circle(chat_id, name, "", user_data['id'])
        
        if not circle_id:
            await update.message.reply_text(s.error("❌ Не удалось создать кружок"))
            return
        
        await update.message.reply_text(s.success(f"✅ Кружок '{name}' создан!"))
    
    async def cmd_join_circle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажите номер кружка: /joincircle 1"))
            return
        
        try:
            circle_num = int(context.args[0])
        except:
            await update.message.reply_text(s.error("❌ Номер должен быть числом"))
            return
        
        user_data = self.db.get_user(update.effective_user.id)
        chat_id = update.effective_chat.id
        
        self.db.cursor.execute("SELECT * FROM circles WHERE chat_id = ? ORDER BY created_at", (chat_id,))
        circles = self.db.cursor.fetchall()
        
        if circle_num < 1 or circle_num > len(circles):
            await update.message.reply_text(s.error("❌ Кружок с таким номером не найден"))
            return
        
        circle = dict(circles[circle_num - 1])
        
        if self.db.join_circle(circle['id'], user_data['id']):
            await update.message.reply_text(s.success(f"✅ Вы присоединились к кружку '{circle['name']}'"))
        else:
            await update.message.reply_text(s.error("❌ Не удалось присоединиться"))
    
    async def cmd_leave_circle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажите номер кружка: /leavecircle 1"))
            return
        
        try:
            circle_num = int(context.args[0])
        except:
            await update.message.reply_text(s.error("❌ Номер должен быть числом"))
            return
        
        user_data = self.db.get_user(update.effective_user.id)
        chat_id = update.effective_chat.id
        
        self.db.cursor.execute("SELECT * FROM circles WHERE chat_id = ? ORDER BY created_at", (chat_id,))
        circles = self.db.cursor.fetchall()
        
        if circle_num < 1 or circle_num > len(circles):
            await update.message.reply_text(s.error("❌ Кружок с таким номером не найден"))
            return
        
        circle = dict(circles[circle_num - 1])
        
        if self.db.leave_circle(circle['id'], user_data['id']):
            await update.message.reply_text(s.success(f"✅ Вы покинули кружок '{circle['name']}'"))
        else:
            await update.message.reply_text(s.error("❌ Не удалось покинуть кружок"))

    # ===== ЗАКЛАДКИ =====
    async def cmd_add_bookmark(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text(s.error("❌ Использование: /addbookmark Название ссылка"))
            return
        
        name = context.args[0]
        content = " ".join(context.args[1:])
        user_data = self.db.get_user(update.effective_user.id)
        chat_id = update.effective_chat.id
        
        message_id = update.message.reply_to_message.message_id if update.message.reply_to_message else None
        
        bookmark_id = self.db.add_bookmark(chat_id, user_data['id'], name, content, message_id)
        
        await update.message.reply_text(s.success(f"✅ Закладка '{name}' сохранена! ID: {bookmark_id}"))
    
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
            await update.message.reply_text(s.error("❌ Укажите ID закладки: /bookmark 123"))
            return
        
        try:
            bookmark_id = int(context.args[0])
        except:
            await update.message.reply_text(s.error("❌ ID должен быть числом"))
            return
        
        chat_id = update.effective_chat.id
        self.db.cursor.execute("SELECT * FROM bookmarks WHERE id = ? AND chat_id = ?", (bookmark_id, chat_id))
        bm = self.db.cursor.fetchone()
        
        if not bm:
            await update.message.reply_text(s.error("❌ Закладка не найдена"))
            return
        
        bm = dict(bm)
        user = self.db.get_user_by_id(bm['user_id'])
        user_name = user.get('nickname') or user['first_name'] if user else "Неизвестно"
        
        text = (
            f"{s.header(f'📌 ЗАКЛАДКА: {bm['name']}')}\n\n"
            f"{bm['content']}\n\n"
            f"👤 Добавил: {user_name}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_remove_bookmark(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажите ID закладки: /removebookmark 123"))
            return
        
        try:
            bookmark_id = int(context.args[0])
        except:
            await update.message.reply_text(s.error("❌ ID должен быть числом"))
            return
        
        user_data = self.db.get_user(update.effective_user.id)
        chat_id = update.effective_chat.id
        
        self.db.cursor.execute("SELECT user_id FROM bookmarks WHERE id = ? AND chat_id = ?", (bookmark_id, chat_id))
        row = self.db.cursor.fetchone()
        
        if not row:
            await update.message.reply_text(s.error("❌ Закладка не найдена"))
            return
        
        if row[0] != user_data['id'] and user_data['rank'] < 2:
            await update.message.reply_text(s.error("❌ У вас нет прав на удаление этой закладки"))
            return
        
        self.db.cursor.execute("DELETE FROM bookmarks WHERE id = ?", (bookmark_id,))
        self.db.conn.commit()
        
        await update.message.reply_text(s.success("✅ Закладка удалена"))
    
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
    
    async def cmd_my_bookmarks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.cmd_bookmarks(update, context)

    # ===== ТАЙМЕРЫ =====
    async def cmd_add_timer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text(s.error("❌ Использование: /addtimer 30м /ping"))
            return
        
        time_str = context.args[0]
        command = " ".join(context.args[1:])
        
        minutes = parse_time(time_str)
        if not minutes:
            await update.message.reply_text(s.error("❌ Неверный формат времени. Используйте: 30м, 2ч, 1д"))
            return
        
        user_data = self.db.get_user(update.effective_user.id)
        chat_id = update.effective_chat.id
        execute_at = datetime.now() + timedelta(minutes=minutes)
        
        timer_id = self.db.add_timer(chat_id, user_data['id'], execute_at, command)
        
        if not timer_id:
            await update.message.reply_text(s.error("❌ Достигнут лимит таймеров в чате (макс. 5)"))
            return
        
        await update.message.reply_text(
            s.success(f"✅ Таймер #{timer_id} установлен на {execute_at.strftime('%d.%m.%Y %H:%M')}")
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
            await update.message.reply_text(s.error("❌ Укажите ID таймера: /removetimer 1"))
            return
        
        try:
            timer_id = int(context.args[0])
        except:
            await update.message.reply_text(s.error("❌ ID должен быть числом"))
            return
        
        user_data = self.db.get_user(update.effective_user.id)
        chat_id = update.effective_chat.id
        
        self.db.cursor.execute("SELECT user_id FROM timers WHERE id = ? AND chat_id = ?", (timer_id, chat_id))
        row = self.db.cursor.fetchone()
        
        if not row:
            await update.message.reply_text(s.error("❌ Таймер не найден"))
            return
        
        if row[0] != user_data['id'] and user_data['rank'] < 2:
            await update.message.reply_text(s.error("❌ У вас нет прав на удаление этого таймера"))
            return
        
        self.db.cursor.execute("UPDATE timers SET status = 'cancelled' WHERE id = ?", (timer_id,))
        self.db.conn.commit()
        
        await update.message.reply_text(s.success(f"✅ Таймер #{timer_id} удалён"))

    # ===== НАГРАДЫ =====
    async def cmd_give_award(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 3:
            await update.message.reply_text(s.error("❌ Использование: /giveaward 4 @user Текст"))
            return
        
        try:
            degree = int(context.args[0])
        except:
            await update.message.reply_text(s.error("❌ Степень должна быть числом от 1 до 8"))
            return
        
        username = context.args[1].replace('@', '')
        award_text = " ".join(context.args[2:])
        
        if degree < 1 or degree > 8:
            await update.message.reply_text(s.error("❌ Степень должна быть от 1 до 8"))
            return
        
        user_data = self.db.get_user(update.effective_user.id)
        if degree > user_data['rank'] and user_data['rank'] < 8:
            await update.message.reply_text(s.error(f"❌ Ваш ранг позволяет выдавать только степени до {user_data['rank']}"))
            return
        
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        award_id = self.db.give_award(update.effective_chat.id, target['id'], user_data['id'], degree, award_text)
        
        await update.message.reply_text(s.success(f"✅ Награда #{award_id} степени {degree} выдана {target['first_name']}!"))
        
        try:
            await self.send_private_message(
                target['telegram_id'],
                f"🏅 ВАМ ВЫДАЛИ НАГРАДУ!\n\n"
                f"Степень: {degree}\n"
                f"Текст: {award_text}\n"
                f"От: {update.effective_user.first_name}"
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
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
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
            text += f"• Степень {award['degree']} — {award['text']}\n"
            text += f"  От {award['awarded_by_name']}, {date}\n\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_remove_award(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text(s.error("❌ Использование: /removeaward 123 @user"))
            return
        
        try:
            award_id = int(context.args[0])
        except:
            await update.message.reply_text(s.error("❌ ID награды должен быть числом"))
            return
        
        username = context.args[1].replace('@', '')
        user_data = self.db.get_user(update.effective_user.id)
        
        if user_data['rank'] < 2:
            await update.message.reply_text(s.error("❌ Недостаточно прав для снятия наград"))
            return
        
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        self.db.cursor.execute("DELETE FROM awards WHERE id = ? AND chat_id = ?", (award_id, update.effective_chat.id))
        self.db.conn.commit()
        
        if self.db.cursor.rowcount > 0:
            await update.message.reply_text(s.success(f"✅ Награда #{award_id} снята"))
        else:
            await update.message.reply_text(s.error("❌ Награда не найдена"))

    # ===== КЛАНЫ =====
    async def cmd_clan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)
        
        if not user_data.get('clan_id', 0):
            await update.message.reply_text("ℹ️ Вы не состоите в клане")
            return
        
        clan = self.get_clan(user_data['clan_id'])
        if not clan:
            await update.message.reply_text("❌ Клан не найден")
            return
        
        members = self.get_clan_members(clan['id'])
        
        text = f"🏰 КЛАН: {clan['name']}\n\n"
        text += f"📊 Уровень: {clan.get('level', 1)}\n"
        text += f"💰 Казна: {clan.get('coins', 0)} 💰\n"
        text += f"👥 Участников: {len(members)}\n\n"
        text += "**Участники:\n"
        
        for member in members:
            name = member.get('nickname') or member['first_name']
            role_emoji = "👑" if member.get('clan_role') == 'owner' else "🛡" if member.get('clan_role') == 'admin' else "👤"
            text += f"{role_emoji} {name}\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_clans(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.db.cursor.execute("SELECT name, level, members FROM clans ORDER BY level DESC LIMIT 10")
        clans = self.db.cursor.fetchall()
        
        if not clans:
            await update.message.reply_text("ℹ️ Нет созданных кланов")
            return
        
        text = "🏰 ТОП КЛАНОВ\n\n"
        for i, clan in enumerate(clans, 1):
            text += f"{i}. {clan[0]} — ур.{clan[1]}, {clan[2]} участников\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_create_clan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Укажите название клана: /createclan Название")
            return
        
        name = " ".join(context.args)
        user_data = self.db.get_user(update.effective_user.id)
        
        if user_data.get('clan_id', 0):
            await update.message.reply_text("❌ Вы уже в клане")
            return
        
        if user_data['coins'] < 1000:
            await update.message.reply_text(f"❌ Недостаточно монет. Нужно 1000 💰")
            return
        
        clan_id = self.db.create_clan(update.effective_chat.id, name, "", user_data['id'])
        if not clan_id:
            await update.message.reply_text("❌ Клан с таким названием уже существует")
            return
        
        self.db.add_coins(user_data['id'], -1000)
        
        await update.message.reply_text(f"✅ Клан '{name}' создан!")
    
    async def cmd_join_clan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Укажите название клана: /joinclan Название")
            return
        
        name = " ".join(context.args)
        user_data = self.db.get_user(update.effective_user.id)
        
        if user_data.get('clan_id', 0):
            await update.message.reply_text("❌ Вы уже в клане")
            return
        
        self.db.cursor.execute("SELECT * FROM clans WHERE name = ? AND chat_id = ?", (name, update.effective_chat.id))
        clan = self.db.cursor.fetchone()
        
        if not clan:
            await update.message.reply_text("❌ Клан не найден")
            return
        
        if self.db.join_clan(clan[0], user_data['id']):
            await update.message.reply_text(f"✅ Вы вступили в клан '{name}'")
        else:
            await update.message.reply_text("❌ Не удалось вступить в клан")
    
    async def cmd_leave_clan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)
        
        if not user_data.get('clan_id', 0):
            await update.message.reply_text("❌ Вы не в клане")
            return
        
        if user_data.get('clan_role') == 'owner':
            await update.message.reply_text("❌ Владелец не может покинуть клан")
            return
        
        if self.db.leave_clan(user_data['id']):
            await update.message.reply_text("✅ Вы покинули клан")
        else:
            await update.message.reply_text("❌ Не удалось покинуть клан")
    
    def get_clan(self, clan_id: int) -> Optional[Dict]:
        self.db.cursor.execute("SELECT * FROM clans WHERE id = ?", (clan_id,))
        row = self.db.cursor.fetchone()
        return dict(row) if row else None
    
    def get_clan_members(self, clan_id: int) -> List[Dict]:
        self.db.cursor.execute("SELECT id, first_name, nickname, clan_role FROM users WHERE clan_id = ?", (clan_id,))
        return [dict(row) for row in self.db.cursor.fetchall()]

    # ===== БОНУСЫ =====
    async def cmd_bonuses(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = """
🎁 КИБЕР-БОНУСЫ

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
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_bonus_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажите название бонуса"))
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
                text = (
                    f"**{title}**\n\n"
                    f"💰 Цена: {price} 💜\n"
                    f"⏳ Длительность: {duration}\n\n"
                    f"{desc}\n\n"
                    f"🛒 Купить: /buybonus {key} 1"
                )
                await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
                return
        
        await update.message.reply_text(s.error("❌ Бонус не найден"))
    
    async def cmd_buy_bonus(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text(s.error("❌ Использование: /buybonus [название] [срок]"))
            return
        
        name = context.args[0].lower()
        try:
            duration = int(context.args[1])
        except:
            await update.message.reply_text(s.error("❌ Срок должен быть числом"))
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
            await update.message.reply_text("❌ Бонус не найден")
            return
        
        total = price * duration
        
        if user_data['neons'] < total:
            await update.message.reply_text(f"❌ Недостаточно неонов. Нужно {total} 💜")
            return
        
        if self.db.buy_bonus(user_data['id'], bonus_type, duration, total):
            await update.message.reply_text(s.success(f"✅ Бонус '{name}' куплен на {duration} мес. за {total} 💜"))
        else:
            await update.message.reply_text(s.error("❌ Ошибка при покупке"))
    
    async def _check_rp_packet(self, user_id: int) -> bool:
        user = self.db.get_user_by_id(user_id)
        if not user:
            return False
        
        if user.get('rp_packet_until') and datetime.fromisoformat(user['rp_packet_until']) > datetime.now():
            return True
        if user.get('cyber_status_until') and datetime.fromisoformat(user['cyber_status_until']) > datetime.now():
            return True
        
        return False
    
    async def cmd_cyber_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.cmd_bonus_info(update, context)
    
    async def cmd_buy_cyber_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.cmd_buy_bonus(update, context)
    
    async def cmd_glitch_hammer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.cmd_bonus_info(update, context)
    
    async def cmd_use_glitch_hammer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 1:
            await update.message.reply_text(s.error("❌ Укажите пользователя: /use_glitch_hammer @user"))
            return
        
        username = context.args[0].replace('@', '')
        user_data = self.db.get_user(update.effective_user.id)
        chat_id = update.effective_chat.id
        
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        if target['rank'] >= user_data['rank'] and user_data['id'] != OWNER_ID:
            await update.message.reply_text(s.error("❌ Нельзя применить к модератору выше рангом"))
            return
        
        if self.db.use_glitch_hammer(user_data['id'], chat_id, target['id']):
            until = self.db.mute_user(target['id'], 24*60, user_data['id'], "Глитч-молот")
            
            # Отправляем уведомление в ЛС
            await self.send_private_message(
                target['telegram_id'],
                f"🔨     ГЛИТЧ-МОЛОТ**\n\n"
                f"🦸 Модератор: {update.effective_user.first_name}\n"
                f"⏳ Срок: 24 часа\n"
                f"💬 Причина: Глитч-молот"
            )
            
            await update.message.reply_text(s.success(f"✅ Глитч-молот применён к {target['first_name']} на 24 часа!"))
        else:
            await update.message.reply_text(s.error("❌ У вас нет активного глитч-молота"))
    
    async def cmd_turbo_drive(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.cmd_bonus_info(update, context)
    
    async def cmd_buy_turbo_drive(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.cmd_buy_bonus(update, context)
    
    async def cmd_invisible(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.cmd_bonus_info(update, context)
    
    async def cmd_use_invisible(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat.type != "private":
            await update.message.reply_text(s.error("❌ Эта команда работает только в ЛС"))
            return
        
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажите текст сообщения"))
            return
        
        text = " ".join(context.args)
        user_data = self.db.get_user(update.effective_user.id)
        
        if not self.db.has_invisible_bonus(user_data['id']):
            await update.message.reply_text(s.error("❌ У вас нет активного бонуса 'Невидимка'"))
            return
        
        await update.message.reply_text(s.success("✅ Анонимное сообщение отправлено!"))
    
    async def cmd_allow_invisible(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 1:
            await update.message.reply_text(s.error("❌ Укажите пользователя: /allow_invisible @user"))
            return
        
        username = context.args[0].replace('@', '')
        user_data = self.db.get_user(update.effective_user.id)
        chat_id = update.effective_chat.id
        
        if user_data['rank'] < 3:
            await update.message.reply_text(s.error("❌ Недостаточно прав"))
            return
        
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        self.db.cursor.execute("DELETE FROM invisible_bans WHERE chat_id = ? AND user_id = ?", (chat_id, target['id']))
        self.db.conn.commit()
        
        await update.message.reply_text(s.success(f"✅ {target['first_name']} может использовать невидимку"))
    
    async def cmd_ban_invisible(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 1:
            await update.message.reply_text(s.error("❌ Укажите пользователя: /ban_invisible @user"))
            return
        
        username = context.args[0].replace('@', '')
        user_data = self.db.get_user(update.effective_user.id)
        chat_id = update.effective_chat.id
        
        if user_data['rank'] < 3:
            await update.message.reply_text(s.error("❌ Недостаточно прав"))
            return
        
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        self.db.cursor.execute("INSERT OR REPLACE INTO invisible_bans (chat_id, user_id, banned_by) VALUES (?, ?, ?)",
                             (chat_id, target['id'], user_data['id']))
        self.db.conn.commit()
        
        await update.message.reply_text(s.success(f"✅ {target['first_name']} забанен в невидимке"))
    
    async def cmd_neon_nick(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.cmd_bonus_info(update, context)
    
    async def cmd_buy_neon_nick(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.cmd_buy_bonus(update, context)
    
    async def cmd_cyber_luck(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.cmd_bonus_info(update, context)
    
    async def cmd_buy_cyber_luck(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.cmd_buy_bonus(update, context)
    
    async def cmd_firewall(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.cmd_bonus_info(update, context)
    
    async def cmd_buy_firewall(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.cmd_buy_bonus(update, context)
    
    async def cmd_rp_packet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.cmd_bonus_info(update, context)
    
    async def cmd_buy_rp_packet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.cmd_buy_bonus(update, context)

    # ===== РП КОМАНДЫ =====
    async def cmd_rp_hack(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_rp_packet(update.effective_user.id):
            await update.message.reply_text(s.error("❌ Для этой команды нужен РП-пакет или Кибер-статус"))
            return
        
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажите пользователя: /взломать @user"))
            return
        
        username = context.args[0].replace('@', '')
        target = self.db.get_user_by_username(username)
        target_name = target.get('nickname') or target['first_name'] if target else username
        
        actions = [
            f"💻 Взломал аккаунт {target_name} и получил доступ к переписке",
            f"🔓 Взломал базу данных и узнал все секреты {target_name}",
            f"📱 Взломал телефон {target_name} и читает сообщения"
        ]
        
        await update.message.reply_text(f"🤖 {random.choice(actions)}")
    
    async def cmd_rp_glitch(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_rp_packet(update.effective_user.id):
            await update.message.reply_text(s.error("❌ Для этой команды нужен РП-пакет или Кибер-статус"))
            return
        
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажите пользователя: /заглючить @user"))
            return
        
        username = context.args[0].replace('@', '')
        target = self.db.get_user_by_username(username)
        target_name = target.get('nickname') or target['first_name'] if target else username
        
        actions = [
            f"⚡ Вызвал системный глитч у {target_name}, теперь он двоится",
            f"💫 Заглючил {target_name}, теперь он разговаривает с собой",
            f"🌀 Внёс ошибку в код {target_name}, делает странные вещи"
        ]
        
        await update.message.reply_text(f"🤖 {random.choice(actions)}")
    
    async def cmd_rp_reboot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_rp_packet(update.effective_user.id):
            await update.message.reply_text(s.error("❌ Для этой команды нужен РП-пакет или Кибер-статус"))
            return
        
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажите пользователя: /перегрузить @user"))
            return
        
        username = context.args[0].replace('@', '')
        target = self.db.get_user_by_username(username)
        target_name = target.get('nickname') or target['first_name'] if target else username
        
        await update.message.reply_text(f"🤖 Перезагрузил {target_name}. Подождите 5 секунд... 🔄")
    
    async def cmd_rp_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_rp_packet(update.effective_user.id):
            await update.message.reply_text(s.error("❌ Для этой команды нужен РП-пакет или Кибер-статус"))
            return
        
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажите пользователя: /закодить @user"))
            return
        
        username = context.args[0].replace('@', '')
        target = self.db.get_user_by_username(username)
        target_name = target.get('nickname') or target['first_name'] if target else username
        
        code = f"function {target_name}() {{ return 'робот'; }}"
        await update.message.reply_text(f"🤖 Закодил {target_name} в функцию:\n`{code}`", parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_rp_digitize(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_rp_packet(update.effective_user.id):
            await update.message.reply_text(s.error("❌ Для этой команды нужен РП-пакет или Кибер-статус"))
            return
        
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажите пользователя: /оцифровать @user"))
            return
        
        username = context.args[0].replace('@', '')
        target = self.db.get_user_by_username(username)
        target_name = target.get('nickname') or target['first_name'] if target else username
        
        binary = ' '.join(format(ord(c), '08b') for c in target_name[:3])
        await update.message.reply_text(f"🤖 Оцифровал {target_name}: `{binary}...`", parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_rp_hack_deep(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_rp_packet(update.effective_user.id):
            await update.message.reply_text(s.error("❌ Для этой команды нужен РП-пакет или Кибер-статус"))
            return
        
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажите пользователя: /хакнуть @user"))
            return
        
        username = context.args[0].replace('@', '')
        target = self.db.get_user_by_username(username)
        target_name = target.get('nickname') or target['first_name'] if target else username
        
        data = {
            'IP': f'192.168.{random.randint(1,255)}.{random.randint(1,255)}',
            'Пароль': '*' * random.randint(6, 12),
            'Баланс': f'{random.randint(0,1000)} 💰'
        }
        
        text = f"🤖 Данные {target_name}:\n"
        for key, value in data.items():
            text += f"• {key}: {value}\n"
        
        await update.message.reply_text(text)
    
    async def cmd_rp_download(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_rp_packet(update.effective_user.id):
            await update.message.reply_text(s.error("❌ Для этой команды нужен РП-пакет или Кибер-статус"))
            return
        
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажите пользователя: /скачать @user"))
            return
        
        username = context.args[0].replace('@', '')
        target = self.db.get_user_by_username(username)
        target_name = target.get('nickname') or target['first_name'] if target else username
        
        size = random.randint(1, 100)
        await update.message.reply_text(f"🤖 Скачиваю данные {target_name}... {size}% [░░░░░░░░░░]")
        await asyncio.sleep(1)
        await update.message.reply_text(f"🤖 Скачивание завершено! Получено {random.randint(10,500)} МБ данных.")
    
    async def cmd_rp_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_rp_packet(update.effective_user.id):
            await update.message.reply_text(s.error("❌ Для этой команды нужен РП-пакет или Кибер-статус"))
            return
        
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажите пользователя: /обновить @user"))
            return
        
        username = context.args[0].replace('@', '')
        target = self.db.get_user_by_username(username)
        target_name = target.get('nickname') or target['first_name'] if target else username
        
        version = f"v{random.randint(1,9)}.{random.randint(0,9)}.{random.randint(0,9)}"
        await update.message.reply_text(f"🤖 Обновляю {target_name} до версии {version}...")
        await asyncio.sleep(1)
        await update.message.reply_text(f"🤖 Обновление завершено! Добавлены новые функции.")

    # ===== ТЕЛЕГРАМ БОНУСЫ =====
    async def cmd_tg_premium(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = """
⭐️ TELEGRAM PREMIUM

💰 Цены:
• 3 месяца — 1500 💜
• 6 месяцев — 2500 💜
• 12 месяцев — 4000 💜

📝 Команды:
• /buy_tg_premium 3 — купить себе
• /gift_tg_premium 3 @user — подарить
        """
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_buy_tg_premium(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 1:
            await update.message.reply_text(s.error("❌ Укажите срок: /buy_tg_premium 3"))
            return
        
        try:
            months = int(context.args[0])
        except:
            await update.message.reply_text(s.error("❌ Срок должен быть числом"))
            return
        
        prices = {3: 1500, 6: 2500, 12: 4000}
        if months not in prices:
            await update.message.reply_text(s.error("❌ Доступные периоды: 3, 6, 12 месяцев"))
            return
        
        user_data = self.db.get_user(update.effective_user.id)
        price = prices[months]
        
        if user_data['neons'] < price:
            await update.message.reply_text(s.error(f"❌ Недостаточно неонов. Нужно {price} 💜"))
            return
        
        self.db.add_neons(user_data['id'], -price)
        await update.message.reply_text(s.success(f"✅ Telegram Premium на {months} мес. активирован!"))
    
    async def cmd_gift_tg_premium(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text(s.error("❌ Использование: /gift_tg_premium 3 @user"))
            return
        
        try:
            months = int(context.args[0])
        except:
            await update.message.reply_text(s.error("❌ Срок должен быть числом"))
            return
        
        username = context.args[1].replace('@', '')
        
        prices = {3: 1500, 6: 2500, 12: 4000}
        if months not in prices:
            await update.message.reply_text(s.error("❌ Доступные периоды: 3, 6, 12 месяцев"))
            return
        
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        user_data = self.db.get_user(update.effective_user.id)
        price = prices[months]
        
        if user_data['neons'] < price:
            await update.message.reply_text(s.error(f"❌ Недостаточно неонов. Нужно {price} 💜"))
            return
        
        self.db.add_neons(user_data['id'], -price)
        await update.message.reply_text(s.success(f"✅ Telegram Premium на {months} мес. подарен {target['first_name']}!"))
    
    async def cmd_tg_gift(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = """
🎁 TELEGRAM ПОДАРКИ

💰 Цена: 500 💜 за подарок

📝 Команды:
• /buy_tg_gift — купить подарок
• /gift_tg_gift @user — подарить подарок
        """
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_buy_tg_gift(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)
        
        if user_data['neons'] < 500:
            await update.message.reply_text(s.error(f"❌ Недостаточно неонов. Нужно 500 💜"))
            return
        
        self.db.add_neons(user_data['id'], -500)
        gifts = ["🎂 Торт", "🎈 Шары", "🎉 Хлопушка", "🎊 Конфетти", "🎀 Бантик"]
        gift = random.choice(gifts)
        
        await update.message.reply_text(s.success(f"✅ Вы купили подарок: {gift}!"))
    
    async def cmd_gift_tg_gift(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 1:
            await update.message.reply_text(s.error("❌ Укажите пользователя: /gift_tg_gift @user"))
            return
        
        username = context.args[0].replace('@', '')
        user_data = self.db.get_user(update.effective_user.id)
        
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        if user_data['neons'] < 500:
            await update.message.reply_text(s.error(f"❌ Недостаточно неонов. Нужно 500 💜"))
            return
        
        self.db.add_neons(user_data['id'], -500)
        gifts = ["🎂 Торт", "🎈 Шары", "🎉 Хлопушка", "🎊 Конфетти", "🎀 Бантик"]
        gift = random.choice(gifts)
        
        await update.message.reply_text(s.success(f"✅ Вы подарили {gift} пользователю {target['first_name']}!"))
    
    async def cmd_tg_stars(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = """
🌟 TELEGRAM ЗВЁЗДЫ

💰 Курс: 1 ⭐️ = 10 💜

📝 Команды:
• /buy_tg_stars 100 — купить 100 звёзд
• /transfer_tg_stars 50 @user — передать звёзды
• /my_tg_stars — история транзакций
        """
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_buy_tg_stars(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 1:
            await update.message.reply_text(s.error("❌ Укажите количество: /buy_tg_stars 100"))
            return
        
        try:
            stars = int(context.args[0])
        except:
            await update.message.reply_text(s.error("❌ Количество должно быть числом"))
            return
        
        user_data = self.db.get_user(update.effective_user.id)
        price = stars * 10
        
        if user_data['neons'] < price:
            await update.message.reply_text(s.error(f"❌ Недостаточно неонов. Нужно {price} 💜"))
            return
        
        self.db.add_neons(user_data['id'], -price)
        await update.message.reply_text(s.success(f"✅ Куплено {stars} ⭐️ за {price} 💜!"))
    
    async def cmd_transfer_tg_stars(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text(s.error("❌ Использование: /transfer_tg_stars 50 @user"))
            return
        
        try:
            stars = int(context.args[0])
        except:
            await update.message.reply_text(s.error("❌ Количество должно быть числом"))
            return
        
        username = context.args[1].replace('@', '')
        target = self.db.get_user_by_username(username)
        
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        await update.message.reply_text(s.success(f"✅ Передано {stars} ⭐️ пользователю {target['first_name']}!"))
    
    async def cmd_my_tg_stars(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(s.info("ℹ️ Функция в разработке"))

    # ===== ТЕМЫ ДЛЯ РОЛЕЙ =====
    async def cmd_themes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = """
🎨 ТЕМЫ РОЛЕЙ

• `!темы default` — Стандартная
• `!темы cyber` — Киберпанк
• `!темы fantasy` — Фэнтези
• `!темы anime` — Аниме
• `!темы military` — Военная

Примеры названий:
• Киберпанк: Хакер, Кодер, Админ
• Фэнтези: Маг, Воин, Эльф
        """
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_apply_theme(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(s.info("ℹ️ Функция в разработке"))
    
    async def cmd_apply_theme_by_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(s.info("ℹ️ Функция в разработке"))

    # ===== ПРИВЯЗКА ЧАТА =====
    async def cmd_bind_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat.type == "private":
            await update.message.reply_text(s.error("❌ Эта команда работает только в группах"))
            return
        
        chat_id = update.effective_chat.id
        chat_title = update.effective_chat.title
        
        chat_code = hashlib.md5(f"{chat_id}_{random.randint(1000,9999)}".encode()).hexdigest()[:8]
        
        self.db.cursor.execute('''
            INSERT INTO chat_settings (chat_id, chat_name, chat_code)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET chat_code = excluded.chat_code
        ''', (chat_id, chat_title, chat_code))
        self.db.conn.commit()
        
        await update.message.reply_text(
            f"{s.success('✅ Чат привязан!')}\n\n"
            f"Код чата: `{chat_code}`",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def cmd_chat_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        
        self.db.cursor.execute("SELECT chat_code FROM chat_settings WHERE chat_id = ?", (chat_id,))
        row = self.db.cursor.fetchone()
        
        if not row:
            await update.message.reply_text(s.error("❌ Чат не привязан. Используйте !привязать"))
            return
        
        await update.message.reply_text(f"🔑 Код чата: `{row[0]}`", parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_change_chat_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 1:
            await update.message.reply_text(s.error("❌ Укажите новый код: /changecode x5g7k9"))
            return
        
        new_code = context.args[0]
        user_data = self.db.get_user(update.effective_user.id)
        chat_id = update.effective_chat.id
        
        if user_data['rank'] < 3 and user_data['id'] != OWNER_ID:
            await update.message.reply_text(s.error("❌ Недостаточно прав"))
            return
        
        if len(new_code) < 3 or len(new_code) > 10:
            await update.message.reply_text(s.error("❌ Код должен быть от 3 до 10 символов"))
            return
        
        self.db.cursor.execute("SELECT chat_id FROM chat_settings WHERE chat_code = ?", (new_code,))
        if self.db.cursor.fetchone():
            await update.message.reply_text(s.error("❌ Этот код уже занят"))
            return
        
        self.db.cursor.execute("UPDATE chat_settings SET chat_code = ? WHERE chat_id = ?", (new_code, chat_id))
        self.db.conn.commit()
        
        await update.message.reply_text(s.success(f"✅ Код чата изменён на `{new_code}`"))
    
    async def cmd_treasury(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        
        self.db.cursor.execute("SELECT treasury_neons, treasury_glitches FROM chat_settings WHERE chat_id = ?", (chat_id,))
        row = self.db.cursor.fetchone()
        
        if not row:
            await update.message.reply_text(s.error("❌ Настройки чата не найдены"))
            return
        
        neons, glitches = row[0], row[1]
        
        text = (
            f"{s.header('💰 КУБЫШКА ЧАТА')}\n\n"
            f"{s.stat('Неонов', f'{neons} 💜')}\n"
            f"{s.stat('Глитчей', f'{glitches} 🖥')}\n\n"
            f"{s.cmd('/treasurywithdraw', 'вывести неоны в кошелёк')}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_treasury_withdraw(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)
        chat_id = update.effective_chat.id
        
        if user_data['rank'] < 3 and user_data['id'] != OWNER_ID:
            await update.message.reply_text(s.error("❌ Недостаточно прав"))
            return
        
        self.db.cursor.execute("SELECT treasury_neons FROM chat_settings WHERE chat_id = ?", (chat_id,))
        row = self.db.cursor.fetchone()
        
        if not row or row[0] == 0:
            await update.message.reply_text(s.error("❌ В кубышке нет неонов"))
            return
        
        neons = row[0]
        
        self.db.add_neons(user_data['id'], neons)
        self.db.cursor.execute("UPDATE chat_settings SET treasury_neons = 0 WHERE chat_id = ?", (chat_id,))
        self.db.conn.commit()
        
        await update.message.reply_text(s.success(f"✅ {neons} 💜 переведены в ваш кошелёк!"))

    # ===== РАЗВЛЕЧЕНИЯ =====
    async def cmd_joke(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        jokes = [
            "Встречаются два программиста:\n— Слышал, ты женился?\n— Да.\n— Ну и как она?\n— Да нормально, интерфейс дружественный...",
            "— Доктор, у меня глисты.\n— А вы что, их видите?\n— Нет, я с ними переписываюсь.",
            "Идут два кота по крыше. Один говорит:\n— Мяу.\n— Мяу-мяу.\n— Ты чё, с ума сошёл? Нас же люди услышат!",
        ]
        await update.message.reply_text(f"😄 {random.choice(jokes)}")
    
    async def cmd_fact(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        facts = [
            "Осьминоги имеют три сердца и голубую кровь.",
            "Бананы технически являются ягодами, а клубника — нет.",
            "В Швейцарии запрещено держать только одну морскую свинку.",
        ]
        await update.message.reply_text(f"🔍 {random.choice(facts)}")
    
    async def cmd_quote(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        quotes = [
            "Жизнь — это то, что с тобой происходит, пока ты строишь планы. — Джон Леннон",
            "Будьте тем изменением, которое вы хотите увидеть в мире. — Махатма Ганди",
            "Единственный способ делать великие дела — любить то, что вы делаете. — Стив Джобс",
        ]
        await update.message.reply_text(f"📜 {random.choice(quotes)}")
    
    async def cmd_whoami(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        roles = ["супергерой", "злодей", "тайный агент", "космонавт", "пират"]
        await update.message.reply_text(f"🦸 Вы — {random.choice(roles)}!")
    
    async def cmd_advice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        advices = [
            "Пейте больше воды.",
            "Высыпайтесь — это важно для здоровья.",
            "Делайте зарядку по утрам.",
        ]
        await update.message.reply_text(f"💡 {random.choice(advices)}")
    
    async def cmd_compatibility(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text(s.error("❌ Укажите двух пользователей: /compatibility @user1 @user2"))
            return
        
        username1 = context.args[0].replace('@', '')
        username2 = context.args[1].replace('@', '')
        
        user1 = self.db.get_user_by_username(username1)
        user2 = self.db.get_user_by_username(username2)
        
        if not user1 or not user2:
            await update.message.reply_text(s.error("❌ Пользователи не найдены"))
            return
        
        name1 = user1.get('nickname') or user1['first_name']
        name2 = user2.get('nickname') or user2['first_name']
        
        compatibility = random.randint(0, 100)
        
        if compatibility < 30:
            emoji = "💔"
            text = "Очень низкая совместимость"
        elif compatibility < 50:
            emoji = "🤔"
            text = "Ниже среднего"
        elif compatibility < 70:
            emoji = "👍"
            text = "Неплохая совместимость"
        elif compatibility < 90:
            emoji = "💕"
            text = "Хорошая совместимость"
        else:
            emoji = "💖"
            text = "Идеальная совместимость!"
        
        await update.message.reply_text(
            f"{s.header('💞 СОВМЕСТИМОСТЬ')}\n\n"
            f"{emoji} {name1} и {name2}\n\n"
            f"Совместимость: {compatibility}%\n{text}",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def cmd_weather(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            city = "Москва"
        else:
            city = " ".join(context.args)
        
        temp = random.randint(-10, 30)
        conditions = ["ясно", "облачно", "пасмурно", "дождь", "снег", "гроза"]
        condition = random.choice(conditions)
        wind = random.randint(0, 10)
        humidity = random.randint(30, 90)
        
        text = (
            f"🌦 Погода в {city}:\n"
            f"🌡 {temp}°C, {condition}\n"
            f"💨 ветер {wind} м/с\n"
            f"💧 влажность {humidity}%"
        )
        
        await update.message.reply_text(text)
    
    async def cmd_random(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            max_num = 100
        else:
            try:
                max_num = int(context.args[0])
            except:
                await update.message.reply_text(s.error("❌ Укажите число"))
                return
        
        result = random.randint(0, max_num)
        await update.message.reply_text(f"🎲 Случайное число: {result}", parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_choose(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажите варианты через или: /choose чай или кофе"))
            return
        
        text = " ".join(context.args)
        options = re.split(r'\s+или\s+', text)
        
        if len(options) < 2:
            await update.message.reply_text(s.error("❌ Нужно минимум 2 варианта через 'или'"))
            return
        
        choice = random.choice(options)
        await update.message.reply_text(f"🤔 Я выбираю: {choice}", parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_dane(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("❌ Задайте вопрос: /dane сегодня будет дождь?"))
            return
        
        answers = [
            "🎱 Безусловно да",
            "🎱 Определённо да",
            "🎱 Без сомнений",
            "🎱 Да — определённо",
            "🎱 Мне кажется — да",
            "🎱 Вероятнее всего",
            "🎱 Хорошие перспективы",
            "🎱 Знаки говорят — да",
            "🎱 Пока не ясно, попробуй снова",
            "🎱 Спроси позже",
            "🎱 Лучше не рассказывать",
            "🎱 Сейчас нельзя предсказать",
            "🎱 Сконцентрируйся и спроси опять",
            "🎱 Даже не думай",
            "🎱 Мой ответ — нет",
            "🎱 По моим данным — нет",
            "🎱 Перспективы не очень хорошие",
            "🎱 Весьма сомнительно",
        ]
        
        await update.message.reply_text(f"❓ {random.choice(answers)}")
    
    async def cmd_ship(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            chat_id = update.effective_chat.id
            cursor = self.db.cursor
            cursor.execute("SELECT DISTINCT user_id FROM messages WHERE chat_id = ? ORDER BY RANDOM() LIMIT 2", (chat_id,))
            users = cursor.fetchall()
            
            if len(users) < 2:
                await update.message.reply_text(s.error("❌ Недостаточно участников для шипперинга"))
                return
            
            user1_id, user2_id = users[0][0], users[1][0]
        else:
            username1 = context.args[0].replace('@', '')
            username2 = context.args[1].replace('@', '')
            
            user1 = self.db.get_user_by_username(username1)
            user2 = self.db.get_user_by_username(username2)
            
            if not user1 or not user2:
                await update.message.reply_text(s.error("❌ Пользователи не найдены"))
                return
            
            user1_id, user2_id = user1['id'], user2['id']
        
        user1_data = self.db.get_user_by_id(user1_id)
        user2_data = self.db.get_user_by_id(user2_id)
        
        name1 = user1_data.get('nickname') or user1_data['first_name']
        name2 = user2_data.get('nickname') or user2_data['first_name']
        
        compatibility = random.randint(0, 100)
        
        if compatibility < 30:
            emoji = "💔"
            desc = "Очень низкая совместимость"
        elif compatibility < 50:
            emoji = "🤔"
            desc = "Ниже среднего"
        elif compatibility < 70:
            emoji = "👍"
            desc = "Неплохая совместимость"
        elif compatibility < 90:
            emoji = "💕"
            desc = "Хорошая совместимость"
        else:
            emoji = "💖"
            desc = "Идеальная совместимость!"
        
        self.db.create_pair(update.effective_chat.id, user1_id, user2_id)
        
        await update.message.reply_text(
            f"{s.header('💞 ШИППЕРИМ')}\n\n"
            f"{emoji} {name1} + {name2}\n\n"
            f"Совместимость: {compatibility}%\n{desc}",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def cmd_pairing(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        pairs = self.db.get_chat_pairs(update.effective_chat.id)
        
        if not pairs:
            await update.message.reply_text(s.info("В этом чате пока нет пар"))
            return
        
        text = f"{s.header('💞 ПАРЫ ЧАТА')}\n\n"
        for pair in pairs[:10]:
            text += f"{pair['name1']} + {pair['name2']}\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_pairs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.cmd_pairing(update, context)

    # ===== ПОЛЕЗНОЕ =====
    async def cmd_ping(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        start = time.time()
        msg = await update.message.reply_text("🏓 Понг...")
        end = time.time()
        ping = int((end - start) * 1000)
        await msg.edit_text(f"🏓 Понг!\n⏱️ {ping} мс", parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_uptime(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        uptime = datetime.now() - self.start_time
        days = uptime.days
        hours = uptime.seconds // 3600
        minutes = (uptime.seconds % 3600) // 60
        
        await update.message.reply_text(
            f"⏱️ Аптайм: {days}д {hours}ч {minutes}м",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def cmd_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        users_count = self.db.cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        messages_count = self.db.cursor.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        
        text = (
            f"{s.header('🤖 ИНФОРМАЦИЯ О БОТЕ')}\n\n"
            f"Название: {BOT_NAME}\n"
            f"Версия: {BOT_VERSION}\n"
            f"Владелец: {OWNER_USERNAME}\n\n"
            f"{s.stat('Пользователей', users_count)}\n"
            f"{s.stat('Сообщений', messages_count)}\n"
            f"{s.stat('Команд', '300+')}\n"
            f"{s.stat('AI', 'Подключен' if self.ai and self.ai.is_available else 'Не подключен')}\n"
            f"{s.stat('VK', 'Подключен' if self.vk and self.vk.is_available else 'Не подключен')}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    # ===== ТОПЫ =====
    async def cmd_top(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = f"{s.header('🏆 ТОП ИГРОКОВ')}\n\n"
        top_coins = self.db.get_top("coins", 5)
        text += f"{s.section('💰 ПО МОНЕТАМ')}"
        for i, row in enumerate(top_coins, 1):
            name = row[1] or row[0]
            text += f"{i}. {name} — {row[2]} 💰\n"
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_top_coins(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        top = self.db.get_top("coins", 10)
        text = f"{s.header('💰 ТОП ПО МОНЕТАМ')}\n\n"
        for i, row in enumerate(top, 1):
            name = row[1] or row[0]
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} {name} — {row[2]} 💰\n"
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_top_level(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        top = self.db.get_top("level", 10)
        text = f"{s.header('📊 ТОП ПО УРОВНЮ')}\n\n"
        for i, row in enumerate(top, 1):
            name = row[1] or row[0]
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} {name} — {row[2]} уровень\n"
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_top_neons(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        top = self.db.get_top("neons", 10)
        text = f"{s.header('💜 ТОП ПО НЕОНАМ')}\n\n"
        for i, row in enumerate(top, 1):
            name = row[1] or row[0]
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} {name} — {row[2]} 💜\n"
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_top_glitches(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        top = self.db.get_top("glitches", 10)
        text = f"{s.header('🖥 ТОП ПО ГЛИТЧАМ')}\n\n"
        for i, row in enumerate(top, 1):
            name = row[1] or row[0]
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} {name} — {row[2]} 🖥\n"
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    # ===== СТАТИСТИКА ЧАТА (РУССКИЕ КОМАНДЫ) =====
    async def cmd_chat_stats_today(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._chat_stats_period(update, "day")
    
    async def cmd_chat_stats_week(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._chat_stats_period(update, "week")
    
    async def cmd_chat_stats_month(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._chat_stats_period(update, "month")
    
    async def cmd_chat_stats_all(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._chat_stats_period(update, "all")
    
    async def cmd_stats_custom(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        parts = text.split()
        
        if len(parts) < 2:
            return
        
        try:
            limit = int(parts[1])
        except:
            return
        
        period = "day"
        if len(parts) > 2:
            period_map = {"неделя": "week", "месяц": "month", "вся": "all"}
            period = period_map.get(parts[2].lower(), "day")
        
        await self._chat_stats_period(update, period, limit)
    
    async def _chat_stats_period(self, update: Update, period: str, limit: int = 10):
        chat_id = update.effective_chat.id
        cursor = self.db.cursor
        
        now = datetime.now()
        
        if period == "day":
            time_ago = now - timedelta(days=1)
            period_name = "день"
        elif period == "week":
            time_ago = now - timedelta(days=7)
            period_name = "неделю"
        elif period == "month":
            time_ago = now - timedelta(days=30)
            period_name = "месяц"
        else:
            time_ago = datetime(2000, 1, 1)
            period_name = "всё время"
        
        cursor.execute('''
            SELECT username, first_name, COUNT(*) as msg_count
            FROM messages 
            WHERE chat_id = ? AND timestamp > ?
            GROUP BY user_id 
            ORDER BY msg_count DESC 
            LIMIT ?
        ''', (chat_id, time_ago.isoformat(), limit))
        
        top_users = cursor.fetchall()
        
        if not top_users:
            await update.message.reply_text(s.info("Нет данных за этот период"))
            return
        
        text = f"{s.header(f'🏆 ТОП ЗА {period_name.upper()}')}\n\n"
        for i, (username, first_name, count) in enumerate(top_users, 1):
            name = username or first_name or "Пользователь"
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} {name} — {count} 💬\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_top_chat_today(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._chat_stats_period(update, "day")
    
    async def cmd_top_chat_week(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._chat_stats_period(update, "week")
    
    async def cmd_top_chat_month(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._chat_stats_period(update, "month")
    
    async def cmd_top_chat_all(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._chat_stats_period(update, "all")

    # =========================================================================
    # МЕТОДЫ МОДЕРАЦИИ - УПРАВЛЕНИЕ РАНГАМИ
    # =========================================================================
    
    async def _set_rank(self, update: Update, target_rank: int):
        """Общая логика установки ранга"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 4 and user.id != OWNER_ID:
            await update.message.reply_text("⛔️ Недостаточно прав. Нужен ранг 4+")
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
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        if target_user['rank'] >= user_data['rank'] and user.id != OWNER_ID:
            await update.message.reply_text("⛔️ Нельзя назначить ранг выше своего")
            return
        
        self.db.set_rank(target_user['id'], target_rank, user_data['id'])
        rank_info = RANKS[target_rank]
        await update.message.reply_text(
            f"✅ Ранг назначен!\n\n"
            f"👤 Пользователь: {target_user['first_name']}\n"
            f"🎖️ Ранг: {rank_info['emoji']} {rank_info['name']}"
        )
    
    async def cmd_set_rank(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._set_rank(update, 1)
    
    async def cmd_set_rank2(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._set_rank(update, 2)
    
    async def cmd_set_rank3(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._set_rank(update, 3)
    
    async def cmd_set_rank4(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._set_rank(update, 4)
    
    async def cmd_set_rank5(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._set_rank(update, 5)
    
    async def cmd_lower_rank(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Понизить ранг пользователя"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 4 and user.id != OWNER_ID:
            await update.message.reply_text("⛔️ Недостаточно прав")
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
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        if target_user['rank'] <= 0:
            await update.message.reply_text("❌ Пользователь и так участник")
            return
        
        if target_user['rank'] >= user_data['rank'] and user.id != OWNER_ID:
            await update.message.reply_text("⛔️ Нельзя понизить модератора выше рангом")
            return
        
        new_rank = target_user['rank'] - 1
        self.db.set_rank(target_user['id'], new_rank, user_data['id'])
        rank_info = RANKS[new_rank]
        await update.message.reply_text(
            f"✅ Ранг понижен!\n\n"
            f"👤 Пользователь: {target_user['first_name']}\n"
            f"🎖️ Новый ранг: {rank_info['emoji']} {rank_info['name']}"
        )
    
    async def cmd_remove_rank(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Снять ранг с пользователя"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 4 and user.id != OWNER_ID:
            await update.message.reply_text("⛔️ Недостаточно прав")
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
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        if target_user['rank'] >= user_data['rank'] and user.id != OWNER_ID:
            await update.message.reply_text("⛔️ Нельзя снять модератора выше рангом")
            return
        
        self.db.set_rank(target_user['id'], 0, user_data['id'])
        await update.message.reply_text(
            f"✅ Модератор снят!\n\n"
            f"👤 Пользователь: {target_user['first_name']}\n"
            f"🎖️ Теперь: 👤 Участник"
        )
    
    async def cmd_remove_left(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Очистка вышедших модераторов"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data['rank'] < 4 and user.id != OWNER_ID:
            await update.message.reply_text("⛔️ Недостаточно прав")
            return
        
        await update.message.reply_text("✅ Проверка вышедших модераторов выполнена")
    
    async def cmd_remove_all_ranks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Снять всех модераторов"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data['rank'] < 5 and user.id != OWNER_ID:
            await update.message.reply_text("⛔️ Только для создателя")
            return
        
        self.db.cursor.execute("SELECT id FROM users WHERE rank > 0")
        mods = self.db.cursor.fetchall()
        
        for mod_id in mods:
            self.db.set_rank(mod_id[0], 0, user_data['id'])
        
        await update.message.reply_text(f"✅ Снято модераторов: {len(mods)}")
    
    async def cmd_who_admins(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список администраторов"""
        admins = self.db.get_admins()
        if not admins:
            await update.message.reply_text("👥 В чате нет администраторов")
            return
        
        text = "👑 АДМИНИСТРАЦИЯ\n\n"
        for admin in admins:
            name = admin['first_name']
            username = f" (@{admin['username']})" if admin['username'] else ""
            rank_emoji = RANKS[admin['rank']]["emoji"]
            text += f"{rank_emoji} {name}{username} — {admin['rank_name']}\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    # =========================================================================
    # МЕТОДЫ МОДЕРАЦИИ - ПРЕДУПРЕЖДЕНИЯ (ВАРНЫ)
    # =========================================================================
    
    async def cmd_warn(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выдать предупреждение"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        chat_id = update.effective_chat.id
        
        if user_data['rank'] < 1 and user.id != OWNER_ID:
            await update.message.reply_text("⛔️ Недостаточно прав. Нужен ранг 1+", parse_mode=ParseMode.MARKDOWN)
            return
        
        target_user = None
        reason = "Нарушение правил"
        
        if update.message.reply_to_message:
            target_id = update.message.reply_to_message.from_user.id
            target_user = self.db.get_user_by_id(self.db.get_user(target_id)['id'])
            parts = text.split('\n', 1)
            if len(parts) > 1 and parts[1].strip():
                reason = parts[1].strip()
        else:
            match = re.search(r'(?:варн|пред)\s+@?(\S+)(?:\s+(.+))?', text, re.IGNORECASE)
            if match:
                username = match.group(1)
                target_user = self.db.get_user_by_username(username)
                if match.group(2):
                    reason = match.group(2)
        
        if not target_user:
            await update.message.reply_text("❌ Пользователь не найден", parse_mode=ParseMode.MARKDOWN)
            return
        
        if target_user['rank'] >= user_data['rank'] and user.id != OWNER_ID:
            await update.message.reply_text("⛔️ Нельзя выдать предупреждение модератору выше рангом", parse_mode=ParseMode.MARKDOWN)
            return
        
        warns = self.db.add_warn(target_user['id'], user_data['id'], reason)
        
        admin_name = f"@{user.username}" if user.username else user.first_name
        target_name = f"@{target_user['username']}" if target_user.get('username') else target_user['first_name']
        
        # Уведомление в ЛС
        try:
            await context.bot.send_message(
                target_user['telegram_id'],
                f"⚠️ Предупреждение ({warns}/4)\n\n"
                f"💬 Причина: {reason}\n"
                f"🦸 Модератор: {admin_name}",
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass
        
        await update.message.reply_text(
            f"⚠️ Предупреждение ({warns}/4)\n\n"
            f"👤 Пользователь: {target_name}\n"
            f"💬 Причина: {reason}\n"
            f"🦸 Модератор: {admin_name}",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # АВТОМАТИЧЕСКИЕ ДЕЙСТВИЯ
        if warns == 2:
            minutes = 60
            self.db.mute_user(target_user['id'], minutes, user_data['id'], "2 предупреждения")
            try:
                until_date = int(time.time()) + (minutes * 60)
                permissions = {
                    'can_send_messages': False,
                    'can_send_media_messages': False,
                    'can_send_polls': False,
                    'can_send_other_messages': False,
                    'can_add_web_page_previews': False
                }
                await context.bot.restrict_chat_member(
                    chat_id=chat_id,
                    user_id=target_user['telegram_id'],
                    permissions=permissions,
                    until_date=until_date
                )
                await update.message.reply_text(f"🔇 Мут на 1 час\n\n👤 {target_name}", parse_mode=ParseMode.MARKDOWN)
            except Exception as e:
                logger.error(f"Ошибка мута: {e}")
        
        elif warns == 3:
            minutes = 1440
            self.db.mute_user(target_user['id'], minutes, user_data['id'], "3 предупреждения")
            try:
                until_date = int(time.time()) + (minutes * 60)
                permissions = {
                    'can_send_messages': False,
                    'can_send_media_messages': False,
                    'can_send_polls': False,
                    'can_send_other_messages': False,
                    'can_add_web_page_previews': False
                }
                await context.bot.restrict_chat_member(
                    chat_id=chat_id,
                    user_id=target_user['telegram_id'],
                    permissions=permissions,
                    until_date=until_date
                )
                await update.message.reply_text(f"🔇 Мут на 24 часа\n\n👤 {target_name}", parse_mode=ParseMode.MARKDOWN)
            except Exception as e:
                logger.error(f"Ошибка мута: {e}")
        
        elif warns >= 4:
            self.db.ban_user(target_user['id'], user_data['id'], "4 предупреждения")
            try:
                await context.bot.ban_chat_member(
                    chat_id=chat_id,
                    user_id=target_user['telegram_id']
                )
                await update.message.reply_text(f"🔴 Пользователь забанен (4/4)\n\n👤 {target_name}", parse_mode=ParseMode.MARKDOWN)
            except Exception as e:
                logger.error(f"Ошибка бана: {e}")
    
    async def cmd_warns(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список предупреждений пользователя"""
        if not context.args:
            await update.message.reply_text("❌ Укажите пользователя: `/warns @user`")
            return
        
        username = context.args[0].replace('@', '')
        target = self.db.get_user_by_username(username)
        
        if not target:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        warns_list = self.db.get_warns(target['id'])
        target_name = f"@{target['username']}" if target.get('username') else target['first_name']
        
        if not warns_list:
            await update.message.reply_text(f"📋 У {target_name} нет предупреждений")
            return
        
        text = f"📋 ПРЕДУПРЕЖДЕНИЯ: {target_name}\n\n"
        for warn in warns_list:
            admin = self.db.get_user_by_id(warn['admin_id'])
            admin_name = f"@{admin['username']}" if admin and admin.get('username') else (admin['first_name'] if admin else 'Система')
            date = datetime.fromisoformat(warn['date']).strftime("%d.%m.%Y %H:%M")
            text += (
                f"⚠️ ID {warn['id']}\n"
                f"💬 Причина: {warn['reason']}\n"
                f"🦸 Модератор: {admin_name}\n"
                f"📅 Дата: {date}\n\n"
            )
        
        text += f"📊 Всего: {len(warns_list)}/4"
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_my_warns(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Мои предупреждения"""
        user_data = self.db.get_user(update.effective_user.id)
        warns_list = self.db.get_warns(user_data['id'])
        
        if not warns_list:
            await update.message.reply_text("✅ У вас нет предупреждений")
            return
        
        user_name = f"@{user_data['username']}" if user_data.get('username') else user_data['first_name']
        text = f"📋 МОИ ПРЕДУПРЕЖДЕНИЯ: {user_name}\n\n"
        
        for warn in warns_list:
            admin = self.db.get_user_by_id(warn['admin_id'])
            admin_name = f"@{admin['username']}" if admin and admin.get('username') else (admin['first_name'] if admin else 'Система')
            date = datetime.fromisoformat(warn['date']).strftime("%d.%m.%Y %H:%M")
            text += (
                f"⚠️ ID {warn['id']}\n"
                f"💬 Причина: {warn['reason']}\n"
                f"🦸 Модератор: {admin_name}\n"
                f"📅 Дата: {date}\n\n"
            )
        
        text += f"📊 Всего: {len(warns_list)}/4"
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_unwarn(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Снять последнее предупреждение"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 1 and user.id != OWNER_ID:
            await update.message.reply_text("⛔️ Недостаточно прав")
            return
        
        target_user = None
        if update.message.reply_to_message:
            target_id = update.message.reply_to_message.from_user.id
            target_user = self.db.get_user_by_id(self.db.get_user(target_id)['id'])
        else:
            match = re.search(r'снять варн\s+@?(\S+)', text, re.IGNORECASE)
            if match:
                username = match.group(1)
                target_user = self.db.get_user_by_username(username)
        
        if not target_user:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        removed = self.db.remove_last_warn(target_user['id'], user_data['id'])
        target_name = f"@{target_user['username']}" if target_user.get('username') else target_user['first_name']
        admin_name = f"@{user.username}" if user.username else user.first_name
        
        if not removed:
            await update.message.reply_text(f"📋 У {target_name} нет предупреждений")
            return
        
        warns_list = self.db.get_warns(target_user['id'])
        remaining = len(warns_list)
        
        await update.message.reply_text(
            f"✅ Предупреждение снято\n\n"
            f"👤 Пользователь: {target_name}\n"
            f"🦸 Модератор: {admin_name}\n"
            f"📊 Осталось: {remaining}/4"
        )
    
    async def cmd_unwarn_all(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Снять все предупреждения"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 2 and user.id != OWNER_ID:
            await update.message.reply_text("⛔️ Недостаточно прав")
            return
        
        match = re.search(r'снять все варны\s+@?(\S+)', text, re.IGNORECASE)
        if not match:
            await update.message.reply_text("❌ Укажите пользователя")
            return
        
        username = match.group(1)
        target_user = self.db.get_user_by_username(username)
        
        if not target_user:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        warns_list = self.db.get_warns(target_user['id'])
        for _ in warns_list:
            self.db.remove_last_warn(target_user['id'], user_data['id'])
        
        target_name = target_user.get('nickname') or target_user['first_name']
        await update.message.reply_text(f"✅ Все предупреждения сняты с {target_name}")
    
    # =========================================================================
    # МЕТОДЫ МОДЕРАЦИИ - МУТ
    # =========================================================================
    
    async def cmd_mute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Замутить пользователя"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        chat_id = update.effective_chat.id
        
        if user_data['rank'] < 2 and user.id != OWNER_ID:
            await update.message.reply_text("⛔️ Недостаточно прав. Нужен ранг 2+")
            return
        
        match = re.search(r'мут\s+@?(\S+)(?:\s+(\d+[мчд]))?(?:\s+(.+))?', text, re.IGNORECASE)
        if not match:
            await update.message.reply_text("❌ Пример: мут @user 30м спам")
            return
        
        username = match.group(1)
        time_str = match.group(2) if match.group(2) else "60м"
        reason = match.group(3) if match.group(3) else "Нарушение правил"
        
        minutes = parse_time(time_str)
        if not minutes:
            await update.message.reply_text("❌ Неверный формат времени. Используйте: 30м, 2ч, 1д")
            return
        
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        if target['rank'] >= user_data['rank'] and user.id != OWNER_ID:
            await update.message.reply_text("⛔️ Нельзя замутить модератора выше рангом")
            return
        
        until = self.db.mute_user(target['id'], minutes, user_data['id'], reason)
        until_str = until.strftime("%d.%m.%Y %H:%M")
        
        mute_success = False
        try:
            until_date = int(time.time()) + (minutes * 60)
            permissions = {
                'can_send_messages': False,
                'can_send_media_messages': False,
                'can_send_polls': False,
                'can_send_other_messages': False,
                'can_add_web_page_previews': False
            }
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=target['telegram_id'],
                permissions=permissions,
                until_date=until_date
            )
            mute_success = True
        except Exception as e:
            logger.error(f"Ошибка мута: {e}")
        
        # Уведомление в ЛС
        try:
            await context.bot.send_message(
                target['telegram_id'],
                f"🔇 ВАС ЗАМУТИЛИ\n\n"
                f"⏱️ Срок: {time_str}\n"
                f"💬 Причина: {reason}\n"
                f"📅 До: {until_str}"
            )
        except:
            pass
        
        admin_name = f"@{user.username}" if user.username else user.first_name
        target_name = f"@{target['username']}" if target.get('username') else target['first_name']
        
        await update.message.reply_text(
            f"🔇 МУТ\n\n"
            f"👤 Пользователь: {target_name}\n"
            f"⏱️ Срок: {time_str}\n"
            f"📅 До: {until_str}\n"
            f"💬 Причина: {reason}\n"
            f"🦸 Модератор: {admin_name}\n\n"
            f"{'✅ Мут применен' if mute_success else '❌ Не удалось применить мут'}"
        )
    
    async def cmd_mutelist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список замученных пользователей"""
        muted = self.db.get_muted_users()
        
        if not muted:
            await update.message.reply_text("📋 Список замученных пуст")
            return
        
        text = "📋 СПИСОК ЗАМУЧЕННЫХ\n\n"
        for mute in muted[:15]:
            until = datetime.fromisoformat(mute['mute_until']).strftime("%d.%m %H:%M")
            name = mute['first_name']
            username = f" (@{mute['username']})" if mute.get('username') else ""
            text += f"🔇 {name}{username} — до {until}\n"
        
        if len(muted) > 15:
            text += f"\n👥 Всего: {len(muted)} (показаны первые 15)"
        else:
            text += f"\n👥 Всего: {len(muted)}"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_unmute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Снять мут"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        chat_id = update.effective_chat.id
        
        if user_data['rank'] < 2 and user.id != OWNER_ID:
            await update.message.reply_text("⛔️ Недостаточно прав")
            return
        
        username = text.replace('размут', '').replace('@', '').strip()
        if not username and update.message.reply_to_message:
            target_id = update.message.reply_to_message.from_user.id
            target = self.db.get_user_by_id(self.db.get_user(target_id)['id'])
        elif username:
            target = self.db.get_user_by_username(username)
        else:
            await update.message.reply_text("❌ Укажите пользователя")
            return
        
        if not target:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        self.db.unmute_user(target['id'], user_data['id'])
        
        try:
            permissions = {
                'can_send_messages': True,
                'can_send_media_messages': True,
                'can_send_polls': True,
                'can_send_other_messages': True,
                'can_add_web_page_previews': True
            }
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=target['telegram_id'],
                permissions=permissions
            )
        except:
            pass
        
        # Уведомление в ЛС
        try:
            await context.bot.send_message(
                target['telegram_id'],
                "✅ Мут снят"
            )
        except:
            pass
        
        admin_name = f"@{user.username}" if user.username else user.first_name
        target_name = f"@{target['username']}" if target.get('username') else target['first_name']
        
        await update.message.reply_text(f"✅ Мут снят с {target_name}")
    
    # =========================================================================
    # МЕТОДЫ МОДЕРАЦИИ - БАН
    # =========================================================================
    
    async def cmd_ban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Забанить пользователя"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        chat_id = update.effective_chat.id

        if user_data['rank'] < 2 and user.id != OWNER_ID:
            await update.message.reply_text("⛔️ Недостаточно прав. Нужен ранг 2+", parse_mode=ParseMode.MARKDOWN)
            return

        match = re.search(r'бан\s+@?(\S+)(?:\s+(.+))?', text, re.IGNORECASE)
        if not match:
            await update.message.reply_text("❌ Пример: `бан @user спам`", parse_mode=ParseMode.MARKDOWN)
            return

        username = match.group(1)
        reason = match.group(2) if match.group(2) else "Нарушение правил"

        target_data = self.db.get_user_by_username(username)
        if not target_data:
            await update.message.reply_text("❌ Пользователь не найден", parse_mode=ParseMode.MARKDOWN)
            return

        target_internal_id = target_data['id']
        target_telegram_id = target_data['telegram_id']
        target_name = target_data.get('nickname') or target_data['first_name']

        if target_data['rank'] >= user_data['rank'] and user.id != OWNER_ID:
            await update.message.reply_text("⛔️ Нельзя забанить модератора выше рангом", parse_mode=ParseMode.MARKDOWN)
            return

        # Проверяем права бота
        try:
            bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
            if bot_member.status not in ['administrator', 'creator']:
                await update.message.reply_text("❌ Бот не администратор! Выдайте права.", parse_mode=ParseMode.MARKDOWN)
                return
            if not bot_member.can_restrict_members:
                await update.message.reply_text("❌ У бота нет права на блокировку!", parse_mode=ParseMode.MARKDOWN)
                return
        except Exception as e:
            logger.error(f"Ошибка проверки прав: {e}")

        # НАСТОЯЩИЙ БАН В TELEGRAM
        try:
            await context.bot.ban_chat_member(
                chat_id=chat_id,
                user_id=target_telegram_id,
                until_date=int(time.time()) + (30 * 24 * 60 * 60)  # 30 дней
            )
            ban_success_telegram = True
            logger.info(f"Пользователь {target_telegram_id} забанен в чате {chat_id}")
        except Exception as e:
            ban_success_telegram = False
            logger.error(f"Ошибка бана в Telegram для {target_telegram_id}: {e}")
            await update.message.reply_text(f"❌ Ошибка Telegram: {str(e)[:100]}", parse_mode=ParseMode.MARKDOWN)
            return

        # БАН В БАЗЕ ДАННЫХ
        if ban_success_telegram:
            self.db.ban_user(target_internal_id, user_data['id'], reason)

            admin_name = f"@{user.username}" if user.username else user.first_name
            target_display_name = f"@{target_data['username']}" if target_data.get('username') else target_name

            text = (
                f"🔴 Пользователь забанен\n\n"
                f"👢 Пользователь: {target_display_name}\n"
                f"🦸 Модератор: {admin_name}\n"
                f"💬 Причина: {reason}\n"
                f"📅 Срок: 30 дней"
            )
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

            # Уведомление в ЛС
            try:
                await context.bot.send_message(
                    target_telegram_id,
                    f"🔴 Вас заблокировали в чате\n\n"
                    f"👢 Чат: {update.effective_chat.title}\n"
                    f"🦸 Модератор: {admin_name}\n"
                    f"💬 Причина: {reason}\n"
                    f"📅 Срок: 30 дней",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Не удалось уведомить пользователя {target_telegram_id} о бане: {e}")
    
    async def cmd_banlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список забаненных"""
        bans = self.db.get_banlist()
        
        if not bans:
            await update.message.reply_text("📋 Список забаненных пуст")
            return
        
        text = "📋 СПИСОК ЗАБАНЕННЫХ\n\n"
        for ban in bans[:15]:
            name = ban.get('first_name', 'Неизвестно')
            username = f" (@{ban['username']})" if ban.get('username') else ""
            text += f"🔴 {name}{username}\n"
        
        if len(bans) > 15:
            text += f"\n👥 Всего: {len(bans)} (показаны первые 15)"
        else:
            text += f"\n👥 Всего: {len(bans)}"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_unban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Разбанить пользователя"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        chat_id = update.effective_chat.id

        if user_data['rank'] < 2 and user.id != OWNER_ID:
            await update.message.reply_text("⛔️ Недостаточно прав. Нужен ранг 2+", parse_mode=ParseMode.MARKDOWN)
            return

        username = text.replace('разбан', '').replace('@', '').strip()
        if not username:
            await update.message.reply_text("❌ Укажите пользователя: `разбан @user`", parse_mode=ParseMode.MARKDOWN)
            return

        target_data = self.db.get_user_by_username(username)
        if not target_data:
            await update.message.reply_text("❌ Пользователь не найден", parse_mode=ParseMode.MARKDOWN)
            return

        target_internal_id = target_data['id']
        target_telegram_id = target_data['telegram_id']
        target_name = target_data.get('nickname') or target_data['first_name']

        # Разбан в Telegram
        try:
            await context.bot.unban_chat_member(
                chat_id=chat_id,
                user_id=target_telegram_id,
                only_if_banned=True
            )
            unban_success_telegram = True
        except Exception as e:
            unban_success_telegram = False
            logger.error(f"Ошибка разбана в Telegram для {target_telegram_id}: {e}")

        # Разбан в БД
        self.db.unban_user(target_internal_id, user_data['id'])

        admin_name = f"@{user.username}" if user.username else user.first_name
        target_display_name = f"@{target_data['username']}" if target_data.get('username') else target_name

        if unban_success_telegram:
            await update.message.reply_text(
                f"✅ Бан снят\n\n"
                f"👤 Пользователь: {target_display_name}\n"
                f"🦸 Модератор: {admin_name}",
                parse_mode=ParseMode.MARKDOWN
            )
            # Уведомление в ЛС
            try:
                await context.bot.send_message(
                    target_telegram_id,
                    f"✅ Вас разблокировали в чате\n\n"
                    f"👢 Чат: {update.effective_chat.title}\n"
                    f"🦸 Модератор: {admin_name}",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Не удалось уведомить {target_telegram_id} о разбане: {e}")
        else:
            await update.message.reply_text(
                f"⚠️ Бан снят в базе данных, но возникла ошибка при разбане в Telegram.\n\n"
                f"👤 Пользователь: {target_display_name}",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def cmd_kick(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Кикнуть пользователя"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        chat_id = update.effective_chat.id
        
        if user_data['rank'] < 1 and user.id != OWNER_ID:
            await update.message.reply_text("⛔️ Недостаточно прав")
            return
        
        username = text.replace('кик', '').replace('@', '').strip()
        target = self.db.get_user_by_username(username)
        
        if not target and update.message.reply_to_message:
            target_id = update.message.reply_to_message.from_user.id
            target = self.db.get_user_by_id(self.db.get_user(target_id)['id'])
        
        if not target:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        try:
            await context.bot.ban_chat_member(chat_id, target['telegram_id'])
            await context.bot.unban_chat_member(chat_id, target['telegram_id'])
            await update.message.reply_text(f"✅ {target['first_name']} исключен")
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {e}")
    
    # =========================================================================
    # МЕТОДЫ МОДЕРАЦИИ - ПРОВЕРКА ПРАВ
    # =========================================================================
    
    async def cmd_checkrights(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Проверка прав бота в чате"""
        chat_id = update.effective_chat.id
        
        try:
            bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
            
            if bot_member.status == 'creator':
                await update.message.reply_text("✅ Бот является создателем чата! Полные права.")
            elif bot_member.status == 'administrator':
                rights = []
                if bot_member.can_restrict_members:
                    rights.append("✅ может банить/мутить")
                else:
                    rights.append("❌ НЕТ ПРАВА на бан/мут!")
                
                if bot_member.can_delete_messages:
                    rights.append("✅ может удалять сообщения")
                else:
                    rights.append("❌ не может удалять сообщения")
                
                if bot_member.can_pin_messages:
                    rights.append("✅ может закреплять")
                else:
                    rights.append("❌ не может закреплять")
                
                rights_text = "\n".join(rights)
                await update.message.reply_text(
                    f"👑 Бот администратор\n\n{rights_text}"
                )
            else:
                await update.message.reply_text("❌ Бот не администратор! Выдайте права.")
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка проверки: {e}")
    
    # =========================================================================
    # МЕТОДЫ МОДЕРАЦИИ - ТРИГГЕРЫ
    # =========================================================================
    
    async def cmd_add_trigger(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Добавить триггер"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 3 and user.id != OWNER_ID:
            await update.message.reply_text("⛔️ Недостаточно прав")
            return
        
        text = text[9:].strip()
        if "=" not in text:
            await update.message.reply_text("❌ Формат: +триггер слово = действие")
            return
        
        word, action = text.split("=", 1)
        word = word.strip().lower()
        action = action.strip()
        
        action_parts = action.split()
        action_type = action_parts[0].lower()
        action_value = action_parts[1] if len(action_parts) > 1 else None
        
        if action_type not in ["delete", "mute", "warn", "ban"]:
            await update.message.reply_text("❌ Действие должно быть: delete, mute, warn, ban")
            return
        
        self.db.cursor.execute('''
            INSERT INTO triggers (chat_id, word, action, action_value, created_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (update.effective_chat.id, word, action_type, action_value, user_data['id']))
        self.db.conn.commit()
        
        await update.message.reply_text(f"✅ Триггер добавлен: {word} -> {action}")
    
    async def cmd_remove_trigger(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Удалить триггер"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 3 and user.id != OWNER_ID:
            await update.message.reply_text("⛔️ Недостаточно прав")
            return
        
        trigger_id = text[9:].strip()
        if not trigger_id.isdigit():
            await update.message.reply_text("❌ Укажите ID триггера")
            return
        
        self.db.cursor.execute("DELETE FROM triggers WHERE id = ? AND chat_id = ?", 
                             (int(trigger_id), update.effective_chat.id))
        self.db.conn.commit()
        
        await update.message.reply_text("✅ Триггер удален")
    
    async def cmd_list_triggers(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список триггеров в чате"""
        self.db.cursor.execute("SELECT id, word, action, action_value FROM triggers WHERE chat_id = ?", 
                             (update.effective_chat.id,))
        triggers = self.db.cursor.fetchall()
        
        if not triggers:
            await update.message.reply_text("ℹ️ В этом чате нет триггеров")
            return
        
        text = "🔹 ТРИГГЕРЫ ЧАТА\n\n"
        for trigger in triggers:
            action_text = trigger[2]
            if trigger[3]:
                action_text += f" {trigger[3]}"
            text += f"ID: {trigger[0]} | {trigger[1]} → {action_text}\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    # =========================================================================
    # МЕТОДЫ МОДЕРАЦИИ - НАСТРОЙКИ ЧАТА
    # =========================================================================
    
    async def _toggle_setting(self, update: Update, setting: str):
        """Включить/выключить настройку"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data['rank'] < 3 and user.id != OWNER_ID:
            await update.message.reply_text("⛔️ Недостаточно прав")
            return
        
        parts = update.message.text.split()
        if len(parts) < 2:
            await update.message.reply_text("❌ Укажите on или off")
            return
        
        state = 1 if parts[1].lower() in ["on", "вкл", "да"] else 0
        
        self.db.cursor.execute(f'''
            INSERT INTO chat_settings (chat_id, {setting})
            VALUES (?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET {setting} = excluded.{setting}
        ''', (update.effective_chat.id, state))
        self.db.conn.commit()
        
        status = "включен" if state else "выключен"
        names = {"antimat": "Антимат", "antilink": "Антиссылки", "antiflood": "Антифлуд"}
        await update.message.reply_text(f"✅ {names.get(setting, setting)} {status}")
    
    async def cmd_set_antimat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._toggle_setting(update, "antimat")
    
    async def cmd_set_antilink(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._toggle_setting(update, "antilink")
    
    async def cmd_set_antiflood(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._toggle_setting(update, "antiflood")
    
    async def cmd_clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Очистить сообщения"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data['rank'] < 2 and user.id != OWNER_ID:
            await update.message.reply_text("⛔️ Недостаточно прав")
            return
        
        parts = update.message.text.split()
        if len(parts) < 2:
            await update.message.reply_text("❌ Укажите количество: чистка 50")
            return
        
        try:
            count = int(parts[1])
            if count > 100:
                count = 100
        except:
            await update.message.reply_text("❌ Количество должно быть числом")
            return
        
        try:
            await update.message.delete()
            messages = []
            async for msg in context.bot.get_chat_history(update.effective_chat.id, limit=count):
                messages.append(msg.message_id)
            
            if messages:
                await context.bot.delete_messages(update.effective_chat.id, messages)
                await context.bot.send_message(
                    update.effective_chat.id, 
                    f"✅ Удалено {len(messages)} сообщений",
                    disable_notification=True
                )
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {e}")
    
    async def cmd_clear_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Очистить сообщения пользователя"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 2 and user.id != OWNER_ID:
            await update.message.reply_text("⛔️ Недостаточно прав")
            return
        
        username = text.replace('чистка от', '').strip().replace('@', '')
        target = self.db.get_user_by_username(username)
        
        if not target:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        await update.message.reply_text(f"🔄 Удаляю сообщения {target['first_name']}...")
    
    async def cmd_set_welcome(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установить приветствие"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data['rank'] < 3 and user.id != OWNER_ID:
            await update.message.reply_text("⛔️ Недостаточно прав")
            return
        
        welcome_text = update.message.text[12:].strip()
        if not welcome_text:
            await update.message.reply_text("❌ Укажите текст приветствия")
            return
        
        self.db.cursor.execute('''
            INSERT INTO chat_settings (chat_id, welcome)
            VALUES (?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET welcome = excluded.welcome
        ''', (update.effective_chat.id, welcome_text))
        self.db.conn.commit()
        
        await update.message.reply_text("✅ Приветствие установлено")
    
    async def cmd_set_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установить правила"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data['rank'] < 3 and user.id != OWNER_ID:
            await update.message.reply_text("⛔️ Недостаточно прав")
            return
        
        rules_text = update.message.text[9:].strip()
        if not rules_text:
            await update.message.reply_text("❌ Укажите текст правил")
            return
        
        self.db.cursor.execute('''
            INSERT INTO chat_settings (chat_id, rules)
            VALUES (?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET rules = excluded.rules
        ''', (update.effective_chat.id, rules_text))
        self.db.conn.commit()
        
        await update.message.reply_text("✅ Правила установлены")
    
    async def cmd_show_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать правила"""
        self.db.cursor.execute("SELECT rules FROM chat_settings WHERE chat_id = ?", (update.effective_chat.id,))
        row = self.db.cursor.fetchone()
        
        if row and row[0]:
            await update.message.reply_text(f"📜 Правила чата:\n\n{row[0]}")
        else:
            await update.message.reply_text("ℹ️ В этом чате ещё не установлены правила")
    
    async def cmd_set_captcha(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Включить/выключить капчу"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data['rank'] < 3 and user.id != OWNER_ID:
            await update.message.reply_text("⛔️ Недостаточно прав")
            return
        
        parts = update.message.text.split()
        if len(parts) < 2:
            await update.message.reply_text("❌ Укажите on или off")
            return
        
        state = 1 if parts[1].lower() in ["on", "вкл", "да"] else 0
        
        self.db.cursor.execute('''
            INSERT INTO chat_settings (chat_id, captcha)
            VALUES (?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET captcha = excluded.captcha
        ''', (update.effective_chat.id, state))
        self.db.conn.commit()
        
        status = "включена" if state else "выключена"
        await update.message.reply_text(f"✅ Капча {status}")
    
    # =========================================================================
    # МЕТОДЫ МОДЕРАЦИИ - ГОЛОСОВАНИЕ ЗА БАН
    # =========================================================================
    
    async def cmd_ban_vote(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Создать голосование за бан"""
        if len(context.args) < 1:
            await update.message.reply_text("❌ Использование: /banvote @user")
            return
        
        username = context.args[0].replace('@', '')
        user_data = self.db.get_user(update.effective_user.id)
        chat_id = update.effective_chat.id
        
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        required_votes = 5
        min_rank = 0
        
        if len(context.args) >= 3:
            try:
                required_votes = int(context.args[1])
                min_rank = int(context.args[2])
            except:
                pass
        
        vote_id = self.db.create_ban_vote(chat_id, target['id'], user_data['id'], required_votes, min_rank)
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ ЗА БАН", callback_data=f"vote_for_{vote_id}"),
                InlineKeyboardButton("❌ ПРОТИВ", callback_data=f"vote_against_{vote_id}")
            ]
        ])
        
        await update.message.reply_text(
            f"🗳 ГОЛОСОВАНИЕ ЗА БАН\n\n"
            f"👤 Цель:** {target['first_name']}\n"
            f"👑 Инициатор:** {update.effective_user.first_name}\n"
            f"📊 Требуется голосов: {required_votes}\n"
            f"🎚 Мин. ранг: {min_rank}\n\n"
            f"Голосуйте!",
            reply_markup=keyboard
        )
    
    async def cmd_stop_vote(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Остановить голосование"""
        if len(context.args) < 1:
            await update.message.reply_text("❌ Укажите пользователя: /stopvote @user")
            return
        
        username = context.args[0].replace('@', '')
        user_data = self.db.get_user(update.effective_user.id)
        chat_id = update.effective_chat.id
        
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        self.db.cursor.execute("SELECT * FROM ban_votes WHERE chat_id = ? AND target_id = ? AND status = 'active'",
                             (chat_id, target['id']))
        vote = self.db.cursor.fetchone()
        
        if not vote:
            await update.message.reply_text("❌ Активное голосование не найдено")
            return
        
        vote = dict(vote)
        
        if vote['created_by'] != user_data['id'] and user_data['rank'] < 3:
            await update.message.reply_text("❌ У вас нет прав на остановку этого голосования")
            return
        
        self.db.cursor.execute("UPDATE ban_votes SET status = 'stopped' WHERE id = ?", (vote['id'],))
        self.db.conn.commit()
        
        await update.message.reply_text("✅ Голосование остановлено")
    
    async def cmd_vote_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о голосовании"""
        if len(context.args) < 1:
            await update.message.reply_text("❌ Укажите пользователя: /voteinfo @user")
            return
        
        username = context.args[0].replace('@', '')
        chat_id = update.effective_chat.id
        
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        self.db.cursor.execute("SELECT * FROM ban_votes WHERE chat_id = ? AND target_id = ? AND status = 'active'",
                             (chat_id, target['id']))
        vote = self.db.cursor.fetchone()
        
        if not vote:
            await update.message.reply_text("❌ Активное голосование не найдено")
            return
        
        vote = dict(vote)
        creator = self.db.get_user_by_id(vote['created_by'])
        creator_name = creator.get('nickname') or creator['first_name'] if creator else "Неизвестно"
        
        text = (
            f"🗳 ИНФОРМАЦИЯ О ГОЛОСОВАНИИ\n\n"
            f"👤 Цель: {target['first_name']}\n"
            f"👑 Инициатор: {creator_name}\n"
            f"📊 Требуется голосов: {vote['required_votes']}\n"
            f"🎚 Мин. ранг: {vote['min_rank']}\n"
            f"✅ Голосов ЗА: {vote['votes_for']}\n"
            f"❌ Голосов ПРОТИВ: {vote['votes_against']}"
        )
        
        await update.message.reply_text(text)
    
    async def cmd_vote_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список активных голосований"""
        chat_id = update.effective_chat.id
        
        self.db.cursor.execute("SELECT * FROM ban_votes WHERE chat_id = ? AND status = 'active'", (chat_id,))
        votes = self.db.cursor.fetchall()
        
        if not votes:
            await update.message.reply_text("ℹ️ Нет активных голосований")
            return
        
        text = "🗳 АКТИВНЫЕ ГОЛОСОВАНИЯ\n\n"
        for vote in votes:
            vote = dict(vote)
            target = self.db.get_user_by_id(vote['target_id'])
            target_name = target.get('nickname') or target['first_name'] if target else "Неизвестно"
            text += f"• {target_name} — {vote['votes_for']}/{vote['required_votes']}\n"
        
        await update.message.reply_text(text)
        
    # ===== ТАЙНЫЙ ОРДЕН (УЛУЧШЕННАЯ ВЕРСИЯ) =====
    async def cmd_order(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о Тайном Ордене"""
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
👁️ ТАЙНЫЙ ОРДЕН

Цикл {order_dict['cycle_number']} активен!
Пять избранных уже среди нас...

🕵️ Раскрытие: {revelation}
📊 Участников: {len(members)}

Твой статус: {rank_info['name']}
{'🔮 ТЫ ИЗБРАН!' if in_order else '👤 Ты не в ордене... пока что.'}

📝 Команды:
/order rank — мой ранг
/order points — мои очки
                """
            else:
                text = f"""
👁️ ТАЙНЫЙ ОРДЕН

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
👁️ РАНГИ ОРДЕНА

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

Твой ранг: {rank_info['name']}
Очков: {rank_info['points']}
            """
            await update.message.reply_text(
                f"👁️ {ranks_text}",
                parse_mode=ParseMode.MARKDOWN
            )
        
        elif context.args[0].lower() == "points":
            text = f"""
👁️ МОИ ОЧКИ ОРДЕНА

📊 Всего очков: {rank_info['points']}
📈 Ранг: {rank_info['name']}

💡 Очки начисляются за:
• Активность в чате
• Победы в играх
• Особые достижения
            """
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_start_order(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Запустить новый цикл ордена (для админов)"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        chat_id = update.effective_chat.id
        
        if user_data['rank'] < 3 and user.id != OWNER_ID:
            await update.message.reply_text("❌ Только администраторы могут запустить орден.")
            return
        
        members, cycle = self.db.start_order_cycle(chat_id)
        
        for member_id in members:
            try:
                member = await self.get_user_name(member_id)
                # Отправляем в ЛС каждому избранному
                await self.send_private_message(
                    member_id,
                    f"👁️ Тайный орден\n\nТы избран. Орден следит за тобой...\n\n"
                    f"Цикл {cycle} начался. Твои действия будут влиять на ход истории."
                )
            except:
                pass
        
        await update.message.reply_text(
            f"👁️ ТАЙНЫЙ ОРДЕН\n\n"
            f"Цикл {cycle} начался.\n"
            f"Пять избранных уже среди нас...\n"
            f"Кто они? Узнаем через 7 дней."
        )
    
    async def cmd_reveal_order(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Раскрыть орден досрочно (для админов)"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        chat_id = update.effective_chat.id
        
        if user_data['rank'] < 3 and user.id != OWNER_ID:
            await update.message.reply_text("❌ Только администраторы могут раскрыть орден.")
            return
        
        result = self.db.reveal_order(chat_id)
        
        if not result:
            await update.message.reply_text("❌ Нет активного ордена.")
            return
        
        members = result['members']
        points = result['points']
        cycle = result['cycle']
        
        message = f"👁️ ТАЙНЫЙ ОРДЕН РАСКРЫТ!\n\n"
        message += "Всё это время среди вас были избранные...\n\n"
        
        for i, member_id in enumerate(members):
            name = await self.get_user_name(member_id)
            member_points = points.get(str(member_id), 0)
            
            if i == 0:
                medal = "🏆"
                self.db.add_order_points(member_id, chat_id, 500, "Победа в цикле ордена")
                # Отправляем поздравление победителю в ЛС
                await self.send_private_message(
                    member_id,
                    f"🏆 ПОЗДРАВЛЯЕМ!\n\n"
                    f"Ты стал лидером цикла {cycle} Тайного Ордена!\n"
                    f"➕ 500 очков ордена"
                )
            elif i == 1:
                medal = "🥈"
            elif i == 2:
                medal = "🥉"
            else:
                medal = "👤"
            
            message += f"{medal} {name} — {member_points} очков\n"
        
        message += f"\n👁️ Спектр: Спектр наблюдал за вами..."
        
        await update.message.reply_text(message)

    # ===== НОВЫЕ КОМАНДЫ ДЛЯ AI =====
    async def cmd_set_ai_prompt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Устанавливает кастомный промпт для AI в чате"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        chat_id = update.effective_chat.id
        
        if user_data['rank'] < 3 and user.id != OWNER_ID:
            await update.message.reply_text("❌ Только администраторы могут менять промпт AI.")
            return
        
        if not context.args:
            await update.message.reply_text(
                "❌ Укажите новый промпт для AI.\n"
                "Пример: /set_ai_prompt Ты дружелюбный помощник в игровом чате"
            )
            return
        
        prompt = " ".join(context.args)
        
        # Сохраняем в настройки чата
        self.db.cursor.execute('''
            UPDATE chat_settings SET ai_prompt = ? WHERE chat_id = ?
        ''', (prompt, chat_id))
        self.db.conn.commit()
        
        # Обновляем в AI
        if self.ai and self.ai.is_available:
            await self.ai.set_chat_prompt(chat_id, prompt)
        
        await update.message.reply_text(s.success("✅ Промпт AI обновлён!"))
    
    async def cmd_ai_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает статус AI"""
        if self.ai and self.ai.is_available:
            text = (
                f"{s.header('🤖 AI СТАТУС')}\n\n"
                f"✅ AI подключен и работает\n"
                f"Модель: llama-3.3-70b-versatile\n"
                f"Кулдаун: {AI_COOLDOWN} сек\n\n"
                f"Команды:\n"
                f"/set_ai_prompt [текст] - изменить промпт (админы)"
            )
        else:
            text = (
                f"{s.header('🤖 AI СТАТУС')}\n\n"
                f"❌ AI не подключен\n"
                f"Причина: нет API ключа или ошибка инициализации"
            )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    # ===== НОВЫЕ КОМАНДЫ ДЛЯ ВНЕШНИХ API =====
    async def cmd_currency(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает курсы валют (имитация)"""
        rates = {
            "USD": random.randint(90, 100),
            "EUR": random.randint(95, 105),
            "CNY": random.randint(12, 15),
            "BTC": random.randint(50000, 60000)
        }
        
        text = f"{s.header('💱 КУРСЫ ВАЛЮТ')}\n\n"
        for currency, rate in rates.items():
            text += f"• {currency}: {rate} ₽\n"
        
        text += f"\n🔄 Данные обновляются каждую минуту"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_news(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает последние новости (имитация)"""
        news = [
            "📰 В Спектре появилась биржа валют! Теперь можно торговать неонами.",
            "🎮 Новая игра 'Тайный Орден' уже доступна! Станьте избранным.",
            "💰 Ежедневные бонусы увеличены на 20% для всех игроков.",
            "🤖 AI Спектра теперь лучше понимает мемы и шутки.",
            "⚔️ Система дуэлей обновлена: добавлен рейтинг и достижения."
        ]
        
        text = f"{s.header('📰 ПОСЛЕДНИЕ НОВОСТИ')}\n\n"
        for i, news_item in enumerate(news[:3], 1):
            text += f"{i}. {news_item}\n\n"
        
        text += f"📅 {datetime.now().strftime('%d.%m.%Y')}"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

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
            await update.message.reply_text("❌ Неверный номер. Введите 0-7")
    
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
            await update.message.reply_text("⚠️ Запрещенное слово! Сообщение удалено.")
            return
        
        if context.user_data.get('awaiting_rps'):
            if message_text in ["1", "2", "3"]:
                context.user_data['awaiting_rps'] = False
                
                choices = {1: "🪨 Камень", 2: "✂️ Ножницы", 3: "📄 Бумага"}
                results = {
                    (1,2): "win", (2,3): "win", (3,1): "win",
                    (2,1): "lose", (3,2): "lose", (1,3): "lose"
                }
                
                player_choice = int(message_text)
                bot_choice = random.randint(1, 3)
                
                text = f"✊ КНБ\n\n"
                text += f"👤 Вы: {choices[player_choice]}\n"
                text += f"🤖 Бот: {choices[bot_choice]}\n\n"
                
                if player_choice == bot_choice:
                    self.db.update_user(user_data['id'], rps_draws=user_data.get('rps_draws', 0) + 1)
                    text += "🤝 НИЧЬЯ!"
                elif results.get((player_choice, bot_choice)) == "win":
                    self.db.update_user(user_data['id'], rps_wins=user_data.get('rps_wins', 0) + 1)
                    reward = random.randint(10, 30)
                    self.db.add_coins(user_data['id'], reward)
                    text += f"🎉 ПОБЕДА! +{reward} 💰"
                else:
                    self.db.update_user(user_data['id'], rps_losses=user_data.get('rps_losses', 0) + 1)
                    text += "😢 ПОРАЖЕНИЕ!"
                
                await update.message.reply_text(text)
                return
        
        if message_text.lower().startswith('голосовать '):
            try:
                vote_num = int(message_text.split()[1])
                for game in self.mafia_games.values():
                    if game.chat_id == chat.id and game.phase == "day" and user.id in game.get_alive_players():
                        alive_players = game.get_alive_players()
                        if 1 <= vote_num <= len(alive_players):
                            target_id = alive_players[vote_num - 1]
                            game.votes[user.id] = target_id
                            
                            # Отправляем подтверждение в ЛС
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
                                f"🎉 ПОБЕДА!\n\n"
                                f"Число {game['number']}!\n"
                                f"Попыток: {game['attempts']}\n"
                                f"Выигрыш: {win} 💰"
                            )
                            del self.games_in_progress[game_id]
                        elif game['attempts'] >= game['max_attempts']:
                            self.db.update_user(user_data['id'], guess_losses=user_data.get('guess_losses', 0) + 1)
                            await update.message.reply_text(
                                f"❌ Попытки кончились! Было число {game['number']}"
                            )
                            del self.games_in_progress[game_id]
                        elif guess < game['number']:
                            await update.message.reply_text(f"📈 Загаданное число больше {guess}")
                        else:
                            await update.message.reply_text(f"📉 Загаданное число меньше {guess}")
                    except ValueError:
                        await update.message.reply_text("❌ Введите число от 1 до 100")
                    return
                
                elif game_id.startswith('bulls_'):
                    if len(message_text) != 4 or not message_text.isdigit():
                        await update.message.reply_text("❌ Введите 4 цифры")
                        return
                    
                    guess = message_text
                    if len(set(guess)) != 4:
                        await update.message.reply_text("❌ Цифры не должны повторяться")
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
                            f"🎉 ПОБЕДА!\n\n"
                            f"Число {game['number']}!\n"
                            f"Попыток: {len(game['attempts'])}\n"
                            f"Выигрыш: {win} 💰"
                        )
                        del self.games_in_progress[game_id]
                    elif len(game['attempts']) >= game['max_attempts']:
                        self.db.update_user(user_data['id'], bulls_losses=user_data.get('bulls_losses', 0) + 1)
                        await update.message.reply_text(
                            f"❌ Попытки кончились! Было число {game['number']}"
                        )
                        del self.games_in_progress[game_id]
                    else:
                        await update.message.reply_text(
                            f"🔍 Быки: {bulls}, Коровы: {cows}\n"
                            f"Осталось попыток: {game['max_attempts'] - len(game['attempts'])}"
                        )
                    return

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
                    # Не добавляем никаких префиксов, просто отправляем ответ
                    await update.message.reply_text(response)
                    
                    # Обновляем прогресс квеста
                    self.db.update_quest_progress(user_data['id'], 'ai_interactions', 1)
                    return
            except Exception as e:
                logger.error(f"AI response error: {e}")
    
    async def handle_left_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выхода участника из чата"""
        member = update.message.left_chat_member
        if member.is_bot:
            return
        
        # Получаем информацию о пользователе
        user_data = self.db.get_user_by_id(member.id)
        if user_data:
            name = user_data.get('nickname') or member.first_name
        else:
            name = member.first_name
        
        # Отправляем сообщение о выходе
        await update.message.reply_text(
            f"👋 {name} покинул чат...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Логируем событие
        self.db.log_action(
            member.id, 
            'left_chat', 
            f"Покинул чат {update.effective_chat.title}",
            chat_id=update.effective_chat.id
        )

    async def handle_new_chat_members(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик добавления бота в новые чаты (без проверки прав)"""
        for member in update.message.new_chat_members:
            if member.id == context.bot.id:
                # Бота добавили в новый чат
                chat = update.effective_chat
                added_by = update.message.from_user
                
                # Текст сообщения
                welcome_text = f"""
Привет, {chat.title}!
Меня добавил {added_by.first_name}.

📌 Основные команды:
• /menu — главное меню
• /help — список всех команд
• /profile — мой профиль
• /balance — мой баланс
• /games — игры

⚠️ Для полноценной работы выдайте мне права администратора!

👑 Владелец: {OWNER_USERNAME}
                """
                
                # Клавиатура
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📋 Команды", callback_data="help_menu")],
                    [InlineKeyboardButton("👑 Владелец", url=f"https://t.me/{OWNER_USERNAME.replace('@', '')}")]
                ])
                
                # Отправляем фото с подписью
                await update.message.reply_photo(
                    photo="https://i.postimg.cc/wxt62Qy5/photo-2026-02-22-22-19-50.jpg",
                    caption=welcome_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=keyboard
                )
                
                logger.info(f"✅ Бот добавлен в чат: {chat.title} (ID: {chat.id})")
                
                # Сохраняем в БД
                self.db.cursor.execute('''
                    INSERT OR IGNORE INTO chat_settings (chat_id, chat_name)
                    VALUES (?, ?)
                ''', (chat.id, chat.title))
                self.db.conn.commit()

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        if not query.message:
            logger.error("Нет сообщения для редактирования")
            return
    
        data = query.data
        data = query.data
        user = query.from_user
        user_data = self.db.get_user(user.id)

        if data == "random_chat":
            self.db.cursor.execute("SELECT chat_id, chat_name FROM chat_settings WHERE chat_code IS NOT NULL ORDER BY RANDOM() LIMIT 1")
            row = self.db.cursor.fetchone()
            if row:
                await query.edit_message_text(
                    f"🎲 Случайная беседа найдена!\n\n"
                    f"Название: {row[1]}\n"
                    f"ID: `{row[0]}`\n\n"
                    f"Присоединяйтесь!"
                )
            else:
                await query.edit_message_text("❌ Нет доступных бесед")

        elif data == "top_chats":
            await self.cmd_top_chats(update, context)

        elif data == "help_menu":
            await self.cmd_help(update, context)

        elif data == "setup_info":
            text = """
# 🔧 Установка

Подробная инструкция по установке бота:
https://teletype.in/@nobucraft/2_pbVPOhaYo
            """
            await query.edit_message_text(text, disable_web_page_preview=True)

        elif data == "neons_info":
            text = """
# 💜 Что такое неоны?

Неоны — основная валюта кибер-вселенной Спектра.

## Как получить:
• Ежедневный бонус (/daily)
• Победы в играх
• Убийство боссов
• Покупка за монеты (1000 💰 = 1 💜)
• Реферальная система
• Выполнение квестов (/quests)

## На что тратить:
• Покупка бонусов
• Telegram Premium
• Подарки
• Улучшения в играх
• Торговля на бирже

## Команды:
/neons — мой баланс
/transfer @user 100 — перевести неоны
/farm — ферма глитчей (1 💜 = 100 🖥)
/exchange — биржа
            """
            await query.edit_message_text(text)

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

        elif data.startswith("chat_card_"):
            chat_id = int(data.split('_')[2])
            await query.edit_message_text(
                "📇 Карточка чата\n\nФункция в разработке",
                parse_mode=ParseMode.MARKDOWN
            )

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
                    await query.edit_message_text(
                        s.success(f"✅ Куплено: {w['name']}!\nТеперь ваш урон: {new_damage}"),
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    await query.edit_message_text(
                        s.error(f"❌ Недостаточно монет. Нужно {w['price']} 💰"),
                        parse_mode=ParseMode.MARKDOWN
                    )

        elif data == "boss_list":
            bosses = self.db.get_bosses()
            text = f"{s.header('👾 БОССЫ')}\n\n"
            for i, boss in enumerate(bosses[:5]):
                status = "⚔️" if boss['is_alive'] else "💀"
                health_bar = self._progress_bar(boss['health'], boss['max_health'], 10)
                text += f"{i+1}. {status} {boss['name']}\n   {health_bar}\n\n"
            
            keyboard_buttons = []
            for i, boss in enumerate(bosses[:5]):
                if boss['is_alive']:
                    keyboard_buttons.append(InlineKeyboardButton(
                        f"⚔️ {boss['name']}",
                        callback_data=f"boss_attack_{boss['id']}"
                    ))
            
            keyboard_buttons.append(InlineKeyboardButton("🔄 Регенерация", callback_data="boss_regen"))
            
            await query.edit_message_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(self._split_buttons(keyboard_buttons, 1))
            )

        elif data.startswith("saper_"):
            parts = data.split('_')
            if len(parts) >= 3:
                game_id = f"{parts[1]}_{parts[2]}"
                cell = int(parts[3])
                
                if game_id in self.games_in_progress:
                    game = self.games_in_progress[game_id]
                    if game['user_id'] != user.id:
                        await query.answer("Это не ваша игра!", show_alert=True)
                        return
                    
                    x = (cell - 1) // 3
                    y = (cell - 1) % 3
                    
                    if x == game['mine_x'] and y == game['mine_y']:
                        await query.edit_message_text(
                            f"{s.header('💥 БУМ!')}\n\n{s.error('Ты подорвался на мине!')}\n\nПроигрыш: {game['bet']} 💰",
                            parse_mode=ParseMode.MARKDOWN
                        )
                        del self.games_in_progress[game_id]
                    else:
                        game['opened'] += 1
                        game['field'][x][y] = "✅"
                        
                        if game['opened'] >= 8:
                            win = game['bet'] * 3
                            self.db.add_coins(user_data['id'], win)
                            self.db.update_user(user_data['id'], slots_wins=user_data.get('slots_wins', 0) + 1)
                            await query.edit_message_text(
                                s.success(f"🎉 ПОБЕДА! Ты открыл все безопасные клетки!\nВыигрыш: {win} 💰"),
                                parse_mode=ParseMode.MARKDOWN
                            )
                            del self.games_in_progress[game_id]
                        else:
                            field_text = ""
                            for i in range(3):
                                field_text += ' '.join(game['field'][i]) + "\n"
                            
                            keyboard_buttons = []
                            for i in range(3):
                                for j in range(3):
                                    cell_num = i * 3 + j + 1
                                    if game['field'][i][j] == "✅":
                                        keyboard_buttons.append(InlineKeyboardButton(f"✅", callback_data="disabled"))
                                    else:
                                        keyboard_buttons.append(InlineKeyboardButton(f"⬜️", callback_data=f"saper_{game_id}_{cell_num}"))
                            
                            await query.edit_message_text(
                                f"{s.header('💣 САПЁР')}\n\n{field_text}",
                                parse_mode=ParseMode.MARKDOWN,
                                reply_markup=InlineKeyboardMarkup(self._split_buttons(keyboard_buttons, 3))
                            )

        elif data.startswith("vote_for_"):
            vote_id = int(data.split('_')[2])
            if self.db.vote_for_ban(vote_id, user_data['id'], True):
                await query.edit_message_text(s.success("✅ Ваш голос учтён (ЗА БАН)"))
                
                self.db.cursor.execute("SELECT * FROM ban_votes WHERE id = ?", (vote_id,))
                vote = self.db.cursor.fetchone()
                if vote and vote[7] >= vote[5]:
                    target = self.db.get_user_by_id(vote[2])
                    if target:
                        self.db.ban_user(target['id'], vote[3], "По результатам голосования")
                        self.db.cursor.execute("UPDATE ban_votes SET status = 'completed' WHERE id = ?", (vote_id,))
                        self.db.conn.commit()
                        
                        await context.bot.send_message(
                            vote[1],
                            s.error(f"🔨 Пользователь {target['first_name']} забанен по результатам голосования!")
                        )
            else:
                await query.edit_message_text(s.error("❌ Не удалось проголосовать"))

        elif data.startswith("vote_against_"):
            vote_id = int(data.split('_')[2])
            if self.db.vote_for_ban(vote_id, user_data['id'], False):
                await query.edit_message_text(s.success("✅ Ваш голос учтён (ПРОТИВ БАНА)"))
            else:
                await query.edit_message_text(s.error("❌ Не удалось проголосовать"))

        elif data.startswith("mafia_confirm_"):
            chat_id = int(data.split('_')[2])
            if chat_id in self.mafia_games:
                game = self.mafia_games[chat_id]
                if user.id in game.players:
                    game.confirm_player(user.id)
                    
                    self.db.cursor.execute('''
                        INSERT INTO mafia_confirmations (game_id, user_id, confirmed)
                        VALUES (?, ?, 1)
                        ON CONFLICT(game_id, user_id) DO UPDATE SET confirmed = 1
                    ''', (game.game_id, user.id))
                    self.db.conn.commit()
                    
                    await query.edit_message_text(
                        f"{s.success('✅ Подтверждение получено!')}\n\n"
                        f"{s.info('Ожидайте начала игры...')}",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    
                    if game.all_confirmed():
                        await self._mafia_start_game(game, context)

        elif data.startswith("accept_duel_"):
            duel_id = int(data.split('_')[2])
            duel = self.db.get_duel(duel_id)
            
            if not duel or duel['opponent_id'] != user_data['id'] or duel['status'] != 'pending':
                await query.edit_message_text(s.error("❌ Дуэль не найдена или уже обработана"))
                return
            
            self.db.update_duel(duel_id, status='accepted')
            
            challenger = self.db.get_user_by_id(duel['challenger_id'])
            opponent = self.db.get_user_by_id(duel['opponent_id'])
            
            if not challenger or not opponent:
                await query.edit_message_text(s.error("❌ Ошибка загрузки данных"))
                return
            
            await query.edit_message_text(
                f"{s.success('✅ Дуэль принята!')}\n\n"
                f"⚔️ {challenger['first_name']} VS {opponent['first_name']} ⚔️\n"
                f"💰 Ставка: {duel['bet']} 💰\n\n"
                f"🔄 Дуэль начинается...",
                parse_mode=ParseMode.MARKDOWN
            )
            
            asyncio.create_task(self._process_duel(duel_id, challenger, opponent, duel['bet'], update.effective_chat.id, context))

        elif data.startswith("reject_duel_"):
            duel_id = int(data.split('_')[2])
            duel = self.db.get_duel(duel_id)
            
            if not duel or duel['opponent_id'] != user_data['id'] or duel['status'] != 'pending':
                await query.edit_message_text(s.error("❌ Дуэль не найдена или уже обработана"))
                return
            
            self.db.update_duel(duel_id, status='rejected')
            self.db.add_coins(duel['challenger_id'], duel['bet'])
            
            await query.edit_message_text(
                f"{s.error('❌ Дуэль отклонена')}\n\n"
                f"Ставка возвращена.",
                parse_mode=ParseMode.MARKDOWN
            )

        elif data.startswith("marry_accept_"):
            proposer_id = int(data.split('_')[2])
            
            if user_data.get('spouse', 0):
                await query.edit_message_text(s.error("❌ Вы уже в браке"), parse_mode=ParseMode.MARKDOWN)
                return
            
            proposer = self.db.get_user_by_id(proposer_id)
            if not proposer:
                await query.edit_message_text(s.error("❌ Пользователь не найден"), parse_mode=ParseMode.MARKDOWN)
                return
            
            if proposer.get('spouse', 0):
                await query.edit_message_text(s.error("❌ Пользователь уже в браке"), parse_mode=ParseMode.MARKDOWN)
                return
            
            now = datetime.now().isoformat()
            self.db.update_user(user_data['id'], spouse=proposer_id, married_since=now)
            self.db.update_user(proposer_id, spouse=user_data['id'], married_since=now)
            
            text = (
                f"# Спектр | Свадьба\n\n"
                f"💍 Поздравляем!\n"
                f"{user_data['first_name']} и {proposer['first_name']} теперь в браке! 🎉\n\n"
                f"💕 Совместимость: {random.randint(70, 100)}%\n"
                f"💰 Бонус молодожёнам: +500 💰 каждому\n"
                f"✨ Особый статус: Супруг(а)"
            )
            
            self.db.add_coins(user_data['id'], 500)
            self.db.add_coins(proposer_id, 500)
            
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
            
            await self.send_private_message(
                proposer['telegram_id'],
                f"{s.success('💞 ПОЗДРАВЛЯЕМ!')}\n\n"
                f"{s.item(f'{user_data["first_name"]} принял(а) ваше предложение!')}",
                parse_mode=ParseMode.MARKDOWN
            )

        elif data.startswith("marry_reject_"):
            proposer_id = int(data.split('_')[2])
            await query.edit_message_text(s.error("❌ Предложение отклонено"), parse_mode=ParseMode.MARKDOWN)
            await self.send_private_message(
                proposer_id,
                s.error("❌ Ваше предложение отклонили"),
                parse_mode=ParseMode.MARKDOWN
            )

        elif data == "bookmark_help":
            text = """
# 📌 Закладки

Как использовать:

• `+Закладка Название` (с новой строки содержимое) — создать
• `закладка [ID]` — показать
• `чатбук` — все закладки чата
• `мои закладки` — ваши закладки
• `-Закладка [ID]` — удалить
            """
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)

        elif data == "circle_help":
            text = """
# 🔄 Кружки

Как использовать:

• `создать кружок Название` (с новой строки описание) — создать
• `кружки` — список кружков
• `кружок [номер]` — информация
• `+Кружок [номер]` — присоединиться
• `-Кружок [номер]` — выйти
            """
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)

        elif data == "achievements_help":
            text = """
# 🏅 Ачивки

Как использовать:

• `мои ачивки` — ваши достижения
• `топ ачивок` — рейтинг
• `ачивка [ID]` — информация
• `+Ачивки` / `-Ачивки` — приватность
            """
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)

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

    # ===== НАСТРОЙКА ОБРАБОТЧИКОВ (setup_handlers) =====
    def setup_handlers(self):
        """Регистрация всех обработчиков"""
        
        # ===== ОСНОВНЫЕ КОМАНДЫ =====
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CommandHandler("menu", self.show_menu))
        
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
        self.app.add_handler(CommandHandler("myprofile", self.cmd_my_profile))
        self.app.add_handler(CommandHandler("profile_public", self.cmd_profile_public))
        self.app.add_handler(CommandHandler("profile_private", self.cmd_profile_private))
        
        # ===== СТАТИСТИКА =====
        self.app.add_handler(CommandHandler("stats", self.cmd_stats))
        self.app.add_handler(CommandHandler("mystats", self.cmd_my_stats))
        self.app.add_handler(CommandHandler("top", self.cmd_top))
        self.app.add_handler(CommandHandler("topcoins", self.cmd_top_coins))
        self.app.add_handler(CommandHandler("toplevel", self.cmd_top_level))
        self.app.add_handler(CommandHandler("topneons", self.cmd_top_neons))
        self.app.add_handler(CommandHandler("topglitches", self.cmd_top_glitches))
        
        # ===== МОДЕРАЦИЯ =====
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
        
        # ===== МОДЕРАЦИЯ (РАНГИ) =====
        self.app.add_handler(CommandHandler("set_rank", self.cmd_set_rank))
        self.app.add_handler(CommandHandler("set_rank2", self.cmd_set_rank2))
        self.app.add_handler(CommandHandler("set_rank3", self.cmd_set_rank3))
        self.app.add_handler(CommandHandler("set_rank4", self.cmd_set_rank4))
        self.app.add_handler(CommandHandler("set_rank5", self.cmd_set_rank5))
        self.app.add_handler(CommandHandler("lower_rank", self.cmd_lower_rank))
        self.app.add_handler(CommandHandler("remove_rank", self.cmd_remove_rank))
        self.app.add_handler(CommandHandler("remove_left", self.cmd_remove_left))
        self.app.add_handler(CommandHandler("remove_all_ranks", self.cmd_remove_all_ranks))
        
        # ===== МУТ/БАН =====
        self.app.add_handler(CommandHandler("mute", self.cmd_mute))
        self.app.add_handler(CommandHandler("unmute", self.cmd_unmute))
        self.app.add_handler(CommandHandler("ban", self.cmd_ban))
        self.app.add_handler(CommandHandler("unban", self.cmd_unban))
        self.app.add_handler(CommandHandler("kick", self.cmd_kick))
        
        # ===== ЭКОНОМИКА =====
        self.app.add_handler(CommandHandler("balance", self.cmd_balance))
        self.app.add_handler(CommandHandler("coins", self.cmd_balance))
        self.app.add_handler(CommandHandler("pay", self.cmd_pay))
        self.app.add_handler(CommandHandler("daily", self.cmd_daily))
        self.app.add_handler(CommandHandler("streak", self.cmd_streak))
        self.app.add_handler(CommandHandler("vip", self.cmd_vip_info))
        self.app.add_handler(CommandHandler("buyvip", self.cmd_buy_vip))
        self.app.add_handler(CommandHandler("premium", self.cmd_premium_info))
        self.app.add_handler(CommandHandler("buypremium", self.cmd_buy_premium))
        self.app.add_handler(CommandHandler("shop", self.cmd_shop))
        self.app.add_handler(CommandHandler("buy", self.cmd_buy))
        
        # ===== НОВАЯ ЭКОНОМИКА (НЕОНЫ, ГЛИТЧИ) =====
        self.app.add_handler(CommandHandler("neons", self.cmd_neons))
        self.app.add_handler(CommandHandler("glitches", self.cmd_glitches))
        self.app.add_handler(CommandHandler("farm", self.cmd_farm))
        self.app.add_handler(CommandHandler("transfer", self.cmd_transfer_neons))
        self.app.add_handler(CommandHandler("exchange", self.cmd_exchange))
        
        # ===== НОВЫЕ МОДУЛИ (КВЕСТЫ, БИРЖА) =====
        self.app.add_handler(CommandHandler("quests", self.cmd_quests))
        self.app.add_handler(CommandHandler("exchange", self.cmd_exchange_market))
        self.app.add_handler(CommandHandler("buyorder", self.cmd_buy_order))
        self.app.add_handler(CommandHandler("sellorder", self.cmd_sell_order))
        self.app.add_handler(CommandHandler("myorders", self.cmd_my_orders))
        self.app.add_handler(CommandHandler("cancelorder", self.cmd_cancel_order))
        
        # ===== РАЗВЛЕЧЕНИЯ =====
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
        
        # ===== ИГРЫ =====
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
        
        # ===== БОССЫ =====
        self.app.add_handler(CommandHandler("bosses", self.cmd_bosses))
        self.app.add_handler(CommandHandler("boss", self.cmd_boss_fight))
        self.app.add_handler(CommandHandler("bossinfo", self.cmd_boss_info))
        self.app.add_handler(CommandHandler("regen", self.cmd_regen))
        
        # ===== ДУЭЛИ =====
        self.app.add_handler(CommandHandler("duel", self.cmd_duel))
        self.app.add_handler(CommandHandler("duels", self.cmd_duels))
        self.app.add_handler(CommandHandler("duelrating", self.cmd_duel_rating))
        
        # ===== Мафия (улучшенная) =====
        self.app.add_handler(CommandHandler("mafia", self.cmd_mafia))
        self.app.add_handler(CommandHandler("mafiastart", self.cmd_mafia_start))
        self.app.add_handler(CommandHandler("mafiajoin", self.cmd_mafia_join))
        self.app.add_handler(CommandHandler("mafialeave", self.cmd_mafia_leave))
        self.app.add_handler(CommandHandler("mafiaroles", self.cmd_mafia_roles))
        self.app.add_handler(CommandHandler("mafiarules", self.cmd_mafia_rules))
        self.app.add_handler(CommandHandler("mafiastats", self.cmd_mafia_stats))
        
        # ===== АЧИВКИ =====
        self.app.add_handler(CommandHandler("achievements", self.cmd_achievements))
        self.app.add_handler(CommandHandler("myachievements", self.cmd_my_achievements))
        self.app.add_handler(CommandHandler("achievement", self.cmd_achievement_info))
        self.app.add_handler(CommandHandler("topachievements", self.cmd_top_achievements))
        self.app.add_handler(CommandHandler("achievements_public", self.cmd_achievements_public))
        self.app.add_handler(CommandHandler("achievements_private", self.cmd_achievements_private))
        
        # ===== КРУЖКИ =====
        self.app.add_handler(CommandHandler("circles", self.cmd_circles))
        self.app.add_handler(CommandHandler("circle", self.cmd_circle))
        self.app.add_handler(CommandHandler("createcircle", self.cmd_create_circle))
        self.app.add_handler(CommandHandler("joincircle", self.cmd_join_circle))
        self.app.add_handler(CommandHandler("leavecircle", self.cmd_leave_circle))
        
        # ===== ЗАКЛАДКИ =====
        self.app.add_handler(CommandHandler("bookmarks", self.cmd_bookmarks))
        self.app.add_handler(CommandHandler("bookmark", self.cmd_bookmark))
        self.app.add_handler(CommandHandler("addbookmark", self.cmd_add_bookmark))
        self.app.add_handler(CommandHandler("removebookmark", self.cmd_remove_bookmark))
        self.app.add_handler(CommandHandler("chatbook", self.cmd_chat_bookmarks))
        self.app.add_handler(CommandHandler("mybookmarks", self.cmd_my_bookmarks))
        
        # ===== ТАЙМЕРЫ =====
        self.app.add_handler(CommandHandler("timers", self.cmd_timers))
        self.app.add_handler(CommandHandler("addtimer", self.cmd_add_timer))
        self.app.add_handler(CommandHandler("removetimer", self.cmd_remove_timer))
        
        # ===== НАГРАДЫ =====
        self.app.add_handler(CommandHandler("awards", self.cmd_awards))
        self.app.add_handler(CommandHandler("giveaward", self.cmd_give_award))
        self.app.add_handler(CommandHandler("removeaward", self.cmd_remove_award))
        
        # ===== КЛАНЫ =====
        self.app.add_handler(CommandHandler("clan", self.cmd_clan))
        self.app.add_handler(CommandHandler("clans", self.cmd_clans))
        self.app.add_handler(CommandHandler("createclan", self.cmd_create_clan))
        self.app.add_handler(CommandHandler("joinclan", self.cmd_join_clan))
        self.app.add_handler(CommandHandler("leaveclan", self.cmd_leave_clan))
        
        # ===== БОНУСЫ =====
        self.app.add_handler(CommandHandler("bonuses", self.cmd_bonuses))
        self.app.add_handler(CommandHandler("bonusinfo", self.cmd_bonus_info))
        self.app.add_handler(CommandHandler("buybonus", self.cmd_buy_bonus))
        self.app.add_handler(CommandHandler("cyberstatus", self.cmd_cyber_status))
        self.app.add_handler(CommandHandler("glitchhammer", self.cmd_glitch_hammer))
        self.app.add_handler(CommandHandler("turbodrive", self.cmd_turbo_drive))
        self.app.add_handler(CommandHandler("invisible", self.cmd_invisible))
        self.app.add_handler(CommandHandler("neonick", self.cmd_neon_nick))
        self.app.add_handler(CommandHandler("cyberluck", self.cmd_cyber_luck))
        self.app.add_handler(CommandHandler("firewall", self.cmd_firewall))
        self.app.add_handler(CommandHandler("rppacket", self.cmd_rp_packet))
        self.app.add_handler(CommandHandler("use_glitch_hammer", self.cmd_use_glitch_hammer))
        self.app.add_handler(CommandHandler("use_invisible", self.cmd_use_invisible))
        self.app.add_handler(CommandHandler("allow_invisible", self.cmd_allow_invisible))
        self.app.add_handler(CommandHandler("ban_invisible", self.cmd_ban_invisible))

        # ===== ТЕСТОВЫЕ КОМАНДЫ =====
        self.app.add_handler(CommandHandler("testai", self.cmd_test_ai))
        
        # ===== РП КОМАНДЫ =====
        self.app.add_handler(CommandHandler("rp_hack", self.cmd_rp_hack))
        self.app.add_handler(CommandHandler("rp_glitch", self.cmd_rp_glitch))
        self.app.add_handler(CommandHandler("rp_reboot", self.cmd_rp_reboot))
        self.app.add_handler(CommandHandler("rp_code", self.cmd_rp_code))
        self.app.add_handler(CommandHandler("rp_digitize", self.cmd_rp_digitize))
        self.app.add_handler(CommandHandler("rp_hack_deep", self.cmd_rp_hack_deep))
        self.app.add_handler(CommandHandler("rp_download", self.cmd_rp_download))
        self.app.add_handler(CommandHandler("rp_update", self.cmd_rp_update))
        
        # ===== ТЕЛЕГРАМ БОНУСЫ =====
        self.app.add_handler(CommandHandler("tgpremium", self.cmd_tg_premium))
        self.app.add_handler(CommandHandler("buy_tg_premium", self.cmd_buy_tg_premium))
        self.app.add_handler(CommandHandler("gift_tg_premium", self.cmd_gift_tg_premium))
        self.app.add_handler(CommandHandler("tggift", self.cmd_tg_gift))
        self.app.add_handler(CommandHandler("buy_tg_gift", self.cmd_buy_tg_gift))
        self.app.add_handler(CommandHandler("gift_tg_gift", self.cmd_gift_tg_gift))
        self.app.add_handler(CommandHandler("tgstars", self.cmd_tg_stars))
        self.app.add_handler(CommandHandler("buy_tg_stars", self.cmd_buy_tg_stars))
        self.app.add_handler(CommandHandler("transfer_tg_stars", self.cmd_transfer_tg_stars))
        self.app.add_handler(CommandHandler("my_tg_stars", self.cmd_my_tg_stars))
        
        # ===== ТЕМЫ ДЛЯ РОЛЕЙ =====
        self.app.add_handler(CommandHandler("themes", self.cmd_themes))
        self.app.add_handler(CommandHandler("apply_theme", self.cmd_apply_theme))
        self.app.add_handler(CommandHandler("apply_theme_by_name", self.cmd_apply_theme_by_name))
        
        # ===== ПРИВЯЗКА ЧАТА =====
        self.app.add_handler(CommandHandler("bind_chat", self.cmd_bind_chat))
        self.app.add_handler(CommandHandler("chat_code", self.cmd_chat_code))
        self.app.add_handler(CommandHandler("changecode", self.cmd_change_chat_code))
        
        # ===== КУБЫШКА =====
        self.app.add_handler(CommandHandler("treasury", self.cmd_treasury))
        self.app.add_handler(CommandHandler("treasury_withdraw", self.cmd_treasury_withdraw))
        
        # ===== БЕСЕДЫ =====
        self.app.add_handler(CommandHandler("randomchat", self.cmd_random_chat))
        self.app.add_handler(CommandHandler("topchats", self.cmd_top_chats))
        self.app.add_handler(CommandHandler("setupinfo", self.cmd_setup_info))
        
        # ===== ПОЛЕЗНОЕ =====
        self.app.add_handler(CommandHandler("ping", self.cmd_ping))
        self.app.add_handler(CommandHandler("uptime", self.cmd_uptime))
        self.app.add_handler(CommandHandler("info", self.cmd_info))
        
        # ===== НОВЫЕ КОМАНДЫ =====
        # Тайный орден
        self.app.add_handler(CommandHandler("order", self.cmd_order))
        self.app.add_handler(CommandHandler("startorder", self.cmd_start_order))
        self.app.add_handler(CommandHandler("revealorder", self.cmd_reveal_order))
        
        # AI команды
        self.app.add_handler(CommandHandler("set_ai_prompt", self.cmd_set_ai_prompt))
        self.app.add_handler(CommandHandler("ai_status", self.cmd_ai_status))
        
        # Внешние API
        self.app.add_handler(CommandHandler("currency", self.cmd_currency))
        self.app.add_handler(CommandHandler("news", self.cmd_news))
        
        # ===== РУССКИЕ КОМАНДЫ (MessageHandler) =====
        
        # Статистика чата
        self.app.add_handler(MessageHandler(filters.Regex(r'^стата$'), self.cmd_chat_stats_today))
        self.app.add_handler(MessageHandler(filters.Regex(r'^стата неделя$'), self.cmd_chat_stats_week))
        self.app.add_handler(MessageHandler(filters.Regex(r'^стата месяц$'), self.cmd_chat_stats_month))
        self.app.add_handler(MessageHandler(filters.Regex(r'^стата вся$'), self.cmd_chat_stats_all))
        self.app.add_handler(MessageHandler(filters.Regex(r'^топ$'), self.cmd_top_chat_today))
        self.app.add_handler(MessageHandler(filters.Regex(r'^топ неделя$'), self.cmd_top_chat_week))
        self.app.add_handler(MessageHandler(filters.Regex(r'^топ месяц$'), self.cmd_top_chat_month))
        self.app.add_handler(MessageHandler(filters.Regex(r'^топ вся$'), self.cmd_top_chat_all))
        
        # Ачивки
        self.app.add_handler(MessageHandler(filters.Regex(r'^мои ачивки$'), self.cmd_my_achievements))
        self.app.add_handler(MessageHandler(filters.Regex(r'^топ ачивок$'), self.cmd_top_achievements))
        self.app.add_handler(MessageHandler(filters.Regex(r'^ачивка \d+$'), self.cmd_achievement_info))
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+Ачивки$'), self.cmd_achievements_public))
        self.app.add_handler(MessageHandler(filters.Regex(r'^-Ачивки$'), self.cmd_achievements_private))
        
        # Кружки
        self.app.add_handler(MessageHandler(filters.Regex(r'^кружки$'), self.cmd_circles))
        self.app.add_handler(MessageHandler(filters.Regex(r'^кружок \d+$'), self.cmd_circle))
        self.app.add_handler(MessageHandler(filters.Regex(r'^создать кружок'), self.cmd_create_circle))
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+Кружок \d+$'), self.cmd_join_circle))
        self.app.add_handler(MessageHandler(filters.Regex(r'^-Кружок \d+$'), self.cmd_leave_circle))
        
        # Закладки
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+Закладка'), self.cmd_add_bookmark))
        self.app.add_handler(MessageHandler(filters.Regex(r'^закладка \d+$'), self.cmd_bookmark))
        self.app.add_handler(MessageHandler(filters.Regex(r'^чатбук$'), self.cmd_chat_bookmarks))
        self.app.add_handler(MessageHandler(filters.Regex(r'^мои закладки$'), self.cmd_my_bookmarks))
        self.app.add_handler(MessageHandler(filters.Regex(r'^-Закладка \d+$'), self.cmd_remove_bookmark))
        
        # Таймеры
        self.app.add_handler(MessageHandler(filters.Regex(r'^таймер через'), self.cmd_add_timer))
        self.app.add_handler(MessageHandler(filters.Regex(r'^таймер на'), self.cmd_add_timer))
        self.app.add_handler(MessageHandler(filters.Regex(r'^таймеры$'), self.cmd_timers))
        self.app.add_handler(MessageHandler(filters.Regex(r'^удалить таймер \d+$'), self.cmd_remove_timer))
        
        # Награды
        self.app.add_handler(MessageHandler(filters.Regex(r'^наградить \d+'), self.cmd_give_award))
        self.app.add_handler(MessageHandler(filters.Regex(r'^награды'), self.cmd_awards))
        self.app.add_handler(MessageHandler(filters.Regex(r'^снять награду'), self.cmd_remove_award))
        
        # Анкета
        self.app.add_handler(MessageHandler(filters.Regex(r'^моя анкета$'), self.cmd_my_profile))
        self.app.add_handler(MessageHandler(filters.Regex(r'^мой пол '), self.cmd_set_gender))
        self.app.add_handler(MessageHandler(filters.Regex(r'^-Пол$'), self.cmd_remove_gender))
        self.app.add_handler(MessageHandler(filters.Regex(r'^мой город '), self.cmd_set_city))
        self.app.add_handler(MessageHandler(filters.Regex(r'^мой др '), self.cmd_set_birth))
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+Анкета$'), self.cmd_profile_public))
        self.app.add_handler(MessageHandler(filters.Regex(r'^-Анкета$'), self.cmd_profile_private))
        
        # Модерация
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
        
        # Темы
        self.app.add_handler(MessageHandler(filters.Regex(r'^!темы$'), self.cmd_themes))
        self.app.add_handler(MessageHandler(filters.Regex(r'^!темы \d+$'), self.cmd_apply_theme))
        self.app.add_handler(MessageHandler(filters.Regex(r'^!темы \w+$'), self.cmd_apply_theme_by_name))
        
        # Привязка чата
        self.app.add_handler(MessageHandler(filters.Regex(r'^!привязать$'), self.cmd_bind_chat))
        self.app.add_handler(MessageHandler(filters.Regex(r'^код чата$'), self.cmd_chat_code))
        self.app.add_handler(MessageHandler(filters.Regex(r'^сменить код'), self.cmd_change_chat_code))
        
        # Кубышка
        self.app.add_handler(MessageHandler(filters.Regex(r'^кубышка$'), self.cmd_treasury))
        self.app.add_handler(MessageHandler(filters.Regex(r'^кубышка в неоны$'), self.cmd_treasury_withdraw))
        
        # Русские текстовые команды
        self.app.add_handler(MessageHandler(filters.Regex(r'^Случайная беседа$'), self.cmd_random_chat))
        self.app.add_handler(MessageHandler(filters.Regex(r'^Беседы топ дня$'), self.cmd_top_chats))
        self.app.add_handler(MessageHandler(filters.Regex(r'^Команды$'), self.cmd_help))
        self.app.add_handler(MessageHandler(filters.Regex(r'^Установка$'), self.cmd_setup_info))
        
        # Цифровое меню
        self.app.add_handler(MessageHandler(filters.Regex('^[0-9]$'), self.handle_numbers))
        
        # Обработчики сообщений
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, self.handle_new_chat_members))
        self.app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, self.handle_left_member))
        
        # Callback кнопки
        self.app.add_handler(CallbackQueryHandler(self.button_callback))
        
        self.app.add_error_handler(self.error_handler)
        
        logger.info(f"✅ Зарегистрировано обработчиков: {len(self.app.handlers)}")

    # ===== ОБРАБОТЧИК ОШИБОК =====
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ошибок"""
        try:
            # Логируем ошибку
            logger.error(f"Ошибка: {context.error}")
            
            # Не отправляем сообщение об ошибке в каждом чате
            # Только если это критическая ошибка и есть update
            if update and update.effective_message:
                # Не спамим "внутренняя ошибка" на каждую мелочь
                if "Database" in str(context.error) or "Connection" in str(context.error):
                    await update.effective_message.reply_text(
                        "❌ Ошибка базы данных. Попробуйте позже."
                    )
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
            
            asyncio.create_task(self.check_timers())
            
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
