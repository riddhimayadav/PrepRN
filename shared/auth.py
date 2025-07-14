# File: shared/auth.py

import sqlalchemy as db
from sqlalchemy import inspect

engine = db.create_engine("sqlite:///preprn.db")
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


def login_or_signup():
    while True:
        choice = input("Do you want to login or sign up? (login/signup): ").strip().lower()
        if choice == "login":
            return login()
        elif choice == "signup":
            return signup()
        else:
            print("Invalid input. Please type 'login' or 'signup'.\n")

def get_user_id(username):
    with engine.connect() as connection:
        result = connection.execute(
            db.text("SELECT id FROM users WHERE username = :u"),
            {"u": username}
        ).fetchone()
        return result[0] if result else None
