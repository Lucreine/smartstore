import json
from pathlib import Path
from typing import Any

from smartstore.tools.delivery import calculate_delivery
from smartstore.tools.inventory import load_inventory, save_inventory
from smartstore.tools.products import PRODUCTS


ORDERS_FILE = Path(__file__).resolve().parents[3] / "data" / "commandes.json"


def load_orders() -> list[dict[str, Any]]:
    """Charge les commandes enregistrées."""
    ORDERS_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not ORDERS_FILE.exists():
        save_orders([])

    with ORDERS_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_orders(orders: list[dict[str, Any]]) -> None:
    """Enregistre les commandes dans le fichier JSON."""
    ORDERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary_file = ORDERS_FILE.with_suffix(".tmp")

    with temporary_file.open("w", encoding="utf-8") as file:
        json.dump(orders, file, ensure_ascii=False, indent=2)

    temporary_file.replace(ORDERS_FILE)


def calculate_order_quote(
    destination: str,
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    """Calcule un devis sans enregistrer de commande."""

    if not items:
        return {"success": False, "message": "La commande ne contient aucun article."}

    products_by_reference = {
        product["reference"]: product for product in PRODUCTS
    }

    inventory = load_inventory()
    requested_quantities: dict[str, int] = {}

    for item in items:
        reference = str(item.get("reference", "")).strip().upper()
        quantity = item.get("quantity")

        if (
            isinstance(quantity, bool)
            or not isinstance(quantity, int)
            or quantity <= 0
        ):
            return {
                "success": False,
                "message": f"Quantité invalide pour {reference or 'un article'}.",
            }

        if reference not in products_by_reference:
            return {
                "success": False,
                "message": f"Référence inconnue : {reference}",
            }

        requested_quantities[reference] = (
            requested_quantities.get(reference, 0) + quantity
        )

    validated_items = []

    for reference, quantity in requested_quantities.items():
        available = inventory.get(reference, 0)

        if available < quantity:
            return {
                "success": False,
                "message": f"Stock insuffisant pour {reference}.",
                "reference": reference,
                "available": available,
                "requested": quantity,
            }

        product = products_by_reference[reference]
        unit_price = product["price"]

        validated_items.append({
            "reference": reference,
            "name": product["name"],
            "quantity": quantity,
            "unit_price": unit_price,
            "subtotal": unit_price * quantity,
        })

    delivery = calculate_delivery(destination)

    if not delivery["found"]:
        return {
            "success": False,
            "message": delivery["message"],
            "supported_zones": delivery.get("supported_zones", []),
        }

    subtotal = sum(item["subtotal"] for item in validated_items)
    delivery_fee = delivery["delivery_fee"]

    return {
        "success": True,
        "items": validated_items,
        "destination": destination,
        "subtotal": subtotal,
        "delivery_fee": delivery_fee,
        "total": subtotal + delivery_fee,
        "currency": "XOF",
        "delivery_time": delivery["delivery_time"],
    }


def create_order_request(
    customer_name: str,
    destination: str,
    items: list[dict[str, Any]],
    customer_phone: str = "",
    mode: str = "validation",
    client_consent: bool = False,
) -> dict[str, Any]:
    """Crée un devis ou une commande en attente de validation par Afi."""

    if mode not in ("devis", "validation"):
        return {
            "success": False,
            "message": "Mode invalide. Utiliser devis ou validation.",
        }

    if not customer_name.strip():
        return {"success": False, "message": "Le nom du client est obligatoire."}

    if mode == "validation" and not customer_phone.strip():
        return {
            "success": False,
            "message": "Le téléphone du client est obligatoire.",
        }

    quote = calculate_order_quote(destination, items)

    if not quote["success"]:
        return quote

    if mode == "devis":
        return {
            **quote,
            "mode": "devis",
            "message": "Devis calculé. Aucune commande enregistrée.",
        }

    if client_consent is not True:
        return {
            "success": False,
            "approved": False,
            "message": "Le consentement du client est requis.",
        }

    orders = load_orders()

    order = {
        "id": max((o.get("id", 0) for o in orders), default=0) + 1,
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "destination": destination,
        "items": quote["items"],
        "subtotal": quote["subtotal"],
        "delivery_fee": quote["delivery_fee"],
        "total": quote["total"],
        "currency": "XOF",
        "status": "pending",
    }

    orders.append(order)
    save_orders(orders)

    return {
        "success": True,
        "approved": False,
        "order": order,
        "message": (
            "Le client a accepté le devis. "
            "La commande est en attente de validation par Afi."
        ),
    }


def approve_order(order_id: int) -> dict[str, Any]:
    """Valide une commande en attente et décrémente le stock."""

    orders = load_orders()
    order = next((o for o in orders if o["id"] == order_id), None)

    if order is None:
        return {"success": False, "message": "Commande introuvable."}

    if order["status"] != "pending":
        return {
            "success": False,
            "message": f"Cette commande a déjà le statut {order['status']}.",
        }

    inventory = load_inventory()

    for item in order["items"]:
        reference = item["reference"]
        quantity = item["quantity"]

        if inventory.get(reference, 0) < quantity:
            return {
                "success": False,
                "message": f"Stock insuffisant pour {reference}.",
            }

    for item in order["items"]:
        inventory[item["reference"]] -= item["quantity"]

    order["status"] = "confirmed"
    save_inventory(inventory)
    save_orders(orders)

    return {
        "success": True,
        "approved": True,
        "order": order,
        "message": "Commande validée. Le stock a été mis à jour.",
    }


def reject_order(order_id: int) -> dict[str, Any]:
    """Refuse une commande en attente sans modifier le stock."""

    orders = load_orders()
    order = next((o for o in orders if o["id"] == order_id), None)

    if order is None:
        return {"success": False, "message": "Commande introuvable."}

    if order["status"] != "pending":
        return {
            "success": False,
            "message": f"Cette commande a déjà le statut {order['status']}.",
        }

    order["status"] = "rejected"
    save_orders(orders)

    return {
        "success": True,
        "approved": False,
        "order": order,
        "message": "Commande refusée par Afi. Le stock n'a pas été modifié.",
    }
