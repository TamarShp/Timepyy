import pandas as pd
from database import ScheduleDatabase


class ScheduleAnalytics:
    """Uses Pandas to analyze scheduling efficiency and time allocations."""

    def __init__(self, db: ScheduleDatabase):
        self.db = db

    def load_events_dataframe(self) -> pd.DataFrame:
        with self.db.get_connection() as conn:
            df = pd.read_sql_query("SELECT * FROM events;", conn)

        # If there are no events yet, return the empty DataFrame safely
        if df.empty or 'event_date' not in df.columns:
            return pd.DataFrame()

        df['event_date'] = pd.to_datetime(df['event_date']).dt.date
        df['total_start_time'] = pd.to_datetime(df['total_start_time'])
        df['total_end_time'] = pd.to_datetime(df['total_end_time'])

        df['net_hours'] = df['duration_minutes'] / 60.0
        df['buffer_total_minutes'] = df['buffer_before_minutes'] + df['buffer_after_minutes']
        df['buffer_total_hours'] = df['buffer_total_minutes'] / 60.0
        df['total_blocked_hours'] = df['net_hours'] + df['buffer_total_hours']
        return df

    def get_category_breakdown(self) -> pd.DataFrame:
        df = self.load_events_dataframe()
        if df.empty:
            print("[INFO] No events found in the database yet to generate analytics.")
            return pd.DataFrame()

        summary = df.groupby('category').agg(
            total_events=('id', 'count'),
            net_productive_hours=('net_hours', 'sum'),
            buffer_overhead_hours=('buffer_total_hours', 'sum'),
            total_blocked_hours=('total_blocked_hours', 'sum')
        ).round(2)

        summary['buffer_percentage'] = (
            (summary['buffer_overhead_hours'] / summary['total_blocked_hours']) * 100
        ).round(1)

        return summary.sort_values(by='total_blocked_hours', ascending=False)