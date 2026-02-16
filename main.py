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

# Для Telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# Для VK
try:
    from vkbottle import API, Bot
    from vkbottle.bot import Message
    VKBOTTLE_AVAILABLE = True
except ImportError:
    VKBOTTLE_AVAILABLE = False
    print("⚠️ vkbottle не установлен. VK бот будет отключен.")

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===================== КОНФИГУРАЦИЯ =====================
# Telegram
TELEGRAM_TOKEN = "8326390250:AAFuUVHZ6ucUtLy132Ep1pmteRr6tTk7u0Q"
OWNER_ID_TG = 1732658530
OWNER_USERNAME_TG = "@NobuCraft"

# VK
VK_TOKEN = "vk1.a.sl7q9qebmFwqxkdpMVJTQpLWUtLMsKYPvVInyidaBe1GwkuxkDewfvYss7AcGYPlbw817In-UDgILA38ltHafX3p-t0_xaNWPwXOPpwPezMqq89fx1y9ru6lyde_qFYtu-ll3J-1_vBPPCZ0fHyh4j8qxkiXWCVBgFKtkNhqukNIFTbWqMjX57iMIPbawIdYOr_ngdaXRuGXZAAxzffhbg"
OWNER_ID_VK = 713616259

# OpenRouter AI
OPENROUTER_KEY = "sk-97ac1d0de1844c449852a5470cbcae35"

# Настройки
SPAM_LIMIT = 5
SPAM_WINDOW = 3
SPAM_MUTE_TIME = 120

