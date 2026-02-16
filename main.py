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
import math
import io
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Для Telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from telegram.constants import ParseMode

# Для VK
try:
    from vkbottle import API, Bot
    from vkbottle.bot import Message
    from vkbottle_types.events import GroupEventType
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

# ===================== МОЩНЫЙ AI КЛАСС =====================
class PowerfulAI:
    """Мощный AI для генерации всего и вся"""
    
    def __init__(self):
        self.api_token = "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"
        self.contexts = {}
        self.use_api = True
        print("🤖 МОЩНЫЙ AI инициализирован")
        
        # База знаний для разных тем
        self.knowledge_base = {
            "привет": [
                "Привет! Как твои дела?",
                "Здравствуй! Чем могу помочь?",
                "Хай! Рад тебя видеть!",
                "Приветствую! Как настроение?"
            ],
            "пока": [
                "До встречи! Возвращайся скорее!",
                "Пока! Буду ждать новых сообщений!",
                "Удачи! Пиши еще!",
                "Всего хорошего!"
            ],
            "спасибо": [
                "Пожалуйста! Обращайся!",
                "Не за что! Рад помочь!",
                "Всегда пожалуйста!",
                "На здоровье!"
            ],
            "как дела": [
                "Отлично! А у тебя?",
                "Хорошо! Работаю, помогаю людям!",
                "Прекрасно! Спасибо, что спросил!",
                "Нормально, а у тебя как?"
            ],
            "кто ты": [
                "Я Спектр - мощный AI бот с кучей функций!",
                "Я искусственный интеллект, созданный для общения и игр!",
                "Я твой виртуальный помощник с широкими возможностями!",
                "Я бот Спектр, умею играть в игры, общаться и многое другое!"
            ],
            "что делаешь": [
                "Общаюсь с тобой и жду новых команд!",
                "Думаю над ответом и готовлюсь помогать!",
                "Анализирую информацию и отвечаю на вопросы!",
                "Работаю! А ты чем занят?"
            ],
            "помощь": [
                "Я могу: общаться, играть в игры, показывать профили, и многое другое!",
                "Введи /help для полного списка команд!",
                "Я умею играть в мафию, сапёр, русскую рулетку и многое другое!",
                "Спрашивай что хочешь - я отвечу!"
            ],
            "игры": [
                "У меня есть: мафия, сапёр, русская рулетка, крестики-нолики 3D, КНБ!",
                "Хочешь поиграть? Введи /games для выбора!",
                "Я мастер игр! Выбирай любую!",
                "В мафию можно поиграть с друзьями!"
            ],
            "мафия": [
                "Мафия - классическая игра! Создай игру через /mafia_create",
                "В мафию можно играть компанией от 4 человек!",
                "Ночью просыпается мафия, днем голосуем!",
                "Хочешь стать мафией или мирным?"
            ],
            "босс": [
                "Боссы ждут тебя! Используй /boss для начала битвы!",
                "Побеждай боссов и получай награды!",
                "Каждый босс сильнее предыдущего!",
                "Удачи в битве с боссом!"
            ],
            "профиль": [
                "Твой профиль показывает всю статистику! Используй /profile",
                "В профиле видно твои монеты, уровень и достижения!",
                "Прокачивай персонажа и становись сильнее!",
                "Соревнуйся с друзьями в топе!"
            ],
            "погода": [
                "Я не знаю погоду, но могу рассказать интересный факт!",
                "Погода - штука непредсказуемая, как и мои ответы!",
                "Лучше спроси что-нибудь другое!",
                "Зато я знаю курс биткоина!"
            ],
            "любовь": [
                "Любовь - это прекрасно! 💕",
                "В боте можно даже пожениться! Есть команды /marry",
                "Создавай семьи и заводи детей в боте!",
                "Романтика - это круто!"
            ],
            "еда": [
                "Я люблю электричество! А ты что любишь?",
                "Пицца - отличный выбор!",
                "Ммм, вкусно!",
                "А я питаюсь током!"
            ]
        }
        
        # Универсальные ответы
        self.default_responses = [
            "Интересно! Расскажи подробнее!",
            "Понятно. А что еще?",
            "Хм, занятно!",
            "Я тебя слушаю!",
            "Давай поговорим об этом!",
            "Ух ты! Ничего себе!",
            "Круто! А я вот бот!",
            "Забавно!",
            "Я подумаю над этим...",
            "Отлично! Продолжай!",
            "Мне нравится ход твоих мыслей!",
            "А что ты думаешь по этому поводу?",
            "Хорошая мысль!",
            "Согласен с тобой!",
            "Возможно ты прав!"
        ]
    
    async def get_response(self, message: str, user_id: int = 0, context: str = "chat") -> str:
        """Получить ответ от AI на ЛЮБОЕ сообщение"""
        message_lower = message.lower().strip()
        
        # Пробуем получить ответ через API Hugging Face
        api_response = await self._try_api_response(message)
        if api_response:
            return api_response
        
        # Если API не работает - используем мощную локальную базу
        return self._get_smart_response(message_lower)
    
    async def _try_api_response(self, message: str) -> Optional[str]:
        """Попытка получить ответ через Hugging Face API"""
        try:
            API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.1"
            headers = {"Authorization": f"Bearer {self.api_token}"}
            
            prompt = f"<s>[INST] Ты дружелюбный AI бот. Ответь на сообщение пользователя кратко и с эмодзи: {message} [/INST]"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(API_URL, headers=headers, json={
                    "inputs": prompt,
                    "parameters": {
                        "max_new_tokens": 150,
                        "temperature": 0.8,
                        "top_p": 0.95,
                        "do_sample": True
                    }
                }, timeout=15) as resp:
                    
                    if resp.status == 200:
                        result = await resp.json()
                        if isinstance(result, list) and len(result) > 0:
                            text = result[0].get("generated_text", "")
                            response = text.split("[/INST]")[-1] if "[/INST]" in text else text
                            if response and len(response) > 5 and "[" not in response:
                                return response.strip()
                    return None
        except:
            return None
    
    def _get_smart_response(self, message: str) -> str:
        """Умный локальный ответ на основе анализа сообщения"""
        
        # Проверяем ключевые слова в сообщении
        for key, responses in self.knowledge_base.items():
            if key in message:
                return random.choice(responses)
        
        # Анализируем длину сообщения
        words = message.split()
        
        if len(words) == 1:
            # Одно слово
            single_word_responses = [
                f"Интересное слово: {message}!",
                f"{message}? А что это значит?",
                f"Хм, {message}... Расскажи подробнее!",
                f"Я запомню слово {message}!",
                f"Круто! А что еще?"
            ]
            return random.choice(single_word_responses)
        
        elif len(words) == 2:
            # Два слова
            two_word_responses = [
                f"Ты сказал '{message}'. Очень интересно!",
                f"Понял тебя: {message}",
                f"Расскажи побольше о {message}",
                f"Хорошая мысль: {message}",
                f"Я подумаю над твоими словами: {message}"
            ]
            return random.choice(two_word_responses)
        
        elif len(words) <= 5:
            # Короткое предложение
            short_responses = [
                f"Отлично! '{message}' - хорошая мысль!",
                f"Я тебя понял: {message}",
                f"Интересное мнение: {message}",
                f"Согласен с тобой насчет {message}",
                f"Продолжай в том же духе!"
            ]
            return random.choice(short_responses)
        
        else:
            # Длинное сообщение
            long_responses = [
                f"Я внимательно прочитал твое сообщение. Очень содержательно!",
                f"Спасибо за развернутый ответ! Я ценю это.",
                f"Ух ты, сколько текста! Мне нравится твоя активность!",
                f"Отличное сообщение! Давай обсудим это подробнее?",
                f"Я в восторге от твоего сообщения! Продолжай в том же духе!"
            ]
            return random.choice(long_responses)
    
    async def generate_image(self, prompt: str) -> Optional[bytes]:
        """Генерирует изображение по промпту"""
        try:
            API_URL = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-dev"
            headers = {"Authorization": f"Bearer {self.api_token}"}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(API_URL, headers=headers, json={
                    "inputs": prompt
                }, timeout=30) as resp:
                    
                    if resp.status == 200:
                        return await resp.read()
                    return None
        except:
            return None
    
    async def generate_mafia_image(self, phase: str) -> Optional[bytes]:
        """Генерирует изображение для мафии"""
        prompts = {
            "night": "dark night city moonlight mafia game cinematic style",
            "day": "sunny day city morning mafia game investigation style",
            "kill": "dramatic murder scene mafia game dark style",
            "vote": "people voting discussion mafia game day style"
        }
        prompt = prompts.get(phase, prompts["day"])
        return await self.generate_image(prompt)

