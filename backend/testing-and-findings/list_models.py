from app.config import settings
from google import genai

def list_models():
    try:
        client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        print("Available models:")
        for m in client.models.list():
            if "gemini" in m.name.lower():
                print(f" - {m.name}")
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    list_models()
