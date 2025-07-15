import google.generativeai as genai
import os

model = "gemini-pro"
def get_genai_model(api_key: str):
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model)

def get_summary(title: str) -> str:
    prompt = f"Write a short, enticing meal description for the dish: '{title}'."
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print("Gemini error:", e)
        return "A delicious and healthy choice!"