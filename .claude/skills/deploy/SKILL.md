---
name: deploy
description: Botni Railway'ga deploy qilish — tekshiruv, commit, main'ga push. "deploy", "push qil", "chiqar" deyilganda ishlat.
---

# Deploy (Railway, `main` branch)

Har bir qadam muvaffaqiyatsiz bo'lsa — TO'XTA va xatoni ko'rsat.

1. **Branch**: `git branch --show-current`. `main` bo'lmasa (ayniqsa `master`) — to'xta, foydalanuvchidan so'ra.
2. **Sintaksis**: `python -m py_compile main.py` va o'zgargan boshqa `.py` fayllar.
3. **Import testi** (bash):
   ```bash
   BOT_TOKEN=x API_ID=1 API_HASH=x ADMIN_IDS=1 DB_PATH="$TEMP/deploy_t.db" python -c "import main"
   ```
   Keyin vaqtinchalik `deploy_t.db` ni o'chir.
4. **Diff ko'rigi**: `git diff --stat` + `git diff`. Pul (`balance`) o'zgargan bo'lsa — `/money-check` qoidalarini qo'lla.
   Sir (token, parol, `.env`, `*.db`, `*.session`) commit'ga tushmasin.
5. **Commit**: conventional uslub (`feat:`, `fix:`, `style(ui):`), qisqa, mazmunli. Faqat kerakli fayllarni `git add` qil (`git add -A` emas).
6. **Push**: `git push origin main`. Foydalanuvchi aytmaguncha `--force` YO'Q.
7. Natijani qisqa ayt: commit hash, push holati. Railway avtomatik deploy qiladi.
