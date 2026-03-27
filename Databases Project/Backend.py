"""
COP 4710 Term Project — Flask Backend
Run with: python app.py
Then open http://127.0.0.1:5000 in your browser.
"""

from flask import Flask, request, jsonify
import sqlite3
from datetime import date

app = Flask(__name__)
DB_PATH = "reading_list.db"


# ── Database connection helper ────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row  # lets you access columns by name
    return conn


# ── Home route ────────────────────────────────────────────────────────────────

@app.route("/")
def home():
    return "Reading List App is running!"


# ══════════════════════════════════════════════════════════════════════════════
# BOOK ROUTES
# ══════════════════════════════════════════════════════════════════════════════

# Search books by title, author, or genre
# Example: /books/search?title=dune
#          /books/search?author=tolkien
#          /books/search?genre=Fantasy
@app.route("/books/search", methods=["GET"])
def search_books():
    title  = request.args.get("title",  "")
    author = request.args.get("author", "")
    genre  = request.args.get("genre",  "")

    query  = "SELECT * FROM Book WHERE 1=1"
    params = []

    if title:
        query += " AND Title LIKE ?"
        params.append(f"%{title}%")
    if author:
        query += " AND Author LIKE ?"
        params.append(f"%{author}%")
    if genre:
        query += " AND Genre LIKE ?"
        params.append(f"%{genre}%")

    query += " LIMIT 50"

    conn = get_db()
    books = conn.execute(query, params).fetchall()
    conn.close()

    return jsonify([dict(book) for book in books])


# Get a single book by ID
# Example: /books/1
@app.route("/books/<int:book_id>", methods=["GET"])
def get_book(book_id):
    conn = get_db()
    book = conn.execute(
        "SELECT * FROM Book WHERE BookID = ?", (book_id,)
    ).fetchone()
    conn.close()

    if not book:
        return jsonify({"error": "Book not found"}), 404

    return jsonify(dict(book))


# ══════════════════════════════════════════════════════════════════════════════
# USER ROUTES
# ══════════════════════════════════════════════════════════════════════════════

# Get all users
# Example: /users
@app.route("/users", methods=["GET"])
def get_users():
    conn = get_db()
    users = conn.execute("SELECT * FROM User").fetchall()
    conn.close()
    return jsonify([dict(u) for u in users])


# Get a single user by ID
# Example: /users/1
@app.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM User WHERE UserID = ?", (user_id,)
    ).fetchone()
    conn.close()

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify(dict(user))


# Create a new user
# POST /users
# Body: { "name": "John Doe", "email": "john@example.com" }
@app.route("/users", methods=["POST"])
def create_user():
    data  = request.get_json()
    name  = data.get("name")
    email = data.get("email")

    if not name or not email:
        return jsonify({"error": "Name and email are required"}), 400

    join_date = date.today().strftime("%Y-%m-%d")

    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO User (Name, Email, JoinDate) VALUES (?,?,?)",
            (name, email, join_date)
        )
        user_id = cur.lastrowid

        # Automatically create a list for the new user
        conn.execute(
            "INSERT INTO List (UserID) VALUES (?)",
            (user_id,)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "Email already exists"}), 400
    finally:
        conn.close()

    return jsonify({"message": "User created", "UserID": user_id}), 201


# ══════════════════════════════════════════════════════════════════════════════
# LIST ROUTES (CRUD)
# ══════════════════════════════════════════════════════════════════════════════

# READ — Get all books on a user's list
# Example: /users/1/list
@app.route("/users/<int:user_id>/list", methods=["GET"])
def get_user_list(user_id):
    conn = get_db()
    rows = conn.execute("""
        SELECT b.BookID, b.Title, b.Author, b.Genre,
               r.Status, r.DateAdded, r.StartDate, r.EndDate
        FROM   User u
        JOIN   List l        ON u.UserID = l.UserID
        JOIN   References_ r ON l.ListID = r.ListID
        JOIN   Book b        ON r.BookID = b.BookID
        WHERE  u.UserID = ?
        ORDER  BY r.DateAdded DESC
    """, (user_id,)).fetchall()
    conn.close()

    return jsonify([dict(row) for row in rows])


# CREATE — Add a book to a user's list
# POST /users/1/list
# Body: { "book_id": 42 }
@app.route("/users/<int:user_id>/list", methods=["POST"])
def add_book_to_list(user_id):
    data    = request.get_json()
    book_id = data.get("book_id")

    if not book_id:
        return jsonify({"error": "book_id is required"}), 400

    date_added = date.today().strftime("%Y-%m-%d")

    conn = get_db()

    # Get this user's ListID
    list_row = conn.execute(
        "SELECT ListID FROM List WHERE UserID = ?", (user_id,)
    ).fetchone()

    if not list_row:
        return jsonify({"error": "User not found"}), 404

    list_id = list_row["ListID"]

    try:
        conn.execute("""
            INSERT INTO References_ (BookID, ListID, Status, DateAdded)
            VALUES (?, ?, 'want to read', ?)
        """, (book_id, list_id, date_added))
        conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "Book is already on this list"}), 400
    finally:
        conn.close()

    return jsonify({"message": "Book added to list"}), 201


