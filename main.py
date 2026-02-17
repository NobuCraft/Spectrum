#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
СПЕКТР - SPECTRUM BOT
Официальный игровой бот
Версия 1.0
"""

import asyncio
import logging
import random
import sqlite3
import datetime
from typing import Optional, Dict, Any, List, Tuple
import json
import os
import sys
import signal
import time
import hashlib
from collections import defaultdict
import traceback

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

# ========== ЗАЩИТА ОТ МНОЖЕСТВЕННЫХ ЭКЗЕМПЛЯРОВ ==========
LOCK_FILE = None
TOKEN = "8326390250:AAG1nTYdy07AuKsYXS3yvDehfU2JuR0RqGo"
TOKEN_HASH = hashlib.md5(TOKEN.encode()).hexdigest()[:8]

def cleanup_lock():
    global LOCK_FILE
    if LOCK_FILE and os.path.exists(LOCK_FILE):
        try:
            os.remove(LOCK_FILE)
        except:
            pass

def ensure_single_instance():
    global LOCK_FILE
    lock_dir = "/tmp/spectrum_locks"
    try:
        os.makedirs(lock_dir, exist_ok=True)
    except:
        lock_dir = "."
    
    LOCK_FILE = os.path.join(lock_dir, f"bot_{TOKEN_HASH}.lock")
    
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, 'r') as f:
                old_pid = int(f.read().strip())
            try:
                os.kill(old_pid, 0)
                os.kill(old_pid, signal.SIGTERM)
                time.sleep(2)
            except:
                pass
        except:
            pass
    
    with open(LOCK_FILE, 'w') as f:
        f.write(str(os.getpid()))

ensure_single_instance()

# ========== КОНФИГУРАЦИЯ ==========
class Config:
    TELEGRAM_TOKEN = TOKEN
    OWNER_ID = 1732658530
    OWNER_USERNAME = "@NobuCraft"
    SPAM_LIMIT = 5
    SPAM_WINDOW = 3
    SPAM_MUTE_TIME = 120
    VIP_PRICE = 5000
    PREMIUM_PRICE = 15000
    VIP_DAYS = 30
    PREMIUM_DAYS = 30
    MAX_NICK_LENGTH = 30
    MAX_TITLE_LENGTH = 30
    MAX_MOTTO_LENGTH = 100
    DAILY_COOLDOWN = 86400
    WEEKLY_COOLDOWN = 604800

# ========== ФОРМАТТЕР ==========
class Formatter:
    SEPARATOR = "─" * 30
    SEPARATOR_LIGHT = "╌" * 30
    SEPARATOR_DOUBLE = "═" * 30

    @classmethod
    def header(cls, title, emoji="⚜️"):
        return f"\n{emoji} **{title.upper()}** {emoji}\n{cls.SEPARATOR_DOUBLE}\n"

    @classmethod
    def section(cls, title, emoji="📌"):
        return f"\n{emoji} **{title}**\n{cls.SEPARATOR}\n"

    @classmethod
    def command(cls, cmd, desc, usage=""):
        if usage:
            return f"• `/{cmd} {usage}` — {desc}"
        return f"• `/{cmd}` — {desc}"

    @classmethod
    def item(cls, text, emoji="•"):
        return f"{emoji} {text}"

    @classmethod
    def stat(cls, name, value, emoji="📊"):
        return f"{emoji} **{name}:** {value}"

    @classmethod
    def success(cls, text):
        return f"✅ **{text}**"

    @classmethod
    def error(cls, text):
        return f"❌ **{text}**"

    @classmethod
    def warning(cls, text):
        return f"⚠️ **{text}**"

    @classmethod
    def info(cls, text):
        return f"ℹ️ **{text}**"

    @classmethod
    def code(cls, text):
        return f"`{text}`"

f = Formatter()

# ========== КЛАВИАТУРЫ ==========
class Keyboard:
    @staticmethod
    def make(buttons):
        keyboard = []
        for row in buttons:
            kb_row = []
            for text, callback in row:
                kb_row.append(InlineKeyboardButton(text, callback_data=callback))
            keyboard.append(kb_row)
        return InlineKeyboardMarkup(keyboard)

    @classmethod
    def main_menu(cls):
        return cls.make([
            [("👤 ПРОФИЛЬ", "menu_profile"), ("📊 СТАТИСТИКА", "menu_stats")],
            [("👾 БОССЫ", "menu_bosses"), ("🎰 КАЗИНО", "menu_casino")],
            [("🛍 МАГАЗИН", "menu_shop"), ("💎 ПРИВИЛЕГИИ", "menu_donate")],
            [("📚 ПОМОЩЬ", "menu_help")]
        ])

    @classmethod
    def back(cls):
        return cls.make([[("🔙 НАЗАД", "menu_back")]])

kb = Keyboard()

# ========== БАЗА ДАННЫХ ==========
class Database:
    def __init__(self):
        self.conn = sqlite3.connect("spectrum.db", check_same_thread=False)
        self.c = self.conn.cursor()
        self.create_tables()
        self.init_bosses()

    def create_tables(self):
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                username TEXT,
                first_name TEXT,
                coins INTEGER DEFAULT 1000,
                level INTEGER DEFAULT 1,
                exp INTEGER DEFAULT 0,
                energy INTEGER DEFAULT 100,
                health INTEGER DEFAULT 100,
                max_health INTEGER DEFAULT 100,
                damage INTEGER DEFAULT 10,
                armor INTEGER DEFAULT 0,
                role TEXT DEFAULT 'user',
                warns INTEGER DEFAULT 0,
                warns_list TEXT DEFAULT '[]',
                mute_until TEXT,
                banned INTEGER DEFAULT 0,
                vip_until TEXT,
                premium_until TEXT,
                nickname TEXT,
                title TEXT DEFAULT '',
                motto TEXT DEFAULT 'Нет девиза',
                gender TEXT DEFAULT 'не указан',
                boss_kills INTEGER DEFAULT 0,
                rps_wins INTEGER DEFAULT 0,
                rps_losses INTEGER DEFAULT 0,
                rps_draws INTEGER DEFAULT 0,
                casino_wins INTEGER DEFAULT 0,
                casino_losses INTEGER DEFAULT 0,
                daily_streak INTEGER DEFAULT 0,
                last_daily TEXT,
                last_weekly TEXT,
                last_seen TEXT,
                registered TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

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
                is_alive INTEGER DEFAULT 1
            )
        ''')
        self.conn.commit()

    def init_bosses(self):
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

    def get_user(self, telegram_id, first_name="Player"):
        self.c.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        user = self.c.fetchone()
        
        if not user:
            role = 'owner' if telegram_id == Config.OWNER_ID else 'user'
            self.c.execute('''
                INSERT INTO users (telegram_id, first_name, role, last_seen)
                VALUES (?, ?, ?, ?)
            ''', (telegram_id, first_name, role, datetime.datetime.now().isoformat()))
            self.conn.commit()
            return self.get_user(telegram_id, first_name)
        
        col_names = [description[0] for description in self.c.description]
        user_dict = dict(zip(col_names, user))
        
        self.c.execute("UPDATE users SET last_seen = ? WHERE telegram_id = ?", 
                      (datetime.datetime.now().isoformat(), telegram_id))
        self.conn.commit()
        
        return user_dict

    def update_user(self, user_id, **kwargs):
        for key, value in kwargs.items():
            self.c.execute(f"UPDATE users SET {key} = ? WHERE id = ?", (value, user_id))
        self.conn.commit()

    def add_coins(self, user_id, amount):
        self.c.execute("UPDATE users SET coins = coins + ? WHERE id = ?", (amount, user_id))
        self.conn.commit()
        self.c.execute("SELECT coins FROM users WHERE id = ?", (user_id,))
        return self.c.fetchone()[0]

    def add_exp(self, user_id, amount):
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

    def add_energy(self, user_id, amount):
        self.c.execute("UPDATE users SET energy = MIN(100, energy + ?) WHERE id = ?", (amount, user_id))
        self.conn.commit()

    def heal(self, user_id, amount):
        self.c.execute("UPDATE users SET health = MIN(max_health, health + ?) WHERE id = ?", 
                      (amount, user_id))
        self.conn.commit()

    def damage(self, user_id, amount):
        self.c.execute("UPDATE users SET health = MAX(0, health - ?) WHERE id = ?", (amount, user_id))
        self.conn.commit()

    def is_vip(self, user_id):
        self.c.execute("SELECT vip_until FROM users WHERE id = ?", (user_id,))
        row = self.c.fetchone()
        if row and row[0]:
            return datetime.datetime.fromisoformat(row[0]) > datetime.datetime.now()
        return False

    def is_premium(self, user_id):
        self.c.execute("SELECT premium_until FROM users WHERE id = ?", (user_id,))
        row = self.c.fetchone()
        if row and row[0]:
            return datetime.datetime.fromisoformat(row[0]) > datetime.datetime.now()
        return False

    def set_vip(self, user_id, days):
        until = datetime.datetime.now() + datetime.timedelta(days=days)
        self.c.execute("UPDATE users SET vip_until = ?, role = 'vip' WHERE id = ?", 
                      (until.isoformat(), user_id))
        self.conn.commit()
        return until

    def set_premium(self, user_id, days):
        until = datetime.datetime.now() + datetime.timedelta(days=days)
        self.c.execute("UPDATE users SET premium_until = ?, role = 'premium' WHERE id = ?", 
                      (until.isoformat(), user_id))
        self.conn.commit()
        return until

    def get_bosses(self, alive_only=True):
        if alive_only:
            self.c.execute("SELECT * FROM bosses WHERE is_alive = 1 ORDER BY level")
        else:
            self.c.execute("SELECT * FROM bosses ORDER BY level")
        col_names = [description[0] for description in self.c.description]
        return [dict(zip(col_names, row)) for row in self.c.fetchall()]

    def get_boss(self, boss_id):
        self.c.execute("SELECT * FROM bosses WHERE id = ?", (boss_id,))
        row = self.c.fetchone()
        if row:
            col_names = [description[0] for description in self.c.description]
            return dict(zip(col_names, row))
        return None

    def damage_boss(self, boss_id, damage):
        self.c.execute("UPDATE bosses SET health = health - ? WHERE id = ?", (damage, boss_id))
        self.c.execute("SELECT health FROM bosses WHERE id = ?", (boss_id,))
        health = self.c.fetchone()[0]
        if health <= 0:
            self.c.execute("UPDATE bosses SET is_alive = 0 WHERE id = ?", (boss_id,))
            self.conn.commit()
            return True
        self.conn.commit()
        return False

    def respawn_bosses(self):
        self.c.execute("UPDATE bosses SET is_alive = 1, health = max_health")
        self.conn.commit()

    def add_boss_kill(self, user_id):
        self.c.execute("UPDATE users SET boss_kills = boss_kills + 1 WHERE id = ?", (user_id,))
        self.conn.commit()

    def add_daily_streak(self, user_id):
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

    def get_top(self, field, limit=10):
        self.c.execute(f"SELECT first_name, nickname, {field} FROM users ORDER BY {field} DESC LIMIT ?", (limit,))
        return self.c.fetchall()

    def add_warn(self, user_id, admin_id, reason):
        self.c.execute("SELECT warns, warns_list FROM users WHERE id = ?", (user_id,))
        warns, warns_list = self.c.fetchone()
        warns_list = json.loads(warns_list)
        warns_list.append({
            'id': len(warns_list) + 1,
            'admin_id': admin_id,
            'reason': reason,
            'date': datetime.datetime.now().isoformat()
        })
        self.c.execute("UPDATE users SET warns = ?, warns_list = ? WHERE id = ?",
                      (warns + 1, json.dumps(warns_list), user_id))
        self.conn.commit()
        return warns + 1

    def close(self):
        self.conn.close()

db = Database()

# ========== ОСНОВНОЙ КЛАСС БОТА ==========
class SpectrumBot:
    def __init__(self):
        self.db = db
        self.spam = defaultdict(list)
        self.app = Application.builder().token(Config.TELEGRAM_TOKEN).build()
        self.start_time = datetime.datetime.now()
        self.setup_handlers()

    def setup_handlers(self):
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CommandHandler("menu", self.cmd_menu))
        self.app.add_handler(CommandHandler("profile", self.cmd_profile))
        self.app.add_handler(CommandHandler("nick", self.cmd_nick))
        self.app.add_handler(CommandHandler("title", self.cmd_title))
        self.app.add_handler(CommandHandler("motto", self.cmd_motto))
        self.app.add_handler(CommandHandler("gender", self.cmd_gender))
        self.app.add_handler(CommandHandler("stats", self.cmd_stats))
        self.app.add_handler(CommandHandler("top", self.cmd_top))
        self.app.add_handler(CommandHandler("daily", self.cmd_daily))
        self.app.add_handler(CommandHandler("weekly", self.cmd_weekly))
        self.app.add_handler(CommandHandler("bosses", self.cmd_bosses))
        self.app.add_handler(CommandHandler("boss", self.cmd_boss_fight))
        self.app.add_handler(CommandHandler("regen", self.cmd_regen))
        self.app.add_handler(CommandHandler("casino", self.cmd_casino))
        self.app.add_handler(CommandHandler("roulette", self.cmd_roulette))
        self.app.add_handler(CommandHandler("dice", self.cmd_dice))
        self.app.add_handler(CommandHandler("rps", self.cmd_rps))
        self.app.add_handler(CommandHandler("shop", self.cmd_shop))
        self.app.add_handler(CommandHandler("buy", self.cmd_buy))
        self.app.add_handler(CommandHandler("pay", self.cmd_pay))
        self.app.add_handler(CommandHandler("donate", self.cmd_donate))
        self.app.add_handler(CommandHandler("vip", self.cmd_vip))
        self.app.add_handler(CommandHandler("premium", self.cmd_premium))
        self.app.add_handler(CommandHandler("warn", self.cmd_warn))
        self.app.add_handler(CommandHandler("mute", self.cmd_mute))
        self.app.add_handler(CommandHandler("ban", self.cmd_ban))
        self.app.add_handler(CommandHandler("time", self.cmd_time))
        self.app.add_handler(CommandHandler("id", self.cmd_id))
        self.app.add_handler(CommandHandler("ping", self.cmd_ping))
        self.app.add_handler(CallbackQueryHandler(self.button_callback))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    def get_role_emoji(self, role):
        emojis = {'owner': '👑', 'admin': '⚜️', 'premium': '💎', 'vip': '🌟', 'user': '👤'}
        return emojis.get(role, '👤')

    async def check_spam(self, update):
        user_id = update.effective_user.id
        now = time.time()
        self.spam[user_id] = [t for t in self.spam[user_id] if now - t < Config.SPAM_WINDOW]
        self.spam[user_id].append(now)
        if len(self.spam[user_id]) > Config.SPAM_LIMIT:
            await update.message.reply_text(f.error(f"Спам! Мут на {Config.SPAM_MUTE_TIME} минут"))
            return True
        return False

    # ========== КОМАНДЫ ==========

    async def cmd_start(self, update, context):
        user = update.effective_user
        user_data = self.db.get_user(user.id, user.first_name)
        
        text = (f.header("ДОБРО ПОЖАЛОВАТЬ") + "\n\n" +
                f"👋 **Привет, {user.first_name}!**\n" +
                f"Я — **СПЕКТР**, твой игровой помощник.\n\n" +
                f.section("ТВОЙ ПРОФИЛЬ") +
                f.item(f"{self.get_role_emoji(user_data['role'])} Роль: {user_data['role']}") + "\n" +
                f.item(f"💰 Монеты: {user_data['coins']}") + "\n" +
                f.item(f"📊 Уровень: {user_data['level']}") + "\n" +
                f.item(f"⚡ Энергия: {user_data['energy']}/100") + "\n\n" +
                f.section("БЫСТРЫЙ СТАРТ") +
                f.command("profile", "твой профиль") + "\n" +
                f.command("bosses", "битва с боссами") + "\n" +
                f.command("daily", "ежедневный бонус") + "\n" +
                f.command("help", "все команды") + "\n\n" +
                f"👑 **Владелец:** {Config.OWNER_USERNAME}")
        
        await update.message.reply_text(text, reply_markup=kb.main_menu(), parse_mode="Markdown")

    async def cmd_help(self, update, context):
        text = (f.header("СПРАВКА") + "\n\n" +
                f.section("ОСНОВНЫЕ") +
                f.command("start", "начать") + "\n" +
                f.command("menu", "меню") + "\n" +
                f.command("profile", "профиль") + "\n" +
                f.command("stats", "статистика") + "\n\n" +
                f.section("ПРОФИЛЬ") +
                f.command("nick [ник]", "установить ник") + "\n" +
                f.command("title [титул]", "установить титул") + "\n" +
                f.command("motto [девиз]", "установить девиз") + "\n" +
                f.command("gender [м/ж]", "установить пол") + "\n\n" +
                f.section("ИГРЫ") +
                f.command("bosses", "боссы") + "\n" +
                f.command("casino", "казино") + "\n" +
                f.command("rps", "камень-ножницы-бумага") + "\n\n" +
                f.section("ЭКОНОМИКА") +
                f.command("daily", "ежедневный бонус") + "\n" +
                f.command("weekly", "недельный бонус") + "\n" +
                f.command("shop", "магазин") + "\n" +
                f.command("pay @ник сумма", "перевести монеты") + "\n" +
                f.command("donate", "привилегии") + "\n\n" +
                f"👑 **Владелец:** {Config.OWNER_USERNAME}")
        
        await update.message.reply_text(text, reply_markup=kb.back(), parse_mode="Markdown")

    async def cmd_menu(self, update, context):
        await update.message.reply_text(f.header("ГЛАВНОЕ МЕНЮ") + "\nВыбери раздел:", 
                                        reply_markup=kb.main_menu(), parse_mode="Markdown")

    async def cmd_profile(self, update, context):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        display_name = user_data.get("nickname") or user.first_name
        title = user_data.get("title", "")
        motto = user_data.get("motto", "Нет девиза")
        
        vip = "✅ VIP" if self.db.is_vip(user_data["id"]) else "❌ Нет"
        premium = "✅ PREMIUM" if self.db.is_premium(user_data["id"]) else "❌ Нет"
        
        exp_needed = user_data["level"] * 100
        exp_progress = f"`{'█' * int((user_data['exp']/exp_needed)*10)}{'░' * (10 - int((user_data['exp']/exp_needed)*10))}` {user_data['exp']}/{exp_needed}"
        
        text = (f.header("ПРОФИЛЬ") + "\n\n" +
                f"**{display_name}** {title}\n" +
                f"_{motto}_\n\n" +
                f.section("ХАРАКТЕРИСТИКИ") +
                f.stat("Уровень", user_data["level"]) + "\n" +
                f.stat("Опыт", exp_progress) + "\n" +
                f.stat("Монеты", f"{user_data['coins']} 💰") + "\n" +
                f.stat("Энергия", f"{user_data['energy']}/100 ⚡") + "\n\n" +
                f.section("БОЕВЫЕ") +
                f.stat("❤️ Здоровье", f"{user_data['health']}/{user_data['max_health']}") + "\n" +
                f.stat("⚔️ Урон", user_data["damage"]) + "\n" +
                f.stat("🛡 Броня", user_data["armor"]) + "\n" +
                f.stat("👾 Боссов убито", user_data["boss_kills"]) + "\n\n" +
                f.section("СТАТУС") +
                f.item(vip) + "\n" +
                f.item(premium) + "\n" +
                f.item(f"Пол: {user_data['gender']}") + "\n" +
                f.item(f"ID: {f.code(str(user.id))}"))
        
        await update.message.reply_text(text, reply_markup=kb.back(), parse_mode="Markdown")

    async def cmd_nick(self, update, context):
        if not context.args:
            await update.message.reply_text(f.error("Укажи ник: /nick [ник]"))
            return
        nick = " ".join(context.args)
        if len(nick) > Config.MAX_NICK_LENGTH:
            await update.message.reply_text(f.error(f"Максимум {Config.MAX_NICK_LENGTH} символов"))
            return
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data["id"], nickname=nick)
        await update.message.reply_text(f.success(f"Ник установлен: {nick}"))

    async def cmd_title(self, update, context):
        if not context.args:
            await update.message.reply_text(f.error("Укажи титул: /title [титул]"))
            return
        title = " ".join(context.args)
        if len(title) > Config.MAX_TITLE_LENGTH:
            await update.message.reply_text(f.error(f"Максимум {Config.MAX_TITLE_LENGTH} символов"))
            return
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data["id"], title=title)
        await update.message.reply_text(f.success(f"Титул установлен: {title}"))

    async def cmd_motto(self, update, context):
        if not context.args:
            await update.message.reply_text(f.error("Укажи девиз: /motto [девиз]"))
            return
        motto = " ".join(context.args)
        if len(motto) > Config.MAX_MOTTO_LENGTH:
            await update.message.reply_text(f.error(f"Максимум {Config.MAX_MOTTO_LENGTH} символов"))
            return
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data["id"], motto=motto)
        await update.message.reply_text(f.success(f"Девиз установлен: _{motto}_"))

    async def cmd_gender(self, update, context):
        if not context.args or context.args[0].lower() not in ["м", "ж"]:
            await update.message.reply_text(f.error("Укажи /gender м или /gender ж"))
            return
        gender = "мужской" if context.args[0].lower() == "м" else "женский"
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data["id"], gender=gender)
        await update.message.reply_text(f.success(f"Пол установлен: {gender}"))

    async def cmd_stats(self, update, context):
        user_data = self.db.get_user(update.effective_user.id)
        text = (f.header("СТАТИСТИКА") + "\n\n" +
                f.stat("Сообщений", user_data.get("messages_count", 0)) + "\n" +
                f.stat("РПС побед", user_data["rps_wins"]) + "\n" +
                f.stat("РПС поражений", user_data["rps_losses"]) + "\n" +
                f.stat("Казино побед", user_data["casino_wins"]) + "\n" +
                f.stat("Казино поражений", user_data["casino_losses"]))
        await update.message.reply_text(text, reply_markup=kb.back(), parse_mode="Markdown")

    async def cmd_top(self, update, context):
        top_coins = self.db.get_top("coins", 10)
        top_level = self.db.get_top("level", 10)
        
        text = f.header("ТОП ИГРОКОВ") + "\n\n"
        text += f.section("ПО МОНЕТАМ") + "\n"
        for i, row in enumerate(top_coins, 1):
            name = row[1] or row[0]
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} **{name}** — {row[2]} 💰\n"
        
        text += f"\n" + f.section("ПО УРОВНЮ") + "\n"
        for i, row in enumerate(top_level, 1):
            name = row[1] or row[0]
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} **{name}** — {row[2]} ур.\n"
        
        await update.message.reply_text(text, reply_markup=kb.back(), parse_mode="Markdown")

    async def cmd_daily(self, update, context):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data.get("last_daily"):
            last = datetime.datetime.fromisoformat(user_data["last_daily"])
            if (datetime.datetime.now() - last).seconds < Config.DAILY_COOLDOWN:
                remain = Config.DAILY_COOLDOWN - (datetime.datetime.now() - last).seconds
                await update.message.reply_text(f.warning(f"Бонус через {remain//3600}ч {(remain%3600)//60}м"))
                return
        
        streak = self.db.add_daily_streak(user_data["id"])
        coins = random.randint(100, 300)
        exp = random.randint(20, 60)
        
        if self.db.is_vip(user_data["id"]):
            coins = int(coins * 1.5)
            exp = int(exp * 1.5)
        if self.db.is_premium(user_data["id"]):
            coins = int(coins * 2)
            exp = int(exp * 2)
        
        self.db.add_coins(user_data["id"], coins)
        self.db.add_exp(user_data["id"], exp)
        self.db.add_energy(user_data["id"], 20)
        
        text = (f.header("ЕЖЕДНЕВНЫЙ БОНУС") + "\n\n" +
                f.item(f"🔥 Стрик: {streak} дней") + "\n" +
                f.item(f"💰 Монеты: +{coins}") + "\n" +
                f.item(f"✨ Опыт: +{exp}") + "\n" +
                f.item(f"⚡ Энергия: +20") + "\n\n" +
                f.info("Заходи завтра!"))
        
        await update.message.reply_text(text, parse_mode="Markdown")

    async def cmd_weekly(self, update, context):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data.get("last_weekly"):
            last = datetime.datetime.fromisoformat(user_data["last_weekly"])
            if (datetime.datetime.now() - last).seconds < Config.WEEKLY_COOLDOWN:
                await update.message.reply_text(f.warning("Бонус раз в неделю!"))
                return
        
        coins = random.randint(1000, 3000)
        exp = random.randint(200, 500)
        
        if self.db.is_vip(user_data["id"]):
            coins = int(coins * 1.5)
            exp = int(exp * 1.5)
        if self.db.is_premium(user_data["id"]):
            coins = int(coins * 2)
            exp = int(exp * 2)
        
        self.db.add_coins(user_data["id"], coins)
        self.db.add_exp(user_data["id"], exp)
        self.db.update_user(user_data["id"], last_weekly=datetime.datetime.now().isoformat())
        
        text = (f.header("НЕДЕЛЬНЫЙ БОНУС") + "\n\n" +
                f.item(f"💰 Монеты: +{coins}") + "\n" +
                f.item(f"✨ Опыт: +{exp}") + "\n\n" +
                f.info("Через неделю снова!"))
        
        await update.message.reply_text(text, parse_mode="Markdown")

    async def cmd_bosses(self, update, context):
        user_data = self.db.get_user(update.effective_user.id)
        bosses = self.db.get_bosses()
        
        if not bosses:
            self.db.respawn_bosses()
            bosses = self.db.get_bosses()
        
        text = f.header("АРЕНА БОССОВ") + "\n\n"
        
        if bosses:
            boss = bosses[0]
            bar = f"{'█' * int((boss['health']/boss['max_health'])*20)}{'░' * (20 - int((boss['health']/boss['max_health'])*20))}"
            text += (f"**ТЕКУЩИЙ БОСС**\n" +
                    f"└ {boss['name']} (ур.{boss['level']})\n" +
                    f"└ ❤️ `{bar}` {boss['health']}/{boss['max_health']}\n" +
                    f"└ ⚔️ Урон: {boss['damage']}\n" +
                    f"└ 💰 Награда: {boss['reward_coins']}\n\n")
        
        text += (f.section("ТВОИ ПОКАЗАТЕЛИ") +
                f.stat("❤️ Здоровье", f"{user_data['health']}/{user_data['max_health']}") + "\n" +
                f.stat("⚡ Энергия", f"{user_data['energy']}/100") + "\n" +
                f.stat("⚔️ Урон", user_data["damage"]) + "\n" +
                f.stat("👾 Убито", user_data["boss_kills"]) + "\n\n" +
                f.section("КОМАНДЫ") +
                f.command("boss [ID]", "атаковать босса") + "\n" +
                f.command("regen", "восстановить ❤️ и ⚡"))
        
        await update.message.reply_text(text, reply_markup=kb.back(), parse_mode="Markdown")

    async def cmd_boss_fight(self, update, context):
        if not context.args:
            await update.message.reply_text(f.error("Укажи ID босса: /boss 1"))
            return
        
        try:
            boss_id = int(context.args[0])
        except:
            await update.message.reply_text(f.error("Неверный ID"))
            return
        
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        boss = self.db.get_boss(boss_id)
        
        if not boss or not boss["is_alive"]:
            await update.message.reply_text(f.error("Босс не найден"))
            return
        
        if user_data["energy"] < 10:
            await update.message.reply_text(f.error("Мало энергии! /regen"))
            return
        
        self.db.add_energy(user_data["id"], -10)
        
        damage_bonus = 1.0
        if self.db.is_vip(user_data["id"]): damage_bonus += 0.2
        if self.db.is_premium(user_data["id"]): damage_bonus += 0.3
        
        player_damage = int(user_data["damage"] * damage_bonus) + random.randint(-5, 5)
        boss_damage = boss["damage"] + random.randint(-5, 5)
        player_taken = max(1, boss_damage - user_data["armor"] // 2)
        
        killed = self.db.damage_boss(boss_id, player_damage)
        self.db.damage(user_data["id"], player_taken)
        
        text = f.header("БИТВА") + "\n\n"
        text += f.item(f"Твой урон: {player_damage}") + "\n"
        text += f.item(f"Урон босса: {player_taken}") + "\n\n"
        
        if killed:
            reward = boss["reward_coins"] * (1 + user_data["level"] // 10)
            if self.db.is_vip(user_data["id"]): reward = int(reward * 1.5)
            if self.db.is_premium(user_data["id"]): reward = int(reward * 2)
            
            self.db.add_coins(user_data["id"], reward)
            self.db.add_boss_kill(user_data["id"])
            self.db.add_exp(user_data["id"], boss["reward_exp"])
            
            text += f.success("ПОБЕДА!") + "\n"
            text += f.item(f"💰 +{reward} монет") + "\n"
        else:
            text += f.warning("Босс ещё жив!") + "\n"
        
        if user_data["health"] <= player_taken:
            self.db.heal(user_data["id"], 50)
            text += f"\n" + f.info("Воскрешён с 50❤️")
        
        await update.message.reply_text(text, parse_mode="Markdown")

    async def cmd_regen(self, update, context):
        user_data = self.db.get_user(update.effective_user.id)
        cost = 20
        
        if user_data["coins"] < cost:
            await update.message.reply_text(f.error(f"Нужно {cost} 💰"))
            return
        
        self.db.add_coins(user_data["id"], -cost)
        self.db.heal(user_data["id"], 50)
        self.db.add_energy(user_data["id"], 20)
        
        await update.message.reply_text(f.success("Регенерация! ❤️+50 ⚡+20"), parse_mode="Markdown")

    async def cmd_casino(self, update, context):
        text = (f.header("КАЗИНО") + "\n\n" +
                f.command("roulette [ставка] [цвет]", "рулетка") + "\n" +
                f.command("dice [ставка]", "кости") + "\n" +
                f.command("rps", "камень-ножницы-бумага"))
        await update.message.reply_text(text, reply_markup=kb.back(), parse_mode="Markdown")

    async def cmd_roulette(self, update, context):
        user_data = self.db.get_user(update.effective_user.id)
        
        bet = 10
        choice = "red"
        if context.args:
            try:
                bet = int(context.args[0])
                if len(context.args) > 1:
                    choice = context.args[1]
            except:
                pass
        
        if bet > user_data["coins"]:
            await update.message.reply_text(f.error("Недостаточно монет"))
            return
        
        num = random.randint(0, 36)
        red = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]
        color = "red" if num in red else "black" if num != 0 else "green"
        
        win = (choice == str(num)) or (choice == color)
        
        if win:
            multi = 36 if choice == str(num) else 2
            win_amount = bet * multi
            self.db.add_coins(user_data["id"], win_amount)
            res = f.success(f"ВЫИГРЫШ! +{win_amount} 💰")
        else:
            self.db.add_coins(user_data["id"], -bet)
            res = f.error(f"ПРОИГРЫШ! -{bet} 💰")
        
        text = (f.header("РУЛЕТКА") + "\n\n" +
                f.item(f"Ставка: {bet} 💰") + "\n" +
                f.item(f"Выпало: {num} {color}") + "\n\n" +
                res)
        
        await update.message.reply_text(text, parse_mode="Markdown")

    async def cmd_dice(self, update, context):
        user_data = self.db.get_user(update.effective_user.id)
        
        bet = 10
        if context.args:
            try:
                bet = int(context.args[0])
            except:
                pass
        
        if bet > user_data["coins"]:
            await update.message.reply_text(f.error("Недостаточно монет"))
            return
        
        d1 = random.randint(1, 6)
        d2 = random.randint(1, 6)
        total = d1 + d2
        
        if total in [7, 11]:
            win = bet * 2
            self.db.add_coins(user_data["id"], win)
            res = f.success(f"ВЫИГРЫШ! +{win} 💰")
        elif total in [2, 3, 12]:
            win = 0
            self.db.add_coins(user_data["id"], -bet)
            res = f.error(f"ПРОИГРЫШ! -{bet} 💰")
        else:
            win = bet
            res = f.info(f"НИЧЬЯ! +{bet} 💰")
        
        text = (f.header("КОСТИ") + "\n\n" +
                f.item(f"Ставка: {bet} 💰") + "\n" +
                f.item(f"Кости: {d1} + {d2} = {total}") + "\n\n" +
                res)
        
        await update.message.reply_text(text, parse_mode="Markdown")

    async def cmd_rps(self, update, context):
        await update.message.reply_text(
            f.header("КАМЕНЬ-НОЖНИЦЫ-БУМАГА") + "\nВыбери:",
            reply_markup=kb.back(),
            parse_mode="Markdown"
        )

    async def cmd_shop(self, update, context):
        text = (f.header("МАГАЗИН") + "\n\n" +
                f.section("ЗЕЛЬЯ") +
                f.command("buy зелье здоровья", "50 💰 (❤️+30)") + "\n" +
                f.command("buy большое зелье", "100 💰 (❤️+70)") + "\n\n" +
                f.section("ОРУЖИЕ") +
                f.command("buy меч", "200 💰 (⚔️+10)") + "\n" +
                f.command("buy легендарный меч", "500 💰 (⚔️+30)") + "\n\n" +
                f.section("БРОНЯ") +
                f.command("buy щит", "150 💰 (🛡+5)") + "\n" +
                f.command("buy доспехи", "400 💰 (🛡+15)") + "\n\n" +
                f.section("ЭНЕРГИЯ") +
                f.command("buy энергетик", "30 💰 (⚡+20)") + "\n" +
                f.command("buy батарейка", "80 💰 (⚡+50)"))
        
        await update.message.reply_text(text, reply_markup=kb.back(), parse_mode="Markdown")

    async def cmd_buy(self, update, context):
        if not context.args:
            await update.message.reply_text(f.error("Что купить?"))
            return
        
        item = " ".join(context.args).lower()
        user_data = self.db.get_user(update.effective_user.id)
        
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
            await update.message.reply_text(f.error("Нет такого товара"))
            return
        
        data = items[item]
        if user_data["coins"] < data["price"]:
            await update.message.reply_text(f.error(f"Нужно {data['price']} 💰"))
            return
        
        self.db.add_coins(user_data["id"], -data["price"])
        
        if "heal" in data:
            self.db.heal(user_data["id"], data["heal"])
            await update.message.reply_text(f.success(f"❤️ +{data['heal']}"))
        elif "damage" in data:
            new = user_data["damage"] + data["damage"]
            self.db.update_user(user_data["id"], damage=new)
            await update.message.reply_text(f.success(f"⚔️ +{data['damage']}"))
        elif "armor" in data:
            new = user_data["armor"] + data["armor"]
            self.db.update_user(user_data["id"], armor=new)
            await update.message.reply_text(f.success(f"🛡 +{data['armor']}"))
        elif "energy" in data:
            self.db.add_energy(user_data["id"], data["energy"])
            await update.message.reply_text(f.success(f"⚡ +{data['energy']}"))

    async def cmd_pay(self, update, context):
        if len(context.args) < 2:
            await update.message.reply_text(f.error("Использование: /pay @ник сумма"))
            return
        
        username = context.args[0]
        try:
            amount = int(context.args[1])
        except:
            await update.message.reply_text(f.error("Сумма должна быть числом"))
            return
        
        if amount <= 0:
            await update.message.reply_text(f.error("Сумма > 0"))
            return
        
        user_data = self.db.get_user(update.effective_user.id)
        
        if user_data["coins"] < amount:
            await update.message.reply_text(f.error(f"Нужно {amount} 💰"))
            return
        
        target_name = username.replace("@", "")
        self.db.c.execute("SELECT id FROM users WHERE username = ?", (target_name,))
        row = self.db.c.fetchone()
        
        if not row:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        target_id = row[0]
        
        self.db.add_coins(user_data["id"], -amount)
        self.db.add_coins(target_id, amount)
        
        await update.message.reply_text(f.success(f"Переведено {amount} 💰"), parse_mode="Markdown")

    async def cmd_donate(self, update, context):
        text = (f.header("ПРИВИЛЕГИИ") + "\n\n" +
                f.section("VIP СТАТУС") +
                f"Цена: {Config.VIP_PRICE} 💰 / {Config.VIP_DAYS} дней\n" +
                f.item("⚔️ Урон +20%") + "\n" +
                f.item("💰 Награда +50%") + "\n" +
                f.item("🎁 Бонус +50%") + "\n\n" +
                f.section("PREMIUM СТАТУС") +
                f"Цена: {Config.PREMIUM_PRICE} 💰 / {Config.PREMIUM_DAYS} дней\n" +
                f.item("⚔️ Урон +50%") + "\n" +
                f.item("💰 Награда +100%") + "\n" +
                f.item("🎁 Бонус +100%") + "\n\n" +
                f.command("vip", "купить VIP") + "\n" +
                f.command("premium", "купить PREMIUM"))
        
        await update.message.reply_text(text, reply_markup=kb.back(), parse_mode="Markdown")

    async def cmd_vip(self, update, context):
        user_data = self.db.get_user(update.effective_user.id)
        
        if user_data["coins"] < Config.VIP_PRICE:
            await update.message.reply_text(f.error(f"Нужно {Config.VIP_PRICE} 💰"))
            return
        
        if self.db.is_vip(user_data["id"]):
            await update.message.reply_text(f.error("VIP уже активен"))
            return
        
        self.db.add_coins(user_data["id"], -Config.VIP_PRICE)
        until = self.db.set_vip(user_data["id"], Config.VIP_DAYS)
        date_str = until.strftime("%d.%m.%Y")
        
        await update.message.reply_text(
            f.success("VIP АКТИВИРОВАН") + "\n\n" +
            f.item("Срок: до " + date_str),
            parse_mode="Markdown"
        )

    async def cmd_premium(self, update, context):
        user_data = self.db.get_user(update.effective_user.id)
        
        if user_data["coins"] < Config.PREMIUM_PRICE:
            await update.message.reply_text(f.error(f"Нужно {Config.PREMIUM_PRICE} 💰"))
            return
        
        if self.db.is_premium(user_data["id"]):
            await update.message.reply_text(f.error("PREMIUM уже активен"))
            return
        
        self.db.add_coins(user_data["id"], -Config.PREMIUM_PRICE)
        until = self.db.set_premium(user_data["id"], Config.PREMIUM_DAYS)
        date_str = until.strftime("%d.%m.%Y")
        
        await update.message.reply_text(
            f.success("PREMIUM АКТИВИРОВАН") + "\n\n" +
            f.item("Срок: до " + date_str),
            parse_mode="Markdown"
        )

    async def cmd_warn(self, update, context):
        if update.effective_user.id != Config.OWNER_ID:
            await update.message.reply_text(f.error("Нет прав"))
            return
        
        if len(context.args) < 1:
            await update.message.reply_text(f.error("/warn @ник [причина]"))
            return
        
        username = context.args[0].replace("@", "")
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else "Нарушение"
        
        self.db.c.execute("SELECT id FROM users WHERE username = ?", (username,))
        row = self.db.c.fetchone()
        
        if not row:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        warns = self.db.add_warn(row[0], update.effective_user.id, reason)
        await update.message.reply_text(f.success(f"Предупреждение {warns}/3"), parse_mode="Markdown")

    async def cmd_mute(self, update, context):
        if update.effective_user.id != Config.OWNER_ID:
            await update.message.reply_text(f.error("Нет прав"))
            return
        
        if len(context.args) < 2:
            await update.message.reply_text(f.error("/mute @ник минут [причина]"))
            return
        
        username = context.args[0].replace("@", "")
        try:
            minutes = int(context.args[1])
        except:
            await update.message.reply_text(f.error("Время должно быть числом"))
            return
        
        self.db.c.execute("SELECT id FROM users WHERE username = ?", (username,))
        row = self.db.c.fetchone()
        
        if not row:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        until = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
        self.db.c.execute("UPDATE users SET mute_until = ? WHERE id = ?", 
                         (until.isoformat(), row[0]))
        self.db.conn.commit()
        
        await update.message.reply_text(f.success(f"Мут {minutes} минут"), parse_mode="Markdown")

    async def cmd_ban(self, update, context):
        if update.effective_user.id != Config.OWNER_ID:
            await update.message.reply_text(f.error("Нет прав"))
            return
        
        if len(context.args) < 1:
            await update.message.reply_text(f.error("/ban @ник [причина]"))
            return
        
        username = context.args[0].replace("@", "")
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else "Нарушение"
        
        self.db.c.execute("SELECT id FROM users WHERE username = ?", (username,))
        row = self.db.c.fetchone()
        
        if not row:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        self.db.c.execute("UPDATE users SET banned = 1 WHERE id = ?", (row[0],))
        self.db.conn.commit()
        
        await update.message.reply_text(f.success(f"Пользователь забанен"), parse_mode="Markdown")

    async def cmd_time(self, update, context):
        now = datetime.datetime.now()
        date_str = now.strftime("%d.%m.%Y")
        time_str = now.strftime("%H:%M:%S")
        
        text = (f.header("ТЕКУЩЕЕ ВРЕМЯ") + "\n\n" +
                f.item("Дата: " + date_str) + "\n" +
                f.item("Время: " + time_str))
        
        await update.message.reply_text(text, parse_mode="Markdown")

    async def cmd_id(self, update, context):
        user = update.effective_user
        await update.message.reply_text(f"🆔 **ID:** `{user.id}`", parse_mode="Markdown")

    async def cmd_ping(self, update, context):
        start = time.time()
        msg = await update.message.reply_text("🏓 Pong...")
        end = time.time()
        ping = int((end - start) * 1000)
        await msg.edit_text(f"🏓 **Понг!**\n⏱ `{ping}ms`", parse_mode="Markdown")

    async def button_callback(self, update, context):
        query = update.callback_query
        await query.answer()
        data = query.data
        
        if data == "menu_back":
            await query.edit_message_text(
                f.header("ГЛАВНОЕ МЕНЮ") + "\nВыбери раздел:",
                reply_markup=kb.main_menu(),
                parse_mode="Markdown"
            )
        elif data == "menu_profile":
            await self.cmd_profile(update, context)
        elif data == "menu_stats":
            await self.cmd_stats(update, context)
        elif data == "menu_bosses":
            await self.cmd_bosses(update, context)
        elif data == "menu_casino":
            await self.cmd_casino(update, context)
        elif data == "menu_shop":
            await self.cmd_shop(update, context)
        elif data == "menu_donate":
            await self.cmd_donate(update, context)
        elif data == "menu_help":
            await self.cmd_help(update, context)

    async def handle_message(self, update, context):
        user = update.effective_user
        text = update.message.text
        
        if text.startswith("/"):
            return
        
        if await self.check_spam(update):
            return
        
        user_data = self.db.get_user(user.id, user.first_name)
        
        responses = [
            "Используй /help для списка команд.",
            "Я слушаю. Что дальше?",
            "Напиши /menu для навигации.",
            "Чем могу помочь?"
        ]
        
        await update.message.reply_text(random.choice(responses))

    async def run(self):
        try:
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling(drop_pending_updates=True)
            logger.info("✅ Бот СПЕКТР запущен")
            while True:
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await asyncio.sleep(5)
            await self.run()

    async def close(self):
        self.db.close()
        cleanup_lock()

async def main():
    print("=" * 50)
    print("🚀 ЗАПУСК БОТА СПЕКТР")
    print("=" * 50)
    
    bot = SpectrumBot()
    
    try:
        await bot.run()
    except KeyboardInterrupt:
        logger.info("Остановка...")
        await bot.close()
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await bot.close()

if __name__ == "__main__":
    asyncio.run(main())
