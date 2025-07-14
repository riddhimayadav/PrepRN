import google.generativeai as genai

def get_genai_model(api_key: str, model_name: str = "gemini-pro"):
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)