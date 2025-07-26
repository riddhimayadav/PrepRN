import sqlite3
from typing import List, Dict, Any

def init_db(path: str) -> sqlite3.Connection:
    """Initialize the SQLite database and tables if they don't exist."""
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    # Table to track user requests 
    cur.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            budget REAL NOT NULL,
            servings INTEGER NOT NULL,
            diets TEXT
        )
    ''')
    # Table to store meals generated from a request
    cur.execute('''
        CREATE TABLE IF NOT EXISTS meals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL,
            title TEXT,
            price REAL,
            diets TEXT,
            summary TEXT,
            source_url TEXT,
            loved INTEGER DEFAULT 0,
            FOREIGN KEY(request_id) REFERENCES requests(id)
        )
    ''')

    add_loved_column_to_meals(conn)
    
    # Table to store meals generated from a request
    cur.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL,
            satisfied BOOLEAN NOT NULL,
            comments TEXT,
            FOREIGN KEY(request_id) REFERENCES requests(id)
        )
    ''')
    # Table to store Gemini-generated local store suggestions
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


def add_loved_column_to_meals(conn: sqlite3.Connection) -> None:
    """Add loved column to meals table if it doesn't exist."""
    cur = conn.cursor()
    try:
        cur.execute('ALTER TABLE meals ADD COLUMN loved INTEGER DEFAULT 0')
        conn.commit()
    except sqlite3.OperationalError:
        # Column already exists
        pass


def toggle_meal_love_status(conn: sqlite3.Connection, user_id: int, meal_name: str, meal_url: str) -> bool:
    """Toggle the love status of a meal for a user and return the new status."""
    cur = conn.cursor()
    
    # First, find the meal in the user's saved meals
    cur.execute('''
        SELECT meals.id, meals.loved
        FROM meals
        JOIN requests ON meals.request_id = requests.id
        WHERE requests.user_id = ? AND meals.title = ? AND meals.source_url = ?
        LIMIT 1
    ''', (user_id, meal_name, meal_url))
    
    result = cur.fetchone()
    
    if result:
        meal_id, current_loved_status = result
        # Toggle the loved status
        new_loved_status = 1 if current_loved_status == 0 else 0
        
        cur.execute('''
            UPDATE meals SET loved = ? WHERE id = ?
        ''', (new_loved_status, meal_id))
        
        conn.commit()
        return bool(new_loved_status)
    
    return False


def get_user_loved_meals(conn: sqlite3.Connection, user_id: int) -> List[tuple]:
    """Retrieve all loved meals for a user."""
    cur = conn.cursor()
    cur.execute('''
        SELECT meals.title, meals.price, meals.summary, meals.source_url
        FROM meals
        JOIN requests ON meals.request_id = requests.id
        WHERE requests.user_id = ? AND meals.loved = 1
        ORDER BY meals.id DESC
    ''', (user_id,))
    return cur.fetchall()


# Save a meal request and return the ID of the newly created request row
def save_request(
    conn: sqlite3.Connection, user_id: int, budget: float, servings: int, diets: List[str]
) -> int:
    """Save a meal-plan request (including servings) and return its ID."""
    diets_str = ','.join(diets)
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO requests (user_id, budget, servings, diets) VALUES (?, ?, ?, ?)',
        (user_id, budget, servings, diets_str)
    )
    conn.commit()
    return cur.lastrowid


# Save a batch of meal records linked to a request
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


# Save user feedback for a specific request
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


# Save Gemini-generated store suggestions for a given request
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


# Retrieve all saved meals for a given user
def get_saved_meals(conn: sqlite3.Connection, user_id: int) -> List[tuple]:
    """Retrieve all saved meals for a user, joined with request metadata."""
    cur = conn.cursor()
    cur.execute('''
        SELECT meals.title, meals.price, meals.summary, meals.source_url, meals.loved
        FROM meals
        JOIN requests ON meals.request_id = requests.id
        WHERE requests.user_id = ?
        ORDER BY meals.id DESC
    ''', (user_id,))
    return cur.fetchall()


def clear_loved_meals_db(conn: sqlite3.Connection, user_id: int) -> None:
    """Clear all loved meals for a user by setting loved = 0."""
    cur = conn.cursor()
    cur.execute('''
        UPDATE meals SET loved = 0 
        WHERE request_id IN (
            SELECT id FROM requests WHERE user_id = ?
        )
    ''', (user_id,))
    conn.commit()


# Delete all meals (and requests) associated with a user
def clear_meals(conn: sqlite3.Connection, user_id: int) -> None:
    """Delete all meals and related requests for a user."""
    cur = conn.cursor()
    # Get all request IDs associated with this user
    cur.execute('SELECT id FROM requests WHERE user_id = ?', (user_id,))
    request_ids = [row[0] for row in cur.fetchall()]

    if request_ids:
        # Delete meals linked to these requests
        cur.execute(
            f'DELETE FROM meals WHERE request_id IN ({",".join("?" * len(request_ids))})',
            request_ids
        )
        # Optionally delete the requests themselves
        cur.execute(
            f'DELETE FROM requests WHERE id IN ({",".join("?" * len(request_ids))})',
            request_ids
        )
    conn.commit()