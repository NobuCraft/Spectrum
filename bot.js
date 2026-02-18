import { Telegraf } from "telegraf";
import axios from "axios";

const TOKEN = process.env.TELEGRAM_TOKEN || "8326390250:AAEpXRnhLLLi5zUeFC39nfkHDlxR5ZFQ_yQ";
const DEEPSEEK_KEY = process.env.DEEPSEEK_KEY || "sk-4c18a0f28fce421482cbcedcc33cb18d";

const bot = new Telegraf(TOKEN);

// Функция для DeepSeek
async function askDeepSeek(question) {
  try {
    const response = await axios.post(
      "https://api.deepseek.com/v1/chat/completions",
      {
        model: "deepseek-chat",
        messages: [
          { role: "system", content: "Ты — полезный ассистент. Отвечай кратко и по делу." },
          { role: "user", content: question }
        ],
        temperature: 0.7,
      },
      {
        headers: {
          "Authorization": `Bearer ${DEEPSEEK_KEY}`,
          "Content-Type": "application/json",
        },
      }
    );
    return response.data.choices[0].message.content;
  } catch (error) {
    console.error("DeepSeek error:", error.message);
    return "😵 Ошибка связи с AI. Попробуй позже.";
  }
}

// Команда /start
bot.start((ctx) => {
  ctx.reply(
    "🤖 *DeepSeek Test Bot*\n\nПривет! Я тестовый бот с DeepSeek AI.\n\n" +
    "📝 *Команды:*\n" +
    "• /ask [вопрос] — спросить AI\n" +
    "• /test — проверить работу\n" +
    "• /id — узнать свой ID",
    { parse_mode: "Markdown" }
  );
});

// Команда /ask — спросить AI
bot.command("ask", async (ctx) => {
  const question = ctx.message.text.replace("/ask", "").trim();
  
  if (!question) {
    return ctx.reply("❓ Напиши вопрос после /ask\nПример: `/ask как дела?`", 
      { parse_mode: "Markdown" });
  }

  await ctx.sendChatAction("typing");
  const answer = await askDeepSeek(question);
  ctx.reply(`🤖 *DeepSeek:*\n${answer}`, { parse_mode: "Markdown" });
});

// Команда /test
bot.command("test", (ctx) => {
  ctx.reply("✅ Бот работает!\n🤖 DeepSeek подключен");
});

// Команда /id
bot.command("id", (ctx) => {
  ctx.reply(`🆔 Твой ID: \`${ctx.from.id}\``, { parse_mode: "Markdown" });
});

// Ответ на любое сообщение (если не команда)
bot.on("text", async (ctx) => {
  // Не отвечаем на команды
  if (ctx.message.text.startsWith("/")) return;
  
  await ctx.sendChatAction("typing");
  const answer = await askDeepSeek(ctx.message.text);
  ctx.reply(`🤖 *DeepSeek:*\n${answer}`, { parse_mode: "Markdown" });
});

// Запуск
bot.launch().then(() => {
  console.log("🤖 DeepSeek Test Bot запущен!");
  console.log("📊 DeepSeek API:", DEEPSEEK_KEY ? "Подключен" : "Нет ключа");
});

// Graceful stop
process.once("SIGINT", () => bot.stop("SIGINT"));
process.once("SIGTERM", () => bot.stop("SIGTERM"));
