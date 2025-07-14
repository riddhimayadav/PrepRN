import sqlite3

def get_prepngo_meals(user_id):
    conn = sqlite3.connect('preprn.db')
    cur = conn.cursor()
    cur.execute("""
        SELECT title, price, summary, source_url
        FROM meals
        WHERE request_id IN (SELECT id FROM requests WHERE user_id = ?)
    """, (user_id,))
    meals = cur.fetchall()
    conn.close()
    return meals
