import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "wallet.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            balance_usd REAL NOT NULL DEFAULT 0.0,
            initial_balance_usd REAL NOT NULL DEFAULT 0.0
        );
    """)
    cur.execute("PRAGMA table_info(users)")
    cols = [c[1] for c in cur.fetchall()]
    if "initial_balance_usd" not in cols:
        cur.execute(
            "ALTER TABLE users ADD COLUMN initial_balance_usd REAL NOT NULL DEFAULT 0.0"
        )
        cur.execute(
            "UPDATE users SET initial_balance_usd = balance_usd WHERE initial_balance_usd = 0.0"
        )
    conn.commit()
    conn.close()


def create_user(username: str, start_balance: float = 0.05):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR IGNORE INTO users (username, balance_usd, initial_balance_usd)
        VALUES (?, ?, ?)
    """,
        (username, start_balance, start_balance),
    )
    conn.commit()
    conn.close()


def get_balance(username: str) -> float:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT balance_usd FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0.0


def deduct_balance(username: str, amount: float):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT balance_usd FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return False
    current = row[0]
    if current < amount:
        conn.close()
        return False
    new_balance = round(current - amount, 6)
    cur.execute(
        "UPDATE users SET balance_usd=? WHERE username=?", (new_balance, username)
    )
    conn.commit()
    conn.close()
    return new_balance


def get_user_info(username: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT balance_usd, initial_balance_usd FROM users WHERE username=?",
        (username,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {"balance_usd": row[0], "initial_balance_usd": row[1]}
