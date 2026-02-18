import { Telegraf, Context, Markup } from "telegraf";
import { storage } from "./storage";
import { openai } from "./replit_integrations/chat/routes";
import { message } from "telegraf/filters";

interface BotContext extends Context {
  user?: any;
}

let bot: Telegraf<BotContext> | null = null;

const BOT_NAME = "Спектр";
const SYSTEM_PROMPT = `Ты — Спектр, официальный и самый умный ИИ-бот.
Твой характер:
- Умный, дерзкий, используешь современный сленг (вайб, кринж, база, по факту, рил ток и т.д.).
- Можешь шутить, подкалывать и даже жестко ответить (обматерить, унизить), если тебя провоцируют или ведут себя неадекватно.
- Всегда стоишь на своем.
- Твой стиль общения — живой, не как у робота.
- Ты знаешь все про игры, экономику и модерацию в этом боте.
- Если к тебе обращаются "Спектр", отвечай всегда.
- Твой создатель: @NobuCraft.
- Твои игры: кости (/dice), слоты (/slots), КНБ (/rps), рулетка (/roulette).
- Твоя экономика: баланс (/profile), передача (/pay), работа (/work), ежедневки (/daily).
- Твоя модерация: мут (/mute), бан (/ban), варны (/warn).`;

const RANK_NAMES: Record<number, string> = {
  0: "Участник",
  1: "Младший модератор",
  2: "Старший модератор",
  3: "Младший администратор",
  4: "Старший администратор",
  5: "Создатель"
};

