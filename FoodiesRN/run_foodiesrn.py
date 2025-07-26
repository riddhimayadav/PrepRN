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
import json


# Load environment variables
load_dotenv()
YELP_KEY = os.getenv("YELP_KEY")
GENAI_KEY = os.getenv("GENAI_KEY")
print("GENAI_KEY in Flask:", GENAI_KEY)
GEOAPIFY_KEY = os.getenv("GEOAPIFY_KEY")


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
                image_url TEXT,
                distance_meters REAL,
                driving_distance_miles REAL,
                driving_duration_minutes REAL,
                loved BOOLEAN DEFAULT FALSE
            )
        """))
        connection.commit()


def clear_loved_restaurants_db(user_id):
    """Clear all loved restaurants for a specific user by setting loved = FALSE"""
    create_foodiesrn_table()
    with engine.connect() as connection:
        connection.execute(
            db.text(f"UPDATE {TABLE_RN} SET loved = FALSE WHERE user_id = :uid"),
            {"uid": user_id}
        )
        connection.commit()
    print("\nAll your loved restaurants have been cleared.")


def calculate_distances_with_geoapify(user_lat, user_lng, restaurants):
    """
    Calculate driving distances and times from user location to restaurants using Geoapify API.
    Also calculates straight-line distances as fallback.
    """
    print(f"[DEBUG] User location: {user_lat}, {user_lng}")
    print(f"[DEBUG] Number of restaurants to process: {len(restaurants)}")
    
    if not GEOAPIFY_KEY:
        print("WARNING: GEOAPIFY_KEY not found. Distance filtering will use straight-line distance only.")
        # Calculate straight-line distances as fallback
        for restaurant in restaurants:
            if 'coordinates' in restaurant:
                rest_lat = restaurant['coordinates']['latitude']
                rest_lng = restaurant['coordinates']['longitude']
                
                # Haversine formula for straight-line distance
                import math
                
                # Convert latitude and longitude from degrees to radians
                lat1, lon1, lat2, lon2 = map(math.radians, [user_lat, user_lng, rest_lat, rest_lng])
                
                # Haversine formula
                dlat = lat2 - lat1
                dlon = lon2 - lon1
                a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
                c = 2 * math.asin(math.sqrt(a))
                
                # Radius of earth in kilometers is 6371
                distance_km = 6371 * c
                distance_meters = distance_km * 1000
                
                restaurant['distance_meters'] = distance_meters
                restaurant['driving_distance_miles'] = None
                restaurant['driving_duration_minutes'] = None
                print(f"[DEBUG] {restaurant['name']}: {distance_meters / 1609.344:.2f} miles (straight-line)")
        return restaurants

    # Prepare sources and targets for API call
    sources = [{"lat": user_lat, "lon": user_lng}]
    targets = []
    
    for restaurant in restaurants:
        if 'coordinates' in restaurant:
            rest_lat = restaurant['coordinates']['latitude']
            rest_lng = restaurant['coordinates']['longitude']
            targets.append({"lat": rest_lat, "lon": rest_lng})
            print(f"[DEBUG] Restaurant {restaurant['name']} coordinates: {rest_lat}, {rest_lng}")
    
    if not targets:
        print("No restaurant coordinates found for distance calculation")
        return restaurants
    
    print(f"[DEBUG] Making Geoapify API call with {len(sources)} sources and {len(targets)} targets")
    
    # Make API call to Geoapify Route Matrix
    url = "https://api.geoapify.com/v1/routematrix"
    headers = {
        "Content-Type": "application/json"
    }
    
    # Request body in JSON format
    data = {
        "mode": "drive",
        "sources": sources,
        "targets": targets
    }
    
    params = {
        "apiKey": GEOAPIFY_KEY
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, params=params, timeout=15)
        response.raise_for_status()
        result = response.json()
        
        print(f"[DEBUG] Geoapify API response received. Keys: {result.keys()}")
        
        # Parse results and add to restaurants
        if 'sources_to_targets' in result and result['sources_to_targets']:
            matrix = result['sources_to_targets'][0]
            print(f"[DEBUG] Matrix length: {len(matrix)}")
            
            for i, restaurant in enumerate(restaurants):
                if i < len(matrix) and 'coordinates' in restaurant:
                    route_info = matrix[i]
                    print(f"[DEBUG] Route info for {restaurant['name']}: {route_info}")
                    
                    # Get driving distance and time
                    if 'distance' in route_info and 'time' in route_info:
                        distance_meters = route_info['distance']
                        time_seconds = route_info['time']
                        
                        restaurant['distance_meters'] = distance_meters
                        restaurant['driving_distance_miles'] = distance_meters / 1609.344  # Convert to miles
                        restaurant['driving_duration_minutes'] = time_seconds / 60  # Convert to minutes
                        
                        print(f"[DEBUG] {restaurant['name']}: {restaurant['driving_distance_miles']:.2f} miles, {restaurant['driving_duration_minutes']:.1f} min")
                    else:
                        # API call failed for this restaurant, calculate straight-line distance
                        rest_lat = restaurant['coordinates']['latitude']
                        rest_lng = restaurant['coordinates']['longitude']
                        
                        import math
                        lat1, lon1, lat2, lon2 = map(math.radians, [user_lat, user_lng, rest_lat, rest_lng])
                        dlat = lat2 - lat1
                        dlon = lon2 - lon1
                        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
                        c = 2 * math.asin(math.sqrt(a))
                        distance_km = 6371 * c
                        distance_meters = distance_km * 1000
                        
                        restaurant['distance_meters'] = distance_meters
                        restaurant['driving_distance_miles'] = None
                        restaurant['driving_duration_minutes'] = None
                        print(f"[DEBUG] {restaurant['name']}: {distance_meters / 1609.344:.2f} miles (fallback straight-line)")
        else:
            print("[DEBUG] No matrix found in API response")
            print(f"[DEBUG] Full API response: {result}")
        
        print(f"[TIMER] Geoapify distance calculation completed for {len(restaurants)} restaurants")
        return restaurants
        
    except Exception as e:
        print(f"Error calculating distances with Geoapify: {e}")
        # Fallback to straight-line distance calculation
        for restaurant in restaurants:
            if 'coordinates' in restaurant:
                rest_lat = restaurant['coordinates']['latitude']
                rest_lng = restaurant['coordinates']['longitude']
                
                import math
                lat1, lon1, lat2, lon2 = map(math.radians, [user_lat, user_lng, rest_lat, rest_lng])
                dlat = lat2 - lat1
                dlon = lon2 - lon1
                a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
                c = 2 * math.asin(math.sqrt(a))
                distance_km = 6371 * c
                distance_meters = distance_km * 1000
                
                restaurant['distance_meters'] = distance_meters
                restaurant['driving_distance_miles'] = None
                restaurant['driving_duration_minutes'] = None
                print(f"[DEBUG] {restaurant['name']}: {distance_meters / 1609.344:.2f} miles (error fallback)")
        
        return restaurants


def filter_by_radius(restaurants, radius_miles):
    """Filter restaurants based on radius in miles"""
    filtered = []
    
    print(f"[DEBUG] Filtering {len(restaurants)} restaurants by {radius_miles} mile radius")
    
    for restaurant in restaurants:
        # Use driving distance if available, otherwise use straight-line distance
        if restaurant.get('driving_distance_miles') is not None:
            distance_miles = restaurant['driving_distance_miles']
            distance_type = "driving"
        elif restaurant.get('distance_meters') is not None:
            distance_miles = restaurant['distance_meters'] / 1609.344  # Convert meters to miles
            distance_type = "straight-line"
        else:
            # No distance data available, skip this restaurant
            print(f"[DEBUG] {restaurant['name']}: No distance data available, skipping")
            continue
        
        print(f"[DEBUG] {restaurant['name']}: {distance_miles:.2f} miles ({distance_type})")
        
        if distance_miles <= radius_miles:
            filtered.append(restaurant)
            print(f"[DEBUG] ✅ {restaurant['name']} included (within {radius_miles} miles)")
        else:
            print(f"[DEBUG] ❌ {restaurant['name']} excluded ({distance_miles:.2f} > {radius_miles} miles)")
    
    print(f"[DEBUG] Filtered results: {len(filtered)} restaurants within {radius_miles} miles")
    return filtered


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
        "limit": 50
    }

    if user_input.get("latitude") and user_input.get("longitude"):
        params["latitude"] = user_input["latitude"]
        params["longitude"] = user_input["longitude"]
        # Remove location param when using coordinates
        del params["location"]

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
                "image_url": biz.get("image_url", ""),
                "coordinates": biz.get("coordinates", {})
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
                if 'loved' not in r:
                    r['loved'] = False

                connection.execute(
                    db.text(f"""
                        INSERT INTO {TABLE_RN} 
                        (name, location, price, rating, url, user_location, cuisine, vibe, user_id, image_url,
                        distance_meters, driving_distance_miles, driving_duration_minutes, loved)
                        VALUES (:name, :location, :price, :rating, :url, :user_location, :cuisine, :vibe, :user_id, :image_url,
                        :distance_meters, :driving_distance_miles, :driving_duration_minutes, :loved)
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
                SELECT name, location, rating, price, url, image_url, cuisine, vibe, user_location,
                distance_meters, driving_distance_miles, driving_duration_minutes, loved
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


# Toggle love status for a restaurant
def toggle_restaurant_love(user_id, restaurant_name, restaurant_location):
    """Toggle the loved status of a restaurant"""
    create_foodiesrn_table()
    with engine.connect() as connection:
        # First check if restaurant exists and get current loved status
        result = connection.execute(
            db.text(f"""
                SELECT loved FROM {TABLE_RN} 
                WHERE user_id = :uid AND name = :name AND location = :location
            """),
            {"uid": user_id, "name": restaurant_name, "location": restaurant_location}
        ).fetchone()
        
        if result:
            # Toggle the loved status
            new_loved_status = not bool(result[0])
            connection.execute(
                db.text(f"""
                    UPDATE {TABLE_RN} 
                    SET loved = :loved 
                    WHERE user_id = :uid AND name = :name AND location = :location
                """),
                {"loved": new_loved_status, "uid": user_id, "name": restaurant_name, "location": restaurant_location}
            )
            connection.commit()
            return new_loved_status
    return False


# Get loved restaurants for a user
def get_loved_restaurants(user_id):
    """Get all loved restaurants for a user"""
    create_foodiesrn_table()
    with engine.connect() as connection:
        results = connection.execute(
            db.text(f"""
                SELECT name, location, rating, price, url, image_url, cuisine, vibe, user_location,
                       distance_meters, driving_distance_miles, driving_duration_minutes, loved
                FROM {TABLE_RN} 
                WHERE user_id = :uid AND loved = TRUE
            """),
            {"uid": user_id}
        ).fetchall()
    return results


