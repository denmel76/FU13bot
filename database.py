import aiosqlite

DB_NAME = "consult.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                limit_count INTEGER DEFAULT 10
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                role TEXT,
                content TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                question TEXT,
                answer TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

async def get_user(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT limit_count FROM users WHERE user_id = ?", (user_id,))
        user = await cursor.fetchone()
        if not user:
            await db.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
            await db.commit()
            return (10,)
        return user

async def update_limit(user_id, amount):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET limit_count = limit_count + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()

async def add_history(user_id, role, content):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO history (user_id, role, content) VALUES (?, ?, ?)", (user_id, role, content))
        await db.commit()

async def get_history(user_id, limit=10):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT role, content FROM history WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit))
        rows = await cursor.fetchall()
        return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

async def clear_history(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM history WHERE user_id = ?", (user_id,))
        await db.commit()

async def save_log(user_id, username, question, answer):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO logs (user_id, username, question, answer) VALUES (?, ?, ?, ?)", (user_id, username, question, answer))
        await db.commit()

async def get_logs(limit=20):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT username, question, answer, created_at FROM logs ORDER BY id DESC LIMIT ?", (limit,))
        return await cursor.fetchall()
