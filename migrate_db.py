import asyncio
import aiosqlite
import os

DB_PATH = os.getenv("DB_PATH", "database.db")

async def migrate():
    print(f"Migrating database: {DB_PATH}")
    async with aiosqlite.connect(DB_PATH) as db:
        # 1. Update mandatory_channels
        try:
            await db.execute("ALTER TABLE mandatory_channels ADD COLUMN status TEXT DEFAULT 'Active'")
            print("Added status to mandatory_channels")
        except Exception as e:
            print(f"status column: {e}")
            
        try:
            await db.execute("ALTER TABLE mandatory_channels ADD COLUMN sort_order INTEGER DEFAULT 0")
            print("Added sort_order to mandatory_channels")
        except Exception as e:
            print(f"sort_order column: {e}")
            
        try:
            await db.execute("ALTER TABLE mandatory_channels ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP")
            await db.execute("ALTER TABLE mandatory_channels ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP")
            print("Added timestamps to mandatory_channels")
        except Exception as e:
            print(f"mandatory_channels timestamps: {e}")

        # 2. Update users
        try:
            await db.execute("ALTER TABLE users ADD COLUMN subscription_verified INTEGER DEFAULT 0")
            print("Added subscription_verified to users")
        except Exception as e:
            print(f"subscription_verified column: {e}")
            
        try:
            await db.execute("ALTER TABLE users ADD COLUMN reward_given INTEGER DEFAULT 0")
            print("Added reward_given to users")
        except Exception as e:
            print(f"reward_given column: {e}")

        # 3. Create referrals table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL UNIQUE,
                reward_given INTEGER DEFAULT 0,
                reward_amount INTEGER DEFAULT 1000,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("Created referrals table")
        
        await db.commit()
        print("Migration complete!")

if __name__ == "__main__":
    asyncio.run(migrate())
