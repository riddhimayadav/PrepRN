# File: shared/auth.py

import sqlalchemy as db
from sqlalchemy import inspect

engine = db.create_engine('sqlite:///recommendations.db')
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

def signup():
    while True:
        username = input("Choose a username: ").strip()
        password = input("Choose a password: ").strip()

        with engine.connect() as connection:
            result = connection.execute(
                db.text("SELECT * FROM users WHERE username = :u"),
                {"u": username}
            ).fetchone()

            if result:
                print("❌ Username already exists. Try again.\n")
            else:
                connection.execute(
                    db.text("INSERT INTO users (username, password) VALUES (:u, :p)"),
                    {"u": username, "p": password}
                )
                connection.commit()
                print("✅ Account created successfully!\n")
                return username

def login():
    while True:
        username = input("Username: ").strip()
        with engine.connect() as connection:
            user = connection.execute(
                db.text("SELECT * FROM users WHERE username = :u"),
                {"u": username}
            ).fetchone()

        if not user:
            print("❌ Username not found.")
            choice = input("Do you want to try again or sign up? (login/signup): ").strip().lower()
            if choice == "signup":
                return signup()
            else:
                continue

        for _ in range(3):
            password = input("Password: ").strip()
            with engine.connect() as connection:
                result = connection.execute(
                    db.text("SELECT * FROM users WHERE username = :u AND password = :p"),
                    {"u": username, "p": password}
                ).fetchone()

            if result:
                print("✅ Login successful!\n")
                return username
            else:
                print("Incorrect password. Try again.\n")

        print("❌ Too many failed attempts. Restarting...\n")

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
