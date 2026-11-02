
from decimal import Decimal, InvalidOperation

import httpx


FRANKFURTER_URL = "https://api.frankfurter.dev/v2"


async def convert_currency(
    amount: float,
    target_currency: str,
) -> dict:
    """Convertit un montant XOF vers une autre devise avec un taux réel."""

    try:
        value = Decimal(str(amount))
    except (InvalidOperation, ValueError, TypeError):
        return {
            "success": False,
            "message": "Montant invalide.",
        }

    if not value.is_finite() or value <= 0:
        return {
            "success": False,
            "message": "Le montant doit être supérieur à zéro.",
        }

    if not isinstance(target_currency, str):
        return {
            "success": False,
            "message": "Devise non prise en charge.",
        }

    currency = target_currency.strip().upper()

    if (
        len(currency) != 3
        or not currency.isascii()
        or not currency.isalpha()
    ):
        return {
            "success": False,
            "message": "Devise non prise en charge.",
        }

    if currency == "XOF":
        return {
            "success": True,
            "amount": float(value),
            "converted_amount": float(value),
            "base_currency": "XOF",
            "target_currency": "XOF",
            "rate": 1.0,
            "date": None,
        }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                f"{FRANKFURTER_URL}/rate/XOF/{currency}"
            )
            response.raise_for_status()
            data = response.json()

        rate = Decimal(str(data["rate"]))

        if not rate.is_finite() or rate <= 0:
            raise ValueError("Taux de change invalide.")

        converted = (value * rate).quantize(Decimal("0.01"))

        return {
            "success": True,
            "amount": float(value),
            "converted_amount": float(converted),
            "base_currency": "XOF",
            "target_currency": currency,
            "rate": float(rate),
            "date": data["date"],
        }

    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in (404, 422):
            return {
                "success": False,
                "message": "Devise non prise en charge.",
            }

        return {
            "success": False,
            "message": "Impossible de récupérer le taux de change. Veuillez réessayer.",
        }

    except (
        httpx.HTTPError,
        KeyError,
        ValueError,
        InvalidOperation,
        TypeError,
    ):
        return {
            "success": False,
            "message": "Impossible de récupérer le taux de change. Veuillez réessayer.",
        }
