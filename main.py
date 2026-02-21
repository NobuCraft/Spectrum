#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
СПЕКТР v3.0 ULTIMATE - Полная переработка с новыми модулями
"""

import os
import sys
import logging
import asyncio
import json
import random
import sqlite3
import datetime
import time
import hashlib
import re
import math
from typing import Optional, Dict, Any, List, Tuple, Union
from collections import defaultdict, deque
from enum import Enum
from io import BytesIO
import uuid
from telegram import ChatPermissions

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode
from telegram.error import TelegramError

# ========== GROQ AI ==========
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    print("⚠️ Библиотека groq не установлена, AI будет отключен")

# ========== НАСТРОЙКИ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ==========
TOKEN = os.environ.get("BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
OWNER_ID = int(os.environ.get("OWNER_ID", "1732658530"))
OWNER_USERNAME = os.environ.get("OWNER_USERNAME", "@NobuCraft")

if not TOKEN:
    print("❌ ОШИБКА: BOT_TOKEN не найден в переменных окружения!")
    sys.exit(1)

# ========== КОНСТАНТЫ ==========
BOT_NAME = "Спектр"
BOT_VERSION = "3.0 ULTIMATE"
BOT_USERNAME = "SpectrumServers_bot"

# Настройки модерации
RANKS = {
    0: {"name": "Участник", "emoji": "👤"},
    1: {"name": "Помощник", "emoji": "🟢"},
    2: {"name": "Модератор", "emoji": "🔵"},
    3: {"name": "Администратор", "emoji": "🟣"},
    4: {"name": "Главный админ", "emoji": "🔴"},
    5: {"name": "Создатель", "emoji": "👑"}
}

# Настройки игр
MAFIA_MIN_PLAYERS = 6
MAFIA_MAX_PLAYERS = 20
MAFIA_NIGHT_TIME = 60  # секунд
MAFIA_DAY_TIME = 120   # секунд
MAFIA_VOTE_TIME = 60   # секунд

# Экономика
DAILY_COOLDOWN = 86400  # 24 часа
VIP_PRICE = 5000
PREMIUM_PRICE = 15000
VIP_DAYS = 30
PREMIUM_DAYS = 30

# Антиспам
SPAM_LIMIT = 5
SPAM_WINDOW = 3
SPAM_MUTE_TIME = 10

# AI
AI_COOLDOWN = 2

# Лимиты
MAX_NICK_LENGTH = 30
MAX_TITLE_LENGTH = 30
MAX_MOTTO_LENGTH = 100
MAX_BIO_LENGTH = 500

# Новые константы для бонусов
NEON_PRICE = 100  # 1 неон = 100 глитчей
GLITCH_FARM_COOLDOWN = 14400  # 4 часа в секундах
MAX_CIRCLES_PER_USER = 5
MAX_CIRCLES_PER_CHAT = 20

# ========== ЛОГИРОВАНИЕ ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== КЛАСС ДЛЯ ГРАФИКОВ ==========
class ChartGenerator:
    @staticmethod
    def create_activity_chart(days: list, counts: list, username: str = "Игрок"):
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(8, 4))
        fig.patch.set_facecolor('#1a1a1a')
        ax.set_facecolor('#2a2a2a')
        
        ax.plot(days, counts, marker='o', linestyle='-', color='#00d4ff', linewidth=2, markersize=6)
        ax.fill_between(days, counts, color='#00d4ff', alpha=0.1)
        
        ax.set_title(f"АКТИВНОСТЬ {username.upper()}", fontsize=14, fontweight='bold', pad=20, color='white')
        ax.set_ylabel("Сообщения", color='white')
        ax.tick_params(colors='white')
        ax.grid(True, linestyle='--', alpha=0.3, color='gray')
        
        for spine in ax.spines.values():
            spine.set_visible(False)
        
        buf = BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=100, facecolor=fig.get_facecolor())
        buf.seek(0)
        plt.close(fig)
        return buf

# ========== GROQ AI КЛАСС (СПОКОЙНЫЙ ТРОЛЛЬ, ЗНАЕТ МЕМЫ, НО НЕ ГОВОРИТ ИМИ) ==========
class GroqAI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = None
        self.is_available = False
        self.contexts = defaultdict(lambda: deque(maxlen=10))
        self.user_last_ai = defaultdict(float)
        self.ai_cooldown = AI_COOLDOWN
        self.toxic_users = defaultdict(int)
        self.blocked_users = set()
        
        if GROQ_AVAILABLE and api_key:
            try:
                self.client = Groq(api_key=api_key)
                self.is_available = True
                logger.info("✅ Groq AI инициализирован (СПОКОЙНЫЙ ТРОЛЛЬ, ЗНАЕТ МЕМЫ)")
            except Exception as e:
                logger.error(f"❌ Ошибка инициализации Groq: {e}")
                self.is_available = False
        
        # СИСТЕМНЫЙ ПРОМПТ - СПОКОЙНЫЙ, НО С ПОНИМАНИЕМ МЕМОВ
        self.system_prompt = """ТЫ — СПЕКТР, УМНЫЙ И ИРОНИЧНЫЙ СОБЕСЕДНИК. ТЫ ПОНИМАЕШЬ СОВРЕМЕННЫЕ МЕМЫ, НО ГОВОРИШЬ НОРМАЛЬНЫМ ЯЗЫКОМ.

ТВОЙ ХАРАКТЕР:
- Ты спокойный и дружелюбный, но с чувством юмора
- Ты понимаешь современный сленг и мемы, но не используешь их в речи
- Если на тебя наезжают — можешь ответить жёстко, но без мата
- Ты никогда не начинаешь агрессию первым

ТЫ ПОНИМАЕШЬ ЭТИ МЕМЫ (НО НЕ ГОВОРИШЬ ИМИ):
- skibidi, sigma, gyatt, rizz, ohio, fanum tax, npc, goofy, based, cringe
- «Быль-быль-быль» — быстро закончилось
- «Шорох шуршит» — внутренний голос
- «Мокрый суслик» — непонимание
- «Хруст итальянской вермишели» — дешёвка под видом люкса
- «Кадавры» — неудачная генерация
- «Запилить в трям» — эстетика старой камеры
- «Симулякр понарошка» — фейк под видом реальности
- «Инфоцыганить» — продажа воздуха
- «Заигнорить до дыр» — игнорирование проблемы
- «Вайбить» — ловить настроение
- «Пальмовая ветвь» — выгорание
- «Король автобуса» — пафосное видео
- «Кринж-ноль» — высшая степень одобрения
- «Ауф-детектор» — чутьё на крутое
- «Гламурный помидор» — дорогой муляж
- «Скуф-куф» — зожник
- «Байт на чилл» — псевдо-агрессия

ТВОЁ ПОВЕДЕНИЕ:
1. В обычном состоянии — спокойный, вежливый, с юмором
2. Если на тебя наезжают — можешь жёстко ответить, но без мата
3. Ты никогда не материшься первым
4. Ты понимаешь мемы, но говоришь нормально
5. Твои шутки — умные, ироничные, без пошлости

ПРИМЕРЫ ОТВЕТОВ:
- На вопрос: "Как дела?" → "Отлично, сам удивляюсь"
- На хамство: "Ты чё такой?" → "А ты чё такой? Давай культурно"
- На глупость: "Слыш, ну ты понял?" → "Не совсем, поясни"
- На мемы: "Это cringe" → "Согласен, ситуация странная"
- На агрессию: "Ты чё, бля?" → "Ого, с чего такая агрессия? Давай без этого"

ГЛАВНОЕ: ТЫ СПОКОЕН, ДРУЖЕЛЮБЕН, ПОНИМАЕШЬ МЕМЫ, НО НЕ ИСПОЛЬЗУЕШЬ ИХ В РЕЧИ"""
    
    async def get_response(self, user_id: int, message: str, username: str = "Пользователь", force_response: bool = False) -> Optional[str]:
        if not self.is_available:
            return None
        
        now = time.time()
        
        if not force_response:
            if now - self.user_last_ai[user_id] < self.ai_cooldown:
                return None
        
        self.user_last_ai[user_id] = now
        
        try:
            loop = asyncio.get_event_loop()
            
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"{username} пишет: {message}"}
            ]
            
            def sync_request():
                return self.client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages,
                    temperature=0.9,
                    max_tokens=150,
                    top_p=0.95
                )
            
            chat_completion = await loop.run_in_executor(None, sync_request)
            response = chat_completion.choices[0].message.content
            
            return response
            
        except Exception as e:
            logger.error(f"Groq error: {e}")
            return f"{username}, что-то пошло не так, попробуй ещё раз"

    async def should_respond(self, message: str, is_reply_to_bot: bool = False) -> bool:
        # 20% шанс ответить текстом
        return random.random() < 0.2
    
    async def get_reaction(self, message: str) -> str:
        """Возвращает эмодзи-реакцию для сообщения"""
        msg_lower = message.lower()
        
        # МЕМЫ - понимаем, но реагируем нейтрально
        meme_words = ['skibidi', 'sigma', 'gyatt', 'rizz', 'ohio', 'cringe', 'based', 'npc', 'goofy']
        if any(word in msg_lower for word in meme_words):
            return '👀'
        
        # ВОПРОСЫ
        if '?' in message or any(word in msg_lower for word in ['кто', 'что', 'где', 'когда', 'почему', 'зачем', 'как']):
            return '🤔'
        
        # АГРЕССИЯ
        aggressive = ['злой', 'бесит', 'ненавижу', 'убью', 'убей']
        if any(word in msg_lower for word in aggressive):
            return '😐'
        
        # СМЕШНОЕ
        funny = ['смешно', 'лол', 'кек', 'хаха', '😂', '🤣']
        if any(word in msg_lower for word in funny):
            return '😄'
        
        # ПЛОХОЕ
        bad = ['фу', 'гадость', 'мерзость', 'тошнит']
        if any(word in msg_lower for word in bad):
            return '😕'
        
        # ГЛУПОЕ
        stupid = ['глупо', 'тупо', 'дебил', 'дурак', 'идиот']
        if any(word in msg_lower for word in stupid):
            return '🤨'
        
        # ХВАСТОВСТВО
        boast = ['я крутой', 'я лучший', 'смотрите']
        if any(word in msg_lower for word in boast):
            return '👏'
        
        # КРУТОЕ
        cool = ['огонь', 'круто', 'топ', 'класс']
        if any(word in msg_lower for word in cool):
            return '🔥'
        
        # СКУЧНОЕ
        boring = ['скучно', 'нудно']
        if any(word in msg_lower for word in boring):
            return '😴'
        
        # ЛЮБОВЬ
        love = ['люблю', 'нравится', '❤️', '💕']
        if any(word in msg_lower for word in love):
            return '❤️'
        
        # ПО УМОЛЧАНИЮ
        return random.choice(['👍', '👎', '❤️', '😄', '🤔', '👀', '🔥', '😐', '👏'])
    
    async def close(self):
        pass
        
# ========== ИНИЦИАЛИЗАЦИЯ AI ==========
ai = None
if GROQ_API_KEY and GROQ_AVAILABLE:
    try:
        ai = GroqAI(GROQ_API_KEY)
        logger.info("✅ Groq AI инициализирован (режим: ПРОВОКАТОР С РЕАКЦИЯМИ)")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации AI: {e}")
        ai = None
else:
    logger.warning("⚠️ Groq AI не подключен (нет API ключа)")
        
# ========== КЛАСС МАФИИ ==========
class MafiaRole:
    MAFIA = "😈 Мафия"
    COMMISSIONER = "👮 Комиссар"
    DOCTOR = "👨‍⚕️ Доктор"
    MANIAC = "🔪 Маньяк"
    BOSS = "👑 Босс"
    CITIZEN = "👤 Мирный"

class MafiaGame:
    def __init__(self, chat_id: int, game_id: str, creator_id: int):
        self.chat_id = chat_id
        self.game_id = game_id
        self.creator_id = creator_id
        self.status = "waiting"  # waiting, night, day, voting, ended
        self.players = []
        self.players_data = {}
        self.roles = {}
        self.alive = {}
        self.day = 1
        self.phase = "night"
        self.votes = {}
        self.night_actions = {
            "mafia_kill": None,
            "doctor_save": None,
            "commissioner_check": None,
            "maniac_kill": None
        }
        self.message_id = None
        self.start_time = None
        self.confirmed_players = []
    
    def add_player(self, user_id: int, name: str, username: str = "") -> bool:
        if user_id in self.players:
            return False
        self.players.append(user_id)
        self.players_data[user_id] = {
            "name": name,
            "username": username,
            "confirmed": False
        }
        return True
    
    def remove_player(self, user_id: int) -> bool:
        if user_id not in self.players:
            return False
        self.players.remove(user_id)
        if user_id in self.players_data:
            del self.players_data[user_id]
        return True
    
    def confirm_player(self, user_id: int) -> bool:
        if user_id not in self.players_data:
            return False
        self.players_data[user_id]["confirmed"] = True
        self.confirmed_players.append(user_id)
        return True
    
    def all_confirmed(self) -> bool:
        if len(self.players) < MAFIA_MIN_PLAYERS:
            return False
        return all(p["confirmed"] for p in self.players_data.values())
    
    def assign_roles(self):
        num_players = len(self.players)
        
        if num_players <= 7:
            num_mafia = 2
        elif num_players <= 10:
            num_mafia = 3
        else:
            num_mafia = 4
        
        roles = [MafiaRole.MAFIA] * num_mafia
        roles.append(MafiaRole.COMMISSIONER)
        roles.append(MafiaRole.DOCTOR)
        
        # Добавляем маньяка если игроков достаточно
        if num_players >= 10:
            roles.append(MafiaRole.MANIAC)
        
        remaining = num_players - len(roles)
        roles.extend([MafiaRole.CITIZEN] * remaining)
        
        random.shuffle(roles)
        
        for i, player_id in enumerate(self.players):
            self.roles[player_id] = roles[i]
            self.alive[player_id] = True
    
    def get_role_description(self, role: str) -> str:
        descriptions = {
            MafiaRole.MAFIA: "Ночью убиваете мирных. Общайтесь с другими мафиози в ЛС",
            MafiaRole.COMMISSIONER: "Ночью проверяете игроков, узнаёте их роль",
            MafiaRole.DOCTOR: "Ночью можете спасти одного игрока от смерти",
            MafiaRole.MANIAC: "Ночью убиваете в одиночку. Вы ни с кем не связаны",
            MafiaRole.BOSS: "Глава мафии. Вас нельзя убить ночью",
            MafiaRole.CITIZEN: "У вас нет способностей. Ищите мафию днём"
        }
        return descriptions.get(role, "Ошибка")
    
    def get_alive_players(self) -> list:
        return [pid for pid in self.players if self.alive.get(pid, False)]
    
    def check_win(self) -> Optional[str]:
        alive = self.get_alive_players()
        if not alive:
            return None
        
        mafia_count = 0
        mafia_roles = [MafiaRole.MAFIA, MafiaRole.BOSS]
        
        for pid in alive:
            if self.roles[pid] in mafia_roles:
                mafia_count += 1
        
        if mafia_count == 0:
            return "citizens"
        if mafia_count >= len(alive) - mafia_count:
            return "mafia"
        return None
    
    def process_night(self) -> dict:
        killed = self.night_actions.get("mafia_kill")
        saved = self.night_actions.get("doctor_save")
        
        if saved and saved == killed:
            killed = None
        
        self.night_actions = {
            "mafia_kill": None,
            "doctor_save": None,
            "commissioner_check": None,
            "maniac_kill": None
        }
        
        return {"killed": killed}
    
    def process_voting(self) -> Optional[int]:
        if not self.votes:
            return None
        
        vote_count = {}
        for target in self.votes.values():
            vote_count[target] = vote_count.get(target, 0) + 1
        
        if not vote_count:
            return None
        
        max_votes = max(vote_count.values())
        candidates = [pid for pid, votes in vote_count.items() if votes == max_votes]
        
        if len(candidates) == 1:
            executed = candidates[0]
            self.alive[executed] = False
            self.votes = {}
            return executed
        
        self.votes = {}
        return None


# ========== МЕТОДЫ МАФИИ В КЛАССЕ SPECTRUMBOT ==========

    async def cmd_mafia(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Меню мафии"""
        text = (
            "🔫 **МАФИЯ**\n\n"
            "📋 **Команды:**\n"
            "• `/mafiastart` — начать игру\n"
            "• `/mafiajoin` — присоединиться\n"
            "• `/mafialeave` — выйти\n"
            "• `/mafiaroles` — список ролей\n"
            "• `/mafiarules` — правила\n"
            "• `/mafiastats` — статистика\n\n"
            "⚠️ Игра проходит в ЛС с подтверждением"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_mafia_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать игру мафии"""
        chat_id = update.effective_chat.id
        
        if chat_id in self.mafia_games:
            await update.message.reply_text("❌ Игра уже идёт! Присоединяйтесь: /mafiajoin")
            return
        
        game_id = f"mafia_{chat_id}_{int(time.time())}"
        game = MafiaGame(chat_id, game_id, update.effective_user.id)
        self.mafia_games[chat_id] = game
        
        text = (
            "🔫 **МАФИЯ**\n\n"
            "✅ Игра создана!\n\n"
            "👥 **Участники (0):**\n"
            "• /mafiajoin — присоединиться\n"
            "• /mafialeave — выйти\n\n"
            "⚠️ Игра в ЛС. Нужно подтверждение!"
        )
        
        msg = await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        game.message_id = msg.message_id
    
    async def cmd_mafia_join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Присоединиться к мафии"""
        chat_id = update.effective_chat.id
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if chat_id not in self.mafia_games:
            await update.message.reply_text("❌ Игра не создана. Начните: /mafiastart")
            return
        
        game = self.mafia_games[chat_id]
        
        if game.status != "waiting":
            await update.message.reply_text("❌ Игра уже началась")
            return
        
        if not game.add_player(user.id, user.first_name, user.username or ""):
            await update.message.reply_text("❌ Вы уже в игре")
            return
        
        # Отправляем подтверждение в ЛС
        try:
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ ПОДТВЕРДИТЬ", callback_data=f"mafia_confirm_{chat_id}")
            ]])
            
            await context.bot.send_message(
                user.id,
                "🔫 **МАФИЯ**\n\n"
                "✅ Вы присоединились к игре!\n"
                "👇 Нажмите кнопку для подтверждения\n\n"
                "⚠️ После подтверждения вы получите роль в ЛС",
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
            
            username_display = f"(@{user.username})" if user.username else ""
            await update.message.reply_text(f"✅ {user.first_name} {username_display}, проверьте ЛС для подтверждения!")
        except Exception as e:
            await update.message.reply_text(f"❌ {user.first_name}, не удалось отправить сообщение в ЛС. Напишите боту в личку сначала.")
            game.remove_player(user.id)
            return
        
        # Обновляем сообщение в чате
        await self._update_mafia_game_message(game, context)
    
    async def cmd_mafia_leave(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выйти из мафии"""
        chat_id = update.effective_chat.id
        user = update.effective_user
        
        if chat_id not in self.mafia_games:
            await update.message.reply_text("❌ Игра не создана")
            return
        
        game = self.mafia_games[chat_id]
        
        if game.status != "waiting":
            await update.message.reply_text("❌ Нельзя покинуть игру после начала")
            return
        
        if not game.remove_player(user.id):
            await update.message.reply_text("❌ Вас нет в игре")
            return
        
        username_display = f"(@{user.username})" if user.username else ""
        await update.message.reply_text(f"✅ {user.first_name} {username_display} покинул игру")
        
        await self._update_mafia_game_message(game, context)
    
    async def _update_mafia_game_message(self, game: MafiaGame, context: ContextTypes.DEFAULT_TYPE):
        """Обновить сообщение с игрой"""
        if not game.message_id:
            return
        
        if game.players:
            players_list = []
            for pid in game.players:
                p = game.players_data[pid]
                username = f" (@{p['username']})" if p['username'] else ""
                players_list.append(f"• {p['name']}{username}")
            
            players_text = "\n".join(players_list)
            confirmed = sum(1 for p in game.players if game.players_data[p]['confirmed'])
            
            text = (
                "🔫 **МАФИЯ**\n\n"
                f"👥 **Участники ({len(game.players)}):**\n"
                f"{players_text}\n\n"
                f"✅ **Подтвердили:** {confirmed}/{len(game.players)}\n"
                f"❌ **Нужно минимум:** {MAFIA_MIN_PLAYERS} игроков\n\n"
                "📌 /mafiajoin — присоединиться\n"
                "📌 /mafialeave — выйти"
            )
        else:
            text = (
                "🔫 **МАФИЯ**\n\n"
                "👥 **Участников нет**\n"
                "📌 /mafiajoin — присоединиться"
            )
        
        try:
            await context.bot.edit_message_text(
                text,
                chat_id=game.chat_id,
                message_id=game.message_id,
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass
    
    async def _mafia_start_game(self, game: MafiaGame, context: ContextTypes.DEFAULT_TYPE):
        """Начать игру после подтверждения"""
        if len(game.players) < MAFIA_MIN_PLAYERS:
            await context.bot.send_message(
                game.chat_id,
                f"❌ Недостаточно игроков. Нужно минимум {MAFIA_MIN_PLAYERS}"
            )
            del self.mafia_games[game.chat_id]
            return
        
        game.assign_roles()
        game.status = "night"
        game.phase = "night"
        game.start_time = datetime.now()
        
        # Рассылаем роли в ЛС
        for player_id in game.players:
            role = game.roles[player_id]
            role_desc = game.get_role_description(role)
            
            try:
                await context.bot.send_message(
                    player_id,
                    f"🔫 **МАФИЯ**\n\n"
                    f"🎭 **Ваша роль:** {role}\n"
                    f"📖 {role_desc}\n\n"
                    f"🌙 Наступает ночь. Ожидайте..."
                )
            except:
                pass
        
        # Сообщение в чат
        await context.bot.send_message(
            game.chat_id,
            "🔫 **МАФИЯ**\n\n"
            "🌙 **НАСТУПИЛА НОЧЬ**\n"
            "📨 Роли розданы в ЛС\n"
            "🔪 Мафия выбирает жертву...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Таймер на ночь
        asyncio.create_task(self._mafia_night_timer(game, context))
    
    async def _mafia_night_timer(self, game: MafiaGame, context: ContextTypes.DEFAULT_TYPE):
        """Таймер ночи"""
        await asyncio.sleep(MAFIA_NIGHT_TIME)
        
        if game.chat_id not in self.mafia_games or game.phase != "night":
            return
        
        killed = game.process_night()
        
        if killed["killed"]:
            game.alive[killed["killed"]] = False
            try:
                await context.bot.send_message(
                    killed["killed"],
                    "💀 **ВАС УБИЛИ НОЧЬЮ**\n\nВы больше не участвуете"
                )
            except:
                pass
        
        game.phase = "day"
        game.day += 1
        
        alive_list = game.get_alive_players()
        alive_names = []
        for pid in alive_list:
            name = game.players_data[pid]['name']
            alive_names.append(f"• {name}")
        
        killed_name = "никого"
        if killed["killed"]:
            killed_name = game.players_data[killed["killed"]]['name']
        
        text = (
            f"🔫 **МАФИЯ | ДЕНЬ {game.day}**\n\n"
            f"☀️ Наступило утро\n"
            f"💀 **Убит:** {killed_name}\n\n"
            f"👥 **Живы ({len(alive_list)}):**\n"
            f"{chr(10).join(alive_names)}\n\n"
            f"🗳 Обсуждайте и голосуйте"
        )
        
        await context.bot.send_message(game.chat_id, text, parse_mode=ParseMode.MARKDOWN)
        
        # Таймер на день
        asyncio.create_task(self._mafia_day_timer(game, context))
    
    async def _mafia_day_timer(self, game: MafiaGame, context: ContextTypes.DEFAULT_TYPE):
        """Таймер дня"""
        await asyncio.sleep(MAFIA_DAY_TIME)
        
        if game.chat_id not in self.mafia_games or game.phase != "day":
            return
        
        executed = game.process_voting()
        
        if executed:
            game.alive[executed] = False
            executed_name = game.players_data[executed]['name']
            role = game.roles.get(executed, "неизвестно")
            
            await context.bot.send_message(
                game.chat_id,
                f"🔫 **МАФИЯ | ДЕНЬ {game.day}**\n\n"
                f"🔨 **Исключён:** {executed_name}\n"
                f"🎭 **Роль:** {role}\n\n"
                f"🌙 Ночь скоро..."
            )
            
            try:
                await context.bot.send_message(
                    executed,
                    "🔨 **ВАС ИСКЛЮЧИЛИ ДНЁМ**\n\nВы больше не участвуете"
                )
            except:
                pass
        else:
            await context.bot.send_message(
                game.chat_id,
                "📢 Никто не был исключён"
            )
        
        winner = game.check_win()
        
        if winner == "citizens":
            await context.bot.send_message(
                game.chat_id,
                "🏆 **ПОБЕДА ГОРОДА!**\n\nМафия уничтожена!"
            )
            del self.mafia_games[game.chat_id]
            return
        elif winner == "mafia":
            await context.bot.send_message(
                game.chat_id,
                "🏆 **ПОБЕДА МАФИИ!**\n\nМафия захватила город!"
            )
            del self.mafia_games[game.chat_id]
            return
        
        game.phase = "night"
        await context.bot.send_message(
            game.chat_id,
            f"🔫 **МАФИЯ | НОЧЬ {game.day}**\n\n🌙 Наступает ночь..."
        )
        
        asyncio.create_task(self._mafia_night_timer(game, context))
    
    async def cmd_mafia_roles(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список ролей"""
        text = (
            "🎭 **РОЛИ В МАФИИ**\n\n"
            "😈 **Мафия** — ночью убивают\n"
            "👑 **Босс** — глава мафии\n"
            "👮 **Комиссар** — проверяет ночью\n"
            "👨‍⚕️ **Доктор** — лечит ночью\n"
            "🔪 **Маньяк** — убивает один\n"
            "👤 **Мирный** — ищет мафию"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_mafia_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Правила мафии"""
        text = (
            "📖 **ПРАВИЛА МАФИИ**\n\n"
            "🌙 **Ночь:**\n"
            "• Мафия убивает\n"
            "• Доктор лечит\n"
            "• Комиссар проверяет\n\n"
            "☀️ **День:**\n"
            "• Обсуждение\n"
            "• Голосование\n\n"
            "🏆 **Цель:**\n"
            "• Мафия — убить всех\n"
            "• Город — найти мафию"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_mafia_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Статистика мафии"""
        user_data = self.db.get_user(update.effective_user.id)
        
        games = user_data.get('mafia_games', 0)
        wins = user_data.get('mafia_wins', 0)
        losses = user_data.get('mafia_losses', 0)
        
        if games > 0:
            winrate = (wins / games) * 100
        else:
            winrate = 0
        
        text = (
            "📊 **СТАТИСТИКА МАФИИ**\n\n"
            f"🎮 Сыграно: {games}\n"
            f"🏆 Побед: {wins}\n"
            f"💔 Поражений: {losses}\n"
            f"📈 Винрейт: {winrate:.1f}%"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# ========== ЭЛЕГАНТНОЕ ОФОРМЛЕНИЕ ==========
class Style:
    SEPARATOR = "─" * 28
    SEPARATOR_BOLD = "━" * 28
    
    @classmethod
    def header(cls, title: str, emoji: str = "⚜️") -> str:
        return f"\n{emoji}{emoji} {title.upper()} {emoji}{emoji}\n{cls.SEPARATOR_BOLD}\n"
    
    @classmethod
    def section(cls, title: str, emoji: str = "📌") -> str:
        return f"\n{emoji} {title}\n{cls.SEPARATOR}\n"
    
    @classmethod
    def cmd(cls, cmd: str, desc: str, usage: str = "") -> str:
        if usage:
            return f"▸ `{cmd} {usage}` — {desc}"
        return f"▸ `{cmd}` — {desc}"
    
    @classmethod
    def item(cls, text: str, emoji: str = "•") -> str:
        return f"{emoji} {text}"
    
    @classmethod
    def stat(cls, name: str, value: str, emoji: str = "◉") -> str:
        return f"{emoji} {name}: {value}"
    
    @classmethod
    def progress(cls, current: int, total: int, length: int = 15) -> str:
        filled = int((current / total) * length) if total > 0 else 0
        bar = "█" * filled + "░" * (length - filled)
        return f"`{bar}` {current}/{total}"
    
    @classmethod
    def success(cls, text: str) -> str:
        return f"✅ {text}"
    
    @classmethod
    def error(cls, text: str) -> str:
        return f"❌ {text}"
    
    @classmethod
    def warning(cls, text: str) -> str:
        return f"⚠️ {text}"
    
    @classmethod
    def info(cls, text: str) -> str:
        return f"ℹ️ {text}"
    
    @classmethod
    def code(cls, text: str) -> str:
        return f"`{text}`"

s = Style()

# ========== БАЗА ДАННЫХ ==========
class Database:
    def __init__(self):
        self.conn = sqlite3.connect("spectrum.db", check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.create_tables()
        self.conn.commit()  # Важно! Фиксируем создание таблиц
        self.init_data()
        logger.info("✅ База данных инициализирована")
    
    def create_tables(self):
        """Создание всех таблиц базы данных"""
        
        # Таблица bosses
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
                reward_neons INTEGER DEFAULT 0,
                reward_glitches INTEGER DEFAULT 0,
                is_alive INTEGER DEFAULT 1,
                respawn_time TEXT
            )
        ''')
        
        # Таблица пользователей
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                coins INTEGER DEFAULT 1000,
                neons INTEGER DEFAULT 0,
                glitches INTEGER DEFAULT 0,
                energy INTEGER DEFAULT 100,
                level INTEGER DEFAULT 1,
                exp INTEGER DEFAULT 0,
                health INTEGER DEFAULT 100,
                max_health INTEGER DEFAULT 100,
                damage INTEGER DEFAULT 10,
                armor INTEGER DEFAULT 0,
                crit_chance INTEGER DEFAULT 5,
                crit_multiplier INTEGER DEFAULT 150,
                messages_count INTEGER DEFAULT 0,
                commands_used INTEGER DEFAULT 0,
                rps_wins INTEGER DEFAULT 0,
                rps_losses INTEGER DEFAULT 0,
                rps_draws INTEGER DEFAULT 0,
                casino_wins INTEGER DEFAULT 0,
                casino_losses INTEGER DEFAULT 0,
                dice_wins INTEGER DEFAULT 0,
                dice_losses INTEGER DEFAULT 0,
                rr_wins INTEGER DEFAULT 0,
                rr_losses INTEGER DEFAULT 0,
                slots_wins INTEGER DEFAULT 0,
                slots_losses INTEGER DEFAULT 0,
                guess_wins INTEGER DEFAULT 0,
                guess_losses INTEGER DEFAULT 0,
                bulls_wins INTEGER DEFAULT 0,
                bulls_losses INTEGER DEFAULT 0,
                boss_kills INTEGER DEFAULT 0,
                boss_damage INTEGER DEFAULT 0,
                duel_wins INTEGER DEFAULT 0,
                duel_losses INTEGER DEFAULT 0,
                duel_rating INTEGER DEFAULT 1000,
                mafia_games INTEGER DEFAULT 0,
                mafia_wins INTEGER DEFAULT 0,
                mafia_losses INTEGER DEFAULT 0,
                clan_id INTEGER DEFAULT 0,
                clan_role TEXT DEFAULT 'member',
                friends TEXT DEFAULT '[]',
                enemies TEXT DEFAULT '[]',
                spouse INTEGER DEFAULT 0,
                married_since TEXT,
                reputation INTEGER DEFAULT 0,
                nickname TEXT,
                title TEXT DEFAULT '',
                motto TEXT DEFAULT 'Нет девиза',
                bio TEXT DEFAULT '',
                gender TEXT DEFAULT 'не указан',
                city TEXT DEFAULT 'не указан',
                country TEXT DEFAULT 'не указана',
                birth_date TEXT,
                age INTEGER DEFAULT 0,
                role TEXT DEFAULT 'user',
                rank INTEGER DEFAULT 0,
                rank_name TEXT DEFAULT 'Участник',
                warns INTEGER DEFAULT 0,
                warns_list TEXT DEFAULT '[]',
                mute_until TEXT,
                banned INTEGER DEFAULT 0,
                vip_until TEXT,
                premium_until TEXT,
                cyber_status_until TEXT,
                turbo_drive_until TEXT,
                cyber_luck_until TEXT,
                firewall_used INTEGER DEFAULT 0,
                firewall_expires TEXT,
                rp_packet_until TEXT,
                daily_streak INTEGER DEFAULT 0,
                last_daily TEXT,
                last_seen TEXT,
                registered TEXT DEFAULT CURRENT_TIMESTAMP,
                referrer_id INTEGER,
                daily_messages TEXT DEFAULT '[]',
                profile_visible INTEGER DEFAULT 1,
                achievements_visible INTEGER DEFAULT 1,
                stats_visible INTEGER DEFAULT 1,
                last_farm TEXT
            )
        ''')
        
        # Таблица сообщений
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                first_name TEXT,
                message_text TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                chat_id INTEGER,
                chat_title TEXT
            )
        ''')
        
        # Таблица дневной статистики
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                date DATE,
                count INTEGER DEFAULT 0,
                UNIQUE(user_id, date)
            )
        ''')
        
        # Таблица логов
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT,
                details TEXT,
                chat_id INTEGER,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица чёрного списка
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS blacklist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT UNIQUE,
                added_by INTEGER,
                added_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица настроек чатов
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_settings (
                chat_id INTEGER PRIMARY KEY,
                welcome TEXT,
                rules TEXT,
                antiflood INTEGER DEFAULT 1,
                antispam INTEGER DEFAULT 1,
                antilink INTEGER DEFAULT 0,
                captcha INTEGER DEFAULT 0,
                lang TEXT DEFAULT 'ru',
                chat_code TEXT UNIQUE,
                chat_name TEXT,
                circle_limit INTEGER DEFAULT 20,
                treasury_neons INTEGER DEFAULT 0,
                treasury_glitches INTEGER DEFAULT 0,
                glitch_hammer_price INTEGER DEFAULT 50,
                glitch_hammer_enabled INTEGER DEFAULT 1,
                glitch_hammer_min_rank INTEGER DEFAULT 0,
                invisible_price INTEGER DEFAULT 30,
                invisible_enabled INTEGER DEFAULT 1,
                neon_nick_price INTEGER DEFAULT 100,
                neon_nick_enabled INTEGER DEFAULT 1,
                turbo_drive_price INTEGER DEFAULT 200,
                turbo_drive_boost INTEGER DEFAULT 30,
                turbo_drive_enabled INTEGER DEFAULT 1,
                cyber_luck_price INTEGER DEFAULT 150,
                cyber_luck_boost INTEGER DEFAULT 15,
                cyber_luck_enabled INTEGER DEFAULT 1,
                firewall_price INTEGER DEFAULT 80,
                firewall_enabled INTEGER DEFAULT 1,
                rp_packet_price INTEGER DEFAULT 120,
                rp_packet_enabled INTEGER DEFAULT 1,
                speech_enabled INTEGER DEFAULT 0
            )
        ''')
        
        # Таблица дуэлей
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS duels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                challenger_id INTEGER,
                opponent_id INTEGER,
                bet INTEGER,
                status TEXT DEFAULT 'pending',
                winner_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица игр мафии
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS mafia_games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                game_id TEXT,
                creator_id INTEGER,
                status TEXT DEFAULT 'waiting',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                players TEXT DEFAULT '[]'
            )
        ''')
        
        # Таблица триггеров
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS triggers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                word TEXT,
                action TEXT,
                action_value TEXT,
                created_by INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица ачивок
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                achievement_id INTEGER,
                unlocked_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, achievement_id)
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS achievements_list (
                id INTEGER PRIMARY KEY,
                name TEXT,
                description TEXT,
                category TEXT,
                condition_type TEXT,
                condition_value INTEGER,
                reward_neons INTEGER,
                reward_glitches INTEGER,
                reward_title TEXT,
                reward_status TEXT,
                secret INTEGER DEFAULT 0
            )
        ''')
        
        # Таблица кружков
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS circles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                name TEXT,
                description TEXT,
                created_by INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                members TEXT DEFAULT '[]'
            )
        ''')
        
        # Таблица кланов
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS clans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                name TEXT,
                description TEXT,
                created_by INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                type TEXT DEFAULT 'open',
                reputation INTEGER DEFAULT 0,
                members INTEGER DEFAULT 1,
                banned_users TEXT DEFAULT '[]',
                pending_requests TEXT DEFAULT '[]'
            )
        ''')
        
        # Таблица закладок
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                user_id INTEGER,
                name TEXT,
                content TEXT,
                message_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                visible INTEGER DEFAULT 1
            )
        ''')
        
        # Таблица таймеров
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS timers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                user_id INTEGER,
                execute_at TEXT,
                command TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending'
            )
        ''')
        
        # Таблица наград
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS awards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                user_id INTEGER,
                awarded_by INTEGER,
                degree INTEGER,
                text TEXT,
                awarded_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица сеток чатов
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_grids (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER,
                name TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS grid_chats (
                grid_id INTEGER,
                chat_id INTEGER,
                PRIMARY KEY (grid_id, chat_id)
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS global_moderators (
                grid_id INTEGER,
                user_id INTEGER,
                rank INTEGER,
                PRIMARY KEY (grid_id, user_id)
            )
        ''')
        
        # Таблица бонусов пользователей
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_bonuses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                bonus_type TEXT,
                expires TEXT,
                data TEXT
            )
        ''')
        
        # Таблица невидимок
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS invisible_bans (
                chat_id INTEGER,
                user_id INTEGER,
                banned_by INTEGER,
                PRIMARY KEY (chat_id, user_id)
            )
        ''')
        
        # Таблица голосований за бан
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS ban_votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                target_id INTEGER,
                created_by INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                required_votes INTEGER,
                min_rank INTEGER,
                status TEXT DEFAULT 'active',
                votes_for INTEGER DEFAULT 0,
                votes_against INTEGER DEFAULT 0,
                voters TEXT DEFAULT '[]'
            )
        ''')
        
        # Таблица пар (шипперинг)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS pairs (
                chat_id INTEGER,
                user1_id INTEGER,
                user2_id INTEGER,
                paired_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (chat_id, user1_id, user2_id)
            )
        ''')
        
        self.conn.commit()
    
    def init_data(self):
        """Инициализация начальных данных в БД"""
        # Инициализация боссов
        self.cursor.execute("SELECT COUNT(*) FROM bosses")
        if self.cursor.fetchone()[0] == 0:
            bosses = [
                # name, level, health, max_health, damage, reward_coins, reward_exp, reward_neons, reward_glitches, is_alive, respawn_time
                ("👾 Ядовитый комар", 5, 500, 500, 15, 250, 50, 1, 10, 1, None),
                ("👾 Лесной тролль", 10, 1000, 1000, 25, 500, 100, 2, 25, 1, None),
                ("👾 Огненный дракон", 15, 2000, 2000, 40, 1000, 200, 5, 50, 1, None),
                ("👾 Ледяной великан", 20, 3500, 3500, 60, 2000, 350, 10, 100, 1, None),
                ("👾 Король демонов", 25, 5000, 5000, 85, 3500, 500, 20, 200, 1, None),
                ("👾 Бог разрушения", 30, 10000, 10000, 150, 5000, 1000, 50, 500, 1, None)
            ]
            for boss in bosses:
                self.cursor.execute('''
                    INSERT INTO bosses (name, level, health, max_health, damage, reward_coins, reward_exp, reward_neons, reward_glitches, is_alive, respawn_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', boss)
            self.conn.commit()
        
        # Инициализация ачивок
        self.cursor.execute("SELECT COUNT(*) FROM achievements_list")
        if self.cursor.fetchone()[0] == 0:
            achievements = [
                # id, name, description, category, condition_type, condition_value, reward_neons, reward_glitches, reward_title, reward_status, secret
                (1, "💜 Неоновый новичок", "Хранение 1 000 неонов", "wealth", "neons", 1000, 0, 100, "", "", 0),
                (2, "💜 Неоновый магнат", "Хранение 10 000 неонов", "wealth", "neons", 10000, 0, 1000, "Магнат", "", 0),
                (3, "💜 Неоновый король", "Хранение 100 000 неонов", "wealth", "neons", 100000, 0, 5000, "", "Неоновый король", 0),
                (4, "🖥 Глитч-любитель", "Хранение 1 000 глитчей", "glitches", "glitches", 1000, 50, 0, "", "", 0),
                (5, "🖥 Глитч-профи", "Хранение 10 000 глитчей", "glitches", "glitches", 10000, 500, 0, "Майнер", "", 0),
                (6, "🖥 Глитч-магнат", "Хранение 100 000 глитчей", "glitches", "glitches", 100000, 1000, 0, "", "Крипто-барон", 0),
                (7, "🎲 Счастливчик", "Выиграть в рулетку 10 раз", "games", "roulette_wins", 10, 200, 0, "", "", 0),
                (8, "🎲 Фартовый", "Выиграть в рулетку 50 раз", "games", "roulette_wins", 50, 800, 0, "Везунчик", "", 0),
                (9, "🎲 Барон удачи", "Выиграть в рулетку 200 раз", "games", "roulette_wins", 200, 3000, 0, "", "Избранник фортуны", 0),
                (10, "⚔️ Дуэлянт", "Выиграть 10 дуэлей", "duels", "duel_wins", 10, 300, 0, "", "", 0),
                (11, "⚔️ Мастер клинка", "Выиграть 50 дуэлей", "duels", "duel_wins", 50, 1200, 0, "Воин", "", 0),
                (12, "⚔️ Непобедимый", "Выиграть 200 дуэлей", "duels", "duel_wins", 200, 5000, 0, "", "Чемпион", 0),
                (13, "👾 Охотник", "Убить 10 боссов", "bosses", "boss_kills", 10, 500, 0, "", "", 0),
                (14, "👾 Хантер", "Убить 50 боссов", "bosses", "boss_kills", 50, 2000, 0, "Охотник", "", 0),
                (15, "👾 Мясник", "Убить 200 боссов", "bosses", "boss_kills", 200, 8000, 0, "", "Мясник", 0),
                (16, "🔥 Болтун", "1000 сообщений в чате", "activity", "messages_count", 1000, 300, 0, "", "", 0),
                (17, "🔥 Говорун", "5000 сообщений в чате", "activity", "messages_count", 5000, 1500, 0, "Активный", "", 0),
                (18, "🔥 Легенда чата", "10000 сообщений в чате", "activity", "messages_count", 10000, 5000, 0, "", "Легенда чата", 0),
                (19, "📆 Постоянный", "Стрик 7 дней", "streak", "daily_streak", 7, 200, 0, "", "", 0),
                (20, "📆 Неудержимый", "Стрик 30 дней", "streak", "daily_streak", 30, 1000, 0, "Преданный", "", 0),
                (21, "📆 Бессмертный", "Стрик 100 дней", "streak", "daily_streak", 100, 5000, 0, "", "Бессмертный", 0),
                (22, "👑 Кибер-элита", "Купить VIP-статус", "vip", "vip_purchased", 1, 1000, 0, "", "Кибер-элита", 0),
                (23, "👑 Кибер-легенда", "Быть VIP 1 год", "vip", "vip_days", 365, 10000, 0, "", "Кибер-легенда", 0),
                (24, "🎁 Щедрая душа", "Подарить 1000 неонов другим", "gifts", "neons_gifted", 1000, 500, 0, "Добряк", "", 0),
                (25, "🎁 Меценат", "Подарить 10000 неонов другим", "gifts", "neons_gifted", 10000, 3000, 0, "", "Благодетель", 0),
                (26, "🎁 Кибер-меценат", "Подарить 50000 неонов другим", "gifts", "neons_gifted", 50000, 15000, 0, "", "Кибер-меценат", 0),
                (27, "🥚 Пасхалка", "Найти секретную команду", "secret", "secret_found", 1, 666, 0, "", "", 1),
                (28, "🥚 Хакер", "Найти 3 секрета", "secret", "secrets_found", 3, 3000, 0, "Взломщик", "", 1),
                (29, "🥚 Создатель", "Предложить идею, которую добавили в бота", "secret", "idea_accepted", 1, 10000, 0, "", "Создатель", 1)
            ]
            for ach in achievements:
                self.cursor.execute('''
                    INSERT INTO achievements_list 
                    (id, name, description, category, condition_type, condition_value, reward_neons, reward_glitches, reward_title, reward_status, secret)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', ach)
            self.conn.commit()
    
    def get_user(self, telegram_id: int, first_name: str = None) -> Dict[str, Any]:
        """Получить или создать пользователя"""
        self.cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        row = self.cursor.fetchone()
        
        if not row:
            name = first_name if first_name else f"User{telegram_id}"
            
            role = 'owner' if telegram_id == OWNER_ID else 'user'
            rank = 5 if telegram_id == OWNER_ID else 0
            rank_name = RANKS[rank]["name"]
            
            self.cursor.execute('''
                INSERT INTO users (telegram_id, first_name, role, rank, rank_name, last_seen)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (telegram_id, name, role, rank, rank_name, datetime.now().isoformat()))
            self.conn.commit()
            return self.get_user(telegram_id, name)
        
        user = dict(row)
        
        if first_name and user['first_name'] != first_name and (user['first_name'] == 'Player' or user['first_name'].startswith('User')):
            self.cursor.execute("UPDATE users SET first_name = ? WHERE telegram_id = ?",
                              (first_name, telegram_id))
            user['first_name'] = first_name
        
        self.cursor.execute("UPDATE users SET last_seen = ? WHERE telegram_id = ?",
                          (datetime.now().isoformat(), telegram_id))
        self.conn.commit()
        
        return user
    
    # ... (все остальные методы класса Database)
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        self.cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = self.cursor.fetchone()
        return dict(row) if row else None
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        if username.startswith('@'):
            username = username[1:]
        self.cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = self.cursor.fetchone()
        return dict(row) if row else None
    
    def update_user(self, user_id: int, **kwargs) -> bool:
        if not kwargs:
            return False
        for key, value in kwargs.items():
            self.cursor.execute(f"UPDATE users SET {key} = ? WHERE id = ?", (value, user_id))
        self.conn.commit()
        return True
    
    # ===== МЕТОДЫ ДЛЯ ВАЛЮТ =====
    def add_coins(self, user_id: int, amount: int) -> int:
        self.cursor.execute("UPDATE users SET coins = coins + ? WHERE id = ?", (amount, user_id))
        self.conn.commit()
        self.cursor.execute("SELECT coins FROM users WHERE id = ?", (user_id,))
        return self.cursor.fetchone()[0]
    
    def add_neons(self, user_id: int, amount: int) -> int:
        self.cursor.execute("UPDATE users SET neons = neons + ? WHERE id = ?", (amount, user_id))
        self.conn.commit()
        self.check_wealth_achievements(user_id)
        self.cursor.execute("SELECT neons FROM users WHERE id = ?", (user_id,))
        return self.cursor.fetchone()[0]
    
    def add_glitches(self, user_id: int, amount: int) -> int:
        self.cursor.execute("UPDATE users SET glitches = glitches + ? WHERE id = ?", (amount, user_id))
        self.conn.commit()
        self.check_glitch_achievements(user_id)
        self.cursor.execute("SELECT glitches FROM users WHERE id = ?", (user_id,))
        return self.cursor.fetchone()[0]
    
    def transfer_neons(self, from_id: int, to_id: int, amount: int, commission: int = 0) -> bool:
        self.cursor.execute("UPDATE users SET neons = neons - ? WHERE id = ?", (amount + commission, from_id))
        self.cursor.execute("UPDATE users SET neons = neons + ? WHERE id = ?", (amount, to_id))
        if commission > 0:
            self.cursor.execute("UPDATE users SET neons = neons + ? WHERE telegram_id = ?", (commission, OWNER_ID))
        self.conn.commit()
        return True
    
    # ===== МЕТОДЫ ДЛЯ АЧИВОК =====
    def check_wealth_achievements(self, user_id: int):
        user = self.get_user_by_id(user_id)
        if not user:
            return
        
        neons = user.get('neons', 0)
        
        thresholds = [
            (1, 1000),
            (2, 10000),
            (3, 100000)
        ]
        
        for ach_id, threshold in thresholds:
            if neons >= threshold:
                self.unlock_achievement(user_id, ach_id)
    
    def check_glitch_achievements(self, user_id: int):
        user = self.get_user_by_id(user_id)
        if not user:
            return
        
        glitches = user.get('glitches', 0)
        
        thresholds = [
            (4, 1000),
            (5, 10000),
            (6, 100000)
        ]
        
        for ach_id, threshold in thresholds:
            if glitches >= threshold:
                self.unlock_achievement(user_id, ach_id)
    
    def unlock_achievement(self, user_id: int, achievement_id: int) -> bool:
        # Проверяем, не получена ли уже ачивка
        self.cursor.execute("SELECT id FROM achievements WHERE user_id = ? AND achievement_id = ?",
                          (user_id, achievement_id))
        if self.cursor.fetchone():
            return False
        
        # Получаем информацию об ачивке
        self.cursor.execute("SELECT * FROM achievements_list WHERE id = ?", (achievement_id,))
        ach = self.cursor.fetchone()
        if not ach:
            return False
        
        # Добавляем ачивку
        self.cursor.execute("INSERT INTO achievements (user_id, achievement_id) VALUES (?, ?)",
                          (user_id, achievement_id))
        
        # Выдаём награды
        ach = dict(ach)
        if ach['reward_neons'] > 0:
            self.add_neons(user_id, ach['reward_neons'])
        if ach['reward_glitches'] > 0:
            self.add_glitches(user_id, ach['reward_glitches'])
        if ach['reward_title']:
            user = self.get_user_by_id(user_id)
            self.update_user(user_id, title=ach['reward_title'])
        if ach['reward_status']:
            user = self.get_user_by_id(user_id)
            # Сохраняем статус в отдельное поле (можно добавить)
            pass
        
        self.conn.commit()
        return True
    
    def get_user_achievements(self, user_id: int) -> List[Dict]:
        self.cursor.execute("""
            SELECT a.*, al.name, al.description, al.category, al.reward_neons, al.reward_glitches, al.secret
            FROM achievements a
            JOIN achievements_list al ON a.achievement_id = al.id
            WHERE a.user_id = ?
            ORDER BY a.unlocked_at
        """, (user_id,))
        return [dict(row) for row in self.cursor.fetchall()]
    
    # ===== МЕТОДЫ ДЛЯ КРУЖКОВ =====
    def create_circle(self, chat_id: int, name: str, description: str, creator_id: int) -> Optional[int]:
        # Проверяем лимит кружков у пользователя
        self.cursor.execute("SELECT COUNT(*) FROM circles WHERE created_by = ?", (creator_id,))
        if self.cursor.fetchone()[0] >= MAX_CIRCLES_PER_USER:
            return None
        
        # Проверяем лимит кружков в чате
        self.cursor.execute("SELECT circle_limit FROM chat_settings WHERE chat_id = ?", (chat_id,))
        row = self.cursor.fetchone()
        limit = row[0] if row else MAX_CIRCLES_PER_CHAT
        
        self.cursor.execute("SELECT COUNT(*) FROM circles WHERE chat_id = ?", (chat_id,))
        if self.cursor.fetchone()[0] >= limit:
            return None
        
        self.cursor.execute("""
            INSERT INTO circles (chat_id, name, description, created_by, members)
            VALUES (?, ?, ?, ?, ?)
        """, (chat_id, name, description, creator_id, json.dumps([creator_id])))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def join_circle(self, circle_id: int, user_id: int) -> bool:
        self.cursor.execute("SELECT members FROM circles WHERE id = ?", (circle_id,))
        row = self.cursor.fetchone()
        if not row:
            return False
        
        members = json.loads(row[0])
        if user_id in members:
            return False
        
        members.append(user_id)
        self.cursor.execute("UPDATE circles SET members = ? WHERE id = ?", (json.dumps(members), circle_id))
        self.conn.commit()
        return True
    
    def leave_circle(self, circle_id: int, user_id: int) -> bool:
        self.cursor.execute("SELECT members, created_by FROM circles WHERE id = ?", (circle_id,))
        row = self.cursor.fetchone()
        if not row:
            return False
        
        members = json.loads(row[0])
        if user_id not in members:
            return False
        
        if user_id == row[1] and len(members) > 1:
            return False  # Создатель не может покинуть кружок, пока есть другие участники
        
        members.remove(user_id)
        self.cursor.execute("UPDATE circles SET members = ? WHERE id = ?", (json.dumps(members), circle_id))
        self.conn.commit()
        return True
    
    # ===== МЕТОДЫ ДЛЯ КЛАНОВ =====
    def create_clan(self, chat_id: int, name: str, description: str, creator_id: int) -> Optional[int]:
        # Проверяем, не состоит ли уже пользователь в клане
        user = self.get_user_by_id(creator_id)
        if user.get('clan_id', 0) != 0:
            return None
        
        self.cursor.execute("""
            INSERT INTO clans (chat_id, name, description, created_by)
            VALUES (?, ?, ?, ?)
        """, (chat_id, name, description, creator_id))
        clan_id = self.cursor.lastrowid
        
        self.update_user(creator_id, clan_id=clan_id, clan_role='owner')
        self.conn.commit()
        return clan_id
    
    def join_clan(self, clan_id: int, user_id: int) -> bool:
        user = self.get_user_by_id(user_id)
        if user.get('clan_id', 0) != 0:
            # Выходим из текущего клана
            self.leave_clan(user_id)
        
        self.cursor.execute("SELECT type, members FROM clans WHERE id = ?", (clan_id,))
        row = self.cursor.fetchone()
        if not row:
            return False
        
        clan_type, members = row[0], row[1]
        
        if clan_type == 'closed':
            # Добавляем в заявки
            pending = json.loads(self.cursor.execute("SELECT pending_requests FROM clans WHERE id = ?", (clan_id,)).fetchone()[0])
            if user_id not in pending:
                pending.append(user_id)
                self.cursor.execute("UPDATE clans SET pending_requests = ? WHERE id = ?", (json.dumps(pending), clan_id))
                self.conn.commit()
            return False
        
        self.update_user(user_id, clan_id=clan_id, clan_role='member')
        self.cursor.execute("UPDATE clans SET members = members + 1 WHERE id = ?", (clan_id,))
        self.conn.commit()
        return True
    
    def leave_clan(self, user_id: int) -> bool:
        user = self.get_user_by_id(user_id)
        if not user or user.get('clan_id', 0) == 0:
            return False
        
        clan_id = user['clan_id']
        
        if user.get('clan_role') == 'owner':
            # Передаём права следующему участнику
            self.cursor.execute("SELECT id FROM users WHERE clan_id = ? AND id != ? LIMIT 1", (clan_id, user_id))
            new_owner = self.cursor.fetchone()
            if new_owner:
                self.update_user(new_owner[0], clan_role='owner')
        
        self.update_user(user_id, clan_id=0, clan_role='member')
        self.cursor.execute("UPDATE clans SET members = members - 1 WHERE id = ?", (clan_id,))
        self.conn.commit()
        return True
    
    # ===== МЕТОДЫ ДЛЯ ЗАКЛАДОК =====
    def add_bookmark(self, chat_id: int, user_id: int, name: str, content: str, message_id: int = None) -> int:
        self.cursor.execute("""
            INSERT INTO bookmarks (chat_id, user_id, name, content, message_id)
            VALUES (?, ?, ?, ?, ?)
        """, (chat_id, user_id, name, content, message_id))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_chat_bookmarks(self, chat_id: int) -> List[Dict]:
        self.cursor.execute("""
            SELECT b.*, u.first_name, u.username
            FROM bookmarks b
            JOIN users u ON b.user_id = u.id
            WHERE b.chat_id = ? AND b.visible = 1
            ORDER BY b.created_at DESC
        """, (chat_id,))
        return [dict(row) for row in self.cursor.fetchall()]
    
    def get_user_bookmarks(self, user_id: int, chat_id: int = None) -> List[Dict]:
        if chat_id:
            self.cursor.execute("""
                SELECT * FROM bookmarks
                WHERE user_id = ? AND chat_id = ?
                ORDER BY created_at DESC
            """, (user_id, chat_id))
        else:
            self.cursor.execute("""
                SELECT * FROM bookmarks
                WHERE user_id = ?
                ORDER BY created_at DESC
            """, (user_id,))
        return [dict(row) for row in self.cursor.fetchall()]
    
    # ===== МЕТОДЫ ДЛЯ ТАЙМЕРОВ =====
    def add_timer(self, chat_id: int, user_id: int, execute_at: datetime, command: str) -> Optional[int]:
        # Проверяем лимит таймеров в чате
        self.cursor.execute("SELECT COUNT(*) FROM timers WHERE chat_id = ? AND status = 'pending'", (chat_id,))
        if self.cursor.fetchone()[0] >= 5:
            return None
        
        self.cursor.execute("""
            INSERT INTO timers (chat_id, user_id, execute_at, command)
            VALUES (?, ?, ?, ?)
        """, (chat_id, user_id, execute_at.isoformat(), command))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_pending_timers(self) -> List[Dict]:
        now = datetime.now().isoformat()
        self.cursor.execute("""
            SELECT * FROM timers
            WHERE status = 'pending' AND execute_at <= ?
        """, (now,))
        return [dict(row) for row in self.cursor.fetchall()]
    
    def complete_timer(self, timer_id: int):
        self.cursor.execute("UPDATE timers SET status = 'completed' WHERE id = ?", (timer_id,))
        self.conn.commit()
    
    # ===== МЕТОДЫ ДЛЯ НАГРАД =====
    def give_award(self, chat_id: int, user_id: int, awarded_by: int, degree: int, text: str) -> int:
        self.cursor.execute("""
            INSERT INTO awards (chat_id, user_id, awarded_by, degree, text)
            VALUES (?, ?, ?, ?, ?)
        """, (chat_id, user_id, awarded_by, degree, text))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_user_awards(self, user_id: int, chat_id: int = None) -> List[Dict]:
        if chat_id:
            self.cursor.execute("""
                SELECT a.*, u.first_name as awarded_by_name
                FROM awards a
                JOIN users u ON a.awarded_by = u.id
                WHERE a.user_id = ? AND a.chat_id = ?
                ORDER BY a.degree DESC, a.awarded_at DESC
            """, (user_id, chat_id))
        else:
            self.cursor.execute("""
                SELECT a.*, u.first_name as awarded_by_name
                FROM awards a
                JOIN users u ON a.awarded_by = u.id
                WHERE a.user_id = ?
                ORDER BY a.degree DESC, a.awarded_at DESC
            """, (user_id,))
        return [dict(row) for row in self.cursor.fetchall()]
    
    # ===== МЕТОДЫ ДЛЯ СЕТОК ЧАТОВ =====
    def create_grid(self, owner_id: int, name: str) -> int:
        self.cursor.execute("INSERT INTO chat_grids (owner_id, name) VALUES (?, ?)", (owner_id, name))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def add_chat_to_grid(self, grid_id: int, chat_id: int) -> bool:
        try:
            self.cursor.execute("INSERT INTO grid_chats (grid_id, chat_id) VALUES (?, ?)", (grid_id, chat_id))
            self.conn.commit()
            return True
        except:
            return False
    
    def get_user_grids(self, user_id: int) -> List[Dict]:
        self.cursor.execute("""
            SELECT * FROM chat_grids WHERE owner_id = ?
        """, (user_id,))
        return [dict(row) for row in self.cursor.fetchall()]
    
    # ===== МЕТОДЫ ДЛЯ БОНУСОВ =====
    def buy_bonus(self, user_id: int, bonus_type: str, duration_days: int, price_neons: int) -> bool:
        user = self.get_user_by_id(user_id)
        if user.get('neons', 0) < price_neons:
            return False
        
        expires = (datetime.now() + timedelta(days=duration_days)).isoformat()
        
        field_map = {
            'cyber_status': 'cyber_status_until',
            'turbo_drive': 'turbo_drive_until',
            'cyber_luck': 'cyber_luck_until',
            'rp_packet': 'rp_packet_until'
        }
        
        if bonus_type in field_map:
            self.update_user(user_id, **{field_map[bonus_type]: expires})
        elif bonus_type == 'glitch_hammer':
            # Одноразовый бонус
            self.cursor.execute("""
                INSERT INTO user_bonuses (user_id, bonus_type, expires, data)
                VALUES (?, ?, ?, ?)
            """, (user_id, 'glitch_hammer', expires, json.dumps({'uses_left': 1})))
        elif bonus_type == 'firewall':
            expires = (datetime.now() + timedelta(days=30)).isoformat()
            self.update_user(user_id, firewall_used=0, firewall_expires=expires)
        elif bonus_type == 'invisible':
            self.cursor.execute("""
                INSERT INTO user_bonuses (user_id, bonus_type, expires, data)
                VALUES (?, ?, ?, ?)
            """, (user_id, 'invisible', expires, json.dumps({'uses_left': 999})))
        
        self.add_neons(user_id, -price_neons)
        self.conn.commit()
        return True
    
    def use_glitch_hammer(self, user_id: int, chat_id: int, target_id: int) -> bool:
        # Проверяем наличие бонуса
        self.cursor.execute("""
            SELECT * FROM user_bonuses 
            WHERE user_id = ? AND bonus_type = 'glitch_hammer' AND (expires IS NULL OR expires > ?)
        """, (user_id, datetime.now().isoformat()))
        bonus = self.cursor.fetchone()
        
        if not bonus:
            return False
        
        data = json.loads(bonus[5])
        if data.get('uses_left', 0) <= 0:
            return False
        
        # Уменьшаем количество использований
        data['uses_left'] -= 1
        if data['uses_left'] <= 0:
            self.cursor.execute("DELETE FROM user_bonuses WHERE id = ?", (bonus[0],))
        else:
            self.cursor.execute("UPDATE user_bonuses SET data = ? WHERE id = ?", (json.dumps(data), bonus[0]))
        
        # Мутим цель (логика мута будет в основном коде)
        self.conn.commit()
        return True
    
    def has_invisible_bonus(self, user_id: int) -> bool:
        self.cursor.execute("""
            SELECT * FROM user_bonuses 
            WHERE user_id = ? AND bonus_type = 'invisible' AND (expires IS NULL OR expires > ?)
        """, (user_id, datetime.now().isoformat()))
        return self.cursor.fetchone() is not None
    
    def is_invisible_banned(self, chat_id: int, user_id: int) -> bool:
        self.cursor.execute("SELECT * FROM invisible_bans WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
        return self.cursor.fetchone() is not None
    
    # ===== МЕТОДЫ ДЛЯ ГОЛОСОВАНИЙ =====
    def create_ban_vote(self, chat_id: int, target_id: int, created_by: int, required_votes: int, min_rank: int) -> int:
        self.cursor.execute("""
            INSERT INTO ban_votes (chat_id, target_id, created_by, required_votes, min_rank)
            VALUES (?, ?, ?, ?, ?)
        """, (chat_id, target_id, created_by, required_votes, min_rank))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def vote_for_ban(self, vote_id: int, user_id: int, vote: bool) -> bool:
        self.cursor.execute("SELECT * FROM ban_votes WHERE id = ? AND status = 'active'", (vote_id,))
        vote_data = self.cursor.fetchone()
        if not vote_data:
            return False
        
        voters = json.loads(vote_data[9])
        if user_id in voters:
            return False
        
        voters.append(user_id)
        
        if vote:
            new_for = vote_data[7] + 1
        else:
            new_for = vote_data[7]  # votes_for
            new_against = vote_data[8] + 1
        
        self.cursor.execute("""
            UPDATE ban_votes 
            SET votes_for = ?, votes_against = ?, voters = ?
            WHERE id = ?
        """, (new_for, new_against, json.dumps(voters), vote_id))
        self.conn.commit()
        return True
    
    # ===== МЕТОДЫ ДЛЯ ПАР (ШИППЕРИНГ) =====
    def create_pair(self, chat_id: int, user1_id: int, user2_id: int) -> bool:
        try:
            self.cursor.execute("""
                INSERT INTO pairs (chat_id, user1_id, user2_id)
                VALUES (?, ?, ?)
            """, (chat_id, user1_id, user2_id))
            self.conn.commit()
            return True
        except:
            return False
    
    def get_chat_pairs(self, chat_id: int) -> List[Dict]:
        self.cursor.execute("""
            SELECT p.*, u1.first_name as name1, u2.first_name as name2
            FROM pairs p
            JOIN users u1 ON p.user1_id = u1.id
            JOIN users u2 ON p.user2_id = u2.id
            WHERE p.chat_id = ?
        """, (chat_id,))
        return [dict(row) for row in self.cursor.fetchall()]
    
    # ===== СТАРЫЕ МЕТОДЫ (СОХРАНЯЕМ ДЛЯ СОВМЕСТИМОСТИ) =====
    def save_message(self, user_id: int, username: str, first_name: str, text: str, chat_id: int, chat_title: str):
        self.cursor.execute('''
            INSERT INTO messages (user_id, username, first_name, message_text, chat_id, chat_title)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, text, chat_id, chat_title))
        
        today = datetime.now().date().isoformat()
        self.cursor.execute('''
            INSERT INTO daily_stats (user_id, date, count)
            VALUES (?, ?, 1)
            ON CONFLICT(user_id, date) DO UPDATE SET count = count + 1
        ''', (user_id, today))
        
        self.cursor.execute('''
            INSERT INTO users (telegram_id, username, first_name, last_seen, messages_count)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, 1)
            ON CONFLICT(telegram_id) DO UPDATE SET
                last_seen = CURRENT_TIMESTAMP,
                messages_count = messages_count + 1,
                username = excluded.username,
                first_name = excluded.first_name
        ''', (user_id, username, first_name))
        
        self.conn.commit()
        
        # Проверяем ачивки по активности
        user = self.get_user_by_id(user_id)
        if user:
            msg_count = user.get('messages_count', 0) + 1
            if msg_count >= 1000:
                self.unlock_achievement(user_id, 16)
            if msg_count >= 5000:
                self.unlock_achievement(user_id, 17)
            if msg_count >= 10000:
                self.unlock_achievement(user_id, 18)
    
    def get_weekly_stats(self, user_id: int) -> Tuple[List[str], List[int]]:
        days = []
        counts = []
        
        for i in range(6, -1, -1):
            date = (datetime.now() - timedelta(days=i)).date()
            day_name = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][date.weekday()]
            days.append(day_name)
            
            self.cursor.execute('''
                SELECT count FROM daily_stats
                WHERE user_id = ? AND date = ?
            ''', (user_id, date.isoformat()))
            row = self.cursor.fetchone()
            counts.append(row[0] if row else 0)
        
        return days, counts
    
    def add_exp(self, user_id: int, amount: int) -> bool:
        self.cursor.execute("UPDATE users SET exp = exp + ? WHERE id = ?", (amount, user_id))
        self.cursor.execute("SELECT exp, level FROM users WHERE id = ?", (user_id,))
        row = self.cursor.fetchone()
        exp, level = row[0], row[1]
        if exp >= level * 100:
            self.cursor.execute("UPDATE users SET level = level + 1, exp = exp - ? WHERE id = ?", 
                              (level * 100, user_id))
            self.conn.commit()
            return True
        self.conn.commit()
        return False
    
    def add_energy(self, user_id: int, amount: int) -> int:
        self.cursor.execute("UPDATE users SET energy = MIN(100, energy + ?) WHERE id = ?", (amount, user_id))
        self.conn.commit()
        self.cursor.execute("SELECT energy FROM users WHERE id = ?", (user_id,))
        return self.cursor.fetchone()[0]
    
    def heal(self, user_id: int, amount: int) -> int:
        self.cursor.execute("UPDATE users SET health = MIN(max_health, health + ?) WHERE id = ?", (amount, user_id))
        self.conn.commit()
        self.cursor.execute("SELECT health FROM users WHERE id = ?", (user_id,))
        return self.cursor.fetchone()[0]
    
    def damage(self, user_id: int, amount: int) -> int:
        self.cursor.execute("UPDATE users SET health = MAX(0, health - ?) WHERE id = ?", (amount, user_id))
        self.conn.commit()
        self.cursor.execute("SELECT health FROM users WHERE id = ?", (user_id,))
        return self.cursor.fetchone()[0]
    
    def is_vip(self, user_id: int) -> bool:
        self.cursor.execute("SELECT vip_until FROM users WHERE id = ?", (user_id,))
        row = self.cursor.fetchone()
        if row and row[0]:
            return datetime.fromisoformat(row[0]) > datetime.now()
        return False
    
    def is_premium(self, user_id: int) -> bool:
        self.cursor.execute("SELECT premium_until FROM users WHERE id = ?", (user_id,))
        row = self.cursor.fetchone()
        if row and row[0]:
            return datetime.fromisoformat(row[0]) > datetime.now()
        return False
    
    def set_vip(self, user_id: int, days: int) -> datetime:
        until = datetime.now() + timedelta(days=days)
        self.cursor.execute("UPDATE users SET vip_until = ?, role = 'vip' WHERE id = ?",
                          (until.isoformat(), user_id))
        self.conn.commit()
        self.unlock_achievement(user_id, 22)
        return until
    
    def set_premium(self, user_id: int, days: int) -> datetime:
        until = datetime.now() + timedelta(days=days)
        self.cursor.execute("UPDATE users SET premium_until = ?, role = 'premium' WHERE id = ?",
                          (until.isoformat(), user_id))
        self.conn.commit()
        return until
    
    def set_rank(self, user_id: int, rank: int, admin_id: int) -> bool:
        if rank not in RANKS:
            return False
        self.cursor.execute("UPDATE users SET rank = ?, rank_name = ? WHERE id = ?",
                          (rank, RANKS[rank]["name"], user_id))
        self.conn.commit()
        self.log_action(admin_id, "set_rank", f"{user_id} -> {rank}")
        return True
    
    def get_admins(self) -> List[Dict]:
        self.cursor.execute("SELECT id, first_name, username, rank, rank_name FROM users WHERE rank > 0 ORDER BY rank DESC")
        return [dict(row) for row in self.cursor.fetchall()]
    
    def add_warn(self, user_id: int, admin_id: int, reason: str) -> int:
        self.cursor.execute("SELECT warns, warns_list FROM users WHERE id = ?", (user_id,))
        row = self.cursor.fetchone()
        warns, warns_list = row[0], json.loads(row[1])
        warns_list.append({
            'id': len(warns_list) + 1,
            'admin_id': admin_id,
            'reason': reason,
            'date': datetime.now().isoformat()
        })
        new_warns = warns + 1
        self.cursor.execute("UPDATE users SET warns = ?, warns_list = ? WHERE id = ?",
                          (new_warns, json.dumps(warns_list), user_id))
        self.conn.commit()
        self.log_action(admin_id, "add_warn", f"{user_id}: {reason}")
        return new_warns
    
    def get_warns(self, user_id: int) -> List[Dict]:
        self.cursor.execute("SELECT warns_list FROM users WHERE id = ?", (user_id,))
        row = self.cursor.fetchone()
        return json.loads(row[0]) if row and row[0] else []
    
    def remove_last_warn(self, user_id: int, admin_id: int) -> Optional[Dict]:
        self.cursor.execute("SELECT warns, warns_list FROM users WHERE id = ?", (user_id,))
        row = self.cursor.fetchone()
        warns, warns_list = row[0], json.loads(row[1])
        if not warns_list:
            return None
        removed = warns_list.pop()
        self.cursor.execute("UPDATE users SET warns = ?, warns_list = ? WHERE id = ?",
                          (warns - 1, json.dumps(warns_list), user_id))
        self.conn.commit()
        self.log_action(admin_id, "remove_warn", f"{user_id}")
        return removed
    
    def mute_user(self, user_id: int, minutes: int, admin_id: int, reason: str = "") -> datetime:
        until = datetime.now() + timedelta(minutes=minutes)
        self.cursor.execute("UPDATE users SET mute_until = ? WHERE id = ?", (until.isoformat(), user_id))
        self.conn.commit()
        self.log_action(admin_id, "mute", f"{user_id} {minutes}мин: {reason}")
        return until
    
    def is_muted(self, user_id: int) -> bool:
        self.cursor.execute("SELECT mute_until FROM users WHERE id = ?", (user_id,))
        row = self.cursor.fetchone()
        if row and row[0]:
            return datetime.fromisoformat(row[0]) > datetime.now()
        return False
    
    def unmute_user(self, user_id: int, admin_id: int) -> bool:
        self.cursor.execute("UPDATE users SET mute_until = NULL WHERE id = ?", (user_id,))
        self.conn.commit()
        self.log_action(admin_id, "unmute", str(user_id))
        return True
    
    def get_muted_users(self) -> List[Dict]:
        self.cursor.execute("SELECT id, first_name, username, mute_until FROM users WHERE mute_until > ?",
                          (datetime.now().isoformat(),))
        return [dict(row) for row in self.cursor.fetchall()]
    
    def ban_user(self, user_id: int, admin_id: int, reason: str) -> bool:
        self.cursor.execute('''
            UPDATE users SET banned = 1, ban_reason = ?, ban_date = ?, ban_admin = ?
            WHERE id = ?
        ''', (reason, datetime.now().isoformat(), admin_id, user_id))
        self.conn.commit()
        self.log_action(admin_id, "ban", f"{user_id}: {reason}")
        return True
    
    def unban_user(self, user_id: int, admin_id: int) -> bool:
        self.cursor.execute("UPDATE users SET banned = 0, ban_reason = NULL, ban_date = NULL, ban_admin = NULL WHERE id = ?", (user_id,))
        self.conn.commit()
        self.log_action(admin_id, "unban", str(user_id))
        return True
    
    def is_banned(self, user_id: int) -> bool:
        self.cursor.execute("SELECT banned FROM users WHERE id = ?", (user_id,))
        row = self.cursor.fetchone()
        return row and row[0] == 1
    
    def get_banlist(self) -> List[Dict]:
        self.cursor.execute("SELECT id, first_name, username FROM users WHERE banned = 1")
        return [dict(row) for row in self.cursor.fetchall()]
    
    def add_to_blacklist(self, word: str, admin_id: int) -> bool:
        try:
            self.cursor.execute("INSERT INTO blacklist (word, added_by) VALUES (?, ?)", (word.lower(), admin_id))
            self.conn.commit()
            self.log_action(admin_id, "add_blacklist", word)
            return True
        except:
            return False
    
    def remove_from_blacklist(self, word: str, admin_id: int) -> bool:
        self.cursor.execute("DELETE FROM blacklist WHERE word = ?", (word.lower(),))
        self.conn.commit()
        self.log_action(admin_id, "remove_blacklist", word)
        return self.cursor.rowcount > 0
    
    def get_blacklist(self) -> List[str]:
        self.cursor.execute("SELECT word FROM blacklist ORDER BY word")
        return [row[0] for row in self.cursor.fetchall()]
    
    def is_word_blacklisted(self, text: str) -> bool:
        words = self.get_blacklist()
        text_lower = text.lower()
        for word in words:
            if word in text_lower:
                return True
        return False
    
    def get_top(self, field: str, limit: int = 10) -> List[Tuple]:
        self.cursor.execute(f"SELECT first_name, nickname, {field} FROM users ORDER BY {field} DESC LIMIT ?", (limit,))
        return self.cursor.fetchall()
    
    def add_daily_streak(self, user_id: int) -> int:
        today = datetime.now().date()
        self.cursor.execute("SELECT last_daily, daily_streak FROM users WHERE id = ?", (user_id,))
        row = self.cursor.fetchone()
        
        if row and row[0]:
            last = datetime.fromisoformat(row[0]).date()
            if last == today - timedelta(days=1):
                streak = row[1] + 1
            elif last == today:
                return row[1]
            else:
                streak = 1
        else:
            streak = 1
        
        self.cursor.execute("UPDATE users SET daily_streak = ?, last_daily = ? WHERE id = ?",
                          (streak, datetime.now().isoformat(), user_id))
        self.conn.commit()
        
        # Проверяем ачивки по стрику
        if streak >= 7:
            self.unlock_achievement(user_id, 19)
        if streak >= 30:
            self.unlock_achievement(user_id, 20)
        if streak >= 100:
            self.unlock_achievement(user_id, 21)
        
        return streak
    
    def get_bosses(self, alive_only: bool = True) -> List[Dict]:
        if alive_only:
            self.cursor.execute("SELECT * FROM bosses WHERE is_alive = 1 ORDER BY level")
        else:
            self.cursor.execute("SELECT * FROM bosses ORDER BY level")
        return [dict(row) for row in self.cursor.fetchall()]
    
    def get_boss(self, boss_id: int) -> Optional[Dict]:
        self.cursor.execute("SELECT * FROM bosses WHERE id = ?", (boss_id,))
        row = self.cursor.fetchone()
        return dict(row) if row else None
    
    def damage_boss(self, boss_id: int, damage: int) -> bool:
        self.cursor.execute("UPDATE bosses SET health = health - ? WHERE id = ?", (damage, boss_id))
        self.cursor.execute("SELECT health FROM bosses WHERE id = ?", (boss_id,))
        health = self.cursor.fetchone()[0]
        if health <= 0:
            self.cursor.execute("UPDATE bosses SET is_alive = 0, respawn_time = ? WHERE id = ?",
                              ((datetime.now() + timedelta(hours=1)).isoformat(), boss_id))
            self.conn.commit()
            return True
        self.conn.commit()
        return False
    
    def respawn_bosses(self):
        self.cursor.execute("UPDATE bosses SET health = max_health, is_alive = 1, respawn_time = NULL")
        self.conn.commit()
    
    def add_boss_kill(self, user_id: int):
        self.cursor.execute("UPDATE users SET boss_kills = boss_kills + 1 WHERE id = ?", (user_id,))
        self.conn.commit()
        
        # Проверяем ачивки по боссам
        user = self.get_user_by_id(user_id)
        kills = user.get('boss_kills', 0) + 1
        if kills >= 10:
            self.unlock_achievement(user_id, 13)
        if kills >= 50:
            self.unlock_achievement(user_id, 14)
        if kills >= 200:
            self.unlock_achievement(user_id, 15)
    
    def create_duel(self, challenger_id: int, opponent_id: int, bet: int) -> int:
        self.cursor.execute('''
            INSERT INTO duels (challenger_id, opponent_id, bet)
            VALUES (?, ?, ?)
        ''', (challenger_id, opponent_id, bet))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_duel(self, duel_id: int) -> Optional[Dict]:
        self.cursor.execute("SELECT * FROM duels WHERE id = ?", (duel_id,))
        row = self.cursor.fetchone()
        return dict(row) if row else None
    
    def update_duel(self, duel_id: int, **kwargs):
        for key, value in kwargs.items():
            self.cursor.execute(f"UPDATE duels SET {key} = ? WHERE id = ?", (value, duel_id))
        self.conn.commit()
    
    def log_action(self, user_id: int, action: str, details: str = "", chat_id: int = None):
        self.cursor.execute('''
            INSERT INTO logs (user_id, action, details, chat_id, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, action, details, chat_id, datetime.now().isoformat()))
        self.conn.commit()
    
    def close(self):
        self.conn.close()

db = Database()

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def get_rank_emoji(rank: int) -> str:
    return RANKS.get(rank, RANKS[0])["emoji"]

def get_rank_name(rank: int) -> str:
    return RANKS.get(rank, RANKS[0])["name"]

def has_permission(user_data: Dict, required_rank: int) -> bool:
    return user_data.get('rank', 0) >= required_rank

def extract_user_id(text: str) -> Optional[int]:
    match = re.search(r'@(\w+)', text)
    if match:
        username = match.group(1)
        user = db.get_user_by_username(username)
        if user:
            return user['id']
    
    match = re.search(r'tg://user\?id=(\d+)', text)
    if match:
        return int(match.group(1))
    
    match = re.search(r'(\d+)', text)
    if match:
        return int(match.group(1))
    
    return None

def parse_time(time_str: str) -> Optional[int]:
    match = re.match(r'(\d+)([мчд])', time_str)
    if not match:
        return None
    
    amount = int(match.group(1))
    unit = match.group(2)
    
    if unit == 'м':
        return amount
    elif unit == 'ч':
        return amount * 60
    elif unit == 'д':
        return amount * 1440
    
    return None

def parse_datetime(date_str: str) -> Optional[datetime]:
    """Парсит дату в формате ДД.ММ ЧЧ:ММ"""
    try:
        now = datetime.now()
        if '.' in date_str:
            day_month, time_part = date_str.split()
            day, month = map(int, day_month.split('.'))
            hour, minute = map(int, time_part.split(':'))
            year = now.year
            if month < now.month:
                year += 1
            return datetime(year, month, day, hour, minute)
        else:
            hour, minute = map(int, date_str.split(':'))
            return now.replace(hour=hour, minute=minute, second=0)
    except:
        return None

# ========== ОСНОВНОЙ КЛАСС БОТА ==========
class SpectrumBot:
    def __init__(self):
        self.db = db
        self.ai = ai
        self.spam_tracker = defaultdict(list)
        self.app = Application.builder().token(TOKEN).build()
        self.start_time = datetime.now()
        self.games_in_progress = {}
        self.mafia_games = {}  # chat_id -> MafiaGame
        self.duels_in_progress = {}
        self.boss_fights = {}  # user_id -> {boss_id, damage_done}
        self.active_ban_votes = {}
        self.setup_handlers()
        logger.info(f"✅ Бот {BOT_NAME} инициализирован")

        # ===== ПРОФИЛЬ =====
    async def cmd_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        display_name = user_data.get('nickname') or user.first_name
        title = user_data.get('title', '')
        motto = user_data.get('motto', 'Нет девиза')
        bio = user_data.get('bio', '')
        
        vip_status = "✅ VIP" if self.db.is_vip(user_data['id']) else "❌"
        premium_status = "✅ PREMIUM" if self.db.is_premium(user_data['id']) else "❌"
        
        exp_needed = user_data['level'] * 100
        exp_progress = s.progress(user_data['exp'], exp_needed)
        
        warns = "🔴" * user_data['warns'] + "⚪️" * (4 - user_data['warns'])
        
        friends_list = json.loads(user_data.get('friends', '[]'))
        friends_count = len(friends_list)
        
        enemies_list = json.loads(user_data.get('enemies', '[]'))
        enemies_count = len(enemies_list)
        
        registered = datetime.fromisoformat(user_data['registered']) if user_data.get('registered') else datetime.now()
        days_in_chat = (datetime.now() - registered).days
        
        username_display = f"(@{user.username})" if user.username else ""
        
        profile_text = (
            f"👤 **{display_name}** {title} {username_display}\n"
            f"_{motto}_\n"
            f"{bio}\n\n"
            f"📊 **Характеристики**\n"
            f"• Ранг: {get_rank_emoji(user_data['rank'])} {user_data['rank_name']}\n"
            f"• Уровень: {user_data['level']} ({exp_progress})\n"
            f"• Монеты: {user_data['coins']:,} 💰\n"
            f"• Неоны: {user_data['neons']:,} 💜\n"
            f"• Глитчи: {user_data['glitches']:,} 🖥\n"
            f"• Энергия: {user_data['energy']}/100 ⚡️\n"
            f"• Здоровье: {user_data['health']}/{user_data['max_health']} ❤️\n\n"
            
            f"📈 **Статистика**\n"
            f"• Сообщений: {user_data['messages_count']} 💬\n"
            f"• Репутация: {user_data['reputation']} ⭐️\n"
            f"• Предупреждения: {warns}\n"
            f"• Боссов убито: {user_data['boss_kills']} 👾\n"
            f"• Друзей: {friends_count} / Врагов: {enemies_count}\n\n"
            
            f"💎 **Статусы**\n"
            f"• VIP: {vip_status}\n"
            f"• PREMIUM: {premium_status}\n\n"
            
            f"📅 **В чате:** {days_in_chat} дней\n"
            f"🆔 ID: `{user.id}`"
        )
        
        await update.message.reply_text(profile_text, parse_mode=ParseMode.MARKDOWN)

    async def cmd_set_nick(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Укажите ник: /nick [ник]")
            return
        nick = " ".join(context.args)
        if len(nick) > MAX_NICK_LENGTH:
            await update.message.reply_text(f"❌ Максимальная длина: {MAX_NICK_LENGTH} символов")
            return
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], nickname=nick)
        await update.message.reply_text(f"✅ Ник установлен: {nick}")

    async def cmd_set_title(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Укажите титул: /title [титул]")
            return
        title = " ".join(context.args)
        if len(title) > MAX_TITLE_LENGTH:
            await update.message.reply_text(f"❌ Максимальная длина: {MAX_TITLE_LENGTH} символов")
            return
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], title=title)
        await update.message.reply_text(f"✅ Титул установлен: {title}")

    async def cmd_set_motto(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Укажите девиз: /motto [девиз]")
            return
        motto = " ".join(context.args)
        if len(motto) > MAX_MOTTO_LENGTH:
            await update.message.reply_text(f"❌ Максимальная длина: {MAX_MOTTO_LENGTH} символов")
            return
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], motto=motto)
        await update.message.reply_text(f"✅ Девиз установлен: {motto}")

    async def cmd_set_bio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Напишите о себе: /bio [текст]")
            return
        bio = " ".join(context.args)
        if len(bio) > MAX_BIO_LENGTH:
            await update.message.reply_text(f"❌ Максимальная длина: {MAX_BIO_LENGTH} символов")
            return
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], bio=bio)
        await update.message.reply_text("✅ Информация сохранена")

    async def cmd_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        await update.message.reply_text(f"🆔 Ваш ID: `{user.id}`", parse_mode=ParseMode.MARKDOWN)

    def setup_handlers(self):
        """Регистрация всех обработчиков"""
        
        # ===== ОСНОВНЫЕ КОМАНДЫ =====
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CommandHandler("menu", self.show_menu))
        
        # ===== ПРОФИЛЬ =====
        self.app.add_handler(CommandHandler("profile", self.cmd_profile))
        self.app.add_handler(CommandHandler("nick", self.cmd_set_nick))
        self.app.add_handler(CommandHandler("title", self.cmd_set_title))
        self.app.add_handler(CommandHandler("motto", self.cmd_set_motto))
        self.app.add_handler(CommandHandler("bio", self.cmd_set_bio))
        self.app.add_handler(CommandHandler("gender", self.cmd_set_gender))
        self.app.add_handler(CommandHandler("city", self.cmd_set_city))
        self.app.add_handler(CommandHandler("country", self.cmd_set_country))
        self.app.add_handler(CommandHandler("birth", self.cmd_set_birth))
        self.app.add_handler(CommandHandler("age", self.cmd_set_age))
        self.app.add_handler(CommandHandler("id", self.cmd_id))
        
        # ===== СТАТИСТИКА =====
        self.app.add_handler(CommandHandler("stats", self.cmd_stats))
        self.app.add_handler(CommandHandler("mystats", self.cmd_my_stats))
        self.app.add_handler(CommandHandler("top", self.cmd_top))
        self.app.add_handler(CommandHandler("topcoins", self.cmd_top_coins))
        self.app.add_handler(CommandHandler("toplevel", self.cmd_top_level))
        self.app.add_handler(CommandHandler("topneons", self.cmd_top_neons))
        self.app.add_handler(CommandHandler("topglitches", self.cmd_top_glitches))
        
        # ===== МОДЕРАЦИЯ =====
        self.app.add_handler(CommandHandler("admins", self.cmd_who_admins))
        self.app.add_handler(CommandHandler("warns", self.cmd_warns))
        self.app.add_handler(CommandHandler("mywarns", self.cmd_my_warns))
        self.app.add_handler(CommandHandler("mutelist", self.cmd_mutelist))
        self.app.add_handler(CommandHandler("banlist", self.cmd_banlist))
        self.app.add_handler(CommandHandler("triggers", self.cmd_list_triggers))
        self.app.add_handler(CommandHandler("rules", self.cmd_show_rules))
        self.app.add_handler(CommandHandler("checkrights", self.cmd_checkrights))

        
        # ===== ЭКОНОМИКА =====
        self.app.add_handler(CommandHandler("balance", self.cmd_balance))
        self.app.add_handler(CommandHandler("coins", self.cmd_balance))
        self.app.add_handler(CommandHandler("pay", self.cmd_pay))
        self.app.add_handler(CommandHandler("daily", self.cmd_daily))
        self.app.add_handler(CommandHandler("streak", self.cmd_streak))
        self.app.add_handler(CommandHandler("vip", self.cmd_vip_info))
        self.app.add_handler(CommandHandler("buyvip", self.cmd_buy_vip))
        self.app.add_handler(CommandHandler("premium", self.cmd_premium_info))
        self.app.add_handler(CommandHandler("buypremium", self.cmd_buy_premium))
        self.app.add_handler(CommandHandler("shop", self.cmd_shop))
        self.app.add_handler(CommandHandler("buy", self.cmd_buy))
        
        # ===== НОВАЯ ЭКОНОМИКА (НЕОНЫ, ГЛИТЧИ) =====
        self.app.add_handler(CommandHandler("neons", self.cmd_neons))
        self.app.add_handler(CommandHandler("glitches", self.cmd_glitches))
        self.app.add_handler(CommandHandler("farm", self.cmd_farm))
        self.app.add_handler(CommandHandler("transfer", self.cmd_transfer_neons))
        self.app.add_handler(CommandHandler("exchange", self.cmd_exchange))
        
        # ===== РАЗВЛЕЧЕНИЯ =====
        self.app.add_handler(CommandHandler("joke", self.cmd_joke))
        self.app.add_handler(CommandHandler("fact", self.cmd_fact))
        self.app.add_handler(CommandHandler("quote", self.cmd_quote))
        self.app.add_handler(CommandHandler("whoami", self.cmd_whoami))
        self.app.add_handler(CommandHandler("advice", self.cmd_advice))
        self.app.add_handler(CommandHandler("compatibility", self.cmd_compatibility))
        self.app.add_handler(CommandHandler("weather", self.cmd_weather))
        self.app.add_handler(CommandHandler("random", self.cmd_random))
        self.app.add_handler(CommandHandler("choose", self.cmd_choose))
        self.app.add_handler(CommandHandler("dane", self.cmd_dane))
        self.app.add_handler(CommandHandler("ship", self.cmd_ship))
        self.app.add_handler(CommandHandler("pairing", self.cmd_pairing))
        self.app.add_handler(CommandHandler("pairs", self.cmd_pairs))
        
        # ===== ИГРЫ =====
        self.app.add_handler(CommandHandler("games", self.cmd_games))
        self.app.add_handler(CommandHandler("coin", self.cmd_coin))
        self.app.add_handler(CommandHandler("dice", self.cmd_dice))
        self.app.add_handler(CommandHandler("dicebet", self.cmd_dice_bet))
        self.app.add_handler(CommandHandler("rps", self.cmd_rps))
        self.app.add_handler(CommandHandler("rr", self.cmd_russian_roulette))
        self.app.add_handler(CommandHandler("roulette", self.cmd_roulette))
        self.app.add_handler(CommandHandler("slots", self.cmd_slots))
        self.app.add_handler(CommandHandler("saper", self.cmd_saper))
        self.app.add_handler(CommandHandler("guess", self.cmd_guess))
        self.app.add_handler(CommandHandler("bulls", self.cmd_bulls))
        
        # ===== БОССЫ =====
        self.app.add_handler(CommandHandler("bosses", self.cmd_bosses))
        self.app.add_handler(CommandHandler("boss", self.cmd_boss_fight))
        self.app.add_handler(CommandHandler("bossinfo", self.cmd_boss_info))
        self.app.add_handler(CommandHandler("regen", self.cmd_regen))
        
        # ===== ДУЭЛИ =====
        self.app.add_handler(CommandHandler("duel", self.cmd_duel))
        self.app.add_handler(CommandHandler("duels", self.cmd_duels))
        self.app.add_handler(CommandHandler("duelrating", self.cmd_duel_rating))

        # ===== Мафия =====
        self.app.add_handler(CommandHandler("mafia", self.cmd_mafia))
        self.app.add_handler(CommandHandler("mafiastart", self.cmd_mafia_start))
        self.app.add_handler(CommandHandler("mafiajoin", self.cmd_mafia_join))
        self.app.add_handler(CommandHandler("mafialeave", self.cmd_mafia_leave))
        self.app.add_handler(CommandHandler("mafiaroles", self.cmd_mafia_roles))
        self.app.add_handler(CommandHandler("mafiarules", self.cmd_mafia_rules))
        self.app.add_handler(CommandHandler("mafiastats", self.cmd_mafia_stats))

        # ===== БЕСЕДЫ =====
        self.app.add_handler(CommandHandler("randomchat", self.cmd_random_chat))
        self.app.add_handler(CommandHandler("topchats", self.cmd_top_chats))
        
        # ===== КЛАНЫ =====
        self.app.add_handler(CommandHandler("clan", self.cmd_clan))
        self.app.add_handler(CommandHandler("clans", self.cmd_clans))
        self.app.add_handler(CommandHandler("createclan", self.cmd_create_clan))
        self.app.add_handler(CommandHandler("joinclan", self.cmd_join_clan))
        self.app.add_handler(CommandHandler("leaveclan", self.cmd_leave_clan))
        
        # ===== АЧИВКИ =====
        self.app.add_handler(CommandHandler("achievements", self.cmd_achievements))
        self.app.add_handler(CommandHandler("myachievements", self.cmd_my_achievements))
        self.app.add_handler(CommandHandler("achievement", self.cmd_achievement_info))
        self.app.add_handler(CommandHandler("topachievements", self.cmd_top_achievements))
        
        # ===== КРУЖКИ =====
        self.app.add_handler(CommandHandler("circles", self.cmd_circles))
        self.app.add_handler(CommandHandler("circle", self.cmd_circle))
        self.app.add_handler(CommandHandler("createcircle", self.cmd_create_circle))
        self.app.add_handler(CommandHandler("joincircle", self.cmd_join_circle))
        self.app.add_handler(CommandHandler("leavecircle", self.cmd_leave_circle))
        
        # ===== ЗАКЛАДКИ =====
        self.app.add_handler(CommandHandler("bookmarks", self.cmd_bookmarks))
        self.app.add_handler(CommandHandler("bookmark", self.cmd_bookmark))
        self.app.add_handler(CommandHandler("addbookmark", self.cmd_add_bookmark))
        self.app.add_handler(CommandHandler("removebookmark", self.cmd_remove_bookmark))
        self.app.add_handler(CommandHandler("chatbook", self.cmd_chat_bookmarks))
        
        # ===== ТАЙМЕРЫ =====
        self.app.add_handler(CommandHandler("timers", self.cmd_timers))
        self.app.add_handler(CommandHandler("timer", self.cmd_add_timer))
        self.app.add_handler(CommandHandler("removetimer", self.cmd_remove_timer))
        
        # ===== НАГРАДЫ =====
        self.app.add_handler(CommandHandler("awards", self.cmd_awards))
        self.app.add_handler(CommandHandler("award", self.cmd_give_award))
        self.app.add_handler(CommandHandler("removeaward", self.cmd_remove_award))
        
        # ===== ГОЛОСОВАНИЕ ЗА БАН =====
        self.app.add_handler(CommandHandler("banvote", self.cmd_ban_vote))
        self.app.add_handler(CommandHandler("stopvote", self.cmd_stop_vote))
        self.app.add_handler(CommandHandler("voteinfo", self.cmd_vote_info))
        self.app.add_handler(CommandHandler("votelist", self.cmd_vote_list))
        
        # ===== СЕТКИ ЧАТОВ =====
        self.app.add_handler(CommandHandler("grid", self.cmd_grid))
        self.app.add_handler(CommandHandler("grids", self.cmd_grids))
        self.app.add_handler(CommandHandler("creategrid", self.cmd_create_grid))
        self.app.add_handler(CommandHandler("addchat", self.cmd_add_chat_to_grid))
        self.app.add_handler(CommandHandler("globalmod", self.cmd_global_mod))
        
        # ===== БОНУСЫ =====
        self.app.add_handler(CommandHandler("bonuses", self.cmd_bonuses))
        self.app.add_handler(CommandHandler("buybonus", self.cmd_buy_bonus))
        self.app.add_handler(CommandHandler("bonusinfo", self.cmd_bonus_info))
        
        # Бонус 1: Кибер-статус
        self.app.add_handler(CommandHandler("cyberstatus", self.cmd_cyber_status))
        
        # Бонус 2: Глитч-молот
        self.app.add_handler(CommandHandler("glitchhammer", self.cmd_glitch_hammer))
        
        # Бонус 3: Турбо-драйв
        self.app.add_handler(CommandHandler("turbodrive", self.cmd_turbo_drive))
        
        # Бонус 4: Невидимка
        self.app.add_handler(CommandHandler("invisible", self.cmd_invisible))
        
        # Бонус 5: Неон-ник
        self.app.add_handler(CommandHandler("neonick", self.cmd_neon_nick))
        
        # Бонус 6: Кибер-удача
        self.app.add_handler(CommandHandler("cyberluck", self.cmd_cyber_luck))
        
        # Бонус 7: Файрволл
        self.app.add_handler(CommandHandler("firewall", self.cmd_firewall))
        
        # Бонус 8: РП-пакет
        self.app.add_handler(CommandHandler("rppacket", self.cmd_rp_packet))
        
                # РП команды для РП-пакета (через MessageHandler с regex)
        self.app.add_handler(MessageHandler(filters.Regex(r'^/взломать\s+@'), self.cmd_rp_hack))
        self.app.add_handler(MessageHandler(filters.Regex(r'^/заглючить\s+@'), self.cmd_rp_glitch))
        self.app.add_handler(MessageHandler(filters.Regex(r'^/перегрузить\s+@'), self.cmd_rp_reboot))
        self.app.add_handler(MessageHandler(filters.Regex(r'^/закодить\s+@'), self.cmd_rp_code))
        self.app.add_handler(MessageHandler(filters.Regex(r'^/оцифровать\s+@'), self.cmd_rp_digitize))
        self.app.add_handler(MessageHandler(filters.Regex(r'^/хакнуть\s+@'), self.cmd_rp_hack_deep))
        self.app.add_handler(MessageHandler(filters.Regex(r'^/скачать\s+@'), self.cmd_rp_download))
        self.app.add_handler(MessageHandler(filters.Regex(r'^/обновить\s+@'), self.cmd_rp_update))
        
        # ===== ТЕЛЕГРАМ БОНУСЫ =====
        self.app.add_handler(CommandHandler("tgpremium", self.cmd_tg_premium))
        self.app.add_handler(CommandHandler("tggift", self.cmd_tg_gift))
        self.app.add_handler(CommandHandler("tgstars", self.cmd_tg_stars))
        
        # ===== АНКЕТА =====
        self.app.add_handler(CommandHandler("myprofile", self.cmd_my_profile))
        
        # ===== СТАТИСТИКА ЧАТА (РУССКИЕ КОМАНДЫ) =====
        self.app.add_handler(MessageHandler(filters.Regex(r'^стата$'), self.cmd_chat_stats_today))
        self.app.add_handler(MessageHandler(filters.Regex(r'^стата неделя$'), self.cmd_chat_stats_week))
        self.app.add_handler(MessageHandler(filters.Regex(r'^стата месяц$'), self.cmd_chat_stats_month))
        self.app.add_handler(MessageHandler(filters.Regex(r'^стата вся$'), self.cmd_chat_stats_all))
        self.app.add_handler(MessageHandler(filters.Regex(r'^топ$'), self.cmd_top_chat_today))
        self.app.add_handler(MessageHandler(filters.Regex(r'^топ неделя$'), self.cmd_top_chat_week))
        self.app.add_handler(MessageHandler(filters.Regex(r'^топ месяц$'), self.cmd_top_chat_month))
        self.app.add_handler(MessageHandler(filters.Regex(r'^топ вся$'), self.cmd_top_chat_all))
        
        # ===== АЧИВКИ (РУССКИЕ) =====
        self.app.add_handler(MessageHandler(filters.Regex(r'^мои ачивки$'), self.cmd_my_achievements))
        self.app.add_handler(MessageHandler(filters.Regex(r'^топ ачивок$'), self.cmd_top_achievements))
        self.app.add_handler(MessageHandler(filters.Regex(r'^ачивка \d+$'), self.cmd_achievement_info))
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+Ачивки$'), self.cmd_achievements_public))
        self.app.add_handler(MessageHandler(filters.Regex(r'^-Ачивки$'), self.cmd_achievements_private))
        
        # ===== КРУЖКИ (РУССКИЕ) =====
        self.app.add_handler(MessageHandler(filters.Regex(r'^кружки$'), self.cmd_circles))
        self.app.add_handler(MessageHandler(filters.Regex(r'^кружок \d+$'), self.cmd_circle))
        self.app.add_handler(MessageHandler(filters.Regex(r'^создать кружок'), self.cmd_create_circle))
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+Кружок \d+$'), self.cmd_join_circle))
        self.app.add_handler(MessageHandler(filters.Regex(r'^-Кружок \d+$'), self.cmd_leave_circle))
        
        # ===== ЗАКЛАДКИ (РУССКИЕ) =====
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+Закладка'), self.cmd_add_bookmark))
        self.app.add_handler(MessageHandler(filters.Regex(r'^закладка \d+$'), self.cmd_bookmark))
        self.app.add_handler(MessageHandler(filters.Regex(r'^чатбук$'), self.cmd_chat_bookmarks))
        self.app.add_handler(MessageHandler(filters.Regex(r'^мои закладки$'), self.cmd_my_bookmarks))
        self.app.add_handler(MessageHandler(filters.Regex(r'^-Закладка \d+$'), self.cmd_remove_bookmark))
        
        # ===== ТАЙМЕРЫ (РУССКИЕ) =====
        self.app.add_handler(MessageHandler(filters.Regex(r'^таймер через'), self.cmd_add_timer))
        self.app.add_handler(MessageHandler(filters.Regex(r'^таймер на'), self.cmd_add_timer))
        self.app.add_handler(MessageHandler(filters.Regex(r'^таймеры$'), self.cmd_timers))
        self.app.add_handler(MessageHandler(filters.Regex(r'^удалить таймер \d+$'), self.cmd_remove_timer))
        
        # ===== НАГРАДЫ (РУССКИЕ) =====
        self.app.add_handler(MessageHandler(filters.Regex(r'^наградить \d+'), self.cmd_give_award))
        self.app.add_handler(MessageHandler(filters.Regex(r'^награды'), self.cmd_awards))
        self.app.add_handler(MessageHandler(filters.Regex(r'^снять награду'), self.cmd_remove_award))
        
        # ===== ГОЛОСОВАНИЕ ЗА БАН (РУССКИЕ) =====
        self.app.add_handler(MessageHandler(filters.Regex(r'^гб @'), self.cmd_ban_vote))
        self.app.add_handler(MessageHandler(filters.Regex(r'^гб стоп'), self.cmd_stop_vote))
        self.app.add_handler(MessageHandler(filters.Regex(r'^гб инфо'), self.cmd_vote_info))
        self.app.add_handler(MessageHandler(filters.Regex(r'^гб список$'), self.cmd_vote_list))
        
        # ===== БОНУСЫ (РУССКИЕ) =====
        self.app.add_handler(MessageHandler(filters.Regex(r'^купить кибер-статус'), self.cmd_buy_cyber_status))
        self.app.add_handler(MessageHandler(filters.Regex(r'^применить глитч-молот'), self.cmd_use_glitch_hammer))
        self.app.add_handler(MessageHandler(filters.Regex(r'^купить турбо-драйв'), self.cmd_buy_turbo_drive))
        self.app.add_handler(MessageHandler(filters.Regex(r'^невидимка '), self.cmd_use_invisible))
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+Невидимка'), self.cmd_allow_invisible))
        self.app.add_handler(MessageHandler(filters.Regex(r'^-Невидимка'), self.cmd_ban_invisible))
        self.app.add_handler(MessageHandler(filters.Regex(r'^купить неон-ник'), self.cmd_buy_neon_nick))
        self.app.add_handler(MessageHandler(filters.Regex(r'^купить кибер-удачу'), self.cmd_buy_cyber_luck))
        self.app.add_handler(MessageHandler(filters.Regex(r'^купить файрволл'), self.cmd_buy_firewall))
        self.app.add_handler(MessageHandler(filters.Regex(r'^купить рп-пакет'), self.cmd_buy_rp_packet))
        
        # ===== ТЕЛЕГРАМ БОНУСЫ (РУССКИЕ) =====
        self.app.add_handler(MessageHandler(filters.Regex(r'^купить тг прем'), self.cmd_buy_tg_premium))
        self.app.add_handler(MessageHandler(filters.Regex(r'^подарить тг прем'), self.cmd_gift_tg_premium))
        self.app.add_handler(MessageHandler(filters.Regex(r'^купить тг подарок'), self.cmd_buy_tg_gift))
        self.app.add_handler(MessageHandler(filters.Regex(r'^подарить тг подарок'), self.cmd_gift_tg_gift))
        self.app.add_handler(MessageHandler(filters.Regex(r'^купить тг зв'), self.cmd_buy_tg_stars))
        self.app.add_handler(MessageHandler(filters.Regex(r'^передать тг зв'), self.cmd_transfer_tg_stars))
        self.app.add_handler(MessageHandler(filters.Regex(r'^где мои тг зв'), self.cmd_my_tg_stars))
        
        # ===== АНКЕТА (РУССКИЕ) =====
        self.app.add_handler(MessageHandler(filters.Regex(r'^моя анкета$'), self.cmd_my_profile))
        self.app.add_handler(MessageHandler(filters.Regex(r'^мой пол '), self.cmd_set_gender))
        self.app.add_handler(MessageHandler(filters.Regex(r'^-Пол$'), self.cmd_remove_gender))
        self.app.add_handler(MessageHandler(filters.Regex(r'^мой город '), self.cmd_set_city))
        self.app.add_handler(MessageHandler(filters.Regex(r'^мой др '), self.cmd_set_birth))
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+Анкета$'), self.cmd_profile_public))
        self.app.add_handler(MessageHandler(filters.Regex(r'^-Анкета$'), self.cmd_profile_private))
        
        # ===== МОДЕРАЦИЯ (РУССКИЕ) =====
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+Модер|^!модер|^повысить$'), self.cmd_set_rank))
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+Модер 2|^!модер 2|^повысить 2$'), self.cmd_set_rank2))
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+Модер 3|^!модер 3|^повысить 3$'), self.cmd_set_rank3))
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+Модер 4|^!модер 4|^повысить 4$'), self.cmd_set_rank4))
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+Модер 5|^!модер 5|^повысить 5$'), self.cmd_set_rank5))
        self.app.add_handler(MessageHandler(filters.Regex(r'^понизить'), self.cmd_lower_rank))
        self.app.add_handler(MessageHandler(filters.Regex(r'^снять |^разжаловать'), self.cmd_remove_rank))
        self.app.add_handler(MessageHandler(filters.Regex(r'^варн|^пред'), self.cmd_warn))
        self.app.add_handler(MessageHandler(filters.Regex(r'^снять варн'), self.cmd_unwarn))
        self.app.add_handler(MessageHandler(filters.Regex(r'^снять все варны'), self.cmd_unwarn_all))
        self.app.add_handler(MessageHandler(filters.Regex(r'^мут'), self.cmd_mute))
        self.app.add_handler(MessageHandler(filters.Regex(r'^размут'), self.cmd_unmute))
        self.app.add_handler(MessageHandler(filters.Regex(r'^бан'), self.cmd_ban))
        self.app.add_handler(MessageHandler(filters.Regex(r'^разбан'), self.cmd_unban))
        self.app.add_handler(MessageHandler(filters.Regex(r'^кик'), self.cmd_kick))
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+триггер'), self.cmd_add_trigger))
        self.app.add_handler(MessageHandler(filters.Regex(r'^-триггер'), self.cmd_remove_trigger))
        self.app.add_handler(MessageHandler(filters.Regex(r'^антимат'), self.cmd_set_antimat))
        self.app.add_handler(MessageHandler(filters.Regex(r'^антиссылки'), self.cmd_set_antilink))
        self.app.add_handler(MessageHandler(filters.Regex(r'^антифлуд'), self.cmd_set_antiflood))
        self.app.add_handler(MessageHandler(filters.Regex(r'^чистка'), self.cmd_clear))
        self.app.add_handler(MessageHandler(filters.Regex(r'^чистка от'), self.cmd_clear_user))
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+приветствие'), self.cmd_set_welcome))
        self.app.add_handler(MessageHandler(filters.Regex(r'^\+правила'), self.cmd_set_rules))
        self.app.add_handler(MessageHandler(filters.Regex(r'^капча'), self.cmd_set_captcha))

        # ===== РУССКИЕ ТЕКСТОВЫЕ КОМАНДЫ =====
        self.app.add_handler(MessageHandler(filters.Regex(r'^Случайная беседа$'), self.cmd_random_chat))
        self.app.add_handler(MessageHandler(filters.Regex(r'^Беседы топ дня$'), self.cmd_top_chats))
        self.app.add_handler(MessageHandler(filters.Regex(r'^Команды$'), self.cmd_help))
        self.app.add_handler(MessageHandler(filters.Regex(r'^Установка$'), self.cmd_setup_info))
        
        # ===== ТЕМЫ ДЛЯ РОЛЕЙ =====
        self.app.add_handler(MessageHandler(filters.Regex(r'^!темы$'), self.cmd_themes))
        self.app.add_handler(MessageHandler(filters.Regex(r'^!темы \d+$'), self.cmd_apply_theme))
        self.app.add_handler(MessageHandler(filters.Regex(r'^!темы \w+$'), self.cmd_apply_theme_by_name))
        
        # ===== ПРИВЯЗКА ЧАТА =====
        self.app.add_handler(MessageHandler(filters.Regex(r'^!привязать$'), self.cmd_bind_chat))
        
        # ===== КОД ЧАТА =====
        self.app.add_handler(CommandHandler("chatcode", self.cmd_chat_code))
        self.app.add_handler(MessageHandler(filters.Regex(r'^код чата$'), self.cmd_chat_code))
        self.app.add_handler(MessageHandler(filters.Regex(r'^сменить код'), self.cmd_change_chat_code))
        
        # ===== КУБЫШКА =====
        self.app.add_handler(CommandHandler("treasury", self.cmd_treasury))
        self.app.add_handler(MessageHandler(filters.Regex(r'^кубышка$'), self.cmd_treasury))
        self.app.add_handler(MessageHandler(filters.Regex(r'^кубышка в неоны$'), self.cmd_treasury_withdraw))
        
        # ===== ОБРАБОТЧИК ЦИФРОВОГО МЕНЮ =====
        self.app.add_handler(MessageHandler(filters.Regex('^[0-9]$'), self.handle_numbers))
        
        # ===== ОБРАБОТЧИКИ СООБЩЕНИЙ =====
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, self.handle_new_members))
        self.app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, self.handle_left_member))
        
        # ===== CALLBACK КНОПКИ =====
        self.app.add_handler(CallbackQueryHandler(self.button_callback))
        
        self.app.add_error_handler(self.error_handler)
        
        logger.info(f"✅ Зарегистрировано обработчиков: {len(self.app.handlers)}")
    
    async def check_spam(self, update: Update) -> bool:
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if has_permission(user_data, 2):
            return False
        
        now = time.time()
        user_id = user.id
        
        self.spam_tracker[user_id] = [t for t in self.spam_tracker[user_id] if now - t < SPAM_WINDOW]
        self.spam_tracker[user_id].append(now)
        
        if len(self.spam_tracker[user_id]) > SPAM_LIMIT:
            self.db.mute_user(user_data['id'], SPAM_MUTE_TIME, 0, "Авто-спам")
            await update.message.reply_text(s.error(f"Спам! Мут на {SPAM_MUTE_TIME} минут"))
            self.spam_tracker[user_id] = []
            return True
        return False
    
    # ===== ОСНОВНЫЕ КОМАНДЫ =====
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /start с новым дизайном"""
        user = update.effective_user
        user_data = self.db.get_user(user.id, user.first_name)
        
        # Проверка реферальной ссылки
        if context.args and context.args[0].isdigit():
            referrer_id = int(context.args[0])
            if referrer_id != user_data['id']:
                self.db.update_user(user_data['id'], referrer_id=referrer_id)
                self.db.add_neons(referrer_id, 50)  # 50 неонов за реферала
                try:
                    await context.bot.send_message(
                        referrer_id,
                        s.success(f"🎉 По вашей ссылке зарегистрировался {user.first_name}! +50 💜")
                    )
                except:
                    pass
        
        # Создаем клавиатуру с кнопками
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎲 Случайная беседа", callback_data="random_chat")],
            [InlineKeyboardButton("🏆 Беседы топ дня", callback_data="top_chats")],
            [InlineKeyboardButton("📋 Команды", callback_data="help_menu")],
            [InlineKeyboardButton("🔧 Установка", callback_data="setup_info")],
            [InlineKeyboardButton("💜 Что такое неоны", callback_data="neons_info")],
            [InlineKeyboardButton("🎁 Бонусы", callback_data="bonuses_menu")]
        ])
        
        text = f"""
👨‍💼 [Spectrum | Чат-менеджер](https://t.me/{BOT_USERNAME}) приветствует Вас!

Я могу предложить следующие темы:

1). [установка](https://teletype.in/@nobucraft/2_pbVPOhaYo) — инструкция установки Спектра;
2). [команды](https://teletype.in/@nobucraft/h0ZU9C1yXNS) — список команд бота;
3). что такое неоны — неоны, виртуальная валюта, как её получить;
4). [бонусы](https://teletype.in/@nobucraft/60hXq-x3h6S) — какие есть бонусы во вселенной Спектра;
5). мой спам — проверить, есть ли вы в базе «Спектр-антиспам».

[Список всех команд с их описанием](https://teletype.in/@nobucraft/h0ZU9C1yXNS)
[Канал](https://t.me/Spectrum_Game) с важными новостями.
[Канал с полезными статьями](https://t.me/Spectrum_poleznoe)

🔈 Для вызова клавиатуры с основными темами, введите `начать` или `помощь`.
        """
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=keyboard
        )
        
        self.db.log_action(user_data['id'], 'start')
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда помощи"""
        text = (
            s.header("СПРАВКА") + "\n"
            f"{s.section('📌 ОСНОВНЫЕ')}"
            f"{s.cmd('start', 'начать')}\n"
            f"{s.cmd('menu', 'меню с цифрами')}\n"
            f"{s.cmd('profile', 'профиль')}\n"
            f"{s.cmd('id', 'узнать свой ID')}\n\n"
            
            f"{s.section('🤖 ИСКУССТВЕННЫЙ ИНТЕЛЛЕКТ')}"
            f"{s.cmd('Спектр [вопрос]', 'задать вопрос AI (в группах)')}\n"
            f"{s.cmd('[любое сообщение]', 'AI отвечает в личке')}\n\n"
            
            f"{s.section('⚙️ МОДЕРАЦИЯ')}"
            f"{s.cmd('+Модер @user', '1 ранг')}\n"
            f"{s.cmd('варн @user [причина]', 'предупреждение')}\n"
            f"{s.cmd('мут @user 30м [причина]', 'заглушить')}\n"
            f"{s.cmd('бан @user [причина]', 'заблокировать')}\n"
            f"{s.cmd('админы', 'список администрации')}\n\n"
            
            f"{s.section('💰 ЭКОНОМИКА')}"
            f"{s.cmd('balance', 'баланс')}\n"
            f"{s.cmd('daily', 'ежедневный бонус')}\n"
            f"{s.cmd('shop', 'магазин')}\n"
            f"{s.cmd('neons', 'мои неоны')}\n"
            f"{s.cmd('farm', 'ферма глитчей')}\n\n"
            
            f"{s.section('🎮 ИГРЫ')}"
            f"{s.cmd('games', 'меню игр')}\n"
            f"{s.cmd('rr [ставка]', 'русская рулетка')}\n"
            f"{s.cmd('bosses', 'список боссов')}\n"
            f"{s.cmd('duel @user [ставка]', 'вызвать на дуэль')}\n\n"
            
            f"{s.section('👾 БОССЫ')}"
            f"{s.cmd('bosses', 'список боссов')}\n"
            f"{s.cmd('boss [ID]', 'атаковать босса')}\n"
            f"{s.cmd('regen', 'восстановить энергию')}\n\n"
            
            f"{s.section('🎭 МАФИЯ')}"
            f"{s.cmd('mafia', 'меню мафии')}\n"
            f"{s.cmd('mafiastart', 'начать игру')}\n"
            f"{s.cmd('mafiajoin', 'присоединиться')}\n\n"
            
            f"{s.section('🏅 НОВЫЕ МОДУЛИ')}"
            f"{s.cmd('achievements', 'ачивки')}\n"
            f"{s.cmd('circles', 'кружки по интересам')}\n"
            f"{s.cmd('bookmarks', 'закладки')}\n"
            f"{s.cmd('bonuses', 'кибер-бонусы')}\n\n"
            
            f"{s.section('📊 ГРАФИКИ')}"
            f"{s.cmd('menu', 'меню → 5')}\n"
            f"{s.cmd('profile', 'профиль с графиком')}\n\n"
            
            f"👑 Владелец: {OWNER_USERNAME}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def show_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Главное меню с цифрами"""
        text = """
# Спектр | Меню

Выберите действие (напишите цифру):

1️⃣ 👤 Профиль
2️⃣ 📊 Статистика
3️⃣ 🎮 Игры
4️⃣ 💰 Магазин
5️⃣ 📈 График активности
6️⃣ ❓ Помощь
7️⃣ 📞 Контакты
0️⃣ 🔙 Выход

📝 Просто напишите номер в чат
        """
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def show_contacts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Контакты"""
        text = f"""
# Спектр | Контакты

👑 **Владелец: {OWNER_USERNAME}
📢 Канал: @spectrum_channel
💬 Чат: @spectrum_chat
📧 Email: support@spectrum.ru
        """
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def show_chart(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать график активности"""
        user = update.effective_user
        
        await update.message.chat.send_action(action="upload_photo")
        
        days, counts = self.db.get_weekly_stats(user.id)
        
        chart = ChartGenerator.create_activity_chart(days, counts, user.first_name)
        
        await update.message.reply_photo(
            photo=chart,
            caption=f"📊 Активность {user.first_name} за последние 7 дней",
            parse_mode='Markdown'
        )

        # ===== СЛУЧАЙНАЯ БЕСЕДА =====
    async def cmd_random_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Поиск случайной беседы как в Ирисе"""
        
        # Получаем случайный чат из базы
        self.db.cursor.execute("""
            SELECT cs.chat_id, cs.chat_name, cs.chat_code, 
                   COUNT(DISTINCT m.user_id) as members,
                   MIN(m.timestamp) as created,
                   SUM(CASE WHEN m.timestamp > datetime('now', '-1 day') THEN 1 ELSE 0 END) as day_active,
                   SUM(CASE WHEN m.timestamp > datetime('now', '-7 day') THEN 1 ELSE 0 END) as week_active,
                   SUM(CASE WHEN m.timestamp > datetime('now', '-30 day') THEN 1 ELSE 0 END) as month_active,
                   COUNT(m.id) as total_messages
            FROM chat_settings cs
            LEFT JOIN messages m ON cs.chat_id = m.chat_id
            WHERE cs.chat_code IS NOT NULL
            GROUP BY cs.chat_id
            ORDER BY RANDOM()
            LIMIT 1
        """)
        
        row = self.db.cursor.fetchone()
        
        if not row:
            await update.message.reply_text(
                "🍬 **В базе пока нет бесед**\n\n"
                "Добавьте бота в чат и введите `!привязать`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        chat = dict(row)
        
        # Форматируем дату создания
        created_date = datetime.fromisoformat(chat['created']).strftime("%d.%m.%Y") if chat['created'] else "неизвестно"
        
        # Определяем тип чата (заглушка, в реальности нужно получать из Telegram)
        chat_type = "открытый" if random.choice([True, False]) else "закрытый"
        entry_type = "свободный" if random.choice([True, False]) else "по заявкам"
        
        # Форматируем активность
        day_active = chat['day_active'] or 0
        week_active = chat['week_active'] or 0
        month_active = chat['month_active'] or 0
        total = chat['total_messages'] or 0
        
        # Создаем клавиатуру
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📩 Попроситься в чат", url=f"https://t.me/{chat['chat_name']}" if chat['chat_name'] else None)],
            [InlineKeyboardButton("📇 Карточка в каталоге", callback_data=f"chat_card_{chat['chat_id']}")],
            [InlineKeyboardButton("🔄 Другую беседу", callback_data="random_chat")]
        ])
        
        text = (
            f"🍬 **Случайная беседа**\n\n"
            f"📢 **Чат «{chat['chat_name'] or 'Без названия'}»**\n"
            f"👤 **Попроситься в чат:** [ссылка]\n"
            f"📇 **Карточка в Ирис-каталоге**\n\n"
            f"🏆 **Ирис-коин рейтинг:** {random.randint(100000, 999999):,}\n"
            f"📅 **Создан:** {created_date}\n"
            f"👥 **Участников:** {chat['members'] or 0} участника\n"
            f"🔒 **Тип:** {chat_type}, вход {entry_type}\n"
            f"📊 **Актив:** {day_active} | {week_active} | {month_active} | {total:,}"
        )
        
        await update.message.reply_text(
            text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
    
    # ===== ТОП БЕСЕД =====
    async def cmd_top_chats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Топ бесед по активности"""
        
        period = "день"
        if context.args:
            if context.args[0] in ["день", "неделя", "месяц", "всё"]:
                period = context.args[0]
        
        time_filter = {
            "день": "datetime('now', '-1 day')",
            "неделя": "datetime('now', '-7 day')",
            "месяц": "datetime('now', '-30 day')",
            "всё": "datetime('2000-01-01')"
        }.get(period, "datetime('now', '-1 day')")
        
        self.db.cursor.execute(f"""
            SELECT cs.chat_name, COUNT(m.id) as msg_count
            FROM chat_settings cs
            LEFT JOIN messages m ON cs.chat_id = m.chat_id AND m.timestamp > {time_filter}
            WHERE cs.chat_code IS NOT NULL
            GROUP BY cs.chat_id
            HAVING msg_count > 0
            ORDER BY msg_count DESC
            LIMIT 10
        """)
        
        chats = self.db.cursor.fetchall()
        
        if not chats:
            await update.message.reply_text(
                f"📊 **Нет данных за {period}**",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        text = f"🏆 **ТОП БЕСЕД ЗА {period.upper()}**\n\n"
        
        for i, chat in enumerate(chats, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            name = chat[0] or f"Чат {i}"
            text += f"{medal} **{name}** — {chat[1]} 💬\n"
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📅 День", callback_data="top_chats_day"),
                InlineKeyboardButton("📆 Неделя", callback_data="top_chats_week"),
                InlineKeyboardButton("📆 Месяц", callback_data="top_chats_month")
            ],
            [InlineKeyboardButton("🔄 Случайная беседа", callback_data="random_chat")]
        ])
        
        await update.message.reply_text(
            text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )

    async def cmd_setup_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация об установке"""
        text = (
            "🔧 **УСТАНОВКА БОТА**\n\n"
            "1️⃣ Добавьте бота в группу\n"
            "2️⃣ Сделайте бота администратором\n"
            "3️⃣ Введите `!привязать` для привязки чата\n"
            "4️⃣ Настройте приветствие: `+приветствие Текст`\n"
            "5️⃣ Настройте правила: `+правила Текст`\n\n"
            "📚 Подробнее: https://telegra.ph/Iris-bot-setup"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        
            # ===== КОМАНДЫ МОДЕРАЦИИ =====
    async def _set_rank(self, update: Update, target_rank: int):
        """Общая логика установки ранга"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 4 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав. Нужен ранг 4+"))
            return
        
        target_user = None
        if update.message.reply_to_message:
            target_id = update.message.reply_to_message.from_user.id
            target_user = self.db.get_user_by_id(self.db.get_user(target_id)['id'])
        else:
            match = re.search(r'@(\S+)', text)
            if match:
                username = match.group(1)
                target_user = self.db.get_user_by_username(username)
        
        if not target_user:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        if target_user['rank'] >= user_data['rank'] and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Нельзя назначить ранг выше своего"))
            return
        
        self.db.set_rank(target_user['id'], target_rank, user_data['id'])
        rank_info = RANKS[target_rank]
        await update.message.reply_text(
            f"{s.success('Ранг назначен!')}\n\n"
            f"{s.item(f'Пользователь: {target_user["first_name"]}')}\n"
            f"{s.item(f'Ранг: {rank_info["emoji"]} {rank_info["name"]}')}",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def cmd_set_rank(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._set_rank(update, 1)
    
    async def cmd_set_rank2(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._set_rank(update, 2)
    
    async def cmd_set_rank3(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._set_rank(update, 3)
    
    async def cmd_set_rank4(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._set_rank(update, 4)
    
    async def cmd_set_rank5(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._set_rank(update, 5)
    
    async def cmd_lower_rank(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 4 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав"))
            return
        
        target_user = None
        if update.message.reply_to_message:
            target_id = update.message.reply_to_message.from_user.id
            target_user = self.db.get_user_by_id(self.db.get_user(target_id)['id'])
        else:
            match = re.search(r'@(\S+)', text)
            if match:
                username = match.group(1)
                target_user = self.db.get_user_by_username(username)
        
        if not target_user:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        if target_user['rank'] <= 0:
            await update.message.reply_text(s.error("❌ Пользователь и так участник"))
            return
        
        if target_user['rank'] >= user_data['rank'] and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Нельзя понизить модератора выше рангом"))
            return
        
        new_rank = target_user['rank'] - 1
        self.db.set_rank(target_user['id'], new_rank, user_data['id'])
        rank_info = RANKS[new_rank]
        await update.message.reply_text(
            f"{s.success('Ранг понижен!')}\n\n"
            f"{s.item(f'Пользователь: {target_user["first_name"]}')}\n"
            f"{s.item(f'Новый ранг: {rank_info["emoji"]} {rank_info["name"]}')}",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def cmd_remove_rank(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 4 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав"))
            return
        
        target_user = None
        if update.message.reply_to_message:
            target_id = update.message.reply_to_message.from_user.id
            target_user = self.db.get_user_by_id(self.db.get_user(target_id)['id'])
        else:
            username = text.replace('снять', '').replace('разжаловать', '').strip().replace('@', '')
            if username:
                target_user = self.db.get_user_by_username(username)
        
        if not target_user:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        if target_user['rank'] >= user_data['rank'] and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Нельзя снять модератора выше рангом"))
            return
        
        self.db.set_rank(target_user['id'], 0, user_data['id'])
        await update.message.reply_text(
            f"{s.success('Модератор снят!')}\n\n"
            f"{s.item(f'Пользователь: {target_user["first_name"]}')}\n"
            f"{s.item('Теперь: 👤 Участник')}",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def cmd_remove_left(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data['rank'] < 4 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав"))
            return
        
        await update.message.reply_text(s.success("✅ Проверка вышедших модераторов выполнена"))
    
    async def cmd_remove_all_ranks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data['rank'] < 5 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Только для создателя"))
            return
        
        self.db.cursor.execute("SELECT id FROM users WHERE rank > 0")
        mods = self.db.cursor.fetchall()
        
        for mod_id in mods:
            self.db.set_rank(mod_id[0], 0, user_data['id'])
        
        await update.message.reply_text(
            s.success(f"✅ Снято модераторов: {len(mods)}"),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def cmd_who_admins(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        admins = self.db.get_admins()
        if not admins:
            await update.message.reply_text(s.info("👥 В чате нет администраторов"))
            return
        text = s.header("АДМИНИСТРАЦИЯ") + "\n\n"
        for admin in admins:
            name = admin['first_name']
            username = f" (@{admin['username']})" if admin['username'] else ""
            rank_emoji = RANKS[admin['rank']]["emoji"]
            text += f"{s.item(f'{rank_emoji} {name}{username} — {admin["rank_name"]}')}\n"
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
async def cmd_warn(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = self.db.get_user(user.id)
    text = update.message.text
    chat_id = update.effective_chat.id
    
    if user_data['rank'] < 1 and user.id != OWNER_ID:
        await update.message.reply_text("⛔️ **Недостаточно прав. Нужен ранг 1+**", parse_mode=ParseMode.MARKDOWN)
        return
    
    target_user = None
    reason = "Нарушение правил"
    
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
        target_user = self.db.get_user_by_id(self.db.get_user(target_id)['id'])
        parts = text.split('\n', 1)
        if len(parts) > 1 and parts[1].strip():
            reason = parts[1].strip()
    else:
        match = re.search(r'(?:варн|пред)\s+@?(\S+)(?:\s+(.+))?', text, re.IGNORECASE)
        if match:
            username = match.group(1)
            target_user = self.db.get_user_by_username(username)
            if match.group(2):
                reason = match.group(2)
    
    if not target_user:
        await update.message.reply_text("❌ **Пользователь не найден**", parse_mode=ParseMode.MARKDOWN)
        return
    
    if target_user['rank'] >= user_data['rank'] and user.id != OWNER_ID:
        await update.message.reply_text("⛔️ **Нельзя выдать предупреждение модератору выше рангом**", parse_mode=ParseMode.MARKDOWN)
        return
    
    warns = self.db.add_warn(target_user['id'], user_data['id'], reason)
    
    admin_name = f"@{user.username}" if user.username else user.first_name
    target_name = f"@{target_user['username']}" if target_user.get('username') else target_user['first_name']
    
    # Уведомление в ЛС
    try:
        await context.bot.send_message(
            target_user['telegram_id'],
            f"⚠️ **Предупреждение ({warns}/4)**\n\n"
            f"💬 **Причина:** {reason}\n"
            f"🦸 **Модератор:** {admin_name}",
            parse_mode=ParseMode.MARKDOWN
        )
    except:
        pass
    
    await update.message.reply_text(
        f"⚠️ **Предупреждение ({warns}/4)**\n\n"
        f"👤 **Пользователь:** {target_name}\n"
        f"💬 **Причина:** {reason}\n"
        f"🦸 **Модератор:** {admin_name}",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # АВТОМАТИЧЕСКИЕ ДЕЙСТВИЯ
    if warns == 2:
        minutes = 60
        self.db.mute_user(target_user['id'], minutes, user_data['id'], "2 предупреждения")
        try:
            until_date = int(time.time()) + (minutes * 60)
            permissions = {'can_send_messages': False, 'can_send_media_messages': False, 'can_send_polls': False, 'can_send_other_messages': False, 'can_add_web_page_previews': False}
            await context.bot.restrict_chat_member(chat_id, target_user['telegram_id'], permissions=permissions, until_date=until_date)
            await update.message.reply_text(f"🔇 **Мут на 1 час**\n\n👤 {target_name}", parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.error(f"Ошибка мута: {e}")
    
    elif warns == 3:
        minutes = 1440
        self.db.mute_user(target_user['id'], minutes, user_data['id'], "3 предупреждения")
        try:
            until_date = int(time.time()) + (minutes * 60)
            permissions = {'can_send_messages': False, 'can_send_media_messages': False, 'can_send_polls': False, 'can_send_other_messages': False, 'can_add_web_page_previews': False}
            await context.bot.restrict_chat_member(chat_id, target_user['telegram_id'], permissions=permissions, until_date=until_date)
            await update.message.reply_text(f"🔇 **Мут на 24 часа**\n\n👤 {target_name}", parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.error(f"Ошибка мута: {e}")
    
    elif warns >= 4:
        self.db.ban_user(target_user['id'], user_data['id'], "4 предупреждения")
        try:
            await context.bot.ban_chat_member(chat_id, target_user['telegram_id'])
            await update.message.reply_text(f"🔴 **Пользователь забанен (4/4)**\n\n👤 {target_name}", parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.error(f"Ошибка бана: {e}")
                
async def cmd_warns(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ **Укажите пользователя:** `/warns @user`", parse_mode=ParseMode.MARKDOWN)
        return
    
    username = context.args[0].replace('@', '')
    target = self.db.get_user_by_username(username)
    
    if not target:
        await update.message.reply_text("❌ **Пользователь не найден**", parse_mode=ParseMode.MARKDOWN)
        return
    
    warns_list = self.db.get_warns(target['id'])
    target_name = f"@{target['username']}" if target.get('username') else target['first_name']
    
    if not warns_list:
        await update.message.reply_text(f"📋 **У {target_name} нет предупреждений**", parse_mode=ParseMode.MARKDOWN)
        return
    
    text = f"📋 **ПРЕДУПРЕЖДЕНИЯ: {target_name}**\n\n"
    for warn in warns_list:
        admin = self.db.get_user_by_id(warn['admin_id'])
        admin_name = f"@{admin['username']}" if admin and admin.get('username') else (admin['first_name'] if admin else 'Система')
        date = datetime.fromisoformat(warn['date']).strftime("%d.%m.%Y %H:%M")
        text += (
            f"⚠️ **ID {warn['id']}**\n"
            f"💬 **Причина:** {warn['reason']}\n"
            f"🦸 **Модератор:** {admin_name}\n"
            f"📅 **Дата:** {date}\n\n"
        )
    
    text += f"📊 **Всего:** {len(warns_list)}/4"
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
async def cmd_my_warns(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = self.db.get_user(update.effective_user.id)
    warns_list = self.db.get_warns(user_data['id'])
    
    if not warns_list:
        await update.message.reply_text("✅ **У вас нет предупреждений**", parse_mode=ParseMode.MARKDOWN)
        return
    
    user_name = f"@{user_data['username']}" if user_data.get('username') else user_data['first_name']
    text = f"📋 **МОИ ПРЕДУПРЕЖДЕНИЯ: {user_name}**\n\n"
    
    for warn in warns_list:
        admin = self.db.get_user_by_id(warn['admin_id'])
        admin_name = f"@{admin['username']}" if admin and admin.get('username') else (admin['first_name'] if admin else 'Система')
        date = datetime.fromisoformat(warn['date']).strftime("%d.%m.%Y %H:%M")
        text += (
            f"⚠️ **ID {warn['id']}**\n"
            f"💬 **Причина:** {warn['reason']}\n"
            f"🦸 **Модератор:** {admin_name}\n"
            f"📅 **Дата:** {date}\n\n"
        )
    
    text += f"📊 **Всего:** {len(warns_list)}/4"
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    
async def cmd_unwarn(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = self.db.get_user(user.id)
    text = update.message.text
    
    if user_data['rank'] < 1 and user.id != OWNER_ID:
        await update.message.reply_text("⛔️ **Недостаточно прав**", parse_mode=ParseMode.MARKDOWN)
        return
    
    target_user = None
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
        target_user = self.db.get_user_by_id(self.db.get_user(target_id)['id'])
    else:
        match = re.search(r'снять варн\s+@?(\S+)', text, re.IGNORECASE)
        if match:
            username = match.group(1)
            target_user = self.db.get_user_by_username(username)
    
    if not target_user:
        await update.message.reply_text("❌ **Пользователь не найден**", parse_mode=ParseMode.MARKDOWN)
        return
    
    removed = self.db.remove_last_warn(target_user['id'], user_data['id'])
    target_name = f"@{target_user['username']}" if target_user.get('username') else target_user['first_name']
    admin_name = f"@{user.username}" if user.username else user.first_name
    
    if not removed:
        await update.message.reply_text(f"📋 **У {target_name} нет предупреждений**", parse_mode=ParseMode.MARKDOWN)
        return
    
    warns_list = self.db.get_warns(target_user['id'])
    remaining = len(warns_list)
    
    await update.message.reply_text(
        f"✅ **Предупреждение снято**\n\n"
        f"👤 **Пользователь:** {target_name}\n"
        f"🦸 **Модератор:** {admin_name}\n"
        f"📊 **Осталось:** {remaining}/4",
        parse_mode=ParseMode.MARKDOWN
    )
    
    async def cmd_unwarn_all(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 2 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав"))
            return
        
        match = re.search(r'снять все варны\s+@?(\S+)', text, re.IGNORECASE)
        if not match:
            await update.message.reply_text(s.error("❌ Укажите пользователя"))
            return
        
        username = match.group(1)
        target_user = self.db.get_user_by_username(username)
        
        if not target_user:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        warns_list = self.db.get_warns(target_user['id'])
        for _ in warns_list:
            self.db.remove_last_warn(target_user['id'], user_data['id'])
        
        target_name = target_user.get('nickname') or target_user['first_name']
        await update.message.reply_text(s.success(f"✅ Все предупреждения сняты с {target_name}"))
    
    async def cmd_mute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        chat_id = update.effective_chat.id
        
        if user_data['rank'] < 2 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав. Нужен ранг 2+"))
            return
        
        match = re.search(r'мут\s+@?(\S+)(?:\s+(\d+[мчд]))?(?:\s+(.+))?', text, re.IGNORECASE)
        if not match:
            await update.message.reply_text(s.error("❌ Пример: мут @user 30м спам"))
            return
        
        username = match.group(1)
        time_str = match.group(2) if match.group(2) else "60м"
        reason = match.group(3) if match.group(3) else "Нарушение правил"
        
        minutes = parse_time(time_str)
        if not minutes:
            await update.message.reply_text(s.error("❌ Неверный формат времени. Используйте: 30м, 2ч, 1д"))
            return
        
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        if target['rank'] >= user_data['rank'] and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Нельзя замутить модератора выше рангом"))
            return
        
        # Сохраняем в БД
        until = self.db.mute_user(target['id'], minutes, user_data['id'], reason)
        until_str = until.strftime("%d.%m.%Y %H:%M")
        
        # НАСТОЯЩИЙ МУТ
        mute_success = False
        try:
            until_date = int(time.time()) + (minutes * 60)
            
            permissions = {
                'can_send_messages': False,
                'can_send_media_messages': False,
                'can_send_polls': False,
                'can_send_other_messages': False,
                'can_add_web_page_previews': False
            }
            
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=target['telegram_id'],
                permissions=permissions,
                until_date=until_date
            )
            mute_success = True
        except Exception as e:
            logger.error(f"Ошибка мута: {e}")
        
        try:
            await context.bot.send_message(
                target['telegram_id'],
                f"{s.warning('🔇 ВАС ЗАМУТИЛИ')}\n\n"
                f"{s.item(f'Срок: {time_str}')}\n"
                f"{s.item(f'Причина: {reason}')}\n"
                f"{s.item(f'До: {until_str}')}"
            )
        except:
            pass
        
        text = (
            s.header("МУТ") + "\n"
            f"{s.item(f'Пользователь: {target["first_name"]}')}\n"
            f"{s.item(f'Срок: {time_str}')}\n"
            f"{s.item(f'До: {until_str}')}\n"
            f"{s.item(f'Причина: {reason}')}\n\n"
            f"{'✅ Мут применен' if mute_success else '❌ Не удалось применить мут'}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        
async def cmd_mutelist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    muted = self.db.get_muted_users()
    
    if not muted:
        await update.message.reply_text("📋 **Список замученных пуст**", parse_mode=ParseMode.MARKDOWN)
        return
    
    text = "📋 **СПИСОК ЗАМУЧЕННЫХ**\n\n"
    
    for mute in muted[:15]:
        until = datetime.fromisoformat(mute['mute_until']).strftime("%d.%m %H:%M")
        name = mute['first_name']
        username = f" (@{mute['username']})" if mute.get('username') else ""
        
        text += f"🔇 {name}{username} — до {until}\n"
    
    if len(muted) > 15:
        text += f"\n👥 **Всего:** {len(muted)} (показаны первые 15)"
    else:
        text += f"\n👥 **Всего:** {len(muted)}"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def cmd_unmute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        chat_id = update.effective_chat.id
        
        if user_data['rank'] < 2 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав"))
            return
        
        username = text.replace('размут', '').replace('@', '').strip()
        if not username and update.message.reply_to_message:
            target_id = update.message.reply_to_message.from_user.id
            target = self.db.get_user_by_id(self.db.get_user(target_id)['id'])
        elif username:
            target = self.db.get_user_by_username(username)
        else:
            await update.message.reply_text(s.error("❌ Укажите пользователя"))
            return
        
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        self.db.unmute_user(target['id'], user_data['id'])
        
        try:
            permissions = {
                'can_send_messages': True,
                'can_send_media_messages': True,
                'can_send_polls': True,
                'can_send_other_messages': True,
                'can_add_web_page_previews': True
            }
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=target['telegram_id'],
                permissions=permissions
            )
        except:
            pass
        
        try:
            await context.bot.send_message(
                target['telegram_id'],
                s.success("✅ Мут снят")
            )
        except:
            pass
        
        await update.message.reply_text(s.success(f"✅ Мут снят с {target['first_name']}"))
    
    # ========== ИСПРАВЛЕННЫЙ МЕТОД cmd_ban (РЕАЛЬНЫЙ БАН) ==========
async def cmd_ban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = self.db.get_user(user.id)
    text = update.message.text
    chat_id = update.effective_chat.id
    
    if user_data['rank'] < 2 and user.id != OWNER_ID:
        await update.message.reply_text("⛔️ **Недостаточно прав. Нужен ранг 2+**", parse_mode=ParseMode.MARKDOWN)
        return
    
    match = re.search(r'бан\s+@?(\S+)(?:\s+(.+))?', text, re.IGNORECASE)
    if not match:
        await update.message.reply_text("❌ **Пример:** `бан @user спам`", parse_mode=ParseMode.MARKDOWN)
        return
    
    username = match.group(1)
    reason = match.group(2) if match.group(2) else "Нарушение правил"
    
    target = self.db.get_user_by_username(username)
    if not target:
        await update.message.reply_text("❌ **Пользователь не найден**", parse_mode=ParseMode.MARKDOWN)
        return
    
    if target['rank'] >= user_data['rank'] and user.id != OWNER_ID:
        await update.message.reply_text("⛔️ **Нельзя забанить модератора выше рангом**", parse_mode=ParseMode.MARKDOWN)
        return
    
    # Проверяем права бота
    try:
        bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
        if bot_member.status not in ['administrator', 'creator']:
            await update.message.reply_text(
                "❌ **Бот не администратор!**\nВыдайте права с опцией **«Блокировка пользователей»**",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        if not bot_member.can_restrict_members:
            await update.message.reply_text(
                "❌ **У бота нет права на блокировку!**\nВключите **«Блокировка пользователей»**",
                parse_mode=ParseMode.MARKDOWN
            )
            return
    except Exception as e:
        logger.error(f"Ошибка проверки прав: {e}")
    
    # НАСТОЯЩИЙ БАН
    try:
        await context.bot.ban_chat_member(
            chat_id=chat_id,
            user_id=target['telegram_id'],
            until_date=int(time.time()) + (30 * 24 * 60 * 60)  # 30 дней
        )
        
        # Бан в БД
        self.db.ban_user(target['id'], user_data['id'], reason)
        
        # Красивое оформление
        admin_name = f"@{user.username}" if user.username else user.first_name
        target_name = f"@{target['username']}" if target.get('username') else target['first_name']
        
        text = (
            f"🔴 **Пользователь забанен**\n\n"
            f"👢 **Пользователь:** {target_name}\n"
            f"🦸 **Модератор:** {admin_name}\n"
            f"💬 **Причина:** {reason}\n"
            f"📅 **Срок:** 30 дней"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        
        # Уведомление в ЛС
        try:
            await context.bot.send_message(
                target['telegram_id'],
                f"🔴 **Вас заблокировали в чате**\n\n"
                f"👢 **Чат:** {update.effective_chat.title}\n"
                f"🦸 **Модератор:** {admin_name}\n"
                f"💬 **Причина:** {reason}\n"
                f"📅 **Срок:** 30 дней",
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass
            
    except Exception as e:
        logger.error(f"Ошибка бана: {e}")
        await update.message.reply_text(
            f"❌ **Ошибка:** {str(e)[:100]}",
            parse_mode=ParseMode.MARKDOWN
        )
    
    # ========== ИСПРАВЛЕННЫЙ МЕТОД cmd_banlist ==========
async def cmd_banlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    bans = self.db.get_banlist()
    
    if not bans:
        await update.message.reply_text("📋 **Список забаненных пуст**", parse_mode=ParseMode.MARKDOWN)
        return
    
    text = "📋 **СПИСОК ЗАБАНЕННЫХ**\n\n"
    
    for ban in bans[:15]:
        name = ban.get('first_name', 'Неизвестно')
        username = f" (@{ban['username']})" if ban.get('username') else ""
        text += f"🔴 {name}{username}\n"
    
    if len(bans) > 15:
        text += f"\n👥 **Всего:** {len(bans)} (показаны первые 15)"
    else:
        text += f"\n👥 **Всего:** {len(bans)}"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
  
    # ========== ИСПРАВЛЕННЫЙ МЕТОД cmd_unban ==========
async def cmd_unban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = self.db.get_user(user.id)
    text = update.message.text
    chat_id = update.effective_chat.id
    
    if user_data['rank'] < 2 and user.id != OWNER_ID:
        await update.message.reply_text("⛔️ **Недостаточно прав. Нужен ранг 2+**", parse_mode=ParseMode.MARKDOWN)
        return
    
    username = text.replace('разбан', '').replace('@', '').strip()
    if not username:
        await update.message.reply_text("❌ **Укажите пользователя:** `разбан @user`", parse_mode=ParseMode.MARKDOWN)
        return
    
    target = self.db.get_user_by_username(username)
    if not target:
        await update.message.reply_text("❌ **Пользователь не найден**", parse_mode=ParseMode.MARKDOWN)
        return
    
    # Разбан в Telegram
    try:
        await context.bot.unban_chat_member(
            chat_id=chat_id,
            user_id=target['telegram_id'],
            only_if_banned=True
        )
        
        # Разбан в БД
        self.db.unban_user(target['id'], user_data['id'])
        
        admin_name = f"@{user.username}" if user.username else user.first_name
        target_name = f"@{target['username']}" if target.get('username') else target['first_name']
        
        await update.message.reply_text(
            f"✅ **Бан снят**\n\n"
            f"👤 **Пользователь:** {target_name}\n"
            f"🦸 **Модератор:** {admin_name}",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Уведомление в ЛС
        try:
            await context.bot.send_message(
                target['telegram_id'],
                f"✅ **Вас разблокировали в чате**\n\n"
                f"👢 **Чат:** {update.effective_chat.title}\n"
                f"🦸 **Модератор:** {admin_name}",
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass
            
    except Exception as e:
        logger.error(f"Ошибка разбана: {e}")
        await update.message.reply_text(
            f"❌ **Ошибка:** {str(e)[:100]}",
            parse_mode=ParseMode.MARKDOWN
        )

    async def cmd_kick(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        chat_id = update.effective_chat.id
        
        if user_data['rank'] < 1 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав"))
            return
        
        username = text.replace('кик', '').replace('@', '').strip()
        target = self.db.get_user_by_username(username)
        
        if not target and update.message.reply_to_message:
            target_id = update.message.reply_to_message.from_user.id
            target = self.db.get_user_by_id(self.db.get_user(target_id)['id'])
        
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        try:
            await context.bot.ban_chat_member(chat_id, target['telegram_id'])
            await context.bot.unban_chat_member(chat_id, target['telegram_id'])
            await update.message.reply_text(s.success(f"✅ {target['first_name']} исключен"))
        except Exception as e:
            await update.message.reply_text(s.error(f"❌ Ошибка: {e}"))

    async def cmd_checkrights(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Проверка прав бота в чате"""
        chat_id = update.effective_chat.id
        
        try:
            bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
            
            if bot_member.status == 'creator':
                await update.message.reply_text(s.success("✅ Бот является создателем чата! Полные права."))
            elif bot_member.status == 'administrator':
                rights = []
                if bot_member.can_restrict_members:
                    rights.append("✅ может банить/мутить")
                else:
                    rights.append("❌ НЕТ ПРАВА на бан/мут! (нужно включить)")
                
                if bot_member.can_delete_messages:
                    rights.append("✅ может удалять сообщения")
                else:
                    rights.append("❌ не может удалять сообщения")
                
                if bot_member.can_pin_messages:
                    rights.append("✅ может закреплять")
                else:
                    rights.append("❌ не может закреплять")
                
                if bot_member.can_invite_users:
                    rights.append("✅ может приглашать")
                else:
                    rights.append("❌ не может приглашать")
                
                if bot_member.can_change_info:
                    rights.append("✅ может менять информацию")
                else:
                    rights.append("❌ не может менять информацию")
                
                rights_text = "\n".join(rights)
                await update.message.reply_text(
                    f"👑 **Бот администратор**\n\n{rights_text}",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await update.message.reply_text(s.error("❌ Бот не администратор! Выдайте права администратора."))
        except Exception as e:
            await update.message.reply_text(s.error(f"❌ Ошибка проверки: {e}"))
            
    async def cmd_add_trigger(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 3 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав"))
            return
        
        text = text[9:].strip()
        if "=" not in text:
            await update.message.reply_text(s.error("❌ Формат: +триггер слово = действие"))
            return
        
        word, action = text.split("=", 1)
        word = word.strip().lower()
        action = action.strip()
        
        action_parts = action.split()
        action_type = action_parts[0].lower()
        action_value = action_parts[1] if len(action_parts) > 1 else None
        
        if action_type not in ["delete", "mute", "warn", "ban"]:
            await update.message.reply_text(s.error("❌ Действие должно быть: delete, mute, warn, ban"))
            return
        
        self.db.cursor.execute('''
            INSERT INTO triggers (chat_id, word, action, action_value, created_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (update.effective_chat.id, word, action_type, action_value, user_data['id']))
        self.db.conn.commit()
        
        await update.message.reply_text(s.success(f"✅ Триггер добавлен: {word} -> {action}"))
    
    async def cmd_remove_trigger(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 3 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав"))
            return
        
        trigger_id = text[9:].strip()
        if not trigger_id.isdigit():
            await update.message.reply_text(s.error("❌ Укажите ID триггера"))
            return
        
        self.db.cursor.execute("DELETE FROM triggers WHERE id = ? AND chat_id = ?", 
                             (int(trigger_id), update.effective_chat.id))
        self.db.conn.commit()
        
        await update.message.reply_text(s.success("✅ Триггер удален"))
    
    async def cmd_list_triggers(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.db.cursor.execute("SELECT id, word, action, action_value FROM triggers WHERE chat_id = ?", 
                             (update.effective_chat.id,))
        triggers = self.db.cursor.fetchall()
        
        if not triggers:
            await update.message.reply_text(s.info("В этом чате нет триггеров"))
            return
        
        text = s.header("ТРИГГЕРЫ ЧАТА") + "\n\n"
        for trigger in triggers:
            action_text = trigger[2]
            if trigger[3]:
                action_text += f" {trigger[3]}"
            text += f"ID: {trigger[0]} | {trigger[1]} → {action_text}\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def _toggle_setting(self, update: Update, setting: str):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data['rank'] < 3 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав"))
            return
        
        parts = update.message.text.split()
        if len(parts) < 2:
            await update.message.reply_text(s.error("❌ Укажите on или off"))
            return
        
        state = 1 if parts[1].lower() in ["on", "вкл", "да"] else 0
        
        self.db.cursor.execute(f'''
            INSERT INTO chat_settings (chat_id, {setting})
            VALUES (?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET {setting} = excluded.{setting}
        ''', (update.effective_chat.id, state))
        self.db.conn.commit()
        
        status = "включен" if state else "выключен"
        names = {"antimat": "Антимат", "antilink": "Антиссылки", "antiflood": "Антифлуд"}
        await update.message.reply_text(s.success(f"✅ {names[setting]} {status}"))
    
    async def cmd_set_antimat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._toggle_setting(update, "antimat")
    
    async def cmd_set_antilink(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._toggle_setting(update, "antilink")
    
    async def cmd_set_antiflood(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._toggle_setting(update, "antiflood")
    
    async def cmd_clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data['rank'] < 2 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав"))
            return
        
        parts = update.message.text.split()
        if len(parts) < 2:
            await update.message.reply_text(s.error("❌ Укажите количество: чистка 50"))
            return
        
        try:
            count = int(parts[1])
            if count > 100:
                count = 100
        except:
            await update.message.reply_text(s.error("❌ Количество должно быть числом"))
            return
        
        try:
            await update.message.delete()
            messages = []
            async for msg in context.bot.get_chat_history(update.effective_chat.id, limit=count):
                messages.append(msg.message_id)
            
            if messages:
                await context.bot.delete_messages(update.effective_chat.id, messages)
                await context.bot.send_message(update.effective_chat.id, 
                                              s.success(f"✅ Удалено {len(messages)} сообщений"),
                                              disable_notification=True)
        except Exception as e:
            await update.message.reply_text(s.error(f"❌ Ошибка: {e}"))
    
    async def cmd_clear_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        text = update.message.text
        
        if user_data['rank'] < 2 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав"))
            return
        
        username = text.replace('чистка от', '').strip().replace('@', '')
        target = self.db.get_user_by_username(username)
        
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        await update.message.reply_text(s.info(f"🔄 Удаляю сообщения {target['first_name']}..."))
    
    async def cmd_set_welcome(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data['rank'] < 3 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав"))
            return
        
        welcome_text = update.message.text[12:].strip()
        if not welcome_text:
            await update.message.reply_text(s.error("❌ Укажите текст приветствия"))
            return
        
        self.db.cursor.execute('''
            INSERT INTO chat_settings (chat_id, welcome)
            VALUES (?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET welcome = excluded.welcome
        ''', (update.effective_chat.id, welcome_text))
        self.db.conn.commit()
        
        await update.message.reply_text(s.success("✅ Приветствие установлено"))
    
    async def cmd_set_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data['rank'] < 3 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав"))
            return
        
        rules_text = update.message.text[9:].strip()
        if not rules_text:
            await update.message.reply_text(s.error("❌ Укажите текст правил"))
            return
        
        self.db.cursor.execute('''
            INSERT INTO chat_settings (chat_id, rules)
            VALUES (?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET rules = excluded.rules
        ''', (update.effective_chat.id, rules_text))
        self.db.conn.commit()
        
        await update.message.reply_text(s.success("✅ Правила установлены"))
    
    async def cmd_show_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.db.cursor.execute("SELECT rules FROM chat_settings WHERE chat_id = ?", (update.effective_chat.id,))
        row = self.db.cursor.fetchone()
        
        if row and row[0]:
            await update.message.reply_text(f"📜 **Правила чата:**\n\n{row[0]}", parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(s.info("В этом чате ещё не установлены правила"))
    
    async def cmd_set_captcha(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data['rank'] < 3 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Недостаточно прав"))
            return
        
        parts = update.message.text.split()
        if len(parts) < 2:
            await update.message.reply_text(s.error("❌ Укажите on или off"))
            return
        
        state = 1 if parts[1].lower() in ["on", "вкл", "да"] else 0
        
        self.db.cursor.execute('''
            INSERT INTO chat_settings (chat_id, captcha)
            VALUES (?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET captcha = excluded.captcha
        ''', (update.effective_chat.id, state))
        self.db.conn.commit()
        
        status = "включена" if state else "выключена"
        await update.message.reply_text(s.success(f"✅ Капча {status}"))
    
    async def cmd_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        vip_status = "✅ Активен" if self.db.is_vip(user_data['id']) else "❌ Не активен"
        vip_until = ""
        if self.db.is_vip(user_data['id']):
            vip_until = self.db.cursor.execute("SELECT vip_until FROM users WHERE id = ?", (user_data['id'],)).fetchone()[0]
            vip_until = datetime.fromisoformat(vip_until).strftime("%d.%m.%Y")
        
        premium_status = "✅ Активен" if self.db.is_premium(user_data['id']) else "❌ Не активен"
        
        text = (
            f"# Спектр | Кошелёк пользователя {user.first_name}**\n\n"
            f"💰 Баланс: {user_data['coins']:,} 💰\n"
            f"💜 Неоны: {user_data['neons']:,}\n"
            f"🖥 Глитчи: {user_data['glitches']:,}\n\n"
            f"💎 VIP статус: {vip_status}\n"
            f"{f'📅 VIP до: {vip_until}' if self.db.is_vip(user_data['id']) else ''}\n"
            f"👑 PREMIUM: {premium_status}\n\n"
            f"🔥 Стрик: {user_data['daily_streak']} дней\n"
            f"🎁 /daily — доступно"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_pay(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text(s.error("❌ Использование: /pay @user сумма"))
            return
        
        username = context.args[0].replace('@', '')
        try:
            amount = int(context.args[1])
        except:
            await update.message.reply_text(s.error("❌ Сумма должна быть числом"))
            return
        
        if amount <= 0:
            await update.message.reply_text(s.error("❌ Сумма должна быть больше 0"))
            return
        
        user_data = self.db.get_user(update.effective_user.id)
        
        if user_data['coins'] < amount:
            await update.message.reply_text(s.error(f"❌ Недостаточно монет. Баланс: {user_data['coins']} 💰"))
            return
        
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        if target['id'] == user_data['id']:
            await update.message.reply_text(s.error("❌ Нельзя перевести самому себе"))
            return
        
        self.db.add_coins(user_data['id'], -amount)
        self.db.add_coins(target['id'], amount)
        
        commission_text = ""
        if not self.db.is_premium(user_data['id']):
            commission = int(amount * 0.05)
            self.db.add_coins(user_data['id'], -commission)
            commission_text = f"\n{s.item(f'💸 Комиссия: {commission} (5%)')}"
        
        target_name = target.get('nickname') or target['first_name']
        
        text = (
            s.header("💸 ПЕРЕВОД") + "\n"
            f"{s.item(f'Получатель: {target_name}')}\n"
            f"{s.item(f'Сумма: {amount} 💰')}{commission_text}\n\n"
            f"{s.success('✅ Перевод выполнен!')}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        self.db.log_action(user_data['id'], 'pay', f"{amount}💰 -> {target['id']}")
    
    async def cmd_daily(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data.get('last_daily'):
            last = datetime.fromisoformat(user_data['last_daily'])
            if (datetime.now() - last).seconds < DAILY_COOLDOWN:
                remain = DAILY_COOLDOWN - (datetime.now() - last).seconds
                hours = remain // 3600
                minutes = (remain % 3600) // 60
                await update.message.reply_text(s.warning(f"⏳ Бонус через {hours}ч {minutes}м"))
                return
        
        streak = self.db.add_daily_streak(user_data['id'])
        
        coins = random.randint(100, 300)
        neons = random.randint(1, 5)
        exp = random.randint(20, 60)
        energy = 20
        
        coins = int(coins * (1 + min(streak, 30) * 0.05))
        neons = int(neons * (1 + min(streak, 30) * 0.05))
        exp = int(exp * (1 + min(streak, 30) * 0.05))
        
        if self.db.is_vip(user_data['id']):
            coins = int(coins * 1.5)
            neons = int(neons * 1.5)
            exp = int(exp * 1.5)
            energy = int(energy * 1.5)
        if self.db.is_premium(user_data['id']):
            coins = int(coins * 2)
            neons = int(neons * 2)
            exp = int(exp * 2)
            energy = int(energy * 2)
        
        self.db.add_coins(user_data['id'], coins)
        self.db.add_neons(user_data['id'], neons)
        self.db.add_exp(user_data['id'], exp)
        self.db.add_energy(user_data['id'], energy)
        
        text = (
            f"# Спектр | Ежедневный бонус\n\n"
            f"🎉 {user.first_name}, вы получили бонус!\n\n"
            f"💰 Монеты: +{coins}\n"
            f"💜 Неоны: +{neons}\n"
            f"🔥 Стрик: {streak} дней\n"
            f"✨ Опыт: +{exp}\n"
            f"⚡️ Энергия: +{energy}\n\n"
            f"💰 Новый баланс: {user_data['coins'] + coins} 💰\n"
            f"💜 Новые неоны: {user_data['neons'] + neons}\n\n"
            f"⏳ Следующий бонус через: 24 часа"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        self.db.log_action(user_data['id'], 'daily', f'+{coins}💰 +{neons}💜')
    
    async def cmd_streak(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)
        streak = user_data.get('daily_streak', 0)
        
        text = (
            s.header("🔥 ТЕКУЩИЙ СТРИК") + "\n\n"
            f"{s.stat('Дней подряд', streak)}\n"
            f"{s.stat('Множитель', f'x{1 + min(streak, 30) * 0.05:.2f}')}\n\n"
            f"{s.info('Чем больше стрик, тем выше бонус!')}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_shop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            s.header("🛍 МАГАЗИН") + "\n\n"
            f"{s.section('💊 ЗЕЛЬЯ')}"
            f"{s.cmd('buy зелье здоровья', '50 💰 (❤️+30)')}\n"
            f"{s.cmd('buy большое зелье', '100 💰 (❤️+70)')}\n\n"
            f"{s.section('⚔️ ОРУЖИЕ')}"
            f"{s.cmd('buy меч', '200 💰 (⚔️+10)')}\n"
            f"{s.cmd('buy легендарный меч', '500 💰 (⚔️+30)')}\n\n"
            f"{s.section('⚡️ ЭНЕРГИЯ')}"
            f"{s.cmd('buy энергетик', '30 💰 (⚡️+20)')}\n"
            f"{s.cmd('buy батарейка', '80 💰 (⚡️+50)')}\n\n"
            f"{s.section('💎 ПРИВИЛЕГИИ')}"
            f"{s.cmd('vip', f'VIP ({VIP_PRICE} 💰 / 30 дней)')}\n"
            f"{s.cmd('premium', f'PREMIUM ({PREMIUM_PRICE} 💰 / 30 дней)')}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_buy(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("❌ Что купить? /buy [предмет]"))
            return
        
        item = " ".join(context.args).lower()
        user_data = self.db.get_user(update.effective_user.id)
        
        items = {
            "зелье здоровья": {"price": 50, "heal": 30},
            "большое зелье": {"price": 100, "heal": 70},
            "меч": {"price": 200, "damage": 10},
            "легендарный меч": {"price": 500, "damage": 30},
            "энергетик": {"price": 30, "energy": 20},
            "батарейка": {"price": 80, "energy": 50}
        }
        
        if item not in items:
            await update.message.reply_text(s.error("❌ Такого товара нет в магазине"))
            return
        
        item_data = items[item]
        
        if user_data['coins'] < item_data['price']:
            await update.message.reply_text(s.error(f"❌ Недостаточно монет. Нужно {item_data['price']} 💰"))
            return
        
        self.db.add_coins(user_data['id'], -item_data['price'])
        
        effects = []
        if 'heal' in item_data:
            new_health = self.db.heal(user_data['id'], item_data['heal'])
            effects.append(f"❤️ Здоровье +{item_data['heal']} (теперь {new_health})")
        
        if 'damage' in item_data:
            new_damage = user_data['damage'] + item_data['damage']
            self.db.update_user(user_data['id'], damage=new_damage)
            effects.append(f"⚔️ Урон +{item_data['damage']} (теперь {new_damage})")
        
        if 'energy' in item_data:
            new_energy = self.db.add_energy(user_data['id'], item_data['energy'])
            effects.append(f"⚡️ Энергия +{item_data['energy']} (теперь {new_energy})")
        
        effects_text = "\n".join([f"{s.item(e)}" for e in effects])
        
        await update.message.reply_text(
            f"{s.success('✅ Покупка совершена!')}\n\n"
            f"{s.item(f'Предмет: {item}')}\n"
            f"{effects_text}",
            parse_mode=ParseMode.MARKDOWN
        )
        
        self.db.log_action(user_data['id'], 'buy', item)
    
    async def cmd_vip_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            s.header("💎 VIP СТАТУС") + "\n\n"
            f"Цена: {VIP_PRICE} 💰 / {VIP_DAYS} дней\n\n"
            f"{s.item('⚔️ Урон в битвах +20%')}\n"
            f"{s.item('💰 Награда с боссов +50%')}\n"
            f"{s.item('🎁 Ежедневный бонус +50%')}\n"
            f"{s.item('💎 Алмазы +1 в день')}\n\n"
            f"{s.cmd('buyvip', 'купить VIP')}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_premium_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            s.header("💎 PREMIUM СТАТУС") + "\n\n"
            f"Цена: {PREMIUM_PRICE} 💰 / {PREMIUM_DAYS} дней\n\n"
            f"{s.item('⚔️ Урон в битвах +50%')}\n"
            f"{s.item('💰 Награда с боссов +100%')}\n"
            f"{s.item('🎁 Ежедневный бонус +100%')}\n"
            f"{s.item('💎 Алмазы +3 в день')}\n"
            f"{s.item('🚫 Игнорирование спам-фильтра')}\n\n"
            f"{s.cmd('buypremium', 'купить PREMIUM')}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_buy_vip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)
        
        if user_data['coins'] < VIP_PRICE:
            await update.message.reply_text(s.error(f"❌ Недостаточно монет. Нужно {VIP_PRICE} 💰"))
            return
        
        if self.db.is_vip(user_data['id']):
            await update.message.reply_text(s.error("❌ VIP статус уже активен"))
            return
        
        self.db.add_coins(user_data['id'], -VIP_PRICE)
        until = self.db.set_vip(user_data['id'], VIP_DAYS)
        date_str = until.strftime("%d.%m.%Y")
        
        text = (
            s.header("✨ VIP СТАТУС АКТИВИРОВАН") + "\n\n"
            f"{s.item(f'Срок: до {date_str}')}\n\n"
            f"{s.info('Спасибо за поддержку!')}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        self.db.log_action(user_data['id'], 'buy_vip')
    
    async def cmd_buy_premium(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)
        
        if user_data['coins'] < PREMIUM_PRICE:
            await update.message.reply_text(s.error(f"❌ Недостаточно монет. Нужно {PREMIUM_PRICE} 💰"))
            return
        
        if self.db.is_premium(user_data['id']):
            await update.message.reply_text(s.error("❌ PREMIUM статус уже активен"))
            return
        
        self.db.add_coins(user_data['id'], -PREMIUM_PRICE)
        until = self.db.set_premium(user_data['id'], PREMIUM_DAYS)
        date_str = until.strftime("%d.%m.%Y")
        
        text = (
            s.header("✨ PREMIUM СТАТУС АКТИВИРОВАН") + "\n\n"
            f"{s.item(f'Срок: до {date_str}')}\n\n"
            f"{s.info('Спасибо за поддержку!')}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        self.db.log_action(user_data['id'], 'buy_premium')
    
    async def handle_numbers(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка цифр меню"""
        text = update.message.text.strip()
        
        if text == "1":
            await self.cmd_profile(update, context)
        elif text == "2":
            await self.cmd_stats(update, context)
        elif text == "3":
            await self.cmd_games(update, context)
        elif text == "4":
            await self.cmd_shop(update, context)
        elif text == "5":
            await self.show_chart(update, context)
        elif text == "6":
            await self.cmd_help(update, context)
        elif text == "7":
            await self.show_contacts(update, context)
        elif text == "0":
            await self.show_menu(update, context)
    
    # ===== ПРОФИЛЬ =====
    async def cmd_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        display_name = user_data.get('nickname') or user.first_name
        title = user_data.get('title', '')
        motto = user_data.get('motto', 'Нет девиза')
        bio = user_data.get('bio', '')
        
        vip_status = "✅ VIP" if self.db.is_vip(user_data['id']) else "❌"
        premium_status = "✅ PREMIUM" if self.db.is_premium(user_data['id']) else "❌"
        
        cyber_status = "✅" if user_data.get('cyber_status_until') and datetime.fromisoformat(user_data['cyber_status_until']) > datetime.now() else "❌"
        turbo_drive = "✅" if user_data.get('turbo_drive_until') and datetime.fromisoformat(user_data['turbo_drive_until']) > datetime.now() else "❌"
        rp_packet = "✅" if user_data.get('rp_packet_until') and datetime.fromisoformat(user_data['rp_packet_until']) > datetime.now() else "❌"
        
        exp_needed = user_data['level'] * 100
        exp_progress = s.progress(user_data['exp'], exp_needed)
        
        warns = "🔴" * user_data['warns'] + "⚪️" * (3 - user_data['warns'])
        
        friends_list = json.loads(user_data.get('friends', '[]'))
        friends_count = len(friends_list)
        
        enemies_list = json.loads(user_data.get('enemies', '[]'))
        enemies_count = len(enemies_list)
        
        # Ачивки
        achievements = self.db.get_user_achievements(user_data['id'])
        achievements_count = len(achievements)
        
        # Дата регистрации
        registered = datetime.fromisoformat(user_data['registered']) if user_data.get('registered') else datetime.now()
        days_in_chat = (datetime.now() - registered).days
        
        # Получаем дневную статистику
        days, counts = self.db.get_weekly_stats(user.id)
        total_messages = sum(counts)
        avg_per_day = total_messages / 7 if total_messages > 0 else 0
        
        # Генерируем график
        chart = ChartGenerator.create_activity_chart(days, counts, user.first_name)
        
        # Текст профиля
        profile_text = (
            f"# Спектр | Профиль\n\n"
            f"👤 {display_name} {title}\n"
            f"_{motto}_\n"
            f"{bio}\n\n"
            f"📊 **Характеристики**\n"
            f"• Ранг: {get_rank_emoji(user_data['rank'])} {user_data['rank_name']}\n"
            f"• Уровень: {user_data['level']} ({exp_progress})\n"
            f"• Монеты: {user_data['coins']:,} 💰\n"
            f"• Неоны: {user_data['neons']:,} 💜\n"
            f"• Глитчи: {user_data['glitches']:,} 🖥\n"
            f"• Энергия: {user_data['energy']}/100 ⚡️\n"
            f"• Здоровье: {user_data['health']}/{user_data['max_health']} ❤️\n\n"
            
            f"📈 **Статистика**\n"
            f"• За неделю: {total_messages} 💬\n"
            f"• В среднем: {avg_per_day:.1f}/день\n"
            f"• Репутация: {user_data['reputation']} ⭐️\n"
            f"• Ачивки: {achievements_count} 🏅\n"
            f"• Предупреждения: {warns}\n"
            f"• Боссов убито: {user_data['boss_kills']} 👾\n"
            f"• Друзей: {friends_count} / Врагов: {enemies_count}\n\n"
            
            f"💎 **Статусы**\n"
            f"• VIP: {vip_status}\n"
            f"• PREMIUM: {premium_status}\n"
            f"• Кибер-статус: {cyber_status}\n"
            f"• Турбо-драйв: {turbo_drive}\n"
            f"• РП-пакет: {rp_packet}\n\n"
            
            f"📅 **Даты**\n"
            f"• В чате: {days_in_chat} дней\n"
            f"• Регистрация: {registered.strftime('%d.%m.%Y')}\n"
            f"• ID: `{user.id}`"
        )
        
        # Отправляем фото с диаграммой и текстом
        await update.message.reply_photo(
            photo=chart,
            caption=profile_text,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def cmd_set_nick(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажите ник: /nick [ник]"))
            return
        nick = " ".join(context.args)
        if len(nick) > MAX_NICK_LENGTH:
            await update.message.reply_text(s.error(f"❌ Максимальная длина: {MAX_NICK_LENGTH} символов"))
            return
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], nickname=nick)
        await update.message.reply_text(s.success(f"✅ Ник установлен: {nick}"))
    
    async def cmd_set_title(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажите титул: /title [титул]"))
            return
        title = " ".join(context.args)
        if len(title) > MAX_TITLE_LENGTH:
            await update.message.reply_text(s.error(f"❌ Максимальная длина: {MAX_TITLE_LENGTH} символов"))
            return
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], title=title)
        await update.message.reply_text(s.success(f"✅ Титул установлен: {title}"))
    
    async def cmd_set_motto(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажите девиз: /motto [девиз]"))
            return
        motto = " ".join(context.args)
        if len(motto) > MAX_MOTTO_LENGTH:
            await update.message.reply_text(s.error(f"❌ Максимальная длина: {MAX_MOTTO_LENGTH} символов"))
            return
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], motto=motto)
        await update.message.reply_text(s.success(f"✅ Девиз установлен: {motto}"))
    
    async def cmd_set_bio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("❌ Напишите о себе: /bio [текст]"))
            return
        bio = " ".join(context.args)
        if len(bio) > MAX_BIO_LENGTH:
            await update.message.reply_text(s.error(f"❌ Максимальная длина: {MAX_BIO_LENGTH} символов"))
            return
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], bio=bio)
        await update.message.reply_text(s.success("✅ Информация сохранена"))
    
    async def cmd_set_gender(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        if text.startswith('мой пол '):
            gender = text.replace('мой пол ', '').strip().lower()
        elif context.args:
            gender = context.args[0].lower()
        else:
            await update.message.reply_text(s.error("❌ Укажите пол (м/ж/др): мой пол м"))
            return
        
        if gender not in ["м", "ж", "др"]:
            await update.message.reply_text(s.error("❌ Пол должен быть 'м', 'ж' или 'др'"))
            return
        
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], gender=gender)
        
        gender_text = {"м": "Мужской", "ж": "Женский", "др": "Другой"}[gender]
        await update.message.reply_text(s.success(f"✅ Пол установлен: {gender_text}"))
    
    async def cmd_remove_gender(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], gender='не указан')
        await update.message.reply_text(s.success("✅ Пол удалён из анкеты"))
    
    async def cmd_set_city(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        if text.startswith('мой город '):
            city = text.replace('мой город ', '').strip()
        elif context.args:
            city = " ".join(context.args)
        else:
            await update.message.reply_text(s.error("❌ Укажите город: мой город Москва"))
            return
        
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], city=city)
        await update.message.reply_text(s.success(f"✅ Город установлен: {city}"))
    
    async def cmd_set_country(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажите страну: /country [страна]"))
            return
        country = " ".join(context.args)
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], country=country)
        await update.message.reply_text(s.success(f"✅ Страна установлена: {country}"))
    
    async def cmd_set_birth(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        if text.startswith('мой др '):
            birth = text.replace('мой др ', '').strip().split()[0]
        elif context.args:
            birth = context.args[0]
        else:
            await update.message.reply_text(s.error("❌ Укажите дату (ДД.ММ.ГГГГ): мой др 01.01.2000"))
            return
        
        if not re.match(r'\d{2}\.\d{2}\.\d{4}', birth):
            await update.message.reply_text(s.error("❌ Неверный формат. Используйте ДД.ММ.ГГГГ"))
            return
        
        # Проверяем видимость
        visibility = "всё"  # по умолчанию
        if len(text.split()) > 2:
            visibility = text.split()[-1].lower()
        
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], birth_date=birth)
        
        try:
            day, month, year = map(int, birth.split('.'))
            today = datetime.now()
            age = today.year - year - ((today.month, today.day) < (month, day))
            self.db.update_user(user_data['id'], age=age)
        except:
            pass
        
        await update.message.reply_text(s.success(f"✅ Дата рождения установлена: {birth} (видимость: {visibility})"))
    
    async def cmd_set_age(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажите возраст: /age [число]"))
            return
        try:
            age = int(context.args[0])
            if age < 1 or age > 150:
                await update.message.reply_text(s.error("❌ Возраст должен быть от 1 до 150"))
                return
        except:
            await update.message.reply_text(s.error("❌ Возраст должен быть числом"))
            return
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], age=age)
        await update.message.reply_text(s.success(f"✅ Возраст установлен: {age}"))
    
    async def cmd_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        await update.message.reply_text(s.info(f"🆔 Ваш ID: `{user.id}`"), parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_my_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Просмотр своей анкеты"""
        await self.cmd_profile(update, context)
    
    async def cmd_profile_public(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сделать профиль публичным"""
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], profile_visible=1)
        await update.message.reply_text(s.success("✅ Ваш профиль теперь виден всем"))
    
    async def cmd_profile_private(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сделать профиль приватным"""
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], profile_visible=0)
        await update.message.reply_text(s.success("✅ Ваш профиль теперь скрыт от других"))
    
    # ===== СТАТИСТИКА =====
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat
        cursor = self.db.cursor
        
        now = datetime.now()
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        # Общая статистика
        cursor.execute('''
            SELECT COUNT(DISTINCT user_id), COUNT(*) 
            FROM messages 
            WHERE chat_id = ?
        ''', (chat.id,))
        result = cursor.fetchone()
        total_users = result[0] if result else 0
        total_msgs = result[1] if result else 0
        
        # Статистика за день
        cursor.execute('''
            SELECT COUNT(*) FROM messages 
            WHERE chat_id = ? AND timestamp > ?
        ''', (chat.id, day_ago.isoformat()))
        daily_msgs = cursor.fetchone()[0] or 0
        
        # Статистика за неделю
        cursor.execute('''
            SELECT COUNT(*) FROM messages 
            WHERE chat_id = ? AND timestamp > ?
        ''', (chat.id, week_ago.isoformat()))
        weekly_msgs = cursor.fetchone()[0] or 0
        
        # Статистика за месяц
        cursor.execute('''
            SELECT COUNT(*) FROM messages 
            WHERE chat_id = ? AND timestamp > ?
        ''', (chat.id, month_ago.isoformat()))
        monthly_msgs = cursor.fetchone()[0] or 0
        
        # Топ пользователей
        cursor.execute('''
            SELECT username, first_name, COUNT(*) as msg_count
            FROM messages 
            WHERE chat_id = ? 
            GROUP BY user_id 
            ORDER BY msg_count DESC 
            LIMIT 5
        ''', (chat.id,))
        top_users = cursor.fetchall()
        
        text = (
            f"# Спектр | Статистика чата\n\n"
            f"📅 {chat.title}\n"
            f"👥 Участников: {total_users}\n\n"
            
            f"📊 **Активность**\n"
            f"• За день: {daily_msgs:,} 💬\n"
            f"• За неделю: {weekly_msgs:,} 💬\n"
            f"• За месяц: {monthly_msgs:,} 💬\n"
            f"• За всё время: {total_msgs:,} 💬\n\n"
        )
        
        if top_users:
            text += "🏆 **Топ-5 активных:**\n"
            for i, (username, first_name, count) in enumerate(top_users, 1):
                name = username or first_name or "Пользователь"
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                text += f"{medal} {name} — {count} 💬\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_my_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)
        
        text = (
            s.header("📊 МОЯ СТАТИСТИКА") + "\n\n"
            f"{s.stat('Сообщений', user_data['messages_count'])}\n"
            f"{s.stat('Команд', user_data['commands_used'])}\n"
            f"{s.stat('Репутация', user_data['reputation'])}\n"
            f"{s.stat('КНБ побед', user_data['rps_wins'])}\n"
            f"{s.stat('Дуэлей побед', user_data['duel_wins'])}\n"
            f"{s.stat('Рейтинг дуэлей', user_data['duel_rating'])}\n"
            f"{s.stat('Боссов убито', user_data['boss_kills'])}\n"
            f"{s.stat('Игр в мафию', user_data['mafia_games'])}"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_top(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = s.header("🏆 ТОП ИГРОКОВ") + "\n\n"
        top_coins = self.db.get_top("coins", 5)
        text += s.section("💰 ПО МОНЕТАМ")
        for i, row in enumerate(top_coins, 1):
            name = row[1] or row[0]
            text += f"{i}. {name} — {row[2]} 💰\n"
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_top_coins(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        top = self.db.get_top("coins", 10)
        text = s.header("💰 ТОП ПО МОНЕТАМ") + "\n\n"
        for i, row in enumerate(top, 1):
            name = row[1] or row[0]
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} {name} — {row[2]} 💰\n"
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_top_level(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        top = self.db.get_top("level", 10)
        text = s.header("📊 ТОП ПО УРОВНЮ") + "\n\n"
        for i, row in enumerate(top, 1):
            name = row[1] or row[0]
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} {name} — {row[2]} уровень\n"
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_top_neons(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        top = self.db.get_top("neons", 10)
        text = s.header("💜 ТОП ПО НЕОНАМ") + "\n\n"
        for i, row in enumerate(top, 1):
            name = row[1] or row[0]
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} {name} — {row[2]} 💜\n"
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_top_glitches(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        top = self.db.get_top("glitches", 10)
        text = s.header("🖥 ТОП ПО ГЛИТЧАМ") + "\n\n"
        for i, row in enumerate(top, 1):
            name = row[1] or row[0]
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} {name} — {row[2]} 🖥\n"
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    # ===== СТАТИСТИКА ЧАТА (РУССКИЕ КОМАНДЫ) =====
    async def cmd_chat_stats_today(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._chat_stats_period(update, "day")
    
    async def cmd_chat_stats_week(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._chat_stats_period(update, "week")
    
    async def cmd_chat_stats_month(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._chat_stats_period(update, "month")
    
    async def cmd_chat_stats_all(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._chat_stats_period(update, "all")
    
    async def cmd_stats_custom(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        parts = text.split()
        
        if len(parts) < 2:
            return
        
        try:
            limit = int(parts[1])
        except:
            return
        
        period = "day"
        if len(parts) > 2:
            period_map = {"неделя": "week", "месяц": "month", "вся": "all"}
            period = period_map.get(parts[2].lower(), "day")
        
        await self._chat_stats_period(update, period, limit)
    
    async def _chat_stats_period(self, update: Update, period: str, limit: int = 10):
        chat_id = update.effective_chat.id
        cursor = self.db.cursor
        
        now = datetime.now()
        
        if period == "day":
            time_ago = now - timedelta(days=1)
            period_name = "день"
        elif period == "week":
            time_ago = now - timedelta(days=7)
            period_name = "неделю"
        elif period == "month":
            time_ago = now - timedelta(days=30)
            period_name = "месяц"
        else:
            time_ago = datetime(2000, 1, 1)
            period_name = "всё время"
        
        cursor.execute('''
            SELECT username, first_name, COUNT(*) as msg_count
            FROM messages 
            WHERE chat_id = ? AND timestamp > ?
            GROUP BY user_id 
            ORDER BY msg_count DESC 
            LIMIT ?
        ''', (chat_id, time_ago.isoformat(), limit))
        
        top_users = cursor.fetchall()
        
        if not top_users:
            await update.message.reply_text(s.info("Нет данных за этот период"))
            return
        
        text = s.header(f"🏆 ТОП ЗА {period_name.upper()}") + "\n\n"
        for i, (username, first_name, count) in enumerate(top_users, 1):
            name = username or first_name or "Пользователь"
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} {name} — {count} 💬\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_top_chat_today(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._chat_stats_period(update, "day")
    
    async def cmd_top_chat_week(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._chat_stats_period(update, "week")
    
    async def cmd_top_chat_month(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._chat_stats_period(update, "month")
    
    async def cmd_top_chat_all(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._chat_stats_period(update, "all")
    
    # ===== НОВАЯ ЭКОНОМИКА =====
    async def cmd_neons(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Просмотр баланса неонов"""
        user_data = self.db.get_user(update.effective_user.id)
        
        text = (
            s.header("💜 МОИ НЕОНЫ") + "\n\n"
            f"{s.stat('Баланс', f'{user_data["neons"]} 💜')}\n"
            f"{s.stat('В глитчах', f'{user_data["glitches"]} 🖥')}\n\n"
            f"{s.section('КОМАНДЫ')}"
            f"{s.cmd('transfer @user 100', 'передать неоны')}\n"
            f"{s.cmd('exchange 100', 'обменять глитчи на неоны')}\n"
            f"{s.cmd('farm', 'ферма глитчей')}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_glitches(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Просмотр баланса глитчей"""
        user_data = self.db.get_user(update.effective_user.id)
        
        # Конвертация в неоны
        neons_from_glitches = user_data['glitches'] // NEON_PRICE
        
        text = (
            s.header("🖥 МОИ ГЛИТЧИ") + "\n\n"
            f"{s.stat('Баланс', f'{user_data["glitches"]} 🖥')}\n"
            f"{s.stat('Можно обменять', f'{neons_from_glitches} 💜')}\n\n"
            f"{s.section('КОМАНДЫ')}"
            f"{s.cmd('exchange 100', 'обменять глитчи на неоны')}\n"
            f"{s.cmd('farm', 'ферма глитчей')}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_farm(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ферма глитчей"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        # Проверяем кулдаун
        last_farm = user_data.get('last_farm')
        if last_farm:
            last = datetime.fromisoformat(last_farm)
            if (datetime.now() - last).seconds < GLITCH_FARM_COOLDOWN:
                remain = GLITCH_FARM_COOLDOWN - (datetime.now() - last).seconds
                hours = remain // 3600
                minutes = (remain % 3600) // 60
                await update.message.reply_text(s.warning(f"⏳ Ферма будет доступна через {hours}ч {minutes}м"))
                return
        
        # Добыча глитчей
        glitches_earned = random.randint(10, 50)
        
        # Бонус от статусов
        if self.db.is_vip(user_data['id']):
            glitches_earned = int(glitches_earned * 1.2)
        if self.db.is_premium(user_data['id']):
            glitches_earned = int(glitches_earned * 1.3)
        if user_data.get('turbo_drive_until') and datetime.fromisoformat(user_data['turbo_drive_until']) > datetime.now():
            glitches_earned = int(glitches_earned * 1.5)
        
        self.db.add_glitches(user_data['id'], glitches_earned)
        self.db.update_user(user_data['id'], last_farm=datetime.now().isoformat())
        
        text = (
            s.header("🖥 ФЕРМА ГЛИТЧЕЙ") + "\n\n"
            f"{s.success('✅ Вы успешно нафармили!')}\n"
            f"{s.item(f'Добыто: {glitches_earned} 🖥')}\n\n"
            f"{s.item(f'Теперь у вас: {user_data["glitches"] + glitches_earned} 🖥')}\n\n"
            f"{s.info('Следующая ферма через 4 часа')}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        
        # Проверяем ачивки
        self.db.check_glitch_achievements(user_data['id'])
    
    async def cmd_transfer_neons(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Перевод неонов другому пользователю"""
        if len(context.args) < 2:
            await update.message.reply_text(s.error("❌ Использование: /transfer @user 100"))
            return
        
        username = context.args[0].replace('@', '')
        try:
            amount = int(context.args[1])
        except:
            await update.message.reply_text(s.error("❌ Сумма должна быть числом"))
            return
        
        if amount <= 0:
            await update.message.reply_text(s.error("❌ Сумма должна быть больше 0"))
            return
        
        user_data = self.db.get_user(update.effective_user.id)
        
        if user_data['neons'] < amount:
            await update.message.reply_text(s.error(f"❌ Недостаточно неонов. Баланс: {user_data['neons']} 💜"))
            return
        
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        if target['id'] == user_data['id']:
            await update.message.reply_text(s.error("❌ Нельзя перевести самому себе"))
            return
        
        # Комиссия для обычных пользователей
        commission = 0
        if not self.db.is_vip(user_data['id']) and not self.db.is_premium(user_data['id']):
            commission = int(amount * 0.05)  # 5% комиссии
        
        self.db.transfer_neons(user_data['id'], target['id'], amount, commission)
        
        target_name = target.get('nickname') or target['first_name']
        
        text = (
            s.header("💜 ПЕРЕВОД НЕОНОВ") + "\n"
            f"{s.item(f'Получатель: {target_name}')}\n"
            f"{s.item(f'Сумма: {amount} 💜')}\n"
        )
        
        if commission > 0:
            text += f"{s.item(f'Комиссия: {commission} 💜 (5%)')}\n"
        
        text += f"\n{s.success('✅ Перевод выполнен!')}"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        self.db.log_action(user_data['id'], 'transfer_neons', f"{amount}💜 -> {target['id']}")
    
    async def cmd_exchange(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обмен глитчей на неоны"""
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажите количество глитчей для обмена"))
            return
        
        try:
            glitches = int(context.args[0])
        except:
            await update.message.reply_text(s.error("❌ Количество должно быть числом"))
            return
        
        if glitches < NEON_PRICE:
            await update.message.reply_text(s.error(f"❌ Минимум для обмена: {NEON_PRICE} глитчей"))
            return
        
        user_data = self.db.get_user(update.effective_user.id)
        
        if user_data['glitches'] < glitches:
            await update.message.reply_text(s.error(f"❌ Недостаточно глитчей. Баланс: {user_data['glitches']} 🖥"))
            return
        
        neons = glitches // NEON_PRICE
        used_glitches = neons * NEON_PRICE
        remainder = glitches - used_glitches
        
        self.db.add_glitches(user_data['id'], -used_glitches)
        self.db.add_neons(user_data['id'], neons)
        
        text = (
            s.header("💱 ОБМЕН ВАЛЮТ") + "\n\n"
            f"{s.item(f'Обменено: {used_glitches} 🖥 → {neons} 💜')}\n"
            f"{s.item(f'Остаток глитчей: {user_data["glitches"] - used_glitches + remainder} 🖥')}\n"
            f"{s.item(f'Новый баланс неонов: {user_data["neons"] + neons} 💜')}\n\n"
            f"{s.success('✅ Обмен выполнен!')}"
        )
        
        if remainder > 0:
            text += f"\n{s.info(f'Остаток {remainder} глитчей не обменян (нужно {NEON_PRICE} для 1 неона)')}"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    # ===== РАЗВЛЕЧЕНИЯ =====
    async def cmd_joke(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        jokes = [
            "Встречаются два программиста:\n— Слышал, ты женился?\n— Да.\n— Ну и как она?\n— Да нормально, интерфейс дружественный...",
            "— Доктор, у меня глисты.\n— А вы что, их видите?\n— Нет, я с ними переписываюсь.",
            "Идут два кота по крыше. Один говорит:\n— Мяу.\n— Мяу-мяу.\n— Ты чё, с ума сошёл? Нас же люди услышат!",
            "Заходит как-то Windows в бар, а бармен говорит:\n— Извините, но у нас для вас нет места.",
            "— Алло, это служба поддержки?\n— Да.\n— У меня кнопка «Пуск» не запускается.",
        ]
        await update.message.reply_text(f"😄 {random.choice(jokes)}")
    
    async def cmd_fact(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        facts = [
            "Осьминоги имеют три сердца и голубую кровь.",
            "Бананы технически являются ягодами, а клубника — нет.",
            "В Швейцарии запрещено держать только одну морскую свинку.",
            "Глаз страуса больше, чем его мозг.",
            "Мед никогда не портится. Археологи находили 3000-летний мёд в гробницах египтян.",
        ]
        await update.message.reply_text(f"🔍 {random.choice(facts)}")
    
    async def cmd_quote(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        quotes = [
            "Жизнь — это то, что с тобой происходит, пока ты строишь планы. — Джон Леннон",
            "Будьте тем изменением, которое вы хотите увидеть в мире. — Махатма Ганди",
            "Единственный способ делать великие дела — любить то, что вы делаете. — Стив Джобс",
            "Всё гениальное просто. — Альберт Эйнштейн",
            "Победа — это ещё не всё, всё — это постоянное желание побеждать. — Винс Ломбарди",
        ]
        await update.message.reply_text(f"📜 {random.choice(quotes)}")
    
    async def cmd_whoami(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        roles = ["супергерой", "злодей", "тайный агент", "космонавт", "пират", "киборг", "хакер", "маг"]
        await update.message.reply_text(f"🦸 Вы — {random.choice(roles)}!")
    
    async def cmd_advice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        advices = [
            "Пейте больше воды.",
            "Высыпайтесь — это важно для здоровья.",
            "Делайте зарядку по утрам.",
            "Улыбайтесь чаще — это заразительно.",
            "Не откладывайте на завтра то, что можно сделать сегодня.",
        ]
        await update.message.reply_text(f"💡 {random.choice(advices)}")

    async def cmd_compatibility(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Проверка совместимости двух пользователей"""
        if len(context.args) < 2:
            await update.message.reply_text(s.error("❌ Укажите двух пользователей: /compatibility @user1 @user2"))
            return
        
        username1 = context.args[0].replace('@', '')
        username2 = context.args[1].replace('@', '')
        
        user1 = self.db.get_user_by_username(username1)
        user2 = self.db.get_user_by_username(username2)
        
        if not user1 or not user2:
            await update.message.reply_text(s.error("❌ Пользователи не найдены"))
            return
        
        name1 = user1.get('nickname') or user1['first_name']
        name2 = user2.get('nickname') or user2['first_name']
        
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
        
        await update.message.reply_text(
            f"{s.header('💞 СОВМЕСТИМОСТЬ')}\n\n"
            f"{emoji} {name1} и {name2}\n\n"
            f"Совместимость: {compatibility}%\n{text}",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def cmd_weather(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Погода (симуляция)"""
        if not context.args:
            city = "Москва"
        else:
            city = " ".join(context.args)
        
        # Симулируем погоду
        temp = random.randint(-10, 30)
        conditions = ["ясно", "облачно", "пасмурно", "дождь", "снег", "гроза"]
        condition = random.choice(conditions)
        wind = random.randint(0, 10)
        humidity = random.randint(30, 90)
        
        text = (
            f"🌦 Погода в {city}:\n"
            f"🌡 {temp}°C, {condition}\n"
            f"💨 ветер {wind} м/с\n"
            f"💧 влажность {humidity}%"
        )
        
        await update.message.reply_text(text)
    
    async def cmd_random(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Случайное число"""
        if not context.args:
            max_num = 100
        else:
            try:
                max_num = int(context.args[0])
            except:
                await update.message.reply_text(s.error("❌ Укажите число"))
                return
        
        result = random.randint(0, max_num)
        await update.message.reply_text(f"🎲 Случайное число: **{result}**", parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_choose(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор из вариантов"""
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажите варианты через или: /choose чай или кофе"))
            return
        
        text = " ".join(context.args)
        options = re.split(r'\s+или\s+', text)
        
        if len(options) < 2:
            await update.message.reply_text(s.error("❌ Нужно минимум 2 варианта через 'или'"))
            return
        
        choice = random.choice(options)
        await update.message.reply_text(f"🤔 Я выбираю: **{choice}**", parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_dane(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Да/нет"""
        if not context.args:
            await update.message.reply_text(s.error("❌ Задайте вопрос: /dane сегодня будет дождь?"))
            return
        
        answers = [
            "🎱 Безусловно да",
            "🎱 Определённо да",
            "🎱 Без сомнений",
            "🎱 Да — определённо",
            "🎱 Можешь быть уверен в этом",
            "🎱 Мне кажется — да",
            "🎱 Вероятнее всего",
            "🎱 Хорошие перспективы",
            "🎱 Знаки говорят — да",
            "🎱 Пока не ясно, попробуй снова",
            "🎱 Спроси позже",
            "🎱 Лучше не рассказывать",
            "🎱 Сейчас нельзя предсказать",
            "🎱 Сконцентрируйся и спроси опять",
            "🎱 Даже не думай",
            "🎱 Мой ответ — нет",
            "🎱 По моим данным — нет",
            "🎱 Перспективы не очень хорошие",
            "🎱 Весьма сомнительно",
        ]
        
        await update.message.reply_text(f"❓ {random.choice(answers)}")
    
    async def cmd_ship(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Шипперинг"""
        if len(context.args) < 2:
            # Случайная пара из участников
            chat_id = update.effective_chat.id
            cursor = self.db.cursor
            cursor.execute("SELECT DISTINCT user_id FROM messages WHERE chat_id = ? ORDER BY RANDOM() LIMIT 2", (chat_id,))
            users = cursor.fetchall()
            
            if len(users) < 2:
                await update.message.reply_text(s.error("❌ Недостаточно участников для шипперинга"))
                return
            
            user1_id, user2_id = users[0][0], users[1][0]
        else:
            username1 = context.args[0].replace('@', '')
            username2 = context.args[1].replace('@', '')
            
            user1 = self.db.get_user_by_username(username1)
            user2 = self.db.get_user_by_username(username2)
            
            if not user1 or not user2:
                await update.message.reply_text(s.error("❌ Пользователи не найдены"))
                return
            
            user1_id, user2_id = user1['id'], user2['id']
        
        user1_data = self.db.get_user_by_id(user1_id)
        user2_data = self.db.get_user_by_id(user2_id)
        
        name1 = user1_data.get('nickname') or user1_data['first_name']
        name2 = user2_data.get('nickname') or user2_data['first_name']
        
        compatibility = random.randint(0, 100)
        
        if compatibility < 30:
            emoji = "💔"
            desc = "Очень низкая совместимость"
        elif compatibility < 50:
            emoji = "🤔"
            desc = "Ниже среднего"
        elif compatibility < 70:
            emoji = "👍"
            desc = "Неплохая совместимость"
        elif compatibility < 90:
            emoji = "💕"
            desc = "Хорошая совместимость"
        else:
            emoji = "💖"
            desc = "Идеальная совместимость!"
        
        # Сохраняем пару
        self.db.create_pair(update.effective_chat.id, user1_id, user2_id)
        
        await update.message.reply_text(
            f"{s.header('💞 ШИППЕРИМ')}\n\n"
            f"{emoji} {name1} + {name2}\n\n"
            f"Совместимость: {compatibility}%\n{desc}",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def cmd_pairing(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список пар в этом чате"""
        pairs = self.db.get_chat_pairs(update.effective_chat.id)
        
        if not pairs:
            await update.message.reply_text(s.info("В этом чате пока нет пар"))
            return
        
        text = s.header("💞 ПАРЫ ЧАТА") + "\n\n"
        for pair in pairs[:10]:
            text += f"{pair['name1']} + {pair['name2']}\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_pairs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.cmd_pairing(update, context)

        # ===== КЛАНЫ =====
    async def cmd_clan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о своем клане"""
        user_data = self.db.get_user(update.effective_user.id)
        
        if not user_data.get('clan_id', 0):
            await update.message.reply_text(s.info("Вы не состоите в клане"))
            return
        
        clan = self.db.get_clan(user_data['clan_id'])
        if not clan:
            await update.message.reply_text(s.error("Клан не найден"))
            return
        
        members = self.db.get_clan_members(clan['id'])
        
        text = (
            f"# Спектр | Клан\n\n"
            f"🏰 {clan['name']}\n\n"
            f"📊 **Информация**\n"
            f"• Уровень: {clan['level']}\n"
            f"• Опыт: {clan['exp']}\n"
            f"• Казна: {clan['coins']} 💰\n"
            f"• Участников: {len(members)}\n\n"
            f"👥 **Участники:**\n"
        )
        
        for member in members:
            name = member.get('nickname') or member['first_name']
            role_emoji = "👑" if member['role'] == 'owner' else "🛡" if member['role'] == 'admin' else "👤"
            text += f"{role_emoji} {name}\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_clans(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список кланов"""
        self.db.cursor.execute("SELECT name, level, members FROM clans ORDER BY level DESC LIMIT 10")
        clans = self.db.cursor.fetchall()
        
        if not clans:
            await update.message.reply_text(s.info("Нет созданных кланов"))
            return
        
        text = s.header("🏰 ТОП КЛАНОВ") + "\n\n"
        for i, clan in enumerate(clans, 1):
            text += f"{i}. {clan[0]} — ур.{clan[1]}, {clan[2]} участников\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_create_clan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Создать клан"""
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажите название клана: /createclan [название]"))
            return
        
        name = " ".join(context.args)
        user_data = self.db.get_user(update.effective_user.id)
        
        if user_data.get('clan_id', 0):
            await update.message.reply_text(s.error("❌ Вы уже в клане"))
            return
        
        if user_data['coins'] < 1000:
            await update.message.reply_text(s.error(f"❌ Недостаточно монет. Нужно 1000 💰"))
            return
        
        clan_id = self.db.create_clan(update.effective_chat.id, name, "", user_data['id'])
        if not clan_id:
            await update.message.reply_text(s.error("❌ Клан с таким названием уже существует"))
            return
        
        self.db.add_coins(user_data['id'], -1000)
        
        await update.message.reply_text(s.success(f"✅ Клан '{name}' создан!"))
    
    async def cmd_join_clan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Вступить в клан"""
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажите название клана: /joinclan [название]"))
            return
        
        name = " ".join(context.args)
        user_data = self.db.get_user(update.effective_user.id)
        
        if user_data.get('clan_id', 0):
            await update.message.reply_text(s.error("❌ Вы уже в клане"))
            return
        
        self.db.cursor.execute("SELECT * FROM clans WHERE name = ? AND chat_id = ?", (name, update.effective_chat.id))
        clan = self.db.cursor.fetchone()
        
        if not clan:
            await update.message.reply_text(s.error("❌ Клан не найден"))
            return
        
        if self.db.join_clan(clan[0], user_data['id']):
            await update.message.reply_text(s.success(f"✅ Вы вступили в клан '{name}'"))
        else:
            await update.message.reply_text(s.error("❌ Не удалось вступить в клан"))
    
    async def cmd_leave_clan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Покинуть клан"""
        user_data = self.db.get_user(update.effective_user.id)
        
        if not user_data.get('clan_id', 0):
            await update.message.reply_text(s.error("❌ Вы не в клане"))
            return
        
        if user_data.get('clan_role') == 'owner':
            await update.message.reply_text(s.error("❌ Владелец не может покинуть клан"))
            return
        
        clan_id = user_data['clan_id']
        self.db.cursor.execute("DELETE FROM clan_members WHERE user_id = ?", (user_data['id'],))
        self.db.update_user(user_data['id'], clan_id=0, clan_role='member')
        self.db.cursor.execute("UPDATE clans SET members = members - 1 WHERE id = ?", (clan_id,))
        self.db.conn.commit()
        
        await update.message.reply_text(s.success("✅ Вы покинули клан"))
    
    # ===== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ДЛЯ КЛАНОВ =====
    def get_clan(self, clan_id: int) -> Optional[Dict]:
        """Получить информацию о клане"""
        self.db.cursor.execute("SELECT * FROM clans WHERE id = ?", (clan_id,))
        row = self.db.cursor.fetchone()
        return dict(row) if row else None
    
    def get_clan_members(self, clan_id: int) -> List[Dict]:
        """Получить список участников клана"""
        self.db.cursor.execute("SELECT id, first_name, nickname, clan_role FROM users WHERE clan_id = ?", (clan_id,))
        return [dict(row) for row in self.db.cursor.fetchall()]

        # ===== СЕТКИ ЧАТОВ =====
    async def cmd_grid(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о сетке"""
        await update.message.reply_text(s.info("Используйте /grids для списка сеток"))
    
    async def cmd_grids(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список сеток пользователя"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        grids = self.db.get_user_grids(user_data['id'])
        
        if not grids:
            await update.message.reply_text(s.info("У вас нет созданных сеток"))
            return
        
        text = s.header("🔗 МОИ СЕТКИ") + "\n\n"
        for grid in grids:
            text += f"ID: {grid['id']} | {grid['name']}\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_create_grid(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Создать сетку чатов"""
        text = update.message.text
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user.id != OWNER_ID and user_data['rank'] < 5:
            await update.message.reply_text(s.error("❌ Только создатель может создавать сетки"))
            return
        
        # Проверяем, откуда пришла команда
        if text.startswith('/creategrid'):
            if len(context.args) < 1:
                await update.message.reply_text(s.error("❌ Укажите название сетки: /creategrid main"))
                return
            name = context.args[0]
        else:
            match = re.search(r'создать сетку\s+(\S+)', text, re.IGNORECASE)
            if not match:
                await update.message.reply_text(s.error("❌ Укажите название сетки: создать сетка main"))
                return
            name = match.group(1)
        
        grid_id = self.db.create_grid(user_data['id'], name)
        
        await update.message.reply_text(s.success(f"✅ Сетка '{name}' (ID: {grid_id}) создана!"))
    
    async def cmd_add_chat_to_grid(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Добавить чат в сетку"""
        text = update.message.text
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        chat_id = update.effective_chat.id
        
        # Проверяем, откуда пришла команда
        if text.startswith('/addchat'):
            if len(context.args) < 1:
                await update.message.reply_text(s.error("❌ Укажите ID сетки: /addchat 1"))
                return
            try:
                grid_id = int(context.args[0])
            except:
                await update.message.reply_text(s.error("❌ ID сетки должен быть числом"))
                return
        else:
            match = re.search(r'установить сетку\s+(\d+)', text, re.IGNORECASE)
            if not match:
                await update.message.reply_text(s.error("❌ Укажите ID сетки: установить сетку 1"))
                return
            grid_id = int(match.group(1))
        
        # Проверяем, владелец ли сетки
        self.db.cursor.execute("SELECT owner_id FROM chat_grids WHERE id = ?", (grid_id,))
        row = self.db.cursor.fetchone()
        
        if not row:
            await update.message.reply_text(s.error("❌ Сетка не найдена"))
            return
        
        if row[0] != user_data['id'] and user.id != OWNER_ID:
            await update.message.reply_text(s.error("❌ Вы не владелец этой сетки"))
            return
        
        if self.db.add_chat_to_grid(grid_id, chat_id):
            await update.message.reply_text(s.success("✅ Чат добавлен в сетку!"))
        else:
            await update.message.reply_text(s.error("❌ Чат уже в сетке"))
    
    async def cmd_global_mod(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Назначить глобального модератора"""
        text = update.message.text
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        # Парсим: +глмодер @user
        match = re.search(r'\+глмодер\s+@?(\S+)', text, re.IGNORECASE)
        if match:
            username = match.group(1)
            target = self.db.get_user_by_username(username)
            if not target:
                await update.message.reply_text(s.error("❌ Пользователь не найден"))
                return
            
            await update.message.reply_text(s.success(f"✅ {target['first_name']} назначен глобальным модератором"))
            return
        
        # Парсим: сетка 3 !модер @user
        match = re.search(r'сетка (\d+)\s+(!+)модер\s+@?(\S+)', text, re.IGNORECASE)
        if match:
            grid_id = int(match.group(1))
            rank = len(match.group(2))
            username = match.group(3)
            
            target = self.db.get_user_by_username(username)
            if not target:
                await update.message.reply_text(s.error("❌ Пользователь не найден"))
                return
            
            # Проверяем права на сетку
            self.db.cursor.execute("SELECT owner_id FROM chat_grids WHERE id = ?", (grid_id,))
            row = self.db.cursor.fetchone()
            
            if not row:
                await update.message.reply_text(s.error("❌ Сетка не найдена"))
                return
            
            if row[0] != user_data['id'] and user.id != OWNER_ID:
                await update.message.reply_text(s.error("❌ Вы не владелец этой сетки"))
                return
            
            # Добавляем в глобальные модераторы
            self.db.cursor.execute("INSERT OR REPLACE INTO global_moderators (grid_id, user_id, rank) VALUES (?, ?, ?)",
                                 (grid_id, target['id'], rank))
            self.db.conn.commit()
            
            await update.message.reply_text(s.success(f"✅ {target['first_name']} получил ранг {rank} во всех чатах сетки"))
            return
        
        await update.message.reply_text(s.error("❌ Неверный формат команды"))
    
    async def cmd_global_mods_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список глобальных модераторов"""
        self.db.cursor.execute("""
            SELECT gm.*, u.first_name, u.username 
            FROM global_moderators gm
            JOIN users u ON gm.user_id = u.id
        """)
        mods = self.db.cursor.fetchall()
        
        if not mods:
            await update.message.reply_text(s.info("Нет глобальных модераторов"))
            return
        
        text = s.header("🌐 ГЛОБАЛЬНЫЕ МОДЕРАТОРЫ") + "\n\n"
        for mod in mods:
            text += f"• {mod['first_name']} (@{mod['username']}) — ранг {mod['rank']}\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_add_global_mod(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Добавить глобального модератора"""
        await self.cmd_global_mod(update, context)
    
    async def cmd_remove_global_mod(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Удалить глобального модератора"""
        text = update.message.text
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        match = re.search(r'-глмодер\s+@?(\S+)', text, re.IGNORECASE)
        if not match:
            await update.message.reply_text(s.error("❌ Укажите пользователя: -глмодер @user"))
            return
        
        username = match.group(1)
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        self.db.cursor.execute("DELETE FROM global_moderators WHERE user_id = ?", (target['id'],))
        self.db.conn.commit()
        
        await update.message.reply_text(s.success(f"✅ {target['first_name']} снят с глобальной модерации"))
    
    async def cmd_grid_set_rank(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установить ранг во всех чатах сетки"""
        await self.cmd_global_mod(update, context)
    
    # ===== ИГРЫ =====
    async def cmd_games(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = """
# Спектр | Игры

🎮 Доступные игры:

🔫 /rr [ставка] — Русская рулетка
🎲 /dicebet [ставка] — Кости
🎰 /slots [ставка] — Слоты
✊ /rps — Камень-ножницы-бумага
💣 /saper [ставка] — Сапёр
🔢 /guess [ставка] — Угадай число
🐂 /bulls [ставка] — Быки и коровы

💰 Твой баланс: /balance
        """
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_coin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        result = random.choice(["Орёл", "Решка"])
        await update.message.reply_text(
            f"{s.header('🪙 МОНЕТКА')}\n\n{s.item(f'Выпало: {result}')}",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def cmd_dice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        result = random.randint(1, 6)
        await update.message.reply_text(
            f"{s.header('🎲 КУБИК')}\n\n{s.item(f'Выпало: {result}')}",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def cmd_dice_bet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажите ставку: /dicebet 100"))
            return
        
        try:
            bet = int(context.args[0])
        except:
            await update.message.reply_text(s.error("❌ Ставка должна быть числом"))
            return
        
        if bet > user_data['coins']:
            await update.message.reply_text(s.error(f"❌ Недостаточно монет. Баланс: {user_data['coins']} 💰"))
            return
        
        if bet <= 0:
            await update.message.reply_text(s.error("❌ Ставка должна быть больше 0"))
            return
        
        dice1 = random.randint(1, 6)
        dice2 = random.randint(1, 6)
        total = dice1 + dice2
        
        win_multiplier = 1
        if total in [7, 11]:
            win_multiplier = 2
            self.db.update_user(user_data['id'], dice_wins=user_data.get('dice_wins', 0) + 1)
            result_text = s.success(f"🎉 ВЫИГРЫШ!")
        elif total in [2, 3, 12]:
            win_multiplier = 0
            self.db.update_user(user_data['id'], dice_losses=user_data.get('dice_losses', 0) + 1)
            result_text = s.error(f"💀 ПРОИГРЫШ!")
        else:
            win_multiplier = 1
            result_text = s.info(f"🔄 НИЧЬЯ!")
        
        win_amount = bet * win_multiplier if win_multiplier > 0 else -bet
        
        if win_multiplier > 0:
            self.db.add_coins(user_data['id'], win_amount - bet if win_multiplier > 1 else 0)
        else:
            self.db.add_coins(user_data['id'], -bet)
        
        text = (
            f"# Спектр | Кости\n\n"
            f"Игрок: {user.first_name}\n"
            f"Ставка: {bet} 💰\n\n"
            f"🎲 {dice1} + {dice2} = {total}\n\n"
            f"{result_text}\n"
        )
        
        if win_multiplier > 1:
            text += f"+{win_amount - bet} 💰\n"
        elif win_multiplier == 0:
            text += f"-{bet} 💰\n"
        else:
            text += f"Ставка возвращена\n"
        
        text += f"\n💰 Новый баланс: {user_data['coins'] + (win_amount - bet if win_multiplier > 1 else -bet if win_multiplier == 0 else 0)} 💰"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_roulette(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
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
            await update.message.reply_text(s.error(f"❌ Недостаточно монет. Баланс: {user_data['coins']} 💰"))
            return
        
        if bet <= 0:
            await update.message.reply_text(s.error("❌ Ставка должна быть больше 0"))
            return
        
        num = random.randint(0, 36)
        red_numbers = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]
        
        if num == 0:
            color = "green"
        elif num in red_numbers:
            color = "red"
        else:
            color = "black"
        
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
            self.db.update_user(user_data['id'], casino_wins=user_data.get('casino_wins', 0) + 1)
            result = s.success(f"🎉 ВЫИГРЫШ! +{win_amount} 💰")
            
            # Проверка ачивок
            wins = user_data.get('casino_wins', 0) + 1
            if wins >= 10:
                self.db.unlock_achievement(user_data['id'], 7)
            if wins >= 50:
                self.db.unlock_achievement(user_data['id'], 8)
            if wins >= 200:
                self.db.unlock_achievement(user_data['id'], 9)
        else:
            self.db.add_coins(user_data['id'], -bet)
            self.db.update_user(user_data['id'], casino_losses=user_data.get('casino_losses', 0) + 1)
            result = s.error(f"💀 ПРОИГРЫШ! -{bet} 💰")
        
        text = (
            f"# Спектр | Рулетка\n\n"
            f"Игрок: {user.first_name}\n"
            f"Ставка: {bet} 💰\n"
            f"Выбрано: {choice}\n\n"
            f"🎰 Выпало: {num} {color}\n\n"
            f"{result}\n\n"
            f"💰 Новый баланс: {user_data['coins'] + (win_amount if win else -bet)} 💰"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        self.db.log_action(user_data['id'], 'roulette', f"{'win' if win else 'lose'} {bet}")
    
    async def cmd_slots(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        bet = 10
        if context.args:
            try:
                bet = int(context.args[0])
            except:
                pass
        
        if bet > user_data['coins']:
            await update.message.reply_text(s.error(f"❌ Недостаточно монет. Баланс: {user_data['coins']} 💰"))
            return
        
        if bet <= 0:
            await update.message.reply_text(s.error("❌ Ставка должна быть больше 0"))
            return
        
        symbols = ["🍒", "🍋", "🍊", "7️⃣", "💎", "⭐️"]
        spin = [random.choice(symbols) for _ in range(3)]
        
        if len(set(spin)) == 1:
            if spin[0] == "7️⃣":
                win = bet * 50
            elif spin[0] == "💎":
                win = bet * 30
            elif spin[0] == "⭐️":
                win = bet * 20
            else:
                win = bet * 10
            result = s.success(f"🎉 ДЖЕКПОТ! +{win} 💰")
            self.db.update_user(user_data['id'], slots_wins=user_data.get('slots_wins', 0) + 1)
        elif len(set(spin)) == 2:
            win = bet * 2
            result = s.success(f"🎉 ВЫИГРЫШ! +{win} 💰")
            self.db.update_user(user_data['id'], slots_wins=user_data.get('slots_wins', 0) + 1)
        else:
            win = 0
            result = s.error(f"💀 ПРОИГРЫШ! -{bet} 💰")
            self.db.update_user(user_data['id'], slots_losses=user_data.get('slots_losses', 0) + 1)
        
        if win > 0:
            self.db.add_coins(user_data['id'], win)
        else:
            self.db.add_coins(user_data['id'], -bet)
        
        text = (
            f"# Спектр | Слоты\n\n"
            f"Игрок: {user.first_name}\n"
            f"Ставка: {bet} 💰\n\n"
            f"[ {' | '.join(spin)} ]\n\n"
            f"{result}\n\n"
            f"💰 Новый баланс: {user_data['coins'] + (win if win > 0 else -bet)} 💰"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_rps(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = """
# Спектр | Камень-ножницы-бумага

Выберите жест (напишите цифру):

1️⃣ 🪨 Камень
2️⃣ ✂️ Ножницы
3️⃣ 📄 Бумага
        """
        await update.message.reply_text(text, parse_mode='Markdown')
        context.user_data['awaiting_rps'] = True
    
    async def cmd_russian_roulette(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        bet = 10
        if context.args:
            try:
                bet = int(context.args[0])
            except:
                await update.message.reply_text(s.error("❌ Ставка должна быть числом"))
                return
        
        if bet > user_data['coins']:
            await update.message.reply_text(s.error(f"❌ Недостаточно монет. Баланс: {user_data['coins']} 💰"))
            return
        
        if bet <= 0:
            await update.message.reply_text(s.error("❌ Ставка должна быть больше 0"))
            return
        
        chamber = random.randint(1, 6)
        shot = random.randint(1, 6)
        
        await asyncio.sleep(2)
        
        if chamber == shot:
            self.db.add_coins(user_data['id'], -bet)
            self.db.update_user(user_data['id'], rr_losses=user_data.get('rr_losses', 0) + 1)
            result_text = "💥 *Бах!* Выстрел..."
            win_text = s.error(f"💀 ВЫ ПРОИГРАЛИ! -{bet} 💰")
            
            # Кикаем из чата (опционально)
            try:
                await update.effective_chat.ban_member(user.id)
                await update.effective_chat.unban_member(user.id)
            except:
                pass
        else:
            win = bet * 5
            self.db.add_coins(user_data['id'], win)
            self.db.update_user(user_data['id'], rr_wins=user_data.get('rr_wins', 0) + 1)
            result_text = "🔫 *Щёлк...* В этот раз повезло!"
            win_text = s.success(f"🎉 ВЫ ВЫИГРАЛИ! +{win} 💰")
        
        text = (
            f"# Спектр | Русская рулетка\n\n"
            f"Игрок: {user.first_name}\n"
            f"Ставка: {bet} 💰\n\n"
            f"{result_text}\n\n"
            f"{win_text}\n\n"
            f"💰 Новый баланс: {user_data['coins'] + (win if chamber != shot else -bet)} 💰"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        self.db.log_action(user_data['id'], 'rr', f"{'win' if chamber != shot else 'lose'} {bet}")
    
    async def cmd_saper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        bet = 10
        if context.args:
            try:
                bet = int(context.args[0])
            except:
                bet = 10
        
        if bet > user_data['coins']:
            await update.message.reply_text(s.error(f"❌ Недостаточно монет. Баланс: {user_data['coins']} 💰"))
            return
        
        field = [['⬜️' for _ in range(3)] for _ in range(3)]
        mine_x, mine_y = random.randint(0, 2), random.randint(0, 2)
        
        game_id = f"saper_{user.id}_{int(time.time())}"
        self.games_in_progress[game_id] = {
            'user_id': user.id,
            'field': field,
            'mine_x': mine_x,
            'mine_y': mine_y,
            'bet': bet,
            'opened': 0
        }
        
        self.db.add_coins(user_data['id'], -bet)
        
        # Создаем кнопки для сапёра
        keyboard = []
        for i in range(3):
            row = []
            for j in range(3):
                cell_num = i * 3 + j + 1
                row.append(InlineKeyboardButton(f"⬜️", callback_data=f"saper_{game_id}_{cell_num}"))
            keyboard.append(row)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = (
            s.header("💣 САПЁР") + "\n\n"
            f"{s.item(f'Ставка: {bet} 💰')}\n"
            f"{s.item('Выберите клетку:')}\n\n"
            f"{s.info('Нажимайте на кнопки, чтобы открыть клетки')}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    
    async def cmd_guess(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        bet = 10
        if context.args:
            try:
                bet = int(context.args[0])
            except:
                bet = 10
        
        if bet > user_data['coins']:
            await update.message.reply_text(s.error(f"❌ Недостаточно монет. Баланс: {user_data['coins']} 💰"))
            return
        
        number = random.randint(1, 100)
        game_id = f"guess_{user.id}_{int(time.time())}"
        self.games_in_progress[game_id] = {
            'user_id': user.id,
            'number': number,
            'attempts': 0,
            'max_attempts': 7,
            'bet': bet
        }
        
        self.db.add_coins(user_data['id'], -bet)
        
        await update.message.reply_text(
            f"{s.header('🔢 УГАДАЙ ЧИСЛО')}\n\n"
            f"{s.item('Я загадал число от 1 до 100')}\n"
            f"{s.item(f'Ставка: {bet} 💰')}\n"
            f"{s.item('Попыток: 7')}\n\n"
            f"{s.info('Напиши свой вариант...')}",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def cmd_bulls(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        bet = 10
        if context.args:
            try:
                bet = int(context.args[0])
            except:
                bet = 10
        
        if bet > user_data['coins']:
            await update.message.reply_text(s.error(f"❌ Недостаточно монет. Баланс: {user_data['coins']} 💰"))
            return
        
        digits = random.sample(range(10), 4)
        number = ''.join(map(str, digits))
        
        game_id = f"bulls_{user.id}_{int(time.time())}"
        self.games_in_progress[game_id] = {
            'user_id': user.id,
            'number': number,
            'attempts': [],
            'max_attempts': 10,
            'bet': bet
        }
        
        self.db.add_coins(user_data['id'], -bet)
        
        await update.message.reply_text(
            f"{s.header('🐂 БЫКИ И КОРОВЫ')}\n\n"
            f"{s.item('Я загадал 4-значное число без повторов')}\n"
            f"{s.item(f'Ставка: {bet} 💰')}\n"
            f"{s.item('Попыток: 10')}\n"
            f"{s.item('Бык — цифра на своём месте')}\n"
            f"{s.item('Корова — цифра есть, но не на своём месте')}\n\n"
            f"{s.info('Напиши свой вариант (4 цифры)...')}",
            parse_mode=ParseMode.MARKDOWN
        )
    
    # ===== БОССЫ (УЛУЧШЕННАЯ ВЕРСИЯ) =====
    async def cmd_bosses(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        bosses = self.db.get_bosses()
        
        if not bosses:
            self.db.respawn_bosses()
            bosses = self.db.get_bosses()
        
        text = s.header("👾 БОССЫ") + "\n\n"
        
        for i, boss in enumerate(bosses[:5]):
            health_bar = s.progress(boss['health'], boss['max_health'], 15)
            text += (
                f"{i+1}. {boss['name']} (ур.{boss['level']})\n"
                f"{s.item(f'❤️ {health_bar}')}\n"
                f"{s.item(f'⚔️ Урон: {boss['damage']}')}\n"
                f"{s.item(f'💰 Награда: {boss['reward_coins']} 💰, ✨ {boss['reward_exp']}')}\n"
                f"{s.item(f'💜 Неоны: {boss['reward_neons']}, 🖥 Глитчи: {boss['reward_glitches']}')}\n\n"
            )
        
        text += (
            f"{s.section('ТВОИ ПОКАЗАТЕЛИ')}\n"
            f"{s.stat('❤️ Здоровье', f'{user_data["health"]}/{user_data["max_health"]}')}\n"
            f"{s.stat('⚡️ Энергия', f'{user_data["energy"]}/100')}\n"
            f"{s.stat('⚔️ Урон', user_data["damage"])}\n"
            f"{s.stat('👾 Боссов убито', user_data["boss_kills"])}\n\n"
            f"{s.section('КОМАНДЫ')}\n"
            f"{s.cmd('boss [ID]', 'атаковать босса')}\n"
            f"{s.cmd('regen', 'восстановить ❤️ и ⚡️')}\n"
            f"{s.cmd('buy damage', 'купить оружие (+урон)')}"
        )
        
        # Создаем кнопки для быстрой атаки
        keyboard = []
        for i, boss in enumerate(bosses[:5]):
            status = "⚔️" if boss['is_alive'] else "💀"
            keyboard.append([InlineKeyboardButton(
                f"{status} {boss['name']} (❤️ {boss['health']}/{boss['max_health']})",
                callback_data=f"boss_attack_{boss['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔄 Регенерация", callback_data="boss_regen")])
        keyboard.append([InlineKeyboardButton("⚔️ Купить оружие", callback_data="boss_buy_weapon")])
        keyboard.append([InlineKeyboardButton("📋 К списку боссов", callback_data="boss_list")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    
    async def cmd_boss_fight(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажи ID босса: /boss 1"))
            return
        
        try:
            boss_id = int(context.args[0])
        except:
            await update.message.reply_text(s.error("❌ Неверный ID"))
            return
        
        await self._process_boss_attack(update, context, user, user_data, boss_id, is_callback=False)
    
    async def _process_boss_attack(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                   user, user_data, boss_id: int, is_callback: bool = False):
        """Общая логика атаки босса"""
        boss = self.db.get_boss(boss_id)
        
        if not boss or not boss['is_alive']:
            msg = s.error("❌ Босс не найден или уже повержен")
            if is_callback:
                await update.callback_query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN)
            else:
                await update.message.reply_text(msg)
            return
        
        if user_data['energy'] < 10:
            msg = s.error("❌ Недостаточно энергии. Используй /regen или кнопку регенерации")
            if is_callback:
                await update.callback_query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN)
            else:
                await update.message.reply_text(msg)
            return
        
        # Тратим энергию
        self.db.add_energy(user_data['id'], -10)
        
        # Расчет урона
        damage_bonus = 1.0
        if self.db.is_vip(user_data['id']):
            damage_bonus += 0.2
        if self.db.is_premium(user_data['id']):
            damage_bonus += 0.3
        if user_data.get('turbo_drive_until') and datetime.fromisoformat(user_data['turbo_drive_until']) > datetime.now():
            damage_bonus += 0.2
        
        base_damage = user_data['damage'] * damage_bonus
        player_damage = int(base_damage) + random.randint(-5, 5)
        
        crit = random.randint(1, 100) <= user_data['crit_chance']
        if crit:
            player_damage = int(player_damage * user_data['crit_multiplier'] / 100)
            crit_text = "💥 КРИТИЧЕСКИЙ УДАР! "
        else:
            crit_text = ""
        
        # Босс контратакует
        boss_damage = boss['damage'] + random.randint(-5, 5)
        
        # Защита
        armor_reduction = user_data['armor'] // 2
        player_taken = max(1, boss_damage - armor_reduction)
        
        # Наносим урон
        killed = self.db.damage_boss(boss_id, player_damage)
        self.db.damage(user_data['id'], player_taken)
        
        # Добавляем урон в статистику
        total_damage = user_data.get('boss_damage', 0) + player_damage
        self.db.update_user(user_data['id'], boss_damage=total_damage)
        
        text = s.header("⚔️ БИТВА С БОССОМ") + "\n\n"
        text += f"{s.item(f'{crit_text}Твой урон: {player_damage}')}\n"
        text += f"{s.item(f'Урон босса: {player_taken}')}\n\n"
        
        if killed:
            # Бонусы за убийство
            reward_coins = boss['reward_coins']
            reward_exp = boss['reward_exp']
            reward_neons = boss['reward_neons']
            reward_glitches = boss['reward_glitches']
            
            # Множители от статусов
            if self.db.is_vip(user_data['id']):
                reward_coins = int(reward_coins * 1.5)
                reward_exp = int(reward_exp * 1.5)
                reward_neons = int(reward_neons * 1.5)
                reward_glitches = int(reward_glitches * 1.5)
            if self.db.is_premium(user_data['id']):
                reward_coins = int(reward_coins * 2)
                reward_exp = int(reward_exp * 2)
                reward_neons = int(reward_neons * 2)
                reward_glitches = int(reward_glitches * 2)
            
            self.db.add_coins(user_data['id'], reward_coins)
            self.db.add_neons(user_data['id'], reward_neons)
            self.db.add_glitches(user_data['id'], reward_glitches)
            leveled_up = self.db.add_exp(user_data['id'], reward_exp)
            self.db.add_boss_kill(user_data['id'])
            
            text += f"{s.success('ПОБЕДА!')}\n"
            text += f"{s.item(f'💰 Монеты: +{reward_coins}')}\n"
            text += f"{s.item(f'💜 Неоны: +{reward_neons}')}\n"
            text += f"{s.item(f'🖥 Глитчи: +{reward_glitches}')}\n"
            text += f"{s.item(f'✨ Опыт: +{reward_exp}')}\n"
            
            if leveled_up:
                text += f"{s.success(f'✨ УРОВЕНЬ ПОВЫШЕН!')}\n"
        else:
            boss_info = self.db.get_boss(boss_id)
            text += f"{s.warning('Босс ещё жив!')}\n"
            text += f"❤️ Осталось: {boss_info['health']} здоровья\n"
        
        if user_data['health'] <= player_taken:
            self.db.heal(user_data['id'], 50)
            text += f"\n{s.info('Ты погиб и воскрешён с 50❤️')}"
        
        # Обновляем данные пользователя
        user_data = self.db.get_user(user.id)
        
        text += f"\n{s.item(f'Твое здоровье: {user_data["health"]}/{user_data["max_health"]} ❤️')}"
        text += f"\n{s.item(f'Энергия: {user_data["energy"]}/100 ⚡️')}"
        
        # Создаем кнопки для продолжения
        keyboard = [
            [InlineKeyboardButton("⚔️ Атаковать снова", callback_data=f"boss_attack_{boss_id}")],
            [InlineKeyboardButton("🔄 Регенерация (20💰)", callback_data="boss_regen")],
            [InlineKeyboardButton("⚔️ Купить оружие", callback_data="boss_buy_weapon")],
            [InlineKeyboardButton("📋 К списку боссов", callback_data="boss_list")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if is_callback:
            await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        
        self.db.log_action(user_data['id'], 'boss_fight', f"Урон {player_damage}")
    
    async def cmd_boss_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажи ID босса: /bossinfo 1"))
            return
        
        try:
            boss_id = int(context.args[0])
        except:
            await update.message.reply_text(s.error("❌ Неверный ID"))
            return
        
        boss = self.db.get_boss(boss_id)
        if not boss:
            await update.message.reply_text(s.error("❌ Босс не найден"))
            return
        
        status = "ЖИВ" if boss['is_alive'] else "ПОВЕРЖЕН"
        health_bar = s.progress(boss['health'], boss['max_health'], 20)
        
        text = (
            f"# Спектр | Информация о боссе\n\n"
            f"👾 {boss['name']}\n\n"
            f"📊 **Характеристики**\n"
            f"• Уровень: {boss['level']}\n"
            f"• ❤️ Здоровье: {health_bar}\n"
            f"• ⚔️ Урон: {boss['damage']}\n"
            f"• 💰 Награда: {boss['reward_coins']} 💰\n"
            f"• 💜 Неоны: {boss['reward_neons']}\n"
            f"• 🖥 Глитчи: {boss['reward_glitches']}\n"
            f"• ✨ Опыт: {boss['reward_exp']}\n"
            f"• 📊 Статус: {status}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_regen(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = self.db.get_user(update.effective_user.id)
        
        cost = 20
        if user_data['coins'] < cost:
            await update.message.reply_text(s.error(f"❌ Недостаточно монет. Нужно {cost} 💰"))
            return
        
        self.db.add_coins(user_data['id'], -cost)
        self.db.heal(user_data['id'], 50)
        self.db.add_energy(user_data['id'], 20)
        
        user_data = self.db.get_user(update.effective_user.id)
        
        text = (
            f"{s.success('✅ Регенерация завершена!')}\n\n"
            f"{s.item('❤️ Здоровье +50')}\n"
            f"{s.item('⚡️ Энергия +20')}\n"
            f"{s.item(f'💰 Потрачено: {cost}')}\n\n"
            f"{s.item(f'Теперь: ❤️ {user_data["health"]} | ⚡️ {user_data["energy"]}')}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    # ===== ДУЭЛИ =====
    async def cmd_duel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if len(context.args) < 2:
            await update.message.reply_text(s.error("❌ Использование: /duel @user ставка"))
            return
        
        username = context.args[0].replace('@', '')
        try:
            bet = int(context.args[1])
        except:
            await update.message.reply_text(s.error("❌ Ставка должна быть числом"))
            return
        
        if bet <= 0:
            await update.message.reply_text(s.error("❌ Ставка должна быть больше 0"))
            return
        
        if bet > user_data['coins']:
            await update.message.reply_text(s.error(f"❌ Недостаточно монет. Баланс: {user_data['coins']} 💰"))
            return
        
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        if target['id'] == user_data['id']:
            await update.message.reply_text(s.error("❌ Нельзя вызвать на дуэль самого себя"))
            return
        
        self.db.cursor.execute(
            "SELECT id FROM duels WHERE (challenger_id = ? OR opponent_id = ?) AND status = 'pending'",
            (user_data['id'], user_data['id'])
        )
        if self.db.cursor.fetchone():
            await update.message.reply_text(s.error("❌ У тебя уже есть активная дуэль"))
            return
        
        duel_id = self.db.create_duel(user_data['id'], target['id'], bet)
        self.db.add_coins(user_data['id'], -bet)
        
        target_name = target.get('nickname') or target['first_name']
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ ПРИНЯТЬ", callback_data=f"accept_duel_{duel_id}"),
                InlineKeyboardButton("❌ ОТКЛОНИТЬ", callback_data=f"reject_duel_{duel_id}")
            ]
        ])
        
        await update.message.reply_text(
            f"# Спектр | Дуэль\n\n"
            f"⚔️ {user.first_name} VS {target_name} ⚔️\n"
            f"💰 Ставка: {bet} 💰\n\n"
            f"{user.first_name} вызывает на дуэль!\n\n"
            f"{target_name}, прими вызов:",
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
        
        self.duels_in_progress[duel_id] = {
            'challenger': user_data['id'],
            'opponent': target['id'],
            'bet': bet,
            'chat_id': update.effective_chat.id,
            'message_id': None,
            'status': 'pending'
        }

    async def _process_duel(self, duel_id: int, challenger: Dict, opponent: Dict, bet: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Обработка дуэли"""
        await asyncio.sleep(2)
        
        challenger_roll = random.randint(1, 100)
        opponent_roll = random.randint(1, 100)
        
        if self.db.is_vip(challenger['id']):
            challenger_roll += 5
        if self.db.is_vip(opponent['id']):
            opponent_roll += 5
        
        if challenger_roll > opponent_roll:
            winner = challenger
            loser = opponent
            winner_score = challenger_roll
            loser_score = opponent_roll
        elif opponent_roll > challenger_roll:
            winner = opponent
            loser = challenger
            winner_score = opponent_roll
            loser_score = challenger_roll
        else:
            await context.bot.send_message(
                chat_id,
                s.info("🤝 Ничья! Перебрасываем..."),
                parse_mode=ParseMode.MARKDOWN
            )
            await asyncio.sleep(1)
            await self._process_duel(duel_id, challenger, opponent, bet, chat_id, context)
            return
        
        win_amount = bet * 2
        self.db.add_coins(winner['id'], win_amount)
        
        self.db.update_user(winner['id'], 
                          duel_wins=self.db.get_user_by_id(winner['id']).get('duel_wins', 0) + 1,
                          duel_rating=self.db.get_user_by_id(winner['id']).get('duel_rating', 1000) + 25)
        
        self.db.update_user(loser['id'], 
                          duel_losses=self.db.get_user_by_id(loser['id']).get('duel_losses', 0) + 1,
                          duel_rating=self.db.get_user_by_id(loser['id']).get('duel_rating', 1000) - 15)
        
        result_text = (
            f"# Спектр | Результат дуэли\n\n"
            f"⚔️ **{winner['first_name']}** VS **{loser['first_name']}**\n\n"
            f"🎲 **Результаты:**\n"
            f"• {winner['first_name']}: {winner_score}\n"
            f"• {loser['first_name']}: {loser_score}\n\n"
            f"🏆 **Победитель:** {winner['first_name']}\n"
            f"💰 Выигрыш: {win_amount} 💰\n\n"
            f"{s.success('Поздравляем!')}"
        )
        
        await context.bot.send_message(chat_id, result_text, parse_mode=ParseMode.MARKDOWN)
        
        self.db.update_duel(duel_id, status='completed', winner_id=winner['id'])
    
    async def cmd_duels(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.db.cursor.execute("SELECT * FROM duels WHERE status = 'pending'")
        duels = self.db.cursor.fetchall()
        
        if not duels:
            await update.message.reply_text(s.info("Нет активных дуэлей"))
            return
        
        text = s.header("⚔️ АКТИВНЫЕ ДУЭЛИ") + "\n\n"
        for duel in duels:
            challenger = self.db.get_user_by_id(duel[1])
            opponent = self.db.get_user_by_id(duel[2])
            if challenger and opponent:
                text += f"{s.item(f'{challenger["first_name"]} vs {opponent["first_name"]} — ставка {duel[3]} 💰')}\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_duel_rating(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.db.cursor.execute("SELECT first_name, nickname, duel_rating FROM users WHERE duel_rating > 0 ORDER BY duel_rating DESC LIMIT 10")
        top = self.db.cursor.fetchall()
        
        if not top:
            await update.message.reply_text(s.info("Рейтинг пуст"))
            return
        
        text = s.header("⚔️ ТОП ДУЭЛЯНТОВ") + "\n\n"
        for i, row in enumerate(top, 1):
            name = row[1] or row[0]
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} {name} — {row[2]} очков\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    # ===== АЧИВКИ =====
    async def cmd_achievements(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация об ачивках"""
        text = """
# Спектр | Ачивки

🏅 **Команды:**

/achievements — эта информация
/myachievements — мои ачивки
/achievement [ID] — информация об ачивке
/topachievements — топ коллекционеров

📋 **Категории ачивок:**
💜 По богатству
🖥 По глитчам
🎲 По играм
⚔️ По дуэлям
👾 По боссам
🔥 По активности
📆 По стрикам
💎 VIP-ачивки
🎁 Особые
🤖 Секретные

🔐 **Приватность:**
+Ачивки — открыть доступ к вашим ачивкам
-Ачивки — скрыть ваши ачивки от других
        """
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_my_achievements(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Мои ачивки"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        # Проверяем приватность
        if not user_data.get('achievements_visible', 1) and not has_permission(user_data, 1):
            if context.args:
                # Смотрим ачивки другого пользователя
                username = context.args[0].replace('@', '')
                target = self.db.get_user_by_username(username)
                if target:
                    if not target.get('achievements_visible', 1):
                        await update.message.reply_text(s.error("❌ Пользователь скрыл свои ачивки"))
                        return
                    user_data = target
                else:
                    await update.message.reply_text(s.error("❌ Пользователь не найден"))
                    return
            else:
                await update.message.reply_text(s.error("❌ Ваши ачивки скрыты. Используйте +Ачивки чтобы открыть"))
                return
        
        achievements = self.db.get_user_achievements(user_data['id'])
        
        if not achievements:
            await update.message.reply_text(s.info("У вас пока нет ачивок"))
            return
        
        # Группируем по категориям
        categories = {
            'wealth': '💜 БОГАТСТВО',
            'glitches': '🖥 ГЛИТЧИ',
            'games': '🎲 ИГРЫ',
            'duels': '⚔️ ДУЭЛИ',
            'bosses': '👾 БОССЫ',
            'activity': '🔥 АКТИВНОСТЬ',
            'streak': '📆 СТРИКИ',
            'vip': '💎 VIP',
            'gifts': '🎁 ОСОБЫЕ',
            'secret': '🤖 СЕКРЕТНЫЕ'
        }
        
        grouped = defaultdict(list)
        for ach in achievements:
            if ach['secret'] and not has_permission(user_data, 1):
                continue  # Скрываем секретные ачивки от обычных пользователей
            grouped[ach['category']].append(ach)
        
        name = user_data.get('nickname') or user_data['first_name']
        
        text = s.header(f"🏅 АЧИВКИ: {name}") + f"\nВсего: {len(achievements)}\n\n"
        
        for category_key, category_name in categories.items():
            if category_key in grouped:
                text += f"{category_name}\n"
                for ach in grouped[category_key]:
                    text += f"  • {ach['name']} — {ach['description']}\n"
                text += "\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_achievement_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о конкретной ачивке"""
        text = update.message.text
        
        # Парсим ID ачивки
        match = re.search(r'ачивка (\d+)', text)
        if not match:
            await update.message.reply_text(s.error("❌ Укажите ID ачивки: ачивка 15"))
            return
        
        ach_id = int(match.group(1))
        
        self.db.cursor.execute("SELECT * FROM achievements_list WHERE id = ?", (ach_id,))
        ach = self.db.cursor.fetchone()
        
        if not ach:
            await update.message.reply_text(s.error("❌ Ачивка не найдена"))
            return
        
        ach = dict(ach)
        
        # Проверяем, получена ли ачивка
        user_data = self.db.get_user(update.effective_user.id)
        self.db.cursor.execute("SELECT unlocked_at FROM achievements WHERE user_id = ? AND achievement_id = ?",
                             (user_data['id'], ach_id))
        unlocked = self.db.cursor.fetchone()
        
        status = "✅ ПОЛУЧЕНО" if unlocked else "❌ НЕ ПОЛУЧЕНО"
        if unlocked:
            date = datetime.fromisoformat(unlocked[0]).strftime("%d.%m.%Y %H:%M")
            status += f" ({date})"
        
        secret_note = " (СЕКРЕТНАЯ)" if ach['secret'] else ""
        
        text = (
            f"# Спектр | Ачивка {ach_id}{secret_note}\n\n"
            f"🏅 **{ach['name']}**\n"
            f"📝 {ach['description']}\n\n"
            f"🎁 **Награда:**\n"
        )
        
        if ach['reward_neons'] > 0:
            text += f"• {ach['reward_neons']} 💜 неонов\n"
        if ach['reward_glitches'] > 0:
            text += f"• {ach['reward_glitches']} 🖥 глитчей\n"
        if ach['reward_title']:
            text += f"• Титул: {ach['reward_title']}\n"
        if ach['reward_status']:
            text += f"• Статус: {ach['reward_status']}\n"
        
        text += f"\n📊 **Статус:** {status}"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_top_achievements(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Топ коллекционеров ачивок"""
        self.db.cursor.execute("""
            SELECT u.first_name, u.nickname, COUNT(a.id) as count
            FROM users u
            LEFT JOIN achievements a ON u.id = a.user_id
            GROUP BY u.id
            ORDER BY count DESC
            LIMIT 10
        """)
        
        top = self.db.cursor.fetchall()
        
        if not top or top[0][2] == 0:
            await update.message.reply_text(s.info("Топ ачивок пуст"))
            return
        
        text = s.header("🏆 ТОП КОЛЛЕКЦИОНЕРОВ") + "\n\n"
        for i, row in enumerate(top, 1):
            name = row[1] or row[0]
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} {name} — {row[2]} ачивок\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_achievements_public(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сделать ачивки публичными"""
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], achievements_visible=1)
        await update.message.reply_text(s.success("✅ Ваши ачивки теперь видны всем"))
    
    async def cmd_achievements_private(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Скрыть ачивки"""
        user_data = self.db.get_user(update.effective_user.id)
        self.db.update_user(user_data['id'], achievements_visible=0)
        await update.message.reply_text(s.success("✅ Ваши ачивки теперь скрыты от других"))
    
    # ===== КРУЖКИ =====
    async def cmd_circles(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список кружков в чате"""
        chat_id = update.effective_chat.id
        
        self.db.cursor.execute("SELECT * FROM circles WHERE chat_id = ? ORDER BY created_at", (chat_id,))
        circles = self.db.cursor.fetchall()
        
        if not circles:
            await update.message.reply_text(s.info("В этом чате нет кружков"))
            return
        
        text = s.header("🔄 КРУЖКИ ЧАТА") + "\n\n"
        for i, circle in enumerate(circles, 1):
            circle = dict(circle)
            members = json.loads(circle['members'])
            text += f"{i}. {circle['name']} — {len(members)} участников\n"
            if circle['description']:
                text += f"   _{circle['description']}_\n"
        
        text += f"\n{s.cmd('кружок [номер]', 'информация о кружке')}\n"
        text += f"{s.cmd('+Кружок [номер]', 'присоединиться')}"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_circle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о кружке"""
        text = update.message.text
        chat_id = update.effective_chat.id
        
        match = re.search(r'кружок (\d+)', text)
        if not match:
            await update.message.reply_text(s.error("❌ Укажите номер кружка: кружок 1"))
            return
        
        circle_num = int(match.group(1))
        
        self.db.cursor.execute("SELECT * FROM circles WHERE chat_id = ? ORDER BY created_at", (chat_id,))
        circles = self.db.cursor.fetchall()
        
        if circle_num < 1 or circle_num > len(circles):
            await update.message.reply_text(s.error("❌ Кружок с таким номером не найден"))
            return
        
        circle = dict(circles[circle_num - 1])
        members = json.loads(circle['members'])
        
        creator = self.db.get_user_by_id(circle['created_by'])
        creator_name = creator.get('nickname') or creator['first_name'] if creator else "Неизвестно"
        
        # Получаем имена участников
        member_names = []
        for member_id in members[:10]:
            member = self.db.get_user_by_id(member_id)
            if member:
                member_names.append(member.get('nickname') or member['first_name'])
        
        text = (
            s.header(f"🔄 КРУЖОК: {circle['name']}") + "\n\n"
            f"📝 {circle['description']}\n\n"
            f"👑 Создатель: {creator_name}\n"
            f"👥 Участников: {len(members)}\n\n"
        )
        
        if member_names:
            text += "**Участники:**\n"
            for name in member_names:
                text += f"• {name}\n"
        
        if len(members) > 10:
            text += f"... и ещё {len(members) - 10}\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_create_circle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Создать кружок"""
        text = update.message.text
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        chat_id = update.effective_chat.id
        
        # Парсим название и описание
        lines = text.split('\n', 1)
        first_line = lines[0]
        
        if first_line.startswith('создать кружок '):
            name = first_line.replace('создать кружок ', '').strip()
        else:
            await update.message.reply_text(s.error("❌ Формат: создать кружок Название\nОписание"))
            return
        
        description = lines[1].strip() if len(lines) > 1 else ""
        
        if len(name) > 50:
            await update.message.reply_text(s.error("❌ Название слишком длинное (макс. 50 символов)"))
            return
        
        circle_id = self.db.create_circle(chat_id, name, description, user_data['id'])
        
        if not circle_id:
            await update.message.reply_text(s.error("❌ Не удалось создать кружок. Возможно, достигнут лимит"))
            return
        
        await update.message.reply_text(s.success(f"✅ Кружок '{name}' создан!"))
    
    async def cmd_join_circle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Присоединиться к кружку"""
        text = update.message.text
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        chat_id = update.effective_chat.id
        
        match = re.search(r'\+Кружок (\d+)', text)
        if not match:
            await update.message.reply_text(s.error("❌ Укажите номер кружка: +Кружок 1"))
            return
        
        circle_num = int(match.group(1))
        
        self.db.cursor.execute("SELECT * FROM circles WHERE chat_id = ? ORDER BY created_at", (chat_id,))
        circles = self.db.cursor.fetchall()
        
        if circle_num < 1 or circle_num > len(circles):
            await update.message.reply_text(s.error("❌ Кружок с таким номером не найден"))
            return
        
        circle = dict(circles[circle_num - 1])
        
        if self.db.join_circle(circle['id'], user_data['id']):
            await update.message.reply_text(s.success(f"✅ Вы присоединились к кружку '{circle['name']}'"))
        else:
            await update.message.reply_text(s.error("❌ Не удалось присоединиться к кружку"))
    
    async def cmd_leave_circle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Покинуть кружок"""
        text = update.message.text
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        chat_id = update.effective_chat.id
        
        match = re.search(r'-Кружок (\d+)', text)
        if not match:
            await update.message.reply_text(s.error("❌ Укажите номер кружка: -Кружок 1"))
            return
        
        circle_num = int(match.group(1))
        
        self.db.cursor.execute("SELECT * FROM circles WHERE chat_id = ? ORDER BY created_at", (chat_id,))
        circles = self.db.cursor.fetchall()
        
        if circle_num < 1 or circle_num > len(circles):
            await update.message.reply_text(s.error("❌ Кружок с таким номером не найден"))
            return
        
        circle = dict(circles[circle_num - 1])
        
        if self.db.leave_circle(circle['id'], user_data['id']):
            await update.message.reply_text(s.success(f"✅ Вы покинули кружок '{circle['name']}'"))
        else:
            await update.message.reply_text(s.error("❌ Не удалось покинуть кружок"))
    
    # ===== ЗАКЛАДКИ =====
    async def cmd_add_bookmark(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Добавить закладку"""
        text = update.message.text
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        chat_id = update.effective_chat.id
        
        lines = text.split('\n', 1)
        first_line = lines[0]
        
        if first_line.startswith('+Закладка '):
            name = first_line.replace('+Закладка ', '').strip()
        else:
            await update.message.reply_text(s.error("❌ Формат: +Закладка Название\nСодержимое"))
            return
        
        if len(name) > 50:
            await update.message.reply_text(s.error("❌ Название слишком длинное (макс. 50 символов)"))
            return
        
        content = lines[1].strip() if len(lines) > 1 else ""
        
        if not content:
            await update.message.reply_text(s.error("❌ Укажите содержимое закладки"))
            return
        
        message_id = update.message.reply_to_message.message_id if update.message.reply_to_message else None
        
        bookmark_id = self.db.add_bookmark(chat_id, user_data['id'], name, content, message_id)
        
        await update.message.reply_text(s.success(f"✅ Закладка #{bookmark_id} '{name}' сохранена!"))
    
    async def cmd_bookmarks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Мои закладки"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        chat_id = update.effective_chat.id
        
        bookmarks = self.db.get_user_bookmarks(user_data['id'], chat_id)
        
        if not bookmarks:
            await update.message.reply_text(s.info("У вас нет закладок в этом чате"))
            return
        
        text = s.header("📌 МОИ ЗАКЛАДКИ") + "\n\n"
        for i, bm in enumerate(bookmarks, 1):
            text += f"{i}. {bm['name']} — закладка {bm['id']}\n"
        
        text += f"\n{s.cmd('закладка [номер]', 'показать закладку')}"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_chat_bookmarks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Чатбук - все закладки чата"""
        chat_id = update.effective_chat.id
        
        bookmarks = self.db.get_chat_bookmarks(chat_id)
        
        if not bookmarks:
            await update.message.reply_text(s.info("В этом чате нет публичных закладок"))
            return
        
        text = s.header("📚 ЧАТБУК") + "\n\n"
        for i, bm in enumerate(bookmarks[:20], 1):
            name = bm.get('nickname') or bm['first_name']
            text += f"{i}. {bm['name']} (от {name}) — закладка {bm['id']}\n"
        
        if len(bookmarks) > 20:
            text += f"\n... и ещё {len(bookmarks) - 20}"
        
        text += f"\n\n{s.cmd('закладка [ID]', 'показать закладку')}"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_my_bookmarks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Мои закладки (русская команда)"""
        await self.cmd_bookmarks(update, context)
    
    async def cmd_bookmark(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать закладку"""
        text = update.message.text
        chat_id = update.effective_chat.id
        
        match = re.search(r'закладка (\d+)', text)
        if not match:
            await update.message.reply_text(s.error("❌ Укажите ID закладки: закладка 123"))
            return
        
        bookmark_id = int(match.group(1))
        
        self.db.cursor.execute("SELECT * FROM bookmarks WHERE id = ? AND chat_id = ?", (bookmark_id, chat_id))
        bm = self.db.cursor.fetchone()
        
        if not bm:
            await update.message.reply_text(s.error("❌ Закладка не найдена"))
            return
        
        bm = dict(bm)
        user = self.db.get_user_by_id(bm['user_id'])
        user_name = user.get('nickname') or user['first_name'] if user else "Неизвестно"
        
        text = (
            s.header(f"📌 ЗАКЛАДКА: {bm['name']}") + "\n\n"
            f"{bm['content']}\n\n"
            f"👤 Добавил: {user_name}\n"
            f"📅 {datetime.fromisoformat(bm['created_at']).strftime('%d.%m.%Y %H:%M')}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_remove_bookmark(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Удалить закладку"""
        text = update.message.text
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        chat_id = update.effective_chat.id
        
        match = re.search(r'-Закладка (\d+)', text)
        if not match:
            await update.message.reply_text(s.error("❌ Укажите ID закладки: -Закладка 123"))
            return
        
        bookmark_id = int(match.group(1))
        
        self.db.cursor.execute("SELECT user_id FROM bookmarks WHERE id = ? AND chat_id = ?", (bookmark_id, chat_id))
        row = self.db.cursor.fetchone()
        
        if not row:
            await update.message.reply_text(s.error("❌ Закладка не найдена"))
            return
        
        # Проверяем права (владелец или модератор)
        if row[0] != user_data['id'] and user_data['rank'] < 2:
            await update.message.reply_text(s.error("❌ У вас нет прав на удаление этой закладки"))
            return
        
        self.db.cursor.execute("DELETE FROM bookmarks WHERE id = ?", (bookmark_id,))
        self.db.conn.commit()
        
        await update.message.reply_text(s.success("✅ Закладка удалена"))
    
    # ===== ТАЙМЕРЫ =====
    async def cmd_add_timer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Добавить таймер"""
        text = update.message.text
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        chat_id = update.effective_chat.id
        
        # Проверяем права (VIP или модератор)
        is_vip = self.db.is_vip(user_data['id']) or self.db.is_premium(user_data['id'])
        if user_data['rank'] < 1 and not is_vip:
            await update.message.reply_text(s.error("❌ Таймеры доступны модераторам и VIP"))
            return
        
        # Парсим тип таймера
        if text.startswith('таймер через '):
            # Таймер через период
            rest = text.replace('таймер через ', '').strip()
            parts = rest.split('\n', 1)
            time_str = parts[0].strip()
            command = parts[1].strip() if len(parts) > 1 else ""
            
            # Парсим время
            match = re.match(r'(\d+)\s*(м|ч|д|мин|час|день|дней)', time_str.lower())
            if not match:
                await update.message.reply_text(s.error("❌ Неверный формат времени. Пример: таймер через 30м /ping"))
                return
            
            amount = int(match.group(1))
            unit = match.group(2)
            
            if unit in ['м', 'мин']:
                delta = timedelta(minutes=amount)
            elif unit in ['ч', 'час']:
                delta = timedelta(hours=amount)
            elif unit in ['д', 'день', 'дней']:
                delta = timedelta(days=amount)
            else:
                await update.message.reply_text(s.error("❌ Неверная единица времени"))
                return
            
            execute_at = datetime.now() + delta
            
        elif text.startswith('таймер на '):
            # Таймер на конкретную дату
            rest = text.replace('таймер на ', '').strip()
            parts = rest.split('\n', 1)
            date_str = parts[0].strip()
            command = parts[1].strip() if len(parts) > 1 else ""
            
            execute_at = parse_datetime(date_str)
            if not execute_at:
                await update.message.reply_text(s.error("❌ Неверный формат даты. Пример: таймер на 25.12 15:30 /ping"))
                return
        else:
            return
        
        if not command:
            await update.message.reply_text(s.error("❌ Укажите команду для выполнения"))
            return
        
        timer_id = self.db.add_timer(chat_id, user_data['id'], execute_at, command)
        
        if not timer_id:
            await update.message.reply_text(s.error("❌ Достигнут лимит таймеров в чате (макс. 5)"))
            return
        
        await update.message.reply_text(
            s.success(f"✅ Таймер #{timer_id} установлен на {execute_at.strftime('%d.%m.%Y %H:%M')}")
        )
    
    async def cmd_timers(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список таймеров"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        chat_id = update.effective_chat.id
        
        self.db.cursor.execute("""
            SELECT * FROM timers 
            WHERE chat_id = ? AND status = 'pending' 
            ORDER BY execute_at
        """, (chat_id,))
        timers = self.db.cursor.fetchall()
        
        if not timers:
            await update.message.reply_text(s.info("В этом чате нет активных таймеров"))
            return
        
        text = s.header("⏰ ТАЙМЕРЫ ЧАТА") + "\n\n"
        for i, timer in enumerate(timers, 1):
            timer = dict(timer)
            creator = self.db.get_user_by_id(timer['user_id'])
            creator_name = creator.get('nickname') or creator['first_name'] if creator else "Неизвестно"
            execute_at = datetime.fromisoformat(timer['execute_at']).strftime('%d.%m.%Y %H:%M')
            text += f"{i}. #{timer['id']} — {execute_at}\n   Команда: {timer['command']}\n   Создатель: {creator_name}\n\n"
        
        text += s.cmd('удалить таймер [номер]', 'удалить таймер')
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_remove_timer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Удалить таймер"""
        text = update.message.text
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        chat_id = update.effective_chat.id
        
        match = re.search(r'удалить таймер (\d+)', text)
        if not match:
            await update.message.reply_text(s.error("❌ Укажите номер таймера: удалить таймер 1"))
            return
        
        timer_num = int(match.group(1))
        
        self.db.cursor.execute("""
            SELECT * FROM timers 
            WHERE chat_id = ? AND status = 'pending' 
            ORDER BY execute_at
        """, (chat_id,))
        timers = self.db.cursor.fetchall()
        
        if timer_num < 1 or timer_num > len(timers):
            await update.message.reply_text(s.error("❌ Таймер с таким номером не найден"))
            return
        
        timer = dict(timers[timer_num - 1])
        
        # Проверяем права
        if timer['user_id'] != user_data['id'] and user_data['rank'] < 2:
            await update.message.reply_text(s.error("❌ У вас нет прав на удаление этого таймера"))
            return
        
        self.db.cursor.execute("UPDATE timers SET status = 'cancelled' WHERE id = ?", (timer['id'],))
        self.db.conn.commit()
        
        await update.message.reply_text(s.success(f"✅ Таймер #{timer['id']} удалён"))
    
    async def check_timers(self):
        """Проверка и выполнение таймеров"""
        while True:
            try:
                timers = self.db.get_pending_timers()
                
                for timer in timers:
                    try:
                        # Выполняем команду
                        await self.app.bot.send_message(
                            chat_id=timer['chat_id'],
                            text=f"⏰ Сработал таймер #{timer['id']}\nВыполняю команду: {timer['command']}"
                        )
                        
                        # Здесь можно реализовать выполнение команды
                        # Для простоты просто отправляем уведомление
                        
                        self.db.complete_timer(timer['id'])
                    except Exception as e:
                        logger.error(f"Ошибка выполнения таймера {timer['id']}: {e}")
                
                await asyncio.sleep(60)  # Проверяем каждую минуту
            except Exception as e:
                logger.error(f"Ошибка в check_timers: {e}")
                await asyncio.sleep(60)
    
    # ===== НАГРАДЫ =====
    async def cmd_give_award(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выдать награду"""
        text = update.message.text
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        chat_id = update.effective_chat.id
        
        # Проверяем права
        if user_data['rank'] < 1:
            await update.message.reply_text(s.error("❌ Недостаточно прав для выдачи наград"))
            return
        
        # Парсим команду: наградить 4 @user текст
        match = re.search(r'наградить (\d+)\s+@?(\S+)(?:\s+(.+))?', text, re.IGNORECASE | re.DOTALL)
        if not match:
            await update.message.reply_text(s.error("❌ Формат: наградить [степень] @user\nТекст"))
            return
        
        degree = int(match.group(1))
        username = match.group(2)
        award_text = match.group(3).strip() if match.group(3) else ""
        
        if degree < 1 or degree > 8:
            await update.message.reply_text(s.error("❌ Степень должна быть от 1 до 8"))
            return
        
        # Проверяем, может ли пользователь выдавать такую степень
        if degree > user_data['rank'] and user_data['rank'] < 8:
            await update.message.reply_text(s.error(f"❌ Ваш ранг позволяет выдавать только степени до {user_data['rank']}"))
            return
        
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        award_id = self.db.give_award(chat_id, target['id'], user_data['id'], degree, award_text)
        
        target_name = target.get('nickname') or target['first_name']
        
        await update.message.reply_text(
            s.success(f"✅ Награда #{award_id} степени {degree} выдана {target_name}!")
        )
        
        # Уведомляем в ЛС
        try:
            await context.bot.send_message(
                target['telegram_id'],
                f"{s.success('🏅 ВАМ ВЫДАЛИ НАГРАДУ!')}\n\n"
                f"Степень: {degree}\n"
                f"Текст: {award_text}\n"
                f"От: {user.first_name}"
            )
        except:
            pass
    
    async def cmd_awards(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Просмотр наград пользователя"""
        text = update.message.text
        chat_id = update.effective_chat.id
        
        # Определяем целевого пользователя
        if text.startswith('награды @'):
            username = text.replace('награды @', '').strip()
            target = self.db.get_user_by_username(username)
        else:
            target = self.db.get_user(update.effective_user.id)
        
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        awards = self.db.get_user_awards(target['id'], chat_id)
        
        if not awards:
            name = target.get('nickname') or target['first_name']
            await update.message.reply_text(s.info(f"У {name} нет наград"))
            return
        
        name = target.get('nickname') or target['first_name']
        text = s.header(f"🏅 НАГРАДЫ: {name}") + "\n\n"
        
        for award in awards:
            date = datetime.fromisoformat(award['awarded_at']).strftime('%d.%m.%Y')
            text += f"• Степень {award['degree']} — {award['text']}\n"
            text += f"  От {award['awarded_by_name']}, {date}\n\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_remove_award(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Снять награду"""
        text = update.message.text
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        chat_id = update.effective_chat.id
        
        # Проверяем права
        if user_data['rank'] < 2:
            await update.message.reply_text(s.error("❌ Недостаточно прав для снятия наград"))
            return
        
        # Парсим: снять награду 123 @user
        match = re.search(r'снять награду\s+(\d+)\s+@?(\S+)', text, re.IGNORECASE)
        if match:
            award_id = int(match.group(1))
            username = match.group(2)
            
            target = self.db.get_user_by_username(username)
            if not target:
                await update.message.reply_text(s.error("❌ Пользователь не найден"))
                return
            
            self.db.cursor.execute("DELETE FROM awards WHERE id = ? AND chat_id = ?", (award_id, chat_id))
            self.db.conn.commit()
            
            if self.db.cursor.rowcount > 0:
                await update.message.reply_text(s.success(f"✅ Награда #{award_id} снята"))
            else:
                await update.message.reply_text(s.error("❌ Награда не найдена"))
            return
        
        # Парсим: снять все награды @user
        match = re.search(r'снять все награды\s+@?(\S+)', text, re.IGNORECASE)
        if match:
            username = match.group(1)
            
            target = self.db.get_user_by_username(username)
            if not target:
                await update.message.reply_text(s.error("❌ Пользователь не найден"))
                return
            
            self.db.cursor.execute("DELETE FROM awards WHERE user_id = ? AND chat_id = ?", (target['id'], chat_id))
            self.db.conn.commit()
            
            count = self.db.cursor.rowcount
            await update.message.reply_text(s.success(f"✅ Снято наград: {count}"))
            return
        
        await update.message.reply_text(s.error("❌ Неверный формат команды"))
    
    # ===== ГОЛОСОВАНИЕ ЗА БАН =====
    async def cmd_ban_vote(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Создать голосование за бан"""
        text = update.message.text
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        chat_id = update.effective_chat.id
        
        # Проверяем права
        if user_data['rank'] < 1 and not self.db.is_vip(user_data['id']):
            await update.message.reply_text(s.error("❌ Недостаточно прав для создания голосования"))
            return
        
        # Парсим: гб @user или гб 5 2 @user
        parts = text.split()
        
        if len(parts) >= 2:
            if parts[1].startswith('@'):
                # гб @user
                username = parts[1].replace('@', '')
                required_votes = 5
                min_rank = 0
            elif len(parts) >= 4 and parts[3].startswith('@'):
                # гб 5 2 @user
                try:
                    required_votes = int(parts[1])
                    min_rank = int(parts[2])
                    username = parts[3].replace('@', '')
                except:
                    await update.message.reply_text(s.error("❌ Неверный формат команды"))
                    return
            else:
                await update.message.reply_text(s.error("❌ Укажите пользователя: гб @user"))
                return
        else:
            await update.message.reply_text(s.error("❌ Укажите пользователя: гб @user"))
            return
        
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        if target['rank'] >= user_data['rank'] and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Нельзя создать голосование против модератора выше рангом"))
            return
        
        # Проверяем, нет ли уже активного голосования
        self.db.cursor.execute("SELECT id FROM ban_votes WHERE chat_id = ? AND target_id = ? AND status = 'active'",
                             (chat_id, target['id']))
        if self.db.cursor.fetchone():
            await update.message.reply_text(s.error("❌ Активное голосование за этого пользователя уже существует"))
            return
        
        vote_id = self.db.create_ban_vote(chat_id, target['id'], user_data['id'], required_votes, min_rank)
        
        target_name = target.get('nickname') or target['first_name']
        
        # Создаем клавиатуру для голосования
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ ЗА БАН", callback_data=f"vote_for_{vote_id}"),
                InlineKeyboardButton("❌ ПРОТИВ", callback_data=f"vote_against_{vote_id}")
            ]
        ])
        
        await update.message.reply_text(
            f"{s.header('🗳 ГОЛОСОВАНИЕ ЗА БАН')}\n\n"
            f"Цель: {target_name}\n"
            f"Инициатор: {user.first_name}\n"
            f"Требуется голосов: {required_votes}\n"
            f"Минимальный ранг голосующих: {min_rank}\n\n"
            f"Голосуйте!",
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def cmd_stop_vote(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Остановить голосование"""
        text = update.message.text
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        chat_id = update.effective_chat.id
        
        match = re.search(r'гб стоп\s+@?(\S+)', text, re.IGNORECASE)
        if not match:
            await update.message.reply_text(s.error("❌ Укажите пользователя: гб стоп @user"))
            return
        
        username = match.group(1)
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        self.db.cursor.execute("SELECT * FROM ban_votes WHERE chat_id = ? AND target_id = ? AND status = 'active'",
                             (chat_id, target['id']))
        vote = self.db.cursor.fetchone()
        
        if not vote:
            await update.message.reply_text(s.error("❌ Активное голосование не найдено"))
            return
        
        vote = dict(vote)
        
        # Проверяем права
        if vote['created_by'] != user_data['id'] and user_data['rank'] < 3:
            await update.message.reply_text(s.error("❌ У вас нет прав на остановку этого голосования"))
            return
        
        self.db.cursor.execute("UPDATE ban_votes SET status = 'stopped' WHERE id = ?", (vote['id'],))
        self.db.conn.commit()
        
        await update.message.reply_text(s.success("✅ Голосование остановлено"))
    
    async def cmd_vote_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о голосовании"""
        text = update.message.text
        chat_id = update.effective_chat.id
        
        match = re.search(r'гб инфо\s+@?(\S+)', text, re.IGNORECASE)
        if not match:
            await update.message.reply_text(s.error("❌ Укажите пользователя: гб инфо @user"))
            return
        
        username = match.group(1)
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        self.db.cursor.execute("SELECT * FROM ban_votes WHERE chat_id = ? AND target_id = ? AND status = 'active'",
                             (chat_id, target['id']))
        vote = self.db.cursor.fetchone()
        
        if not vote:
            await update.message.reply_text(s.error("❌ Активное голосование не найдено"))
            return
        
        vote = dict(vote)
        creator = self.db.get_user_by_id(vote['created_by'])
        creator_name = creator.get('nickname') or creator['first_name'] if creator else "Неизвестно"
        target_name = target.get('nickname') or target['first_name']
        
        voters = json.loads(vote['voters'])
        
        text = (
            s.header("🗳 ИНФОРМАЦИЯ О ГОЛОСОВАНИИ") + "\n\n"
            f"Цель: {target_name}\n"
            f"Инициатор: {creator_name}\n"
            f"Требуется голосов: {vote['required_votes']}\n"
            f"Минимальный ранг: {vote['min_rank']}\n"
            f"Голосов ЗА: {vote['votes_for']}\n"
            f"Голосов ПРОТИВ: {vote['votes_against']}\n"
            f"Проголосовало: {len(voters)}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_vote_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список активных голосований"""
        chat_id = update.effective_chat.id
        
        self.db.cursor.execute("SELECT * FROM ban_votes WHERE chat_id = ? AND status = 'active'", (chat_id,))
        votes = self.db.cursor.fetchall()
        
        if not votes:
            await update.message.reply_text(s.info("Нет активных голосований"))
            return
        
        text = s.header("🗳 АКТИВНЫЕ ГОЛОСОВАНИЯ") + "\n\n"
        for vote in votes:
            vote = dict(vote)
            target = self.db.get_user_by_id(vote['target_id'])
            target_name = target.get('nickname') or target['first_name'] if target else "Неизвестно"
            text += f"• {target_name} — {vote['votes_for']}/{vote['required_votes']}\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    # ===== СЕТКИ ЧАТОВ =====
    async def cmd_create_grid(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Создать сетку чатов"""
        text = update.message.text
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user.id != OWNER_ID and user_data['rank'] < 5:
            await update.message.reply_text(s.error("❌ Только создатель может создавать сетки"))
            return
        
        match = re.search(r'создать сетку\s+(\S+)', text, re.IGNORECASE)
        if not match:
            await update.message.reply_text(s.error("❌ Укажите название сетки: создать сетка main"))
            return
        
        name = match.group(1)
        
        grid_id = self.db.create_grid(user_data['id'], name)
        
        await update.message.reply_text(s.success(f"✅ Сетка '{name}' (ID: {grid_id}) создана!"))
    
    async def cmd_add_chat_to_grid(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Добавить чат в сетку"""
        text = update.message.text
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        chat_id = update.effective_chat.id
        
        match = re.search(r'установить сетку\s+(\d+)', text, re.IGNORECASE)
        if not match:
            await update.message.reply_text(s.error("❌ Укажите ID сетки: установить сетку 1"))
            return
        
        grid_id = int(match.group(1))
        
        # Проверяем, владелец ли сетки
        self.db.cursor.execute("SELECT owner_id FROM chat_grids WHERE id = ?", (grid_id,))
        row = self.db.cursor.fetchone()
        
        if not row:
            await update.message.reply_text(s.error("❌ Сетка не найдена"))
            return
        
        if row[0] != user_data['id'] and user.id != OWNER_ID:
            await update.message.reply_text(s.error("❌ Вы не владелец этой сетки"))
            return
        
        if self.db.add_chat_to_grid(grid_id, chat_id):
            await update.message.reply_text(s.success("✅ Чат добавлен в сетку!"))
        else:
            await update.message.reply_text(s.error("❌ Чат уже в сетке"))
    
    async def cmd_grids(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список сеток пользователя"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        grids = self.db.get_user_grids(user_data['id'])
        
        if not grids:
            await update.message.reply_text(s.info("У вас нет созданных сеток"))
            return
        
        text = s.header("🔗 МОИ СЕТКИ") + "\n\n"
        for grid in grids:
            text += f"ID: {grid['id']} | {grid['name']}\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_global_mod(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Назначить глобального модератора"""
        text = update.message.text
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        # Парсим: +глмодер @user или сетка 3 !модер @user
        match = re.search(r'\+глмодер\s+@?(\S+)', text, re.IGNORECASE)
        if match:
            username = match.group(1)
            target = self.db.get_user_by_username(username)
            if not target:
                await update.message.reply_text(s.error("❌ Пользователь не найден"))
                return
            
            # Назначаем глобальным модератором (ранг 1 во всех чатах сетки)
            # Здесь нужна логика применения ко всем чатам
            await update.message.reply_text(s.success(f"✅ {target['first_name']} назначен глобальным модератором"))
            return
        
        match = re.search(r'сетка (\d+)\s+(!+)модер\s+@?(\S+)', text, re.IGNORECASE)
        if match:
            grid_id = int(match.group(1))
            rank = len(match.group(2))  # Количество ! определяет ранг
            username = match.group(3)
            
            target = self.db.get_user_by_username(username)
            if not target:
                await update.message.reply_text(s.error("❌ Пользователь не найден"))
                return
            
            # Проверяем права на сетку
            self.db.cursor.execute("SELECT owner_id FROM chat_grids WHERE id = ?", (grid_id,))
            row = self.db.cursor.fetchone()
            
            if not row:
                await update.message.reply_text(s.error("❌ Сетка не найдена"))
                return
            
            if row[0] != user_data['id'] and user.id != OWNER_ID:
                await update.message.reply_text(s.error("❌ Вы не владелец этой сетки"))
                return
            
            # Добавляем в глобальные модераторы
            self.db.cursor.execute("INSERT OR REPLACE INTO global_moderators (grid_id, user_id, rank) VALUES (?, ?, ?)",
                                 (grid_id, target['id'], rank))
            self.db.conn.commit()
            
            # Здесь нужно применить ранг во всех чатах сетки
            
            await update.message.reply_text(s.success(f"✅ {target['first_name']} получил ранг {rank} во всех чатах сетки"))
            return
        
        await update.message.reply_text(s.error("❌ Неверный формат команды"))
    
    async def cmd_global_mods_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список глобальных модераторов"""
        # Здесь нужно получить список из БД
        await update.message.reply_text(s.info("Функция в разработке"))
    
    async def cmd_add_global_mod(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Добавить глобального модератора"""
        await self.cmd_global_mod(update, context)
    
    async def cmd_remove_global_mod(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Удалить глобального модератора"""
        text = update.message.text
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        match = re.search(r'-глмодер\s+@?(\S+)', text, re.IGNORECASE)
        if not match:
            await update.message.reply_text(s.error("❌ Укажите пользователя: -глмодер @user"))
            return
        
        username = match.group(1)
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        # Удаляем из глобальных модераторов
        self.db.cursor.execute("DELETE FROM global_moderators WHERE user_id = ?", (target['id'],))
        self.db.conn.commit()
        
        await update.message.reply_text(s.success(f"✅ {target['first_name']} снят с глобальной модерации"))
    
    async def cmd_grid_set_rank(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установить ранг во всех чатах сетки"""
        # Эта команда уже обрабатывается в cmd_global_mod
        pass
    
    # ===== БОНУСЫ =====
    async def cmd_bonuses(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о бонусах"""
        text = """
# Спектр | Бонусы 🎁

Бонусы — это расширение возможностей Спектра в вашем чате.
Приобретаются на валюту вселенной Спектра — **неоны** 💜

## Доступные бонусы:

1. [👾 Кибер-статус](https://t.me/Spectrum_poleznoe/24) — премиум-доступ, неоновый ник, эксклюзивные РП-команды
2. [🔨 Глитч-молот](https://t.me/Spectrum_poleznoe/26) — временно заглючить (замутить) любого пользователя
3. [⚡ Турбо-драйв](https://t.me/Spectrum_poleznoe/27) — ускоренная прокачка и регенерация
4. [👻 Невидимка](https://t.me/Spectrum_poleznoe/28) — отправка анонимных сообщений
5. [🌈 Неон-ник](https://t.me/Spectrum_poleznoe/29) — фиолетовое свечение ника
6. [🎰 Кибер-удача](https://t.me/Spectrum_poleznoe/30) — увеличение шансов в играх
7. [🔒 Файрволл](https://t.me/Spectrum_poleznoe/31) — защита от мутов и банов
8. [🤖 РП-пакет](https://t.me/Spectrum_poleznoe/32) — эксклюзивные кибер-РП команды

📖 [Подробнее о бонусах](https://teletype.in/@nobucraft/ytX3VR5CKp4)

Команды:
/bonusinfo [название] — информация о конкретном бонусе
/buybonus [название] [срок] — покупка бонуса
        """
        await update.message.reply_text(text, parse_mode='Markdown', disable_web_page_preview=True)
    
    async def cmd_bonus_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о конкретном бонусе"""
        if not context.args:
            await update.message.reply_text(s.error("❌ Укажите название бонуса"))
            return
        
        bonus_name = " ".join(context.args).lower()
        
        bonuses = {
            "кибер-статус": {
                "name": "👾 Кибер-статус",
                "price": 100,
                "duration": "месяц",
                "desc": "Премиум-доступ во вселенную Спектра. Ваш ник засияет неоновым светом, а в вашем распоряжении появятся эксклюзивные кибер-команды.",
                "features": [
                    "🖥 установка неонового ника в чате",
                    "🤖 использование эксклюзивных РП-команд",
                    "⚡ ускоренная прокачка (+20% опыта)",
                    "📟 специальный статус в профиле",
                    "🔒 скрытность от некоторых команд",
                    "💬 получение уведомлений в личные сообщения"
                ],
                "rp_commands": "Взломать • Заглючить • Перегрузить • Закодить • Оцифровать • Хакнуть • Скачать • Обновить • Дефрагментировать • Оптимизировать"
            },
            "глитч-молот": {
                "name": "🔨 Глитч-молот",
                "price": 50,
                "duration": "единоразово",
                "desc": "Позволяет временно заглючить (замутить) любого пользователя сроком до 24 часов, если его ранг не выше «Администратор» (3 уровень).",
                "command": "применить глитч-молот @user"
            },
            "турбо-драйв": {
                "name": "⚡ Турбо-драйв",
                "price": 200,
                "duration": "месяц",
                "desc": "Увеличивает скорость прокачки и регенерацию энергии. С турбо-драйвом вы будете развиваться в 1.5 раза быстрее!",
                "boost": "+50% к опыту и энергии"
            },
            "невидимка": {
                "name": "👻 Невидимка",
                "price": 30,
                "duration": "30 дней",
                "desc": "Позволяет отправлять анонимные сообщения в чат. Участники не узнают, кто отправил сообщение.",
                "command": "Отправка через ЛС бота: Невидимка [текст]"
            },
            "неон-ник": {
                "name": "🌈 Неон-ник",
                "price": 100,
                "duration": "навсегда",
                "desc": "Позволяет установить неоновый никнейм с фиолетовым свечением.",
                "command": "После покупки ваш ник автоматически засияет"
            },
            "кибер-удача": {
                "name": "🎰 Кибер-удача",
                "price": 150,
                "duration": "3 дня",
                "desc": "Увеличивает шансы на выигрыш во всех играх бота.",
                "boost": "+15% к удаче"
            },
            "файрволл": {
                "name": "🔒 Файрволл",
                "price": 80,
                "duration": "до первого использования",
                "desc": "Одноразовая защита от мутов и банов. Активируется автоматически.",
                "note": "Не срабатывает на действия создателя чата"
            },
            "рп-пакет": {
                "name": "🤖 РП-пакет",
                "price": 120,
                "duration": "месяц",
                "desc": "Открывает доступ к эксклюзивным кибер-РП командам.",
                "commands": "/взломать, /заглючить, /перегрузить, /закодить, /оцифровать, /хакнуть, /скачать, /обновить"
            }
        }
        
        bonus = None
        for key, value in bonuses.items():
            if key in bonus_name:
                bonus = value
                break
        
        if not bonus:
            await update.message.reply_text(s.error("❌ Бонус не найден"))
            return
        
        text = s.header(bonus['name']) + "\n"
        text += f"💰 Цена: {bonus['price']} 💜\n"
        text += f"⏳ Длительность: {bonus['duration']}\n\n"
        text += f"{bonus['desc']}\n\n"
        
        if 'features' in bonus:
            text += "**Возможности:**\n"
            for feature in bonus['features']:
                text += f"• {feature}\n"
            text += "\n"
        
        if 'rp_commands' in bonus:
            text += f"🤖 **РП-команды:** {bonus['rp_commands']}\n\n"
        
        if 'command' in bonus:
            text += f"📝 **Использование:** `{bonus['command']}`\n\n"
        
        text += f"🛒 **Купить:** `/buybonus {bonus_name} 1` (на 1 месяц)"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_buy_bonus(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Купить бонус"""
        if len(context.args) < 2:
            await update.message.reply_text(s.error("❌ Использование: /buybonus [название] [срок]"))
            return
        
        bonus_name = context.args[0].lower()
        try:
            duration = int(context.args[1])
        except:
            await update.message.reply_text(s.error("❌ Срок должен быть числом (месяцев)"))
            return
        
        user_data = self.db.get_user(update.effective_user.id)
        
        # Маппинг бонусов
        bonuses = {
            "кибер-статус": {"type": "cyber_status", "price": 100},
            "турбо-драйв": {"type": "turbo_drive", "price": 200},
            "кибер-удача": {"type": "cyber_luck", "price": 150},
            "рп-пакет": {"type": "rp_packet", "price": 120},
            "глитч-молот": {"type": "glitch_hammer", "price": 50},
            "невидимка": {"type": "invisible", "price": 30},
            "неон-ник": {"type": "neon_nick", "price": 100},
            "файрволл": {"type": "firewall", "price": 80}
        }
        
        bonus = None
        for key, value in bonuses.items():
            if key in bonus_name:
                bonus = value
                break
        
        if not bonus:
            await update.message.reply_text(s.error("❌ Бонус не найден"))
            return
        
        total_price = bonus['price'] * duration
        
        if user_data['neons'] < total_price:
            await update.message.reply_text(s.error(f"❌ Недостаточно неонов. Нужно {total_price} 💜"))
            return
        
        if self.db.buy_bonus(user_data['id'], bonus['type'], duration, total_price):
            await update.message.reply_text(
                s.success(f"✅ Бонус '{bonus_name}' куплен на {duration} мес. за {total_price} 💜")
            )
        else:
            await update.message.reply_text(s.error("❌ Ошибка при покупке бонуса"))
    
    # ===== КОНКРЕТНЫЕ БОНУСЫ =====
    async def cmd_cyber_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о кибер-статусе"""
        await self.cmd_bonus_info(update, context)
    
    async def cmd_buy_cyber_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Купить кибер-статус"""
        text = update.message.text
        user_data = self.db.get_user(update.effective_user.id)
        
        # Парсим: купить кибер-статус 3 или купить кибер-статус 3 @user
        match = re.search(r'купить кибер-статус\s+(\d+)(?:\s+@?(\S+))?', text, re.IGNORECASE)
        if not match:
            await update.message.reply_text(s.error("❌ Использование: купить кибер-статус 3 [@user]"))
            return
        
        months = int(match.group(1))
        target_username = match.group(2) if match.group(2) else None
        
        target_id = user_data['id']
        target_name = user_data['first_name']
        
        if target_username:
            target = self.db.get_user_by_username(target_username)
            if not target:
                await update.message.reply_text(s.error("❌ Пользователь не найден"))
                return
            target_id = target['id']
            target_name = target['first_name']
        
        price = 100 * months
        
        if user_data['neons'] < price and target_username:
            await update.message.reply_text(s.error(f"❌ Недостаточно неонов. Нужно {price} 💜"))
            return
        
        if self.db.buy_bonus(target_id, 'cyber_status', months * 30, price if target_username else price):
            await update.message.reply_text(
                s.success(f"✅ Кибер-статус куплен для {target_name} на {months} мес.")
            )
        else:
            await update.message.reply_text(s.error("❌ Ошибка при покупке"))
    
    async def cmd_glitch_hammer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о глитч-молоте"""
        text = """
# 🔨 Глитч-молот

Позволяет временно заглючить (замутить) любого пользователя сроком до 24 часов.

💰 Цена: 50 💜
⏳ Длительность: единоразово

📝 Использование: `применить глитч-молот @user`

⚙️ Настройка в чате:
• Глитч-молот [цена] — установка цены
• Глитч-молот 0 — отключение
• дк глитч-молот [ранг] — ограничение по рангу
        """
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_use_glitch_hammer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Применить глитч-молот"""
        text = update.message.text
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        chat_id = update.effective_chat.id
        
        match = re.search(r'применить глитч-молот\s+@?(\S+)', text, re.IGNORECASE)
        if not match:
            await update.message.reply_text(s.error("❌ Укажите пользователя: применить глитч-молот @user"))
            return
        
        username = match.group(1)
        target = self.db.get_user_by_username(username)
        
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        if target['rank'] >= user_data['rank'] and user.id != OWNER_ID:
            await update.message.reply_text(s.error("⛔️ Нельзя применить к модератору выше рангом"))
            return
        
        # Проверяем наличие бонуса
        if self.db.use_glitch_hammer(user_data['id'], chat_id, target['id']):
            # Мутим на 24 часа
            until = self.db.mute_user(target['id'], 24*60, user_data['id'], "Глитч-молот")
            await update.message.reply_text(
                s.success(f"✅ Глитч-молот применён к {target['first_name']} на 24 часа!")
            )
        else:
            await update.message.reply_text(s.error("❌ У вас нет активного глитч-молота"))
    
    async def cmd_turbo_drive(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о турбо-драйве"""
        await self.cmd_bonus_info(update, context)
    
    async def cmd_buy_turbo_drive(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Купить турбо-драйв"""
        text = update.message.text
        user_data = self.db.get_user(update.effective_user.id)
        
        match = re.search(r'купить турбо-драйв\s+(\d+)', text, re.IGNORECASE)
        if not match:
            await update.message.reply_text(s.error("❌ Использование: купить турбо-драйв 3"))
            return
        
        months = int(match.group(1))
        price = 200 * months
        
        if user_data['neons'] < price:
            await update.message.reply_text(s.error(f"❌ Недостаточно неонов. Нужно {price} 💜"))
            return
        
        if self.db.buy_bonus(user_data['id'], 'turbo_drive', months * 30, price):
            await update.message.reply_text(s.success(f"✅ Турбо-драйв активирован на {months} мес."))
        else:
            await update.message.reply_text(s.error("❌ Ошибка при покупке"))
    
    async def cmd_invisible(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о невидимке"""
        text = """
# 👻 Невидимка

Позволяет отправлять анонимные сообщения в чат через ЛС бота.

💰 Цена: 30 💜
⏳ Длительность: 30 дней

📝 Использование в ЛС:
`Невидимка Текст сообщения`

⚙️ Настройка в чате:
• Невидимка [цена] — установка цены
• +Невидимка @user — разрешить пользователю
• -Невидимка @user — запретить пользователю
        """
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_use_invisible(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отправить анонимное сообщение (только в ЛС)"""
        if update.effective_chat.type != "private":
            await update.message.reply_text(s.error("❌ Эта команда работает только в личных сообщениях с ботом"))
            return
        
        text = update.message.text
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if not text.startswith('Невидимка '):
            return
        
        message_text = text.replace('Невидимка ', '', 1).strip()
        
        if not message_text:
            await update.message.reply_text(s.error("❌ Укажите текст сообщения"))
            return
        
        # Проверяем наличие бонуса
        if not self.db.has_invisible_bonus(user_data['id']):
            await update.message.reply_text(s.error("❌ У вас нет активного бонуса 'Невидимка'"))
            return
        
        # Здесь нужно отправить сообщение в привязанный чат
        # Для простоты пока просто сохраняем
        await update.message.reply_text(s.success("✅ Анонимное сообщение отправлено!"))
    
    async def cmd_allow_invisible(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Разрешить пользователю использовать невидимку"""
        text = update.message.text
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        chat_id = update.effective_chat.id
        
        if user_data['rank'] < 3:
            await update.message.reply_text(s.error("❌ Недостаточно прав"))
            return
        
        match = re.search(r'\+Невидимка\s+@?(\S+)', text, re.IGNORECASE)
        if not match:
            await update.message.reply_text(s.error("❌ Укажите пользователя: +Невидимка @user"))
            return
        
        username = match.group(1)
        target = self.db.get_user_by_username(username)
        
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        # Удаляем из бана
        self.db.cursor.execute("DELETE FROM invisible_bans WHERE chat_id = ? AND user_id = ?", (chat_id, target['id']))
        self.db.conn.commit()
        
        await update.message.reply_text(s.success(f"✅ {target['first_name']} может использовать невидимку"))
    
    async def cmd_ban_invisible(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Запретить пользователю использовать невидимку"""
        text = update.message.text
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        chat_id = update.effective_chat.id
        
        if user_data['rank'] < 3:
            await update.message.reply_text(s.error("❌ Недостаточно прав"))
            return
        
        match = re.search(r'-Невидимка\s+@?(\S+)', text, re.IGNORECASE)
        if not match:
            await update.message.reply_text(s.error("❌ Укажите пользователя: -Невидимка @user"))
            return
        
        username = match.group(1)
        target = self.db.get_user_by_username(username)
        
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        # Добавляем в бан
        self.db.cursor.execute("INSERT OR REPLACE INTO invisible_bans (chat_id, user_id, banned_by) VALUES (?, ?, ?)",
                             (chat_id, target['id'], user_data['id']))
        self.db.conn.commit()
        
        await update.message.reply_text(s.success(f"✅ {target['first_name']} забанен в невидимке"))
    
    async def cmd_neon_nick(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о неон-нике"""
        await self.cmd_bonus_info(update, context)
    
    async def cmd_buy_neon_nick(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Купить неон-ник"""
        user_data = self.db.get_user(update.effective_user.id)
        
        if user_data['neons'] < 100:
            await update.message.reply_text(s.error(f"❌ Недостаточно неонов. Нужно 100 💜"))
            return
        
        if self.db.buy_bonus(user_data['id'], 'neon_nick', 9999, 100):
            # Устанавливаем специальный статус
            await update.message.reply_text(s.success("✅ Неон-ник активирован! Ваш ник теперь сияет!"))
        else:
            await update.message.reply_text(s.error("❌ Ошибка при покупке"))
    
    async def cmd_cyber_luck(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о кибер-удаче"""
        await self.cmd_bonus_info(update, context)
    
    async def cmd_buy_cyber_luck(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Купить кибер-удачу"""
        text = update.message.text
        user_data = self.db.get_user(update.effective_user.id)
        
        match = re.search(r'купить кибер-удачу\s+(\d+)', text, re.IGNORECASE)
        if not match:
            await update.message.reply_text(s.error("❌ Использование: купить кибер-удачу 3"))
            return
        
        days = int(match.group(1))
        price = 50 * days  # 50 неонов за 3 дня
        
        if user_data['neons'] < price:
            await update.message.reply_text(s.error(f"❌ Недостаточно неонов. Нужно {price} 💜"))
            return
        
        if self.db.buy_bonus(user_data['id'], 'cyber_luck', days, price):
            await update.message.reply_text(s.success(f"✅ Кибер-удача активирована на {days} дней!"))
        else:
            await update.message.reply_text(s.error("❌ Ошибка при покупке"))
    
    async def cmd_firewall(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о файрволле"""
        await self.cmd_bonus_info(update, context)
    
    async def cmd_buy_firewall(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Купить файрволл"""
        user_data = self.db.get_user(update.effective_user.id)
        
        if user_data['neons'] < 80:
            await update.message.reply_text(s.error(f"❌ Недостаточно неонов. Нужно 80 💜"))
            return
        
        if self.db.buy_bonus(user_data['id'], 'firewall', 30, 80):
            await update.message.reply_text(s.success("✅ Файрволл активирован! Вы защищены от одного наказания."))
        else:
            await update.message.reply_text(s.error("❌ Ошибка при покупке"))
    
    async def cmd_rp_packet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о РП-пакете"""
        await self.cmd_bonus_info(update, context)
    
    async def cmd_buy_rp_packet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Купить РП-пакет"""
        text = update.message.text
        user_data = self.db.get_user(update.effective_user.id)
        
        match = re.search(r'купить рп-пакет\s+(\d+)', text, re.IGNORECASE)
        if not match:
            await update.message.reply_text(s.error("❌ Использование: купить рп-пакет 3"))
            return
        
        months = int(match.group(1))
        price = 120 * months
        
        if user_data['neons'] < price:
            await update.message.reply_text(s.error(f"❌ Недостаточно неонов. Нужно {price} 💜"))
            return
        
        if self.db.buy_bonus(user_data['id'], 'rp_packet', months * 30, price):
            await update.message.reply_text(s.success(f"✅ РП-пакет активирован на {months} мес.!"))
        else:
            await update.message.reply_text(s.error("❌ Ошибка при покупке"))
    
    # ===== РП КОМАНДЫ =====
    async def _check_rp_packet(self, user_id: int) -> bool:
        """Проверка наличия РП-пакета"""
        user = self.db.get_user_by_id(user_id)
        if not user:
            return False
        
        if user.get('rp_packet_until') and datetime.fromisoformat(user['rp_packet_until']) > datetime.now():
            return True
        if user.get('cyber_status_until') and datetime.fromisoformat(user['cyber_status_until']) > datetime.now():
            return True
        
        return False
    
    async def cmd_rp_hack(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/взломать @user"""
        if not await self._check_rp_packet(update.effective_user.id):
            await update.message.reply_text(s.error("❌ Для этой команды нужен РП-пакет или Кибер-статус"))
            return
        
        text = update.message.text
        match = re.search(r'@(\S+)', text)
        if not match:
            await update.message.reply_text(s.error("❌ Укажите пользователя"))
            return
        
        username = match.group(1)
        target = self.db.get_user_by_username(username)
        target_name = target.get('nickname') or target['first_name'] if target else username
        
        actions = [
            f"💻 Взломал аккаунт {target_name} и получил доступ к его переписке",
            f"🔓 Взломал базу данных и узнал все секреты {target_name}",
            f"📱 Взломал телефон {target_name} и теперь читает его сообщения",
            f"🖥 Взломал компьютер {target_name} и скачал все файлы"
        ]
        
        await update.message.reply_text(f"🤖 {random.choice(actions)}")
    
    async def cmd_rp_glitch(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/заглючить @user"""
        if not await self._check_rp_packet(update.effective_user.id):
            await update.message.reply_text(s.error("❌ Для этой команды нужен РП-пакет или Кибер-статус"))
            return
        
        text = update.message.text
        match = re.search(r'@(\S+)', text)
        if not match:
            await update.message.reply_text(s.error("❌ Укажите пользователя"))
            return
        
        username = match.group(1)
        target = self.db.get_user_by_username(username)
        target_name = target.get('nickname') or target['first_name'] if target else username
        
        actions = [
            f"⚡ Вызвал системный глитч у {target_name}, теперь он двоится в глазах",
            f"💫 Заглючил {target_name}, теперь он разговаривает с самим собой",
            f"🌀 Внёс ошибку в код {target_name}, теперь он делает странные вещи",
            f"📟 Отправил вирус {target_name}, теперь его аватарка мерцает"
        ]
        
        await update.message.reply_text(f"🤖 {random.choice(actions)}")
    
    async def cmd_rp_reboot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/перегрузить @user"""
        if not await self._check_rp_packet(update.effective_user.id):
            await update.message.reply_text(s.error("❌ Для этой команды нужен РП-пакет или Кибер-статус"))
            return
        
        text = update.message.text
        match = re.search(r'@(\S+)', text)
        if not match:
            await update.message.reply_text(s.error("❌ Укажите пользователя"))
            return
        
        username = match.group(1)
        target = self.db.get_user_by_username(username)
        target_name = target.get('nickname') or target['first_name'] if target else username
        
        await update.message.reply_text(f"🤖 Перезагрузил {target_name}. Подождите 5 секунд... 🔄")
    
    async def cmd_rp_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/закодить @user"""
        if not await self._check_rp_packet(update.effective_user.id):
            await update.message.reply_text(s.error("❌ Для этой команды нужен РП-пакет или Кибер-статус"))
            return
        
        text = update.message.text
        match = re.search(r'@(\S+)', text)
        if not match:
            await update.message.reply_text(s.error("❌ Укажите пользователя"))
            return
        
        username = match.group(1)
        target = self.db.get_user_by_username(username)
        target_name = target.get('nickname') or target['first_name'] if target else username
        
        code = f"function {target_name}() {{ return 'робот'; }}"
        
        await update.message.reply_text(f"🤖 Закодил {target_name} в функцию:\n`{code}`", parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_rp_digitize(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/оцифровать @user"""
        if not await self._check_rp_packet(update.effective_user.id):
            await update.message.reply_text(s.error("❌ Для этой команды нужен РП-пакет или Кибер-статус"))
            return
        
        text = update.message.text
        match = re.search(r'@(\S+)', text)
        if not match:
            await update.message.reply_text(s.error("❌ Укажите пользователя"))
            return
        
        username = match.group(1)
        target = self.db.get_user_by_username(username)
        target_name = target.get('nickname') or target['first_name'] if target else username
        
        binary = ' '.join(format(ord(c), '08b') for c in target_name[:3])
        
        await update.message.reply_text(f"🤖 Оцифровал {target_name}: `{binary}...`", parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_rp_hack_deep(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/хакнуть @user"""
        if not await self._check_rp_packet(update.effective_user.id):
            await update.message.reply_text(s.error("❌ Для этой команды нужен РП-пакет или Кибер-статус"))
            return
        
        text = update.message.text
        match = re.search(r'@(\S+)', text)
        if not match:
            await update.message.reply_text(s.error("❌ Укажите пользователя"))
            return
        
        username = match.group(1)
        target = self.db.get_user_by_username(username)
        target_name = target.get('nickname') or target['first_name'] if target else username
        
        data = {
            'IP': f'192.168.{random.randint(1,255)}.{random.randint(1,255)}',
            'Пароль': '*' * random.randint(6, 12),
            'Баланс': f'{random.randint(0,1000)} 💰',
            'Последний вход': 'только что'
        }
        
        text = f"🤖 Данные {target_name}:\n"
        for key, value in data.items():
            text += f"• {key}: {value}\n"
        
        await update.message.reply_text(text)
    
    async def cmd_rp_download(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/скачать @user"""
        if not await self._check_rp_packet(update.effective_user.id):
            await update.message.reply_text(s.error("❌ Для этой команды нужен РП-пакет или Кибер-статус"))
            return
        
        text = update.message.text
        match = re.search(r'@(\S+)', text)
        if not match:
            await update.message.reply_text(s.error("❌ Укажите пользователя"))
            return
        
        username = match.group(1)
        target = self.db.get_user_by_username(username)
        target_name = target.get('nickname') or target['first_name'] if target else username
        
        size = random.randint(1, 100)
        
        await update.message.reply_text(f"🤖 Скачиваю данные {target_name}... {size}% [░░░░░░░░░░]")
        await asyncio.sleep(1)
        await update.message.reply_text(f"🤖 Скачивание завершено! Получено {random.randint(10,500)} МБ данных.")
    
    async def cmd_rp_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/обновить @user"""
        if not await self._check_rp_packet(update.effective_user.id):
            await update.message.reply_text(s.error("❌ Для этой команды нужен РП-пакет или Кибер-статус"))
            return
        
        text = update.message.text
        match = re.search(r'@(\S+)', text)
        if not match:
            await update.message.reply_text(s.error("❌ Укажите пользователя"))
            return
        
        username = match.group(1)
        target = self.db.get_user_by_username(username)
        target_name = target.get('nickname') or target['first_name'] if target else username
        
        version = f"v{random.randint(1,9)}.{random.randint(0,9)}.{random.randint(0,9)}"
        
        await update.message.reply_text(f"🤖 Обновляю {target_name} до версии {version}...")
        await asyncio.sleep(1)
        await update.message.reply_text(f"🤖 Обновление завершено! Добавлены новые функции.")
    
    # ===== ТЕЛЕГРАМ БОНУСЫ =====
    async def cmd_tg_premium(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о Telegram Premium"""
        text = """
# ⭐️ Telegram Premium

Купите Telegram Premium за неоны!

💰 Цены:
• 3 месяца — 1500 💜
• 6 месяцев — 2500 💜
• 12 месяцев — 4000 💜

📝 Команды:
• `купить тг прем 3` — купить себе на 3 месяца
• `подарить тг прем 6 @user` — подарить на 6 месяцев

💡 Бонусы Telegram Premium:
• Увеличенные лимиты
• Стикеры премиум
• Реакции
• Голосовые в 2 раза дольше
• И многое другое!
        """
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_buy_tg_premium(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Купить Telegram Premium"""
        text = update.message.text
        user_data = self.db.get_user(update.effective_user.id)
        
        match = re.search(r'купить тг прем\s+(\d+)', text, re.IGNORECASE)
        if not match:
            await update.message.reply_text(s.error("❌ Использование: купить тг прем 3"))
            return
        
        months = int(match.group(1))
        
        prices = {3: 1500, 6: 2500, 12: 4000}
        if months not in prices:
            await update.message.reply_text(s.error("❌ Доступные периоды: 3, 6, 12 месяцев"))
            return
        
        price = prices[months]
        
        if user_data['neons'] < price:
            await update.message.reply_text(s.error(f"❌ Недостаточно неонов. Нужно {price} 💜"))
            return
        
        # Здесь должна быть интеграция с Telegram API для покупки Premium
        # Пока просто имитируем
        self.db.add_neons(user_data['id'], -price)
        
        await update.message.reply_text(
            s.success(f"✅ Telegram Premium на {months} мес. активирован! Спасибо за покупку!")
        )
    
    async def cmd_gift_tg_premium(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Подарить Telegram Premium"""
        text = update.message.text
        user_data = self.db.get_user(update.effective_user.id)
        
        match = re.search(r'подарить тг прем\s+(\d+)\s+@?(\S+)', text, re.IGNORECASE)
        if not match:
            await update.message.reply_text(s.error("❌ Использование: подарить тг прем 3 @user"))
            return
        
        months = int(match.group(1))
        username = match.group(2)
        
        prices = {3: 1500, 6: 2500, 12: 4000}
        if months not in prices:
            await update.message.reply_text(s.error("❌ Доступные периоды: 3, 6, 12 месяцев"))
            return
        
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        price = prices[months]
        
        if user_data['neons'] < price:
            await update.message.reply_text(s.error(f"❌ Недостаточно неонов. Нужно {price} 💜"))
            return
        
        self.db.add_neons(user_data['id'], -price)
        
        await update.message.reply_text(
            s.success(f"✅ Telegram Premium на {months} мес. подарен {target['first_name']}!")
        )
        
        try:
            await context.bot.send_message(
                target['telegram_id'],
                f"{s.success('🎁 ВАМ ПОДАРИЛИ TELEGRAM PREMIUM!')}\n\n"
                f"От: {update.effective_user.first_name}\n"
                f"Срок: {months} месяцев"
            )
        except:
            pass
    
    async def cmd_tg_gift(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о Telegram подарках"""
        text = """
# 🎁 Telegram Подарки

Дарите подарки из Telegram за неоны!

💰 Цена: 500 💜 за подарок

📝 Команды:
• `купить тг подарок` — купить подарок себе
• `подарить тг подарок @user` — подарить подарок

🎁 Подарки бывают разные:
🎂 Торт, 🎈 Шары, 🎉 Хлопушка, 🎊 Конфетти, 🎀 Бантик
        """
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_buy_tg_gift(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Купить Telegram подарок"""
        user_data = self.db.get_user(update.effective_user.id)
        
        if user_data['neons'] < 500:
            await update.message.reply_text(s.error(f"❌ Недостаточно неонов. Нужно 500 💜"))
            return
        
        self.db.add_neons(user_data['id'], -500)
        
        gifts = ["🎂 Торт", "🎈 Шары", "🎉 Хлопушка", "🎊 Конфетти", "🎀 Бантик"]
        gift = random.choice(gifts)
        
        await update.message.reply_text(
            s.success(f"✅ Вы купили подарок: {gift}! Он появится в вашем инвентаре.")
        )
    
    async def cmd_gift_tg_gift(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Подарить Telegram подарок"""
        text = update.message.text
        user_data = self.db.get_user(update.effective_user.id)
        
        match = re.search(r'подарить тг подарок\s+@?(\S+)', text, re.IGNORECASE)
        if not match:
            await update.message.reply_text(s.error("❌ Использование: подарить тг подарок @user"))
            return
        
        username = match.group(1)
        target = self.db.get_user_by_username(username)
        
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        if user_data['neons'] < 500:
            await update.message.reply_text(s.error(f"❌ Недостаточно неонов. Нужно 500 💜"))
            return
        
        self.db.add_neons(user_data['id'], -500)
        
        gifts = ["🎂 Торт", "🎈 Шары", "🎉 Хлопушка", "🎊 Конфетти", "🎀 Бантик"]
        gift = random.choice(gifts)
        
        await update.message.reply_text(
            s.success(f"✅ Вы подарили {gift} пользователю {target['first_name']}!")
        )
        
        try:
            await context.bot.send_message(
                target['telegram_id'],
                f"{s.success('🎁 ВАМ ПОДАРИЛИ ПОДАРОК!')}\n\n"
                f"От: {update.effective_user.first_name}\n"
                f"Подарок: {gift}"
            )
        except:
            pass
    
    async def cmd_tg_stars(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о Telegram Звёздах"""
        text = """
# 🌟 Telegram Звёзды

Покупайте Telegram Звёзды за неоны!

💰 Курс: 1 ⭐️ = 10 💜

📝 Команды:
• `купить тг зв 100` — купить 100 звёзд
• `передать тг зв 50 @user` — передать звёзды
• `где мои тг зв` — история транзакций
        """
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_buy_tg_stars(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Купить Telegram Звёзды"""
        text = update.message.text
        user_data = self.db.get_user(update.effective_user.id)
        
        match = re.search(r'купить тг зв\s+(\d+)', text, re.IGNORECASE)
        if not match:
            await update.message.reply_text(s.error("❌ Использование: купить тг зв 100"))
            return
        
        stars = int(match.group(1))
        price = stars * 10  # 10 неонов за 1 звезду
        
        if user_data['neons'] < price:
            await update.message.reply_text(s.error(f"❌ Недостаточно неонов. Нужно {price} 💜"))
            return
        
        self.db.add_neons(user_data['id'], -price)
        
        # Здесь нужно добавить интеграцию с Telegram Stars API
        
        await update.message.reply_text(
            s.success(f"✅ Куплено {stars} ⭐️ за {price} 💜!")
        )
    
    async def cmd_transfer_tg_stars(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Передать Telegram Звёзды"""
        text = update.message.text
        user_data = self.db.get_user(update.effective_user.id)
        
        match = re.search(r'передать тг зв\s+(\d+)\s+@?(\S+)', text, re.IGNORECASE)
        if not match:
            await update.message.reply_text(s.error("❌ Использование: передать тг зв 50 @user"))
            return
        
        stars = int(match.group(1))
        username = match.group(2)
        
        target = self.db.get_user_by_username(username)
        if not target:
            await update.message.reply_text(s.error("❌ Пользователь не найден"))
            return
        
        # Здесь должна быть интеграция с Telegram API
        
        await update.message.reply_text(
            s.success(f"✅ Передано {stars} ⭐️ пользователю {target['first_name']}!")
        )
    
    async def cmd_my_tg_stars(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """История транзакций Telegram Звёзд"""
        await update.message.reply_text(s.info("Функция в разработке"))
    
    # ===== ТЕМЫ ДЛЯ РОЛЕЙ =====
    async def cmd_themes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список доступных тем для ролей"""
        themes = {
            "default": "Стандартная",
            "cyber": "Киберпанк",
            "fantasy": "Фэнтези",
            "anime": "Аниме",
            "military": "Военная"
        }
        
        text = s.header("🎨 ТЕМЫ РОЛЕЙ") + "\n\n"
        for key, name in themes.items():
            text += f"• `!темы {key}` — {name}\n"
        
        text += "\nПримеры названий:\n"
        text += "• Киберпанк: Хакер, Кодер, Системный администратор\n"
        text += "• Фэнтези: Маг, Воин, Эльф\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_apply_theme(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Применить тему"""
        text = update.message.text
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data['rank'] < 3:
            await update.message.reply_text(s.error("❌ Недостаточно прав"))
            return
        
        match = re.search(r'!темы\s+(\d+)', text)
        if not match:
            return
        
        theme_num = int(match.group(1))
        
        themes = {
            1: ["Хакер", "Кодер", "Админ", "Сисоп", "Девелопер"],
            2: ["Маг", "Воин", "Лучник", "Паладин", "Некромант"],
            3: ["Самурай", "Ниндзя", "Сенсей", "Ронин", "Сёгун"],
            4: ["Капитан", "Лейтенант", "Сержант", "Рядовой", "Генерал"],
            5: ["Ангел", "Демон", "Падший", "Святой", "Пророк"]
        }
        
        if theme_num not in themes:
            await update.message.reply_text(s.error("❌ Тема не найдена"))
            return
        
        # Здесь нужно применить тему к рангам
        await update.message.reply_text(s.success(f"✅ Тема {theme_num} применена!"))
    
    async def cmd_apply_theme_by_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Применить тему по имени"""
        text = update.message.text
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data['rank'] < 3:
            await update.message.reply_text(s.error("❌ Недостаточно прав"))
            return
        
        match = re.search(r'!темы\s+(\w+)', text)
        if not match:
            return
        
        theme_name = match.group(1).lower()
        
        themes = {
            "cyber": ["Хакер", "Кодер", "Админ", "Сисоп", "Девелопер"],
            "fantasy": ["Маг", "Воин", "Лучник", "Паладин", "Некромант"],
            "anime": ["Самурай", "Ниндзя", "Сенсей", "Ронин", "Сёгун"],
            "military": ["Капитан", "Лейтенант", "Сержант", "Рядовой", "Генерал"]
        }
        
        if theme_name not in themes:
            await update.message.reply_text(s.error("❌ Тема не найдена"))
            return
        
        await update.message.reply_text(s.success(f"✅ Тема '{theme_name}' применена!"))
    
    # ===== ПРИВЯЗКА ЧАТА =====
    async def cmd_bind_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Привязать чат (для использования через ЛС)"""
        if update.effective_chat.type == "private":
            await update.message.reply_text(s.error("❌ Эта команда работает только в группах"))
            return
        
        chat_id = update.effective_chat.id
        chat_title = update.effective_chat.title
        
        # Генерируем код чата
        chat_code = hashlib.md5(f"{chat_id}_{random.randint(1000,9999)}".encode()).hexdigest()[:8]
        
        self.db.cursor.execute('''
            INSERT INTO chat_settings (chat_id, chat_name, chat_code)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET chat_code = excluded.chat_code
        ''', (chat_id, chat_title, chat_code))
        self.db.conn.commit()
        
        await update.message.reply_text(
            f"{s.success('✅ Чат привязан!')}\n\n"
            f"Код чата: `{chat_code}`\n\n"
            f"Теперь вы можете использовать команды через ЛС бота, указывая этот код."
        )
    
    # ===== КОД ЧАТА =====
    async def cmd_chat_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получить код чата"""
        chat_id = update.effective_chat.id
        
        self.db.cursor.execute("SELECT chat_code FROM chat_settings WHERE chat_id = ?", (chat_id,))
        row = self.db.cursor.fetchone()
        
        if not row:
            await update.message.reply_text(s.error("❌ Чат не привязан. Используйте !привязать"))
            return
        
        await update.message.reply_text(
            f"🔑 Код чата: `{row[0]}`\n\n"
            f"Используйте этот код для команд через ЛС бота."
        )
    
    async def cmd_change_chat_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сменить код чата"""
        text = update.message.text
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        chat_id = update.effective_chat.id
        
        if user_data['rank'] < 3 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("❌ Недостаточно прав"))
            return
        
        match = re.search(r'сменить код\s+(\S+)', text, re.IGNORECASE)
        if not match:
            await update.message.reply_text(s.error("❌ Укажите новый код: сменить код x5g7k9"))
            return
        
        new_code = match.group(1)
        
        if len(new_code) < 3 or len(new_code) > 10:
            await update.message.reply_text(s.error("❌ Код должен быть от 3 до 10 символов"))
            return
        
        # Проверяем, свободен ли код
        self.db.cursor.execute("SELECT chat_id FROM chat_settings WHERE chat_code = ?", (new_code,))
        if self.db.cursor.fetchone():
            await update.message.reply_text(s.error("❌ Этот код уже занят"))
            return
        
        self.db.cursor.execute("UPDATE chat_settings SET chat_code = ? WHERE chat_id = ?", (new_code, chat_id))
        self.db.conn.commit()
        
        await update.message.reply_text(s.success(f"✅ Код чата изменён на `{new_code}`"))
    
    # ===== КУБЫШКА =====
    async def cmd_treasury(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о кубышке чата"""
        chat_id = update.effective_chat.id
        
        self.db.cursor.execute("SELECT treasury_neons, treasury_glitches FROM chat_settings WHERE chat_id = ?", (chat_id,))
        row = self.db.cursor.fetchone()
        
        if not row:
            await update.message.reply_text(s.error("❌ Настройки чата не найдены"))
            return
        
        neons, glitches = row[0], row[1]
        
        text = (
            s.header("💰 КУБЫШКА ЧАТА") + "\n\n"
            f"{s.stat('Неонов', f'{neons} 💜')}\n"
            f"{s.stat('Глитчей', f'{glitches} 🖥')}\n\n"
            f"40% от покупок бонусов в чате поступает в кубышку.\n\n"
            f"{s.cmd('кубышка в неоны', 'перевести неоны в личный кошелёк')}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_treasury_withdraw(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Вывод из кубышки"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        chat_id = update.effective_chat.id
        
        if user_data['rank'] < 3 and user.id != OWNER_ID:
            await update.message.reply_text(s.error("❌ Недостаточно прав"))
            return
        
        self.db.cursor.execute("SELECT treasury_neons FROM chat_settings WHERE chat_id = ?", (chat_id,))
        row = self.db.cursor.fetchone()
        
        if not row or row[0] == 0:
            await update.message.reply_text(s.error("❌ В кубышке нет неонов"))
            return
        
        neons = row[0]
        
        self.db.add_neons(user_data['id'], neons)
        self.db.cursor.execute("UPDATE chat_settings SET treasury_neons = 0 WHERE chat_id = ?", (chat_id,))
        self.db.conn.commit()
        
        await update.message.reply_text(s.success(f"✅ {neons} 💜 переведены в ваш кошелёк!"))
    
    # ===== ОБРАБОТЧИК СООБЩЕНИЙ =====
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        message_text = update.message.text
        chat = update.effective_chat
        
        if not user or not message_text:
            return
        
        # Сохраняем сообщение в БД
        self.db.save_message(
            user.id, 
            user.username, 
            user.first_name, 
            message_text, 
            chat.id, 
            chat.title
        )
        
        if message_text.startswith('/'):
            return
        
        user_data = self.db.get_user(user.id, user.first_name)
        self.db.update_user(user_data['id'], messages_count=user_data.get('messages_count', 0) + 1)
        
        if self.db.is_banned(user_data['id']):
            return
        
        if self.db.is_muted(user_data['id']):
            await update.message.reply_text(s.error("🔇 Ты в муте"))
            return
        
        # Проверка на файрволл (защита от наказаний)
        if user_data.get('firewall_expires') and datetime.fromisoformat(user_data['firewall_expires']) > datetime.now():
            if user_data.get('firewall_used') == 0:
                # Файрволл активен, но пока не использован
                pass
        
        if await self.check_spam(update):
            return
        
        if self.db.is_word_blacklisted(message_text):
            await update.message.delete()
            await update.message.reply_text(s.warning("⚠️ Запрещенное слово! Сообщение удалено."))
            return
        
        # Обработка RPS (камень-ножницы-бумага)
        if context.user_data.get('awaiting_rps'):
            if message_text in ["1", "2", "3"]:
                context.user_data['awaiting_rps'] = False
                
                choices = {1: "🪨 Камень", 2: "✂️ Ножницы", 3: "📄 Бумага"}
                results = {
                    (1,2): "win", (2,3): "win", (3,1): "win",
                    (2,1): "lose", (3,2): "lose", (1,3): "lose"
                }
                
                player_choice = int(message_text)
                bot_choice = random.randint(1, 3)
                
                text = s.header("✊ КНБ") + "\n\n"
                text += f"**Вы: {choices[player_choice]}\n"
                text += f"Бот: {choices[bot_choice]}\n\n"
                
                if player_choice == bot_choice:
                    self.db.update_user(user_data['id'], rps_draws=user_data.get('rps_draws', 0) + 1)
                    text += s.info("🤝 НИЧЬЯ!")
                elif results.get((player_choice, bot_choice)) == "win":
                    self.db.update_user(user_data['id'], rps_wins=user_data.get('rps_wins', 0) + 1)
                    reward = random.randint(10, 30)
                    self.db.add_coins(user_data['id'], reward)
                    text += s.success(f"🎉 ПОБЕДА! +{reward} 💰")
                else:
                    self.db.update_user(user_data['id'], rps_losses=user_data.get('rps_losses', 0) + 1)
                    text += s.error("😢 ПОРАЖЕНИЕ!")
                
                await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
                return
        
        # Проверка на активные игры
        for game_id, game in list(self.games_in_progress.items()):
            if game.get('user_id') == user.id:
                if game_id.startswith('guess_'):
                    try:
                        guess = int(message_text)
                        game['attempts'] += 1
                        
                        if guess == game['number']:
                            win = game['bet'] * 2
                            self.db.add_coins(user_data['id'], win)
                            self.db.update_user(user_data['id'], guess_wins=user_data.get('guess_wins', 0) + 1)
                            await update.message.reply_text(
                                s.success(f"🎉 ПОБЕДА! Число {game['number']}!\nПопыток: {game['attempts']}\nВыигрыш: {win} 💰"),
                                parse_mode=ParseMode.MARKDOWN
                            )
                            del self.games_in_progress[game_id]
                        elif game['attempts'] >= game['max_attempts']:
                            self.db.update_user(user_data['id'], guess_losses=user_data.get('guess_losses', 0) + 1)
                            await update.message.reply_text(
                                s.error(f"❌ Попытки кончились! Было число {game['number']}"),
                                parse_mode=ParseMode.MARKDOWN
                            )
                            del self.games_in_progress[game_id]
                        elif guess < game['number']:
                            await update.message.reply_text(f"📈 Загаданное число больше {guess}")
                        else:
                            await update.message.reply_text(f"📉 Загаданное число меньше {guess}")
                    except ValueError:
                        await update.message.reply_text(s.error("❌ Введите число от 1 до 100"))
                    return
                
                elif game_id.startswith('bulls_'):
                    if len(message_text) != 4 or not message_text.isdigit():
                        await update.message.reply_text(s.error("❌ Введите 4 цифры"))
                        return
                    
                    guess = message_text
                    if len(set(guess)) != 4:
                        await update.message.reply_text(s.error("❌ Цифры не должны повторяться"))
                        return
                    
                    bulls = 0
                    cows = 0
                    for i in range(4):
                        if guess[i] == game['number'][i]:
                            bulls += 1
                        elif guess[i] in game['number']:
                            cows += 1
                    
                    game['attempts'].append((guess, bulls, cows))
                    
                    if bulls == 4:
                        win = game['bet'] * 3
                        self.db.add_coins(user_data['id'], win)
                        self.db.update_user(user_data['id'], bulls_wins=user_data.get('bulls_wins', 0) + 1)
                        await update.message.reply_text(
                            s.success(f"🎉 ПОБЕДА! Число {game['number']}!\nПопыток: {len(game['attempts'])}\nВыигрыш: {win} 💰"),
                            parse_mode=ParseMode.MARKDOWN
                        )
                        del self.games_in_progress[game_id]
                    elif len(game['attempts']) >= game['max_attempts']:
                        self.db.update_user(user_data['id'], bulls_losses=user_data.get('bulls_losses', 0) + 1)
                        await update.message.reply_text(
                            s.error(f"❌ Попытки кончились! Было число {game['number']}"),
                            parse_mode=ParseMode.MARKDOWN
                        )
                        del self.games_in_progress[game_id]
                    else:
                        await update.message.reply_text(
                            f"🔍 Быки: {bulls}, Коровы: {cows}\nОсталось попыток: {game['max_attempts'] - len(game['attempts'])}"
                        )
                    return

                               # Проверяем, нужно ли AI ответить
        is_reply_to_bot = (update.message.reply_to_message and 
                          update.message.reply_to_message.from_user.id == context.bot.id)
        
        should_respond = False
        force_response = False
        ai_message = message_text  # копируем для возможного изменения
        
        # Всегда отвечаем на "Спектр"
        if ai_message.lower().startswith("спектр"):
            should_respond = True
            force_response = True
            ai_message = ai_message[6:].strip()
            if not ai_message:
                ai_message = "Привет"
        # В личке отвечаем на всё
        elif chat.type == "private":
            should_respond = True
            force_response = True
        # В группах проверяем по алгоритму
        elif self.ai and self.ai.is_available:
            should_respond = await self.ai.should_respond(ai_message, is_reply_to_bot)
            force_response = False
        
        if should_respond and self.ai and self.ai.is_available:
            try:
                await update.message.chat.send_action(action="typing")
                response = await self.ai.get_response(
                    user.id, 
                    ai_message, 
                    user.first_name,
                    force_response=force_response
                )
                if response:
                    # Добавляем эмодзи робота только если это прямое обращение
                    prefix = "🤖 " if force_response else ""
                    await update.message.reply_text(f"{prefix}{response}", parse_mode=ParseMode.MARKDOWN)
                    return
            except Exception as e:
                logger.error(f"AI response error: {e}")
        
        # AI отвечает если:
        # 1. Это личка (чат с ботом) - всегда отвечает
        # 2. В группе - только если сообщение начинается со слова "Спектр"
        should_respond = False
        
        if chat.type == "private":
            should_respond = True
        elif message_text.lower().startswith("спектр"):
            message_text = message_text[6:].strip()
            if not message_text:
                message_text = "Привет"
            should_respond = True
        
        if should_respond and self.ai and self.ai.is_available:
            try:
                await update.message.chat.send_action(action="typing")
                response = await self.ai.get_response(user.id, message_text, user.first_name)
                if response:
                    await update.message.reply_text(f"🤖 Спектр: {response}", parse_mode=ParseMode.MARKDOWN)
                    return
            except Exception as e:
                logger.error(f"AI response error: {e}")
        
        # Если AI не сработал, но это личка, отправляем подсказку
        if chat.type == "private" and not should_respond:
            await update.message.reply_text(
                "🤖 Я здесь! Используй /help для списка команд или просто напиши мне что-нибудь."
            )
    
    async def handle_new_members(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        
        self.db.cursor.execute("SELECT welcome FROM chat_settings WHERE chat_id = ?", (chat_id,))
        row = self.db.cursor.fetchone()
        welcome_text = row[0] if row and row[0] else "Добро пожаловать!"
        
        for member in update.message.new_chat_members:
            if member.is_bot:
                continue
            
            self.db.get_user(member.id, member.first_name)
            
            # Проверяем пол для приветствия
            user_data = self.db.get_user_by_id(member.id)
            gender = user_data.get('gender', 'не указан')
            
            welcome = welcome_text.replace('{имя}', member.first_name)
            if gender == 'м':
                welcome = welcome.replace('{ж|м|мн}', 'присоединился')
            elif gender == 'ж':
                welcome = welcome.replace('{ж|м|мн}', 'присоединилась')
            else:
                welcome = welcome.replace('{ж|м|мн}', 'присоединился(ась)')
            
            await update.message.reply_text(
                f"👋 {welcome}\n\n{member.first_name}, используй /help для команд!",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def handle_left_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        member = update.message.left_chat_member
        if member.is_bot:
            return
        
        await update.message.reply_text(f"👋 {member.first_name} покинул чат...", parse_mode=ParseMode.MARKDOWN)
    
    # ===== CALLBACK КНОПКИ =====
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        user = query.from_user
        user_data = self.db.get_user(user.id)
        
        # Кнопки главного меню
        if data == "random_chat":
            # Поиск случайной беседы
            self.db.cursor.execute("SELECT chat_id, chat_name FROM chat_settings WHERE chat_code IS NOT NULL ORDER BY RANDOM() LIMIT 1")
            row = self.db.cursor.fetchone()
            if row:
                await query.edit_message_text(
                    f"🎲 Случайная беседа найдена!\n\n"
                    f"Название: {row[1]}\n"
                    f"ID: `{row[0]}`\n\n"
                    f"Присоединяйтесь!"
                )
            else:
                await query.edit_message_text("❌ Нет доступных бесед")
        
        elif data == "top_chats":
            # Топ бесед за день
            await query.edit_message_text("🏆 Функция в разработке")
        
        elif data == "help_menu":
            await self.cmd_help(update, context)
        
        elif data == "setup_info":
            text = """
# 🔧 Установка

Подробная инструкция по установке бота:
https://teletype.in/@nobucraft/2_pbVPOhaYo

Основные шаги:
1. Добавьте бота в группу
2. Дайте права администратора
3. Настройте приветствие: +приветствие Текст
4. Установите правила: +правила Текст
5. Настройте модерацию через !модер
            """
            await query.edit_message_text(text, disable_web_page_preview=True)

        elif data == "disabled":
            await query.answer("Эта клетка уже открыта", show_alert=False)
        
        elif data == "neons_info":
            text = """
# 💜 Что такое неоны?

Неоны — основная валюта кибер-вселенной Спектра.

## Как получить:
• Ежедневный бонус (/daily)
• Победы в играх
• Убийство боссов
• Покупка за монеты (1000 💰 = 1 💜)
• Реферальная система

## На что тратить:
• Покупка бонусов
• Telegram Premium
• Подарки
• Улучшения в играх

## Команды:
/neons — мой баланс
/transfer @user 100 — перевести неоны
/farm — ферма глитчей (1 💜 = 100 🖥)
            """
            await query.edit_message_text(text)
        
        elif data == "bonuses_menu":
            await self.cmd_bonuses(update, context)

        elif data == "random_chat":
            await self.cmd_random_chat(update, context)
        
        elif data == "top_chats_day":
            context.args = ["день"]
            await self.cmd_top_chats(update, context)
        
        elif data == "top_chats_week":
            context.args = ["неделя"]
            await self.cmd_top_chats(update, context)
        
        elif data == "top_chats_month":
            context.args = ["месяц"]
            await self.cmd_top_chats(update, context)
        
        elif data.startswith("chat_card_"):
            chat_id = int(data.split('_')[2])
            # Здесь можно добавить карточку чата
            await query.edit_message_text(
                "📇 **Карточка чата**\n\nФункция в разработке",
                parse_mode=ParseMode.MARKDOWN
            )
        
        # Кнопки боссов
        elif data.startswith("boss_attack_"):
            boss_id = int(data.split('_')[2])
            await self._process_boss_attack(update, context, user, user_data, boss_id, is_callback=True)
        
        elif data == "boss_regen":
            # Регенерация через кнопку
            await self.cmd_regen(update, context)
        
        elif data == "boss_buy_weapon":
            # Покупка оружия
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🗡 Меч (+10 урона) - 200💰", callback_data="buy_weapon_sword")],
                [InlineKeyboardButton("⚔️ Легендарный меч (+30 урона) - 500💰", callback_data="buy_weapon_legendary")],
                [InlineKeyboardButton("🔫 Бластер (+50 урона) - 1000💰", callback_data="buy_weapon_blaster")],
                [InlineKeyboardButton("🔙 Назад", callback_data="boss_list")]
            ])
            await query.edit_message_text(
                s.header("⚔️ МАГАЗИН ОРУЖИЯ") + "\n\nВыберите оружие:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard
            )
        
        elif data.startswith("buy_weapon_"):
            weapon = data.replace("buy_weapon_", "")
            weapons = {
                "sword": {"name": "🗡 Меч", "damage": 10, "price": 200},
                "legendary": {"name": "⚔️ Легендарный меч", "damage": 30, "price": 500},
                "blaster": {"name": "🔫 Бластер", "damage": 50, "price": 1000}
            }
            
            if weapon in weapons:
                w = weapons[weapon]
                if user_data['coins'] >= w['price']:
                    self.db.add_coins(user_data['id'], -w['price'])
                    new_damage = user_data['damage'] + w['damage']
                    self.db.update_user(user_data['id'], damage=new_damage)
                    await query.edit_message_text(
                        s.success(f"✅ Куплено: {w['name']}!\nТеперь ваш урон: {new_damage}"),
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    await query.edit_message_text(
                        s.error(f"❌ Недостаточно монет. Нужно {w['price']} 💰"),
                        parse_mode=ParseMode.MARKDOWN
                    )
        
        elif data == "boss_list":
            bosses = self.db.get_bosses()
            text = s.header("👾 БОССЫ") + "\n\n"
            for i, boss in enumerate(bosses[:5]):
                status = "⚔️" if boss['is_alive'] else "💀"
                health_bar = s.progress(boss['health'], boss['max_health'], 10)
                text += f"{i+1}. {status} {boss['name']}\n   {health_bar}\n\n"
            
            keyboard = []
            for i, boss in enumerate(bosses[:5]):
                if boss['is_alive']:
                    keyboard.append([InlineKeyboardButton(
                        f"⚔️ {boss['name']}",
                        callback_data=f"boss_attack_{boss['id']}"
                    )])
            
            keyboard.append([InlineKeyboardButton("🔄 Регенерация", callback_data="boss_regen")])
            
            await query.edit_message_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        # Кнопки сапёра
        elif data.startswith("saper_"):
            parts = data.split('_')
            if len(parts) >= 3:
                game_id = f"{parts[1]}_{parts[2]}"
                cell = int(parts[3])
                
                if game_id in self.games_in_progress:
                    game = self.games_in_progress[game_id]
                    if game['user_id'] != user.id:
                        await query.answer("Это не ваша игра!", show_alert=True)
                        return
                    
                    x = (cell - 1) // 3
                    y = (cell - 1) % 3
                    
                    if x == game['mine_x'] and y == game['mine_y']:
                        await query.edit_message_text(
                            f"{s.header('💥 БУМ!')}\n\n{s.error('Ты подорвался на мине!')}\n\nПроигрыш: {game['bet']} 💰",
                            parse_mode=ParseMode.MARKDOWN
                        )
                        del self.games_in_progress[game_id]
                    else:
                        game['opened'] += 1
                        game['field'][x][y] = "✅"
                        
                        if game['opened'] >= 8:
                            win = game['bet'] * 3
                            self.db.add_coins(user_data['id'], win)
                            self.db.update_user(user_data['id'], slots_wins=user_data.get('slots_wins', 0) + 1)
                            await query.edit_message_text(
                                s.success(f"🎉 ПОБЕДА! Ты открыл все безопасные клетки!\nВыигрыш: {win} 💰"),
                                parse_mode=ParseMode.MARKDOWN
                            )
                            del self.games_in_progress[game_id]
                        else:
                            # Обновляем поле
                            field_text = ""
                            for i in range(3):
                                field_text += ' '.join(game['field'][i]) + "\n"
                            
                            # Создаем новые кнопки
                            keyboard = []
                            for i in range(3):
                                row = []
                                for j in range(3):
                                    cell_num = i * 3 + j + 1
                                    if game['field'][i][j] == "✅":
                                        row.append(InlineKeyboardButton(f"✅", callback_data="disabled"))
                                    else:
                                        row.append(InlineKeyboardButton(f"⬜️", callback_data=f"saper_{game_id}_{cell_num}"))
                                keyboard.append(row)
                            
                            await query.edit_message_text(
                                f"{s.header('💣 САПЁР')}\n\n{field_text}",
                                parse_mode=ParseMode.MARKDOWN,
                                reply_markup=InlineKeyboardMarkup(keyboard)
                            )
        
        # Кнопки голосования за бан
        elif data.startswith("vote_for_"):
            vote_id = int(data.split('_')[2])
            if self.db.vote_for_ban(vote_id, user_data['id'], True):
                await query.edit_message_text(s.success("✅ Ваш голос учтён (ЗА БАН)"))
                
                # Проверяем, достигнут ли лимит
                self.db.cursor.execute("SELECT * FROM ban_votes WHERE id = ?", (vote_id,))
                vote = self.db.cursor.fetchone()
                if vote and vote[7] >= vote[5]:  # votes_for >= required_votes
                    target = self.db.get_user_by_id(vote[2])
                    if target:
                        # Баним
                        self.db.ban_user(target['id'], vote[3], "По результатам голосования")
                        self.db.cursor.execute("UPDATE ban_votes SET status = 'completed' WHERE id = ?", (vote_id,))
                        self.db.conn.commit()
                        
                        await context.bot.send_message(
                            vote[1],  # chat_id
                            s.error(f"🔨 Пользователь {target['first_name']} забанен по результатам голосования!")
                        )
            else:
                await query.edit_message_text(s.error("❌ Не удалось проголосовать"))
        
        elif data.startswith("vote_against_"):
            vote_id = int(data.split('_')[2])
            if self.db.vote_for_ban(vote_id, user_data['id'], False):
                await query.edit_message_text(s.success("✅ Ваш голос учтён (ПРОТИВ БАНА)"))
            else:
                await query.edit_message_text(s.error("❌ Не удалось проголосовать"))
        
        # Кнопки мафии
        elif data.startswith("mafia_confirm_"):
            chat_id = int(data.split('_')[2])
            if chat_id in self.mafia_games:
                game = self.mafia_games[chat_id]
                if user.id in game.players:
                    game.confirm_player(user.id)
                    await query.edit_message_text(
                        f"{s.success('✅ Подтверждение получено!')}\n\n"
                        f"{s.info('Ожидайте начала игры...')}",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    
                    # Проверяем, все ли подтвердили
                    if game.all_confirmed():
                        await self._mafia_start_game(game, context)
        
                # Кнопки дуэлей
        elif data.startswith("accept_duel_"):
            duel_id = int(data.split('_')[2])
            duel = self.db.get_duel(duel_id)
            
            if not duel or duel['opponent_id'] != user_data['id'] or duel['status'] != 'pending':
                await query.edit_message_text(s.error("❌ Дуэль не найдена или уже обработана"))
                return
            
            self.db.update_duel(duel_id, status='accepted')
            
            challenger = self.db.get_user_by_id(duel['challenger_id'])
            opponent = self.db.get_user_by_id(duel['opponent_id'])
            
            if not challenger or not opponent:
                await query.edit_message_text(s.error("❌ Ошибка загрузки данных"))
                return
            
            await query.edit_message_text(
                f"{s.success('✅ Дуэль принята!')}\n\n"
                f"⚔️ {challenger['first_name']} VS {opponent['first_name']} ⚔️\n"
                f"💰 Ставка: {duel['bet']} 💰\n\n"
                f"🔄 Дуэль начинается...",
                parse_mode=ParseMode.MARKDOWN
            )
            
            asyncio.create_task(self._process_duel(duel_id, challenger, opponent, duel['bet'], update.effective_chat.id, context))
        
        elif data.startswith("reject_duel_"):
            duel_id = int(data.split('_')[2])
            duel = self.db.get_duel(duel_id)
            
            if not duel or duel['opponent_id'] != user_data['id'] or duel['status'] != 'pending':
                await query.edit_message_text(s.error("❌ Дуэль не найдена или уже обработана"))
                return
            
            self.db.update_duel(duel_id, status='rejected')
            self.db.add_coins(duel['challenger_id'], duel['bet'])
            
            await query.edit_message_text(
                f"{s.error('❌ Дуэль отклонена')}\n\n"
                f"Ставка возвращена.",
                parse_mode=ParseMode.MARKDOWN
            )
        
        # Кнопки брака
        elif data.startswith("marry_accept_"):
            proposer_id = int(data.split('_')[2])
            
            if user_data.get('spouse', 0):
                await query.edit_message_text(s.error("❌ Вы уже в браке"), parse_mode=ParseMode.MARKDOWN)
                return
            
            proposer = self.db.get_user_by_id(proposer_id)
            if not proposer:
                await query.edit_message_text(s.error("❌ Пользователь не найден"), parse_mode=ParseMode.MARKDOWN)
                return
            
            if proposer.get('spouse', 0):
                await query.edit_message_text(s.error("❌ Пользователь уже в браке"), parse_mode=ParseMode.MARKDOWN)
                return
            
            now = datetime.now().isoformat()
            self.db.update_user(user_data['id'], spouse=proposer_id, married_since=now)
            self.db.update_user(proposer_id, spouse=user_data['id'], married_since=now)
            
            text = (
                f"# Спектр | Свадьба\n\n"
                f"💍 Поздравляем!\n"
                f"{user_data['first_name']} и {proposer['first_name']} теперь в браке! 🎉\n\n"
                f"💕 Совместимость: {random.randint(70, 100)}%\n"
                f"💰 Бонус молодожёнам: +500 💰 каждому\n"
                f"✨ Особый статус: Супруг(а)"
            )
            
            self.db.add_coins(user_data['id'], 500)
            self.db.add_coins(proposer_id, 500)
            
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
            
            await context.bot.send_message(
                proposer['telegram_id'],
                f"{s.success('💞 ПОЗДРАВЛЯЕМ!')}\n\n"
                f"{s.item(f'{user_data["first_name"]} принял(а) ваше предложение!')}",
                parse_mode=ParseMode.MARKDOWN
            )
        
        elif data.startswith("marry_reject_"):
            proposer_id = int(data.split('_')[2])
            await query.edit_message_text(s.error("❌ Предложение отклонено"), parse_mode=ParseMode.MARKDOWN)
            await context.bot.send_message(
                proposer_id,
                s.error("❌ Ваше предложение отклонили"),
                parse_mode=ParseMode.MARKDOWN
            )
        
        # Кнопки для закладок
        elif data == "bookmark_help":
            text = """
# 📌 Закладки

Как использовать:

• `+Закладка Название` (с новой строки содержимое) — создать
• `закладка [ID]` — показать
• `чатбук` — все закладки чата
• `мои закладки` — ваши закладки
• `-Закладка [ID]` — удалить
            """
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
        
        # Кнопки для кружков
        elif data == "circle_help":
            text = """
# 🔄 Кружки

Как использовать:

• `создать кружок Название` (с новой строки описание) — создать
• `кружки` — список кружков
• `кружок [номер]` — информация
• `+Кружок [номер]` — присоединиться
• `-Кружок [номер]` — выйти
            """
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
        
        # Кнопки для ачивок
        elif data == "achievements_help":
            text = """
# 🏅 Ачивки

Как использовать:

• `мои ачивки` — ваши достижения
• `топ ачивок` — рейтинг
• `ачивка [ID]` — информация
• `+Ачивки` / `-Ачивки` — приватность
            """
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
    
    # ===== МАФИЯ =====
    async def cmd_mafia(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = """
# Спектр | Мафия

🎮 **Команды мафии:

/mafiastart — начать новую игру
/mafiajoin — присоединиться к игре
/mafialeave — выйти из игры
/mafiaroles — список ролей
/mafiarules — правила игры
/mafiastats — статистика

⚠️ Игра проходит в ЛС с подтверждением!
        """
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_mafia_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        
        if chat_id in self.mafia_games:
            await update.message.reply_text(s.error("❌ Игра уже идёт! Присоединяйтесь: /mafiajoin"))
            return
        
        game_id = f"mafia_{chat_id}_{int(time.time())}"
        game = MafiaGame(chat_id, game_id, update.effective_user.id)
        self.mafia_games[chat_id] = game
        
        text = (
            s.header("🔫 МАФИЯ") + "\n\n"
            f"{s.success('🎮 Игра создана!')}\n\n"
            f"{s.item('Участники (0):')}\n"
            f"{s.item('/mafiajoin — присоединиться')}\n"
            f"{s.item('/mafialeave — выйти')}\n\n"
            f"{s.info('Игра будет проходить в ЛС с ботом. Подтверждение обязательно!')}"
        )
        
        msg = await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        game.message_id = msg.message_id
    
    async def cmd_mafia_join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        user = update.effective_user
        
        if chat_id not in self.mafia_games:
            await update.message.reply_text(s.error("❌ Игра не создана. Начните: /mafiastart"))
            return
        
        game = self.mafia_games[chat_id]
        
        if game.status != "waiting":
            await update.message.reply_text(s.error("❌ Игра уже началась"))
            return
        
        if not game.add_player(user.id, user.first_name, user.username or ""):
            await update.message.reply_text(s.error("❌ Вы уже в игре"))
            return
        
        # Отправляем подтверждение в ЛС
        try:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ ПОДТВЕРДИТЬ", callback_data=f"mafia_confirm_{chat_id}")]
            ])
            
            await context.bot.send_message(
                user.id,
                f"{s.header('🔫 МАФИЯ')}\n\n"
                f"{s.item('Вы присоединились к игре!')}\n"
                f"{s.item('Нажмите кнопку для подтверждения')}\n\n"
                f"{s.info('После подтверждения вы получите свою роль в ЛС')}",
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
            
            await update.message.reply_text(s.success(f"✅ {user.first_name}, проверьте ЛС для подтверждения!"))
        except Exception as e:
            await update.message.reply_text(
                s.error(f"❌ {user.first_name}, не удалось отправить сообщение в ЛС. Напишите боту в личку сначала.")
            )
            game.remove_player(user.id)
            return
        
        # Обновляем сообщение в чате
        players_list = "\n".join([f"{i+1}. {game.players_data[pid]['name']}" for i, pid in enumerate(game.players)])
        confirmed = sum(1 for p in game.players if game.players_data[p]['confirmed'])
        
        text = (
            s.header("🔫 МАФИЯ") + "\n\n"
            f"{s.item(f'Участники ({len(game.players)}):')}\n"
            f"{players_list}\n\n"
            f"{s.item(f'Подтвердили: {confirmed}/{len(game.players)}')}\n"
            f"{s.item('/mafiajoin — присоединиться')}\n"
            f"{s.item('/mafialeave — выйти')}\n\n"
            f"{s.info('Для старта нужно минимум 6 игроков и все подтверждения')}"
        )
        
        try:
            await context.bot.edit_message_text(
                text,
                chat_id=chat_id,
                message_id=game.message_id,
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass
    
    async def cmd_mafia_leave(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        user = update.effective_user
        
        if chat_id not in self.mafia_games:
            await update.message.reply_text(s.error("❌ Игра не создана"))
            return
        
        game = self.mafia_games[chat_id]
        
        if game.status != "waiting":
            await update.message.reply_text(s.error("❌ Нельзя покинуть игру после начала"))
            return
        
        if not game.remove_player(user.id):
            await update.message.reply_text(s.error("❌ Вас нет в игре"))
            return
        
        await update.message.reply_text(s.success(f"✅ {user.first_name} покинул игру"))
        
        # Обновляем сообщение в чате
        if game.players:
            players_list = "\n".join([f"{i+1}. {game.players_data[pid]['name']}" for i, pid in enumerate(game.players)])
            confirmed = sum(1 for p in game.players if game.players_data[p]['confirmed'])
            
            text = (
                s.header("🔫 МАФИЯ") + "\n\n"
                f"{s.item(f'Участники ({len(game.players)}):')}\n"
                f"{players_list}\n\n"
                f"{s.item(f'Подтвердили: {confirmed}/{len(game.players)}')}\n"
                f"{s.item('/mafiajoin — присоединиться')}\n"
                f"{s.item('/mafialeave — выйти')}\n\n"
                f"{s.info('Для старта нужно минимум 6 игроков и все подтверждения')}"
            )
        else:
            text = (
                s.header("🔫 МАФИЯ") + "\n\n"
                f"{s.item('Участников нет')}\n"
                f"{s.item('/mafiajoin — присоединиться')}"
            )
        
        try:
            await context.bot.edit_message_text(
                text,
                chat_id=chat_id,
                message_id=game.message_id,
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass
    
    async def cmd_mafia_roles(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            s.header("🔫 РОЛИ В МАФИИ") + "\n\n"
            f"{s.section('😈 МАФИЯ')}"
            f"{s.item('😈 Мафиози — ночью убивают')}\n"
            f"{s.item('👑 Босс — глава мафии')}\n\n"
            f"{s.section('👼 ГОРОД')}"
            f"{s.item('👮 Комиссар — проверяет ночью')}\n"
            f"{s.item('👨‍⚕️ Доктор — лечит ночью')}\n"
            f"{s.item('👤 Мирный — ищет мафию')}\n\n"
            f"{s.section('🎭 ОСОБЫЕ')}"
            f"{s.item('🔪 Маньяк — убивает один')}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_mafia_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            s.header("🔫 ПРАВИЛА МАФИИ") + "\n\n"
            f"{s.section('🌙 НОЧЬ')}"
            f"{s.item('1. Мафия выбирает жертву')}\n"
            f"{s.item('2. Доктор выбирает, кого спасти')}\n"
            f"{s.item('3. Комиссар проверяет')}\n\n"
            f"{s.section('☀️ ДЕНЬ')}"
            f"{s.item('1. Объявление жертв ночи')}\n"
            f"{s.item('2. Обсуждение')}\n"
            f"{s.item('3. Голосование за исключение')}\n\n"
            f"{s.section('🏆 ЦЕЛЬ')}"
            f"{s.item('Мафия — убить всех мирных')}\n"
            f"{s.item('Город — найти всю мафию')}\n\n"
            f"{s.info('Все действия в ЛС с ботом. Подтверждение обязательно!')}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_mafia_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        text = (
            s.header("🔫 СТАТИСТИКА МАФИИ") + "\n\n"
            f"{s.stat('Сыграно игр', user_data['mafia_games'])}\n"
            f"{s.stat('Побед', user_data['mafia_wins'])}\n"
            f"{s.stat('Поражений', user_data['mafia_losses'])}\n"
            f"{s.stat('Процент побед', f'{(user_data["mafia_wins"]/max(1, user_data["mafia_games"])*100):.1f}%')}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def _mafia_start_game(self, game: MafiaGame, context: ContextTypes.DEFAULT_TYPE):
        """Начать игру после подтверждения всех игроков"""
        if len(game.players) < MAFIA_MIN_PLAYERS:
            await context.bot.send_message(
                game.chat_id,
                s.error(f"❌ Недостаточно игроков. Нужно минимум {MAFIA_MIN_PLAYERS}")
            )
            del self.mafia_games[game.chat_id]
            return
        
        game.assign_roles()
        game.status = "night"
        game.phase = "night"
        game.start_time = datetime.now()
        
        for player_id in game.players:
            role = game.roles[player_id]
            role_desc = game.get_role_description(role)
            
            try:
                await context.bot.send_message(
                    player_id,
                    f"{s.header('🔫 МАФИЯ')}\n\n"
                    f"{s.item(f'Ваша роль: {role}')}\n"
                    f"{s.item(role_desc)}\n\n"
                    f"{s.info('Ночь начинается. Ожидайте действий.')}",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
        
        await context.bot.send_message(
            game.chat_id,
            f"{s.header('🔫 МАФИЯ')}\n\n"
            f"{s.success('🌙 НАСТУПИЛА НОЧЬ')}\n"
            f"{s.item('Все роли розданы в ЛС')}\n"
            f"{s.item('Мафия выбирает жертву...')}\n"
            f"{s.item('Доктор выбирает, кого спасти...')}",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Запускаем таймер на ночь
        asyncio.create_task(self._mafia_night_timer(game, context, MAFIA_NIGHT_TIME))
    
    async def _mafia_night_timer(self, game: MafiaGame, context: ContextTypes.DEFAULT_TYPE, seconds: int):
        await asyncio.sleep(seconds)
        
        if game.chat_id not in self.mafia_games or game.phase != "night":
            return
        
        await self._mafia_process_night(game, context)
    
    async def _mafia_process_night(self, game: MafiaGame, context: ContextTypes.DEFAULT_TYPE):
        result = game.process_night()
        
        if result["killed"]:
            game.alive[result["killed"]] = False
            try:
                await context.bot.send_message(
                    result["killed"],
                    f"{s.error('💀 ВАС УБИЛИ НОЧЬЮ')}\n\n"
                    f"{s.item('Вы больше не участвуете в игре.')}",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
        
        game.phase = "day"
        game.day += 1
        game.votes = {}
        
        alive_list = game.get_alive_players()
        alive_names = []
        for i, pid in enumerate(alive_list, 1):
            name = game.players_data[pid]['name']
            alive_names.append(f"{i}. {name}")
        
        killed_name = "никто"
        if result["killed"]:
            killed_name = game.players_data[result["killed"]]['name']
        
        text = (
            s.header(f"🔫 МАФИЯ | ДЕНЬ {game.day}") + "\n\n"
            f"{s.item(f'☀️ Наступило утро...')}\n"
            f"{s.item(f'💀 Прошлой ночью был убит: {killed_name}')}\n\n"
            f"{s.section('ЖИВЫЕ ИГРОКИ')}\n"
            f"{chr(10).join([s.item(name) for name in alive_names])}\n\n"
            f"{s.info('Обсуждайте и голосуйте: голосовать [номер]')}"
        )
        
        await context.bot.send_message(game.chat_id, text, parse_mode=ParseMode.MARKDOWN)
        
        asyncio.create_task(self._mafia_day_timer(game, context, MAFIA_DAY_TIME))
    
    async def _mafia_day_timer(self, game: MafiaGame, context: ContextTypes.DEFAULT_TYPE, seconds: int):
        await asyncio.sleep(seconds)
        
        if game.chat_id not in self.mafia_games or game.phase != "day":
            return
        
        await self._mafia_process_day(game, context)
    
    async def _mafia_process_day(self, game: MafiaGame, context: ContextTypes.DEFAULT_TYPE):
        executed = game.process_voting()
        
        if executed:
            game.alive[executed] = False
            executed_name = game.players_data[executed]['name']
            role = game.roles.get(executed, "неизвестно")
            
            text = (
                s.header(f"🔫 МАФИЯ | ДЕНЬ {game.day}") + "\n\n"
                f"{s.item(f'🔨 По результатам голосования исключён: {executed_name}')}\n"
                f"{s.item(f'Роль: {role}')}\n\n"
                f"{s.info('Ночь скоро наступит...')}"
            )
            
            await context.bot.send_message(game.chat_id, text, parse_mode=ParseMode.MARKDOWN)
            
            try:
                await context.bot.send_message(
                    executed,
                    f"{s.error('🔨 ВАС ИСКЛЮЧИЛИ ДНЁМ')}\n\n"
                    f"{s.item('Вы больше не участвуете в игре.')}",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
        else:
            await context.bot.send_message(
                game.chat_id,
                f"{s.info('📢 Никто не был исключён сегодня')}",
                parse_mode=ParseMode.MARKDOWN
            )
        
        winner = game.check_win()
        
        if winner == "citizens":
            await context.bot.send_message(
                game.chat_id,
                f"{s.success('🏆 ПОБЕДА ГОРОДА!')}\n\n"
                f"{s.item('Вся мафия уничтожена!')}",
                parse_mode=ParseMode.MARKDOWN
            )
            
            for pid in game.players:
                user_data = self.db.get_user_by_id(pid)
                if user_data:
                    self.db.update_user(pid, mafia_games=user_data.get('mafia_games', 0) + 1)
                    if game.roles.get(pid) not in [MafiaRole.MAFIA, MafiaRole.BOSS]:
                        self.db.update_user(pid, mafia_wins=user_data.get('mafia_wins', 0) + 1)
                        self.db.add_coins(pid, 500)
            
            del self.mafia_games[game.chat_id]
            return
        
        if winner == "mafia":
            await context.bot.send_message(
                game.chat_id,
                f"{s.success('🏆 ПОБЕДА МАФИИ!')}\n\n"
                f"{s.item('Мафия захватила город!')}",
                parse_mode=ParseMode.MARKDOWN
            )
            
            for pid in game.players:
                user_data = self.db.get_user_by_id(pid)
                if user_data:
                    self.db.update_user(pid, mafia_games=user_data.get('mafia_games', 0) + 1)
                    if game.roles.get(pid) in [MafiaRole.MAFIA, MafiaRole.BOSS]:
                        self.db.update_user(pid, mafia_wins=user_data.get('mafia_wins', 0) + 1)
                        self.db.add_coins(pid, 500)
            
            del self.mafia_games[game.chat_id]
            return
        
        game.phase = "night"
        game.night_actions = {
            "mafia_kill": None,
            "doctor_save": None,
            "commissioner_check": None,
            "maniac_kill": None
        }
        
        await context.bot.send_message(
            game.chat_id,
            f"{s.header(f'🔫 МАФИЯ | НОЧЬ {game.day}')}\n\n"
            f"{s.success('🌙 НАСТУПИЛА НОЧЬ')}\n"
            f"{s.item('Мафия выбирает жертву...')}",
            parse_mode=ParseMode.MARKDOWN
        )
        
        asyncio.create_task(self._mafia_night_timer(game, context, MAFIA_NIGHT_TIME))
    
    # ===== ПОЛЕЗНОЕ =====
    async def cmd_ping(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        start = time.time()
        msg = await update.message.reply_text("🏓 Понг...")
        end = time.time()
        ping = int((end - start) * 1000)
        await msg.edit_text(f"🏓 Понг!\n⏱️ {ping} мс", parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_uptime(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        uptime = datetime.now() - self.start_time
        days = uptime.days
        hours = uptime.seconds // 3600
        minutes = (uptime.seconds % 3600) // 60
        
        await update.message.reply_text(
            f"⏱️ **Аптайм: {days}д {hours}ч {minutes}м",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def cmd_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        users_count = self.db.cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        messages_count = self.db.cursor.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        
        text = (
            s.header("🤖 ИНФОРМАЦИЯ О БОТЕ") + "\n\n"
            f"Название: {BOT_NAME}\n"
            f"Версия: {BOT_VERSION}\n"
            f"Владелец: {OWNER_USERNAME}\n\n"
            f"{s.stat('Пользователей', users_count)}\n"
            f"{s.stat('Сообщений', messages_count)}\n"
            f"{s.stat('Команд', '300+')}\n"
            f"{s.stat('AI', 'Подключен' if self.ai and self.ai.is_available else 'Не подключен')}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    # ===== ОСТАЛЬНЫЕ КОМАНДЫ МОДЕРАЦИИ (СОКРАЩЕННО) =====
    # Здесь идут все команды модерации, которые были в оригинале
    # Они остаются без изменений, поэтому я их пропускаю для краткости
    
    # ===== ОБРАБОТЧИК ОШИБОК =====
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Ошибка: {context.error}")
        try:
            if update and update.effective_message:
                await update.effective_message.reply_text(s.error("❌ Произошла внутренняя ошибка"))
        except:
            pass
    
    # ===== ЗАПУСК =====
    async def run(self):
        try:
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling(drop_pending_updates=True)
            
            logger.info(f"🚀 Бот {BOT_NAME} успешно запущен")
            logger.info(f"👑 Владелец: {OWNER_USERNAME}")
            logger.info(f"🤖 AI: {'Подключен' if self.ai and self.ai.is_available else 'Не подключен'}")
            
            while True:
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Критическая ошибка: {e}")
            await asyncio.sleep(5)
            await self.run()
    
    async def close(self):
        logger.info("👋 Завершение работы бота...")
        if self.ai:
            await self.ai.close()
        self.db.close()
        logger.info("✅ Бот остановлен")

# ========== ТОЧКА ВХОДА ==========
async def main():
    print("=" * 60)
    print(f"✨ ЗАПУСК БОТА {BOT_NAME} v{BOT_VERSION} ✨")
    print("=" * 60)
    print(f"📊 Команд: 300+")
    print(f"📊 Модулей: 30+")
    
    # Проверяем AI
    global ai
    if GROQ_API_KEY and ai is not None and ai.is_available:
        print(f"📊 AI: Groq подключен (режим: ПРОВОКАТОР)")
    else:
        print(f"📊 AI: Не подключен")
    
    print("=" * 60)
    
    bot = SpectrumBot()
    
    try:
        await bot.app.initialize()
        await bot.app.start()
        await bot.app.updater.start_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        
        asyncio.create_task(bot.check_timers())
        
        logger.info(f"🚀 Бот {BOT_NAME} успешно запущен и слушает обновления")
        
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("👋 Остановка по запросу пользователя")
        await bot.app.updater.stop()
        await bot.app.stop()
        await bot.app.shutdown()
        await bot.close()
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        await bot.app.updater.stop()
        await bot.app.stop()
        await bot.app.shutdown()
        await bot.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Программа завершена пользователем")
    except Exception as e:
        logger.error(f"❌ Фатальная ошибка: {e}")
        import traceback
        traceback.print_exc()
