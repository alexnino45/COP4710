from flask import Blueprint, jsonify, request

from database.db import get_db_connection

books_bp = Blueprint("books", __name__)


@books_bp.route("/books/search", methods=["GET"])
def search_books():
    title = request.args.get("title", "").strip()
    author = request.args.get("author", "").strip()
    genre = request.args.get("genre", "").strip()

    query = "SELECT * FROM Book WHERE 1=1"
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

    query += " ORDER BY Title LIMIT 50"

    conn = get_db_connection()
    books = conn.execute(query, params).fetchall()
    conn.close()
    return jsonify([dict(book) for book in books])


@books_bp.route("/books/<int:book_id>", methods=["GET"])
def get_book(book_id: int):
    conn = get_db_connection()
    book = conn.execute("SELECT * FROM Book WHERE BookID = ?", (book_id,)).fetchone()
    conn.close()

    if not book:
        return jsonify({"error": "Book not found"}), 404

    return jsonify(dict(book))
