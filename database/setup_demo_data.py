"""
COP 4710 Term Project — Demo Data Setup Script
Run this once to populate Christian's account with realistic historical data.

Usage:
    python setup_demo_data.py

Make sure reading_list.db is in the same folder before running.
"""

import sqlite3
import random
from datetime import datetime, timedelta

DB_PATH = "reading_list.db"
USER_ID = 1

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn

def random_date(start, end):
    delta = end - start
    return (start + timedelta(days=random.randint(0, delta.days))).strftime("%Y-%m-%d")

conn = get_db()
cur  = conn.cursor()

# Get Christian's ListID
list_row = cur.execute(
    "SELECT ListID FROM List WHERE UserID = ?", (USER_ID,)
).fetchone()

if not list_row:
    print("User not found. Make sure USER_ID is correct.")
    conn.close()
    exit()

list_id = list_row["ListID"]

# Clear existing list entries for this user to start fresh
cur.execute("DELETE FROM References_ WHERE ListID = ?", (list_id,))
cur.execute("DELETE FROM Read WHERE UserID = ?", (USER_ID,))
conn.commit()
print("Cleared existing list entries.")

# ── Pick random books by ID ───────────────────────────────────────────────────
random_ids = random.sample(range(1, 5001), 20)
selected_books = []

for book_id in random_ids:
    book = cur.execute(
        "SELECT BookID, Title, Author, Genre FROM Book WHERE BookID = ?",
        (book_id,)
    ).fetchone()
    if book:
        selected_books.append(book)

print(f"Selected {len(selected_books)} books.")

# ── Define date ranges ────────────────────────────────────────────────────────
now        = datetime.now()
six_months = now - timedelta(days=180)
two_months = now - timedelta(days=60)
one_month  = now - timedelta(days=30)
two_weeks  = now - timedelta(days=14)

# ── Insert books with realistic dates ────────────────────────────────────────

# 8 finished books — spread over past 6 months
finished_books = selected_books[:8]
for book in finished_books:
    date_added  = random_date(six_months, two_months)
    da_dt       = datetime.strptime(date_added, "%Y-%m-%d")
    start_date  = random_date(da_dt, da_dt + timedelta(days=7))
    sd_dt       = datetime.strptime(start_date, "%Y-%m-%d")
    end_date    = random_date(sd_dt + timedelta(days=3), sd_dt + timedelta(days=45))

    cur.execute("""
        INSERT OR IGNORE INTO References_ (BookID, ListID, Status, DateAdded, StartDate, EndDate)
        VALUES (?, ?, 'finished', ?, ?, ?)
    """, (book["BookID"], list_id, date_added, start_date, end_date))

    cur.execute("""
        INSERT OR IGNORE INTO Read (UserID, BookID) VALUES (?, ?)
    """, (USER_ID, book["BookID"]))

    print(f"  [finished] {book['Title']} — added {date_added}, finished {end_date}")

# 4 currently reading books — 2 stalled (30+ days), 2 recent
stalled_books = selected_books[8:10]
for book in stalled_books:
    date_added = random_date(six_months, two_months)
    start_date = random_date(
        now - timedelta(days=90),
        now - timedelta(days=35)
    )

    cur.execute("""
        INSERT OR IGNORE INTO References_ (BookID, ListID, Status, DateAdded, StartDate, EndDate)
        VALUES (?, ?, 'currently reading', ?, ?, NULL)
    """, (book["BookID"], list_id, date_added, start_date))

    print(f"  [stalled]  {book['Title']} — started {start_date} (pace tracker flagged)")

recent_reading = selected_books[10:12]
for book in recent_reading:
    date_added = random_date(two_weeks, now)
    start_date = random_date(
        datetime.strptime(date_added, "%Y-%m-%d"),
        now
    )

    cur.execute("""
        INSERT OR IGNORE INTO References_ (BookID, ListID, Status, DateAdded, StartDate, EndDate)
        VALUES (?, ?, 'currently reading', ?, ?, NULL)
    """, (book["BookID"], list_id, date_added, start_date))

    print(f"  [reading]  {book['Title']} — started {start_date}")

# 4 want to read books
want_books = selected_books[12:16]
for book in want_books:
    date_added = random_date(two_weeks, now)

    cur.execute("""
        INSERT OR IGNORE INTO References_ (BookID, ListID, Status, DateAdded, StartDate, EndDate)
        VALUES (?, ?, 'want to read', ?, NULL, NULL)
    """, (book["BookID"], list_id, date_added))

    print(f"  [want]     {book['Title']} — added {date_added}")

conn.commit()

# ── Sanity check ──────────────────────────────────────────────────────────────
print("\n── Summary ───────────────────────────────────────────────────────────")
counts = cur.execute("""
    SELECT Status, COUNT(*) as count
    FROM References_
    WHERE ListID = ?
    GROUP BY Status
""", (list_id,)).fetchall()

for row in counts:
    print(f"  {row['Status']}: {row['count']} books")

avg = cur.execute("""
    SELECT ROUND(AVG(JULIANDAY(EndDate) - JULIANDAY(DateAdded)), 1) as avg_days
    FROM References_
    WHERE ListID = ? AND Status = 'finished' AND EndDate IS NOT NULL
""", (list_id,)).fetchone()

print(f"  Avg days to finish: {dict(avg)['avg_days']} days")

stalled = cur.execute("""
    SELECT COUNT(*) as count
    FROM References_
    WHERE ListID = ?
    AND Status = 'currently reading'
    AND StartDate IS NOT NULL
    AND JULIANDAY('now') - JULIANDAY(StartDate) > 30
""", (list_id,)).fetchone()

print(f"  Pace tracker flags: {dict(stalled)['count']} stalled books")

conn.close()
print("\n✅ Demo data setup complete. Refresh your dashboard to see the changes.")
