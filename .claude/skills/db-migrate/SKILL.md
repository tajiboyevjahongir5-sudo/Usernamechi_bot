---
name: db-migrate
description: SQLite sxemaga yangi jadval yoki ustun qo'shish (init_db) mavjud Railway bazasini buzmasdan.
---

# DB migratsiya (`init_db`)

Railway'da ishlab turgan baza bor — sxema o'zgarishi faqat **qo'shimcha** va **qayta ishga tushirishga chidamli** bo'lsin.

1. `grep -n "async def init_db" main.py`, keyin o'zgartiriladigan jadvalning `CREATE TABLE` qismini offset/limit bilan o'qi.
2. **Yangi jadval**: `CREATE TABLE IF NOT EXISTS ...` — `init_db` ichida, bog'liq jadvallar yonida. Kerakli indeks: `CREATE INDEX IF NOT EXISTS ...`.
3. **Yangi ustun** — ikkala joyga:
   - `CREATE TABLE` ta'rifiga (yangi bazalar uchun);
   - o'sha jadval migratsiyalari qatoriga, mavjud uslubda:
     ```python
     try: await db.execute("ALTER TABLE users ADD COLUMN yangi_ustun INTEGER DEFAULT 0")
     except Exception: pass
     ```
   - Har doim `DEFAULT` ber (eski qatorlar uchun). `NOT NULL` faqat `DEFAULT` bilan.
4. TAQIQ: `DROP TABLE`, `DROP COLUMN`, ustun nomini o'zgartirish, ma'lumotni o'chiruvchi UPDATE — foydalanuvchi aniq so'ramasa.
5. Yangi ustunni ishlatadigan SELECT/INSERT'larni yangila (grep bilan top).
6. Tekshiruv: import testi va yangi bo'sh baza bilan `init_db` ishlashi:
   ```bash
   BOT_TOKEN=x API_ID=1 API_HASH=x ADMIN_IDS=1 DB_PATH="$TEMP/mig_t.db" python -c "import asyncio, main; asyncio.run(main.init_db()); asyncio.run(main.init_db()); print('ok')"
   ```
   (Ikki marta — qayta ishga tushishga chidamlilikni tekshiradi.) Keyin `mig_t.db` ni o'chir.
