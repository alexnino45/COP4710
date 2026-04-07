from flask import Blueprint, jsonify

from database.db import get_db_connection

stats_bp = Blueprint("stats", __name__)


@stats_bp.route("/users/<int:user_id>/stats", methods=["GET"])
def get_user_stats(user_id: int):
    conn = get_db_connection()

    status_counts = conn.execute(
        """
        SELECT r.Status, COUNT(*) AS count
        FROM List l
        JOIN References_ r ON l.ListID = r.ListID
        WHERE l.UserID = ?
        GROUP BY r.Status
        """,
        (user_id,),
    ).fetchall()

    genre_counts = conn.execute(
        """
        SELECT b.Genre, COUNT(*) AS count
        FROM List l
        JOIN References_ r ON l.ListID = r.ListID
        JOIN Book b ON r.BookID = b.BookID
        WHERE l.UserID = ? AND r.Status = 'finished'
        GROUP BY b.Genre
        ORDER BY count DESC
        """,
        (user_id,),
    ).fetchall()

    avg_days = conn.execute(
        """
        SELECT ROUND(AVG(JULIANDAY(r.EndDate) - JULIANDAY(r.StartDate)), 1) AS avg_days
        FROM List l
        JOIN References_ r ON l.ListID = r.ListID
        WHERE l.UserID = ?
          AND r.Status = 'finished'
          AND r.StartDate IS NOT NULL
          AND r.EndDate IS NOT NULL
        """,
        (user_id,),
    ).fetchone()

    slow_reads = conn.execute(
        """
        SELECT b.Title, b.Author,
               ROUND(JULIANDAY('now') - JULIANDAY(r.StartDate)) AS days_reading
        FROM List l
        JOIN References_ r ON l.ListID = r.ListID
        JOIN Book b ON r.BookID = b.BookID
        WHERE l.UserID = ?
          AND r.Status = 'currently reading'
          AND r.StartDate IS NOT NULL
          AND JULIANDAY('now') - JULIANDAY(r.StartDate) > 30
        ORDER BY days_reading DESC
        """,
        (user_id,),
    ).fetchall()

    conn.close()
    return jsonify({
        "status_counts": [dict(row) for row in status_counts],
        "genre_counts": [dict(row) for row in genre_counts],
        "avg_days_to_finish": dict(avg_days)["avg_days"] if avg_days else None,
        "slow_reads": [dict(row) for row in slow_reads],
    })
