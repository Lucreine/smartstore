
import json

import pytest

from smartstore.tools import inventory


INITIAL_STOCK = {
    "P01": 14,
    "P02": 3,
    "P03": 0,
    "P04": 8,
    "P05": 5,
    "P06": 40,
}


@pytest.fixture(autouse=True)
def setup_stock(tmp_path, monkeypatch):
    """Utilise un fichier JSON temporaire pour chaque test."""
    stock_file = tmp_path / "stock.json"

    stock_file.write_text(
        json.dumps(INITIAL_STOCK),
        encoding="utf-8",
    )

    monkeypatch.setattr(inventory, "STOCK_FILE", stock_file)


@pytest.mark.parametrize(
    ("reference", "expected_quantity"),
    [
        ("P01", 14),
        ("P02", 3),
        ("P03", 0),
        ("P04", 8),
        ("P05", 5),
        ("P06", 40),
    ],
)
def test_check_stock_for_all_products(reference, expected_quantity):
    result = inventory.check_stock(reference)

    assert result["found"] is True
    assert result["quantity"] == expected_quantity
    assert result["available"] is (expected_quantity > 0)


def test_check_out_of_stock_product():
    result = inventory.check_stock("P03")

    assert result["found"] is True
    assert result["available"] is False
    assert result["quantity"] == 0
    assert result["message"] == "Produit en rupture de stock."


def test_check_unknown_product():
    result = inventory.check_stock("UNKNOWN")

    assert result["found"] is False
    assert "quantity" not in result
    assert result["message"] == "référence inconnue"


def test_reference_is_case_insensitive():
    result = inventory.check_stock("p01")

    assert result["found"] is True
    assert result["quantity"] == 14


def test_reference_with_spaces():
    result = inventory.check_stock(" P01 ")

    assert result["found"] is True
    assert result["quantity"] == 14


def test_decrease_stock():
    result = inventory.decrease_stock("P05", 2)

    assert result["success"] is True
    assert result["remaining_stock"] == 3
    assert inventory.check_stock("P05")["quantity"] == 3


def test_cannot_decrease_more_than_available():
    result = inventory.decrease_stock("P05", 6)

    assert result["success"] is False
    assert inventory.check_stock("P05")["quantity"] == 5


def test_cannot_decrease_with_invalid_quantity():
    for quantity in (0, -1, 1.5, True):
        result = inventory.decrease_stock("P05", quantity)
        assert result["success"] is False


def test_stock_is_persisted_in_json():
    inventory.decrease_stock("P01", 2)

    saved_stock = json.loads(
        inventory.STOCK_FILE.read_text(encoding="utf-8")
    )

    assert saved_stock["P01"] == 12
