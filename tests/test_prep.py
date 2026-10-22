from unittest.mock import Mock

import app as routes


def test_meal_request_passes_validated_input(authenticated_client, csrf_token, monkeypatch):
    planner = Mock(return_value={"meals": [], "stores": "Example stores"})
    monkeypatch.setattr(routes, "get_prepngo_meals", planner)
    response = authenticated_client.post("/prep", data={
        "location": "Austin, TX", "budget": "25", "servings": "2", "grocery": "yes", "meal_type": "dinner",
        "csrf_token": csrf_token(authenticated_client),
    }, follow_redirects=True)
    assert response.status_code == 200
    planner.assert_called_once()
    assert planner.call_args.args[0]["budget"] == 25.0


def test_invalid_budget_never_calls_provider(authenticated_client, csrf_token, monkeypatch):
    planner = Mock()
    monkeypatch.setattr(routes, "get_prepngo_meals", planner)
    response = authenticated_client.post("/prep", data={
        "location": "Austin", "budget": "not-a-number", "servings": "2", "grocery": "yes",
        "csrf_token": csrf_token(authenticated_client),
    }, follow_redirects=True)
    assert response.status_code == 200
    planner.assert_not_called()


def test_invalid_servings_never_calls_provider(authenticated_client, csrf_token, monkeypatch):
    planner = Mock()
    monkeypatch.setattr(routes, "get_prepngo_meals", planner)
    response = authenticated_client.post("/prep", data={
        "location": "Austin", "budget": "25", "servings": "0", "grocery": "yes",
        "csrf_token": csrf_token(authenticated_client),
    }, follow_redirects=True)
    assert response.status_code == 200
    planner.assert_not_called()
