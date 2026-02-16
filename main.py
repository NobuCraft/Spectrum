import asyncio
import logging
import random
import sqlite3
import datetime
from typing import Optional, Dict, Any, List
import aiohttp
import json
import os
import re
from collections import defaultdict
import time

# Для Telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from telegram.error import TelegramError, NetworkError

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===================== КОНФИГУРАЦИЯ =====================
TELEGRAM_TOKEN = "8326390250:AAFuUVHZ6ucUtLy132Ep1pmteRr6tTk7u0Q"
OWNER_ID = 1732658530
OWNER_USERNAME = "@NobuCraft"

# Список администраторов и модераторов (по имени)
ADMINS = [
    "Илья Евсевлеев",
    "Глеб Захаров",
    "Сергей Фросск",
    "Владимир Рычалкин",
    "Eva Zainchkovskaya",
    "Александр Омгресин",
    "Банов Алексей"
]

MODERATORS = [
    "Максим Добродушный"
]

# Статьи УК для рандома
ARTICLES = [
    {"number": "105", "name": "Убийство", "description": "Убийство, то есть умышленное причинение смерти другому человеку", "term": "от 6 до 15 лет"},
    {"number": "111", "name": "Умышленное причинение тяжкого вреда здоровью", "description": "Умышленное причинение тяжкого вреда здоровью", "term": "до 8 лет"},
    {"number": "112", "name": "Умышленное причинение средней тяжести вреда здоровью", "description": "Умышленное причинение средней тяжести вреда здоровью", "term": "до 3 лет"},
    {"number": "115", "name": "Умышленное причинение легкого вреда здоровью", "description": "Умышленное причинение легкого вреда здоровью", "term": "до 2 лет"},
    {"number": "116", "name": "Побои", "description": "Побои", "term": "до 2 лет"},
    {"number": "119", "name": "Угроза убийством", "description": "Угроза убийством или причинением тяжкого вреда здоровью", "term": "до 2 лет"},
    {"number": "126", "name": "Похищение человека", "description": "Похищение человека", "term": "от 4 до 8 лет"},
    {"number": "127", "name": "Незаконное лишение свободы", "description": "Незаконное лишение свободы", "term": "до 2 лет"},
    {"number": "128", "name": "Клевета", "description": "Клевета", "term": "до 1 года"},
    {"number": "129", "name": "Оскорбление", "description": "Оскорбление", "term": "до 1 года"},
    {"number": "130", "name": "Хулиганство", "description": "Хулиганство", "term": "до 5 лет"},
    {"number": "158", "name": "Кража", "description": "Кража", "term": "до 2 лет"},
    {"number": "159", "name": "Мошенничество", "description": "Мошенничество", "term": "до 2 лет"},
    {"number": "160", "name": "Присвоение или растрата", "description": "Присвоение или растрата", "term": "до 2 лет"},
    {"number": "161", "name": "Грабеж", "description": "Грабеж", "term": "до 4 лет"},
    {"number": "162", "name": "Разбой", "description": "Разбой", "term": "от 3 до 8 лет"},
    {"number": "163", "name": "Вымогательство", "description": "Вымогательство", "term": "до 4 лет"},
    {"number": "166", "name": "Неправомерное завладение автомобилем", "description": "Неправомерное завладение автомобилем или иным транспортным средством без цели хищения", "term": "до 2 лет"},
    {"number": "167", "name": "Умышленные уничтожение или повреждение имущества", "description": "Умышленные уничтожение или повреждение имущества", "term": "до 2 лет"},
    {"number": "168", "name": "Уничтожение или повреждение имущества по неосторожности", "description": "Уничтожение или повреждение имущества по неосторожности", "term": "до 1 года"},
    {"number": "205", "name": "Террористический акт", "description": "Террористический акт", "term": "от 8 до 15 лет"},
    {"number": "206", "name": "Захват заложника", "description": "Захват заложника", "term": "от 5 до 10 лет"},
    {"number": "207", "name": "Заведомо ложное сообщение об акте терроризма", "description": "Заведомо ложное сообщение об акте терроризма", "term": "до 3 лет"},
    {"number": "213", "name": "Хулиганство", "description": "Хулиганство", "term": "до 5 лет"},
    {"number": "214", "name": "Вандализм", "description": "Вандализм", "term": "до 1 года"},
    {"number": "228", "name": "Незаконные приобретение, хранение, перевозка наркотиков", "description": "Незаконные приобретение, хранение, перевозка наркотических средств", "term": "до 3 лет"},
    {"number": "261", "name": "Уничтожение или повреждение лесных насаждений", "description": "Уничтожение или повреждение лесных насаждений", "term": "до 1 года"}
]

# Настройки
SPAM_LIMIT = 5
SPAM_WINDOW = 3
SPAM_MUTE_TIME = 120

# Ранги пользователей
RANKS = {
    0: "👤 Новичок",
    1: "🌟 Активный",
    2: "⭐ Опытный",
    3: "✨ Ветеран",
    4: "💫 Легенда",
    5: "👑 Элита"
}

# Награды
ACHIEVEMENTS = {
    "first_blood": "🩸 Первая кровь - убить первого босса",
    "boss_killer_10": "👾 Охотник на боссов - убить 10 боссов",
    "boss_killer_50": "👾 Мастер охоты - убить 50 боссов",
    "boss_killer_100": "👾 Легендарный охотник - убить 100 боссов",
    "rich_1000": "💰 Богач - накопить 1000 монет",
    "rich_10000": "💰 Миллионер - накопить 10000 монет",
    "rich_100000": "💰 Магнат - накопить 100000 монет",
    "donator": "💎 Меценат - сделать первое пожертвование",
    "vip": "🌟 VIP статус",
    "premium": "💎 PREMIUM статус",
    "active_30": "📅 Завсегдатай - быть активным 30 дней",
    "active_100": "📅 Старожил - быть активным 100 дней",
    "silence_return": "🤫 Молчун - вернуться после долгого отсутствия",
    "article_1": "📜 Статья 261 - получить первую статью"
}

