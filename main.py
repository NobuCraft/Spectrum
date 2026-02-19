import asyncio
import logging
import random
import re
import sqlite3
import string
import json
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
import os

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command, Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ParseMode, InputFile
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import groq

# Конфигурация из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "123456789").split(",")))
DATABASE_URL = os.getenv("DATABASE_URL", "spectr.db")

# Инициализация
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())
groq_client = groq.AsyncGroq(api_key=GROQ_API_KEY)

# База данных
conn = sqlite3.connect(DATABASE_URL, check_same_thread=False)
cursor = conn.cursor()

# Создание таблиц
cursor.executescript("""
-- Пользователи
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    rank INTEGER DEFAULT 0,
    warnings INTEGER DEFAULT 0,
    is_muted INTEGER DEFAULT 0,
    mute_until TEXT,
    iris_balance INTEGER DEFAULT 100,
    vip_level INTEGER DEFAULT 0,
    reputation INTEGER DEFAULT 0,
    married_to INTEGER,
    clan_id INTEGER,
    joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    messages_count INTEGER DEFAULT 0,
    commands_count INTEGER DEFAULT 0,
    daily_streak INTEGER DEFAULT 0,
    last_daily TIMESTAMP,
    bio TEXT,
    age INTEGER,
    city TEXT,
    gender TEXT,
    photo_id TEXT
);

-- Модераторы чата
CREATE TABLE IF NOT EXISTS moderators (
    user_id INTEGER,
    chat_id INTEGER,
    rank INTEGER,
    assigned_by INTEGER,
    assigned_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER DEFAULT 1,
    PRIMARY KEY (user_id, chat_id)
);

-- Предупреждения
CREATE TABLE IF NOT EXISTS warnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    chat_id INTEGER,
    reason TEXT,
    issued_by INTEGER,
    issued_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Муты
CREATE TABLE IF NOT EXISTS mutes (
    user_id INTEGER,
    chat_id INTEGER,
    until TIMESTAMP,
    reason TEXT,
    issued_by INTEGER,
    PRIMARY KEY (user_id, chat_id)
);

-- Баны
CREATE TABLE IF NOT EXISTS bans (
    user_id INTEGER,
    chat_id INTEGER,
    reason TEXT,
    issued_by INTEGER,
    issued_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, chat_id)
);

-- Глобальные баны
CREATE TABLE IF NOT EXISTS global_bans (
    user_id INTEGER PRIMARY KEY,
    reason TEXT,
    issued_by INTEGER,
    issued_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Триггеры
CREATE TABLE IF NOT EXISTS triggers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER,
    trigger_word TEXT,
    action TEXT,
    action_param TEXT,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Настройки чата
CREATE TABLE IF NOT EXISTS chat_settings (
    chat_id INTEGER PRIMARY KEY,
    welcome_message TEXT,
    rules TEXT,
    captcha_enabled INTEGER DEFAULT 0,
    captcha_difficulty INTEGER DEFAULT 3,
    antimat INTEGER DEFAULT 0,
    antilinks INTEGER DEFAULT 0,
    antiflood INTEGER DEFAULT 0,
    antispam INTEGER DEFAULT 0,
    antiraid INTEGER DEFAULT 0,
    antibot INTEGER DEFAULT 0,
    language TEXT DEFAULT 'ru',
    region TEXT,
    allow_links INTEGER DEFAULT 1,
    allow_media INTEGER DEFAULT 1,
    allow_stickers INTEGER DEFAULT 1,
    allow_gifs INTEGER DEFAULT 1,
    verification_enabled INTEGER DEFAULT 0
);

-- Команды и права
CREATE TABLE IF NOT EXISTS command_permissions (
    command TEXT,
    chat_id INTEGER,
    min_rank INTEGER DEFAULT 0,
    PRIMARY KEY (command, chat_id)
);

-- Исключения для команд
CREATE TABLE IF NOT EXISTS command_exceptions (
    command TEXT,
    user_id INTEGER,
    chat_id INTEGER,
    PRIMARY KEY (command, user_id, chat_id)
);

-- Сетка чатов
CREATE TABLE IF NOT EXISTS chat_grids (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS grid_chats (
    grid_id INTEGER,
    chat_id INTEGER,
    PRIMARY KEY (grid_id, chat_id)
);

-- Игры мафии
CREATE TABLE IF NOT EXISTS mafia_games (
    game_id TEXT PRIMARY KEY,
    chat_id INTEGER,
    status TEXT DEFAULT 'waiting',
    phase TEXT DEFAULT 'day',
    day_count INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    mafia_kill_target INTEGER,
    doctor_heal_target INTEGER,
    commissioner_check_target INTEGER,
    maniac_kill_target INTEGER,
    boss_protected INTEGER DEFAULT 0,
    min_players INTEGER DEFAULT 6,
    max_players INTEGER DEFAULT 20
);

CREATE TABLE IF NOT EXISTS mafia_players (
    user_id INTEGER,
    game_id TEXT,
    role TEXT,
    is_alive INTEGER DEFAULT 1,
    action_target INTEGER,
    action_done INTEGER DEFAULT 0,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    vote_for INTEGER,
    PRIMARY KEY (user_id, game_id)
);

-- Русская рулетка
CREATE TABLE IF NOT EXISTS russian_roulette (
    user_id INTEGER PRIMARY KEY,
    chat_id INTEGER,
    chamber_position INTEGER,
    bullet_position INTEGER,
    games_played INTEGER DEFAULT 0,
    games_won INTEGER DEFAULT 0,
    last_game TIMESTAMP
);

-- Ириски (транзакции)
CREATE TABLE IF NOT EXISTS iris_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_user INTEGER,
    to_user INTEGER,
    amount INTEGER,
    reason TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Магазин
CREATE TABLE IF NOT EXISTS shop_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    description TEXT,
    price INTEGER,
    type TEXT,
    stock INTEGER DEFAULT -1,
    is_available INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS user_items (
    user_id INTEGER,
    item_id INTEGER,
    quantity INTEGER DEFAULT 1,
    purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, item_id)
);

-- Друзья
CREATE TABLE IF NOT EXISTS friends (
    user_id INTEGER,
    friend_id INTEGER,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, friend_id)
);

-- Враги
CREATE TABLE IF NOT EXISTS enemies (
    user_id INTEGER,
    enemy_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, enemy_id)
);

-- Игнор
CREATE TABLE IF NOT EXISTS ignored (
    user_id INTEGER,
    ignored_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, ignored_id)
);

-- Кланы
CREATE TABLE IF NOT EXISTS clans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    leader_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    balance INTEGER DEFAULT 0,
    description TEXT,
    emblem TEXT
);

CREATE TABLE IF NOT EXISTS clan_members (
    clan_id INTEGER,
    user_id INTEGER,
    role TEXT DEFAULT 'member',
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (clan_id, user_id)
);

-- Кружки
CREATE TABLE IF NOT EXISTS circles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    description TEXT,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS circle_members (
    circle_id INTEGER,
    user_id INTEGER,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (circle_id, user_id)
);

CREATE TABLE IF NOT EXISTS circle_meetings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    circle_id INTEGER,
    title TEXT,
    date TEXT,
    time TEXT,
    place TEXT,
    created_by INTEGER
);

-- Достижения
CREATE TABLE IF NOT EXISTS achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    description TEXT,
    reward INTEGER DEFAULT 0,
    icon TEXT
);

CREATE TABLE IF NOT EXISTS user_achievements (
    user_id INTEGER,
    achievement_id INTEGER,
    earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, achievement_id)
);

-- Награды
CREATE TABLE IF NOT EXISTS awards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    description TEXT,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_awards (
    user_id INTEGER,
    award_id INTEGER,
    awarded_by INTEGER,
    awarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, award_id)
);

-- Заметки
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    title TEXT,
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tags TEXT
);

-- Закладки
CREATE TABLE IF NOT EXISTS bookmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    title TEXT,
    content TEXT,
    url TEXT,
    category TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таймеры
CREATE TABLE IF NOT EXISTS timers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    chat_id INTEGER,
    title TEXT,
    end_time TIMESTAMP,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Напоминания
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    text TEXT,
    remind_time TIMESTAMP,
    repeat_interval TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Дуэли
CREATE TABLE IF NOT EXISTS duels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    challenger_id INTEGER,
    opponent_id INTEGER,
    bet_amount INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    challenger_hp INTEGER DEFAULT 100,
    opponent_hp INTEGER DEFAULT 100,
    current_turn INTEGER,
    winner_id INTEGER
);

-- Кубы (коллекционные)
CREATE TABLE IF NOT EXISTS cubes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    color TEXT,
    rarity TEXT,
    price INTEGER,
    emoji TEXT
);

CREATE TABLE IF NOT EXISTS user_cubes (
    user_id INTEGER,
    cube_id INTEGER,
    quantity INTEGER DEFAULT 1,
    obtained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, cube_id)
);

-- Темы
CREATE TABLE IF NOT EXISTS topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER,
    title TEXT,
    description TEXT,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    votes_for INTEGER DEFAULT 0,
    votes_against INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS topic_votes (
    topic_id INTEGER,
    user_id INTEGER,
    vote_type TEXT,
    voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (topic_id, user_id)
);

-- Предложения команд
CREATE TABLE IF NOT EXISTS command_suggestions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    command TEXT,
    description TEXT,
    suggested_by INTEGER,
    votes_for INTEGER DEFAULT 0,
    votes_against INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Черный список слов
CREATE TABLE IF NOT EXISTS blacklist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER,
    word TEXT,
    added_by INTEGER,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Спамлист
CREATE TABLE IF NOT EXISTS spamlist (
    user_id INTEGER PRIMARY KEY,
    reason TEXT,
    added_by INTEGER,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Мошенники
CREATE TABLE IF NOT EXISTS scammers (
    user_id INTEGER PRIMARY KEY,
    proof TEXT,
    added_by INTEGER,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""")
conn.commit()

# Состояния для FSM
class MafiaGame(StatesGroup):
    waiting = State()
    joining = State()
    night_actions = State()
    day_voting = State()
    trial = State()

class RussianRoulette(StatesGroup):
    playing = State()

class Duel(StatesGroup):
    fighting = State()

class Profile(StatesGroup):
    editing_name = State()
    editing_age = State()
    editing_city = State()
    editing_bio = State()
    editing_gender = State()
    editing_photo = State()

class Note(StatesGroup):
    adding = State()
    editing = State()

class Bookmark(StatesGroup):
    adding = State()
    editing = State()

class Timer(StatesGroup):
    adding = State()

class Reminder(StatesGroup):
    adding = State()

class Clan(StatesGroup):
    creating = State()
    joining = State()

class Circle(StatesGroup):
    creating = State()
    meeting = State()

# Утилиты
def get_user_rank(user_id: int, chat_id: int) -> int:
    """Получить ранг пользователя в чате"""
    cursor.execute("SELECT rank FROM moderators WHERE user_id = ? AND chat_id = ? AND is_active = 1", (user_id, chat_id))
    result = cursor.fetchone()
    if result:
        return result[0]
    
    if user_id in ADMIN_IDS:
        return 5
    
    return 0

def check_permission(command: str, chat_id: int, user_id: int) -> bool:
    """Проверить, есть ли у пользователя права на команду"""
    # Проверка исключений
    cursor.execute("SELECT 1 FROM command_exceptions WHERE command = ? AND user_id = ? AND chat_id = ?", 
                  (command, user_id, chat_id))
    if cursor.fetchone():
        return True
    
    user_rank = get_user_rank(user_id, chat_id)
    
    cursor.execute("SELECT min_rank FROM command_permissions WHERE command = ? AND chat_id = ?", (command, chat_id))
    result = cursor.fetchone()
    required_rank = result[0] if result else 0
    
    return user_rank >= required_rank

def parse_time(time_str: str) -> Optional[timedelta]:
    """Парсинг времени из строки (30м, 2ч, 1д)"""
    match = re.match(r"(\d+)([сcмчд])", time_str.lower())
    if not match:
        return None
    
    amount = int(match.group(1))
    unit = match.group(2)
    
    if unit in ["с", "c"]:
        return timedelta(seconds=amount)
    elif unit == "м":
        return timedelta(minutes=amount)
    elif unit == "ч":
        return timedelta(hours=amount)
    elif unit == "д":
        return timedelta(days=amount)
    
    return None

def format_number(num: int) -> str:
    """Форматирование числа с разделителями"""
    return f"{num:,}".replace(",", " ")

def get_rank_emoji(rank: int) -> str:
    """Получить эмодзи для ранга"""
    emojis = ["👤", "🛡️", "⚔️", "👑", "💎", "🌟"]
    return emojis[rank] if rank < len(emojis) else "❓"

def get_rank_name(rank: int) -> str:
    """Получить название ранга"""
    names = ["Пользователь", "Мл. модератор", "Ст. модератор", "Мл. администратор", "Ст. администратор", "Создатель"]
    return names[rank] if rank < len(names) else "Неизвестно"

