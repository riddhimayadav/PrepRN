from FoodiesRN.run_foodiesrn import run_foodiesrn

def main():
    print("\n🍴 Welcome to PrepRN – Smart Food. In or Out.\n")
    while True:
        choice = input("What do you want to do? (in/out/exit): ").lower()
        if choice == "out":
            run_foodiesrn()
        elif choice == "in":
            print("PrepNGo is under construction 🛠️\n")
        elif choice == "exit":
            print("Goodbye 👋")
            break
        else:
            print("Invalid option. Please type 'in', 'out', or 'exit'.\n")

if __name__ == "__main__":
    main()
