"""Account storage with hashed passwords and an explicit legacy migration."""

from getpass import getpass

import sqlalchemy as db
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from shared.database import engine


def create_user_table():
    with engine.begin() as connection:
        connection.execute(db.text("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                password_scheme TEXT NOT NULL DEFAULT 'legacy'
            )
        """))
        columns = {row[1] for row in connection.execute(db.text("PRAGMA table_info(users)"))}
        if "password_scheme" not in columns:
            connection.execute(db.text("ALTER TABLE users ADD COLUMN password_scheme TEXT NOT NULL DEFAULT 'legacy'"))


def signup(username, password):
    if not isinstance(username, str) or not isinstance(password, str):
        return None
    username = username.strip()
    if not username or not password.strip():
        return None
    password_hash = generate_password_hash(password)
    try:
        with engine.begin() as connection:
            connection.execute(
                db.text("INSERT INTO users (username, password, password_scheme) VALUES (:u, :p, 'werkzeug')"),
                {"u": username, "p": password_hash},
            )
    except IntegrityError:
        return None
    return username


def login(username, password):
    if not isinstance(username, str) or not isinstance(password, str):
        return None
    with engine.connect() as connection:
        result = connection.execute(
            db.text("SELECT username, password, password_scheme FROM users WHERE username = :u"),
            {"u": username.strip()},
        ).mappings().first()
    if not result or result["password_scheme"] != "werkzeug":
        return None
    try:
        valid = check_password_hash(result["password"], password)
    except (ValueError, TypeError):
        valid = False
    return result["username"] if valid else None


def migrate_legacy_passwords():
    """Hash legacy rows in one transaction; preserve account IDs and plaintext-looking passwords."""
    create_user_table()
    with engine.begin() as connection:
        rows = connection.execute(
            db.text("SELECT id, password FROM users WHERE password_scheme = 'legacy'")
        ).mappings().all()
        for row in rows:
            connection.execute(
                db.text("UPDATE users SET password = :password, password_scheme = 'werkzeug' WHERE id = :id AND password_scheme = 'legacy'"),
                {"password": generate_password_hash(row["password"]), "id": row["id"]},
            )
    return len(rows)


def login_or_signup():
    create_user_table()
    while True:
        choice = input("Log in or sign up? (login/signup): ").strip().lower()
        if choice not in {"login", "signup"}:
            print("Please choose login or signup.")
            continue
        username = input("Username: ").strip()
        password = getpass("Password: ")
        result = login(username, password) if choice == "login" else signup(username, password)
        if result:
            return result
        print("Account could not be authenticated or created.")


def get_user_id(username):
    with engine.connect() as connection:
        result = connection.execute(
            db.text("SELECT id FROM users WHERE username = :u"), {"u": username}
        ).first()
    return result[0] if result else None
