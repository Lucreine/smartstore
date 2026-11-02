
import httpx
import pytest

from smartstore.tools import currency


class FakeResponse:
    status_code = 200

    def raise_for_status(self):
        pass

    def json(self):
        return {
            "date": "2026-11-02",
            "base": "XOF",
            "quote": "EUR",
            "rate": 0.0015238,
        }


class FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def get(self, url):
        assert url.endswith("/rate/XOF/EUR")
        return FakeResponse()


class UnsupportedCurrencyResponse:
    status_code = 404

    def raise_for_status(self):
        request = httpx.Request("GET", "https://api.frankfurter.dev/v2/rate/XOF/ABC")
        response = httpx.Response(404, request=request)
        raise httpx.HTTPStatusError(
            "Not Found",
            request=request,
            response=response,
        )


class UnsupportedCurrencyClient(FakeAsyncClient):
    async def get(self, url):
        return UnsupportedCurrencyResponse()


@pytest.mark.asyncio
async def test_convert_xof_to_eur(monkeypatch):
    monkeypatch.setattr(
        currency.httpx,
        "AsyncClient",
        FakeAsyncClient,
    )

    result = await currency.convert_currency(10000, "EUR")

    assert result["success"] is True
    assert result["amount"] == 10000.0
    assert result["converted_amount"] == 15.24
    assert result["base_currency"] == "XOF"
    assert result["target_currency"] == "EUR"
    assert result["rate"] == 0.0015238
    assert result["date"] == "2026-11-02"


@pytest.mark.asyncio
async def test_convert_xof_to_xof():
    result = await currency.convert_currency(10000, "XOF")

    assert result["success"] is True
    assert result["converted_amount"] == 10000.0
    assert result["rate"] == 1.0


@pytest.mark.asyncio
@pytest.mark.parametrize("amount", [0, -100, "abc", float("inf")])
async def test_reject_invalid_amount(amount):
    result = await currency.convert_currency(amount, "EUR")

    assert result["success"] is False
    assert "message" in result


@pytest.mark.asyncio
@pytest.mark.parametrize("currency_code", ["", "EURO", "12A", "ÉUR"])
async def test_reject_invalid_currency(currency_code):
    result = await currency.convert_currency(10000, currency_code)

    assert result["success"] is False
    assert result["message"] == "Devise non prise en charge."


@pytest.mark.asyncio
async def test_reject_unsupported_currency(monkeypatch):
    monkeypatch.setattr(
        currency.httpx,
        "AsyncClient",
        UnsupportedCurrencyClient,
    )

    result = await currency.convert_currency(10000, "ABC")

    assert result["success"] is False
    assert result["message"] == "Devise non prise en charge."
