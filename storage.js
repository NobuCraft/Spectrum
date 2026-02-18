// storage.js
import Database from 'better-sqlite3';
const db = new Database('spectrum.db');

// Создаем таблицы
db.exec(`
  CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegramId INTEGER UNIQUE,
    username TEXT,
    firstName TEXT,
    lastName TEXT,
    role TEXT DEFAULT 'user',
    rank INTEGER DEFAULT 0,
    rankName TEXT DEFAULT 'Участник',
    coins INTEGER DEFAULT 1000,
    diamonds INTEGER DEFAULT 0,
    energy INTEGER DEFAULT 100,
    level INTEGER DEFAULT 1,
    exp INTEGER DEFAULT 0,
    health INTEGER DEFAULT 100,
    maxHealth INTEGER DEFAULT 100,
    damage INTEGER DEFAULT 10,
    armor INTEGER DEFAULT 0,
    bossKills INTEGER DEFAULT 0,
    warns INTEGER DEFAULT 0,
    muteUntil TEXT,
    banned INTEGER DEFAULT 0,
    banDate TEXT,
    banReason TEXT,
    lastWork TEXT,
    lastDaily TEXT,
    diceWins INTEGER DEFAULT 0,
    diceLosses INTEGER DEFAULT 0,
    slotsWins INTEGER DEFAULT 0,
    slotsLosses INTEGER DEFAULT 0,
    rpsWins INTEGER DEFAULT 0,
    rpsLosses INTEGER DEFAULT 0,
    rpsDraws INTEGER DEFAULT 0,
    casinoWins INTEGER DEFAULT 0,
    casinoLosses INTEGER DEFAULT 0,
    commandsCount INTEGER DEFAULT 0,
    nickname TEXT,
    createdAt TEXT DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE IF NOT EXISTS blacklist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word TEXT UNIQUE
  );

  CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    userId INTEGER,
    action TEXT,
    details TEXT,
    createdAt TEXT DEFAULT CURRENT_TIMESTAMP
  );
`);

export const storage = {
  // Пользователи
  getUserByTelegramId: (telegramId) => {
    return db.prepare('SELECT * FROM users WHERE telegramId = ?').get(telegramId);
  },
  
  createUser: (userData) => {
    const stmt = db.prepare(`
      INSERT INTO users (telegramId, username, firstName, lastName, role, rank, rankName)
      VALUES (@telegramId, @username, @firstName, @lastName, @role, @rank, @rankName)
    `);
    stmt.run(userData);
    return storage.getUserByTelegramId(userData.telegramId);
  },
  
  updateUser: (id, updates) => {
    const keys = Object.keys(updates);
    const setStr = keys.map(k => `${k} = ?`).join(', ');
    const values = keys.map(k => updates[k]);
    db.prepare(`UPDATE users SET ${setStr} WHERE id = ?`).run(...values, id);
  },
  
  getUsersByRank: (minRank) => {
    return db.prepare('SELECT * FROM users WHERE rank >= ?').all(minRank);
  },
  
  // Черный список
  isWordBlacklisted: (text) => {
    const words = db.prepare('SELECT word FROM blacklist').all();
    return words.some(w => text.toLowerCase().includes(w.word.toLowerCase()));
  },
  
  addToBlacklist: (word) => {
    db.prepare('INSERT OR IGNORE INTO blacklist (word) VALUES (?)').run(word.toLowerCase());
  },
  
  removeFromBlacklist: (word) => {
    db.prepare('DELETE FROM blacklist WHERE word = ?').run(word.toLowerCase());
  },
  
  getBlacklist: () => {
    return db.prepare('SELECT word FROM blacklist').all().map(w => w.word);
  },
  
  // Логи
  createLog: (logData) => {
    db.prepare('INSERT INTO logs (userId, action, details) VALUES (?, ?, ?)')
      .run(logData.userId, logData.action, logData.details);
  }
};
