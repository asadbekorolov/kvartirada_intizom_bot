# 🏢 Kvartira Bot — Household Management Telegram Bot

A production-ready, modular, and resilient Telegram bot built with **aiogram 3.x**, **APScheduler**, and **SQLite (via aiosqlite)** for an 8-person flatmate household.

---

## 👥 Flatmate Household Roster & Initial Data

| ID | Name | Room | Default Duty Role & Water Queue Index |
|---|---|---|---|
| 1 | Avazbek | Room 1 | Sat Daily Duty | Sat Laundry | Water Index 0 |
| 2 | Firdavs | Room 1 | Tue Daily Duty | Mon Laundry | Water Index 1 |
| 3 | Asadbek bro | Room 1 | Thu Daily Duty | Wed Laundry | Water Index 2 |
| 4 | Omadbek | Room 1 | Sun Daily Duty (Pair) | Thu Laundry | Water Index 3 |
| 5 | Ilyosbek | Room 2 | Sun Daily Duty (Pair) | Sat Laundry | Water Index 4 |
| 6 | Jaloliddin | Room 2 | Mon Daily Duty | Tue Laundry | Water Index 5 |
| 7 | Asadbek | Room 2 | Wed Daily Duty | Fri Laundry | Water Index 6 |
| 8 | Mavlonbek | Room 2 | Fri Daily Duty | Sun Laundry | Water Index 7 |

---

## 🌟 Key Features & Modules

### 📅 Module A: Daily Task Management & Interactive Checklist
- **07:30 Tashkent Morning Briefing:** Broadcasts today's daily lead, laundry lead, and water queue person to the Telegram group chat with an interactive checklist:
  - `[ ❌ / ✅ ] Taom tayyorlash`
  - `[ ❌ / ✅ ] Non olib kelish`
  - `[ ❌ / ✅ ] Umumiy idishlar / xontaxta tozaligi`
  - `[ ❌ / ✅ ] Axlat to'kish (Oshxona & Tualet)`
- **Dynamic State Engine:** Instant inline button toggling without chat spam.
- **Automated Celebration:** Automatically posts a celebration message when all 4 core tasks are completed.
- **21:30 Evening Enforcement:** Sends a firm reminder tagging active daily duty leads if `Axlat to'kish` remains incomplete.

### 🚰 Module B: Event-Driven Water Queue (Photo Verification & Proxy Logic)
- Initiate via `/suv` or `🚰 Suv olib keldim` reply button.
- Select bringer name -> Send photo proof.
- Calculates circular next person: `(bringer_index + 1) % 8`.
- Out-of-turn / Proxy support: Recalculates circular queue starting from whoever brought water.

### 🔄 Module C: Peer-to-Peer Duty Swap Engine
- Initiate via `/almashish` or `🔄 Navbat almashish` button.
- Select target day & flatmate -> Dispatches inline approval card `[ ✅ Roziman ]` / `[ ❌ Rad etish ]`.
- Updates `daily_overrides` table upon approval.
- Auto-resets temporary weekly overrides every Sunday at 23:59 Asia/Tashkent.

### 🧹 Module D: Yakshanbalik General Uborqa (Sunday Deep Clean)
- Triggers every Sunday at 09:00 Tashkent Time with an 11-point inspection checklist for rotating Sunday cleaning pairs:
  - Pair 1: Omadbek & Asadbek bro
  - Pair 2: Ilyosbek & Jaloliddin
  - Pair 3: Avazbek & Firdavs
  - Pair 4: Mavlonbek & Asadbek

### ⚙️ Module E: Protected Admin Operations
- `/suv_admin <user_id>`: Force-sets current water index.
- `/almash_admin <day_index> <user_ids>`: Force-swaps daily duty schedule.
- `/reset_tasks`: Resets daily checklist states.
- `/bind_admin <user_id> <telegram_id>`: Force-binds Telegram ID to flatmate profile.

---

## 📁 Directory Architecture

```
kvartira_bot/
├── .env.example              # Environment variables template
├── .env                      # Production environment configuration
├── requirements.txt          # Python dependencies
├── config.py                 # Pydantic Settings & timezone helper
├── database/
│   ├── connection.py         # SQLite connection manager & auto-seeding
│   ├── schema.sql            # Table DDL definitions
│   └── repositories.py       # Async CRUD repositories
├── services/
│   ├── queue_service.py      # Duty rotation & circular queue calculations
│   └── scheduler_jobs.py     # APScheduler 07:30, 21:30, Sun 09:00, Sun 23:59 jobs
├── states.py                 # FSM States (Water, Swap)
├── keyboards/
│   ├── inline.py             # Dynamic checklist & approval inline keyboards
│   └── reply.py              # Persistent main menu reply keyboard
├── middlewares/
│   ├── auth.py               # Telegram user profile mapper
│   └── admin.py              # IsAdminFilter command guard
├── handlers/
│   ├── common.py             # /start, /help, claim profile
│   ├── duty.py               # /bugun & task toggle callbacks
│   ├── water.py              # /suv photo submission & queue advance
│   ├── swap.py               # /almashish peer swap workflow
│   └── admin.py              # Admin override commands
├── test_bot.py               # Standalone unit & integration test runner
└── bot.py                    # Application entry point
```

---

## 🚀 Installation & Quick Start

1. **Clone/Navigate to Project:**
   ```bash
   cd C:\Users\asadb\.gemini\antigravity-ide\scratch\kvartira_bot
   ```

2. **Set up Environment Variables:**
   Edit `.env`:
   ```ini
   BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
   GROUP_CHAT_ID=-1001234567890
   ADMIN_USER_IDS=12345678,87654321
   BOT_TZ=Asia/Tashkent
   DB_PATH=kvartira.db
   ```

3. **Run Unit & Integration Tests:**
   ```bash
   .venv\Scripts\python.exe test_bot.py
   ```

4. **Launch Bot:**
   ```bash
   .venv\Scripts\python.exe bot.py
   ```
