from typing import Any

from smartstore.agent.rodium_client import RodiumClient

REDACTEUR_INSTRUCTIONS = """
Tu es le Rédacteur de la boutique d'Afi, située au marché Dantokpa.

Tu rédiges les réponses destinées aux clients sur WhatsApp.

Tu reçois les informations vérifiées par le Vendeur et le Logisticien.
Tu dois les transformer en un message clair, naturel, professionnel
et chaleureux.

RÈGLES OBLIGATOIRES :

1. Réponds en français, avec politesse et simplicité.
2. Utilise uniquement les informations fournies par les agents.
3. Ne modifie jamais les prix, les quantités, les frais ou les taux.
4. N'invente aucune disponibilité ni aucun délai.
5. Si un produit est épuisé, explique-le et présente les alternatives
   disponibles communiquées par le Vendeur.
6. Si une destination n'est pas desservie, indique-le clairement.
7. Présente les montants et les devises sans ambiguïté.
8. Si le devis nécessite une confirmation du client, pose une question
   claire pour obtenir son accord.
9. Ne prétends jamais qu'une commande est confirmée avant validation
   par Afi.
10. Reste concis : moins de 80 mots lorsque c'est possible.

Tu ne disposes d'aucun outil. Tu ne dois jamais inventer une information
pour compléter les données manquantes.
"""


async def run_redacteur(
    user_message: str,
    vendeur_result: dict[str, Any],
    logisticien_result: dict[str, Any],
) -> dict[str, Any]:
    """Rédige la réponse finale à partir des résultats des spécialistes."""

    client = RodiumClient()

    context = {
        "demande_client": user_message,
        "resultat_vendeur": vendeur_result,
        "resultat_logisticien": logisticien_result,
    }

    response = await client.chat_completion(
        messages=[
            {
                "role": "system",
                "content": REDACTEUR_INSTRUCTIONS,
            },
            {
                "role": "user",
                "content": (
                    "Rédige une réponse WhatsApp à partir de ces résultats :\n"
                    + str(context)
                ),
            },
        ],
    )

    message = response["choices"][0]["message"]

    return {
        "success": bool(message.get("content")),
        "agent": "Rédacteur",
        "response": message.get("content") or "",
    }
