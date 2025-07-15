import requests
import os

API_KEY = os.getenv("SPOONACULAR_API_KEY")  # From your .env file

def get_meal_plan(budget, servings, diets):
    max_price_per_meal = budget / servings

    diet_param = ",".join(diets) if diets else ""

    url = "https://api.spoonacular.com/recipes/complexSearch"
    params = {
        "apiKey": API_KEY,
        "number": 3,
        "addRecipeInformation": True,
        "diet": diet_param,
        "maxPrice": max_price_per_meal
    }

    response = requests.get(url, params=params)
    data = response.json()

    meals = []
    for item in data.get("results", []):
        meals.append({
            "title": item["title"],
            "price": item.get("pricePerServing", 0) / 100,
            "diets": item.get("diets", []),
            "summary": "",  # Gemini will add this later
            "source_url": item.get("sourceUrl", "")
        })

    return meals
