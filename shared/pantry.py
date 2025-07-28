import sqlite3
from typing import List

DB_PATH = "preprn.db"
TABLE_NAME = "pantry_items"

def init_pantry_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            item TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def get_pantry_items(user_id: int) -> List[str]:
    """Fetch all pantry items for this user."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(f"""
        SELECT item
          FROM {TABLE_NAME}
         WHERE user_id = ?
         ORDER BY item
    """, (user_id,))
    rows = [row[0] for row in cur.fetchall()]
    conn.close()
    return rows

def add_pantry_item(user_id: int, item_name: str) -> None:
    """Insert a new pantry item (if it doesn’t already exist)."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # avoid exact duplicates
    cur.execute(f"""
        SELECT 1 FROM {TABLE_NAME}
         WHERE user_id = ? AND item = ?
    """, (user_id, item_name))
    if not cur.fetchone():
        cur.execute(f"""
            INSERT INTO {TABLE_NAME} (user_id, item)
            VALUES (?, ?)
        """, (user_id, item_name))
    conn.commit()
    conn.close()

def remove_pantry_item(user_id: int, item_name: str) -> None:
    """Delete one pantry item by name."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(f"""
        DELETE FROM {TABLE_NAME}
         WHERE user_id = ? AND item = ?
    """, (user_id, item_name))
    conn.commit()
    conn.close()