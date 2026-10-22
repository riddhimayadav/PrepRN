import sqlalchemy as db
from werkzeug.security import check_password_hash

from shared.auth import get_user_id, login, migrate_legacy_passwords, signup
from shared.database import engine
import shared.auth as accounts


def test_signup_hashes_password_and_login_checks_it():
    assert signup("alice", "long-password") == "alice"
    with engine.connect() as connection:
        row = connection.execute(db.text("SELECT password, password_scheme FROM users WHERE username = 'alice'")).first()
    assert row.password != "long-password"
    assert row.password_scheme == "werkzeug"
    assert check_password_hash(row.password, "long-password")
    assert login("alice", "long-password") == "alice"
    assert login("alice", "wrong-password") is None
    assert login("' OR 1=1 --", "long-password") is None


def test_duplicate_username_does_not_replace_password():
    signup("alice", "original-password")
    assert signup("alice", "different-password") is None
    assert login("alice", "original-password") == "alice"
    assert login("alice", "different-password") is None


def test_legacy_password_migration_preserves_accounts_and_is_idempotent():
    # A plaintext password can resemble a hash; the explicit scheme distinguishes it.
    password = "scrypt:example$not$a-real-hash"
    with engine.begin() as connection:
        connection.execute(db.text("INSERT INTO users (username, password) VALUES (:u, :p)"), {"u": "legacy", "p": password})
    account_id = get_user_id("legacy")
    assert login("legacy", password) is None
    assert migrate_legacy_passwords() == 1
    assert login("legacy", password) == "legacy"
    assert get_user_id("legacy") == account_id
    assert migrate_legacy_passwords() == 0


def test_migration_does_not_rehash_new_accounts():
    signup("alice", "long-password")
    assert migrate_legacy_passwords() == 0
    assert login("alice", "long-password") == "alice"


def test_original_database_schema_can_be_upgraded_without_losing_account_ids(tmp_path, monkeypatch):
    legacy_engine = db.create_engine(db.URL.create("sqlite", database=str(tmp_path / "legacy.db")))
    try:
        with legacy_engine.begin() as connection:
            connection.execute(db.text("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL)"))
            connection.execute(db.text("INSERT INTO users VALUES (7, 'existing', 'original-password')"))
        monkeypatch.setattr(accounts, "engine", legacy_engine)
        assert accounts.migrate_legacy_passwords() == 1
        assert accounts.login("existing", "original-password") == "existing"
        assert accounts.get_user_id("existing") == 7
    finally:
        legacy_engine.dispose()
