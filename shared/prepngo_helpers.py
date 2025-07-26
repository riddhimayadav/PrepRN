# Import SQLite and internal PrepnGo modules
import sqlite3
from prepngo.PrepnGo import main as run_prepngo_main
from prepngo.database_functions import *


# Run the PrepnGo meal planner and return the meal results
def get_prepngo_meals(user_input, user_id):
    meals = run_prepngo_main(user_input)
    return meals


# Save meal results and associated request data into the database
def save_prepngo_results(meals, user_input, user_id):
    conn = init_db('preprn.db')
    req_id = save_request(conn, user_id, float(user_input['budget']), int(user_input['servings']), user_input.get('diets', []))
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
