import sqlite3
from datetime import datetime, time
from typing import Optional, List, Tuple
from models import Event, Attendee, RoutineSlot, UserProfile


class ScheduleDatabase:
    """Manages SQLite tables, relationships, and queries."""

    def __init__(self, db_name: str = "smart_scheduler.db"):
        self.db_name = db_name
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_name)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_db(self) -> None:
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    name TEXT PRIMARY KEY,
                    color_hex TEXT NOT NULL
                );
            """)

            default_categories = [
                ("Work", "#d1e7dd"),
                ("Academic", "#cff4fc"),
                ("Personal", "#fff3cd"),
                ("Health", "#f8d7da")
            ]
            cursor.executemany("""
                INSERT OR IGNORE INTO categories (name, color_hex) VALUES (?, ?);
            """, default_categories)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_profile (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    wake_time TEXT NOT NULL,
                    sleep_time TEXT NOT NULL
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_routines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    day_of_week INTEGER NOT NULL,
                    start_clock TEXT NOT NULL,
                    duration_minutes INTEGER NOT NULL,
                    buffer_before_minutes INTEGER NOT NULL,
                    buffer_after_minutes INTEGER NOT NULL,
                    color_hex TEXT DEFAULT '#fef3c7',
                    FOREIGN KEY (user_id) REFERENCES user_profile (id) ON DELETE CASCADE
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    event_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    start_clock TEXT NOT NULL,
                    duration_minutes INTEGER NOT NULL,
                    buffer_before_minutes INTEGER NOT NULL,
                    buffer_after_minutes INTEGER NOT NULL,
                    total_start_time TEXT NOT NULL,
                    total_end_time TEXT NOT NULL,
                    location TEXT,
                    color_hex TEXT DEFAULT '#ffffff',
                    recurrence_freq TEXT DEFAULT 'None',
                    recurrence_days TEXT DEFAULT ''
                );
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_interval 
                ON events (total_start_time, total_end_time);
            """)
            # Ensure reminder column exists in events table
        try:
            cursor.execute("ALTER TABLE events ADD COLUMN reminder_min INTEGER DEFAULT 0;")
        except Exception:
            pass  # Column already exists
            conn.commit()

    def load_user_profile_with_colors(self) -> Tuple[Optional[UserProfile], List[dict]]:
        """Loads the registered user and recurring routines with their display colors."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, full_name, wake_time, sleep_time FROM user_profile LIMIT 1;")
            user_row = cursor.fetchone()
            if not user_row:
                return None, []

            user_id, name, wake_str, sleep_str = user_row
            cursor.execute("""
                SELECT title, category, day_of_week, start_clock, 
                       duration_minutes, buffer_before_minutes, buffer_after_minutes, color_hex
                FROM user_routines WHERE user_id = ?;
            """, (user_id,))
            
            raw_routines = cursor.fetchall()
            routines = []
            routine_details = []

            for r in raw_routines:
                slot = RoutineSlot(
                    title=r[0], category=r[1], day_of_week=r[2],
                    start_clock=time.fromisoformat(r[3]), duration_minutes=r[4],
                    buffer_before_minutes=r[5], buffer_after_minutes=r[6]
                )
                routines.append(slot)
                routine_details.append({
                    "slot": slot,
                    "color_hex": r[7] or "#fef3c7"
                })

            profile = UserProfile(
                id=user_id, full_name=name,
                wake_time=time.fromisoformat(wake_str),
                sleep_time=time.fromisoformat(sleep_str),
                routines=routines
            )
            return profile, routine_details

    def load_user_profile(self) -> Optional[UserProfile]:
        profile, _ = self.load_user_profile_with_colors()
        return profile

    def save_user_profile_with_colors(self, user: UserProfile, routine_colors: List[str]) -> int:
        """Saves user profile and assigns individual colors to routine slots."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_routines;")
            cursor.execute("DELETE FROM user_profile;")

            cursor.execute("""
                INSERT INTO user_profile (full_name, wake_time, sleep_time)
                VALUES (?, ?, ?);
            """, (user.full_name, user.wake_time.isoformat(), user.sleep_time.isoformat()))
            user_id = cursor.lastrowid

            for idx, r in enumerate(user.routines):
                assigned_color = routine_colors[idx] if idx < len(routine_colors) else "#fef3c7"
                cursor.execute("""
                    INSERT INTO user_routines (
                        user_id, title, category, day_of_week, start_clock,
                        duration_minutes, buffer_before_minutes, buffer_after_minutes, color_hex
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    user_id, r.title, r.category, r.day_of_week,
                    r.start_clock.isoformat(), r.duration_minutes,
                    r.buffer_before_minutes, r.buffer_after_minutes, assigned_color
                ))
            conn.commit()
            return user_id

    def get_categories(self) -> List[Tuple[str, str]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, color_hex FROM categories ORDER BY name ASC;")
            return cursor.fetchall()

    def add_category(self, name: str, color_hex: str) -> None:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO categories (name, color_hex) VALUES (?, ?)
                ON CONFLICT(name) DO UPDATE SET color_hex = excluded.color_hex;
            """, (name, color_hex))
            conn.commit()

    def save_event_record(self, title: str, category: str, event_date_str: str,
                          end_date_str: str, start_clock_str: str, duration: int,
                          buf_before: int, buf_after: int, total_start_str: str,
                          total_end_str: str, color_hex: str, recurrence_freq: str = "None",
                          recurrence_days: str = "", reminder_min: int = 0) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO events (
                    title, category, event_date, end_date, start_clock,
                    duration_minutes, buffer_before_minutes, buffer_after_minutes,
                    total_start_time, total_end_time, color_hex,
                    recurrence_freq, recurrence_days, reminder_min
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                title, category, event_date_str, end_date_str, start_clock_str,
                duration, buf_before, buf_after, total_start_str,
                total_end_str, color_hex, recurrence_freq, recurrence_days, reminder_min
            ))
            conn.commit()
            return cursor.lastrowid

    def delete_event(self, event_id: int) -> None:
        """Deletes an event by its database primary key."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM events WHERE id = ?;", (event_id,))
            conn.commit()

    def update_event_record(self, event_id: int, title: str, category: str,
                            event_date_str: str, end_date_str: str, start_clock_str: str,
                            duration: int, buf_before: int, buf_after: int,
                            total_start_str: str, total_end_str: str, color_hex: str,
                            reminder_min: int = 0):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE events
                SET title = ?,
                    category = ?,
                    event_date = ?,
                    end_date = ?,
                    start_clock = ?,
                    duration_minutes = ?,
                    buffer_before_minutes = ?,
                    buffer_after_minutes = ?,
                    total_start_time = ?,
                    total_end_time = ?,
                    color_hex = ?,
                    reminder_min = ?
                WHERE id = ?;
            """, (
                title, category, event_date_str, end_date_str, start_clock_str,
                duration, buf_before, buf_after, total_start_str, total_end_str,
                color_hex, int(reminder_min), event_id
            ))
            conn.commit()
            print(f">>> DB UPDATED: Event {event_id} set reminder_min to {reminder_min}")