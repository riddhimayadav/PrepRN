# Import SQLite and internal PrepnGo modules
import sqlite3
from prepngo.PrepnGo import main as run_prepngo_main
from prepngo.database_functions import *
from FoodiesRN.run_foodiesrn import engine
from sqlalchemy import text


# Run the PrepnGo meal planner and return the meal results

def get_prepngo_meals(user_input, user_id):
    results = run_prepngo_main(user_input)
    meals   = results.get("meals", [])

    for m in meals:
        # --- locate the recipe ID ---
        # adjust this if your meal dict uses a different key
        recipe_id = m.get("id") or m.get("spoon_id")
        if not recipe_id:
            # if you encoded the ID in the URL, you could parse it out:
            #   recipe_id = extract_from(m.get("source_url"))
            m["ingredients"]  = []
            m["instructions"] = []
            continue

        # --- fetch the full recipe information ---
        info = requests.get(
            f"https://api.spoonacular.com/recipes/{recipe_id}/information",
            params={"apiKey": SPOON_KEY, "includeNutrition": False}
        ).json()

        # pull ingredient lines
        m["ingredients"] = [
            ing.get("original", "").strip()
            for ing in info.get("extendedIngredients", [])
        ]

        # pull step‑by‑step instructions
        instr = []
        for block in info.get("analyzedInstructions", []):
            for step in block.get("steps", []):
                text = step.get("step", "").strip()
                if text:
                    instr.append(text)
        m["instructions"] = instr

    results["meals"] = meals
    return results



# Save meal results and associated request data into the database
def save_prepngo_results(meals, user_input, user_id):
    migrate_meals_notes_table()

    for m in meals:
        # build step list
        instr_blocks = m.get("analyzedInstructions", [])
        steps = [s["step"]
                 for b in instr_blocks
                 for s in b.get("steps", [])]
        m["instructions"] = json.dumps(steps)

        # build ingredients list
        ingr = m.get("extendedIngredients", [])
        m["ingredients"] = json.dumps([i["original"] for i in ingr])

        m["user_id"] = user_id

    conn = init_db('preprn.db')
    req_id = save_request(...)
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
        conn.execute(text("""
            UPDATE meals 
               SET notes = :notes 
             WHERE user_id = :uid AND title = :title
        """), {"notes": notes, "uid": user_id, "title": title})
        conn.commit()

def get_meal_notes(user_id, title):
    migrate_meals_notes_table()
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT notes 
              FROM meals 
             WHERE user_id = :uid AND title = :title
        """), {"uid": user_id, "title": title}).fetchone()
    return row[0] if row else ""