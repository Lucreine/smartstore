import unicodedata
from typing import Any

def normalize_destination(destination: str) -> str:
    """Normalise une destination pour faciliter sa comparaison."""
    normalized = unicodedata.normalize("NFKD", destination.strip().casefold())
    return "".join(
        char for char in normalized
        if not unicodedata.combining(char)
    )

DELIVERY_RATES: dict[str, int] = {
    "cotonou": 1000,
    "calavi": 2000,
    "porto-novo": 3000,
    "ouidah": 3500,
    "akpakpa": 1000,
    "fidjrosse": 1500,
}


SUPPORTED_ZONES = [
    "Cotonou",
    "Akpakpa",
    "Fidjrossè",
    "Calavi",
    "Porto-Novo",
    "Ouidah",
]

DELIVERY_TIME = "24 à 48 heures"


def calculate_delivery(destination: str) -> dict[str, Any]:
    """
    Calcule les frais et le délai de livraison.

    Retourne une erreur avec la liste des zones desservies
    lorsque la destination n'est pas prise en charge.
    """
    normalized_destination = normalize_destination(destination)

    if not normalized_destination:
        return {
            "found": False,
            "message": "Veuillez préciser la destination.",
            "supported_zones": SUPPORTED_ZONES,
        }

    fee = DELIVERY_RATES.get(normalized_destination)

    if fee is None:
        return {
            "found": False,
            "destination": destination.strip(),
            "currency": "XOF",
            "message": "Zone non desservie.",
            "supported_zones": SUPPORTED_ZONES,
        }

    return {
        "found": True,
        "destination": destination.strip(),
        "delivery_fee": fee,
        "currency": "XOF",
        "delivery_time": DELIVERY_TIME,
        "message": (
            f"Livraison disponible à {destination.strip()}. "
            f"Frais : {fee} FCFA. "
            f"Délai : {DELIVERY_TIME}."
        ),
    }
