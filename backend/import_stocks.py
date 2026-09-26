import argparse
import csv
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from database import connect, init_db

REQUIRED_COLUMNS = {
    "SYMBOL",
    "NAME OF COMPANY",
    "SERIES",
    "ISIN NUMBER",
}

def read_stocks(path: Path) -> list[tuple[str, str, str, str, str]]:
    stocks = []
    seen = set()

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise ValueError("The CSV has no header.")

        # Exchange exports can include spaces around column names.
        reader.fieldnames = [name.strip() for name in reader.fieldnames]

        missing = REQUIRED_COLUMNS - set(reader.fieldnames)
        if missing:
            raise ValueError(
                "Missing required CSV columns: " + ", ".join(sorted(missing))
            )

        for line_number, row in enumerate(reader, start=2):
            if None in row:
                raise ValueError(f"Unexpected extra columns on row {line_number}.")

            values = {
                name: (row.get(name) or "").strip()
                for name in REQUIRED_COLUMNS
            }

            if not all(values.values()):
                raise ValueError(f"Missing required value on row {line_number}.")

            symbol = values["SYMBOL"].upper()
            series = values["SERIES"].upper()
            key = (symbol, series)

            if key in seen:
                raise ValueError(
                    f"Duplicate symbol/series on row {line_number}: {key}"
                )

            seen.add(key)
            stocks.append((
                "NSE",
                symbol,
                series,
                values["NAME OF COMPANY"],
                values["ISIN NUMBER"].upper(),
            ))

    if not stocks:
        raise ValueError("The CSV contains no stocks.")

    return stocks

def main() -> None:
    parser = argparse.ArgumentParser(description="Import an NSE listing CSV.")
    parser.add_argument("csv_path", type=Path)
    args = parser.parse_args()

    # Validate the entire file before changing the database.
    try:
        stocks = read_stocks(args.csv_path)
    except (OSError, UnicodeError, ValueError, csv.Error) as error:
        raise SystemExit(f"Import failed; directory unchanged: {error}")

    init_db()
    imported_at = datetime.now(timezone.utc).isoformat()

    with closing(connect()) as connection:
        # Replacement and metadata update succeed or roll back together.
        with connection:
            connection.execute("DELETE FROM stocks WHERE exchange = ?", ("NSE",))
            connection.executemany(
                """
                INSERT INTO stocks
                    (exchange, symbol, series, company_name, isin)
                VALUES (?, ?, ?, ?, ?)
                """,
                stocks,
            )
            connection.execute(
                """
                INSERT INTO directory_imports
                    (exchange, imported_at, source_file, row_count)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(exchange) DO UPDATE SET
                    imported_at = excluded.imported_at,
                    source_file = excluded.source_file,
                    row_count = excluded.row_count
                """,
                ("NSE", imported_at, args.csv_path.name, len(stocks)),
            )

    print(f"Imported {len(stocks):,} NSE listings.")
    print(f"Import time: {imported_at}")

if __name__ == "__main__":
    main()
