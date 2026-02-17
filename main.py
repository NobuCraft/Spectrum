#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
СПЕКТР МЕГА-БОТ - ПОЛНАЯ ВЕРСИЯ
Объединение: Iris (модерация) + TrueMafia (игра) + TReanfer (экономика) + Anya (AI)
Автор: @NobuCraft
Версия: 3.0.0
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
import hashlib
import base64
import math
from enum import Enum

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from telegram.error import TelegramError, InvalidToken

# ========== НАСТРОЙКА ЛОГИРОВАНИЯ ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== КОНФИГУРАЦИЯ ==========
TELEGRAM_TOKEN = "8326390250:AAG1nTYdy07AuKsYXS3yvDehfU2JuR0RqGo"
GEMINI_API_KEY = "AIzaSyBPT4JUIevH0UiwXVY9eQjrY_pTPLeLbNE"
OWNER_ID = 1732658530
OWNER_USERNAME = "@NobuCraft"

# Настройки антиспама
SPAM_LIMIT = 5
SPAM_WINDOW = 3
SPAM_MUTE_TIME = 120

# ========== СИСТЕМА РАНГОВ (IRIS) ==========
class Rank(Enum):
    USER = 0
    JUNIOR_MODER = 1
    SENIOR_MODER = 2
    JUNIOR_ADMIN = 3
    SENIOR_ADMIN = 4
    CREATOR = 5

RANK_NAMES = {
    0: "👤 Участник",
    1: "🛡️ Младший модератор",
    2: "🛡️ Старший модератор",
    3: "⚜️ Младший администратор",
    4: "⚜️ Старший администратор",
    5: "👑 Создатель"
}

# ========== ЦЕНЫ НА ПРИВИЛЕГИИ (TREANFER) ==========
PRIVILEGE_PRICES = {
    "vip": 5000,
    "premium": 15000,
    "lord": 30000,
    "ultra": 50000,
    "moderator": 100000,
    "admin": 200000,
    "creator": 500000
}

PRIVILEGE_DAYS = {
    "vip": 30,
    "premium": 30,
    "lord": 30,
    "ultra": 30,
    "moderator": 30,
    "admin": 30,
    "creator": 365
}

# ========== СТИЛЬ IRIS (КЛАСС ДЛЯ ФОРМАТИРОВАНИЯ) ==========
class IrisFormatter:
    """Полный набор форматирования в стиле Iris"""
    
    @staticmethod
    def header(title: str, emoji: str = "📋") -> str:
        """Красивый заголовок с рамкой"""
        return (
            f"╔══════════════════════════════╗\n"
            f"║    {emoji} {title}    ║\n"
            f"╚══════════════════════════════╝\n"
        )
    
    @staticmethod
    def section(title: str, emoji: str = "▫️") -> str:
        """Заголовок раздела с линией"""
        return f"\n{emoji} **{title}**\n" + "━" * 25 + "\n"
    
    @staticmethod
    def command(name: str, desc: str, usage: str = "", emoji: str = "・") -> str:
        """Форматирование команды"""
        if usage:
            return f"{emoji} `/{name} {usage}` — {desc}"
        return f"{emoji} `/{name}` — {desc}"
    
    @staticmethod
    def param(name: str, desc: str) -> str:
        """Параметр команды"""
        return f"└ {name} — {desc}"
    
    @staticmethod
    def example(text: str) -> str:
        """Пример использования"""
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
    
    @staticmethod
    def spoiler(text: str) -> str:
        return f"||{text}||"
    
    @staticmethod
    def quote(text: str) -> str:
        return f"> {text}"

f = IrisFormatter()

