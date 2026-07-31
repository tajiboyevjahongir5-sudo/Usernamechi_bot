"""
================================================
 migrate_to_pg.py — Volume (SQLite) ➔ PostgreSQL
================================================
 Dynamic Migration Tool for Usernamechi SaaS Bot
================================================
"""

import asyncio
import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Migrator")

SEARCH_PATHS = [
    "/app/data/usernamechi.db",
    "usernamechi.db",
    "saas.db",
    "app.db",
    "database.db"
]

def find_sqlite_db():
    for p in SEARCH_PATHS:
        if os.path.exists(p) and os.path.getsize(p) > 0:
            return p
    return None

async def run_migration():
    pg_url = os.getenv("DATABASE_URL")
    if not pg_url:
        logger.error("❌ DATABASE_URL environment variable topilmadi! Railway PostgreSQL bog'langani tekshiring.")
        return False
        
    pg_url = pg_url.replace("postgres://", "postgresql://")
    
    sqlite_db_path = find_sqlite_db()
    if not sqlite_db_path:
        logger.warning("⚠️ Migratsiya uchun SQLite (.db) fayl topilmadi. Yangi PostgreSQL bazadan boshlanadi.")
        return False
        
    logger.info(f"📂 Topilgan SQLite baza: {sqlite_db_path} (Hajmi: {os.path.getsize(sqlite_db_path)} bayt)")

    try:
        import aiosqlite
        import asyncpg
    except ImportError:
        logger.error("❌ Required libraries missing. Run: pip install asyncpg psycopg2-binary aiosqlite")
        return False

    logger.info("🔌 PostgreSQL ga ulanmoqda...")
    pg_pool = await asyncpg.create_pool(pg_url, min_size=1, max_size=5)

    async with pg_pool.acquire() as pg:
        # 1. Schema yaratish
        logger.info("🏗 PostgreSQL jadvallari yaratilmoqda...")
        await pg.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id BIGINT PRIMARY KEY,
                first_name TEXT DEFAULT '',
                username TEXT DEFAULT '',
                balance BIGINT DEFAULT 5000,
                seller_balance BIGINT DEFAULT 0,
                free_searches INT DEFAULT 1,
                session_string TEXT DEFAULT '',
                is_premium INT DEFAULT 0,
                premium_until TEXT DEFAULT '',
                referred_by BIGINT DEFAULT 0,
                referrer_id BIGINT DEFAULT 0,
                reward_given INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS monitoring_tasks (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT,
                username VARCHAR(32) NOT NULL,
                paid_amount BIGINT DEFAULT 10000,
                status VARCHAR(20) DEFAULT 'monitoring',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS listings (
                id SERIAL PRIMARY KEY,
                seller_id BIGINT,
                username VARCHAR(32) NOT NULL,
                price BIGINT NOT NULL,
                status VARCHAR(20) DEFAULT 'active',
                is_auction INT DEFAULT 0,
                current_bid BIGINT DEFAULT 0,
                highest_bidder_id BIGINT DEFAULT 0,
                auction_ends_at DOUBLE PRECISION DEFAULT 0,
                telegram_message_id BIGINT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS listing_orders (
                id SERIAL PRIMARY KEY,
                listing_id INT,
                buyer_id BIGINT,
                expected_amount BIGINT NOT NULL,
                status VARCHAR(20) DEFAULT 'completed',
                created_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
            );

            CREATE TABLE IF NOT EXISTS withdrawals (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT,
                amount BIGINT NOT NULL,
                card_number VARCHAR(30),
                card_owner VARCHAR(100),
                status VARCHAR(20) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS settings (
                key VARCHAR(100) PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS payment_cards (
                id SERIAL PRIMARY KEY,
                card_number VARCHAR(30) NOT NULL,
                card_owner VARCHAR(100) DEFAULT '',
                daily_limit INT DEFAULT 40,
                today_count INT DEFAULT 0,
                last_reset_date VARCHAR(20) DEFAULT '',
                is_active INT DEFAULT 1,
                sort_order INT DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS referrals (
                id SERIAL PRIMARY KEY,
                referrer_id BIGINT,
                user_id BIGINT,
                reward_given INT DEFAULT 1,
                reward_amount BIGINT DEFAULT 1000,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 2. SQLite ulanish
        async with aiosqlite.connect(sqlite_db_path) as sl:
            sl.row_factory = aiosqlite.Row

            # A. USERS migratsiya
            async with sl.execute("SELECT * FROM users") as c:
                users = await c.fetchall()
            u_count = 0
            for u in users:
                d = dict(u)
                await pg.execute("""
                    INSERT INTO users (telegram_id, first_name, username, balance, seller_balance, session_string, is_premium, premium_until, referred_by, referrer_id, reward_given)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    ON CONFLICT (telegram_id) DO UPDATE SET
                        balance = EXCLUDED.balance,
                        seller_balance = EXCLUDED.seller_balance,
                        session_string = EXCLUDED.session_string,
                        is_premium = EXCLUDED.is_premium
                """, d.get('telegram_id'), d.get('first_name','') or '', d.get('username','') or '',
                     d.get('balance', 0) or 0, d.get('seller_balance', 0) or 0,
                     d.get('session_string','') or '', d.get('is_premium',0) or 0,
                     str(d.get('premium_until','') or ''), d.get('referred_by',0) or 0,
                     d.get('referrer_id',0) or 0, d.get('reward_given',0) or 0)
                u_count += 1
            logger.info(f"✅ {u_count} ta foydalanuvchi PostgreSQL ga ko'chirildi.")

            # B. MONITORING_TASKS migratsiya
            async with sl.execute("SELECT * FROM monitoring_tasks") as c:
                tasks = await c.fetchall()
            t_count = 0
            for t in tasks:
                d = dict(t)
                await pg.execute("""
                    INSERT INTO monitoring_tasks (telegram_id, username, paid_amount, status)
                    VALUES ($1, $2, $3, $4)
                """, d.get('telegram_id'), d.get('username',''), d.get('paid_amount', 10000) or 10000, d.get('status','monitoring') or 'monitoring')
                t_count += 1
            logger.info(f"✅ {t_count} ta monitoring nishon ko'chirildi.")

            # C. LISTINGS migratsiya
            async with sl.execute("SELECT * FROM listings") as c:
                listings = await c.fetchall()
            l_count = 0
            for l in listings:
                d = dict(l)
                await pg.execute("""
                    INSERT INTO listings (seller_id, username, price, status, is_auction, current_bid, highest_bidder_id, auction_ends_at, telegram_message_id)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """, d.get('seller_id'), d.get('username',''), d.get('price',0) or 0, d.get('status','active'),
                     d.get('is_auction',0) or 0, d.get('current_bid',0) or 0, d.get('highest_bidder_id',0) or 0,
                     float(d.get('auction_ends_at',0) or 0), d.get('telegram_message_id',0) or 0)
                l_count += 1
            logger.info(f"✅ {l_count} ta e'lon ko'chirildi.")

            # D. SETTINGS migratsiya
            async with sl.execute("SELECT * FROM settings") as c:
                settings = await c.fetchall()
            s_count = 0
            for s in settings:
                d = dict(s)
                await pg.execute("""
                    INSERT INTO settings (key, value) VALUES ($1, $2)
                    ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
                """, d.get('key'), str(d.get('value','')))
                s_count += 1
            logger.info(f"✅ {s_count} ta sozlama ko'chirildi.")

    await pg_pool.close()
    logger.info("🎉 Barcha Volume ma'lumotlari PostgreSQL ga MUVAFFAQIYATLI KO'CHIRILDI!")
    return True

if __name__ == "__main__":
    asyncio.run(run_migration())
