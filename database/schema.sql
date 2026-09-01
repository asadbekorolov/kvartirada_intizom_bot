-- SQLite Schema for Kvartira Bot

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

CREATE TABLE IF NOT EXISTS water_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    current_user_index INT NOT NULL DEFAULT 0 -- 0..7
);

CREATE TABLE IF NOT EXISTS water_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brought_by_user_id INT NOT NULL,
    photo_file_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(brought_by_user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS swap_requests (
    id TEXT PRIMARY KEY,
    requester_id INT NOT NULL,
    target_id INT NOT NULL,
    day_of_week INT NOT NULL,
    target_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING', -- PENDING, APPROVED, REJECTED
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
