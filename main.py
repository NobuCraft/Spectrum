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

# DeepSeek API
DEEPSEEK_KEY = "sk-97ac1d0de1844c449852a5470cbcae35"
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

# Настройки
SPAM_LIMIT = 5
SPAM_WINDOW = 3
SPAM_MUTE_TIME = 120

# Цены на привилегии
VIP_PRICE = 5000
PREMIUM_PRICE = 15000
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
            
            if 'role' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
            if 'warns' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN warns INTEGER DEFAULT 0")
            if 'mute_until' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN mute_until TIMESTAMP")
            if 'banned' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN banned INTEGER DEFAULT 0")
            if 'health' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN health INTEGER DEFAULT 100")
            if 'armor' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN armor INTEGER DEFAULT 0")
            if 'damage' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN damage INTEGER DEFAULT 10")
            if 'boss_kills' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN boss_kills INTEGER DEFAULT 0")
            if 'vip_until' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN vip_until TIMESTAMP")
            if 'premium_until' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN premium_until TIMESTAMP")
            if 'clan_id' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN clan_id INTEGER DEFAULT 0")
            if 'clan_role' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN clan_role TEXT DEFAULT 'member'")
            if 'mafia_wins' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN mafia_wins INTEGER DEFAULT 0")
            if 'mafia_games' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN mafia_games INTEGER DEFAULT 0")
            if 'mafia_best_role' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN mafia_best_role TEXT DEFAULT 'none'")
            if 'rps_wins' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN rps_wins INTEGER DEFAULT 0")
            if 'rps_losses' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN rps_losses INTEGER DEFAULT 0")
            if 'rps_draws' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN rps_draws INTEGER DEFAULT 0")
            if 'casino_wins' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN casino_wins INTEGER DEFAULT 0")
            if 'casino_losses' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN casino_losses INTEGER DEFAULT 0")
            if 'rr_wins' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN rr_wins INTEGER DEFAULT 0")
            if 'rr_losses' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN rr_losses INTEGER DEFAULT 0")
            if 'rr_games' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN rr_games INTEGER DEFAULT 0")
            if 'ttt_wins' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN ttt_wins INTEGER DEFAULT 0")
            if 'ttt_losses' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN ttt_losses INTEGER DEFAULT 0")
            if 'ttt_draws' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN ttt_draws INTEGER DEFAULT 0")
            if 'gender' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN gender TEXT DEFAULT 'unknown'")
            if 'nickname' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN nickname TEXT")
            self.conn.commit()
        except Exception as e:
            print(f"Ошибка миграции: {e}")
    
    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                level INTEGER DEFAULT 1,
                exp INTEGER DEFAULT 0,
                coins INTEGER DEFAULT 1000,
                energy INTEGER DEFAULT 100,
                reputation INTEGER DEFAULT 0,
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
                mafia_best_role TEXT DEFAULT 'none',
                rps_wins INTEGER DEFAULT 0,
                rps_losses INTEGER DEFAULT 0,
                rps_draws INTEGER DEFAULT 0,
                casino_wins INTEGER DEFAULT 0,
                casino_losses INTEGER DEFAULT 0,
                rr_wins INTEGER DEFAULT 0,
                rr_losses INTEGER DEFAULT 0,
                rr_games INTEGER DEFAULT 0,
                ttt_wins INTEGER DEFAULT 0,
                ttt_losses INTEGER DEFAULT 0,
                ttt_draws INTEGER DEFAULT 0,
                gender TEXT DEFAULT 'unknown',
                nickname TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS stats (
                user_id INTEGER PRIMARY KEY,
                messages_count INTEGER DEFAULT 0,
                commands_used INTEGER DEFAULT 0,
                games_played INTEGER DEFAULT 0,
                daily_streak INTEGER DEFAULT 0,
                last_daily TIMESTAMP,
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
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS clans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                owner_id INTEGER,
                level INTEGER DEFAULT 1,
                exp INTEGER DEFAULT 0,
                members INTEGER DEFAULT 1,
                rating INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
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
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS rr_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                item_name TEXT,
                item_type TEXT,
                item_desc TEXT,
                quantity INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
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
                turn_order TEXT,
                started_at TIMESTAMP
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS ttt_lobbies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_id INTEGER,
                opponent_id INTEGER DEFAULT 0,
                status TEXT DEFAULT 'waiting',
                created_at TIMESTAMP
            )
        ''')
        
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
        
        self.conn.commit()
    
    def init_data(self):
        # Инициализация боссов
        self.init_bosses()
        
        # Инициализация предметов для Русской рулетки
        self.cursor.execute("SELECT * FROM rr_inventory LIMIT 1")
        if not self.cursor.fetchone():
            items_data = [
                (0, "🪙 Монета Демона", "active", "Убирает или добавляет один патрон"),
                (0, "👁️‍🗨️ Кровавый Глаз", "active", "Показывает патроны в текущей и следующей позициях"),
                (0, "🔄 Обратный Спин", "active", "Меняет направление вращения барабана"),
                (0, "⏳ Песочные часы", "active", "Пропускает ход"),
                (0, "🎲 Кубик Судьбы", "active", "Случайно изменяет количество патронов"),
                (0, "🤡 Маска Клоуна", "active", "Полностью перезаряжает оружие"),
                (0, "👁️ Глаз Провидца", "active", "Показывает патрон в текущей позиции"),
                (0, "🧲 Магнит Пули", "active", "Сдвигает все патроны на одну позицию"),
                (0, "🔎 Проклятая лупа", "active", "Показывает точную позицию случайного патрона")
            ]
            for user_id, name, typ, desc in items_data:
                self.cursor.execute(
                    "INSERT INTO rr_inventory (user_id, item_name, item_type, item_desc) VALUES (?, ?, ?, ?)",
                    (user_id, name, typ, desc)
                )
        
        self.conn.commit()
    
    def init_bosses(self):
        self.cursor.execute("SELECT * FROM bosses")
        if not self.cursor.fetchone():
            bosses_data = [
                ("🌲 Лесной тролль", 5, 200, 20, 100, "https://i.imgur.com/troll.jpg"),
                ("🐉 Огненный дракон", 10, 500, 40, 250, "https://i.imgur.com/dragon.jpg"),
                ("❄️ Ледяной великан", 15, 1000, 60, 500, "https://i.imgur.com/giant.jpg"),
                ("⚔️ Темный рыцарь", 20, 2000, 80, 1000, "https://i.imgur.com/knight.jpg"),
                ("👾 Король демонов", 25, 5000, 150, 2500, "https://i.imgur.com/demon.jpg"),
                ("💀 Бог разрушения", 30, 10000, 300, 5000, "https://i.imgur.com/god.jpg")
            ]
            for name, level, health, damage, reward, image in bosses_data:
                self.cursor.execute('''
                    INSERT INTO bosses (boss_name, boss_level, boss_health, boss_max_health, boss_damage, boss_reward, boss_image)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (name, level, health, health, damage, reward, image))
    
    def respawn_bosses(self):
        self.cursor.execute(
            "UPDATE bosses SET is_alive = 1, boss_health = boss_max_health"
        )
        self.conn.commit()
    
    def get_user(self, user_id: int, first_name: str = "Player", last_name: str = ""):
        self.cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = self.cursor.fetchone()
        
        if not user:
            role = 'owner' if user_id == OWNER_ID else 'user'
            self.cursor.execute('''
                INSERT INTO users (user_id, first_name, last_name, role) 
                VALUES (?, ?, ?, ?)
            ''', (user_id, first_name, last_name, role))
            
            self.cursor.execute('''
                INSERT INTO stats (user_id) VALUES (?)
            ''', (user_id,))
            
            self.conn.commit()
            return self.get_user(user_id, first_name, last_name)
        
        columns = [description[0] for description in self.cursor.description]
        return dict(zip(columns, user))
    
    def add_coins(self, user_id: int, coins: int):
        self.cursor.execute(
            "UPDATE users SET coins = coins + ? WHERE user_id = ?",
            (coins, user_id)
        )
        self.conn.commit()
    
    def add_exp(self, user_id: int, exp: int):
        self.cursor.execute(
            "UPDATE users SET exp = exp + ? WHERE user_id = ?",
            (exp, user_id)
        )
        
        self.cursor.execute(
            "SELECT exp, level FROM users WHERE user_id = ?",
            (user_id,)
        )
        user = self.cursor.fetchone()
        
        exp_needed = user[1] * 100
        if user[0] >= exp_needed:
            self.cursor.execute(
                "UPDATE users SET level = level + 1, exp = exp - ? WHERE user_id = ?",
                (exp_needed, user_id)
            )
        self.conn.commit()
    
    def add_energy(self, user_id: int, energy: int):
        self.cursor.execute(
            "UPDATE users SET energy = energy + ? WHERE user_id = ?",
            (energy, user_id)
        )
        self.conn.commit()
    
    def add_stat(self, user_id: int, stat: str, value: int = 1):
        self.cursor.execute(
            f"UPDATE stats SET {stat} = {stat} + ? WHERE user_id = ?",
            (value, user_id)
        )
        self.conn.commit()
    
    def damage(self, user_id: int, amount: int):
        self.cursor.execute(
            "UPDATE users SET health = health - ? WHERE user_id = ?",
            (amount, user_id)
        )
        self.conn.commit()
    
    def heal(self, user_id: int, amount: int):
        self.cursor.execute(
            "UPDATE users SET health = health + ? WHERE user_id = ?",
            (amount, user_id)
        )
        self.conn.commit()
    
    def mute_user(self, user_id: int, minutes: int, admin_id: int = None, reason: str = "Спам"):
        mute_until = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
        self.cursor.execute(
            "UPDATE users SET mute_until = ? WHERE user_id = ?",
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
        self.cursor.execute(
            "UPDATE users SET warns = warns + 1 WHERE user_id = ?",
            (user_id,)
        )
        self.conn.commit()
        
        self.cursor.execute("SELECT warns FROM users WHERE user_id = ?", (user_id,))
        warns = self.cursor.fetchone()[0]
        
        if warns >= 3:
            self.mute_user(user_id, 1440, admin_id, "3 предупреждения")
            return f"⚠️ Пользователь получил 3 варна и был замучен на 24 часа!"
        return f"⚠️ Пользователь получил варн ({warns}/3)"
    
    def ban_user(self, user_id: int, admin_id: int):
        self.cursor.execute(
            "UPDATE users SET banned = 1 WHERE user_id = ?",
            (user_id,)
        )
        self.conn.commit()
    
    def unban_user(self, user_id: int):
        self.cursor.execute(
            "UPDATE users SET banned = 0, warns = 0 WHERE user_id = ?",
            (user_id,)
        )
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
        self.cursor.execute(
            "UPDATE users SET vip_until = ?, role = 'vip' WHERE user_id = ?",
            (vip_until, user_id)
        )
        self.conn.commit()
    
    def set_premium(self, user_id: int, days: int):
        premium_until = datetime.datetime.now() + datetime.timedelta(days=days)
        self.cursor.execute(
            "UPDATE users SET premium_until = ?, role = 'premium' WHERE user_id = ?",
            (premium_until, user_id)
        )
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
        self.cursor.execute(
            "UPDATE bosses SET boss_health = boss_health - ? WHERE id = ?",
            (damage, boss_id)
        )
        self.conn.commit()
        
        self.cursor.execute("SELECT boss_health FROM bosses WHERE id = ?", (boss_id,))
        health = self.cursor.fetchone()[0]
        
        if health <= 0:
            self.cursor.execute(
                "UPDATE bosses SET is_alive = 0 WHERE id = ?",
                (boss_id,)
            )
            self.conn.commit()
            return True
        return False
    
    def add_boss_kill(self, user_id):
        self.cursor.execute(
            "UPDATE users SET boss_kills = boss_kills + 1 WHERE user_id = ?",
            (user_id,)
        )
        self.conn.commit()
    
    def get_top(self, by="coins", limit=10):
        self.cursor.execute(
            f"SELECT first_name, {by} FROM users ORDER BY {by} DESC LIMIT ?",
            (limit,)
        )
        return self.cursor.fetchall()
    
    def create_clan(self, name, owner_id):
        try:
            self.cursor.execute(
                "INSERT INTO clans (name, owner_id) VALUES (?, ?)",
                (name, owner_id)
            )
            self.conn.commit()
            clan_id = self.cursor.lastrowid
            self.cursor.execute(
                "INSERT INTO clan_members (clan_id, user_id, role, joined_at) VALUES (?, ?, ?, ?)",
                (clan_id, owner_id, 'owner', datetime.datetime.now())
            )
            self.cursor.execute(
                "UPDATE users SET clan_id = ?, clan_role = 'owner' WHERE user_id = ?",
                (clan_id, owner_id)
            )
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
        self.cursor.execute(
            "INSERT INTO clan_members (clan_id, user_id, role, joined_at) VALUES (?, ?, ?, ?)",
            (clan_id, user_id, 'member', datetime.datetime.now())
        )
        self.cursor.execute(
            "UPDATE users SET clan_id = ?, clan_role = 'member' WHERE user_id = ?",
            (clan_id, user_id)
        )
        self.cursor.execute(
            "UPDATE clans SET members = members + 1 WHERE id = ?",
            (clan_id,)
        )
        self.conn.commit()
    
    def leave_clan(self, user_id, clan_id):
        self.cursor.execute(
            "DELETE FROM clan_members WHERE clan_id = ? AND user_id = ?",
            (clan_id, user_id)
        )
        self.cursor.execute(
            "UPDATE users SET clan_id = 0, clan_role = 'member' WHERE user_id = ?",
            (user_id,)
        )
        self.cursor.execute(
            "UPDATE clans SET members = members - 1 WHERE id = ?",
            (clan_id,)
        )
        self.conn.commit()
    
    def rr_get_user(self, user_id):
        user = self.get_user(user_id, "")
        return {
            "money": user.get('rr_money', 100),
            "wins": user.get('rr_wins', 0),
            "losses": user.get('rr_losses', 0),
            "games": user.get('rr_games', 0)
        }
    
    def rr_update_user(self, user_id, money=None, wins=None, losses=None, games=None):
        updates = []
        params = []
        
        if money is not None:
            updates.append("rr_money = ?")
            params.append(money)
        if wins is not None:
            updates.append("rr_wins = ?")
            params.append(wins)
        if losses is not None:
            updates.append("rr_losses = ?")
            params.append(losses)
        if games is not None:
            updates.append("rr_games = ?")
            params.append(games)
        
        if updates:
            params.append(user_id)
            self.cursor.execute(
                f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?",
                params
            )
            self.conn.commit()
    
    def rr_add_money(self, user_id, amount):
        self.cursor.execute(
            "UPDATE users SET rr_money = rr_money + ? WHERE user_id = ?",
            (amount, user_id)
        )
        self.conn.commit()
    
    def rr_get_inventory(self, user_id):
        self.cursor.execute(
            "SELECT id, item_name, quantity FROM rr_inventory WHERE user_id = ? AND quantity > 0",
            (user_id,)
        )
        return self.cursor.fetchall()
    
    def rr_add_item(self, user_id, item_name, quantity=1):
        self.cursor.execute(
            "SELECT id, quantity FROM rr_inventory WHERE user_id = ? AND item_name = ?",
            (user_id, item_name)
        )
        item = self.cursor.fetchone()
        if item:
            self.cursor.execute(
                "UPDATE rr_inventory SET quantity = quantity + ? WHERE id = ?",
                (quantity, item[0])
            )
        else:
            self.cursor.execute(
                "INSERT INTO rr_inventory (user_id, item_name, item_type, item_desc, quantity) VALUES (?, ?, ?, ?, ?)",
                (user_id, item_name, "active", "Магический предмет", quantity)
            )
        self.conn.commit()
    
    def rr_create_lobby(self, creator_id, max_players, bet):
        self.cursor.execute('''
            INSERT INTO rr_lobbies (creator_id, max_players, bet, players, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (creator_id, max_players, bet, str([creator_id]), datetime.datetime.now()))
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
                self.cursor.execute(
                    "UPDATE rr_lobbies SET players = ? WHERE id = ?",
                    (str(players), lobby_id)
                )
                self.conn.commit()
                return True
        return False
    
    def rr_leave_lobby(self, lobby_id, user_id):
        self.cursor.execute("SELECT players, creator_id FROM rr_lobbies WHERE id = ?", (lobby_id,))
        result = self.cursor.fetchone()
        if result:
            players = eval(result[0])
            if user_id in players:
                players.remove(user_id)
                self.cursor.execute(
                    "UPDATE rr_lobbies SET players = ? WHERE id = ?",
                    (str(players), lobby_id)
                )
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
                INSERT INTO rr_games (lobby_id, players, current_player, cylinder_size, bullets, positions, alive_players, phase, turn_order, started_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (lobby_id, str(players), current_player, cylinder_size, bullets, str(positions), str(players), 'playing', str(players), datetime.datetime.now()))
            game_id = self.cursor.lastrowid
            
            self.cursor.execute(
                "UPDATE rr_lobbies SET status = 'playing' WHERE id = ?",
                (lobby_id,)
            )
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
            self.rr_update_user(user_id, losses=1)
            
            if len(alive_players) == 1:
                winner_id = alive_players[0]
                self.rr_update_user(winner_id, wins=1)
                self.cursor.execute(
                    "UPDATE rr_games SET phase = 'finished' WHERE id = ?",
                    (game_id,)
                )
                self.conn.commit()
                return "game_over", winner_id
        else:
            result = "alive"
            positions = positions[1:] + [False]
        
        current_player = (current_player + 1) % len(alive_players)
        
        self.cursor.execute('''
            UPDATE rr_games SET current_player = ?, positions = ?, alive_players = ? WHERE id = ?
        ''', (current_player, str(positions), str(alive_players), game_id))
        self.conn.commit()
        
        return result
    
    def ttt_create_lobby(self, creator_id):
        self.cursor.execute('''
            INSERT INTO ttt_lobbies (creator_id, created_at)
            VALUES (?, ?)
        ''', (creator_id, datetime.datetime.now()))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def ttt_join_lobby(self, lobby_id, user_id):
        self.cursor.execute(
            "UPDATE ttt_lobbies SET opponent_id = ?, status = 'playing' WHERE id = ? AND opponent_id = 0",
            (user_id, lobby_id)
        )
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
    
    def close(self):
        self.conn.close()

# ===================== БАЗА ДАННЫХ =====================
db = Database()

# ===================== ИИ С DEEPSEEK =====================
class SpectrumAI:
    def __init__(self):
        self.contexts = {}
        self.user_state = {}
        self.session = None
        self.deepseek_working = False
        print("🤖 ИИ СПЕКТР инициализирован")
    
    async def get_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def get_deepseek_response(self, message: str, user_id: int) -> str:
        try:
            session = await self.get_session()
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {DEEPSEEK_KEY}"
            }
            
            system_prompt = (
                "Ты - игровой бот «СПЕКТР». Ты помогаешь игрокам сражаться с боссами, "
                "играть в казино, русскую рулетку, крестики-нолики и мафию. "
                "Отвечай кратко, с эмодзи, по-русски. Ты дружелюбный помощник."
            )
            
            if user_id not in self.contexts:
                self.contexts[user_id] = [
                    {"role": "system", "content": system_prompt}
                ]
            
            self.contexts[user_id].append({"role": "user", "content": message})
            
            if len(self.contexts[user_id]) > 11:
                self.contexts[user_id] = [self.contexts[user_id][0]] + self.contexts[user_id][-10:]
            
            data = {
                "model": "deepseek-chat",
                "messages": self.contexts[user_id],
                "temperature": 0.7,
                "max_tokens": 150
            }
            
            async with session.post(DEEPSEEK_URL, json=data, headers=headers, timeout=15) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    ai_response = result["choices"][0]["message"]["content"]
                    self.contexts[user_id].append({"role": "assistant", "content": ai_response})
                    self.deepseek_working = True
                    return ai_response
                else:
                    print(f"DeepSeek ошибка: {resp.status}")
                    self.deepseek_working = False
                    return None
        except Exception as e:
            print(f"DeepSeek ошибка: {e}")
            self.deepseek_working = False
            return None
    
    async def get_response(self, user_id: int, message: str) -> str:
        msg_lower = message.lower().strip()
        
        # Сначала пробуем DeepSeek
        deepseek_response = await self.get_deepseek_response(message, user_id)
        if deepseek_response:
            return f"🤖 **СПЕКТР:** {deepseek_response}"
        
        # Если DeepSeek не работает — встроенные ответы
        if any(word in msg_lower for word in ["привет", "здравствуй", "хай"]):
            return "👋 **СПЕКТР:** Приветствую, игрок. Чем могу помочь?"
        
        elif any(word in msg_lower for word in ["как дела", "как ты"]):
            return "⚙️ **СПЕКТР:** Всё отлично! Анализирую твой прогресс."
        
        elif any(word in msg_lower for word in ["спасибо", "благодарю"]):
            return "🤝 **СПЕКТР:** Обращайся. Удачных сражений!"
        
        elif any(word in msg_lower for word in ["пока", "до свидания"]):
            return "👋 **СПЕКТР:** До встречи! Не забывай забирать /daily!"
        
        elif any(word in msg_lower for word in ["кто ты", "ты кто"]):
            return "🤖 **СПЕКТР:** Я — искусственный интеллект, созданный для помощи в играх."
        
        elif any(word in msg_lower for word in ["что ты умеешь", "твои функции"]):
            return (
                "📋 **СПЕКТР:** Мои возможности:\n"
                "• 👾 Битвы с боссами\n"
                "• 🎰 Казино\n"
                "• 💣 Русская рулетка\n"
                "• ⭕ Крестики-нолики 3D\n"
                "• 🔪 Мафия\n"
                "• 👥 Кланы\n"
                "• 💎 Привилегии\n\n"
                "Полный список: /help"
            )
        
        elif any(word in msg_lower for word in ["помощь", "что делать"]):
            return "📚 **СПЕКТР:** Используй /help для списка всех команд."
        
        else:
            responses = [
                "🤖 Я внимательно слушаю. Можешь уточнить?",
                "🎯 Напиши /help, чтобы увидеть все команды.",
                "💡 Если хочешь сразиться с боссом, используй /bosses",
                "📊 Хочешь узнать свою статистику? /profile",
                "🛍 Нужны предметы? /shop",
                "🎁 Не забудь забрать награду: /daily",
                "👥 Интересуют кланы? /clan",
                "🎰 Попытай удачу в казино: /casino",
                "💣 Русская рулетка: .rr",
                "⭕ Крестики-нолики: .кн"
            ]
            return random.choice(responses)
    
    async def close(self):
        if self.session:
            await self.session.close()

# ===================== ОСНОВНОЙ КЛАСС БОТА =====================
class GameBot:
    def __init__(self):
        self.db = db
        self.ai = SpectrumAI()
        self.spam_tracker = defaultdict(list)
        self.application = Application.builder().token(TELEGRAM_TOKEN).build()
        self.setup_handlers()
        logger.info("✅ Бот «СПЕКТР» инициализирован")
    
    def setup_handlers(self):
        # Основные команды
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        self.application.add_handler(CommandHandler("profile", self.cmd_profile))
        self.application.add_handler(CommandHandler("top", self.cmd_top))
        self.application.add_handler(CommandHandler("daily", self.cmd_daily))
        
        # Статистика по играм
        self.application.add_handler(CommandHandler("mafia_stats", self.cmd_mafia_stats))
        self.application.add_handler(CommandHandler("boss_stats", self.cmd_boss_stats))
        self.application.add_handler(CommandHandler("rps_stats", self.cmd_rps_stats))
        self.application.add_handler(CommandHandler("casino_stats", self.cmd_casino_stats))
        self.application.add_handler(CommandHandler("rr_stats", self.cmd_rr_stats))
        self.application.add_handler(CommandHandler("ttt_stats", self.cmd_ttt_stats))
        
        # Боссы
        self.application.add_handler(CommandHandler("bosses", self.cmd_boss_list))
        self.application.add_handler(CommandHandler("boss_fight", self.cmd_boss_fight))
        
        # Магазин
        self.application.add_handler(CommandHandler("shop", self.cmd_shop))
        self.application.add_handler(CommandHandler("buy", self.cmd_buy))
        
        # Привилегии
        self.application.add_handler(CommandHandler("donate", self.cmd_donate))
        self.application.add_handler(CommandHandler("vip", self.cmd_vip))
        self.application.add_handler(CommandHandler("premium", self.cmd_premium))
        
        # Кланы
        self.application.add_handler(CommandHandler("clan", self.cmd_clan))
        self.application.add_handler(CommandHandler("clan_create", self.cmd_clan_create))
        self.application.add_handler(CommandHandler("clan_join", self.cmd_clan_join))
        self.application.add_handler(CommandHandler("clan_leave", self.cmd_clan_leave))
        
        # Казино
        self.application.add_handler(CommandHandler("casino", self.cmd_casino))
        self.application.add_handler(CommandHandler("roulette", self.cmd_roulette))
        self.application.add_handler(CommandHandler("dice", self.cmd_dice_casino))
        
        # Русская рулетка
        self.application.add_handler(CommandHandler("rr", self.cmd_rr))
        self.application.add_handler(CommandHandler("rr_start", self.cmd_rr_start))
        self.application.add_handler(CommandHandler("rr_join", self.cmd_rr_join))
        self.application.add_handler(CommandHandler("rr_shot", self.cmd_rr_shot))
        
        # Крестики-нолики
        self.application.add_handler(CommandHandler("ttt", self.cmd_ttt))
        self.application.add_handler(CommandHandler("ttt_challenge", self.cmd_ttt_challenge))
        self.application.add_handler(CommandHandler("ttt_move", self.cmd_ttt_move))
        
        # Камень-ножницы-бумага
        self.application.add_handler(CommandHandler("rps", self.cmd_rps))
        
        # Админские
        self.application.add_handler(CommandHandler("mute", self.cmd_mute))
        self.application.add_handler(CommandHandler("warn", self.cmd_warn))
        self.application.add_handler(CommandHandler("ban", self.cmd_ban))
        self.application.add_handler(CommandHandler("unban", self.cmd_unban))
        self.application.add_handler(CommandHandler("give", self.cmd_give))
        
        # Обработчики
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        logger.info("✅ Все обработчики зарегистрированы")
    
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
        self.db.get_user(user.id, user.first_name, user.last_name or "")
        
        text = (
            f"⚔️ **ДОБРО ПОЖАЛОВАТЬ В «СПЕКТР», {user.first_name}!** ⚔️\n\n"
            f"🎮 **Твой статус:** {self.get_role_emoji('user')} user\n"
            f"💰 **Монеты:** 1000 🪙\n\n"
            f"**ОСНОВНЫЕ КОМАНДЫ:**\n"
            f"👤 /profile - Твой профиль\n"
            f"🏆 /top - Топ игроков\n"
            f"🎁 /daily - Ежедневная награда\n"
            f"👾 /bosses - Битвы с боссами\n"
            f"🛍 /shop - Магазин\n"
            f"💎 /donate - Привилегии\n"
            f"🎰 /casino - Казино\n"
            f"💣 /rr - Русская рулетка\n"
            f"⭕ /ttt - Крестики-нолики 3D\n"
            f"📊 /mafia_stats - Статистика мафии\n"
            f"📊 /boss_stats - Статистика боссов\n"
            f"📊 /rps_stats - Статистика КНБ\n"
            f"📊 /casino_stats - Статистика казино\n"
            f"📚 /help - Все команды\n\n"
            f"👑 **Владелец:** {OWNER_USERNAME}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
        self.db.add_stat(user.id, "commands_used")
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        text = (
            "📚 **ВСЕ КОМАНДЫ БОТА «СПЕКТР»**\n\n"
            
            "👤 **ПРОФИЛЬ И СТАТИСТИКА**\n"
            "/profile - Твой профиль\n"
            "/top - Топ игроков\n"
            "/daily - Ежедневная награда\n\n"
            
            "📊 **СТАТИСТИКА ПО ИГРАМ**\n"
            "/mafia_stats - Статистика в мафии\n"
            "/boss_stats - Статистика по боссам\n"
            "/rps_stats - Статистика КНБ\n"
            "/casino_stats - Статистика в казино\n"
            "/rr_stats - Статистика в русской рулетке\n"
            "/ttt_stats - Статистика в крестиках-ноликах\n\n"
            
            "👾 **БИТВЫ С БОССАМИ**\n"
            "/bosses - Список боссов\n"
            "/boss_fight [ID] - Сразиться с боссом\n\n"
            
            "🛍 **МАГАЗИН И ДОНАТ**\n"
            "/shop - Магазин предметов\n"
            "/buy [предмет] - Купить предмет\n"
            "/donate - Привилегии\n"
            "/vip - Купить VIP (5000 🪙)\n"
            "/premium - Купить Premium (15000 🪙)\n\n"
            
            "👥 **КЛАНЫ**\n"
            "/clan - Инфо о клане\n"
            "/clan_create [название] - Создать клан\n"
            "/clan_join [ID] - Вступить в клан\n"
            "/clan_leave - Покинуть клан\n\n"
            
            "🎰 **КАЗИНО**\n"
            "/casino - Меню казино\n"
            "/roulette [ставка] [цвет/число] - Рулетка\n"
            "/dice [ставка] - Кости\n\n"
            
            "💣 **РУССКАЯ РУЛЕТКА**\n"
            "/rr - Инфо об игре\n"
            "/rr_start [игроки] [ставка] - Создать лобби\n"
            "/rr_join [ID] - Войти в лобби\n"
            "/rr_shot - Сделать выстрел\n\n"
            
            "⭕ **КРЕСТИКИ-НОЛИКИ 3D**\n"
            "/ttt - Правила игры\n"
            "/ttt_challenge [ID] - Вызвать на игру\n"
            "/ttt_move [клетка] - Сделать ход\n\n"
            
            "✊ **КАМЕНЬ-НОЖНИЦЫ-БУМАГА**\n"
            "/rps - Сыграть в КНБ\n\n"
            
            "👑 **АДМИН КОМАНДЫ**\n"
            "/mute [ID] [минут] - Замутить\n"
            "/warn [ID] - Выдать варн\n"
            "/ban [ID] - Забанить\n"
            "/unban [ID] - Разбанить\n"
            "/give [ID] [сумма] - Выдать монеты\n\n"
            
            f"👑 **Владелец:** {OWNER_USERNAME}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
        self.db.add_stat(user.id, "commands_used")
    
    async def cmd_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id, user.first_name, user.last_name or "")
        
        if self.db.is_muted(user.id):
            remaining = self.db.get_mute_time(user.id)
            await update.message.reply_text(f"🔇 Вы замучены. Осталось: {remaining}")
            return
        
        self.db.cursor.execute("SELECT * FROM stats WHERE user_id = ?", (user.id,))
        stats = self.db.cursor.fetchone()
        
        vip_status = "✅ Активен" if self.is_vip(user.id) else "❌ Нет"
        premium_status = "✅ Активен" if self.is_premium(user.id) else "❌ Нет"
        
        clan = self.db.get_user_clan(user.id)
        clan_name = clan[1] if clan else "Нет"
        
        rr = self.db.rr_get_user(user.id)
        
        text = (
            f"👤 **ПРОФИЛЬ ИГРОКА**\n\n"
            f"**Основное:**\n"
            f"Имя: {user_data.get('first_name', user.first_name)}\n"
            f"Роль: {self.get_role_emoji(user_data.get('role', 'user'))} {user_data.get('role', 'user')}\n"
            f"Уровень: {user_data.get('level', 1)}\n"
            f"Опыт: {user_data.get('exp', 0)}/{user_data.get('level', 1) * 100}\n"
            f"Монеты: {user_data.get('coins', 1000)} 🪙\n"
            f"Энергия: {user_data.get('energy', 100)} ⚡\n\n"
            
            f"**Боевые характеристики:**\n"
            f"Здоровье: {user_data.get('health', 100)} ❤️\n"
            f"Броня: {user_data.get('armor', 0)} 🛡\n"
            f"Урон: {user_data.get('damage', 10)} ⚔️\n\n"
            
            f"**Привилегии:**\n"
            f"VIP: {vip_status}\n"
            f"Premium: {premium_status}\n\n"
            
            f"**Клан:**\n"
            f"Название: {clan_name}\n"
            f"Роль в клане: {user_data.get('clan_role', 'member')}\n\n"
            
            f"**Статистика:**\n"
            f"Сообщений: {stats[1] if stats else 0}\n"
            f"Команд: {stats[2] if stats else 0}\n"
            f"Игр сыграно: {stats[3] if stats else 0}\n"
            f"Дней подряд: {stats[4] if stats else 0}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
        self.db.add_stat(user.id, "commands_used")
    
    async def cmd_mafia_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        wins = user_data.get('mafia_wins', 0)
        games = user_data.get('mafia_games', 0)
        best_role = user_data.get('mafia_best_role', 'none')
        
        text = (
            f"🔪 **СТАТИСТИКА МАФИИ**\n\n"
            f"👤 Игрок: {user.first_name}\n"
            f"🏆 Побед: {wins}\n"
            f"🎮 Игр сыграно: {games}\n"
            f"📊 Винрейт: {self.calc_winrate(wins, games)}%\n"
            f"⭐ Лучшая роль: {best_role}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_boss_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        kills = user_data.get('boss_kills', 0)
        
        text = (
            f"👾 **СТАТИСТИКА БОССОВ**\n\n"
            f"👤 Игрок: {user.first_name}\n"
            f"💀 Боссов убито: {kills}\n"
            f"⚔️ Урон: {user_data.get('damage', 10)}\n"
            f"🛡 Броня: {user_data.get('armor', 0)}"
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
            f"✊ **СТАТИСТИКА КАМЕНЬ-НОЖНИЦЫ-БУМАГА**\n\n"
            f"👤 Игрок: {user.first_name}\n"
            f"🏆 Побед: {wins}\n"
            f"💔 Поражений: {losses}\n"
            f"🤝 Ничьих: {draws}\n"
            f"🎮 Всего игр: {total}\n"
            f"📊 Винрейт: {self.calc_winrate(wins, total)}%"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_casino_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        wins = user_data.get('casino_wins', 0)
        losses = user_data.get('casino_losses', 0)
        total = wins + losses
        
        text = (
            f"🎰 **СТАТИСТИКА КАЗИНО**\n\n"
            f"👤 Игрок: {user.first_name}\n"
            f"🏆 Побед: {wins}\n"
            f"💔 Поражений: {losses}\n"
            f"🎮 Всего игр: {total}\n"
            f"📊 Винрейт: {self.calc_winrate(wins, total)}%"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_rr_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        rr = self.db.rr_get_user(user.id)
        
        text = (
            f"💣 **СТАТИСТИКА РУССКОЙ РУЛЕТКИ**\n\n"
            f"👤 Игрок: {user.first_name}\n"
            f"💀 Черепки: {rr['money']}\n"
            f"🏆 Побед: {rr['wins']}\n"
            f"💔 Поражений: {rr['losses']}\n"
            f"🎮 Игр: {rr['games']}\n"
            f"📊 Винрейт: {self.calc_winrate(rr['wins'], rr['games'])}%"
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
            f"⭕ **СТАТИСТИКА КРЕСТИКОВ-НОЛИКОВ 3D**\n\n"
            f"👤 Игрок: {user.first_name}\n"
            f"🏆 Побед: {wins}\n"
            f"💔 Поражений: {losses}\n"
            f"🤝 Ничьих: {draws}\n"
            f"🎮 Всего игр: {total}\n"
            f"📊 Винрейт: {self.calc_winrate(wins, total)}%"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_top(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        top_coins = self.db.get_top("coins", 10)
        top_level = self.db.get_top("level", 10)
        top_boss = self.db.get_top("boss_kills", 10)
        
        text = "🏆 **ТОП ИГРОКОВ**\n\n"
        
        text += "💰 **По монетам:**\n"
        for i, (name, value) in enumerate(top_coins, 1):
            text += f"{i}. {name} - {value} 🪙\n"
        
        text += "\n📊 **По уровню:**\n"
        for i, (name, value) in enumerate(top_level, 1):
            text += f"{i}. {name} - {value} ур.\n"
        
        text += "\n👾 **По убийству боссов:**\n"
        for i, (name, value) in enumerate(top_boss, 1):
            text += f"{i}. {name} - {value} боссов\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_daily(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id, user.first_name, user.last_name or "")
        
        if self.db.is_muted(user.id):
            remaining = self.db.get_mute_time(user.id)
            await update.message.reply_text(f"🔇 Вы замучены. Осталось: {remaining}")
            return
        
        self.db.cursor.execute(
            "SELECT last_daily, daily_streak FROM stats WHERE user_id = ?",
            (user.id,)
        )
        result = self.db.cursor.fetchone()
        
        today = datetime.datetime.now().date()
        
        if result and result[0]:
            last_date = datetime.datetime.fromisoformat(result[0]).date()
            if last_date == today:
                await update.message.reply_text("❌ Ты уже получал награду сегодня!")
                return
        
        coins = random.randint(100, 300)
        exp = random.randint(20, 60)
        energy = random.randint(10, 30)
        
        streak = result[1] + 1 if result and result[0] else 1
        
        coins = int(coins * (1 + streak * 0.1))
        exp = int(exp * (1 + streak * 0.1))
        
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
            "UPDATE stats SET last_daily = ?, daily_streak = ? WHERE user_id = ?",
            (datetime.datetime.now(), streak, user.id)
        )
        self.db.conn.commit()
        
        await update.message.reply_text(
            f"🎁 **ЕЖЕДНЕВНАЯ НАГРАДА**\n\n"
            f"🔥 Стрик: {streak} дней\n"
            f"💰 +{coins} монет\n"
            f"✨ +{exp} опыта\n"
            f"⚡ +{energy} энергии",
            parse_mode='Markdown'
        )
    
    async def cmd_boss_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        bosses = self.db.get_bosses(alive_only=True)
        
        if not bosses:
            await update.message.reply_text("👾 Все боссы повержены! Ждите возрождения...")
            self.db.respawn_bosses()
            bosses = self.db.get_bosses(alive_only=True)
            if not bosses:
                await update.message.reply_text("❌ Не удалось возродить боссов")
                return
        
        text = "👾 **СПИСОК БОССОВ**\n\n"
        for boss in bosses[:10]:
            text += f"**{boss[1]}** (ур.{boss[2]})\n"
            text += f"ID: {boss[0]} | ❤️ {boss[3]}/{boss[4]} | 💰 {boss[6]}\n\n"
        
        text += "Сразиться: /boss_fight [ID]"
        
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
        
        player_damage = user_data['damage'] + random.randint(-5, 5)
        boss_damage = boss[5] + random.randint(-5, 5)
        player_taken = max(1, boss_damage - user_data['armor'] // 2)
        
        if self.is_vip(user.id):
            player_damage = int(player_damage * 1.2)
        if self.is_premium(user.id):
            player_damage = int(player_damage * 1.5)
        
        boss_killed = self.db.damage_boss(boss_id, player_damage)
        self.db.damage(user.id, player_taken)
        
        text = f"⚔️ **БИТВА С БОССОМ** ⚔️\n\n"
        text += f"Ты нанес {player_damage} урона!\n"
        text += f"Босс нанес тебе {player_taken} урона!\n\n"
        
        if boss_killed:
            reward = boss[6] * (1 + user_data['level'] // 10)
            if self.is_vip(user.id):
                reward = int(reward * 1.5)
            if self.is_premium(user.id):
                reward = int(reward * 2)
            
            self.db.add_coins(user.id, reward)
            self.db.add_boss_kill(user.id)
            self.db.add_exp(user.id, boss[2] * 10)
            
            text += f"🎉 **ПОБЕДА!**\n"
            text += f"💰 Награда: {reward} монет\n"
            text += f"✨ Опыт: +{boss[2] * 10}"
        else:
            boss_info = self.db.get_boss(boss_id)
            text += f"👾 Босс еще жив! Осталось {boss_info[3]}❤️"
        
        if user_data['health'] <= player_taken:
            self.db.heal(user.id, 50)
            text += "\n\n💀 Ты погиб в бою, но воскрешен с 50❤️"
        
        self.db.add_stat(user.id, "games_played")
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_shop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "🏪 **МАГАЗИН «СПЕКТР»**\n\n"
            
            "💊 **ЗЕЛЬЯ**\n"
            "• Зелье здоровья - 50 🪙 (❤️+30)\n"
            "• Большое зелье - 100 🪙 (❤️+70)\n\n"
            
            "⚔️ **ОРУЖИЕ**\n"
            "• Меч - 200 🪙 (⚔️+10)\n"
            "• Легендарный меч - 500 🪙 (⚔️+30)\n\n"
            
            "🛡 **БРОНЯ**\n"
            "• Щит - 150 🪙 (🛡+5)\n"
            "• Доспехи - 400 🪙 (🛡+15)\n\n"
            
            "⚡ **ЭНЕРГИЯ**\n"
            "• Энергетик - 30 🪙 (⚡+20)\n"
            "• Батарейка - 80 🪙 (⚡+50)\n\n"
            
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
            self.db.cursor.execute(
                "UPDATE users SET damage = damage + ? WHERE user_id = ?",
                (item_data['damage'], user.id)
            )
            self.db.conn.commit()
            await update.message.reply_text(f"✅ Урон +{item_data['damage']}⚔️")
        
        elif 'armor' in item_data:
            self.db.cursor.execute(
                "UPDATE users SET armor = armor + ? WHERE user_id = ?",
                (item_data['armor'], user.id)
            )
            self.db.conn.commit()
            await update.message.reply_text(f"✅ Броня +{item_data['armor']}🛡")
        
        elif 'energy' in item_data:
            self.db.add_energy(user.id, item_data['energy'])
            await update.message.reply_text(f"✅ Энергия +{item_data['energy']}⚡")
    
    async def cmd_donate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "💎 **ПРИВИЛЕГИИ «СПЕКТР»** 💎\n\n"
            
            "🌟 **VIP СТАТУС**\n"
            f"• Цена: {VIP_PRICE} 🪙\n"
            f"• Длительность: {VIP_DAYS} дней\n"
            "• Бонусы:\n"
            "  - Урон в битвах +20%\n"
            "  - Награда с боссов +50%\n"
            "  - Ежедневный бонус +50%\n"
            "  - Нет спам-фильтра\n"
            f"• Купить: /vip\n\n"
            
            "💎 **PREMIUM СТАТУС**\n"
            f"• Цена: {PREMIUM_PRICE} 🪙\n"
            f"• Длительность: {PREMIUM_DAYS} дней\n"
            "• Бонусы:\n"
            "  - Все бонусы VIP\n"
            "  - Урон в битвах +50%\n"
            "  - Награда с боссов +100%\n"
            "  - Ежедневный бонус +100%\n\n"
            
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
            f"Теперь у тебя VIP статус на {VIP_DAYS} дней!",
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
            f"Теперь у тебя PREMIUM статус на {PREMIUM_DAYS} дней!",
            parse_mode='Markdown'
        )
    
    async def cmd_clan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        clan = self.db.get_user_clan(user.id)
        
        if not clan:
            await update.message.reply_text(
                "👥 Ты не состоишь в клане.\n"
                "Создать: /clan_create [название]\n"
                "Присоединиться: /clan_join [ID]"
            )
            return
        
        members = self.db.get_clan_members(clan[0])
        
        text = (
            f"👥 **КЛАН «{clan[1]}»**\n\n"
            f"📊 Уровень: {clan[3]}\n"
            f"✨ Опыт: {clan[4]}/{clan[3] * 500}\n"
            f"👤 Участников: {clan[5]}\n"
            f"⭐ Рейтинг: {clan[6]}\n\n"
            f"**Участники:**\n"
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
    
    async def cmd_casino(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("🎰 Рулетка", callback_data="casino_roulette"),
             InlineKeyboardButton("🎲 Кости", callback_data="casino_dice")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🎰 **ДОБРО ПОЖАЛОВАТЬ В КАЗИНО!** 🎰\n\n"
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
            await update.message.reply_text(f"❌ Недостаточно монет! У тебя {user_data['coins']} 🪙")
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
            result_text = f"🎉 Ты выиграл {winnings} 🪙!"
        else:
            self.db.add_coins(user.id, -bet)
            self.db.add_stat(user.id, "casino_losses", 1)
            result_text = f"😢 Ты проиграл {bet} 🪙"
        
        await update.message.reply_text(
            f"🎰 **РУЛЕТКА**\n\n"
            f"Ставка: {bet} 🪙 на {choice}\n"
            f"Выпало: {result_num} {result_color}\n\n"
            f"{result_text}",
            parse_mode='Markdown'
        )
    
    async def cmd_dice_casino(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id, user.first_name, user.last_name or "")
        
        bet = 10
        if context.args:
            try:
                bet = int(context.args[0])
            except:
                pass
        
        if bet > user_data['coins']:
            await update.message.reply_text(f"❌ Недостаточно монет! У тебя {user_data['coins']} 🪙")
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
            f"{dice1} + {dice2} = {total}\n\n"
            f"{result_text}",
            parse_mode='Markdown'
        )
    
    async def cmd_rr(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(
                "💣 **РУССКАЯ РУЛЕТКА**\n\n"
                "Команды:\n"
                "/rr_start [игроки] [ставка] - Создать лобби\n"
                "/rr_join [ID] - Войти в лобби\n"
                "/rr_shot - Сделать выстрел\n"
                "/rr_stats - Моя статистика",
                parse_mode='Markdown'
            )
            return
        
        subcmd = context.args[0].lower()
        
        if subcmd == "stats":
            await self.cmd_rr_stats(update, context)
    
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
        
        if bet < 1 or bet > 10000:
            await update.message.reply_text("❌ Ставка должна быть от 1 до 10000")
            return
        
        user = update.effective_user
        user_data = self.db.rr_get_user(user.id)
        
        if user_data['money'] < bet:
            await update.message.reply_text(f"❌ Недостаточно черепков! У тебя {user_data['money']} 💀")
            return
        
        lobby_id = self.db.rr_create_lobby(user.id, max_players, bet)
        
        await update.message.reply_text(
            f"💣 **ЛОББИ СОЗДАНО!**\n\n"
            f"ID: {lobby_id}\n"
            f"Создатель: {user.first_name}\n"
            f"Игроков: 1/{max_players}\n"
            f"Ставка: {bet} 💀\n\n"
            f"Присоединиться: /rr_join {lobby_id}",
            parse_mode='Markdown'
        )
    
    async def cmd_rr_join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Использование: /rr_join [ID]")
            return
        
        try:
            lobby_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ Неправильный ID")
            return
        
        user = update.effective_user
        user_data = self.db.rr_get_user(user.id)
        lobby = self.db.rr_get_lobby(lobby_id)
        
        if not lobby:
            await update.message.reply_text("❌ Лобби не найдено")
            return
        
        if lobby[5] != 'waiting':
            await update.message.reply_text("❌ Игра уже началась")
            return
        
        players = eval(lobby[4])
        
        if user.id in players:
            await update.message.reply_text("❌ Ты уже в этом лобби")
            return
        
        if len(players) >= lobby[2]:
            await update.message.reply_text("❌ Лобби уже заполнено")
            return
        
        if user_data['money'] < lobby[3]:
            await update.message.reply_text(f"❌ Недостаточно черепков! Нужно {lobby[3]} 💀")
            return
        
        if self.db.rr_join_lobby(lobby_id, user.id):
            await update.message.reply_text(f"✅ Ты присоединился к лобби {lobby_id}!")
        else:
            await update.message.reply_text("❌ Не удалось присоединиться к лобби")
    
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
        await update.message.reply_text(
            "⭕ **КРЕСТИКИ-НОЛИКИ 3D**\n\n"
            "Правила: В каждой клетке обычного поля находится ещё одно поле. Нужно выиграть на 3 малых полях в ряд.\n\n"
            "Команды:\n"
            "/ttt_challenge [ID] - Вызвать игрока\n"
            "/ttt_move [клетка] - Сделать ход",
            parse_mode='Markdown'
        )
    
    async def cmd_ttt_challenge(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Использование: /ttt_challenge [ID]")
            return
        
        await update.message.reply_text("⭕ Функция вызова будет доступна в следующем обновлении!")
    
    async def cmd_ttt_move(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("⭕ Функция хода будет доступна в следующем обновлении!")
    
    async def cmd_rps(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [
                InlineKeyboardButton("🪨 Камень", callback_data="rps_rock"),
                InlineKeyboardButton("✂️ Ножницы", callback_data="rps_scissors"),
                InlineKeyboardButton("📄 Бумага", callback_data="rps_paper")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("✊ **ВЫБЕРИ ХОД:**", reply_markup=reply_markup, parse_mode='Markdown')
    
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
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        message_text = update.message.text
        
        if self.db.is_banned(user.id):
            await update.message.reply_text("🚫 Вы забанены в боте.")
            return
        
        if self.db.is_muted(user.id):
            remaining = self.db.get_mute_time(user.id)
            await update.message.reply_text(f"🔇 Вы замучены. Осталось: {remaining}")
            return
        
        if await self.check_spam(update):
            return
        
        # Обработка команд с точкой
        if message_text.startswith('.'):
            parts = message_text[1:].split()
            cmd = parts[0].lower()
            
            if cmd == "rps":
                await self.cmd_rps(update, context)
            elif cmd == "rr":
                await self.cmd_rr(update, context)
            elif cmd == "ttt":
                await self.cmd_ttt(update, context)
            else:
                await update.message.reply_text("❓ Неизвестная команда.")
            
            self.db.add_stat(user.id, "commands_used")
            return
        
        # Получаем ответ от ИИ
        response = await self.ai.get_response(user.id, message_text)
        await update.message.reply_text(response, parse_mode='Markdown')
        
        self.db.add_exp(user.id, 1)
        self.db.add_stat(user.id, "messages_count")
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user = update.effective_user
        data = query.data
        
        if data == "casino_roulette":
            await self.cmd_roulette(update, context)
        elif data == "casino_dice":
            await self.cmd_dice_casino(update, context)
        elif data.startswith("rps_"):
            choice = data.split('_')[1]
            bot_choice = random.choice(["rock", "scissors", "paper"])
            
            choices = {
                "rock": "🪨 Камень",
                "scissors": "✂️ Ножницы",
                "paper": "📄 Бумага"
            }
            
            result_map = {
                ("rock", "scissors"): "win",
                ("rock", "paper"): "lose",
                ("scissors", "paper"): "win",
                ("scissors", "rock"): "lose",
                ("paper", "rock"): "win",
                ("paper", "scissors"): "lose"
            }
            
            if choice == bot_choice:
                result = "draw"
            else:
                result = result_map.get((choice, bot_choice), "lose")
            
            if result == "win":
                self.db.cursor.execute("UPDATE users SET rps_wins = rps_wins + 1 WHERE user_id = ?", (user.id,))
                text = f"{choices[choice]} vs {choices[bot_choice]}\n\n🎉 Ты выиграл!"
            elif result == "lose":
                self.db.cursor.execute("UPDATE users SET rps_losses = rps_losses + 1 WHERE user_id = ?", (user.id,))
                text = f"{choices[choice]} vs {choices[bot_choice]}\n\n😢 Ты проиграл!"
            else:
                self.db.cursor.execute("UPDATE users SET rps_draws = rps_draws + 1 WHERE user_id = ?", (user.id,))
                text = f"{choices[choice]} vs {choices[bot_choice]}\n\n🤝 Ничья!"
            
            self.db.conn.commit()
            await query.edit_message_text(text, parse_mode='Markdown')
    
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
