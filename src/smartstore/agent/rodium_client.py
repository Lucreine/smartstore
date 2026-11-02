import os
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()


class RodiumClient:
    """Client HTTP pour communiquer avec l'API RodiumAI."""

    def __init__(self) -> None:
        self.api_key = os.getenv("RODIUMAI_API_KEY")
        self.base_url = os.getenv(
            "RODIUMAI_URL",
            "https://api.rodiumai.io/v1",
        ).rstrip("/")
        self.model = os.getenv("RODIUMAI_MODEL")

        if not self.api_key:
            raise ValueError("RODIUMAI_API_KEY est absente du fichier .env")

        if not self.model:
            raise ValueError("RODIUMAI_MODEL est absent du fichier .env")

    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Envoie une conversation à RodiumAI."""

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 1500,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )

            response.raise_for_status()
            return response.json()