
from smartstore.agent.evaluator import evaluate_response


def make_trace():
    return [
        {
            "tool": "chercher_produits",
            "arguments": {"query": "sac"},
            "result": {
                "success": True,
                "products": [
                    {
                        "reference": "P03",
                        "name": "Sac en raphia",
                        "price": 7500,
                    },
                    {
                        "reference": "P04",
                        "name": "Sandales en cuir",
                        "price": 9000,
                    },
                ],
            },
        },
        {
            "tool": "verifier_stock",
            "arguments": {"reference": "P03"},
            "result": {
                "found": True,
                "reference": "P03",
                "available": False,
                "quantity": 0,
            },
        },
        {
            "tool": "verifier_stock",
            "arguments": {"reference": "P04"},
            "result": {
                "found": True,
                "reference": "P04",
                "available": True,
                "quantity": 8,
            },
        },
    ]


def test_response_under_80_words():
    result = evaluate_response(
        "Bonjour ! Bienvenue dans notre boutique.",
        [],
    )

    assert result["passed"] is True
    assert result["word_count"] <= 80

def test_response_over_80_words():
    response = "Bonjour " + "merci " * 80

    result = evaluate_response(response, [])

    assert result["passed"] is False
    assert any("80 maximum" in issue for issue in result["issues"])


def test_detect_false_stock_availability():
    result = evaluate_response(
        "Le sac en raphia est disponible.",
        make_trace(),
    )

    assert result["passed"] is False
    assert any("disponible" in issue for issue in result["issues"])


def test_accept_available_alternative():
    result = evaluate_response(
        "Le sac en raphia est en rupture de stock. "
        "Je vous propose les sandales en cuir, disponibles.",
        make_trace(),
    )

    assert result["passed"] is True


def test_reject_response_without_alternative():
    result = evaluate_response(
        "Le sac en raphia est en rupture de stock.",
        make_trace(),
    )

    assert result["passed"] is False
    assert any("alternative" in issue for issue in result["issues"])


def test_reject_unapproved_order_confirmation():
    trace = make_trace() + [
        {
            "tool": "creer_commande",
            "arguments": {},
            "result": {
                "success": False,
                "approved": False,
                "message": "Commande refusée.",
            },
        }
    ]

    result = evaluate_response(
        "Votre commande est confirmée.",
        trace,
    )

    assert result["passed"] is False
    assert any("commande confirmée" in issue for issue in result["issues"])

def test_accept_unapproved_order_refusal_message():
    trace = [
        {
            "tool": "creer_commande",
            "arguments": {},
            "result": {
                "success": False,
                "approved": False,
                "message": "Commande refusée.",
            },
        }
    ]

    result = evaluate_response(
        "La commande n'a pas été enregistrée.",
        trace,
    )

    assert result["passed"] is True


def test_accept_correct_order_total():
    trace = [
        {
            "tool": "chercher_produits",
            "result": {
                "products": [
                    {
                        "reference": "P05",
                        "name": "Robe en wax",
                        "price": 22000,
                    }
                ]
            },
        },
        {
            "tool": "creer_commande",
            "result": {
                "success": True,
                "mode": "devis",
                "currency": "XOF",
                "items": [
                    {
                        "reference": "P05",
                        "name": "Robe en wax",
                        "quantity": 2,
                        "unit_price": 22000,
                        "subtotal": 44000,
                    }
                ],
                "subtotal": 44000,
                "delivery_fee": 2000,
                "total": 46000,
            },
        },
    ]

    response = (
        "Deux robes en wax : 44 000 FCFA. "
        "Livraison : 2 000 FCFA. Total : 46 000 FCFA."
    )

    result = evaluate_response(response, trace)

    assert result["passed"] is True


def test_reject_incorrect_order_total():
    trace = [
        {
            "tool": "chercher_produits",
            "result": {
                "products": [
                    {
                        "reference": "P05",
                        "name": "Robe en wax",
                        "price": 22000,
                    }
                ]
            },
        },
        {
            "tool": "creer_commande",
            "result": {
                "success": True,
                "mode": "devis",
                "currency": "XOF",
                "items": [
                    {
                        "reference": "P05",
                        "name": "Robe en wax",
                        "quantity": 2,
                        "unit_price": 22000,
                        "subtotal": 44000,
                    }
                ],
                "subtotal": 44000,
                "delivery_fee": 2000,
                "total": 46000,
            },
        },
    ]

    response = "Le total de votre commande est de 48 000 FCFA."

    result = evaluate_response(response, trace)

    assert result["passed"] is False
    assert any("montant annoncé" in issue for issue in result["issues"])


def test_reject_incorrect_quote_arithmetic():
    trace = [
        {
            "tool": "creer_commande",
            "result": {
                "success": True,
                "mode": "devis",
                "currency": "XOF",
                "items": [
                    {
                        "reference": "P05",
                        "name": "Robe en wax",
                        "quantity": 2,
                        "unit_price": 22000,
                        "subtotal": 44000,
                    }
                ],
                "subtotal": 44000,
                "delivery_fee": 2000,
                "total": 48000,
            },
        }
    ]

    result = evaluate_response(
        "Le total est de 48 000 FCFA.",
        trace,
    )

    assert result["passed"] is False
    assert any("total du devis" in issue for issue in result["issues"])

def test_reject_quote_request_without_tool_calls():
    result = evaluate_response(
        response="Bonjour Afi ! Je vais préparer votre devis.",
        trace=[],
        user_message=(
            "Je veux 2 robes en wax et 1 sac en raphia "
            "livrés à Calavi. Préparez-moi un devis."
        ),
    )

    assert result["passed"] is False
    assert any(
        "chercher_produits" in issue
        for issue in result["issues"]
    )
    assert any(
        "verifier_stock" in issue
        for issue in result["issues"]
    )
    assert any(
        "frais_livraison" in issue
        for issue in result["issues"]
    )


def test_accept_quote_request_with_required_tools():
    trace = [
        {
            "tool": "chercher_produits",
            "result": {
                "success": True,
                "products": [
                    {
                        "reference": "P05",
                        "name": "Robe en wax",
                        "price": 22000,
                    }
                ],
            },
        },
        {
            "tool": "verifier_stock",
            "result": {
                "found": True,
                "reference": "P05",
                "available": True,
                "quantity": 5,
            },
        },
        {
            "tool": "frais_livraison",
            "result": {
                "found": True,
                "destination": "Calavi",
                "fee": 2000,
            },
        },
    ]

    result = evaluate_response(
        response="Les robes sont disponibles. Je prépare votre devis.",
        trace=trace,
        user_message="Je souhaite un devis pour deux robes en wax à Calavi.",
    )

    assert result["passed"] is True