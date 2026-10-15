# Usernamechi bot

Telegram username qidirish/poylash/sotish boti. aiogram + FastAPI + Telethon + SQLite (aiosqlite).

## Tuzilma
- `main.py` (~9900 qator) — butun backend bitta faylda. **To'liq o'qima**: funksiyani `grep -n "def nom"` bilan top, keyin offset/limit bilan faqat o'sha qismni o'qi.
  - DB sxema: `init_db`; qidiruv: `generate_usernames`, `search_sniper`, `score_username`; poylash: `monitoring_loop`, `api_monitor_start`; savdo: `api_marketplace_*`, `transfer_username`, `auction_close_loop`; admin API: `/api/admin/*` (`x_admin_token` + `for/else: raise 403`).
- `bot/words.py` — so'z lug'atlari. `*.txt` lug'at fayllarini o'qima (katta).
- `static/app/index.html` — mini-app, `static/admin/index.html` — admin panel.
- E'tibor berma: `legacy/`, `create_files*.py`, `inject_*.py`, `temp.js`, `search*.py`, `do_grep.py`.
- `promo/` — reklama videosi skriptlari (git'dan chetlatilgan).

## Qoidalar
- Pul o'zgarishi faqat atomik: `UPDATE ... SET balance=balance-? WHERE ... AND balance>=?` + `rowcount` tekshiruvi.
- Deploy: Railway `main` branchidan. Push `main`ga (`master` emas).
- Tekshiruv: `python -m py_compile main.py`; import testi: `BOT_TOKEN=x API_ID=1 API_HASH=x ADMIN_IDS=1 DB_PATH=t.db python -c "import main"`.
- Javoblar o'zbekcha, qisqa.
