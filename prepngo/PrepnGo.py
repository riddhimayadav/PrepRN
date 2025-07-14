# Meal Prep Shopping List Automator (Google AI Studio version)
# Prompts user for meal budget, # of people cooking for & dietary restrictions
# Uses Spoonacular API to generate 3 meal prep ideas
# Uses Gemini API to summarize recipes
# Saves to SQLite DB
import os
import sqlite3
import google.generativeai as genai
import requests
import pyfiglet
from colorama import init, Fore, Style
from typing import List
from .database_functions import (
    init_db,
    save_request,
    save_meals,
    save_feedback,
    save_local_stores
)

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
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")
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

def main(user_id):
    init(autoreset=True)

    ascii_banner = pyfiglet.figlet_format("Prep and Go ")
    print(Fore.MAGENTA + ascii_banner)
    print(Fore.MAGENTA + Style.BRIGHT + "Welcome to the Prep and Go!\n")

    # 1. Init DB
    conn = init_db(DB_PATH)

    # 2. Get user budget
    while True:
        try:
            budget = float(input("Enter your meal budget (e.g. 25.0): ").strip())
            break
        except ValueError:
            print("Please enter a valid number.")
    
    # 3 Prompt for servings
    while True:
        try:
            servings = int(input("How many people are you cooking for? ").strip())
            if servings < 1:
                raise ValueError
            break
        except ValueError:
            print("Please enter a valid integer (at least 1).")

    # 4. Get user dietary restrictions
    diets_input = input("Enter any dietary restrictions separated by commas (press Enter if none): ").strip()
    diets = [d.strip() for d in diets_input.split(",") if d.strip()]

    city = input("Enter your city: ").strip()
    state = input("Enter your state (2-letter abbreviation): ").strip()

    # 4.6 Ask Gemini for local store ideas
    print("\nAsking Gemini for local stores in your area…\n")
    local_stores_text = get_local_stores_from_gemini(city, state, budget)
    print("=== Gemini's Suggested Local Stores ===")
    print(local_stores_text)

    # 5. Save request
    request_id = save_request(conn, user_id, budget, servings, diets)
    print(f"Request #{request_id} saved with budget ${budget}, servings {servings}, diets {diets}.")

    save_local_stores(conn, request_id, city, state, local_stores_text)


    # 5. Fetch recipes using Spoonacular API
    try:
        raw = call_spoonacular(budget, diets)
    except requests.HTTPError as e:
        print(f"No meal ideas were generated. Please try with different parameters or try again later: {e}")
        conn.close()
        return
    # 6. Show meals and prepare for DB insert
    meals_to_save = []
    print("\nHere are your meal suggestions:\n")

    for item in raw:
        base_price = item.get('pricePerServing', 0) / 100
        total_price = base_price * servings
        summary = summarize_with_genai(item.get('summary', ''))
        
        meals_to_save.append({
            'title': item.get('title', 'Unknown'),
            'price': item.get('pricePerServing', 0) / 100,
            'diets': item.get('diets', []),
            'summary': summary,
            'source_url': item.get('sourceUrl', '#'),
        })
    if not meals_to_save:
        print("No recipes found under that budget/diet combination.")
        conn.close()
        return
    # 7. Show the meals and save them
    display_meals(meals_to_save)
    save_meals(conn, request_id, meals_to_save)

    # optional: shopping list
    want_list = input("\nWould you like a consolidated shopping list? (yes/no): ").strip().lower()
    if want_list.startswith('y'):
        print("\nGenerating shopping list…\n")
        shopping_list = generate_shopping_list_with_genai(meals_to_save)
        print(shopping_list)

    # 8. Feedback
    print("\n--- Feedback ---")
    feedback = input("Are you satisfied with these meal suggestions? (yes/no): ").strip().lower()
    satisfied = feedback in ["yes", "y"]
    comments = input("Any comments? (optional): ").strip()
    save_feedback(conn, request_id, satisfied, comments)
    conn.close()

    if satisfied:
        print("\nGreat! Thanks for your feedback.")
    else:
        print("\nSorry to hear that. We'll improve next time.")

if __name__ == '__main__':
    main()