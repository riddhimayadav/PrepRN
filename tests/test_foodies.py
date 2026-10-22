from unittest.mock import Mock

import app as routes
import requests


def test_missing_search_fields_do_not_call_provider(authenticated_client, csrf_token, monkeypatch):
    search = Mock()
    monkeypatch.setattr(routes, "run_restaurant_search", search)
    response = authenticated_client.post("/foodies", data={"csrf_token": csrf_token(authenticated_client)})
    assert response.status_code == 200
    assert b"Please fill out all fields" in response.data
    search.assert_not_called()


def test_search_results_survive_redirect(authenticated_client, csrf_token, monkeypatch):
    search = Mock(return_value=[{"name": "Example Cafe", "location": "Austin", "rating": 4.5,
                               "price": "$$", "url": "https://example.com", "image_url": ""}])
    monkeypatch.setattr(routes, "run_restaurant_search", search)
    response = authenticated_client.post("/foodies", data={
        "location": "Austin", "cuisine": "Thai", "price": "$$", "vibe": "Cozy",
        "csrf_token": csrf_token(authenticated_client),
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Example Cafe" in response.data
    search.assert_called_once()


def test_provider_timeout_returns_a_usable_error(authenticated_client, csrf_token, monkeypatch):
    monkeypatch.setattr(routes, "run_restaurant_search", Mock(side_effect=requests.Timeout("provider unavailable")))
    response = authenticated_client.post("/foodies", data={
        "location": "Austin", "cuisine": "Thai", "price": "$$", "vibe": "Cozy",
        "csrf_token": csrf_token(authenticated_client),
    })
    assert response.status_code == 200
    assert b"Something went wrong" in response.data
