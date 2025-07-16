import google.generativeai as genai
import os

def get_genai_model(api_key: str, model_name: str = "gemini-pro"):
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)

def get_summary(title: str, model=None) -> str:
    prompt = f"Write a short, enticing meal description for the dish: '{title}'."
    try:
        if model is None:
            api_key = os.getenv("GOOGLE_API_KEY")
            model = get_genai_model(api_key)
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print("Gemini error:", e)
        return "A delicious and healthy choice!"
