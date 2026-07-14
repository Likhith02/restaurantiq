"""Storage layer.

Local (your laptop): SQLite — a single file, zero setup.
Online (Render etc.): PostgreSQL — set the DATABASE_URL environment variable
and the same code uses the cloud database instead, so data survives restarts.
"""
import os
import sqlite3
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path

DATABASE_URL = os.environ.get("DATABASE_URL", "")
IS_PG = DATABASE_URL.startswith(("postgres://", "postgresql://"))

if IS_PG:
    import psycopg
    from psycopg.rows import dict_row

# RIQ_DB_PATH lets tests (and containers) relocate the SQLite file.
DB_PATH = Path(os.environ.get("RIQ_DB_PATH") or Path(__file__).resolve().parent.parent / "restaurantiq.db")

_ID = "SERIAL PRIMARY KEY" if IS_PG else "INTEGER PRIMARY KEY AUTOINCREMENT"
_FLOAT = "DOUBLE PRECISION" if IS_PG else "REAL"

SCHEMA = [
    f"""CREATE TABLE IF NOT EXISTS restaurants (
      id {_ID},
      phone TEXT UNIQUE NOT NULL,
      name TEXT,
      rtype TEXT,
      seats INTEGER,
      currency TEXT DEFAULT '₹'
    )""",
    f"""CREATE TABLE IF NOT EXISTS entries (
      id {_ID},
      restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
      date TEXT NOT NULL,
      sales {_FLOAT} NOT NULL,
      customers INTEGER,
      staff_count INTEGER,
      staff_cost {_FLOAT},
      food_cost {_FLOAT},
      notes TEXT,
      UNIQUE(restaurant_id, date)
    )""",
    f"""CREATE TABLE IF NOT EXISTS otps (
      phone TEXT PRIMARY KEY,
      code TEXT NOT NULL,
      expires_at {_FLOAT} NOT NULL
    )""",
]


def _q(sql: str) -> str:
    """SQLite uses ? placeholders, PostgreSQL uses %s. One codebase, both work."""
    return sql.replace("?", "%s") if IS_PG else sql


@contextmanager
def _db():
    if IS_PG:
        with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
            yield conn
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


def init_db() -> None:
    with _db() as conn:
        for stmt in SCHEMA:
            conn.execute(stmt)


def get_restaurant_by_phone(phone: str):
    with _db() as conn:
        row = conn.execute(_q("SELECT * FROM restaurants WHERE phone=?"), (phone,)).fetchone()
        return dict(row) if row else None


def get_restaurant(rid: int):
    with _db() as conn:
        row = conn.execute(_q("SELECT * FROM restaurants WHERE id=?"), (rid,)).fetchone()
        return dict(row) if row else None


def create_restaurant(phone: str) -> int:
    with _db() as conn:
        row = conn.execute(
            _q("INSERT INTO restaurants (phone) VALUES (?) RETURNING id"), (phone,)
        ).fetchone()
        return row["id"]


def update_restaurant(rid: int, name: str, rtype: str, seats: int | None, currency: str) -> None:
    with _db() as conn:
        conn.execute(
            _q("UPDATE restaurants SET name=?, rtype=?, seats=?, currency=? WHERE id=?"),
            (name, rtype, seats, currency, rid),
        )


def upsert_entry(rid: int, entry: dict) -> None:
    with _db() as conn:
        conn.execute(
            _q(
                "INSERT INTO entries (restaurant_id, date, sales, customers, staff_count, staff_cost, food_cost, notes) "
                "VALUES (?,?,?,?,?,?,?,?) "
                "ON CONFLICT (restaurant_id, date) DO UPDATE SET "
                "sales=excluded.sales, customers=excluded.customers, staff_count=excluded.staff_count, "
                "staff_cost=excluded.staff_cost, food_cost=excluded.food_cost, notes=excluded.notes"
            ),
            (rid, entry["date"], entry["sales"], entry.get("customers"), entry.get("staff_count"),
             entry.get("staff_cost"), entry.get("food_cost"), entry.get("notes")),
        )


def get_entries(rid: int, days: int = 90) -> list[dict]:
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    with _db() as conn:
        rows = conn.execute(
            _q(
                "SELECT date, sales, customers, staff_count, staff_cost, food_cost, notes "
                "FROM entries WHERE restaurant_id=? AND date >= ? ORDER BY date ASC"
            ),
            (rid, cutoff),
        ).fetchall()
        return [dict(r) for r in rows]


def save_otp(phone: str, code: str, expires_at: float) -> None:
    with _db() as conn:
        conn.execute(
            _q(
                "INSERT INTO otps (phone, code, expires_at) VALUES (?,?,?) "
                "ON CONFLICT (phone) DO UPDATE SET code=excluded.code, expires_at=excluded.expires_at"
            ),
            (phone, code, expires_at),
        )


def pop_otp(phone: str):
    with _db() as conn:
        row = conn.execute(_q("SELECT code, expires_at FROM otps WHERE phone=?"), (phone,)).fetchone()
        if row:
            conn.execute(_q("DELETE FROM otps WHERE phone=?"), (phone,))
        return dict(row) if row else None
