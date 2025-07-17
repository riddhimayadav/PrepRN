import requests
import os

API_KEY = os.getenv("SPOON_API_KEY")

def get_random_meal_plan(budget, servings, tags):
    """
    budget & servings are available if you want to compute per-meal price,
    but the 'random' endpoint only supports 'tags'.
    """
    url = "https://api.spoonacular.com/recipes/random"
    # Lowercase & drop empty
    clean_tags = [t.lower() for t in tags if t]
    params = {
        "apiKey": API_KEY,
        "number": 3,
        "tags": ",".join(clean_tags) or None,
    }
    resp = requests.get(url, params={k: v for k, v in params.items() if v})
    resp.raise_for_status()
    data = resp.json().get("recipes", [])
    meals = []
    for item in data:
        meals.append({
            "title":       item.get("title", ""),
            "price":       round(item.get("pricePerServing", 0) / 100, 2),
            "diets":       item.get("diets", []),
            "summary":     "",
            "source_url":  item.get("sourceUrl", "")
        })
    return meals