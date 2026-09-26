from contextlib import asynccontextmanager, closing

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from database import BASE_DIR, connect, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Stock AI API",
    description="Local stock directory. No live prices or AI predictions yet.",
    version="0.2.0",
    lifespan=lifespan,
)


class Stock(BaseModel):
    exchange: str
    symbol: str
    series: str
    company_name: str
    isin: str


class StockPage(BaseModel):
    items: list[Stock]
    total: int
    page: int
    page_size: int


@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "stock-ai-backend"}


@app.get("/directory")
def directory_status():
    with closing(connect()) as connection:
        row = connection.execute(
            """
            SELECT exchange, imported_at, source_file, row_count
            FROM directory_imports
            WHERE exchange = ?
            """,
            ("NSE",),
        ).fetchone()

    return {
        "exchange": "NSE",
        "import": dict(row) if row else None,
        "prices_available": False,
        "predictions_available": False,
    }


@app.get("/stocks", response_model=StockPage)
def list_stocks(
    q: str = Query(default="", max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
):
    query = q.strip()

    # Treat %, _, and backslash as literal search characters.
    escaped = (
        query.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )
    pattern = f"%{escaped}%"

    where = """
        WHERE exchange = ?
          AND (
              symbol LIKE ? ESCAPE '\\'
              OR company_name LIKE ? ESCAPE '\\'
          )
    """
    parameters = ("NSE", pattern, pattern)

    with closing(connect()) as connection:
        # Keep count and results within the same read snapshot.
        connection.execute("BEGIN")

        total = connection.execute(
            f"SELECT COUNT(*) FROM stocks {where}",
            parameters,
        ).fetchone()[0]

        rows = connection.execute(
            f"""
            SELECT exchange, symbol, series, company_name, isin
            FROM stocks
            {where}
            ORDER BY symbol, series
            LIMIT ? OFFSET ?
            """,
            (*parameters, page_size, (page - 1) * page_size),
        ).fetchall()

    return StockPage(
        items=[Stock(**dict(row)) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )
