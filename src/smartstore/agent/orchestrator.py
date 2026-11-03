
import json
from typing import Any

import httpx

from smartstore.agent.evaluator import evaluate_response
from smartstore.agent.instructions import SYSTEM_INSTRUCTIONS
from smartstore.agent.rodium_client import RodiumClient
from smartstore.tools import TOOLS, execute_tool

MAX_STEPS = 10

async def run_agent(
    user_message: str,
    max_steps: int = MAX_STEPS,
) -> dict[str, Any]:
    """Exécute la boucle penser, agir, observer et évaluer."""

    if max_steps < 1:
        raise ValueError("max_steps doit être supérieur ou égal à 1.")

    client = RodiumClient()

    messages = [
        {
            "role": "system",
            "content": SYSTEM_INSTRUCTIONS,
        },
        {
            "role": "user",
            "content": user_message,
        },
    ]

    trace: list[dict[str, Any]] = []
    tool_cache: dict[str, dict[str, Any]] = {}
    out_of_stock_refs: set[str] = set()

    for step in range(1, max_steps + 1):
        # PENSER : le modèle décide de répondre ou d'utiliser des outils.
        response = await client.chat_completion(
            messages=messages,
            tools=TOOLS,
        )

        assistant_message = response["choices"][0]["message"]
        tool_calls = assistant_message.get("tool_calls", [])

        # Si aucun outil n'est demandé, le modèle propose sa réponse.
        if not tool_calls:
            final_response = assistant_message.get("content") or ""

            # ÉVALUER : vérifier la réponse avant de la transmettre.
            evaluation = evaluate_response(
                response=final_response, 
                trace=trace,
                user_message=user_message,)

            if evaluation["passed"]:
                return {
                    "success": True,
                    "response": final_response,
                    "steps": step,
                    "evaluation": evaluation,
                    "trace": trace,
                }

            # Si l'évaluation échoue, demander une nouvelle réponse.
            if step < max_steps:
                messages.append(assistant_message)

                critique = (
                    "Ta réponse précédente n'a pas passé l'évaluation. "
                    "Corrige-la en tenant compte des problèmes suivants : "
                    f"{json.dumps(evaluation['issues'], ensure_ascii=False)}. "
                    "Utilise uniquement les informations provenant des outils. "
                    "N'invente aucun prix, stock, frais ou taux de change. "
                    "Ne prétends jamais qu'une commande est enregistrée "
                    "si la validation d'Afi a été refusée."
                )

                messages.append({
                    "role": "user",
                    "content": critique,
                })
                continue

            return {
                "success": False,
                "response": (
                    "Je préfère vérifier certaines informations avant "
                    "de vous donner une réponse définitive."
                ),
                "steps": step,
                "evaluation": evaluation,
                "trace": trace,
            }

        # AGIR : exécuter les outils demandés par le modèle.
        messages.append(assistant_message)

        for tool_call in tool_calls:
            function = tool_call["function"]
            tool_name = function["name"]
            arguments: dict[str, Any] = {}

            try:
                arguments = json.loads(function["arguments"])

                if not isinstance(arguments, dict):
                    raise TypeError(
                        "Les arguments doivent être un objet JSON."
                    )

                print(f"\n🔧 OUTIL UTILISÉ : {tool_name}")
                print(f"📥 ARGUMENTS : {arguments}")

                cache_key = json.dumps(
                    {
                        "tool": tool_name,
                        "arguments": arguments,
                    },
                    sort_keys=True,
                    ensure_ascii=False,
                )

                # Réutiliser le résultat si l'appel a déjà été effectué.
                if cache_key in tool_cache:
                    result = tool_cache[cache_key]
                    print(f"♻️ RÉSULTAT RÉUTILISÉ : {tool_name}")
                else:
                    result = await execute_tool(tool_name, arguments)

                    if tool_name == "verifier_stock" and result.get("success") is True and result.get("available") is False:
                        ref = result.get("reference")
                        if ref:
                            out_of_stock_refs.add(ref)
                            print(f"🚫 PRODUIT ÉPUISÉ AJOUTÉ AU REGISTRE : {ref}")

                    # 2. Si chercher_produits renvoie des produits, on retire ceux qui sont dans out_of_stock_refs
                    if tool_name == "chercher_produits" and result.get("success") is True:
                        products = result.get("products", [])
                        filtered_products = [
                            p for p in products 
                            if p.get("reference") not in out_of_stock_refs
                        ]
                        result["products"] = filtered_products
                        if not filtered_products:
                           result = {
                                "success": True,
                                "products": [],
                                "message": "Aucune alternative disponible en stock. Le produit demandé est en rupture et il n'y a pas d'autre substitut. Passe directement à la création du devis (creer_commande) avec les articles disponibles."
                            }

                    # Ne mémoriser que les résultats réussis.                    
                    if result.get("success") is True and tool_name != "creer_commande":
                        tool_cache[cache_key] = result

                print(f"📤 RÉSULTAT : {result}")
                print("-" * 60)

            except (
                json.JSONDecodeError,
                KeyError,
                TypeError,
                ValueError,
                httpx.HTTPError,
                OSError,
            ) as error:
                result = {
                    "success": False,
                    "message": (
                        f"Erreur lors de l'exécution de {tool_name} : "
                        f"{error}"
                    ),
                }

            # OBSERVER : conserver le résultat de chaque outil.
            trace.append({
                "step": step,
                "tool": tool_name,
                "arguments": arguments,
                "result": result,
            })

            # Le résultat de l'outil retourne au modèle.
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": json.dumps(
                    result,
                    ensure_ascii=False,
                ),
            })

    return {
        "success": False,
        "response": (
            "La limite d'étapes a été atteinte. La réponse n'a pas pu être finalisée."
        ),
        "steps": max_steps,
        "trace": trace,
    }
