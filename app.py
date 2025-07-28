# Main Flask application for PrepRN

from flask import Flask, render_template, request, redirect, url_for, session, flash
from shared.auth import create_user_table, get_user_id
from FoodiesRN.run_foodiesrn import *
from forms import LoginForm, SignupForm
from shared.auth import login
from prepngo.PrepnGo import main as run_prepngo_meals
from prepngo.prepngo_helpers import *
from dotenv import load_dotenv
import time
from FoodiesRN.run_foodiesrn import create_foodiesrn_table
import urllib.parse
from prepngo.database_functions import init_db
from flask import jsonify
import json

# helper for dashboard
from shared.pantry import (
    init_pantry_db,
    get_pantry_items,
    add_pantry_item,
    remove_pantry_item,
)
from shared.profile  import (
    get_user_restrictions, set_user_restrictions,
)
from shared.activity import get_recent_liked_restaurants
from prepngo.prepngo_helpers import get_loved_meals
# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = "secret_key"
# spoon_key = os.getenv("SPOON_API_KEY")
# yelp_key = os.getenv("YELP_API_KEY")
api_key = os.getenv("SPOON_API_KEY")
print("DEBUG Spoon Key:", api_key) 
params = {
    "apiKey": api_key
}

# Create user table if it doesn't already exist
create_user_table()
create_foodiesrn_table()
migrate_database()
init_pantry_db()

# Home route redirects to login page
@app.route("/")
@app.route("/home")
def home():
    session.pop("prep_results", None)
    return render_template("home.html")


# Sign-up route: handles new user registration
@app.route("/signup", methods=["GET", "POST"])
def signup_view():
    form = SignupForm()
    error = None
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        from shared.auth import signup
        result = signup(username, password)
        if result:
            session["username"] = username
            user_id = get_user_id(username)
            session["user_id"] = user_id
            return redirect(url_for("dashboard"))
        else:
            error = "Username already taken."
    return render_template("signup.html", form=form, error=error)


# Login route: handles user login
@app.route("/login", methods=["GET", "POST"])
def login_view():
    form = LoginForm()
    error = None
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        from shared.auth import login
        valid_user = login(username, password)
        if valid_user:
            session["username"] = valid_user
            user_id = get_user_id(username)
            session["user_id"] = user_id
            return redirect(url_for("dashboard"))
        else:
            error = "Invalid username or password."
    return render_template("login.html", form=form, error=error)


# Dashboard route: visible only after login
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login_view"))

    user_id = session["user_id"]
    username = session["username"]

    if request.method == "POST":
        action = request.form.get("action")

        # NEW: handle the comma‑sep pantry update
        if action == "update_pantry":
            # first remove everything
            for old in get_pantry_items(user_id):
                remove_pantry_item(user_id, old)
            # then add each new, trimmed item
            raw = request.form["pantry_list"]
            for itm in [i.strip() for i in raw.split(",") if i.strip()]:
                add_pantry_item(user_id, itm)

        elif action == "update_restrictions":
            set_user_restrictions(user_id, request.form.getlist("diet"))

        elif action == "update_budget":
            set_weekly_budget(user_id, float(request.form["budget"]))
            set_daily_allocation(
              user_id,
              float(request.form["daily_percent"]) / 100.0
            )

        return redirect(url_for("dashboard"))

    # on GET just load whatever’s in the DB now
    pantry_items     = get_pantry_items(user_id)
    restrictions     = get_user_restrictions(user_id)
    # weekly_budget    = get_weekly_budget(user_id)
    # daily_percent    = get_daily_allocation(user_id)
    liked_recipes     = get_loved_meals(user_id)
    liked_restaurants= get_recent_liked_restaurants(user_id, 7)

    return render_template(
      "dashboard.html",
      user=username,
      pantry_items=pantry_items,
      restrictions=restrictions,
    #   weekly_budget=weekly_budget,
    #   daily_percent=daily_percent,
      liked_recipes=liked_recipes,
      liked_restaurants=liked_restaurants
    )


