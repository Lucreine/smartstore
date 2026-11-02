
import unicodedata
from typing import Any


PRODUCTS: list[dict[str, Any]] = [
    {
        "reference": "P01",
        "name": "Pagne wax 6 yards",
        "category": "pagne",
        "price": 12000,
        "currency": "XOF",
    },
    {
        "reference": "P02",
        "name": "Chemise bazin homme",
        "category": "vêtement",
        "price": 18500,
        "currency": "XOF",
    },
    {
        "reference": "P03",
        "name": "Sac en raphia",
        "category": "accessoire",
        "price": 7500,
        "currency": "XOF",
    },
    {
        "reference": "P04",
        "name": "Sandales en cuir",
        "category": "chaussure",
        "price": 9000,
        "currency": "XOF",
    },
    {
        "reference": "P05",
        "name": "Robe en wax",
        "category": "vêtement",
        "price": 22000,
        "currency": "XOF",
    },
    {
        "reference": "P06",
        "name": "Beurre de karité 500 g",
        "category": "cosmétique",
        "price": 3500,
        "currency": "XOF",
    },
]


def normalize_token(token: str) -> str:
    """Normalise un mot pour faciliter la recherche."""
    normalized = unicodedata.normalize("NFKD", token.casefold().strip())
    normalized = "".join(
        char for char in normalized
        if not unicodedata.combining(char)
    )

    if len(normalized) > 3 and normalized.endswith("s"):
        normalized = normalized[:-1]

    return normalized


def search_product(
    query: str = "",
    max_price: int | None = None,
) -> list[dict[str, Any]]:
    """Recherche des produits par mots-clés et prix maximum."""

    query_tokens = [
        normalize_token(token)
        for token in query.split()
    ]

    results = []

    for product in PRODUCTS:
        searchable_text = " ".join([
            product["name"],
            product["category"],
            product["reference"],
        ])

        searchable_tokens = {
            normalize_token(token)
            for token in searchable_text.split()
        }

        matches_query = all(
            token in searchable_tokens
            for token in query_tokens
        )

        matches_price = (
            max_price is None
            or product["price"] <= max_price
        )

        if matches_query and matches_price:
            results.append(product.copy())

    return results
