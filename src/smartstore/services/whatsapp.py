import httpx
import os

GREEN_API_ID = os.getenv("GREEN_API_ID")
GREEN_API_TOKEN = os.getenv("GREEN_API_TOKEN")

async def send_whatsapp_message(chat_id: str, message: str):
    """Envoie un message texte via Green API."""
    url = f"https://api.green-api.com/waInstance{GREEN_API_ID}/sendMessage/{GREEN_API_TOKEN}"
    payload = {
        "chatId": chat_id,
        "message": message
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, timeout=10.0)
            return response.json()
        except Exception as e:
            print(f"Erreur d'envoi WhatsApp: {e}")
            return None