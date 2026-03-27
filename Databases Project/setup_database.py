"""
COP 4710 Term Project — Database Setup Script
Run this once to create and populate the SQLite database.

Usage:
    pip install pandas
    python setup_database.py

Place your Kaggle books CSV (books.csv) in the same folder before running.
Download from: https://www.kaggle.com/datasets/jealousleopard/goodreadsbooks
"""

import sqlite3
import pandas as pd
import random
from datetime import datetime, timedelta

DB_PATH = "reading_list.db"
KAGGLE_CSV = "Books_df.csv"       # path to your downloaded Kaggle CSV

# ── Helpers ──────────────────────────────────────────────────────────────────

def random_date(start: datetime, end: datetime) -> str:
    delta = end - start
    return (start + timedelta(days=random.randint(0, delta.days))).strftime("%Y-%m-%d")


# ── 1. Connect and create schema ──────────────────────────────────────────────

conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()

cur.executescript("""
    PRAGMA foreign_keys = ON;

    CREATE TABLE IF NOT EXISTS User (
        UserID   INTEGER PRIMARY KEY AUTOINCREMENT,
        Name     TEXT    NOT NULL,
        Email    TEXT    NOT NULL UNIQUE,
        JoinDate TEXT    NOT NULL          -- stored as YYYY-MM-DD
    );

    CREATE TABLE IF NOT EXISTS Book (
        BookID  INTEGER PRIMARY KEY AUTOINCREMENT,
        Title   TEXT    NOT NULL,
        Author  TEXT,
        Genre   TEXT
    );

    -- A reading list belongs to one user
    CREATE TABLE IF NOT EXISTS List (
        ListID     INTEGER PRIMARY KEY AUTOINCREMENT,
        Status     TEXT    NOT NULL CHECK(Status IN ('want to read','currently reading','finished')),
        DateAdded  TEXT    NOT NULL,
        StartDate  TEXT,                   -- NULL until user starts the book
        EndDate    TEXT,                   -- NULL until user finishes the book
        UserID     INTEGER NOT NULL,
        FOREIGN KEY (UserID) REFERENCES User(UserID) ON DELETE CASCADE
    );

    -- Which books a user has read (many-to-many)
    CREATE TABLE IF NOT EXISTS Read (
        UserID  INTEGER NOT NULL,
        BookID  INTEGER NOT NULL,
        PRIMARY KEY (UserID, BookID),
        FOREIGN KEY (UserID) REFERENCES User(UserID) ON DELETE CASCADE,
        FOREIGN KEY (BookID) REFERENCES Book(BookID) ON DELETE CASCADE
    );

    -- Which books appear on which list entry (many-to-many)
    CREATE TABLE IF NOT EXISTS References_ (
        BookID  INTEGER NOT NULL,
        ListID  INTEGER NOT NULL,
        PRIMARY KEY (BookID, ListID),
        FOREIGN KEY (BookID) REFERENCES Book(BookID) ON DELETE CASCADE,
        FOREIGN KEY (ListID) REFERENCES List(ListID) ON DELETE CASCADE
    );
""")
# Note: SQLite reserves "References" as a keyword, so the table is named References_
# In your Flask queries just use References_ everywhere.

print("✓ Schema created.")


# ── 2. Load Kaggle books CSV into Book table ──────────────────────────────────

try:
    df = pd.read_csv(KAGGLE_CSV, on_bad_lines="skip", encoding="latin-1")
    print(f"  CSV loaded: {len(df)} rows, columns: {list(df.columns)}")
except FileNotFoundError:
    print(f"⚠ '{KAGGLE_CSV}' not found. Skipping book import — add the file and re-run.")
    df = pd.DataFrame()

if not df.empty:
    # ── Column mapping (GoodReads kaggle dataset column names) ──────────────
    # Adjust these if your CSV has different column names.
    col_map = {
        "Title":            "Title",
        "Author":          "Author",
        "Main Genre": "Genre",
    }
    # Genre isn't in every dataset; we'll map ratings shelf if present,
    # otherwise leave NULL.
    rename = {}
    for src, dst in col_map.items():
        matches = [c for c in df.columns if c.lower().strip() == src.lower()]
        if matches:
            rename[matches[0]] = dst

    df = df.rename(columns=rename)

    # Keep only what we need
    keep = [c for c in ["Title", "Author", "Genre"] if c in df.columns]
    df = df[keep].dropna(subset=["Title"])

    # Normalise Year to integer (may be float in CSV)
    if "Year" in df.columns:
        df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype("Int64")

    # Truncate to 5 000 books so the DB stays lightweight; remove limit if you want all
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
    # Seed a handful of placeholder books so the rest of the script still works
    placeholder_books = [
        ("The Great Gatsby",          "F. Scott Fitzgerald", "Fiction",    1925),
        ("To Kill a Mockingbird",     "Harper Lee",          "Fiction",    1960),
        ("1984",                      "George Orwell",       "Dystopian",  1949),
        ("Dune",                      "Frank Herbert",       "Sci-Fi",     1965),
        ("The Hobbit",                "J.R.R. Tolkien",      "Fantasy",    1937),
        ("Harry Potter and the Sorcerer's Stone", "J.K. Rowling", "Fantasy", 1997),
        ("The Catcher in the Rye",    "J.D. Salinger",       "Fiction",    1951),
        ("Brave New World",           "Aldous Huxley",       "Dystopian",  1932),
        ("The Hitchhiker's Guide",    "Douglas Adams",       "Sci-Fi",     1979),
        ("Gone Girl",                 "Gillian Flynn",       "Thriller",   2012),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO Book (Title, Author, Genre, Year) VALUES (?,?,?,?)",
        placeholder_books
    )
    conn.commit()
    print("✓ Placeholder books inserted (add books.csv for real data).")


