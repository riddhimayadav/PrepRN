"""Test storage is always temporary, and live HTTP requests are rejected."""

import atexit
import os
from pathlib import Path
import re
import tempfile

import pytest
import requests
import sqlalchemy as db

_database = tempfile.TemporaryDirectory(prefix="preprn-tests-")
atexit.register(_database.cleanup)
os.environ["PREPRN_DATABASE_PATH"] = str(Path(_database.name) / "test.db")
os.environ["SECRET_KEY"] = "test-session-secret-not-for-deployment"
for _key in ["YELP_KEY", "SPOON_API_KEY", "GOOGLE_API_KEY", "GENAI_KEY", "GEOAPIFY_KEY"]:
    os.environ.pop(_key, None)

from app import app
from shared.auth import get_user_id, signup
from shared.database import engine


@pytest.fixture(autouse=True)
def isolate_requests_and_storage(monkeypatch):
    def reject_request(*args, **kwargs):
        raise AssertionError("A test attempted a live HTTP request; mock the provider instead.")
    monkeypatch.setattr(requests.sessions.Session, "request", reject_request)
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=True)
    with engine.begin() as connection:
        for table in db.inspect(engine).get_table_names():
            connection.execute(db.text(f'DELETE FROM "{table}"'))
    yield


@pytest.fixture
def client():
    return app.test_client()


@pytest.fixture
def authenticated_client(client):
    signup("tester", "correct-horse-password")
    with client.session_transaction() as session:
        session["user_id"] = get_user_id("tester")
        session["username"] = "tester"
    return client


@pytest.fixture
def csrf_token():
    def get_token(client):
        response = client.get("/login")
        match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', response.get_data(as_text=True))
        assert match, "The sign-in form must supply a CSRF token"
        return match.group(1)
    return get_token
