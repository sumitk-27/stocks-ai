import sys
from contextlib import closing

import pytest

from database import connect
from import_stocks import main as import_main
from import_stocks import read_stocks

def run_import(path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["import_stocks.py", str(path)])
    import_main()

def test_reader_normalizes_headers_and_values(make_csv):
    path = make_csv(
        [[" alpha ", " Alpha Limited ", " eq ", " test00000001 "]],
        headers=(
            " SYMBOL ",
            " NAME OF COMPANY ",
            " SERIES ",
            " ISIN NUMBER ",
        ),
    )

    assert read_stocks(path) == [
        ("NSE", "ALPHA", "EQ", "Alpha Limited", "TEST00000001")
    ]

@pytest.mark.parametrize(
    "rows, expected_error",
    [
        ([], "no stocks"),
        (
            [["ALPHA", "", "EQ", "TEST00000001"]],
            "Missing required value",
        ),
        (
            [
                ["ALPHA", "Alpha Limited", "EQ", "TEST00000001"],
                ["alpha", "Alpha Limited", "eq", "TEST00000001"],
            ],
            "Duplicate",
        ),
        (
            [["ALPHA", "Alpha Limited", "EQ", "TEST00000001", "extra"]],
            "extra columns",
        ),
    ],
)
def test_reader_rejects_invalid_rows(make_csv, rows, expected_error):
    path = make_csv(rows)

    with pytest.raises(ValueError, match=expected_error):
        read_stocks(path)

def test_reader_rejects_wrong_headers(make_csv):
    path = make_csv(
        [["ALPHA", "Alpha Limited"]],
        headers=("ticker", "company"),
    )

    with pytest.raises(ValueError, match="Missing required CSV columns"):
        read_stocks(path)

def test_import_replaces_snapshot_and_records_metadata(
    make_csv, monkeypatch, seeded_stocks
):
    path = make_csv([
        ["NEW", "New Company", "EQ", "TEST00000099"],
    ])

    run_import(path, monkeypatch)

    with closing(connect()) as connection:
        stocks = connection.execute(
            "SELECT symbol FROM stocks ORDER BY symbol"
        ).fetchall()
        metadata = connection.execute(
            "SELECT * FROM directory_imports WHERE exchange = 'NSE'"
        ).fetchone()

    assert [row["symbol"] for row in stocks] == ["NEW"]
    assert metadata["row_count"] == 1
    assert metadata["source_file"] == "listings.csv"
    assert metadata["imported_at"]

def test_invalid_import_preserves_existing_directory(
    make_csv, monkeypatch, seeded_stocks
):
    path = make_csv([
        ["NEW", "New Company", "EQ", "TEST00000099"],
        ["BROKEN", "", "EQ", "TEST00000100"],
    ])

    with pytest.raises(SystemExit, match="directory unchanged"):
        run_import(path, monkeypatch)

    with closing(connect()) as connection:
        rows = connection.execute(
            "SELECT symbol FROM stocks ORDER BY symbol"
        ).fetchall()

    assert [row["symbol"] for row in rows] == [
        stock[1] for stock in seeded_stocks
    ]

def test_repeated_import_does_not_duplicate_listings(make_csv, monkeypatch):
    path = make_csv([
        ["ALPHA", "Alpha Limited", "EQ", "TEST00000001"],
    ])

    run_import(path, monkeypatch)
    run_import(path, monkeypatch)

    with closing(connect()) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM stocks"
        ).fetchone()[0]

    assert count == 1