# ===================== БАЗА ДАННЫХ =====================
class Database:
    def __init__(self, db_name="spectrum_bot.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
        self.init_data()
    
    def create_tables(self):
        # Пользователи
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                coins INTEGER DEFAULT 1000,
                diamonds INTEGER DEFAULT 100,
                health INTEGER DEFAULT 100,
                max_health INTEGER DEFAULT 100,
                energy INTEGER DEFAULT 100,
                level INTEGER DEFAULT 1,
                exp INTEGER DEFAULT 0,
                power REAL DEFAULT 100.0,
                role TEXT DEFAULT 'user',
                warns INTEGER DEFAULT 0,
                mute_until TIMESTAMP,
                banned INTEGER DEFAULT 0,
                ban_reason TEXT,
                ban_date TIMESTAMP,
                banned_by INTEGER,
                last_active TIMESTAMP,
                regens INTEGER DEFAULT 3,
                vk_link TEXT,
                rank INTEGER DEFAULT 0,
                reputation INTEGER DEFAULT 0,
                reputation_given INTEGER DEFAULT 0,
                join_date TIMESTAMP,
                message_count INTEGER DEFAULT 0,
                boss_kills INTEGER DEFAULT 0,
                boss_hits INTEGER DEFAULT 0,
                donations INTEGER DEFAULT 0,
                articles TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Босс
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS boss (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                boss_name TEXT,
                boss_health INTEGER,
                boss_max_health INTEGER,
                boss_damage INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Статистика
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS stats (
                user_id INTEGER PRIMARY KEY,
                messages_count INTEGER DEFAULT 0,
                commands_used INTEGER DEFAULT 0,
                boss_hits INTEGER DEFAULT 0,
                boss_kills INTEGER DEFAULT 0,
                regen_used INTEGER DEFAULT 0,
                last_seen TIMESTAMP,
                total_online INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Баны (история)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS bans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                user_name TEXT,
                admin_id INTEGER,
                admin_name TEXT,
                reason TEXT,
                duration INTEGER,
                ban_date TIMESTAMP,
                unban_date TIMESTAMP,
                is_permanent INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (admin_id) REFERENCES users (user_id)
            )
        ''')
        
        # Муты (история)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS mutes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                user_name TEXT,
                admin_id INTEGER,
                admin_name TEXT,
                reason TEXT,
                duration INTEGER,
                mute_date TIMESTAMP,
                mute_until TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (admin_id) REFERENCES users (user_id)
            )
        ''')
        
        # Варны (история)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS warns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                user_name TEXT,
                admin_id INTEGER,
                admin_name TEXT,
                reason TEXT,
                warn_date TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (admin_id) REFERENCES users (user_id)
            )
        ''')
        
        # Инвентарь
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                item_name TEXT,
                item_type TEXT,
                quantity INTEGER DEFAULT 1,
                damage_bonus INTEGER DEFAULT 0,
                health_bonus INTEGER DEFAULT 0,
                energy_bonus INTEGER DEFAULT 0,
                description TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Магазин
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS shop (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT,
                item_type TEXT,
                price_coins INTEGER,
                price_diamonds INTEGER,
                damage_bonus INTEGER DEFAULT 0,
                health_bonus INTEGER DEFAULT 0,
                energy_bonus INTEGER DEFAULT 0,
                description TEXT
            )
        ''')
        
        # Автосообщения
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS auto_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT,
                interval_minutes INTEGER DEFAULT 60,
                enabled INTEGER DEFAULT 1
            )
        ''')
        
        # Настройки
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # Закладки
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message_id INTEGER,
                chat_id INTEGER,
                description TEXT,
                created_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Достижения
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                achievement_key TEXT,
                achieved_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                UNIQUE(user_id, achievement_key)
            )
        ''')
        
        # Переводы
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_id INTEGER,
                to_id INTEGER,
                amount INTEGER,
                currency TEXT,
                created_at TIMESTAMP,
                FOREIGN KEY (from_id) REFERENCES users (user_id),
                FOREIGN KEY (to_id) REFERENCES users (user_id)
            )
        ''')
        
        self.conn.commit()
        self.init_shop()
        self.init_boss()
        self.init_auto_messages()
    
    def init_shop(self):
        self.cursor.execute("SELECT * FROM shop")
        if not self.cursor.fetchone():
            shop_items = [
                ("🗡 Обычный меч", "weapon", 100, 0, 10, 0, 0, "Увеличивает урон на 10%"),
                ("⚔️ Стальной меч", "weapon", 300, 0, 25, 0, 0, "Увеличивает урон на 25%"),
                ("🔥 Огненный меч", "weapon", 0, 50, 50, 0, 0, "Увеличивает урон на 50%"),
                ("💎 Алмазный меч", "weapon", 0, 100, 100, 0, 0, "Увеличивает урон на 100%"),
                ("🛡 Деревянный щит", "armor", 50, 0, 0, 20, 0, "Увеличивает здоровье на 20"),
                ("⚜ Золотой щит", "armor", 200, 0, 0, 50, 0, "Увеличивает здоровье на 50"),
                ("🔮 Магический щит", "armor", 0, 80, 0, 100, 0, "Увеличивает здоровье на 100"),
                ("💊 Малое зелье", "potion", 30, 0, 0, 30, 0, "Восстанавливает 30 HP"),
                ("🧪 Большое зелье", "potion", 100, 0, 0, 100, 0, "Восстанавливает 100 HP"),
                ("⚡ Энергетик", "energy", 20, 0, 0, 0, 20, "Восстанавливает 20 энергии"),
                ("🔋 Батарейка", "energy", 50, 0, 0, 0, 50, "Восстанавливает 50 энергии"),
            ]
            for item in shop_items:
                self.cursor.execute('''
                    INSERT INTO shop (item_name, item_type, price_coins, price_diamonds, damage_bonus, health_bonus, energy_bonus, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', item)
            self.conn.commit()
    
    def init_boss(self):
        self.cursor.execute("SELECT * FROM boss")
        if not self.cursor.fetchone():
            self.cursor.execute('''
                INSERT INTO boss (boss_name, boss_health, boss_max_health, boss_damage)
                VALUES (?, ?, ?, ?)
            ''', ("🦟 Ядовитый комар", 2780, 2780, 34))
            self.conn.commit()
    
    def init_auto_messages(self):
        self.cursor.execute("SELECT * FROM auto_messages")
        if not self.cursor.fetchone():
            messages = [
                ("🔥 Не забывай атаковать босса! /boss_st", 30, 1),
                ("💪 Улучши своё оружие в магазине! /shop", 60, 1),
                ("💰 Зарабатывай монеты и алмазы!", 90, 1),
                ("👥 Приглашай друзей в игру!", 120, 1),
            ]
            for msg, interval, enabled in messages:
                self.cursor.execute('''
                    INSERT INTO auto_messages (message, interval_minutes, enabled)
                    VALUES (?, ?, ?)
                ''', (msg, interval, enabled))
            self.conn.commit()
    
    def get_user(self, user_id: int, first_name: str = "Player", username: str = ""):
        self.cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = self.cursor.fetchone()
        
        if not user:
            role = 'admin' if first_name in ADMINS else 'moderator' if first_name in MODERATORS else 'user'
            vk_link = f"https://vk.com/id{user_id}"
            join_date = datetime.datetime.now()
            self.cursor.execute('''
                INSERT INTO users (user_id, first_name, username, role, vk_link, join_date, last_active) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, first_name, username, role, vk_link, join_date, join_date))
            
            self.cursor.execute('''
                INSERT INTO stats (user_id, last_seen) VALUES (?, ?)
            ''', (user_id, join_date))
            
            self.conn.commit()
            return self.get_user(user_id, first_name, username)
        
        columns = [description[0] for description in self.cursor.description]
        return dict(zip(columns, user))
    
    def get_user_by_name(self, name: str):
        self.cursor.execute("SELECT * FROM users WHERE first_name LIKE ? OR username LIKE ?", (f"%{name}%", f"%{name}%"))
        return self.cursor.fetchone()
    
    def get_user_by_id(self, user_id: int):
        self.cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return self.cursor.fetchone()
    
    def add_coins(self, user_id: int, coins: int):
        self.cursor.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (coins, user_id))
        self.conn.commit()
        
        # Проверка достижений
        user = self.get_user(user_id)
        if user['coins'] >= 1000 and not self.has_achievement(user_id, "rich_1000"):
            self.add_achievement(user_id, "rich_1000")
        if user['coins'] >= 10000 and not self.has_achievement(user_id, "rich_10000"):
            self.add_achievement(user_id, "rich_10000")
        if user['coins'] >= 100000 and not self.has_achievement(user_id, "rich_100000"):
            self.add_achievement(user_id, "rich_100000")
    
    def add_diamonds(self, user_id: int, diamonds: int):
        self.cursor.execute("UPDATE users SET diamonds = diamonds + ? WHERE user_id = ?", (diamonds, user_id))
        self.conn.commit()
    
    def add_energy(self, user_id: int, energy: int):
        self.cursor.execute("UPDATE users SET energy = energy + ? WHERE user_id = ?", (energy, user_id))
        self.conn.commit()
    
    def add_power(self, user_id: int, power: int):
        self.cursor.execute("UPDATE users SET power = power + ? WHERE user_id = ?", (power, user_id))
        self.conn.commit()
    
    def heal(self, user_id: int, amount: int):
        self.cursor.execute("UPDATE users SET health = health + ? WHERE user_id = ?", (amount, user_id))
        if amount > 0:
            health = self.get_user(user_id)['health']
            max_health = self.get_user(user_id)['max_health']
            if health > max_health:
                self.cursor.execute("UPDATE users SET health = max_health WHERE user_id = ?", (user_id,))
        self.conn.commit()
    
    def damage(self, user_id: int, amount: int):
        self.cursor.execute("UPDATE users SET health = health - ? WHERE user_id = ?", (amount, user_id))
        self.conn.commit()
    
    def get_boss(self):
        self.cursor.execute("SELECT * FROM boss ORDER BY id DESC LIMIT 1")
        return self.cursor.fetchone()
    
    def damage_boss(self, damage):
        self.cursor.execute("UPDATE boss SET boss_health = boss_health - ?", (damage,))
        self.conn.commit()
        
        self.cursor.execute("SELECT boss_health FROM boss")
        health = self.cursor.fetchone()[0]
        
        if health <= 0:
            self.respawn_boss()
            return True
        return False
    
    def respawn_boss(self):
        new_bosses = [
            ("🦟 Ядовитый комар", 2780, 34),
            ("🐉 Огненный дракон", 5000, 50),
            ("👾 Космический монстр", 10000, 75),
            ("💀 Повелитель тьмы", 20000, 100),
            ("🧟 Зомби-апокалипсис", 15000, 60),
            ("🤖 Механический гигант", 25000, 120),
        ]
        boss = random.choice(new_bosses)
        self.cursor.execute("UPDATE boss SET boss_name = ?, boss_health = ?, boss_max_health = ?, boss_damage = ?", boss)
        self.conn.commit()
    
    def add_boss_kill(self, user_id: int):
        self.cursor.execute("UPDATE users SET boss_kills = boss_kills + 1 WHERE user_id = ?", (user_id,))
        self.conn.commit()
        
        user = self.get_user(user_id)
        kills = user['boss_kills']
        
        if kills >= 1 and not self.has_achievement(user_id, "first_blood"):
            self.add_achievement(user_id, "first_blood")
        if kills >= 10 and not self.has_achievement(user_id, "boss_killer_10"):
            self.add_achievement(user_id, "boss_killer_10")
        if kills >= 50 and not self.has_achievement(user_id, "boss_killer_50"):
            self.add_achievement(user_id, "boss_killer_50")
        if kills >= 100 and not self.has_achievement(user_id, "boss_killer_100"):
            self.add_achievement(user_id, "boss_killer_100")
    
    def add_stat(self, user_id: int, stat: str, value: int = 1):
        self.cursor.execute(f"UPDATE stats SET {stat} = {stat} + ? WHERE user_id = ?", (value, user_id))
        self.conn.commit()
    
    def update_last_seen(self, user_id):
        now = datetime.datetime.now()
        self.cursor.execute("UPDATE users SET last_active = ? WHERE user_id = ?", (now, user_id))
        
        # Обновляем общее время онлайн
        user = self.get_user(user_id)
        if user['last_active']:
            last = datetime.datetime.fromisoformat(user['last_active'])
            delta = now - last
            minutes = delta.total_seconds() / 60
            self.cursor.execute("UPDATE stats SET total_online = total_online + ? WHERE user_id = ?", (minutes, user_id))
        
        self.cursor.execute("UPDATE stats SET last_seen = ? WHERE user_id = ?", (now, user_id))
        self.conn.commit()
    
    def get_inactive_users(self, days=30):
        cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
        self.cursor.execute("SELECT user_id, first_name FROM users WHERE last_active < ?", (cutoff,))
        return self.cursor.fetchall()
    
    def get_shop_items(self, item_type=None):
        if item_type:
            self.cursor.execute("SELECT * FROM shop WHERE item_type = ?", (item_type,))
        else:
            self.cursor.execute("SELECT * FROM shop")
        return self.cursor.fetchall()
    
    def get_shop_item(self, item_id):
        self.cursor.execute("SELECT * FROM shop WHERE id = ?", (item_id,))
        return self.cursor.fetchone()
    
    def buy_item(self, user_id, item_id, currency):
        item = self.get_shop_item(item_id)
        if not item:
            return None
        
        user = self.get_user(user_id)
        
        if currency == 'coins' and user['coins'] >= item[3]:
            self.add_coins(user_id, -item[3])
            self.add_item(user_id, item[1], item[2], item[8], item[5], item[6], item[7])
            return item
        elif currency == 'diamonds' and user['diamonds'] >= item[4]:
            self.add_diamonds(user_id, -item[4])
            self.add_item(user_id, item[1], item[2], item[8], item[5], item[6], item[7])
            return item
        
        return None
    
    def add_item(self, user_id, item_name, item_type, description, damage_bonus=0, health_bonus=0, energy_bonus=0):
        self.cursor.execute('''
            INSERT INTO inventory (user_id, item_name, item_type, quantity, damage_bonus, health_bonus, energy_bonus, description)
            VALUES (?, ?, ?, 1, ?, ?, ?, ?)
        ''', (user_id, item_name, item_type, damage_bonus, health_bonus, energy_bonus, description))
        self.conn.commit()
    
    def get_inventory(self, user_id):
        self.cursor.execute("SELECT * FROM inventory WHERE user_id = ?", (user_id,))
        return self.cursor.fetchall()
    
    def use_item(self, user_id, item_id):
        self.cursor.execute("SELECT * FROM inventory WHERE id = ? AND user_id = ?", (item_id, user_id))
        item = self.cursor.fetchone()
        
        if item:
            if item[4] > 0:  # damage_bonus
                self.add_power(user_id, item[4])
            if item[5] > 0:  # health_bonus
                self.heal(user_id, item[5])
            if item[6] > 0:  # energy_bonus
                self.add_energy(user_id, item[6])
            
            if item[3] > 1:
                self.cursor.execute("UPDATE inventory SET quantity = quantity - 1 WHERE id = ?", (item_id,))
            else:
                self.cursor.execute("DELETE FROM inventory WHERE id = ?", (item_id,))
            self.conn.commit()
            return item
        return None
    
    def get_auto_messages(self, enabled_only=True):
        if enabled_only:
            self.cursor.execute("SELECT * FROM auto_messages WHERE enabled = 1")
        else:
            self.cursor.execute("SELECT * FROM auto_messages")
        return self.cursor.fetchall()
    
    def toggle_auto_messages(self):
        current = self.get_setting('auto_messages', 'on')
        new = 'off' if current == 'on' else 'on'
        self.set_setting('auto_messages', new)
        return new
    
    def is_auto_messages_on(self):
        return self.get_setting('auto_messages', 'on') == 'on'
    
    def get_setting(self, key, default=None):
        self.cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        result = self.cursor.fetchone()
        return result[0] if result else default
    
    def set_setting(self, key, value):
        self.cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        self.conn.commit()
    
    def get_player_count(self):
        self.cursor.execute("SELECT COUNT(*) FROM users")
        return self.cursor.fetchone()[0]
    
    def get_top(self, by="coins", limit=10):
        self.cursor.execute(f"SELECT first_name, {by} FROM users ORDER BY {by} DESC LIMIT ?", (limit,))
        return self.cursor.fetchall()
    
    # ==================== ЗАКЛАДКИ ====================
    
    def add_bookmark(self, user_id, message_id, chat_id, description):
        self.cursor.execute('''
            INSERT INTO bookmarks (user_id, message_id, chat_id, description, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, message_id, chat_id, description, datetime.datetime.now()))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_bookmarks(self, user_id):
        self.cursor.execute("SELECT * FROM bookmarks WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        return self.cursor.fetchall()
    
    def get_bookmark(self, bookmark_id, user_id):
        self.cursor.execute("SELECT * FROM bookmarks WHERE id = ? AND user_id = ?", (bookmark_id, user_id))
        return self.cursor.fetchone()
    
    def delete_bookmark(self, bookmark_id, user_id):
        self.cursor.execute("DELETE FROM bookmarks WHERE id = ? AND user_id = ?", (bookmark_id, user_id))
        self.conn.commit()
    
    # ==================== ДОСТИЖЕНИЯ ====================
    
    def add_achievement(self, user_id, achievement_key):
        if achievement_key in ACHIEVEMENTS:
            self.cursor.execute('''
                INSERT OR IGNORE INTO achievements (user_id, achievement_key, achieved_at)
                VALUES (?, ?, ?)
            ''', (user_id, achievement_key, datetime.datetime.now()))
            self.conn.commit()
            return True
        return False
    
    def has_achievement(self, user_id, achievement_key):
        self.cursor.execute("SELECT * FROM achievements WHERE user_id = ? AND achievement_key = ?", (user_id, achievement_key))
        return self.cursor.fetchone() is not None
    
    def get_achievements(self, user_id):
        self.cursor.execute("SELECT achievement_key, achieved_at FROM achievements WHERE user_id = ? ORDER BY achieved_at DESC", (user_id,))
        return self.cursor.fetchall()
    
    # ==================== ТРАНЗАКЦИИ ====================
    
    def add_transaction(self, from_id, to_id, amount, currency):
        self.cursor.execute('''
            INSERT INTO transactions (from_id, to_id, amount, currency, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (from_id, to_id, amount, currency, datetime.datetime.now()))
        self.conn.commit()
    
    def get_transactions(self, user_id, limit=10):
        self.cursor.execute('''
            SELECT * FROM transactions WHERE from_id = ? OR to_id = ? ORDER BY created_at DESC LIMIT ?
        ''', (user_id, user_id, limit))
        return self.cursor.fetchall()
    
    # ==================== БАНЫ, МУТЫ, ВАРНЫ ====================
    
    def mute_user(self, user_id: int, minutes: int, admin_id: int, reason: str = "Нарушение"):
        mute_until = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
        self.cursor.execute("UPDATE users SET mute_until = ? WHERE user_id = ?", (mute_until, user_id))
        
        admin = self.get_user(admin_id)
        user = self.get_user(user_id)
        
        self.cursor.execute('''
            INSERT INTO mutes (user_id, user_name, admin_id, admin_name, reason, duration, mute_date, mute_until)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, user['first_name'], admin_id, admin['first_name'], reason, minutes, datetime.datetime.now(), mute_until))
        
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
                minutes = remaining.seconds // 60
                seconds = remaining.seconds % 60
                return f"{minutes} мин {seconds} сек"
        return "0"
    
    def get_mutes(self, page=1, per_page=10):
        offset = (page - 1) * per_page
        self.cursor.execute('''
            SELECT * FROM mutes ORDER BY mute_date DESC LIMIT ? OFFSET ?
        ''', (per_page, offset))
        return self.cursor.fetchall()
    
    def get_mutes_count(self):
        self.cursor.execute("SELECT COUNT(*) FROM mutes")
        return self.cursor.fetchone()[0]
    
    def add_warn(self, user_id: int, admin_id: int, reason: str = "Нарушение"):
        self.cursor.execute("UPDATE users SET warns = warns + 1 WHERE user_id = ?", (user_id,))
        
        admin = self.get_user(admin_id)
        user = self.get_user(user_id)
        
        self.cursor.execute('''
            INSERT INTO warns (user_id, user_name, admin_id, admin_name, reason, warn_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, user['first_name'], admin_id, admin['first_name'], reason, datetime.datetime.now()))
        
        self.conn.commit()
        
        self.cursor.execute("SELECT warns FROM users WHERE user_id = ?", (user_id,))
        warns = self.cursor.fetchone()[0]
        
        if warns >= 3:
            self.mute_user(user_id, 1440, admin_id, "3 предупреждения")
            return f"⚠️ Пользователь получил 3 варна и был замучен на 24 часа!"
        return f"⚠️ Пользователь получил варн ({warns}/3)"
    
    def get_warns(self, user_id=None, page=1, per_page=10):
        offset = (page - 1) * per_page
        if user_id:
            self.cursor.execute('''
                SELECT * FROM warns WHERE user_id = ? ORDER BY warn_date DESC LIMIT ? OFFSET ?
            ''', (user_id, per_page, offset))
        else:
            self.cursor.execute('''
                SELECT * FROM warns ORDER BY warn_date DESC LIMIT ? OFFSET ?
            ''', (per_page, offset))
        return self.cursor.fetchall()
    
    def get_warns_count(self, user_id=None):
        if user_id:
            self.cursor.execute("SELECT COUNT(*) FROM warns WHERE user_id = ?", (user_id,))
        else:
            self.cursor.execute("SELECT COUNT(*) FROM warns")
        return self.cursor.fetchone()[0]
    
    def ban_user(self, user_id: int, admin_id: int, reason: str = "Нарушение", duration: int = 0):
        is_permanent = 1 if duration == 0 else 0
        unban_date = None if duration == 0 else datetime.datetime.now() + datetime.timedelta(minutes=duration)
        
        self.cursor.execute('''
            UPDATE users SET banned = 1, ban_reason = ?, ban_date = ?, banned_by = ? WHERE user_id = ?
        ''', (reason, datetime.datetime.now(), admin_id, user_id))
        
        admin = self.get_user(admin_id)
        user = self.get_user(user_id)
        
        self.cursor.execute('''
            INSERT INTO bans (user_id, user_name, admin_id, admin_name, reason, duration, ban_date, unban_date, is_permanent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, user['first_name'], admin_id, admin['first_name'], reason, duration, datetime.datetime.now(), unban_date, is_permanent))
        
        self.conn.commit()
    
    def unban_user(self, user_id: int):
        self.cursor.execute("UPDATE users SET banned = 0, warns = 0 WHERE user_id = ?", (user_id,))
        self.conn.commit()
    
    def is_banned(self, user_id: int) -> bool:
        self.cursor.execute("SELECT banned FROM users WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()
        return result and result[0] == 1
    
    def get_bans(self, page=1, per_page=10):
        offset = (page - 1) * per_page
        self.cursor.execute('''
            SELECT * FROM bans ORDER BY ban_date DESC LIMIT ? OFFSET ?
        ''', (per_page, offset))
        return self.cursor.fetchall()
    
    def get_bans_count(self):
        self.cursor.execute("SELECT COUNT(*) FROM bans")
        return self.cursor.fetchone()[0]
    
    def is_admin(self, user_id: int) -> bool:
        user = self.get_user(user_id)
        return user['role'] in ['admin', 'moderator']
    
    def is_owner(self, user_id: int) -> bool:
        return user_id == OWNER_ID
    
    def get_random_article(self):
        return random.choice(ARTICLES)
    
    def add_article(self, user_id, article_number):
        user = self.get_user(user_id)
        articles = user['articles'] or ''
        if articles:
            articles += f",{article_number}"
        else:
            articles = article_number
        self.cursor.execute("UPDATE users SET articles = ? WHERE user_id = ?", (articles, user_id))
        self.conn.commit()
        
        if article_number == "261" and not self.has_achievement(user_id, "article_1"):
            self.add_achievement(user_id, "article_1")
    
    def add_reputation(self, user_id, amount, giver_id):
        self.cursor.execute("UPDATE users SET reputation = reputation + ? WHERE user_id = ?", (amount, user_id))
        self.cursor.execute("UPDATE users SET reputation_given = reputation_given + ? WHERE user_id = ?", (1, giver_id))
        self.conn.commit()
    
    def get_rank(self, user_id):
        user = self.get_user(user_id)
        days_active = (datetime.datetime.now() - datetime.datetime.fromisoformat(user['join_date'])).days
        
        if days_active < 30:
            return 0
        elif days_active < 100:
            return 1
        elif days_active < 300:
            return 2
        elif days_active < 500:
            return 3
        elif days_active < 1000:
            return 4
        else:
            return 5
    
    def get_rank_name(self, rank):
        return RANKS.get(rank, "👤 Новичок")
    
    def format_duration(self, seconds):
        minutes = seconds // 60
        hours = minutes // 60
        days = hours // 24
        months = days // 30
        years = days // 365
        
        if years > 0:
            return f"{years} г"
        elif months > 0:
            return f"{months} мес"
        elif days > 0:
            return f"{days} д"
        elif hours > 0:
            return f"{hours} ч"
        elif minutes > 0:
            return f"{minutes} мин"
        else:
            return f"{seconds} сек"
    
    def close(self):
        self.conn.close()

# ===================== БАЗА ДАННЫХ =====================
db = Database()

# ===================== ОСНОВНОЙ КЛАСС БОТА =====================
class GameBot:
    def __init__(self):
        self.db = db
        self.spam_tracker = defaultdict(list)
        self.application = Application.builder().token(TELEGRAM_TOKEN).build()
        self.auto_message_task = None
        self.setup_handlers()
        logger.info("✅ Бот инициализирован")
    
    def setup_handlers(self):
        # Основные команды
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("menu", self.cmd_menu))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        
        # Босс
        self.application.add_handler(CommandHandler("boss", self.cmd_boss))
        self.application.add_handler(CommandHandler("boss_st", self.cmd_boss_st))
        self.application.add_handler(CommandHandler("boss_info", self.cmd_boss_info))
        
        # Магазин и донаты
        self.application.add_handler(CommandHandler("shop", self.cmd_shop))
        self.application.add_handler(CommandHandler("donate", self.cmd_donate))
        self.application.add_handler(CommandHandler("buy", self.cmd_buy))
        
        # Платежи
        self.application.add_handler(CommandHandler("payd", self.cmd_payd))
        self.application.add_handler(CommandHandler("payh", self.cmd_payh))
        
        # Регенерация
        self.application.add_handler(CommandHandler("regen", self.cmd_regen))
        
        # Автосообщения
        self.application.add_handler(CommandHandler("automes", self.cmd_automes))
        
        # Правила
        self.application.add_handler(CommandHandler("rules", self.cmd_rules))
        
        # Снять мут
        self.application.add_handler(CommandHandler("namutebuy", self.cmd_namutebuy))
        
        # Игроки
        self.application.add_handler(CommandHandler("players", self.cmd_players))
        self.application.add_handler(CommandHandler("player", self.cmd_player))
        self.application.add_handler(CommandHandler("top", self.cmd_top))
        
        # Команды донатеров
        self.application.add_handler(CommandHandler("cmd", self.cmd_donator_commands))
        
        # Бесплатные заряды
        self.application.add_handler(CommandHandler("eng", self.cmd_eng))
        
        # Личные сообщения
        self.application.add_handler(CommandHandler("sms", self.cmd_sms))
        
        # Моя статья
        self.application.add_handler(CommandHandler("моя_статья", self.cmd_my_article))
        
        # Кто я
        self.application.add_handler(CommandHandler("кто_я", self.cmd_whoami))
        
        # Бан-лист, мут-лист, варн-лист
        self.application.add_handler(CommandHandler("banlist", self.cmd_banlist))
        self.application.add_handler(CommandHandler("mutelist", self.cmd_mutelist))
        self.application.add_handler(CommandHandler("warnlist", self.cmd_warnlist))
        
        # Закладки
        self.application.add_handler(CommandHandler("закладка", self.cmd_add_bookmark))
        self.application.add_handler(CommandHandler("закладки", self.cmd_bookmarks))
        
        # Достижения
        self.application.add_handler(CommandHandler("достижения", self.cmd_achievements))
        
        # Админские команды
        self.application.add_handler(CommandHandler("mute", self.cmd_mute))
        self.application.add_handler(CommandHandler("warn", self.cmd_warn))
        self.application.add_handler(CommandHandler("ban", self.cmd_ban))
        self.application.add_handler(CommandHandler("unban", self.cmd_unban))
        
        # Обработчики
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        logger.info("✅ Все обработчики зарегистрированы")
    
    def get_main_menu_keyboard(self):
        keyboard = [
            [InlineKeyboardButton("👊 Ударить босса", callback_data="boss_st"),
             InlineKeyboardButton("🔄 Регенерация", callback_data="regen")],
            [InlineKeyboardButton("🛍 Магазин", callback_data="shop"),
             InlineKeyboardButton("💎 Донат", callback_data="donate")],
            [InlineKeyboardButton("👥 Игроки", callback_data="players"),
             InlineKeyboardButton("🏆 Топ", callback_data="top")],
            [InlineKeyboardButton("📖 Правила", callback_data="rules"),
             InlineKeyboardButton("📞 Помощь", callback_data="help")],
            [InlineKeyboardButton("🚫 Бан-лист", callback_data="banlist_1"),
             InlineKeyboardButton("🔇 Мут-лист", callback_data="mutelist_1")],
            [InlineKeyboardButton("⚠️ Варн-лист", callback_data="warnlist_1"),
             InlineKeyboardButton("📌 Закладки", callback_data="bookmarks")],
            [InlineKeyboardButton("🏆 Достижения", callback_data="achievements"),
             InlineKeyboardButton("📜 Моя статья", callback_data="my_article")]
        ]
        return keyboard
    
    def get_back_button(self):
        return [InlineKeyboardButton("🔙 Назад", callback_data="menu_back")]
    
    def get_pagination_keyboard(self, list_type, page, total_pages):
        keyboard = []
        nav_row = []
        
        if page > 1:
            nav_row.append(InlineKeyboardButton("◀️ Назад", callback_data=f"{list_type}_{page-1}"))
        
        nav_row.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
        
        if page < total_pages:
            nav_row.append(InlineKeyboardButton("Вперед ▶️", callback_data=f"{list_type}_{page+1}"))
        
        keyboard.append(nav_row)
        keyboard.append([InlineKeyboardButton("🔙 В меню", callback_data="menu_back")])
        
        return keyboard
    
    def is_admin(self, user_id: int) -> bool:
        return self.db.is_admin(user_id)
    
    def is_owner(self, user_id: int) -> bool:
        return user_id == OWNER_ID
    
    async def check_spam(self, update: Update) -> bool:
        user_id = update.effective_user.id
        if self.is_admin(user_id) or self.is_owner(user_id):
            return False
        
        current_time = time.time()
        self.spam_tracker[user_id] = [t for t in self.spam_tracker[user_id] if current_time - t < SPAM_WINDOW]
        self.spam_tracker[user_id].append(current_time)
        
        if len(self.spam_tracker[user_id]) > SPAM_LIMIT:
            self.db.mute_user(user_id, SPAM_MUTE_TIME, 0, "Автоматический спам")
            await update.message.reply_text(f"🚫 **СПАМ-ФИЛЬТР**\n\nВы замучены на {SPAM_MUTE_TIME} минут.")
            self.spam_tracker[user_id] = []
            return True
        return False
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id, user.first_name, user.username or "")
        self.db.update_last_seen(user.id)
        
        # Проверка на долгое отсутствие
        last_seen = user_data.get('last_active')
        if last_seen:
            last_date = datetime.datetime.fromisoformat(last_seen)
            days_ago = (datetime.datetime.now() - last_date).days
            if days_ago > 30:
                await self.announce_return(user.first_name)
                if not self.db.has_achievement(user.id, "silence_return"):
                    self.db.add_achievement(user.id, "silence_return")
        
        boss = self.db.get_boss()
        
        text = (
            f"╔══════════════════════════════╗\n"
            f"║  ⚔️ **ДОБРО ПОЖАЛОВАТЬ!** ⚔️  ║\n"
            f"╚══════════════════════════════╝\n\n"
            
            f"🔥 **{user.first_name}**, добро пожаловать на арену!\n"
            f"↪️ Ваша цель - убить босса.\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💀 **ТЕКУЩИЙ БОСС**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"▫️ **Имя:** {boss[1]}\n"
            f"▫️ **Здоровье:** {boss[2]}/{boss[3]} ❤️\n"
            f"▫️ **Урон от босса:** -{boss[4]} HP\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🗡 **ТВОИ ХАРАКТЕРИСТИКИ**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"▫️ **Здоровье:** {user_data['health']}/{user_data['max_health']} ❤️\n"
            f"▫️ **Уровень силы:** {user_data['power']:.2f}%\n"
            f"▫️ **Энергия:** {user_data['energy']} ⚡\n"
            f"▫️ **Регенераций:** {user_data['regens']} 🔄\n"
            f"▫️ **Монеты:** {user_data['coins']} 🪙\n"
            f"▫️ **Алмазы:** {user_data['diamonds']} 💎\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏺ **ОСНОВНЫЕ КОМАНДЫ**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👊 /boss_st — ударить босса\n"
            f"➕ /regen — регенерация\n"
            f"🛍 /shop — магазин\n"
            f"💎 /donate — донат\n"
            f"👥 /players — игроки\n"
            f"📖 /rules — правила\n"
            f"📜 /моя_статья — получить статью\n"
            f"👤 /кто_я — мой профиль\n\n"
            
            f"👑 **Владелец:** {OWNER_USERNAME}"
        )
        
        keyboard = self.get_main_menu_keyboard()
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        self.db.add_stat(user.id, "commands_used")
    
    async def announce_return(self, name):
        for chat_id in [OWNER_ID]:
            try:
                await self.application.bot.send_message(
                    chat_id=chat_id,
                    text=f"⚡️⚡️⚡️ **Святые угодники!**\n{name} заговорил после более, чем месячного молчания!!! Поприветствуйте молчуна! 👏",
                    parse_mode='Markdown'
                )
            except:
                pass
    
    async def cmd_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = self.get_main_menu_keyboard()
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🎮 **ГЛАВНОЕ МЕНЮ**\n\nВыбери действие:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        text = (
            "📚 **ВСЕ КОМАНДЫ БОТА**\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚔️ **БОСС**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ /boss — информация о боссе\n"
            "▫️ /boss_st — ударить босса\n"
            "▫️ /regen — регенерация здоровья\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🛍 **МАГАЗИН И ДОНАТЫ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ /shop — магазин\n"
            "▫️ /donate — донаты\n"
            "▫️ /buy [ID] [монеты/алмазы] — купить предмет\n"
            "▫️ /payd [ник] [сумма] — передать монеты\n"
            "▫️ /payh [ник] [сумма] — передать алмазы\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "👥 **ИГРОКИ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ /players — количество игроков\n"
            "▫️ /player [ник] — профиль игрока\n"
            "▫️ /кто_я — мой профиль\n"
            "▫️ /top — топ игроков\n"
            "▫️ /sms [ник] [текст] — личное сообщение\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚙️ **НАСТРОЙКИ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ /automes on/off — автосообщения\n"
            "▫️ /namutebuy — снять мут\n"
            "▫️ /eng — получить энергию\n"
            "▫️ /rules — правила\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📜 **СТАТЬИ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ /моя_статья — получить случайную статью\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📌 **ЗАКЛАДКИ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ +закладка [описание] — создать закладку\n"
            "▫️ /закладки — список закладок\n"
            "▫️ /закладка [номер] — перейти к закладке\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🏆 **ДОСТИЖЕНИЯ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ /достижения — мои достижения\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📋 **СПИСКИ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ /banlist — список забаненных\n"
            "▫️ /mutelist — список замученных\n"
            "▫️ /warnlist — список предупреждений\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "👑 **АДМИН КОМАНДЫ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ /mute [ник] [минут] [причина] — замутить\n"
            "▫️ /warn [ник] [причина] — выдать варн\n"
            "▫️ /ban [ник] [минут] [причина] — забанить (0 = навсегда)\n"
            "▫️ /unban [ник] — разбанить\n\n"
            
            f"👑 **Владелец:** {OWNER_USERNAME}"
        )
        
        keyboard = [self.get_back_button()]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        self.db.add_stat(user.id, "commands_used")
    
    async def cmd_boss(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        boss = self.db.get_boss()
        
        if user_data['health'] <= 0:
            await update.message.reply_text(
                f"❎ [{user.first_name}], вам нужно восстановить жизни, чтобы ударить босса!\n"
                f"❓ Чтобы восстановить жизни, напишите в чат \"Регенерация\" или используйте /regen"
            )
            return
        
        text = (
            f"╔══════════════════════════════╗\n"
            f"║    👾 **БИТВА С БОССОМ**    ║\n"
            f"╚══════════════════════════════╝\n\n"
            
            f"🔥 [{user.first_name}], добро пожаловать на арену!\n"
            f"↪️ Ваша цель убить босса.\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💀 **ТЕКУЩИЙ БОСС**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"▫️ **Имя:** {boss[1]}\n"
            f"▫️ **Урон от босса:** -{boss[4]} HP\n"
            f"▫️ **Жизни босса:** {boss[2]} HP\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🗡 **ТВОИ ХАРАКТЕРИСТИКИ**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"▫️ **Уровень силы:** {user_data['power']:.2f}%\n"
            f"▫️ **Твое здоровье:** {user_data['health']}/{user_data['max_health']} ❤️\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏺ **КОМАНДЫ**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👊 /boss_st — ударить босса\n"
            f"➕ /regen — регенерация\n"
            f"🗡 /shop — магазин оружия"
        )
        
        keyboard = [
            [InlineKeyboardButton("👊 Ударить босса", callback_data="boss_st"),
             InlineKeyboardButton("🔄 Регенерация", callback_data="regen")],
            self.get_back_button()
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def cmd_boss_st(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id, user.first_name, user.username or "")
        
        if self.db.is_muted(user.id):
            remaining = self.db.get_mute_time(user.id)
            await update.message.reply_text(f"🔇 Вы замучены. Осталось: {remaining}")
            return
        
        if user_data['health'] <= 0:
            await update.message.reply_text(
                f"❎ [{user.first_name}], вам нужно восстановить жизни, чтобы ударить босса!\n"
                f"❓ Чтобы восстановить жизни, напишите в чат \"Регенерация\" или используйте /regen"
            )
            return
        
        if user_data['energy'] < 10:
            await update.message.reply_text("❌ Недостаточно энергии! Купи энергию в магазине или используй /eng")
            return
        
        self.db.add_energy(user.id, -10)
        
        # Расчет урона
        player_damage = int(10 * (user_data['power'] / 100))
        boss = self.db.get_boss()
        player_taken = boss[4]
        
        self.db.damage(user.id, player_taken)
        boss_killed = self.db.damage_boss(player_damage)
        self.db.add_stat(user.id, "boss_hits", 1)
        
        if user_data['health'] <= player_taken:
            self.db.heal(user.id, 20)
            await update.message.reply_text("💀 Вы погибли в бою, но воскресли с 20 HP!")
        
        if boss_killed:
            # Награда за убийство босса
            coins_reward = random.randint(100, 500)
            diamonds_reward = random.randint(1, 10)
            self.db.add_coins(user.id, coins_reward)
            self.db.add_diamonds(user.id, diamonds_reward)
            self.db.add_boss_kill(user.id)
            
            boss = self.db.get_boss()
            await update.message.reply_text(
                f"🎉 **БОСС ПОВЕРЖЕН!** 🎉\n\n"
                f"Появился новый босс: **{boss[1]}**\n"
                f"❤️ Здоровье: {boss[2]}/{boss[3]}\n\n"
                f"💰 Награда: +{coins_reward} монет, +{diamonds_reward} алмазов!"
            )
        else:
            boss = self.db.get_boss()
            await update.message.reply_text(
                f"👊 **УДАР ПО БОССУ**\n\n"
                f"▫️ **Твой урон:** {player_damage}\n"
                f"▫️ **Урон от босса:** {player_taken}\n"
                f"▫️ **Твое здоровье:** {user_data['health'] - player_taken}/{user_data['max_health']} ❤️\n"
                f"▫️ **Здоровье босса:** {boss[2]}/{boss[3]} ❤️"
            )
    
    async def cmd_boss_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        boss = self.db.get_boss()
        await update.message.reply_text(
            f"👾 **ИНФОРМАЦИЯ О БОССЕ**\n\n"
            f"▫️ **Имя:** {boss[1]}\n"
            f"▫️ **Здоровье:** {boss[2]}/{boss[3]} ❤️\n"
            f"▫️ **Урон:** {boss[4]} HP"
        )
    
    async def cmd_shop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        weapons = self.db.get_shop_items('weapon')
        armors = self.db.get_shop_items('armor')
        potions = self.db.get_shop_items('potion')
        energies = self.db.get_shop_items('energy')
        
        text = (
            "╔══════════════════════════════╗\n"
            "║       🛍 **МАГАЗИН**         ║\n"
            "╚══════════════════════════════╝\n\n"
        )
        
        text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "⚔️ **ОРУЖИЕ**\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        for item in weapons:
            text += f"**ID: {item[0]}** {item[1]}\n"
            text += f"└ 💰 {item[3]} монет | 💎 {item[4]} алмазов\n"
            text += f"└ {item[8]}\n\n"
        
        text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "🛡 **БРОНЯ**\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        for item in armors:
            text += f"**ID: {item[0]}** {item[1]}\n"
            text += f"└ 💰 {item[3]} монет | 💎 {item[4]} алмазов\n"
            text += f"└ {item[8]}\n\n"
        
        text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "💊 **ЗЕЛЬЯ**\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        for item in potions:
            text += f"**ID: {item[0]}** {item[1]}\n"
            text += f"└ 💰 {item[3]} монет | 💎 {item[4]} алмазов\n"
            text += f"└ {item[8]}\n\n"
        
        text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "⚡ **ЭНЕРГИЯ**\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        for item in energies:
            text += f"**ID: {item[0]}** {item[1]}\n"
            text += f"└ 💰 {item[3]} монет | 💎 {item[4]} алмазов\n"
            text += f"└ {item[8]}\n\n"
        
        text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "🛒 **Купить:** /buy [ID] [монеты/алмазы]\n"
        text += "Пример: /buy 1 монеты"
        
        keyboard = [self.get_back_button()]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def cmd_donate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "╔══════════════════════════════╗\n"
            "║       💎 **ДОНАТ**           ║\n"
            "╚══════════════════════════════╝\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**VIP СТАТУСЫ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ **VIP** — 500 💎\n"
            "  • +50% к урону\n"
            "  • +50% к регенерации\n"
            "  • Без спам-фильтра\n\n"
            
            "▫️ **PREMIUM** — 1000 💎\n"
            "  • +100% к урону\n"
            "  • +100% к регенерации\n"
            "  • Ежедневные бонусы\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**РЕСУРСЫ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ 100 монет — 10 💎\n"
            "▫️ 1000 монет — 90 💎\n"
            "▫️ 10000 монет — 800 💎\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**ЭНЕРГИЯ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ 100 энергии — 20 💎\n"
            "▫️ 500 энергии — 90 💎\n\n"
            
            f"👑 По вопросам доната: {OWNER_USERNAME}"
        )
        
        keyboard = [self.get_back_button()]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def cmd_buy(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /buy [ID] [монеты/алмазы]")
            return
        
        try:
            item_id = int(context.args[0])
            currency = context.args[1].lower()
            if currency not in ['монеты', 'алмазы']:
                await update.message.reply_text("❌ Валюта должна быть 'монеты' или 'алмазы'")
                return
        except:
            await update.message.reply_text("❌ Неправильный формат")
            return
        
        user = update.effective_user
        currency_map = {'монеты': 'coins', 'алмазы': 'diamonds'}
        
        result = self.db.buy_item(user.id, item_id, currency_map[currency])
        
        if result:
            await update.message.reply_text(f"✅ Ты купил {result[1]}!")
        else:
            await update.message.reply_text("❌ Недостаточно средств или предмет не найден")
    
    async def cmd_payd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /payd [ник] [сумма]")
            return
        
        name = context.args[0]
        try:
            amount = int(context.args[1])
        except:
            await update.message.reply_text("❌ Сумма должна быть числом")
            return
        
        if amount <= 0:
            await update.message.reply_text("❌ Сумма должна быть положительной")
            return
        
        sender = update.effective_user
        sender_data = self.db.get_user(sender.id)
        
        if sender_data['coins'] < amount:
            await update.message.reply_text(f"❌ У тебя только {sender_data['coins']} монет")
            return
        
        receiver = self.db.get_user_by_name(name)
        if not receiver:
            await update.message.reply_text("❌ Игрок не найден")
            return
        
        receiver_id = receiver[0]
        receiver_name = receiver[2]
        
        self.db.add_coins(sender.id, -amount)
        self.db.add_coins(receiver_id, amount)
        self.db.add_transaction(sender.id, receiver_id, amount, "coins")
        
        await update.message.reply_text(f"✅ Переведено {amount} монет игроку {receiver_name}")
        
        try:
            await context.bot.send_message(
                chat_id=receiver_id,
                text=f"💰 **ПЕРЕВОД!**\n\n{receiver_name}, игрок {sender.first_name} перевёл тебе {amount} монет!",
                parse_mode='Markdown'
            )
        except:
            pass
    
    async def cmd_payh(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /payh [ник] [сумма]")
            return
        
        name = context.args[0]
        try:
            amount = int(context.args[1])
        except:
            await update.message.reply_text("❌ Сумма должна быть числом")
            return
        
        if amount <= 0:
            await update.message.reply_text("❌ Сумма должна быть положительной")
            return
        
        sender = update.effective_user
        sender_data = self.db.get_user(sender.id)
        
        if sender_data['diamonds'] < amount:
            await update.message.reply_text(f"❌ У тебя только {sender_data['diamonds']} алмазов")
            return
        
        receiver = self.db.get_user_by_name(name)
        if not receiver:
            await update.message.reply_text("❌ Игрок не найден")
            return
        
        receiver_id = receiver[0]
        receiver_name = receiver[2]
        
        self.db.add_diamonds(sender.id, -amount)
        self.db.add_diamonds(receiver_id, amount)
        self.db.add_transaction(sender.id, receiver_id, amount, "diamonds")
        
        await update.message.reply_text(f"✅ Переведено {amount} алмазов игроку {receiver_name}")
        
        try:
            await context.bot.send_message(
                chat_id=receiver_id,
                text=f"💎 **ПЕРЕВОД!**\n\n{receiver_name}, игрок {sender.first_name} перевёл тебе {amount} алмазов!",
                parse_mode='Markdown'
            )
        except:
            pass
    
    async def cmd_regen(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data['regens'] <= 0:
            await update.message.reply_text("❌ У тебя закончились регенерации! Купи в магазине")
            return
        
        if user_data['health'] >= user_data['max_health']:
            await update.message.reply_text("❌ У тебя уже полное здоровье")
            return
        
        self.db.heal(user.id, user_data['max_health'])
        self.db.cursor.execute("UPDATE users SET regens = regens - 1 WHERE user_id = ?", (user.id,))
        self.db.conn.commit()
        self.db.add_stat(user.id, "regen_used", 1)
        
        await update.message.reply_text(f"✅ Здоровье восстановлено! Осталось регенераций: {user_data['regens'] - 1}")
    
    async def cmd_automes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        if not self.is_admin(user.id):
            await update.message.reply_text("❌ Только администраторы могут управлять автосообщениями")
            return
        
        if context.args and context.args[0].lower() == 'on':
            self.db.set_setting('auto_messages', 'on')
            await update.message.reply_text("✅ Автосообщения включены")
        elif context.args and context.args[0].lower() == 'off':
            self.db.set_setting('auto_messages', 'off')
            await update.message.reply_text("✅ Автосообщения выключены")
        else:
            current = self.db.get_setting('auto_messages', 'on')
            await update.message.reply_text(f"📢 Автосообщения: {'включены' if current == 'on' else 'выключены'}")
    
    async def cmd_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "📖 **ПРАВИЛА ЧАТА**\n\n"
            "1️⃣ **Уважайте других участников**\n"
            "   • Никаких оскорблений и унижений\n"
            "   • Никакого буллинга\n\n"
            "2️⃣ **Не спамьте**\n"
            "   • Не флудите\n"
            "   • Не рекламируйте\n"
            "   • Не пишите капсом\n\n"
            "3️⃣ **Играйте честно**\n"
            "   • Не используйте баги\n"
            "   • Не мультиаккаунтите\n\n"
            "4️⃣ **Слушайтесь администрацию**\n"
            "   • Выполняйте требования модераторов\n"
            "   • Не спорьте с админами\n\n"
            "5️⃣ **Наказания**\n"
            "   • Предупреждение → Мут → Бан\n"
            "   • 3 варна = 24 часа мута\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "👑 **АДМИНЫ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        
        for admin in ADMINS:
            text += f"👑 {admin}\n"
        
        text += "\n━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "🛡 **МОДЕРАТОРЫ**\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        for mod in MODERATORS:
            text += f"🛡 {mod}\n"
        
        keyboard = [self.get_back_button()]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def cmd_namutebuy(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if not self.db.is_muted(user.id):
            await update.message.reply_text("❌ Ты не в муте")
            return
        
        price = 100
        if user_data['coins'] < price:
            await update.message.reply_text(f"❌ Недостаточно монет! Нужно {price} 🪙")
            return
        
        self.db.add_coins(user.id, -price)
        self.db.cursor.execute("UPDATE users SET mute_until = NULL WHERE user_id = ?", (user.id,))
        self.db.conn.commit()
        
        await update.message.reply_text(f"✅ Мут снят! Списан {price} 🪙")
    
    async def cmd_players(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        count = self.db.get_player_count()
        await update.message.reply_text(f"👥 **Всего игроков:** {count}")
    
    async def cmd_player(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Укажи ник игрока: /player [ник]")
            return
        
        name = " ".join(context.args)
        user_data = self.db.get_user_by_name(name)
        
        if not user_data:
            await update.message.reply_text("❌ Игрок не найден")
            return
        
        user_id = user_data[0]
        user_info = self.db.get_user(user_id)
        
        # Получаем статистику
        self.db.cursor.execute("SELECT * FROM stats WHERE user_id = ?", (user_id,))
        stats = self.db.cursor.fetchone()
        
        # Расчет времени
        join_date = datetime.datetime.fromisoformat(user_info['join_date'])
        days_active = (datetime.datetime.now() - join_date).days
        years = days_active // 365
        months = (days_active % 365) // 30
        days = days_active % 30
        
        last_seen = datetime.datetime.fromisoformat(user_info['last_active'])
        last_seen_delta = datetime.datetime.now() - last_seen
        last_seen_str = self.db.format_duration(last_seen_delta.total_seconds())
        
        rank = self.db.get_rank(user_id)
        rank_name = self.db.get_rank_name(rank)
        
        text = (
            f"👤 **ПРОФИЛЬ ИГРОКА**\n\n"
            f"Это [https://vk.com/id{user_id}|{user_info['first_name']}]\n"
            f"⭐ [{user_info['level']}] Ранг: {rank_name}\n"
            f"Репутация: ✨ {user_info['reputation']} | ➕ {user_info['reputation_given']}\n"
            f"Первое появление: {join_date.strftime('%d.%m.%Y')} ({years} г {months} мес {days} д)\n"
            f"Последний актив: {last_seen_str}\n\n"
            
            f"**Характеристики:**\n"
            f"💰 Монеты: {user_info['coins']} 🪙\n"
            f"💎 Алмазы: {user_info['diamonds']}\n"
            f"❤️ Здоровье: {user_info['health']}/{user_info['max_health']}\n"
            f"⚔️ Урон: {user_info['power']}%\n"
            f"👾 Боссов убито: {user_info['boss_kills']}\n"
            f"📊 Сообщений: {stats[1] if stats else 0}\n"
        )
        
        keyboard = [self.get_back_button()]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def cmd_top(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        top_coins = self.db.get_top("coins", 10)
        top_kills = self.db.get_top("boss_kills", 10)
        top_reputation = self.db.get_top("reputation", 10)
        
        text = (
            "╔══════════════════════════════╗\n"
            "║    🏆 **ТОП ИГРОКОВ**       ║\n"
            "╚══════════════════════════════╝\n\n"
        )
        
        text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "💰 **ПО МОНЕТАМ**\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        for i, (name, value) in enumerate(top_coins, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
            text += f"{medal} **{i}.** {name} — {value} 🪙\n"
        
        text += "\n━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "👾 **ПО УБИЙСТВУ БОССОВ**\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        for i, (name, value) in enumerate(top_kills, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
            text += f"{medal} **{i}.** {name} — {value} боссов\n"
        
        text += "\n━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "⭐ **ПО РЕПУТАЦИИ**\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        for i, (name, value) in enumerate(top_reputation, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
            text += f"{medal} **{i}.** {name} — {value} ⭐\n"
        
        keyboard = [self.get_back_button()]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def cmd_donator_commands(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "🧩 **КОМАНДЫ ДОНАТЕРОВ**\n\n"
            "▫️ /vip — купить VIP статус\n"
            "▫️ /premium — купить PREMIUM статус\n"
            "▫️ /diamonds — купить алмазы\n"
            "▫️ /energy — купить энергию\n\n"
            "💎 VIP статус (500 💎):\n"
            "  • +50% к урону\n"
            "  • +50% к регенерации\n"
            "  • Без спам-фильтра\n\n"
            "💎 PREMIUM статус (1000 💎):\n"
            "  • +100% к урону\n"
            "  • +100% к регенерации\n"
            "  • Ежедневные бонусы"
        )
        
        keyboard = [self.get_back_button()]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def cmd_eng(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        # Проверка, можно ли получить бесплатно (раз в час)
        # В реальном коде нужно добавить проверку времени
        
        self.db.add_energy(user.id, 20)
        await update.message.reply_text("✅ +20 энергии! Бесплатный заряд активирован!")
    
    async def cmd_sms(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /sms [ник] [текст]")
            return
        
        name = context.args[0]
        text = " ".join(context.args[1:])
        
        sender = update.effective_user
        
        receiver = self.db.get_user_by_name(name)
        if not receiver:
            await update.message.reply_text("❌ Игрок не найден")
            return
        
        receiver_id = receiver[0]
        receiver_name = receiver[2]
        
        try:
            await context.bot.send_message(
                chat_id=receiver_id,
                text=f"💬 **ЛИЧНОЕ СООБЩЕНИЕ**\n\nОт {sender.first_name}:\n{text}",
                parse_mode='Markdown'
            )
            await update.message.reply_text(f"✅ Сообщение отправлено {receiver_name}!")
        except:
            await update.message.reply_text("❌ Не удалось отправить сообщение")
    
    async def cmd_my_article(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        article = self.db.get_random_article()
        term_days = random.randint(1, 30)
        
        self.db.add_article(user.id, article["number"])
        
        text = (
            f"🤷‍♂️ **Сегодня {user.first_name} приговаривается к статье {article['number']}. {article['name']}**\n\n"
            f"📜 **Статья {article['number']}**\n"
            f"{article['description']}\n"
            f"⚖️ **Наказание:** {article['term']}\n"
            f"⏱ **Срок:** {term_days} {'день' if term_days == 1 else 'дня' if term_days < 5 else 'дней'}\n\n"
            f"💬 Приговор вступает в силу немедленно!"
        )
        
        keyboard = [self.get_back_button()]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def cmd_whoami(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id, user.first_name, user.username or "")
        
        # Получаем статистику
        self.db.cursor.execute("SELECT * FROM stats WHERE user_id = ?", (user.id,))
        stats = self.db.cursor.fetchone()
        
        # Расчет времени
        join_date = datetime.datetime.fromisoformat(user_data['join_date'])
        days_active = (datetime.datetime.now() - join_date).days
        years = days_active // 365
        months = (days_active % 365) // 30
        days = days_active % 30
        
        last_seen = datetime.datetime.fromisoformat(user_data['last_active'])
        last_seen_delta = datetime.datetime.now() - last_seen
        last_seen_str = self.db.format_duration(last_seen_delta.total_seconds())
        
        # Статистика онлайн
        total_online = stats[6] if stats and len(stats) > 6 else 0
        online_days = total_online // (24 * 60)
        online_hours = (total_online % (24 * 60)) // 60
        online_minutes = total_online % 60
        
        rank = self.db.get_rank(user.id)
        rank_name = self.db.get_rank_name(rank)
        
        # Роль
        role_emoji = "👑" if user_data['role'] == 'admin' else "🛡" if user_data['role'] == 'moderator' else "👤"
        role_text = "Админ" if user_data['role'] == 'admin' else "Модератор" if user_data['role'] == 'moderator' else "Игрок"
        
        text = (
            f"👤 **Кто я**\n\n"
            f"Это [https://vk.com/id{user.id}|{user.first_name}]\n"
            f"⭐ [{user_data['level']}] Ранг: {rank_name}\n"
            f"Роль: {role_emoji} {role_text}\n"
            f"Репутация: ✨ {user_data['reputation']} | ➕ {user_data['reputation_given']}\n"
            f"Первое появление: {join_date.strftime('%d.%m.%Y')} ({years} г {months} мес {days} д)\n"
            f"Последний актив: {last_seen_str}\n"
            f"Актив (д|ч|мин): {online_days} | {online_hours} | {online_minutes}\n\n"
            
            f"**Характеристики:**\n"
            f"💰 Монеты: {user_data['coins']} 🪙\n"
            f"💎 Алмазы: {user_data['diamonds']}\n"
            f"❤️ Здоровье: {user_data['health']}/{user_data['max_health']}\n"
            f"⚔️ Урон: {user_data['power']}%\n"
            f"👾 Боссов убито: {user_data['boss_kills']}\n"
            f"📊 Сообщений: {stats[1] if stats else 0}\n"
            f"🔋 Регенераций: {user_data['regens']}\n"
        )
        
        # Кнопки
        keyboard = [
            [InlineKeyboardButton("🏆 Достижения", callback_data="achievements"),
             InlineKeyboardButton("📌 Закладки", callback_data="bookmarks")],
            [InlineKeyboardButton("📜 Моя статья", callback_data="my_article")],
            self.get_back_button()
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def cmd_add_bookmark(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        if not context.args:
            await update.message.reply_text("❌ Использование: +закладка [описание]")
            return
        
        description = " ".join(context.args)
        
        if not update.message.reply_to_message:
            await update.message.reply_text("❌ Ответь на сообщение, которое хочешь сохранить")
            return
        
        message_id = update.message.reply_to_message.message_id
        chat_id = update.effective_chat.id
        
        bookmark_id = self.db.add_bookmark(user.id, message_id, chat_id, description)
        
        await update.message.reply_text(f"✅ Закладка #{bookmark_id} создана!\nОписание: {description}")
    
    async def cmd_bookmarks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        bookmarks = self.db.get_bookmarks(user.id)
        
        if not bookmarks:
            await update.message.reply_text("📌 У тебя пока нет закладок. Создай первую: +закладка [описание]")
            return
        
        if context.args:
            try:
                bookmark_id = int(context.args[0])
                bookmark = self.db.get_bookmark(bookmark_id, user.id)
                
                if bookmark:
                    await context.bot.forward_message(
                        chat_id=update.effective_chat.id,
                        from_chat_id=bookmark[3],
                        message_id=bookmark[2]
                    )
                    
                    keyboard = [[InlineKeyboardButton("🗑 Удалить", callback_data=f"delete_bookmark_{bookmark_id}")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await update.message.reply_text(
                        f"📌 Закладка #{bookmark_id}\nОписание: {bookmark[4]}",
                        reply_markup=reply_markup
                    )
                else:
                    await update.message.reply_text("❌ Закладка не найдена")
            except ValueError:
                await update.message.reply_text("❌ Неправильный номер закладки")
        else:
            text = "📌 **ТВОИ ЗАКЛАДКИ**\n\n"
            for bm in bookmarks:
                text += f"#{bm[0]} — {bm[4]} ({bm[5][:16]})\n"
            
            text += "\n💬 Перейти: /закладки [номер]"
            
            keyboard = [self.get_back_button()]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def cmd_achievements(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        achievements = self.db.get_achievements(user.id)
        
        if not achievements:
            await update.message.reply_text("🏆 У тебя пока нет достижений. Играй и открывай новые!")
            return
        
        text = "🏆 **ТВОИ ДОСТИЖЕНИЯ**\n\n"
        
        for ach_key, ach_date in achievements:
            if ach_key in ACHIEVEMENTS:
                date_obj = datetime.datetime.fromisoformat(ach_date)
                date_str = date_obj.strftime("%d.%m.%Y")
                text += f"▫️ {ACHIEVEMENTS[ach_key]}\n  📅 {date_str}\n\n"
        
        keyboard = [self.get_back_button()]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def cmd_banlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        page = 1
        if context.args and context.args[0].isdigit():
            page = int(context.args[0])
        
        bans = self.db.get_bans(page, 10)
        total_bans = self.db.get_bans_count()
        total_pages = (total_bans + 9) // 10
        
        if not bans:
            await update.message.reply_text("📋 Список банов пуст")
            return
        
        text = f"🚫 **СПИСОК ЗАБАНЕННЫХ** (стр. {page}/{total_pages})\n\n"
        
        for ban in bans:
            ban_id, user_id, user_name, admin_id, admin_name, reason, duration, ban_date, unban_date, is_permanent = ban
            
            ban_date_obj = datetime.datetime.fromisoformat(ban_date)
            date_str = ban_date_obj.strftime("%d.%m.%Y")
            
            text += f"**{ban_id}. [id{user_id}|{user_name}]**\n"
            text += f"⏱ {'Навсегда' if is_permanent else f'{duration} мин'}\n"
            if reason:
                text += f"💬 Причина: {reason}\n"
            text += f"Забанил: [id{admin_id}|{admin_name}]\n"
            text += f"📅 {date_str}\n\n"
        
        keyboard = self.get_pagination_keyboard("banlist", page, total_pages)
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def cmd_mutelist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        page = 1
        if context.args and context.args[0].isdigit():
            page = int(context.args[0])
        
        mutes = self.db.get_mutes(page, 10)
        total_mutes = self.db.get_mutes_count()
        total_pages = (total_mutes + 9) // 10
        
        if not mutes:
            await update.message.reply_text("📋 Список мутов пуст")
            return
        
        text = f"🔇 **СПИСОК ЗАМУЧЕННЫХ** (стр. {page}/{total_pages})\n\n"
        
        for mute in mutes:
            mute_id, user_id, user_name, admin_id, admin_name, reason, duration, mute_date, mute_until = mute
            
            mute_date_obj = datetime.datetime.fromisoformat(mute_date)
            date_str = mute_date_obj.strftime("%d.%m.%Y")
            
            text += f"**{mute_id}. [id{user_id}|{user_name}]**\n"
            text += f"⏱ {duration} мин\n"
            if reason:
                text += f"💬 Причина: {reason}\n"
            text += f"Замутил: [id{admin_id}|{admin_name}]\n"
            text += f"📅 {date_str}\n\n"
        
        keyboard = self.get_pagination_keyboard("mutelist", page, total_pages)
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def cmd_warnlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        page = 1
        if context.args and context.args[0].isdigit():
            page = int(context.args[0])
        
        warns = self.db.get_warns(None, page, 10)
        total_warns = self.db.get_warns_count()
        total_pages = (total_warns + 9) // 10
        
        if not warns:
            await update.message.reply_text("📋 Список варнов пуст")
            return
        
        text = f"⚠️ **СПИСОК ВАРНОВ** (стр. {page}/{total_pages})\n\n"
        
        for warn in warns:
            warn_id, user_id, user_name, admin_id, admin_name, reason, warn_date = warn
            
            warn_date_obj = datetime.datetime.fromisoformat(warn_date)
            date_str = warn_date_obj.strftime("%d.%m.%Y")
            
            text += f"**{warn_id}. [id{user_id}|{user_name}]**\n"
            if reason:
                text += f"💬 Причина: {reason}\n"
            text += f"Выдал: [id{admin_id}|{admin_name}]\n"
            text += f"📅 {date_str}\n\n"
        
        keyboard = self.get_pagination_keyboard("warnlist", page, total_pages)
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def cmd_mute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Недостаточно прав")
            return
        
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /mute [ник] [минут] [причина]")
            return
        
        name = context.args[0]
        try:
            minutes = int(context.args[1])
            reason = " ".join(context.args[2:]) if len(context.args) > 2 else "Нарушение"
        except:
            await update.message.reply_text("❌ Неправильный формат")
            return
        
        admin = update.effective_user
        
        target = self.db.get_user_by_name(name)
        if not target:
            await update.message.reply_text("❌ Игрок не найден")
            return
        
        target_id = target[0]
        target_name = target[2]
        
        if target_id == OWNER_ID:
            await update.message.reply_text("❌ Нельзя замутить владельца")
            return
        
        self.db.mute_user(target_id, minutes, admin.id, reason)
        
        await update.message.reply_text(f"🔇 Пользователь {target_name} замучен на {minutes} минут\nПричина: {reason}")
        
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=f"🔇 **ВЫ ЗАМУЧЕНЫ**\n\nНа {minutes} минут.\nПричина: {reason}\n\nСнять мут: /namutebuy",
                parse_mode='Markdown'
            )
        except:
            pass
    
    async def cmd_warn(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Недостаточно прав")
            return
        
        if len(context.args) < 1:
            await update.message.reply_text("❌ Использование: /warn [ник] [причина]")
            return
        
        name = context.args[0]
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else "Нарушение"
        
        admin = update.effective_user
        
        target = self.db.get_user_by_name(name)
        if not target:
            await update.message.reply_text("❌ Игрок не найден")
            return
        
        target_id = target[0]
        target_name = target[2]
        
        if target_id == OWNER_ID:
            await update.message.reply_text("❌ Нельзя выдать варн владельцу")
            return
        
        result = self.db.add_warn(target_id, admin.id, reason)
        await update.message.reply_text(result)
        
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=f"⚠️ **ПРЕДУПРЕЖДЕНИЕ**\n\n{reason}",
                parse_mode='Markdown'
            )
        except:
            pass
    
    async def cmd_ban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Недостаточно прав")
            return
        
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /ban [ник] [минут] [причина] (0 = навсегда)")
            return
        
        name = context.args[0]
        try:
            minutes = int(context.args[1])
            reason = " ".join(context.args[2:]) if len(context.args) > 2 else "Нарушение"
        except:
            await update.message.reply_text("❌ Неправильный формат")
            return
        
        admin = update.effective_user
        
        target = self.db.get_user_by_name(name)
        if not target:
            await update.message.reply_text("❌ Игрок не найден")
            return
        
        target_id = target[0]
        target_name = target[2]
        
        if target_id == OWNER_ID:
            await update.message.reply_text("❌ Нельзя забанить владельца")
            return
        
        self.db.ban_user(target_id, admin.id, reason, minutes)
        
        duration_text = "навсегда" if minutes == 0 else f"на {minutes} минут"
        await update.message.reply_text(f"🚫 Пользователь {target_name} забанен {duration_text}\nПричина: {reason}")
        
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=f"🚫 **ВЫ ЗАБАНЕНЫ**\n\n{duration_text}\nПричина: {reason}\n\nЕсли хочешь вернуться, напиши забанившему модератору или создателю беседы.",
                parse_mode='Markdown'
            )
        except:
            pass
    
    async def cmd_unban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Недостаточно прав")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Использование: /unban [ник]")
            return
        
        name = context.args[0]
        
        target = self.db.get_user_by_name(name)
        if not target:
            await update.message.reply_text("❌ Игрок не найден")
            return
        
        target_id = target[0]
        target_name = target[2]
        
        self.db.unban_user(target_id)
        await update.message.reply_text(f"✅ Пользователь {target_name} разбанен")
        
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text="✅ **ВЫ РАЗБАНЕНЫ**\n\nДобро пожаловать обратно!",
                parse_mode='Markdown'
            )
        except:
            pass
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        message_text = update.message.text
        self.db.update_last_seen(user.id)
        
        if self.db.is_banned(user.id):
            ban_info = self.db.get_user(user.id)
            await update.message.reply_text(
                f"🚫 **ВЫ ЗАБАНЕНЫ**\n\n"
                f"Причина: {ban_info['ban_reason']}\n"
                f"Дата: {ban_info['ban_date'][:16]}\n\n"
                f"Если хочешь вернуться, напиши забанившему модератору или создателю беседы."
            )
            return
        
        if self.db.is_muted(user.id):
            remaining = self.db.get_mute_time(user.id)
            await update.message.reply_text(f"🔇 Вы замучены. Осталось: {remaining}")
            return
        
        if await self.check_spam(update):
            return
        
        # Обработка команд без слэша
        if message_text.lower() == "регенерация":
            await self.cmd_regen(update, context)
            return
        
        if message_text.startswith("+закладка"):
            context.args = message_text[10:].strip().split()
            await self.cmd_add_bookmark(update, context)
            return
        
        # Обновляем счетчик сообщений
        self.db.cursor.execute("UPDATE users SET message_count = message_count + 1 WHERE user_id = ?", (user.id,))
        self.db.conn.commit()
        self.db.add_stat(user.id, "messages_count", 1)
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user = update.effective_user
        data = query.data
        
        if data == "noop":
            return
        
        elif data == "menu_back":
            keyboard = self.get_main_menu_keyboard()
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "🎮 **ГЛАВНОЕ МЕНЮ**\n\nВыбери действие:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        
        elif data == "boss_st":
            await self.cmd_boss_st(update, context)
        elif data == "regen":
            await self.cmd_regen(update, context)
        elif data == "shop":
            await self.cmd_shop(update, context)
        elif data == "donate":
            await self.cmd_donate(update, context)
        elif data == "players":
            await self.cmd_players(update, context)
        elif data == "top":
            await self.cmd_top(update, context)
        elif data == "rules":
            await self.cmd_rules(update, context)
        elif data == "help":
            await self.cmd_help(update, context)
        elif data == "achievements":
            await self.cmd_achievements(update, context)
        elif data == "my_article":
            await self.cmd_my_article(update, context)
        elif data == "bookmarks":
            await self.cmd_bookmarks(update, context)
        
        elif data.startswith("banlist_"):
            page = int(data.split('_')[1])
            await self.cmd_banlist(update, context, page)
        elif data.startswith("mutelist_"):
            page = int(data.split('_')[1])
            await self.cmd_mutelist(update, context, page)
        elif data.startswith("warnlist_"):
            page = int(data.split('_')[1])
            await self.cmd_warnlist(update, context, page)
        
        elif data.startswith("delete_bookmark_"):
            bookmark_id = int(data.split('_')[2])
            self.db.delete_bookmark(bookmark_id, user.id)
            await query.edit_message_text("✅ Закладка удалена")
    
    async def run(self):
        try:
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            logger.info("🚀 Бот «СПЕКТР» запущен!")
            while True:
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await asyncio.sleep(5)
            await self.run()
    
    async def close(self):
        self.db.close()
        logger.info("👋 Бот остановлен")

# ===================== ТОЧКА ВХОДА =====================
async def main():
    bot = GameBot()
    try:
        await bot.run()
    except KeyboardInterrupt:
        await bot.close()
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await bot.close()

if __name__ == "__main__":
    asyncio.run(main())
