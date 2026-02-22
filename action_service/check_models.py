from dotenv import dotenv_values

try:
    from google import genai
except ImportError:
    print("google.genai not installed")
    exit()

env = dotenv_values(".env")
GEMINI_KEY = env.get("GEMINI_API_KEY")

if not GEMINI_KEY:
    print("GEMINI_API_KEY not found in .env")
    exit()

client = genai.Client(api_key=GEMINI_KEY)

print("Listing available models:\n")

for model in client.models.list():
    print(model.name)