# View saved recommendations from both FoodiesRN and PrepnGo
@app.route("/my_recommendations")
def my_recommendations():
    if "user_id" not in session:
        return redirect(url_for("login_view"))
    
    user_id = session["user_id"]
    session.pop('foodies_results', None)
    foodiesrn_results = view_saved_recommendations(user_id)
    loved_restaurants = get_loved_restaurants(user_id)  
    prepngo_results = get_saved_prepngo(session["user_id"])
    loved_meals = get_loved_meals(session["user_id"])
    return render_template("my_recommendations.html",
                           foodiesrn_results=foodiesrn_results,
                           loved_restaurants=loved_restaurants,
                           prepngo_results=prepngo_results,
                           loved_meals=loved_meals)


# Clear saved FoodiesRN results
@app.route("/clear_foodiesrn", methods=["POST"])
def clear_foodiesrn():
    if "user_id" not in session:
        return redirect(url_for("login_view"))

    clear_saved_recommendations(session["user_id"])
    return redirect(url_for("my_recommendations"))


# Clear saved PrepnGo results
@app.route("/clear_prepngo", methods=["POST"])
def clear_prepngo():
    if "user_id" not in session:
        return redirect(url_for("login_view"))
    clear_saved_prepngo(session["user_id"])
    return redirect(url_for("my_recommendations"))


# Clear loved restaurants
@app.route("/clear_loved_restaurants", methods=["POST"])
def clear_loved_restaurants():
    if "user_id" not in session:
        return redirect(url_for("login_view"))
    
    from FoodiesRN.run_foodiesrn import clear_loved_restaurants_db
    clear_loved_restaurants_db(session["user_id"])
    return redirect(url_for("my_recommendations"))


# Clear loved meals  
@app.route("/clear_loved_meals", methods=["POST"])
def clear_loved_meals():
    if "user_id" not in session:
        return redirect(url_for("login_view"))
    
    from prepngo.prepngo_helpers import clear_loved_meals_db
    clear_loved_meals_db(session["user_id"])
    return redirect(url_for("my_recommendations"))


# Restaurant detail page
@app.route("/restaurant/<path:restaurant_name>/<path:restaurant_location>")
def restaurant_detail(restaurant_name, restaurant_location):
    if "user_id" not in session:
        return redirect(url_for("login_view"))
    
    # Get restaurant details from the database
    user_id = session["user_id"]
    saved_restaurants = view_saved_recommendations(user_id)
    
    # Find the specific restaurant
    restaurant = None
    for r in saved_restaurants:
        if r.name == restaurant_name and r.location == restaurant_location:
            restaurant = r
            break
    
    if not restaurant:
        flash("Restaurant not found.")
        return redirect(url_for("foodies"))
    
    # Get current notes for this restaurant
    from FoodiesRN.run_foodiesrn import get_restaurant_notes
    current_notes = get_restaurant_notes(user_id, restaurant_name, restaurant_location)
    
    # Create Google Maps search query for external link
    maps_query = f"{restaurant_name} {restaurant_location}"
    
    return render_template("restaurant_detail.html", 
                         restaurant=restaurant, 
                         maps_query=maps_query,
                         current_notes=current_notes)  # NEW: Pass notes to template


