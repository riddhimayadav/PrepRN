import sqlite3
from typing import List, Dict, Any

def init_db(path: str) -> sqlite3.Connection:
    """Initialize the SQLite database and tables if they don't exist."""
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            budget REAL NOT NULL,
            servings INTEGER NOT NULL,
            diets TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS meals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL,
            title TEXT,
            price REAL,
            diets TEXT,
            summary TEXT,
            source_url TEXT,
            FOREIGN KEY(request_id) REFERENCES requests(id)
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL,
            satisfied BOOLEAN NOT NULL,
            comments TEXT,
            FOREIGN KEY(request_id) REFERENCES requests(id)
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS local_stores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL,
            city TEXT,
            state TEXT,
            suggestions TEXT,
            FOREIGN KEY(request_id) REFERENCES requests(id)
        )
    ''')
    conn.commit()
    return conn

def save_request(
    conn: sqlite3.Connection, user_id: int, budget: float, servings: int, diets: List[str]
) -> int:
    """Save a meal-plan request (including servings) and return its ID."""
    diets_str = ','.join(diets)
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO requests (user_id, budget, servings, diets) VALUES (?, ?, ?)',
        (user_id, budget, servings, diets_str)
    )
    conn.commit()
    return cur.lastrowid

def save_meals(
    conn: sqlite3.Connection, request_id: int, meals: List[Dict[str, Any]]
) -> None:
    """Batch-insert generated meals for a given request."""
    cur = conn.cursor()
    for m in meals:
        cur.execute('''
            INSERT INTO meals
                (request_id, title, price, diets, summary, source_url)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            request_id,
            m['title'],
            m['price'],
            ','.join(m['diets']),
            m['summary'],
            m['source_url'],
        ))
    conn.commit()


def save_feedback(
    conn: sqlite3.Connection, request_id: int, satisfied: bool, comments: str
) -> None:
    """Save end-of-flow user feedback."""
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO feedback (request_id, satisfied, comments) VALUES (?, ?, ?)',
        (request_id, int(satisfied), comments)
    )
    conn.commit()
def save_local_stores(
    conn: sqlite3.Connection, request_id: int, city: str, state: str, suggestions: str
) -> None:
    """Save Gemini's local store suggestions linked to a request."""
    cur = conn.cursor()
    cur.execute(
        '''
        INSERT INTO local_stores (request_id, city, state, suggestions)
        VALUES (?, ?, ?, ?)
        ''',
        (request_id, city, state, suggestions)
    )
    conn.commit()