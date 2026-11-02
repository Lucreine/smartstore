import os

import httpx
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("RODIUMAI_API_KEY")
base_url = os.getenv("RODIUMAI_URL", "https://api.rodiumai.io/v1")
model = os.getenv("RODIUMAI_MODEL")

if not api_key or not model:
    raise SystemExit("Vérifie RODIUMAI_API_KEY et RODIUMAI_MODEL dans .env")

response = httpx.post(
    f"{base_url.rstrip('/')}/chat/completions",
    headers={"Authorization": f"Bearer {api_key}"},
    json={
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": "Bonjour, présente-moi brièvement la boutique et ses pagnes.",
            }
        ],
        "max_tokens": 150,
    },
    timeout=60,
)

print("HTTP Status:", response.status_code)

if response.is_success:
    data = response.json()
    print("Réponse de l'IA :")
    print(data["choices"][0]["message"]["content"])
else:
    print(response.text)