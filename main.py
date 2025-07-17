# From CLI, not needed for Flask app

from FoodiesRN.run_foodiesrn import run_food_module
from shared.auth import create_user_table, login_or_signup, get_user_id

def main():
    print("\n🍴 Welcome to PrepRN – Smart Food. In or Out.\n")

    create_user_table()
    username = login_or_signup()
    user_id = get_user_id(username)

    run_food_module(user_id)

if __name__ == "__main__":
    main()
