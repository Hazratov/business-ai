import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
print(f"API Key found: {api_key is not None}")
if api_key:
    print(f"API Key starts with: {api_key[:10]}...")

try:
    client = OpenAI(api_key=api_key)
    print("OpenAI client initialized successfully.")
except Exception as e:
    print(f"Error initializing OpenAI client: {e}")
