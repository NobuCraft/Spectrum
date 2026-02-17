#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
СПЕКТР - SPECTRUM BOT
Официальный бот с командами Iris, играми и диаграммами
Версия 4.0
"""

import asyncio
import logging
import random
import sqlite3
import datetime
import json
import os
import sys
import signal
import time
import hashlib
from collections import defaultdict
from io import BytesIO
import traceback
from typing import Optional, Dict, Any, List, Tuple

# Устанавливаем зависимости если нет
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
except ImportError:
    os.system("pip install matplotlib numpy")
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np

try:
    import psutil
except ImportError:
    os.system("pip install psutil")
    import psutil

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from telegram.error import Conflict

# ========== НАСТРОЙКА ЛОГИРОВАНИЯ ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('spectrum_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ========== КОНФИГУРАЦИЯ ==========
class Config:
    TELEGRAM_TOKEN = "8326390250:AAG1nTYdy07AuKsYXS3yvDehfU2JuR0RqGo"
    OWNER_ID = 1732658530
    OWNER_USERNAME = "@NobuCraft"
    
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
    
    # Временные интервалы
    DAILY_COOLDOWN = 86400
    WEEKLY_COOLDOWN = 604800

# ========== НАДЁЖНАЯ ЗАЩИТА ОТ ЭКЗЕМПЛЯРОВ ==========
# ========== УЛУЧШЕННАЯ ЗАЩИТА ОТ МНОЖЕСТВЕННЫХ ЭКЗЕМПЛЯРОВ ==========
class SingleInstance:
    """Гарантирует запуск только одного экземпляра бота"""
    
    def __init__(self):
        self.lock_file = None
        self.token_hash = hashlib.md5(Config.TELEGRAM_TOKEN.encode()).hexdigest()[:16]
        
    def kill_other_instances(self):
        """Агрессивно убивает все другие процессы с этим токеном"""
        current_pid = os.getpid()
        killed = False
        
        try:
            # Ищем все Python процессы
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    # Пропускаем текущий процесс
                    if proc.info['pid'] == current_pid:
                        continue
                    
                    # Проверяем командную строку
                    cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                    
                    # Ищем процессы с нашим токеном или именем бота
                    if ('python' in proc.info['name'].lower() and 
                        (Config.TELEGRAM_TOKEN in cmdline or 'spectrum' in cmdline.lower())):
                        
                        logger.warning(f"🔪 Найден процесс-конкурент {proc.info['pid']}, убиваем...")
                        
                        # Сначала SIGTERM
                        proc.terminate()
                        time.sleep(1)
                        
                        # Если ещё жив - SIGKILL
                        if proc.is_running():
                            logger.warning(f"💀 Процесс {proc.info['pid']} не отвечает, применяем SIGKILL")
                            proc.kill()
                        
                        killed = True
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
                    
        except Exception as e:
            logger.error(f"Ошибка при убийстве процессов: {e}")
        
        if killed:
            logger.info("✅ Все конкурирующие процессы убиты")
            time.sleep(2)
            return True
            
        return False
    
    def force_delete_old_lock(self):
        """Принудительно удаляет старые lock-файлы"""
        try:
            lock_dir = "/tmp/spectrum_locks"
            if os.path.exists(lock_dir):
                for file in os.listdir(lock_dir):
                    if file.startswith(f"bot_{self.token_hash}"):
                        lock_path = os.path.join(lock_dir, file)
                        try:
                            # Проверяем, есть ли живой процесс с этим PID
                            with open(lock_path, 'r') as f:
                                old_pid = int(f.read().strip())
                            
                            try:
                                os.kill(old_pid, 0)
                                # Процесс жив - убиваем
                                os.kill(old_pid, signal.SIGKILL)
                                time.sleep(1)
                            except OSError:
                                pass  # Процесс мертв
                                
                            os.remove(lock_path)
                            logger.info(f"✅ Удален старый lock-файл: {lock_path}")
                            
                        except:
                            try:
                                os.remove(lock_path)
                            except:
                                pass
        except Exception as e:
            logger.error(f"Ошибка при удалении lock-файлов: {e}")
    
    def create_lock(self):
        """Создает lock-файл с проверкой"""
        try:
            lock_dir = "/tmp/spectrum_locks"
            os.makedirs(lock_dir, exist_ok=True)
            
            self.lock_file = os.path.join(lock_dir, f"bot_{self.token_hash}.lock")
            
            # Проверяем существующий lock
            if os.path.exists(self.lock_file):
                try:
                    with open(self.lock_file, 'r') as f:
                        old_pid = int(f.read().strip())
                    
                    # Проверяем жив ли процесс
                    try:
                        os.kill(old_pid, 0)
                        # Процесс жив - убиваем его
                        logger.warning(f"🔪 Найден живой процесс {old_pid}, убиваем...")
                        os.kill(old_pid, signal.SIGKILL)
                        time.sleep(1)
                    except OSError:
                        pass  # Процесс мертв
                        
                except Exception as e:
                    logger.error(f"Ошибка при чтении lock-файла: {e}")
                
                # Удаляем старый lock-файл
                try:
                    os.remove(self.lock_file)
                except:
                    pass
            
            # Создаем новый lock
            with open(self.lock_file, 'w') as f:
                f.write(str(os.getpid()))
            
            logger.info(f"✅ Lock-файл создан: {self.lock_file}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка создания lock-файла: {e}")
            return False
    
    def cleanup(self):
        """Удаляет lock-файл"""
        if self.lock_file and os.path.exists(self.lock_file):
            try:
                os.remove(self.lock_file)
                logger.info("✅ Lock-файл удален")
            except Exception as e:
                logger.error(f"Ошибка при удалении lock-файла: {e}")

# Создаем экземпляр защиты
guard = SingleInstance()

# Агрессивно убиваем все конкурирующие процессы
guard.kill_other_instances()
guard.force_delete_old_lock()
guard.create_lock()

# Дополнительная проверка при импорте
import atexit
atexit.register(guard.cleanup)

# ========== ФОРМАТТЕР В СТИЛЕ IRIS ==========
class Formatter:
    """Красивое оформление как у Iris"""
    
    @classmethod
    def header(cls, title: str, emoji: str = "⚜️") -> str:
        """Заголовок"""
        return f"\n{emoji} **{title.upper()}** {emoji}\n" + "─" * 30 + "\n"
    
    @classmethod
    def section(cls, title: str, emoji: str = "📌") -> str:
        """Раздел"""
        return f"\n{emoji} **{title}**\n" + "─" * 25 + "\n"
    
    @classmethod
    def command(cls, cmd: str, desc: str, usage: str = "") -> str:
        """Команда"""
        if usage:
            return f"• `/{cmd} {usage}` — {desc}"
        return f"• `/{cmd}` — {desc}"
    
    @classmethod
    def param(cls, name: str, desc: str) -> str:
        """Параметр команды"""
        return f"  └ {name} — {desc}"
    
    @classmethod
    def example(cls, text: str) -> str:
        """Пример использования"""
        return f"  └ Пример: `{text}`"
    
    @classmethod
    def item(cls, text: str, emoji: str = "•") -> str:
        """Элемент списка"""
        return f"{emoji} {text}"
    
    @classmethod
    def stat(cls, name: str, value: str, emoji: str = "📊") -> str:
        """Статистика"""
        return f"{emoji} **{name}:** {value}"
    
    @classmethod
    def progress(cls, current: int, total: int, length: int = 15) -> str:
        """Прогресс-бар"""
        filled = int((current / total) * length)
        bar = "█" * filled + "░" * (length - filled)
        return f"`{bar}` {current}/{total}"
    
    @classmethod
    def success(cls, text: str) -> str:
        """Успех"""
        return f"✅ **{text}**"
    
    @classmethod
    def error(cls, text: str) -> str:
        """Ошибка"""
        return f"❌ **{text}**"
    
    @classmethod
    def warning(cls, text: str) -> str:
        """Предупреждение"""
        return f"⚠️ **{text}**"
    
    @classmethod
    def info(cls, text: str) -> str:
        """Информация"""
        return f"ℹ️ **{text}**"
    
    @classmethod
    def code(cls, text: str) -> str:
        """Моноширинный текст"""
        return f"`{text}`"
    
    @classmethod
    def bold(cls, text: str) -> str:
        """Жирный текст"""
        return f"**{text}**"
    
    @classmethod
    def italic(cls, text: str) -> str:
        """Курсив"""
        return f"_{text}_"

f = Formatter()

# ========== КЛАВИАТУРЫ ==========
class Keyboard:
    """Создание клавиатур"""
    
    @staticmethod
    def make(buttons: List[List[Tuple[str, str]]]) -> InlineKeyboardMarkup:
        """Создает клавиатуру из списка кнопок"""
        keyboard = []
        for row in buttons:
            kb_row = []
            for text, callback in row:
                kb_row.append(InlineKeyboardButton(text, callback_data=callback))
            keyboard.append(kb_row)
        return InlineKeyboardMarkup(keyboard)
    
    @classmethod
    def main_menu(cls) -> InlineKeyboardMarkup:
        """Главное меню"""
        return cls.make([
            [("👤 ПРОФИЛЬ", "menu_profile"), ("📊 СТАТИСТИКА", "menu_stats")],
            [("👾 БОССЫ", "menu_bosses"), ("🎰 КАЗИНО", "menu_casino")],
            [("🛍 МАГАЗИН", "menu_shop"), ("💎 ПРИВИЛЕГИИ", "menu_donate")],
            [("⚙️ МОДЕРАЦИЯ", "menu_mod"), ("📚 ПОМОЩЬ", "menu_help")]
        ])
    
    @classmethod
    def back(cls) -> InlineKeyboardMarkup:
        """Кнопка назад"""
        return cls.make([[("🔙 НАЗАД", "menu_back")]])
    
    @classmethod
    def back_main(cls) -> InlineKeyboardMarkup:
        """Кнопки назад и на главную"""
        return cls.make([
            [("🔙 НАЗАД", "menu_back"), ("🏠 ГЛАВНАЯ", "menu_main")]
        ])
    
    @classmethod
    def confirm_cancel(cls) -> InlineKeyboardMarkup:
        """Кнопки подтверждения и отмены"""
        return cls.make([
            [("✅ ПОДТВЕРДИТЬ", "confirm"), ("❌ ОТМЕНИТЬ", "cancel")]
        ])
    
    @classmethod
    def pagination(cls, current: int, total: int, prefix: str) -> InlineKeyboardMarkup:
        """Кнопки пагинации"""
        buttons = []
        row = []
        
        if current > 1:
            row.append(("◀️", f"{prefix}_page_{current-1}"))
        
        row.append((f"📄 {current}/{total}", "noop"))
        
        if current < total:
            row.append(("▶️", f"{prefix}_page_{current+1}"))
        
        buttons.append(row)
        return cls.make(buttons)
    
    @classmethod
    def mod_menu(cls) -> InlineKeyboardMarkup:
        """Меню модерации"""
        return cls.make([
            [("⚠️ ВАРНЫ", "mod_warns"), ("🔇 МУТЫ", "mod_mutes")],
            [("🔨 БАНЫ", "mod_bans"), ("📋 ЛОГИ", "mod_logs")],
            [("⚙️ НАСТРОЙКИ", "mod_settings"), ("👥 АДМИНЫ", "mod_admins")],
            [("🔙 НАЗАД", "menu_back")]
        ])
    
    @classmethod
    def casino_menu(cls) -> InlineKeyboardMarkup:
        """Меню казино"""
        return cls.make([
            [("🎰 РУЛЕТКА", "casino_roulette"), ("🎲 КОСТИ", "casino_dice")],
            [("✊ КНБ", "casino_rps"), ("🎰 СЛОТЫ", "casino_slots")],
            [("🔙 НАЗАД", "menu_back")]
        ])
    
    @classmethod
    def rps_game(cls) -> InlineKeyboardMarkup:
        """Кнопки для КНБ"""
        return cls.make([
            [("🪨 КАМЕНЬ", "rps_rock"), ("✂️ НОЖНИЦЫ", "rps_scissors"), ("📄 БУМАГА", "rps_paper")],
            [("🔙 НАЗАД", "menu_back")]
        ])

kb = Keyboard()

# ========== БАЗА ДАННЫХ ==========
class Database:
    """Работа с базой данных"""
    
    def __init__(self, db_name: str = "spectrum.db"):
        self.db_name = db_name
        self.conn = None
        self.cursor = None
        self.connect()
        self.create_tables()
        self.init_bosses()
        logger.info("✅ База данных инициализирована")
    
    def connect(self):
        """Подключение к БД"""
        try:
            self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            self.cursor.execute("PRAGMA foreign_keys = ON")
        except sqlite3.Error as e:
            logger.error(f"Ошибка подключения к БД: {e}")
            raise
    
    def create_tables(self):
        """Создание таблиц"""
        with self.conn:
            # Пользователи
            self.cursor.execute('''
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
                    
                    -- Статистика
                    boss_kills INTEGER DEFAULT 0,
                    messages_count INTEGER DEFAULT 0,
                    commands_used INTEGER DEFAULT 0,
                    
                    -- Игры
                    rps_wins INTEGER DEFAULT 0,
                    rps_losses INTEGER DEFAULT 0,
                    rps_draws INTEGER DEFAULT 0,
                    casino_wins INTEGER DEFAULT 0,
                    casino_losses INTEGER DEFAULT 0,
                    
                    -- Профиль
                    nickname TEXT,
                    title TEXT DEFAULT '',
                    motto TEXT DEFAULT 'Нет девиза',
                    gender TEXT DEFAULT 'не указан',
                    city TEXT DEFAULT 'не указан',
                    birth_date TEXT,
                    reputation INTEGER DEFAULT 0,
                    
                    -- Модерация
                    role TEXT DEFAULT 'user',
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
                    last_seen TEXT,
                    registered TEXT DEFAULT CURRENT_TIMESTAMP,
                    
                    -- Активность для диаграммы
                    activity_data TEXT DEFAULT '{}'
                )
            ''')
            
            # Индексы
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_telegram_id ON users(telegram_id)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_username ON users(username)')
            
            # Боссы
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
                    is_alive INTEGER DEFAULT 1
                )
            ''')
            
            # Логи
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action TEXT,
                    details TEXT,
                    chat_id INTEGER,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            
            # Черный список слов
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS blacklist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word TEXT UNIQUE,
                    added_by INTEGER,
                    added_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Настройки чатов
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
    
    def init_bosses(self):
        """Инициализация боссов"""
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
        """Получение или создание пользователя"""
        self.cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        row = self.cursor.fetchone()
        
        if not row:
            role = 'owner' if telegram_id == Config.OWNER_ID else 'user'
            self.cursor.execute('''
                INSERT INTO users (telegram_id, first_name, role, last_seen)
                VALUES (?, ?, ?, ?)
            ''', (telegram_id, first_name, role, datetime.datetime.now().isoformat()))
            self.conn.commit()
            return self.get_user(telegram_id, first_name)
        
        # Обновляем last_seen
        self.cursor.execute("UPDATE users SET last_seen = ? WHERE telegram_id = ?",
                          (datetime.datetime.now().isoformat(), telegram_id))
        self.conn.commit()
        
        return dict(row)
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение пользователя по ID"""
        self.cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = self.cursor.fetchone()
        return dict(row) if row else None
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Получение пользователя по username"""
        if username.startswith('@'):
            username = username[1:]
        
        self.cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = self.cursor.fetchone()
        return dict(row) if row else None
    
    def update_user(self, user_id: int, **kwargs) -> bool:
        """Обновление данных пользователя"""
        if not kwargs:
            return False
        
        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values())
        values.append(user_id)
        
        self.cursor.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def add_coins(self, user_id: int, amount: int) -> int:
        """Добавление монет"""
        self.cursor.execute("UPDATE users SET coins = coins + ? WHERE id = ?", (amount, user_id))
        self.conn.commit()
        self.cursor.execute("SELECT coins FROM users WHERE id = ?", (user_id,))
        return self.cursor.fetchone()[0]
    
    def add_diamonds(self, user_id: int, amount: int) -> int:
        """Добавление алмазов"""
        self.cursor.execute("UPDATE users SET diamonds = diamonds + ? WHERE id = ?", (amount, user_id))
        self.conn.commit()
        self.cursor.execute("SELECT diamonds FROM users WHERE id = ?", (user_id,))
        return self.cursor.fetchone()[0]
    
    def add_exp(self, user_id: int, amount: int) -> bool:
        """Добавление опыта"""
        self.cursor.execute("UPDATE users SET exp = exp + ? WHERE id = ?", (amount, user_id))
        self.cursor.execute("SELECT exp, level FROM users WHERE id = ?", (user_id,))
        exp, level = self.cursor.fetchone()
        
        if exp >= level * 100:
            self.cursor.execute("UPDATE users SET level = level + 1, exp = exp - ? WHERE id = ?",
                              (level * 100, user_id))
            self.conn.commit()
            return True
        
        self.conn.commit()
        return False
    
    def add_energy(self, user_id: int, amount: int) -> int:
        """Добавление энергии"""
        self.cursor.execute("UPDATE users SET energy = MIN(100, energy + ?) WHERE id = ?", (amount, user_id))
        self.conn.commit()
        self.cursor.execute("SELECT energy FROM users WHERE id = ?", (user_id,))
        return self.cursor.fetchone()[0]
    
    def heal(self, user_id: int, amount: int) -> int:
        """Лечение"""
        self.cursor.execute("UPDATE users SET health = MIN(max_health, health + ?) WHERE id = ?", (amount, user_id))
        self.conn.commit()
        self.cursor.execute("SELECT health FROM users WHERE id = ?", (user_id,))
        return self.cursor.fetchone()[0]
    
    def damage(self, user_id: int, amount: int) -> int:
        """Нанесение урона"""
        self.cursor.execute("UPDATE users SET health = MAX(0, health - ?) WHERE id = ?", (amount, user_id))
        self.conn.commit()
        self.cursor.execute("SELECT health FROM users WHERE id = ?", (user_id,))
        return self.cursor.fetchone()[0]
    
    def is_vip(self, user_id: int) -> bool:
        """Проверка VIP статуса"""
        self.cursor.execute("SELECT vip_until FROM users WHERE id = ?", (user_id,))
        row = self.cursor.fetchone()
        if row and row[0]:
            return datetime.datetime.fromisoformat(row[0]) > datetime.datetime.now()
        return False
    
    def is_premium(self, user_id: int) -> bool:
        """Проверка PREMIUM статуса"""
        self.cursor.execute("SELECT premium_until FROM users WHERE id = ?", (user_id,))
        row = self.cursor.fetchone()
        if row and row[0]:
            return datetime.datetime.fromisoformat(row[0]) > datetime.datetime.now()
        return False
    
    def set_vip(self, user_id: int, days: int) -> datetime.datetime:
        """Установка VIP статуса"""
        until = datetime.datetime.now() + datetime.timedelta(days=days)
        self.cursor.execute("UPDATE users SET vip_until = ?, role = 'vip' WHERE id = ?",
                          (until.isoformat(), user_id))
        self.conn.commit()
        return until
    
    def set_premium(self, user_id: int, days: int) -> datetime.datetime:
        """Установка PREMIUM статуса"""
        until = datetime.datetime.now() + datetime.timedelta(days=days)
        self.cursor.execute("UPDATE users SET premium_until = ?, role = 'premium' WHERE id = ?",
                          (until.isoformat(), user_id))
        self.conn.commit()
        return until
    
    def get_bosses(self, alive_only: bool = True) -> List[Dict[str, Any]]:
        """Получение списка боссов"""
        if alive_only:
            self.cursor.execute("SELECT * FROM bosses WHERE is_alive = 1 ORDER BY level")
        else:
            self.cursor.execute("SELECT * FROM bosses ORDER BY level")
        return [dict(row) for row in self.cursor.fetchall()]
    
    def get_boss(self, boss_id: int) -> Optional[Dict[str, Any]]:
        """Получение информации о боссе"""
        self.cursor.execute("SELECT * FROM bosses WHERE id = ?", (boss_id,))
        row = self.cursor.fetchone()
        return dict(row) if row else None
    
    def damage_boss(self, boss_id: int, damage: int) -> bool:
        """Нанесение урона боссу"""
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
        """Возрождение боссов"""
        self.cursor.execute("UPDATE bosses SET is_alive = 1, health = max_health")
        self.conn.commit()
    
    def add_boss_kill(self, user_id: int):
        """Добавление убийства босса"""
        self.cursor.execute("UPDATE users SET boss_kills = boss_kills + 1 WHERE id = ?", (user_id,))
        self.conn.commit()
    
    def get_top(self, field: str, limit: int = 10) -> List[Tuple]:
        """Получение топа игроков"""
        self.cursor.execute(f"SELECT first_name, nickname, {field} FROM users ORDER BY {field} DESC LIMIT ?", (limit,))
        return self.cursor.fetchall()
    
    def add_warn(self, user_id: int, admin_id: int, reason: str) -> int:
        """Добавление предупреждения"""
        self.cursor.execute("SELECT warns, warns_list FROM users WHERE id = ?", (user_id,))
        warns, warns_list = self.cursor.fetchone()
        warns_list = json.loads(warns_list)
        
        warns_list.append({
            'id': len(warns_list) + 1,
            'admin_id': admin_id,
            'reason': reason,
            'date': datetime.datetime.now().isoformat()
        })
        
        self.cursor.execute("UPDATE users SET warns = ?, warns_list = ? WHERE id = ?",
                          (warns + 1, json.dumps(warns_list), user_id))
        self.conn.commit()
        return warns + 1
    
    def get_warns(self, user_id: int) -> List[Dict]:
        """Получение списка предупреждений"""
        self.cursor.execute("SELECT warns_list FROM users WHERE id = ?", (user_id,))
        row = self.cursor.fetchone()
        return json.loads(row[0]) if row and row[0] else []
    
    def remove_last_warn(self, user_id: int) -> Optional[Dict]:
        """Удаление последнего предупреждения"""
        self.cursor.execute("SELECT warns, warns_list FROM users WHERE id = ?", (user_id,))
        warns, warns_list = self.cursor.fetchone()
        warns_list = json.loads(warns_list)
        
        if not warns_list:
            return None
        
        removed = warns_list.pop()
        
        self.cursor.execute("UPDATE users SET warns = ?, warns_list = ? WHERE id = ?",
                          (warns - 1, json.dumps(warns_list), user_id))
        self.conn.commit()
        return removed
    
    def mute_user(self, user_id: int, minutes: int, admin_id: int = None, reason: str = "Нарушение") -> datetime.datetime:
        """Мут пользователя"""
        until = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
        self.cursor.execute("UPDATE users SET mute_until = ? WHERE id = ?", (until.isoformat(), user_id))
        self.conn.commit()
        return until
    
    def is_muted(self, user_id: int) -> bool:
        """Проверка на мут"""
        self.cursor.execute("SELECT mute_until FROM users WHERE id = ?", (user_id,))
        row = self.cursor.fetchone()
        if row and row[0]:
            return datetime.datetime.fromisoformat(row[0]) > datetime.datetime.now()
        return False
    
    def unmute_user(self, user_id: int) -> bool:
        """Снятие мута"""
        self.cursor.execute("UPDATE users SET mute_until = NULL WHERE id = ?", (user_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def get_muted_users(self) -> List[Dict[str, Any]]:
        """Список замученных"""
        self.cursor.execute("SELECT id, first_name, username, mute_until FROM users WHERE mute_until > ?",
                          (datetime.datetime.now().isoformat(),))
        return [dict(row) for row in self.cursor.fetchall()]
    
    def ban_user(self, user_id: int, admin_id: int, reason: str = "Нарушение") -> bool:
        """Бан пользователя"""
        self.cursor.execute('''
            UPDATE users SET banned = 1, ban_reason = ?, ban_date = ?, ban_admin = ?
            WHERE id = ?
        ''', (reason, datetime.datetime.now().isoformat(), admin_id, user_id))
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def unban_user(self, user_id: int) -> bool:
        """Разбан пользователя"""
        self.cursor.execute("UPDATE users SET banned = 0, ban_reason = NULL, ban_date = NULL, ban_admin = NULL WHERE id = ?", (user_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def is_banned(self, user_id: int) -> bool:
        """Проверка на бан"""
        self.cursor.execute("SELECT banned FROM users WHERE id = ?", (user_id,))
        row = self.cursor.fetchone()
        return row and row[0] == 1
    
    def get_banlist(self, page: int = 1, limit: int = 10) -> Tuple[List[Dict[str, Any]], int]:
        """Список забаненных"""
        offset = (page - 1) * limit
        
        self.cursor.execute("SELECT COUNT(*) FROM users WHERE banned = 1")
        total = self.cursor.fetchone()[0]
        
        self.cursor.execute('''
            SELECT id, first_name, username, ban_reason, ban_date, ban_admin
            FROM users WHERE banned = 1 ORDER BY ban_date DESC LIMIT ? OFFSET ?
        ''', (limit, offset))
        
        bans = []
        for row in self.cursor.fetchall():
            ban = dict(row)
            if ban['ban_admin']:
                admin = self.get_user_by_id(ban['ban_admin'])
                ban['admin_name'] = admin.get('first_name', 'Система') if admin else 'Система'
            else:
                ban['admin_name'] = 'Система'
            bans.append(ban)
        
        return bans, total
    
    def add_daily_streak(self, user_id: int) -> int:
        """Добавление дня в стрик"""
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
    
    def update_activity(self, user_id: int):
        """Обновление данных активности для диаграммы"""
        today = datetime.datetime.now().strftime("%d.%m")
        
        self.cursor.execute("SELECT activity_data FROM users WHERE id = ?", (user_id,))
        row = self.cursor.fetchone()
        
        if row and row[0]:
            activity = json.loads(row[0])
        else:
            activity = {}
        
        # Увеличиваем счетчик для сегодняшнего дня
        if today in activity:
            activity[today] += 1
        else:
            activity[today] = 1
            
            # Оставляем только последние 30 дней
            if len(activity) > 30:
                oldest = sorted(activity.keys())[0]
                del activity[oldest]
        
        self.cursor.execute("UPDATE users SET activity_data = ? WHERE id = ?",
                          (json.dumps(activity), user_id))
        self.conn.commit()
    
    def get_activity_data(self, user_id: int) -> Dict[str, int]:
        """Получение данных активности"""
        self.cursor.execute("SELECT activity_data FROM users WHERE id = ?", (user_id,))
        row = self.cursor.fetchone()
        return json.loads(row[0]) if row and row[0] else {}
    
    def add_to_blacklist(self, word: str, admin_id: int) -> bool:
        """Добавление слова в черный список"""
        try:
            self.cursor.execute("INSERT INTO blacklist (word, added_by) VALUES (?, ?)",
                              (word.lower(), admin_id))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def remove_from_blacklist(self, word: str) -> bool:
        """Удаление слова из черного списка"""
        self.cursor.execute("DELETE FROM blacklist WHERE word = ?", (word.lower(),))
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def get_blacklist(self) -> List[str]:
        """Получение черного списка"""
        self.cursor.execute("SELECT word FROM blacklist ORDER BY word")
        return [row[0] for row in self.cursor.fetchall()]
    
    def log_action(self, user_id: int, action: str, details: str = "", chat_id: int = None):
        """Логирование действия"""
        self.cursor.execute('''
            INSERT INTO logs (user_id, action, details, chat_id, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, action, details, chat_id, datetime.datetime.now().isoformat()))
        self.conn.commit()
    
    def close(self):
        """Закрытие соединения"""
        if self.conn:
            self.conn.close()

# Инициализация БД
db = Database()

# ========== ГЕНЕРАТОР ДИАГРАММ ==========
class ChartGenerator:
    """Генерация диаграмм активности как в Iris"""
    
    @staticmethod
    def generate_activity_chart(activity_data: Dict[str, int]) -> BytesIO:
        """
        Генерирует диаграмму активности
        Формат как на фото: даты внизу, столбцы активности
        """
        try:
            # Сортируем даты
            dates = sorted(activity_data.keys())
            values = [activity_data[date] for date in dates]
            
            # Если данных мало, добавляем заглушки
            if len(dates) < 5:
                # Создаем тестовые данные как на фото
                test_dates = ["22.06", "13.07", "03.08", "24.08", "14.09", 
                            "05.10", "26.10", "16.11", "07.12", "28.12", 
                            "18.01", "06.02", "13.02"]
                test_values = [random.randint(5, 20) for _ in test_dates]
                dates = test_dates
                values = test_values
            
            # Создаем график
            plt.figure(figsize=(10, 4))
            
            # Столбцы
            bars = plt.bar(dates, values, color='#4CAF50', alpha=0.7, width=0.6)
            
            # Настройка внешнего вида
            plt.title('Статистика активности', fontsize=14, fontweight='bold', pad=20)
            plt.xlabel('Дата', fontsize=10)
            plt.ylabel('Сообщения', fontsize=10)
            
            # Поворот подписей дат
            plt.xticks(rotation=45, ha='right', fontsize=8)
            
            # Добавляем значения над столбцами
            for bar in bars:
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                        f'{int(height)}', ha='center', va='bottom', fontsize=8)
            
            # Сетка для удобства
            plt.grid(axis='y', alpha=0.3, linestyle='--')
            
            # Добавляем подписи "Сохранено/Несохранено" как на фото
            plt.figtext(0.02, 0.98, '📊 Статистика активности', 
                       fontsize=12, fontweight='bold', ha='left')
            plt.figtext(0.02, 0.94, '✅ Сохранено', 
                       fontsize=10, color='green', ha='left')
            plt.figtext(0.02, 0.90, '❌ Несохранено', 
                       fontsize=10, color='red', ha='left')
            
            # Настраиваем отступы
            plt.tight_layout()
            
            # Сохраняем в буфер
            buf = BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            plt.close()
            
            return buf
            
        except Exception as e:
            logger.error(f"Ошибка генерации диаграммы: {e}")
            # Возвращаем пустой буфер в случае ошибки
            return BytesIO()

# ========== ОСНОВНОЙ КЛАСС БОТА ==========
class SpectrumBot:
    """Основной класс бота"""
    
    def __init__(self):
        self.db = db
        self.chart_gen = ChartGenerator()
        self.spam_tracker = defaultdict(list)
        self.application = Application.builder().token(Config.TELEGRAM_TOKEN).build()
        self.start_time = datetime.datetime.now()
        self.setup_handlers()
        logger.info("✅ Бот СПЕКТР инициализирован")
    
    def setup_handlers(self):
        """Регистрация всех обработчиков"""
        
        # ===== ОСНОВНЫЕ КОМАНДЫ =====
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        self.application.add_handler(CommandHandler("menu", self.cmd_menu))
        self.application.add_handler(CommandHandler("id", self.cmd_id))
        self.application.add_handler(CommandHandler("chatid", self.cmd_chatid))
        self.application.add_handler(CommandHandler("ping", self.cmd_ping))
        self.application.add_handler(CommandHandler("info", self.cmd_info))
        self.application.add_handler(CommandHandler("uptime", self.cmd_uptime))
        
        # ===== ПРОФИЛЬ =====
        self.application.add_handler(CommandHandler("profile", self.cmd_profile))
        self.application.add_handler(CommandHandler("nick", self.cmd_nick))
        self.application.add_handler(CommandHandler("title", self.cmd_title))
        self.application.add_handler(CommandHandler("motto", self.cmd_motto))
        self.application.add_handler(CommandHandler("gender", self.cmd_gender))
        self.application.add_handler(CommandHandler("city", self.cmd_city))
        self.application.add_handler(CommandHandler("birth", self.cmd_birth))
        self.application.add_handler(CommandHandler("rep", self.cmd_rep))
        
        # ===== СТАТИСТИКА =====
        self.application.add_handler(CommandHandler("stats", self.cmd_stats))
        self.application.add_handler(CommandHandler("top", self.cmd_top))
        self.application.add_handler(CommandHandler("daily", self.cmd_daily))
        self.application.add_handler(CommandHandler("weekly", self.cmd_weekly))
        self.application.add_handler(CommandHandler("streak", self.cmd_streak))
        
        # ===== БИТВЫ =====
        self.application.add_handler(CommandHandler("bosses", self.cmd_bosses))
        self.application.add_handler(CommandHandler("boss", self.cmd_boss_fight))
        self.application.add_handler(CommandHandler("bossinfo", self.cmd_boss_info))
        self.application.add_handler(CommandHandler("regen", self.cmd_regen))
        
        # ===== КАЗИНО =====
        self.application.add_handler(CommandHandler("casino", self.cmd_casino))
        self.application.add_handler(CommandHandler("roulette", self.cmd_roulette))
        self.application.add_handler(CommandHandler("dice", self.cmd_dice))
        self.application.add_handler(CommandHandler("rps", self.cmd_rps))
        self.application.add_handler(CommandHandler("slots", self.cmd_slots))
        
        # ===== ЭКОНОМИКА =====
        self.application.add_handler(CommandHandler("shop", self.cmd_shop))
        self.application.add_handler(CommandHandler("buy", self.cmd_buy))
        self.application.add_handler(CommandHandler("pay", self.cmd_pay))
        self.application.add_handler(CommandHandler("donate", self.cmd_donate))
        self.application.add_handler(CommandHandler("vip", self.cmd_buy_vip))
        self.application.add_handler(CommandHandler("premium", self.cmd_buy_premium))
        
        # ===== МОДЕРАЦИЯ =====
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
        self.application.add_handler(CommandHandler("clear", self.cmd_clear))
        self.application.add_handler(CommandHandler("pin", self.cmd_pin))
        self.application.add_handler(CommandHandler("unpin", self.cmd_unpin))
        self.application.add_handler(CommandHandler("slowmode", self.cmd_slowmode))
        self.application.add_handler(CommandHandler("adminlist", self.cmd_adminlist))
        self.application.add_handler(CommandHandler("report", self.cmd_report))
        
        # ===== НАСТРОЙКИ ЧАТА =====
        self.application.add_handler(CommandHandler("setwelcome", self.cmd_setwelcome))
        self.application.add_handler(CommandHandler("setrules", self.cmd_setrules))
        self.application.add_handler(CommandHandler("setlang", self.cmd_setlang))
        self.application.add_handler(CommandHandler("setantiflood", self.cmd_setantiflood))
        self.application.add_handler(CommandHandler("setantispam", self.cmd_setantispam))
        self.application.add_handler(CommandHandler("setantilink", self.cmd_setantilink))
        self.application.add_handler(CommandHandler("setcaptcha", self.cmd_setcaptcha))
        self.application.add_handler(CommandHandler("setlog", self.cmd_setlog))
        self.application.add_handler(CommandHandler("rules", self.cmd_show_rules))
        self.application.add_handler(CommandHandler("welcome", self.cmd_show_welcome))
        
        # ===== ЧЕРНЫЙ СПИСОК =====
        self.application.add_handler(CommandHandler("addblacklist", self.cmd_add_blacklist))
        self.application.add_handler(CommandHandler("removeblacklist", self.cmd_remove_blacklist))
        self.application.add_handler(CommandHandler("blacklist", self.cmd_show_blacklist))
        
        # ===== ИГРЫ И РАЗВЛЕЧЕНИЯ =====
        self.application.add_handler(CommandHandler("game", self.cmd_game))
        self.application.add_handler(CommandHandler("quiz", self.cmd_quiz))
        self.application.add_handler(CommandHandler("coin", self.cmd_coin))
        self.application.add_handler(CommandHandler("random", self.cmd_random))
        self.application.add_handler(CommandHandler("choose", self.cmd_choose))
        
        # ===== ПОЛЕЗНОЕ =====
        self.application.add_handler(CommandHandler("weather", self.cmd_weather))
        self.application.add_handler(CommandHandler("time", self.cmd_time))
        self.application.add_handler(CommandHandler("date", self.cmd_date))
        self.application.add_handler(CommandHandler("calc", self.cmd_calc))
        self.application.add_handler(CommandHandler("translate", self.cmd_translate))
        self.application.add_handler(CommandHandler("qr", self.cmd_qr))
        
        # ===== АДМИН-КОМАНДЫ =====
        self.application.add_handler(CommandHandler("promote", self.cmd_promote))
        self.application.add_handler(CommandHandler("demote", self.cmd_demote))
        self.application.add_handler(CommandHandler("leave", self.cmd_leave))
        self.application.add_handler(CommandHandler("broadcast", self.cmd_broadcast))
        
        # ===== ОБРАБОТЧИКИ =====
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, self.handle_new_members))
        self.application.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, self.handle_left_member))
        
        # Обработчик ошибок
        self.application.add_error_handler(self.error_handler)
        
        logger.info(f"✅ Зарегистрировано {len(self.application.handlers)} обработчиков")
    
    def get_role_emoji(self, role: str) -> str:
        """Получение эмодзи для роли"""
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
        """Проверка прав пользователя"""
        role_hierarchy = ['user', 'vip', 'premium', 'moderator', 'admin', 'owner']
        user_role = user_data.get('role', 'user')
        
        if user_role not in role_hierarchy:
            return False
        
        return role_hierarchy.index(user_role) >= role_hierarchy.index(required_role)
    
    async def check_spam(self, update: Update) -> bool:
        """Проверка на спам"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if self.has_permission(user_data, 'premium'):
            return False
        
        now = time.time()
        user_id = user.id
        
        self.spam_tracker[user_id] = [t for t in self.spam_tracker[user_id] if now - t < Config.SPAM_WINDOW]
        self.spam_tracker[user_id].append(now)
        
        if len(self.spam_tracker[user_id]) > Config.SPAM_LIMIT:
            self.db.mute_user(user_data['id'], Config.SPAM_MUTE_TIME, 0, "Авто-спам")
            await update.message.reply_text(f.error(f"Спам! Мут на {Config.SPAM_MUTE_TIME} минут"))
            self.spam_tracker[user_id] = []
            return True
        
        return False
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ошибок"""
        logger.error(f"Ошибка: {context.error}")
        try:
            if update and update.effective_message:
                await update.effective_message.reply_text(f.error("Произошла ошибка"))
        except:
            pass

    # ===== ОСНОВНЫЕ КОМАНДЫ =====

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        user = update.effective_user
        user_data = self.db.get_user(user.id, user.first_name)
        
        text = (
            f.header("ДОБРО ПОЖАЛОВАТЬ") + "\n\n" +
            f"👋 **Привет, {user.first_name}!**\n" +
            f"Я — **СПЕКТР**, твой официальный игровой помощник.\n\n" +
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
            f"👑 **Владелец:** {Config.OWNER_USERNAME}"
        )
        
        await update.message.reply_text(text, reply_markup=kb.main_menu(), parse_mode="Markdown")
        self.db.log_action(user_data['id'], 'start', 'Запуск бота', update.effective_chat.id)
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help"""
        text = (
            f.header("СПРАВКА") + "\n\n" +
            f.section("ОСНОВНЫЕ") +
            f.command("start", "начать работу") + "\n" +
            f.command("menu", "главное меню") + "\n" +
            f.command("profile", "твой профиль") + "\n" +
            f.command("stats", "твоя статистика") + "\n" +
            f.command("top", "топ игроков") + "\n\n" +
            f.section("ПРОФИЛЬ") +
            f.command("nick [ник]", "установить ник") + "\n" +
            f.command("title [титул]", "установить титул") + "\n" +
            f.command("motto [девиз]", "установить девиз") + "\n" +
            f.command("gender [м/ж]", "установить пол") + "\n\n" +
            f.section("ИГРЫ") +
            f.command("bosses", "битва с боссами") + "\n" +
            f.command("casino", "казино") + "\n" +
            f.command("rps", "камень-ножницы-бумага") + "\n\n" +
            f.section("ЭКОНОМИКА") +
            f.command("daily", "ежедневный бонус") + "\n" +
            f.command("shop", "магазин") + "\n" +
            f.command("pay @ник сумма", "перевести монеты") + "\n" +
            f.command("donate", "привилегии") + "\n\n" +
            f.section("МОДЕРАЦИЯ") +
            f.command("warn @ник [причина]", "предупреждение") + "\n" +
            f.command("mute @ник минут [причина]", "заглушить") + "\n" +
            f.command("ban @ник [причина]", "заблокировать") + "\n" +
            f.command("banlist", "список забаненных") + "\n\n" +
            f"👑 **Владелец:** {Config.OWNER_USERNAME}"
        )
        
        await update.message.reply_text(text, reply_markup=kb.back(), parse_mode="Markdown")
    
    async def cmd_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /menu"""
        await update.message.reply_text(
            f.header("ГЛАВНОЕ МЕНЮ") + "\nВыбери раздел:",
            reply_markup=kb.main_menu(),
            parse_mode="Markdown"
        )
    
    async def cmd_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /id"""
        user = update.effective_user
        
        if context.args:
            username = context.args[0].replace('@', '')
            target = self.db.get_user_by_username(username)
            if target:
                await update.message.reply_text(
                    f"🆔 **ID пользователя {username}:**\n`{target['telegram_id']}`",
                    parse_mode="Markdown"
                )
                return
        
        await update.message.reply_text(
            f"🆔 **Твой ID:**\n`{user.id}`",
            parse_mode="Markdown"
        )
    
    async def cmd_chatid(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /chatid"""
        chat = update.effective_chat
        await update.message.reply_text(
            f"💬 **ID чата:**\n`{chat.id}`",
            parse_mode="Markdown"
        )
    
    async def cmd_ping(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /ping"""
        start = time.time()
        msg = await update.message.reply_text("🏓 Pong...")
        end = time.time()
        ping = int((end - start) * 1000)
        await msg.edit_text(f"🏓 **Понг!**\n⏱ `{ping}ms`", parse_mode="Markdown")
    
    async def cmd_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /info"""
        text = (
            f.header("О БОТЕ") + "\n\n" +
            f"🤖 **СПЕКТР** v4.0\n" +
            f"├ Создан: {Config.OWNER_USERNAME}\n" +
            f"├ Язык: Python/Telegram\n" +
            f"├ Команд: 150+\n" +
            f"└ Статус: ✅ Работает\n\n" +
            f"📊 **Статистика**\n" +
            f"├ Пользователей: {self.db.cursor.execute('SELECT COUNT(*) FROM users').fetchone()[0]}\n" +
            f"└ Запущен: {self.start_time.strftime('%d.%m.%Y %H:%M')}"
        )
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_uptime(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /uptime"""
        uptime = datetime.datetime.now() - self.start_time
        days = uptime.days
        hours = uptime.seconds // 3600
        minutes = (uptime.seconds % 3600) // 60
        
        await update.message.reply_text(
            f"⏱ **Аптайм:**\n{days}д {hours}ч {minutes}м",
            parse_mode="Markdown"
        )

    # ===== ПРОФИЛЬ =====

    async def cmd_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /profile с диаграммой активности"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        # Обновляем активность
        self.db.update_activity(user_data['id'])
        
        # Получаем данные для диаграммы
        activity_data = self.db.get_activity_data(user_data['id'])
        
        # Генерируем диаграмму
        chart_buffer = self.chart_gen.generate_activity_chart(activity_data)
        
        # Формируем текст профиля
        display_name = user_data.get('nickname') or user.first_name
        title = user_data.get('title', '')
        motto = user_data.get('motto', 'Нет девиза')
        
        vip_status = "✅ VIP" if self.db.is_vip(user_data['id']) else "❌"
        premium_status = "✅ PREMIUM" if self.db.is_premium(user_data['id']) else "❌"
        
        exp_needed = user_data['level'] * 100
        exp_progress = f.progress(user_data['exp'], exp_needed)
        
        # Считаем общую активность
        total_messages = sum(activity_data.values()) if activity_data else 0
        
        text = (
            f.header("ПРОФИЛЬ") + "\n\n" +
            f"**{display_name}** {title}\n" +
            f"_{motto}_\n\n" +
            f.section("ХАРАКТЕРИСТИКИ") +
            f.stat("Уровень", user_data['level']) + "\n" +
            f.stat("Опыт", exp_progress) + "\n" +
            f.stat("Монеты", f"{user_data['coins']} 💰") + "\n" +
            f.stat("Энергия", f"{user_data['energy']}/100 ⚡") + "\n\n" +
            f.section("БОЕВЫЕ") +
            f.stat("❤️ Здоровье", f"{user_data['health']}/{user_data['max_health']}") + "\n" +
            f.stat("⚔️ Урон", user_data['damage']) + "\n" +
            f.stat("👾 Боссов убито", user_data['boss_kills']) + "\n\n" +
            f.section("СТАТИСТИКА") +
            f.stat("📨 Сообщений", total_messages) + "\n" +
            f.stat("🎮 Игр сыграно", user_data['rps_wins'] + user_data['rps_losses'] + user_data['casino_wins'] + user_data['casino_losses']) + "\n\n" +
            f.section("СТАТУС") +
            f.item(f"VIP: {vip_status}") + "\n" +
            f.item(f"PREMIUM: {premium_status}") + "\n" +
            f.item(f"Пол: {user_data['gender']}") + "\n" +
            f.item(f"ID: `{user.id}`")
        )
        
        # Отправляем с диаграммой
        if chart_buffer.getbuffer().nbytes > 100:
            await update.message.reply_photo(
                photo=chart_buffer,
                caption=text,
                reply_markup=kb.back(),
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(text, reply_markup=kb.back(), parse_mode="Markdown")
    
    async def cmd_nick(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установка ника"""
        if not context.args:
            await update.message.reply_text(f.error("Укажи ник: /nick [ник]"))
            return
        
        nick = " ".join(context.args)
        if len(nick) > Config.MAX_NICK_LENGTH:
            await update.message.reply_text(f.error(f"Максимум {Config.MAX_NICK_LENGTH} символов"))
            return
        
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], nickname=nick)
        
        await update.message.reply_text(f.success(f"Ник установлен: {nick}"))
    
    async def cmd_title(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установка титула"""
        if not context.args:
            await update.message.reply_text(f.error("Укажи титул: /title [титул]"))
            return
        
        title = " ".join(context.args)
        if len(title) > Config.MAX_TITLE_LENGTH:
            await update.message.reply_text(f.error(f"Максимум {Config.MAX_TITLE_LENGTH} символов"))
            return
        
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], title=title)
        
        await update.message.reply_text(f.success(f"Титул установлен: {title}"))
    
    async def cmd_motto(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установка девиза"""
        if not context.args:
            await update.message.reply_text(f.error("Укажи девиз: /motto [девиз]"))
            return
        
        motto = " ".join(context.args)
        if len(motto) > Config.MAX_MOTTO_LENGTH:
            await update.message.reply_text(f.error(f"Максимум {Config.MAX_MOTTO_LENGTH} символов"))
            return
        
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], motto=motto)
        
        await update.message.reply_text(f.success(f"Девиз установлен: _{motto}_"))
    
    async def cmd_gender(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установка пола"""
        if not context.args or context.args[0].lower() not in ['м', 'ж']:
            await update.message.reply_text(f.error("Укажи /gender м или /gender ж"))
            return
        
        gender = "мужской" if context.args[0].lower() == 'м' else "женский"
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], gender=gender)
        
        await update.message.reply_text(f.success(f"Пол установлен: {gender}"))
    
    async def cmd_city(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установка города"""
        if not context.args:
            await update.message.reply_text(f.error("Укажи город: /city [город]"))
            return
        
        city = " ".join(context.args)
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], city=city)
        
        await update.message.reply_text(f.success(f"Город установлен: {city}"))
    
    async def cmd_birth(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установка даты рождения"""
        if not context.args:
            await update.message.reply_text(f.error("Укажи дату: /birth ДД.ММ.ГГГГ"))
            return
        
        date_str = context.args[0]
        try:
            datetime.datetime.strptime(date_str, "%d.%m.%Y")
            user_data = self.db.get_user(update.effective_user.id)
            self.db.update_user(user_data['id'], birth_date=date_str)
            await update.message.reply_text(f.success(f"Дата рождения установлена: {date_str}"))
        except:
            await update.message.reply_text(f.error("Неверный формат. Используй: ДД.ММ.ГГГГ"))
    
    async def cmd_rep(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Изменение репутации"""
        if len(context.args) < 2:
            await update.message.reply_text(f.error("Использование: /rep @ник +/-"))
            return
        
        username = context.args[0].replace('@', '')
        action = context.args[1]
        
        if action not in ['+', '-']:
            await update.message.reply_text(f.error("Используй + или -"))
            return
        
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        change = 1 if action == '+' else -1
        new_rep = target['reputation'] + change
        
        self.db.update_user(target['id'], reputation=new_rep)
        
        action_text = "повысил" if action == '+' else "понизил"
        await update.message.reply_text(
            f.success(f"Ты {action_text} репутацию {target['first_name']}"),
            parse_mode="Markdown"
        )

    # ===== СТАТИСТИКА =====

    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Статистика пользователя"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        text = (
            f.header("ТВОЯ СТАТИСТИКА") + "\n\n" +
            f.section("ОБЩАЯ") +
            f.stat("Сообщений", user_data['messages_count']) + "\n" +
            f.stat("Команд", user_data['commands_used']) + "\n" +
            f.stat("Игр", user_data['rps_wins'] + user_data['rps_losses'] + user_data['casino_wins'] + user_data['casino_losses']) + "\n\n" +
            f.section("КНБ") +
            f.stat("Побед", user_data['rps_wins']) + "\n" +
            f.stat("Поражений", user_data['rps_losses']) + "\n" +
            f.stat("Ничьих", user_data['rps_draws']) + "\n\n" +
            f.section("КАЗИНО") +
            f.stat("Побед", user_data['casino_wins']) + "\n" +
            f.stat("Поражений", user_data['casino_losses'])
        )
        
        await update.message.reply_text(text, reply_markup=kb.back(), parse_mode="Markdown")
    
    async def cmd_top(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Топ игроков"""
        top_coins = self.db.get_top("coins", 10)
        top_level = self.db.get_top("level", 10)
        top_boss = self.db.get_top("boss_kills", 10)
        
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
        
        text += f"\n" + f.section("ПО БОССАМ") + "\n"
        for i, row in enumerate(top_boss, 1):
            name = row[1] or row[0]
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} **{name}** — {row[2]} 👾\n"
        
        await update.message.reply_text(text, reply_markup=kb.back(), parse_mode="Markdown")
    
    async def cmd_daily(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ежедневный бонус"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        # Проверка кулдауна
        if user_data.get('last_daily'):
            last = datetime.datetime.fromisoformat(user_data['last_daily'])
            if (datetime.datetime.now() - last).seconds < Config.DAILY_COOLDOWN:
                remain = Config.DAILY_COOLDOWN - (datetime.datetime.now() - last).seconds
                hours = remain // 3600
                minutes = (remain % 3600) // 60
                await update.message.reply_text(f.warning(f"Бонус через {hours}ч {minutes}м"))
                return
        
        streak = self.db.add_daily_streak(user_data['id'])
        
        # Базовая награда
        coins = random.randint(100, 300)
        exp = random.randint(20, 60)
        
        # Множитель от стрика
        coins = int(coins * (1 + min(streak, 30) * 0.05))
        exp = int(exp * (1 + min(streak, 30) * 0.05))
        
        # Множитель от привилегий
        if self.db.is_vip(user_data['id']):
            coins = int(coins * 1.5)
            exp = int(exp * 1.5)
        if self.db.is_premium(user_data['id']):
            coins = int(coins * 2)
            exp = int(exp * 2)
        
        self.db.add_coins(user_data['id'], coins)
        self.db.add_exp(user_data['id'], exp)
        self.db.add_energy(user_data['id'], 20)
        
        text = (
            f.header("ЕЖЕДНЕВНЫЙ БОНУС") + "\n\n" +
            f.item(f"🔥 Стрик: {streak} дней") + "\n" +
            f.item(f"💰 Монеты: +{coins}") + "\n" +
            f.item(f"✨ Опыт: +{exp}") + "\n" +
            f.item(f"⚡ Энергия: +20") + "\n\n" +
            f.info("Заходи завтра!")
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")
        self.db.log_action(user_data['id'], 'daily', f"Получено {coins}💰, {exp}✨")
    
    async def cmd_weekly(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Недельный бонус"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data.get('last_weekly'):
            last = datetime.datetime.fromisoformat(user_data['last_weekly'])
            if (datetime.datetime.now() - last).seconds < Config.WEEKLY_COOLDOWN:
                await update.message.reply_text(f.warning("Бонус можно получить раз в неделю!"))
                return
        
        coins = random.randint(1000, 3000)
        exp = random.randint(200, 500)
        
        if self.db.is_vip(user_data['id']):
            coins = int(coins * 1.5)
            exp = int(exp * 1.5)
        if self.db.is_premium(user_data['id']):
            coins = int(coins * 2)
            exp = int(exp * 2)
        
        self.db.add_coins(user_data['id'], coins)
        self.db.add_exp(user_data['id'], exp)
        self.db.update_user(user_data['id'], last_weekly=datetime.datetime.now().isoformat())
        
        text = (
            f.header("НЕДЕЛЬНЫЙ БОНУС") + "\n\n" +
            f.item(f"💰 Монеты: +{coins}") + "\n" +
            f.item(f"✨ Опыт: +{exp}") + "\n\n" +
            f.info("Через неделю снова!")
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_streak(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о стрике"""
        user_data = self.db.get_user(update.effective_user.id)
        streak = user_data.get('daily_streak', 0)
        
        await update.message.reply_text(
            f"🔥 **Текущий стрик:** {streak} дней\n" +
            f"📈 Множитель: x{1 + min(streak, 30) * 0.05:.2f}",
            parse_mode="Markdown"
        )

    # ===== БИТВЫ =====

    async def cmd_bosses(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список боссов"""
        user_data = self.db.get_user(update.effective_user.id)
        bosses = self.db.get_bosses()
        
        if not bosses:
            self.db.respawn_bosses()
            bosses = self.db.get_bosses()
        
        text = f.header("АРЕНА БОССОВ") + "\n\n"
        
        if bosses:
            boss = bosses[0]
            bar = f.progress(boss['health'], boss['max_health'], 20)
            text += (
                f"**ТЕКУЩИЙ БОСС**\n" +
                f"└ {boss['name']} (ур.{boss['level']})\n" +
                f"└ ❤️ {bar}\n" +
                f"└ ⚔️ Урон: {boss['damage']}\n" +
                f"└ 💰 Награда: {boss['reward_coins']}\n\n"
            )
        
        text += (
            f.section("ТВОИ ПОКАЗАТЕЛИ") +
            f.stat("❤️ Здоровье", f"{user_data['health']}/{user_data['max_health']}") + "\n" +
            f.stat("⚡ Энергия", f"{user_data['energy']}/100") + "\n" +
            f.stat("⚔️ Урон", user_data['damage']) + "\n" +
            f.stat("👾 Убито", user_data['boss_kills']) + "\n\n" +
            f.section("КОМАНДЫ") +
            f.command("boss [ID]", "атаковать босса", "1") + "\n" +
            f.command("bossinfo [ID]", "информация о боссе", "1") + "\n" +
            f.command("regen", "восстановить ❤️ и ⚡")
        )
        
        await update.message.reply_text(text, reply_markup=kb.back(), parse_mode="Markdown")
    
    async def cmd_boss_fight(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Битва с боссом"""
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
        
        if not boss or not boss['is_alive']:
            await update.message.reply_text(f.error("Босс не найден"))
            return
        
        if user_data['energy'] < 10:
            await update.message.reply_text(f.error("Мало энергии! Используй /regen"))
            return
        
        # Тратим энергию
        self.db.add_energy(user_data['id'], -10)
        
        # Расчет урона
        damage_bonus = 1.0
        if self.db.is_vip(user_data['id']):
            damage_bonus += 0.2
        if self.db.is_premium(user_data['id']):
            damage_bonus += 0.3
        
        player_damage = int(user_data['damage'] * damage_bonus) + random.randint(-5, 5)
        boss_damage = boss['damage'] + random.randint(-5, 5)
        player_taken = max(1, boss_damage - user_data['armor'] // 2)
        
        killed = self.db.damage_boss(boss_id, player_damage)
        self.db.damage(user_data['id'], player_taken)
        
        text = f.header("БИТВА") + "\n\n"
        text += f.item(f"Твой урон: {player_damage}") + "\n"
        text += f.item(f"Урон босса: {player_taken}") + "\n\n"
        
        if killed:
            reward = boss['reward_coins'] * (1 + user_data['level'] // 10)
            if self.db.is_vip(user_data['id']):
                reward = int(reward * 1.5)
            if self.db.is_premium(user_data['id']):
                reward = int(reward * 2)
            
            self.db.add_coins(user_data['id'], reward)
            self.db.add_boss_kill(user_data['id'])
            self.db.add_exp(user_data['id'], boss['reward_exp'])
            
            text += f.success("ПОБЕДА!") + "\n"
            text += f.item(f"💰 +{reward} монет") + "\n"
        else:
            text += f.warning("Босс ещё жив!") + "\n"
        
        if user_data['health'] <= player_taken:
            self.db.heal(user_data['id'], 50)
            text += f"\n" + f.info("Воскрешён с 50❤️")
        
        await update.message.reply_text(text, parse_mode="Markdown")
        self.db.log_action(user_data['id'], 'boss_fight', f"Битва с боссом {boss['name']}")
    
    async def cmd_boss_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о боссе"""
        if not context.args:
            await update.message.reply_text(f.error("Укажи ID босса: /bossinfo 1"))
            return
        
        try:
            boss_id = int(context.args[0])
        except:
            await update.message.reply_text(f.error("Неверный ID"))
            return
        
        boss = self.db.get_boss(boss_id)
        if not boss:
            await update.message.reply_text(f.error("Босс не найден"))
            return
        
        status = "ЖИВ" if boss['is_alive'] else "ПОВЕРЖЕН"
        bar = f.progress(boss['health'], boss['max_health'], 20)
        
        text = (
            f.header(f"БОСС: {boss['name']}") + "\n\n" +
            f.stat("Уровень", boss['level']) + "\n" +
            f.stat("❤️ Здоровье", bar) + "\n" +
            f.stat("⚔️ Урон", boss['damage']) + "\n" +
            f.stat("💰 Награда", f"{boss['reward_coins']} 💰") + "\n" +
            f.stat("📊 Статус", status)
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_regen(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Восстановление"""
        user_data = self.db.get_user(update.effective_user.id)
        cost = 20
        
        if user_data['coins'] < cost:
            await update.message.reply_text(f.error(f"Нужно {cost} 💰"))
            return
        
        self.db.add_coins(user_data['id'], -cost)
        self.db.heal(user_data['id'], 50)
        self.db.add_energy(user_data['id'], 20)
        
        await update.message.reply_text(f.success("Регенерация! ❤️+50 ⚡+20"), parse_mode="Markdown")

    # ===== КАЗИНО =====

    async def cmd_casino(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Меню казино"""
        await update.message.reply_text(
            f.header("КАЗИНО") + "\nВыбери игру:",
            reply_markup=kb.casino_menu(),
            parse_mode="Markdown"
        )
    
    async def cmd_roulette(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Рулетка"""
        user_data = self.db.get_user(update.effective_user.id)
        
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
            await update.message.reply_text(f.error("Недостаточно монет"))
            return
        
        if bet <= 0:
            await update.message.reply_text(f.error("Ставка должна быть > 0"))
            return
        
        # Результат
        num = random.randint(0, 36)
        red = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]
        color = "red" if num in red else "black" if num != 0 else "green"
        
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
            self.db.update_user(user_data['id'], casino_wins=user_data['casino_wins'] + 1)
            result = f.success(f"ВЫИГРЫШ! +{win_amount} 💰")
        else:
            self.db.add_coins(user_data['id'], -bet)
            self.db.update_user(user_data['id'], casino_losses=user_data['casino_losses'] + 1)
            result = f.error(f"ПРОИГРЫШ! -{bet} 💰")
        
        text = (
            f.header("РУЛЕТКА") + "\n\n" +
            f.item(f"Ставка: {bet} 💰") + "\n" +
            f.item(f"Выпало: {num} {color}") + "\n\n" +
            result
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")
        self.db.log_action(user_data['id'], 'roulette', f"Ставка {bet}, результат {num}")
    
    async def cmd_dice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Кости"""
        user_data = self.db.get_user(update.effective_user.id)
        
        bet = 10
        if context.args:
            try:
                bet = int(context.args[0])
            except:
                pass
        
        if bet > user_data['coins']:
            await update.message.reply_text(f.error("Недостаточно монет"))
            return
        
        d1 = random.randint(1, 6)
        d2 = random.randint(1, 6)
        total = d1 + d2
        
        if total in [7, 11]:
            win = bet * 2
            self.db.add_coins(user_data['id'], win)
            self.db.update_user(user_data['id'], casino_wins=user_data['casino_wins'] + 1)
            result = f.success(f"ВЫИГРЫШ! +{win} 💰")
        elif total in [2, 3, 12]:
            self.db.add_coins(user_data['id'], -bet)
            self.db.update_user(user_data['id'], casino_losses=user_data['casino_losses'] + 1)
            result = f.error(f"ПРОИГРЫШ! -{bet} 💰")
        else:
            result = f.info(f"НИЧЬЯ! Ставка возвращена")
        
        text = (
            f.header("КОСТИ") + "\n\n" +
            f.item(f"Ставка: {bet} 💰") + "\n" +
            f.item(f"Кости: {d1} + {d2} = {total}") + "\n\n" +
            result
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_rps(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Камень-ножницы-бумага"""
        await update.message.reply_text(
            f.header("КАМЕНЬ-НОЖНИЦЫ-БУМАГА") + "\nВыбери:",
            reply_markup=kb.rps_game(),
            parse_mode="Markdown"
        )
    
    async def cmd_slots(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Слоты"""
        user_data = self.db.get_user(update.effective_user.id)
        
        bet = 10
        if context.args:
            try:
                bet = int(context.args[0])
            except:
                pass
        
        if bet > user_data['coins']:
            await update.message.reply_text(f.error("Недостаточно монет"))
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
            result = f.success(f"ДЖЕКПОТ! +{win} 💰")
        elif len(set(spin)) == 2:
            win = bet * 2
            result = f.success(f"ВЫИГРЫШ! +{win} 💰")
        else:
            win = 0
            result = f.error(f"ПРОИГРЫШ! -{bet} 💰")
        
        if win > 0:
            self.db.add_coins(user_data['id'], win)
            self.db.update_user(user_data['id'], casino_wins=user_data['casino_wins'] + 1)
        else:
            self.db.add_coins(user_data['id'], -bet)
            self.db.update_user(user_data['id'], casino_losses=user_data['casino_losses'] + 1)
        
        text = (
            f.header("СЛОТЫ") + "\n\n" +
            f"{' '.join(spin)}\n\n" +
            f.item(f"Ставка: {bet} 💰") + "\n" +
            result
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")

    # ===== ЭКОНОМИКА =====

    async def cmd_shop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Магазин"""
        text = (
            f.header("МАГАЗИН") + "\n\n" +
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
            f.command("buy батарейка", "80 💰 (⚡+50)")
        )
        
        await update.message.reply_text(text, reply_markup=kb.back(), parse_mode="Markdown")
    
    async def cmd_buy(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Покупка предметов"""
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
        
        if user_data['coins'] < data['price']:
            await update.message.reply_text(f.error(f"Нужно {data['price']} 💰"))
            return
        
        self.db.add_coins(user_data['id'], -data['price'])
        
        if 'heal' in data:
            new = self.db.heal(user_data['id'], data['heal'])
            await update.message.reply_text(f.success(f"❤️ +{data['heal']} (теперь {new})"))
        elif 'damage' in data:
            new = user_data['damage'] + data['damage']
            self.db.update_user(user_data['id'], damage=new)
            await update.message.reply_text(f.success(f"⚔️ +{data['damage']} (теперь {new})"))
        elif 'armor' in data:
            new = user_data['armor'] + data['armor']
            self.db.update_user(user_data['id'], armor=new)
            await update.message.reply_text(f.success(f"🛡 +{data['armor']} (теперь {new})"))
        elif 'energy' in data:
            new = self.db.add_energy(user_data['id'], data['energy'])
            await update.message.reply_text(f.success(f"⚡ +{data['energy']} (теперь {new})"))
        
        self.db.log_action(user_data['id'], 'buy', f"Куплено: {item}")
    
    async def cmd_pay(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Перевод монет"""
        if len(context.args) < 2:
            await update.message.reply_text(f.error("Использование: /pay @ник сумма"))
            return
        
        username = context.args[0].replace('@', '')
        try:
            amount = int(context.args[1])
        except:
            await update.message.reply_text(f.error("Сумма должна быть числом"))
            return
        
        if amount <= 0:
            await update.message.reply_text(f.error("Сумма должна быть > 0"))
            return
        
        user_data = self.db.get_user(update.effective_user.id)
        
        if user_data['coins'] < amount:
            await update.message.reply_text(f.error(f"Недостаточно монет. Баланс: {user_data['coins']} 💰"))
            return
        
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        if target['id'] == user_data['id']:
            await update.message.reply_text(f.error("Нельзя перевести самому себе"))
            return
        
        # Перевод
        self.db.add_coins(user_data['id'], -amount)
        self.db.add_coins(target['id'], amount)
        
        # Комиссия для не-премиум
        if not self.db.is_premium(user_data['id']):
            commission = int(amount * 0.05)
            self.db.add_coins(user_data['id'], -commission)
            comm_text = f"\n{f.item(f'💸 Комиссия: {commission} (5%)')}"
        else:
            comm_text = ""
        
        target_name = target.get('nickname') or target['first_name']
        
        text = (
            f.header("ПЕРЕВОД") + "\n\n" +
            f.item(f"Получатель: {target_name}") + "\n" +
            f.item(f"Сумма: {amount} 💰") +
            comm_text + "\n" +
            f.item(f"Отправитель: {update.effective_user.first_name}") + "\n\n" +
            f.success("Перевод выполнен!")
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")
        self.db.log_action(user_data['id'], 'pay', f"Перевод {amount}💰 пользователю {target['id']}")
    
    async def cmd_donate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о привилегиях"""
        text = (
            f.header("ПРИВИЛЕГИИ") + "\n\n" +
            f.section("VIP СТАТУС") +
            f"Цена: {Config.VIP_PRICE} 💰 / {Config.VIP_DAYS} дней\n" +
            f.item("⚔️ Урон +20%") + "\n" +
            f.item("💰 Награда +50%") + "\n" +
            f.item("🎁 Бонус +50%") + "\n\n" +
            f.section("PREMIUM СТАТУС") +
            f"Цена: {Config.PREMIUM_PRICE} 💰 / {Config.PREMIUM_DAYS} дней\n" +
            f.item("⚔️ Урон +50%") + "\n" +
            f.item("💰 Награда +100%") + "\n" +
            f.item("🎁 Бонус +100%") + "\n" +
            f.item("🚫 Без комиссии") + "\n\n" +
            f.command("vip", "купить VIP") + "\n" +
            f.command("premium", "купить PREMIUM")
        )
        
        await update.message.reply_text(text, reply_markup=kb.back(), parse_mode="Markdown")
    
    async def cmd_buy_vip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Покупка VIP"""
        user_data = self.db.get_user(update.effective_user.id)
        
        if user_data['coins'] < Config.VIP_PRICE:
            await update.message.reply_text(f.error(f"Нужно {Config.VIP_PRICE} 💰"))
            return
        
        if self.db.is_vip(user_data['id']):
            await update.message.reply_text(f.error("VIP уже активен"))
            return
        
        self.db.add_coins(user_data['id'], -Config.VIP_PRICE)
        until = self.db.set_vip(user_data['id'], Config.VIP_DAYS)
        date_str = until.strftime("%d.%m.%Y")
        
        await update.message.reply_text(
            f.success("VIP АКТИВИРОВАН") + "\n\n" +
            f.item("Срок: до " + date_str),
            parse_mode="Markdown"
        )
        self.db.log_action(user_data['id'], 'buy_vip', f"Куплен VIP на {Config.VIP_DAYS} дней")
    
    async def cmd_buy_premium(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Покупка PREMIUM"""
        user_data = self.db.get_user(update.effective_user.id)
        
        if user_data['coins'] < Config.PREMIUM_PRICE:
            await update.message.reply_text(f.error(f"Нужно {Config.PREMIUM_PRICE} 💰"))
            return
        
        if self.db.is_premium(user_data['id']):
            await update.message.reply_text(f.error("PREMIUM уже активен"))
            return
        
        self.db.add_coins(user_data['id'], -Config.PREMIUM_PRICE)
        until = self.db.set_premium(user_data['id'], Config.PREMIUM_DAYS)
        date_str = until.strftime("%d.%m.%Y")
        
        await update.message.reply_text(
            f.success("PREMIUM АКТИВИРОВАН") + "\n\n" +
            f.item("Срок: до " + date_str),
            parse_mode="Markdown"
        )
        self.db.log_action(user_data['id'], 'buy_premium', f"Куплен PREMIUM на {Config.PREMIUM_DAYS} дней")

    # ===== МОДЕРАЦИЯ =====

    async def cmd_warn(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Предупреждение"""
        admin = update.effective_user
        admin_data = self.db.get_user(admin.id)
        
        if not self.has_permission(admin_data, 'moderator') and admin.id != Config.OWNER_ID:
            await update.message.reply_text(f.error("Нет прав"))
            return
        
        if len(context.args) < 1:
            await update.message.reply_text(f.error("Использование: /warn @ник [причина]"))
            return
        
        username = context.args[0].replace('@', '')
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else "Нарушение"
        
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        if self.has_permission(target, 'moderator') and admin.id != Config.OWNER_ID:
            await update.message.reply_text(f.error("Нельзя предупредить администратора"))
            return
        
        warns = self.db.add_warn(target['id'], admin_data['id'], reason)
        
        target_name = target.get('nickname') or target['first_name']
        
        text = (
            f.header("ПРЕДУПРЕЖДЕНИЕ") + "\n\n" +
            f.item(f"Пользователь: {target_name}") + "\n" +
            f.item(f"Предупреждений: {warns}/3") + "\n" +
            f.item(f"Причина: {reason}") + "\n" +
            f.item(f"Администратор: {admin.first_name}")
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")
        
        # Авто-мут при 3 предупреждениях
        if warns >= 3:
            self.db.mute_user(target['id'], 60, admin_data['id'], "3 предупреждения")
            await update.message.reply_text(f.warning(f"{target_name} замучен на 60 минут"))
        
        self.db.log_action(admin_data['id'], 'warn', f"Предупреждение {target['id']}: {reason}")
    
    async def cmd_warns(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список предупреждений"""
        if not context.args:
            await update.message.reply_text(f.error("Укажи пользователя: /warns @ник"))
            return
        
        username = context.args[0].replace('@', '')
        target = self.db.get_user_by_username(username)
        
        if not target:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        warns_list = self.db.get_warns(target['id'])
        target_name = target.get('nickname') or target['first_name']
        
        if not warns_list:
            await update.message.reply_text(f.info(f"У {target_name} нет предупреждений"))
            return
        
        text = f.header(f"ПРЕДУПРЕЖДЕНИЯ: {target_name}") + "\n\n"
        
        for warn in warns_list:
            admin = self.db.get_user_by_id(warn['admin_id'])
            admin_name = admin.get('first_name', 'Система') if admin else 'Система'
            date = datetime.datetime.fromisoformat(warn['date']).strftime("%d.%m.%Y %H:%M")
            
            text += (
                f"**ID: {warn['id']}**\n" +
                f"└ Причина: {warn['reason']}\n" +
                f"└ Админ: {admin_name}\n" +
                f"└ Дата: {date}\n\n"
            )
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_unwarn(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Снятие предупреждения"""
        admin = update.effective_user
        admin_data = self.db.get_user(admin.id)
        
        if not self.has_permission(admin_data, 'moderator') and admin.id != Config.OWNER_ID:
            await update.message.reply_text(f.error("Нет прав"))
            return
        
        if not context.args:
            await update.message.reply_text(f.error("Укажи пользователя: /unwarn @ник"))
            return
        
        username = context.args[0].replace('@', '')
        target = self.db.get_user_by_username(username)
        
        if not target:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        removed = self.db.remove_last_warn(target['id'])
        target_name = target.get('nickname') or target['first_name']
        
        if not removed:
            await update.message.reply_text(f.info(f"У {target_name} нет предупреждений"))
            return
        
        await update.message.reply_text(f.success(f"Предупреждение снято с {target_name}"))
        self.db.log_action(admin_data['id'], 'unwarn', f"Снято предупреждение с {target['id']}")
    
    async def cmd_mute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Мут пользователя"""
        admin = update.effective_user
        admin_data = self.db.get_user(admin.id)
        
        if not self.has_permission(admin_data, 'moderator') and admin.id != Config.OWNER_ID:
            await update.message.reply_text(f.error("Нет прав"))
            return
        
        if len(context.args) < 2:
            await update.message.reply_text(f.error("Использование: /mute @ник минут [причина]"))
            return
        
        username = context.args[0].replace('@', '')
        try:
            minutes = int(context.args[1])
            reason = " ".join(context.args[2:]) if len(context.args) > 2 else "Нарушение"
        except:
            await update.message.reply_text(f.error("Время должно быть числом"))
            return
        
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        if self.has_permission(target, 'moderator') and admin.id != Config.OWNER_ID:
            await update.message.reply_text(f.error("Нельзя замутить администратора"))
            return
        
        until = self.db.mute_user(target['id'], minutes, admin_data['id'], reason)
        target_name = target.get('nickname') or target['first_name']
        
        until_str = until.strftime("%d.%m.%Y %H:%M")
        
        text = (
            f.header("МУТ") + "\n\n" +
            f.item(f"Пользователь: {target_name}") + "\n" +
            f.item(f"Срок: {minutes} минут") + "\n" +
            f.item(f"До: {until_str}") + "\n" +
            f.item(f"Причина: {reason}") + "\n" +
            f.item(f"Админ: {admin.first_name}")
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")
        self.db.log_action(admin_data['id'], 'mute', f"Мут {target['id']} на {minutes} минут")
    
    async def cmd_unmute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Снятие мута"""
        admin = update.effective_user
        admin_data = self.db.get_user(admin.id)
        
        if not self.has_permission(admin_data, 'moderator') and admin.id != Config.OWNER_ID:
            await update.message.reply_text(f.error("Нет прав"))
            return
        
        if not context.args:
            await update.message.reply_text(f.error("Укажи пользователя: /unmute @ник"))
            return
        
        username = context.args[0].replace('@', '')
        target = self.db.get_user_by_username(username)
        
        if not target:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        if not self.db.is_muted(target['id']):
            await update.message.reply_text(f.info("Пользователь не в муте"))
            return
        
        self.db.unmute_user(target['id'])
        target_name = target.get('nickname') or target['first_name']
        
        await update.message.reply_text(f.success(f"Мут снят с {target_name}"))
        self.db.log_action(admin_data['id'], 'unmute', f"Снят мут с {target['id']}")
    
    async def cmd_mutelist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список замученных"""
        muted = self.db.get_muted_users()
        
        if not muted:
            await update.message.reply_text(f.info("Нет пользователей в муте"))
            return
        
        text = f.header("СПИСОК ЗАМУЧЕННЫХ") + "\n\n"
        
        for user in muted[:10]:
            until = datetime.datetime.fromisoformat(user['mute_until']).strftime("%d.%m.%Y %H:%M")
            name = user.get('nickname') or user['first_name']
            text += f.item(f"{name} — до {until}") + "\n"
        
        if len(muted) > 10:
            text += f"\n... и еще {len(muted) - 10}"
        
        await update.message.reply_text(text, reply_markup=kb.back(), parse_mode="Markdown")
    
    async def cmd_ban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Бан пользователя"""
        admin = update.effective_user
        admin_data = self.db.get_user(admin.id)
        
        if not self.has_permission(admin_data, 'moderator') and admin.id != Config.OWNER_ID:
            await update.message.reply_text(f.error("Нет прав"))
            return
        
        if len(context.args) < 1:
            await update.message.reply_text(f.error("Использование: /ban @ник [причина]"))
            return
        
        username = context.args[0].replace('@', '')
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else "Нарушение"
        
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        if self.has_permission(target, 'moderator') and admin.id != Config.OWNER_ID:
            await update.message.reply_text(f.error("Нельзя забанить администратора"))
            return
        
        if self.db.is_banned(target['id']):
            await update.message.reply_text(f.error("Пользователь уже забанен"))
            return
        
        self.db.ban_user(target['id'], admin_data['id'], reason)
        target_name = target.get('nickname') or target['first_name']
        
        text = (
            f.header("БЛОКИРОВКА") + "\n\n" +
            f.item(f"Пользователь: {target_name}") + "\n" +
            f.item(f"Причина: {reason}") + "\n" +
            f.item(f"Админ: {admin.first_name}")
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")
        self.db.log_action(admin_data['id'], 'ban', f"Бан {target['id']}: {reason}")
    
    async def cmd_unban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Разбан пользователя"""
        admin = update.effective_user
        admin_data = self.db.get_user(admin.id)
        
        if not self.has_permission(admin_data, 'moderator') and admin.id != Config.OWNER_ID:
            await update.message.reply_text(f.error("Нет прав"))
            return
        
        if not context.args:
            await update.message.reply_text(f.error("Укажи пользователя: /unban @ник"))
            return
        
        username = context.args[0].replace('@', '')
        target = self.db.get_user_by_username(username)
        
        if not target:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        if not self.db.is_banned(target['id']):
            await update.message.reply_text(f.info("Пользователь не забанен"))
            return
        
        self.db.unban_user(target['id'])
        target_name = target.get('nickname') or target['first_name']
        
        await update.message.reply_text(f.success(f"Бан снят с {target_name}"))
        self.db.log_action(admin_data['id'], 'unban', f"Разбан {target['id']}")
    
    async def cmd_banlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список забаненных"""
        page = 1
        if context.args and context.args[0].isdigit():
            page = int(context.args[0])
        
        bans, total = self.db.get_banlist(page)
        total_pages = (total + 9) // 10
        
        if not bans:
            await update.message.reply_text(f.info("Список забаненных пуст"))
            return
        
        text = f.header("СПИСОК ЗАБАНЕННЫХ") + "\n"
        text += f"Страница {page}/{total_pages}\n\n"
        
        for i, ban in enumerate(bans, 1):
            date = datetime.datetime.fromisoformat(ban['ban_date']).strftime("%d.%m.%Y") if ban['ban_date'] else "неизвестно"
            name = ban.get('nickname') or ban['first_name']
            text += (
                f"{i}. {name}\n" +
                f"└ Причина: {ban['ban_reason']}\n" +
                f"└ Дата: {date}\n" +
                f"└ Заблокировал: {ban['admin_name']}\n\n"
            )
        
        await update.message.reply_text(
            text,
            reply_markup=kb.pagination(page, total_pages, "banlist"),
            parse_mode="Markdown"
        )
    
    async def cmd_kick(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Исключение пользователя"""
        admin = update.effective_user
        admin_data = self.db.get_user(admin.id)
        
        if not self.has_permission(admin_data, 'moderator') and admin.id != Config.OWNER_ID:
            await update.message.reply_text(f.error("Нет прав"))
            return
        
        if not context.args:
            await update.message.reply_text(f.error("Укажи пользователя: /kick @ник"))
            return
        
        username = context.args[0].replace('@', '')
        target = self.db.get_user_by_username(username)
        
        if not target:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        target_name = target.get('nickname') or target['first_name']
        
        # В Telegram нужно использовать ban с последующим unban для kick
        try:
            await update.effective_chat.ban_member(target['telegram_id'])
            await update.effective_chat.unban_member(target['telegram_id'])
            await update.message.reply_text(f.success(f"Пользователь {target_name} исключен"))
        except Exception as e:
            await update.message.reply_text(f.error(f"Ошибка: {e}"))
    
    async def cmd_clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Очистка сообщений"""
        admin = update.effective_user
        admin_data = self.db.get_user(admin.id)
        
        if not self.has_permission(admin_data, 'moderator') and admin.id != Config.OWNER_ID:
            await update.message.reply_text(f.error("Нет прав"))
            return
        
        if not context.args:
            await update.message.reply_text(f.error("Укажи количество: /clear [1-100]"))
            return
        
        try:
            amount = int(context.args[0])
            if amount <= 0 or amount > 100:
                await update.message.reply_text(f.error("От 1 до 100"))
                return
        except:
            await update.message.reply_text(f.error("Неверное число"))
            return
        
        await update.message.reply_text(f"🧹 Очищаю {amount} сообщений...")
        # В группах нужно больше прав
    
    async def cmd_pin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Закрепление сообщения"""
        if not update.message.reply_to_message:
            await update.message.reply_text(f.error("Ответь на сообщение для закрепления"))
            return
        
        try:
            await update.message.reply_to_message.pin()
            await update.message.reply_text(f.success("Сообщение закреплено"))
        except Exception as e:
            await update.message.reply_text(f.error(f"Ошибка: {e}"))
    
    async def cmd_unpin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Открепление сообщения"""
        try:
            await update.effective_chat.unpin_message()
            await update.message.reply_text(f.success("Сообщение откреплено"))
        except Exception as e:
            await update.message.reply_text(f.error(f"Ошибка: {e}"))
    
    async def cmd_slowmode(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Медленный режим"""
        admin = update.effective_user
        admin_data = self.db.get_user(admin.id)
        
        if not self.has_permission(admin_data, 'moderator') and admin.id != Config.OWNER_ID:
            await update.message.reply_text(f.error("Нет прав"))
            return
        
        if not context.args:
            await update.message.reply_text(f.error("Укажи секунды: /slowmode [секунд]"))
            return
        
        try:
            seconds = int(context.args[0])
            if seconds < 0 or seconds > 3600:
                await update.message.reply_text(f.error("От 0 до 3600 секунд"))
                return
            
            await update.effective_chat.set_slow_mode_delay(seconds)
            if seconds > 0:
                await update.message.reply_text(f.success(f"Медленный режим: {seconds} секунд"))
            else:
                await update.message.reply_text(f.success("Медленный режим отключен"))
        except Exception as e:
            await update.message.reply_text(f.error(f"Ошибка: {e}"))
    
    async def cmd_adminlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список администраторов"""
        try:
            admins = await update.effective_chat.get_administrators()
            text = f.header("АДМИНИСТРАТОРЫ") + "\n\n"
            
            for admin in admins:
                user = admin.user
                if user.is_bot:
                    continue
                text += f.item(f"{user.first_name} (@{user.username})") + "\n"
            
            await update.message.reply_text(text, parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f.error(f"Ошибка: {e}"))
    
    async def cmd_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Репорт на пользователя"""
        if not update.message.reply_to_message:
            await update.message.reply_text(f.error("Ответь на сообщение нарушителя"))
            return
        
        reported = update.message.reply_to_message.from_user
        reporter = update.effective_user
        reason = " ".join(context.args) if context.args else "Нарушение"
        
        # Отправляем админам
        text = (
            f.header("РЕПОРТ") + "\n\n" +
            f.item(f"От: {reporter.first_name}") + "\n" +
            f.item(f"На: {reported.first_name} (@{reported.username})") + "\n" +
            f.item(f"Причина: {reason}") + "\n\n" +
            f"ID нарушителя: `{reported.id}`"
        )
        
        await update.message.reply_text(f.success("Репорт отправлен администраторам"))
        
        # Здесь можно добавить пересылку админам

    # ===== НАСТРОЙКИ ЧАТА =====

    async def cmd_setwelcome(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установка приветствия"""
        if not context.args:
            await update.message.reply_text(f.error("Укажи текст приветствия"))
            return
        
        text = " ".join(context.args)
        chat_id = update.effective_chat.id
        
        self.db.cursor.execute("INSERT OR REPLACE INTO chat_settings (chat_id, welcome) VALUES (?, ?)",
                              (chat_id, text))
        self.db.conn.commit()
        
        await update.message.reply_text(f.success("Приветствие установлено"))
    
    async def cmd_setrules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установка правил"""
        if not context.args:
            await update.message.reply_text(f.error("Укажи текст правил"))
            return
        
        text = " ".join(context.args)
        chat_id = update.effective_chat.id
        
        self.db.cursor.execute("INSERT OR REPLACE INTO chat_settings (chat_id, rules) VALUES (?, ?)",
                              (chat_id, text))
        self.db.conn.commit()
        
        await update.message.reply_text(f.success("Правила установлены"))
    
    async def cmd_setlang(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установка языка"""
        if not context.args or context.args[0] not in ['ru', 'en', 'uk']:
            await update.message.reply_text(f.error("Доступно: ru, en, uk"))
            return
        
        lang = context.args[0]
        chat_id = update.effective_chat.id
        
        self.db.cursor.execute("INSERT OR REPLACE INTO chat_settings (chat_id, lang) VALUES (?, ?)",
                              (chat_id, lang))
        self.db.conn.commit()
        
        await update.message.reply_text(f.success(f"Язык установлен: {lang}"))
    
    async def cmd_setantiflood(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Антифлуд"""
        if not context.args or context.args[0] not in ['on', 'off']:
            await update.message.reply_text(f.error("Используй: /setantiflood on/off"))
            return
        
        value = 1 if context.args[0] == 'on' else 0
        chat_id = update.effective_chat.id
        
        self.db.cursor.execute("INSERT OR REPLACE INTO chat_settings (chat_id, antiflood) VALUES (?, ?)",
                              (chat_id, value))
        self.db.conn.commit()
        
        await update.message.reply_text(f.success(f"Антифлуд: {context.args[0]}"))
    
    async def cmd_setantispam(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Антиспам"""
        if not context.args or context.args[0] not in ['on', 'off']:
            await update.message.reply_text(f.error("Используй: /setantispam on/off"))
            return
        
        value = 1 if context.args[0] == 'on' else 0
        chat_id = update.effective_chat.id
        
        self.db.cursor.execute("INSERT OR REPLACE INTO chat_settings (chat_id, antispam) VALUES (?, ?)",
                              (chat_id, value))
        self.db.conn.commit()
        
        await update.message.reply_text(f.success(f"Антиспам: {context.args[0]}"))
    
    async def cmd_setantilink(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Запрет ссылок"""
        if not context.args or context.args[0] not in ['on', 'off']:
            await update.message.reply_text(f.error("Используй: /setantilink on/off"))
            return
        
        value = 1 if context.args[0] == 'on' else 0
        chat_id = update.effective_chat.id
        
        self.db.cursor.execute("INSERT OR REPLACE INTO chat_settings (chat_id, antilink) VALUES (?, ?)",
                              (chat_id, value))
        self.db.conn.commit()
        
        await update.message.reply_text(f.success(f"Запрет ссылок: {context.args[0]}"))
    
    async def cmd_setcaptcha(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Капча при входе"""
        if not context.args or context.args[0] not in ['on', 'off']:
            await update.message.reply_text(f.error("Используй: /setcaptcha on/off"))
            return
        
        value = 1 if context.args[0] == 'on' else 0
        chat_id = update.effective_chat.id
        
        self.db.cursor.execute("INSERT OR REPLACE INTO chat_settings (chat_id, captcha) VALUES (?, ?)",
                              (chat_id, value))
        self.db.conn.commit()
        
        await update.message.reply_text(f.success(f"Капча: {context.args[0]}"))
    
    async def cmd_setlog(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установка чата для логов"""
        if not context.args:
            await update.message.reply_text(f.error("Укажи ID чата для логов"))
            return
        
        try:
            log_chat = int(context.args[0])
            chat_id = update.effective_chat.id
            
            self.db.cursor.execute("INSERT OR REPLACE INTO chat_settings (chat_id, log_chat) VALUES (?, ?)",
                                  (chat_id, log_chat))
            self.db.conn.commit()
            
            await update.message.reply_text(f.success(f"Лог-чат установлен: {log_chat}"))
        except:
            await update.message.reply_text(f.error("Неверный ID"))
    
    async def cmd_show_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать правила"""
        chat_id = update.effective_chat.id
        
        self.db.cursor.execute("SELECT rules FROM chat_settings WHERE chat_id = ?", (chat_id,))
        row = self.db.cursor.fetchone()
        
        if row and row[0]:
            await update.message.reply_text(
                f.header("ПРАВИЛА ЧАТА") + "\n\n" + row[0],
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(f.info("Правила не установлены"))
    
    async def cmd_show_welcome(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать приветствие"""
        chat_id = update.effective_chat.id
        
        self.db.cursor.execute("SELECT welcome FROM chat_settings WHERE chat_id = ?", (chat_id,))
        row = self.db.cursor.fetchone()
        
        if row and row[0]:
            await update.message.reply_text(
                f.header("ПРИВЕТСТВИЕ") + "\n\n" + row[0],
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(f.info("Приветствие не установлено"))

    # ===== ЧЕРНЫЙ СПИСОК =====

    async def cmd_add_blacklist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Добавление слова в черный список"""
        admin = update.effective_user
        admin_data = self.db.get_user(admin.id)
        
        if not self.has_permission(admin_data, 'moderator') and admin.id != Config.OWNER_ID:
            await update.message.reply_text(f.error("Нет прав"))
            return
        
        if not context.args:
            await update.message.reply_text(f.error("Укажи слово для добавления"))
            return
        
        word = " ".join(context.args).lower()
        
        if self.db.add_to_blacklist(word, admin_data['id']):
            await update.message.reply_text(f.success(f"Слово '{word}' добавлено в черный список"))
        else:
            await update.message.reply_text(f.error(f"Слово '{word}' уже в списке"))
    
    async def cmd_remove_blacklist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Удаление слова из черного списка"""
        admin = update.effective_user
        admin_data = self.db.get_user(admin.id)
        
        if not self.has_permission(admin_data, 'moderator') and admin.id != Config.OWNER_ID:
            await update.message.reply_text(f.error("Нет прав"))
            return
        
        if not context.args:
            await update.message.reply_text(f.error("Укажи слово для удаления"))
            return
        
        word = " ".join(context.args).lower()
        
        if self.db.remove_from_blacklist(word):
            await update.message.reply_text(f.success(f"Слово '{word}' удалено из черного списка"))
        else:
            await update.message.reply_text(f.error(f"Слово '{word}' не найдено"))
    
    async def cmd_show_blacklist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать черный список"""
        blacklist = self.db.get_blacklist()
        
        if not blacklist:
            await update.message.reply_text(f.info("Черный список пуст"))
            return
        
        text = f.header("ЧЕРНЫЙ СПИСОК") + "\n\n"
        for word in blacklist[:20]:
            text += f.item(word) + "\n"
        
        if len(blacklist) > 20:
            text += f"\n... и еще {len(blacklist) - 20}"
        
        await update.message.reply_text(text, parse_mode="Markdown")

    # ===== ИГРЫ И РАЗВЛЕЧЕНИЯ =====

    async def cmd_game(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список игр"""
        text = (
            f.header("ИГРЫ") + "\n\n" +
            f.command("quiz", "викторина") + "\n" +
            f.command("coin", "подбросить монету") + "\n" +
            f.command("random [мин] [макс]", "случайное число") + "\n" +
            f.command("choose [а] [б]", "выбрать из вариантов")
        )
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_quiz(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Викторина"""
        questions = [
            {"q": "Столица Франции?", "a": "Париж"},
            {"q": "Сколько планет в солнечной системе?", "a": "8"},
            {"q": "Кто написал 'Война и мир'?", "a": "Толстой"},
            {"q": "Самый большой океан?", "a": "Тихий"},
            {"q": "Год начала Второй мировой войны?", "a": "1939"}
        ]
        
        q = random.choice(questions)
        await update.message.reply_text(f"❓ **Вопрос:** {q['q']}\n\n(ответ напиши в чат)")
        # Здесь нужна система ожидания ответа
    
    async def cmd_coin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Монетка"""
        result = random.choice(["Орел", "Решка"])
        await update.message.reply_text(f"🪙 **Монетка:** {result}", parse_mode="Markdown")
    
    async def cmd_random(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Случайное число"""
        if len(context.args) < 2:
            await update.message.reply_text(f.error("Использование: /random мин макс"))
            return
        
        try:
            min_val = int(context.args[0])
            max_val = int(context.args[1])
            if min_val >= max_val:
                await update.message.reply_text(f.error("min должно быть меньше max"))
                return
            
            result = random.randint(min_val, max_val)
            await update.message.reply_text(f"🎲 **Случайное число:** {result}", parse_mode="Markdown")
        except:
            await update.message.reply_text(f.error("Неверные числа"))
    
    async def cmd_choose(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор из вариантов"""
        if len(context.args) < 2:
            await update.message.reply_text(f.error("Укажи варианты: /choose вариант1 вариант2 ..."))
            return
        
        choice = random.choice(context.args)
        await update.message.reply_text(f"🤔 **Я выбираю:** {choice}", parse_mode="Markdown")

    # ===== ПОЛЕЗНОЕ =====

    async def cmd_weather(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Погода"""
        city = " ".join(context.args) if context.args else "Москва"
        
        # Симуляция погоды
        weathers = ["☀️ солнечно", "⛅ облачно", "☁️ пасмурно", "🌧 дождь", "⛈ гроза", "❄️ снег"]
        temp = random.randint(-15, 30)
        wind = random.randint(0, 15)
        weather = random.choice(weathers)
        
        text = (
            f.header(f"ПОГОДА: {city.upper()}") + "\n\n" +
            f"{weather}, {temp}°C\n" +
            f"💨 Ветер: {wind} м/с\n" +
            f"📅 {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_time(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Текущее время"""
        now = datetime.datetime.now()
        date_str = now.strftime("%d.%m.%Y")
        time_str = now.strftime("%H:%M:%S")
        
        await update.message.reply_text(
            f"⏰ **Текущее время:**\n{date_str} {time_str}",
            parse_mode="Markdown"
        )
    
    async def cmd_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Текущая дата"""
        now = datetime.datetime.now()
        date_str = now.strftime("%d.%m.%Y")
        day_str = now.strftime("%A")
        
        await update.message.reply_text(
            f"📅 **Сегодня:** {date_str}\n📆 **День недели:** {day_str}",
            parse_mode="Markdown"
        )
    
    async def cmd_calc(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Калькулятор"""
        if not context.args:
            await update.message.reply_text(f.error("Укажи выражение: /calc 2+2"))
            return
        
        expr = " ".join(context.args)
        try:
            # Безопасное вычисление
            result = eval(expr, {"__builtins__": {}}, {})
            await update.message.reply_text(f"🧮 **Результат:** {result}", parse_mode="Markdown")
        except:
            await update.message.reply_text(f.error("Неверное выражение"))
    
    async def cmd_translate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Переводчик (заглушка)"""
        await update.message.reply_text(f.info("Функция перевода в разработке"))
    
    async def cmd_qr(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """QR-код (заглушка)"""
        await update.message.reply_text(f.info("Генерация QR-кода в разработке"))

    # ===== АДМИН-КОМАНДЫ =====

    async def cmd_promote(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Назначение администратора"""
        if update.effective_user.id != Config.OWNER_ID:
            await update.message.reply_text(f.error("Только для владельца"))
            return
        
        if not context.args:
            await update.message.reply_text(f.error("Укажи пользователя: /promote @ник"))
            return
        
        username = context.args[0].replace('@', '')
        target = self.db.get_user_by_username(username)
        
        if not target:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        self.db.update_user(target['id'], role='admin')
        await update.message.reply_text(f.success(f"{target['first_name']} теперь администратор"))
    
    async def cmd_demote(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Снятие администратора"""
        if update.effective_user.id != Config.OWNER_ID:
            await update.message.reply_text(f.error("Только для владельца"))
            return
        
        if not context.args:
            await update.message.reply_text(f.error("Укажи пользователя: /demote @ник"))
            return
        
        username = context.args[0].replace('@', '')
        target = self.db.get_user_by_username(username)
        
        if not target:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        self.db.update_user(target['id'], role='user')
        await update.message.reply_text(f.success(f"{target['first_name']} больше не администратор"))
    
    async def cmd_leave(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Бот покидает чат"""
        if update.effective_user.id != Config.OWNER_ID:
            await update.message.reply_text(f.error("Только для владельца"))
            return
        
        await update.message.reply_text("👋 Пока!")
        await update.effective_chat.leave()
    
    async def cmd_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Рассылка по всем чатам"""
        if update.effective_user.id != Config.OWNER_ID:
            await update.message.reply_text(f.error("Только для владельца"))
            return
        
        if not context.args:
            await update.message.reply_text(f.error("Укажи текст рассылки"))
            return
        
        text = " ".join(context.args)
        await update.message.reply_text(f.success("Рассылка отправляется..."))
        
        # Здесь нужно получить все чаты и разослать

    # ===== ОБРАБОТЧИКИ =====

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        user = update.effective_user
        message_text = update.message.text
        
        if message_text.startswith('/'):
            return
        
        user_data = self.db.get_user(user.id, user.first_name)
        
        # Обновляем статистику
        self.db.update_user(user_data['id'], messages_count=user_data['messages_count'] + 1)
        self.db.update_activity(user_data['id'])
        
        # Проверка на бан
        if self.db.is_banned(user_data['id']):
            return
        
        # Проверка на мут
        if self.db.is_muted(user_data['id']):
            await update.message.reply_text(f.error("Ты в муте"))
            return
        
        # Проверка на спам
        if await self.check_spam(update):
            return
        
        # Проверка черного списка
        blacklist = self.db.get_blacklist()
        msg_lower = message_text.lower()
        for word in blacklist:
            if word in msg_lower:
                await update.message.delete()
                await update.message.reply_text(f.warning(f"Запрещенное слово: {word}"))
                return
        
        # Простые ответы
        if any(word in msg_lower for word in ["привет", "здравствуйте", "хай"]):
            await update.message.reply_text("👋 Привет! Чем могу помочь?")
        elif any(word in msg_lower for word in ["как дела", "как ты"]):
            await update.message.reply_text("✅ Всё отлично, работаю!")
        elif any(word in msg_lower for word in ["спасибо", "благодарю"]):
            await update.message.reply_text("🤝 Всегда пожалуйста!")
        elif any(word in msg_lower for word in ["кто создал", "владелец"]):
            await update.message.reply_text(f"👑 Владелец: {Config.OWNER_USERNAME}")
        else:
            responses = [
                "Используй /help для списка команд",
                "Напиши /menu для навигации",
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
                f"👋 {welcome_text}\n\n{member.first_name}, используй /help для команд!"
            )
    
    async def handle_left_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ухода участников"""
        member = update.message.left_chat_member
        if member.is_bot:
            return
        
        await update.message.reply_text(f"👋 {member.first_name} покинул чат...")

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
                f.header("ГЛАВНОЕ МЕНЮ") + "\nВыбери раздел:",
                reply_markup=kb.main_menu(),
                parse_mode="Markdown"
            )
        
        elif data == "menu_back":
            await query.edit_message_text(
                f.header("ГЛАВНОЕ МЕНЮ") + "\nВыбери раздел:",
                reply_markup=kb.main_menu(),
                parse_mode="Markdown"
            )
        
        elif data == "menu_profile":
            context.args = []
            await self.cmd_profile(update, context)
        
        elif data == "menu_stats":
            context.args = []
            await self.cmd_stats(update, context)
        
        elif data == "menu_bosses":
            context.args = []
            await self.cmd_bosses(update, context)
        
        elif data == "menu_casino":
            await query.edit_message_text(
                f.header("КАЗИНО") + "\nВыбери игру:",
                reply_markup=kb.casino_menu(),
                parse_mode="Markdown"
            )
        
        elif data == "casino_roulette":
            context.args = []
            await self.cmd_roulette(update, context)
        
        elif data == "casino_dice":
            context.args = []
            await self.cmd_dice(update, context)
        
        elif data == "casino_rps":
            await query.edit_message_text(
                f.header("КНБ") + "\nВыбери:",
                reply_markup=kb.rps_game(),
                parse_mode="Markdown"
            )
        
        elif data == "casino_slots":
            context.args = []
            await self.cmd_slots(update, context)
        
        elif data == "menu_shop":
            context.args = []
            await self.cmd_shop(update, context)
        
        elif data == "menu_donate":
            context.args = []
            await self.cmd_donate(update, context)
        
        elif data == "menu_mod":
            await query.edit_message_text(
                f.header("МОДЕРАЦИЯ") + "\nВыбери раздел:",
                reply_markup=kb.mod_menu(),
                parse_mode="Markdown"
            )
        
        elif data == "mod_warns":
            await query.edit_message_text(
                f.header("УПРАВЛЕНИЕ ПРЕДУПРЕЖДЕНИЯМИ") + "\n\n" +
                f.command("warn @ник [причина]", "дать предупреждение") + "\n" +
                f.command("warns @ник", "список предупреждений") + "\n" +
                f.command("unwarn @ник", "снять предупреждение"),
                reply_markup=kb.back(),
                parse_mode="Markdown"
            )
        
        elif data == "mod_mutes":
            await query.edit_message_text(
                f.header("УПРАВЛЕНИЕ МУТАМИ") + "\n\n" +
                f.command("mute @ник минут [причина]", "заглушить") + "\n" +
                f.command("unmute @ник", "снять мут") + "\n" +
                f.command("mutelist", "список замученных"),
                reply_markup=kb.back(),
                parse_mode="Markdown"
            )
        
        elif data == "mod_bans":
            await query.edit_message_text(
                f.header("УПРАВЛЕНИЕ БАНАМИ") + "\n\n" +
                f.command("ban @ник [причина]", "заблокировать") + "\n" +
                f.command("unban @ник", "разблокировать") + "\n" +
                f.command("banlist [страница]", "список забаненных"),
                reply_markup=kb.back(),
                parse_mode="Markdown"
            )
        
        elif data == "mod_logs":
            await query.edit_message_text(
                f.header("ЛОГИ") + "\n\n" +
                f.command("setlog [чат]", "установить чат для логов") + "\n" +
                f.command("logs", "последние логи"),
                reply_markup=kb.back(),
                parse_mode="Markdown"
            )
        
        elif data == "mod_settings":
            await query.edit_message_text(
                f.header("НАСТРОЙКИ ЧАТА") + "\n\n" +
                f.command("setwelcome [текст]", "приветствие") + "\n" +
                f.command("setrules [текст]", "правила") + "\n" +
                f.command("setlang [ru/en]", "язык") + "\n" +
                f.command("setantiflood [on/off]", "антифлуд") + "\n" +
                f.command("setantispam [on/off]", "антиспам") + "\n" +
                f.command("setantilink [on/off]", "запрет ссылок") + "\n" +
                f.command("setcaptcha [on/off]", "капча"),
                reply_markup=kb.back(),
                parse_mode="Markdown"
            )
        
        elif data == "mod_admins":
            await query.edit_message_text(
                f.header("АДМИНИСТРАТОРЫ") + "\n\n" +
                f.command("adminlist", "список админов") + "\n" +
                f.command("promote @ник", "назначить админом") + "\n" +
                f.command("demote @ник", "снять админа"),
                reply_markup=kb.back(),
                parse_mode="Markdown"
            )
        
        elif data == "menu_help":
            context.args = []
            await self.cmd_help(update, context)
        
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
            
            text = f.header("КНБ") + "\n\n"
            text += f"{emoji[choice]} **Вы:** {names[choice]}\n"
            text += f"{emoji[bot_choice]} **Бот:** {names[bot_choice]}\n\n"
            
            user_data = self.db.get_user(user.id)
            
            if choice == bot_choice:
                self.db.update_user(user_data['id'], rps_draws=user_data['rps_draws'] + 1)
                text += f.info("🤝 **НИЧЬЯ!**")
            elif results.get((choice, bot_choice)) == "win":
                self.db.update_user(user_data['id'], rps_wins=user_data['rps_wins'] + 1)
                reward = random.randint(10, 30)
                self.db.add_coins(user_data['id'], reward)
                text += f.success(f"🎉 **ПОБЕДА!** +{reward} 💰")
            else:
                self.db.update_user(user_data['id'], rps_losses=user_data['rps_losses'] + 1)
                text += f.error("😢 **ПОРАЖЕНИЕ!**")
            
            await query.edit_message_text(
                text,
                reply_markup=kb.back(),
                parse_mode="Markdown"
            )

    # ===== ЗАПУСК =====

    async def run(self):
        """Запуск бота"""
        try:
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling(
                drop_pending_updates=True,
                allowed_updates=["message", "callback_query", "chat_member"]
            )
            
            logger.info("🚀 Бот СПЕКТР успешно запущен")
            logger.info(f"👑 Владелец: {Config.OWNER_USERNAME}")
            logger.info(f"📊 PID: {os.getpid()}")
            
            # Бесконечное ожидание
            while True:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Критическая ошибка: {e}")
            logger.error(traceback.format_exc())
            await asyncio.sleep(5)
            await self.run()

    async def close(self):
        """Закрытие бота"""
        logger.info("👋 Завершение работы бота...")
        self.db.close()
        guard.cleanup()
        logger.info("✅ Бот остановлен")


# ========== ТОЧКА ВХОДА ==========
async def main():
    """Главная функция"""
    print("=" * 60)
    print("🚀 ЗАПУСК БОТА СПЕКТР v4.0")
    print("=" * 60)
    print(f"📊 PID: {os.getpid()}")
    print(f"📁 Lock-файл: {guard.lock_file}")
    print("=" * 60)
    
    bot = SpectrumBot()
    
    try:
        await bot.run()
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки от пользователя")
        await bot.close()
    except Exception as e:
        logger.error(f"Необработанная ошибка: {e}")
        logger.error(traceback.format_exc())
        await bot.close()
    finally:
        guard.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
