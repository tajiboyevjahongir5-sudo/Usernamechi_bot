import sys
sys.path.insert(0, '.')
import os
os.environ.setdefault('BOT_TOKEN', 'test:test')
os.environ.setdefault('API_ID', '1')
os.environ.setdefault('API_HASH', 'test')

from main import prepare_pg_sql

tests = [
    ("INSERT OR IGNORE - literal values",
     "INSERT OR IGNORE INTO settings (key, value) VALUES ('payment_card', '8600')"),
    ("INSERT OR IGNORE - with params",
     "INSERT OR IGNORE INTO users (telegram_id, balance) VALUES (?, 5000)"),
    ("INSERT OR REPLACE",
     "INSERT OR REPLACE INTO pending_referrals (telegram_id, referrer_id) VALUES (?, ?)"),
    ("strftime interval delete",
     "DELETE FROM search_tasks WHERE created_at < CAST(strftime('%s','now', '-3 days') AS REAL)"),
    ("CREATE TABLE AUTOINCREMENT",
     "CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, tid INTEGER)"),
    ("PRAGMA",
     "PRAGMA journal_mode=WAL"),
    ("ON CONFLICT DO UPDATE",
     "ON CONFLICT(key) DO UPDATE SET value=?"),
    ("strftime basic",
     "UPDATE topups SET status='expired' WHERE status='pending' AND created_at <= (strftime('%s','now') - 180)"),
]

all_ok = True
for name, sql in tests:
    result = prepare_pg_sql(sql)
    bad_patterns = ["INSERT OR IGNORE", "INSERT OR REPLACE", "AUTOINCREMENT", "strftime"]
    bad = [p for p in bad_patterns if p in result]
    status = "✅" if not bad else f"❌ HALI: {bad}"
    print(f"{status} [{name}]")
    print(f"   IN:  {sql[:90]}")
    print(f"   OUT: {result[:90]}")
    print()
    if bad:
        all_ok = False

print("=" * 50)
print("NATIJA:", "✅ BARCHA TESTLAR O'TDI" if all_ok else "❌ BA'ZI TESTLAR MUVAFFAQIYATSIZ")
