# 🏢 Kvartira Bot — Flatmate Household Management System

A production-ready, modular, and resilient Telegram bot built with **aiogram 3.x**, **APScheduler**, **aiohttp**, and **SQLite (via aiosqlite)** for an 8-person flatmate household.

---

## 👥 Flatmate Roster & Room Assignments

### 🏠 1-Xona (Room 1):
1. **Avazbek** (ID 1)
2. **Firdavs** (ID 2)
3. **Asadbek bro** (ID 3)
4. **Omadbek** (ID 4)
* **Water Queue (1-Xona Baki):** `Avazbek ➔ Firdavs ➔ Asadbek bro ➔ Omadbek` (Circular)

### 🚪 2-Xona (Room 2):
5. **Ilyosbek** (ID 5)
6. **Jaloliddin** (ID 6)
7. **Asadbek** (ID 7)
8. **Mavlonbek** (ID 8)
* **Water Queue (2-Xona Baki):** `Ilyosbek ➔ Jaloliddin ➔ Asadbek ➔ Mavlonbek` (Circular)

---

## 🗓️ Default Rotations & Schedules

### 👨‍🍳 Kunlik Navbatchilik (`daily_duty`):
* **Dushanba:** Jaloliddin (6)
* **Seshanba:** Firdavs (2)
* **Chorshanba:** Asadbek (7)
* **Payshanba:** Asadbek bro (3)
* **Juma:** Mavlonbek (8)
* **Shanba:** Avazbek (1)
* **Yakshanba:** Omadbek (4) & Ilyosbek (5)

### 🧺 Kir Yuvish Navbati (`laundry_duty`):
* **Dushanba:** Firdavs (2) / Mavlonbek (8)
* **Seshanba:** Jaloliddin (6)
* **Chorshanba:** Asadbek bro (3)
* **Payshanba:** Omadbek (4)
* **Juma:** Asadbek (7)
* **Shanba:** Ilyosbek (5)
* **Yakshanba:** Avazbek (1) / Mavlonbek (8)

### 👥 Oylik 4-Haftalik Juftliklar (Bozorlik & General Uborqa):
* **1-hafta (1–7 kunlar):** Omadbek (4) & Asadbek bro (3)
* **2-hafta (8–14 kunlar):** Ilyosbek (5) & Jaloliddin (6)
* **3-hafta (15–21 kunlar):** Avazbek (1) & Firdavs (2)
* **4-hafta (22–oy oxiri):** Mavlonbek (8) & Asadbek (7)

---

## 🌟 Asosiy Imkoniyatlar & Anti-Spam UX

1. **Anti-Spam & Guruh Tozaligi:**
   - Guruhdagi barcha buyruqlar (`/start`, `/bugun`, `/suv`, `/hafta`, `/almashish`) avtomatik ravishda o'chiriladi (`await message.delete()`).
   - Tugmalar bosilganda xabar ichida o'zgaradi (In-Place Edit), yangi ortiqcha xabarlar chiqarilmaydi.
   - Interaktiv jarayonlar (rasm yuborish, navbat tanlash) to'liq botning shaxsiy chatiga (PM) deep-link orqali yo'naltiriladi.
   - Guruhdagi vaqtinchalik xabarlar 30 soniyadan so'ng avtomatik o'chiriladi.

2. **2 ta Alohida Suv Baki (Dual-Room Queues):**
   - 1-xona va 2-xona alohida baklar navbatini mustaqil boshqaradi.
   - Rasm proof (Foto) faqat PM da qabul qilinadi va yakunlangach guruhga 1 ta chiroyli hisobot beriladi.

3. **Kengaytirilgan Almashuv Tizimi (`/almashish`):**
   - **Kunlik navbatchilik almashish** (masalan: Dushanba kungi navbatni boshqa kishi bilan almashish).
   - **Haftalik juftlik almashish** (masalan: 1-hafta juftligi 3-hafta juftligi bilan to'liq almashishi).
   - **Juftlik ichida o'rinbosar biriktirish** (masalan: Omadbek o'z o'rniga boshqa xonadoshni biriktirishi).

4. **Avtomatlashtirilgan Eslatmalar (Asia/Tashkent):**
   - **07:30** — Kunlik brifing + 4 ta vazifa nazorat ro'yxati (Taom, Non, Idishlar, Axlat).
   - **21:30** — Axlat to'kilmagan bo'lsa navbatchilarni teg qilib qattiq eslatma yuborish.
   - **Yakshanba 09:00** — 11 ta punktli general tozalik nazorat ro'yxati.
   - **Yakshanba 23:59** — Vaqtinchalik o'zgartirishlarni avtomatik tozalash va standart rejani tiklash.

5. **24/7 Keep-Alive HTTP Server:**
   - Render / Koyeb platformalarida uxlab qolmasligi uchun `http://0.0.0.0:8080/health` endpointi faol.

---

## 🛠️ O'rnatish va Ishga Tushirish

```bash
# Virtual environment yaratish va paketlarni o'rnatish
pip install -r requirements.txt

# Testlarni yurgazish
python test_bot.py

# Botni ishga tushirish
python bot.py
```
