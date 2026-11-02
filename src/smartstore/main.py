import logging
from typing import Any
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from smartstore.agent.orchestrator import run_agent
from smartstore.tools.orders import (
    load_orders,
    approve_order,
    reject_order,
)
import os
from smartstore.services.whatsapp import send_whatsapp_message
from smartstore.agent.orchestrator import run_agent
from smartstore.tools.orders import load_orders, approve_order, reject_order

app = FastAPI(
    title="SmartStore API",
    description=(
        "API du vendeur intelligent de la boutique "
        "de pagnes et accessoires du marché Dantokpa."
    ),
    version="1.0.0",
)

class ChatRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=2000,
        description="Message envoyé par le client.",
    )

class ChatResponse(BaseModel):
    success: bool
    response: str
    steps: int
    evaluation: dict[str, Any] | None = None
    trace: list[dict[str, Any]] | None = None

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "SmartStore API",
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        result = await run_agent(request.message)
        return ChatResponse(
            success=result["success"],
            response=result["response"],
            steps=result["steps"],
            evaluation=result.get("evaluation"),
            trace=result.get("trace"),
        )
    except Exception:
        logging.exception("Erreur pendant l'exécution de l'agent")
        raise HTTPException(
            status_code=503,
            detail="Le service est temporairement indisponible.",
        ) from None


@app.get("/orders/pending")
async def get_pending_orders():
    """Liste les commandes en attente de validation par Afi."""
    orders = load_orders()

    pending = [
        order for order in orders
        if order.get("status") == "pending"
    ]

    return {
        "success": True,
        "count": len(pending),
        "orders": pending,
    }

@app.post("/orders/{order_id}/approve")
async def validate_order(order_id: int):
    """Afi valide une commande et déclenche la diminution du stock."""
    result = approve_order(order_id)

    if not result["success"]:
        status_code = (
            404 if result["message"] == "Commande introuvable."
            else 409
        )
        raise HTTPException(
            status_code=status_code,
            detail=result["message"],
        )

    return result

@app.post("/orders/{order_id}/reject")
async def refuse_order(order_id: int):
    """Afi refuse une commande sans modifier le stock."""
    result = reject_order(order_id)

    if not result["success"]:
        status_code = (
            404 if result["message"] == "Commande introuvable."
            else 409
        )
        raise HTTPException(
            status_code=status_code,
            detail=result["message"],
        )

    return result

security = HTTPBearer()
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "mon_secret_securise")
AFI_CHAT_ID = os.getenv("AFI_CHAT_ID", "2290167535145@c.us") # Le numéro WhatsApp d'Afi

# Mémoire simple de dédoublonnage (en production, utilise Redis ou KV)
processed_messages = set()

async def process_incoming_message(chat_id: str, sender_name: str, text: str):
    """Exécute l'agent ou gère les commandes d'Afi en arrière-plan."""
    
    # 1. Gestion des commandes si c'est Afi qui répond (OUI ID / NON ID)
    if chat_id == AFI_CHAT_ID:
        text_upper = text.strip().upper()
        if text_upper.startswith("OUI") or text_upper.startswith("NON"):
            parts = text_upper.split()
            if len(parts) == 2 and parts[1].isdigit():
                order_id = int(parts[1])
                if parts[0] == "OUI":
                    res = approve_order(order_id)
                    msg = f"✅ Commande #{order_id} validée avec succès !" if res["success"] else f"❌ Erreur : {res.get('message')}"
                else:
                    res = reject_order(order_id)
                    msg = f"❌ Commande #{order_id} refusée." if res["success"] else f"❌ Erreur : {res.get('message')}"
                
                await send_whatsapp_message(AFI_CHAT_ID, msg)
                return

    # 2. Cas général : Message d'un client traité par l'agent
    # (Ici tu peux injecter un garde-fou contre l'injection de prompt ou vérifier les limites)
    result = await run_agent(text)
    bot_response = result["response"]

    # Si une commande a été générée et mise en attente, on prévient Afi
    # (Tu peux adapter selon la façon dont ton agent crée la commande en statut 'pending')
    
    # Réponse au client
    await send_whatsapp_message(chat_id, bot_response)


@app.post("/webhook")
async def green_api_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Endpoint recevant les webhooks de Green API."""
    print("Webhook reçu : ", credentials.credentials)
    # Vérification du jeton de sécurité du webhook
    if credentials.credentials != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Accès non autorisé")

    body = await request.json()
    
    # Ne traiter que les messages entrants
    if body.get("typeWebhook") == "incomingMessageReceived":
        message_data = body.get("messageData", {})
        type_message = message_data.get("typeMessage")
        
        # On ne traite que les messages texte
        if type_message == "textMessage":
            receipt_id = body.get("receiptId")
            
            # Dédoublonnage
            if receipt_id in processed_messages:
                return {"status": "ignored", "reason": "duplicate"}
            processed_messages.add(receipt_id)
            
            sender_data = body.get("senderData", {})
            chat_id = sender_data.get("chatId")
            sender_name = sender_data.get("senderName", "Client")
            text = message_data.get("textMessageData", {}).get("textMessage", "")
            
            # Ignorer les messages de groupe (@g.us)
            if chat_id and "@g.us" not in chat_id:
                # Lancer en arrière-plan pour répondre vite à Green API (code 200 immédiat)
                background_tasks.add_task(process_incoming_message, chat_id, sender_name, text)

    return {"status": "ok"}