import requests
import os

API_KEY = os.getenv("SPOON_API_KEY")  # From your .env file

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

    print("\n--- DEBUG: Calling Spoonacular ---")
    print("URL:", url)
    print("Params:", params)

    response = requests.get(url, params=params)
    print("Status Code:", response.status_code)
    print("Raw Response:", response.text[:500])

    try:
        data = response.json()
    except Exception as e:
        print("❌ ERROR parsing JSON:", e)
        return []

    meals = []
    for item in data.get("results", []):
        meals.append({
            "title": item["title"],
            "price": item.get("pricePerServing", 0) / 100,
            "diets": item.get("diets", []),
            "summary": "",  # Gemini will add this later
            "source_url": item.get("sourceUrl", "")
        })

    print("Parsed Meals:", meals)

    return meals
