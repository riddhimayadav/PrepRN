# Import SQLAlchemy for database interaction
import sqlalchemy as db
from sqlalchemy import inspect


# Create a SQLite engine using 'preprn.db'
engine = db.create_engine("sqlite:////home/preprn/PrepRN/preprn.db")
inspector = inspect(engine)


# Function to create a users table if it doesn't already exist
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


# Function to register a new user
def signup(username, password):
    if not username.strip() or not password.strip():
        return None

    with engine.connect() as connection:
        existing = connection.execute(
            db.text("SELECT * FROM users WHERE username = :u"),
            {"u": username}
        ).fetchone()

        if existing:
            return None
        else:
            connection.execute(
                db.text("INSERT INTO users (username, password) VALUES (:u, :p)"),
                {"u": username, "p": password}
            )
            connection.commit()
            return username


# Function to log in an existing user
def login(username, password):
    with engine.connect() as connection:
        result = connection.execute(
            db.text("SELECT * FROM users WHERE username = :u AND password = :p"),
            {"u": username, "p": password}
        ).fetchone()

    if result:
        return username
    else:
        return None


# CLI function to prompt user to either login or sign up (used for terminal version)
def login_or_signup():
    while True:
        choice = input("Do you want to login or sign up? (login/signup): ").strip().lower()
        if choice == "login":
            return login()
        elif choice == "signup":
            return signup()
        else:
            print("Invalid input. Please type 'login' or 'signup'.\n")


# Function to retrieve a user's ID based on their username
def get_user_id(username):
    with engine.connect() as connection:
        result = connection.execute(
            db.text("SELECT id FROM users WHERE username = :u"),
            {"u": username}
        ).fetchone()
        return result[0] if result else None
