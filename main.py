#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
СПЕКТР БОТ - МЕГА ВЕРСИЯ
Telegram бот с оформлением в стиле Iris
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

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from telegram.error import TelegramError

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== КОНФИГУРАЦИЯ ==========
TELEGRAM_TOKEN = "8326390250:AAEpXRnhLLLi5zUeFC39nfkHDlxR5ZFQ_yQ"
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
    def __init__(self, db_name="spectrum_bot.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
        self.migrate_tables()
        self.init_data()
        print("✅ База данных инициализирована")
    
    def create_tables(self):
        # Основная таблица пользователей
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                coins INTEGER DEFAULT 1000,
                diamonds INTEGER DEFAULT 0,
                energy INTEGER DEFAULT 100,
                level INTEGER DEFAULT 1,
                exp INTEGER DEFAULT 0,
                role TEXT DEFAULT 'user',
                warns INTEGER DEFAULT 0,
                warns_list TEXT DEFAULT '[]',
                mute_until TIMESTAMP,
                banned INTEGER DEFAULT 0,
                ban_reason TEXT,
                ban_date TIMESTAMP,
                ban_admin INTEGER,
                health INTEGER DEFAULT 100,
                armor INTEGER DEFAULT 0,
                damage INTEGER DEFAULT 10,
                boss_kills INTEGER DEFAULT 0,
                vip_until TIMESTAMP,
                premium_until TIMESTAMP,
                clan_id INTEGER DEFAULT 0,
                clan_role TEXT DEFAULT 'member',
                rps_wins INTEGER DEFAULT 0,
                rps_losses INTEGER DEFAULT 0,
                rps_draws INTEGER DEFAULT 0,
                casino_wins INTEGER DEFAULT 0,
                casino_losses INTEGER DEFAULT 0,
                cases INTEGER DEFAULT 0,
                keys INTEGER DEFAULT 0,
                gender TEXT DEFAULT 'unknown',
                nickname TEXT,
                city TEXT,
                bio TEXT,
                title TEXT,
                motto TEXT,
                citizenship INTEGER DEFAULT 0,
                achievements TEXT DEFAULT '[]',
                achievements_visible INTEGER DEFAULT 1,
                marry_id INTEGER DEFAULT 0,
                love_points INTEGER DEFAULT 0,
                children INTEGER DEFAULT 0,
                rep INTEGER DEFAULT 0,
                warns_count INTEGER DEFAULT 0,
                mutes_count INTEGER DEFAULT 0,
                bans_count INTEGER DEFAULT 0,
                last_seen TIMESTAMP,
                referrals INTEGER DEFAULT 0,
                referral_link TEXT,
                daily_streak INTEGER DEFAULT 0,
                last_daily TIMESTAMP,
                active_days INTEGER DEFAULT 0,
                active_weeks INTEGER DEFAULT 0,
                active_months INTEGER DEFAULT 0,
                total_active_days INTEGER DEFAULT 0,
                automes_enabled INTEGER DEFAULT 0,
                platform TEXT DEFAULT 'tg',
                platform_id TEXT,
                last_free_energy TIMESTAMP,
                last_weekly TIMESTAMP,
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
                voice_count INTEGER DEFAULT 0,
                photo_count INTEGER DEFAULT 0,
                sticker_count INTEGER DEFAULT 0,
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
        
        # Питомцы
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS pets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER,
                pet_name TEXT,
                pet_type TEXT,
                health INTEGER DEFAULT 100,
                max_health INTEGER DEFAULT 100,
                attack INTEGER DEFAULT 10,
                experience INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                created_at TIMESTAMP,
                FOREIGN KEY (owner_id) REFERENCES users (user_id)
            )
        ''')
        
        # Закладки
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                text TEXT,
                message_link TEXT,
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
        
        # Турниры
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
        
        # Ставки на турниры
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS bets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                tournament_id INTEGER,
                amount INTEGER,
                created_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
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
        
        # Триггеры
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS triggers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                trigger_word TEXT,
                action TEXT,
                created_by INTEGER,
                created_at TIMESTAMP
            )
        ''')
        
        # Доступ команд
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS command_access (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                command_name TEXT,
                min_rank INTEGER DEFAULT 0,
                enabled INTEGER DEFAULT 1,
                UNIQUE(chat_id, command_name)
            )
        ''')
        
        # Личный доступ команд
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS personal_access (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                user_id INTEGER,
                command_name TEXT,
                allowed INTEGER DEFAULT 1,
                UNIQUE(chat_id, user_id, command_name)
            )
        ''')
        
        # Настройки чата
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_settings (
                chat_id INTEGER PRIMARY KEY,
                title TEXT,
                description TEXT,
                rules TEXT,
                welcome_message TEXT,
                chat_link TEXT,
                autokick_enabled INTEGER DEFAULT 0,
                autokick_settings TEXT,
                chat_enabled INTEGER DEFAULT 1,
                channels_allowed INTEGER DEFAULT 0,
                join_notifications INTEGER DEFAULT 1,
                leave_notifications INTEGER DEFAULT 1,
                min_reg_days INTEGER DEFAULT 0,
                auto_join_enabled INTEGER DEFAULT 0,
                invite_limit INTEGER DEFAULT 0,
                antiraid_enabled INTEGER DEFAULT 0,
                links_allowed INTEGER DEFAULT 1,
                allowed_links TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Глобальные модераторы
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS global_moderators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                role TEXT DEFAULT 'moderator',
                added_by INTEGER,
                created_at TIMESTAMP,
                UNIQUE(user_id)
            )
        ''')
        
        # Глобальные баны
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS global_bans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                reason TEXT,
                banned_by INTEGER,
                banned_at TIMESTAMP,
                UNIQUE(user_id)
            )
        ''')
        
        # Гражданство чатов
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS citizenship (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                chat_id INTEGER,
                joined_at TIMESTAMP,
                UNIQUE(user_id, chat_id)
            )
        ''')
        
        # Подписки на пользователей
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subscriber_id INTEGER,
                subscribed_to INTEGER,
                created_at TIMESTAMP,
                UNIQUE(subscriber_id, subscribed_to)
            )
        ''')
        
        # Награды
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS rewards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                reward_name TEXT,
                reward_desc TEXT,
                awarded_by INTEGER,
                awarded_at TIMESTAMP
            )
        ''')
        
        self.conn.commit()
    
    def migrate_tables(self):
        try:
            self.cursor.execute("PRAGMA table_info(users)")
            columns = [col[1] for col in self.cursor.fetchall()]
            
            required_columns = {
                'warns_list': "ALTER TABLE users ADD COLUMN warns_list TEXT DEFAULT '[]'",
                'ban_reason': "ALTER TABLE users ADD COLUMN ban_reason TEXT",
                'ban_date': "ALTER TABLE users ADD COLUMN ban_date TIMESTAMP",
                'ban_admin': "ALTER TABLE users ADD COLUMN ban_admin INTEGER",
                'title': "ALTER TABLE users ADD COLUMN title TEXT",
                'motto': "ALTER TABLE users ADD COLUMN motto TEXT",
                'citizenship': "ALTER TABLE users ADD COLUMN citizenship INTEGER DEFAULT 0",
                'achievements': "ALTER TABLE users ADD COLUMN achievements TEXT DEFAULT '[]'",
                'achievements_visible': "ALTER TABLE users ADD COLUMN achievements_visible INTEGER DEFAULT 1",
            }
            
            for col, sql in required_columns.items():
                if col not in columns:
                    try:
                        self.cursor.execute(sql)
                        print(f"✅ Добавлена колонка: {col}")
                    except:
                        pass
            
            self.conn.commit()
        except Exception as e:
            print(f"Ошибка миграции: {e}")
    
    def init_data(self):
        self.init_bosses()
    
    def init_bosses(self):
        self.cursor.execute("SELECT * FROM bosses")
        if not self.cursor.fetchone():
            bosses_data = [
                ("🦟 Ядовитый комар", 5, 500, 15, 250, ""),
                ("🌲 Лесной тролль", 10, 1000, 25, 500, ""),
                ("🐉 Огненный дракон", 15, 2000, 40, 1000, ""),
                ("❄️ Ледяной великан", 20, 3500, 60, 2000, ""),
                ("👾 Король демонов", 25, 5000, 85, 3500, ""),
                ("💀 Бог разрушения", 30, 10000, 150, 5000, "")
            ]
            for name, level, health, damage, reward, image in bosses_data:
                self.cursor.execute('''
                    INSERT INTO bosses (boss_name, boss_level, boss_health, boss_max_health, boss_damage, boss_reward, boss_image)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (name, level, health, health, damage, reward, image))
            self.conn.commit()
            print("✅ Боссы инициализированы")
    
    def get_or_create_user(self, platform: str, platform_id: str, first_name: str = "Player") -> Dict:
        self.cursor.execute(
            "SELECT * FROM users WHERE platform = ? AND platform_id = ?",
            (platform, platform_id)
        )
        user = self.cursor.fetchone()
        
        if not user:
            role = 'owner' if (platform == 'tg' and int(platform_id) == OWNER_ID) else 'user'
            self.cursor.execute('''
                INSERT INTO users (platform, platform_id, first_name, role, referral_link, last_seen) 
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (platform, platform_id, first_name, role, f"ref_{platform}_{platform_id}_{int(time.time())}", datetime.datetime.now()))
            
            user_id = self.cursor.lastrowid
            
            self.cursor.execute('''
                INSERT INTO stats (user_id) VALUES (?)
            ''', (user_id,))
            
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
    
    def get_user_by_name(self, name_query: str) -> Optional[Dict]:
        self.cursor.execute(
            "SELECT user_id FROM users WHERE nickname = ? OR first_name LIKE ? ORDER BY last_seen DESC LIMIT 1",
            (name_query, f'%{name_query}%')
        )
        result = self.cursor.fetchone()
        if result:
            return self.get_user_by_id(result[0])
        return None
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        self.cursor.execute(
            "SELECT user_id FROM users WHERE username = ?",
            (username.replace('@', ''),)
        )
        result = self.cursor.fetchone()
        if result:
            return self.get_user_by_id(result[0])
        return None
    
    def get_players_count(self) -> int:
        self.cursor.execute("SELECT COUNT(*) FROM users")
        return self.cursor.fetchone()[0]
    
    def add_coins(self, user_id: int, coins: int):
        self.cursor.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (coins, user_id))
        self.conn.commit()
    
    def add_diamonds(self, user_id: int, amount: int):
        self.cursor.execute("UPDATE users SET diamonds = diamonds + ? WHERE user_id = ?", (amount, user_id))
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
        current_health = self.get_user_by_id(user_id).get('health', 100)
        new_health = min(100, current_health + amount)
        self.cursor.execute("UPDATE users SET health = ? WHERE user_id = ?", (new_health, user_id))
        self.conn.commit()
    
    # ========== СИСТЕМА БАНОВ И ПРЕДУПРЕЖДЕНИЙ ==========
    
    def add_warn(self, user_id: int, admin_id: int, reason: str = "Нарушение") -> Dict:
        """Выдать предупреждение"""
        user_data = self.get_user_by_id(user_id)
        warns_list = json.loads(user_data.get('warns_list', '[]'))
        
        warn_data = {
            'id': len(warns_list) + 1,
            'admin_id': admin_id,
            'reason': reason,
            'date': datetime.datetime.now().isoformat(),
            'expires': (datetime.datetime.now() + datetime.timedelta(days=30)).isoformat()
        }
        
        warns_list.append(warn_data)
        
        self.cursor.execute(
            "UPDATE users SET warns = warns + 1, warns_count = warns_count + 1, warns_list = ? WHERE user_id = ?",
            (json.dumps(warns_list), user_id)
        )
        self.conn.commit()
        
        warns_count = len(warns_list)
        
        return {
            'warn_id': warn_data['id'],
            'warns_count': warns_count,
            'warn_data': warn_data
        }
    
    def get_warns(self, user_id: int) -> List[Dict]:
        """Получить список предупреждений"""
        user_data = self.get_user_by_id(user_id)
        return json.loads(user_data.get('warns_list', '[]'))
    
    def remove_last_warn(self, user_id: int) -> Optional[Dict]:
        """Снять последнее предупреждение"""
        user_data = self.get_user_by_id(user_id)
        warns_list = json.loads(user_data.get('warns_list', '[]'))
        
        if not warns_list:
            return None
        
        removed = warns_list.pop()
        
        self.cursor.execute(
            "UPDATE users SET warns = warns - 1, warns_list = ? WHERE user_id = ?",
            (json.dumps(warns_list), user_id)
        )
        self.conn.commit()
        
        return removed
    
    def remove_warn_by_number(self, user_id: int, warn_number: int) -> Optional[Dict]:
        """Снять предупреждение по номеру"""
        user_data = self.get_user_by_id(user_id)
        warns_list = json.loads(user_data.get('warns_list', '[]'))
        
        filtered = [w for w in warns_list if w.get('id') != warn_number]
        
        if len(filtered) == len(warns_list):
            return None
        
        self.cursor.execute(
            "UPDATE users SET warns = ?, warns_list = ? WHERE user_id = ?",
            (len(filtered), json.dumps(filtered), user_id)
        )
        self.conn.commit()
        
        return {'removed': True, 'new_count': len(filtered)}
    
    def remove_all_warns(self, user_id: int) -> int:
        """Снять все предупреждения"""
        self.cursor.execute(
            "UPDATE users SET warns = 0, warns_list = '[]' WHERE user_id = ?",
            (user_id,)
        )
        self.conn.commit()
        return 0
    
    # ========== МУТ ==========
    
    def mute_user(self, user_id: int, minutes: int, admin_id: int = None, reason: str = "Спам"):
        """Заглушить пользователя"""
        mute_until = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
        self.cursor.execute(
            "UPDATE users SET mute_until = ?, mutes_count = mutes_count + 1 WHERE user_id = ?",
            (mute_until, user_id)
        )
        self.conn.commit()
        return mute_until
    
    def is_muted(self, user_id: int) -> bool:
        """Проверить, заглушен ли пользователь"""
        self.cursor.execute("SELECT mute_until FROM users WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()
        if result and result[0]:
            mute_until = datetime.datetime.fromisoformat(result[0])
            return datetime.datetime.now() < mute_until
        return False
    
    def get_mute_time(self, user_id: int) -> str:
        """Получить оставшееся время мута"""
        self.cursor.execute("SELECT mute_until FROM users WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()
        if result and result[0]:
            mute_until = datetime.datetime.fromisoformat(result[0])
            if datetime.datetime.now() < mute_until:
                remaining = mute_until - datetime.datetime.now()
                days = remaining.days
                hours = remaining.seconds // 3600
                minutes = (remaining.seconds % 3600) // 60
                seconds = remaining.seconds % 60
                
                parts = []
                if days > 0:
                    parts.append(f"{days} дн")
                if hours > 0:
                    parts.append(f"{hours} ч")
                if minutes > 0:
                    parts.append(f"{minutes} мин")
                if seconds > 0 or not parts:
                    parts.append(f"{seconds} сек")
                
                return " ".join(parts)
        return "0"
    
    def unmute_user(self, user_id: int):
        """Снять мут"""
        self.cursor.execute("UPDATE users SET mute_until = NULL WHERE user_id = ?", (user_id,))
        self.conn.commit()
    
    def get_muted_users(self) -> List[Tuple]:
        """Получить список заглушенных пользователей"""
        self.cursor.execute(
            "SELECT user_id, first_name, mute_until FROM users WHERE mute_until IS NOT NULL AND mute_until > ? ORDER BY mute_until",
            (datetime.datetime.now(),)
        )
        return self.cursor.fetchall()
    
    # ========== БАН ==========
    
    def ban_user(self, user_id: int, admin_id: int, reason: str = "Нарушение", period: str = "навсегда"):
        """Заблокировать пользователя"""
        ban_until = None
        if period != "навсегда":
            # Парсим период (1д, 1н, 1м, 1г)
            match = re.match(r'(\d+)([днмг])', period)
            if match:
                num, unit = int(match.group(1)), match.group(2)
                if unit == 'д':
                    ban_until = datetime.datetime.now() + datetime.timedelta(days=num)
                elif unit == 'н':
                    ban_until = datetime.datetime.now() + datetime.timedelta(weeks=num)
                elif unit == 'м':
                    ban_until = datetime.datetime.now() + datetime.timedelta(days=num*30)
                elif unit == 'г':
                    ban_until = datetime.datetime.now() + datetime.timedelta(days=num*365)
        
        self.cursor.execute(
            "UPDATE users SET banned = 1, bans_count = bans_count + 1, ban_reason = ?, ban_date = ?, ban_admin = ? WHERE user_id = ?",
            (reason, datetime.datetime.now(), admin_id, user_id)
        )
        self.conn.commit()
        
        if ban_until:
            # Если временный бан, сохраняем дату разбана в отдельном поле
            self.cursor.execute(
                "UPDATE users SET ban_until = ? WHERE user_id = ?",
                (ban_until, user_id)
            )
            self.conn.commit()
        
        return ban_until
    
    def unban_user(self, user_id: int):
        """Разблокировать пользователя"""
        self.cursor.execute(
            "UPDATE users SET banned = 0, warns = 0, ban_reason = NULL, ban_date = NULL, ban_admin = NULL WHERE user_id = ?",
            (user_id,)
        )
        self.conn.commit()
    
    def is_banned(self, user_id: int) -> bool:
        """Проверить, заблокирован ли пользователь"""
        self.cursor.execute("SELECT banned, ban_until FROM users WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()
        if result and result[0] == 1:
            if result[1]:  # Временный бан
                ban_until = datetime.datetime.fromisoformat(result[1])
                if datetime.datetime.now() < ban_until:
                    return True
                else:
                    # Срок истек, разбаниваем автоматически
                    self.unban_user(user_id)
                    return False
            return True
        return False
    
    def get_ban_reason(self, user_id: int) -> Optional[Dict]:
        """Получить причину бана"""
        self.cursor.execute(
            "SELECT ban_reason, ban_date, ban_admin FROM users WHERE user_id = ? AND banned = 1",
            (user_id,)
        )
        result = self.cursor.fetchone()
        if result:
            admin_data = self.get_user_by_id(result[2]) if result[2] else None
            return {
                'reason': result[0],
                'date': result[1],
                'admin_id': result[2],
                'admin_name': admin_data.get('first_name') if admin_data else 'Неизвестно'
            }
        return None
    
    def get_banlist(self, page: int = 1, limit: int = 10) -> Tuple[List, int]:
        """Получить список забаненных"""
        offset = (page - 1) * limit
        self.cursor.execute(
            "SELECT COUNT(*) FROM users WHERE banned = 1"
        )
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
                'admin': admin_data.get('first_name') if admin_data else 'Неизвестно'
            })
        
        return bans, total
    
    # ========== ТРИГГЕРЫ ==========
    
    def add_trigger(self, chat_id: int, trigger_word: str, action: str, created_by: int):
        """Добавить триггер"""
        self.cursor.execute('''
            INSERT INTO triggers (chat_id, trigger_word, action, created_by, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (chat_id, trigger_word, action, created_by, datetime.datetime.now()))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def remove_trigger(self, trigger_id: int):
        """Удалить триггер"""
        self.cursor.execute("DELETE FROM triggers WHERE id = ?", (trigger_id,))
        self.conn.commit()
    
    def get_triggers(self, chat_id: int) -> List[Tuple]:
        """Получить список триггеров чата"""
        self.cursor.execute("SELECT * FROM triggers WHERE chat_id = ? ORDER BY created_at", (chat_id,))
        return self.cursor.fetchall()
    
    def check_trigger(self, chat_id: int, text: str) -> Optional[str]:
        """Проверить, есть ли триггер на текст"""
        self.cursor.execute("SELECT action FROM triggers WHERE chat_id = ? AND ? LIKE '%' || trigger_word || '%'", (chat_id, text))
        result = self.cursor.fetchone()
        return result[0] if result else None
    
    # ========== ДОСТУП КОМАНД ==========
    
    def set_command_access(self, chat_id: int, command_name: str, min_rank: int = 0, enabled: int = 1):
        """Установить доступ к команде"""
        self.cursor.execute('''
            INSERT INTO command_access (chat_id, command_name, min_rank, enabled)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(chat_id, command_name) DO UPDATE SET
            min_rank = excluded.min_rank,
            enabled = excluded.enabled
        ''', (chat_id, command_name, min_rank, enabled))
        self.conn.commit()
    
    def get_command_access(self, chat_id: int, command_name: str) -> Dict:
        """Получить доступ к команде"""
        self.cursor.execute(
            "SELECT min_rank, enabled FROM command_access WHERE chat_id = ? AND command_name = ?",
            (chat_id, command_name)
        )
        result = self.cursor.fetchone()
        if result:
            return {'min_rank': result[0], 'enabled': result[1]}
        return {'min_rank': 0, 'enabled': 1}
    
    def disable_command(self, chat_id: int, command_name: str):
        """Отключить команду"""
        self.set_command_access(chat_id, command_name, 0, 0)
    
    def enable_command(self, chat_id: int, command_name: str):
        """Включить команду"""
        self.set_command_access(chat_id, command_name, 0, 1)
    
    def set_personal_access(self, chat_id: int, user_id: int, command_name: str, allowed: int = 1):
        """Установить личный доступ к команде"""
        self.cursor.execute('''
            INSERT INTO personal_access (chat_id, user_id, command_name, allowed)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(chat_id, user_id, command_name) DO UPDATE SET
            allowed = excluded.allowed
        ''', (chat_id, user_id, command_name, allowed))
        self.conn.commit()
    
    def get_personal_access(self, chat_id: int, user_id: int, command_name: str) -> Optional[int]:
        """Получить личный доступ к команде"""
        self.cursor.execute(
            "SELECT allowed FROM personal_access WHERE chat_id = ? AND user_id = ? AND command_name = ?",
            (chat_id, user_id, command_name)
        )
        result = self.cursor.fetchone()
        return result[0] if result else None
    
    def remove_personal_access(self, chat_id: int, user_id: int, command_name: str = None):
        """Удалить личный доступ"""
        if command_name:
            self.cursor.execute(
                "DELETE FROM personal_access WHERE chat_id = ? AND user_id = ? AND command_name = ?",
                (chat_id, user_id, command_name)
            )
        else:
            self.cursor.execute(
                "DELETE FROM personal_access WHERE chat_id = ? AND user_id = ?",
                (chat_id, user_id)
            )
        self.conn.commit()
    
    # ========== НАСТРОЙКИ ЧАТА ==========
    
    def get_chat_settings(self, chat_id: int) -> Dict:
        """Получить настройки чата"""
        self.cursor.execute("SELECT * FROM chat_settings WHERE chat_id = ?", (chat_id,))
        settings = self.cursor.fetchone()
        
        if not settings:
            self.cursor.execute('''
                INSERT INTO chat_settings (chat_id) VALUES (?)
            ''', (chat_id,))
            self.conn.commit()
            return self.get_chat_settings(chat_id)
        
        columns = [description[0] for description in self.cursor.description]
        return dict(zip(columns, settings))
    
    def update_chat_settings(self, chat_id: int, **kwargs):
        """Обновить настройки чата"""
        for key, value in kwargs.items():
            self.cursor.execute(
                f"UPDATE chat_settings SET {key} = ? WHERE chat_id = ?",
                (value, chat_id)
            )
        self.conn.commit()
    
    def set_chat_rules(self, chat_id: int, rules: str):
        """Установить правила чата"""
        self.update_chat_settings(chat_id, rules=rules)
    
    def set_welcome_message(self, chat_id: int, message: str):
        """Установить приветствие"""
        self.update_chat_settings(chat_id, welcome_message=message)
    
    def set_chat_link(self, chat_id: int, link: str):
        """Установить ссылку на чат"""
        self.update_chat_settings(chat_id, chat_link=link)
    
    def toggle_chat(self, chat_id: int, enabled: bool):
        """Включить/отключить чат"""
        self.update_chat_settings(chat_id, chat_enabled=1 if enabled else 0)
    
    def add_allowed_link(self, chat_id: int, link: str):
        """Добавить ссылку в разрешенные"""
        settings = self.get_chat_settings(chat_id)
        allowed = json.loads(settings.get('allowed_links', '[]'))
        if link not in allowed:
            allowed.append(link)
            self.update_chat_settings(chat_id, allowed_links=json.dumps(allowed))
    
    def remove_allowed_link(self, chat_id: int, link: str):
        """Удалить ссылку из разрешенных"""
        settings = self.get_chat_settings(chat_id)
        allowed = json.loads(settings.get('allowed_links', '[]'))
        if link in allowed:
            allowed.remove(link)
            self.update_chat_settings(chat_id, allowed_links=json.dumps(allowed))
    
    # ========== ГЛОБАЛЬНЫЕ МОДЕРАТОРЫ ==========
    
    def add_global_moderator(self, user_id: int, added_by: int, role: str = 'moderator'):
        """Добавить глобального модератора"""
        self.cursor.execute('''
            INSERT INTO global_moderators (user_id, role, added_by, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
            role = excluded.role,
            added_by = excluded.added_by,
            created_at = excluded.created_at
        ''', (user_id, role, added_by, datetime.datetime.now()))
        self.conn.commit()
    
    def remove_global_moderator(self, user_id: int):
        """Удалить глобального модератора"""
        self.cursor.execute("DELETE FROM global_moderators WHERE user_id = ?", (user_id,))
        self.conn.commit()
    
    def is_global_moderator(self, user_id: int) -> bool:
        """Проверить, является ли пользователь глобальным модератором"""
        self.cursor.execute("SELECT 1 FROM global_moderators WHERE user_id = ?", (user_id,))
        return self.cursor.fetchone() is not None
    
    def get_global_moderators(self) -> List[Tuple]:
        """Получить список глобальных модераторов"""
        self.cursor.execute("SELECT * FROM global_moderators ORDER BY created_at")
        return self.cursor.fetchall()
    
    # ========== ГЛОБАЛЬНЫЕ БАНЫ ==========
    
    def add_global_ban(self, user_id: int, reason: str, banned_by: int):
        """Добавить глобальный бан"""
        self.cursor.execute('''
            INSERT INTO global_bans (user_id, reason, banned_by, banned_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
            reason = excluded.reason,
            banned_by = excluded.banned_by,
            banned_at = excluded.banned_at
        ''', (user_id, reason, banned_by, datetime.datetime.now()))
        self.conn.commit()
    
    def remove_global_ban(self, user_id: int):
        """Удалить глобальный бан"""
        self.cursor.execute("DELETE FROM global_bans WHERE user_id = ?", (user_id,))
        self.conn.commit()
    
    def is_globally_banned(self, user_id: int) -> bool:
        """Проверить, есть ли глобальный бан"""
        self.cursor.execute("SELECT 1 FROM global_bans WHERE user_id = ?", (user_id,))
        return self.cursor.fetchone() is not None
    
    def get_global_bans(self) -> List[Tuple]:
        """Получить список глобальных банов"""
        self.cursor.execute("SELECT * FROM global_bans ORDER BY banned_at DESC")
        return self.cursor.fetchall()
    
    # ========== ГРАЖДАНСТВО ==========
    
    def add_citizenship(self, user_id: int, chat_id: int):
        """Выдать гражданство чата"""
        self.cursor.execute('''
            INSERT INTO citizenship (user_id, chat_id, joined_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, chat_id) DO NOTHING
        ''', (user_id, chat_id, datetime.datetime.now()))
        self.conn.commit()
        
        self.cursor.execute(
            "UPDATE users SET citizenship = citizenship + 1 WHERE user_id = ?",
            (user_id,)
        )
        self.conn.commit()
    
    def remove_citizenship(self, user_id: int, chat_id: int):
        """Лишить гражданства"""
        self.cursor.execute(
            "DELETE FROM citizenship WHERE user_id = ? AND chat_id = ?",
            (user_id, chat_id)
        )
        self.conn.commit()
        
        self.cursor.execute(
            "UPDATE users SET citizenship = citizenship - 1 WHERE user_id = ?",
            (user_id,)
        )
        self.conn.commit()
    
    def get_citizens(self, chat_id: int) -> List[Tuple]:
        """Получить список граждан чата"""
        self.cursor.execute('''
            SELECT u.user_id, u.first_name, u.nickname, c.joined_at
            FROM citizenship c
            JOIN users u ON c.user_id = u.user_id
            WHERE c.chat_id = ?
            ORDER BY c.joined_at
        ''', (chat_id,))
        return self.cursor.fetchall()
    
    # ========== ПОДПИСКИ ==========
    
    def add_subscription(self, subscriber_id: int, subscribed_to: int):
        """Подписаться на пользователя"""
        self.cursor.execute('''
            INSERT INTO subscriptions (subscriber_id, subscribed_to, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT(subscriber_id, subscribed_to) DO NOTHING
        ''', (subscriber_id, subscribed_to, datetime.datetime.now()))
        self.conn.commit()
    
    def remove_subscription(self, subscriber_id: int, subscribed_to: int):
        """Отписаться от пользователя"""
        self.cursor.execute(
            "DELETE FROM subscriptions WHERE subscriber_id = ? AND subscribed_to = ?",
            (subscriber_id, subscribed_to)
        )
        self.conn.commit()
    
    def get_subscriptions(self, user_id: int) -> List[Tuple]:
        """Получить список подписок пользователя"""
        self.cursor.execute('''
            SELECT u.user_id, u.first_name, u.nickname, s.created_at
            FROM subscriptions s
            JOIN users u ON s.subscribed_to = u.user_id
            WHERE s.subscriber_id = ?
            ORDER BY s.created_at DESC
        ''', (user_id,))
        return self.cursor.fetchall()
    
    def get_subscribers(self, user_id: int) -> List[Tuple]:
        """Получить список подписчиков пользователя"""
        self.cursor.execute('''
            SELECT u.user_id, u.first_name, u.nickname, s.created_at
            FROM subscriptions s
            JOIN users u ON s.subscriber_id = u.user_id
            WHERE s.subscribed_to = ?
            ORDER BY s.created_at DESC
        ''', (user_id,))
        return self.cursor.fetchall()
    
    # ========== НАГРАДЫ ==========
    
    def add_reward(self, user_id: int, reward_name: str, reward_desc: str, awarded_by: int):
        """Добавить награду пользователю"""
        self.cursor.execute('''
            INSERT INTO rewards (user_id, reward_name, reward_desc, awarded_by, awarded_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, reward_name, reward_desc, awarded_by, datetime.datetime.now()))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_rewards(self, user_id: int) -> List[Tuple]:
        """Получить награды пользователя"""
        self.cursor.execute('''
            SELECT r.reward_name, r.reward_desc, u.first_name, r.awarded_at
            FROM rewards r
            JOIN users u ON r.awarded_by = u.user_id
            WHERE r.user_id = ?
            ORDER BY r.awarded_at DESC
        ''', (user_id,))
        return self.cursor.fetchall()
    
    # ========== БОССЫ ==========
    
    def respawn_bosses(self):
        self.cursor.execute("UPDATE bosses SET is_alive = 1, boss_health = boss_max_health")
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
    
    def close(self):
        self.conn.close()

# Инициализация БД
db = Database()

# ========== КЛАСС ДЛЯ ФОРМАТИРОВАНИЯ В СТИЛЕ IRIS ==========
class IrisFormatter:
    """Класс для форматирования текста в стиле Iris"""
    
    @staticmethod
    def header(title: str, emoji: str = "📋") -> str:
        """Создает заголовок раздела"""
        return (
            f"╔══════════════════════════════╗\n"
            f"║    {emoji} {title}    ║\n"
            f"╚══════════════════════════════╝\n"
        )
    
    @staticmethod
    def section(title: str, emoji: str = "▫️") -> str:
        """Создает заголовок подраздела"""
        return f"\n{emoji} **{title}**\n" + "━" * 25 + "\n"
    
    @staticmethod
    def command(name: str, description: str, usage: str = "", emoji: str = "・") -> str:
        """Форматирует команду"""
        if usage:
            return f"{emoji} `/{name} {usage}` — {description}"
        return f"{emoji} `/{name}` — {description}"
    
    @staticmethod
    def command_block(title: str, commands: List[Tuple[str, str, str]], emoji: str = "📌") -> str:
        """Создает блок команд"""
        text = IrisFormatter.section(title, emoji)
        for cmd, desc, usage in commands:
            text += IrisFormatter.command(cmd, desc, usage) + "\n"
        return text
    
    @staticmethod
    def warning(text: str) -> str:
        """Форматирует предупреждение"""
        return f"⚠️ **Внимание:** {text}"
    
    @staticmethod
    def note(text: str) -> str:
        """Форматирует примечание"""
        return f"📌 *{text}*"
    
    @staticmethod
    def example(text: str) -> str:
        """Форматирует пример"""
        return f"└ Пример: `{text}`"
    
    @staticmethod
    def param(name: str, description: str) -> str:
        """Форматирует описание параметра"""
        return f"▫️ `{name}` — {description}"
    
    @staticmethod
    def link(text: str, url: str) -> str:
        """Создает ссылку"""
        return f"[{text}]({url})"
    
    @staticmethod
    def user_link(user_id: int, name: str) -> str:
        """Создает ссылку на пользователя"""
        return f"[{name}](tg://user?id={user_id})"
    
    @staticmethod
    def list_item(text: str, emoji: str = "•") -> str:
        """Элемент списка"""
        return f"{emoji} {text}"
    
    @staticmethod
    def code(text: str) -> str:
        """Форматирует код"""
        return f"`{text}`"
    
    @staticmethod
    def bold(text: str) -> str:
        """Жирный текст"""
        return f"**{text}**"
    
    @staticmethod
    def italic(text: str) -> str:
        """Курсив"""
        return f"_{text}_"
    
    @staticmethod
    def spoiler(text: str) -> str:
        """Спойлер"""
        return f"||{text}||"
    
    @staticmethod
    def quote(text: str) -> str:
        """Цитата"""
        return f"> {text}"
    
    @staticmethod
    def success(text: str) -> str:
        """Успех"""
        return f"✅ {text}"
    
    @staticmethod
    def error(text: str) -> str:
        """Ошибка"""
        return f"❌ {text}"
    
    @staticmethod
    def info(text: str) -> str:
        """Информация"""
        return f"ℹ️ {text}"
    
    @staticmethod
    def progress(current: int, total: int, length: int = 10) -> str:
        """Прогресс-бар"""
        filled = int((current / total) * length)
        bar = "█" * filled + "░" * (length - filled)
        return f"{bar} {current}/{total}"

# ========== ОСНОВНОЙ КЛАСС БОТА ==========
class GameBot:
    def __init__(self):
        self.db = db
        self.spam_tracker = defaultdict(list)
        self.application = Application.builder().token(TELEGRAM_TOKEN).build()
        self.f = IrisFormatter()  # Форматтер для красивого вывода
        self.setup_handlers()
        print("✅ Бот «СПЕКТР» инициализирован")
    
    def setup_handlers(self):
        # Основные
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        self.application.add_handler(CommandHandler("menu", self.cmd_menu))
        
        # Профиль
        self.application.add_handler(CommandHandler("profile", self.cmd_profile))
        self.application.add_handler(CommandHandler("whoami", self.cmd_whoami))
        self.application.add_handler(CommandHandler("whois", self.cmd_whois))
        self.application.add_handler(CommandHandler("myprofile", self.cmd_my_profile))
        self.application.add_handler(CommandHandler("setnick", self.cmd_set_nick))
        self.application.add_handler(CommandHandler("settitle", self.cmd_set_title))
        self.application.add_handler(CommandHandler("setmotto", self.cmd_set_motto))
        self.application.add_handler(CommandHandler("setbio", self.cmd_set_bio))
        self.application.add_handler(CommandHandler("setgender", self.cmd_set_gender))
        self.application.add_handler(CommandHandler("setcity", self.cmd_set_city))
        self.application.add_handler(CommandHandler("setbirthday", self.cmd_set_birthday))
        
        # Статистика
        self.application.add_handler(CommandHandler("mystats", self.cmd_my_stats))
        self.application.add_handler(CommandHandler("top", self.cmd_top))
        self.application.add_handler(CommandHandler("daily", self.cmd_daily))
        self.application.add_handler(CommandHandler("weekly", self.cmd_weekly))
        self.application.add_handler(CommandHandler("streak", self.cmd_streak))
        self.application.add_handler(CommandHandler("rep", self.cmd_rep))
        
        # Система банов и предупреждений
        self.application.add_handler(CommandHandler("warn", self.cmd_warn))
        self.application.add_handler(CommandHandler("warns", self.cmd_warns))
        self.application.add_handler(CommandHandler("mywarns", self.cmd_my_warns))
        self.application.add_handler(CommandHandler("unwarn", self.cmd_unwarn))
        self.application.add_handler(CommandHandler("unwarnall", self.cmd_unwarn_all))
        self.application.add_handler(CommandHandler("warnlimit", self.cmd_warn_limit))
        
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
        
        # Боссы
        self.application.add_handler(CommandHandler("bosses", self.cmd_boss_list))
        self.application.add_handler(CommandHandler("boss", self.cmd_boss_info))
        self.application.add_handler(CommandHandler("bossfight", self.cmd_boss_fight))
        self.application.add_handler(CommandHandler("regen", self.cmd_regen))
        self.application.add_handler(CommandHandler("bossstats", self.cmd_boss_stats))
        
        # Казино
        self.application.add_handler(CommandHandler("casino", self.cmd_casino))
        self.application.add_handler(CommandHandler("roulette", self.cmd_roulette))
        self.application.add_handler(CommandHandler("dice", self.cmd_dice))
        self.application.add_handler(CommandHandler("blackjack", self.cmd_blackjack))
        self.application.add_handler(CommandHandler("slots", self.cmd_slots))
        self.application.add_handler(CommandHandler("rps", self.cmd_rps))
        self.application.add_handler(CommandHandler("rpsstats", self.cmd_rps_stats))
        self.application.add_handler(CommandHandler("casinostats", self.cmd_casino_stats))
        
        # Экономика
        self.application.add_handler(CommandHandler("shop", self.cmd_shop))
        self.application.add_handler(CommandHandler("buy", self.cmd_buy))
        self.application.add_handler(CommandHandler("inventory", self.cmd_inventory))
        self.application.add_handler(CommandHandler("pay", self.cmd_pay))
        self.application.add_handler(CommandHandler("paydiamond", self.cmd_pay_diamond))
        self.application.add_handler(CommandHandler("donate", self.cmd_donate))
        self.application.add_handler(CommandHandler("vip", self.cmd_vip))
        self.application.add_handler(CommandHandler("premium", self.cmd_premium))
        
        # Долги
        self.application.add_handler(CommandHandler("debt", self.cmd_debt))
        self.application.add_handler(CommandHandler("debts", self.cmd_debts))
        self.application.add_handler(CommandHandler("paydebt", self.cmd_pay_debt))
        
        # Закладки
        self.application.add_handler(CommandHandler("addbookmark", self.cmd_add_bookmark))
        self.application.add_handler(CommandHandler("bookmarks", self.cmd_bookmarks))
        
        # Подписки
        self.application.add_handler(CommandHandler("subscribe", self.cmd_subscribe))
        self.application.add_handler(CommandHandler("unsubscribe", self.cmd_unsubscribe))
        self.application.add_handler(CommandHandler("mysubs", self.cmd_my_subs))
        self.application.add_handler(CommandHandler("mysubscribers", self.cmd_my_subscribers))
        
        # Награды
        self.application.add_handler(CommandHandler("rewards", self.cmd_rewards))
        self.application.add_handler(CommandHandler("addreward", self.cmd_add_reward))
        
        # Достижения
        self.application.add_handler(CommandHandler("achievements", self.cmd_achievements))
        
        # Гражданство
        self.application.add_handler(CommandHandler("citizens", self.cmd_citizens))
        self.application.add_handler(CommandHandler("grantcitizen", self.cmd_grant_citizen))
        
        # Прочие
        self.application.add_handler(CommandHandler("weather", self.cmd_weather))
        self.application.add_handler(CommandHandler("news", self.cmd_news))
        self.application.add_handler(CommandHandler("quote", self.cmd_quote))
        self.application.add_handler(CommandHandler("players", self.cmd_players))
        self.application.add_handler(CommandHandler("mycrime", self.cmd_mycrime))
        self.application.add_handler(CommandHandler("engfree", self.cmd_eng_free))
        self.application.add_handler(CommandHandler("sms", self.cmd_sms))
        
        # Обработчики
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.application.add_handler(MessageHandler(filters.VOICE, self.handle_voice))
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        self.application.add_handler(MessageHandler(filters.Sticker.ALL, self.handle_sticker))
        self.application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, self.handle_new_members))
        self.application.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, self.handle_left_member))
        
        print("✅ Все обработчики зарегистрированы")
    
    def is_admin(self, user_id: int) -> bool:
        user = self.db.get_user_by_id(user_id)
        return user.get('role', 'user') in ['owner', 'admin', 'moderator']
    
    def is_owner(self, user_id: int) -> bool:
        return user_id == OWNER_ID
    
    def is_vip(self, user_id: int) -> bool:
        return self.db.is_vip(user_id) or self.is_admin(user_id)
    
    def is_premium(self, user_id: int) -> bool:
        return self.db.is_premium(user_id) or self.is_admin(user_id)
    
    def get_role_emoji(self, role: str) -> str:
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
        role_hierarchy = ['user', 'vip', 'premium', 'moderator', 'admin', 'owner']
        user_role = user_data.get('role', 'user')
        if user_role not in role_hierarchy:
            return False
        user_level = role_hierarchy.index(user_role)
        required_level = role_hierarchy.index(required_role)
        return user_level >= required_level
    
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
                self.f.error(f"Спам-фильтр. Вы замучены на {SPAM_MUTE_TIME} минут."),
                parse_mode='Markdown'
            )
            self.spam_tracker[user_id] = []
            return True
        return False
    
    # ========== ОСНОВНЫЕ КОМАНДЫ ==========
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_or_create_user("tg", str(user.id), user.first_name)
        self.db.update_last_seen(user.id)
        
        if context.args and context.args[0].isdigit():
            referrer_id = int(context.args[0])
            if referrer_id != user.id:
                self.db.add_referral(referrer_id, user.id, 200)
                try:
                    await context.bot.send_message(
                        chat_id=referrer_id,
                        text=self.f.success(f"По вашей реферальной ссылке зарегистрировался {user.first_name}! +200 🪙")
                    )
                except:
                    pass
        
        text = (
            self.f.header("ДОБРО ПОЖАЛОВАТЬ", "⚔️") + "\n"
            f"🌟 **Привет, {user.first_name}!**\n\n"
            f"Я — **«СПЕКТР»**, твой игровой помощник!\n\n"
            self.f.section("ТВОЙ ПРОФИЛЬ", "👤") + "\n"
            f"{self.f.list_item(f'Роль: {self.get_role_emoji(user_data.get("role", "user"))} {user_data.get("role", "user")}')}\n"
            f"{self.f.list_item(f'Монеты: {user_data.get("coins", 1000)} 🪙')}\n"
            f"{self.f.list_item(f'Уровень: {user_data.get("level", 1)}')}\n\n"
            self.f.section("ГЛАВНОЕ МЕНЮ", "📌") + "\n"
            f"{self.f.command('profile', 'твой профиль')}\n"
            f"{self.f.command('bosses', 'битва с боссами')}\n"
            f"{self.f.command('casino', 'казино')}\n"
            f"{self.f.command('shop', 'магазин')}\n"
            f"{self.f.command('donate', 'привилегии')}\n\n"
            f"👑 **Владелец:** {OWNER_USERNAME}\n\n"
            f"💡 Напиши /menu для интерактивного меню"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
        self.db.add_stat(user.id, "commands_used")
    
    async def cmd_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = self.get_main_menu_keyboard()
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            self.f.header("ГЛАВНОЕ МЕНЮ", "🎮") + "\nВыбери раздел:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    def get_main_menu_keyboard(self):
        return [
            [InlineKeyboardButton("👤 Профиль", callback_data="menu_profile"),
             InlineKeyboardButton("📊 Статистика", callback_data="menu_stats")],
            [InlineKeyboardButton("👾 Боссы", callback_data="menu_bosses"),
             InlineKeyboardButton("🎰 Казино", callback_data="menu_casino")],
            [InlineKeyboardButton("🛍 Магазин", callback_data="menu_shop"),
             InlineKeyboardButton("💎 Привилегии", callback_data="menu_donate")],
            [InlineKeyboardButton("⚙️ Модерация", callback_data="menu_moderation"),
             InlineKeyboardButton("📚 Помощь", callback_data="menu_help")],
        ]
    
    def get_back_button(self):
        return [InlineKeyboardButton("🔙 Назад", callback_data="menu_back")]
    
    # ========== КОМАНДЫ ПРОФИЛЯ ==========
    
    async def cmd_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_or_create_user("tg", str(user.id), user.first_name)
        
        target_id = user.id
        target_name = user.first_name
        
        if context.args:
            query = " ".join(context.args)
            # Проверяем по нику или юзернейму
            target_user = self.db.get_user_by_name(query) or self.db.get_user_by_username(query)
            if target_user:
                target_id = target_user['user_id']
                target_name = target_user.get('nickname') or target_user.get('first_name', 'Игрок')
            else:
                await update.message.reply_text(self.f.error(f"Пользователь '{query}' не найден"))
                return
        
        target_data = self.db.get_user_by_id(target_id)
        stats = self.db.get_user_stats(target_id)
        
        vip_status = "✅ Активен" if self.db.is_vip(target_id) else "❌ Нет"
        premium_status = "✅ Активен" if self.db.is_premium(target_id) else "❌ Нет"
        
        clan = self.db.get_user_clan(target_id)
        clan_name = clan[1] if clan else "Нет"
        
        display_name = target_data.get('nickname') or target_name
        title = target_data.get('title') or ""
        motto = target_data.get('motto') or ""
        
        join_date = target_data.get('created_at', '')
        if join_date:
            join_dt = datetime.datetime.fromisoformat(join_date)
            join_str = join_dt.strftime("%d.%m.%Y")
        else:
            join_str = "неизвестно"
        
        warns = target_data.get('warns', 0)
        warns_display = "🔴" * warns + "⚪" * (3 - warns) if warns <= 3 else "🔴🔴🔴"
        
        text = (
            self.f.header("ПРОФИЛЬ ИГРОКА", "👤") + "\n\n"
            f"**{display_name}** {title}\n"
            f"_{motto}_\n\n"
            self.f.section("ОСНОВНОЕ", "📌") + "\n"
            f"{self.f.list_item(f'Роль: {self.get_role_emoji(target_data.get("role", "user"))} {target_data.get("role", "user")}')}\n"
            f"{self.f.list_item(f'Уровень: {target_data.get("level", 1)}')}\n"
            f"{self.f.list_item(f'Опыт: {target_data.get("exp", 0)}/{target_data.get("level", 1) * 100}')}\n"
            f"{self.f.list_item(f'Монеты: {target_data.get("coins", 1000)} 🪙')}\n"
            f"{self.f.list_item(f'Алмазы: {target_data.get("diamonds", 0)} 💎')}\n"
            f"{self.f.list_item(f'Энергия: {target_data.get("energy", 100)} ⚡')}\n\n"
            self.f.section("БОЕВЫЕ", "⚔️") + "\n"
            f"{self.f.list_item(f'Здоровье: {target_data.get("health", 100)} ❤️')}\n"
            f"{self.f.list_item(f'Урон: {target_data.get("damage", 10)} ⚔️')}\n"
            f"{self.f.list_item(f'Броня: {target_data.get("armor", 0)} 🛡')}\n"
            f"{self.f.list_item(f'Боссов убито: {target_data.get("boss_kills", 0)} 👾')}\n\n"
            self.f.section("ПРИВИЛЕГИИ", "💎") + "\n"
            f"{self.f.list_item(f'VIP: {vip_status}')}\n"
            f"{self.f.list_item(f'Premium: {premium_status}')}\n\n"
            self.f.section("КЛАН", "👥") + "\n"
            f"{self.f.list_item(f'Название: {clan_name}')}\n"
            f"{self.f.list_item(f'Роль: {target_data.get("clan_role", "member")}')}\n\n"
            self.f.section("ИНФОРМАЦИЯ", "ℹ️") + "\n"
            f"{self.f.list_item(f'Дата регистрации: {join_str}')}\n"
            f"{self.f.list_item(f'Предупреждения: {warns_display} ({warns}/3)')}\n"
            f"{self.f.list_item(f'Репутация: {target_data.get("rep", 0)} ⭐')}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_whoami(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_or_create_user("tg", str(user.id), user.first_name)
        
        role_emoji = self.get_role_emoji(user_data.get('role', 'user'))
        join_date = user_data.get('created_at', '')
        if join_date:
            join_dt = datetime.datetime.fromisoformat(join_date)
            years = (datetime.datetime.now() - join_dt).days // 365
            months = ((datetime.datetime.now() - join_dt).days % 365) // 30
            join_str = join_dt.strftime("%d.%m.%Y") + f" ({years} г {months} мес)"
        else:
            join_str = "неизвестно"
        
        last_seen = user_data.get('last_seen', '')
        if last_seen:
            last_dt = datetime.datetime.fromisoformat(last_seen)
            delta = datetime.datetime.now() - last_dt
            if delta.days > 0:
                last_str = f"{delta.days} дн назад"
            elif delta.seconds > 3600:
                last_str = f"{delta.seconds // 3600} ч назад"
            else:
                last_str = f"{delta.seconds // 60} мин назад"
        else:
            last_str = "никогда"
        
        text = (
            f"**{self.f.user_link(user.id, user.first_name)}**\n"
            f"{role_emoji} Ранг: **{user_data.get('role')}**\n"
            f"Репутация: ✨ {user_data.get('rep', 0)} | ➕ 0\n"
            f"Первое появление: {join_str}\n"
            f"Последний актив: {last_str}\n"
            f"Актив (д|н|м|весь): {user_data.get('active_days', 0)} | {user_data.get('active_weeks', 0)} | {user_data.get('active_months', 0)} | {user_data.get('total_active_days', 0)}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_whois(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(self.f.error("Укажи ник: /whois @username"))
            return
        
        query = context.args[0]
        target_user = self.db.get_user_by_name(query) or self.db.get_user_by_username(query)
        
        if not target_user:
            await update.message.reply_text(self.f.error(f"Пользователь '{query}' не найден"))
            return
        
        user_data = target_user
        role_emoji = self.get_role_emoji(user_data.get('role', 'user'))
        
        join_date = user_data.get('created_at', '')
        if join_date:
            join_dt = datetime.datetime.fromisoformat(join_date)
            years = (datetime.datetime.now() - join_dt).days // 365
            months = ((datetime.datetime.now() - join_dt).days % 365) // 30
            join_str = join_dt.strftime("%d.%m.%Y") + f" ({years} г {months} мес)"
        else:
            join_str = "неизвестно"
        
        last_seen = user_data.get('last_seen', '')
        if last_seen:
            last_dt = datetime.datetime.fromisoformat(last_seen)
            delta = datetime.datetime.now() - last_dt
            if delta.days > 0:
                last_str = f"{delta.days} дн назад"
            elif delta.seconds > 3600:
                last_str = f"{delta.seconds // 3600} ч назад"
            else:
                last_str = f"{delta.seconds // 60} мин назад"
        else:
            last_str = "никогда"
        
        display_name = user_data.get('nickname') or user_data.get('first_name', 'Игрок')
        
        text = (
            f"**[{user_data.get('platform_id')}|{display_name}]**\n"
            f"{role_emoji} Ранг: **{user_data.get('role')}**\n"
            f"Репутация: ✨ {user_data.get('rep', 0)} | ➕ 0\n"
            f"Первое появление: {join_str}\n"
            f"Последний актив: {last_str}\n"
            f"Актив (д|н|м|весь): {user_data.get('active_days', 0)} | {user_data.get('active_weeks', 0)} | {user_data.get('active_months', 0)} | {user_data.get('total_active_days', 0)}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_my_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.cmd_whoami(update, context)
    
    async def cmd_set_nick(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(self.f.error("Укажи ник: /setnick НовыйНик"))
            return
        
        nick = " ".join(context.args)
        if len(nick) > 30:
            await update.message.reply_text(self.f.error("Ник слишком длинный (макс 30 символов)"))
            return
        
        user_id = update.effective_user.id
        self.db.cursor.execute(
            "UPDATE users SET nickname = ? WHERE user_id = ?",
            (nick, user_id)
        )
        self.db.conn.commit()
        
        await update.message.reply_text(self.f.success(f"Ник установлен: {nick}"))
    
    async def cmd_set_title(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(self.f.error("Укажи звание: /settitle МоёЗвание"))
            return
        
        title = " ".join(context.args)
        if len(title) > 30:
            await update.message.reply_text(self.f.error("Звание слишком длинное (макс 30 символов)"))
            return
        
        user_id = update.effective_user.id
        self.db.cursor.execute(
            "UPDATE users SET title = ? WHERE user_id = ?",
            (title, user_id)
        )
        self.db.conn.commit()
        
        await update.message.reply_text(self.f.success(f"Звание установлено: {title}"))
    
    async def cmd_set_motto(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(self.f.error("Укажи девиз: /setmotto МойДевиз"))
            return
        
        motto = " ".join(context.args)
        if len(motto) > 100:
            await update.message.reply_text(self.f.error("Девиз слишком длинный (макс 100 символов)"))
            return
        
        user_id = update.effective_user.id
        self.db.cursor.execute(
            "UPDATE users SET motto = ? WHERE user_id = ?",
            (motto, user_id)
        )
        self.db.conn.commit()
        
        await update.message.reply_text(self.f.success(f"Девиз установлен: {motto}"))
    
    async def cmd_set_bio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(self.f.error("Укажи описание: /setbio Текст описания"))
            return
        
        bio = " ".join(context.args)
        if len(bio) > 500:
            await update.message.reply_text(self.f.error("Описание слишком длинное (макс 500 символов)"))
            return
        
        user_id = update.effective_user.id
        self.db.cursor.execute(
            "UPDATE users SET bio = ? WHERE user_id = ?",
            (bio, user_id)
        )
        self.db.conn.commit()
        
        await update.message.reply_text(self.f.success("Описание сохранено!"))
    
    async def cmd_set_gender(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args or context.args[0].lower() not in ['м', 'ж', 'др']:
            await update.message.reply_text(self.f.error("Укажи пол: /setgender [м|ж|др]"))
            return
        
        gender = context.args[0].lower()
        user_id = update.effective_user.id
        self.db.cursor.execute(
            "UPDATE users SET gender = ? WHERE user_id = ?",
            (gender, user_id)
        )
        self.db.conn.commit()
        
        await update.message.reply_text(self.f.success(f"Пол установлен: {gender}"))
    
    async def cmd_set_city(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(self.f.error("Укажи город: /setcity Москва"))
            return
        
        city = " ".join(context.args)
        user_id = update.effective_user.id
        self.db.cursor.execute(
            "UPDATE users SET city = ? WHERE user_id = ?",
            (city, user_id)
        )
        self.db.conn.commit()
        
        await update.message.reply_text(self.f.success(f"Город установлен: {city}"))
    
    async def cmd_set_birthday(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(self.f.error("Укажи дату рождения: /setbirthday ДД.ММ.ГГГГ"))
            return
        
        birthday = context.args[0]
        # Простая проверка формата
        if not re.match(r'\d{2}\.\d{2}\.\d{4}', birthday):
            await update.message.reply_text(self.f.error("Неверный формат. Используй ДД.ММ.ГГГГ"))
            return
        
        user_id = update.effective_user.id
        self.db.cursor.execute(
            "UPDATE users SET birthday = ? WHERE user_id = ?",
            (birthday, user_id)
        )
        self.db.conn.commit()
        
        await update.message.reply_text(self.f.success(f"Дата рождения установлена: {birthday}"))
    
    # ========== СТАТИСТИКА ==========
    
    async def cmd_my_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user_by_id(user.id)
        stats = self.db.get_user_stats(user.id)
        
        # Создаем простой график активности
        hours = list(range(24))
        activity = [random.randint(0, 10) for _ in hours]  # В реальности брать из БД
        
        graph = "Активность по часам:\n"
        for i in range(0, 24, 3):
            bar = "█" * activity[i]
            graph += f"{i:2d}:00 {bar}\n"
        
        text = (
            self.f.header("ТВОЯ СТАТИСТИКА", "📊") + "\n\n"
            f"{self.f.list_item(f'Сообщений: {stats[1] if stats else 0}')}\n"
            f"{self.f.list_item(f'Команд: {stats[2] if stats else 0}')}\n"
            f"{self.f.list_item(f'Игр сыграно: {stats[3] if stats else 0}')}\n"
            f"{self.f.list_item(f'Голосовых: {stats[4] if stats else 0}')}\n"
            f"{self.f.list_item(f'Фото: {stats[5] if stats else 0}')}\n"
            f"{self.f.list_item(f'Стикеров: {stats[6] if stats else 0}')}\n\n"
            f"{graph}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_top(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        top_coins = self.db.get_top("coins", 10)
        top_level = self.db.get_top("level", 10)
        top_boss = self.db.get_top("boss_kills", 10)
        
        text = self.f.header("ТОП ИГРОКОВ", "🏆") + "\n\n"
        
        text += self.f.section("ПО МОНЕТАМ", "💰") + "\n"
        for i, (name, value) in enumerate(top_coins, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
            text += f"{medal} **{i}.** {name} — {value} 🪙\n"
        
        text += "\n" + self.f.section("ПО УРОВНЮ", "📊") + "\n"
        for i, (name, value) in enumerate(top_level, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
            text += f"{medal} **{i}.** {name} — {value} ур.\n"
        
        text += "\n" + self.f.section("ПО УБИЙСТВУ БОССОВ", "👾") + "\n"
        for i, (name, value) in enumerate(top_boss, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
            text += f"{medal} **{i}.** {name} — {value} боссов\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_daily(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)
        
        if self.db.is_muted(user_id):
            remaining = self.db.get_mute_time(user_id)
            await update.message.reply_text(self.f.error(f"Вы замучены. Осталось: {remaining}"))
            return
        
        today = datetime.datetime.now().date()
        
        if user_data.get('last_daily'):
            last_date = datetime.datetime.fromisoformat(user_data['last_daily']).date()
            if last_date == today:
                await update.message.reply_text(self.f.error("Ты уже получал награду сегодня!"))
                return
        
        streak = self.db.add_daily_streak(user_id)
        
        coins = random.randint(100, 300)
        exp = random.randint(20, 60)
        energy = random.randint(10, 30)
        
        coins = int(coins * (1 + min(streak, 30) * 0.05))
        exp = int(exp * (1 + min(streak, 30) * 0.05))
        
        if self.is_vip(user_id):
            coins = int(coins * 1.5)
            exp = int(exp * 1.5)
        if self.is_premium(user_id):
            coins = int(coins * 2)
            exp = int(exp * 2)
        
        self.db.add_coins(user_id, coins)
        self.db.add_exp(user_id, exp)
        self.db.add_energy(user_id, energy)
        
        text = (
            self.f.header("ЕЖЕДНЕВНАЯ НАГРАДА", "🎁") + "\n\n"
            f"{self.f.list_item(f'Стрик: {streak} дней 🔥')}\n"
            f"{self.f.list_item(f'Монеты: +{coins} 🪙')}\n"
            f"{self.f.list_item(f'Опыт: +{exp} ✨')}\n"
            f"{self.f.list_item(f'Энергия: +{energy} ⚡')}\n\n"
            f"{self.f.note('Заходи завтра за новой наградой!')}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_weekly(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)
        
        last_weekly = user_data.get('last_weekly')
        if last_weekly:
            last = datetime.datetime.fromisoformat(last_weekly)
            if (datetime.datetime.now() - last).days < 7:
                await update.message.reply_text(self.f.error("Ты уже получал недельный бонус! Приходи через неделю."))
                return
        
        coins = random.randint(1000, 3000)
        diamonds = random.randint(10, 30)
        
        if self.is_vip(user_id):
            coins = int(coins * 1.5)
            diamonds = int(diamonds * 1.5)
        if self.is_premium(user_id):
            coins = int(coins * 2)
            diamonds = int(diamonds * 2)
        
        self.db.add_coins(user_id, coins)
        self.db.add_diamonds(user_id, diamonds)
        
        self.db.cursor.execute(
            "UPDATE users SET last_weekly = ? WHERE user_id = ?",
            (datetime.datetime.now(), user_id)
        )
        self.db.conn.commit()
        
        text = (
            self.f.header("НЕДЕЛЬНЫЙ БОНУС", "📅") + "\n\n"
            f"{self.f.list_item(f'Монеты: +{coins} 🪙')}\n"
            f"{self.f.list_item(f'Алмазы: +{diamonds} 💎')}\n\n"
            f"{self.f.note('Возвращайся через неделю!')}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_streak(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)
        
        streak = user_data.get('daily_streak', 0)
        last_daily = user_data.get('last_daily', 'никогда')
        
        if last_daily != 'никогда':
            last = datetime.datetime.fromisoformat(last_daily)
            days_missed = (datetime.datetime.now() - last).days
        else:
            days_missed = 0
        
        text = (
            self.f.header("ТВОЙ СТРИК", "🔥") + "\n\n"
            f"{self.f.list_item(f'Дней подряд: {streak}')}\n"
            f"{self.f.list_item(f'Последний вход: {last_daily[:10] if last_daily != "никогда" else "никогда"}')}\n"
            f"{self.f.list_item(f'Пропущено дней: {days_missed}')}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_rep(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(self.f.error("Укажи ник: /rep @username"))
            return
        
        query = context.args[0]
        target_user = self.db.get_user_by_name(query) or self.db.get_user_by_username(query)
        
        if not target_user:
            await update.message.reply_text(self.f.error(f"Пользователь не найден"))
            return
        
        user_id = update.effective_user.id
        if target_user['user_id'] == user_id:
            await update.message.reply_text(self.f.error("Нельзя дать репутацию самому себе"))
            return
        
        self.db.cursor.execute(
            "UPDATE users SET rep = rep + 1 WHERE user_id = ?",
            (target_user['user_id'],)
        )
        self.db.conn.commit()
        
        name = target_user.get('nickname') or target_user.get('first_name', 'Игрок')
        await update.message.reply_text(self.f.success(f"Репутация пользователя {name} повышена!"))
    
    # ========== СИСТЕМА БАНОВ И ПРЕДУПРЕЖДЕНИЙ ==========
    
    async def cmd_warn(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выдать предупреждение"""
        admin = update.effective_user
        admin_data = self.db.get_user_by_id(admin.id)
        
        if not self.has_permission(admin_data, 'moderator'):
            await update.message.reply_text(self.f.error("Недостаточно прав"))
            return
        
        if len(context.args) < 1:
            await update.message.reply_text(
                self.f.header("ВЫДАЧА ПРЕДУПРЕЖДЕНИЯ", "⚠️") + "\n\n" +
                self.f.command("warn @user [причина]", "выдать предупреждение") + "\n" +
                self.f.example("warn @user Флуд в чате")
            )
            return
        
        query = context.args[0]
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else "Нарушение"
        
        target_user = self.db.get_user_by_name(query) or self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(self.f.error(f"Пользователь '{query}' не найден"))
            return
        
        result = self.db.add_warn(target_user['user_id'], admin.id, reason)
        
        name = target_user.get('nickname') or target_user.get('first_name', 'Игрок')
        warns_count = result['warns_count']
        warns_display = "🔴" * warns_count + "⚪" * (3 - warns_count)
        
        text = (
            self.f.header("ПРЕДУПРЕЖДЕНИЕ", "⚠️") + "\n\n"
            f"{self.f.list_item(f'Пользователь: {self.f.user_link(target_user["user_id"], name)}')}\n"
            f"{self.f.list_item(f'Предупреждений: {warns_display} ({warns_count}/3)')}\n"
            f"{self.f.list_item(f'Причина: {reason}')}\n"
            f"{self.f.list_item(f'Админ: {self.f.user_link(admin.id, admin.first_name)}')}\n\n"
        )
        
        if warns_count >= 3:
            self.db.mute_user(target_user['user_id'], 1440, admin.id, "3 предупреждения")
            text += self.f.warning("Пользователь получил 3 варна и был замучен на 24 часа!")
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_warns(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список предупреждений пользователя"""
        if not context.args:
            await update.message.reply_text(self.f.error("Укажи ник: /warns @username"))
            return
        
        query = context.args[0]
        target_user = self.db.get_user_by_name(query) or self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(self.f.error(f"Пользователь не найден"))
            return
        
        warns_list = self.db.get_warns(target_user['user_id'])
        name = target_user.get('nickname') or target_user.get('first_name', 'Игрок')
        
        if not warns_list:
            await update.message.reply_text(self.f.info(f"У пользователя {name} нет предупреждений"))
            return
        
        text = self.f.header(f"ПРЕДУПРЕЖДЕНИЯ {name.upper()}", "📋") + "\n\n"
        
        for warn in warns_list:
            admin = self.db.get_user_by_id(warn['admin_id'])
            admin_name = admin.get('first_name', 'Неизвестно') if admin else 'Неизвестно'
            date = datetime.datetime.fromisoformat(warn['date']).strftime("%d.%m.%Y %H:%M")
            
            text += (
                f"**ID: {warn['id']}**\n"
                f"{self.f.list_item(f'Причина: {warn["reason"]}')}\n"
                f"{self.f.list_item(f'Админ: {admin_name}')}\n"
                f"{self.f.list_item(f'Дата: {date}')}\n\n"
            )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_my_warns(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Мои предупреждения"""
        user_id = update.effective_user.id
        warns_list = self.db.get_warns(user_id)
        
        if not warns_list:
            await update.message.reply_text(self.f.info("У тебя нет предупреждений"))
            return
        
        text = self.f.header("ТВОИ ПРЕДУПРЕЖДЕНИЯ", "📋") + "\n\n"
        
        for warn in warns_list:
            admin = self.db.get_user_by_id(warn['admin_id'])
            admin_name = admin.get('first_name', 'Неизвестно') if admin else 'Неизвестно'
            date = datetime.datetime.fromisoformat(warn['date']).strftime("%d.%m.%Y %H:%M")
            
            text += (
                f"**ID: {warn['id']}**\n"
                f"{self.f.list_item(f'Причина: {warn["reason"]}')}\n"
                f"{self.f.list_item(f'Админ: {admin_name}')}\n"
                f"{self.f.list_item(f'Дата: {date}')}\n\n"
            )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_unwarn(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Снять последнее предупреждение"""
        admin = update.effective_user
        admin_data = self.db.get_user_by_id(admin.id)
        
        if not self.has_permission(admin_data, 'moderator'):
            await update.message.reply_text(self.f.error("Недостаточно прав"))
            return
        
        if not context.args:
            await update.message.reply_text(self.f.error("Укажи ник: /unwarn @username"))
            return
        
        query = context.args[0]
        target_user = self.db.get_user_by_name(query) or self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(self.f.error(f"Пользователь не найден"))
            return
        
        removed = self.db.remove_last_warn(target_user['user_id'])
        name = target_user.get('nickname') or target_user.get('first_name', 'Игрок')
        
        if not removed:
            await update.message.reply_text(self.f.info(f"У пользователя {name} нет предупреждений"))
            return
        
        text = (
            self.f.header("СНЯТИЕ ПРЕДУПРЕЖДЕНИЯ", "✅") + "\n\n"
            f"{self.f.list_item(f'Пользователь: {self.f.user_link(target_user["user_id"], name)}')}\n"
            f"{self.f.list_item(f'Снято предупреждение ID: {removed["id"]}')}\n"
            f"{self.f.list_item(f'Причина: {removed["reason"]}')}\n"
            f"{self.f.list_item(f'Админ: {self.f.user_link(admin.id, admin.first_name)}')}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_unwarn_all(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Снять все предупреждения"""
        admin = update.effective_user
        admin_data = self.db.get_user_by_id(admin.id)
        
        if not self.has_permission(admin_data, 'moderator'):
            await update.message.reply_text(self.f.error("Недостаточно прав"))
            return
        
        if not context.args:
            await update.message.reply_text(self.f.error("Укажи ник: /unwarnall @username"))
            return
        
        query = context.args[0]
        target_user = self.db.get_user_by_name(query) or self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(self.f.error(f"Пользователь не найден"))
            return
        
        self.db.remove_all_warns(target_user['user_id'])
        name = target_user.get('nickname') or target_user.get('first_name', 'Игрок')
        
        text = (
            self.f.header("СНЯТИЕ ВСЕХ ПРЕДУПРЕЖДЕНИЙ", "✅") + "\n\n"
            f"{self.f.list_item(f'Пользователь: {self.f.user_link(target_user["user_id"], name)}')}\n"
            f"{self.f.list_item(f'Снято все предупреждения')}\n"
            f"{self.f.list_item(f'Админ: {self.f.user_link(admin.id, admin.first_name)}')}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_warn_limit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установить лимит предупреждений (заглушка)"""
        await update.message.reply_text(self.f.info("Функция будет доступна в следующем обновлении"))
    
    # ========== МУТ ==========
    
    async def cmd_mute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Заглушить пользователя"""
        admin = update.effective_user
        admin_data = self.db.get_user_by_id(admin.id)
        
        if not self.has_permission(admin_data, 'moderator'):
            await update.message.reply_text(self.f.error("Недостаточно прав"))
            return
        
        if len(context.args) < 2:
            await update.message.reply_text(
                self.f.header("МУТ ПОЛЬЗОВАТЕЛЯ", "🔇") + "\n\n" +
                self.f.command("mute @user [минуты] [причина]", "заглушить пользователя") + "\n" +
                self.f.example("mute @user 30 Флуд в чате")
            )
            return
        
        query = context.args[0]
        try:
            minutes = int(context.args[1])
        except:
            await update.message.reply_text(self.f.error("Время должно быть числом (в минутах)"))
            return
        
        reason = " ".join(context.args[2:]) if len(context.args) > 2 else "Нарушение"
        
        target_user = self.db.get_user_by_name(query) or self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(self.f.error(f"Пользователь '{query}' не найден"))
            return
        
        mute_until = self.db.mute_user(target_user['user_id'], minutes, admin.id, reason)
        name = target_user.get('nickname') or target_user.get('first_name', 'Игрок')
        
        until_str = mute_until.strftime("%d.%m.%Y %H:%M")
        
        text = (
            self.f.header("МУТ", "🔇") + "\n\n"
            f"{self.f.list_item(f'Пользователь: {self.f.user_link(target_user["user_id"], name)}')}\n"
            f"{self.f.list_item(f'Срок: {minutes} минут')}\n"
            f"{self.f.list_item(f'До: {until_str}')}\n"
            f"{self.f.list_item(f'Причина: {reason}')}\n"
            f"{self.f.list_item(f'Админ: {self.f.user_link(admin.id, admin.first_name)}')}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_unmute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Снять мут"""
        admin = update.effective_user
        admin_data = self.db.get_user_by_id(admin.id)
        
        if not self.has_permission(admin_data, 'moderator'):
            await update.message.reply_text(self.f.error("Недостаточно прав"))
            return
        
        if not context.args:
            await update.message.reply_text(self.f.error("Укажи ник: /unmute @username"))
            return
        
        query = context.args[0]
        target_user = self.db.get_user_by_name(query) or self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(self.f.error(f"Пользователь не найден"))
            return
        
        if not self.db.is_muted(target_user['user_id']):
            name = target_user.get('nickname') or target_user.get('first_name', 'Игрок')
            await update.message.reply_text(self.f.info(f"Пользователь {name} не в муте"))
            return
        
        self.db.unmute_user(target_user['user_id'])
        name = target_user.get('nickname') or target_user.get('first_name', 'Игрок')
        
        text = (
            self.f.header("СНЯТИЕ МУТА", "✅") + "\n\n"
            f"{self.f.list_item(f'Пользователь: {self.f.user_link(target_user["user_id"], name)}')}\n"
            f"{self.f.list_item(f'Админ: {self.f.user_link(admin.id, admin.first_name)}')}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_mutelist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список замученных"""
        muted = self.db.get_muted_users()
        
        if not muted:
            await update.message.reply_text(self.f.info("Нет пользователей в муте"))
            return
        
        text = self.f.header("СПИСОК ЗАМУЧЕННЫХ", "🔇") + "\n\n"
        
        for user_id, name, mute_until in muted:
            if mute_until:
                until = datetime.datetime.fromisoformat(mute_until).strftime("%d.%m.%Y %H:%M")
            else:
                until = "неизвестно"
            
            text += f"{self.f.list_item(f'{name}: до {until}')}\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_check_mute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Проверить наличие мута"""
        if not context.args:
            await update.message.reply_text(self.f.error("Укажи ник: /checkmute @username"))
            return
        
        query = context.args[0]
        target_user = self.db.get_user_by_name(query) or self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(self.f.error(f"Пользователь не найден"))
            return
        
        name = target_user.get('nickname') or target_user.get('first_name', 'Игрок')
        
        if self.db.is_muted(target_user['user_id']):
            remaining = self.db.get_mute_time(target_user['user_id'])
            await update.message.reply_text(self.f.warning(f"{name} в муте. Осталось: {remaining}"))
        else:
            await update.message.reply_text(self.f.success(f"{name} не в муте"))
    
    # ========== БАН ==========
    
    async def cmd_ban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Забанить пользователя"""
        admin = update.effective_user
        admin_data = self.db.get_user_by_id(admin.id)
        
        if not self.has_permission(admin_data, 'moderator'):
            await update.message.reply_text(self.f.error("Недостаточно прав"))
            return
        
        if len(context.args) < 1:
            await update.message.reply_text(
                self.f.header("БАН ПОЛЬЗОВАТЕЛЯ", "🔴") + "\n\n" +
                self.f.command("ban @user [срок] [причина]", "заблокировать пользователя") + "\n" +
                self.f.example("ban @user 7д Спам") + "\n" +
                self.f.example("ban @user навсегда Рейд") + "\n\n" +
                self.f.note("Срок: 1д, 1н, 1м, 1г или навсегда")
            )
            return
        
        query = context.args[0]
        period = context.args[1] if len(context.args) > 1 else "навсегда"
        reason = " ".join(context.args[2:]) if len(context.args) > 2 else "Нарушение правил"
        
        target_user = self.db.get_user_by_name(query) or self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(self.f.error(f"Пользователь '{query}' не найден"))
            return
        
        ban_until = self.db.ban_user(target_user['user_id'], admin.id, reason, period)
        name = target_user.get('nickname') or target_user.get('first_name', 'Игрок')
        
        period_text = f"на {period}" if period != "навсегда" else "навсегда"
        
        text = (
            self.f.header("БАН", "🔴") + "\n\n"
            f"{self.f.list_item(f'Пользователь: {self.f.user_link(target_user["user_id"], name)}')}\n"
            f"{self.f.list_item(f'Срок: {period_text}')}\n"
            f"{self.f.list_item(f'Причина: {reason}')}\n"
            f"{self.f.list_item(f'Админ: {self.f.user_link(admin.id, admin.first_name)}')}\n\n"
            f"{self.f.note('Если хочешь вернуться, напиши забанившему модератору')}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
        # Удаляем сообщение пользователя, если оно есть (опционально)
        if update.message.reply_to_message:
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=update.message.reply_to_message.message_id
                )
            except:
                pass
    
    async def cmd_unban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Разбанить пользователя"""
        admin = update.effective_user
        admin_data = self.db.get_user_by_id(admin.id)
        
        if not self.has_permission(admin_data, 'moderator'):
            await update.message.reply_text(self.f.error("Недостаточно прав"))
            return
        
        if not context.args:
            await update.message.reply_text(self.f.error("Укажи ник: /unban @username"))
            return
        
        query = context.args[0]
        target_user = self.db.get_user_by_name(query) or self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(self.f.error(f"Пользователь не найден"))
            return
        
        if not self.db.is_banned(target_user['user_id']):
            name = target_user.get('nickname') or target_user.get('first_name', 'Игрок')
            await update.message.reply_text(self.f.info(f"Пользователь {name} не в бане"))
            return
        
        self.db.unban_user(target_user['user_id'])
        name = target_user.get('nickname') or target_user.get('first_name', 'Игрок')
        
        text = (
            self.f.header("РАЗБАН", "✅") + "\n\n"
            f"{self.f.list_item(f'Пользователь: {self.f.user_link(target_user["user_id"], name)}')}\n"
            f"{self.f.list_item(f'Админ: {self.f.user_link(admin.id, admin.first_name)}')}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_banlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список забаненных"""
        page = 1
        if context.args and context.args[0].isdigit():
            page = int(context.args[0])
        
        bans, total = self.db.get_banlist(page)
        total_pages = (total + 9) // 10
        
        if not bans:
            await update.message.reply_text(self.f.info("Список забаненных пуст"))
            return
        
        text = self.f.header(f"СПИСОК ЗАБАНЕННЫХ", "📋") + "\n"
        text += f"Страница {page}/{total_pages}\n\n"
        
        for i, ban in enumerate(bans, 1):
            date = datetime.datetime.fromisoformat(ban['date']).strftime("%d.%m.%Y") if ban['date'] else "неизвестно"
            text += (
                f"{i}. {ban['name']}\n"
                f"└ Причина: {ban['reason']}\n"
                f"└ Дата: {date}\n"
                f"└ Забанил: {ban['admin']}\n\n"
            )
        
        # Создаем клавиатуру для навигации
        keyboard = []
        nav_row = []
        
        if page > 1:
            nav_row.append(InlineKeyboardButton("◀️", callback_data=f"banlist_{page-1}"))
        if page < total_pages:
            nav_row.append(InlineKeyboardButton("▶️", callback_data=f"banlist_{page+1}"))
        
        if nav_row:
            keyboard.append(nav_row)
        
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def cmd_ban_reason(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать причину бана"""
        if not context.args:
            await update.message.reply_text(self.f.error("Укажи ник: /banreason @username"))
            return
        
        query = context.args[0]
        target_user = self.db.get_user_by_name(query) or self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(self.f.error(f"Пользователь не найден"))
            return
        
        ban_info = self.db.get_ban_reason(target_user['user_id'])
        name = target_user.get('nickname') or target_user.get('first_name', 'Игрок')
        
        if not ban_info:
            await update.message.reply_text(self.f.info(f"Пользователь {name} не забанен"))
            return
        
        date = datetime.datetime.fromisoformat(ban_info['date']).strftime("%d.%m.%Y %H:%M") if ban_info['date'] else "неизвестно"
        
        text = (
            self.f.header("ПРИЧИНА БАНА", "🔴") + "\n\n"
            f"{self.f.list_item(f'Пользователь: {name}')}\n"
            f"{self.f.list_item(f'Причина: {ban_info["reason"]}')}\n"
            f"{self.f.list_item(f'Дата: {date}')}\n"
            f"{self.f.list_item(f'Админ: {ban_info["admin_name"]}')}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_kick(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Исключить пользователя"""
        admin = update.effective_user
        admin_data = self.db.get_user_by_id(admin.id)
        
        if not self.has_permission(admin_data, 'moderator'):
            await update.message.reply_text(self.f.error("Недостаточно прав"))
            return
        
        if not context.args:
            await update.message.reply_text(
                self.f.header("ИСКЛЮЧЕНИЕ", "👢") + "\n\n" +
                self.f.command("kick @user [причина]", "исключить пользователя")
            )
            return
        
        query = context.args[0]
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else "Без причины"
        
        target_user = self.db.get_user_by_name(query) or self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(self.f.error(f"Пользователь '{query}' не найден"))
            return
        
        name = target_user.get('nickname') or target_user.get('first_name', 'Игрок')
        
        text = (
            self.f.header("ИСКЛЮЧЕНИЕ", "👢") + "\n\n"
            f"{self.f.list_item(f'Пользователь: {self.f.user_link(target_user["user_id"], name)}')}\n"
            f"{self.f.list_item(f'Причина: {reason}')}\n"
            f"{self.f.list_item(f'Админ: {self.f.user_link(admin.id, admin.first_name)}')}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
        # Здесь должен быть код для исключения пользователя из чата
        # await context.bot.ban_chat_member(chat_id, target_user['user_id'])
        # await context.bot.unban_chat_member(chat_id, target_user['user_id'])
    
    async def cmd_amnesty(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Амнистия для всех забаненных"""
        admin = update.effective_user
        admin_data = self.db.get_user_by_id(admin.id)
        
        if not self.has_permission(admin_data, 'admin'):
            await update.message.reply_text(self.f.error("Недостаточно прав. Требуется администратор."))
            return
        
        # Получаем всех забаненных
        self.db.cursor.execute("SELECT user_id FROM users WHERE banned = 1")
        banned_users = self.db.cursor.fetchall()
        
        for user_id in banned_users:
            self.db.unban_user(user_id[0])
        
        text = (
            self.f.header("АМНИСТИЯ", "🕊️") + "\n\n"
            f"{self.f.list_item(f'Разбанено пользователей: {len(banned_users)}')}\n"
            f"{self.f.list_item(f'Админ: {self.f.user_link(admin.id, admin.first_name)}')}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    # ========== БОССЫ ==========
    
    async def cmd_boss_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список боссов"""
        bosses = self.db.get_bosses(alive_only=True)
        
        if not bosses:
            self.db.respawn_bosses()
            bosses = self.db.get_bosses(alive_only=True)
        
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)
        
        damage_bonus = 1.0
        if self.db.is_vip(user_id):
            damage_bonus += 0.2
        if self.db.is_premium(user_id):
            damage_bonus += 0.3
        
        player_damage = user_data.get('damage', 10) * damage_bonus
        
        text = self.f.header("АРЕНА БОССА", "👊") + "\n\n"
        text += "↪️ Твоя цель: убить босса.\n\n"
        
        if bosses:
            boss = bosses[0]
            health_percent = (boss[3] / boss[4]) * 100
            health_bar = self.f.progress(boss[3], boss[4], 15)
            
            text += (
                f"💀 **Текущий босс:** {boss[1]} (ур. {boss[2]})\n"
                f"💫 Урон от босса: {max(1, boss[5]-5)}-{boss[5]+5} HP\n"
                f"🖤 Жизни босса: {health_bar}\n"
                f"🗡 Твой урон: {player_damage:.1f}⚔️ (сила: {damage_bonus*100:.0f}%)\n"
                f"❤️ Твое здоровье: {user_data.get('health', 100)}/100\n\n"
            )
            
            text += "Другие боссы:\n"
            for i, b in enumerate(bosses[1:], 2):
                text += f"{i}. {b[1]} (❤️ {b[3]}/{b[4]})\n"
        
        text += (
            "\n" + self.f.section("КОМАНДЫ", "⏺") + "\n"
            f"{self.f.command('bossfight [ID]', 'атаковать босса')}\n"
            f"{self.f.command('regen', 'восстановить здоровье')}\n"
            f"{self.f.command('bossinfo [ID]', 'информация о боссе')}\n"
            f"{self.f.command('bossstats', 'статистика битв')}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_boss_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о боссе"""
        if not context.args:
            await update.message.reply_text(self.f.error("Укажи ID босса: /bossinfo 1"))
            return
        
        try:
            boss_id = int(context.args[0])
        except:
            await update.message.reply_text(self.f.error("Неправильный ID босса"))
            return
        
        boss = self.db.get_boss(boss_id)
        if not boss:
            await update.message.reply_text(self.f.error("Босс не найден"))
            return
        
        status = "👾 ЖИВ" if boss[8] else "💀 ПОВЕРЖЕН"
        health_percent = (boss[3] / boss[4]) * 100
        health_bar = self.f.progress(boss[3], boss[4], 20)
        
        text = (
            self.f.header(f"БОСС: {boss[1]}", "👾") + "\n\n"
            f"{self.f.list_item(f'Уровень: {boss[2]}')}\n"
            f"{self.f.list_item(f'❤️ Здоровье: {boss[3]}/{boss[4]}')}\n"
            f"{health_bar}\n"
            f"{self.f.list_item(f'⚔️ Урон: {boss[5]}')}\n"
            f"{self.f.list_item(f'💰 Награда: {boss[6]} 🪙')}\n"
            f"{self.f.list_item(f'📊 Статус: {status}')}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_boss_fight(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Битва с боссом"""
        user = update.effective_user
        user_data = self.db.get_user_by_id(user.id)
        
        if self.db.is_muted(user.id):
            remaining = self.db.get_mute_time(user.id)
            await update.message.reply_text(self.f.error(f"Вы замучены. Осталось: {remaining}"))
            return
        
        if not context.args:
            await update.message.reply_text(self.f.error("Укажи ID босса: /bossfight 1"))
            return
        
        try:
            boss_id = int(context.args[0])
        except:
            await update.message.reply_text(self.f.error("Неправильный ID босса"))
            return
        
        boss = self.db.get_boss(boss_id)
        if not boss or not boss[8]:
            await update.message.reply_text(self.f.error("Босс уже повержен или не найден"))
            return
        
        if user_data['energy'] < 10:
            await update.message.reply_text(self.f.error("Нужно 10 энергии для битвы! Используй /regen"))
            return
        
        self.db.add_energy(user.id, -10)
        
        damage_bonus = 1.0
        if self.db.is_vip(user.id):
            damage_bonus += 0.2
        if self.db.is_premium(user.id):
            damage_bonus += 0.3
        
        player_damage = int(user_data['damage'] * damage_bonus) + random.randint(-5, 5)
        boss_damage = boss[5] + random.randint(-5, 5)
        player_taken = max(1, boss_damage - user_data['armor'] // 2)
        
        boss_killed = self.db.damage_boss(boss_id, player_damage)
        self.db.damage(user.id, player_taken)
        
        text = self.f.header("БИТВА С БОССОМ", "⚔️") + "\n\n"
        text += f"{self.f.list_item(f'Ты нанес: {player_damage} урона')}\n"
        text += f"{self.f.list_item(f'Босс нанес: {player_taken} урона')}\n\n"
        
        if boss_killed:
            reward = boss[6] * (1 + user_data['level'] // 10)
            if self.db.is_vip(user.id):
                reward = int(reward * 1.5)
            if self.db.is_premium(user.id):
                reward = int(reward * 2)
            
            self.db.add_coins(user.id, reward)
            self.db.add_boss_kill(user.id)
            self.db.add_exp(user.id, boss[2] * 10)
            
            text += self.f.success(f"ПОБЕДА!") + "\n"
            text += f"{self.f.list_item(f'💰 Награда: {reward} монет')}\n"
            text += f"{self.f.list_item(f'✨ Опыт: +{boss[2] * 10}')}\n\n"
            
            # Проверка достижений
            boss_kills = user_data.get('boss_kills', 0) + 1
            if boss_kills == 10:
                self.db.add_achievement(user.id, "👾 Охотник на боссов", "Убито 10 боссов", 500)
            elif boss_kills == 50:
                self.db.add_achievement(user.id, "👾 Легендарный охотник", "Убито 50 боссов", 2000)
        else:
            boss_info = self.db.get_boss(boss_id)
            text += f"{self.f.warning('Босс еще жив!')}\n"
            text += f"❤️ Осталось: {boss_info[3]} здоровья\n\n"
        
        if user_data['health'] <= player_taken:
            self.db.heal(user.id, 50)
            text += self.f.info("Ты погиб в бою, но воскрешен с 50❤️")
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_regen(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Регенерация здоровья"""
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)
        
        cost = 20
        if user_data['coins'] < cost:
            await update.message.reply_text(self.f.error(f"Недостаточно монет! Нужно {cost} 🪙"))
            return
        
        self.db.add_coins(user_id, -cost)
        self.db.heal(user_id, 50)
        self.db.add_energy(user_id, 20)
        
        await update.message.reply_text(
            self.f.success("Регенерация завершена!") + "\n" +
            f"{self.f.list_item('❤️ Здоровье +50')}\n"
            f"{self.f.list_item('⚡ Энергия +20')}",
            parse_mode='Markdown'
        )
    
    async def cmd_boss_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Статистика битв с боссами"""
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)
        
        text = (
            self.f.header("СТАТИСТИКА БОССОВ", "👾") + "\n\n"
            f"{self.f.list_item(f'Боссов убито: {user_data.get("boss_kills", 0)} 💀')}\n"
            f"{self.f.list_item(f'Урон: {user_data.get("damage", 10)} ⚔️')}\n"
            f"{self.f.list_item(f'Броня: {user_data.get("armor", 0)} 🛡')}\n"
            f"{self.f.list_item(f'Здоровье: {user_data.get("health", 100)} ❤️')}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    # ========== КАЗИНО ==========
    
    async def cmd_casino(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Казино"""
        text = (
            self.f.header("КАЗИНО «СПЕКТР»", "🎰") + "\n\n"
            f"{self.f.command('roulette [ставка] [цвет/число]', 'рулетка')}\n"
            f"{self.f.command('dice [ставка]', 'кости')}\n"
            f"{self.f.command('blackjack [ставка]', 'блэкджек')}\n"
            f"{self.f.command('slots [ставка]', 'слоты')}\n"
            f"{self.f.command('rps', 'камень-ножницы-бумага')}\n\n"
            f"{self.f.example('roulette 10 red')}\n"
            f"{self.f.example('dice 50')}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
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
            await update.message.reply_text(self.f.error(f"У тебя только {user_data['coins']} 🪙"))
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
            self.db.cursor.execute("UPDATE users SET casino_wins = casino_wins + 1 WHERE user_id = ?", (user_id,))
            self.db.conn.commit()
            result_text = self.f.success(f"Ты выиграл {winnings} 🪙!")
        else:
            self.db.add_coins(user_id, -bet)
            self.db.cursor.execute("UPDATE users SET casino_losses = casino_losses + 1 WHERE user_id = ?", (user_id,))
            self.db.conn.commit()
            result_text = self.f.error(f"Ты проиграл {bet} 🪙")
        
        text = (
            self.f.header("РУЛЕТКА", "🎰") + "\n\n"
            f"{self.f.list_item(f'Ставка: {bet} 🪙')}\n"
            f"{self.f.list_item(f'Выбрано: {choice}')}\n"
            f"{self.f.list_item(f'Выпало: {result_num} {result_color}')}\n\n"
            f"{result_text}"
        )
        
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
            await update.message.reply_text(self.f.error(f"У тебя только {user_data['coins']} 🪙"))
            return
        
        dice1 = random.randint(1, 6)
        dice2 = random.randint(1, 6)
        total = dice1 + dice2
        
        if total in [7, 11]:
            win = bet * 2
            result_text = self.f.success(f"Ты выиграл {win} 🪙!")
        elif total in [2, 3, 12]:
            win = 0
            result_text = self.f.error(f"Ты проиграл {bet} 🪙")
        else:
            win = bet
            result_text = self.f.info(f"Ничья, ставка возвращена: {bet} 🪙")
        
        if win > 0:
            self.db.add_coins(user_id, win)
            self.db.cursor.execute("UPDATE users SET casino_wins = casino_wins + 1 WHERE user_id = ?", (user_id,))
        else:
            self.db.add_coins(user_id, -bet)
            self.db.cursor.execute("UPDATE users SET casino_losses = casino_losses + 1 WHERE user_id = ?", (user_id,))
        
        self.db.conn.commit()
        
        text = (
            self.f.header("КОСТИ", "🎲") + "\n\n"
            f"{self.f.list_item(f'Ставка: {bet} 🪙')}\n"
            f"{self.f.list_item(f'Кубики: {dice1} + {dice2}')}\n"
            f"{self.f.list_item(f'Сумма: {total}')}\n\n"
            f"{result_text}"
        )
        
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
            await update.message.reply_text(self.f.error(f"У тебя только {user_data['coins']} 🪙"))
            return
        
        player_card1 = random.randint(1, 11)
        player_card2 = random.randint(1, 11)
        player_total = player_card1 + player_card2
        
        dealer_card1 = random.randint(1, 11)
        dealer_card2 = random.randint(1, 11)
        dealer_total = dealer_card1 + dealer_card2
        
        if player_total > 21:
            result = "lose"
            result_text = self.f.error(f"Ты проиграл {bet} 🪙")
        elif dealer_total > 21:
            result = "win"
            win = bet * 2
            result_text = self.f.success(f"Ты выиграл {win} 🪙!")
        elif player_total > dealer_total:
            result = "win"
            win = bet * 2
            result_text = self.f.success(f"Ты выиграл {win} 🪙!")
        elif player_total < dealer_total:
            result = "lose"
            result_text = self.f.error(f"Ты проиграл {bet} 🪙")
        else:
            result = "draw"
            result_text = self.f.info(f"Ничья, ставка возвращена: {bet} 🪙")
        
        if result == "win":
            self.db.add_coins(user_id, win)
            self.db.cursor.execute("UPDATE users SET casino_wins = casino_wins + 1 WHERE user_id = ?", (user_id,))
        elif result == "lose":
            self.db.add_coins(user_id, -bet)
            self.db.cursor.execute("UPDATE users SET casino_losses = casino_losses + 1 WHERE user_id = ?", (user_id,))
        
        self.db.conn.commit()
        
        text = (
            self.f.header("БЛЭКДЖЕК", "🃏") + "\n\n"
            f"{self.f.list_item(f'Твои карты: {player_card1} + {player_card2} = {player_total}')}\n"
            f"{self.f.list_item(f'Карты дилера: {dealer_card1} + {dealer_card2} = {dealer_total}')}\n\n"
            f"{result_text}"
        )
        
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
            await update.message.reply_text(self.f.error(f"У тебя только {user_data['coins']} 🪙"))
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
            result_text = self.f.success("ДЖЕКПОТ!")
        elif len(set(spin)) == 2:
            win = bet * 2
            result_text = self.f.success("Маленький выигрыш!")
        else:
            win = 0
            result_text = self.f.error("Не повезло...")
        
        if win > 0:
            self.db.add_coins(user_id, win)
            self.db.cursor.execute("UPDATE users SET casino_wins = casino_wins + 1 WHERE user_id = ?", (user_id,))
        else:
            self.db.add_coins(user_id, -bet)
            self.db.cursor.execute("UPDATE users SET casino_losses = casino_losses + 1 WHERE user_id = ?", (user_id,))
        
        self.db.conn.commit()
        
        text = (
            self.f.header("СЛОТЫ", "🎰") + "\n\n"
            f"{' '.join(spin)}\n\n"
            f"{result_text}\n"
            f"{'💰 +' + str(win) + ' 🪙' if win > 0 else '💸 -' + str(bet) + ' 🪙'}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_rps(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Камень-ножницы-бумага"""
        keyboard = [
            [
                InlineKeyboardButton("🪨 Камень", callback_data="rps_rock"),
                InlineKeyboardButton("✂️ Ножницы", callback_data="rps_scissors"),
                InlineKeyboardButton("📄 Бумага", callback_data="rps_paper")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = (
            self.f.header("КАМЕНЬ-НОЖНИЦЫ-БУМАГА", "✊") + "\n\n"
            "🪨 Камень побеждает Ножницы\n"
            "✂️ Ножницы побеждают Бумагу\n"
            "📄 Бумага побеждает Камень\n\n"
            "**Выбери свой ход:**"
        )
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def cmd_rps_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Статистика КНБ"""
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)
        
        wins = user_data.get('rps_wins', 0)
        losses = user_data.get('rps_losses', 0)
        draws = user_data.get('rps_draws', 0)
        total = wins + losses + draws
        
        winrate = (wins / total * 100) if total > 0 else 0
        
        text = (
            self.f.header("СТАТИСТИКА КНБ", "✊") + "\n\n"
            f"{self.f.list_item(f'Побед: {wins} 🏆')}\n"
            f"{self.f.list_item(f'Поражений: {losses} 💔')}\n"
            f"{self.f.list_item(f'Ничьих: {draws} 🤝')}\n"
            f"{self.f.list_item(f'Всего игр: {total} 🎮')}\n"
            f"{self.f.list_item(f'Винрейт: {winrate:.1f}% 📊')}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_casino_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Статистика казино"""
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)
        
        wins = user_data.get('casino_wins', 0)
        losses = user_data.get('casino_losses', 0)
        total = wins + losses
        
        winrate = (wins / total * 100) if total > 0 else 0
        
        text = (
            self.f.header("СТАТИСТИКА КАЗИНО", "🎰") + "\n\n"
            f"{self.f.list_item(f'Побед: {wins} 🏆')}\n"
            f"{self.f.list_item(f'Поражений: {losses} 💔')}\n"
            f"{self.f.list_item(f'Всего игр: {total} 🎮')}\n"
            f"{self.f.list_item(f'Винрейт: {winrate:.1f}% 📊')}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    # ========== ЭКОНОМИКА ==========
    
    async def cmd_shop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Магазин"""
        text = (
            self.f.header("МАГАЗИН «СПЕКТР»", "🏪") + "\n\n"
            self.f.section("ЗЕЛЬЯ", "💊") + "\n"
            f"{self.f.command('buy зелье здоровья', '50 🪙 (❤️+30)')}\n"
            f"{self.f.command('buy большое зелье', '100 🪙 (❤️+70)')}\n\n"
            self.f.section("ОРУЖИЕ", "⚔️") + "\n"
            f"{self.f.command('buy меч', '200 🪙 (⚔️+10)')}\n"
            f"{self.f.command('buy легендарный меч', '500 🪙 (⚔️+30)')}\n\n"
            self.f.section("БРОНЯ", "🛡") + "\n"
            f"{self.f.command('buy щит', '150 🪙 (🛡+5)')}\n"
            f"{self.f.command('buy доспехи', '400 🪙 (🛡+15)')}\n\n"
            self.f.section("ЭНЕРГИЯ", "⚡") + "\n"
            f"{self.f.command('buy энергетик', '30 🪙 (⚡+20)')}\n"
            f"{self.f.command('buy батарейка', '80 🪙 (⚡+50)')}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_buy(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Купить предмет"""
        if not context.args:
            await update.message.reply_text(self.f.error("Укажи предмет: /buy меч"))
            return
        
        item = " ".join(context.args).lower()
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)
        
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
            await update.message.reply_text(self.f.error("Такого предмета нет в магазине"))
            return
        
        item_data = items[item]
        
        if user_data['coins'] < item_data['price']:
            await update.message.reply_text(self.f.error(f"Недостаточно монет! Нужно {item_data['price']} 🪙"))
            return
        
        self.db.add_coins(user_id, -item_data['price'])
        
        if 'heal' in item_data:
            self.db.heal(user_id, item_data['heal'])
            await update.message.reply_text(self.f.success(f"Здоровье +{item_data['heal']}❤️"))
        
        elif 'damage' in item_data:
            self.db.cursor.execute(
                "UPDATE users SET damage = damage + ? WHERE user_id = ?",
                (item_data['damage'], user_id)
            )
            self.db.conn.commit()
            await update.message.reply_text(self.f.success(f"Урон +{item_data['damage']}⚔️"))
        
        elif 'armor' in item_data:
            self.db.cursor.execute(
                "UPDATE users SET armor = armor + ? WHERE user_id = ?",
                (item_data['armor'], user_id)
            )
            self.db.conn.commit()
            await update.message.reply_text(self.f.success(f"Броня +{item_data['armor']}🛡"))
        
        elif 'energy' in item_data:
            self.db.add_energy(user_id, item_data['energy'])
            await update.message.reply_text(self.f.success(f"Энергия +{item_data['energy']}⚡"))
    
    async def cmd_inventory(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Инвентарь"""
        await update.message.reply_text(self.f.info("Инвентарь будет доступен в следующем обновлении"))
    
    async def cmd_pay(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Перевести монеты"""
        if len(context.args) < 2:
            await update.message.reply_text(self.f.error("Использование: /pay @ник сумма"))
            return
        
        query = context.args[0]
        try:
            amount = int(context.args[1])
        except:
            await update.message.reply_text(self.f.error("Сумма должна быть числом"))
            return
        
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)
        
        target_user = self.db.get_user_by_name(query) or self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(self.f.error(f"Пользователь не найден"))
            return
        
        if target_user['user_id'] == user_id:
            await update.message.reply_text(self.f.error("Нельзя перевести самому себе"))
            return
        
        if user_data['coins'] < amount:
            await update.message.reply_text(self.f.error(f"Недостаточно монет! У тебя {user_data['coins']} 🪙"))
            return
        
        self.db.add_coins(user_id, -amount)
        self.db.add_coins(target_user['user_id'], amount)
        
        name = target_user.get('nickname') or target_user.get('first_name', 'Игрок')
        
        text = (
            self.f.header("ПЕРЕВОД", "💰") + "\n\n"
            f"{self.f.list_item(f'Получатель: {name}')}\n"
            f"{self.f.list_item(f'Сумма: {amount} 🪙')}\n"
            f"{self.f.list_item(f'Отправитель: {update.effective_user.first_name}')}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_pay_diamond(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Перевести алмазы"""
        if len(context.args) < 2:
            await update.message.reply_text(self.f.error("Использование: /paydiamond @ник сумма"))
            return
        
        query = context.args[0]
        try:
            amount = int(context.args[1])
        except:
            await update.message.reply_text(self.f.error("Сумма должна быть числом"))
            return
        
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)
        
        if not self.is_premium(user_id):
            await update.message.reply_text(self.f.error("Перевод алмазов доступен только PREMIUM пользователям"))
            return
        
        target_user = self.db.get_user_by_name(query) or self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(self.f.error(f"Пользователь не найден"))
            return
        
        if target_user['user_id'] == user_id:
            await update.message.reply_text(self.f.error("Нельзя перевести самому себе"))
            return
        
        if user_data['diamonds'] < amount:
            await update.message.reply_text(self.f.error(f"Недостаточно алмазов! У тебя {user_data['diamonds']} 💎"))
            return
        
        self.db.add_diamonds(user_id, -amount)
        self.db.add_diamonds(target_user['user_id'], amount)
        
        name = target_user.get('nickname') or target_user.get('first_name', 'Игрок')
        
        text = (
            self.f.header("ПЕРЕВОД АЛМАЗОВ", "💎") + "\n\n"
            f"{self.f.list_item(f'Получатель: {name}')}\n"
            f"{self.f.list_item(f'Сумма: {amount} 💎')}\n"
            f"{self.f.list_item(f'Отправитель: {update.effective_user.first_name}')}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_donate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Привилегии"""
        text = (
            self.f.header("ПРИВИЛЕГИИ «СПЕКТР»", "💎") + "\n\n"
            self.f.section("VIP СТАТУС", "🌟") + "\n"
            f"Цена: {VIP_PRICE} 🪙 / {VIP_DAYS} дней\n"
            f"{self.f.list_item('Урон в битвах +20%')}\n"
            f"{self.f.list_item('Награда с боссов +50%')}\n"
            f"{self.f.list_item('Ежедневный бонус +50%')}\n"
            f"{self.f.list_item('Нет спам-фильтра')}\n\n"
            self.f.section("PREMIUM СТАТУС", "💎") + "\n"
            f"Цена: {PREMIUM_PRICE} 🪙 / {PREMIUM_DAYS} дней\n"
            f"{self.f.list_item('Все бонусы VIP')}\n"
            f"{self.f.list_item('Урон в битвах +50%')}\n"
            f"{self.f.list_item('Награда с боссов +100%')}\n"
            f"{self.f.list_item('Ежедневный бонус +100%')}\n\n"
            f"Купить: /vip или /premium\n"
            f"👑 По вопросам: {OWNER_USERNAME}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_vip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Купить VIP"""
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)
        
        if user_data['coins'] < VIP_PRICE:
            await update.message.reply_text(self.f.error(f"Недостаточно монет! Нужно {VIP_PRICE} 🪙"))
            return
        
        if self.db.is_vip(user_id):
            await update.message.reply_text(self.f.error("У тебя уже есть VIP статус!"))
            return
        
        self.db.add_coins(user_id, -VIP_PRICE)
        self.db.set_vip(user_id, VIP_DAYS)
        
        await update.message.reply_text(
            self.f.success("ПОЗДРАВЛЯЮ!") + "\n\n"
            f"Теперь у тебя VIP статус на {VIP_DAYS} дней!\n"
            "Все бонусы уже активны.",
            parse_mode='Markdown'
        )
    
    async def cmd_premium(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Купить Premium"""
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)
        
        if user_data['coins'] < PREMIUM_PRICE:
            await update.message.reply_text(self.f.error(f"Недостаточно монет! Нужно {PREMIUM_PRICE} 🪙"))
            return
        
        if self.db.is_premium(user_id):
            await update.message.reply_text(self.f.error("У тебя уже есть Premium статус!"))
            return
        
        self.db.add_coins(user_id, -PREMIUM_PRICE)
        self.db.set_premium(user_id, PREMIUM_DAYS)
        
        await update.message.reply_text(
            self.f.success("ПОЗДРАВЛЯЮ!") + "\n\n"
            f"Теперь у тебя PREMIUM статус на {PREMIUM_DAYS} дней!\n"
            "Ты элита!",
            parse_mode='Markdown'
        )
    
    # ========== ДОЛГИ ==========
    
    async def cmd_debt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Дать в долг"""
        if len(context.args) < 3:
            await update.message.reply_text(self.f.error("Использование: /debt @ник сумма причина"))
            return
        
        query = context.args[0]
        try:
            amount = int(context.args[1])
            reason = " ".join(context.args[2:])
        except:
            await update.message.reply_text(self.f.error("Неправильный формат"))
            return
        
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)
        
        target_user = self.db.get_user_by_name(query) or self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(self.f.error(f"Пользователь не найден"))
            return
        
        if target_user['user_id'] == user_id:
            await update.message.reply_text(self.f.error("Нельзя дать в долг самому себе"))
            return
        
        if user_data['coins'] < amount:
            await update.message.reply_text(self.f.error(f"У тебя только {user_data['coins']} 🪙"))
            return
        
        self.db.add_coins(user_id, -amount)
        debt_id = self.db.create_debt(target_user['user_id'], user_id, amount, reason)
        
        name = target_user.get('nickname') or target_user.get('first_name', 'Игрок')
        
        text = (
            self.f.header("ДОЛГ ОФОРМЛЕН", "💰") + "\n\n"
            f"{self.f.list_item(f'Должник: {name}')}\n"
            f"{self.f.list_item(f'Сумма: {amount} 🪙')}\n"
            f"{self.f.list_item(f'Причина: {reason}')}\n"
            f"{self.f.list_item(f'ID долга: {debt_id}')}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_debts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список долгов"""
        user_id = update.effective_user.id
        debts = self.db.get_debts(user_id)
        
        if not debts:
            await update.message.reply_text(self.f.info("У тебя нет активных долгов"))
            return
        
        text = self.f.header("ТВОИ ДОЛГИ", "💰") + "\n\n"
        
        for debt in debts:
            debtor_id, creditor_id, amount, reason, created, deadline, is_paid = debt[1:8]
            
            if debtor_id == user_id:
                role = "Ты должен"
                other_id = creditor_id
            else:
                role = "Должны тебе"
                other_id = debtor_id
            
            other = self.db.get_user_by_id(other_id)
            other_name = other.get('first_name', f"ID {other_id}") if other else f"ID {other_id}"
            
            created_str = datetime.datetime.fromisoformat(created).strftime("%d.%m.%Y")
            deadline_str = datetime.datetime.fromisoformat(deadline).strftime("%d.%m.%Y")
            
            text += (
                f"**ID: {debt[0]}**\n"
                f"{self.f.list_item(f'{role}: {other_name}')}\n"
                f"{self.f.list_item(f'Сумма: {amount} 🪙')}\n"
                f"{self.f.list_item(f'Причина: {reason}')}\n"
                f"{self.f.list_item(f'Создан: {created_str}')}\n"
                f"{self.f.list_item(f'Срок: {deadline_str}')}\n\n"
            )
        
        text += f"{self.f.note('Оплатить: /paydebt ID')}"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_pay_debt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Оплатить долг"""
        if not context.args:
            await update.message.reply_text(self.f.error("Укажи ID долга: /paydebt 1"))
            return
        
        try:
            debt_id = int(context.args[0])
        except:
            await update.message.reply_text(self.f.error("Неправильный ID"))
            return
        
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)
        
        self.db.cursor.execute("SELECT * FROM debts WHERE id = ?", (debt_id,))
        debt = self.db.cursor.fetchone()
        
        if not debt:
            await update.message.reply_text(self.f.error("Долг не найден"))
            return
        
        debtor_id, creditor_id, amount, reason, created, deadline, is_paid = debt[1:8]
        
        if is_paid:
            await update.message.reply_text(self.f.error("Долг уже оплачен"))
            return
        
        if debtor_id != user_id:
            await update.message.reply_text(self.f.error("Это не твой долг"))
            return
        
        if user_data['coins'] < amount:
            await update.message.reply_text(self.f.error(f"Недостаточно монет! Нужно {amount} 🪙"))
            return
        
        self.db.add_coins(user_id, -amount)
        self.db.add_coins(creditor_id, amount)
        self.db.pay_debt(debt_id)
        
        creditor = self.db.get_user_by_id(creditor_id)
        creditor_name = creditor.get('first_name', 'Кредитор') if creditor else 'Кредитор'
        
        text = (
            self.f.header("ДОЛГ ОПЛАЧЕН", "✅") + "\n\n"
            f"{self.f.list_item(f'Сумма: {amount} 🪙')}\n"
            f"{self.f.list_item(f'Получатель: {creditor_name}')}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    # ========== ЗАКЛАДКИ ==========
    
    async def cmd_add_bookmark(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Добавить закладку"""
        if not context.args:
            await update.message.reply_text(self.f.error("Укажи текст закладки: /addbookmark текст"))
            return
        
        text = " ".join(context.args)
        user_id = update.effective_user.id
        
        # Создаем ссылку на сообщение
        chat = update.effective_chat
        message_id = update.message.message_id
        message_link = f"https://t.me/c/{str(chat.id)[4:]}/{message_id}" if str(chat.id).startswith('-100') else f"https://t.me/{chat.username}/{message_id}" if chat.username else None
        
        bookmark_id = self.db.add_bookmark(user_id, text, message_link or "")
        
        await update.message.reply_text(self.f.success(f"Закладка сохранена! ID: {bookmark_id}"))
    
    async def cmd_bookmarks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список закладок"""
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)
        bookmarks = self.db.get_bookmarks(user_id)
        
        if not bookmarks:
            name = user_data.get('nickname') or user_data.get('first_name', 'Пользователь')
            await update.message.reply_text(self.f.info(f"У {name} пока нет закладок."))
            return
        
        if context.args and context.args[0].isdigit():
            idx = int(context.args[0]) - 1
            if 0 <= idx < len(bookmarks):
                b_id, text, link, created = bookmarks[idx]
                created_str = datetime.datetime.fromisoformat(created).strftime("%d.%m.%Y %H:%M")
                
                text = (
                    self.f.header(f"ЗАКЛАДКА #{idx+1}", "📌") + "\n\n"
                    f"📝 {text}\n\n"
                )
                if link:
                    text += f"🔗 [Перейти к сообщению]({link})\n"
                text += f"📅 {created_str}"
                
                await update.message.reply_text(text, parse_mode='Markdown', disable_web_page_preview=True)
            else:
                await update.message.reply_text(self.f.error("Закладка не найдена"))
            return
        
        name = user_data.get('nickname') or user_data.get('first_name', 'Пользователь')
        text = self.f.header(f"ЗАКЛАДКИ {name.upper()}", "📌") + "\n\n"
        
        for i, (b_id, b_text, b_link, b_created) in enumerate(bookmarks, 1):
            created_short = datetime.datetime.fromisoformat(b_created).strftime("%d.%m.%Y")
            text += f"**{i}.** {b_text[:50]}... — {created_short}\n"
        
        text += f"\n{self.f.note('Для просмотра: /bookmarks [номер]')}"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    # ========== ПОДПИСКИ ==========
    
    async def cmd_subscribe(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Подписаться на пользователя"""
        if not context.args:
            await update.message.reply_text(self.f.error("Укажи ник: /subscribe @username"))
            return
        
        query = context.args[0]
        user_id = update.effective_user.id
        
        target_user = self.db.get_user_by_name(query) or self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(self.f.error(f"Пользователь не найден"))
            return
        
        if target_user['user_id'] == user_id:
            await update.message.reply_text(self.f.error("Нельзя подписаться на самого себя"))
            return
        
        self.db.add_subscription(user_id, target_user['user_id'])
        name = target_user.get('nickname') or target_user.get('first_name', 'Игрок')
        
        await update.message.reply_text(self.f.success(f"Ты подписался на {name}!"))
    
    async def cmd_unsubscribe(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отписаться от пользователя"""
        if not context.args:
            await update.message.reply_text(self.f.error("Укажи ник: /unsubscribe @username"))
            return
        
        query = context.args[0]
        user_id = update.effective_user.id
        
        target_user = self.db.get_user_by_name(query) or self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(self.f.error(f"Пользователь не найден"))
            return
        
        self.db.remove_subscription(user_id, target_user['user_id'])
        name = target_user.get('nickname') or target_user.get('first_name', 'Игрок')
        
        await update.message.reply_text(self.f.success(f"Ты отписался от {name}"))
    
    async def cmd_my_subs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Мои подписки"""
        user_id = update.effective_user.id
        subscriptions = self.db.get_subscriptions(user_id)
        
        if not subscriptions:
            await update.message.reply_text(self.f.info("Ты ни на кого не подписан"))
            return
        
        text = self.f.header("ТВОИ ПОДПИСКИ", "📋") + "\n\n"
        
        for sub in subscriptions:
            name = sub[1] or f"ID {sub[0]}"
            date = datetime.datetime.fromisoformat(sub[3]).strftime("%d.%m.%Y") if sub[3] else "неизвестно"
            text += f"{self.f.list_item(f'{name} — с {date}')}\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_my_subscribers(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Мои подписчики"""
        user_id = update.effective_user.id
        subscribers = self.db.get_subscribers(user_id)
        
        if not subscribers:
            await update.message.reply_text(self.f.info("У тебя пока нет подписчиков"))
            return
        
        text = self.f.header("ТВОИ ПОДПИСЧИКИ", "📋") + "\n\n"
        
        for sub in subscribers:
            name = sub[1] or f"ID {sub[0]}"
            date = datetime.datetime.fromisoformat(sub[3]).strftime("%d.%m.%Y") if sub[3] else "неизвестно"
            text += f"{self.f.list_item(f'{name} — с {date}')}\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    # ========== НАГРАДЫ ==========
    
    async def cmd_rewards(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Мои награды"""
        user_id = update.effective_user.id
        rewards = self.db.get_rewards(user_id)
        
        if not rewards:
            await update.message.reply_text(self.f.info("У тебя пока нет наград"))
            return
        
        text = self.f.header("ТВОИ НАГРАДЫ", "🏆") + "\n\n"
        
        for reward in rewards:
            name, desc, awarded_by, date = reward
            date_str = datetime.datetime.fromisoformat(date).strftime("%d.%m.%Y") if date else "неизвестно"
            text += (
                f"**{name}**\n"
                f"{self.f.list_item(desc)}\n"
                f"{self.f.list_item(f'От: {awarded_by}')}\n"
                f"{self.f.list_item(f'Дата: {date_str}')}\n\n"
            )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_add_reward(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Добавить награду (админ)"""
        admin = update.effective_user
        admin_data = self.db.get_user_by_id(admin.id)
        
        if not self.has_permission(admin_data, 'admin'):
            await update.message.reply_text(self.f.error("Недостаточно прав"))
            return
        
        if len(context.args) < 3:
            await update.message.reply_text(self.f.error("Использование: /addreward @ник Название | Описание"))
            return
        
        query = context.args[0]
        reward_text = " ".join(context.args[1:])
        
        if '|' not in reward_text:
            await update.message.reply_text(self.f.error("Формат: Название | Описание"))
            return
        
        reward_name, reward_desc = [x.strip() for x in reward_text.split('|', 1)]
        
        target_user = self.db.get_user_by_name(query) or self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(self.f.error(f"Пользователь не найден"))
            return
        
        self.db.add_reward(target_user['user_id'], reward_name, reward_desc, admin.id)
        
        name = target_user.get('nickname') or target_user.get('first_name', 'Игрок')
        
        text = (
            self.f.header("НАГРАДА ДОБАВЛЕНА", "🏆") + "\n\n"
            f"{self.f.list_item(f'Пользователь: {name}')}\n"
            f"{self.f.list_item(f'Название: {reward_name}')}\n"
            f"{self.f.list_item(f'Описание: {reward_desc}')}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    # ========== ДОСТИЖЕНИЯ ==========
    
    async def cmd_achievements(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список достижений"""
        user_id = update.effective_user.id
        achievements = self.db.get_achievements(user_id)
        
        if not achievements:
            await update.message.reply_text(
                self.f.info("У тебя пока нет достижений. Играй и открывай новые!") + "\n\n" +
                "Доступные достижения:\n"
                "👾 Охотник на боссов — убить 10 боссов (+500 🪙)\n"
                "👾 Легендарный охотник — убить 50 боссов (+2000 🪙)\n"
                "📈 Новичок — достичь 10 уровня\n"
                "📈 Ветеран — достичь 25 уровня\n"
                "🎰 Игроман — сыграть 50 игр в казино\n"
                "👥 Социальный — вступить в клан\n"
                "💍 Семьянин — вступить в брак"
            )
            return
        
        text = self.f.header("ТВОИ ДОСТИЖЕНИЯ", "🏆") + "\n\n"
        
        for name, desc, date, reward in achievements:
            date_obj = datetime.datetime.fromisoformat(date)
            date_str = date_obj.strftime("%d.%m.%Y")
            text += f"**{name}**\n└ {desc}\n└ 📅 {date_str}"
            if reward > 0:
                text += f" (+{reward} 🪙)"
            text += "\n\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    # ========== ГРАЖДАНСТВО ==========
    
    async def cmd_citizens(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список граждан чата"""
        chat_id = update.effective_chat.id
        citizens = self.db.get_citizens(chat_id)
        
        if not citizens:
            await update.message.reply_text(self.f.info("В этом чате пока нет граждан"))
            return
        
        text = self.f.header("ГРАЖДАНЕ ЧАТА", "🏡") + "\n\n"
        
        for citizen in citizens:
            user_id, name, nickname, joined_at = citizen
            display_name = nickname or name
            date = datetime.datetime.fromisoformat(joined_at).strftime("%d.%m.%Y") if joined_at else "неизвестно"
            text += f"{self.f.list_item(f'{display_name} — с {date}')}\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_grant_citizen(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выдать гражданство (админ)"""
        admin = update.effective_user
        admin_data = self.db.get_user_by_id(admin.id)
        
        if not self.has_permission(admin_data, 'moderator'):
            await update.message.reply_text(self.f.error("Недостаточно прав"))
            return
        
        if not context.args:
            await update.message.reply_text(self.f.error("Укажи ник: /grantcitizen @username"))
            return
        
        query = context.args[0]
        chat_id = update.effective_chat.id
        
        target_user = self.db.get_user_by_name(query) or self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(self.f.error(f"Пользователь не найден"))
            return
        
        self.db.add_citizenship(target_user['user_id'], chat_id)
        
        name = target_user.get('nickname') or target_user.get('first_name', 'Игрок')
        await update.message.reply_text(self.f.success(f"{name} теперь гражданин этого чата!"))
    
    # ========== ПРОЧИЕ КОМАНДЫ ==========
    
    async def cmd_weather(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Погода"""
        city = " ".join(context.args) if context.args else "Москва"
        
        weathers = ["☀️ солнечно", "⛅ облачно с прояснениями", "☁️ пасмурно", 
                   "🌧 дождь", "⛈ гроза", "❄️ снег", "🌫 туман"]
        temp = random.randint(-15, 30)
        wind = random.randint(0, 15)
        humidity = random.randint(30, 90)
        weather = random.choice(weathers)
        
        text = (
            self.f.header(f"ПОГОДА В {city.upper()}", "🌍") + "\n\n"
            f"{weather}, {temp}°C\n"
            f"💨 Ветер: {wind} м/с\n"
            f"💧 Влажность: {humidity}%\n"
            f"📅 {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_news(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Новости"""
        news_list = [
            "🎮 Новое обновление бота! Добавлены новые команды!",
            "👾 Новый босс «Король демонов» уже на арене!",
            "🏆 Начинается еженедельный турнир!",
            "💎 Скидки на VIP статус до конца недели!",
            "📚 Полный список команд: /help"
        ]
        
        text = (
            self.f.header("НОВОСТИ", "📰") + "\n\n"
            f"{random.choice(news_list)}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_quote(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Цитата дня"""
        quotes = [
            "Жизнь — как коробка шоколадных конфет: никогда не знаешь, какая начинка тебе попадётся.",
            "Сложнее всего начать действовать, все остальное зависит только от упорства.",
            "Успех — это способность идти от поражения к поражению, не теряя энтузиазма.",
            "Лучший способ предсказать будущее — создать его.",
            "Не бойтесь, что у вас не получится. Бойтесь, что вы не попробуете.",
            "Будь собой, остальные роли уже заняты."
        ]
        
        text = (
            self.f.header("ЦИТАТА ДНЯ", "📝") + "\n\n"
            f"«{random.choice(quotes)}»"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_players(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Количество игроков"""
        count = self.db.get_players_count()
        
        text = (
            self.f.header("СТАТИСТИКА", "👥") + "\n\n"
            f"Всего игроков: {count}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_mycrime(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Моя статья"""
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
        
        text = (
            f"🤷‍♂️ Сегодня {today} {self.f.user_link(user.id, user.first_name)} приговаривается к статье {article_num}. {article_name}\n"
            f"⏱ Срок: {sentence} {'год' if sentence==1 else 'года' if sentence<5 else 'лет'}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_eng_free(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Бесплатная энергия"""
        user_id = update.effective_user.id
        user_data = self.db.get_user_by_id(user_id)
        
        last_free = user_data.get('last_free_energy')
        if last_free:
            last = datetime.datetime.fromisoformat(last_free)
            if (datetime.datetime.now() - last).seconds < 3600:
                remaining = 3600 - (datetime.datetime.now() - last).seconds
                minutes = remaining // 60
                await update.message.reply_text(self.f.error(f"Бесплатную энергию можно получать раз в час. Осталось: {minutes} мин"))
                return
        
        energy = 20
        self.db.add_energy(user_id, energy)
        
        self.db.cursor.execute(
            "UPDATE users SET last_free_energy = ? WHERE user_id = ?",
            (datetime.datetime.now(), user_id)
        )
        self.db.conn.commit()
        
        await update.message.reply_text(self.f.success(f"Ты получил {energy} ⚡ энергии!"))
    
    async def cmd_sms(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Личное сообщение"""
        if len(context.args) < 2:
            await update.message.reply_text(self.f.error("Использование: /sms @ник сообщение"))
            return
        
        query = context.args[0]
        message = " ".join(context.args[1:])
        
        target_user = self.db.get_user_by_name(query) or self.db.get_user_by_username(query)
        if not target_user:
            await update.message.reply_text(self.f.error(f"Пользователь не найден"))
            return
        
        sender = update.effective_user
        
        # Отправляем личное сообщение
        try:
            await context.bot.send_message(
                chat_id=target_user['user_id'],
                text=(
                    f"💬 Личное сообщение от {self.f.user_link(sender.id, sender.first_name)}:\n\n"
                    f"{message}"
                ),
                parse_mode='Markdown'
            )
            await update.message.reply_text(self.f.success("Сообщение отправлено!"))
        except Exception as e:
            await update.message.reply_text(self.f.error("Не удалось отправить сообщение. Возможно, пользователь не запускал бота."))
    
    # ========== HELP ==========
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Справка"""
        text = (
            self.f.header("СПРАВКА", "📚") + "\n\n"
            self.f.section("ОСНОВНЫЕ КОМАНДЫ", "🔹") + "\n"
            f"{self.f.command('start', 'начать работу с ботом')}\n"
            f"{self.f.command('menu', 'главное меню')}\n"
            f"{self.f.command('profile', 'твой профиль')}\n"
            f"{self.f.command('whoami', 'информация о себе')}\n"
            f"{self.f.command('whois @ник', 'информация о пользователе')}\n\n"
            
            self.f.section("ИГРЫ", "🎮") + "\n"
            f"{self.f.command('bosses', 'битва с боссами')}\n"
            f"{self.f.command('casino', 'казино')}\n"
            f"{self.f.command('rps', 'камень-ножницы-бумага')}\n\n"
            
            self.f.section("ЭКОНОМИКА", "💰") + "\n"
            f"{self.f.command('daily', 'ежедневный бонус')}\n"
            f"{self.f.command('weekly', 'недельный бонус')}\n"
            f"{self.f.command('shop', 'магазин')}\n"
            f"{self.f.command('pay @ник сумма', 'перевести монеты')}\n"
            f"{self.f.command('donate', 'привилегии')}\n\n"
            
            self.f.section("МОДЕРАЦИЯ", "⚙️") + "\n"
            f"{self.f.command('warn @ник [причина]', 'предупреждение')}\n"
            f"{self.f.command('mute @ник минут [причина]', 'заглушить')}\n"
            f"{self.f.command('ban @ник [срок] [причина]', 'заблокировать')}\n"
            f"{self.f.command('banlist', 'список забаненных')}\n"
            f"{self.f.command('mutelist', 'список замученных')}\n\n"
            
            f"👑 **Владелец:** {OWNER_USERNAME}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    # ========== ОБРАБОТЧИКИ СООБЩЕНИЙ ==========
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка обычных сообщений"""
        user = update.effective_user
        message_text = update.message.text
        
        # Игнорируем команды
        if message_text.startswith('/'):
            return
        
        self.db.get_or_create_user("tg", str(user.id), user.first_name)
        self.db.update_last_seen(user.id)
        self.db.add_stat(user.id, "messages_count", 1)
        
        if self.db.is_banned(user.id):
            return
        
        if self.db.is_muted(user.id):
            remaining = self.db.get_mute_time(user.id)
            await update.message.reply_text(self.f.error(f"Вы замучены. Осталось: {remaining}"))
            return
        
        if await self.check_spam(update):
            return
        
        # Простые ответы
        msg_lower = message_text.lower()
        
        if any(word in msg_lower for word in ["привет", "здравствуй", "хай", "ку"]):
            await update.message.reply_text("👋 Привет! Как твои дела?")
        elif any(word in msg_lower for word in ["как дела", "как ты", "чё как"]):
            await update.message.reply_text("⚙️ Всё отлично! А у тебя?")
        elif any(word in msg_lower for word in ["спасибо", "благодарю", "пасиб"]):
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
    
    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка голосовых"""
        user = update.effective_user
        self.db.update_voice_count(user.id)
        self.db.update_last_seen(user.id)
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка фото"""
        user = update.effective_user
        self.db.update_photo_count(user.id)
        self.db.update_last_seen(user.id)
    
    async def handle_sticker(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка стикеров"""
        user = update.effective_user
        self.db.update_sticker_count(user.id)
        self.db.update_last_seen(user.id)
    
    async def handle_new_members(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Новые участники"""
        for member in update.message.new_chat_members:
            if member.is_bot:
                continue
            
            await update.message.reply_text(
                self.f.success(f"Добро пожаловать, {member.first_name}!") + "\n" +
                self.f.note("Напиши /help для списка команд"),
                parse_mode='Markdown'
            )
    
    async def handle_left_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Участник покинул чат"""
        member = update.message.left_chat_member
        if member.is_bot:
            return
        
        await update.message.reply_text(
            self.f.info(f"Пока, {member.first_name}! Будем ждать тебя снова 👋"),
            parse_mode='Markdown'
        )
    
    # ========== CALLBACK КНОПКИ ==========
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатий на кнопки"""
        query = update.callback_query
        await query.answer()
        user = query.from_user
        data = query.data
        
        if data == "menu_back":
            keyboard = self.get_main_menu_keyboard()
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                self.f.header("ГЛАВНОЕ МЕНЮ", "🎮") + "\n\nВыбери раздел:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        
        elif data == "menu_profile":
            await self.cmd_profile(update, context)
        
        elif data == "menu_stats":
            await self.cmd_my_stats(update, context)
        
        elif data == "menu_bosses":
            await self.cmd_boss_list(update, context)
        
        elif data == "menu_casino":
            await self.cmd_casino(update, context)
        
        elif data == "menu_shop":
            await self.cmd_shop(update, context)
        
        elif data == "menu_donate":
            await self.cmd_donate(update, context)
        
        elif data == "menu_moderation":
            text = (
                self.f.header("МОДЕРАЦИЯ", "⚙️") + "\n\n"
                f"{self.f.command('warn @ник [причина]', 'предупреждение')}\n"
                f"{self.f.command('warns @ник', 'список предупреждений')}\n"
                f"{self.f.command('unwarn @ник', 'снять предупреждение')}\n"
                f"{self.f.command('mute @ник минут [причина]', 'заглушить')}\n"
                f"{self.f.command('unmute @ник', 'снять мут')}\n"
                f"{self.f.command('mutelist', 'список замученных')}\n"
                f"{self.f.command('ban @ник [срок] [причина]', 'заблокировать')}\n"
                f"{self.f.command('unban @ник', 'разблокировать')}\n"
                f"{self.f.command('banlist', 'список забаненных')}\n"
                f"{self.f.command('kick @ник', 'исключить')}\n"
                f"{self.f.command('banreason @ник', 'причина бана')}"
            )
            await query.edit_message_text(text, parse_mode='Markdown')
        
        elif data == "menu_help":
            await self.cmd_help(update, context)
        
        elif data.startswith("banlist_"):
            page = int(data.split('_')[1])
            await self.cmd_banlist(update, context, page)
        
        elif data.startswith("rps_"):
            choice = data.split('_')[1]
            bot_choice = random.choice(["rock", "scissors", "paper"])
            
            choices = {"rock": "🪨 Камень", "scissors": "✂️ Ножницы", "paper": "📄 Бумага"}
            
            wins_map = {
                ("rock", "scissors"): "win",
                ("scissors", "paper"): "win",
                ("paper", "rock"): "win",
                ("scissors", "rock"): "lose",
                ("paper", "scissors"): "lose",
                ("rock", "paper"): "lose"
            }
            
            result_text = f"{choices[choice]} vs {choices[bot_choice]}\n\n"
            
            if choice == bot_choice:
                self.db.cursor.execute("UPDATE users SET rps_draws = rps_draws + 1 WHERE user_id = ?", (user.id,))
                self.db.conn.commit()
                result_text += "🤝 **Ничья!**"
            else:
                result = wins_map.get((choice, bot_choice))
                if result == "win":
                    self.db.cursor.execute("UPDATE users SET rps_wins = rps_wins + 1 WHERE user_id = ?", (user.id,))
                    self.db.conn.commit()
                    result_text += "🎉 **Ты выиграл!**"
                    
                    # Награда
                    reward = random.randint(10, 50)
                    self.db.add_coins(user.id, reward)
                    result_text += f" +{reward} 🪙"
                else:
                    self.db.cursor.execute("UPDATE users SET rps_losses = rps_losses + 1 WHERE user_id = ?", (user.id,))
                    self.db.conn.commit()
                    result_text += "😢 **Ты проиграл!**"
            
            await query.edit_message_text(result_text, parse_mode='Markdown')
    
    # ========== ЗАПУСК ==========
    
    async def run(self):
        """Запуск бота"""
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
        """Остановка бота"""
        self.db.close()
        logger.info("👋 Бот остановлен")

# ========== ТОЧКА ВХОДА ==========
async def main():
    """Главная функция"""
    print("=" * 50)
    print("🚀 ЗАПУСК БОТА «СПЕКТР»")
    print("=" * 50)
    
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
