# Import SQLite and internal PrepnGo modules
import sqlite3
from prepngo.PrepnGo import main as run_prepngo_main
from prepngo.database_functions import init_db, save_request, save_meals, get_saved_meals, clear_meals


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


# Clear all saved meal results for a user
def clear_saved_prepngo(user_id):
    conn = init_db('preprn.db')
    clear_meals(conn, user_id)
    conn.close()
