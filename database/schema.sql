-- SQLite Schema for Kvartira Bot (Dual-Room & Monthly Pair Upgraded)

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    telegram_id BIGINT UNIQUE NULL,
    name TEXT NOT NULL,
    room_number INT NOT NULL,
    is_admin BOOLEAN NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS daily_overrides (
    week_number INT NOT NULL,
    day_of_week INT NOT NULL, -- 0=Mon, 1=Tue, ..., 6=Sun
    assigned_user_ids TEXT NOT NULL, -- JSON array string or comma separated IDs, e.g. "1" or "4,5"
    PRIMARY KEY(week_number, day_of_week)
);

CREATE TABLE IF NOT EXISTS daily_task_logs (
    log_date TEXT NOT NULL, -- YYYY-MM-DD
    task_key TEXT NOT NULL, -- 'cooking', 'bread', 'table_dishes', 'trash'
    is_completed BOOLEAN NOT NULL DEFAULT 0,
    completed_by INT NULL,
    completed_at TEXT NULL,
    PRIMARY KEY(log_date, task_key),
    FOREIGN KEY(completed_by) REFERENCES users(id) ON DELETE SET NULL
);

-- Dual-room independent water queues (Room 1 & Room 2)
CREATE TABLE IF NOT EXISTS room_water_state (
    room_id INTEGER PRIMARY KEY, -- 1 or 2
    current_user_index INT NOT NULL DEFAULT 0 -- 0..3
);

CREATE TABLE IF NOT EXISTS room_water_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INT NOT NULL,
    brought_by_user_id INT NOT NULL,
    photo_file_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(brought_by_user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Monthly Pair Rotations (Week 1..4 per Month)
CREATE TABLE IF NOT EXISTS weekly_pair_assignments (
    month_year TEXT NOT NULL, -- YYYY-MM
    week_index INT NOT NULL,  -- 0..3 (Week 1..4)
    pair_id INT NOT NULL,     -- 1..4
    member1_id INT NOT NULL,
    member2_id INT NOT NULL,
    PRIMARY KEY(month_year, week_index),
    FOREIGN KEY(member1_id) REFERENCES users(id),
    FOREIGN KEY(member2_id) REFERENCES users(id)
);

-- Advanced Swaps: DAILY, WEEKLY_PAIR, PAIR_MEMBER_PROXY
CREATE TABLE IF NOT EXISTS swap_requests (
    id TEXT PRIMARY KEY,
    requester_id INT NOT NULL,
    target_id INT NOT NULL,
    swap_type TEXT NOT NULL, -- 'DAILY', 'WEEKLY_PAIR', 'PAIR_MEMBER_PROXY'
    target_info TEXT NOT NULL, -- JSON string payload with swap details (days, week_index, etc.)
    status TEXT NOT NULL DEFAULT 'PENDING', -- 'PENDING', 'APPROVED', 'REJECTED'
    created_at TEXT NOT NULL,
    FOREIGN KEY(requester_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(target_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS deep_clean_logs (
    log_date TEXT NOT NULL,
    item_key TEXT NOT NULL,
    is_completed BOOLEAN NOT NULL DEFAULT 0,
    completed_by INT NULL,
    completed_at TEXT NULL,
    PRIMARY KEY(log_date, item_key),
    FOREIGN KEY(completed_by) REFERENCES users(id) ON DELETE SET NULL
);
