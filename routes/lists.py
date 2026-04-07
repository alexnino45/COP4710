from datetime import date

from flask import Blueprint, jsonify, request

from database.db import get_db_connection

lists_bp = Blueprint("lists", __name__)
VALID_STATUSES = ["want to read", "currently reading", "finished"]


def get_list_id_for_user(conn, user_id: int):
    list_row = conn.execute("SELECT ListID FROM List WHERE UserID = ?", (user_id,)).fetchone()
    return list_row["ListID"] if list_row else None


@lists_bp.route("/users/<int:user_id>/list", methods=["GET"])
def get_user_list(user_id: int):
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT b.BookID, b.Title, b.Author, b.Genre,
               r.Status, r.DateAdded, r.StartDate, r.EndDate
        FROM List l
        JOIN References_ r ON l.ListID = r.ListID
        JOIN Book b ON r.BookID = b.BookID
        WHERE l.UserID = ?
        ORDER BY r.DateAdded DESC, b.Title ASC
        """,
        (user_id,),
    ).fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


@lists_bp.route("/users/<int:user_id>/list", methods=["POST"])
def add_book_to_list(user_id: int):
    data = request.get_json(silent=True) or {}
    book_id = data.get("book_id")
    if not book_id:
        return jsonify({"error": "book_id is required"}), 400

    conn = get_db_connection()
    list_id = get_list_id_for_user(conn, user_id)
    if not list_id:
        conn.close()
        return jsonify({"error": "User not found"}), 404

    try:
        conn.execute(
            """
            INSERT INTO References_ (BookID, ListID, Status, DateAdded)
            VALUES (?, ?, 'want to read', ?)
            """,
            (book_id, list_id, date.today().strftime("%Y-%m-%d")),
        )
        conn.commit()
    except Exception as exc:
        conn.rollback()
        conn.close()
        message = "Book is already on this list" if "UNIQUE constraint failed" in str(exc) else str(exc)
        return jsonify({"error": message}), 400

    conn.close()
    return jsonify({"message": "Book added to list"}), 201


@lists_bp.route("/users/<int:user_id>/list/<int:book_id>", methods=["PUT"])
def update_book_status(user_id: int, book_id: int):
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status not in VALID_STATUSES:
        return jsonify({"error": f"Status must be one of: {VALID_STATUSES}"}), 400

    conn = get_db_connection()
    list_id = get_list_id_for_user(conn, user_id)
    if not list_id:
        conn.close()
        return jsonify({"error": "User not found"}), 404

    today = date.today().strftime("%Y-%m-%d")

    if status == "currently reading":
        conn.execute(
            """
            UPDATE References_
            SET Status = ?, StartDate = COALESCE(StartDate, ?)
            WHERE BookID = ? AND ListID = ?
            """,
            (status, today, book_id, list_id),
        )
    elif status == "finished":
        conn.execute(
            """
            UPDATE References_
            SET Status = ?, EndDate = ?, StartDate = COALESCE(StartDate, ?)
            WHERE BookID = ? AND ListID = ?
            """,
            (status, today, today, book_id, list_id),
        )
        conn.execute(
            "INSERT OR IGNORE INTO Read (UserID, BookID) VALUES (?, ?)",
            (user_id, book_id),
        )
    else:
        conn.execute(
            "UPDATE References_ SET Status = ? WHERE BookID = ? AND ListID = ?",
            (status, book_id, list_id),
        )

    conn.commit()
    conn.close()
    return jsonify({"message": "Status updated"})


@lists_bp.route("/users/<int:user_id>/list/<int:book_id>", methods=["DELETE"])
def remove_book_from_list(user_id: int, book_id: int):
    conn = get_db_connection()
    list_id = get_list_id_for_user(conn, user_id)
    if not list_id:
        conn.close()
        return jsonify({"error": "User not found"}), 404

    conn.execute("DELETE FROM References_ WHERE BookID = ? AND ListID = ?", (book_id, list_id))
    conn.commit()
    conn.close()
    return jsonify({"message": "Book removed from list"})
