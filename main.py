#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SPECTRUM BOT - Официальная версия
Telegram бот с красивым оформлением
"""

import asyncio
import logging
import random
import sqlite3
import datetime
from typing import Optional, Dict, Any, List, Tuple
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

# ========== НАСТРОЙКА ЛОГИРОВАНИЯ ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== КОНФИГУРАЦИЯ ==========
TELEGRAM_TOKEN = "8326390250:AAG1nTYdy07AuKsYXS3yvDehfU2JuR0RqGo"
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

# ========== БАЗА ДАННЫХ ==========
class Database:
    def __init__(self, db_name="spectrum.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
        print("✅ База данных инициализирована")

    def create_tables(self):
        # Таблица пользователей
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                username TEXT,
                first_name TEXT,
                coins INTEGER DEFAULT 1000,
                diamonds INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                exp INTEGER DEFAULT 0,
                role TEXT DEFAULT 'user',
                warns INTEGER DEFAULT 0,
                warns_list TEXT DEFAULT '[]',
                mute_until TIMESTAMP,
                banned INTEGER DEFAULT 0,
                health INTEGER DEFAULT 100,
                armor INTEGER DEFAULT 0,
                damage INTEGER DEFAULT 10,
                boss_kills INTEGER DEFAULT 0,
                vip_until TIMESTAMP,
                premium_until TIMESTAMP,
                clan_id INTEGER DEFAULT 0,
                rps_wins INTEGER DEFAULT 0,
                rps_losses INTEGER DEFAULT 0,
                rps_draws INTEGER DEFAULT 0,
                casino_wins INTEGER DEFAULT 0,
                casino_losses INTEGER DEFAULT 0,
                nickname TEXT,
                title TEXT DEFAULT '',
                motto TEXT DEFAULT 'Нет девиза',
                rep INTEGER DEFAULT 0,
                last_seen TIMESTAMP,
                daily_streak INTEGER DEFAULT 0,
                last_daily TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица боссов
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS bosses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                level INTEGER,
                health INTEGER,
                max_health INTEGER,
                damage INTEGER,
                reward INTEGER,
                is_alive INTEGER DEFAULT 1
            )
        ''')
        
        # Таблица кланов
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS clans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                owner_id INTEGER,
                level INTEGER DEFAULT 1,
                exp INTEGER DEFAULT 0,
                members INTEGER DEFAULT 1,
                rating INTEGER DEFAULT 0
            )
        ''')
        
        # Таблица участников клана
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS clan_members (
                clan_id INTEGER,
                user_id INTEGER,
                role TEXT DEFAULT 'member',
                joined_at TIMESTAMP,
                UNIQUE(clan_id, user_id)
            )
        ''')
        
        self.conn.commit()
        self.init_bosses()
    
    def init_bosses(self):
        self.cursor.execute("SELECT COUNT(*) FROM bosses")
        if self.cursor.fetchone()[0] == 0:
            bosses = [
                ("Ядовитый комар", 5, 500, 15, 250),
                ("Лесной тролль", 10, 1000, 25, 500),
                ("Огненный дракон", 15, 2000, 40, 1000),
                ("Ледяной великан", 20, 3500, 60, 2000),
                ("Король демонов", 25, 5000, 85, 3500),
                ("Бог разрушения", 30, 10000, 150, 5000)
            ]
            for name, level, health, damage, reward in bosses:
                self.cursor.execute(
                    "INSERT INTO bosses (name, level, health, max_health, damage, reward) VALUES (?, ?, ?, ?, ?, ?)",
                    (name, level, health, health, damage, reward)
                )
            self.conn.commit()
    
    def get_or_create_user(self, telegram_id: int, first_name: str = "Player") -> Dict:
        self.cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        user = self.cursor.fetchone()
        
        if not user:
            role = 'owner' if telegram_id == OWNER_ID else 'user'
            self.cursor.execute(
                "INSERT INTO users (telegram_id, first_name, role, last_seen) VALUES (?, ?, ?, ?)",
                (telegram_id, first_name, role, datetime.datetime.now())
            )
            self.conn.commit()
            return self.get_or_create_user(telegram_id, first_name)
        
        self.cursor.execute(
            "UPDATE users SET last_seen = ? WHERE telegram_id = ?",
            (datetime.datetime.now(), telegram_id)
        )
        self.conn.commit()
        
        columns = [description[0] for description in self.cursor.description]
        return dict(zip(columns, user))
    
    def get_user_by_id(self, user_id: int) -> Dict:
        self.cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = self.cursor.fetchone()
        if not user:
            return {}
        columns = [description[0] for description in self.cursor.description]
        return dict(zip(columns, user))
    
    def add_coins(self, user_id: int, amount: int):
        self.cursor.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (amount, user_id))
        self.conn.commit()
    
    def add_exp(self, user_id: int, amount: int):
        self.cursor.execute("UPDATE users SET exp = exp + ? WHERE user_id = ?", (amount, user_id))
        self.conn.commit()
    
    def add_stat(self, user_id: int, stat: str, value: int = 1):
        self.cursor.execute(f"UPDATE users SET {stat} = {stat} + ? WHERE user_id = ?", (value, user_id))
        self.conn.commit()
    
    def get_bosses(self, alive_only=True):
        if alive_only:
            self.cursor.execute("SELECT * FROM bosses WHERE is_alive = 1")
        else:
            self.cursor.execute("SELECT * FROM bosses")
        return self.cursor.fetchall()
    
    def damage_boss(self, boss_id, damage):
        self.cursor.execute("UPDATE bosses SET health = health - ? WHERE id = ?", (damage, boss_id))
        self.conn.commit()
        
        self.cursor.execute("SELECT health FROM bosses WHERE id = ?", (boss_id,))
        health = self.cursor.fetchone()[0]
        
        if health <= 0:
            self.cursor.execute("UPDATE bosses SET is_alive = 0 WHERE id = ?", (boss_id,))
            self.conn.commit()
            return True
        return False
    
    def respawn_bosses(self):
        self.cursor.execute("UPDATE bosses SET is_alive = 1, health = max_health")
        self.conn.commit()
    
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

# Инициализация БД
db = Database()

# ========== ФОРМАТТЕР ТЕКСТА ==========
class Formatter:
    @staticmethod
    def header(text: str) -> str:
        return f"\n📌 **{text}**\n" + "━" * 25 + "\n"
    
    @staticmethod
    def section(text: str) -> str:
        return f"\n▫️ **{text}**"
    
    @staticmethod
    def cmd(name: str, desc: str, params: str = "") -> str:
        if params:
            return f"• `/{name} {params}` — {desc}"
        return f"• `/{name}` — {desc}"
    
    @staticmethod
    def item(text: str) -> str:
        return f"• {text}"
    
    @staticmethod
    def stat(name: str, value: str) -> str:
        return f"▫️ **{name}:** {value}"
    
    @staticmethod
    def success(text: str) -> str:
        return f"✅ {text}"
    
    @staticmethod
    def error(text: str) -> str:
        return f"❌ {text}"
    
    @staticmethod
    def info(text: str) -> str:
        return f"ℹ️ {text}"
    
    @staticmethod
    def warn(text: str) -> str:
        return f"⚠️ {text}"
    
    @staticmethod
    def link(user_id: int, name: str) -> str:
        return f"[{name}](tg://user?id={user_id})"

f = Formatter()

# ========== КЛАВИАТУРЫ ==========
class Keyboards:
    @staticmethod
    def main_menu():
        keyboard = [
            [InlineKeyboardButton("👤 ПРОФИЛЬ", callback_data="profile"),
             InlineKeyboardButton("📊 ТОП", callback_data="top")],
            [InlineKeyboardButton("👾 БОССЫ", callback_data="bosses"),
             InlineKeyboardButton("🎰 КАЗИНО", callback_data="casino")],
            [InlineKeyboardButton("👥 КЛАНЫ", callback_data="clan"),
             InlineKeyboardButton("💰 МАГАЗИН", callback_data="shop")],
            [InlineKeyboardButton("💎 ПРИВИЛЕГИИ", callback_data="donate"),
             InlineKeyboardButton("📚 ПОМОЩЬ", callback_data="help")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def back():
        keyboard = [[InlineKeyboardButton("🔙 НАЗАД", callback_data="menu")]]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def bosses(bosses):
        keyboard = []
        for boss in bosses[:3]:
            keyboard.append([InlineKeyboardButton(
                f"⚔️ {boss[1]}", 
                callback_data=f"boss_fight_{boss[0]}"
            )])
        keyboard.append([InlineKeyboardButton("🔙 НАЗАД", callback_data="menu")])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def casino():
        keyboard = [
            [InlineKeyboardButton("🎰 РУЛЕТКА", callback_data="roulette"),
             InlineKeyboardButton("🎲 КОСТИ", callback_data="dice")],
            [InlineKeyboardButton("🃏 БЛЭКДЖЕК", callback_data="blackjack"),
             InlineKeyboardButton("🎰 СЛОТЫ", callback_data="slots")],
            [InlineKeyboardButton("🔙 НАЗАД", callback_data="menu")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def rps():
        keyboard = [
            [InlineKeyboardButton("🪨 КАМЕНЬ", callback_data="rps_rock"),
             InlineKeyboardButton("✂️ НОЖНИЦЫ", callback_data="rps_scissors"),
             InlineKeyboardButton("📄 БУМАГА", callback_data="rps_paper")],
            [InlineKeyboardButton("🔙 НАЗАД", callback_data="casino")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def clan_menu(in_clan: bool):
        if in_clan:
            keyboard = [
                [InlineKeyboardButton("📊 ИНФО", callback_data="clan_info"),
                 InlineKeyboardButton("👥 УЧАСТНИКИ", callback_data="clan_members")],
                [InlineKeyboardButton("🚪 ПОКИНУТЬ", callback_data="clan_leave"),
                 InlineKeyboardButton("🔙 НАЗАД", callback_data="menu")]
            ]
        else:
            keyboard = [
                [InlineKeyboardButton("➕ СОЗДАТЬ", callback_data="clan_create"),
                 InlineKeyboardButton("🔍 ПРИСОЕДИНИТЬСЯ", callback_data="clan_join")],
                [InlineKeyboardButton("🏆 ТОП КЛАНОВ", callback_data="clan_top"),
                 InlineKeyboardButton("🔙 НАЗАД", callback_data="menu")]
            ]
        return InlineKeyboardMarkup(keyboard)

# ========== SPECTRUM AI ==========
class SpectrumAI:
    def __init__(self):
        self.contexts = defaultdict(list)
        print("🤖 Spectrum AI инициализирован")

    async def get_response(self, user_id: int, message: str) -> str:
        msg = message.lower()
        
        # Сохраняем в контекст
        if user_id not in self.contexts:
            self.contexts[user_id] = []
        self.contexts[user_id].append(f"User: {message}")
        if len(self.contexts[user_id]) > 5:
            self.contexts[user_id] = self.contexts[user_id][-5:]
        
        # Приветствия
        if any(word in msg for word in ["привет", "здравствуй", "хай", "ку"]):
            return "👋 Привет! Как твои дела? Чем могу помочь?"
        
        # Как дела
        if any(word in msg for word in ["как дела", "как ты", "чё как"]):
            return "😊 У меня всё отлично! А у тебя как настроение?"
        
        # Спасибо
        if any(word in msg for word in ["спасибо", "благодарю", "пасиб"]):
            return "🤝 Всегда пожалуйста! Рад помочь."
        
        # Кто создал
        if any(word in msg for word in ["кто создал", "создатель", "владелец"]):
            return f"👑 Меня создал {OWNER_USERNAME}"
        
        # Что умеешь
        if any(word in msg for word in ["что умеешь", "команды", "помощь"]):
            return "📚 Я умею многое! Напиши /help для списка команд."
        
        # Игры
        if any(word in msg for word in ["игра", "поиграть", "во что"]):
            return "🎮 У нас есть боссы (/bosses), казино (/casino) и КНБ (/rps)!"
        
        # Боссы
        if any(word in msg for word in ["босс", "битва"]):
            return "👾 Боссы ждут! Используй /bosses для просмотра."
        
        # Прощание
        if any(word in msg for word in ["пока", "до свидания", "удачи"]):
            return "👋 Пока! Заходи ещё, буду скучать!"
        
        # Вопросы
        if "?" in msg:
            return "❓ Хороший вопрос! Я не знаю точного ответа, но могу помочь с командами."
        
        # По умолчанию
        responses = [
            "😊 Расскажи подробнее!",
            "🤔 Интересно... А что дальше?",
            "💡 Понял, продолжай.",
            "🔥 Отлично! Есть что-то ещё?",
            "😉 Я внимательно слушаю."
        ]
        return random.choice(responses)

ai = SpectrumAI()

# ========== ОСНОВНОЙ КЛАСС БОТА ==========
class SpectrumBot:
    def __init__(self):
        self.db = db
        self.ai = ai
        self.application = Application.builder().token(TELEGRAM_TOKEN).build()
        self.setup_handlers()
        print("✅ Бот Spectrum инициализирован")

    def setup_handlers(self):
        # Команды
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        self.application.add_handler(CommandHandler("menu", self.cmd_menu))
        self.application.add_handler(CommandHandler("profile", self.cmd_profile))
        self.application.add_handler(CommandHandler("top", self.cmd_top))
        self.application.add_handler(CommandHandler("daily", self.cmd_daily))
        self.application.add_handler(CommandHandler("bosses", self.cmd_bosses))
        self.application.add_handler(CommandHandler("boss", self.cmd_boss_fight))
        self.application.add_handler(CommandHandler("casino", self.cmd_casino))
        self.application.add_handler(CommandHandler("roulette", self.cmd_roulette))
        self.application.add_handler(CommandHandler("dice", self.cmd_dice))
        self.application.add_handler(CommandHandler("blackjack", self.cmd_blackjack))
        self.application.add_handler(CommandHandler("slots", self.cmd_slots))
        self.application.add_handler(CommandHandler("rps", self.cmd_rps))
        self.application.add_handler(CommandHandler("clan", self.cmd_clan))
        self.application.add_handler(CommandHandler("shop", self.cmd_shop))
        self.application.add_handler(CommandHandler("donate", self.cmd_donate))
        self.application.add_handler(CommandHandler("vip", self.cmd_vip))
        self.application.add_handler(CommandHandler("premium", self.cmd_premium))
        
        # Callback для кнопок
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Обработка сообщений
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        print("✅ Обработчики зарегистрированы")

    # ========== ОСНОВНЫЕ КОМАНДЫ ==========
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_or_create_user(user.id, user.first_name)
        
        text = (f.header("SPECTRUM") + "\n"
                f"👋 **Привет, {user.first_name}!**\n\n"
                f"Я — твой игровой помощник. Умею:\n"
                f"• 👾 Сражаться с боссами\n"
                f"• 🎰 Играть в казино\n"
                f"• 👥 Управлять кланами\n"
                f"• 💰 Зарабатывать монеты\n\n"
                f"{f.stat('Монеты', str(user_data.get('coins', 1000)) + ' 💰')}\n"
                f"{f.stat('Уровень', str(user_data.get('level', 1)))}\n\n"
                f"Выбери раздел в меню:")
        
        await update.message.reply_text(
            text,
            reply_markup=Keyboards.main_menu(),
            parse_mode='Markdown'
        )
    
    async def cmd_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            f.header("ГЛАВНОЕ МЕНЮ") + "\nВыбери раздел:",
            reply_markup=Keyboards.main_menu(),
            parse_mode='Markdown'
        )
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (f.header("ПОМОЩЬ") + "\n"
                f"{f.cmd('profile', 'твой профиль')}\n"
                f"{f.cmd('top', 'топ игроков')}\n"
                f"{f.cmd('daily', 'ежедневный бонус')}\n"
                f"{f.cmd('bosses', 'список боссов')}\n"
                f"{f.cmd('boss [ID]', 'атаковать босса', '1')}\n"
                f"{f.cmd('casino', 'казино')}\n"
                f"{f.cmd('rps', 'камень-ножницы-бумага')}\n"
                f"{f.cmd('clan', 'кланы')}\n"
                f"{f.cmd('shop', 'магазин')}\n"
                f"{f.cmd('donate', 'привилегии')}")
        
        await update.message.reply_text(text, reply_markup=Keyboards.back(), parse_mode='Markdown')
    
    # ========== ПРОФИЛЬ ==========
    
    async def cmd_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_or_create_user(user.id, user.first_name)
        
        vip = "✅ VIP" if self.db.is_vip(user_data['user_id']) else "❌ Нет"
        premium = "✅ PREMIUM" if self.db.is_premium(user_data['user_id']) else "❌ Нет"
        
        text = (f.header("ПРОФИЛЬ") + "\n"
                f"**{user_data.get('nickname') or user.first_name}**\n"
                f"_{user_data.get('motto', 'Нет девиза')}_\n\n"
                f"{f.stat('Монеты', str(user_data.get('coins', 0)) + ' 💰')}\n"
                f"{f.stat('Уровень', str(user_data.get('level', 1)))}\n"
                f"{f.stat('Опыт', str(user_data.get('exp', 0)))}\n"
                f"{f.stat('Боссов убито', str(user_data.get('boss_kills', 0)))}\n\n"
                f"{f.stat('VIP', vip)}\n"
                f"{f.stat('Premium', premium)}\n"
                f"{f.stat('РПС побед', str(user_data.get('rps_wins', 0)))}\n"
                f"{f.stat('Казино побед', str(user_data.get('casino_wins', 0)))}")
        
        await update.message.reply_text(text, reply_markup=Keyboards.back(), parse_mode='Markdown')
    
    async def cmd_top(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = f.header("ТОП ИГРОКОВ") + "\n"
        text += "💰 **По монетам:**\n"
        
        self.db.cursor.execute("SELECT first_name, coins FROM users ORDER BY coins DESC LIMIT 5")
        for i, (name, coins) in enumerate(self.db.cursor.fetchall(), 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} {name} — {coins} 💰\n"
        
        await update.message.reply_text(text, reply_markup=Keyboards.back(), parse_mode='Markdown')
    
    async def cmd_daily(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_or_create_user(user.id, user.first_name)
        user_id = user_data['user_id']
        
        streak = self.db.add_daily_streak(user_id)
        
        coins = random.randint(100, 300)
        exp = random.randint(20, 60)
        
        coins = int(coins * (1 + min(streak, 30) * 0.05))
        
        self.db.add_coins(user_id, coins)
        self.db.add_exp(user_id, exp)
        
        text = (f.header("ЕЖЕДНЕВНЫЙ БОНУС") + "\n"
                f"🔥 Стрик: {streak} дней\n"
                f"💰 Монеты: +{coins}\n"
                f"✨ Опыт: +{exp}\n\n"
                f"Заходи завтра!")
        
        await update.message.reply_text(text, reply_markup=Keyboards.back(), parse_mode='Markdown')
    
    # ========== БОССЫ ==========
    
    async def cmd_bosses(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_or_create_user(user.id, user.first_name)
        bosses = self.db.get_bosses()
        
        if not bosses:
            self.db.respawn_bosses()
            bosses = self.db.get_bosses()
        
        text = f.header("АРЕНА БОССОВ") + "\n"
        
        if bosses:
            boss = bosses[0]
            health_bar = "█" * int(boss[3] * 10 / boss[4]) + "░" * (10 - int(boss[3] * 10 / boss[4]))
            text += (f"**{boss[1]}** (ур.{boss[2]})\n"
                    f"❤️ {boss[3]}/{boss[4]} {health_bar}\n"
                    f"⚔️ Урон: {boss[5]}\n"
                    f"💰 Награда: {boss[6]}\n\n")
        
        text += (f"⚡ Твоя энергия: {user_data.get('energy', 100)}/100\n"
                 f"❤️ Твоё здоровье: {user_data.get('health', 100)}/100")
        
        await update.message.reply_text(
            text,
            reply_markup=Keyboards.bosses(bosses),
            parse_mode='Markdown'
        )
    
    async def cmd_boss_fight(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Укажи ID босса: /boss 1")
            return
        
        try:
            boss_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ Неверный ID")
            return
        
        user = update.effective_user
        user_data = self.db.get_or_create_user(user.id, user.first_name)
        bosses = self.db.get_bosses()
        
        boss = None
        for b in bosses:
            if b[0] == boss_id:
                boss = b
                break
        
        if not boss:
            await update.message.reply_text("❌ Босс не найден")
            return
        
        if user_data['energy'] < 10:
            await update.message.reply_text("❌ Недостаточно энергии!")
            return
        
        self.db.add_stat(user_data['user_id'], "energy", -10)
        
        player_damage = user_data['damage'] + random.randint(-3, 3)
        boss_damage = boss[5] + random.randint(-3, 3)
        player_taken = max(1, boss_damage - user_data['armor'] // 2)
        
        killed = self.db.damage_boss(boss_id, player_damage)
        
        text = f.header("БИТВА") + "\n"
        text += f"⚔️ Твой урон: {player_damage}\n"
        text += f"💥 Урон босса: {player_taken}\n\n"
        
        if killed:
            reward = boss[6] * (1 + user_data['level'] // 10)
            self.db.add_coins(user_data['user_id'], reward)
            self.db.add_stat(user_data['user_id'], "boss_kills", 1)
            text += f"🎉 **ПОБЕДА!**\n💰 Награда: {reward}"
        else:
            text += f"👾 Босс ещё жив!"
        
        await update.message.reply_text(text, reply_markup=Keyboards.back(), parse_mode='Markdown')
    
    # ========== КАЗИНО ==========
    
    async def cmd_casino(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            f.header("КАЗИНО") + "\nВыбери игру:",
            reply_markup=Keyboards.casino(),
            parse_mode='Markdown'
        )
    
    async def cmd_roulette(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_or_create_user(user.id, user.first_name)
        
        bet = 10
        color = "red"
        
        if context.args:
            try:
                bet = int(context.args[0])
                if len(context.args) > 1:
                    color = context.args[1]
            except:
                pass
        
        if bet > user_data['coins']:
            await update.message.reply_text("❌ Недостаточно монет!")
            return
        
        num = random.randint(0, 36)
        colors = ["red", "black", "green"]
        if num == 0:
            result_color = "green"
        elif num in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]:
            result_color = "red"
        else:
            result_color = "black"
        
        win = (color == result_color)
        
        if win:
            multiplier = 36 if color == "green" else 2
            win_amount = bet * multiplier
            self.db.add_coins(user_data['user_id'], win_amount)
            result = f"🎉 Вы выиграли {win_amount} 💰!"
        else:
            self.db.add_coins(user_data['user_id'], -bet)
            result = f"😢 Вы проиграли {bet} 💰"
        
        text = (f.header("РУЛЕТКА") + "\n"
                f"🎲 Выпало: {num} {result_color}\n"
                f"💰 Ставка: {bet}\n\n"
                f"{result}")
        
        await update.message.reply_text(text, reply_markup=Keyboards.back(), parse_mode='Markdown')
    
    async def cmd_dice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_or_create_user(user.id, user.first_name)
        
        bet = 10
        if context.args:
            try:
                bet = int(context.args[0])
            except:
                pass
        
        if bet > user_data['coins']:
            await update.message.reply_text("❌ Недостаточно монет!")
            return
        
        dice1 = random.randint(1, 6)
        dice2 = random.randint(1, 6)
        total = dice1 + dice2
        
        if total in [7, 11]:
            win = bet * 2
            result = f"🎉 Вы выиграли {win} 💰!"
        elif total in [2, 3, 12]:
            win = 0
            result = f"😢 Вы проиграли {bet} 💰"
        else:
            win = bet
            result = f"🔄 Ничья, ставка возвращена"
        
        if win > 0:
            self.db.add_coins(user_data['user_id'], win)
        
        text = (f.header("КОСТИ") + "\n"
                f"🎲 {dice1} + {dice2} = {total}\n"
                f"💰 Ставка: {bet}\n\n"
                f"{result}")
        
        await update.message.reply_text(text, reply_markup=Keyboards.back(), parse_mode='Markdown')
    
    async def cmd_blackjack(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_or_create_user(user.id, user.first_name)
        
        bet = 10
        if context.args:
            try:
                bet = int(context.args[0])
            except:
                pass
        
        if bet > user_data['coins']:
            await update.message.reply_text("❌ Недостаточно монет!")
            return
        
        player = random.randint(12, 21)
        dealer = random.randint(12, 21)
        
        if player > 21:
            result = "lose"
        elif dealer > 21 or player > dealer:
            result = "win"
        elif player < dealer:
            result = "lose"
        else:
            result = "draw"
        
        if result == "win":
            win = bet * 2
            self.db.add_coins(user_data['user_id'], win)
            result_text = f"🎉 Вы выиграли {win} 💰!"
        elif result == "lose":
            self.db.add_coins(user_data['user_id'], -bet)
            result_text = f"😢 Вы проиграли {bet} 💰"
        else:
            result_text = f"🔄 Ничья, ставка возвращена"
        
        text = (f.header("БЛЭКДЖЕК") + "\n"
                f"🎴 Вы: {player}\n"
                f"🃏 Дилер: {dealer}\n\n"
                f"{result_text}")
        
        await update.message.reply_text(text, reply_markup=Keyboards.back(), parse_mode='Markdown')
    
    async def cmd_slots(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_or_create_user(user.id, user.first_name)
        
        bet = 10
        if context.args:
            try:
                bet = int(context.args[0])
            except:
                pass
        
        if bet > user_data['coins']:
            await update.message.reply_text("❌ Недостаточно монет!")
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
            result = f"🎉 ДЖЕКПОТ! +{win} 💰"
        elif len(set(spin)) == 2:
            win = bet * 2
            result = f"🎉 Маленький выигрыш! +{win} 💰"
        else:
            win = 0
            result = f"😢 Не повезло... -{bet} 💰"
        
        if win > 0:
            self.db.add_coins(user_data['user_id'], win)
        else:
            self.db.add_coins(user_data['user_id'], -bet)
        
        text = (f.header("СЛОТЫ") + "\n"
                f"{' '.join(spin)}\n\n"
                f"{result}")
        
        await update.message.reply_text(text, reply_markup=Keyboards.back(), parse_mode='Markdown')
    
    async def cmd_rps(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            f.header("КАМЕНЬ-НОЖНИЦЫ-БУМАГА") + "\nВыбери:",
            reply_markup=Keyboards.rps(),
            parse_mode='Markdown'
        )
    
    # ========== КЛАНЫ ==========
    
    async def cmd_clan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_or_create_user(user.id, user.first_name)
        
        in_clan = user_data.get('clan_id', 0) != 0
        
        await update.message.reply_text(
            f.header("КЛАНЫ") + "\n" + ("Ты в клане" if in_clan else "Ты не в клане"),
            reply_markup=Keyboards.clan_menu(in_clan),
            parse_mode='Markdown'
        )
    
    # ========== МАГАЗИН ==========
    
    async def cmd_shop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (f.header("МАГАЗИН") + "\n"
                f"{f.item('Зелье здоровья — 50 💰')}\n"
                f"{f.item('Большое зелье — 100 💰')}\n"
                f"{f.item('Меч — 200 💰')}\n"
                f"{f.item('Легендарный меч — 500 💰')}\n"
                f"{f.item('Щит — 150 💰')}\n"
                f"{f.item('Энергетик — 30 💰')}\n\n"
                f"Купить: /buy [название]")
        
        await update.message.reply_text(text, reply_markup=Keyboards.back(), parse_mode='Markdown')
    
    async def cmd_donate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (f.header("ПРИВИЛЕГИИ") + "\n"
                f"🌟 **VIP** — {VIP_PRICE} 💰\n"
                f"• Урон +20%\n"
                f"• Награда +50%\n"
                f"• Бонусы +50%\n\n"
                f"💎 **PREMIUM** — {PREMIUM_PRICE} 💰\n"
                f"• Урон +50%\n"
                f"• Награда +100%\n"
                f"• Бонусы +100%\n\n"
                f"Купить: /vip или /premium")
        
        await update.message.reply_text(text, reply_markup=Keyboards.back(), parse_mode='Markdown')
    
    async def cmd_vip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_or_create_user(user.id, user.first_name)
        
        if user_data['coins'] < VIP_PRICE:
            await update.message.reply_text(f"❌ Недостаточно монет! Нужно {VIP_PRICE}")
            return
        
        self.db.add_coins(user_data['user_id'], -VIP_PRICE)
        vip_until = datetime.datetime.now() + datetime.timedelta(days=VIP_DAYS)
        self.db.cursor.execute(
            "UPDATE users SET vip_until = ?, role = 'vip' WHERE user_id = ?",
            (vip_until, user_data['user_id'])
        )
        self.db.conn.commit()
        
        await update.message.reply_text(f"✅ VIP статус активирован на {VIP_DAYS} дней!")
    
    async def cmd_premium(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_or_create_user(user.id, user.first_name)
        
        if user_data['coins'] < PREMIUM_PRICE:
            await update.message.reply_text(f"❌ Недостаточно монет! Нужно {PREMIUM_PRICE}")
            return
        
        self.db.add_coins(user_data['user_id'], -PREMIUM_PRICE)
        premium_until = datetime.datetime.now() + datetime.timedelta(days=PREMIUM_DAYS)
        self.db.cursor.execute(
            "UPDATE users SET premium_until = ?, role = 'premium' WHERE user_id = ?",
            (premium_until, user_data['user_id'])
        )
        self.db.conn.commit()
        
        await update.message.reply_text(f"✅ PREMIUM статус активирован на {PREMIUM_DAYS} дней!")

    # ========== ОБРАБОТКА КНОПОК ==========
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        
        print(f"🔘 Нажата кнопка: {data}")
        
        # Главное меню
        if data == "menu":
            await self.cmd_menu(update, context)
            return
        
        if data == "profile":
            await self.cmd_profile(update, context)
            return
        
        if data == "top":
            await self.cmd_top(update, context)
            return
        
        if data == "bosses":
            await self.cmd_bosses(update, context)
            return
        
        if data == "casino":
            await self.cmd_casino(update, context)
            return
        
        if data == "clan":
            await self.cmd_clan(update, context)
            return
        
        if data == "shop":
            await self.cmd_shop(update, context)
            return
        
        if data == "donate":
            await self.cmd_donate(update, context)
            return
        
        if data == "help":
            await self.cmd_help(update, context)
            return
        
        # Казино
        if data == "roulette":
            await self.cmd_roulette(update, context)
            return
        
        if data == "dice":
            await self.cmd_dice(update, context)
            return
        
        if data == "blackjack":
            await self.cmd_blackjack(update, context)
            return
        
        if data == "slots":
            await self.cmd_slots(update, context)
            return
        
        # КНБ
        if data.startswith("rps_"):
            choice = data.split('_')[1]
            await self.play_rps(update, choice)
            return
        
        # Боссы
        if data.startswith("boss_fight_"):
            boss_id = int(data.split('_')[2])
            context.args = [str(boss_id)]
            await self.cmd_boss_fight(update, context)
            return
        
        await query.edit_message_text("❓ Неизвестная команда", reply_markup=Keyboards.back())
    
    async def play_rps(self, update: Update, choice: str):
        query = update.callback_query
        user = update.effective_user
        user_data = self.db.get_or_create_user(user.id, user.first_name)
        
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
        
        text = f"{emoji[choice]} Вы: {names[choice]}\n{emoji[bot_choice]} Бот: {names[bot_choice]}\n\n"
        
        if choice == bot_choice:
            self.db.add_stat(user_data['user_id'], "rps_draws", 1)
            text += "🤝 **НИЧЬЯ!**"
        elif results.get((choice, bot_choice)) == "win":
            self.db.add_stat(user_data['user_id'], "rps_wins", 1)
            reward = random.randint(10, 30)
            self.db.add_coins(user_data['user_id'], reward)
            text += f"🎉 **ПОБЕДА!** +{reward} 💰"
        else:
            self.db.add_stat(user_data['user_id'], "rps_losses", 1)
            text += "😢 **ПОРАЖЕНИЕ!**"
        
        await query.edit_message_text(text, reply_markup=Keyboards.back(), parse_mode='Markdown')
    
    # ========== ОБРАБОТКА СООБЩЕНИЙ ==========
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        text = update.message.text
        
        if text.startswith('/'):
            return
        
        user_data = self.db.get_or_create_user(user.id, user.first_name)
        
        response = await self.ai.get_response(user.id, text)
        await update.message.reply_text(f"🤖 {response}", parse_mode='Markdown')
    
    # ========== ЗАПУСК ==========
    
    def run(self):
        print("=" * 60)
        print("🚀 ЗАПУСК БОТА SPECTRUM")
        print("=" * 60)
        
        # Удаляем вебхук
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.application.bot.delete_webhook(drop_pending_updates=True))
        
        print("✅ Вебхук удален")
        print("🚀 Запуск polling...")
        
        self.application.run_polling(drop_pending_updates=True)


# ========== ТОЧКА ВХОДА ==========
if __name__ == "__main__":
    bot = SpectrumBot()
    bot.run()
