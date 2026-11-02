
import pytest

from smartstore.tools.products import search_product


def test_search_existing_product():
    results = search_product("Pagne wax")

    assert len(results) == 1
    assert results[0]["reference"] == "P01"
    assert results[0]["price"] == 12000


def test_search_by_category():
    results = search_product("vêtement")

    assert len(results) == 2
    assert {product["reference"] for product in results} == {"P02", "P05"}


def test_search_by_max_price():
    results = search_product(max_price=10000)

    assert len(results) == 3
    assert {product["reference"] for product in results} == {
        "P03", "P04", "P06"
    }


def test_search_unknown_product():
    results = search_product("Produit inexistant")

    assert results == []


def test_search_is_case_insensitive():
    results = search_product("PAGNE WAX")

    assert len(results) == 1
    assert results[0]["reference"] == "P01"


def test_search_by_reference():
    results = search_product("P06")

    assert len(results) == 1
    assert results[0]["name"] == "Beurre de karité 500 g"


def test_search_by_accent_insensitive_category():
    results = search_product("vetement")

    assert len(results) == 2