# FoodiesRN route: search for restaurants based on preferences
@app.route("/foodies", methods=["GET", "POST"])
def foodies():
    if "user_id" not in session:
        return redirect(url_for("login_view"))

    if request.method == "POST":
        user_input = {
            "location": request.form.get("location"),
            "cuisine": request.form.get("cuisine"),
            "price": request.form.get("price"),
            "vibe": request.form.get("vibe"),
            "radius": request.form.get("radius") if request.form.get("latitude") else None,  # Only use radius with GPS
            "latitude": request.form.get("latitude"),
            "longitude": request.form.get("longitude")
        }

        # Validate required fields
        if not all([user_input["cuisine"], user_input["price"], user_input["vibe"], user_input["location"]]):
            return render_template("foodies.html", results=None, error_msg="Please fill out all fields.")

        if not user_input["location"] and not (user_input["latitude"] and user_input["longitude"]):
            return render_template("foodies.html", results=None, error_msg="Please enter a location or use GPS.")

        try:
            results = run_restaurant_search(user_input, session["user_id"])
            
            # Add Google Maps URLs to each result
            for restaurant in results:
                maps_query = f"{restaurant['name']} {restaurant['location']}"
                restaurant['maps_url'] = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(maps_query)}"
                restaurant['detail_url'] = url_for('restaurant_detail', 
                                                 restaurant_name=restaurant['name'], 
                                                 restaurant_location=restaurant['location'])
            
            # Store results in session and redirect to GET request
            session['foodies_results'] = results
            return redirect(url_for('foodies'))
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return render_template("foodies.html", results=None, error_msg="Something went wrong. Please try again.")

    # GET request - show form or stored results
    results = session.get('foodies_results')
    return render_template("foodies.html", results=results, error_msg=None)


# Clear search results route
@app.route("/foodies/clear")
def clear_foodies_search():
    if "user_id" not in session:
        return redirect(url_for("login_view"))
    
    session.pop('foodies_results', None)
    return redirect(url_for('foodies'))


# PrepnGo route: generate meal plan based on input
@app.route("/prep", methods=["GET", "POST"])
def prep():
    if "user_id" not in session:
        return redirect(url_for("login_view"))

    user_id      = session["user_id"]
    restrictions = get_user_restrictions(user_id)
    pantry_items = get_pantry_items(user_id)

    # —— If the URL has ?clear=1, force‐clear old results —— 
    if request.method == "GET" and request.args.get("clear"):
        session.pop("prep_results", None)

    # —— POST: handle form submission —— 
    if request.method == "POST":
        grocery = request.form.get("grocery")  # "yes" or "no"
        user_input = {
            "location":  request.form.get("location","").strip(),
            "budget":    request.form.get("budget","").strip(),
            "servings":  request.form.get("servings","").strip(),
            "diets":     restrictions,
            "meal_type": request.form.get("meal_type","").strip(),
            "grocery":   grocery,
            # pantry branch when grocery == "no"
            "pantry":    [] if grocery == "yes" else pantry_items,
        }

        # —— Validation —— 
        if not user_input["location"] or not user_input["servings"]:
            flash("Please enter both a location and number of servings.")
            return redirect(url_for("prep"))
        if grocery == "yes" and not user_input["budget"]:
            flash("Please enter your budget for today’s meal.")
            return redirect(url_for("prep"))

        # —— Run PrepnGo & stash results —— 
        start   = time.time()
        results = get_prepngo_meals(user_input, user_id)
        results["duration"] = f"{time.time() - start:.2f}"

        save_prepngo_results(results["meals"], user_input, user_id)
        session["prep_results"] = results

        # redirect to GET (without clearing!) so spinner + scroll work
        return redirect(url_for("prep"))

    # —— GET: just render the form *with* existing results (if any) —— 
    results = session.get("prep_results")
    return render_template(
        "prep.html",
        results=      results,
        restrictions= restrictions,
        pantry_items= pantry_items
    )


# Logout route: clears session data
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_view"))


# AJAX route to toggle restaurant love status
@app.route("/love_restaurant", methods=["POST"])
def love_restaurant():
    if "user_id" not in session:
        return {"error": "Not logged in"}, 401
    
    data = request.get_json()
    restaurant_name = data.get("name")
    restaurant_location = data.get("location")
    
    if not restaurant_name or not restaurant_location:
        return {"error": "Missing restaurant data"}, 400
    
    try:
        new_loved_status = toggle_restaurant_love(
            session["user_id"], 
            restaurant_name, 
            restaurant_location
        )
        return {"loved": new_loved_status}
    except Exception as e:
        return {"error": str(e)}, 500

