from unittest.mock import Mock

from prepngo import PrepnGo as planner


def test_grocery_flow_preserves_meal_type_and_uses_fallback(monkeypatch):
    provider = Mock(return_value=[{"title": "Example meal", "price": 4.0, "diets": [], "source_url": "https://example.com"}])
    monkeypatch.setattr(planner, "get_random_meal_plan", provider)
    monkeypatch.setattr(planner, "_generate_genai_description_with_timeout", lambda *args, **kwargs: None)
    result = planner.main({"budget": "25", "servings": "2", "diets": ["vegetarian"],
                           "meal_type": "dinner", "location": "Austin, TX", "grocery": "yes"})
    assert result["meals"][0]["meal_type"] == "dinner"
    assert result["meals"][0]["summary"]
    provider.assert_called_once_with(25.0, 2, ["vegetarian", "dinner"])


def test_pantry_flow_uses_ingredients_without_grocery_cost(monkeypatch):
    monkeypatch.setattr(planner, "find_by_ingredients", Mock(return_value=[{"id": 7}]))
    monkeypatch.setattr(planner, "get_recipe_information", Mock(return_value={"title": "Rice and beans", "diets": [], "sourceUrl": "https://example.com"}))
    monkeypatch.setattr(planner, "_generate_genai_description_with_timeout", lambda *args, **kwargs: None)
    monkeypatch.setattr(planner.time, "sleep", lambda *args: None)
    result = planner.main({"budget": "0", "servings": "1", "diets": [], "location": "Austin, TX",
                           "meal_type": "lunch", "grocery": "no", "pantry": ["rice", "beans"]})
    assert result["meals"][0]["price"] == 0.0
    assert "No grocery stores needed" in result["stores"]
