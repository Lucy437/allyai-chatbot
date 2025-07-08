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
    """Create the events table if it doesn't exist."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS usage_events (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            event_type TEXT,
            timestamp TIMESTAMPTZ,
            payload JSONB
        )
    """)
    conn.commit()
    cur.close()
    conn.close()


def log_event(user_id, event_type, payload_dict):
    """Insert a usage event into the database."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO usage_events (user_id, event_type, timestamp, payload)
            VALUES (%s, %s, %s, %s)
        """, (user_id, event_type, datetime.utcnow(), json.dumps(payload_dict)))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[Analytics Error] Failed to log event: {e}")
