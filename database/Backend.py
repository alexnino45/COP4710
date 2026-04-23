"""
COP 4710 Term Project — Flask Backend
Run with: python Backend.py
Then open http://127.0.0.1:5000 in your browser.
"""

from flask import Flask, request, jsonify, session, render_template, redirect
import sqlite3
from datetime import date

app = Flask(__name__)
app.secret_key = "cop4710-dev-key"
DB_PATH = "reading_list.db"


# ── Database connection helper ────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row  # lets you access columns by name
    return conn


# ── Home (page) route ────────────────────────────────────────────────────────────────

@app.route("/")
def home():
    return render_template("index.html")

# ── Login (page) route ───────────────────────────────────────────────────────────────

@app.route("/login-page")
def login_page():
    return render_template("login.html")

# ── List route ────────────────────────────────────────────────────────────────

@app.route("/dashboard")
def dashboard():
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login-page")

    conn = get_db()

    user = conn.execute(
        "SELECT * FROM User WHERE UserID = ?", (user_id,)
    ).fetchone()

    reading_list = conn.execute("""
        SELECT b.BookID, b.Title, b.Author, b.Genre,
               r.Status, r.DateAdded, r.StartDate, r.EndDate
        FROM   List l
        JOIN   References_ r ON l.ListID = r.ListID
        JOIN   Book b        ON r.BookID = b.BookID
        WHERE  l.UserID = ?
        ORDER  BY r.DateAdded DESC
    """, (user_id,)).fetchall()

    status_counts = conn.execute("""
        SELECT r.Status, COUNT(*) as count
        FROM   List l
        JOIN   References_ r ON l.ListID = r.ListID
        WHERE  l.UserID = ?
        GROUP  BY r.Status
    """, (user_id,)).fetchall()

    genre_counts = conn.execute("""
        SELECT b.Genre, COUNT(*) as count
        FROM   List l
        JOIN   References_ r ON l.ListID  = r.ListID
        JOIN   Book b        ON r.BookID  = b.BookID
        WHERE  l.UserID = ?
        GROUP  BY b.Genre
        ORDER  BY count DESC
    """, (user_id,)).fetchall()

    avg_days = conn.execute("""
        SELECT ROUND(AVG(
            JULIANDAY(r.EndDate) - JULIANDAY(r.DateAdded)
        ), 1) as avg_days
        FROM   List l
        JOIN   References_ r ON l.ListID = r.ListID
        WHERE  l.UserID = ?
        AND    r.Status = 'finished'
        AND    r.EndDate   IS NOT NULL
    """, (user_id,)).fetchone()

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

    status_dict = {row["Status"]: row["count"] for row in status_counts}
    total_finished = max(status_dict.get("finished", 1), 1)
    genres = [
        {
            "name":  row["Genre"],
            "count": row["count"],
            "pct":   round(row["count"] / total_finished * 100)
        }
        for row in genre_counts
    ]

    stats = {
        "want_to_read":      status_dict.get("want to read", 0),
        "currently_reading": status_dict.get("currently reading", 0),
        "finished":          status_dict.get("finished", 0),
        "avg_days":          float(dict(avg_days)["avg_days"]) if avg_days and dict(avg_days)["avg_days"] else 0.0,
        "genres":            genres
    }

    status_class_map = {
        "want to read":      "want",
        "currently reading": "reading",
        "finished":          "done"
    }
    books = [
        {
            "BookID":       row["BookID"],
            "title":        row["Title"],
            "author":       row["Author"],
            "genre":        row["Genre"],
            "status":       row["Status"],
            "status_class": status_class_map.get(row["Status"], "want"),
            "date_added":   row["DateAdded"],
            "start_date":   row["StartDate"],
            "end_date":     row["EndDate"]
        }
        for row in reading_list
    ]

    pace_alerts = [
        {
            "title": row["Title"],
            "days":  int(row["days_reading"])
        }
        for row in slow_reads
    ]

    return render_template(
        "user.html",
        user=dict(user),
        reading_list=books,
        stats=stats,
        pace_alerts=pace_alerts
    )

