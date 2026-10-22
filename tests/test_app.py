import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize("path", ["/login", "/signup"])
def test_account_pages_include_csrf_token(client, csrf_token, path):
    assert client.get(path).status_code == 200
    assert csrf_token(client)


@pytest.mark.parametrize("path", ["/dashboard", "/foodies", "/prep", "/my_recommendations"])
def test_member_pages_require_login(client, path):
    response = client.get(path)
    assert response.status_code == 302
    assert "/login" in response.location


def test_startup_requires_a_session_secret():
    environment = os.environ.copy()
    environment.pop("SECRET_KEY", None)
    result = subprocess.run([sys.executable, "-c", "import app"],
                            cwd=Path(__file__).resolve().parents[1], env=environment,
                            capture_output=True, text=True)
    assert result.returncode != 0
    assert "Set SECRET_KEY" in result.stderr


def test_signup_login_and_logout(client, csrf_token):
    token = csrf_token(client)
    response = client.post("/signup", data={"username": "alice", "password": "long-password", "csrf_token": token})
    assert response.status_code == 302
    assert "/dashboard" in response.location
    client.get("/logout")
    token = csrf_token(client)
    response = client.post("/login", data={"username": "alice", "password": "long-password", "csrf_token": token})
    assert response.status_code == 302
    with client.session_transaction() as session:
        assert session["username"] == "alice"
    client.get("/logout")
    with client.session_transaction() as session:
        assert "user_id" not in session


def test_json_mutations_require_csrf(authenticated_client):
    response = authenticated_client.post("/love_restaurant", json={"name": "Cafe", "location": "Austin"})
    assert response.status_code == 400


@pytest.mark.parametrize("route", ["/signup", "/login"])
def test_normalized_usernames_keep_a_valid_account_session(client, csrf_token, route):
    if route == "/login":
        from shared.auth import signup
        signup("alice", "long-password")
    response = client.post(route, data={
        "username": " alice ", "password": "long-password", "csrf_token": csrf_token(client),
    })
    assert response.status_code == 302
    with client.session_transaction() as session:
        assert session["username"] == "alice"
        assert isinstance(session["user_id"], int)
