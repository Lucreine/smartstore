
import json

import pytest

from smartstore.tools import inventory, orders


INITIAL_STOCK = {
    "P01": 14,
    "P02": 3,
    "P03": 0,
    "P04": 8,
    "P05": 5,
    "P06": 40,
}


@pytest.fixture(autouse=True)
def setup_files(tmp_path, monkeypatch):
    """Utilise des fichiers JSON temporaires pour chaque test."""

    stock_file = tmp_path / "stock.json"
    orders_file = tmp_path / "commandes.json"

    stock_file.write_text(
        json.dumps(INITIAL_STOCK),
        encoding="utf-8",
    )
    orders_file.write_text("[]", encoding="utf-8")

    monkeypatch.setattr(inventory, "STOCK_FILE", stock_file)
    monkeypatch.setattr(orders, "ORDERS_FILE", orders_file)


def create_test_request():
    return orders.create_order_request(
        customer_name="Amina",
        customer_phone="97000000",
        destination="Cotonou",
        items=[
            {
                "reference": "P05",
                "quantity": 2,
            }
        ],
        client_consent=True,
    )

def test_create_order_request(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "o")

    result = create_test_request()

    assert result["success"] is True
    assert result["approved"] is True
    assert result["order"]["subtotal"] == 44000
    assert result["order"]["delivery_fee"] == 1000
    assert result["order"]["total"] == 45000
    assert result["order"]["status"] == "confirmed"


def test_order_decreases_stock_after_approval(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "o")

    create_test_request()

    result = inventory.check_stock("P05")

    assert result["quantity"] == 3


def test_order_is_saved_in_json(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "o")

    create_test_request()

    saved_orders = orders.load_orders()

    assert len(saved_orders) == 1
    assert saved_orders[0]["customer_name"] == "Amina"
    assert saved_orders[0]["total"] == 45000


def test_order_refused_by_manager(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "n")

    result = create_test_request()

    assert result["success"] is False
    assert result["approved"] is False
    assert inventory.check_stock("P05")["quantity"] == 5
    assert orders.load_orders() == []


def test_cannot_order_out_of_stock_product(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "o")

    result = orders.create_order_request(
        customer_name="Amina",
        customer_phone="97000000",
        destination="Cotonou",
        items=[
            {
                "reference": "P03",
                "quantity": 1,
            }
        ],
    )

    assert result["success"] is False
    assert "stock insuffisant" in result["message"]
    assert inventory.check_stock("P03")["quantity"] == 0
    assert orders.load_orders() == []


def test_cannot_order_more_than_available(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "o")

    result = orders.create_order_request(
        customer_name="Amina",
        customer_phone="97000000",
        destination="Cotonou",
        items=[
            {
                "reference": "P05",
                "quantity": 6,
            }
        ],
    )

    assert result["success"] is False
    assert inventory.check_stock("P05")["quantity"] == 5
    assert orders.load_orders() == []


def test_cannot_order_in_unsupported_zone(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "o")

    result = orders.create_order_request(
        customer_name="Amina",
        customer_phone="97000000",
        destination="Lomé",
        items=[
            {
                "reference": "P05",
                "quantity": 1,
            }
        ],
    )

    assert result["success"] is False
    assert "supported_zones" in result
    assert inventory.check_stock("P05")["quantity"] == 5
    assert orders.load_orders() == []


def test_cannot_order_with_invalid_quantity(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "o")

    for quantity in (0, -1, 1.5, True):
        result = orders.create_order_request(
            customer_name="Amina",
            customer_phone="97000000",
            destination="Cotonou",
            items=[
                {
                    "reference": "P05",
                    "quantity": quantity,
                }
            ],
        )

        assert result["success"] is False

    assert inventory.check_stock("P05")["quantity"] == 5
    assert orders.load_orders() == []

def test_order_requires_customer_consent(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "o")

    result = orders.create_order_request(
        customer_name="Amina",
        customer_phone="97000000",
        destination="Calavi",
        items=[
            {
                "reference": "P05",
                "quantity": 2,
            }
        ],
        mode="validation",
        client_consent=False,
    )

    assert result["success"] is False
    assert result["approved"] is False
    assert "consentement" in result["message"].lower()

    stock = inventory.check_stock("P05")
    assert stock["quantity"] == 5

    assert orders.load_orders() == []