import re
import unicodedata
from typing import Any

from smartstore.agent.evaluator import evaluate_response
from smartstore.agent.logisticien import run_logisticien
from smartstore.agent.redacteur import run_redacteur
from smartstore.agent.vendeur import run_vendeur


def normalize_text(text: str) -> str:
    """Normalise le texte pour faciliter la détection des intentions."""

    normalized = unicodedata.normalize("NFKD", text.lower())
    return "".join(
        char for char in normalized
        if not unicodedata.combining(char)
    )

def detect_intents(message: str) -> tuple[bool, bool]:
    """Détermine quels spécialistes doivent être sollicités."""

    text = normalize_text(message)

    vendor_keywords = [
        "produit", "pagne", "wax", "chemise", "bazin", "sac",
        "raphia", "sandale", "robe", "karite", "beurre",
        "catalogue", "prix", "stock", "disponible", "disponibles",
        "disponibilite", "commander", "commande", "acheter",
        "achat", "article", "quantite", "combien", "devis",
    ]

    logistician_keywords = [
        "livraison", "livrer", "livrez", "expedition",
        "expedier", "frais", "destination", "zone", "delai",
        "cotonou", "akpakpa", "fidjrosse", "calavi",
        "porto-novo", "ouidah", "lome", "devise",
        "convertir", "conversion", "euro", "euros",
        "eur", "dollar", "usd", "naira", "ngn",
        "paris", "monnaie",
    ]

    def contains_keyword(keywords: list[str]) -> bool:
        return any(
            re.search(
                rf"(?<!\w){re.escape(keyword)}(?!\w)",
                text,
            )
            for keyword in keywords
        )

    needs_vendor = contains_keyword(vendor_keywords)
    needs_logistician = contains_keyword(logistician_keywords)

    return needs_vendor, needs_logistician

async def run_gerant(user_message: str) -> dict[str, Any]:
    """Coordonne les agents spécialisés et évalue la réponse finale."""

    print("\n" + "=" * 60)
    print("GERANT : analyse de la demande")
    print("=" * 60)

    needs_vendor, needs_logistician = detect_intents(user_message)

    vendeur_result = {
        "success": True,
        "agent": "Vendeur",
        "response": "Agent non sollicité pour cette demande.",
        "trace": [],
    }

    logisticien_result = {
        "success": True,
        "agent": "Logisticien",
        "response": "Agent non sollicité pour cette demande.",
        "trace": [],
    }

    # 1. Le Vendeur traite les produits et les commandes.
    if needs_vendor:
        print("\nGERANT -> Vendeur")
        vendeur_result = await run_vendeur(user_message)

    # 2. Le Logisticien reçoit aussi les résultats du Vendeur.
    if needs_logistician:
        print("\nGERANT -> Logisticien")

        logisticien_message = (
            f"Demande originale du client : {user_message}\n\n"
            f"Informations vérifiées par le Vendeur : "
            f"{vendeur_result}"
        )

        logisticien_result = await run_logisticien(
            logisticien_message
        )

    # 3. Rassembler les traces des spécialistes.
    trace = (
        vendeur_result.get("trace", [])
        + logisticien_result.get("trace", [])
    )

    # 4. Le Rédacteur prépare le message WhatsApp.
    print("\nGERANT -> Rédacteur")

    redaction = await run_redacteur(
        user_message=user_message,
        vendeur_result=vendeur_result,
        logisticien_result=logisticien_result,
    )

    final_response = redaction.get("response", "")

    # 5. Le Gérant évalue la réponse finale.
    evaluation = evaluate_response(
        response=final_response,
        trace=trace,
        user_message=user_message,
    )

    print("\nÉVALUATION DU GÉRANT :", evaluation)

    return {
        "success": (
            bool(final_response)
            and evaluation.get("passed", False)
        ),
        "response": final_response,
        "steps": (
            vendeur_result.get("steps", 0)
            + logisticien_result.get("steps", 0)
            + 1
        ),
        "evaluation": evaluation,
        "trace": trace,
        "agents": {
            "vendeur": vendeur_result,
            "logisticien": logisticien_result,
            "redacteur": redaction,
        },
    }
