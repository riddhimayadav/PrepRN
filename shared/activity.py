import sqlite3
from typing import List, Dict
from prepngo.database_functions import init_db, get_saved_meals
from FoodiesRN.run_foodiesrn import create_foodiesrn_table, view_saved_recommendations

DB_PATH = "preprn.db"

def get_recent_recipes(user_id: int, days: int = 7) -> List[Dict]:
    """
    Return up to the last `days` days of cooked recipes.
    For simplicity we'll just grab the last `n` saved meals.
    """
    conn = sqlite3.connect(DB_PATH)
    # initialize tables if needed
    init_db(DB_PATH)
    rows = get_saved_meals(conn, user_id)
    conn.close()
    # rows are tuples (title, price, summary, source_url, loved)
    recent = []
    for title, price, summary, url, loved in rows[-5:]:
        recent.append({"title": title})
    return recent

def get_recent_liked_restaurants(user_id: int, days: int = 7) -> List[Dict]:
    """
    Return restaurants the user has 'loved' in the last `days`.
    We'll just pull all with loved=TRUE.
    """
    create_foodiesrn_table()
    all_saved = view_saved_recommendations(user_id)
    # all_saved are RowProxy with .loved field at index -1
    liked = []
    for r in all_saved:
        if getattr(r, "loved", False):
            liked.append({"name": r.name})
    return liked
