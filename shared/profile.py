import sqlite3
from typing import List, Tuple

DB_PATH = "preprn.db"
TABLE = "user_profile"

def _connect():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # ensure table exists
    cur.execute(f"""
      CREATE TABLE IF NOT EXISTS {TABLE} (
        user_id        INTEGER PRIMARY KEY,
        restrictions   TEXT    DEFAULT '',
        weekly_budget  REAL    DEFAULT 0.0,
        daily_percent  REAL    DEFAULT 0.5
      )
    """)
    conn.commit()
    return conn, cur

def get_user_restrictions(user_id: int) -> List[str]:
    conn, cur = _connect()
    cur.execute(f"SELECT restrictions FROM {TABLE} WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    if not row:
        cur.execute(f"INSERT INTO {TABLE}(user_id) VALUES(?)", (user_id,))
        conn.commit()
        res = []
    else:
        res = [r for r in row[0].split(",") if r]
    conn.close()
    return res

def set_user_restrictions(user_id: int, restrictions: List[str]) -> None:
    conn, cur = _connect()
    cur.execute(f"""
      UPDATE {TABLE}
         SET restrictions = ?
       WHERE user_id = ?
    """, (",".join(restrictions), user_id))
    conn.commit()
    conn.close()

# def get_weekly_budget(user_id: int) -> float:
#     conn, cur = _connect()
#     cur.execute(f"SELECT weekly_budget FROM {TABLE} WHERE user_id = ?", (user_id,))
#     row = cur.fetchone()
#     if not row:
#         cur.execute(f"INSERT INTO {TABLE}(user_id) VALUES(?)", (user_id,))
#         conn.commit()
#         val = 0.0
#     else:
#         val = row[0] or 0.0
#     conn.close()
#     return val

# def set_weekly_budget(user_id: int, budget: float) -> None:
#     conn, cur = _connect()
#     cur.execute(f"""
#       UPDATE {TABLE}
#          SET weekly_budget = ?
#        WHERE user_id = ?
#     """, (budget, user_id))
#     conn.commit()
#     conn.close()

# def get_daily_allocation(user_id: int) -> float:
#     conn, cur = _connect()
#     cur.execute(f"SELECT daily_percent FROM {TABLE} WHERE user_id = ?", (user_id,))
#     row = cur.fetchone()
#     if not row:
#         cur.execute(f"INSERT INTO {TABLE}(user_id) VALUES(?)", (user_id,))
#         conn.commit()
#         pct = 0.5
#     else:
#         pct = row[0] or 0.5
#     conn.close()
#     return pct

# def set_daily_allocation(user_id: int, pct: float) -> None:
#     conn, cur = _connect()
#     cur.execute(f"""
#       UPDATE {TABLE}
#          SET daily_percent = ?
#        WHERE user_id = ?
#     """, (pct, user_id))
#     conn.commit()
#     conn.close()