# UPDATE — Update the status of a book on a user's list
# PUT /users/1/list/42
# Body: { "status": "currently reading" }
#    or { "status": "finished" }
@app.route("/users/<int:user_id>/list/<int:book_id>", methods=["PUT"])
def update_book_status(user_id, book_id):
    data   = request.get_json()
    status = data.get("status")

    valid_statuses = ["want to read", "currently reading", "finished"]
    if status not in valid_statuses:
        return jsonify({"error": f"Status must be one of: {valid_statuses}"}), 400

    today = date.today().strftime("%Y-%m-%d")

    conn = get_db()

    list_row = conn.execute(
        "SELECT ListID FROM List WHERE UserID = ?", (user_id,)
    ).fetchone()

    if not list_row:
        return jsonify({"error": "User not found"}), 404

    list_id = list_row["ListID"]

    # Automatically set StartDate and EndDate based on status
    if status == "currently reading":
        conn.execute("""
            UPDATE References_
            SET    Status = ?, StartDate = ?
            WHERE  BookID = ? AND ListID = ?
        """, (status, today, book_id, list_id))

    elif status == "finished":
        conn.execute("""
            UPDATE References_
            SET    Status = ?, EndDate = ?
            WHERE  BookID = ? AND ListID = ?
        """, (status, today, book_id, list_id))

        # Add to Read table when finished
        conn.execute("""
            INSERT OR IGNORE INTO Read (UserID, BookID) VALUES (?,?)
        """, (user_id, book_id))

    else:
        conn.execute("""
            UPDATE References_
            SET    Status = ?
            WHERE  BookID = ? AND ListID = ?
        """, (status, book_id, list_id))

    conn.commit()
    conn.close()

    return jsonify({"message": "Status updated"})


# DELETE — Remove a book from a user's list
# DELETE /users/1/list/42
@app.route("/users/<int:user_id>/list/<int:book_id>", methods=["DELETE"])
def remove_book_from_list(user_id, book_id):
    conn = get_db()

    list_row = conn.execute(
        "SELECT ListID FROM List WHERE UserID = ?", (user_id,)
    ).fetchone()

    if not list_row:
        return jsonify({"error": "User not found"}), 404

    list_id = list_row["ListID"]

    conn.execute("""
        DELETE FROM References_
        WHERE BookID = ? AND ListID = ?
    """, (book_id, list_id))
    conn.commit()
    conn.close()

    return jsonify({"message": "Book removed from list"})


# ══════════════════════════════════════════════════════════════════════════════
# STATISTICS ROUTES (Advanced feature — pace tracker)
# ══════════════════════════════════════════════════════════════════════════════

# Get reading statistics for a user
# Example: /users/1/stats
@app.route("/users/<int:user_id>/stats", methods=["GET"])
def get_user_stats(user_id):
    conn = get_db()

    # Total books by status
    status_counts = conn.execute("""
        SELECT r.Status, COUNT(*) as count
        FROM   List l
        JOIN   References_ r ON l.ListID = r.ListID
        WHERE  l.UserID = ?
        GROUP  BY r.Status
    """, (user_id,)).fetchall()

    # Total books finished per genre
    genre_counts = conn.execute("""
        SELECT b.Genre, COUNT(*) as count
        FROM   List l
        JOIN   References_ r ON l.ListID  = r.ListID
        JOIN   Book b        ON r.BookID  = b.BookID
        WHERE  l.UserID = ? AND r.Status = 'finished'
        GROUP  BY b.Genre
        ORDER  BY count DESC
    """, (user_id,)).fetchall()

    # Average days to finish a book
    avg_days = conn.execute("""
        SELECT ROUND(AVG(
            JULIANDAY(r.EndDate) - JULIANDAY(r.StartDate)
        ), 1) as avg_days
        FROM   List l
        JOIN   References_ r ON l.ListID = r.ListID
        WHERE  l.UserID = ?
        AND    r.Status = 'finished'
        AND    r.StartDate IS NOT NULL
        AND    r.EndDate   IS NOT NULL
    """, (user_id,)).fetchone()

    # Books currently reading for unusually long (pace tracker)
    slow_reads = conn.execute("""
        SELECT b.Title, b.Author,
               ROUND(JULIANDAY('now') - JULIANDAY(r.StartDate)) as days_reading
        FROM   List l
        JOIN   References_ r ON l.ListID = r.ListID
        JOIN   Book b        ON r.BookID = b.BookID
        WHERE  l.UserID = ?
        AND    r.Status = 'currently reading'
        AND    r.StartDate IS NOT NULL
        AND    JULIANDAY('now') - JULIANDAY(r.StartDate) > 30
        ORDER  BY days_reading DESC
    """, (user_id,)).fetchall()

    conn.close()

    return jsonify({
        "status_counts":  [dict(row) for row in status_counts],
        "genre_counts":   [dict(row) for row in genre_counts],
        "avg_days_to_finish": dict(avg_days)["avg_days"] if avg_days else None,
        "slow_reads":     [dict(row) for row in slow_reads]
    })


# ── Run the app ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True)
    