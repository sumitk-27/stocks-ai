import csv
from contextlib import closing

import pytest
from fastapi.testclient import TestClient

import database
from main import app

@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    """Redirect all database operations to a fresh temporary file."""
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test-stocks.db")
    database.init_db()

@pytest.fixture
def client(isolated_database):
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture
def seeded_stocks(isolated_database):
    """Synthetic test data, not real prices or verified listings."""
    stocks = [
        ("NSE", "ALPHA", "EQ", "Alpha Industries", "TEST00000001"),
        ("NSE", "BETA", "EQ", "Beta Technologies", "TEST00000002"),
        ("NSE", "GAMMA", "EQ", "Gamma Industries", "TEST00000003"),
        ("NSE", "PERCENT", "EQ", "Growth 100% Holdings", "TEST00000004"),
        ("NSE", "UNDER", "EQ", "Under_score Limited", "TEST00000005"),
    ]

    with closing(database.connect()) as connection:
        with connection:
            connection.executemany(
                """
                INSERT INTO stocks
                    (exchange, symbol, series, company_name, isin)
                VALUES (?, ?, ?, ?, ?)
                """,
                stocks,
            )

    return stocks

@pytest.fixture
def make_csv(tmp_path):
    def create(
        rows,
        headers=("SYMBOL", "NAME OF COMPANY", "SERIES", "ISIN NUMBER"),
    ):
        path = tmp_path / "listings.csv"

        with path.open("w", encoding="utf-8-sig", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(headers)
            writer.writerows(rows)

        return path

    return create
