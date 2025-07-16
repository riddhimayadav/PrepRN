import requests
import os

API_KEY = os.getenv("SPOON_API_KEY")  # From your .env file

def get_random_meal_plan(budget, servings, diets):
    max_price_per_meal = budget / servings
    url = "https://api.spoonacular.com/recipes/random"
    params = {
        "apiKey": API_KEY,
        "number": 3,
        "tags": ",".join(diets) if diets else None
    }
    resp = requests.get(url, params={k: v for k, v in params.items() if v})
    resp.raise_for_status()
    data = resp.json()
    return [
        {
          "title": r["title"],
          "price": r.get("pricePerServing", 0) / 100,
          "diets": r.get("diets", []),
          "summary": "",
          "source_url": r.get("sourceUrl", "")
        }
        for r in data.get("recipes", [])
    ]
