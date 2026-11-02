import re
import unicodedata
from typing import Any


def normalize_text(value: str) -> str:
    """Normalise un texte pour faciliter les comparaisons."""
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(
        char for char in normalized
        if not unicodedata.combining(char)
    )

def is_quote_request(user_message: str) -> bool:
    """Détecte une demande explicite de devis ou de commande."""
    normalized = normalize_text(user_message)

    keywords = (
        "devis",
        "commander",
        "commande",
        "passer commande",
    )

    return any(keyword in normalized for keyword in keywords)

def extract_fcfa_amounts(response: str) -> list[int]:
    """Extrait les montants annoncés en FCFA, CFA ou XOF."""

    pattern = (
        r"(\d[\d\s.,]*)\s*"
        r"(?:FCFA|F\s*CFA|XOF|CFA)\b"
    )

    matches = re.findall(pattern, response, flags=re.IGNORECASE)

    amounts = []

    for match in matches:
        digits = re.sub(r"\D", "", match)

        if digits:
            amounts.append(int(digits))

    return amounts


def evaluate_response(
    response: str,
    trace: list[dict[str, Any]],
    user_message: str = "",
) -> dict[str, Any]:
    """Vérifie la cohérence de la réponse avec les résultats des outils."""

    issues: list[str] = []

    if not response or not response.strip():
        issues.append("La réponse de l'agent est vide.")
        return {
            "passed": False,
            "issues": issues,
            "message": "La réponse nécessite une correction.",
        }

    # 1. Limite de 80 mots.
    word_count = len(response.split())

    if word_count > 80:
        issues.append(
            f"La réponse contient {word_count} mots au lieu de 80 maximum."
        )

    normalized_response = normalize_text(response)
    sentences = re.split(r"[.!?;\n]+", normalized_response)

    # Vérifier que les demandes de devis utilisent les outils obligatoires.
    if is_quote_request(user_message):
        called_tools = {
            entry.get("tool")
            for entry in trace
        }

        required_tools = {
            "chercher_produits",
            "verifier_stock",
            "frais_livraison",
        }

        missing_tools = required_tools - called_tools

        if missing_tools:
            issues.append(
                "La demande de devis nécessite les appels suivants : "
                + ", ".join(sorted(missing_tools))
                + "."
            )

    # 2. Récupérer les produits réellement retournés par l'outil.
    products: dict[str, dict[str, Any]] = {}

    for entry in trace:
        if entry.get("tool") != "chercher_produits":
            continue

        result = entry.get("result", {})

        for product in result.get("products", []):
            reference = product.get("reference")

            if reference:
                products[reference] = product

    # 3. Récupérer les stocks vérifiés.
    stock_results: dict[str, dict[str, Any]] = {}

    for entry in trace:
        if entry.get("tool") != "verifier_stock":
            continue

        result = entry.get("result", {})

        if result.get("found") and result.get("reference"):
            stock_results[result["reference"]] = result

    # 4. Vérifier les affirmations sur la disponibilité.
    unavailable_products = []

    for reference, result in stock_results.items():
        product = products.get(reference, {})
        product_name = product.get("name", reference)

        normalized_name = normalize_text(product_name)
        normalized_reference = normalize_text(reference)

        relevant_sentences = [
            sentence
            for sentence in sentences
            if normalized_name in sentence
            or normalized_reference in sentence
        ]

        available = result.get("available")
        quantity = result.get("quantity")

        if available is False:
            unavailable_products.append(product_name)

        for sentence in relevant_sentences:
            says_unavailable = any(
                phrase in sentence
                for phrase in (
                    "rupture de stock",
                    "indisponible",
                    "epuise",
                    "plus disponible",
                    "n'est pas disponible",
                )
            )

            says_available = (
                any(
                    phrase in sentence
                    for phrase in (
                        "disponible",
                        "en stock",
                        "stock disponible",
                    )
                )
                and not says_unavailable
            )

            if available is False and says_available:
                issues.append(
                    f"{product_name} est indisponible, "
                    "mais la réponse annonce qu'il est disponible."
                )

            if available is True and says_unavailable:
                issues.append(
                    f"{product_name} est disponible, "
                    "mais la réponse annonce qu'il est indisponible."
                )

            # Vérifier une quantité de stock explicitement annoncée.
            if quantity is not None:
                quantity_pattern = (
                    r"\b(\d+)\s+"
                    r"(?:exemplaires?|pieces?|unites?)\b"
                )

                mentioned_quantities = re.findall(
                    quantity_pattern,
                    sentence,
                )

                if any(
                    int(value) != quantity
                    for value in mentioned_quantities
                ):
                    issues.append(
                        f"La quantité annoncée pour {product_name} "
                        f"ne correspond pas au stock réel ({quantity})."
                    )

    # 5. Vérifier qu'une alternative disponible et vérifiée est proposée.
    if unavailable_products:
        available_alternatives = []

        # Identifier les références des produits déjà demandés par le client.
        normalized_user_message = normalize_text(user_message)

        requested_references = {
            reference
            for reference, product in products.items()
            if product.get("name")
            and normalize_text(product["name"]) in normalized_user_message
        }

        # Identifier les références des produits indisponibles.
        unavailable_references = {
            reference
            for reference, result in stock_results.items()
            if result.get("available") is False
        }

        # Identifier les alternatives disponibles qui n'étaient pas demandées.
        for reference, result in stock_results.items():
            if reference in requested_references:
                continue

            if reference in unavailable_references:
                continue

            if result.get("available") is not True:
                continue

            product = products.get(reference, {})
            product_name = product.get("name")

            if product_name:
                available_alternatives.append(product_name)

        # Vérifier qu'une véritable alternative est mentionnée.
        alternative_mentioned = any(
            normalize_text(name) in normalized_response
            for name in available_alternatives
        )

        if not available_alternatives or not alternative_mentioned:
            issues.append(
                "Un produit est indisponible, mais aucune alternative "
                "différente, disponible et vérifiée n'est proposée."
            )
    # 6. Vérifier les affirmations concernant les commandes.
    confirmation_phrases = (
        "commande confirmee",
        "votre commande est confirmee",
        "commande validee",
        "commande enregistree",
        "commande a ete enregistree",
    )

    claims_order_confirmed = any(
        phrase in normalized_response
        for phrase in confirmation_phrases
    )

    for entry in trace:
        if entry.get("tool") != "creer_commande":
            continue

        result = entry.get("result", {})
        approved = result.get("approved")
        success = result.get("success")

        if claims_order_confirmed and (
            success is not True or approved is not True
        ):
            issues.append(
                "La réponse annonce une commande confirmée, "
                "mais l'outil ne confirme pas son enregistrement."
            )

    
    # 7. Vérifier les montants annoncés par rapport aux outils.

    trusted_amounts: set[int] = set()

    # Prix officiels récupérés dans le catalogue.
    for product in products.values():
        price = product.get("price")

        if isinstance(price, int) and not isinstance(price, bool):
            trusted_amounts.add(price)

    # Frais de livraison retournés par frais_livraison.
    for entry in trace:
        if entry.get("tool") != "frais_livraison":
            continue

        result = entry.get("result", {})

        delivery_fee = result.get("delivery_fee")

        if (
            result.get("success") is True
            and result.get("currency") == "XOF"
            and isinstance(delivery_fee, int)
            and not isinstance(delivery_fee, bool)
        ):
            trusted_amounts.add(delivery_fee)

    # Devis ou commande retourné par creer_commande.
    for entry in trace:
        if entry.get("tool") != "creer_commande":
            continue

        result = entry.get("result", {})

        # En mode validation, les informations sont dans order.
        quote = result.get("order", result)

        if quote.get("currency") != "XOF":
            continue

        quote_items = quote.get("items", [])

        for item in quote_items:
            unit_price = item.get("unit_price")
            item_subtotal = item.get("subtotal")
            quantity = item.get("quantity")

            if isinstance(unit_price, int):
                trusted_amounts.add(unit_price)

            if isinstance(item_subtotal, int):
                trusted_amounts.add(item_subtotal)

            # Vérifier le calcul de chaque ligne.
            if (
                isinstance(unit_price, int)
                and isinstance(quantity, int)
                and isinstance(item_subtotal, int)
                and unit_price * quantity != item_subtotal
            ):
                issues.append(
                    "Le sous-total d'un article ne correspond pas "
                    "à son prix unitaire multiplié par sa quantité."
                )

        subtotal = quote.get("subtotal")
        delivery_fee = quote.get("delivery_fee")
        total = quote.get("total")

        if isinstance(subtotal, int):
            trusted_amounts.add(subtotal)

        if isinstance(delivery_fee, int):
            trusted_amounts.add(delivery_fee)

        if isinstance(total, int):
            trusted_amounts.add(total)

        # Vérifier le sous-total général.
        calculated_subtotal = sum(
            item.get("subtotal", 0)
            for item in quote_items
        )

        if (
            isinstance(subtotal, int)
            and subtotal != calculated_subtotal
        ):
            issues.append(
                "Le sous-total du devis ne correspond pas "
                "à la somme des articles."
            )

        # Vérifier le total général.
        if (
            isinstance(subtotal, int)
            and isinstance(delivery_fee, int)
            and isinstance(total, int)
            and total != subtotal + delivery_fee
        ):
            issues.append(
                "Le total du devis ne correspond pas "
                "au sous-total augmenté de la livraison."
            )

    # Comparer les montants annoncés aux valeurs officielles.
    for amount in extract_fcfa_amounts(response):
        if amount not in trusted_amounts:
            issues.append(
                f"Le montant annoncé ({amount} FCFA) "
                "ne correspond à aucune valeur retournée "
                "par les outils."
            )


    return {
        "passed": len(issues) == 0,
        "issues": issues,
        "message": (
            "La réponse est cohérente avec les résultats des outils."
            if not issues
            else "La réponse nécessite une correction."
        ),
        "word_count": word_count,
    }