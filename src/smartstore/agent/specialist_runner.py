import json
from typing import Any

from smartstore.agent.rodium_client import RodiumClient
from smartstore.tools import TOOLS, execute_tool


async def run_specialist(
    agent_name: str,
    instructions: str,
    user_message: str,
    allowed_tool_names: list[str] | None = None,
    max_steps: int = 6,
    required_tools: list[str] | None = None,
) -> dict[str, Any]:
    """Exécute un agent spécialisé avec uniquement ses outils autorisés."""

    allowed_tool_names = allowed_tool_names or []

    specialist_tools = [
        tool
        for tool in TOOLS
        if tool["function"]["name"] in allowed_tool_names
    ]

    client = RodiumClient()

    messages = [
        {"role": "system", "content": instructions},
        {"role": "user", "content": user_message},
    ]

    trace: list[dict[str, Any]] = []
    required_tools = required_tools or []

    for step in range(1, max_steps + 1):
        response = await client.chat_completion(
            messages=messages,
            tools=specialist_tools if specialist_tools else None,
        )

        assistant_message = response["choices"][0]["message"]
        tool_calls = assistant_message.get("tool_calls", [])

        if not tool_calls:
            executed_tools = {
                item["tool"] for item in trace
            }

            missing_tools = [
                tool for tool in required_tools
                if tool not in executed_tools
            ]

            if missing_tools:
                messages.append(assistant_message)
                messages.append({
                    "role": "user",
                    "content": (
                        "Tu ne peux pas encore répondre au client. "
                        "Tu dois obligatoirement exécuter ces outils : "
                        f"{', '.join(missing_tools)}. "
                        "Effectue les vérifications nécessaires avant "
                        "de formuler ta réponse."
                    ),
                })
                continue

            return {
                "success": bool(assistant_message.get("content")),
                "agent": agent_name,
                "response": assistant_message.get("content") or "",
                "steps": step,
                "trace": trace,
            }

        messages.append(assistant_message)

        for tool_call in tool_calls:
            function = tool_call["function"]
            tool_name = function["name"]

            try:
                arguments = json.loads(function["arguments"])

                if not isinstance(arguments, dict):
                    raise TypeError("Les arguments doivent être un objet JSON.")

                if tool_name not in allowed_tool_names:
                    result = {
                        "success": False,
                        "message": (
                            f"L'agent {agent_name} n'est pas autorisé "
                            f"à utiliser l'outil {tool_name}."
                        ),
                    }
                else:
                    print(f"\n[{agent_name}] Outil : {tool_name}")
                    print(f"Arguments : {arguments}")

                    result = await execute_tool(tool_name, arguments)

            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
                arguments = {}
                result = {
                    "success": False,
                    "message": f"Erreur d'exécution de {tool_name} : {error}",
                }

            trace.append({
                "step": step,
                "agent": agent_name,
                "tool": tool_name,
                "arguments": arguments,
                "result": result,
            })

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": json.dumps(result, ensure_ascii=False),
            })

    return {
        "success": False,
        "agent": agent_name,
        "response": "La limite d'étapes de l'agent a été atteinte.",
        "steps": max_steps,
        "trace": trace,
    }
