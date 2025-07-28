import unittest
from prepngo.PrepnGo import main

class TestPrepnGoMain(unittest.TestCase):

    def test_main_with_grocery_shopping(self):
        # Test normal grocery shopping flow
        user_input = {
            "budget": "50",
            "servings": "3",
            "diets": ["vegetarian"],
            "meal_type": "dinner",
            "location": "Austin, TX",
            "grocery": "yes",
            "pantry": []
        }
        result = main(user_input)
        self.assertIn("meals", result)
        self.assertIsInstance(result["meals"], list)
        self.assertGreaterEqual(len(result["meals"]), 1)
        self.assertIn("stores", result)
        self.assertIsInstance(result["stores"], str)

    def test_main_with_pantry_only(self):
        # Test pantry-only flow (no grocery shopping)
        user_input = {
            "budget": "0",
            "servings": "2",
            "diets": [],
            "meal_type": "lunch",
            "location": "Los Angeles, CA",
            "grocery": "no",
            "pantry": ["rice", "beans", "onion"]
        }
        result = main(user_input)
        self.assertIn("meals", result)
        self.assertTrue(all(meal["price"] == 0.0 for meal in result["meals"]))
        self.assertIn("stores", result)
        self.assertIn("No grocery stores needed", result["stores"])

    def test_meal_type_persists(self):
        # Make sure meal_type is saved in the meal object
        user_input = {
            "budget": "30",
            "servings": "1",
            "diets": [],
            "meal_type": "breakfast",
            "location": "Chicago, IL",
            "grocery": "yes",
            "pantry": []
        }
        result = main(user_input)
        for meal in result["meals"]:
            self.assertEqual(meal.get("meal_type"), "breakfast")

if __name__ == '__main__':
    unittest.main()
