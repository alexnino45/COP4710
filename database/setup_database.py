"""
Creates and populates the SQLite database for the COP4710 reading list project.

Run from the project root with:
    python database/setup_database.py
"""

import random
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import BOOKS_CSV_PATH, DB_PATH

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def random_date(start: datetime, end: datetime) -> str:
    delta = end - start
    return (start + timedelta(days=random.randint(0, delta.days))).strftime("%Y-%m-%d")


def initialize_schema(conn: sqlite3.Connection) -> None:
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.executescript(schema_sql)


def load_books(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    try:
        df = pd.read_csv(BOOKS_CSV_PATH, on_bad_lines="skip", encoding="latin-1")
        print(f"Loaded books CSV with {len(df)} rows.")
    except FileNotFoundError:
        print("Books CSV not found. Using placeholder books instead.")
        df = pd.DataFrame()

    if not df.empty:
        rename_map = {}
        for source_name, target_name in {
            "Title": "Title",
            "Author": "Author",
            "Main Genre": "Genre",
        }.items():
            matches = [column for column in df.columns if column.strip() == source_name]
            if matches:
                rename_map[matches[0]] = target_name

        df = df.rename(columns=rename_map)
        kept_columns = [column for column in ["Title", "Author", "Genre"] if column in df.columns]
        df = df[kept_columns].dropna(subset=["Title"]).head(5000)

        records = [
            (
                row.get("Title", "Unknown"),
                row.get("Author", None),
                row.get("Genre", None),
            )
            for _, row in df.iterrows()
        ]

        cur.executemany(
            "INSERT OR IGNORE INTO Book (Title, Author, Genre) VALUES (?, ?, ?)",
            records,
        )
        conn.commit()
        print(f"Inserted {len(records)} books into Book.")
    else:
        placeholder_books = [
            ("The Great Gatsby", "F. Scott Fitzgerald", "Fiction"),
            ("To Kill a Mockingbird", "Harper Lee", "Fiction"),
            ("1984", "George Orwell", "Dystopian"),
            ("Dune", "Frank Herbert", "Sci-Fi"),
            ("The Hobbit", "J.R.R. Tolkien", "Fantasy"),
        ]
        cur.executemany(
            "INSERT OR IGNORE INTO Book (Title, Author, Genre) VALUES (?, ?, ?)",
            placeholder_books,
        )
        conn.commit()
        print("Inserted placeholder books.")


def load_sample_users(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    sample_users = [
        ("Christian Koeller", "christian@example.com"),
        ("Avery Rodriguez", "avery@example.com"),
        ("Alexander Nino", "alexander@example.com"),
        ("Tomas Caruso", "tomas@example.com"),
    ]

    start_range = datetime(2022, 1, 1)
    end_range = datetime(2024, 12, 31)

    for name, email in sample_users:
        join_date = random_date(start_range, end_range)
        cur.execute(
            "INSERT OR IGNORE INTO User (Name, Email, Password, JoinDate) VALUES (?, ?, ?, ?)",
            (name, email, "password123", join_date),
        )
        user_row = cur.execute("SELECT UserID FROM User WHERE Email = ?", (email,)).fetchone()
        if user_row:
            cur.execute("INSERT OR IGNORE INTO List (UserID) VALUES (?)", (user_row[0],))

    conn.commit()
    print("Inserted sample users and lists.")


def print_sanity_check(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    print("\nSanity check:")
    for table_name in ["User", "Book", "List", "Read", "References_"]:
        count = cur.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        print(f"  {table_name}: {count} rows")


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    initialize_schema(conn)
    load_books(conn)
    load_sample_users(conn)
    print_sanity_check(conn)
    conn.close()
    print(f"\nDatabase ready at {DB_PATH}")


if __name__ == "__main__":
    main()
