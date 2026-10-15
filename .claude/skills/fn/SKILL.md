---
name: fn
description: main.py (~9900 qator) ichidan funksiya yoki endpointni butun faylni o'qimasdan topib o'qish. Argument — funksiya nomi, endpoint yo'li yoki kalit so'z.
---

# main.py'dan kerakli qismni topish

`main.py` ni HECH QACHON to'liq o'qima.

1. Top:
   - funksiya: `grep -n "def ARG\b" main.py`
   - endpoint: `grep -n '"/api/.*ARG' main.py`
   - kalit so'z: `grep -n "ARG" main.py | head -30`
2. Funksiya oxirini aniqlash: boshlanish qatoridan keyingi birinchi top-level `def`/`async def`/`@app`/`# ───` qatori:
   `awk -v s=START 'NR>s && /^(async def|def|@app|class|# ─)/{print NR; exit}' main.py`
3. Faqat shu oraliqni o'qi (Read offset/limit). Chaqiruvchilarni bilish kerak bo'lsa: `grep -n "ARG(" main.py`.
4. Natija: `main.py:QATOR` havolasi + funksiya nima qilishining 1–3 qatorli qisqa izohi.
