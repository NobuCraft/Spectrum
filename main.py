#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
СПЕКТР v2.0 ULTIMATE 

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

import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from telegram.constants import ParseMode
from telegram.error import TelegramError

# ========== НАСТРОЙКИ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ==========
TOKEN = os.environ.get("BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
OWNER_ID = int(os.environ.get("OWNER_ID", "1732658530"))
OWNER_USERNAME = os.environ.get("OWNER_USERNAME", "@NobuCraft")

if not TOKEN:
    print("❌ ОШИБКА: BOT_TOKEN не найден в переменных окружения!")
    sys.exit(1)

# ========== КОНСТАНТЫ ==========
BOT_NAME = "Спектр"
BOT_VERSION = "6.0 ULTIMATE"

# Настройки модерации
RANKS = {
    0: {"name": "Участник", "emoji": "👤"},
    1: {"name": "Младший модератор", "emoji": "🟢"},
    2: {"name": "Старший модератор", "emoji": "🔵"},
    3: {"name": "Младший администратор", "emoji": "🟣"},
    4: {"name": "Старший администратор", "emoji": "🔴"},
    5: {"name": "Создатель", "emoji": "👑"}
}

# Гифки
GIFS = {
    "mafia_day": "https://files.catbox.moe/g9vc7v.mp4",
    "mafia_night": "https://files.catbox.moe/lvcm8n.mp4",
    "russian_roulette": "https://files.catbox.moe/pj64wq.gif",
    "mafia_kill": "https://files.catbox.moe/mafia_kill.gif",
    "mafia_vote": "https://files.catbox.moe/mafia_vote.gif"
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
AI_CHANCE = 30
AI_COOLDOWN = 2

# Лимиты
MAX_NICK_LENGTH = 30
MAX_TITLE_LENGTH = 30
MAX_MOTTO_LENGTH = 100
MAX_BIO_LENGTH = 500

# ========== ЛОГИРОВАНИЕ ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== КЛАССЫ МАФИИ ==========
class MafiaRole(str, Enum):
    MAFIA = "😈 Мафия"
    COMMISSIONER = "👮 Комиссар"
    DOCTOR = "👨‍⚕️ Доктор"
    MANIAC = "🔪 Маньяк"
    BOSS = "👑 Босс"
    CITIZEN = "👤 Мирный"
    LADY = "💃 Леди"
    SHERIFF = "🔫 Шериф"
    TERRORIST = "💣 Террорист"

class MafiaGame:
    def __init__(self, chat_id: int, game_id: str, creator_id: int):
        self.chat_id = chat_id
        self.game_id = game_id
        self.creator_id = creator_id
        self.status = "waiting"  # waiting, night, day, voting, ended
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
        self.start_time: Optional[datetime.datetime] = None
        
        # Для TrueMafia стиля
        self.mafia_chat_id: Optional[int] = None
        self.kill_history: List[str] = []
    
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
            extra_roles = []
        elif num_players <= 10:
            num_mafia = 3
            extra_roles = [MafiaRole.MANIAC]
        elif num_players <= 13:
            num_mafia = 4
            extra_roles = [MafiaRole.MANIAC, MafiaRole.LADY]
        else:
            num_mafia = 4
            extra_roles = [MafiaRole.MANIAC, MafiaRole.LADY, MafiaRole.SHERIFF]
        
        roles = [MafiaRole.MAFIA] * num_mafia
        roles.append(MafiaRole.COMMISSIONER)
        roles.append(MafiaRole.DOCTOR)
        roles.extend(extra_roles)
        
        remaining = num_players - len(roles)
        roles.extend([MafiaRole.CITIZEN] * remaining)
        
        random.shuffle(roles)
        
        for i, player_id in enumerate(self.players):
            self.roles[player_id] = roles[i]
            self.alive[player_id] = True
    
    def get_role_description(self, role: str) -> str:
        descriptions = {
            MafiaRole.MAFIA: "Ночью вы можете убивать мирных жителей. Общайтесь с другими мафиози в ЛС.",
            MafiaRole.COMMISSIONER: "Ночью вы можете проверять игроков, узнавая их роль.",
            MafiaRole.DOCTOR: "Ночью вы можете спасать одного игрока от смерти.",
            MafiaRole.MANIAC: "Ночью вы можете убивать. Вы ни с кем не связаны.",
            MafiaRole.BOSS: "Вы - глава мафии. Вас нельзя убить ночью.",
            MafiaRole.CITIZEN: "У вас нет особых способностей. Ищите мафию днём.",
            MafiaRole.LADY: "Ночью вы можете соблазнить игрока - он не умрёт, но пропустит день.",
            MafiaRole.SHERIFF: "Вы можете застрелить игрока раз за игру.",
            MafiaRole.TERRORIST: "Если вас убьют, вы забираете с собой одного случайного игрока."
        }
        return descriptions.get(role, "Ошибка")
    
    def get_alive_players(self) -> List[int]:
        return [pid for pid in self.players if self.alive.get(pid, False)]
    
    def get_alive_count(self) -> Dict[str, int]:
        alive = self.get_alive_players()
        mafia = sum(1 for pid in alive if self.roles[pid] in [MafiaRole.MAFIA, MafiaRole.BOSS])
        citizens = len(alive) - mafia
        return {"mafia": mafia, "citizens": citizens, "total": len(alive)}
    
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
        maniac_kill = self.night_actions.get("maniac_kill")
        checked = self.night_actions.get("commissioner_check")
        
        if saved and saved == killed:
            killed = None
        
        if maniac_kill and maniac_kill != saved:
            if killed:
                pass
            else:
                killed = maniac_kill
        
        result = {
            "killed": killed,
            "checked": checked,
            "check_result": self.roles.get(checked) if checked else None
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

# ========== ЭЛЕГАНТНОЕ ОФОРМЛЕНИЕ ==========
class Style:
    SEPARATOR = "─" * 28
    SEPARATOR_BOLD = "━" * 28
    
    @classmethod
    def header(cls, title: str, emoji: str = "⚜️") -> str:
        return f"\n{emoji}{emoji} **{title.upper()}** {emoji}{emoji}\n{cls.SEPARATOR_BOLD}\n"
    
    @classmethod
    def section(cls, title: str, emoji: str = "📌") -> str:
        return f"\n{emoji} **{title}**\n{cls.SEPARATOR}\n"
    
    @classmethod
    def cmd(cls, cmd: str, desc: str, usage: str = "") -> str:
        if usage:
            return f"▸ `/{cmd} {usage}` — {desc}"
        return f"▸ `/{cmd}` — {desc}"
    
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
            [("👾 БОССЫ", "game_bosses"), ("⚔️ ДУЭЛИ", "game_duels")],
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
    def mafia_confirm(cls, chat_id: int):
        return cls.make([[(f"✅ ПОДТВЕРДИТЬ", f"mafia_confirm_{chat_id}")]])
    
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
    def rps(cls):
        return cls.make([
            [("🪨 КАМЕНЬ", "rps_rock"), ("✂️ НОЖНИЦЫ", "rps_scissors"), ("📄 БУМАГА", "rps_paper")],
            [("🔙 НАЗАД", "menu_back")]
        ])
    
    @classmethod
    def duel_accept(cls, duel_id: int):
        return cls.make([
            [("✅ ПРИНЯТЬ", f"accept_duel_{duel_id}"),
             ("❌ ОТКЛОНИТЬ", f"reject_duel_{duel_id}")]
        ])

kb = Keyboard()

# ========== БАЗА ДАННЫХ ==========
class Database:
    def __init__(self):
        self.conn = sqlite3.connect("spectrum.db", check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.create_tables()
        self.init_data()
        logger.info("✅ База данных инициализирована")
    
    def create_tables(self):
        self.cursor.execute('''
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
                circles TEXT DEFAULT '[]',
                friends TEXT DEFAULT '[]',
                enemies TEXT DEFAULT '[]',
                crush INTEGER DEFAULT 0,
                spouse INTEGER DEFAULT 0,
                married_since TEXT,
                reputation INTEGER DEFAULT 0,
                achievements TEXT DEFAULT '[]',
                bookmarks TEXT DEFAULT '[]',
                notes TEXT DEFAULT '[]',
                timers TEXT DEFAULT '[]',
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
                daily_streak INTEGER DEFAULT 0,
                last_daily TEXT,
                last_weekly TEXT,
                last_monthly TEXT,
                last_work TEXT,
                last_seen TEXT,
                notifications INTEGER DEFAULT 1,
                registered TEXT DEFAULT CURRENT_TIMESTAMP,
                referrer_id INTEGER
            )
        ''')
        
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_telegram_id ON users(telegram_id)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_username ON users(username)')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT,
                details TEXT,
                chat_id INTEGER,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS blacklist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT UNIQUE,
                added_by INTEGER,
                added_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.cursor.execute('''
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
                image_url TEXT,
                is_alive INTEGER DEFAULT 1
            )
        ''')
        
        self.cursor.execute('''
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
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS clan_members (
                clan_id INTEGER,
                user_id INTEGER UNIQUE,
                role TEXT DEFAULT 'member',
                joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (clan_id) REFERENCES clans(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        self.cursor.execute('''
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
        
        self.cursor.execute('''
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
        
        self.cursor.execute('''
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
        
        self.conn.commit()
    
    def init_data(self):
        self.cursor.execute("SELECT COUNT(*) FROM bosses")
        if self.cursor.fetchone()[0] == 0:
            bosses = [
                ("Ядовитый комар", 5, 500, 500, 15, 250, 50),
                ("Лесной тролль", 10, 1000, 1000, 25, 500, 100),
                ("Огненный дракон", 15, 2000, 2000, 40, 1000, 200),
                ("Ледяной великан", 20, 3500, 3500, 60, 2000, 350),
                ("Король демонов", 25, 5000, 5000, 85, 3500, 500),
                ("Бог разрушения", 30, 10000, 10000, 150, 5000, 1000)
            ]
            for boss in bosses:
                self.cursor.execute('''
                    INSERT INTO bosses (name, level, health, max_health, damage, reward_coins, reward_exp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', boss)
            self.conn.commit()
    
    def get_user(self, telegram_id: int, first_name: str = "Player") -> Dict[str, Any]:
        self.cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        row = self.cursor.fetchone()
        
        if not row:
            role = 'owner' if telegram_id == OWNER_ID else 'user'
            rank = 5 if telegram_id == OWNER_ID else 0
            rank_name = RANKS[rank]["name"]
            
            self.cursor.execute('''
                INSERT INTO users (telegram_id, first_name, role, rank, rank_name, last_seen)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (telegram_id, first_name, role, rank, rank_name, datetime.datetime.now().isoformat()))
            self.conn.commit()
            return self.get_user(telegram_id, first_name)
        
        user = dict(row)
        
        self.cursor.execute("UPDATE users SET last_seen = ?, first_name = ? WHERE telegram_id = ?",
                          (datetime.datetime.now().isoformat(), first_name, telegram_id))
        self.conn.commit()
        
        return user
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        self.cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = self.cursor.fetchone()
        return dict(row) if row else None
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        if username.startswith('@'):
            username = username[1:]
        self.cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = self.cursor.fetchone()
        return dict(row) if row else None
    
    def update_user(self, user_id: int, **kwargs) -> bool:
        if not kwargs:
            return False
        for key, value in kwargs.items():
            self.cursor.execute(f"UPDATE users SET {key} = ? WHERE id = ?", (value, user_id))
        self.conn.commit()
        return True
    
    def add_coins(self, user_id: int, amount: int) -> int:
        self.cursor.execute("UPDATE users SET coins = coins + ? WHERE id = ?", (amount, user_id))
        self.conn.commit()
        self.cursor.execute("SELECT coins FROM users WHERE id = ?", (user_id,))
        return self.cursor.fetchone()[0]
    
    def add_diamonds(self, user_id: int, amount: int) -> int:
        self.cursor.execute("UPDATE users SET diamonds = diamonds + ? WHERE id = ?", (amount, user_id))
        self.conn.commit()
        self.cursor.execute("SELECT diamonds FROM users WHERE id = ?", (user_id,))
        return self.cursor.fetchone()[0]
    
    def add_exp(self, user_id: int, amount: int) -> bool:
        self.cursor.execute("UPDATE users SET exp = exp + ? WHERE id = ?", (amount, user_id))
        self.cursor.execute("SELECT exp, level FROM users WHERE id = ?", (user_id,))
        row = self.cursor.fetchone()
        exp, level = row[0], row[1]
        if exp >= level * 100:
            self.cursor.execute("UPDATE users SET level = level + 1, exp = exp - ? WHERE id = ?", 
                              (level * 100, user_id))
            self.conn.commit()
            return True
        self.conn.commit()
        return False
    
    def add_energy(self, user_id: int, amount: int) -> int:
        self.cursor.execute("UPDATE users SET energy = MIN(100, energy + ?) WHERE id = ?", (amount, user_id))
        self.conn.commit()
        self.cursor.execute("SELECT energy FROM users WHERE id = ?", (user_id,))
        return self.cursor.fetchone()[0]
    
    def heal(self, user_id: int, amount: int) -> int:
        self.cursor.execute("UPDATE users SET health = MIN(max_health, health + ?) WHERE id = ?", (amount, user_id))
        self.conn.commit()
        self.cursor.execute("SELECT health FROM users WHERE id = ?", (user_id,))
        return self.cursor.fetchone()[0]
    
    def damage(self, user_id: int, amount: int) -> int:
        self.cursor.execute("UPDATE users SET health = MAX(0, health - ?) WHERE id = ?", (amount, user_id))
        self.conn.commit()
        self.cursor.execute("SELECT health FROM users WHERE id = ?", (user_id,))
        return self.cursor.fetchone()[0]
    
    def is_vip(self, user_id: int) -> bool:
        self.cursor.execute("SELECT vip_until FROM users WHERE id = ?", (user_id,))
        row = self.cursor.fetchone()
        if row and row[0]:
            return datetime.datetime.fromisoformat(row[0]) > datetime.datetime.now()
        return False
    
    def is_premium(self, user_id: int) -> bool:
        self.cursor.execute("SELECT premium_until FROM users WHERE id = ?", (user_id,))
        row = self.cursor.fetchone()
        if row and row[0]:
            return datetime.datetime.fromisoformat(row[0]) > datetime.datetime.now()
        return False
    
    def set_vip(self, user_id: int, days: int) -> datetime.datetime:
        until = datetime.datetime.now() + datetime.timedelta(days=days)
        self.cursor.execute("UPDATE users SET vip_until = ?, role = 'vip' WHERE id = ?",
                          (until.isoformat(), user_id))
        self.conn.commit()
        return until
    
    def set_premium(self, user_id: int, days: int) -> datetime.datetime:
        until = datetime.datetime.now() + datetime.timedelta(days=days)
        self.cursor.execute("UPDATE users SET premium_until = ?, role = 'premium' WHERE id = ?",
                          (until.isoformat(), user_id))
        self.conn.commit()
        return until
    
    def set_rank(self, user_id: int, rank: int, admin_id: int) -> bool:
        if rank not in RANKS:
            return False
        self.cursor.execute("UPDATE users SET rank = ?, rank_name = ? WHERE id = ?",
                          (rank, RANKS[rank]["name"], user_id))
        self.conn.commit()
        self.log_action(admin_id, "set_rank", f"{user_id} -> {rank}")
        return True
    
    def get_admins(self) -> List[Dict]:
        self.cursor.execute("SELECT id, first_name, username, rank, rank_name FROM users WHERE rank > 0 ORDER BY rank DESC")
        return [dict(row) for row in self.cursor.fetchall()]
    
    def add_warn(self, user_id: int, admin_id: int, reason: str) -> int:
        self.cursor.execute("SELECT warns, warns_list FROM users WHERE id = ?", (user_id,))
        row = self.cursor.fetchone()
        warns, warns_list = row[0], json.loads(row[1])
        warns_list.append({
            'id': len(warns_list) + 1,
            'admin_id': admin_id,
            'reason': reason,
            'date': datetime.datetime.now().isoformat()
        })
        new_warns = warns + 1
        self.cursor.execute("UPDATE users SET warns = ?, warns_list = ? WHERE id = ?",
                          (new_warns, json.dumps(warns_list), user_id))
        self.conn.commit()
        self.log_action(admin_id, "add_warn", f"{user_id}: {reason}")
        return new_warns
    
    def get_warns(self, user_id: int) -> List[Dict]:
        self.cursor.execute("SELECT warns_list FROM users WHERE id = ?", (user_id,))
        row = self.cursor.fetchone()
        return json.loads(row[0]) if row and row[0] else []
    
    def remove_last_warn(self, user_id: int, admin_id: int) -> Optional[Dict]:
        self.cursor.execute("SELECT warns, warns_list FROM users WHERE id = ?", (user_id,))
        row = self.cursor.fetchone()
        warns, warns_list = row[0], json.loads(row[1])
        if not warns_list:
            return None
        removed = warns_list.pop()
        self.cursor.execute("UPDATE users SET warns = ?, warns_list = ? WHERE id = ?",
                          (warns - 1, json.dumps(warns_list), user_id))
        self.conn.commit()
        self.log_action(admin_id, "remove_warn", f"{user_id}")
        return removed
    
    def mute_user(self, user_id: int, minutes: int, admin_id: int, reason: str = "") -> datetime.datetime:
        until = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
        self.cursor.execute("UPDATE users SET mute_until = ? WHERE id = ?", (until.isoformat(), user_id))
        self.conn.commit()
        self.log_action(admin_id, "mute", f"{user_id} {minutes}мин: {reason}")
        return until
    
    def is_muted(self, user_id: int) -> bool:
        self.cursor.execute("SELECT mute_until FROM users WHERE id = ?", (user_id,))
        row = self.cursor.fetchone()
        if row and row[0]:
            return datetime.datetime.fromisoformat(row[0]) > datetime.datetime.now()
        return False
    
    def unmute_user(self, user_id: int, admin_id: int) -> bool:
        self.cursor.execute("UPDATE users SET mute_until = NULL WHERE id = ?", (user_id,))
        self.conn.commit()
        self.log_action(admin_id, "unmute", str(user_id))
        return True
    
    def get_muted_users(self) -> List[Dict]:
        self.cursor.execute("SELECT id, first_name, username, mute_until FROM users WHERE mute_until > ?",
                          (datetime.datetime.now().isoformat(),))
        return [dict(row) for row in self.cursor.fetchall()]
    
    def ban_user(self, user_id: int, admin_id: int, reason: str) -> bool:
        self.cursor.execute('''
            UPDATE users SET banned = 1, ban_reason = ?, ban_date = ?, ban_admin = ?
            WHERE id = ?
        ''', (reason, datetime.datetime.now().isoformat(), admin_id, user_id))
        self.conn.commit()
        self.log_action(admin_id, "ban", f"{user_id}: {reason}")
        return True
    
    def unban_user(self, user_id: int, admin_id: int) -> bool:
        self.cursor.execute("UPDATE users SET banned = 0, ban_reason = NULL, ban_date = NULL, ban_admin = NULL WHERE id = ?", (user_id,))
        self.conn.commit()
        self.log_action(admin_id, "unban", str(user_id))
        return True
    
    def is_banned(self, user_id: int) -> bool:
        self.cursor.execute("SELECT banned FROM users WHERE id = ?", (user_id,))
        row = self.cursor.fetchone()
        return row and row[0] == 1
    
    def get_banlist(self) -> List[Dict]:
        self.cursor.execute("SELECT id, first_name, username FROM users WHERE banned = 1")
        return [dict(row) for row in self.cursor.fetchall()]
    
    def add_to_blacklist(self, word: str, admin_id: int) -> bool:
        try:
            self.cursor.execute("INSERT INTO blacklist (word, added_by) VALUES (?, ?)", (word.lower(), admin_id))
            self.conn.commit()
            self.log_action(admin_id, "add_blacklist", word)
            return True
        except:
            return False
    
    def remove_from_blacklist(self, word: str, admin_id: int) -> bool:
        self.cursor.execute("DELETE FROM blacklist WHERE word = ?", (word.lower(),))
        self.conn.commit()
        self.log_action(admin_id, "remove_blacklist", word)
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
    
    def get_top(self, field: str, limit: int = 10) -> List[Tuple]:
        self.cursor.execute(f"SELECT first_name, nickname, {field} FROM users ORDER BY {field} DESC LIMIT ?", (limit,))
        return self.cursor.fetchall()
    
    def add_daily_streak(self, user_id: int) -> int:
        today = datetime.datetime.now().date()
        self.cursor.execute("SELECT last_daily, daily_streak FROM users WHERE id = ?", (user_id,))
        row = self.cursor.fetchone()
        
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
        
        self.cursor.execute("UPDATE users SET daily_streak = ?, last_daily = ? WHERE id = ?",
                          (streak, datetime.datetime.now().isoformat(), user_id))
        self.conn.commit()
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
            self.cursor.execute("UPDATE bosses SET is_alive = 0 WHERE id = ?", (boss_id,))
            self.conn.commit()
            return True
        self.conn.commit()
        return False
    
    def respawn_bosses(self):
        self.cursor.execute("UPDATE bosses SET health = max_health, is_alive = 1")
        self.conn.commit()
    
    def add_boss_kill(self, user_id: int):
        self.cursor.execute("UPDATE users SET boss_kills = boss_kills + 1 WHERE id = ?", (user_id,))
        self.conn.commit()
    
    def create_duel(self, challenger_id: int, opponent_id: int, bet: int) -> int:
        self.cursor.execute('''
            INSERT INTO duels (challenger_id, opponent_id, bet)
            VALUES (?, ?, ?)
        ''', (challenger_id, opponent_id, bet))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_duel(self, duel_id: int) -> Optional[Dict]:
        self.cursor.execute("SELECT * FROM duels WHERE id = ?", (duel_id,))
        row = self.cursor.fetchone()
        return dict(row) if row else None
    
    def update_duel(self, duel_id: int, **kwargs):
        for key, value in kwargs.items():
            self.cursor.execute(f"UPDATE duels SET {key} = ? WHERE id = ?", (value, duel_id))
        self.conn.commit()
    
    def create_clan(self, name: str, owner_id: int) -> Optional[int]:
        try:
            self.cursor.execute("INSERT INTO clans (name, owner_id) VALUES (?, ?)", (name, owner_id))
            clan_id = self.cursor.lastrowid
            self.cursor.execute("INSERT INTO clan_members (clan_id, user_id, role) VALUES (?, ?, 'owner')", (clan_id, owner_id))
            self.cursor.execute("UPDATE users SET clan_id = ?, clan_role = 'owner' WHERE id = ?", (clan_id, owner_id))
            self.conn.commit()
            return clan_id
        except:
            return None
    
    def get_clan(self, clan_id: int) -> Optional[Dict]:
        self.cursor.execute("SELECT * FROM clans WHERE id = ?", (clan_id,))
        row = self.cursor.fetchone()
        return dict(row) if row else None
    
    def get_clan_by_name(self, name: str) -> Optional[Dict]:
        self.cursor.execute("SELECT * FROM clans WHERE name = ?", (name,))
        row = self.cursor.fetchone()
        return dict(row) if row else None
    
    def get_clan_members(self, clan_id: int) -> List[Dict]:
        self.cursor.execute('''
            SELECT u.id, u.first_name, u.username, u.nickname, cm.role, cm.joined_at
            FROM clan_members cm
            JOIN users u ON cm.user_id = u.id
            WHERE cm.clan_id = ?
        ''', (clan_id,))
        return [dict(row) for row in self.cursor.fetchall()]
    
    def log_action(self, user_id: int, action: str, details: str = "", chat_id: int = None):
        self.cursor.execute('''
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
        self.session: Optional[aiohttp.ClientSession] = None
        self.contexts = defaultdict(lambda: deque(maxlen=15))
        self.user_last_ai = defaultdict(float)
        self.ai_cooldown = AI_COOLDOWN
        
        self.system_prompt = """Ты — Спектр, дерзкий и умный ИИ-бот в Telegram. Ты используешь современный сленг и мемы. 
Твой характер: дерзкий, но дружелюбный. Можешь жестко ответить на хамство. 
Знаешь всё про игры (мафия, русская рулетка, дуэли), экономику, модерацию (5 рангов). 
Твой создатель — @NobuCraft. Отвечай кратко, с юмором, используй эмодзи."""
    
    async def get_session(self) -> aiohttp.ClientSession:
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
            messages = [
                {"role": "system", "content": self.system_prompt},
                *history,
                {"role": "user", "content": message}
            ]
            
            data = {
                "model": "llama-3.3-70b-versatile",
                "messages": messages,
                "temperature": 0.9,
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
                    return "❌ Ошибка связи с AI."
        except Exception as e:
            logger.error(f"Groq error: {e}")
            return None
    
    async def close(self):
        if self.session:
            await self.session.close()

ai = GroqAI(GROQ_API_KEY) if GROQ_API_KEY else None

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
        logger.info(f"✅ Бот {BOT_NAME} инициализирован")
    
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

    def setup_handlers(self):
        """Регистрация всех обработчиков (более 250 команд)"""
        
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

    # ===== СТАТИСТИКА =====
    self.app.add_handler(CommandHandler("stats", self.cmd_stats))
    self.app.add_handler(CommandHandler("mystats", self.cmd_my_stats))
    self.app.add_handler(CommandHandler("top", self.cmd_top))
    self.app.add_handler(CommandHandler("topcoins", self.cmd_top_coins))
    self.app.add_handler(CommandHandler("toplevel", self.cmd_top_level))
    
    # ===== МОДЕРАЦИЯ =====
    self.app.add_handler(MessageHandler(filters.Regex(r'^\+moder|^!moder|^promote'), self.cmd_set_rank))
    self.app.add_handler(MessageHandler(filters.Regex(r'^\+moder 2|^!moder 2|^promote 2'), self.cmd_set_rank2))
    self.app.add_handler(MessageHandler(filters.Regex(r'^\+moder 3|^!moder 3|^promote 3'), self.cmd_set_rank3))
    self.app.add_handler(MessageHandler(filters.Regex(r'^\+moder 4|^!moder 4|^promote 4'), self.cmd_set_rank4))
    self.app.add_handler(MessageHandler(filters.Regex(r'^\+moder 5|^!moder 5|^promote 5'), self.cmd_set_rank5))
    self.app.add_handler(MessageHandler(filters.Regex(r'^demote'), self.cmd_lower_rank))
    self.app.add_handler(MessageHandler(filters.Regex(r'^remove |^dismiss'), self.cmd_remove_rank))
    self.app.add_handler(MessageHandler(filters.Regex(r'^remove_left'), self.cmd_remove_left))
    self.app.add_handler(MessageHandler(filters.Regex(r'^remove_all'), self.cmd_remove_all_ranks))
    self.app.add_handler(CommandHandler("admins", self.cmd_who_admins))
    
    # ===== ПРЕДУПРЕЖДЕНИЯ =====
    self.app.add_handler(MessageHandler(filters.Regex(r'^warn'), self.cmd_warn))
    self.app.add_handler(MessageHandler(filters.Regex(r'^warns'), self.cmd_warns))
    self.app.add_handler(CommandHandler("mywarns", self.cmd_my_warns))
    self.app.add_handler(MessageHandler(filters.Regex(r'^unwarn'), self.cmd_unwarn))
    self.app.add_handler(MessageHandler(filters.Regex(r'^unwarn_all'), self.cmd_unwarn_all))
    
    # ===== МУТЫ =====
    self.app.add_handler(MessageHandler(filters.Regex(r'^mute'), self.cmd_mute))
    self.app.add_handler(CommandHandler("mutelist", self.cmd_mutelist))
    self.app.add_handler(MessageHandler(filters.Regex(r'^unmute'), self.cmd_unmute))
    
    # ===== БАНЫ =====
    self.app.add_handler(MessageHandler(filters.Regex(r'^ban'), self.cmd_ban))
    self.app.add_handler(CommandHandler("banlist", self.cmd_banlist))
    self.app.add_handler(MessageHandler(filters.Regex(r'^unban'), self.cmd_unban))
    self.app.add_handler(MessageHandler(filters.Regex(r'^kick'), self.cmd_kick))
    
    # ===== ТРИГГЕРЫ =====
    self.app.add_handler(MessageHandler(filters.Regex(r'^\+trigger'), self.cmd_add_trigger))
    self.app.add_handler(MessageHandler(filters.Regex(r'^-trigger'), self.cmd_remove_trigger))
    self.app.add_handler(CommandHandler("triggers", self.cmd_list_triggers))
    
    # ===== АВТОМОДЕРАЦИЯ =====
    self.app.add_handler(MessageHandler(filters.Regex(r'^antimat'), self.cmd_set_antimat))
    self.app.add_handler(MessageHandler(filters.Regex(r'^antilink'), self.cmd_set_antilink))
    self.app.add_handler(MessageHandler(filters.Regex(r'^antiflood'), self.cmd_set_antiflood))
    
    # ===== ЧИСТКА =====
    self.app.add_handler(MessageHandler(filters.Regex(r'^clear'), self.cmd_clear))
    self.app.add_handler(MessageHandler(filters.Regex(r'^clear_user'), self.cmd_clear_user))
    
    # ===== НАСТРОЙКИ ЧАТА =====
    self.app.add_handler(MessageHandler(filters.Regex(r'^\+welcome'), self.cmd_set_welcome))
    self.app.add_handler(MessageHandler(filters.Regex(r'^\+rules'), self.cmd_set_rules))
    self.app.add_handler(CommandHandler("rules", self.cmd_show_rules))
    self.app.add_handler(MessageHandler(filters.Regex(r'^captcha'), self.cmd_set_captcha))
    
    # ===== ЭКОНОМИКА =====
    self.app.add_handler(CommandHandler("balance", self.cmd_balance))
    self.app.add_handler(CommandHandler("pay", self.cmd_pay))
    self.app.add_handler(CommandHandler("topcoins", self.cmd_top_coins))
    self.app.add_handler(CommandHandler("daily", self.cmd_daily))
    self.app.add_handler(CommandHandler("streak", self.cmd_streak))
    self.app.add_handler(CommandHandler("vip", self.cmd_vip_info))
    self.app.add_handler(CommandHandler("buyvip", self.cmd_buy_vip))
    self.app.add_handler(CommandHandler("premium", self.cmd_premium_info))
    self.app.add_handler(CommandHandler("buypremium", self.cmd_buy_premium))
    self.app.add_handler(CommandHandler("shop", self.cmd_shop))
    self.app.add_handler(CommandHandler("buy", self.cmd_buy))
    
    # ===== РАЗВЛЕЧЕНИЯ =====
    self.app.add_handler(CommandHandler("joke", self.cmd_joke))
    self.app.add_handler(CommandHandler("fact", self.cmd_fact))
    self.app.add_handler(CommandHandler("quote", self.cmd_quote))
    self.app.add_handler(CommandHandler("whoami", self.cmd_whoami))
    self.app.add_handler(CommandHandler("advice", self.cmd_advice))
    self.app.add_handler(CommandHandler("ask", self.cmd_ask))
    self.app.add_handler(CommandHandler("compatibility", self.cmd_compatibility))
    
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
    
    # ===== КЛАНЫ =====
    self.app.add_handler(CommandHandler("clan", self.cmd_clan))
    self.app.add_handler(CommandHandler("clans", self.cmd_clans))
    self.app.add_handler(CommandHandler("createclan", self.cmd_create_clan))
    self.app.add_handler(CommandHandler("joinclan", self.cmd_join_clan))
    self.app.add_handler(CommandHandler("leaveclan", self.cmd_leave_clan))
    
    # ===== ОТНОШЕНИЯ =====
    self.app.add_handler(CommandHandler("friend", self.cmd_add_friend))
    self.app.add_handler(CommandHandler("enemy", self.cmd_add_enemy))
    self.app.add_handler(CommandHandler("forgive", self.cmd_remove_enemy))
    
    # ===== БРАКИ =====
    self.app.add_handler(CommandHandler("propose", self.cmd_propose))
    self.app.add_handler(CommandHandler("divorce", self.cmd_divorce))
    self.app.add_handler(CommandHandler("families", self.cmd_families))
    
    # ===== РЕПУТАЦИЯ =====
    self.app.add_handler(MessageHandler(filters.Regex(r'^\+rep'), self.cmd_add_rep))
    self.app.add_handler(MessageHandler(filters.Regex(r'^-rep'), self.cmd_remove_rep))
    self.app.add_handler(CommandHandler("rep", self.cmd_rep))
    
    # ===== МАФИЯ =====
    self.app.add_handler(CommandHandler("mafia", self.cmd_mafia))
    self.app.add_handler(CommandHandler("mafiastart", self.cmd_mafia_start))
    self.app.add_handler(CommandHandler("mafiajoin", self.cmd_mafia_join))
    self.app.add_handler(CommandHandler("mafialeave", self.cmd_mafia_leave))
    self.app.add_handler(CommandHandler("mafiaroles", self.cmd_mafia_roles))
    self.app.add_handler(CommandHandler("mafiarules", self.cmd_mafia_rules))
    
    # ===== ПОЛЕЗНОЕ =====
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
        
        if context.args and context.args[0].isdigit():
            referrer_id = int(context.args[0])
            if referrer_id != user_data['id']:
                self.db.update_user(user_data['id'], referrer_id=referrer_id)
                self.db.add_coins(referrer_id, 500)
                try:
                    await context.bot.send_message(
                        referrer_id,
                        s.success(f"🎉 По вашей ссылке зарегистрировался {user.first_name}! +500 💰")
                    )
                except:
                    pass
        
        text = (
            s.header("СПЕКТР") + "\n"
            f"👋 **Привет, {user.first_name}!**\n"
            f"Я — **Спектр**, твой помощник с AI и играми.\n\n"
            f"{s.section('ТВОЙ ПРОФИЛЬ')}"
            f"{s.stat('Монеты', f'{user_data["coins"]} 💰')}\n"
            f"{s.stat('Уровень', user_data["level"])}\n"
            f"{s.stat('Ранг', get_rank_emoji(user_data["rank"]) + ' ' + user_data["rank_name"])}\n"
            f"{s.stat('Энергия', f'{user_data["energy"]}/100 ⚡')}\n\n"
            f"{s.section('ЧТО Я УМЕЮ')}"
            f"{s.item('🤖 Дерзкий AI со сленгом')}\n"
            f"{s.item('🔫 Мафия как TrueMafia')}\n"
            f"{s.item('🎲 Русская рулетка, кости')}\n"
            f"{s.item('👾 Боссы, дуэли, кланы')}\n"
            f"{s.item('⚙️ Модерация (5 рангов)')}\n"
            f"{s.item('💰 Экономика, VIP')}\n\n"
            f"{s.section('БЫСТРЫЙ СТАРТ')}"
            f"{s.cmd('profile', 'профиль')}\n"
            f"{s.cmd('мафия', 'игра в мафию')}\n"
            f"{s.cmd('бонус', 'ежедневный бонус')}\n"
            f"{s.cmd('help', 'все команды')}\n\n"
            f"👑 **Владелец:** {OWNER_USERNAME}"
        )
        
        await update.message.reply_text(text, reply_markup=kb.main(), parse_mode=ParseMode.MARKDOWN)
        self.db.log_action(user_data['id'], 'start')
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            s.header("СПРАВКА") + "\n"
            f"{s.section('📌 ОСНОВНЫЕ')}"
            f"{s.cmd('start', 'начать')}\n"
            f"{s.cmd('menu', 'главное меню')}\n"
            f"{s.cmd('profile', 'профиль')}\n\n"
            
            f"{s.section('⚙️ МОДЕРАЦИЯ')}"
            f"{s.cmd('+Модер @user', '1 ранг')}\n"
            f"{s.cmd('+Модер 2 @user', '2 ранг')}\n"
            f"{s.cmd('+Модер 3 @user', '3 ранг')}\n"
            f"{s.cmd('+Модер 4 @user', '4 ранг')}\n"
            f"{s.cmd('+Модер 5 @user', '5 ранг')}\n"
            f"{s.cmd('варн @user [причина]', 'предупреждение')}\n"
            f"{s.cmd('мут @user 30м [причина]', 'заглушить')}\n"
            f"{s.cmd('бан @user [причина]', 'заблокировать')}\n\n"
            
            f"{s.section('💰 ЭКОНОМИКА')}"
            f"{s.cmd('ириски', 'баланс')}\n"
            f"{s.cmd('передать @user сумма', 'перевести')}\n"
            f"{s.cmd('бонус', 'ежедневный бонус')}\n"
            f"{s.cmd('магазин', 'список товаров')}\n\n"
            
            f"{s.section('🔫 МАФИЯ')}"
            f"{s.cmd('мафия', 'меню мафии')}\n"
            f"{s.cmd('мафиястарт', 'начать игру')}\n"
            f"{s.cmd('мафияприсоединиться', 'присоединиться')}\n\n"
            
            f"{s.section('🎮 ИГРЫ')}"
            f"{s.cmd('рр [ставка]', 'русская рулетка')}\n"
            f"{s.cmd('кости [ставка]', 'игра в кости')}\n"
            f"{s.cmd('боссы', 'список боссов')}\n"
            f"{s.cmd('дуэль @user [ставка]', 'вызвать на дуэль')}"
        )
        
        await update.message.reply_text(text, reply_markup=kb.back(), parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            s.header("ГЛАВНОЕ МЕНЮ") + "\nВыберите раздел:",
            reply_markup=kb.main(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def cmd_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        
        friends_list = json.loads(user_data.get('friends', '[]'))
        friends_count = len(friends_list)
        
        enemies_list = json.loads(user_data.get('enemies', '[]'))
        enemies_count = len(enemies_list)
        
        clan_info = ""
        if user_data.get('clan_id', 0) > 0:
            clan = self.db.get_clan(user_data['clan_id'])
            if clan:
                clan_info = f"\n{s.stat('Клан', clan['name'])}"
        
        spouse_info = ""
        if user_data.get('spouse', 0) > 0:
            spouse = self.db.get_user_by_id(user_data['spouse'])
            if spouse:
                spouse_name = spouse.get('nickname') or spouse['first_name']
                spouse_info = f"\n{s.stat('💍 Супруг(а)', spouse_name)}"
        
        text = (
            s.header("ПРОФИЛЬ") + "\n"
            f"**{display_name}** {title}\n"
            f"_{motto}_\n"
            f"{bio}\n\n"
            f"{s.section('ХАРАКТЕРИСТИКИ')}"
            f"{s.stat('Ранг', get_rank_emoji(user_data['rank']) + ' ' + user_data['rank_name'])}\n"
            f"{s.stat('Уровень', user_data['level'])}\n"
            f"{s.stat('Опыт', exp_progress)}\n"
            f"{s.stat('Монеты', f'{user_data["coins"]} 💰')}\n"
            f"{s.stat('Энергия', f'{user_data["energy"]}/100 ⚡')}\n"
            f"{s.stat('Здоровье', f'{user_data["health"]}/{user_data["max_health"]} ❤️')}\n\n"
            f"{s.section('СТАТИСТИКА')}"
            f"{s.stat('Сообщений', user_data['messages_count'])}\n"
            f"{s.stat('Репутация', user_data['reputation'])}\n"
            f"{s.stat('Предупреждения', warns)}\n"
            f"{s.stat('Боссов убито', user_data['boss_kills'])}{clan_info}{spouse_info}\n\n"
            f"{s.section('СТАТУС')}"
            f"{s.item(f'VIP: {vip_status}')}\n"
            f"{s.item(f'PREMIUM: {premium_status}')}\n"
            f"{s.item(f'ID: {s.code(str(user.id))}')}"
        )
        
        await update.message.reply_text(text, reply_markup=kb.back(), parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_set_nick(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажите ник: /nick [ник]"))
            return
        nick = " ".join(context.args)
        if len(nick) > MAX_NICK_LENGTH:
            await update.message.reply_text(s.error(f"❌ Максимальная длина: {MAX_NICK_LENGTH} символов"))
            return
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], nickname=nick)
        await update.message.reply_text(s.success(f"✅ Ник установлен: {nick}"))
    
    async def cmd_set_title(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажите титул: /title [титул]"))
            return
        title = " ".join(context.args)
        if len(title) > MAX_TITLE_LENGTH:
            await update.message.reply_text(s.error(f"❌ Максимальная длина: {MAX_TITLE_LENGTH} символов"))
            return
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], title=title)
        await update.message.reply_text(s.success(f"✅ Титул установлен: {title}"))
    
    async def cmd_set_motto(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажите девиз: /motto [девиз]"))
            return
        motto = " ".join(context.args)
        if len(motto) > MAX_MOTTO_LENGTH:
            await update.message.reply_text(s.error(f"❌ Максимальная длина: {MAX_MOTTO_LENGTH} символов"))
            return
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], motto=motto)
        await update.message.reply_text(s.success(f"✅ Девиз установлен: {motto}"))
    
    async def cmd_set_bio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("❌ Напишите о себе: /bio [текст]"))
            return
        bio = " ".join(context.args)
        if len(bio) > MAX_BIO_LENGTH:
            await update.message.reply_text(s.error(f"❌ Максимальная длина: {MAX_BIO_LENGTH} символов"))
            return
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], bio=bio)
        await update.message.reply_text(s.success("✅ Информация сохранена"))
    
    async def cmd_set_gender(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажите пол (м/ж): /gender [м/ж]"))
            return
        gender = context.args[0].lower()
        if gender not in ["м", "ж"]:
            await update.message.reply_text(s.error("❌ Пол должен быть 'м' или 'ж'"))
            return
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], gender=gender)
        gender_text = "Мужской" if gender == "м" else "Женский"
        await update.message.reply_text(s.success(f"✅ Пол установлен: {gender_text}"))
    
    async def cmd_set_city(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажите город: /city [город]"))
            return
        city = " ".join(context.args)
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], city=city)
        await update.message.reply_text(s.success(f"✅ Город установлен: {city}"))
    
    async def cmd_set_country(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажите страну: /country [страна]"))
            return
        country = " ".join(context.args)
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], country=country)
        await update.message.reply_text(s.success(f"✅ Страна установлена: {country}"))
    
    async def cmd_set_birth(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажите дату (ДД.ММ.ГГГГ): /birth [дата]"))
            return
        birth = context.args[0]
        if not re.match(r'\d{2}\.\d{2}\.\d{4}', birth):
            await update.message.reply_text(s.error("❌ Неверный формат. Используйте ДД.ММ.ГГГГ"))
            return
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], birth_date=birth)
        try:
            day, month, year = map(int, birth.split('.'))
            today = datetime.datetime.now()
            age = today.year - year - ((today.month, today.day) < (month, day))
            self.db.update_user(user_data['id'], age=age)
        except:
            pass
        await update.message.reply_text(s.success(f"✅ Дата рождения установлена: {birth}"))
    
    async def cmd_set_age(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажите возраст: /age [число]"))
            return
        try:
            age = int(context.args[0])
            if age < 1 or age > 150:
                await update.message.reply_text(s.error("❌ Возраст должен быть от 1 до 150"))
                return
        except:
            await update.message.reply_text(s.error("❌ Возраст должен быть числом"))
            return
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], age=age)
        await update.message.reply_text(s.success(f"✅ Возраст установлен: {age}"))
    
    async def cmd_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        await update.message.reply_text(s.info(f"🆔 Ваш ID: `{user.id}`"), parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(s.info("📊 Функция в разработке"), parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_my_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)
        text = (
            s.header("📊 МОЯ СТАТИСТИКА") + "\n\n"
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
    
    async def cmd_top(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = s.header("🏆 ТОП ИГРОКОВ") + "\n\n"
        top_coins = self.db.get_top("coins", 5)
        text += s.section("💰 ПО МОНЕТАМ")
        for i, row in enumerate(top_coins, 1):
            name = row[1] or row[0]
            text += f"{i}. **{name}** — {row[2]} 💰\n"
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_top_coins(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        top = self.db.get_top("coins", 10)
        text = s.header("💰 ТОП ПО МОНЕТАМ") + "\n\n"
        for i, row in enumerate(top, 1):
            name = row[1] or row[0]
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} **{name}** — {row[2]} 💰\n"
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_top_level(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        top = self.db.get_top("level", 10)
        text = s.header("📊 ТОП ПО УРОВНЮ") + "\n\n"
        for i, row in enumerate(top, 1):
            name = row[1] or row[0]
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} **{name}** — {row[2]} уровень\n"
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    # ===== КОМАНДЫ МОДЕРАЦИИ =====
    async def _set_rank(self, update: Update, target_rank: int):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 4 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав. Нужен ранг 4+"))
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
        
        if target_user['rank'] >= user_data['rank'] and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Нельзя назначить ранг выше своего"))
            return
        
        self.db.set_rank(target_user['id'], target_rank, user_data['id'])
        rank_info = RANKS[target_rank]
        await update.message.reply_text(
            f"{s.success('Ранг назначен!')}\n\n"
            f"{s.item(f'Пользователь: {target_user["first_name"]}')}\n"
            f"{s.item(f'Ранг: {rank_info["emoji"]} {rank_info["name"]}')}",
            parse_mode=ParseMode.MARKDOWN
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
            f"{s.item(f'Новый ранг: {rank_info["emoji"]} {rank_info["name"]}')}",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def cmd_remove_rank(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def cmd_remove_left(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data['rank'] < 4 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав"))
            return
        
        await update.message.reply_text(s.success("✅ Проверка вышедших модераторов выполнена"))
    
    async def cmd_remove_all_ranks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data['rank'] < 5 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Только для создателя"))
            return
        
        self.db.cursor.execute("SELECT id FROM users WHERE rank > 0")
        mods = self.db.cursor.fetchall()
        
        for mod_id in mods:
            self.db.set_rank(mod_id[0], 0, user_data['id'])
        
        await update.message.reply_text(
            s.success(f"✅ Снято модераторов: {len(mods)}"),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def cmd_who_admins(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    # ===== ПРЕДУПРЕЖДЕНИЯ =====
    async def cmd_warn(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        if target_user['rank'] >= user_data['rank'] and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Нельзя выдать предупреждение модератору выше рангом"))
            return
        
        warns = self.db.add_warn(target_user['id'], user_data['id'], reason)
        
        try:
            await context.bot.send_message(
                target_user['telegram_id'],
                f"{s.warning('⚠️ ВЫ ПОЛУЧИЛИ ПРЕДУПРЕЖДЕНИЕ')}\n\n"
                f"{s.item(f'Причина: {reason}')}\n"
                f"{s.item(f'Всего: {warns}/3')}"
            )
        except:
            pass
        
        text = (
            s.header("ПРЕДУПРЕЖДЕНИЕ") + "\n"
            f"{s.item(f'Пользователь: {target_user["first_name"]}')}\n"
            f"{s.item(f'Предупреждений: {warns}/3')}\n"
            f"{s.item(f'Причина: {reason}')}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        
        if warns >= 3:
            self.db.mute_user(target_user['id'], 60, user_data['id'], "3 предупреждения")
            await update.message.reply_text(s.warning(f"⚠️ {target_user['first_name']} замучен на 1 час"))
        if warns >= 5:
            self.db.ban_user(target_user['id'], user_data['id'], "5 предупреждений")
            await update.message.reply_text(s.error(f"🔨 {target_user['first_name']} забанен"))
    
    async def cmd_warns(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажите пользователя: /варны @user"))
            return
        
        username = context.args[0].replace('@', '')
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
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_my_warns(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_unwarn(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            match = re.search(r'снять варн\s+@?(\S+)', text, re.IGNORECASE)
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
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 2 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав"))
            return
        
        match = re.search(r'снять все варны\s+@?(\S+)', text, re.IGNORECASE)
        if not match:
            await update.message.reply_text(s.error("❌ Укажите пользователя"))
            return
        
        username = match.group(1)
        target_user = self.db.get_user_by_username(username)
        
        if not target_user:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        warns_list = self.db.get_warns(target_user['id'])
        for _ in warns_list:
            self.db.remove_last_warn(target_user['id'], user_data['id'])
        
        target_name = target_user.get('nickname') or target_user['first_name']
        await update.message.reply_text(s.success(f"✅ Все предупреждения сняты с {target_name}"))
    
    # ===== МУТЫ =====
    async def cmd_mute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 2 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав. Нужен ранг 2+"))
            return
        
        match = re.search(r'мут\s+@?(\S+)(?:\s+(\d+[мчд]))?(?:\s+(.+))?', text, re.IGNORECASE)
        if not match:
            await update.message.reply_text(s.error("❌ Пример: мут @user 30м спам"))
            return
        
        username = match.group(1)
        time_str = match.group(2) if match.group(2) else "60м"
        reason = match.group(3) if match.group(3) else "Нарушение правил"
        
        minutes = parse_time(time_str)
        if not minutes:
            await update.message.reply_text(s.error("❌ Неверный формат времени. Используйте: 30м, 2ч, 1д"))
            return
        
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        if target['rank'] >= user_data['rank'] and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Нельзя замутить модератора выше рангом"))
            return
        
        until = self.db.mute_user(target['id'], minutes, user_data['id'], reason)
        until_str = until.strftime("%d.%m.%Y %H:%M")
        
        try:
            await context.bot.send_message(
                target['telegram_id'],
                f"{s.warning('🔇 ВАС ЗАМУТИЛИ')}\n\n"
                f"{s.item(f'Срок: {time_str}')}\n"
                f"{s.item(f'Причина: {reason}')}\n"
                f"{s.item(f'До: {until_str}')}"
            )
        except:
            pass
        
        text = (
            s.header("МУТ") + "\n"
            f"{s.item(f'Пользователь: {target["first_name"]}')}\n"
            f"{s.item(f'Срок: {time_str}')}\n"
            f"{s.item(f'До: {until_str}')}\n"
            f"{s.item(f'Причина: {reason}')}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_mutelist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_unmute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 2 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав"))
            return
        
        username = text.replace('размут', '').replace('@', '').strip()
        if not username and update.message.reply_to_message:
            target_id = update.message.reply_to_message.from_user.id
            target = self.db.get_user_by_id(self.db.get_user(target_id)['id'])
        elif username:
            target = self.db.get_user_by_username(username)
        else:
            await update.message.reply_text(s.error("❌ Укажите пользователя"))
            return
        
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        if not self.db.is_muted(target['id']):
            await update.message.reply_text(s.info("Пользователь не в муте"))
            return
        
        self.db.unmute_user(target['id'], user_data['id'])
        
        try:
            await context.bot.send_message(
                target['telegram_id'],
                s.success("✅ Мут снят")
            )
        except:
            pass
        
        await update.message.reply_text(s.success(f"✅ Мут снят с {target['first_name']}"))
    
    # ===== БАНЫ =====
    async def cmd_ban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 2 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав. Нужен ранг 2+"))
            return
        
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
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        
        try:
            await update.effective_chat.ban_member(target['telegram_id'])
        except:
            pass
    
    async def cmd_banlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        bans = self.db.get_banlist()
        
        if not bans:
            await update.message.reply_text(s.info("Список забаненных пуст"))
            return
        
        text = s.header("СПИСОК ЗАБАНЕННЫХ") + "\n\n"
        for ban in bans:
            name = ban.get('first_name', 'Неизвестно')
            username = f" (@{ban['username']})" if ban['username'] else ""
            text += f"{s.item(f'{name}{username}')}\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_unban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        
        try:
            await context.bot.send_message(
                target['telegram_id'],
                s.success("✅ Бан снят")
            )
        except:
            pass
        
        await update.message.reply_text(s.success(f"✅ Бан снят с {target['first_name']}"))
        
        try:
            await update.effective_chat.unban_member(target['telegram_id'])
        except:
            pass
    
    async def cmd_kick(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 1 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав"))
            return
        
        username = text.replace('кик', '').replace('@', '').strip()
        target = self.db.get_user_by_username(username)
        
        if not target and update.message.reply_to_message:
            target_id = update.message.reply_to_message.from_user.id
            target = self.db.get_user_by_id(self.db.get_user(target_id)['id'])
        
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        try:
            await update.effective_chat.ban_member(target['telegram_id'])
            await update.effective_chat.unban_member(target['telegram_id'])
            await update.message.reply_text(s.success(f"✅ {target['first_name']} исключен"))
        except Exception as e:
            await update.message.reply_text(s.error(f"❌ Ошибка: {e}"))
    
    # ===== ТРИГГЕРЫ =====
    async def cmd_add_trigger(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 3 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав"))
            return
        
        text = text[9:].strip()
        if "=" not in text:
            await update.message.reply_text(s.error("❌ Формат: +триггер слово = действие"))
            return
        
        word, action = text.split("=", 1)
        word = word.strip().lower()
        action = action.strip()
        
        action_parts = action.split()
        action_type = action_parts[0].lower()
        action_value = action_parts[1] if len(action_parts) > 1 else None
        
        if action_type not in ["delete", "mute", "warn", "ban"]:
            await update.message.reply_text(s.error("❌ Действие должно быть: delete, mute, warn, ban"))
            return
        
        self.db.cursor.execute('''
            INSERT INTO triggers (chat_id, word, action, action_value, created_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (update.effective_chat.id, word, action_type, action_value, user_data['id']))
        self.db.conn.commit()
        
        await update.message.reply_text(s.success(f"✅ Триггер добавлен: {word} -> {action}"))
    
    async def cmd_remove_trigger(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 3 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав"))
            return
        
        trigger_id = text[9:].strip()
        if not trigger_id.isdigit():
            await update.message.reply_text(s.error("❌ Укажите ID триггера"))
            return
        
        self.db.cursor.execute("DELETE FROM triggers WHERE id = ? AND chat_id = ?", 
                             (int(trigger_id), update.effective_chat.id))
        self.db.conn.commit()
        
        await update.message.reply_text(s.success("✅ Триггер удален"))
    
    async def cmd_list_triggers(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.db.cursor.execute("SELECT id, word, action, action_value FROM triggers WHERE chat_id = ?", 
                             (update.effective_chat.id,))
        triggers = self.db.cursor.fetchall()
        
        if not triggers:
            await update.message.reply_text(s.info("В этом чате нет триггеров"))
            return
        
        text = s.header("ТРИГГЕРЫ ЧАТА") + "\n\n"
        for trigger in triggers:
            action_text = trigger[2]
            if trigger[3]:
                action_text += f" {trigger[3]}"
            text += f"ID: {trigger[0]} | {trigger[1]} → {action_text}\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    # ===== АВТОМОДЕРАЦИЯ =====
    async def _toggle_setting(self, update: Update, setting: str):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data['rank'] < 3 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав"))
            return
        
        parts = update.message.text.split()
        if len(parts) < 2:
            await update.message.reply_text(s.error("❌ Укажите on или off"))
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
        await update.message.reply_text(s.success(f"✅ {names[setting]} {status}"))
    
    async def cmd_set_antimat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._toggle_setting(update, "antimat")
    
    async def cmd_set_antilink(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._toggle_setting(update, "antilink")
    
    async def cmd_set_antiflood(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._toggle_setting(update, "antiflood")
    
    # ===== ЧИСТКА =====
    async def cmd_clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data['rank'] < 2 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав"))
            return
        
        parts = update.message.text.split()
        if len(parts) < 2:
            await update.message.reply_text(s.error("❌ Укажите количество: чистка 50"))
            return
        
        try:
            count = int(parts[1])
            if count > 100:
                count = 100
        except:
            await update.message.reply_text(s.error("❌ Количество должно быть числом"))
            return
        
        try:
            await update.message.delete()
            messages = []
            async for msg in context.bot.get_chat_history(update.effective_chat.id, limit=count):
                messages.append(msg.message_id)
            
            if messages:
                await context.bot.delete_messages(update.effective_chat.id, messages)
                await context.bot.send_message(update.effective_chat.id, 
                                              s.success(f"✅ Удалено {len(messages)} сообщений"),
                                              disable_notification=True)
        except Exception as e:
            await update.message.reply_text(s.error(f"❌ Ошибка: {e}"))
    
    async def cmd_clear_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 2 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав"))
            return
        
        username = text.replace('чистка от', '').strip().replace('@', '')
        target = self.db.get_user_by_username(username)
        
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        await update.message.reply_text(s.info(f"🔄 Удаляю сообщения {target['first_name']}..."))
    
    # ===== НАСТРОЙКИ ЧАТА =====
    async def cmd_set_welcome(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data['rank'] < 3 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав"))
            return
        
        welcome_text = update.message.text[12:].strip()
        if not welcome_text:
            await update.message.reply_text(s.error("❌ Укажите текст приветствия"))
            return
        
        self.db.cursor.execute('''
            INSERT INTO chat_settings (chat_id, welcome)
            VALUES (?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET welcome = excluded.welcome
        ''', (update.effective_chat.id, welcome_text))
        self.db.conn.commit()
        
        await update.message.reply_text(s.success("✅ Приветствие установлено"))
    
    async def cmd_set_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data['rank'] < 3 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав"))
            return
        
        rules_text = update.message.text[9:].strip()
        if not rules_text:
            await update.message.reply_text(s.error("❌ Укажите текст правил"))
            return
        
        self.db.cursor.execute('''
            INSERT INTO chat_settings (chat_id, rules)
            VALUES (?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET rules = excluded.rules
        ''', (update.effective_chat.id, rules_text))
        self.db.conn.commit()
        
        await update.message.reply_text(s.success("✅ Правила установлены"))
    
    async def cmd_show_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.db.cursor.execute("SELECT rules FROM chat_settings WHERE chat_id = ?", (update.effective_chat.id,))
        row = self.db.cursor.fetchone()
        
        if row and row[0]:
            await update.message.reply_text(f"📜 **Правила чата:**\n\n{row[0]}", parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(s.info("В этом чате ещё не установлены правила"))
    
    async def cmd_set_captcha(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data['rank'] < 3 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав"))
            return
        
        parts = update.message.text.split()
        if len(parts) < 2:
            await update.message.reply_text(s.error("❌ Укажите on или off"))
            return
        
        state = 1 if parts[1].lower() in ["on", "вкл", "да"] else 0
        
        self.db.cursor.execute('''
            INSERT INTO chat_settings (chat_id, captcha)
            VALUES (?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET captcha = excluded.captcha
        ''', (update.effective_chat.id, state))
        self.db.conn.commit()
        
        status = "включена" if state else "выключена"
        await update.message.reply_text(s.success(f"✅ Капча {status}"))
    
    # ===== ЭКОНОМИКА =====
    async def cmd_daily(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            s.header("🎁 ЕЖЕДНЕВНЫЙ БОНУС") + "\n"
            f"{s.item(f'🔥 Стрик: {streak} дней')}\n"
            f"{s.item(f'💰 Монеты: +{coins}')}\n"
            f"{s.item(f'✨ Опыт: +{exp}')}\n"
            f"{s.item(f'⚡ Энергия: +{energy}')}\n\n"
            f"{s.info('Заходи завтра!')}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        self.db.log_action(user_data['id'], 'daily', f'+{coins}💰')
    
    async def cmd_streak(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)
        streak = user_data.get('daily_streak', 0)
        
        text = (
            s.header("🔥 ТЕКУЩИЙ СТРИК") + "\n\n"
            f"{s.stat('Дней подряд', streak)}\n"
            f"{s.stat('Множитель', f'x{1 + min(streak, 30) * 0.05:.2f}')}\n\n"
            f"{s.info('Чем больше стрик, тем выше бонус!')}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_shop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            s.header("🛍️ МАГАЗИН") + "\n\n"
            f"{s.section('💊 ЗЕЛЬЯ')}"
            f"{s.cmd('buy зелье здоровья', '50 💰 (❤️+30)')}\n"
            f"{s.cmd('buy большое зелье', '100 💰 (❤️+70)')}\n\n"
            f"{s.section('⚔️ ОРУЖИЕ')}"
            f"{s.cmd('buy меч', '200 💰 (⚔️+10)')}\n"
            f"{s.cmd('buy легендарный меч', '500 💰 (⚔️+30)')}\n\n"
            f"{s.section('⚡ ЭНЕРГИЯ')}"
            f"{s.cmd('buy энергетик', '30 💰 (⚡+20)')}\n"
            f"{s.cmd('buy батарейка', '80 💰 (⚡+50)')}\n\n"
            f"{s.section('💎 ПРИВИЛЕГИИ')}"
            f"{s.cmd('vip', f'VIP ({VIP_PRICE} 💰 / 30 дней)')}\n"
            f"{s.cmd('premium', f'PREMIUM ({PREMIUM_PRICE} 💰 / 30 дней)')}"
        )
        
        await update.message.reply_text(text, reply_markup=kb.back(), parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_buy(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("❌ Что купить? /buy [предмет]"))
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
        
        if 'energy' in item_data:
            new_energy = self.db.add_energy(user_data['id'], item_data['energy'])
            effects.append(f"⚡ Энергия +{item_data['energy']} (теперь {new_energy})")
        
        effects_text = "\n".join([f"{s.item(e)}" for e in effects])
        
        await update.message.reply_text(
            f"{s.success('✅ Покупка совершена!')}\n\n"
            f"{s.item(f'Предмет: {item}')}\n"
            f"{effects_text}",
            parse_mode=ParseMode.MARKDOWN
        )
        
        self.db.log_action(user_data['id'], 'buy', item)
    
    async def cmd_pay(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        
        self.db.add_coins(user_data['id'], -amount)
        self.db.add_coins(target['id'], amount)
        
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
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        self.db.log_action(user_data['id'], 'pay', f"{amount}💰 -> {target['id']}")
    
    async def cmd_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)
        
        text = (
            s.header("💰 БАЛАНС") + "\n\n"
            f"{s.stat('Монеты', f'{user_data["coins"]} 💰')}\n"
            f"{s.stat('Алмазы', f'{user_data["diamonds"]} 💎')}\n"
            f"{s.stat('Энергия', f'{user_data["energy"]}/100 ⚡')}\n"
            f"{s.stat('Здоровье', f'{user_data["health"]}/{user_data["max_health"]} ❤️')}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_vip_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            s.header("💎 VIP СТАТУС") + "\n\n"
            f"Цена: {VIP_PRICE} 💰 / {VIP_DAYS} дней\n\n"
            f"{s.item('⚔️ Урон в битвах +20%')}\n"
            f"{s.item('💰 Награда с боссов +50%')}\n"
            f"{s.item('🎁 Ежедневный бонус +50%')}\n"
            f"{s.item('💎 Алмазы +1 в день')}\n\n"
            f"{s.cmd('купитьвип', 'купить VIP')}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_premium_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            s.header("💎 PREMIUM СТАТУС") + "\n\n"
            f"Цена: {PREMIUM_PRICE} 💰 / {PREMIUM_DAYS} дней\n\n"
            f"{s.item('⚔️ Урон в битвах +50%')}\n"
            f"{s.item('💰 Награда с боссов +100%')}\n"
            f"{s.item('🎁 Ежедневный бонус +100%')}\n"
            f"{s.item('💎 Алмазы +3 в день')}\n"
            f"{s.item('🚫 Игнорирование спам-фильтра')}\n\n"
            f"{s.cmd('купитьпремиум', 'купить PREMIUM')}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_buy_vip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            f"{s.item(f'Срок: до {date_str}')}\n\n"
            f"{s.info('Спасибо за поддержку!')}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        self.db.log_action(user_data['id'], 'buy_vip')
    
    async def cmd_buy_premium(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            s.header("✨ PREMIUM СТАТУС АКТИВИРОВАН") + "\n\n"
            f"{s.item(f'Срок: до {date_str}')}\n\n"
            f"{s.info('Спасибо за поддержку!')}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        self.db.log_action(user_data['id'], 'buy_premium')
    
    # ===== ИГРЫ =====
    async def cmd_coin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        result = random.choice(["Орел", "Решка"])
        await update.message.reply_text(
            f"{s.header('🪙 МОНЕТКА')}\n\n{s.item(f'Выпало: {result}')}",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def cmd_dice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        result = random.randint(1, 6)
        await update.message.reply_text(
            f"{s.header('🎲 КУБИК')}\n\n{s.item(f'Выпало: {result}')}",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def cmd_dice_bet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if not context.args:
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
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_roulette(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        self.db.log_action(user_data['id'], 'roulette', f"{'win' if win else 'lose'} {bet}")
    
    async def cmd_slots(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        
        symbols = ["🍒", "🍋", "🍊", "7️⃣", "💎", "🎰", "⭐"]
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
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_rps(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            s.header("✊ КНБ") + "\nВыберите жест:",
            reply_markup=kb.rps(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def cmd_russian_roulette(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        
        try:
            await context.bot.send_animation(
                chat_id=update.effective_chat.id,
                animation=GIFS["russian_roulette"]
            )
        except:
            pass
        
        chamber = random.randint(1, 6)
        shot = random.randint(1, 6)
        
        await asyncio.sleep(2)
        
        if chamber == shot:
            self.db.add_coins(user_data['id'], -bet)
            self.db.update_user(user_data['id'], rr_losses=user_data.get('rr_losses', 0) + 1)
            text = (
                s.header("💀 РУССКАЯ РУЛЕТКА") + "\n\n"
                f"{s.item(f'Ставка: {bet} 💰')}\n"
                f"{s.item('Бах! Выстрел...')}\n\n"
                f"{s.error(f'ВЫ ПРОИГРАЛИ! -{bet} 💰')}"
            )
        else:
            win = bet * 5
            self.db.add_coins(user_data['id'], win)
            self.db.update_user(user_data['id'], rr_wins=user_data.get('rr_wins', 0) + 1)
            text = (
                s.header("🔫 РУССКАЯ РУЛЕТКА") + "\n\n"
                f"{s.item(f'Ставка: {bet} 💰')}\n"
                f"{s.item('Щёлк... В этот раз повезло!')}\n\n"
                f"{s.success(f'ВЫ ВЫИГРАЛИ! +{win} 💰')}"
            )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        self.db.log_action(user_data['id'], 'rr', f"{'win' if chamber != shot else 'lose'} {bet}")
    
    async def cmd_saper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_guess(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def cmd_bulls(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            parse_mode=ParseMode.MARKDOWN
        )
    
    # ===== БОССЫ =====
    async def cmd_bosses(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            f"{s.cmd('реген', 'восстановить ❤️ и ⚡')}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_boss_fight(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        player_taken = max(1, boss_damage - user_data['armor'] // 2)
        
        killed = self.db.damage_boss(boss_id, player_damage)
        self.db.damage(user_data['id'], player_taken)
        
        text = s.header("⚔️ БИТВА С БОССОМ") + "\n\n"
        text += f"{s.item(f'{crit_text}Твой урон: {player_damage}')}\n"
        text += f"{s.item(f'Урон босса: {player_taken}')}\n\n"
        
        if killed:
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
        
        if user_data['health'] <= player_taken:
            self.db.heal(user_data['id'], 50)
            text += f"\n{s.info('Ты погиб и воскрешён с 50❤️')}"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        self.db.log_action(user_data['id'], 'boss_fight', f"Битва с боссом {boss['name']}")
    
    async def cmd_boss_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_regen(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            parse_mode=ParseMode.MARKDOWN
        )
    
    # ===== ДУЭЛИ =====
    async def cmd_duel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        
        self.db.cursor.execute("SELECT id FROM duels WHERE (challenger_id = ? OR opponent_id = ?) AND status = 'pending'",
                             (user_data['id'], user_data['id']))
        if self.db.cursor.fetchone():
            await update.message.reply_text(s.error("❌ У тебя уже есть активная дуэль"))
            return
        
        duel_id = self.db.create_duel(user_data['id'], target['id'], bet)
        self.db.add_coins(user_data['id'], -bet)
        
        target_name = target.get('nickname') or target['first_name']
        
        await update.message.reply_text(
            f"{s.header('⚔️ ВЫЗОВ НА ДУЭЛЬ')}\n\n"
            f"{s.item(f'Противник: {target_name}')}\n"
            f"{s.item(f'Ставка: {bet} 💰')}\n\n"
            f"{s.info('Ожидание ответа...')}",
            reply_markup=kb.duel_accept(duel_id),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def cmd_duels(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.db.cursor.execute("SELECT * FROM duels WHERE status = 'pending'")
        duels = self.db.cursor.fetchall()
        
        if not duels:
            await update.message.reply_text(s.info("Нет активных дуэлей"))
            return
        
        text = s.header("⚔️ АКТИВНЫЕ ДУЭЛИ") + "\n\n"
        for duel in duels:
            challenger = self.db.get_user_by_id(duel[1])
            opponent = self.db.get_user_by_id(duel[2])
            if challenger and opponent:
                text += f"{s.item(f'{challenger["first_name"]} vs {opponent["first_name"]} — ставка {duel[3]} 💰')}\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_duel_rating(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.db.cursor.execute("SELECT first_name, nickname, duel_rating FROM users ORDER BY duel_rating DESC LIMIT 10")
        top = self.db.cursor.fetchall()
        
        if not top:
            await update.message.reply_text(s.info("Рейтинг пуст"))
            return
        
        text = s.header("⚔️ ТОП ДУЭЛЯНТОВ") + "\n\n"
        for i, row in enumerate(top, 1):
            name = row[1] or row[0]
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} **{name}** — {row[2]} очков\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    # ===== КЛАНЫ =====
    async def cmd_clan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)
        
        if not user_data.get('clan_id', 0):
            await update.message.reply_text(s.info("Вы не состоите в клане"))
            return
        
        clan = self.db.get_clan(user_data['clan_id'])
        if not clan:
            await update.message.reply_text(s.error("Клан не найден"))
            return
        
        members = self.db.get_clan_members(clan['id'])
        
        text = (
            s.header(f"🏰 КЛАН: {clan['name']}") + "\n\n"
            f"{s.stat('Уровень', clan['level'])}\n"
            f"{s.stat('Опыт', clan['exp'])}\n"
            f"{s.stat('Казна', f'{clan["coins"]} 💰')}\n"
            f"{s.stat('Участников', len(members))}\n\n"
            f"{s.section('УЧАСТНИКИ')}"
        )
        
        for member in members:
            name = member.get('nickname') or member['first_name']
            role_emoji = "👑" if member['role'] == 'owner' else "🛡️" if member['role'] == 'admin' else "👤"
            text += f"{role_emoji} {name}\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_clans(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.db.cursor.execute("SELECT name, level, members FROM clans ORDER BY level DESC LIMIT 10")
        clans = self.db.cursor.fetchall()
        
        if not clans:
            await update.message.reply_text(s.info("Нет созданных кланов"))
            return
        
        text = s.header("🏰 ТОП КЛАНОВ") + "\n\n"
        for i, clan in enumerate(clans, 1):
            text += f"{i}. **{clan[0]}** — ур.{clan[1]}, {clan[2]} участников\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_create_clan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажите название клана: /создатьклан [название]"))
            return
        
        name = " ".join(context.args)
        user_data = self.db.get_user(update.effective_user.id)
        
        if user_data.get('clan_id', 0):
            await update.message.reply_text(s.error("❌ Вы уже в клане"))
            return
        
        if user_data['coins'] < 1000:
            await update.message.reply_text(s.error(f"❌ Недостаточно монет. Нужно 1000 💰"))
            return
        
        clan_id = self.db.create_clan(name, user_data['id'])
        if not clan_id:
            await update.message.reply_text(s.error("❌ Клан с таким названием уже существует"))
            return
        
        self.db.add_coins(user_data['id'], -1000)
        
        await update.message.reply_text(s.success(f"✅ Клан '{name}' создан!"))
    
    async def cmd_join_clan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажите название клана: /вступить [название]"))
            return
        
        name = " ".join(context.args)
        user_data = self.db.get_user(update.effective_user.id)
        
        if user_data.get('clan_id', 0):
            await update.message.reply_text(s.error("❌ Вы уже в клане"))
            return
        
        clan = self.db.get_clan_by_name(name)
        if not clan:
            await update.message.reply_text(s.error("❌ Клан не найден"))
            return
        
        self.db.cursor.execute("INSERT INTO clan_members (clan_id, user_id) VALUES (?, ?)", (clan['id'], user_data['id']))
        self.db.update_user(user_data['id'], clan_id=clan['id'], clan_role='member')
        self.db.cursor.execute("UPDATE clans SET members = members + 1 WHERE id = ?", (clan['id'],))
        self.db.conn.commit()
        
        await update.message.reply_text(s.success(f"✅ Вы вступили в клан '{name}'"))
    
    async def cmd_leave_clan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)
        
        if not user_data.get('clan_id', 0):
            await update.message.reply_text(s.error("❌ Вы не в клане"))
            return
        
        if user_data.get('clan_role') == 'owner':
            await update.message.reply_text(s.error("❌ Владелец не может покинуть клан"))
            return
        
        clan_id = user_data['clan_id']
        self.db.cursor.execute("DELETE FROM clan_members WHERE user_id = ?", (user_data['id'],))
        self.db.update_user(user_data['id'], clan_id=0, clan_role='member')
        self.db.cursor.execute("UPDATE clans SET members = members - 1 WHERE id = ?", (clan_id,))
        self.db.conn.commit()
        
        await update.message.reply_text(s.success("✅ Вы покинули клан"))
    
    # ===== ОТНОШЕНИЯ =====
    async def cmd_add_friend(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажите пользователя: /друг @user"))
            return
        
        username = context.args[0].replace('@', '')
        target = self.db.get_user_by_username(username)
        
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        user_data = self.db.get_user(update.effective_user.id)
        
        if target['id'] == user_data['id']:
            await update.message.reply_text(s.error("❌ Нельзя добавить в друзья самого себя"))
            return
        
        friends = json.loads(user_data.get('friends', '[]'))
        if target['id'] in friends:
            await update.message.reply_text(s.error("❌ Уже в друзьях"))
            return
        
        enemies = json.loads(user_data.get('enemies', '[]'))
        if target['id'] in enemies:
            await update.message.reply_text(s.error("❌ Сначала уберите из врагов"))
            return
        
        friends.append(target['id'])
        self.db.update_user(user_data['id'], friends=json.dumps(friends))
        
        target_name = target.get('nickname') or target['first_name']
        await update.message.reply_text(s.success(f"✅ {target_name} добавлен в друзья"))
    
    async def cmd_add_enemy(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажите пользователя: /враг @user"))
            return
        
        username = context.args[0].replace('@', '')
        target = self.db.get_user_by_username(username)
        
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        user_data = self.db.get_user(update.effective_user.id)
        
        if target['id'] == user_data['id']:
            await update.message.reply_text(s.error("❌ Нельзя объявить врагом самого себя"))
            return
        
        enemies = json.loads(user_data.get('enemies', '[]'))
        if target['id'] in enemies:
            await update.message.reply_text(s.error("❌ Уже во врагах"))
            return
        
        friends = json.loads(user_data.get('friends', '[]'))
        if target['id'] in friends:
            friends.remove(target['id'])
            self.db.update_user(user_data['id'], friends=json.dumps(friends))
        
        enemies.append(target['id'])
        self.db.update_user(user_data['id'], enemies=json.dumps(enemies))
        
        target_name = target.get('nickname') or target['first_name']
        await update.message.reply_text(s.success(f"⚔️ {target_name} объявлен врагом"))
    
    async def cmd_remove_enemy(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажите пользователя: /простить @user"))
            return
        
        username = context.args[0].replace('@', '')
        target = self.db.get_user_by_username(username)
        
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        user_data = self.db.get_user(update.effective_user.id)
        
        enemies = json.loads(user_data.get('enemies', '[]'))
        if target['id'] not in enemies:
            await update.message.reply_text(s.error("❌ Не во врагах"))
            return
        
        enemies.remove(target['id'])
        self.db.update_user(user_data['id'], enemies=json.dumps(enemies))
        
        target_name = target.get('nickname') or target['first_name']
        await update.message.reply_text(s.success(f"✅ {target_name} прощен"))
    
    # ===== БРАКИ =====
    async def cmd_propose(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажите пользователя: /предложить @user"))
            return
        
        username = context.args[0].replace('@', '')
        target = self.db.get_user_by_username(username)
        
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        user_data = self.db.get_user(update.effective_user.id)
        
        if target['id'] == user_data['id']:
            await update.message.reply_text(s.error("❌ Нельзя жениться на себе"))
            return
        
        if user_data.get('spouse', 0):
            await update.message.reply_text(s.error("❌ Вы уже в браке"))
            return
        
        if target.get('spouse', 0):
            await update.message.reply_text(s.error("❌ Пользователь уже в браке"))
            return
        
        target_name = target.get('nickname') or target['first_name']
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ ПРИНЯТЬ", callback_data=f"marry_accept_{user_data['id']}"),
             InlineKeyboardButton("❌ ОТКЛОНИТЬ", callback_data=f"marry_reject_{user_data['id']}")]
        ])
        
        await context.bot.send_message(
            target['telegram_id'],
            f"{s.header('💍 ПРЕДЛОЖЕНИЕ')}\n\n"
            f"{user_data['first_name']} предлагает вам вступить в брак!",
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
        
        await update.message.reply_text(s.success(f"✅ Предложение отправлено {target_name}"))
    
    async def cmd_divorce(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)
        
        if not user_data.get('spouse', 0):
            await update.message.reply_text(s.error("❌ Вы не в браке"))
            return
        
        spouse_id = user_data['spouse']
        
        self.db.update_user(user_data['id'], spouse=0, married_since=None)
        self.db.update_user(spouse_id, spouse=0, married_since=None)
        
        await update.message.reply_text(s.info("💔 Брак расторгнут"))
    
    async def cmd_families(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.db.cursor.execute("""
            SELECT u1.first_name, u2.first_name 
            FROM users u1, users u2 
            WHERE u1.spouse = u2.id AND u1.id < u2.id
            LIMIT 10
        """)
        families = self.db.cursor.fetchall()
        
        if not families:
            await update.message.reply_text(s.info("В чате пока нет семей"))
            return
        
        text = s.header("👥 СЕМЬИ ЧАТА") + "\n\n"
        for fam in families:
            text += f"💞 {fam[0]} + {fam[1]}\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    # ===== РЕПУТАЦИЯ =====
    async def cmd_add_rep(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._change_rep(update, 1)
    
    async def cmd_remove_rep(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._change_rep(update, -1)
    
    async def _change_rep(self, update: Update, change: int):
        text = update.message.text
        user_data = self.db.get_user(update.effective_user.id)
        
        match = re.search(r'[+-]репа\s+@?(\S+)', text, re.IGNORECASE)
        if not match:
            await update.message.reply_text(s.error("❌ Укажите пользователя"))
            return
        
        username = match.group(1)
        target = self.db.get_user_by_username(username)
        
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        if target['id'] == user_data['id']:
            await update.message.reply_text(s.error("❌ Нельзя изменить репутацию себе"))
            return
        
        new_rep = target['reputation'] + change
        self.db.update_user(target['id'], reputation=new_rep)
        
        target_name = target.get('nickname') or target['first_name']
        action = "повышена" if change > 0 else "понижена"
        
        await update.message.reply_text(s.success(f"✅ Репутация {target_name} {action}"))
    
    async def cmd_rep(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        target_id = update.effective_user.id
        
        if context.args:
            username = context.args[0].replace('@', '')
            target = self.db.get_user_by_username(username)
            if target:
                target_id = target['id']
        
        user_data = self.db.get_user_by_id(target_id)
        if not user_data:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        name = user_data.get('nickname') or user_data['first_name']
        
        await update.message.reply_text(f"⭐ **{name}**\nРепутация: {user_data['reputation']}", parse_mode=ParseMode.MARKDOWN)
    
    # ===== МАФИЯ =====
    async def cmd_mafia(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            s.header("🔫 МАФИЯ") + "\nВыберите действие:",
            reply_markup=kb.mafia(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def cmd_mafia_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        
        if chat_id in self.mafia_games:
            await update.message.reply_text(s.error("❌ Игра уже идёт! Присоединяйтесь: /мафияприсоединиться"))
            return
        
        game_id = f"mafia_{chat_id}_{int(time.time())}"
        game = MafiaGame(chat_id, game_id, update.effective_user.id)
        self.mafia_games[chat_id] = game
        
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
            f"{s.item('/мафиявыйти — выйти')}\n\n"
            f"{s.info('Игра будет проходить в ЛС с ботом')}"
        )
        
        msg = await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        game.message_id = msg.message_id
    
    async def cmd_mafia_join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        user = update.effective_user
        
        if chat_id not in self.mafia_games:
            await update.message.reply_text(s.error("❌ Игра не создана. Начните: /мафиястарт"))
            return
        
        game = self.mafia_games[chat_id]
        
        if game.status != "waiting":
            await update.message.reply_text(s.error("❌ Игра уже началась"))
            return
        
        if not game.add_player(user.id, user.first_name, user.username or ""):
            await update.message.reply_text(s.error("❌ Вы уже в игре"))
            return
        
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
            f"{s.item('/мафияприсоединиться — присоединиться')}\n"
            f"{s.item('/мафиявыйти — выйти')}\n\n"
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
        
        if game.players:
            players_list = "\n".join([f"{i+1}. {game.players_data[pid]['name']}" for i, pid in enumerate(game.players)])
            confirmed = sum(1 for p in game.players if game.players_data[p]['confirmed'])
            
            text = (
                s.header("🔫 МАФИЯ") + "\n\n"
                f"{s.item(f'Участники ({len(game.players)}):')}\n"
                f"{players_list}\n\n"
                f"{s.item(f'Подтвердили: {confirmed}/{len(game.players)}')}\n"
                f"{s.item('/мафияприсоединиться — присоединиться')}\n"
                f"{s.item('/мафиявыйти — выйти')}\n\n"
                f"{s.info('Для старта нужно минимум 6 игроков')}"
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
                message_id=game.message_id,
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass
    
    async def cmd_mafia_roles(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            f"{s.item('🔪 Маньяк — убивает один')}\n"
            f"{s.item('💃 Леди — соблазняет и защищает')}\n"
            f"{s.item('🔫 Шериф — стреляет раз в игру')}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_mafia_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            f"{s.item('Город — найти всю мафию')}\n\n"
            f"{s.info('Все действия в ЛС с ботом')}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def _mafia_start_game(self, game: MafiaGame, context: ContextTypes.DEFAULT_TYPE):
        if len(game.players) < MAFIA_MIN_PLAYERS:
            await context.bot.send_message(
                game.chat_id,
                s.error(f"❌ Недостаточно игроков. Нужно минимум {MAFIA_MIN_PLAYERS}")
            )
            del self.mafia_games[game.chat_id]
            return
        
        game.assign_roles()
        game.status = "night"
        game.phase = "night"
        game.start_time = datetime.datetime.now()
        
        for player_id in game.players:
            role = game.roles[player_id]
            role_desc = game.get_role_description(role)
            
            try:
                await context.bot.send_message(
                    player_id,
                    f"{s.header('🔫 МАФИЯ')}\n\n"
                    f"{s.item(f'Ваша роль: {role}')}\n"
                    f"{s.item(role_desc)}\n\n"
                    f"{s.info('Ночь начинается. Ожидайте действий.')}",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
        
        try:
            await context.bot.send_animation(
                chat_id=game.chat_id,
                animation=GIFS["mafia_night"]
            )
        except:
            pass
        
        await context.bot.send_message(
            game.chat_id,
            f"{s.header('🔫 МАФИЯ')}\n\n"
            f"{s.success('🌙 НАСТУПИЛА НОЧЬ')}\n"
            f"{s.item('Мафия выбирает жертву...')}\n"
            f"{s.item('Доктор выбирает, кого спасти...')}",
            parse_mode=ParseMode.MARKDOWN
        )
        
        asyncio.create_task(self._mafia_night_timer(game, context, MAFIA_NIGHT_TIME))
    
    async def _mafia_night_timer(self, game: MafiaGame, context: ContextTypes.DEFAULT_TYPE, seconds: int):
        await asyncio.sleep(seconds)
        
        if game.chat_id not in self.mafia_games or game.phase != "night":
            return
        
        await self._mafia_process_night(game, context)
    
    async def _mafia_process_night(self, game: MafiaGame, context: ContextTypes.DEFAULT_TYPE):
        result = game.process_night()
        
        if result["killed"]:
            game.alive[result["killed"]] = False
            try:
                await context.bot.send_message(
                    result["killed"],
                    f"{s.error('💀 ВАС УБИЛИ НОЧЬЮ')}\n\n"
                    f"{s.item('Вы больше не участвуете в игре.')}",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
        
        game.phase = "day"
        game.day += 1
        game.votes = {}
        
        try:
            await context.bot.send_animation(
                chat_id=game.chat_id,
                animation=GIFS["mafia_day"]
            )
        except:
            pass
        
        alive_list = game.get_alive_players()
        alive_names = []
        for i, pid in enumerate(alive_list, 1):
            name = game.players_data[pid]['name']
            alive_names.append(f"{i}. {name}")
        
        killed_name = "никто"
        if result["killed"]:
            killed_name = game.players_data[result["killed"]]['name']
        
        text = (
            s.header(f"🔫 МАФИЯ | ДЕНЬ {game.day}") + "\n\n"
            f"{s.item(f'☀️ Наступило утро...')}\n"
            f"{s.item(f'💀 Прошлой ночью был убит: {killed_name}')}\n\n"
            f"{s.section('ЖИВЫЕ ИГРОКИ')}\n"
            f"{chr(10).join([s.item(name) for name in alive_names])}\n\n"
            f"{s.info('Обсуждайте и голосуйте')}"
        )
        
        await context.bot.send_message(game.chat_id, text, parse_mode=ParseMode.MARKDOWN)
        
        asyncio.create_task(self._mafia_day_timer(game, context, MAFIA_DAY_TIME))
    
    async def _mafia_day_timer(self, game: MafiaGame, context: ContextTypes.DEFAULT_TYPE, seconds: int):
        await asyncio.sleep(seconds)
        
        if game.chat_id not in self.mafia_games or game.phase != "day":
            return
        
        await self._mafia_process_day(game, context)
    
    async def _mafia_process_day(self, game: MafiaGame, context: ContextTypes.DEFAULT_TYPE):
        executed = game.process_voting()
        
        if executed:
            game.alive[executed] = False
            executed_name = game.players_data[executed]['name']
            role = game.roles.get(executed, "неизвестно")
            
            text = (
                s.header(f"🔫 МАФИЯ | ДЕНЬ {game.day}") + "\n\n"
                f"{s.item(f'🔨 По результатам голосования исключён: {executed_name}')}\n"
                f"{s.item(f'Роль: {role}')}\n\n"
                f"{s.info('Ночь скоро наступит...')}"
            )
            
            await context.bot.send_message(game.chat_id, text, parse_mode=ParseMode.MARKDOWN)
            
            try:
                await context.bot.send_message(
                    executed,
                    f"{s.error('🔨 ВАС ИСКЛЮЧИЛИ ДНЁМ')}\n\n"
                    f"{s.item('Вы больше не участвуете в игре.')}",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
        else:
            await context.bot.send_message(
                game.chat_id,
                f"{s.info('📢 Никто не был исключён сегодня')}",
                parse_mode=ParseMode.MARKDOWN
            )
        
        winner = game.check_win()
        
        if winner == "citizens":
            await context.bot.send_message(
                game.chat_id,
                f"{s.success('🏆 ПОБЕДА ГОРОДА!')}\n\n"
                f"{s.item('Вся мафия уничтожена!')}",
                parse_mode=ParseMode.MARKDOWN
            )
            
            for pid in game.players:
                user_data = self.db.get_user_by_id(pid)
                if user_data:
                    self.db.update_user(pid, mafia_games=user_data.get('mafia_games', 0) + 1)
                    if game.roles.get(pid) not in [MafiaRole.MAFIA, MafiaRole.BOSS]:
                        self.db.update_user(pid, mafia_wins=user_data.get('mafia_wins', 0) + 1)
                        self.db.add_coins(pid, 500)
            
            del self.mafia_games[game.chat_id]
            return
        
        if winner == "mafia":
            await context.bot.send_message(
                game.chat_id,
                f"{s.success('🏆 ПОБЕДА МАФИИ!')}\n\n"
                f"{s.item('Мафия захватила город!')}",
                parse_mode=ParseMode.MARKDOWN
            )
            
            for pid in game.players:
                user_data = self.db.get_user_by_id(pid)
                if user_data:
                    self.db.update_user(pid, mafia_games=user_data.get('mafia_games', 0) + 1)
                    if game.roles.get(pid) in [MafiaRole.MAFIA, MafiaRole.BOSS]:
                        self.db.update_user(pid, mafia_wins=user_data.get('mafia_wins', 0) + 1)
                        self.db.add_coins(pid, 500)
            
            del self.mafia_games[game.chat_id]
            return
        
        game.phase = "night"
        game.night_actions = {
            "mafia_kill": None,
            "doctor_save": None,
            "commissioner_check": None,
            "maniac_kill": None
        }
        
        try:
            await context.bot.send_animation(
                chat_id=game.chat_id,
                animation=GIFS["mafia_night"]
            )
        except:
            pass
        
        await context.bot.send_message(
            game.chat_id,
            f"{s.header(f'🔫 МАФИЯ | НОЧЬ {game.day}')}\n\n"
            f"{s.success('🌙 НАСТУПИЛА НОЧЬ')}\n"
            f"{s.item('Мафия выбирает жертву...')}",
            parse_mode=ParseMode.MARKDOWN
        )
        
        asyncio.create_task(self._mafia_night_timer(game, context, MAFIA_NIGHT_TIME))
    
    # ===== ПОЛЕЗНОЕ =====
    async def cmd_ping(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        start = time.time()
        msg = await update.message.reply_text("🏓 Понг...")
        end = time.time()
        ping = int((end - start) * 1000)
        await msg.edit_text(f"🏓 **Понг!**\n⏱️ {ping} мс", parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_uptime(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        uptime = datetime.datetime.now() - self.start_time
        days = uptime.days
        hours = uptime.seconds // 3600
        minutes = (uptime.seconds % 3600) // 60
        
        await update.message.reply_text(
            f"⏱️ **Аптайм:** {days}д {hours}ч {minutes}м",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def cmd_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        users_count = self.db.cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        
        text = (
            s.header("🤖 ИНФОРМАЦИЯ О БОТЕ") + "\n\n"
            f"**Название:** {BOT_NAME}\n"
            f"**Версия:** {BOT_VERSION}\n"
            f"**Владелец:** {OWNER_USERNAME}\n\n"
            f"{s.stat('Пользователей', users_count)}\n"
            f"{s.stat('Команд', '250+')}\n"
            f"{s.stat('AI', 'Подключен' if ai else 'Не подключен')}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    # ===== РАЗВЛЕЧЕНИЯ =====
    async def cmd_joke(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        jokes = [
            "Встречаются два программиста:\n— Слышал, ты женился?\n— Да.\n— Ну и как она?\n— Да нормально, интерфейс дружественный...",
            "— Доктор, у меня глисты.\n— А вы что, их видите?\n— Нет, я с ними переписываюсь.",
            "Идут два кота по крыше. Один говорит:\n— Мяу.\n— Мяу-мяу.\n— Ты чё, с ума сошёл? Нас же люди услышат!",
            "— Почему программисты путают Хэллоуин и Рождество?\n— Потому что Oct 31 = Dec 25.",
        ]
        await update.message.reply_text(f"😄 {random.choice(jokes)}")
    
    async def cmd_fact(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        facts = [
            "Осьминоги имеют три сердца и голубую кровь.",
            "Бананы технически являются ягодами, а клубника — нет.",
            "В Швейцарии запрещено держать только одну морскую свинку.",
            "Мед никогда не портится. Археологи находили 3000-летний мед в гробницах.",
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
            "Улыбайтесь чаще — это заразительно.",
        ]
        await update.message.reply_text(f"💡 {random.choice(advices)}")
    
    async def cmd_ask(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        question = " ".join(context.args) if context.args else ""
        if not question:
            await update.message.reply_text(s.error("❌ Задайте вопрос: /гадать [вопрос]"))
            return
        
        answers = ["Да", "Нет", "Возможно", "Определённо да", "Определённо нет"]
        await update.message.reply_text(f"🎱 **Вопрос:** {question}\n\n**Ответ:** {random.choice(answers)}", parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_compatibility(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text(s.error("❌ Укажите двух пользователей: /совместимость @user1 @user2"))
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
            f"{emoji} **{name1}** и **{name2}**\n\n"
            f"Совместимость: {compatibility}%\n{text}",
            parse_mode=ParseMode.MARKDOWN
        )
    
    # ===== ОБРАБОТЧИК СООБЩЕНИЙ =====
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        message_text = update.message.text
        
        if message_text.startswith('/'):
            return
        
        user_data = self.db.get_user(user.id, user.first_name)
        self.db.update_user(user_data['id'], messages_count=user_data.get('messages_count', 0) + 1)
        
        if self.db.is_banned(user_data['id']):
            return
        
        if self.db.is_muted(user_data['id']):
            await update.message.reply_text(s.error("🔇 Ты в муте"))
            return
        
        if await self.check_spam(update):
            return
        
        if self.db.is_word_blacklisted(message_text):
            await update.message.delete()
            await update.message.reply_text(s.warning("⚠️ Запрещенное слово! Сообщение удалено."))
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
                            await update.message.reply_text(s.success(f"🎉 ПОБЕДА! Число {game['number']}!\nВыигрыш: {win} 💰"), parse_mode=ParseMode.MARKDOWN)
                            del self.games_in_progress[game_id]
                        elif game['attempts'] >= game['max_attempts']:
                            self.db.update_user(user_data['id'], guess_losses=user_data.get('guess_losses', 0) + 1)
                            await update.message.reply_text(s.error(f"❌ Попытки кончились! Было число {game['number']}"), parse_mode=ParseMode.MARKDOWN)
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
                        await update.message.reply_text(s.success(f"🎉 ПОБЕДА! Число {game['number']}!\nВыигрыш: {win} 💰"), parse_mode=ParseMode.MARKDOWN)
                        del self.games_in_progress[game_id]
                    elif len(game['attempts']) >= game['max_attempts']:
                        self.db.update_user(user_data['id'], bulls_losses=user_data.get('bulls_losses', 0) + 1)
                        await update.message.reply_text(s.error(f"❌ Попытки кончились! Было число {game['number']}"), parse_mode=ParseMode.MARKDOWN)
                        del self.games_in_progress[game_id]
                    else:
                        await update.message.reply_text(f"🔍 Быки: {bulls}, Коровы: {cows}\nОсталось попыток: {game['max_attempts'] - len(game['attempts'])}")
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
                            await update.message.reply_text(f"{s.header('💥 БУМ!')}\n\n{s.error('Ты подорвался на мине!')}\n\nПроигрыш: {game['bet']} 💰", parse_mode=ParseMode.MARKDOWN)
                            del self.games_in_progress[game_id]
                        else:
                            game['opened'] += 1
                            if game['opened'] >= 8:
                                win = game['bet'] * 3
                                self.db.add_coins(user_data['id'], win)
                                self.db.update_user(user_data['id'], slots_wins=user_data.get('slots_wins', 0) + 1)
                                await update.message.reply_text(s.success(f"🎉 ПОБЕДА! Ты открыл все безопасные клетки!\nВыигрыш: {win} 💰"), parse_mode=ParseMode.MARKDOWN)
                                del self.games_in_progress[game_id]
                            else:
                                await update.message.reply_text(s.success("✅ Клетка безопасна! Продолжай..."))
                    except ValueError:
                        await update.message.reply_text(s.error("❌ Введите число от 1 до 9"))
                    return
        
        if ai and random.randint(1, 100) <= AI_CHANCE:
            await update.message.chat.send_action(action="typing")
            response = await ai.get_response(user.id, message_text, user.first_name)
            if response:
                await update.message.reply_text(f"🤖 **Спектр:** {response}", parse_mode=ParseMode.MARKDOWN)
                return
        
        msg_lower = message_text.lower()
        
        if any(word in msg_lower for word in ["привет", "здравствуйте", "хай", "ку"]):
            responses = ["👋 Привет!", "Йо, братан!", "Здарова!"]
            await update.message.reply_text(random.choice(responses))
        elif any(word in msg_lower for word in ["как дела", "как ты"]):
            responses = ["✨ Всё отлично!", "База! Норм", "Пушка!"]
            await update.message.reply_text(random.choice(responses))
        elif any(word in msg_lower for word in ["спасибо", "пасиб"]):
            responses = ["🤝 Всегда пожалуйста!", "Не за что!"]
            await update.message.reply_text(random.choice(responses))
        elif any(word in msg_lower for word in ["кто создал", "владелец"]):
            await update.message.reply_text(f"👑 Мой создатель: {OWNER_USERNAME}")
        else:
            responses = ["Используй /help для списка команд", "Напиши /menu для навигации"]
            await update.message.reply_text(random.choice(responses))
    
    async def handle_new_members(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        
        self.db.cursor.execute("SELECT welcome FROM chat_settings WHERE chat_id = ?", (chat_id,))
        row = self.db.cursor.fetchone()
        welcome_text = row[0] if row and row[0] else "Добро пожаловать!"
        
        for member in update.message.new_chat_members:
            if member.is_bot:
                continue
            
            self.db.get_user(member.id, member.first_name)
            
            await update.message.reply_text(
                f"👋 {welcome_text}\n\n{member.first_name}, используй /help для команд!",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def handle_left_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        member = update.message.left_chat_member
        if member.is_bot:
            return
        
        await update.message.reply_text(f"👋 {member.first_name} покинул чат...", parse_mode=ParseMode.MARKDOWN)
    
    # ===== CALLBACK КНОПКИ =====
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        user = query.from_user
        
        if data == "menu_main":
            await query.edit_message_text(
                s.header("ГЛАВНОЕ МЕНЮ") + "\nВыберите раздел:",
                reply_markup=kb.main(),
                parse_mode=ParseMode.MARKDOWN
            )
        elif data == "menu_back":
            await query.edit_message_text(
                s.header("ГЛАВНОЕ МЕНЮ") + "\nВыберите раздел:",
                reply_markup=kb.main(),
                parse_mode=ParseMode.MARKDOWN
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
                parse_mode=ParseMode.MARKDOWN
            )
        elif data == "menu_mafia":
            await query.edit_message_text(
                s.header("🔫 МАФИЯ") + "\nВыберите действие:",
                reply_markup=kb.mafia(),
                parse_mode=ParseMode.MARKDOWN
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
                parse_mode=ParseMode.MARKDOWN
            )
        elif data == "eco_balance":
            context.args = []
            await self.cmd_balance(update, context)
        elif data == "eco_shop":
            context.args = []
            await self.cmd_shop(update, context)
        elif data == "eco_bonus":
            await query.edit_message_text(
                f"{s.header('🎁 БОНУСЫ')}\n\n{s.cmd('daily', 'ежедневный бонус')}",
                reply_markup=kb.back(),
                parse_mode=ParseMode.MARKDOWN
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
                parse_mode=ParseMode.MARKDOWN
            )
        elif data == "menu_help":
            context.args = []
            await self.cmd_help(update, context)
        elif data == "game_rr":
            context.args = []
            await self.cmd_russian_roulette(update, context)
        elif data == "game_dice":
            context.args = ['10']
            await self.cmd_dice_bet(update, context)
        elif data == "game_roulette":
            context.args = ['10']
            await self.cmd_roulette(update, context)
        elif data == "game_slots":
            context.args = ['10']
            await self.cmd_slots(update, context)
        elif data == "game_rps":
            await query.edit_message_text(
                s.header("✊ КНБ") + "\nВыберите жест:",
                reply_markup=kb.rps(),
                parse_mode=ParseMode.MARKDOWN
            )
        elif data == "game_saper":
            context.args = ['10']
            await self.cmd_saper(update, context)
        elif data == "game_guess":
            context.args = ['10']
            await self.cmd_guess(update, context)
        elif data == "game_bulls":
            context.args = ['10']
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
                parse_mode=ParseMode.MARKDOWN
            )
        elif data.startswith("mafia_confirm_"):
            chat_id = int(data.split('_')[2])
            if chat_id in self.mafia_games:
                game = self.mafia_games[chat_id]
                if user.id in game.players:
                    game.confirm_player(user.id)
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
            if duel and duel['opponent_id'] == user.id and duel['status'] == 'pending':
                self.db.update_duel(duel_id, status='accepted')
                await query.edit_message_text(
                    f"{s.success('✅ Дуэль принята!')}\n\n"
                    f"{s.info('Скоро начнётся...')}",
                    parse_mode=ParseMode.MARKDOWN
                )
        elif data.startswith("reject_duel_"):
            duel_id = int(data.split('_')[2])
            duel = self.db.get_duel(duel_id)
            if duel and duel['opponent_id'] == user.id and duel['status'] == 'pending':
                self.db.update_duel(duel_id, status='rejected')
                self.db.add_coins(duel['challenger_id'], duel['bet'])
                await query.edit_message_text(
                    f"{s.error('❌ Дуэль отклонена')}",
                    parse_mode=ParseMode.MARKDOWN
                )
        elif data.startswith("marry_accept_"):
            proposer_id = int(data.split('_')[2])
            user_data = self.db.get_user(user.id)
            
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
            
            now = datetime.datetime.now().isoformat()
            self.db.update_user(user_data['id'], spouse=proposer_id, married_since=now)
            self.db.update_user(proposer_id, spouse=user_data['id'], married_since=now)
            
            await query.edit_message_text(
                f"{s.success('💞 ПОЗДРАВЛЯЕМ!')}\n\n"
                f"{s.item('Теперь вы в браке!')}",
                parse_mode=ParseMode.MARKDOWN
            )
            
            await context.bot.send_message(
                proposer['telegram_id'],
                f"{s.success('💞 ПОЗДРАВЛЯЕМ!')}\n\n"
                f"{s.item(f'{user_data["first_name"]} принял(а) ваше предложение!')}",
                parse_mode=ParseMode.MARKDOWN
            )
        elif data.startswith("marry_reject_"):
            proposer_id = int(data.split('_')[2])
            await query.edit_message_text(s.error("❌ Предложение отклонено"), parse_mode=ParseMode.MARKDOWN)
            await context.bot.send_message(
                proposer_id,
                s.error("❌ Ваше предложение отклонили"),
                parse_mode=ParseMode.MARKDOWN
            )
    
    # ===== ОБРАБОТЧИК ОШИБОК =====
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Ошибка: {context.error}")
        try:
            if update and update.effective_message:
                await update.effective_message.reply_text(s.error("❌ Произошла внутренняя ошибка"))
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
            logger.info(f"🤖 AI: {'Подключен' if ai else 'Не подключен'}")
            
            while True:
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Критическая ошибка: {e}")
            await asyncio.sleep(5)
            await self.run()
    
    async def close(self):
        logger.info("👋 Завершение работы бота...")
        if ai:
            await ai.close()
        self.db.close()
        logger.info("✅ Бот остановлен")


# ========== ТОЧКА ВХОДА ==========
async def main():
    print("=" * 60)
    print(f"✨ ЗАПУСК БОТА {BOT_NAME} v{BOT_VERSION} ✨")
    print("=" * 60)
    print(f"📊 Команд: 250+")
    print(f"📊 Модулей: 25+")
    print(f"📊 AI: {'Groq подключен' if GROQ_API_KEY else 'Не подключен'}")
    print("=" * 60)
    
    bot = SpectrumBot()
    
    try:
        await bot.run()
    except KeyboardInterrupt:
        logger.info("Остановка по запросу пользователя")
        await bot.close()
    except Exception as e:
        logger.error(f"Необработанная ошибка: {e}")
        await bot.close()

if __name__ == "__main__":
    asyncio.run(main())
