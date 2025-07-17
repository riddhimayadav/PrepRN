import requests
import os
import random
import google.generativeai as genai
import pandas as pd
import sqlalchemy as db
from sqlalchemy import inspect
from dotenv import load_dotenv
from genai_utils import get_genai_model
import time


# Load environment variables
load_dotenv()
YELP_KEY = os.getenv("YELP_KEY")
GENAI_KEY = os.getenv("GENAI_KEY")
print("GENAI_KEY in Flask:", GENAI_KEY)


# Set up SQLAlchemy database engine
engine = db.create_engine("sqlite:///preprn.db")
TABLE_RN = "foodiesrn_recommendations" # Table name for storing recommendations


def create_foodiesrn_table():
    """Create the foodiesrn_recommendations table if it doesn't exist"""
    with engine.connect() as connection:
        connection.execute(db.text(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_RN} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                location TEXT,
                price TEXT,
                rating REAL,
                url TEXT,
                user_location TEXT,
                cuisine TEXT,
                vibe TEXT,
                user_id INTEGER,
                image_url TEXT
            )
        """))
        connection.commit()


# Prompt user repeatedly until they enter a valid input
def get_valid_input(prompt, valid_options):
    while True:
        user_input = input(prompt).capitalize()
        if user_input in valid_options:
            return user_input
        print("Invalid input. Please choose from:", ", ".join(valid_options))


# Collect restaurant search preferences from the user via CLI
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


# Yelp uses numbers for price ranges
price_map = {
    "$": "1",
    "$$": "2",
    "$$$": "3",
    "$$$$": "4"
}


# Yelp API call to search for restaurants based on user input
# https://docs.developer.yelp.com/reference/v3_business_search
def search_yelp(user_input):
    headers = {
        "Authorization": f"Bearer {YELP_KEY}"
    }

    params = {
        "location": user_input["location"],
        "term": f"{user_input['cuisine']} {user_input['vibe']}",
        "categories": (user_input.get("cuisine") or "").lower(),
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
                "url": biz["url"],
                "image_url": biz.get("image_url", "")
            })

        # this will eventually be sent to google genai after final selection
        return results

    else:
        print("Yelp API Error:", response.status_code)
        print(response.text)
        return []


# Generate GenAI-powered blurbs for each restaurant
def generate_blurbs(businesses, user_input):
    model = get_genai_model(GENAI_KEY, model_name="gemini-1.5-flash")

    prompt = (
        "Write short, Gen Z-style blurbs (2 sentences) numbered (1., 2., 3.). "
        "No restaurant names. No emojis. Include 'people are saying' with your positive opnions.\n\n"
    )

    for i, biz in enumerate(businesses, 1):
        prompt += (
            f"{i}.\n"
            f"Name: {biz['name']}\n"
            f"Location: {biz['location']}\n"
            f"Vibe: {user_input['vibe']}\n\n"
        )

    response_chunks = model.generate_content(prompt, stream=True)

    full_text = ""
    for chunk in response_chunks:
        if hasattr(chunk, "text"):
            full_text += chunk.text

    if not full_text.strip():
        return ["No blurb available."] * len(businesses)


    raw_blurbs = full_text.strip().split("\n\n")
    blurbs = []

    for blurb in raw_blurbs:
        if "." in blurb:
            parts = blurb.split(".", 1)
            if len(parts) == 2:
                blurbs.append(parts[1].strip())
            else:
                blurbs.append(blurb.strip())
        else:
            blurbs.append(blurb.strip())

    # Ensure we return the same number of blurbs as restaurants
    while len(blurbs) < len(businesses):
        blurbs.append("No blurb available.")

    return blurbs


# Clear all saved restaurant recommendations in the DB
def clear_rec_table():
    create_foodiesrn_table()
    with engine.connect() as connection:
        connection.execute(db.text(f"DELETE FROM {TABLE_RN}"))
        connection.commit()


# Save new results to the DB only if they don’t already exist
def save_to_db(results, user_id):
    create_foodiesrn_table()
    with engine.connect() as connection:
        for r in results:
            exists = connection.execute(
                db.text(f"""
                    SELECT 1 FROM {TABLE_RN} 
                    WHERE user_id = :uid AND name = :name
                """),
                {"uid": user_id, "name": r["name"]}
            ).fetchone()

            if not exists:
                connection.execute(
                    db.text(f"""
                        INSERT INTO {TABLE_RN} 
                        (name, location, price, rating, url, user_location, cuisine, vibe, user_id, image_url)
                        VALUES (:name, :location, :price, :rating, :url, :user_location, :cuisine, :vibe, :user_id, :image_url)
                    """),
                    r
                )
        connection.commit()


# Retrieve previously saved recommendations from the DB
def view_saved_recommendations(user_id):
    create_foodiesrn_table()
    with engine.connect() as connection:
        results = connection.execute(
            db.text(f"""
                SELECT name, location, rating, price, url, image_url
                FROM {TABLE_RN} 
                WHERE user_id = :uid
            """),
            {"uid": user_id}
        ).fetchall()
    
    if results:
        return results

    return results


# Remove all saved recommendations for a specific user
def clear_saved_recommendations(user_id):
    create_foodiesrn_table()
    with engine.connect() as connection:
        connection.execute(
            db.text(f"DELETE FROM {TABLE_RN} WHERE user_id = :uid"),
            {"uid": user_id}
        )
        connection.commit()
    print("\nAll your saved recommendations have been cleared.")


# Main function to run Yelp + GenAI-based restaurant recommendation pipeline
def run_restaurant_search(user_input, user_id):
    print("\n🔍 Generating your personalized recommendations...\n")
    start = time.time()
    results = search_yelp(user_input)
    print(f"[TIMER] Yelp API took {time.time() - start:.2f} seconds")

    if results:
        filtered_results = [r for r in results if r["rating"] > 3.5]
        if not filtered_results:
            return []
        num_recs = min(3, len(filtered_results))
        top_recs = random.sample(filtered_results, k=num_recs)

        start = time.time()
        blurbs = generate_blurbs(top_recs, user_input)
        print(f"[TIMER] GenAI API took {time.time() - start:.2f} seconds")

        for biz, blurb in zip(top_recs, blurbs):
            biz["blurb"] = blurb
            biz["user_location"] = user_input["location"]
            biz["cuisine"] = user_input["cuisine"]
            biz["vibe"] = user_input["vibe"]
            biz["user_id"] = user_id
            biz["image_url"] = biz.get("image_url", "")

        save_to_db(top_recs, user_id)
        return top_recs

    else:
        return []


# CLI interface for the FoodiesRN module
def run_food_module(user_id):
    session_recs = []

    while True:
        menu_choice = get_valid_input(
            "\nWhat would you like to do? (view/search/clear/exit): ",
            ["View", "Search", "Clear", "Exit"]
        ).lower()

        if menu_choice == "exit":
            print("\nThanks for using PrepRN! Goodbye 👋")
            break

        sub_choice = get_valid_input(
            "Which category? (restaurant/prep): ",
            ["Restaurant", "Prep"]
        ).lower()

        if sub_choice == "restaurant":
            if menu_choice == "view":
                view_saved_recommendations(user_id)

            elif menu_choice == "search":
                run_restaurant_search(user_id, session_recs)

            elif menu_choice == "clear":
                confirm = get_valid_input(
                    "Are you sure you want to delete all restaurant recommendations? (yes/no): ",
                    ["Yes", "No"]
                ).lower()
                if confirm == "yes":
                    clear_saved_recommendations(user_id)

            else:
                print("Invalid option.\n")

        elif sub_choice == "prep":
            print("🚧 PrepNGo feature is under construction 🛠️\n")

        else:
            print("Invalid category. Please choose 'restaurant' or 'prep'.\n")
