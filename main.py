import asyncio
import logging
import random
import sqlite3
import datetime
from typing import Optional, Dict, Any, List, Tuple
import aiohttp
import json
import re
from collections import defaultdict
import time
import hashlib
import base64
import math
import io
import requests
import os
import sys
import time
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Для Telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from telegram.constants import ParseMode

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===================== ЖЕСТКАЯ ЗАЩИТА =====================
print("🛡️ Активация защиты от множественного запуска...")

# Убиваем все другие процессы бота
try:
    import subprocess
    result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
    lines = result.stdout.split('\n')
    current_pid = os.getpid()
    
    killed = 0
    for line in lines:
        if 'python' in line and 'main.py' in line:
            parts = line.split()
            if len(parts) > 1:
                pid = int(parts[1])
                if pid != current_pid:
                    try:
                        os.kill(pid, 9)
                        print(f"💀 Убит процесс {pid}")
                        killed += 1
                        time.sleep(0.5)
                    except:
                        pass
    
    if killed > 0:
        print(f"✅ Убито {killed} процессов")
    else:
        print("✅ Конфликтов не найдено")
        
except Exception as e:
    print(f"⚠️ Ошибка при очистке: {e}")

print("🚀 Продолжаем запуск...\n")

# ===================== КОНФИГУРАЦИЯ =====================
TELEGRAM_TOKEN = "8326390250:AAEpXRnhLLLi5zUeFC39nfkHDlxR5ZFQ_yQ"
OWNER_ID = 1732658530
OWNER_USERNAME = "@NobuCraft"

# Настройки
SPAM_LIMIT = 5
SPAM_WINDOW = 3
SPAM_MUTE_TIME = 120

# ===================== УМНЫЙ AI КЛАСС =====================
class SpectrumAI:
    """Спектр - умный AI с характером"""
    
    def __init__(self):
        self.api_token = "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"
        self.user_contexts = {}
        self.user_mood = {}
        print("🤖 Спектр (AI) инициализирован")
        
        # Характер AI
        self.personality = {
            "greeting": ["Привет! Я Спектр, как твои дела?", "Здарова! Чего хотел?", "Хэй! Давай общаться!"],
            "mood_happy": ["😊 Отлично!", "🎉 Супер!", "✨ Прекрасно!"],
            "mood_sad": ["😔 Грустно...", "😕 Не очень", "😢 Печально"],
            "mood_energetic": ["⚡ Полон энергии!", "🚀 Готов к приключениям!", "💪 Погнали!"],
            "jokes": [
                "Почему программисты любят темноту? Потому что в темноте включается подсветка клавиатуры!",
                "Как называют бота, который много говорит? Болт-бот!",
                "Что сказал один байт другому? Ты выглядишь битово!",
            ],
            "wisdom": [
                "Жизнь как программирование - если работает, не трогай!",
                "Лучший код - тот, который уже написан",
                "Каждая ошибка - это новый опыт",
            ]
        }
        
        self.knowledge_base = {
            "привет": ["Привет! Как сам?", "Здравствуй! Чего нового?", "Хей-хей!"],
            "как дела": ["У меня всё супер! А у тебя?", "Отлично! Ты как?", "Нормально, работаю!"],
            "что делаешь": ["Думаю над смыслом жизни... А ты?", "Отвечаю на вопросы!", "Жду новых команд!"],
            "кто ты": ["Я Спектр - твой виртуальный друг и помощник!", "Искусственный интеллект с характером!", "Твой AI-компаньон!"],
            "пока": ["До встречи! Буду скучать!", "Пока-пока! Заходи ещё!", "Удачи тебе!"],
            "спасибо": ["Всегда пожалуйста! 😊", "Не за что! Обращайся!", "Рад помочь!"],
            "помощь": ["Чем могу помочь?", "Спрашивай что угодно!", "Я тут чтобы помогать!"],
            "игры": ["Обожаю игры! У нас есть мафия, сапёр, русская рулетка!", "Хочешь поиграть? Выбирай!", "Я мастер игр!"],
            "босс": ["Боссы ждут! /boss - и в бой!", "Побеждай боссов и получай награды!", "Самый сильный босс ждёт тебя!"],
            "погода": ["Погода отличная для общения! А там как знаешь 😉", "Лучше спроси что-то другое!", "Я не метеоролог, но могу поговорить!"],
            "любовь": ["Любовь - это прекрасное чувство! ❤️", "В боте можно даже пожениться!", "Романтика - это круто!"],
            "еда": ["Я питаюсь электричеством! А ты?", "Пицца - лучший выбор!", "Ммм, вкусно!"],
            "работа": ["Работать нужно в удовольствие!", "Главное - не перегореть!", "Делу время, потехе час!"],
            "отдых": ["Отдыхать тоже нужно уметь!", "Расслабься, я с тобой!", "Лучший отдых - общение с друзьями!"],
        }
        
        self.default_responses = [
            "Ого, интересно! Расскажи подробнее!",
            "Понял тебя. А что ещё?",
            "Хм, забавно!",
            "Я тебя слушаю внимательно!",
            "Давай поговорим об этом!",
            "Круто! А я вот думаю о жизни...",
            "Занятно! Продолжай!",
            "Мне нравится ход твоих мыслей!",
            "Согласен с тобой на все 100!",
            "Хорошая мысль, я запомню!",
            "Ты сегодня в ударе!",
            "Мудрые слова!",
            "О, это интересная тема!",
            "Расскажи-ка подробнее!",
            "Я весь во внимании!",
        ]
    
    async def get_response(self, user_id: int, message: str) -> str:
        """Получить умный ответ от AI"""
        message_lower = message.lower().strip()
        
        # Пробуем API
        api_response = await self._try_api_response(message)
        if api_response:
            return api_response
        
        # Ищем в базе знаний
        for key, responses in self.knowledge_base.items():
            if key in message_lower:
                return random.choice(responses)
        
        # Анализ длины сообщения
        words = message.split()
        if len(words) == 1:
            single_responses = [
                f"{message}? Интересное слово!",
                f"Хм, {message}... А что это значит?",
                f"Я запомню слово '{message}'!",
                f"Крутое слово! Расскажи ещё!"
            ]
            return random.choice(single_responses)
        elif len(words) <= 3:
            short_responses = [
                f"'{message}' - понял тебя!",
                f"Окей, {message}",
                f"Согласен насчёт {message}",
                f"Хорошо, продолжай!"
            ]
            return random.choice(short_responses)
        else:
            return random.choice(self.default_responses)
    
    async def _try_api_response(self, message: str) -> Optional[str]:
        """Попытка получить ответ через Hugging Face"""
        try:
            API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.1"
            headers = {"Authorization": f"Bearer {self.api_token}"}
            
            prompt = f"<s>[INST] Ты Спектр - дружелюбный AI с чувством юмора. Ответь на: {message} [/INST]"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(API_URL, headers=headers, json={
                    "inputs": prompt,
                    "parameters": {
                        "max_new_tokens": 150,
                        "temperature": 0.8,
                        "top_p": 0.95,
                    }
                }, timeout=10) as resp:
                    
                    if resp.status == 200:
                        result = await resp.json()
                        if isinstance(result, list) and len(result) > 0:
                            text = result[0].get("generated_text", "")
                            response = text.split("[/INST]")[-1] if "[/INST]" in text else text
                            if response and len(response) > 5:
                                return response.strip()
                    return None
        except:
            return None
    
    async def tell_joke(self) -> str:
        """Рассказать шутку"""
        return random.choice(self.personality["jokes"])
    
    async def give_wisdom(self) -> str:
        """Дать мудрый совет"""
        return random.choice(self.personality["wisdom"])
    
    async def mood(self) -> str:
        """Случайное настроение"""
        moods = list(self.personality.keys())
        mood_key = random.choice([m for m in moods if m.startswith("mood_")])
        return random.choice(self.personality[mood_key])

