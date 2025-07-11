from FoodiesRN.run_foodiesrn import run_foodiesrn
from shared.auth import create_user_table, login_or_signup, get_user_id

def main():
    print("\n🍴 Welcome to PrepRN – Smart Food. In or Out.\n")

    create_user_table()
    username = login_or_signup()
    user_id = get_user_id(username)

    while True:
        choice = input("What do you want to do? (in/out/exit): ").lower()
        if choice == "out":
            run_foodiesrn(user_id)
        elif choice == "in":
            print("PrepNGo is under construction 🛠️\n")
        elif choice == "exit":
            print("Goodbye 👋")
            break
        else:
            print("Invalid option. Please type 'in', 'out', or 'exit'.\n")

if __name__ == "__main__":
    main()
