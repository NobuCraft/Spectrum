#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
СПЕКТР - SPECTRUM BOT
Официальный игровой бот с классическим оформлением
Версия 2.0
"""

import asyncio
import logging
import random
import sqlite3
import datetime
from typing import Optional, Dict, Any, List, Tuple, Union
import json
import os
import sys
import signal
import time
import hashlib
from collections import defaultdict, deque
from contextlib import contextmanager
import traceback

import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from telegram.error import TelegramError, Conflict

# ========== ЗАЩИТА ОТ МНОЖЕСТВЕННЫХ ЭКЗЕМПЛЯРОВ ==========
LOCK_FILE = None
TOKEN_HASH = hashlib.md5("8326390250:AAG1nTYdy07AuKsYXS3yvDehfU2JuR0RqGo".encode()).hexdigest()[:8]

def setup_signal_handlers():
    """Настройка обработчиков сигналов для корректного завершения"""
    def signal_handler(signum, frame):
        logging.info(f"Получен сигнал {signum}, завершаем работу...")
        cleanup_lock()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

def cleanup_lock():
    """Удаление lock-файла при завершении"""
    global LOCK_FILE
    if LOCK_FILE and os.path.exists(LOCK_FILE):
        try:
            os.remove(LOCK_FILE)
            logging.info(f"Lock-файл {LOCK_FILE} удален")
        except:
            pass

def ensure_single_instance():
    """Гарантирует запуск только одного экземпляра бота"""
    global LOCK_FILE
    lock_dir = "/tmp/spectrum_bot_locks"
    os.makedirs(lock_dir, exist_ok=True)
    
    LOCK_FILE = os.path.join(lock_dir, f"bot_{TOKEN_HASH}.lock")
    
    # Проверяем существующий lock-файл
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, 'r') as f:
                old_pid = int(f.read().strip())
            
            # Проверяем, жив ли процесс
            try:
                os.kill(old_pid, 0)
                # Процесс жив - пытаемся его завершить
                logging.warning(f"Найден работающий процесс {old_pid}, пытаемся остановить...")
                os.kill(old_pid, signal.SIGTERM)
                time.sleep(2)
                
                # Проверяем снова
                try:
                    os.kill(old_pid, 0)
                    # Процесс всё ещё жив - используем SIGKILL
                    logging.warning(f"Процесс {old_pid} не отвечает, принудительное завершение...")
                    os.kill(old_pid, signal.SIGKILL)
                    time.sleep(1)
                except OSError:
                    pass  # Процесс успешно завершен
                    
            except OSError:
                # Процесс не существует, можно удалять старый lock
                pass
                
        except Exception as e:
            logging.error(f"Ошибка при проверке lock-файла: {e}")
    
    # Создаем новый lock-файл
    try:
        with open(LOCK_FILE, 'w') as f:
            f.write(str(os.getpid()))
        logging.info(f"Lock-файл создан: {LOCK_FILE} (PID: {os.getpid()})")
    except Exception as e:
        logging.error(f"Не удалось создать lock-файл: {e}")
        sys.exit(1)

# Запускаем защиту при импорте
ensure_single_instance()
setup_signal_handlers()

# ========== НАСТРОЙКА ЛОГИРОВАНИЯ ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler(f'spectrum_bot_{TOKEN_HASH}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ========== КОНФИГУРАЦИЯ ==========
class Config:
    """Класс для хранения конфигурации"""
    TELEGRAM_TOKEN = "8326390250:AAG1nTYdy07AuKsYXS3yvDehfU2JuR0RqGo"
    GEMINI_API_KEY = "AIzaSyBPT4JUIevH0UiwXVY9eQjrY_pTPLeLbNE"
    DEEPSEEK_API_KEY = "sk-4c18a0f28fce421482cbcedcc33cb18d"
    OWNER_ID = 1732658530
    OWNER_USERNAME = "@NobuCraft"
    
    # Настройки спам-фильтра
    SPAM_LIMIT = 5
    SPAM_WINDOW = 3
    SPAM_MUTE_TIME = 120
    
    # Цены на привилегии
    VIP_PRICE = 5000
    PREMIUM_PRICE = 15000
    VIP_DAYS = 30
    PREMIUM_DAYS = 30
    
    # Лимиты
    MAX_NICK_LENGTH = 30
    MAX_TITLE_LENGTH = 30
    MAX_MOTTO_LENGTH = 100
    MAX_MESSAGE_LENGTH = 4096
    
    # Временные интервалы (в секундах)
    DAILY_COOLDOWN = 86400  # 24 часа
    WEEKLY_COOLDOWN = 604800  # 7 дней
    FREE_ENERGY_COOLDOWN = 3600  # 1 час

# ========== ФОРМАТТЕР В СТИЛЕ IRIS ==========
class SpectrumFormatter:
    """Классическое оформление в стиле iris_cm_bot"""
    
    # Символы для рамок
    BOX_TOP = "╔════════════════════════════════════════╗"
    BOX_MID = "╟────────────────────────────────────────╢"
    BOX_BOT = "╚════════════════════════════════════════╝"
    BOX_VERT = "║"
    
    # Разделители
    SEPARATOR = "━" * 40
    SEPARATOR_LIGHT = "┄" * 40
    
    @classmethod
    def header(cls, title: str, emoji: str = "⚜️") -> str:
        """Создает заголовок с рамкой"""
        padding = 38 - len(title) - 2
        left_pad = padding // 2
        right_pad = padding - left_pad
        return (
            f"{cls.BOX_TOP}\n"
            f"{cls.BOX_VERT}{' ' * left_pad}{emoji} {title.upper()} {emoji}{' ' * right_pad}{cls.BOX_VERT}\n"
            f"{cls.BOX_BOT}"
        )
    
    @classmethod
    def section(cls, title: str, emoji: str = "▫️") -> str:
        """Создает раздел"""
        return f"\n{emoji} **{title.upper()}**\n{cls.SEPARATOR}\n"
    
    @classmethod
    def subsection(cls, title: str) -> str:
        """Создает подраздел"""
        return f"\n┏━━ {title} ━━┓\n"
    
    @classmethod
    def command(cls, cmd: str, desc: str, usage: str = "", emoji: str = "・") -> str:
        """Форматирует команду"""
        if usage:
            return f"{emoji} `/{cmd} {usage}` — {desc}"
        return f"{emoji} `/{cmd}` — {desc}"
    
    @classmethod
    def param(cls, name: str, desc: str) -> str:
        """Форматирует параметр"""
        return f"  └ {name} — {desc}"
    
    @classmethod
    def example(cls, text: str) -> str:
        """Форматирует пример"""
        return f"  └ Пример: `{text}`"
    
    @classmethod
    def item(cls, text: str, emoji: str = "•") -> str:
        """Создает элемент списка"""
        return f"{emoji} {text}"
    
    @classmethod
    def numbered_item(cls, number: int, text: str) -> str:
        """Создает нумерованный элемент"""
        return f"{number}. {text}"
    
    @classmethod
    def stat(cls, name: str, value: Union[str, int], emoji: str = "📊") -> str:
        """Форматирует статистику"""
        return f"{emoji} **{name}:** {value}"
    
    @classmethod
    def progress(cls, current: int, total: int, length: int = 15) -> str:
        """Создает прогресс-бар"""
        filled = int((current / total) * length)
        bar = "█" * filled + "░" * (length - filled)
        return f"`{bar}` {current}/{total}"
    
    @classmethod
    def success(cls, text: str) -> str:
        """Сообщение об успехе"""
        return f"✅ **УСПЕХ:** {text}"
    
    @classmethod
    def error(cls, text: str) -> str:
        """Сообщение об ошибке"""
        return f"❌ **ОШИБКА:** {text}"
    
    @classmethod
    def warning(cls, text: str) -> str:
        """Предупреждение"""
        return f"⚠️ **ВНИМАНИЕ:** {text}"
    
    @classmethod
    def info(cls, text: str) -> str:
        """Информационное сообщение"""
        return f"ℹ️ **ИНФО:** {text}"
    
    @classmethod
    def user_link(cls, user_id: int, name: str) -> str:
        """Создает ссылку на пользователя"""
        return f"[{name}](tg://user?id={user_id})"
    
    @classmethod
    def bold(cls, text: str) -> str:
        """Жирный текст"""
        return f"**{text}**"
    
    @classmethod
    def code(cls, text: str) -> str:
        """Моноширинный текст"""
        return f"`{text}`"
    
    @classmethod
    def italic(cls, text: str) -> str:
        """Курсив"""
        return f"_{text}_"
    
    @classmethod
    def spoiler(cls, text: str) -> str:
        """Спойлер"""
        return f"||{text}||"

f = SpectrumFormatter()

# ========== УЛУЧШЕННЫЕ КЛАВИАТУРЫ ==========
class SpectrumKeyboard:
    """Класс для создания клавиатур с гарантированной работой"""
    
    @staticmethod
    def create_keyboard(buttons: List[List[Tuple[str, str]]]) -> InlineKeyboardMarkup:
        """
        Создает клавиатуру из списка кнопок
        Формат: [[(text, callback_data), ...], ...]
        """
        keyboard = []
        for row in buttons:
            keyboard_row = []
            for text, callback in row:
                keyboard_row.append(InlineKeyboardButton(text, callback_data=callback))
            keyboard.append(keyboard_row)
        return InlineKeyboardMarkup(keyboard)
    
    @classmethod
    def main_menu(cls) -> InlineKeyboardMarkup:
        """Главное меню"""
        return cls.create_keyboard([
            [("👤 ПРОФИЛЬ", "menu_profile"), ("📊 СТАТИСТИКА", "menu_stats")],
            [("⚔️ БИТВЫ", "menu_battles"), ("🎰 КАЗИНО", "menu_casino")],
            [("🛍 МАГАЗИН", "menu_shop"), ("💎 ПРИВИЛЕГИИ", "menu_donate")],
            [("⚙️ АДМИН", "menu_admin"), ("📚 ПОМОЩЬ", "menu_help")]
        ])
    
    @classmethod
    def back_button(cls, callback: str = "menu_back") -> InlineKeyboardMarkup:
        """Кнопка назад"""
        return cls.create_keyboard([
            [("🔙 НАЗАД", callback)]
        ])
    
    @classmethod
    def back_and_home(cls) -> InlineKeyboardMarkup:
        """Кнопки назад и на главную"""
        return cls.create_keyboard([
            [("🔙 НАЗАД", "menu_back"), ("🏠 ГЛАВНАЯ", "menu_main")]
        ])
    
    @classmethod
    def confirm_cancel(cls, confirm_cb: str = "confirm", cancel_cb: str = "cancel") -> InlineKeyboardMarkup:
        """Кнопки подтверждения и отмены"""
        return cls.create_keyboard([
            [("✅ ПОДТВЕРДИТЬ", confirm_cb), ("❌ ОТМЕНИТЬ", cancel_cb)]
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
        return cls.create_keyboard(buttons)
    
    @classmethod
    def profile_edit(cls) -> InlineKeyboardMarkup:
        """Кнопки редактирования профиля"""
        return cls.create_keyboard([
            [("✏️ ИЗМЕНИТЬ НИК", "edit_nick"), ("🏷 ИЗМЕНИТЬ ТИТУЛ", "edit_title")],
            [("📝 ИЗМЕНИТЬ ДЕВИЗ", "edit_motto"), ("👤 ИЗМЕНИТЬ ПОЛ", "edit_gender")],
            [("🔙 НАЗАД", "menu_back")]
        ])
    
    @classmethod
    def battle_menu(cls) -> InlineKeyboardMarkup:
        """Меню битв"""
        return cls.create_keyboard([
            [("👾 БОССЫ", "battle_bosses"), ("⚔️ PvP", "battle_pvp")],
            [("🔙 НАЗАД", "menu_back")]
        ])
    
    @classmethod
    def casino_menu(cls) -> InlineKeyboardMarkup:
        """Меню казино"""
        return cls.create_keyboard([
            [("🎰 РУЛЕТКА", "casino_roulette"), ("🎲 КОСТИ", "casino_dice")],
            [("🃏 БЛЭКДЖЕК", "casino_blackjack"), ("🎰 СЛОТЫ", "casino_slots")],
            [("✊ КАМЕНЬ-НОЖНИЦЫ-БУМАГА", "casino_rps")],
            [("🔙 НАЗАД", "menu_back")]
        ])
    
    @classmethod
    def rps_game(cls) -> InlineKeyboardMarkup:
        """Кнопки для игры в КНБ"""
        return cls.create_keyboard([
            [("🪨 КАМЕНЬ", "rps_rock"), ("✂️ НОЖНИЦЫ", "rps_scissors"), ("📄 БУМАГА", "rps_paper")],
            [("🔙 НАЗАД", "menu_back")]
        ])
    
    @classmethod
    def boss_list(cls, bosses: List[tuple]) -> InlineKeyboardMarkup:
        """Список боссов для атаки"""
        buttons = []
        for boss in bosses[:5]:  # Максимум 5 боссов на странице
            buttons.append([(f"⚔️ {boss[1]} (ур.{boss[2]})", f"boss_fight_{boss[0]}")])
        buttons.append([("🔙 НАЗАД", "menu_back")])
        return cls.create_keyboard(buttons)
    
    @classmethod
    def admin_menu(cls, is_owner: bool = False) -> InlineKeyboardMarkup:
        """Меню администратора"""
        buttons = [
            [("📋 СПИСОК ПОЛЬЗОВАТЕЛЕЙ", "admin_users")],
            [("🔇 СПИСОК МУТОВ", "admin_mutelist"), ("🔨 СПИСОК БАНОВ", "admin_banlist")],
            [("📊 СТАТИСТИКА", "admin_stats")],
            [("🔙 НАЗАД", "menu_back")]
        ]
        if is_owner:
            buttons.insert(0, [("👑 ПАНЕЛЬ ВЛАДЕЛЬЦА", "admin_owner_panel")])
        return cls.create_keyboard(buttons)
    
    @classmethod
    def number_picker(cls, prefix: str, min_val: int = 1, max_val: int = 10, current: int = 1) -> InlineKeyboardMarkup:
        """Выбор числа"""
        buttons = []
        
        # Кнопки увеличения/уменьшения
        row = []
        if current > min_val:
            row.append(("➖", f"{prefix}_dec"))
        row.append((f"{current}", "noop"))
        if current < max_val:
            row.append(("➕", f"{prefix}_inc"))
        buttons.append(row)
        
        # Кнопка подтверждения
        buttons.append([("✅ ПОДТВЕРДИТЬ", f"{prefix}_confirm")])
        buttons.append([("🔙 ОТМЕНА", "menu_back")])
        
        return cls.create_keyboard(buttons)

# Сокращенное имя для удобства
kb = SpectrumKeyboard()

# ========== БАЗА ДАННЫХ ==========
class Database:
    """Класс для работы с базой данных"""
    
    def __init__(self, db_name: str = "spectrum.db"):
        self.db_name = db_name
        self.conn = None
        self.cursor = None
        self.connect()
        self.create_tables()
        self.init_data()
        logger.info("✅ База данных инициализирована")

    def connect(self):
        """Подключение к БД с повторными попытками"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
                self.conn.row_factory = sqlite3.Row
                self.cursor = self.conn.cursor()
                # Включаем поддержку внешних ключей
                self.cursor.execute("PRAGMA foreign_keys = ON")
                return
            except sqlite3.Error as e:
                if attempt == max_retries - 1:
                    logger.error(f"Не удалось подключиться к БД: {e}")
                    raise
                time.sleep(1)

    @contextmanager
    def transaction(self):
        """Контекстный менеджер для транзакций"""
        try:
            yield self.cursor
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Ошибка транзакции: {e}")
            raise

    def create_tables(self):
        """Создание всех таблиц"""
        with self.transaction() as cur:
            # Таблица пользователей
            cur.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    language_code TEXT DEFAULT 'ru',
                    
                    -- Игровые ресурсы
                    coins INTEGER DEFAULT 1000,
                    diamonds INTEGER DEFAULT 0,
                    energy INTEGER DEFAULT 100,
                    
                    -- Прогресс
                    level INTEGER DEFAULT 1,
                    exp INTEGER DEFAULT 0,
                    
                    -- Боевые характеристики
                    health INTEGER DEFAULT 100,
                    max_health INTEGER DEFAULT 100,
                    armor INTEGER DEFAULT 0,
                    damage INTEGER DEFAULT 10,
                    crit_chance INTEGER DEFAULT 5,
                    crit_multiplier INTEGER DEFAULT 150,
                    
                    -- Статистика
                    boss_kills INTEGER DEFAULT 0,
                    pvp_wins INTEGER DEFAULT 0,
                    pvp_losses INTEGER DEFAULT 0,
                    messages_count INTEGER DEFAULT 0,
                    commands_used INTEGER DEFAULT 0,
                    
                    -- Игровые статистики
                    rps_wins INTEGER DEFAULT 0,
                    rps_losses INTEGER DEFAULT 0,
                    rps_draws INTEGER DEFAULT 0,
                    casino_wins INTEGER DEFAULT 0,
                    casino_losses INTEGER DEFAULT 0,
                    
                    -- Роли и права
                    role TEXT DEFAULT 'user',
                    
                    -- Профиль
                    nickname TEXT,
                    title TEXT DEFAULT '',
                    motto TEXT DEFAULT 'Нет девиза',
                    gender TEXT DEFAULT 'не указан',
                    city TEXT DEFAULT 'не указан',
                    birth_date TEXT,
                    reputation INTEGER DEFAULT 0,
                    
                    -- Модерация
                    warns INTEGER DEFAULT 0,
                    warns_list TEXT DEFAULT '[]',
                    mute_until TIMESTAMP,
                    banned INTEGER DEFAULT 0,
                    ban_reason TEXT,
                    ban_date TIMESTAMP,
                    ban_admin INTEGER,
                    
                    -- Привилегии
                    vip_until TIMESTAMP,
                    premium_until TIMESTAMP,
                    
                    -- Бонусы
                    daily_streak INTEGER DEFAULT 0,
                    last_daily TIMESTAMP,
                    last_weekly TIMESTAMP,
                    last_free_energy TIMESTAMP,
                    
                    -- Метаданные
                    last_seen TIMESTAMP,
                    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (ban_admin) REFERENCES users(id)
                )
            ''')
            
            # Индексы для быстрого поиска
            cur.execute('CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_users_coins ON users(coins DESC)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_users_level ON users(level DESC)')
            
            # Таблица боссов
            cur.execute('''
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
                    is_alive INTEGER DEFAULT 1,
                    respawn_time TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица для логов
            cur.execute('''
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action TEXT,
                    details TEXT,
                    ip TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            
            # Таблица для черного списка слов
            cur.execute('''
                CREATE TABLE IF NOT EXISTS blacklist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word TEXT UNIQUE,
                    added_by INTEGER,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица для достижений
            cur.execute('''
                CREATE TABLE IF NOT EXISTS achievements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    description TEXT,
                    reward_coins INTEGER,
                    reward_exp INTEGER,
                    icon TEXT
                )
            ''')
            
            # Таблица для полученных достижений
            cur.execute('''
                CREATE TABLE IF NOT EXISTS user_achievements (
                    user_id INTEGER,
                    achievement_id INTEGER,
                    earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, achievement_id),
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (achievement_id) REFERENCES achievements(id)
                )
            ''')

    def init_data(self):
        """Инициализация начальных данных"""
        with self.transaction() as cur:
            # Проверяем наличие боссов
            cur.execute("SELECT COUNT(*) FROM bosses")
            if cur.fetchone()[0] == 0:
                bosses = [
                    ("Ядовитый комар", 5, 500, 500, 15, 250, 50),
                    ("Лесной тролль", 10, 1000, 1000, 25, 500, 100),
                    ("Огненный дракон", 15, 2000, 2000, 40, 1000, 200),
                    ("Ледяной великан", 20, 3500, 3500, 60, 2000, 350),
                    ("Король демонов", 25, 5000, 5000, 85, 3500, 500),
                    ("Бог разрушения", 30, 10000, 10000, 150, 5000, 1000)
                ]
                cur.executemany(
                    "INSERT INTO bosses (name, level, health, max_health, damage, reward_coins, reward_exp) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    bosses
                )
            
            # Проверяем наличие владельца
            cur.execute("SELECT id FROM users WHERE telegram_id = ?", (Config.OWNER_ID,))
            if not cur.fetchone():
                cur.execute(
                    "INSERT INTO users (telegram_id, first_name, role) VALUES (?, ?, ?)",
                    (Config.OWNER_ID, "Owner", "owner")
                )

    def get_user(self, telegram_id: int, first_name: str = "Player") -> Dict[str, Any]:
        """Получение или создание пользователя"""
        with self.transaction() as cur:
            cur.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
            user = cur.fetchone()
            
            if not user:
                role = 'owner' if telegram_id == Config.OWNER_ID else 'user'
                cur.execute('''
                    INSERT INTO users (telegram_id, first_name, role, last_seen)
                    VALUES (?, ?, ?, ?)
                ''', (telegram_id, first_name, role, datetime.datetime.now()))
                
                cur.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
                user = cur.fetchone()
            else:
                cur.execute(
                    "UPDATE users SET last_seen = ?, first_name = ? WHERE telegram_id = ?",
                    (datetime.datetime.now(), first_name, telegram_id)
                )
            
            return dict(user) if user else {}

    def get_user_by_id(self, user_id: int) -> Dict[str, Any]:
        """Получение пользователя по ID"""
        with self.transaction() as cur:
            cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            user = cur.fetchone()
            return dict(user) if user else {}

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Получение пользователя по username"""
        if username.startswith('@'):
            username = username[1:]
        
        with self.transaction() as cur:
            cur.execute("SELECT * FROM users WHERE username = ?", (username,))
            user = cur.fetchone()
            return dict(user) if user else None

    def update_user(self, user_id: int, **kwargs) -> bool:
        """Обновление данных пользователя"""
        if not kwargs:
            return False
        
        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values())
        values.append(user_id)
        
        with self.transaction() as cur:
            cur.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
            return cur.rowcount > 0

    def add_coins(self, user_id: int, amount: int) -> int:
        """Добавление монет"""
        with self.transaction() as cur:
            cur.execute(
                "UPDATE users SET coins = coins + ? WHERE id = ? RETURNING coins",
                (amount, user_id)
            )
            result = cur.fetchone()
            return result[0] if result else 0

    def add_diamonds(self, user_id: int, amount: int) -> int:
        """Добавление алмазов"""
        with self.transaction() as cur:
            cur.execute(
                "UPDATE users SET diamonds = diamonds + ? WHERE id = ? RETURNING diamonds",
                (amount, user_id)
            )
            result = cur.fetchone()
            return result[0] if result else 0

    def add_exp(self, user_id: int, amount: int) -> Dict[str, int]:
        """Добавление опыта с проверкой уровня"""
        with self.transaction() as cur:
            cur.execute(
                "UPDATE users SET exp = exp + ? WHERE id = ? RETURNING exp, level",
                (amount, user_id)
            )
            user = cur.fetchone()
            if not user:
                return {'new_level': 0, 'leveled_up': False}
            
            exp, level = user
            exp_needed = level * 100
            
            if exp >= exp_needed:
                new_level = level + 1
                remaining_exp = exp - exp_needed
                cur.execute(
                    "UPDATE users SET level = ?, exp = ? WHERE id = ?",
                    (new_level, remaining_exp, user_id)
                )
                return {'new_level': new_level, 'leveled_up': True}
            
            return {'new_level': level, 'leveled_up': False}

    def add_energy(self, user_id: int, amount: int) -> int:
        """Добавление энергии (макс 100)"""
        with self.transaction() as cur:
            cur.execute(
                "UPDATE users SET energy = MIN(100, energy + ?) WHERE id = ? RETURNING energy",
                (amount, user_id)
            )
            result = cur.fetchone()
            return result[0] if result else 0

    def damage(self, user_id: int, amount: int) -> int:
        """Нанесение урона"""
        with self.transaction() as cur:
            cur.execute(
                "UPDATE users SET health = MAX(0, health - ?) WHERE id = ? RETURNING health",
                (amount, user_id)
            )
            result = cur.fetchone()
            return result[0] if result else 0

    def heal(self, user_id: int, amount: int) -> int:
        """Лечение"""
        with self.transaction() as cur:
            cur.execute(
                "UPDATE users SET health = MIN(max_health, health + ?) WHERE id = ? RETURNING health",
                (amount, user_id)
            )
            result = cur.fetchone()
            return result[0] if result else 0

    def get_top(self, by: str = "coins", limit: int = 10) -> List[Dict]:
        """Получение топа игроков"""
        valid_fields = ['coins', 'level', 'boss_kills', 'pvp_wins', 'reputation']
        if by not in valid_fields:
            by = 'coins'
        
        with self.transaction() as cur:
            cur.execute(f'''
                SELECT first_name, nickname, {by} as value 
                FROM users 
                WHERE {by} > 0 
                ORDER BY {by} DESC 
                LIMIT ?
            ''', (limit,))
            
            return [dict(row) for row in cur.fetchall()]

    def add_warn(self, user_id: int, admin_id: int, reason: str = "Нарушение") -> Dict:
        """Добавление предупреждения"""
        user = self.get_user_by_id(user_id)
        warns_list = json.loads(user.get('warns_list', '[]'))
        
        warn_data = {
            'id': len(warns_list) + 1,
            'admin_id': admin_id,
            'reason': reason,
            'date': datetime.datetime.now().isoformat()
        }
        
        warns_list.append(warn_data)
        
        with self.transaction() as cur:
            cur.execute(
                "UPDATE users SET warns = warns + 1, warns_list = ? WHERE id = ?",
                (json.dumps(warns_list), user_id)
            )
        
        return {
            'warn_id': warn_data['id'],
            'warns_count': len(warns_list),
            'warn_data': warn_data
        }

    def remove_last_warn(self, user_id: int) -> Optional[Dict]:
        """Удаление последнего предупреждения"""
        user = self.get_user_by_id(user_id)
        warns_list = json.loads(user.get('warns_list', '[]'))
        
        if not warns_list:
            return None
        
        removed = warns_list.pop()
        
        with self.transaction() as cur:
            cur.execute(
                "UPDATE users SET warns = ?, warns_list = ? WHERE id = ?",
                (len(warns_list), json.dumps(warns_list), user_id)
            )
        
        return removed

    def mute_user(self, user_id: int, minutes: int, admin_id: int = None, reason: str = "Нарушение") -> datetime.datetime:
        """Мут пользователя"""
        mute_until = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
        
        with self.transaction() as cur:
            cur.execute(
                "UPDATE users SET mute_until = ? WHERE id = ?",
                (mute_until, user_id)
            )
        
        return mute_until

    def is_muted(self, user_id: int) -> bool:
        """Проверка на мут"""
        with self.transaction() as cur:
            cur.execute("SELECT mute_until FROM users WHERE id = ?", (user_id,))
            result = cur.fetchone()
            
            if result and result[0]:
                mute_until = datetime.datetime.fromisoformat(result[0])
                return datetime.datetime.now() < mute_until
            return False

    def unmute_user(self, user_id: int) -> bool:
        """Снятие мута"""
        with self.transaction() as cur:
            cur.execute("UPDATE users SET mute_until = NULL WHERE id = ?", (user_id,))
            return cur.rowcount > 0

    def get_muted_users(self) -> List[Dict]:
        """Получение списка замученных"""
        with self.transaction() as cur:
            cur.execute('''
                SELECT id, first_name, username, mute_until 
                FROM users 
                WHERE mute_until IS NOT NULL AND mute_until > ?
                ORDER BY mute_until
            ''', (datetime.datetime.now(),))
            return [dict(row) for row in cur.fetchall()]

    def ban_user(self, user_id: int, admin_id: int, reason: str = "Нарушение") -> bool:
        """Бан пользователя"""
        with self.transaction() as cur:
            cur.execute('''
                UPDATE users 
                SET banned = 1, ban_reason = ?, ban_date = ?, ban_admin = ? 
                WHERE id = ?
            ''', (reason, datetime.datetime.now(), admin_id, user_id))
            return cur.rowcount > 0

    def unban_user(self, user_id: int) -> bool:
        """Разбан пользователя"""
        with self.transaction() as cur:
            cur.execute('''
                UPDATE users 
                SET banned = 0, ban_reason = NULL, ban_date = NULL, ban_admin = NULL 
                WHERE id = ?
            ''', (user_id,))
            return cur.rowcount > 0

    def is_banned(self, user_id: int) -> bool:
        """Проверка на бан"""
        with self.transaction() as cur:
            cur.execute("SELECT banned FROM users WHERE id = ?", (user_id,))
            result = cur.fetchone()
            return result and result[0] == 1

    def get_banlist(self, page: int = 1, limit: int = 10) -> Tuple[List[Dict], int]:
        """Получение списка забаненных"""
        offset = (page - 1) * limit
        
        with self.transaction() as cur:
            cur.execute("SELECT COUNT(*) FROM users WHERE banned = 1")
            total = cur.fetchone()[0]
            
            cur.execute('''
                SELECT id, first_name, username, ban_reason, ban_date, ban_admin
                FROM users 
                WHERE banned = 1 
                ORDER BY ban_date DESC 
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            
            bans = []
            for row in cur.fetchall():
                ban = dict(row)
                if ban['ban_admin']:
                    admin = self.get_user_by_id(ban['ban_admin'])
                    ban['admin_name'] = admin.get('first_name', 'Система') if admin else 'Система'
                else:
                    ban['admin_name'] = 'Система'
                bans.append(ban)
            
            return bans, total

    def is_vip(self, user_id: int) -> bool:
        """Проверка VIP статуса"""
        with self.transaction() as cur:
            cur.execute("SELECT vip_until FROM users WHERE id = ?", (user_id,))
            result = cur.fetchone()
            
            if result and result[0]:
                vip_until = datetime.datetime.fromisoformat(result[0])
                return datetime.datetime.now() < vip_until
            return False

    def is_premium(self, user_id: int) -> bool:
        """Проверка PREMIUM статуса"""
        with self.transaction() as cur:
            cur.execute("SELECT premium_until FROM users WHERE id = ?", (user_id,))
            result = cur.fetchone()
            
            if result and result[0]:
                premium_until = datetime.datetime.fromisoformat(result[0])
                return datetime.datetime.now() < premium_until
            return False

    def set_vip(self, user_id: int, days: int) -> datetime.datetime:
        """Установка VIP статуса"""
        vip_until = datetime.datetime.now() + datetime.timedelta(days=days)
        
        with self.transaction() as cur:
            cur.execute(
                "UPDATE users SET vip_until = ?, role = 'vip' WHERE id = ?",
                (vip_until, user_id)
            )
        
        return vip_until

    def set_premium(self, user_id: int, days: int) -> datetime.datetime:
        """Установка PREMIUM статуса"""
        premium_until = datetime.datetime.now() + datetime.timedelta(days=days)
        
        with self.transaction() as cur:
            cur.execute(
                "UPDATE users SET premium_until = ?, role = 'premium' WHERE id = ?",
                (premium_until, user_id)
            )
        
        return premium_until

    def get_bosses(self, alive_only: bool = True) -> List[Dict]:
        """Получение списка боссов"""
        with self.transaction() as cur:
            if alive_only:
                cur.execute("SELECT * FROM bosses WHERE is_alive = 1 ORDER BY level")
            else:
                cur.execute("SELECT * FROM bosses ORDER BY level")
            return [dict(row) for row in cur.fetchall()]

    def get_boss(self, boss_id: int) -> Optional[Dict]:
        """Получение информации о боссе"""
        with self.transaction() as cur:
            cur.execute("SELECT * FROM bosses WHERE id = ?", (boss_id,))
            boss = cur.fetchone()
            return dict(boss) if boss else None

    def damage_boss(self, boss_id: int, damage: int) -> Dict:
        """Нанесение урона боссу"""
        with self.transaction() as cur:
            cur.execute(
                "UPDATE bosses SET health = health - ? WHERE id = ? RETURNING health, is_alive",
                (damage, boss_id)
            )
            result = cur.fetchone()
            
            if result and result[0] <= 0:
                cur.execute(
                    "UPDATE bosses SET is_alive = 0 WHERE id = ?",
                    (boss_id,)
                )
                return {'killed': True, 'health': 0}
            
            return {'killed': False, 'health': result[0] if result else 0}

    def respawn_bosses(self):
        """Возрождение всех боссов"""
        with self.transaction() as cur:
            cur.execute("UPDATE bosses SET is_alive = 1, health = max_health")

    def add_daily_streak(self, user_id: int) -> int:
        """Добавление дня в стрик"""
        today = datetime.datetime.now().date()
        
        with self.transaction() as cur:
            cur.execute("SELECT last_daily, daily_streak FROM users WHERE id = ?", (user_id,))
            result = cur.fetchone()
            
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
            
            cur.execute(
                "UPDATE users SET daily_streak = ?, last_daily = ? WHERE id = ?",
                (streak, datetime.datetime.now(), user_id)
            )
            
            return streak

    def log_action(self, user_id: int, action: str, details: str = "", ip: str = ""):
        """Логирование действий"""
        with self.transaction() as cur:
            cur.execute(
                "INSERT INTO logs (user_id, action, details, ip) VALUES (?, ?, ?, ?)",
                (user_id, action, details, ip)
            )

    def close(self):
        """Закрытие соединения с БД"""
        if self.conn:
            self.conn.close()
            logger.info("Соединение с БД закрыто")

# Инициализация БД
db = Database()

# ========== AI МОДУЛИ ==========
class BaseAI:
    """Базовый класс для AI"""
    
    def __init__(self):
        self.session = None
        self.contexts = defaultdict(lambda: deque(maxlen=10))
    
    async def get_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        if self.session:
            await self.session.close()
    
    def get_fallback_response(self) -> str:
        responses = [
            "Извините, сейчас наблюдаются технические неполадки. Пожалуйста, повторите позже.",
            "Не удалось обработать запрос. Используйте /help для просмотра доступных команд.",
            "Сервис временно недоступен. Приношу извинения за неудобства.",
            "Произошла ошибка при обработке запроса. Попробуйте еще раз через несколько минут."
        ]
        return random.choice(responses)


class GeminiAI(BaseAI):
    """Класс для работы с Gemini AI"""
    
    def __init__(self, api_key: str):
        super().__init__()
        self.api_key = api_key
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        logger.info("🤖 Gemini AI инициализирован")
    
    async def get_response(self, user_id: int, message: str) -> str:
        try:
            session = await self.get_session()
            
            # Системный промпт
            system_prompt = (
                "Ты — СПЕКТР, официальный бот-помощник. "
                "Твои ответы должны быть вежливыми, официальными, но дружелюбными. "
                "Используй эмодзи умеренно. Отвечай кратко и по делу. "
                "Если вопрос не по теме, предложи использовать /help."
            )
            
            # Добавляем сообщение в контекст
            self.contexts[user_id].append({"role": "user", "parts": [{"text": message}]})
            
            # Формируем контекст для запроса
            contents = [
                {"role": "user", "parts": [{"text": system_prompt}]},
                {"role": "model", "parts": [{"text": "Понял. Буду помогать официально и вежливо."}]}
            ]
            contents.extend(list(self.contexts[user_id]))
            
            data = {
                "contents": contents,
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 300,
                    "topP": 0.95,
                    "topK": 40
                },
                "safetySettings": [
                    {
                        "category": "HARM_CATEGORY_HARASSMENT",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    }
                ]
            }
            
            async with session.post(self.api_url, json=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    try:
                        response = result["candidates"][0]["content"]["parts"][0]["text"]
                        self.contexts[user_id].append({"role": "model", "parts": [{"text": response}]})
                        return response
                    except (KeyError, IndexError) as e:
                        logger.error(f"Ошибка парсинга ответа Gemini: {e}")
                        return self.get_fallback_response()
                else:
                    error_text = await resp.text()
                    logger.error(f"Ошибка Gemini API (статус {resp.status}): {error_text}")
                    return self.get_fallback_response()
                    
        except asyncio.TimeoutError:
            logger.error("Таймаут при запросе к Gemini")
            return self.get_fallback_response()
        except Exception as e:
            logger.error(f"Неожиданная ошибка Gemini: {e}")
            return self.get_fallback_response()


class DeepSeekAI(BaseAI):
    """Класс для работы с DeepSeek AI"""
    
    def __init__(self, api_key: str):
        super().__init__()
        self.api_key = api_key
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        logger.info("🤖 DeepSeek AI инициализирован")
    
    async def get_response(self, user_id: int, message: str) -> str:
        try:
            session = await self.get_session()
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Системный промпт
            system_prompt = {
                "role": "system",
                "content": (
                    "Ты — СПЕКТР, официальный бот-помощник. "
                    "Твои ответы должны быть вежливыми, официальными, но дружелюбными. "
                    "Используй эмодзи умеренно. Отвечай кратко и по делу. "
                    "Если вопрос не по теме, предложи использовать /help."
                )
            }
            
            # Получаем историю контекста
            history = list(self.contexts[user_id])
            
            messages = [system_prompt] + history + [{"role": "user", "content": message}]
            
            data = {
                "model": "deepseek-chat",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 300,
                "top_p": 0.95,
                "frequency_penalty": 0,
                "presence_penalty": 0
            }
            
            async with session.post(self.api_url, headers=headers, json=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    try:
                        response = result["choices"][0]["message"]["content"]
                        self.contexts[user_id].append({"role": "user", "content": message})
                        self.contexts[user_id].append({"role": "assistant", "content": response})
                        return response
                    except (KeyError, IndexError) as e:
                        logger.error(f"Ошибка парсинга ответа DeepSeek: {e}")
                        return self.get_fallback_response()
                else:
                    error_text = await resp.text()
                    logger.error(f"Ошибка DeepSeek API (статус {resp.status}): {error_text}")
                    return self.get_fallback_response()
                    
        except Exception as e:
            logger.error(f"Ошибка DeepSeek: {e}")
            return self.get_fallback_response()


class AIAssistant:
    """Объединенный AI ассистент"""
    
    def __init__(self, gemini_key: str, deepseek_key: str):
        self.gemini = GeminiAI(gemini_key)
        self.deepseek = DeepSeekAI(deepseek_key)
        self.current_ai = 'gemini'  # По умолчанию используем Gemini
        logger.info("🤖 AI Assistant инициализирован")
    
    async def get_response(self, user_id: int, message: str) -> str:
        """Получение ответа от текущего AI"""
        try:
            if self.current_ai == 'gemini':
                response = await self.gemini.get_response(user_id, message)
                # Если Gemini не сработал, пробуем DeepSeek
                if response.startswith(("Извините", "Не удалось", "Сервис", "Произошла")):
                    self.current_ai = 'deepseek'
                    return await self.deepseek.get_response(user_id, message)
                return response
            else:
                response = await self.deepseek.get_response(user_id, message)
                if response.startswith(("Извините", "Не удалось", "Сервис", "Произошла")):
                    self.current_ai = 'gemini'
                    return await self.gemini.get_response(user_id, message)
                return response
        except Exception as e:
            logger.error(f"Ошибка AI Assistant: {e}")
            # Пробуем переключиться на другой AI
            if self.current_ai == 'gemini':
                self.current_ai = 'deepseek'
            else:
                self.current_ai = 'gemini'
            return "Произошла ошибка при обработке запроса. Пожалуйста, используйте команды меню."
    
    async def close(self):
        """Закрытие всех соединений"""
        await self.gemini.close()
        await self.deepseek.close()

ai = AIAssistant(Config.GEMINI_API_KEY, Config.DEEPSEEK_API_KEY)

# ========== ОСНОВНОЙ КЛАСС БОТА ==========
class SpectrumBot:
    """Основной класс бота"""
    
    def __init__(self):
        self.db = db
        self.ai = ai
        self.spam_tracker = defaultdict(list)
        self.application = Application.builder().token(Config.TELEGRAM_TOKEN).build()
        self.start_time = datetime.datetime.now()
        self.setup_handlers()
        logger.info("✅ Бот СПЕКТР инициализирован")

    def setup_handlers(self):
        """Регистрация всех обработчиков"""
        
        # Основные команды
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        self.application.add_handler(CommandHandler("menu", self.cmd_menu))
        
        # Профиль
        self.application.add_handler(CommandHandler("profile", self.cmd_profile))
        self.application.add_handler(CommandHandler("nick", self.cmd_set_nick))
        self.application.add_handler(CommandHandler("title", self.cmd_set_title))
        self.application.add_handler(CommandHandler("motto", self.cmd_set_motto))
        self.application.add_handler(CommandHandler("gender", self.cmd_set_gender))
        
        # Статистика и топы
        self.application.add_handler(CommandHandler("stats", self.cmd_stats))
        self.application.add_handler(CommandHandler("top", self.cmd_top))
        self.application.add_handler(CommandHandler("daily", self.cmd_daily))
        self.application.add_handler(CommandHandler("weekly", self.cmd_weekly))
        self.application.add_handler(CommandHandler("streak", self.cmd_streak))
        
        # Битвы
        self.application.add_handler(CommandHandler("bosses", self.cmd_bosses))
        self.application.add_handler(CommandHandler("boss", self.cmd_boss_fight))
        self.application.add_handler(CommandHandler("bossinfo", self.cmd_boss_info))
        self.application.add_handler(CommandHandler("regen", self.cmd_regen))
        
        # Казино
        self.application.add_handler(CommandHandler("casino", self.cmd_casino))
        self.application.add_handler(CommandHandler("roulette", self.cmd_roulette))
        self.application.add_handler(CommandHandler("dice", self.cmd_dice))
        self.application.add_handler(CommandHandler("rps", self.cmd_rps))
        self.application.add_handler(CommandHandler("blackjack", self.cmd_blackjack))
        self.application.add_handler(CommandHandler("slots", self.cmd_slots))
        
        # Экономика
        self.application.add_handler(CommandHandler("shop", self.cmd_shop))
        self.application.add_handler(CommandHandler("buy", self.cmd_buy))
        self.application.add_handler(CommandHandler("pay", self.cmd_pay))
        self.application.add_handler(CommandHandler("donate", self.cmd_donate))
        self.application.add_handler(CommandHandler("vip", self.cmd_buy_vip))
        self.application.add_handler(CommandHandler("premium", self.cmd_buy_premium))
        
        # Модерация
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
        
        # Прочее
        self.application.add_handler(CommandHandler("weather", self.cmd_weather))
        self.application.add_handler(CommandHandler("time", self.cmd_time))
        self.application.add_handler(CommandHandler("quote", self.cmd_quote))
        self.application.add_handler(CommandHandler("id", self.cmd_id))
        self.application.add_handler(CommandHandler("ping", self.cmd_ping))
        
        # Обработчики callback-кнопок и сообщений
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, self.handle_new_members))
        self.application.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, self.handle_left_member))
        
        # Обработчик ошибок
        self.application.add_error_handler(self.error_handler)
        
        logger.info("✅ Все обработчики зарегистрированы")

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
        
        user_level = role_hierarchy.index(user_role)
        required_level = role_hierarchy.index(required_role)
        return user_level >= required_level

    async def check_spam(self, update: Update) -> bool:
        """Проверка на спам"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        # Премиум и выше не проверяются
        if self.has_permission(user_data, 'premium'):
            return False
        
        current_time = time.time()
        user_id = user.id
        
        # Очищаем старые записи
        self.spam_tracker[user_id] = [
            t for t in self.spam_tracker[user_id] 
            if current_time - t < Config.SPAM_WINDOW
        ]
        
        # Добавляем текущее сообщение
        self.spam_tracker[user_id].append(current_time)
        
        # Проверяем лимит
        if len(self.spam_tracker[user_id]) > Config.SPAM_LIMIT:
            self.db.mute_user(
                user_data['id'], 
                Config.SPAM_MUTE_TIME, 
                0, 
                "Автоматический спам-фильтр"
            )
            await update.message.reply_text(
                f.error(f"Обнаружен спам. Вы замучены на {Config.SPAM_MUTE_TIME} минут.")
            )
            self.spam_tracker[user_id] = []
            return True
        
        return False

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ошибок"""
        logger.error(f"Ошибка: {context.error}")
        
        try:
            if update and update.effective_message:
                await update.effective_message.reply_text(
                    f.error("Произошла внутренняя ошибка. Администрация уже уведомлена.")
                )
        except:
            pass

    # ========== ОСНОВНЫЕ КОМАНДЫ ==========
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        user = update.effective_user
        user_data = self.db.get_user(user.id, user.first_name)
        
        text = (
            f"{f.header('ДОБРО ПОЖАЛОВАТЬ', '⚜️')}\n\n"
            f"👋 **Привет, {user.first_name}!**\n"
            f"Я — **СПЕКТР**, твой официальный игровой помощник.\n\n"
            f"{f.section('ТВОЙ ПРОФИЛЬ')}\n"
            f"{f.item(f'{self.get_role_emoji(user_data[\"role\"])} Роль: {user_data[\"role\"]}')}\n"
            f"{f.item(f'💰 Монеты: {user_data[\"coins\"]}')}\n"
            f"{f.item(f'📊 Уровень: {user_data[\"level\"]}')}\n"
            f"{f.item(f'⚡ Энергия: {user_data[\"energy\"]}/100')}\n\n"
            f"{f.section('БЫСТРЫЙ СТАРТ')}\n"
            f"{f.command('profile', 'твой профиль')}\n"
            f"{f.command('bosses', 'битва с боссами')}\n"
            f"{f.command('daily', 'ежедневный бонус')}\n"
            f"{f.command('help', 'все команды')}\n\n"
            f"👑 **Владелец:** {Config.OWNER_USERNAME}"
        )
        
        await update.message.reply_text(
            text,
            reply_markup=kb.main_menu(),
            parse_mode='Markdown'
        )
        
        self.db.log_action(user_data['id'], 'start', f"Запуск бота")

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help"""
        text = (
            f"{f.header('СПРАВКА', '📚')}\n\n"
            f"{f.section('ОСНОВНЫЕ КОМАНДЫ')}\n"
            f"{f.command('start', 'начать работу')}\n"
            f"{f.command('menu', 'главное меню')}\n"
            f"{f.command('profile', 'твой профиль')}\n"
            f"{f.command('stats', 'твоя статистика')}\n\n"
            f"{f.section('ПРОФИЛЬ')}\n"
            f"{f.command('nick [ник]', 'установить ник')}\n"
            f"{f.command('title [титул]', 'установить титул')}\n"
            f"{f.command('motto [девиз]', 'установить девиз')}\n"
            f"{f.command('gender [м/ж/др]', 'установить пол')}\n\n"
            f"{f.section('ИГРЫ')}\n"
            f"{f.command('bosses', 'битва с боссами')}\n"
            f"{f.command('casino', 'казино')}\n"
            f"{f.command('rps', 'камень-ножницы-бумага')}\n\n"
            f"{f.section('ЭКОНОМИКА')}\n"
            f"{f.command('daily', 'ежедневный бонус')}\n"
            f"{f.command('weekly', 'недельный бонус')}\n"
            f"{f.command('shop', 'магазин')}\n"
            f"{f.command('pay @ник сумма', 'перевести монеты')}\n"
            f"{f.command('donate', 'привилегии')}\n\n"
            f"{f.section('МОДЕРАЦИЯ')}\n"
            f"{f.command('warn @ник [причина]', 'предупреждение')}\n"
            f"{f.command('mute @ник минут [причина]', 'заглушить')}\n"
            f"{f.command('ban @ник [причина]', 'заблокировать')}\n"
            f"{f.command('banlist', 'список забаненных')}\n\n"
            f"👑 **Владелец:** {Config.OWNER_USERNAME}"
        )
        
        await update.message.reply_text(
            text,
            reply_markup=kb.back_button(),
            parse_mode='Markdown'
        )

    async def cmd_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /menu"""
        await update.message.reply_text(
            f"{f.header('ГЛАВНОЕ МЕНЮ', '🎮')}\n\nВыберите раздел:",
            reply_markup=kb.main_menu(),
            parse_mode='Markdown'
        )

    # ========== ПРОФИЛЬ ==========

    async def cmd_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /profile"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        # Прогресс уровня
        current_exp = user_data.get('exp', 0)
        current_level = user_data.get('level', 1)
        exp_needed = current_level * 100
        exp_progress = f.progress(current_exp, exp_needed)
        
        # Статусы
        vip_status = "✅ VIP" if self.db.is_vip(user_data['id']) else "❌ Нет"
        premium_status = "✅ PREMIUM" if self.db.is_premium(user_data['id']) else "❌ Нет"
        
        # Предупреждения
        warns = user_data.get('warns', 0)
        warns_display = "🔴" * warns + "⚪" * (3 - warns)
        
        # Имя для отображения
        display_name = user_data.get('nickname') or user.first_name
        title = user_data.get('title', '')
        motto = user_data.get('motto', 'Нет девиза')
        
        text = (
            f"{f.header('ПРОФИЛЬ ИГРОКА', '👤')}\n\n"
            f"**{display_name}** {title}\n"
            f"_{motto}_\n\n"
            f"{f.section('ХАРАКТЕРИСТИКИ')}\n"
            f"{f.stat('Уровень', current_level)}\n"
            f"{f.stat('Опыт', exp_progress)}\n"
            f"{f.stat('Монеты', f'{user_data[\"coins\"]} 💰')}\n"
            f"{f.stat('Алмазы', f'{user_data[\"diamonds\"]} 💎')}\n"
            f"{f.stat('Энергия', f'{user_data[\"energy\"]}/100 ⚡')}\n\n"
            f"{f.section('БОЕВЫЕ')}\n"
            f"{f.stat('❤️ Здоровье', f'{user_data[\"health\"]}/{user_data[\"max_health\"]}')}\n"
            f"{f.stat('⚔️ Урон', user_data['damage'])}\n"
            f"{f.stat('🛡 Броня', user_data['armor'])}\n"
            f"{f.stat('🎯 Крит', f'{user_data[\"crit_chance\"]}% (x{user_data[\"crit_multiplier\"]//100})')}\n"
            f"{f.stat('👾 Боссов убито', user_data['boss_kills'])}\n\n"
            f"{f.section('СТАТУС')}\n"
            f"{f.item(vip_status)}\n"
            f"{f.item(premium_status)}\n"
            f"{f.item(f'Предупреждения: {warns_display}')}\n"
            f"{f.item(f'⭐ Репутация: {user_data[\"reputation\"]}')}\n\n"
            f"{f.section('О СЕБЕ')}\n"
            f"{f.item(f'Пол: {user_data[\"gender\"]}')}\n"
            f"{f.item(f'Город: {user_data[\"city\"]}')}\n"
            f"{f.item(f'ID: {f.code(str(user.id))}')}"
        )
        
        await update.message.reply_text(
            text,
            reply_markup=kb.profile_edit(),
            parse_mode='Markdown'
        )

    async def cmd_set_nick(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установка ника"""
        if not context.args:
            await update.message.reply_text(
                f"{f.header('УСТАНОВКА НИКА', '✏️')}\n\n"
                f"{f.command('nick [ник]', 'установить ник')}\n"
                f"{f.example('nick Spectr')}",
                parse_mode='Markdown'
            )
            return
        
        nick = " ".join(context.args)
        if len(nick) > Config.MAX_NICK_LENGTH:
            await update.message.reply_text(
                f.error(f"Ник слишком длинный. Максимум {Config.MAX_NICK_LENGTH} символов.")
            )
            return
        
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        self.db.update_user(user_data['id'], nickname=nick)
        
        await update.message.reply_text(
            f.success(f"Ник успешно установлен: **{nick}**"),
            parse_mode='Markdown'
        )

    async def cmd_set_title(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установка титула"""
        if not context.args:
            await update.message.reply_text(
                f"{f.header('УСТАНОВКА ТИТУЛА', '🏷')}\n\n"
                f"{f.command('title [титул]', 'установить титул')}\n"
                f"{f.example('title Легенда')}",
                parse_mode='Markdown'
            )
            return
        
        title = " ".join(context.args)
        if len(title) > Config.MAX_TITLE_LENGTH:
            await update.message.reply_text(
                f.error(f"Титул слишком длинный. Максимум {Config.MAX_TITLE_LENGTH} символов.")
            )
            return
        
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        self.db.update_user(user_data['id'], title=title)
        
        await update.message.reply_text(
            f.success(f"Титул успешно установлен: **{title}**"),
            parse_mode='Markdown'
        )

    async def cmd_set_motto(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установка девиза"""
        if not context.args:
            await update.message.reply_text(
                f"{f.header('УСТАНОВКА ДЕВИЗА', '📝')}\n\n"
                f"{f.command('motto [девиз]', 'установить девиз')}\n"
                f"{f.example('motto Carpe diem')}",
                parse_mode='Markdown'
            )
            return
        
        motto = " ".join(context.args)
        if len(motto) > Config.MAX_MOTTO_LENGTH:
            await update.message.reply_text(
                f.error(f"Девиз слишком длинный. Максимум {Config.MAX_MOTTO_LENGTH} символов.")
            )
            return
        
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        self.db.update_user(user_data['id'], motto=motto)
        
        await update.message.reply_text(
            f.success(f"Девиз успешно установлен: _{motto}_"),
            parse_mode='Markdown'
        )

    async def cmd_set_gender(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установка пола"""
        if not context.args or context.args[0].lower() not in ['м', 'ж', 'др']:
            await update.message.reply_text(
                f"{f.header('УСТАНОВКА ПОЛА', '👤')}\n\n"
                f"{f.command('gender [м/ж/др]', 'установить пол')}\n"
                f"{f.example('gender м')}",
                parse_mode='Markdown'
            )
            return
        
        gender_map = {'м': 'мужской', 'ж': 'женский', 'др': 'другой'}
        gender = gender_map[context.args[0].lower()]
        
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        self.db.update_user(user_data['id'], gender=gender)
        
        await update.message.reply_text(
            f.success(f"Пол успешно установлен: **{gender}**"),
            parse_mode='Markdown'
        )

    # ========== СТАТИСТИКА ==========

    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /stats - статистика игрока"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        text = (
            f"{f.header('СТАТИСТИКА ИГРОКА', '📊')}\n\n"
            f"{f.section('ОБЩАЯ')}\n"
            f"{f.stat('Сообщений', user_data['messages_count'])}\n"
            f"{f.stat('Команд использовано', user_data['commands_used'])}\n"
            f"{f.stat('Игр сыграно', user_data['rps_wins'] + user_data['rps_losses'] + user_data['rps_draws'] + user_data['casino_wins'] + user_data['casino_losses'])}\n\n"
            f"{f.section('КНБ')}\n"
            f"{f.stat('Побед', user_data['rps_wins'])}\n"
            f"{f.stat('Поражений', user_data['rps_losses'])}\n"
            f"{f.stat('Ничьих', user_data['rps_draws'])}\n\n"
            f"{f.section('КАЗИНО')}\n"
            f"{f.stat('Побед', user_data['casino_wins'])}\n"
            f"{f.stat('Поражений', user_data['casino_losses'])}\n"
            f"{f.stat('Профит', user_data['casino_wins'] * 10 - user_data['casino_losses'] * 10)} 💰"
        )
        
        await update.message.reply_text(
            text,
            reply_markup=kb.back_button(),
            parse_mode='Markdown'
        )

    async def cmd_top(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /top - топ игроков"""
        top_coins = self.db.get_top('coins', 10)
        top_level = self.db.get_top('level', 10)
        top_boss = self.db.get_top('boss_kills', 10)
        
        text = f"{f.header('ТОП ИГРОКОВ', '🏆')}\n\n"
        
        text += f"{f.section('ПО МОНЕТАМ', '💰')}\n"
        for i, player in enumerate(top_coins, 1):
            name = player.get('nickname') or player['first_name']
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} **{name}** — {player['value']} 💰\n"
        
        text += f"\n{f.section('ПО УРОВНЮ', '📊')}\n"
        for i, player in enumerate(top_level, 1):
            name = player.get('nickname') or player['first_name']
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} **{name}** — {player['value']} ур.\n"
        
        text += f"\n{f.section('ПО УБИЙСТВУ БОССОВ', '👾')}\n"
        for i, player in enumerate(top_boss, 1):
            name = player.get('nickname') or player['first_name']
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} **{name}** — {player['value']} боссов\n"
        
        await update.message.reply_text(
            text,
            reply_markup=kb.back_button(),
            parse_mode='Markdown'
        )

    async def cmd_daily(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /daily - ежедневный бонус"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        # Проверяем, получал ли уже сегодня
        if user_data.get('last_daily'):
            last = datetime.datetime.fromisoformat(user_data['last_daily'])
            if (datetime.datetime.now() - last).seconds < Config.DAILY_COOLDOWN:
                remaining = Config.DAILY_COOLDOWN - (datetime.datetime.now() - last).seconds
                hours = remaining // 3600
                minutes = (remaining % 3600) // 60
                await update.message.reply_text(
                    f.warning(f"Вы уже получали бонус сегодня. Следующий через {hours}ч {minutes}м.")
                )
                return
        
        # Получаем стрик
        streak = self.db.add_daily_streak(user_data['id'])
        
        # Базовые награды
        coins = random.randint(100, 300)
        exp = random.randint(20, 60)
        energy = 20
        
        # Множитель от стрика
        streak_multiplier = 1 + min(streak, 30) * 0.05
        
        # Множитель от привилегий
        vip_mult = 1.5 if self.db.is_vip(user_data['id']) else 1
        prem_mult = 2 if self.db.is_premium(user_data['id']) else 1
        total_mult = streak_multiplier * vip_mult * prem_mult
        
        coins = int(coins * total_mult)
        exp = int(exp * total_mult)
        
        # Начисляем награды
        self.db.add_coins(user_data['id'], coins)
        self.db.add_exp(user_data['id'], exp)
        self.db.add_energy(user_data['id'], energy)
        
        text = (
            f"{f.header('ЕЖЕДНЕВНЫЙ БОНУС', '🎁')}\n\n"
            f"{f.item(f'🔥 Стрик: {streak} дней')}\n"
            f"{f.item(f'💰 Монеты: +{coins}')}\n"
            f"{f.item(f'✨ Опыт: +{exp}')}\n"
            f"{f.item(f'⚡ Энергия: +{energy}')}\n\n"
            f"{f.info('Заходите завтра за новым бонусом!')}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
        self.db.log_action(user_data['id'], 'daily', f"Получен бонус: {coins}💰, {exp}✨")

    async def cmd_weekly(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /weekly - недельный бонус"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data.get('last_weekly'):
            last = datetime.datetime.fromisoformat(user_data['last_weekly'])
            if (datetime.datetime.now() - last).seconds < Config.WEEKLY_COOLDOWN:
                remaining = Config.WEEKLY_COOLDOWN - (datetime.datetime.now() - last).seconds
                days = remaining // 86400
                await update.message.reply_text(
                    f.warning(f"Недельный бонус можно получить через {days} дней.")
                )
                return
        
        # Базовые награды
        coins = random.randint(1000, 3000)
        diamonds = random.randint(10, 30)
        exp = random.randint(200, 500)
        
        # Множитель от привилегий
        vip_mult = 1.5 if self.db.is_vip(user_data['id']) else 1
        prem_mult = 2 if self.db.is_premium(user_data['id']) else 1
        total_mult = vip_mult * prem_mult
        
        coins = int(coins * total_mult)
        diamonds = int(diamonds * total_mult)
        exp = int(exp * total_mult)
        
        # Начисляем награды
        self.db.add_coins(user_data['id'], coins)
        self.db.add_diamonds(user_data['id'], diamonds)
        self.db.add_exp(user_data['id'], exp)
        
        # Обновляем время получения
        self.db.update_user(user_data['id'], last_weekly=datetime.datetime.now())
        
        text = (
            f"{f.header('НЕДЕЛЬНЫЙ БОНУС', '📅')}\n\n"
            f"{f.item(f'💰 Монеты: +{coins}')}\n"
            f"{f.item(f'💎 Алмазы: +{diamonds}')}\n"
            f"{f.item(f'✨ Опыт: +{exp}')}\n\n"
            f"{f.info('Возвращайтесь через неделю!')}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')

    async def cmd_streak(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /streak - информация о стрике"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        streak = user_data.get('daily_streak', 0)
        last_daily = user_data.get('last_daily')
        
        if last_daily:
            last = datetime.datetime.fromisoformat(last_daily)
            days_missed = (datetime.datetime.now() - last).days
            next_bonus = last + datetime.timedelta(days=1)
            if next_bonus > datetime.datetime.now():
                time_until = next_bonus - datetime.datetime.now()
                hours = time_until.seconds // 3600
                minutes = (time_until.seconds % 3600) // 60
                next_text = f"через {hours}ч {minutes}м"
            else:
                next_text = "доступен сейчас"
        else:
            days_missed = 0
            next_text = "доступен сейчас"
        
        text = (
            f"{f.header('ТЕКУЩИЙ СТРИК', '🔥')}\n\n"
            f"{f.item(f'Дней подряд: {streak}')}\n"
            f"{f.item(f'Пропущено дней: {days_missed}')}\n"
            f"{f.item(f'Следующий бонус: {next_text}')}\n\n"
            f"{f.info('Множитель бонуса: x' + str(1 + min(streak, 30) * 0.05))}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')

    # ========== БИТВЫ ==========

    async def cmd_bosses(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /bosses - список боссов"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        bosses = self.db.get_bosses(alive_only=True)
        
        if not bosses:
            self.db.respawn_bosses()
            bosses = self.db.get_bosses(alive_only=True)
        
        text = f"{f.header('АРЕНА БОССОВ', '👾')}\n\n"
        
        if bosses:
            boss = bosses[0]
            health_bar = f.progress(boss['health'], boss['max_health'], 20)
            
            text += (
                f"**ТЕКУЩИЙ БОСС**\n"
                f"└ {boss['name']} (ур. {boss['level']})\n"
                f"└ ❤️ {health_bar}\n"
                f"└ ⚔️ Урон: {boss['damage']}\n"
                f"└ 💰 Награда: {boss['reward_coins']}\n"
                f"└ ✨ Опыт: {boss['reward_exp']}\n\n"
            )
            
            if len(bosses) > 1:
                text += f"{f.section('ОЧЕРЕДЬ')}\n"
                for i, b in enumerate(bosses[1:], 2):
                    text += f"{i}. {b['name']} — ❤️ {b['health']}/{b['max_health']}\n"
        
        text += (
            f"\n{f.section('ТВОИ ПОКАЗАТЕЛИ')}\n"
            f"{f.stat('❤️ Здоровье', f'{user_data[\"health\"]}/{user_data[\"max_health\"]}')}\n"
            f"{f.stat('⚡ Энергия', f'{user_data[\"energy\"]}/100')}\n"
            f"{f.stat('⚔️ Урон', user_data['damage'])}\n"
            f"{f.stat('👾 Убито боссов', user_data['boss_kills'])}\n\n"
            f"{f.section('КОМАНДЫ')}\n"
            f"{f.command('boss [ID]', 'атаковать босса', '1')}\n"
            f"{f.command('bossinfo [ID]', 'информация о боссе', '1')}\n"
            f"{f.command('regen', 'восстановить ❤️ и ⚡')}"
        )
        
        await update.message.reply_text(
            text,
            reply_markup=kb.boss_list(bosses),
            parse_mode='Markdown'
        )

    async def cmd_boss_fight(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /boss - битва с боссом"""
        if not context.args:
            await update.message.reply_text(f.error("Укажите ID босса: /boss 1"))
            return
        
        try:
            boss_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text(f.error("Некорректный ID босса"))
            return
        
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        boss = self.db.get_boss(boss_id)
        if not boss or not boss['is_alive']:
            await update.message.reply_text(f.error("Босс не найден или уже повержен"))
            return
        
        # Проверка энергии
        if user_data['energy'] < 10:
            await update.message.reply_text(f.error("Недостаточно энергии. Используйте /regen"))
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
        if random.randint(1, 100) <= user_data['crit_chance']:
            player_damage = int(player_damage * user_data['crit_multiplier'] / 100)
            crit_text = "💥 КРИТИЧЕСКИЙ УДАР! "
        else:
            crit_text = ""
        
        # Урон босса
        boss_damage = boss['damage'] + random.randint(-5, 5)
        player_taken = max(1, boss_damage - user_data['armor'] // 2)
        
        # Наносим урон
        result = self.db.damage_boss(boss_id, player_damage)
        self.db.damage(user_data['id'], player_taken)
        
        text = f"{f.header('БИТВА С БОССОМ', '⚔️')}\n\n"
        text += f"{f.item(f'{crit_text}Ваш урон: {player_damage}')}\n"
        text += f"{f.item(f'Урон босса: {player_taken}')}\n\n"
        
        if result['killed']:
            # Босс убит
            reward_coins = boss['reward_coins'] * (1 + user_data['level'] // 10)
            reward_exp = boss['reward_exp'] * (1 + user_data['level'] // 10)
            
            # Бонус от привилегий
            if self.db.is_vip(user_data['id']):
                reward_coins = int(reward_coins * 1.5)
                reward_exp = int(reward_exp * 1.5)
            if self.db.is_premium(user_data['id']):
                reward_coins = int(reward_coins * 2)
                reward_exp = int(reward_exp * 2)
            
            self.db.add_coins(user_data['id'], reward_coins)
            level_result = self.db.add_exp(user_data['id'], reward_exp)
            self.db.add_boss_kill(user_data['id'])
            
            text += f"{f.success('ПОБЕДА!')}\n"
            text += f"{f.item(f'💰 Монеты: +{reward_coins}')}\n"
            text += f"{f.item(f'✨ Опыт: +{reward_exp}')}\n"
            
            if level_result['leveled_up']:
                text += f"{f.success(f'УРОВЕНЬ ПОВЫШЕН! Новый уровень: {level_result["new_level"]}')}\n"
        else:
            text += f"{f.warning('Босс еще жив!')}\n"
            boss_info = self.db.get_boss(boss_id)
            text += f"❤️ Осталось: {boss_info['health']} здоровья\n"
        
        # Проверка на смерть игрока
        if user_data['health'] <= player_taken:
            self.db.heal(user_data['id'], 50)
            text += f"\n{f.info('Вы погибли и были воскрешены с 50❤️')}"
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
        self.db.log_action(user_data['id'], 'boss_fight', f"Битва с боссом {boss['name']}")

    async def cmd_boss_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /bossinfo - информация о боссе"""
        if not context.args:
            await update.message.reply_text(f.error("Укажите ID босса: /bossinfo 1"))
            return
        
        try:
            boss_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text(f.error("Некорректный ID босса"))
            return
        
        boss = self.db.get_boss(boss_id)
        if not boss:
            await update.message.reply_text(f.error("Босс не найден"))
            return
        
        status = "ЖИВ" if boss['is_alive'] else "ПОВЕРЖЕН"
        health_bar = f.progress(boss['health'], boss['max_health'], 20)
        
        text = (
            f"{f.header(f'БОСС: {boss["name"]}', '👾')}\n\n"
            f"{f.stat('Уровень', boss['level'])}\n"
            f"{f.stat('❤️ Здоровье', health_bar)}\n"
            f"{f.stat('⚔️ Урон', boss['damage'])}\n"
            f"{f.stat('💰 Награда монетами', boss['reward_coins'])}\n"
            f"{f.stat('✨ Награда опытом', boss['reward_exp'])}\n"
            f"{f.stat('📊 Статус', status)}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')

    async def cmd_regen(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /regen - восстановление"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        cost = 20
        
        if user_data['coins'] < cost:
            await update.message.reply_text(f.error(f"Недостаточно монет. Нужно {cost} 💰"))
            return
        
        self.db.add_coins(user_data['id'], -cost)
        self.db.heal(user_data['id'], 50)
        self.db.add_energy(user_data['id'], 20)
        
        await update.message.reply_text(
            f"{f.success('Регенерация завершена!')}\n"
            f"{f.item('❤️ Здоровье +50')}\n"
            f"{f.item('⚡ Энергия +20')}\n"
            f"{f.item(f'💰 Потрачено: {cost}')}",
            parse_mode='Markdown'
        )

    # ========== КАЗИНО ==========

    async def cmd_casino(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /casino - меню казино"""
        await update.message.reply_text(
            f"{f.header('КАЗИНО', '🎰')}\n\nВыберите игру:",
            reply_markup=kb.casino_menu(),
            parse_mode='Markdown'
        )

    async def cmd_roulette(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /roulette - рулетка"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        # Парсим аргументы
        bet = 10
        choice = "red"
        
        if context.args:
            try:
                bet = int(context.args[0])
                if len(context.args) > 1:
                    choice = context.args[1].lower()
            except:
                pass
        
        # Проверка ставки
        if bet > user_data['coins']:
            await update.message.reply_text(
                f.error(f"Недостаточно монет. Баланс: {user_data['coins']} 💰")
            )
            return
        
        if bet <= 0:
            await update.message.reply_text(f.error("Ставка должна быть положительной"))
            return
        
        # Определение цветов
        red_numbers = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]
        black_numbers = [2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35]
        
        # Результат
        result_num = random.randint(0, 36)
        if result_num == 0:
            result_color = "green"
        elif result_num in red_numbers:
            result_color = "red"
        else:
            result_color = "black"
        
        # Проверка выигрыша
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
        
        # Расчет и начисление
        if win:
            winnings = bet * multiplier
            self.db.add_coins(user_data['id'], winnings)
            self.db.update_user(user_data['id'], casino_wins=user_data['casino_wins'] + 1)
            result_text = f.success(f"ВЫ ВЫИГРАЛИ! +{winnings} 💰")
        else:
            self.db.add_coins(user_data['id'], -bet)
            self.db.update_user(user_data['id'], casino_losses=user_data['casino_losses'] + 1)
            result_text = f.error(f"ВЫ ПРОИГРАЛИ! -{bet} 💰")
        
        text = (
            f"{f.header('РУЛЕТКА', '🎰')}\n\n"
            f"{f.item(f'Ставка: {bet} 💰')}\n"
            f"{f.item(f'Выбрано: {choice}')}\n"
            f"{f.item(f'Выпало: {result_num} {result_color}')}\n\n"
            f"{result_text}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
        self.db.log_action(user_data['id'], 'roulette', f"Ставка {bet}, результат {result_num}")

    async def cmd_dice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /dice - игра в кости"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        # Парсим ставку
        bet = 10
        if context.args:
            try:
                bet = int(context.args[0])
            except:
                pass
        
        # Проверка ставки
        if bet > user_data['coins']:
            await update.message.reply_text(
                f.error(f"Недостаточно монет. Баланс: {user_data['coins']} 💰")
            )
            return
        
        if bet <= 0:
            await update.message.reply_text(f.error("Ставка должна быть положительной"))
            return
        
        # Бросок костей
        dice1 = random.randint(1, 6)
        dice2 = random.randint(1, 6)
        total = dice1 + dice2
        
        # Определение результата
        if total in [7, 11]:
            win = bet * 2
            result_text = f.success(f"ВЫ ВЫИГРАЛИ! +{win} 💰")
            self.db.update_user(user_data['id'], casino_wins=user_data['casino_wins'] + 1)
        elif total in [2, 3, 12]:
            win = 0
            result_text = f.error(f"ВЫ ПРОИГРАЛИ! -{bet} 💰")
            self.db.update_user(user_data['id'], casino_losses=user_data['casino_losses'] + 1)
        else:
            win = bet
            result_text = f.info(f"НИЧЬЯ! Ставка возвращена: {bet} 💰")
        
        # Начисление
        if win > 0:
            self.db.add_coins(user_data['id'], win)
        
        text = (
            f"{f.header('КОСТИ', '🎲')}\n\n"
            f"{f.item(f'Ставка: {bet} 💰')}\n"
            f"{f.item(f'Кубики: {dice1} + {dice2}')}\n"
            f"{f.item(f'Сумма: {total}')}\n\n"
            f"{result_text}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')

    async def cmd_rps(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /rps - камень-ножницы-бумага"""
        await update.message.reply_text(
            f"{f.header('КАМЕНЬ-НОЖНИЦЫ-БУМАГА', '✊')}\n\nВыберите свой ход:",
            reply_markup=kb.rps_game(),
            parse_mode='Markdown'
        )

    async def cmd_blackjack(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /blackjack - блэкджек"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        bet = 10
        if context.args:
            try:
                bet = int(context.args[0])
            except:
                pass
        
        if bet > user_data['coins']:
            await update.message.reply_text(
                f.error(f"Недостаточно монет. Баланс: {user_data['coins']} 💰")
            )
            return
        
        # Простая симуляция блэкджека
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
            self.db.add_coins(user_data['id'], win)
            self.db.update_user(user_data['id'], casino_wins=user_data['casino_wins'] + 1)
            result_text = f.success(f"ВЫ ВЫИГРАЛИ! +{win} 💰")
        elif result == "lose":
            self.db.add_coins(user_data['id'], -bet)
            self.db.update_user(user_data['id'], casino_losses=user_data['casino_losses'] + 1)
            result_text = f.error(f"ВЫ ПРОИГРАЛИ! -{bet} 💰")
        else:
            result_text = f.info(f"НИЧЬЯ! Ставка возвращена: {bet} 💰")
        
        text = (
            f"{f.header('БЛЭКДЖЕК', '🃏')}\n\n"
            f"{f.item(f'Ставка: {bet} 💰')}\n"
            f"{f.item(f'Вы: {player}')}\n"
            f"{f.item(f'Дилер: {dealer}')}\n\n"
            f"{result_text}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')

    async def cmd_slots(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /slots - игровые автоматы"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        bet = 10
        if context.args:
            try:
                bet = int(context.args[0])
            except:
                pass
        
        if bet > user_data['coins']:
            await update.message.reply_text(
                f.error(f"Недостаточно монет. Баланс: {user_data['coins']} 💰")
            )
            return
        
        # Символы для слотов
        symbols = ["🍒", "🍋", "🍊", "7️⃣", "💎", "🎰"]
        spin = [random.choice(symbols) for _ in range(3)]
        
        # Определение выигрыша
        if len(set(spin)) == 1:
            if spin[0] == "7️⃣":
                win = bet * 50
            elif spin[0] == "💎":
                win = bet * 30
            else:
                win = bet * 10
            result_text = f.success(f"ДЖЕКПОТ! +{win} 💰")
        elif len(set(spin)) == 2:
            win = bet * 2
            result_text = f.success(f"МАЛЕНЬКИЙ ВЫИГРЫШ! +{win} 💰")
        else:
            win = 0
            result_text = f.error(f"НЕ ПОВЕЗЛО! -{bet} 💰")
        
        # Начисление
        if win > 0:
            self.db.add_coins(user_data['id'], win)
            self.db.update_user(user_data['id'], casino_wins=user_data['casino_wins'] + 1)
        else:
            self.db.add_coins(user_data['id'], -bet)
            self.db.update_user(user_data['id'], casino_losses=user_data['casino_losses'] + 1)
        
        text = (
            f"{f.header('СЛОТЫ', '🎰')}\n\n"
            f"{' '.join(spin)}\n\n"
            f"{f.item(f'Ставка: {bet} 💰')}\n"
            f"{result_text}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')

    # ========== ЭКОНОМИКА ==========

    async def cmd_shop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /shop - магазин"""
        text = (
            f"{f.header('МАГАЗИН', '🛍')}\n\n"
            f"{f.section('ЗЕЛЬЯ', '💊')}\n"
            f"{f.command('buy зелье здоровья', '50 💰 (❤️+30)')}\n"
            f"{f.command('buy большое зелье', '100 💰 (❤️+70)')}\n\n"
            f"{f.section('ОРУЖИЕ', '⚔️')}\n"
            f"{f.command('buy меч', '200 💰 (⚔️+10)')}\n"
            f"{f.command('buy легендарный меч', '500 💰 (⚔️+30)')}\n\n"
            f"{f.section('БРОНЯ', '🛡')}\n"
            f"{f.command('buy щит', '150 💰 (🛡+5)')}\n"
            f"{f.command('buy доспехи', '400 💰 (🛡+15)')}\n\n"
            f"{f.section('ЭНЕРГИЯ', '⚡')}\n"
            f"{f.command('buy энергетик', '30 💰 (⚡+20)')}\n"
            f"{f.command('buy батарейка', '80 💰 (⚡+50)')}\n\n"
            f"{f.section('КРИТЫ', '💥')}\n"
            f"{f.command('buy амулет', '300 💰 (🎯+5% крита)')}\n"
            f"{f.command('buy кольцо', '600 💰 (💥x2 крит урон)')}"
        )
        
        await update.message.reply_text(
            text,
            reply_markup=kb.back_button(),
            parse_mode='Markdown'
        )

    async def cmd_buy(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /buy - покупка предметов"""
        if not context.args:
            await update.message.reply_text(f.error("Укажите предмет: /buy [название]"))
            return
        
        item = " ".join(context.args).lower()
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        # Словарь предметов
        items = {
            "зелье здоровья": {"price": 50, "heal": 30},
            "большое зелье": {"price": 100, "heal": 70},
            "меч": {"price": 200, "damage": 10},
            "легендарный меч": {"price": 500, "damage": 30},
            "щит": {"price": 150, "armor": 5},
            "доспехи": {"price": 400, "armor": 15},
            "энергетик": {"price": 30, "energy": 20},
            "батарейка": {"price": 80, "energy": 50},
            "амулет": {"price": 300, "crit_chance": 5},
            "кольцо": {"price": 600, "crit_multiplier": 200}
        }
        
        if item not in items:
            await update.message.reply_text(f.error("Такого предмета нет в магазине"))
            return
        
        item_data = items[item]
        
        if user_data['coins'] < item_data['price']:
            await update.message.reply_text(
                f.error(f"Недостаточно монет. Нужно {item_data['price']} 💰")
            )
            return
        
        # Покупка
        self.db.add_coins(user_data['id'], -item_data['price'])
        
        if 'heal' in item_data:
            new_health = self.db.heal(user_data['id'], item_data['heal'])
            await update.message.reply_text(
                f.success(f"Здоровье восстановлено +{item_data['heal']}❤️ (текущее: {new_health})")
            )
        elif 'damage' in item_data:
            new_damage = user_data['damage'] + item_data['damage']
            self.db.update_user(user_data['id'], damage=new_damage)
            await update.message.reply_text(
                f.success(f"Урон увеличен +{item_data['damage']}⚔️ (текущий: {new_damage})")
            )
        elif 'armor' in item_data:
            new_armor = user_data['armor'] + item_data['armor']
            self.db.update_user(user_data['id'], armor=new_armor)
            await update.message.reply_text(
                f.success(f"Броня увеличена +{item_data['armor']}🛡 (текущая: {new_armor})")
            )
        elif 'energy' in item_data:
            new_energy = self.db.add_energy(user_data['id'], item_data['energy'])
            await update.message.reply_text(
                f.success(f"Энергия восстановлена +{item_data['energy']}⚡ (текущая: {new_energy})")
            )
        elif 'crit_chance' in item_data:
            new_crit = user_data['crit_chance'] + item_data['crit_chance']
            self.db.update_user(user_data['id'], crit_chance=new_crit)
            await update.message.reply_text(
                f.success(f"Шанс крита увеличен +{item_data['crit_chance']}% (текущий: {new_crit}%)")
            )
        elif 'crit_multiplier' in item_data:
            new_mult = item_data['crit_multiplier']
            self.db.update_user(user_data['id'], crit_multiplier=new_mult)
            await update.message.reply_text(
                f.success(f"Множитель крита увеличен до x{new_mult//100}")
            )
        
        self.db.log_action(user_data['id'], 'buy', f"Куплен предмет: {item}")

    async def cmd_pay(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /pay - перевод монет"""
        if len(context.args) < 2:
            await update.message.reply_text(f.error("Использование: /pay @username сумма"))
            return
        
        query = context.args[0]
        try:
            amount = int(context.args[1])
        except ValueError:
            await update.message.reply_text(f.error("Сумма должна быть числом"))
            return
        
        if amount <= 0:
            await update.message.reply_text(f.error("Сумма должна быть положительной"))
            return
        
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        target_user = self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        if target_user['id'] == user_data['id']:
            await update.message.reply_text(f.error("Нельзя перевести монеты самому себе"))
            return
        
        if user_data['coins'] < amount:
            await update.message.reply_text(
                f.error(f"Недостаточно монет. Баланс: {user_data['coins']} 💰")
            )
            return
        
        # Перевод
        self.db.add_coins(user_data['id'], -amount)
        self.db.add_coins(target_user['id'], amount)
        
        # Комиссия для не-премиум
        if not self.db.is_premium(user_data['id']):
            commission = int(amount * 0.05)  # 5% комиссии
            self.db.add_coins(user_data['id'], -commission)
            commission_text = f"\n{f.item(f'💸 Комиссия: {commission} (5%)')}"
        else:
            commission_text = ""
        
        target_name = target_user.get('nickname') or target_user['first_name']
        
        text = (
            f"{f.header('ПЕРЕВОД', '💰')}\n\n"
            f"{f.item(f'Получатель: {target_name}')}\n"
            f"{f.item(f'Сумма: {amount} 💰')}"
            f"{commission_text}\n"
            f"{f.item(f'Отправитель: {user.first_name}')}\n\n"
            f"{f.success('Перевод выполнен успешно!')}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
        self.db.log_action(user_data['id'], 'pay', f"Перевод {amount}💰 пользователю {target_user['id']}")

    async def cmd_donate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /donate - информация о привилегиях"""
        text = (
            f"{f.header('ПРИВИЛЕГИИ', '💎')}\n\n"
            f"{f.section('VIP СТАТУС', '🌟')}\n"
            f"Цена: {Config.VIP_PRICE} 💰 / {Config.VIP_DAYS} дней\n"
            f"{f.item('⚔️ Урон в битвах +20%')}\n"
            f"{f.item('💰 Награда с боссов +50%')}\n"
            f"{f.item('🎁 Ежедневный бонус +50%')}\n"
            f"{f.item('💸 Без комиссии при переводе')}\n\n"
            f"{f.section('PREMIUM СТАТУС', '💎')}\n"
            f"Цена: {Config.PREMIUM_PRICE} 💰 / {Config.PREMIUM_DAYS} дней\n"
            f"{f.item('⚔️ Урон в битвах +50%')}\n"
            f"{f.item('💰 Награда с боссов +100%')}\n"
            f"{f.item('🎁 Ежедневный бонус +100%')}\n"
            f"{f.item('💸 Без комиссии при переводе')}\n"
            f"{f.item('🚫 Игнорирование спам-фильтра')}\n"
            f"{f.item('✨ Особый статус в чате')}\n\n"
            f"{f.command('vip', 'купить VIP')}\n"
            f"{f.command('premium', 'купить PREMIUM')}\n\n"
            f"👑 **Владелец:** {Config.OWNER_USERNAME}"
        )
        
        await update.message.reply_text(
            text,
            reply_markup=kb.back_button(),
            parse_mode='Markdown'
        )

    async def cmd_buy_vip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /vip - покупка VIP"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data['coins'] < Config.VIP_PRICE:
            await update.message.reply_text(
                f.error(f"Недостаточно монет. Нужно {Config.VIP_PRICE} 💰")
            )
            return
        
        if self.db.is_vip(user_data['id']):
            await update.message.reply_text(f.error("VIP статус уже активен"))
            return
        
        self.db.add_coins(user_data['id'], -Config.VIP_PRICE)
        until = self.db.set_vip(user_data['id'], Config.VIP_DAYS)
        
        await update.message.reply_text(
            f"{f.success('VIP СТАТУС АКТИВИРОВАН')}\n\n"
            f"{f.item(f'Срок действия: до {until.strftime("%d.%m.%Y")}')}\n"
            f"{f.item('Все бонусы активны!')}",
            parse_mode='Markdown'
        )
        
        self.db.log_action(user_data['id'], 'buy_vip', f"Куплен VIP на {Config.VIP_DAYS} дней")

    async def cmd_buy_premium(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /premium - покупка PREMIUM"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data['coins'] < Config.PREMIUM_PRICE:
            await update.message.reply_text(
                f.error(f"Недостаточно монет. Нужно {Config.PREMIUM_PRICE} 💰")
            )
            return
        
        if self.db.is_premium(user_data['id']):
            await update.message.reply_text(f.error("PREMIUM статус уже активен"))
            return
        
        self.db.add_coins(user_data['id'], -Config.PREMIUM_PRICE)
        until = self.db.set_premium(user_data['id'], Config.PREMIUM_DAYS)
        
        await update.message.reply_text(
            f"{f.success('PREMIUM СТАТУС АКТИВИРОВАН')}\n\n"
            f"{f.item(f'Срок действия: до {until.strftime("%d.%m.%Y")}')}\n"
            f"{f.item('Все бонусы активны!')}",
            parse_mode='Markdown'
        )
        
        self.db.log_action(user_data['id'], 'buy_premium', f"Куплен PREMIUM на {Config.PREMIUM_DAYS} дней")

    # ========== МОДЕРАЦИЯ ==========

    async def cmd_warn(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /warn - предупреждение"""
        admin = update.effective_user
        admin_data = self.db.get_user(admin.id)
        
        if not self.has_permission(admin_data, 'moderator'):
            await update.message.reply_text(f.error("Недостаточно прав"))
            return
        
        if len(context.args) < 1:
            await update.message.reply_text(f.error("Использование: /warn @username [причина]"))
            return
        
        query = context.args[0]
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else "Нарушение правил"
        
        target_user = self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        # Нельзя предупреждать администраторов
        if self.has_permission(target_user, 'moderator'):
            await update.message.reply_text(f.error("Нельзя предупредить администратора"))
            return
        
        result = self.db.add_warn(target_user['id'], admin_data['id'], reason)
        
        target_name = target_user.get('nickname') or target_user['first_name']
        
        text = (
            f"{f.header('ПРЕДУПРЕЖДЕНИЕ', '⚠️')}\n\n"
            f"{f.item(f'Пользователь: {target_name}')}\n"
            f"{f.item(f'Предупреждений: {result["warns_count"]}/3')}\n"
            f"{f.item(f'Причина: {reason}')}\n"
            f"{f.item(f'Администратор: {admin.first_name}')}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
        # Автоматический мут при 3 предупреждениях
        if result['warns_count'] >= 3:
            mute_until = self.db.mute_user(target_user['id'], 60, admin_data['id'], "3 предупреждения")
            await update.message.reply_text(
                f.warning(f"Достигнут лимит предупреждений. {target_name} замучен на 60 минут.")
            )
        
        self.db.log_action(admin_data['id'], 'warn', f"Предупреждение {target_user['id']}: {reason}")

    async def cmd_warns(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /warns - список предупреждений"""
        if not context.args:
            await update.message.reply_text(f.error("Укажите пользователя: /warns @username"))
            return
        
        query = context.args[0]
        target_user = self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        target_name = target_user.get('nickname') or target_user['first_name']
        warns_list = json.loads(target_user.get('warns_list', '[]'))
        
        if not warns_list:
            await update.message.reply_text(f.info(f"У пользователя {target_name} нет предупреждений"))
            return
        
        text = f"{f.header(f'ПРЕДУПРЕЖДЕНИЯ: {target_name}', '📋')}\n\n"
        
        for warn in warns_list:
            admin = self.db.get_user_by_id(warn['admin_id'])
            admin_name = admin.get('first_name', 'Система') if admin else 'Система'
            date = datetime.datetime.fromisoformat(warn['date']).strftime("%d.%m.%Y %H:%M")
            
            text += (
                f"**ID: {warn['id']}**\n"
                f"{f.item(f'Причина: {warn["reason"]}')}\n"
                f"{f.item(f'Администратор: {admin_name}')}\n"
                f"{f.item(f'Дата: {date}')}\n\n"
            )
        
        await update.message.reply_text(text, parse_mode='Markdown')

    async def cmd_unwarn(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /unwarn - снятие предупреждения"""
        admin = update.effective_user
        admin_data = self.db.get_user(admin.id)
        
        if not self.has_permission(admin_data, 'moderator'):
            await update.message.reply_text(f.error("Недостаточно прав"))
            return
        
        if not context.args:
            await update.message.reply_text(f.error("Укажите пользователя: /unwarn @username"))
            return
        
        query = context.args[0]
        target_user = self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        removed = self.db.remove_last_warn(target_user['id'])
        target_name = target_user.get('nickname') or target_user['first_name']
        
        if not removed:
            await update.message.reply_text(f.info(f"У пользователя {target_name} нет предупреждений"))
            return
        
        await update.message.reply_text(
            f.success(f"Последнее предупреждение снято с {target_name}"),
            parse_mode='Markdown'
        )
        
        self.db.log_action(admin_data['id'], 'unwarn', f"Снято предупреждение с {target_user['id']}")

    async def cmd_mute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /mute - мут пользователя"""
        admin = update.effective_user
        admin_data = self.db.get_user(admin.id)
        
        if not self.has_permission(admin_data, 'moderator'):
            await update.message.reply_text(f.error("Недостаточно прав"))
            return
        
        if len(context.args) < 2:
            await update.message.reply_text(f.error("Использование: /mute @username минут [причина]"))
            return
        
        query = context.args[0]
        try:
            minutes = int(context.args[1])
            reason = " ".join(context.args[2:]) if len(context.args) > 2 else "Нарушение"
        except ValueError:
            await update.message.reply_text(f.error("Некорректное время"))
            return
        
        target_user = self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        # Нельзя мутить администраторов
        if self.has_permission(target_user, 'moderator'):
            await update.message.reply_text(f.error("Нельзя замутить администратора"))
            return
        
        mute_until = self.db.mute_user(target_user['id'], minutes, admin_data['id'], reason)
        target_name = target_user.get('nickname') or target_user['first_name']
        
        until_str = mute_until.strftime("%d.%m.%Y %H:%M")
        
        text = (
            f"{f.header('МУТ', '🔇')}\n\n"
            f"{f.item(f'Пользователь: {target_name}')}\n"
            f"{f.item(f'Срок: {minutes} минут')}\n"
            f"{f.item(f'До: {until_str}')}\n"
            f"{f.item(f'Причина: {reason}')}\n"
            f"{f.item(f'Администратор: {admin.first_name}')}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
        self.db.log_action(admin_data['id'], 'mute', f"Мут {target_user['id']} на {minutes} минут: {reason}")

    async def cmd_unmute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /unmute - снятие мута"""
        admin = update.effective_user
        admin_data = self.db.get_user(admin.id)
        
        if not self.has_permission(admin_data, 'moderator'):
            await update.message.reply_text(f.error("Недостаточно прав"))
            return
        
        if not context.args:
            await update.message.reply_text(f.error("Укажите пользователя: /unmute @username"))
            return
        
        query = context.args[0]
        target_user = self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        if not self.db.is_muted(target_user['id']):
            await update.message.reply_text(f.info("Пользователь не в муте"))
            return
        
        self.db.unmute_user(target_user['id'])
        target_name = target_user.get('nickname') or target_user['first_name']
        
        await update.message.reply_text(
            f.success(f"Мут снят с {target_name}"),
            parse_mode='Markdown'
        )
        
        self.db.log_action(admin_data['id'], 'unmute', f"Снят мут с {target_user['id']}")

    async def cmd_mutelist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /mutelist - список замученных"""
        muted = self.db.get_muted_users()
        
        if not muted:
            await update.message.reply_text(f.info("Нет пользователей в муте"))
            return
        
        text = f"{f.header('СПИСОК ЗАМУЧЕННЫХ', '🔇')}\n\n"
        
        for user in muted[:10]:
            until = datetime.datetime.fromisoformat(user['mute_until']).strftime("%d.%m.%Y %H:%M")
            name = user.get('nickname') or user['first_name']
            text += f"{f.item(f'{name} — до {until}')}\n"
        
        await update.message.reply_text(
            text,
            reply_markup=kb.back_button(),
            parse_mode='Markdown'
        )

    async def cmd_ban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /ban - бан пользователя"""
        admin = update.effective_user
        admin_data = self.db.get_user(admin.id)
        
        if not self.has_permission(admin_data, 'moderator'):
            await update.message.reply_text(f.error("Недостаточно прав"))
            return
        
        if len(context.args) < 1:
            await update.message.reply_text(f.error("Использование: /ban @username [причина]"))
            return
        
        query = context.args[0]
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else "Нарушение правил"
        
        target_user = self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        # Нельзя банить администраторов
        if self.has_permission(target_user, 'moderator'):
            await update.message.reply_text(f.error("Нельзя забанить администратора"))
            return
        
        if self.db.is_banned(target_user['id']):
            await update.message.reply_text(f.error("Пользователь уже забанен"))
            return
        
        self.db.ban_user(target_user['id'], admin_data['id'], reason)
        target_name = target_user.get('nickname') or target_user['first_name']
        
        text = (
            f"{f.header('БЛОКИРОВКА', '🔴')}\n\n"
            f"{f.item(f'Пользователь: {target_name}')}\n"
            f"{f.item(f'Причина: {reason}')}\n"
            f"{f.item(f'Администратор: {admin.first_name}')}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
        self.db.log_action(admin_data['id'], 'ban', f"Бан {target_user['id']}: {reason}")

    async def cmd_unban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /unban - разбан пользователя"""
        admin = update.effective_user
        admin_data = self.db.get_user(admin.id)
        
        if not self.has_permission(admin_data, 'moderator'):
            await update.message.reply_text(f.error("Недостаточно прав"))
            return
        
        if not context.args:
            await update.message.reply_text(f.error("Укажите пользователя: /unban @username"))
            return
        
        query = context.args[0]
        target_user = self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        if not self.db.is_banned(target_user['id']):
            await update.message.reply_text(f.info("Пользователь не забанен"))
            return
        
        self.db.unban_user(target_user['id'])
        target_name = target_user.get('nickname') or target_user['first_name']
        
        await update.message.reply_text(
            f.success(f"Блокировка снята с {target_name}"),
            parse_mode='Markdown'
        )
        
        self.db.log_action(admin_data['id'], 'unban', f"Разбан {target_user['id']}")

    async def cmd_banlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /banlist - список забаненных"""
        page = 1
        if context.args and context.args[0].isdigit():
            page = int(context.args[0])
        
        bans, total = self.db.get_banlist(page)
        total_pages = (total + 9) // 10
        
        if not bans:
            await update.message.reply_text(f.info("Список заблокированных пуст"))
            return
        
        text = f"{f.header('СПИСОК ЗАБЛОКИРОВАННЫХ', '📋')}\n"
        text += f"Страница {page}/{total_pages}\n\n"
        
        for i, ban in enumerate(bans, 1):
            date = datetime.datetime.fromisoformat(ban['ban_date']).strftime("%d.%m.%Y") if ban['ban_date'] else "неизвестно"
            name = ban.get('nickname') or ban['first_name']
            text += (
                f"{i}. {name}\n"
                f"└ Причина: {ban['ban_reason']}\n"
                f"└ Дата: {date}\n"
                f"└ Заблокировал: {ban['admin_name']}\n\n"
            )
        
        await update.message.reply_text(
            text,
            reply_markup=kb.pagination(page, total_pages, "banlist"),
            parse_mode='Markdown'
        )

    async def cmd_kick(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /kick - исключение пользователя"""
        admin = update.effective_user
        admin_data = self.db.get_user(admin.id)
        
        if not self.has_permission(admin_data, 'moderator'):
            await update.message.reply_text(f.error("Недостаточно прав"))
            return
        
        if not context.args:
            await update.message.reply_text(f.error("Укажите пользователя: /kick @username"))
            return
        
        query = context.args[0]
        target_user = self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(f.error("Пользователь не найден"))
            return
        
        target_name = target_user.get('nickname') or target_user['first_name']
        
        await update.message.reply_text(
            f.success(f"Пользователь {target_name} исключен из чата"),
            parse_mode='Markdown'
        )
        
        self.db.log_action(admin_data['id'], 'kick', f"Кик {target_user['id']}")

    async def cmd_clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /clear - очистка чата (для администраторов)"""
        admin = update.effective_user
        admin_data = self.db.get_user(admin.id)
        
        if not self.has_permission(admin_data, 'moderator'):
            await update.message.reply_text(f.error("Недостаточно прав"))
            return
        
        if not context.args:
            await update.message.reply_text(f.error("Укажите количество сообщений: /clear [количество]"))
            return
        
        try:
            amount = int(context.args[0])
            if amount <= 0 or amount > 100:
                await update.message.reply_text(f.error("Количество должно быть от 1 до 100"))
                return
        except ValueError:
            await update.message.reply_text(f.error("Некорректное число"))
            return
        
        # В Telegram нельзя удалять чужие сообщения в группах без прав
        await update.message.reply_text(
            f.success(f"Команда очистки на {amount} сообщений отправлена"),
            parse_mode='Markdown'
        )

    # ========== ПРОЧИЕ КОМАНДЫ ==========

    async def cmd_weather(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /weather - погода"""
        city = " ".join(context.args) if context.args else "Москва"
        
        # Симуляция погоды
        weathers = ["☀️ солнечно", "⛅ облачно", "☁️ пасмурно", "🌧 дождь", "⛈ гроза", "❄️ снег"]
        temp = random.randint(-15, 30)
        wind = random.randint(0, 15)
        humidity = random.randint(30, 90)
        weather = random.choice(weathers)
        
        text = (
            f"{f.header(f'ПОГОДА: {city.upper()}', '🌍')}\n\n"
            f"{weather}, {temp}°C\n"
            f"💨 Ветер: {wind} м/с\n"
            f"💧 Влажность: {humidity}%\n"
            f"📅 {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')

    async def cmd_time(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /time - текущее время"""
        now = datetime.datetime.now()
        text = (
            f"{f.header('ТЕКУЩЕЕ ВРЕМЯ', '⏰')}\n\n"
            f"{f.item(f'Дата: {now.strftime("%d.%m.%Y")}')}\n"
            f"{f.item(f'Время: {now.strftime("%H:%M:%S")}')}\n"
            f"{f.item(f'День недели: {now.strftime("%A")}')}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')

    async def cmd_quote(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /quote - случайная цитата"""
        quotes = [
            "Успех — это способность идти от поражения к поражению, не теряя энтузиазма.",
            "Сложнее всего начать действовать, все остальное зависит только от упорства.",
            "Лучший способ предсказать будущее — создать его.",
            "Не бойтесь, что у вас не получится. Бойтесь, что вы не попробуете.",
            "Будьте собой, остальные роли уже заняты.",
            "Каждый день — это новая возможность изменить свою жизнь.",
            "Единственный способ делать великую работу — любить то, что вы делаете.",
            "Верьте, что вы можете, и вы уже на полпути.",
            "Действие — это ключ к успеху.",
            "Терпение и труд всё перетрут."
        ]
        
        text = f"{f.header('ЦИТАТА ДНЯ', '📝')}\n\n«{random.choice(quotes)}»"
        
        await update.message.reply_text(text, parse_mode='Markdown')

    async def cmd_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /id - получение ID"""
        user = update.effective_user
        
        if context.args:
            query = context.args[0]
            target_user = self.db.get_user_by_username(query)
            if target_user:
                target_name = target_user.get('nickname') or target_user['first_name']
                await update.message.reply_text(
                    f"{f.header('ID ПОЛЬЗОВАТЕЛЯ', '🆔')}\n\n"
                    f"{f.item(f'Пользователь: {target_name}')}\n"
                    f"{f.item(f'Telegram ID: {f.code(str(target_user["telegram_id"]))}')}\n"
                    f"{f.item(f'Внутренний ID: {f.code(str(target_user["id"]))}')}",
                    parse_mode='Markdown'
                )
                return
        
        await update.message.reply_text(
            f"{f.header('ТВОЙ ID', '🆔')}\n\n"
            f"{f.item(f'Telegram ID: {f.code(str(user.id))}')}",
            parse_mode='Markdown'
        )

    async def cmd_ping(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /ping - проверка работы"""
        start_time = time.time()
        msg = await update.message.reply_text("🏓 Pong!")
        end_time = time.time()
        
        ping = int((end_time - start_time) * 1000)
        uptime = datetime.datetime.now() - self.start_time
        hours = uptime.seconds // 3600
        minutes = (uptime.seconds % 3600) // 60
        
        await msg.edit_text(
            f"{f.header('ПОНГ', '🏓')}\n\n"
            f"{f.item(f'Задержка: {ping} мс')}\n"
            f"{f.item(f'Аптайм: {hours}ч {minutes}м')}\n"
            f"{f.item(f'Статус: ✅ Работаю')}",
            parse_mode='Markdown'
        )

    # ========== ОБРАБОТЧИКИ ==========

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        user = update.effective_user
        message_text = update.message.text
        
        if message_text.startswith('/'):
            return
        
        user_data = self.db.get_user(user.id, user.first_name)
        
        # Обновляем статистику сообщений
        self.db.update_user(user_data['id'], messages_count=user_data['messages_count'] + 1)
        
        # Проверка на бан
        if self.db.is_banned(user_data['id']):
            return
        
        # Проверка на мут
        if self.db.is_muted(user_data['id']):
            await update.message.reply_text(f.error("Вы находитесь в муте и не можете писать."))
            return
        
        # Проверка на спам
        if await self.check_spam(update):
            return
        
        # Получаем ответ от AI
        response = await self.ai.get_response(user.id, message_text)
        if response:
            await update.message.reply_text(f"🤖 **СПЕКТР:** {response}", parse_mode='Markdown')
            return
        
        # Fallback ответы
        msg_lower = message_text.lower()
        
        if any(word in msg_lower for word in ["привет", "здравствуйте", "хай"]):
            await update.message.reply_text("👋 Здравствуйте! Чем могу помочь?")
        elif any(word in msg_lower for word in ["как дела", "как вы"]):
            await update.message.reply_text("⚙️ Всё функционирует в штатном режиме")
        elif any(word in msg_lower for word in ["спасибо", "благодарю"]):
            await update.message.reply_text("🤝 Рад помочь!")
        elif any(word in msg_lower for word in ["кто создал", "владелец"]):
            await update.message.reply_text(f"👑 Владелец: {Config.OWNER_USERNAME}")
        else:
            responses = [
                "Используйте /help для просмотра доступных команд.",
                "Я к вашим услугам. Напишите /menu для навигации.",
                "Чем могу быть полезен?",
                "Обратитесь к справке /help."
            ]
            await update.message.reply_text(random.choice(responses))

    async def handle_new_members(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка новых участников"""
        for member in update.message.new_chat_members:
            if member.is_bot:
                continue
            
            await update.message.reply_text(
                f"👋 Добро пожаловать, {member.first_name}!\n"
                f"Я — **СПЕКТР**, твой игровой помощник. Используй /help для списка команд.",
                parse_mode='Markdown'
            )

    async def handle_left_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ухода участников"""
        member = update.message.left_chat_member
        if member.is_bot:
            return
        
        await update.message.reply_text(
            f"👋 {member.first_name} покинул чат. Будем ждать возвращения!",
            parse_mode='Markdown'
        )

    # ========== CALLBACK КНОПКИ ==========

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
                f"{f.header('ГЛАВНОЕ МЕНЮ', '🎮')}\n\nВыберите раздел:",
                reply_markup=kb.main_menu(),
                parse_mode='Markdown'
            )
        
        elif data == "menu_back":
            await query.edit_message_text(
                f"{f.header('ГЛАВНОЕ МЕНЮ', '🎮')}\n\nВыберите раздел:",
                reply_markup=kb.main_menu(),
                parse_mode='Markdown'
            )
        
        elif data == "menu_profile":
            context.args = []
            await self.cmd_profile(update, context)
        
        elif data == "menu_stats":
            context.args = []
            await self.cmd_stats(update, context)
        
        elif data == "menu_battles":
            await query.edit_message_text(
                f"{f.header('БИТВЫ', '⚔️')}\n\nВыберите режим:",
                reply_markup=kb.battle_menu(),
                parse_mode='Markdown'
            )
        
        elif data == "battle_bosses":
            context.args = []
            await self.cmd_bosses(update, context)
        
        elif data == "battle_pvp":
            await query.edit_message_text(
                f"{f.header('PvP', '⚔️')}\n\nРаздел в разработке",
                reply_markup=kb.back_button(),
                parse_mode='Markdown'
            )
        
        elif data == "menu_casino":
            await query.edit_message_text(
                f"{f.header('КАЗИНО', '🎰')}\n\nВыберите игру:",
                reply_markup=kb.casino_menu(),
                parse_mode='Markdown'
            )
        
        elif data == "casino_roulette":
            context.args = []
            await self.cmd_roulette(update, context)
        
        elif data == "casino_dice":
            context.args = []
            await self.cmd_dice(update, context)
        
        elif data == "casino_rps":
            await query.edit_message_text(
                f"{f.header('КАМЕНЬ-НОЖНИЦЫ-БУМАГА', '✊')}\n\nВыберите свой ход:",
                reply_markup=kb.rps_game(),
                parse_mode='Markdown'
            )
        
        elif data == "casino_blackjack":
            context.args = []
            await self.cmd_blackjack(update, context)
        
        elif data == "casino_slots":
            context.args = []
            await self.cmd_slots(update, context)
        
        elif data == "menu_shop":
            context.args = []
            await self.cmd_shop(update, context)
        
        elif data == "menu_donate":
            context.args = []
            await self.cmd_donate(update, context)
        
        elif data == "menu_admin":
            user_data = self.db.get_user(user.id)
            is_owner = (user.id == Config.OWNER_ID)
            await query.edit_message_text(
                f"{f.header('АДМИН-ПАНЕЛЬ', '⚙️')}\n\nВыберите действие:",
                reply_markup=kb.admin_menu(is_owner),
                parse_mode='Markdown'
            )
        
        elif data == "menu_help":
            context.args = []
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
                await query.edit_message_text(
                    f"{f.header('ИЗМЕНЕНИЕ НИКА', '✏️')}\n\n"
                    f"Используйте команду:\n"
                    f"{f.command('nick [ник]', 'установить ник')}\n"
                    f"{f.example('nick Spectr')}",
                    reply_markup=kb.back_button(),
                    parse_mode='Markdown'
                )
            elif data == "edit_title":
                await query.edit_message_text(
                    f"{f.header('ИЗМЕНЕНИЕ ТИТУЛА', '🏷')}\n\n"
                    f"Используйте команду:\n"
                    f"{f.command('title [титул]', 'установить титул')}\n"
                    f"{f.example('title Легенда')}",
                    reply_markup=kb.back_button(),
                    parse_mode='Markdown'
                )
            elif data == "edit_motto":
                await query.edit_message_text(
                    f"{f.header('ИЗМЕНЕНИЕ ДЕВИЗА', '📝')}\n\n"
                    f"Используйте команду:\n"
                    f"{f.command('motto [девиз]', 'установить девиз')}\n"
                    f"{f.example('motto Carpe diem')}",
                    reply_markup=kb.back_button(),
                    parse_mode='Markdown'
                )
            elif data == "edit_gender":
                await query.edit_message_text(
                    f"{f.header('ИЗМЕНЕНИЕ ПОЛА', '👤')}\n\n"
                    f"Используйте команду:\n"
                    f"{f.command('gender [м/ж/др]', 'установить пол')}\n"
                    f"{f.example('gender м')}",
                    reply_markup=kb.back_button(),
                    parse_mode='Markdown'
                )
        
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
            
            text = f"{f.header('КНБ', '✊')}\n\n"
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
                reply_markup=kb.back_button(),
                parse_mode='Markdown'
            )

    # ========== ЗАПУСК ==========

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
            logger.info(f"📊 Бот работает с PID: {os.getpid()}")
            
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
        await self.ai.close()
        self.db.close()
        
        # Удаляем lock-файл
        global LOCK_FILE
        cleanup_lock()
        
        logger.info("✅ Бот остановлен")


# ========== ТОЧКА ВХОДА ==========
async def main():
    """Главная функция"""
    print("=" * 60)
    print("🚀 ЗАПУСК БОТА СПЕКТР")
    print("=" * 60)
    print(f"📊 PID: {os.getpid()}")
    print(f"📁 Lock-файл: {LOCK_FILE}")
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
        cleanup_lock()

if __name__ == "__main__":
    asyncio.run(main())