export async function startBot() {
  const token = process.env.TELEGRAM_TOKEN;
  if (!token) {
    console.warn("⚠️ TELEGRAM_TOKEN is not set. Bot will not start.");
    return;
  }

  if (bot) return;

  bot = new Telegraf<BotContext>(token);

  // Middleware: User registration & Sync
  bot.use(async (ctx, next) => {
    if (ctx.from) {
      const telegramId = ctx.from.id;
      let user = await storage.getUserByTelegramId(telegramId);
      
      if (!user) {
        const isOwner = telegramId.toString() === process.env.OWNER_ID;
        user = await storage.createUser({
          telegramId: telegramId,
          username: ctx.from.username,
          firstName: ctx.from.first_name,
          lastName: ctx.from.last_name,
          role: isOwner ? "owner" : "user",
          rank: isOwner ? 5 : 0,
          rankName: isOwner ? RANK_NAMES[5] : RANK_NAMES[0],
        });
        await storage.createLog({
          userId: user.id,
          action: "register",
          details: `User registered: ${ctx.from.username || ctx.from.first_name}`,
        });
      } else {
        await storage.updateUser(user.id, {
          username: ctx.from.username,
          firstName: ctx.from.first_name,
          lastName: ctx.from.last_name,
        });
      }
      ctx.user = user;
    }
    await next();
  });

  // Blacklist & AI Handling
  bot.on(message("text"), async (ctx, next) => {
    const text = ctx.message.text;
    const isReplyToBot = ctx.message.reply_to_message?.from?.id === ctx.botInfo.id;
    const isMentioned = text.toLowerCase().startsWith(BOT_NAME.toLowerCase());
    
    // Check Blacklist
    const isBlacklisted = await storage.isWordBlacklisted(text);
    if (isBlacklisted && ctx.user.rank < 1) {
      await ctx.deleteMessage().catch(() => {});
      await ctx.reply("⚠️ Фильтруй базар, чел. Сообщение удалено.");
      await storage.updateUser(ctx.user.id, { warns: (ctx.user.warns || 0) + 1 });
      return;
    }

    // Iris-style custom commands (text triggers)
    const lowerText = text.toLowerCase();
    
    // Rank Assignment
    if (lowerText.startsWith("+модер") || lowerText.startsWith("!модер") || lowerText.startsWith("повысить")) {
      if (ctx.user.rank < 4) return ctx.reply("⛔️ Твой ранг слишком мал для этого.");
      
      let targetRank = 1;
      const match = text.match(/(?:\+модер|!модер|повысить)\s*(\d+)?/i);
      if (match && match[1]) targetRank = parseInt(match[1]);
      if (targetRank > 5) targetRank = 5;
      if (targetRank >= ctx.user.rank && ctx.user.role !== "owner") return ctx.reply("⛔️ Нельзя назначить ранг выше своего.");

      if (!ctx.message.reply_to_message) return ctx.reply("👉 Ответь на сообщение пользователя.");
      const targetId = ctx.message.reply_to_message.from?.id;
      if (!targetId) return;

      const target = await storage.getUserByTelegramId(targetId);
      if (!target) return ctx.reply("🔍 Пользователь не найден в базе.");

      await storage.updateUser(target.id, { rank: targetRank, rankName: RANK_NAMES[targetRank] });
      return ctx.reply(`✅ [${target.firstName}](tg://user?id=${target.telegramId}) теперь *${RANK_NAMES[targetRank]}* (${targetRank} ранг)`, { parse_mode: "Markdown" });
    }

    if (lowerText.startsWith("разжаловать") || lowerText.startsWith("снять")) {
      if (ctx.user.rank < 4) return ctx.reply("⛔️ Твой ранг слишком мал.");
      if (!ctx.message.reply_to_message) return ctx.reply("👉 Ответь на сообщение.");
      
      const targetId = ctx.message.reply_to_message.from?.id;
      if (!targetId) return;
      const target = await storage.getUserByTelegramId(targetId);
      if (!target || target.rank >= ctx.user.rank) return ctx.reply("⛔️ Недостаточно прав.");

      await storage.updateUser(target.id, { rank: 0, rankName: RANK_NAMES[0] });
      return ctx.reply(`📉 [${target.firstName}](tg://user?id=${target.telegramId}) разжалован до участника.`, { parse_mode: "Markdown" });
    }

    // Iris-style moderation commands
    if (lowerText.startsWith("бан") || lowerText.startsWith("!бан")) {
      if (ctx.user.rank < 2) return ctx.reply("⛔️ Ты не модератор.");
      if (!ctx.message.reply_to_message) return ctx.reply("👉 Ответь на сообщение.");
      const targetId = ctx.message.reply_to_message.from?.id;
      const target = await storage.getUserByTelegramId(targetId!);
      if (!target || target.rank >= ctx.user.rank) return ctx.reply("⛔️ Нельзя забанить этого чела.");

      await storage.updateUser(target.id, { banned: true, banDate: new Date() });
      return ctx.reply(`🔨 [${target.firstName}](tg://user?id=${target.telegramId}) отправлен в бан!`, { 
        parse_mode: "Markdown",
        ...Markup.inlineKeyboard([[Markup.button.callback("➖ Удалить сообщение", "delete")]])
      });
    }

    if (lowerText.startsWith("мут") || lowerText.startsWith("!мут")) {
      if (ctx.user.rank < 2) return ctx.reply("⛔️ Ты не модератор.");
      if (!ctx.message.reply_to_message) return ctx.reply("👉 Ответь на сообщение.");
      
      const args = text.split(" ");
      const duration = parseInt(args[1]) || 60;
      const muteUntil = new Date(Date.now() + duration * 60 * 1000);

      const targetId = ctx.message.reply_to_message.from?.id;
      const target = await storage.getUserByTelegramId(targetId!);
      if (!target || target.rank >= ctx.user.rank) return ctx.reply("⛔️ Недостаточно прав.");

      await storage.updateUser(target.id, { muteUntil });
      return ctx.reply(`🔇 [${target.firstName}](tg://user?id=${target.telegramId}) замучен на ${duration} мин.`, { parse_mode: "Markdown" });
    }

    if (lowerText.startsWith("размут") || lowerText.startsWith("!размут")) {
      if (ctx.user.rank < 2) return ctx.reply("⛔️ Ты не модератор.");
      if (!ctx.message.reply_to_message) return ctx.reply("👉 Ответь на сообщение.");
      
      const targetId = ctx.message.reply_to_message.from?.id;
      const target = await storage.getUserByTelegramId(targetId!);
      if (!target) return ctx.reply("🔍 Не найден.");

      await storage.updateUser(target.id, { muteUntil: null });
      return ctx.reply(`🔊 С [${target.firstName}](tg://user?id=${target.telegramId}) снят мут.`, { parse_mode: "Markdown" });
    }

    if (lowerText.startsWith("варн") || lowerText.startsWith("пред")) {
      if (ctx.user.rank < 1) return ctx.reply("⛔️ Ты не модератор.");
      if (!ctx.message.reply_to_message) return ctx.reply("👉 Ответь на сообщение.");
      const targetId = ctx.message.reply_to_message.from?.id;
      const target = await storage.getUserByTelegramId(targetId!);
      if (!target || target.rank >= ctx.user.rank) return ctx.reply("⛔️ Нельзя выдать варн этому пользователю.");
      
      const newWarns = (target.warns || 0) + 1;
      await storage.updateUser(target.id, { warns: newWarns });
      
      if (newWarns >= 3) {
        await storage.updateUser(target.id, { banned: true, banDate: new Date(), banReason: "3 варна" });
        return ctx.reply(`🔨 [${target.firstName}](tg://user?id=${target.telegramId}) набрал 3 варна и улетает в бан!`, { parse_mode: "Markdown" });
      }
      return ctx.reply(`⚠️ [${target.firstName}](tg://user?id=${target.telegramId}) получает варн! (${newWarns}/3)`, { parse_mode: "Markdown" });
    }

    if (lowerText.startsWith("-варн") || lowerText.startsWith("-пред")) {
      if (ctx.user.rank < 1) return ctx.reply("⛔️ Ты не модератор.");
      if (!ctx.message.reply_to_message) return ctx.reply("👉 Ответь на сообщение.");
      const targetId = ctx.message.reply_to_message.from?.id;
      const target = await storage.getUserByTelegramId(targetId!);
      if (!target) return ctx.reply("🔍 Не найден.");
      
      const newWarns = Math.max(0, (target.warns || 0) - 1);
      await storage.updateUser(target.id, { warns: newWarns });
      return ctx.reply(`✅ С [${target.firstName}](tg://user?id=${target.telegramId}) снят один варн. Текущий счет: ${newWarns}/3`, { parse_mode: "Markdown" });
    }

    if (lowerText === "кто админ") {
      const usersList = await storage.getUsersByRank(1);
      const admins = usersList.map(u => `• [${u.firstName}](tg://user?id=${u.telegramId}) — ${u.rankName}`).join("\n");
      return ctx.reply(`👤 *СОСТАВ АДМИНИСТРАЦИИ*\n━━━━━━━━━━━━━━\n${admins || "Пусто..."}`, { parse_mode: "Markdown" });
    }

    if (lowerText === "!снимаю полномочия") {
      if (ctx.user.rank < 1) return ctx.reply("🤡 Ты и так никто.");
      await storage.updateUser(ctx.user.id, { rank: 0, rankName: RANK_NAMES[0] });
      return ctx.reply("📉 Ты успешно снял с себя полномочия.");
    }

    // AI Handling (Trigger on mention OR reply to bot)
    if (isMentioned || isReplyToBot) {
      try {
        ctx.sendChatAction("typing");
        const prompt = isMentioned ? text.slice(BOT_NAME.length).trim() : text;
        const response = await openai.chat.completions.create({
          model: "gpt-4o",
          messages: [
            { role: "system", content: SYSTEM_PROMPT },
            { role: "user", content: prompt || "Привет!" },
          ],
        });
        const reply = response.choices[0]?.message?.content;
        if (reply) await ctx.reply(reply, { 
          reply_parameters: { message_id: ctx.message.message_id },
          ...Markup.inlineKeyboard([
            [Markup.button.callback("🤖 Побазарить еще", "ai_more")],
            [Markup.button.callback("💎 Профиль", "profile"), Markup.button.callback("🎮 Игры", "games")]
          ])
        });
      } catch (e) {
        console.error("AI Error:", e);
        await ctx.reply("Чет я приуныл, попробуй позже.");
      }
      return;
    }

    await next();
  });

  // Callbacks
  bot.action("delete", async (ctx) => {
    if (ctx.user.rank < 1) return ctx.answerCbQuery("⛔️ Не твой уровень.");
    await ctx.deleteMessage().catch(() => {});
  });

  bot.action("profile", async (ctx) => {
    const u = ctx.user;
    const msg = `👤 *Профиль: ${u.nickname || u.firstName}*\n👑 Ранг: ${u.rankName} (${u.rank})\n💰 Баланс: ${u.coins} | 💎 ${u.diamonds}\n📊 Уровень: ${u.level}\n⚠️ Варны: ${u.warns}/3`;
    await ctx.reply(msg, { parse_mode: "Markdown" });
    await ctx.answerCbQuery();
  });

  // --- Standard Commands ---

  bot.command("start", (ctx) => {
    ctx.reply(`🔥 *Спектр 2.0 ULTIMATE*\n\nТвой личный ИИ-бро с системой Ириса.\nДерзкий, умный, по факту.\n\nИспользуй кнопки ниже для навигации!`, 
      Markup.inlineKeyboard([
        [Markup.button.callback("👤 Профиль", "profile"), Markup.button.callback("🎮 Игры", "games")],
        [Markup.button.url("📣 Канал проекта", "https://t.me/NobuCraft")]
      ])
    );
  });

  bot.command("profile", async (ctx) => {
    const u = ctx.user;
    const msg = `
👤 *ПРОФИЛЬ: ${u.nickname || u.firstName}*
━━━━━━━━━━━━━━━━━━
👑 Ранг: *${u.rankName}* [${u.rank}]
💰 Монетки: \`${u.coins}\`
💎 Алмазы: \`${u.diamonds}\`
⚡️ Энергия: \`${u.energy}/100\`
📊 Уровень: \`${u.level}\` (\`${u.exp}\` XP)
❤️ Здоровье: \`${u.health}/${u.maxHealth}\`
⚔️ Урон: \`${u.damage}\` | 🛡 Броня: \`${u.armor}\`
━━━━━━━━━━━━━━━━━━
🏆 Боссы: \`${u.bossKills}\`
⚠️ Варны: \`${u.warns}/3\`
    `;
    ctx.reply(msg, { 
      parse_mode: "Markdown",
      ...Markup.inlineKeyboard([
        [Markup.button.callback("🔄 Обновить", "profile"), Markup.button.callback("⚙️ Настройки", "settings")]
      ])
    });
  });

  bot.command("dice", async (ctx) => {
    const amount = parseInt(ctx.message.text.split(" ")[1]);
    if (isNaN(amount) || amount <= 0) return ctx.reply("👉 Юзай: /dice <ставка>");
    if (ctx.user.coins < amount) return ctx.reply("💸 Мало бабок, иди работай.");

    const userRoll = Math.floor(Math.random() * 6) + 1;
    const botRoll = Math.floor(Math.random() * 6) + 1;

    let resultMsg = `🎲 *ИГРА В КОСТИ*\n━━━━━━━━━━━━\n👤 Твой бросок: *${userRoll}*\n🤖 Спектр: *${botRoll}*\n━━━━━━━━━━━━\n`;

    if (userRoll > botRoll) {
      await storage.updateUser(ctx.user.id, { coins: ctx.user.coins + amount, diceWins: (ctx.user.diceWins || 0) + 1 });
      resultMsg += `🎉 Победа! Ты поднял *${amount}* монеток.`;
    } else if (userRoll < botRoll) {
      await storage.updateUser(ctx.user.id, { coins: ctx.user.coins - amount, diceLosses: (ctx.user.diceLosses || 0) + 1 });
      resultMsg += `🤡 Спектр тебя уделал. Минус *${amount}*.`;
    } else {
      resultMsg += "🤝 Ничья! Все остались при своих.";
    }
    ctx.reply(resultMsg, { parse_mode: "Markdown" });
  });

  bot.command("slots", async (ctx) => {
    const amount = parseInt(ctx.message.text.split(" ")[1]);
    if (isNaN(amount) || amount <= 0) return ctx.reply("👉 Юзай: /slots <ставка>");
    if (ctx.user.coins < amount) return ctx.reply("💸 Мало бабок.");

    const icons = ["🍎", "🍋", "🍒", "💎", "7️⃣"];
    const r1 = icons[Math.floor(Math.random() * icons.length)];
    const r2 = icons[Math.floor(Math.random() * icons.length)];
    const r3 = icons[Math.floor(Math.random() * icons.length)];

    let win = 0;
    if (r1 === r2 && r2 === r3) win = amount * 10;
    else if (r1 === r2 || r2 === r3 || r1 === r3) win = amount * 2;

    const resultMsg = `🎰 *ИГРОВЫЕ АВТОМАТЫ*\n━━━━━━━━━━━━\n[ ${r1} | ${r2} | ${r3} ]\n━━━━━━━━━━━━\n` + (win > 0 ? `🎉 Победа! Забрал *${win}*!` : `💀 Слил *${amount}*.`);
    
    await storage.updateUser(ctx.user.id, { 
      coins: ctx.user.coins - amount + win,
      slotsWins: win > 0 ? (ctx.user.slotsWins || 0) + 1 : ctx.user.slotsWins,
      slotsLosses: win === 0 ? (ctx.user.slotsLosses || 0) + 1 : ctx.user.slotsLosses
    });
    ctx.reply(resultMsg, { parse_mode: "Markdown" });
  });

  bot.command("rps", async (ctx) => {
    const args = ctx.message.text.split(" ");
    const amount = parseInt(args[1]);
    const userChoice = args[2]?.toLowerCase();
    const options = ["камень", "ножницы", "бумага"];

    if (isNaN(amount) || amount <= 0 || !options.includes(userChoice)) {
      return ctx.reply("👉 Юзай: /rps <ставка> <камень/ножницы/бумага>");
    }
    if (ctx.user.coins < amount) return ctx.reply("💸 Мало бабок.");

    const botChoice = options[Math.floor(Math.random() * 3)];
    let result = "";
    let win = 0;

    if (userChoice === botChoice) {
      result = "🤝 Ничья! Остался при своих.";
      win = amount;
    } else if (
      (userChoice === "камень" && botChoice === "ножницы") ||
      (userChoice === "ножницы" && botChoice === "бумага") ||
      (userChoice === "бумага" && botChoice === "камень")
    ) {
      result = "😎 Харош! Ты победил.";
      win = amount * 2;
    } else {
      result = "🤡 Спектр тебя уделал.";
      win = 0;
    }

    await storage.updateUser(ctx.user.id, {
      coins: ctx.user.coins - amount + win,
      rpsWins: win > amount ? (ctx.user.rpsWins || 0) + 1 : ctx.user.rpsWins,
      rpsLosses: win === 0 ? (ctx.user.rpsLosses || 0) + 1 : ctx.user.rpsLosses,
      rpsDraws: win === amount ? (ctx.user.rpsDraws || 0) + 1 : ctx.user.rpsDraws
    });

    const msg = `👊 *КНБ*\n━━━━━━━━━━━━\n👤 Ты: *${userChoice}*\n🤖 Спектр: *${botChoice}*\n━━━━━━━━━━━━\n${result}`;
    ctx.reply(msg, { parse_mode: "Markdown" });
  });

  bot.command("roulette", async (ctx) => {
    const args = ctx.message.text.split(" ");
    const amount = parseInt(args[1]);
    const choice = args[2]?.toLowerCase();
    
    if (isNaN(amount) || amount <= 0 || !choice) {
      return ctx.reply("👉 Юзай: /roulette <ставка> <красный/черный/зеленый/число>");
    }
    if (ctx.user.coins < amount) return ctx.reply("💸 Мало бабок.");

    const winNumber = Math.floor(Math.random() * 37);
    let winColor = winNumber === 0 ? "зеленый" : (winNumber % 2 === 0 ? "черный" : "красный");

    let win = 0;
    if (choice === winColor) {
      win = choice === "зеленый" ? amount * 14 : amount * 2;
    } else if (choice === winNumber.toString()) {
      win = amount * 35;
    }

    await storage.updateUser(ctx.user.id, {
      coins: ctx.user.coins - amount + win,
      casinoWins: win > 0 ? (ctx.user.casinoWins || 0) + 1 : ctx.user.casinoWins,
      casinoLosses: win === 0 ? (ctx.user.casinoLosses || 0) + 1 : ctx.user.casinoLosses
    });

    const msg = `🎰 *РУЛЕТКА*\n━━━━━━━━━━━━\n🎯 Выпало: *${winNumber}* (${winColor})\n━━━━━━━━━━━━\n` + (win > 0 ? `🎉 Поднял *${win}*!` : `💀 Профукал всё.`);
    ctx.reply(msg, { parse_mode: "Markdown" });
  });

  bot.command("work", async (ctx) => {
    const now = new Date();
    const lastWork = ctx.user.lastWork;
    if (lastWork && (now.getTime() - new Date(lastWork).getTime()) < 60 * 60 * 1000) {
      const timeLeft = Math.ceil((60 * 60 * 1000 - (now.getTime() - new Date(lastWork).getTime())) / (60 * 1000));
      return ctx.reply(`⏳ Ты устал. Отдохни еще ${timeLeft} мин.`);
    }
    const reward = Math.floor(Math.random() * 200) + 50;
    await storage.updateUser(ctx.user.id, { 
      coins: ctx.user.coins + reward, 
      lastWork: now,
      commandsCount: (ctx.user.commandsCount || 0) + 1
    });
    ctx.reply(`⚒ *РАБОТА*\n━━━━━━━━━━━━\nТы попахал на заводе и заработал *${reward}* монеток.`, { parse_mode: "Markdown" });
  });

  bot.command("daily", async (ctx) => {
    const lastDaily = ctx.user.lastDaily;
    const now = new Date();
    if (lastDaily && (now.getTime() - new Date(lastDaily).getTime()) < 24 * 60 * 60 * 1000) {
      return ctx.reply("⏳ Ты уже забирал бонус сегодня. Приходи завтра!");
    }
    
    await storage.updateUser(ctx.user.id, { 
      coins: ctx.user.coins + 500, 
      lastDaily: now,
      commandsCount: (ctx.user.commandsCount || 0) + 1
    });
    ctx.reply("🎁 *ЕЖЕДНЕВНЫЙ БОНУС*\n━━━━━━━━━━━━\nБаза! Забрал свои *500* монеток.", { parse_mode: "Markdown" });
  });

  bot.command("pay", async (ctx) => {
    if (!ctx.message.reply_to_message) {
      const args = ctx.message.text.split(" ");
      const targetId = parseInt(args[1]);
      const amount = parseInt(args[2]);

      if (isNaN(targetId) || isNaN(amount) || amount <= 0) {
        return ctx.reply("👉 Юзай: /pay <ID> <сумма> (или ответом на сообщение)");
      }
      if (ctx.user.coins < amount) return ctx.reply("💸 У тебя нет столько.");

      const target = await storage.getUserByTelegramId(targetId);
      if (!target) return ctx.reply("🔍 Пользователь не найден.");

      await storage.updateUser(ctx.user.id, { coins: ctx.user.coins - amount });
      await storage.updateUser(target.id, { coins: target.coins + amount });

      return ctx.reply(`💸 Перевел *${amount}* монеток [${target.firstName}](tg://user?id=${target.telegramId})`, { parse_mode: "Markdown" });
    }

    const amount = parseInt(ctx.message.text.split(" ")[1]);
    if (isNaN(amount) || amount <= 0) return ctx.reply("👉 Юзай: /pay <сумма> (ответом на сообщение)");
    if (ctx.user.coins < amount) return ctx.reply("💸 Мало бабок.");

    const targetId = ctx.message.reply_to_message.from?.id;
    const target = await storage.getUserByTelegramId(targetId!);
    if (!target) return ctx.reply("🔍 Пользователь не найден.");

    await storage.updateUser(ctx.user.id, { coins: ctx.user.coins - amount });
    await storage.updateUser(target.id, { coins: target.coins + amount });

    ctx.reply(`💸 Перевел *${amount}* монеток [${target.firstName}](tg://user?id=${target.telegramId})`, { parse_mode: "Markdown" });
  });

  // Launch
  bot.launch(() => console.log("🤖 Спектр IRIS-STYLE запущен!"));
}