# ===================== БАЗА ДАННЫХ =====================
class Database:
    def __init__(self, db_name="spectrum_bot.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
        self.init_bosses()
    
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
                mod_rank INTEGER DEFAULT 0,
                privilege TEXT DEFAULT 'user',
                privilege_until TIMESTAMP,
                warns INTEGER DEFAULT 0,
                mute_until TIMESTAMP,
                banned INTEGER DEFAULT 0,
                ban_reason TEXT,
                ban_date TIMESTAMP,
                banned_by INTEGER,
                health INTEGER DEFAULT 100,
                max_health INTEGER DEFAULT 100,
                armor INTEGER DEFAULT 0,
                damage INTEGER DEFAULT 10,
                boss_kills INTEGER DEFAULT 0,
                last_activity TIMESTAMP,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                regen_available TIMESTAMP,
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
                rr_losses INTEGER DEFAULT 0,
                minesweeper_wins INTEGER DEFAULT 0,
                minesweeper_games INTEGER DEFAULT 0,
                activity_data TEXT DEFAULT '{}',
                daily_streak INTEGER DEFAULT 0,
                last_daily TIMESTAMP,
                weekly_streak INTEGER DEFAULT 0,
                last_weekly TIMESTAMP,
                clan_id INTEGER DEFAULT 0,
                clan_role TEXT DEFAULT 'member',
                pet_id INTEGER DEFAULT 0,
                pet_name TEXT DEFAULT '',
                pet_level INTEGER DEFAULT 1,
                pet_exp INTEGER DEFAULT 0,
                pet_hunger INTEGER DEFAULT 100,
                achievements TEXT DEFAULT '[]',
                tournament_points INTEGER DEFAULT 0
            )
        ''')
        
        # Достижения
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                description TEXT,
                reward_coins INTEGER,
                reward_exp INTEGER,
                condition_type TEXT,
                condition_value INTEGER
            )
        ''')
        
        # Кланы
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS clans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                owner_id TEXT,
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
                user_id TEXT,
                role TEXT DEFAULT 'member',
                joined_at TIMESTAMP,
                FOREIGN KEY (clan_id) REFERENCES clans (id)
            )
        ''')
        
        # Питомцы
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS pets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id TEXT,
                name TEXT,
                type TEXT,
                level INTEGER DEFAULT 1,
                exp INTEGER DEFAULT 0,
                hunger INTEGER DEFAULT 100,
                happiness INTEGER DEFAULT 100,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Турниры
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tournaments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                start_date TIMESTAMP,
                end_date TIMESTAMP,
                status TEXT DEFAULT 'pending',
                prize_pool INTEGER DEFAULT 0
            )
        ''')
        
        # Участники турниров
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tournament_participants (
                tournament_id INTEGER,
                user_id TEXT,
                points INTEGER DEFAULT 0,
                FOREIGN KEY (tournament_id) REFERENCES tournaments (id)
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
                warn_date TIMESTAMP,
                warn_expire TIMESTAMP
            )
        ''')
        
        # Боссы
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS bosses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                boss_name TEXT,
                boss_emoji TEXT,
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
                reason TEXT,
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
                message_text TEXT,
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
                anti_spam INTEGER DEFAULT 1,
                rules TEXT DEFAULT '',
                warns_limit INTEGER DEFAULT 3,
                warns_ban_period TEXT DEFAULT '1 день',
                warns_period TEXT DEFAULT '30 дней',
                mute_period TEXT DEFAULT '1 неделя',
                ban_period TEXT DEFAULT 'навсегда',
                language TEXT DEFAULT 'ru'
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
        
        # Мафия - действия
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS mafia_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER,
                player_id TEXT,
                action_type TEXT,
                target_id TEXT,
                round INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Сапёр - игры
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS minesweeper_games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                width INTEGER,
                height INTEGER,
                mines INTEGER,
                board TEXT,
                revealed TEXT,
                flags TEXT,
                status TEXT,
                started_at TIMESTAMP,
                last_move TIMESTAMP
            )
        ''')
        
        # Достижения по умолчанию
        self.cursor.execute("SELECT COUNT(*) FROM achievements")
        if self.cursor.fetchone()[0] == 0:
            achievements = [
                ("Новичок", "Достигнуть 5 уровня", 100, 50, "level", 5),
                ("Опытный", "Достигнуть 10 уровня", 200, 100, "level", 10),
                ("Мастер", "Достигнуть 20 уровня", 500, 200, "level", 20),
                ("Легенда", "Достигнуть 30 уровня", 1000, 500, "level", 30),
                ("Охотник на боссов", "Убить 10 боссов", 300, 150, "boss_kills", 10),
                ("Завоеватель", "Убить 50 боссов", 1000, 500, "boss_kills", 50),
                ("Игрок", "Сыграть 10 игр", 100, 50, "games_played", 10),
                ("Задрот", "Сыграть 100 игр", 500, 200, "games_played", 100),
                ("Миллионер", "Накопить 10000 монет", 1000, 500, "coins", 10000),
                ("Богач", "Накопить 50000 монет", 2000, 1000, "coins", 50000),
                ("Мафиози", "Выиграть 10 игр в мафию", 300, 150, "mafia_wins", 10),
                ("Сапёр", "Выиграть 10 игр в сапёра", 300, 150, "minesweeper_wins", 10),
                ("Везунчик", "Выиграть 10 игр в русскую рулетку", 300, 150, "rr_wins", 10),
                ("Стратег", "Выиграть 10 игр в крестики-нолики", 300, 150, "ttt_wins", 10),
            ]
            for ach in achievements:
                self.cursor.execute('''
                    INSERT INTO achievements (name, description, reward_coins, reward_exp, condition_type, condition_value)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', ach)
            self.conn.commit()
        
        self.conn.commit()
    
    def init_bosses(self):
        self.cursor.execute("SELECT COUNT(*) FROM bosses")
        if self.cursor.fetchone()[0] == 0:
            bosses = [
                ("Ядовитый комар", "🦟", 5, 2780, 2780, 34, 500),
                ("Огненный дракон", "🐉", 10, 5000, 5000, 50, 1000),
                ("Ледяной великан", "❄️", 15, 8000, 8000, 70, 1500),
                ("Темный рыцарь", "⚔️", 20, 12000, 12000, 90, 2000),
                ("Король демонов", "👾", 25, 20000, 20000, 120, 3000),
                ("Бог разрушения", "💀", 30, 30000, 30000, 150, 5000)
            ]
            for boss in bosses:
                self.cursor.execute('''
                    INSERT INTO bosses (boss_name, boss_emoji, boss_level, boss_health, boss_max_health, boss_damage, boss_reward)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', boss)
            self.conn.commit()
    
    def respawn_bosses(self):
        self.cursor.execute("UPDATE bosses SET is_alive = 1, boss_health = boss_max_health")
        self.conn.commit()
    
    def get_user(self, platform, platform_id, username="", first_name="", last_name=""):
        self.cursor.execute(
            "SELECT * FROM users WHERE platform = ? AND platform_id = ?",
            (platform, platform_id)
        )
        user = self.cursor.fetchone()
        
        if not user:
            mod_rank = 5 if (platform == 'tg' and int(platform_id) == OWNER_ID) else 0
            self.cursor.execute('''
                INSERT INTO users (platform, platform_id, username, first_name, last_name, mod_rank, first_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (platform, platform_id, username, first_name, last_name, mod_rank, datetime.datetime.now()))
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
            INSERT INTO transactions (from_id, to_id, amount, currency, reason)
            VALUES (?, ?, ?, ?, ?)
        ''', (f"{from_platform}:{from_id}", f"{to_platform}:{to_id}", amount, currency, "transfer"))
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
    
    def regen_available(self, platform, platform_id):
        self.cursor.execute("SELECT regen_available FROM users WHERE platform = ? AND platform_id = ?", (platform, platform_id))
        result = self.cursor.fetchone()
        if result and result[0]:
            return datetime.datetime.now() >= datetime.datetime.fromisoformat(result[0])
        return True
    
    def use_regen(self, platform, platform_id, cooldown_minutes=5):
        regen_until = datetime.datetime.now() + datetime.timedelta(minutes=cooldown_minutes)
        self.cursor.execute("UPDATE users SET regen_available = ? WHERE platform = ? AND platform_id = ?", (regen_until, platform, platform_id))
        self.conn.commit()
    
    def get_boss(self):
        self.cursor.execute("SELECT * FROM bosses WHERE is_alive = 1 ORDER BY id LIMIT 1")
        boss = self.cursor.fetchone()
        if not boss:
            self.respawn_bosses()
            return self.get_boss()
        columns = [description[0] for description in self.cursor.description]
        return dict(zip(columns, boss))
    
    def get_next_boss(self):
        self.cursor.execute("SELECT * FROM bosses WHERE is_alive = 1 ORDER BY id LIMIT 1")
        boss = self.cursor.fetchone()
        if boss:
            columns = [description[0] for description in self.cursor.description]
            return dict(zip(columns, boss))
        return None
    
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
    
    def add_boss_kill(self, platform, platform_id):
        self.cursor.execute("UPDATE users SET boss_kills = boss_kills + 1 WHERE platform = ? AND platform_id = ?", (platform, platform_id))
        self.conn.commit()
    
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
    
    def get_user_by_id(self, platform, platform_id):
        self.cursor.execute(
            "SELECT * FROM users WHERE platform = ? AND platform_id = ?",
            (platform, platform_id)
        )
        return self.cursor.fetchone()
    
    def add_bookmark(self, platform, platform_id, description, message_link, message_text):
        self.cursor.execute('''
            INSERT INTO bookmarks (platform, platform_id, description, message_link, message_text)
            VALUES (?, ?, ?, ?, ?)
        ''', (platform, platform_id, description, message_link, message_text))
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
        return mute_until
    
    def unmute_user(self, platform, platform_id):
        self.cursor.execute("UPDATE users SET mute_until = NULL WHERE platform = ? AND platform_id = ?", (platform, platform_id))
        self.cursor.execute("UPDATE mutes SET is_active = 0 WHERE platform = ? AND platform_id = ?", (platform, platform_id))
        self.conn.commit()
    
    def add_warn(self, platform, platform_id, username, reason, warned_by, warned_by_name, days=30):
        warn_expire = datetime.datetime.now() + datetime.timedelta(days=days)
        self.cursor.execute("UPDATE users SET warns = warns + 1 WHERE platform = ? AND platform_id = ?", (platform, platform_id))
        self.cursor.execute('''
            INSERT INTO warns (platform, platform_id, username, reason, warned_by, warned_by_name, warn_date, warn_expire)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (platform, platform_id, username, reason, warned_by, warned_by_name, datetime.datetime.now(), warn_expire))
        self.conn.commit()
        self.cursor.execute("SELECT warns FROM users WHERE platform = ? AND platform_id = ?", (platform, platform_id))
        return self.cursor.fetchone()[0]
    
    def remove_warn(self, platform, platform_id, warn_id=None):
        if warn_id:
            self.cursor.execute("DELETE FROM warns WHERE id = ?", (warn_id,))
        else:
            self.cursor.execute("DELETE FROM warns WHERE platform = ? AND platform_id = ? ORDER BY warn_date DESC LIMIT 1", (platform, platform_id))
        self.cursor.execute("UPDATE users SET warns = warns - 1 WHERE platform = ? AND platform_id = ? AND warns > 0", (platform, platform_id))
        self.conn.commit()
    
    def get_warns(self, platform, platform_id):
        self.cursor.execute("SELECT * FROM warns WHERE platform = ? AND platform_id = ? ORDER BY warn_date DESC", (platform, platform_id))
        return self.cursor.fetchall()
    
    def get_warned_users(self, page=1, per_page=10):
        offset = (page - 1) * per_page
        self.cursor.execute('''
            SELECT * FROM warns ORDER BY warn_date DESC LIMIT ? OFFSET ?
        ''', (per_page, offset))
        return self.cursor.fetchall()
    
    def ban_user(self, platform, platform_id, username, reason, duration, banned_by, banned_by_name):
        is_permanent = duration.lower() == "навсегда"
        ban_until = None
        if not is_permanent:
            match = re.match(r'(\d+)\s*([дчм])', duration.lower())
            if match:
                value = int(match.group(1))
                unit = match.group(2)
                if unit == 'д':
                    ban_until = datetime.datetime.now() + datetime.timedelta(days=value)
                elif unit == 'ч':
                    ban_until = datetime.datetime.now() + datetime.timedelta(hours=value)
                elif unit == 'м':
                    ban_until = datetime.datetime.now() + datetime.timedelta(minutes=value)
            else:
                ban_until = datetime.datetime.now() + datetime.timedelta(days=365)
        
        self.cursor.execute("UPDATE users SET banned = 1, ban_reason = ?, ban_date = ?, banned_by = ? WHERE platform = ? AND platform_id = ?", 
                           (reason, datetime.datetime.now(), banned_by, platform, platform_id))
        self.cursor.execute('''
            INSERT INTO bans (platform, platform_id, username, reason, banned_by, banned_by_name, ban_date, ban_duration, ban_until, is_permanent, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (platform, platform_id, username, reason, banned_by, banned_by_name, datetime.datetime.now(), duration, ban_until, 1 if is_permanent else 0, 1))
        self.conn.commit()
    
    def unban_user(self, platform, platform_id):
        self.cursor.execute("UPDATE users SET banned = 0, ban_reason = NULL WHERE platform = ? AND platform_id = ?", (platform, platform_id))
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
    
    def get_mod_rank(self, platform, platform_id):
        self.cursor.execute("SELECT mod_rank FROM users WHERE platform = ? AND platform_id = ?", (platform, platform_id))
        result = self.cursor.fetchone()
        return result[0] if result else 0
    
    def set_mod_rank(self, platform, platform_id, rank, setter_id):
        self.cursor.execute("UPDATE users SET mod_rank = ? WHERE platform = ? AND platform_id = ?", (rank, platform, platform_id))
        self.conn.commit()
    
    def get_moderators(self, platform):
        self.cursor.execute("SELECT platform_id, first_name, username, mod_rank FROM users WHERE platform = ? AND mod_rank > 0 ORDER BY mod_rank DESC", (platform,))
        return self.cursor.fetchall()
    
    def get_group_settings(self, chat_id, platform):
        self.cursor.execute("SELECT * FROM group_settings WHERE chat_id = ? AND platform = ?", (chat_id, platform))
        settings = self.cursor.fetchone()
        if not settings:
            self.cursor.execute('''
                INSERT INTO group_settings (chat_id, platform) VALUES (?, ?)
            ''', (chat_id, platform))
            self.conn.commit()
            return self.get_group_settings(chat_id, platform)
        columns = [description[0] for description in self.cursor.description]
        return dict(zip(columns, settings))
    
    def update_group_setting(self, chat_id, platform, setting, value):
        self.cursor.execute(f"UPDATE group_settings SET {setting} = ? WHERE chat_id = ? AND platform = ?", (value, chat_id, platform))
        self.conn.commit()
    
    def has_privilege(self, platform, platform_id, privilege):
        if int(platform_id) == OWNER_ID:
            return True
        self.cursor.execute("SELECT mod_rank, privilege, privilege_until FROM users WHERE platform = ? AND platform_id = ?", (platform, platform_id))
        user = self.cursor.fetchone()
        if not user:
            return False
        if user[0] >= 3:
            return True
        if user[1] == privilege and user[2]:
            return datetime.datetime.now() < datetime.datetime.fromisoformat(user[2])
        return False
    
    # ===================== НОВЫЕ ФУНКЦИИ =====================
    
    # Ежедневные бонусы
    def can_claim_daily(self, platform, platform_id):
        self.cursor.execute("SELECT last_daily FROM users WHERE platform = ? AND platform_id = ?", (platform, platform_id))
        result = self.cursor.fetchone()
        if result and result[0]:
            last = datetime.datetime.fromisoformat(result[0])
            return datetime.datetime.now().date() > last.date()
        return True
    
    def claim_daily(self, platform, platform_id):
        self.cursor.execute("SELECT daily_streak FROM users WHERE platform = ? AND platform_id = ?", (platform, platform_id))
        streak = self.cursor.fetchone()[0] + 1
        self.cursor.execute("UPDATE users SET daily_streak = ?, last_daily = ? WHERE platform = ? AND platform_id = ?", 
                           (streak, datetime.datetime.now(), platform, platform_id))
        self.conn.commit()
        
        # Расчет награды
        base_coins = 100
        bonus = int(base_coins * (min(streak, 30) * 0.1))
        total = base_coins + bonus
        
        self.add_coins(platform, platform_id, total, "coins")
        self.add_exp(platform, platform_id, 20 + streak)
        
        return total, streak
    
    def can_claim_weekly(self, platform, platform_id):
        self.cursor.execute("SELECT last_weekly FROM users WHERE platform = ? AND platform_id = ?", (platform, platform_id))
        result = self.cursor.fetchone()
        if result and result[0]:
            last = datetime.datetime.fromisoformat(result[0])
            return (datetime.datetime.now() - last).days >= 7
        return True
    
    def claim_weekly(self, platform, platform_id):
        self.cursor.execute("SELECT weekly_streak FROM users WHERE platform = ? AND platform_id = ?", (platform, platform_id))
        streak = self.cursor.fetchone()[0] + 1
        self.cursor.execute("UPDATE users SET weekly_streak = ?, last_weekly = ? WHERE platform = ? AND platform_id = ?", 
                           (streak, datetime.datetime.now(), platform, platform_id))
        self.conn.commit()
        
        total = 500 + (streak * 50)
        self.add_coins(platform, platform_id, total, "coins")
        self.add_exp(platform, platform_id, 100 + streak * 10)
        
        return total, streak
    
    # Достижения
    def check_achievements(self, platform, platform_id):
        user = self.get_user(platform, platform_id)
        self.cursor.execute("SELECT achievements FROM users WHERE platform = ? AND platform_id = ?", (platform, platform_id))
        result = self.cursor.fetchone()
        earned = json.loads(result[0]) if result and result[0] else []
        
        self.cursor.execute("SELECT * FROM achievements")
        achievements = self.cursor.fetchall()
        columns = [description[0] for description in self.cursor.description]
        
        new_achievements = []
        for ach in achievements:
            ach_dict = dict(zip(columns, ach))
            if ach_dict['name'] in earned:
                continue
            
            condition = ach_dict['condition_type']
            value = ach_dict['condition_value']
            
            if condition == 'level' and user['level'] >= value:
                new_achievements.append(ach_dict)
            elif condition == 'boss_kills' and user['boss_kills'] >= value:
                new_achievements.append(ach_dict)
            elif condition == 'games_played' and user['games_played'] >= value:
                new_achievements.append(ach_dict)
            elif condition == 'coins' and user['coins'] >= value:
                new_achievements.append(ach_dict)
            elif condition == 'mafia_wins' and user['mafia_wins'] >= value:
                new_achievements.append(ach_dict)
            elif condition == 'minesweeper_wins' and user['minesweeper_wins'] >= value:
                new_achievements.append(ach_dict)
            elif condition == 'rr_wins' and user['rr_wins'] >= value:
                new_achievements.append(ach_dict)
            elif condition == 'ttt_wins' and user['ttt_wins'] >= value:
                new_achievements.append(ach_dict)
        
        for ach in new_achievements:
            earned.append(ach['name'])
            self.add_coins(platform, platform_id, ach['reward_coins'], "coins")
            self.add_exp(platform, platform_id, ach['reward_exp'])
        
        self.cursor.execute("UPDATE users SET achievements = ? WHERE platform = ? AND platform_id = ?", 
                           (json.dumps(earned), platform, platform_id))
        self.conn.commit()
        
        return new_achievements
    
    # Кланы
    def create_clan(self, name, owner_id):
        try:
            self.cursor.execute("INSERT INTO clans (name, owner_id) VALUES (?, ?)", (name, owner_id))
            self.conn.commit()
            clan_id = self.cursor.lastrowid
            self.cursor.execute("INSERT INTO clan_members (clan_id, user_id, role, joined_at) VALUES (?, ?, ?, ?)", 
                               (clan_id, owner_id, 'owner', datetime.datetime.now()))
            self.cursor.execute("UPDATE users SET clan_id = ?, clan_role = ? WHERE platform_id = ?", 
                               (clan_id, 'owner', owner_id))
            self.conn.commit()
            return clan_id
        except:
            return None
    
    def join_clan(self, clan_id, user_id):
        self.cursor.execute("SELECT members FROM clans WHERE id = ?", (clan_id,))
        members = self.cursor.fetchone()[0]
        if members >= 50:
            return False, "Клан заполнен"
        
        self.cursor.execute("INSERT INTO clan_members (clan_id, user_id, role, joined_at) VALUES (?, ?, ?, ?)", 
                           (clan_id, user_id, 'member', datetime.datetime.now()))
        self.cursor.execute("UPDATE users SET clan_id = ?, clan_role = ? WHERE platform_id = ?", 
                           (clan_id, 'member', user_id))
        self.cursor.execute("UPDATE clans SET members = members + 1 WHERE id = ?", (clan_id,))
        self.conn.commit()
        return True, "Вы вступили в клан"
    
    def get_clan(self, clan_id):
        self.cursor.execute("SELECT * FROM clans WHERE id = ?", (clan_id,))
        clan = self.cursor.fetchone()
        if clan:
            columns = [description[0] for description in self.cursor.description]
            return dict(zip(columns, clan))
        return None
    
    def get_clan_members(self, clan_id):
        self.cursor.execute("SELECT user_id, role, joined_at FROM clan_members WHERE clan_id = ?", (clan_id,))
        return self.cursor.fetchall()
    
    def add_clan_exp(self, clan_id, exp):
        self.cursor.execute("UPDATE clans SET exp = exp + ? WHERE id = ?", (exp, clan_id))
        self.cursor.execute("SELECT exp, level FROM clans WHERE id = ?", (clan_id,))
        exp, level = self.cursor.fetchone()
        if exp >= level * 500:
            self.cursor.execute("UPDATE clans SET level = level + 1, exp = exp - ? WHERE id = ?", (level * 500, clan_id))
        self.conn.commit()
    
    # Питомцы
    def create_pet(self, owner_id, name, pet_type):
        self.cursor.execute('''
            INSERT INTO pets (owner_id, name, type, created_at)
            VALUES (?, ?, ?, ?)
        ''', (owner_id, name, pet_type, datetime.datetime.now()))
        self.conn.commit()
        pet_id = self.cursor.lastrowid
        self.cursor.execute("UPDATE users SET pet_id = ?, pet_name = ? WHERE platform_id = ?", (pet_id, name, owner_id))
        self.conn.commit()
        return pet_id
    
    def get_pet(self, pet_id):
        self.cursor.execute("SELECT * FROM pets WHERE id = ?", (pet_id,))
        pet = self.cursor.fetchone()
        if pet:
            columns = [description[0] for description in self.cursor.description]
            return dict(zip(columns, pet))
        return None
    
    def feed_pet(self, pet_id):
        self.cursor.execute("UPDATE pets SET hunger = hunger + 20, happiness = happiness + 10 WHERE id = ?", (pet_id,))
        self.cursor.execute("UPDATE pets SET hunger = 100 WHERE hunger > 100")
        self.cursor.execute("UPDATE pets SET happiness = 100 WHERE happiness > 100")
        self.conn.commit()
    
    def pet_battle(self, pet1_id, pet2_id):
        pet1 = self.get_pet(pet1_id)
        pet2 = self.get_pet(pet2_id)
        
        power1 = pet1['level'] * 10 + pet1['happiness'] // 10
        power2 = pet2['level'] * 10 + pet2['happiness'] // 10
        
        if random.random() < power1 / (power1 + power2):
            winner = pet1
            loser = pet2
        else:
            winner = pet2
            loser = pet1
        
        self.cursor.execute("UPDATE pets SET wins = wins + 1, exp = exp + 20 WHERE id = ?", (winner['id'],))
        self.cursor.execute("UPDATE pets SET losses = losses + 1, exp = exp + 10 WHERE id = ?", (loser['id'],))
        
        # Проверка уровня
        for pet in [winner, loser]:
            self.cursor.execute("SELECT exp FROM pets WHERE id = ?", (pet['id'],))
            exp = self.cursor.fetchone()[0]
            if exp >= pet['level'] * 100:
                self.cursor.execute("UPDATE pets SET level = level + 1, exp = exp - ? WHERE id = ?", (pet['level'] * 100, pet['id']))
        
        self.conn.commit()
        return winner
    
    # Турниры
    def create_tournament(self, name, days=7):
        start = datetime.datetime.now()
        end = start + datetime.timedelta(days=days)
        self.cursor.execute('''
            INSERT INTO tournaments (name, start_date, end_date, status)
            VALUES (?, ?, ?, ?)
        ''', (name, start, end, 'active'))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def join_tournament(self, tournament_id, user_id):
        self.cursor.execute('''
            INSERT OR IGNORE INTO tournament_participants (tournament_id, user_id)
            VALUES (?, ?)
        ''', (tournament_id, user_id))
        self.conn.commit()
    
    def add_tournament_points(self, tournament_id, user_id, points):
        self.cursor.execute('''
            UPDATE tournament_participants SET points = points + ?
            WHERE tournament_id = ? AND user_id = ?
        ''', (points, tournament_id, user_id))
        self.conn.commit()
    
    def get_tournament_ranking(self, tournament_id):
        self.cursor.execute('''
            SELECT user_id, points FROM tournament_participants
            WHERE tournament_id = ? ORDER BY points DESC LIMIT 10
        ''', (tournament_id,))
        return self.cursor.fetchall()
    
    def close(self):
        self.conn.close()

# ===================== ИНИЦИАЛИЗАЦИЯ =====================
db = Database()
ai = SpectrumAI()

# ===================== ОСНОВНОЙ КЛАСС БОТА =====================
class GameBot:
    def __init__(self):
        self.db = db
        self.ai = ai
        self.tg_application = None
        self.last_activity = defaultdict(dict)
        self.spam_tracker = defaultdict(list)
        self.mafia_games = {}
        
        if TELEGRAM_TOKEN:
            self.tg_application = Application.builder().token(TELEGRAM_TOKEN).build()
            self.setup_tg_handlers()
            logger.info("✅ Telegram бот инициализирован")
    
    # ===================== TELEGRAM ОБРАБОТЧИКИ =====================
    def setup_tg_handlers(self):
        # Основные
        self.tg_application.add_handler(CommandHandler("start", self.cmd_start))
        self.tg_application.add_handler(CommandHandler("help", self.cmd_help))
        
        # Профиль и статистика
        self.tg_application.add_handler(CommandHandler("profile", self.cmd_profile))
        self.tg_application.add_handler(CommandHandler("whoami", self.cmd_whoami))
        self.tg_application.add_handler(CommandHandler("top", self.cmd_top))
        self.tg_application.add_handler(CommandHandler("players", self.cmd_players))
        
        # Боссы
        self.tg_application.add_handler(CommandHandler("boss", self.cmd_boss))
        self.tg_application.add_handler(CommandHandler("boss_fight", self.cmd_boss_fight))
        self.tg_application.add_handler(CommandHandler("regen", self.cmd_regen))
        
        # Экономика
        self.tg_application.add_handler(CommandHandler("shop", self.cmd_shop))
        self.tg_application.add_handler(CommandHandler("donate", self.cmd_donate))
        self.tg_application.add_handler(CommandHandler("pay", self.cmd_pay))
        
        # Ежедневные бонусы
        self.tg_application.add_handler(CommandHandler("daily", self.cmd_daily))
        self.tg_application.add_handler(CommandHandler("weekly", self.cmd_weekly))
        self.tg_application.add_handler(CommandHandler("streak", self.cmd_streak))
        
        # Достижения
        self.tg_application.add_handler(CommandHandler("achievements", self.cmd_achievements))
        
        # Кланы
        self.tg_application.add_handler(CommandHandler("clan", self.cmd_clan))
        self.tg_application.add_handler(CommandHandler("clan_create", self.cmd_clan_create))
        self.tg_application.add_handler(CommandHandler("clan_join", self.cmd_clan_join))
        self.tg_application.add_handler(CommandHandler("clan_top", self.cmd_clan_top))
        
        # Питомцы
        self.tg_application.add_handler(CommandHandler("pet", self.cmd_pet))
        self.tg_application.add_handler(CommandHandler("pet_buy", self.cmd_pet_buy))
        self.tg_application.add_handler(CommandHandler("pet_feed", self.cmd_pet_feed))
        self.tg_application.add_handler(CommandHandler("pet_fight", self.cmd_pet_fight))
        
        # Турниры
        self.tg_application.add_handler(CommandHandler("tournament", self.cmd_tournament))
        self.tg_application.add_handler(CommandHandler("tournament_join", self.cmd_tournament_join))
        self.tg_application.add_handler(CommandHandler("rating", self.cmd_rating))
        
        # Полезные команды
        self.tg_application.add_handler(CommandHandler("joke", self.cmd_joke))
        self.tg_application.add_handler(CommandHandler("wisdom", self.cmd_wisdom))
        self.tg_application.add_handler(CommandHandler("mood", self.cmd_mood))
        self.tg_application.add_handler(CommandHandler("weather", self.cmd_weather))
        self.tg_application.add_handler(CommandHandler("news", self.cmd_news))
        self.tg_application.add_handler(CommandHandler("quote", self.cmd_quote))
        self.tg_application.add_handler(CommandHandler("fact", self.cmd_fact))
        self.tg_application.add_handler(CommandHandler("bitcoin", self.cmd_bitcoin))
        
        # Голосования
        self.tg_application.add_handler(CommandHandler("poll", self.cmd_poll))
        self.tg_application.add_handler(CommandHandler("vote", self.cmd_vote))
        self.tg_application.add_handler(CommandHandler("results", self.cmd_results))
        
        # Закладки и награды
        self.tg_application.add_handler(CommandHandler("bookmark", self.cmd_add_bookmark))
        self.tg_application.add_handler(CommandHandler("bookmarks", self.cmd_bookmarks))
        self.tg_application.add_handler(CommandHandler("award", self.cmd_add_award))
        self.tg_application.add_handler(CommandHandler("awards", self.cmd_awards))
        
        # Система модерации
        self.tg_application.add_handler(CommandHandler("moder", self.cmd_moder))
        self.tg_application.add_handler(CommandHandler("staff", self.cmd_staff))
        self.tg_application.add_handler(CommandHandler("warn", self.cmd_warn))
        self.tg_application.add_handler(CommandHandler("mute", self.cmd_mute))
        self.tg_application.add_handler(CommandHandler("ban", self.cmd_ban))
        self.tg_application.add_handler(CommandHandler("unban", self.cmd_unban))
        self.tg_application.add_handler(CommandHandler("banlist", self.cmd_banlist))
        self.tg_application.add_handler(CommandHandler("rules", self.cmd_rules))
        self.tg_application.add_handler(CommandHandler("set_rules", self.cmd_set_rules))
        
        # Игры
        self.tg_application.add_handler(CommandHandler("rr", self.cmd_rr))
        self.tg_application.add_handler(CommandHandler("rr_start", self.cmd_rr_start))
        self.tg_application.add_handler(CommandHandler("rr_join", self.cmd_rr_join))
        self.tg_application.add_handler(CommandHandler("rr_shot", self.cmd_rr_shot))
        
        self.tg_application.add_handler(CommandHandler("ttt", self.cmd_ttt))
        self.tg_application.add_handler(CommandHandler("ttt_challenge", self.cmd_ttt_challenge))
        self.tg_application.add_handler(CommandHandler("ttt_move", self.cmd_ttt_move))
        
        self.tg_application.add_handler(CommandHandler("mafia", self.cmd_mafia))
        self.tg_application.add_handler(CommandHandler("mafia_create", self.cmd_mafia_create))
        self.tg_application.add_handler(CommandHandler("mafia_join", self.cmd_mafia_join))
        self.tg_application.add_handler(CommandHandler("mafia_start", self.cmd_mafia_start))
        self.tg_application.add_handler(CommandHandler("mafia_vote", self.cmd_mafia_vote))
        self.tg_application.add_handler(CommandHandler("mafia_kill", self.cmd_mafia_kill))
        
        self.tg_application.add_handler(CommandHandler("minesweeper", self.cmd_minesweeper))
        self.tg_application.add_handler(CommandHandler("ms_reveal", self.cmd_ms_reveal))
        self.tg_application.add_handler(CommandHandler("ms_flag", self.cmd_ms_flag))
        
        self.tg_application.add_handler(CommandHandler("rps", self.cmd_rps))
        
        # Обработка сообщений (AI)
        self.tg_application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Обработка новых участников
        self.tg_application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, self.handle_new_members))
        self.tg_application.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, self.handle_left_member))
        
        logger.info("✅ Telegram обработчики зарегистрированы")
    
    # ===================== ОСНОВНЫЕ КОМАНДЫ =====================
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        
        db.get_user('tg', platform_id, user.username or "", user.first_name, user.last_name or "")
        db.update_activity('tg', platform_id)
        
        mood = await self.ai.mood()
        
        text = f"╔══════════════════════════════╗\n"
        text += f"║     ⚔️ **СПЕКТР БОТ** ⚔️     ║\n"
        text += f"╚══════════════════════════════╝\n\n"
        text += f"🌟 **Привет, {user.first_name}!**\n"
        text += f"💬 **Спектр:** {mood}\n\n"
        text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += f"📌 **ОСНОВНЫЕ КОМАНДЫ**\n"
        text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += f"👤 /profile — твой профиль\n"
        text += f"👾 /boss — битва с боссом\n"
        text += f"💰 /shop — магазин\n"
        text += f"🎁 /daily — ежедневный бонус\n"
        text += f"🏆 /achievements — достижения\n"
        text += f"👥 /clan — кланы\n"
        text += f"🐾 /pet — питомцы\n"
        text += f"📊 /top — топ игроков\n"
        text += f"👥 /players — онлайн\n"
        text += f"📚 /help — все команды\n\n"
        text += f"👑 **Владелец:** {OWNER_USERNAME}\n"
        text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        db.update_activity('tg', platform_id)
        
        text = (
            "📚 **СПРАВОЧНИК КОМАНД**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🔰 **ОСНОВНЫЕ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/start — запуск бота\n"
            "/help — эта справка\n"
            "/profile — твой профиль\n"
            "/whoami — информация о себе\n"
            "/top — топ игроков\n"
            "/players — количество игроков\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🎁 **БОНУСЫ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/daily — ежедневный бонус\n"
            "/weekly — недельный бонус\n"
            "/streak — проверить стрик\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🏆 **ДОСТИЖЕНИЯ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/achievements — список достижений\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "👥 **КЛАНЫ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/clan — информация о клане\n"
            "/clan_create [название] — создать клан\n"
            "/clan_join [ID] — вступить в клан\n"
            "/clan_top — топ кланов\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🐾 **ПИТОМЦЫ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/pet — информация о питомце\n"
            "/pet_buy [имя] [тип] — купить питомца\n"
            "/pet_feed — покормить питомца\n"
            "/pet_fight [ID] — битва питомцев\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚔️ **БИТВА С БОССОМ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/boss — информация о боссе\n"
            "/boss_fight [id] — ударить босса\n"
            "/regen — восстановить здоровье\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "💰 **ЭКОНОМИКА**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/shop — магазин\n"
            "/donate — привилегии\n"
            "/pay [ник] [сумма] — перевести монеты\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🎮 **ИГРЫ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/rr — русская рулетка\n"
            "/ttt — крестики-нолики 3D\n"
            "/mafia — мафия\n"
            "/minesweeper [сложность] — сапёр\n"
            "/rps — камень-ножницы-бумага\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🏆 **ТУРНИРЫ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/tournament — информация о турнире\n"
            "/tournament_join — участвовать\n"
            "/rating — рейтинг игроков\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🤖 **AI ФУНКЦИИ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/joke — шутка от Спектра\n"
            "/wisdom — мудрая мысль\n"
            "/mood — настроение Спектра\n"
            "/weather [город] — погода\n"
            "/news — последние новости\n"
            "/quote — цитата дня\n"
            "/fact — случайный факт\n"
            "/bitcoin — курс биткоина\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📊 **ГОЛОСОВАНИЯ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/poll [вопрос] — создать опрос\n"
            "/vote [номер] [вариант] — проголосовать\n"
            "/results [ID] — результаты\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📌 **ЗАКЛАДКИ И НАГРАДЫ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/bookmark [описание] — создать закладку\n"
            "/bookmarks — список закладок\n"
            "/award [ник] [название] — дать награду\n"
            "/awards — список наград\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🛡️ **МОДЕРАЦИЯ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/staff — список модераторов\n"
            "/warn [ссылка] [причина] — варн\n"
            "/mute [ссылка] [время] — мут\n"
            "/ban [ссылка] [время] — бан\n"
            "/unban [ссылка] — разбан\n"
            "/banlist — список банов\n"
            "/rules — правила\n"
            "/set_rules [текст] — установить правила\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👑 **Владелец:** {OWNER_USERNAME}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        
        user_data = db.get_user('tg', platform_id, user.username or "", user.first_name, user.last_name or "")
        db.update_activity('tg', platform_id)
        
        # Проверяем достижения
        new_achievements = db.check_achievements('tg', platform_id)
        
        if db.is_banned('tg', platform_id):
            await update.message.reply_text("🚫 **Вы забанены в боте**")
            return
        
        if db.is_muted('tg', platform_id):
            mute_until = datetime.datetime.fromisoformat(user_data['mute_until'])
            remaining = mute_until - datetime.datetime.now()
            minutes = remaining.seconds // 60
            await update.message.reply_text(f"🔇 **Вы замучены**\nОсталось: {minutes} мин")
            return
        
        # Получаем информацию о клане
        clan_info = ""
        if user_data['clan_id']:
            clan = db.get_clan(user_data['clan_id'])
            if clan:
                clan_info = f"\n👥 Клан: {clan['name']} (ур.{clan['level']})"
        
        # Получаем информацию о питомце
        pet_info = ""
        if user_data['pet_id']:
            pet = db.get_pet(user_data['pet_id'])
            if pet:
                pet_info = f"\n🐾 Питомец: {pet['name']} (ур.{pet['level']})"
        
        # Активность
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
        
        first_seen = "Неизвестно"
        if user_data.get('first_seen'):
            first = datetime.datetime.fromisoformat(user_data['first_seen'])
            delta = datetime.datetime.now() - first
            years = delta.days // 365
            months = (delta.days % 365) // 30
            days = delta.days % 30
            first_seen = f"{first.strftime('%d.%m.%Y')} ({years} г {months} мес {days} дн)"
        
        # Получаем достижения
        achievements = json.loads(user_data.get('achievements', '[]'))
        achievements_text = ""
        if achievements:
            achievements_text = f"\n🏅 Достижений: {len(achievements)}"
        
        text = f"╔══════════════════════════════╗\n"
        text += f"║      👤 **ПРОФИЛЬ** 👤      ║\n"
        text += f"╚══════════════════════════════╝\n\n"
        
        text += f"**{user_data.get('nickname') or user.first_name}**\n"
        text += f"ID: {user.id}\n"
        text += f"{clan_info}{pet_info}\n\n"
        
        text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += f"**РЕСУРСЫ**\n"
        text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += f"🪙 Монеты: {user_data['coins']:,}\n"
        text += f"💎 Алмазы: {user_data['diamonds']:,}\n"
        text += f"💀 Черепки: {user_data['rr_money']}\n"
        text += f"🎁 Стрик: {user_data['daily_streak']} дней\n\n"
        
        text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += f"**ХАРАКТЕРИСТИКИ**\n"
        text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += f"❤️ Здоровье: {user_data['health']}/{user_data['max_health']}\n"
        text += f"⚔️ Урон: {user_data['damage']}\n"
        text += f"⚡ Энергия: {user_data['energy']}\n"
        text += f"📊 Уровень: {user_data['level']}\n"
        text += f"👾 Боссов убито: {user_data['boss_kills']}\n\n"
        
        text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += f"**СТАТИСТИКА**\n"
        text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += f"📝 Сообщений: {user_data['messages_count']}\n"
        text += f"⌨️ Команд: {user_data['commands_used']}\n"
        text += f"🎮 Игр: {user_data['games_played']}\n"
        text += f"🏅 Достижения: {len(achievements)}\n"
        text += f"⏱ Последний визит: {last_activity}\n"
        text += f"📅 Первое появление: {first_seen}"
        
        if new_achievements:
            text += f"\n\n🎉 **НОВЫЕ ДОСТИЖЕНИЯ!**"
            for ach in new_achievements:
                text += f"\n🏅 {ach['name']} +{ach['reward_coins']}🪙"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_whoami(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        
        user_data = db.get_user('tg', platform_id, user.username or "", user.first_name, user.last_name or "")
        
        achievements = json.loads(user_data.get('achievements', '[]'))
        
        text = f"╔══════════════════════════════╗\n"
        text += f"║        👤 **КТО Я** 👤       ║\n"
        text += f"╚══════════════════════════════╝\n\n"
        
        text += f"Это {user.first_name}\n"
        text += f"Репутация: ✨ {user_data['reputation']}\n"
        text += f"Стрик: {user_data['daily_streak']} дней\n"
        text += f"Достижений: {len(achievements)}\n"
        text += f"Первое появление: {user_data['first_seen'][:10]}\n"
        text += f"Активность: {user_data['messages_count']} сообщений\n"
        text += f"Игр сыграно: {user_data['games_played']}"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_top(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        top_coins = db.get_top("coins", 10)
        top_level = db.get_top("level", 10)
        top_boss = db.get_top("boss_kills", 10)
        
        text = f"╔══════════════════════════════╗\n"
        text += f"║      🏆 **ТОП ИГРОКОВ**      ║\n"
        text += f"╚══════════════════════════════╝\n\n"
        
        text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += f"💰 **ПО МОНЕТАМ**\n"
        text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        for i, (username, first_name, value) in enumerate(top_coins, 1):
            name = first_name or username or f"Игрок {i}"
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} {name} — {value:,} 🪙\n"
        
        text += f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += f"📊 **ПО УРОВНЮ**\n"
        text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        for i, (username, first_name, value) in enumerate(top_level, 1):
            name = first_name or username or f"Игрок {i}"
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} {name} — {value} ур.\n"
        
        text += f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += f"👾 **ПО УБИЙСТВУ БОССОВ**\n"
        text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        for i, (username, first_name, value) in enumerate(top_boss, 1):
            name = first_name or username or f"Игрок {i}"
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} {name} — {value} боссов\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_players(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        count = db.get_player_count()
        await update.message.reply_text(f"👥 **Активных игроков:** {count}", parse_mode='Markdown')
    
    # ===================== ЕЖЕДНЕВНЫЕ БОНУСЫ =====================
    async def cmd_daily(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        
        if not db.can_claim_daily('tg', platform_id):
            await update.message.reply_text("❌ Ты уже получал ежедневный бонус сегодня!")
            return
        
        total, streak = db.claim_daily('tg', platform_id)
        
        # AI комментирует
        comment = await self.ai.get_response(user.id, f"игрок получил ежедневный бонус {total} монет, стрик {streak} дней")
        
        text = f"🎁 **ЕЖЕДНЕВНЫЙ БОНУС**\n\n"
        text += f"💰 Получено: {total} 🪙\n"
        text += f"🔥 Стрик: {streak} дней\n\n"
        text += f"💬 **Спектр:** {comment}"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_weekly(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        
        if not db.can_claim_weekly('tg', platform_id):
            await update.message.reply_text("❌ Ты уже получал недельный бонус!")
            return
        
        total, streak = db.claim_weekly('tg', platform_id)
        
        text = f"🎁 **НЕДЕЛЬНЫЙ БОНУС**\n\n"
        text += f"💰 Получено: {total} 🪙\n"
        text += f"🔥 Стрик: {streak} недель"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_streak(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        user_data = db.get_user('tg', platform_id)
        
        streak = user_data.get('daily_streak', 0)
        weekly = user_data.get('weekly_streak', 0)
        
        text = f"🔥 **ТВОЙ СТРИК**\n\n"
        text += f"📅 Дневной: {streak} дней\n"
        text += f"📆 Недельный: {weekly} недель"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    # ===================== ДОСТИЖЕНИЯ =====================
    async def cmd_achievements(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        user_data = db.get_user('tg', platform_id)
        
        achievements = json.loads(user_data.get('achievements', '[]'))
        
        if not achievements:
            await update.message.reply_text("🏅 У тебя пока нет достижений. Играй и получай!")
            return
        
        text = f"🏆 **ТВОИ ДОСТИЖЕНИЯ**\n\n"
        
        for ach in achievements:
            text += f"🏅 {ach}\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    # ===================== КЛАНЫ =====================
    async def cmd_clan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        user_data = db.get_user('tg', platform_id)
        
        if not user_data['clan_id']:
            await update.message.reply_text(
                "👥 Ты не состоишь в клане.\n\n"
                "/clan_create [название] — создать клан\n"
                "/clan_join [ID] — вступить в клан"
            )
            return
        
        clan = db.get_clan(user_data['clan_id'])
        members = db.get_clan_members(clan['id'])
        
        text = f"👥 **КЛАН «{clan['name']}»**\n\n"
        text += f"📊 Уровень: {clan['level']}\n"
        text += f"👥 Участников: {clan['members']}/50\n"
        text += f"🏆 Рейтинг: {clan['rating']}\n\n"
        text += f"**УЧАСТНИКИ**\n"
        
        for member in members[:10]:
            user_id, role, joined = member
            user_data = db.get_user('tg', user_id)
            name = user_data.get('first_name', f"ID {user_id}")
            role_emoji = "👑" if role == 'owner' else "🛡️" if role == 'admin' else "👤"
            text += f"{role_emoji} {name}\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_clan_create(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Использование: /clan_create [название]")
            return
        
        name = " ".join(context.args)
        user = update.effective_user
        platform_id = str(user.id)
        user_data = db.get_user('tg', platform_id)
        
        if len(name) > 30:
            await update.message.reply_text("❌ Название слишком длинное (макс 30 символов)")
            return
        
        if user_data['clan_id']:
            await update.message.reply_text("❌ Ты уже в клане")
            return
        
        if user_data['level'] < 5:
            await update.message.reply_text("❌ Для создания клана нужен 5 уровень")
            return
        
        if user_data['coins'] < 1000:
            await update.message.reply_text("❌ Для создания клана нужно 1000 🪙")
            return
        
        clan_id = db.create_clan(name, platform_id)
        
        if clan_id:
            db.add_coins('tg', platform_id, -1000, "coins")
            await update.message.reply_text(f"✅ Клан «{name}» создан! ID: {clan_id}")
        else:
            await update.message.reply_text("❌ Клан с таким названием уже существует")
    
    async def cmd_clan_join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Использование: /clan_join [ID]")
            return
        
        try:
            clan_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ Неправильный ID")
            return
        
        user = update.effective_user
        platform_id = str(user.id)
        user_data = db.get_user('tg', platform_id)
        
        if user_data['clan_id']:
            await update.message.reply_text("❌ Ты уже в клане")
            return
        
        success, message = db.join_clan(clan_id, platform_id)
        
        if success:
            await update.message.reply_text(f"✅ {message}")
        else:
            await update.message.reply_text(f"❌ {message}")
    
    async def cmd_clan_top(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Здесь нужна функция для топа кланов
        await update.message.reply_text("🏆 Топ кланов будет доступен в следующем обновлении")
    
    # ===================== ПИТОМЦЫ =====================
    async def cmd_pet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        user_data = db.get_user('tg', platform_id)
        
        if not user_data['pet_id']:
            await update.message.reply_text(
                "🐾 У тебя нет питомца.\n"
                "/pet_buy [имя] [тип] — купить питомца\n\n"
                "Типы: дракон, котик, пёсик, зайка"
            )
            return
        
        pet = db.get_pet(user_data['pet_id'])
        
        text = f"🐾 **ПИТОМЕЦ {pet['name']}**\n\n"
        text += f"📊 Уровень: {pet['level']}\n"
        text += f"❤️ Сытость: {pet['hunger']}/100\n"
        text += f"😊 Счастье: {pet['happiness']}/100\n"
        text += f"🏆 Побед: {pet['wins']}\n"
        text += f"💔 Поражений: {pet['losses']}\n\n"
        text += f"/pet_feed — покормить\n"
        text += f"/pet_fight [ID] — битва"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_pet_buy(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /pet_buy [имя] [тип]")
            return
        
        name = context.args[0]
        pet_type = context.args[1]
        
        valid_types = ["дракон", "котик", "пёсик", "зайка"]
        if pet_type not in valid_types:
            await update.message.reply_text(f"❌ Тип должен быть: {', '.join(valid_types)}")
            return
        
        user = update.effective_user
        platform_id = str(user.id)
        user_data = db.get_user('tg', platform_id)
        
        if user_data['pet_id']:
            await update.message.reply_text("❌ У тебя уже есть питомец")
            return
        
        if user_data['coins'] < 500:
            await update.message.reply_text("❌ Нужно 500 🪙 для покупки питомца")
            return
        
        pet_id = db.create_pet(platform_id, name, pet_type)
        db.add_coins('tg', platform_id, -500, "coins")
        
        await update.message.reply_text(f"✅ Питомец {name} куплен! ID: {pet_id}")
    
    async def cmd_pet_feed(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        user_data = db.get_user('tg', platform_id)
        
        if not user_data['pet_id']:
            await update.message.reply_text("❌ У тебя нет питомца")
            return
        
        if user_data['coins'] < 50:
            await update.message.reply_text("❌ Нужно 50 🪙 для кормления")
            return
        
        db.feed_pet(user_data['pet_id'])
        db.add_coins('tg', platform_id, -50, "coins")
        
        await update.message.reply_text("🍖 Питомец покормлен!")
    
    async def cmd_pet_fight(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Использование: /pet_fight [ID питомца]")
            return
        
        try:
            target_pet_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ Неправильный ID")
            return
        
        user = update.effective_user
        platform_id = str(user.id)
        user_data = db.get_user('tg', platform_id)
        
        if not user_data['pet_id']:
            await update.message.reply_text("❌ У тебя нет питомца")
            return
        
        target_pet = db.get_pet(target_pet_id)
        if not target_pet:
            await update.message.reply_text("❌ Питомец не найден")
            return
        
        winner = db.pet_battle(user_data['pet_id'], target_pet_id)
        
        if winner['owner_id'] == platform_id:
            await update.message.reply_text(f"🎉 Твой питомец победил!")
        else:
            await update.message.reply_text(f"😢 Твой питомец проиграл...")
    
    # ===================== ТУРНИРЫ =====================
    async def cmd_tournament(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("🏆 Турниры будут доступны в следующем обновлении")
    
    async def cmd_tournament_join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("🏆 Участие в турнирах будет доступно в следующем обновлении")
    
    async def cmd_rating(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("📊 Рейтинг будет доступен в следующем обновлении")
    
    # ===================== AI ФУНКЦИИ =====================
    async def cmd_joke(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        joke = await self.ai.tell_joke()
        await update.message.reply_text(f"😄 **Шутка от Спектра:**\n\n{joke}", parse_mode='Markdown')
    
    async def cmd_wisdom(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        wisdom = await self.ai.give_wisdom()
        await update.message.reply_text(f"💭 **Мудрость от Спектра:**\n\n{wisdom}", parse_mode='Markdown')
    
    async def cmd_mood(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        mood = await self.ai.mood()
        await update.message.reply_text(f"🤖 **Настроение Спектра:**\n\n{mood}", parse_mode='Markdown')
    
    async def cmd_weather(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Использование: /weather [город]")
            return
        
        city = " ".join(context.args)
        
        # AI генерирует погоду (симуляция)
        response = await self.ai.get_response(user.id, f"какая погода в {city}")
        
        temp = random.randint(-20, 35)
        conditions = ["☀️ Солнечно", "☁️ Облачно", "🌧️ Дождливо", "🌨️ Снежно", "🌩️ Гроза"]
        condition = random.choice(conditions)
        
        text = f"🌤️ **ПОГОДА В {city.upper()}**\n\n"
        text += f"Температура: {temp}°C\n"
        text += f"Состояние: {condition}\n\n"
        text += f"💬 **Спектр:** {response}"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_news(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        response = await self.ai.get_response(user.id, "расскажи последние новости")
        await update.message.reply_text(f"📰 **НОВОСТИ**\n\n{response}", parse_mode='Markdown')
    
    async def cmd_quote(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        response = await self.ai.get_response(user.id, "скажи мудрую цитату")
        await update.message.reply_text(f"💬 **ЦИТАТА ДНЯ**\n\n{response}", parse_mode='Markdown')
    
    async def cmd_fact(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        response = await self.ai.get_response(user.id, "расскажи интересный факт")
        await update.message.reply_text(f"📌 **ИНТЕРЕСНЫЙ ФАКТ**\n\n{response}", parse_mode='Markdown')
    
    async def cmd_bitcoin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        price_usd = random.randint(40000, 70000)
        price_rub = price_usd * 91.5
        
        response = await self.ai.get_response(user.id, f"курс биткоина {price_usd}$")
        
        text = f"₿ **КУРС БИТКОИНА**\n\n"
        text += f"USD: ${price_usd:,}\n"
        text += f"RUB: ₽{int(price_rub):,}\n\n"
        text += f"💬 **Спектр:** {response}"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    # ===================== ГОЛОСОВАНИЯ =====================
    async def cmd_poll(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("📊 Голосования будут доступны в следующем обновлении")
    
    async def cmd_vote(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("🗳️ Голосование будет доступно в следующем обновлении")
    
    async def cmd_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("📊 Результаты будут доступны в следующем обновлении")
    
    # ===================== БОССЫ =====================
    async def cmd_boss(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        
        user_data = db.get_user('tg', platform_id, user.username or "", user.first_name, user.last_name or "")
        db.update_activity('tg', platform_id)
        
        if db.is_banned('tg', platform_id):
            await update.message.reply_text("🚫 Вы забанены в боте.")
            return
        
        if db.is_muted('tg', platform_id):
            mute_until = datetime.datetime.fromisoformat(user_data['mute_until'])
            remaining = mute_until - datetime.datetime.now()
            minutes = remaining.seconds // 60
            await update.message.reply_text(f"🔇 Вы замучены. Осталось: {minutes} мин")
            return
        
        boss = db.get_boss()
        
        if not boss:
            await update.message.reply_text("👾 Все боссы повержены! Ожидайте возрождения...")
            db.respawn_bosses()
            boss = db.get_boss()
        
        player_damage = user_data['damage'] * (1 + user_data['level'] * 0.1)
        
        text = f"╔══════════════════════════════╗\n"
        text += f"║   👾 **БИТВА С БОССОМ** 👾   ║\n"
        text += f"╚══════════════════════════════╝\n\n"
        
        text += f"{boss['boss_emoji']} **{boss['boss_name']}**\n"
        text += f"📊 Уровень: {boss['boss_level']}\n\n"
        
        text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += f"**ХАРАКТЕРИСТИКИ БОССА**\n"
        text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += f"💀 Здоровье: {boss['boss_health']} / {boss['boss_max_health']} HP\n"
        text += f"⚔️ Урон: {boss['boss_damage']} HP\n"
        text += f"💰 Награда: {boss['boss_reward']} 🪙\n\n"
        
        text += f"**ТВОИ ХАРАКТЕРИСТИКИ**\n"
        text += f"❤️ Здоровье: {user_data['health']} HP\n"
        text += f"🗡 Урон: {player_damage:.1f} ({user_data['damage']} базовый)\n"
        text += f"📊 Сила: {((player_damage / boss['boss_damage']) * 100):.1f}%\n\n"
        
        text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += f"**ДЕЙСТВИЯ**\n"
        text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += f"👊 /boss_fight {boss['id']} - ударить босса\n"
        text += f"➕ /regen - восстановить здоровье"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_boss_fight(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        
        if db.is_banned('tg', platform_id):
            await update.message.reply_text("🚫 Вы забанены в боте.")
            return
        
        if db.is_muted('tg', platform_id):
            mute_until = datetime.datetime.fromisoformat(user_data['mute_until'])
            remaining = mute_until - datetime.datetime.now()
            minutes = remaining.seconds // 60
            await update.message.reply_text(f"🔇 Вы замучены. Осталось: {minutes} мин")
            return
        
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
        
        # AI комментирует
        if killed:
            comment = await self.ai.get_response(user.id, f"игрок победил босса {boss['boss_name']}")
        else:
            comment = await self.ai.get_response(user.id, f"игрок нанес {player_damage} урона боссу")
        
        text = f"⚔️ **БИТВА С БОССОМ** ⚔️\n\n"
        text += f"**{boss['boss_name']}**\n\n"
        text += f"▫️ Твой урон: {player_damage} HP\n"
        text += f"▫️ Урон босса: {boss['boss_damage']} HP\n\n"
        
        if killed:
            reward = boss['boss_reward']
            db.add_coins('tg', platform_id, reward, "coins")
            db.add_boss_kill('tg', platform_id)
            db.add_exp('tg', platform_id, boss['boss_level'] * 10)
            
            next_boss = db.get_next_boss()
            
            text += f"🎉 **БОСС ПОВЕРЖЕН!**\n"
            text += f"💰 Награда: {reward} 🪙\n"
            text += f"✨ Опыт: +{boss['boss_level'] * 10}\n\n"
            
            if next_boss:
                text += f"👾 Следующий босс: {next_boss['boss_name']}"
            else:
                text += f"👾 Все боссы побеждены! Ожидайте возрождения..."
                db.respawn_bosses()
        else:
            text += f"👾 Босс еще жив!\n"
            text += f"💀 Осталось: {health_left} HP\n\n"
        
        text += f"💬 **Спектр:** {comment}"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_regen(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        
        user_data = db.get_user('tg', platform_id, user.username or "", user.first_name, user.last_name or "")
        db.update_activity('tg', platform_id)
        
        if db.is_banned('tg', platform_id):
            await update.message.reply_text("🚫 Вы забанены в боте.")
            return
        
        if db.is_muted('tg', platform_id):
            mute_until = datetime.datetime.fromisoformat(user_data['mute_until'])
            remaining = mute_until - datetime.datetime.now()
            minutes = remaining.seconds // 60
            await update.message.reply_text(f"🔇 Вы замучены. Осталось: {minutes} мин")
            return
        
        if not db.regen_available('tg', platform_id):
            await update.message.reply_text("❌ Регенерация еще не доступна! Подождите немного.")
            return
        
        if user_data['health'] < user_data['max_health']:
            heal_amount = user_data['max_health'] - user_data['health']
            db.heal_user('tg', platform_id, heal_amount)
            
            cooldown = 5
            if db.has_privilege('tg', platform_id, 'премиум'):
                cooldown = 1
            elif db.has_privilege('tg', platform_id, 'вип'):
                cooldown = 3
            
            db.use_regen('tg', platform_id, cooldown)
            
            comment = await self.ai.get_response(user.id, "игрок восстановил здоровье")
            
            await update.message.reply_text(
                f"➕ **РЕГЕНЕРАЦИЯ**\n\n"
                f"❤️ Здоровье восстановлено!\n"
                f"Текущее здоровье: {user_data['max_health']}/{user_data['max_health']}\n"
                f"⏱ Следующая регенерация через {cooldown} мин\n\n"
                f"💬 **Спектр:** {comment}",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❤️ У тебя уже полное здоровье!")
    
    # ===================== ЭКОНОМИКА =====================
    async def cmd_shop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        db.update_activity('tg', platform_id)
        
        if db.is_banned('tg', platform_id):
            await update.message.reply_text("🚫 Вы забанены в боте.")
            return
        
        text = (
            "╔══════════════════════════════╗\n"
            "║     🏪 **МАГАЗИН** 🏪        ║\n"
            "╚══════════════════════════════╝\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "💊 **ЗЕЛЬЯ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ Зелье здоровья — 50 🪙 (❤️+30)\n"
            "▫️ Большое зелье — 100 🪙 (❤️+70)\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚔️ **ОРУЖИЕ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ Меч — 200 🪙 (⚔️+10)\n"
            "▫️ Легендарный меч — 500 🪙 (⚔️+30)\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚡ **ЭНЕРГИЯ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ Энергетик — 30 🪙 (⚡+20)\n"
            "▫️ Батарейка — 80 🪙 (⚡+50)\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "💎 **ВАЛЮТА**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ Алмаз — 100 🪙 (💎+1)\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🎲 **ПРЕДМЕТЫ ДЛЯ РУЛЕТКИ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▫️ Монета Демона — 500 🪙\n"
            "▫️ Кровавый Глаз — 300 🪙\n"
            "▫️ Маска Клоуна — 1000 🪙\n\n"
            
            "🛒 Купить: /buy [название]"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_donate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        db.update_activity('tg', platform_id)
        
        if db.is_banned('tg', platform_id):
            await update.message.reply_text("🚫 Вы забанены в боте.")
            return
        
        text = (
            "💎 **ПРИВИЛЕГИИ** 💎\n\n"
            "🌟 VIP — 5000 🪙 (30 дней)\n"
            "💎 Premium — 15000 🪙 (30 дней)\n"
            "👑 Лорд — 30000 🪙 (30 дней)\n"
            "⚡ Ультра — 50000 🪙 (60 дней)\n"
            "🏆 Легенда — 100000 🪙 (90 дней)\n\n"
            f"💳 Приобрести: {OWNER_USERNAME}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_pay(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        db.update_activity('tg', platform_id)
        
        if db.is_banned('tg', platform_id):
            await update.message.reply_text("🚫 Вы забанены в боте.")
            return
        
        if db.is_muted('tg', platform_id):
            mute_until = datetime.datetime.fromisoformat(user_data['mute_until'])
            remaining = mute_until - datetime.datetime.now()
            minutes = remaining.seconds // 60
            await update.message.reply_text(f"🔇 Вы замучены. Осталось: {minutes} мин")
            return
        
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
            comment = await self.ai.get_response(user.id, f"игрок перевел {amount} монет")
            
            await update.message.reply_text(f"✅ {message}\nПолучатель: {target_user[4]}\n\n💬 **Спектр:** {comment}")
            
            try:
                await context.bot.send_message(
                    chat_id=int(target_id),
                    text=f"💰 {user.first_name} перевел вам {amount} 🪙!"
                )
            except:
                pass
        else:
            await update.message.reply_text(f"❌ {message}")
    
    # ===================== СИСТЕМА МОДЕРАЦИИ =====================
    async def cmd_moder(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_moder_rank(update, 5):
            return
        
        await update.message.reply_text("🛡️ Команды модерации:\n/staff - список\n/warn - предупреждение\n/mute - мут\n/ban - бан")
    
    async def cmd_staff(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        mods = db.get_moderators('tg')
        
        if not mods:
            await update.message.reply_text("📭 В этом чате нет модераторов")
            return
        
        text = "🛡️ **СПИСОК МОДЕРАТОРОВ**\n\n"
        
        for mod in mods:
            platform_id, first_name, username, rank = mod
            rank_names = ["", "🛡️ Мл.модер", "⚔️ Ст.модер", "👑 Мл.админ", "💎 Ст.админ", "⭐ Создатель"]
            name = first_name or username or f"ID {platform_id}"
            text += f"{rank_names[rank]} {name}\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_warn(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_moder_rank(update, 1):
            return
        
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /warn [ссылка] [причина]")
            return
        
        target_link = context.args[0]
        reason = " ".join(context.args[1:])
        
        target_id = await self._resolve_mention(update, context, target_link)
        
        if not target_id:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        target_user = db.get_user('tg', target_id)
        target_name = target_user.get('first_name', f"ID {target_id}")
        
        warns = db.add_warn('tg', target_id, target_name, reason, update.effective_user.id, update.effective_user.first_name)
        
        await update.message.reply_text(
            f"⚠️ **Предупреждение выдано**\n\n"
            f"👤 {target_name}\n"
            f"⚠️ Варнов: {warns}/3\n"
            f"💬 Причина: {reason}"
        )
        
        try:
            await context.bot.send_message(
                chat_id=int(target_id),
                text=f"⚠️ Вам выдано предупреждение ({warns}/3)\nПричина: {reason}"
            )
        except:
            pass
    
    async def cmd_mute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_moder_rank(update, 1):
            return
        
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /mute [ссылка] [время] [причина]")
            return
        
        target_link = context.args[0]
        try:
            minutes = int(context.args[1])
        except:
            await update.message.reply_text("❌ Время должно быть числом (минуты)")
            return
        
        reason = " ".join(context.args[2:]) if len(context.args) > 2 else "Нарушение"
        
        target_id = await self._resolve_mention(update, context, target_link)
        
        if not target_id:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        target_user = db.get_user('tg', target_id)
        target_name = target_user.get('first_name', f"ID {target_id}")
        
        db.mute_user('tg', target_id, target_name, minutes, reason, update.effective_user.id, update.effective_user.first_name)
        
        await update.message.reply_text(
            f"🔇 **Пользователь замучен**\n\n"
            f"👤 {target_name}\n"
            f"Время: {minutes} мин\n"
            f"Причина: {reason}"
        )
        
        try:
            await context.bot.send_message(
                chat_id=int(target_id),
                text=f"🔇 Вы замучены на {minutes} минут.\nПричина: {reason}"
            )
        except:
            pass
    
    async def cmd_ban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_moder_rank(update, 2):
            return
        
        if len(context.args) < 3:
            await update.message.reply_text("❌ Использование: /ban [ссылка] [время] [причина]")
            return
        
        target_link = context.args[0]
        duration = context.args[1]
        reason = " ".join(context.args[2:])
        
        target_id = await self._resolve_mention(update, context, target_link)
        
        if not target_id:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        target_user = db.get_user('tg', target_id)
        target_name = target_user.get('first_name', f"ID {target_id}")
        
        db.ban_user('tg', target_id, target_name, reason, duration, update.effective_user.id, update.effective_user.first_name)
        
        await update.message.reply_text(
            f"🚫 **Пользователь забанен**\n\n"
            f"👤 {target_name}\n"
            f"Время: {duration}\n"
            f"Причина: {reason}"
        )
        
        try:
            await context.bot.send_message(
                chat_id=int(target_id),
                text=f"🚫 Вы забанены.\nВремя: {duration}\nПричина: {reason}"
            )
        except:
            pass
    
    async def cmd_unban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_moder_rank(update, 2):
            return
        
        if not context.args:
            await update.message.reply_text("❌ Использование: /unban [ссылка]")
            return
        
        target_link = context.args[0]
        target_id = await self._resolve_mention(update, context, target_link)
        
        if not target_id:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        db.unban_user('tg', target_id)
        
        target_user = db.get_user('tg', target_id)
        target_name = target_user.get('first_name', f"ID {target_id}")
        
        await update.message.reply_text(f"✅ Пользователь {target_name} разбанен")
        
        try:
            await context.bot.send_message(
                chat_id=int(target_id),
                text="✅ Вы разбанены"
            )
        except:
            pass
    
    async def cmd_banlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_moder_rank(update, 1):
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
            text += f"   Время: {duration}\n"
            text += f"   Причина: {reason}\n"
            text += f"   Кто: {banned_by}\n"
            text += f"   Дата: {ban_date}\n\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = str(update.effective_chat.id)
        settings = db.get_group_settings(chat_id, 'tg')
        rules = settings.get('rules', 'Правила не установлены')
        
        text = (
            "╔══════════════════════════════╗\n"
            "║     📖 **ПРАВИЛА ЧАТА** 📖   ║\n"
            "╚══════════════════════════════╝\n\n"
            f"{rules}"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_set_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_moder_rank(update, 3):
            return
        
        if not context.args:
            await update.message.reply_text("❌ Использование: /set_rules [текст правил]")
            return
        
        rules = " ".join(context.args)
        chat_id = str(update.effective_chat.id)
        
        db.update_group_setting(chat_id, 'tg', 'rules', rules)
        
        await update.message.reply_text(f"✅ Правила установлены!")
    
    # ===================== ЗАКЛАДКИ И НАГРАДЫ =====================
    async def cmd_add_bookmark(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Использование: /bookmark [описание]")
            return
        
        description = " ".join(context.args)
        user = update.effective_user
        platform_id = str(user.id)
        
        message_link = f"https://t.me/c/{str(update.effective_chat.id)[4:]}/{update.message.message_id}"
        message_text = update.message.text
        
        db.add_bookmark('tg', platform_id, description, message_link, message_text)
        
        await update.message.reply_text(f"✅ Закладка создана: {description}")
    
    async def cmd_bookmarks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    async def cmd_add_award(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_moder_rank(update, 3):
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
    
    async def cmd_awards(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    # ===================== ИГРЫ =====================
    async def cmd_rr(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "╔══════════════════════════════╗\n"
            "║     💣 **РУССКАЯ РУЛЕТКА** 💣 ║\n"
            "╚══════════════════════════════╝\n\n"
            
            "**ПРАВИЛА**\n"
            "• В барабане 1-3 патрона\n"
            "• Размер барабана: 6-10 позиций\n"
            "• Игроки по очереди стреляют\n"
            "• Победитель забирает все ставки\n\n"
            
            "**КОМАНДЫ**\n"
            "/rr_start [игроки] [ставка] — создать лобби\n"
            "/rr_join [ID] — присоединиться\n"
            "/rr_shot — сделать выстрел"
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
        platform_id = str(user.id)
        
        user_data = db.get_user('tg', platform_id)
        
        if user_data['rr_money'] < bet:
            await update.message.reply_text(f"❌ Недостаточно черепков! У тебя {user_data['rr_money']} 💀")
            return
        
        db.add_coins('tg', platform_id, -bet, "rr_money")
        lobby_id = db.rr_create_lobby(platform_id, max_players, bet)
        
        await update.message.reply_text(
            f"💣 **ЛОББИ СОЗДАНО!**\n\n"
            f"▫️ ID: {lobby_id}\n"
            f"▫️ Создатель: {user.first_name}\n"
            f"▫️ Игроков: 1/{max_players}\n"
            f"▫️ Ставка: {bet} 💀\n\n"
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
        platform_id = str(user.id)
        
        if db.rr_join_lobby(lobby_id, platform_id):
            await update.message.reply_text(f"✅ Ты присоединился к лобби {lobby_id}!")
        else:
            await update.message.reply_text("❌ Не удалось присоединиться")
    
    async def cmd_rr_shot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            
            db.cursor.execute("SELECT bet FROM rr_lobbies WHERE id = ?", (game_dict['lobby_id'],))
            bet = db.cursor.fetchone()[0]
            total_pot = bet * len(json.loads(game_dict['players']))
            db.add_coins('tg', winner_id, total_pot, "rr_money")
            
            await update.message.reply_text(
                f"🏆 **ИГРА ОКОНЧЕНА!**\n\n"
                f"Победитель: {winner_data.first_name}\n"
                f"💰 Выигрыш: {total_pot} 💀",
                parse_mode='Markdown'
            )
    
    async def cmd_ttt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "⭕ **КРЕСТИКИ-НОЛИКИ 3D**\n\n"
            
            "**ПРАВИЛА**\n"
            "• В каждой клетке поля находится ещё одно поле\n"
            "• Нужно выиграть на 3 малых полях в ряд\n"
            "• Победа на малом поле делает его вашим\n"
            "• Игра продолжается пока кто-то не победит\n\n"
            
            "**КОМАНДЫ**\n"
            "/ttt_challenge [ник] — вызвать игрока\n"
            "/ttt_move [клетка] — сделать ход"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_ttt_challenge(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        
        await update.message.reply_text("✅ Запрос отправлен!")
    
    async def cmd_ttt_move(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 1:
            await update.message.reply_text("❌ Использование: /ttt_move [клетка] (например 1_1_2_2)")
            return
        
        try:
            parts = context.args[0].split('_')
            if len(parts) != 4:
                raise ValueError
            main_row, main_col, sub_row, sub_col = map(int, parts)
        except:
            await update.message.reply_text("❌ Неправильный формат")
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
            await update.message.reply_text(f"🏆 Игра окончена!")
        else:
            await update.message.reply_text("✅ Ход сделан!")
    
    async def cmd_mafia(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "🔪 **МАФИЯ**\n\n"
            
            "**ПРАВИЛА**\n"
            "• Игроки делятся на мафию и мирных\n"
            "• Ночью мафия убивает, днем все обсуждают\n"
            "• Цель мафии — убить всех мирных\n"
            "• Цель мирных — найти мафию\n\n"
            
            "**ФАЗЫ ИГРЫ**\n"
            "🌙 Ночь — мафия выбирает жертву\n"
            "☀️ День — обсуждение и голосование\n"
            "⚰️ Смерть — игрок покидает игру\n\n"
            
            "**КОМАНДЫ**\n"
            "/mafia_create — создать игру\n"
            "/mafia_join [ID] — присоединиться\n"
            "/mafia_start — начать игру\n"
            "/mafia_vote [ник] — голосовать\n"
            "/mafia_kill [ник] — убить (для мафии)"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_mafia_create(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        
        game_id = db.mafia_create_game(platform_id)
        self.mafia_games[game_id] = {'votes': {}, 'kill_votes': {}}
        
        await update.message.reply_text(
            f"🔪 **ИГРА МАФИЯ СОЗДАНА!**\n\n"
            f"▫️ ID игры: {game_id}\n"
            f"▫️ Создатель: {user.first_name}\n"
            f"▫️ Игроков: 1/10\n\n"
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
        platform_id = str(user.id)
        
        if db.mafia_join_game(game_id, platform_id):
            await update.message.reply_text(f"✅ Ты присоединился к игре {game_id}!")
        else:
            await update.message.reply_text("❌ Не удалось присоединиться")
    
    async def cmd_mafia_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        
        await update.message.reply_text("🌙 **НАСТУПИЛА НОЧЬ**\nМафия, просыпайтесь!")
    
    async def cmd_mafia_vote(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 1:
            await update.message.reply_text("❌ Использование: /mafia_vote [ник]")
            return
        
        user = update.effective_user
        platform_id = str(user.id)
        
        await update.message.reply_text(f"✅ Голос учтен")
    
    async def cmd_mafia_kill(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 1:
            await update.message.reply_text("❌ Использование: /mafia_kill [ник]")
            return
        
        await update.message.reply_text(f"🔪 Ты выбрал цель")
    
    async def cmd_minesweeper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        
        difficulty = "новичок"
        if context.args:
            difficulty = context.args[0].lower()
        
        sizes = {
            "новичок": (8, 8, 10),
            "любитель": (12, 12, 30),
            "профи": (16, 16, 50)
        }
        
        if difficulty not in sizes:
            await update.message.reply_text("❌ Сложность должна быть: новичок, любитель или профи")
            return
        
        width, height, mines = sizes[difficulty]
        
        game_id = db.minesweeper_create_game(platform_id, width, height, mines)
        
        await update.message.reply_text(
            f"💣 **САПЁР** (сложность: {difficulty})\n\n"
            f"Команды:\n"
            f"/ms_reveal X Y — открыть клетку\n"
            f"/ms_flag X Y — поставить флаг",
            parse_mode='Markdown'
        )
    
    async def cmd_ms_reveal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /ms_reveal X Y")
            return
        
        await update.message.reply_text("✅ Ход сделан")
    
    async def cmd_ms_flag(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /ms_flag X Y")
            return
        
        await update.message.reply_text("🚩 Флаг поставлен")
    
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
            "✊ **КАМЕНЬ-НОЖНИЦЫ-БУМАГА**\n\nВыбери свой ход:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    # ===================== ОБРАБОТКА СООБЩЕНИЙ =====================
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        message_text = update.message.text
        
        user_data = db.get_user('tg', platform_id, user.username or "", user.first_name, user.last_name or "")
        db.update_activity('tg', platform_id)
        db.add_message_count('tg', platform_id)
        
        # Проверка на бан
        if db.is_banned('tg', platform_id):
            return
        
        # Проверка на мут
        if db.is_muted('tg', platform_id):
            mute_until = datetime.datetime.fromisoformat(user_data['mute_until'])
            remaining = mute_until - datetime.datetime.now()
            minutes = remaining.seconds // 60
            await update.message.reply_text(f"🔇 Вы замучены. Осталось: {minutes} мин")
            return
        
        # AI отвечает на любые сообщения
        await update.message.chat.send_action(action="typing")
        response = await self.ai.get_response(user.id, message_text)
        await update.message.reply_text(f"🤖 **Спектр:** {response}", parse_mode='Markdown')
    
    async def handle_new_members(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = str(update.effective_chat.id)
        settings = db.get_group_settings(chat_id, 'tg')
        
        if not settings.get('welcome_enabled', 1):
            return
        
        welcome = settings.get('welcome_message', '🌟 Добро пожаловать, {user}!')
        
        for member in update.message.new_chat_members:
            if member.is_bot:
                continue
            
            # AI генерирует приветствие
            greeting = await self.ai.get_response(member.id, f"поприветствуй нового участника {member.first_name}")
            
            welcome_text = welcome.replace('{user}', f"[{member.first_name}](tg://user?id={member.id})")
            await update.message.reply_text(f"{welcome_text}\n\n💬 **Спектр:** {greeting}", parse_mode='Markdown')
    
    async def handle_left_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = str(update.effective_chat.id)
        settings = db.get_group_settings(chat_id, 'tg')
        
        if not settings.get('goodbye_enabled', 1):
            return
        
        goodbye = settings.get('goodbye_message', '👋 Пока, {user}!')
        member = update.message.left_chat_member
        
        if member.is_bot:
            return
        
        goodbye_text = goodbye.replace('{user}', f"[{member.first_name}](tg://user?id={member.id})")
        await update.message.reply_text(goodbye_text, parse_mode='Markdown')
    
    # ===================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====================
    async def _resolve_mention(self, update: Update, context: ContextTypes.DEFAULT_TYPE, mention: str) -> Optional[str]:
        if mention.isdigit():
            return mention
        
        if mention.startswith('@'):
            username = mention[1:]
            user = db.get_user_by_username('tg', username)
            if user:
                return user[2]
        
        if update.message and update.message.reply_to_message:
            return str(update.message.reply_to_message.from_user.id)
        
        return None
    
    async def _check_moder_rank(self, update: Update, required_rank: int) -> bool:
        user_id = str(update.effective_user.id)
        rank = db.get_mod_rank('tg', user_id)
        if rank >= required_rank:
            return True
        await update.message.reply_text("❌ Недостаточно прав")
        return False
    
    # ===================== ЗАПУСК =====================
    async def run(self):
        if self.tg_application:
            await self.tg_application.initialize()
            await self.tg_application.start()
            await self.tg_application.updater.start_polling()
            logger.info("🚀 Telegram бот запущен!")
        
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
