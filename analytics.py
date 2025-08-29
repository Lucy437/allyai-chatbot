import os
import psycopg2
import json
from datetime import datetime

# Get DB URL from environment (set this in Render)
DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    """Establish a connection to the PostgreSQL database."""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL is not set in environment variables.")
    return psycopg2.connect(DATABASE_URL, sslmode="require")


def init_db():
    """Create the events and user_profiles tables if they don't exist."""
    conn = get_connection()
    cur = conn.cursor()

    # Table for logging events
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS usage_events (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            event_type TEXT,
            timestamp TIMESTAMPTZ,
            payload JSONB
        )
    """
    )

    # Table for storing user profiles
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS user_profiles (
            phone_number TEXT PRIMARY KEY,
            name TEXT,
            chosen_track TEXT,
            current_day INTEGER DEFAULT 0,
            points INTEGER DEFAULT 0,
            streak INTEGER DEFAULT 0,
            waiting_for_answer BOOLEAN DEFAULT FALSE,
            last_updated TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    conn.commit()
    cur.close()
    conn.close()


def log_event(user_id, event_type, payload_dict):
    """Insert a usage event into the database."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO usage_events (user_id, event_type, timestamp, payload)
            VALUES (%s, %s, %s, %s)
        """,
            (user_id, event_type, datetime.utcnow(), json.dumps(payload_dict)),
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[Analytics Error] Failed to log event: {e}")


def create_or_update_user(
    phone,
    name=None,
    chosen_track=None,
    current_day=None,
    points=None,
    streak=None,
    waiting_for_answer=None,
):
    """Insert or update a user profile in Postgres."""
    try:
        conn = get_connection()
        cur = conn.cursor()

        fields = []
        values = []
        if name is not None:
            fields.append("name = %s")
            values.append(name)
        if chosen_track is not None:
            fields.append("chosen_track = %s")
            values.append(chosen_track)
        if current_day is not None:
            fields.append("current_day = %s")
            values.append(current_day)
        if points is not None:
            fields.append("points = %s")
            values.append(points)
        if streak is not None:
            fields.append("streak = %s")
            values.append(streak)
        if waiting_for_answer is not None:
            fields.append("waiting_for_answer = %s")
            values.append(waiting_for_answer)

        if fields:
            sql = f"""
                INSERT INTO user_profiles (phone_number) VALUES (%s)
                ON CONFLICT (phone_number) DO UPDATE SET {', '.join(fields)}, last_updated = CURRENT_TIMESTAMP
            """
            cur.execute(sql, [phone] + values)

        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[Analytics Error] Failed to update user profile: {e}")


def get_user_profile(phone):
    """Fetch a user profile by phone number."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT phone_number, name, chosen_track, current_day, points, streak, waiting_for_answer
            FROM user_profiles WHERE phone_number = %s
        """,
            (phone,),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()

        if row:
            return {
                "phone_number": row[0],
                "name": row[1],
                "chosen_track": row[2],
                "current_day": row[3],
                "points": row[4],
                "streak": row[5],
                "waiting_for_answer": bool(row[6]),
            }
        return None
    except Exception as e:
        print(f"[Analytics Error] Failed to fetch user profile: {e}")
        return None
