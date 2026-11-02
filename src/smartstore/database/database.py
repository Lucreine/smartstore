import sqlite3
from pathlib import Path

DATABASE_PATH = Path("smartstore.db")


def get_connection() -> sqlite3.Connection:
    """Retourne une connexion à la base de données SQLite."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_database() -> None:
    """Crée les tables nécessaires au fonctionnement de la boutique."""
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS order_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                customer_phone TEXT NOT NULL,
                destination TEXT NOT NULL,
                items TEXT NOT NULL,
                subtotal INTEGER NOT NULL,
                delivery_fee INTEGER NOT NULL,
                total INTEGER NOT NULL,
                customer_approved INTEGER NOT NULL DEFAULT 0,
                manager_approved INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER NOT NULL UNIQUE,
                customer_name TEXT NOT NULL,
                customer_phone TEXT NOT NULL,
                destination TEXT NOT NULL,
                items TEXT NOT NULL,
                subtotal INTEGER NOT NULL,
                delivery_fee INTEGER NOT NULL,
                total INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (request_id)
                    REFERENCES order_requests(id)
            )
        """)
        