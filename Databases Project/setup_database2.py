"""
COP 4710 Term Project — Database Setup Script
Run this once to create and populate the SQLite database.

Usage:
    python -m pip install pandas
    python setup_database.py

Place Books_df.csv in the same folder before running.
"""

import sqlite3
import pandas as pd
import random
from datetime import datetime, timedelta

DB_PATH = "reading_list.db"
KAGGLE_CSV = "Books_df.csv"

# ── Helpers ──────────────────────────────────────────────────────────────────

def random_date(start: datetime, end: datetime) -> str:
    delta = end - start
    return (start + timedelta(days=random.randint(0, delta.days))).strftime("%Y-%m-%d")


# ── 1. Connect and create schema ──────────────────────────────────────────────

conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()

cur.executescript("""
    PRAGMA foreign_keys = ON;

    -- One row per user account
    CREATE TABLE IF NOT EXISTS User (
        UserID   INTEGER PRIMARY KEY AUTOINCREMENT,
        Name     TEXT    NOT NULL,
        Email    TEXT    NOT NULL UNIQUE,
        JoinDate TEXT    NOT NULL
    );

    -- One row per book in the catalog
    CREATE TABLE IF NOT EXISTS Book (
        BookID  INTEGER PRIMARY KEY AUTOINCREMENT,
        Title   TEXT    NOT NULL,
        Author  TEXT,
        Genre   TEXT
    );

    -- One row per user — represents their personal reading list
    CREATE TABLE IF NOT EXISTS List (
        ListID  INTEGER PRIMARY KEY AUTOINCREMENT,
        UserID  INTEGER NOT NULL UNIQUE,
        FOREIGN KEY (UserID) REFERENCES User(UserID) ON DELETE CASCADE
    );

    -- Tracks which books are on which list, and the reading status/dates
    CREATE TABLE IF NOT EXISTS References_ (
        BookID    INTEGER NOT NULL,
        ListID    INTEGER NOT NULL,
        Status    TEXT    NOT NULL CHECK(Status IN ('want to read','currently reading','finished')),
        DateAdded TEXT    NOT NULL,
        StartDate TEXT,
        EndDate   TEXT,
        PRIMARY KEY (BookID, ListID),
        FOREIGN KEY (BookID) REFERENCES Book(BookID) ON DELETE CASCADE,
        FOREIGN KEY (ListID) REFERENCES List(ListID) ON DELETE CASCADE
    );

    -- Tracks books a user has fully read (many-to-many)
    CREATE TABLE IF NOT EXISTS Read (
        UserID  INTEGER NOT NULL,
        BookID  INTEGER NOT NULL,
        PRIMARY KEY (UserID, BookID),
        FOREIGN KEY (UserID) REFERENCES User(UserID) ON DELETE CASCADE,
        FOREIGN KEY (BookID) REFERENCES Book(BookID) ON DELETE CASCADE
    );
""")

print("✓ Schema created.")


# ── 2. Load Books_df.csv into Book table ──────────────────────────────────────

try:
    df = pd.read_csv(KAGGLE_CSV, on_bad_lines="skip", encoding="latin-1")
    print(f"  CSV loaded: {len(df)} rows, columns: {list(df.columns)}")
except FileNotFoundError:
    print(f"⚠ '{KAGGLE_CSV}' not found. Skipping book import — add the file and re-run.")
    df = pd.DataFrame()

if not df.empty:
    col_map = {
        "Title":      "Title",
        "Author":     "Author",
        "Main Genre": "Genre",
    }

    rename = {}
    for src, dst in col_map.items():
        matches = [c for c in df.columns if c.strip() == src]
        if matches:
            rename[matches[0]] = dst

    df = df.rename(columns=rename)

    keep = [c for c in ["Title", "Author", "Genre"] if c in df.columns]
    df = df[keep].dropna(subset=["Title"])
    df = df.head(5000)

    records = [
        (
            row.get("Title", "Unknown"),
            row.get("Author", None),
            row.get("Genre",  None),
        )
        for _, row in df.iterrows()
    ]

    cur.executemany(
        "INSERT OR IGNORE INTO Book (Title, Author, Genre) VALUES (?,?,?)",
        records
    )
    conn.commit()
    print(f"✓ {len(records)} books inserted into Book table.")
else:
    placeholder_books = [
        ("The Great Gatsby",      "F. Scott Fitzgerald", "Fiction"),
        ("To Kill a Mockingbird", "Harper Lee",          "Fiction"),
        ("1984",                  "George Orwell",       "Dystopian"),
        ("Dune",                  "Frank Herbert",       "Sci-Fi"),
        ("The Hobbit",            "J.R.R. Tolkien",      "Fantasy"),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO Book (Title, Author, Genre) VALUES (?,?,?)",
        placeholder_books
    )
    conn.commit()
    print("✓ Placeholder books inserted (add Books_df.csv for real data).")


# ── 3. Generate sample User records and their Lists ───────────────────────────

sample_users = [
    ("Christian Koeller", "christian@example.com"),
    ("Avery Rodriguez",   "avery@example.com"),
    ("Alexander Nino",    "alexander@example.com"),
    ("Tomas Caruso",      "tomas@example.com"),
]

start_range = datetime(2022, 1, 1)
end_range   = datetime(2024, 12, 31)

for name, email in sample_users:
    join = random_date(start_range, end_range)
    cur.execute(
        "INSERT OR IGNORE INTO User (Name, Email, JoinDate) VALUES (?,?,?)",
        (name, email, join)
    )
    # Create one List entry per user
    user_id = cur.lastrowid
    cur.execute(
        "INSERT OR IGNORE INTO List (UserID) VALUES (?)",
        (user_id,)
    )

conn.commit()
print(f"✓ {len(sample_users)} users inserted with lists.")


# ── 4. Sanity check ───────────────────────────────────────────────────────────

print("\n── Sanity check ──────────────────────────────────────────────────────")
for table in ["User", "Book", "List", "Read", "References_"]:
    n = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"  {table}: {n} rows")

print("\n── Users and their List IDs ─────────────────────────────────────────")
rows = cur.execute("""
    SELECT u.Name, u.Email, u.JoinDate, l.ListID
    FROM   User u
    JOIN   List l ON u.UserID = l.UserID
""").fetchall()
for row in rows:
    print(f"  {row[0]} ({row[1]}) — joined {row[2]} — ListID: {row[3]}")

conn.close()
print(f"\n✅ Done. Database saved to '{DB_PATH}'")
print("References_, Read tables are empty and ready for real user interactions.")