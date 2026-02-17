#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
СПЕКТР БОТ - ОФИЦИАЛЬНАЯ ВЕРСИЯ
Telegram бот с красивым оформлением и Gemini AI
"""

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

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from telegram.error import TelegramError

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== КОНФИГУРАЦИЯ ==========
TELEGRAM_TOKEN = "8326390250:AAEpXRnhLLLi5zUeFC39nfkHDlxR5ZFQ_yQ"
GEMINI_API_KEY = "AIzaSyBPT4JUIevH0UiwXVY9eQjrY_pTPLeLbNE"
OWNER_ID = 1732658530
OWNER_USERNAME = "@NobuCraft"

# Настройки
SPAM_LIMIT = 5
SPAM_WINDOW = 3
SPAM_MUTE_TIME = 120

# Цены на привилегии
VIP_PRICE = 5000
PREMIUM_PRICE = 15000
VIP_DAYS = 30
PREMIUM_DAYS = 30

# ========== GEMINI AI ==========
class GeminiAI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        self.session = None
        self.contexts = defaultdict(list)
        print("🤖 Gemini AI инициализирован")

    async def get_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session

    async def get_response(self, user_id: int, message: str) -> str:
        try:
            session = await self.get_session()

            system_prompt = (
                "Ты — СПЕКТР, официальный бот-помощник. Отвечай вежливо, официально, "
                "но с легкой долей дружелюбия. Используй эмодзи умеренно. "
                "Помогай пользователям с командами, играми и настройками."
            )

            if user_id not in self.contexts:
                self.contexts[user_id] = [
                    {"role": "user", "parts": [{"text": system_prompt}]},
                    {"role": "model", "parts": [{"text": "Понял. Буду помогать официально и вежливо."}]}
                ]

            self.contexts[user_id].append({"role": "user", "parts": [{"text": message}]})

            if len(self.contexts[user_id]) > 10:
                self.contexts[user_id] = self.contexts[user_id][-10:]

            data = {
                "contents": self.contexts[user_id],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 200,
                    "topP": 0.95
                }
            }

            async with session.post(self.api_url, json=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    try:
                        response = result["candidates"][0]["content"]["parts"][0]["text"]
                        self.contexts[user_id].append({"role": "model", "parts": [{"text": response}]})
                        return response
                    except:
                        return self.get_fallback_response()
                else:
                    error_text = await resp.text()
                    print(f"Ошибка Gemini: {resp.status}")
                    return self.get_fallback_response()

        except Exception as e:
            print(f"Ошибка Gemini: {e}")
            return self.get_fallback_response()

    def get_fallback_response(self) -> str:
        responses = [
            "Обрабатываю запрос... Пожалуйста, повторите позже.",
            "Сейчас наблюдаются технические неполадки. Попробуйте через несколько минут.",
            "Не удалось обработать запрос. Пожалуйста, используйте команды меню.",
            "Сервис временно недоступен. Приношу извинения за неудобства."
        ]
        return random.choice(responses)

    async def close(self):
        if self.session:
            await self.session.close()

# ========== БАЗА ДАННЫХ ==========
class Database:
    def __init__(self, db_name="spectrum_bot.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
        print("✅ База данных инициализирована")

    def create_tables(self):
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
                warns_list TEXT DEFAULT '[]',
                mute_until TIMESTAMP,
                banned INTEGER DEFAULT 0,
                ban_reason TEXT,
                ban_date TIMESTAMP,
                ban_admin INTEGER,
                health INTEGER DEFAULT 100,
                armor INTEGER DEFAULT 0,
                damage INTEGER DEFAULT 10,
                boss_kills INTEGER DEFAULT 0,
                vip_until TIMESTAMP,
                premium_until TIMESTAMP,
                rps_wins INTEGER DEFAULT 0,
                rps_losses INTEGER DEFAULT 0,
                rps_draws INTEGER DEFAULT 0,
                casino_wins INTEGER DEFAULT 0,
                casino_losses INTEGER DEFAULT 0,
                gender TEXT DEFAULT 'не указан',
                nickname TEXT,
                city TEXT DEFAULT 'не указан',
                title TEXT DEFAULT '',
                motto TEXT DEFAULT 'Нет девиза',
                rep INTEGER DEFAULT 0,
                warns_count INTEGER DEFAULT 0,
                mutes_count INTEGER DEFAULT 0,
                bans_count INTEGER DEFAULT 0,
                last_seen TIMESTAMP,
                daily_streak INTEGER DEFAULT 0,
                last_daily TIMESTAMP,
                platform TEXT DEFAULT 'tg',
                platform_id TEXT,
                last_free_energy TIMESTAMP,
                last_weekly TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS stats (
                user_id INTEGER PRIMARY KEY,
                messages_count INTEGER DEFAULT 0,
                commands_used INTEGER DEFAULT 0,
                games_played INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')

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

        self.init_bosses()
        self.conn.commit()

    def init_bosses(self):
        self.cursor.execute("SELECT * FROM bosses")
        if not self.cursor.fetchone():
            bosses_data = [
                ("Ядовитый комар", 5, 500, 15, 250),
                ("Лесной тролль", 10, 1000, 25, 500),
                ("Огненный дракон", 15, 2000, 40, 1000),
                ("Ледяной великан", 20, 3500, 60, 2000),
                ("Король демонов", 25, 5000, 85, 3500),
                ("Бог разрушения", 30, 10000, 150, 5000)
            ]
            for name, level, health, damage, reward in bosses_data:
                self.cursor.execute('''
                    INSERT INTO bosses (boss_name, boss_level, boss_health, boss_max_health, boss_damage, boss_reward)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (name, level, health, health, damage, reward))
            print("✅ Боссы инициализированы")

    def get_or_create_user(self, platform: str, platform_id: str, first_name: str = "Player") -> Dict:
        self.cursor.execute(
            "SELECT * FROM users WHERE platform = ? AND platform_id = ?",
            (platform, platform_id)
        )
        user = self.cursor.fetchone()

        if not user:
            role = 'owner' if int(platform_id) == OWNER_ID else 'user'
            self.cursor.execute('''
                INSERT INTO users (platform, platform_id, first_name, role, last_seen) 
                VALUES (?, ?, ?, ?, ?)
            ''', (platform, platform_id, first_name, role, datetime.datetime.now()))

            user_id = self.cursor.lastrowid

            self.cursor.execute('''
                INSERT INTO stats (user_id) VALUES (?)
            ''', (user_id,))

            self.conn.commit()
            return self.get_user_by_id(user_id)

        self.cursor.execute(
            "UPDATE users SET last_seen = ? WHERE platform = ? AND platform_id = ?",
            (datetime.datetime.now(), platform, platform_id)
        )
        self.conn.commit()

        return self.get_user_by_id(user[0])

    def get_user_by_id(self, user_id: int) -> Dict:
        self.cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = self.cursor.fetchone()
        if not user:
            return {}

        columns = [description[0] for description in self.cursor.description]
        return dict(zip(columns, user))

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        self.cursor.execute(
            "SELECT user_id FROM users WHERE username = ?",
            (username.replace('@', ''),)
        )
        result = self.cursor.fetchone()
        if result:
            return self.get_user_by_id(result[0])
        return None

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

    def add_stat(self, user_id: int, stat: str, value: int = 1):
        self.cursor.execute(f"UPDATE stats SET {stat} = {stat} + ? WHERE user_id = ?", (value, user_id))
        self.conn.commit()

    def damage(self, user_id: int, amount: int):
        self.cursor.execute("UPDATE users SET health = health - ? WHERE user_id = ?", (amount, user_id))
        self.conn.commit()

    def heal(self, user_id: int, amount: int):
        current_health = self.get_user_by_id(user_id).get('health', 100)
        new_health = min(100, current_health + amount)
        self.cursor.execute("UPDATE users SET health = ? WHERE user_id = ?", (new_health, user_id))
        self.conn.commit()

    def add_warn(self, user_id: int, admin_id: int, reason: str = "Нарушение") -> Dict:
        user_data = self.get_user_by_id(user_id)
        warns_list = json.loads(user_data.get('warns_list', '[]'))

        warn_data = {
            'id': len(warns_list) + 1,
            'admin_id': admin_id,
            'reason': reason,
            'date': datetime.datetime.now().isoformat()
        }

        warns_list.append(warn_data)

        self.cursor.execute(
            "UPDATE users SET warns = warns + 1, warns_count = warns_count + 1, warns_list = ? WHERE user_id = ?",
            (json.dumps(warns_list), user_id)
        )
        self.conn.commit()

        return {
            'warn_id': warn_data['id'],
            'warns_count': len(warns_list),
            'warn_data': warn_data
        }

    def get_warns(self, user_id: int) -> List[Dict]:
        user_data = self.get_user_by_id(user_id)
        return json.loads(user_data.get('warns_list', '[]'))

    def remove_last_warn(self, user_id: int) -> Optional[Dict]:
        user_data = self.get_user_by_id(user_id)
        warns_list = json.loads(user_data.get('warns_list', '[]'))

        if not warns_list:
            return None

        removed = warns_list.pop()

        self.cursor.execute(
            "UPDATE users SET warns = ?, warns_list = ? WHERE user_id = ?",
            (len(warns_list), json.dumps(warns_list), user_id)
        )
        self.conn.commit()

        return removed

    def mute_user(self, user_id: int, minutes: int, admin_id: int = None, reason: str = "Нарушение"):
        mute_until = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
        self.cursor.execute(
            "UPDATE users SET mute_until = ?, mutes_count = mutes_count + 1 WHERE user_id = ?",
            (mute_until, user_id)
        )
        self.conn.commit()
        return mute_until

    def is_muted(self, user_id: int) -> bool:
        self.cursor.execute("SELECT mute_until FROM users WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()
        if result and result[0]:
            mute_until = datetime.datetime.fromisoformat(result[0])
            return datetime.datetime.now() < mute_until
        return False

    def unmute_user(self, user_id: int):
        self.cursor.execute("UPDATE users SET mute_until = NULL WHERE user_id = ?", (user_id,))
        self.conn.commit()

    def get_muted_users(self) -> List[Tuple]:
        self.cursor.execute(
            "SELECT user_id, first_name, mute_until FROM users WHERE mute_until IS NOT NULL AND mute_until > ? ORDER BY mute_until",
            (datetime.datetime.now(),)
        )
        return self.cursor.fetchall()

    def ban_user(self, user_id: int, admin_id: int, reason: str = "Нарушение", period: str = "навсегда"):
        self.cursor.execute(
            "UPDATE users SET banned = 1, bans_count = bans_count + 1, ban_reason = ?, ban_date = ?, ban_admin = ? WHERE user_id = ?",
            (reason, datetime.datetime.now(), admin_id, user_id)
        )
        self.conn.commit()

    def unban_user(self, user_id: int):
        self.cursor.execute(
            "UPDATE users SET banned = 0, warns = 0, ban_reason = NULL, ban_date = NULL, ban_admin = NULL WHERE user_id = ?",
            (user_id,)
        )
        self.conn.commit()

    def is_banned(self, user_id: int) -> bool:
        self.cursor.execute("SELECT banned FROM users WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()
        return result and result[0] == 1

    def get_banlist(self, page: int = 1, limit: int = 10) -> Tuple[List, int]:
        offset = (page - 1) * limit
        self.cursor.execute("SELECT COUNT(*) FROM users WHERE banned = 1")
        total = self.cursor.fetchone()[0]

        self.cursor.execute('''
            SELECT user_id, first_name, username, ban_reason, ban_date, ban_admin
            FROM users WHERE banned = 1 ORDER BY ban_date DESC LIMIT ? OFFSET ?
        ''', (limit, offset))

        bans = []
        for row in self.cursor.fetchall():
            admin_data = self.get_user_by_id(row[5]) if row[5] else None
            bans.append({
                'user_id': row[0],
                'name': row[1],
                'username': row[2],
                'reason': row[3],
                'date': row[4],
                'admin': admin_data.get('first_name') if admin_data else 'Система'
            })

        return bans, total

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

        self.cursor.execute(
            "UPDATE users SET daily_streak = ?, last_daily = ? WHERE user_id = ?",
            (streak, datetime.datetime.now(), user_id)
        )
        self.conn.commit()
        return streak

    def close(self):
        self.conn.close()


# Инициализация БД
db = Database()


# ========== КЛАСС ДЛЯ ФОРМАТИРОВАНИЯ В СТИЛЕ IRIS ==========
class IrisFormatter:
    @staticmethod
    def header(title: str, emoji: str = "📋") -> str:
        return (
            f"╔══════════════════════════════╗\n"
            f"║    {emoji} {title}    ║\n"
            f"╚══════════════════════════════╝\n"
        )

    @staticmethod
    def section(title: str, emoji: str = "▫️") -> str:
        return f"\n{emoji} **{title}**\n" + "━" * 25 + "\n"

    @staticmethod
    def command(name: str, desc: str, usage: str = "", emoji: str = "・") -> str:
        if usage:
            return f"{emoji} `/{name} {usage}` — {desc}"
        return f"{emoji} `/{name}` — {desc}"

    @staticmethod
    def param(name: str, desc: str) -> str:
        return f"└ {name} — {desc}"

    @staticmethod
    def example(text: str) -> str:
        return f"└ Пример: `{text}`"

    @staticmethod
    def success(text: str) -> str:
        return f"✅ {text}"

    @staticmethod
    def error(text: str) -> str:
        return f"❌ {text}"

    @staticmethod
    def warning(text: str) -> str:
        return f"⚠️ {text}"

    @staticmethod
    def info(text: str) -> str:
        return f"ℹ️ {text}"

    @staticmethod
    def list_item(text: str, emoji: str = "•") -> str:
        return f"{emoji} {text}"

    @staticmethod
    def progress(current: int, total: int, length: int = 10) -> str:
        filled = int((current / total) * length)
        bar = "█" * filled + "░" * (length - filled)
        return f"`{bar}` {current}/{total}"

    @staticmethod
    def stat(name: str, value: str, emoji: str = "📊") -> str:
        return f"{emoji} **{name}:** {value}"

    @staticmethod
    def user_link(user_id: int, name: str) -> str:
        return f"[{name}](tg://user?id={user_id})"

    @staticmethod
    def bold(text: str) -> str:
        return f"**{text}**"

    @staticmethod
    def code(text: str) -> str:
        return f"`{text}`"


# ========== КЛАСС ДЛЯ КРАСИВЫХ КНОПОК ==========
class IrisKeyboard:
    @staticmethod
    def main_menu():
        keyboard = [
            [
                InlineKeyboardButton("👤 ПРОФИЛЬ", callback_data="menu_profile"),
                InlineKeyboardButton("📊 СТАТИСТИКА", callback_data="menu_stats")
            ],
            [
                InlineKeyboardButton("👾 БОССЫ", callback_data="menu_bosses"),
                InlineKeyboardButton("🎰 КАЗИНО", callback_data="menu_casino")
            ],
            [
                InlineKeyboardButton("🛍 МАГАЗИН", callback_data="menu_shop"),
                InlineKeyboardButton("💎 ПРИВИЛЕГИИ", callback_data="menu_donate")
            ],
            [
                InlineKeyboardButton("⚙️ МОДЕРАЦИЯ", callback_data="menu_moderation"),
                InlineKeyboardButton("📚 ПОМОЩЬ", callback_data="menu_help")
            ],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def back_button(callback: str = "menu_back"):
        keyboard = [[InlineKeyboardButton("🔙 НАЗАД", callback_data=callback)]]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def confirm_cancel():
        keyboard = [
            [
                InlineKeyboardButton("✅ ПОДТВЕРДИТЬ", callback_data="confirm"),
                InlineKeyboardButton("❌ ОТМЕНА", callback_data="cancel")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def pagination(current: int, total: int, prefix: str):
        buttons = []
        row = []

        if current > 1:
            row.append(InlineKeyboardButton("◀️", callback_data=f"{prefix}_page_{current-1}"))

        row.append(InlineKeyboardButton(f"📄 {current}/{total}", callback_data="noop"))

        if current < total:
            row.append(InlineKeyboardButton("▶️", callback_data=f"{prefix}_page_{current+1}"))

        buttons.append(row)
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def rps_game():
        keyboard = [
            [
                InlineKeyboardButton("🪨 КАМЕНЬ", callback_data="rps_rock"),
                InlineKeyboardButton("✂️ НОЖНИЦЫ", callback_data="rps_scissors"),
                InlineKeyboardButton("📄 БУМАГА", callback_data="rps_paper")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)


# ========== ОСНОВНОЙ КЛАСС БОТА ==========
class GameBot:
    def __init__(self):
        self.db = db
        self.ai = GeminiAI(GEMINI_API_KEY)
        self.spam_tracker = defaultdict(list)
        self.application = Application.builder().token(TELEGRAM_TOKEN).build()
        self.f = IrisFormatter()
        self.setup_handlers()
        print("✅ Бот «СПЕКТР» инициализирован")

    def setup_handlers(self):
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        self.application.add_handler(CommandHandler("menu", self.cmd_menu))

        self.application.add_handler(CommandHandler("profile", self.cmd_profile))
        self.application.add_handler(CommandHandler("edit_nick", self.cmd_edit_nick))
        self.application.add_handler(CommandHandler("edit_title", self.cmd_edit_title))
        self.application.add_handler(CommandHandler("edit_motto", self.cmd_edit_motto))
        self.application.add_handler(CommandHandler("edit_gender", self.cmd_edit_gender))

        self.application.add_handler(CommandHandler("mystats", self.cmd_my_stats))
        self.application.add_handler(CommandHandler("top", self.cmd_top))
        self.application.add_handler(CommandHandler("daily", self.cmd_daily))
        self.application.add_handler(CommandHandler("weekly", self.cmd_weekly))
        self.application.add_handler(CommandHandler("streak", self.cmd_streak))

        self.application.add_handler(CommandHandler("bosses", self.cmd_boss_list))
        self.application.add_handler(CommandHandler("bossfight", self.cmd_boss_fight))
        self.application.add_handler(CommandHandler("bossinfo", self.cmd_boss_info))
        self.application.add_handler(CommandHandler("regen", self.cmd_regen))

        self.application.add_handler(CommandHandler("casino", self.cmd_casino))
        self.application.add_handler(CommandHandler("roulette", self.cmd_roulette))
        self.application.add_handler(CommandHandler("dice", self.cmd_dice))
        self.application.add_handler(CommandHandler("rps", self.cmd_rps))

        self.application.add_handler(CommandHandler("shop", self.cmd_shop))
        self.application.add_handler(CommandHandler("buy", self.cmd_buy))
        self.application.add_handler(CommandHandler("pay", self.cmd_pay))
        self.application.add_handler(CommandHandler("donate", self.cmd_donate))
        self.application.add_handler(CommandHandler("vip", self.cmd_vip))
        self.application.add_handler(CommandHandler("premium", self.cmd_premium))

        self.application.add_handler(CommandHandler("warn", self.cmd_warn))
        self.application.add_handler(CommandHandler("warns", self.cmd_warns))
        self.application.add_handler(CommandHandler("unwarn", self.cmd_unwarn))
        self.application.add_handler(CommandHandler("mute", self.cmd_mute))
        self.application.add_handler(CommandHandler("unmute", self.cmd_unmute))
        self.application.add_handler(CommandHandler("mutelist", self.cmd_mutelist))
        self.application.add_handler(CommandHandler("ban", self.cmd_ban))
        self.application.add_handler(CommandHandler("unban", self.cmd_unban))
        self.application.add_handler(CommandHandler("banlist", self.cmd_banlist))
        self.application.add_handler(CommandHandler("kick", self.cmd_kick))

        self.application.add_handler(CommandHandler("weather", self.cmd_weather))
        self.application.add_handler(CommandHandler("news", self.cmd_news))
        self.application.add_handler(CommandHandler("quote", self.cmd_quote))
        self.application.add_handler(CommandHandler("players", self.cmd_players))
        self.application.add_handler(CommandHandler("engfree", self.cmd_eng_free))

        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, self.handle_new_members))
        self.application.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, self.handle_left_member))

        print("✅ Все обработчики зарегистрированы")

    def get_role_emoji(self, role: str) -> str:
        emojis = {
            'owner': '👑',
            'admin': '⚜️',
            'moderator': '🛡️',
            'premium': '💎',
            'vip': '🌟',
            'user': '👤'
        }
        return emojis.get(role, '👤')

    def has_permission(self, user_data: Dict, required_role: str) -> bool:
        role_hierarchy = ['user', 'vip', 'premium', 'moderator', 'admin', 'owner']
        user_role = user_data.get('role', 'user')
        if user_role not in role_hierarchy:
            return False
        user_level = role_hierarchy.index(user_role)
        required_level = role_hierarchy.index(required_role)
        return user_level >= required_level

    async def check_spam(self, update: Update) -> bool:
        user_id = update.effective_user.id
        if self.has_permission(self.db.get_user_by_id(user_id), 'premium'):
            return False

        current_time = time.time()
        self.spam_tracker[user_id] = [t for t in self.spam_tracker[user_id] if current_time - t < SPAM_WINDOW]
        self.spam_tracker[user_id].append(current_time)

        if len(self.spam_tracker[user_id]) > SPAM_LIMIT:
            self.db.mute_user(user_id, SPAM_MUTE_TIME, 0, "Автоматический спам")
            await update.message.reply_text(
                self.f.error(f"Спам-фильтр. Вы замучены на {SPAM_MUTE_TIME} минут."),
                parse_mode='Markdown'
            )
            self.spam_tracker[user_id] = []
            return True
        return False

    # ========== ОСНОВНЫЕ КОМАНДЫ ==========

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_or_create_user("tg", str(user.id), user.first_name)

        text = (f"{self.f.header('ДОБРО ПОЖАЛОВАТЬ', '⚔️')}\n\n"
                f"🌟 **Привет, {user.first_name}!**\n"
                f"Я — **«СПЕКТР»**, твой игровой помощник\n\n"
                f"{self.f.section('ТВОЙ ПРОФИЛЬ', '👤')}\n"
                f"{self.f.list_item('Роль: ' + self.get_role_emoji(user_data.get('role', 'user')) + ' ' + user_data.get('role', 'user'))}\n"
                f"{self.f.list_item('Монеты: ' + str(user_data.get('coins', 1000)) + ' 💰')}\n"
                f"{self.f.list_item('Уровень: ' + str(user_data.get('level', 1)))}\n"
                f"{self.f.list_item('Энергия: ' + str(user_data.get('energy', 100)) + ' ⚡')}\n\n"
                f"{self.f.section('БЫСТРЫЙ СТАРТ', '🚀')}\n"
                f"{self.f.command('profile', 'твой профиль')}\n"
                f"{self.f.command('bosses', 'битва с боссами')}\n"
                f"{self.f.command('daily', 'ежедневный бонус')}\n"
                f"{self.f.command('help', 'все команды')}\n\n"
                f"👑 **Владелец:** {OWNER_USERNAME}")

        await update.message.reply_text(
            text,
            reply_markup=IrisKeyboard.main_menu(),
            parse_mode='Markdown'
        )
        self.db.add_stat(user.id, "commands_used")

    async def cmd_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            f"{self.f.header('ГЛАВНОЕ МЕНЮ', '🎮')}\n\nВыбери раздел:",
            reply_markup=IrisKeyboard.main_menu(),
            parse_mode='Markdown'
        )

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (f"{self.f.header('СПРАВКА', '📚')}\n\n"
                f"{self.f.section('ОСНОВНЫЕ КОМАНДЫ', '🔹')}\n"
                f"{self.f.command('start', 'начать работу')}\n"
                f"{self.f.command('menu', 'главное меню')}\n"
                f"{self.f.command('profile', 'твой профиль')}\n"
                f"{self.f.command('mystats', 'твоя статистика')}\n\n"
                f"{self.f.section('ИГРЫ', '🎮')}\n"
                f"{self.f.command('bosses', 'битва с боссами')}\n"
                f"{self.f.command('casino', 'казино')}\n"
                f"{self.f.command('rps', 'камень-ножницы-бумага')}\n\n"
                f"{self.f.section('ЭКОНОМИКА', '💰')}\n"
                f"{self.f.command('daily', 'ежедневный бонус')}\n"
                f"{self.f.command('weekly', 'недельный бонус')}\n"
                f"{self.f.command('shop', 'магазин')}\n"
                f"{self.f.command('pay @ник сумма', 'перевести монеты')}\n"
                f"{self.f.command('donate', 'привилегии')}\n\n"
                f"{self.f.section('МОДЕРАЦИЯ', '⚙️')}\n"
                f"{self.f.command('warn @ник [причина]', 'предупреждение')}\n"
                f"{self.f.command('mute @ник минут [причина]', 'заглушить')}\n"
                f"{self.f.command('ban @ник [причина]', 'заблокировать')}\n"
                f"{self.f.command('banlist', 'список забаненных')}\n\n"
                f"👑 **Владелец:** {OWNER_USERNAME}")

        await update.message.reply_text(
            text,
            reply_markup=IrisKeyboard.back_button(),
            parse_mode='Markdown'
        )

    # ========== ПРОФИЛЬ ==========

    async def cmd_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user_by_id(user.id)

        current_exp = user_data.get('exp', 0)
        current_level = user_data.get('level', 1)
        exp_needed = current_level * 100
        exp_progress = self.f.progress(current_exp, exp_needed, 15)

        vip_status = "✅ VIP" if self.db.is_vip(user.id) else "❌ Нет"
        premium_status = "✅ PREMIUM" if self.db.is_premium(user.id) else "❌ Нет"

        warns = user_data.get('warns', 0)
        warns_display = "🔴" * warns + "⚪" * (3 - warns)

        text = (f"{self.f.header('ПРОФИЛЬ ИГРОКА', '👤')}\n\n"
                f"**{user_data.get('nickname') or user.first_name}** "
                f"{user_data.get('title', '')}\n"
                f"_{user_data.get('motto', 'Нет девиза')}_\n\n"
                f"{self.f.section('ХАРАКТЕРИСТИКИ', '📊')}\n"
                f"{self.f.stat('Уровень', str(current_level))}\n"
                f"{self.f.stat('Опыт', exp_progress)}\n"
                f"{self.f.stat('Монеты', str(user_data.get('coins', 0)) + ' 💰')}\n"
                f"{self.f.stat('Алмазы', str(user_data.get('diamonds', 0)) + ' 💎')}\n"
                f"{self.f.stat('Энергия', str(user_data.get('energy', 100)) + ' ⚡')}\n\n"
                f"{self.f.section('БОЕВЫЕ', '⚔️')}\n"
                f"{self.f.stat('❤️ Здоровье', str(user_data.get('health', 100)) + '/100')}\n"
                f"{self.f.stat('⚔️ Урон', str(user_data.get('damage', 10)))}\n"
                f"{self.f.stat('🛡 Броня', str(user_data.get('armor', 0)))}\n"
                f"{self.f.stat('👾 Боссов убито', str(user_data.get('boss_kills', 0)))}\n\n"
                f"{self.f.section('СТАТУС', '💎')}\n"
                f"{self.f.list_item(vip_status)}\n"
                f"{self.f.list_item(premium_status)}\n"
                f"{self.f.list_item('Предупреждения: ' + warns_display)}\n"
                f"{self.f.list_item('Репутация: ' + str(user_data.get('rep', 0)) + ' ⭐')}\n\n"
                f"{self.f.section('О СЕБЕ', 'ℹ️')}\n"
                f"{self.f.list_item('Пол: ' + user_data.get('gender', 'не указан'))}\n"
                f"{self.f.list_item('Город: ' + user_data.get('city', 'не указан'))}\n"
                f"{self.f.list_item('ID: ' + self.f.code(str(user.id)))}")

        keyboard = [
            [
                InlineKeyboardButton("✏️ Ник", callback_data="edit_nick"),
                InlineKeyboardButton("🏷 Титул", callback_data="edit_title")
            ],
            [
                InlineKeyboardButton("📝 Девиз", callback_data="edit_motto"),
                InlineKeyboardButton("👤 Пол", callback_data="edit_gender")
            ],
            [InlineKeyboardButton("🔙 НАЗАД", callback_data="menu_back")]
        ]

        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def cmd_edit_nick(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(
                f"{self.f.header('РЕДАКТИРОВАНИЕ НИКА', '✏️')}\n\n"
                f"{self.f.command('edit_nick [ник]', 'установить ник')}\n"
                f"{self.f.example('edit_nick Spectr')}",
                parse_mode='Markdown'
            )
            return

        nick = " ".join(context.args)
        if len(nick) > 30:
            await update.message.reply_text(self.f.error("Ник слишком длинный (макс 30 символов)"))
            return

        user_id = update.effective_user.id
        self.db.cursor.execute(
            "UPDATE users SET nickname = ? WHERE user_id = ?",
            (nick, user_id)
        )
        self.db.conn.commit()

        await update.message.reply_text(self.f.success(f"Ник установлен: {nick}"))

    async def cmd_edit_title(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(
                f"{self.f.header('РЕДАКТИРОВАНИЕ ТИТУЛА', '🏷')}\n\n"
                f"{self.f.command('edit_title [титул]', 'установить титул')}\n"
                f"{self.f.example('edit_title Легенда')}",
                parse_mode='Markdown'
            )
            return

        title = " ".join(context.args)
        if len(title) > 30:
            await update.message.reply_text(self.f.error("Титул слишком длинный (макс 30 символов)"))
            return

        user_id = update.effective_user.id
        self.db.cursor.execute(
            "UPDATE users SET title = ? WHERE user_id = ?",
            (title, user_id)
        )
        self.db.conn.commit()

        await update.message.reply_text(self.f.success(f"Титул установлен: {title}"))

    async def cmd_edit_motto(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(
                f"{self.f.header('РЕДАКТИРОВАНИЕ ДЕВИЗА', '📝')}\n\n"
                f"{self.f.command('edit_motto [девиз]', 'установить девиз')}\n"
                f"{self.f.example('edit_motto Carpe diem')}",
                parse_mode='Markdown'
            )
            return

        motto = " ".join(context.args)
        if len(motto) > 100:
            await update.message.reply_text(self.f.error("Девиз слишком длинный (макс 100 символов)"))
            return

        user_id = update.effective_user.id
        self.db.cursor.execute(
            "UPDATE users SET motto = ? WHERE user_id = ?",
            (motto, user_id)
        )
        self.db.conn.commit()

        await update.message.reply_text(self.f.success(f"Девиз установлен: {motto}"))

    async def cmd_edit_gender(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args or context.args[0].lower() not in ['м', 'ж', 'др']:
            await update.message.reply_text(
                f"{self.f.header('РЕДАКТИРОВАНИЕ ПОЛА', '👤')}\n\n"
                f"{self.f.command('edit_gender [м|ж|др]', 'установить пол')}\n"
                f"{self.f.example('edit_gender м')}",
                parse_mode='Markdown'
            )
            return

        gender = "мужской" if context.args[0].lower() == 'м' else "женский" if context.args[0].lower() == 'ж' else "другой"
        user_id = update.effective_user.id
        self.db.cursor.execute(
            "UPDATE users SET gender = ? WHERE user_id = ?",
            (gender, user_id)
        )
        self.db.conn.commit()

        await update.message.reply_text(self.f.success(f"Пол установлен: {gender}"))

    # ========== СТАТИСТИКА ==========

    async def cmd_my_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user_by_id(user.id)

        self.db.cursor.execute("SELECT * FROM stats WHERE user_id = ?", (user.id,))
        stats = self.db.cursor.fetchone()

        text = (f"{self.f.header('ТВОЯ СТАТИСТИКА', '📊')}\n\n"
                f"{self.f.stat('Сообщений', str(stats[1] if stats else 0))}\n"
                f"{self.f.stat('Команд', str(stats[2] if stats else 0))}\n"
                f"{self.f.stat('Игр сыграно', str(stats[3] if stats else 0))}\n"
                f"{self.f.stat('РПС побед', str(user_data.get('rps_wins', 0)))}\n"
                f"{self.f.stat('Казино побед', str(user_data.get('casino_wins', 0)))}")

        await update.message.reply_text(text, parse_mode='Markdown')

    async def cmd_top(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        top_coins = self.db.get_top("coins", 10)
        top_level = self.db.get_top("level", 10)
        top_boss = self.db.get_top("boss_kills", 10)

        text = f"{self.f.header('ТОП ИГРОКОВ', '🏆')}\n\n"
        text += f"{self.f.section('ПО МОНЕТАМ', '💰')}\n"
        for i, (name, value) in enumerate(top_coins, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
            text += f"{medal} **{i}.** {name} — {value} 💰\n"

        text += f"\n{self.f.section('ПО УРОВНЮ', '📊')}\n"
        for i, (name, value) in enumerate(top_level, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
            text += f"{medal} **{i}.** {name} — {value} ур.\n"

        text += f"\n{self.f.section('ПО УБИЙСТВУ БОССОВ', '👾')}\n"
        for i, (name, value) in enumerate(top_boss, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
            text += f"{medal} **{i}.** {name} — {value} боссов\n"

        await update.message.reply_text(
            text,
            reply_markup=IrisKeyboard.back_button(),
            parse_mode='Markdown'
        )

    async def cmd_daily(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)

        today = datetime.datetime.now().date()
        if user_data.get('last_daily'):
            last_date = datetime.datetime.fromisoformat(user_data['last_daily']).date()
            if last_date == today:
                await update.message.reply_text(self.f.error("Вы уже получали ежедневный бонус сегодня"))
                return

        streak = self.db.add_daily_streak(user_id)

        coins = random.randint(100, 300)
        exp = random.randint(20, 60)

        coins = int(coins * (1 + min(streak, 30) * 0.05))
        exp = int(exp * (1 + min(streak, 30) * 0.05))

        if self.db.is_vip(user_id):
            coins = int(coins * 1.5)
            exp = int(exp * 1.5)
        if self.db.is_premium(user_id):
            coins = int(coins * 2)
            exp = int(exp * 2)

        self.db.add_coins(user_id, coins)
        self.db.add_exp(user_id, exp)

        text = (f"{self.f.header('ЕЖЕДНЕВНЫЙ БОНУС', '🎁')}\n\n"
                f"{self.f.list_item('Стрик: ' + str(streak) + ' дней 🔥')}\n"
                f"{self.f.list_item('Монеты: +' + str(coins) + ' 💰')}\n"
                f"{self.f.list_item('Опыт: +' + str(exp) + ' ✨')}\n\n"
                f"{self.f.info('Заходите завтра за новым бонусом!')}")

        await update.message.reply_text(text, parse_mode='Markdown')

    async def cmd_weekly(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)

        last_weekly = user_data.get('last_weekly')
        if last_weekly:
            last = datetime.datetime.fromisoformat(last_weekly)
            if (datetime.datetime.now() - last).days < 7:
                await update.message.reply_text(self.f.error("Недельный бонус можно получать раз в 7 дней"))
                return

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

        self.db.cursor.execute(
            "UPDATE users SET last_weekly = ? WHERE user_id = ?",
            (datetime.datetime.now(), user_id)
        )
        self.db.conn.commit()

        text = (f"{self.f.header('НЕДЕЛЬНЫЙ БОНУС', '📅')}\n\n"
                f"{self.f.list_item('Монеты: +' + str(coins) + ' 💰')}\n"
                f"{self.f.list_item('Алмазы: +' + str(diamonds) + ' 💎')}\n\n"
                f"{self.f.info('Возвращайтесь через неделю!')}")

        await update.message.reply_text(text, parse_mode='Markdown')

    async def cmd_streak(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)

        streak = user_data.get('daily_streak', 0)
        last_daily = user_data.get('last_daily', 'никогда')

        if last_daily != 'никогда':
            last = datetime.datetime.fromisoformat(last_daily)
            days_missed = (datetime.datetime.now() - last).days
        else:
            days_missed = 0

        text = (f"{self.f.header('ТЕКУЩИЙ СТРИК', '🔥')}\n\n"
                f"{self.f.list_item('Дней подряд: ' + str(streak))}\n"
                f"{self.f.list_item('Последний вход: ' + (last_daily[:10] if last_daily != 'никогда' else 'никогда'))}\n"
                f"{self.f.list_item('Пропущено дней: ' + str(days_missed))}")

        await update.message.reply_text(text, parse_mode='Markdown')

    # ========== БОССЫ ==========

    async def cmd_boss_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)
        bosses = self.db.get_bosses(alive_only=True)

        if not bosses:
            self.db.respawn_bosses()
            bosses = self.db.get_bosses(alive_only=True)

        text = f"{self.f.header('АРЕНА БОССОВ', '👾')}\n\n"

        if bosses:
            boss = bosses[0]
            health_bar = self.f.progress(boss[3], boss[4], 20)

            text += (f"**ТЕКУЩИЙ БОСС**\n"
                     f"└ {boss[1]} (ур. {boss[2]})\n"
                     f"└ ❤️ Здоровье: {health_bar}\n"
                     f"└ ⚔️ Урон: {boss[5]}\n"
                     f"└ Награда: {boss[6]} 💰\n\n")

            if len(bosses) > 1:
                text += f"{self.f.section('ОЧЕРЕДЬ', '📋')}\n"
                for i, b in enumerate(bosses[1:], 2):
                    text += f"{i}. {b[1]} — ❤️ {b[3]}/{b[4]}\n"

        text += (f"\n{self.f.section('ТВОИ ПОКАЗАТЕЛИ', '⚔️')}\n"
                 f"{self.f.stat('❤️ Здоровье', str(user_data.get('health', 100)) + '/100')}\n"
                 f"{self.f.stat('⚡ Энергия', str(user_data.get('energy', 100)) + '/100')}\n"
                 f"{self.f.stat('⚔️ Урон', str(user_data.get('damage', 10)))}\n"
                 f"{self.f.stat('👾 Убито боссов', str(user_data.get('boss_kills', 0)))}\n\n"
                 f"{self.f.section('КОМАНДЫ', '⌨️')}\n"
                 f"{self.f.command('bossfight [ID]', 'атаковать босса', '1')}\n"
                 f"{self.f.command('regen', 'восстановить ❤️ и ⚡')}\n"
                 f"{self.f.command('bossinfo [ID]', 'информация о боссе', '1')}")

        keyboard = []
        for i, boss in enumerate(bosses[:3], 1):
            keyboard.append([
                InlineKeyboardButton(
                    f"⚔️ Атаковать {boss[1][:15]}",
                    callback_data=f"boss_fight_{boss[0]}"
                )
            ])
        keyboard.append([InlineKeyboardButton("🔙 НАЗАД", callback_data="menu_back")])

        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def cmd_boss_fight(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user_by_id(user.id)

        if not context.args:
            await update.message.reply_text(self.f.error("Укажите ID босса: /bossfight 1"))
            return

        try:
            boss_id = int(context.args[0])
        except:
            await update.message.reply_text(self.f.error("Некорректный ID босса"))
            return

        boss = self.db.get_boss(boss_id)
        if not boss or not boss[8]:
            await update.message.reply_text(self.f.error("Босс не найден или уже повержен"))
            return

        if user_data['energy'] < 10:
            await update.message.reply_text(self.f.error("Недостаточно энергии. Используйте /regen"))
            return

        self.db.add_energy(user.id, -10)

        damage_bonus = 1.0
        if self.db.is_vip(user.id):
            damage_bonus += 0.2
        if self.db.is_premium(user.id):
            damage_bonus += 0.3

        player_damage = int(user_data['damage'] * damage_bonus) + random.randint(-5, 5)
        boss_damage = boss[5] + random.randint(-5, 5)
        player_taken = max(1, boss_damage - user_data['armor'] // 2)

        boss_killed = self.db.damage_boss(boss_id, player_damage)
        self.db.damage(user.id, player_taken)

        text = f"{self.f.header('БИТВА С БОССОМ', '⚔️')}\n\n"
        text += f"{self.f.list_item('Ваш урон: ' + str(player_damage))}\n"
        text += f"{self.f.list_item('Урон босса: ' + str(player_taken))}\n\n"

        if boss_killed:
            reward = boss[6] * (1 + user_data['level'] // 10)
            if self.db.is_vip(user.id):
                reward = int(reward * 1.5)
            if self.db.is_premium(user.id):
                reward = int(reward * 2)

            self.db.add_coins(user.id, reward)
            self.db.add_boss_kill(user.id)
            self.db.add_exp(user.id, boss[2] * 10)

            text += f"{self.f.success('ПОБЕДА!')}\n"
            text += f"{self.f.list_item('💰 Награда: ' + str(reward) + ' 💰')}\n"
            text += f"{self.f.list_item('✨ Опыт: +' + str(boss[2] * 10))}\n\n"
        else:
            boss_info = self.db.get_boss(boss_id)
            text += f"{self.f.warning('Босс еще жив!')}\n"
            text += f"❤️ Осталось: {boss_info[3]} здоровья\n\n"

        if user_data['health'] <= player_taken:
            self.db.heal(user.id, 50)
            text += self.f.info("Вы погибли и были воскрешены с 50❤️")

        await update.message.reply_text(text, parse_mode='Markdown')

    async def cmd_boss_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(self.f.error("Укажите ID босса: /bossinfo 1"))
            return

        try:
            boss_id = int(context.args[0])
        except:
            await update.message.reply_text(self.f.error("Некорректный ID босса"))
            return

        boss = self.db.get_boss(boss_id)
        if not boss:
            await update.message.reply_text(self.f.error("Босс не найден"))
            return

        status = "ЖИВ" if boss[8] else "ПОВЕРЖЕН"
        health_bar = self.f.progress(boss[3], boss[4], 20)

        text = (f"{self.f.header(f'БОСС: {boss[1]}', '👾')}\n\n"
                f"{self.f.stat('Уровень', str(boss[2]))}\n"
                f"{self.f.stat('❤️ Здоровье', health_bar)}\n"
                f"{self.f.stat('⚔️ Урон', str(boss[5]))}\n"
                f"{self.f.stat('Награда', str(boss[6]) + ' 💰')}\n"
                f"{self.f.stat('📊 Статус', status)}")

        await update.message.reply_text(text, parse_mode='Markdown')

    async def cmd_regen(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)

        cost = 20
        if user_data['coins'] < cost:
            await update.message.reply_text(self.f.error(f"Недостаточно монет. Нужно {cost} 💰"))
            return

        self.db.add_coins(user_id, -cost)
        self.db.heal(user_id, 50)
        self.db.add_energy(user_id, 20)

        await update.message.reply_text(
            f"{self.f.success('Регенерация завершена!')}\n"
            f"{self.f.list_item('❤️ Здоровье +50')}\n"
            f"{self.f.list_item('⚡ Энергия +20')}",
            parse_mode='Markdown'
        )

    # ========== КАЗИНО ==========

    async def cmd_casino(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (f"{self.f.header('КАЗИНО', '🎰')}\n\n"
                f"{self.f.command('roulette [ставка] [цвет]', 'игра в рулетку')}\n"
                f"{self.f.command('dice [ставка]', 'игра в кости')}\n"
                f"{self.f.command('rps', 'камень-ножницы-бумага')}\n\n"
                f"{self.f.example('roulette 10 red')}\n"
                f"{self.f.example('dice 50')}")

        await update.message.reply_text(
            text,
            reply_markup=IrisKeyboard.back_button(),
            parse_mode='Markdown'
        )

    async def cmd_roulette(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)

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
            await update.message.reply_text(self.f.error(f"Недостаточно монет. Баланс: {user_data['coins']} 💰"))
            return

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
            self.db.add_coins(user_id, winnings)
            self.db.add_stat(user_id, "casino_wins", 1)
            result_text = self.f.success(f"Вы выиграли {winnings} 💰!")
        else:
            self.db.add_coins(user_id, -bet)
            self.db.add_stat(user_id, "casino_losses", 1)
            result_text = self.f.error(f"Вы проиграли {bet} 💰")

        text = (f"{self.f.header('РУЛЕТКА', '🎰')}\n\n"
                f"{self.f.list_item('Ставка: ' + str(bet) + ' 💰')}\n"
                f"{self.f.list_item('Выбрано: ' + choice)}\n"
                f"{self.f.list_item('Выпало: ' + str(result_num) + ' ' + result_color)}\n\n"
                f"{result_text}")

        await update.message.reply_text(text, parse_mode='Markdown')

    async def cmd_dice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)

        bet = 10
        if context.args:
            try:
                bet = int(context.args[0])
            except:
                pass

        if bet > user_data['coins']:
            await update.message.reply_text(self.f.error(f"Недостаточно монет. Баланс: {user_data['coins']} 💰"))
            return

        dice1 = random.randint(1, 6)
        dice2 = random.randint(1, 6)
        total = dice1 + dice2

        if total in [7, 11]:
            win = bet * 2
            result_text = self.f.success(f"Вы выиграли {win} 💰!")
        elif total in [2, 3, 12]:
            win = 0
            result_text = self.f.error(f"Вы проиграли {bet} 💰")
        else:
            win = bet
            result_text = self.f.info(f"Ничья, ставка возвращена: {bet} 💰")

        if win > 0:
            self.db.add_coins(user_id, win)
            self.db.add_stat(user_id, "casino_wins", 1)
        else:
            self.db.add_coins(user_id, -bet)
            self.db.add_stat(user_id, "casino_losses", 1)

        text = (f"{self.f.header('КОСТИ', '🎲')}\n\n"
                f"{self.f.list_item('Ставка: ' + str(bet) + ' 💰')}\n"
                f"{self.f.list_item('Кубики: ' + str(dice1) + ' + ' + str(dice2))}\n"
                f"{self.f.list_item('Сумма: ' + str(total))}\n\n"
                f"{result_text}")

        await update.message.reply_text(text, parse_mode='Markdown')

    async def cmd_rps(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            f"{self.f.header('КАМЕНЬ-НОЖНИЦЫ-БУМАГА', '✊')}\n\nВыберите свой ход:",
            reply_markup=IrisKeyboard.rps_game(),
            parse_mode='Markdown'
        )

    # ========== ЭКОНОМИКА ==========

    async def cmd_shop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (f"{self.f.header('МАГАЗИН', '🛍')}\n\n"
                f"{self.f.section('ЗЕЛЬЯ', '💊')}\n"
                f"{self.f.command('buy зелье здоровья', '50 💰 (❤️+30)')}\n"
                f"{self.f.command('buy большое зелье', '100 💰 (❤️+70)')}\n\n"
                f"{self.f.section('ОРУЖИЕ', '⚔️')}\n"
                f"{self.f.command('buy меч', '200 💰 (⚔️+10)')}\n"
                f"{self.f.command('buy легендарный меч', '500 💰 (⚔️+30)')}\n\n"
                f"{self.f.section('БРОНЯ', '🛡')}\n"
                f"{self.f.command('buy щит', '150 💰 (🛡+5)')}\n"
                f"{self.f.command('buy доспехи', '400 💰 (🛡+15)')}\n\n"
                f"{self.f.section('ЭНЕРГИЯ', '⚡')}\n"
                f"{self.f.command('buy энергетик', '30 💰 (⚡+20)')}\n"
                f"{self.f.command('buy батарейка', '80 💰 (⚡+50)')}")

        await update.message.reply_text(
            text,
            reply_markup=IrisKeyboard.back_button(),
            parse_mode='Markdown'
        )

    async def cmd_buy(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(self.f.error("Укажите предмет: /buy [название]"))
            return

        item = " ".join(context.args).lower()
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)

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
            await update.message.reply_text(self.f.error("Такого предмета нет в магазине"))
            return

        item_data = items[item]

        if user_data['coins'] < item_data['price']:
            await update.message.reply_text(self.f.error(f"Недостаточно монет. Нужно {item_data['price']} 💰"))
            return

        self.db.add_coins(user_id, -item_data['price'])

        if 'heal' in item_data:
            self.db.heal(user_id, item_data['heal'])
            await update.message.reply_text(self.f.success(f"Здоровье восстановлено +{item_data['heal']}❤️"))
        elif 'damage' in item_data:
            self.db.cursor.execute(
                "UPDATE users SET damage = damage + ? WHERE user_id = ?",
                (item_data['damage'], user_id)
            )
            self.db.conn.commit()
            await update.message.reply_text(self.f.success(f"Урон увеличен +{item_data['damage']}⚔️"))
        elif 'armor' in item_data:
            self.db.cursor.execute(
                "UPDATE users SET armor = armor + ? WHERE user_id = ?",
                (item_data['armor'], user_id)
            )
            self.db.conn.commit()
            await update.message.reply_text(self.f.success(f"Броня увеличена +{item_data['armor']}🛡"))
        elif 'energy' in item_data:
            self.db.add_energy(user_id, item_data['energy'])
            await update.message.reply_text(self.f.success(f"Энергия восстановлена +{item_data['energy']}⚡"))

    async def cmd_pay(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text(self.f.error("Использование: /pay @username сумма"))
            return

        query = context.args[0]
        try:
            amount = int(context.args[1])
        except:
            await update.message.reply_text(self.f.error("Сумма должна быть числом"))
            return

        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)

        target_user = self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(self.f.error("Пользователь не найден"))
            return

        if target_user['user_id'] == user_id:
            await update.message.reply_text(self.f.error("Нельзя перевести монеты самому себе"))
            return

        if user_data['coins'] < amount:
            await update.message.reply_text(self.f.error(f"Недостаточно монет. Баланс: {user_data['coins']} 💰"))
            return

        self.db.add_coins(user_id, -amount)
        self.db.add_coins(target_user['user_id'], amount)

        text = (f"{self.f.header('ПЕРЕВОД', '💰')}\n\n"
                f"{self.f.list_item('Получатель: ' + (target_user.get('first_name') or 'Пользователь'))}\n"
                f"{self.f.list_item('Сумма: ' + str(amount) + ' 💰')}\n"
                f"{self.f.list_item('Отправитель: ' + update.effective_user.first_name)}")

        await update.message.reply_text(text, parse_mode='Markdown')

    async def cmd_donate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (f"{self.f.header('ПРИВИЛЕГИИ', '💎')}\n\n"
                f"{self.f.section('VIP СТАТУС', '🌟')}\n"
                f"Цена: {VIP_PRICE} 💰 / {VIP_DAYS} дней\n"
                f"{self.f.list_item('Урон в битвах +20%')}\n"
                f"{self.f.list_item('Награда с боссов +50%')}\n"
                f"{self.f.list_item('Ежедневный бонус +50%')}\n\n"
                f"{self.f.section('PREMIUM СТАТУС', '💎')}\n"
                f"Цена: {PREMIUM_PRICE} 💰 / {PREMIUM_DAYS} дней\n"
                f"{self.f.list_item('Все бонусы VIP')}\n"
                f"{self.f.list_item('Урон в битвах +50%')}\n"
                f"{self.f.list_item('Награда с боссов +100%')}\n"
                f"{self.f.list_item('Ежедневный бонус +100%')}\n\n"
                f"{self.f.command('vip', 'купить VIP')}\n"
                f"{self.f.command('premium', 'купить PREMIUM')}\n\n"
                f"👑 **Владелец:** {OWNER_USERNAME}")

        await update.message.reply_text(
            text,
            reply_markup=IrisKeyboard.back_button(),
            parse_mode='Markdown'
        )

    async def cmd_vip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)

        if user_data['coins'] < VIP_PRICE:
            await update.message.reply_text(self.f.error(f"Недостаточно монет. Нужно {VIP_PRICE} 💰"))
            return

        if self.db.is_vip(user_id):
            await update.message.reply_text(self.f.error("VIP статус уже активен"))
            return

        self.db.add_coins(user_id, -VIP_PRICE)
        self.db.set_vip(user_id, VIP_DAYS)

        await update.message.reply_text(
            f"{self.f.success('VIP СТАТУС АКТИВИРОВАН')}\n\n"
            f"Срок действия: {VIP_DAYS} дней\n"
            f"Все бонусы активны.",
            parse_mode='Markdown'
        )

    async def cmd_premium(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)

        if user_data['coins'] < PREMIUM_PRICE:
            await update.message.reply_text(self.f.error(f"Недостаточно монет. Нужно {PREMIUM_PRICE} 💰"))
            return

        if self.db.is_premium(user_id):
            await update.message.reply_text(self.f.error("PREMIUM статус уже активен"))
            return

        self.db.add_coins(user_id, -PREMIUM_PRICE)
        self.db.set_premium(user_id, PREMIUM_DAYS)

        await update.message.reply_text(
            f"{self.f.success('PREMIUM СТАТУС АКТИВИРОВАН')}\n\n"
            f"Срок действия: {PREMIUM_DAYS} дней\n"
            f"Все бонусы активны.",
            parse_mode='Markdown'
        )

    # ========== МОДЕРАЦИЯ ==========

    async def cmd_warn(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        admin = update.effective_user
        admin_data = self.db.get_user_by_id(admin.id)

        if not self.has_permission(admin_data, 'moderator'):
            await update.message.reply_text(self.f.error("Недостаточно прав"))
            return

        if len(context.args) < 1:
            await update.message.reply_text(self.f.error("Использование: /warn @username [причина]"))
            return

        query = context.args[0]
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else "Нарушение"

        target_user = self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(self.f.error("Пользователь не найден"))
            return

        result = self.db.add_warn(target_user['user_id'], admin.id, reason)

        name = target_user.get('first_name', 'Пользователь')
        warns_count = result['warns_count']

        text = (f"{self.f.header('ПРЕДУПРЕЖДЕНИЕ', '⚠️')}\n\n"
                f"{self.f.list_item('Пользователь: ' + name)}\n"
                f"{self.f.list_item('Предупреждений: ' + str(warns_count) + '/3')}\n"
                f"{self.f.list_item('Причина: ' + reason)}\n"
                f"{self.f.list_item('Администратор: ' + admin.first_name)}")

        await update.message.reply_text(text, parse_mode='Markdown')

    async def cmd_warns(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(self.f.error("Укажите пользователя: /warns @username"))
            return

        query = context.args[0]
        target_user = self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(self.f.error("Пользователь не найден"))
            return

        warns_list = self.db.get_warns(target_user['user_id'])
        name = target_user.get('first_name', 'Пользователь')

        if not warns_list:
            await update.message.reply_text(self.f.info(f"У пользователя {name} нет предупреждений"))
            return

        text = f"{self.f.header(f'ПРЕДУПРЕЖДЕНИЯ: {name}', '📋')}\n\n"

        for warn in warns_list:
            admin = self.db.get_user_by_id(warn['admin_id'])
            admin_name = admin.get('first_name', 'Система') if admin else 'Система'
            date = datetime.datetime.fromisoformat(warn['date']).strftime("%d.%m.%Y %H:%M")

            text += (f"**ID: {warn['id']}**\n"
                     f"{self.f.list_item('Причина: ' + warn['reason'])}\n"
                     f"{self.f.list_item('Администратор: ' + admin_name)}\n"
                     f"{self.f.list_item('Дата: ' + date)}\n\n")

        await update.message.reply_text(text, parse_mode='Markdown')

    async def cmd_unwarn(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        admin = update.effective_user
        admin_data = self.db.get_user_by_id(admin.id)

        if not self.has_permission(admin_data, 'moderator'):
            await update.message.reply_text(self.f.error("Недостаточно прав"))
            return

        if not context.args:
            await update.message.reply_text(self.f.error("Укажите пользователя: /unwarn @username"))
            return

        query = context.args[0]
        target_user = self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(self.f.error("Пользователь не найден"))
            return

        removed = self.db.remove_last_warn(target_user['user_id'])
        name = target_user.get('first_name', 'Пользователь')

        if not removed:
            await update.message.reply_text(self.f.info(f"У пользователя {name} нет предупреждений"))
            return

        await update.message.reply_text(
            self.f.success(f"Последнее предупреждение снято с {name}"),
            parse_mode='Markdown'
        )

    async def cmd_mute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        admin = update.effective_user
        admin_data = self.db.get_user_by_id(admin.id)

        if not self.has_permission(admin_data, 'moderator'):
            await update.message.reply_text(self.f.error("Недостаточно прав"))
            return

        if len(context.args) < 2:
            await update.message.reply_text(self.f.error("Использование: /mute @username минут [причина]"))
            return

        query = context.args[0]
        try:
            minutes = int(context.args[1])
            reason = " ".join(context.args[2:]) if len(context.args) > 2 else "Нарушение"
        except:
            await update.message.reply_text(self.f.error("Некорректное время"))
            return

        target_user = self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(self.f.error("Пользователь не найден"))
            return

        mute_until = self.db.mute_user(target_user['user_id'], minutes, admin.id, reason)
        name = target_user.get('first_name', 'Пользователь')

        until_str = mute_until.strftime("%d.%m.%Y %H:%M")

        text = (f"{self.f.header('МУТ', '🔇')}\n\n"
                f"{self.f.list_item('Пользователь: ' + name)}\n"
                f"{self.f.list_item('Срок: ' + str(minutes) + ' минут')}\n"
                f"{self.f.list_item('До: ' + until_str)}\n"
                f"{self.f.list_item('Причина: ' + reason)}\n"
                f"{self.f.list_item('Администратор: ' + admin.first_name)}")

        await update.message.reply_text(text, parse_mode='Markdown')

    async def cmd_unmute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        admin = update.effective_user
        admin_data = self.db.get_user_by_id(admin.id)

        if not self.has_permission(admin_data, 'moderator'):
            await update.message.reply_text(self.f.error("Недостаточно прав"))
            return

        if not context.args:
            await update.message.reply_text(self.f.error("Укажите пользователя: /unmute @username"))
            return

        query = context.args[0]
        target_user = self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(self.f.error("Пользователь не найден"))
            return

        if not self.db.is_muted(target_user['user_id']):
            await update.message.reply_text(self.f.info("Пользователь не в муте"))
            return

        self.db.unmute_user(target_user['user_id'])
        name = target_user.get('first_name', 'Пользователь')

        await update.message.reply_text(
            self.f.success(f"Мут снят с {name}"),
            parse_mode='Markdown'
        )

    async def cmd_mutelist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        muted = self.db.get_muted_users()

        if not muted:
            await update.message.reply_text(self.f.info("Нет пользователей в муте"))
            return

        text = f"{self.f.header('СПИСОК ЗАМУЧЕННЫХ', '🔇')}\n\n"

        for user_id, name, mute_until in muted[:10]:
            if mute_until:
                until = datetime.datetime.fromisoformat(mute_until).strftime("%d.%m.%Y %H:%M")
            else:
                until = "неизвестно"

            text += f"{self.f.list_item(name + ' — до ' + until)}\n"

        await update.message.reply_text(
            text,
            reply_markup=IrisKeyboard.back_button(),
            parse_mode='Markdown'
        )

    async def cmd_ban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        admin = update.effective_user
        admin_data = self.db.get_user_by_id(admin.id)

        if not self.has_permission(admin_data, 'moderator'):
            await update.message.reply_text(self.f.error("Недостаточно прав"))
            return

        if len(context.args) < 1:
            await update.message.reply_text(self.f.error("Использование: /ban @username [причина]"))
            return

        query = context.args[0]
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else "Нарушение правил"

        target_user = self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(self.f.error("Пользователь не найден"))
            return

        self.db.ban_user(target_user['user_id'], admin.id, reason)
        name = target_user.get('first_name', 'Пользователь')

        text = (f"{self.f.header('БЛОКИРОВКА', '🔴')}\n\n"
                f"{self.f.list_item('Пользователь: ' + name)}\n"
                f"{self.f.list_item('Причина: ' + reason)}\n"
                f"{self.f.list_item('Администратор: ' + admin.first_name)}")

        await update.message.reply_text(text, parse_mode='Markdown')

    async def cmd_unban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        admin = update.effective_user
        admin_data = self.db.get_user_by_id(admin.id)

        if not self.has_permission(admin_data, 'moderator'):
            await update.message.reply_text(self.f.error("Недостаточно прав"))
            return

        if not context.args:
            await update.message.reply_text(self.f.error("Укажите пользователя: /unban @username"))
            return

        query = context.args[0]
        target_user = self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(self.f.error("Пользователь не найден"))
            return

        if not self.db.is_banned(target_user['user_id']):
            await update.message.reply_text(self.f.info("Пользователь не заблокирован"))
            return

        self.db.unban_user(target_user['user_id'])
        name = target_user.get('first_name', 'Пользователь')

        await update.message.reply_text(
            self.f.success(f"Блокировка снята с {name}"),
            parse_mode='Markdown'
        )

    async def cmd_banlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        page = 1
        if context.args and context.args[0].isdigit():
            page = int(context.args[0])

        bans, total = self.db.get_banlist(page)
        total_pages = (total + 9) // 10

        if not bans:
            await update.message.reply_text(self.f.info("Список заблокированных пуст"))
            return

        text = f"{self.f.header('СПИСОК ЗАБЛОКИРОВАННЫХ', '📋')}\n"
        text += f"Страница {page}/{total_pages}\n\n"

        for i, ban in enumerate(bans, 1):
            date = datetime.datetime.fromisoformat(ban['date']).strftime("%d.%m.%Y") if ban['date'] else "неизвестно"
            text += (f"{i}. {ban['name']}\n"
                     f"└ Причина: {ban['reason']}\n"
                     f"└ Дата: {date}\n"
                     f"└ Заблокировал: {ban['admin']}\n\n")

        await update.message.reply_text(
            text,
            reply_markup=IrisKeyboard.pagination(page, total_pages, "banlist"),
            parse_mode='Markdown'
        )

    async def cmd_kick(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        admin = update.effective_user
        admin_data = self.db.get_user_by_id(admin.id)

        if not self.has_permission(admin_data, 'moderator'):
            await update.message.reply_text(self.f.error("Недостаточно прав"))
            return

        if not context.args:
            await update.message.reply_text(self.f.error("Укажите пользователя: /kick @username"))
            return

        query = context.args[0]
        target_user = self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(self.f.error("Пользователь не найден"))
            return

        name = target_user.get('first_name', 'Пользователь')

        await update.message.reply_text(
            self.f.success(f"Пользователь {name} исключен из чата"),
            parse_mode='Markdown'
        )

    # ========== ПРОЧИЕ КОМАНДЫ ==========

    async def cmd_weather(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        city = " ".join(context.args) if context.args else "Москва"

        weathers = ["☀️ солнечно", "⛅ облачно", "☁️ пасмурно", "🌧 дождь", "⛈ гроза", "❄️ снег"]
        temp = random.randint(-15, 30)
        wind = random.randint(0, 15)
        humidity = random.randint(30, 90)
        weather = random.choice(weathers)

        text = (f"{self.f.header(f'ПОГОДА: {city.upper()}', '🌍')}\n\n"
                f"{weather}, {temp}°C\n"
                f"💨 Ветер: {wind} м/с\n"
                f"💧 Влажность: {humidity}%\n"
                f"📅 {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}")

        await update.message.reply_text(text, parse_mode='Markdown')

    async def cmd_news(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        news_list = [
            "Бот «СПЕКТР» успешно запущен",
            "Добавлена система боссов",
            "Обновлен интерфейс команд",
            "Улучшена система модерации",
            "Добавлены ежедневные бонусы",
            "Интегрирован Gemini AI"
        ]

        text = f"{self.f.header('НОВОСТИ', '📰')}\n\n" + f"{random.choice(news_list)}"

        await update.message.reply_text(text, parse_mode='Markdown')

    async def cmd_quote(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        quotes = [
            "Успех — это способность идти от поражения к поражению, не теряя энтузиазма.",
            "Сложнее всего начать действовать, все остальное зависит только от упорства.",
            "Лучший способ предсказать будущее — создать его.",
            "Не бойтесь, что у вас не получится. Бойтесь, что вы не попробуете.",
            "Будьте собой, остальные роли уже заняты.",
            "Каждый день — это новая возможность изменить свою жизнь."
        ]

        text = f"{self.f.header('ЦИТАТА ДНЯ', '📝')}\n\n" + f"«{random.choice(quotes)}»"

        await update.message.reply_text(text, parse_mode='Markdown')

    async def cmd_players(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        count = self.db.get_players_count()

        text = f"{self.f.header('СТАТИСТИКА', '👥')}\n\n" + f"Всего игроков: {count}"

        await update.message.reply_text(text, parse_mode='Markdown')

    async def cmd_eng_free(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)

        last_free = user_data.get('last_free_energy')
        if last_free:
            last = datetime.datetime.fromisoformat(last_free)
            if (datetime.datetime.now() - last).seconds < 3600:
                remaining = 3600 - (datetime.datetime.now() - last).seconds
                minutes = remaining // 60
                await update.message.reply_text(self.f.error(f"Бесплатную энергию можно получать раз в час. Осталось: {minutes} мин"))
                return

        energy = 20
        self.db.add_energy(user_id, energy)

        self.db.cursor.execute(
            "UPDATE users SET last_free_energy = ? WHERE user_id = ?",
            (datetime.datetime.now(), user_id)
        )
        self.db.conn.commit()

        await update.message.reply_text(self.f.success(f"Получено {energy} ⚡ энергии"))

    # ========== ОБРАБОТЧИКИ ==========

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        message_text = update.message.text

        if message_text.startswith('/'):
            return

        user_data = self.db.get_or_create_user("tg", str(user.id), user.first_name)
        self.db.add_stat(user.id, "messages_count", 1)

        if self.db.is_banned(user.id):
            return

        if self.db.is_muted(user.id):
            remaining = self.db.get_mute_time(user.id)
            await update.message.reply_text(self.f.error(f"Вы в муте. Осталось: {remaining}"))
            return

        if await self.check_spam(update):
            return

        response = await self.ai.get_response(user.id, message_text)
        if response:
            await update.message.reply_text(f"🤖 **СПЕКТР:** {response}", parse_mode='Markdown')
            return

        msg_lower = message_text.lower()

        if any(word in msg_lower for word in ["привет", "здравствуйте", "хай"]):
            await update.message.reply_text("👋 Здравствуйте! Чем могу помочь?")
        elif any(word in msg_lower for word in ["как дела", "как вы"]):
            await update.message.reply_text("⚙️ Всё функционирует в штатном режиме")
        elif any(word in msg_lower for word in ["спасибо", "благодарю"]):
            await update.message.reply_text("🤝 Рад помочь!")
        elif any(word in msg_lower for word in ["кто создал", "владелец"]):
            await update.message.reply_text(f"👑 Владелец: {OWNER_USERNAME}")
        else:
            responses = [
                "Используйте /help для просмотра доступных команд.",
                "Я к вашим услугам. Напишите /menu для навигации.",
                "Чем могу быть полезен?",
                "Обратитесь к справке /help."
            ]
            await update.message.reply_text(random.choice(responses))

    async def handle_new_members(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        for member in update.message.new_chat_members:
            if member.is_bot:
                continue

            await update.message.reply_text(
                f"👋 Добро пожаловать, {member.first_name}!\n"
                f"Используйте /help для получения списка команд.",
                parse_mode='Markdown'
            )

    async def handle_left_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        member = update.message.left_chat_member
        if member.is_bot:
            return

        await update.message.reply_text(
            f"👋 {member.first_name} покинул чат. Будем ждать возвращения!",
            parse_mode='Markdown'
        )

    # ========== CALLBACK КНОПКИ ==========

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        user = query.from_user

        if data == "noop":
            return

        elif data == "menu_back":
            await query.edit_message_text(
                f"{self.f.header('ГЛАВНОЕ МЕНЮ', '🎮')}\n\nВыберите раздел:",
                reply_markup=IrisKeyboard.main_menu(),
                parse_mode='Markdown'
            )

        elif data == "menu_profile":
            await self.cmd_profile(update, context)

        elif data == "menu_stats":
            await self.cmd_my_stats(update, context)

        elif data == "menu_bosses":
            await self.cmd_boss_list(update, context)

        elif data == "menu_casino":
            await self.cmd_casino(update, context)

        elif data == "menu_shop":
            await self.cmd_shop(update, context)

        elif data == "menu_donate":
            await self.cmd_donate(update, context)

        elif data == "menu_moderation":
            admin_data = self.db.get_user_by_id(user.id)
            text = f"{self.f.header('МОДЕРАЦИЯ', '⚙️')}\n\n"

            if self.has_permission(admin_data, 'moderator'):
                text += (f"{self.f.command('warn @ник [причина]', 'предупреждение')}\n"
                         f"{self.f.command('mute @ник минут [причина]', 'заглушить')}\n"
                         f"{self.f.command('ban @ник [причина]', 'заблокировать')}\n"
                         f"{self.f.command('banlist', 'список заблокированных')}\n"
                         f"{self.f.command('mutelist', 'список замученных')}\n"
                         f"{self.f.command('kick @ник', 'исключить')}")
            else:
                text += self.f.error("Недостаточно прав для просмотра раздела")

            await query.edit_message_text(
                text,
                reply_markup=IrisKeyboard.back_button(),
                parse_mode='Markdown'
            )

        elif data == "menu_help":
            await self.cmd_help(update, context)

        elif data.startswith("boss_fight_"):
            boss_id = int(data.split('_')[2])
            context.args = [str(boss_id)]
            await self.cmd_boss_fight(update, context)

        elif data.startswith("banlist_page_"):
            page = int(data.split('_')[2])
            context.args = [str(page)]
            await self.cmd_banlist(update, context)

        elif data in ["edit_nick", "edit_title", "edit_motto", "edit_gender"]:
            if data == "edit_nick":
                await self.cmd_edit_nick(update, context)
            elif data == "edit_title":
                await self.cmd_edit_title(update, context)
            elif data == "edit_motto":
                await self.cmd_edit_motto(update, context)
            elif data == "edit_gender":
                await self.cmd_edit_gender(update, context)

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

            text = f"{self.f.header('КНБ', '✊')}\n\n"
            text += f"{emoji[choice]} **Вы:** {names[choice]}\n"
            text += f"{emoji[bot_choice]} **Бот:** {names[bot_choice]}\n\n"

            if choice == bot_choice:
                self.db.add_stat(user.id, "rps_draws")
                text += self.f.info("🤝 **НИЧЬЯ!**")
            elif results.get((choice, bot_choice)) == "win":
                self.db.add_stat(user.id, "rps_wins")
                reward = random.randint(10, 30)
                self.db.add_coins(user.id, reward)
                text += self.f.success(f"🎉 **ПОБЕДА!** +{reward} 💰")
            else:
                self.db.add_stat(user.id, "rps_losses")
                text += self.f.error("😢 **ПОРАЖЕНИЕ!**")

            await query.edit_message_text(
                text,
                reply_markup=IrisKeyboard.back_button(),
                parse_mode='Markdown'
            )

    # ========== ЗАПУСК ==========

    async def run(self):
        try:
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            logger.info("🚀 Бот «СПЕКТР» запущен")
            while True:
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await asyncio.sleep(5)
            await self.run()

    async def close(self):
        await self.ai.close()
        self.db.close()
        logger.info("👋 Бот остановлен")


# ========== ТОЧКА ВХОДА ==========
async def main():
    print("=" * 50)
    print("🚀 ЗАПУСК БОТА «СПЕКТР»")
    print("=" * 50)

    bot = GameBot()

    try:
        await bot.run()
    except KeyboardInterrupt:
        await bot.close()
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        await bot.close()

if __name__ == "__main__":
    asyncio.run(main())
