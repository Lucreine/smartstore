
from typing import Any

from smartstore.tools.currency import convert_currency
from smartstore.tools.delivery import calculate_delivery
from smartstore.tools.inventory import check_stock
from smartstore.tools.orders import create_order_request
from smartstore.tools.products import search_product
import asyncio

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "chercher_produits",
            "description": (
                "Recherche les produits du catalogue par nom, catégorie "
                "ou référence. À utiliser lorsqu'un client demande des "
                "informations sur un produit ou son prix. "
                "Si aucun résultat, signaler qu'aucun produit ne correspond."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Nom, catégorie ou référence recherchée.",
                    },
                    "max_price": {
                        "type": "integer",
                        "description": "Prix maximum en FCFA, facultatif.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "verifier_stock",
            "description": (
                "Vérifie la quantité disponible d'un produit. "
                "À utiliser avant de promettre qu'un article est disponible "
                "ou avant de préparer une commande."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "reference": {
                        "type": "string",
                        "description": "Référence officielle du produit.",
                    },
                },
                "required": ["reference"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "frais_livraison",
            "description": (
                "Vérifie si une destination est desservie et retourne "
                "les frais ainsi que le délai de livraison. "
                "À utiliser lorsqu'un client demande une livraison "
                "ou avant de calculer le total d'une commande."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {
                        "type": "string",
                        "description": "Destination du client.",
                    },
                },
                "required": ["destination"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "convertir_devise",
            "description": (
                "Convertit un montant en FCFA vers EUR, USD, NGN ou une "
                "autre devise prise en charge, en récupérant un taux réel "
                "au moment de la demande. À utiliser lorsqu'un client "
                "demande un prix dans une devise étrangère."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "number",
                        "description": "Montant en FCFA à convertir.",
                    },
                    "target_currency": {
                        "type": "string",
                        "description": "Code ISO de la devise cible.",
                    },
                },
                "required": ["amount", "target_currency"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "creer_commande",
            "description": (
                "Permet de préparer un devis ou de créer une commande en attente. "
                "En mode devis, calcule les prix, le stock et la livraison "
                "sans enregistrer de commande. En mode validation, crée une "
                "commande avec le statut pending uniquement après l'accord "
                "explicite du client. Afi doit ensuite valider ou refuser "
                "la commande via les endpoints de gestion. Le stock ne diminue "
                "qu'après validation par Afi."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {
                        "type": "string",
                        "description": "Nom du client.",
                    },
                   "customer_phone": {
                        "type": "string",
                        "description": (
                            "Téléphone du client. Facultatif en mode devis, "
                            "obligatoire en mode validation. Ne jamais inventer."
                        ),
                    },
                    "destination": {
                        "type": "string",
                        "description": "Zone de livraison.",
                    },
                    "items": {
                        "type": "array",
                        "description": "Articles et quantités demandés.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "reference": {
                                    "type": "string",
                                    "description": "Référence officielle.",
                                },
                                "quantity": {
                                    "type": "integer",
                                    "description": "Quantité demandée.",
                                },
                            },
                            "required": ["reference", "quantity"],
                            "additionalProperties": False,
                        },
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["devis", "validation"],
                        "description": (
                            "devis pour calculer sans enregistrer ; "
                            "validation après accord explicite du client."
                        ),
                    },
                    "client_consent": {
                        "type": "boolean",
                        "description": (
                            "True uniquement si le client a explicitement accepté "
                            "le devis présenté. False dans tous les autres cas."
                        ),
                    },
                },
                "required": [
                    "customer_name",
                    "destination",
                    "items",
                    "mode",
                    "client_consent"
                ],
                "additionalProperties": False,
            },
        },
    },
]

async def execute_tool(
    name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Exécute un outil demandé par l'agent IA."""

    if name == "chercher_produits":
        products = search_product(**arguments)

        if not products:
            return {
                "success": False,
                "message": (
                    f"aucun produit pour {arguments.get('query', '')}"
                ),
            }

        return {
            "success": True,
            "products": products,
        }

    if name == "verifier_stock":
        result = check_stock(**arguments)

        if not result["found"]:
            return {
                "success": False,
                **result,
            }

        return {
            "success": True,
            **result,
        }

    if name == "frais_livraison":
        result = calculate_delivery(**arguments)

        if not result["found"]:
            return {
                "success": False,
                **result,
            }

        return {
            "success": True,
            **result,
        }

    if name == "convertir_devise":
        return await convert_currency(**arguments)

    if name == "creer_commande":
        return await asyncio.to_thread(create_order_request, **arguments)

    return {
        "success": False,
        "message": f"Outil inconnu : {name}",
    }
