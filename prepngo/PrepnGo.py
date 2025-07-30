# Meal Prep Shopping List Automator (Hybrid GenAI + Templates)
# Prompts user for meal budget, # of people cooking for & dietary restrictions
# Uses Spoonacular API to generate 3 meal prep ideas
# Uses GenAI with timeouts for descriptions and store suggestions, falls back to templates
# Saves to SQLite DB
import os
import random
import time
import threading
from typing import List, Dict, Optional
from prepngo.spoonacular_utils import get_random_meal_plan, find_by_ingredients, get_recipe_information
from genai_utils import get_genai_model
from google.api_core.exceptions import ResourceExhausted

# Your API Keys
SPOON_API_KEY = os.getenv('SPOON_API_KEY')
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not SPOON_API_KEY:
    print(" ERROR: SPOON_API_KEY not set. Export your Spoonacular key first.")
    exit(1)

# Template descriptions for meals for fallback
MEAL_DESCRIPTIONS = [
    "A delicious and nutritious meal that's perfect for any time of day. This recipe combines fresh ingredients with time-tested cooking techniques to create something truly memorable that will satisfy both your hunger and your craving for great flavors.",
    "Quick and easy to prepare with simple, wholesome ingredients that you likely already have in your kitchen. Despite its simplicity, this dish delivers complex flavors and satisfying textures that make it feel like a gourmet meal without the complicated preparation.",
    "A flavorful dish that brings comfort and satisfaction to your table while filling your home with amazing aromas. This recipe has that special quality of making any ordinary day feel a little more special, perfect for both casual weeknight dinners and weekend gatherings.",
    "Fresh ingredients come together in this tasty and healthy recipe that celebrates the natural flavors of each component. You'll love how the different elements complement each other to create a harmonious and nutritious meal that feels both indulgent and wholesome.",
    "A classic favorite that never goes out of style - perfect for meal prep and busy schedules. This timeless recipe has been loved by generations because it consistently delivers great taste, reliable results, and the kind of satisfaction that keeps you coming back for more.",
    "Packed with nutrients and bursting with flavor in every bite, this recipe proves that healthy eating doesn't mean sacrificing taste. The vibrant colors and bold flavors make this dish as visually appealing as it is delicious, perfect for nourishing your body and soul.",
    "Simple yet elegant, this dish is sure to become a household favorite that everyone will request again and again. The straightforward preparation belies the sophisticated flavors that develop during cooking, making it perfect for both everyday meals and special occasions.",
    "A hearty meal that's both filling and incredibly satisfying, designed to comfort and nourish you after a long day. This substantial dish provides the kind of deep satisfaction that comes from a well-balanced meal made with care and attention to flavor.",
    "Light and refreshing while still being completely satisfying, this recipe strikes the perfect balance between healthy and delicious. It's the kind of meal that leaves you feeling energized and content, never heavy or overly full, making it ideal for any season.",
    "Bold flavors and vibrant ingredients make this dish truly special and memorable for anyone who tries it. The exciting combination of tastes and textures creates a culinary adventure that transforms ordinary ingredients into something extraordinary and crave-worthy.",
    "Comfort food at its finest - warm, inviting, and delicious in the way that only true comfort food can be. This recipe has that magical quality of making you feel better with every bite, perfect for cozy nights in or when you need a little extra warmth in your day.",
    "A perfect balance of taste and nutrition for the health-conscious cook who refuses to compromise on flavor. This thoughtfully crafted recipe provides all the nutrients your body needs while delivering the satisfying taste your palate craves, proving that healthy can be incredibly delicious.",
    "Easy weeknight dinner that doesn't compromise on flavor or quality, perfect for those busy evenings when you want something special. Despite the quick preparation time, this recipe delivers restaurant-quality results that will impress your family and make dinner feel like a treat.",
    "Restaurant-quality taste you can easily recreate at home with ingredients and techniques that are accessible to any home cook. This recipe brings the sophistication of fine dining to your kitchen, allowing you to enjoy an elevated meal experience without leaving your house.",
    "A crowd-pleaser that works great for families and meal planning, guaranteed to satisfy even the pickiest eaters. This versatile recipe scales easily for large groups and reheats beautifully, making it perfect for busy families who want delicious, stress-free meals throughout the week.",
    "Wholesome ingredients combined to create something truly delightful that nourishes both body and spirit. Each component in this recipe has been carefully chosen not just for its nutritional value, but for how it contributes to the overall harmony and satisfaction of the final dish.",
    "Quick preparation time with maximum flavor payoff, proving that great meals don't always require hours in the kitchen. This efficient recipe uses smart cooking techniques and flavor-building shortcuts to deliver impressive results in minimal time, perfect for today's busy lifestyle.",
    "A versatile dish that pairs well with many different sides and adapts beautifully to your preferences and dietary needs. This flexible recipe serves as a perfect foundation that you can customize with your favorite ingredients or whatever you have available in your kitchen.",
    "Fresh, seasonal ingredients shine in this well-balanced meal that celebrates the natural beauty and flavor of quality produce. This recipe lets each ingredient speak for itself while creating a harmonious composition that highlights the best of what nature has to offer.",
    "Perfect for busy schedules without sacrificing taste or nutrition, this recipe understands that great food should fit into real life. It's designed for people who want to eat well despite their hectic schedules, proving that convenience and quality can absolutely go hand in hand.",
    "A satisfying meal that feels both indulgent and guilt-free, striking that perfect balance we all crave in our food choices. This recipe delivers rich, complex flavors and satisfying textures while still being mindful of nutrition and overall wellness, making it a win-win for your taste buds and your health.",
    "Simple cooking techniques yield surprisingly complex flavors that will amaze anyone who tries this deceptively straightforward recipe. The magic happens in the careful timing and combination of ingredients, creating depth and sophistication that belies the easy preparation method.",
    "Ideal for meal prep - tastes even better the next day as the flavors have time to meld and develop into something even more delicious. This recipe is a meal prepper's dream, maintaining its texture and actually improving in taste over time, making your week of meals even more enjoyable.",
    "A nourishing dish that fuels your body and satisfies your taste buds while providing the sustained energy and satisfaction you need. This well-balanced recipe combines protein, healthy carbohydrates, and essential nutrients in a way that supports your active lifestyle and overall wellness goals.",
    "Easy cleanup and maximum flavor make this a weeknight winner that busy families will love for its practicality and taste. This one-pot wonder minimizes kitchen mess while maximizing deliciousness, proving that the best recipes are often the ones that make your life easier without compromising quality.",
    "Colorful, vibrant, and packed with wholesome goodness that makes eating healthy feel like a celebration rather than a chore. The beautiful presentation and exciting flavors in this recipe prove that nutritious food can be just as visually stunning and delicious as any indulgent dish.",
    "A comforting meal that brings the family together around the table and creates those special moments we all treasure. This recipe has that wonderful quality of fostering connection and conversation, turning a simple meal into a meaningful shared experience that strengthens bonds.",
    "Healthy eating never tasted so good with this flavorful creation that redefines what nutritious food can be. This recipe proves that taking care of your health doesn't mean sacrificing the joy and pleasure of eating, delivering both wellness benefits and incredible taste in every serving.",
    "Minimal ingredients, maximum impact - simplicity at its best, demonstrating how great cooking is often about letting quality ingredients shine. This recipe celebrates the beauty of restraint, showing how a few carefully chosen components can create something far more satisfying than complicated dishes with endless ingredient lists.",
    "A delightful dish that proves healthy food can be absolutely delicious while still providing all the nutrition your body needs to thrive. This recipe bridges the gap between wellness and pleasure, creating a meal that satisfies your health goals and your desire for truly enjoyable food."
]

