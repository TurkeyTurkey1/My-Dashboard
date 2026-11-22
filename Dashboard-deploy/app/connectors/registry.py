from __future__ import annotations

import asyncio
from datetime import datetime

from app.connectors.gmail_imap import GmailImapConnector
from app.connectors.seqta import SeqtaConnector
from app.models import DashboardData, Item

CONNECTORS = [GmailImapConnector(), SeqtaConnector()]


def _sort_key(item: Item) -> datetime:
    return item.due or item.timestamp or datetime.max


async def collect() -> DashboardData:
    results = await asyncio.gather(*(c.fetch() for c in CONNECTORS), return_exceptions=True)
    emails: list[Item] = []
    timetable: list[Item] = []
    assignments: list[Item] = []
    states = []
    warnings: list[str] = []

    for res in results:
        if isinstance(res, Exception):
            warnings.append(str(res)[:200])
            continue
        states.append(res.state)
        if res.state.status == "error":
            warnings.append(f"{res.state.name}: {res.state.detail}")
        for item in res.data.get("emails", []):
            emails.append(item)
        for item in res.data.get("timetable", []):
            timetable.append(item)
        for item in res.data.get("assignments", []):
            assignments.append(item)

    emails.sort(key=lambda i: i.timestamp or datetime.min, reverse=True)
    timetable.sort(key=lambda i: (str(i.meta.get("day", "")), i.timestamp or datetime.max, i.title))
    assignments.sort(key=_sort_key)

    return DashboardData(
        generated_at=datetime.now(),
        connectors=states,
        emails=emails,
        timetable=timetable,
        assignments=assignments,
        warnings=warnings,
    )
