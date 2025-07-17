# Main Flask application for PrepRN

from flask import Flask, render_template, request, redirect, url_for, session, flash
from shared.auth import create_user_table, get_user_id
from FoodiesRN.run_foodiesrn import *
from forms import LoginForm, SignupForm
from shared.auth import login
from prepngo.PrepnGo import main as run_prepngo_meals
from shared.prepngo_helpers import get_prepngo_meals, save_prepngo_results, get_saved_prepngo, clear_saved_prepngo
from dotenv import load_dotenv
import time


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


# Home route redirects to login page
@app.route("/")
@app.route("/home")
def home():
    return redirect(url_for("login_view"))


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
    return render_template("dashboard.html", username=session["username"])


# View saved recommendations from both FoodiesRN and PrepnGo
@app.route("/my_recommendations")
def my_recommendations():
    if "user_id" not in session:
        return redirect(url_for("login_view"))
    
    user_id = session["user_id"]
    foodiesrn_results = view_saved_recommendations(user_id)
    prepngo_results = get_saved_prepngo(session["user_id"])
    return render_template("my_recommendations.html",
                           foodiesrn_results=foodiesrn_results,
                           prepngo_results=prepngo_results)


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
        }

        if not all(user_input.values()):
            print("Please fill out all fields.")
            return render_template("foodies.html", results=None)

        results = run_restaurant_search(user_input, session["user_id"])
        return render_template("foodies.html", results=results)

    return render_template("foodies.html", results=None)


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


# Start the Flask app
if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)