# Main function to run Yelp + GenAI-based restaurant recommendation pipeline
def run_restaurant_search(user_input, user_id):
    print("\n🔍 Generating your personalized recommendations...\n")
    start = time.time()
    results = search_yelp(user_input)
    print(f"[TIMER] Yelp API took {time.time() - start:.2f} seconds")

    # Calculate distances if GPS coordinates are provided
    if user_input.get("latitude") and user_input.get("longitude"):
        start = time.time()
        results = calculate_distances_with_geoapify(
            float(user_input["latitude"]), 
            float(user_input["longitude"]), 
            results
        )
        print(f"[TIMER] Distance calculation took {time.time() - start:.2f} seconds")
        
        # Filter by radius if specified
        try:
            radius_miles = float(user_input.get("radius", 0))
            if radius_miles > 0:
                before_count = len(results)
                results = filter_by_radius(results, radius_miles)
                print(f"[TIMER] Filtered from {before_count} to {len(results)} restaurants within {radius_miles} miles")
        except ValueError:
            print("[WARNING] Radius input could not be converted to float.")


    if results:
        filtered_results = [r for r in results if r["rating"] > 3.5]
        if not filtered_results:
            return []
        num_recs = min(3, len(filtered_results))
        top_recs = random.sample(filtered_results, k=num_recs)

        start = time.time()
        #blurbs = generate_blurbs(top_recs, user_input)
        blurbs = ["Blurb feature disabled for now.", "Blurb feature disabled for now.", "Blurb feature disabled for now."]
        print(f"[TIMER] GenAI API took {time.time() - start:.2f} seconds")

        for biz, blurb in zip(top_recs, blurbs):
            biz["blurb"] = blurb
            biz["user_location"] = user_input["location"]
            biz["cuisine"] = user_input["cuisine"]
            biz["vibe"] = user_input["vibe"]
            biz["user_id"] = user_id
            biz["image_url"] = biz.get("image_url", "")
            if 'distance_meters' not in biz:
                biz['distance_meters'] = None
            if 'driving_distance_miles' not in biz:
                biz['driving_distance_miles'] = None
            if 'driving_duration_minutes' not in biz:
                biz['driving_duration_minutes'] = None
            
            if 'coordinates' in biz:
                del biz['coordinates']

        # Check if any of these restaurants are already loved
        with engine.connect() as connection:
            for restaurant in top_recs:
                loved_check = connection.execute(
                    db.text(f"""
                        SELECT loved FROM {TABLE_RN} 
                        WHERE user_id = :uid AND name = :name AND location = :location
                    """),
                    {"uid": user_id, "name": restaurant["name"], "location": restaurant["location"]}
                ).fetchone()
                
                # Set loved status based on database
                if loved_check:
                    restaurant["loved"] = bool(loved_check[0])
                else:
                    restaurant["loved"] = False

        save_to_db(top_recs, user_id)
        return top_recs

    else:
        return []


# Add this function to your run_foodiesrn.py file

def migrate_database():
    """Add missing distance columns to existing table"""
    with engine.connect() as connection:
        # Check if columns exist and add them if they don't
        try:
            # Try to select the new columns to see if they exist
            connection.execute(db.text(f"SELECT distance_meters FROM {TABLE_RN} LIMIT 1"))
            print("Distance columns already exist")
        except Exception:
            print("Adding missing distance columns...")
            try:
                connection.execute(db.text(f"ALTER TABLE {TABLE_RN} ADD COLUMN distance_meters REAL"))
                connection.execute(db.text(f"ALTER TABLE {TABLE_RN} ADD COLUMN driving_distance_miles REAL"))
                connection.execute(db.text(f"ALTER TABLE {TABLE_RN} ADD COLUMN driving_duration_minutes REAL"))
                connection.commit()
                print("✅ Distance columns added successfully!")
            except Exception as e:
                print(f"Error adding columns: {e}")

        # Check if loved column exists and add it if it doesn't
        try:
            connection.execute(db.text(f"SELECT loved FROM {TABLE_RN} LIMIT 1"))
            print("Loved column already exists")
        except Exception:
            print("Adding missing loved column...")
            try:
                connection.execute(db.text(f"ALTER TABLE {TABLE_RN} ADD COLUMN loved BOOLEAN DEFAULT FALSE"))
                connection.commit()
                print("✅ Loved column added successfully!")
            except Exception as e:
                print(f"Error adding loved column: {e}")


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
