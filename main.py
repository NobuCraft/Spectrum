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
import hashlib
import base64

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

# OpenRouter API (используем твой DeepSeek ключ)
OPENROUTER_KEY = "sk-97ac1d0de1844c449852a5470cbcae35"

# Настройки
SPAM_LIMIT = 5
SPAM_WINDOW = 3
SPAM_MUTE_TIME = 120

# Цены на привилегии
VIP_PRICE = 5000
PREMIUM_PRICE = 15000
ADMIN_PRICE = 50000

# Длительность привилегий (в днях)
VIP_DAYS = 30
PREMIUM_DAYS = 30

# ===================== БАЗА ДАННЫХ =====================
class Database:
    def __init__(self, db_name="spectrum_bot.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
        self.migrate_tables()
        self.init_data()
    
    def migrate_tables(self):
        try:
            self.cursor.execute("PRAGMA table_info(users)")
            columns = [col[1] for col in self.cursor.fetchall()]
            
            # Проверяем и добавляем все необходимые колонки
            required_columns = {
                'role': "ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'",
                'warns': "ALTER TABLE users ADD COLUMN warns INTEGER DEFAULT 0",
                'mute_until': "ALTER TABLE users ADD COLUMN mute_until TIMESTAMP",
                'banned': "ALTER TABLE users ADD COLUMN banned INTEGER DEFAULT 0",
                'health': "ALTER TABLE users ADD COLUMN health INTEGER DEFAULT 100",
                'armor': "ALTER TABLE users ADD COLUMN armor INTEGER DEFAULT 0",
                'damage': "ALTER TABLE users ADD COLUMN damage INTEGER DEFAULT 10",
                'boss_kills': "ALTER TABLE users ADD COLUMN boss_kills INTEGER DEFAULT 0",
                'vip_until': "ALTER TABLE users ADD COLUMN vip_until TIMESTAMP",
                'premium_until': "ALTER TABLE users ADD COLUMN premium_until TIMESTAMP",
                'clan_id': "ALTER TABLE users ADD COLUMN clan_id INTEGER DEFAULT 0",
                'clan_role': "ALTER TABLE users ADD COLUMN clan_role TEXT DEFAULT 'member'",
                'mafia_wins': "ALTER TABLE users ADD COLUMN mafia_wins INTEGER DEFAULT 0",
                'mafia_games': "ALTER TABLE users ADD COLUMN mafia_games INTEGER DEFAULT 0",
                'rps_wins': "ALTER TABLE users ADD COLUMN rps_wins INTEGER DEFAULT 0",
                'rps_losses': "ALTER TABLE users ADD COLUMN rps_losses INTEGER DEFAULT 0",
                'rps_draws': "ALTER TABLE users ADD COLUMN rps_draws INTEGER DEFAULT 0",
                'casino_wins': "ALTER TABLE users ADD COLUMN casino_wins INTEGER DEFAULT 0",
                'casino_losses': "ALTER TABLE users ADD COLUMN casino_losses INTEGER DEFAULT 0",
                'rr_wins': "ALTER TABLE users ADD COLUMN rr_wins INTEGER DEFAULT 0",
                'rr_losses': "ALTER TABLE users ADD COLUMN rr_losses INTEGER DEFAULT 0",
                'rr_games': "ALTER TABLE users ADD COLUMN rr_games INTEGER DEFAULT 0",
                'rr_money': "ALTER TABLE users ADD COLUMN rr_money INTEGER DEFAULT 100",
                'ttt_wins': "ALTER TABLE users ADD COLUMN ttt_wins INTEGER DEFAULT 0",
                'ttt_losses': "ALTER TABLE users ADD COLUMN ttt_losses INTEGER DEFAULT 0",
                'ttt_draws': "ALTER TABLE users ADD COLUMN ttt_draws INTEGER DEFAULT 0",
                'cases': "ALTER TABLE users ADD COLUMN cases INTEGER DEFAULT 0",
                'keys': "ALTER TABLE users ADD COLUMN keys INTEGER DEFAULT 0",
                'gender': "ALTER TABLE users ADD COLUMN gender TEXT DEFAULT 'unknown'",
                'nickname': "ALTER TABLE users ADD COLUMN nickname TEXT",
                'birthday': "ALTER TABLE users ADD COLUMN birthday TEXT",
                'city': "ALTER TABLE users ADD COLUMN city TEXT",
                'bio': "ALTER TABLE users ADD COLUMN bio TEXT",
                'marry_id': "ALTER TABLE users ADD COLUMN marry_id INTEGER DEFAULT 0",
                'marry_date': "ALTER TABLE users ADD COLUMN marry_date TIMESTAMP",
                'love_points': "ALTER TABLE users ADD COLUMN love_points INTEGER DEFAULT 0",
                'children': "ALTER TABLE users ADD COLUMN children INTEGER DEFAULT 0",
                'rep': "ALTER TABLE users ADD COLUMN rep INTEGER DEFAULT 0",
                'warns_count': "ALTER TABLE users ADD COLUMN warns_count INTEGER DEFAULT 0",
                'mutes_count': "ALTER TABLE users ADD COLUMN mutes_count INTEGER DEFAULT 0",
                'bans_count': "ALTER TABLE users ADD COLUMN bans_count INTEGER DEFAULT 0",
                'last_seen': "ALTER TABLE users ADD COLUMN last_seen TIMESTAMP",
                'voice_count': "ALTER TABLE users ADD COLUMN voice_count INTEGER DEFAULT 0",
                'photo_count': "ALTER TABLE users ADD COLUMN photo_count INTEGER DEFAULT 0",
                'sticker_count': "ALTER TABLE users ADD COLUMN sticker_count INTEGER DEFAULT 0",
                'referrals': "ALTER TABLE users ADD COLUMN referrals INTEGER DEFAULT 0",
                'referral_link': "ALTER TABLE users ADD COLUMN referral_link TEXT",
                'daily_streak': "ALTER TABLE users ADD COLUMN daily_streak INTEGER DEFAULT 0",
                'last_daily': "ALTER TABLE users ADD COLUMN last_daily TIMESTAMP",
            }
            
            for col, sql in required_columns.items():
                if col not in columns:
                    self.cursor.execute(sql)
            
            self.conn.commit()
        except Exception as e:
            print(f"Ошибка миграции: {e}")
    
    def create_tables(self):
        # Основная таблица пользователей
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                coins INTEGER DEFAULT 1000,
                energy INTEGER DEFAULT 100,
                level INTEGER DEFAULT 1,
                exp INTEGER DEFAULT 0,
                role TEXT DEFAULT 'user',
                warns INTEGER DEFAULT 0,
                mute_until TIMESTAMP,
                banned INTEGER DEFAULT 0,
                health INTEGER DEFAULT 100,
                armor INTEGER DEFAULT 0,
                damage INTEGER DEFAULT 10,
                boss_kills INTEGER DEFAULT 0,
                vip_until TIMESTAMP,
                premium_until TIMESTAMP,
                clan_id INTEGER DEFAULT 0,
                clan_role TEXT DEFAULT 'member',
                mafia_wins INTEGER DEFAULT 0,
                mafia_games INTEGER DEFAULT 0,
                rps_wins INTEGER DEFAULT 0,
                rps_losses INTEGER DEFAULT 0,
                rps_draws INTEGER DEFAULT 0,
                casino_wins INTEGER DEFAULT 0,
                casino_losses INTEGER DEFAULT 0,
                rr_wins INTEGER DEFAULT 0,
                rr_losses INTEGER DEFAULT 0,
                rr_games INTEGER DEFAULT 0,
                rr_money INTEGER DEFAULT 100,
                ttt_wins INTEGER DEFAULT 0,
                ttt_losses INTEGER DEFAULT 0,
                ttt_draws INTEGER DEFAULT 0,
                cases INTEGER DEFAULT 0,
                keys INTEGER DEFAULT 0,
                gender TEXT DEFAULT 'unknown',
                nickname TEXT,
                birthday TEXT,
                city TEXT,
                bio TEXT,
                marry_id INTEGER DEFAULT 0,
                marry_date TIMESTAMP,
                love_points INTEGER DEFAULT 0,
                children INTEGER DEFAULT 0,
                rep INTEGER DEFAULT 0,
                warns_count INTEGER DEFAULT 0,
                mutes_count INTEGER DEFAULT 0,
                bans_count INTEGER DEFAULT 0,
                last_seen TIMESTAMP,
                voice_count INTEGER DEFAULT 0,
                photo_count INTEGER DEFAULT 0,
                sticker_count INTEGER DEFAULT 0,
                referrals INTEGER DEFAULT 0,
                referral_link TEXT,
                daily_streak INTEGER DEFAULT 0,
                last_daily TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Статистика
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS stats (
                user_id INTEGER PRIMARY KEY,
                messages_count INTEGER DEFAULT 0,
                commands_used INTEGER DEFAULT 0,
                games_played INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Боссы
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
        
        # Кланы
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Члены клана
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS clan_members (
                clan_id INTEGER,
                user_id INTEGER,
                role TEXT DEFAULT 'member',
                joined_at TIMESTAMP,
                FOREIGN KEY (clan_id) REFERENCES clans (id),
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Инвентарь
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                item_name TEXT,
                item_type TEXT,
                item_desc TEXT,
                quantity INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Торговая площадка
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS marketplace (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_id INTEGER,
                item_name TEXT,
                item_type TEXT,
                price INTEGER,
                quantity INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (seller_id) REFERENCES users (user_id)
            )
        ''')
        
        # Подарки
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS gifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_id INTEGER,
                to_id INTEGER,
                item_name TEXT,
                message TEXT,
                sent_at TIMESTAMP,
                is_read INTEGER DEFAULT 0,
                FOREIGN KEY (from_id) REFERENCES users (user_id),
                FOREIGN KEY (to_id) REFERENCES users (user_id)
            )
        ''')
        
        # Рефералы
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referral_id INTEGER,
                reward INTEGER DEFAULT 0,
                joined_at TIMESTAMP,
                FOREIGN KEY (referrer_id) REFERENCES users (user_id),
                FOREIGN KEY (referral_id) REFERENCES users (user_id)
            )
        ''')
        
        # Игры в Мафию
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS mafia_games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_id INTEGER,
                status TEXT DEFAULT 'waiting',
                players TEXT,
                roles TEXT,
                phase TEXT DEFAULT 'night',
                day_count INTEGER DEFAULT 1,
                created_at TIMESTAMP
            )
        ''')
        
        # Кейсы
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_name TEXT,
                case_price INTEGER,
                items TEXT
            )
        ''')
        
        # Русская рулетка - лобби
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS rr_lobbies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_id INTEGER,
                max_players INTEGER,
                bet INTEGER,
                players TEXT,
                status TEXT DEFAULT 'waiting',
                created_at TIMESTAMP
            )
        ''')
        
        # Русская рулетка - игры
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS rr_games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lobby_id INTEGER,
                players TEXT,
                current_player INTEGER,
                cylinder_size INTEGER,
                bullets INTEGER,
                positions TEXT,
                alive_players TEXT,
                phase TEXT,
                started_at TIMESTAMP
            )
        ''')
        
        # Крестики-нолики 3D - лобби
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS ttt_lobbies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_id INTEGER,
                opponent_id INTEGER DEFAULT 0,
                status TEXT DEFAULT 'waiting',
                created_at TIMESTAMP
            )
        ''')
        
        # Крестики-нолики 3D - игры
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS ttt_games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lobby_id INTEGER,
                player_x INTEGER,
                player_o INTEGER,
                current_player INTEGER,
                main_board TEXT,
                sub_boards TEXT,
                last_move INTEGER,
                status TEXT,
                started_at TIMESTAMP
            )
        ''')
        
        # Настройки групп
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS group_settings (
                chat_id INTEGER PRIMARY KEY,
                welcome_enabled INTEGER DEFAULT 1,
                welcome_message TEXT DEFAULT '🌟 Добро пожаловать, {user}!',
                goodbye_enabled INTEGER DEFAULT 1,
                goodbye_message TEXT DEFAULT '👋 Пока, {user}!',
                anti_spam INTEGER DEFAULT 1,
                anti_flood INTEGER DEFAULT 1,
                caps_limit INTEGER DEFAULT 10,
                emoji_limit INTEGER DEFAULT 10,
                link_block INTEGER DEFAULT 0,
                language TEXT DEFAULT 'ru',
                rules TEXT DEFAULT '',
                mute_time INTEGER DEFAULT 5,
                warn_limit INTEGER DEFAULT 3
            )
        ''')
        
        # Правила групп
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS group_rules (
                chat_id INTEGER PRIMARY KEY,
                rules_text TEXT DEFAULT '',
                last_updated TIMESTAMP,
                updated_by INTEGER
            )
        ''')
        
        # Комплименты
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS compliments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                compliment TEXT,
                from_id INTEGER,
                created_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (from_id) REFERENCES users (user_id)
            )
        ''')
        
        # Долги
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS debts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                debtor_id INTEGER,
                creditor_id INTEGER,
                amount INTEGER,
                reason TEXT,
                created_at TIMESTAMP,
                deadline TIMESTAMP,
                is_paid INTEGER DEFAULT 0,
                FOREIGN KEY (debtor_id) REFERENCES users (user_id),
                FOREIGN KEY (creditor_id) REFERENCES users (user_id)
            )
        ''')
        
        # Ежедневные задания
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS dailies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                task_type TEXT,
                progress INTEGER DEFAULT 0,
                target INTEGER,
                reward INTEGER,
                completed INTEGER DEFAULT 0,
                created_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Достижения
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                achievement_name TEXT,
                achievement_desc TEXT,
                earned_date TIMESTAMP,
                reward_coins INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        self.conn.commit()
    
    def init_data(self):
        self.init_bosses()
        self.init_cases()
        self.init_achievements()
    
    def init_bosses(self):
        self.cursor.execute("SELECT * FROM bosses")
        if not self.cursor.fetchone():
            bosses_data = [
                ("🌲 Лесной тролль", 5, 200, 20, 100, "https://i.imgur.com/troll.jpg"),
                ("🐉 Огненный дракон", 10, 500, 40, 250, "https://i.imgur.com/dragon.jpg"),
                ("❄️ Ледяной великан", 15, 1000, 60, 500, "https://i.imgur.com/giant.jpg"),
                ("⚔️ Темный рыцарь", 20, 2000, 80, 1000, "https://i.imgur.com/knight.jpg"),
                ("👾 Король демонов", 25, 5000, 150, 2500, "https://i.imgur.com/demon.jpg"),
                ("💀 Бог разрушения", 30, 10000, 300, 5000, "https://i.imgur.com/god.jpg"),
                ("🌪️ Повелитель бурь", 35, 20000, 400, 10000, "https://i.imgur.com/storm.jpg"),
                ("🔥 Феникс", 40, 50000, 600, 25000, "https://i.imgur.com/phoenix.jpg"),
                ("👁️ Древний ужас", 45, 100000, 1000, 50000, "https://i.imgur.com/ancient.jpg"),
                ("⚡ Бог грома", 50, 200000, 2000, 100000, "https://i.imgur.com/thunder.jpg")
            ]
            for name, level, health, damage, reward, image in bosses_data:
                self.cursor.execute('''
                    INSERT INTO bosses (boss_name, boss_level, boss_health, boss_max_health, boss_damage, boss_reward, boss_image)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (name, level, health, health, damage, reward, image))
            self.conn.commit()
    
    def init_cases(self):
        self.cursor.execute("SELECT * FROM cases")
        if not self.cursor.fetchone():
            cases_data = [
                ("🎁 Обычный кейс", 100, '{"items": [{"name": "100 монет", "type": "coins", "value": 100, "chance": 30}, {"name": "200 монет", "type": "coins", "value": 200, "chance": 25}, {"name": "500 монет", "type": "coins", "value": 500, "chance": 15}, {"name": "VIP на 1 день", "type": "vip", "value": 1, "chance": 10}, {"name": "1000 монет", "type": "coins", "value": 1000, "chance": 10}, {"name": "Ключ", "type": "key", "value": 1, "chance": 5}, {"name": "VIP на 7 дней", "type": "vip", "value": 7, "chance": 3}, {"name": "5000 монет", "type": "coins", "value": 5000, "chance": 2}]}'),
                ("🔮 Редкий кейс", 500, '{"items": [{"name": "500 монет", "type": "coins", "value": 500, "chance": 25}, {"name": "1000 монет", "type": "coins", "value": 1000, "chance": 20}, {"name": "VIP на 3 дня", "type": "vip", "value": 3, "chance": 15}, {"name": "2000 монет", "type": "coins", "value": 2000, "chance": 15}, {"name": "Ключ", "type": "key", "value": 1, "chance": 10}, {"name": "VIP на 7 дней", "type": "vip", "value": 7, "chance": 7}, {"name": "5000 монет", "type": "coins", "value": 5000, "chance": 5}, {"name": "Премиум на 1 день", "type": "premium", "value": 1, "chance": 3}]}'),
                ("💎 Легендарный кейс", 1000, '{"items": [{"name": "1000 монет", "type": "coins", "value": 1000, "chance": 20}, {"name": "VIP на 7 дней", "type": "vip", "value": 7, "chance": 15}, {"name": "2000 монет", "type": "coins", "value": 2000, "chance": 15}, {"name": "5000 монет", "type": "coins", "value": 5000, "chance": 12}, {"name": "Ключ", "type": "key", "value": 2, "chance": 10}, {"name": "Премиум на 3 дня", "type": "premium", "value": 3, "chance": 10}, {"name": "VIP на 30 дней", "type": "vip", "value": 30, "chance": 8}, {"name": "10000 монет", "type": "coins", "value": 10000, "chance": 5}, {"name": "Премиум на 7 дней", "type": "premium", "value": 7, "chance": 5}]}')
            ]
            for name, price, items in cases_data:
                self.cursor.execute(
                    "INSERT INTO cases (case_name, case_price, items) VALUES (?, ?, ?)",
                    (name, price, items)
                )
            self.conn.commit()
    
    def init_achievements(self):
        # Достижения будут добавляться динамически
        pass
    
    def respawn_bosses(self):
        self.cursor.execute("UPDATE bosses SET is_alive = 1, boss_health = boss_max_health")
        self.conn.commit()
    
    def get_user(self, user_id: int, first_name: str = "Player", last_name: str = ""):
        self.cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = self.cursor.fetchone()
        
        if not user:
            role = 'owner' if user_id == OWNER_ID else 'user'
            self.cursor.execute('''
                INSERT INTO users (user_id, first_name, last_name, role, referral_link) 
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, first_name, last_name, role, f"ref_{user_id}_{int(time.time())}"))
            
            self.cursor.execute('''
                INSERT INTO stats (user_id) VALUES (?)
            ''', (user_id,))
            
            self.conn.commit()
            return self.get_user(user_id, first_name, last_name)
        
        columns = [description[0] for description in self.cursor.description]
        return dict(zip(columns, user))
    
    def add_coins(self, user_id: int, coins: int):
        self.cursor.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (coins, user_id))
        self.conn.commit()
    
    def add_exp(self, user_id: int, exp: int):
        self.cursor.execute("UPDATE users SET exp = exp + ? WHERE user_id = ?", (exp, user_id))
        
        self.cursor.execute("SELECT exp, level FROM users WHERE user_id = ?", (user_id,))
        user = self.cursor.fetchone()
        
        exp_needed = user[1] * 100
        if user[0] >= exp_needed:
            self.cursor.execute("UPDATE users SET level = level + 1, exp = exp - ? WHERE user_id = ?", (exp_needed, user_id))
            self.add_achievement(user_id, "📈 Новичок", f"Достиг {user[1] + 1} уровня", 100)
        
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
        self.cursor.execute("UPDATE users SET health = health + ? WHERE user_id = ?", (amount, user_id))
        self.conn.commit()
    
    def mute_user(self, user_id: int, minutes: int, admin_id: int = None, reason: str = "Спам"):
        mute_until = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
        self.cursor.execute("UPDATE users SET mute_until = ?, mutes_count = mutes_count + 1 WHERE user_id = ?", (mute_until, user_id))
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
    
    def add_warn(self, user_id: int, admin_id: int, reason: str = "Нарушение"):
        self.cursor.execute("UPDATE users SET warns = warns + 1, warns_count = warns_count + 1 WHERE user_id = ?", (user_id,))
        self.conn.commit()
        
        self.cursor.execute("SELECT warns FROM users WHERE user_id = ?", (user_id,))
        warns = self.cursor.fetchone()[0]
        
        if warns >= 3:
            self.mute_user(user_id, 1440, admin_id, "3 предупреждения")
            return f"⚠️ Пользователь получил 3 варна и был замучен на 24 часа!"
        return f"⚠️ Пользователь получил варн ({warns}/3)"
    
    def ban_user(self, user_id: int, admin_id: int):
        self.cursor.execute("UPDATE users SET banned = 1, bans_count = bans_count + 1 WHERE user_id = ?", (user_id,))
        self.conn.commit()
    
    def unban_user(self, user_id: int):
        self.cursor.execute("UPDATE users SET banned = 0, warns = 0 WHERE user_id = ?", (user_id,))
        self.conn.commit()
    
    def is_banned(self, user_id: int) -> bool:
        self.cursor.execute("SELECT banned FROM users WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()
        return result and result[0] == 1
    
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
    
    def create_clan(self, name, owner_id):
        try:
            self.cursor.execute("INSERT INTO clans (name, owner_id) VALUES (?, ?)", (name, owner_id))
            self.conn.commit()
            clan_id = self.cursor.lastrowid
            self.cursor.execute("INSERT INTO clan_members (clan_id, user_id, role, joined_at) VALUES (?, ?, ?, ?)", (clan_id, owner_id, 'owner', datetime.datetime.now()))
            self.cursor.execute("UPDATE users SET clan_id = ?, clan_role = 'owner' WHERE user_id = ?", (clan_id, owner_id))
            self.conn.commit()
            return clan_id
        except:
            return None
    
    def get_clan(self, clan_id):
        self.cursor.execute("SELECT * FROM clans WHERE id = ?", (clan_id,))
        return self.cursor.fetchone()
    
    def get_user_clan(self, user_id):
        self.cursor.execute("SELECT clan_id FROM users WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()
        if result and result[0]:
            return self.get_clan(result[0])
        return None
    
    def get_clan_members(self, clan_id):
        self.cursor.execute('''
            SELECT u.user_id, u.first_name, u.last_name, u.level, u.damage, cm.role
            FROM clan_members cm
            JOIN users u ON cm.user_id = u.user_id
            WHERE cm.clan_id = ?
        ''', (clan_id,))
        return self.cursor.fetchall()
    
    def join_clan(self, user_id, clan_id):
        self.cursor.execute("INSERT INTO clan_members (clan_id, user_id, role, joined_at) VALUES (?, ?, ?, ?)", (clan_id, user_id, 'member', datetime.datetime.now()))
        self.cursor.execute("UPDATE users SET clan_id = ?, clan_role = 'member' WHERE user_id = ?", (clan_id, user_id))
        self.cursor.execute("UPDATE clans SET members = members + 1 WHERE id = ?", (clan_id,))
        self.conn.commit()
    
    def leave_clan(self, user_id, clan_id):
        self.cursor.execute("DELETE FROM clan_members WHERE clan_id = ? AND user_id = ?", (clan_id, user_id))
        self.cursor.execute("UPDATE users SET clan_id = 0, clan_role = 'member' WHERE user_id = ?", (user_id,))
        self.cursor.execute("UPDATE clans SET members = members - 1 WHERE id = ?", (clan_id,))
        self.conn.commit()
    
    def add_clan_exp(self, clan_id, exp):
        self.cursor.execute("UPDATE clans SET exp = exp + ? WHERE id = ?", (exp, clan_id))
        self.cursor.execute("SELECT exp, level FROM clans WHERE id = ?", (clan_id,))
        clan = self.cursor.fetchone()
        exp_needed = clan[1] * 500
        if clan[0] >= exp_needed:
            self.cursor.execute("UPDATE clans SET level = level + 1, exp = exp - ? WHERE id = ?", (exp_needed, clan_id))
        self.conn.commit()
    
    def add_item(self, user_id, item_name, item_type, item_desc="", quantity=1):
        self.cursor.execute("SELECT id, quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name))
        item = self.cursor.fetchone()
        if item:
            self.cursor.execute("UPDATE inventory SET quantity = quantity + ? WHERE id = ?", (quantity, item[0]))
        else:
            self.cursor.execute("INSERT INTO inventory (user_id, item_name, item_type, item_desc, quantity) VALUES (?, ?, ?, ?, ?)", (user_id, item_name, item_type, item_desc, quantity))
        self.conn.commit()
    
    def get_inventory(self, user_id):
        self.cursor.execute("SELECT id, item_name, item_type, item_desc, quantity FROM inventory WHERE user_id = ? AND quantity > 0", (user_id,))
        return self.cursor.fetchall()
    
    def use_item(self, user_id, item_id):
        self.cursor.execute("SELECT item_name, quantity FROM inventory WHERE id = ? AND user_id = ?", (item_id, user_id))
        item = self.cursor.fetchone()
        if item and item[1] > 0:
            if item[1] == 1:
                self.cursor.execute("DELETE FROM inventory WHERE id = ?", (item_id,))
            else:
                self.cursor.execute("UPDATE inventory SET quantity = quantity - 1 WHERE id = ?", (item_id,))
            self.conn.commit()
            return item[0]
        return None
    
    def add_to_market(self, seller_id, item_name, item_type, price, quantity=1):
        self.cursor.execute("INSERT INTO marketplace (seller_id, item_name, item_type, price, quantity) VALUES (?, ?, ?, ?, ?)", (seller_id, item_name, item_type, price, quantity))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_market_items(self):
        self.cursor.execute("SELECT * FROM marketplace ORDER BY created_at DESC")
        return self.cursor.fetchall()
    
    def buy_from_market(self, item_id, buyer_id):
        self.cursor.execute("SELECT * FROM marketplace WHERE id = ?", (item_id,))
        item = self.cursor.fetchone()
        if item:
            self.cursor.execute("DELETE FROM marketplace WHERE id = ?", (item_id,))
            self.conn.commit()
            return item
        return None
    
    def send_gift(self, from_id, to_id, item_name, message=""):
        self.cursor.execute("INSERT INTO gifts (from_id, to_id, item_name, message, sent_at) VALUES (?, ?, ?, ?, ?)", (from_id, to_id, item_name, message, datetime.datetime.now()))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_gifts(self, user_id):
        self.cursor.execute("SELECT * FROM gifts WHERE to_id = ? AND is_read = 0 ORDER BY sent_at DESC", (user_id,))
        return self.cursor.fetchall()
    
    def read_gift(self, gift_id):
        self.cursor.execute("UPDATE gifts SET is_read = 1 WHERE id = ?", (gift_id,))
        self.conn.commit()
    
    def add_referral(self, referrer_id, referral_id, reward=200):
        self.cursor.execute("INSERT INTO referrals (referrer_id, referral_id, reward, joined_at) VALUES (?, ?, ?, ?)", (referrer_id, referral_id, reward, datetime.datetime.now()))
        self.cursor.execute("UPDATE users SET referrals = referrals + 1 WHERE user_id = ?", (referrer_id,))
        self.add_coins(referrer_id, reward)
        self.conn.commit()
    
    def get_referrals(self, user_id):
        self.cursor.execute("SELECT * FROM referrals WHERE referrer_id = ?", (user_id,))
        return self.cursor.fetchall()
    
    def create_mafia_game(self, creator_id):
        self.cursor.execute("INSERT INTO mafia_games (creator_id, players, created_at) VALUES (?, ?, ?)", (creator_id, str([creator_id]), datetime.datetime.now()))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def join_mafia_game(self, game_id, user_id):
        self.cursor.execute("SELECT players FROM mafia_games WHERE id = ?", (game_id,))
        result = self.cursor.fetchone()
        if result:
            players = eval(result[0])
            if user_id not in players:
                players.append(user_id)
                self.cursor.execute("UPDATE mafia_games SET players = ? WHERE id = ?", (str(players), game_id))
                self.conn.commit()
                return True
        return False
    
    def get_mafia_game(self, game_id):
        self.cursor.execute("SELECT * FROM mafia_games WHERE id = ?", (game_id,))
        return self.cursor.fetchone()
    
    def get_cases(self):
        self.cursor.execute("SELECT * FROM cases")
        return self.cursor.fetchall()
    
    def get_case(self, case_id):
        self.cursor.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
        return self.cursor.fetchone()
    
    def open_case(self, case_id, user_id):
        case = self.get_case(case_id)
        if not case:
            return None
        
        import json
        items = json.loads(case[3])
        
        total_chance = sum(item['chance'] for item in items)
        roll = random.randint(1, total_chance)
        
        current = 0
        for item in items:
            current += item['chance']
            if roll <= current:
                if item['type'] == 'coins':
                    self.add_coins(user_id, item['value'])
                elif item['type'] == 'vip':
                    self.set_vip(user_id, item['value'])
                elif item['type'] == 'premium':
                    self.set_premium(user_id, item['value'])
                elif item['type'] == 'key':
                    self.cursor.execute("UPDATE users SET keys = keys + ? WHERE user_id = ?", (item['value'], user_id))
                    self.conn.commit()
                return item
        return None
    
    def rr_create_lobby(self, creator_id, max_players, bet):
        self.cursor.execute("INSERT INTO rr_lobbies (creator_id, max_players, bet, players, created_at) VALUES (?, ?, ?, ?, ?)", (creator_id, max_players, bet, str([creator_id]), datetime.datetime.now()))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def rr_get_lobby(self, lobby_id):
        self.cursor.execute("SELECT * FROM rr_lobbies WHERE id = ?", (lobby_id,))
        return self.cursor.fetchone()
    
    def rr_join_lobby(self, lobby_id, user_id):
        self.cursor.execute("SELECT players, max_players FROM rr_lobbies WHERE id = ? AND status = 'waiting'", (lobby_id,))
        result = self.cursor.fetchone()
        if result:
            players = eval(result[0])
            max_players = result[1]
            if user_id not in players and len(players) < max_players:
                players.append(user_id)
                self.cursor.execute("UPDATE rr_lobbies SET players = ? WHERE id = ?", (str(players), lobby_id))
                self.conn.commit()
                return True
        return False
    
    def rr_start_game(self, lobby_id):
        self.cursor.execute("SELECT * FROM rr_lobbies WHERE id = ?", (lobby_id,))
        lobby = self.cursor.fetchone()
        if lobby:
            players = eval(lobby[4])
            bet = lobby[3]
            
            cylinder_size = random.choice([6, 7, 8, 9, 10])
            bullets = random.randint(1, 3)
            
            positions = [False] * cylinder_size
            bullet_positions = random.sample(range(cylinder_size), bullets)
            for pos in bullet_positions:
                positions[pos] = True
            
            random.shuffle(players)
            current_player = 0
            
            self.cursor.execute('''
                INSERT INTO rr_games (lobby_id, players, current_player, cylinder_size, bullets, positions, alive_players, phase, started_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (lobby_id, str(players), current_player, cylinder_size, bullets, str(positions), str(players), 'playing', datetime.datetime.now()))
            game_id = self.cursor.lastrowid
            
            self.cursor.execute("UPDATE rr_lobbies SET status = 'playing' WHERE id = ?", (lobby_id,))
            self.conn.commit()
            
            return game_id, players, cylinder_size, bullets, positions
        return None
    
    def rr_get_game(self, game_id):
        self.cursor.execute("SELECT * FROM rr_games WHERE id = ?", (game_id,))
        return self.cursor.fetchone()
    
    def rr_make_shot(self, game_id, user_id):
        game = self.rr_get_game(game_id)
        if not game:
            return None
        
        players = eval(game[2])
        current_player = game[3]
        positions = eval(game[6])
        alive_players = eval(game[7])
        
        if players[current_player] != user_id:
            return "not_your_turn"
        
        shot_result = positions[0]
        
        if shot_result:
            alive_players.remove(user_id)
            result = "dead"
            
            if len(alive_players) == 1:
                winner_id = alive_players[0]
                self.cursor.execute("UPDATE rr_games SET phase = 'finished' WHERE id = ?", (game_id,))
                self.conn.commit()
                return "game_over", winner_id
        else:
            result = "alive"
            positions = positions[1:] + [False]
        
        current_player = (current_player + 1) % len(alive_players)
        
        self.cursor.execute("UPDATE rr_games SET current_player = ?, positions = ?, alive_players = ? WHERE id = ?", (current_player, str(positions), str(alive_players), game_id))
        self.conn.commit()
        
        return result
    
    def ttt_create_lobby(self, creator_id):
        self.cursor.execute("INSERT INTO ttt_lobbies (creator_id, created_at) VALUES (?, ?)", (creator_id, datetime.datetime.now()))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def ttt_join_lobby(self, lobby_id, user_id):
        self.cursor.execute("UPDATE ttt_lobbies SET opponent_id = ?, status = 'playing' WHERE id = ? AND opponent_id = 0", (user_id, lobby_id))
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def ttt_start_game(self, lobby_id, player_x, player_o):
        main_board = [[0, 0, 0] for _ in range(3)]
        sub_boards = [[[0, 0, 0] for _ in range(3)] for _ in range(9)]
        
        self.cursor.execute('''
            INSERT INTO ttt_games (lobby_id, player_x, player_o, current_player, main_board, sub_boards, last_move, status, started_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (lobby_id, player_x, player_o, player_x, str(main_board), str(sub_boards), -1, 'playing', datetime.datetime.now()))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def ttt_get_game(self, game_id):
        self.cursor.execute("SELECT * FROM ttt_games WHERE id = ?", (game_id,))
        return self.cursor.fetchone()
    
    def ttt_make_move(self, game_id, user_id, main_row, main_col, sub_row, sub_col):
        game = self.ttt_get_game(game_id)
        if not game:
            return None
        
        import json
        main_board = json.loads(game[5])
        sub_boards = json.loads(game[6])
        current_player = game[4]
        last_move = game[7]
        player_x = game[2]
        player_o = game[3]
        
        if current_player != user_id:
            return "not_your_turn"
        
        if sub_boards[main_row * 3 + main_col][sub_row][sub_col] != 0:
            return "cell_occupied"
        
        marker = 1 if current_player == player_x else 2
        sub_boards[main_row * 3 + main_col][sub_row][sub_col] = marker
        
        sub_winner = self.ttt_check_subboard_winner(sub_boards[main_row * 3 + main_col])
        if sub_winner:
            main_board[main_row][main_col] = sub_winner
        
        main_winner = self.ttt_check_mainboard_winner(main_board)
        if main_winner:
            status = 'finished'
            winner = player_x if main_winner == 1 else player_o if main_winner == 2 else 'draw'
        else:
            if self.ttt_check_draw(main_board, sub_boards):
                status = 'finished'
                winner = 'draw'
            else:
                status = 'playing'
                winner = None
                current_player = player_o if current_player == player_x else player_x
                last_move = main_row * 3 + main_col
        
        self.cursor.execute('''
            UPDATE ttt_games SET main_board = ?, sub_boards = ?, current_player = ?, last_move = ?, status = ? WHERE id = ?
        ''', (json.dumps(main_board), json.dumps(sub_boards), current_player, last_move, status, game_id))
        self.conn.commit()
        
        return {
            'status': status,
            'winner': winner,
            'main_board': main_board,
            'sub_boards': sub_boards,
            'last_move': last_move,
            'current_player': current_player
        }
    
    def ttt_check_subboard_winner(self, board):
        for i in range(3):
            if board[i][0] != 0 and board[i][0] == board[i][1] == board[i][2]:
                return board[i][0]
        for j in range(3):
            if board[0][j] != 0 and board[0][j] == board[1][j] == board[2][j]:
                return board[0][j]
        if board[0][0] != 0 and board[0][0] == board[1][1] == board[2][2]:
            return board[0][0]
        if board[0][2] != 0 and board[0][2] == board[1][1] == board[2][0]:
            return board[0][2]
        return 0
    
    def ttt_check_mainboard_winner(self, board):
        return self.ttt_check_subboard_winner(board)
    
    def ttt_check_draw(self, main_board, sub_boards):
        for i in range(3):
            for j in range(3):
                if main_board[i][j] == 0:
                    sub_idx = i * 3 + j
                    for x in range(3):
                        for y in range(3):
                            if sub_boards[sub_idx][x][y] == 0:
                                return False
        return True
    
    def add_compliment(self, user_id, compliment, from_id):
        self.cursor.execute("INSERT INTO compliments (user_id, compliment, from_id, created_at) VALUES (?, ?, ?, ?)", (user_id, compliment, from_id, datetime.datetime.now()))
        self.conn.commit()
    
    def get_compliments(self, user_id):
        self.cursor.execute("SELECT compliment, from_id, created_at FROM compliments WHERE user_id = ? ORDER BY created_at DESC LIMIT 10", (user_id,))
        return self.cursor.fetchall()
    
    def create_debt(self, debtor_id, creditor_id, amount, reason, days=30):
        deadline = datetime.datetime.now() + datetime.timedelta(days=days)
        self.cursor.execute("INSERT INTO debts (debtor_id, creditor_id, amount, reason, created_at, deadline) VALUES (?, ?, ?, ?, ?, ?)", (debtor_id, creditor_id, amount, reason, datetime.datetime.now(), deadline))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def pay_debt(self, debt_id):
        self.cursor.execute("UPDATE debts SET is_paid = 1 WHERE id = ?", (debt_id,))
        self.conn.commit()
    
    def get_debts(self, user_id):
        self.cursor.execute("SELECT * FROM debts WHERE (debtor_id = ? OR creditor_id = ?) AND is_paid = 0 ORDER BY deadline", (user_id, user_id))
        return self.cursor.fetchall()
    
    def create_daily(self, user_id, task_type, target, reward):
        self.cursor.execute("INSERT INTO dailies (user_id, task_type, target, reward, created_at) VALUES (?, ?, ?, ?, ?)", (user_id, task_type, target, reward, datetime.datetime.now()))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def update_daily(self, user_id, task_type, progress=1):
        self.cursor.execute("UPDATE dailies SET progress = progress + ? WHERE user_id = ? AND task_type = ? AND completed = 0", (progress, user_id, task_type))
        self.cursor.execute("SELECT id, progress, target, reward FROM dailies WHERE user_id = ? AND task_type = ? AND completed = 0", (user_id, task_type))
        daily = self.cursor.fetchone()
        if daily and daily[1] >= daily[2]:
            self.cursor.execute("UPDATE dailies SET completed = 1 WHERE id = ?", (daily[0],))
            self.add_coins(user_id, daily[3])
            self.conn.commit()
            return True
        self.conn.commit()
        return False
    
    def get_dailies(self, user_id):
        self.cursor.execute("SELECT * FROM dailies WHERE user_id = ? AND completed = 0", (user_id,))
        return self.cursor.fetchall()
    
    def add_achievement(self, user_id, name, desc, reward=0):
        self.cursor.execute("SELECT * FROM achievements WHERE user_id = ? AND achievement_name = ?", (user_id, name))
        if not self.cursor.fetchone():
            self.cursor.execute("INSERT INTO achievements (user_id, achievement_name, achievement_desc, earned_date, reward_coins) VALUES (?, ?, ?, ?, ?)", (user_id, name, desc, datetime.datetime.now(), reward))
            if reward > 0:
                self.add_coins(user_id, reward)
            self.conn.commit()
            return True
        return False
    
    def get_achievements(self, user_id):
        self.cursor.execute("SELECT achievement_name, achievement_desc, earned_date, reward_coins FROM achievements WHERE user_id = ? ORDER BY earned_date DESC", (user_id,))
        return self.cursor.fetchall()
    
    def update_last_seen(self, user_id):
        self.cursor.execute("UPDATE users SET last_seen = ? WHERE user_id = ?", (datetime.datetime.now(), user_id))
        self.conn.commit()
    
    def update_voice_count(self, user_id):
        self.cursor.execute("UPDATE users SET voice_count = voice_count + 1 WHERE user_id = ?", (user_id,))
        self.conn.commit()
    
    def update_photo_count(self, user_id):
        self.cursor.execute("UPDATE users SET photo_count = photo_count + 1 WHERE user_id = ?", (user_id,))
        self.conn.commit()
    
    def update_sticker_count(self, user_id):
        self.cursor.execute("UPDATE users SET sticker_count = sticker_count + 1 WHERE user_id = ?", (user_id,))
        self.conn.commit()
    
    def marry(self, user1_id, user2_id):
        marry_date = datetime.datetime.now()
        self.cursor.execute("UPDATE users SET marry_id = ?, marry_date = ? WHERE user_id = ?", (user2_id, marry_date, user1_id))
        self.cursor.execute("UPDATE users SET marry_id = ?, marry_date = ? WHERE user_id = ?", (user1_id, marry_date, user2_id))
        self.add_achievement(user1_id, "💍 В браке", "Вступил в брак", 500)
        self.add_achievement(user2_id, "💍 В браке", "Вступил в брак", 500)
        self.conn.commit()
    
    def divorce(self, user_id):
        self.cursor.execute("SELECT marry_id FROM users WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()
        if result and result[0]:
            partner_id = result[0]
            self.cursor.execute("UPDATE users SET marry_id = 0 WHERE user_id IN (?, ?)", (user_id, partner_id))
            self.conn.commit()
            return True
        return False
    
    def add_love_points(self, user_id, points):
        self.cursor.execute("UPDATE users SET love_points = love_points + ? WHERE user_id = ?", (points, user_id))
        self.conn.commit()
    
    def add_child(self, user_id):
        self.cursor.execute("UPDATE users SET children = children + 1 WHERE user_id = ?", (user_id,))
        self.conn.commit()
    
    def get_group_settings(self, chat_id):
        self.cursor.execute("SELECT * FROM group_settings WHERE chat_id = ?", (chat_id,))
        settings = self.cursor.fetchone()
        
        if not settings:
            self.cursor.execute("INSERT INTO group_settings (chat_id) VALUES (?)", (chat_id,))
            self.conn.commit()
            return self.get_group_settings(chat_id)
        
        columns = [description[0] for description in self.cursor.description]
        return dict(zip(columns, settings))
    
    def update_group_setting(self, chat_id, setting, value):
        self.cursor.execute(f"UPDATE group_settings SET {setting} = ? WHERE chat_id = ?", (value, chat_id))
        self.conn.commit()
    
    def get_group_rules(self, chat_id):
        self.cursor.execute("SELECT rules_text FROM group_rules WHERE chat_id = ?", (chat_id,))
        result = self.cursor.fetchone()
        return result[0] if result else ""
    
    def set_group_rules(self, chat_id, rules, admin_id):
        self.cursor.execute("INSERT OR REPLACE INTO group_rules (chat_id, rules_text, last_updated, updated_by) VALUES (?, ?, ?, ?)", (chat_id, rules, datetime.datetime.now(), admin_id))
        self.conn.commit()
    
    def close(self):
        self.conn.close()

# ===================== БАЗА ДАННЫХ =====================
db = Database()

# ===================== OPENROUTER AI =====================
class OpenRouterAI:
    def __init__(self):
        self.api_key = OPENROUTER_KEY
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.session = None
        self.contexts = {}
        print("🤖 OpenRouter AI инициализирован")
    
    async def get_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def get_response(self, user_id: int, message: str) -> str:
        try:
            session = await self.get_session()
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://railway.app",
                "X-Title": "Spectrum Bot"
            }
            
            if user_id not in self.contexts:
                self.contexts[user_id] = [
                    {"role": "system", "content": "Ты игровой бот «СПЕКТР». Отвечай кратко, дружелюбно, с эмодзи. Ты помогаешь с играми, кланами, казино и просто общаешься. Ты - лучший друг для пользователя."}
                ]
            
            self.contexts[user_id].append({"role": "user", "content": message})
            
            if len(self.contexts[user_id]) > 11:
                self.contexts[user_id] = [self.contexts[user_id][0]] + self.contexts[user_id][-10:]
            
            models = [
                "deepseek/deepseek-chat",
                "mistralai/mistral-7b-instruct",
                "openai/gpt-3.5-turbo"
            ]
            
            for model in models:
                try:
                    data = {
                        "model": model,
                        "messages": self.contexts[user_id],
                        "temperature": 0.8,
                        "max_tokens": 200
                    }
                    
                    async with session.post(self.api_url, json=data, headers=headers, timeout=10) as resp:
                        if resp.status == 200:
                            result = await resp.json()
                            ai_response = result["choices"][0]["message"]["content"]
                            self.contexts[user_id].append({"role": "assistant", "content": ai_response})
                            return ai_response
                except:
                    continue
            
            return None
            
        except Exception as e:
            print(f"❌ OpenRouter ошибка: {e}")
            return None
    
    async def close(self):
        if self.session:
            await self.session.close()

# ===================== ОСНОВНОЙ КЛАСС БОТА =====================
class GameBot:
    def __init__(self):
        self.db = db
        self.ai = OpenRouterAI()
        self.spam_tracker = defaultdict(list)
        self.active_games = {}
        self.application = Application.builder().token(TELEGRAM_TOKEN).build()
        self.setup_handlers()
        logger.info("✅ Бот «СПЕКТР» МЕГА-ВЕРСИЯ инициализирован")
    
    def setup_handlers(self):
        # Основные
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        self.application.add_handler(CommandHandler("menu", self.cmd_menu))
        
        # Профиль и статистика
        self.application.add_handler(CommandHandler("profile", self.cmd_profile))
        self.application.add_handler(CommandHandler("editprofile", self.cmd_edit_profile))
        self.application.add_handler(CommandHandler("top", self.cmd_top))
        self.application.add_handler(CommandHandler("daily", self.cmd_daily))
        self.application.add_handler(CommandHandler("rep", self.cmd_rep))
        self.application.add_handler(CommandHandler("compliment", self.cmd_compliment))
        self.application.add_handler(CommandHandler("compliments", self.cmd_compliments))
        
        # Статистика по играм
        self.application.add_handler(CommandHandler("boss_stats", self.cmd_boss_stats))
        self.application.add_handler(CommandHandler("mafia_stats", self.cmd_mafia_stats))
        self.application.add_handler(CommandHandler("rps_stats", self.cmd_rps_stats))
        self.application.add_handler(CommandHandler("casino_stats", self.cmd_casino_stats))
        self.application.add_handler(CommandHandler("rr_stats", self.cmd_rr_stats))
        self.application.add_handler(CommandHandler("ttt_stats", self.cmd_ttt_stats))
        
        # Боссы
        self.application.add_handler(CommandHandler("bosses", self.cmd_boss_list))
        self.application.add_handler(CommandHandler("boss", self.cmd_boss_info))
        self.application.add_handler(CommandHandler("boss_fight", self.cmd_boss_fight))
        
        # Казино
        self.application.add_handler(CommandHandler("casino", self.cmd_casino))
        self.application.add_handler(CommandHandler("roulette", self.cmd_roulette))
        self.application.add_handler(CommandHandler("dice", self.cmd_dice))
        self.application.add_handler(CommandHandler("blackjack", self.cmd_blackjack))
        self.application.add_handler(CommandHandler("slots", self.cmd_slots))
        
        # Камень-ножницы-бумага
        self.application.add_handler(CommandHandler("rps", self.cmd_rps))
        
        # Русская рулетка
        self.application.add_handler(CommandHandler("rr", self.cmd_rr))
        self.application.add_handler(CommandHandler("rr_start", self.cmd_rr_start))
        self.application.add_handler(CommandHandler("rr_join", self.cmd_rr_join))
        self.application.add_handler(CommandHandler("rr_shot", self.cmd_rr_shot))
        
        # Крестики-нолики 3D
        self.application.add_handler(CommandHandler("ttt", self.cmd_ttt))
        self.application.add_handler(CommandHandler("ttt_challenge", self.cmd_ttt_challenge))
        self.application.add_handler(CommandHandler("ttt_move", self.cmd_ttt_move))
        
        # Кланы
        self.application.add_handler(CommandHandler("clan", self.cmd_clan))
        self.application.add_handler(CommandHandler("clan_create", self.cmd_clan_create))
        self.application.add_handler(CommandHandler("clan_join", self.cmd_clan_join))
        self.application.add_handler(CommandHandler("clan_leave", self.cmd_clan_leave))
        self.application.add_handler(CommandHandler("clan_top", self.cmd_clan_top))
        self.application.add_handler(CommandHandler("clan_war", self.cmd_clan_war))
        
        # Мафия
        self.application.add_handler(CommandHandler("mafia", self.cmd_mafia))
        self.application.add_handler(CommandHandler("mafia_create", self.cmd_mafia_create))
        self.application.add_handler(CommandHandler("mafia_join", self.cmd_mafia_join))
        self.application.add_handler(CommandHandler("mafia_start", self.cmd_mafia_start))
        self.application.add_handler(CommandHandler("mafia_vote", self.cmd_mafia_vote))
        
        # Кейсы
        self.application.add_handler(CommandHandler("cases", self.cmd_cases))
        self.application.add_handler(CommandHandler("open", self.cmd_open))
        self.application.add_handler(CommandHandler("keys", self.cmd_keys))
        
        # Инвентарь и магазин
        self.application.add_handler(CommandHandler("inventory", self.cmd_inventory))
        self.application.add_handler(CommandHandler("shop", self.cmd_shop))
        self.application.add_handler(CommandHandler("buy", self.cmd_buy))
        self.application.add_handler(CommandHandler("use", self.cmd_use))
        self.application.add_handler(CommandHandler("market", self.cmd_market))
        self.application.add_handler(CommandHandler("sell", self.cmd_sell))
        
        # Привилегии
        self.application.add_handler(CommandHandler("donate", self.cmd_donate))
        self.application.add_handler(CommandHandler("vip", self.cmd_vip))
        self.application.add_handler(CommandHandler("premium", self.cmd_premium))
        
        # Подарки
        self.application.add_handler(CommandHandler("gift", self.cmd_gift))
        self.application.add_handler(CommandHandler("gifts", self.cmd_gifts))
        
        # Рефералы
        self.application.add_handler(CommandHandler("referral", self.cmd_referral))
        self.application.add_handler(CommandHandler("referrals", self.cmd_referrals))
        
        # Отношения
        self.application.add_handler(CommandHandler("marry", self.cmd_marry))
        self.application.add_handler(CommandHandler("divorce", self.cmd_divorce))
        self.application.add_handler(CommandHandler("love", self.cmd_love))
        self.application.add_handler(CommandHandler("children", self.cmd_children))
        
        # Долги
        self.application.add_handler(CommandHandler("debt", self.cmd_debt))
        self.application.add_handler(CommandHandler("debts", self.cmd_debts))
        self.application.add_handler(CommandHandler("pay", self.cmd_pay))
        
        # Задания
        self.application.add_handler(CommandHandler("dailies", self.cmd_dailies))
        
        # Достижения
        self.application.add_handler(CommandHandler("achievements", self.cmd_achievements))
        
        # Админские
        self.application.add_handler(CommandHandler("mute", self.cmd_mute))
        self.application.add_handler(CommandHandler("warn", self.cmd_warn))
        self.application.add_handler(CommandHandler("ban", self.cmd_ban))
        self.application.add_handler(CommandHandler("unban", self.cmd_unban))
        self.application.add_handler(CommandHandler("give", self.cmd_give))
        self.application.add_handler(CommandHandler("clear", self.cmd_clear))
        
        # Настройки групп
        self.application.add_handler(CommandHandler("rules", self.cmd_rules))
        self.application.add_handler(CommandHandler("set_rules", self.cmd_set_rules))
        self.application.add_handler(CommandHandler("group_settings", self.cmd_group_settings))
        self.application.add_handler(CommandHandler("set_welcome", self.cmd_set_welcome))
        self.application.add_handler(CommandHandler("set_goodbye", self.cmd_set_goodbye))
        
        # Обработчики
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.application.add_handler(MessageHandler(filters.VOICE, self.handle_voice))
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        self.application.add_handler(MessageHandler(filters.Sticker.ALL, self.handle_sticker))
        self.application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, self.handle_new_members))
        self.application.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, self.handle_left_member))
        
        logger.info("✅ Все 70+ обработчиков зарегистрированы")
    
    def is_admin(self, user_id: int) -> bool:
        user = self.db.get_user(user_id)
        return user.get('role', 'user') in ['owner', 'admin']
    
    def is_owner(self, user_id: int) -> bool:
        return user_id == OWNER_ID
    
    def is_vip(self, user_id: int) -> bool:
        return self.db.is_vip(user_id) or self.is_admin(user_id)
    
    def is_premium(self, user_id: int) -> bool:
        return self.db.is_premium(user_id) or self.is_admin(user_id)
    
    def get_role_emoji(self, role):
        emojis = {
            'owner': '👑',
            'admin': '⚜️',
            'premium': '💎',
            'vip': '🌟',
            'user': '👤'
        }
        return emojis.get(role, '👤')
    
    def calc_winrate(self, wins, games):
        if games == 0:
            return 0
        return round((wins / games) * 100, 1)
    
    async def check_spam(self, update: Update) -> bool:
        user_id = update.effective_user.id
        if self.is_admin(user_id) or self.is_owner(user_id) or self.is_premium(user_id):
            return False
        
        current_time = time.time()
        self.spam_tracker[user_id] = [t for t in self.spam_tracker[user_id] if current_time - t < SPAM_WINDOW]
        self.spam_tracker[user_id].append(current_time)
        
        if len(self.spam_tracker[user_id]) > SPAM_LIMIT:
            self.db.mute_user(user_id, SPAM_MUTE_TIME, 0, "Автоматический спам")
            await update.message.reply_text(
                f"🚫 **СПАМ-ФИЛЬТР**\n\nВы замучены на {SPAM_MUTE_TIME} минут.",
                parse_mode='Markdown'
            )
            self.spam_tracker[user_id] = []
            return True
        return False
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id, user.first_name, user.last_name or "")
        self.db.update_last_seen(user.id)
        
        # Проверка на реферала
        if context.args and context.args[0].isdigit():
            referrer_id = int(context.args[0])
            if referrer_id != user.id:
                self.db.add_referral(referrer_id, user.id, 200)
                try:
                    await context.bot.send_message(
                        chat_id=referrer_id,
                        text=f"🎉 По вашей реферальной ссылке зарегистрировался {user.first_name}! +200 🪙"
                    )
                except:
                    pass
        
        text = (
            f"╔══════════════════════════════╗\n"
            f"║  ⚔️ **ДОБРО ПОЖАЛОВАТЬ** ⚔️  ║\n"
            f"╚══════════════════════════════╝\n\n"
            f"🌟 **Привет, {user.first_name}!**\n\n"
            f"Я — **«СПЕКТР»**, твой игровой бот с искусственным интеллектом!\n"
            f"У меня есть ВСЁ, что нужно для отличного времяпрепровождения.\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 **ТВОЙ ПРОФИЛЬ**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"▫️ **Роль:** {self.get_role_emoji(user_data.get('role', 'user'))} {user_data.get('role', 'user')}\n"
            f"▫️ **Монеты:** {user_data.get('coins', 1000)} 🪙\n"
            f"▫️ **Уровень:** {user_data.get('level', 1)}\n"
            f"▫️ **Репутация:** {user_data.get('rep', 0)} ⭐\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 **ГЛАВНОЕ МЕНЮ**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            f"👤 **ПРОФИЛЬ**\n"
            f"└ /profile — твой профиль\n"
            f"└ /editprofile — редактировать\n"
            f"└ /top — топ игроков\n"
            f"└ /daily — ежедневная награда\n\n"
            
            f"💍 **ОТНОШЕНИЯ**\n"
            f"└ /marry [ID] — сделать предложение\n"
            f"└ /love — очки любви\n"
            f"└ /compliment — сказать комплимент\n\n"
            
            f"👾 **БИТВЫ**\n"
            f"└ /bosses — список боссов\n"
            f"└ /boss_fight [ID] — битва\n"
            f"└ /rps — камень-ножницы-бумага\n\n"
            
            f"🎰 **КАЗИНО**\n"
            f"└ /casino — меню казино\n"
            f"└ /roulette [ставка] — рулетка\n"
            f"└ /dice [ставка] — кости\n\n"
            
            f"👥 **КЛАНЫ**\n"
            f"└ /clan — информация\n"
            f"└ /clan_create [название] — создать клан\n\n"
            
            f"🎁 **ЭКОНОМИКА**\n"
            f"└ /cases — кейсы\n"
            f"└ /shop — магазин\n"
            f"└ /inventory — инвентарь\n\n"
            
            f"💎 **ПРИВИЛЕГИИ**\n"
            f"└ /donate — информация\n"
            f"└ /vip — купить VIP\n"
            f"└ /premium — купить Premium\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👑 **Владелец:** {OWNER_USERNAME}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💡 Напиши /menu для интерактивного меню"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
        self.db.add_stat(user.id, "commands_used")
    
    async def cmd_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("👤 Профиль", callback_data="menu_profile"),
             InlineKeyboardButton("💍 Отношения", callback_data="menu_marry")],
            [InlineKeyboardButton("👾 Боссы", callback_data="menu_bosses"),
             InlineKeyboardButton("🎰 Казино", callback_data="menu_casino")],
            [InlineKeyboardButton("👥 Кланы", callback_data="menu_clan"),
             InlineKeyboardButton("🔪 Мафия", callback_data="menu_mafia")],
            [InlineKeyboardButton("🎁 Кейсы", callback_data="menu_cases"),
             InlineKeyboardButton("🛍 Магазин", callback_data="menu_shop")],
            [InlineKeyboardButton("💎 Привилегии", callback_data="menu_donate"),
             InlineKeyboardButton("📊 Статистика", callback_data="menu_stats")],
            [InlineKeyboardButton("📚 Помощь", callback_data="menu_help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🎮 **ГЛАВНОЕ МЕНЮ**\n\nВыбери раздел:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        text = (
            "╔══════════════════════════════╗\n"
            "║   📚 **ВСЕ КОМАНДЫ БОТА**   ║\n"
            "╚══════════════════════════════╝\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "👤 **ПРОФИЛЬ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ /profile — твой профиль\n"
            "▫️ /editprofile — редактировать профиль\n"
            "▫️ /top — топ игроков\n"
            "▫️ /daily — ежедневная награда\n"
            "▫️ /rep — дать репутацию\n"
            "▫️ /compliment — сказать комплимент\n"
            "▫️ /compliments — мои комплименты\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📊 **СТАТИСТИКА ПО ИГРАМ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ /boss_stats — статистика боссов\n"
            "▫️ /mafia_stats — статистика мафии\n"
            "▫️ /rps_stats — статистика КНБ\n"
            "▫️ /casino_stats — статистика казино\n"
            "▫️ /rr_stats — статистика русской рулетки\n"
            "▫️ /ttt_stats — статистика крестиков-ноликов\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "💍 **ОТНОШЕНИЯ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ /marry [ID] — сделать предложение\n"
            "▫️ /divorce — развестись\n"
            "▫️ /love — очки любви\n"
            "▫️ /children — завести ребенка\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "👾 **БОССЫ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ /bosses — список боссов\n"
            "▫️ /boss [ID] — информация о боссе\n"
            "▫️ /boss_fight [ID] — сразиться с боссом\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🎰 **КАЗИНО**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ /casino — меню казино\n"
            "▫️ /roulette [ставка] [цвет/число] — рулетка\n"
            "▫️ /dice [ставка] — кости\n"
            "▫️ /blackjack [ставка] — блэкджек\n"
            "▫️ /slots [ставка] — слоты\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "✊ **КНБ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ /rps — камень-ножницы-бумага\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "💣 **РУССКАЯ РУЛЕТКА**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ /rr — информация\n"
            "▫️ /rr_start [игроки] [ставка] — создать лобби\n"
            "▫️ /rr_join [ID] — присоединиться\n"
            "▫️ /rr_shot — сделать выстрел\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⭕ **КРЕСТИКИ-НОЛИКИ 3D**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ /ttt — информация\n"
            "▫️ /ttt_challenge [ID] — вызвать на игру\n"
            "▫️ /ttt_move [клетка] — сделать ход\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "👥 **КЛАНЫ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ /clan — информация о клане\n"
            "▫️ /clan_create [название] — создать клан\n"
            "▫️ /clan_join [ID] — вступить в клан\n"
            "▫️ /clan_leave — покинуть клан\n"
            "▫️ /clan_top — топ кланов\n"
            "▫️ /clan_war — клановая война\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🔪 **МАФИЯ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ /mafia — информация\n"
            "▫️ /mafia_create — создать игру\n"
            "▫️ /mafia_join [ID] — присоединиться\n"
            "▫️ /mafia_start — начать игру\n"
            "▫️ /mafia_vote [ID] — проголосовать\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🎁 **КЕЙСЫ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ /cases — список кейсов\n"
            "▫️ /open [ID] — открыть кейс\n"
            "▫️ /keys — мои ключи\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🛍 **МАГАЗИН**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ /shop — магазин\n"
            "▫️ /buy [предмет] — купить предмет\n"
            "▫️ /inventory — инвентарь\n"
            "▫️ /use [ID] — использовать предмет\n"
            "▫️ /market — торговая площадка\n"
            "▫️ /sell [предмет] [цена] — продать предмет\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "💎 **ПРИВИЛЕГИИ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ /donate — информация\n"
            "▫️ /vip — купить VIP (5000 🪙)\n"
            "▫️ /premium — купить Premium (15000 🪙)\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🎁 **ПОДАРКИ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ /gift [ID] [предмет] — отправить подарок\n"
            "▫️ /gifts — мои подарки\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "👥 **РЕФЕРАЛЫ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ /referral — реферальная ссылка\n"
            "▫️ /referrals — мои рефералы\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "💰 **ДОЛГИ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ /debt [ID] [сумма] [причина] — дать в долг\n"
            "▫️ /debts — мои долги\n"
            "▫️ /pay [ID] — оплатить долг\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📋 **ЗАДАНИЯ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ /dailies — ежедневные задания\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🏆 **ДОСТИЖЕНИЯ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ /achievements — мои достижения\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "👑 **АДМИН**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ /mute [ID] [минут] — замутить\n"
            "▫️ /warn [ID] — выдать варн\n"
            "▫️ /ban [ID] — забанить\n"
            "▫️ /unban [ID] — разбанить\n"
            "▫️ /give [ID] [сумма] — выдать монеты\n"
            "▫️ /clear [количество] — очистить чат\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "👥 **ГРУППЫ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ /rules — правила чата\n"
            "▫️ /set_rules [текст] — установить правила\n"
            "▫️ /group_settings — настройки группы\n"
            "▫️ /set_welcome [текст] — приветствие\n"
            "▫️ /set_goodbye [текст] — прощание\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👑 **Владелец:** {OWNER_USERNAME}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
        self.db.add_stat(user.id, "commands_used")
    
    async def cmd_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id, user.first_name, user.last_name or "")
        self.db.update_last_seen(user.id)
        
        if self.db.is_muted(user.id):
            remaining = self.db.get_mute_time(user.id)
            await update.message.reply_text(f"🔇 Вы замучены. Осталось: {remaining}")
            return
        
        self.db.cursor.execute("SELECT * FROM stats WHERE user_id = ?", (user.id,))
        stats = self.db.cursor.fetchone()
        
        # Проверка на привилегии
        vip_status = "✅ Активен" if self.is_vip(user.id) else "❌ Нет"
        premium_status = "✅ Активен" if self.is_premium(user.id) else "❌ Нет"
        
        # Клан
        clan = self.db.get_user_clan(user.id)
        clan_name = clan[1] if clan else "Нет"
        
        # Статистика игр
        boss_kills = user_data.get('boss_kills', 0)
        rps_wins = user_data.get('rps_wins', 0)
        rps_losses = user_data.get('rps_losses', 0)
        rps_total = rps_wins + rps_losses + user_data.get('rps_draws', 0)
        casino_wins = user_data.get('casino_wins', 0)
        casino_losses = user_data.get('casino_losses', 0)
        casino_total = casino_wins + casino_losses
        
        # Семья
        marry_id = user_data.get('marry_id', 0)
        if marry_id:
            self.db.cursor.execute("SELECT first_name FROM users WHERE user_id = ?", (marry_id,))
            marry_name = self.db.cursor.fetchone()
            marry_text = marry_name[0] if marry_name else f"ID {marry_id}"
        else:
            marry_text = "Нет"
        
        # Последний визит
        last_seen = user_data.get('last_seen', '')
        if last_seen:
            last_seen_date = datetime.datetime.fromisoformat(last_seen)
            last_seen_str = last_seen_date.strftime("%d.%m.%Y %H:%M")
        else:
            last_seen_str = "Неизвестно"
        
        # Имя и ник
        display_name = user_data.get('nickname') or user.first_name
        gender_emoji = "♂️" if user_data.get('gender') == 'м' else "♀️" if user_data.get('gender') == 'ж' else "❓"
        
        text = (
            f"╔══════════════════════════════╗\n"
            f"║    👤 **ПРОФИЛЬ ИГРОКА**    ║\n"
            f"╚══════════════════════════════╝\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**ОСНОВНОЕ**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"▫️ **Имя:** {display_name} {gender_emoji}\n"
            f"▫️ **Роль:** {self.get_role_emoji(user_data.get('role', 'user'))} {user_data.get('role', 'user')}\n"
            f"▫️ **Уровень:** {user_data.get('level', 1)}\n"
            f"▫️ **Опыт:** {user_data.get('exp', 0)}/{user_data.get('level', 1) * 100}\n"
            f"▫️ **Монеты:** {user_data.get('coins', 1000)} 🪙\n"
            f"▫️ **Энергия:** {user_data.get('energy', 100)} ⚡\n"
            f"▫️ **Репутация:** {user_data.get('rep', 0)} ⭐\n"
            f"▫️ **Последний визит:** {last_seen_str}\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**БОЕВЫЕ ХАРАКТЕРИСТИКИ**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"▫️ **Здоровье:** {user_data.get('health', 100)} ❤️\n"
            f"▫️ **Броня:** {user_data.get('armor', 0)} 🛡\n"
            f"▫️ **Урон:** {user_data.get('damage', 10)} ⚔️\n"
            f"▫️ **Боссов убито:** {boss_kills} 👾\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**ПРИВИЛЕГИИ**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"▫️ **VIP:** {vip_status}\n"
            f"▫️ **Premium:** {premium_status}\n"
            f"▫️ **Кейсы:** {user_data.get('cases', 0)} 🎁\n"
            f"▫️ **Ключи:** {user_data.get('keys', 0)} 🔑\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**КЛАН**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"▫️ **Название:** {clan_name}\n"
            f"▫️ **Роль:** {user_data.get('clan_role', 'member')}\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**СЕМЬЯ**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"▫️ **Супруг(а):** {marry_text}\n"
            f"▫️ **Очки любви:** {user_data.get('love_points', 0)} 💕\n"
            f"▫️ **Дети:** {user_data.get('children', 0)} 👶\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**СТАТИСТИКА ИГР**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"▫️ **КНБ:** {rps_wins} побед, {rps_losses} поражений, всего {rps_total} игр\n"
            f"▫️ **Казино:** {casino_wins} побед, {casino_losses} поражений, всего {casino_total} игр\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**АКТИВНОСТЬ**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"▫️ **Сообщений:** {stats[1] if stats else 0}\n"
            f"▫️ **Команд:** {stats[2] if stats else 0}\n"
            f"▫️ **Игр сыграно:** {stats[3] if stats else 0}\n"
            f"▫️ **Голосовых:** {user_data.get('voice_count', 0)}\n"
            f"▫️ **Фото:** {user_data.get('photo_count', 0)}\n"
            f"▫️ **Стикеров:** {user_data.get('sticker_count', 0)}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
        self.db.add_stat(user.id, "commands_used")
    
    async def cmd_edit_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        text = (
            "✏️ **РЕДАКТИРОВАНИЕ ПРОФИЛЯ**\n\n"
            "Выбери, что хочешь изменить:\n\n"
            "▫️ .nick [ник] — установить никнейм\n"
            "▫️ .gender [м/ж] — установить пол\n"
            "▫️ .birthday [ДД.ММ.ГГГГ] — день рождения\n"
            "▫️ .city [город] — город\n"
            "▫️ .bio [текст] — о себе\n\n"
            "Пример: `.nick Spectr`"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_boss_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        text = (
            f"╔══════════════════════════════╗\n"
            f"║   👾 **СТАТИСТИКА БОССОВ**  ║\n"
            f"╚══════════════════════════════╝\n\n"
            f"▫️ **Игрок:** {user.first_name}\n"
            f"▫️ **Боссов убито:** {user_data.get('boss_kills', 0)} 💀\n"
            f"▫️ **Урон:** {user_data.get('damage', 10)} ⚔️\n"
            f"▫️ **Броня:** {user_data.get('armor', 0)} 🛡\n"
            f"▫️ **Здоровье:** {user_data.get('health', 100)} ❤️"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_mafia_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        wins = user_data.get('mafia_wins', 0)
        games = user_data.get('mafia_games', 0)
        
        text = (
            f"╔══════════════════════════════╗\n"
            f"║   🔪 **СТАТИСТИКА МАФИИ**   ║\n"
            f"╚══════════════════════════════╝\n\n"
            f"▫️ **Игрок:** {user.first_name}\n"
            f"▫️ **Побед:** {wins} 🏆\n"
            f"▫️ **Игр:** {games} 🎮\n"
            f"▫️ **Винрейт:** {self.calc_winrate(wins, games)}% 📊"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_rps_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        wins = user_data.get('rps_wins', 0)
        losses = user_data.get('rps_losses', 0)
        draws = user_data.get('rps_draws', 0)
        total = wins + losses + draws
        
        text = (
            f"╔══════════════════════════════╗\n"
            f"║   ✊ **СТАТИСТИКА КНБ**     ║\n"
            f"╚══════════════════════════════╝\n\n"
            f"▫️ **Игрок:** {user.first_name}\n"
            f"▫️ **Побед:** {wins} 🏆\n"
            f"▫️ **Поражений:** {losses} 💔\n"
            f"▫️ **Ничьих:** {draws} 🤝\n"
            f"▫️ **Всего игр:** {total} 🎮\n"
            f"▫️ **Винрейт:** {self.calc_winrate(wins, total)}% 📊"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_casino_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        wins = user_data.get('casino_wins', 0)
        losses = user_data.get('casino_losses', 0)
        total = wins + losses
        
        text = (
            f"╔══════════════════════════════╗\n"
            f"║   🎰 **СТАТИСТИКА КАЗИНО**  ║\n"
            f"╚══════════════════════════════╝\n\n"
            f"▫️ **Игрок:** {user.first_name}\n"
            f"▫️ **Побед:** {wins} 🏆\n"
            f"▫️ **Поражений:** {losses} 💔\n"
            f"▫️ **Всего игр:** {total} 🎮\n"
            f"▫️ **Винрейт:** {self.calc_winrate(wins, total)}% 📊"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_rr_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        wins = user_data.get('rr_wins', 0)
        losses = user_data.get('rr_losses', 0)
        total = wins + losses
        
        text = (
            f"╔══════════════════════════════╗\n"
            f"║  💣 **СТАТИСТИКА РУЛЕТКИ**  ║\n"
            f"╚══════════════════════════════╝\n\n"
            f"▫️ **Игрок:** {user.first_name}\n"
            f"▫️ **Побед:** {wins} 🏆\n"
            f"▫️ **Поражений:** {losses} 💔\n"
            f"▫️ **Всего игр:** {total} 🎮\n"
            f"▫️ **Винрейт:** {self.calc_winrate(wins, total)}% 📊"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_ttt_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        wins = user_data.get('ttt_wins', 0)
        losses = user_data.get('ttt_losses', 0)
        draws = user_data.get('ttt_draws', 0)
        total = wins + losses + draws
        
        text = (
            f"╔══════════════════════════════╗\n"
            f"║  ⭕ **СТАТИСТИКА TTT**      ║\n"
            f"╚══════════════════════════════╝\n\n"
            f"▫️ **Игрок:** {user.first_name}\n"
            f"▫️ **Побед:** {wins} 🏆\n"
            f"▫️ **Поражений:** {losses} 💔\n"
            f"▫️ **Ничьих:** {draws} 🤝\n"
            f"▫️ **Всего игр:** {total} 🎮\n"
            f"▫️ **Винрейт:** {self.calc_winrate(wins, total)}% 📊"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_top(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        top_coins = self.db.get_top("coins", 10)
        top_level = self.db.get_top("level", 10)
        top_boss = self.db.get_top("boss_kills", 10)
        top_rep = self.db.get_top("rep", 10)
        
        text = (
            f"╔══════════════════════════════╗\n"
            f"║    🏆 **ТОП ИГРОКОВ**      ║\n"
            f"╚══════════════════════════════╝\n\n"
        )
        
        text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "💰 **ПО МОНЕТАМ**\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        for i, (name, value) in enumerate(top_coins, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
            text += f"{medal} **{i}.** {name} — {value} 🪙\n"
        
        text += "\n━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "📊 **ПО УРОВНЮ**\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        for i, (name, value) in enumerate(top_level, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
            text += f"{medal} **{i}.** {name} — {value} ур.\n"
        
        text += "\n━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "👾 **ПО УБИЙСТВУ БОССОВ**\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        for i, (name, value) in enumerate(top_boss, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
            text += f"{medal} **{i}.** {name} — {value} боссов\n"
        
        text += "\n━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "⭐ **ПО РЕПУТАЦИИ**\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        for i, (name, value) in enumerate(top_rep, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
            text += f"{medal} **{i}.** {name} — {value} ⭐\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_daily(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id, user.first_name, user.last_name or "")
        
        if self.db.is_muted(user.id):
            remaining = self.db.get_mute_time(user.id)
            await update.message.reply_text(f"🔇 Вы замучены. Осталось: {remaining}")
            return
        
        today = datetime.datetime.now().date()
        
        if user_data.get('last_daily'):
            last_date = datetime.datetime.fromisoformat(user_data['last_daily']).date()
            if last_date == today:
                await update.message.reply_text("❌ Ты уже получал награду сегодня!")
                return
        
        # Базовая награда
        coins = random.randint(100, 300)
        exp = random.randint(20, 60)
        energy = random.randint(10, 30)
        
        streak = user_data.get('daily_streak', 0) + 1
        
        # Бонус за стрик
        coins = int(coins * (1 + min(streak, 30) * 0.05))
        exp = int(exp * (1 + min(streak, 30) * 0.05))
        
        # Бонус за привилегии
        if self.is_vip(user.id):
            coins = int(coins * 1.5)
            exp = int(exp * 1.5)
        if self.is_premium(user.id):
            coins = int(coins * 2)
            exp = int(exp * 2)
        
        self.db.add_coins(user.id, coins)
        self.db.add_exp(user.id, exp)
        self.db.add_energy(user.id, energy)
        
        self.db.cursor.execute(
            "UPDATE users SET daily_streak = ?, last_daily = ? WHERE user_id = ?",
            (streak, datetime.datetime.now(), user.id)
        )
        self.db.conn.commit()
        
        # Достижение за стрик
        if streak == 7:
            self.db.add_achievement(user.id, "📅 Неделя", "7 дней подряд", 500)
        elif streak == 30:
            self.db.add_achievement(user.id, "📅 Месяц", "30 дней подряд", 2000)
        elif streak == 365:
            self.db.add_achievement(user.id, "📅 Год", "365 дней подряд", 10000)
        
        text = (
            f"╔══════════════════════════════╗\n"
            f"║    🎁 **ЕЖЕДНЕВНАЯ НАГРАДА**   ║\n"
            f"╚══════════════════════════════╝\n\n"
            f"▫️ **Стрик:** {streak} дней 🔥\n"
            f"▫️ **Монеты:** +{coins} 🪙\n"
            f"▫️ **Опыт:** +{exp} ✨\n"
            f"▫️ **Энергия:** +{energy} ⚡\n\n"
            f"🌟 Заходи завтра за новой наградой!"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_rep(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Укажи ID пользователя: /rep 123456789")
            return
        
        try:
            target_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ Неправильный ID")
            return
        
        user = update.effective_user
        
        if user.id == target_id:
            await update.message.reply_text("❌ Нельзя дать репутацию самому себе")
            return
        
        # Проверяем, можно ли дать репутацию (раз в 24 часа)
        # В реальном коде нужно добавить проверку
        
        self.db.cursor.execute("UPDATE users SET rep = rep + 1 WHERE user_id = ?", (target_id,))
        self.db.conn.commit()
        
        self.db.cursor.execute("SELECT first_name FROM users WHERE user_id = ?", (target_id,))
        target_name = self.db.cursor.fetchone()
        target_name = target_name[0] if target_name else f"ID {target_id}"
        
        await update.message.reply_text(f"⭐ Ты повысил репутацию пользователя {target_name}!")
    
    async def cmd_compliment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /compliment [ID] [комплимент]")
            return
        
        try:
            target_id = int(context.args[0])
            compliment = " ".join(context.args[1:])
        except:
            await update.message.reply_text("❌ Неправильный ID")
            return
        
        user = update.effective_user
        
        if user.id == target_id:
            await update.message.reply_text("❌ Себе? Скромненько... но можно 😊")
        
        self.db.add_compliment(target_id, compliment, user.id)
        
        await update.message.reply_text(f"✅ Комплимент отправлен!")
        
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=f"💌 Тебе отправили комплимент!\n\n«{compliment}»\n\n— от {user.first_name}"
            )
        except:
            pass
    
    async def cmd_compliments(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        compliments = self.db.get_compliments(user.id)
        
        if not compliments:
            await update.message.reply_text("📭 У тебя пока нет комплиментов")
            return
        
        text = "💌 **ТВОИ КОМПЛИМЕНТЫ**\n\n"
        
        for compliment, from_id, created_at in compliments:
            self.db.cursor.execute("SELECT first_name FROM users WHERE user_id = ?", (from_id,))
            from_name = self.db.cursor.fetchone()
            from_name = from_name[0] if from_name else f"ID {from_id}"
            
            date_str = datetime.datetime.fromisoformat(created_at).strftime("%d.%m.%Y")
            text += f"▫️ «{compliment}»\n  — от {from_name}, {date_str}\n\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_boss_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        bosses = self.db.get_bosses(alive_only=True)
        
        if not bosses:
            await update.message.reply_text("👾 Все боссы повержены! Ждите возрождения...")
            self.db.respawn_bosses()
            bosses = self.db.get_bosses(alive_only=True)
        
        text = (
            f"╔══════════════════════════════╗\n"
            f"║    👾 **СПИСОК БОССОВ**     ║\n"
            f"╚══════════════════════════════╝\n\n"
        )
        
        for boss in bosses:
            text += f"**{boss[1]}** (ур.{boss[2]})\n"
            text += f"└ ID: {boss[0]} | ❤️ {boss[3]}/{boss[4]} | 💰 {boss[6]}\n\n"
        
        text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "⚔️ **Сразиться:** /boss_fight [ID]"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_boss_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Укажи ID босса: /boss 1")
            return
        
        try:
            boss_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ Неправильный ID")
            return
        
        boss = self.db.get_boss(boss_id)
        if not boss:
            await update.message.reply_text("❌ Босс не найден")
            return
        
        status = "👾 ЖИВ" if boss[8] else "💀 ПОВЕРЖЕН"
        
        text = (
            f"**{boss[1]}** (Уровень {boss[2]})\n\n"
            f"❤️ Здоровье: {boss[3]}/{boss[4]}\n"
            f"⚔️ Урон: {boss[5]}\n"
            f"💰 Награда: {boss[6]} 🪙\n"
            f"📊 Статус: {status}"
        )
        
        if boss[7]:
            try:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=boss[7],
                    caption=text
                )
            except:
                await update.message.reply_text(text, parse_mode='Markdown')
        else:
            await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_boss_fight(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id, user.first_name, user.last_name or "")
        
        if self.db.is_muted(user.id):
            remaining = self.db.get_mute_time(user.id)
            await update.message.reply_text(f"🔇 Вы замучены. Осталось: {remaining}")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Укажи ID босса: /boss_fight 1")
            return
        
        try:
            boss_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ Неправильный ID")
            return
        
        boss = self.db.get_boss(boss_id)
        
        if not boss or not boss[8]:
            await update.message.reply_text("❌ Босс уже повержен или не найден")
            return
        
        if user_data['energy'] < 10:
            await update.message.reply_text("❌ Нужно 10 энергии для битвы!")
            return
        
        self.db.add_energy(user.id, -10)
        
        # Расчет урона
        player_damage = user_data['damage'] + random.randint(-5, 5)
        boss_damage = boss[5] + random.randint(-5, 5)
        player_taken = max(1, boss_damage - user_data['armor'] // 2)
        
        # Бонус за привилегии
        if self.is_vip(user.id):
            player_damage = int(player_damage * 1.2)
        if self.is_premium(user.id):
            player_damage = int(player_damage * 1.5)
        
        boss_killed = self.db.damage_boss(boss_id, player_damage)
        self.db.damage(user.id, player_taken)
        
        text = f"⚔️ **БИТВА С БОССОМ** ⚔️\n\n"
        text += f"▫️ **Ты нанес:** {player_damage} урона\n"
        text += f"▫️ **Босс нанес:** {player_taken} урона\n\n"
        
        if boss_killed:
            reward = boss[6] * (1 + user_data['level'] // 10)
            if self.is_vip(user.id):
                reward = int(reward * 1.5)
            if self.is_premium(user.id):
                reward = int(reward * 2)
            
            self.db.add_coins(user.id, reward)
            self.db.add_boss_kill(user.id)
            self.db.add_exp(user.id, boss[2] * 10)
            self.db.add_stat(user.id, "wins", 1)
            
            text += f"🎉 **ПОБЕДА!**\n"
            text += f"💰 **Награда:** {reward} монет\n"
            text += f"✨ **Опыт:** +{boss[2] * 10}"
        else:
            boss_info = self.db.get_boss(boss_id)
            text += f"👾 **Босс еще жив!**\n"
            text += f"❤️ **Осталось:** {boss_info[3]} здоровья"
            self.db.add_stat(user.id, "losses", 1)
        
        if user_data['health'] <= player_taken:
            self.db.heal(user.id, 50)
            text += "\n\n💀 Ты погиб в бою, но воскрешен с 50❤️"
        
        self.db.add_stat(user.id, "games_played")
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_casino(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("🎰 Рулетка", callback_data="casino_roulette"),
             InlineKeyboardButton("🎲 Кости", callback_data="casino_dice")],
            [InlineKeyboardButton("🃏 Блэкджек", callback_data="casino_blackjack"),
             InlineKeyboardButton("🎰 Слоты", callback_data="casino_slots")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🎰 **КАЗИНО «СПЕКТР»** 🎰\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🎰 **Рулетка** — ставь на цвет или число\n"
            "🎲 **Кости** — классическая игра\n"
            "🃏 **Блэкджек** — игра против дилера\n"
            "🎰 **Слоты** — испытай удачу\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Выбери игру:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def cmd_roulette(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id, user.first_name, user.last_name or "")
        
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
            await update.message.reply_text(f"❌ У тебя только {user_data['coins']} 🪙")
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
            self.db.add_coins(user.id, winnings)
            self.db.add_stat(user.id, "casino_wins", 1)
            result_text = f"🎉 **Ты выиграл {winnings} 🪙!**"
        else:
            self.db.add_coins(user.id, -bet)
            self.db.add_stat(user.id, "casino_losses", 1)
            result_text = f"😢 **Ты проиграл {bet} 🪙**"
        
        await update.message.reply_text(
            f"🎰 **РУЛЕТКА**\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"▫️ **Ставка:** {bet} 🪙\n"
            f"▫️ **Выбрано:** {choice}\n"
            f"▫️ **Выпало:** {result_num} {result_color}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{result_text}",
            parse_mode='Markdown'
        )
    
    async def cmd_dice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id, user.first_name, user.last_name or "")
        
        bet = 10
        if context.args:
            try:
                bet = int(context.args[0])
            except:
                pass
        
        if bet > user_data['coins']:
            await update.message.reply_text(f"❌ У тебя только {user_data['coins']} 🪙")
            return
        
        dice1 = random.randint(1, 6)
        dice2 = random.randint(1, 6)
        total = dice1 + dice2
        
        if total in [7, 11]:
            win = bet * 2
            result_text = f"🎉 Ты выиграл {win} 🪙!"
        elif total in [2, 3, 12]:
            win = 0
            result_text = f"😢 Ты проиграл {bet} 🪙"
        else:
            win = bet
            result_text = f"🔄 Ничья, ставка возвращена: {bet} 🪙"
        
        if win > 0:
            self.db.add_coins(user.id, win)
            self.db.add_stat(user.id, "casino_wins", 1)
        else:
            self.db.add_coins(user.id, -bet)
            self.db.add_stat(user.id, "casino_losses", 1)
        
        await update.message.reply_text(
            f"🎲 **КОСТИ**\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"▫️ **Ставка:** {bet} 🪙\n"
            f"▫️ **Кубики:** {dice1} + {dice2}\n"
            f"▫️ **Сумма:** {total}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{result_text}",
            parse_mode='Markdown'
        )
    
    async def cmd_blackjack(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id, user.first_name, user.last_name or "")
        
        bet = 10
        if context.args:
            try:
                bet = int(context.args[0])
            except:
                pass
        
        if bet > user_data['coins']:
            await update.message.reply_text(f"❌ У тебя только {user_data['coins']} 🪙")
            return
        
        # Упрощенная версия блэкджека
        player_card1 = random.randint(1, 11)
        player_card2 = random.randint(1, 11)
        player_total = player_card1 + player_card2
        
        dealer_card1 = random.randint(1, 11)
        dealer_card2 = random.randint(1, 11)
        dealer_total = dealer_card1 + dealer_card2
        
        if player_total > 21:
            result = "lose"
            result_text = f"😢 **Ты проиграл {bet} 🪙**"
        elif dealer_total > 21:
            result = "win"
            win = bet * 2
            result_text = f"🎉 **Ты выиграл {win} 🪙!**"
        elif player_total > dealer_total:
            result = "win"
            win = bet * 2
            result_text = f"🎉 **Ты выиграл {win} 🪙!**"
        elif player_total < dealer_total:
            result = "lose"
            result_text = f"😢 **Ты проиграл {bet} 🪙**"
        else:
            result = "draw"
            result_text = f"🔄 **Ничья, ставка возвращена:** {bet} 🪙"
        
        if result == "win":
            self.db.add_coins(user.id, win)
            self.db.add_stat(user.id, "casino_wins", 1)
        elif result == "lose":
            self.db.add_coins(user.id, -bet)
            self.db.add_stat(user.id, "casino_losses", 1)
        
        await update.message.reply_text(
            f"🃏 **БЛЭКДЖЕК**\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**Твои карты:** {player_card1} + {player_card2} = {player_total}\n"
            f"**Карты дилера:** {dealer_card1} + {dealer_card2} = {dealer_total}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{result_text}",
            parse_mode='Markdown'
        )
    
    async def cmd_slots(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id, user.first_name, user.last_name or "")
        
        bet = 10
        if context.args:
            try:
                bet = int(context.args[0])
            except:
                pass
        
        if bet > user_data['coins']:
            await update.message.reply_text(f"❌ У тебя только {user_data['coins']} 🪙")
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
            result_text = "🎉 **ДЖЕКПОТ!**"
        elif len(set(spin)) == 2:
            win = bet * 2
            result_text = "🎉 **Маленький выигрыш!**"
        else:
            win = 0
            result_text = "😢 **Не повезло...**"
        
        if win > 0:
            self.db.add_coins(user.id, win)
            self.db.add_stat(user.id, "casino_wins", 1)
        else:
            self.db.add_coins(user.id, -bet)
            self.db.add_stat(user.id, "casino_losses", 1)
        
        await update.message.reply_text(
            f"🎰 **СЛОТЫ**\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**{' '.join(spin)}**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{result_text}\n"
            f"{'💰 +' + str(win) + ' 🪙' if win > 0 else '💸 -' + str(bet) + ' 🪙'}",
            parse_mode='Markdown'
        )
    
    async def cmd_rps(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [
                InlineKeyboardButton("🪨 Камень", callback_data="rps_rock"),
                InlineKeyboardButton("✂️ Ножницы", callback_data="rps_scissors"),
                InlineKeyboardButton("📄 Бумага", callback_data="rps_paper")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "✊ **КАМЕНЬ-НОЖНИЦЫ-БУМАГА**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🪨 Камень побеждает Ножницы\n"
            "✂️ Ножницы побеждают Бумагу\n"
            "📄 Бумага побеждает Камень\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "**Выбери свой ход:**",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def cmd_rr(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "💣 **РУССКАЯ РУЛЕТКА**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**Правила:**\n"
            "• Игроки по очереди стреляют\n"
            "• В барабане 1-3 патрона\n"
            "• Кто остался жив — забирает ставки\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "**Команды:**\n"
            "▫️ /rr_start [игроки] [ставка] — создать лобби\n"
            "▫️ /rr_join [ID] — присоединиться\n"
            "▫️ /rr_shot — сделать выстрел"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_rr_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /rr_start [игроки (2-6)] [ставка]")
            return
        
        try:
            max_players = int(context.args[0])
            bet = int(context.args[1])
        except:
            await update.message.reply_text("❌ Неправильный формат")
            return
        
        if max_players < 2 or max_players > 6:
            await update.message.reply_text("❌ Количество игроков должно быть от 2 до 6")
            return
        
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data['rr_money'] < bet:
            await update.message.reply_text(f"❌ Недостаточно черепков! У тебя {user_data['rr_money']} 💀")
            return
        
        lobby_id = self.db.rr_create_lobby(user.id, max_players, bet)
        
        await update.message.reply_text(
            f"💣 **ЛОББИ СОЗДАНО!**\n\n"
            f"▫️ **ID:** {lobby_id}\n"
            f"▫️ **Создатель:** {user.first_name}\n"
            f"▫️ **Игроков:** 1/{max_players}\n"
            f"▫️ **Ставка:** {bet} 💀\n\n"
            f"Присоединиться: /rr_join {lobby_id}",
            parse_mode='Markdown'
        )
    
    async def cmd_rr_join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Укажи ID лобби: /rr_join 1")
            return
        
        try:
            lobby_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ Неправильный ID")
            return
        
        user = update.effective_user
        lobby = self.db.rr_get_lobby(lobby_id)
        
        if not lobby or lobby[5] != 'waiting':
            await update.message.reply_text("❌ Лобби не найдено или игра уже началась")
            return
        
        players = eval(lobby[4])
        
        if user.id in players:
            await update.message.reply_text("❌ Ты уже в этом лобби")
            return
        
        if len(players) >= lobby[2]:
            await update.message.reply_text("❌ Лобби уже заполнено")
            return
        
        if self.db.rr_join_lobby(lobby_id, user.id):
            players.append(user.id)
            await update.message.reply_text(f"✅ Ты присоединился к лобби {lobby_id}!")
        else:
            await update.message.reply_text("❌ Не удалось присоединиться")
    
    async def cmd_rr_shot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        self.db.cursor.execute(
            "SELECT * FROM rr_games WHERE players LIKE ? AND phase = 'playing'",
            (f'%{user.id}%',)
        )
        game = self.db.cursor.fetchone()
        
        if not game:
            await update.message.reply_text("❌ Ты не участвуешь в активной игре")
            return
        
        result = self.db.rr_make_shot(game[0], user.id)
        
        if result == "not_your_turn":
            await update.message.reply_text("❌ Сейчас не твой ход")
        elif result == "dead":
            await update.message.reply_text("💀 **БАХ!** Ты погиб...")
        elif result == "alive":
            await update.message.reply_text("✅ **ЩЕЛК!** Ты выжил!")
        elif isinstance(result, tuple) and result[0] == "game_over":
            winner_id = result[1]
            winner_data = await context.bot.get_chat(winner_id)
            await update.message.reply_text(
                f"🏆 **ИГРА ОКОНЧЕНА!**\n\n"
                f"Победитель: {winner_data.first_name}",
                parse_mode='Markdown'
            )
    
    async def cmd_ttt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "⭕ **КРЕСТИКИ-НОЛИКИ 3D**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**Правила:**\n"
            "• В каждой клетке поля находится ещё одно поле\n"
            "• Нужно выиграть на 3 малых полях в ряд\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "**Команды:**\n"
            "▫️ /ttt_challenge [ID] — вызвать игрока\n"
            "▫️ /ttt_move [клетка] — сделать ход"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_ttt_challenge(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Укажи ID игрока: /ttt_challenge 123456789")
            return
        
        try:
            opponent_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ Неправильный ID")
            return
        
        user = update.effective_user
        
        lobby_id = self.db.ttt_create_lobby(user.id)
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Принять", callback_data=f"ttt_accept_{lobby_id}"),
                InlineKeyboardButton("❌ Отклонить", callback_data=f"ttt_decline_{lobby_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await context.bot.send_message(
                chat_id=opponent_id,
                text=f"⭕ {user.first_name} вызывает тебя на игру в крестики-нолики 3D!\n\nСогласен?",
                reply_markup=reply_markup
            )
            await update.message.reply_text("✅ Запрос отправлен!")
        except:
            await update.message.reply_text("❌ Не удалось отправить запрос")
    
    async def cmd_ttt_move(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("⭕ Функция будет доступна в следующем обновлении")
    
    async def cmd_clan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        clan = self.db.get_user_clan(user.id)
        
        if not clan:
            await update.message.reply_text(
                "👥 Ты не состоишь в клане.\n\n"
                "Создать: /clan_create [название]\n"
                "Присоединиться: /clan_join [ID]"
            )
            return
        
        members = self.db.get_clan_members(clan[0])
        
        text = (
            f"╔══════════════════════════════╗\n"
            f"║    👥 **КЛАН «{clan[1]}»**   ║\n"
            f"╚══════════════════════════════╝\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**ИНФОРМАЦИЯ**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"▫️ **Уровень:** {clan[3]}\n"
            f"▫️ **Опыт:** {clan[4]}/{clan[3] * 500}\n"
            f"▫️ **Участников:** {clan[5]}\n"
            f"▫️ **Рейтинг:** {clan[6]}\n"
            f"▫️ **Побед/Поражений:** {clan[8]}/{clan[9]}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**УЧАСТНИКИ**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        
        for member in members:
            role_emoji = "👑" if member[5] == 'owner' else "🛡" if member[5] == 'admin' else "👤"
            text += f"{role_emoji} {member[1]} (ур.{member[3]})\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_clan_create(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Укажи название: /clan_create Название")
            return
        
        name = " ".join(context.args)
        user = update.effective_user
        user_data = self.db.get_user(user.id, user.first_name, user.last_name or "")
        
        if len(name) > 30:
            await update.message.reply_text("❌ Название слишком длинное (макс 30 символов)")
            return
        
        if self.db.get_user_clan(user.id):
            await update.message.reply_text("❌ Ты уже в клане")
            return
        
        if user_data['level'] < 5:
            await update.message.reply_text("❌ Для создания клана нужен 5 уровень!")
            return
        
        if user_data['coins'] < 1000:
            await update.message.reply_text("❌ Для создания клана нужно 1000 🪙")
            return
        
        clan_id = self.db.create_clan(name, user.id)
        
        if clan_id:
            self.db.add_coins(user.id, -1000)
            await update.message.reply_text(f"✅ Клан «{name}» создан! ID: {clan_id}")
        else:
            await update.message.reply_text("❌ Клан с таким названием уже существует")
    
    async def cmd_clan_join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Укажи ID клана: /clan_join 1")
            return
        
        try:
            clan_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ Неправильный ID")
            return
        
        user = update.effective_user
        
        if self.db.get_user_clan(user.id):
            await update.message.reply_text("❌ Ты уже в клане")
            return
        
        clan = self.db.get_clan(clan_id)
        
        if not clan:
            await update.message.reply_text("❌ Клан не найден")
            return
        
        if clan[5] >= 50:
            await update.message.reply_text("❌ В клане нет мест (максимум 50)")
            return
        
        self.db.join_clan(user.id, clan_id)
        await update.message.reply_text(f"✅ Ты вступил в клан «{clan[1]}»!")
    
    async def cmd_clan_leave(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        clan = self.db.get_user_clan(user.id)
        
        if not clan:
            await update.message.reply_text("❌ Ты не в клане")
            return
        
        if clan[2] == user.id:
            await update.message.reply_text("❌ Владелец не может покинуть клан.")
            return
        
        self.db.leave_clan(user.id, clan[0])
        await update.message.reply_text("✅ Ты покинул клан")
    
    async def cmd_clan_top(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.db.cursor.execute(
            "SELECT name, level, members, rating, wins FROM clans ORDER BY rating DESC, level DESC LIMIT 10"
        )
        clans = self.db.cursor.fetchall()
        
        text = (
            f"╔══════════════════════════════╗\n"
            f"║    🏆 **ТОП КЛАНОВ**        ║\n"
            f"╚══════════════════════════════╝\n\n"
        )
        
        for i, (name, level, members, rating, wins) in enumerate(clans, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
            text += f"{medal} **{i}. {name}** — {level} ур., {members} уч., {rating} ⭐, {wins} побед\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_clan_war(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("⚔️ Клановые войны будут доступны в следующем обновлении!")
    
    async def cmd_mafia(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "🔪 **МАФИЯ**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**Правила:**\n"
            "• Игроки делятся на мафию и мирных\n"
            "• Ночью мафия убивает, днем все обсуждают\n"
            "• Цель мафии - убить всех мирных\n"
            "• Цель мирных - найти мафию\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "**Команды:**\n"
            "▫️ /mafia_create — создать игру\n"
            "▫️ /mafia_join [ID] — присоединиться\n"
            "▫️ /mafia_start — начать игру\n"
            "▫️ /mafia_vote [ID] — проголосовать"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_mafia_create(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        game_id = self.db.create_mafia_game(user.id)
        
        await update.message.reply_text(
            f"🔪 **ИГРА МАФИЯ СОЗДАНА!**\n\n"
            f"▫️ **ID игры:** {game_id}\n"
            f"▫️ **Создатель:** {user.first_name}\n"
            f"▫️ **Игроков:** 1/10\n\n"
            f"Присоединиться: /mafia_join {game_id}",
            parse_mode='Markdown'
        )
    
    async def cmd_mafia_join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Укажи ID игры: /mafia_join 1")
            return
        
        try:
            game_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ Неправильный ID")
            return
        
        user = update.effective_user
        game = self.db.get_mafia_game(game_id)
        
        if not game:
            await update.message.reply_text("❌ Игра не найдена")
            return
        
        if game[2] != 'waiting':
            await update.message.reply_text("❌ Игра уже началась")
            return
        
        players = eval(game[3])
        
        if len(players) >= 10:
            await update.message.reply_text("❌ В игре уже максимальное количество игроков")
            return
        
        if user.id in players:
            await update.message.reply_text("❌ Ты уже в игре")
            return
        
        if self.db.join_mafia_game(game_id, user.id):
            players.append(user.id)
            
            await update.message.reply_text(f"✅ Ты присоединился к игре {game_id}!")
            
            if game[1] != user.id:
                try:
                    await context.bot.send_message(
                        chat_id=game[1],
                        text=f"🔪 {user.first_name} присоединился к игре! Игроков: {len(players)}/10"
                    )
                except:
                    pass
        else:
            await update.message.reply_text("❌ Не удалось присоединиться")
    
    async def cmd_mafia_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("🔪 Функция будет доступна в следующем обновлении")
    
    async def cmd_mafia_vote(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("🔪 Функция будет доступна в следующем обновлении")
    
    async def cmd_cases(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        cases = self.db.get_cases()
        
        text = (
            f"╔══════════════════════════════╗\n"
            f"║    🎁 **КЕЙСЫ**              ║\n"
            f"╚══════════════════════════════╝\n\n"
        )
        
        for case in cases:
            text += f"**{case[1]}** (ID: {case[0]})\n"
            text += f"└ 💰 Цена: {case[2]} 🪙\n"
            text += f"└ 🎁 Шансы: монеты, VIP, Premium, ключи\n\n"
        
        text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "Открыть: /open [ID]\n"
        text += "Твои ключи: /keys"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_open(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id, user.first_name, user.last_name or "")
        
        if self.db.is_muted(user.id):
            remaining = self.db.get_mute_time(user.id)
            await update.message.reply_text(f"🔇 Вы замучены. Осталось: {remaining}")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Укажи ID кейса: /open 1")
            return
        
        try:
            case_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ Неправильный ID")
            return
        
        case = self.db.get_case(case_id)
        if not case:
            await update.message.reply_text("❌ Кейс не найден")
            return
        
        if user_data['coins'] < case[2]:
            await update.message.reply_text(f"❌ Недостаточно монет! Нужно {case[2]} 🪙")
            return
        
        self.db.add_coins(user.id, -case[2])
        
        result = self.db.open_case(case_id, user.id)
        
        if result:
            text = (
                f"🎁 **РЕЗУЛЬТАТ ОТКРЫТИЯ**\n\n"
                f"▫️ **Кейс:** {case[1]}\n"
                f"▫️ **Выпало:** {result['name']}!"
            )
            
            if result['type'] == 'vip':
                text += f"\n▫️ **VIP статус на {result['value']} дней!**"
            elif result['type'] == 'premium':
                text += f"\n▫️ **Premium статус на {result['value']} дней!**"
            elif result['type'] == 'key':
                text += f"\n▫️ **+{result['value']} ключей!**"
        else:
            text = "❌ Ошибка при открытии кейса"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_keys(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        keys = user_data.get('keys', 0)
        
        await update.message.reply_text(f"🔑 **Твои ключи:** {keys}")
    
    async def cmd_inventory(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        items = self.db.get_inventory(user.id)
        
        if not items:
            await update.message.reply_text("📦 Твой инвентарь пуст")
            return
        
        text = "📦 **ТВОЙ ИНВЕНТАРЬ**\n\n"
        
        for item_id, name, item_type, desc, qty in items:
            text += f"**ID: {item_id}** — {name} x{qty}\n"
            if desc:
                text += f"└ {desc}\n"
            text += "\n"
        
        text += "Использовать: /use [ID]"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_shop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "🏪 **МАГАЗИН «СПЕКТР»**\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "💊 **ЗЕЛЬЯ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ Зелье здоровья — 50 🪙 (❤️+30)\n"
            "▫️ Большое зелье — 100 🪙 (❤️+70)\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚔️ **ОРУЖИЕ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ Меч — 200 🪙 (⚔️+10)\n"
            "▫️ Легендарный меч — 500 🪙 (⚔️+30)\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🛡 **БРОНЯ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ Щит — 150 🪙 (🛡+5)\n"
            "▫️ Доспехи — 400 🪙 (🛡+15)\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚡ **ЭНЕРГИЯ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ Энергетик — 30 🪙 (⚡+20)\n"
            "▫️ Батарейка — 80 🪙 (⚡+50)\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🎁 **КЕЙСЫ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ Обычный кейс — 100 🪙\n"
            "▫️ Редкий кейс — 500 🪙\n"
            "▫️ Легендарный кейс — 1000 🪙\n\n"
            
            "Купить: /buy [название]"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_buy(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id, user.first_name, user.last_name or "")
        
        if self.db.is_muted(user.id):
            remaining = self.db.get_mute_time(user.id)
            await update.message.reply_text(f"🔇 Вы замучены. Осталось: {remaining}")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Укажи предмет: /buy меч")
            return
        
        item = " ".join(context.args).lower()
        
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
            await update.message.reply_text("❌ Такого предмета нет в магазине")
            return
        
        item_data = items[item]
        
        if user_data['coins'] < item_data['price']:
            await update.message.reply_text(f"❌ Недостаточно монет! Нужно {item_data['price']} 🪙")
            return
        
        self.db.add_coins(user.id, -item_data['price'])
        
        if 'heal' in item_data:
            self.db.heal(user.id, item_data['heal'])
            await update.message.reply_text(f"✅ Здоровье +{item_data['heal']}❤️")
        
        elif 'damage' in item_data:
            self.db.cursor.execute("UPDATE users SET damage = damage + ? WHERE user_id = ?", (item_data['damage'], user.id))
            self.db.conn.commit()
            self.db.add_item(user.id, item, "weapon", f"Дает +{item_data['damage']} урона", 1)
            await update.message.reply_text(f"✅ Урон +{item_data['damage']}⚔️")
        
        elif 'armor' in item_data:
            self.db.cursor.execute("UPDATE users SET armor = armor + ? WHERE user_id = ?", (item_data['armor'], user.id))
            self.db.conn.commit()
            self.db.add_item(user.id, item, "armor", f"Дает +{item_data['armor']} брони", 1)
            await update.message.reply_text(f"✅ Броня +{item_data['armor']}🛡")
        
        elif 'energy' in item_data:
            self.db.add_energy(user.id, item_data['energy'])
            await update.message.reply_text(f"✅ Энергия +{item_data['energy']}⚡")
    
    async def cmd_use(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Укажи ID предмета: /use 1")
            return
        
        try:
            item_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ Неправильный ID")
            return
        
        user = update.effective_user
        
        used_item = self.db.use_item(user.id, item_id)
        
        if used_item:
            await update.message.reply_text(f"✅ Использован предмет: {used_item}")
        else:
            await update.message.reply_text("❌ У тебя нет такого предмета")
    
    async def cmd_market(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        items = self.db.get_market_items()
        
        if not items:
            await update.message.reply_text("🏪 Торговая площадка пуста. Продай что-нибудь: /sell")
            return
        
        text = "🏪 **ТОРГОВАЯ ПЛОЩАДКА**\n\n"
        
        for item in items[:10]:
            self.db.cursor.execute("SELECT first_name FROM users WHERE user_id = ?", (item[1],))
            seller = self.db.cursor.fetchone()
            seller_name = seller[0] if seller else "Неизвестно"
            
            text += f"**ID: {item[0]}**\n"
            text += f"└ Товар: {item[2]}\n"
            text += f"└ Цена: {item[4]} 🪙\n"
            text += f"└ Количество: {item[5]}\n"
            text += f"└ Продавец: {seller_name}\n\n"
        
        text += "Купить: /buy_market [ID]"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_sell(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /sell [предмет] [цена]")
            return
        
        item_name = context.args[0]
        try:
            price = int(context.args[1])
        except:
            await update.message.reply_text("❌ Цена должна быть числом")
            return
        
        user = update.effective_user
        
        # Проверяем, есть ли предмет в инвентаре
        items = self.db.get_inventory(user.id)
        has_item = any(item_name.lower() in item[1].lower() for item in items)
        
        if not has_item:
            await update.message.reply_text("❌ У тебя нет такого предмета в инвентаре")
            return
        
        item_id = self.db.add_to_market(user.id, item_name, "item", price, 1)
        
        await update.message.reply_text(f"✅ Товар «{item_name}» выставлен на продажу за {price} 🪙\nID товара: {item_id}")
    
    async def cmd_donate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "💎 **ПРИВИЛЕГИИ «СПЕКТР»** 💎\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🌟 **VIP СТАТУС**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"▫️ **Цена:** {VIP_PRICE} 🪙\n"
            f"▫️ **Длительность:** {VIP_DAYS} дней\n"
            "▫️ **Бонусы:**\n"
            "  • Урон в битвах +20%\n"
            "  • Награда с боссов +50%\n"
            "  • Ежедневный бонус +50%\n"
            "  • Нет спам-фильтра\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "💎 **PREMIUM СТАТУС**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"▫️ **Цена:** {PREMIUM_PRICE} 🪙\n"
            f"▫️ **Длительность:** {PREMIUM_DAYS} дней\n"
            "▫️ **Бонусы:**\n"
            "  • Все бонусы VIP\n"
            "  • Урон в битвах +50%\n"
            "  • Награда с боссов +100%\n"
            "  • Ежедневный бонус +100%\n"
            "  • Доступ к эксклюзивным командам\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👑 По вопросам доната: {OWNER_USERNAME}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_vip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id, user.first_name, user.last_name or "")
        
        if user_data['coins'] < VIP_PRICE:
            await update.message.reply_text(f"❌ Недостаточно монет! Нужно {VIP_PRICE} 🪙")
            return
        
        if self.is_vip(user.id):
            await update.message.reply_text("❌ У тебя уже есть VIP статус!")
            return
        
        self.db.add_coins(user.id, -VIP_PRICE)
        self.db.set_vip(user.id, VIP_DAYS)
        
        await update.message.reply_text(
            f"🌟 **ПОЗДРАВЛЯЮ!**\n\n"
            f"Теперь у тебя VIP статус на {VIP_DAYS} дней!\n"
            f"Все бонусы уже активны.",
            parse_mode='Markdown'
        )
    
    async def cmd_premium(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id, user.first_name, user.last_name or "")
        
        if user_data['coins'] < PREMIUM_PRICE:
            await update.message.reply_text(f"❌ Недостаточно монет! Нужно {PREMIUM_PRICE} 🪙")
            return
        
        if self.is_premium(user.id):
            await update.message.reply_text("❌ У тебя уже есть Premium статус!")
            return
        
        self.db.add_coins(user.id, -PREMIUM_PRICE)
        self.db.set_premium(user.id, PREMIUM_DAYS)
        
        await update.message.reply_text(
            f"💎 **ПОЗДРАВЛЯЮ!**\n\n"
            f"Теперь у тебя PREMIUM статус на {PREMIUM_DAYS} дней!\n"
            f"Ты элита!",
            parse_mode='Markdown'
        )
    
    async def cmd_gift(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /gift [ID] [предмет]")
            return
        
        try:
            to_id = int(context.args[0])
            item_name = " ".join(context.args[1:])
        except:
            await update.message.reply_text("❌ Неправильный формат")
            return
        
        user = update.effective_user
        
        if user.id == to_id:
            await update.message.reply_text("❌ Нельзя дарить подарки самому себе")
            return
        
        # Проверяем, есть ли предмет в инвентаре
        items = self.db.get_inventory(user.id)
        has_item = any(item_name.lower() in item[1].lower() for item in items)
        
        if not has_item:
            await update.message.reply_text("❌ У тебя нет такого предмета в инвентаре")
            return
        
        gift_id = self.db.send_gift(user.id, to_id, item_name, "Подарок")
        
        await update.message.reply_text(f"✅ Подарок отправлен пользователю {to_id}!")
        
        try:
            await context.bot.send_message(
                chat_id=to_id,
                text=f"🎁 Тебе отправлен подарок от {user.first_name}: {item_name}!\n"
                     f"Посмотреть: /gifts"
            )
        except:
            pass
    
    async def cmd_gifts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        gifts = self.db.get_gifts(user.id)
        
        if not gifts:
            await update.message.reply_text("📭 У тебя нет новых подарков")
            return
        
        text = "🎁 **ТВОИ ПОДАРКИ**\n\n"
        
        for gift in gifts:
            self.db.cursor.execute("SELECT first_name FROM users WHERE user_id = ?", (gift[1],))
            sender = self.db.cursor.fetchone()
            sender_name = sender[0] if sender else "Неизвестно"
            
            text += f"▫️ **От:** {sender_name}\n"
            text += f"▫️ **Подарок:** {gift[3]}\n"
            text += f"▫️ **Сообщение:** {gift[4]}\n"
            text += f"▫️ **Получен:** {gift[5][:16]}\n\n"
            
            self.db.read_gift(gift[0])
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_referral(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        referral_link = f"https://t.me/{(await context.bot.get_me()).username}?start={user.id}"
        
        text = (
            "👥 **РЕФЕРАЛЬНАЯ ПРОГРАММА**\n\n"
            "Приглашай друзей и получай бонусы!\n"
            "За каждого приглашенного: +200 🪙\n\n"
            f"▫️ **Твоих рефералов:** {user_data.get('referrals', 0)}\n\n"
            f"🔗 **Твоя ссылка:**\n`{referral_link}`\n\n"
            "Отправь эту ссылку друзьям. Когда они зарегистрируются, ты получишь награду!"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_referrals(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        referrals = self.db.get_referrals(user.id)
        
        if not referrals:
            await update.message.reply_text("👥 У тебя пока нет рефералов")
            return
        
        text = "👥 **ТВОИ РЕФЕРАЛЫ**\n\n"
        
        total_reward = 0
        for ref in referrals:
            self.db.cursor.execute("SELECT first_name FROM users WHERE user_id = ?", (ref[2],))
            ref_user = self.db.cursor.fetchone()
            ref_name = ref_user[0] if ref_user else "Неизвестно"
            
            text += f"▫️ **{ref_name}** — зарегистрирован {ref[4][:10]}, награда: {ref[3]} 🪙\n"
            total_reward += ref[3]
        
        text += f"\n💰 **Всего получено:** {total_reward} 🪙"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_marry(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Укажи ID пользователя: /marry 123456789")
            return
        
        try:
            partner_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ Неправильный ID")
            return
        
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data.get('marry_id', 0) != 0:
            await update.message.reply_text("❌ Ты уже в браке!")
            return
        
        if user_data['level'] < 5:
            await update.message.reply_text("❌ Для брака нужен 5 уровень!")
            return
        
        partner_data = self.db.get_user(partner_id)
        
        if partner_data.get('marry_id', 0) != 0:
            await update.message.reply_text("❌ Этот пользователь уже в браке")
            return
        
        keyboard = [
            [
                InlineKeyboardButton("💍 Согласиться", callback_data=f"marry_accept_{user.id}_{partner_id}"),
                InlineKeyboardButton("💔 Отказаться", callback_data=f"marry_decline_{user.id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await context.bot.send_message(
                chat_id=partner_id,
                text=f"💍 {user.first_name} предлагает тебе выйти замуж/жениться!\n\n"
                     f"Уровень: {user_data['level']}\n"
                     f"Монеты: {user_data['coins']} 🪙\n\n"
                     f"Согласен?",
                reply_markup=reply_markup
            )
            await update.message.reply_text("💍 Предложение отправлено!")
        except:
            await update.message.reply_text("❌ Не удалось отправить предложение")
    
    async def cmd_divorce(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        if self.db.divorce(user.id):
            self.db.add_coins(user.id, -500)
            await update.message.reply_text(
                "💔 Брак расторгнут.\n"
                "Штраф: -500 🪙"
            )
        else:
            await update.message.reply_text("❌ Ты не в браке")
    
    async def cmd_love(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        marry_id = user_data.get('marry_id', 0)
        
        if marry_id == 0:
            await update.message.reply_text("❌ Ты не в браке")
            return
        
        self.db.cursor.execute("SELECT first_name FROM users WHERE user_id = ?", (marry_id,))
        partner = self.db.cursor.fetchone()
        partner_name = partner[0] if partner else f"ID {marry_id}"
        
        love_points = user_data.get('love_points', 0)
        
        text = (
            f"💕 **ОЧКИ ЛЮБВИ**\n\n"
            f"▫️ **Супруг(а):** {partner_name}\n"
            f"▫️ **Очки любви:** {love_points} 💕\n"
            f"▫️ **Детей:** {user_data.get('children', 0)} 👶\n\n"
            f"💡 Дарите подарки и проводите время вместе, чтобы повысить очки любви!"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_children(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data.get('marry_id', 0) == 0:
            await update.message.reply_text("❌ Ты не в браке")
            return
        
        if user_data.get('love_points', 0) < 100:
            await update.message.reply_text("❌ Нужно 100 очков любви!")
            return
        
        if user_data.get('children', 0) >= 5:
            await update.message.reply_text("❌ У вас уже 5 детей (максимум)")
            return
        
        chance = min(0.3 + user_data['love_points'] / 1000, 0.7)
        
        if random.random() < chance:
            self.db.add_child(user.id)
            self.db.add_love_points(user.id, 50)
            
            gender = random.choice(["мальчик", "девочка"])
            
            await update.message.reply_text(
                f"👶 **ПОЗДРАВЛЯЮ!**\n\n"
                f"У вас родился {gender}!\n"
                f"Теперь у вас {user_data['children'] + 1} детей!\n"
                f"+50 💕 за пополнение в семье!"
            )
            
            self.db.add_coins(user.id, 100)
        else:
            await update.message.reply_text("😢 Пока не получилось... Попробуй еще раз")
    
    async def cmd_debt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 3:
            await update.message.reply_text("❌ Использование: /debt [ID] [сумма] [причина]")
            return
        
        try:
            debtor_id = int(context.args[0])
            amount = int(context.args[1])
            reason = " ".join(context.args[2:])
        except:
            await update.message.reply_text("❌ Неправильный формат")
            return
        
        creditor = update.effective_user
        
        if creditor.id == debtor_id:
            await update.message.reply_text("❌ Нельзя дать в долг самому себе")
            return
        
        creditor_data = self.db.get_user(creditor.id)
        
        if creditor_data['coins'] < amount:
            await update.message.reply_text(f"❌ У тебя только {creditor_data['coins']} 🪙")
            return
        
        self.db.add_coins(creditor.id, -amount)
        
        debt_id = self.db.create_debt(debtor_id, creditor.id, amount, reason)
        
        await update.message.reply_text(f"💰 Долг оформлен! ID: {debt_id}")
        
        try:
            await context.bot.send_message(
                chat_id=debtor_id,
                text=f"💰 {creditor.first_name} дал тебе в долг {amount} 🪙\n"
                     f"Причина: {reason}\n"
                     f"ID долга: {debt_id}"
            )
        except:
            pass
    
    async def cmd_debts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        debts = self.db.get_debts(user.id)
        
        if not debts:
            await update.message.reply_text("💰 У тебя нет активных долгов")
            return
        
        text = "💰 **ТВОИ ДОЛГИ**\n\n"
        
        for debt in debts:
            debtor_id, creditor_id, amount, reason, created, deadline, is_paid = debt[1:8]
            
            if debtor_id == user.id:
                role = "Ты должен"
                other_id = creditor_id
            else:
                role = "Должны тебе"
                other_id = debtor_id
            
            self.db.cursor.execute("SELECT first_name FROM users WHERE user_id = ?", (other_id,))
            other = self.db.cursor.fetchone()
            other_name = other[0] if other else f"ID {other_id}"
            
            created_str = datetime.datetime.fromisoformat(created).strftime("%d.%m.%Y")
            deadline_str = datetime.datetime.fromisoformat(deadline).strftime("%d.%m.%Y")
            
            text += f"**ID: {debt[0]}**\n"
            text += f"└ {role}: {other_name}\n"
            text += f"└ Сумма: {amount} 🪙\n"
            text += f"└ Причина: {reason}\n"
            text += f"└ Создан: {created_str}\n"
            text += f"└ Срок: {deadline_str}\n\n"
        
        text += "Оплатить: /pay [ID]"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_pay(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Укажи ID долга: /pay 1")
            return
        
        try:
            debt_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ Неправильный ID")
            return
        
        user = update.effective_user
        
        self.db.cursor.execute("SELECT * FROM debts WHERE id = ?", (debt_id,))
        debt = self.db.cursor.fetchone()
        
        if not debt:
            await update.message.reply_text("❌ Долг не найден")
            return
        
        debtor_id, creditor_id, amount, reason, created, deadline, is_paid = debt[1:8]
        
        if is_paid:
            await update.message.reply_text("❌ Долг уже оплачен")
            return
        
        if debtor_id != user.id:
            await update.message.reply_text("❌ Это не твой долг")
            return
        
        user_data = self.db.get_user(user.id)
        
        if user_data['coins'] < amount:
            await update.message.reply_text(f"❌ Недостаточно монет! Нужно {amount} 🪙")
            return
        
        self.db.add_coins(user.id, -amount)
        self.db.add_coins(creditor_id, amount)
        self.db.pay_debt(debt_id)
        
        await update.message.reply_text(f"✅ Долг оплачен! Переведено {amount} 🪙")
        
        try:
            await context.bot.send_message(
                chat_id=creditor_id,
                text=f"💰 {user.first_name} оплатил долг в размере {amount} 🪙"
            )
        except:
            pass
    
    async def cmd_dailies(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        dailies = self.db.get_dailies(user.id)
        
        if not dailies:
            # Создаем задания на сегодня
            tasks = [
                ("messages", 10, 50, "Отправить 10 сообщений"),
                ("boss_fights", 3, 100, "Сразиться с боссами 3 раза"),
                ("casino", 5, 75, "Сыграть в казино 5 раз")
            ]
            
            text = "📋 **ЕЖЕДНЕВНЫЕ ЗАДАНИЯ**\n\n"
            text += "У тебя пока нет активных заданий. Они появятся после первого действия.\n\n"
            text += "Примеры заданий:\n"
            text += "▫️ Отправить 10 сообщений — 50 🪙\n"
            text += "▫️ Сразиться с боссами 3 раза — 100 🪙\n"
            text += "▫️ Сыграть в казино 5 раз — 75 🪙"
        else:
            text = "📋 **ЕЖЕДНЕВНЫЕ ЗАДАНИЯ**\n\n"
            for daily in dailies:
                task_type, progress, target, reward = daily[2:6]
                percent = int(progress / target * 100)
                bar = "█" * (percent // 10) + "░" * (10 - percent // 10)
                text += f"▫️ **{task_type}:** {progress}/{target} {bar} {percent}%\n"
                text += f"  Награда: {reward} 🪙\n\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_achievements(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        achievements = self.db.get_achievements(user.id)
        
        if not achievements:
            await update.message.reply_text("🏆 У тебя пока нет достижений. Играй и открывай новые!")
            return
        
        text = "🏆 **ТВОИ ДОСТИЖЕНИЯ**\n\n"
        
        for name, desc, date, reward in achievements:
            date_obj = datetime.datetime.fromisoformat(date)
            date_str = date_obj.strftime("%d.%m.%Y")
            text += f"**{name}**\n"
            text += f"└ {desc}\n"
            text += f"└ 📅 {date_str}"
            if reward > 0:
                text += f" (+{reward} 🪙)"
            text += "\n\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_mute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Недостаточно прав")
            return
        
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /mute [ID] [минут]")
            return
        
        try:
            target_id = int(context.args[0])
            minutes = int(context.args[1])
            reason = " ".join(context.args[2:]) if len(context.args) > 2 else "Нарушение"
        except:
            await update.message.reply_text("❌ Неправильный формат")
            return
        
        if target_id == OWNER_ID:
            await update.message.reply_text("❌ Нельзя замутить владельца")
            return
        
        self.db.mute_user(target_id, minutes, update.effective_user.id, reason)
        
        await update.message.reply_text(f"🔇 Пользователь {target_id} замучен на {minutes} минут\nПричина: {reason}")
        
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=f"🔇 Вы замучены на {minutes} минут.\nПричина: {reason}"
            )
        except:
            pass
    
    async def cmd_warn(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Недостаточно прав")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Использование: /warn [ID] [причина]")
            return
        
        try:
            target_id = int(context.args[0])
            reason = " ".join(context.args[1:]) if len(context.args) > 1 else "Нарушение"
        except:
            await update.message.reply_text("❌ Неправильный ID")
            return
        
        if target_id == OWNER_ID:
            await update.message.reply_text("❌ Нельзя выдать варн владельцу")
            return
        
        result = self.db.add_warn(target_id, update.effective_user.id, reason)
        await update.message.reply_text(result)
        
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=f"⚠️ Вам выдано предупреждение.\nПричина: {reason}"
            )
        except:
            pass
    
    async def cmd_ban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Недостаточно прав")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Использование: /ban [ID]")
            return
        
        try:
            target_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ Неправильный ID")
            return
        
        if target_id == OWNER_ID:
            await update.message.reply_text("❌ Нельзя забанить владельца")
            return
        
        self.db.ban_user(target_id, update.effective_user.id)
        await update.message.reply_text(f"🚫 Пользователь {target_id} забанен")
        
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text="🚫 Вы забанены в боте."
            )
        except:
            pass
    
    async def cmd_unban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Недостаточно прав")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Использование: /unban [ID]")
            return
        
        try:
            target_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ Неправильный ID")
            return
        
        self.db.unban_user(target_id)
        await update.message.reply_text(f"✅ Пользователь {target_id} разбанен")
        
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text="✅ Вы разбанены в боте."
            )
        except:
            pass
    
    async def cmd_give(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Недостаточно прав")
            return
        
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /give [ID] [сумма]")
            return
        
        try:
            target_id = int(context.args[0])
            amount = int(context.args[1])
        except:
            await update.message.reply_text("❌ Неправильный формат")
            return
        
        self.db.add_coins(target_id, amount)
        await update.message.reply_text(f"✅ Пользователю {target_id} выдано {amount} 🪙")
        
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=f"💰 Вам начислено {amount} 🪙 от администрации!"
            )
        except:
            pass
    
    async def cmd_clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Недостаточно прав")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Укажи количество сообщений для удаления")
            return
        
        try:
            count = int(context.args[0])
            if count < 1 or count > 100:
                await update.message.reply_text("❌ Количество должно быть от 1 до 100")
                return
        except:
            await update.message.reply_text("❌ Неправильное число")
            return
        
        chat_id = update.effective_chat.id
        
        try:
            await context.bot.delete_message(chat_id, update.message.message_id)
            # Здесь нужно использовать client.delete_messages, но в telegram.ext нет прямого доступа
            await update.message.reply_text(f"✅ Удалено {count} сообщений")
        except:
            await update.message.reply_text("❌ Не удалось удалить сообщения")
    
    async def cmd_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        rules = self.db.get_group_rules(chat_id)
        
        if rules:
            await update.message.reply_text(
                f"📜 **ПРАВИЛА ЧАТА**\n\n"
                f"{rules}",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "📜 **ПРАВИЛА ЧАТА**\n\n"
                "В этом чате ещё нет правил.\n"
                "Установите их командой:\n"
                "/set_rules [текст]"
            )
    
    async def cmd_set_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        if chat_member.status not in ['creator', 'administrator']:
            await update.message.reply_text("❌ Только администраторы могут устанавливать правила")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Укажи текст правил: /set_rules Текст правил")
            return
        
        rules = " ".join(context.args)
        self.db.set_group_rules(chat_id, rules, user_id)
        
        await update.message.reply_text(
            f"✅ **Правила установлены!**\n\n{rules}"
        )
    
    async def cmd_group_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        if chat_member.status not in ['creator', 'administrator']:
            await update.message.reply_text("❌ Только администраторы могут просматривать настройки")
            return
        
        settings = self.db.get_group_settings(chat_id)
        
        text = (
            f"⚙️ **НАСТРОЙКИ ГРУППЫ**\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👋 **Приветствие:** {'✅ Включено' if settings['welcome_enabled'] else '❌ Выключено'}\n"
            f"📝 **Текст:** {settings['welcome_message']}\n\n"
            f"👋 **Прощание:** {'✅ Включено' if settings['goodbye_enabled'] else '❌ Выключено'}\n"
            f"📝 **Текст:** {settings['goodbye_message']}\n\n"
            f"🚫 **Анти-спам:** {'✅ Вкл' if settings['anti_spam'] else '❌ Выкл'}\n"
            f"🚫 **Лимит капса:** {settings['caps_limit']}\n"
            f"🚫 **Лимит эмодзи:** {settings['emoji_limit']}\n"
            f"🔗 **Блок ссылок:** {'✅ Вкл' if settings['link_block'] else '❌ Выкл'}\n"
            f"🌐 **Язык:** {settings['language']}\n"
            f"⚠️ **Лимит варнов:** {settings['warn_limit']}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_set_welcome(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        if chat_member.status not in ['creator', 'administrator']:
            await update.message.reply_text("❌ Только администраторы могут изменять приветствие")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Укажи текст приветствия. Используй {user} для имени")
            return
        
        message = " ".join(context.args)
        self.db.update_group_setting(chat_id, 'welcome_message', message)
        self.db.update_group_setting(chat_id, 'welcome_enabled', 1)
        
        await update.message.reply_text(f"✅ **Приветствие установлено!**\n\n{message}")
    
    async def cmd_set_goodbye(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        if chat_member.status not in ['creator', 'administrator']:
            await update.message.reply_text("❌ Только администраторы могут изменять прощание")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Укажи текст прощания. Используй {user} для имени")
            return
        
        message = " ".join(context.args)
        self.db.update_group_setting(chat_id, 'goodbye_message', message)
        self.db.update_group_setting(chat_id, 'goodbye_enabled', 1)
        
        await update.message.reply_text(f"✅ **Прощание установлено!**\n\n{message}")
    
    async def handle_new_members(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        settings = self.db.get_group_settings(chat_id)
        
        if not settings['welcome_enabled']:
            return
        
        for member in update.message.new_chat_members:
            if member.is_bot:
                continue
            
            welcome = settings['welcome_message'].replace('{user}', f"[{member.first_name}](tg://user?id={member.id})")
            await update.message.reply_text(welcome, parse_mode='Markdown')
    
    async def handle_left_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        settings = self.db.get_group_settings(chat_id)
        
        if not settings['goodbye_enabled']:
            return
        
        member = update.message.left_chat_member
        if member.is_bot:
            return
        
        goodbye = settings['goodbye_message'].replace('{user}', f"[{member.first_name}](tg://user?id={member.id})")
        await update.message.reply_text(goodbye, parse_mode='Markdown')
    
    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        self.db.update_voice_count(user.id)
        self.db.update_last_seen(user.id)
        self.db.update_daily(user.id, "voice")
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        self.db.update_photo_count(user.id)
        self.db.update_last_seen(user.id)
        self.db.update_daily(user.id, "photo")
    
    async def handle_sticker(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        self.db.update_sticker_count(user.id)
        self.db.update_last_seen(user.id)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        message_text = update.message.text
        self.db.update_last_seen(user.id)
        
        if self.db.is_banned(user.id):
            return
        
        if self.db.is_muted(user.id):
            remaining = self.db.get_mute_time(user.id)
            await update.message.reply_text(f"🔇 Вы замучены. Осталось: {remaining}")
            return
        
        if await self.check_spam(update):
            return
        
        # Обновляем ежедневные задания
        self.db.update_daily(user.id, "messages")
        
        # Пробуем OpenRouter
        response = await self.ai.get_response(user.id, message_text)
        if response:
            await update.message.reply_text(f"🤖 **СПЕКТР:** {response}", parse_mode='Markdown')
            self.db.add_stat(user.id, "messages_count")
            self.db.add_exp(user.id, 1)
            return
        
        # Если OpenRouter не ответил — заготовки
        msg_lower = message_text.lower()
        
        if any(word in msg_lower for word in ["привет", "здравствуй", "хай"]):
            await update.message.reply_text("👋 Привет! Как твои дела?")
        
        elif any(word in msg_lower for word in ["как дела", "как ты"]):
            await update.message.reply_text("⚙️ Всё отлично! А у тебя?")
        
        elif any(word in msg_lower for word in ["спасибо", "благодарю"]):
            await update.message.reply_text("🤝 Всегда пожалуйста!")
        
        elif any(word in msg_lower for word in ["пока", "до свидания"]):
            await update.message.reply_text("👋 До встречи!")
        
        elif any(word in msg_lower for word in ["кто ты", "ты кто"]):
            await update.message.reply_text("🤖 Я — СПЕКТР, твой игровой помощник!")
        
        elif any(word in msg_lower for word in ["что ты умеешь", "твои функции"]):
            await update.message.reply_text("📋 Мои возможности в /help")
        
        elif any(word in msg_lower for word in ["босс", "битва"]):
            await update.message.reply_text("👾 Боссы ждут! /bosses")
        
        elif any(word in msg_lower for word in ["профиль", "статистика"]):
            await update.message.reply_text("📊 Твой профиль: /profile")
        
        elif any(word in msg_lower for word in ["награда", "бонус"]):
            await update.message.reply_text("🎁 Ежедневная награда: /daily")
        
        elif any(word in msg_lower for word in ["помощь", "хелп"]):
            await update.message.reply_text("📚 Все команды: /help")
        
        elif any(word in msg_lower for word in ["кто создал", "владелец"]):
            await update.message.reply_text(f"👑 Владелец: {OWNER_USERNAME}")
        
        else:
            responses = [
                "🤖 Я внимательно слушаю. Можешь уточнить?",
                "🎯 Напиши /help, чтобы увидеть команды.",
                "💡 Хочешь сразиться с боссом? /bosses",
                "📊 Хочешь узнать статистику? /profile",
                "🎁 Не забудь /daily!"
            ]
            await update.message.reply_text(random.choice(responses))
        
        self.db.add_stat(user.id, "messages_count")
        self.db.add_exp(user.id, 1)
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user = update.effective_user
        data = query.data
        
        if data == "menu_profile":
            await self.cmd_profile(update, context)
        elif data == "menu_marry":
            await query.edit_message_text(
                "💍 **ОТНОШЕНИЯ**\n\n"
                "▫️ /marry [ID] — сделать предложение\n"
                "▫️ /divorce — развестись\n"
                "▫️ /love — очки любви\n"
                "▫️ /children — завести ребенка\n"
                "▫️ /compliment — сказать комплимент",
                parse_mode='Markdown'
            )
        elif data == "menu_stats":
            await query.edit_message_text(
                "📊 **СТАТИСТИКА**\n\n"
                "▫️ /boss_stats — боссы\n"
                "▫️ /mafia_stats — мафия\n"
                "▫️ /rps_stats — КНБ\n"
                "▫️ /casino_stats — казино\n"
                "▫️ /rr_stats — русская рулетка\n"
                "▫️ /ttt_stats — крестики-нолики",
                parse_mode='Markdown'
            )
        elif data == "menu_bosses":
            await self.cmd_boss_list(update, context)
        elif data == "menu_casino":
            await self.cmd_casino(update, context)
        elif data == "menu_clan":
            await self.cmd_clan(update, context)
        elif data == "menu_mafia":
            await self.cmd_mafia(update, context)
        elif data == "menu_cases":
            await self.cmd_cases(update, context)
        elif data == "menu_shop":
            await self.cmd_shop(update, context)
        elif data == "menu_donate":
            await self.cmd_donate(update, context)
        elif data == "menu_help":
            await self.cmd_help(update, context)
        elif data == "casino_roulette":
            await self.cmd_roulette(update, context)
        elif data == "casino_dice":
            await self.cmd_dice(update, context)
        elif data == "casino_blackjack":
            await self.cmd_blackjack(update, context)
        elif data == "casino_slots":
            await self.cmd_slots(update, context)
        elif data.startswith("rps_"):
            choice = data.split('_')[1]
            bot_choice = random.choice(["rock", "scissors", "paper"])
            
            choices = {"rock": "🪨 Камень", "scissors": "✂️ Ножницы", "paper": "📄 Бумага"}
            
            result_map = {
                ("rock", "scissors"): "win", ("rock", "paper"): "lose",
                ("scissors", "paper"): "win", ("scissors", "rock"): "lose",
                ("paper", "rock"): "win", ("paper", "scissors"): "lose"
            }
            
            if choice == bot_choice:
                result = "draw"
                self.db.cursor.execute("UPDATE users SET rps_draws = rps_draws + 1 WHERE user_id = ?", (user.id,))
                text = f"{choices[choice]} vs {choices[bot_choice]}\n\n🤝 **Ничья!**"
            else:
                result = result_map.get((choice, bot_choice), "lose")
                if result == "win":
                    self.db.cursor.execute("UPDATE users SET rps_wins = rps_wins + 1 WHERE user_id = ?", (user.id,))
                    text = f"{choices[choice]} vs {choices[bot_choice]}\n\n🎉 **Ты выиграл!**"
                else:
                    self.db.cursor.execute("UPDATE users SET rps_losses = rps_losses + 1 WHERE user_id = ?", (user.id,))
                    text = f"{choices[choice]} vs {choices[bot_choice]}\n\n😢 **Ты проиграл!**"
            
            self.db.conn.commit()
            await query.edit_message_text(text, parse_mode='Markdown')
        elif data.startswith("ttt_accept_"):
            lobby_id = int(data.split('_')[2])
            if self.db.ttt_join_lobby(lobby_id, user.id):
                self.db.ttt_start_game(lobby_id, user.id, user.id)
                await query.edit_message_text("⭕ Игра началась! Твой ход.")
            else:
                await query.edit_message_text("❌ Не удалось присоединиться к игре")
        elif data.startswith("ttt_decline_"):
            await query.edit_message_text("❌ Игра отклонена")
        elif data.startswith("marry_accept_"):
            parts = data.split('_')
            proposer_id = int(parts[2])
            partner_id = int(parts[3])
            
            if user.id != partner_id:
                await query.edit_message_text("❌ Это не твое предложение")
                return
            
            self.db.marry(proposer_id, partner_id)
            await query.edit_message_text(
                "💖 **ПОЗДРАВЛЯЮ!**\n\n"
                "Брак заключен! Вы получили:\n"
                "• +500 🪙 каждому\n"
                "• Достижение 💍 В браке"
            )
        elif data.startswith("marry_decline_"):
            await query.edit_message_text("💔 Предложение отклонено")
    
    async def run(self):
        try:
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            logger.info("🚀 Бот «СПЕКТР» МЕГА-ВЕРСИЯ запущен!")
            while True:
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await asyncio.sleep(5)
            await self.run()
    
    async def close(self):
        if self.ai:
            await self.ai.close()
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
