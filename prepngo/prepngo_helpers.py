import os
import requests
import sqlite3
import json
from sqlalchemy import text
import re
from prepngo.PrepnGo import main as run_prepngo_main
from prepngo.database_functions import (
    init_db,
    save_request,
    save_meals,
    get_saved_meals,
    clear_loved_meals_db as clear_loved_db,
    clear_meals,
    toggle_meal_love_status,
    get_user_loved_meals,
)
from FoodiesRN.run_foodiesrn import engine
import logging


# Make sure your SPOON_API_KEY is loaded into the env
SPOON_KEY = os.getenv("SPOON_API_KEY")
if not SPOON_KEY:
    raise RuntimeError("SPOON_API_KEY not set in environment")

def get_prepngo_meals(user_input, user_id):
    """
    Runs your PrepnGo logic, then enriches each meal with ingredients
    & instructions by hitting Spoonacular’s /information endpoint.
    If no explicit `id` field, we parse it from the source_url.
    """
    results = run_prepngo_main(user_input)
    meals   = results.get("meals", [])

    for m in meals:
        # 1) try explicit id keys
        recipe_id = m.get("id") or m.get("spoon_id")

        # 2) fallback: parse from URL, e.g. "…/recipe/W62QWGP6/…"
        if not recipe_id and m.get("source_url"):
            match = re.search(r"/recipe/([^/]+)/", m["source_url"])
            if match:
                recipe_id = match.group(1)

        if not recipe_id:
            logging.warning(f"⚠️  No recipe_id for {m.get('title')}")
            m["ingredients"]  = []
            m["instructions"] = []
            continue

        # 3) fetch full info
        try:
            resp = requests.get(
                f"https://api.spoonacular.com/recipes/{recipe_id}/information",
                params={"apiKey": SPOON_KEY, "includeNutrition": False},
                timeout=10
            )
            resp.raise_for_status()
            info = resp.json()
        except Exception:
            m["ingredients"]  = []
            m["instructions"] = []
            continue

        # 4) extract
        m["ingredients"] = [
            ing.get("original","").strip()
            for ing in info.get("extendedIngredients", [])
            if ing.get("original")
        ]
        steps = []
        for block in info.get("analyzedInstructions", []):
            for step in block.get("steps", []):
                txt = step.get("step","").strip()
                if txt:
                    steps.append(txt)
        m["instructions"] = steps

    results["meals"] = meals
    return results

def save_prepngo_results(meals, user_input, user_id):
    """
    If you still want to persist to your DB, you must serialize
    the Python lists back to JSON strings before saving.
    (But note: your session already has the real lists.)
    """
    # make sure your table has the needed columns
    migrate_meals_notes_table()

    # serialize before saving
    for m in meals:
        m["user_id"]      = user_id
        m["ingredients"]  = json.dumps(m.get("ingredients", []))
        m["instructions"] = json.dumps(m.get("instructions", []))

    conn  = init_db("preprn.db")
    # If grocery is disabled, use 0 as budget fallback
    budget_str = str(user_input.get("budget") or "0").strip()
    budget = float(budget_str) if budget_str else 0.0

    req_id = save_request(conn, user_id,
                        budget,
                        int(user_input.get("servings", 1)),
                        user_input.get("diets", []))

    save_meals(conn, req_id, meals)
    conn.close()

# Retrieve saved meal recommendations for a user
def get_saved_prepngo(user_id):
    conn = init_db('preprn.db')
    results = get_saved_meals(conn, user_id)
    conn.close()
    return results


def clear_loved_meals_db(user_id):
    """Clear all loved meals for a user"""
    conn = init_db('preprn.db')
    from prepngo.database_functions import clear_loved_meals_db as clear_loved_db
    clear_loved_db(conn, user_id)
    conn.close()


def delete_individual_meal(user_id, meal_title):
    """Delete a specific meal for a user"""
    conn = init_db('preprn.db')
    cur = conn.cursor()
    
    # Delete from meals table where the meal belongs to this user
    cur.execute('''
        DELETE FROM meals 
        WHERE title = ? AND request_id IN (
            SELECT id FROM requests WHERE user_id = ?
        )
    ''', (meal_title, user_id))
    
    conn.commit()
    conn.close()
    return True


# Clear all saved meal results for a user
def clear_saved_prepngo(user_id):
    conn = init_db('preprn.db')
    clear_meals(conn, user_id)
    conn.close()


# Toggle the love status of a meal for a user
def toggle_meal_love(user_id, meal_name, meal_url):
    conn = init_db('preprn.db')
    from prepngo.database_functions import toggle_meal_love_status
    loved_status = toggle_meal_love_status(conn, user_id, meal_name, meal_url)
    conn.close()
    return loved_status


# Get all loved meals for a user
def get_loved_meals(user_id):
    conn = init_db('preprn.db')
    from prepngo.database_functions import get_user_loved_meals
    loved_meals = get_user_loved_meals(conn, user_id)
    conn.close()
    return loved_meals

def migrate_meals_notes_table():
    """Add notes, instructions, shopping_list columns to meals table if missing."""
    with engine.connect() as conn:
        for col, typ in [
            ("notes",         "TEXT DEFAULT ''"),
            ("instructions",  "TEXT DEFAULT ''"),
            ("ingredients",   "TEXT DEFAULT ''"),
            ("user_id",       "INTEGER"),
        ]:
            try:
                conn.execute(text(f"SELECT {col} FROM meals LIMIT 1"))
            except Exception:
                conn.execute(text(f"ALTER TABLE meals ADD COLUMN {col} {typ}"))
                conn.commit()
                print(f"✅ Added `{col}` column.")

def update_meal_notes(user_id, title, notes):
    migrate_meals_notes_table()
    with engine.connect() as conn:
        # Fixed query: use JOIN to connect meals -> requests -> user_id
        result = conn.execute(text("""
            UPDATE meals 
               SET notes = :notes 
             WHERE title = :title 
               AND request_id IN (
                   SELECT id FROM requests WHERE user_id = :uid
               )
        """), {"notes": notes, "uid": user_id, "title": title})
        conn.commit()
        
        # Check if any rows were affected
        if result.rowcount > 0:
            print(f"[DEBUG] Successfully updated notes for meal '{title}' (user {user_id})")
            return True
        else:
            print(f"[DEBUG] No meal found with title '{title}' for user {user_id}")
            return False

def get_meal_notes(user_id, title):
    migrate_meals_notes_table()
    with engine.connect() as conn:
        # Fixed query: use JOIN to connect meals -> requests -> user_id
        row = conn.execute(text("""
            SELECT notes 
              FROM meals 
             WHERE title = :title 
               AND request_id IN (
                   SELECT id FROM requests WHERE user_id = :uid
               )
             LIMIT 1
        """), {"uid": user_id, "title": title}).fetchone()
    
    result = row[0] if row else ""
    print(f"[DEBUG] Retrieved notes for '{title}' (user {user_id}): '{result}'")
    return result