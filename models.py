from dataclasses import dataclass, field
from datetime import date, time, datetime, timedelta
from typing import List, Optional


@dataclass
class Attendee:
    """Represents an invited contact."""
    name: str
    phone_number: str


@dataclass
class RoutineSlot:
    """Represents a recurring daily or weekly habit (Workout, Lunch, Sleep window)."""
    title: str
    category: str
    day_of_week: int  # 0 = Monday, 6 = Sunday
    start_clock: time
    duration_minutes: int
    buffer_before_minutes: int = 0
    buffer_after_minutes: int = 0

    def get_effective_window_on_date(self, target_date: date) -> tuple[datetime, datetime]:
        """Calculates gross start and gross end for this routine on a specific date."""
        start_dt = datetime.combine(target_date, self.start_clock)
        gross_start = start_dt - timedelta(minutes=self.buffer_before_minutes)
        gross_end = start_dt + timedelta(minutes=self.duration_minutes + self.buffer_after_minutes)
        return gross_start, gross_end


@dataclass
class UserProfile:
    """Represents the application owner and recurring habits."""
    id: int
    full_name: str
    wake_time: time
    sleep_time: time
    routines: List[RoutineSlot] = field(default_factory=list)

    def check_routine_conflict(self, event_date: date, gross_start: datetime, gross_end: datetime) -> Optional[str]:
        """Checks if a proposed event interval clashes with any recurring personal routine."""
        weekday = event_date.weekday()
        for routine in self.routines:
            if routine.day_of_week == weekday:
                r_start, r_end = routine.get_effective_window_on_date(event_date)
                if (gross_start < r_end) and (gross_end > r_start):
                    return f"Recurring Routine: '{routine.title}' ({r_start.strftime('%H:%M')} - {r_end.strftime('%H:%M')})"
        return None


@dataclass
class Event:
    """Represents a single calendar event with separate date and time objects."""
    title: str
    category: str
    event_date: date
    start_clock: time
    duration_minutes: int
    buffer_before_minutes: int = 0
    buffer_after_minutes: int = 0
    location: Optional[str] = None
    attendees: List[Attendee] = field(default_factory=list)

    @property
    def start_datetime(self) -> datetime:
        return datetime.combine(self.event_date, self.start_clock)

    @property
    def end_datetime(self) -> datetime:
        return self.start_datetime + timedelta(minutes=self.duration_minutes)

    @property
    def total_start_time(self) -> datetime:
        return self.start_datetime - timedelta(minutes=self.buffer_before_minutes)

    @property
    def total_end_time(self) -> datetime:
        return self.end_datetime + timedelta(minutes=self.buffer_after_minutes)

    def overlaps_with(self, other_start: datetime, other_end: datetime) -> bool:
        return (self.total_start_time < other_end) and (self.total_end_time > other_start)