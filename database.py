import sqlite3
from datetime import date, timedelta

DB_PATH = "habits.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (date('now'))
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            goal_per_week INTEGER NOT NULL DEFAULT 7,
            created_at TEXT NOT NULL DEFAULT (date('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            completed INTEGER NOT NULL DEFAULT 1,
            UNIQUE(habit_id, date),
            FOREIGN KEY (habit_id) REFERENCES habits(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()


def add_habit(user_id, name, category, goal):
    if not name or not name.strip():
        return False, "Habit name cannot be empty."
    try:
        conn = get_conn()
        conn.execute(
            "INSERT INTO habits (user_id, name, category, goal_per_week) VALUES (?, ?, ?, ?)",
            (user_id, name.strip(), category, goal)
        )
        conn.commit()
        conn.close()
        return True, "Habit added successfully!"
    except Exception as e:
        return False, str(e)


def get_habits(user_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM habits WHERE user_id = ? ORDER BY created_at ASC",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_habit(habit_id):
    conn = get_conn()
    conn.execute("DELETE FROM checkins WHERE habit_id = ?", (habit_id,))
    conn.execute("DELETE FROM habits WHERE id = ?", (habit_id,))
    conn.commit()
    conn.close()


def update_habit(habit_id, name, category, goal):
    conn = get_conn()
    conn.execute(
        "UPDATE habits SET name = ?, category = ?, goal_per_week = ? WHERE id = ?",
        (name.strip(), category, goal, habit_id)
    )
    conn.commit()
    conn.close()


def toggle_checkin(habit_id, day=None):
    if day is None:
        day = str(date.today())
    conn = get_conn()
    existing = conn.execute(
        "SELECT id FROM checkins WHERE habit_id = ? AND date = ?",
        (habit_id, day)
    ).fetchone()
    if existing:
        conn.execute(
            "DELETE FROM checkins WHERE habit_id = ? AND date = ?",
            (habit_id, day)
        )
        conn.commit()
        conn.close()
        return False  # undone
    else:
        conn.execute(
            "INSERT OR IGNORE INTO checkins (habit_id, date, completed) VALUES (?, ?, 1)",
            (habit_id, day)
        )
        conn.commit()
        conn.close()
        return True  # done


def is_done_today(habit_id):
    today = str(date.today())
    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM checkins WHERE habit_id = ? AND date = ?",
        (habit_id, today)
    ).fetchone()
    conn.close()
    return row is not None


def get_all_checkins(user_id):
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT c.date, c.habit_id, h.name, h.category
        FROM checkins c
        JOIN habits h ON c.habit_id = h.id
        WHERE h.user_id = ?
        ORDER BY c.date ASC
        """,
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_checkins_for_habit(habit_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT date FROM checkins WHERE habit_id = ? ORDER BY date ASC",
        (habit_id,)
    ).fetchall()
    conn.close()
    return [r["date"] for r in rows]