# ── Logout route ───────────────────────────────────────────────────────────────

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login-page")

# ── Profile route ──────────────────────────────────────────────────────────────

@app.route("/profile")
def profile():
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login-page")
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM User WHERE UserID = ?", (user_id,)
    ).fetchone()
    conn.close()
    return render_template("profile.html", user=dict(user))

# ── Change Password route ───────────────────────────────────────────────────────

@app.route("/users/<int:user_id>/password", methods=["PUT"])
def change_password(user_id):
    data             = request.get_json()
    current_password = data.get("current_password")
    new_password     = data.get("new_password")

    conn = get_db()
    user = conn.execute(
        "SELECT * FROM User WHERE UserID = ? AND Password = ?",
        (user_id, current_password)
    ).fetchone()

    if not user:
        conn.close()
        return jsonify({"error": "Current password is incorrect"}), 401

    conn.execute(
        "UPDATE User SET Password = ? WHERE UserID = ?",
        (new_password, user_id)
    )
    conn.commit()
    conn.close()

    return jsonify({"message": "Password updated successfully"}), 200

# ── Delete User route ───────────────────────────────────────────────────────────────────────────

@app.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    conn = get_db()

    user = conn.execute(
        "SELECT * FROM User WHERE UserID = ?", (user_id,)
    ).fetchone()

    if not user:
        conn.close()
        return jsonify({"error": "User not found"}), 404

    conn.execute("DELETE FROM User WHERE UserID = ?", (user_id,))
    conn.commit()
    conn.close()

    session.clear()
    return jsonify({"message": "Account deleted successfully"}), 200

# ── Book Search route ───────────────────────────────────────────────────────────────────────────

@app.route("/books/search", methods=["GET"])
def search_books():
    title  = request.args.get("title",  "")
    author = request.args.get("author", "")
    genre  = request.args.get("genre",  "")
    q      = request.args.get("q",      "")

    params = []

    if q:
        query = """SELECT * FROM Book WHERE 
                   Title LIKE ? OR Author LIKE ? OR Genre LIKE ?
                   LIMIT 50"""
        params = [f"%{q}%", f"%{q}%", f"%{q}%"]
    else:
        query  = "SELECT * FROM Book WHERE 1=1"
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

# ── Get book (by ID) route ──────────────────────────────────────────────────────────────────────

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

# ── Login (user action) route ──────────────────────────────────────────────────────────────────────────────────────

@app.route("/login", methods=["POST"])
def login():
    data     = request.get_json()
    email    = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    conn = get_db()
    user = conn.execute(
        "SELECT * FROM User WHERE Email = ? AND Password = ?",
        (email, password)
    ).fetchone()
    conn.close()

    if not user:
        return jsonify({"error": "Invalid email or password"}), 401

    session["user_id"] = user["UserID"]
    session["user_name"] = user["Name"]
    return jsonify({
        "message":  "Login successful",
        "UserID":   user["UserID"],
        "Name":     user["Name"],
        "Email":    user["Email"],
        "JoinDate": user["JoinDate"]
    }), 200

# ── Create New User route ────────────────────────────────────────────────────────────────────────────

@app.route("/register", methods=["POST"])
def register():
    data     = request.get_json()
    first_name = data.get("first_name")
    last_name  = data.get("last_name")
    name     = f"{first_name} {last_name}"
    email    = data.get("email")
    password = data.get("password")

    if not name or not email or not password:
        return jsonify({"error": "Name, email, and password are required"}), 400

    join_date = date.today().strftime("%Y-%m-%d")

    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO User (Name, Email, Password, JoinDate) VALUES (?,?,?,?)",
            (name, email, password, join_date)
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

    return jsonify({
        "message": "Account created successfully",
        "UserID":  user_id
    }), 201

# ══════════════════════════════════════════════════════════════════════════════
# LIST ROUTES (CRUD)
# ══════════════════════════════════════════════════════════════════════════════

# ── Get User List route ──────────────────────────────────────────────────────────────────────────

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

# ── Add Book to User List route ────────────────────────────────────────────────────────────

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

