"""India Standard Time (IST, UTC+05:30) helpers for timestamps stored/displayed in the app."""

from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))


def now_ist() -> datetime:
    return datetime.now(IST)


def now_str() -> str:
    """Wall-clock timestamp in Asia/Kolkata (IST): YYYY-MM-DD HH:MM:SS"""
    return now_ist().strftime("%Y-%m-%d %H:%M:%S")


def today_str() -> str:
    return now_ist().strftime("%Y-%m-%d")
