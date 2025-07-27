# Meal Prep Shopping List Automator (Google AI Studio version)
# Prompts user for meal budget, # of people cooking for & dietary restrictions
# Uses Spoonacular API to generate 3 meal prep ideas
# Uses Gemini API to summarize recipes
# Saves to SQLite DB
import os
from typing import List, Dict
from prepngo.spoonacular_utils import get_random_meal_plan
from genai_utils import get_summary, get_genai_model
from google.api_core.exceptions import ResourceExhausted

# Your AI Studio API Key

SPOON_API_KEY = os.getenv('SPOON_API_KEY')
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
model = get_genai_model(GOOGLE_API_KEY, model_name="gemini-1.5-flash")

if not SPOON_API_KEY:
    print(" ERROR: SPOON_API_KEY not set. Export your Spoonacular key first.")
    exit(1)
if not GOOGLE_API_KEY:
    print(" ERROR: GOOGLE_API_KEY environment variable not set.")
    print("Please set it like this in your terminal:")
    print('export GOOGLE_API_KEY="YOUR_KEY_HERE"')
    exit(1)

def _generate_store_suggestions(city: str, state: str, budget: float) -> str:
    prompt = (
        f"I'm planning to grocery shop in {city}, {state} with a budget of ${budget:.2f}. "
        "Please suggest 3 local grocery stores or supermarket chains in that city, each with a plausible price range "
        "(low–high) and a one‑line description. "
        "Format exactly like:\n\n"
        "- Store Name (Price Range: $low–$high): Description\n"
    )
    try:
        response = model.generate_content(prompt)
        return response.text.strip() if response and hasattr(response, "text") else ""
    except ResourceExhausted as e:
        print("⚠️ Gemini quota exceeded when generating store suggestions:", e)
        return "🛒 Store recommendations are temporarily unavailable due to quota limits. Please try again later."
    except Exception as e:
        print("⚠️ Error generating store suggestions:", e)
        return "🛒 Could not generate store recommendations at this time."
    
    
def call_spoonacular(budget, diets):
    # Fetch 3 recipes under budget matching diets from Spoonacular.
    url = 'https://api.spoonacular.com/recipes/random'
    params = {
        'apiKey': SPOON_API_KEY,
        'maxPrice': budget,
        'number': 3,
        'addRecipeInformation': True,
        'diet': ','.join(diets) if diets else None,
    }
    resp = requests.get(url, params={k: v for k, v in params.items() if v is not None})
    resp.raise_for_status()
    return resp.json().get('results', [])
def get_local_stores_from_gemini(city: str, state: str, budget: float) -> str:
    prompt = (
        f"I'm planning to shop for groceries in {city}, {state}. "
        f"My budget is around ${budget:.2f}. "
        "Please suggest 5 local grocery stores or supermarket chains in that city, "
        "with a plausible price range for each in dollars (low–high), and a short one-line description. "
        "Format them exactly like this:\n\n"
        "- Store Name (Price Range: $low–$high): Description\n\n"
        "Keep it concise and realistic."
    )
    resp = model.generate_content(prompt)
    return resp.text.strip()
def summarize_with_genai(text):
    # Summarize recipe description with Gemini and Spoonacular.
    if not text:
        return ""
    resp = model.generate_content(f"Summarize this recipe:\n\n{text}")
    return resp.text.strip()
    
    response = model.generate_content(prompt)
    text = response.text

def display_meals(meals):
    print("\n=== Meal Suggestions ===")
    for i, m in enumerate(meals, 1):
        print(f"[{i}] {m['title']} — ${m['price']:.2f}")
        print(f"    Diets: {', '.join(m['diets']) or 'none'}")
        print(f"    Summary: {m['summary']}\n")

def generate_shopping_list_with_genai(recipes: List[dict]) -> str:
    #ask gemini for recipe grocery list
    titles = [r['title'] for r in recipes]
    prompt = (
        "Here are five recipes I plan to make:\n"
        + "\n".join(f"- {t}" for t in titles)
        + "\n\nPlease provide a combined shopping list of ingredients organized by category (produce, dairy, pantry, etc.). "
    )
    resp = model.generate_content(prompt)
    return resp.text.strip()

def main(user_input: dict) -> dict:
    budget = float(user_input["budget"])
    servings = int(user_input["servings"])
    diets = user_input.get('diets', [])
    meal_type = user_input.get("meal_type", "")
    grocery = user_input.get("grocery", "yes")
    pantry = user_input.get("pantry", [])

    tags = [d.strip().lower() for d in diets if d]
    if meal_type:
        tags.append(meal_type.strip().lower())

    loc = user_input.get("location", "")
    city, state = (loc.split(",") + [""])[:2]
    city, state = city.strip(), state.strip()

    # If user doesn't want to go grocery shopping
    if grocery.lower() == "no":
        from prepngo.spoonacular_utils import find_by_ingredients, get_recipe_information

        basic_meals = find_by_ingredients(pantry, number=5)

        meals = []
        for item in basic_meals:
            full_details = get_recipe_information(item['id'])
            meal = {
                "title": full_details.get("title", ""),
                "summary": get_summary(full_details.get("title", "")),
                "price": 0.0,  # pantry meals are free
                "diets": full_details.get("diets", []),
                "source_url": full_details.get("sourceUrl", "")
            }
            meals.append(meal)

        return {
            "meals": meals,
            "stores": "✅ No grocery stores needed. All meals use pantry ingredients!"
        }

    # Otherwise, fetch random meal plan with grocery shopping
    meals = get_random_meal_plan(budget, servings, tags)
    stores = _generate_store_suggestions(city, state, budget)
    for meal in meals:
        meal['summary'] = get_summary(meal['title'])

    return {
        "meals": meals,
        "stores": stores
    }