@app.route("/meal/<path:title>")
def meal_detail(title):
    if "user_id" not in session:
        return redirect(url_for("login_view"))
    user_id = session["user_id"]
    
    # Check if coming from my_recommendations
    source = request.args.get('source', '')
    
    if source.startswith('prep-'):
        # Coming from my_recommendations - get meal from database
        saved_meals = get_saved_prepngo(user_id)
        meal = None
        
        # Find the meal in saved results
        for m in saved_meals:
            if m[0] == title:  # m[0] is the title
                meal = {
                    "title": m[0],
                    "price": m[1], 
                    "summary": m[2],
                    "source_url": m[3],
                    "loved": m[4],
                    "diets": [],  # We don't store diets in the simple DB format
                    "meal_type": "",  # We don't store meal_type in the simple DB format
                    "instructions": [],  # Will be empty for DB meals
                    "ingredients": []   # Will be empty for DB meals
                }
                break
                
        if not meal:
            flash("Recipe not found.", "warning") 
            return redirect(url_for("my_recommendations"))
            
        # Empty lists since DB doesn't store detailed info
        instructions = []
        ingredients = []
        
    else:
        # Coming from prep form - get meal from session
        results = session.get("prep_results", {}) or {}
        meals = results.get("meals", [])
        meal = next((m for m in meals if m["title"] == title), None)

        if not meal:
            flash("Recipe not found.", "warning")
            return redirect(url_for("prep"))

        # grab the lists we injected
        instructions = meal.get("instructions", [])
        ingredients = meal.get("ingredients", [])

    current_notes = get_meal_notes(user_id, title)

    return render_template("meal_detail.html",
        meal=meal,
        instructions=instructions,
        ingredients=ingredients,
        current_notes=current_notes,
        source=source  # Pass source to template
    )


@app.route("/get_loved_restaurants")
def get_loved_restaurants_route():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    user_id = session["user_id"]
    loved_restaurants = get_loved_restaurants(user_id)

    # Format into list of dicts for frontend
    formatted = [
        {
            "name": r[0],
            "location": r[1],
            "rating": r[2],
            "price": r[3],
            "url": r[4],
            "image_url": r[5],
        }
        for r in loved_restaurants
    ]
    return jsonify({"restaurants": formatted})


# AJAX route to toggle meal love status
@app.route("/love_meal", methods=["POST"])
def love_meal():
    if "user_id" not in session:
        return {"error": "Not logged in"}, 401
    
    data = request.get_json()
    meal_name = data.get("name")
    meal_url = data.get("url")
    
    if not meal_name or not meal_url:
        return {"error": "Missing meal data"}, 400
    
    try:
        new_loved_status = toggle_meal_love(
            session["user_id"], 
            meal_name, 
            meal_url
        )
        return {"loved": new_loved_status}
    except Exception as e:
        return {"error": str(e)}, 500


@app.route("/update_restaurant_notes", methods=["POST"])
def update_restaurant_notes_route():
    if "user_id" not in session:
        return {"error": "Not logged in"}, 401
    
    data = request.get_json()
    restaurant_name = data.get("name")
    restaurant_location = data.get("location")
    notes = data.get("notes", "").strip()
    
    if not restaurant_name or not restaurant_location:
        return {"error": "Missing restaurant data"}, 400
    
    try:
        from FoodiesRN.run_foodiesrn import update_restaurant_notes
        update_restaurant_notes(
            session["user_id"], 
            restaurant_name, 
            restaurant_location,
            notes
        )
        return {"success": True, "notes": notes}
    except Exception as e:
        return {"error": str(e)}, 500


@app.route("/update_meal_notes", methods=["POST"])
def update_meal_notes_route():
    if "user_id" not in session:
        return {"error":"Not logged in"}, 401
    data = request.get_json()
    title = data.get("title")
    notes = data.get("notes", "").strip()
    success = update_meal_notes(session["user_id"], title, notes)
    return {"success": success}

# Start the Flask app
if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
