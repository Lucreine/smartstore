import logging
from typing import Any
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, Header
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
from smartstore.tools.orders import load_orders, approve_order, reject_order, create_order_request
import json

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

processed_messages = set()

async def process_incoming_message(chat_id: str, text: str):
    """Exécute l'agent ou gère les validations d'Afi par WhatsApp."""
    
    if chat_id == AFI_CHAT_ID:
        text_upper = text.strip().upper()
        parts = text_upper.split()
        
        if len(parts) == 2 and parts[1].isdigit():
            action = parts[0]
            order_id = int(parts[1])
            
            if action == "OUI":
                result = approve_order(order_id)
                if result["success"]:
                    msg_afi = f"✅ Commande #{order_id} validée avec succès. Le stock a été mis à jour."
                    order_data = result.get("order", {})
                    client_chat_id = order_data.get("chat_id") or order_data.get("client_chat_id")

                    if client_chat_id:
                        await send_whatsapp_message(
                            client_chat_id, 
                            f"🎉 Bonne nouvelle ! Votre commande #{order_id} a été validée par Afi. Nous préparons votre livraison."
                        )
                else:
                    msg_afi = f"❌ Erreur lors de la validation : {result.get('message')}"
            elif action == "NON":
                result = reject_order(order_id)
                if result["success"]:
                    msg_afi = f"❌ Commande #{order_id} refusée."

                    order_data = result.get("order", {})
                    client_chat_id = order_data.get("chat_id") or order_data.get("client_chat_id")
                    if client_chat_id:
                        await send_whatsapp_message(
                            client_chat_id, 
                            f"❌ Désolé, votre commande #{order_id} n'a pas pu être validée par Afi."
                        )
                else:
                    msg_afi = f"❌ Erreur : {result.get('message')}"
            else:
                msg_afi = "Commande incomprise. Répondez par OUI <id> ou NON <id> (ex: OUI 12)."
            
            await send_whatsapp_message(AFI_CHAT_ID, msg_afi)
            return

    result = await run_agent(text)
    bot_response = result["response"]
    
    await send_whatsapp_message(chat_id, bot_response)

    orders = load_orders()
    pending_orders = [o for o in orders if o.get("status") == "pending"]
    
    if pending_orders:
        latest_order = pending_orders[-1]
        order_id = latest_order.get("id")
        
        if not latest_order.get("notified_afi"):
            latest_order["notified_afi"] = True
            
            details = latest_order.get("details", "Articles divers")
            zone = latest_order.get("zone", "Inconnue")
            total = latest_order.get("total", 0)
            
            message_afi = (
                f"🔔 **Nouvelle commande en attente (#{order_id})**\n"
                f"Client : {chat_id}\n"
                f"Détails : {details}\n"
                f"Zone : {zone}\n"
                f"Total : {total} FCFA\n\n"
                f"Répondez **OUI {order_id}** pour valider ou **NON {order_id}** pour refuser."
            )
            await send_whatsapp_message(AFI_CHAT_ID, message_afi)

@app.post("/webhook")
async def green_api_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    authorization: str = Header(None)
):
    """Endpoint recevant les webhooks de Green API."""
    token_recu = authorization
    if authorization and authorization.startswith("Bearer "):
        token_recu = authorization.replace("Bearer ", "").strip()

    if token_recu != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Accès non autorisé")

    body_bytes = await request.body()
    if not body_bytes:
        return {"status": "ignored", "reason": "empty body"}
    
    try:
        body = json.loads(body_bytes)
    except json.JSONDecodeError:
        return {"status": "error", "reason": "invalid json"}
    
    if body.get("typeWebhook") == "incomingMessageReceived":
        message_data = body.get("messageData", {})
        type_message = message_data.get("typeMessage")
        
        if type_message == "textMessage":
            receipt_id = body.get("receiptId")
            
            if receipt_id in processed_messages:
                return {"status": "ignored", "reason": "duplicate"}
            processed_messages.add(receipt_id)
            
            sender_data = body.get("senderData", {})
            chat_id = sender_data.get("chatId")
            sender_name = sender_data.get("senderName", "Client")
            text = message_data.get("textMessageData", {}).get("textMessage", "")
            
            if chat_id and "@g.us" not in chat_id:
                background_tasks.add_task(process_incoming_message, chat_id, sender_name, text)

    return {"status": "ok"}