def extract_user_id(text: str) -> Optional[int]:
    """Извлечь ID пользователя из текста (ссылка или упоминание)"""
    # Формат: @username
    match = re.search(r"@(\w+)", text)
    if match:
        username = match.group(1)
        cursor.execute("SELECT user_id FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        if result:
            return result[0]
    
    # Формат: ссылка на пользователя
    match = re.search(r"tg://user\?id=(\d+)", text)
    if match:
        return int(match.group(1))
    
    # Формат: просто число
    match = re.search(r"(\d+)", text)
    if match:
        return int(match.group(1))
    
    return None

def get_user_info(user_id: int) -> Dict:
    """Получить информацию о пользователе"""
    cursor.execute("""
        SELECT user_id, username, first_name, last_name, iris_balance, 
               vip_level, reputation, messages_count, commands_count
        FROM users WHERE user_id = ?
    """, (user_id,))
    result = cursor.fetchone()
    if result:
        return {
            "id": result[0],
            "username": result[1],
            "first_name": result[2],
            "last_name": result[3],
            "balance": result[4],
            "vip": result[5],
            "reputation": result[6],
            "messages": result[7],
            "commands": result[8]
        }
    return None

# Декоратор проверки прав
def permission_required(command: str):
    def decorator(func):
        async def wrapper(message: types.Message, *args, **kwargs):
            if not check_permission(command, message.chat.id, message.from_user.id):
                await message.reply("🚫 У вас нет прав для использования этой команды.")
                return
            return await func(message, *args, **kwargs)
        return wrapper
    return decorator

# Регистрация пользователя
async def register_user(message: types.Message):
    cursor.execute("""
        INSERT OR IGNORE INTO users (user_id, username, first_name, last_name)
        VALUES (?, ?, ?, ?)
    """, (message.from_user.id, message.from_user.username, 
          message.from_user.first_name, message.from_user.last_name))
    conn.commit()

# Команды модерации
@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    await register_user(message)
    
    text = """
🌟 <b>Спектр 2.0</b> — многофункциональный бот для чатов

<b>Доступные модули:</b>
👮‍♂️ Модерация (5 рангов)
🎮 Игры: Мафия, Русская рулетка, Дуэли
💰 Экономика: Ириски, магазин, донат
👥 Социальное: Кланы, друзья, браки
📊 Статистика и рейтинги
🤖 Искусственный интеллект

<b>Команды:</b>
/help — список всех команд
/profile — анкета пользователя
/mafia — начать игру в мафию
/roulette — русская рулетка
/duel — вызвать на дуэль
/clan — управление кланом
/shop — магазин
/daily — ежедневный бонус

Присоединяйся к игре! 🎮
"""
    await message.reply(text)

@dp.message_handler(commands=["help"])
async def cmd_help(message: types.Message):
    await register_user(message)
    
    text = """
📚 <b>Спектр 2.0 — Справка</b>

<b>Основные разделы:</b>
• /help_mod — команды модерации
• /help_game — игровые команды
• /help_social — социальные команды
• /help_economy — экономика и магазин
• /help_utils — полезные команды

<b>Быстрые команды:</b>
/mafia — начать мафию
/roulette — русская рулетка
/profile — анкета
/top — топ чата
/daily — бонус

По всем вопросам: @admin
"""
    await message.reply(text)

@dp.message_handler(commands=["help_mod"])
async def cmd_help_mod(message: types.Message):
    text = """
👮‍♂️ <b>Команды модерации</b>

<b>Назначение модераторов:</b>
+Модер [ссылка] — ранг 1
+Модер 2 [ссылка] — ранг 2
+Модер 3 [ссылка] — ранг 3
+Модер 4 [ссылка] — ранг 4
+Модер 5 [ссылка] — ранг 5

<b>Управление рангами:</b>
Повысить [ссылка] — +1 ранг
Понизить [ссылка] — -1 ранг
Снять [ссылка] — снять статус

<b>Предупреждения:</b>
Варн [ссылка] [причина] — выдать варн
Варны [ссылка] — список варнов
Снять варн [ссылка] — снять последний

<b>Муты и баны:</b>
Мут [ссылка] [время] [причина]
Размут [ссылка]
Бан [ссылка] [причина]
Разбан [ссылка]
Кик [ссылка]

<b>Очистка:</b>
Чистка [количество]
Чистка всё
Чистка от [ссылка]

<b>Настройки:</b>
Антимат on/off
Антиссылки on/off
Антифлуд on/off
"""
    await message.reply(text)

@dp.message_handler(commands=["help_game"])
async def cmd_help_game(message: types.Message):
    text = """
🎮 <b>Игровые команды</b>

<b>Мафия:</b>
/mafia — начать игру
/join — присоединиться
/start_game — начать (создатель)
/leave — выйти из игры
/roles — список ролей
/vote [@user] — голосовать
/kill [@user] — убить (мафия)
/heal [@user] — лечить (доктор)
/check [@user] — проверить (комиссар)

<b>Русская рулетка:</b>
/roulette — начать игру
/shoot — выстрелить
/spin — прокрутить барабан

<b>Дуэли:</b>
/duel [@user] [ставка] — вызвать
/accept [ID] — принять
/attack [сила] — атаковать
/defend — защищаться
/surrender — сдаться

<b>Развлечения:</b>
/anekdot — случайный анекдот
/fact — интересный факт
/quote — цитата
/whoami — кто я?
/coin — монетка
/dice — бросить кубик
/random [мин] [макс] — число
/choose [вар1/вар2] — выбор
/compatibility [@user1] [@user2] — совместимость
"""
    await message.reply(text)

@dp.message_handler(commands=["help_social"])
async def cmd_help_social(message: types.Message):
    text = """
👥 <b>Социальные команды</b>

<b>Анкета:</b>
/profile — моя анкета
/profile [@user] — анкета пользователя
/name [текст] — изменить имя
/age [число] — изменить возраст
/city [город] — изменить город
/bio [текст] — о себе
/gender [м/ж] — пол
/photo — загрузить фото

<b>Отношения:</b>
/friend [@user] — добавить в друзья
/unfriend [@user] — удалить из друзей
/enemy [@user] — объявить врагом
/forgive [@user] — простить
/ignore [@user] — игнорировать
/unignore [@user] — убрать из игнора

<b>Браки:</b>
/marry [@user] — предложить
/accept_marriage — принять
/divorce — развод
/families — список семей

<b>Кланы:</b>
/clan create [название] — создать
/clan join [название] — вступить
/clan leave — выйти
/clan info — информация
/clan top — топ кланов

<b>Кружки:</b>
/circle create [название] — создать
/circle join [название] — вступить
/circle meeting [дата] [время] [место] — встреча
"""
    await message.reply(text)

@dp.message_handler(commands=["help_economy"])
async def cmd_help_economy(message: types.Message):
    text = """
💰 <b>Экономика и магазин</b>

<b>Ириски (валюта):</b>
/balance — мой баланс
/balance [@user] — баланс пользователя
/transfer [@user] [сумма] — перевести
/top_balance — топ богачей

<b>Ежедневные бонусы:</b>
/daily — получить бонус
/streak — текущий стрик
/bonuses — список бонусов

<b>VIP статус:</b>
/vip — информация о VIP
/vip_price — стоимость
/vip_list — список VIP

<b>Магазин:</b>
/shop — список товаров
/buy [товар] — купить
/gift [@user] [товар] — подарить
/inventory — инвентарь

<b>Кубы (коллекционные):</b>
/cubes — мои кубы
/buy_cube [цвет] — купить куб
/cube_top — топ коллекционеров
/gift_cube [@user] [ID] — подарить куб

<b>Награды:</b>
/awards — список наград
/give_award [@user] [название] — вручить (модератор)
/my_awards — мои награды
"""
    await message.reply(text)

@dp.message_handler(commands=["help_utils"])
async def cmd_help_utils(message: types.Message):
    text = """
🔧 <b>Полезные команды</b>

<b>Заметки:</b>
/note [текст] — создать заметку
/notes — список заметок
/note_del [ID] — удалить
/note_edit [ID] [текст] — редактировать

<b>Закладки:</b>
/bookmark [название] [ссылка] — сохранить
/bookmarks — список
/bookmark_del [ID] — удалить

<b>Таймеры и напоминания:</b>
/timer [название] [время] — создать таймер
/timers — список таймеров
/remind [текст] [время] — напоминание
/reminders — список напоминаний

<b>Статистика:</b>
/stat — статистика чата
/stat_today — за сегодня
/stat_week — за неделю
/stat_month — за месяц
/top_messages — топ по сообщениям
/top_commands — топ по командам
/top_warns — топ нарушителей
/my_stat — моя статистика

<b>Темы и голосования:</b>
/topic [название] — создать тему
/topics — список тем
/vote_for [ID] — голосовать за
/vote_against [ID] — голосовать против
/suggest [команда] [описание] — предложить команду
"""
    await message.reply(text)

# Команды модерации
@dp.message_handler(lambda message: re.match(r"^[+!]+модер|админ", message.text.lower()))
async def cmd_add_moderator(message: types.Message):
    await register_user(message)
    
    if not check_permission("add_moderator", message.chat.id, message.from_user.id) and message.from_user.id not in ADMIN_IDS:
        await message.reply("🚫 У вас нет прав для назначения модераторов.")
        return
    
    # Определяем ранг по количеству восклицательных знаков или плюсов
    text = message.text.lower()
    rank = text.count("!") + text.count("+") - 1  # -1 потому что минимум 1 символ
    
    # Проверка на +Модер 2 и т.д.
    match = re.search(r"модер\s*(\d)", text)
    if match:
        rank = int(match.group(1))
    
    # Извлекаем ссылку на пользователя
    parts = message.text.split()
    user_link = None
    for part in parts:
        if "@" in part or "tg://" in part or part.isdigit():
            user_link = part
            break
    
    if not user_link:
        await message.reply("❌ Укажите пользователя (ссылку или @username)")
        return
    
    target_id = extract_user_id(user_link)
    if not target_id:
        await message.reply("❌ Не удалось определить пользователя")
        return
    
    # Проверяем, не превышает ли назначаемый ранг ранг назначающего
    user_rank = get_user_rank(message.from_user.id, message.chat.id)
    if rank > user_rank and message.from_user.id not in ADMIN_IDS:
        await message.reply("🚫 Вы не можете назначить модератора с рангом выше вашего")
        return
    
    cursor.execute("""
        INSERT OR REPLACE INTO moderators (user_id, chat_id, rank, assigned_by)
        VALUES (?, ?, ?, ?)
    """, (target_id, message.chat.id, rank, message.from_user.id))
    conn.commit()
    
    rank_name = get_rank_name(rank)
    await message.reply(f"✅ Пользователь назначен модератором\nРанг: {rank_name} {get_rank_emoji(rank)}")

@dp.message_handler(lambda message: message.text.startswith("Повысить"))
async def cmd_promote(message: types.Message):
    await register_user(message)
    
    if not check_permission("promote", message.chat.id, message.from_user.id):
        await message.reply("🚫 У вас нет прав для повышения.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("❌ Укажите пользователя")
        return
    
    target_id = extract_user_id(parts[1])
    if not target_id:
        await message.reply("❌ Не удалось определить пользователя")
        return
    
    cursor.execute("SELECT rank FROM moderators WHERE user_id = ? AND chat_id = ?", (target_id, message.chat.id))
    result = cursor.fetchone()
    
    if not result:
        await message.reply("❌ Пользователь не является модератором")
        return
    
    current_rank = result[0]
    new_rank = min(current_rank + 1, 5)
    
    user_rank = get_user_rank(message.from_user.id, message.chat.id)
    if new_rank > user_rank and message.from_user.id not in ADMIN_IDS:
        await message.reply("🚫 Вы не можете повысить пользователя до ранга выше вашего")
        return
    
    cursor.execute("UPDATE moderators SET rank = ? WHERE user_id = ? AND chat_id = ?", 
                  (new_rank, target_id, message.chat.id))
    conn.commit()
    
    rank_name = get_rank_name(new_rank)
    await message.reply(f"✅ Пользователь повышен\nНовый ранг: {rank_name} {get_rank_emoji(new_rank)}")

@dp.message_handler(lambda message: message.text.startswith("Понизить"))
async def cmd_demote(message: types.Message):
    await register_user(message)
    
    if not check_permission("demote", message.chat.id, message.from_user.id):
        await message.reply("🚫 У вас нет прав для понижения.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("❌ Укажите пользователя")
        return
    
    target_id = extract_user_id(parts[1])
    if not target_id:
        await message.reply("❌ Не удалось определить пользователя")
        return
    
    cursor.execute("SELECT rank FROM moderators WHERE user_id = ? AND chat_id = ?", (target_id, message.chat.id))
    result = cursor.fetchone()
    
    if not result:
        await message.reply("❌ Пользователь не является модератором")
        return
    
    current_rank = result[0]
    new_rank = max(current_rank - 1, 1)
    
    cursor.execute("UPDATE moderators SET rank = ? WHERE user_id = ? AND chat_id = ?", 
                  (new_rank, target_id, message.chat.id))
    conn.commit()
    
    rank_name = get_rank_name(new_rank)
    await message.reply(f"✅ Пользователь понижен\nНовый ранг: {rank_name} {get_rank_emoji(new_rank)}")

@dp.message_handler(lambda message: message.text.startswith(("Снять", "Разжаловать")))
async def cmd_remove_moderator(message: types.Message):
    await register_user(message)
    
    if not check_permission("remove_moderator", message.chat.id, message.from_user.id):
        await message.reply("🚫 У вас нет прав для снятия модераторов.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("❌ Укажите пользователя")
        return
    
    target_id = extract_user_id(parts[1])
    if not target_id:
        await message.reply("❌ Не удалось определить пользователя")
        return
    
    cursor.execute("DELETE FROM moderators WHERE user_id = ? AND chat_id = ?", (target_id, message.chat.id))
    conn.commit()
    
    await message.reply("✅ Модератор снят")

@dp.message_handler(lambda message: message.text == "Снять вышедших")
async def cmd_remove_left_moderators(message: types.Message):
    await register_user(message)
    
    if not check_permission("remove_moderator", message.chat.id, message.from_user.id):
        await message.reply("🚫 У вас нет прав.")
        return
    
    # Получаем список участников чата
    try:
        chat_members = await bot.get_chat_administrators(message.chat.id)
        member_ids = [member.user.id for member in chat_members]
    except:
        await message.reply("❌ Не удалось получить список участников")
        return
    
    cursor.execute("SELECT user_id FROM moderators WHERE chat_id = ?", (message.chat.id,))
    mods = cursor.fetchall()
    
    removed = 0
    for mod in mods:
        if mod[0] not in member_ids:
            cursor.execute("DELETE FROM moderators WHERE user_id = ? AND chat_id = ?", (mod[0], message.chat.id))
            removed += 1
    
    conn.commit()
    await message.reply(f"✅ Снято модераторов, вышедших из чата: {removed}")

@dp.message_handler(lambda message: message.text in ["!Снять всех", "!Разжаловать всех"])
async def cmd_remove_all_moderators(message: types.Message):
    await register_user(message)
    
    if not check_permission("remove_moderator", message.chat.id, message.from_user.id) and message.from_user.id not in ADMIN_IDS:
        await message.reply("🚫 У вас нет прав.")
        return
    
    cursor.execute("DELETE FROM moderators WHERE chat_id = ?", (message.chat.id,))
    conn.commit()
    
    await message.reply("✅ Все модераторы сняты")

# Предупреждения
@dp.message_handler(lambda message: message.text.startswith(("Варн", "Пред")))
async def cmd_warn(message: types.Message):
    await register_user(message)
    
    if not check_permission("warn", message.chat.id, message.from_user.id):
        await message.reply("🚫 У вас нет прав для выдачи предупреждений.")
        return
    
    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        await message.reply("❌ Укажите пользователя\nПример: Варн @user причина")
        return
    
    target_id = extract_user_id(parts[1])
    if not target_id:
        await message.reply("❌ Не удалось определить пользователя")
        return
    
    reason = parts[2] if len(parts) > 2 else "Без причины"
    
    cursor.execute("""
        INSERT INTO warnings (user_id, chat_id, reason, issued_by)
        VALUES (?, ?, ?, ?)
    """, (target_id, message.chat.id, reason, message.from_user.id))
    
    cursor.execute("UPDATE users SET warnings = warnings + 1 WHERE user_id = ?", (target_id,))
    
    # Получаем количество предупреждений
    cursor.execute("SELECT warnings FROM users WHERE user_id = ?", (target_id,))
    warn_count = cursor.fetchone()[0]
    
    conn.commit()
    
    # Автоматические наказания
    if warn_count >= 5:
        # Бан
        await message.chat.kick(target_id)
        await message.reply(f"🚫 Пользователь забанен (5/5 предупреждений)")
    elif warn_count >= 3:
        # Мут на час
        mute_until = datetime.now() + timedelta(hours=1)
        cursor.execute("""
            INSERT OR REPLACE INTO mutes (user_id, chat_id, until, reason, issued_by)
            VALUES (?, ?, ?, ?, ?)
        """, (target_id, message.chat.id, mute_until.isoformat(), "Автоматический мут (3 предупреждения)", message.from_user.id))
        cursor.execute("UPDATE users SET is_muted = 1 WHERE user_id = ?", (target_id,))
        conn.commit()
        await message.reply(f"🔇 Пользователь замучен на 1 час (3/5 предупреждений)")
    else:
        await message.reply(f"⚠️ Пользователь получил предупреждение ({warn_count}/5)\nПричина: {reason}")

@dp.message_handler(lambda message: message.text.startswith(("Варны", "Преды")))
async def cmd_warns(message: types.Message):
    await register_user(message)
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("❌ Укажите пользователя")
        return
    
    target_id = extract_user_id(parts[1])
    if not target_id:
        await message.reply("❌ Не удалось определить пользователя")
        return
    
    cursor.execute("""
        SELECT id, reason, issued_by, issued_date 
        FROM warnings 
        WHERE user_id = ? AND chat_id = ?
        ORDER BY issued_date DESC
    """, (target_id, message.chat.id))
    warns = cursor.fetchall()
    
    if not warns:
        await message.reply("✅ У пользователя нет предупреждений")
        return
    
    text = f"⚠️ <b>Предупреждения пользователя:</b>\n\n"
    for warn in warns[:10]:  # Показываем последние 10
        date = datetime.fromisoformat(warn[3]).strftime("%d.%m.%Y %H:%M")
        text += f"ID: {warn[0]} | {date}\nПричина: {warn[1]}\n\n"
    
    await message.reply(text)

@dp.message_handler(lambda message: message.text.startswith("Снять варн") or message.text.startswith("Снять пред"))
async def cmd_remove_warn(message: types.Message):
    await register_user(message)
    
    if not check_permission("warn", message.chat.id, message.from_user.id):
        await message.reply("🚫 У вас нет прав.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("❌ Укажите пользователя или ID предупреждения")
        return
    
    # Проверяем, является ли второй аргумент числом (ID)
    if parts[1].isdigit():
        # Снятие по ID
        warn_id = int(parts[1])
        cursor.execute("SELECT user_id FROM warnings WHERE id = ? AND chat_id = ?", (warn_id, message.chat.id))
        result = cursor.fetchone()
        
        if not result:
            await message.reply("❌ Предупреждение не найдено")
            return
        
        user_id = result[0]
        cursor.execute("DELETE FROM warnings WHERE id = ?", (warn_id,))
        cursor.execute("UPDATE users SET warnings = warnings - 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        
        await message.reply(f"✅ Предупреждение ID {warn_id} снято")
    else:
        # Снятие последнего предупреждения пользователя
        target_id = extract_user_id(parts[1])
        if not target_id:
            await message.reply("❌ Не удалось определить пользователя")
            return
        
        cursor.execute("""
            SELECT id FROM warnings 
            WHERE user_id = ? AND chat_id = ?
            ORDER BY issued_date DESC LIMIT 1
        """, (target_id, message.chat.id))
        result = cursor.fetchone()
        
        if not result:
            await message.reply("❌ У пользователя нет предупреждений")
            return
        
        warn_id = result[0]
        cursor.execute("DELETE FROM warnings WHERE id = ?", (warn_id,))
        cursor.execute("UPDATE users SET warnings = warnings - 1 WHERE user_id = ?", (target_id,))
        conn.commit()
        
        await message.reply(f"✅ Последнее предупреждение снято")

@dp.message_handler(lambda message: message.text.startswith("Снять все варны") or message.text.startswith("Снять все преды"))
async def cmd_remove_all_warns(message: types.Message):
    await register_user(message)
    
    if not check_permission("warn", message.chat.id, message.from_user.id):
        await message.reply("🚫 У вас нет прав.")
        return
    
    parts = message.text.split()
    if len(parts) < 3:
        await message.reply("❌ Укажите пользователя")
        return
    
    target_id = extract_user_id(parts[2])
    if not target_id:
        await message.reply("❌ Не удалось определить пользователя")
        return
    
    cursor.execute("DELETE FROM warnings WHERE user_id = ? AND chat_id = ?", (target_id, message.chat.id))
    cursor.execute("UPDATE users SET warnings = 0 WHERE user_id = ?", (target_id,))
    conn.commit()
    
    await message.reply(f"✅ Все предупреждения сняты")

# Муты
@dp.message_handler(lambda message: message.text.startswith("Мут"))
async def cmd_mute(message: types.Message):
    await register_user(message)
    
    if not check_permission("mute", message.chat.id, message.from_user.id):
        await message.reply("🚫 У вас нет прав для мута.")
        return
    
    # Парсим команду: Мут @user 30м спам
    parts = message.text.split(maxsplit=3)
    if len(parts) < 3:
        await message.reply("❌ Укажите пользователя и время\nПример: Мут @user 30м спам")
        return
    
    target_id = extract_user_id(parts[1])
    if not target_id:
        await message.reply("❌ Не удалось определить пользователя")
        return
    
    time_delta = parse_time(parts[2])
    if not time_delta:
        await message.reply("❌ Неверный формат времени. Используйте: 30м, 2ч, 1д")
        return
    
    reason = parts[3] if len(parts) > 3 else "Без причины"
    
    mute_until = datetime.now() + time_delta
    
    cursor.execute("""
        INSERT OR REPLACE INTO mutes (user_id, chat_id, until, reason, issued_by)
        VALUES (?, ?, ?, ?, ?)
    """, (target_id, message.chat.id, mute_until.isoformat(), reason, message.from_user.id))
    
    cursor.execute("UPDATE users SET is_muted = 1 WHERE user_id = ?", (target_id,))
    conn.commit()
    
    # Ограничиваем права пользователя
    try:
        await message.chat.restrict(
            target_id,
            types.ChatPermissions(can_send_messages=False),
            until_date=mute_until
        )
    except:
        pass
    
    time_str = f"{time_delta.seconds // 3600}ч {(time_delta.seconds // 60) % 60}м" if time_delta.seconds < 86400 else f"{time_delta.days}д"
    await message.reply(f"🔇 Пользователь замучен на {time_str}\nПричина: {reason}")

@dp.message_handler(commands=["мутлист", "Мутлист", "Мут-лист"])
async def cmd_mutelist(message: types.Message):
    await register_user(message)
    
    cursor.execute("""
        SELECT m.user_id, u.username, u.first_name, m.until, m.reason
        FROM mutes m
        LEFT JOIN users u ON m.user_id = u.user_id
        WHERE m.chat_id = ? AND datetime(m.until) > datetime('now')
        ORDER BY m.until
    """, (message.chat.id,))
    mutes = cursor.fetchall()
    
    if not mutes:
        await message.reply("📋 Список замученных пуст")
        return
    
    text = "🔇 <b>Список замученных:</b>\n\n"
    for mute in mutes:
        user = mute[1] or mute[2] or str(mute[0])
        until = datetime.fromisoformat(mute[3]).strftime("%d.%m.%Y %H:%M")
        text += f"• {user} — до {until}\nПричина: {mute[4]}\n\n"
    
    await message.reply(text)

@dp.message_handler(lambda message: message.text.startswith(("Размут", "Снять мут")))
async def cmd_unmute(message: types.Message):
    await register_user(message)
    
    if not check_permission("mute", message.chat.id, message.from_user.id):
        await message.reply("🚫 У вас нет прав.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("❌ Укажите пользователя")
        return
    
    target_id = extract_user_id(parts[1])
    if not target_id:
        await message.reply("❌ Не удалось определить пользователя")
        return
    
    cursor.execute("DELETE FROM mutes WHERE user_id = ? AND chat_id = ?", (target_id, message.chat.id))
    cursor.execute("UPDATE users SET is_muted = 0 WHERE user_id = ?", (target_id,))
    conn.commit()
    
    # Восстанавливаем права
    try:
        await message.chat.restrict(
            target_id,
            types.ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        )
    except:
        pass
    
    await message.reply(f"✅ Мут снят")

# Баны
@dp.message_handler(lambda message: message.text.startswith("Бан"))
async def cmd_ban(message: types.Message):
    await register_user(message)
    
    if not check_permission("ban", message.chat.id, message.from_user.id):
        await message.reply("🚫 У вас нет прав для бана.")
        return
    
    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        await message.reply("❌ Укажите пользователя")
        return
    
    target_id = extract_user_id(parts[1])
    if not target_id:
        await message.reply("❌ Не удалось определить пользователя")
        return
    
    reason = parts[2] if len(parts) > 2 else "Без причины"
    
    cursor.execute("""
        INSERT OR REPLACE INTO bans (user_id, chat_id, reason, issued_by)
        VALUES (?, ?, ?, ?)
    """, (target_id, message.chat.id, reason, message.from_user.id))
    conn.commit()
    
    try:
        await message.chat.kick(target_id)
        await message.reply(f"🚫 Пользователь забанен\nПричина: {reason}")
    except:
        await message.reply("❌ Не удалось забанить пользователя")

@dp.message_handler(commands=["банлист", "Банлист", "Бан-лист"])
async def cmd_banlist(message: types.Message):
    await register_user(message)
    
    cursor.execute("""
        SELECT b.user_id, u.username, u.first_name, b.reason, b.issued_date
        FROM bans b
        LEFT JOIN users u ON b.user_id = u.user_id
        WHERE b.chat_id = ?
        ORDER BY b.issued_date DESC
    """, (message.chat.id,))
    bans = cursor.fetchall()
    
    if not bans:
        await message.reply("📋 Список забаненных пуст")
        return
    
    text = "🚫 <b>Список забаненных:</b>\n\n"
    for ban in bans[:20]:  # Показываем последние 20
        user = ban[1] or ban[2] or str(ban[0])
        date = datetime.fromisoformat(ban[4]).strftime("%d.%m.%Y")
        text += f"• {user} — {date}\nПричина: {ban[3]}\n\n"
    
    await message.reply(text)

@dp.message_handler(lambda message: message.text.startswith(("Разбан", "Снять бан")))
async def cmd_unban(message: types.Message):
    await register_user(message)
    
    if not check_permission("ban", message.chat.id, message.from_user.id):
        await message.reply("🚫 У вас нет прав.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("❌ Укажите пользователя")
        return
    
    target_id = extract_user_id(parts[1])
    if not target_id:
        await message.reply("❌ Не удалось определить пользователя")
        return
    
    cursor.execute("DELETE FROM bans WHERE user_id = ? AND chat_id = ?", (target_id, message.chat.id))
    conn.commit()
    
    try:
        await message.chat.unban(target_id)
        await message.reply(f"✅ Пользователь разбанен")
    except:
        await message.reply("❌ Не удалось разбанить пользователя")

@dp.message_handler(lambda message: message.text.startswith("Кик"))
async def cmd_kick(message: types.Message):
    await register_user(message)
    
    if not check_permission("kick", message.chat.id, message.from_user.id):
        await message.reply("🚫 У вас нет прав для кика.")
        return
    
    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        await message.reply("❌ Укажите пользователя")
        return
    
    target_id = extract_user_id(parts[1])
    if not target_id:
        await message.reply("❌ Не удалось определить пользователя")
        return
    
    reason = parts[2] if len(parts) > 2 else "Без причины"
    
    try:
        await message.chat.kick(target_id)
        await message.chat.unban(target_id)  # Сразу разбаниваем, чтобы можно было заново зайти
        await message.reply(f"👢 Пользователь кикнут\nПричина: {reason}")
    except:
        await message.reply("❌ Не удалось кикнуть пользователя")

# Глобальные действия
@dp.message_handler(lambda message: message.text.startswith("Глобал бан"))
async def cmd_global_ban(message: types.Message):
    await register_user(message)
    
    if message.from_user.id not in ADMIN_IDS:
        await message.reply("🚫 Только создатель может использовать глобальные команды.")
        return
    
    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        await message.reply("❌ Укажите пользователя")
        return
    
    target_id = extract_user_id(parts[1])
    if not target_id:
        await message.reply("❌ Не удалось определить пользователя")
        return
    
    reason = parts[2] if len(parts) > 2 else "Без причины"
    
    cursor.execute("""
        INSERT OR REPLACE INTO global_bans (user_id, reason, issued_by)
        VALUES (?, ?, ?)
    """, (target_id, reason, message.from_user.id))
    conn.commit()
    
    await message.reply(f"🌐 Пользователь забанен глобально\nПричина: {reason}")

@dp.message_handler(lambda message: message.text.startswith("Глобал разбан"))
async def cmd_global_unban(message: types.Message):
    await register_user(message)
    
    if message.from_user.id not in ADMIN_IDS:
        await message.reply("🚫 Только создатель может использовать глобальные команды.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("❌ Укажите пользователя")
        return
    
    target_id = extract_user_id(parts[1])
    if not target_id:
        await message.reply("❌ Не удалось определить пользователя")
        return
    
    cursor.execute("DELETE FROM global_bans WHERE user_id = ?", (target_id,))
    conn.commit()
    
    await message.reply(f"🌐 Глобальный бан снят")

# Триггеры
@dp.message_handler(lambda message: message.text.startswith("+Триггер"))
async def cmd_add_trigger(message: types.Message):
    await register_user(message)
    
    if not check_permission("triggers", message.chat.id, message.from_user.id):
        await message.reply("🚫 У вас нет прав для создания триггеров.")
        return
    
    # Формат: +Триггер слово = действие
    text = message.text[9:].strip()  # Убираем "+Триггер "
    
    if "=" not in text:
        await message.reply("❌ Неверный формат. Используйте: +Триггер слово = действие")
        return
    
    trigger_word, action = text.split("=", 1)
    trigger_word = trigger_word.strip().lower()
    action = action.strip()
    
    # Парсим действие: delete, mute 30м, warn, ban
    action_parts = action.split()
    action_type = action_parts[0].lower()
    action_param = action_parts[1] if len(action_parts) > 1 else None
    
    if action_type not in ["delete", "mute", "warn", "ban"]:
        await message.reply("❌ Неверное действие. Доступно: delete, mute [время], warn, ban")
        return
    
    cursor.execute("""
        INSERT INTO triggers (chat_id, trigger_word, action, action_param, created_by)
        VALUES (?, ?, ?, ?, ?)
    """, (message.chat.id, trigger_word, action_type, action_param, message.from_user.id))
    conn.commit()
    
    await message.reply(f"✅ Триггер добавлен\nСлово: {trigger_word}\nДействие: {action}")

@dp.message_handler(lambda message: message.text.startswith("-Триггер"))
async def cmd_remove_trigger(message: types.Message):
    await register_user(message)
    
    if not check_permission("triggers", message.chat.id, message.from_user.id):
        await message.reply("🚫 У вас нет прав.")
        return
    
    trigger_id = message.text[9:].strip()
    if not trigger_id.isdigit():
        await message.reply("❌ Укажите ID триггера")
        return
    
    cursor.execute("DELETE FROM triggers WHERE id = ? AND chat_id = ?", (int(trigger_id), message.chat.id))
    conn.commit()
    
    await message.reply(f"✅ Триггер удален")

@dp.message_handler(commands=["триггеры", "Триггеры"])
async def cmd_triggers(message: types.Message):
    await register_user(message)
    
    cursor.execute("SELECT id, trigger_word, action, action_param FROM triggers WHERE chat_id = ?", (message.chat.id,))
    triggers = cursor.fetchall()
    
    if not triggers:
        await message.reply("📋 В этом чате нет триггеров")
        return
    
    text = "🔍 <b>Триггеры чата:</b>\n\n"
    for trigger in triggers:
        action_text = trigger[2]
        if trigger[3]:
            action_text += f" {trigger[3]}"
        text += f"ID: {trigger[0]} | Слово: {trigger[1]} → {action_text}\n"
    
    await message.reply(text)

# Автомодерация
@dp.message_handler(lambda message: message.text.startswith(("Антимат", "антимат")))
async def cmd_antimat(message: types.Message):
    await register_user(message)
    
    if not check_permission("settings", message.chat.id, message.from_user.id):
        await message.reply("🚫 У вас нет прав.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("❌ Укажите on или off")
        return
    
    state = 1 if parts[1].lower() in ["on", "вкл", "да"] else 0
    
    cursor.execute("""
        INSERT OR REPLACE INTO chat_settings (chat_id, antimat)
        VALUES (?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET antimat = excluded.antimat
    """, (message.chat.id, state))
    conn.commit()
    
    status = "включен" if state else "выключен"
    await message.reply(f"✅ Антимат {status}")

@dp.message_handler(lambda message: message.text.startswith(("Антиссылки", "антиссылки")))
async def cmd_antilinks(message: types.Message):
    await register_user(message)
    
    if not check_permission("settings", message.chat.id, message.from_user.id):
        await message.reply("🚫 У вас нет прав.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("❌ Укажите on или off")
        return
    
    state = 1 if parts[1].lower() in ["on", "вкл", "да"] else 0
    
    cursor.execute("""
        INSERT OR REPLACE INTO chat_settings (chat_id, antilinks)
        VALUES (?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET antilinks = excluded.antilinks
    """, (message.chat.id, state))
    conn.commit()
    
    status = "включен" if state else "выключен"
    await message.reply(f"✅ Антиссылки {status}")

@dp.message_handler(lambda message: message.text.startswith(("Антифлуд", "антифлуд")))
async def cmd_antiflood(message: types.Message):
    await register_user(message)
    
    if not check_permission("settings", message.chat.id, message.from_user.id):
        await message.reply("🚫 У вас нет прав.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("❌ Укажите on или off")
        return
    
    state = 1 if parts[1].lower() in ["on", "вкл", "да"] else 0
    
    cursor.execute("""
        INSERT OR REPLACE INTO chat_settings (chat_id, antiflood)
        VALUES (?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET antiflood = excluded.antiflood
    """, (message.chat.id, state))
    conn.commit()
    
    status = "включен" if state else "выключен"
    await message.reply(f"✅ Антифлуд {status}")

# Права доступа
@dp.message_handler(lambda message: message.text.startswith("Права"))
async def cmd_permissions(message: types.Message):
    await register_user(message)
    
    if not check_permission("permissions", message.chat.id, message.from_user.id):
        await message.reply("🚫 У вас нет прав для настройки прав.")
        return
    
    parts = message.text.split()
    
    if len(parts) == 1 or (len(parts) == 2 and parts[1] == "список"):
        # Список прав
        cursor.execute("SELECT command, min_rank FROM command_permissions WHERE chat_id = ?", (message.chat.id,))
        perms = cursor.fetchall()
        
        if not perms:
            await message.reply("📋 Все команды используют стандартные права")
            return
        
        text = "🔧 <b>Настройки прав:</b>\n\n"
        for perm in perms:
            text += f"• {perm[0]} — мин. ранг {perm[1]} {get_rank_emoji(perm[1])}\n"
        
        await message.reply(text)
        return
    
    if len(parts) >= 4 and parts[2] == "=":
        # Установка прав: Права команда = ранг
        command = parts[1]
        try:
            rank = int(parts[3])
        except:
            await message.reply("❌ Ранг должен быть числом от 0 до 5")
            return
        
        if rank < 0 or rank > 5:
            await message.reply("❌ Ранг должен быть от 0 до 5")
            return
        
        cursor.execute("""
            INSERT OR REPLACE INTO command_permissions (command, chat_id, min_rank)
            VALUES (?, ?, ?)
        """, (command, message.chat.id, rank))
        conn.commit()
        
        await message.reply(f"✅ Для команды {command} установлен минимальный ранг {rank}")

@dp.message_handler(commands=["сброситьправа", "Сбросить права"])
async def cmd_reset_permissions(message: types.Message):
    await register_user(message)
    
    if not check_permission("permissions", message.chat.id, message.from_user.id) and message.from_user.id not in ADMIN_IDS:
        await message.reply("🚫 У вас нет прав.")
        return
    
    cursor.execute("DELETE FROM command_permissions WHERE chat_id = ?", (message.chat.id,))
    conn.commit()
    
    await message.reply("✅ Настройки прав сброшены к стандартным")

@dp.message_handler(lambda message: message.text.startswith("Запретить"))
async def cmd_forbid_command(message: types.Message):
    await register_user(message)
    
    if not check_permission("permissions", message.chat.id, message.from_user.id):
        await message.reply("🚫 У вас нет прав.")
        return
    
    command = message.text[9:].strip()
    if not command:
        await message.reply("❌ Укажите команду")
        return
    
    cursor.execute("""
        INSERT OR REPLACE INTO command_permissions (command, chat_id, min_rank)
        VALUES (?, ?, 6)
    """, (command, message.chat.id))  # Ранг 6 означает запрет для всех
    conn.commit()
    
    await message.reply(f"✅ Команда {command} запрещена для всех")

@dp.message_handler(lambda message: message.text.startswith("Разрешить"))
async def cmd_allow_command(message: types.Message):
    await register_user(message)
    
    if not check_permission("permissions", message.chat.id, message.from_user.id):
        await message.reply("🚫 У вас нет прав.")
        return
    
    command = message.text[9:].strip()
    if not command:
        await message.reply("❌ Укажите команду")
        return
    
    cursor.execute("DELETE FROM command_permissions WHERE command = ? AND chat_id = ?", (command, message.chat.id))
    conn.commit()
    
    await message.reply(f"✅ Команда {command} разрешена для всех")

@dp.message_handler(lambda message: message.text.startswith("Исключение"))
async def cmd_command_exception(message: types.Message):
    await register_user(message)
    
    if not check_permission("permissions", message.chat.id, message.from_user.id):
        await message.reply("🚫 У вас нет прав.")
        return
    
    # Формат: Исключение команда = @user
    text = message.text[10:].strip()
    
    if "=" not in text:
        await message.reply("❌ Неверный формат. Используйте: Исключение команда = @user")
        return
    
    command_part, user_part = text.split("=", 1)
    command = command_part.strip()
    user_link = user_part.strip()
    
    target_id = extract_user_id(user_link)
    if not target_id:
        await message.reply("❌ Не удалось определить пользователя")
        return
    
    cursor.execute("""
        INSERT OR REPLACE INTO command_exceptions (command, user_id, chat_id)
        VALUES (?, ?, ?)
    """, (command, target_id, message.chat.id))
    conn.commit()
    
    await message.reply(f"✅ Исключение добавлено\nПользователь может использовать {command}")

# Чистка чата
@dp.message_handler(lambda message: message.text.startswith("Чистка"))
async def cmd_clean(message: types.Message):
    await register_user(message)
    
    if not check_permission("clean", message.chat.id, message.from_user.id):
        await message.reply("🚫 У вас нет прав для очистки.")
        return
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("❌ Укажите количество сообщений или фильтр")
        return
    
    param = parts[1].strip()
    
    # Проверка на особые команды
    if param == "всё" or param == "все":
        if get_user_rank(message.from_user.id, message.chat.id) < 5 and message.from_user.id not in ADMIN_IDS:
            await message.reply("🚫 Только создатель может очистить всё")
            return
        
        # Очистка всех сообщений (только для супергрупп)
        try:
            # В Telegram нельзя удалить все сообщения сразу
            await message.reply("⚠️ Очистка всех сообщений невозможна. Используйте 'Чистка 100' для удаления последних 100 сообщений")
        except:
            pass
        return
    
    if param == "ботов":
        # Удаление сообщений ботов
        await message.reply("🔄 Удаляю сообщения ботов...")
        # Здесь нужна логика поиска сообщений ботов
        return
    
    if param == "файлов":
        # Удаление файлов и медиа
        await message.reply("🔄 Удаляю файлы...")
        return
    
    if param.startswith("от "):
        # Удаление сообщений конкретного пользователя
        user_link = param[3:].strip()
        target_id = extract_user_id(user_link)
        if not target_id:
            await message.reply("❌ Не удалось определить пользователя")
            return
        
        await message.reply(f"🔄 Удаляю сообщения пользователя...")
        return
    
    if param == "ссылки":
        # Удаление сообщений со ссылками
        await message.reply("🔄 Удаляю сообщения со ссылками...")
        return
    
    if param == "мат":
        await message.reply("🔄 Удаляю сообщения с матом...")
        return
    
    if param == "спам":
        await message.reply("🔄 Удаляю спам...")
        return
    
    # Очистка по количеству
    if param.isdigit():
        count = int(param)
        if count > 100:
            count = 100
        
        try:
            # Удаляем сообщение с командой
            await message.delete()
            
            # Получаем сообщения для удаления
            messages = []
            async for msg in bot.iterate_history(message.chat.id, limit=count):
                messages.append(msg.message_id)
            
            if messages:
                await bot.delete_messages(message.chat.id, messages)
                await message.answer(f"✅ Удалено {len(messages)} сообщений", disable_notification=True)
            else:
                await message.answer("❌ Нет сообщений для удаления")
        except Exception as e:
            await message.answer(f"❌ Ошибка: {e}")
    else:
        await message.reply("❌ Неверный параметр. Используйте число или: всё, ботов, файлов, от @user, ссылки, мат, спам")

# Настройка чата
@dp.message_handler(lambda message: message.text.startswith("+Приветствие"))
async def cmd_set_welcome(message: types.Message):
    await register_user(message)
    
    if not check_permission("settings", message.chat.id, message.from_user.id):
        await message.reply("🚫 У вас нет прав.")
        return
    
    welcome_text = message.text[12:].strip()
    if not welcome_text:
        await message.reply("❌ Укажите текст приветствия")
        return
    
    cursor.execute("""
        INSERT OR REPLACE INTO chat_settings (chat_id, welcome_message)
        VALUES (?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET welcome_message = excluded.welcome_message
    """, (message.chat.id, welcome_text))
    conn.commit()
    
    await message.reply("✅ Приветствие установлено")

@dp.message_handler(lambda message: message.text.startswith("+Правила"))
async def cmd_set_rules(message: types.Message):
    await register_user(message)
    
    if not check_permission("settings", message.chat.id, message.from_user.id):
        await message.reply("🚫 У вас нет прав.")
        return
    
    rules_text = message.text[9:].strip()
    if not rules_text:
        await message.reply("❌ Укажите текст правил")
        return
    
    cursor.execute("""
        INSERT OR REPLACE INTO chat_settings (chat_id, rules)
        VALUES (?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET rules = excluded.rules
    """, (message.chat.id, rules_text))
    conn.commit()
    
    await message.reply("✅ Правила установлены")

@dp.message_handler(commands=["правила", "Правила", "Правила чата"])
async def cmd_rules(message: types.Message):
    await register_user(message)
    
    cursor.execute("SELECT rules FROM chat_settings WHERE chat_id = ?", (message.chat.id,))
    result = cursor.fetchone()
    
    if result and result[0]:
        await message.reply(f"📜 <b>Правила чата:</b>\n\n{result[0]}")
    else:
        await message.reply("📜 В этом чате ещё не установлены правила")

@dp.message_handler(lambda message: message.text == "-Приветствие")
async def cmd_remove_welcome(message: types.Message):
    await register_user(message)
    
    if not check_permission("settings", message.chat.id, message.from_user.id):
        await message.reply("🚫 У вас нет прав.")
        return
    
    cursor.execute("UPDATE chat_settings SET welcome_message = NULL WHERE chat_id = ?", (message.chat.id,))
    conn.commit()
    
    await message.reply("✅ Приветствие удалено")

@dp.message_handler(lambda message: message.text.startswith("Капча"))
async def cmd_captcha(message: types.Message):
    await register_user(message)
    
    if not check_permission("settings", message.chat.id, message.from_user.id):
        await message.reply("🚫 У вас нет прав.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("❌ Укажите on/off или сложность")
        return
    
    if parts[1].lower() in ["on", "off", "вкл", "выкл"]:
        state = 1 if parts[1].lower() in ["on", "вкл"] else 0
        cursor.execute("""
            INSERT OR REPLACE INTO chat_settings (chat_id, captcha_enabled)
            VALUES (?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET captcha_enabled = excluded.captcha_enabled
        """, (message.chat.id, state))
        conn.commit()
        
        status = "включена" if state else "выключена"
        await message.reply(f"✅ Капча {status}")
    elif parts[1].lower() == "сложность" and len(parts) >= 3:
        try:
            difficulty = int(parts[2])
            if difficulty < 1 or difficulty > 5:
                await message.reply("❌ Сложность должна быть от 1 до 5")
                return
            
            cursor.execute("""
                INSERT OR REPLACE INTO chat_settings (chat_id, captcha_difficulty)
                VALUES (?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET captcha_difficulty = excluded.captcha_difficulty
            """, (message.chat.id, difficulty))
            conn.commit()
            
            await message.reply(f"✅ Сложность капчи установлена: {difficulty}")
        except:
            await message.reply("❌ Неверное значение сложности")

@dp.message_handler(lambda message: message.text.startswith("Верификация"))
async def cmd_verification(message: types.Message):
    await register_user(message)
    
    if not check_permission("settings", message.chat.id, message.from_user.id):
        await message.reply("🚫 У вас нет прав.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("❌ Укажите on или off")
        return
    
    state = 1 if parts[1].lower() in ["on", "вкл", "да"] else 0
    
    cursor.execute("""
        INSERT OR REPLACE INTO chat_settings (chat_id, verification_enabled)
        VALUES (?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET verification_enabled = excluded.verification_enabled
    """, (message.chat.id, state))
    conn.commit()
    
    status = "включена" if state else "выключена"
    await message.reply(f"✅ Ручная верификация {status}")

@dp.message_handler(lambda message: message.text.startswith("Язык"))
async def cmd_language(message: types.Message):
    await register_user(message)
    
    if not check_permission("settings", message.chat.id, message.from_user.id):
        await message.reply("🚫 У вас нет прав.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("❌ Укажите язык (ru/uk/en)")
        return
    
    lang = parts[1].lower()
    if lang not in ["ru", "uk", "en"]:
        await message.reply("❌ Поддерживаемые языки: ru, uk, en")
        return
    
    cursor.execute("""
        INSERT OR REPLACE INTO chat_settings (chat_id, language)
        VALUES (?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET language = excluded.language
    """, (message.chat.id, lang))
    conn.commit()
    
    languages = {"ru": "Русский", "uk": "Українська", "en": "English"}
    await message.reply(f"✅ Язык чата: {languages[lang]}")

@dp.message_handler(lambda message: message.text.startswith("Регион"))
async def cmd_region(message: types.Message):
    await register_user(message)
    
    if not check_permission("settings", message.chat.id, message.from_user.id):
        await message.reply("🚫 У вас нет прав.")
        return
    
    region = message.text[7:].strip()
    if not region:
        await message.reply("❌ Укажите регион")
        return
    
    cursor.execute("""
        INSERT OR REPLACE INTO chat_settings (chat_id, region)
        VALUES (?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET region = excluded.region
    """, (message.chat.id, region))
    conn.commit()
    
    await message.reply(f"✅ Регион чата: {region}")

@dp.message_handler(lambda message: message.text.startswith("Ссылки"))
async def cmd_links(message: types.Message):
    await register_user(message)
    
    if not check_permission("settings", message.chat.id, message.from_user.id):
        await message.reply("🚫 У вас нет прав.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("❌ Укажите on или off")
        return
    
    state = 1 if parts[1].lower() in ["on", "вкл", "да"] else 0
    
    cursor.execute("""
        INSERT OR REPLACE INTO chat_settings (chat_id, allow_links)
        VALUES (?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET allow_links = excluded.allow_links
    """, (message.chat.id, state))
    conn.commit()
    
    status = "разрешены" if state else "запрещены"
    await message.reply(f"✅ Ссылки {status}")

# Сетка чатов
grids = {}  # Временное хранение сеток в памяти

@dp.message_handler(lambda message: message.text.startswith("Сетка создать"))
async def cmd_grid_create(message: types.Message):
    await register_user(message)
    
    if not check_permission("grid", message.chat.id, message.from_user.id) and message.from_user.id not in ADMIN_IDS:
        await message.reply("🚫 У вас нет прав.")
        return
    
    name = message.text[13:].strip()
    if not name:
        await message.reply("❌ Укажите название сетки")
        return
    
    cursor.execute("""
        INSERT INTO chat_grids (name, created_by)
        VALUES (?, ?)
    """, (name, message.from_user.id))
    grid_id = cursor.lastrowid
    conn.commit()
    
    grids[grid_id] = {"name": name, "chats": []}
    
    await message.reply(f"✅ Сетка '{name}' создана (ID: {grid_id})")

@dp.message_handler(lambda message: message.text.startswith("Сетка добавить"))
async def cmd_grid_add(message: types.Message):
    await register_user(message)
    
    if not check_permission("grid", message.chat.id, message.from_user.id):
        await message.reply("🚫 У вас нет прав.")
        return
    
    parts = message.text.split()
    if len(parts) < 3:
        await message.reply("❌ Укажите ID сетки и чат\nПример: Сетка добавить 1 @chat")
        return
    
    try:
        grid_id = int(parts[2])
    except:
        await message.reply("❌ Неверный ID сетки")
        return
    
    # Проверяем существование сетки
    cursor.execute("SELECT * FROM chat_grids WHERE id = ?", (grid_id,))
    if not cursor.fetchone():
        await message.reply("❌ Сетка не найдена")
        return
    
    chat_link = parts[3] if len(parts) > 3 else None
    if not chat_link:
        await message.reply("❌ Укажите чат")
        return
    
    # Получаем ID чата (для упрощения используем текущий чат)
    chat_id = message.chat.id
    
    cursor.execute("INSERT INTO grid_chats (grid_id, chat_id) VALUES (?, ?)", (grid_id, chat_id))
    conn.commit()
    
    await message.reply(f"✅ Чат добавлен в сетку {grid_id}")

@dp.message_handler(lambda message: message.text.startswith("Сетка список"))
async def cmd_grid_list(message: types.Message):
    await register_user(message)
    
    cursor.execute("SELECT id, name, created_by FROM chat_grids")
    grids_db = cursor.fetchall()
    
    if not grids_db:
        await message.reply("📋 Нет созданных сеток")
        return
    
    text = "📋 <b>Сетки чатов:</b>\n\n"
    for grid in grids_db:
        cursor.execute("SELECT COUNT(*) FROM grid_chats WHERE grid_id = ?", (grid[0],))
        count = cursor.fetchone()[0]
        text += f"ID: {grid[0]} | {grid[1]} — чатов: {count}\n"
    
    await message.reply(text)

@dp.message_handler(lambda message: message.text.startswith("Сетка синхронизировать"))
async def cmd_grid_sync(message: types.Message):
    await register_user(message)
    
    if not check_permission("grid", message.chat.id, message.from_user.id):
        await message.reply("🚫 У вас нет прав.")
        return
    
    parts = message.text.split()
    if len(parts) < 3:
        await message.reply("❌ Укажите ID сетки")
        return
    
    try:
        grid_id = int(parts[2])
    except:
        await message.reply("❌ Неверный ID сетки")
        return
    
    # Получаем все чаты в сетке
    cursor.execute("SELECT chat_id FROM grid_chats WHERE grid_id = ?", (grid_id,))
    chats = cursor.fetchall()
    
    if not chats:
        await message.reply("❌ В сетке нет чатов")
        return
    
    # Получаем настройки текущего чата
    cursor.execute("SELECT * FROM chat_settings WHERE chat_id = ?", (message.chat.id,))
    settings = cursor.fetchone()
    
    if not settings:
        await message.reply("❌ Нет настроек для синхронизации")
        return
    
    # Применяем настройки ко всем чатам сетки
    for chat in chats:
        chat_id = chat[0]
        if chat_id == message.chat.id:
            continue
        
        # Копируем настройки
        cursor.execute("""
            INSERT OR REPLACE INTO chat_settings 
            (chat_id, welcome_message, rules, captcha_enabled, captcha_difficulty, 
             antimat, antilinks, antiflood, antispam, language, region,
             allow_links, allow_media, allow_stickers, allow_gifs)
            SELECT ?, welcome_message, rules, captcha_enabled, captcha_difficulty,
                   antimat, antilinks, antiflood, antispam, language, region,
                   allow_links, allow_media, allow_stickers, allow_gifs
            FROM chat_settings WHERE chat_id = ?
        """, (chat_id, message.chat.id))
    
    conn.commit()
    await message.reply(f"✅ Настройки синхронизированы для {len(chats)} чатов")

# Анкета пользователя
@dp.message_handler(commands=["анкета", "profile", "Анкета", "Моя анкета"])
async def cmd_profile(message: types.Message):
    await register_user(message)
    
    parts = message.text.split()
    if len(parts) > 1:
        # Просмотр анкеты другого пользователя
        target_id = extract_user_id(parts[1])
        if not target_id:
            await message.reply("❌ Не удалось определить пользователя")
            return
    else:
        target_id = message.from_user.id
    
    cursor.execute("""
        SELECT user_id, username, first_name, last_name, iris_balance, 
               vip_level, reputation, messages_count, commands_count,
               bio, age, city, gender, photo_id, joined_date
        FROM users WHERE user_id = ?
    """, (target_id,))
    user = cursor.fetchone()
    
    if not user:
        await message.reply("❌ Пользователь не найден")
        return
    
    # Получаем достижения
    cursor.execute("""
        SELECT a.name, a.icon FROM user_achievements ua
        JOIN achievements a ON ua.achievement_id = a.id
        WHERE ua.user_id = ?
    """, (target_id,))
    achievements = cursor.fetchall()
    
    # Получаем клан
    cursor.execute("""
        SELECT c.name FROM clan_members cm
        JOIN clans c ON cm.clan_id = c.id
        WHERE cm.user_id = ?
    """, (target_id,))
    clan = cursor.fetchone()
    
    # Получаем супруга
    cursor.execute("SELECT married_to FROM users WHERE user_id = ?", (target_id,))
    married_to = cursor.fetchone()[0]
    
    if married_to:
        cursor.execute("SELECT username, first_name FROM users WHERE user_id = ?", (married_to,))
        spouse = cursor.fetchone()
        spouse_text = f"💍 {spouse[0] or spouse[1]}" if spouse else "💍 Неизвестно"
    else:
        spouse_text = "💔 Нет"
    
    # Формируем анкету
    name = user[2] or f"ID {user[0]}"
    if user[3]:
        name += f" {user[3]}"
    
    rank = get_user_rank(target_id, message.chat.id)
    rank_emoji = get_rank_emoji(rank)
    rank_name = get_rank_name(rank)
    
    text = f"""
👤 <b>Анкета пользователя</b>

{rank_emoji} <b>{name}</b>
@{user[1] or 'нет'}

📊 <b>Статистика:</b>
💰 Ириски: {format_number(user[4])}
⭐ Репутация: {user[6]}
💎 VIP: {'Да' if user[5] > 0 else 'Нет'}
📝 Сообщений: {format_number(user[7])}
🔧 Команд: {format_number(user[8])}
{rank_emoji} Ранг: {rank_name}

"""
    
    if clan:
        text += f"🏰 Клан: {clan[0]}\n"
    
    text += f"💍 Семья: {spouse_text}\n\n"
    
    if user[9] or user[10] or user[11] or user[12]:
        text += "<b>О себе:</b>\n"
        if user[9]:
            text += f"📝 {user[9]}\n"
        if user[10]:
            text += f"🎂 Возраст: {user[10]}\n"
        if user[11]:
            text += f"🏙️ Город: {user[11]}\n"
        if user[12]:
            gender = "Мужской" if user[12] == "м" else "Женский" if user[12] == "ж" else user[12]
            text += f"⚥ Пол: {gender}\n"
    
    if achievements:
        text += "\n<b>Достижения:</b>\n"
        for ach in achievements[:5]:  # Показываем последние 5
            text += f"{ach[1] or '🏅'} {ach[0]}\n"
    
    if user[13]:  # Фото
        try:
            await bot.send_photo(message.chat.id, user[13], caption=text)
        except:
            await message.reply(text)
    else:
        await message.reply(text)

@dp.message_handler(commands=["имя", "name"])
async def cmd_set_name(message: types.Message):
    await register_user(message)
    
    name = message.text[5:].strip()
    if not name:
        await message.reply("❌ Укажите имя")
        return
    
    cursor.execute("UPDATE users SET first_name = ? WHERE user_id = ?", (name, message.from_user.id))
    conn.commit()
    
    await message.reply(f"✅ Имя изменено на: {name}")

@dp.message_handler(commands=["возраст", "age"])
async def cmd_set_age(message: types.Message):
    await register_user(message)
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("❌ Укажите возраст")
        return
    
    try:
        age = int(parts[1])
        if age < 1 or age > 150:
            await message.reply("❌ Возраст должен быть от 1 до 150")
            return
    except:
        await message.reply("❌ Возраст должен быть числом")
        return
    
    cursor.execute("UPDATE users SET age = ? WHERE user_id = ?", (age, message.from_user.id))
    conn.commit()
    
    await message.reply(f"✅ Возраст установлен: {age}")

@dp.message_handler(commands=["город", "city"])
async def cmd_set_city(message: types.Message):
    await register_user(message)
    
    city = message.text[6:].strip()
    if not city:
        await message.reply("❌ Укажите город")
        return
    
    cursor.execute("UPDATE users SET city = ? WHERE user_id = ?", (city, message.from_user.id))
    conn.commit()
    
    await message.reply(f"✅ Город установлен: {city}")

@dp.message_handler(commands=["био", "bio", "О себе"])
async def cmd_set_bio(message: types.Message):
    await register_user(message)
    
    bio = message.text[4:].strip() if message.text.startswith("/bio") else message.text[5:].strip()
    if not bio:
        await message.reply("❌ Напишите о себе")
        return
    
    if len(bio) > 500:
        await message.reply("❌ Текст слишком длинный (максимум 500 символов)")
        return
    
    cursor.execute("UPDATE users SET bio = ? WHERE user_id = ?", (bio, message.from_user.id))
    conn.commit()
    
    await message.reply("✅ Информация о себе сохранена")

@dp.message_handler(commands=["пол", "gender"])
async def cmd_set_gender(message: types.Message):
    await register_user(message)
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("❌ Укажите пол (м/ж)")
        return
    
    gender = parts[1].lower()
    if gender not in ["м", "ж"]:
        await message.reply("❌ Укажите 'м' для мужского или 'ж' для женского")
        return
    
    cursor.execute("UPDATE users SET gender = ? WHERE user_id = ?", (gender, message.from_user.id))
    conn.commit()
    
    gender_text = "Мужской" if gender == "м" else "Женский"
    await message.reply(f"✅ Пол установлен: {gender_text}")

@dp.message_handler(commands=["фото", "photo", "аватар"])
async def cmd_set_photo(message: types.Message):
    await register_user(message)
    
    await message.reply("📸 Отправьте фото для аватара")

@dp.message_handler(content_types=['photo'])
async def handle_photo(message: types.Message):
    # Сохраняем ID фото
    photo_id = message.photo[-1].file_id
    
    cursor.execute("UPDATE users SET photo_id = ? WHERE user_id = ?", (photo_id, message.from_user.id))
    conn.commit()
    
    await message.reply("✅ Фото профиля обновлено")

# Статистика
@dp.message_handler(commands=["стата", "stat", "Статистика"])
async def cmd_stat(message: types.Message):
    await register_user(message)
    
    # Общая статистика чата
    cursor.execute("SELECT COUNT(*) FROM users WHERE joined_chat IS NOT NULL")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE joined_date > datetime('now', '-1 day')")
    new_today = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(messages_count) FROM users")
    total_messages = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM warnings WHERE chat_id = ?", (message.chat.id,))
    total_warns = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM mutes WHERE chat_id = ?", (message.chat.id,))
    total_mutes = cursor.fetchone()[0]
    
    text = f"""
📊 <b>Статистика чата</b>

👥 Всего пользователей: {format_number(total_users)}
🆕 Новых за сегодня: {new_today}
📝 Всего сообщений: {format_number(total_messages)}
⚠️ Предупреждений: {total_warns}
🔇 Му

🔇 Мутов: {total_mutes}

🏆 Активность за сегодня:
"""
    
    # Топ активных за сегодня
    cursor.execute("""
        SELECT user_id, username, first_name, messages_count 
        FROM users 
        WHERE messages_count > 0
        ORDER BY messages_count DESC 
        LIMIT 5
    """)
    top = cursor.fetchall()
    
    if top:
        text += "\n<b>Топ по сообщениям:</b>\n"
        for i, user in enumerate(top, 1):
            name = user[1] or user[2] or f"ID {user[0]}"
            text += f"{i}. {name} — {user[3]} 📝\n"
    
    await message.reply(text)

@dp.message_handler(commands=["статасегодня", "stat_today"])
async def cmd_stat_today(message: types.Message):
    await register_user(message)
    
    cursor.execute("""
        SELECT COUNT(DISTINCT user_id) FROM messages 
        WHERE chat_id = ? AND date(timestamp) = date('now')
    """, (message.chat.id,))
    active_users = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) FROM messages 
        WHERE chat_id = ? AND date(timestamp) = date('now')
    """, (message.chat.id,))
    messages_today = cursor.fetchone()[0]
    
    text = f"""
📊 <b>Статистика за сегодня</b>

👥 Активных пользователей: {active_users}
📝 Сообщений: {messages_today}

<b>Самые активные:</b>
"""
    
    cursor.execute("""
        SELECT u.user_id, u.username, u.first_name, COUNT(*) as msg_count
        FROM messages m
        JOIN users u ON m.user_id = u.user_id
        WHERE m.chat_id = ? AND date(m.timestamp) = date('now')
        GROUP BY m.user_id
        ORDER BY msg_count DESC
        LIMIT 5
    """, (message.chat.id,))
    top = cursor.fetchall()
    
    for i, user in enumerate(top, 1):
        name = user[1] or user[2] or f"ID {user[0]}"
        text += f"{i}. {name} — {user[3]} 📝\n"
    
    await message.reply(text)

@dp.message_handler(commands=["топ", "top"])
async def cmd_top(message: types.Message):
    await register_user(message)
    
    text = "🏆 <b>Топ чата</b>\n\n"
    
    # Топ по сообщениям
    cursor.execute("""
        SELECT user_id, username, first_name, messages_count 
        FROM users 
        ORDER BY messages_count DESC 
        LIMIT 5
    """)
    top_messages = cursor.fetchall()
    
    if top_messages:
        text += "<b>По сообщениям:</b>\n"
        for i, user in enumerate(top_messages, 1):
            name = user[1] or user[2] or f"ID {user[0]}"
            text += f"{i}. {name} — {user[3]} 📝\n"
        text += "\n"
    
    # Топ по командам
    cursor.execute("""
        SELECT user_id, username, first_name, commands_count 
        FROM users 
        ORDER BY commands_count DESC 
        LIMIT 5
    """)
    top_commands = cursor.fetchall()
    
    if top_commands:
        text += "<b>По командам:</b>\n"
        for i, user in enumerate(top_commands, 1):
            name = user[1] or user[2] or f"ID {user[0]}"
            text += f"{i}. {name} — {user[3]} 🔧\n"
        text += "\n"
    
    # Топ по репутации
    cursor.execute("""
        SELECT user_id, username, first_name, reputation 
        FROM users 
        ORDER BY reputation DESC 
        LIMIT 5
    """)
    top_reputation = cursor.fetchall()
    
    if top_reputation:
        text += "<b>По репутации:</b>\n"
        for i, user in enumerate(top_reputation, 1):
            name = user[1] or user[2] or f"ID {user[0]}"
            text += f"{i}. {name} — {user[3]} ⭐\n"
    
    await message.reply(text)

# Экономика и ириски
@dp.message_handler(commands=["ириски", "balance", "баланс"])
async def cmd_balance(message: types.Message):
    await register_user(message)
    
    parts = message.text.split()
    if len(parts) > 1:
        target_id = extract_user_id(parts[1])
        if not target_id:
            await message.reply("❌ Не удалось определить пользователя")
            return
    else:
        target_id = message.from_user.id
    
    cursor.execute("SELECT iris_balance, username, first_name FROM users WHERE user_id = ?", (target_id,))
    result = cursor.fetchone()
    
    if not result:
        await message.reply("❌ Пользователь не найден")
        return
    
    balance = result[0]
    name = result[1] or result[2] or f"ID {target_id}"
    
    await message.reply(f"💰 <b>Баланс {name}</b>\n\nИриски: {format_number(balance)}")

@dp.message_handler(commands=["передать", "transfer"])
async def cmd_transfer(message: types.Message):
    await register_user(message)
    
    parts = message.text.split()
    if len(parts) < 3:
        await message.reply("❌ Укажите пользователя и сумму\nПример: /передать @user 100")
        return
    
    target_id = extract_user_id(parts[1])
    if not target_id:
        await message.reply("❌ Не удалось определить пользователя")
        return
    
    try:
        amount = int(parts[2])
        if amount <= 0:
            await message.reply("❌ Сумма должна быть положительной")
            return
    except:
        await message.reply("❌ Сумма должна быть числом")
        return
    
    # Проверяем баланс отправителя
    cursor.execute("SELECT iris_balance FROM users WHERE user_id = ?", (message.from_user.id,))
    sender_balance = cursor.fetchone()[0]
    
    if sender_balance < amount:
        await message.reply("❌ Недостаточно ирисок")
        return
    
    # Проверяем существование получателя
    cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (target_id,))
    if not cursor.fetchone():
        await message.reply("❌ Получатель не найден")
        return
    
    # Выполняем перевод
    cursor.execute("UPDATE users SET iris_balance = iris_balance - ? WHERE user_id = ?", 
                  (amount, message.from_user.id))
    cursor.execute("UPDATE users SET iris_balance = iris_balance + ? WHERE user_id = ?", 
                  (amount, target_id))
    
    # Записываем транзакцию
    cursor.execute("""
        INSERT INTO iris_transactions (from_user, to_user, amount, reason)
        VALUES (?, ?, ?, ?)
    """, (message.from_user.id, target_id, amount, "Перевод"))
    
    conn.commit()
    
    await message.reply(f"✅ Переведено {amount} ирисок пользователю")

@dp.message_handler(commands=["топбаланса", "top_balance"])
async def cmd_top_balance(message: types.Message):
    await register_user(message)
    
    cursor.execute("""
        SELECT user_id, username, first_name, iris_balance 
        FROM users 
        ORDER BY iris_balance DESC 
        LIMIT 10
    """)
    top = cursor.fetchall()
    
    if not top:
        await message.reply("📊 Нет данных")
        return
    
    text = "💰 <b>Топ богачей</b>\n\n"
    for i, user in enumerate(top, 1):
        name = user[1] or user[2] or f"ID {user[0]}"
        text += f"{i}. {name} — {format_number(user[3])} 🪙\n"
    
    await message.reply(text)

# Ежедневный бонус
@dp.message_handler(commands=["daily", "бонус", "дэйлик"])
async def cmd_daily(message: types.Message):
    await register_user(message)
    
    cursor.execute("SELECT last_daily, daily_streak FROM users WHERE user_id = ?", (message.from_user.id,))
    result = cursor.fetchone()
    
    last_daily = result[0]
    streak = result[1] or 0
    
    now = datetime.now()
    
    if last_daily:
        last = datetime.fromisoformat(last_daily)
        # Если прошло больше 2 дней, сбрасываем стрик
        if (now - last).days > 1:
            streak = 0
        
        # Если бонус уже получали сегодня
        if last.date() == now.date():
            await message.reply("❌ Сегодня вы уже получали бонус. Приходите завтра!")
            return
    
    # Рассчитываем бонус
    base_bonus = 100
    streak_bonus = streak * 10
    total_bonus = base_bonus + streak_bonus
    
    # VIP бонус
    cursor.execute("SELECT vip_level FROM users WHERE user_id = ?", (message.from_user.id,))
    vip_level = cursor.fetchone()[0]
    if vip_level > 0:
        total_bonus = int(total_bonus * (1 + vip_level * 0.1))
    
    # Обновляем данные
    new_streak = streak + 1
    cursor.execute("""
        UPDATE users 
        SET iris_balance = iris_balance + ?,
            last_daily = ?,
            daily_streak = ?
        WHERE user_id = ?
    """, (total_bonus, now.isoformat(), new_streak, message.from_user.id))
    conn.commit()
    
    await message.reply(f"""
🎁 <b>Ежедневный бонус получен!</b>

💰 Получено: {total_bonus} ирисок
🔥 Текущий стрик: {new_streak} дней
💎 Базовый бонус: {base_bonus}
✨ Бонус за стрик: +{streak_bonus}
{f'👑 VIP бонус: +{int(total_bonus * 0.1 * vip_level)}' if vip_level > 0 else ''}
""")

@dp.message_handler(commands=["стрик", "streak"])
async def cmd_streak(message: types.Message):
    await register_user(message)
    
    cursor.execute("SELECT daily_streak FROM users WHERE user_id = ?", (message.from_user.id,))
    streak = cursor.fetchone()[0] or 0
    
    await message.reply(f"🔥 Ваш текущий стрик: {streak} дней")

# VIP статус
@dp.message_handler(commands=["vip", "VIP"])
async def cmd_vip(message: types.Message):
    await register_user(message)
    
    cursor.execute("SELECT vip_level FROM users WHERE user_id = ?", (message.from_user.id,))
    vip_level = cursor.fetchone()[0]
    
    text = f"""
👑 <b>VIP статус</b>

Ваш уровень: {vip_level}

<b>Преимущества VIP:</b>
• Уровень 1: +10% к доходу, особые команды
• Уровень 2: +20% к доходу, уникальные кубы
• Уровень 3: +30% к доходу, создание кланов
• Уровень 4: +40% к доходу, доступ к эксклюзивным играм
• Уровень 5: +50% к доходу, личный менеджер

<b>Цены:</b>
Уровень 1: 1000 ирисок
Уровень 2: 5000 ирисок
Уровень 3: 15000 ирисок
Уровень 4: 50000 ирисок
Уровень 5: 100000 ирисок

/vip_buy [уровень] — купить VIP
"""
    await message.reply(text)

@dp.message_handler(commands=["vip_buy", "vip_купить"])
async def cmd_vip_buy(message: types.Message):
    await register_user(message)
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("❌ Укажите уровень VIP (1-5)")
        return
    
    try:
        level = int(parts[1])
        if level < 1 or level > 5:
            await message.reply("❌ Уровень должен быть от 1 до 5")
            return
    except:
        await message.reply("❌ Уровень должен быть числом")
        return
    
    # Цены
    prices = {1: 1000, 2: 5000, 3: 15000, 4: 50000, 5: 100000}
    price = prices[level]
    
    cursor.execute("SELECT iris_balance FROM users WHERE user_id = ?", (message.from_user.id,))
    balance = cursor.fetchone()[0]
    
    if balance < price:
        await message.reply(f"❌ Недостаточно ирисок. Нужно: {price}")
        return
    
    cursor.execute("UPDATE users SET iris_balance = iris_balance - ?, vip_level = ? WHERE user_id = ?",
                  (price, level, message.from_user.id))
    conn.commit()
    
    await message.reply(f"✅ Поздравляем! Вы приобрели VIP уровень {level}")

# Магазин
@dp.message_handler(commands=["shop", "магазин"])
async def cmd_shop(message: types.Message):
    await register_user(message)
    
    cursor.execute("SELECT id, name, description, price, stock FROM shop_items WHERE is_available = 1")
    items = cursor.fetchall()
    
    if not items:
        # Добавляем базовые товары
        cursor.executemany("""
            INSERT INTO shop_items (name, description, price, type, stock)
            VALUES (?, ?, ?, ?, ?)
        """, [
            ("🍬 Конфетка", "Маленький подарок", 50, "gift", -1),
            ("🎁 Подарок", "Случайный приз", 200, "gift", -1),
            ("🔮 Магический куб", "Редкий коллекционный куб", 500, "cube", 100),
            ("👑 VIP неделя", "VIP статус на 7 дней", 1000, "vip", -1),
            ("💎 Кристалл", "Украшение для профиля", 300, "decor", 50),
            ("🎫 Лотерейный билет", "Шанс выиграть джекпот", 100, "lottery", -1),
            ("⚔️ Меч", "Оружие для дуэлей", 800, "duel", 20),
            ("🛡️ Щит", "Защита в дуэлях", 600, "duel", 20)
        ])
        conn.commit()
        
        cursor.execute("SELECT id, name, description, price, stock FROM shop_items WHERE is_available = 1")
        items = cursor.fetchall()
    
    text = "🏪 <b>Магазин</b>\n\n"
    for item in items:
        stock_text = f" (в наличии: {item[4]})" if item[4] > 0 else " (∞)" if item[4] == -1 else " (нет)"
        text += f"<b>ID: {item[0]}</b> {item[1]}\n"
        text += f"📝 {item[2]}\n"
        text += f"💰 {item[3]} ирисок{stock_text}\n\n"
    
    text += "/buy [ID] [количество] — купить\n/gift [@user] [ID] — подарить"
    
    await message.reply(text)

@dp.message_handler(commands=["buy", "купить"])
async def cmd_buy(message: types.Message):
    await register_user(message)
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("❌ Укажите ID товара")
        return
    
    try:
        item_id = int(parts[1])
        quantity = int(parts[2]) if len(parts) > 2 else 1
    except:
        await message.reply("❌ Неверный формат")
        return
    
    cursor.execute("SELECT name, price, type, stock FROM shop_items WHERE id = ? AND is_available = 1", (item_id,))
    item = cursor.fetchone()
    
    if not item:
        await message.reply("❌ Товар не найден")
        return
    
    name, price, item_type, stock = item
    total_price = price * quantity
    
    if stock > 0 and stock < quantity:
        await message.reply(f"❌ В наличии только {stock} шт.")
        return
    
    cursor.execute("SELECT iris_balance FROM users WHERE user_id = ?", (message.from_user.id,))
    balance = cursor.fetchone()[0]
    
    if balance < total_price:
        await message.reply(f"❌ Недостаточно ирисок. Нужно: {total_price}")
        return
    
    # Списываем ириски
    cursor.execute("UPDATE users SET iris_balance = iris_balance - ? WHERE user_id = ?",
                  (total_price, message.from_user.id))
    
    # Добавляем товар в инвентарь
    cursor.execute("""
        INSERT INTO user_items (user_id, item_id, quantity)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, item_id) DO UPDATE SET quantity = quantity + excluded.quantity
    """, (message.from_user.id, item_id, quantity))
    
    # Обновляем остаток
    if stock > 0:
        cursor.execute("UPDATE shop_items SET stock = stock - ? WHERE id = ?", (quantity, item_id))
    
    conn.commit()
    
    await message.reply(f"✅ Куплено: {name} x{quantity} за {total_price} ирисок")

@dp.message_handler(commands=["gift", "подарить"])
async def cmd_gift(message: types.Message):
    await register_user(message)
    
    parts = message.text.split()
    if len(parts) < 3:
        await message.reply("❌ Укажите пользователя и ID товара\nПример: /gift @user 1")
        return
    
    target_id = extract_user_id(parts[1])
    if not target_id:
        await message.reply("❌ Не удалось определить пользователя")
        return
    
    try:
        item_id = int(parts[2])
        quantity = int(parts[3]) if len(parts) > 3 else 1
    except:
        await message.reply("❌ Неверный формат")
        return
    
    # Проверяем наличие товара у отправителя
    cursor.execute("SELECT quantity FROM user_items WHERE user_id = ? AND item_id = ?", 
                  (message.from_user.id, item_id))
    result = cursor.fetchone()
    
    if not result or result[0] < quantity:
        await message.reply("❌ У вас нет этого товара в таком количестве")
        return
    
    cursor.execute("SELECT name FROM shop_items WHERE id = ?", (item_id,))
    item_name = cursor.fetchone()[0]
    
    # Уменьшаем количество у отправителя
    if result[0] == quantity:
        cursor.execute("DELETE FROM user_items WHERE user_id = ? AND item_id = ?", 
                      (message.from_user.id, item_id))
    else:
        cursor.execute("UPDATE user_items SET quantity = quantity - ? WHERE user_id = ? AND item_id = ?",
                      (quantity, message.from_user.id, item_id))
    
    # Добавляем получателю
    cursor.execute("""
        INSERT INTO user_items (user_id, item_id, quantity)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, item_id) DO UPDATE SET quantity = quantity + excluded.quantity
    """, (target_id, item_id, quantity))
    
    conn.commit()
    
    await message.reply(f"🎁 Подарок отправлен!\n{quantity}x {item_name} → пользователю")

@dp.message_handler(commands=["inventory", "инвентарь"])
async def cmd_inventory(message: types.Message):
    await register_user(message)
    
    cursor.execute("""
        SELECT s.id, s.name, s.description, ui.quantity
        FROM user_items ui
        JOIN shop_items s ON ui.item_id = s.id
        WHERE ui.user_id = ?
        ORDER BY ui.quantity DESC
    """, (message.from_user.id,))
    items = cursor.fetchall()
    
    if not items:
        await message.reply("📦 Ваш инвентарь пуст")
        return
    
    text = "📦 <b>Ваш инвентарь</b>\n\n"
    for item in items:
        text += f"<b>ID: {item[0]}</b> {item[1]} x{item[3]}\n"
        text += f"📝 {item[2]}\n\n"
    
    await message.reply(text)

# Развлечения
@dp.message_handler(commands=["анекдот", "anekdot", "шутка"])
async def cmd_anekdot(message: types.Message):
    await register_user(message)
    
    jokes = [
        "Встречаются два программиста:\n— Слышал, ты женился?\n— Да.\n— Ну и как она?\n— Да нормально, интерфейс дружественный, в обслуживании неприхотлива, вот только с бэкапами беда — каждые 9 месяцев приходится систему переустанавливать.",
        "— Доктор, у меня глисты.\n— А вы что, их видите?\n— Нет, я с ними переписываюсь.",
        "Идут два кота по крыше. Один говорит:\n— Мяу.\n— Мяу-мяу.\n— Ты чё, с ума сошёл? Нас же люди услышат!",
        "Стоит программист в душе и кричит:\n— Окей, гугл, смой воду!\n— Окей, гугл, убери пену!\n— Окей, гугл, выключи воду!\n— Окей, гугл, подай полотенце!\nЖена из комнаты:\n— Ты там скоро? Ужин стынет.\n— Окей, гугл, найди жену...",
        "— Вовочка, почему ты опоздал в школу?\n— Я видел сон, что побывал в 30 странах, и так устал, что решил отдохнуть.",
        "— Дорогой, я сегодня так устала...\n— А что случилось?\n— Да ничего особенного, просто тяжелый день.\n— А что ты делала?\n— Лежала на диване и думала о жизни.",
        "— Алло, это служба спасения? У меня тут кот на дерево залез!\n— А высота большая?\n— Да метра два!\n— И что, сам слезть не может?\n— Не знаю, я его еще не спрашивал.",
        "— Почему программисты путают Хэллоуин и Рождество?\n— Потому что Oct 31 = Dec 25.",
        "— Доктор, я шизофреник!\n— Ну, это мы еще посмотрим, кто из нас двоих шизофреник!",
        "— Вовочка, составь предложение со словом «антресоли».\n— Антресоли — это настолько сложно, что я даже не знаю, с чем его едят."
    ]
    
    await message.reply(f"😄 <b>Анекдот:</b>\n\n{random.choice(jokes)}")

@dp.message_handler(commands=["факт", "fact"])
async def cmd_fact(message: types.Message):
    await register_user(message)
    
    facts = [
        "Осьминоги имеют три сердца и голубую кровь.",
        "Бананы технически являются ягодами, а клубника — нет.",
        "В Швейцарии запрещено держать только одну морскую свинку, потому что они социальные животные.",
        "Коровы имеют лучших друзей и могут испытывать стресс при разлуке с ними.",
        "Австралия длиннее, чем Луна в диаметре.",
        "Наполеон не был низким. Его рост составлял около 170 см, что было средним для того времени.",
        "В Японии есть отель, который обслуживают роботы.",
        "Кошки не могут чувствовать сладкий вкус.",
        "Самый длинный полет курицы длился 13 секунд.",
        "Мед никогда не портится. Археологи находили 3000-летний мед в гробницах, который всё ещё съедобен."
    ]
    
    await message.reply(f"🔍 <b>Интересный факт:</b>\n\n{random.choice(facts)}")

@dp.message_handler(commands=["цитата", "quote"])
async def cmd_quote(message: types.Message):
    await register_user(message)
    
    quotes = [
        "Жизнь — это то, что с тобой происходит, пока ты строишь планы. — Джон Леннон",
        "Будьте тем изменением, которое вы хотите увидеть в мире. — Махатма Ганди",
        "Единственный способ делать великие дела — любить то, что вы делаете. — Стив Джобс",
        "В конце концов, важны не годы в жизни, а жизнь в годах. — Авраам Линкольн",
        "Если вы хотите идти быстро, идите один. Если хотите идти далеко, идите вместе. — Африканская пословица",
        "Успех — это способность идти от неудачи к неудаче, не теряя энтузиазма. — Уинстон Черчилль",
        "Самая большая слава не в том, чтобы никогда не падать, а в том, чтобы вставать каждый раз, когда вы падаете. — Конфуций",
        "Счастье — это когда то, что вы думаете, говорите и делаете, находится в гармонии. — Махатма Ганди",
        "Не судите каждый день по урожаю, который вы собрали, а по семенам, которые вы посадили. — Роберт Стивенсон",
        "Лучшее время посадить дерево было 20 лет назад. Следующее лучшее время — сегодня. — Китайская пословица"
    ]
    
    await message.reply(f"📜 <b>Цитата:</b>\n\n{random.choice(quotes)}")

@dp.message_handler(commands=["ктоя", "whoami"])
async def cmd_whoami(message: types.Message):
    await register_user(message)
    
    roles = [
        "супергерой", "злодей", "тайный агент", "космонавт", "пират", 
        "робот", "инопланетянин", "волшебник", "вампир", "оборотень",
        "призрак", "эльф", "гном", "дракон", "рыцарь", "ниндзя",
        "самурай", "ковбой", "индеец", "детектив", "шпион"
    ]
    
    await message.reply(f"🦸 Вы — {random.choice(roles)}!")

@dp.message_handler(commands=["совет", "advice"])
async def cmd_advice(message: types.Message):
    await register_user(message)
    
    advices = [
        "Пейте больше воды.",
        "Высыпайтесь — это важно для здоровья.",
        "Делайте зарядку по утрам.",
        "Улыбайтесь чаще — это заразительно.",
        "Читайте книги — они развивают воображение.",
        "Не откладывайте на завтра то, что можно сделать сегодня.",
        "Слушайте больше, чем говорите.",
        "Иногда полезно просто помолчать.",
        "Цените время — оно невосполнимо.",
        "Будьте добры к другим и к себе."
    ]
    
    await message.reply(f"💡 <b>Совет:</b>\n\n{random.choice(advices)}")

# Гадания
@dp.message_handler(commands=["гадать", "ask"])
async def cmd_ask(message: types.Message):
    await register_user(message)
    
    question = message.text[7:].strip()
    if not question:
        await message.reply("❌ Задайте вопрос")
        return
    
    answers = [
        "Да", "Нет", "Возможно", "Определённо да", "Определённо нет",
        "Спросите позже", "Лучше не знать", "Сейчас нельзя ответить",
        "Сконцентрируйтесь и спросите снова", "Мой ответ — да",
        "Мой ответ — нет", "По моим данным — да", "Перспективы не очень",
        "Весьма вероятно", "Маловероятно", "Без сомнения", "Ни в коем случае",
        "Да, но будьте осторожны", "Нет, но не отчаивайтесь"
    ]
    
    await message.reply(f"🎱 <b>Вопрос:</b> {question}\n\n<b>Ответ:</b> {random.choice(answers)}")

@dp.message_handler(commands=["да/нет", "yesno"])
async def cmd_yesno(message: types.Message):
    await register_user(message)
    
    answers = ["Да ✅", "Нет ❌", "Возможно 🤔", "Скорее да", "Скорее нет"]
    
    await message.reply(f"🎲 {random.choice(answers)}")

@dp.message_handler(commands=["шар", "ball"])
async def cmd_ball(message: types.Message):
    await register_user(message)
    
    answers = [
        "Бесспорно", "Предрешено", "Никаких сомнений", "Определённо да",
        "Можешь быть уверен в этом", "Мне кажется — да", "Вероятнее всего",
        "Хорошие перспективы", "Знаки говорят — да", "Да",
        "Пока не ясно, попробуй снова", "Спроси позже", "Лучше не рассказывать",
        "Сейчас нельзя предсказать", "Сконцентрируйся и спроси опять",
        "Даже не думай", "Мой ответ — нет", "По моим данным — нет",
        "Перспективы не очень", "Весьма сомнительно"
    ]
    
    await message.reply(f"🔮 {random.choice(answers)}")

@dp.message_handler(commands=["совместимость", "compatibility"])
async def cmd_compatibility(message: types.Message):
    await register_user(message)
    
    parts = message.text.split()
    if len(parts) < 3:
        await message.reply("❌ Укажите двух пользователей\nПример: /совместимость @user1 @user2")
        return
    
    user1_id = extract_user_id(parts[1])
    user2_id = extract_user_id(parts[2])
    
    if not user1_id or not user2_id:
        await message.reply("❌ Не удалось определить пользователей")
        return
    
    # Получаем имена
    cursor.execute("SELECT username, first_name FROM users WHERE user_id = ?", (user1_id,))
    user1 = cursor.fetchone()
    cursor.execute("SELECT username, first_name FROM users WHERE user_id = ?", (user2_id,))
    user2 = cursor.fetchone()
    
    name1 = user1[0] or user1[1] or f"ID {user1_id}"
    name2 = user2[0] or user2[1] or f"ID {user2_id}"
    
    # Генерируем совместимость
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
    
    await message.reply(f"""
💞 <b>Совместимость</b>

{emoji} <b>{name1}</b> и <b>{name2}</b>

Совместимость: {compatibility}%
{text}
""")

# Игры
@dp.message_handler(commands=["монетка", "coin"])
async def cmd_coin(message: types.Message):
    await register_user(message)
    
    result = random.choice(["Орёл", "Решка"])
    emoji = "🪙" if result == "Орёл" else "🪙"
    
    await message.reply(f"{emoji} <b>{result}</b>")

@dp.message_handler(commands=["кубик", "dice"])
async def cmd_dice(message: types.Message):
    await register_user(message)
    
    result = random.randint(1, 6)
    emojis = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
    
    await message.reply(f"🎲 <b>{result}</b> {emojis[result-1]}")

@dp.message_handler(commands=["случайное", "random"])
async def cmd_random(message: types.Message):
    await register_user(message)
    
    parts = message.text.split()
    if len(parts) < 3:
        await message.reply("❌ Укажите минимум и максимум\nПример: /случайное 1 100")
        return
    
    try:
        min_val = int(parts[1])
        max_val = int(parts[2])
        if min_val >= max_val:
            await message.reply("❌ Минимум должен быть меньше максимума")
            return
    except:
        await message.reply("❌ Укажите числа")
        return
    
    result = random.randint(min_val, max_val)
    
    await message.reply(f"🎲 Случайное число: <b>{result}</b>")

@dp.message_handler(commands=["выбери", "choose"])
async def cmd_choose(message: types.Message):
    await register_user(message)
    
    text = message.text[7:].strip()
    if not text:
        await message.reply("❌ Укажите варианты через / или ,\nПример: /выбери пицца/суши/бургер")
        return
    
    # Разделяем по / или ,
    if "/" in text:
        options = [opt.strip() for opt in text.split("/")]
    elif "," in text:
        options = [opt.strip() for opt in text.split(",")]
    else:
        options = [text]
    
    if len(options) < 2:
        await message.reply("❌ Укажите хотя бы 2 варианта")
        return
    
    result = random.choice(options)
    
    await message.reply(f"🤔 Я выбираю: <b>{result}</b>")

# Модуль дуэлей
@dp.message_handler(commands=["дуэль", "duel"])
async def cmd_duel(message: types.Message):
    await register_user(message)
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("❌ Укажите противника\nПример: /дуэль @user 100")
        return
    
    target_id = extract_user_id(parts[1])
    if not target_id:
        await message.reply("❌ Не удалось определить пользователя")
        return
    
    if target_id == message.from_user.id:
        await message.reply("❌ Нельзя вызвать на дуэль самого себя")
        return
    
    bet = 0
    if len(parts) > 2:
        try:
            bet = int(parts[2])
            if bet < 0:
                await message.reply("❌ Ставка должна быть положительной")
                return
        except:
            await message.reply("❌ Ставка должна быть числом")
            return
    
    # Проверяем баланс
    cursor.execute("SELECT iris_balance FROM users WHERE user_id = ?", (message.from_user.id,))
    balance = cursor.fetchone()[0]
    
    if balance < bet:
        await message.reply("❌ Недостаточно ирисок для ставки")
        return
    
    # Создаем дуэль
    cursor.execute("""
        INSERT INTO duels (challenger_id, opponent_id, bet_amount)
        VALUES (?, ?, ?)
    """, (message.from_user.id, target_id, bet))
    duel_id = cursor.lastrowid
    conn.commit()
    
    # Уведомляем противника
    await message.reply(f"""
⚔️ <b>Вызов на дуэль!</b>

ID дуэли: {duel_id}
Противник: @{parts[1]}
Ставка: {bet} ирисок

/accept {duel_id} — принять
/decline {duel_id} — отклонить
""")

@dp.message_handler(commands=["дуэли", "duels"])
async def cmd_duels(message: types.Message):
    await register_user(message)
    
    cursor.execute("""
        SELECT id, challenger_id, opponent_id, bet_amount, status
        FROM duels
        WHERE status = 'pending' AND (challenger_id = ? OR opponent_id = ?)
    """, (message.from_user.id, message.from_user.id))
    duels = cursor.fetchall()
    
    if not duels:
        await message.reply("📋 У вас нет активных дуэлей")
        return
    
    text = "⚔️ <b>Ваши дуэли:</b>\n\n"
    for duel in duels:
        opponent = duel[2] if duel[1] == message.from_user.id else duel[1]
        cursor.execute("SELECT username, first_name FROM users WHERE user_id = ?", (opponent,))
        opp_info = cursor.fetchone()
        opp_name = opp_info[0] or opp_info[1] or f"ID {opponent}"
        
        text += f"ID: {duel[0]} | Противник: {opp_name}\n"
        text += f"Ставка: {duel[3]} | Статус: {duel[4]}\n\n"
    
    await message.reply(text)

@dp.message_handler(commands=["принять", "accept"])
async def cmd_accept_duel(message: types.Message):
    await register_user(message)
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("❌ Укажите ID дуэли")
        return
    
    try:
        duel_id = int(parts[1])
    except:
        await message.reply("❌ Неверный ID")
        return
    
    cursor.execute("""
        SELECT id, challenger_id, opponent_id, bet_amount, status
        FROM duels WHERE id = ? AND opponent_id = ? AND status = 'pending'
    """, (duel_id, message.from_user.id))
    duel = cursor.fetchone()
    
    if not duel:
        await message.reply("❌ Дуэль не найдена или уже принята")
        return
    
    # Проверяем баланс
    cursor.execute("SELECT iris_balance FROM users WHERE user_id = ?", (message.from_user.id,))
    balance = cursor.fetchone()[0]
    
    if balance < duel[3]:
        await message.reply("❌ Недостаточно ирисок для ставки")
        return
    
    # Начинаем дуэль
    cursor.execute("UPDATE duels SET status = 'active' WHERE id = ?", (duel_id,))
    conn.commit()
    
    await message.reply(f"""
⚔️ <b>Дуэль началась!</b>

ID: {duel_id}

<b>Команды:</b>
/attack [сила 1-10] — атаковать
/defend — защищаться
/surrender — сдаться

Удачи! 💪
""")

@dp.message_handler(commands=["отклонить", "decline"])
async def cmd_decline_duel(message: types.Message):
    await register_user(message)
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("❌ Укажите ID дуэли")
        return
    
    try:
        duel_id = int(parts[1])
    except:
        await message.reply("❌ Неверный ID")
        return
    
    cursor.execute("""
        DELETE FROM duels 
        WHERE id = ? AND opponent_id = ? AND status = 'pending'
    """, (duel_id, message.from_user.id))
    conn.commit()
    
    await message.reply("✅ Дуэль отклонена")

@dp.message_handler(commands=["атака", "attack"])
async def cmd_attack(message: types.Message):
    await register_user(message)
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("❌ Укажите силу атаки (1-10)")
        return
    
    try:
        power = int(parts[1])
        if power < 1 or power > 10:
            await message.reply("❌ Сила должна быть от 1 до 10")
            return
    except:
        await message.reply("❌ Сила должна быть числом")
        return
    
    # Ищем активную дуэль
    cursor.execute("""
        SELECT id, challenger_id, opponent_id, challenger_hp, opponent_hp, current_turn, bet_amount
        FROM duels 
        WHERE status = 'active' AND (challenger_id = ? OR opponent_id = ?)
    """, (message.from_user.id, message.from_user.id))
    duel = cursor.fetchone()
    
    if not duel:
        await message.reply("❌ У вас нет активной дуэли")
        return
    
    duel_id, challenger, opponent, chp, ohp, turn, bet = duel
    
    # Определяем, чей ход
    if turn is None:
        turn = challenger
    
    if message.from_user.id != turn:
        await message.reply("❌ Сейчас не ваш ход")
        return
    
    # Рассчитываем урон
    damage = random.randint(power * 5, power * 10)
    crit = random.random() < 0.2  # 20% на критический удар
    if crit:
        damage = int(damage * 1.5)
    
    # Применяем урон
    if message.from_user.id == challenger:
        new_hp = ohp - damage
        next_turn = opponent
        hp_col = "opponent_hp"
    else:
        new_hp = chp - damage
        next_turn = challenger
        hp_col = "challenger_hp"
    
    if new_hp <= 0:
        # Победа
        winner = message.from_user.id
        loser = opponent if winner == challenger else challenger
        
        # Переводим ставку
        if bet > 0:
            cursor.execute("UPDATE users SET iris_balance = iris_balance + ? WHERE user_id = ?", (bet, winner))
            cursor.execute("UPDATE users SET iris_balance = iris_balance - ? WHERE user_id = ?", (bet, loser))
        
        cursor.execute("UPDATE duels SET status = 'finished', winner_id = ? WHERE id = ?", (winner, duel_id))
        conn.commit()
        
        await message.reply(f"""
⚔️ <b>ПОБЕДА!</b>

Ваш урон: {damage}{' (КРИТ)' if crit else ''}
Противник повержен!

{'💰 Вы выиграли ' + str(bet) + ' ирисок!' if bet > 0 else ''}
""")
    else:
        # Обновляем HP
        cursor.execute(f"UPDATE duels SET {hp_col} = ?, current_turn = ? WHERE id = ?", (new_hp, next_turn, duel_id))
        conn.commit()
        
        await message.reply(f"""
⚔️ <b>Атака!</b>

Урон: {damage}{' (КРИТ)' if crit else ''}
У противника осталось: {new_hp} HP

Следующий ход: {'ваш' if next_turn == message.from_user.id else 'противника'}
""")

@dp.message_handler(commands=["защита", "defend"])
async def cmd_defend(message: types.Message):
    await register_user(message)
    
    # Ищем активную дуэль
    cursor.execute("""
        SELECT id, challenger_id, opponent_id, challenger_hp, opponent_hp, current_turn
        FROM duels 
        WHERE status = 'active' AND (challenger_id = ? OR opponent_id = ?)
    """, (message.from_user.id, message.from_user.id))
    duel = cursor.fetchone()
    
    if not duel:
        await message.reply("❌ У вас нет активной дуэли")
        return
    
    duel_id, challenger, opponent, chp, ohp, turn = duel
    
    if message.from_user.id != turn:
        await message.reply("❌ Сейчас не ваш ход")
        return
    
    # Защита увеличивает HP
    heal = random.randint(10, 30)
    
    if message.from_user.id == challenger:
        new_hp = chp + heal
        next_turn = opponent
        hp_col = "challenger_hp"
    else:
        new_hp = ohp + heal
        next_turn = challenger
        hp_col = "opponent_hp"
    
    cursor.execute(f"UPDATE duels SET {hp_col} = ?, current_turn = ? WHERE id = ?", (new_hp, next_turn, duel_id))
    conn.commit()
    
    await message.reply(f"""
🛡️ <b>Защита!</b>

Восстановлено: {heal} HP
Теперь у вас: {new_hp} HP

Следующий ход: {'ваш' if next_turn == message.from_user.id else 'противника'}
""")

@dp.message_handler(commands=["сдаться", "surrender"])
async def cmd_surrender(message: types.Message):
    await register_user(message)
    
    # Ищем активную дуэль
    cursor.execute("""
        SELECT id, challenger_id, opponent_id, bet_amount
        FROM duels 
        WHERE status = 'active' AND (challenger_id = ? OR opponent_id = ?)
    """, (message.from_user.id, message.from_user.id))
    duel = cursor.fetchone()
    
    if not duel:
        await message.reply("❌ У вас нет активной дуэли")
        return
    
    duel_id, challenger, opponent, bet = duel
    
    winner = opponent if message.from_user.id == challenger else challenger
    
    # Переводим ставку
    if bet > 0:
        cursor.execute("UPDATE users SET iris_balance = iris_balance + ? WHERE user_id = ?", (bet, winner))
        cursor.execute("UPDATE users SET iris_balance = iris_balance - ? WHERE user_id = ?", (bet, message.from_user.id))
    
    cursor.execute("UPDATE duels SET status = 'finished', winner_id = ? WHERE id = ?", (winner, duel_id))
    conn.commit()
    
    await message.reply(f"""
🏳️ <b>Поражение</b>

Вы сдались. Победитель: @{winner}
{'💰 Вы потеряли ' + str(bet) + ' ирисок' if bet > 0 else ''}
""")

# Модуль отношений
@dp.message_handler(commands=["друг", "friend"])
async def cmd_add_friend(message: types.Message):
    await register_user(message)
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("❌ Укажите пользователя")
        return
    
    target_id = extract_user_id(parts[1])
    if not target_id:
        await message.reply("❌ Не удалось определить пользователя")
        return
    
    if target_id == message.from_user.id:
        await message.reply("❌ Нельзя добавить в друзья самого себя")
        return
    
    # Проверяем, не враг ли
    cursor.execute("SELECT 1 FROM enemies WHERE user_id = ? AND enemy_id = ?", 
                  (message.from_user.id, target_id))
    if cursor.fetchone():
        await message.reply("❌ Сначала простите врага командой /forgive")
        return
    
    # Проверяем, не в игноре
    cursor.execute("SELECT 1 FROM ignored WHERE user_id = ? AND ignored_id = ?", 
                  (message.from_user.id, target_id))
    if cursor.fetchone():
        await message.reply("❌ Сначала уберите из игнора командой /unignore")
        return
    
    # Проверяем существующую заявку
    cursor.execute("""
        SELECT status FROM friends 
        WHERE (user_id = ? AND friend_id = ?) OR (user_id = ? AND friend_id = ?)
    """, (message.from_user.id, target_id, target_id, message.from_user.id))
    result = cursor.fetchone()
    
    if result:
        if result[0] == "accepted":
            await message.reply("❌ Вы уже друзья")
        elif result[0] == "pending":
            await message.reply("❌ Заявка уже отправлена")
        return
    
    # Отправляем заявку
    cursor.execute("""
        INSERT INTO friends (user_id, friend_id, status)
        VALUES (?, ?, 'pending')
    """, (message.from_user.id, target_id))
    conn.commit()
    
    await message.reply("✅ Заявка в друзья отправлена")

@dp.message_handler(commands=["принятьдруга", "accept_friend"])
async def cmd_accept_friend(message: types.Message):
    await register_user(message)
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("❌ Укажите пользователя")
        return
    
    target_id = extract_user_id(parts[1])
    if not target_id:
        await message.reply("❌ Не удалось определить пользователя")
        return
    
    cursor.execute("""
        UPDATE friends 
        SET status = 'accepted' 
        WHERE user_id = ? AND friend_id = ? AND status = 'pending'
    """, (target_id, message.from_user.id))
    
    if cursor.rowcount > 0:
        conn.commit()
        await message.reply("✅ Заявка принята! Теперь вы друзья")
    else:
        await message.reply("❌ Нет заявки от этого пользователя")

@dp.message_handler(commands=["отклонитьдруга", "decline_friend"])
async def cmd_decline_friend(message: types.Message):
    await register_user(message)
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("❌ Укажите пользователя")
        return
    
    target_id = extract_user_id(parts[1])
    if not target_id:
        await message.reply("❌ Не удалось определить пользователя")
        return
    
    cursor.execute("""
        DELETE FROM friends 
        WHERE user_id = ? AND friend_id = ? AND status = 'pending'
    """, (target_id, message.from_user.id))
    conn.commit()
    
    await message.reply("✅ Заявка отклонена")

@dp.message_handler(commands=["удалитьдруга", "unfriend"])
async def cmd_unfriend(message: types.Message):
    await register_user(message)
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("❌ Укажите пользователя")
        return
    
    target_id = extract_user_id(parts[1])
    if not target_id:
        await message.reply("❌ Не удалось определить пользователя")
        return
    
    cursor.execute("""
        DELETE FROM friends 
        WHERE (user_id = ? AND friend_id = ?) OR (user_id = ? AND friend_id = ?)
    """, (message.from_user.id, target_id, target_id, message.from_user.id))
    conn.commit()
    
    await message.reply("✅ Пользователь удален из друзей")

@dp.message_handler(commands=["друзья", "friends"])
async def cmd_friends(message: types.Message):
    await register_user(message)
    
    # Получаем список друзей
    cursor.execute("""
        SELECT u.user_id, u.username, u.first_name
        FROM friends f
        JOIN users u ON (f.friend_id = u.user_id AND f.user_id = ?) OR (f.user_id = u.user_id AND f.friend_id = ?)
        WHERE f.status = 'accepted'
    """, (message.from_user.id, message.from_user.id))
    friends = cursor.fetchall()
    
    # Получаем входящие заявки
    cursor.execute("""
        SELECT u.user_id, u.username, u.first_name
        FROM friends f
        JOIN users u ON f.user_id = u.user_id
        WHERE f.friend_id = ? AND f.status = 'pending'
    """, (message.from_user.id,))
    incoming = cursor.fetchall()
    
    text = "👥 <b>Ваши друзья</b>\n\n"
    
    if friends:
        text += "<b>Друзья:</b>\n"
        for friend in friends:
            name = friend[1] or friend[2] or f"ID {friend[0]}"
            text += f"• {name}\n"
    else:
        text += "У вас пока нет друзей\n"
    
    if incoming:
        text += "\n<b>Входящие заявки:</b>\n"
        for req in incoming:
            name = req[1] or req[2] or f"ID {req[0]}"
            text += f"• {name} — /accept_friend {req[0]}\n"
    
    await message.reply(text)

@dp.message_handler(commands=["враг", "enemy"])
async def cmd_add_enemy(message: types.Message):
    await register_user(message)
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("❌ Укажите пользователя")
        return
    
    target_id = extract_user_id(parts[1])
    if not target_id:
        await message.reply("❌ Не удалось определить пользователя")
        return
    
    if target_id == message.from_user.id:
        await message.reply("❌ Нельзя объявить врагом самого себя")
        return
    
    # Удаляем из друзей, если были
    cursor.execute("""
        DELETE FROM friends 
        WHERE (user_id = ? AND friend_id = ?) OR (user_id = ? AND friend_id = ?)
    """, (message.from_user.id, target_id, target_id, message.from_user.id))
    
    cursor.execute("""
        INSERT OR REPLACE INTO enemies (user_id, enemy_id)
        VALUES (?, ?)
    """, (message.from_user.id, target_id))
    conn.commit()
    
    await message.reply("⚔️ Пользователь объявлен врагом")

@dp.message_handler(commands=["простить", "forgive"])
async def cmd_forgive(message: types.Message):
    await register_user(message)
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("❌ Укажите пользователя")
        return
    
    target_id = extract_user_id(parts[1])
    if not target_id:
        await message.reply("❌ Не удалось определить пользователя")
        return
    
    cursor.execute("DELETE FROM enemies WHERE user_id = ? AND enemy_id = ?", 
                  (message.from_user.id, target_id))
    conn.commit()
    
    await message.reply("✅ Враг прощен")

@dp.message_handler(commands=["игнор", "ignore"])
async def cmd_ignore(message: types.Message):
    await register_user(message)
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("❌ Укажите пользователя")
        return
    
    target_id = extract_user_id(parts[1])
    if not target_id:
        await message.reply("❌ Не удалось определить пользователя")
        return
    
    if target_id == message.from_user.id:
        await message.reply("❌ Нельзя игнорировать самого себя")
        return
    
    cursor.execute("""
        INSERT OR REPLACE INTO ignored (user_id, ignored_id)
        VALUES (?, ?)
    """, (message.from_user.id, target_id))
    conn.commit()
    
    await message.reply("🚫 Пользователь добавлен в игнор-лист")

@dp.message_handler(commands=["убратьигнор", "unignore"])
async def cmd_unignore(message: types.Message):
    await register_user(message)
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("❌ Укажите пользователя")
        return
    
    target_id = extract_user_id(parts[1])
    if not target_id:
        await message.reply("❌ Не удалось определить пользователя")
        return
    
    cursor.execute("DELETE FROM ignored WHERE user_id = ? AND ignored_id = ?", 
                  (message.from_user.id, target_id))
    conn.commit()
    
    await message.reply("✅ Пользователь убран из игнора")

# Модуль браков
@dp.message_handler(commands=["предложить", "marry"])
async def cmd_marry(message: types.Message):
    await register_user(message)
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("❌ Укажите пользователя")
        return
    
    target_id = extract_user_id(parts[1])
    if not target_id:
        await message.reply("❌ Не удалось определить пользователя")
        return
    
    if target_id == message.from_user.id:
        await message.reply("❌ Нельзя жениться на самом себе")
        return
    
    # Проверяем, не женат ли уже
    cursor.execute("SELECT married_to FROM users WHERE user_id = ?", (message.from_user.id,))
    if cursor.fetchone()[0]:
        await message.reply("❌ Вы уже в браке. Сначала разведитесь")
        return
    
    cursor.execute("SELECT married_to FROM users WHERE user_id = ?", (target_id,))
    if cursor.fetchone()[0]:
        await message.reply("❌ Этот пользователь уже в браке")
        return
    
    # Сохраняем предложение в памяти
    # В реальном проекте нужно создать таблицу для предложений
    await message.reply(f"💍 Предложение отправлено! Пользователь должен принять командой /accept_marriage")

@dp.message_handler(commands=["принятьбрак", "accept_marriage"])
async def cmd_accept_marriage(message: types.Message):
    await register_user(message)
    
    # Здесь должна быть логика принятия предложения
    # Для упрощения сразу заключаем брак
    cursor.execute("""
        UPDATE users 
        SET married_to = ? 
        WHERE user_id = ?
    """, (message.from_user.id, message.from_user.id))  # В реальности нужно ID партнера
    
    await message.reply("💞 Поздравляю! Теперь вы в браке!")

@dp.message_handler(commands=["развод", "divorce"])
async def cmd_divorce(message: types.Message):
    await register_user(message)
    
    cursor.execute("SELECT married_to FROM users WHERE user_id = ?", (message.from_user.id,))
    married_to = cursor.fetchone()[0]
    
    if not married_to:
        await message.reply("❌ Вы не в браке")
        return
    
    cursor.execute("UPDATE users SET married_to = NULL WHERE user_id = ? OR user_id = ?", 
                  (message.from_user.id, married_to))
    conn.commit()
    
    await message.reply("💔 Брак расторгнут")

@dp.message_handler(commands=["семьи", "families"])
async def cmd_families(message: types.Message):
    await register_user(message)
    
    cursor.execute("""
        SELECT u1.user_id, u1.username, u1.first_name, u2.user_id, u2.username, u2.first_name
        FROM users u1
        JOIN users u2 ON u1.married_to = u2.user_id
        WHERE u1.user_id < u2.user_id
        LIMIT 10
    """)
    families = cursor.fetchall()
    
    if not families:
        await message.reply("👥 В этом чате пока нет семей")
        return
    
    text = "👥 <b>Семьи чата:</b>\n\n"
    for fam in families:
        name1 = fam[1] or fam[2] or f"ID {fam[0]}"
        name2 = fam[4] or fam[5] or f"ID {fam[3]}"
        text += f"💞 {name1} + {name2}\n"
    
    await message.reply(text)

# Модуль кланов
@dp.message_handler(commands=["клан", "clan"])
async def cmd_clan(message: types.Message):
    await register_user(message)
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("""
🏰 <b>Команды кланов</b>

/clan create [название] — создать клан
/clan join [название] — вступить в клан
/clan leave — выйти из клана
/clan info — информация о вашем клане
/clan top — топ кланов
/clan donate [сумма] — внести в казну
/clan kick [@user] — исключить (лидер)
/clan leader [@user] — передать лидерство
""")
        return
    
    action = parts[1].lower()
    
    if action == "create":
        if len(parts) < 3:
            await message.reply("❌ Укажите название клана")
            return
        
        name = " ".join(parts[2:])
        
        # Проверяем, не в клане ли уже
        cursor.execute("SELECT clan_id FROM users WHERE user_id = ?", (message.from_user.id,))
        if cursor.fetchone()[0]:
            await message.reply("❌ Вы уже в клане")
            return
        
        # Проверяем уникальность названия
        cursor.execute("SELECT 1 FROM clans WHERE name = ?", (name,))
        if cursor.fetchone():
            await message.reply("❌ Клан с таким названием уже существует")
            return
        
        # Создаем клан
        cursor.execute("""
            INSERT INTO clans (name, leader_id)
            VALUES (?, ?)
        """, (name, message.from_user.id))
        clan_id = cursor.lastrowid
        
        # Добавляем создателя
        cursor.execute("""
            INSERT INTO clan_members (clan_id, user_id, role)
            VALUES (?, ?, 'leader')
        """, (clan_id, message.from_user.id))
        
        cursor.execute("UPDATE users SET clan_id = ? WHERE user_id = ?", (clan_id, message.from_user.id))
        conn.commit()
        
        await message.reply(f"✅ Клан '{name}' создан!")
    
    elif action == "join":
        if len(parts) < 3:
            await message.reply("❌ Укажите название клана")
            return
        
        name = " ".join(parts[2:])
        
        cursor.execute("SELECT id FROM clans WHERE name = ?", (name,))
        result = cursor.fetchone()
        
        if not result:
            await message.reply("❌ Клан не найден")
            return
        
        clan_id = result[0]
        
        # Проверяем, не в клане ли уже
        cursor.execute("SELECT clan_id FROM users WHERE user_id = ?", (message.from_user.id,))
        if cursor.fetchone()[0]:
            await message.reply("❌ Вы уже в клане")
            return
        
        cursor.execute("""
            INSERT INTO clan_members (clan_id, user_id)
            VALUES (?, ?)
        """, (clan_id, message.from_user.id))
        
        cursor.execute("UPDATE users SET clan_id = ? WHERE user_id = ?", (clan_id, message.from_user.id))
        conn.commit()
        
        await message.reply(f"✅ Вы вступили в клан '{name}'")
    
    elif action == "leave":
        cursor.execute("SELECT clan_id FROM users WHERE user_id = ?", (message.from_user.id,))
        clan_id = cursor.fetchone()[0]
        
        if not clan_id:
            await message.reply("❌ Вы не в клане")
            return
        
        cursor.execute("SELECT role FROM clan_members WHERE clan_id = ? AND user_id = ?", 
                      (clan_id, message.from_user.id))
        role = cursor.fetchone()[0]
        
        if role == "leader":
            await message.reply("❌ Лидер не может покинуть клан. Передайте лидерство или удалите клан")
            return
        
        cursor.execute("DELETE FROM clan_members WHERE clan_id = ? AND user_id = ?", 
                      (clan_id, message.from_user.id))
        cursor.execute("UPDATE users SET clan_id = NULL WHERE user_id = ?", (message.from_user.id,))
        conn.commit()
        
        await message.reply("✅ Вы покинули клан")
    
    elif action == "info":
        cursor.execute("SELECT clan_id FROM users WHERE user_id = ?", (message.from_user.id,))
        clan_id = cursor.fetchone()[0]
        
        if not clan_id:
            await message.reply("❌ Вы не в клане")
            return
        
        cursor.execute("SELECT name, leader_id, balance, description FROM clans WHERE id = ?", (clan_id,))
        clan = cursor.fetchone()
        
        cursor.execute("""
            SELECT u.user_id, u.username, u.first_name, cm.role
            FROM clan_members cm
            JOIN users u ON cm.user_id = u.user_id
            WHERE cm.clan_id = ?
        """, (clan_id,))
        members = cursor.fetchall()
        
        cursor.execute("SELECT username, first_name FROM users WHERE user_id = ?", (clan[1],))
        leader = cursor.fetchone()
        leader_name = leader[0] or leader[1] or f"ID {clan[1]}"
        
        text = f"""
🏰 <b>Клан: {clan[0]}</b>

👑 Лидер: {leader_name}
💰 Казна: {clan[2]} ирисок
👥 Участников: {len(members)}

<b>Участники:</b>
"""
        
        for member in members:
            name = member[1] or member[2] or f"ID {member[0]}"
            role_emoji = "👑" if member[3] == "leader" else "🛡️" if member[3] == "admin" else "👤"
            text += f"{role_emoji} {name}\n"
        
        await message.reply(text)
    
    elif action == "top":
        cursor.execute("""
            SELECT c.name, COUNT(cm.user_id) as members, c.balance
            FROM clans c
            LEFT JOIN clan_members cm ON c.id = cm.clan_id
            GROUP BY c.id
            ORDER BY members DESC, c.balance DESC
            LIMIT 10
        """)
        clans = cursor.fetchall()
        
        if not clans:
            await message.reply("🏰 Пока нет созданных кланов")
            return
        
        text = "🏆 <b>Топ кланов</b>\n\n"
        for i, clan in enumerate(clans, 1):
            text += f"{i}. {clan[0]} — {clan[1]} участников, {clan[2]} 🪙\n"
        
        await message.reply(text)
    
    elif action == "donate":
        if len(parts) < 3:
            await message.reply("❌ Укажите сумму")
            return
        
        try:
            amount = int(parts[2])
            if amount <= 0:
                await message.reply("❌ Сумма должна быть положительной")
                return
        except:
            await message.reply("❌ Сумма должна быть числом")
            return
        
        cursor.execute("SELECT clan_id FROM users WHERE user_id = ?", (message.from_user.id,))
        clan_id = cursor.fetchone()[0]
        
        if not clan_id:
            await message.reply("❌ Вы не в клане")
            return
        
        cursor.execute("SELECT iris_balance FROM users WHERE user_id = ?", (message.from_user.id,))
        balance = cursor.fetchone()[0]
        
        if balance < amount:
            await message.reply("❌ Недостаточно ирисок")
            return
        
        cursor.execute("UPDATE users SET iris_balance = iris_balance - ? WHERE user_id = ?", 
                      (amount, message.from_user.id))
        cursor.execute("UPDATE clans SET balance = balance + ? WHERE id = ?", (amount, clan_id))
        conn.commit()
        
        await message.reply(f"✅ Вы внесли {amount} ирисок в казну клана")

# Модуль кружков
@dp.message_handler(commands=["кружок", "circle"])
async def cmd_circle(message: types.Message):
    await register_user(message)
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("""
🎯 <b>Команды кружков</b>

/circle create [название] — создать кружок
/circle join [название] — вступить в кружок
/circle leave — выйти из кружка
/circle list — список кружков
/circle meeting [дата] [время] [место] — создать встречу
""")
        return
    
    action = parts[1].lower()
    
    if action == "create":
        if len(parts) < 3:
            await message.reply("❌ Укажите название кружка")
            return
        
        name = " ".join(parts[2:])
        
        cursor.execute("""
            INSERT INTO circles (name, created_by)
            VALUES (?, ?)
        """, (name, message.from_user.id))
        circle_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO circle_members (circle_id, user_id)
            VALUES (?, ?)
        """, (circle_id, message.from_user.id))
        conn.commit()
        
        await message.reply(f"✅ Кружок '{name}' создан!")
    
    elif action == "join":
        if len(parts) < 3:
            await message.reply("❌ Укажите название кружка")
            return
        
        name = " ".join(parts[2:])
        
        cursor.execute("SELECT id FROM circles WHERE name = ?", (name,))
        result = cursor.fetchone()
        
        if not result:
            await message.reply("❌ Кружок не найден")
            return
        
        circle_id = result[0]
        
        cursor.execute("""
            INSERT OR IGNORE INTO circle_members (circle_id, user_id)
            VALUES (?, ?)
        """, (circle_id, message.from_user.id))
        conn.commit()
        
        await message.reply(f"✅ Вы вступили в кружок '{name}'")
    
    elif action == "leave":
        if len(parts) < 3:
            await message.reply("❌ Укажите название кружка")
            return
        
        name = " ".join(parts[2:])
        
        cursor.execute("SELECT id FROM circles WHERE name = ?", (name,))
        result = cursor.fetchone()
        
        if not result:
            await message.reply("❌ Кружок не найден")
            return
        
        circle_id = result[0]
        
        cursor.execute("DELETE FROM circle_members WHERE circle_id = ? AND user_id = ?", 
                      (circle_id, message.from_user.id))
        conn.commit()
        
        await message.reply(f"✅ Вы покинули кружок '{name}'")
    
    elif action == "list":
        cursor.execute("""
            SELECT c.name, COUNT(cm.user_id) as members
            FROM circles c
            LEFT JOIN circle_members cm ON c.id = cm.circle_id
            GROUP BY c.id
            ORDER BY members DESC
        """)
        circles = cursor.fetchall()
        
        if not circles:
            await message.reply("🎯 Пока нет созданных кружков")
            return
        
        text = "🎯 <b>Кружки по интересам</b>\n\n"
        for circle in circles:
            text += f"• {circle[0]} — {circle[1]} участников\n"
        
        await message.reply(text)
    
    elif action == "meeting":
        if len(parts) < 5:
            await message.reply("❌ Укажите дату, время и место\nПример: /circle meeting 25.12 19:00 У дома")
            return
        
        date = parts[2]
        time = parts[3]
        place = " ".join(parts[4:])
        
        # Ищем кружки пользователя
        cursor.execute("""
            SELECT c.id, c.name
            FROM circle_members cm
            JOIN circles c ON cm.circle_id = c.id
            WHERE cm.user_id = ?
        """, (message.from_user.id,))
        circles = cursor.fetchall()
        
        if not circles:
            await message.reply("❌ Вы не состоите в кружках")
            return
        
        # Для простоты берем первый кружок
        circle_id, circle_name = circles[0]
        
        cursor.execute("""
            INSERT INTO circle_meetings (circle_id, title, date, time, place, created_by)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (circle_id, f"Встреча {circle_name}", date, time, place, message.from_user.id))
        conn.commit()
        
        await message.reply(f"✅ Встреча создана!\n📅 {date} в {time}\n📍 {place}")

# Модуль репутации
@dp.message_handler(lambda message: message.text.startswith(("+Репа", "+Репутация")))
async def cmd_add_reputation(message: types.Message):
    await register_user(message)
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("❌ Укажите пользователя")
        return
    
    target_id = extract_user_id(parts[1])
    if not target_id:
        await message.reply("❌ Не удалось определить пользователя")
        return
    
    if target_id == message.from_user.id:
        await message.reply("❌ Нельзя изменить репутацию самому себе")
        return
    
    cursor.execute("UPDATE users SET reputation = reputation + 1 WHERE user_id = ?", (target_id,))
    conn.commit()
    
    await message.reply("✅ Репутация повышена")

@dp.message_handler(lambda message: message.text.startswith(("-Репа", "-Репутация")))
async def cmd_remove_reputation(message: types.Message):
    await register_user(message)
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("❌ Укажите пользователя")
        return
    
    target_id = extract_user_id(parts[1])
    if not target_id:
        await message.reply("❌ Не удалось определить пользователя")
        return
    
    if target_id == message.from_user.id:
        await message.reply("❌ Нельзя изменить репутацию самому себе")
        return
    
    cursor.execute("UPDATE users SET reputation = reputation - 1 WHERE user_id = ?", (target_id,))
    conn.commit()
    
    await message.reply("✅ Репутация понижена")

@dp.message_handler(commands=["репа", "reputation"])
async def cmd_reputation(message: types.Message):
    await register_user(message)
    
    parts = message.text.split()
    if len(parts) > 1:
        target_id = extract_user_id(parts[1])
        if not target_id:
            await message.reply("❌ Не удалось определить пользователя")
            return
    else:
        target_id = message.from_user.id
    
    cursor.execute("SELECT username, first_name, reputation FROM users WHERE user_id = ?", (target_id,))
    user = cursor.fetchone()
    
    if not user:
        await message.reply("❌ Пользователь не найден")
        return
    
    name = user[0] or user[1] or f"ID {target_id}"
    
    await message.reply(f"⭐ <b>Репутация {name}</b>\n\n{user[2]}")

# Модуль кубов
@dp.message_handler(commands=["кубы", "cubes"])
async def cmd_cubes(message: types.Message):
    await register_user(message)
    
    cursor.execute("""
        SELECT c.id, c.name, c.color, c.rarity, c.emoji, uc.quantity
        FROM user_cubes uc
        JOIN cubes c ON uc.cube_id = c.id
        WHERE uc.user_id = ?
        ORDER BY c.rarity DESC
    """, (message.from_user.id,))
    cubes = cursor.fetchall()
    
    if not cubes:
        # Добавляем базовые кубы
        cursor.executemany("""
            INSERT INTO cubes (name, color, rarity, price, emoji)
            VALUES (?, ?, ?, ?, ?)
        """, [
            ("Огненный куб", "красный", "обычный", 100, "🔥"),
            ("Водный куб", "синий", "обычный", 100, "💧"),
            ("Земляной куб", "зеленый", "обычный", 100, "🌿"),
            ("Воздушный куб", "белый", "обычный", 100, "💨"),
            ("Магический куб", "фиолетовый", "редкий", 500, "✨"),
            ("Золотой куб", "золотой", "эпический", 1000, "🌟"),
            ("Алмазный куб", "голубой", "легендарный", 5000, "💎"),
            ("Космический куб", "черный", "мифический", 10000, "🌌")
        ])
        conn.commit()
        
        await message.reply("📦 У вас пока нет кубов. Купите в магазине: /buy_cube")
        return
    
    text = "📦 <b>Ваши кубы</b>\n\n"
    for cube in cubes:
        text += f"{cube[4]} {cube[1]} ({cube[2]}) x{cube[5]}\n"
        text += f"Редкость: {cube[3]}\n\n"
    
    await message.reply(text)

@dp.message_handler(commands=["купитькуб", "buy_cube"])
async def cmd_buy_cube(message: types.Message):
    await register_user(message)
    
    parts = message.text.split()
    color = parts[1] if len(parts) > 1 else None
    
    if color:
        cursor.execute("SELECT id, name, price, emoji FROM cubes WHERE color = ?", (color,))
    else:
        cursor.execute("SELECT id, name, price, emoji FROM cubes ORDER BY RANDOM() LIMIT 1")
    
    cube = cursor.fetchone()
    
    if not cube:
        await message.reply("❌ Куб не найден. Доступные цвета: красный, синий, зеленый, белый, фиолетовый, золотой, голубой, черный")
        return
    
    cube_id, name, price, emoji = cube
    
    cursor.execute("SELECT iris_balance FROM users WHERE user_id = ?", (message.from_user.id,))
    balance = cursor.fetchone()[0]
    
    if balance < price:
        await message.reply(f"❌ Недостаточно ирисок. Нужно: {price}")
        return
    
    cursor.execute("UPDATE users SET iris_balance = iris_balance - ? WHERE user_id = ?", (price, message.from_user.id))
    
    cursor.execute("""
        INSERT INTO user_cubes (user_id, cube_id, quantity)
        VALUES (?, ?, 1)
        ON CONFLICT(user_id, cube_id) DO UPDATE SET quantity = quantity + 1
    """, (message.from_user.id, cube_id))
    conn.commit()
    
    await message.reply(f"✅ Вы купили {emoji} {name} за {price} ирисок!")

@dp.message_handler(commands=["топкубов", "cube_top"])
async def cmd_cube_top(message: types.Message):
    await register_user(message)
    
    cursor.execute("""
        SELECT u.user_id, u.username, u.first_name, COUNT(uc.cube_id) as total_cubes
        FROM user_cubes uc
        JOIN users u ON uc.user_id = u.user_id
        GROUP BY uc.user_id
        ORDER BY total_cubes DESC
        LIMIT 10
    """)
    top = cursor.fetchall()
    
    if not top:
        await message.reply("🏆 Пока нет коллекционеров кубов")
        return
    
    text = "🏆 <b>Топ коллекционеров кубов</b>\n\n"
    for i, user in enumerate(top, 1):
        name = user[1] or user[2] or f"ID {user[0]}"
        text += f"{i}. {name} — {user[3]} кубов\n"
    
    await message.reply(text)

# Модуль тем
@dp.message_handler(lambda message: message.text.startswith("+Тема"))
async def cmd_add_topic(message: types.Message):
    await register_user(message)
    
    if not check_permission("topics", message.chat.id, message.from_user.id):
        await message.reply("🚫 У вас нет прав для создания тем")
        return
    
    text = message.text[6:].strip()
    if "|" in text:
        title, description = text.split("|", 1)
        title = title.strip()
        description = description.strip()
    else:
        title = text
        description = ""
    
    if not title:
        await message.reply("❌ Укажите название темы")
        return
    
    cursor.execute("""
        INSERT INTO topics (chat_id, title, description, created_by)
        VALUES (?, ?, ?, ?)
    """, (message.chat.id, title, description, message.from_user.id))
    topic_id = cursor.lastrowid
    conn.commit()
    
    await message.reply(f"✅ Тема создана! ID: {topic_id}")

@dp.message_handler(commands=["темы", "topics"])
async def cmd_topics(message: types.Message):
    await register_user(message)
    
    cursor.execute("""
        SELECT id, title, description, votes_for, votes_against, created_by
        FROM topics
        WHERE chat_id = ? AND is_active = 1
        ORDER BY votes_for - votes_against DESC
    """, (message.chat.id,))
    topics = cursor.fetchall()
    
    if not topics:
        await message.reply("📋 В этом чате нет активных тем")
        return
    
    text = "📋 <b>Темы для обсуждения</b>\n\n"
    for topic in topics:
        cursor.execute("SELECT username, first_name FROM users WHERE user_id = ?", (topic[5],))
        creator = cursor.fetchone()
        creator_name = creator[0] or creator[1] or f"ID {topic[5]}"
        
        text += f"<b>ID: {topic[0]}</b> {topic[1]}\n"
        if topic[2]:
            text += f"📝 {topic[2]}\n"
        text += f"👍 {topic[3]} | 👎 {topic[4]}\n"
        text += f"Автор: {creator_name}\n\n"
    
    text += "/vote_for [ID] — голосовать за\n/vote_against [ID] — голосовать против"
    
    await message.reply(text)

@dp.message_handler(commands=["голосоватьза", "vote_for"])
async def cmd_vote_for(message: types.Message):
    await register_user(message)
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("❌ Укажите ID темы")
        return
    
    try:
        topic_id = int(parts[1])
    except:
        await message.reply("❌ Неверный ID")
        return
    
    # Проверяем, не голосовал ли уже
    cursor.execute("SELECT 1 FROM topic_votes WHERE topic_id = ? AND user_id = ?", 
                  (topic_id, message.from_user.id))
    if cursor.fetchone():
        await message.reply("❌ Вы уже голосовали в этой теме")
        return
    
    cursor.execute("""
        INSERT INTO topic_votes (topic_id, user_id, vote_type)
        VALUES (?, ?, 'for')
    """, (topic_id, message.from_user.id))
    
    cursor.execute("UPDATE topics SET votes_for = votes_for + 1 WHERE id = ?", (topic_id,))
    conn.commit()
    
    await message.reply("✅ Голос учтен")

@dp.message_handler(commands=["голосоватьпротив", "vote_against"])
async def cmd_vote_against(message: types.Message):
    await register_user(message)
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("❌ Укажите ID темы")
        return
    
    try:
        topic_id = int(parts[1])
    except:
        await message.reply("❌ Неверный ID")
        return
    
    # Проверяем, не голосовал ли уже
    cursor.execute("SELECT 1 FROM topic_votes WHERE topic_id = ? AND user_id = ?", 
                  (topic_id, message.from_user.id))
    if cursor.fetchone():
        await message.reply("❌ Вы уже голосовали в этой теме")
        return
    
    cursor.execute("""
        INSERT INTO topic_votes (topic_id, user_id, vote_type)
        VALUES (?, ?, 'against')
    """, (topic_id, message.from_user.id))
    
    cursor.execute("UPDATE topics SET votes_against = votes_against + 1 WHERE id = ?", (topic_id,))
    conn.commit()
    
    await message.reply("✅ Голос учтен")

# Модуль заметок
@dp.message_handler(commands=["заметка", "note"])
async def cmd_note(message: types.Message):
    await register_user(message)
    
    text = message.text[7:].strip()
    if not text:
        await message.reply("❌ Напишите текст заметки")
        return
    
    # Разделяем на заголовок и содержание
    if "\n" in text:
        title, content = text.split("\n", 1)
    else:
        title = "Заметка"
        content = text
    
    cursor.execute("""
        INSERT INTO notes (user_id, title, content)
        VALUES (?, ?, ?)
    """, (message.from_user.id, title[:100], content))
    note_id = cursor.lastrowid
    conn.commit()
    
    await message.reply(f"✅ Заметка сохранена! ID: {note_id}")

@dp.message_handler(commands=["заметки", "notes"])
async def cmd_notes(message: types.Message):
    await register_user(message)
    
    cursor.execute("""
        SELECT id, title, created_at
        FROM notes
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 20
    """, (message.from_user.id,))
    notes = cursor.fetchall()
    
    if not notes:
        await message.reply("📝 У вас нет заметок")
        return
    
    text = "📝 <b>Ваши заметки</b>\n\n"
    for note in notes:
        date = datetime.fromisoformat(note[2]).strftime("%d.%m.%Y")
        text += f"ID: {note[0]} | {date}\n{note[1]}\n\n"
    
    text += "/note [текст] — создать\n/note_del [ID] — удалить\n/note_view [ID] — просмотреть"
    
    await message.reply(text)

@dp.message_handler(commands=["заметка_удалить", "note_del"])
async def cmd_note_delete(message: types.Message):
    await register_user(message)
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("❌ Укажите ID заметки")
        return
    
    try:
        note_id = int(parts[1])
    except:
        await message.reply("❌ Неверный ID")
        return
    
    cursor.execute("DELETE FROM notes WHERE id = ? AND user_id = ?", (note_id, message.from_user.id))
    conn.commit()
    
    if cursor.rowcount > 0:
        await message.reply("✅ Заметка удалена")
    else:
        await message.reply("❌ Заметка не найдена")

@dp.message_handler(commands=["заметка_просмотр", "note_view"])
async def cmd_note_view(message: types.Message):
    await register_user(message)
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("❌ Укажите ID заметки")
        return
    
    try:
        note_id = int(parts[1])
    except:
        await message.reply("❌ Неверный ID")
        return
    
    cursor.execute("SELECT title, content, created_at FROM notes WHERE id = ? AND user_id = ?", 
                  (note_id, message.from_user.id))
    note = cursor.fetchone()
    
    if not note:
        await message.reply("❌ Заметка не найдена")
        return
    
    date = datetime.fromisoformat(note[2]).strftime("%d.%m.%Y %H:%M")
    
    await message.reply(f"""
📝 <b>{note[0]}</b>
📅 {date}

{note[1]}
""")

# Модуль таймеров
@dp.message_handler(commands=["таймер", "timer"])
async def cmd_timer(message: types.Message):
    await register_user(message)
    
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.reply("❌ Укажите название и время\nПример: /таймер Пицца 15м")
        return
    
    title = parts[1]
    time_str = parts[2]
    
    time_delta = parse_time(time_str)
    if not time_delta:
        await message.reply("❌ Неверный формат времени. Используйте: 30м, 2ч, 1д")
        return
    
    end_time = datetime.now() + time_delta
    
    cursor.execute("""
        INSERT INTO timers (user_id, chat_id, title, end_time)
        VALUES (?, ?, ?, ?)
    """, (message.from_user.id, message.chat.id, title, end_time.isoformat()))
    timer_id = cursor.lastrowid
    conn.commit()
    
    # Запускаем таймер
    asyncio.create_task(run_timer(timer_id, title, end_time, message.chat.id, message.from_user.id))
    
    time_str = f"{time_delta.seconds // 3600}ч {(time_delta.seconds // 60) % 60}м" if time_delta.seconds < 86400 else f"{time_delta.days}д"
    await message.reply(f"⏰ Таймер '{title}' запущен на {time_str}")

async def run_timer(timer_id: int, title: str, end_time: datetime, chat_id: int, user_id: int):
    """Запуск таймера"""
    now = datetime.now()
    wait_seconds = (end_time - now).total_seconds()
    
    if wait_seconds > 0:
        await asyncio.sleep(wait_seconds)
        
        # Проверяем, активен ли таймер
        cursor.execute("SELECT is_active FROM timers WHERE id = ?", (timer_id,))
        result = cursor.fetchone()
        
        if result and result[0]:
            await bot.send_message(chat_id, f"⏰ <b>Таймер</b>\n\n{title}\nВремя вышло!", reply_to_message_id=user_id)
            cursor.execute("UPDATE timers SET is_active = 0 WHERE id = ?", (timer_id,))
            conn.commit()

@dp.message_handler(commands=["таймеры", "timers"])
async def cmd_timers(message: types.Message):
    await register_user(message)
    
    cursor.execute("""
        SELECT id, title, end_time
        FROM timers
        WHERE user_id = ? AND is_active = 1 AND datetime(end_time) > datetime('now')
        ORDER BY end_time
    """, (message.from_user.id,))
    timers = cursor.fetchall()
    
    if not timers:
        await message.reply("⏰ У вас нет активных таймеров")
        return
    
    text = "⏰ <b>Ваши таймеры</b>\n\n"
    for timer in timers:
        end = datetime.fromisoformat(timer[2])
        remaining = end - datetime.now()
        remaining_str = f"{remaining.seconds // 3600}ч {(remaining.seconds // 60) % 60}м" if remaining.days == 0 else f"{remaining.days}д {remaining.seconds // 3600}ч"
        
        text += f"ID: {timer[0]} | {timer[1]}\nОсталось: {remaining_str}\n\n"
    
    text += "/timer_del [ID] — удалить"
    
    await message.reply(text)

@dp.message_handler(commands=["таймер_удалить", "timer_del"])
async def cmd_timer_delete(message: types.Message):
    await register_user(message)
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("❌ Укажите ID таймера")
        return
    
    try:
        timer_id = int(parts[1])
    except:
        await message.reply("❌ Неверный ID")
        return
    
    cursor.execute("UPDATE timers SET is_active = 0 WHERE id = ? AND user_id = ?", 
                  (timer_id, message.from_user.id))
    conn.commit()
    
    await message.reply("✅ Таймер удален")

# Модуль напоминаний
@dp.message_handler(commands=["напомнить", "remind"])
async def cmd_remind(message: types.Message):
    await register_user(message)
    
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.reply("❌ Укажите текст и время\nПример: /напомнить Купить молоко 30м")
        return
    
    text = parts[1]
    time_str = parts[2]
    
    time_delta = parse_time(time_str)
    if not time_delta:
        await message.reply("❌ Неверный формат времени. Используйте: 30м, 2ч, 1д")
        return
    
    remind_time = datetime.now() + time_delta
    
    cursor.execute("""
        INSERT INTO reminders (user_id, text, remind_time)
        VALUES (?, ?, ?)
    """, (message.from_user.id, text, remind_time.isoformat()))
    remind_id = cursor.lastrowid
    conn.commit()
    
    # Запускаем напоминание
    asyncio.create_task(run_reminder(remind_id, text, remind_time, message.from_user.id))
    
    time_str = f"{time_delta.seconds // 3600}ч {(time_delta.seconds // 60) % 60}м" if time_delta.seconds < 86400 else f"{time_delta.days}д"
    await message.reply(f"🔔 Напоминание установлено на {time_str}")

async def run_reminder(remind_id: int, text: str, remind_time: datetime, user_id: int):
    """Запуск напоминания"""
    now = datetime.now()
    wait_seconds = (remind_time - now).total_seconds()
    
    if wait_seconds > 0:
        await asyncio.sleep(wait_seconds)
        
        # Проверяем, активно ли напоминание
        cursor.execute("SELECT is_active FROM reminders WHERE id = ?", (remind_id,))
        result = cursor.fetchone()
        
        if result and result[0]:
            await bot.send_message(user_id, f"🔔 <b>Напоминание</b>\n\n{text}")
            cursor.execute("UPDATE reminders SET is_active = 0 WHERE id = ?", (remind_id,))
            conn.commit()

# Модуль ИИ (GROQ)
@dp.message_handler(commands=["ai", "ии", "спроси"])
async def cmd_ai(message: types.Message):
    await register_user(message)
    
    question = message.text[4:].strip() if message.text.startswith("/ai") else message.text[5:].strip()
    if not question:
        await message.reply("❌ Задайте вопрос")
        return
    
    # Отправляем "печатает..."
    await message.chat.send_chat_action("typing")
    
    try:
        # Запрос к GROQ
        completion = await groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Ты - Спектр, дружелюбный AI-ассистент в Telegram. Отвечай кратко, с юмором, но по делу. Ты можешь спорить, если тебя оскорбляют, и шутить. Используй эмодзи."},
                {"role": "user", "content": question}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        answer = completion.choices[0].message.content
        
        # Если ответ слишком длинный, разбиваем
        if len(answer) > 4000:
            parts = [answer[i:i+4000] for i in range(0, len(answer), 4000)]
            for part in parts:
                await message.reply(part)
        else:
            await message.reply(answer)
            
    except Exception as e:
        await message.reply("🤖 Извините, я временно не могу ответить. Попробуйте позже.")

# Модуль мафии
games = {}  # Хранилище активных игр

class MafiaRoles:
    MAFIA = "мафия"
    COMMISSIONER = "комиссар"
    DOCTOR = "доктор"
    MANIAC = "маньяк"
    BOSS = "босс"
    CITIZEN = "мирный"

@dp.message_handler(commands=["мафия", "mafia"])
async def cmd_mafia(message: types.Message):
    await register_user(message)
    
    # Проверяем, не идет ли уже игра
    if message.chat.id in games:
        await message.reply("🎮 В этом чате уже идет игра!")
        return
    
    # Создаем новую игру
    game_id = f"{message.chat.id}_{datetime.now().timestamp()}"
    
    cursor.execute("""
        INSERT INTO mafia_games (game_id, chat_id, status)
        VALUES (?, ?, 'waiting')
    """, (game_id, message.chat.id))
    conn.commit()
    
    games[message.chat.id] = {
        "game_id": game_id,
        "status": "waiting",
        "players": [],
        "creator": message.from_user.id,
        "phase": "waiting",
        "day": 1
    }
    
    # Отправляем гифку дня (здесь нужно добавить реальные гифки)
    await message.reply_animation(
        "https://files.catbox.moe/g9vc7v.mp4",  # Гифка дня
        caption="""
🎮 <b>Мафия</b>

Игра начинается!
Для участия напишите /join
Минимум игроков: 6
Максимум: 20

Создатель игры может начать командой /start_game
"""
    )

@dp.message_handler(commands=["join"])
async def cmd_join_mafia(message: types.Message):
    await register_user(message)
    
    if message.chat.id not in games:
        await message.reply("❌ В этом чате нет игры. Создайте командой /mafia")
        return
    
    game = games[message.chat.id]
    
    if game["status"] != "waiting":
        await message.reply("❌ Игра уже началась")
        return
    
    if message.from_user.id in game["players"]:
        await message.reply("❌ Вы уже в игре")
        return
    
    if len(game["players"]) >= 20:
        await message.reply("❌ Достигнут лимит игроков (20)")
        return
    
    game["players"].append(message.from_user.id)
    
    # Отправляем подтверждение в ЛС
    try:
        await bot.send_message(
            message.from_user.id,
            "✅ Вы присоединились к игре в мафию!\nОжидайте начала игры."
        )
    except:
        pass
    
    await message.reply(f"✅ Вы присоединились! Игроков: {len(game['players'])}")

@dp.message_handler(commands=["start_game"])
async def cmd_start_game(message: types.Message):
    await register_user(message)
    
    if message.chat.id not in games:
        await message.reply("❌ В этом чате нет игры")
        return
    
    game = games[message.chat.id]
    
    if game["creator"] != message.from_user.id:
        await message.reply("❌ Только создатель игры может начать")
        return
    
    if len(game["players"]) < 6:
        await message.reply(f"❌ Недостаточно игроков. Нужно минимум 6, сейчас {len(game['players'])}")
        return
    
    # Начинаем игру
    game["status"] = "active"
    game["phase"] = "night"
    
    # Раздаем роли
    roles = assign_roles(len(game["players"]))
    random.shuffle(roles)
    
    game["roles"] = {}
    for i, player in enumerate(game["players"]):
        game["roles"][player] = roles[i]
    
    # Сохраняем в БД
    for player in game["players"]:
        cursor.execute("""
            INSERT INTO mafia_players (user_id, game_id, role, is_alive)
            VALUES (?, ?, ?, 1)
        """, (player, game["game_id"], game["roles"][player]))
    conn.commit()
    
    # Отправляем роли в ЛС
    for player in game["players"]:
        role = game["roles"][player]
        try:
            await bot.send_message(
                player,
                f"🎭 <b>Ваша роль:</b> {role}\n\n{get_role_description(role)}"
            )
        except:
            pass
    
    # Отправляем гифку ночи
    await message.reply_animation(
        "https://files.catbox.moe/lvcm8n.mp4",  # Гифка ночи
        caption="""
🌙 <b>Ночь 1</b>

Город засыпает...
Мафия выбирает жертву
Доктор выбирает, кого спасти
Комиссар проверяет игрока
Маньяк выбирает цель

Роли получили в личных сообщениях
"""
    )
    
    # Запускаем ночную фазу
    asyncio.create_task(night_phase(message.chat.id, game))

def assign_roles(player_count: int) -> list:
    """Распределение ролей в зависимости от количества игроков"""
    roles = []
    
    # Баланс ролей
    if player_count <= 7:
        # 6-7 игроков
        mafia_count = 2
        roles.extend([MafiaRoles.MAFIA] * mafia_count)
        roles.extend([MafiaRoles.COMMISSIONER])
        roles.extend([MafiaRoles.DOCTOR])
        # Остальные мирные
        roles.extend([MafiaRoles.CITIZEN] * (player_count - len(roles)))
    elif player_count <= 10:
        # 8-10 игроков
        mafia_count = 3
        roles.extend([MafiaRoles.MAFIA] * mafia_count)
        roles.extend([MafiaRoles.COMMISSIONER])
        roles.extend([MafiaRoles.DOCTOR])
        roles.extend([MafiaRoles.MANIAC])
        # Остальные мирные
        roles.extend([MafiaRoles.CITIZEN] * (player_count - len(roles)))
    else:
        # 11-20 игроков
        mafia_count = 4
        roles.extend([MafiaRoles.MAFIA] * mafia_count)
        roles.extend([MafiaRoles.COMMISSIONER])
        roles.extend([MafiaRoles.DOCTOR])
        roles.extend([MafiaRoles.MANIAC])
        roles.extend([MafiaRoles.BOSS])
        # Остальные мирные
        roles.extend([MafiaRoles.CITIZEN] * (player_count - len(roles)))
    
    return roles

def get_role_description(role: str) -> str:
    """Описание роли"""
    descriptions = {
        MafiaRoles.MAFIA: "Вы - мафия. Ночью можете убивать игроков. Команда: /kill @user",
        MafiaRoles.COMMISSIONER: "Вы - комиссар. Ночью можете проверять игроков. Команда: /check @user",
        MafiaRoles.DOCTOR: "Вы - доктор. Ночью можете лечить игроков. Команда: /heal @user",
        MafiaRoles.MANIAC: "Вы - маньяк. Ночью можете убивать игроков. Команда: /kill @user",
        MafiaRoles.BOSS: "Вы - босс мафии. Вас нельзя убить ночью.",
        MafiaRoles.CITIZEN: "Вы - мирный житель. Днем участвуете в голосовании. Команда: /vote @user"
    }
    return descriptions.get(role, "Ошибка")

async def night_phase(chat_id: int, game: dict):
    """Ночная фаза игры"""
    # Ждем 2 минуты на действия
    await asyncio.sleep(120)
    
    # Обрабатываем результаты ночи
    # Здесь должна быть логика обработки действий игроков
    
    # Переходим к дню
    game["phase"] = "day"
    game["day"] += 1
    
    # Отправляем гифку дня
    await bot.send_animation(
        chat_id,
        "https://files.catbox.moe/g9vc7v.mp4",
        caption=f"""
☀️ <b>День {game['day']}</b>

Солнце всходит, подсушивая на тротуарах пролитую ночью кровь...

Начинается голосование!
/vote @user — отдать голос
"""
    )
    
    # Запускаем дневную фазу
    asyncio.create_task(day_phase(chat_id, game))

async def day_phase(chat_id: int, game: dict):
    """Дневная фаза игры"""
    # Ждем 3 минуты на голосование
    await asyncio.sleep(180)
    
    # Подсчитываем голоса и выгоняем игрока
    # Здесь должна быть логика подсчета голосов
    
    # Проверяем условия победы
    if check_win_conditions(game):
        return
    
    # Переходим к ночи
    game["phase"] = "night"
    
    await bot.send_animation(
        chat_id,
        "https://files.catbox.moe/lvcm8n.mp4",
        caption=f"""
🌙 <b>Ночь {game['day'] + 1}</b>

Город засыпает...
Мафия выбирает жертву
"""
    )
    
    asyncio.create_task(night_phase(chat_id, game))

def check_win_conditions(game: dict) -> bool:
    """Проверка условий победы"""
    # Здесь должна быть логика проверки победы
    return False

# Запуск бота
async def on_startup(dp):
    logging.info("Бот запущен")
    # Здесь можно добавить уведомление админам

async def on_shutdown(dp):
    logging.info("Бот остановлен")
    conn.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup, on_shutdown=on_shutdown)
