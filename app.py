# Main Flask application for PrepRN

from flask import Flask, render_template, request, redirect, url_for, session, flash
from shared.auth import create_user_table, get_user_id
from FoodiesRN.run_foodiesrn import *
from forms import LoginForm, SignupForm
from shared.auth import login
from prepngo.PrepnGo import main as run_prepngo_meals
from shared.prepngo_helpers import *
from dotenv import load_dotenv
import time
from FoodiesRN.run_foodiesrn import create_foodiesrn_table
import urllib.parse
from prepngo.database_functions import init_db


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


# Home route redirects to login page
@app.route("/")
@app.route("/home")
def home():
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
@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect(url_for("login_view"))
    session.pop('foodies_results', None)
    return render_template("dashboard.html", username=session["username"])


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
    
    from shared.prepngo_helpers import clear_loved_meals_db
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
    
    # Create Google Maps search query for external link
    maps_query = f"{restaurant_name} {restaurant_location}"
    
    return render_template("restaurant_detail.html", 
                         restaurant=restaurant, 
                         maps_query=maps_query)


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

    #drop any previous results
    if request.method == "GET":
        session.pop("prep_results", None)
        results = None

    #generate & save new results
    else:
        user_input = {
            "location": request.form.get("location"),
            "budget":   request.form.get("budget"),
            "servings": request.form.get("servings"),
            "diets":    request.form.getlist("diet"),
            "meal_type": request.form.get("meal_type", "").strip()
        }

        if not (user_input["location"] and user_input["budget"] and user_input["servings"]):
            flash("Please fill out all fields.")
            return redirect(url_for("prep"))

        start = time.time()
        results = get_prepngo_meals(user_input, session["user_id"])
        # measure end‑to‑end
        results["duration"] = f"{(time.time() - start):.2f}"

        save_prepngo_results(results["meals"], user_input, session["user_id"])

        # Check loved status for each meal after saving to database
        conn = init_db('preprn.db')
        for meal in results["meals"]:
            cur = conn.cursor()
            cur.execute('''
                SELECT meals.loved
                FROM meals
                JOIN requests ON meals.request_id = requests.id
                WHERE requests.user_id = ? AND meals.title = ? AND meals.source_url = ?
                ORDER BY meals.id DESC
                LIMIT 1
            ''', (session["user_id"], meal['title'], meal['source_url']))
            
            loved_result = cur.fetchone()
            meal['loved'] = bool(loved_result[0]) if loved_result else False

        conn.close()
        session["prep_results"] = results
    return render_template("prep.html", results=session.get("prep_results"))


# Display the results of the PrepnGo meal plan
@app.route("/prep/results")
def prep_results():
    if "user_id" not in session:
        return redirect(url_for("login_view"))

    results = session.get("prep_results")
    if not results:
        flash("No meal plan generated yet.")
        return redirect(url_for("prep"))

    return render_template("prep_results.html", results=results)


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


# Start the Flask app
if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)