def get_random_description():
    """Return a random description from our template list."""
    return random.choice(MEAL_DESCRIPTIONS)

def _generate_genai_description_with_timeout(meal_title: str, timeout: float = 2.0) -> Optional[str]:
    """
    Try to generate a meal description using GenAI with a timeout.
    Returns None if timeout is exceeded or if GenAI fails.
    """
    if not GOOGLE_API_KEY:
        return None
    
    result = [None]  # Use list to allow modification from inner function
    exception_occurred = [False]
    
    def genai_task():
        try:
            model = get_genai_model(GOOGLE_API_KEY)
            prompt = f"Write a short, appetizing description (2-3 sentences) for this meal: {meal_title}. Focus on taste, preparation style, and appeal."
            
            response = model.generate_content(prompt)
            if response and response.text:
                result[0] = response.text.strip()
        except Exception as e:
            print(f"[DEBUG] GenAI description failed for '{meal_title}': {e}")
            exception_occurred[0] = True
    
    # Start the GenAI task in a separate thread
    thread = threading.Thread(target=genai_task)
    thread.daemon = True
    thread.start()
    thread.join(timeout=timeout)
    
    if thread.is_alive():
        print(f"[DEBUG] GenAI description timeout ({timeout}s) for '{meal_title}', using fallback")
        return None
    elif exception_occurred[0]:
        return None
    else:
        return result[0]