# ========== КЛАВИАТУРЫ В СТИЛЕ IRIS ==========
class IrisKeyboard:
    """Все клавиатуры бота"""
    
    @staticmethod
    def main_menu():
        """Главное меню"""
        keyboard = [
            [InlineKeyboardButton("👤 ПРОФИЛЬ", callback_data="menu_profile"),
             InlineKeyboardButton("⚙️ МОДЕРАЦИЯ", callback_data="menu_moderation")],
            [InlineKeyboardButton("🔪 МАФИЯ", callback_data="menu_mafia"),
             InlineKeyboardButton("💰 ЭКОНОМИКА", callback_data="menu_economy")],
            [InlineKeyboardButton("🎮 ИГРЫ", callback_data="menu_games"),
             InlineKeyboardButton("🤖 ИИ-ЧАТ", callback_data="menu_ai")],
            [InlineKeyboardButton("👑 ПРИВИЛЕГИИ", callback_data="menu_donate"),
             InlineKeyboardButton("📚 ПОМОЩЬ", callback_data="menu_help")]
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
    def moderation_menu():
        keyboard = [
            [InlineKeyboardButton("⚠️ ВАРНЫ", callback_data="mod_warns"),
             InlineKeyboardButton("🔇 МУТЫ", callback_data="mod_mutes")],
            [InlineKeyboardButton("🔴 БАНЫ", callback_data="mod_bans"),
             InlineKeyboardButton("📋 СПИСКИ", callback_data="mod_lists")],
            [InlineKeyboardButton("⚙️ НАСТРОЙКИ", callback_data="mod_settings"),
             InlineKeyboardButton("🔙 НАЗАД", callback_data="menu_back")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def mafia_game_menu():
        keyboard = [
            [InlineKeyboardButton("🔪 СОЗДАТЬ ИГРУ", callback_data="mafia_create")],
            [InlineKeyboardButton("🎮 ПРИСОЕДИНИТЬСЯ", callback_data="mafia_join")],
            [InlineKeyboardButton("▶️ НАЧАТЬ ИГРУ", callback_data="mafia_start")],
            [InlineKeyboardButton("🗳️ ПРОГОЛОСОВАТЬ", callback_data="mafia_vote")],
            [InlineKeyboardButton("📊 СТАТИСТИКА", callback_data="mafia_stats")],
            [InlineKeyboardButton("🔙 НАЗАД", callback_data="menu_back")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def economy_menu():
        keyboard = [
            [InlineKeyboardButton("🛍 МАГАЗИН", callback_data="shop"),
             InlineKeyboardButton("💎 ПРИВИЛЕГИИ", callback_data="donate")],
            [InlineKeyboardButton("📦 ИНВЕНТАРЬ", callback_data="inventory"),
             InlineKeyboardButton("🏆 ТОП", callback_data="top")],
            [InlineKeyboardButton("💰 ПЕРЕВОД", callback_data="pay"),
             InlineKeyboardButton("🎁 БОНУСЫ", callback_data="bonuses")],
            [InlineKeyboardButton("🔙 НАЗАД", callback_data="menu_back")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def games_menu():
        keyboard = [
            [InlineKeyboardButton("👾 БОССЫ", callback_data="bosses"),
             InlineKeyboardButton("🎰 КАЗИНО", callback_data="casino")],
            [InlineKeyboardButton("✊ КНБ", callback_data="rps"),
             InlineKeyboardButton("⭕ КРЕСТИКИ-НОЛИКИ", callback_data="ttt")],
            [InlineKeyboardButton("💣 САПЁР", callback_data="minesweeper"),
             InlineKeyboardButton("🧠 МЕМОРИ", callback_data="memory")],
            [InlineKeyboardButton("🔙 НАЗАД", callback_data="menu_back")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def rps_game():
        keyboard = [
            [
                InlineKeyboardButton("🪨 КАМЕНЬ", callback_data="rps_rock"),
                InlineKeyboardButton("✂️ НОЖНИЦЫ", callback_data="rps_scissors"),
                InlineKeyboardButton("📄 БУМАГА", callback_data="rps_paper")
            ],
            [InlineKeyboardButton("🔙 НАЗАД", callback_data="menu_back")]
        ]
        return InlineKeyboardMarkup(keyboard)

# ========== БАЗА ДАННЫХ (ПОЛНАЯ) ==========
class Database:
    def __init__(self, db_name="spectrum_mega.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_all_tables()
        self.init_data()
        print("✅ Мега-база данных инициализирована")

    def create_all_tables(self):
        """Создание всех таблиц бота"""
        
        # ===== ТАБЛИЦА ПОЛЬЗОВАТЕЛЕЙ (ОСНОВНАЯ) =====
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                
                -- Экономика (TReanfer)
                coins INTEGER DEFAULT 1000,
                diamonds INTEGER DEFAULT 0,
                crystals INTEGER DEFAULT 0,
                
                -- Привилегии
                role TEXT DEFAULT 'user',
                vip_until TIMESTAMP,
                premium_until TIMESTAMP,
                lord_until TIMESTAMP,
                ultra_until TIMESTAMP,
                
                -- Модерация (Iris)
                rank INTEGER DEFAULT 0,
                warns INTEGER DEFAULT 0,
                warns_list TEXT DEFAULT '[]',
                mute_until TIMESTAMP,
                banned INTEGER DEFAULT 0,
                ban_reason TEXT,
                ban_date TIMESTAMP,
                ban_admin INTEGER,
                
                -- Игры
                level INTEGER DEFAULT 1,
                exp INTEGER DEFAULT 0,
                health INTEGER DEFAULT 100,
                armor INTEGER DEFAULT 0,
                damage INTEGER DEFAULT 10,
                boss_kills INTEGER DEFAULT 0,
                
                -- Статистика игр
                rps_wins INTEGER DEFAULT 0,
                rps_losses INTEGER DEFAULT 0,
                rps_draws INTEGER DEFAULT 0,
                casino_wins INTEGER DEFAULT 0,
                casino_losses INTEGER DEFAULT 0,
                ttt_wins INTEGER DEFAULT 0,
                ttt_losses INTEGER DEFAULT 0,
                ttt_draws INTEGER DEFAULT 0,
                memory_wins INTEGER DEFAULT 0,
                memory_games INTEGER DEFAULT 0,
                mine_wins INTEGER DEFAULT 0,
                mine_games INTEGER DEFAULT 0,
                mafia_wins INTEGER DEFAULT 0,
                mafia_games INTEGER DEFAULT 0,
                
                -- Профиль
                gender TEXT DEFAULT 'не указан',
                nickname TEXT,
                city TEXT DEFAULT 'не указан',
                bio TEXT,
                title TEXT DEFAULT '',
                motto TEXT DEFAULT 'Нет девиза',
                rep INTEGER DEFAULT 0,
                
                -- Активность
                messages_count INTEGER DEFAULT 0,
                commands_used INTEGER DEFAULT 0,
                last_seen TIMESTAMP,
                daily_streak INTEGER DEFAULT 0,
                last_daily TIMESTAMP,
                last_weekly TIMESTAMP,
                
                -- Системное
                platform TEXT DEFAULT 'tg',
                platform_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # ===== ТАБЛИЦА МОДЕРАЦИИ (IRIS) =====
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS moderation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                user_id INTEGER,
                admin_id INTEGER,
                action TEXT,
                reason TEXT,
                duration INTEGER,
                created_at TIMESTAMP
            )
        ''')
        
        # ===== ТАБЛИЦА ТРИГГЕРОВ (IRIS) =====
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS triggers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                trigger_word TEXT,
                response TEXT,
                created_by INTEGER,
                created_at TIMESTAMP
            )
        ''')
        
        # ===== ТАБЛИЦА НАСТРОЕК ЧАТА (IRIS) =====
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_settings (
                chat_id INTEGER PRIMARY KEY,
                rules TEXT,
                welcome_message TEXT,
                goodbye_message TEXT,
                auto_kick INTEGER DEFAULT 0,
                auto_kick_time INTEGER DEFAULT 30,
                anti_raid INTEGER DEFAULT 0,
                anti_spam INTEGER DEFAULT 1,
                captcha INTEGER DEFAULT 0
            )
        ''')
        
        # ===== ТАБЛИЦА ИГР МАФИИ (TRUEMAFIA) =====
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS mafia_games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_id INTEGER,
                status TEXT DEFAULT 'waiting',
                players TEXT,
                roles TEXT,
                phase TEXT DEFAULT 'night',
                day_count INTEGER DEFAULT 1,
                votes TEXT,
                killed TEXT,
                created_at TIMESTAMP
            )
        ''')
        
        # ===== ТАБЛИЦА МАГАЗИНА (TREANFER) =====
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS shop_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                description TEXT,
                price_coins INTEGER,
                price_diamonds INTEGER,
                type TEXT,
                value TEXT,
                stock INTEGER DEFAULT -1
            )
        ''')
        
        # ===== ТАБЛИЦА ИНВЕНТАРЯ =====
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                item_id INTEGER,
                quantity INTEGER DEFAULT 1,
                acquired_at TIMESTAMP
            )
        ''')
        
        # ===== ТАБЛИЦА КЛАНОВ =====
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
                created_at TIMESTAMP
            )
        ''')
        
        # ===== ТАБЛИЦА УЧАСТНИКОВ КЛАНА =====
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS clan_members (
                clan_id INTEGER,
                user_id INTEGER,
                role TEXT DEFAULT 'member',
                joined_at TIMESTAMP,
                UNIQUE(clan_id, user_id)
            )
        ''')
        
        # ===== ТАБЛИЦА БОССОВ =====
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
                created_at TIMESTAMP
            )
        ''')
        
        # ===== ТАБЛИЦА ДОСТИЖЕНИЙ =====
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                achievement_name TEXT,
                achievement_desc TEXT,
                earned_date TIMESTAMP,
                reward_coins INTEGER DEFAULT 0,
                UNIQUE(user_id, achievement_name)
            )
        ''')
        
        # ===== ТАБЛИЦА ДОЛГОВ =====
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS debts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                debtor_id INTEGER,
                creditor_id INTEGER,
                amount INTEGER,
                reason TEXT,
                created_at TIMESTAMP,
                deadline TIMESTAMP,
                is_paid INTEGER DEFAULT 0
            )
        ''')
        
        # ===== ТАБЛИЦА ТУРНИРОВ =====
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tournaments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                game_type TEXT,
                status TEXT DEFAULT 'registering',
                prize_pool INTEGER,
                max_participants INTEGER,
                participants TEXT,
                start_date TIMESTAMP,
                created_at TIMESTAMP
            )
        ''')
        
        self.conn.commit()
    
    def init_data(self):
        """Инициализация начальных данных"""
        
        # Инициализация боссов
        self.cursor.execute("SELECT COUNT(*) FROM bosses")
        if self.cursor.fetchone()[0] == 0:
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
        
        # Инициализация магазина
        self.cursor.execute("SELECT COUNT(*) FROM shop_items")
        if self.cursor.fetchone()[0] == 0:
            shop_data = [
                ("Зелье здоровья", "Восстанавливает 30 HP", 50, 0, "heal", "30", -1),
                ("Большое зелье", "Восстанавливает 70 HP", 100, 0, "heal", "70", -1),
                ("Меч", "Увеличивает урон на 10", 200, 0, "damage", "10", -1),
                ("Легендарный меч", "Увеличивает урон на 30", 500, 0, "damage", "30", -1),
                ("Щит", "Увеличивает броню на 5", 150, 0, "armor", "5", -1),
                ("Доспехи", "Увеличивает броню на 15", 400, 0, "armor", "15", -1),
                ("Энергетик", "Восстанавливает 20 энергии", 30, 0, "energy", "20", -1),
                ("Батарейка", "Восстанавливает 50 энергии", 80, 0, "energy", "50", -1),
                ("VIP пропуск", "VIP статус на 30 дней", 5000, 100, "vip", "30", 10),
                ("PREMIUM пропуск", "PREMIUM статус на 30 дней", 15000, 300, "premium", "30", 5),
            ]
            for item in shop_data:
                self.cursor.execute('''
                    INSERT INTO shop_items (name, description, price_coins, price_diamonds, type, value, stock)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', item)
        
        self.conn.commit()
    
    # ========== МЕТОДЫ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ ==========
    
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
    
    # ========== МЕТОДЫ ДЛЯ ЭКОНОМИКИ (TREANFER) ==========
    
    def add_coins(self, user_id: int, amount: int):
        self.cursor.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (amount, user_id))
        self.conn.commit()
    
    def add_diamonds(self, user_id: int, amount: int):
        self.cursor.execute("UPDATE users SET diamonds = diamonds + ? WHERE user_id = ?", (amount, user_id))
        self.conn.commit()
    
    def add_crystals(self, user_id: int, amount: int):
        self.cursor.execute("UPDATE users SET crystals = crystals + ? WHERE user_id = ?", (amount, user_id))
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
    
    def get_top(self, by="coins", limit=10):
        self.cursor.execute(f"SELECT first_name, {by} FROM users ORDER BY {by} DESC LIMIT ?", (limit,))
        return self.cursor.fetchall()
    
    # ========== МЕТОДЫ ДЛЯ ПРИВИЛЕГИЙ ==========
    
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
    
    # ========== МЕТОДЫ ДЛЯ МАГАЗИНА ==========
    
    def get_shop_items(self):
        self.cursor.execute("SELECT * FROM shop_items ORDER BY price_coins")
        return self.cursor.fetchall()
    
    def get_shop_item(self, item_id):
        self.cursor.execute("SELECT * FROM shop_items WHERE id = ?", (item_id,))
        return self.cursor.fetchone()
    
    def buy_item(self, user_id: int, item_id: int, quantity: int = 1):
        item = self.get_shop_item(item_id)
        if not item:
            return None
        
        user = self.get_user_by_id(user_id)
        total_price = item[3] * quantity
        
        if user['coins'] < total_price:
            return False
        
        self.add_coins(user_id, -total_price)
        
        # Добавляем в инвентарь
        self.cursor.execute('''
            INSERT INTO inventory (user_id, item_id, quantity, acquired_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, item_id) DO UPDATE SET quantity = quantity + ?
        ''', (user_id, item_id, quantity, datetime.datetime.now(), quantity))
        
        self.conn.commit()
        return True
    
    def get_inventory(self, user_id: int):
        self.cursor.execute('''
            SELECT i.*, s.name, s.description, s.type, s.value
            FROM inventory i
            JOIN shop_items s ON i.item_id = s.id
            WHERE i.user_id = ? AND i.quantity > 0
        ''', (user_id,))
        return self.cursor.fetchall()
    
    # ========== МЕТОДЫ ДЛЯ МОДЕРАЦИИ (IRIS) ==========
    
    def get_user_rank(self, user_id: int, chat_id: int = None) -> int:
        user = self.get_user_by_id(user_id)
        return user.get('rank', 0)
    
    def set_user_rank(self, user_id: int, rank: int, admin_id: int):
        self.cursor.execute("UPDATE users SET rank = ? WHERE user_id = ?", (rank, user_id))
        
        # Логируем действие
        self.cursor.execute('''
            INSERT INTO moderation (chat_id, user_id, admin_id, action, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (0, user_id, admin_id, f"rank_change_{rank}", datetime.datetime.now()))
        
        self.conn.commit()
    
    def add_warn(self, user_id: int, admin_id: int, reason: str = "Нарушение") -> Dict:
        user = self.get_user_by_id(user_id)
        warns_list = json.loads(user.get('warns_list', '[]'))
        
        warn_data = {
            'id': len(warns_list) + 1,
            'admin_id': admin_id,
            'reason': reason,
            'date': datetime.datetime.now().isoformat()
        }
        
        warns_list.append(warn_data)
        
        self.cursor.execute(
            "UPDATE users SET warns = warns + 1, warns_list = ? WHERE user_id = ?",
            (json.dumps(warns_list), user_id)
        )
        self.conn.commit()
        
        return {
            'warn_id': warn_data['id'],
            'warns_count': len(warns_list),
            'warn_data': warn_data
        }
    
    def get_warns(self, user_id: int) -> List[Dict]:
        user = self.get_user_by_id(user_id)
        return json.loads(user.get('warns_list', '[]'))
    
    def remove_last_warn(self, user_id: int) -> Optional[Dict]:
        user = self.get_user_by_id(user_id)
        warns_list = json.loads(user.get('warns_list', '[]'))
        
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
            "UPDATE users SET mute_until = ? WHERE user_id = ?",
            (mute_until, user_id)
        )
        
        # Логируем
        self.cursor.execute('''
            INSERT INTO moderation (chat_id, user_id, admin_id, action, reason, duration, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (0, user_id, admin_id, "mute", reason, minutes, datetime.datetime.now()))
        
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
                days = remaining.days
                hours = remaining.seconds // 3600
                minutes = (remaining.seconds % 3600) // 60
                
                parts = []
                if days > 0:
                    parts.append(f"{days} дн")
                if hours > 0:
                    parts.append(f"{hours} ч")
                if minutes > 0:
                    parts.append(f"{minutes} мин")
                
                return " ".join(parts)
        return "0"
    
    def unmute_user(self, user_id: int):
        self.cursor.execute("UPDATE users SET mute_until = NULL WHERE user_id = ?", (user_id,))
        self.conn.commit()
    
    def get_muted_users(self) -> List[Tuple]:
        self.cursor.execute(
            "SELECT user_id, first_name, mute_until FROM users WHERE mute_until IS NOT NULL AND mute_until > ? ORDER BY mute_until",
            (datetime.datetime.now(),)
        )
        return self.cursor.fetchall()
    
    def ban_user(self, user_id: int, admin_id: int, reason: str = "Нарушение"):
        self.cursor.execute(
            "UPDATE users SET banned = 1, ban_reason = ?, ban_date = ?, ban_admin = ? WHERE user_id = ?",
            (reason, datetime.datetime.now(), admin_id, user_id)
        )
        
        # Логируем
        self.cursor.execute('''
            INSERT INTO moderation (chat_id, user_id, admin_id, action, reason, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (0, user_id, admin_id, "ban", reason, datetime.datetime.now()))
        
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
    
    # ========== МЕТОДЫ ДЛЯ ТРИГГЕРОВ (IRIS) ==========
    
    def add_trigger(self, chat_id: int, trigger_word: str, response: str, created_by: int):
        self.cursor.execute('''
            INSERT INTO triggers (chat_id, trigger_word, response, created_by, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (chat_id, trigger_word.lower(), response, created_by, datetime.datetime.now()))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_triggers(self, chat_id: int) -> List[Tuple]:
        self.cursor.execute("SELECT * FROM triggers WHERE chat_id = ? ORDER BY created_at", (chat_id,))
        return self.cursor.fetchall()
    
    def check_trigger(self, chat_id: int, text: str) -> Optional[str]:
        self.cursor.execute(
            "SELECT response FROM triggers WHERE chat_id = ? AND ? LIKE '%' || trigger_word || '%'",
            (chat_id, text.lower())
        )
        result = self.cursor.fetchone()
        return result[0] if result else None
    
    def remove_trigger(self, trigger_id: int):
        self.cursor.execute("DELETE FROM triggers WHERE id = ?", (trigger_id,))
        self.conn.commit()
    
    # ========== МЕТОДЫ ДЛЯ НАСТРОЕК ЧАТА ==========
    
    def get_chat_settings(self, chat_id: int) -> Dict:
        self.cursor.execute("SELECT * FROM chat_settings WHERE chat_id = ?", (chat_id,))
        settings = self.cursor.fetchone()
        
        if not settings:
            self.cursor.execute("INSERT INTO chat_settings (chat_id) VALUES (?)", (chat_id,))
            self.conn.commit()
            return self.get_chat_settings(chat_id)
        
        columns = [description[0] for description in self.cursor.description]
        return dict(zip(columns, settings))
    
    def set_rules(self, chat_id: int, rules: str):
        self.cursor.execute(
            "INSERT OR REPLACE INTO chat_settings (chat_id, rules) VALUES (?, ?)",
            (chat_id, rules)
        )
        self.conn.commit()
    
    def get_rules(self, chat_id: int) -> str:
        settings = self.get_chat_settings(chat_id)
        return settings.get('rules', 'Правила не установлены')
    
    def set_welcome(self, chat_id: int, message: str):
        self.cursor.execute(
            "UPDATE chat_settings SET welcome_message = ? WHERE chat_id = ?",
            (message, chat_id)
        )
        self.conn.commit()
    
    def get_welcome(self, chat_id: int) -> Optional[str]:
        settings = self.get_chat_settings(chat_id)
        return settings.get('welcome_message')
    
    # ========== МЕТОДЫ ДЛЯ МАФИИ (TRUEMAFIA) ==========
    
    def create_mafia_game(self, creator_id: int) -> int:
        self.cursor.execute('''
            INSERT INTO mafia_games (creator_id, players, votes, killed, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (creator_id, json.dumps([creator_id]), json.dumps({}), json.dumps([]), datetime.datetime.now()))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def join_mafia_game(self, game_id: int, user_id: int) -> bool:
        self.cursor.execute("SELECT players, status FROM mafia_games WHERE id = ?", (game_id,))
        result = self.cursor.fetchone()
        if not result or result[1] != 'waiting':
            return False
        
        players = json.loads(result[0])
        if user_id in players or len(players) >= 10:
            return False
        
        players.append(user_id)
        self.cursor.execute("UPDATE mafia_games SET players = ? WHERE id = ?", (json.dumps(players), game_id))
        self.conn.commit()
        return True
    
    def leave_mafia_game(self, game_id: int, user_id: int) -> bool:
        self.cursor.execute("SELECT players, creator_id FROM mafia_games WHERE id = ?", (game_id,))
        result = self.cursor.fetchone()
        if not result:
            return False
        
        players = json.loads(result[0])
        creator_id = result[1]
        
        if user_id not in players:
            return False
        
        players.remove(user_id)
        
        # Если создатель выходит, делаем нового создателя
        if user_id == creator_id and players:
            creator_id = players[0]
        
        self.cursor.execute(
            "UPDATE mafia_games SET players = ?, creator_id = ? WHERE id = ?",
            (json.dumps(players), creator_id, game_id)
        )
        self.conn.commit()
        return True
    
    def get_mafia_game(self, game_id: int) -> Optional[Dict]:
        self.cursor.execute("SELECT * FROM mafia_games WHERE id = ?", (game_id,))
        row = self.cursor.fetchone()
        if not row:
            return None
        
        columns = [description[0] for description in self.cursor.description]
        return dict(zip(columns, row))
    
    def get_active_mafia_games(self):
        self.cursor.execute("SELECT * FROM mafia_games WHERE status IN ('waiting', 'playing') ORDER BY created_at DESC")
        return self.cursor.fetchall()
    
    def start_mafia_game(self, game_id: int) -> Optional[Dict]:
        game = self.get_mafia_game(game_id)
        if not game or game['status'] != 'waiting':
            return None
        
        players = json.loads(game['players'])
        if len(players) < 5:
            return None
        
        random.shuffle(players)
        
        # Распределение ролей
        roles = {}
        mafia_count = max(1, len(players) // 3)
        sheriff_count = 1 if len(players) >= 6 else 0
        doctor_count = 1 if len(players) >= 7 else 0
        
        # Назначаем мафию
        for i in range(mafia_count):
            roles[str(players[i])] = 'mafia'
        
        # Назначаем шерифа
        if sheriff_count:
            for player in players[mafia_count:]:
                if str(player) not in roles:
                    roles[str(player)] = 'sheriff'
                    break
        
        # Назначаем доктора
        if doctor_count:
            for player in players[mafia_count:]:
                if str(player) not in roles:
                    roles[str(player)] = 'doctor'
                    break
        
        # Остальные мирные
        for player in players:
            if str(player) not in roles:
                roles[str(player)] = 'civilian'
        
        self.cursor.execute('''
            UPDATE mafia_games SET status = 'playing', roles = ?, phase = 'night', day_count = 1
            WHERE id = ?
        ''', (json.dumps(roles), game_id))
        self.conn.commit()
        
        return {
            'players': players,
            'roles': roles,
            'mafia_count': mafia_count,
            'sheriff_count': sheriff_count,
            'doctor_count': doctor_count
        }
    
    def mafia_night_action(self, game_id: int, mafia_kill: int = None, doctor_save: int = None, sheriff_check: int = None) -> Dict:
        game = self.get_mafia_game(game_id)
        if not game or game['phase'] != 'night':
            return {'success': False, 'reason': 'not_night'}
        
        killed = json.loads(game.get('killed', '[]'))
        votes = json.loads(game.get('votes', '{}'))
        
        # Мафия убивает
        if mafia_kill:
            killed.append(mafia_kill)
        
        # Доктор спасает (отменяет убийство)
        if doctor_save and doctor_save in killed:
            killed.remove(doctor_save)
        
        # Шериф проверяет
        sheriff_result = None
        if sheriff_check:
            roles = json.loads(game['roles'])
            sheriff_result = roles.get(str(sheriff_check)) == 'mafia'
        
        # Переходим в день
        self.cursor.execute('''
            UPDATE mafia_games SET phase = 'day', killed = ?, votes = ?
            WHERE id = ?
        ''', (json.dumps(killed), json.dumps(votes), game_id))
        self.conn.commit()
        
        return {
            'success': True,
            'killed': killed,
            'sheriff_result': sheriff_result,
            'day': game['day_count']
        }
    
    def mafia_day_vote(self, game_id: int, voter_id: int, target_id: int) -> Dict:
        game = self.get_mafia_game(game_id)
        if not game or game['phase'] != 'day':
            return {'success': False, 'reason': 'not_day'}
        
        votes = json.loads(game.get('votes', '{}'))
        votes[str(voter_id)] = target_id
        
        self.cursor.execute("UPDATE mafia_games SET votes = ? WHERE id = ?", (json.dumps(votes), game_id))
        self.conn.commit()
        
        return {'success': True, 'votes': votes}
    
    def mafia_end_day(self, game_id: int) -> Dict:
        game = self.get_mafia_game(game_id)
        if not game or game['phase'] != 'day':
            return {'success': False, 'reason': 'not_day'}
        
        votes = json.loads(game.get('votes', '{}'))
        killed = json.loads(game.get('killed', '[]'))
        
        # Подсчет голосов
        vote_count = {}
        for target in votes.values():
            vote_count[target] = vote_count.get(target, 0) + 1
        
        # Казнь
        executed = None
        if vote_count:
            max_votes = max(vote_count.values())
            candidates = [p for p, v in vote_count.items() if v == max_votes]
            if len(candidates) == 1:
                executed = candidates[0]
                killed.append(executed)
        
        # Проверка на окончание игры
        roles = json.loads(game['roles'])
        players = json.loads(game['players'])
        
        alive = [p for p in players if p not in killed]
        alive_mafia = sum(1 for p in alive if roles.get(str(p)) == 'mafia')
        alive_civilians = len(alive) - alive_mafia
        
        game_over = False
        winner = None
        
        if alive_mafia == 0:
            game_over = True
            winner = 'civilians'
        elif alive_mafia >= alive_civilians:
            game_over = True
            winner = 'mafia'
        
        if game_over:
            self.cursor.execute("UPDATE mafia_games SET status = 'finished', killed = ? WHERE id = ?", (json.dumps(killed), game_id))
        else:
            self.cursor.execute('''
                UPDATE mafia_games SET phase = 'night', day_count = day_count + 1, killed = ?, votes = ?
                WHERE id = ?
            ''', (json.dumps(killed), json.dumps({}), game_id))
        
        self.conn.commit()
        
        return {
            'success': True,
            'executed': executed,
            'killed': killed,
            'game_over': game_over,
            'winner': winner
        }
    
    # ========== МЕТОДЫ ДЛЯ КЛАНОВ ==========
    
    def create_clan(self, name: str, owner_id: int) -> Optional[int]:
        try:
            self.cursor.execute('''
                INSERT INTO clans (name, owner_id, created_at)
                VALUES (?, ?, ?)
            ''', (name, owner_id, datetime.datetime.now()))
            clan_id = self.cursor.lastrowid
            
            self.cursor.execute('''
                INSERT INTO clan_members (clan_id, user_id, role, joined_at)
                VALUES (?, ?, ?, ?)
            ''', (clan_id, owner_id, 'owner', datetime.datetime.now()))
            
            self.cursor.execute("UPDATE users SET clan_id = ? WHERE user_id = ?", (clan_id, owner_id))
            self.conn.commit()
            return clan_id
        except:
            return None
    
    def get_clan(self, clan_id: int) -> Optional[Tuple]:
        self.cursor.execute("SELECT * FROM clans WHERE id = ?", (clan_id,))
        return self.cursor.fetchone()
    
    def get_user_clan(self, user_id: int) -> Optional[Tuple]:
        self.cursor.execute("SELECT clan_id FROM users WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()
        if result and result[0]:
            return self.get_clan(result[0])
        return None
    
    def get_clan_members(self, clan_id: int) -> List[Tuple]:
        self.cursor.execute('''
            SELECT u.user_id, u.first_name, u.nickname, u.level, cm.role, cm.joined_at
            FROM clan_members cm
            JOIN users u ON cm.user_id = u.user_id
            WHERE cm.clan_id = ?
            ORDER BY cm.role = 'owner' DESC, cm.joined_at
        ''', (clan_id,))
        return self.cursor.fetchall()
    
    def join_clan(self, user_id: int, clan_id: int) -> bool:
        if self.get_user_clan(user_id):
            return False
        
        clan = self.get_clan(clan_id)
        if not clan or clan[5] >= 50:
            return False
        
        self.cursor.execute('''
            INSERT INTO clan_members (clan_id, user_id, role, joined_at)
            VALUES (?, ?, ?, ?)
        ''', (clan_id, user_id, 'member', datetime.datetime.now()))
        
        self.cursor.execute("UPDATE users SET clan_id = ? WHERE user_id = ?", (clan_id, user_id))
        self.cursor.execute("UPDATE clans SET members = members + 1 WHERE id = ?", (clan_id,))
        self.conn.commit()
        return True
    
    def leave_clan(self, user_id: int) -> bool:
        clan = self.get_user_clan(user_id)
        if not clan:
            return False
        
        if clan[2] == user_id:
            # Владелец передает права или распускает клан
            members = self.get_clan_members(clan[0])
            if len(members) == 1:
                # Распускаем клан
                self.cursor.execute("DELETE FROM clans WHERE id = ?", (clan[0],))
                self.cursor.execute("DELETE FROM clan_members WHERE clan_id = ?", (clan[0],))
            else:
                # Передаем права следующему
                next_owner = members[1][0]
                self.cursor.execute("UPDATE clan_members SET role = 'owner' WHERE clan_id = ? AND user_id = ?", (clan[0], next_owner))
                self.cursor.execute("UPDATE clans SET owner_id = ? WHERE id = ?", (next_owner, clan[0]))
                self.cursor.execute("DELETE FROM clan_members WHERE clan_id = ? AND user_id = ?", (clan[0], user_id))
                self.cursor.execute("UPDATE clans SET members = members - 1 WHERE id = ?", (clan[0],))
        else:
            self.cursor.execute("DELETE FROM clan_members WHERE clan_id = ? AND user_id = ?", (clan[0], user_id))
            self.cursor.execute("UPDATE clans SET members = members - 1 WHERE id = ?", (clan[0],))
        
        self.cursor.execute("UPDATE users SET clan_id = 0 WHERE user_id = ?", (user_id,))
        self.conn.commit()
        return True
    
    def add_clan_exp(self, clan_id: int, exp: int):
        self.cursor.execute("UPDATE clans SET exp = exp + ? WHERE id = ?", (exp, clan_id))
        
        self.cursor.execute("SELECT exp, level FROM clans WHERE id = ?", (clan_id,))
        clan = self.cursor.fetchone()
        if clan:
            exp_needed = clan[1] * 500
            if clan[0] >= exp_needed:
                self.cursor.execute("UPDATE clans SET level = level + 1, exp = exp - ? WHERE id = ?", (exp_needed, clan_id))
        
        self.conn.commit()
    
    def get_top_clans(self, limit: int = 10):
        self.cursor.execute("SELECT name, level, members, rating FROM clans ORDER BY rating DESC, level DESC LIMIT ?", (limit,))
        return self.cursor.fetchall()
    
    # ========== МЕТОДЫ ДЛЯ БОССОВ ==========
    
    def get_bosses(self, alive_only: bool = True):
        if alive_only:
            self.cursor.execute("SELECT * FROM bosses WHERE is_alive = 1 ORDER BY boss_level")
        else:
            self.cursor.execute("SELECT * FROM bosses ORDER BY boss_level")
        return self.cursor.fetchall()
    
    def get_boss(self, boss_id: int):
        self.cursor.execute("SELECT * FROM bosses WHERE id = ?", (boss_id,))
        return self.cursor.fetchone()
    
    def damage_boss(self, boss_id: int, damage: int) -> bool:
        self.cursor.execute("UPDATE bosses SET boss_health = boss_health - ? WHERE id = ?", (damage, boss_id))
        self.conn.commit()
        
        self.cursor.execute("SELECT boss_health FROM bosses WHERE id = ?", (boss_id,))
        health = self.cursor.fetchone()[0]
        
        if health <= 0:
            self.cursor.execute("UPDATE bosses SET is_alive = 0 WHERE id = ?", (boss_id,))
            self.conn.commit()
            return True
        return False
    
    def respawn_bosses(self):
        self.cursor.execute("UPDATE bosses SET is_alive = 1, boss_health = boss_max_health")
        self.conn.commit()
    
    def add_boss_kill(self, user_id: int):
        self.cursor.execute("UPDATE users SET boss_kills = boss_kills + 1 WHERE user_id = ?", (user_id,))
        self.conn.commit()
    
    # ========== МЕТОДЫ ДЛЯ ДОСТИЖЕНИЙ ==========
    
    def add_achievement(self, user_id: int, name: str, desc: str, reward: int = 0) -> bool:
        try:
            self.cursor.execute('''
                INSERT INTO achievements (user_id, achievement_name, achievement_desc, earned_date, reward_coins)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, name, desc, datetime.datetime.now(), reward))
            
            if reward > 0:
                self.add_coins(user_id, reward)
            
            self.conn.commit()
            return True
        except:
            return False
    
    def get_achievements(self, user_id: int) -> List[Tuple]:
        self.cursor.execute("SELECT achievement_name, achievement_desc, earned_date, reward_coins FROM achievements WHERE user_id = ? ORDER BY earned_date DESC", (user_id,))
        return self.cursor.fetchall()
    
    # ========== МЕТОДЫ ДЛЯ ДОЛГОВ ==========
    
    def create_debt(self, debtor_id: int, creditor_id: int, amount: int, reason: str, days: int = 30) -> int:
        deadline = datetime.datetime.now() + datetime.timedelta(days=days)
        self.cursor.execute('''
            INSERT INTO debts (debtor_id, creditor_id, amount, reason, created_at, deadline)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (debtor_id, creditor_id, amount, reason, datetime.datetime.now(), deadline))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_debts(self, user_id: int) -> List[Tuple]:
        self.cursor.execute('''
            SELECT * FROM debts WHERE (debtor_id = ? OR creditor_id = ?) AND is_paid = 0 ORDER BY deadline
        ''', (user_id, user_id))
        return self.cursor.fetchall()
    
    def pay_debt(self, debt_id: int):
        self.cursor.execute("UPDATE debts SET is_paid = 1 WHERE id = ?", (debt_id,))
        self.conn.commit()
    
    # ========== МЕТОДЫ ДЛЯ БОНУСОВ ==========
    
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
    
    def can_claim_weekly(self, user_id: int) -> bool:
        self.cursor.execute("SELECT last_weekly FROM users WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()
        if not result or not result[0]:
            return True
        
        last = datetime.datetime.fromisoformat(result[0])
        return (datetime.datetime.now() - last).days >= 7
    
    def claim_weekly(self, user_id: int):
        self.cursor.execute("UPDATE users SET last_weekly = ? WHERE user_id = ?", (datetime.datetime.now(), user_id))
        self.conn.commit()
    
    def close(self):
        self.conn.close()

# Инициализация БД
db = Database() 

# ========== GEMINI AI (КАК В ANYA) ==========
class GeminiAI:
    """Полноценный AI с памятью и контекстом"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
        self.session = None
        self.contexts = defaultdict(list)
        self.max_context_length = 10
        self.system_prompt = (
            "Ты — СПЕКТР, дружелюбный и умный бот-помощник. "
            "Ты объединяешь в себе функции чат-менеджера (как Iris), "
            "ведущего игры в мафию (как TrueMafia), экономического бота (как TReanfer) "
            "и просто собеседника (как Anya). "
            "Отвечай кратко, но информативно, используй эмодзи. "
            "Помогай пользователям с командами, играми и настройками. "
            "Будь вежливым и дружелюбным."
        )
        print("🤖 Gemini AI (Anya style) инициализирован")

    async def get_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session

    async def get_response(self, user_id: int, message: str) -> str:
        try:
            session = await self.get_session()

            if user_id not in self.contexts:
                self.contexts[user_id] = [
                    {"role": "user", "parts": [{"text": self.system_prompt}]},
                    {"role": "model", "parts": [{"text": "Привет! Я СПЕКТР, твой помощник. Чем могу помочь?"}]}
                ]

            self.contexts[user_id].append({"role": "user", "parts": [{"text": message}]})

            if len(self.contexts[user_id]) > self.max_context_length:
                self.contexts[user_id] = [self.contexts[user_id][0]] + self.contexts[user_id][-self.max_context_length+1:]

            data = {
                "contents": self.contexts[user_id],
                "generationConfig": {
                    "temperature": 0.8,
                    "maxOutputTokens": 300,
                    "topP": 0.95,
                    "topK": 40
                }
            }

            async with session.post(self.api_url, json=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    try:
                        response = result["candidates"][0]["content"]["parts"][0]["text"]
                        self.contexts[user_id].append({"role": "model", "parts": [{"text": response}]})
                        return response
                    except Exception as e:
                        print(f"Ошибка парсинга Gemini: {e}")
                        return self.get_fallback_response(message)
                else:
                    error_text = await resp.text()
                    print(f"Ошибка Gemini API: {resp.status} - {error_text[:200]}")
                    return self.get_fallback_response(message)

        except asyncio.TimeoutError:
            return "⏱️ Превышено время ожидания. Попробуйте еще раз."
        except Exception as e:
            print(f"Ошибка Gemini: {e}")
            return self.get_fallback_response(message)

    def get_fallback_response(self, message: str) -> str:
        """Умные запасные ответы"""
        msg = message.lower()
        
        # Приветствия
        if any(word in msg for word in ["привет", "здравствуй", "хай", "ку", "здаров"]):
            return "👋 Привет! Как дела? Чем могу помочь сегодня?"
        
        # Как дела
        if any(word in msg for word in ["как дела", "как ты", "чё как", "чо как"]):
            return "😊 Всё отлично! Работаю, помогаю игрокам. А у тебя как?"
        
        # Спасибо
        if any(word in msg for word in ["спасибо", "благодарю", "пасиб", "спс"]):
            return "🤝 Всегда пожалуйста! Рад помочь."
        
        # Кто создал
        if any(word in msg for word in ["кто создал", "создатель", "владелец", "твой папа"]):
            return f"👑 Мой создатель: {OWNER_USERNAME}"
        
        # Команды
        if any(word in msg for word in ["команды", "что умеешь", "помощь"]):
            return "📚 Я умею многое! Напиши /help для полного списка команд.\n🔹 Модерация (как Iris)\n🔹 Мафия (как TrueMafia)\n🔹 Экономика (как TReanfer)\n🔹 Игры и развлечения\n🔹 И просто поболтать!"
        
        # Игры
        if any(word in msg for word in ["игра", "поиграть", "во что"]):
            return "🎮 У меня есть:\n👾 Боссы (/bosses)\n🎰 Казино (/casino)\n✊ КНБ (/rps)\n🔪 Мафия (/mafia)\n⭕ Крестики-нолики (/ttt)\n💣 Сапёр (/minesweeper)\n🧠 Мемори (/memory)"
        
        # Боссы
        if any(word in msg for word in ["босс", "битва"]):
            return "👾 Боссы ждут тебя на арене! Используй /bosses для просмотра и /bossfight [ID] для битвы."
        
        # Казино
        if any(word in msg for word in ["казино", "рулетка", "кости"]):
            return "🎰 В казино тебя ждут: рулетка, кости, слоты и КНБ! Напиши /casino для подробностей."
        
        # Экономика
        if any(word in msg for word in ["деньги", "монеты", "экономика"]):
            return "💰 У нас есть полноценная экономика! Зарабатывай монеты в играх, покупай предметы в /shop, получай /daily бонусы и становись богаче!"
        
        # Привилегии
        if any(word in msg for word in ["донат", "привилегии", "vip", "premium"]):
            return "💎 Хочешь больше возможностей? Посмотри /donate! VIP, PREMIUM и другие статусы ждут тебя."
        
        # Мафия
        if any(word in msg for word in ["мафия", "mafia"]):
            return "🔪 Хочешь сыграть в мафию? Создай игру командой /mafia_create, пригласи друзей и начните расследование!"
        
        # По умолчанию
        responses = [
            "🤔 Интересно... Расскажи подробнее!",
            "😊 Понял, продолжай.",
            "✨ Я внимательно слушаю.",
            "💡 Кстати, у меня есть много игр! Напиши /games",
            "🎯 Принято. Что дальше?",
            "🔥 Отлично! Есть что-то ещё?"
        ]
        return random.choice(responses)

    async def close(self):
        if self.session:
            await self.session.close()

ai = GeminiAI(GEMINI_API_KEY)

# ========== ОСНОВНОЙ КЛАСС БОТА (НАЧАЛО) ==========
class SpectrumBot:
    def __init__(self):
        self.db = db
        self.ai = ai
        self.spam_tracker = defaultdict(list)
        self.active_games = {}  # Для хранения активных игр (КНБ, ТТТ, и т.д.)
        self.mafia_games = {}   # Для кэширования игр в мафию
        self.application = Application.builder().token(TELEGRAM_TOKEN).build()
        self.setup_handlers()
        print("✅ Мега-бот «СПЕКТР» (объединённый) инициализирован")

    def setup_handlers(self):
        """Регистрация всех обработчиков команд"""
        
        # ===== БАЗОВЫЕ КОМАНДЫ =====
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        self.application.add_handler(CommandHandler("menu", self.cmd_menu))
        
        # ===== ПРОФИЛЬ И СТАТИСТИКА =====
        self.application.add_handler(CommandHandler("profile", self.cmd_profile))
        self.application.add_handler(CommandHandler("editprofile", self.cmd_edit_profile))
        self.application.add_handler(CommandHandler("top", self.cmd_top))
        self.application.add_handler(CommandHandler("stats", self.cmd_stats))
        
        # ===== МОДУЛЬ МОДЕРАЦИИ (IRIS) =====
        # Управление рангами
        self.application.add_handler(CommandHandler("rank", self.cmd_rank))
        self.application.add_handler(CommandHandler("setrank", self.cmd_set_rank))
        self.application.add_handler(CommandHandler("ranks", self.cmd_ranks_list))
        
        # Предупреждения
        self.application.add_handler(CommandHandler("warn", self.cmd_warn))
        self.application.add_handler(CommandHandler("warns", self.cmd_warns))
        self.application.add_handler(CommandHandler("mywarns", self.cmd_my_warns))
        self.application.add_handler(CommandHandler("unwarn", self.cmd_unwarn))
        self.application.add_handler(CommandHandler("unwarnall", self.cmd_unwarn_all))
        
        # Мут
        self.application.add_handler(CommandHandler("mute", self.cmd_mute))
        self.application.add_handler(CommandHandler("unmute", self.cmd_unmute))
        self.application.add_handler(CommandHandler("mutelist", self.cmd_mutelist))
        self.application.add_handler(CommandHandler("checkmute", self.cmd_check_mute))
        
        # Бан
        self.application.add_handler(CommandHandler("ban", self.cmd_ban))
        self.application.add_handler(CommandHandler("unban", self.cmd_unban))
        self.application.add_handler(CommandHandler("banlist", self.cmd_banlist))
        self.application.add_handler(CommandHandler("banreason", self.cmd_ban_reason))
        self.application.add_handler(CommandHandler("kick", self.cmd_kick))
        self.application.add_handler(CommandHandler("amnesty", self.cmd_amnesty))
        
        # Настройки чата
        self.application.add_handler(CommandHandler("rules", self.cmd_rules))
        self.application.add_handler(CommandHandler("setrules", self.cmd_set_rules))
        self.application.add_handler(CommandHandler("welcome", self.cmd_welcome))
        self.application.add_handler(CommandHandler("setwelcome", self.cmd_set_welcome))
        self.application.add_handler(CommandHandler("goodbye", self.cmd_goodbye))
        self.application.add_handler(CommandHandler("setgoodbye", self.cmd_set_goodbye))
        
        # Триггеры
        self.application.add_handler(CommandHandler("trigger", self.cmd_trigger))
        self.application.add_handler(CommandHandler("addtrigger", self.cmd_add_trigger))
        self.application.add_handler(CommandHandler("triggers", self.cmd_list_triggers))
        self.application.add_handler(CommandHandler("deltrigger", self.cmd_del_trigger))
        
        # ===== МОДУЛЬ МАФИИ (TRUEMAFIA) =====
        self.application.add_handler(CommandHandler("mafia", self.cmd_mafia))
        self.application.add_handler(CommandHandler("mafiacreate", self.cmd_mafia_create))
        self.application.add_handler(CommandHandler("mafiajoin", self.cmd_mafia_join))
        self.application.add_handler(CommandHandler("mafialeave", self.cmd_mafia_leave))
        self.application.add_handler(CommandHandler("mafiastart", self.cmd_mafia_start))
        self.application.add_handler(CommandHandler("mafialist", self.cmd_mafia_list))
        self.application.add_handler(CommandHandler("mafiavote", self.cmd_mafia_vote))
        self.application.add_handler(CommandHandler("mafianight", self.cmd_mafia_night_action))
        self.application.add_handler(CommandHandler("mafiaday", self.cmd_mafia_day_vote))
        self.application.add_handler(CommandHandler("mafiastats", self.cmd_mafia_stats))
        
        # ===== МОДУЛЬ ЭКОНОМИКИ (TREANFER + ТВОЙ) =====
        self.application.add_handler(CommandHandler("shop", self.cmd_shop))
        self.application.add_handler(CommandHandler("buy", self.cmd_buy))
        self.application.add_handler(CommandHandler("inventory", self.cmd_inventory))
        self.application.add_handler(CommandHandler("use", self.cmd_use))
        self.application.add_handler(CommandHandler("pay", self.cmd_pay))
        self.application.add_handler(CommandHandler("paydiamond", self.cmd_pay_diamond))
        self.application.add_handler(CommandHandler("paycrystal", self.cmd_pay_crystal))
        self.application.add_handler(CommandHandler("daily", self.cmd_daily))
        self.application.add_handler(CommandHandler("weekly", self.cmd_weekly))
        self.application.add_handler(CommandHandler("streak", self.cmd_streak))
        
        # ===== МОДУЛЬ ПРИВИЛЕГИЙ =====
        self.application.add_handler(CommandHandler("donate", self.cmd_donate))
        self.application.add_handler(CommandHandler("vip", self.cmd_vip))
        self.application.add_handler(CommandHandler("premium", self.cmd_premium))
        self.application.add_handler(CommandHandler("lord", self.cmd_lord))
        self.application.add_handler(CommandHandler("ultra", self.cmd_ultra))
        self.application.add_handler(CommandHandler("moderator", self.cmd_buy_moderator))
        
        # ===== МОДУЛЬ КЛАНОВ =====
        self.application.add_handler(CommandHandler("clan", self.cmd_clan))
        self.application.add_handler(CommandHandler("clancreate", self.cmd_clan_create))
        self.application.add_handler(CommandHandler("clanjoin", self.cmd_clan_join))
        self.application.add_handler(CommandHandler("clanleave", self.cmd_clan_leave))
        self.application.add_handler(CommandHandler("clantop", self.cmd_clan_top))
        self.application.add_handler(CommandHandler("clanwar", self.cmd_clan_war))
        
        # ===== МОДУЛЬ БОССОВ (ТВОЙ) =====
        self.application.add_handler(CommandHandler("bosses", self.cmd_boss_list))
        self.application.add_handler(CommandHandler("boss", self.cmd_boss_info))
        self.application.add_handler(CommandHandler("bossfight", self.cmd_boss_fight))
        self.application.add_handler(CommandHandler("bossstats", self.cmd_boss_stats))
        self.application.add_handler(CommandHandler("regen", self.cmd_regen))
        
        # ===== МОДУЛЬ КАЗИНО =====
        self.application.add_handler(CommandHandler("casino", self.cmd_casino))
        self.application.add_handler(CommandHandler("roulette", self.cmd_roulette))
        self.application.add_handler(CommandHandler("dice", self.cmd_dice))
        self.application.add_handler(CommandHandler("blackjack", self.cmd_blackjack))
        self.application.add_handler(CommandHandler("slots", self.cmd_slots))
        
        # ===== МОДУЛЬ ИГР =====
        self.application.add_handler(CommandHandler("rps", self.cmd_rps))
        self.application.add_handler(CommandHandler("ttt", self.cmd_ttt))
        self.application.add_handler(CommandHandler("tttmove", self.cmd_ttt_move))
        self.application.add_handler(CommandHandler("memory", self.cmd_memory))
        self.application.add_handler(CommandHandler("memoryplay", self.cmd_memory_play))
        self.application.add_handler(CommandHandler("minesweeper", self.cmd_minesweeper))
        self.application.add_handler(CommandHandler("mineopen", self.cmd_mine_open))
        
        # ===== МОДУЛЬ ДОЛГОВ =====
        self.application.add_handler(CommandHandler("debt", self.cmd_debt))
        self.application.add_handler(CommandHandler("debts", self.cmd_debts))
        self.application.add_handler(CommandHandler("paydebt", self.cmd_pay_debt))
        
        # ===== МОДУЛЬ ДОСТИЖЕНИЙ =====
        self.application.add_handler(CommandHandler("achievements", self.cmd_achievements))
        
        # ===== ПРОЧИЕ КОМАНДЫ =====
        self.application.add_handler(CommandHandler("weather", self.cmd_weather))
        self.application.add_handler(CommandHandler("news", self.cmd_news))
        self.application.add_handler(CommandHandler("quote", self.cmd_quote))
        self.application.add_handler(CommandHandler("players", self.cmd_players))
        self.application.add_handler(CommandHandler("mycrime", self.cmd_mycrime))
        self.application.add_handler(CommandHandler("engfree", self.cmd_eng_free))
        self.application.add_handler(CommandHandler("sms", self.cmd_sms))
        
        # ===== ОБРАБОТЧИКИ СООБЩЕНИЙ =====
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, self.handle_new_members))
        self.application.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, self.handle_left_member))
        
        print(f"✅ Зарегистрировано 80+ обработчиков команд")

    def get_role_emoji(self, role: str) -> str:
        """Эмодзи для ролей"""
        emojis = {
            'owner': '👑',
            'admin': '⚜️',
            'moderator': '🛡️',
            'creator': '⭐',
            'ultra': '🦅',
            'lord': '🦀',
            'premium': '🐊',
            'vip': '🐛',
            'user': '👤'
        }
        return emojis.get(role, '👤')

    def get_rank_name(self, rank: int) -> str:
        """Название ранга модератора"""
        return RANK_NAMES.get(rank, f"Ранг {rank}")

    def has_permission(self, user_data: Dict, required_rank: int) -> bool:
        """Проверка прав (по рангам Iris)"""
        user_rank = user_data.get('rank', 0)
        return user_rank >= required_rank

    async def check_spam(self, update: Update) -> bool:
        """Проверка на спам"""
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)
        
        if self.has_permission(user_data, 1):  # Модераторы не проверяются
            return False
        
        current_time = time.time()
        self.spam_tracker[user_id] = [t for t in self.spam_tracker[user_id] if current_time - t < SPAM_WINDOW]
        self.spam_tracker[user_id].append(current_time)
        
        if len(self.spam_tracker[user_id]) > SPAM_LIMIT:
            self.db.mute_user(user_id, SPAM_MUTE_TIME, 0, "Автоматический спам")
            await update.message.reply_text(
                f.error(f"Спам-фильтр. Вы замучены на {SPAM_MUTE_TIME} минут."),
                parse_mode='Markdown'
            )
            self.spam_tracker[user_id] = []
            return True
        return False

    # ========== БАЗОВЫЕ КОМАНДЫ ==========
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        user = update.effective_user
        user_data = self.db.get_or_create_user("tg", str(user.id), user.first_name)
        
        text = (f.header("СПЕКТР МЕГА-БОТ", "⚡") + "\n\n"
                f"👋 **Привет, {user.first_name}!**\n\n"
                f"Я — объединённый бот, который вобрал в себя лучшее от:\n"
                f"{f.list_item('🛡️ Iris — полная модерация чатов')}\n"
                f"{f.list_item('🔪 TrueMafia — классическая мафия')}\n"
                f"{f.list_item('💰 TReanfer — экономика и донат')}\n"
                f"{f.list_item('🤖 Anya — умный AI с характером')}\n\n"
                
                f"{f.section('ТВОЙ ПРОФИЛЬ', '👤')}\n"
                f"{f.list_item('Монеты: ' + str(user_data.get('coins', 1000)) + ' 💰')}\n"
                f"{f.list_item('Алмазы: ' + str(user_data.get('diamonds', 0)) + ' 💎')}\n"
                f"{f.list_item('Кристаллы: ' + str(user_data.get('crystals', 0)) + ' 🔮')}\n"
                f"{f.list_item('Ранг: ' + self.get_rank_name(user_data.get('rank', 0)))}\n"
                f"{f.list_item('Уровень: ' + str(user_data.get('level', 1)))}\n\n"
                
                f"{f.section('БЫСТРЫЙ СТАРТ', '🚀')}\n"
                f"{f.command('menu', 'главное меню')}\n"
                f"{f.command('profile', 'твой профиль')}\n"
                f"{f.command('shop', 'магазин')}\n"
                f"{f.command('bosses', 'битва с боссами')}\n"
                f"{f.command('mafia', 'игра в мафию')}\n"
                f"{f.command('help', 'все команды')}\n\n"
                
                f"👑 **Владелец:** {OWNER_USERNAME}")
        
        await update.message.reply_text(
            text,
            reply_markup=IrisKeyboard.main_menu(),
            parse_mode='Markdown'
        )
        self.db.add_stat(user.id, "commands_used", 1)
    
    async def cmd_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Главное меню"""
        await update.message.reply_text(
            f.header("ГЛАВНОЕ МЕНЮ", "🎮") + "\n\nВыбери раздел:",
            reply_markup=IrisKeyboard.main_menu(),
            parse_mode='Markdown'
        )
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Полная справка по командам"""
        text = (f.header("ПОЛНАЯ СПРАВКА", "📚") + "\n\n"
                
                f"{f.section('👤 ПРОФИЛЬ')}\n"
                f"{f.command('profile', 'твой профиль')}\n"
                f"{f.command('editprofile', 'редактировать профиль')}\n"
                f"{f.command('stats', 'статистика игр')}\n"
                f"{f.command('top', 'топ игроков')}\n\n"
                
                f"{f.section('🛡️ МОДЕРАЦИЯ (Iris)')}\n"
                f"{f.command('rank [@user]', 'узнать ранг')}\n"
                f"{f.command('warn @user [причина]', 'выдать предупреждение')}\n"
                f"{f.command('warns @user', 'список предупреждений')}\n"
                f"{f.command('unwarn @user', 'снять предупреждение')}\n"
                f"{f.command('mute @user минут [причина]', 'заглушить')}\n"
                f"{f.command('unmute @user', 'снять мут')}\n"
                f"{f.command('ban @user [причина]', 'заблокировать')}\n"
                f"{f.command('unban @user', 'разблокировать')}\n"
                f"{f.command('banlist', 'список забаненных')}\n"
                f"{f.command('mutelist', 'список замученных')}\n"
                f"{f.command('kick @user', 'исключить из чата')}\n"
                f"{f.command('rules', 'правила чата')}\n"
                f"{f.command('setrules [текст]', 'установить правила')}\n"
                f"{f.command('welcome', 'приветствие чата')}\n"
                f"{f.command('setwelcome [текст]', 'установить приветствие')}\n"
                f"{f.command('trigger [слово] [ответ]', 'добавить триггер')}\n\n"
                
                f"{f.section('🔪 МАФИЯ (TrueMafia)')}\n"
                f"{f.command('mafia', 'информация о мафии')}\n"
                f"{f.command('mafiacreate', 'создать новую игру')}\n"
                f"{f.command('mafiajoin [ID]', 'присоединиться к игре')}\n"
                f"{f.command('mafialeave', 'покинуть игру')}\n"
                f"{f.command('mafialist', 'список активных игр')}\n"
                f"{f.command('mafiastart', 'начать игру')}\n"
                f"{f.command('mafiavote [@user]', 'проголосовать днём')}\n"
                f"{f.command('mafianight [убить] [спасти] [проверить]', 'ночные действия')}\n"
                f"{f.command('mafiastats', 'статистика игр')}\n\n"
                
                f"{f.section('💰 ЭКОНОМИКА (TReanfer)')}\n"
                f"{f.command('shop', 'магазин')}\n"
                f"{f.command('buy [название]', 'купить предмет')}\n"
                f"{f.command('inventory', 'инвентарь')}\n"
                f"{f.command('use [ID]', 'использовать предмет')}\n"
                f"{f.command('pay @user сумма', 'перевести монеты')}\n"
                f"{f.command('paydiamond @user сумма', 'перевести алмазы')}\n"
                f"{f.command('paycrystal @user сумма', 'перевести кристаллы')}\n"
                f"{f.command('daily', 'ежедневный бонус')}\n"
                f"{f.command('weekly', 'недельный бонус')}\n"
                f"{f.command('streak', 'текущий стрик')}\n\n"
                
                f"{f.section('👑 ПРИВИЛЕГИИ')}\n"
                f"{f.command('donate', 'информация о привилегиях')}\n"
                f"{f.command('vip', 'купить VIP (5000💰)')}\n"
                f"{f.command('premium', 'купить PREMIUM (15000💰)')}\n"
                f"{f.command('lord', 'купить LORD (30000💰)')}\n"
                f"{f.command('ultra', 'купить ULTRA (50000💰)')}\n\n"
                
                f"{f.section('👥 КЛАНЫ')}\n"
                f"{f.command('clan', 'информация о твоём клане')}\n"
                f"{f.command('clancreate [название]', 'создать клан')}\n"
                f"{f.command('clanjoin [ID]', 'вступить в клан')}\n"
                f"{f.command('clanleave', 'покинуть клан')}\n"
                f"{f.command('clantop', 'топ кланов')}\n\n"
                
                f"{f.section('👾 БОССЫ И БИТВЫ')}\n"
                f"{f.command('bosses', 'список боссов')}\n"
                f"{f.command('boss [ID]', 'информация о боссе')}\n"
                f"{f.command('bossfight [ID]', 'атаковать босса')}\n"
                f"{f.command('bossstats', 'статистика битв')}\n"
                f"{f.command('regen', 'восстановить ❤️ и ⚡')}\n\n"
                
                f"{f.section('🎰 КАЗИНО')}\n"
                f"{f.command('casino', 'меню казино')}\n"
                f"{f.command('roulette [ставка] [цвет]', 'рулетка')}\n"
                f"{f.command('dice [ставка]', 'кости')}\n"
                f"{f.command('blackjack [ставка]', 'блэкджек')}\n"
                f"{f.command('slots [ставка]', 'слоты')}\n\n"
                
                f"{f.section('🎮 ИГРЫ')}\n"
                f"{f.command('rps', 'камень-ножницы-бумага')}\n"
                f"{f.command('ttt', 'крестики-нолики')}\n"
                f"{f.command('tttmove [1-9]', 'сделать ход')}\n"
                f"{f.command('memory', 'мемори (найди пары)')}\n"
                f"{f.command('memoryplay [номер]', 'открыть карту')}\n"
                f"{f.command('minesweeper', 'сапёр')}\n"
                f"{f.command('mineopen [ряд] [колонка]', 'открыть клетку')}\n\n"
                
                f"{f.section('💰 ДОЛГИ')}\n"
                f"{f.command('debt @user сумма [причина]', 'дать в долг')}\n"
                f"{f.command('debts', 'список долгов')}\n"
                f"{f.command('paydebt [ID]', 'оплатить долг')}\n\n"
                
                f"{f.section('🏆 ДОСТИЖЕНИЯ')}\n"
                f"{f.command('achievements', 'твои достижения')}\n\n"
                
                f"{f.section('🌍 ПРОЧЕЕ')}\n"
                f"{f.command('weather [город]', 'погода')}\n"
                f"{f.command('news', 'новости бота')}\n"
                f"{f.command('quote', 'цитата дня')}\n"
                f"{f.command('players', 'количество игроков')}\n"
                f"{f.command('mycrime', 'случайная статья УК')}\n"
                f"{f.command('engfree', 'бесплатная энергия (раз/час)')}\n"
                f"{f.command('sms @user [текст]', 'личное сообщение')}\n\n"
                
                f"👑 **Владелец:** {OWNER_USERNAME}")
        
        await update.message.reply_text(
            text,
            reply_markup=IrisKeyboard.back_button(),
            parse_mode='Markdown'
        )

    # ========== ПРОФИЛЬ ==========
    
    async def cmd_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Профиль пользователя"""
        user = update.effective_user
        user_data = self.db.get_user_by_id(user.id)
        
        # Прогресс до следующего уровня
        current_exp = user_data.get('exp', 0)
        current_level = user_data.get('level', 1)
        exp_needed = current_level * 100
        exp_progress = f.progress(current_exp, exp_needed, 15)
        
        # Статус привилегий
        vip_status = "✅ VIP" if self.db.is_vip(user.id) else "❌ Нет"
        premium_status = "✅ PREMIUM" if self.db.is_premium(user.id) else "❌ Нет"
        
        # Предупреждения
        warns = user_data.get('warns', 0)
        warns_display = "🔴" * warns + "⚪" * (3 - warns)
        
        # Клан
        clan = self.db.get_user_clan(user.id)
        clan_name = clan[1] if clan else "Нет"
        
        text = (f.header("ПРОФИЛЬ ИГРОКА", "👤") + "\n\n"
                f"**{user_data.get('nickname') or user.first_name}** "
                f"{user_data.get('title', '')}\n"
                f"_{user_data.get('motto', 'Нет девиза')}_\n\n"
                
                f"{f.section('ХАРАКТЕРИСТИКИ', '📊')}\n"
                f"{f.stat('Уровень', str(current_level))}\n"
                f"{f.stat('Опыт', exp_progress)}\n"
                f"{f.stat('Монеты', f"{user_data.get('coins', 0):,} 💰".replace(',', ' '))}\n"
                f"{f.stat('Алмазы', f"{user_data.get('diamonds', 0):,} 💎".replace(',', ' '))}\n"
                f"{f.stat('Кристаллы', f"{user_data.get('crystals', 0):,} 🔮".replace(',', ' '))}\n\n"
                
                f"{f.section('БОЕВЫЕ', '⚔️')}\n"
                f"{f.stat('❤️ Здоровье', str(user_data.get('health', 100)) + '/100')}\n"
                f"{f.stat('⚔️ Урон', str(user_data.get('damage', 10)))}\n"
                f"{f.stat('🛡 Броня', str(user_data.get('armor', 0)))}\n"
                f"{f.stat('👾 Боссов убито', str(user_data.get('boss_kills', 0)))}\n\n"
                
                f"{f.section('СТАТУС', '💎')}\n"
                f"{f.list_item(vip_status)}\n"
                f"{f.list_item(premium_status)}\n"
                f"{f.list_item('Ранг: ' + self.get_rank_name(user_data.get('rank', 0)))}\n"
                f"{f.list_item('Клан: ' + clan_name)}\n"
                f"{f.list_item('Предупреждения: ' + warns_display)}\n"
                f"{f.list_item('Репутация: ' + str(user_data.get('rep', 0)) + ' ⭐')}\n\n"
                
                f"{f.section('СТАТИСТИКА ИГР', '🎮')}\n"
                f"{f.stat('РПС побед', str(user_data.get('rps_wins', 0)))}\n"
                f"{f.stat('Казино побед', str(user_data.get('casino_wins', 0)))}\n"
                f"{f.stat('Мафия побед', str(user_data.get('mafia_wins', 0)))}\n"
                f"{f.stat('TTT побед', str(user_data.get('ttt_wins', 0)))}\n"
                f"{f.stat('Мемори побед', str(user_data.get('memory_wins', 0)))}\n"
                f"{f.stat('Сапёр побед', str(user_data.get('mine_wins', 0)))}\n\n"
                
                f"{f.section('О СЕБЕ', 'ℹ️')}\n"
                f"{f.list_item('Пол: ' + user_data.get('gender', 'не указан'))}\n"
                f"{f.list_item('Город: ' + user_data.get('city', 'не указан'))}\n"
                f"{f.list_item('ID: ' + f.code(str(user.id)))}")
        
        keyboard = [
            [InlineKeyboardButton("✏️ РЕДАКТИРОВАТЬ", callback_data="edit_profile")],
            [InlineKeyboardButton("🔙 НАЗАД", callback_data="menu_back")]
        ]
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def cmd_edit_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Редактирование профиля"""
        text = (f.header("РЕДАКТИРОВАНИЕ ПРОФИЛЯ", "✏️") + "\n\n"
                f"{f.command('nick [ник]', 'установить ник')}\n"
                f"{f.command('title [титул]', 'установить титул')}\n"
                f"{f.command('motto [девиз]', 'установить девиз')}\n"
                f"{f.command('gender [м|ж|др]', 'установить пол')}\n"
                f"{f.command('city [город]', 'установить город')}\n"
                f"{f.command('bio [текст]', 'установить описание')}\n\n"
                f"{f.example('nick Spectr')}\n"
                f"{f.example('title Легенда')}\n"
                f"{f.example('motto Carpe diem')}\n"
                f"{f.example('gender м')}\n"
                f"{f.example('city Москва')}\n"
                f"{f.example('bio Люблю играть в мафию')}")
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Статистика игр"""
        user = update.effective_user
        user_data = self.db.get_user_by_id(user.id)
        
        text = (f.header("СТАТИСТИКА ИГР", "📊") + "\n\n"
                f"{f.section('✊ КНБ')}\n"
                f"{f.stat('Побед', str(user_data.get('rps_wins', 0)))}\n"
                f"{f.stat('Поражений', str(user_data.get('rps_losses', 0)))}\n"
                f"{f.stat('Ничьих', str(user_data.get('rps_draws', 0)))}\n\n"
                
                f"{f.section('🎰 КАЗИНО')}\n"
                f"{f.stat('Побед', str(user_data.get('casino_wins', 0)))}\n"
                f"{f.stat('Поражений', str(user_data.get('casino_losses', 0)))}\n\n"
                
                f"{f.section('🔪 МАФИЯ')}\n"
                f"{f.stat('Побед', str(user_data.get('mafia_wins', 0)))}\n"
                f"{f.stat('Игр', str(user_data.get('mafia_games', 0)))}\n\n"
                
                f"{f.section('⭕ КРЕСТИКИ-НОЛИКИ')}\n"
                f"{f.stat('Побед', str(user_data.get('ttt_wins', 0)))}\n"
                f"{f.stat('Поражений', str(user_data.get('ttt_losses', 0)))}\n"
                f"{f.stat('Ничьих', str(user_data.get('ttt_draws', 0)))}\n\n"
                
                f"{f.section('🧠 МЕМОРИ')}\n"
                f"{f.stat('Побед', str(user_data.get('memory_wins', 0)))}\n"
                f"{f.stat('Игр', str(user_data.get('memory_games', 0)))}\n\n"
                
                f"{f.section('💣 САПЁР')}\n"
                f"{f.stat('Побед', str(user_data.get('mine_wins', 0)))}\n"
                f"{f.stat('Игр', str(user_data.get('mine_games', 0)))}")
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_top(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Топ игроков"""
        top_coins = self.db.get_top("coins", 10)
        top_level = self.db.get_top("level", 10)
        top_boss = self.db.get_top("boss_kills", 10)
        
        text = f.header("ТОП ИГРОКОВ", "🏆") + "\n\n"
        
        text += f.section("ПО МОНЕТАМ", "💰") + "\n"
        for i, (name, value) in enumerate(top_coins, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
            text += f"{medal} **{i}.** {name} — {value:,} 💰\n".replace(',', ' ')
        
        text += f"\n{f.section('ПО УРОВНЮ', '📊')}\n"
        for i, (name, value) in enumerate(top_level, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
            text += f"{medal} **{i}.** {name} — {value} ур.\n"
        
        text += f"\n{f.section('ПО УБИЙСТВУ БОССОВ', '👾')}\n"
        for i, (name, value) in enumerate(top_boss, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
            text += f"{medal} **{i}.** {name} — {value} боссов\n"
        
        await update.message.reply_text(
            text,
            reply_markup=IrisKeyboard.back_button(),
            parse_mode='Markdown'
        )
    
    # ========== МОДУЛЬ МОДЕРАЦИИ (IRIS) ==========
    
    async def cmd_rank(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Узнать ранг пользователя"""
        target_id = update.effective_user.id
        target_name = update.effective_user.first_name
        
        if context.args:
            query = context.args[0]
            target_user = self.db.get_user_by_username(query)
            if target_user:
                target_id = target_user['user_id']
                target_name = target_user.get('first_name', 'Пользователь')
            else:
                await update.message.reply_text(f.error(f"Пользователь {query} не найден"))
                return
        
        user_data = self.db.get_user_by_id(target_id)
        rank = user_data.get('rank', 0)
        
        text = (f.header("ИНФОРМАЦИЯ О РАНГЕ", "🛡️") + "\n\n"
                f"{f.list_item('Пользователь: ' + target_name)}\n"
                f"{f.list_item('Ранг: ' + self.get_rank_name(rank))}\n"
                f"{f.list_item('Уровень доступа: ' + str(rank))}")
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_set_rank(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установить ранг пользователя (для админов)"""
        admin = update.effective_user
        admin_data = self.db.get_user_by_id(admin.id)
        
        if not self.has_permission(admin_data, 4):  # Только админы 4+ ранга
            await update.message.reply_text(f.error("Недостаточно прав"))
            return
        
        if len(context.args) < 2:
            await update.message.reply_text(f.error("Использование: /setrank @user [0-5]"))
            return
        
        query = context.args[0]
        try:
            new_rank = int(context.args[1])
            if new_rank < 0 or new_rank > 5:
                await update.message.reply_text(f.error("Ранг должен быть от 0 до 5"))
                return
        except:
            await update.message.reply_text(f.error("Неверный формат ранга"))
            return
        
        target_user = self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        self.db.set_user_rank(target_user['user_id'], new_rank, admin.id)
        
        text = (f.header("РАНГ ИЗМЕНЁН", "✅") + "\n\n"
                f"{f.list_item('Пользователь: ' + target_user.get('first_name', 'Пользователь'))}\n"
                f"{f.list_item('Новый ранг: ' + self.get_rank_name(new_rank))}\n"
                f"{f.list_item('Админ: ' + admin.first_name)}")
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_ranks_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список рангов"""
        text = (f.header("СИСТЕМА РАНГОВ", "🛡️") + "\n\n"
                f"{f.list_item('0 - 👤 Участник')}\n"
                f"{f.list_item('1 - 🛡️ Младший модератор')}\n"
                f"{f.list_item('2 - 🛡️ Старший модератор')}\n"
                f"{f.list_item('3 - ⚜️ Младший администратор')}\n"
                f"{f.list_item('4 - ⚜️ Старший администратор')}\n"
                f"{f.list_item('5 - 👑 Создатель')}\n\n"
                f"{f.info('Чем выше ранг, тем больше команд доступно')}")
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_warn(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выдать предупреждение"""
        admin = update.effective_user
        admin_data = self.db.get_user_by_id(admin.id)
        
        if not self.has_permission(admin_data, 1):  # Минимум младший модератор
            await update.message.reply_text(f.error("Недостаточно прав"))
            return
        
        if len(context.args) < 1:
            await update.message.reply_text(f.error("Использование: /warn @user [причина]"))
            return
        
        query = context.args[0]
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else "Нарушение"
        
        target_user = self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        result = self.db.add_warn(target_user['user_id'], admin.id, reason)
        
        text = (f.header("ПРЕДУПРЕЖДЕНИЕ", "⚠️") + "\n\n"
                f"{f.list_item('Пользователь: ' + target_user.get('first_name', 'Пользователь'))}\n"
                f"{f.list_item('Предупреждений: ' + str(result['warns_count']) + '/3')}\n"
                f"{f.list_item('Причина: ' + reason)}\n"
                f"{f.list_item('Админ: ' + admin.first_name)}")
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
        # Если набралось 3 варна - автоматический мут
        if result['warns_count'] >= 3:
            self.db.mute_user(target_user['user_id'], 1440, admin.id, "3 предупреждения")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f.warning(f"{target_user.get('first_name', 'Пользователь')} получил 3 варна и замучен на 24ч")
            )
    
    async def cmd_warns(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список предупреждений пользователя"""
        if not context.args:
            await update.message.reply_text(f.error("Укажите пользователя: /warns @user"))
            return
        
        query = context.args[0]
        target_user = self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        warns_list = self.db.get_warns(target_user['user_id'])
        name = target_user.get('first_name', 'Пользователь')
        
        if not warns_list:
            await update.message.reply_text(f.info(f"У {name} нет предупреждений"))
            return
        
        text = f.header(f"ПРЕДУПРЕЖДЕНИЯ: {name}", "📋") + "\n\n"
        
        for warn in warns_list:
            admin = self.db.get_user_by_id(warn['admin_id'])
            admin_name = admin.get('first_name', 'Система') if admin else 'Система'
            date = datetime.datetime.fromisoformat(warn['date']).strftime("%d.%m.%Y %H:%M")
            
            text += (f"**ID: {warn['id']}**\n"
                     f"{f.list_item('Причина: ' + warn['reason'])}\n"
                     f"{f.list_item('Админ: ' + admin_name)}\n"
                     f"{f.list_item('Дата: ' + date)}\n\n")
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_my_warns(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Мои предупреждения"""
        user_id = update.effective_user.id
        warns_list = self.db.get_warns(user_id)
        
        if not warns_list:
            await update.message.reply_text(f.info("У тебя нет предупреждений"))
            return
        
        text = f.header("ТВОИ ПРЕДУПРЕЖДЕНИЯ", "📋") + "\n\n"
        
        for warn in warns_list:
            admin = self.db.get_user_by_id(warn['admin_id'])
            admin_name = admin.get('first_name', 'Система') if admin else 'Система'
            date = datetime.datetime.fromisoformat(warn['date']).strftime("%d.%m.%Y %H:%M")
            
            text += (f"**ID: {warn['id']}**\n"
                     f"{f.list_item('Причина: ' + warn['reason'])}\n"
                     f"{f.list_item('Админ: ' + admin_name)}\n"
                     f"{f.list_item('Дата: ' + date)}\n\n")
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_unwarn(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Снять последнее предупреждение"""
        admin = update.effective_user
        admin_data = self.db.get_user_by_id(admin.id)
        
        if not self.has_permission(admin_data, 1):
            await update.message.reply_text(f.error("Недостаточно прав"))
            return
        
        if not context.args:
            await update.message.reply_text(f.error("Укажите пользователя: /unwarn @user"))
            return
        
        query = context.args[0]
        target_user = self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        removed = self.db.remove_last_warn(target_user['user_id'])
        name = target_user.get('first_name', 'Пользователь')
        
        if not removed:
            await update.message.reply_text(f.info(f"У {name} нет предупреждений"))
            return
        
        await update.message.reply_text(
            f.success(f"Последнее предупреждение снято с {name}"),
            parse_mode='Markdown'
        )
    
    async def cmd_unwarn_all(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Снять все предупреждения"""
        admin = update.effective_user
        admin_data = self.db.get_user_by_id(admin.id)
        
        if not self.has_permission(admin_data, 3):  # Минимум младший админ
            await update.message.reply_text(f.error("Недостаточно прав"))
            return
        
        if not context.args:
            await update.message.reply_text(f.error("Укажите пользователя: /unwarnall @user"))
            return
        
        query = context.args[0]
        target_user = self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        self.db.remove_all_warns(target_user['user_id'])
        name = target_user.get('first_name', 'Пользователь')
        
        await update.message.reply_text(
            f.success(f"Все предупреждения сняты с {name}"),
            parse_mode='Markdown'
        )
    
    async def cmd_mute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Заглушить пользователя"""
        admin = update.effective_user
        admin_data = self.db.get_user_by_id(admin.id)
        
        if not self.has_permission(admin_data, 1):
            await update.message.reply_text(f.error("Недостаточно прав"))
            return
        
        if len(context.args) < 2:
            await update.message.reply_text(f.error("Использование: /mute @user минут [причина]"))
            return
        
        query = context.args[0]
        try:
            minutes = int(context.args[1])
            reason = " ".join(context.args[2:]) if len(context.args) > 2 else "Нарушение"
        except:
            await update.message.reply_text(f.error("Неверный формат времени"))
            return
        
        target_user = self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        mute_until = self.db.mute_user(target_user['user_id'], minutes, admin.id, reason)
        name = target_user.get('first_name', 'Пользователь')
        
        until_str = mute_until.strftime("%d.%m.%Y %H:%M")
        
        text = (f.header("МУТ", "🔇") + "\n\n"
                f"{f.list_item('Пользователь: ' + name)}\n"
                f"{f.list_item('Срок: ' + str(minutes) + ' минут')}\n"
                f"{f.list_item('До: ' + until_str)}\n"
                f"{f.list_item('Причина: ' + reason)}\n"
                f"{f.list_item('Админ: ' + admin.first_name)}")
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_unmute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Снять мут"""
        admin = update.effective_user
        admin_data = self.db.get_user_by_id(admin.id)
        
        if not self.has_permission(admin_data, 1):
            await update.message.reply_text(f.error("Недостаточно прав"))
            return
        
        if not context.args:
            await update.message.reply_text(f.error("Укажите пользователя: /unmute @user"))
            return
        
        query = context.args[0]
        target_user = self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        if not self.db.is_muted(target_user['user_id']):
            await update.message.reply_text(f.info("Пользователь не в муте"))
            return
        
        self.db.unmute_user(target_user['user_id'])
        name = target_user.get('first_name', 'Пользователь')
        
        await update.message.reply_text(
            f.success(f"Мут снят с {name}"),
            parse_mode='Markdown'
        )
    
    async def cmd_mutelist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список замученных"""
        muted = self.db.get_muted_users()
        
        if not muted:
            await update.message.reply_text(f.info("Нет пользователей в муте"))
            return
        
        text = f.header("СПИСОК ЗАМУЧЕННЫХ", "🔇") + "\n\n"
        
        for user_id, name, mute_until in muted[:10]:
            if mute_until:
                until = datetime.datetime.fromisoformat(mute_until).strftime("%d.%m.%Y %H:%M")
            else:
                until = "неизвестно"
            
            text += f"{f.list_item(name + ' — до ' + until)}\n"
        
        await update.message.reply_text(
            text,
            reply_markup=IrisKeyboard.back_button(),
            parse_mode='Markdown'
        )
    
    async def cmd_check_mute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Проверить наличие мута"""
        if not context.args:
            await update.message.reply_text(f.error("Укажите пользователя: /checkmute @user"))
            return
        
        query = context.args[0]
        target_user = self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        name = target_user.get('first_name', 'Пользователь')
        
        if self.db.is_muted(target_user['user_id']):
            remaining = self.db.get_mute_time(target_user['user_id'])
            await update.message.reply_text(f.warning(f"{name} в муте. Осталось: {remaining}"))
        else:
            await update.message.reply_text(f.success(f"{name} не в муте"))
    
    async def cmd_ban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Заблокировать пользователя"""
        admin = update.effective_user
        admin_data = self.db.get_user_by_id(admin.id)
        
        if not self.has_permission(admin_data, 2):  # Минимум старший модератор
            await update.message.reply_text(f.error("Недостаточно прав"))
            return
        
        if len(context.args) < 1:
            await update.message.reply_text(f.error("Использование: /ban @user [причина]"))
            return
        
        query = context.args[0]
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else "Нарушение правил"
        
        target_user = self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        self.db.ban_user(target_user['user_id'], admin.id, reason)
        name = target_user.get('first_name', 'Пользователь')
        
        text = (f.header("БЛОКИРОВКА", "🔴") + "\n\n"
                f"{f.list_item('Пользователь: ' + name)}\n"
                f"{f.list_item('Причина: ' + reason)}\n"
                f"{f.list_item('Админ: ' + admin.first_name)}")
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_unban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Разблокировать пользователя"""
        admin = update.effective_user
        admin_data = self.db.get_user_by_id(admin.id)
        
        if not self.has_permission(admin_data, 2):
            await update.message.reply_text(f.error("Недостаточно прав"))
            return
        
        if not context.args:
            await update.message.reply_text(f.error("Укажите пользователя: /unban @user"))
            return
        
        query = context.args[0]
        target_user = self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        if not self.db.is_banned(target_user['user_id']):
            await update.message.reply_text(f.info("Пользователь не заблокирован"))
            return
        
        self.db.unban_user(target_user['user_id'])
        name = target_user.get('first_name', 'Пользователь')
        
        await update.message.reply_text(
            f.success(f"Блокировка снята с {name}"),
            parse_mode='Markdown'
        )
    
    async def cmd_banlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список забаненных"""
        page = 1
        if context.args and context.args[0].isdigit():
            page = int(context.args[0])
        
        bans, total = self.db.get_banlist(page)
        total_pages = (total + 9) // 10
        
        if not bans:
            await update.message.reply_text(f.info("Список заблокированных пуст"))
            return
        
        text = f.header("СПИСОК ЗАБЛОКИРОВАННЫХ", "📋") + "\n"
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
    
    async def cmd_ban_reason(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Причина бана"""
        if not context.args:
            await update.message.reply_text(f.error("Укажите пользователя: /banreason @user"))
            return
        
        query = context.args[0]
        target_user = self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        if not self.db.is_banned(target_user['user_id']):
            name = target_user.get('first_name', 'Пользователь')
            await update.message.reply_text(f.info(f"{name} не заблокирован"))
            return
        
        ban_info = self.db.get_ban_reason(target_user['user_id'])
        name = target_user.get('first_name', 'Пользователь')
        
        date = datetime.datetime.fromisoformat(ban_info['date']).strftime("%d.%m.%Y %H:%M") if ban_info['date'] else "неизвестно"
        
        text = (f.header("ПРИЧИНА БАНА", "🔴") + "\n\n"
                f"{f.list_item('Пользователь: ' + name)}\n"
                f"{f.list_item('Причина: ' + ban_info['reason'])}\n"
                f"{f.list_item('Дата: ' + date)}\n"
                f"{f.list_item('Админ: ' + ban_info['admin_name'])}")
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_kick(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Исключить пользователя"""
        admin = update.effective_user
        admin_data = self.db.get_user_by_id(admin.id)
        
        if not self.has_permission(admin_data, 1):
            await update.message.reply_text(f.error("Недостаточно прав"))
            return
        
        if not context.args:
            await update.message.reply_text(f.error("Использование: /kick @user [причина]"))
            return
        
        query = context.args[0]
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else "Без причины"
        
        target_user = self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        name = target_user.get('first_name', 'Пользователь')
        
        text = (f.header("ИСКЛЮЧЕНИЕ", "👢") + "\n\n"
                f"{f.list_item('Пользователь: ' + name)}\n"
                f"{f.list_item('Причина: ' + reason)}\n"
                f"{f.list_item('Админ: ' + admin.first_name)}")
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
        # Здесь код для исключения из чата
        try:
            await context.bot.ban_chat_member(update.effective_chat.id, target_user['user_id'])
            await context.bot.unban_chat_member(update.effective_chat.id, target_user['user_id'])
        except:
            pass
    
    async def cmd_amnesty(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Амнистия - разбанить всех"""
        admin = update.effective_user
        admin_data = self.db.get_user_by_id(admin.id)
        
        if not self.has_permission(admin_data, 4):  # Только старшие админы
            await update.message.reply_text(f.error("Недостаточно прав"))
            return
        
        # Получаем всех забаненных
        bans, _ = self.db.get_banlist(1, 1000)
        
        for ban in bans:
            self.db.unban_user(ban['user_id'])
        
        await update.message.reply_text(
            f.success(f"Амнистия проведена! Разбанено {len(bans)} пользователей."),
            parse_mode='Markdown'
        )
    
    # ========== МОДУЛЬ МАФИИ (TRUEMAFIA) ==========
    
    async def cmd_mafia(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о мафии"""
        text = (f.header("МАФИЯ", "🔪") + "\n\n"
                f"{f.section('ПРАВИЛА ИГРЫ')}\n"
                f"{f.list_item('Игроки делятся на мафию и мирных жителей')}\n"
                f"{f.list_item('Ночью мафия убивает, мирные спят')}\n"
                f"{f.list_item('Днём все обсуждают и голосуют за казнь')}\n"
                f"{f.list_item('Цель мафии - убить всех мирных')}\n"
                f"{f.list_item('Цель мирных - найти и казнить мафию')}\n\n"
                
                f"{f.section('РОЛИ')}\n"
                f"{f.list_item('🔪 Мафия - убивают ночью')}\n"
                f"{f.list_item('👮 Шериф - проверяет принадлежность к мафии')}\n"
                f"{f.list_item('💊 Доктор - спасает убитого')}\n"
                f"{f.list_item('👤 Мирный - ищет мафию днём')}\n\n"
                
                f"{f.section('КОМАНДЫ')}\n"
                f"{f.command('mafiacreate', 'создать новую игру')}\n"
                f"{f.command('mafiajoin [ID]', 'присоединиться к игре')}\n"
                f"{f.command('mafialist', 'список активных игр')}\n"
                f"{f.command('mafiastart', 'начать игру')}\n"
                f"{f.command('mafiavote @user', 'проголосовать днём')}\n"
                f"{f.command('mafianight [убить] [спасти] [проверить]', 'ночные действия')}")
        
        await update.message.reply_text(
            text,
            reply_markup=IrisKeyboard.mafia_game_menu(),
            parse_mode='Markdown'
        )
    
    async def cmd_mafia_create(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Создать игру в мафию"""
        user_id = update.effective_user.id
        
        # Проверяем, не участвует ли уже в игре
        active_games = self.db.get_active_mafia_games()
        for game in active_games:
            players = json.loads(game[4]) if isinstance(game[4], str) else []
            if user_id in players:
                await update.message.reply_text(f.error("Вы уже участвуете в игре!"))
                return
        
        game_id = self.db.create_mafia_game(user_id)
        
        text = (f.header("ИГРА СОЗДАНА", "🔪") + "\n\n"
                f"{f.list_item('ID игры: ' + str(game_id))}\n"
                f"{f.list_item('Создатель: ' + update.effective_user.first_name)}\n"
                f"{f.list_item('Игроков: 1/10')}\n"
                f"{f.list_item('Статус: ожидание игроков')}\n\n"
                f"Присоединиться: /mafiajoin {game_id}")
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_mafia_join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Присоединиться к игре"""
        if not context.args:
            await update.message.reply_text(f.error("Укажите ID игры: /mafiajoin 1"))
            return
        
        try:
            game_id = int(context.args[0])
        except:
            await update.message.reply_text(f.error("Неверный ID игры"))
            return
        
        game = self.db.get_mafia_game(game_id)
        if not game:
            await update.message.reply_text(f.error("Игра не найдена"))
            return
        
        if game['status'] != 'waiting':
            await update.message.reply_text(f.error("Игра уже началась"))
            return
        
        user_id = update.effective_user.id
        players = json.loads(game['players'])
        
        if user_id in players:
            await update.message.reply_text(f.error("Вы уже в игре"))
            return
        
        if len(players) >= 10:
            await update.message.reply_text(f.error("В игре максимальное количество игроков"))
            return
        
        if self.db.join_mafia_game(game_id, user_id):
            players.append(user_id)
            await update.message.reply_text(
                f.success(f"Вы присоединились к игре! Игроков: {len(players)}/10"),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(f.error("Не удалось присоединиться к игре"))
    
    async def cmd_mafia_leave(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Покинуть игру"""
        user_id = update.effective_user.id
        
        # Ищем игру, где участвует пользователь
        active_games = self.db.get_active_mafia_games()
        game_id = None
        
        for game in active_games:
            players = json.loads(game[4])
            if user_id in players:
                game_id = game[0]
                break
        
        if not game_id:
            await update.message.reply_text(f.error("Вы не участвуете ни в одной игре"))
            return
        
        if self.db.leave_mafia_game(game_id, user_id):
            await update.message.reply_text(f.success("Вы покинули игру"), parse_mode='Markdown')
        else:
            await update.message.reply_text(f.error("Не удалось покинуть игру"))
    
    async def cmd_mafia_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список активных игр"""
        games = self.db.get_active_mafia_games()
        
        if not games:
            await update.message.reply_text(f.info("Нет активных игр"))
            return
        
        text = f.header("АКТИВНЫЕ ИГРЫ", "📋") + "\n\n"
        
        for game in games:
            game_id, creator_id, status, players_str = game[0], game[1], game[2], game[4]
            players = json.loads(players_str) if isinstance(players_str, str) else []
            creator = self.db.get_user_by_id(creator_id)
            creator_name = creator.get('first_name', 'Неизвестно') if creator else 'Неизвестно'
            
            text += (f"**ID: {game_id}**\n"
                     f"└ Создатель: {creator_name}\n"
                     f"└ Статус: {'⏳ ожидание' if status == 'waiting' else '🔴 игра'}\n"
                     f"└ Игроков: {len(players)}/10\n\n")
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_mafia_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать игру"""
        user_id = update.effective_user.id
        
        # Ищем игру, созданную пользователем
        games = self.db.get_active_mafia_games()
        game_id = None
        
        for game in games:
            if game[1] == user_id and game[2] == 'waiting':
                game_id = game[0]
                break
        
        if not game_id:
            await update.message.reply_text(f.error("У вас нет созданных игр в ожидании"))
            return
        
        result = self.db.start_mafia_game(game_id)
        if not result:
            await update.message.reply_text(f.error("Не удалось начать игру (нужно минимум 5 игроков)"))
            return
        
        # Отправляем роли игрокам в личку
        game = self.db.get_mafia_game(game_id)
        players = json.loads(game['players'])
        roles = json.loads(game['roles'])
        
        for player_id in players:
            role = roles.get(str(player_id), 'civilian')
            role_emoji = {
                'mafia': '🔪 Мафия',
                'sheriff': '👮 Шериф',
                'doctor': '💊 Доктор',
                'civilian': '👤 Мирный'
            }.get(role, '👤 Мирный')
            
            role_desc = {
                'mafia': 'Вы просыпаетесь ночью и можете убить одного игрока.',
                'sheriff': 'Ночью вы можете проверить одного игрока на принадлежность к мафии.',
                'doctor': 'Ночью вы можете спасти одного игрока от смерти.',
                'civilian': 'Днём вы участвуете в обсуждении и голосовании.'
            }.get(role, '')
            
            try:
                await context.bot.send_message(
                    chat_id=player_id,
                    text=(f.header("МАФИЯ: ТВОЯ РОЛЬ", role_emoji.split()[0]) + "\n\n"
                          f"{f.list_item('Роль: ' + role_emoji)}\n"
                          f"{f.list_item(role_desc)}\n\n"
                          f"Ночь наступает! Мафия может убить.")
                )
            except:
                pass
        
        # Объявляем в чате
        mafia_count = result['mafia_count']
        text = (f.header("ИГРА НАЧАЛАСЬ", "🔪") + "\n\n"
                f"{f.list_item(f'Всего игроков: {len(players)}')}\n"
                f"{f.list_item(f'Мафия: {mafia_count}')}\n"
                f"{f.list_item('Шериф: есть' if result['sheriff_count'] > 0 else 'Шериф: нет')}\n"
                f"{f.list_item('Доктор: есть' if result['doctor_count'] > 0 else 'Доктор: нет')}\n\n"
                f"{f.info('Роли разосланы в личные сообщения. Ночная фаза началась!')}")
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_mafia_vote(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Проголосовать днём"""
        user_id = update.effective_user.id
        
        if not context.args:
            await update.message.reply_text(f.error("Укажите игрока: /mafiavote @user"))
            return
        
        query = context.args[0]
        target_user = self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        target_id = target_user['user_id']
        
        # Ищем активную игру, где участвует пользователь
        games = self.db.get_active_mafia_games()
        game_id = None
        
        for game in games:
            if game[2] == 'playing':
                players = json.loads(game[4])
                if user_id in players:
                    game_id = game[0]
                    break
        
        if not game_id:
            await update.message.reply_text(f.error("Вы не участвуете в активной игре"))
            return
        
        game = self.db.get_mafia_game(game_id)
        if game['phase'] != 'day':
            await update.message.reply_text(f.error("Сейчас ночная фаза. Голосование невозможно."))
            return
        
        result = self.db.mafia_day_vote(game_id, user_id, target_id)
        
        if result['success']:
            await update.message.reply_text(
                f.success(f"Ваш голос за {target_user.get('first_name')} учтён!"),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(f.error("Не удалось проголосовать"))
    
    async def cmd_mafia_night_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ночные действия (для мафии, шерифа, доктора)"""
        user_id = update.effective_user.id
        
        # Ищем активную игру
        games = self.db.get_active_mafia_games()
        game_id = None
        user_role = None
        
        for game in games:
            if game[2] == 'playing':
                players = json.loads(game[4])
                if user_id in players:
                    game_id = game[0]
                    roles = json.loads(game[5]) if isinstance(game[5], str) else {}
                    user_role = roles.get(str(user_id))
                    break
        
        if not game_id:
            await update.message.reply_text(f.error("Вы не участвуете в активной игре"))
            return
        
        game = self.db.get_mafia_game(game_id)
        if game['phase'] != 'night':
            await update.message.reply_text(f.error("Сейчас дневная фаза. Действия ночью невозможны."))
            return
        
        # Парсим аргументы в зависимости от роли
        mafia_kill = None
        doctor_save = None
        sheriff_check = None
        
        if user_role == 'mafia' and context.args:
            query = context.args[0]
            target = self.db.get_user_by_username(query)
            if target:
                mafia_kill = target['user_id']
        
        elif user_role == 'doctor' and context.args:
            query = context.args[0]
            target = self.db.get_user_by_username(query)
            if target:
                doctor_save = target['user_id']
        
        elif user_role == 'sheriff' and context.args:
            query = context.args[0]
            target = self.db.get_user_by_username(query)
            if target:
                sheriff_check = target['user_id']
        
        result = self.db.mafia_night_action(game_id, mafia_kill, doctor_save, sheriff_check)
        
        if result['success']:
            if user_role == 'sheriff' and result.get('sheriff_result') is not None:
                verdict = "мафия" if result['sheriff_result'] else "мирный"
                await update.message.reply_text(
                    f.info(f"Результат проверки: {verdict}"),
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    f.success("Действие выполнено!"),
                    parse_mode='Markdown'
                )
            
            # Если все действия совершены, завершаем ночь
            if result.get('day'):
                # Завершаем день и переходим к голосованию
                day_result = self.db.mafia_end_day(game_id)
                
                if day_result['success']:
                    killed_names = []
                    for uid in day_result['killed']:
                        u = self.db.get_user_by_id(uid)
                        if u:
                            killed_names.append(u.get('first_name', 'Неизвестно'))
                    
                    text = (f.header("НАСТУПИЛ ДЕНЬ", "☀️") + "\n\n")
                    
                    if killed_names:
                        text += f"{f.list_item('Убитые: ' + ', '.join(killed_names))}\n"
                    else:
                        text += f"{f.list_item('Этой ночью никто не погиб')}\n"
                    
                    if day_result.get('executed'):
                        exec_user = self.db.get_user_by_id(day_result['executed'])
                        exec_name = exec_user.get('first_name', 'Неизвестно') if exec_user else 'Неизвестно'
                        text += f"{f.list_item('Казнён: ' + exec_name)}\n"
                    
                    if day_result['game_over']:
                        winner = "Мафия" if day_result['winner'] == 'mafia' else "Мирные"
                        text += f"\n{f.success(f'ИГРА ОКОНЧЕНА! Победила {winner}!')}"
                        
                        # Обновляем статистику
                        for player_id in json.loads(game['players']):
                            if day_result['winner'] == 'mafia' and roles.get(str(player_id)) == 'mafia':
                                self.db.add_stat(player_id, "mafia_wins", 1)
                            elif day_result['winner'] == 'civilians' and roles.get(str(player_id)) != 'mafia':
                                self.db.add_stat(player_id, "mafia_wins", 1)
                    
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=text,
                        parse_mode='Markdown'
                    )
        else:
            await update.message.reply_text(f.error(result.get('reason', 'Не удалось выполнить действие')))

    # ========== МОДУЛЬ ЭКОНОМИКИ (TREANFER) ==========
    
    async def cmd_shop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Магазин предметов"""
        items = self.db.get_shop_items()
        
        text = f.header("МАГАЗИН", "🛍") + "\n\n"
        
        for item in items:
            item_id, name, desc, price_coins, price_diamonds, item_type, value, stock = item[:8]
            price_str = f"{price_coins} 💰" if price_coins > 0 else f"{price_diamonds} 💎"
            stock_str = f" (осталось: {stock})" if stock > 0 else " (∞)" if stock == -1 else " (0)"
            
            text += (f"**{item_id}. {name}** {price_str}{stock_str}\n"
                     f"└ {desc}\n\n")
        
        text += f"{f.command('buy [название или ID]', 'купить предмет')}\n"
        text += f"{f.command('inventory', 'твой инвентарь')}"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_buy(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Купить предмет"""
        if not context.args:
            await update.message.reply_text(f.error("Укажите предмет: /buy [название или ID]"))
            return
        
        query = " ".join(context.args).lower()
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)
        
        # Ищем предмет по ID или названию
        items = self.db.get_shop_items()
        selected_item = None
        
        # Сначала по ID
        if query.isdigit():
            item_id = int(query)
            for item in items:
                if item[0] == item_id:
                    selected_item = item
                    break
        
        # Потом по названию
        if not selected_item:
            for item in items:
                if query in item[1].lower():
                    selected_item = item
                    break
        
        if not selected_item:
            await update.message.reply_text(f.error("Предмет не найден"))
            return
        
        item_id, name, desc, price_coins, price_diamonds, item_type, value, stock = selected_item[:8]
        
        # Проверка наличия
        if stock == 0:
            await update.message.reply_text(f.error("Этот предмет закончился"))
            return
        
        # Проверка денег
        if price_coins > 0 and user_data['coins'] < price_coins:
            await update.message.reply_text(f.error(f"Недостаточно монет. Нужно {price_coins} 💰"))
            return
        
        if price_diamonds > 0 and user_data['diamonds'] < price_diamonds:
            await update.message.reply_text(f.error(f"Недостаточно алмазов. Нужно {price_diamonds} 💎"))
            return
        
        # Покупка
        if price_coins > 0:
            self.db.add_coins(user_id, -price_coins)
        if price_diamonds > 0:
            self.db.add_diamonds(user_id, -price_diamonds)
        
        # Применение эффекта
        effect_text = ""
        if item_type == "heal":
            self.db.heal(user_id, int(value))
            effect_text = f"❤️ Здоровье +{value}"
        elif item_type == "damage":
            self.db.cursor.execute("UPDATE users SET damage = damage + ? WHERE user_id = ?", (int(value), user_id))
            self.db.conn.commit()
            effect_text = f"⚔️ Урон +{value}"
        elif item_type == "armor":
            self.db.cursor.execute("UPDATE users SET armor = armor + ? WHERE user_id = ?", (int(value), user_id))
            self.db.conn.commit()
            effect_text = f"🛡 Броня +{value}"
        elif item_type == "energy":
            self.db.add_energy(user_id, int(value))
            effect_text = f"⚡ Энергия +{value}"
        elif item_type in ["vip", "premium"]:
            # Привилегии обрабатываются отдельно
            pass
        else:
            # Добавляем в инвентарь
            self.db.cursor.execute('''
                INSERT INTO inventory (user_id, item_id, quantity, acquired_at)
                VALUES (?, ?, ?, ?)
            ''', (user_id, item_id, 1, datetime.datetime.now()))
            self.db.conn.commit()
            effect_text = f"📦 Предмет добавлен в инвентарь"
        
        text = (f.header("ПОКУПКА СОВЕРШЕНА", "✅") + "\n\n"
                f"{f.list_item('Предмет: ' + name)}\n"
                f"{f.list_item('Цена: ' + (str(price_coins) + ' 💰' if price_coins > 0 else str(price_diamonds) + ' 💎'))}\n")
        
        if effect_text:
            text += f"{f.list_item('Эффект: ' + effect_text)}\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_inventory(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Инвентарь пользователя"""
        user_id = update.effective_user.id
        items = self.db.get_inventory(user_id)
        
        if not items:
            await update.message.reply_text(f.info("Твой инвентарь пуст"))
            return
        
        text = f.header("ТВОЙ ИНВЕНТАРЬ", "📦") + "\n\n"
        
        for item in items:
            inv_id, user_id, item_id, quantity, acquired_at, name, desc, item_type, value = item
            date = datetime.datetime.fromisoformat(acquired_at).strftime("%d.%m.%Y") if acquired_at else "неизвестно"
            
            text += (f"**ID: {inv_id}** — {name} x{quantity}\n"
                     f"└ {desc}\n"
                     f"└ Получено: {date}\n\n")
        
        text += f"{f.command('use [ID]', 'использовать предмет')}"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_use(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Использовать предмет из инвентаря"""
        if not context.args:
            await update.message.reply_text(f.error("Укажите ID предмета: /use 1"))
            return
        
        try:
            inv_id = int(context.args[0])
        except:
            await update.message.reply_text(f.error("Неверный ID"))
            return
        
        user_id = update.effective_user.id
        
        # Получаем предмет из инвентаря
        self.db.cursor.execute('''
            SELECT i.*, s.name, s.description, s.type, s.value
            FROM inventory i
            JOIN shop_items s ON i.item_id = s.id
            WHERE i.id = ? AND i.user_id = ? AND i.quantity > 0
        ''', (inv_id, user_id))
        
        item = self.db.cursor.fetchone()
        if not item:
            await update.message.reply_text(f.error("Предмет не найден в инвентаре"))
            return
        
        inv_id, user_id, item_id, quantity, acquired_at, name, desc, item_type, value = item[:9]
        
        # Применяем эффект
        effect_text = ""
        if item_type == "heal":
            self.db.heal(user_id, int(value))
            effect_text = f"❤️ Здоровье +{value}"
        elif item_type == "damage":
            self.db.cursor.execute("UPDATE users SET damage = damage + ? WHERE user_id = ?", (int(value), user_id))
            self.db.conn.commit()
            effect_text = f"⚔️ Урон +{value}"
        elif item_type == "armor":
            self.db.cursor.execute("UPDATE users SET armor = armor + ? WHERE user_id = ?", (int(value), user_id))
            self.db.conn.commit()
            effect_text = f"🛡 Броня +{value}"
        elif item_type == "energy":
            self.db.add_energy(user_id, int(value))
            effect_text = f"⚡ Энергия +{value}"
        else:
            await update.message.reply_text(f.error("Этот предмет нельзя использовать"))
            return
        
        # Уменьшаем количество
        if quantity > 1:
            self.db.cursor.execute("UPDATE inventory SET quantity = quantity - 1 WHERE id = ?", (inv_id,))
        else:
            self.db.cursor.execute("DELETE FROM inventory WHERE id = ?", (inv_id,))
        self.db.conn.commit()
        
        text = (f.header("ПРЕДМЕТ ИСПОЛЬЗОВАН", "✅") + "\n\n"
                f"{f.list_item('Предмет: ' + name)}\n"
                f"{f.list_item('Эффект: ' + effect_text)}")
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_pay(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Перевести монеты"""
        if len(context.args) < 2:
            await update.message.reply_text(f.error("Использование: /pay @user сумма"))
            return
        
        query = context.args[0]
        try:
            amount = int(context.args[1])
        except:
            await update.message.reply_text(f.error("Сумма должна быть числом"))
            return
        
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)
        
        target_user = self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        if target_user['user_id'] == user_id:
            await update.message.reply_text(f.error("Нельзя перевести самому себе"))
            return
        
        if user_data['coins'] < amount:
            await update.message.reply_text(f.error(f"Недостаточно монет. У тебя {user_data['coins']} 💰"))
            return
        
        self.db.add_coins(user_id, -amount)
        self.db.add_coins(target_user['user_id'], amount)
        
        text = (f.header("ПЕРЕВОД ВЫПОЛНЕН", "💰") + "\n\n"
                f"{f.list_item('Получатель: ' + target_user.get('first_name', 'Пользователь'))}\n"
                f"{f.list_item('Сумма: ' + str(amount) + ' 💰')}\n"
                f"{f.list_item('Отправитель: ' + update.effective_user.first_name)}")
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_pay_diamond(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Перевести алмазы"""
        if len(context.args) < 2:
            await update.message.reply_text(f.error("Использование: /paydiamond @user сумма"))
            return
        
        query = context.args[0]
        try:
            amount = int(context.args[1])
        except:
            await update.message.reply_text(f.error("Сумма должна быть числом"))
            return
        
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)
        
        target_user = self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        if target_user['user_id'] == user_id:
            await update.message.reply_text(f.error("Нельзя перевести самому себе"))
            return
        
        if user_data['diamonds'] < amount:
            await update.message.reply_text(f.error(f"Недостаточно алмазов. У тебя {user_data['diamonds']} 💎"))
            return
        
        self.db.add_diamonds(user_id, -amount)
        self.db.add_diamonds(target_user['user_id'], amount)
        
        text = (f.header("ПЕРЕВОД АЛМАЗОВ", "💎") + "\n\n"
                f"{f.list_item('Получатель: ' + target_user.get('first_name', 'Пользователь'))}\n"
                f"{f.list_item('Сумма: ' + str(amount) + ' 💎')}\n"
                f"{f.list_item('Отправитель: ' + update.effective_user.first_name)}")
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_pay_crystal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Перевести кристаллы"""
        if len(context.args) < 2:
            await update.message.reply_text(f.error("Использование: /paycrystal @user сумма"))
            return
        
        query = context.args[0]
        try:
            amount = int(context.args[1])
        except:
            await update.message.reply_text(f.error("Сумма должна быть числом"))
            return
        
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)
        
        target_user = self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        if target_user['user_id'] == user_id:
            await update.message.reply_text(f.error("Нельзя перевести самому себе"))
            return
        
        if user_data['crystals'] < amount:
            await update.message.reply_text(f.error(f"Недостаточно кристаллов. У тебя {user_data['crystals']} 🔮"))
            return
        
        self.db.add_crystals(user_id, -amount)
        self.db.add_crystals(target_user['user_id'], amount)
        
        text = (f.header("ПЕРЕВОД КРИСТАЛЛОВ", "🔮") + "\n\n"
                f"{f.list_item('Получатель: ' + target_user.get('first_name', 'Пользователь'))}\n"
                f"{f.list_item('Сумма: ' + str(amount) + ' 🔮')}\n"
                f"{f.list_item('Отправитель: ' + update.effective_user.first_name)}")
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_daily(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ежедневный бонус"""
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)
        
        today = datetime.datetime.now().date()
        if user_data.get('last_daily'):
            last_date = datetime.datetime.fromisoformat(user_data['last_daily']).date()
            if last_date == today:
                await update.message.reply_text(f.error("Вы уже получали ежедневный бонус сегодня"))
                return
        
        streak = self.db.add_daily_streak(user_id)
        
        coins = random.randint(100, 300)
        exp = random.randint(20, 60)
        energy = random.randint(10, 30)
        
        coins = int(coins * (1 + min(streak, 30) * 0.05))
        exp = int(exp * (1 + min(streak, 30) * 0.05))
        
        if self.db.is_vip(user_id):
            coins = int(coins * 1.5)
            exp = int(exp * 1.5)
            energy = int(energy * 1.5)
        if self.db.is_premium(user_id):
            coins = int(coins * 2)
            exp = int(exp * 2)
            energy = int(energy * 2)
        
        self.db.add_coins(user_id, coins)
        self.db.add_exp(user_id, exp)
        self.db.add_energy(user_id, energy)
        
        text = (f.header("ЕЖЕДНЕВНЫЙ БОНУС", "🎁") + "\n\n"
                f"{f.list_item('Стрик: ' + str(streak) + ' дней 🔥')}\n"
                f"{f.list_item('Монеты: +' + str(coins) + ' 💰')}\n"
                f"{f.list_item('Опыт: +' + str(exp) + ' ✨')}\n"
                f"{f.list_item('Энергия: +' + str(energy) + ' ⚡')}\n\n"
                f"{f.info('Заходи завтра за новым бонусом!')}")
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_weekly(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Недельный бонус"""
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)
        
        if not self.db.can_claim_weekly(user_id):
            await update.message.reply_text(f.error("Недельный бонус можно получать раз в 7 дней"))
            return
        
        coins = random.randint(1000, 3000)
        diamonds = random.randint(10, 30)
        crystals = random.randint(1, 5)
        
        if self.db.is_vip(user_id):
            coins = int(coins * 1.5)
            diamonds = int(diamonds * 1.5)
            crystals = int(crystals * 1.5)
        if self.db.is_premium(user_id):
            coins = int(coins * 2)
            diamonds = int(diamonds * 2)
            crystals = int(crystals * 2)
        
        self.db.add_coins(user_id, coins)
        self.db.add_diamonds(user_id, diamonds)
        self.db.add_crystals(user_id, crystals)
        self.db.claim_weekly(user_id)
        
        text = (f.header("НЕДЕЛЬНЫЙ БОНУС", "📅") + "\n\n"
                f"{f.list_item('Монеты: +' + str(coins) + ' 💰')}\n"
                f"{f.list_item('Алмазы: +' + str(diamonds) + ' 💎')}\n"
                f"{f.list_item('Кристаллы: +' + str(crystals) + ' 🔮')}\n\n"
                f"{f.info('Возвращайся через неделю!')}")
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_streak(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Текущий стрик"""
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)
        
        streak = user_data.get('daily_streak', 0)
        last_daily = user_data.get('last_daily', 'никогда')
        
        if last_daily != 'никогда':
            last = datetime.datetime.fromisoformat(last_daily)
            days_missed = (datetime.datetime.now() - last).days
        else:
            days_missed = 0
        
        text = (f.header("ТЕКУЩИЙ СТРИК", "🔥") + "\n\n"
                f"{f.list_item('Дней подряд: ' + str(streak))}\n"
                f"{f.list_item('Последний вход: ' + (last_daily[:10] if last_daily != 'никогда' else 'никогда'))}\n"
                f"{f.list_item('Пропущено дней: ' + str(days_missed))}")
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    # ========== МОДУЛЬ ПРИВИЛЕГИЙ ==========
    
    async def cmd_donate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о привилегиях"""
        text = (f.header("ПРИВИЛЕГИИ", "💎") + "\n\n"
                
                f"{f.section('VIP СТАТУС', '🌟')}\n"
                f"Цена: {PRIVILEGE_PRICES['vip']} 💰 / {PRIVILEGE_DAYS['vip']} дней\n"
                f"{f.list_item('Урон в битвах +20%')}\n"
                f"{f.list_item('Награда с боссов +50%')}\n"
                f"{f.list_item('Ежедневный бонус +50%')}\n"
                f"{f.list_item('Нет спам-фильтра')}\n\n"
                
                f"{f.section('PREMIUM СТАТУС', '💎')}\n"
                f"Цена: {PRIVILEGE_PRICES['premium']} 💰 / {PRIVILEGE_DAYS['premium']} дней\n"
                f"{f.list_item('Все бонусы VIP')}\n"
                f"{f.list_item('Урон в битвах +50%')}\n"
                f"{f.list_item('Награда с боссов +100%')}\n"
                f"{f.list_item('Ежедневный бонус +100%')}\n"
                f"{f.list_item('Доступ к алмазам')}\n\n"
                
                f"{f.section('LORD СТАТУС', '👑')}\n"
                f"Цена: {PRIVILEGE_PRICES['lord']} 💰 / {PRIVILEGE_DAYS['lord']} дней\n"
                f"{f.list_item('Все бонусы PREMIUM')}\n"
                f"{f.list_item('Личные комнаты')}\n"
                f"{f.list_item('Кастомные цвета в профиле')}\n\n"
                
                f"{f.section('ULTRA СТАТУС', '🦅')}\n"
                f"Цена: {PRIVILEGE_PRICES['ultra']} 💰 / {PRIVILEGE_DAYS['ultra']} дней\n"
                f"{f.list_item('Все бонусы LORD')}\n"
                f"{f.list_item('Эксклюзивные скины')}\n\n"
                
                f"Купить: /vip, /premium, /lord, /ultra")
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_vip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Купить VIP"""
        await self.buy_privilege(update, "vip")
    
    async def cmd_premium(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Купить PREMIUM"""
        await self.buy_privilege(update, "premium")
    
    async def cmd_lord(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Купить LORD"""
        await self.buy_privilege(update, "lord")
    
    async def cmd_ultra(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Купить ULTRA"""
        await self.buy_privilege(update, "ultra")
    
    async def buy_privilege(self, update: Update, priv_type: str):
        """Общая функция покупки привилегий"""
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)
        
        price = PRIVILEGE_PRICES.get(priv_type, 0)
        days = PRIVILEGE_DAYS.get(priv_type, 30)
        
        # Проверка на уже активную привилегию
        if priv_type == "vip" and self.db.is_vip(user_id):
            await update.message.reply_text(f.error("VIP статус уже активен"))
            return
        if priv_type == "premium" and self.db.is_premium(user_id):
            await update.message.reply_text(f.error("PREMIUM статус уже активен"))
            return
        
        if user_data['coins'] < price:
            await update.message.reply_text(f.error(f"Недостаточно монет. Нужно {price} 💰"))
            return
        
        self.db.add_coins(user_id, -price)
        
        # Устанавливаем привилегию
        until = datetime.datetime.now() + datetime.timedelta(days=days)
        
        if priv_type == "vip":
            self.db.cursor.execute("UPDATE users SET vip_until = ?, role = 'vip' WHERE user_id = ?", (until, user_id))
        elif priv_type == "premium":
            self.db.cursor.execute("UPDATE users SET premium_until = ?, role = 'premium' WHERE user_id = ?", (until, user_id))
        elif priv_type == "lord":
            self.db.cursor.execute("UPDATE users SET lord_until = ?, role = 'lord' WHERE user_id = ?", (until, user_id))
        elif priv_type == "ultra":
            self.db.cursor.execute("UPDATE users SET ultra_until = ?, role = 'ultra' WHERE user_id = ?", (until, user_id))
        
        self.db.conn.commit()
        
        text = (f.header("ПРИВИЛЕГИЯ АКТИВИРОВАНА", "✅") + "\n\n"
                f"{f.list_item('Статус: ' + priv_type.upper())}\n"
                f"{f.list_item('Срок: ' + str(days) + ' дней')}\n"
                f"{f.list_item('Действует до: ' + until.strftime('%d.%m.%Y'))}\n\n"
                f"{f.success('Все бонусы активны!')}")
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_buy_moderator(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Купить статус модератора (для доната)"""
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)
        
        price = PRIVILEGE_PRICES.get('moderator', 100000)
        
        if user_data['coins'] < price:
            await update.message.reply_text(f.error(f"Недостаточно монет. Нужно {price} 💰"))
            return
        
        if user_data.get('rank', 0) >= 1:
            await update.message.reply_text(f.error("У вас уже есть модераторские права"))
            return
        
        self.db.add_coins(user_id, -price)
        self.db.set_user_rank(user_id, 1, user_id)  # Ранг 1 - младший модератор
        
        await update.message.reply_text(
            f.success("Поздравляем! Теперь у вас статус младшего модератора!"),
            parse_mode='Markdown'
        )
    
    # ========== МОДУЛЬ КЛАНОВ ==========
    
    async def cmd_clan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о клане"""
        user_id = update.effective_user.id
        clan = self.db.get_user_clan(user_id)
        
        if not clan:
            text = (f.header("КЛАНЫ", "👥") + "\n\n"
                    f"{f.info('Ты не состоишь в клане')}\n\n"
                    f"{f.command('clancreate [название]', 'создать клан')}\n"
                    f"{f.command('clanjoin [ID]', 'вступить в клан')}\n"
                    f"{f.command('clantop', 'топ кланов')}")
            
            await update.message.reply_text(text, parse_mode='Markdown')
            return
        
        clan_id, name, owner_id, level, exp, members, rating, wins, losses, created_at = clan
        
        members_list = self.db.get_clan_members(clan_id)
        owner = self.db.get_user_by_id(owner_id)
        owner_name = owner.get('first_name', 'Неизвестно') if owner else 'Неизвестно'
        
        text = (f.header(f"КЛАН: {name}", "👥") + "\n\n"
                f"{f.section('ИНФОРМАЦИЯ', '📊')}\n"
                f"{f.stat('Уровень', str(level))}\n"
                f"{f.stat('Опыт', str(exp) + '/' + str(level * 500))}\n"
                f"{f.stat('Участников', str(members) + '/50')}\n"
                f"{f.stat('Рейтинг', str(rating))}\n"
                f"{f.stat('Побед/Поражений', str(wins) + '/' + str(losses))}\n"
                f"{f.stat('Создатель', owner_name)}\n\n"
                
                f"{f.section('УЧАСТНИКИ', '👤')}\n")
        
        for member in members_list:
            mid, mname, mnick, mlevel, mrole, joined = member
            role_emoji = "👑" if mrole == 'owner' else "🛡️" if mrole == 'admin' else "👤"
            display = mnick or mname
            text += f"{role_emoji} {display} (ур.{mlevel})\n"
        
        text += f"\n{f.command('clanleave', 'покинуть клан')}"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_clan_create(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Создать клан"""
        if not context.args:
            await update.message.reply_text(f.error("Укажите название клана: /clancreate Название"))
            return
        
        name = " ".join(context.args)
        if len(name) > 30:
            await update.message.reply_text(f.error("Название слишком длинное (макс 30 символов)"))
            return
        
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)
        
        if self.db.get_user_clan(user_id):
            await update.message.reply_text(f.error("Вы уже в клане"))
            return
        
        if user_data['level'] < 5:
            await update.message.reply_text(f.error("Для создания клана нужен 5 уровень"))
            return
        
        if user_data['coins'] < 1000:
            await update.message.reply_text(f.error("Для создания клана нужно 1000 💰"))
            return
        
        clan_id = self.db.create_clan(name, user_id)
        
        if clan_id:
            self.db.add_coins(user_id, -1000)
            await update.message.reply_text(
                f.success(f"Клан «{name}» создан! ID: {clan_id}"),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(f.error("Клан с таким названием уже существует"))
    
    async def cmd_clan_join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Вступить в клан"""
        if not context.args:
            await update.message.reply_text(f.error("Укажите ID клана: /clanjoin 1"))
            return
        
        try:
            clan_id = int(context.args[0])
        except:
            await update.message.reply_text(f.error("Неверный ID клана"))
            return
        
        user_id = update.effective_user.id
        
        if self.db.get_user_clan(user_id):
            await update.message.reply_text(f.error("Вы уже в клане"))
            return
        
        clan = self.db.get_clan(clan_id)
        if not clan:
            await update.message.reply_text(f.error("Клан не найден"))
            return
        
        if clan[5] >= 50:
            await update.message.reply_text(f.error("В клане нет мест"))
            return
        
        if self.db.join_clan(user_id, clan_id):
            await update.message.reply_text(
                f.success(f"Вы вступили в клан «{clan[1]}»!"),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(f.error("Не удалось вступить в клан"))
    
    async def cmd_clan_leave(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Покинуть клан"""
        user_id = update.effective_user.id
        
        if self.db.leave_clan(user_id):
            await update.message.reply_text(f.success("Вы покинули клан"), parse_mode='Markdown')
        else:
            await update.message.reply_text(f.error("Вы не в клане"))
    
    async def cmd_clan_top(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Топ кланов"""
        clans = self.db.get_top_clans(10)
        
        if not clans:
            await update.message.reply_text(f.info("Нет созданных кланов"))
            return
        
        text = f.header("ТОП КЛАНОВ", "🏆") + "\n\n"
        
        for i, (name, level, members, rating) in enumerate(clans, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
            text += f"{medal} **{i}. {name}** — ур.{level}, уч.{members}, рейтинг {rating}\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_clan_war(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Клановая война"""
        user_id = update.effective_user.id
        clan = self.db.get_user_clan(user_id)
        
        if not clan:
            await update.message.reply_text(f.error("Вы не в клане"))
            return
        
        await update.message.reply_text(
            f.info("Клановые войны скоро будут доступны!"),
            parse_mode='Markdown'
        )

    # ========== МОДУЛЬ БОССОВ ==========
    
    async def cmd_boss_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список боссов"""
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)
        bosses = self.db.get_bosses(alive_only=True)
        
        if not bosses:
            self.db.respawn_bosses()
            bosses = self.db.get_bosses(alive_only=True)
        
        text = f.header("АРЕНА БОССОВ", "👾") + "\n\n"
        
        if bosses:
            boss = bosses[0]
            health_bar = f.progress(boss[3], boss[4], 20)
            
            text += (f"**ТЕКУЩИЙ БОСС**\n"
                     f"└ {boss[1]} (ур. {boss[2]})\n"
                     f"└ ❤️ Здоровье: {health_bar}\n"
                     f"└ ⚔️ Урон: {boss[5]}\n"
                     f"└ Награда: {boss[6]} 💰\n\n")
            
            if len(bosses) > 1:
                text += f.section("ОЧЕРЕДЬ", "📋") + "\n"
                for i, b in enumerate(bosses[1:], 2):
                    text += f"{i}. {b[1]} — ❤️ {b[3]}/{b[4]}\n"
        
        text += (f"\n{f.section('ТВОИ ПОКАЗАТЕЛИ', '⚔️')}\n"
                 f"{f.stat('❤️ Здоровье', str(user_data.get('health', 100)) + '/100')}\n"
                 f"{f.stat('⚡ Энергия', str(user_data.get('energy', 100)) + '/100')}\n"
                 f"{f.stat('⚔️ Урон', str(user_data.get('damage', 10)))}\n"
                 f"{f.stat('👾 Убито боссов', str(user_data.get('boss_kills', 0)))}\n\n"
                 f"{f.section('КОМАНДЫ', '⌨️')}\n"
                 f"{f.command('bossfight [ID]', 'атаковать босса', '1')}\n"
                 f"{f.command('regen', 'восстановить ❤️ и ⚡')}\n"
                 f"{f.command('boss [ID]', 'информация о боссе', '1')}\n"
                 f"{f.command('bossstats', 'статистика битв')}")
        
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
    
    async def cmd_boss_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о боссе"""
        if not context.args:
            await update.message.reply_text(f.error("Укажите ID босса: /boss 1"))
            return
        
        try:
            boss_id = int(context.args[0])
        except:
            await update.message.reply_text(f.error("Неверный ID босса"))
            return
        
        boss = self.db.get_boss(boss_id)
        if not boss:
            await update.message.reply_text(f.error("Босс не найден"))
            return
        
        status = "ЖИВ" if boss[8] else "ПОВЕРЖЕН"
        health_bar = f.progress(boss[3], boss[4], 20)
        
        text = (f.header(f"БОСС: {boss[1]}", "👾") + "\n\n"
                f"{f.stat('Уровень', str(boss[2]))}\n"
                f"{f.stat('❤️ Здоровье', health_bar)}\n"
                f"{f.stat('⚔️ Урон', str(boss[5]))}\n"
                f"{f.stat('💰 Награда', str(boss[6]) + ' 💰')}\n"
                f"{f.stat('📊 Статус', status)}")
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_boss_fight(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Битва с боссом"""
        user = update.effective_user
        user_data = self.db.get_user_by_id(user.id)
        
        if self.db.is_muted(user.id):
            remaining = self.db.get_mute_time(user.id)
            await update.message.reply_text(f.error(f"Вы в муте. Осталось: {remaining}"))
            return
        
        if not context.args:
            await update.message.reply_text(f.error("Укажите ID босса: /bossfight 1"))
            return
        
        try:
            boss_id = int(context.args[0])
        except:
            await update.message.reply_text(f.error("Неверный ID босса"))
            return
        
        boss = self.db.get_boss(boss_id)
        if not boss or not boss[8]:
            await update.message.reply_text(f.error("Босс не найден или уже повержен"))
            return
        
        if user_data['energy'] < 10:
            await update.message.reply_text(f.error("Недостаточно энергии. Используй /regen"))
            return
        
        self.db.add_energy(user.id, -10)
        
        # Расчёт урона
        damage_bonus = 1.0
        if self.db.is_vip(user.id):
            damage_bonus += 0.2
        if self.db.is_premium(user.id):
            damage_bonus += 0.3
        if self.db.is_vip(user.id) and self.db.is_premium(user.id):
            damage_bonus += 0.5
        
        player_damage = int(user_data['damage'] * damage_bonus) + random.randint(-5, 5)
        boss_damage = boss[5] + random.randint(-5, 5)
        player_taken = max(1, boss_damage - user_data['armor'] // 2)
        
        boss_killed = self.db.damage_boss(boss_id, player_damage)
        self.db.damage(user.id, player_taken)
        
        text = f.header("БИТВА С БОССОМ", "⚔️") + "\n\n"
        text += f"{f.list_item('Ваш урон: ' + str(player_damage))}\n"
        text += f"{f.list_item('Урон босса: ' + str(player_taken))}\n\n"
        
        if boss_killed:
            reward = boss[6] * (1 + user_data['level'] // 10)
            if self.db.is_vip(user.id):
                reward = int(reward * 1.5)
            if self.db.is_premium(user.id):
                reward = int(reward * 2)
            
            self.db.add_coins(user.id, reward)
            self.db.add_boss_kill(user.id)
            self.db.add_exp(user.id, boss[2] * 10)
            
            # Проверка достижений
            boss_kills = user_data.get('boss_kills', 0) + 1
            if boss_kills == 10:
                self.db.add_achievement(user.id, "👾 Охотник на боссов", "Убито 10 боссов", 500)
            elif boss_kills == 50:
                self.db.add_achievement(user.id, "👾 Легендарный охотник", "Убито 50 боссов", 2000)
            
            text += f.success("ПОБЕДА!") + "\n"
            text += f"{f.list_item('💰 Награда: ' + str(reward) + ' 💰')}\n"
            text += f"{f.list_item('✨ Опыт: +' + str(boss[2] * 10))}\n\n"
        else:
            boss_info = self.db.get_boss(boss_id)
            text += f.warning("Босс еще жив!") + "\n"
            text += f"❤️ Осталось: {boss_info[3]} здоровья\n\n"
        
        if user_data['health'] <= player_taken:
            self.db.heal(user.id, 50)
            text += f.info("Вы погибли и были воскрешены с 50❤️")
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_boss_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Статистика битв с боссами"""
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)
        
        text = (f.header("СТАТИСТИКА БОССОВ", "👾") + "\n\n"
                f"{f.stat('Боссов убито', str(user_data.get('boss_kills', 0)))}\n"
                f"{f.stat('⚔️ Урон', str(user_data.get('damage', 10)))}\n"
                f"{f.stat('🛡 Броня', str(user_data.get('armor', 0)))}\n"
                f"{f.stat('❤️ Здоровье', str(user_data.get('health', 100)) + '/100')}")
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_regen(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Регенерация здоровья и энергии"""
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)
        
        cost = 20
        if user_data['coins'] < cost:
            await update.message.reply_text(f.error(f"Недостаточно монет. Нужно {cost} 💰"))
            return
        
        self.db.add_coins(user_id, -cost)
        self.db.heal(user_id, 50)
        self.db.add_energy(user_id, 20)
        
        await update.message.reply_text(
            f.success("Регенерация завершена!") + "\n" +
            f"{f.list_item('❤️ Здоровье +50')}\n"
            f"{f.list_item('⚡ Энергия +20')}",
            parse_mode='Markdown'
        )
    
    # ========== МОДУЛЬ КАЗИНО ==========
    
    async def cmd_casino(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Главное меню казино"""
        text = (f.header("КАЗИНО", "🎰") + "\n\n"
                f"{f.section('ИГРЫ', '🎲')}\n"
                f"{f.command('roulette [ставка] [цвет]', 'рулетка')}\n"
                f"{f.command('dice [ставка]', 'кости')}\n"
                f"{f.command('blackjack [ставка]', 'блэкджек')}\n"
                f"{f.command('slots [ставка]', 'слоты')}\n\n"
                f"{f.section('ПРИМЕРЫ', '📝')}\n"
                f"{f.example('roulette 10 red')}\n"
                f"{f.example('dice 50')}\n"
                f"{f.example('blackjack 100')}\n"
                f"{f.example('slots 20')}")
        
        await update.message.reply_text(
            text,
            reply_markup=IrisKeyboard.back_button(),
            parse_mode='Markdown'
        )
    
    async def cmd_roulette(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Рулетка"""
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
            await update.message.reply_text(f.error(f"Недостаточно монет. Баланс: {user_data['coins']} 💰"))
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
            result_text = f.success(f"Вы выиграли {winnings} 💰!")
        else:
            self.db.add_coins(user_id, -bet)
            self.db.add_stat(user_id, "casino_losses", 1)
            result_text = f.error(f"Вы проиграли {bet} 💰")
        
        text = (f.header("РУЛЕТКА", "🎰") + "\n\n"
                f"{f.list_item('Ставка: ' + str(bet) + ' 💰')}\n"
                f"{f.list_item('Выбрано: ' + choice)}\n"
                f"{f.list_item('Выпало: ' + str(result_num) + ' ' + result_color)}\n\n"
                f"{result_text}")
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_dice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Кости"""
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)
        
        bet = 10
        if context.args:
            try:
                bet = int(context.args[0])
            except:
                pass
        
        if bet > user_data['coins']:
            await update.message.reply_text(f.error(f"Недостаточно монет. Баланс: {user_data['coins']} 💰"))
            return
        
        dice1 = random.randint(1, 6)
        dice2 = random.randint(1, 6)
        total = dice1 + dice2
        
        if total in [7, 11]:
            win = bet * 2
            result_text = f.success(f"Вы выиграли {win} 💰!")
        elif total in [2, 3, 12]:
            win = 0
            result_text = f.error(f"Вы проиграли {bet} 💰")
        else:
            win = bet
            result_text = f.info(f"Ничья, ставка возвращена: {bet} 💰")
        
        if win > 0:
            self.db.add_coins(user_id, win)
            self.db.add_stat(user_id, "casino_wins", 1)
        else:
            self.db.add_coins(user_id, -bet)
            self.db.add_stat(user_id, "casino_losses", 1)
        
        text = (f.header("КОСТИ", "🎲") + "\n\n"
                f"{f.list_item('Ставка: ' + str(bet) + ' 💰')}\n"
                f"{f.list_item('Кубики: ' + str(dice1) + ' + ' + str(dice2))}\n"
                f"{f.list_item('Сумма: ' + str(total))}\n\n"
                f"{result_text}")
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_blackjack(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Блэкджек"""
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)
        
        bet = 10
        if context.args:
            try:
                bet = int(context.args[0])
            except:
                pass
        
        if bet > user_data['coins']:
            await update.message.reply_text(f.error(f"Недостаточно монет. Баланс: {user_data['coins']} 💰"))
            return
        
        player_cards = [random.randint(1, 11), random.randint(1, 11)]
        player_total = sum(player_cards)
        
        dealer_cards = [random.randint(1, 11), random.randint(1, 11)]
        dealer_total = sum(dealer_cards)
        
        # Простая логика блэкджека
        if player_total == 21:
            result = "win"
            win = int(bet * 2.5)
            result_text = f.success(f"БЛЭКДЖЕК! Вы выиграли {win} 💰!")
        elif player_total > 21:
            result = "lose"
            result_text = f.error(f"Перебор! Вы проиграли {bet} 💰")
        elif dealer_total > 21:
            result = "win"
            win = bet * 2
            result_text = f.success(f"Дилер перебрал! Вы выиграли {win} 💰!")
        elif player_total > dealer_total:
            result = "win"
            win = bet * 2
            result_text = f.success(f"Вы выиграли {win} 💰!")
        elif player_total < dealer_total:
            result = "lose"
            result_text = f.error(f"Вы проиграли {bet} 💰")
        else:
            result = "draw"
            result_text = f.info(f"Ничья, ставка возвращена: {bet} 💰")
        
        if result == "win":
            self.db.add_coins(user_id, win)
            self.db.add_stat(user_id, "casino_wins", 1)
        elif result == "lose":
            self.db.add_coins(user_id, -bet)
            self.db.add_stat(user_id, "casino_losses", 1)
        
        text = (f.header("БЛЭКДЖЕК", "🃏") + "\n\n"
                f"{f.list_item('Ваши карты: ' + ' + '.join(str(c) for c in player_cards) + ' = ' + str(player_total))}\n"
                f"{f.list_item('Карты дилера: ' + ' + '.join(str(c) for c in dealer_cards) + ' = ' + str(dealer_total))}\n\n"
                f"{result_text}")
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_slots(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Слоты"""
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)
        
        bet = 10
        if context.args:
            try:
                bet = int(context.args[0])
            except:
                pass
        
        if bet > user_data['coins']:
            await update.message.reply_text(f.error(f"Недостаточно монет. Баланс: {user_data['coins']} 💰"))
            return
        
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
            result_text = f.success("ДЖЕКПОТ!")
        elif len(set(spin)) == 2:
            win = bet * 2
            result_text = f.success("Маленький выигрыш!")
        else:
            win = 0
            result_text = f.error("Не повезло...")
        
        if win > 0:
            self.db.add_coins(user_id, win)
            self.db.add_stat(user_id, "casino_wins", 1)
        else:
            self.db.add_coins(user_id, -bet)
            self.db.add_stat(user_id, "casino_losses", 1)
        
        text = (f.header("СЛОТЫ", "🎰") + "\n\n"
                f"{' '.join(spin)}\n\n"
                f"{result_text}\n"
                f"{'💰 +' + str(win) + ' 💰' if win > 0 else '💸 -' + str(bet) + ' 💰'}")
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    # ========== МОДУЛЬ ИГР ==========
    
    async def cmd_rps(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Камень-ножницы-бумага"""
        await update.message.reply_text(
            f.header("КАМЕНЬ-НОЖНИЦЫ-БУМАГА", "✊") + "\n\nВыбери свой ход:",
            reply_markup=IrisKeyboard.rps_game(),
            parse_mode='Markdown'
        )
    
    async def cmd_ttt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Крестики-нолики"""
        user_id = update.effective_user.id
        
        # Создаём новую игру
        game_id = f"ttt_{user_id}_{int(time.time())}"
        self.active_games[game_id] = {
            'type': 'ttt',
            'player_x': user_id,
            'player_o': None,
            'board': [' '] * 9,
            'turn': user_id,
            'moves': 0
        }
        
        text = (f.header("КРЕСТИКИ-НОЛИКИ", "⭕") + "\n\n"
                f"{f.info('Ожидание соперника...')}\n"
                f"{f.list_item('ID игры: ' + game_id)}\n\n"
                f"Соперник должен написать: /tttmove {game_id}")
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_ttt_move(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сделать ход в крестики-нолики"""
        if len(context.args) < 2:
            await update.message.reply_text(f.error("Использование: /tttmove [ID игры] [клетка 1-9]"))
            return
        
        game_id = context.args[0]
        try:
            cell = int(context.args[1]) - 1
            if cell < 0 or cell > 8:
                await update.message.reply_text(f.error("Клетка должна быть от 1 до 9"))
                return
        except:
            await update.message.reply_text(f.error("Неверный номер клетки"))
            return
        
        user_id = update.effective_user.id
        
        if game_id not in self.active_games:
            await update.message.reply_text(f.error("Игра не найдена"))
            return
        
        game = self.active_games[game_id]
        
        if game['type'] != 'ttt':
            await update.message.reply_text(f.error("Неверный тип игры"))
            return
        
        # Если второй игрок ещё не присоединился
        if game['player_o'] is None:
            if user_id == game['player_x']:
                await update.message.reply_text(f.error("Ожидание соперника"))
                return
            else:
                game['player_o'] = user_id
                game['turn'] = game['player_x']
        
        if game['turn'] != user_id:
            await update.message.reply_text(f.error("Сейчас не ваш ход"))
            return
        
        if game['board'][cell] != ' ':
            await update.message.reply_text(f.error("Эта клетка уже занята"))
            return
        
        # Ставим символ
        symbol = '❌' if game['turn'] == game['player_x'] else '⭕'
        game['board'][cell] = symbol
        game['moves'] += 1
        
        # Проверяем победу
        win_combinations = [
            [0,1,2], [3,4,5], [6,7,8],
            [0,3,6], [1,4,7], [2,5,8],
            [0,4,8], [2,4,6]
        ]
        
        winner = None
        for combo in win_combinations:
            if game['board'][combo[0]] == game['board'][combo[1]] == game['board'][combo[2]] != ' ':
                winner = user_id
                break
        
        # Отображаем доску
        board_display = ""
        for i in range(0, 9, 3):
            board_display += f"{game['board'][i]} | {game['board'][i+1]} | {game['board'][i+2]}\n"
            if i < 6:
                board_display += "---------\n"
        
        if winner:
            # Обновляем статистику
            if winner == game['player_x']:
                self.db.add_stat(game['player_x'], "ttt_wins", 1)
                self.db.add_stat(game['player_o'], "ttt_losses", 1)
            else:
                self.db.add_stat(game['player_o'], "ttt_wins", 1)
                self.db.add_stat(game['player_x'], "ttt_losses", 1)
            
            del self.active_games[game_id]
            
            text = (f.header("ИГРА ОКОНЧЕНА", "🏆") + "\n\n"
                    f"{board_display}\n\n"
                    f"{f.success('Победил ' + ('❌' if winner == game['player_x'] else '⭕'))}")
            
            await update.message.reply_text(text, parse_mode='Markdown')
        
        elif game['moves'] == 9:
            # Ничья
            self.db.add_stat(game['player_x'], "ttt_draws", 1)
            self.db.add_stat(game['player_o'], "ttt_draws", 1)
            del self.active_games[game_id]
            
            text = (f.header("ИГРА ОКОНЧЕНА", "🤝") + "\n\n"
                    f"{board_display}\n\n"
                    f"{f.info('Ничья!')}")
            
            await update.message.reply_text(text, parse_mode='Markdown')
        
        else:
            # Меняем игрока
            game['turn'] = game['player_o'] if game['turn'] == game['player_x'] else game['player_x']
            
            text = (f.header("ХОД СДЕЛАН", "✅") + "\n\n"
                    f"{board_display}\n\n"
                    f"{f.info('Ход ' + ('❌' if game['turn'] == game['player_x'] else '⭕'))}")
            
            await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_memory(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Игра Мемори (найди пары)"""
        user_id = update.effective_user.id
        
        cards = ['🐶', '🐱', '🐭', '🐹', '🐰', '🦊', '🐻', '🐼'] * 2
        random.shuffle(cards)
        
        game_id = f"memory_{user_id}_{int(time.time())}"
        self.active_games[game_id] = {
            'type': 'memory',
            'cards': cards,
            'revealed': [False] * 16,
            'first_pick': None,
            'pairs': 0,
            'moves': 0
        }
        
        text = (f.header("МЕМОРИ", "🧠") + "\n\n"
                f"Найди все пары!\n\n"
                f"1  2  3  4\n"
                f"5  6  7  8\n"
                f"9 10 11 12\n"
                f"13 14 15 16\n\n"
                f"{f.command('memoryplay [номер]', 'открыть карту')}")
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_memory_play(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Открыть карту в Мемори"""
        if not context.args or not context.args[0].isdigit():
            await update.message.reply_text(f.error("Укажи номер карты: /memoryplay 1"))
            return
        
        card = int(context.args[0]) - 1
        if card < 0 or card > 15:
            await update.message.reply_text(f.error("Карта должна быть от 1 до 16"))
            return
        
        user_id = update.effective_user.id
        
        # Ищем игру
        for game_id, game in list(self.active_games.items()):
            if game['type'] == 'memory' and game_id.startswith(f"memory_{user_id}"):
                if game['revealed'][card]:
                    await update.message.reply_text(f.error("Эта карта уже открыта"))
                    return
                
                game['revealed'][card] = True
                game['moves'] += 1
                
                if game['first_pick'] is None:
                    game['first_pick'] = card
                    await update.message.reply_text(
                        f"{f.info(f'Выбрана карта {context.args[0]}: {game["cards"][card]}')}\n"
                        f"Выбери вторую карту: /memoryplay [номер]",
                        parse_mode='Markdown'
                    )
                else:
                    first = game['first_pick']
                    if game['cards'][first] == game['cards'][card]:
                        # Пара найдена
                        game['pairs'] += 1
                        game['first_pick'] = None
                        
                        if game['pairs'] == 8:
                            # Победа
                            self.db.add_stat(user_id, "memory_wins", 1)
                            self.db.add_stat(user_id, "memory_games", 1)
                            
                            reward = random.randint(50, 200)
                            self.db.add_coins(user_id, reward)
                            
                            del self.active_games[game_id]
                            
                            await update.message.reply_text(
                                f.header("ПОБЕДА!", "🎉") + "\n\n"
                                f"{f.list_item(f'Пар найдено: 8/8')}\n"
                                f"{f.list_item(f'Ходов: {game["moves"]}')}\n"
                                f"{f.list_item(f'Награда: +{reward} 💰')}",
                                parse_mode='Markdown'
                            )
                        else:
                            await update.message.reply_text(
                                f.success(f"Пара найдена! ({game['cards'][first]})") + "\n"
                                f"{f.info(f'Осталось пар: {8 - game["pairs"]}')}",
                                parse_mode='Markdown'
                            )
                    else:
                        # Не пара - закрываем
                        game['revealed'][first] = False
                        game['revealed'][card] = False
                        game['first_pick'] = None
                        
                        await update.message.reply_text(
                            f.error(f"Не пара: {game['cards'][first]} и {game['cards'][card]}"),
                            parse_mode='Markdown'
                        )
                return
        
        await update.message.reply_text(f.error("У тебя нет активной игры"), parse_mode='Markdown')
    
    async def cmd_minesweeper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сапёр"""
        user_id = update.effective_user.id
        
        size = 5
        mines = 5
        
        # Генерируем поле
        field = [[0] * size for _ in range(size)]
        mine_positions = random.sample(range(size * size), mines)
        
        for pos in mine_positions:
            x, y = pos // size, pos % size
            field[x][y] = '💣'
            
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < size and 0 <= ny < size and field[nx][ny] != '💣':
                        if field[nx][ny] == 0:
                            field[nx][ny] = 1
                        else:
                            field[nx][ny] += 1
        
        game_id = f"mine_{user_id}_{int(time.time())}"
        self.active_games[game_id] = {
            'type': 'minesweeper',
            'field': field,
            'revealed': [[False] * size for _ in range(size)],
            'mines': mine_positions,
            'size': size
        }
        
        text = (f.header("САПЁР", "💣") + "\n\n"
                f"Найди все мины!\n\n"
                f"  1 2 3 4 5\n")
        
        for i in range(size):
            text += f"{i+1} "
            for j in range(size):
                text += "⬜ "
            text += "\n"
        
        text += f"\n{f.command('mineopen [ряд] [колонка]', 'открыть клетку')}\n"
        text += f"{f.example('mineopen 3 3')}"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_mine_open(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Открыть клетку в сапёре"""
        if len(context.args) < 2 or not context.args[0].isdigit() or not context.args[1].isdigit():
            await update.message.reply_text(f.error("Укажи ряд и колонку: /mineopen 3 3"))
            return
        
        x = int(context.args[0]) - 1
        y = int(context.args[1]) - 1
        
        user_id = update.effective_user.id
        
        # Ищем игру
        for game_id, game in list(self.active_games.items()):
            if game['type'] == 'minesweeper' and game_id.startswith(f"mine_{user_id}"):
                if x < 0 or x >= game['size'] or y < 0 or y >= game['size']:
                    await update.message.reply_text(f.error(f"Координаты должны быть от 1 до {game['size']}"))
                    return
                
                if game['revealed'][x][y]:
                    await update.message.reply_text(f.error("Эта клетка уже открыта"))
                    return
                
                if game['field'][x][y] == '💣':
                    # Проигрыш
                    self.db.add_stat(user_id, "mine_games", 1)
                    
                    # Показываем все мины
                    display = f.header("БАБАХ!", "💥") + "\n\n"
                    for i in range(game['size']):
                        for j in range(game['size']):
                            if game['field'][i][j] == '💣':
                                display += "💣 "
                            elif game['revealed'][i][j]:
                                display += f"{game['field'][i][j]} "
                            else:
                                display += "⬜ "
                        display += "\n"
                    
                    del self.active_games[game_id]
                    await update.message.reply_text(display + "\n😢 Ты подорвался!", parse_mode='Markdown')
                    return
                
                # Открываем клетку
                game['revealed'][x][y] = True
                
                # Проверяем победу
                revealed_count = sum(sum(row) for row in game['revealed'])
                if revealed_count == game['size'] * game['size'] - len(game['mines']):
                    # Победа
                    self.db.add_stat(user_id, "mine_wins", 1)
                    self.db.add_stat(user_id, "mine_games", 1)
                    
                    reward = random.randint(100, 300)
                    self.db.add_coins(user_id, reward)
                    
                    del self.active_games[game_id]
                    
                    await update.message.reply_text(
                        f.header("ПОБЕДА!", "🎉") + "\n\n"
                        f"Ты нашёл все мины!\n"
                        f"+{reward} 💰",
                        parse_mode='Markdown'
                    )
                    return
                
                # Отображаем поле
                display = f.header("САПЁР", "💣") + "\n\n"
                display += "  1 2 3 4 5\n"
                for i in range(game['size']):
                    display += f"{i+1} "
                    for j in range(game['size']):
                        if game['revealed'][i][j]:
                            display += f"{game['field'][i][j]} "
                        else:
                            display += "⬜ "
                    display += "\n"
                
                display += f"\nОткрыто клеток: {revealed_count}"
                
                await update.message.reply_text(display, parse_mode='Markdown')
                return
        
        await update.message.reply_text(f.error("У тебя нет активной игры"), parse_mode='Markdown')
    
    # ========== МОДУЛЬ ДОЛГОВ ==========
    
    async def cmd_debt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Дать в долг"""
        if len(context.args) < 3:
            await update.message.reply_text(f.error("Использование: /debt @user сумма причина"))
            return
        
        query = context.args[0]
        try:
            amount = int(context.args[1])
            reason = " ".join(context.args[2:])
        except:
            await update.message.reply_text(f.error("Неверный формат"))
            return
        
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)
        
        target_user = self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        if target_user['user_id'] == user_id:
            await update.message.reply_text(f.error("Нельзя дать в долг самому себе"))
            return
        
        if user_data['coins'] < amount:
            await update.message.reply_text(f.error(f"Недостаточно монет. У тебя {user_data['coins']} 💰"))
            return
        
        self.db.add_coins(user_id, -amount)
        debt_id = self.db.create_debt(target_user['user_id'], user_id, amount, reason)
        
        text = (f.header("ДОЛГ ОФОРМЛЕН", "💰") + "\n\n"
                f"{f.list_item('Должник: ' + target_user.get('first_name', 'Пользователь'))}\n"
                f"{f.list_item('Сумма: ' + str(amount) + ' 💰')}\n"
                f"{f.list_item('Причина: ' + reason)}\n"
                f"{f.list_item('ID долга: ' + str(debt_id))}")
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
        # Уведомление должнику
        try:
            await context.bot.send_message(
                chat_id=target_user['user_id'],
                text=(f.header("ВЫ ДОЛЖНЫ", "💰") + "\n\n"
                      f"{f.list_item('Кредитор: ' + update.effective_user.first_name)}\n"
                      f"{f.list_item('Сумма: ' + str(amount) + ' 💰')}\n"
                      f"{f.list_item('Причина: ' + reason)}\n"
                      f"{f.list_item('ID долга: ' + str(debt_id))}")
            )
        except:
            pass
    
    async def cmd_debts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список долгов"""
        user_id = update.effective_user.id
        debts = self.db.get_debts(user_id)
        
        if not debts:
            await update.message.reply_text(f.info("У тебя нет активных долгов"))
            return
        
        text = f.header("ТВОИ ДОЛГИ", "💰") + "\n\n"
        
        for debt in debts:
            debt_id, debtor_id, creditor_id, amount, reason, created, deadline, is_paid = debt
            
            if debtor_id == user_id:
                role = "Ты должен"
                other_id = creditor_id
            else:
                role = "Должны тебе"
                other_id = debtor_id
            
            other = self.db.get_user_by_id(other_id)
            other_name = other.get('first_name', 'Пользователь') if other else 'Пользователь'
            
            created_str = datetime.datetime.fromisoformat(created).strftime("%d.%m.%Y")
            deadline_str = datetime.datetime.fromisoformat(deadline).strftime("%d.%m.%Y")
            
            text += (f"**ID: {debt_id}**\n"
                     f"{f.list_item(f'{role}: {other_name}')}\n"
                     f"{f.list_item(f'Сумма: {amount} 💰')}\n"
                     f"{f.list_item(f'Причина: {reason}')}\n"
                     f"{f.list_item(f'Создан: {created_str}')}\n"
                     f"{f.list_item(f'Срок: {deadline_str}')}\n\n")
        
        text += f"{f.command('paydebt [ID]', 'оплатить долг')}"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_pay_debt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Оплатить долг"""
        if not context.args:
            await update.message.reply_text(f.error("Укажи ID долга: /paydebt 1"))
            return
        
        try:
            debt_id = int(context.args[0])
        except:
            await update.message.reply_text(f.error("Неверный ID"))
            return
        
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)
        
        self.db.cursor.execute("SELECT * FROM debts WHERE id = ?", (debt_id,))
        debt = self.db.cursor.fetchone()
        
        if not debt:
            await update.message.reply_text(f.error("Долг не найден"))
            return
        
        debtor_id, creditor_id, amount, reason, created, deadline, is_paid = debt[1:8]
        
        if is_paid:
            await update.message.reply_text(f.error("Долг уже оплачен"))
            return
        
        if debtor_id != user_id:
            await update.message.reply_text(f.error("Это не твой долг"))
            return
        
        if user_data['coins'] < amount:
            await update.message.reply_text(f.error(f"Недостаточно монет. Нужно {amount} 💰"))
            return
        
        self.db.add_coins(user_id, -amount)
        self.db.add_coins(creditor_id, amount)
        self.db.pay_debt(debt_id)
        
        creditor = self.db.get_user_by_id(creditor_id)
        creditor_name = creditor.get('first_name', 'Кредитор') if creditor else 'Кредитор'
        
        text = (f.header("ДОЛГ ОПЛАЧЕН", "✅") + "\n\n"
                f"{f.list_item('Сумма: ' + str(amount) + ' 💰')}\n"
                f"{f.list_item('Получатель: ' + creditor_name)}")
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
        # Уведомление кредитору
        try:
            await context.bot.send_message(
                chat_id=creditor_id,
                text=(f.header("ДОЛГ ОПЛАЧЕН", "💰") + "\n\n"
                      f"{f.list_item('Должник: ' + update.effective_user.first_name)}\n"
                      f"{f.list_item('Сумма: ' + str(amount) + ' 💰')}")
            )
        except:
            pass

    # ========== МОДУЛЬ ДОСТИЖЕНИЙ ==========
    
    async def cmd_achievements(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список достижений"""
        user_id = update.effective_user.id
        achievements = self.db.get_achievements(user_id)
        
        if not achievements:
            text = (f.header("ДОСТИЖЕНИЯ", "🏆") + "\n\n"
                    f"{f.info('У тебя пока нет достижений')}\n\n"
                    f"{f.section('ДОСТУПНЫЕ ДОСТИЖЕНИЯ')}\n"
                    f"{f.list_item('👾 Охотник на боссов — убить 10 боссов (+500 💰)')}\n"
                    f"{f.list_item('👾 Легендарный охотник — убить 50 боссов (+2000 💰)')}\n"
                    f"{f.list_item('📈 Новичок — достичь 10 уровня')}\n"
                    f"{f.list_item('📈 Ветеран — достичь 25 уровня')}\n"
                    f"{f.list_item('🎰 Игроман — сыграть 50 игр в казино')}\n"
                    f"{f.list_item('🔪 Мафиози — выиграть 10 игр в мафию')}\n"
                    f"{f.list_item('👥 Социальный — вступить в клан')}\n"
                    f"{f.list_item('💎 Богач — накопить 10000 монет')}")
            
            await update.message.reply_text(text, parse_mode='Markdown')
            return
        
        text = f.header("ТВОИ ДОСТИЖЕНИЯ", "🏆") + "\n\n"
        
        for name, desc, date, reward in achievements:
            date_obj = datetime.datetime.fromisoformat(date)
            date_str = date_obj.strftime("%d.%m.%Y")
            text += f"**{name}**\n└ {desc}\n└ 📅 {date_str}"
            if reward > 0:
                text += f" (+{reward} 💰)"
            text += "\n\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    # ========== ПРОЧИЕ КОМАНДЫ ==========
    
    async def cmd_weather(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Погода (имитация)"""
        city = " ".join(context.args) if context.args else "Москва"
        
        weathers = ["☀️ солнечно", "⛅ облачно", "☁️ пасмурно", "🌧 дождь", "⛈ гроза", "❄️ снег", "🌫 туман"]
        temp = random.randint(-20, 35)
        wind = random.randint(0, 20)
        humidity = random.randint(30, 95)
        weather = random.choice(weathers)
        
        text = (f.header(f"ПОГОДА: {city.upper()}", "🌍") + "\n\n"
                f"{weather}, {temp}°C\n"
                f"💨 Ветер: {wind} м/с\n"
                f"💧 Влажность: {humidity}%\n"
                f"📅 {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}")
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_news(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Новости бота"""
        news_list = [
            "🎉 Мега-обновление! Бот объединил Iris, TrueMafia, TReanfer и Anya!",
            "👾 Новые боссы уже на арене! Проверь /bosses",
            "🔪 Мафия теперь с полными ролями! Играй в /mafia",
            "💰 Введены кристаллы — новая валюта для донатеров!",
            "🏆 Система достижений запущена! Собирай /achievements",
            "👥 Кланы теперь с рейтингами! Создай свой /clancreate",
            "🎰 Казино обновлено: добавлен блэкджек!",
            "📊 Топ игроков теперь показывает лидеров по разным категориям"
        ]
        
        text = (f.header("НОВОСТИ", "📰") + "\n\n"
                f"{random.choice(news_list)}")
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_quote(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Цитата дня"""
        quotes = [
            "Успех — это способность идти от поражения к поражению, не теряя энтузиазма.",
            "Сложнее всего начать действовать, все остальное зависит только от упорства.",
            "Лучший способ предсказать будущее — создать его.",
            "Не бойтесь, что у вас не получится. Бойтесь, что вы не попробуете.",
            "Будь собой, остальные роли уже заняты.",
            "Падать — часть жизни, подниматься — ее смысл.",
            "Сегодня ты там, куда тебя привели твои вчерашние мысли.",
            "Жизнь — как коробка шоколадных конфет: никогда не знаешь, какая начинка тебе попадётся."
        ]
        
        text = (f.header("ЦИТАТА ДНЯ", "📝") + "\n\n"
                f"«{random.choice(quotes)}»")
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_players(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Количество игроков"""
        count = self.db.get_players_count()  # Нужно добавить этот метод в Database
        
        text = (f.header("СТАТИСТИКА", "👥") + "\n\n"
                f"Всего игроков: {count}")
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_mycrime(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Случайная статья УК РФ"""
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
            ("159", "Мошенничество"),
            ("213", "Хулиганство")
        ]
        
        article_num, article_name = random.choice(crimes)
        sentence = random.randint(1, 15)
        
        today = datetime.datetime.now().strftime("%d.%m.%Y")
        user = update.effective_user
        
        text = (f"🤷‍♂️ Сегодня {today} {f.user_link(user.id, user.first_name)} "
                f"приговаривается к статье {article_num}. {article_name}\n"
                f"⏱ Срок: {sentence} {'год' if sentence == 1 else 'года' if sentence < 5 else 'лет'}")
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_eng_free(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Бесплатная энергия (раз в час)"""
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)
        
        last_free = user_data.get('last_free_energy')
        if last_free:
            last = datetime.datetime.fromisoformat(last_free)
            if (datetime.datetime.now() - last).seconds < 3600:
                remaining = 3600 - (datetime.datetime.now() - last).seconds
                minutes = remaining // 60
                await update.message.reply_text(f.error(f"Бесплатную энергию можно получать раз в час. Осталось: {minutes} мин"))
                return
        
        energy = 20
        self.db.add_energy(user_id, energy)
        
        self.db.cursor.execute(
            "UPDATE users SET last_free_energy = ? WHERE user_id = ?",
            (datetime.datetime.now(), user_id)
        )
        self.db.conn.commit()
        
        await update.message.reply_text(f.success(f"Получено {energy} ⚡ энергии"), parse_mode='Markdown')
    
    async def cmd_sms(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Личное сообщение"""
        if len(context.args) < 2:
            await update.message.reply_text(f.error("Использование: /sms @user сообщение"))
            return
        
        query = context.args[0]
        message = " ".join(context.args[1:])
        
        target_user = self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        sender = update.effective_user
        
        try:
            await context.bot.send_message(
                chat_id=target_user['user_id'],
                text=(f.header("ЛИЧНОЕ СООБЩЕНИЕ", "💬") + "\n\n"
                      f"{f.list_item('От: ' + f.user_link(sender.id, sender.first_name))}\n"
                      f"{f.list_item('Сообщение: ' + message)}")
            )
            await update.message.reply_text(f.success("Сообщение отправлено!"), parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f.error("Не удалось отправить сообщение. Возможно, пользователь не запускал бота."))
    
    # ========== ОБРАБОТЧИКИ СООБЩЕНИЙ ==========
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка обычных сообщений (AI-чат)"""
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
            await update.message.reply_text(f.error(f"Вы в муте. Осталось: {remaining}"))
            return
        
        if await self.check_spam(update):
            return
        
        # Проверка триггеров (Iris feature)
        chat_id = update.effective_chat.id
        trigger_response = self.db.check_trigger(chat_id, message_text)
        if trigger_response:
            await update.message.reply_text(trigger_response, parse_mode='Markdown')
            return
        
        # AI-ответ
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        response = await self.ai.get_response(user.id, message_text)
        await update.message.reply_text(f"🤖 {response}", parse_mode='Markdown')
    
    async def handle_new_members(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Приветствие новых участников"""
        chat_id = update.effective_chat.id
        welcome = self.db.get_welcome(chat_id)
        
        for member in update.message.new_chat_members:
            if member.is_bot:
                continue
            
            if welcome:
                text = welcome.replace('{user}', f.user_link(member.id, member.first_name))
            else:
                text = f"👋 Добро пожаловать, {f.user_link(member.id, member.first_name)}!\nИспользуй /help для списка команд."
            
            await update.message.reply_text(text, parse_mode='Markdown')
    
    async def handle_left_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Прощание с уходящими участниками"""
        member = update.message.left_chat_member
        if member.is_bot:
            return
        
        await update.message.reply_text(
            f"👋 {member.first_name} покинул чат. Будем ждать возвращения!",
            parse_mode='Markdown'
        )
    
    # ========== CALLBACK КНОПКИ ==========
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатий на инлайн-кнопки"""
        query = update.callback_query
        await query.answer()
        data = query.data
        user = query.from_user
        
        if data == "noop":
            return
        
        elif data == "menu_back":
            await query.edit_message_text(
                f.header("ГЛАВНОЕ МЕНЮ", "🎮") + "\n\nВыбери раздел:",
                reply_markup=IrisKeyboard.main_menu(),
                parse_mode='Markdown'
            )
        
        elif data == "menu_profile":
            await self.cmd_profile(update, context)
        
        elif data == "menu_moderation":
            text = (f.header("МОДЕРАЦИЯ", "🛡️") + "\n\n"
                    f"{f.section('ОСНОВНЫЕ КОМАНДЫ')}\n"
                    f"{f.command('warn @user [причина]', 'предупреждение')}\n"
                    f"{f.command('mute @user минут [причина]', 'заглушить')}\n"
                    f"{f.command('ban @user [причина]', 'заблокировать')}\n"
                    f"{f.command('kick @user', 'исключить')}\n"
                    f"{f.command('banlist', 'список банов')}\n"
                    f"{f.command('mutelist', 'список мутов')}\n\n"
                    f"{f.section('НАСТРОЙКИ ЧАТА')}\n"
                    f"{f.command('rules', 'правила')}\n"
                    f"{f.command('setrules [текст]', 'установить правила')}\n"
                    f"{f.command('welcome', 'приветствие')}\n"
                    f"{f.command('setwelcome [текст]', 'установить приветствие')}")
            
            await query.edit_message_text(
                text,
                reply_markup=IrisKeyboard.back_button(),
                parse_mode='Markdown'
            )
        
        elif data == "menu_mafia":
            await self.cmd_mafia(update, context)
        
        elif data == "menu_economy":
            text = (f.header("ЭКОНОМИКА", "💰") + "\n\n"
                    f"{f.section('МАГАЗИН')}\n"
                    f"{f.command('shop', 'магазин')}\n"
                    f"{f.command('buy [ID]', 'купить предмет')}\n"
                    f"{f.command('inventory', 'инвентарь')}\n\n"
                    f"{f.section('ПЕРЕВОДЫ')}\n"
                    f"{f.command('pay @user сумма', 'перевести монеты')}\n"
                    f"{f.command('paydiamond @user сумма', 'перевести алмазы')}\n\n"
                    f"{f.section('БОНУСЫ')}\n"
                    f"{f.command('daily', 'ежедневный бонус')}\n"
                    f"{f.command('weekly', 'недельный бонус')}\n"
                    f"{f.command('streak', 'текущий стрик')}")
            
            await query.edit_message_text(
                text,
                reply_markup=IrisKeyboard.back_button(),
                parse_mode='Markdown'
            )
        
        elif data == "menu_games":
            text = (f.header("ИГРЫ", "🎮") + "\n\n"
                    f"{f.section('БОССЫ')}\n"
                    f"{f.command('bosses', 'список боссов')}\n"
                    f"{f.command('bossfight [ID]', 'атаковать босса')}\n\n"
                    f"{f.section('КАЗИНО')}\n"
                    f"{f.command('casino', 'меню казино')}\n"
                    f"{f.command('roulette [ставка] [цвет]', 'рулетка')}\n"
                    f"{f.command('dice [ставка]', 'кости')}\n\n"
                    f"{f.section('МИНИ-ИГРЫ')}\n"
                    f"{f.command('rps', 'камень-ножницы-бумага')}\n"
                    f"{f.command('ttt', 'крестики-нолики')}\n"
                    f"{f.command('memory', 'мемори')}\n"
                    f"{f.command('minesweeper', 'сапёр')}")
            
            await query.edit_message_text(
                text,
                reply_markup=IrisKeyboard.back_button(),
                parse_mode='Markdown'
            )
        
        elif data == "menu_ai":
            text = (f.header("AI-ЧАТ", "🤖") + "\n\n"
                    f"{f.info('Просто напиши мне что-нибудь!')}\n"
                    f"{f.list_item('Я отвечу с помощью Gemini AI')}\n"
                    f"{f.list_item('Понимаю контекст разговора')}\n"
                    f"{f.list_item('Могу помочь с любыми вопросами')}\n\n"
                    f"{f.section('ПРИМЕРЫ')}\n"
                    f"{f.list_item('Привет!')}\n"
                    f"{f.list_item('Расскажи анекдот')}\n"
                    f"{f.list_item('Что нового в боте?')}")
            
            await query.edit_message_text(
                text,
                reply_markup=IrisKeyboard.back_button(),
                parse_mode='Markdown'
            )
        
        elif data == "menu_donate":
            await self.cmd_donate(update, context)
        
        elif data == "menu_help":
            await self.cmd_help(update, context)
        
        elif data == "edit_profile":
            await self.cmd_edit_profile(update, context)
        
        elif data.startswith("boss_fight_"):
            boss_id = int(data.split('_')[2])
            context.args = [str(boss_id)]
            await self.cmd_boss_fight(update, context)
        
        elif data.startswith("banlist_page_"):
            page = int(data.split('_')[2])
            context.args = [str(page)]
            await self.cmd_banlist(update, context)
        
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
            
            text = f.header("КНБ", "✊") + "\n\n"
            text += f"{emoji[choice]} **Вы:** {names[choice]}\n"
            text += f"{emoji[bot_choice]} **Бот:** {names[bot_choice]}\n\n"
            
            if choice == bot_choice:
                self.db.add_stat(user.id, "rps_draws", 1)
                text += f.info("🤝 **НИЧЬЯ!**")
            elif results.get((choice, bot_choice)) == "win":
                self.db.add_stat(user.id, "rps_wins", 1)
                reward = random.randint(10, 30)
                self.db.add_coins(user.id, reward)
                text += f.success(f"🎉 **ПОБЕДА!** +{reward} 💰")
            else:
                self.db.add_stat(user.id, "rps_losses", 1)
                text += f.error("😢 **ПОРАЖЕНИЕ!**")
            
            await query.edit_message_text(
                text,
                reply_markup=IrisKeyboard.back_button(),
                parse_mode='Markdown'
            )
        
        elif data in ["mafia_create", "mafia_join", "mafia_start", "mafia_vote"]:
            if data == "mafia_create":
                await self.cmd_mafia_create(update, context)
            elif data == "mafia_join":
                await self.cmd_mafia_join(update, context)
            elif data == "mafia_start":
                await self.cmd_mafia_start(update, context)
            elif data == "mafia_vote":
                await self.cmd_mafia_vote(update, context)
    
    # ========== ЗАПУСК ==========
    
    def run(self):
        """Запуск бота"""
        print("=" * 60)
        print("🚀 ЗАПУСК МЕГА-БОТА «СПЕКТР»")
        print("=" * 60)
        print("📦 Модули:")
        print("  ✅ Iris (полная модерация)")
        print("  ✅ TrueMafia (классическая мафия)")
        print("  ✅ TReanfer (экономика и донат)")
        print("  ✅ Anya (AI-чат с Gemini)")
        print("  ✅ Твои игры (боссы, казино, КНБ, ТТТ, мемори, сапёр)")
        print("=" * 60)
        print("👑 Владелец:", OWNER_USERNAME)
        print("=" * 60)
        
        self.application.run_polling()


# ========== ТОЧКА ВХОДА ==========
if __name__ == "__main__":
    bot = SpectrumBot()
    bot.run()
