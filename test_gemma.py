import requests
import json

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL      = "gemma2:2b"

payload = {
    "model": MODEL,
    "prompt": "Write a one-line git commit message for adding a login button.",
    "stream": False
}

print("Sending request to Ollama...")
response = requests.post(OLLAMA_URL, json=payload)

if response.status_code == 200:
    data = response.json()
    print("\n--- Gemma says ---")
    print(data["response"])
else:
    print(f"ERROR: {response.status_code}")
    print(response.text)