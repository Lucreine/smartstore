import logging
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from smartstore.agent.orchestrator import run_agent
from smartstore.tools.orders import (
    load_orders,
    approve_order,
    reject_order,
)

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