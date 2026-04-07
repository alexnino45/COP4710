from datetime import date

from flask import Blueprint, jsonify, request

from database.db import get_db_connection

users_bp = Blueprint("users", __name__)


@users_bp.route("/users", methods=["GET"])
def get_users():
    conn = get_db_connection()
    users = conn.execute("SELECT * FROM User ORDER BY UserID").fetchall()
    conn.close()
    return jsonify([dict(user) for user in users])


@users_bp.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id: int):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM User WHERE UserID = ?", (user_id,)).fetchone()
    conn.close()

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify(dict(user))


@users_bp.route("/users", methods=["POST"])
def create_user():
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()

    if not name or not email:
        return jsonify({"error": "Name and email are required"}), 400

    join_date = date.today().strftime("%Y-%m-%d")

    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO User (Name, Email, JoinDate) VALUES (?, ?, ?)",
            (name, email, join_date),
        )
        user_id = cursor.lastrowid
        conn.execute("INSERT INTO List (UserID) VALUES (?)", (user_id,))
        conn.commit()
    except Exception as exc:
        conn.rollback()
        message = "Email already exists" if "UNIQUE constraint failed" in str(exc) else str(exc)
        conn.close()
        return jsonify({"error": message}), 400

    conn.close()
    return jsonify({
        "message": "User created successfully",
        "user": {
            "UserID": user_id,
            "Name": name,
            "Email": email,
            "JoinDate": join_date,
        },
    }), 201