# ===================== КЛАСС ДЛЯ СОЗДАНИЯ КАРТИНОК =====================
class ImageGenerator:
    """Генерирует красивые картинки для профилей и игр"""
    
    def __init__(self):
        self.width = 800
        self.height = 400
        self.colors = {
            "background": (45, 45, 45),
            "primary": (155, 89, 182),
            "success": (46, 204, 113),
            "warning": (241, 196, 15),
            "error": (231, 76, 60),
            "text": (255, 255, 255),
            "text_secondary": (200, 200, 200)
        }
        print("🎨 Генератор изображений инициализирован")
    
    async def create_profile_image(self, user_data: dict) -> bytes:
        """Создает красивое изображение профиля"""
        img = Image.new('RGB', (self.width, self.height), color=self.colors["background"])
        draw = ImageDraw.Draw(img)
        
        # Рисуем градиент
        for i in range(self.height):
            color = (
                int(self.colors["background"][0] * (1 - i/self.height) + self.colors["primary"][0] * (i/self.height)),
                int(self.colors["background"][1] * (1 - i/self.height) + self.colors["primary"][1] * (i/self.height)),
                int(self.colors["background"][2] * (1 - i/self.height) + self.colors["primary"][2] * (i/self.height))
            )
            draw.line([(0, i), (self.width, i)], fill=color)
        
        # Рисуем рамку
        draw.rectangle([10, 10, self.width-10, self.height-10], outline=self.colors["primary"], width=3)
        
        # Текст профиля
        y = 50
        draw.text((50, y), f"👤 {user_data.get('first_name', 'Игрок')}", fill=self.colors["text"], font=None)
        y += 50
        
        stats = [
            f"🪙 Монеты: {user_data.get('coins', 0):,}",
            f"💎 Алмазы: {user_data.get('diamonds', 0)}",
            f"❤️ Здоровье: {user_data.get('health', 100)}/{user_data.get('max_health', 100)}",
            f"⚔️ Урон: {user_data.get('damage', 10)}",
            f"📊 Уровень: {user_data.get('level', 1)}",
            f"👾 Боссов убито: {user_data.get('boss_kills', 0)}"
        ]
        
        for stat in stats:
            draw.text((70, y), stat, fill=self.colors["text_secondary"], font=None)
            y += 40
        
        # Сохраняем в байты
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        return img_bytes.getvalue()
    
    async def create_activity_chart(self, activity_data: dict) -> bytes:
        """Создает диаграмму активности"""
        img = Image.new('RGB', (600, 300), color=self.colors["background"])
        draw = ImageDraw.Draw(img)
        
        # Получаем данные за последние 7 дней
        today = datetime.datetime.now()
        dates = [(today - datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]
        
        values = [activity_data.get(date, 0) for date in dates]
        max_value = max(values) if values else 1
        
        # Рисуем столбцы
        bar_width = 50
        spacing = 20
        x = 50
        
        days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        
        for i, (value, day) in enumerate(zip(values, days)):
            bar_height = int((value / max_value) * 200) if max_value > 0 else 0
            bar_height = max(bar_height, 10)
            
            # Цвет столбца
            color = self.colors["success"] if value > 0 else self.colors["warning"]
            
            # Рисуем столбец
            draw.rectangle(
                [x, 250 - bar_height, x + bar_width, 250],
                fill=color,
                outline=self.colors["text"],
                width=2
            )
            
            # День недели
            draw.text((x + 15, 260), day, fill=self.colors["text"], font=None)
            
            # Значение
            if value > 0:
                draw.text((x + 15, 210 - bar_height), str(value), fill=self.colors["text"], font=None)
            
            x += bar_width + spacing
        
        # Сохраняем в байты
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        return img_bytes.getvalue()
    
    async def create_mafia_image(self, phase: str, day_count: int = 1, killed: str = None) -> bytes:
        """Создает изображение для мафии"""
        img = Image.new('RGB', (600, 300), color=self.colors["background"])
        draw = ImageDraw.Draw(img)
        
        # Градиент
        for i in range(300):
            if phase == "night":
                color = (20, 20, 40)
            elif phase == "day":
                color = (135, 206, 235)
            else:
                color = (139, 0, 0)
            draw.line([(0, i), (600, i)], fill=color)
        
        # Текст
        if phase == "night":
            draw.text((250, 100), "🌙 НОЧЬ", fill=(255, 255, 255), font=None)
            draw.text((200, 150), f"День {day_count}", fill=(200, 200, 200), font=None)
            draw.text((150, 200), "Мафия просыпается...", fill=(200, 200, 200), font=None)
        elif phase == "day":
            draw.text((250, 100), "☀️ ДЕНЬ", fill=(0, 0, 0), font=None)
            draw.text((200, 150), f"День {day_count}", fill=(50, 50, 50), font=None)
            draw.text((150, 200), "Все обсуждают и голосуют", fill=(50, 50, 50), font=None)
        elif phase == "kill" and killed:
            draw.text((250, 100), "💀 УБИТ", fill=(255, 255, 255), font=None)
            draw.text((200, 150), killed, fill=(255, 200, 200), font=None)
            draw.text((150, 200), "Покойся с миром", fill=(200, 200, 200), font=None)
        
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        return img_bytes.getvalue()

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
                activity_data TEXT DEFAULT '{}'
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
            mod_rank = 5 if (platform == 'tg' and int(platform_id) == OWNER_ID_TG) or (platform == 'vk' and int(platform_id) == OWNER_ID_VK) else 0
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
    
    def update_activity_data(self, platform, platform_id):
        self.cursor.execute("SELECT activity_data FROM users WHERE platform = ? AND platform_id = ?", (platform, platform_id))
        result = self.cursor.fetchone()
        if result and result[0]:
            activity_data = json.loads(result[0])
        else:
            activity_data = {}
        
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        activity_data[today] = activity_data.get(today, 0) + 1
        
        keys = sorted(activity_data.keys(), reverse=True)
        if len(keys) > 30:
            for key in keys[30:]:
                del activity_data[key]
        
        self.cursor.execute("UPDATE users SET activity_data = ? WHERE platform = ? AND platform_id = ?", (json.dumps(activity_data), platform, platform_id))
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
        if int(platform_id) in [OWNER_ID_TG, OWNER_ID_VK]:
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
        
        sub_winner = self.ttt_check_winner(sub_boards[main_row * 3 + main_col])
        if sub_winner:
            main_board[main_row][main_col] = sub_winner
        
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
        
        mafia_count = max(1, len(players) // 3)
        roles_list = ['mafia'] * mafia_count + ['civilian'] * (len(players) - mafia_count)
        random.shuffle(roles_list)
        
        roles_dict = {players[i]: roles_list[i] for i in range(len(players))}
        
        self.cursor.execute('''
            UPDATE mafia_games SET roles = ?, status = 'playing', phase = 'night' WHERE id = ?
        ''', (json.dumps(roles_dict), game_id))
        self.conn.commit()
        
        return roles_dict
    
    def mafia_get_game(self, game_id):
        self.cursor.execute("SELECT * FROM mafia_games WHERE id = ?", (game_id,))
        game = self.cursor.fetchone()
        if game:
            columns = [description[0] for description in self.cursor.description]
            return dict(zip(columns, game))
        return None
    
    def mafia_get_active_game(self, user_id):
        self.cursor.execute(
            "SELECT * FROM mafia_games WHERE players LIKE ? AND status = 'playing'",
            (f'%{user_id}%',)
        )
        return self.cursor.fetchone()
    
    def mafia_next_phase(self, game_id):
        game = self.mafia_get_game(game_id)
        if not game:
            return None
        
        if game['phase'] == 'night':
            self.cursor.execute("UPDATE mafia_games SET phase = 'day', day_count = day_count + 1 WHERE id = ?", (game_id,))
            self.conn.commit()
            return 'day'
        else:
            self.cursor.execute("UPDATE mafia_games SET phase = 'night' WHERE id = ?", (game_id,))
            self.conn.commit()
            return 'night'
    
    def mafia_add_action(self, game_id, player_id, action_type, target_id, round_num):
        self.cursor.execute('''
            INSERT INTO mafia_actions (game_id, player_id, action_type, target_id, round)
            VALUES (?, ?, ?, ?, ?)
        ''', (game_id, player_id, action_type, target_id, round_num))
        self.conn.commit()
    
    def mafia_get_actions(self, game_id, round_num, action_type=None):
        if action_type:
            self.cursor.execute(
                "SELECT * FROM mafia_actions WHERE game_id = ? AND round = ? AND action_type = ?",
                (game_id, round_num, action_type)
            )
        else:
            self.cursor.execute(
                "SELECT * FROM mafia_actions WHERE game_id = ? AND round = ?",
                (game_id, round_num)
            )
        return self.cursor.fetchall()
    
    def mafia_remove_player(self, game_id, player_id):
        game = self.mafia_get_game(game_id)
        if not game:
            return False
        
        players = json.loads(game['players'])
        if player_id in players:
            players.remove(player_id)
            self.cursor.execute("UPDATE mafia_games SET players = ? WHERE id = ?", (json.dumps(players), game_id))
            self.conn.commit()
            
            roles = json.loads(game['roles'])
            alive_mafia = sum(1 for p in players if roles.get(p) == 'mafia')
            alive_civilians = sum(1 for p in players if roles.get(p) != 'mafia')
            
            if alive_mafia == 0:
                return "civilians_win"
            elif alive_mafia >= alive_civilians:
                return "mafia_win"
            elif len(players) == 0:
                return "draw"
        
        return "continue"
    
    # ===================== САПЁР =====================
    def minesweeper_create_game(self, user_id, width=8, height=8, mines=10):
        board = [[0 for _ in range(width)] for _ in range(height)]
        revealed = [[False for _ in range(width)] for _ in range(height)]
        flags = [[False for _ in range(width)] for _ in range(height)]
        
        positions = [(x, y) for x in range(width) for y in range(height)]
        mine_positions = random.sample(positions, mines)
        
        for x, y in mine_positions:
            board[y][x] = -1
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    if dy == 0 and dx == 0:
                        continue
                    ny, nx = y + dy, x + dx
                    if 0 <= nx < width and 0 <= ny < height and board[ny][nx] != -1:
                        board[ny][nx] += 1
        
        self.cursor.execute('''
            INSERT INTO minesweeper_games (user_id, width, height, mines, board, revealed, flags, status, started_at, last_move)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, width, height, mines, json.dumps(board), json.dumps(revealed), json.dumps(flags), 'playing', datetime.datetime.now(), datetime.datetime.now()))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def minesweeper_get_game(self, game_id):
        self.cursor.execute("SELECT * FROM minesweeper_games WHERE id = ?", (game_id,))
        game = self.cursor.fetchone()
        if game:
            columns = [description[0] for description in self.cursor.description]
            return dict(zip(columns, game))
        return None
    
    def minesweeper_reveal(self, game_id, x, y):
        game = self.minesweeper_get_game(game_id)
        if not game or game['status'] != 'playing':
            return None
        
        board = json.loads(game['board'])
        revealed = json.loads(game['revealed'])
        flags = json.loads(game['flags'])
        
        if revealed[y][x] or flags[y][x]:
            return "already_revealed"
        
        if board[y][x] == -1:
            revealed[y][x] = True
            status = 'lost'
            result = "mine"
        else:
            self.minesweeper_flood_fill(board, revealed, x, y)
            status = 'won' if self.minesweeper_check_win(board, revealed) else 'playing'
            result = "safe"
        
        self.cursor.execute('''
            UPDATE minesweeper_games SET revealed = ?, status = ?, last_move = ? WHERE id = ?
        ''', (json.dumps(revealed), status, datetime.datetime.now(), game_id))
        self.conn.commit()
        
        return {
            'status': status,
            'result': result,
            'board': board,
            'revealed': revealed,
            'flags': flags
        }
    
    def minesweeper_flood_fill(self, board, revealed, x, y):
        width = len(board[0])
        height = len(board)
        
        if x < 0 or x >= width or y < 0 or y >= height:
            return
        if revealed[y][x] or board[y][x] == -1:
            return
        
        revealed[y][x] = True
        
        if board[y][x] == 0:
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    if dy == 0 and dx == 0:
                        continue
                    self.minesweeper_flood_fill(board, revealed, x + dx, y + dy)
    
    def minesweeper_toggle_flag(self, game_id, x, y):
        game = self.minesweeper_get_game(game_id)
        if not game or game['status'] != 'playing':
            return None
        
        flags = json.loads(game['flags'])
        revealed = json.loads(game['revealed'])
        
        if revealed[y][x]:
            return "already_revealed"
        
        flags[y][x] = not flags[y][x]
        
        self.cursor.execute('''
            UPDATE minesweeper_games SET flags = ?, last_move = ? WHERE id = ?
        ''', (json.dumps(flags), datetime.datetime.now(), game_id))
        self.conn.commit()
        
        return flags
    
    def minesweeper_check_win(self, board, revealed):
        width = len(board[0])
        height = len(board)
        
        for y in range(height):
            for x in range(width):
                if board[y][x] != -1 and not revealed[y][x]:
                    return False
        return True
    
    def close(self):
        self.conn.close()

# ===================== КОНФИГУРАЦИЯ =====================
# Telegram
TELEGRAM_TOKEN = "8326390250:AAEpXRnhLLLi5zUeFC39nfkHDlxR5ZFQ_yQ"
OWNER_ID_TG = 1732658530
OWNER_USERNAME_TG = "@NobuCraft"

# VK
VK_TOKEN = "vk1.a.sl7q9qebmFwqxkdpMVJTQpLWUtLMsKYPvVInyidaBe1GwkuxkDewfvYss7AcGYPlbw817In-UDgILA38ltHafX3p-t0_xaNWPwXOPpwPezMqq89fx1y9ru6lyde_qFYtu-ll3J-1_vBPPCZ0fHyh4j8qxkiXWCVBgFKtkNhqukNIFTbWqMjX57iMIPbawIdYOr_ngdaXRuGXZAAxzffhbg"
OWNER_ID_VK = 713616259
GROUP_ID_VK = 196406092

# Настройки
SPAM_LIMIT = 5
SPAM_WINDOW = 3
SPAM_MUTE_TIME = 120

# Ранги модераторов
MODER_RANKS = {
    0: "👤 Пользователь",
    1: "🛡️ Младший модератор",
    2: "⚔️ Старший модератор",
    3: "👑 Младший администратор",
    4: "💎 Старший администратор",
    5: "⭐ Создатель"
}

# Привилегии
PRIVILEGES = {
    "вип": {"price": 5000, "days": 30, "emoji": "🌟"},
    "премиум": {"price": 15000, "days": 30, "emoji": "💎"},
    "лорд": {"price": 30000, "days": 30, "emoji": "👑"},
    "ультра": {"price": 50000, "days": 60, "emoji": "⚡"},
    "легенда": {"price": 100000, "days": 90, "emoji": "🏆"},
    "эврольд": {"price": 200000, "days": 180, "emoji": "🌌"},
    "властелин": {"price": 500000, "days": 365, "emoji": "👾"},
    "титан": {"price": 1000000, "days": 365, "emoji": "🗿"},
    "терминатор": {"price": 2000000, "days": 365, "emoji": "🤖"},
    "маг": {"price": 75000, "days": 60, "emoji": "🔮"}
}

# ===================== ИНИЦИАЛИЗАЦИЯ =====================
db = Database()
ai = PowerfulAI()
img_gen = ImageGenerator()

# ===================== ОСНОВНОЙ КЛАСС БОТА =====================
class GameBot:
    def __init__(self):
        self.db = db
        self.ai = ai
        self.img_gen = img_gen
        self.tg_application = None
        self.vk_bot = None
        self.vk_api = None
        self.last_activity = defaultdict(dict)
        self.spam_tracker = defaultdict(list)
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
        self.tg_application.add_handler(CommandHandler("cmd", self.tg_cmd_privilege_commands))
        
        # Система модерации
        self.tg_application.add_handler(CommandHandler("moder", self.tg_cmd_moder))
        self.tg_application.add_handler(CommandHandler("moder2", self.tg_cmd_moder2))
        self.tg_application.add_handler(CommandHandler("moder3", self.tg_cmd_moder3))
        self.tg_application.add_handler(CommandHandler("moder4", self.tg_cmd_moder4))
        self.tg_application.add_handler(CommandHandler("moder5", self.tg_cmd_moder5))
        self.tg_application.add_handler(CommandHandler("promote", self.tg_cmd_promote))
        self.tg_application.add_handler(CommandHandler("demote", self.tg_cmd_demote))
        self.tg_application.add_handler(CommandHandler("remove_moder", self.tg_cmd_remove_moder))
        self.tg_application.add_handler(CommandHandler("staff", self.tg_cmd_staff))
        self.tg_application.add_handler(CommandHandler("who_invited", self.tg_cmd_who_invited))
        
        # Предупреждения
        self.tg_application.add_handler(CommandHandler("warn", self.tg_cmd_warn))
        self.tg_application.add_handler(CommandHandler("warns", self.tg_cmd_warns))
        self.tg_application.add_handler(CommandHandler("my_warns", self.tg_cmd_my_warns))
        self.tg_application.add_handler(CommandHandler("warnlist", self.tg_cmd_warnlist))
        self.tg_application.add_handler(CommandHandler("remove_warn", self.tg_cmd_remove_warn))
        self.tg_application.add_handler(CommandHandler("clear_warns", self.tg_cmd_clear_warns))
        
        # Мут
        self.tg_application.add_handler(CommandHandler("mute", self.tg_cmd_mute))
        self.tg_application.add_handler(CommandHandler("unmute", self.tg_cmd_unmute))
        self.tg_application.add_handler(CommandHandler("mutelist", self.tg_cmd_mutelist))
        self.tg_application.add_handler(CommandHandler("check_mute", self.tg_cmd_check_mute))
        
        # Бан
        self.tg_application.add_handler(CommandHandler("ban", self.tg_cmd_ban))
        self.tg_application.add_handler(CommandHandler("unban", self.tg_cmd_unban))
        self.tg_application.add_handler(CommandHandler("banlist", self.tg_cmd_banlist))
        
        # Правила и настройки
        self.tg_application.add_handler(CommandHandler("rules", self.tg_cmd_rules))
        self.tg_application.add_handler(CommandHandler("set_rules", self.tg_cmd_set_rules))
        self.tg_application.add_handler(CommandHandler("warns_limit", self.tg_cmd_warns_limit))
        self.tg_application.add_handler(CommandHandler("mute_period", self.tg_cmd_mute_period))
        self.tg_application.add_handler(CommandHandler("ban_period", self.tg_cmd_ban_period))
        
        # Русская рулетка
        self.tg_application.add_handler(CommandHandler("rr", self.tg_cmd_rr))
        self.tg_application.add_handler(CommandHandler("rr_start", self.tg_cmd_rr_start))
        self.tg_application.add_handler(CommandHandler("rr_join", self.tg_cmd_rr_join))
        self.tg_application.add_handler(CommandHandler("rr_shot", self.tg_cmd_rr_shot))
        
        # Крестики-нолики 3D
        self.tg_application.add_handler(CommandHandler("ttt", self.tg_cmd_ttt))
        self.tg_application.add_handler(CommandHandler("ttt_challenge", self.tg_cmd_ttt_challenge))
        self.tg_application.add_handler(CommandHandler("ttt_move", self.tg_cmd_ttt_move))
        
        # Мафия
        self.tg_application.add_handler(CommandHandler("mafia", self.tg_cmd_mafia))
        self.tg_application.add_handler(CommandHandler("mafia_create", self.tg_cmd_mafia_create))
        self.tg_application.add_handler(CommandHandler("mafia_join", self.tg_cmd_mafia_join))
        self.tg_application.add_handler(CommandHandler("mafia_start", self.tg_cmd_mafia_start))
        self.tg_application.add_handler(CommandHandler("mafia_vote", self.tg_cmd_mafia_vote))
        self.tg_application.add_handler(CommandHandler("mafia_kill", self.tg_cmd_mafia_kill))
        
        # Сапёр
        self.tg_application.add_handler(CommandHandler("minesweeper", self.tg_cmd_minesweeper))
        self.tg_application.add_handler(CommandHandler("ms_reveal", self.tg_cmd_ms_reveal))
        self.tg_application.add_handler(CommandHandler("ms_flag", self.tg_cmd_ms_flag))
        
        # Камень-ножницы-бумага
        self.tg_application.add_handler(CommandHandler("rps", self.tg_cmd_rps))
        
        # Полезные команды
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
        self.tg_application.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, self.tg_handle_left_member))
        
        logger.info("✅ Telegram обработчики зарегистрированы")
    
    # ===================== TELEGRAM КОМАНДЫ =====================
    async def tg_cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        
        db.get_user('tg', platform_id, user.username or "", user.first_name, user.last_name or "")
        db.update_activity('tg', platform_id)
        
        # AI генерирует приветствие
        greeting = await self.ai.get_response(f"поприветствуй нового пользователя {user.first_name}")
        
        text = f"╔══════════════════════════════╗\n"
        text += f"║     ⚔️ **СПЕКТР БОТ** ⚔️     ║\n"
        text += f"╚══════════════════════════════╝\n\n"
        text += f"🌟 {greeting}\n\n"
        text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += f"        **ОСНОВНЫЕ КОМАНДЫ**\n"
        text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += f"👤 /profile — твой профиль\n"
        text += f"👾 /boss — битва с боссом\n"
        text += f"💰 /shop — магазин\n"
        text += f"💎 /donate — привилегии\n"
        text += f"📊 /top — топ игроков\n"
        text += f"👥 /players — онлайн\n"
        text += f"🛡️ /staff — модераторы\n"
        text += f"📚 /help — все команды\n\n"
        text += f"👑 **Владелец:** {OWNER_USERNAME_TG}\n"
        text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        keyboard = [
            [InlineKeyboardButton("👤 Профиль", callback_data="profile"),
             InlineKeyboardButton("👾 Босс", callback_data="boss")],
            [InlineKeyboardButton("💰 Магазин", callback_data="shop"),
             InlineKeyboardButton("💎 Привилегии", callback_data="donate")],
            [InlineKeyboardButton("📊 Топ", callback_data="top"),
             InlineKeyboardButton("👥 Онлайн", callback_data="players")],
            [InlineKeyboardButton("🛡️ Модерация", callback_data="moderation"),
             InlineKeyboardButton("🎮 Игры", callback_data="games")],
            [InlineKeyboardButton("📚 Команды", callback_data="help"),
             InlineKeyboardButton("📖 Правила", callback_data="rules")]
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
            [InlineKeyboardButton("🛡️ Модерация", callback_data="moderation"),
             InlineKeyboardButton("🎮 Игры", callback_data="games")],
            [InlineKeyboardButton("📚 Команды", callback_data="help"),
             InlineKeyboardButton("📖 Правила", callback_data="rules")],
            [InlineKeyboardButton("📌 Закладки", callback_data="bookmarks_menu"),
             InlineKeyboardButton("🏅 Награды", callback_data="awards_menu")]
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
        
        # AI генерирует помощь
        help_text = await self.ai.get_response("что ты умеешь? расскажи кратко")
        
        text = f"📚 **СПРАВОЧНИК КОМАНД**\n\n"
        text += f"🤖 **AI:** {help_text}\n\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "🔰 **ОСНОВНЫЕ**\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "• /start — запуск бота\n"
        text += "• /menu — главное меню\n"
        text += "• /help — эта справка\n"
        text += "• /profile — твой профиль (с картинкой!)\n"
        text += "• /whoami — информация о себе\n"
        text += "• /top — топ игроков\n"
        text += "• /players — количество игроков\n\n"
        
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "⚔️ **БИТВА С БОССОМ**\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "• /boss — информация о боссе\n"
        text += "• /boss_fight [id] — ударить босса\n"
        text += "• /regen — восстановить здоровье\n\n"
        
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "💰 **ЭКОНОМИКА**\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "• /shop — магазин\n"
        text += "• /donate — привилегии\n"
        text += "• /pay [ник] [сумма] — перевести монеты\n"
        text += "• /cmd [привилегия] — команды доната\n\n"
        
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "🛡️ **МОДЕРАЦИЯ**\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "• /staff — список модераторов\n"
        text += "• /moder [ссылка] — назначить модератором\n"
        text += "• /promote [ссылка] — повысить ранг\n"
        text += "• /demote [ссылка] — понизить ранг\n"
        text += "• /remove_moder [ссылка] — снять модератора\n\n"
        
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "🎮 **ИГРЫ**\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "• /rr — русская рулетка\n"
        text += "• /ttt — крестики-нолики 3D\n"
        text += "• /mafia — мафия (с картинками!)\n"
        text += "• /minesweeper [сложность] — сапёр\n"
        text += "• /rps — камень-ножницы-бумага\n\n"
        
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "📌 **ЗАКЛАДКИ И НАГРАДЫ**\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "• /bookmark [описание] — создать закладку\n"
        text += "• /bookmarks — список закладок\n"
        text += "• /award [ник] [название] — дать награду\n"
        text += "• /awards — список наград\n\n"
        
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "📖 **ПРАВИЛА**\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "• /rules — показать правила\n"
        text += "• /set_rules [текст] — установить правила\n\n"
        
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "ℹ️ **ПОЛЕЗНОЕ**\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "• /info [событие] — правдивость события\n"
        text += "• /holidays — праздники сегодня\n"
        text += "• /fact — случайный факт\n"
        text += "• /wisdom — мудрая цитата\n"
        text += "• /population — население Земли\n"
        text += "• /bitcoin — курс биткоина"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def tg_cmd_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        
        user_data = db.get_user('tg', platform_id, user.username or "", user.first_name, user.last_name or "")
        db.update_activity('tg', platform_id)
        db.update_activity_data('tg', platform_id)
        
        if db.is_banned('tg', platform_id):
            await update.message.reply_text("🚫 **Вы забанены в боте**")
            return
        
        if db.is_muted('tg', platform_id):
            mute_until = datetime.datetime.fromisoformat(user_data['mute_until'])
            remaining = mute_until - datetime.datetime.now()
            minutes = remaining.seconds // 60
            await update.message.reply_text(f"🔇 **Вы замучены**\nОсталось: {minutes} мин")
            return
        
        # Генерируем красивую картинку профиля
        await update.message.chat.send_action(action="upload_photo")
        profile_img = await self.img_gen.create_profile_image(user_data)
        
        # AI комментирует профиль
        comment = await self.ai.get_response(f"посмотри на профиль игрока {user.first_name} с монетами {user_data['coins']} и уровнем {user_data['level']}, напиши короткий комментарий")
        
        caption = f"👤 **Профиль {user.first_name}**\n\n{comment}"
        
        await update.message.reply_photo(
            photo=InputFile(io.BytesIO(profile_img), filename="profile.png"),
            caption=caption,
            parse_mode='Markdown'
        )
    
    async def tg_cmd_whoami(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        
        user_data = db.get_user('tg', platform_id, user.username or "", user.first_name, user.last_name or "")
        db.update_activity_data('tg', platform_id)
        
        mod_rank = user_data.get('mod_rank', 0)
        rank_name = MODER_RANKS.get(mod_rank, "👤 Пользователь")
        
        privilege = user_data.get('privilege', 'user')
        privilege_text = f" | {privilege}" if privilege != 'user' else ""
        
        awards = db.get_awards('tg', platform_id)
        awards_text = ""
        if awards:
            awards_text = "\n🏅 **Награды:**\n"
            for award in awards[:3]:
                awards_text += f"   • {award[3]}\n"
        
        first_seen = "Неизвестно"
        if user_data.get('first_seen'):
            first = datetime.datetime.fromisoformat(user_data['first_seen'])
            delta = datetime.datetime.now() - first
            years = delta.days // 365
            months = (delta.days % 365) // 30
            days = delta.days % 30
            first_seen = f"{first.strftime('%d.%m.%Y')} ({years} г {months} мес {days} дн)"
        
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
        
        # Генерируем диаграмму активности
        activity_data = json.loads(user_data.get('activity_data', '{}'))
        chart_img = await self.img_gen.create_activity_chart(activity_data)
        
        # AI описывает пользователя
        ai_desc = await self.ai.get_response(f"опиши игрока с именем {user.first_name} у него уровень {user_data['level']} и {user_data['coins']} монет")
        
        await update.message.reply_photo(
            photo=InputFile(io.BytesIO(chart_img), filename="activity.png"),
            caption=f"📊 **Активность {user.first_name}**\n\n{ai_desc}",
            parse_mode='Markdown'
        )
    
    async def tg_cmd_top(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        top_coins = db.get_top("coins", 10)
        top_level = db.get_top("level", 10)
        top_boss = db.get_top("boss_kills", 10)
        
        text = "╔══════════════════════════════╗\n"
        text += "║      🏆 **ТОП ИГРОКОВ**      ║\n"
        text += "╚══════════════════════════════╝\n\n"
        
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "💰 **ПО МОНЕТАМ**\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        for i, (username, first_name, value) in enumerate(top_coins, 1):
            name = first_name or username or f"Игрок {i}"
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} {name} — {value:,} 🪙\n"
        
        text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "📊 **ПО УРОВНЮ**\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        for i, (username, first_name, value) in enumerate(top_level, 1):
            name = first_name or username or f"Игрок {i}"
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} {name} — {value} ур.\n"
        
        text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "👾 **ПО УБИЙСТВУ БОССОВ**\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        for i, (username, first_name, value) in enumerate(top_boss, 1):
            name = first_name or username or f"Игрок {i}"
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} {name} — {value} боссов\n"
        
        # AI комментирует топ
        comment = await self.ai.get_response("посмотри на топ игроков, напиши короткое мотивирующее сообщение")
        text += f"\n💬 {comment}"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def tg_cmd_players(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        count = db.get_player_count()
        await update.message.reply_text(f"👥 **Активных игроков:** {count}", parse_mode='Markdown')
    
    # ===================== КОМАНДЫ БОССОВ =====================
    async def tg_cmd_boss(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        
        # AI комментирует битву
        ai_comment = await self.ai.get_response(f"игрок с уроном {player_damage} собирается бить босса {boss['boss_name']} с здоровьем {boss['boss_health']}, что скажешь?")
        
        text = f"╔══════════════════════════════╗\n"
        text += f"║   👾 **БИТВА С БОССОМ** 👾   ║\n"
        text += f"╚══════════════════════════════╝\n\n"
        
        text += f"{boss['boss_emoji']} **{boss['boss_name']}**\n"
        text += f"📊 Уровень: {boss['boss_level']}\n\n"
        
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "**ХАРАКТЕРИСТИКИ БОССА**\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += f"💀 Здоровье: {boss['boss_health']} / {boss['boss_max_health']} HP\n"
        text += f"⚔️ Урон: {boss['boss_damage']} HP\n"
        text += f"💰 Награда: {boss['boss_reward']} 🪙\n\n"
        
        text += "**ТВОИ ХАРАКТЕРИСТИКИ**\n"
        text += f"❤️ Здоровье: {user_data['health']} HP\n"
        text += f"🗡 Урон: {player_damage:.1f} ({user_data['damage']} базовый)\n"
        text += f"📊 Сила: {((player_damage / boss['boss_damage']) * 100):.1f}%\n\n"
        
        text += f"💬 **AI:** {ai_comment}\n\n"
        
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "**ДЕЙСТВИЯ**\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += f"👊 /boss_fight {boss['id']} - ударить босса\n"
        text += f"➕ /regen - восстановить здоровье"
        
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
        
        # AI комментирует результат
        if killed:
            ai_comment = await self.ai.get_response(f"игрок победил босса {boss['boss_name']} и получил награду {boss['boss_reward']} монет, поздравь его")
        else:
            ai_comment = await self.ai.get_response(f"игрок нанес {player_damage} урона боссу {boss['boss_name']}, у босса осталось {health_left} здоровья, подбодри игрока")
        
        text = f"⚔️ **БИТВА С БОССОМ** ⚔️\n\n"
        text += f"**{boss['boss_name']}**\n\n"
        text += f"• **Твой урон:** {player_damage} HP\n"
        text += f"• **Урон босса:** {boss['boss_damage']} HP\n\n"
        
        if killed:
            reward = boss['boss_reward']
            db.add_coins('tg', platform_id, reward, "coins")
            db.add_boss_kill('tg', platform_id)
            db.add_exp('tg', platform_id, boss['boss_level'] * 10)
            
            next_boss = db.get_next_boss()
            
            text += f"🎉 **БОСС ПОВЕРЖЕН!**\n"
            text += f"💰 **Награда:** {reward} 🪙\n"
            text += f"✨ **Опыт:** +{boss['boss_level'] * 10}\n\n"
            
            if next_boss:
                text += f"👾 **Следующий босс:** {next_boss['boss_name']}"
            else:
                text += f"👾 **Все боссы побеждены!** Ожидайте возрождения..."
                db.respawn_bosses()
        else:
            text += f"👾 **Босс еще жив!**\n"
            text += f"💀 **Осталось:** {health_left} HP\n\n"
        
        text += f"💬 **AI:** {ai_comment}"
        
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
            
            # AI комментирует регенерацию
            ai_comment = await self.ai.get_response("игрок восстановил здоровье, скажи что-нибудь приятное")
            
            await update.message.reply_text(
                f"➕ **РЕГЕНЕРАЦИЯ**\n\n"
                f"❤️ Здоровье восстановлено!\n"
                f"Текущее здоровье: {user_data['max_health']}/{user_data['max_health']}\n"
                f"⏱ Следующая регенерация через {cooldown} мин\n\n"
                f"💬 {ai_comment}",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❤️ У тебя уже полное здоровье!")
    
    # ===================== ЭКОНОМИКА =====================
    async def tg_cmd_shop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            "• Зелье здоровья — 50 🪙 (❤️+30)\n"
            "• Большое зелье — 100 🪙 (❤️+70)\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚔️ **ОРУЖИЕ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "• Меч — 200 🪙 (⚔️+10)\n"
            "• Легендарный меч — 500 🪙 (⚔️+30)\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚡ **ЭНЕРГИЯ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "• Энергетик — 30 🪙 (⚡+20)\n"
            "• Батарейка — 80 🪙 (⚡+50)\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "💎 **ВАЛЮТА**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "• Алмаз — 100 🪙 (💎+1)\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🎲 **ПРЕДМЕТЫ ДЛЯ РУЛЕТКИ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "• Монета Демона — 500 🪙\n"
            "• Кровавый Глаз — 300 🪙\n"
            "• Маска Клоуна — 1000 🪙\n\n"
            
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
        
        if db.is_banned('tg', platform_id):
            await update.message.reply_text("🚫 Вы забанены в боте.")
            return
        
        text = "╔══════════════════════════════╗\n"
        text += "║   💎 **ПРИВИЛЕГИИ** 💎     ║\n"
        text += "╚══════════════════════════════╝\n\n"
        
        for priv_name, priv_data in PRIVILEGES.items():
            text += f"{priv_data['emoji']} **{priv_name.upper()}**\n"
            text += f"└ 💰 Цена: {priv_data['price']} 🪙\n"
            text += f"└ 📅 Длительность: {priv_data['days']} дн\n\n"
        
        text += "👑 **АДМИН-ПРИВИЛЕГИИ**\n"
        text += "🛡️ Младший модератор, ⚔️ Старший модератор, 👑 Администратор\n\n"
        text += f"💳 Приобрести: напишите {OWNER_USERNAME_TG}"
        
        # AI добавляет мотивацию
        motivation = await self.ai.get_response("напиши короткое мотивирующее сообщение для покупки привилегий")
        text += f"\n\n💬 {motivation}"
        
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
            # AI поздравляет с переводом
            congrats = await self.ai.get_response(f"игрок перевел {amount} монет, напиши короткое поздравление")
            
            await update.message.reply_text(f"✅ {message}\nПолучатель: {target_user[4]}\n\n💬 {congrats}")
            
            try:
                await context.bot.send_message(
                    chat_id=int(target_id),
                    text=f"💰 {user.first_name} перевел вам {amount} 🪙!\n\n💬 {congrats}"
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
                "/cmd легенда\n"
                "/cmd эврольд\n"
                "/cmd властелин\n"
                "/cmd титан\n"
                "/cmd терминатор\n"
                "/cmd маг"
            )
            return
        
        privilege = context.args[0].lower()
        
        privilege_commands = {
            "вип": ["/regen (кулдаун 3 мин)", "/boss_fight x2"],
            "премиум": ["/regen (кулдаун 1 мин)", "/boss_fight x3", "/heal_all"],
            "лорд": ["/god_mode", "/boss_instant"],
            "ультра": ["/super_attack", "/boss_double"],
            "легенда": ["/legendary_skill"],
            "эврольд": ["/cosmic_power"],
            "властелин": ["/master_control"],
            "титан": ["/titan_strike"],
            "терминатор": ["/terminate"],
            "маг": ["/spell", "/magic_shield"]
        }
        
        if privilege in privilege_commands:
            text = f"**КОМАНДЫ {privilege.upper()}**\n\n"
            for cmd in privilege_commands[privilege]:
                text += f"• {cmd}\n"
        else:
            text = "❌ Неизвестная привилегия"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    # ===================== СИСТЕМА МОДЕРАЦИИ =====================
    async def tg_cmd_moder(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._assign_moder_rank(update, context, 1)
    
    async def tg_cmd_moder2(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._assign_moder_rank(update, context, 2)
    
    async def tg_cmd_moder3(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._assign_moder_rank(update, context, 3)
    
    async def tg_cmd_moder4(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._assign_moder_rank(update, context, 4)
    
    async def tg_cmd_moder5(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._assign_moder_rank(update, context, 5)
    
    async def _assign_moder_rank(self, update: Update, context: ContextTypes.DEFAULT_TYPE, rank: int):
        if not await self._check_moder_rank(update, 5):
            return
        
        if not context.args:
            await update.message.reply_text(f"❌ Использование: /moder{'' if rank == 1 else f'{rank}'} [ссылка]")
            return
        
        target_link = context.args[0]
        target_id = await self._resolve_mention(update, context, target_link)
        
        if not target_id:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        target_user = db.get_user('tg', target_id)
        target_name = target_user.get('first_name', f"ID {target_id}")
        
        db.set_mod_rank('tg', target_id, rank, update.effective_user.id)
        
        await update.message.reply_text(f"✅ {MODER_RANKS[rank]} назначен для {target_name}")
    
    async def tg_cmd_promote(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_moder_rank(update, 5):
            return
        
        if not context.args:
            await update.message.reply_text("❌ Использование: /promote [ссылка]")
            return
        
        target_link = context.args[0]
        target_id = await self._resolve_mention(update, context, target_link)
        
        if not target_id:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        current_rank = db.get_mod_rank('tg', target_id)
        if current_rank >= 5:
            await update.message.reply_text("❌ Нельзя повысить создателя")
            return
        
        new_rank = min(current_rank + 1, 5)
        db.set_mod_rank('tg', target_id, new_rank, update.effective_user.id)
        
        target_user = db.get_user('tg', target_id)
        target_name = target_user.get('first_name', f"ID {target_id}")
        
        await update.message.reply_text(f"✅ {target_name} повышен до {MODER_RANKS[new_rank]}")
    
    async def tg_cmd_demote(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_moder_rank(update, 5):
            return
        
        if not context.args:
            await update.message.reply_text("❌ Использование: /demote [ссылка]")
            return
        
        target_link = context.args[0]
        target_id = await self._resolve_mention(update, context, target_link)
        
        if not target_id:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        current_rank = db.get_mod_rank('tg', target_id)
        if current_rank <= 0:
            await update.message.reply_text("❌ Пользователь не является модератором")
            return
        
        if current_rank >= 5:
            await update.message.reply_text("❌ Нельзя понизить создателя")
            return
        
        new_rank = max(current_rank - 1, 0)
        db.set_mod_rank('tg', target_id, new_rank, update.effective_user.id)
        
        target_user = db.get_user('tg', target_id)
        target_name = target_user.get('first_name', f"ID {target_id}")
        
        rank_name = MODER_RANKS[new_rank] if new_rank > 0 else "👤 Пользователь"
        await update.message.reply_text(f"✅ {target_name} понижен до {rank_name}")
    
    async def tg_cmd_remove_moder(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_moder_rank(update, 5):
            return
        
        if not context.args:
            await update.message.reply_text("❌ Использование: /remove_moder [ссылка]")
            return
        
        target_link = context.args[0]
        target_id = await self._resolve_mention(update, context, target_link)
        
        if not target_id:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        current_rank = db.get_mod_rank('tg', target_id)
        if current_rank <= 0:
            await update.message.reply_text("❌ Пользователь не является модератором")
            return
        
        if current_rank >= 5:
            await update.message.reply_text("❌ Нельзя снять создателя")
            return
        
        db.set_mod_rank('tg', target_id, 0, update.effective_user.id)
        
        target_user = db.get_user('tg', target_id)
        target_name = target_user.get('first_name', f"ID {target_id}")
        
        await update.message.reply_text(f"✅ С {target_name} снят статус модератора")
    
    async def tg_cmd_staff(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        mods = db.get_moderators('tg')
        
        if not mods:
            await update.message.reply_text("📭 В этом чате нет модераторов")
            return
        
        text = "🛡️ **СПИСОК МОДЕРАТОРОВ**\n\n"
        
        for mod in mods:
            platform_id, first_name, username, rank = mod
            status = "🟢"
            name = first_name or username or f"ID {platform_id}"
            text += f"{status} {name} — {MODER_RANKS[rank]}\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def tg_cmd_who_invited(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Использование: /who_invited [ссылка]")
            return
        
        target_link = context.args[0]
        target_id = await self._resolve_mention(update, context, target_link)
        
        if not target_id:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        await update.message.reply_text("ℹ️ Информация о назначении будет доступна в следующем обновлении")
    
    # ===================== ВАРНЫ =====================
    async def tg_cmd_warn(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_moder_rank(update, 1):
            return
        
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /warn [ссылка] [время] [причина]")
            return
        
        target_link = context.args[0]
        duration = context.args[1]
        reason = " ".join(context.args[2:]) if len(context.args) > 2 else "Нарушение"
        
        target_id = await self._resolve_mention(update, context, target_link)
        
        if not target_id:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        target_user = db.get_user('tg', target_id)
        target_name = target_user.get('first_name', f"ID {target_id}")
        
        settings = db.get_group_settings(str(update.effective_chat.id), 'tg')
        warns_limit = settings.get('warns_limit', 3)
        
        days = 30
        match = re.match(r'(\d+)\s*(д|день|дней|дня)', duration.lower())
        if match:
            days = int(match.group(1))
        
        warns = db.add_warn('tg', target_id, target_name, reason, update.effective_user.id, update.effective_user.first_name, days)
        
        await update.message.reply_text(
            f"⚠️ **Предупреждение выдано**\n\n"
            f"👤 {target_name}\n"
            f"⚠️ Варнов: {warns}/{warns_limit}\n"
            f"💬 Причина: {reason}"
        )
        
        if warns >= warns_limit:
            ban_period = settings.get('warns_ban_period', '1 день')
            db.ban_user('tg', target_id, target_name, f"Достигнут лимит предупреждений ({warns})", ban_period, update.effective_user.id, update.effective_user.first_name)
            await update.message.reply_text(f"🚫 Пользователь {target_name} забанен на {ban_period} (достигнут лимит варнов)")
        
        try:
            await context.bot.send_message(
                chat_id=int(target_id),
                text=f"⚠️ Вам выдано предупреждение ({warns}/{warns_limit})\nПричина: {reason}"
            )
        except:
            pass
    
    async def tg_cmd_warns(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Использование: /warns [ссылка]")
            return
        
        target_link = context.args[0]
        target_id = await self._resolve_mention(update, context, target_link)
        
        if not target_id:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        target_user = db.get_user('tg', target_id)
        target_name = target_user.get('first_name', f"ID {target_id}")
        
        warns = db.get_warns('tg', target_id)
        
        if not warns:
            await update.message.reply_text(f"✅ У {target_name} нет предупреждений")
            return
        
        text = f"⚠️ **ПРЕДУПРЕЖДЕНИЯ {target_name.upper()}**\n\n"
        
        for i, warn in enumerate(warns, 1):
            reason = warn[4] or "Не указана"
            warned_by = warn[6] or "Неизвестно"
            warn_date = warn[7][:16] if warn[7] else "Неизвестно"
            text += f"{i}. {reason}\n   👮 {warned_by} — {warn_date}\n\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def tg_cmd_my_warns(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        
        warns = db.get_warns('tg', platform_id)
        
        if not warns:
            await update.message.reply_text("✅ У вас нет предупреждений")
            return
        
        text = f"⚠️ **ВАШИ ПРЕДУПРЕЖДЕНИЯ**\n\n"
        
        for i, warn in enumerate(warns, 1):
            reason = warn[4] or "Не указана"
            warned_by = warn[6] or "Неизвестно"
            warn_date = warn[7][:16] if warn[7] else "Неизвестно"
            text += f"{i}. {reason}\n   👮 {warned_by} — {warn_date}\n\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def tg_cmd_warnlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_moder_rank(update, 1):
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
    
    async def tg_cmd_remove_warn(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_moder_rank(update, 1):
            return
        
        if not context.args:
            await update.message.reply_text("❌ Использование: /remove_warn [ссылка]")
            return
        
        target_link = context.args[0]
        target_id = await self._resolve_mention(update, context, target_link)
        
        if not target_id:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        db.remove_warn('tg', target_id)
        
        target_user = db.get_user('tg', target_id)
        target_name = target_user.get('first_name', f"ID {target_id}")
        
        await update.message.reply_text(f"✅ Последнее предупреждение снято с {target_name}")
    
    async def tg_cmd_clear_warns(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_moder_rank(update, 1):
            return
        
        if not context.args:
            await update.message.reply_text("❌ Использование: /clear_warns [ссылка]")
            return
        
        target_link = context.args[0]
        target_id = await self._resolve_mention(update, context, target_link)
        
        if not target_id:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        warns = db.get_warns('tg', target_id)
        for warn in warns:
            db.remove_warn('tg', target_id, warn[0])
        
        target_user = db.get_user('tg', target_id)
        target_name = target_user.get('first_name', f"ID {target_id}")
        
        await update.message.reply_text(f"✅ Все предупреждения сняты с {target_name}")
    
    # ===================== МУТ =====================
    async def tg_cmd_mute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    async def tg_cmd_unmute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_moder_rank(update, 1):
            return
        
        if not context.args:
            await update.message.reply_text("❌ Использование: /unmute [ссылка]")
            return
        
        target_link = context.args[0]
        target_id = await self._resolve_mention(update, context, target_link)
        
        if not target_id:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        db.unmute_user('tg', target_id)
        
        target_user = db.get_user('tg', target_id)
        target_name = target_user.get('first_name', f"ID {target_id}")
        
        await update.message.reply_text(f"✅ Мут снят с {target_name}")
        
        try:
            await context.bot.send_message(
                chat_id=int(target_id),
                text="✅ Ваш мут снят"
            )
        except:
            pass
    
    async def tg_cmd_mutelist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_moder_rank(update, 1):
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
            text += f"   Время: {duration}\n"
            text += f"   Причина: {reason}\n"
            text += f"   Кто: {muted_by}\n"
            text += f"   Дата: {mute_date}\n\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def tg_cmd_check_mute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Использование: /check_mute [ссылка]")
            return
        
        target_link = context.args[0]
        target_id = await self._resolve_mention(update, context, target_link)
        
        if not target_id:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        if db.is_muted('tg', target_id):
            user_data = db.get_user('tg', target_id)
            mute_until = datetime.datetime.fromisoformat(user_data['mute_until'])
            remaining = mute_until - datetime.datetime.now()
            minutes = remaining.seconds // 60
            await update.message.reply_text(f"🔇 Пользователь замучен. Осталось: {minutes} мин")
        else:
            await update.message.reply_text("✅ Пользователь не замучен")
    
    # ===================== БАН =====================
    async def tg_cmd_ban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    async def tg_cmd_unban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    async def tg_cmd_banlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    # ===================== ПРАВИЛА И НАСТРОЙКИ =====================
    async def tg_cmd_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    async def tg_cmd_set_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_moder_rank(update, 3):
            return
        
        if not context.args:
            await update.message.reply_text("❌ Использование: /set_rules [текст правил]")
            return
        
        rules = " ".join(context.args)
        chat_id = str(update.effective_chat.id)
        
        db.update_group_setting(chat_id, 'tg', 'rules', rules)
        
        await update.message.reply_text(f"✅ Правила установлены!")
    
    async def tg_cmd_warns_limit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_moder_rank(update, 3):
            return
        
        if not context.args:
            await update.message.reply_text("❌ Использование: /warns_limit [число]")
            return
        
        try:
            limit = int(context.args[0])
        except:
            await update.message.reply_text("❌ Введите число")
            return
        
        chat_id = str(update.effective_chat.id)
        db.update_group_setting(chat_id, 'tg', 'warns_limit', limit)
        
        await update.message.reply_text(f"✅ Лимит предупреждений установлен: {limit}")
    
    async def tg_cmd_mute_period(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_moder_rank(update, 3):
            return
        
        if not context.args:
            await update.message.reply_text("❌ Использование: /mute_period [время]")
            return
        
        period = " ".join(context.args)
        chat_id = str(update.effective_chat.id)
        db.update_group_setting(chat_id, 'tg', 'mute_period', period)
        
        await update.message.reply_text(f"✅ Срок мута по умолчанию установлен: {period}")
    
    async def tg_cmd_ban_period(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_moder_rank(update, 3):
            return
        
        if not context.args:
            await update.message.reply_text("❌ Использование: /ban_period [время]")
            return
        
        period = " ".join(context.args)
        chat_id = str(update.effective_chat.id)
        db.update_group_setting(chat_id, 'tg', 'ban_period', period)
        
        await update.message.reply_text(f"✅ Срок бана по умолчанию установлен: {period}")
    
    # ===================== РУССКАЯ РУЛЕТКА =====================
    async def tg_cmd_rr(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "╔══════════════════════════════╗\n"
            "║     💣 **РУССКАЯ РУЛЕТКА** 💣 ║\n"
            "╚══════════════════════════════╝\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**ПРАВИЛА**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "• В барабане 1-3 патрона\n"
            "• Размер барабана: 6-10 позиций\n"
            "• Игроки по очереди стреляют\n"
            "• Победитель забирает все ставки\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**МАГИЧЕСКИЕ ПРЕДМЕТЫ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🪙 Монета Демона — убирает/добавляет патрон\n"
            "👁️ Кровавый Глаз — показывает патроны\n"
            "🔄 Обратный Спин — меняет направление\n"
            "⏳ Песочные часы — пропускает ход\n"
            "🎲 Кубик Судьбы — меняет количество патронов\n"
            "🤡 Маска Клоуна — перезаряжает оружие\n"
            "👁️ Глаз Провидца — показывает текущую позицию\n"
            "🧲 Магнит Пули — сдвигает патроны\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**КОМАНДЫ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/rr_start [игроки] [ставка] — создать лобби\n"
            "/rr_join [ID] — присоединиться\n"
            "/rr_shot — сделать выстрел"
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
        
        db.add_coins('tg', platform_id, -bet, "rr_money")
        lobby_id = db.rr_create_lobby(platform_id, max_players, bet)
        
        await update.message.reply_text(
            f"💣 **ЛОББИ СОЗДАНО!**\n\n"
            f"• **ID:** {lobby_id}\n"
            f"• **Создатель:** {user.first_name}\n"
            f"• **Игроков:** 1/{max_players}\n"
            f"• **Ставка:** {bet} 💀\n\n"
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
            
            db.cursor.execute("SELECT players, max_players, bet FROM rr_lobbies WHERE id = ?", (lobby_id,))
            result = db.cursor.fetchone()
            if result:
                players = json.loads(result[0])
                max_players = result[1]
                
                if len(players) == max_players:
                    game_data = db.rr_start_game(lobby_id)
                    if game_data:
                        game_id, players, cylinder_size, bullets, positions = game_data
                        
                        for player_id in players:
                            try:
                                await context.bot.send_message(
                                    chat_id=int(player_id),
                                    text=f"💣 **ИГРА НАЧАЛАСЬ!**\n\n"
                                         f"Барабан: {cylinder_size} позиций\n"
                                         f"Патронов: {bullets}\n\n"
                                         f"Первый ходит: {players[0]}"
                                )
                            except:
                                pass
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
            
            db.cursor.execute("SELECT bet FROM rr_lobbies WHERE id = ?", (game_dict['lobby_id'],))
            bet = db.cursor.fetchone()[0]
            total_pot = bet * len(json.loads(game_dict['players']))
            db.add_coins('tg', winner_id, total_pot, "rr_money")
            
            # AI поздравляет победителя
            congrats = await self.ai.get_response(f"поздравь игрока {winner_data.first_name} с победой в русской рулетке")
            
            await update.message.reply_text(
                f"🏆 **ИГРА ОКОНЧЕНА!**\n\n"
                f"Победитель: {winner_data.first_name}\n"
                f"💰 Выигрыш: {total_pot} 💀\n\n"
                f"💬 {congrats}",
                parse_mode='Markdown'
            )
    
    # ===================== КРЕСТИКИ-НОЛИКИ 3D =====================
    async def tg_cmd_ttt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "╔══════════════════════════════╗\n"
            "║   ⭕ **КРЕСТИКИ-НОЛИКИ 3D** ⭕ ║\n"
            "╚══════════════════════════════╝\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**ПРАВИЛА**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "• В каждой клетке поля находится ещё одно поле\n"
            "• Нужно выиграть на 3 малых полях в ряд\n"
            "• Победа на малом поле делает его вашим\n"
            "• Игра продолжается пока кто-то не победит\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**КОМАНДЫ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/ttt_challenge [ник] — вызвать игрока\n"
            "/ttt_move [клетка] — сделать ход (клетка: ряд_колонка_подряд_подколонка, например 1_1_2_2)"
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
            "╔══════════════════════════════╗\n"
            "║     🔪 **МАФИЯ** 🔪          ║\n"
            "╚══════════════════════════════╝\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**ПРАВИЛА**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "• Игроки делятся на мафию и мирных\n"
            "• Ночью мафия убивает, днем все обсуждают\n"
            "• Цель мафии — убить всех мирных\n"
            "• Цель мирных — найти мафию\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**ФАЗЫ ИГРЫ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🌙 **Ночь** — мафия выбирает жертву\n"
            "☀️ **День** — обсуждение и голосование\n"
            "⚰️ **Смерть** — игрок покидает игру\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**КОМАНДЫ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/mafia_create — создать игру\n"
            "/mafia_join [ID] — присоединиться\n"
            "/mafia_start — начать игру\n"
            "/mafia_vote [ник] — проголосовать днем\n"
            "/mafia_kill [ник] — убить ночью (для мафии)"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="games_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def tg_cmd_mafia_create(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        
        game_id = db.mafia_create_game(platform_id)
        self.mafia_games[game_id] = {
            'votes': {},
            'kill_votes': {}
        }
        
        await update.message.reply_text(
            f"🔪 **ИГРА МАФИЯ СОЗДАНА!**\n\n"
            f"• **ID игры:** {game_id}\n"
            f"• **Создатель:** {user.first_name}\n"
            f"• **Игроков:** 1/10\n\n"
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
        
        # Генерируем картинки для мафии
        night_img = await self.img_gen.create_mafia_image("night", 1)
        day_img = await self.img_gen.create_mafia_image("day", 1)
        
        for player_id in players:
            role = roles[player_id]
            if role == 'mafia':
                role_text = "🔪 **Мафия**"
                role_desc = "Ты просыпаешься ночью и можешь убивать"
            else:
                role_text = "👨‍🌾 **Мирный житель**"
                role_desc = "Ты просыпаешься днем и ищешь мафию"
            
            try:
                await context.bot.send_photo(
                    chat_id=int(player_id),
                    photo=InputFile(io.BytesIO(night_img), filename="night.png"),
                    caption=f"🌙 **НОЧЬ НАСТУПАЕТ...**\n\nТвоя роль: {role_text}\n{role_desc}"
                )
            except:
                pass
        
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=InputFile(io.BytesIO(night_img), filename="night.png"),
            caption="🌙 **НАСТУПИЛА НОЧЬ**\nМафия просыпается и выбирает жертву.\nИспользуйте: /mafia_kill [ник]"
        )
    
    async def tg_cmd_mafia_vote(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 1:
            await update.message.reply_text("❌ Использование: /mafia_vote [ник]")
            return
        
        user = update.effective_user
        platform_id = str(user.id)
        
        game_data = db.mafia_get_active_game(platform_id)
        if not game_data:
            await update.message.reply_text("❌ Ты не участвуешь в активной игре")
            return
        
        columns = [description[0] for description in db.cursor.description]
        game_dict = dict(zip(columns, game_data))
        
        if game_dict['phase'] != 'day':
            await update.message.reply_text("❌ Сейчас нельзя голосовать (ночь)")
            return
        
        target_name = context.args[0]
        target_user = db.get_user_by_username('tg', target_name)
        
        if not target_user:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        target_id = target_user[2]
        players = json.loads(game_dict['players'])
        
        if target_id not in players:
            await update.message.reply_text("❌ Этот игрок не в игре")
            return
        
        db.mafia_add_action(game_dict['id'], platform_id, 'vote', target_id, game_dict['day_count'])
        
        votes = db.mafia_get_actions(game_dict['id'], game_dict['day_count'], 'vote')
        
        if len(votes) >= len(players):
            vote_count = {}
            for vote in votes:
                target = vote[4]
                vote_count[target] = vote_count.get(target, 0) + 1
            
            max_votes = max(vote_count.values())
            candidates = [p for p, c in vote_count.items() if c == max_votes]
            
            if len(candidates) == 1:
                killed_id = candidates[0]
                killed_user = db.get_user('tg', killed_id)
                killed_name = killed_user.get('first_name', f"ID {killed_id}")
                
                result = db.mafia_remove_player(game_dict['id'], killed_id)
                
                # Генерируем картинку убийства
                kill_img = await self.img_gen.create_mafia_image("kill", game_dict['day_count'], killed_name)
                
                if result == "civilians_win":
                    for player_id in players:
                        if player_id != killed_id:
                            try:
                                await context.bot.send_photo(
                                    chat_id=int(player_id),
                                    photo=InputFile(io.BytesIO(kill_img), filename="win.png"),
                                    caption="🏆 **ИГРА ОКОНЧЕНА!**\n\n👨‍🌾 **Мирные жители победили!**"
                                )
                            except:
                                pass
                    return
                elif result == "mafia_win":
                    for player_id in players:
                        if player_id != killed_id:
                            try:
                                await context.bot.send_photo(
                                    chat_id=int(player_id),
                                    photo=InputFile(io.BytesIO(kill_img), filename="win.png"),
                                    caption="🏆 **ИГРА ОКОНЧЕНА!**\n\n🔪 **Мафия победила!**"
                                )
                            except:
                                pass
                    return
                
                db.mafia_next_phase(game_dict['id'])
                
                day_img = await self.img_gen.create_mafia_image("day", game_dict['day_count'] + 1)
                
                for player_id in players:
                    if player_id != killed_id:
                        try:
                            await context.bot.send_photo(
                                chat_id=int(player_id),
                                photo=InputFile(io.BytesIO(day_img), filename="day.png"),
                                caption=f"☀️ **НАСТУПИЛО УТРО**\n\nНочью был убит: {killed_name}\n\nОбсудите и голосуйте!"
                            )
                        except:
                            pass
                
                await update.message.reply_text(
                    f"💀 **ИТОГИ НОЧИ**\n\n"
                    f"Мафия убила: {killed_name}\n\n"
                    f"☀️ **НАСТУПАЕТ ДЕНЬ**"
                )
            else:
                await update.message.reply_text("🔄 Ничья в голосовании. Никто не казнен.")
                db.mafia_next_phase(game_dict['id'])
        
        await update.message.reply_text(f"✅ Голос учтен")
    
    async def tg_cmd_mafia_kill(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 1:
            await update.message.reply_text("❌ Использование: /mafia_kill [ник]")
            return
        
        user = update.effective_user
        platform_id = str(user.id)
        
        game_data = db.mafia_get_active_game(platform_id)
        if not game_data:
            await update.message.reply_text("❌ Ты не участвуешь в активной игре")
            return
        
        columns = [description[0] for description in db.cursor.description]
        game_dict = dict(zip(columns, game_data))
        
        if game_dict['phase'] != 'night':
            await update.message.reply_text("❌ Сейчас нельзя убивать (день)")
            return
        
        roles = json.loads(game_dict['roles'])
        if roles.get(platform_id) != 'mafia':
            await update.message.reply_text("❌ Только мафия может убивать ночью")
            return
        
        target_name = context.args[0]
        target_user = db.get_user_by_username('tg', target_name)
        
        if not target_user:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        target_id = target_user[2]
        players = json.loads(game_dict['players'])
        
        if target_id not in players:
            await update.message.reply_text("❌ Этот игрок не в игре")
            return
        
        db.mafia_add_action(game_dict['id'], platform_id, 'kill', target_id, game_dict['day_count'])
        
        mafia_count = sum(1 for r in roles.values() if r == 'mafia')
        kills = db.mafia_get_actions(game_dict['id'], game_dict['day_count'], 'kill')
        
        if len(kills) >= mafia_count:
            kill_count = {}
            for kill in kills:
                target = kill[4]
                kill_count[target] = kill_count.get(target, 0) + 1
            
            killed_id = max(kill_count.items(), key=lambda x: x[1])[0]
            killed_user = db.get_user('tg', killed_id)
            killed_name = killed_user.get('first_name', f"ID {killed_id}")
            
            result = db.mafia_remove_player(game_dict['id'], killed_id)
            
            if result == "civilians_win":
                win_img = await self.img_gen.create_mafia_image("day", game_dict['day_count'])
                for player_id in players:
                    if player_id != killed_id:
                        try:
                            await context.bot.send_photo(
                                chat_id=int(player_id),
                                photo=InputFile(io.BytesIO(win_img), filename="win.png"),
                                caption="🏆 **ИГРА ОКОНЧЕНА!**\n\n👨‍🌾 **Мирные жители победили!**"
                            )
                        except:
                            pass
                return
            elif result == "mafia_win":
                win_img = await self.img_gen.create_mafia_image("day", game_dict['day_count'])
                for player_id in players:
                    if player_id != killed_id:
                        try:
                            await context.bot.send_photo(
                                chat_id=int(player_id),
                                photo=InputFile(io.BytesIO(win_img), filename="win.png"),
                                caption="🏆 **ИГРА ОКОНЧЕНА!**\n\n🔪 **Мафия победила!**"
                            )
                        except:
                            pass
                return
            elif result == "continue":
                db.mafia_next_phase(game_dict['id'])
                
                day_img = await self.img_gen.create_mafia_image("day", game_dict['day_count'] + 1)
                
                for player_id in players:
                    if player_id != killed_id:
                        try:
                            await context.bot.send_photo(
                                chat_id=int(player_id),
                                photo=InputFile(io.BytesIO(day_img), filename="day.png"),
                                caption=f"☀️ **НАСТУПИЛО УТРО**\n\nНочью был убит: {killed_name}\n\nОбсудите и голосуйте!"
                            )
                        except:
                            pass
                
                await update.message.reply_text(
                    f"💀 **ИТОГИ НОЧИ**\n\n"
                    f"Мафия убила: {killed_name}\n\n"
                    f"☀️ **НАСТУПАЕТ ДЕНЬ**"
                )
        
        await update.message.reply_text(f"🔪 Ты выбрал цель: {target_name}")
    
    # ===================== САПЁР =====================
    async def tg_cmd_minesweeper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        
        board_display = self._format_minesweeper_board(game_id, width, height)
        
        await update.message.reply_text(
            f"💣 **САПЁР** (сложность: {difficulty})\n\n"
            f"{board_display}\n\n"
            f"Команды:\n"
            f"/ms_reveal X Y — открыть клетку\n"
            f"/ms_flag X Y — поставить флаг",
            parse_mode='Markdown'
        )
    
    def _format_minesweeper_board(self, game_id, width, height):
        game = db.minesweeper_get_game(game_id)
        if not game:
            return "Игра не найдена"
        
        revealed = json.loads(game['revealed'])
        flags = json.loads(game['flags'])
        status = game['status']
        
        if status == 'lost':
            board = json.loads(game['board'])
        
        header = "   " + " ".join([f"{i:2}" for i in range(width)]) + "\n"
        board_display = header
        
        for y in range(height):
            row = f"{y:2} "
            for x in range(width):
                if flags[y][x]:
                    row += "🚩 "
                elif revealed[y][x]:
                    if status == 'lost' and board[y][x] == -1:
                        row += "💣 "
                    elif board[y][x] == 0:
                        row += "⬜ "
                    else:
                        row += f"{board[y][x]}  "
                else:
                    row += "⬛ "
            board_display += row + "\n"
        
        return board_display
    
    async def tg_cmd_ms_reveal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /ms_reveal X Y")
            return
        
        try:
            x = int(context.args[0])
            y = int(context.args[1])
        except:
            await update.message.reply_text("❌ Координаты должны быть числами")
            return
        
        user = update.effective_user
        platform_id = str(user.id)
        
        db.cursor.execute(
            "SELECT * FROM minesweeper_games WHERE user_id = ? AND status = 'playing' ORDER BY last_move DESC LIMIT 1",
            (platform_id,)
        )
        game = db.cursor.fetchone()
        
        if not game:
            await update.message.reply_text("❌ У тебя нет активной игры. Начни новую через /minesweeper")
            return
        
        columns = [description[0] for description in db.cursor.description]
        game_dict = dict(zip(columns, game))
        
        result = db.minesweeper_reveal(game_dict['id'], x, y)
        
        if result == "already_revealed":
            await update.message.reply_text("❌ Эта клетка уже открыта или помечена флагом")
            return
        
        board_display = self._format_minesweeper_board(game_dict['id'], game_dict['width'], game_dict['height'])
        
        if result['status'] == 'lost':
            await update.message.reply_text(
                f"💥 **Ты проиграл!**\n\n{board_display}",
                parse_mode='Markdown'
            )
        elif result['status'] == 'won':
            db.cursor.execute("UPDATE users SET minesweeper_wins = minesweeper_wins + 1, minesweeper_games = minesweeper_games + 1 WHERE platform = ? AND platform_id = ?", ('tg', platform_id))
            db.conn.commit()
            await update.message.reply_text(
                f"🏆 **ПОБЕДА!**\n\n{board_display}",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"✅ Ход сделан\n\n{board_display}",
                parse_mode='Markdown'
            )
    
    async def tg_cmd_ms_flag(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /ms_flag X Y")
            return
        
        try:
            x = int(context.args[0])
            y = int(context.args[1])
        except:
            await update.message.reply_text("❌ Координаты должны быть числами")
            return
        
        user = update.effective_user
        platform_id = str(user.id)
        
        db.cursor.execute(
            "SELECT * FROM minesweeper_games WHERE user_id = ? AND status = 'playing' ORDER BY last_move DESC LIMIT 1",
            (platform_id,)
        )
        game = db.cursor.fetchone()
        
        if not game:
            await update.message.reply_text("❌ У тебя нет активной игры. Начни новую через /minesweeper")
            return
        
        columns = [description[0] for description in db.cursor.description]
        game_dict = dict(zip(columns, game))
        
        result = db.minesweeper_toggle_flag(game_dict['id'], x, y)
        
        if result == "already_revealed":
            await update.message.reply_text("❌ Нельзя поставить флаг на открытую клетку")
            return
        
        board_display = self._format_minesweeper_board(game_dict['id'], game_dict['width'], game_dict['height'])
        await update.message.reply_text(f"🚩 Флаг обновлен\n\n{board_display}", parse_mode='Markdown')
    
    # ===================== КАМЕНЬ-НОЖНИЦЫ-БУМАГА =====================
    async def tg_cmd_rps(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [
                InlineKeyboardButton("🪨 Камень", callback_data="rps_rock"),
                InlineKeyboardButton("✂️ Ножницы", callback_data="rps_scissors"),
                InlineKeyboardButton("📄 Бумага", callback_data="rps_paper")
            ],
            [InlineKeyboardButton("🔙 Назад", callback_data="games_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "✊ **КАМЕНЬ-НОЖНИЦЫ-БУМАГА**\n\n"
            "Выбери свой ход:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    # ===================== ПОЛЕЗНЫЕ КОМАНДЫ =====================
    async def tg_cmd_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Использование: /info [событие]")
            return
        
        event = " ".join(context.args)
        
        # AI генерирует ответ
        response = await self.ai.get_response(f"оцени правдивость события: {event}")
        await update.message.reply_text(f"📊 **ПРАВДИВОСТЬ СОБЫТИЯ**\n\n{response}", parse_mode='Markdown')
    
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
            text = f"📅 **Сегодня:** {holidays[date_key]}"
        else:
            # AI генерирует сообщение
            text = await self.ai.get_response("какой сегодня праздник?")
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def tg_cmd_fact(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # AI генерирует факт
        fact = await self.ai.get_response("расскажи интересный факт")
        await update.message.reply_text(f"📌 **СЛУЧАЙНЫЙ ФАКТ**\n\n{fact}", parse_mode='Markdown')
    
    async def tg_cmd_wisdom(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # AI генерирует цитату
        quote = await self.ai.get_response("скажи мудрую цитату")
        await update.message.reply_text(f"💭 **МУДРАЯ МЫСЛЬ**\n\n{quote}", parse_mode='Markdown')
    
    async def tg_cmd_population(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        world_pop = 7_900_000_000
        
        # AI комментирует
        comment = await self.ai.get_response("напиши что-нибудь о населении Земли")
        
        await update.message.reply_text(
            f"🌍 **НАСЕЛЕНИЕ ЗЕМЛИ**\n\n"
            f"👥 Примерно: {world_pop:,} человек\n\n"
            f"💬 {comment}",
            parse_mode='Markdown'
        )
    
    async def tg_cmd_bitcoin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        price_usd = random.randint(40000, 70000)
        price_rub = price_usd * 91.5
        
        # AI комментирует курс
        comment = await self.ai.get_response(f"курс биткоина {price_usd}$")
        
        await update.message.reply_text(
            f"₿ **КУРС БИТКОИНА**\n\n"
            f"USD: ${price_usd:,}\n"
            f"RUB: ₽{int(price_rub):,}\n\n"
            f"💬 {comment}",
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
        message_text = update.message.text
        
        db.add_bookmark('tg', platform_id, description, message_link, message_text)
        
        # AI подтверждает
        response = await self.ai.get_response(f"подтверди создание закладки {description}")
        
        await update.message.reply_text(f"✅ **ЗАКЛАДКА**\n\n{response}", parse_mode='Markdown')
    
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
        
        # AI поздравляет
        congrats = await self.ai.get_response(f"поздравь с наградой {award_name}")
        
        await update.message.reply_text(f"🏅 **НАГРАДА**\n\n{congrats}", parse_mode='Markdown')
        
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
            text += f"• **{award[3]}** — от {award[5]} ({award_date})\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    # ===================== ОБРАБОТКА СООБЩЕНИЙ =====================
    async def tg_handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        platform_id = str(user.id)
        message_text = update.message.text
        
        user_data = db.get_user('tg', platform_id, user.username or "", user.first_name, user.last_name or "")
        db.update_activity('tg', platform_id)
        db.add_message_count('tg', platform_id)
        db.update_activity_data('tg', platform_id)
        
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
        
        # 🤖 AI ОТВЕТЫ НА ЛЮБЫЕ СООБЩЕНИЯ (кроме команд)
        if not message_text.startswith('/'):
            await update.message.chat.send_action(action="typing")
            response = await self.ai.get_response(message_text, user.id)
            await update.message.reply_text(f"🤖 **AI:** {response}", parse_mode='Markdown')
            return
        
        # Проверка на длительное молчание
        last_msg_time = self.last_activity['tg'].get(platform_id, 0)
        current_time = time.time()
        
        if last_msg_time > 0 and current_time - last_msg_time > 30 * 24 * 3600:
            await update.message.reply_text(
                f"⚡️⚡️⚡️ **Святые угодники!**\n\n"
                f"{user.first_name} заговорил после более, чем месячного молчания!!!\n"
                f"Поприветствуйте молчуна! 👏"
            )
        
        self.last_activity['tg'][platform_id] = current_time
        
        # Приветствие для новых
        if user_data['messages_count'] == 1:
            await update.message.reply_text(f"🌟 Добро пожаловать, {user.first_name}! Используй /help для списка команд.")
    
    async def tg_handle_new_members(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = str(update.effective_chat.id)
        settings = db.get_group_settings(chat_id, 'tg')
        
        if not settings.get('welcome_enabled', 1):
            return
        
        welcome = settings.get('welcome_message', '🌟 Добро пожаловать, {user}!')
        
        for member in update.message.new_chat_members:
            if member.is_bot:
                continue
            
            # AI генерирует приветствие
            greeting = await self.ai.get_response(f"поприветствуй нового участника {member.first_name}")
            
            welcome_text = f"🌟 **Новый участник!**\n\n{greeting}"
            await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    async def tg_handle_left_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = str(update.effective_chat.id)
        settings = db.get_group_settings(chat_id, 'tg')
        
        if not settings.get('goodbye_enabled', 1):
            return
        
        member = update.message.left_chat_member
        
        if member.is_bot:
            return
        
        # AI генерирует прощание
        goodbye = await self.ai.get_response(f"попрощайся с участником {member.first_name}")
        
        await update.message.reply_text(f"👋 **Участник покинул чат**\n\n{goodbye}", parse_mode='Markdown')
    
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
        elif data == "moderation":
            keyboard = [
                [InlineKeyboardButton("🛡️ Модераторы", callback_data="staff"),
                 InlineKeyboardButton("⚠️ Варны", callback_data="warn_menu")],
                [InlineKeyboardButton("🔇 Муты", callback_data="mutelist"),
                 InlineKeyboardButton("🚫 Баны", callback_data="banlist")],
                [InlineKeyboardButton("📖 Правила", callback_data="rules"),
                 InlineKeyboardButton("🔙 Назад", callback_data="menu_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "🛡️ **МОДЕРАЦИЯ**\n\nВыберите раздел:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        elif data == "games":
            keyboard = [
                [InlineKeyboardButton("💣 Русская рулетка", callback_data="rr"),
                 InlineKeyboardButton("⭕ Крестики-нолики 3D", callback_data="ttt")],
                [InlineKeyboardButton("🔪 Мафия", callback_data="mafia"),
                 InlineKeyboardButton("💥 Сапёр", callback_data="minesweeper")],
                [InlineKeyboardButton("✊ КНБ", callback_data="rps"),
                 InlineKeyboardButton("🔙 Назад", callback_data="menu_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "🎮 **ИГРЫ**\n\nВыберите игру:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        elif data == "bookmarks_menu":
            await self.tg_cmd_bookmarks(update, context)
        elif data == "awards_menu":
            await self.tg_cmd_awards(update, context)
        elif data == "staff":
            await self.tg_cmd_staff(update, context)
        elif data == "warn_menu":
            keyboard = [
                [InlineKeyboardButton("📋 Список варнов", callback_data="warnlist"),
                 InlineKeyboardButton("👤 Мои варны", callback_data="my_warns")],
                [InlineKeyboardButton("🔙 Назад", callback_data="moderation")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "⚠️ **ПРЕДУПРЕЖДЕНИЯ**\n\nВыберите действие:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        elif data == "warnlist":
            context.args = []
            await self.tg_cmd_warnlist(update, context)
        elif data == "my_warns":
            await self.tg_cmd_my_warns(update, context)
        elif data == "mutelist":
            context.args = []
            await self.tg_cmd_mutelist(update, context)
        elif data == "banlist":
            context.args = []
            await self.tg_cmd_banlist(update, context)
        
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
                "• Зелье здоровья — 50 🪙 (❤️+30)\n"
                "• Большое зелье — 100 🪙 (❤️+70)\n\n"
                "Купить: /buy [название]"
            )
        elif data == "buy_weapons":
            await query.edit_message_text(
                "⚔️ **ОРУЖИЕ**\n\n"
                "• Меч — 200 🪙 (⚔️+10)\n"
                "• Легендарный меч — 500 🪙 (⚔️+30)\n\n"
                "Купить: /buy [название]"
            )
        elif data == "buy_energy":
            await query.edit_message_text(
                "⚡ **ЭНЕРГИЯ**\n\n"
                "• Энергетик — 30 🪙 (⚡+20)\n"
                "• Батарейка — 80 🪙 (⚡+50)\n\n"
                "Купить: /buy [название]"
            )
        elif data == "buy_diamonds":
            await query.edit_message_text(
                "💎 **АЛМАЗЫ**\n\n"
                "• Алмаз — 100 🪙 (💎+1)\n\n"
                "Купить: /buy алмаз"
            )
        elif data == "buy_rr_items":
            await query.edit_message_text(
                "🎲 **ПРЕДМЕТЫ ДЛЯ РУЛЕТКИ**\n\n"
                "• Монета Демона — 500 🪙\n"
                "• Кровавый Глаз — 300 🪙\n"
                "• Маска Клоуна — 1000 🪙\n\n"
                "Купить: /buy [название]"
            )
        
        # Игры
        elif data == "rr":
            await self.tg_cmd_rr(update, context)
        elif data == "ttt":
            await self.tg_cmd_ttt(update, context)
        elif data == "mafia":
            await self.tg_cmd_mafia(update, context)
        elif data == "minesweeper":
            context.args = ["новичок"]
            await self.tg_cmd_minesweeper(update, context)
        elif data == "rps":
            await self.tg_cmd_rps(update, context)
        elif data == "rr_create":
            await query.edit_message_text(
                "💣 **СОЗДАНИЕ ИГРЫ**\n\n"
                "Используй команду:\n"
                "/rr_start [игроки] [ставка]\n\n"
                "Пример: /rr_start 4 100"
            )
        
        # Крестики-нолики
        elif data.startswith("ttt_accept_"):
            game_id = int(data.split("_")[2])
            await query.edit_message_text("✅ Ты принял вызов! Игра начинается...")
        elif data.startswith("ttt_decline_"):
            await query.edit_message_text("❌ Ты отклонил вызов")
        
        # КНБ
        elif data.startswith("rps_"):
            user_choice = data.split("_")[1]
            bot_choice = random.choice(["rock", "scissors", "paper"])
            
            choices = {"rock": "🪨 Камень", "scissors": "✂️ Ножницы", "paper": "📄 Бумага"}
            
            result_map = {
                ("rock", "scissors"): "win", ("rock", "paper"): "lose",
                ("scissors", "paper"): "win", ("scissors", "rock"): "lose",
                ("paper", "rock"): "win", ("paper", "scissors"): "lose"
            }
            
            if user_choice == bot_choice:
                db.cursor.execute("UPDATE users SET rps_draws = rps_draws + 1 WHERE platform = ? AND platform_id = ?", ('tg', str(update.effective_user.id)))
                text = f"{choices[user_choice]} vs {choices[bot_choice]}\n\n🤝 **Ничья!**"
            else:
                result = result_map.get((user_choice, bot_choice), "lose")
                if result == "win":
                    db.cursor.execute("UPDATE users SET rps_wins = rps_wins + 1 WHERE platform = ? AND platform_id = ?", ('tg', str(update.effective_user.id)))
                    text = f"{choices[user_choice]} vs {choices[bot_choice]}\n\n🎉 **Ты выиграл!**"
                else:
                    db.cursor.execute("UPDATE users SET rps_losses = rps_losses + 1 WHERE platform = ? AND platform_id = ?", ('tg', str(update.effective_user.id)))
                    text = f"{choices[user_choice]} vs {choices[bot_choice]}\n\n😢 **Ты проиграл!**"
            
            db.conn.commit()
            
            # AI комментирует результат
            comment = await self.ai.get_response(f"игрок {update.effective_user.first_name} сыграл в КНБ и {'выиграл' if result == 'win' else 'проиграл' if result == 'lose' else 'сыграл вничью'}")
            
            text += f"\n\n💬 {comment}"
            
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="games")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
        # Навигация
        elif data == "menu_back":
            keyboard = [
                [InlineKeyboardButton("👤 Профиль", callback_data="profile"),
                 InlineKeyboardButton("👾 Босс", callback_data="boss")],
                [InlineKeyboardButton("💰 Магазин", callback_data="shop"),
                 InlineKeyboardButton("💎 Привилегии", callback_data="donate")],
                [InlineKeyboardButton("📊 Топ", callback_data="top"),
                 InlineKeyboardButton("👥 Онлайн", callback_data="players")],
                [InlineKeyboardButton("🛡️ Модерация", callback_data="moderation"),
                 InlineKeyboardButton("🎮 Игры", callback_data="games")],
                [InlineKeyboardButton("📚 Команды", callback_data="help"),
                 InlineKeyboardButton("📖 Правила", callback_data="rules")],
                [InlineKeyboardButton("📌 Закладки", callback_data="bookmarks_menu"),
                 InlineKeyboardButton("🏅 Награды", callback_data="awards_menu")]
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
                 InlineKeyboardButton("💥 Сапёр", callback_data="minesweeper")],
                [InlineKeyboardButton("✊ КНБ", callback_data="rps"),
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
        if not VKBOTTLE_AVAILABLE or not self.vk_bot:
            return
        
        @self.vk_bot.on.message()
        async def vk_message_handler(message: Message):
            await self.vk_handle_message(message)
        
        logger.info("✅ VK обработчики зарегистрированы")
    
    async def vk_handle_message(self, message: Message):
        if message.text and message.text.startswith('/start'):
            await message.reply(
                "👋 Привет! Я бот Спектр. Полная поддержка VK будет добавлена позже."
            )
    
    # ===================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====================
    async def _resolve_mention(self, update: Update, context: ContextTypes.DEFAULT_TYPE, mention: str) -> Optional[str]:
        """Преобразует упоминание в ID пользователя"""
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
        """Проверяет, имеет ли пользователь достаточный ранг"""
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
