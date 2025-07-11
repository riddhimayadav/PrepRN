import requests
import os
import random
import google.generativeai as genai
import pandas as pd
import sqlalchemy as db
from sqlalchemy import inspect

YELP_KEY = os.getenv("YELP_KEY")
GENAI_KEY = os.getenv("GENAI_KEY")


# reprompts if not valid input
def get_valid_input(prompt, valid_options):
    while True:
        user_input = input(prompt).capitalize()
        if user_input in valid_options:
            return user_input
        print("Invalid input. Please choose from:", ", ".join(valid_options))


# getting user input
def get_user_input():

    location = input("\nEnter your city (e.g., Austin, TX): ")

    cuisines = [
        "Thai", "Mexican", "Vegan", "American", "Chinese",
        "Barbeque", "Greek", "Indian", "Italian"
    ]
    print("Choose a cuisine from the following options:", ", ".join(cuisines))
    cuisine = get_valid_input("Cuisine: ", cuisines)

    prices = ["$", "$$", "$$$", "$$$$"]
    print("Choose a price range:", ", ".join(prices))
    price = get_valid_input("Price: ", prices)

    vibes = ["Cozy", "Trendy", "Romantic", "Casual"]
    print("Choose a vibe:", ", ".join(vibes))
    vibe = get_valid_input("Vibe: ", vibes)

    return {
        "location": location,
        "cuisine": cuisine,
        "price": price,
        "vibe": vibe
    }

# in yelp api search, prices are passed as numbers


price_map = {
    "$": "1",
    "$$": "2",
    "$$$": "3",
    "$$$$": "4"
}


# yelp api call

# https://docs.developer.yelp.com/reference/v3_business_search


def search_yelp(user_input):
    headers = {
        "Authorization": f"Bearer {YELP_KEY}"
    }

    params = {
        "location": user_input["location"],
        "term": f"{user_input['cuisine']} {user_input['vibe']}",
        "categories": user_input["cuisine"].lower(),
        "price": price_map[user_input["price"]],
        "limit": 10
    }

    url = "https://api.yelp.com/v3/businesses/search"
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()
        businesses = data['businesses']

        # just extract the fields we need
        results = []
        for biz in businesses:
            results.append({
                "name": biz["name"],
                "rating": biz["rating"],
                "price": biz.get("price", "N/A"),
                "location": ", ".join(
                    biz["location"].get("display_address", [])
                ),
                "url": biz["url"]
            })

        # this will eventually be sent to google genai after final selection
        return results

    else:
        print("Yelp API Error:", response.status_code)
        print(response.text)
        return []


# return food blurb for user display

