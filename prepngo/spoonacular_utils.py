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
def find_by_ingredients(ingredients, number=5):
    api_key = os.getenv("SPOON_API_KEY")

    response = requests.get(
        "https://api.spoonacular.com/recipes/findByIngredients",
        params={
            "apiKey": api_key,
            "ingredients": ",".join(ingredients),
            "number": number,
            "ranking": 1,  # prioritize recipes that use more of the ingredients
            "ignorePantry": False,
            
        }
    )
    response.raise_for_status()
    return response.json()

def get_recipe_information(recipe_id: int) -> dict:
    api_key = os.getenv("SPOON_API_KEY")
    url = f"https://api.spoonacular.com/recipes/{recipe_id}/information"
    params = {"apiKey": api_key}

    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()