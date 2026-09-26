import sqlite3
from contextlib import closing
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "stocks.db"


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with closing(connect()) as connection:
        with connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS stocks (
                    exchange TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    series TEXT NOT NULL,
                    company_name TEXT NOT NULL,
                    isin TEXT NOT NULL,
                    PRIMARY KEY (exchange, symbol, series)
                );

                CREATE TABLE IF NOT EXISTS directory_imports (
                    exchange TEXT PRIMARY KEY,
                    imported_at TEXT NOT NULL,
                    source_file TEXT NOT NULL,
                    row_count INTEGER NOT NULL
                );
            """)