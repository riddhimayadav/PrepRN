from flask import Flask, render_template, request, redirect, url_for, session
from shared.auth import create_user_table, get_user_id
from FoodiesRN.run_foodiesrn import run_restaurant_search
from forms import LoginForm, SignupForm
from shared.auth import login


app = Flask(__name__)
app.secret_key = "secret_key"

create_user_table()


@app.route("/")
@app.route("/home")
def index():
    return render_template("index.html")

@app.route("/signup", methods=["GET", "POST"])
def signup_view():
    form = SignupForm()
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
            return "❌ Username already taken. <a href='/signup'>Try again</a>"
    return render_template("signup.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login_view():
    form = LoginForm()
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
            return "❌ Invalid login. <a href='/login'>Try again</a>"
    return render_template("login.html", form=form)


@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect(url_for("login_view"))
    return render_template("dashboard.html", username=session["username"])

@app.route("/my_recommendations")
def my_recommendations():
    if "user_id" not in session:
        return redirect(url_for("login_view"))
    
    results = [
        {"name": "Sushi Place", "location": "Austin, TX", "rating": 4.5, "price": "$$"},
        {"name": "Taco Spot", "location": "Austin, TX", "rating": 4.2, "price": "$"},
    ]
    return render_template("my_recommendations.html", results=results)


@app.route("/prep", methods=["GET", "POST"])
def prep():
    if "user_id" not in session:
        return redirect(url_for("login_view"))

    return render_template("prep.html")


@app.route("/foodies", methods=["GET", "POST"])
def foodies():
    if "user_id" not in session:
        return redirect(url_for("login_view"))

    return render_template("foodies.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