# ── Update Book Status route ──────────────────────────────────────────────────────────────

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
        # Preserve StartDate if it exists, otherwise set it to today
        existing = conn.execute("""
            SELECT StartDate FROM References_
            WHERE BookID = ? AND ListID = ?
        """, (book_id, list_id)).fetchone()

        start = existing["StartDate"] if existing and existing["StartDate"] else today

        conn.execute("""
            UPDATE References_
            SET    Status = ?, EndDate = ?, StartDate = ?
            WHERE  BookID = ? AND ListID = ?
        """, (status, today, start, book_id, list_id))

        conn.execute("""
            INSERT OR IGNORE INTO Read (UserID, BookID) VALUES (?,?)
        """, (user_id, book_id))

    else:
        conn.execute("""
            UPDATE References_
            SET    Status = ?, StartDate = NULL, EndDate = NULL
            WHERE  BookID = ? AND ListID = ?
        """, (status, book_id, list_id))

    conn.commit()
    conn.close()

    return jsonify({"message": "Status updated"})

# ── Delete Book from List route ──────────────────────────────────────────────────────────────────────

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

@app.route("/stats")
def stats():
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login-page")

    conn = get_db()

    user = conn.execute(
        "SELECT * FROM User WHERE UserID = ?", (user_id,)
    ).fetchone()

    status_counts = conn.execute("""
        SELECT r.Status, COUNT(*) as count
        FROM   List l
        JOIN   References_ r ON l.ListID = r.ListID
        WHERE  l.UserID = ?
        GROUP  BY r.Status
    """, (user_id,)).fetchall()

    genre_counts = conn.execute("""
        SELECT b.Genre, COUNT(*) as count
        FROM   List l
        JOIN   References_ r ON l.ListID  = r.ListID
        JOIN   Book b        ON r.BookID  = b.BookID
        WHERE  l.UserID = ?
        GROUP  BY b.Genre
        ORDER  BY count DESC
    """, (user_id,)).fetchall()

    avg_days = conn.execute("""
        SELECT ROUND(AVG(
            JULIANDAY(r.EndDate) - JULIANDAY(r.DateAdded)
        ), 1) as avg_days
        FROM   List l
        JOIN   References_ r ON l.ListID = r.ListID
        WHERE  l.UserID = ?
        AND    r.Status = 'finished'
        AND    r.EndDate IS NOT NULL
    """, (user_id,)).fetchone()

    avg_days_by_genre = conn.execute("""
        SELECT b.Genre,
               ROUND(AVG(
                   JULIANDAY(r.EndDate) - JULIANDAY(r.DateAdded)
               ), 1) as avg_days
        FROM   List l
        JOIN   References_ r ON l.ListID = r.ListID
        JOIN   Book b        ON r.BookID = b.BookID
        WHERE  l.UserID = ?
        AND    r.Status = 'finished'
        AND    r.EndDate IS NOT NULL
        GROUP  BY b.Genre
        ORDER  BY avg_days ASC
    """, (user_id,)).fetchall()

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

    status_dict = {row["Status"]: row["count"] for row in status_counts}
    total = max(sum(status_dict.values()), 1)
    genres = [
        {
            "name":  row["Genre"],
            "count": row["count"],
            "pct":   round(row["count"] / total * 100)
        }
        for row in genre_counts
    ]

    stats = {
        "want_to_read":      status_dict.get("want to read", 0),
        "currently_reading": status_dict.get("currently reading", 0),
        "finished":          status_dict.get("finished", 0),
        "avg_days":          float(dict(avg_days)["avg_days"]) if avg_days and dict(avg_days)["avg_days"] else 0.0,
        "genres":            genres,
        "avg_days_by_genre": [dict(row) for row in avg_days_by_genre]
    }

    pace_alerts = [
        {
            "title":  row["Title"],
            "author": row["Author"],
            "days":   int(row["days_reading"])
        }
        for row in slow_reads
    ]

    return render_template(
        "stats.html",
        user=dict(user),
        stats=stats,
        pace_alerts=pace_alerts
    )

# ── Run the app ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True)
    