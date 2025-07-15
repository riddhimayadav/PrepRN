from flask import Flask, render_template, request, redirect, url_for, session, flash
from shared.auth import create_user_table, get_user_id
from FoodiesRN.run_foodiesrn import *
from forms import LoginForm, SignupForm
from shared.auth import login
# from shared.prepngo_helpers import get_prepngo_meals
# from prepngo.PrepnGo import main as run_prepngo
# from prepngo.database_functions import *
from shared.prepngo_helpers import get_prepngo_meals, save_prepngo_results, get_saved_prepngo, clear_saved_prepngo
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = "secret_key"

create_user_table()


@app.route("/")
@app.route("/home")
def home():
    return redirect(url_for("login_view"))

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


@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect(url_for("login_view"))
    return render_template("dashboard.html", username=session["username"])

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

@app.route("/clear_foodiesrn", methods=["POST"])
def clear_foodiesrn():
    if "user_id" not in session:
        return redirect(url_for("login_view"))

    clear_saved_recommendations(session["user_id"])
    return redirect(url_for("my_recommendations"))


@app.route("/clear_prepngo", methods=["POST"])
def clear_prepngo():
    if "user_id" not in session:
        return redirect(url_for("login_view"))
    clear_saved_prepngo(session["user_id"])
    return redirect(url_for("my_recommendations"))


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

@app.route("/prep", methods=["GET", "POST"])
def prep():
    if "user_id" not in session:
        return redirect(url_for("login_view"))
    if request.method == "POST":
        user_input = {
            "location": request.form.get("location"),
            "budget": request.form.get("budget"),
            "servings": request.form.get("servings"),
            "diets": request.form.getlist("diet"),
            "user_id": session["user_id"]
        }
        if not all([user_input['location'], user_input['budget'], user_input['servings']]):
            print("Please fill out all fields.")
            return render_template("prep.html", results=None)  
        results = get_prepngo_meals(user_input, session["user_id"])
        save_prepngo_results(results, user_input, session["user_id"])
        return render_template("prep.html", results=results, user_input=user_input)        
    return render_template("prep.html", results=None)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_view"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)