genai.configure(api_key=GENAI_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")


def generate_blurb(business, user_input):
    prompt = (
        "Write a fun, personality-filled blurb using Gen Z Lingo "
        "for this restaurant:\n\n"
        "Only return the blurb – do not explain anything or "
        "include headings or bullet points.\n\n"
        f"Name: {business['name']}\n"
        f"Cuisine: {user_input['cuisine']}\n"
        f"Price: {user_input['price']}\n"
        f"Location: {user_input['location']}\n"
        f"Vibe: {user_input['vibe']}\n\n"
        f"Explain why it fits someone looking for a "
        f"{user_input['vibe']} experience."
        "Also, based on your knowledge, what do people typically say about "
        f"{business['name']} in {user_input['location']}?"
        "Only include positive traits, and explicitly write 'people are saying' add in what pros."
    )

    response = model.generate_content(prompt)

    if response is None or not hasattr(response, "text") or not response.text.strip():
        return (
            f"{business['name']} fits the {user_input['vibe']} vibe and is popular for a reason. "
            "People are saying it’s a go-to spot with great energy and good eats!"
        )

    return response.text.strip()


engine = db.create_engine('sqlite:///recommendations.db')
inspector = inspect(engine)

def create_user_table():
    with engine.connect() as connection:
        connection.execute(db.text("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
        """))
        connection.commit()


def clear_rec_table():
    with engine.connect() as connection:
        connection.execute(db.text("DELETE FROM recommendations"))
        connection.commit()


def save_to_db(results, user_id):
    df = pd.DataFrame(results)
    df["user_id"] = user_id
    df.to_sql("recommendations", con=engine, if_exists="append", index=False)


def view_saved_recommendations(user_id):
    with engine.connect() as connection:
        results = connection.execute(
            db.text("""
                SELECT name, location, rating, price, url 
                FROM recommendations 
                WHERE user_id = :uid
            """),
            {"uid": user_id}
        ).fetchall()

        if results:
            print("\nYour Saved Recommendations:")
            print("-" * 40)
            for r in results:
                print(f"{r.name} – {r.location}")
                print(f"Rating: {r.rating} | Price: {r.price}")
                print(f"Yelp URL: {r.url}")
                print("-" * 40)
        else:
            print("\nYou don't have any saved recommendations yet.")


def clear_saved_recommendations(user_id):
    with engine.connect() as connection:
        connection.execute(
            db.text("DELETE FROM recommendations WHERE user_id = :uid"),
            {"uid": user_id}
        )
        connection.commit()
    print("\nAll your saved recommendations have been cleared.")


def add_user():
    while True:
        username = input("Choose a username: ").strip()
        password = input("Choose a password: ").strip()

        with engine.connect() as connection:
            result = connection.execute(
                db.text("SELECT * FROM users WHERE username = :u"),
                {"u": username}
            ).fetchone()

            if result:
                print("Username already exists. Try a different one.\n")
            else:
                connection.execute(db.text(
                    "INSERT INTO users (username, password) VALUES (:u, :p)"
                ), {"u": username, "p": password})
                connection.commit()
                print("Account created successfully!\n")
                return username


def verify_user():
    while True:
        username = input("Username: ").strip()

        with engine.connect() as connection:
            user_exists = connection.execute(
                db.text("SELECT * FROM users WHERE username = :u"),
                {"u": username}
            ).fetchone()

        if not user_exists:
            choice = get_valid_input(
                "Username not found. Do you want to try again or sign up? (login/signup): ",
                ["Login", "Signup"]
            )
            if choice.lower() == "signup":
                return add_user()
            else:
                continue

        while True:
            password = input("Password: ").strip()

            with engine.connect() as connection:
                correct_credentials = connection.execute(
                    db.text("SELECT * FROM users WHERE username = :u AND password = :p"),
                    {"u": username, "p": password}
                ).fetchone()

            if correct_credentials:
                print("Login successful!\n")
                return username
            else:
                print("Incorrect password. Try again.\n")


def get_user_id(username):
    with engine.connect() as connection:
        result = connection.execute(
            db.text("SELECT id FROM users WHERE username = :u"),
            {"u": username}
        ).fetchone()
        return result[0] if result else None


def run_foodiesrn():
    create_user_table()

    print("\nWelcome to FoodiesRN!\n")
    action = get_valid_input("Do you want to log in or sign up? (login/signup): ", ["Login", "Signup"])

    if action.lower() == "signup":
        username = add_user()
    else:
        username = verify_user()

    user_id = get_user_id(username)
    session_recs = []

    while True:
        menu_choice = get_valid_input(
            "\nWhat would you like to do? (view/search/clear/exit): ",
            ["View", "Search", "Clear", "Exit"]
        )

        if menu_choice.lower() == "view":
            view_saved_recommendations(user_id)

        elif menu_choice.lower() == "search":
            user_input = get_user_input()
            results = search_yelp(user_input)

            if results:
                filtered_results = [r for r in results if r["rating"] > 3.5]
                num_recs = min(3, len(filtered_results))
                top_recs = random.sample(filtered_results, k=num_recs)

                for biz in top_recs:
                    blurb = generate_blurb(biz, user_input)

                    print(f"\n{biz['name']} – {biz['location']}")
                    print(f"Rating: {biz['rating']} | Price: {biz['price']}")
                    print()
                    print(blurb)
                    print()
                    print(f"Yelp URL: {biz['url']}")
                    print("-" * 40)

                    session_recs.append({
                        "name": biz["name"],
                        "location": biz["location"],
                        "price": biz["price"],
                        "rating": biz["rating"],
                        "url": biz["url"],
                        "user_location": user_input["location"],
                        "cuisine": user_input["cuisine"],
                        "vibe": user_input["vibe"],
                        "user_id": user_id
                    })

                if session_recs:
                    save_to_db(session_recs, user_id)
                    session_recs.clear()

            else:
                print("No matches found. Try adjusting your preferences.")

        elif menu_choice.lower() == "clear":
            confirm = get_valid_input(
                "Are you sure you want to delete all saved recommendations? (yes/no): ",
                ["Yes", "No"]
            )
            if confirm.lower() == "yes":
                clear_saved_recommendations(user_id)

        else:
            print("\nThanks for using FoodiesRN! Goodbye 👋")
            break