# ===================== БАЗА ДАННЫХ =====================
class Database:
    def __init__(self, db_name="spectrum_bot.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self):
        # Пользователи
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT,
                platform_id TEXT UNIQUE,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                coins INTEGER DEFAULT 1000,
                diamonds INTEGER DEFAULT 0,
                crystals INTEGER DEFAULT 0,
                rr_money INTEGER DEFAULT 100,
                energy INTEGER DEFAULT 100,
                level INTEGER DEFAULT 1,
                exp INTEGER DEFAULT 0,
                role TEXT DEFAULT 'user',
                privilege TEXT DEFAULT 'user',
                privilege_until TIMESTAMP,
                warns INTEGER DEFAULT 0,
                mute_until TIMESTAMP,
                banned INTEGER DEFAULT 0,
                health INTEGER DEFAULT 100,
                max_health INTEGER DEFAULT 100,
                armor INTEGER DEFAULT 0,
                damage INTEGER DEFAULT 10,
                boss_kills INTEGER DEFAULT 0,
                last_activity TIMESTAMP,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                messages_count INTEGER DEFAULT 0,
                commands_used INTEGER DEFAULT 0,
                games_played INTEGER DEFAULT 0,
                reputation INTEGER DEFAULT 0,
                reputation_given INTEGER DEFAULT 0,
                description TEXT DEFAULT '',
                gender TEXT DEFAULT 'unknown',
                nickname TEXT DEFAULT '',
                birthday TEXT DEFAULT '',
                city TEXT DEFAULT '',
                mafia_wins INTEGER DEFAULT 0,
                mafia_games INTEGER DEFAULT 0,
                rps_wins INTEGER DEFAULT 0,
                rps_losses INTEGER DEFAULT 0,
                rps_draws INTEGER DEFAULT 0,
                casino_wins INTEGER DEFAULT 0,
                casino_losses INTEGER DEFAULT 0,
                ttt_wins INTEGER DEFAULT 0,
                ttt_losses INTEGER DEFAULT 0,
                ttt_draws INTEGER DEFAULT 0,
                rr_wins INTEGER DEFAULT 0,
                rr_losses INTEGER DEFAULT 0
            )
        ''')
        
        # Баны
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS bans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT,
                platform_id TEXT,
                username TEXT,
                reason TEXT,
                banned_by INTEGER,
                banned_by_name TEXT,
                ban_date TIMESTAMP,
                ban_duration TEXT,
                ban_until TIMESTAMP,
                is_permanent INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # Муты
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS mutes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT,
                platform_id TEXT,
                username TEXT,
                reason TEXT,
                muted_by INTEGER,
                muted_by_name TEXT,
                mute_date TIMESTAMP,
                mute_duration TEXT,
                mute_until TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # Варны
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS warns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT,
                platform_id TEXT,
                username TEXT,
                reason TEXT,
                warned_by INTEGER,
                warned_by_name TEXT,
                warn_date TIMESTAMP
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
                is_alive INTEGER DEFAULT 1
            )
        ''')
        
        # Транзакции
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_id TEXT,
                to_id TEXT,
                amount INTEGER,
                currency TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Закладки
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT,
                platform_id TEXT,
                description TEXT,
                message_link TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Награды
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS awards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT,
                platform_id TEXT,
                award_name TEXT,
                award_description TEXT,
                awarded_by INTEGER,
                awarded_by_name TEXT,
                award_date TIMESTAMP
            )
        ''')
        
        # Настройки групп
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS group_settings (
                chat_id TEXT PRIMARY KEY,
                platform TEXT,
                welcome_enabled INTEGER DEFAULT 1,
                welcome_message TEXT DEFAULT '🌟 Добро пожаловать, {user}!',
                goodbye_enabled INTEGER DEFAULT 1,
                goodbye_message TEXT DEFAULT '👋 Пока, {user}!',
                rules TEXT DEFAULT ''
            )
        ''')
        
        # Русская рулетка - лобби
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS rr_lobbies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_id TEXT,
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
                items TEXT,
                started_at TIMESTAMP
            )
        ''')
        
        # Предметы для русской рулетки
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS rr_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                item_name TEXT,
                item_type TEXT,
                quantity INTEGER DEFAULT 1
            )
        ''')
        
        # Крестики-нолики 3D - игры
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS ttt_games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_x TEXT,
                player_o TEXT,
                current_player TEXT,
                main_board TEXT,
                sub_boards TEXT,
                last_move INTEGER,
                status TEXT,
                started_at TIMESTAMP
            )
        ''')
        
        # Мафия - игры
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS mafia_games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_id TEXT,
                players TEXT,
                roles TEXT,
                phase TEXT DEFAULT 'night',
                day_count INTEGER DEFAULT 1,
                status TEXT DEFAULT 'waiting',
                created_at TIMESTAMP
            )
        ''')
        
        self.conn.commit()
        self.init_bosses()
    
    def init_bosses(self):
        self.cursor.execute("SELECT COUNT(*) FROM bosses")
        if self.cursor.fetchone()[0] == 0:
            bosses = [
                ("🦟 Ядовитый комар", 5, 2780, 2780, 34, 500),
                ("🐉 Огненный дракон", 10, 5000, 5000, 50, 1000),
                ("❄️ Ледяной великан", 15, 8000, 8000, 70, 1500),
                ("⚔️ Темный рыцарь", 20, 12000, 12000, 90, 2000),
                ("👾 Король демонов", 25, 20000, 20000, 120, 3000),
                ("💀 Бог разрушения", 30, 30000, 30000, 150, 5000)
            ]
            for boss in bosses:
                self.cursor.execute('''
                    INSERT INTO bosses (boss_name, boss_level, boss_health, boss_max_health, boss_damage, boss_reward)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', boss)
            self.conn.commit()
    
    def get_user(self, platform, platform_id, username="", first_name="", last_name=""):
        self.cursor.execute(
            "SELECT * FROM users WHERE platform = ? AND platform_id = ?",
            (platform, platform_id)
        )
        user = self.cursor.fetchone()
        
        if not user:
            role = 'owner' if (platform == 'tg' and int(platform_id) == OWNER_ID_TG) or (platform == 'vk' and int(platform_id) == OWNER_ID_VK) else 'user'
            self.cursor.execute('''
                INSERT INTO users (platform, platform_id, username, first_name, last_name, role, first_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (platform, platform_id, username, first_name, last_name, role, datetime.datetime.now()))
            self.conn.commit()
            return self.get_user(platform, platform_id, username, first_name, last_name)
        
        columns = [description[0] for description in self.cursor.description]
        return dict(zip(columns, user))
    
    def update_activity(self, platform, platform_id):
        self.cursor.execute(
            "UPDATE users SET last_activity = ? WHERE platform = ? AND platform_id = ?",
            (datetime.datetime.now(), platform, platform_id)
        )
        self.conn.commit()
    
    def add_coins(self, platform, platform_id, amount, currency="coins"):
        if currency == "coins":
            self.cursor.execute("UPDATE users SET coins = coins + ? WHERE platform = ? AND platform_id = ?", (amount, platform, platform_id))
        elif currency == "diamonds":
            self.cursor.execute("UPDATE users SET diamonds = diamonds + ? WHERE platform = ? AND platform_id = ?", (amount, platform, platform_id))
        elif currency == "rr_money":
            self.cursor.execute("UPDATE users SET rr_money = rr_money + ? WHERE platform = ? AND platform_id = ?", (amount, platform, platform_id))
        elif currency == "energy":
            self.cursor.execute("UPDATE users SET energy = energy + ? WHERE platform = ? AND platform_id = ?", (amount, platform, platform_id))
        self.conn.commit()
    
    def transfer_money(self, from_platform, from_id, to_platform, to_id, amount, currency="coins"):
        from_user = self.get_user(from_platform, from_id)
        if currency == "coins" and from_user['coins'] < amount:
            return False, "Недостаточно монет"
        if currency == "diamonds" and from_user['diamonds'] < amount:
            return False, "Недостаточно алмазов"
        
        self.add_coins(from_platform, from_id, -amount, currency)
        self.add_coins(to_platform, to_id, amount, currency)
        
        self.cursor.execute('''
            INSERT INTO transactions (from_id, to_id, amount, currency)
            VALUES (?, ?, ?, ?)
        ''', (f"{from_platform}:{from_id}", f"{to_platform}:{to_id}", amount, currency))
        self.conn.commit()
        
        return True, f"Переведено {amount} {currency}"
    
    def add_exp(self, platform, platform_id, exp):
        self.cursor.execute(
            "UPDATE users SET exp = exp + ? WHERE platform = ? AND platform_id = ?",
            (exp, platform, platform_id)
        )
        self.cursor.execute(
            "SELECT exp, level FROM users WHERE platform = ? AND platform_id = ?",
            (platform, platform_id)
        )
        user = self.cursor.fetchone()
        if user and user[0] >= user[1] * 100:
            self.cursor.execute(
                "UPDATE users SET level = level + 1, exp = exp - ? WHERE platform = ? AND platform_id = ?",
                (user[1] * 100, platform, platform_id)
            )
        self.conn.commit()
    
    def damage_user(self, platform, platform_id, damage):
        self.cursor.execute(
            "UPDATE users SET health = health - ? WHERE platform = ? AND platform_id = ?",
            (damage, platform, platform_id)
        )
        self.cursor.execute(
            "SELECT health FROM users WHERE platform = ? AND platform_id = ?",
            (platform, platform_id)
        )
        health = self.cursor.fetchone()[0]
        if health <= 0:
            self.cursor.execute(
                "UPDATE users SET health = max_health WHERE platform = ? AND platform_id = ?",
                (platform, platform_id)
            )
        self.conn.commit()
        return health > 0
    
    def heal_user(self, platform, platform_id, amount):
        self.cursor.execute(
            "UPDATE users SET health = health + ? WHERE platform = ? AND platform_id = ?",
            (amount, platform, platform_id)
        )
        self.cursor.execute(
            "UPDATE users SET health = max_health WHERE health > max_health AND platform = ? AND platform_id = ?",
            (platform, platform_id)
        )
        self.conn.commit()
    
    def get_boss(self):
        self.cursor.execute("SELECT * FROM bosses WHERE is_alive = 1 ORDER BY id LIMIT 1")
        boss = self.cursor.fetchone()
        if not boss:
            self.cursor.execute("UPDATE bosses SET is_alive = 1, boss_health = boss_max_health")
            self.conn.commit()
            return self.get_boss()
        columns = [description[0] for description in self.cursor.description]
        return dict(zip(columns, boss))
    
    def damage_boss(self, boss_id, damage):
        self.cursor.execute("UPDATE bosses SET boss_health = boss_health - ? WHERE id = ?", (damage, boss_id))
        self.conn.commit()
        self.cursor.execute("SELECT boss_health FROM bosses WHERE id = ?", (boss_id,))
        health = self.cursor.fetchone()[0]
        if health <= 0:
            self.cursor.execute("UPDATE bosses SET is_alive = 0 WHERE id = ?", (boss_id,))
            self.conn.commit()
            return True, 0
        return False, health
    
    def get_player_count(self):
        week_ago = datetime.datetime.now() - datetime.timedelta(days=7)
        self.cursor.execute("SELECT COUNT(*) FROM users WHERE last_activity > ?", (week_ago,))
        return self.cursor.fetchone()[0]
    
    def get_top(self, by="coins", limit=10):
        self.cursor.execute(f"SELECT username, first_name, {by} FROM users ORDER BY {by} DESC LIMIT ?", (limit,))
        return self.cursor.fetchall()
    
    def get_user_by_username(self, platform, username):
        username = username.lstrip('@')
        self.cursor.execute(
            "SELECT * FROM users WHERE platform = ? AND (username LIKE ? OR first_name LIKE ?)",
            (platform, f"%{username}%", f"%{username}%")
        )
        return self.cursor.fetchone()
    
    def add_bookmark(self, platform, platform_id, description, message_link):
        self.cursor.execute('''
            INSERT INTO bookmarks (platform, platform_id, description, message_link)
            VALUES (?, ?, ?, ?)
        ''', (platform, platform_id, description, message_link))
        self.conn.commit()
    
    def get_bookmarks(self, platform, platform_id):
        self.cursor.execute(
            "SELECT * FROM bookmarks WHERE platform = ? AND platform_id = ? ORDER BY timestamp DESC",
            (platform, platform_id)
        )
        return self.cursor.fetchall()
    
    def add_award(self, platform, platform_id, award_name, award_description, awarded_by, awarded_by_name):
        self.cursor.execute('''
            INSERT INTO awards (platform, platform_id, award_name, award_description, awarded_by, awarded_by_name, award_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (platform, platform_id, award_name, award_description, awarded_by, awarded_by_name, datetime.datetime.now()))
        self.conn.commit()
    
    def get_awards(self, platform, platform_id):
        self.cursor.execute(
            "SELECT * FROM awards WHERE platform = ? AND platform_id = ? ORDER BY award_date DESC",
            (platform, platform_id)
        )
        return self.cursor.fetchall()
    
    def is_muted(self, platform, platform_id):
        self.cursor.execute("SELECT mute_until FROM users WHERE platform = ? AND platform_id = ?", (platform, platform_id))
        result = self.cursor.fetchone()
        if result and result[0]:
            return datetime.datetime.now() < datetime.datetime.fromisoformat(result[0])
        return False
    
    def mute_user(self, platform, platform_id, username, minutes, reason, muted_by, muted_by_name):
        mute_until = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
        self.cursor.execute("UPDATE users SET mute_until = ? WHERE platform = ? AND platform_id = ?", (mute_until, platform, platform_id))
        self.cursor.execute('''
            INSERT INTO mutes (platform, platform_id, username, reason, muted_by, muted_by_name, mute_date, mute_duration, mute_until, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (platform, platform_id, username, reason, muted_by, muted_by_name, datetime.datetime.now(), f"{minutes} мин", mute_until, 1))
        self.conn.commit()
    
    def unmute_user(self, platform, platform_id):
        self.cursor.execute("UPDATE users SET mute_until = NULL WHERE platform = ? AND platform_id = ?", (platform, platform_id))
        self.cursor.execute("UPDATE mutes SET is_active = 0 WHERE platform = ? AND platform_id = ?", (platform, platform_id))
        self.conn.commit()
    
    def add_warn(self, platform, platform_id, username, reason, warned_by, warned_by_name):
        self.cursor.execute("UPDATE users SET warns = warns + 1 WHERE platform = ? AND platform_id = ?", (platform, platform_id))
        self.cursor.execute('''
            INSERT INTO warns (platform, platform_id, username, reason, warned_by, warned_by_name, warn_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (platform, platform_id, username, reason, warned_by, warned_by_name, datetime.datetime.now()))
        self.conn.commit()
        self.cursor.execute("SELECT warns FROM users WHERE platform = ? AND platform_id = ?", (platform, platform_id))
        return self.cursor.fetchone()[0]
    
    def ban_user(self, platform, platform_id, username, reason, duration, banned_by, banned_by_name):
        is_permanent = duration.lower() == "навсегда"
        ban_until = None if is_permanent else datetime.datetime.now() + datetime.timedelta(days=365)
        
        self.cursor.execute("UPDATE users SET banned = 1 WHERE platform = ? AND platform_id = ?", (platform, platform_id))
        self.cursor.execute('''
            INSERT INTO bans (platform, platform_id, username, reason, banned_by, banned_by_name, ban_date, ban_duration, ban_until, is_permanent, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (platform, platform_id, username, reason, banned_by, banned_by_name, datetime.datetime.now(), duration, ban_until, 1 if is_permanent else 0, 1))
        self.conn.commit()
    
    def unban_user(self, platform, platform_id):
        self.cursor.execute("UPDATE users SET banned = 0 WHERE platform = ? AND platform_id = ?", (platform, platform_id))
        self.cursor.execute("UPDATE bans SET is_active = 0 WHERE platform = ? AND platform_id = ?", (platform, platform_id))
        self.conn.commit()
    
    def is_banned(self, platform, platform_id):
        self.cursor.execute("SELECT banned FROM users WHERE platform = ? AND platform_id = ?", (platform, platform_id))
        result = self.cursor.fetchone()
        return result and result[0] == 1
    
    def get_banned_users(self, page=1, per_page=10):
        offset = (page - 1) * per_page
        self.cursor.execute('''
            SELECT * FROM bans WHERE is_active = 1 ORDER BY ban_date DESC LIMIT ? OFFSET ?
        ''', (per_page, offset))
        return self.cursor.fetchall()
    
    def get_muted_users(self, page=1, per_page=10):
        offset = (page - 1) * per_page
        self.cursor.execute('''
            SELECT * FROM mutes WHERE is_active = 1 ORDER BY mute_date DESC LIMIT ? OFFSET ?
        ''', (per_page, offset))
        return self.cursor.fetchall()
    
    def get_warned_users(self, page=1, per_page=10):
        offset = (page - 1) * per_page
        self.cursor.execute('''
            SELECT * FROM warns ORDER BY warn_date DESC LIMIT ? OFFSET ?
        ''', (per_page, offset))
        return self.cursor.fetchall()
    
    def has_privilege(self, platform, platform_id, privilege):
        if int(platform_id) in [OWNER_ID_TG, OWNER_ID_VK]:
            return True
        self.cursor.execute("SELECT role, privilege, privilege_until FROM users WHERE platform = ? AND platform_id = ?", (platform, platform_id))
        user = self.cursor.fetchone()
        if not user:
            return False
        if user[0] in ['owner', 'admin']:
            return True
        if user[1] == privilege and user[2]:
            return datetime.datetime.now() < datetime.datetime.fromisoformat(user[2])
        return False
    
    def set_privilege(self, platform, platform_id, privilege, days):
        until = datetime.datetime.now() + datetime.timedelta(days=days) if days > 0 else None
        self.cursor.execute("UPDATE users SET privilege = ?, privilege_until = ? WHERE platform = ? AND platform_id = ?", (privilege, until, platform, platform_id))
        self.conn.commit()
    
    # ===================== РУССКАЯ РУЛЕТКА =====================
    def rr_create_lobby(self, creator_id, max_players, bet):
        self.cursor.execute('''
            INSERT INTO rr_lobbies (creator_id, max_players, bet, players, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (creator_id, max_players, bet, json.dumps([creator_id]), datetime.datetime.now()))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def rr_join_lobby(self, lobby_id, user_id):
        self.cursor.execute("SELECT players, max_players FROM rr_lobbies WHERE id = ? AND status = 'waiting'", (lobby_id,))
        result = self.cursor.fetchone()
        if result:
            players = json.loads(result[0])
            if user_id not in players and len(players) < result[1]:
                players.append(user_id)
                self.cursor.execute("UPDATE rr_lobbies SET players = ? WHERE id = ?", (json.dumps(players), lobby_id))
                self.conn.commit()
                return True
        return False
    
    def rr_start_game(self, lobby_id):
        self.cursor.execute("SELECT * FROM rr_lobbies WHERE id = ?", (lobby_id,))
        lobby = self.cursor.fetchone()
        if not lobby:
            return None
        
        columns = [description[0] for description in self.cursor.description]
        lobby_dict = dict(zip(columns, lobby))
        
        players = json.loads(lobby_dict['players'])
        bet = lobby_dict['bet']
        
        cylinder_size = random.randint(6, 10)
        bullets = random.randint(1, 3)
        
        positions = [False] * cylinder_size
        for pos in random.sample(range(cylinder_size), bullets):
            positions[pos] = True
        
        random.shuffle(players)
        
        self.cursor.execute('''
            INSERT INTO rr_games (lobby_id, players, current_player, cylinder_size, bullets, positions, alive_players, phase, items, started_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (lobby_id, json.dumps(players), 0, cylinder_size, bullets, json.dumps(positions), json.dumps(players), 'playing', json.dumps({}), datetime.datetime.now()))
        game_id = self.cursor.lastrowid
        
        self.cursor.execute("UPDATE rr_lobbies SET status = 'playing' WHERE id = ?", (lobby_id,))
        self.conn.commit()
        
        return game_id, players, cylinder_size, bullets, positions
    
    def rr_get_game(self, game_id):
        self.cursor.execute("SELECT * FROM rr_games WHERE id = ?", (game_id,))
        game = self.cursor.fetchone()
        if game:
            columns = [description[0] for description in self.cursor.description]
            return dict(zip(columns, game))
        return None
    
    def rr_make_shot(self, game_id, user_id):
        game = self.rr_get_game(game_id)
        if not game:
            return None
        
        players = json.loads(game['players'])
        current_player = game['current_player']
        positions = json.loads(game['positions'])
        alive_players = json.loads(game['alive_players'])
        
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
        
        if alive_players:
            current_player = (current_player + 1) % len(alive_players)
        
        self.cursor.execute("UPDATE rr_games SET current_player = ?, positions = ?, alive_players = ? WHERE id = ?", 
                           (current_player, json.dumps(positions), json.dumps(alive_players), game_id))
        self.conn.commit()
        
        return result
    
    def rr_add_item(self, user_id, item_name, item_type):
        self.cursor.execute("SELECT id, quantity FROM rr_items WHERE user_id = ? AND item_name = ?", (user_id, item_name))
        item = self.cursor.fetchone()
        if item:
            self.cursor.execute("UPDATE rr_items SET quantity = quantity + 1 WHERE id = ?", (item[0],))
        else:
            self.cursor.execute("INSERT INTO rr_items (user_id, item_name, item_type, quantity) VALUES (?, ?, ?, ?)", 
                               (user_id, item_name, item_type, 1))
        self.conn.commit()
    
    def rr_get_items(self, user_id):
        self.cursor.execute("SELECT * FROM rr_items WHERE user_id = ?", (user_id,))
        return self.cursor.fetchall()
    
    # ===================== КРЕСТИКИ-НОЛИКИ 3D =====================
    def ttt_create_game(self, player_x, player_o):
        main_board = [[0, 0, 0] for _ in range(3)]
        sub_boards = [[[0, 0, 0] for _ in range(3)] for _ in range(9)]
        
        self.cursor.execute('''
            INSERT INTO ttt_games (player_x, player_o, current_player, main_board, sub_boards, last_move, status, started_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (player_x, player_o, player_x, json.dumps(main_board), json.dumps(sub_boards), -1, 'playing', datetime.datetime.now()))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def ttt_make_move(self, game_id, user_id, main_row, main_col, sub_row, sub_col):
        self.cursor.execute("SELECT * FROM ttt_games WHERE id = ?", (game_id,))
        game = self.cursor.fetchone()
        if not game:
            return None
        
        columns = [description[0] for description in self.cursor.description]
        game_dict = dict(zip(columns, game))
        
        main_board = json.loads(game_dict['main_board'])
        sub_boards = json.loads(game_dict['sub_boards'])
        current_player = game_dict['current_player']
        
        if current_player != user_id:
            return "not_your_turn"
        
        if sub_boards[main_row * 3 + main_col][sub_row][sub_col] != 0:
            return "cell_occupied"
        
        marker = 1 if user_id == game_dict['player_x'] else 2
        sub_boards[main_row * 3 + main_col][sub_row][sub_col] = marker
        
        # Проверка победы на малом поле
        sub_winner = self.ttt_check_winner(sub_boards[main_row * 3 + main_col])
        if sub_winner:
            main_board[main_row][main_col] = sub_winner
        
        # Проверка победы на главном поле
        main_winner = self.ttt_check_winner(main_board)
        if main_winner:
            status = 'finished'
            winner = game_dict['player_x'] if main_winner == 1 else game_dict['player_o']
        else:
            status = 'playing'
            winner = None
            current_player = game_dict['player_o'] if current_player == game_dict['player_x'] else game_dict['player_x']
        
        self.cursor.execute('''
            UPDATE ttt_games SET main_board = ?, sub_boards = ?, current_player = ?, status = ? WHERE id = ?
        ''', (json.dumps(main_board), json.dumps(sub_boards), current_player, status, game_id))
        self.conn.commit()
        
        return {
            'status': status,
            'winner': winner,
            'main_board': main_board,
            'sub_boards': sub_boards,
            'current_player': current_player
        }
    
    def ttt_check_winner(self, board):
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
    
    # ===================== МАФИЯ =====================
    def mafia_create_game(self, creator_id):
        self.cursor.execute('''
            INSERT INTO mafia_games (creator_id, players, created_at)
            VALUES (?, ?, ?)
        ''', (creator_id, json.dumps([creator_id]), datetime.datetime.now()))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def mafia_join_game(self, game_id, user_id):
        self.cursor.execute("SELECT players FROM mafia_games WHERE id = ? AND status = 'waiting'", (game_id,))
        result = self.cursor.fetchone()
        if result:
            players = json.loads(result[0])
            if user_id not in players and len(players) < 10:
                players.append(user_id)
                self.cursor.execute("UPDATE mafia_games SET players = ? WHERE id = ?", (json.dumps(players), game_id))
                self.conn.commit()
                return True
        return False
    
    def mafia_start_game(self, game_id):
        self.cursor.execute("SELECT players FROM mafia_games WHERE id = ?", (game_id,))
        result = self.cursor.fetchone()
        if not result:
            return None
        
        players = json.loads(result[0])
        if len(players) < 4:
            return "not_enough_players"
        
        # Распределение ролей
        mafia_count = max(1, len(players) // 3)
        roles = ['mafia'] * mafia_count + ['civilian'] * (len(players) - mafia_count)
        random.shuffle(roles)
        
        roles_dict = {players[i]: roles[i] for i in range(len(players))}
        
        self.cursor.execute('''
            UPDATE mafia_games SET roles = ?, status = 'playing', phase = 'night' WHERE id = ?
        ''', (json.dumps(roles_dict), game_id))
        self.conn.commit()
        
        return roles_dict
    
    def close(self):
        self.conn.close()

# ===================== ИНИЦИАЛИЗАЦИЯ БАЗЫ =====================
db = Database()

# ===================== ОСНОВНОЙ КЛАСС БОТА =====================
class GameBot:
    def __init__(self):
        self.db = db
        self.tg_application = None
        self.vk_bot = None
        self.vk_api = None
        self.last_activity = defaultdict(dict)
        self.rr_games = {}
        self.ttt_games = {}
        self.mafia_games = {}
        
        if TELEGRAM_TOKEN:
            self.tg_application = Application.builder().token(TELEGRAM_TOKEN).build()
            self.setup_tg_handlers()
            logger.info("✅ Telegram бот инициализирован")
        
        if VK_TOKEN and VKBOTTLE_AVAILABLE:
            self.vk_bot = Bot(VK_TOKEN)
            self.vk_api = API(VK_TOKEN)
            self.setup_vk_handlers()
            logger.info("✅ VK бот инициализирован")
    
    # ===================== TELEGRAM ОБРАБОТЧИКИ =====================
    def setup_tg_handlers(self):
        # Основные
        self.tg_application.add_handler(CommandHandler("start", self.tg_cmd_start))
        self.tg_application.add_handler(CommandHandler("menu", self.tg_cmd_menu))
        self.tg_application.add_handler(CommandHandler("help", self.tg_cmd_help))
        
        # Профиль и статистика
        self.tg_application.add_handler(CommandHandler("profile", self.tg_cmd_profile))
        self.tg_application.add_handler(CommandHandler("whoami", self.tg_cmd_whoami))
        self.tg_application.add_handler(CommandHandler("top", self.tg_cmd_top))
        self.tg_application.add_handler(CommandHandler("players", self.tg_cmd_players))
        
        # Боссы
        self.tg_application.add_handler(CommandHandler("boss", self.tg_cmd_boss))
        self.tg_application.add_handler(CommandHandler("boss_fight", self.tg_cmd_boss_fight))
        self.tg_application.add_handler(CommandHandler("regen", self.tg_cmd_regen))
        
        # Экономика
        self.tg_application.add_handler(CommandHandler("shop", self.tg_cmd_shop))
        self.tg_application.add_handler(CommandHandler("donate", self.tg_cmd_donate))
        self.tg_application.add_handler(CommandHandler("pay", self.tg_cmd_pay))
        
        # Команды
        self.tg_application.add_handler(CommandHandler("cmd", self.tg_cmd_privilege_commands))
        self.tg_application.add_handler(CommandHandler("rules", self.tg_cmd_rules))
        self.tg_application.add_handler(CommandHandler("set_rules", self.tg_cmd_set_rules))
        
        # Админские
        self.tg_application.add_handler(CommandHandler("mute", self.tg_cmd_mute))
        self.tg_application.add_handler(CommandHandler("unmute", self.tg_cmd_unmute))
        self.tg_application.add_handler(CommandHandler("warn", self.tg_cmd_warn))
        self.tg_application.add_handler(CommandHandler("ban", self.tg_cmd_ban))
        self.tg_application.add_handler(CommandHandler("unban", self.tg_cmd_unban))
        self.tg_application.add_handler(CommandHandler("banlist", self.tg_cmd_banlist))
        self.tg_application.add_handler(CommandHandler("mutelist", self.tg_cmd_mutelist))
        self.tg_application.add_handler(CommandHandler("warnlist", self.tg_cmd_warnlist))
        
        # Русская рулетка
        self.tg_application.add_handler(CommandHandler("rr", self.tg_cmd_rr))
        self.tg_application.add_handler(CommandHandler("rr_start", self.tg_cmd_rr_start))
        self.tg_application.add_handler(CommandHandler("rr_join", self.tg_cmd_rr_join))
        self.tg_application.add_handler(CommandHandler("rr_shot", self.tg_cmd_rr_shot))
        self.tg_application.add_handler(CommandHandler("rr_items", self.tg_cmd_rr_items))
        
        # Крестики-нолики 3D
        self.tg_application.add_handler(CommandHandler("ttt", self.tg_cmd_ttt))
        self.tg_application.add_handler(CommandHandler("ttt_challenge", self.tg_cmd_ttt_challenge))
        self.tg_application.add_handler(CommandHandler("ttt_move", self.tg_cmd_ttt_move))
        
        # Мафия
        self.tg_application.add_handler(CommandHandler("mafia", self.tg_cmd_mafia))
        self.tg_application.add_handler(CommandHandler("mafia_create", self.tg_cmd_mafia_create))
        self.tg_application.add_handler(CommandHandler("mafia_join", self.tg_cmd_mafia_join))
        self.tg_application.add_handler(CommandHandler("mafia_start", self.tg_cmd_mafia_start))
        
        # Полезные команды (без внешних API)
        self.tg_application.add_handler(CommandHandler("info", self.tg_cmd_info))
        self.tg_application.add_handler(CommandHandler("holidays", self.tg_cmd_holidays))
        self.tg_application.add_handler(CommandHandler("fact", self.tg_cmd_fact))
        self.tg_application.add_handler(CommandHandler("wisdom", self.tg_cmd_wisdom))
        self.tg_application.add_handler(CommandHandler("population", self.tg_cmd_population))
        self.tg_application.add_handler(CommandHandler("bitcoin", self.tg_cmd_bitcoin))
        
        # Закладки и награды
        self.tg_application.add_handler(CommandHandler("bookmark", self.tg_cmd_add_bookmark))
        self.tg_application.add_handler(CommandHandler("bookmarks", self.tg_cmd_bookmarks))
        self.tg_application.add_handler(CommandHandler("award", self.tg_cmd_add_award))
        self.tg_application.add_handler(CommandHandler("awards", self.tg_cmd_awards))
        
        # Интерактивные кнопки
        self.tg_application.add_handler(CallbackQueryHandler(self.tg_button_callback))
        
        # Обработка сообщений
        self.tg_application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.tg_handle_message))
        self.tg_application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, self.tg_handle_new_members))
        
        logger.info("✅ Telegram обработчики зарегистрированы")
    
    # ===================== TELEGRAM КОМАНДЫ =====================
    async def tg_cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        
        db.get_user('tg', platform_id, user.username or "", user.first_name, user.last_name or "")
        db.update_activity('tg', platform_id)
        
        text = (
            f"╔══════════════════════════════╗\n"
            f"║   ⚔️ **СПЕКТР БОТ** ⚔️       ║\n"
            f"╚══════════════════════════════╝\n\n"
            f"🌟 **Привет, {user.first_name}!**\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**ОСНОВНЫЕ КОМАНДЫ**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 /profile - твой профиль\n"
            f"👾 /boss - битва с боссом\n"
            f"💰 /shop - магазин\n"
            f"💎 /donate - привилегии\n"
            f"📊 /top - топ игроков\n"
            f"👥 /players - онлайн\n"
            f"📚 /help - все команды\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👑 Владелец: {OWNER_USERNAME_TG}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━"
        )
        
        keyboard = [
            [InlineKeyboardButton("👤 Профиль", callback_data="profile"),
             InlineKeyboardButton("👾 Босс", callback_data="boss")],
            [InlineKeyboardButton("💰 Магазин", callback_data="shop"),
             InlineKeyboardButton("💎 Привилегии", callback_data="donate")],
            [InlineKeyboardButton("📊 Топ", callback_data="top"),
             InlineKeyboardButton("👥 Онлайн", callback_data="players")],
            [InlineKeyboardButton("📚 Команды", callback_data="help"),
             InlineKeyboardButton("📖 Правила", callback_data="rules")],
            [InlineKeyboardButton("🎮 Игры", callback_data="games")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def tg_cmd_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        db.update_activity('tg', platform_id)
        
        keyboard = [
            [InlineKeyboardButton("👤 Профиль", callback_data="profile"),
             InlineKeyboardButton("👾 Босс", callback_data="boss")],
            [InlineKeyboardButton("💰 Магазин", callback_data="shop"),
             InlineKeyboardButton("💎 Привилегии", callback_data="donate")],
            [InlineKeyboardButton("📊 Топ", callback_data="top"),
             InlineKeyboardButton("👥 Онлайн", callback_data="players")],
            [InlineKeyboardButton("📚 Команды", callback_data="help"),
             InlineKeyboardButton("📖 Правила", callback_data="rules")],
            [InlineKeyboardButton("🎮 Игры", callback_data="games"),
             InlineKeyboardButton("📌 Закладки", callback_data="bookmarks_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🎮 **ГЛАВНОЕ МЕНЮ**\n\nВыберите раздел:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def tg_cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        db.update_activity('tg', platform_id)
        
        text = (
            "📚 **ВСЕ КОМАНДЫ БОТА**\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**ОСНОВНЫЕ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/start - запуск бота\n"
            "/menu - главное меню\n"
            "/help - эта справка\n"
            "/profile - твой профиль\n"
            "/whoami - информация о себе\n"
            "/top - топ игроков\n"
            "/players - количество игроков\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**БИТВА С БОССОМ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/boss - информация о боссе\n"
            "/boss_fight [id] - ударить босса\n"
            "/regen - восстановить здоровье\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**ЭКОНОМИКА**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/shop - магазин\n"
            "/donate - привилегии\n"
            "/pay [ник] [сумма] - перевести монеты\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**ИГРЫ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/rr - русская рулетка\n"
            "/ttt - крестики-нолики 3D\n"
            "/mafia - мафия\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**ПОЛЕЗНОЕ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/info [событие] - правдивость события\n"
            "/holidays - праздники сегодня\n"
            "/fact - случайный факт\n"
            "/wisdom - мудрая цитата\n"
            "/population - население Земли\n"
            "/bitcoin - курс биткоина\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**ЗАКЛАДКИ И НАГРАДЫ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/bookmark [описание] - создать закладку\n"
            "/bookmarks - список закладок\n"
            "/award [ник] [название] - дать награду (админ)\n"
            "/awards - список наград\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**АДМИН-КОМАНДЫ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/mute [ник] [время] [причина] - мут\n"
            "/unmute [ник] - снять мут\n"
            "/warn [ник] [причина] - предупреждение\n"
            "/ban [ник] [время] [причина] - бан\n"
            "/unban [ник] - разбан\n"
            "/banlist - список банов\n"
            "/mutelist - список мутов\n"
            "/warnlist - список варнов\n"
            "/set_rules [текст] - установить правила\n"
            "/rules - показать правила\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**КОМАНДЫ ПРИВИЛЕГИЙ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/cmd [привилегия] - команды доната"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def tg_cmd_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        
        user_data = db.get_user('tg', platform_id, user.username or "", user.first_name, user.last_name or "")
        db.update_activity('tg', platform_id)
        
        if db.is_banned('tg', platform_id):
            await update.message.reply_text("🚫 Вы забанены в боте.")
            return
        
        if db.is_muted('tg', platform_id):
            await update.message.reply_text("🔇 Вы замучены.")
            return
        
        # Получаем привилегию
        privilege = user_data.get('privilege', 'user')
        privilege_emoji = "👑" if privilege == 'создатель' else "🛡" if privilege in ['модератор', 'оператор'] else "🌟" if privilege == 'вип' else "💎" if privilege == 'премиум' else "👤"
        
        # Получаем последнюю активность
        last_activity = "Неизвестно"
        if user_data.get('last_activity'):
            last = datetime.datetime.fromisoformat(user_data['last_activity'])
            delta = datetime.datetime.now() - last
            if delta.days > 0:
                last_activity = f"{delta.days} дн назад"
            elif delta.seconds > 3600:
                last_activity = f"{delta.seconds // 3600} ч назад"
            else:
                last_activity = f"{delta.seconds // 60} мин назад"
        
        # Получаем первое появление
        first_seen = "Неизвестно"
        if user_data.get('first_seen'):
            first = datetime.datetime.fromisoformat(user_data['first_seen'])
            delta = datetime.datetime.now() - first
            years = delta.days // 365
            months = (delta.days % 365) // 30
            days = delta.days % 30
            first_seen = f"{first.strftime('%d.%m.%Y')} ({years} г {months} мес {days} дн)"
        
        text = (
            f"╔══════════════════════════════╗\n"
            f"║   👤 **ПРОФИЛЬ ИГРОКА**      ║\n"
            f"╚══════════════════════════════╝\n\n"
            
            f"**{user_data.get('nickname') or user.first_name}** {privilege_emoji}\n"
            f"ID: {user.id}\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**РЕСУРСЫ**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🪙 Монеты: {user_data['coins']:,}\n"
            f"💎 Алмазы: {user_data['diamonds']:,}\n"
            f"💀 Черепки: {user_data['rr_money']}\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**ХАРАКТЕРИСТИКИ**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"❤️ Здоровье: {user_data['health']}/{user_data['max_health']}\n"
            f"⚔️ Урон: {user_data['damage']}\n"
            f"⚡ Энергия: {user_data['energy']}\n"
            f"📊 Уровень: {user_data['level']}\n"
            f"👾 Боссов убито: {user_data['boss_kills']}\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**СТАТИСТИКА ИГР**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔪 Мафия: {user_data['mafia_wins']}/{user_data['mafia_games']}\n"
            f"✊ КНБ: {user_data['rps_wins']}-{user_data['rps_losses']}-{user_data['rps_draws']}\n"
            f"🎰 Казино: {user_data['casino_wins']}-{user_data['casino_losses']}\n"
            f"⭕ TTT: {user_data['ttt_wins']}-{user_data['ttt_losses']}-{user_data['ttt_draws']}\n"
            f"💣 Рулетка: {user_data['rr_wins']}-{user_data['rr_losses']}\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**АКТИВНОСТЬ**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📝 Сообщений: {user_data['messages_count']}\n"
            f"⌨️ Команд: {user_data['commands_used']}\n"
            f"⭐ Репутация: {user_data['reputation']}\n"
            f"⏱ Последний визит: {last_activity}\n"
            f"📅 Первое появление: {first_seen}"
        )
        
        if user_data.get('description'):
            text += f"\n\n📝 **О себе:** {user_data['description']}"
        
        keyboard = [
            [InlineKeyboardButton("🏅 Награды", callback_data="awards")],
            [InlineKeyboardButton("🔙 Назад", callback_data="menu_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def tg_cmd_whoami(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        
        user_data = db.get_user('tg', platform_id, user.username or "", user.first_name, user.last_name or "")
        
        # Получаем привилегию
        privilege = user_data.get('privilege', 'user')
        privilege_emoji = "👑" if privilege == 'создатель' else "🛡" if privilege in ['модератор', 'оператор'] else "🌟" if privilege == 'вип' else "💎" if privilege == 'премиум' else "👤"
        
        # Получаем награды
        awards = db.get_awards('tg', platform_id)
        awards_text = ""
        if awards:
            awards_text = "\n🏅 Награды:\n"
            for award in awards[:3]:
                awards_text += f"   • {award[3]}\n"
        
        # Получаем первое появление
        first_seen = "Неизвестно"
        if user_data.get('first_seen'):
            first = datetime.datetime.fromisoformat(user_data['first_seen'])
            delta = datetime.datetime.now() - first
            years = delta.days // 365
            months = (delta.days % 365) // 30
            days = delta.days % 30
            first_seen = f"{first.strftime('%d.%m.%Y')} ({years} г {months} мес {days} дн)"
        
        # Получаем последнюю активность
        last_activity = "Неизвестно"
        if user_data.get('last_activity'):
            last = datetime.datetime.fromisoformat(user_data['last_activity'])
            delta = datetime.datetime.now() - last
            if delta.days > 0:
                last_activity = f"{delta.days} дн назад"
            elif delta.seconds > 3600:
                last_activity = f"{delta.seconds // 3600} ч назад"
            else:
                last_activity = f"{delta.seconds // 60} мин назад"
        
        text = (
            f"Это [{user.id}|{user.first_name}]\n"
            f"{privilege_emoji} [{user_data['level']}] Ранг: {privilege.upper() if privilege != 'user' else 'Пользователь'}\n"
            f"Репутация: ✨ {user_data['reputation']} | ➕ {user_data['reputation_given']}\n"
            f"Первое появление: {first_seen}\n"
            f"Последний актив: {last_activity}\n"
            f"Актив (д|н|м|весь): {user_data['messages_count']} | {user_data['commands_used']} | {user_data['games_played']} | {delta.days if 'delta' in locals() else 0}"
            f"{awards_text}"
        )
        
        keyboard = [
            [InlineKeyboardButton("🏅 Награды", callback_data="awards")],
            [InlineKeyboardButton("🔙 Назад", callback_data="menu_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def tg_cmd_top(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        top_coins = db.get_top("coins", 10)
        top_level = db.get_top("level", 10)
        top_boss = db.get_top("boss_kills", 10)
        
        text = (
            f"╔══════════════════════════════╗\n"
            f"║    🏆 **ТОП ИГРОКОВ**        ║\n"
            f"╚══════════════════════════════╝\n\n"
        )
        
        text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "💰 **ПО МОНЕТАМ**\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        for i, (username, first_name, value) in enumerate(top_coins, 1):
            name = first_name or username or f"Игрок {i}"
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} {name} — {value:,} 🪙\n"
        
        text += "\n━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "📊 **ПО УРОВНЮ**\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        for i, (username, first_name, value) in enumerate(top_level, 1):
            name = first_name or username or f"Игрок {i}"
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} {name} — {value} ур.\n"
        
        text += "\n━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "👾 **ПО УБИЙСТВУ БОССОВ**\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        for i, (username, first_name, value) in enumerate(top_boss, 1):
            name = first_name or username or f"Игрок {i}"
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} {name} — {value} боссов\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def tg_cmd_players(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        count = db.get_player_count()
        await update.message.reply_text(f"👥 **Активных игроков:** {count}", parse_mode='Markdown')
    
    async def tg_cmd_boss(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        
        user_data = db.get_user('tg', platform_id, user.username or "", user.first_name, user.last_name or "")
        db.update_activity('tg', platform_id)
        
        boss = db.get_boss()
        
        if not boss:
            await update.message.reply_text("👾 Все боссы повержены! Ожидайте возрождения...")
            return
        
        player_damage = user_data['damage'] * (1 + user_data['level'] * 0.1)
        
        text = (
            f"╔══════════════════════════════╗\n"
            f"║   👾 **БИТВА С БОССОМ**      ║\n"
            f"╚══════════════════════════════╝\n\n"
            
            f"🔥 **{boss['boss_name']}**\n"
            f"Уровень: {boss['boss_level']}\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**ХАРАКТЕРИСТИКИ БОССА**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💀 Здоровье: {boss['boss_health']} / {boss['boss_max_health']} HP\n"
            f"⚔️ Урон: {boss['boss_damage']} HP\n"
            f"💰 Награда: {boss['boss_reward']} 🪙\n\n"
            
            f"**ТВОИ ХАРАКТЕРИСТИКИ**\n"
            f"❤️ Здоровье: {user_data['health']} HP\n"
            f"🗡 Урон: {player_damage:.1f} ({user_data['damage']} базовый)\n"
            f"📊 Сила: {((player_damage / boss['boss_damage']) * 100):.1f}%\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**ДЕЙСТВИЯ**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👊 /boss_fight {boss['id']} - ударить босса\n"
            f"➕ /regen - восстановить здоровье"
        )
        
        keyboard = [
            [InlineKeyboardButton("👊 Ударить", callback_data=f"boss_fight_{boss['id']}"),
             InlineKeyboardButton("➕ Регенерация", callback_data="regen")],
            [InlineKeyboardButton("🔙 Назад", callback_data="menu_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def tg_cmd_boss_fight(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        
        if not context.args:
            await update.message.reply_text("❌ Использование: /boss_fight [id]")
            return
        
        try:
            boss_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ Неправильный ID")
            return
        
        user_data = db.get_user('tg', platform_id, user.username or "", user.first_name, user.last_name or "")
        db.update_activity('tg', platform_id)
        
        if user_data['health'] <= 0:
            await update.message.reply_text("💀 У вас нет здоровья! Используйте /regen")
            return
        
        if user_data['energy'] < 5:
            await update.message.reply_text("⚡ Недостаточно энергии! Нужно 5 ⚡")
            return
        
        db.add_coins('tg', platform_id, -5, "energy")
        
        player_damage = int(user_data['damage'] * (1 + user_data['level'] * 0.1))
        boss = db.get_boss()
        
        if not boss or boss['id'] != boss_id:
            await update.message.reply_text("❌ Босс не найден или уже повержен")
            return
        
        killed, health_left = db.damage_boss(boss_id, player_damage)
        db.damage_user('tg', platform_id, boss['boss_damage'])
        
        text = f"⚔️ **БИТВА С БОССОМ** ⚔️\n\n"
        text += f"**{boss['boss_name']}**\n\n"
        text += f"▫️ **Твой урон:** {player_damage} HP\n"
        text += f"▫️ **Урон босса:** {boss['boss_damage']} HP\n\n"
        
        if killed:
            reward = boss['boss_reward']
            db.add_coins('tg', platform_id, reward, "coins")
            db.add_boss_kill('tg', platform_id)
            db.add_exp('tg', platform_id, boss['boss_level'] * 10)
            
            text += f"🎉 **БОСС ПОВЕРЖЕН!**\n"
            text += f"💰 **Награда:** {reward} 🪙\n"
            text += f"✨ **Опыт:** +{boss['boss_level'] * 10}"
        else:
            text += f"👾 **Босс еще жив!**\n"
            text += f"💀 **Осталось:** {health_left} HP"
        
        user_data = db.get_user('tg', platform_id)
        if user_data['health'] <= 0:
            text += f"\n\n💀 **Ты погиб в бою!** Используй /regen для восстановления."
        
        keyboard = [[InlineKeyboardButton("🔙 К боссу", callback_data="boss")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def tg_cmd_regen(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        
        user_data = db.get_user('tg', platform_id, user.username or "", user.first_name, user.last_name or "")
        db.update_activity('tg', platform_id)
        
        if user_data['health'] < user_data['max_health']:
            heal_amount = user_data['max_health'] - user_data['health']
            db.heal_user('tg', platform_id, heal_amount)
            
            await update.message.reply_text(
                f"➕ **РЕГЕНЕРАЦИЯ**\n\n"
                f"❤️ Здоровье восстановлено!\n"
                f"Текущее здоровье: {user_data['max_health']}/{user_data['max_health']}"
            )
        else:
            await update.message.reply_text("❤️ У тебя уже полное здоровье!")
    
    async def tg_cmd_shop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        db.update_activity('tg', platform_id)
        
        text = (
            "💰 **МАГАЗИН «СПЕКТР»**\n\n"
            
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
            "⚡ **ЭНЕРГИЯ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ Энергетик — 30 🪙 (⚡+20)\n"
            "▫️ Батарейка — 80 🪙 (⚡+50)\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "💎 **ВАЛЮТА**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ Алмаз — 100 🪙 (💎+1)\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**ПРЕДМЕТЫ ДЛЯ РУЛЕТКИ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ Монета Демона — 500 🪙\n"
            "▫️ Кровавый Глаз — 300 🪙\n"
            "▫️ Маска Клоуна — 1000 🪙\n\n"
            
            "🛒 Купить: /buy [название]"
        )
        
        keyboard = [
            [InlineKeyboardButton("💊 Зелья", callback_data="buy_potions"),
             InlineKeyboardButton("⚔️ Оружие", callback_data="buy_weapons")],
            [InlineKeyboardButton("⚡ Энергия", callback_data="buy_energy"),
             InlineKeyboardButton("💎 Алмазы", callback_data="buy_diamonds")],
            [InlineKeyboardButton("🎲 Предметы рулетки", callback_data="buy_rr_items"),
             InlineKeyboardButton("🔙 Назад", callback_data="menu_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def tg_cmd_donate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        db.update_activity('tg', platform_id)
        
        text = "💎 **ПРИВИЛЕГИИ «СПЕКТР»** 💎\n\n"
        
        privileges = [
            ("🌟 Вип", 5000, 30, ["/regen x2", "/boss_fight x2"]),
            ("💎 Премиум", 15000, 30, ["/regen x3", "/boss_fight x3", "/heal_all"]),
            ("👑 Лорд", 30000, 30, ["/god_mode", "/boss_instant"]),
            ("⚡ Ультра", 50000, 60, ["/super_attack", "/boss_double"]),
            ("🏆 Легенда", 100000, 90, ["/legendary_skill"]),
            ("🌌 Эврольд", 200000, 180, ["/cosmic_power"]),
            ("👾 Властелин", 500000, 365, ["/master_control"]),
            ("🗿 Титан", 1000000, 365, ["/titan_strike"]),
            ("🤖 Терминатор", 2000000, 365, ["/terminate"]),
            ("🔮 Маг", 75000, 60, ["/spell", "/magic_shield"])
        ]
        
        for name, price, days, commands in privileges:
            text += f"{name}\n"
            text += f"└ 💰 Цена: {price} 🪙\n"
            text += f"└ 📅 Длительность: {days} дн\n"
            for cmd in commands:
                text += f"└ {cmd}\n"
            text += "\n"
        
        text += "👑 **АДМИН-ПРИВИЛЕГИИ**\n"
        text += "модератор, оператор, анти-грифер, хелпер, создатель\n\n"
        text += f"💳 Приобрести: напишите {OWNER_USERNAME_TG}"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="menu_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def tg_cmd_pay(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /pay [ник] [сумма]")
            return
        
        target_name = context.args[0]
        try:
            amount = int(context.args[1])
        except:
            await update.message.reply_text("❌ Сумма должна быть числом")
            return
        
        user = update.effective_user
        platform_id = str(user.id)
        
        user_data = db.get_user('tg', platform_id)
        
        if amount <= 0:
            await update.message.reply_text("❌ Сумма должна быть положительной")
            return
        
        if user_data['coins'] < amount:
            await update.message.reply_text(f"❌ Недостаточно монет! У вас {user_data['coins']} 🪙")
            return
        
        target_user = db.get_user_by_username('tg', target_name)
        
        if not target_user:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        target_id = target_user[2]
        
        success, message = db.transfer_money('tg', platform_id, 'tg', target_id, amount, "coins")
        
        if success:
            await update.message.reply_text(f"✅ {message}\nПолучатель: {target_user[4]}")
            
            try:
                await context.bot.send_message(
                    chat_id=int(target_id),
                    text=f"💰 {user.first_name} перевел вам {amount} 🪙!"
                )
            except:
                pass
        else:
            await update.message.reply_text(f"❌ {message}")
    
    async def tg_cmd_privilege_commands(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(
                "❌ Укажите привилегию:\n"
                "/cmd вип\n"
                "/cmd премиум\n"
                "/cmd лорд\n"
                "/cmd ультра\n"
                "/cmd модератор\n"
                "/cmd оператор\n"
                "/cmd создатель"
            )
            return
        
        privilege = context.args[0].lower()
        
        commands = {
            "вип": ["/regen (кулдаун 3 мин)", "/boss_fight x2"],
            "премиум": ["/regen (кулдаун 1 мин)", "/boss_fight x3", "/heal_all"],
            "лорд": ["/god_mode", "/boss_instant"],
            "ультра": ["/super_attack", "/boss_double"],
            "модератор": ["/mute", "/unmute", "/warn", "/banlist", "/mutelist", "/warnlist"],
            "оператор": ["/ban", "/unban", "/give", "/clear", "/set_rules"],
            "создатель": ["/global_ban", "/system", "/set_privilege"]
        }
        
        if privilege not in commands:
            await update.message.reply_text("❌ Неизвестная привилегия")
            return
        
        text = f"**КОМАНДЫ {privilege.upper()}**\n\n"
        for cmd in commands[privilege]:
            text += f"▫️ {cmd}\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def tg_cmd_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = str(update.effective_chat.id)
        
        db.cursor.execute("SELECT rules FROM group_settings WHERE chat_id = ? AND platform = 'tg'", (chat_id,))
        result = db.cursor.fetchone()
        rules = result[0] if result else "Правила не установлены. Админ может установить их через /set_rules"
        
        await update.message.reply_text(f"📖 **ПРАВИЛА ЧАТА**\n\n{rules}", parse_mode='Markdown')
    
    async def tg_cmd_set_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_id = str(update.effective_chat.id)
        
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        if chat_member.status not in ['creator', 'administrator'] and not db.has_privilege('tg', str(user_id), 'создатель'):
            await update.message.reply_text("❌ Только администраторы могут устанавливать правила")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Использование: /set_rules [текст правил]")
            return
        
        rules = " ".join(context.args)
        
        db.cursor.execute('''
            INSERT OR REPLACE INTO group_settings (chat_id, platform, rules)
            VALUES (?, ?, ?)
        ''', (chat_id, 'tg', rules))
        db.conn.commit()
        
        await update.message.reply_text(f"✅ Правила установлены!")
    
    # ===================== АДМИН КОМАНДЫ =====================
    async def tg_cmd_mute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        
        if not db.has_privilege('tg', user_id, 'модератор') and not db.has_privilege('tg', user_id, 'создатель'):
            await update.message.reply_text("❌ Недостаточно прав")
            return
        
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /mute [ник] [время] [причина]")
            return
        
        target_name = context.args[0]
        try:
            minutes = int(context.args[1])
        except:
            await update.message.reply_text("❌ Время должно быть числом (минуты)")
            return
        
        reason = " ".join(context.args[2:]) if len(context.args) > 2 else "Нарушение"
        
        target_user = db.get_user_by_username('tg', target_name)
        
        if not target_user:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        target_id = target_user[2]
        target_username = target_user[3] or target_user[4]
        
        db.mute_user('tg', target_id, target_username, minutes, reason, update.effective_user.id, update.effective_user.first_name)
        
        await update.message.reply_text(
            f"🔇 **Пользователь замучен**\n\n"
            f"👤 {target_username}\n"
            f"⏱ Время: {minutes} мин\n"
            f"💬 Причина: {reason}"
        )
        
        try:
            await context.bot.send_message(
                chat_id=int(target_id),
                text=f"🔇 Вы замучены на {minutes} минут.\nПричина: {reason}"
            )
        except:
            pass
    
    async def tg_cmd_unmute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        
        if not db.has_privilege('tg', user_id, 'модератор') and not db.has_privilege('tg', user_id, 'создатель'):
            await update.message.reply_text("❌ Недостаточно прав")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Использование: /unmute [ник]")
            return
        
        target_name = context.args[0]
        
        target_user = db.get_user_by_username('tg', target_name)
        
        if not target_user:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        target_id = target_user[2]
        
        db.unmute_user('tg', target_id)
        
        await update.message.reply_text(f"✅ Мут снят с {target_name}")
        
        try:
            await context.bot.send_message(
                chat_id=int(target_id),
                text="✅ Ваш мут снят"
            )
        except:
            pass
    
    async def tg_cmd_warn(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        
        if not db.has_privilege('tg', user_id, 'модератор') and not db.has_privilege('tg', user_id, 'создатель'):
            await update.message.reply_text("❌ Недостаточно прав")
            return
        
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /warn [ник] [причина]")
            return
        
        target_name = context.args[0]
        reason = " ".join(context.args[1:])
        
        target_user = db.get_user_by_username('tg', target_name)
        
        if not target_user:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        target_id = target_user[2]
        target_username = target_user[3] or target_user[4]
        
        warns = db.add_warn('tg', target_id, target_username, reason, update.effective_user.id, update.effective_user.first_name)
        
        await update.message.reply_text(
            f"⚠️ **Предупреждение выдано**\n\n"
            f"👤 {target_username}\n"
            f"⚠️ Варнов: {warns}/3\n"
            f"💬 Причина: {reason}"
        )
        
        if warns >= 3:
            db.mute_user('tg', target_id, target_username, 1440, "3 предупреждения", update.effective_user.id, update.effective_user.first_name)
            await update.message.reply_text(f"⚠️ Пользователь получил 3 варна и замучен на 24 часа!")
        
        try:
            await context.bot.send_message(
                chat_id=int(target_id),
                text=f"⚠️ Вам выдано предупреждение ({warns}/3)\nПричина: {reason}"
            )
        except:
            pass
    
    async def tg_cmd_ban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        
        if not db.has_privilege('tg', user_id, 'оператор') and not db.has_privilege('tg', user_id, 'создатель'):
            await update.message.reply_text("❌ Недостаточно прав")
            return
        
        if len(context.args) < 3:
            await update.message.reply_text("❌ Использование: /ban [ник] [время] [причина]")
            return
        
        target_name = context.args[0]
        duration = context.args[1]
        reason = " ".join(context.args[2:])
        
        target_user = db.get_user_by_username('tg', target_name)
        
        if not target_user:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        target_id = target_user[2]
        target_username = target_user[3] or target_user[4]
        
        db.ban_user('tg', target_id, target_username, reason, duration, update.effective_user.id, update.effective_user.first_name)
        
        await update.message.reply_text(
            f"🚫 **Пользователь забанен**\n\n"
            f"👤 {target_username}\n
⏱ Срок: {duration}\n"
            f"💬 Причина: {reason}"
        )
        
        try:
            await context.bot.send_message(
                chat_id=int(target_id),
                text=f"🚫 Вы забанены.\nСрок: {duration}\nПричина: {reason}"
            )
        except:
            pass
    
    async def tg_cmd_unban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        
        if not db.has_privilege('tg', user_id, 'оператор') and not db.has_privilege('tg', user_id, 'создатель'):
            await update.message.reply_text("❌ Недостаточно прав")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Использование: /unban [ник]")
            return
        
        target_name = context.args[0]
        
        target_user = db.get_user_by_username('tg', target_name)
        
        if not target_user:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        target_id = target_user[2]
        
        db.unban_user('tg', target_id)
        
        await update.message.reply_text(f"✅ Пользователь {target_name} разбанен")
        
        try:
            await context.bot.send_message(
                chat_id=int(target_id),
                text="✅ Вы разбанены"
            )
        except:
            pass
    
    async def tg_cmd_banlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        
        if not db.has_privilege('tg', user_id, 'модератор') and not db.has_privilege('tg', user_id, 'создатель'):
            await update.message.reply_text("❌ Недостаточно прав")
            return
        
        page = 1
        if context.args:
            try:
                page = int(context.args[0])
            except:
                pass
        
        bans = db.get_banned_users(page, 10)
        
        if not bans:
            await update.message.reply_text("📭 Список банов пуст")
            return
        
        text = f"🚫 **СПИСОК ЗАБАНЕННЫХ** (стр. {page})\n\n"
        
        for i, ban in enumerate(bans, 1):
            username = ban[3] or f"ID {ban[2]}"
            reason = ban[4] or "Не указана"
            banned_by = ban[6] or "Неизвестно"
            ban_date = ban[7][:10] if ban[7] else "Неизвестно"
            duration = "Навсегда" if ban[10] else ban[8]
            
            text += f"{i}. {username}\n"
            text += f"   ⏱ {duration}\n"
            text += f"   💬 {reason}\n"
            text += f"   👮 {banned_by}\n"
            text += f"   📅 {ban_date}\n\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def tg_cmd_mutelist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        
        if not db.has_privilege('tg', user_id, 'модератор') and not db.has_privilege('tg', user_id, 'создатель'):
            await update.message.reply_text("❌ Недостаточно прав")
            return
        
        page = 1
        if context.args:
            try:
                page = int(context.args[0])
            except:
                pass
        
        mutes = db.get_muted_users(page, 10)
        
        if not mutes:
            await update.message.reply_text("📭 Список мутов пуст")
            return
        
        text = f"🔇 **СПИСОК ЗАМУЧЕННЫХ** (стр. {page})\n\n"
        
        for i, mute in enumerate(mutes, 1):
            username = mute[3] or f"ID {mute[2]}"
            reason = mute[4] or "Не указана"
            muted_by = mute[6] or "Неизвестно"
            mute_date = mute[7][:10] if mute[7] else "Неизвестно"
            duration = mute[8]
            
            text += f"{i}. {username}\n"
            text += f"   ⏱ {duration}\n"
            text += f"   💬 {reason}\n"
            text += f"   👮 {muted_by}\n"
            text += f"   📅 {mute_date}\n\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def tg_cmd_warnlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        
        if not db.has_privilege('tg', user_id, 'модератор') and not db.has_privilege('tg', user_id, 'создатель'):
            await update.message.reply_text("❌ Недостаточно прав")
            return
        
        page = 1
        if context.args:
            try:
                page = int(context.args[0])
            except:
                pass
        
        warns = db.get_warned_users(page, 10)
        
        if not warns:
            await update.message.reply_text("📭 Список предупреждений пуст")
            return
        
        text = f"⚠️ **СПИСОК ПРЕДУПРЕЖДЕНИЙ** (стр. {page})\n\n"
        
        for i, warn in enumerate(warns, 1):
            username = warn[3] or f"ID {warn[2]}"
            reason = warn[4] or "Не указана"
            warned_by = warn[6] or "Неизвестно"
            warn_date = warn[7][:10] if warn[7] else "Неизвестно"
            
            text += f"{i}. {username}\n"
            text += f"   💬 {reason}\n"
            text += f"   👮 {warned_by}\n"
            text += f"   📅 {warn_date}\n\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    # ===================== РУССКАЯ РУЛЕТКА =====================
    async def tg_cmd_rr(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "💣 **РУССКАЯ РУЛЕТКА**\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**ПРАВИЛА**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "• В барабане 1-3 патрона\n"
            "• Размер барабана: 6-10 позиций\n"
            "• Игроки по очереди стреляют\n"
            "• Победитель забирает все ставки\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**МАГИЧЕСКИЕ ПРЕДМЕТЫ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🪙 Монета Демона — убирает/добавляет патрон\n"
            "👁️ Кровавый Глаз — показывает патроны\n"
            "🔄 Обратный Спин — меняет направление\n"
            "⏳ Песочные часы — пропускает ход\n"
            "🎲 Кубик Судьбы — меняет количество патронов\n"
            "🤡 Маска Клоуна — перезаряжает оружие\n"
            "👁️ Глаз Провидца — показывает текущую позицию\n"
            "🧲 Магнит Пули — сдвигает патроны\n"
            "🔎 Проклятая лупа — показывает случайный патрон\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**КОМАНДЫ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/rr_start [игроки] [ставка] - создать лобби\n"
            "/rr_join [ID] - присоединиться\n"
            "/rr_shot - сделать выстрел\n"
            "/rr_items - мои предметы"
        )
        
        keyboard = [
            [InlineKeyboardButton("🎲 Создать игру", callback_data="rr_create")],
            [InlineKeyboardButton("🔙 Назад", callback_data="games_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def tg_cmd_rr_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        platform_id = str(user.id)
        
        user_data = db.get_user('tg', platform_id)
        
        if user_data['rr_money'] < bet:
            await update.message.reply_text(f"❌ Недостаточно черепков! У тебя {user_data['rr_money']} 💀")
            return
        
        lobby_id = db.rr_create_lobby(platform_id, max_players, bet)
        
        await update.message.reply_text(
            f"💣 **ЛОББИ СОЗДАНО!**\n\n"
            f"▫️ **ID:** {lobby_id}\n"
            f"▫️ **Создатель:** {user.first_name}\n"
            f"▫️ **Игроков:** 1/{max_players}\n"
            f"▫️ **Ставка:** {bet} 💀\n\n"
            f"Присоединиться: /rr_join {lobby_id}",
            parse_mode='Markdown'
        )
    
    async def tg_cmd_rr_join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Укажи ID лобби: /rr_join 1")
            return
        
        try:
            lobby_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ Неправильный ID")
            return
        
        user = update.effective_user
        platform_id = str(user.id)
        
        if db.rr_join_lobby(lobby_id, platform_id):
            await update.message.reply_text(f"✅ Ты присоединился к лобби {lobby_id}!")
        else:
            await update.message.reply_text("❌ Не удалось присоединиться")
    
    async def tg_cmd_rr_shot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        
        db.cursor.execute(
            "SELECT * FROM rr_games WHERE players LIKE ? AND phase = 'playing'",
            (f'%{platform_id}%',)
        )
        game = db.cursor.fetchone()
        
        if not game:
            await update.message.reply_text("❌ Ты не участвуешь в активной игре")
            return
        
        columns = [description[0] for description in db.cursor.description]
        game_dict = dict(zip(columns, game))
        
        result = db.rr_make_shot(game_dict['id'], platform_id)
        
        if result == "not_your_turn":
            await update.message.reply_text("❌ Сейчас не твой ход")
        elif result == "dead":
            await update.message.reply_text("💀 **БАХ!** Ты погиб...")
        elif result == "alive":
            await update.message.reply_text("✅ **ЩЕЛК!** Ты выжил!")
        elif isinstance(result, tuple) and result[0] == "game_over":
            winner_id = result[1]
            winner_data = await context.bot.get_chat(int(winner_id))
            await update.message.reply_text(
                f"🏆 **ИГРА ОКОНЧЕНА!**\n\n"
                f"Победитель: {winner_data.first_name}",
                parse_mode='Markdown'
            )
    
    async def tg_cmd_rr_items(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        
        items = db.rr_get_items(platform_id)
        
        if not items:
            await update.message.reply_text("📦 У тебя нет предметов для русской рулетки")
            return
        
        text = "📦 **ТВОИ ПРЕДМЕТЫ**\n\n"
        
        for item in items:
            text += f"▫️ **{item[2]}** x{item[4]}\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    # ===================== КРЕСТИКИ-НОЛИКИ 3D =====================
    async def tg_cmd_ttt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "⭕ **КРЕСТИКИ-НОЛИКИ 3D**\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**ПРАВИЛА**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "• В каждой клетке поля находится ещё одно поле\n"
            "• Нужно выиграть на 3 малых полях в ряд\n"
            "• Победа на малом поле делает его вашим\n"
            "• Игра продолжается пока кто-то не победит\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**КОМАНДЫ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/ttt_challenge [ник] - вызвать игрока\n"
            "/ttt_move [клетка] - сделать ход (клетка: ряд_колонка_подряд_подколонка, например 1_1_2_2)"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="games_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def tg_cmd_ttt_challenge(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Использование: /ttt_challenge [ник]")
            return
        
        target_name = context.args[0]
        user = update.effective_user
        platform_id = str(user.id)
        
        target_user = db.get_user_by_username('tg', target_name)
        
        if not target_user:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        target_id = target_user[2]
        
        game_id = db.ttt_create_game(platform_id, target_id)
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Принять", callback_data=f"ttt_accept_{game_id}"),
                InlineKeyboardButton("❌ Отклонить", callback_data=f"ttt_decline_{game_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await context.bot.send_message(
                chat_id=int(target_id),
                text=f"⭕ {user.first_name} вызывает тебя на игру в крестики-нолики 3D!\n\nСогласен?",
                reply_markup=reply_markup
            )
            await update.message.reply_text("✅ Запрос отправлен!")
        except:
            await update.message.reply_text("❌ Не удалось отправить запрос")
    
    async def tg_cmd_ttt_move(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 1:
            await update.message.reply_text("❌ Использование: /ttt_move [клетка] (например 1_1_2_2)")
            return
        
        try:
            parts = context.args[0].split('_')
            if len(parts) != 4:
                raise ValueError
            main_row, main_col, sub_row, sub_col = map(int, parts)
        except:
            await update.message.reply_text("❌ Неправильный формат. Используй: ряд_колонка_подряд_подколонка (1_1_2_2)")
            return
        
        user = update.effective_user
        platform_id = str(user.id)
        
        db.cursor.execute(
            "SELECT * FROM ttt_games WHERE (player_x = ? OR player_o = ?) AND status = 'playing'",
            (platform_id, platform_id)
        )
        game = db.cursor.fetchone()
        
        if not game:
            await update.message.reply_text("❌ У тебя нет активной игры")
            return
        
        columns = [description[0] for description in db.cursor.description]
        game_dict = dict(zip(columns, game))
        
        result = db.ttt_make_move(game_dict['id'], platform_id, main_row-1, main_col-1, sub_row-1, sub_col-1)
        
        if result == "not_your_turn":
            await update.message.reply_text("❌ Сейчас не твой ход")
        elif result == "cell_occupied":
            await update.message.reply_text("❌ Эта клетка уже занята")
        elif result and result['status'] == 'finished':
            winner = "Ты" if result['winner'] == platform_id else "Противник"
            await update.message.reply_text(f"🏆 **Игра окончена!**\n\nПобедитель: {winner}")
        else:
            await update.message.reply_text("✅ Ход сделан!")
    
    # ===================== МАФИЯ =====================
    async def tg_cmd_mafia(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "🔪 **МАФИЯ**\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**ПРАВИЛА**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "• Игроки делятся на мафию и мирных\n"
            "• Ночью мафия убивает, днем все обсуждают\n"
            "• Цель мафии - убить всех мирных\n"
            "• Цель мирных - найти мафию\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**ФАЗЫ ИГРЫ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🌙 **Ночь** - мафия выбирает жертву\n"
            "☀️ **День** - обсуждение и голосование\n"
            "⚰️ **Смерть** - игрок покидает игру\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**КОМАНДЫ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/mafia_create - создать игру\n"
            "/mafia_join [ID] - присоединиться\n"
            "/mafia_start - начать игру"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="games_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def tg_cmd_mafia_create(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        
        game_id = db.mafia_create_game(platform_id)
        
        await update.message.reply_text(
            f"🔪 **ИГРА МАФИЯ СОЗДАНА!**\n\n"
            f"▫️ **ID игры:** {game_id}\n"
            f"▫️ **Создатель:** {user.first_name}\n"
            f"▫️ **Игроков:** 1/10\n\n"
            f"Присоединиться: /mafia_join {game_id}",
            parse_mode='Markdown'
        )
    
    async def tg_cmd_mafia_join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Укажи ID игры: /mafia_join 1")
            return
        
        try:
            game_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ Неправильный ID")
            return
        
        user = update.effective_user
        platform_id = str(user.id)
        
        if db.mafia_join_game(game_id, platform_id):
            await update.message.reply_text(f"✅ Ты присоединился к игре {game_id}!")
        else:
            await update.message.reply_text("❌ Не удалось присоединиться")
    
    async def tg_cmd_mafia_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        
        db.cursor.execute("SELECT * FROM mafia_games WHERE creator_id = ? AND status = 'waiting'", (platform_id,))
        game = db.cursor.fetchone()
        
        if not game:
            await update.message.reply_text("❌ У тебя нет созданной игры")
            return
        
        columns = [description[0] for description in db.cursor.description]
        game_dict = dict(zip(columns, game))
        
        roles = db.mafia_start_game(game_dict['id'])
        
        if roles == "not_enough_players":
            await update.message.reply_text("❌ Недостаточно игроков (нужно минимум 4)")
            return
        
        players = json.loads(game_dict['players'])
        
        for player_id in players:
            role = roles[player_id]
            role_text = "🔪 Мафия" if role == 'mafia' else "👨‍🌾 Мирный"
            
            try:
                if player_id == platform_id:
                    await update.message.reply_text(f"🔪 **ИГРА НАЧАЛАСЬ!**\n\nТвоя роль: {role_text}")
                else:
                    await context.bot.send_message(
                        chat_id=int(player_id),
                        text=f"🔪 **ИГРА НАЧАЛАСЬ!**\n\nТвоя роль: {role_text}"
                    )
            except:
                pass
    
    # ===================== ПОЛЕЗНЫЕ КОМАНДЫ =====================
    async def tg_cmd_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Использование: /info [событие]")
            return
        
        event = " ".join(context.args)
        probability = random.randint(0, 100)
        
        await update.message.reply_text(
            f"📊 **ПРАВДИВОСТЬ СОБЫТИЯ**\n\n"
            f"Событие: {event}\n"
            f"Вероятность: {probability}%",
            parse_mode='Markdown'
        )
    
    async def tg_cmd_holidays(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        today = datetime.datetime.now()
        
        holidays = {
            "01-01": "🎄 Новый год",
            "01-07": "🎅 Рождество",
            "02-23": "🎖️ День защитника Отечества",
            "03-08": "🌸 Международный женский день",
            "05-01": "🌷 Праздник Весны и Труда",
            "05-09": "🎗️ День Победы",
            "06-12": "🇷🇺 День России",
            "11-04": "🤝 День народного единства"
        }
        
        date_key = today.strftime("%m-%d")
        
        if date_key in holidays:
            await update.message.reply_text(f"📅 **Сегодня:** {holidays[date_key]}", parse_mode='Markdown')
        else:
            await update.message.reply_text("📅 Сегодня нет праздников", parse_mode='Markdown')
    
    async def tg_cmd_fact(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        facts = [
            "🐝 Пчелы могут узнавать человеческие лица.",
            "🌍 В Антарктиде есть только один постоянный вид насекомых.",
            "🦑 Кальмары имеют три сердца.",
            "🐘 Слоны - единственные млекопитающие, которые не могут прыгать.",
            "🍌 Бананы технически являются ягодами.",
            "🌊 Океаны покрывают 71% поверхности Земли.",
            "🚀 Следы на Луне останутся на миллионы лет.",
            "💧 Человек может прожить без еды около месяца, но без воды только неделю.",
            "🧠 Мозг человека генерирует достаточно электричества, чтобы зажечь лампочку.",
            "👁️ Человеческий глаз может различать около 10 миллионов цветов."
        ]
        
        fact = random.choice(facts)
        
        await update.message.reply_text(f"📌 **СЛУЧАЙНЫЙ ФАКТ**\n\n{fact}", parse_mode='Markdown')
    
    async def tg_cmd_wisdom(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        quotes = [
            "🌟 Жизнь - это то, что с тобой происходит, пока ты строишь планы.",
            "💫 Будь тем изменением, которое хочешь увидеть в мире.",
            "✨ Счастье не в том, чтобы делать всегда, что хочешь, а в том, чтобы всегда хотеть того, что делаешь.",
            "⭐ Самая большая слава не в том, чтобы никогда не падать, а в том, чтобы вставать каждый раз, когда падаешь.",
            "☀️ Жизнь измеряется не количеством вдохов, а количеством моментов, от которых захватывает дух."
        ]
        
        quote = random.choice(quotes)
        
        await update.message.reply_text(f"💭 **МУДРАЯ МЫСЛЬ**\n\n{quote}", parse_mode='Markdown')
    
    async def tg_cmd_population(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        world_pop = 7_900_000_000
        
        await update.message.reply_text(
            f"🌍 **НАСЕЛЕНИЕ ЗЕМЛИ**\n\n"
            f"Примерно: {world_pop:,} человек",
            parse_mode='Markdown'
        )
    
    async def tg_cmd_bitcoin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        price_usd = random.randint(40000, 70000)
        price_rub = price_usd * 91.5
        
        await update.message.reply_text(
            f"₿ **КУРС БИТКОИНА**\n\n"
            f"USD: ${price_usd:,}\n"
            f"RUB: ₽{int(price_rub):,}",
            parse_mode='Markdown'
        )
    
    # ===================== ЗАКЛАДКИ И НАГРАДЫ =====================
    async def tg_cmd_add_bookmark(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Использование: /bookmark [описание]")
            return
        
        description = " ".join(context.args)
        user = update.effective_user
        platform_id = str(user.id)
        
        message_link = f"https://t.me/c/{str(update.effective_chat.id)[4:]}/{update.message.message_id}"
        
        db.add_bookmark('tg', platform_id, description, message_link)
        
        await update.message.reply_text(f"✅ Закладка создана: {description}")
    
    async def tg_cmd_bookmarks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        
        bookmarks = db.get_bookmarks('tg', platform_id)
        
        if not bookmarks:
            await update.message.reply_text(
                "📭 У вас нет закладок.\n\n"
                "💬 Для создания закладки используйте:\n"
                "/bookmark [описание]"
            )
            return
        
        text = "📌 **ВАШИ ЗАКЛАДКИ**\n\n"
        
        for i, bookmark in enumerate(bookmarks, 1):
            text += f"{i}. {bookmark[3]} — [ссылка]({bookmark[4]})\n"
        
        await update.message.reply_text(text, parse_mode='Markdown', disable_web_page_preview=True)
    
    async def tg_cmd_add_award(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        
        if not db.has_privilege('tg', user_id, 'создатель'):
            await update.message.reply_text("❌ Недостаточно прав")
            return
        
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /award [ник] [название награды]")
            return
        
        target_name = context.args[0]
        award_name = " ".join(context.args[1:])
        
        target_user = db.get_user_by_username('tg', target_name)
        
        if not target_user:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        target_id = target_user[2]
        
        db.add_award('tg', target_id, award_name, award_name, update.effective_user.id, update.effective_user.first_name)
        
        await update.message.reply_text(f"✅ Награда '{award_name}' выдана пользователю {target_name}")
        
        try:
            await context.bot.send_message(
                chat_id=int(target_id),
                text=f"🏅 Вам выдана награда: {award_name}"
            )
        except:
            pass
    
    async def tg_cmd_awards(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        
        awards = db.get_awards('tg', platform_id)
        
        if not awards:
            await update.message.reply_text("🏅 У вас пока нет наград")
            return
        
        text = "🏅 **ВАШИ НАГРАДЫ**\n\n"
        
        for award in awards:
            award_date = datetime.datetime.fromisoformat(award[6]).strftime("%d.%m.%Y")
            text += f"▫️ **{award[3]}** — от {award[5]} ({award_date})\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    # ===================== ОБРАБОТКА СООБЩЕНИЙ =====================
    async def tg_handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        message_text = update.message.text
        
        user_data = db.get_user('tg', platform_id, user.username or "", user.first_name, user.last_name or "")
        db.update_activity('tg', platform_id)
        db.add_message_count('tg', platform_id)
        
        if db.is_banned('tg', platform_id) or db.is_muted('tg', platform_id):
            return
        
        # Проверка на длительное молчание
        last_msg_time = self.last_activity['tg'].get(platform_id, 0)
        current_time = time.time()
        
        if last_msg_time > 0 and current_time - last_msg_time > 30 * 24 * 3600:
            await update.message.reply_text(
                f"⚡️⚡️⚡️ Святые угодники!\n"
                f"{user.first_name} заговорил после более, чем месячного молчания!!! Поприветствуйте молчуна! 👏"
            )
        
        self.last_activity['tg'][platform_id] = current_time
        
        if user_data['messages_count'] == 1:
            await update.message.reply_text(f"🌟 Добро пожаловать, {user.first_name}! Используй /help для списка команд.")
    
    async def tg_handle_new_members(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = str(update.effective_chat.id)
        
        db.cursor.execute("SELECT welcome_message FROM group_settings WHERE chat_id = ? AND platform = 'tg'", (chat_id,))
        result = db.cursor.fetchone()
        welcome = result[0] if result else "🌟 Добро пожаловать, {user}!"
        
        for member in update.message.new_chat_members:
            if member.is_bot:
                continue
            
            welcome_text = welcome.replace('{user}', f"[{member.first_name}](tg://user?id={member.id})")
            await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    # ===================== ОБРАБОТКА КНОПОК =====================
    async def tg_button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        
        # Главное меню
        if data == "profile":
            await self.tg_cmd_profile(update, context)
        elif data == "boss":
            await self.tg_cmd_boss(update, context)
        elif data == "shop":
            await self.tg_cmd_shop(update, context)
        elif data == "donate":
            await self.tg_cmd_donate(update, context)
        elif data == "top":
            await self.tg_cmd_top(update, context)
        elif data == "players":
            await self.tg_cmd_players(update, context)
        elif data == "help":
            await self.tg_cmd_help(update, context)
        elif data == "rules":
            await self.tg_cmd_rules(update, context)
        elif data == "games":
            keyboard = [
                [InlineKeyboardButton("💣 Русская рулетка", callback_data="rr"),
                 InlineKeyboardButton("⭕ Крестики-нолики 3D", callback_data="ttt")],
                [InlineKeyboardButton("🔪 Мафия", callback_data="mafia")],
                [InlineKeyboardButton("🔙 Назад", callback_data="menu_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "🎮 **ИГРЫ**\n\nВыберите игру:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        elif data == "bookmarks_menu":
            await self.tg_cmd_bookmarks(update, context)
        
        # Босс
        elif data.startswith("boss_fight_"):
            boss_id = data.split("_")[2]
            context.args = [boss_id]
            await self.tg_cmd_boss_fight(update, context)
        elif data == "regen":
            await self.tg_cmd_regen(update, context)
        
        # Магазин
        elif data == "buy_potions":
            await query.edit_message_text(
                "💊 **ЗЕЛЬЯ**\n\n"
                "▫️ Зелье здоровья — 50 🪙 (❤️+30)\n"
                "▫️ Большое зелье — 100 🪙 (❤️+70)\n\n"
                "Купить: /buy [название]"
            )
        elif data == "buy_weapons":
            await query.edit_message_text(
                "⚔️ **ОРУЖИЕ**\n\n"
                "▫️ Меч — 200 🪙 (⚔️+10)\n"
                "▫️ Легендарный меч — 500 🪙 (⚔️+30)\n\n"
                "Купить: /buy [название]"
            )
        elif data == "buy_energy":
            await query.edit_message_text(
                "⚡ **ЭНЕРГИЯ**\n\n"
                "▫️ Энергетик — 30 🪙 (⚡+20)\n"
                "▫️ Батарейка — 80 🪙 (⚡+50)\n\n"
                "Купить: /buy [название]"
            )
        elif data == "buy_diamonds":
            await query.edit_message_text(
                "💎 **АЛМАЗЫ**\n\n"
                "▫️ Алмаз — 100 🪙 (💎+1)\n\n"
                "Купить: /buy алмаз"
            )
        elif data == "buy_rr_items":
            await query.edit_message_text(
                "🎲 **ПРЕДМЕТЫ ДЛЯ РУЛЕТКИ**\n\n"
                "▫️ Монета Демона — 500 🪙\n"
                "▫️ Кровавый Глаз — 300 🪙\n"
                "▫️ Маска Клоуна — 1000 🪙\n\n"
                "Купить: /buy [название]"
            )
        
        # Игры
        elif data == "rr":
            await self.tg_cmd_rr(update, context)
        elif data == "ttt":
            await self.tg_cmd_ttt(update, context)
        elif data == "mafia":
            await self.tg_cmd_mafia(update, context)
        elif data == "rr_create":
            await query.edit_message_text(
                "💣 **СОЗДАНИЕ ИГРЫ**\n\n"
                "Используй команду:\n"
                "/rr_start [игроки] [ставка]\n\n"
                "Пример: /rr_start 4 100"
            )
        
        # Крестики-нолики
        elif data.startswith("ttt_accept_"):
            await query.edit_message_text("✅ Ты принял вызов! Игра начинается...")
        elif data.startswith("ttt_decline_"):
            await query.edit_message_text("❌ Ты отклонил вызов")
        
        # Профиль
        elif data == "awards":
            await self.tg_cmd_awards(update, context)
        
        # Навигация
        elif data == "menu_back":
            keyboard = [
                [InlineKeyboardButton("👤 Профиль", callback_data="profile"),
                 InlineKeyboardButton("👾 Босс", callback_data="boss")],
                [InlineKeyboardButton("💰 Магазин", callback_data="shop"),
                 InlineKeyboardButton("💎 Привилегии", callback_data="donate")],
                [InlineKeyboardButton("📊 Топ", callback_data="top"),
                 InlineKeyboardButton("👥 Онлайн", callback_data="players")],
                [InlineKeyboardButton("📚 Команды", callback_data="help"),
                 InlineKeyboardButton("📖 Правила", callback_data="rules")],
                [InlineKeyboardButton("🎮 Игры", callback_data="games"),
                 InlineKeyboardButton("📌 Закладки", callback_data="bookmarks_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "🎮 **ГЛАВНОЕ МЕНЮ**\n\nВыберите раздел:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        elif data == "games_menu":
            keyboard = [
                [InlineKeyboardButton("💣 Русская рулетка", callback_data="rr"),
                 InlineKeyboardButton("⭕ Крестики-нолики 3D", callback_data="ttt")],
                [InlineKeyboardButton("🔪 Мафия", callback_data="mafia"),
                 InlineKeyboardButton("🔙 Назад", callback_data="menu_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "🎮 **ИГРЫ**\n\nВыберите игру:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        elif data == "noop":
            pass
        else:
            await query.edit_message_text(
                "❌ Неизвестная команда",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="menu_back")]])
            )
    
    # ===================== VK ОБРАБОТЧИКИ =====================
    def setup_vk_handlers(self):
        if not VKBOTTLE_AVAILABLE:
            return
        
        @self.vk_bot.on.message()
        async def vk_message_handler(message: Message):
            await self.vk_handle_message(message)
        
        logger.info("✅ VK обработчики зарегистрированы")
    
    async def vk_handle_message(self, message: Message):
        # Здесь будет VK логика (можно добавить позже)
        pass
    
    # ===================== ЗАПУСК =====================
    async def run(self):
        if self.tg_application:
            await self.tg_application.initialize()
            await self.tg_application.start()
            await self.tg_application.updater.start_polling()
            logger.info("🚀 Telegram бот запущен!")
        
        if self.vk_bot and VKBOTTLE_AVAILABLE:
            asyncio.create_task(self.vk_bot.run_polling())
            logger.info("🚀 VK бот запущен!")
        
        while True:
            await asyncio.sleep(1)
    
    async def close(self):
        if self.tg_application:
            await self.tg_application.stop()
        db.close()
        logger.info("👋 Боты остановлены")

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
