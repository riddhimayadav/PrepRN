# Import the Gemini AI client and os for environment variables
import google.generativeai as genai
import os


# Function to initialize and return a Gemini generative model
def get_genai_model(api_key: str, model_name: str = "gemini-1.5-flash"):
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)

# Function to generate a short meal description using Gemini AI
def get_summary(title: str, model=None) -> str:
    prompt = f"Write a short, enticing meal description for the dish: '{title}'."
    try:
        if model is None:
            # If no model is passed, load API key from env and get the default model
            api_key = os.getenv("GOOGLE_API_KEY")
            model = get_genai_model(api_key, "gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        # Print error and return a fallback description
        print("Gemini error:", e)
        return "A delicious and healthy choice!"
