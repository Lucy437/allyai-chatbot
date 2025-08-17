import sqlite3

DB_NAME = "allyai.db"

def init_user_profiles_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            phone_number TEXT PRIMARY KEY,
            name TEXT,
            chosen_track TEXT,
            current_day INTEGER DEFAULT 0,
            points INTEGER DEFAULT 0,
            streak INTEGER DEFAULT 0,
            waiting_for_answer BOOLEAN DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def create_or_update_user(phone, name=None, chosen_track=None, current_day=None, points=None, streak=None, waiting_for_answer=None):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    fields = []
    values = []
    if name is not None:
        fields.append("name = ?")
        values.append(name)
    if chosen_track is not None:
        fields.append("chosen_track = ?")
        values.append(chosen_track)
    if current_day is not None:
        fields.append("current_day = ?")
        values.append(current_day)
    if points is not None:
        fields.append("points = ?")
        values.append(points)
    if streak is not None:
        fields.append("streak = ?")
        values.append(streak)
    if waiting_for_answer is not None:
        fields.append("waiting_for_answer = ?")
        values.append(int(waiting_for_answer))

    if fields:
        sql = f"""
            INSERT INTO user_profiles (phone_number) VALUES (?)
            ON CONFLICT(phone_number) DO UPDATE SET {', '.join(fields)}, last_updated = CURRENT_TIMESTAMP
        """
        cur.execute(sql, [phone] + values)

    conn.commit()
    conn.close()


def get_user_profile(phone):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        SELECT phone_number, name, chosen_track, current_day, points, streak, waiting_for_answer
        FROM user_profiles WHERE phone_number = ?
    """, (phone,))
    row = cur.fetchone()
    conn.close()

    if row:
        return {
            "phone_number": row[0],
            "name": row[1],
            "chosen_track": row[2],
            "current_day": row[3],
            "points": row[4],
            "streak": row[5],
            "waiting_for_answer": bool(row[6])
        }
    else:
        return None
