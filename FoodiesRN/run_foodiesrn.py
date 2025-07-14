import requests
import os
import random
import google.generativeai as genai
import pandas as pd
import sqlalchemy as db
from sqlalchemy import inspect

YELP_KEY = os.getenv("YELP_KEY")
GENAI_KEY = os.getenv("GENAI_KEY")

engine = db.create_engine("sqlite:///preprn.db")
TABLE_RN = "foodiesrn_recommendations"


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


def generate_blurbs(businesses, user_input):
    prompt = (
        "Write a short, fun, Gen Z-style blurb for each of the following restaurants. "
        "Keep each blurb to 2–3 sentences max. Make each blurb exciting and positive. "
        "Separate each restaurant clearly using numbered format (1., 2., 3.).\n\n"
        "Also, based on your knowledge, what do people typically say about "
        f"the particular restuarant in {user_input['location']}?"
        "Only include positive traits, and explicitly write 'people are saying' add in what pros."
        "Add this one extra sentence to each blurb, don't create separate section."
    )

    for i, biz in enumerate(businesses, 1):
        prompt += (
            f"{i}.\n"
            f"Name: {biz['name']}\n"
            f"Cuisine: {user_input['cuisine']}\n"
            f"Price: {biz['price']}\n"
            f"Location: {biz['location']}\n"
            f"Vibe: {user_input['vibe']}\n\n"
        )

    response = model.generate_content(prompt)

    if response is None or not hasattr(response, "text") or not response.text.strip():
        return ["No blurb available."] * len(businesses)

    raw_blurbs = response.text.strip().split("\n")
    blurbs = []
    current = ""

    for line in raw_blurbs:
        if line.strip().startswith(tuple(str(i) + "." for i in range(1, len(businesses) + 1))):
            if current:
                blurbs.append(current.strip())
            current = line
        else:
            current += "\n" + line

    if current:
        blurbs.append(current.strip())

    while len(blurbs) < len(businesses):
        blurbs.append("No blurb available.")

    return blurbs


def clear_rec_table():
    with engine.connect() as connection:
        connection.execute(db.text(f"DELETE FROM {TABLE_RN}"))
        connection.commit()


def save_to_db(results, user_id):
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
                        (name, location, price, rating, url, user_location, cuisine, vibe, user_id)
                        VALUES (:name, :location, :price, :rating, :url, :user_location, :cuisine, :vibe, :user_id)
                    """),
                    r
                )
        connection.commit()


def view_saved_recommendations(user_id):
    with engine.connect() as connection:
        results = connection.execute(
            db.text(f"""
                SELECT name, location, rating, price, url 
                FROM {TABLE_RN} 
                WHERE user_id = :uid
            """),
            {"uid": user_id}
        ).fetchall()

    return results


def clear_saved_recommendations(user_id):
    with engine.connect() as connection:
        connection.execute(
            db.text(f"DELETE FROM {TABLE_RN} WHERE user_id = :uid"),
            {"uid": user_id}
        )
        connection.commit()
    print("\nAll your saved recommendations have been cleared.")


def run_restaurant_search(user_input, user_id):
    print("\n🔍 Generating your personalized recommendations...\n")
    results = search_yelp(user_input)

    if results:
        filtered_results = [r for r in results if r["rating"] > 3.5]
        if not filtered_results:
            return []
        num_recs = min(3, len(filtered_results))
        top_recs = random.sample(filtered_results, k=num_recs)

        blurbs = generate_blurbs(top_recs, user_input)

        for biz, blurb in zip(top_recs, blurbs):
            biz["blurb"] = blurb
            biz["user_location"] = user_input["location"]
            biz["cuisine"] = user_input["cuisine"]
            biz["vibe"] = user_input["vibe"]
            biz["user_id"] = user_id

        save_to_db(top_recs, user_id)
        return top_recs

    else:
        return []



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
