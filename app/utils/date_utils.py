from datetime import datetime, date, time
from typing import Optional

HEBREW_MONTH_NAMES = {
    "ינואר": "January", "פברואר": "February", "מרץ": "March",
    "אפריל": "April", "מאי": "May", "יוני": "June",
    "יולי": "July", "אוגוסט": "August", "ספטמבר": "September",
    "אוקטובר": "October", "נובמבר": "November", "דצמבר": "December"
}

HEBREW_DAY_NAMES = {
    "ראשון": "sunday", "שני": "monday", "שלישי": "tuesday",
    "רביעי": "wednesday", "חמישי": "thursday", "שישי": "friday", "שבת": "saturday"
}

WEEKDAY_INDEX_TO_NAME = {
    0: "monday", 1: "tuesday", 2: "wednesday", 3: "thursday",
    4: "friday", 5: "saturday", 6: "sunday"
}


def parse_hebrew_date(date_str: str) -> Optional[date]:
    """Parse Hebrew date format (e.g., 'שישי, 12 אפריל 2025') to Python date."""
    if not date_str or not isinstance(date_str, str):
        return None
    try:
        if "," not in date_str:
            return None
        _, date_part = date_str.split(",", 1)
        date_part = date_part.strip()
        parts = date_part.split()
        if len(parts) < 3:
            return None
        day_num = parts[0]
        month_name = parts[1]
        year = parts[2]
        if month_name in HEBREW_MONTH_NAMES:
            month_name = HEBREW_MONTH_NAMES[month_name]
        return datetime.strptime(f"{day_num} {month_name} {year}", "%d %B %Y").date()
    except (ValueError, IndexError):
        return None


def calculate_days_ahead(slot_date: date) -> int:
    """Calculate how many days ahead a date is from today."""
    today = date.today()
    return (slot_date - today).days


def get_weekday_name(date_obj: date) -> str:
    """Get lowercase weekday name (monday, tuesday, etc.) from a date."""
    return WEEKDAY_INDEX_TO_NAME[date_obj.weekday()]


def parse_slot_start_time(time_str: str) -> Optional[time]:
    """Parse slot time string (e.g., '14:00 - 18:00') and return start time."""
    if not time_str or not isinstance(time_str, str):
        return None
    try:
        if " - " in time_str:
            start_str = time_str.split(" - ")[0].strip()
        else:
            start_str = time_str.strip()
        parts = start_str.split(":")
        if len(parts) >= 2:
            return time(int(parts[0]), int(parts[1]))
        return None
    except (ValueError, IndexError):
        return None


def parse_time_string(time_str: str) -> Optional[time]:
    """Parse a time string (e.g., '14:00') to a time object."""
    if not time_str or not isinstance(time_str, str):
        return None
    try:
        parts = time_str.strip().split(":")
        if len(parts) >= 2:
            return time(int(parts[0]), int(parts[1]))
        return None
    except (ValueError, IndexError):
        return None


def is_time_in_range(slot_time: time, from_str: str, to_str: str) -> bool:
    """Check if slot_time falls within the range [from_str, to_str]."""
    from_time = parse_time_string(from_str)
    to_time = parse_time_string(to_str)
    if from_time is None or to_time is None:
        return True  # fail-open on parse error
    return from_time <= slot_time <= to_time
