import sqlite3
import json
from datetime import datetime

DB_NAME = "history.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            points_count INTEGER,
            points_json TEXT,
            center_x REAL,
            center_y REAL,
            diameter REAL
        )
    ''')
    conn.commit()
    conn.close()


def save_session(points, sphere=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    pts_data = [[p.x, p.y] for p in points]

    center_x = sphere.center[0] if sphere else None
    center_y = sphere.center[1] if sphere else None
    diameter = sphere.radius * 2 if sphere else None

    cursor.execute('''
        INSERT INTO sessions (timestamp, points_count, points_json, center_x, center_y, diameter)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), len(points), json.dumps(pts_data), center_x, center_y,
          diameter))

    conn.commit()
    conn.close()


def get_recent_sessions(limit=15):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT id, timestamp, points_count, diameter FROM sessions ORDER BY id DESC LIMIT ?', (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_session_data_by_id(session_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT points_json, center_x, center_y, diameter FROM sessions WHERE id = ?', (session_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "points": json.loads(row[0]),
            "center": (row[1], row[2]) if row[1] is not None else None,
            "radius": row[3] / 2 if row[3] is not None else None
        }
    return None