---
name: admin-api
description: Yangi /api/admin/* endpoint qo'shish (FastAPI, x_admin_token himoyasi) va kerak bo'lsa admin panelga ulash.
---

# Yangi admin endpoint

1. Mavjud o'xshash endpointni top: `grep -n '@app\.\(get\|post\)("/api/admin' main.py`. Yangi endpointni mantiqan mos bo'lim yoniga qo'y.
2. **Majburiy shablon** (himoyasiz admin endpoint bo'lmasin):
   ```python
   @app.post("/api/admin/NOM")
   async def admin_nom(request: Request, x_admin_token: str = Header(default="")):
       for aid in ADMIN_IDS:
           if get_admin_token(aid) == x_admin_token: break
       else: raise HTTPException(403)
       data = await request.json()
       async with aiosqlite.connect(DB_PATH, timeout=20.0) as db:
           db.row_factory = aiosqlite.Row
           ...
   ```
3. Qoidalar:
   - SQL faqat parametrli (`?`), f-string bilan SQL YO'Q.
   - Kiruvchi qiymatlarni tekshir (tur, chegara); xato bo'lsa `HTTPException(400, "...")`.
   - Pulga tegsa — `/money-check` qoidalari.
   - Ro'yxat qaytarsa `LIMIT` qo'y.
4. Admin panel (`static/admin/index.html`) kerak bo'lsa: mavjud fetch chaqiruvini grep bilan top va o'sha uslubda `x-admin-token` header bilan chaqir.
5. Tekshiruv: `python -m py_compile main.py` + import testi (CLAUDE.md).
