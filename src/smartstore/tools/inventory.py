
import json
from pathlib import Path
from typing import Any


STOCK_FILE = Path(__file__).resolve().parents[3] / "data" / "stock.json"

INITIAL_INVENTORY: dict[str, int] = {
    "P01": 14,
    "P02": 3,
    "P03": 0,
    "P04": 8,
    "P05": 5,
    "P06": 40,
}


def load_inventory() -> dict[str, int]:
    """Charge le stock depuis le fichier JSON."""

    STOCK_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not STOCK_FILE.exists():
        save_inventory(INITIAL_INVENTORY.copy())

    with STOCK_FILE.open("r", encoding="utf-8") as file:
        inventory = json.load(file)

    return inventory


def save_inventory(inventory: dict[str, int]) -> None:
    """Enregistre le stock dans le fichier JSON."""

    STOCK_FILE.parent.mkdir(parents=True, exist_ok=True)

    temporary_file = STOCK_FILE.with_suffix(".tmp")

    with temporary_file.open("w", encoding="utf-8") as file:
        json.dump(inventory, file, ensure_ascii=False, indent=2)

    temporary_file.replace(STOCK_FILE)


def check_stock(reference: str) -> dict[str, Any]:
    """Vérifie le stock d'un produit à partir de sa référence."""

    normalized_reference = reference.strip().upper()
    inventory = load_inventory()

    if normalized_reference not in inventory:
        return {
            "found": False,
            "reference": normalized_reference,
            "message": "référence inconnue",
        }

    quantity = inventory[normalized_reference]

    return {
        "found": True,
        "reference": normalized_reference,
        "quantity": quantity,
        "available": quantity > 0,
        "message": (
            "Produit disponible."
            if quantity > 0
            else "Produit en rupture de stock."
        ),
    }


def decrease_stock(reference: str, quantity: int) -> dict[str, Any]:
    """Décrémente le stock après validation de la commande."""

    normalized_reference = reference.strip().upper()

    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        return {
            "success": False,
            "message": "La quantité doit être un entier positif.",
        }

    inventory = load_inventory()

    if normalized_reference not in inventory:
        return {
            "success": False,
            "message": "référence inconnue",
        }

    available_quantity = inventory[normalized_reference]

    if available_quantity < quantity:
        return {
            "success": False,
            "message": f"stock insuffisant pour {normalized_reference}",
            "available": available_quantity,
            "requested": quantity,
        }

    inventory[normalized_reference] -= quantity
    save_inventory(inventory)

    return {
        "success": True,
        "reference": normalized_reference,
        "remaining_stock": inventory[normalized_reference],
    }
