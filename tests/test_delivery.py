import pytest

from smartstore.tools.delivery import calculate_delivery

@pytest.mark.parametrize(
    ("destination", "expected_fee"),
    [
        ("Cotonou", 1000),
        ("Akpakpa", 1000),
        ("Fidjrossè", 1500),
        ("Calavi", 2000),
        ("Porto-Novo", 3000),
        ("Ouidah", 3500),
    ],
)
def test_delivery_supported_zones(destination, expected_fee):
    result = calculate_delivery(destination)

    assert result["found"] is True
    assert result["delivery_fee"] == expected_fee
    assert result["currency"] == "XOF"
    assert result["delivery_time"] == "24 à 48 heures"

def test_delivery_case_insensitive():
    result = calculate_delivery("COTONOU")

    assert result["found"] is True
    assert result["delivery_fee"] == 1000

def test_delivery_accent_insensitive():
    result = calculate_delivery("Fidjrosse")

    assert result["found"] is True
    assert result["delivery_fee"] == 1500

def test_delivery_unknown_destination():
    result = calculate_delivery("Parakou")

    assert result["found"] is False
    assert "delivery_fee" not in result
    assert result["message"] == "Zone non desservie."
    assert len(result["supported_zones"]) == 6

def test_delivery_empty_destination():
    result = calculate_delivery("")

    assert result["found"] is False
    assert result["message"] == "Veuillez préciser la destination."