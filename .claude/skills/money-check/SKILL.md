---
name: money-check
description: Balans/pul o'zgarishlarini race-condition va double-spend uchun tekshirish. Pul, balans, to'lov, yechish, sotish, auksion kodiga tegilganda yoki deploy'dan oldin ishlat.
---

# Pul xavfsizligi tekshiruvi

Maqsad: `balance`, `seller_balance`, `current_bid`, `charged_amount` va boshqa pul maydonlarida double-spend bo'lmasin.

## Qayerni tekshirish
- Argument berilsa — o'sha funksiya/qator. Aks holda `git diff` (staged + unstaged).
- Topish: `grep -n "balance\|seller_balance\|withdraw\|charged_amount\|current_bid" main.py` — faqat diffga yaqin joylar.

## Qoidalar (har biri uchun ✅/❌)
1. **Ayirish atomik**: `UPDATE ... SET x=x-? WHERE ... AND x>=?` va `cur.rowcount` tekshiriladi (`deduct_balance` namunasi).
   ❌ `SELECT balance` → Python'da solishtirish → `UPDATE SET balance=?` (read-modify-write).
2. **rowcount = 0 bo'lsa** — jarayon to'xtaydi, xizmat berilmaydi, xabar qaytariladi.
3. **Holat o'tishi atomik**: buyurtma/yechish/listing statusi `UPDATE ... SET status='done' WHERE id=? AND status='pending'` + rowcount — ikki marta tasdiqlashning oldini oladi.
4. **Tartib**: avval pul yechiladi (atomik), keyin xizmat. Xizmat muvaffaqiyatsiz bo'lsa — qaytarish (refund) bor.
5. **Bitta tranzaksiya**: bir-biriga bog'liq yozuvlar (yechish + order yaratish) bitta `db` ulanishida va bitta `commit` bilan.
6. **Manfiy/yolg'on summa**: foydalanuvchidan kelgan `amount` > 0 va butun son ekanligi tekshiriladi.
7. **Qaytarish (refund) bir marta**: refund ham status shartli UPDATE bilan himoyalangan.

## Natija
Har bir topilma: `main.py:QATOR` — muammo — qanday buzilishi (aniq ssenariy) — tuzatish. Muammo yo'q bo'lsa qisqa "✅ toza" de.
Foydalanuvchi so'rasa tuzat; tuzatgandan keyin `python -m py_compile main.py`.
