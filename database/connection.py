import os
import aiosqlite
from contextlib import asynccontextmanager
from config import settings

INITIAL_USERS = [
    (1, None, "Avazbek", 1, 0),
    (2, None, "Firdavs", 1, 0),
    (3, None, "Asadbek bro", 1, 0),
    (4, None, "Omadbek", 1, 0),
    (5, None, "Ilyosbek", 2, 0),
    (6, None, "Jaloliddin", 2, 0),
    (7, None, "Asadbek", 2, 0),
    (8, None, "Mavlonbek", 2, 0)
]


@asynccontextmanager
async def get_db():
    db = await aiosqlite.connect(settings.DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON;")
    try:
        yield db
    finally:
        await db.close()


async def init_db():
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    async with get_db() as db:
        await db.executescript(schema_sql)
        await db.commit()

        # Seed initial 8 flatmates if empty
        cursor = await db.execute("SELECT COUNT(*) as count FROM users")
        row = await cursor.fetchone()
        if row and row["count"] == 0:
            for u in INITIAL_USERS:
                await db.execute(
                    "INSERT INTO users (id, telegram_id, name, room_number, is_admin) VALUES (?, ?, ?, ?, ?)",
                    u
                )
            await db.commit()

        # Seed initial water state if empty
        cursor = await db.execute("SELECT COUNT(*) as count FROM water_state")
        row = await cursor.fetchone()
        if row and row["count"] == 0:
            await db.execute("INSERT INTO water_state (id, current_user_index) VALUES (1, 0)")
            await db.commit()
