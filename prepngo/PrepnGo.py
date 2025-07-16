# Meal Prep Shopping List Automator (Google AI Studio version)
# Prompts user for meal budget, # of people cooking for & dietary restrictions
# Uses Spoonacular API to generate 3 meal prep ideas
# Uses Gemini API to summarize recipes
# Saves to SQLite DB
import os
import google.generativeai as genai
from prepngo.spoonacular_utils import get_meal_plan
from genai_utils import get_summary
import requests
from typing import List
from .database_functions import (
    init_db,
    save_request,
    save_meals,
    save_feedback,
    save_local_stores
)
from genai_utils import get_genai_model

# Your AI Studio API Key

SPOON_API_KEY = os.getenv('SPOON_API_KEY')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

if not SPOON_API_KEY:
    print(" ERROR: SPOON_API_KEY not set. Export your Spoonacular key first.")
    exit(1)
if not GOOGLE_API_KEY:
    print(" ERROR: GOOGLE_API_KEY environment variable not set.")
    print("Please set it like this in your terminal:")
    print('export GOOGLE_API_KEY="YOUR_KEY_HERE"')
    exit(1)

# Initialize Gemini
model = get_genai_model(GOOGLE_API_KEY, model_name="gemini-1.5-flash")
DB_PATH = 'preprn.db'

def call_spoonacular(budget, diets):
    # Fetch 3 recipes under budget matching diets from Spoonacular.
    url = 'https://api.spoonacular.com/recipes/complexSearch'
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

def main(user_input: dict) -> list:

    budget = float(user_input["budget"])
    servings = int(user_input["servings"])
    diets = user_input.get('diets', [])
    if isinstance(diets, str):
        diets = [diets]
    # user_id = user_input.get('user_id')

    # Get meals from Spoonacular API
    meals = get_meal_plan(budget, servings, diets)

    # Add Gemini AI summaries if needed
    for meal in meals:
        meal['summary'] = get_summary(meal['title'])

    return meals