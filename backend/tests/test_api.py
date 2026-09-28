import pytest

def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_empty_directory(client):
    response = client.get("/stocks")

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "total": 0,
        "page": 1,
        "page_size": 25,
    }

    metadata = client.get("/directory").json()
    assert metadata["import"] is None
    assert metadata["prices_available"] is False
    assert metadata["predictions_available"] is False

@pytest.mark.parametrize(
    "query, expected_symbols",
    [
        ("alpha", ["ALPHA"]),
        ("  ALPHA  ", ["ALPHA"]),
        ("industries", ["ALPHA", "GAMMA"]),
        ("does-not-exist", []),
        ("%", ["PERCENT"]),
        ("_", ["UNDER"]),
        ("' OR 1=1 --", []),
    ],
)
def test_search(client, seeded_stocks, query, expected_symbols):
    response = client.get("/stocks", params={"q": query})

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == len(expected_symbols)
    assert [stock["symbol"] for stock in data["items"]] == expected_symbols

def test_pagination_has_no_duplicates_or_missing_rows(client, seeded_stocks):
    symbols = []

    for page in (1, 2, 3):
        response = client.get(
            "/stocks",
            params={"page": page, "page_size": 2},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 5
        assert data["page"] == page
        assert data["page_size"] == 2

        symbols.extend(stock["symbol"] for stock in data["items"])

    assert symbols == [stock[1] for stock in seeded_stocks]
    assert len(symbols) == len(set(symbols))

def test_page_beyond_results_is_empty(client, seeded_stocks):
    response = client.get(
        "/stocks",
        params={"page": 99, "page_size": 2},
    )

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total"] == 5

@pytest.mark.parametrize(
    "params",
    [
        {"page": 0},
        {"page": -1},
        {"page": "abc"},
        {"page_size": 0},
        {"page_size": 101},
        {"q": "a" * 101},
    ],
)
def test_invalid_query_parameters(client, params):
    response = client.get("/stocks", params=params)

    assert response.status_code == 422

def test_dashboard_is_served(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Stock AI" in response.text