def _generate_store_suggestions_with_genai_timeout(city: str, state: str, budget: float, timeout: float = 3.0) -> str:
    """
    Try to generate store suggestions using GenAI with timeout, fallback to templates.
    """
    if GOOGLE_API_KEY:
        result = [None]
        exception_occurred = [False]
        
        # def genai_task():
        #     try:
        #         model = get_genai_model(GOOGLE_API_KEY)
        #         prompt = f"""Suggest 3 grocery stores in {city}, {state} for a budget of ${budget:.2f}. 
        #         Include store names, brief descriptions, and estimated price ranges. 
        #         Format as a bulleted list with store name, price range, and one sentence description."""
                
        #         response = model.generate_content(prompt)
        #         if response and response.text:
        #             result[0] = response.text.strip()
        #     except Exception as e:
        #         print(f"[DEBUG] GenAI store suggestions failed: {e}")
        #         exception_occurred[0] = True
        
        # # Start the GenAI task in a separate thread
        # thread = threading.Thread(target=genai_task)
        # thread.daemon = True
        # thread.start()
        # thread.join(timeout=timeout)
        
        # if thread.is_alive():
        #     print(f"[DEBUG] GenAI store suggestions timeout ({timeout}s), using fallback")
        # elif not exception_occurred[0] and result[0]:
        #     print("[DEBUG] Using GenAI store suggestions")
        #     return result[0]
    
    # Fallback to template-based store suggestions
    print("[DEBUG] Using template store suggestions")
    return _generate_template_store_suggestions(city, state, budget)

def _generate_template_store_suggestions(city: str, state: str, budget: float) -> str:
    """Generate store suggestions using template patterns as fallback."""
    
    # Common grocery store chains by region/budget for fallback
    budget_stores = [
        "Walmart Supercenter (Price Range: $15–$35): Great for budget-friendly groceries with a wide selection",
        "Aldi (Price Range: $12–$28): Known for quality products at unbeatable prices",
        "Food 4 Less (Price Range: $14–$32): Warehouse-style savings on everyday groceries"
    ]
    
    mid_range_stores = [
        "Kroger (Price Range: $20–$45): Fresh produce and quality meats with good weekly deals",
        "Safeway (Price Range: $22–$48): Reliable selection with frequent sales and promotions",
        "Giant Food (Price Range: $21–$46): Fresh ingredients with a focus on quality and value"
    ]
    
    premium_stores = [
        "Whole Foods Market (Price Range: $35–$75): Organic and natural products with premium quality",
        "Fresh Market (Price Range: $32–$68): Gourmet ingredients and specialty items",
        "Harris Teeter (Price Range: $28–$58): Quality groceries with excellent customer service"
    ]
    
    # Select stores based on budget
    if budget < 25:
        selected_stores = random.sample(budget_stores, 2) + random.sample(mid_range_stores, 1)
    elif budget < 50:
        selected_stores = random.sample(mid_range_stores, 2) + random.sample(budget_stores, 1)
    else:
        selected_stores = random.sample(premium_stores, 2) + random.sample(mid_range_stores, 1)
    
    # Format the response
    result = f"Recommended grocery stores in {city}, {state}:\n\n"
    for store in selected_stores:
        result += f"- {store}\n"
    
    return result.strip()

def main(user_input: dict) -> dict:
    budget = float(user_input["budget"]) if user_input["budget"] else 0.0
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
        print("[DEBUG] Pantry ingredients:", pantry)
        basic_meals = find_by_ingredients(pantry, number=5)
        print("[DEBUG] Spoonacular returned:", basic_meals)

        meals = []
        for item in basic_meals:
            try:
                full_details = get_recipe_information(item['id'])
                meal_title = full_details.get("title", "")
                
                # Try GenAI description with 2 second timeout, fallback to template
                genai_description = _generate_genai_description_with_timeout(meal_title, timeout=2.0)
                description = genai_description if genai_description else get_random_description()
                
                meal = {
                    "title": meal_title,
                    "summary": description,
                    "price": 0.0,
                    "diets": full_details.get("diets", []),
                    "source_url": full_details.get("sourceUrl", ""),
                    "meal_type": meal_type
                }
                meals.append(meal)
                time.sleep(1.2)  # Prevent hitting rate limit (esp. on free tier)
            except Exception as e:
                print("[ERROR] Failed to fetch details for recipe:", item['id'], e)

        return {
            "meals": meals,
            "stores": "No grocery stores needed. All meals use pantry ingredients!"
        }

    # Otherwise, fetch random meal plan with grocery shopping
    meals = get_random_meal_plan(budget, servings, tags)
    
    # Generate store suggestions with GenAI timeout (3 seconds), fallback to templates
    stores = _generate_store_suggestions_with_genai_timeout(city, state, budget, timeout=3.0)
    
    # Add descriptions (GenAI with 2 second timeout) and meal_type to each meal
    for meal in meals:
        meal_title = meal.get('title', '')
        
        # Try GenAI description with 2 second timeout, fallback to template
        genai_description = _generate_genai_description_with_timeout(meal_title, timeout=2.0)
        meal['summary'] = genai_description if genai_description else get_random_description()
        meal['meal_type'] = meal_type

    return {
        "meals": meals,
        "stores": stores
    }