# ── 3. Generate sample User records ──────────────────────────────────────────

sample_users = [
    ("Christian Koeller",  "Christian@example.com"),
    ("Avery Rodriguez",      "Avery@example.com"),
    ("Alexander Nino",    "Alexander@example.com"),
    ("Tomas Caruso",    "Tomas@example.com"),
]

start_range = datetime(2022, 1, 1)
end_range   = datetime(2024, 12, 31)

for name, email in sample_users:
    join = random_date(start_range, end_range)
    cur.execute(
        "INSERT OR IGNORE INTO User (Name, Email, JoinDate) VALUES (?,?,?)",
        (name, email, join)
    )

conn.commit()
print(f"✓ {len(sample_users)} users inserted.")


# ── 4. Generate List + References_ + Read entries ────────────────────────────

user_ids = [r[0] for r in cur.execute("SELECT UserID FROM User").fetchall()]
book_ids = [r[0] for r in cur.execute("SELECT BookID FROM Book").fetchall()]

statuses       = ["want to read", "currently reading", "finished"]
status_weights = [0.3, 0.2, 0.5]   # most books are "finished" in sample data

list_rows       = []
references_rows = []
read_rows       = set()

for uid in user_ids:
    # Each user gets between 5 and 15 list entries
    n_books = random.randint(5, 15)
    chosen  = random.sample(book_ids, min(n_books, len(book_ids)))

    join_date = cur.execute(
        "SELECT JoinDate FROM User WHERE UserID=?", (uid,)
    ).fetchone()[0]
    join_dt = datetime.strptime(join_date, "%Y-%m-%d")

    for bid in chosen:
        status    = random.choices(statuses, weights=status_weights)[0]
        date_added = random_date(join_dt, datetime.now())
        da_dt      = datetime.strptime(date_added, "%Y-%m-%d")

        if status == "want to read":
            start_date = None
            end_date   = None
        elif status == "currently reading":
            start_date = random_date(da_dt, datetime.now())
            end_date   = None
        else:  # finished
            start_date = random_date(da_dt, datetime.now())
            sd_dt      = datetime.strptime(start_date, "%Y-%m-%d")
            end_date   = random_date(sd_dt, datetime.now())
            read_rows.add((uid, bid))   # track in Read table too

        cur.execute(
            """INSERT INTO List (Status, DateAdded, StartDate, EndDate, UserID)
               VALUES (?,?,?,?,?)""",
            (status, date_added, start_date, end_date, uid)
        )
        list_id = cur.lastrowid
        references_rows.append((bid, list_id))

cur.executemany(
    "INSERT OR IGNORE INTO References_ (BookID, ListID) VALUES (?,?)",
    references_rows
)
cur.executemany(
    "INSERT OR IGNORE INTO Read (UserID, BookID) VALUES (?,?)",
    list(read_rows)
)
conn.commit()

list_count = cur.execute("SELECT COUNT(*) FROM List").fetchone()[0]
ref_count  = cur.execute("SELECT COUNT(*) FROM References_").fetchone()[0]
read_count = cur.execute("SELECT COUNT(*) FROM Read").fetchone()[0]
print(f"✓ {list_count} List rows, {ref_count} References_ rows, {read_count} Read rows inserted.")


# ── 5. Quick sanity check ─────────────────────────────────────────────────────

print("\n── Sanity check ──────────────────────────────────────────────────────")
for table in ["User", "Book", "List", "Read", "References_"]:
    n = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"  {table}: {n} rows")

# Sample join query matching your project requirements
print("\n── Sample join: books on Alice's list ──────────────────────────────")
rows = cur.execute("""
    SELECT b.Title, b.Author, l.Status
    FROM   User u
    JOIN   List l        ON u.UserID  = l.UserID
    JOIN   References_ r ON l.ListID  = r.ListID
    JOIN   Book b        ON r.BookID  = b.BookID
    WHERE  u.Name = 'Alice Johnson'
    LIMIT  5
""").fetchall()
for row in rows:
    print(f"  {row[0]} by {row[1]} — [{row[2]}]")

# Sample aggregate query
print("\n── Sample aggregate: finished books per user ────────────────────────")
rows = cur.execute("""
    SELECT u.Name, COUNT(*) AS finished_count
    FROM   User u
    JOIN   List l ON u.UserID = l.UserID
    WHERE  l.Status = 'finished'
    GROUP  BY u.UserID
    ORDER  BY finished_count DESC
""").fetchall()
for row in rows:
    print(f"  {row[0]}: {row[1]} books finished")

conn.close()
print(f"\n✅ Done. Database saved to '{DB_PATH}'")