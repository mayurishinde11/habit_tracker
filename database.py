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
    cur  = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT NOT NULL UNIQUE,
            email         TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at    TEXT NOT NULL DEFAULT (date('now'))
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS habits (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL,
            name         TEXT    NOT NULL,
            category     TEXT    NOT NULL,
            goal_per_week INTEGER NOT NULL DEFAULT 7,
            created_at   TEXT    NOT NULL DEFAULT (date('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS checkins (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id   INTEGER NOT NULL,
            date       TEXT    NOT NULL,
            completed  INTEGER NOT NULL DEFAULT 1,
            UNIQUE(habit_id, date),
            FOREIGN KEY (habit_id) REFERENCES habits(id) ON DELETE CASCADE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS steps (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            date       TEXT    NOT NULL,
            steps      INTEGER NOT NULL DEFAULT 0,
            goal       INTEGER NOT NULL DEFAULT 10000,
            note       TEXT    DEFAULT '',
            created_at TEXT    NOT NULL DEFAULT (datetime('now')),
            UNIQUE(user_id, date),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # ── Water table ───────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS water (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            date       TEXT    NOT NULL,
            glasses    REAL    NOT NULL DEFAULT 0,
            goal       REAL    NOT NULL DEFAULT 8,
            unit       TEXT    NOT NULL DEFAULT 'glasses',
            note       TEXT    DEFAULT '',
            created_at TEXT    NOT NULL DEFAULT (datetime('now')),
            UNIQUE(user_id, date),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # ── Sleep table ───────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sleep (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            date        TEXT    NOT NULL,
            bedtime     TEXT    NOT NULL,
            wake_time   TEXT    NOT NULL,
            hours_slept REAL    NOT NULL DEFAULT 0,
            quality     INTEGER NOT NULL DEFAULT 3,
            note        TEXT    DEFAULT '',
            created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
            UNIQUE(user_id, date),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # ── Weight table ──────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS weight (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            date       TEXT    NOT NULL,
            weight_kg  REAL    NOT NULL,
            goal_kg    REAL    DEFAULT NULL,
            unit       TEXT    NOT NULL DEFAULT 'kg',
            note       TEXT    DEFAULT '',
            created_at TEXT    NOT NULL DEFAULT (datetime('now')),
            UNIQUE(user_id, date),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()


# ── Habit functions ───────────────────────────────────────────────────────────

def add_habit(user_id, name, category, goal):
    if not name or not name.strip():
        return False, "Habit name cannot be empty."
    try:
        conn = get_conn()
        conn.execute(
            "INSERT INTO habits (user_id, name, category, goal_per_week) VALUES (?, ?, ?, ?)",
            (user_id, name.strip(), category, goal)
        )
        conn.commit(); conn.close()
        return True, "Habit added successfully!"
    except Exception as e:
        return False, str(e)

def get_habits(user_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM habits WHERE user_id = ? ORDER BY created_at ASC", (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_habit(habit_id):
    conn = get_conn()
    conn.execute("DELETE FROM checkins WHERE habit_id = ?", (habit_id,))
    conn.execute("DELETE FROM habits WHERE id = ?", (habit_id,))
    conn.commit(); conn.close()

def update_habit(habit_id, name, category, goal):
    conn = get_conn()
    conn.execute(
        "UPDATE habits SET name=?, category=?, goal_per_week=? WHERE id=?",
        (name.strip(), category, goal, habit_id)
    )
    conn.commit(); conn.close()

def toggle_checkin(habit_id, day=None):
    if day is None:
        day = str(date.today())
    conn     = get_conn()
    existing = conn.execute(
        "SELECT id FROM checkins WHERE habit_id=? AND date=?", (habit_id, day)
    ).fetchone()
    if existing:
        conn.execute("DELETE FROM checkins WHERE habit_id=? AND date=?", (habit_id, day))
        conn.commit(); conn.close(); return False
    else:
        conn.execute(
            "INSERT OR IGNORE INTO checkins (habit_id, date, completed) VALUES (?,?,1)",
            (habit_id, day)
        )
        conn.commit(); conn.close(); return True

def is_done_today(habit_id):
    conn = get_conn()
    row  = conn.execute(
        "SELECT id FROM checkins WHERE habit_id=? AND date=?",
        (habit_id, str(date.today()))
    ).fetchone()
    conn.close()
    return row is not None

def get_all_checkins(user_id):
    conn = get_conn()
    rows = conn.execute(
        """SELECT c.date, c.habit_id, h.name, h.category
           FROM checkins c JOIN habits h ON c.habit_id = h.id
           WHERE h.user_id = ? ORDER BY c.date ASC""",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_checkins_for_habit(habit_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT date FROM checkins WHERE habit_id=? ORDER BY date ASC", (habit_id,)
    ).fetchall()
    conn.close()
    return [r["date"] for r in rows]


# ── Steps functions ───────────────────────────────────────────────────────────

def log_steps(user_id, steps, goal=10000, log_date=None, note=""):
    if log_date is None:
        log_date = str(date.today())
    conn = get_conn()
    conn.execute(
        """INSERT INTO steps (user_id, date, steps, goal, note) VALUES (?,?,?,?,?)
           ON CONFLICT(user_id, date)
           DO UPDATE SET steps=excluded.steps, goal=excluded.goal, note=excluded.note""",
        (user_id, log_date, steps, goal, note)
    )
    conn.commit(); conn.close()

def get_steps_today(user_id):
    conn = get_conn()
    row  = conn.execute(
        "SELECT * FROM steps WHERE user_id=? AND date=?",
        (user_id, str(date.today()))
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def get_steps_history(user_id, days=30):
    since = str(date.today() - timedelta(days=days - 1))
    conn  = get_conn()
    rows  = conn.execute(
        "SELECT * FROM steps WHERE user_id=? AND date>=? ORDER BY date ASC",
        (user_id, since)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_steps_all(user_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM steps WHERE user_id=? ORDER BY date ASC", (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_steps_entry(user_id, entry_date):
    conn = get_conn()
    conn.execute("DELETE FROM steps WHERE user_id=? AND date=?", (user_id, entry_date))
    conn.commit(); conn.close()


# ── Water functions ───────────────────────────────────────────────────────────

def log_water(user_id, glasses, goal=8, unit="glasses", log_date=None, note=""):
    if log_date is None:
        log_date = str(date.today())
    conn = get_conn()
    conn.execute(
        """INSERT INTO water (user_id, date, glasses, goal, unit, note) VALUES (?,?,?,?,?,?)
           ON CONFLICT(user_id, date)
           DO UPDATE SET glasses=excluded.glasses, goal=excluded.goal,
                         unit=excluded.unit, note=excluded.note""",
        (user_id, log_date, glasses, goal, unit, note)
    )
    conn.commit(); conn.close()

def get_water_today(user_id):
    conn = get_conn()
    row  = conn.execute(
        "SELECT * FROM water WHERE user_id=? AND date=?",
        (user_id, str(date.today()))
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def get_water_history(user_id, days=30):
    since = str(date.today() - timedelta(days=days - 1))
    conn  = get_conn()
    rows  = conn.execute(
        "SELECT * FROM water WHERE user_id=? AND date>=? ORDER BY date ASC",
        (user_id, since)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_water_all(user_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM water WHERE user_id=? ORDER BY date ASC", (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_water_entry(user_id, entry_date):
    conn = get_conn()
    conn.execute("DELETE FROM water WHERE user_id=? AND date=?", (user_id, entry_date))
    conn.commit(); conn.close()


# ── Sleep functions ───────────────────────────────────────────────────────────

def log_sleep(user_id, bedtime, wake_time, hours_slept, quality=3, log_date=None, note=""):
    if log_date is None:
        log_date = str(date.today())
    conn = get_conn()
    conn.execute(
        """INSERT INTO sleep (user_id, date, bedtime, wake_time, hours_slept, quality, note)
           VALUES (?,?,?,?,?,?,?)
           ON CONFLICT(user_id, date)
           DO UPDATE SET bedtime=excluded.bedtime, wake_time=excluded.wake_time,
                         hours_slept=excluded.hours_slept, quality=excluded.quality,
                         note=excluded.note""",
        (user_id, log_date, bedtime, wake_time, hours_slept, quality, note)
    )
    conn.commit(); conn.close()

def get_sleep_today(user_id):
    conn = get_conn()
    row  = conn.execute(
        "SELECT * FROM sleep WHERE user_id=? AND date=?",
        (user_id, str(date.today()))
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def get_sleep_history(user_id, days=30):
    since = str(date.today() - timedelta(days=days - 1))
    conn  = get_conn()
    rows  = conn.execute(
        "SELECT * FROM sleep WHERE user_id=? AND date>=? ORDER BY date ASC",
        (user_id, since)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_sleep_all(user_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM sleep WHERE user_id=? ORDER BY date ASC", (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_sleep_entry(user_id, entry_date):
    conn = get_conn()
    conn.execute("DELETE FROM sleep WHERE user_id=? AND date=?", (user_id, entry_date))
    conn.commit(); conn.close()


# ── Weight functions ──────────────────────────────────────────────────────────

def log_weight(user_id, weight_kg, goal_kg=None, unit="kg", log_date=None, note=""):
    if log_date is None:
        log_date = str(date.today())
    conn = get_conn()
    conn.execute(
        """INSERT INTO weight (user_id, date, weight_kg, goal_kg, unit, note)
           VALUES (?,?,?,?,?,?)
           ON CONFLICT(user_id, date)
           DO UPDATE SET weight_kg=excluded.weight_kg, goal_kg=excluded.goal_kg,
                         unit=excluded.unit, note=excluded.note""",
        (user_id, log_date, weight_kg, goal_kg, unit, note)
    )
    conn.commit(); conn.close()

def get_weight_today(user_id):
    conn = get_conn()
    row  = conn.execute(
        "SELECT * FROM weight WHERE user_id=? AND date=?",
        (user_id, str(date.today()))
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def get_weight_history(user_id, days=90):
    since = str(date.today() - timedelta(days=days - 1))
    conn  = get_conn()
    rows  = conn.execute(
        "SELECT * FROM weight WHERE user_id=? AND date>=? ORDER BY date ASC",
        (user_id, since)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_weight_all(user_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM weight WHERE user_id=? ORDER BY date ASC", (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_latest_weight(user_id):
    conn = get_conn()
    row  = conn.execute(
        "SELECT * FROM weight WHERE user_id=? ORDER BY date DESC LIMIT 1", (user_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def delete_weight_entry(user_id, entry_date):
    conn = get_conn()
    conn.execute("DELETE FROM weight WHERE user_id=? AND date=?", (user_id, entry_date))
    conn.commit(); conn.close()