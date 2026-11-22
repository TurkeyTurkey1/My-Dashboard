from __future__ import annotations

from datetime import datetime, timedelta

from app.models import Item


def _at(days: int = 0, hours: int = 0, minutes: int = 0) -> datetime:
    now = datetime.now().replace(second=0, microsecond=0)
    return now + timedelta(days=days, hours=hours, minutes=minutes)


def demo_data() -> dict[str, list[Item]]:
    weekday = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][datetime.now().weekday()]
    return {
        "emails": [
            Item(source="Gmail", title="Welcome to your dashboard", subtitle="demo@example.com", timestamp=_at(hours=-2), meta={"snippet": "Connect Gmail with an App Password in .env"}),
            Item(source="Gmail", title="Assessment reminder", subtitle="teacher@school.example", timestamp=_at(hours=-6), meta={"snippet": "Sample unread message"}),
        ],
        "timetable": [
            Item(source="SEQTA", title="English", subtitle="Room A3 · Ms Patel", timestamp=_at(hours=1), due=_at(hours=1, minutes=50), meta={"day": weekday, "period": "P1"}),
            Item(source="SEQTA", title="Mathematics", subtitle="Room B12 · Mr Nguyen", timestamp=_at(hours=2), due=_at(hours=2, minutes=50), meta={"day": weekday, "period": "P2"}),
            Item(source="SEQTA", title="Science", subtitle="Lab 2 · Dr Lee", timestamp=_at(hours=4), due=_at(hours=4, minutes=50), meta={"day": weekday, "period": "P3"}),
        ],
        "assignments": [
            Item(source="SEQTA", title="English essay draft", subtitle="English", due=_at(days=2, hours=23), meta={"status": "pending"}),
            Item(source="SEQTA", title="Maths problem set", subtitle="Mathematics", due=_at(days=5, hours=9), meta={"status": "pending"}),
            Item(source="SEQTA", title="Science prac report", subtitle="Science", due=_at(days=8, hours=16), meta={"status": "pending"}),
        ],
    }
